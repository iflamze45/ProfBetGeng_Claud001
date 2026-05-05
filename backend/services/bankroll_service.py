"""
Bankroll Service — promoted from _quarantine/bankroll_optimizer.py (v0.9.0).
Implements Kelly Criterion + Quarter-Kelly fractional staking with market impact.
Changes from quarantine: singularity_engine dep removed (multiplier fixed at 1.0),
sentiment multiplier removed, no module-level singleton.
"""
import logging
from typing import Optional

from pydantic import BaseModel

logger = logging.getLogger("pbg.bankroll")

_LIQUIDITY_RESISTANCE: dict[str, float] = {
    "SportyBet": 0.85,
    "Bet9ja": 0.70,
}

_KELLY_FRACTION = 0.25  # Quarter-Kelly


class KellyRecommendation(BaseModel):
    optimal_fraction: float
    suggested_stake: float
    confidence_level: str   # "CONSERVATIVE" | "AGGRESSIVE" | "PRO"
    risk_of_ruin: float
    bankroll_snapshot: float
    market_impact: float


class BankrollService:
    """
    Kelly Criterion bankroll optimizer.
    All methods are pure / deterministic — no random module.
    """

    # ------------------------------------------------------------------
    # Core math — pure, testable
    # ------------------------------------------------------------------

    def _kelly_fraction(self, p_win: float, odds: float) -> float:
        """Quarter-Kelly fraction. Returns 0.0 when edge is negative or b==0."""
        b = odds - 1.0
        if b <= 0 or p_win <= 0:
            return 0.0
        q = 1.0 - p_win
        f_star = (b * p_win - q) / b
        return max(0.0, f_star * _KELLY_FRACTION)

    def _raw_f_star(self, p_win: float, odds: float) -> float:
        """Raw Kelly f* (before fractional scaling). Used for confidence label."""
        b = odds - 1.0
        if b <= 0 or p_win <= 0:
            return 0.0
        q = 1.0 - p_win
        return (b * p_win - q) / b

    def _market_impact(self, stake: float, venue: str) -> float:
        """Predicted slippage: (stake / 1_000_000) * (1 - resistance)."""
        resistance = _LIQUIDITY_RESISTANCE.get(venue, 0.5)
        return (stake / 1_000_000) * (1.0 - resistance)

    def _risk_of_ruin(self, p_win: float, odds: float) -> float:
        """Simplified risk-of-ruin over 20 staking units."""
        b = odds - 1.0
        if b <= 0 or p_win <= 0:
            return 1.0
        q = 1.0 - p_win
        edge = p_win * b - q
        if edge <= 0:
            return 1.0
        return round(((1.0 - edge) / (1.0 + edge)) ** 20, 6)

    def _confidence(self, f_star: float) -> str:
        if f_star > 0.15:
            return "PRO"
        if f_star > 0.05:
            return "AGGRESSIVE"
        return "CONSERVATIVE"

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def calculate_stake(
        self,
        bankroll: float,
        p_win: float,
        odds: float,
        venue: str = "SportyBet",
    ) -> KellyRecommendation:
        """Compute Kelly-optimal stake recommendation."""
        f_star = self._raw_f_star(p_win, odds)
        applied_fraction = max(0.0, f_star * _KELLY_FRACTION)
        suggested_stake = bankroll * applied_fraction

        # Market impact + cap
        impact = self._market_impact(suggested_stake, venue)
        if impact > 0.02:
            suggested_stake *= 0.5
            impact = self._market_impact(suggested_stake, venue)

        return KellyRecommendation(
            optimal_fraction=round(applied_fraction, 4),
            suggested_stake=round(suggested_stake, 2),
            confidence_level=self._confidence(f_star),
            risk_of_ruin=self._risk_of_ruin(p_win, odds),
            bankroll_snapshot=bankroll,
            market_impact=round(impact, 4),
        )

    def get_recommendation(
        self,
        bankroll: float,
        p_win: float,
        odds: float,
        venue: str = "SportyBet",
    ) -> KellyRecommendation:
        """Alias for calculate_stake — used by the API endpoint."""
        return self.calculate_stake(bankroll, p_win, odds, venue)
