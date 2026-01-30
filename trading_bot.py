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
        
        # 🔄 Auto Recommendation Timer (5분마다 자동 업데이트 + 1위 종목 추가)
        self.auto_recommendation_enabled = True
        self.auto_recommendation_interval = 60  # 3분 (180초)
        self.auto_timer_thread = None
        
        # 🔄 봇 초기화 시 포지션 자동 복구 (START 버튼 전에도 보유 코인 감지)
        self._recover_positions()
        
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
                # 0. 🔄 포지션 동기화 (수동 매도 감지)
                self._sync_positions_with_exchange()
                
                # 1. 포지션 체크 (모든 보유 포지션)
                for ticker in list(self.positions.keys()):
                    self._check_exit_conditions(ticker)
                
                # 2. 진입 체크 (모든 선택된 티커)
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
        (재시작 시 포지션 유지용)
        """
        logger.info("🔄 Syncing positions from exchange...")
        try:
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

                logger.info(f"♻️ Recovered Position: {ticker} (Amt: {amount:.4f}, Avg: {entry_price:,.0f})")
                
                self.positions[ticker] = {
                    "ticker": ticker,
                    "trade_id": f"recovered_{ticker}_{int(time.time())}",
                    "entry_price": entry_price,
                    "amount": amount,
                    "entry_time": datetime.now() # 진입 시간은 현재로 리셋
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
            # 1. 현재 데이터 수집
            df = self.exchange.get_ohlcv(ticker)
            if df is None or len(df) < 30:
                return
            
            # 2. 특징 추출
            features = FeatureEngineer.extract_features(df)
            if not features:
                return
            
            # 3. AI 예측
            features_df = FeatureEngineer.features_to_dataframe(features)
            prediction, confidence = self.learner.predict(features_df)
            
            # 4. 매수 조건 평가
            rsi = features['rsi']
            bb_position = features['bb_position']
            
            # XGBoost가 상승 예측 AND 확신도 높음
            ai_signal = (prediction == 1) and (confidence > self.confidence_threshold)
            
            # Mean Reversion 시그널 (과매도 또는 볼린저 하단)
            oversold = (rsi < 30) or (bb_position < 0.2)
            
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
                            f"Price dropped {drop_pct:.1f}%: {current_price:,.0f} < {rebuy_price_threshold:,.0f}"
                        )
                
                # 손절 케이스: 가격 상승 시 재매수
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
                            f"Price recovered {rise_pct:.1f}%: {current_price:,.0f} > {rebuy_price_threshold:,.0f}"
                        )
                
                # 쿨다운 해제
                del self.sold_coins_cooldown[ticker]
                # 티커 리스트에 재추가
                if ticker not in self.tickers:
                    self.tickers.append(ticker)
            
            if ai_signal and oversold:
                self._execute_buy(ticker, features, confidence)
            else:
                logger.debug(
                    f"📊 [{ticker}] No Entry Signal - "
                    f"Pred:{prediction}, Conf:{confidence:.2%}, "
                    f"RSI:{rsi:.1f}, BB:{bb_position:.2f}"
                )
        
        except Exception as e:
            logger.error(f"❌ Entry check failed: {e}")
    
    def _execute_buy(self, ticker: str, features: Dict, confidence: float):
        """
        매수 주문 실행
        """
        try:
            # 🛡️ 최소 주문 금액 검증 (5,000원)
            if self.trade_amount < 5000:
                logger.warning(
                    f"⚠️ Cannot buy {ticker}: Trade amount ({self.trade_amount:,.0f} KRW) "
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
            buy_amount = self.trade_amount / current_price
            
            # 3. 주문 실행 (Market Order)
            logger.info(f"🚀 Executing REAL Buy Order for {ticker}...")
            order = self.exchange.buy_market_order(ticker, self.trade_amount, buy_amount)
            
            if not order:
                logger.error("❌ Order Failed")
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
            
            # 2. 현재 데이터 수집
            df = self.exchange.get_ohlcv(ticker)
            should_exit = False
            exit_reason = ""
            
            # 조건 1: 목표 수익률
            if profit_rate >= self.target_profit:
                should_exit = True
                exit_reason = f"Target Profit ({self.target_profit*100}%)"
            
            # 조건 2: 손절
            elif profit_rate <= -self.stop_loss:
                should_exit = True
                exit_reason = f"Stop Loss ({-self.stop_loss*100}%)"
            
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
        🕐 5분마다 추천 업데이트 + 1위 종목 자동 추가
        """
        logger.info("🔄 Auto recommendation timer loop started")
        
        while self.is_running:
            try:
                # 5분 대기
                time.sleep(self.auto_recommendation_interval)
                
                if not self.is_running:
                    break
                
                logger.info("🔄 Auto-updating coin recommendations...")
                
                # 추천 업데이트
                recs = self.coin_selector.get_top_recommendations(top_n=5)
                self.recommended_coins = recs
                
                if not recs:
                    logger.warning("⚠️ No recommendations available")
                    continue
                
                # 1위 종목 추출
                top_coin = recs[0]
                ticker = top_coin['ticker']
                score = top_coin['score']
                confidence = top_coin['confidence']
                
                logger.info(f"🏆 Top Recommendation: {ticker} (Score={score:.1f}, Confidence={confidence:.1f}%)")
                
                # 중복 체크: 이미 Active Tickers에 있으면 스킵
                if ticker in self.tickers:
                    logger.info(f"📊 {ticker} is already in active tickers. Skipping.")
                    continue
                
                # 중복 체크: 이미 포지션 보유 중이면 스킵
                if ticker in self.positions:
                    logger.info(f"📊 {ticker} position already exists. Skipping.")
                    continue
                
                # 🛡️ 최소 주문 금액 체크 (5,000원)
                if self.trade_amount < 5000:
                    logger.warning(
                        f"⚠️ Trade amount ({self.trade_amount:,.0f} KRW) is below minimum (5,000 KRW). "
                        f"Skipping auto-add for {ticker}."
                    )
                    continue
                
                # 자동 추가
                self.tickers.append(ticker)
                logger.info(f"✅ Auto-added {ticker} to active tickers! (Score={score:.1f}, Conf={confidence:.1f}%)")
                
            except Exception as e:
                logger.error(f"❌ Auto recommendation timer error: {e}")
                
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
    
