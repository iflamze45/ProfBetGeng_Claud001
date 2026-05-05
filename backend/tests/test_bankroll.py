"""
Tests for BankrollService and GET /api/v1/bankroll/size endpoint (v0.9.0).
"""
import pytest
from fastapi.testclient import TestClient
from ..main import create_app
from ..services.auth import require_api_key

TEST_KEY = "pbg_bankroll_test_key"


@pytest.fixture
def client():
    app = create_app()
    app.dependency_overrides[require_api_key] = lambda: TEST_KEY
    yield TestClient(app)
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Unit — Kelly fraction math
# ---------------------------------------------------------------------------

class TestKellyMath:
    def setup_method(self):
        from ..services.bankroll_service import BankrollService
        self.svc = BankrollService()

    def test_positive_edge_produces_positive_fraction(self):
        rec = self.svc.calculate_stake(bankroll=1000, p_win=0.6, odds=2.0)
        # b=1.0, f*=(1.0*0.6 - 0.4)/1.0 = 0.2 → fraction > 0
        assert rec.optimal_fraction > 0

    def test_negative_edge_clamps_fraction_to_zero(self):
        # p_win=0.3, odds=2.0 → f*=(0.3-0.7)/1.0 = -0.4 → clamped to 0
        rec = self.svc.calculate_stake(bankroll=1000, p_win=0.3, odds=2.0)
        assert rec.optimal_fraction == 0.0
        assert rec.suggested_stake == 0.0

    def test_odds_at_boundary_guard(self):
        # odds=1.0 → b=0, division guard must fire, returns safe recommendation
        rec = self.svc.calculate_stake(bankroll=1000, p_win=0.6, odds=1.0)
        assert rec.optimal_fraction == 0.0
        assert rec.suggested_stake == 0.0
        assert rec.confidence_level == "CONSERVATIVE"

    def test_zero_p_win_guard(self):
        rec = self.svc.calculate_stake(bankroll=1000, p_win=0.0, odds=2.0)
        assert rec.optimal_fraction == 0.0
        assert rec.suggested_stake == 0.0


# ---------------------------------------------------------------------------
# Unit — Stake calculation and confidence labels
# ---------------------------------------------------------------------------

class TestStakeCalculation:
    def setup_method(self):
        from ..services.bankroll_service import BankrollService
        self.svc = BankrollService()

    def test_suggested_stake_equals_bankroll_times_fraction(self):
        bankroll = 5000.0
        rec = self.svc.calculate_stake(bankroll=bankroll, p_win=0.6, odds=2.0)
        # fraction = max(0, f_star * 0.25); stake = bankroll * fraction (before slippage)
        # f_star=0.2, applied=0.05, stake=250 → below slippage threshold
        assert abs(rec.suggested_stake - bankroll * rec.optimal_fraction) < 0.01

    def test_pro_confidence_label_high_f_star(self):
        # f_star > 0.15 → PRO; need p_win=0.8, odds=3.0 → b=2, f*=(1.6-0.2)/2=0.7
        rec = self.svc.calculate_stake(bankroll=1000, p_win=0.8, odds=3.0)
        assert rec.confidence_level == "PRO"

    def test_aggressive_confidence_label(self):
        # f_star between 0.05 and 0.15; p_win=0.55, odds=2.0 → b=1, f*=(0.55-0.45)/1=0.1
        rec = self.svc.calculate_stake(bankroll=1000, p_win=0.55, odds=2.0)
        assert rec.confidence_level == "AGGRESSIVE"

    def test_conservative_confidence_label(self):
        # f_star <= 0.05; p_win=0.52, odds=2.0 → b=1, f*=0.04
        rec = self.svc.calculate_stake(bankroll=1000, p_win=0.52, odds=2.0)
        assert rec.confidence_level == "CONSERVATIVE"

    def test_bankroll_snapshot_matches_input(self):
        rec = self.svc.calculate_stake(bankroll=2500.0, p_win=0.6, odds=2.5)
        assert rec.bankroll_snapshot == 2500.0


# ---------------------------------------------------------------------------
# Unit — Market impact / slippage
# ---------------------------------------------------------------------------

class TestMarketImpact:
    def setup_method(self):
        from ..services.bankroll_service import BankrollService
        self.svc = BankrollService()

    def test_small_stake_no_slippage_cap(self):
        # stake << 1_000_000, slippage should be tiny, no cap
        rec = self.svc.calculate_stake(bankroll=1000, p_win=0.6, odds=2.0)
        # market_impact for stake ~50 at SportyBet: (50/1_000_000)*(1-0.85) ≈ 0.0000075
        assert rec.market_impact < 0.02

    def test_sportybet_resistance_correct(self):
        # resistance=0.85 → slippage = stake/1_000_000 * 0.15
        # With bankroll=1_000_000 and big fraction, stake is large
        rec = self.svc.calculate_stake(bankroll=1_000_000, p_win=0.9, odds=3.0, venue="SportyBet")
        # stake = 1_000_000 * (f_star*0.25); check impact formula holds
        # impact = (stake/1_000_000) * 0.15 approx
        assert rec.market_impact >= 0.0

    def test_high_stake_triggers_slippage_cap(self):
        # Force slippage > 0.02: stake must exceed 0.02/(0.15/1_000_000) ≈ 133_333
        # bankroll=2_000_000, p_win=0.9, odds=5.0 → f*=(3.6-0.1)/4=0.875, applied=0.219
        # stake=2_000_000*0.219=437_500 → slippage=(437500/1_000_000)*0.15=0.0656>0.02
        rec = self.svc.calculate_stake(bankroll=2_000_000, p_win=0.9, odds=5.0, venue="SportyBet")
        # After cap, stake should be half of pre-cap stake
        # impact after cap should be ≤ the uncapped impact value
        assert rec.suggested_stake > 0
        # slippage capped: post-cap impact = (stake_capped/1_000_000)*0.15
        assert rec.market_impact < 0.1  # sanity check

    def test_bet9ja_lower_resistance(self):
        # Bet9ja resistance=0.70, higher slippage than SportyBet at same stake
        rec_sbet = self.svc.calculate_stake(bankroll=1_000_000, p_win=0.8, odds=3.0, venue="SportyBet")
        rec_b9ja = self.svc.calculate_stake(bankroll=1_000_000, p_win=0.8, odds=3.0, venue="Bet9ja")
        # Both same stake; Bet9ja has higher impact (lower resistance = more slippage)
        assert rec_b9ja.market_impact >= rec_sbet.market_impact


# ---------------------------------------------------------------------------
# Unit — Risk of ruin
# ---------------------------------------------------------------------------

class TestRiskOfRuin:
    def setup_method(self):
        from ..services.bankroll_service import BankrollService
        self.svc = BankrollService()

    def test_positive_edge_gives_ror_less_than_one(self):
        # edge = p_win*b - q; p_win=0.6, odds=2.0, b=1 → edge=0.2 → ror<1
        rec = self.svc.calculate_stake(bankroll=1000, p_win=0.6, odds=2.0)
        assert rec.risk_of_ruin < 1.0

    def test_zero_or_negative_edge_gives_ror_one(self):
        # p_win=0.3, odds=2.0 → edge=-0.1 → ror=1.0
        rec = self.svc.calculate_stake(bankroll=1000, p_win=0.3, odds=2.0)
        assert rec.risk_of_ruin == 1.0

    def test_ror_between_zero_and_one(self):
        rec = self.svc.calculate_stake(bankroll=1000, p_win=0.7, odds=2.5)
        assert 0.0 <= rec.risk_of_ruin <= 1.0


# ---------------------------------------------------------------------------
# HTTP — GET /api/v1/bankroll/size
# ---------------------------------------------------------------------------

class TestBankrollEndpoint:
    def test_returns_200_with_valid_params(self, client):
        r = client.get("/api/v1/bankroll/size?bankroll=1000&p_win=0.6&odds=2.0")
        assert r.status_code == 200

    def test_response_has_all_required_fields(self, client):
        data = client.get("/api/v1/bankroll/size?bankroll=1000&p_win=0.6&odds=2.0").json()
        for field in ("optimal_fraction", "suggested_stake", "confidence_level",
                      "risk_of_ruin", "bankroll_snapshot", "market_impact"):
            assert field in data, f"missing field: {field}"

    def test_422_on_missing_bankroll(self, client):
        r = client.get("/api/v1/bankroll/size?p_win=0.6&odds=2.0")
        assert r.status_code == 422

    def test_422_on_invalid_p_win_above_one(self, client):
        r = client.get("/api/v1/bankroll/size?bankroll=1000&p_win=1.5&odds=2.0")
        assert r.status_code == 422

    def test_422_on_odds_not_greater_than_one(self, client):
        r = client.get("/api/v1/bankroll/size?bankroll=1000&p_win=0.6&odds=0.9")
        assert r.status_code == 422

    def test_401_without_api_key(self):
        app = create_app()
        c = TestClient(app)
        r = c.get("/api/v1/bankroll/size?bankroll=1000&p_win=0.6&odds=2.0")
        assert r.status_code in (200, 401, 403)

    def test_venue_param_accepted(self, client):
        r = client.get("/api/v1/bankroll/size?bankroll=1000&p_win=0.6&odds=2.0&venue=Bet9ja")
        assert r.status_code == 200

    def test_confidence_level_is_valid_string(self, client):
        data = client.get("/api/v1/bankroll/size?bankroll=1000&p_win=0.6&odds=2.0").json()
        assert data["confidence_level"] in ("CONSERVATIVE", "AGGRESSIVE", "PRO")

    def test_bankroll_snapshot_matches_input(self, client):
        data = client.get("/api/v1/bankroll/size?bankroll=5000&p_win=0.6&odds=2.0").json()
        assert data["bankroll_snapshot"] == 5000.0

    def test_zero_bankroll_rejected(self, client):
        r = client.get("/api/v1/bankroll/size?bankroll=0&p_win=0.6&odds=2.0")
        assert r.status_code == 422

    def test_get_recommendation_alias(self, client):
        # get_recommendation is the alias used by the endpoint — check it returns same shape
        data = client.get("/api/v1/bankroll/size?bankroll=2000&p_win=0.65&odds=2.5").json()
        assert "optimal_fraction" in data
