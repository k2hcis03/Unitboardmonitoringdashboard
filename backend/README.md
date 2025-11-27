# Unit Board Control Backend

라즈베리파이 4 기반 유닛보드 모니터링 및 제어 시스템 백엔드

## 기술 스택

- **Litestar**: 고성능 Python 웹 프레임워크
- **Python-CAN**: CAN-FD 버스 통신
- **WebSocket**: 실시간 상태 업데이트

## 설치

```bash
# 가상환경 생성
python -m venv venv

# 가상환경 활성화 (Windows)
venv\Scripts\activate

# 의존성 설치
pip install -r requirements.txt
```

## 실행

```bash
python main.py
```

또는

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

## 프로젝트 구조

```
backend/
├── app/
│   ├── __init__.py
│   ├── main.py              # Litestar 앱 엔트리포인트
│   ├── config.py            # 설정 관리
│   ├── models/              # Pydantic 모델
│   │   ├── __init__.py
│   │   ├── unit.py
│   │   ├── gpio.py
│   │   └── sensor.py
│   ├── controllers/         # API 컨트롤러
│   │   ├── __init__.py
│   │   ├── unit.py
│   │   ├── gpio.py
│   │   └── websocket.py
│   ├── services/            # 비즈니스 로직
│   │   ├── __init__.py
│   │   ├── can_bus.py       # CAN-FD 통신 서비스
│   │   ├── unit_manager.py  # 유닛보드 관리
│   │   └── state_manager.py # 상태 관리
│   └── utils/
│       ├── __init__.py
│       └── logger.py
├── requirements.txt
├── pyproject.toml
└── README.md
```

