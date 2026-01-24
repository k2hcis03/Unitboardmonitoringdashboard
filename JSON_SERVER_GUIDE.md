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

## 상태 수신 (포트 7001)

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
