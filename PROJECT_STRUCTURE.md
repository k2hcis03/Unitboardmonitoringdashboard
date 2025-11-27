# 프로젝트 구조 가이드

## 📁 전체 프로젝트 구조

```
Unitboardmonitoringdashboard/
├── backend/                     # 백엔드 (Litestar)
│   ├── app/
│   │   ├── main.py             # Litestar 앱 엔트리포인트
│   │   ├── config.py            # 설정 관리
│   │   ├── models/             # Pydantic 모델
│   │   │   ├── unit.py         # 유닛보드 상태 모델
│   │   │   ├── gpio.py         # GPIO 제어 모델
│   │   │   └── sensor.py       # 센서 데이터 모델
│   │   ├── controllers/        # API 컨트롤러
│   │   │   ├── unit.py         # 유닛보드 상태 API
│   │   │   ├── gpio.py         # GPIO 제어 API
│   │   │   └── websocket.py    # WebSocket 핸들러
│   │   ├── services/           # 비즈니스 로직
│   │   │   ├── can_bus.py      # CAN-FD 통신 서비스
│   │   │   ├── unit_manager.py # 유닛보드 관리
│   │   │   └── state_manager.py # 상태 관리
│   │   └── utils/
│   │       └── logger.py       # 로깅 설정
│   ├── requirements.txt
│   ├── pyproject.toml
│   └── README.md
│
├── src/                         # 프론트엔드 (React)
│   ├── components/
│   │   ├── StatusMonitoringCard.tsx  # 상태 모니터링 카드
│   │   ├── GPIOControlPanel.tsx      # GPIO 제어 패널
│   │   └── FunctionButtonPanel.tsx   # 기능 버튼 패널
│   ├── services/
│   │   └── api.ts              # 백엔드 API 클라이언트
│   ├── hooks/
│   │   └── useWebSocket.ts     # WebSocket 훅
│   ├── App.tsx
│   └── main.tsx
│
├── package.json
├── vite.config.ts
├── README.md
└── PROJECT_STRUCTURE.md         # 이 파일 (신규)
```

## 🔄 통신 구조

### 1. 웹 프론트엔드 ↔ 백엔드 (Litestar)

- **REST API**: `http://localhost:8000/api/*`
- **WebSocket**: `ws://localhost:8000/ws/status`

## 🎯 주요 컴포넌트

### 백엔드

#### 1. 유닛 관리자 (`app/services/unit_manager.py`)

유닛보드 제어 및 상태 관리를 담당합니다.

**주요 기능:**
- 유닛보드 상태 조회
- GPIO 제어
- 모터 제어

#### 2. 상태 관리자 (`app/services/state_manager.py`)

유닛보드 상태를 메모리에 저장하고 관리합니다.

**주요 기능:**
- 상태 저장 및 조회
- GPIO 상태 관리
- 모터 상태 관리
- 밸브 상태 관리

### 프론트엔드

#### 1. 상태 모니터링 카드 (`StatusMonitoringCard.tsx`)

유닛보드의 센서 데이터와 상태를 표시합니다.

#### 2. GPIO 제어 패널 (`GPIOControlPanel.tsx`)

GPIO 및 모터를 제어하는 UI입니다.

#### 3. 기능 버튼 패널 (`FunctionButtonPanel.tsx`)

레시피 실행, 펌웨어 업데이트 등의 기능을 제공합니다.

## 🔌 API 엔드포인트

### 웹 프론트엔드용 REST API

- `GET /api/units/` - 모든 유닛보드 상태 조회
- `GET /api/units/{unit_id}` - 특정 유닛보드 상태 조회
- `GET /api/units/{unit_id}/gpio` - GPIO 상태 조회
- `POST /api/gpio/control` - GPIO 제어
- `POST /api/gpio/motor` - 모터 제어

## 📝 데이터 흐름

### 1. 웹 프론트엔드에서 GPIO 제어

```
React Frontend
    ↓ POST /api/gpio/control
Litestar Backend (Controller)
    ↓ unit_manager.control_gpio()
Unit Manager
    ↓ state_manager.set_gpio_state()
State Manager
```

## 🚀 다음 단계

### 현재 완료된 기능

1. ✅ 기본 GPIO 제어 및 상태 모니터링
2. ✅ REST API 엔드포인트
3. ✅ WebSocket 실시간 상태 업데이트

### 향후 구현 예정

1. **레시피 실행 기능**
   - 레시피 파일 파싱
   - 단계별 실행 로직
   - 진행 상태 추적

2. **펌웨어 업데이트**
   - 펌웨어 파일 업로드
   - CAN-FD를 통한 펌웨어 전송
   - 업데이트 진행 상태

3. **실시간 센서 모니터링**
   - CAN-FD에서 센서 데이터 읽기
   - WebSocket을 통한 실시간 업데이트

4. **에러 처리 및 로깅**
   - 상세한 에러 메시지
   - 로그 파일 저장
   - 알림 시스템

## 🔧 설정

### 환경 변수

`backend/.env` 파일:

```env
# 웹 서버
HOST=0.0.0.0
PORT=8000

# CAN-FD
CAN_INTERFACE=socketcan
CAN_CHANNEL=can0
CAN_BITRATE=500000
CAN_FD=true

# 기타
MAX_UNITS=20
```

## 📚 참고 문서

- [README.md](README.md) - 프로젝트 전체 개요
- [src/CURSOR_AI_GUIDE.md](src/CURSOR_AI_GUIDE.md) - 프론트엔드 개발 가이드

