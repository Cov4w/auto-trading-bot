"""
Bot Control Router
==================
봇 시작/중지, 설정 변경, 추천 업데이트 등 제어 API
"""

from fastapi import APIRouter, HTTPException, Depends
from typing import Dict
import logging

from models.schemas import (
    BotStatus, SuccessResponse, StartBotRequest, StopBotRequest,
    UpdateConfigRequest, TickerToggleRequest, User
)


router = APIRouter()
logger = logging.getLogger(__name__)


def get_current_user():
    """Import auth dependency to avoid circular imports"""
    from routers.auth import get_current_user
    return get_current_user


def get_bot():
    """봇 인스턴스 가져오기"""
    from main import trading_bot
    if trading_bot is None:
        raise HTTPException(status_code=500, detail="Bot not initialized")
    return trading_bot


@router.get("/status", response_model=BotStatus)
async def get_bot_status():
    """
    봇 현재 상태 조회

    Returns:
        BotStatus: 봇의 현재 상태 정보
    """
    try:
        bot = get_bot()
        status = bot.get_status()
        return BotStatus(**status)
    except Exception as e:
        logger.error(f"Failed to get bot status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/start", response_model=SuccessResponse)
async def start_bot(request: StartBotRequest = None, current_user: User = Depends(get_current_user)):
    """
    봇 시작

    Args:
        request: 선택적으로 티커 리스트 지정 가능

    Returns:
        SuccessResponse: 성공 여부
    """
    try:
        bot = get_bot()

        if bot.is_running:
            return SuccessResponse(
                success=False,
                message="Bot is already running"
            )

        # 티커 설정 (요청에 포함된 경우)
        if request and request.tickers:
            bot.tickers = request.tickers

        bot.start()

        return SuccessResponse(
            success=True,
            message="Bot started successfully",
            data={"tickers": bot.tickers}
        )

    except Exception as e:
        logger.error(f"Failed to start bot: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/stop", response_model=SuccessResponse)
async def stop_bot(current_user: User = Depends(get_current_user)):
    """
    봇 중지

    Returns:
        SuccessResponse: 성공 여부
    """
    try:
        bot = get_bot()

        if not bot.is_running:
            return SuccessResponse(
                success=False,
                message="Bot is not running"
            )

        bot.stop()

        return SuccessResponse(
            success=True,
            message="Bot stopped successfully"
        )

    except Exception as e:
        logger.error(f"Failed to stop bot: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/retrain", response_model=SuccessResponse)
async def retrain_model(current_user: User = Depends(get_current_user)):
    """
    모델 강제 재학습

    Returns:
        SuccessResponse: 성공 여부
    """
    try:
        bot = get_bot()
        bot.force_retrain()

        return SuccessResponse(
            success=True,
            message="Model retrained successfully",
            data={
                "accuracy": bot.learner.metrics.get('accuracy', 0),
                "total_samples": bot.learner.metrics.get('total_samples', 0)
            }
        )

    except Exception as e:
        logger.error(f"Failed to retrain model: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/backtest/run", response_model=SuccessResponse)
async def run_backtest(
    ticker: str = None,
    days: int = 200,
    async_mode: bool = True,
    current_user: User = Depends(get_current_user)
):
    """
    백테스팅 실행

    Args:
        ticker: 백테스팅할 코인 (None이면 현재 주요 코인 사용)
        days: 테스트 기간 (일, 최대 200일)
        async_mode: 백그라운드 실행 여부

    Returns:
        SuccessResponse: 백테스팅 시작/완료 결과
    """
    try:
        bot = get_bot()
        result = bot.run_backtest(ticker=ticker, days=min(days, 200), async_mode=async_mode)

        return SuccessResponse(
            success=True,
            message=result.get('message', 'Backtest started'),
            data=result
        )

    except Exception as e:
        logger.error(f"Failed to run backtest: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/backtest/status", response_model=SuccessResponse)
async def get_backtest_status(current_user: User = Depends(get_current_user)):
    """
    백테스팅 상태 조회

    Returns:
        SuccessResponse: 백테스팅 진행 상태
    """
    try:
        bot = get_bot()
        status = bot.get_backtest_status()

        return SuccessResponse(
            success=True,
            message="Backtest status retrieved",
            data=status
        )

    except Exception as e:
        logger.error(f"Failed to get backtest status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/update-recommendations", response_model=SuccessResponse)
async def update_recommendations(current_user: User = Depends(get_current_user)):
    """
    코인 추천 목록 업데이트 (비동기)

    Returns:
        SuccessResponse: 성공 여부
    """
    try:
        bot = get_bot()

        if bot.is_updating_recommendations:
            return SuccessResponse(
                success=False,
                message="Recommendation update already in progress"
            )

        bot.update_recommendations_async()

        return SuccessResponse(
            success=True,
            message="Recommendation update started"
        )

    except Exception as e:
        logger.error(f"Failed to update recommendations: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/config", response_model=SuccessResponse)
async def update_config(request: UpdateConfigRequest, current_user: User = Depends(get_current_user)):
    """
    봇 설정 업데이트

    Args:
        request: 업데이트할 설정 (trade_amount, target_profit, stop_loss, rebuy_threshold)

    Returns:
        SuccessResponse: 성공 여부
    """
    try:
        bot = get_bot()

        updated = {}

        if request.trade_amount is not None:
            bot.trade_amount = request.trade_amount
            updated['trade_amount'] = request.trade_amount

        if request.target_profit is not None:
            bot.target_profit = request.target_profit
            updated['target_profit'] = request.target_profit

        if request.stop_loss is not None:
            bot.stop_loss = request.stop_loss
            updated['stop_loss'] = request.stop_loss

        if request.rebuy_threshold is not None:
            bot.rebuy_threshold = request.rebuy_threshold
            updated['rebuy_threshold'] = request.rebuy_threshold

        if request.use_net_profit is not None:
            bot.use_net_profit = request.use_net_profit
            updated['use_net_profit'] = request.use_net_profit

        if request.use_dynamic_target is not None:
            bot.use_dynamic_target = request.use_dynamic_target
            updated['use_dynamic_target'] = request.use_dynamic_target

        if request.use_dynamic_sizing is not None:
            bot.use_dynamic_sizing = request.use_dynamic_sizing
            updated['use_dynamic_sizing'] = request.use_dynamic_sizing

        logger.info("=" * 60)
        logger.info("⚙️ TRADING SETTINGS UPDATED")
        for key, value in updated.items():
            if 'profit' in key or 'loss' in key or 'threshold' in key:
                logger.info(f"   {key}: {value * 100:.1f}%")
            elif isinstance(value, bool):
                logger.info(f"   {key}: {'Enabled' if value else 'Disabled'}")
            else:
                logger.info(f"   {key}: {value:,.0f} KRW")
        logger.info("=" * 60)

        return SuccessResponse(
            success=True,
            message="Configuration updated successfully",
            data={"updated": updated}
        )

    except Exception as e:
        logger.error(f"Failed to update config: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/ticker/toggle", response_model=SuccessResponse)
async def toggle_ticker(request: TickerToggleRequest, current_user: User = Depends(get_current_user)):
    """
    티커 추가/제거 토글

    Args:
        request: 토글할 티커

    Returns:
        SuccessResponse: 성공 여부
    """
    try:
        bot = get_bot()

        was_active = request.ticker in bot.tickers
        bot.toggle_ticker(request.ticker)
        is_active = request.ticker in bot.tickers

        action = "added" if is_active else "removed"

        return SuccessResponse(
            success=True,
            message=f"Ticker {request.ticker} {action}",
            data={
                "ticker": request.ticker,
                "is_active": is_active,
                "active_tickers": bot.tickers
            }
        )

    except Exception as e:
        logger.error(f"Failed to toggle ticker: {e}")
        raise HTTPException(status_code=500, detail=str(e))
