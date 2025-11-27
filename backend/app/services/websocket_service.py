import json
import logging
from typing import Set
from litestar import WebSocket

logger = logging.getLogger(__name__)

class WebSocketManager:
    """WebSocket 연결 관리자"""
    
    def __init__(self):
        self.connections: Set[WebSocket] = set()
    
    async def add_connection(self, socket: WebSocket) -> None:
        """연결 추가"""
        self.connections.add(socket)
        logger.info(f"WebSocket connected: {len(self.connections)} connections")
    
    async def remove_connection(self, socket: WebSocket) -> None:
        """연결 제거"""
        self.connections.discard(socket)
        logger.info(f"WebSocket disconnected: {len(self.connections)} connections")
    
    async def broadcast(self, message: dict) -> None:
        """모든 연결에 메시지 브로드캐스트"""
        if not self.connections:
            return
        
        message_str = json.dumps(message)
        disconnected = set()
        
        for socket in self.connections:
            try:
                await socket.send_text(message_str)
            except Exception as e:
                logger.error(f"Error broadcasting to socket: {e}")
                disconnected.add(socket)
        
        # 연결이 끊어진 소켓 제거
        for socket in disconnected:
            self.connections.discard(socket)

# 전역 WebSocket 관리자 인스턴스
ws_manager = WebSocketManager()

