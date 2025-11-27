"""Unit board API controller"""
from litestar import Controller, get, post
from litestar.exceptions import NotFoundException
from typing import Dict
from app.models.unit import UnitStatus
from app.models.gpio import GPIOState
from app.services.unit_manager import unit_manager


class UnitController(Controller):
    """유닛보드 API 컨트롤러"""
    
    path = "/units"
    
    @get("/", summary="모든 유닛보드 상태 조회")
    async def get_all_units(self) -> Dict[int, UnitStatus]:
        """모든 유닛보드의 상태를 조회합니다."""
        units = await unit_manager.get_all_units_status()
        return units
    
    @get("/{unit_id:int}", summary="특정 유닛보드 상태 조회")
    async def get_unit_status(self, unit_id: int) -> UnitStatus:
        """특정 유닛보드의 상태를 조회합니다.
        
        Args:
            unit_id: 유닛보드 ID (0-31)
        
        Returns:
            유닛보드 상태
        """
        status = await unit_manager.get_unit_status(unit_id)
        if status is None:
            raise NotFoundException(f"Unit {unit_id} not found")
        return status
    
    @get("/{unit_id:int}/gpio", summary="GPIO 상태 조회")
    async def get_gpio_state(self, unit_id: int) -> GPIOState:
        """유닛보드의 GPIO 상태를 조회합니다.
        
        Args:
            unit_id: 유닛보드 ID (0-31)
        
        Returns:
            GPIO 상태 (8개)
        """
        from app.services.state_manager import state_manager
        gpio_state = await state_manager.get_gpio_state(unit_id)
        if gpio_state is None:
            raise NotFoundException(f"Unit {unit_id} not found")
        return gpio_state

