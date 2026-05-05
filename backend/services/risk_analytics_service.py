"""
Risk Analytics Service — promoted from _quarantine/risk_analytics.py (v0.7.3).
Provides quantitative portfolio risk metrics (Sharpe, Sortino, drawdown, volatility, alpha).
Changes from quarantine: RiskMetrics → PortfolioRiskMetrics, DynamicHedging dropped, singletons removed.
"""
import numpy as np
import logging
from typing import List
from pydantic import BaseModel

logger = logging.getLogger("pbg.risk_analytics")


class PortfolioRiskMetrics(BaseModel):
    sharpe_ratio: float
    sortino_ratio: float
    max_drawdown: float
    volatility: float
    alpha: float
    correlation_penalty: float = 0.0
    value_gap_avg: float = 0.0
    leg_risks: List[float] = []


class RiskAnalyticsService:
    def __init__(self, risk_free_rate: float = 0.05):
        self.risk_free_rate = risk_free_rate

    def calculate_metrics(self, returns: List[float]) -> PortfolioRiskMetrics:
        if len(returns) < 5:
            return self._empty_metrics()

        returns_arr = np.array(returns)
        mean_return = float(np.mean(returns_arr))
        vol = float(np.std(returns_arr))

        excess_return = mean_return - (self.risk_free_rate / 365)
        sharpe = excess_return / vol if vol != 0 else 0.0

        downside = returns_arr[returns_arr < 0]
        downside_std = float(np.std(downside)) if len(downside) > 0 else 0.001
        sortino = excess_return / downside_std

        cumulative = np.cumsum(returns_arr)
        peak = np.maximum.accumulate(cumulative)
        drawdown = peak - cumulative
        max_dd = float(np.max(drawdown)) if len(drawdown) > 0 else 0.0

        return PortfolioRiskMetrics(
            sharpe_ratio=round(sharpe, 3),
            sortino_ratio=round(sortino, 3),
            max_drawdown=round(max_dd, 3),
            volatility=round(vol, 3),
            alpha=round(mean_return * 1.5, 3),
            value_gap_avg=round(mean_return, 3),
        )

    def _empty_metrics(self) -> PortfolioRiskMetrics:
        return PortfolioRiskMetrics(
            sharpe_ratio=0.0,
            sortino_ratio=0.0,
            max_drawdown=0.0,
            volatility=0.0,
            alpha=0.0,
        )
