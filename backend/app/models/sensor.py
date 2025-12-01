"""Sensor data models"""
from pydantic import BaseModel, Field


class SensorData(BaseModel):
    """센서 데이터"""
    temperature_1: float = Field(0.0, description="온도센서1 (°C)")
    temperature_2: float = Field(0.0, description="온도센서2 (°C)")
    temperature_3: float = Field(0.0, description="온도센서3 (°C)")
    temperature_4: float = Field(0.0, description="온도센서4 (°C)")
    temperature_5: float = Field(0.0, description="온도센서5 (°C)")
    temperature_6: float = Field(0.0, description="온도센서6 (°C)")
    temperature_7: float = Field(0.0, description="온도센서7 (°C)")
    temperature_8: float = Field(0.0, description="온도센서8 (°C)")
    ph: float = Field(0.0, description="pH 센서")
    co2: float = Field(0.0, description="CO₂ 센서 (ppm)")
    flow_rate: float = Field(0.0, description="유량 센서 (L/min)")
    brix: float = Field(0.0, description="당도 센서 (Brix)")
    load_cell: float = Field(0.0, description="로드셀 (kg)")


class SensorReading(BaseModel):
    """센서 읽기 (별칭)"""
    pass

