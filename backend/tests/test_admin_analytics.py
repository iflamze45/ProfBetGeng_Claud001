"""
Tests for admin analytics endpoint (v0.7.1).
"""
import pytest
from fastapi.testclient import TestClient
from ..main import create_app
from ..config import get_settings
from ..services.admin_service import MockAdminService


VALID_ADMIN_TOKEN = get_settings().admin_token
INVALID_ADMIN_TOKEN = VALID_ADMIN_TOKEN + "_invalid"


@pytest.fixture
def admin_service():
    return MockAdminService()


@pytest.fixture
def client(admin_service):
    app = create_app()
    from ..admin_routes import get_admin_service
    app.dependency_overrides[get_admin_service] = lambda: admin_service
    yield TestClient(app)
    app.dependency_overrides.clear()


class TestAnalyticsEndpoint:
    def test_returns_200(self, client):
        resp = client.get(
            "/api/v1/admin/analytics",
            headers={"X-Admin-Token": VALID_ADMIN_TOKEN},
        )
        assert resp.status_code == 200

    def test_response_has_required_fields(self, client):
        resp = client.get(
            "/api/v1/admin/analytics",
            headers={"X-Admin-Token": VALID_ADMIN_TOKEN},
        )
        data = resp.json()
        assert "total_conversions" in data
        assert "conversions_per_key" in data
        assert "daily_trend" in data
        assert "success_rate" in data

    def test_total_conversions_is_int(self, client):
        resp = client.get(
            "/api/v1/admin/analytics",
            headers={"X-Admin-Token": VALID_ADMIN_TOKEN},
        )
        assert isinstance(resp.json()["total_conversions"], int)

    def test_success_rate_is_float_between_0_and_1(self, client):
        resp = client.get(
            "/api/v1/admin/analytics",
            headers={"X-Admin-Token": VALID_ADMIN_TOKEN},
        )
        rate = resp.json()["success_rate"]
        assert isinstance(rate, float)
        assert 0.0 <= rate <= 1.0

    def test_conversions_per_key_is_list(self, client):
        resp = client.get(
            "/api/v1/admin/analytics",
            headers={"X-Admin-Token": VALID_ADMIN_TOKEN},
        )
        assert isinstance(resp.json()["conversions_per_key"], list)

    def test_daily_trend_is_list(self, client):
        resp = client.get(
            "/api/v1/admin/analytics",
            headers={"X-Admin-Token": VALID_ADMIN_TOKEN},
        )
        assert isinstance(resp.json()["daily_trend"], list)

    def test_daily_trend_items_have_date_and_count(self, client):
        # Use a service seeded with conversion data
        seeded = MockAdminService(
            seed_conversions=[
                {"api_key": "key-001", "is_fully_converted": True, "created_at": "2026-05-01T10:00:00+00:00"},
                {"api_key": "key-001", "is_fully_converted": False, "created_at": "2026-05-01T14:00:00+00:00"},
                {"api_key": "key-002", "is_fully_converted": True, "created_at": "2026-05-02T09:00:00+00:00"},
            ]
        )
        app = create_app()
        from ..admin_routes import get_admin_service
        app.dependency_overrides[get_admin_service] = lambda: seeded
        c = TestClient(app)
        resp = c.get("/api/v1/admin/analytics", headers={"X-Admin-Token": VALID_ADMIN_TOKEN})
        app.dependency_overrides.clear()

        trend = resp.json()["daily_trend"]
        assert len(trend) > 0
        for item in trend:
            assert "date" in item
            assert "count" in item

    def test_aggregates_correctly_with_seed_data(self, client):
        seeded = MockAdminService(
            seed_conversions=[
                {"api_key": "key-001", "is_fully_converted": True, "created_at": "2026-05-01T10:00:00+00:00"},
                {"api_key": "key-001", "is_fully_converted": True, "created_at": "2026-05-01T11:00:00+00:00"},
                {"api_key": "key-002", "is_fully_converted": False, "created_at": "2026-05-02T09:00:00+00:00"},
            ]
        )
        app = create_app()
        from ..admin_routes import get_admin_service
        app.dependency_overrides[get_admin_service] = lambda: seeded
        c = TestClient(app)
        resp = c.get("/api/v1/admin/analytics", headers={"X-Admin-Token": VALID_ADMIN_TOKEN})
        app.dependency_overrides.clear()

        data = resp.json()
        assert data["total_conversions"] == 3
        assert abs(data["success_rate"] - 2/3) < 0.001
        per_key = {item["api_key"]: item["count"] for item in data["conversions_per_key"]}
        assert per_key["key-001"] == 2
        assert per_key["key-002"] == 1

    def test_returns_403_without_token(self, client):
        resp = client.get("/api/v1/admin/analytics")
        assert resp.status_code == 403

    def test_returns_403_with_wrong_token(self, client):
        resp = client.get(
            "/api/v1/admin/analytics",
            headers={"X-Admin-Token": INVALID_ADMIN_TOKEN},
        )
        assert resp.status_code == 403

    def test_empty_conversions_returns_zero_rate(self, client):
        resp = client.get(
            "/api/v1/admin/analytics",
            headers={"X-Admin-Token": VALID_ADMIN_TOKEN},
        )
        data = resp.json()
        assert data["total_conversions"] == 0
        assert data["success_rate"] == 0.0
