"""
CLV (Closing Line Value) Service — promoted from _quarantine/clv_tracker.py (v0.7.3).
Measures entry quality by comparing execution odds to closing odds (deterministic).
Changes from quarantine: compute_clv() added (deterministic), log_market_closure() dropped (random), singleton removed.
"""
import logging
from pydantic import BaseModel

logger = logging.getLogger("pbg.clv_service")


class CLVReport(BaseModel):
    match_id: str
    execution_odds: float
    closing_odds: float
    alpha_beat: float


class CLVService:
    def compute_clv(
        self,
        execution_odds: float,
        closing_odds: float,
        match_id: str = "unknown",
    ) -> CLVReport:
        alpha_beat = round((execution_odds / closing_odds) - 1.0, 4)
        return CLVReport(
            match_id=match_id,
            execution_odds=execution_odds,
            closing_odds=closing_odds,
            alpha_beat=alpha_beat,
        )
