import logging
import random
from enum import Enum
from typing import Dict

logger = logging.getLogger("pbg.veil")

class ProxyType(Enum):
    DATACENTER = "dc"
    RESIDENTIAL = "res"
    MOBILE = "mob"

class ProxyVeil:
    """
    Sovereign Infrastructure: Advanced anti-bot proxy controller.
    Rotates infrastructure and tunnel types to evade bookmaker detection.
    """
    
    def __init__(self):
        self.risk_scores: Dict[str, float] = {} # venue -> suspicion_score

    def get_optimal_proxy(self, venue: str) -> ProxyType:
        """
        Determines the safest proxy type for the current target.
        """
        score = self.risk_scores.get(venue, 0.0)
        
        if score > 0.8:
            logger.warning(f"VEIL_CORE: Extreme suspicion on {venue}. Routing via MOBILE (LTE) Ghost Tunnel.")
            return ProxyType.MOBILE
        elif score > 0.4:
            logger.info(f"VEIL_CORE: Elevated suspicion on {venue}. Routing via RESIDENTIAL Static.")
            return ProxyType.RESIDENTIAL
        
        return ProxyType.DATACENTER

    def record_detection_event(self, venue: str):
        """
        Increment risk score when a 403 or captcha is detected.
        """
        current = self.risk_scores.get(venue, 0.0)
        self.risk_scores[venue] = min(1.0, current + 0.2)
        logger.error(f"VEIL_CORE: Detection event on {venue}. Suspect Score: {self.risk_scores[venue]:.2f}")

# Singleton
veil = ProxyVeil()
