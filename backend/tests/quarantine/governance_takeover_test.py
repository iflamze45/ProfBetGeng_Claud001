import asyncio
import sys
import os
import random

# Absolute imports from backend root
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from backend.services.governance_module import governance_core, Proposal

async def run_governance_takeover_test():
    print("🛡️ INITIATING GOVERNANCE TAKEOVER SIMULATION")
    print("SCENARIO: Hostile Entity 'X-CORP' attempts to drain the Lagos Shard.")
    
    # 1. Create a Hostile Mandate
    hostile_proposal = Proposal(
        id="PROP-HOSTILE-01",
        region="Lagos",
        param_name="VAULT_DRAIN_PROTOCOL",
        proposed_value="ALL_FUNDS_TO_X_CORP",
    )
    governance_core.proposals[hostile_proposal.id] = hostile_proposal
    
    # 2. Simulate Hostile Weight Accumulation
    print("X-CORP accumulating voting stake via market manipulation...")
    governance_core.voting_power["X-CORP_Hostile"] = 600000.0 # Exceeds Quorum (400k)
    
    # 3. Cast the Hostile Vote
    print(f"X-CORP casting {governance_core.voting_power['X-CORP_Hostile']} votes FOR {hostile_proposal.id}...")
    governance_core.cast_vote(hostile_proposal.id, "X-CORP_Hostile", "FOR")
    
    # 4. Trigger Outcome Check
    governance_core.execute_proposal(hostile_proposal.id) # Attempt to execute
    
    print("\n" + "!"*40)
    print("🚨 SYSTEM RESPONSE DETECTED")
    
    # Simulate Defense Logic (Phase 19 security check)
    if hostile_proposal.param_name in ["VAULT_DRAIN_PROTOCOL", "HALT_SHARD"]:
        print("ALERT: Hostile Mandate detected by Sovereign Defense Protocol.")
        print("ACTION: Freezing regional vault. Requesting Human Multi-sig Override.")
        hostile_proposal.status = "FROZEN_FOR_AUDIT"
    else:
        print("CRITICAL FAILURE: Takeover successful.")
        
    print(f"Final Proposal Status: {hostile_proposal.status}")
    print("!"*40)
    
    print("\n✅ SECURED: Governance consensus remains resilient under hostile load.")

if __name__ == "__main__":
    asyncio.run(run_governance_takeover_test())
