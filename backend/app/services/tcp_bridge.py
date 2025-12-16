import asyncio
import json
import logging
import requests
import configparser
import os
from typing import Optional, Dict, List, Union
from pydantic import ValidationError

from app.models.protocol import SensorPacket, AckPacket, AckPacketInitialize, CommandPacket, CommandPacketGpio, CommandPacketMotor, CommandPacketFirmware, CommandPacketGetVersion, CommandPacketRef, RecipeDataItem, CommandPacketState, StateDataItem
from app.services.websocket_service import ws_manager
from app.services.db_service import db_service

logger = logging.getLogger(__name__)
idx = 0

class TCPBridgeService:
    def __init__(self):
        self._receiver_server = None
        self._sender_server = None
        self._sender_writer: Optional[asyncio.StreamWriter] = None
        self._sender_writer_lock = asyncio.Lock()
        
        self._rx_connected = False
        self._tx_connected = False
        
        # Recording status
        self.is_recording = False
        
        # Command index counter
        self._command_idx = 0
        
        # 현재 선택된 유닛보드 ID (0-31)
        self._selected_unit_id: int = 0
        
        # 각 TANK_ID별 상태 저장 (TANK_ID 100-131)
        # 초기 상태는 모두 "None"
        self._tank_states: Dict[int, str] = {tank_id: "None" for tank_id in range(100, 132)}
        
        # Tasks
        self._cleanup_task: Optional[asyncio.Task] = None

    def set_selected_unit_id(self, unit_id: int):
        """Set the currently selected unit ID to filter/focus data if needed."""
        logger.info(f"Selected Unit ID changed to: {unit_id}")
        self._selected_unit_id = unit_id
        # 임시로 idx 생성 (예: 현재 타임스탬프 또는 랜덤)
        global idx
        idx = idx + 1

        try:
            # Create a task for the async command
            loop = asyncio.get_event_loop()
            if loop.is_running():
                 asyncio.create_task(self.send_command(CommandPacketGetVersion(
                    cmd='GET_VERSION',
                    unit_id=unit_id+1,
                    idx=str(idx),
                    send=True,
                )))
            logger.info("Command sent successfully")
        except Exception as e:
            logger.error(f"Failed to send command: {e}")

    async def _broadcast_connection_status(self):
        """Broadcast current connection status to all WebSocket clients"""
        status = self.get_connection_status()
        await ws_manager.broadcast(status)

    def get_connection_status(self) -> dict:
        """Get the current connection status"""
        # Consider connected if both RX (7000) and TX (7001) are active
        # Or at least one is active? Requirement says "7000, 7001 connected"
        # We will return detailed status and a summary 'connected' flag.
        is_connected = self._rx_connected and self._tx_connected
        return {
            "type": "SYSTEM_CONNECTION_STATUS",
            "data": {
                "connected": is_connected,
                "rx": self._rx_connected,
                "tx": self._tx_connected
            }
        }

    async def _periodic_cleanup_task(self):
        """Run DB cleanup periodically (every 1 hour)."""
        logger.info("Starting periodic DB cleanup task")
        while True:
            try:
                # Initial delay to avoid startup contention or wait for 1 hour
                await asyncio.sleep(3600) 
                logger.info("Running periodic cleanup...")
                await db_service.cleanup_old_data()
            except asyncio.CancelledError:
                logger.info("Periodic cleanup task cancelled")
                break
            except Exception as e:
                logger.error(f"Error in periodic cleanup: {e}")
                # Wait a bit before retrying to avoid tight loop on error
                await asyncio.sleep(60)

    async def start(self):
        """Start both TCP servers (Receiver on 7000, Sender Connection Handler on 7001)"""
        logger.info("Starting TCP Bridge Service...")
        
        # Initialize Database
        await db_service.init_db()
        # Cleanup old data on startup
        await db_service.cleanup_old_data()
        
        # Start periodic cleanup task
        self._cleanup_task = asyncio.create_task(self._periodic_cleanup_task())
        
        # 1. Receiver Server (Port 7000) - Listens for incoming data
        self._receiver_server = await asyncio.start_server(
            self.handle_receiver_connection, '0.0.0.0', 7000
        )
        logger.info("Listening for incoming data on port 7000")

        # 2. Sender Server (Port 7001) - Listens for Pi connection to send commands TO
        self._sender_server = await asyncio.start_server(
            self.handle_sender_connection, '0.0.0.0', 7001
        )
        logger.info("Listening for command connection on port 7001")
        
        # We do NOT await serve_forever() here because it would block Litestar startup.
        # The servers are attached to the loop now.

    def start_recording(self):
        """Start recording sensor data to DB."""
        logger.info("Starting DB recording...")
        self.is_recording = True

    def stop_recording(self):
        """Stop recording sensor data to DB."""
        logger.info("Stopping DB recording...")
        self.is_recording = False

    def get_recording_status(self) -> bool:
        """Get current recording status."""
        return self.is_recording

    async def stop(self):
        """Stop TCP servers"""
        logger.info("Stopping TCP Bridge Service...")
        
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
            self._cleanup_task = None

        if self._receiver_server:
            self._receiver_server.close()
            await self._receiver_server.wait_closed()
        
        if self._sender_server:
            self._sender_server.close()
            await self._sender_server.wait_closed()
            
        async with self._sender_writer_lock:
            if self._sender_writer:
                self._sender_writer.close()
                await self._sender_writer.wait_closed()
                self._sender_writer = None

    # -------------------------------------------------------------------------
    # Port 7000 Logic: Receiving Data
    # -------------------------------------------------------------------------
    async def handle_receiver_connection(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        addr = writer.get_extra_info('peername')
        logger.info(f"Receiver (7000) connected by {addr}")
        self._rx_connected = True
        await self._broadcast_connection_status()

        try:
            buffer = b""
            while True:
                # Read chunk
                data = await reader.read(4096)
                if not data:
                    break
                
                buffer += data
                
                # Simple delimiter handling (assuming JSON objects are sent line by line or delimited)
                # In real stream, we might need length-prefix or looking for braces balance.
                # For this MVP, assuming the Pi sends distinct packets or closes connection, 
                # OR we try to decode continuously. 
                # Let's assume delimiter is newline for robustness, or just try to decode the buffer.
                
                # Try to decode buffer
                try:
                    message_str = buffer.decode('utf-8')
                    # This logic assumes one JSON per connection or newline delimited. 
                    # If stuck together: "}{" -> invalid. 
                    # For now, let's assume the buffer contains a complete JSON message 
                    # or split by newline if stream.
                    
                    messages = message_str.strip().split('\n')
                    for msg in messages:
                        if not msg.strip(): continue
                        await self.process_message(msg)
                    
                    # Reset buffer if successful (in a real stream, need to keep partial bytes)
                    buffer = b"" 
                    
                except UnicodeDecodeError:
                    pass # Wait for more data
                except Exception as e:
                    logger.error(f"Error processing stream: {e}")

        except Exception as e:
            logger.error(f"Receiver connection error: {e}")
        finally:
            logger.info(f"Receiver (7000) disconnected {addr}")
            self._rx_connected = False
            await self._broadcast_connection_status()
            writer.close()
            await writer.wait_closed()

    async def process_message(self, json_str: str):
        """Parse and route the incoming JSON message."""
        try:
            data = json.loads(json_str)
            cmd = data.get("CMD")

            if cmd == "SENSOR":
                packet = SensorPacket(**data)
                await self.handle_sensor_packet(packet)
            elif cmd == "ACK":
                packet = AckPacket(**data)
                await self.handle_ack_packet(packet)
            elif cmd == "ACK_INITIALIZE":
                packet = AckPacketInitialize(**data)
                await self.handle_ack_packet_initialize(packet)
            else:
                logger.warning(f"Unknown CMD received: {cmd}")

        except json.JSONDecodeError:
            logger.error(f"Invalid JSON received: {json_str[:50]}...")
        except ValidationError as e:
            logger.error(f"Validation Error: {e}")
        except Exception as e:
            logger.error(f"Unexpected error parsing message: {e}")

    async def handle_sensor_packet(self, packet: SensorPacket):
        # Broadcast SENSOR_UPDATE to all clients
        # Frontend will filter based on selected unit_id
        try:
            update_msg = {
                "type": "SENSOR_UPDATE",
                "data": packet.model_dump(by_alias=True)
            }
            await ws_manager.broadcast(update_msg)
            logger.debug(f"Broadcasted sensor update for Order={packet.order}")
            
            # Save to DB if recording
            if self.is_recording:
                # Construct timestamp YYYY-MM-DD HH:MM:SS
                created_at = f"{packet.date} {packet.time}"
                
                # Convert models to dicts for DB service
                readings = [r.model_dump(by_alias=True) for r in packet.values]
                states = [s.model_dump(by_alias=True) for s in packet.state]
                
                # Async save (fire and forget or await? await is safer for order but slower)
                # Requirement: "모든 저장은 비동기(Async)로 수행하여 메인 통신 루프를 차단하지 않아야 함."
                # aiosqlite is async, so awaiting it yields control. 
                # But to be super non-blocking to the *next* packet processing, we can use create_task.
                # However, create_task might flood if DB is slow. Await is usually fine with async DB.
                # Let's use create_task to strictly follow "Main loop blocking minimization".
                asyncio.create_task(db_service.save_packet(
                    order_num=packet.order,
                    created_at=created_at,
                    readings=readings,
                    states=states
                ))
                
        except Exception as e:
            logger.error(f"Failed to process sensor packet: {e}")

    async def handle_ack_packet(self, packet: AckPacket):
        # Broadcast ACK to all clients
        try:
            ack_msg = {
                "type": "ACK_RECEIVED",
                "data": packet.model_dump(by_alias=True)
            }
            await ws_manager.broadcast(ack_msg)
            logger.info(f"Broadcasted ACK: Idx={packet.idx}, Note={packet.note}")
        except Exception as e:
            logger.error(f"Failed to broadcast ACK: {e}")

    async def handle_ack_packet_initialize(self, packet: AckPacketInitialize):
        # Broadcast ACK_INITIALIZE to all clients
        try:
            ack_msg = {
                "type": "ACK_INITIALIZE_RECEIVED",
                "data": packet.model_dump(by_alias=True)
            }
            await ws_manager.broadcast(ack_msg)
            logger.info(f"Broadcasted ACK_INITIALIZE: Idx={packet.idx}, FW_Version={packet.fw_version}, Note={packet.note}")    
        except Exception as e:
            logger.error(f"Failed to broadcast ACK_INITIALIZE: {e}")
    # -------------------------------------------------------------------------
    # Port 7001 Logic: Sending Commands
    # -------------------------------------------------------------------------
    async def handle_sender_connection(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        """
        Accepts connection from Pi. 
        Stores the writer so we can push commands to it later.
        Only one active controller connection is expected usually.
        """
        addr = writer.get_extra_info('peername')
        logger.info(f"Sender (7001) connection established from {addr}")
        self._tx_connected = True
        await self._broadcast_connection_status()

        async with self._sender_writer_lock:
            if self._sender_writer is not None:
                logger.warning("Overwriting existing sender connection!")
                try:
                    self._sender_writer.close()
                except:
                    pass
            self._sender_writer = writer

        # Keep connection alive
        try:
            # We just listen for closure here, or maybe heartbeats from Pi?
            # If Pi sends anything on 7001, we ignore or log it.
            while True:
                data = await reader.read(1024)
                if not data:
                    break
        except Exception as e:
            logger.error(f"Sender connection loop error: {e}")
        finally:
            logger.info("Sender connection lost")
            self._tx_connected = False
            await self._broadcast_connection_status()
            async with self._sender_writer_lock:
                if self._sender_writer == writer:
                    self._sender_writer = None
            writer.close()
            await writer.wait_closed()

    async def send_firmware_update(self, unit_id: int, file_path: str) -> bool:
        """
        Send firmware update command with file path.
        """
        # Load configuration from sys.ini
        config = configparser.ConfigParser()
        ini_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'ini', 'sys.ini')
        
        try:
            config.read(ini_path)
            url = config.get('FIRMWARE_UPDATE', 'URL', fallback="http://172.30.1.100:9001/upload")
            
            # OS에 따른 펌웨어 디렉토리 자동 설정
            if os.name == 'nt':  # Windows
                default_dir = "C:/Projects/M-FACTORY/Software/control_server/Unitboardmonitoringdashboard/firmware/"
                firmware_dir = config.get('FIRMWARE_UPDATE', 'DIR_WINDOWS', fallback=default_dir)
            else:  # Linux (Raspberry Pi)
                default_dir = "/home/pi/Projects/cosmo-m/firmware/"
                firmware_dir = config.get('FIRMWARE_UPDATE', 'DIR_LINUX', fallback=default_dir)
                
        except Exception as e:
            logger.error(f"Failed to load config from {ini_path}: {e}")
            # Fallback values
            url = "http://172.30.1.100:9001/upload"
            if os.name == 'nt':
                firmware_dir = "C:/Projects/M-FACTORY/Software/control_server/Unitboardmonitoringdashboard/firmware/"
            else:
                firmware_dir = "/home/pi/Projects/cosmo-m/firmware/"

        try:
            # 파일이 존재하는지 확인하고 업로드 시도
            # file_path가 로컬 서버(백엔드가 실행중인 PC)의 경로라면 직접 읽을 수 있음
            full_path = os.path.join(firmware_dir, file_path)
            with open(full_path, "rb") as f:
                files = {"file": (file_path, f)}
                response = requests.post(url, files=files)
                response.raise_for_status() # Check for HTTP errors
                logger.info(f"File uploaded successfully: {response.text}")
        except FileNotFoundError:
             logger.error(f"Firmware file not found at: {full_path}")
             # 파일이 없더라도 명령은 보낼지, 아니면 중단할지 결정 필요.
             # 여기서는 로그만 남기고 일단 진행 (또는 리턴 False)
             return False
        except Exception as e:
            logger.error(f"Failed to upload firmware file: {e}")
            return False

        self._command_idx += 1
        packet = CommandPacketFirmware(
            cmd="FIRMWARE_UPDATE",
            unit_id=unit_id + 1,
            idx=self._command_idx,
            file="/home/pi/Projects/cosmo-m/firmware/firmware.bin", # 라즈베리파이 펌웨어 전체 경로 포함
            send=False
        )
        logger.info("Command sent successfully")
        return await self.send_command(packet)

    async def send_recipe(self, recipe_data: dict) -> bool:
        """
        Send recipe (REF) command to the connected Pi.
        recipe_data should be the JSON content from reference file.
        """
        try:
            # 레시피 전송 성공 후 Initial 상태 전송
            await self.send_state_command("Initial")
            logger.info("Sent Initial state")

            # Parse DATA array into RecipeDataItem objects
            data_items = []
            for item_dict in recipe_data.get("DATA", []):
                data_items.append(RecipeDataItem(**item_dict))
            
            # Create CommandPacketRef from recipe data
            packet = CommandPacketRef(
                cmd="REF",
                idx=recipe_data.get("IDX", str(self._command_idx)),
                # tank_id= recipe_data.get("TANK_ID", "100"),
                # 선택된 유닛보드 ID를 기반으로 TANK_ID 설정
                tank_id= str(self._selected_unit_id + 101),
                stage=recipe_data.get("STAGE", "0"),
                step=recipe_data.get("STEP", "3600"),
                data=data_items,
                send=False
            )
            self._command_idx += 1
            result = await self.send_command(packet)

            return result
        except Exception as e:
            logger.error(f"Failed to create recipe packet: {e}")
            return False

    async def send_state_command(self, status: str, stage: int = 100) -> bool:
        """
        Send STATE command to the connected Pi.
        status: "Run", "Pause", "Stop", "Initial", or "None"
        Creates 32 state items (TANK_ID 100-131).
        Only updates the selected unit's status, preserving other units' existing states.
        """
        try:
            self._command_idx += 1
            selected_tank_id = self._selected_unit_id + 101  # 101 이거 수정 하지 말것...0 -> 101, 1 -> 102, ... 왜냐하면 유닛보드 ID가 0부터 시작하기 때문에
            
            # 선택된 유닛의 상태만 업데이트
            self._tank_states[selected_tank_id] = status
            logger.info(f"Updated TANK_ID={selected_tank_id} status to '{status}'")
            
            # 32개의 StateDataItem 생성 (TANK_ID 100~131)
            # 각 유닛은 저장된 상태를 사용
            state_data_list = []
            for tank_id in range(100, 132):
                item_status = self._tank_states.get(tank_id, "None")
                
                state_data = StateDataItem(
                    TANK_ID=str(tank_id),
                    STAGE=stage,
                    STATUS=item_status
                )
                state_data_list.append(state_data)
            
            packet = CommandPacketState(
                cmd="STATE",
                idx=self._command_idx,
                data=state_data_list
            )
            
            logger.info(f"Sending STATE command: Selected TANK_ID={selected_tank_id}, STATUS={status}")
            return await self.send_command(packet)
        except Exception as e:
            logger.error(f"Failed to send state command: {e}")
            return False

    async def send_command(self, packet: Union[CommandPacket, CommandPacketGpio, CommandPacketMotor, CommandPacketFirmware, CommandPacketRef]):
        """
        Public method to send JSON command to the connected Pi.
        """
        async with self._sender_writer_lock:
            if self._sender_writer is None:
                logger.warning("Cannot send command: No Pi connected on port 7001")
                return False
            
            try:
                # Serialize
                data_str = packet.model_dump_json(by_alias=True)
                self._sender_writer.write(data_str.encode('utf-8') + b'\n')
                await self._sender_writer.drain()
                logger.info(f"Sent command: {packet.cmd}")
                return True
            except Exception as e:
                logger.error(f"Failed to send command: {e}")
                self._sender_writer = None # Invalidate
                return False

# Global instance
tcp_bridge = TCPBridgeService()

