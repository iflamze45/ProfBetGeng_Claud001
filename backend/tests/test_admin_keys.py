"""
Tests for admin key management endpoints (v0.7.0).
All endpoints gated by X-Admin-Token header.
"""
import pytest
from fastapi.testclient import TestClient
from ..main import create_app
from ..config import get_settings
from ..services.admin_service import MockAdminService


VALID_ADMIN_TOKEN = get_settings().admin_token
INVALID_ADMIN_TOKEN = "wrong_token"

SEED_KEYS = [
    {
        "key_id": "key-001",
        "key_prefix": "pbg_aaa11111",
        "name": "Test Key Alpha",
        "is_active": True,
        "request_count": 42,
        "created_at": "2026-05-01T10:00:00+00:00",
        "last_used_at": "2026-05-04T09:00:00+00:00",
    },
    {
        "key_id": "key-002",
        "key_prefix": "pbg_bbb22222",
        "name": "Test Key Beta",
        "is_active": True,
        "request_count": 7,
        "created_at": "2026-05-02T12:00:00+00:00",
        "last_used_at": None,
    },
    {
        "key_id": "key-003",
        "key_prefix": "pbg_ccc33333",
        "name": "Test Key Gamma",
        "is_active": False,
        "request_count": 0,
        "created_at": "2026-05-03T08:00:00+00:00",
        "last_used_at": None,
    },
]


@pytest.fixture
def admin_service():
    return MockAdminService(seed_keys=SEED_KEYS)


@pytest.fixture
def client(admin_service):
    app = create_app()
    from ..admin_routes import get_admin_service
    app.dependency_overrides[get_admin_service] = lambda: admin_service
    yield TestClient(app)
    app.dependency_overrides.clear()


class TestListKeys:
    def test_returns_200_with_key_list(self, client):
        resp = client.get(
            "/api/v1/admin/keys",
            headers={"X-Admin-Token": VALID_ADMIN_TOKEN},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "keys" in data
        assert len(data["keys"]) == 3

    def test_key_fields_present(self, client):
        resp = client.get(
            "/api/v1/admin/keys",
            headers={"X-Admin-Token": VALID_ADMIN_TOKEN},
        )
        key = resp.json()["keys"][0]
        for field in ("key_id", "key_prefix", "name", "is_active", "request_count", "created_at"):
            assert field in key, f"Missing field: {field}"

    def test_key_hash_not_exposed(self, client):
        resp = client.get(
            "/api/v1/admin/keys",
            headers={"X-Admin-Token": VALID_ADMIN_TOKEN},
        )
        for key in resp.json()["keys"]:
            assert "key_hash" not in key

    def test_returns_403_without_token(self, client):
        resp = client.get("/api/v1/admin/keys")
        assert resp.status_code == 403

    def test_returns_403_with_wrong_token(self, client):
        resp = client.get(
            "/api/v1/admin/keys",
            headers={"X-Admin-Token": INVALID_ADMIN_TOKEN},
        )
        assert resp.status_code == 403


class TestDeactivateKey:
    def test_deactivates_active_key(self, client):
        resp = client.delete(
            "/api/v1/admin/keys/key-001",
            headers={"X-Admin-Token": VALID_ADMIN_TOKEN},
        )
        assert resp.status_code == 200
        assert resp.json()["success"] is True

    def test_returns_404_for_unknown_key(self, client):
        resp = client.delete(
            "/api/v1/admin/keys/key-999",
            headers={"X-Admin-Token": VALID_ADMIN_TOKEN},
        )
        assert resp.status_code == 404

    def test_returns_403_without_token(self, client):
        resp = client.delete("/api/v1/admin/keys/key-001")
        assert resp.status_code == 403

    def test_returns_403_with_wrong_token(self, client):
        resp = client.delete(
            "/api/v1/admin/keys/key-001",
            headers={"X-Admin-Token": INVALID_ADMIN_TOKEN},
        )
        assert resp.status_code == 403


class TestPatchKey:
    def test_updates_name(self, client):
        resp = client.patch(
            "/api/v1/admin/keys/key-001",
            headers={"X-Admin-Token": VALID_ADMIN_TOKEN},
            json={"name": "Renamed Key"},
        )
        assert resp.status_code == 200
        assert resp.json()["name"] == "Renamed Key"

    def test_toggles_is_active(self, client):
        resp = client.patch(
            "/api/v1/admin/keys/key-001",
            headers={"X-Admin-Token": VALID_ADMIN_TOKEN},
            json={"is_active": False},
        )
        assert resp.status_code == 200
        assert resp.json()["is_active"] is False

    def test_returns_404_for_unknown_key(self, client):
        resp = client.patch(
            "/api/v1/admin/keys/key-999",
            headers={"X-Admin-Token": VALID_ADMIN_TOKEN},
            json={"name": "Ghost Key"},
        )
        assert resp.status_code == 404

    def test_returns_403_without_token(self, client):
        resp = client.patch(
            "/api/v1/admin/keys/key-001",
            json={"name": "No Auth"},
        )
        assert resp.status_code == 403

    def test_returns_403_with_wrong_token(self, client):
        resp = client.patch(
            "/api/v1/admin/keys/key-001",
            headers={"X-Admin-Token": INVALID_ADMIN_TOKEN},
            json={"name": "Bad Token"},
        )
        assert resp.status_code == 403
