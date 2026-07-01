"""
Section 1B — Data model / schema unit tests.

Tests run against the in-memory seeded test DB from conftest.py.
Validates structural invariants: coordinates, price ordering, target years, seeding counts.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

import pytest
from sqlalchemy.orm import Session
from app.models import Area, AreaPriceHistory, InfrastructureProject, Prediction


# Indian mainland bounding box (conservative, covers all 5 seeded cities)
INDIA_LAT_MIN, INDIA_LAT_MAX = 8.0, 37.0
INDIA_LNG_MIN, INDIA_LNG_MAX = 68.0, 97.0

VALID_RECS = {"Strong Buy", "Buy", "Hold", "Avoid", "Sell"}


class TestSeedCounts:

    def test_exactly_10_areas_seeded(self, db_session: Session):
        count = db_session.query(Area).count()
        assert count == 10, f"Expected 10 areas, got {count}"

    def test_price_history_count(self, db_session: Session):
        # 10 areas × 12 quarters each = 120 rows
        count = db_session.query(AreaPriceHistory).count()
        assert count == 120, f"Expected 120 price history rows, got {count}"

    def test_infrastructure_project_count(self, db_session: Session):
        # 32 projects across 10 areas (per CLAUDE.md)
        count = db_session.query(InfrastructureProject).count()
        assert count == 32, f"Expected 32 infra projects, got {count}"

    def test_all_areas_have_predictions(self, db_session: Session):
        areas = db_session.query(Area).all()
        for area in areas:
            pred = (
                db_session.query(Prediction)
                .filter(Prediction.area_id == area.id)
                .first()
            )
            assert pred is not None, f"Area '{area.name}' has no prediction"

    def test_all_areas_have_non_null_growth_score(self, db_session: Session):
        for pred in db_session.query(Prediction).all():
            assert pred.growth_score is not None
            assert pred.risk_score is not None
            assert pred.confidence_score is not None
            assert pred.recommendation is not None

    def test_all_recommendations_are_valid(self, db_session: Session):
        for pred in db_session.query(Prediction).all():
            assert pred.recommendation in VALID_RECS, (
                f"Invalid recommendation '{pred.recommendation}'"
            )


class TestCoordinates:

    def test_all_area_lats_within_india(self, db_session: Session):
        areas = db_session.query(Area).all()
        for area in areas:
            assert INDIA_LAT_MIN <= area.lat <= INDIA_LAT_MAX, (
                f"{area.name}: lat={area.lat} out of Indian bounds"
            )

    def test_all_area_lngs_within_india(self, db_session: Session):
        areas = db_session.query(Area).all()
        for area in areas:
            assert INDIA_LNG_MIN <= area.lng <= INDIA_LNG_MAX, (
                f"{area.name}: lng={area.lng} out of Indian bounds"
            )

    def test_no_null_coordinates(self, db_session: Session):
        areas = db_session.query(Area).all()
        for area in areas:
            assert area.lat is not None
            assert area.lng is not None


class TestPriceHistory:

    def test_price_history_no_negative_prices(self, db_session: Session):
        rows = db_session.query(AreaPriceHistory).all()
        for row in rows:
            assert row.price_sqft > 0, (
                f"Non-positive price {row.price_sqft} for area_id={row.area_id}"
            )

    def test_price_history_ordered_ascending_per_area(self, db_session: Session):
        areas = db_session.query(Area).all()
        for area in areas:
            history = (
                db_session.query(AreaPriceHistory)
                .filter(AreaPriceHistory.area_id == area.id)
                .order_by(AreaPriceHistory.date)
                .all()
            )
            dates = [h.date for h in history]
            assert dates == sorted(dates), (
                f"{area.name}: price history dates not ascending"
            )

    def test_price_history_12_quarters_per_area(self, db_session: Session):
        areas = db_session.query(Area).all()
        for area in areas:
            count = (
                db_session.query(AreaPriceHistory)
                .filter(AreaPriceHistory.area_id == area.id)
                .count()
            )
            assert count == 12, (
                f"{area.name}: expected 12 quarters, got {count}"
            )

    def test_price_history_prices_increase_over_time(self, db_session: Session):
        """All 10 seeded areas have upward price trajectories."""
        areas = db_session.query(Area).all()
        for area in areas:
            history = (
                db_session.query(AreaPriceHistory)
                .filter(AreaPriceHistory.area_id == area.id)
                .order_by(AreaPriceHistory.date)
                .all()
            )
            first_price = history[0].price_sqft
            last_price = history[-1].price_sqft
            assert last_price > first_price, (
                f"{area.name}: last price {last_price} not greater than first {first_price}"
            )


class TestInfrastructureProjects:

    def test_all_projects_have_known_area(self, db_session: Session):
        area_ids = {a.id for a in db_session.query(Area).all()}
        projects = db_session.query(InfrastructureProject).all()
        for proj in projects:
            assert proj.area_id in area_ids, (
                f"Project '{proj.name}' references unknown area_id={proj.area_id}"
            )

    def test_target_years_in_valid_range(self, db_session: Session):
        """
        Completed projects may have target_year as early as 2023 (e.g. Whitefield Metro,
        Sarjapur Road Widening). Future projects go up to 2029. We allow 2020–2035.
        """
        projects = db_session.query(InfrastructureProject).all()
        for proj in projects:
            if proj.target_year is not None:
                assert 2020 <= proj.target_year <= 2035, (
                    f"Project '{proj.name}' has target_year={proj.target_year} "
                    "outside 2020–2035"
                )

    def test_all_projects_have_name_type_status(self, db_session: Session):
        projects = db_session.query(InfrastructureProject).all()
        for proj in projects:
            assert proj.name and len(proj.name) > 0
            assert proj.type and len(proj.type) > 0
            assert proj.status and len(proj.status) > 0

    def test_minimum_projects_per_area(self, db_session: Session):
        """Each area has at least 2 infrastructure projects (per CLAUDE.md)."""
        areas = db_session.query(Area).all()
        for area in areas:
            count = (
                db_session.query(InfrastructureProject)
                .filter(InfrastructureProject.area_id == area.id)
                .count()
            )
            assert count >= 2, (
                f"{area.name}: only {count} infra project(s), expected ≥ 2"
            )


class TestScoreRanges:

    def test_growth_scores_in_0_100(self, db_session: Session):
        for pred in db_session.query(Prediction).all():
            assert 0 <= pred.growth_score <= 100, (
                f"growth_score={pred.growth_score} out of range"
            )

    def test_risk_scores_in_0_100(self, db_session: Session):
        for pred in db_session.query(Prediction).all():
            assert 0 <= pred.risk_score <= 100, (
                f"risk_score={pred.risk_score} out of range"
            )

    def test_confidence_scores_in_0_100(self, db_session: Session):
        for pred in db_session.query(Prediction).all():
            assert 0 <= pred.confidence_score <= 100, (
                f"confidence_score={pred.confidence_score} out of range"
            )
