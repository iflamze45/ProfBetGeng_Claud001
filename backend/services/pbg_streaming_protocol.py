import json
import httpx
import logging
import asyncio
import time
from typing import AsyncGenerator, Dict, Any
from fastapi import WebSocket, WebSocketDisconnect

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
        return {
            "timestamp": time.time(),
            "active_nodes": len(live_odds_manager.active_connections),
            "status": "LIVE",
        }

    async def stream_analysis(self, prompt: str) -> AsyncGenerator[str, None]:
        payload = {
            "model": self.model,
            "max_tokens": 1024,
            "messages": [{"role": "user", "content": prompt}],
            "stream": True,
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
                                    yield f"data: {json.dumps({'text': text_chunk})}\n\n"

                        except json.JSONDecodeError:
                            logger.warning(f"Failed to parse streaming JSON chunk: {data_str}")
                            continue

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

        protocol = StreamingProtocol("", "")  # Logic only
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
