"""
RiskEngine — M3 Phase 1
Computes deterministic risk metrics from a ConvertedTicket.
No external calls — pure math, always synchronous.
"""
import math
from collections import Counter
from typing import List, Optional

from pydantic import BaseModel

from ..models import ConvertedTicket, NormalizedSelection


class RiskMetrics(BaseModel):
    variance: float
    expected_value: float
    kelly_fraction: float
    combined_implied_probability: float
    correlation_exposure: float
    selection_count: int
    avg_odds: float
    avg_val_gap_score: float = 0.0


class RiskEngine:
    @staticmethod
    def compute(
        ticket: ConvertedTicket,
        normalized: Optional[List[NormalizedSelection]] = None,
    ) -> RiskMetrics:
        odds = [s.odds for s in ticket.selections]
        n = len(odds)

        if n == 0:
            return RiskMetrics(
                variance=0.0,
                expected_value=0.0,
                kelly_fraction=0.0,
                combined_implied_probability=0.0,
                correlation_exposure=0.0,
                selection_count=0,
                avg_odds=0.0,
                avg_val_gap_score=0.0,
            )

        avg = sum(odds) / n
        variance = math.sqrt(sum((o - avg) ** 2 for o in odds) / n)

        # Use provided total_odds if available, else product
        if ticket.total_odds is not None:
            total_odds = ticket.total_odds
        else:
            total_odds = 1.0
            for o in odds:
                total_odds *= o

        cip = 1.0 / total_odds if total_odds > 0 else 0.0

        # EV per unit stake using naive 50/50 prior per leg.
        # This avoids the tautology (cip*total_odds - 1 = 0 always).
        # Negative EV = the house edge is visible at these odds.
        naive_prob = 0.5 ** n
        ev = naive_prob * total_odds - 1.0

        # Kelly criterion using naive_prob as the probability estimate.
        # b = net decimal odds (profit per unit staked)
        b = total_odds - 1.0
        if b <= 0:
            kelly = 0.0
        else:
            q = 1.0 - naive_prob
            kelly = max(0.0, min(1.0, (naive_prob * b - q) / b))

        # Correlation exposure: fraction of selections sharing a repeated event_id
        event_ids = [s.event_id for s in ticket.selections]
        counts = Counter(event_ids)
        duplicated = sum(c for c in counts.values() if c > 1)
        correlation_exposure = duplicated / n if n > 0 else 0.0

        avg_val_gap = 0.0
        if normalized:
            gaps = [s.val_gap_score for s in normalized if s.val_gap_score != 0.0]
            if gaps:
                avg_val_gap = round(sum(gaps) / len(gaps), 4)

        return RiskMetrics(
            variance=variance,
            expected_value=ev,
            kelly_fraction=kelly,
            combined_implied_probability=cip,
            correlation_exposure=correlation_exposure,
            selection_count=n,
            avg_odds=avg,
            avg_val_gap_score=avg_val_gap,
        )
