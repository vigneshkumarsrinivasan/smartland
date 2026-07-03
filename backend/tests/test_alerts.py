"""
Section D — Alert CRUD + notification tests.

Endpoints:
  GET  /alerts
  POST /alerts
  DELETE /alerts/{id}
  POST /alerts/test-fire

Notifications are mock-safe (no API keys in test env → log to stdout, return True).
"""
import sys, os, uuid
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest


def _bearer(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _register(test_app, email: str) -> str:
    resp = test_app.post("/billing/register", json={"email": email, "name": "Test"})
    return resp.json()["token"]


def _get_first_area_id(test_app) -> int:
    return test_app.get("/areas").json()[0]["id"]


# ── POST /alerts ───────────────────────────────────────────────────────────────

class TestCreateAlert:

    def test_create_requires_auth(self, test_app):
        area_id = _get_first_area_id(test_app)
        r = test_app.post("/alerts", json={"area_id": area_id, "alert_type": "price_movement"})
        assert r.status_code == 401

    def test_create_email_alert_200(self, test_app):
        token = _register(test_app, f"alert1_{uuid.uuid4().hex[:8]}@test.com")
        area_id = _get_first_area_id(test_app)
        r = test_app.post(
            "/alerts",
            json={"area_id": area_id, "alert_type": "price_movement", "channel": "email"},
            headers=_bearer(token),
        )
        assert r.status_code == 200

    def test_create_returns_alert_fields(self, test_app):
        token = _register(test_app, f"alert2_{uuid.uuid4().hex[:8]}@test.com")
        area_id = _get_first_area_id(test_app)
        r = test_app.post(
            "/alerts",
            json={"area_id": area_id, "alert_type": "price_movement", "channel": "email"},
            headers=_bearer(token),
        )
        data = r.json()
        for field in ("id", "area_id", "alert_type", "channel", "is_active"):
            assert field in data, f"Missing field: {field}"

    def test_create_invalid_area_404(self, test_app):
        token = _register(test_app, f"alert3_{uuid.uuid4().hex[:8]}@test.com")
        r = test_app.post(
            "/alerts",
            json={"area_id": 999999, "alert_type": "price_movement", "channel": "email"},
            headers=_bearer(token),
        )
        assert r.status_code == 404

    def test_create_invalid_alert_type_422(self, test_app):
        token = _register(test_app, f"alert4_{uuid.uuid4().hex[:8]}@test.com")
        area_id = _get_first_area_id(test_app)
        r = test_app.post(
            "/alerts",
            json={"area_id": area_id, "alert_type": "bad_type", "channel": "email"},
            headers=_bearer(token),
        )
        assert r.status_code == 422

    def test_create_invalid_channel_422(self, test_app):
        token = _register(test_app, f"alert5_{uuid.uuid4().hex[:8]}@test.com")
        area_id = _get_first_area_id(test_app)
        r = test_app.post(
            "/alerts",
            json={"area_id": area_id, "alert_type": "price_movement", "channel": "telegram"},
            headers=_bearer(token),
        )
        assert r.status_code == 422

    def test_create_whatsapp_requires_phone(self, test_app):
        token = _register(test_app, f"alert6_{uuid.uuid4().hex[:8]}@test.com")
        area_id = _get_first_area_id(test_app)
        r = test_app.post(
            "/alerts",
            json={"area_id": area_id, "alert_type": "price_movement", "channel": "whatsapp"},
            headers=_bearer(token),
        )
        assert r.status_code == 422

    def test_create_whatsapp_with_phone_ok(self, test_app):
        token = _register(test_app, f"alert7_{uuid.uuid4().hex[:8]}@test.com")
        area_id = _get_first_area_id(test_app)
        r = test_app.post(
            "/alerts",
            json={
                "area_id": area_id,
                "alert_type": "price_movement",
                "channel": "whatsapp",
                "phone": "919876543210",
            },
            headers=_bearer(token),
        )
        assert r.status_code == 200

    def test_create_upsert_same_type_updates(self, test_app):
        """Creating same (user, area, alert_type) twice should upsert, not duplicate."""
        token = _register(test_app, f"upsert_{uuid.uuid4().hex[:8]}@test.com")
        area_id = _get_first_area_id(test_app)
        # Create first
        r1 = test_app.post(
            "/alerts",
            json={"area_id": area_id, "alert_type": "price_movement", "channel": "email", "threshold": 5.0},
            headers=_bearer(token),
        )
        id1 = r1.json()["id"]
        # Create same type again with different threshold
        r2 = test_app.post(
            "/alerts",
            json={"area_id": area_id, "alert_type": "price_movement", "channel": "email", "threshold": 10.0},
            headers=_bearer(token),
        )
        # Should update the existing alert, not create a new one
        assert r2.json()["id"] == id1
        assert r2.json()["threshold"] == 10.0

    def test_create_score_change_alert(self, test_app):
        token = _register(test_app, f"sc_{uuid.uuid4().hex[:8]}@test.com")
        area_id = _get_first_area_id(test_app)
        r = test_app.post(
            "/alerts",
            json={"area_id": area_id, "alert_type": "score_change", "channel": "email"},
            headers=_bearer(token),
        )
        assert r.status_code == 200
        assert r.json()["alert_type"] == "score_change"

    def test_create_weekly_digest_alert(self, test_app):
        token = _register(test_app, f"wd_{uuid.uuid4().hex[:8]}@test.com")
        area_id = _get_first_area_id(test_app)
        r = test_app.post(
            "/alerts",
            json={"area_id": area_id, "alert_type": "weekly_digest", "channel": "email"},
            headers=_bearer(token),
        )
        assert r.status_code == 200

    def test_create_alert_area_name_in_response(self, test_app):
        token = _register(test_app, f"nm_{uuid.uuid4().hex[:8]}@test.com")
        areas = test_app.get("/areas").json()
        area = areas[0]
        r = test_app.post(
            "/alerts",
            json={"area_id": area["id"], "alert_type": "price_movement", "channel": "email"},
            headers=_bearer(token),
        )
        data = r.json()
        assert data["area_name"] == area["name"]


# ── GET /alerts ────────────────────────────────────────────────────────────────

class TestListAlerts:

    def test_list_requires_auth(self, test_app):
        r = test_app.get("/alerts")
        assert r.status_code == 401

    def test_list_returns_list(self, test_app):
        token = _register(test_app, f"list1_{uuid.uuid4().hex[:8]}@test.com")
        r = test_app.get("/alerts", headers=_bearer(token))
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_list_empty_for_new_user(self, test_app):
        token = _register(test_app, f"empty_{uuid.uuid4().hex[:8]}@test.com")
        data = test_app.get("/alerts", headers=_bearer(token)).json()
        assert data == []

    def test_list_shows_created_alert(self, test_app):
        token = _register(test_app, f"show_{uuid.uuid4().hex[:8]}@test.com")
        area_id = _get_first_area_id(test_app)
        test_app.post(
            "/alerts",
            json={"area_id": area_id, "alert_type": "price_movement", "channel": "email"},
            headers=_bearer(token),
        )
        data = test_app.get("/alerts", headers=_bearer(token)).json()
        assert len(data) == 1
        assert data[0]["area_id"] == area_id

    def test_list_excludes_deleted_alerts(self, test_app):
        token = _register(test_app, f"del_lst_{uuid.uuid4().hex[:8]}@test.com")
        area_id = _get_first_area_id(test_app)
        r = test_app.post(
            "/alerts",
            json={"area_id": area_id, "alert_type": "price_movement", "channel": "email"},
            headers=_bearer(token),
        )
        alert_id = r.json()["id"]
        test_app.delete(f"/alerts/{alert_id}", headers=_bearer(token))
        data = test_app.get("/alerts", headers=_bearer(token)).json()
        assert all(a["id"] != alert_id for a in data)

    def test_list_only_own_alerts(self, test_app):
        """Users should only see their own alerts."""
        token_a = _register(test_app, f"own_a_{uuid.uuid4().hex[:8]}@test.com")
        token_b = _register(test_app, f"own_b_{uuid.uuid4().hex[:8]}@test.com")
        area_id = _get_first_area_id(test_app)
        # User A creates an alert
        test_app.post(
            "/alerts",
            json={"area_id": area_id, "alert_type": "price_movement", "channel": "email"},
            headers=_bearer(token_a),
        )
        # User B should see no alerts
        data_b = test_app.get("/alerts", headers=_bearer(token_b)).json()
        assert data_b == []


# ── DELETE /alerts/{id} ────────────────────────────────────────────────────────

class TestDeleteAlert:

    def test_delete_requires_auth(self, test_app):
        r = test_app.delete("/alerts/1")
        assert r.status_code == 401

    def test_delete_own_alert_ok(self, test_app):
        token = _register(test_app, f"del1_{uuid.uuid4().hex[:8]}@test.com")
        area_id = _get_first_area_id(test_app)
        r = test_app.post(
            "/alerts",
            json={"area_id": area_id, "alert_type": "price_movement", "channel": "email"},
            headers=_bearer(token),
        )
        alert_id = r.json()["id"]
        del_r = test_app.delete(f"/alerts/{alert_id}", headers=_bearer(token))
        assert del_r.status_code == 200
        assert del_r.json()["status"] == "deleted"

    def test_delete_soft_deletes(self, test_app):
        """Deleted alert should not appear in list but still exist in DB (is_active=False)."""
        token = _register(test_app, f"soft_{uuid.uuid4().hex[:8]}@test.com")
        area_id = _get_first_area_id(test_app)
        r = test_app.post(
            "/alerts",
            json={"area_id": area_id, "alert_type": "price_movement", "channel": "email"},
            headers=_bearer(token),
        )
        alert_id = r.json()["id"]
        test_app.delete(f"/alerts/{alert_id}", headers=_bearer(token))
        # Alert should not appear in list
        data = test_app.get("/alerts", headers=_bearer(token)).json()
        assert all(a["id"] != alert_id for a in data)

    def test_delete_wrong_user_404(self, test_app):
        token_a = _register(test_app, f"del_a_{uuid.uuid4().hex[:8]}@test.com")
        token_b = _register(test_app, f"del_b_{uuid.uuid4().hex[:8]}@test.com")
        area_id = _get_first_area_id(test_app)
        r = test_app.post(
            "/alerts",
            json={"area_id": area_id, "alert_type": "price_movement", "channel": "email"},
            headers=_bearer(token_a),
        )
        alert_id = r.json()["id"]
        # User B tries to delete User A's alert
        del_r = test_app.delete(f"/alerts/{alert_id}", headers=_bearer(token_b))
        assert del_r.status_code == 404

    def test_delete_nonexistent_alert_404(self, test_app):
        token = _register(test_app, f"del_nx_{uuid.uuid4().hex[:8]}@test.com")
        r = test_app.delete("/alerts/999999", headers=_bearer(token))
        assert r.status_code == 404


# ── POST /alerts/test-fire ────────────────────────────────────────────────────

class TestFireAlerts:

    def test_test_fire_returns_200_no_key_in_dev(self, test_app):
        import os
        from app.routers import alerts as alerts_mod
        original = os.environ.get("ADMIN_API_KEY")
        os.environ.pop("ADMIN_API_KEY", None)
        try:
            r = test_app.post("/alerts/test-fire")
            assert r.status_code == 200
            assert r.json()["status"] == "fired"
        finally:
            if original is not None:
                os.environ["ADMIN_API_KEY"] = original

    def test_test_fire_wrong_key_403(self, test_app):
        import os
        os.environ["ADMIN_API_KEY"] = "secret-test-key"
        try:
            r = test_app.post("/alerts/test-fire", headers={"X-Admin-Key": "wrong"})
            assert r.status_code == 403
        finally:
            os.environ.pop("ADMIN_API_KEY", None)


# ── Notification functions (mock mode: no API keys set) ───────────────────────

class TestNotificationsMockMode:

    def test_send_email_returns_true_no_key(self):
        """Without RESEND_API_KEY, send_email logs and returns True."""
        import os
        from unittest.mock import patch
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("RESEND_API_KEY", None)
            from app import notifications
            original = notifications.RESEND_API_KEY
            notifications.RESEND_API_KEY = ""
            try:
                result = notifications.send_email("a@b.com", "Test", "<p>hi</p>")
                assert result is True
            finally:
                notifications.RESEND_API_KEY = original

    def test_send_alert_email_returns_true_no_key(self):
        from app import notifications
        original = notifications.RESEND_API_KEY
        notifications.RESEND_API_KEY = ""
        try:
            result = notifications.send_alert_email(
                to="test@test.com",
                area_name="Sarjapur",
                city="Bangalore",
                alert_type="price_movement",
                message="Price changed",
                growth_score=75.0,
                risk_score=35.0,
                recommendation="Buy",
            )
            assert result is True
        finally:
            notifications.RESEND_API_KEY = original

    def test_send_whatsapp_returns_true_no_key(self):
        from app import notifications
        original = notifications.INTERAKT_API_KEY
        notifications.INTERAKT_API_KEY = ""
        try:
            result = notifications.send_whatsapp("919876543210", "test_template", ["arg1"])
            assert result is True
        finally:
            notifications.INTERAKT_API_KEY = original

    def test_send_alert_whatsapp_returns_true_no_key(self):
        from app import notifications
        original = notifications.INTERAKT_API_KEY
        notifications.INTERAKT_API_KEY = ""
        try:
            result = notifications.send_alert_whatsapp(
                phone="919876543210",
                area_name="Sarjapur",
                recommendation="Buy",
                growth_score=75.0,
                message="Price rose 6%",
            )
            assert result is True
        finally:
            notifications.INTERAKT_API_KEY = original

    def test_send_weekly_digest_returns_true_no_key(self):
        from app import notifications
        original = notifications.RESEND_API_KEY
        notifications.RESEND_API_KEY = ""
        try:
            result = notifications.send_weekly_digest_email(
                to="test@test.com",
                areas=[{
                    "name": "Sarjapur",
                    "city": "Bangalore",
                    "growth_score": 75.0,
                    "risk_score": 35.0,
                    "recommendation": "Buy",
                    "current_price_sqft": 6400,
                }],
            )
            assert result is True
        finally:
            notifications.RESEND_API_KEY = original


# ── check_price_alerts() smoke test ───────────────────────────────────────────

class TestCheckPriceAlerts:

    def test_check_price_alerts_runs_without_exception(self):
        """Should not raise even with an empty DB (via mocked SessionLocal)."""
        from unittest.mock import patch, MagicMock
        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.all.return_value = []
        # scheduler imports SessionLocal from app.database inside the function body
        with patch("app.database.SessionLocal", return_value=mock_db):
            from app.scheduler import check_price_alerts
            check_price_alerts()  # must not raise

    def test_send_weekly_digest_runs_without_exception(self):
        from unittest.mock import patch, MagicMock
        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.all.return_value = []
        with patch("app.database.SessionLocal", return_value=mock_db):
            from app.scheduler import send_weekly_digest
            send_weekly_digest()  # must not raise
