import logging
import asyncio
import random
from typing import Set, List
from .node_manager import sgn_hub

logger = logging.getLogger("pbg.gossip")

class GossipProtocol:
    """
    P2P Signal Propagation for the Sovereign Global Network.
    Synchronizes Arbitrage 'Pulses' between regional nodes.
    """
    
    def __init__(self):
        self.known_signals: Set[str] = set() # Set of Arb Match IDs
        self.sync_interval = 30 # seconds

    async def start_gossip_loop(self):
        logger.info("GOSSIP_SERVICE: Peer-to-Peer discovery active.")
        while True:
            await self.propagate()
            await asyncio.sleep(self.sync_interval)

    async def propagate(self):
        """
        Simulates gossiping signal state with 2 random neighbor nodes.
        """
        nodes = list(sgn_hub.nodes.values())
        online_nodes = [n for n in nodes if n.status == "ONLINE"]
        
        if len(online_nodes) < 2: return

        targets = random.sample(online_nodes, 2)
        
        for t in targets:
            # Simulation: Only sync a small diff
            diff_count = random.randint(1, 5)
            logger.info(f"GOSSIP_SYNC: Propagating {diff_count} signals to {t.id} ({t.region}).")
            # In a real node: requests.post(f"{t.endpoint}/api/v1/sync", json=...)

    def receive_gossip(self, signals: List[str]):
        new_discoveries = set(signals) - self.known_signals
        if new_discoveries:
            logger.info(f"GOSSIP_RECV: Discovered {len(new_discoveries)} new arbs from peers.")
            self.known_signals.update(new_discoveries)

# Singleton
gossip_core = GossipProtocol()
