import logging
import time
from typing import Dict, Optional
from pydantic import BaseModel

logger = logging.getLogger("pbg.gateway")

class APIKey(BaseModel):
    key: str
    tier: str # "BASIC" | "PRO" | "INSTITUTIONAL"
    requests_today: int = 0
    last_request: float = 0

class InstitutionalGateway:
    """
    Phase 18: Institutional API.
    Monetizes neural fair-odds data via managed endpoints.
    """
    def __init__(self):
        self.keys: Dict[str, APIKey] = {
            "test-basic": APIKey(key="test-basic", tier="BASIC"),
            "test-institutional": APIKey(key="test-institutional", tier="INSTITUTIONAL")
        }
        self.api_revenue_total: float = 0.0

    def validate_request(self, key_str: str) -> bool:
        if key_str not in self.keys:
            return False
        
        key = self.keys[key_str]
        # Tier-based Rate Limiting (Simulated)
        now = time.time()
        if key.tier == "BASIC" and (now - key.last_request) < 1.0:
            return False # 1 req/sec
            
        key.requests_today += 1
        key.last_request = now
        
        # Charge per request
        fee = 50.0 if key.tier == "INSTITUTIONAL" else 5.0
        self.api_revenue_total += fee
        
        return True

    def get_alpha_feed(self, key: str):
        if not self.validate_request(key):
            return {"error": "UNAUTHORIZED_OR_RATE_LIMIT"}
            
        from backend.services.alpha_engine import alpha_pricer
        # In actual implementation, we'd pass real odds.
        return alpha_pricer.calculate_fair_value({"Consensus": 2.10})

    def get_gateway_status(self) -> dict:
        return {
            "total_revenue": self.api_revenue_total,
            "active_keys": len(self.keys),
            "tiers": {
                "BASIC": len([k for k in self.keys.values() if k.tier == "BASIC"]),
                "INSTITUTIONAL": len([k for k in self.keys.values() if k.tier == "INSTITUTIONAL"])
            }
        }

# Global instance
gateway = InstitutionalGateway()
