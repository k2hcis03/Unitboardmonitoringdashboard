# 유닛보드 모니터링 시스템 - Cursor AI 작업 가이드

## 🏗️ 프로젝트 구조

```
Unitboardmonitoringdashboard/
├── src/                         # React 프론트엔드
│   ├── App.tsx
│   ├── components/
│   │   ├── StatusMonitoringCard.tsx
│   │   ├── GPIOControlPanel.tsx
│   │   ├── FunctionButtonPanel.tsx
│   │   └── ui/                  # shadcn/ui 컴포넌트
│   ├── services/
│   │   └── api.ts              # 백엔드 통신 API
│   ├── hooks/
│   │   └── useWebSocket.ts     # 실시간 데이터 수신
│   └── main.tsx
│
├── sensor_view/                 # 센서 DB 조회 UI (Python)
│   ├── app.py                   # Tkinter 기반 UI
│   ├── requirements.txt
│   └── README.md
│
└── backend/                     # Litestar 백엔드
    ├── main.py                  # 진입점 (uvicorn 실행)
    ├── app/
    │   ├── main.py             # Litestar 앱 정의
    │   ├── config.py           # 설정 관리
    │   ├── models/             # Pydantic 모델
    │   │   ├── unit.py         # 유닛보드 상태 모델
    │   │   ├── gpio.py         # GPIO 제어 모델
    │   │   ├── sensor.py       # 센서 데이터 모델
    │   ├── controllers/        # API 컨트롤러
    │   │   ├── unit.py         # 유닛보드 상태 API
    │   │   ├── gpio.py         # GPIO 제어 API
    │   │   └── websocket.py    # WebSocket 핸들러
    │   ├── services/           # 비즈니스 로직
    │   │   ├── unit_manager.py # 유닛보드 관리
    │   │   └── state_manager.py # 상태 관리
    │   └── utils/
    │       └── logger.py       # 로깅 설정
    ├── requirements.txt
```

---

## 📡 API 설계

### REST API 엔드포인트 (웹 프론트엔드용)

#### 1. 유닛보드 상태 조회
```http
GET /api/units/
GET /api/units/{unit_id}
GET /api/units/{unit_id}/gpio
```
**응답 예시:**
```json
{
  "unit_info": {
    "unit_id": 0,
    "name": "Unit 0",
    "firmware_version": "v0.0.0",
    "is_connected": true
  },
  "sensors": {
    "temperature_1": 12.5,
    "temperature_2": 12.3,
    "temperature_3": 34.4,
    "temperature_4": 20.2,
    "ph": 12.3,
    "co2": 12.3,
    "flow_rate": 34.4,
    "brix": 20.2,
    "load_cell": 125.8
  },
  "motor": {
    "is_on": false,
    "speed": 0
  },
  "valves": {
    "valve_1": false,
    "valve_2": false,
    "valve_3": false,
    "valve_4": false
  },
  "last_updated": "2024-01-01T00:00:00"
}
```

#### 2. GPIO 제어 (개별)
```http
POST /api/gpio/control
```
**요청:**
```json
{
  "unit_id": 0,
  "gpio_index": 0,
  "state": true
}
```

#### 3. GPIO 일괄 제어 (모든 GPIO 상태 한 번에)
```http
POST /api/gpio/bulk
```
**요청:**
```json
{
  "unit_id": 0,
  "gpio_states": [true, false, true, false, false, false, false, false]
}
```
**응답:**
```json
{
  "success": true,
  "unit_id": 0,
  "gpio_states": [true, false, true, false, false, false, false, false],
  "results": [
    {"gpio_index": 0, "state": true, "success": true},
    ...
  ]
}
```

#### 4. 모터 제어
```http
POST /api/gpio/motor
```
**요청:**
```json
{
  "unit_id": 0,
  "is_on": true,
  "speed": 1500
}
```

### WebSocket 엔드포인트

#### 실시간 상태 업데이트
```
ws://localhost:8000/ws/status
```
**메시지 형식:**
```json
{
  "type": "status_update",
  "unit_id": 0,
  "data": {
    "sensors": {...},
    "motor": {...},
    "valves": {...},
    "gpio": [true, false, ...]
  }
}
```

---

## 🎯 Cursor AI 프롬프트 예시

### 1️⃣ 백엔드 생성 (Litestar)

```
@backend/app/main.py를 생성해줘

Litestar를 사용한 백엔드 서버를 만들어줘:
- CORS 설정 (프론트엔드 http://localhost:5173 허용)
- REST API 라우트: 
  - GET /api/units/ (모든 유닛보드 상태)
  - GET /api/units/{unit_id} (특정 유닛보드 상태)
  - POST /api/gpio/control (GPIO 개별 제어)
  - POST /api/gpio/bulk (GPIO 일괄 제어)
  - POST /api/gpio/motor (모터 제어)
- WebSocket 엔드포인트: /ws/status (실시간 상태 업데이트)

requirements.txt:
- litestar>=2.0.0
- uvicorn[standard]>=0.24.0
- pydantic>=2.0.0
- pydantic-settings>=2.0.0
- websockets>=12.0
```

### 2️⃣ 프론트엔드 API 서비스 생성

```
@src/services/api.ts를 생성해줘

백엔드 API와 통신하는 서비스를 만들어줘:
- fetch API 사용 (axios 대신)
- BASE_URL: http://localhost:8000 (환경 변수로 설정 가능)
- getAllUnitsStatus() - GET /api/units/
- getUnitStatus(unitId) - GET /api/units/{unit_id}
- getGPIOState(unitId) - GET /api/units/{unit_id}/gpio
- controlGPIO(request) - POST /api/gpio/control (개별 제어)
- controlGPIOBulk(request) - POST /api/gpio/bulk (일괄 제어)
- controlMotor(request) - POST /api/gpio/motor
- 에러 핸들링 포함
```

### 3️⃣ WebSocket Hook 생성

```
@src/hooks/useWebSocket.ts를 생성해줘

WebSocket으로 실시간 상태 데이터를 받는 커스텀 훅을 만들어줘:
- ws://localhost:8000/ws/status 연결
- 자동 재연결 로직
- 유닛보드 상태 데이터 state 관리
- 연결 상태 표시 (connected, disconnected, error)
- 여러 유닛보드 상태 동시 관리
```

### 4️⃣ App.tsx 업데이트 (백엔드 연동)

```
@src/App.tsx를 수정해줘

백엔드와 연동하도록 변경해줘:
1. 유닛보드 ID 상태 관리 (기본값: 0)
2. GPIO 상태 관리 (8개 GPIO)
3. GPIO 토글 시 controlGPIOBulk() 호출 - 모든 GPIO 상태를 한 번에 전송
4. 모터 제어 시 controlMotor() 호출
5. FunctionButtonPanel에 유닛보드 선택 기능 연동
6. 에러 발생 시 이전 상태로 롤백
```

### 5️⃣ StatusMonitoringCard 업데이트

```
@src/components/StatusMonitoringCard.tsx를 수정해줘

백엔드에서 유닛보드 상태 데이터를 받아 표시하도록 변경해줘:
- Props로 unitId와 UnitStatus 받기
- 또는 useWebSocket 훅으로 실시간 데이터 수신
- 센서 데이터: temperature_1~4, ph, co2, flow_rate, brix, load_cell
- 모터 상태: motor.is_on, motor.speed
- 밸브 상태: valves.valve_1~4
- 유닛보드 연결 상태 표시

Props 타입 정의도 추가해줘.
```

### 6️⃣ GPIOControlPanel 업데이트

```
@src/components/GPIOControlPanel.tsx를 수정해줘

GPIO 토글/모터 제어 시 로딩 상태를 표시하도록 개선해줘:
- 버튼 클릭 중 로딩 스피너 표시
- API 호출 성공/실패 toast 알림 (sonner 사용)
- 에러 발생 시 이전 상태로 롤백
- GPIO 변경 시 모든 GPIO 상태를 일괄 전송 (controlGPIOBulk 사용)
```

---

## 🔧 시스템 아키텍처

### 통신 구조

```
Windows PC Browser (프론트엔드)
    ↓ REST API / WebSocket
Litestar Backend (포트 9000)
```

### 주요 특징

1. **상태 관리**
   - `StateManager`: 메모리 기반 상태 저장
   - `UnitManager`: 유닛보드 제어 및 상태 관리

---

## 🚀 실행 방법

### 백엔드 실행
```bash
cd backend

# 가상환경 생성 (처음 한 번만)
python -m venv venv

# 가상환경 활성화
# Windows PowerShell:
.\venv\Scripts\Activate.ps1
# Linux/Mac:
source venv/bin/activate

# 의존성 설치
pip install -r requirements.txt

# 서버 실행
python main.py
# 또는
uvicorn app.main:app --reload --host 0.0.0.0 --port 9000
```

서버가 다음 주소에서 실행됩니다:
- 웹 API: http://localhost:9000
- API 문서: http://localhost:9000/docs

### 프론트엔드 실행
```bash
# 루트 디렉토리에서
npm install
npm run dev
```

프론트엔드가 http://localhost:5173 에서 실행됩니다.

---

## 📝 TypeScript 타입 정의

```typescript
// src/services/api.ts에 정의됨

export interface UnitStatus {
  unit_info: {
    unit_id: number;
    name: string | null;
    firmware_version: string | null;
    is_connected: boolean;
  };
  sensors: {
    temperature_1: number;
    temperature_2: number;
    temperature_3: number;
    temperature_4: number;
    ph: number;
    co2: number;
    flow_rate: number;
    brix: number;
    load_cell: number;
  };
  motor: {
    is_on: boolean;
    speed: number;
  };
  valves: {
    valve_1: boolean;
    valve_2: boolean;
    valve_3: boolean;
    valve_4: boolean;
  };
  last_updated: string;
}

export interface GPIOControlRequest {
  unit_id: number;
  gpio_index: number;
  state: boolean;
}

export interface GPIOBulkControlRequest {
  unit_id: number;
  gpio_states: boolean[]; // GPIO 1-8 상태
}

export interface MotorControlRequest {
  unit_id: number;
  is_on: boolean;
  speed?: number;
}
```

---

## 🔒 보안 고려사항

1. **API 인증**: JWT 토큰 기반 인증 추가
2. **HTTPS**: 프로덕션 환경에서 SSL 인증서 사용
3. **Rate Limiting**: 과도한 요청 방지
4. **입력 검증**: 센서 값/제어 명령 범위 체크

---

## 📊 모니터링 & 로깅

```
@backend/utils/logger.py 를 생성해줘

로깅 시스템을 구축해줘:
- 모든 센서 데이터 읽기 로그
- GPIO/모터 제어 명령 로그
- 에러 로그 (파일 + 콘솔)
- 로그 파일 로테이션
- 타임스탬프 포함
```

---

## 🧪 테스트

### 백엔드 테스트
```bash
# 모든 유닛보드 상태 조회
curl http://localhost:8000/api/units/

# 특정 유닛보드 상태 조회
curl http://localhost:8000/api/units/0

# GPIO 개별 제어
curl -X POST http://localhost:8000/api/gpio/control \
  -H "Content-Type: application/json" \
  -d '{"unit_id": 0, "gpio_index": 0, "state": true}'

# GPIO 일괄 제어
curl -X POST http://localhost:8000/api/gpio/bulk \
  -H "Content-Type: application/json" \
  -d '{"unit_id": 0, "gpio_states": [true, false, true, false, false, false, false, false]}'

# 모터 제어
curl -X POST http://localhost:8000/api/gpio/motor \
  -H "Content-Type: application/json" \
  -d '{"unit_id": 0, "is_on": true, "speed": 1500}'
```

### WebSocket 테스트
```bash
# websocat 설치 후
websocat ws://localhost:8000/ws/status
```

---

## 🎨 추가 개선 사항

1. **데이터 시각화**: Recharts로 센서 데이터 그래프
2. **알림 시스템**: 센서 값 임계치 초과 시 알림
3. **데이터 저장**: SQLite/PostgreSQL에 센서 데이터 저장
4. **히스토리 조회**: 과거 데이터 조회 기능
5. **사용자 관리**: 다중 사용자 권한 관리

---

## 📞 Cursor AI에게 전체 시스템 생성 요청

```
이 프로젝트 구조를 기반으로 전체 시스템을 생성해줘:

1. backend/app/ 폴더에 Litestar 기반 백엔드 생성
   - main.py: CORS, REST API, WebSocket
   - controllers/: unit.py, gpio.py, websocket.py
   - services/: unit_manager.py, state_manager.py
   - models/: unit.py, gpio.py, sensor.py
   - config.py: 설정 관리

2. src/ 폴더에 React 프론트엔드 연동
   - services/api.ts: fetch 기반 API 클라이언트
   - hooks/useWebSocket.ts: 실시간 데이터 수신
   - App.tsx: 백엔드 연동, GPIO 일괄 제어
   - components/: StatusMonitoringCard, GPIOControlPanel, FunctionButtonPanel

3. GPIO 제어 시 모든 GPIO 상태를 일괄 전송 (controlGPIOBulk)

5. 유닛보드 선택 기능 (최대 32개)

모든 파일을 생성하고 README.md도 만들어줘.
```

## 🔄 현재 구현 상태

### ✅ 완료된 기능
- [x] Litestar 백엔드 구조
- [x] REST API 엔드포인트 (유닛보드, GPIO, 모터)
- [x] GPIO 일괄 제어 API
- [x] WebSocket 실시간 상태 업데이트
- [x] 프론트엔드 API 클라이언트
- [x] GPIO 제어 UI 연동
- [x] 유닛보드 선택 기능
- [x] Raw JSON 직접 전송 기능 (POST /api/gpio/raw-json)

### 🚧 향후 구현 예정
- [ ] 레시피 실행 기능
- [ ] 펌웨어 업데이트
- [ ] 실시간 센서 데이터 WebSocket 연동
- [ ] 상태 모니터링 카드 백엔드 연동
- [ ] 에러 처리 및 로깅 개선

---

## 📡 SENSOR 패킷 ERROR 필드

라즈베리파이에서 전송하는 SENSOR JSON 패킷에 `ERROR` 배열이 포함됩니다.

### 데이터 포맷
```json
{
  "CMD": "SENSOR",
  "ERROR": [
    {"TANK_ID": 100, "CODE": "0"},
    {"TANK_ID": 101, "CODE": "1"}
  ]
}
```

### 백엔드 모델 (`protocol.py`)
```python
class ErrorItem(BaseModel):
    tank_id: Union[str, int] = Field(..., alias="TANK_ID")
    code: str = Field(..., alias="CODE")

class SensorPacket(BaseModel):
    # ... 기존 필드 ...
    error: List[ErrorItem] = Field(default_factory=list, alias="ERROR")
```

### 프론트엔드 처리 (`FunctionButtonPanel.tsx`)
- SENSOR_UPDATE WebSocket 메시지에서 ERROR 배열을 읽음
- 현재 선택된 유닛보드의 TANK_ID에 매칭되는 ERROR 항목을 찾음
- CODE가 `"0"`이면 녹색 LED + "정상" 표시
- CODE가 `"0"`이 아니면 빨간색 LED + "에러: {CODE}" 표시

---

## 📤 Raw JSON 직접 전송 기능

사용자가 직접 JSON을 입력하여 라즈베리파이로 전송할 수 있는 기능입니다.

### API 엔드포인트
```http
POST /api/gpio/raw-json
Content-Type: application/json

{
  "UNIT_ID": 601,
  "IDX": 1,
  "TANK_ID": "601",
  "CMD": "TEMP_RPM",
  "SPEED": 1000,
  "DIR": "FW",
  "ONOFF": "ON",
  "TIME": 300,
  "SEND": true
}
```

### 프론트엔드 UI
- "JSON 전송" 버튼 클릭 시 입력 패널 표시
- textarea에 JSON 입력 후 "전송" 버튼으로 전송
- "템플릿" 버튼: 현재 선택된 유닛보드 기준 기본 JSON 템플릿 생성
- "초기화" 버튼: 입력 내용 초기화
