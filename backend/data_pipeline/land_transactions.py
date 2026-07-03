"""
Land Transactions Ingester — RERA State Registry CSV Exports

Sources:
  - RERA Karnataka: https://rera.karnataka.gov.in
  - MahaRERA: https://maharera.maharashtra.gov.in
  - RERA Tamil Nadu: https://www.tnrera.in
  - RERA Telangana: https://rera.telangana.gov.in

Direct programmatic API access is not available from these portals.
Ingest from CSV exports downloaded from each RERA portal.
Default CSV location: data_pipeline/data/land_transactions.csv

CSV schema:
    area_name, date (YYYY-MM-DD), price_sqft, transaction_count, source

What it updates:
  - AreaPriceHistory — upserts quarterly price rows
  - GrowthSignal.transaction_velocity_score — derived from transaction count trend
  - GrowthSignal.land_scarcity_score — derived from price momentum vs. transaction volume

To replace with a live scraper:
  Override the _load_rows() method and return the same list-of-dicts format.

Run standalone:
    python -m data_pipeline.land_transactions
"""
import sys
import os
import csv
import logging
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from sqlalchemy.orm import Session
from app.models import Area, AreaPriceHistory, GrowthSignal
from data_pipeline.base import BaseIngester

logger = logging.getLogger(__name__)

CSV_PATH = os.path.join(os.path.dirname(__file__), "data", "land_transactions.csv")

# Transaction count → velocity score mapping (0–100)
# A very active market (250+ txns/quarter) → 95
# A thin market (< 50 txns/quarter) → 20
def _velocity_score(avg_txns: float) -> float:
    if avg_txns <= 0:
        return 20.0
    score = 20.0 + (avg_txns / 270) * 75
    return round(min(95.0, max(20.0, score)), 1)


def _scarcity_score(price_growth_pct: float, avg_txns: float) -> float:
    """
    High price growth + falling transactions → high scarcity premium.
    High price growth + rising transactions → moderate scarcity.
    """
    growth_factor = min(price_growth_pct / 60, 1.0)  # normalise to 60% max CAGR
    txn_factor = max(0.3, 1.0 - avg_txns / 300)       # fewer txns → higher scarcity
    score = 20.0 + growth_factor * 50 + txn_factor * 25
    return round(min(95.0, max(20.0, score)), 1)


class LandTransactionsIngester(BaseIngester):
    source_name = "RERA Land Registry"
    source_category = "Transaction"
    freshness_hours = 24  # daily for live feeds

    def _load_rows(self) -> list[dict]:
        rows = []
        with open(CSV_PATH, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                rows.append(row)
        logger.info("Loaded %d rows from %s", len(rows), CSV_PATH)
        return rows

    def ingest(self, db: Session) -> dict:
        rows = self._load_rows()
        area_map = {a.name: a for a in db.query(Area).all()}

        # Group by area for velocity/scarcity computation
        area_rows: dict[str, list[dict]] = {}
        for row in rows:
            area_rows.setdefault(row["area_name"], []).append(row)

        inserted = updated = skipped = 0
        updated_ids: list[int] = []

        for area_name, a_rows in area_rows.items():
            area = area_map.get(area_name)
            if not area:
                logger.warning("Area '%s' not in DB — skipping %d rows", area_name, len(a_rows))
                skipped += len(a_rows)
                continue

            # Upsert price history rows
            prices = []
            for row in a_rows:
                try:
                    dt = datetime.strptime(row["date"], "%Y-%m-%d")
                    price = float(row["price_sqft"])
                    txns = int(row["transaction_count"])
                    prices.append((dt, price, txns))
                except (ValueError, KeyError) as e:
                    logger.warning("  Bad row for %s: %s", area_name, e)
                    skipped += 1
                    continue

                existing = (
                    db.query(AreaPriceHistory)
                    .filter(
                        AreaPriceHistory.area_id == area.id,
                        AreaPriceHistory.date == dt,
                    )
                    .first()
                )
                if existing:
                    existing.price_sqft = price
                    updated += 1
                else:
                    db.add(AreaPriceHistory(area_id=area.id, date=dt, price_sqft=price))
                    inserted += 1

            db.commit()

            # Compute velocity and scarcity scores from transaction trends
            if len(prices) >= 4:
                prices_sorted = sorted(prices, key=lambda x: x[0])
                txns_all = [t for _, _, t in prices_sorted]
                avg_txns = sum(txns_all) / len(txns_all)

                # Price CAGR
                p0 = prices_sorted[0][1]
                p1 = prices_sorted[-1][1]
                years = (prices_sorted[-1][0] - prices_sorted[0][0]).days / 365.25
                cagr_pct = ((p1 / p0) ** (1 / years) - 1) * 100 if years > 0 else 0

                vel_s = _velocity_score(avg_txns)
                scar_s = _scarcity_score(cagr_pct, avg_txns)

                gs = db.query(GrowthSignal).filter(GrowthSignal.area_id == area.id).first()
                if gs:
                    gs.transaction_velocity_score = vel_s
                    gs.land_scarcity_score = scar_s
                else:
                    db.add(GrowthSignal(
                        area_id=area.id,
                        transaction_velocity_score=vel_s,
                        land_scarcity_score=scar_s,
                    ))
                logger.info(
                    "  %-22s cagr=%.1f%% avg_txns=%.0f vel=%.1f scar=%.1f",
                    area_name, cagr_pct, avg_txns, vel_s, scar_s,
                )
                updated_ids.append(area.id)

        db.commit()
        self.recompute_predictions(db, updated_ids)
        return {"inserted": inserted, "updated": updated, "skipped": skipped}


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    ingester = LandTransactionsIngester()
    ingester.run()
