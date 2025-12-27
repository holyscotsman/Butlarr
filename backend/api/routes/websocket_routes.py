"""WebSocket endpoints for real-time updates."""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
import json
import structlog

logger = structlog.get_logger(__name__)

router = APIRouter()


@router.websocket("/scan")
async def scan_websocket(websocket: WebSocket):
    """WebSocket for real-time scan updates."""
    # Access app state via websocket scope (correct FastAPI pattern)
    app = websocket.scope["app"]
    ws_manager = app.state.ws_manager
    
    await ws_manager.connect(websocket, "scan")
    logger.info("WebSocket connected", channel="scan")
    
    try:
        while True:
            data = await websocket.receive_text()
            try:
                message = json.loads(data)
                if message.get("type") == "ping":
                    await websocket.send_json({"type": "pong"})
            except json.JSONDecodeError:
                logger.warning("Invalid JSON in WebSocket message")
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket, "scan")
        logger.info("WebSocket disconnected", channel="scan")
    except Exception as e:
        logger.error("WebSocket error", channel="scan", error=str(e))
        ws_manager.disconnect(websocket, "scan")


@router.websocket("/activity")
async def activity_websocket(websocket: WebSocket):
    """WebSocket for real-time activity updates."""
    app = websocket.scope["app"]
    ws_manager = app.state.ws_manager
    
    await ws_manager.connect(websocket, "activity")
    logger.info("WebSocket connected", channel="activity")
    
    try:
        while True:
            data = await websocket.receive_text()
            try:
                message = json.loads(data)
                if message.get("type") == "ping":
                    await websocket.send_json({"type": "pong"})
            except json.JSONDecodeError:
                logger.warning("Invalid JSON in WebSocket message")
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket, "activity")
        logger.info("WebSocket disconnected", channel="activity")
    except Exception as e:
        logger.error("WebSocket error", channel="activity", error=str(e))
        ws_manager.disconnect(websocket, "activity")
