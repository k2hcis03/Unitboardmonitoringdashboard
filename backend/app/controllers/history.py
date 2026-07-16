from typing import List, Optional, Dict
from litestar import Controller, get, post
from litestar.response import File
from litestar.status_codes import HTTP_200_OK
from pydantic import BaseModel

from app.services.tcp_bridge import tcp_bridge
from app.services.db_service import db_service
import pandas as pd
import io
import os
import logging

logger = logging.getLogger(__name__)

class RecordingStartRequest(BaseModel):
    recipe_id: Optional[str] = None
    reset_db: bool = False
    # 녹화를 시작할 유닛(탱크) ID. None이면 백엔드가 현재 선택한 유닛을 사용한다.
    unit_id: Optional[int] = None

class RecordingControlRequest(BaseModel):
    # 일시정지/종료할 유닛(탱크) ID. None이면 현재 선택한 유닛을 사용한다.
    unit_id: Optional[int] = None

class HistoryController(Controller):
    path = ""

    # Recording Control
    @post(path="/recording/start")
    async def start_recording(self, data: Optional[RecordingStartRequest] = None) -> dict:
        """특정 유닛(탱크)의 DB 녹화를 시작하고 STATE Run 명령을 전송한다."""
        recipe_id = data.recipe_id if data else None
        reset_db = data.reset_db if data else False
        # unit_id가 지정되지 않으면 현재 선택된 유닛을 사용한다.
        tank_id = data.unit_id if (data and data.unit_id is not None) else tcp_bridge.get_selected_unit_id()
        logger.info(f"Starting recording for tank {tank_id}. Recipe ID: {recipe_id}, reset_db: {reset_db}")
        # reset_db가 True면 해당 유닛의 데이터만 초기화한다. (다른 유닛 녹화 데이터는 보존)
        db_cleared = False
        if reset_db:
            db_cleared = await db_service.clear_tank(tank_id)
        # 해당 탱크만 STATE "Run"으로 전환 → 이후 SENSOR 패킷에서 이 탱크 데이터가 저장된다.
        await tcp_bridge.send_state_command("Run", unit_id=tank_id)
        return {
            "status": "started",
            "is_recording": True,
            "unit_id": tank_id,
            "recipe_id": recipe_id,
            "db_cleared": db_cleared,
        }

    @post(path="/recording/pause")
    async def pause_recording(self, data: Optional[RecordingControlRequest] = None) -> dict:
        """특정 유닛(탱크)의 DB 녹화를 일시정지하고 STATE Pause 명령을 전송한다."""
        tank_id = data.unit_id if (data and data.unit_id is not None) else tcp_bridge.get_selected_unit_id()
        await tcp_bridge.send_state_command("Pause", unit_id=tank_id)
        return {"status": "paused", "is_recording": False, "unit_id": tank_id}

    @post(path="/recording/stop")
    async def stop_recording(self, data: Optional[RecordingControlRequest] = None) -> dict:
        """특정 유닛(탱크)의 DB 녹화를 종료하고 STATE Stop 명령을 전송한다."""
        tank_id = data.unit_id if (data and data.unit_id is not None) else tcp_bridge.get_selected_unit_id()
        await tcp_bridge.send_state_command("Stop", unit_id=tank_id)
        return {"status": "stopped", "is_recording": False, "unit_id": tank_id}

    @get(path="/recording/status")
    async def get_recording_status(self) -> dict:
        """현재 녹화 상태(녹화 중인 유닛 목록 포함) 반환."""
        return tcp_bridge.get_recording_status()

    # History Query
    @get(path="/history/chart")
    async def get_chart_data(
        self, 
        start: str, 
        end: str, 
        tank_id: Optional[str] = None, 
        sensor_ids: Optional[List[int]] = None
    ) -> List[dict]:
        """
        Get data for charts.
        start/end format: YYYY-MM-DD HH:MM:SS
        """
        # Note: sensor_ids might need parsing if passed as comma-separated in some frameworks,
        # but Litestar usually handles List[int] via query params like ?sensor_ids=1&sensor_ids=2
        return await db_service.get_history(start, end, tank_id, sensor_ids)

    @get(path="/history/export")
    async def export_csv(
        self, 
        start: str, 
        end: str
    ) -> File:
        """Export data to CSV."""
        data = await db_service.get_export_data(start, end)
        
        df = pd.DataFrame(data)
        if df.empty:
             return File(
                path=io.BytesIO(b"No data"),
                filename="export.csv",
                content_disposition_type="attachment",
                media_type="text/csv"
            )

        # Convert to CSV
        csv_buffer = io.BytesIO()
        df.to_csv(csv_buffer, index=False)
        csv_buffer.seek(0)
        
        return File(
            path=csv_buffer,
            filename=f"sensor_data_{start}_{end}.csv",
            content_disposition_type="attachment",
            media_type="text/csv"
        )

