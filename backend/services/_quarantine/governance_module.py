import logging
from typing import List, Dict, Any, Optional
from pydantic import BaseModel
from datetime import datetime, timedelta

logger = logging.getLogger("pbg.governance")

class Proposal(BaseModel):
    id: str
    region: str # "Lagos", "London", "Tokyo"
    param_name: str # e.g., "MAX_EXPOSURE"
    proposed_value: Any
    votes_for: float = 0.0
    votes_against: float = 0.0
    status: str = "OPEN" # "OPEN", "PASSED", "REJECTED", "EXECUTED"
    created_at: datetime = datetime.now()
    deadline: datetime = datetime.now() + timedelta(hours=24)

class GovernanceModule:
    """
    Phase 19: Decentralized control of Regional Shards.
    """
    def __init__(self):
        self.proposals: Dict[str, Proposal] = {}
        self.voting_power: Dict[str, float] = {
            "BlackRock_Syndicate": 450000.0,
            "Nexus_Alpha_Fund": 280000.0,
            "Lagos_Quant_Lab": 120000.0
        }
        self.seed_mock_proposals()

    def seed_mock_proposals(self):
        p1 = Proposal(
            id="PROP-001",
            region="Lagos",
            param_name="MAX_REGIONAL_EXPOSURE",
            proposed_value=5000000.0, # 5M NGN
            votes_for=150000.0
        )
        self.proposals[p1.id] = p1

    def get_voter_weight(self, voter_name: str) -> float:
        """Dynamically calculates weight based on active liquidity provision."""
        base_power = self.voting_power.get(voter_name, 0.0)
        # In P19, large providers get a 1.2x boost to encourage governance participation
        return base_power * 1.2 if base_power > 300000 else base_power

    def cast_vote(self, proposal_id: str, voter_name: str, vote_type: str) -> bool:
        if proposal_id not in self.proposals:
            return False
            
        power = self.get_voter_weight(voter_name)
        if power == 0: return False
            
        proposal = self.proposals[proposal_id]
        if vote_type == "FOR": proposal.votes_for += power
        else: proposal.votes_against += power
            
        # Check Quorum (Simulated 1M weight quorum)
        if (proposal.votes_for + proposal.votes_against) > 800000:
            proposal.status = "PASSED" if proposal.votes_for > proposal.votes_against else "REJECTED"
            
        logger.info(f"VOTE_CAST: {voter_name} weight {power:.0f} cast on {proposal_id}")
        return True

    def execute_proposal(self, proposal_id: str):
        proposal = self.proposals.get(proposal_id)
        if not proposal or proposal.status != "PASSED":
            return False
            
        logger.info(f"EXECUTING_GOVERNANCE: Applying {proposal.param_name} to {proposal.region}")
        
        if "REBALANCE" in proposal.param_name:
            # Concrete move logic
            source = "LONDON_VAULT" if proposal.region == "Lagos" else "LAGOS_VAULT"
            logger.warning(f"REBALANCE_EXECUTION: Moving {proposal.proposed_value} NGN from {source} to {proposal.region}")
            
        proposal.status = "EXECUTED"
        return True

    def get_proposals_list(self) -> List[Dict[str, Any]]:
        return [p.dict() for p in self.proposals.values()]

    def get_gov_status(self) -> dict:
        return {
            "total_proposals": len(self.proposals),
            "voting_power": self.voting_power,
            "active_proposals": self.get_proposals_list()
        }

# Global Instance
governance_core = GovernanceModule()
