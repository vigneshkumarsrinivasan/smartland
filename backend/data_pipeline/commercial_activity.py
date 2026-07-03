"""
Commercial Activity Ingester — OpenStreetMap Overpass API

Source: OpenStreetMap via Overpass API (https://overpass-api.de)
Free tier: no API key required. Rate limit: max 10,000 requests/day.
One request per area centroid (10 areas = 10 requests total).

Query: count commercial nodes (shops, offices, restaurants, banks, supermarkets)
within a 5km radius of each area centroid. Maps count → commercial_activity_score (0–100).

Run standalone:
    python -m data_pipeline.commercial_activity
"""
import sys
import os
import time
import logging

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import requests
from sqlalchemy.orm import Session
from app.models import Area, GrowthSignal
from data_pipeline.base import BaseIngester

logger = logging.getLogger(__name__)

OVERPASS_URL = os.getenv("OVERPASS_URL", "https://overpass-api.de/api/interpreter")
RADIUS_M = 5000       # 5 km radius
REQUEST_TIMEOUT = 45  # seconds per request
POLITE_DELAY = 5.0    # seconds between requests (Overpass fair-use policy: avoid 429s)


def _build_query(lat: float, lng: float) -> str:
    return f"""[out:json][timeout:35];
(
  node["shop"](around:{RADIUS_M},{lat},{lng});
  node["amenity"~"^(restaurant|cafe|bank|fuel|pharmacy|supermarket|fast_food|hospital|school)$"]
      (around:{RADIUS_M},{lat},{lng});
  node["office"](around:{RADIUS_M},{lat},{lng});
  node["building"~"^(commercial|office|retail|supermarket)$"](around:{RADIUS_M},{lat},{lng});
);
out count;
"""


def _fetch_count(lat: float, lng: float) -> int:
    """Call Overpass API and return commercial node count. Raises on HTTP error."""
    resp = requests.post(
        OVERPASS_URL,
        data={"data": _build_query(lat, lng)},
        timeout=REQUEST_TIMEOUT + 10,
        headers={"User-Agent": "LandSignalAI-DataPipeline/1.0 (contact: pipeline@landsignal.ai)"},
    )
    resp.raise_for_status()
    data = resp.json()
    # Overpass count mode returns:
    # {"elements": [{"type": "count", "id": 0, "tags": {"nodes": "N", "total": "N"}}]}
    elements = data.get("elements", [])
    if elements:
        tags = elements[0].get("tags", {})
        return int(tags.get("total", tags.get("nodes", 0)))
    return 0


def _count_to_score(count: int) -> float:
    """Map commercial node count to 0–100 score."""
    # Calibrated against Indian metro areas:
    # Whitefield/Hinjewadi (dense IT corridor): ~1000+ nodes → 85+
    # Hoskote/Sriperumbudur (light industrial): ~50-150 nodes → 25-40
    if count <= 0:
        return 10.0
    if count <= 50:
        return 10.0 + (count / 50) * 20        # 10–30
    if count <= 200:
        return 30.0 + ((count - 50) / 150) * 20  # 30–50
    if count <= 500:
        return 50.0 + ((count - 200) / 300) * 20  # 50–70
    if count <= 1000:
        return 70.0 + ((count - 500) / 500) * 15  # 70–85
    return min(97.0, 85.0 + ((count - 1000) / 2000) * 12)


class CommercialActivityIngester(BaseIngester):
    source_name = "OpenStreetMap Overpass"
    source_category = "Commercial"
    freshness_hours = 168  # weekly — OSM data updates frequently but commercial patterns stable

    def ingest(self, db: Session) -> dict:
        areas = db.query(Area).all()
        inserted = updated = skipped = 0
        updated_ids: list[int] = []

        for i, area in enumerate(areas):
            try:
                count = _fetch_count(area.lat, area.lng)
                score = round(_count_to_score(count), 1)

                gs = db.query(GrowthSignal).filter(GrowthSignal.area_id == area.id).first()
                if gs:
                    gs.commercial_activity_score = score
                    updated += 1
                else:
                    db.add(GrowthSignal(area_id=area.id, commercial_activity_score=score))
                    inserted += 1

                db.commit()
                updated_ids.append(area.id)
                logger.info("  %-22s %5d nodes → score %.1f", area.name, count, score)

            except requests.exceptions.Timeout:
                logger.warning("  %-22s Overpass timeout — skipping", area.name)
                skipped += 1
            except requests.exceptions.RequestException as e:
                logger.warning("  %-22s Overpass error: %s — skipping", area.name, e)
                skipped += 1
            except Exception as e:
                logger.warning("  %-22s unexpected error: %s — skipping", area.name, e)
                skipped += 1

            # Polite delay between requests (not needed before the last request)
            if i < len(areas) - 1:
                time.sleep(POLITE_DELAY)

        self.recompute_predictions(db, updated_ids)
        return {"inserted": inserted, "updated": updated, "skipped": skipped}


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    ingester = CommercialActivityIngester()
    ingester.run()
