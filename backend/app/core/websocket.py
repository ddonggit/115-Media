"""WebSocket connection manager for task progress pushing."""
import json
import logging
from typing import Any
from fastapi import WebSocket

logger = logging.getLogger(__name__)


class ConnectionManager:
    """Manages WebSocket connections for real-time task updates."""

    def __init__(self) -> None:
        self._connections: set[WebSocket] = set()

    async def connect(self, ws: WebSocket) -> None:
        await ws.accept()
        self._connections.add(ws)
        logger.info("WebSocket connected: %s", id(ws))

    def disconnect(self, ws: WebSocket) -> None:
        self._connections.discard(ws)
        logger.info("WebSocket disconnected: %s", id(ws))

    async def broadcast(self, event: str, data: dict[str, Any]) -> None:
        """Send a JSON event to all connected clients."""
        payload = json.dumps({"event": event, "data": data})
        stale: set[WebSocket] = set()
        for ws in self._connections:
            try:
                await ws.send_text(payload)
            except Exception:
                stale.add(ws)
        for ws in stale:
            self._connections.discard(ws)

    @property
    def active_count(self) -> int:
        return len(self._connections)


# Singleton
manager = ConnectionManager()
