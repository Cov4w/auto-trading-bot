"""
Backtesting Engine
==================
과거 데이터로 트레이딩 전략 시뮬레이션 및 성과 평가

Features:
- 업비트 API 기반 과거 데이터 수집
- AI 모델 기반 매매 시뮬레이션
- 성과 지표 계산 (승률, 손익비, MDD, Sharpe Ratio)
- 백그라운드 실행 지원
- 완료 시 자동 모델 재학습
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, Optional, List
import logging
import threading
import time
import pyupbit

logger = logging.getLogger(__name__)


class Backtester:
    """
    백테스팅 엔진

    과거 데이터로 현재 AI 전략의 성과를 시뮬레이션하고,
    결과가 좋으면 자동으로 모델을 재학습시킵니다.
    """

    def __init__(self, trading_bot, tickers: List[str] = None, days: int = 200):
        """
        Args:
            trading_bot: TradingBot 인스턴스
            tickers: 백테스팅할 코인 리스트 (None이면 실제 거래 내역에서 자동 선택)
            days: 테스트할 기간 (일)
        """
        self.bot = trading_bot
        self.tickers = tickers or self._get_traded_coins()
        self.days = days

        # 시뮬레이션 상태
        self.initial_capital = 1_000_000
        self.capital = self.initial_capital
        self.position = None
        self.trades = []
        self.capital_history = [self.initial_capital]

        # 백테스팅 상태
        self.is_running = False
        self.thread = None
        self.progress = 0
        self.status = "idle"  # idle, running, completed, failed
        self.results = None
        self.current_ticker = None  # 현재 처리 중인 코인

    def _get_traded_coins(self) -> List[str]:
        """
        실제 거래 내역에서 코인 목록 가져오기 (거래량 상위 10개)
        """
        import sqlite3

        try:
            with sqlite3.connect(self.bot.memory.db_path) as conn:
                cursor = conn.execute("""
                    SELECT ticker, COUNT(*) as count
                    FROM trades
                    WHERE status = 'closed'
                    GROUP BY ticker
                    ORDER BY count DESC
                    LIMIT 10
                """)
                tickers = [row[0] for row in cursor.fetchall()]

            if not tickers:
                # 거래 내역이 없으면 기본 코인
                logger.warning("⚠️ No trade history found, using default coins")
                return ["BTC", "ETH", "XRP"]

            logger.info(f"📊 Selected {len(tickers)} coins from trade history: {', '.join(tickers)}")
            return tickers

        except Exception as e:
            logger.error(f"❌ Failed to get traded coins: {e}")
            return ["BTC", "ETH", "XRP"]

    def fetch_historical_data(self, ticker: str, days: int = 200) -> Optional[pd.DataFrame]:
        """
        업비트에서 과거 데이터 가져오기

        Args:
            ticker: 티커 (예: "BTC")
            days: 가져올 일수 (최대 200일)

        Returns:
            OHLCV 데이터프레임
        """
        try:
            logger.info(f"📊 Fetching {days} days of historical data for {ticker}...")

            # 업비트 API 호출 (최대 200일)
            df = pyupbit.get_ohlcv(f"KRW-{ticker}", interval="day", count=min(days, 200))

            if df is None or len(df) == 0:
                logger.error(f"❌ No data retrieved for {ticker}")
                return None

            logger.info(f"✅ Retrieved {len(df)} days of data ({df.index[0]} ~ {df.index[-1]})")
            return df

        except Exception as e:
            logger.error(f"❌ Failed to fetch historical data: {e}")
            return None

    def simulate_trade(self, df: pd.DataFrame, ticker: str = None):
        """
        과거 데이터로 매매 시뮬레이션

        Args:
            df: OHLCV 데이터프레임
            ticker: 현재 백테스팅 중인 코인 (None이면 self.current_ticker 사용)
        """
        from .data_manager import FeatureEngineer

        # 현재 코인 티커
        if ticker is None:
            ticker = self.current_ticker or (self.tickers[0] if self.tickers else "BTC")

        logger.info(f"   💰 Current Capital: {self.capital:,.0f} KRW")
        logger.info(f"   📅 Period: {df.index[0].strftime('%Y-%m-%d')} ~ {df.index[-1].strftime('%Y-%m-%d')}")

        feature_engineer = FeatureEngineer()

        for i in range(len(df)):
            current_date = df.index[i]
            current_price = df.iloc[i]['close']

            # 최소 데이터 필요 (기술적 지표 계산)
            if i < 30:
                continue

            # 특징 추출
            try:
                features = feature_engineer.extract_features(df.iloc[:i+1], ticker)
                if features is None:
                    continue
            except Exception as e:
                logger.debug(f"Feature extraction failed at {current_date}: {e}")
                continue

            # AI 예측
            prediction, confidence = self.bot.learner.predict(features)

            # 매수 조건: prediction=2 (좋은수익) AND confidence > 임계값 AND 포지션 없음
            if prediction == 2 and confidence >= self.bot.confidence_threshold and self.position is None:
                # 매수 실행
                trade_amount = min(self.bot.trade_amount, self.capital * 0.1)

                if trade_amount >= 6000:  # 최소 주문 금액
                    amount = trade_amount / current_price

                    self.position = {
                        'entry_date': current_date,
                        'entry_price': current_price,
                        'amount': amount,
                        'trade_amount': trade_amount,
                        'confidence': confidence
                    }

                    # 🔥 중요: 매수 시 자본 감소
                    self.capital -= trade_amount
                    self.capital_history.append(self.capital)

                    logger.info(f"[매수] {current_date.strftime('%Y-%m-%d')} | {current_price:,.0f}원 | 확신도: {confidence:.2%} | 잔액: {self.capital:,.0f}원")

            # 매도 조건: 포지션 있음 AND (익절 OR 손절)
            elif self.position is not None:
                entry_price = self.position['entry_price']
                profit_rate = (current_price - entry_price) / entry_price

                should_sell = False
                sell_reason = ""

                # 익절
                if profit_rate >= self.bot.target_profit:
                    should_sell = True
                    sell_reason = f"Target Profit ({self.bot.target_profit*100:.1f}%)"

                # 손절
                elif profit_rate <= -self.bot.stop_loss:
                    should_sell = True
                    sell_reason = f"Stop Loss ({-self.bot.stop_loss*100:.1f}%)"

                if should_sell:
                    # 매도 실행
                    exit_amount = self.position['amount'] * current_price
                    profit = exit_amount - self.position['trade_amount']

                    # 🔥 중요: 매도 시 전체 금액 회수 (원금 + 수익/손실)
                    self.capital += exit_amount
                    self.capital_history.append(self.capital)

                    # 거래 기록
                    self.trades.append({
                        'entry_date': self.position['entry_date'],
                        'exit_date': current_date,
                        'entry_price': entry_price,
                        'exit_price': current_price,
                        'profit_rate': profit_rate,
                        'profit': profit,
                        'confidence': self.position['confidence'],
                        'reason': sell_reason,
                        'ticker': ticker  # 🆕 어떤 코인인지 기록
                    })

                    logger.info(f"[매도] {current_date.strftime('%Y-%m-%d')} | {current_price:,.0f}원 | 수익률: {profit_rate*100:+.2f}% | {sell_reason} | 잔액: {self.capital:,.0f}원")

                    self.position = None

        logger.info("=" * 60)
        logger.info(f"✅ Simulation Complete - Total Trades: {len(self.trades)}")

    def analyze_results(self) -> Dict:
        """
        백테스팅 결과 분석

        Returns:
            성과 지표 딕셔너리
        """
        if len(self.trades) == 0:
            return {
                'total_trades': 0,
                'win_rate': 0,
                'total_return': 0,
                'final_capital': self.capital,
                'avg_profit': 0,
                'avg_loss': 0,
                'profit_loss_ratio': 0,
                'max_drawdown': 0,
                'sharpe_ratio': 0,
                'wins': 0,
                'losses': 0,
                'tested_coins': self.tickers,
                'coin_count': len(self.tickers),
                'message': '거래 없음 (매수 신호가 발생하지 않음)'
            }

        # 승률
        wins = sum(1 for t in self.trades if t['profit_rate'] > 0)
        win_rate = wins / len(self.trades)

        # 수익률
        total_return = (self.capital - self.initial_capital) / self.initial_capital

        # 평균 수익/손실
        profitable_trades = [t for t in self.trades if t['profit_rate'] > 0]
        losing_trades = [t for t in self.trades if t['profit_rate'] < 0]

        avg_profit = np.mean([t['profit_rate'] for t in profitable_trades]) if profitable_trades else 0
        avg_loss = np.mean([t['profit_rate'] for t in losing_trades]) if losing_trades else 0

        # 손익비
        profit_loss_ratio = abs(avg_profit / avg_loss) if avg_loss != 0 else 0

        # MDD (Maximum Drawdown)
        peak = self.initial_capital
        max_drawdown = 0

        for capital in self.capital_history:
            if capital > peak:
                peak = capital
            drawdown = (peak - capital) / peak
            if drawdown > max_drawdown:
                max_drawdown = drawdown

        # Sharpe Ratio (간단 버전)
        returns = [t['profit_rate'] for t in self.trades]
        sharpe_ratio = (np.mean(returns) - 0) / np.std(returns) if len(returns) > 1 else 0

        results = {
            'total_trades': len(self.trades),
            'win_rate': win_rate,
            'total_return': total_return,
            'final_capital': self.capital,
            'avg_profit': avg_profit,
            'avg_loss': avg_loss,
            'profit_loss_ratio': profit_loss_ratio,
            'max_drawdown': max_drawdown,
            'sharpe_ratio': sharpe_ratio,
            'wins': wins,
            'losses': len(self.trades) - wins
        }

        return results

    def print_results(self, results: Dict):
        """결과 출력"""
        logger.info("=" * 60)
        logger.info("📊 BACKTESTING RESULTS")
        logger.info("=" * 60)
        logger.info(f"총 거래 수: {results['total_trades']}건")
        logger.info(f"승: {results['wins']}건 / 패: {results['losses']}건")
        logger.info(f"승률: {results['win_rate']*100:.2f}%")
        logger.info(f"총 수익률: {results['total_return']*100:+.2f}%")
        logger.info(f"최종 자본: {results['final_capital']:,.0f}원 (초기: {self.initial_capital:,.0f}원)")
        logger.info(f"평균 수익: {results['avg_profit']*100:+.2f}%")
        logger.info(f"평균 손실: {results['avg_loss']*100:.2f}%")
        logger.info(f"손익비: {results['profit_loss_ratio']:.2f}")
        logger.info(f"최대 낙폭(MDD): {results['max_drawdown']*100:.2f}%")
        logger.info(f"Sharpe Ratio: {results['sharpe_ratio']:.2f}")
        logger.info("=" * 60)

        # 평가
        if results['win_rate'] >= 0.45 and results['profit_loss_ratio'] >= 1.5:
            logger.info("✅ 전략 검증 성공! 실전 투입 가능 수준입니다.")
            return True
        else:
            logger.warning("⚠️ 전략 개선 필요:")
            if results['win_rate'] < 0.45:
                logger.warning(f"   - 승률 {results['win_rate']*100:.1f}% < 목표 45%")
            if results['profit_loss_ratio'] < 1.5:
                logger.warning(f"   - 손익비 {results['profit_loss_ratio']:.2f} < 목표 1.5")
            return False

    def run(self):
        """백테스팅 실행 (동기) - 멀티 코인 지원"""
        try:
            self.status = "running"
            self.progress = 0

            logger.info("=" * 60)
            logger.info(f"🚀 Starting Multi-Coin Backtesting")
            logger.info(f"   Coins: {', '.join(self.tickers)} ({len(self.tickers)}개)")
            logger.info(f"   Period: {self.days} days")
            logger.info("=" * 60)

            # 각 코인마다 백테스팅 실행
            for idx, ticker in enumerate(self.tickers):
                self.current_ticker = ticker
                logger.info(f"\n[{idx+1}/{len(self.tickers)}] Testing {ticker}...")

                # 1. 데이터 수집
                df = self.fetch_historical_data(ticker, self.days)

                if df is None:
                    logger.warning(f"   ⚠️ Skipping {ticker}: No data available")
                    continue

                # 2. 시뮬레이션 (이 코인에 대해)
                self.simulate_trade(df, ticker)

                # 진행률 업데이트
                self.progress = int((idx + 1) / len(self.tickers) * 100)

            # 3. 전체 결과 분석
            logger.info("\n📊 Analyzing Overall Results...")
            results = self.analyze_results()
            self.results = results

            # 코인별 통계 추가
            results['tested_coins'] = self.tickers
            results['coin_count'] = len(self.tickers)

            # 4. 결과 출력
            is_good = self.print_results(results)

            # 5. 성과가 좋으면 모델 재학습
            if is_good and results['total_trades'] >= 30:
                logger.info("🎓 Strategy validated! Triggering model retraining...")
                self._retrain_with_backtest_data()

            self.status = "completed"
            return results

        except Exception as e:
            logger.error(f"❌ Backtesting failed: {e}")
            import traceback
            logger.error(traceback.format_exc())
            self.status = "failed"
            return None

    def run_async(self):
        """백테스팅 비동기 실행 (백그라운드)"""
        if self.is_running:
            logger.warning("⚠️ Backtesting is already running")
            return False

        self.is_running = True
        self.thread = threading.Thread(target=self._run_background, daemon=True)
        self.thread.start()

        logger.info("🚀 Backtesting started in background")
        return True

    def _run_background(self):
        """백그라운드 실행 래퍼"""
        try:
            self.run()
        finally:
            self.is_running = False

    def _retrain_with_backtest_data(self):
        """
        백테스팅 결과를 학습 데이터에 추가하고 모델 재학습

        주의: 실제로는 백테스팅 결과를 DB에 저장하지 않고,
        현재 모델이 이미 실전 데이터로 학습되어 있으므로
        여기서는 단순히 재학습만 트리거합니다.
        """
        logger.info("🎓 Retraining model based on backtesting validation...")
        self.bot._retrain_model()

    def get_status(self) -> Dict:
        """백테스팅 상태 조회"""
        return {
            'is_running': self.is_running,
            'status': self.status,
            'progress': self.progress,
            'results': self.results
        }
