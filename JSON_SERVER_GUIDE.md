# JSON Server Guide

라즈베리파이 메인 제어 프로그램과 통신하는 JSON 서버의 기본 규격을 정리합니다.

## 포트 구성

- **포트 7000 (Send)**: 라즈베리파이 프로그램이 명령을 보내는 포트
- **포트 7001 (Receive)**: 라즈베리파이 프로그램이 상태를 받는 포트

## 명령 프로토콜 (포트 7000)

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

## 응답 프로토콜 (포트 7000)

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

## 상태 수신 (포트 7000 - Receiver)

라즈베리파이 프로그램이 TCP 포트 7000으로 연결하여 주기적으로 SENSOR 패킷을 전송합니다.

### SENSOR 패킷 포맷

```json
{
  "CMD": "SENSOR",
  "ORDER": 1535,
  "DATE": "2023-06-16",
  "TIME": "09:08:07",
  "VALUES": [
    {"TANK_ID": "100", "SENSOR_ID": 1100, "VALUE": "20.2"},
    {"TANK_ID": "100", "SENSOR_ID": 1101, "VALUE": "19.8"},
    {"TANK_ID": "101", "SENSOR_ID": 1100, "VALUE": "21.0"}
  ],
  "STATE": [
    {"TANK_ID": 100, "STAGE": 0, "STATUS": "None"},
    {"TANK_ID": 101, "STAGE": 100, "STATUS": "Run"}
  ],
  "ERROR": [
    {"TANK_ID": 100, "CODE": "0"},
    {"TANK_ID": 101, "CODE": "1"},
    {"TANK_ID": 102, "CODE": "2"}
  ]
}
```

#### ERROR 필드 설명

| 필드 | 타입 | 설명 |
|------|------|------|
| TANK_ID | int/string | 탱크(유닛보드) ID |
| CODE | string | 에러 코드. `"0"` = 정상, 그 외 값 = 에러 (프론트엔드에 에러 코드 표시) |

- ERROR 배열은 선택적(optional)이며, 없을 경우 빈 배열로 처리됩니다.
- 프론트엔드는 현재 선택된 유닛보드의 TANK_ID에 해당하는 ERROR 항목을 찾아 시스템 상태를 표시합니다.

## 명령 전송 (포트 7001 - Sender)

PC(백엔드)에서 라즈베리파이로 명령을 전송하는 포트입니다.

### 상태 수신 (레거시 포맷)

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
          "temperature_2": 12.3
        },
        "motor": {
          "is_on": false,
          "speed": 0
        },
        "valves": {
          "valve_1": false
        },
        "gpio": [false, false, false, false],
        "last_updated": "2024-01-01T00:00:00"
      }
    }
  },
  "timestamp": 1234567890.123
}
```
