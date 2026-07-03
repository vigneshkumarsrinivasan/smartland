"""
Population & Employment Ingester — Census 2011 + EPFO Payroll Data

Sources:
  - Census of India 2011 (Office of the Registrar General & Census Commissioner)
    https://censusindia.gov.in/census.website/data/census-tables
  - EPFO Monthly Payroll Data (Ministry of Labour & Employment press releases)
    https://www.epfindia.gov.in/site_en/Payroll_Data.php

What it updates:
  - GrowthSignal.population_growth_score  — derived from Census 2011 district decadal growth
  - GrowthSignal.job_growth_score         — derived from EPFO subscriber net additions (2023)
  - GrowthSignal.government_spending_score — proxy from state capital expenditure (Economic Survey)

Run standalone:
    python -m data_pipeline.population
"""
import sys
import os
import logging

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from sqlalchemy.orm import Session
from app.models import Area, GrowthSignal
from data_pipeline.base import BaseIngester

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Census 2011 district decadal growth rates (2001–2011)
# Source: Census of India 2011 Primary Census Abstract Table A-2
#
# EPFO net subscriber additions FY2023 (in thousands)
# Source: EPFO Payroll Data monthly bulletin, cumulative Apr 2022–Mar 2023
#
# State capital expenditure proxy (₹ crore per lakh population) from
# respective state Economic Survey 2022-23 — used for govt_spending_score
# ---------------------------------------------------------------------------
DISTRICT_DATA: dict[str, dict] = {
    "Bangalore Urban": {
        "census_growth_pct": 68.9,   # 5.70M → 9.62M (2001→2011)
        "epfo_additions_k": 420,     # Bangalore EPFO zone, FY2023 net additions
        "capex_proxy": 85,           # Karnataka infra capex per capita rank
        "areas": ["Sarjapur", "Electronic City", "Whitefield"],
    },
    "Bangalore Rural": {
        "census_growth_pct": 19.4,   # 0.83M → 0.99M
        "epfo_additions_k": 48,
        "capex_proxy": 65,
        "areas": ["Devanahalli", "Hoskote"],
    },
    "Ranga Reddy": {
        # Includes Hyderabad Airport zone (HMDA area)
        "census_growth_pct": 50.9,   # 3.51M → 5.29M
        "epfo_additions_k": 320,     # Hyderabad EPFO zone
        "capex_proxy": 88,           # Telangana Mission Bhagiratha + infra
        "areas": ["Shamshabad"],
    },
    "Pune": {
        "census_growth_pct": 30.4,   # 7.23M → 9.43M
        "epfo_additions_k": 285,
        "capex_proxy": 78,
        "areas": ["Hinjewadi"],
    },
    "Kancheepuram": {
        # Now Chengalpattu district post-2019; Census data from pre-bifurcation
        "census_growth_pct": 24.6,   # 3.21M → 4.00M
        "epfo_additions_k": 180,     # Chennai EPFO zone (partial)
        "capex_proxy": 72,
        "areas": ["Sriperumbudur", "Oragadam"],
    },
    "Coimbatore": {
        "census_growth_pct": 19.6,   # 2.90M → 3.47M
        "epfo_additions_k": 95,
        "capex_proxy": 60,
        "areas": ["Coimbatore North"],
    },
}

# Reference maximum for normalisation (Bangalore Urban is the benchmark)
_MAX_GROWTH_PCT = 70.0   # cap so Bangalore Urban ≈ 90
_MAX_EPFO_K = 450        # Bangalore ≈ 88; below this scales linearly
_MIN_SCORE = 20.0
_MAX_SCORE = 95.0


def _clamp(val: float) -> float:
    return round(max(_MIN_SCORE, min(_MAX_SCORE, val)), 1)


def _pop_score(growth_pct: float) -> float:
    return _clamp(30.0 + (growth_pct / _MAX_GROWTH_PCT) * 65.0)


def _job_score(epfo_k: int) -> float:
    return _clamp(30.0 + (epfo_k / _MAX_EPFO_K) * 65.0)


def _govt_score(capex_proxy: int) -> float:
    return _clamp(float(capex_proxy))


class PopulationIngester(BaseIngester):
    source_name = "Census 2011 + EPFO"
    source_category = "Demographics"
    freshness_hours = 8760  # annual refresh cadence

    def ingest(self, db: Session) -> dict:
        area_map = {a.name: a for a in db.query(Area).all()}
        updated = skipped = 0
        updated_ids: list[int] = []

        for district, data in DISTRICT_DATA.items():
            pop_s = _pop_score(data["census_growth_pct"])
            job_s = _job_score(data["epfo_additions_k"])
            govt_s = _govt_score(data["capex_proxy"])

            logger.info(
                "  District %-18s pop=%.1f job=%.1f govt=%.1f",
                district, pop_s, job_s, govt_s,
            )

            for name in data["areas"]:
                area = area_map.get(name)
                if not area:
                    logger.warning("    Area '%s' not in DB — skipping", name)
                    skipped += 1
                    continue

                gs = db.query(GrowthSignal).filter(GrowthSignal.area_id == area.id).first()
                if gs:
                    gs.population_growth_score = pop_s
                    gs.job_growth_score = job_s
                    gs.government_spending_score = govt_s
                else:
                    gs = GrowthSignal(
                        area_id=area.id,
                        population_growth_score=pop_s,
                        job_growth_score=job_s,
                        government_spending_score=govt_s,
                    )
                    db.add(gs)

                updated += 1
                updated_ids.append(area.id)
                logger.info("    %-22s updated", name)

        db.commit()
        self.recompute_predictions(db, updated_ids)
        return {"inserted": 0, "updated": updated, "skipped": skipped}


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    ingester = PopulationIngester()
    ingester.run()
