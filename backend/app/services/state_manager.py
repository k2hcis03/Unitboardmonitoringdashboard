"""State management service"""
from typing import Dict, Optional
from datetime import datetime
from app.models.unit import UnitStatus, UnitInfo, SensorReading, MotorStatus, ValveStatus
from app.models.gpio import GPIOState
import asyncio
import logging

logger = logging.getLogger(__name__)

class StateManager:
    """유닛보드 상태 관리 서비스"""
    
    def __init__(self, max_units: int = 20):
        self.max_units = max_units
        self._units: Dict[int, UnitStatus] = {}
        self._gpio_states: Dict[int, GPIOState] = {}
        self._lock = asyncio.Lock()
        self._initialize_units()
    
    def _initialize_units(self):
        """유닛보드 초기 상태 설정"""
        for unit_id in range(self.max_units):
            unit_info = UnitInfo(
                unit_id=unit_id,
                name=f"Unit {unit_id}",
                firmware_version="v0.0.0",
                is_connected=False
            )
            
            sensors = SensorReading(
                temperature_1=12.5,
                temperature_2=12.3,
                temperature_3=34.4,
                temperature_4=20.2,
                ph=12.3,
                co2=12.3,
                flow_rate=34.4,
                brix=20.2,
                load_cell=125.8
            )
            
            motor = MotorStatus(is_on=False, speed=0)
            valves = ValveStatus(valve_1=False, valve_2=False, valve_3=False, valve_4=False)
            
            self._units[unit_id] = UnitStatus(
                unit_info=unit_info,
                sensors=sensors,
                motor=motor,
                valves=valves,
                last_updated=datetime.now()
            )
            
            # GPIO 초기화
            self._gpio_states[unit_id] = GPIOState(gpio_states=[False] * 8)
    
    async def get_unit_status(self, unit_id: int) -> Optional[UnitStatus]:
        """유닛보드 상태 조회"""
        async with self._lock:
            return self._units.get(unit_id)
    
    async def get_all_units_status(self) -> Dict[int, UnitStatus]:
        """모든 유닛보드 상태 조회"""
        async with self._lock:
            return self._units.copy()
    
    async def update_unit_status(self, unit_id: int, status: UnitStatus):
        """유닛보드 상태 업데이트"""
        async with self._lock:
            if unit_id < self.max_units:
                status.last_updated = datetime.now()
                self._units[unit_id] = status
    
    async def get_gpio_state(self, unit_id: int) -> Optional[GPIOState]:
        """GPIO 상태 조회"""
        async with self._lock:
            return self._gpio_states.get(unit_id)
    
    async def set_gpio_state(self, unit_id: int, gpio_index: int, state: bool) -> bool:
        """GPIO 상태 설정"""
        async with self._lock:
            if unit_id not in self._gpio_states:
                return False
            
            if 0 <= gpio_index < 8:
                self._gpio_states[unit_id].gpio_states[gpio_index] = state
                return True
            return False
    
    async def set_motor_state(self, unit_id: int, is_on: bool, speed: Optional[int] = None) -> bool:
        """모터 상태 설정"""
        async with self._lock:
            if unit_id not in self._units:
                return False
            
            unit = self._units[unit_id]
            unit.motor.is_on = is_on
            if speed is not None:
                unit.motor.speed = speed
            unit.last_updated = datetime.now()
            return True
    
    async def set_valve_state(self, unit_id: int, valve_index: int, state: bool) -> bool:
        """밸브 상태 설정"""
        async with self._lock:
            if unit_id not in self._units:
                return False
            
            unit = self._units[unit_id]
            valve_map = {
                0: 'valve_1',
                1: 'valve_2',
                2: 'valve_3',
                3: 'valve_4'
            }
            
            if valve_index in valve_map:
                setattr(unit.valves, valve_map[valve_index], state)
                unit.last_updated = datetime.now()
                return True
            return False


# 전역 상태 관리자 인스턴스
state_manager = StateManager(max_units=20)

