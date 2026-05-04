"""
TDD — SentimentAnalysisService (M3 Phase 1)
Tests written first (RED). Implementation follows.
"""
import pytest
from backend.models import ConvertedTicket, Bet9jaSelection
from backend.services.sentiment import (
    SentimentReport,
    SentimentAnalysisService,
    MockSentimentService,
    SentimentServiceProtocol,
)


def make_selection(odds: float, market: str = "1X2") -> Bet9jaSelection:
    return Bet9jaSelection(
        event_id="evt_001",
        event_name="Arsenal vs Chelsea",
        market=market,
        pick="1",
        odds=odds,
        original_market=market,
    )


def make_ticket(odds_list: list[float]) -> ConvertedTicket:
    total = 1.0
    for o in odds_list:
        total *= o
    return ConvertedTicket(
        source_booking_code="SENT_TEST",
        selections=[make_selection(o) for o in odds_list],
        converted_count=len(odds_list),
        skipped_count=0,
        total_odds=total,
    )


class TestSentimentReportModel:
    def test_has_required_fields(self):
        r = SentimentReport(
            label="bullish",
            score=0.72,
            confidence=0.85,
            source="heuristic",
        )
        assert r.label == "bullish"
        assert r.score == pytest.approx(0.72)
        assert r.confidence == pytest.approx(0.85)
        assert r.source == "heuristic"

    def test_score_in_range(self):
        r = SentimentReport(label="neutral", score=0.5, confidence=0.6, source="heuristic")
        assert 0.0 <= r.score <= 1.0

    def test_label_options(self):
        for label in ("bullish", "neutral", "bearish"):
            r = SentimentReport(label=label, score=0.5, confidence=0.6, source="heuristic")
            assert r.label == label


class TestSentimentServiceProtocol:
    def test_mock_implements_protocol(self):
        svc: SentimentServiceProtocol = MockSentimentService()
        assert callable(getattr(svc, "analyse", None))


class TestMockSentimentService:
    @pytest.mark.asyncio
    async def test_returns_sentiment_report(self):
        svc = MockSentimentService()
        ticket = make_ticket([2.0, 1.9])
        result = await svc.analyse(ticket)
        assert isinstance(result, SentimentReport)

    @pytest.mark.asyncio
    async def test_source_is_mock(self):
        svc = MockSentimentService()
        result = await svc.analyse(make_ticket([2.0]))
        assert result.source == "mock"

    @pytest.mark.asyncio
    async def test_label_is_valid(self):
        svc = MockSentimentService()
        result = await svc.analyse(make_ticket([2.0]))
        assert result.label in ("bullish", "neutral", "bearish")

    @pytest.mark.asyncio
    async def test_score_in_range(self):
        svc = MockSentimentService()
        result = await svc.analyse(make_ticket([2.0]))
        assert 0.0 <= result.score <= 1.0


class TestSentimentHeuristic:
    """SentimentAnalysisService._heuristic falls back without Claude API."""

    @pytest.mark.asyncio
    async def test_high_odds_is_bearish(self):
        # total_odds >= 10 → bearish
        svc = SentimentAnalysisService.__new__(SentimentAnalysisService)
        svc.api_key = None  # forces heuristic path
        ticket = make_ticket([5.0, 4.0])  # total = 20x
        result = await svc._heuristic(ticket)
        assert result.label == "bearish"
        assert result.source == "heuristic"

    @pytest.mark.asyncio
    async def test_low_odds_is_bullish(self):
        # total_odds < 3 → bullish
        svc = SentimentAnalysisService.__new__(SentimentAnalysisService)
        svc.api_key = None
        ticket = make_ticket([1.3, 1.5])  # total ≈ 1.95
        result = await svc._heuristic(ticket)
        assert result.label == "bullish"
        assert result.source == "heuristic"

    @pytest.mark.asyncio
    async def test_mid_odds_is_neutral(self):
        svc = SentimentAnalysisService.__new__(SentimentAnalysisService)
        svc.api_key = None
        ticket = make_ticket([2.0, 2.5])  # total = 5.0
        result = await svc._heuristic(ticket)
        assert result.label == "neutral"
        assert result.source == "heuristic"

    @pytest.mark.asyncio
    async def test_heuristic_confidence_is_low(self):
        svc = SentimentAnalysisService.__new__(SentimentAnalysisService)
        svc.api_key = None
        result = await svc._heuristic(make_ticket([2.0]))
        assert result.confidence < 0.5


class TestSentimentServiceFallback:
    """When no API key → falls back to heuristic."""

    @pytest.mark.asyncio
    async def test_no_api_key_uses_heuristic(self):
        svc = SentimentAnalysisService(api_key=None)
        result = await svc.analyse(make_ticket([2.0, 2.0]))
        assert result.source == "heuristic"
