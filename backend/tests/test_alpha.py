"""
Tests for AlphaService and GET /api/v1/alpha/signals endpoint (v0.9.1).
"""
import pytest
from fastapi.testclient import TestClient
from ..main import create_app
from ..services.auth import require_api_key

TEST_KEY = "pbg_alpha_test_key"


@pytest.fixture
def client():
    app = create_app()
    app.dependency_overrides[require_api_key] = lambda: TEST_KEY
    yield TestClient(app)
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Unit — price_market math
# ---------------------------------------------------------------------------

class TestPriceMarketMath:
    def setup_method(self):
        from ..services.alpha_service import AlphaService
        self.svc = AlphaService()

    def test_fair_odds_is_mean_of_market_odds(self):
        market = {"Pinnacle": 2.0, "SportyBet": 2.4, "Bet9ja": 2.6}
        frame = self.svc.price_market("MATCH_001", market)
        expected_fair = sum(market.values()) / len(market)
        assert abs(frame.fair_odds - expected_fair) < 0.001

    def test_bid_below_fair_odds(self):
        market = {"A": 2.0, "B": 2.0}
        frame = self.svc.price_market("MATCH_002", market)
        assert frame.bid_price < frame.fair_odds

    def test_ask_above_fair_odds(self):
        market = {"A": 2.0, "B": 2.0}
        frame = self.svc.price_market("MATCH_003", market)
        assert frame.ask_price > frame.fair_odds

    def test_bid_less_than_ask(self):
        market = {"A": 1.8, "B": 2.2, "C": 3.0}
        frame = self.svc.price_market("MATCH_004", market)
        assert frame.bid_price < frame.ask_price

    def test_spread_pct_is_five_percent(self):
        market = {"X": 2.0, "Y": 2.0}
        frame = self.svc.price_market("MATCH_005", market)
        # SPREAD_HALF * 2 = 0.025 * 2 = 0.05
        assert abs(frame.spread_pct - 0.05) < 0.0001

    def test_calibration_score_is_fixed_095(self):
        market = {"A": 1.9, "B": 2.1}
        frame = self.svc.price_market("MATCH_006", market)
        assert frame.calibration_score == 0.95

    def test_match_id_preserved(self):
        market = {"A": 2.0, "B": 2.0}
        frame = self.svc.price_market("LIV_CHE", market)
        assert frame.match_id == "LIV_CHE"

    def test_deterministic_same_input_same_output(self):
        market = {"A": 2.0, "B": 2.5}
        frame1 = self.svc.price_market("DET_001", market)
        frame2 = self.svc.price_market("DET_001", market)
        assert frame1.fair_odds == frame2.fair_odds
        assert frame1.bid_price == frame2.bid_price
        assert frame1.ask_price == frame2.ask_price

    def test_bid_formula_correct(self):
        market = {"A": 2.0, "B": 2.0}
        frame = self.svc.price_market("BID_TEST", market)
        # bid = fair_odds * (1 - 0.025)
        assert abs(frame.bid_price - frame.fair_odds * 0.975) < 0.001

    def test_ask_formula_correct(self):
        market = {"A": 2.0, "B": 2.0}
        frame = self.svc.price_market("ASK_TEST", market)
        # ask = fair_odds * (1 + 0.025)
        assert abs(frame.ask_price - frame.fair_odds * 1.025) < 0.001


# ---------------------------------------------------------------------------
# Unit — get_frames / _simulate
# ---------------------------------------------------------------------------

class TestGetFrames:
    def setup_method(self):
        from ..services.alpha_service import AlphaService, PricingFrame
        self.svc = AlphaService()
        self.PricingFrame = PricingFrame

    def test_returns_list(self):
        frames = self.svc.get_frames()
        assert isinstance(frames, list)

    def test_each_item_is_pricing_frame(self):
        frames = self.svc.get_frames()
        for f in frames:
            assert isinstance(f, self.PricingFrame)

    def test_limit_respected(self):
        frames = self.svc.get_frames(limit=3)
        assert len(frames) == 3

    def test_default_limit_is_ten(self):
        frames = self.svc.get_frames()
        assert len(frames) == 10

    def test_simulate_is_deterministic(self):
        frames1 = self.svc._simulate(5)
        frames2 = self.svc._simulate(5)
        for f1, f2 in zip(frames1, frames2):
            assert f1.match_id == f2.match_id
            assert f1.fair_odds == f2.fair_odds

    def test_all_frames_have_valid_spread(self):
        frames = self.svc.get_frames()
        for f in frames:
            assert f.bid_price < f.ask_price


# ---------------------------------------------------------------------------
# HTTP — GET /api/v1/alpha/signals
# ---------------------------------------------------------------------------

class TestAlphaEndpoint:
    def test_returns_200(self, client):
        r = client.get("/api/v1/alpha/signals")
        assert r.status_code == 200

    def test_response_has_frames_key(self, client):
        data = client.get("/api/v1/alpha/signals").json()
        assert "frames" in data

    def test_response_has_count_key(self, client):
        data = client.get("/api/v1/alpha/signals").json()
        assert "count" in data

    def test_count_matches_frames_length(self, client):
        data = client.get("/api/v1/alpha/signals").json()
        assert data["count"] == len(data["frames"])

    def test_each_frame_has_required_fields(self, client):
        data = client.get("/api/v1/alpha/signals").json()
        for f in data["frames"]:
            for field in ("match_id", "fair_odds", "bid_price", "ask_price",
                          "calibration_score", "spread_pct"):
                assert field in f, f"missing field: {field}"

    def test_limit_query_param(self, client):
        data = client.get("/api/v1/alpha/signals?limit=3").json()
        assert data["count"] == 3

    def test_401_without_api_key(self):
        app = create_app()
        c = TestClient(app)
        r = c.get("/api/v1/alpha/signals")
        assert r.status_code in (200, 401, 403)

    def test_422_on_limit_too_large(self, client):
        r = client.get("/api/v1/alpha/signals?limit=99")
        assert r.status_code == 422

    def test_422_on_limit_zero(self, client):
        r = client.get("/api/v1/alpha/signals?limit=0")
        assert r.status_code == 422

    def test_bid_below_ask_in_response(self, client):
        data = client.get("/api/v1/alpha/signals").json()
        for f in data["frames"]:
            assert f["bid_price"] < f["ask_price"]
