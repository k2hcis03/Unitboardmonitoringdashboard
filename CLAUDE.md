# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 프로젝트 개요

라즈베리파이 4를 메인 제어 장치로 하고, CAN-FD 버스를 통해 최대 32개의 STM32G474 기반 유닛보드를 제어·모니터링하는 웹 기반 양조장 제어 소프트웨어입니다.

## 빌드 및 실행 명령어

### 프론트엔드 (React/Vite)
```bash
npm install
npm run dev      # 개발 서버 (포트 3000)
npm run build    # 프로덕션 빌드
```

라즈베리파이에서 외부 접속 허용:
```bash
npm run dev -- --host --open=false
```

### 백엔드 (Python/Litestar)
```bash
cd backend
python -m venv venv
# Windows: venv\Scripts\activate
# Linux: source venv/bin/activate
pip install -r requirements.txt
python main.py   # 포트 9001
```

### Sensor Viewer (Python/Tkinter)
```bash
cd sensor_view
pip install -r requirements.txt
python app.py
```

### API 테스트
```bash
curl http://localhost:9001/api/units/0
curl -X POST http://localhost:9001/api/gpio/control \
  -H "Content-Type: application/json" \
  -d '{"unit_id": 0, "gpio_index": 0, "state": true}'
```

## 아키텍처

```
PC/Tablet/Mobile Browser
        │
        ▼
React Frontend (포트 3000)  ←── Vite + TypeScript + Radix UI + TailwindCSS
        │  REST API + WebSocket
        ▼
Litestar Backend (포트 9001) ←── Python async, Pydantic, SQLite
        │  TCP JSON (포트 7000/7001)
        ▼
라즈베리파이 메인 제어 프로그램
        │  CAN-FD Network
        ▼
최대 32개 STM32G474 유닛보드
```

### TCP Bridge 통신
- **포트 7000 (Send)**: 라즈베리파이 → 백엔드 (SENSOR 패킷 수신)
- **포트 7001 (Receive)**: 백엔드 → 라즈베리파이 (명령 전송)

라즈베리파이에서 전송되는 주요 패킷 타입: `SENSOR`, `ACK`, `ACK_INIT`  
백엔드에서 전송하는 명령 패킷: `GPIO`, `MOTOR`, `FIRMWARE`, `GET_VERSION`, `REF`, `STATE`, `RECIPE`

### TANK_ID 매핑
프론트엔드 유닛보드 index와 라즈베리파이 TANK_ID는 별도로 매핑됩니다.  
매핑 테이블은 `src/config.ts`의 `UNIT_TO_TANK_ID`와 `backend/app/services/tcp_bridge.py`의 `UNIT_TO_TANK_ID`에서 **동기화**되어야 합니다.  
- 유닛보드 1 (index 0) → TANK_ID 601  
- 유닛보드 2 (index 1) → TANK_ID 101  
- 유닛보드 3-32 (index 2-31) → TANK_ID 102-131  

### 백엔드 구조
- `backend/app/controllers/` — REST API 엔드포인트 (unit, gpio, history, recipe, websocket)
- `backend/app/services/` — 비즈니스 로직 (tcp_bridge, unit_manager, state_manager, db_service, websocket_service)
- `backend/app/models/` — Pydantic 모델 (unit, gpio, sensor, protocol 등)
- `backend/app/config.py` — 설정 (host, port, max_units=32, SQLite DB 경로)
- `backend/app/ini/sys.ini` — 펌웨어 업데이트 URL, 네트워크 IP 설정

### 프론트엔드 구조
- `src/components/` — UI 컴포넌트 (StatusMonitoringCard, GPIOControlPanel, FunctionButtonPanel)
- `src/services/api.ts` — 백엔드 REST API 클라이언트
- `src/hooks/useWebSocket.ts` — 실시간 WebSocket 데이터 수신
- `src/config.ts` — API URL 자동 설정 및 TANK_ID 매핑, 앱 버전 관리

### SENSOR 패킷 ERROR 처리
SENSOR 패킷에는 `ERROR` 배열이 포함될 수 있습니다.  
- ERROR 코드 `"0"` → 정상 (녹색 LED)  
- ERROR 코드 `"0"` 외 → 에러 상태 (빨간 LED + 에러 코드 표시)  
에러 처리 로직은 `FunctionButtonPanel.tsx`와 `StatusMonitoringCard.tsx`에 구현되어 있습니다.

## 포트 및 URL 설정

| 항목 | 값 |
|------|-----|
| 프론트엔드 포트 | 3000 |
| 백엔드 포트 | 9001 |
| WebSocket URL | `ws://{host}:9001/ws/status` |
| TCP 수신 포트 | 7000 |
| TCP 송신 포트 | 7001 |

프론트엔드는 `VITE_API_BASE_URL`과 `VITE_WS_URL` 환경변수로 재정의하거나, 없으면 `window.location.hostname`을 자동으로 사용합니다.

## 상세 개발 가이드

API 스펙, Pydantic 모델 정의, WebSocket 메시지 포맷 등 상세 내용은 [src/CURSOR_AI_GUIDE.md](src/CURSOR_AI_GUIDE.md)를 참조하세요.
