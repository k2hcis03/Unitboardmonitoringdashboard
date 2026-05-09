# 작업 완료 시 체크리스트

## 프론트엔드 변경 시
- [ ] TypeScript 타입 오류 없는지 확인 (IDE 확인)
- [ ] TANK_ID 매핑 변경 시 `src/config.ts`와 `backend/app/services/tcp_bridge.py` 동기화
- [ ] 새 WebSocket 메시지 타입 추가 시 `WebSocketContext.tsx`와 `FunctionButtonPanel.tsx` 양쪽 처리

## 백엔드 변경 시
- [ ] Pydantic 모델 변경 시 관련 컨트롤러/서비스 확인
- [ ] TCP 패킷 포맷 변경 시 `backend/app/models/protocol.py` 업데이트
- [ ] 비동기 DB 작업은 `asyncio.create_task` 또는 `await` 사용 (메인 루프 차단 금지)

## 공통
- [ ] 커밋 메시지 한국어로 작성
- [ ] 코드 주석 한국어로 작성
- [ ] 포트 설정 변경 시 `CLAUDE.md` 포트 테이블 업데이트
- [ ] 빌드/실행 테스트: 프론트엔드 `npm run dev`, 백엔드 `python main.py`

## 주요 포트 (변경 금지)
| 서비스 | 포트 |
|--------|------|
| 프론트엔드 | 3000 |
| 백엔드 | 9001 |
| TCP 수신 (Pi→백엔드) | 7000 |
| TCP 송신 (백엔드→Pi) | 7001 |
