# 프로젝트 개요: Unitboard Monitoring Dashboard

라즈베리파이 4를 메인 제어 장치로 사용하고, CAN-FD 버스를 통해 최대 32개의 STM32G474 기반 유닛보드를 제어·모니터링하는 **양조장 제어 웹 소프트웨어**입니다.

## 시스템 구성
- **프론트엔드**: React (Vite + TypeScript + Radix UI + TailwindCSS) — 포트 3000
- **백엔드**: Python Litestar (async, Pydantic, SQLite) — 포트 9001
- **Sensor Viewer**: Python Tkinter 독립 앱 (`sensor_view/`)
- **라즈베리파이**: CAN-FD 네트워크로 유닛보드 제어

## 통신 구조
```
Browser → React (3000) ←REST+WebSocket→ Litestar (9001) ←TCP JSON→ 라즈베리파이 ←CAN-FD→ 유닛보드
```
- 포트 7000: 라즈베리파이 → 백엔드 (SENSOR 패킷 수신)
- 포트 7001: 백엔드 → 라즈베리파이 (명령 전송)

## TANK_ID 매핑
프론트엔드 index와 라즈베리파이 TANK_ID는 별도 매핑:
- 유닛보드 1 (index 0) → TANK_ID 601
- 유닛보드 2 (index 1) → TANK_ID 101
- 유닛보드 3~32 (index 2~31) → TANK_ID 102~131
- `src/config.ts`의 `UNIT_TO_TANK_ID`와 `backend/app/services/tcp_bridge.py`의 `UNIT_TO_TANK_ID`를 항상 동기화해야 함
