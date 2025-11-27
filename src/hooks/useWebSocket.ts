/**
 * WebSocket을 통한 실시간 상태 업데이트 훅
 * 이제 Context를 사용하여 전역 연결을 공유합니다.
 */
import { useWebSocketContext } from '../contexts/WebSocketContext';
import { WebSocketMessage } from '../contexts/WebSocketContext';

export type { WebSocketMessage };

export function useWebSocket() {
  return useWebSocketContext();
}

