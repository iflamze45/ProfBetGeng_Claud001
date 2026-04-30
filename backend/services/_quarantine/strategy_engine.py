import logging
from typing import List, Dict, Optional, Any
from pydantic import BaseModel

logger = logging.getLogger("pbg.strategy_engine")

class ArbSignal(BaseModel):
    match_id: str
    teams: str
    outcomes: Dict[str, float]
    bookmakers: Dict[str, str]
    profit_margin: float

class StrategyEngine:
    """
    Advanced Algorithmic strategy engine for Multi-Market Arbitrage 
    and Quantitative Risk Management.
    """
    
    def __init__(self):
        self.active_signals: List[ArbSignal] = []
        self.lead_lag_rankings: Dict[str, float] = {
            "Pinnacle": 10.0, # Pure Leader
            "SportyBet": 2.0,  # Lagging
            "Bet9ja": 1.5      # Extreme Lag
        }
        # Phase 14: Correlation Matrix
        self.mover_history: Dict[str, List[str]] = {} # match_id -> [venue_order]

    def record_market_move(self, match_id: str, venue: str):
        """Phase 14.1: Tracks the sequence of odds changes."""
        if match_id not in self.mover_history:
            self.mover_history[match_id] = []
        
        if venue not in self.mover_history[match_id]:
            self.mover_history[match_id].append(venue)
            logger.info(f"TEMPORAL_MATRIC: {venue} moved for {match_id}. Position: {len(self.mover_history[match_id])}")

    def detect_temporal_alpha(self, signal: ArbSignal) -> bool:
        """
        Temporal Arbitrage: Checks if the signal is triggered by a 
        'Market Leader' moving while 'Laggards' are still static.
        """
        history = self.mover_history.get(signal.match_id, [])
        if not history:
            return False

        primary_mover = history[0]
        is_leader_moving = self.lead_lag_rankings.get(primary_mover, 0) > 8.0
        
        # If a top leader moved first, and our target bookie (laggard) hasn't moved yet...
        for outcome_code, venue in signal.bookmakers.items():
            if self.lead_lag_rankings.get(venue, 0) < 3.0:
                logger.info(f"CHRONOS_ALPHA: Primary Mover ({primary_mover}) detected. Front-running {venue} lag.")
                return True
        return False

    def update_market_leaders(self, venue: str, score: float):
        self.lead_lag_rankings[venue] = score

    def calculate_triangulated_arb(self, market_data: Dict[str, Dict[str, float]]) -> Optional[ArbSignal]:
        best_odds = {"1": 0.0, "X": 0.0, "2": 0.0}
        source_bookie = {"1": "", "X": "", "2": ""}
        
        for bookie, odds in market_data.items():
            for outcome, val in odds.items():
                if val > best_odds.get(outcome, 0):
                    best_odds[outcome] = val
                    source_bookie[outcome] = bookie

        if any(v == 0 for v in best_odds.values()): return None
        total_inverse = sum(1.0 / v for v in best_odds.values())
        
        if total_inverse < 1.0:
            profit_margin = 1.0 - total_inverse
            return ArbSignal(
                match_id="ARB_" + str(hash(frozenset(best_odds.items()))),
                teams="Triangulated Match",
                outcomes=best_odds,
                bookmakers=source_bookie,
                profit_margin=profit_margin
            )
        return None

    def calculate_hedge_requirement(
        self, 
        current_stake: float, 
        original_odds: float, 
        live_opposing_odds: float
    ) -> Dict[str, float]:
        potential_return = current_stake * original_odds
        hedge_stake = potential_return / live_opposing_odds
        guaranteed_profit = potential_return - current_stake - hedge_stake
        return {
            "hedge_stake": round(hedge_stake, 2),
            "guaranteed_profit": round(guaranteed_profit, 2),
            "roi_ratio": round(guaranteed_profit / (current_stake + hedge_stake), 4)
        }

    def check_liquidity(self, bookmaker: str, required_stake: float) -> Dict[str, Any]:
        mock_balances = {
            "sportybet": 45000.0,
            "bet9ja": 12000.0,
            "1xbet": 800.0
        }
        current_bal = mock_balances.get(bookmaker, 0.0)
        is_ready = current_bal >= required_stake
        return {
            "bookmaker": bookmaker,
            "available": current_bal,
            "required": required_stake,
            "is_ready": is_ready,
            "rebalance_needed": not is_ready
        }

    def get_engine_status(self) -> Dict[str, Any]:
        return {
            "active_signals_count": len(self.active_signals),
            "lead_lag_rankings": self.lead_lag_rankings,
            "mover_history_count": len(self.mover_history)
        }

# Singleton
quant_engine = StrategyEngine()
