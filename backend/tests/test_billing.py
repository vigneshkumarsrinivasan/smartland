"""
Section B — Billing / Subscription tests.

Plans seeded by conftest (Free/Pro/Enterprise).
Users created by conftest fixtures or inline per test with unique emails.
Uses shared test_app + db_session (session-scoped).

Deviations from test prompt spec:
  - Plans are Free/Pro/Enterprise (NOT Free/Starter/Pro)
  - No JWT/bcrypt: auth is UUID bearer tokens
  - /billing/subscribe (not /billing/create-subscription)
  - /billing/me (not /billing/status)
  - Admin returns 401 on wrong key (not 403)
  - MOCK_MODE is always True in tests (no Razorpay keys set)
"""
import sys, os, uuid
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest

# ── Helpers ────────────────────────────────────────────────────────────────────

def _bearer(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _register(test_app, email: str, name: str = "Test User") -> dict:
    resp = test_app.post("/billing/register", json={"email": email, "name": name})
    assert resp.status_code == 200
    return resp.json()


# ── GET /billing/plans ────────────────────────────────────────────────────────

class TestBillingPlans:

    def test_plans_returns_200(self, test_app):
        r = test_app.get("/billing/plans")
        assert r.status_code == 200

    def test_plans_returns_list(self, test_app):
        data = test_app.get("/billing/plans").json()
        assert isinstance(data, list)

    def test_plans_returns_three(self, test_app):
        data = test_app.get("/billing/plans").json()
        assert len(data) == 3

    def test_plan_slugs_correct(self, test_app):
        data = test_app.get("/billing/plans").json()
        slugs = {p["slug"] for p in data}
        assert slugs == {"free", "pro", "enterprise"}

    def test_free_plan_price_zero(self, test_app):
        data = test_app.get("/billing/plans").json()
        free = next(p for p in data if p["slug"] == "free")
        assert free["price_inr"] == 0

    def test_pro_plan_price_999(self, test_app):
        data = test_app.get("/billing/plans").json()
        pro = next(p for p in data if p["slug"] == "pro")
        assert pro["price_inr"] == 999

    def test_enterprise_plan_price_4999(self, test_app):
        data = test_app.get("/billing/plans").json()
        ent = next(p for p in data if p["slug"] == "enterprise")
        assert ent["price_inr"] == 4999

    def test_free_plan_max_reports_3(self, test_app):
        data = test_app.get("/billing/plans").json()
        free = next(p for p in data if p["slug"] == "free")
        assert free["max_reports_per_month"] == 3

    def test_pro_plan_unlimited_reports(self, test_app):
        data = test_app.get("/billing/plans").json()
        pro = next(p for p in data if p["slug"] == "pro")
        assert pro["max_reports_per_month"] is None

    def test_enterprise_plan_unlimited_reports(self, test_app):
        data = test_app.get("/billing/plans").json()
        ent = next(p for p in data if p["slug"] == "enterprise")
        assert ent["max_reports_per_month"] is None

    def test_plans_have_features_list(self, test_app):
        data = test_app.get("/billing/plans").json()
        for plan in data:
            assert isinstance(plan["features"], list)
            assert len(plan["features"]) > 0

    def test_plans_ordered_by_price(self, test_app):
        data = test_app.get("/billing/plans").json()
        prices = [p["price_inr"] for p in data]
        assert prices == sorted(prices)


# ── POST /billing/register ─────────────────────────────────────────────────────

class TestRegister:

    def test_register_returns_200(self, test_app):
        email = f"reg_{uuid.uuid4().hex[:8]}@test.com"
        r = test_app.post("/billing/register", json={"email": email})
        assert r.status_code == 200

    def test_register_returns_token(self, test_app):
        email = f"reg_{uuid.uuid4().hex[:8]}@test.com"
        data = _register(test_app, email)
        assert "token" in data
        assert len(data["token"]) > 10

    def test_register_returns_user_object(self, test_app):
        email = f"reg_{uuid.uuid4().hex[:8]}@test.com"
        data = _register(test_app, email)
        assert "user" in data
        assert data["user"]["email"] == email

    def test_register_assigns_free_plan(self, test_app):
        email = f"reg_{uuid.uuid4().hex[:8]}@test.com"
        data = _register(test_app, email)
        assert data["user"]["plan"]["slug"] == "free"

    def test_register_same_email_returns_same_token(self, test_app):
        email = f"idem_{uuid.uuid4().hex[:8]}@test.com"
        d1 = _register(test_app, email)
        d2 = _register(test_app, email)
        assert d1["token"] == d2["token"]

    def test_register_with_name(self, test_app):
        email = f"named_{uuid.uuid4().hex[:8]}@test.com"
        data = _register(test_app, email, name="Test Name")
        assert data["user"]["name"] == "Test Name"

    def test_register_without_name_ok(self, test_app):
        email = f"noname_{uuid.uuid4().hex[:8]}@test.com"
        r = test_app.post("/billing/register", json={"email": email})
        assert r.status_code == 200

    def test_register_missing_email_422(self, test_app):
        r = test_app.post("/billing/register", json={"name": "No Email"})
        assert r.status_code == 422


# ── GET /billing/me ────────────────────────────────────────────────────────────

class TestBillingMe:

    def test_me_requires_auth(self, test_app):
        r = test_app.get("/billing/me")
        assert r.status_code == 401

    def test_me_invalid_token_401(self, test_app):
        r = test_app.get("/billing/me", headers=_bearer("bad-token"))
        assert r.status_code == 401

    def test_me_returns_user(self, test_app, free_user):
        r = test_app.get("/billing/me", headers=_bearer(free_user.auth_token))
        assert r.status_code == 200
        data = r.json()
        assert data["user"]["email"] == free_user.email

    def test_me_returns_subscription_field(self, test_app, free_user):
        r = test_app.get("/billing/me", headers=_bearer(free_user.auth_token))
        data = r.json()
        assert "subscription" in data

    def test_me_returns_usage_field(self, test_app, free_user):
        r = test_app.get("/billing/me", headers=_bearer(free_user.auth_token))
        data = r.json()
        assert "usage" in data
        assert "reports_used_this_month" in data["usage"]
        assert "reports_limit" in data["usage"]

    def test_me_free_user_plan_slug(self, test_app, free_user):
        r = test_app.get("/billing/me", headers=_bearer(free_user.auth_token))
        data = r.json()
        assert data["user"]["plan"]["slug"] == "free"

    def test_me_free_user_no_active_sub(self, test_app, free_user):
        r = test_app.get("/billing/me", headers=_bearer(free_user.auth_token))
        data = r.json()
        # Free user with no paid subscription
        sub = data["subscription"]
        assert sub is None or sub["status"] not in ("active",)

    def test_me_pro_user_has_active_sub(self, test_app, pro_user):
        r = test_app.get("/billing/me", headers=_bearer(pro_user.auth_token))
        data = r.json()
        assert data["subscription"]["status"] == "active"

    def test_me_usage_limit_free_plan_3(self, test_app, free_user):
        r = test_app.get("/billing/me", headers=_bearer(free_user.auth_token))
        data = r.json()
        assert data["usage"]["reports_limit"] == 3

    def test_me_usage_limit_pro_none(self, test_app, pro_user):
        r = test_app.get("/billing/me", headers=_bearer(pro_user.auth_token))
        data = r.json()
        assert data["usage"]["reports_limit"] is None


# ── POST /billing/subscribe ────────────────────────────────────────────────────

class TestSubscribe:

    def test_subscribe_requires_auth(self, test_app):
        r = test_app.post("/billing/subscribe", json={"plan_slug": "pro"})
        assert r.status_code == 401

    def test_subscribe_invalid_plan_404(self, test_app, free_user):
        r = test_app.post(
            "/billing/subscribe",
            json={"plan_slug": "platinum"},
            headers=_bearer(free_user.auth_token),
        )
        assert r.status_code == 404

    def test_subscribe_pro_mock_mode(self, test_app):
        # Use a fresh user so we don't mutate shared free_user fixture
        email = f"sub_pro_{uuid.uuid4().hex[:8]}@test.com"
        token = _register(test_app, email)["token"]
        r = test_app.post(
            "/billing/subscribe",
            json={"plan_slug": "pro"},
            headers=_bearer(token),
        )
        assert r.status_code == 200
        data = r.json()
        assert data["mock_mode"] is True
        assert data["status"] == "active"

    def test_subscribe_pro_returns_plan(self, test_app):
        email = f"sub_plan_{uuid.uuid4().hex[:8]}@test.com"
        token = _register(test_app, email)["token"]
        r = test_app.post(
            "/billing/subscribe",
            json={"plan_slug": "pro"},
            headers=_bearer(token),
        )
        data = r.json()
        assert data["plan"]["slug"] == "pro"

    def test_subscribe_pro_returns_subscription(self, test_app):
        email = f"sub_subobj_{uuid.uuid4().hex[:8]}@test.com"
        token = _register(test_app, email)["token"]
        r = test_app.post(
            "/billing/subscribe",
            json={"plan_slug": "pro"},
            headers=_bearer(token),
        )
        data = r.json()
        assert "subscription" in data
        assert data["subscription"]["status"] == "active"

    def test_subscribe_pro_returns_checkout_params(self, test_app):
        email = f"sub_ck_{uuid.uuid4().hex[:8]}@test.com"
        token = _register(test_app, email)["token"]
        r = test_app.post(
            "/billing/subscribe",
            json={"plan_slug": "pro"},
            headers=_bearer(token),
        )
        data = r.json()
        assert "checkout_params" in data
        assert "subscription_id" in data["checkout_params"]

    def test_subscribe_free_plan_downgrade(self, test_app):
        # Subscribe to pro first, then downgrade to free
        email = f"downgrade_{uuid.uuid4().hex[:8]}@test.com"
        token = _register(test_app, email)["token"]
        test_app.post("/billing/subscribe", json={"plan_slug": "pro"}, headers=_bearer(token))
        r = test_app.post("/billing/subscribe", json={"plan_slug": "free"}, headers=_bearer(token))
        assert r.status_code == 200
        data = r.json()
        assert data["status"] == "switched"


# ── POST /billing/webhook ──────────────────────────────────────────────────────

class TestWebhook:

    def _make_payload(self, event: str, sub_id: str) -> dict:
        return {
            "event": event,
            "payload": {
                "subscription": {
                    "entity": {"id": sub_id}
                }
            }
        }

    def _create_sub_and_get_id(self, test_app) -> tuple[str, str]:
        """Register user, subscribe to pro, return (token, sub_id)."""
        email = f"wh_{uuid.uuid4().hex[:8]}@test.com"
        token = _register(test_app, email)["token"]
        r = test_app.post("/billing/subscribe", json={"plan_slug": "pro"}, headers=_bearer(token))
        sub_id = r.json()["subscription"]["razorpay_subscription_id"]
        return token, sub_id

    def test_webhook_unknown_sub_ignored(self, test_app):
        payload = self._make_payload("subscription.activated", "sub_does_not_exist_xyz")
        r = test_app.post("/billing/webhook", json=payload)
        assert r.status_code == 200
        assert r.json()["status"] == "unknown_subscription"

    def test_webhook_subscription_charged_keeps_active(self, test_app):
        _, sub_id = self._create_sub_and_get_id(test_app)
        payload = self._make_payload("subscription.charged", sub_id)
        r = test_app.post("/billing/webhook", json=payload)
        assert r.status_code == 200
        assert r.json()["status"] == "ok"

    def test_webhook_subscription_cancelled(self, test_app):
        _, sub_id = self._create_sub_and_get_id(test_app)
        payload = self._make_payload("subscription.cancelled", sub_id)
        r = test_app.post("/billing/webhook", json=payload)
        assert r.status_code == 200
        assert r.json()["event"] == "subscription.cancelled"

    def test_webhook_subscription_paused(self, test_app):
        _, sub_id = self._create_sub_and_get_id(test_app)
        payload = self._make_payload("subscription.paused", sub_id)
        r = test_app.post("/billing/webhook", json=payload)
        assert r.status_code == 200

    def test_webhook_invalid_json_400(self, test_app):
        r = test_app.post(
            "/billing/webhook",
            content=b"not-json",
            headers={"Content-Type": "application/json"},
        )
        assert r.status_code == 400

    def test_webhook_no_subscription_entity_ignored(self, test_app):
        r = test_app.post(
            "/billing/webhook",
            json={"event": "subscription.activated", "payload": {}},
        )
        assert r.status_code == 200
        assert r.json()["status"] == "ignored"


# ── POST /billing/cancel ───────────────────────────────────────────────────────

class TestCancel:

    def test_cancel_requires_auth(self, test_app):
        r = test_app.post("/billing/cancel")
        assert r.status_code == 401

    def test_cancel_no_subscription_404(self, test_app):
        email = f"nocancel_{uuid.uuid4().hex[:8]}@test.com"
        token = _register(test_app, email)["token"]
        r = test_app.post("/billing/cancel", headers=_bearer(token))
        assert r.status_code == 404

    def test_cancel_active_subscription_ok(self, test_app):
        email = f"cancel_{uuid.uuid4().hex[:8]}@test.com"
        token = _register(test_app, email)["token"]
        test_app.post("/billing/subscribe", json={"plan_slug": "pro"}, headers=_bearer(token))
        r = test_app.post("/billing/cancel", headers=_bearer(token))
        assert r.status_code == 200
        assert r.json()["status"] == "cancelled"

    def test_cancel_reverts_to_free_plan(self, test_app):
        email = f"revert_{uuid.uuid4().hex[:8]}@test.com"
        token = _register(test_app, email)["token"]
        test_app.post("/billing/subscribe", json={"plan_slug": "pro"}, headers=_bearer(token))
        test_app.post("/billing/cancel", headers=_bearer(token))
        me = test_app.get("/billing/me", headers=_bearer(token)).json()
        assert me["user"]["plan"]["slug"] == "free"


# ── POST /billing/log-usage ────────────────────────────────────────────────────

class TestLogUsage:

    def test_log_usage_requires_auth(self, test_app):
        r = test_app.post("/billing/log-usage?event_type=area_report")
        assert r.status_code == 401

    def test_log_usage_returns_logged(self, test_app, pro_user):
        r = test_app.post(
            "/billing/log-usage?event_type=area_report&resource_id=1",
            headers=_bearer(pro_user.auth_token),
        )
        assert r.status_code == 200
        assert r.json()["status"] == "logged"

    def test_log_usage_free_limit_exceeded_402(self, test_app):
        email = f"limit_{uuid.uuid4().hex[:8]}@test.com"
        token = _register(test_app, email)["token"]
        # Use up the 3 allowed reports
        for _ in range(3):
            test_app.post("/billing/log-usage?event_type=area_report", headers=_bearer(token))
        # 4th should fail
        r = test_app.post("/billing/log-usage?event_type=area_report", headers=_bearer(token))
        assert r.status_code == 402
        body = r.json()
        assert body["detail"]["code"] == "usage_limit_exceeded"

    def test_log_usage_non_report_event_no_limit_check(self, test_app):
        email = f"nocheck_{uuid.uuid4().hex[:8]}@test.com"
        token = _register(test_app, email)["token"]
        # "compare" event is not subject to report limit
        r = test_app.post("/billing/log-usage?event_type=compare", headers=_bearer(token))
        assert r.status_code == 200
