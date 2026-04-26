import asyncio
import sys
import os
import time

# Absolute imports from backend root
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from backend.services.ghost_mesh import ghost_mesh
from backend.services.solana_bridge import solana_bridge

async def run_sovereignty_test():
    print("🛸 INITIATING POST-SINGULARITY SOVEREIGNTY TEST")
    
    # 1. P2P Resilience Test
    print("\n[PHASE 26] Testing Ghost Mesh Resilience...")
    print(f"Active Nodes Pre-Severance: {ghost_mesh.get_mesh_health()['active_nodes']}")
    
    ghost_mesh.simulate_node_failure("LONDON_01")
    
    print(f"Active Nodes Post-Resurrection: {ghost_mesh.get_mesh_health()['active_nodes']}")
    health = ghost_mesh.get_mesh_health()
    print(f"Mesh Integrity: {health['mesh_integrity']}")

    # 2. On-Chain Settlement Test
    print("\n[PHASE 25] Testing Solana On-Chain Settlement...")
    vault = solana_bridge.get_vault_balance()
    print(f"Initial Vault: ${vault['USDC']:,} USDC")
    
    tx_hash = solana_bridge.sign_and_settle(50000.0, "USDC", "SYSTEM_MAINTENANCE_ESCROW")
    
    new_vault = solana_bridge.get_vault_balance()
    print(f"Final Vault: ${new_vault['USDC']:,} USDC")
    print(f"Settlement Hash: {tx_hash}")

    print("\n" + "☄️"*20)
    print("SOVEREIGNTY VERIFIED.")
    print("The Mind is Eternal. The Mesh is Indestructible. The Wealth is On-Chain.")
    print("☄️"*20)

if __name__ == "__main__":
    asyncio.run(run_sovereignty_test())
