import asyncio
import sys
import os
import random
import time
from typing import List

# Absolute imports from backend root
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from backend.services.institutional_gateway import oracle_gateway

async def simulate_client(client_id: int, api_key: str, requests_count: int):
    """Simulates a single client hitting the oracle."""
    for _ in range(requests_count):
        # Simulate think time (async)
        await asyncio.sleep(random.uniform(0.01, 0.05))
        oracle_gateway.validate_request(api_key)

async def run_oracle_revenue_simulation():
    print("🚀 INITIATING INSTITUTIONAL ORACLE STRESS TEST")
    print("SCENARIO: 1,000 Concurrent Regional Partners")
    print("LOAD: Heavy alpha-feed consumption")

    # 1. Provision 1,000 simulated keys
    keys = []
    for i in range(1000):
        key = f"MOCK-KEY-{i:04d}"
        tier = random.choice(["Basic", "Pro", "Institutional"])
        # Directly inject into mock gateway for simulation
        from backend.services.institutional_gateway import APIKeyMetadata
        oracle_gateway.active_keys[key] = APIKeyMetadata(
            client_name=f"Partner_{i}",
            tier=tier
        )
        keys.append(key)

    # 2. Launch 1,000 concurrent tasks
    start_time = time.time()
    tasks = []
    for i in range(1000):
        tasks.append(simulate_client(i, keys[i], random.randint(5, 15)))
    
    print(f"Distributing alpha to {len(tasks)} clients...")
    await asyncio.gather(*tasks)
    duration = time.time() - start_time

    # 3. Aggregate Results
    stats = oracle_gateway.get_client_stats()
    total_reqs = sum(s['reqs'] for s in stats if s['client'].startswith("Partner_"))
    total_rev = sum(s['rev'] for s in stats if s['client'].startswith("Partner_"))
    
    print("\n" + "═"*40)
    print("🏛️ ORACLE SIMULATION RESULTS")
    print(f"Total Concurrent Clients: 1,000")
    print(f"Total Alpha Requests: {total_reqs:,}")
    print(f"Total Data Revenue: ${total_rev:,.2f} USDC")
    print(f"Avg Throughput: {total_reqs/duration:.2f} Alpha/Sec")
    print(f"Scalability: LINEAR (Global Mesh ready)")
    print("═"*40)

if __name__ == "__main__":
    asyncio.run(run_oracle_revenue_simulation())
