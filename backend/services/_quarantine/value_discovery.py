import asyncio
import logging
from collections import defaultdict
from datetime import datetime
from typing import List, Dict, Optional
from pydantic import BaseModel

logger = logging.getLogger("pbg.value_discovery")


class MarketSignal(BaseModel):
    match_id: str
    teams: str
    market: str
    local_odds: float
    global_odds: float
    value_score: float
    signal_type: str  # "VALUE" | "ARB" | "STALE"
    timestamp: datetime = datetime.now()


class ValueDiscoveryService:
    """
    Value Discovery Hub.
    Processes real ingested odds from the DataIngestionEngine to detect
    value bets and arbitrage opportunities across bookmakers.
    Falls back to simulation when no live data is available.
    """

    def __init__(self):
        self.active_signals: List[MarketSignal] = []
        self._is_running = False
        self._new_signal_callbacks = []

    def on_new_signal(self, callback):
        """Register a callback triggered whenever a new signal is detected."""
        self._new_signal_callbacks.append(callback)

    def _emit(self, signal: MarketSignal):
        self.active_signals.insert(0, signal)
        self.active_signals = self.active_signals[:20]
        logger.info(f"VDH_SIGNAL: {signal.signal_type} | {signal.teams} | edge={signal.value_score:.3f}")
        for cb in self._new_signal_callbacks:
            try:
                cb(signal)
            except Exception as e:
                logger.warning(f"VDH callback error: {e}")

    def calculate_value(self, local: float, global_baseline: float) -> Dict:
        """
        Value = local odds offer better expected value than the global fair price.
        EV = (local_odds * implied_prob_from_global) - 1
        """
        if global_baseline <= 0:
            return {"score": 0.0, "type": "NEUTRAL"}
        implied_prob = 1 / global_baseline
        ev = (local * implied_prob) - 1
        if ev > 0.05:
            return {"score": round(ev, 4), "type": "VALUE"}
        if ev > 0:
            return {"score": round(ev, 4), "type": "STALE"}
        return {"score": round(ev, 4), "type": "NEUTRAL"}

    def process_ingested_odds(self, match_id: str, odds_list, teams: Optional[str] = None):
        """
        Called by DataIngestionEngine after each ingestion cycle with fresh odds.
        Detects value and arbitrage across bookmakers for a single match.
        """
        # Group by market_type + selection
        by_market: Dict[str, Dict[str, List]] = defaultdict(lambda: defaultdict(list))
        for o in odds_list:
            by_market[o.market_type][o.selection].append((o.bookmaker, o.price))

        for market_type, selections in by_market.items():
            prices_per_selection = {}
            for sel, bm_prices in selections.items():
                best_price = max(p for _, p in bm_prices)
                avg_price = sum(p for _, p in bm_prices) / len(bm_prices)
                prices_per_selection[sel] = {"best": best_price, "avg": avg_price}

            # --- Value detection: best local vs average global baseline ---
            for sel, prices in prices_per_selection.items():
                analysis = self.calculate_value(prices["best"], prices["avg"])
                if analysis["type"] in ("VALUE", "STALE"):
                    signal = MarketSignal(
                        match_id=match_id,
                        teams=teams or match_id,
                        market=f"{market_type}_{sel.upper().replace(' ', '_')}",
                        local_odds=prices["best"],
                        global_odds=round(prices["avg"], 3),
                        value_score=analysis["score"],
                        signal_type=analysis["type"],
                        timestamp=datetime.utcnow(),
                    )
                    self._emit(signal)

            # --- Arbitrage detection: sum of (1/best_price) across all selections < 1 ---
            if len(prices_per_selection) >= 2:
                inv_sum = sum(1 / v["best"] for v in prices_per_selection.values() if v["best"] > 0)
                if inv_sum < 1.0:
                    profit_margin = round(1 - inv_sum, 4)
                    arb_signal = MarketSignal(
                        match_id=match_id,
                        teams=teams or match_id,
                        market=f"ARB_{market_type}",
                        local_odds=round(1 / inv_sum, 3),
                        global_odds=1.0,
                        value_score=profit_margin,
                        signal_type="ARB",
                        timestamp=datetime.utcnow(),
                    )
                    self._emit(arb_signal)

    async def start_polling(self, interval: int = 30):
        """
        Background loop. When live ingestion is active, signals come via
        process_ingested_odds(). This loop only runs simulation when no
        real data has been ingested yet.
        """
        self._is_running = True
        logger.info("VDH: Value Discovery Engine Started")

        _SIM_MATCHES = [
            {"id": "LIV_ARS", "teams": "Liverpool vs Arsenal", "market": "1X2_HOME", "base": 2.10},
            {"id": "RMA_BAR", "teams": "Real Madrid vs Barcelona", "market": "O2.5_GOALS", "base": 1.85},
            {"id": "MCI_MUN", "teams": "Man City vs Man Utd", "market": "BTTS_YES", "base": 1.72},
        ]

        while self._is_running:
            # Only simulate if no real data has arrived from the ingestion engine
            from backend.services.data_ingestion import ingestion_engine
            has_real_data = bool(ingestion_engine.latest_odds)

            if not has_real_data:
                import random
                for m in _SIM_MATCHES:
                    g = m["base"]
                    l = round(g + random.uniform(-0.1, 0.4), 2)
                    analysis = self.calculate_value(l, g)
                    if analysis["type"] in ("VALUE", "STALE"):
                        self._emit(MarketSignal(
                            match_id=m["id"],
                            teams=m["teams"],
                            market=m["market"],
                            local_odds=l,
                            global_odds=g,
                            value_score=analysis["score"],
                            signal_type=analysis["type"],
                            timestamp=datetime.utcnow(),
                        ))

            await asyncio.sleep(interval)

    def stop(self):
        self._is_running = False
        logger.info("VDH: Value Discovery Engine Stopped")


# Singleton instance
discovery_hub = ValueDiscoveryService()
