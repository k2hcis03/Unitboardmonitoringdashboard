# 유닛보드 모니터링 시스템 - Cursor AI 작업 가이드

## 🏗️ 프로젝트 구조

```
unitboard-system/
├── frontend/                    # React 프론트엔드
│   ├── src/
│   │   ├── App.tsx
│   │   ├── components/
│   │   │   ├── StatusMonitoringCard.tsx
│   │   │   ├── GPIOControlPanel.tsx
│   │   │   └── FunctionButtonPanel.tsx
│   │   ├── services/
│   │   │   └── api.ts          # 백엔드 통신 API
│   │   ├── hooks/
│   │   │   └── useWebSocket.ts # 실시간 데이터 수신
│   │   └── types/
│   │       └── index.ts        # TypeScript 타입 정의
│   └── package.json
│
└── backend/                     # Litestar 백엔드
    ├── main.py                  # Litestar 앱 진입점
    ├── routes/
    │   ├── sensors.py           # 센서 데이터 엔드포인트
    │   └── control.py           # GPIO/모터 제어 엔드포인트
    ├── hardware/
    │   ├── sensor_manager.py    # 센서 데이터 읽기
    │   ├── gpio_controller.py   # GPIO 제어
    │   └── motor_controller.py  # 모터 제어
    └── requirements.txt
```

---

## 📡 API 설계

### REST API 엔드포인트

#### 1. 센서 데이터 조회
```http
GET /api/sensors/status
```
**응답:**
```json
{
  "temperature": {
    "sensor1": 12.5,
    "sensor2": 12.3,
    "sensor3": 34.4,
    "sensor4": 20.2
  },
  "ph": 12.3,
  "co2": 12.3,
  "flow": 34.4,
  "brix": 20.2,
  "loadcell": 125.8,
  "motor_speed": 1250,
  "valves": {
    "valve1": true,
    "valve2": false,
    "valve3": true,
    "valve4": false
  }
}
```

#### 2. GPIO 제어
```http
POST /api/control/gpio
```
**요청:**
```json
{
  "gpio_number": 1,
  "state": true
}
```
**응답:**
```json
{
  "success": true,
  "gpio_number": 1,
  "state": true
}
```

#### 3. 모터 제어
```http
POST /api/control/motor
```
**요청:**
```json
{
  "on": true,
  "speed": 1500
}
```
**응답:**
```json
{
  "success": true,
  "motor_on": true,
  "motor_speed": 1500
}
```

### WebSocket 엔드포인트

#### 실시간 센서 데이터 스트리밍
```
ws://localhost:8000/ws/sensors
```
**메시지 형식:**
```json
{
  "type": "sensor_update",
  "timestamp": "2025-11-25T10:30:00Z",
  "data": {
    "temperature1": 12.5,
    "ph": 12.3,
    ...
  }
}
```

---

## 🎯 Cursor AI 프롬프트 예시

### 1️⃣ 백엔드 생성 (Litestar)

```
@새파일 backend/main.py를 생성해줘

Litestar를 사용한 백엔드 서버를 만들어줘:
- CORS 설정 (프론트엔드 http://localhost:5173 허용)
- REST API 라우트: /api/sensors/status, /api/control/gpio, /api/control/motor
- WebSocket 엔드포인트: /ws/sensors (1초마다 센서 데이터 전송)
- 현재는 더미 데이터 사용 (나중에 실제 하드웨어 연결)

requirements.txt도 함께 만들어줘:
- litestar
- uvicorn
- python-dotenv
```

### 2️⃣ 프론트엔드 API 서비스 생성

```
@새파일 frontend/src/services/api.ts를 생성해줘

백엔드 API와 통신하는 서비스를 만들어줘:
- axios 사용
- BASE_URL: http://localhost:8000
- getSensorStatus() - GET /api/sensors/status
- controlGPIO(gpioNumber, state) - POST /api/control/gpio
- controlMotor(on, speed) - POST /api/control/motor
- 에러 핸들링 포함
```

### 3️⃣ WebSocket Hook 생성

```
@새파일 frontend/src/hooks/useWebSocket.ts를 생성해줘

WebSocket으로 실시간 센서 데이터를 받는 커스텀 훅을 만들어줘:
- ws://localhost:8000/ws/sensors 연결
- 자동 재연결 로직
- 센서 데이터 state 관리
- 연결 상태 표시 (connected, disconnected, error)
```

### 4️⃣ App.tsx 업데이트 (백엔드 연동)

```
@App.tsx 를 수정해줘

백엔드와 연동하도록 변경해줘:
1. useWebSocket 훅으로 실시간 센서 데이터 수신
2. StatusMonitoringCard에 실시간 데이터 전달
3. GPIO 토글 시 API 호출 (api.controlGPIO)
4. 모터 속도 변경 시 API 호출 (api.controlMotor)
5. 연결 상태 표시 (우측 상단에 LED 인디케이터)
```

### 5️⃣ StatusMonitoringCard 업데이트

```
@StatusMonitoringCard.tsx 를 수정해줘

Props로 실시간 센서 데이터를 받도록 변경해줘:
- temperature1, temperature2, temperature3, temperature4
- ph, co2, flow, brix, loadcell
- motorSpeed, valve1, valve2, valve3, valve4

Props 타입 정의도 추가해줘.
```

### 6️⃣ GPIOControlPanel 업데이트

```
@GPIOControlPanel.tsx 를 수정해줘

GPIO 토글/모터 제어 시 로딩 상태를 표시하도록 개선해줘:
- 버튼 클릭 중 로딩 스피너 표시
- API 호출 성공/실패 toast 알림 (sonner 사용)
- 에러 발생 시 이전 상태로 롤백
```

---

## 🔧 하드웨어 연동 가이드 (백엔드)

### 7️⃣ Raspberry Pi GPIO 연동

```
@backend/hardware/gpio_controller.py 를 생성해줘

Raspberry Pi GPIO 제어 코드를 작성해줘:
- RPi.GPIO 또는 gpiod 라이브러리 사용
- GPIO 1-8번 핀 제어 함수
- set_gpio(pin, state) 함수
- get_gpio_state(pin) 함수
- 안전한 초기화/정리 (cleanup) 포함
```

### 8️⃣ 센서 데이터 읽기

```
@backend/hardware/sensor_manager.py 를 생성해줘

센서 데이터를 읽는 매니저 클래스를 만들어줘:
- read_temperature(sensor_id) - I2C 온도 센서 읽기
- read_ph() - pH 센서 읽기
- read_co2() - CO2 센서 읽기
- read_flow() - 유량 센서 읽기
- read_brix() - 당도 센서 읽기
- read_loadcell() - 로드셀 읽기 (HX711 사용)

현재는 랜덤 데이터 반환, 나중에 실제 센서 코드로 교체 가능하도록 설계
```

### 9️⃣ 모터 제어 (PWM)

```
@backend/hardware/motor_controller.py 를 생성해줘

모터 속도 제어 코드를 작성해줘:
- PWM 방식으로 0-2000 RPM 제어
- set_motor_speed(rpm) 함수
- get_motor_speed() 함수
- 모터 ON/OFF 함수
- 안전 장치 (최대/최소 속도 제한)
```

---

## 🚀 실행 방법

### 백엔드 실행
```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### 프론트엔드 실행
```bash
cd frontend
npm install
npm run dev
```

---

## 📝 TypeScript 타입 정의

```typescript
// frontend/src/types/index.ts

export interface SensorData {
  temperature: {
    sensor1: number;
    sensor2: number;
    sensor3: number;
    sensor4: number;
  };
  ph: number;
  co2: number;
  flow: number;
  brix: number;
  loadcell: number;
  motor_speed: number;
  valves: {
    valve1: boolean;
    valve2: boolean;
    valve3: boolean;
    valve4: boolean;
  };
}

export interface GPIOControlRequest {
  gpio_number: number;
  state: boolean;
}

export interface MotorControlRequest {
  on: boolean;
  speed: number;
}

export interface APIResponse<T> {
  success: boolean;
  data?: T;
  error?: string;
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
# API 테스트
curl http://localhost:8000/api/sensors/status

# GPIO 제어 테스트
curl -X POST http://localhost:8000/api/control/gpio \
  -H "Content-Type: application/json" \
  -d '{"gpio_number": 1, "state": true}'
```

### WebSocket 테스트
```bash
# websocat 설치 후
websocat ws://localhost:8000/ws/sensors
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

1. backend/ 폴더에 Litestar 기반 백엔드 생성
   - main.py: CORS, REST API, WebSocket
   - routes/: sensors.py, control.py
   - hardware/: 하드웨어 제어 모듈 (현재는 더미 데이터)

2. frontend/ 폴더에 React 프론트엔드 연동
   - services/api.ts: axios 기반 API 클라이언트
   - hooks/useWebSocket.ts: 실시간 데이터 수신
   - App.tsx 수정: 백엔드 연동

3. 실시간 센서 데이터 스트리밍 (1초 간격)

4. GPIO/모터 제어 시 즉시 백엔드로 전송

모든 파일을 생성하고 README.md도 만들어줘.
```
