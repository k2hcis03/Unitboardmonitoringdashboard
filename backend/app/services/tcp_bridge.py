import asyncio
import json
import logging
import requests
import configparser
import os
from datetime import datetime
from typing import Optional, Dict, List, Union
from pydantic import ValidationError

from app.models.protocol import SensorPacket, AckPacket, AckPacketInitialize, CommandPacket, CommandPacketGpio, CommandPacketMotor, CommandPacketFirmware, CommandPacketGetVersion, CommandPacketRef, RecipeDataItem, CommandPacketState, StateDataItem, PingPacket
from app.services.websocket_service import ws_manager
from app.services.db_service import db_service

logger = logging.getLogger(__name__)
idx = 0

# 프론트엔드 config.ts의 UNIT_TO_TANK_ID와 동일한 매핑
# 유닛보드 index(0~31) → 라즈베리파이 TANK_ID
UNIT_TO_TANK_ID: List[int] = [
    601,  # 유닛보드 1 (index 0)
    101,  # 유닛보드 2 (index 1)
    102,  # 유닛보드 3
    103,  # 유닛보드 4
    104, 105, 106, 107, 108, 109, 110, 201, 202, 203, 301, 501,
    502, 503, 118, 119, 120, 121, 122, 123, 124, 125, 126, 127, 128, 129, 130, 131  # 유닛보드 5~32
]

class TCPBridgeService:
    def __init__(self):
        self._receiver_server = None
        self._sender_server = None
        self._sender_writer: Optional[asyncio.StreamWriter] = None
        self._sender_writer_lock = asyncio.Lock()
        
        self._rx_connected = False
        self._tx_connected = False

        # 현재 활성 수신 연결 추적 (재연결 시 이전 핸들러가 상태를 덮어쓰는 것을 방지)
        self._receiver_writer: Optional[asyncio.StreamWriter] = None
        
        # Recording status
        self.is_recording = False
        
        # Command index counter
        self._command_idx = 0

        # PING IDX 카운터 (0~99,999 순환)
        self._ping_idx: int = 0
        
        # 현재 선택된 유닛보드 ID (프론트엔드 매핑된 TANK_ID, 기본값: 601 = 유닛보드 1)
        self._selected_unit_id: int = 601
        
        # 각 TANK_ID별 상태 저장 (UNIT_TO_TANK_ID 매핑 기반)
        # 초기 상태는 모두 "None"
        self._tank_states: Dict[int, str] = {tank_id: "None" for tank_id in UNIT_TO_TANK_ID}
        
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
                    unit_id=str(unit_id),  # 프론트엔드에서 이미 매핑된 TANK_ID 값을 문자열로 전송
                    tank_id=str(unit_id),  # 프론트엔드에서 이미 매핑된 TANK_ID 값을 문자열로 전송
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
        is_connected = self._rx_connected or self._tx_connected
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
        self._receiver_writer = writer
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

                # 라즈베리파이는 메시지 구분자(\n) 없이 JSON 객체를 연속 전송하며,
                # 큰 SENSOR 패킷(>4096B)은 여러 read에 걸쳐 쪼개져 온다.
                # _extract_json_objects가 버퍼 앞에서부터 완전한 JSON 객체를
                # 가능한 만큼 떼어내고, 마지막 미완성 객체는 buffer에 남긴다.
                objects, buffer = self._extract_json_objects(buffer)
                for obj_str in objects:
                    await self.process_message(obj_str)

                # 안전장치: 스트림 정렬 오류로 버퍼가 무한정 쌓이며 아무 객체도
                # 떼지 못하는 '영구 침묵' 상태 방지. SENSOR 패킷은 ~5KB이므로
                # 64KB를 넘으면 비정상으로 보고 버퍼를 리셋(resync)한다.
                if len(buffer) > 65536:
                    logger.warning(
                        f"Receiver buffer overflow ({len(buffer)} bytes) without "
                        f"complete JSON — resyncing (data discarded)"
                    )
                    buffer = b""

        except Exception as e:
            logger.error(f"Receiver connection error: {e}")
        finally:
            logger.info(f"Receiver (7000) disconnected {addr}")
            # 이 연결이 현재 활성 연결인 경우에만 상태를 변경 (재연결 시 경쟁 조건 방지)
            if self._receiver_writer == writer:
                self._receiver_writer = None
                self._rx_connected = False
            await self._broadcast_connection_status()
            writer.close()
            await writer.wait_closed()

    def _extract_json_objects(self, buffer: bytes):
        """버퍼에서 완전한 JSON 객체 문자열들을 추출하고, 처리하지 못한
        나머지 바이트를 반환한다.

        구분자(\\n)가 있든 없든, 객체가 연속으로 붙어 오든(`}{`), 하나가 여러
        read에 걸쳐 쪼개져 오든 모두 처리한다. json.JSONDecoder.raw_decode로
        버퍼 앞에서부터 완전한 객체를 하나씩 떼어내고, 마지막 미완성 객체는
        다음 read에서 이어붙이도록 그대로 남긴다.

        Returns:
            (objects, remaining): 완전한 JSON 객체 문자열 리스트와 남은 바이트.
        """
        try:
            text = buffer.decode('utf-8')
        except UnicodeDecodeError:
            # 멀티바이트 문자 경계에서 잘림 — 더 읽어서 보완 (ASCII 페이로드에선 거의 없음)
            return [], buffer

        objects = []
        decoder = json.JSONDecoder()
        pos = 0
        n = len(text)
        while pos < n:
            # 객체 사이의 공백/개행 건너뛰기 (raw_decode는 선행 공백을 처리하지 않음)
            while pos < n and text[pos] in ' \t\r\n':
                pos += 1
            if pos >= n:
                break
            try:
                _obj, end = decoder.raw_decode(text, pos)
            except json.JSONDecodeError:
                # pos부터는 아직 완전한 객체가 아님 — 다음 read 대기
                break
            objects.append(text[pos:end])
            pos = end

        return objects, text[pos:].encode('utf-8')

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
                logger.warning(f"Unknown CMD received: {cmd} | keys: {list(data.keys())} | raw: {json_str[:300]}")

        except json.JSONDecodeError:
            logger.error(f"Invalid JSON received (len={len(json_str)}): {json_str[:200]}...")
        except ValidationError as e:
            logger.error(f"Validation Error for CMD={data.get('CMD') if 'data' in dir() else '?'}: {e}")
        except Exception as e:
            logger.error(f"Unexpected error parsing message: {e} | raw: {json_str[:200]}")

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
                # 저장 시각은 라즈베리파이가 보낸 패킷의 DATE/TIME이 아니라
                # 백엔드(PC)의 현재 시각을 사용한다. (Pi 시계 오차와 무관하게 정확한 시간 기록)
                created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                
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

        ping_task = asyncio.create_task(self._ping_loop())

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
            ping_task.cancel()
            try:
                await ping_task
            except asyncio.CancelledError:
                pass
            logger.info("Sender connection lost")
            # 이 연결이 현재 활성 연결인 경우에만 상태를 변경 (재연결 시 경쟁 조건 방지)
            async with self._sender_writer_lock:
                if self._sender_writer == writer:
                    self._sender_writer = None
                    self._tx_connected = False
            await self._broadcast_connection_status()
            writer.close()
            await writer.wait_closed()

    async def _ping_loop(self):
        """포트 7001 연결 동안 1초마다 PING 패킷 전송. IDX는 0~99,999 순환."""
        logger.info("PING 루프 시작 (1초 간격)")
        while True:
            packet = PingPacket.model_validate({"CMD": "PING", "IDX": str(self._ping_idx), "NOTE": "OK"})
            sent = await self.send_command(packet)
            if not sent:
                logger.warning("PING 전송 실패 — 루프 종료")
                break
            self._ping_idx = (self._ping_idx + 1) % 100000
            await asyncio.sleep(1)

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
            unit_id=str(unit_id),  # 프론트엔드에서 이미 매핑된 TANK_ID 값을 문자열로 전송
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
        # 수신한 레시피 데이터 요약 로그 (전송 시작 시점)
        data_count = len(recipe_data.get("DATA", []))
        logger.info(
            f"[send_recipe] 시작: IDX={recipe_data.get('IDX')}, "
            f"TANK_ID={recipe_data.get('TANK_ID')}, "
            f"selected_unit_id={self._selected_unit_id}, "
            f"STAGE={recipe_data.get('STAGE')}, STEP={recipe_data.get('STEP')}, "
            f"DATA 항목 수={data_count}"
        )

        try:
            # 1단계: 레시피 전송 전 Initial 상태 전송
            initial_ok = await self.send_state_command("Initial")
            logger.info(f"[send_recipe] 1단계 Initial 상태 전송 결과: {initial_ok}")
            if not initial_ok:
                logger.warning("[send_recipe] Initial 상태 전송 실패 (연결 문제 가능성) - 레시피 전송 계속 진행")

            # 2단계: DATA 배열을 RecipeDataItem 객체로 파싱
            data_items = []
            for i, item_dict in enumerate(recipe_data.get("DATA", [])):
                try:
                    data_items.append(RecipeDataItem(**item_dict))
                except Exception as item_err:
                    # 어떤 항목/필드에서 파싱이 실패했는지 정확히 남김
                    logger.error(
                        f"[send_recipe] 2단계 DATA[{i}] 파싱 실패: {item_err} / 원본 항목={item_dict}"
                    )
                    raise
            logger.info(f"[send_recipe] 2단계 DATA 파싱 완료: {len(data_items)}개")

            # 3단계: 레시피 데이터로 CommandPacketRef 생성
            packet = CommandPacketRef(
                cmd="REF",
                idx=recipe_data.get("IDX", str(self._command_idx)),
                # tank_id= recipe_data.get("TANK_ID", "100"),
                # 선택된 유닛보드 ID가 이미 매핑된 TANK_ID이므로 그대로 사용
                # UNIT_ID/TANK_ID는 다른 명령어와 동일하게 매핑된 TANK_ID 값을 사용
                tank_id= str(self._selected_unit_id),
                unit_id= str(self._selected_unit_id),
                stage=recipe_data.get("STAGE", "0"),
                step=recipe_data.get("STEP", "3600"),
                data=data_items,
                send=False
            )
            logger.info(f"[send_recipe] 3단계 REF 패킷 생성 완료: idx={packet.idx}, tank_id={packet.tank_id}")
            self._command_idx += 1

            # 4단계: REF 패킷 전송
            result = await self.send_command(packet)
            logger.info(f"[send_recipe] 4단계 REF 패킷 전송 결과: {result}")

            return result
        except Exception as e:
            # exc_info=True 로 전체 트레이스백을 남겨 원인 파악을 돕는다
            logger.error(f"[send_recipe] 레시피 패킷 처리 실패: {e}", exc_info=True)
            return False

    async def send_state_command(self, status: str, stage: int = 100, unit_id: Optional[int] = None) -> bool:
        """
        Send STATE command to the connected Pi.
        status: "Run", "Pause", "Stop", "Initial", or "None"
        Creates 32 state items using UNIT_TO_TANK_ID mapping.
        Only updates the selected unit's status, preserving other units' existing states.
        
        Args:
            status: 상태 문자열
            stage: 공정 단계 (기본값: 100)
            unit_id: 특정 유닛의 TANK_ID (None이면 현재 선택된 유닛 사용)
        """
        try:
            self._command_idx += 1
            selected_tank_id = unit_id if unit_id is not None else self._selected_unit_id
            
            # 선택된 유닛의 상태만 업데이트
            self._tank_states[selected_tank_id] = status
            logger.info(f"Updated TANK_ID={selected_tank_id} status to '{status}'")
            
            # UNIT_TO_TANK_ID 매핑 기반으로 32개의 StateDataItem 생성
            # 각 유닛은 저장된 상태를 사용
            state_data_list = []
            for tank_id in UNIT_TO_TANK_ID:
                item_status = self._tank_states.get(tank_id, "None")
                
                state_data = StateDataItem(
                    # UNIT_ID/TANK_ID는 다른 명령어와 동일하게 매핑된 TANK_ID 값을 사용
                    UNIT_ID=str(tank_id),
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

    async def send_command(self, packet: Union[CommandPacket, CommandPacketGpio, CommandPacketMotor, CommandPacketFirmware, CommandPacketRef, PingPacket]):
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
                if packet.cmd == "PING":
                    logger.debug(f"Sent command: {packet.cmd}")
                else:
                    logger.info(f"Sent command: {packet.cmd}")
                return True
            except Exception as e:
                logger.error(f"Failed to send command (cmd={getattr(packet, 'cmd', '?')}): {e}", exc_info=True)
                self._sender_writer = None # Invalidate
                return False

    async def send_raw_json(self, json_data: dict) -> bool:
        """
        Send raw JSON dict directly to the connected Pi without Pydantic validation.
        """
        async with self._sender_writer_lock:
            if self._sender_writer is None:
                logger.warning("Cannot send raw JSON: No Pi connected on port 7001")
                return False
            
            try:
                data_str = json.dumps(json_data, ensure_ascii=False)
                self._sender_writer.write(data_str.encode('utf-8') + b'\n')
                await self._sender_writer.drain()
                logger.info(f"Sent raw JSON: {data_str[:200]}")
                return True
            except Exception as e:
                logger.error(f"Failed to send raw JSON: {e}")
                self._sender_writer = None
                return False

# Global instance
tcp_bridge = TCPBridgeService()

