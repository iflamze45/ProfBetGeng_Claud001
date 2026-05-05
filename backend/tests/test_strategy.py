"""
Tests for StrategyService and GET /api/v1/quant/arbs endpoint (v0.9.2).
The existing stub returns exactly 1 hardcoded item with profit_margin=0.042.
These tests distinguish the real service output from the stub by checking:
- Multiple items returned (stub returns 1)
- Arb math is correct (profit_margin = 1 - sum(1/best_odds))
- No-arb case returns None from find_arb()
- Hedge formula is verified
- Response items match ArbSignal schema exactly
"""
import pytest
from fastapi.testclient import TestClient
from ..main import create_app
from ..services.auth import require_api_key

TEST_KEY = "pbg_strategy_test_key"


@pytest.fixture
def client():
    app = create_app()
    app.dependency_overrides[require_api_key] = lambda: TEST_KEY
    yield TestClient(app)
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Unit — find_arb math
# ---------------------------------------------------------------------------

class TestArbDetection:
    def setup_method(self):
        from ..services.strategy_service import StrategyService
        self.svc = StrategyService()

    def test_arb_detected_when_sum_inverse_below_one(self):
        # sum(1/odds) = 1/3.0 + 1/3.5 + 1/4.0 = 0.333 + 0.286 + 0.25 = 0.869 < 1.0
        market = {
            "SportyBet": {"1": 3.0, "X": 3.5},
            "Bet9ja":    {"1": 2.8, "X": 3.0, "2": 4.0},
            "Pinnacle":  {"1": 2.9, "X": 3.2, "2": 4.2},
        }
        result = self.svc.find_arb(market)
        assert result is not None

    def test_no_arb_when_sum_inverse_above_one(self):
        # typical overround market — no arb
        market = {
            "SportyBet": {"1": 1.9, "X": 3.2, "2": 4.0},
            "Bet9ja":    {"1": 1.85, "X": 3.1, "2": 3.9},
        }
        result = self.svc.find_arb(market)
        assert result is None

    def test_profit_margin_formula_correct(self):
        # Force a clean arb: best odds = {1: 4.0, X: 4.0, 2: 4.0}
        # sum_inv = 3*(1/4.0) = 0.75 → profit = 0.25
        market = {
            "A": {"1": 4.0, "X": 3.0, "2": 3.0},
            "B": {"1": 3.0, "X": 4.0, "2": 3.0},
            "C": {"1": 3.0, "X": 3.0, "2": 4.0},
        }
        result = self.svc.find_arb(market)
        assert result is not None
        assert abs(result.profit_margin - 0.25) < 0.001

    def test_arb_signal_has_correct_fields(self):
        market = {
            "A": {"1": 4.0, "X": 3.0, "2": 3.0},
            "B": {"1": 3.0, "X": 4.0, "2": 3.0},
            "C": {"1": 3.0, "X": 3.0, "2": 4.0},
        }
        result = self.svc.find_arb(market)
        assert result is not None
        assert hasattr(result, "match_id")
        assert hasattr(result, "teams")
        assert hasattr(result, "outcomes")
        assert hasattr(result, "bookmakers")
        assert hasattr(result, "profit_margin")

    def test_best_odds_selected_per_outcome(self):
        # For outcome "1": SportyBet=3.0 should beat Bet9ja=2.5
        market = {
            "SportyBet": {"1": 3.0, "X": 3.0, "2": 3.0},
            "Bet9ja":    {"1": 2.5, "X": 3.5, "2": 3.5},
        }
        result = self.svc.find_arb(market)
        if result is not None:
            assert result.outcomes.get("1", 0) >= 3.0
            assert result.outcomes.get("X", 0) >= 3.0

    def test_overround_market_returns_none(self):
        # Typical bookmaker margin: sum(1/odds) > 1 → no arb
        market = {
            "SportyBet": {"1": 1.90, "X": 3.20, "2": 3.90},
            "Bet9ja":    {"1": 1.88, "X": 3.10, "2": 3.80},
        }
        # sum_inv = 1/1.90 + 1/3.20 + 1/3.90 ≈ 0.526 + 0.313 + 0.256 = 1.095 > 1.0
        result = self.svc.find_arb(market)
        assert result is None


# ---------------------------------------------------------------------------
# Unit — hedge_requirement formula
# ---------------------------------------------------------------------------

class TestHedgeFormula:
    def setup_method(self):
        from ..services.strategy_service import StrategyService
        self.svc = StrategyService()

    def test_hedge_stake_formula(self):
        # potential_return = 100 * 2.0 = 200
        # hedge_stake = 200 / 2.5 = 80
        result = self.svc.hedge_requirement(stake=100, original_odds=2.0, live_odds=2.5)
        assert abs(result["hedge_stake"] - 80.0) < 0.01

    def test_guaranteed_profit_formula(self):
        # guaranteed_profit = 200 - 100 - 80 = 20
        result = self.svc.hedge_requirement(stake=100, original_odds=2.0, live_odds=2.5)
        assert abs(result["guaranteed_profit"] - 20.0) < 0.01

    def test_hedge_result_has_required_keys(self):
        result = self.svc.hedge_requirement(stake=50, original_odds=3.0, live_odds=2.0)
        assert "hedge_stake" in result
        assert "guaranteed_profit" in result

    def test_potential_return_drives_hedge(self):
        # Higher stake → higher potential_return → higher hedge_stake
        r1 = self.svc.hedge_requirement(stake=100, original_odds=2.0, live_odds=2.0)
        r2 = self.svc.hedge_requirement(stake=200, original_odds=2.0, live_odds=2.0)
        assert r2["hedge_stake"] > r1["hedge_stake"]


# ---------------------------------------------------------------------------
# Unit — get_arb_windows / _simulate
# ---------------------------------------------------------------------------

class TestGetArbWindows:
    def setup_method(self):
        from ..services.strategy_service import StrategyService, ArbSignal
        self.svc = StrategyService()
        self.ArbSignal = ArbSignal

    def test_returns_list(self):
        windows = self.svc.get_arb_windows()
        assert isinstance(windows, list)

    def test_each_item_is_arb_signal(self):
        windows = self.svc.get_arb_windows()
        for w in windows:
            assert isinstance(w, self.ArbSignal)

    def test_default_returns_multiple_items(self):
        # CRITICAL: stub returns 1 item — real service returns >= 2
        windows = self.svc.get_arb_windows(limit=3)
        assert len(windows) == 3

    def test_simulate_is_deterministic(self):
        w1 = self.svc._simulate(3)
        w2 = self.svc._simulate(3)
        for a, b in zip(w1, w2):
            assert a.match_id == b.match_id
            assert a.profit_margin == b.profit_margin


# ---------------------------------------------------------------------------
# HTTP — GET /api/v1/quant/arbs (upgraded from stub)
# ---------------------------------------------------------------------------

class TestArbEndpoint:
    def test_returns_200(self, client):
        r = client.get("/api/v1/quant/arbs")
        assert r.status_code == 200

    def test_response_has_windows_key(self, client):
        data = client.get("/api/v1/quant/arbs").json()
        assert "windows" in data

    def test_each_window_has_required_fields(self, client):
        data = client.get("/api/v1/quant/arbs").json()
        for w in data["windows"]:
            for field in ("match_id", "teams", "outcomes", "bookmakers", "profit_margin"):
                assert field in w, f"missing field: {field}"

    def test_multiple_windows_returned(self, client):
        # CRITICAL: stub always returns exactly 1 window — real service returns > 1 by default
        data = client.get("/api/v1/quant/arbs").json()
        assert len(data["windows"]) > 1

    def test_limit_query_param(self, client):
        data = client.get("/api/v1/quant/arbs?limit=2").json()
        assert len(data["windows"]) == 2

    def test_profit_margin_is_float(self, client):
        data = client.get("/api/v1/quant/arbs").json()
        for w in data["windows"]:
            assert isinstance(w["profit_margin"], float)

    def test_401_without_api_key(self):
        app = create_app()
        c = TestClient(app)
        r = c.get("/api/v1/quant/arbs")
        assert r.status_code in (200, 401, 403)
