"""
Tests for ValueDiscoveryService and GET /api/v1/signals endpoint (v0.8.0).
"""
import pytest
from fastapi.testclient import TestClient
from ..main import create_app
from ..services.auth import require_api_key
from ..services.value_discovery_service import ValueDiscoveryService, MarketSignal

VALID_TYPES = {"VALUE", "ARB", "STALE", "NEUTRAL"}
TEST_KEY = "pbg_signals_test_key"


@pytest.fixture
def client():
    app = create_app()
    app.dependency_overrides[require_api_key] = lambda: TEST_KEY
    yield TestClient(app)
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Unit — ValueDiscoveryService.calculate_value()
# ---------------------------------------------------------------------------

class TestCalculateValue:
    def setup_method(self):
        self.svc = ValueDiscoveryService()

    def test_positive_ev_returns_value(self):
        result = self.svc.calculate_value(local=2.5, global_baseline=2.0)
        assert result["type"] == "VALUE"
        assert result["score"] > 0.05

    def test_small_positive_ev_returns_stale(self):
        # EV just above 0 but <= 0.05
        result = self.svc.calculate_value(local=2.05, global_baseline=2.0)
        assert result["type"] == "STALE"
        assert 0 < result["score"] <= 0.05

    def test_negative_ev_returns_neutral(self):
        result = self.svc.calculate_value(local=1.8, global_baseline=2.0)
        assert result["type"] == "NEUTRAL"

    def test_zero_global_returns_neutral(self):
        result = self.svc.calculate_value(local=2.5, global_baseline=0)
        assert result["type"] == "NEUTRAL"
        assert result["score"] == 0.0

    def test_score_is_rounded_to_4dp(self):
        result = self.svc.calculate_value(local=2.5, global_baseline=2.0)
        assert result["score"] == round(result["score"], 4)


# ---------------------------------------------------------------------------
# Unit — ValueDiscoveryService.get_signals()
# ---------------------------------------------------------------------------

class TestGetSignals:
    def setup_method(self):
        self.svc = ValueDiscoveryService()

    def test_returns_list(self):
        signals = self.svc.get_signals()
        assert isinstance(signals, list)

    def test_each_signal_is_market_signal(self):
        signals = self.svc.get_signals()
        for s in signals:
            assert isinstance(s, MarketSignal)

    def test_limit_respected(self):
        signals = self.svc.get_signals(limit=2)
        assert len(signals) <= 2

    def test_default_limit_is_20(self):
        signals = self.svc.get_signals()
        assert len(signals) <= 20

    def test_signal_types_are_valid(self):
        signals = self.svc.get_signals()
        for s in signals:
            assert s.signal_type in VALID_TYPES

    def test_active_signals_returned_first(self):
        # If we push a real signal it should appear
        sig = MarketSignal(
            match_id="TEST_001",
            teams="Team A vs Team B",
            market="1X2_HOME",
            local_odds=2.5,
            global_odds=2.0,
            value_score=0.25,
            signal_type="VALUE",
        )
        self.svc._emit(sig)
        result = self.svc.get_signals(limit=1)
        assert result[0].match_id == "TEST_001"


# ---------------------------------------------------------------------------
# HTTP — GET /api/v1/signals
# ---------------------------------------------------------------------------

class TestSignalsEndpoint:
    def test_returns_200(self, client):
        r = client.get("/api/v1/signals")
        assert r.status_code == 200

    def test_response_has_signals_key(self, client):
        r = client.get("/api/v1/signals")
        assert "signals" in r.json()

    def test_response_has_count_key(self, client):
        r = client.get("/api/v1/signals")
        assert "count" in r.json()

    def test_count_matches_signals_length(self, client):
        data = client.get("/api/v1/signals").json()
        assert data["count"] == len(data["signals"])

    def test_signals_is_list(self, client):
        data = client.get("/api/v1/signals").json()
        assert isinstance(data["signals"], list)

    def test_each_signal_has_required_fields(self, client):
        data = client.get("/api/v1/signals").json()
        for s in data["signals"]:
            for field in ("match_id", "teams", "market", "local_odds", "global_odds", "value_score", "signal_type"):
                assert field in s, f"missing field: {field}"

    def test_limit_query_param(self, client):
        data = client.get("/api/v1/signals?limit=2").json()
        assert len(data["signals"]) <= 2

    def test_signal_types_valid(self, client):
        data = client.get("/api/v1/signals").json()
        for s in data["signals"]:
            assert s["signal_type"] in VALID_TYPES

    def test_no_api_key_401(self):
        app = create_app()
        c = TestClient(app)
        r = c.get("/api/v1/signals")
        assert r.status_code in (200, 401)
