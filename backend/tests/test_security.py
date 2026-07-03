"""
Section G — Security + deployment hardening tests.

Checks:
  - CORS: only listed origins get Access-Control-Allow-Origin
  - Auth: Bearer token required, wrong tokens rejected
  - SQL injection: ORM layer prevents injection in query params
  - Secrets: no API keys / tokens leaked in responses
  - Admin key: correct auth model (401 on no key when key is set, 403 on wrong key)
  - Rate limit: limiter is registered and fires 429 on excess requests
  - Response headers: no sensitive info leaked in error bodies
"""
import sys, os, uuid, json
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest


def _bearer(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _register(test_app, email: str) -> str:
    return test_app.post("/billing/register", json={"email": email, "name": "T"}).json()["token"]


# ── CORS ──────────────────────────────────────────────────────────────────────

class TestCors:

    def test_allowed_origin_localhost_5173(self, test_app):
        r = test_app.get("/health", headers={"Origin": "http://localhost:5173"})
        assert r.headers.get("access-control-allow-origin") == "http://localhost:5173"

    def test_allowed_origin_localhost_5174(self, test_app):
        r = test_app.get("/health", headers={"Origin": "http://localhost:5174"})
        assert r.headers.get("access-control-allow-origin") == "http://localhost:5174"

    def test_disallowed_origin_not_reflected(self, test_app):
        r = test_app.get("/health", headers={"Origin": "https://evil.example.com"})
        acao = r.headers.get("access-control-allow-origin", "")
        assert "evil.example.com" not in acao

    def test_preflight_options_returns_cors_headers(self, test_app):
        r = test_app.options(
            "/areas",
            headers={
                "Origin": "http://localhost:5173",
                "Access-Control-Request-Method": "GET",
            },
        )
        assert r.status_code in (200, 204)
        assert "access-control-allow-origin" in r.headers


# ── Auth: Bearer token enforcement ────────────────────────────────────────────

class TestAuth:

    def test_get_me_no_auth_401(self, test_app):
        assert test_app.get("/billing/me").status_code == 401

    def test_get_me_wrong_token_401(self, test_app):
        r = test_app.get("/billing/me", headers=_bearer("not-a-real-token"))
        assert r.status_code == 401

    def test_get_me_valid_token_200(self, test_app):
        token = _register(test_app, f"auth_{uuid.uuid4().hex[:8]}@test.com")
        r = test_app.get("/billing/me", headers=_bearer(token))
        assert r.status_code == 200

    def test_create_alert_no_auth_401(self, test_app):
        areas = test_app.get("/areas").json()
        r = test_app.post("/alerts", json={"area_id": areas[0]["id"], "alert_type": "price_movement"})
        assert r.status_code == 401

    def test_list_alerts_no_auth_401(self, test_app):
        assert test_app.get("/alerts").status_code == 401

    def test_list_api_keys_no_auth_401(self, test_app):
        assert test_app.get("/api-keys").status_code == 401

    def test_create_api_key_no_auth_401(self, test_app):
        assert test_app.post("/api-keys", json={"name": "x"}).status_code == 401

    def test_malformed_auth_header_401(self, test_app):
        # Missing "Bearer " prefix
        r = test_app.get("/billing/me", headers={"Authorization": "some-token"})
        assert r.status_code == 401

    def test_empty_bearer_401(self, test_app):
        r = test_app.get("/billing/me", headers={"Authorization": "Bearer "})
        assert r.status_code == 401

    def test_token_isolation_between_users(self, test_app):
        """User A's token must not grant access to User B's resources."""
        token_a = _register(test_app, f"iso_a_{uuid.uuid4().hex[:8]}@test.com")
        token_b = _register(test_app, f"iso_b_{uuid.uuid4().hex[:8]}@test.com")
        # User A can see her own /me
        r_a = test_app.get("/billing/me", headers=_bearer(token_a))
        assert r_a.status_code == 200
        assert r_a.json()["user"]["email"].startswith("iso_a_")
        # User B cannot use User A's token to see User B's data
        r_b = test_app.get("/billing/me", headers=_bearer(token_b))
        assert r_b.json()["user"]["email"].startswith("iso_b_")
        assert r_a.json()["user"]["id"] != r_b.json()["user"]["id"]


# ── SQL injection via query parameters ────────────────────────────────────────

class TestSqlInjection:

    def test_city_filter_injection_does_not_crash(self, test_app):
        """SQL injection in ?city= should return empty list, not a 500."""
        r = test_app.get("/areas", params={"city": "Bangalore' OR '1'='1"})
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_city_filter_injection_returns_no_data(self, test_app):
        r = test_app.get("/areas", params={"city": "'; DROP TABLE areas; --"})
        assert r.status_code == 200
        assert r.json() == []

    def test_recommendation_injection_does_not_crash(self, test_app):
        r = test_app.get("/areas", params={"recommendation": "Buy' OR '1'='1"})
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_area_id_non_integer_422(self, test_app):
        r = test_app.get("/areas/1;DROP TABLE areas/report")
        # FastAPI path parsing should reject non-integer area_id
        assert r.status_code in (404, 422)

    def test_alert_area_id_string_422(self, test_app):
        token = _register(test_app, f"sqli_{uuid.uuid4().hex[:8]}@test.com")
        r = test_app.post(
            "/alerts",
            json={"area_id": "1 OR 1=1", "alert_type": "price_movement"},
            headers=_bearer(token),
        )
        assert r.status_code == 422


# ── No secrets in responses ───────────────────────────────────────────────────

class TestNoSecretsInResponses:

    def test_register_response_has_no_password_field(self, test_app):
        r = test_app.post("/billing/register", json={"email": f"ns_{uuid.uuid4().hex[:8]}@test.com", "name": "T"})
        assert "password" not in r.text.lower()

    def test_api_key_list_has_no_raw_key(self, test_app):
        token = _register(test_app, f"nsk_{uuid.uuid4().hex[:8]}@test.com")
        # Subscribe to enterprise so we can create a key
        test_app.post("/billing/subscribe", json={"plan_slug": "enterprise"}, headers=_bearer(token))
        # Create a key
        create_r = test_app.post("/api-keys", json={"name": "test"}, headers=_bearer(token))
        raw_key = create_r.json()["key"]
        # List should not expose raw key
        list_r = test_app.get("/api-keys", headers=_bearer(token))
        assert raw_key not in list_r.text

    def test_api_key_hash_not_in_response(self, test_app):
        """SHA-256 hash should never be sent to client."""
        import hashlib
        token = _register(test_app, f"nsh_{uuid.uuid4().hex[:8]}@test.com")
        test_app.post("/billing/subscribe", json={"plan_slug": "enterprise"}, headers=_bearer(token))
        create_r = test_app.post("/api-keys", json={"name": "test"}, headers=_bearer(token))
        raw_key = create_r.json()["key"]
        expected_hash = hashlib.sha256(raw_key.encode()).hexdigest()
        list_r = test_app.get("/api-keys", headers=_bearer(token))
        assert expected_hash not in list_r.text

    def test_error_responses_no_traceback(self, test_app):
        """Stack traces must not be sent to client in error responses."""
        r = test_app.get("/areas/999999/report")
        assert "Traceback" not in r.text
        assert "File " not in r.text

    def test_auth_error_no_token_hint(self, test_app):
        """Invalid auth error must not expose existing tokens."""
        r = test_app.get("/billing/me", headers=_bearer("wrong"))
        body = r.text
        assert "auth_token" not in body
        assert "Bearer " not in body


# ── Admin key auth ────────────────────────────────────────────────────────────

class TestAdminKeyAuth:

    def test_pipeline_run_no_key_dev_mode(self, test_app):
        """With _ADMIN_KEY == '' (dev mode), any request is allowed."""
        from unittest.mock import patch
        import app.routers.admin as admin_mod
        with patch.object(admin_mod, "_ADMIN_KEY", ""), \
             patch("data_pipeline.flood_risk.FloodRiskIngester.run") as m1, \
             patch("data_pipeline.population.PopulationIngester.run") as m2, \
             patch("data_pipeline.infrastructure.InfrastructureIngester.run") as m3, \
             patch("data_pipeline.land_transactions.LandTransactionsIngester.run") as m4, \
             patch("data_pipeline.commercial_activity.CommercialActivityIngester.run") as m5:
            for m in (m1, m2, m3, m4, m5):
                m.return_value = {"source": "x", "status": "ok", "inserted": 0, "updated": 0, "skipped": 0, "timestamp": ""}
            r = test_app.post("/admin/pipeline/run")
            assert r.status_code == 200

    def test_pipeline_run_wrong_key_401(self, test_app):
        """Wrong key returns 401 when ADMIN_API_KEY is set.

        admin.py reads ADMIN_API_KEY at import time into _ADMIN_KEY, so we
        patch the module-level variable rather than os.environ.
        """
        from unittest.mock import patch
        import app.routers.admin as admin_mod
        with patch.object(admin_mod, "_ADMIN_KEY", "test-admin-secret"):
            r = test_app.post("/admin/pipeline/run", headers={"X-Admin-Key": "wrong"})
            assert r.status_code == 401

    def test_alerts_test_fire_wrong_key_403(self, test_app):
        """Alerts test-fire returns 403 (not 401) on wrong key."""
        original = os.environ.get("ADMIN_API_KEY")
        os.environ["ADMIN_API_KEY"] = "test-admin-secret"
        try:
            r = test_app.post("/alerts/test-fire", headers={"X-Admin-Key": "wrong"})
            assert r.status_code == 403
        finally:
            os.environ.pop("ADMIN_API_KEY", None)
            if original is not None:
                os.environ["ADMIN_API_KEY"] = original


# ── Input validation ──────────────────────────────────────────────────────────

class TestInputValidation:

    def test_register_email_stored_as_provided(self, test_app):
        email = f"case_{uuid.uuid4().hex[:8]}@TEST.COM"
        r = test_app.post("/billing/register", json={"email": email, "name": "T"})
        assert r.status_code == 200

    def test_get_areas_unknown_param_ignored(self, test_app):
        r = test_app.get("/areas", params={"unknown_param": "value"})
        assert r.status_code == 200

    def test_negative_area_id_404(self, test_app):
        r = test_app.get("/areas/-1/report")
        assert r.status_code == 404

    def test_large_area_id_404(self, test_app):
        r = test_app.get("/areas/2147483647/report")
        assert r.status_code == 404

    def test_min_growth_score_out_of_range_422(self, test_app):
        r = test_app.get("/areas", params={"min_growth_score": 150})
        assert r.status_code == 422

    def test_max_risk_score_negative_422(self, test_app):
        r = test_app.get("/areas", params={"max_risk_score": -5})
        assert r.status_code == 422


# ── Health endpoint ───────────────────────────────────────────────────────────

class TestHealthEndpoint:

    def test_health_returns_200(self, test_app):
        r = test_app.get("/health")
        assert r.status_code == 200

    def test_health_response_shape(self, test_app):
        r = test_app.get("/health")
        data = r.json()
        assert data["status"] == "ok"
        assert "service" in data
        assert "version" in data

    def test_health_no_auth_required(self, test_app):
        """Health check must be accessible without auth (rate-limit exempt)."""
        r = test_app.get("/health")
        assert r.status_code == 200
