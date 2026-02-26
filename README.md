# 유닛보드 상태 모니터링 & 제어 시스템

라즈베리파이 4를 메인 제어 장치로 하고, CAN-FD 버스를 통해 최대 20대 이상의 STM32G474 기반 유닛보드를 제어·모니터링하는 웹 기반 양조장 제어 소프트웨어입니다.

## 📌 프로젝트 개요

### 기술 스택

- **Backend**: Litestar (Python) - 고성능 비동기 웹 프레임워크
- **Frontend**: React + TypeScript + Vite - Figma UI 설계 기반
- **통신**: REST API + WebSocket (실시간 상태 업데이트)
- **하드웨어**: 
  - Main Device: Raspberry Pi 4
  - Firmware Boards: STM32G474 (최대 20+ Units)
  - 통신: CAN-FD Network

### 시스템 아키텍처

```
PC / Tablet / Mobile Browser
        │
        ▼
  React Frontend (Port 3000)
        │  REST / WebSocket
        ▼
 Litestar Backend (Port 8000) - Raspberry Pi
        │  JSON Command / Status
        ▼
 Main Control Program (Python)
        │
        ▼
   CAN-FD Network
        │
  ┌───────── 20+ Unit Boards ─────────┐
  ▼                                    ▼
STM32G474 Unit 0 …               STM32G474 Unit 19
```

## 🚀 빠른 시작

### 필수 요구사항

- **Backend**: Python 3.10+
- **Frontend**: Node.js 16+
- **Raspberry Pi**: (프로덕션 환경에서만 필요)

### Backend 설정

```bash
cd backend

# 가상환경 생성 (Windows)
python -m venv venv
venv\Scripts\activate

# 가상환경 생성 (Linux/Mac)
python -m venv venv
source venv/bin/activate

# 의존성 설치
pip install -r requirements.txt

# 서버 실행
python main.py
```

백엔드 서버가 `http://localhost:8000`에서 실행됩니다.

### Frontend 설정

```bash
# 루트 디렉토리에서

# 의존성 설치
npm install

# 개발 서버 실행
npm run dev
```

프론트엔드가 `http://localhost:3000`에서 실행됩니다.

### Sensor Viewer 실행

```bash
cd sensor_view

# 가상환경 생성 (Windows)
python -m venv venv
venv\Scripts\activate

# 의존성 설치
pip install -r requirements.txt

# UI 실행
python app.py
```

## 📁 프로젝트 구조

```
Unitboardmonitoringdashboard/
├── backend/                     # 백엔드 (Litestar)
│   ├── app/
│   │   ├── main.py             # Litestar 앱 엔트리포인트
│   │   ├── config.py           # 설정 관리
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
├── sensor_view/                 # 센서 DB 조회 UI (Python)
│   ├── app.py                   # 메인 UI 앱
│   ├── requirements.txt         # UI 의존성
│   └── README.md
│
├── package.json
├── vite.config.ts
└── README.md
```

## 🔌 API 엔드포인트

### REST API (웹 프론트엔드용)

#### 1. 유닛보드 상태 조회

```http
GET /api/units/
GET /api/units/{unit_id}
GET /api/units/{unit_id}/gpio
```

#### 2. GPIO 제어

```http
POST /api/gpio/control
Content-Type: application/json

{
  "unit_id": 0,
  "gpio_index": 0,
  "state": true
}
```

#### 3. 모터 제어

```http
POST /api/gpio/motor
Content-Type: application/json

{
  "unit_id": 0,
  "is_on": true,
  "speed": 1500
}
```

### WebSocket

```javascript
ws://localhost:8000/ws/status
```

실시간 상태 업데이트를 위한 WebSocket 연결입니다.

### JSON 서버 (라즈베리파이 클라이언트용)

라즈베리파이 기반 메인 제어 프로그램과 통신하기 위한 JSON 서버입니다.

#### 포트 구성

- **포트 7000 (Send)**: 라즈베리파이 프로그램이 명령을 보내는 포트
- **포트 7001 (Receive)**: 라즈베리파이 프로그램이 상태를 받는 포트

#### 명령 프로토콜 (포트 7000)

라즈베리파이 프로그램에서 JSON 명령을 전송:

```json
{
  "command": "get_status",
  "unit_id": 0,
  "timestamp": 1234567890.123
}
```

지원하는 명령:
- `get_status`: 특정 유닛보드 상태 조회
- `get_all_units`: 모든 유닛보드 상태 조회
- `set_gpio`: GPIO 제어
- `set_motor`: 모터 제어
- `set_valve`: 밸브 제어
- `heartbeat`: 연결 확인

#### 응답 프로토콜 (포트 7000)

서버에서 JSON 응답을 반환:

```json
{
  "type": "success",
  "success": true,
  "unit_id": 0,
  "data": {
    "gpio_index": 0,
    "state": true
  },
  "timestamp": 1234567890.123
}
```

#### 상태 수신 (포트 7001)

라즈베리파이 프로그램이 연결하면, 서버가 주기적으로(1초마다) 모든 유닛보드 상태를 전송:

```json
{
  "type": "status",
  "success": true,
  "data": {
    "units": {
      "0": {
        "unit_id": 0,
        "is_connected": true,
        "sensors": {
          "temperature_1": 12.5,
          "temperature_2": 12.3,
          ...
        },
        "motor": {
          "is_on": false,
          "speed": 0
        },
        "valves": {
          "valve_1": false,
          ...
        },
        "gpio": [false, false, ...],
        "last_updated": "2024-01-01T00:00:00"
      },
      ...
    }
  },
  "timestamp": 1234567890.123
}
```

## 🎯 주요 기능

### 현재 구현된 기능

1. ✅ **유닛보드 상태 값 표시**
   - 센서 데이터 (온도, pH, CO₂, 유량, 당도, 로드셀)
   - 모터 상태 (ON/OFF, 속도)
   - 밸브 상태 (4개)

2. ✅ **GPIO 제어**
   - GPIO 1-8 개별 제어
   - 모터 속도 제어 (0-2000 RPM)
   - 모터 ON/OFF 제어

3. ✅ **유닛보드 선택**
   - 최대 32개 유닛보드 선택 가능

4. ✅ **시스템 에러 상태 표시**
   - SENSOR 패킷의 ERROR 배열에서 선택된 유닛보드의 에러 코드 표시
   - CODE `"0"` → 녹색 LED + "정상"
   - CODE `"0"` 외 → 빨간색 LED + "에러: {CODE}"

### 향후 구현 예정

- 레시피 실행 자동화
- 실시간 센서 모니터링 (WebSocket)
- 펌웨어 업데이트
- 설정 파일 기반 자동 구성

## 🔧 설정

### Backend 설정

`backend/.env` 파일을 생성하여 설정을 변경할 수 있습니다:

```env
HOST=0.0.0.0
PORT=9000
CAN_INTERFACE=socketcan
CAN_CHANNEL=can0
CAN_BITRATE=500000
CAN_FD=true
MAX_UNITS=20
JSON_SEND_PORT=7000
JSON_RECEIVE_PORT=7001
```

### Frontend 설정

`src/.env` 파일을 생성하여 API URL을 설정할 수 있습니다.

**Windows (로컬 개발) 예시:**
```env
VITE_API_BASE_URL=http://localhost:9000
VITE_WS_URL=ws://localhost:9000/ws/status
```

**Linux (라즈베리파이) 예시:**
```env
# 라즈베리파이의 IP 주소를 사용해야 합니다
VITE_API_BASE_URL=http://172.30.1.100:9000
VITE_WS_URL=ws://172.30.1.100:9000/ws/status
```

### 리눅스(라즈베리파이) 실행 가이드

라즈베리파이에서 실행 시 외부 접속을 허용하려면 다음과 같이 실행하세요:

```bash
# 외부 접속 허용 및 브라우저 자동 실행 방지
npm run dev -- --host --open=false
```

또는 `vite.config.ts` 파일에 설정을 추가할 수 있습니다.

**참고: 파일 감시자 한도 오류 (ENOSPC) 해결**
라즈베리파이에서 `Error: ENOSPC: System limit for number of file watchers reached` 오류가 발생하면 다음 명령어로 시스템 한계치를 늘려주세요:

```bash
echo fs.inotify.max_user_watches=524288 | sudo tee -a /etc/sysctl.conf && sudo sysctl -p
```

### 백엔드 호스트 설정 (Windows/Linux 공용)

백엔드의 펌웨어 업데이트 URL이나 IP 설정은 `backend/app/ini/sys.ini` 파일에서 관리합니다:

```ini
[FIRMWARE_UPDATE]
URL = http://172.30.1.100:8000/upload
DIR = C:/Projects/M-FACTORY/Software/control_server/Unitboardmonitoringdashboard/firmware/

[NETWORK]
HOST_IP = 172.30.1.100
```

## 🧪 테스트

### API 테스트

```bash
# 유닛보드 상태 조회
curl http://localhost:9000/api/units/0

# GPIO 제어
curl -X POST http://localhost:9000/api/gpio/control \
  -H "Content-Type: application/json" \
  -d '{"unit_id": 0, "gpio_index": 0, "state": true}'
```

## 📝 개발 가이드

자세한 개발 가이드는 [src/CURSOR_AI_GUIDE.md](src/CURSOR_AI_GUIDE.md)를 참고하세요.

## 📄 라이선스

이 프로젝트는 프라이빗 프로젝트입니다.

## 🤝 기여

프로젝트는 단계적으로 개발 중입니다. 현재 기본 구조와 핵심 기능이 구현되었으며, CAN-FD 통신 및 실제 하드웨어 연동은 다음 단계에서 진행됩니다.
