import asyncio
import logging
import httpx
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

# --- Data Models (Internal Normalized Schema) ---

class NormalizedOdds(object):
    def __init__(self, bookmaker: str, match_id: str, market_type: str, selection: str, price: float, timestamp: datetime):
        self.bookmaker = bookmaker
        self.match_id = match_id
        self.market_type = market_type
        self.selection = selection
        self.price = price
        self.timestamp = timestamp

    def to_dict(self) -> Dict[str, Any]:
        return {
            "bookmaker": self.bookmaker,
            "match_id": self.match_id,
            "market_type": self.market_type,
            "selection": self.selection,
            "price": self.price,
            "timestamp": self.timestamp.isoformat()
        }

# --- Provider Interfaces ---

class BaseIngestionProvider(ABC):
    def __init__(self, name: str, api_key: Optional[str] = None):
        self.name = name
        self.api_key = api_key

    @abstractmethod
    async def fetch_live_markets(self) -> List[NormalizedOdds]:
        """Fetch and normalize live markets from the specific provider."""
        pass


class TheOddsAPIProvider(BaseIngestionProvider):
    def __init__(self, api_key: str):
        super().__init__("TheOddsAPI", api_key)
        self.base_url = "https://api.the-odds-api.com/v4/sports/upcoming/odds"

    async def fetch_live_markets(self) -> List[NormalizedOdds]:
        if not self.api_key:
            logger.warning(f"[{self.name}] No API key provided, skipping ingestion.")
            return []
            
        normalized_data = []
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(
                    self.base_url,
                    params={
                        "apiKey": self.api_key,
                        "regions": "eu,uk",
                        "markets": "h2h,totals,btts",
                        "oddsFormat": "decimal"
                    }
                )
                response.raise_for_status()
                data = response.json()
                
                for match in data:
                    match_id = match.get("id")
                    for bookmaker in match.get("bookmakers", []):
                        bm_name = bookmaker.get("title")
                        for market in bookmaker.get("markets", []):
                            market_type = market.get("key")
                            for outcome in market.get("outcomes", []):
                                normalized_data.append(
                                    NormalizedOdds(
                                        bookmaker=bm_name,
                                        match_id=match_id,
                                        market_type=self._normalize_market_key(market_type),
                                        selection=outcome.get("name"),
                                        price=outcome.get("price"),
                                        timestamp=datetime.utcnow()
                                    )
                                )
        except Exception as e:
            logger.error(f"[{self.name}] Failed to fetch active markets: {e}")
        
        return normalized_data

    def _normalize_market_key(self, raw_key: str) -> str:
        # Normalizer logic mapping variations (GG <-> BTTS)
        mapping = {
            "h2h": "1X2",
            "totals": "OVER_UNDER",
            "btts": "GG_NG"
        }
        return mapping.get(raw_key, raw_key.upper())


class AfricanBookmakerScraper(BaseIngestionProvider):
    """
    Reverse-engineered public API ingestion for platforms like SportyBet, Bet9ja without official API wrappers.
    Currently acts as a mock/simulator pending specific target endpoints.
    """
    def __init__(self):
        super().__init__("AfricanMarketScraper")

    async def fetch_live_markets(self) -> List[NormalizedOdds]:
        # Mocking localized high-frequency liquidity
        logger.debug(f"[{self.name}] Polling localized African broker endpoints...")
        await asyncio.sleep(0.5)
        return [
            NormalizedOdds("SportyBet", "fixture_991", "1X2", "Home", 2.15, datetime.utcnow()),
            NormalizedOdds("Bet9ja", "fixture_991", "1X2", "Home", 2.10, datetime.utcnow()),
            NormalizedOdds("SportyBet", "fixture_991", "GG_NG", "GG", 1.85, datetime.utcnow())
        ]


# --- Central Ingestion Engine ---

class DataIngestionEngine:
    def __init__(self):
        self.providers: List[BaseIngestionProvider] = []
        self._is_running = False
        self.latest_odds: Dict[str, List[NormalizedOdds]] = {} # match_id -> odds

    def register_provider(self, provider: BaseIngestionProvider):
        self.providers.append(provider)
        logger.info(f"[Ingestion Engine] Registered provider: {provider.name}")

    async def start_polling(self, interval_seconds: int = 30):
        self._is_running = True
        logger.info("[Ingestion Engine] Starting centralized data ingestion loop.")
        while self._is_running:
            tasks = [provider.fetch_live_markets() for provider in self.providers]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Reset pipeline context for new cycle
            ingested_count = 0
            
            for provider_result in results:
                if isinstance(provider_result, Exception):
                    logger.error(f"[Ingestion Engine] Provider task failed: {provider_result}")
                    continue
                
                for odds in provider_result:
                    if odds.match_id not in self.latest_odds:
                        self.latest_odds[odds.match_id] = []
                    
                    # Store or update the latest price
                    # (In production, push to a timeseries DB or Redis instead of local dict)
                    self.latest_odds[odds.match_id].append(odds)
                    ingested_count += 1
            
            logger.info(f"[Ingestion Engine] Cycle complete. Ingested {ingested_count} edge data points.")
            
            # Analyze for arbitrage/value using the newly ingested data
            self._trigger_value_discovery()
            
            await asyncio.sleep(interval_seconds)

    def _trigger_value_discovery(self):
        """Passes fresh normalized data to the value discovery / arbitrage pipeline."""
        from backend.services.value_discovery import discovery_hub
        for match_id, odds_list in self.latest_odds.items():
            if not odds_list:
                continue
            # Derive team name from match metadata if available, else use match_id
            teams = getattr(odds_list[0], "teams", match_id)
            discovery_hub.process_ingested_odds(match_id, odds_list, teams=teams)

    def stop(self):
        self._is_running = False
        logger.info("[Ingestion Engine] Data ingestion loop stopped.")

# --- Global Instance ---
from backend.config import get_settings
_settings = get_settings()

ingestion_engine = DataIngestionEngine()

if _settings.the_odds_api_key:
    ingestion_engine.register_provider(TheOddsAPIProvider(api_key=_settings.the_odds_api_key))
else:
    logger.warning("No `the_odds_api_key` found in environment. TheOddsAPI fallback disabled.")

ingestion_engine.register_provider(AfricanBookmakerScraper())
