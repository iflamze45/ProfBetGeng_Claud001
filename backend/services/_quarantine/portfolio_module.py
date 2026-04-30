import logging
from typing import List, Dict, Any
from pydantic import BaseModel
from ..models import ExecutionResult, TicketStatus

logger = logging.getLogger("pbg.portfolio")

class PortfolioStats(BaseModel):
    total_staked: float = 0.0
    total_returns: float = 0.0
    active_risk: float = 0.0
    infrastructure_costs: float = 0.0 # Phase 15 Integration
    market_making_yield: float = 0.0 # Phase 17
    api_data_revenue: float = 0.0 # Phase 18

class PortfolioIntelligence:
    """
    Analyzes global financial health across all regional nodes.
    Tracks 'Compute Rent' and decommissioning triggers.
    """
    
    def __init__(self):
        self.stats = PortfolioStats()

    def update_stats(self, stake: float, returns: float, active_shard_count: int = 1):
        self.stats.total_staked += stake
        self.stats.total_returns += returns
        
        # Infrastructure Rent: Dynamic scaling based on active mesh size
        base_rent = 1250.0 # NGN base per node
        calculated_rent = base_rent * active_shard_count
        self.stats.infrastructure_costs += calculated_rent
        
        net = self.stats.total_returns - (self.stats.total_staked + self.stats.infrastructure_costs)
        logger.info(f"PORTFOLIO_CORE: Net Liquidity (After ₦{calculated_rent:,.2f} Mesh Rent): ₦{net:,.2f}")

        # Phase 15: Expansion Trigger
        from .singularity_engine import singularity_core
        singularity_core.evaluate_mesh_expansion(current_profit=net, volume_saturation=0.90)

    def check_node_viability(self, node_id: str, lifetime_yield: float, lifetime_cost: float) -> bool:
        """
        Determines if a node is profitable enough to continue existing.
        """
        if lifetime_yield < (lifetime_cost * 1.05): # Must maintain 5% margin
            logger.warning(f"NODE_REAPER: Node {node_id} failed viability check. Yield: {lifetime_yield} vs Cost: {lifetime_cost}")
            return False
        return True

    def settle_ticket(self, result: ExecutionResult):
        """
        Intelligence Update: Definitive tracking of ticket outcomes.
        """
        self.stats.total_returns += result.payout_actual
        
        # Log precision/alpha beat
        alpha_beat = result.consensus_clv # Closing Value
        
        status_code = "ALPHA_BEAT" if alpha_beat > 0 else "DECAY"
        logger.info(f"SETTLEMENT_FINAL: Ticket {result.ticket_id} settled. ROI: {result.roi_actual*100:.2f}% | CLV_{status_code}: {alpha_beat*100:.2f}%")

# Singleton
portfolio_core = PortfolioIntelligence()
