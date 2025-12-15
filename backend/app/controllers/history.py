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

class HistoryController(Controller):
    path = ""

    # Recording Control
    @post(path="/recording/start")
    async def start_recording(self, data: Optional[RecordingStartRequest] = None) -> dict:
        """Start DB recording and send STATE Run command."""
        recipe_id = data.recipe_id if data else None
        logger.info(f"Starting recording. Recipe ID: {recipe_id}")
        tcp_bridge.start_recording()
        # Send STATE "Run" command
        await tcp_bridge.send_state_command("Run")
        return {"status": "started", "is_recording": True, "recipe_id": recipe_id}

    @post(path="/recording/pause")
    async def pause_recording(self) -> dict:
        """Pause DB recording and send STATE Pause command."""
        tcp_bridge.stop_recording()
        # Send STATE "Pause" command
        await tcp_bridge.send_state_command("Pause")
        return {"status": "paused", "is_recording": False}

    @post(path="/recording/stop")
    async def stop_recording(self) -> dict:
        """Stop DB recording and send STATE Stop command."""
        tcp_bridge.stop_recording()
        # Send STATE "Stop" command
        await tcp_bridge.send_state_command("Stop")
        return {"status": "stopped", "is_recording": False}

    @get(path="/recording/status")
    async def get_recording_status(self) -> dict:
        """Get current recording status."""
        return {"is_recording": tcp_bridge.get_recording_status()}

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

