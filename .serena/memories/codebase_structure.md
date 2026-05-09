# 코드베이스 구조

## 루트
```
/
├── src/                    # 프론트엔드 (React/TypeScript)
├── backend/                # 백엔드 (Python/Litestar)
├── sensor_view/            # 독립형 센서 뷰어 (Python/Tkinter)
├── firmware/               # 펌웨어 바이너리
├── reference/              # 레시피 참조 파일
├── package.json            # 프론트엔드 의존성
├── vite.config.ts          # Vite 설정
└── CLAUDE.md               # AI 가이드

## 프론트엔드 (src/)
├── App.tsx                 # 루트 컴포넌트
├── main.tsx                # 진입점
├── config.ts               # API URL, TANK_ID 매핑, 앱 버전
├── components/
│   ├── DashboardPanel.tsx          # 대시보드 레이아웃
│   ├── FunctionButtonPanel.tsx     # 제어 버튼, 연결상태, 레시피
│   ├── GPIOControlPanel.tsx        # GPIO 제어
│   ├── StatusMonitoringCard.tsx    # 유닛 상태 카드
│   └── ui/                         # shadcn/ui 공통 컴포넌트
├── contexts/
│   └── WebSocketContext.tsx        # WebSocket 전역 Context
├── hooks/
│   └── useWebSocket.ts             # WebSocket 훅
└── services/
    └── api.ts                      # REST API 클라이언트

## 백엔드 (backend/)
├── main.py                         # Litestar 앱 진입점
└── app/
    ├── config.py                   # 설정 (포트, max_units=32, DB 경로)
    ├── controllers/                # REST 엔드포인트
    │   ├── unit.py                 # 유닛 상태 API
    │   ├── gpio.py                 # GPIO 제어 API
    │   ├── history.py              # 히스토리/DB API
    │   ├── recipe.py               # 레시피 API
    │   ├── system.py               # 시스템 API
    │   └── websocket.py            # WebSocket 핸들러
    ├── models/                     # Pydantic 모델
    │   ├── protocol.py             # TCP 패킷 모델 (SENSOR, ACK, 명령)
    │   ├── unit.py                 # 유닛 모델
    │   ├── gpio.py                 # GPIO 모델
    │   └── sensor.py               # 센서 모델
    ├── services/                   # 비즈니스 로직
    │   ├── tcp_bridge.py           # TCP 통신 (포트 7000/7001)
    │   ├── unit_manager.py         # 유닛 상태 관리
    │   ├── state_manager.py        # 상태 관리
    │   ├── db_service.py           # SQLite DB 서비스
    │   └── websocket_service.py    # WebSocket 브로드캐스트
    └── ini/
        └── sys.ini                 # 펌웨어 URL, 네트워크 IP
```
