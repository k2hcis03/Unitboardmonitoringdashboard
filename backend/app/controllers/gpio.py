"""GPIO control API controller"""
from litestar import Controller, post
from litestar.exceptions import NotFoundException
from app.models.gpio import GPIOControl, MotorControl, GPIOBulkControl
from app.models.protocol import CommandPacket, ControlValue, CommandPacketGpio, CommandPacketMotor
from app.services.unit_manager import unit_manager
from app.services.tcp_bridge import tcp_bridge

idx = 0
class GPIOController(Controller):
    """GPIO 제어 API 컨트롤러"""
    
    path = "/gpio"
    @post("/control", summary="GPIO 제어")
    async def control_gpio(self, data: GPIOControl) -> dict:
        """GPIO 상태를 제어합니다.
        
        Args:
            data: GPIO 제어 요청
        
        Returns:
            제어 결과
        """
        success = await unit_manager.control_gpio(
            unit_id=data.unit_id,
            gpio_index=data.gpio_index,
            state=data.state
        )
        
        if not success:
            raise NotFoundException(f"Failed to control GPIO on unit {data.unit_id}")
        
        return {
            "success": True,
            "unit_id": data.unit_id,
            "gpio_index": data.gpio_index,
            "state": data.state
        }
    
    @post("/motor", summary="모터 제어")
    async def control_motor(self, data: MotorControl) -> dict:
        """모터를 제어합니다.
        
        Args:
            data: 모터 제어 요청
        
        Returns:
            제어 결과
        """
        success = await unit_manager.control_motor(
            unit_id=data.unit_id,
            is_on=data.is_on,
            speed=data.speed or 0
        )
        # TODO: time도 unit_manager에 반영할지 결정 필요 (현재는 speed만 반영됨)
        
        if not success:
            raise NotFoundException(f"Failed to control motor on unit {data.unit_id}")
            
        import time
        import logging

        logger = logging.getLogger(__name__)
        global idx
        idx = idx + 1
        logger.info(f"Sending TEMP_RPM command for Unit {data.unit_id} (Tank {data.unit_id+101})")

        try:
            await tcp_bridge.send_command(CommandPacketMotor(
                cmd='TEMP_RPM',
                unit_id=data.unit_id+1,
                idx=str(idx),
                tank_id=str(data.unit_id+101),
                speed=data.speed if data.is_on else 0,
                onoff="ON" if data.speed else "OFF",
                dir= 0,
                time=data.time or 0,
            ))
            logger.info("Command sent successfully")
        except Exception as e:
            logger.error(f"Failed to send command: {e}")

        return {
            "success": True,
            "unit_id": data.unit_id,
            "motor_on": data.is_on,
            "speed": data.speed or 0,
            "time": data.time or 0
        }
    
    @post("/bulk", summary="GPIO 일괄 제어")
    async def control_gpio_bulk(self, data: GPIOBulkControl) -> dict:
        """모든 GPIO 상태를 한 번에 제어합니다.
        
        Args:
            data: GPIO 일괄 제어 요청
            
        Returns:
            제어 결과
        """
        # 각 GPIO를 순차적으로 제어
        results = []
        for gpio_index, state in enumerate(data.gpio_states):
            success = await unit_manager.control_gpio(
                unit_id=data.unit_id,
                gpio_index=gpio_index,
                state=state
            )
            results.append({
                "gpio_index": gpio_index,
                "state": state,
                "success": success
            })
        
        all_success = all(r["success"] for r in results)
        
        if not all_success:
            raise NotFoundException(f"Failed to control some GPIOs on unit {data.unit_id}")
        
        # 임시로 idx 생성 (예: 현재 타임스탬프 또는 랜덤)
        import time
        import logging
        logger = logging.getLogger(__name__)
        
        global idx
        idx = idx + 1
        logger.info(f"Sending CTRL command for Unit {data.unit_id} (Tank {data.unit_id+101})")

        try:
            # await tcp_bridge.send_command(CommandPacket(
            #     cmd='CTRL',
            #     idx=str(idx),
            #     tank_id=str(data.unit_id+101),
            #     ctrl=[
            #         ControlValue(
            #             sensor_id = str(i + 500),
            #             param0="ON" if state else "OFF",
            #             param1="ON" if state else "OFF"
            #         )
            #         for i, state in enumerate(data.gpio_states)
            #     ],
            # ))
            await tcp_bridge.send_command(CommandPacketGpio(
                cmd='SET_GPIO',
                unit_id=data.unit_id+1,
                idx=str(idx),
                tank_id=str(data.unit_id+101),
                value=[state for state in data.gpio_states],
            ))
            logger.info("Command sent successfully")
        except Exception as e:
            logger.error(f"Failed to send command: {e}")

        return {
            "success": True,
            "unit_id": data.unit_id,
            "gpio_states": data.gpio_states,
            "results": results
        }
        

