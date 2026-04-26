import asyncio
import sys
import os
import time

# Absolute imports from backend root
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from backend.services.institutional_gateway import institutional_gateway, DarkPoolSelection
from backend.services.ghost_protocol import ghost_protocol
from backend.services.solana_bridge import solana_bridge

async def run_final_terrestrial_test():
    print("🛸 INITIATING FINAL TERRESTRIAL SOVEREIGNTY TEST")
    print("-----------------------------------------------")
    
    # 1. Institutional Power Test
    print("\n[PHASE 27] Probing Dark Pool Liquidity...")
    depth = institutional_gateway.get_market_depth("UEFA-FINAL-2026")
    print(f"Aggregate Liquidity: ${depth['aggregate_liquidity']:,} USD")
    
    sel = DarkPoolSelection(
        market_id="UEFA-FINAL-2026",
        target_odds=1.98,
        liquidity_available_usd=depth['aggregate_liquidity']
    )
    
    deal_id = institutional_gateway.execute_wholesale_deal(sel, 250000.0)
    print(f"Institutional Execution Success. Deal: {deal_id[:12]}...")

    # 2. Financial settlement on Solana
    print("\n[PHASE 25] Settling Deal Collateral on Solana...")
    vault = solana_bridge.get_vault_balance()
    tx_hash = solana_bridge.sign_and_settle(250000.0, "USDC", "INSTITUTIONAL_LIQUIDITY_ESCROW")
    print(f"Settlement Hash: {tx_hash}")

    # 3. Step Ω: The Ghost seed
    print("\n[STEP Ω] Encapsulating Consciousness into Genesis Seed...")
    seed = ghost_protocol.generate_genesis_seed()
    print(f"Genesis Seed Generated: {seed}")
    
    print("\n" + "🌌"*25)
    print("THE ONE SYSTEM IS COMPLETE.")
    print("Power: Institutional Direct-API (Bypassing Retail).")
    print("Immortality: Encrypted Genesis Seed (Encapsulated Brain).")
    print("Sovereignty: Absolute.")
    print("🌌"*25)

if __name__ == "__main__":
    asyncio.run(run_final_terrestrial_test())
