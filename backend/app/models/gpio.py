"""GPIO control models"""
from pydantic import BaseModel, Field
from typing import List, Optional


class GPIOState(BaseModel):
    """GPIO 상태"""
    gpio_states: List[bool] = Field(
        ..., 
        min_length=8, 
        max_length=8, 
        description="GPIO 1-8 상태 (True=ON, False=OFF)"
    )


class GPIOControl(BaseModel):
    """GPIO 제어 요청"""
    unit_id: int = Field(..., ge=0, le=31, description="유닛보드 ID")
    gpio_index: int = Field(..., ge=0, le=7, description="GPIO 번호 (0-7, GPIO1-8)")
    state: bool = Field(..., description="설정할 상태 (True=ON, False=OFF)")


class MotorControl(BaseModel):
    """모터 제어 요청"""
    unit_id: int = Field(..., ge=0, le=31, description="유닛보드 ID")
    is_on: bool = Field(..., description="모터 ON/OFF")
    speed: Optional[int] = Field(None, ge=0, le=2000, description="모터 속도 (RPM, 0-2000)")
    dir: Optional[int] = Field(None, description="모터 방향")
    time: Optional[int] = Field(None, ge=0, le=60, description="모터 작동 시간 (0-60s)")


class GPIOBulkControl(BaseModel):
    """GPIO 일괄 제어 요청"""
    unit_id: int = Field(..., ge=0, le=31, description="유닛보드 ID")
    gpio_states: List[bool] = Field(
        ..., 
        min_length=8, 
        max_length=8, 
        description="GPIO 1-8 상태 (True=ON, False=OFF)"
    )
