"""
Alerts router — manage user alert subscriptions for area price/score changes.

Endpoints:
  GET  /alerts           — list current user's active alerts
  POST /alerts           — subscribe to an alert for an area
  DELETE /alerts/{id}    — remove an alert subscription
  POST /alerts/test-fire — manually trigger check_price_alerts (admin testing)
"""
from typing import Optional
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Header
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Alert, Area, User
from app.routers.billing import get_current_user

router = APIRouter(prefix="/alerts", tags=["alerts"])


class AlertCreateRequest(BaseModel):
    area_id: int
    alert_type: str = "price_movement"   # "price_movement" | "score_change" | "weekly_digest"
    channel: str = "email"               # "email" | "whatsapp" | "both"
    threshold: Optional[float] = 5.0
    phone: Optional[str] = None          # required when channel is whatsapp/both


def _alert_to_dict(alert: Alert) -> dict:
    return {
        "id": alert.id,
        "area_id": alert.area_id,
        "area_name": alert.area.name if alert.area else None,
        "city": alert.area.city.name if (alert.area and alert.area.city) else None,
        "alert_type": alert.alert_type,
        "channel": alert.channel,
        "threshold": alert.threshold,
        "phone": alert.phone,
        "is_active": alert.is_active,
        "last_triggered_at": alert.last_triggered_at.isoformat() if alert.last_triggered_at else None,
        "created_at": alert.created_at.isoformat(),
    }


@router.get("")
def list_alerts(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    alerts = (
        db.query(Alert)
        .filter(Alert.user_id == current_user.id, Alert.is_active == True)
        .order_by(Alert.created_at.desc())
        .all()
    )
    return [_alert_to_dict(a) for a in alerts]


@router.post("")
def create_alert(
    body: AlertCreateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    area = db.query(Area).filter(Area.id == body.area_id).first()
    if not area:
        raise HTTPException(status_code=404, detail="Area not found")

    if body.alert_type not in ("price_movement", "score_change", "weekly_digest"):
        raise HTTPException(status_code=422, detail="Invalid alert_type")

    if body.channel not in ("email", "whatsapp", "both"):
        raise HTTPException(status_code=422, detail="Invalid channel")

    if body.channel in ("whatsapp", "both") and not body.phone:
        raise HTTPException(
            status_code=422,
            detail="phone is required when channel is 'whatsapp' or 'both'",
        )

    # Upsert: one alert per (user, area, type, channel)
    existing = (
        db.query(Alert)
        .filter(
            Alert.user_id == current_user.id,
            Alert.area_id == body.area_id,
            Alert.alert_type == body.alert_type,
        )
        .first()
    )
    if existing:
        existing.channel = body.channel
        existing.threshold = body.threshold
        existing.phone = body.phone
        existing.is_active = True
        db.commit()
        db.refresh(existing)
        return _alert_to_dict(existing)

    alert = Alert(
        user_id=current_user.id,
        area_id=body.area_id,
        alert_type=body.alert_type,
        channel=body.channel,
        threshold=body.threshold,
        phone=body.phone,
    )
    db.add(alert)
    db.commit()
    db.refresh(alert)
    return _alert_to_dict(alert)


@router.delete("/{alert_id}")
def delete_alert(
    alert_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    alert = (
        db.query(Alert)
        .filter(Alert.id == alert_id, Alert.user_id == current_user.id)
        .first()
    )
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    alert.is_active = False
    db.commit()
    return {"status": "deleted"}


@router.post("/test-fire")
def test_fire_alerts(
    x_admin_key: Optional[str] = Header(default=None, alias="X-Admin-Key"),
):
    """Manually run the daily alert check (for testing without waiting for cron)."""
    import os
    key = os.getenv("ADMIN_API_KEY", "")
    if key and x_admin_key != key:
        raise HTTPException(status_code=403, detail="Invalid admin key")

    from app.scheduler import check_price_alerts
    check_price_alerts()
    return {"status": "fired"}
