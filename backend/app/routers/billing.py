"""
Billing router — Razorpay subscription management.

Endpoints:
  GET  /billing/plans       — list active plans (public)
  POST /billing/register    — create / login user, returns auth token
  GET  /billing/me          — current user + subscription + usage (auth required)
  POST /billing/subscribe   — create Razorpay subscription or mock (auth required)
  POST /billing/webhook     — Razorpay webhook handler (signature verified)
  POST /billing/cancel      — cancel active subscription (auth required)

Auth: Bearer token passed as Authorization header. Token is a UUID stored in User.auth_token.
Razorpay: mock mode when RAZORPAY_KEY_ID env var is not set (returns fake checkout params).
"""
import json
import os
import hashlib
import hmac
import logging
from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from pydantic import BaseModel, EmailStr
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Plan, User, Subscription, UsageLog

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/billing", tags=["billing"])

RAZORPAY_KEY_ID = os.getenv("RAZORPAY_KEY_ID", "")
RAZORPAY_KEY_SECRET = os.getenv("RAZORPAY_KEY_SECRET", "")
RAZORPAY_WEBHOOK_SECRET = os.getenv("RAZORPAY_WEBHOOK_SECRET", "")
MOCK_MODE = not (RAZORPAY_KEY_ID and RAZORPAY_KEY_SECRET)


def _get_razorpay_client():
    if MOCK_MODE:
        return None
    import razorpay
    return razorpay.Client(auth=(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET))


# ── Auth dependency ────────────────────────────────────────────────────────────

def get_current_user(
    authorization: Optional[str] = Header(default=None),
    db: Session = Depends(get_db),
) -> User:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Authorization header required")
    token = authorization.split(" ", 1)[1].strip()
    user = db.query(User).filter(User.auth_token == token).first()
    if not user:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    return user


# ── Pydantic schemas ───────────────────────────────────────────────────────────

class RegisterRequest(BaseModel):
    email: str
    name: Optional[str] = None


class SubscribeRequest(BaseModel):
    plan_slug: str


# ── Helpers ────────────────────────────────────────────────────────────────────

def _plan_to_dict(plan: Plan) -> dict:
    features = json.loads(plan.features_json) if plan.features_json else []
    return {
        "id": plan.id,
        "name": plan.name,
        "slug": plan.slug,
        "price_inr": plan.price_inr,
        "billing_cycle": plan.billing_cycle,
        "max_reports_per_month": plan.max_reports_per_month,
        "features": features,
        "razorpay_plan_id": plan.razorpay_plan_id,
    }


def _subscription_to_dict(sub: Optional[Subscription]) -> Optional[dict]:
    if not sub:
        return None
    return {
        "id": sub.id,
        "plan_id": sub.plan_id,
        "razorpay_subscription_id": sub.razorpay_subscription_id,
        "status": sub.status,
        "current_period_start": sub.current_period_start.isoformat() if sub.current_period_start else None,
        "current_period_end": sub.current_period_end.isoformat() if sub.current_period_end else None,
        "created_at": sub.created_at.isoformat(),
    }


def _reports_this_month(user_id: int, db: Session) -> int:
    start = datetime.utcnow().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    return (
        db.query(func.count(UsageLog.id))
        .filter(
            UsageLog.user_id == user_id,
            UsageLog.event_type == "area_report",
            UsageLog.created_at >= start,
        )
        .scalar()
        or 0
    )


def _active_subscription(user_id: int, db: Session) -> Optional[Subscription]:
    return (
        db.query(Subscription)
        .filter(
            Subscription.user_id == user_id,
            Subscription.status.in_(["active", "authenticated"]),
        )
        .order_by(Subscription.created_at.desc())
        .first()
    )


# ── Routes ────────────────────────────────────────────────────────────────────

@router.get("/plans")
def list_plans(db: Session = Depends(get_db)):
    plans = db.query(Plan).filter(Plan.is_active == True).order_by(Plan.price_inr).all()
    return [_plan_to_dict(p) for p in plans]


@router.post("/register")
def register(body: RegisterRequest, db: Session = Depends(get_db)):
    """Create a new user or return existing one. Returns auth token."""
    user = db.query(User).filter(User.email == body.email).first()
    if not user:
        # Assign Free plan by default
        free_plan = db.query(Plan).filter(Plan.slug == "free").first()
        user = User(
            email=body.email,
            name=body.name,
            auth_token=User.generate_token(),
            plan_id=free_plan.id if free_plan else None,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    elif not user.auth_token:
        user.auth_token = User.generate_token()
        db.commit()
        db.refresh(user)

    plan = db.query(Plan).filter(Plan.id == user.plan_id).first() if user.plan_id else None
    return {
        "token": user.auth_token,
        "user": {
            "id": user.id,
            "email": user.email,
            "name": user.name,
            "plan": _plan_to_dict(plan) if plan else None,
        },
    }


@router.get("/me")
def get_me(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    plan = db.query(Plan).filter(Plan.id == current_user.plan_id).first() if current_user.plan_id else None
    sub = _active_subscription(current_user.id, db)
    reports_used = _reports_this_month(current_user.id, db)
    return {
        "user": {
            "id": current_user.id,
            "email": current_user.email,
            "name": current_user.name,
            "plan": _plan_to_dict(plan) if plan else None,
        },
        "subscription": _subscription_to_dict(sub),
        "usage": {
            "reports_used_this_month": reports_used,
            "reports_limit": plan.max_reports_per_month if plan else 3,
        },
    }


@router.post("/subscribe")
def subscribe(
    body: SubscribeRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Create a Razorpay subscription for the requested plan.
    Returns checkout params for the frontend to open Razorpay modal.
    In mock mode (no API keys), returns fake params so UI still works.
    """
    plan = db.query(Plan).filter(Plan.slug == body.plan_slug, Plan.is_active == True).first()
    if not plan:
        raise HTTPException(status_code=404, detail=f"Plan '{body.plan_slug}' not found")

    if plan.slug == "free":
        # Downgrade: just set plan_id and cancel any active sub
        active = _active_subscription(current_user.id, db)
        if active:
            active.status = "cancelled"
        current_user.plan_id = plan.id
        db.commit()
        return {"status": "switched", "plan": _plan_to_dict(plan)}

    if MOCK_MODE:
        # Dev/test: return mock checkout params, create a mock active subscription
        sub = Subscription(
            user_id=current_user.id,
            plan_id=plan.id,
            razorpay_subscription_id=f"sub_mock_{current_user.id}_{plan.slug}",
            status="active",
            current_period_start=datetime.utcnow(),
            current_period_end=datetime.utcnow() + timedelta(days=30),
        )
        db.add(sub)
        current_user.plan_id = plan.id
        db.commit()
        db.refresh(sub)
        return {
            "mock_mode": True,
            "status": "active",
            "plan": _plan_to_dict(plan),
            "subscription": _subscription_to_dict(sub),
            "checkout_params": {
                "key": "rzp_test_mock",
                "subscription_id": sub.razorpay_subscription_id,
                "name": "LandSignal AI",
                "description": f"{plan.name} Plan — ₹{plan.price_inr}/month",
            },
        }

    # Live Razorpay mode
    client = _get_razorpay_client()
    if not plan.razorpay_plan_id:
        raise HTTPException(
            status_code=422,
            detail=f"Plan '{plan.slug}' has no Razorpay plan ID configured. "
                   "Create the plan in Razorpay dashboard and set razorpay_plan_id.",
        )

    try:
        rz_sub = client.subscription.create({
            "plan_id": plan.razorpay_plan_id,
            "customer_notify": 1,
            "quantity": 1,
            "total_count": 12,
            "notes": {"user_id": str(current_user.id), "email": current_user.email},
        })
    except Exception as exc:
        logger.error("Razorpay subscription creation failed: %s", exc)
        raise HTTPException(status_code=502, detail=f"Razorpay error: {exc}")

    sub = Subscription(
        user_id=current_user.id,
        plan_id=plan.id,
        razorpay_subscription_id=rz_sub["id"],
        status=rz_sub.get("status", "created"),
    )
    db.add(sub)
    db.commit()
    db.refresh(sub)

    return {
        "mock_mode": False,
        "status": sub.status,
        "plan": _plan_to_dict(plan),
        "subscription": _subscription_to_dict(sub),
        "checkout_params": {
            "key": RAZORPAY_KEY_ID,
            "subscription_id": sub.razorpay_subscription_id,
            "name": "LandSignal AI",
            "description": f"{plan.name} Plan — ₹{plan.price_inr}/month",
            "prefill": {"email": current_user.email, "name": current_user.name or ""},
        },
    }


@router.post("/webhook")
async def razorpay_webhook(request: Request, db: Session = Depends(get_db)):
    """Handle Razorpay subscription webhook events."""
    body_bytes = await request.body()
    signature = request.headers.get("x-razorpay-signature", "")

    if RAZORPAY_WEBHOOK_SECRET and signature:
        expected = hmac.new(
            RAZORPAY_WEBHOOK_SECRET.encode(),
            body_bytes,
            hashlib.sha256,
        ).hexdigest()
        if not hmac.compare_digest(expected, signature):
            raise HTTPException(status_code=400, detail="Invalid webhook signature")

    try:
        payload = json.loads(body_bytes)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON payload")

    event = payload.get("event", "")
    entity = payload.get("payload", {}).get("subscription", {}).get("entity", {})
    rz_sub_id = entity.get("id")
    if not rz_sub_id:
        return {"status": "ignored"}

    sub = db.query(Subscription).filter(
        Subscription.razorpay_subscription_id == rz_sub_id
    ).first()
    if not sub:
        logger.warning("Webhook for unknown subscription %s", rz_sub_id)
        return {"status": "unknown_subscription"}

    STATUS_MAP = {
        "subscription.authenticated": "authenticated",
        "subscription.activated": "active",
        "subscription.charged": "active",
        "subscription.paused": "paused",
        "subscription.resumed": "active",
        "subscription.cancelled": "cancelled",
        "subscription.completed": "completed",
        "subscription.expired": "expired",
    }

    if event in STATUS_MAP:
        sub.status = STATUS_MAP[event]

    if event in ("subscription.activated", "subscription.charged"):
        # Update period dates from payload if present
        cs = entity.get("current_start")
        ce = entity.get("current_end")
        if cs:
            sub.current_period_start = datetime.utcfromtimestamp(cs)
        if ce:
            sub.current_period_end = datetime.utcfromtimestamp(ce)
        # Upgrade user's plan
        if sub.user:
            sub.user.plan_id = sub.plan_id

    if event == "subscription.cancelled":
        # Revert to free plan
        free_plan = db.query(Plan).filter(Plan.slug == "free").first()
        if sub.user and free_plan:
            sub.user.plan_id = free_plan.id

    db.commit()
    logger.info("Webhook %s processed for subscription %s", event, rz_sub_id)
    return {"status": "ok", "event": event}


@router.post("/cancel")
def cancel_subscription(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    sub = _active_subscription(current_user.id, db)
    if not sub:
        raise HTTPException(status_code=404, detail="No active subscription found")

    if not MOCK_MODE and sub.razorpay_subscription_id and not sub.razorpay_subscription_id.startswith("sub_mock_"):
        try:
            client = _get_razorpay_client()
            client.subscription.cancel(sub.razorpay_subscription_id, {"cancel_at_cycle_end": 1})
        except Exception as exc:
            logger.error("Razorpay cancel failed: %s", exc)
            raise HTTPException(status_code=502, detail=f"Razorpay error: {exc}")

    sub.status = "cancelled"
    free_plan = db.query(Plan).filter(Plan.slug == "free").first()
    if free_plan:
        current_user.plan_id = free_plan.id
    db.commit()
    return {"status": "cancelled"}


@router.post("/log-usage")
def log_usage(
    event_type: str,
    resource_id: Optional[int] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Record a usage event and check if the user is within their plan limits."""
    plan = db.query(Plan).filter(Plan.id == current_user.plan_id).first() if current_user.plan_id else None

    if event_type == "area_report" and plan and plan.max_reports_per_month is not None:
        used = _reports_this_month(current_user.id, db)
        if used >= plan.max_reports_per_month:
            raise HTTPException(
                status_code=402,
                detail={
                    "code": "usage_limit_exceeded",
                    "message": f"You've used {used}/{plan.max_reports_per_month} reports this month. Upgrade to Pro for unlimited access.",
                    "upgrade_url": "/pricing",
                },
            )

    log = UsageLog(user_id=current_user.id, event_type=event_type, resource_id=resource_id)
    db.add(log)
    db.commit()
    return {"status": "logged", "event_type": event_type}
