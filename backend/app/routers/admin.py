"""
Admin router.

POST /admin/pipeline/run — trigger all data pipeline ingesters sequentially.

Auth: X-Admin-Key header checked against ADMIN_API_KEY env var.
      If ADMIN_API_KEY is not set, auth is bypassed (dev mode only).
"""
import os
import logging
from datetime import datetime

from fastapi import APIRouter, Header, HTTPException

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/admin", tags=["admin"])

_ADMIN_KEY = os.getenv("ADMIN_API_KEY", "")


def _check_auth(x_admin_key: str | None) -> None:
    if not _ADMIN_KEY:
        return  # dev mode: no key set → open
    if x_admin_key != _ADMIN_KEY:
        raise HTTPException(status_code=401, detail="Invalid admin key")


@router.post("/pipeline/run")
def run_pipeline(x_admin_key: str | None = Header(default=None)):
    """
    Trigger all data pipeline ingesters sequentially.
    Returns a summary of each ingester's run result.
    """
    _check_auth(x_admin_key)

    # Import here to avoid circular imports at startup
    from data_pipeline.flood_risk import FloodRiskIngester
    from data_pipeline.population import PopulationIngester
    from data_pipeline.infrastructure import InfrastructureIngester
    from data_pipeline.land_transactions import LandTransactionsIngester
    from data_pipeline.commercial_activity import CommercialActivityIngester

    ingesters = [
        FloodRiskIngester(),
        PopulationIngester(),
        InfrastructureIngester(),
        LandTransactionsIngester(),
        CommercialActivityIngester(),
    ]

    started_at = datetime.utcnow().isoformat()
    results = []

    for ingester in ingesters:
        logger.info("Running ingester: %s", ingester.source_name)
        result = ingester.run()
        results.append(result)

    total_inserted = sum(r.get("inserted", 0) for r in results)
    total_updated = sum(r.get("updated", 0) for r in results)
    all_ok = all(r.get("status") == "ok" for r in results)

    return {
        "started_at": started_at,
        "completed_at": datetime.utcnow().isoformat(),
        "overall_status": "ok" if all_ok else "partial",
        "total_inserted": total_inserted,
        "total_updated": total_updated,
        "ingesters": results,
    }
