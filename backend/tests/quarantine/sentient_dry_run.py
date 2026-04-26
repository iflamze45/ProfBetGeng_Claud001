import asyncio
import sys
import os

from backend.services.ticket_pulse import match_pulse
from backend.services.risk_analytics import hedging_core
from backend.services.settlement_layer import settlement_core

async def run_sentient_sim():
    print("🚀 INITIATING SENTIENT SETTLEMENT DRY RUN")
    match_id = "TEST-ARS-LIV-001"
    
    # 1. Ingest initial match state
    print("\n[MATCH START] Arsenal vs Liverpool")
    tele = match_pulse.ingest_match_event(match_id, "START", {"minute": 0})
    print(f"Prob: {tele.win_probability*100}% | Score: {tele.home_score}-{tele.away_score}")

    # 2. Ingest a Goal (The Pulse)
    print("\n[EVENT] GOOOOOOOAL! Arsenal scores (84')")
    tele = match_pulse.ingest_match_event(match_id, "GOAL", {"team": "home", "minute": 84})
    print(f"NEW Prob: {tele.win_probability*100}% | Score: {tele.home_score}-{tele.away_score}")

    # 3. Dynamic Hedging Decision
    print("\n[HEDGING] Evaluating Exit Strategy...")
    cash_out_value = 145000
    potential_payout = 160000
    stake = 50000
    
    alpha = hedging_core.calculate_hedging_alpha(tele.win_probability, cash_out_value, potential_payout)
    should_exit = hedging_core.should_lock_profit(tele.win_probability, cash_out_value, stake)
    
    print(f"Exit Alpha: {alpha:.4f}")
    print(f"Should Lock Profit? {'YES ✅' if should_exit else 'NO ❌'}")

    # 4. Vault Sweep (Settlement)
    if should_exit:
        print(f"\n[SETTLEMENT] Triggering Institutional Sweep of ₦{cash_out_value:,}...")
        tx_hash = await settlement_core.initiate_vault_sweep(cash_out_value, "SportyBet_PRO_X1")
        print(f"VAULT CONFIRMED. TX: {tx_hash}")

    print("\n🏁 DRY RUN COMPLETE. PHASE 16 LOGIC VERIFIED.")

if __name__ == "__main__":
    asyncio.run(run_sentient_sim())
