import logging
from typing import Dict, Optional, Any
from pydantic import BaseModel

from .singularity_engine import singularity_core

logger = logging.getLogger("pbg.bankroll_optimizer")

class KellyRecommendation(BaseModel):
    optimal_fraction: float
    suggested_stake: float
    confidence_level: str # "CONSERVATIVE" | "AGGRESSIVE" | "PRO"
    risk_of_ruin: float
    bankroll_snapshot: float
    market_impact: float # Predicted slippage

class KellyOptimizer:
    """
    Implements the Kelly Criterion and fractional-Kelly strategies
    to optimize bankroll management based on Value Discovery signals.
    """
    
    def __init__(self, multiplier: float = 0.25):
        # We start with Quarter-Kelly (0.25) to be safe/conservative
        self.multiplier = multiplier
        self.liquidity_resistance: dict = {"SportyBet": 0.85, "Bet9ja": 0.70} # 1.0 = High liquidity

    def calculate_market_impact(self, venue: str, stake: float) -> float:
        """
        Hyperdimensional Alpha: Predicts the odds slash (slippage) 
        caused by our own liquidity entry.
        """
        resistance = self.liquidity_resistance.get(venue, 0.5)
        # Simulation: Every 1,000,000 units of stake drops odds by (1-resistance)%
        slippage = (stake / 1_000_000) * (1 - resistance)
        return slippage

    def calculate_optimal_stake(
        self, 
        current_bankroll: float, 
        p_win: float, 
        b_odds: float,
        venue: str = "SportyBet",
        social_volume_spike: float = 1.0,
        request: Optional[Any] = None
    ) -> KellyRecommendation:
        """
        Socially-Weighted Kelly Criterion with Singularity Risk Adjustment.
        """
        if b_odds <= 1.0 or p_win <= 0:
            return self._empty_recommendation(current_bankroll)

        # b is net odds (odds - 1)
        b = b_odds - 1
        q = 1 - p_win
        
        # f* = (bp - q) / b
        f_star = (b * p_win - q) / b
        
        # Risk Management: Fractional Kelly (default 0.25)
        # Apply sentiment uplift: if vol spike, we increase exposure cautiously
        sentiment_multiplier = min(1.5, social_volume_spike)
        applied_multiplier = self.multiplier * sentiment_multiplier
        
        applied_fraction = max(0, f_star * applied_multiplier)

        # Neural Risk Overlay (Singularity Engine)
        drift_prob = singularity_core.predict_execution_drift(getattr(request, "match_id", "GLOBAL"))
        singularity_mult = singularity_core.get_singularity_stake_multiplier(drift_prob)

        suggested_stake = current_bankroll * applied_fraction * singularity_mult

        # Market Impact Adjustment: Reduce stake if slippage exceeds 2%
        impact = self.calculate_market_impact(venue, suggested_stake)
        if impact > 0.02:
            logger.warning(f"IMPACT_THRESHOLD: High slippage ({impact*100:.2f}%) detected for {venue}. Capping stake.")
            suggested_stake *= 0.5
            impact = self.calculate_market_impact(venue, suggested_stake)

        match_id = getattr(request, "match_id", "UNKNOWN")
        logger.info(f"KELLY_STAKE: Suggested ₦{suggested_stake:,.2f} for {match_id} (Drift Adj: {singularity_mult}x)")
        
        # Categorize confidence
        if f_star > 0.15:
            confidence = "PRO"
        elif f_star > 0.05:
            confidence = "AGGRESSIVE"
        else:
            confidence = "CONSERVATIVE"

        # Risk of Ruin calculation
        # Simplified formula: ((1 - (p-q))/(1 + (p-q)))^bankroll_units
        edge = (p_win * b) - q
        if edge > 0:
            ror = pow((1 - edge) / (1 + edge), 20) # 20 units of stake safety
        else:
            ror = 1.0

        return KellyRecommendation(
            optimal_fraction=round(applied_fraction, 4),
            suggested_stake=round(suggested_stake, 2),
            confidence_level=confidence,
            risk_of_ruin=round(ror, 6),
            bankroll_snapshot=current_bankroll,
            market_impact=round(impact, 4)
        )

    def _empty_recommendation(self, bankroll: float) -> KellyRecommendation:
        return KellyRecommendation(
            optimal_fraction=0.0,
            suggested_stake=0.0,
            confidence_level="CONSERVATIVE",
            risk_of_ruin=0.0,
            bankroll_snapshot=bankroll,
            market_impact=0.0
        )

# Singleton
kelly_protocol = KellyOptimizer()
