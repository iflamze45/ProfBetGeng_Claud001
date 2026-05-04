"""
TDD — RiskEngine (M3 Phase 1)
Tests written first (RED). Implementation follows.
"""
import pytest
from backend.models import ConvertedTicket, Bet9jaSelection
from backend.services.risk_engine import RiskEngine, RiskMetrics


def make_selection(odds: float, event_id: str = "evt_001") -> Bet9jaSelection:
    return Bet9jaSelection(
        event_id=event_id,
        event_name="Test Match",
        market="1X2",
        pick="1",
        odds=odds,
        original_market="1X2",
    )


def make_ticket(odds_list: list[float], event_ids: list[str] | None = None) -> ConvertedTicket:
    if event_ids is None:
        event_ids = [f"evt_{i:03d}" for i in range(len(odds_list))]
    selections = [make_selection(o, eid) for o, eid in zip(odds_list, event_ids)]
    total_odds = 1.0
    for o in odds_list:
        total_odds *= o
    return ConvertedTicket(
        source_booking_code="TEST123",
        selections=selections,
        converted_count=len(selections),
        skipped_count=0,
        total_odds=total_odds,
    )


class TestRiskMetricsModel:
    def test_risk_metrics_has_required_fields(self):
        m = RiskMetrics(
            variance=0.5,
            expected_value=-0.1,
            kelly_fraction=0.05,
            combined_implied_probability=0.25,
            correlation_exposure=0.0,
            selection_count=3,
            avg_odds=2.0,
        )
        assert m.variance == pytest.approx(0.5)
        assert m.selection_count == 3


class TestRiskEngineCombinedImpliedProbability:
    def test_single_selection(self):
        ticket = make_ticket([2.0])
        metrics = RiskEngine.compute(ticket)
        assert metrics.combined_implied_probability == pytest.approx(0.5, abs=1e-6)

    def test_two_selections(self):
        ticket = make_ticket([2.0, 2.0])
        metrics = RiskEngine.compute(ticket)
        assert metrics.combined_implied_probability == pytest.approx(0.25, abs=1e-6)

    def test_three_selections(self):
        ticket = make_ticket([2.0, 3.0, 5.0])
        metrics = RiskEngine.compute(ticket)
        expected = (1 / 2.0) * (1 / 3.0) * (1 / 5.0)
        assert metrics.combined_implied_probability == pytest.approx(expected, abs=1e-6)


class TestRiskEngineKellyFraction:
    def test_kelly_positive_ev(self):
        # p=0.5, total_odds=2.0 → b=1.0 → kelly=(0.5*1 - 0.5)/1 = 0
        ticket = make_ticket([2.0])
        metrics = RiskEngine.compute(ticket)
        assert metrics.kelly_fraction == pytest.approx(0.0, abs=1e-6)

    def test_kelly_negative_ev_clamps_to_zero(self):
        # p=0.5, total_odds=1.5 → b=0.5 → kelly=(0.5*0.5 - 0.5)/0.5 = -0.5 → clamp to 0
        ticket = make_ticket([1.5])
        metrics = RiskEngine.compute(ticket)
        assert metrics.kelly_fraction == 0.0

    def test_kelly_bounded_zero_to_one(self):
        ticket = make_ticket([3.0, 5.0])
        metrics = RiskEngine.compute(ticket)
        assert 0.0 <= metrics.kelly_fraction <= 1.0


class TestRiskEngineVariance:
    def test_single_selection_zero_variance(self):
        ticket = make_ticket([2.0])
        metrics = RiskEngine.compute(ticket)
        assert metrics.variance == pytest.approx(0.0, abs=1e-6)

    def test_identical_odds_zero_variance(self):
        ticket = make_ticket([2.0, 2.0, 2.0])
        metrics = RiskEngine.compute(ticket)
        assert metrics.variance == pytest.approx(0.0, abs=1e-6)

    def test_variance_nonzero_for_different_odds(self):
        ticket = make_ticket([1.5, 3.5])
        metrics = RiskEngine.compute(ticket)
        assert metrics.variance > 0.0

    def test_variance_is_population_std(self):
        # odds [1.0, 3.0] → mean=2.0, population std = 1.0
        ticket = make_ticket([1.0, 3.0])
        metrics = RiskEngine.compute(ticket)
        assert metrics.variance == pytest.approx(1.0, abs=1e-6)


class TestRiskEngineExpectedValue:
    def test_ev_fair_odds(self):
        # p=0.5, total_odds=2.0 → EV = 0.5*2 - 1 = 0
        ticket = make_ticket([2.0])
        metrics = RiskEngine.compute(ticket)
        assert metrics.expected_value == pytest.approx(0.0, abs=1e-6)

    def test_ev_negative_for_house_edge(self):
        # p=1/2, total_odds=1.8 → EV = 0.5*1.8 - 1 = -0.1
        ticket = make_ticket([1.8])
        metrics = RiskEngine.compute(ticket)
        assert metrics.expected_value == pytest.approx(-0.1, abs=1e-6)

    def test_ev_uses_total_odds(self):
        ticket = make_ticket([2.0, 2.0])
        metrics = RiskEngine.compute(ticket)
        # cip=0.25, total_odds=4.0 → EV = 0.25*4 - 1 = 0
        assert metrics.expected_value == pytest.approx(0.0, abs=1e-6)


class TestRiskEngineCorrelationExposure:
    def test_no_correlation_different_events(self):
        ticket = make_ticket([2.0, 2.0], event_ids=["evt_001", "evt_002"])
        metrics = RiskEngine.compute(ticket)
        assert metrics.correlation_exposure == pytest.approx(0.0, abs=1e-6)

    def test_full_correlation_same_event(self):
        ticket = make_ticket([2.0, 2.0], event_ids=["evt_001", "evt_001"])
        metrics = RiskEngine.compute(ticket)
        assert metrics.correlation_exposure == pytest.approx(1.0, abs=1e-6)

    def test_partial_correlation(self):
        # 2 of 4 selections share same event
        ticket = make_ticket(
            [2.0, 2.0, 2.0, 2.0],
            event_ids=["evt_001", "evt_001", "evt_002", "evt_003"],
        )
        metrics = RiskEngine.compute(ticket)
        # 2 out of 4 are duplicates → 2/4 = 0.5
        assert metrics.correlation_exposure == pytest.approx(0.5, abs=1e-6)


class TestRiskEngineScalars:
    def test_selection_count(self):
        ticket = make_ticket([2.0, 3.0, 1.5])
        metrics = RiskEngine.compute(ticket)
        assert metrics.selection_count == 3

    def test_avg_odds(self):
        ticket = make_ticket([2.0, 4.0])
        metrics = RiskEngine.compute(ticket)
        assert metrics.avg_odds == pytest.approx(3.0, abs=1e-6)

    def test_total_odds_none_uses_product(self):
        ticket = ConvertedTicket(
            source_booking_code="NO_TOTAL",
            selections=[make_selection(2.0), make_selection(3.0)],
            converted_count=2,
            skipped_count=0,
            total_odds=None,
        )
        metrics = RiskEngine.compute(ticket)
        assert metrics.combined_implied_probability == pytest.approx(1 / 6.0, abs=1e-6)
