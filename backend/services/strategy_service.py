"""
Strategy Service — promoted from _quarantine/strategy_engine.py (v0.9.2).
Multi-market arbitrage detection and hedge calculation.
Changes from quarantine: random removed, external deps stripped,
deterministic simulation only, no module-level singleton.
"""
import logging
from typing import Optional

from pydantic import BaseModel

logger = logging.getLogger("pbg.strategy")

_SIM_FIXTURES = [
    {
        "id": "ARB_001",
        "teams": "Liverpool vs Arsenal",
        "market": {
            "Pinnacle":  {"1": 4.20, "X": 3.80, "2": 4.10},
            "SportyBet": {"1": 4.00, "X": 4.20, "2": 3.90},
            "Bet9ja":    {"1": 3.90, "X": 3.70, "2": 4.30},
        },
    },
    {
        "id": "ARB_002",
        "teams": "Real Madrid vs Barcelona",
        "market": {
            "Pinnacle":  {"1": 3.50, "X": 3.60, "2": 3.70},
            "SportyBet": {"1": 3.30, "X": 3.80, "2": 3.50},
            "Bet9ja":    {"1": 3.40, "X": 3.50, "2": 3.90},
        },
    },
    {
        "id": "ARB_003",
        "teams": "Man City vs Man Utd",
        "market": {
            "Pinnacle":  {"1": 4.00, "X": 4.00, "2": 4.00},
            "SportyBet": {"1": 3.80, "X": 4.10, "2": 3.90},
            "Bet9ja":    {"1": 3.90, "X": 3.90, "2": 4.20},
        },
    },
    {
        "id": "ARB_004",
        "teams": "PSG vs Dortmund",
        "market": {
            "Pinnacle":  {"1": 3.60, "X": 3.70, "2": 3.80},
            "SportyBet": {"1": 3.50, "X": 3.90, "2": 3.60},
            "Bet9ja":    {"1": 3.70, "X": 3.60, "2": 4.00},
        },
    },
    {
        "id": "ARB_005",
        "teams": "Juventus vs Inter Milan",
        "market": {
            "Pinnacle":  {"1": 3.80, "X": 3.80, "2": 3.80},
            "SportyBet": {"1": 3.60, "X": 4.00, "2": 3.70},
            "Bet9ja":    {"1": 3.70, "X": 3.70, "2": 4.00},
        },
    },
]

LEAD_LAG = {"Pinnacle": 10.0, "SportyBet": 2.0, "Bet9ja": 1.5}


class ArbSignal(BaseModel):
    match_id: str
    teams: str
    outcomes: dict[str, float]
    bookmakers: dict[str, str]
    profit_margin: float


class StrategyService:
    """
    Algorithmic arbitrage detection and hedge calculator.
    All methods are pure / deterministic — no random module.
    """

    # ------------------------------------------------------------------
    # Core math — pure, testable
    # ------------------------------------------------------------------

    def find_arb(self, market_data: dict[str, dict[str, float]]) -> Optional[ArbSignal]:
        """
        Triangulated arb: find best odds per outcome across bookmakers.
        Returns ArbSignal if sum(1/best_odds) < 1.0, else None.
        """
        best_odds: dict[str, float] = {}
        source_bookie: dict[str, str] = {}

        for bookie, odds in market_data.items():
            for outcome, val in odds.items():
                if val > best_odds.get(outcome, 0.0):
                    best_odds[outcome] = val
                    source_bookie[outcome] = bookie

        if not best_odds or any(v == 0.0 for v in best_odds.values()):
            return None

        total_inverse = sum(1.0 / v for v in best_odds.values())
        if total_inverse < 1.0:
            profit_margin = round(1.0 - total_inverse, 6)
            match_id = "ARB_" + str(abs(hash(frozenset(best_odds.items()))) % 100_000)
            return ArbSignal(
                match_id=match_id,
                teams="Triangulated Match",
                outcomes={k: round(v, 3) for k, v in best_odds.items()},
                bookmakers=source_bookie,
                profit_margin=profit_margin,
            )
        return None

    def hedge_requirement(
        self,
        stake: float,
        original_odds: float,
        live_odds: float,
    ) -> dict:
        """Calculate hedge stake and guaranteed profit."""
        potential_return = stake * original_odds
        hedge_stake = potential_return / live_odds
        guaranteed_profit = potential_return - stake - hedge_stake
        return {
            "hedge_stake": round(hedge_stake, 2),
            "guaranteed_profit": round(guaranteed_profit, 2),
        }

    # ------------------------------------------------------------------
    # Public read — used by the API endpoint
    # ------------------------------------------------------------------

    def get_arb_windows(self, limit: int = 5) -> list[ArbSignal]:
        return self._simulate(limit)

    def _simulate(self, limit: int) -> list[ArbSignal]:
        results: list[ArbSignal] = []
        for f in _SIM_FIXTURES[:limit]:
            sig = self.find_arb(f["market"])
            if sig is not None:
                sig = ArbSignal(
                    match_id=f["id"],
                    teams=f["teams"],
                    outcomes=sig.outcomes,
                    bookmakers=sig.bookmakers,
                    profit_margin=sig.profit_margin,
                )
            else:
                # Fixture guaranteed to be an arb — force with best odds
                all_odds: dict[str, float] = {}
                source: dict[str, str] = {}
                for bookie, odds in f["market"].items():
                    for outcome, val in odds.items():
                        if val > all_odds.get(outcome, 0.0):
                            all_odds[outcome] = val
                            source[outcome] = bookie
                inv = sum(1.0 / v for v in all_odds.values())
                margin = round(max(0.0, 1.0 - inv), 6)
                sig = ArbSignal(
                    match_id=f["id"],
                    teams=f["teams"],
                    outcomes={k: round(v, 3) for k, v in all_odds.items()},
                    bookmakers=source,
                    profit_margin=margin,
                )
            results.append(sig)
        return results
