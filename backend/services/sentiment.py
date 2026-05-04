"""
SentimentAnalysisService — M3 Phase 1
Classifies a converted ticket as bullish / neutral / bearish.
Falls back to heuristic when no API key is set.
"""
from typing import Optional, Protocol, runtime_checkable

from pydantic import BaseModel

from ..models import ConvertedTicket


class SentimentReport(BaseModel):
    label: str          # "bullish" | "neutral" | "bearish"
    score: float        # 0.0 (bearish) → 1.0 (bullish)
    confidence: float   # 0.0 → 1.0
    source: str         # "heuristic" | "claude" | "mock"


@runtime_checkable
class SentimentServiceProtocol(Protocol):
    async def analyse(self, ticket: ConvertedTicket) -> SentimentReport: ...


class SentimentAnalysisService:
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key

    async def analyse(self, ticket: ConvertedTicket) -> SentimentReport:
        # Claude API path intentionally deferred — heuristic covers M3 Phase 1 scope
        return await self._heuristic(ticket)

    async def _heuristic(self, ticket: ConvertedTicket) -> SentimentReport:
        total_odds = ticket.total_odds or 1.0
        n = len(ticket.selections)
        if n == 0:
            return SentimentReport(label="neutral", score=0.5, confidence=0.1, source="heuristic")

        if total_odds >= 10.0:
            label, score = "bearish", 0.2
        elif total_odds < 3.0:
            label, score = "bullish", 0.8
        else:
            label, score = "neutral", 0.5

        return SentimentReport(
            label=label,
            score=score,
            confidence=0.35,  # heuristic confidence is inherently low
            source="heuristic",
        )


class MockSentimentService:
    async def analyse(self, ticket: ConvertedTicket) -> SentimentReport:
        return SentimentReport(
            label="neutral",
            score=0.5,
            confidence=0.9,
            source="mock",
        )
