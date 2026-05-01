import logging
from typing import List, Dict, Optional
from pydantic import BaseModel
from datetime import datetime

logger = logging.getLogger("pbg.node_manager")

class SatelliteNode(BaseModel):
    id: str
    region: str # "Lagos" | "London" | "NYC"
    endpoint: str
    latency_ms: int = 0
    status: str = "OFFLINE" # ONLINE | OFFLINE | BUSY
    active_tasks: int = 0
    last_seen: Optional[datetime] = None

class NodeManager:
    """
    Registry for global Satellite Nodes in the SGN (Sovereign Global Network).
    Orchestrates cross-region execution task distribution.
    """
    
    def __init__(self):
        self.nodes: Dict[str, SatelliteNode] = {
            "LAG-01": SatelliteNode(id="LAG-01", region="Lagos", endpoint="https://lagos.pbg.io", status="ONLINE"),
            "LDN-01": SatelliteNode(id="LDN-01", region="London", endpoint="https://london.pbg.io", status="ONLINE"),
            "NYC-01": SatelliteNode(id="NYC-01", region="NYC", endpoint="https://nyc.pbg.io", status="OFFLINE"),
        }

    def register_node(self, node: SatelliteNode):
        self.nodes[node.id] = node
        logger.info(f"NODE_REGISTERED: {node.id} in {node.region} cluster.")

    def get_optimal_node(self, bookmaker_region: str) -> Optional[SatelliteNode]:
        """
        Logic to route tasks to the node with lowest latency to a bookie.
        """
        # Simplistic routing: Match region
        for n in self.nodes.values():
            if n.region.lower() == bookmaker_region.lower() and n.status == "ONLINE":
                return n
        
        # Fallback to any online node
        return next((n for n in self.nodes.values() if n.status == "ONLINE"), None)

    def heartbeat(self, node_id: str, latency: int):
        if node_id in self.nodes:
            self.nodes[node_id].status = "ONLINE"
            self.nodes[node_id].latency_ms = latency
            self.nodes[node_id].last_seen = datetime.now()
            logger.info(f"NODE_ALIVE: {node_id} | Latency: {latency}ms")

# Singleton
sgn_hub = NodeManager()
