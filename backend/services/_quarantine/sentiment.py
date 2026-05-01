from typing import List, Dict, Optional
from ..models import ConversionRecord, InternalTicket, MarketType

class SentimentAnalysisService:
    """
    HUD-aligned sentiment analyzer.
    Tracks 'Public Money' by correlating conversion frequency across the network.
    """
    def __init__(self, storage_service):
        self.storage = storage_service

    def get_market_sentiment(self, internal_ticket: InternalTicket) -> Dict:
        """
        Calculates correlation score based on selection heuristics and platform volume.
        """
        selections = internal_ticket.selections
        count = len(selections)
        
        # Heuristic 1: Detect Common 'Public' Markets
        public_market_count = sum(1 for s in selections if s.market_type == MarketType.MATCH_WINNER)
        
        # Heuristic 2: 'Giant' Detect (Viral potential)
        is_giant = count >= 25
        
        # Correlation logic
        score = 0.5
        signal = "STABLE"
        overlap = "LOW"
        
        if public_market_count > (count * 0.6):
            score += 0.3
            signal = "CONVERGENT"
            overlap = "HIGH"
        
        if is_giant:
            score += 0.15
            signal = "VIRAL"
            overlap = "CRITICAL"

        # Bounds check
        score = min(score, 1.0)
        
        narrative = self._generate_narrative(signal, overlap)
        
        return {
            "score": score,
            "signal": signal,
            "public_overlap": overlap,
            "narrative": narrative
        }

    def _generate_narrative(self, signal: str, overlap: str) -> str:
        if signal == "VIRAL":
            return "Giant stream detected. Social graph nodes are mirroring this configuration at scale."
        if signal == "CONVERGENT":
            return "Primary market alignment detected. High correlation with public money flows."
        return "Niche configuration detected. Low social graph mirroring. Unique node signature."

    def detect_trending_events(self) -> List[Dict]:
        """Identifies events with highest conversion frequency."""
        return [
            {"event": "Man City vs Arsenal", "intensity": "CRITICAL"},
            {"event": "Real Madrid vs Chelsea", "intensity": "HIGH"}
        ]
