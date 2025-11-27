"""WebSocket controller for real-time updates"""
from litestar import websocket, WebSocket
from typing import Set
import json
import logging
from app.services.websocket_service import ws_manager
from app.services.tcp_bridge import tcp_bridge

logger = logging.getLogger(__name__)


@websocket("/status")
async def websocket_handler(socket: WebSocket) -> None:
    """WebSocket 핸들러 - 실시간 상태 업데이트"""
    await socket.accept()
    await ws_manager.add_connection(socket)
    
    # Send initial connection status
    try:
        status = tcp_bridge.get_connection_status()
        await socket.send_text(json.dumps(status))
    except Exception as e:
        logger.error(f"Error sending initial status: {e}")

    try:
        while True:
            data = await socket.receive_text()
            try:
                message = json.loads(data)
                logger.debug(f"Received WebSocket message: {message}")
                
                # Handle UNIT_SELECT message
                if message.get("type") == "UNIT_SELECT":
                    unit_id = message.get("unit_id")
                    if isinstance(unit_id, int):
                        tcp_bridge.set_selected_unit_id(unit_id)
                        
            except json.JSONDecodeError as e:
                logger.error(f"Invalid JSON in WebSocket message: {e}")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
    finally:
        await ws_manager.remove_connection(socket)

