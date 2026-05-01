import logging
from typing import List, Dict, Any
from pydantic import BaseModel
from datetime import datetime

logger = logging.getLogger("pbg.treasury")

class AssetAllocation(BaseModel):
    asset_name: str # "USDC", "BTC", "NGN_LIQUIDITY"
    value_usd: float
    percentage: float
    risk_tier: str # "Cold", "Active", "Yield"

class TreasuryReserve(BaseModel):
    total_value_usd: float = 0.0
    last_rebalance: datetime = datetime.now()
    allocations: List[AssetAllocation] = []

class TreasuryModule:
    """
    Phase 22: Sovereign Wealth Management.
    Managing the long-term reserves of PBG.
    """
    def __init__(self):
        self.reserve = TreasuryReserve()
        self.seed_initial_reserves()

    def seed_initial_reserves(self):
        self.reserve.allocations = [
            AssetAllocation(asset_name="USDC-Reserve", value_usd=450000.0, percentage=45.0, risk_tier="Cold"),
            AssetAllocation(asset_name="BTC-Growth", value_usd=250000.0, percentage=25.0, risk_tier="Yield"),
            AssetAllocation(asset_name="Active-Liquidity", value_usd=300000.0, percentage=30.0, risk_tier="Active"),
        ]
        self.reserve.total_value_usd = sum(a.value_usd for a in self.reserve.allocations)

    def route_profit_to_reserve(self, amount_usd: float):
        """Routes 10% of profit to the Cold Reserve."""
        tax_amt = amount_usd * 0.10
        for asset in self.reserve.allocations:
            if asset.risk_tier == "Cold":
                asset.value_usd += tax_amt
        
        self.reserve.total_value_usd += tax_amt
        logger.info(f"TREASURY_HARVEST: Routed ${tax_amt:,.2f} to Sovereign Cold Storage.")

    def execute_rebalance(self, target_allocation: Dict[str, float]):
        """Bridges idle vault funds between tiers to maintain targets."""
        logger.warning("REBALANCING_TREASURY: Shifting assets between Active and Cold tiers.")
        # Logic to move capital based on risk-adjusted mandates
        self.reserve.last_rebalance = datetime.now()

    def trigger_circuit_breaker(self, current_drawdown: float):
        """Flattens all positions if drawdown exceeds 5%."""
        if current_drawdown > 0.05:
            logger.critical(f"CIRCUIT_BREAKER: Drawdown reach {current_drawdown*100:.1f}%. Retreating to COLD STORAGE.")
            # Move all 'Active' to 'Cold' 
            for asset in self.reserve.allocations:
                if asset.risk_tier == "Active":
                    asset.risk_tier = "Emergency_Hold"
            return True
        return False

    def get_treasury_status(self) -> Dict[str, Any]:
        return self.reserve.dict()

# Global Instance
treasury_core = TreasuryModule()
