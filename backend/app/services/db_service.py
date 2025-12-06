import aiosqlite
import asyncio
import logging
import os
import configparser
import pandas as pd
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional

from app.config import settings

logger = logging.getLogger(__name__)

class DBService:
    def __init__(self, db_path: str = settings.db_path):
        self.db_path = db_path
        self._load_sys_config()

    def _load_sys_config(self):
        """Load configuration from sys.ini to override defaults if present."""
        try:
            config = configparser.ConfigParser()
            ini_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'ini', 'sys.ini')
            if os.path.exists(ini_path):
                config.read(ini_path)
                if 'DATABASE' in config:
                    db_conf = config['DATABASE']
                    self.max_size_mb = db_conf.getint('MAX_DB_SIZE_MB', fallback=settings.max_db_size_mb)
                    self.retention_days = db_conf.getint('MAX_RETENTION_DAYS', fallback=settings.retention_days)
                    logger.info(f"Loaded DB config from sys.ini: Size={self.max_size_mb}MB, Retention={self.retention_days}days")
                else:
                    self.max_size_mb = settings.max_db_size_mb
                    self.retention_days = settings.retention_days
            else:
                self.max_size_mb = settings.max_db_size_mb
                self.retention_days = settings.retention_days
        except Exception as e:
            logger.error(f"Failed to load sys.ini config: {e}")
            self.max_size_mb = settings.max_db_size_mb
            self.retention_days = settings.retention_days

    async def init_db(self):
        """Initialize the database with required tables and indexes."""
        logger.info(f"Initializing database at {self.db_path}")
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("PRAGMA foreign_keys = ON;")
            
            # Packets table
            await db.execute("""
                CREATE TABLE IF NOT EXISTS packets (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    order_num INTEGER,
                    created_at DATETIME
                )
            """)
            await db.execute("CREATE INDEX IF NOT EXISTS idx_packets_created_at ON packets(created_at)")

            # Readings table
            await db.execute("""
                CREATE TABLE IF NOT EXISTS readings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    packet_id INTEGER,
                    tank_id TEXT,
                    sensor_id INTEGER,
                    value REAL,
                    FOREIGN KEY(packet_id) REFERENCES packets(id) ON DELETE CASCADE
                )
            """)
            await db.execute("CREATE INDEX IF NOT EXISTS idx_readings_tank_sensor ON readings(tank_id, sensor_id)")

            # States table
            await db.execute("""
                CREATE TABLE IF NOT EXISTS states (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    packet_id INTEGER,
                    tank_id TEXT,
                    stage INTEGER,
                    status TEXT,
                    FOREIGN KEY(packet_id) REFERENCES packets(id) ON DELETE CASCADE
                )
            """)
            
            await db.commit()

    async def save_packet(self, order_num: int, created_at: str, readings: List[Dict], states: List[Dict]):
        """Save a complete packet with its readings and states transactionally."""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute("PRAGMA foreign_keys = ON;")
                async with db.execute("BEGIN"):
                    # Insert packet
                    cursor = await db.execute(
                        "INSERT INTO packets (order_num, created_at) VALUES (?, ?)",
                        (order_num, created_at)
                    )
                    packet_id = cursor.lastrowid

                    # Insert readings
                    if readings:
                        readings_data = [
                            (packet_id, str(r['TANK_ID']), r['SENSOR_ID'], float(r['VALUE']))
                            for r in readings
                        ]
                        await db.executemany(
                            "INSERT INTO readings (packet_id, tank_id, sensor_id, value) VALUES (?, ?, ?, ?)",
                            readings_data
                        )

                    # Insert states
                    if states:
                        states_data = [
                            (packet_id, str(s['TANK_ID']), s['STAGE'], s['STATUS'])
                            for s in states
                        ]
                        await db.executemany(
                            "INSERT INTO states (packet_id, tank_id, stage, status) VALUES (?, ?, ?, ?)",
                            states_data
                        )
                    
                    await db.commit()
            return True
        except Exception as e:
            logger.error(f"Failed to save packet: {e}")
            return False

    async def get_history(self, start: str, end: str, tank_id: Optional[str] = None, sensor_ids: Optional[List[int]] = None) -> List[Dict]:
        """Query history data for charts."""
        query = """
            SELECT p.created_at as time, r.value, r.sensor_id
            FROM readings r
            JOIN packets p ON r.packet_id = p.id
            WHERE p.created_at BETWEEN ? AND ?
        """
        params = [start, end]

        if tank_id:
            query += " AND r.tank_id = ?"
            params.append(str(tank_id))
        
        if sensor_ids:
            placeholders = ','.join(['?'] * len(sensor_ids))
            query += f" AND r.sensor_id IN ({placeholders})"
            params.extend(sensor_ids)
            
        query += " ORDER BY p.created_at ASC"

        try:
            async with aiosqlite.connect(self.db_path) as db:
                db.row_factory = aiosqlite.Row
                async with db.execute(query, params) as cursor:
                    rows = await cursor.fetchall()
                    return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"Failed to query history: {e}")
            return []

    async def get_export_data(self, start: str, end: str) -> List[Dict]:
        """Query detailed data for CSV export."""
        query = """
            SELECT 
                p.created_at as Timestamp, 
                r.tank_id as Tank_ID, 
                r.sensor_id as Sensor_ID, 
                r.value as Value,
                s.stage as Stage,
                s.status as Status
            FROM packets p
            JOIN readings r ON p.id = r.packet_id
            LEFT JOIN states s ON p.id = s.packet_id AND r.tank_id = s.tank_id
            WHERE p.created_at BETWEEN ? AND ?
            ORDER BY p.created_at ASC, r.tank_id ASC, r.sensor_id ASC
        """
        params = [start, end]

        try:
            async with aiosqlite.connect(self.db_path) as db:
                db.row_factory = aiosqlite.Row
                async with db.execute(query, params) as cursor:
                    rows = await cursor.fetchall()
                    return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"Failed to query export data: {e}")
            return []

    async def cleanup_old_data(self):
        """Delete data older than retention_days or if DB size exceeds limit."""
        # Refresh config in case sys.ini changed
        self._load_sys_config()
        
        # 1. Date-based cleanup
        cutoff_date = (datetime.now() - timedelta(days=self.retention_days)).strftime("%Y-%m-%d %H:%M:%S")
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute("PRAGMA foreign_keys = ON;")
                
                # Delete by date
                await db.execute("DELETE FROM packets WHERE created_at < ?", (cutoff_date,))
                await db.commit()
                
                # 2. Size-based cleanup
                # Check current DB size
                if os.path.exists(self.db_path):
                    current_size = os.path.getsize(self.db_path)
                    max_size_bytes = self.max_size_mb * 1024 * 1024
                    
                    if current_size > max_size_bytes:
                        logger.info(f"DB size ({current_size/1024/1024:.2f}MB) exceeds limit ({self.max_size_mb}MB). Cleaning up...")
                        
                        # Loop until size is within limit (with buffer)
                        # To avoid infinite loop if VACUUM doesn't help enough, add max iterations
                        max_iterations = 100 
                        iteration = 0
                        
                        while current_size > max_size_bytes and iteration < max_iterations:
                            # Delete oldest 100 packets (adjustable)
                            # Using subquery to identify oldest packets
                            await db.execute("""
                                DELETE FROM packets 
                                WHERE id IN (
                                    SELECT id FROM packets ORDER BY created_at ASC LIMIT 100
                                )
                            """)
                            await db.commit()
                            
                            # VACUUM to reclaim space and update file size
                            await db.execute("VACUUM")
                            
                            current_size = os.path.getsize(self.db_path)
                            iteration += 1
                            
                        logger.info(f"Cleanup finished. Final size: {current_size/1024/1024:.2f}MB")
                    else:
                        # Just VACUUM if we deleted by date, to keep it tidy
                        await db.execute("VACUUM")
                        
                logger.info(f"Cleaned up data older than {cutoff_date}")
        except Exception as e:
            logger.error(f"Failed to cleanup database: {e}")

db_service = DBService()

