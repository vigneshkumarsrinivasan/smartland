"""
API Key management router.

Endpoints:
  GET    /api-keys          — list caller's active API keys
  POST   /api-keys          — generate a new API key (Enterprise plan required)
  DELETE /api-keys/{id}     — revoke a key

Key format:  ls_live_<32 random hex chars>   (e.g. ls_live_a3f91c...)
Stored:      SHA-256 hash of full key
Displayed:   prefix only after creation (ls_live_a3f91c...)
             Full key shown ONCE at creation time — cannot be recovered.

Rate limits: stored per key in ApiKey.requests_per_minute
  Enterprise plan → 300 req/min (default for new keys)
  Pro plan        → 60  req/min
  Free plan       → not allowed to create keys
"""
import hashlib
import os
import secrets
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import ApiKey, User
from app.routers.billing import get_current_user

router = APIRouter(prefix="/api-keys", tags=["api-keys"])

_KEY_PREFIX = "ls_live_"
_RPM_BY_PLAN = {"enterprise": 300, "pro": 60, "free": 0}


def _generate_raw_key() -> str:
    return _KEY_PREFIX + secrets.token_hex(32)


def _hash_key(raw: str) -> str:
    return hashlib.sha256(raw.encode()).hexdigest()


def _key_to_dict(key: ApiKey, raw: Optional[str] = None) -> dict:
    d = {
        "id": key.id,
        "name": key.name,
        "key_prefix": key.key_prefix,
        "scopes": key.scopes,
        "requests_per_minute": key.requests_per_minute,
        "last_used_at": key.last_used_at.isoformat() if key.last_used_at else None,
        "expires_at": key.expires_at.isoformat() if key.expires_at else None,
        "is_active": key.is_active,
        "created_at": key.created_at.isoformat(),
    }
    if raw:
        d["key"] = raw  # shown ONCE at creation
    return d


class ApiKeyCreateRequest(BaseModel):
    name: str
    scopes: str = "read"   # "read" | "read,write"


@router.get("")
def list_api_keys(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    keys = (
        db.query(ApiKey)
        .filter(ApiKey.user_id == current_user.id, ApiKey.is_active == True)
        .order_by(ApiKey.created_at.desc())
        .all()
    )
    return [_key_to_dict(k) for k in keys]


@router.post("")
def create_api_key(
    body: ApiKeyCreateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Generate a new API key. Enterprise plan required; Pro users get 60 req/min keys."""
    plan_slug = current_user.plan.slug if current_user.plan else "free"
    rpm = _RPM_BY_PLAN.get(plan_slug, 0)

    if rpm == 0:
        raise HTTPException(
            status_code=403,
            detail="API key access requires a Pro or Enterprise subscription. Upgrade at /pricing.",
        )

    if body.scopes not in ("read", "read,write"):
        raise HTTPException(status_code=422, detail="scopes must be 'read' or 'read,write'")

    # Enterprise-only write scope
    if body.scopes == "read,write" and plan_slug != "enterprise":
        raise HTTPException(
            status_code=403,
            detail="Write scope requires an Enterprise subscription.",
        )

    raw_key = _generate_raw_key()
    key_obj = ApiKey(
        user_id=current_user.id,
        name=body.name,
        key_hash=_hash_key(raw_key),
        key_prefix=raw_key[:20],  # "ls_live_" + first 12 random chars
        scopes=body.scopes,
        requests_per_minute=rpm,
    )
    db.add(key_obj)
    db.commit()
    db.refresh(key_obj)

    return _key_to_dict(key_obj, raw=raw_key)


@router.delete("/{key_id}")
def revoke_api_key(
    key_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    key_obj = (
        db.query(ApiKey)
        .filter(ApiKey.id == key_id, ApiKey.user_id == current_user.id)
        .first()
    )
    if not key_obj:
        raise HTTPException(status_code=404, detail="API key not found")
    key_obj.is_active = False
    db.commit()
    return {"status": "revoked"}


def validate_api_key(raw_key: str, db: Session) -> Optional[ApiKey]:
    """
    Validate a raw API key from an X-Api-Key header.
    Returns the ApiKey row if valid and active, None otherwise.
    Updates last_used_at on successful validation.
    """
    key_hash = _hash_key(raw_key)
    key_obj = (
        db.query(ApiKey)
        .filter(ApiKey.key_hash == key_hash, ApiKey.is_active == True)
        .first()
    )
    if not key_obj:
        return None
    if key_obj.expires_at and key_obj.expires_at < datetime.utcnow():
        return None
    key_obj.last_used_at = datetime.utcnow()
    db.commit()
    return key_obj
