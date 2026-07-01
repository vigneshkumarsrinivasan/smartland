"""
Section 2 — Backend integration tests.

Uses TestClient (synchronous) wired to an in-memory SQLite DB seeded via conftest.py.
Tests only the endpoints that are actually implemented:
  GET /health
  GET /areas/dump
  GET /areas (with filters)
  GET /areas/{id}/report
  GET /data-sources

Endpoints NOT tested here (not implemented in this phase — frontend-only features):
  POST /auth/*          — Auth deferred to Phase 5+
  POST /opportunities   — Opportunity Finder is frontend-side filtering only
  POST /compare         — Compare Areas is frontend-side only
  POST /watchlist/*     — Watchlist uses localStorage, no backend route
  POST /reports/*       — Reports deferred to Phase 5+
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

import pytest
from fastapi.testclient import TestClient

VALID_RECS = {"Strong Buy", "Buy", "Hold", "Avoid", "Sell"}
EXPECTED_AREA_NAMES = {
    "Sarjapur", "Devanahalli", "Electronic City", "Whitefield", "Hoskote",
    "Shamshabad", "Hinjewadi", "Sriperumbudur", "Oragadam", "Coimbatore North",
}
BANGALORE_AREAS = {"Sarjapur", "Devanahalli", "Electronic City", "Whitefield", "Hoskote"}


# ---------------------------------------------------------------------------
# GET /health
# ---------------------------------------------------------------------------

class TestHealth:

    def test_health_returns_200(self, test_app: TestClient):
        r = test_app.get("/health")
        assert r.status_code == 200

    def test_health_returns_ok_status(self, test_app: TestClient):
        body = test_app.get("/health").json()
        assert body.get("status") == "ok"

    def test_health_returns_json(self, test_app: TestClient):
        r = test_app.get("/health")
        assert "application/json" in r.headers["content-type"]


# ---------------------------------------------------------------------------
# GET /areas/dump  (Phase 1 gate endpoint)
# ---------------------------------------------------------------------------

class TestAreasDump:

    def test_dump_returns_200(self, test_app: TestClient):
        r = test_app.get("/areas/dump")
        assert r.status_code == 200

    def test_dump_returns_10_areas(self, test_app: TestClient):
        data = test_app.get("/areas/dump").json()
        assert len(data) == 10

    def test_dump_has_price_history(self, test_app: TestClient):
        data = test_app.get("/areas/dump").json()
        for item in data:
            assert "price_history" in item
            assert len(item["price_history"]) == 12


# ---------------------------------------------------------------------------
# GET /areas
# ---------------------------------------------------------------------------

class TestListAreas:

    def test_list_returns_200(self, test_app: TestClient):
        r = test_app.get("/areas")
        assert r.status_code == 200

    def test_list_returns_exactly_10_areas(self, test_app: TestClient):
        data = test_app.get("/areas").json()
        assert len(data) == 10

    def test_list_all_expected_area_names_present(self, test_app: TestClient):
        data = test_app.get("/areas").json()
        names = {a["name"] for a in data}
        assert names == EXPECTED_AREA_NAMES

    def test_list_required_fields_present(self, test_app: TestClient):
        data = test_app.get("/areas").json()
        required = {"id", "name", "city", "lat", "lng", "current_price_sqft",
                    "growth_score", "risk_score", "confidence_score",
                    "recommendation", "cagr_pct"}
        for item in data:
            missing = required - item.keys()
            assert not missing, f"Missing fields {missing} in area '{item.get('name')}'"

    def test_list_growth_scores_in_range(self, test_app: TestClient):
        data = test_app.get("/areas").json()
        for item in data:
            assert 0 <= item["growth_score"] <= 100, (
                f"{item['name']}: growth_score={item['growth_score']}"
            )

    def test_list_risk_scores_in_range(self, test_app: TestClient):
        data = test_app.get("/areas").json()
        for item in data:
            assert 0 <= item["risk_score"] <= 100, (
                f"{item['name']}: risk_score={item['risk_score']}"
            )

    def test_list_confidence_scores_in_range(self, test_app: TestClient):
        data = test_app.get("/areas").json()
        for item in data:
            assert 0 <= item["confidence_score"] <= 100

    def test_list_valid_recommendations(self, test_app: TestClient):
        data = test_app.get("/areas").json()
        for item in data:
            assert item["recommendation"] in VALID_RECS, (
                f"Invalid recommendation '{item['recommendation']}' for {item['name']}"
            )

    def test_list_no_null_core_fields(self, test_app: TestClient):
        data = test_app.get("/areas").json()
        must_not_be_null = ["id", "name", "city", "lat", "lng",
                            "current_price_sqft", "growth_score",
                            "risk_score", "confidence_score", "recommendation"]
        for item in data:
            for field in must_not_be_null:
                assert item[field] is not None, (
                    f"Field '{field}' is null for area '{item.get('name')}'"
                )


# ---------------------------------------------------------------------------
# GET /areas — filters
# ---------------------------------------------------------------------------

class TestAreasFilters:

    def test_city_filter_returns_only_bangalore(self, test_app: TestClient):
        data = test_app.get("/areas?city=Bangalore").json()
        assert len(data) == 5
        for item in data:
            assert item["city"] == "Bangalore"
            assert item["name"] in BANGALORE_AREAS

    def test_city_filter_nonexistent_returns_empty_not_404(self, test_app: TestClient):
        r = test_app.get("/areas?city=NonExistentCity")
        assert r.status_code == 200
        assert r.json() == []

    def test_min_growth_score_filter(self, test_app: TestClient):
        data = test_app.get("/areas?min_growth_score=70").json()
        for item in data:
            assert item["growth_score"] >= 70, (
                f"{item['name']} has growth_score={item['growth_score']} < 70"
            )

    def test_max_risk_score_filter(self, test_app: TestClient):
        data = test_app.get("/areas?max_risk_score=45").json()
        for item in data:
            assert item["risk_score"] <= 45, (
                f"{item['name']} has risk_score={item['risk_score']} > 45"
            )

    def test_recommendation_filter(self, test_app: TestClient):
        for rec in VALID_RECS:
            data = test_app.get(f"/areas?recommendation={rec}").json()
            for item in data:
                assert item["recommendation"] == rec

    def test_combined_city_and_growth_filter(self, test_app: TestClient):
        data = test_app.get("/areas?city=Bangalore&min_growth_score=60").json()
        for item in data:
            assert item["city"] == "Bangalore"
            assert item["growth_score"] >= 60

    def test_impossible_filter_returns_empty_not_500(self, test_app: TestClient):
        # min_growth_score=99 → no area can satisfy this with the seeded data
        r = test_app.get("/areas?min_growth_score=99")
        assert r.status_code == 200
        assert r.json() == []

    def test_hyderabad_filter(self, test_app: TestClient):
        data = test_app.get("/areas?city=Hyderabad").json()
        assert len(data) == 1
        assert data[0]["name"] == "Shamshabad"


# ---------------------------------------------------------------------------
# GET /areas/{id}/report
# ---------------------------------------------------------------------------

class TestAreaReport:

    def _get_first_area_id(self, test_app: TestClient) -> int:
        areas = test_app.get("/areas").json()
        return areas[0]["id"]

    def _get_sarjapur_id(self, test_app: TestClient) -> int:
        areas = test_app.get("/areas").json()
        for a in areas:
            if a["name"] == "Sarjapur":
                return a["id"]
        raise ValueError("Sarjapur not found")

    def test_valid_id_returns_200(self, test_app: TestClient):
        aid = self._get_first_area_id(test_app)
        r = test_app.get(f"/areas/{aid}/report")
        assert r.status_code == 200

    def test_invalid_id_returns_404(self, test_app: TestClient):
        r = test_app.get("/areas/99999/report")
        assert r.status_code == 404

    def test_report_top_level_keys(self, test_app: TestClient):
        aid = self._get_first_area_id(test_app)
        data = test_app.get(f"/areas/{aid}/report").json()
        required_keys = {"area", "price_history", "forecast", "growth_signals",
                         "risk_signals", "infrastructure_projects", "ai_summary"}
        missing = required_keys - data.keys()
        assert not missing, f"Missing top-level keys: {missing}"

    def test_area_summary_fields_in_report(self, test_app: TestClient):
        aid = self._get_first_area_id(test_app)
        area = test_app.get(f"/areas/{aid}/report").json()["area"]
        for field in ["id", "name", "city", "current_price_sqft",
                      "growth_score", "risk_score", "confidence_score", "recommendation"]:
            assert field in area, f"Missing field '{field}' in area summary"

    def test_forecast_has_three_scenarios(self, test_app: TestClient):
        aid = self._get_first_area_id(test_app)
        forecast = test_app.get(f"/areas/{aid}/report").json()["forecast"]
        assert "base" in forecast, "Missing 'base' forecast scenario"
        assert "optimistic" in forecast, "Missing 'optimistic' forecast scenario"
        assert "risk" in forecast, "Missing 'risk' forecast scenario (spec calls it 'risk')"

    def test_forecast_year_price_shape(self, test_app: TestClient):
        aid = self._get_first_area_id(test_app)
        forecast = test_app.get(f"/areas/{aid}/report").json()["forecast"]
        for scenario in ["base", "optimistic", "risk"]:
            entries = forecast[scenario]
            assert len(entries) >= 3, f"Scenario '{scenario}' has fewer than 3 data points"
            for entry in entries:
                assert "year" in entry and "price_sqft" in entry

    def test_forecast_years_ascending(self, test_app: TestClient):
        aid = self._get_first_area_id(test_app)
        forecast = test_app.get(f"/areas/{aid}/report").json()["forecast"]
        for scenario, entries in forecast.items():
            years = [e["year"] for e in entries]
            assert years == sorted(years), f"Scenario '{scenario}' years not ascending"

    def test_forecast_optimistic_above_base_above_risk(self, test_app: TestClient):
        """Optimistic prices > base prices > risk prices for every year (no crossover)."""
        aid = self._get_sarjapur_id(test_app)
        forecast = test_app.get(f"/areas/{aid}/report").json()["forecast"]
        base = {e["year"]: e["price_sqft"] for e in forecast["base"]}
        opt  = {e["year"]: e["price_sqft"] for e in forecast["optimistic"]}
        risk = {e["year"]: e["price_sqft"] for e in forecast["risk"]}
        for year in base:
            # Year 0 (anchor): all three scenarios start at the same current price
            if opt[year] == base[year] == risk[year]:
                continue
            assert opt[year] >= base[year], (
                f"Year {year}: optimistic={opt[year]} < base={base[year]}"
            )
            assert base[year] >= risk[year], (
                f"Year {year}: base={base[year]} < risk={risk[year]}"
            )

    def test_growth_signals_has_7_factors(self, test_app: TestClient):
        aid = self._get_first_area_id(test_app)
        gs = test_app.get(f"/areas/{aid}/report").json()["growth_signals"]
        expected_keys = {"infrastructure", "job_growth", "population_growth",
                         "commercial_activity", "transaction_velocity",
                         "land_scarcity", "government_spending"}
        assert set(gs.keys()) == expected_keys

    def test_risk_signals_has_7_factors(self, test_app: TestClient):
        aid = self._get_first_area_id(test_app)
        rs = test_app.get(f"/areas/{aid}/report").json()["risk_signals"]
        expected_keys = {"flood", "water", "legal", "overvaluation",
                         "pollution", "crime", "delay"}
        assert set(rs.keys()) == expected_keys

    def test_infrastructure_projects_ordered_by_year(self, test_app: TestClient):
        aid = self._get_first_area_id(test_app)
        projects = test_app.get(f"/areas/{aid}/report").json()["infrastructure_projects"]
        years = [p["target_year"] for p in projects if p["target_year"] is not None]
        assert years == sorted(years), "Infrastructure projects not ordered by target_year"

    def test_ai_summary_is_non_empty_string(self, test_app: TestClient):
        aid = self._get_first_area_id(test_app)
        summary = test_app.get(f"/areas/{aid}/report").json()["ai_summary"]
        assert isinstance(summary, str) and len(summary) > 10

    def test_ai_summary_contains_area_name(self, test_app: TestClient):
        aid = self._get_sarjapur_id(test_app)
        summary = test_app.get(f"/areas/{aid}/report").json()["ai_summary"]
        assert "Sarjapur" in summary

    def test_price_history_12_entries(self, test_app: TestClient):
        aid = self._get_first_area_id(test_app)
        history = test_app.get(f"/areas/{aid}/report").json()["price_history"]
        assert len(history) == 12

    def test_report_for_each_seeded_area(self, test_app: TestClient):
        """Every seeded area must return a valid 200 report."""
        areas = test_app.get("/areas").json()
        for area in areas:
            r = test_app.get(f"/areas/{area['id']}/report")
            assert r.status_code == 200, (
                f"Area '{area['name']}' (id={area['id']}) returned {r.status_code}"
            )


# ---------------------------------------------------------------------------
# GET /data-sources
# ---------------------------------------------------------------------------

class TestDataSources:

    def test_returns_200(self, test_app: TestClient):
        r = test_app.get("/data-sources")
        assert r.status_code == 200

    def test_returns_list(self, test_app: TestClient):
        data = test_app.get("/data-sources").json()
        assert isinstance(data, list)

    def test_returns_8_sources(self, test_app: TestClient):
        data = test_app.get("/data-sources").json()
        assert len(data) == 8, f"Expected 8 data sources, got {len(data)}"

    def test_required_fields(self, test_app: TestClient):
        data = test_app.get("/data-sources").json()
        for src in data:
            assert "id" in src
            assert "name" in src
            assert "category" in src
            assert "status" in src

    def test_all_known_sources_present(self, test_app: TestClient):
        data = test_app.get("/data-sources").json()
        names = {s["name"] for s in data}
        expected = {"CREDAI Price Registry", "NHAI Project Tracker", "BMRCL Metro Updates",
                    "Census 2011 + Projections", "MCA Company Registrations",
                    "RERA Filings", "IMD Flood Hazard Maps", "CPCB Pollution Index"}
        assert names == expected

    def test_status_values_are_valid(self, test_app: TestClient):
        data = test_app.get("/data-sources").json()
        valid_statuses = {"active", "degraded", "offline"}
        for src in data:
            assert src["status"] in valid_statuses, (
                f"Source '{src['name']}' has invalid status '{src['status']}'"
            )
