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

# 프론트엔드 config.ts의 UNIT_TO_TANK_ID와 동일한 매핑
# 유닛보드 index(0~31) → 라즈베리파이 TANK_ID
UNIT_TO_TANK_ID: List[int] = [
    601,  # 유닛보드 1 (index 0)
    101,  # 유닛보드 2 (index 1)
    102,  # 유닛보드 3
    103,  # 유닛보드 4
    104, 105, 106, 107, 108, 109, 110, 111, 112, 113, 114, 115,
    116, 117, 118, 119, 120, 121, 122, 123, 124, 125, 126, 127, 128, 129, 130, 131  # 유닛보드 5~32
]

# 재접속 대기 시간 (초)
RECONNECT_DELAY = 5


class TCPBridgeService:
    def __init__(self):
        # 클라이언트 모드: 단일 연결로 송수신 모두 처리
        self._sender_writer: Optional[asyncio.StreamWriter] = None
        self._sender_writer_lock = asyncio.Lock()

        self._rx_connected = False
        self._tx_connected = False

        # Recording status
        self.is_recording = False

        # Command index counter
        self._command_idx = 0

        # 현재 선택된 유닛보드 ID (프론트엔드 매핑된 TANK_ID, 기본값: 601 = 유닛보드 1)
        self._selected_unit_id: int = 601

        # 각 TANK_ID별 상태 저장 (UNIT_TO_TANK_ID 매핑 기반)
        self._tank_states: Dict[int, str] = {tank_id: "None" for tank_id in UNIT_TO_TANK_ID}

        # 라즈베리파이 접속 정보 (sys.ini에서 로드)
        self._rpi_host: str = "172.30.1.100"
        self._rpi_port: int = 7000

        # Tasks
        self._connect_task: Optional[asyncio.Task] = None
        self._cleanup_task: Optional[asyncio.Task] = None
        self._running: bool = False

    # -------------------------------------------------------------------------
    # 설정 로드
    # -------------------------------------------------------------------------
    def _load_config(self):
        """sys.ini에서 라즈베리파이 접속 정보 로드"""
        config = configparser.ConfigParser()
        ini_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'ini', 'sys.ini'
        )
        try:
            config.read(ini_path)
            self._rpi_host = config.get('NETWORK', 'HOST_IP', fallback='172.30.1.100')
            self._rpi_port = config.getint('NETWORK', 'TCP_PORT', fallback=7000)
            logger.info(f"RPi 접속 설정: {self._rpi_host}:{self._rpi_port}")
        except Exception as e:
            logger.error(f"sys.ini 로드 실패, 기본값 사용: {e}")

    # -------------------------------------------------------------------------
    # 유닛 선택 / 연결 상태
    # -------------------------------------------------------------------------
    def set_selected_unit_id(self, unit_id: int):
        """선택된 유닛보드 변경 시 호출"""
        logger.info(f"Selected Unit ID changed to: {unit_id}")
        self._selected_unit_id = unit_id
        global idx
        idx = idx + 1

        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                asyncio.create_task(self.send_command(CommandPacketGetVersion(
                    cmd='GET_VERSION',
                    unit_id=str(unit_id),
                    idx=str(idx),
                    send=True,
                )))
            logger.info("Command sent successfully")
        except Exception as e:
            logger.error(f"Failed to send command: {e}")

    async def _broadcast_connection_status(self):
        """WebSocket 클라이언트 전체에 연결 상태 브로드캐스트"""
        status = self.get_connection_status()
        await ws_manager.broadcast(status)

    def get_connection_status(self) -> dict:
        """현재 연결 상태 반환 (단일 연결이므로 rx=tx)"""
        is_connected = self._rx_connected and self._tx_connected
        return {
            "type": "SYSTEM_CONNECTION_STATUS",
            "data": {
                "connected": is_connected,
                "rx": self._rx_connected,
                "tx": self._tx_connected
            }
        }

    # -------------------------------------------------------------------------
    # 시작 / 종료
    # -------------------------------------------------------------------------
    async def start(self):
        """TCP 클라이언트 시작: 라즈베리파이에 접속하고 자동 재접속 루프 실행"""
        logger.info("Starting TCP Bridge Service (Client Mode)...")

        # DB 초기화
        await db_service.init_db()
        await db_service.cleanup_old_data()

        # 주기적 정리 태스크 시작
        self._cleanup_task = asyncio.create_task(self._periodic_cleanup_task())

        # 접속 설정 로드
        self._load_config()

        # 접속 루프 시작
        self._running = True
        self._connect_task = asyncio.create_task(self._connection_loop())
        logger.info(f"TCP 클라이언트 시작: {self._rpi_host}:{self._rpi_port} 접속 시도 중...")

    async def stop(self):
        """TCP 클라이언트 종료"""
        logger.info("Stopping TCP Bridge Service...")
        self._running = False

        if self._connect_task:
            self._connect_task.cancel()
            try:
                await self._connect_task
            except asyncio.CancelledError:
                pass
            self._connect_task = None

        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
            self._cleanup_task = None

        async with self._sender_writer_lock:
            if self._sender_writer:
                try:
                    self._sender_writer.close()
                    await self._sender_writer.wait_closed()
                except Exception:
                    pass
                self._sender_writer = None

    def start_recording(self):
        """센서 데이터 DB 기록 시작"""
        logger.info("Starting DB recording...")
        self.is_recording = True

    def stop_recording(self):
        """센서 데이터 DB 기록 중지"""
        logger.info("Stopping DB recording...")
        self.is_recording = False

    def get_recording_status(self) -> bool:
        return self.is_recording

    # -------------------------------------------------------------------------
    # 연결 루프 (클라이언트 핵심)
    # -------------------------------------------------------------------------
    async def _connection_loop(self):
        """라즈베리파이 서버에 접속하고, 끊기면 자동으로 재접속"""
        while self._running:
            try:
                logger.info(f"라즈베리파이 접속 시도: {self._rpi_host}:{self._rpi_port}")
                reader, writer = await asyncio.open_connection(self._rpi_host, self._rpi_port)

                # 연결 성공 → 상태 업데이트
                async with self._sender_writer_lock:
                    self._sender_writer = writer
                self._rx_connected = True
                self._tx_connected = True
                await self._broadcast_connection_status()
                logger.info(f"라즈베리파이 연결 성공: {self._rpi_host}:{self._rpi_port}")

                # 수신 루프 (연결이 끊길 때까지 블록)
                await self._receive_loop(reader, writer)

            except (ConnectionRefusedError, OSError) as e:
                logger.warning(f"라즈베리파이 접속 실패: {e}")
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"연결 오류: {e}")
            finally:
                # 연결 해제 처리
                self._rx_connected = False
                self._tx_connected = False
                async with self._sender_writer_lock:
                    self._sender_writer = None
                await self._broadcast_connection_status()

            if self._running:
                logger.info(f"{RECONNECT_DELAY}초 후 재접속 시도...")
                await asyncio.sleep(RECONNECT_DELAY)

    async def _receive_loop(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        """연결된 소켓에서 데이터를 수신하고 메시지를 처리"""
        buffer = b""
        try:
            while True:
                data = await reader.read(4096)
                if not data:
                    logger.info("라즈베리파이 연결 종료 (EOF)")
                    break

                buffer += data

                try:
                    message_str = buffer.decode('utf-8')
                    messages = message_str.strip().split('\n')
                    for msg in messages:
                        if not msg.strip():
                            continue
                        await self.process_message(msg)
                    buffer = b""
                except UnicodeDecodeError:
                    pass  # 더 많은 데이터 대기
                except Exception as e:
                    logger.error(f"스트림 처리 오류: {e}")
                    buffer = b""

        except asyncio.CancelledError:
            raise
        except Exception as e:
            logger.error(f"수신 루프 오류: {e}")
        finally:
            try:
                writer.close()
                await writer.wait_closed()
            except Exception:
                pass

    # -------------------------------------------------------------------------
    # 주기적 DB 정리
    # -------------------------------------------------------------------------
    async def _periodic_cleanup_task(self):
        """1시간마다 DB 오래된 데이터 정리"""
        logger.info("Starting periodic DB cleanup task")
        while True:
            try:
                await asyncio.sleep(3600)
                logger.info("Running periodic cleanup...")
                await db_service.cleanup_old_data()
            except asyncio.CancelledError:
                logger.info("Periodic cleanup task cancelled")
                break
            except Exception as e:
                logger.error(f"Error in periodic cleanup: {e}")
                await asyncio.sleep(60)

    # -------------------------------------------------------------------------
    # 수신 메시지 처리 (변경 없음)
    # -------------------------------------------------------------------------
    async def process_message(self, json_str: str):
        """수신된 JSON 메시지를 파싱하여 적절한 핸들러로 라우팅"""
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
        """SENSOR 패킷 처리: WebSocket 브로드캐스트 및 DB 저장"""
        try:
            update_msg = {
                "type": "SENSOR_UPDATE",
                "data": packet.model_dump(by_alias=True)
            }
            await ws_manager.broadcast(update_msg)
            logger.debug(f"Broadcasted sensor update for Order={packet.order}")

            if self.is_recording:
                created_at = f"{packet.date} {packet.time}"
                readings = [r.model_dump(by_alias=True) for r in packet.values]
                states = [s.model_dump(by_alias=True) for s in packet.state]
                asyncio.create_task(db_service.save_packet(
                    order_num=packet.order,
                    created_at=created_at,
                    readings=readings,
                    states=states
                ))

        except Exception as e:
            logger.error(f"Failed to process sensor packet: {e}")

    async def handle_ack_packet(self, packet: AckPacket):
        """ACK 패킷 처리: WebSocket 브로드캐스트"""
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
        """ACK_INITIALIZE 패킷 처리: WebSocket 브로드캐스트"""
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
    # 명령 전송 (변경 없음 - _sender_writer 재사용)
    # -------------------------------------------------------------------------
    async def send_command(self, packet: Union[CommandPacket, CommandPacketGpio, CommandPacketMotor, CommandPacketFirmware, CommandPacketRef]):
        """Pydantic 패킷을 JSON으로 직렬화하여 라즈베리파이에 전송"""
        async with self._sender_writer_lock:
            if self._sender_writer is None:
                logger.warning("Cannot send command: 라즈베리파이에 연결되어 있지 않습니다")
                return False

            try:
                data_str = packet.model_dump_json(by_alias=True)
                self._sender_writer.write(data_str.encode('utf-8') + b'\n')
                await self._sender_writer.drain()
                logger.info(f"Sent command: {packet.cmd}")
                return True
            except Exception as e:
                logger.error(f"Failed to send command: {e}")
                self._sender_writer = None
                return False

    async def send_raw_json(self, json_data: dict) -> bool:
        """Pydantic 검증 없이 raw JSON을 라즈베리파이에 직접 전송"""
        async with self._sender_writer_lock:
            if self._sender_writer is None:
                logger.warning("Cannot send raw JSON: 라즈베리파이에 연결되어 있지 않습니다")
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

    # -------------------------------------------------------------------------
    # 고수준 명령 (변경 없음)
    # -------------------------------------------------------------------------
    async def send_firmware_update(self, unit_id: int, file_path: str) -> bool:
        """펌웨어 업데이트 명령 전송"""
        config = configparser.ConfigParser()
        ini_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'ini', 'sys.ini'
        )

        try:
            config.read(ini_path)
            url = config.get('FIRMWARE_UPDATE', 'URL', fallback="http://172.30.1.100:9001/upload")

            if os.name == 'nt':
                default_dir = "C:/Projects/M-FACTORY/Software/control_server/Unitboardmonitoringdashboard/firmware/"
                firmware_dir = config.get('FIRMWARE_UPDATE', 'DIR_WINDOWS', fallback=default_dir)
            else:
                default_dir = "/home/pi/Projects/cosmo-m/firmware/"
                firmware_dir = config.get('FIRMWARE_UPDATE', 'DIR_LINUX', fallback=default_dir)

        except Exception as e:
            logger.error(f"Failed to load config from {ini_path}: {e}")
            url = "http://172.30.1.100:9001/upload"
            firmware_dir = "C:/Projects/M-FACTORY/Software/control_server/Unitboardmonitoringdashboard/firmware/" \
                if os.name == 'nt' else "/home/pi/Projects/cosmo-m/firmware/"

        try:
            full_path = os.path.join(firmware_dir, file_path)
            with open(full_path, "rb") as f:
                files = {"file": (file_path, f)}
                response = requests.post(url, files=files)
                response.raise_for_status()
                logger.info(f"File uploaded successfully: {response.text}")
        except FileNotFoundError:
            logger.error(f"Firmware file not found at: {full_path}")
            return False
        except Exception as e:
            logger.error(f"Failed to upload firmware file: {e}")
            return False

        self._command_idx += 1
        packet = CommandPacketFirmware(
            cmd="FIRMWARE_UPDATE",
            unit_id=str(unit_id),
            idx=self._command_idx,
            file="/home/pi/Projects/cosmo-m/firmware/firmware.bin",
            send=False
        )
        logger.info("Command sent successfully")
        return await self.send_command(packet)

    async def send_recipe(self, recipe_data: dict) -> bool:
        """레시피(REF) 명령 전송"""
        try:
            await self.send_state_command("Initial")
            logger.info("Sent Initial state")

            data_items = []
            for item_dict in recipe_data.get("DATA", []):
                data_items.append(RecipeDataItem(**item_dict))

            packet = CommandPacketRef(
                cmd="REF",
                idx=recipe_data.get("IDX", str(self._command_idx)),
                tank_id=str(self._selected_unit_id),
                stage=recipe_data.get("STAGE", "0"),
                step=recipe_data.get("STEP", "3600"),
                data=data_items,
                send=False
            )
            self._command_idx += 1
            return await self.send_command(packet)
        except Exception as e:
            logger.error(f"Failed to create recipe packet: {e}")
            return False

    async def send_state_command(self, status: str, stage: int = 100, unit_id: Optional[int] = None) -> bool:
        """
        STATE 명령 전송: 선택된 유닛의 상태만 업데이트하고 나머지는 기존 상태 유지.
        status: "Run", "Pause", "Stop", "Initial", "None"
        """
        try:
            self._command_idx += 1
            selected_tank_id = unit_id if unit_id is not None else self._selected_unit_id

            self._tank_states[selected_tank_id] = status
            logger.info(f"Updated TANK_ID={selected_tank_id} status to '{status}'")

            state_data_list = []
            for tank_id in UNIT_TO_TANK_ID:
                item_status = self._tank_states.get(tank_id, "None")
                state_data_list.append(StateDataItem(
                    TANK_ID=str(tank_id),
                    STAGE=stage,
                    STATUS=item_status
                ))

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


# 전역 인스턴스
tcp_bridge = TCPBridgeService()
