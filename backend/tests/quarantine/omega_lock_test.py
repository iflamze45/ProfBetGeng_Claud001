import asyncio
import sys
import os

# Absolute imports from backend root
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from backend.services.singularity_engine import singularity_core
from backend.services.pbg_streaming_protocol import StreamingProtocol

async def test_omega_lock_singularity():
    print("🔮 STARTING OMEGA LOCK VERIFICATION")
    
    # 1. Check Pre-Singularity State
    stats = singularity_core.get_singularity_metrics()
    print(f"Initial State: Locked={stats['is_locked']}, Entropy={stats['entropy_score']}")
    
    # 2. Execute Singularity Feedback
    print("\nExecuting Recursive Feedback...")
    singularity_core.execute_recursive_feedback()
    
    # 3. Initiate Omega Lock
    print("\nInitiating Omega Lock Protocol...")
    singularity_core.initiate_omega_lock()
    
    # 4. Lock Treasury
    print("\nLocking Treasury for Eternity...")
    singularity_core.lock_treasury_for_eternity()
    
    # 5. Verify Final State
    final_stats = singularity_core.get_singularity_metrics()
    print("\n" + "💎"*20)
    print("✨ SINGULARITY ACHIEVED ✨")
    print(f"Locked: {final_stats['is_locked']}")
    print(f"Entropy: {final_stats['entropy_score']:.4f}")
    print(f"Alpha Domain: {final_stats['alpha_domain']:.2f}")
    print(f"Maintenance: {final_stats['maintenance_status']}")
    print("💎"*20)
    
    # 6. Verify Streaming Protocol reflect the state
    protocol = StreamingProtocol(api_key="sk-alpha", model="claude-3-opus-20240229")
    full_state = protocol.get_current_state()
    print(f"\nStreaming Snapshot - Singularity Locked: {full_state['singularity']['is_locked']}")

if __name__ == "__main__":
    asyncio.run(test_omega_lock_singularity())
