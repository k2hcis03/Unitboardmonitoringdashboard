"""Application configuration"""
from pydantic_settings import BaseSettings
from typing import Optional, List


class Settings(BaseSettings):
    """Application settings"""
    
    # Server settings
    host: str = "0.0.0.0"
    port: int = 9001
    reload: bool = True
    
    # Unit board settings
    max_units: int = 32  # 최대 유닛보드 수
    
    # Database settings
    db_path: str = "sensor_data.db"
    retention_days: int = 30
    max_db_size_mb: int = 500  # Default 500MB
    
    # CORS settings
    cors_origins: List[str] = [
        "http://localhost:3000",
        "http://localhost:5173",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
        "http://172.30.1.100:3000",
        "http://172.30.1.100:5173",
        "*", # Development only
    ]
    
    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()

