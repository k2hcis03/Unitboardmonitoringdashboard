# 코드 스타일 및 규칙

## 언어
- **응답/커밋/주석/문서**: 한국어
- **변수명/함수명**: 영어 (코드 표준)

## 프론트엔드 (TypeScript/React)
- 컴포넌트: PascalCase 함수형 컴포넌트, `.tsx`
- 훅: `use` 접두사 (예: `useWebSocket`, `useWebSocketContext`)
- 서비스/유틸: camelCase, `.ts`
- UI 컴포넌트: `src/components/ui/` (shadcn/ui 기반)
- 상태관리: React useState/useContext, WebSocket은 Context로 전역 공유
- API 통신: `src/services/api.ts`의 `APIClient` 클래스 사용
- 스타일: TailwindCSS 유틸리티 클래스

## 백엔드 (Python)
- 프레임워크: Litestar (async)
- 데이터 검증: Pydantic 모델
- DB: SQLite + aiosqlite (비동기)
- 로깅: Python `logging` 모듈
- 컨트롤러: `backend/app/controllers/` (REST 엔드포인트)
- 서비스: `backend/app/services/` (비즈니스 로직)
- 모델: `backend/app/models/` (Pydantic 모델)
- 설정: `backend/app/config.py`, `backend/app/ini/sys.ini`

## WebSocket 메시지 타입
- `SYSTEM_CONNECTION_STATUS`: TCP 연결 상태
- `SENSOR_UPDATE`: 센서 데이터 업데이트
- `ACK_RECEIVED`: 명령 확인
- `ACK_INITIALIZE_RECEIVED`: 초기화 확인 (펌웨어 버전 포함)
- `UNIT_SELECT`: 프론트엔드 → 백엔드 유닛 선택

## ERROR 처리
- ERROR 코드 `"0"` → 정상 (녹색 LED)
- ERROR 코드 `"0"` 외 → 에러 상태 (빨간 LED + 코드 표시)
