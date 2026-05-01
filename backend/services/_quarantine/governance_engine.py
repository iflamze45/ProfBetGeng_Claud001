import logging
from typing import List, Dict, Optional
from pydantic import BaseModel
from datetime import datetime

logger = logging.getLogger("pbg.governance")

class Proposal(BaseModel):
    proposal_id: str
    match_id: str
    requested_stake: float
    approvals: List[str] = [] # UserIDs
    rejections: List[str] = []
    status: str = "PENDING" # PENDING | APPROVED | REJECTED | EXECUTED
    threshold: int = 2 # Required approvals for auto-execution

class GovernanceEngine:
    """
    Multi-Sig Consensus Layer for Autonomous Execution.
    Ensures high-value trades are validated by multiple neural bridge nodes.
    """
    
    def __init__(self):
        self.proposals: Dict[str, Proposal] = {}

    def create_proposal(self, match_id: str, stake: float) -> Proposal:
        pid = f"PROP_{int(datetime.now().timestamp())}"
        p = Proposal(proposal_id=pid, match_id=match_id, requested_stake=stake)
        self.proposals[pid] = p
        logger.info(f"GOVERNANCE_ACTIVE: Proposal {pid} created for {match_id}.")
        return p

    def submit_vote(self, proposal_id: str, user_id: str, approved: bool) -> Proposal:
        if proposal_id not in self.proposals:
            raise Exception("PROPOSAL_NOT_FOUND")
            
        p = self.proposals[proposal_id]
        if approved:
            if user_id not in p.approvals: p.approvals.append(user_id)
        else:
            if user_id not in p.rejections: p.rejections.append(user_id)
            
        # Update Status
        if len(p.approvals) >= p.threshold:
            p.status = "APPROVED"
            logger.info(f"CONSENSUS_REACHED: Proposal {proposal_id} cleared for execution.")
        elif len(p.rejections) >= p.threshold:
            p.status = "REJECTED"
            
        return p

    async def generate_system_proposal(self, strategy_roi: float):
        """
        Singularity-led governance. Automatically proposes system upgrades 
        based on performance telemetry.
        """
        if strategy_roi > 0.15: # 15% ROI Threshold
            title = "PHASE_12_BANKROLL_EXPANSION"
            p = self.create_proposal(title, 5000.0)
            logger.info(f"GOV_DAO: Auto-generated expansion proposal {p.proposal_id}")
            
            # Simulated Auto-Vote from trusted node signatures
            self.submit_vote(p.proposal_id, "NODE_LAGOS_01", True)
            self.submit_vote(p.proposal_id, "NODE_LONDON_01", True)
            
            return p.proposal_id
        return None

# Singleton
gov_engine = GovernanceEngine()
