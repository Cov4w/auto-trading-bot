"""
Trading Core Engine
===================
실시간 가격 모니터링, 신호 감지, 주문 실행, 그리고 결과 기록 후 자가 학습을 트리거하는
트레이딩 봇의 핵심 엔진입니다.

Trading Flow:
1. 실시간 가격 모니터링 (60초 주기)
2. 특징 추출 및 AI 예측
3. 매수 신호 감지 → 주문 실행
4. 포지션 모니터링 (목표가/손절가/타이밍 매도)
5. 매도 완료 → 결과 기록 → N건 누적 시 모델 재학습
"""

import time
import threading
from datetime import datetime, timedelta
from typing import Optional, Dict
import logging
import os
from dotenv import load_dotenv


import pandas as pd
import numpy as np

from data_manager import TradeMemory, ModelLearner, FeatureEngineer
from coin_selector import CoinSelector
from exchange_manager import ExchangeManager

# Load Environment Variables
load_dotenv()

# Setup Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class TradingBot:
    """
    자가 진화 트레이딩 봇
    
    Renaissance Technologies 스타일의 지속 학습 메커니즘을 탑재한
    자동 매매 봇입니다.
    """
    
    def __init__(self):
        # Exchange Selection
        self.exchange_name = os.getenv("EXCHANGE", "bithumb").lower()
        
        # Load Keys based on Exchange
        if self.exchange_name == 'bithumb':
            self.access_key = os.getenv("BITHUMB_CONNECT_KEY")
            self.secret_key = os.getenv("BITHUMB_SECRET_KEY")
        elif self.exchange_name == 'upbit':
            self.access_key = os.getenv("UPBIT_ACCESS_KEY")
            self.secret_key = os.getenv("UPBIT_SECRET_KEY")
        
        # Initialize Exchange Manager
        self.exchange = ExchangeManager(self.exchange_name, self.access_key, self.secret_key)
        
        # Trading Configuration
        # Trading Configuration
        self.tickers = [os.getenv("TICKER", "BTC")] # Manage multiple tickers
        self.ticker = self.tickers[0] # Keep for backward compatibility with some UI parts if needed, serves as "primary"
        self.use_ai_selection = os.getenv("USE_AI_COIN_SELECTION", "true").lower() == "true"
        self.trade_amount = float(os.getenv("TRADE_AMOUNT", 10000))
        self.target_profit = float(os.getenv("TARGET_PROFIT", 0.02))
        self.stop_loss = float(os.getenv("STOP_LOSS", 0.02))
        self.rebuy_threshold = float(os.getenv("REBUY_THRESHOLD", 0.015))  # 재매수 하락폭
        
        # Learning Configuration
        self.retrain_threshold = int(os.getenv("RETRAIN_THRESHOLD", 10))
        self.confidence_threshold = float(os.getenv("MODEL_CONFIDENCE_THRESHOLD", 0.7))
        
        # 🆕 Trailing Stop Loss Configuration
        self.trailing_stop_enabled = True
        self.trailing_activation = 0.015  # 1.5% 수익 시 트레일링 활성화
        self.trailing_distance = 0.01      # peak 대비 -1% 하락 시 매도
        
        # Risk Management
        self.max_position_size = float(os.getenv("MAX_POSITION_SIZE", 0.3))
        
        # Data & Model Manager
        self.memory = TradeMemory()
        self.learner = ModelLearner()
        
        # 🔥 AI Coin Selector
        self.coin_selector = CoinSelector(self.learner, self.memory, self.exchange)
        self.recommended_coins = []  # 추천 코인 리스트 캐시
        
        # Trading State
        self.is_running = False
        self.positions: Dict[str, Dict] = {}  # {ticker: {position_info}}
        self.thread: Optional[threading.Thread] = None
        
        # Performance Metrics (Session)
        self.session_trades = 0
        self.session_wins = 0
        
        # Async Recommendation Update
        self.is_updating_recommendations = False
        self.recommendation_thread = None
        
        # 🔥 매도 후 재매수 방지 (쿨다운)
        self.sold_coins_cooldown = {}  # {ticker: exit_price}
        self.failed_buy_cooldown = {}  # {ticker: timestamp} -> 매수 실패 시 쿨다운
        
        # 🔄 Auto Recommendation Timer (5분마다 자동 업데이트 + 1위 종목 추가)
        self.auto_recommendation_enabled = True
        self.auto_recommendation_interval = 30  # 30초 (더 빠른 업데이트)
        self.auto_timer_thread = None
        
        # 🔄 봇 초기화 시 포지션 자동 복구 (START 버튼 전에도 보유 코인 감지)
        self._recover_positions()
        
        # 🛑 Max Drawdown Limit
        self.max_drawdown = 0.05  # -5% 손실 시 중단
        self.initial_balance = None
        self.peak_balance = None
        self.last_mdd_check = 0  # 타임스탬프
        
        logger.info("=" * 60)
        logger.info("🚀 Trading Bot Initialized")
        logger.info(f"   AI Coin Selection: {'✅ Enabled' if self.use_ai_selection else '❌ Disabled'}")
        logger.info(f"   Tickers: {self.tickers}")
        logger.info(f"   Trade Amount: {self.trade_amount:,.0f} KRW")
        logger.info(f"   Target Profit: {self.target_profit * 100}%")
        logger.info(f"   Stop Loss: {self.stop_loss * 100}%")
        logger.info(f"   Auto Recommendation: {'✅ ON (5min)' if self.auto_recommendation_enabled else '❌ OFF'}")
        logger.info("=" * 60)
    
    def start(self):
        """봇 시작 (백그라운드 스레드)"""
        if self.is_running:
            logger.warning("⚠️ Bot is already running!")
            return
        
        self.is_running = True
        
        # 🛡️ MDD 초기화
        try:
            balance_info = self.exchange.get_balance(ticker="KRW")
            current_balance = balance_info.get('krw_balance', 0) if isinstance(balance_info, dict) else 0
            self.initial_balance = current_balance
            self.peak_balance = current_balance
            logger.info(f"💰 Initial Balance for MDD: {current_balance:,.0f} KRW (Limit: -{self.max_drawdown*100}%)")
        except Exception as e:
            logger.warning(f"⚠️ Failed to init MDD balance: {e}")
            self.initial_balance = 0
            self.peak_balance = 0

        self.thread = threading.Thread(target=self._trading_loop, daemon=True)
        self.thread.start()
        
        # 🕐 Auto Recommendation Timer 시작
        if self.auto_recommendation_enabled:
            self.auto_timer_thread = threading.Thread(target=self._auto_recommendation_timer, daemon=True)
            self.auto_timer_thread.start()
            logger.info("⏰ Auto recommendation timer started (5-min interval)")
        
        logger.info("✅ Bot STARTED")
    
    def stop(self):
        """봇 중지"""
        if not self.is_running:
            logger.warning("⚠️ Bot is not running!")
            return
        
        self.is_running = False
        if self.thread:
            self.thread.join(timeout=5)
        logger.info("🛑 Bot STOPPED")
    
    def _check_drawdown_limit(self):
        """
        🛑 Max Drawdown (MDD) 체크
        - 전체 자산(현금 + 보유코인) 기준
        - Peak 대비 5% 이상 하락 시 봇 중지
        """
        try:
            # 1. API 호출 제한 (1분마다 체크)
            if time.time() - self.last_mdd_check < 60:
                return False
            self.last_mdd_check = time.time()
            
            # 2. 전체 자산 계산
            # KRW 잔고
            krw_info = self.exchange.get_balance("KRW") # 아무 티커나 줘도 KRW 잔고 나옴
            cash = krw_info.get('krw_balance', 0)
            
            # 보유 코인 가치
            holdings = self.exchange.get_holdings()
            coin_value = 0
            
            for h in holdings:
                ticker = h['ticker']
                amount = h['amount']
                # 현재가 조회 (없으면 평단가 사용)
                cp = self.exchange.get_current_price(ticker)
                if not cp:
                    cp = h.get('avg_buy_price', 0)
                
                coin_value += amount * cp
            
            total_equity = cash + coin_value
            
            # 3. Peak 업데이트
            if self.peak_balance is None or total_equity > self.peak_balance:
                self.peak_balance = total_equity
                # logger.debug(f"💰 New Peak Balance: {total_equity:,.0f} KRW")
            
            # 4. MDD 계산
            if self.peak_balance > 0:
                drawdown = (self.peak_balance - total_equity) / self.peak_balance
            else:
                drawdown = 0
            
            # logger.debug(f"📉 Check MDD: {drawdown:.2%} (Limit: {self.max_drawdown:.0%})")
            
            # 5. 한도 초과 시 비상 정지
            if drawdown >= self.max_drawdown:
                logger.error("=" * 60)
                logger.error(f"🛑 MAX DRAWDOWN LIMIT REACHED: -{drawdown*100:.2f}%")
                logger.error(f"   Peak: {self.peak_balance:,.0f} KRW")
                logger.error(f"   Current: {total_equity:,.0f} KRW")
                logger.error("🛑 STOPPING BOT & SELLING ALL POSITIONS")
                logger.error("=" * 60)
                
                # 모든 포지션 시장가 청산
                for ticker in list(self.positions.keys()):
                    logger.warning(f"🚨 MDD Emergency Sell: {ticker}")
                    self._execute_sell(ticker, 0, "MDD Triggered")
                
                self.stop()
                return True
                
        except Exception as e:
            logger.error(f"⚠️ MDD check failed: {e}")
        
        return False

    def _trading_loop(self):
        """
        메인 트레이딩 루프
        
        60초 주기로 시장을 모니터링하고 매매 로직을 실행합니다.
        """
        logger.info("🔄 Trading Loop Started")
        
        if self.learner.model is None:
            self._initial_training()
            
        # Recover positions from exchange (Sync)
        self._recover_positions()
        
        while self.is_running:
            try:
                # 🛑 MDD 체크 (비상 정지)
                if self._check_drawdown_limit():
                    break
                
                # 1. 포지션 조회 (업비트 실시간 싱크)
                self._sync_positions_with_exchange()
                
                # 1. 포지션 체크 (모든 보유 포지션)
                for ticker in list(self.positions.keys()):
                    self._check_exit_conditions(ticker)
                
                # 2. 진입 체크 (모든 선택된 티커)
                # 🛡️ 잔액 사전 체크: 잔액 부족 시 전체 매수 스킵
                balance_info = self.get_account_balance()
                available_krw = balance_info.get('krw_balance', 0)
                
                if available_krw < self.trade_amount:
                    logger.debug(f"💸 Insufficient balance ({available_krw:,.0f} KRW). Skipping all buy checks.")
                else:
                    for ticker in self.tickers:
                        # 이미 포지션이 있는 코인은 건너뜀
                        if ticker not in self.positions:
                            self._check_entry_conditions(ticker)
                
                # 2. 대기 (10초)
                time.sleep(10)
                
            except Exception as e:
                logger.error(f"❌ Error in trading loop: {e}")
                time.sleep(10)
        
        logger.info("🔄 Trading Loop Stopped")

    def _recover_positions(self):
        """
        거래소 잔고를 조회하여 누락된 포지션을 복구합니다.
        (재시작 시 포지션 유지용 - 보유 시간도 유지)
        """
        logger.info("🔄 Syncing positions from exchange...")
        try:
            # 0. DB에서 열린 포지션 조회 (진입 시간 복구용)
            db_positions = self.memory.get_open_positions()
            db_lookup = {p['ticker']: p for p in db_positions}
            
            # 1. 모든 보유 코인 조회 (Upbit API 사용)
            holdings = self.exchange.get_holdings()
            
            for item in holdings:
                ticker = item['ticker']
                amount = item['amount']
                avg_price = item['avg_buy_price']
                
                # 이미 봇이 알고 있으면 스킵
                if ticker in self.positions: continue
                
                # 포지션 등록 (평단가 정보 활용)
                entry_price = avg_price
                if entry_price <= 0:
                     entry_price = self.exchange.get_current_price(ticker) or 0
                
                if entry_price <= 0:
                    continue
                
                # 🔥 DB에서 진입 시간 복구 (없으면 현재 시간)
                if ticker in db_lookup:
                    db_entry = db_lookup[ticker]
                    trade_id = db_entry['id']
                    entry_time_str = db_entry['entry_time']
                    try:
                        entry_time = datetime.fromisoformat(entry_time_str)
                    except:
                        entry_time = datetime.now()
                    logger.info(f"♻️ Recovered Position: {ticker} (Amt: {amount:.4f}, Avg: {entry_price:,.0f}, EntryTime: {entry_time_str})")
                else:
                    trade_id = f"recovered_{ticker}_{int(time.time())}"
                    entry_time = datetime.now()
                    logger.info(f"♻️ New Position: {ticker} (Amt: {amount:.4f}, Avg: {entry_price:,.0f})")

                self.positions[ticker] = {
                    "ticker": ticker,
                    "trade_id": trade_id,
                    "entry_price": entry_price,
                    "amount": amount,
                    "entry_time": entry_time  # 🔥 DB에서 복구된 시간!
                }
                
                # 감시 목록(Tickers)에 자동 추가
                if ticker not in self.tickers:
                    self.tickers.append(ticker)
                    logger.info(f"➕ Auto-added to watch list: {ticker}")
            
            logger.info(f"✅ Position Recovery Complete. Managing {len(self.positions)} positions.")
            
        except Exception as e:
            logger.error(f"❌ Position recovery failed: {e}")
    
    def _sync_positions_with_exchange(self):
        """
        실시간 잔고 조회하여 수동 매도된 포지션 제거
        """
        try:
            holdings = self.exchange.get_holdings()
            holding_tickers = {h['ticker'] for h in holdings}
            
            # 봇은 포지션으로 인식하고 있지만, 거래소에는 없는 코인 찾기
            removed_tickers = []
            for ticker in list(self.positions.keys()):
                if ticker not in holding_tickers:
                    removed_tickers.append(ticker)
                    del self.positions[ticker]
            
            # 로그 출력
            if removed_tickers:
                for ticker in removed_tickers:
                    logger.info(f"🗑️ Position removed: {ticker} (Sold manually or insufficient balance)")
                    # Active Tickers에서도 제거
                    if ticker in self.tickers:
                        self.tickers.remove(ticker)
        
        except Exception as e:
            logger.error(f"❌ Position sync failed: {e}")
    
    def _initial_training(self):
        """
        초기 모델 학습 (Cold Start)
        
        과거 30일 데이터를 수집하여 기본 모델을 생성합니다.
        """
        logger.info("🎓 Starting Initial Model Training...")
        
        try:
            # 과거 30일 데이터 수집 (Primary Ticker 기준)
            df = self.exchange.get_ohlcv(self.tickers[0], interval="day")
            
            if df is None or len(df) < 30:
                logger.warning("⚠️ Insufficient historical data. Using demo mode.")
                return
            
            # 특징 추출 및 라벨 생성 (단순화: 다음 날 상승 여부)
            features_list = []
            labels = []
            
            for i in range(len(df) - 1):
                # i번째 날의 특징 추출
                window_df = df.iloc[:i+1]
                if len(window_df) < 30:
                    continue
                
                features = FeatureEngineer.extract_features(window_df)
                if not features:
                    continue
                
                # 다음 날 상승 여부 (라벨)
                next_day_return = (df.iloc[i+1]['close'] - df.iloc[i]['close']) / df.iloc[i]['close']
                label = 1 if next_day_return > 0 else 0
                
                features_list.append(features)
                labels.append(label)
            
            # DataFrame으로 변환
            X = pd.DataFrame(features_list)
            y = pd.Series(labels)
            
            # 모델 학습
            if len(X) >= 30:
                self.learner.train_initial_model(X, y)
                logger.info("✅ Initial Training Complete")
            else:
                logger.warning("⚠️ Not enough data for training")
        
        except Exception as e:
            logger.error(f"❌ Initial training failed: {e}")
    
    def _check_entry_conditions(self, ticker: str):
        """
        매수 조건 체크 및 진입
        """
        try:
            # 🚫 매수 실패 쿨다운 체크 (1분)
            if ticker in self.failed_buy_cooldown:
                last_fail_time = self.failed_buy_cooldown[ticker]
                if datetime.now() - last_fail_time < timedelta(minutes=1):
                    # 쿨다운 중이면 스킵
                    return
                else:
                    # 시간 지났으면 해제 및 재도전 허용
                    del self.failed_buy_cooldown[ticker]
                    logger.info(f"🔓 {ticker} buy cooldown released.")

            # 1. 현재 데이터 수집
            df = self.exchange.get_ohlcv(ticker)
            if df is None or len(df) < 30:
                return
            
            # 🛡️ 최소 가격 필터 (저가 코인 제외)
            current_price = self.exchange.get_current_price(ticker)
            MIN_PRICE = 100  # 100원 미만 코인 제외
            if current_price and current_price < MIN_PRICE:
                logger.debug(f"⚠️ [{ticker}] Price too low ({current_price} KRW), skipping")
                return
            
            # 2. 특징 추출
            features = FeatureEngineer.extract_features(df)
            if not features:
                return
            
            # 3. AI 예측
            features_df = FeatureEngineer.features_to_dataframe(features)
            prediction, confidence = self.learner.predict(features_df)
            
            # 4. 매수 조건 평가 (🆕 다양화된 진입 조건)
            rsi = features['rsi']
            bb_position = features['bb_position']
            rsi_change = features.get('rsi_change', 0)
            volume_trend = features.get('volume_trend', 0)
            
            # ❄️ Hybrid Mode: AI가 없거나 확신이 없어도, 기술적 지표가 강력하면 매수 (데이터 수집 겸용)
            # 조건: RSI 30 미만(과매도) AND 반등 시작(Change>0) AND 볼린저 하단
            is_strong_technical_signal = (rsi < 30) and (rsi_change > 0) and (bb_position < 0.2)
            
            if is_strong_technical_signal:
                logger.info(f"💎 Technical Value Buy: {ticker} (RSI={rsi:.1f}, Change={rsi_change:.1f}) - AI Override")
                self._execute_buy(ticker, features, 0.5)  # 확신도 0.5(중립)로 진입
                return
            
            # 🔧 확신도 기반 시그널 (클래스 수에 상관없이 작동)
            # confidence는 "좋은 수익" 확률 (class 2 또는 class 1)
            ai_profit_signal = confidence > self.confidence_threshold
            
            # Mean Reversion 시그널 (과매도 또는 볼린저 하단)
            oversold = (rsi < 30) or (bb_position < 0.2)
            
            # 🆕 모멘텀 시그널: RSI가 상승 중 (과매도 회복 패턴)
            momentum_signal = (rsi < 40) and (rsi_change > 2)  # RSI 35 이하에서 상승 중
            
            # 🆕 거래량 시그널: 거래량 증가 중
            volume_signal = volume_trend > 0.2  # 거래량 20% 증가
            
            # 🛡️ 중복 매수 방지: 이미 포지션이 있으면 스킵
            if ticker in self.positions:
                logger.debug(f"📊 [{ticker}] Already in position. Skipping buy.")
                return
            
            # 🚫 쿨다운 체크: 익절/손절에 따라 다른 로직
            if ticker in self.sold_coins_cooldown:
                cooldown_info = self.sold_coins_cooldown[ticker]
                
                # 🔧 하위 호환성: 기존 float 형식 처리
                if isinstance(cooldown_info, (int, float)):
                    # 기존 형식 → 새 형식으로 변환 (익절로 가정)
                    cooldown_info = {'exit_price': cooldown_info, 'reason': 'Target Profit'}
                    self.sold_coins_cooldown[ticker] = cooldown_info
                
                last_exit_price = cooldown_info['exit_price']
                exit_reason = cooldown_info['reason']
                current_price = self.exchange.get_current_price(ticker)
                
                if not current_price:
                    return
                
                # 익절 케이스: 가격 하락 시 재매수
                if 'Profit' in exit_reason:
                    rebuy_price_threshold = last_exit_price * (1 - self.rebuy_threshold)
                    
                    if current_price >= rebuy_price_threshold:
                        logger.debug(
                            f"🚫 [{ticker}] Profit cooldown active. "
                            f"Current: {current_price:,.0f} >= Threshold: {rebuy_price_threshold:,.0f}"
                        )
                        return
                    else:
                        drop_pct = (last_exit_price - current_price) / last_exit_price * 100
                        logger.info(
                            f"✅ [{ticker}] Profit cooldown released! "
                            f"Price dropped {drop_pct:.1f}%"
                        )
                
                # 손절 케이스: 가격 회복 시 재매수
                else:
                    rebuy_price_threshold = last_exit_price * (1 + self.rebuy_threshold)
                    
                    if current_price <= rebuy_price_threshold:
                        logger.debug(
                            f"🚫 [{ticker}] Loss cooldown active. "
                            f"Current: {current_price:,.0f} <= Threshold: {rebuy_price_threshold:,.0f}"
                        )
                        return
                    else:
                        rise_pct = (current_price - last_exit_price) / last_exit_price * 100
                        logger.info(
                            f"✅ [{ticker}] Loss cooldown released! "
                            f"Price recovered {rise_pct:.1f}%"
                        )
                
                # 쿨다운 해제
                del self.sold_coins_cooldown[ticker]
                # 티커 리스트에 재추가
                if ticker not in self.tickers:
                    self.tickers.append(ticker)
            
            # 🆕 다양화된 매수 조건 (3가지 시나리오)
            # 시나리오 1: AI가 좋은 수익 예측 + 과매도
            condition_1 = ai_profit_signal and oversold
            
            # 시나리오 2: AI 매우 높은 확신도(90%+) → 과매도 조건 완화
            condition_2 = confidence > 0.90
            
            # 시나리오 3: 과매도 회복 패턴 (RSI 상승 + 거래량 증가)
            condition_3 = oversold and momentum_signal and volume_signal and (confidence > 0.7)
            
            if condition_1 or condition_2 or condition_3:
                reason = "AI+Oversold" if condition_1 else ("High Confidence" if condition_2 else "Momentum Recovery")
                logger.info(f"✅ [{ticker}] Entry Signal: {reason} (Conf={confidence:.1%}, RSI={rsi:.1f})")
                self._execute_buy(ticker, features, confidence)
            else:
                logger.debug(
                    f"📊 [{ticker}] No Entry Signal - "
                    f"Pred:{prediction}, Conf:{confidence:.2%}, "
                    f"RSI:{rsi:.1f}, BB:{bb_position:.2f}"
                )
        
        except Exception as e:
            logger.error(f"❌ Entry check failed: {e}")
    
    def calculate_position_size(self, ticker: str, confidence: float) -> float:
        """
        🔥 Dynamic Position Sizing (Kelly Criterion)
        확신도와 승률에 따라 투자 금액 동적 조절
        """
        try:
            # 1. 통계 데이터 조회
            stats = self.memory.get_statistics()
            win_rate = stats.get('win_rate', 0.0)
            avg_win = stats.get('avg_profit', 0.01)  # 기본 1%
            avg_loss = abs(stats.get('avg_loss', -0.01))
            
            # 통계 신뢰도 부족 시 (데이터 30개 미만) -> 고정 금액
            if stats.get('total_trades', 0) < 30:
                return float(self.trade_amount)
            
            # 2. Kelly Criterion 계산
            # f* = (p * b - q) / b
            # p = win_rate, b = avg_win / avg_loss, q = 1 - p
            if avg_loss > 0:
                b = avg_win / avg_loss
                kelly_fraction = (win_rate * b - (1 - win_rate)) / b
            else:
                kelly_fraction = 0
            
            # 3. Half-Kelly (안전 모드) 및 제한
            # 이론값의 50%만 적용, 최대 25% 제한
            kelly_fraction = max(0, min(kelly_fraction * 0.5, 0.25))
            
            # 4. 잔액 조회
            balance = self.exchange.get_balance(ticker="KRW")
            if isinstance(balance, dict):
                 krw_balance = balance.get('krw_balance', 0)
            else:
                 krw_balance = 0
            
            # 5. 최종 금액 계산 (Kelly * Confidence)
            optimal_amount = krw_balance * kelly_fraction * confidence
            
            # 6. 최소/최대 한도 적용
            min_amount = 5002  # 업비트 최소 주문 5000원 + 여유
            max_amount = krw_balance * 0.3  # 최대 잔액의 30%까지만
            
            final_amount = max(min_amount, min(optimal_amount, max_amount))
            
            logger.info(
                f"💰 Position Sizing: {final_amount:,.0f} KRW "
                f"(Kelly={kelly_fraction:.1%}, Conf={confidence:.1%}, Bal={krw_balance:,.0f})"
            )
            return final_amount
            
        except Exception as e:
            logger.warning(f"⚠️ Position sizing failed: {e}. Using default.")
            return float(self.trade_amount)

    def _execute_buy(self, ticker: str, features: Dict, confidence: float):
        """
        매수 주문 실행
        """
        try:
            # 💰 Dynamic Position Sizing 적용
            trade_money = self.calculate_position_size(ticker, confidence)
            
            # 🛡️ 최소 주문 금액 검증 (5,000원)
            if trade_money < 5000:
                logger.warning(
                    f"⚠️ Cannot buy {ticker}: Trade amount ({trade_money:,.0f} KRW) "
                    f"is below minimum (5,000 KRW)."
                )
                logger.info("💡 Tip: Increase 'Trade Amount' to at least 5,000 KRW in sidebar.")
                return
            
            # 1. 현재 가격
            current_price = self.exchange.get_current_price(ticker)
            if not current_price:
                logger.error("❌ Failed to get current price")
                return
            
            # 2. 매수 수량 계산
            buy_amount = trade_money / current_price
            
            # 3. 주문 실행 (Market Order)
            logger.info(f"🚀 Executing REAL Buy Order for {ticker} (Amt: {trade_money:,.0f} KRW)...")
            order = self.exchange.buy_market_order(ticker, trade_money, buy_amount)
            
            if not order:
                logger.error("❌ Order Failed")
                # 실패 쿨다운 등록 (1분)
                self.failed_buy_cooldown[ticker] = datetime.now()
                logger.warning(f"⏳ {ticker} added to failed buy cooldown for 1 minute.")
                return
            
            # 데모 모드 (실제 주문 없이 시뮬레이션)
            # logger.info("💰 [DEMO] Buy Order Executed")
            logger.info(f"   Ticker: {ticker}")
            logger.info(f"   Price: {current_price:,.0f} KRW")
            logger.info(f"   Amount: {buy_amount:.6f} {ticker}")
            logger.info(f"   Confidence: {confidence:.2%}")
            
            # 4. TradeMemory에 진입 기록
            trade_id = self.memory.save_trade_entry(
                ticker=ticker,
                entry_price=current_price,
                features=features,
                model_confidence=confidence
            )
            
            # 5. 포지션 저장
            self.positions[ticker] = {
                "ticker": ticker,
                "trade_id": trade_id,
                "entry_price": current_price,
                "amount": buy_amount,
                "entry_time": datetime.now()
            }
            
            logger.info(f"✅ Position Opened: {ticker} (Trade ID={trade_id})")
        
        except Exception as e:
            logger.error(f"❌ Buy execution failed: {e}")
    
    def _check_exit_conditions(self, ticker: str):
        """
        매도 조건 체크 및 청산
        """
        if ticker not in self.positions:
            return
        
        position = self.positions[ticker]
        
        try:
            # 1. 현재 가격
            current_price = self.exchange.get_current_price(ticker)
            if not current_price:
                return
            
            entry_price = position['entry_price']
            profit_rate = (current_price - entry_price) / entry_price
            
            # 🔍 디버그: 모든 포지션 상태 출력
            logger.info(
                f"📊 [{ticker}] Price:{current_price:,.0f}, Entry:{entry_price:,.0f}, "
                f"Profit:{profit_rate*100:.2f}% (Target:>{self.target_profit*100:.1f}%)"
            )
            
            # 2. 현재 데이터 수집 (Emergency Check를 위해 미리 로드)
            df = self.exchange.get_ohlcv(ticker)
            should_exit = False
            exit_reason = ""
            
            # 🚨 0순위: Emergency Exit (Flash Crash)
            # 현재 캔들 시가 대비 3% 이상 급락 시 즉시 탈출
            if df is not None and not df.empty:
                last_candle = df.iloc[-1]
                candle_open = last_candle['open']
                if candle_open > 0:
                    candle_drop = (current_price - candle_open) / candle_open
                    if candle_drop < -0.03:  # -3% 급락
                        logger.warning(f"🚨 [{ticker}] Emergency Exit Triggered! Drop {candle_drop*100:.1f}%")
                        self._execute_sell(ticker, current_price, f"🚨 FLASH CRASH (Drop {candle_drop*100:.1f}%)")
                        return

            # 조건 1: 목표 수익률 (Emergency가 아닐 때만 체크)
            if profit_rate >= self.target_profit:
                should_exit = True
                exit_reason = f"Target Profit ({self.target_profit*100}%)"
            
            # 조건 2: 손절
            elif profit_rate <= -self.stop_loss:
                should_exit = True
                exit_reason = f"Stop Loss ({-self.stop_loss*100}%)"
            
            # 🆕 조건 2.5: Trailing Stop Loss
            elif self.trailing_stop_enabled and profit_rate >= self.trailing_activation:
                # Peak 가격 추적
                if 'peak_price' not in position:
                    position['peak_price'] = entry_price
                
                if current_price > position['peak_price']:
                    position['peak_price'] = current_price
                    logger.debug(f"🔼 [{ticker}] New Peak: {current_price:,.0f} (+{profit_rate*100:.2f}%)")
                
                # Peak 대비 하락률 체크
                trailing_stop_price = position['peak_price'] * (1 - self.trailing_distance)
                
                if current_price < trailing_stop_price:
                    peak_profit = (position['peak_price'] - entry_price) / entry_price
                    should_exit = True
                    exit_reason = f"Trailing Stop (Peak={position['peak_price']:,.0f}, +{peak_profit*100:.1f}%)"
                    logger.info(f"🔔 [{ticker}] Trailing Stop Triggered! Peak={position['peak_price']:,.0f}, Current={current_price:,.0f}")
            
            # 조건 3: 볼린저 밴드 상단 (타이밍 매도)
            elif df is not None and len(df) >= 20:
                features = FeatureEngineer.extract_features(df)
                if features.get('bb_position', 0) > 0.95:  # 상단 5% 이내
                    should_exit = True
                    exit_reason = "Bollinger Band Upper"
            
            # 3. 매도 실행
            if should_exit:
                self._execute_sell(ticker, current_price, exit_reason)
            else:
                logger.debug(
                    f"📊 [{ticker}] Position Monitoring - "
                    f"Profit: {profit_rate*100:.2f}%, "
                    f"Price: {current_price:,.0f}"
                )
        
        except Exception as e:
            logger.error(f"❌ Exit check failed: {e}")
    
    def _execute_sell(self, ticker: str, exit_price: float, reason: str):
        """
        매도 주문 실행
        """
        try:
            position = self.positions[ticker]
            
            # � 실시간 잔고 동기화 (수동 매수/매도 반영)
            holdings = self.exchange.get_holdings()
            actual_amount = None
            
            for holding in holdings:
                if holding['ticker'] == ticker:
                    actual_amount = holding['amount']
                    break
            
            if actual_amount is not None and actual_amount != position['amount']:
                logger.info(
                    f"🔄 Balance synced for {ticker}: "
                    f"{position['amount']:.4f} → {actual_amount:.4f} "
                    f"(Manual trade detected)"
                )
                position['amount'] = actual_amount
            elif actual_amount is None:
                logger.warning(f"⚠️ {ticker} not found in holdings. Position may have been sold manually.")
                del self.positions[ticker]
                return
            
            # �🛡️ 최소 주문 금액 검증 (업비트: 5,000원)
            # 업비트 시장가 매도는 "주문 수량 × 매수 1호가"로 계산됨
            bid_price = self.exchange.get_orderbook_bid_price(ticker)
            
            if not bid_price:
                logger.warning(f"⚠️ Failed to get bid price for {ticker}, using exit_price as fallback")
                bid_price = exit_price
            
            estimated_amount = position['amount'] * bid_price
            min_order_amount = 4990  # KRW (소수점 계산 오차 허용)
            
            if estimated_amount < min_order_amount:
                logger.warning(
                    f"⚠️ Cannot sell {ticker}: Order amount ({estimated_amount:,.0f} KRW) "
                    f"is below minimum ({min_order_amount:,.0f} KRW). "
                    f"Hold: {position['amount']:.4f} {ticker} @ bid {bid_price:,.0f} KRW"
                )
                logger.info(f"💡 Tip: Wait for price to rise or buy more to reach {min_order_amount} KRW")
                logger.info(f"📊 Current: {bid_price:.0f} KRW, Need: {min_order_amount / position['amount']:.0f} KRW/coin")
                return
            
            # 1. 주문 실행 (Market Order)
            logger.info(f"🚀 Executing REAL Sell Order for {ticker}...")
            logger.info(f"   Estimated amount: {estimated_amount:,.0f} KRW (bid: {bid_price:,.0f} × {position['amount']:.4f})")
            order = self.exchange.sell_market_order(ticker, position['amount'])
            
            if not order:
                logger.error("❌ Sell Order Failed")
                return
            
            # 데모 모드
            entry_price = position['entry_price']
            profit_rate = (exit_price - entry_price) / entry_price
            
            # logger.info("💸 [DEMO] Sell Order Executed")
            logger.info(f"   Ticker: {ticker}")
            logger.info(f"   Exit Price: {exit_price:,.0f} KRW")
            logger.info(f"   Profit: {profit_rate*100:+.2f}%")
            logger.info(f"   Reason: {reason}")
            
            # 2. TradeMemory 업데이트 (trade_id가 있는 경우에만)
            trade_id = position.get('trade_id')
            if trade_id is not None:
                self.memory.update_trade_exit(
                    trade_id=trade_id,
                    exit_price=exit_price
                )
            else:
                logger.info("ℹ️ Recovered position - no trade_id to update in DB")
            
            # 3. 세션 통계 업데이트
            self.session_trades += 1
            if profit_rate > 0:
                self.session_wins += 1
            
            # 4. trade_id 저장 (없을 수도 있음)
            closed_trade_id = position.get('trade_id', 'N/A')
            
            # 5. 🔥 익절/손절 모두 쿨다운 등록 (재매수 방지)
            self.sold_coins_cooldown[ticker] = {
                'exit_price': exit_price,
                'reason': reason  # 'Target Profit' or 'Stop Loss'
            }
            
            if profit_rate > 0:
                logger.info(
                    f"🚫 [{ticker}] Profit cooldown. "
                    f"Will rebuy if price drops below {exit_price * (1 - self.rebuy_threshold):,.0f} KRW"
                )
            else:
                logger.info(
                    f"🚫 [{ticker}] Loss cooldown. "
                    f"Will rebuy if price recovers above {exit_price * (1 + self.rebuy_threshold):,.0f} KRW"
                )
            
            # 티커 리스트에서 제거
            if ticker in self.tickers:
                self.tickers.remove(ticker)
                logger.info(f"➖ [{ticker}] Removed from active tickers")
            
            # 6. 포지션 클리어
            del self.positions[ticker]
            
            # 6. 🔥 학습 트리거 (N건 누적 시)
            stats = self.memory.get_statistics()
            if stats and stats.get('total_trades', 0) % self.retrain_threshold == 0 and stats.get('total_trades', 0) > 0:
                logger.info("🎓 Triggering Model Retraining...")
                self._retrain_model()
            
            logger.info(f"✅ Position Closed: Trade ID={closed_trade_id}")
        
        except Exception as e:
            logger.error(f"❌ Sell execution failed: {e}")
            import traceback
            logger.error(traceback.format_exc())
    
    def _retrain_model(self):
        """
        모델 재학습 실행
        
        축적된 실전 매매 데이터를 사용하여 모델을 업데이트합니다.
        이것이 'Self-Evolving' 메커니즘의 핵심입니다!
        """
        try:
            # 1. 학습 데이터 로드
            data = self.memory.get_learning_data(min_samples=30)
            if data is None:
                logger.warning("⚠️ Not enough data for retraining")
                return
            
            X, y = data
            
            # 2. 재학습
            old_accuracy = self.learner.metrics.get('accuracy', 0)
            self.learner.retrain_model(X, y)
            new_accuracy = self.learner.metrics.get('accuracy', 0)
            
            # 3. 결과 로깅
            improvement = new_accuracy - old_accuracy
            emoji = "📈" if improvement > 0 else "📉"
            
            logger.info("=" * 60)
            logger.info(f"🎓 MODEL RETRAINING COMPLETE")
            logger.info(f"   Old Accuracy: {old_accuracy:.2%}")
            logger.info(f"   New Accuracy: {new_accuracy:.2%}")
            logger.info(f"   {emoji} Improvement: {improvement:+.2%}")
            logger.info(f"   Training Samples: {len(X)}")
            logger.info("=" * 60)
        
        except Exception as e:
            logger.error(f"❌ Model retraining failed: {e}")
    
    def force_retrain(self):
        """수동 재학습 트리거 (UI에서 호출)"""
        logger.info("🔄 Manual Retraining Triggered")
        self._retrain_model()
    
    def update_coin_recommendations(self):
        """코인 추천 리스트 업데이트 (Sync - Legacy or Direct Call)"""
        self.recommended_coins = self.coin_selector.get_top_recommendations(top_n=5)
        return self.recommended_coins

    def update_recommendations_async(self):
        """코인 추천 리스트 업데이트 (Async - Non-blocking)"""
        if self.is_updating_recommendations:
            logger.warning("⚠️ Recommendation update already in progress")
            return
        
        self.is_updating_recommendations = True
        self.recommendation_thread = threading.Thread(target=self._recommendation_worker, daemon=True)
        self.recommendation_thread.start()
        logger.info("🔄 Started async recommendation update...")

    def _recommendation_worker(self):
        """백그라운드 추천 업데이트 워커"""
        try:
            recs = self.coin_selector.get_top_recommendations(top_n=5)
            self.recommended_coins = recs
            logger.info(f"✅ Async recommendation update complete: {len(recs)} coins")
        except Exception as e:
            logger.error(f"❌ Async recommendation update failed: {e}")
        finally:
            self.is_updating_recommendations = False
    
    def _auto_recommendation_timer(self):
        """
        🕐 1분마다 추천 업데이트 + 1위 종목 자동 추가
        """
        logger.info("🔄 Auto recommendation timer loop started")
        
        while self.is_running:
            try:
                logger.info("🔄 Auto-updating coin recommendations...")
                
                # 추천 업데이트
                recs = self.coin_selector.get_top_recommendations(top_n=5)
                self.recommended_coins = recs
                
                # 🏆 상위 코인 중 첫 번째 미보유 종목 자동 추가
                if recs:
                    added = False
                    for i, rec in enumerate(recs, 1):
                        ticker = rec['ticker']
                        score = rec['score']
                        conf = rec['confidence']
                        
                        # 이미 보유 중이거나 쿨다운 중이면 스킵
                        if ticker in self.tickers:
                            logger.debug(f"   {i}위 {ticker}: Already in tickers")
                            continue
                        
                        if ticker in self.positions:
                            logger.debug(f"   {i}위 {ticker}: Already holding position")
                            continue
                        
                        if ticker in self.sold_coins_cooldown:
                            logger.debug(f"   {i}위 {ticker}: In cooldown")
                            continue
                        
                        # 첫 번째 사용 가능한 코인 발견!
                        logger.info(f"🏆 Rank #{i} Recommendation: {ticker} (Score={score:.1f}, Confidence={conf:.1%})")
                        self.tickers.append(ticker)
                        logger.info(f"➕ Auto-added coin: {ticker}")
                        added = True
                        break
                    
                    if not added:
                        logger.info("📊 All top 5 coins are already owned or in cooldown. No new additions.")
                
                # 대기 (1초 단위로 체크하여 빠른 종료 지원)
                for _ in range(self.auto_recommendation_interval):
                    if not self.is_running:
                        break
                    time.sleep(1)
            except Exception as e:
                logger.error(f"❌ Auto recommendation timer error: {e}")
                time.sleep(60) # 에러 시 1분 대기
                
        logger.info("🔄 Auto recommendation timer stopped")
    
    def toggle_ticker(self, ticker: str):
        """티커 활성화/비활성화 토글"""
        if ticker in self.tickers:
            if len(self.tickers) > 1: # 최소 1개 유지를 원한다면
                self.tickers.remove(ticker)
                logger.info(f"➖ Ticker Removed: {ticker}")
            else:
                logger.warning("⚠️ Cannot remove last ticker")
        else:
            self.tickers.append(ticker)
            logger.info(f"➕ Ticker Added: {ticker}")
    
    def get_status(self) -> Dict:
        """
        봇 현재 상태 반환 (UI용)
        """
        stats = self.memory.get_statistics()
        
        return {
            "is_running": self.is_running,
            "tickers": self.tickers,
            "use_ai_selection": self.use_ai_selection,
            "recommended_coins": self.recommended_coins,
            "positions": self.positions,
            "model_accuracy": self.learner.metrics.get('accuracy', 0),
            "total_trades": stats['total_trades'],
            "win_rate": stats['win_rate'],
            "avg_profit_pct": stats['avg_profit_pct'],
            "session_trades": self.session_trades,
            "session_win_rate": (self.session_wins / self.session_trades * 100) if self.session_trades > 0 else 0,
            "last_trained": self.learner.metrics.get('last_trained'),
            "session_win_rate": (self.session_wins / self.session_trades * 100) if self.session_trades > 0 else 0,
            "last_trained": self.learner.metrics.get('last_trained'),
            "total_learning_samples": self.learner.metrics.get('total_samples', 0),
            "is_updating_recommendations": getattr(self, 'is_updating_recommendations', False)
        }


    
    def get_account_balance(self) -> Dict:
        """계좌 잔액 및 모든 보유 포지션 조회"""
        try:
            # 1. KRW 잔액 (Upbit/Bithumb 공통)
            # 임의의 티커로 호출하여 KRW 잔액 획득 (구조상 KRW는 공통)
            balance_data = self.exchange.get_balance(self.tickers[0] if self.tickers else "BTC")
            
            total_krw = balance_data.get("krw_balance", 0)
            total_value = total_krw
            holdings = []
            
            # 2. 선택된 코인들의 보유량 확인
            # (주의: 실제 거래소 잔액을 다 조회하려면 get_balances() API가 필요하지만, 
            #  여기서는 선택된 티커들에 대해서만 루프를 돕니다)
            target_tickers = set(self.tickers) | set(self.positions.keys())
            
            for ticker in target_tickers:
                b_data = self.exchange.get_balance(ticker)
                coin_amount = b_data.get("coin_balance", 0)
                
                if coin_amount > 0:
                    current_price = self.exchange.get_current_price(ticker) or 0
                    val = coin_amount * current_price
                    total_value += val
                    
                    holdings.append({
                        "ticker": ticker,
                        "amount": coin_amount,
                        "value": val
                    })
            
            return {
                "krw_balance": total_krw,
                "holdings": holdings,
                "total_value": total_value,
                "api_ok": True
            }
        except Exception as e:
            logger.warning(f"⚠️ Balance error: {e}")
            return {
                "krw_balance": 0,
                "holdings": [],
                "total_value": 0,
                "api_ok": False
            }

if __name__ == "__main__":
    # 테스트 실행
    print("=" * 60)
    print("Trading Bot Test")
    print("=" * 60)
    
    bot = TradingBot()
    print("\n✅ Bot Created")
    
    status = bot.get_status()
    print(f"\n📊 Status:")
    print(f"   Running: {status['is_running']}")
    print(f"   Model Accuracy: {status['model_accuracy']:.2%}")
    print(f"   Total Trades: {status['total_trades']}")
    
    print("\n" + "=" * 60)
    print("✅ Test Complete!")
    print("=" * 60)
    
