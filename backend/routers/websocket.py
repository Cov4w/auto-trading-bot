"""
WebSocket Router
================
실시간 데이터 스트리밍 (로그, 가격, 상태 변경 등)
"""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from typing import Set
import logging
import asyncio
import json
from datetime import datetime
import traceback


router = APIRouter()
logger = logging.getLogger(__name__)


def safe_json_dumps(data: dict) -> str:
    """JSON 직렬화 안전하게 수행 (nan/inf 처리)"""
    def sanitize(obj):
        if isinstance(obj, float):
            if obj != obj or obj == float('inf') or obj == float('-inf'):  # nan or inf
                return 0.0
        return obj

    return json.dumps(data, default=str)


# 연결된 클라이언트 관리
class ConnectionManager:
    def __init__(self):
        self.active_connections: Set[WebSocket] = set()

    async def connect(self, websocket: WebSocket):
        """클라이언트 연결"""
        await websocket.accept()
        self.active_connections.add(websocket)
        logger.info(f"Client connected. Total connections: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        """클라이언트 연결 해제"""
        self.active_connections.discard(websocket)
        logger.info(f"Client disconnected. Total connections: {len(self.active_connections)}")

    async def broadcast(self, message: dict):
        """모든 클라이언트에게 메시지 전송"""
        disconnected = set()

        for connection in self.active_connections:
            try:
                # datetime 직렬화 문제 해결을 위해 default=str 사용
                await connection.send_text(json.dumps(message, default=str))
            except Exception as e:
                logger.error(f"Failed to send message to client: {e}")
                disconnected.add(connection)

        # 연결 끊긴 클라이언트 제거
        for conn in disconnected:
            self.disconnect(conn)


manager = ConnectionManager()


def get_bot():
    """봇 인스턴스 가져오기"""
    from main import trading_bot
    return trading_bot


@router.websocket("/live")
async def websocket_live_updates(websocket: WebSocket):
    """
    실시간 업데이트 WebSocket 엔드포인트

    전송 메시지 타입:
    - status: 봇 상태 업데이트
    - price: 가격 업데이트
    - trade: 거래 실행 알림
    - log: 로그 메시지
    """
    await manager.connect(websocket)
    update_interval = 10  # 10초마다 상태 업데이트
    client_timeout = 120  # 클라이언트 메시지 타임아웃 2분 (백그라운드 탭 고려)

    try:
        # 초기 상태 전송
        bot = get_bot()
        if bot:
            try:
                status = bot.get_status()
                await websocket.send_text(json.dumps({
                    "type": "status",
                    "data": status,
                    "timestamp": datetime.now().isoformat()
                }, default=str))
            except Exception as e:
                logger.warning(f"Failed to send initial status: {e}")

        last_client_message = asyncio.get_event_loop().time()

        # 클라이언트로부터 메시지 수신 대기
        while True:
            try:
                # 클라이언트 메시지 수신 (keep-alive) - update_interval 타임아웃
                data = await asyncio.wait_for(
                    websocket.receive_text(),
                    timeout=float(update_interval)
                )
                last_client_message = asyncio.get_event_loop().time()

                # ping/pong 처리
                if data == "ping":
                    await websocket.send_text(json.dumps({
                        "type": "pong",
                        "timestamp": datetime.now().isoformat()
                    }, default=str))

            except asyncio.TimeoutError:
                # 클라이언트 타임아웃 체크 (백그라운드 탭이 오래 방치된 경우)
                current_time = asyncio.get_event_loop().time()
                if current_time - last_client_message > client_timeout:
                    logger.info("Client inactive for too long, closing connection")
                    break

                # 주기적으로 상태 업데이트 전송 + 서버 heartbeat
                if bot:
                    try:
                        # 봇 상태
                        status = bot.get_status()

                        # 현재 가격 정보
                        prices = {}
                        for ticker in bot.tickers[:10]:  # 최대 10개만 조회 (속도 개선)
                            try:
                                price = bot.exchange.get_current_price(ticker)
                                if price:
                                    prices[ticker] = price
                            except Exception:
                                pass  # 개별 가격 조회 실패는 무시

                        # 상태 전송
                        await websocket.send_text(json.dumps({
                            "type": "update",
                            "data": {
                                "status": status,
                                "prices": prices
                            },
                            "timestamp": datetime.now().isoformat()
                        }, default=str))

                    except Exception as e:
                        logger.warning(f"Error preparing update: {e}")
                        # 연결 유지를 위해 최소한 heartbeat 전송
                        try:
                            await websocket.send_text(json.dumps({
                                "type": "heartbeat",
                                "timestamp": datetime.now().isoformat()
                            }))
                        except Exception:
                            break  # heartbeat도 실패하면 연결 종료
                else:
                    # 봇이 없어도 heartbeat 전송하여 연결 유지
                    try:
                        await websocket.send_text(json.dumps({
                            "type": "heartbeat",
                            "timestamp": datetime.now().isoformat()
                        }))
                    except Exception:
                        break

            except WebSocketDisconnect:
                logger.info("Client initiated disconnect")
                break

            except Exception as e:
                # 예상치 못한 에러 - 로깅 후 계속 시도
                logger.warning(f"WebSocket receive error: {type(e).__name__}: {e}")
                await asyncio.sleep(1)  # 잠시 대기 후 재시도

    except WebSocketDisconnect:
        logger.info("WebSocket disconnected normally")

    except Exception as e:
        logger.error(f"WebSocket error: {type(e).__name__}: {e}")
        logger.debug(traceback.format_exc())

    finally:
        manager.disconnect(websocket)


@router.websocket("/logs")
async def websocket_logs(websocket: WebSocket):
    """
    실시간 로그 스트리밍 WebSocket 엔드포인트

    로그 레벨에 따른 메시지 전송
    """
    await websocket.accept()
    logger.info("Log streaming client connected")

    try:
        # 로그 핸들러를 통해 실시간 로그 전송
        # (실제 구현은 logging handler를 커스터마이징 필요)

        # 예시: 주기적으로 최근 로그 전송
        while True:
            try:
                # Keep-alive
                await asyncio.sleep(5)

                # 로그 메시지 전송 (실제로는 로그 핸들러에서 가져와야 함)
                await websocket.send_text(json.dumps({
                    "type": "log",
                    "level": "info",
                    "message": "System is running normally",
                    "timestamp": datetime.now().isoformat()
                }, default=str))

            except WebSocketDisconnect:
                break

    except Exception as e:
        logger.error(f"Log WebSocket error: {e}")

    finally:
        logger.info("Log streaming client disconnected")


async def broadcast_trade_event(trade_data: dict):
    """
    거래 이벤트 브로드캐스트
    (trading_bot.py에서 호출 가능)
    """
    await manager.broadcast({
        "type": "trade",
        "data": trade_data,
        "timestamp": datetime.now().isoformat()
    })


async def broadcast_log(level: str, message: str):
    """
    로그 메시지 브로드캐스트
    (로그 핸들러에서 호출 가능)
    """
    await manager.broadcast({
        "type": "log",
        "level": level,
        "message": message,
        "timestamp": datetime.now().isoformat()
    })
