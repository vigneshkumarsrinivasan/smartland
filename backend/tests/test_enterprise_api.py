"""
Section E — Enterprise API key tests.

Endpoints:
  GET    /api-keys
  POST   /api-keys
  DELETE /api-keys/{id}

Pure functions:
  _generate_raw_key()
  _hash_key(raw)
  validate_api_key(raw, db)
"""
import sys, os, uuid, hashlib, secrets
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest


def _bearer(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _register(test_app, email: str, plan: str = "free") -> tuple[str, dict]:
    """Register a user and return (token, response_json). Subscribes to plan in mock mode."""
    resp = test_app.post("/billing/register", json={"email": email, "name": "Test User"})
    data = resp.json()
    token = data["token"]
    if plan != "free":
        # Subscribe endpoint expects plan_slug (not plan_id)
        r = test_app.post(
            "/billing/subscribe",
            json={"plan_slug": plan},
            headers=_bearer(token),
        )
        assert r.status_code == 200, f"Subscribe to {plan} failed: {r.json()}"
    return token, data


# ── _generate_raw_key() ────────────────────────────────────────────────────────

class TestGenerateRawKey:

    def test_raw_key_starts_with_prefix(self):
        from app.routers.api_keys import _generate_raw_key
        key = _generate_raw_key()
        assert key.startswith("ls_live_")

    def test_raw_key_length_is_72(self):
        from app.routers.api_keys import _generate_raw_key
        # "ls_live_" (8) + secrets.token_hex(32) (64) = 72
        key = _generate_raw_key()
        assert len(key) == 72

    def test_raw_keys_are_unique(self):
        from app.routers.api_keys import _generate_raw_key
        keys = {_generate_raw_key() for _ in range(50)}
        assert len(keys) == 50

    def test_raw_key_hex_portion_is_lowercase_hex(self):
        from app.routers.api_keys import _generate_raw_key
        key = _generate_raw_key()
        hex_part = key[len("ls_live_"):]
        assert all(c in "0123456789abcdef" for c in hex_part)


# ── _hash_key() ────────────────────────────────────────────────────────────────

class TestHashKey:

    def test_hash_returns_64_hex_chars(self):
        from app.routers.api_keys import _hash_key
        h = _hash_key("ls_live_abc")
        assert len(h) == 64
        assert all(c in "0123456789abcdef" for c in h)

    def test_hash_is_sha256(self):
        from app.routers.api_keys import _hash_key
        raw = "ls_live_test"
        expected = hashlib.sha256(raw.encode()).hexdigest()
        assert _hash_key(raw) == expected

    def test_hash_is_deterministic(self):
        from app.routers.api_keys import _hash_key
        assert _hash_key("x") == _hash_key("x")

    def test_different_inputs_give_different_hashes(self):
        from app.routers.api_keys import _hash_key
        assert _hash_key("key_a") != _hash_key("key_b")


# ── key_prefix from raw key ────────────────────────────────────────────────────

class TestKeyPrefix:

    def test_key_prefix_is_first_20_chars(self):
        from app.routers.api_keys import _generate_raw_key
        raw = _generate_raw_key()
        prefix = raw[:20]
        assert len(prefix) == 20
        assert prefix.startswith("ls_live_")

    def test_key_prefix_from_known_raw(self):
        # "ls_live_" = 8 chars, then 12 more = 20 total
        raw = "ls_live_" + "a" * 64
        prefix = raw[:20]
        assert prefix == "ls_live_" + "a" * 12


# ── GET /api-keys ──────────────────────────────────────────────────────────────

class TestListApiKeys:

    def test_list_requires_auth(self, test_app):
        r = test_app.get("/api-keys")
        assert r.status_code == 401

    def test_list_returns_empty_for_new_user(self, test_app):
        token, _ = _register(test_app, f"lst_{uuid.uuid4().hex[:8]}@test.com")
        r = test_app.get("/api-keys", headers=_bearer(token))
        assert r.status_code == 200
        assert r.json() == []

    def test_list_shows_no_raw_key(self, test_app):
        """Raw key must NOT appear in list response."""
        token, _ = _register(test_app, f"nrk_{uuid.uuid4().hex[:8]}@test.com", plan="enterprise")
        test_app.post("/api-keys", json={"name": "test"}, headers=_bearer(token))
        keys = test_app.get("/api-keys", headers=_bearer(token)).json()
        assert all("key" not in k for k in keys), "Full key must not appear in list"

    def test_list_shows_key_prefix(self, test_app):
        token, _ = _register(test_app, f"pfx_{uuid.uuid4().hex[:8]}@test.com", plan="enterprise")
        test_app.post("/api-keys", json={"name": "test"}, headers=_bearer(token))
        keys = test_app.get("/api-keys", headers=_bearer(token)).json()
        assert len(keys) >= 1
        assert all("key_prefix" in k for k in keys)


# ── POST /api-keys ─────────────────────────────────────────────────────────────

class TestCreateApiKey:

    def test_create_requires_auth(self, test_app):
        r = test_app.post("/api-keys", json={"name": "my key"})
        assert r.status_code == 401

    def test_free_user_forbidden(self, test_app):
        token, _ = _register(test_app, f"free_{uuid.uuid4().hex[:8]}@test.com", plan="free")
        r = test_app.post("/api-keys", json={"name": "my key"}, headers=_bearer(token))
        assert r.status_code == 403

    def test_pro_user_can_create_key(self, test_app):
        token, _ = _register(test_app, f"pro_{uuid.uuid4().hex[:8]}@test.com", plan="pro")
        r = test_app.post("/api-keys", json={"name": "my key"}, headers=_bearer(token))
        assert r.status_code == 200

    def test_enterprise_user_can_create_key(self, test_app):
        token, _ = _register(test_app, f"ent_{uuid.uuid4().hex[:8]}@test.com", plan="enterprise")
        r = test_app.post("/api-keys", json={"name": "ent key"}, headers=_bearer(token))
        assert r.status_code == 200

    def test_create_returns_full_key_once(self, test_app):
        token, _ = _register(test_app, f"once_{uuid.uuid4().hex[:8]}@test.com", plan="enterprise")
        r = test_app.post("/api-keys", json={"name": "temp"}, headers=_bearer(token))
        data = r.json()
        assert "key" in data
        assert data["key"].startswith("ls_live_")
        assert len(data["key"]) == 72

    def test_create_key_prefix_matches(self, test_app):
        token, _ = _register(test_app, f"pfm_{uuid.uuid4().hex[:8]}@test.com", plan="enterprise")
        r = test_app.post("/api-keys", json={"name": "temp"}, headers=_bearer(token))
        data = r.json()
        assert data["key_prefix"] == data["key"][:20]

    def test_enterprise_key_rpm_300(self, test_app):
        token, _ = _register(test_app, f"rpm300_{uuid.uuid4().hex[:8]}@test.com", plan="enterprise")
        r = test_app.post("/api-keys", json={"name": "temp"}, headers=_bearer(token))
        assert r.json()["requests_per_minute"] == 300

    def test_pro_key_rpm_60(self, test_app):
        token, _ = _register(test_app, f"rpm60_{uuid.uuid4().hex[:8]}@test.com", plan="pro")
        r = test_app.post("/api-keys", json={"name": "temp"}, headers=_bearer(token))
        assert r.json()["requests_per_minute"] == 60

    def test_create_with_name(self, test_app):
        token, _ = _register(test_app, f"nm_{uuid.uuid4().hex[:8]}@test.com", plan="enterprise")
        r = test_app.post("/api-keys", json={"name": "production key"}, headers=_bearer(token))
        assert r.json()["name"] == "production key"

    def test_create_default_scope_is_read(self, test_app):
        token, _ = _register(test_app, f"sc_{uuid.uuid4().hex[:8]}@test.com", plan="enterprise")
        r = test_app.post("/api-keys", json={"name": "temp"}, headers=_bearer(token))
        assert r.json()["scopes"] == "read"

    def test_create_read_write_scope_enterprise_ok(self, test_app):
        token, _ = _register(test_app, f"rw_{uuid.uuid4().hex[:8]}@test.com", plan="enterprise")
        r = test_app.post("/api-keys", json={"name": "rw key", "scopes": "read,write"}, headers=_bearer(token))
        assert r.status_code == 200
        assert r.json()["scopes"] == "read,write"

    def test_create_read_write_scope_pro_forbidden(self, test_app):
        """Pro plan cannot create read,write scoped keys."""
        token, _ = _register(test_app, f"rwp_{uuid.uuid4().hex[:8]}@test.com", plan="pro")
        r = test_app.post("/api-keys", json={"name": "rw", "scopes": "read,write"}, headers=_bearer(token))
        assert r.status_code == 403

    def test_create_invalid_scope_422(self, test_app):
        token, _ = _register(test_app, f"ivs_{uuid.uuid4().hex[:8]}@test.com", plan="enterprise")
        r = test_app.post("/api-keys", json={"name": "temp", "scopes": "admin"}, headers=_bearer(token))
        assert r.status_code == 422

    def test_key_not_in_list_after_creation(self, test_app):
        """Full key must not appear in subsequent GET /api-keys."""
        token, _ = _register(test_app, f"hid_{uuid.uuid4().hex[:8]}@test.com", plan="enterprise")
        r = test_app.post("/api-keys", json={"name": "hidden"}, headers=_bearer(token))
        created_key = r.json()["key"]
        keys = test_app.get("/api-keys", headers=_bearer(token)).json()
        assert all(k.get("key") != created_key for k in keys)

    def test_created_key_is_active(self, test_app):
        token, _ = _register(test_app, f"act_{uuid.uuid4().hex[:8]}@test.com", plan="enterprise")
        r = test_app.post("/api-keys", json={"name": "temp"}, headers=_bearer(token))
        assert r.json()["is_active"] is True


# ── DELETE /api-keys/{id} ─────────────────────────────────────────────────────

class TestRevokeApiKey:

    def test_revoke_requires_auth(self, test_app):
        r = test_app.delete("/api-keys/1")
        assert r.status_code == 401

    def test_revoke_own_key_ok(self, test_app):
        token, _ = _register(test_app, f"rev_{uuid.uuid4().hex[:8]}@test.com", plan="enterprise")
        key_id = test_app.post("/api-keys", json={"name": "temp"}, headers=_bearer(token)).json()["id"]
        r = test_app.delete(f"/api-keys/{key_id}", headers=_bearer(token))
        assert r.status_code == 200
        assert r.json()["status"] == "revoked"

    def test_revoke_removes_from_list(self, test_app):
        token, _ = _register(test_app, f"rm_{uuid.uuid4().hex[:8]}@test.com", plan="enterprise")
        key_id = test_app.post("/api-keys", json={"name": "temp"}, headers=_bearer(token)).json()["id"]
        test_app.delete(f"/api-keys/{key_id}", headers=_bearer(token))
        keys = test_app.get("/api-keys", headers=_bearer(token)).json()
        assert all(k["id"] != key_id for k in keys)

    def test_revoke_wrong_user_404(self, test_app):
        token_a, _ = _register(test_app, f"ra_{uuid.uuid4().hex[:8]}@test.com", plan="enterprise")
        token_b, _ = _register(test_app, f"rb_{uuid.uuid4().hex[:8]}@test.com", plan="enterprise")
        key_id = test_app.post("/api-keys", json={"name": "temp"}, headers=_bearer(token_a)).json()["id"]
        r = test_app.delete(f"/api-keys/{key_id}", headers=_bearer(token_b))
        assert r.status_code == 404

    def test_revoke_nonexistent_404(self, test_app):
        token, _ = _register(test_app, f"nx_{uuid.uuid4().hex[:8]}@test.com", plan="enterprise")
        r = test_app.delete("/api-keys/999999", headers=_bearer(token))
        assert r.status_code == 404


# ── validate_api_key() ─────────────────────────────────────────────────────────

class TestValidateApiKey:

    def test_valid_key_returns_key_obj(self, test_app, db_session):
        token, _ = _register(test_app, f"val_{uuid.uuid4().hex[:8]}@test.com", plan="enterprise")
        r = test_app.post("/api-keys", json={"name": "validate_test"}, headers=_bearer(token))
        raw_key = r.json()["key"]

        from app.routers.api_keys import validate_api_key
        result = validate_api_key(raw_key, db_session)
        assert result is not None
        assert result.is_active is True

    def test_invalid_key_returns_none(self, db_session):
        from app.routers.api_keys import validate_api_key
        result = validate_api_key("ls_live_" + "z" * 64, db_session)
        assert result is None

    def test_wrong_prefix_returns_none(self, db_session):
        from app.routers.api_keys import validate_api_key
        result = validate_api_key("bad_prefix_" + "a" * 64, db_session)
        assert result is None

    def test_revoked_key_returns_none(self, test_app, db_session):
        token, _ = _register(test_app, f"rvl_{uuid.uuid4().hex[:8]}@test.com", plan="enterprise")
        r = test_app.post("/api-keys", json={"name": "to_revoke"}, headers=_bearer(token))
        data = r.json()
        raw_key = data["key"]
        key_id = data["id"]

        # Revoke it
        test_app.delete(f"/api-keys/{key_id}", headers=_bearer(token))

        from app.routers.api_keys import validate_api_key
        result = validate_api_key(raw_key, db_session)
        assert result is None

    def test_validate_updates_last_used_at(self, test_app, db_session):
        token, _ = _register(test_app, f"lut_{uuid.uuid4().hex[:8]}@test.com", plan="enterprise")
        r = test_app.post("/api-keys", json={"name": "last_used"}, headers=_bearer(token))
        raw_key = r.json()["key"]

        from app.routers.api_keys import validate_api_key
        key_obj = validate_api_key(raw_key, db_session)
        assert key_obj.last_used_at is not None
