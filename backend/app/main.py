"""Main Litestar application"""
from litestar import Litestar, Router
from litestar.config.cors import CORSConfig
from litestar.openapi import OpenAPIConfig
from litestar.logging import LoggingConfig
from app.config import settings
from app.controllers.unit import UnitController
from app.controllers.gpio import GPIOController
from app.controllers.history import HistoryController
from app.controllers.websocket import websocket_handler
from app.services.tcp_bridge import tcp_bridge
from app.utils.logger import setup_logging
import logging

# 로깅 설정
setup_logging()
logger = logging.getLogger(__name__)

# 라우터 생성
api_router = Router(
    path="/api",
    route_handlers=[
        UnitController,
        GPIOController,
        HistoryController,
    ]
)

# WebSocket 라우터
ws_router = Router(
    path="/ws",
    route_handlers=[
        websocket_handler,
    ]
)

# CORS 설정
cors_config = CORSConfig(
    allow_origins=settings.cors_origins,
    allow_methods=["*"],
    allow_headers=["*"],
    allow_credentials=True,
)

# OpenAPI 설정
openapi_config = OpenAPIConfig(
    title="Unit Board Control API",
    version="0.1.0",
    description="유닛보드 모니터링 및 제어 시스템 API",
)

# 로깅 설정
logging_config = LoggingConfig(
    root={
        "level": "INFO",
        "handlers": ["console"],
    },
    formatters={
        "standard": {
            "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        }
    }
)

# Startup 핸들러
async def startup() -> None:
    """애플리케이션 시작 시 실행"""
    logger.info("Starting Unit Board Control Backend...")
    await tcp_bridge.start()


# Shutdown 핸들러
async def shutdown() -> None:
    """애플리케이션 종료 시 실행"""
    logger.info("Shutting down Unit Board Control Backend...")
    await tcp_bridge.stop()


# Litestar 앱 생성
app = Litestar(
    route_handlers=[
        api_router,
        ws_router,
    ],
    cors_config=cors_config,
    openapi_config=openapi_config,
    logging_config=logging_config,
    on_startup=[startup],
    on_shutdown=[shutdown],
)


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.reload,
    )

