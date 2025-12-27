"""WebSocket connection manager for real-time updates."""

from typing import Dict, List, Set
from fastapi import WebSocket
import structlog
import json

logger = structlog.get_logger(__name__)


class WebSocketManager:
    """Manages WebSocket connections for real-time updates."""
    
    def __init__(self):
        self._connections: Dict[str, Set[WebSocket]] = {
            "scan": set(),
            "activity": set(),
        }
    
    async def connect(self, websocket: WebSocket, channel: str):
        """Accept and register a WebSocket connection."""
        await websocket.accept()
        if channel not in self._connections:
            self._connections[channel] = set()
        self._connections[channel].add(websocket)
        logger.info("WebSocket connected", channel=channel, total=len(self._connections[channel]))
    
    def disconnect(self, websocket: WebSocket, channel: str):
        """Remove a WebSocket connection."""
        if channel in self._connections:
            self._connections[channel].discard(websocket)
            logger.info("WebSocket disconnected", channel=channel, total=len(self._connections[channel]))
    
    async def broadcast(self, channel: str, message: dict):
        """Broadcast message to all connections in a channel."""
        if channel not in self._connections:
            return
        
        dead_connections = set()
        
        for websocket in self._connections[channel]:
            try:
                await websocket.send_json(message)
            except Exception as e:
                logger.warning("Failed to send WebSocket message", error=str(e))
                dead_connections.add(websocket)
        
        # Clean up dead connections
        for ws in dead_connections:
            self._connections[channel].discard(ws)
    
    async def send_to_one(self, websocket: WebSocket, message: dict):
        """Send message to a specific connection."""
        try:
            await websocket.send_json(message)
        except Exception as e:
            logger.warning("Failed to send WebSocket message", error=str(e))
    
    def get_connection_count(self, channel: str = None) -> int:
        """Get number of active connections."""
        if channel:
            return len(self._connections.get(channel, set()))
        return sum(len(conns) for conns in self._connections.values())
