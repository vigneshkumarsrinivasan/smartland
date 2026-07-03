"""
Rate limiting setup for LandSignal AI.

Uses slowapi (wrapper around `limits` library) on top of FastAPI/Starlette.

Key function precedence:
  1. X-Api-Key header present → use the key value as identifier (each key gets its own bucket)
  2. Authenticated user (Bearer token) → use "user:<id>"
  3. Fallback → remote IP address

Default limits:
  - Browser/IP traffic:   60 req/minute
  - API key traffic:      determined per key (requests_per_minute from DB)
  - Unauthenticated:      30 req/minute

Rate limit headers (X-RateLimit-*) are disabled — slowapi requires a
`response: Response` parameter on every decorated endpoint to inject them,
which would pollute every route signature.
"""
import logging
from starlette.requests import Request
from slowapi import Limiter
from slowapi.util import get_remote_address

logger = logging.getLogger(__name__)

_API_KEY_HEADER = "X-Api-Key"
_AUTH_HEADER = "Authorization"


def _identify_request(request: Request) -> str:
    """Custom key function: API key → user token → IP."""
    api_key = request.headers.get(_API_KEY_HEADER)
    if api_key:
        return f"apikey:{api_key[:16]}"  # truncated — enough for bucketing

    auth = request.headers.get(_AUTH_HEADER, "")
    if auth.startswith("Bearer "):
        token = auth[7:16]  # first 9 chars of token for bucketing
        return f"token:{token}"

    return get_remote_address(request)


limiter = Limiter(
    key_func=_identify_request,
    default_limits=["60/minute"],
    headers_enabled=False,  # header injection requires response: Response param in every endpoint
)


def get_rate_limit_for_api_key(api_key_value: str) -> str:
    """
    Look up the per-key rate limit from the database.
    Returns a slowapi limit string like "120/minute".
    Falls back to "10/minute" if the key is not found or inactive.
    """
    try:
        from app.database import SessionLocal
        from app.models import ApiKey
        import hashlib
        key_hash = hashlib.sha256(api_key_value.encode()).hexdigest()
        db = SessionLocal()
        try:
            key_obj = db.query(ApiKey).filter(
                ApiKey.key_hash == key_hash,
                ApiKey.is_active == True,
            ).first()
            if key_obj:
                return f"{key_obj.requests_per_minute}/minute"
        finally:
            db.close()
    except Exception as exc:
        logger.warning("Rate limit lookup failed: %s", exc)
    return "10/minute"
