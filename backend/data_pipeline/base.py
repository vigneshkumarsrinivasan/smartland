"""
BaseIngester — shared logic for all data pipeline ingesters.

Every ingester:
  1. Implements ingest(db) → dict with inserted/updated/skipped counts
  2. Calls run() which handles the DB session, DataSource bookkeeping, and logging
  3. Can call recompute_predictions(db, area_ids) after updating signals
"""
import logging
import sys
import os
from datetime import datetime

# Allow running from backend/ directory
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.models import DataSource, GrowthSignal, RiskSignal, Prediction, Area
from app.scoring import AreaSignals, score_area

logger = logging.getLogger(__name__)


class BaseIngester:
    source_name: str = "Unknown"
    source_category: str = "Pipeline"
    freshness_hours: int = 24

    def ingest(self, db: Session) -> dict:
        raise NotImplementedError("Subclasses must implement ingest(db)")

    def run(self) -> dict:
        """Run the ingester: open DB session, call ingest(), update DataSource, log summary."""
        # Ensure schema is up-to-date before opening a session
        # (important when running standalone outside FastAPI startup)
        from app.database import upgrade_db
        upgrade_db()

        result: dict = {
            "source": self.source_name,
            "status": "error",
            "inserted": 0,
            "updated": 0,
            "skipped": 0,
        }
        db = SessionLocal()
        try:
            counts = self.ingest(db)
            result.update(counts)
            result["status"] = "ok"
            self._upsert_data_source(db, "active")
        except Exception as exc:
            logger.error("[%s] ingestion failed: %s", self.source_name, exc)
            result["error"] = str(exc)
            self._upsert_data_source(db, "degraded")
        finally:
            db.close()

        result["timestamp"] = datetime.utcnow().isoformat()
        self._log_summary(result)
        return result

    # ------------------------------------------------------------------
    # Helpers

    def _upsert_data_source(self, db: Session, status: str) -> None:
        ds = db.query(DataSource).filter(DataSource.name == self.source_name).first()
        now = datetime.utcnow()
        if ds:
            ds.status = status
            ds.last_run_at = now
            ds.last_updated = now
            ds.freshness_hours = self.freshness_hours
        else:
            ds = DataSource(
                name=self.source_name,
                category=self.source_category,
                status=status,
                last_updated=now,
                last_run_at=now,
                freshness_hours=self.freshness_hours,
                coverage="Bangalore, Hyderabad, Pune, Chennai, Coimbatore",
            )
            db.add(ds)
        db.commit()

    def recompute_predictions(self, db: Session, area_ids: list) -> int:
        """Re-score areas whose signals were updated. Returns number of predictions refreshed."""
        refreshed = 0
        for area_id in area_ids:
            gs = db.query(GrowthSignal).filter(GrowthSignal.area_id == area_id).first()
            rs = db.query(RiskSignal).filter(RiskSignal.area_id == area_id).first()
            if not gs or not rs:
                continue

            def _v(val):
                return float(val) if val is not None else 50.0

            signals = AreaSignals(
                infrastructure=_v(gs.infrastructure_score),
                job_growth=_v(gs.job_growth_score),
                population_growth=_v(gs.population_growth_score),
                commercial_activity=_v(gs.commercial_activity_score),
                transaction_velocity=_v(gs.transaction_velocity_score),
                land_scarcity=_v(gs.land_scarcity_score),
                government_spending=_v(gs.government_spending_score),
                flood_risk=_v(rs.flood_risk),
                water_risk=_v(rs.water_risk),
                legal_risk=_v(rs.legal_risk),
                overvaluation_risk=_v(rs.overvaluation_risk),
                pollution_risk=_v(rs.pollution_risk),
                crime_risk=_v(rs.crime_risk),
                delay_risk=_v(rs.delay_risk),
            )
            scored = score_area(signals)

            pred = (
                db.query(Prediction)
                .filter(Prediction.area_id == area_id)
                .order_by(Prediction.generated_at.desc())
                .first()
            )
            if pred:
                pred.growth_score = scored.growth_score
                pred.risk_score = scored.risk_score
                pred.confidence_score = scored.confidence_score
                pred.recommendation = scored.recommendation
                pred.generated_at = datetime.utcnow()
            else:
                db.add(Prediction(
                    area_id=area_id,
                    growth_score=scored.growth_score,
                    risk_score=scored.risk_score,
                    confidence_score=scored.confidence_score,
                    recommendation=scored.recommendation,
                ))
            refreshed += 1
        db.commit()
        return refreshed

    def _log_summary(self, result: dict) -> None:
        print(
            f"[{result['source']}] status={result['status']} "
            f"inserted={result.get('inserted', 0)} "
            f"updated={result.get('updated', 0)} "
            f"skipped={result.get('skipped', 0)} "
            f"ts={result.get('timestamp', '')}"
        )
        if "error" in result:
            print(f"  ERROR: {result['error']}")
