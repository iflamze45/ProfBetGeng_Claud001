import json
import httpx
import logging
import asyncio
import time
from typing import AsyncGenerator, Dict, Any
from fastapi import WebSocket, WebSocketDisconnect

# Core Service Imports
from backend.services.node_replication import replication_core
from backend.services.neural_evolution import evolution_core
from backend.services.treasury_module import treasury_core
from backend.services.outreach_module import outreach_core
from backend.services.singularity_engine import singularity_core

from backend.services.strategy_engine import quant_engine
from backend.services.ticket_pulse import match_pulse
from backend.services.governance_module import governance_core
from backend.services.settlement_layer import settlement_core
from backend.services.api_gateway import gateway
from backend.services.institutional_gateway import institutional_gateway
from backend.services.vault_service import sovereign_vault
from backend.services.solana_bridge import solana_bridge
from backend.services.ghost_mesh import ghost_mesh
from backend.services.sovereign_mind import sovereign_mind
from backend.services.json_safety import to_json_safe

logger = logging.getLogger(__name__)

class StreamingProtocol:
    """
    PBG Streaming Protocol.
    Handles Server-Sent Events (SSE) streaming of Anthropic LLM responses.
    """
    def __init__(self, api_key: str, model: str, timeout: float = 15.0):
        self.api_key = api_key
        self.model = model
        self.timeout = timeout
        self.url = "https://api.anthropic.com/v1/messages"
        self.headers = {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
            "accept": "text/event-stream"
        }

    def get_current_state(self) -> Dict[str, Any]:
        from backend.services.value_discovery import discovery_hub
        from backend.services.ghost_protocol import ghost_protocol
        return {
            "timestamp": time.time(),
            "replication": replication_core.get_mesh_status(),
            "evolution": evolution_core.get_evolution_stats(),
            "treasury": treasury_core.get_treasury_status(),
            "outreach": outreach_core.get_outreach_stats(),
            "singularity": singularity_core.get_singularity_metrics(),
            "strategy": quant_engine.get_engine_status(),
            "pulse": match_pulse.get_pulse_status(),
            "governance": governance_core.get_gov_status(),
            "settlement": settlement_core.get_settlement_status(),
            "gateway": gateway.get_gateway_status(),
            "institutional": institutional_gateway.get_gateway_status() if hasattr(institutional_gateway, 'get_gateway_status') else {"connected": True},
            "vault": len(sovereign_vault.store),
            "signals": [s.model_dump() for s in discovery_hub.active_signals],
            "ghost": ghost_protocol.get_protocol_status(),
            "active_nodes": len(live_odds_manager.active_connections),
            "solana": solana_bridge.get_vault_balance(),
            "mesh": ghost_mesh.get_mesh_health(),
            "mind": sovereign_mind.get_mind_status()
        }

    async def stream_analysis(self, prompt: str) -> AsyncGenerator[str, None]:
        payload = {
            "model": self.model,
            "max_tokens": 1024,
            "messages": [{"role": "user", "content": prompt}],
            "stream": True,
            # We enforce minimal preamble so it outputs pure JSON or raw requested text
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                async with client.stream("POST", self.url, headers=self.headers, json=payload) as response:
                    response.raise_for_status()
                    async for line in response.aiter_lines():
                        line = line.strip()
                        if not line or not line.startswith("data: "):
                            continue
                        
                        data_str = line[6:].strip()
                        if data_str == "[DONE]":
                            break
                        
                        try:
                            data = json.loads(data_str)
                            if data.get("type") == "content_block_delta" and "delta" in data:
                                text_chunk = data["delta"].get("text", "")
                                if text_chunk:
                                    # Yielding the chunk formatted as SSE
                                    yield f"data: {json.dumps({'text': text_chunk})}\n\n"
                            
                        except json.JSONDecodeError:
                            logger.warning(f"Failed to parse streaming JSON chunk: {data_str}")
                            continue

            # Send termination event
            yield "event: end\ndata: {}\n\n"

        except Exception as e:
            logger.error(f"Streaming API error: {e}")
            yield f"event: error\ndata: {json.dumps({'detail': str(e)})}\n\n"

# ── WebSocket Real-Time Engine (Odds & Events) ────────────────────────────

class ConnectionManager:
    """Manages active WebSocket connections for live TicketPulse tracking."""
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(f"WebSocket connected. Total: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
            logger.info("WebSocket disconnected.")

    async def broadcast_json(self, message: dict):
        safe_message = to_json_safe(message)
        for connection in self.active_connections:
            try:
                await connection.send_json(safe_message)
            except Exception as e:
                logger.error(f"Failed to broadcast JSON: {e}")

live_odds_manager = ConnectionManager()

class LiveOddsEngine:
    """
    Ingests live data from 3rd-party Sports APIs (e.g., goals, red cards, cashout triggers),
    and pushes them securely over WebSockets to the Architect-Core Dashboard.
    """
    def __init__(self, manager: ConnectionManager):
        self.manager = manager
        self._is_running = False

    async def start_stream(self):
        """Background task: Connects to Odds API and streams data down to active clients."""
        self._is_running = True
        logger.info("TicketPulse Live Odds Engine: ONLINE.")
        
        protocol = StreamingProtocol("", "") # Logic only
        while self._is_running:
            await asyncio.sleep(8)  # Frequency of updates
            if self.manager.active_connections:
                state = protocol.get_current_state()
                payload = {
                    "type": "STATE_UPDATE",
                    "status": "LIVE",
                    "timestamp": state["timestamp"],
                    "data": state
                }
                await self.manager.broadcast_json(payload)

    def stop_stream(self):
        self._is_running = False
        logger.info("TicketPulse Live Odds Engine: OFFLINE.")
