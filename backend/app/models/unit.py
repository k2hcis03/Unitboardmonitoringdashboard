"""Unit board models"""
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class UnitInfo(BaseModel):
    """유닛보드 기본 정보"""
    unit_id: int = Field(..., ge=0, le=31, description="유닛보드 ID (0-31)")
    name: Optional[str] = Field(None, description="유닛보드 이름")
    firmware_version: Optional[str] = Field(None, description="펌웨어 버전")
    is_connected: bool = Field(False, description="연결 상태")


class SensorReading(BaseModel):
    """센서 읽기 값"""
    temperature_1: float = Field(0.0, description="온도센서1 (°C)")
    temperature_2: float = Field(0.0, description="온도센서2 (°C)")
    temperature_3: float = Field(0.0, description="온도센서3 (°C)")
    temperature_4: float = Field(0.0, description="온도센서4 (°C)")
    ph: float = Field(0.0, description="pH 센서")
    co2: float = Field(0.0, description="CO₂ 센서 (ppm)")
    flow_rate: float = Field(0.0, description="유량 센서 (L/min)")
    brix: float = Field(0.0, description="당도 센서 (Brix)")
    load_cell: float = Field(0.0, description="로드셀 (kg)")


class MotorStatus(BaseModel):
    """모터 상태"""
    is_on: bool = Field(False, description="모터 ON/OFF")
    speed: int = Field(0, ge=0, le=2000, description="모터 속도 (RPM)")


class ValveStatus(BaseModel):
    """밸브 상태"""
    valve_1: bool = Field(False, description="밸브1")
    valve_2: bool = Field(False, description="밸브2")
    valve_3: bool = Field(False, description="밸브3")
    valve_4: bool = Field(False, description="밸브4")


class UnitStatus(BaseModel):
    """유닛보드 전체 상태"""
    unit_info: UnitInfo
    sensors: SensorReading
    motor: MotorStatus
    valves: ValveStatus
    last_updated: datetime = Field(default_factory=datetime.now, description="마지막 업데이트 시간")

class FirmwareUpdateRequest(BaseModel):
    """펌웨어 업데이트 요청"""
    file_path: str = Field(..., description="펌웨어 파일 경로")
