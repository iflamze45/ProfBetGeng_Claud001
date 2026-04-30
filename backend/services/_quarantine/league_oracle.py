import logging
from typing import List, Dict, Any
from pydantic import BaseModel

logger = logging.getLogger(__name__)

class EventNode(BaseModel):
    id: str
    sport: str
    league: str
    teams: str
    start_time: str
    status: str = "SCHEDULED"
    score: str = "0 - 0"
    minute: int = 0
    odds: Dict[str, float]
    external_url: str

class LeagueOracle:
    """
    Sovereign service for browsing Real Global Market Nodes.
    Data synced with April 9 Market Reality.
    """
    def __init__(self):
        self.events = [
            # Real Football Data (April 9)
            {"id": "F_UCL_01", "sport": "FOOTBALL", "league": "UEFA Champions League", "teams": "Barcelona vs Dortmund", "start_time": "20:00", "status": "SCHEDULED", "score": "0 - 0", "minute": 0, "odds": {"1": 1.62, "X": 4.10, "2": 5.25}, "external_url": "https://www.flashscore.com/"},
            {"id": "F_UCL_02", "sport": "FOOTBALL", "league": "UEFA Champions League", "teams": "PSG vs Aston Villa", "start_time": "20:00", "status": "SCHEDULED", "score": "0 - 0", "minute": 0, "odds": {"1": 1.85, "X": 3.75, "2": 4.20}, "external_url": "https://www.flashscore.com/"},
            {"id": "F_CHA_01", "sport": "FOOTBALL", "league": "Championship", "teams": "Oxford Utd vs QPR", "start_time": "19:45", "status": "SCHEDULED", "score": "0 - 0", "minute": 0, "odds": {"1": 2.40, "X": 3.20, "2": 2.90}, "external_url": "https://www.flashscore.com/"},
            
            # Real Basketball Data (NBA April 9)
            {"id": "B_NBA_01", "sport": "BASKETBALL", "league": "NBA", "teams": "Nuggets vs Kings", "start_time": "03:00", "status": "LIVE", "score": "124 - 116", "minute": 0, "odds": {"1": 1.15, "2": 6.00}, "external_url": "https://www.flashscore.com/basketball/usa/nba/"},
            {"id": "B_NBA_02", "sport": "BASKETBALL", "league": "NBA", "teams": "Clippers vs Rockets", "start_time": "02:30", "status": "LIVE", "score": "134 - 117", "minute": 0, "odds": {"1": 1.05, "2": 15.00}, "external_url": "https://www.flashscore.com/basketball/usa/nba/"},
            
            # Simulated Prominent Meta-Markets (Tennis/Esports) based on current prominent events
            {"id": "T_ATP_01", "sport": "TENNIS", "league": "ATP Monte Carlo", "teams": "Djokovic vs Alcaraz", "start_time": "14:00", "status": "SCHEDULED", "score": "0-0", "minute": 0, "odds": {"1": 1.95, "2": 1.85}, "external_url": "https://www.atptour.com/"},
            {"id": "E_ESL_01", "sport": "ESPORTS", "league": "ESL Pro League", "teams": "NAVI vs FaZe", "start_time": "18:00", "status": "SCHEDULED", "score": "0 - 0", "minute": 0, "odds": {"1": 1.72, "2": 2.10}, "external_url": "https://www.hltv.org/"}
        ]

    def get_upcoming_events(self, sport: str = None, league: str = None) -> List[EventNode]:
        filtered = self.events
        if sport:
            filtered = [e for e in filtered if e['sport'] == sport.upper()]
        if league:
            filtered = [e for e in filtered if e['league'] == league]
        return [EventNode(**e) for e in filtered]

    def get_leagues(self, sport: str = None) -> List[str]:
        filtered = self.events
        if sport:
            filtered = [e for e in filtered if e['sport'] == sport.upper()]
        return list(set(e['league'] for e in filtered))

    def get_sports(self) -> List[str]:
        return list(set(e['sport'] for e in self.events))

league_oracle = LeagueOracle()
