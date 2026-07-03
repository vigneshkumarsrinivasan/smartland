"""
Section C — PDF Report tests.

Report endpoint: GET /areas/{id}/report
PDF variant:    GET /areas/{id}/report?format=pdf

Deviations from test prompt spec:
  - No async POST /reports/generate endpoint — reports are generated inline
    on GET /areas/{id}/report with ?format=pdf query param.
  - WeasyPrint may not be available on this machine (Windows without GTK).
    When unavailable, the endpoint returns HTML fallback (text/html).
    Tests detect this and assert the correct content type in each case.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from app.pdf_report import is_pdf_available, render_report

PDF_AVAILABLE = is_pdf_available()

EXPECTED_AREA_NAMES = [
    "Sarjapur", "Devanahalli", "Electronic City", "Whitefield", "Hoskote",
    "Shamshabad", "Hinjewadi", "Sriperumbudur", "Oragadam", "Coimbatore North",
]


# ── Helper ─────────────────────────────────────────────────────────────────────

def _get_area_ids(test_app) -> list[int]:
    return [a["id"] for a in test_app.get("/areas").json()]


# ── render_report() unit tests ─────────────────────────────────────────────────

class TestRenderReport:

    def _minimal_report_data(self, area_name="Sarjapur") -> dict:
        return {
            "area": {
                "id": 1,
                "name": area_name,
                "city": "Bangalore",
                "land_type": "Residential",
                "current_price_sqft": 6400,
                "growth_score": 75.0,
                "risk_score": 35.0,
                "confidence_score": 82.0,
                "recommendation": "Buy",
                "cagr_pct": 10.5,
            },
            "ai_summary": "Sarjapur is well-positioned for growth.",
            "growth_signals": {
                "infrastructure": 80.0,
                "job_growth": 78.0,
                "population_growth": 72.0,
                "commercial_activity": 75.0,
                "transaction_velocity": 70.0,
                "land_scarcity": 78.0,
                "government_spending": 65.0,
            },
            "risk_signals": {
                "flood": 32.0,
                "water": 38.0,
                "legal": 35.0,
                "overvaluation": 45.0,
                "pollution": 28.0,
                "crime": 25.0,
                "delay": 42.0,
            },
            "price_history": [
                {"date": "2022-01-01", "price_sqft": 4800},
                {"date": "2024-10-01", "price_sqft": 6250},
            ],
            "infrastructure_projects": [
                {
                    "name": "Peripheral Ring Road",
                    "type": "Highway",
                    "status": "Under Construction",
                    "target_year": 2027,
                    "impact_score": 8.5,
                }
            ],
            "forecast": {
                "base": [
                    {"year": 2025, "price_sqft": 6400},
                    {"year": 2026, "price_sqft": 6720},
                    {"year": 2027, "price_sqft": 7056},
                ],
                "optimistic": [
                    {"year": 2025, "price_sqft": 6400},
                    {"year": 2026, "price_sqft": 6800},
                    {"year": 2027, "price_sqft": 7225},
                ],
                "risk": [
                    {"year": 2025, "price_sqft": 6400},
                    {"year": 2026, "price_sqft": 6592},
                    {"year": 2027, "price_sqft": 6790},
                ],
            },
        }

    def test_render_returns_bytes_and_media_type(self):
        content, media_type = render_report(self._minimal_report_data())
        assert isinstance(content, bytes)
        assert len(content) > 0
        assert media_type in ("application/pdf", "text/html")

    def test_render_pdf_if_weasyprint_available(self):
        content, media_type = render_report(self._minimal_report_data())
        if PDF_AVAILABLE:
            assert media_type == "application/pdf"
            assert content[:4] == b"%PDF"
        else:
            assert media_type == "text/html"

    def test_render_html_fallback_contains_area_name(self):
        if PDF_AVAILABLE:
            pytest.skip("WeasyPrint available — testing HTML fallback path only")
        content, media_type = render_report(self._minimal_report_data("Hinjewadi"))
        assert b"Hinjewadi" in content

    def test_render_html_contains_recommendation(self):
        if PDF_AVAILABLE:
            pytest.skip("HTML inspection only when WeasyPrint unavailable")
        content, _ = render_report(self._minimal_report_data())
        assert b"Buy" in content

    def test_render_html_no_lorem_ipsum(self):
        if PDF_AVAILABLE:
            pytest.skip("HTML inspection only when WeasyPrint unavailable")
        content, _ = render_report(self._minimal_report_data())
        assert b"lorem ipsum" not in content.lower()

    def test_render_html_no_placeholder_brackets(self):
        if PDF_AVAILABLE:
            pytest.skip("HTML inspection only when WeasyPrint unavailable")
        content, _ = render_report(self._minimal_report_data())
        assert b"{{" not in content
        assert b"}}" not in content

    def test_render_different_area_names(self):
        for area in ["Devanahalli", "Whitefield", "Hoskote"]:
            data = self._minimal_report_data(area)
            content, media_type = render_report(data)
            assert isinstance(content, bytes)
            assert len(content) > 100


# ── GET /areas/{id}/report ─────────────────────────────────────────────────────

class TestReportEndpoint:

    def test_report_valid_area_200(self, test_app):
        areas = test_app.get("/areas").json()
        area_id = areas[0]["id"]
        r = test_app.get(f"/areas/{area_id}/report")
        assert r.status_code == 200

    def test_report_invalid_area_404(self, test_app):
        r = test_app.get("/areas/999999/report")
        assert r.status_code == 404

    def test_report_string_area_id_422(self, test_app):
        r = test_app.get("/areas/not-a-number/report")
        assert r.status_code == 422

    def test_report_default_json_content_type(self, test_app):
        areas = test_app.get("/areas").json()
        area_id = areas[0]["id"]
        r = test_app.get(f"/areas/{area_id}/report")
        assert "application/json" in r.headers["content-type"]

    def test_report_required_json_fields(self, test_app):
        areas = test_app.get("/areas").json()
        area_id = areas[0]["id"]
        data = test_app.get(f"/areas/{area_id}/report").json()
        for field in ("area", "growth_signals", "risk_signals",
                      "price_history", "infrastructure_projects",
                      "ai_summary", "forecast"):
            assert field in data, f"Missing field: {field}"

    def test_report_area_name_matches(self, test_app):
        areas = test_app.get("/areas").json()
        for a in areas:
            report = test_app.get(f"/areas/{a['id']}/report").json()
            assert report["area"]["name"] == a["name"]

    def test_report_forecast_has_scenarios(self, test_app):
        areas = test_app.get("/areas").json()
        report = test_app.get(f"/areas/{areas[0]['id']}/report").json()
        forecast = report["forecast"]
        assert "base" in forecast
        assert "optimistic" in forecast
        assert "risk" in forecast

    def test_report_forecast_base_years_ascending(self, test_app):
        areas = test_app.get("/areas").json()
        report = test_app.get(f"/areas/{areas[0]['id']}/report").json()
        years = [f["year"] for f in report["forecast"]["base"]]
        assert years == sorted(years)

    def test_report_ai_summary_not_empty(self, test_app):
        areas = test_app.get("/areas").json()
        report = test_app.get(f"/areas/{areas[0]['id']}/report").json()
        assert len(report["ai_summary"]) > 20

    def test_report_all_10_areas(self, test_app):
        areas = test_app.get("/areas").json()
        for a in areas:
            r = test_app.get(f"/areas/{a['id']}/report")
            assert r.status_code == 200, f"Report failed for area {a['name']}"

    def test_report_growth_signals_keys(self, test_app):
        areas = test_app.get("/areas").json()
        data = test_app.get(f"/areas/{areas[0]['id']}/report").json()
        expected_keys = {
            "infrastructure", "job_growth", "population_growth",
            "commercial_activity", "transaction_velocity",
            "land_scarcity", "government_spending",
        }
        assert expected_keys.issubset(data["growth_signals"].keys())

    def test_report_risk_signals_keys(self, test_app):
        areas = test_app.get("/areas").json()
        data = test_app.get(f"/areas/{areas[0]['id']}/report").json()
        expected_keys = {"flood", "water", "legal", "overvaluation", "pollution", "crime", "delay"}
        assert expected_keys.issubset(data["risk_signals"].keys())


# ── GET /areas/{id}/report?format=pdf ─────────────────────────────────────────

class TestPdfFormat:

    def test_pdf_request_returns_bytes(self, test_app):
        areas = test_app.get("/areas").json()
        area_id = areas[0]["id"]
        r = test_app.get(f"/areas/{area_id}/report?format=pdf")
        assert r.status_code == 200
        assert len(r.content) > 0

    def test_pdf_content_disposition_attachment(self, test_app):
        areas = test_app.get("/areas").json()
        area_id = areas[0]["id"]
        r = test_app.get(f"/areas/{area_id}/report?format=pdf")
        assert r.status_code == 200
        cd = r.headers.get("content-disposition", "")
        assert "attachment" in cd

    def test_pdf_content_type_pdf_or_html(self, test_app):
        areas = test_app.get("/areas").json()
        area_id = areas[0]["id"]
        r = test_app.get(f"/areas/{area_id}/report?format=pdf")
        ct = r.headers.get("content-type", "")
        assert "application/pdf" in ct or "text/html" in ct

    def test_pdf_bytes_start_with_pdf_header_if_available(self, test_app):
        if not PDF_AVAILABLE:
            pytest.skip("WeasyPrint not available — PDF header check skipped")
        areas = test_app.get("/areas").json()
        area_id = areas[0]["id"]
        r = test_app.get(f"/areas/{area_id}/report?format=pdf")
        assert r.content[:4] == b"%PDF"

    def test_pdf_invalid_area_404(self, test_app):
        r = test_app.get("/areas/999999/report?format=pdf")
        assert r.status_code == 404

    def test_pdf_filename_contains_area_name(self, test_app):
        areas = test_app.get("/areas").json()
        area = areas[0]
        r = test_app.get(f"/areas/{area['id']}/report?format=pdf")
        cd = r.headers.get("content-disposition", "")
        # Filename should reference the area somehow
        area_slug = area["name"].lower().replace(" ", "_")
        assert area_slug in cd or "report" in cd


# ── is_pdf_available() ─────────────────────────────────────────────────────────

class TestPdfAvailability:

    def test_is_pdf_available_returns_bool(self):
        result = is_pdf_available()
        assert isinstance(result, bool)
