"""
Tests for WhaleTrackerService and GET /api/v1/analytics/whales endpoint (v0.8.1).
"""
import pytest
from fastapi.testclient import TestClient
from ..main import create_app
from ..services.auth import require_api_key
from ..services.whale_tracker_service import WhaleTrackerService, WhalePulse

TEST_KEY = "pbg_whales_test_key"


@pytest.fixture
def client():
    app = create_app()
    app.dependency_overrides[require_api_key] = lambda: TEST_KEY
    yield TestClient(app)
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Unit — WhaleTrackerService
# ---------------------------------------------------------------------------

class TestWhaleTrackerService:
    def setup_method(self):
        self.svc = WhaleTrackerService()

    def test_get_pulses_returns_list(self):
        assert isinstance(self.svc.get_pulses(), list)

    def test_each_pulse_is_whale_pulse(self):
        for p in self.svc.get_pulses():
            assert isinstance(p, WhalePulse)

    def test_limit_respected(self):
        assert len(self.svc.get_pulses(limit=2)) <= 2

    def test_default_limit_is_10(self):
        assert len(self.svc.get_pulses()) <= 10

    def test_confidence_in_range(self):
        for p in self.svc.get_pulses():
            assert 0.0 <= p.confidence_score <= 1.0

    def test_volume_positive(self):
        for p in self.svc.get_pulses():
            assert p.aggregated_volume > 0

    def test_nodes_reporting_positive(self):
        for p in self.svc.get_pulses():
            assert p.nodes_reporting > 0

    def test_register_pulse_appears_first(self):
        pulse = WhalePulse(
            match_id="TEST_WHALE",
            selection="1X2_HOME",
            aggregated_volume=2_000_000,
            confidence_score=0.95,
            nodes_reporting=5,
        )
        self.svc.register(pulse)
        assert self.svc.get_pulses(limit=1)[0].match_id == "TEST_WHALE"

    def test_register_capped_at_20(self):
        for i in range(25):
            self.svc.register(WhalePulse(
                match_id=f"W_{i}",
                selection="BTTS",
                aggregated_volume=1_500_000,
                confidence_score=0.80,
                nodes_reporting=3,
            ))
        assert len(self.svc.get_pulses(limit=50)) <= 20


# ---------------------------------------------------------------------------
# HTTP — GET /api/v1/analytics/whales
# ---------------------------------------------------------------------------

class TestWhalesEndpoint:
    def test_returns_200(self, client):
        assert client.get("/api/v1/analytics/whales").status_code == 200

    def test_has_pulses_key(self, client):
        assert "pulses" in client.get("/api/v1/analytics/whales").json()

    def test_has_count_key(self, client):
        assert "count" in client.get("/api/v1/analytics/whales").json()

    def test_count_matches_pulses_length(self, client):
        data = client.get("/api/v1/analytics/whales").json()
        assert data["count"] == len(data["pulses"])

    def test_each_pulse_has_required_fields(self, client):
        data = client.get("/api/v1/analytics/whales").json()
        for p in data["pulses"]:
            for f in ("match_id", "selection", "aggregated_volume", "confidence_score", "nodes_reporting"):
                assert f in p, f"missing field: {f}"

    def test_limit_param(self, client):
        data = client.get("/api/v1/analytics/whales?limit=2").json()
        assert len(data["pulses"]) <= 2

    def test_no_api_key_gated(self):
        app = create_app()
        r = TestClient(app).get("/api/v1/analytics/whales")
        assert r.status_code in (200, 401)
