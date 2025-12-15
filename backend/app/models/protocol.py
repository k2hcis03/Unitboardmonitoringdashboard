from typing import List, Union, Optional
from pydantic import BaseModel, Field, field_validator

# -----------------------------------------------------------------------------
# 1. Sensor Data Structures
# -----------------------------------------------------------------------------

class SensorValue(BaseModel):
    # Support both string "100" and int 100 for TANK_ID based on user example
    tank_id: Union[str, int] = Field(..., alias="TANK_ID")
    sensor_id: int = Field(..., alias="SENSOR_ID")
    value: str = Field(..., alias="VALUE")

    @field_validator('tank_id')
    @classmethod
    def parse_tank_id(cls, v):
        return int(v) # Normalize to int internally

class TankState(BaseModel):
    tank_id: int = Field(..., alias="TANK_ID")
    stage: int = Field(..., alias="STAGE")
    status: str = Field(..., alias="STATUS")

class SensorPacket(BaseModel):
    cmd: str = Field("SENSOR", alias="CMD")
    order: int = Field(..., alias="ORDER")
    date: str = Field(..., alias="DATE")
    time: str = Field(..., alias="TIME")
    values: List[SensorValue] = Field(..., alias="VALUES")
    state: List[TankState] = Field(..., alias="STATE")

# -----------------------------------------------------------------------------
# 2. ACK Structures
# -----------------------------------------------------------------------------

class AckPacket(BaseModel):
    cmd: str = Field("ACK", alias="CMD")
    idx: Union[str, int] = Field(..., alias="IDX")
    note: str = Field("OK", alias="NOTE")

class AckPacketInitialize(BaseModel):
    cmd: str = Field("ACK_INITIALIZE", alias="CMD")
    idx: Union[str, int] = Field(..., alias="IDX")
    fw_version: int = Field(..., alias="FW_VERSION")
    note: str = Field("OK", alias="NOTE")
# -----------------------------------------------------------------------------
# 3. Command Structures (PC -> Pi) - Placeholder for Port 7001
# -----------------------------------------------------------------------------
class PingPacket(BaseModel):
    cmd: str = Field("PING", alias="CMD")
    idx: Union[str, int] = Field(..., alias="IDX")
    note: str = Field("OK", alias="NOTE")

class ControlValue(BaseModel):
    # Support both string "100" and int 100 for TANK_ID based on user example
    sensor_id: Union[str, int] = Field(..., alias="SENSOR_ID")
    param0: str = Field(..., alias="PARAM0")
    param1: str = Field(..., alias="PARAM1")

    class Config:
        populate_by_name = True

class CommandPacket(BaseModel):
    cmd: str = Field(..., alias="CMD")
    idx: Union[str, int] = Field(..., alias="IDX")
    tank_id: Union[str, int] = Field(..., alias="TANK_ID")
    ctrl: List[ControlValue] = Field(..., alias="CTRL")
    # Add other fields as needed for sending commands
    payload: Optional[dict] = Field(None, alias="PAYLOAD")

    class Config:
        populate_by_name = True
    
class CommandPacketGpio(BaseModel):
    cmd: str = Field(..., alias="CMD")
    unit_id: Union[str, int] = Field(..., alias="UNIT_ID")
    idx: Union[str, int] = Field(..., alias="IDX")
    tank_id: Union[str, int] = Field(..., alias="TANK_ID")
    value: List[bool] = Field(..., alias="VALUE", min_length=8, max_length=8)
    send: bool = Field(False, alias="SEND")
    # Add other fields as needed for sending commands
    payload: Optional[dict] = Field(None, alias="PAYLOAD")

    class Config:
        populate_by_name = True

class CommandPacketMotor(BaseModel):
    cmd: str = Field(..., alias="CMD")
    unit_id: Union[str, int] = Field(..., alias="UNIT_ID")
    idx: Union[str, int] = Field(..., alias="IDX")
    tank_id: Union[str, int] = Field(..., alias="TANK_ID")
    speed: Union[str, int] = Field(..., alias="SPEED")
    dir: Union[str, int] = Field(..., alias="DIR")
    onoff: Union[str, int] = Field(..., alias="ONOFF")
    time: Union[str, int] = Field(..., alias="TIME")
    send: bool = Field(False, alias="SEND")
    # Add other fields as needed for sending commands
    payload: Optional[dict] = Field(None, alias="PAYLOAD")

    class Config:
        populate_by_name = True

class CommandPacketFirmware(BaseModel):
    cmd: str = Field("FW_UPDATE", alias="CMD")
    unit_id: Union[str, int] = Field(..., alias="UNIT_ID")
    idx: Union[str, int] = Field(..., alias="IDX")
    file: str = Field(..., alias="FILE")
    send: bool = Field(False, alias="SEND")
    class Config:
        populate_by_name = True

class CommandPacketGetVersion(BaseModel):
    cmd: str = Field("GET_VERSION", alias="CMD")
    unit_id: Union[str, int] = Field(..., alias="UNIT_ID")
    idx: Union[str, int] = Field(..., alias="IDX")
    send: bool = Field(False, alias="SEND")
    class Config:
        populate_by_name = True

class RecipeDataItem(BaseModel):
    index: int = Field(..., alias="INDEX")
    temp: float = Field(..., alias="TEMP")
    temp_mgn: float = Field(..., alias="TEMP_MGN")
    m_time: int = Field(..., alias="M_TIME")
    m_rpm: int = Field(..., alias="M_RPM")
    
    class Config:
        populate_by_name = True

class CommandPacketRef(BaseModel):
    cmd: str = Field("REF", alias="CMD")
    idx: Union[str, int] = Field(..., alias="IDX")
    tank_id: Union[str, int] = Field(..., alias="TANK_ID")
    stage: Union[str, int] = Field(..., alias="STAGE")
    step: Union[str, int] = Field(..., alias="STEP")
    data: List[RecipeDataItem] = Field(..., alias="DATA")
    send: bool = Field(False, alias="SEND")
    
    class Config:
        populate_by_name = True

class StateDataItem(BaseModel):
    tank_id: Union[str, int] = Field(..., alias="TANK_ID")
    stage: int = Field(..., alias="STAGE")
    status: str = Field(..., alias="STATUS")
    
    class Config:
        populate_by_name = True

class CommandPacketState(BaseModel):
    cmd: str = Field("STATE", alias="CMD")
    idx: Union[str, int] = Field(..., alias="IDX")
    data: List[StateDataItem] = Field(..., alias="DATA")
    
    class Config:
        populate_by_name = True
