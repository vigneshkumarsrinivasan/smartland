"""
Section A — Data Pipeline tests.

Each test that calls ingester.ingest() gets a fresh in-memory SQLite DB
(pipeline_db fixture) so mutations don't bleed into the shared session DB
used by API tests.

Admin-endpoint tests reuse the shared test_app fixture since they only
test auth gating (no DB mutations that would conflict).
"""
import sys
import os
import json
from datetime import datetime
from unittest.mock import patch, MagicMock

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.database import Base
from app.models import (
    City, Area, GrowthSignal, RiskSignal, Prediction,
    DataSource, AreaPriceHistory, InfrastructureProject,
)

# ── Isolated pipeline DB ───────────────────────────────────────────────────────

AREA_SEED = [
    ("Sarjapur",        "Bangalore Urban",  12.8693, 77.7950, 6400),
    ("Devanahalli",     "Bangalore Rural",  13.2485, 77.7145, 4100),
    ("Electronic City", "Bangalore Urban",  12.8458, 77.6603, 5300),
    ("Whitefield",      "Bangalore Urban",  12.9698, 77.7499, 8100),
    ("Hoskote",         "Bangalore Rural",  13.0704, 77.7985, 2550),
    ("Shamshabad",      "Hyderabad",        17.2403, 78.4294, 4500),
    ("Hinjewadi",       "Pune",             18.5912, 73.7382, 7200),
    ("Sriperumbudur",   "Chennai",          12.9673, 79.9454, 2600),
    ("Oragadam",        "Chennai",          12.8342, 80.0557, 3400),
    ("Coimbatore North","Coimbatore",       11.0711, 77.0028, 3200),
]


def _build_pipeline_db():
    """Return a fresh seeded in-memory Session for pipeline tests."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    db = Session()

    city_cache: dict[str, City] = {}
    for name, city_name, lat, lng, price in AREA_SEED:
        if city_name not in city_cache:
            city = City(name=city_name, state="India", lat=lat, lng=lng)
            db.add(city)
            db.flush()
            city_cache[city_name] = city

        area = Area(
            name=name,
            city_id=city_cache[city_name].id,
            lat=lat, lng=lng,
            current_price_sqft=float(price),
            land_type="Residential",
        )
        db.add(area)
        db.flush()

        db.add(GrowthSignal(
            area_id=area.id,
            infrastructure_score=60.0, job_growth_score=60.0,
            population_growth_score=60.0, commercial_activity_score=60.0,
            transaction_velocity_score=60.0, land_scarcity_score=60.0,
            government_spending_score=60.0,
        ))
        db.add(RiskSignal(
            area_id=area.id,
            flood_risk=40.0, water_risk=40.0, legal_risk=40.0,
            overvaluation_risk=40.0, pollution_risk=40.0,
            crime_risk=40.0, delay_risk=40.0,
        ))
        db.add(Prediction(
            area_id=area.id,
            growth_score=65.0, risk_score=40.0,
            confidence_score=75.0, recommendation="Buy",
        ))

        # Minimal price history for LandTransactionsIngester idempotency tests
        for i, price_val in enumerate([5000, 5200, 5400, 5600]):
            from datetime import datetime as dt
            db.add(AreaPriceHistory(
                area_id=area.id,
                date=dt(2022 + i // 4, 1 + (i % 4) * 3, 1),
                price_sqft=float(price_val),
            ))

    db.commit()
    return db


@pytest.fixture
def pipeline_db():
    db = _build_pipeline_db()
    yield db
    db.close()


# ── Pure function: _count_to_score ────────────────────────────────────────────

from data_pipeline.commercial_activity import _count_to_score


def test_count_to_score_zero():
    assert _count_to_score(0) == 10.0


def test_count_to_score_50():
    score = _count_to_score(50)
    assert 29.9 < score <= 30.1


def test_count_to_score_200():
    score = _count_to_score(200)
    assert 49.9 < score <= 50.1


def test_count_to_score_500():
    score = _count_to_score(500)
    assert 69.9 < score <= 70.1


def test_count_to_score_1000():
    score = _count_to_score(1000)
    assert 84.9 < score <= 85.1


def test_count_to_score_above_1000():
    score = _count_to_score(2000)
    assert 85.0 < score <= 97.0


def test_count_to_score_monotone():
    counts = [0, 25, 50, 100, 200, 400, 500, 750, 1000, 2000]
    scores = [_count_to_score(c) for c in counts]
    assert scores == sorted(scores)


# ── Pure function: _infra_to_score ────────────────────────────────────────────

from data_pipeline.infrastructure import _infra_to_score


def test_infra_to_score_completed_single():
    projs = [{"impact_score": 9.0, "status": "Completed"}]
    score = _infra_to_score(projs)
    assert score == round(min(99.0, max(10.0, 9.0 * 1.0 / 0.24)), 1)


def test_infra_to_score_announced_less_than_completed():
    completed = [{"impact_score": 9.0, "status": "Completed"}]
    announced = [{"impact_score": 9.0, "status": "Announced"}]
    assert _infra_to_score(completed) > _infra_to_score(announced)


def test_infra_to_score_floor_10():
    assert _infra_to_score([]) == 10.0


def test_infra_to_score_cap_99():
    many = [{"impact_score": 10.0, "status": "Completed"}] * 50
    assert _infra_to_score(many) == 99.0


def test_infra_to_score_unknown_status_uses_04():
    projs = [{"impact_score": 6.0, "status": "Unknown"}]
    expected = round(min(99.0, max(10.0, 6.0 * 0.4 / 0.24)), 1)
    assert _infra_to_score(projs) == expected


# ── Pure function: _velocity_score / _scarcity_score ─────────────────────────

from data_pipeline.land_transactions import _velocity_score, _scarcity_score


def test_velocity_score_zero():
    assert _velocity_score(0) == 20.0


def test_velocity_score_high():
    score = _velocity_score(270)
    assert score == 95.0


def test_velocity_score_caps_at_95():
    assert _velocity_score(10_000) == 95.0


def test_velocity_score_monotone():
    vals = [_velocity_score(x) for x in [0, 50, 100, 200, 270, 500]]
    assert all(vals[i] <= vals[i + 1] for i in range(len(vals) - 1))


def test_scarcity_score_high_growth_low_txns():
    score = _scarcity_score(50.0, 10)
    assert score > 50.0


def test_scarcity_score_low_growth_high_txns():
    score = _scarcity_score(5.0, 250)
    assert score < 50.0


def test_scarcity_score_floor_20():
    assert _scarcity_score(0, 1000) >= 20.0


def test_scarcity_score_cap_95():
    assert _scarcity_score(100, 0) <= 95.0


# ── Pure function: _pop_score / _job_score / _govt_score ─────────────────────

from data_pipeline.population import _pop_score, _job_score, _govt_score


def test_pop_score_bangalore_urban():
    score = _pop_score(68.9)
    assert 20.0 <= score <= 95.0
    assert score > 80.0  # high growth → high score


def test_pop_score_low_growth():
    score = _pop_score(5.0)
    assert 20.0 <= score <= 95.0
    assert score < 40.0


def test_pop_score_clamped():
    # formula: _clamp(30.0 + 0 * 65) = 30.0 (floor is 30, not 20)
    assert _pop_score(0) == 30.0
    assert _pop_score(1000) == 95.0


def test_job_score_high_epfo():
    score = _job_score(420)
    assert 20.0 <= score <= 95.0
    assert score > 75.0


def test_job_score_low_epfo():
    score = _job_score(10)
    assert 20.0 <= score <= 95.0
    assert score < 35.0


def test_govt_score_clamped_at_95():
    assert _govt_score(100) == 95.0


def test_govt_score_clamped_at_20():
    assert _govt_score(0) == 20.0


def test_govt_score_mid():
    score = _govt_score(75)
    assert score == 75.0


# ── FloodRiskIngester ─────────────────────────────────────────────────────────

from data_pipeline.flood_risk import FloodRiskIngester, FLOOD_RISK_DATA


def test_flood_risk_ingest_result_shape(pipeline_db):
    ingester = FloodRiskIngester()
    result = ingester.ingest(pipeline_db)
    assert "inserted" in result
    assert "updated" in result
    assert "skipped" in result
    assert result["inserted"] == 0  # always updates existing rows


def test_flood_risk_updates_known_areas(pipeline_db):
    ingester = FloodRiskIngester()
    result = ingester.ingest(pipeline_db)
    assert result["updated"] == len(FLOOD_RISK_DATA)


def test_flood_risk_scores_written_to_db(pipeline_db):
    FloodRiskIngester().ingest(pipeline_db)
    areas = pipeline_db.query(Area).filter(Area.name == "Hoskote").all()
    area = areas[0]
    rs = pipeline_db.query(RiskSignal).filter(RiskSignal.area_id == area.id).first()
    assert rs.flood_risk == 75.0


def test_flood_risk_scores_in_range(pipeline_db):
    FloodRiskIngester().ingest(pipeline_db)
    for rs in pipeline_db.query(RiskSignal).all():
        if rs.flood_risk is not None:
            assert 0.0 <= rs.flood_risk <= 100.0


def test_flood_risk_idempotent(pipeline_db):
    ingester = FloodRiskIngester()
    r1 = ingester.ingest(pipeline_db)
    r2 = ingester.ingest(pipeline_db)
    assert r1["updated"] == r2["updated"]
    # Scores should be unchanged after second run
    area = pipeline_db.query(Area).filter(Area.name == "Devanahalli").first()
    rs = pipeline_db.query(RiskSignal).filter(RiskSignal.area_id == area.id).first()
    assert rs.flood_risk == FLOOD_RISK_DATA["Devanahalli"]["flood_risk"]


# ── PopulationIngester ────────────────────────────────────────────────────────

from data_pipeline.population import PopulationIngester, DISTRICT_DATA


def test_population_ingest_result_shape(pipeline_db):
    ingester = PopulationIngester()
    result = ingester.ingest(pipeline_db)
    assert result["inserted"] == 0
    assert "updated" in result
    assert "skipped" in result


def test_population_updates_all_areas(pipeline_db):
    ingester = PopulationIngester()
    result = ingester.ingest(pipeline_db)
    expected = sum(len(d["areas"]) for d in DISTRICT_DATA.values())
    assert result["updated"] == expected


def test_population_scores_in_range(pipeline_db):
    PopulationIngester().ingest(pipeline_db)
    for gs in pipeline_db.query(GrowthSignal).all():
        for val in [gs.population_growth_score, gs.job_growth_score, gs.government_spending_score]:
            if val is not None:
                assert 20.0 <= val <= 95.0


def test_population_idempotent(pipeline_db):
    ingester = PopulationIngester()
    r1 = ingester.ingest(pipeline_db)
    r2 = ingester.ingest(pipeline_db)
    assert r1["updated"] == r2["updated"]


# ── InfrastructureIngester ────────────────────────────────────────────────────

from data_pipeline.infrastructure import InfrastructureIngester, INFRA_PROJECTS


def test_infra_ingest_first_run_inserts(pipeline_db):
    ingester = InfrastructureIngester()
    result = ingester.ingest(pipeline_db)
    assert result["inserted"] > 0
    assert result["inserted"] == len(INFRA_PROJECTS)


def test_infra_projects_have_source_url(pipeline_db):
    InfrastructureIngester().ingest(pipeline_db)
    projs = pipeline_db.query(InfrastructureProject).all()
    for p in projs:
        assert p.source_url, f"Missing source_url on project {p.name}"
        assert p.data_source, f"Missing data_source on project {p.name}"


def test_infra_idempotent_second_run_updates(pipeline_db):
    ingester = InfrastructureIngester()
    r1 = ingester.ingest(pipeline_db)
    r2 = ingester.ingest(pipeline_db)
    # Second run: all rows already exist → inserted=0, updated=N
    assert r2["inserted"] == 0
    assert r2["updated"] == r1["inserted"]


def test_infra_updates_growth_signal(pipeline_db):
    InfrastructureIngester().ingest(pipeline_db)
    area = pipeline_db.query(Area).filter(Area.name == "Devanahalli").first()
    gs = pipeline_db.query(GrowthSignal).filter(GrowthSignal.area_id == area.id).first()
    # Devanahalli has 4 high-impact projects, expect a high score
    assert gs.infrastructure_score is not None
    assert gs.infrastructure_score > 50.0


# ── CommercialActivityIngester ────────────────────────────────────────────────

from data_pipeline.commercial_activity import CommercialActivityIngester


def test_commercial_activity_mocked_success(pipeline_db):
    mock_resp = MagicMock()
    mock_resp.raise_for_status = MagicMock()
    mock_resp.json.return_value = {
        "elements": [{"type": "count", "id": 0, "tags": {"total": "300", "nodes": "300"}}]
    }
    with patch("data_pipeline.commercial_activity.requests.post", return_value=mock_resp):
        with patch("data_pipeline.commercial_activity.time.sleep"):
            ingester = CommercialActivityIngester()
            result = ingester.ingest(pipeline_db)

    assert result["updated"] + result["inserted"] == 10
    assert result["skipped"] == 0


def test_commercial_activity_timeout_skips(pipeline_db):
    import requests as req
    def raise_timeout(*args, **kwargs):
        raise req.exceptions.Timeout("timeout")

    with patch("data_pipeline.commercial_activity.requests.post", side_effect=raise_timeout):
        with patch("data_pipeline.commercial_activity.time.sleep"):
            ingester = CommercialActivityIngester()
            result = ingester.ingest(pipeline_db)

    assert result["skipped"] == 10
    assert result["updated"] + result["inserted"] == 0


def test_commercial_activity_score_mapped_correctly(pipeline_db):
    mock_resp = MagicMock()
    mock_resp.raise_for_status = MagicMock()
    mock_resp.json.return_value = {
        "elements": [{"type": "count", "id": 0, "tags": {"total": "1000"}}]
    }
    with patch("data_pipeline.commercial_activity.requests.post", return_value=mock_resp):
        with patch("data_pipeline.commercial_activity.time.sleep"):
            CommercialActivityIngester().ingest(pipeline_db)

    gs = pipeline_db.query(GrowthSignal).first()
    assert gs.commercial_activity_score == 85.0


# ── DataSource tracking ───────────────────────────────────────────────────────

def test_data_source_upsert_on_success(pipeline_db):
    ingester = FloodRiskIngester()
    # _upsert_data_source is called by run(); test it directly here
    ingester._upsert_data_source(pipeline_db, "active")
    ds = pipeline_db.query(DataSource).filter(
        DataSource.name == "NDMA Flood Hazard Atlas"
    ).first()
    assert ds is not None
    assert ds.status == "active"
    assert ds.last_run_at is not None


def test_data_source_degraded_on_failure(pipeline_db):
    ingester = FloodRiskIngester()
    with patch.object(ingester, "ingest", side_effect=RuntimeError("boom")):
        result = ingester.run()
    assert result["status"] == "error"
    assert "error" in result


# ── BaseIngester.run() return shape ───────────────────────────────────────────

def test_run_result_keys():
    ingester = FloodRiskIngester()
    with patch.object(ingester, "ingest", return_value={"inserted": 0, "updated": 5, "skipped": 0}):
        with patch("app.database.upgrade_db"):
            with patch("data_pipeline.base.SessionLocal") as mock_sl:
                mock_db = _build_pipeline_db()
                mock_sl.return_value = mock_db
                result = ingester.run()

    for key in ("source", "status", "inserted", "updated", "skipped", "timestamp"):
        assert key in result, f"Missing key: {key}"


def test_run_result_status_ok_on_success():
    ingester = PopulationIngester()
    with patch.object(ingester, "ingest", return_value={"inserted": 0, "updated": 10, "skipped": 0}):
        with patch("app.database.upgrade_db"):
            with patch("data_pipeline.base.SessionLocal") as mock_sl:
                mock_sl.return_value = _build_pipeline_db()
                result = ingester.run()
    assert result["status"] == "ok"


def test_run_result_status_error_on_exception():
    ingester = PopulationIngester()
    with patch.object(ingester, "ingest", side_effect=ValueError("bad")):
        with patch("app.database.upgrade_db"):
            with patch("data_pipeline.base.SessionLocal") as mock_sl:
                mock_sl.return_value = _build_pipeline_db()
                result = ingester.run()
    assert result["status"] == "error"
    assert "error" in result


def test_run_source_name_in_result():
    ingester = FloodRiskIngester()
    with patch.object(ingester, "ingest", return_value={"inserted": 0, "updated": 1, "skipped": 0}):
        with patch("app.database.upgrade_db"):
            with patch("data_pipeline.base.SessionLocal") as mock_sl:
                mock_sl.return_value = _build_pipeline_db()
                result = ingester.run()
    assert result["source"] == "NDMA Flood Hazard Atlas"


# ── Admin endpoint auth ───────────────────────────────────────────────────────

def test_admin_pipeline_wrong_key_returns_401(test_app):
    import os
    original = os.environ.get("ADMIN_API_KEY")
    os.environ["ADMIN_API_KEY"] = "secret-key"
    try:
        # Need to reload the admin module's key — patch the check instead
        from app.routers import admin as admin_mod
        original_key = admin_mod._ADMIN_KEY
        admin_mod._ADMIN_KEY = "secret-key"
        resp = test_app.post(
            "/admin/pipeline/run",
            headers={"X-Admin-Key": "wrong-key"},
        )
        assert resp.status_code == 401
    finally:
        admin_mod._ADMIN_KEY = original_key
        if original is None:
            os.environ.pop("ADMIN_API_KEY", None)
        else:
            os.environ["ADMIN_API_KEY"] = original


def test_admin_pipeline_no_key_dev_bypass(test_app):
    from app.routers import admin as admin_mod
    original_key = admin_mod._ADMIN_KEY
    admin_mod._ADMIN_KEY = ""  # dev mode — bypass
    _mock_result = {
        "source": "mock", "status": "ok",
        "inserted": 0, "updated": 1, "skipped": 0,
        "timestamp": datetime.utcnow().isoformat(),
    }
    try:
        # Patch ingesters at source module so local imports in run_pipeline() get mocks
        with patch("data_pipeline.flood_risk.FloodRiskIngester") as m1, \
             patch("data_pipeline.population.PopulationIngester") as m2, \
             patch("data_pipeline.infrastructure.InfrastructureIngester") as m3, \
             patch("data_pipeline.land_transactions.LandTransactionsIngester") as m4, \
             patch("data_pipeline.commercial_activity.CommercialActivityIngester") as m5:
            for mock_cls in (m1, m2, m3, m4, m5):
                mock_cls.return_value.run.return_value = _mock_result
            resp = test_app.post("/admin/pipeline/run")
        assert resp.status_code == 200
        assert resp.json()["overall_status"] == "ok"
    finally:
        admin_mod._ADMIN_KEY = original_key


# ── Scoring integration: scores differ between areas ─────────────────────────

def test_scoring_differentiated(db_session):
    preds = db_session.query(Prediction).all()
    scores = [p.growth_score for p in preds]
    assert len(set(scores)) > 1, "All areas must not have identical growth scores"


def test_scores_in_valid_range(db_session):
    for pred in db_session.query(Prediction).all():
        assert 0 <= pred.growth_score <= 100
        assert 0 <= pred.risk_score <= 100
        assert 0 <= pred.confidence_score <= 100


def test_recommendations_are_valid(db_session):
    valid = {"Strong Buy", "Buy", "Hold", "Avoid", "Sell"}
    for pred in db_session.query(Prediction).all():
        assert pred.recommendation in valid
