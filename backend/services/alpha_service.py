"""
Alpha Service — promoted from _quarantine/alpha_engine.py (v0.9.1).
Provides market-making pricing frames using consensus odds.
Changes from quarantine: random.random() removed — all math is deterministic,
calibration_score fixed at 0.95, spread_pct added to model, no module-level singleton.
"""
import logging
from typing import Optional

from pydantic import BaseModel

logger = logging.getLogger("pbg.alpha")

_SIM_FIXTURES = [
    {"id": "LIV_CHE", "market": {"Pinnacle": 2.10, "SportyBet": 2.05, "Bet9ja": 2.08}},
    {"id": "RMA_BAR", "market": {"Pinnacle": 1.85, "SportyBet": 1.90, "Bet9ja": 1.87}},
    {"id": "MCI_MUN", "market": {"Pinnacle": 1.72, "SportyBet": 1.68, "Bet9ja": 1.70}},
    {"id": "PSG_BVB", "market": {"Pinnacle": 3.40, "SportyBet": 3.35, "Bet9ja": 3.45}},
    {"id": "JUV_INT", "market": {"Pinnacle": 2.60, "SportyBet": 2.55, "Bet9ja": 2.58}},
    {"id": "ARS_TOT", "market": {"Pinnacle": 2.20, "SportyBet": 2.15, "Bet9ja": 2.18}},
    {"id": "BVB_SCH", "market": {"Pinnacle": 1.55, "SportyBet": 1.52, "Bet9ja": 1.54}},
    {"id": "ATM_SEV", "market": {"Pinnacle": 2.00, "SportyBet": 1.98, "Bet9ja": 2.02}},
    {"id": "POR_BEN", "market": {"Pinnacle": 1.90, "SportyBet": 1.88, "Bet9ja": 1.92}},
    {"id": "AJX_PSV", "market": {"Pinnacle": 2.30, "SportyBet": 2.28, "Bet9ja": 2.32}},
]


class PricingFrame(BaseModel):
    match_id: str
    fair_odds: float
    bid_price: float
    ask_price: float
    calibration_score: float
    spread_pct: float


class AlphaService:
    """
    Market-making pricing engine.
    All methods are pure / deterministic — no random module.
    """

    SPREAD_HALF = 0.025  # 2.5% each side

    # ------------------------------------------------------------------
    # Core math — pure, testable
    # ------------------------------------------------------------------

    def price_market(self, match_id: str, market_odds: dict[str, float]) -> PricingFrame:
        """Synthesize consensus odds into a neutral alpha pricing frame."""
        consensus = sum(market_odds.values()) / len(market_odds)
        fair_odds = round(consensus, 3)
        bid = round(fair_odds * (1.0 - self.SPREAD_HALF), 3)
        ask = round(fair_odds * (1.0 + self.SPREAD_HALF), 3)
        return PricingFrame(
            match_id=match_id,
            fair_odds=fair_odds,
            bid_price=bid,
            ask_price=ask,
            calibration_score=0.95,
            spread_pct=round(self.SPREAD_HALF * 2, 4),
        )

    # ------------------------------------------------------------------
    # Public read — used by the API endpoint
    # ------------------------------------------------------------------

    def get_frames(self, limit: int = 10) -> list[PricingFrame]:
        return self._simulate(limit)

    def _simulate(self, limit: int) -> list[PricingFrame]:
        frames: list[PricingFrame] = []
        for f in _SIM_FIXTURES[:limit]:
            frames.append(self.price_market(f["id"], f["market"]))
        return frames
