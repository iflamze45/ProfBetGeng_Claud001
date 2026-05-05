"""
Tests for syndicate management endpoints (v0.7.2).
All endpoints gated by X-API-Key; owner-scoped by the validated key.
"""
import pytest
from fastapi.testclient import TestClient
from ..main import create_app
from ..services.auth import require_api_key
from ..services.syndicate_service import MockSyndicateService

OWNER_KEY = "pbg_test_owner_key"
OTHER_KEY = "pbg_test_other_key"


@pytest.fixture
def syndicate_service():
    return MockSyndicateService()


@pytest.fixture
def client(syndicate_service):
    app = create_app()
    from ..routes import get_syndicate_service
    app.dependency_overrides[require_api_key] = lambda: OWNER_KEY
    app.dependency_overrides[get_syndicate_service] = lambda: syndicate_service
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture
def client_no_auth():
    """Client with NO api key override — tests 401 behaviour."""
    app = create_app()
    yield TestClient(app)
    app.dependency_overrides.clear()


class TestCreateSyndicate:
    def test_creates_syndicate_returns_201(self, client):
        resp = client.post("/api/v1/syndicates", json={"name": "Alpha Squad"})
        assert resp.status_code == 201

    def test_response_has_required_fields(self, client):
        resp = client.post("/api/v1/syndicates", json={"name": "Alpha Squad"})
        data = resp.json()
        for field in ("id", "name", "owner_api_key", "created_at"):
            assert field in data, f"Missing field: {field}"

    def test_owner_is_the_api_key(self, client):
        resp = client.post("/api/v1/syndicates", json={"name": "My Group"})
        assert resp.json()["owner_api_key"] == OWNER_KEY

    def test_no_api_key_returns_401(self, client_no_auth):
        resp = client_no_auth.post("/api/v1/syndicates", json={"name": "Ghost"})
        assert resp.status_code == 401

    def test_missing_name_returns_422(self, client):
        resp = client.post("/api/v1/syndicates", json={})
        assert resp.status_code == 422


class TestListSyndicates:
    def test_returns_200_with_list(self, client, syndicate_service):
        syndicate_service.create_syndicate("Squad A", OWNER_KEY)
        syndicate_service.create_syndicate("Squad B", OWNER_KEY)
        resp = client.get("/api/v1/syndicates")
        assert resp.status_code == 200
        data = resp.json()
        assert "syndicates" in data
        assert len(data["syndicates"]) == 2

    def test_only_returns_owned_syndicates(self, client, syndicate_service):
        syndicate_service.create_syndicate("My Squad", OWNER_KEY)
        syndicate_service.create_syndicate("Other Squad", OTHER_KEY)
        resp = client.get("/api/v1/syndicates")
        assert len(resp.json()["syndicates"]) == 1

    def test_no_api_key_returns_401(self, client_no_auth):
        resp = client_no_auth.get("/api/v1/syndicates")
        assert resp.status_code == 401


class TestDeleteSyndicate:
    def test_owner_can_delete(self, client, syndicate_service):
        created = syndicate_service.create_syndicate("Temp Squad", OWNER_KEY)
        resp = client.delete(f"/api/v1/syndicates/{created['id']}")
        assert resp.status_code == 204

    def test_non_owner_gets_404(self, client, syndicate_service):
        created = syndicate_service.create_syndicate("Other Squad", OTHER_KEY)
        resp = client.delete(f"/api/v1/syndicates/{created['id']}")
        assert resp.status_code == 404

    def test_unknown_id_gets_404(self, client):
        resp = client.delete("/api/v1/syndicates/nonexistent-id")
        assert resp.status_code == 404

    def test_no_api_key_returns_401(self, client_no_auth):
        resp = client_no_auth.delete("/api/v1/syndicates/some-id")
        assert resp.status_code == 401


class TestAddMember:
    def test_adds_member_returns_201(self, client, syndicate_service):
        created = syndicate_service.create_syndicate("My Squad", OWNER_KEY)
        resp = client.post(
            f"/api/v1/syndicates/{created['id']}/members",
            json={"api_key": OTHER_KEY},
        )
        assert resp.status_code == 201

    def test_response_has_member_fields(self, client, syndicate_service):
        created = syndicate_service.create_syndicate("My Squad", OWNER_KEY)
        resp = client.post(
            f"/api/v1/syndicates/{created['id']}/members",
            json={"api_key": OTHER_KEY},
        )
        data = resp.json()
        assert "syndicate_id" in data
        assert "api_key" in data

    def test_unknown_syndicate_returns_404(self, client):
        resp = client.post(
            "/api/v1/syndicates/bad-id/members",
            json={"api_key": OTHER_KEY},
        )
        assert resp.status_code == 404

    def test_no_api_key_returns_401(self, client_no_auth):
        resp = client_no_auth.post("/api/v1/syndicates/some-id/members", json={"api_key": "x"})
        assert resp.status_code == 401


class TestRemoveMember:
    def test_removes_member_returns_204(self, client, syndicate_service):
        created = syndicate_service.create_syndicate("My Squad", OWNER_KEY)
        syndicate_service.add_member(created["id"], OTHER_KEY)
        resp = client.delete(f"/api/v1/syndicates/{created['id']}/members/{OTHER_KEY}")
        assert resp.status_code == 204

    def test_unknown_member_returns_404(self, client, syndicate_service):
        created = syndicate_service.create_syndicate("My Squad", OWNER_KEY)
        resp = client.delete(f"/api/v1/syndicates/{created['id']}/members/ghost-key")
        assert resp.status_code == 404

    def test_no_api_key_returns_401(self, client_no_auth):
        resp = client_no_auth.delete("/api/v1/syndicates/some-id/members/other-key")
        assert resp.status_code == 401


class TestAddTicket:
    def test_adds_ticket_returns_201(self, client, syndicate_service):
        created = syndicate_service.create_syndicate("My Squad", OWNER_KEY)
        resp = client.post(
            f"/api/v1/syndicates/{created['id']}/tickets",
            json={"booking_code": "SB123456"},
        )
        assert resp.status_code == 201

    def test_response_has_ticket_fields(self, client, syndicate_service):
        created = syndicate_service.create_syndicate("My Squad", OWNER_KEY)
        resp = client.post(
            f"/api/v1/syndicates/{created['id']}/tickets",
            json={"booking_code": "SB123456"},
        )
        data = resp.json()
        assert "id" in data
        assert "syndicate_id" in data
        assert "booking_code" in data

    def test_unknown_syndicate_returns_404(self, client):
        resp = client.post(
            "/api/v1/syndicates/bad-id/tickets",
            json={"booking_code": "SB999"},
        )
        assert resp.status_code == 404

    def test_no_api_key_returns_401(self, client_no_auth):
        resp = client_no_auth.post("/api/v1/syndicates/id/tickets", json={"booking_code": "X"})
        assert resp.status_code == 401
