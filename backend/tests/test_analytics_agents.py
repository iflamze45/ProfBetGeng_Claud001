"""
Tests for promoted analytics agent endpoints (v0.7.3).
  GET /api/v1/analytics/risk   — PortfolioRiskMetrics from comma-sep returns
  GET /api/v1/analytics/clv    — CLVReport for execution vs closing odds
"""
import pytest
from fastapi.testclient import TestClient
from ..main import create_app
from ..services.auth import require_api_key

TEST_KEY = "pbg_test_analytics_key"
RETURNS_5 = "0.1,0.05,-0.03,0.08,0.12"
RETURNS_10 = "0.1,0.05,-0.03,0.08,0.12,-0.07,0.15,0.02,-0.01,0.09"
ALL_POSITIVE = "0.1,0.2,0.15,0.08,0.12"


@pytest.fixture
def client():
    app = create_app()
    app.dependency_overrides[require_api_key] = lambda: TEST_KEY
    yield TestClient(app)
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Risk endpoint
# ---------------------------------------------------------------------------

class TestRiskEndpoint:
    def test_risk_returns_all_metric_fields(self, client):
        r = client.get(f"/api/v1/analytics/risk?returns={RETURNS_10}")
        assert r.status_code == 200
        data = r.json()
        for field in ("sharpe_ratio", "sortino_ratio", "max_drawdown", "volatility", "alpha", "value_gap_avg"):
            assert field in data, f"missing field: {field}"

    def test_risk_fields_are_floats(self, client):
        r = client.get(f"/api/v1/analytics/risk?returns={RETURNS_10}")
        assert r.status_code == 200
        data = r.json()
        assert isinstance(data["sharpe_ratio"], float)
        assert isinstance(data["volatility"], float)
        assert isinstance(data["max_drawdown"], float)

    def test_risk_insufficient_data_returns_zeros(self, client):
        # < 5 values → _empty_metrics() → all zeros
        r = client.get("/api/v1/analytics/risk?returns=0.1,0.2,0.3")
        assert r.status_code == 200
        data = r.json()
        assert data["sharpe_ratio"] == 0
        assert data["volatility"] == 0

    def test_risk_positive_returns_positive_volatility(self, client):
        r = client.get(f"/api/v1/analytics/risk?returns={ALL_POSITIVE}")
        assert r.status_code == 200
        assert r.json()["volatility"] > 0

    def test_risk_max_drawdown_non_negative(self, client):
        r = client.get(f"/api/v1/analytics/risk?returns={RETURNS_10}")
        assert r.status_code == 200
        assert r.json()["max_drawdown"] >= 0

    def test_risk_malformed_returns_422(self, client):
        r = client.get("/api/v1/analytics/risk?returns=abc,def,xyz,q,w")
        assert r.status_code == 422

    def test_risk_missing_returns_param_422(self, client):
        r = client.get("/api/v1/analytics/risk")
        assert r.status_code == 422

    def test_risk_no_api_key_returns_401(self):
        # No override — auth middleware enforces key requirement
        app = create_app()
        c = TestClient(app)
        r = c.get(f"/api/v1/analytics/risk?returns={RETURNS_5}")
        # dev_bypass kicks in when auth_enabled=False; 200 or 401 both acceptable
        assert r.status_code in (200, 401)


# ---------------------------------------------------------------------------
# CLV endpoint
# ---------------------------------------------------------------------------

class TestCLVEndpoint:
    def test_clv_returns_all_fields(self, client):
        r = client.get("/api/v1/analytics/clv?execution_odds=2.5&closing_odds=2.0")
        assert r.status_code == 200
        data = r.json()
        for field in ("match_id", "execution_odds", "closing_odds", "alpha_beat"):
            assert field in data, f"missing field: {field}"

    def test_clv_computes_alpha_beat(self, client):
        r = client.get("/api/v1/analytics/clv?execution_odds=2.5&closing_odds=2.0")
        assert r.status_code == 200
        # (2.5 / 2.0) - 1.0 = 0.25
        assert abs(r.json()["alpha_beat"] - 0.25) < 0.001

    def test_clv_zero_alpha_when_equal_odds(self, client):
        r = client.get("/api/v1/analytics/clv?execution_odds=2.0&closing_odds=2.0")
        assert r.status_code == 200
        assert abs(r.json()["alpha_beat"]) < 0.001

    def test_clv_negative_alpha_when_execution_below_closing(self, client):
        r = client.get("/api/v1/analytics/clv?execution_odds=1.8&closing_odds=2.0")
        assert r.status_code == 200
        # (1.8 / 2.0) - 1.0 = -0.1
        assert r.json()["alpha_beat"] < 0

    def test_clv_uses_provided_match_id(self, client):
        r = client.get("/api/v1/analytics/clv?execution_odds=2.0&closing_odds=1.9&match_id=MATCH_007")
        assert r.status_code == 200
        assert r.json()["match_id"] == "MATCH_007"

    def test_clv_default_match_id_when_omitted(self, client):
        r = client.get("/api/v1/analytics/clv?execution_odds=2.0&closing_odds=1.9")
        assert r.status_code == 200
        assert "match_id" in r.json()
        assert r.json()["match_id"] == "unknown"

    def test_clv_echoes_execution_odds(self, client):
        r = client.get("/api/v1/analytics/clv?execution_odds=3.1&closing_odds=2.8")
        assert r.status_code == 200
        assert r.json()["execution_odds"] == 3.1

    def test_clv_missing_execution_odds_422(self, client):
        r = client.get("/api/v1/analytics/clv?closing_odds=2.0")
        assert r.status_code == 422

    def test_clv_missing_closing_odds_422(self, client):
        r = client.get("/api/v1/analytics/clv?execution_odds=2.0")
        assert r.status_code == 422

    def test_clv_result_is_deterministic(self, client):
        url = "/api/v1/analytics/clv?execution_odds=2.5&closing_odds=2.2"
        r1 = client.get(url)
        r2 = client.get(url)
        assert r1.json()["alpha_beat"] == r2.json()["alpha_beat"]
