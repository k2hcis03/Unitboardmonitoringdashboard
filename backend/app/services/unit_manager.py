"""Unit board management service"""
import logging
from typing import Dict, Optional
from app.services.state_manager import state_manager
from app.models.unit import UnitStatus

logger = logging.getLogger(__name__)

class UnitManager:
    """유닛보드 관리 서비스"""
    
    async def get_unit_status(self, unit_id: int) -> Optional[UnitStatus]:
        """유닛보드 상태 조회
        
        라즈베리파이 클라이언트에서 받은 상태 데이터를 반환합니다.
        """
        status = await state_manager.get_unit_status(unit_id)
        return status
    
    async def get_all_units_status(self) -> Dict[int, UnitStatus]:
        """모든 유닛보드 상태 조회"""
        return await state_manager.get_all_units_status()
    
    async def control_gpio(self, unit_id: int, gpio_index: int, state: bool) -> bool:
        """GPIO 제어"""
        # 상태 관리자에 반영
        await state_manager.set_gpio_state(unit_id, gpio_index, state)
        logger.info(f"Unit {unit_id} GPIO {gpio_index} set to {state}")
        return True
    
    async def control_motor(self, unit_id: int, is_on: bool, speed: int = 0) -> bool:
        """모터 제어"""
        # 상태 관리자에 반영
        await state_manager.set_motor_state(unit_id, is_on, speed)
        logger.info(f"Unit {unit_id} Motor: {'ON' if is_on else 'OFF'}, Speed: {speed} RPM")
        return True


# 전역 유닛 관리자 인스턴스
unit_manager = UnitManager()

