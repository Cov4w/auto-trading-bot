"""
AI-Powered Coin Selector
=========================
빗썸 상장 코인들을 실시간 분석하여 승률이 높은 상위 5개 코인을 추천합니다.

Selection Criteria:
- AI 모델 확신도 (Confidence Score)
- 기술적 지표 강도 (RSI, Bollinger Bands)
- 거래량 및 변동성
- 과거 승률 데이터
"""

# import pybithumb #  Removed dependency on direct pybithumb import
import pandas as pd
import numpy as np
from typing import List, Dict, Tuple, Optional
import logging
import time
from datetime import datetime

from data_manager import FeatureEngineer, ModelLearner, TradeMemory

logger = logging.getLogger(__name__)


class CoinSelector:
    """
    AI 기반 코인 선택 및 추천 시스템
    
    🔥 빗썸 전체 상장 코인을 실시간으로 분석하여 가장 수익성이 높을 것으로 
    예상되는 상위 5개 코인을 추천합니다.
    """
    
    def __init__(self, learner: ModelLearner, memory: TradeMemory, exchange):
        """
        Args:
            learner: 학습된 AI 모델
            memory: 매매 기록 저장소 (과거 승률 참조용)
            exchange: ExchangeManager 인스턴스
        """
        self.learner = learner
        self.memory = memory
        self.exchange = exchange
        
        # 🔥 전체 상장 코인 동적 로드
        self.candidate_coins = self._get_all_tickers()
        
        # 🔄 순차 검사를 위한 인덱스 (Pagination)
        self.scan_index = 0
        self.batch_size = 50  # 한 번에 검사할 코인 수
        
        logger.info("✅ CoinSelector initialized")
        logger.info(f"📊 Total coins available: {len(self.candidate_coins)}")
        logger.info(f"⚡ Scan Batch Size: {self.batch_size} (Full Scan in ~{len(self.candidate_coins)//self.batch_size * 3} mins)")
    
    def _get_all_tickers(self) -> List[str]:
        """
        전체 상장 코인 리스트 가져오기
        
        Returns:
            tickers: KRW 마켓 전체 티커 리스트
        """
        try:
            # ExchangeManager로 전체 티커 가져오기
            all_tickers = self.exchange.get_tickers()
            
            if not all_tickers:
                logger.warning("⚠️ Failed to get tickers from Bithumb API, using fallback list")
                # 폴백: 주요 코인만
                return ["BTC", "ETH", "XRP", "SOL", "DOGE", "ADA", "AVAX", "MATIC", "DOT", "LINK"]
            
            # KRW 마켓만 필터링 (payment_currency가 'KRW'인 것들)
            krw_tickers = [ticker for ticker in all_tickers if ticker != "BTC"]  # BTC는 기본 포함
            
            # BTC를 맨 앞에 배치
            if "BTC" in all_tickers:
                krw_tickers.insert(0, "BTC")
            
            # 🔥 전체 리스트 반환 (나중에 나눠서 검사)
            logger.info(f"✅ Loaded {len(krw_tickers)} coins from {self.exchange.exchange_name}")
            return krw_tickers
        
        except Exception as e:
            logger.error(f"❌ Error fetching tickers: {e}")
            # 폴백: 주요 20개 코인
            return [
                "BTC", "ETH", "XRP", "SOL", "DOGE",
                "ADA", "AVAX", "MATIC", "DOT", "LINK",
                "UNI", "ATOM", "NEAR", "APT", "ARB",
                "OP", "SUI", "STX", "INJ", "TIA"
            ]
    
    def refresh_coin_list(self):
        """
        코인 리스트 수동 갱신
        
        빗썸에 새로운 코인이 상장되었을 때 호출
        """
        logger.info("🔄 Refreshing coin list...")
        self.candidate_coins = self._get_all_tickers()
        logger.info(f"✅ Updated to {len(self.candidate_coins)} coins")
    
    def analyze_coin(self, ticker: str) -> Optional[Dict]:
        """
        단일 코인 분석
        
        Args:
            ticker: 코인 티커 (예: "BTC")
        
        Returns:
            analysis: 분석 결과 딕셔너리
                - ticker: 티커
                - confidence: AI 확신도
                - features: 기술적 지표
                - score: 종합 점수
                - recommendation: 매수 추천 여부
        """
        try:
            # 1. OHLCV 데이터 수집 (최근 1시간, 1분봉)
            df = self.exchange.get_ohlcv(ticker)
            
            if df is None or len(df) < 30:
                logger.debug(f"⚠️ {ticker}: Insufficient data")
                return None
            
            # 2. 특징 추출
            features = FeatureEngineer.extract_features(df)
            if not features:
                return None
            
            # 3. AI 예측
            features_df = FeatureEngineer.features_to_dataframe(features)
            prediction, confidence = self.learner.predict(features_df)
            
            # 4. 종합 점수 계산
            score = self._calculate_score(features, confidence, prediction, ticker)
            
            # 5. 매수 추천 여부
            recommendation = self._should_recommend(features, confidence, prediction, score)
            
            # 6. 현재 가격
            current_price = self.exchange.get_current_price(ticker)
            
            # 🛡️ 최소 가격 필터 (저가 코인 제외)
            MIN_PRICE = 100  # 100원 미만 코인 제외
            if current_price and current_price < MIN_PRICE:
                logger.debug(f"⚠️ {ticker}: Price too low ({current_price} KRW < {MIN_PRICE}), skipping")
                return None
            
            return {
                "ticker": ticker,
                "confidence": confidence,
                "prediction": prediction,
                "features": features,
                "score": score,
                "recommendation": recommendation,
                "current_price": current_price,
                "timestamp": datetime.now()
            }
        
        except Exception as e:
            logger.error(f"❌ Failed to analyze {ticker}: {e}")
            return None
    
    def _calculate_score(self, features: Dict, confidence: float, 
                        prediction: int, ticker: str) -> float:
        """
        종합 점수 계산 (0 ~ 100)
        
        점수 구성:
        - AI 확신도: 40%
        - 기술적 지표 강도: 30%
        - 과거 승률: 20%
        - 거래량/변동성: 10%
        """
        score = 0.0
        
        # 1. AI 확신도 (40점 만점)
        ai_score = confidence * 40
        score += ai_score
        
        # 2. 기술적 지표 강도 (30점 만점)
        technical_score = 0
        
        # RSI 과매도 구간 (0~30)
        rsi = features.get('rsi', 50)
        if rsi < 30:
            technical_score += 10  # 강한 과매도
        elif rsi < 40:
            technical_score += 5   # 과매도
        
        # Bollinger Band 하단 근접
        bb_position = features.get('bb_position', 0.5)
        if bb_position < 0.2:
            technical_score += 10  # 하단 20% 이내
        elif bb_position < 0.3:
            technical_score += 5   # 하단 30% 이내
        
        # MACD 상승 전환
        macd = features.get('macd', 0)
        macd_signal = features.get('macd_signal', 0)
        if macd > macd_signal:
            technical_score += 10  # 골든 크로스
        
        score += technical_score
        
        # 3. 과거 승률 (20점 만점)
        historical_score = self._get_historical_score(ticker)
        score += historical_score
        
        # 4. 거래량/변동성 (10점 만점)
        volume_ratio = features.get('volume_ratio', 1.0)
        atr = features.get('atr', 0)
        
        volume_score = min(volume_ratio * 5, 5)  # 거래량 비율 (최대 5점)
        volatility_score = min(atr / 100000 * 5, 5)  # 변동성 (최대 5점)
        
        score += volume_score + volatility_score
        
        return min(score, 100.0)  # 최대 100점
    
    def _get_historical_score(self, ticker: str) -> float:
        """
        특정 티커의 과거 승률 기반 점수
        
        Returns:
            score: 0 ~ 20점
        """
        try:
            import sqlite3
            conn = sqlite3.connect(self.memory.db_path)
            
            result = conn.execute("""
                SELECT 
                    COUNT(*) as total,
                    SUM(CASE WHEN is_profitable = 1 THEN 1 ELSE 0 END) as wins
                FROM trades
                WHERE ticker = ? AND status = 'closed'
            """, (ticker,)).fetchone()
            
            conn.close()
            
            total, wins = result
            if total == 0:
                return 10.0  # 중립 점수 (데이터 없음)
            
            win_rate = wins / total
            return win_rate * 20  # 승률 100% = 20점
        
        except Exception as e:
            logger.debug(f"No historical data for {ticker}")
            return 10.0
    
    def _should_recommend(self, features: Dict, confidence: float, 
                         prediction: int, score: float) -> bool:
        """
        매수 추천 여부 판단
        
        Criteria:
        - AI 상승 예측 (prediction == 1)
        - 확신도 > 0.6
        - 종합 점수 > 60
        - (RSI < 40 OR BB 하단 30% 이내)
        """
        if prediction != 1:
            return False
        
        if confidence < 0.6:
            return False
        
        if score < 60:
            return False
        
        # Mean Reversion 조건
        rsi = features.get('rsi', 50)
        bb_position = features.get('bb_position', 0.5)
        
        if rsi > 40 and bb_position > 0.3:
            return False  # 과매도 아님
        
        return True
    
    def get_top_recommendations(self, top_n: int = 5) -> List[Dict]:
        """
        상위 N개 추천 코인 반환 (순차적 배치 스캔)
        """
        total_coins = len(self.candidate_coins)
        if total_coins == 0:
            return []
            
        # 🔄 현재 배치 범위 계산
        start_idx = self.scan_index
        end_idx = min(start_idx + self.batch_size, total_coins)
        
        # 검사 대상 슬라이싱
        target_tickers = self.candidate_coins[start_idx:end_idx]
        
        logger.info(
            f"🔍 Scanning Batch: {start_idx+1}~{end_idx} / {total_coins} coins "
            f"({len(target_tickers)} items)"
        )
        
        # 모델이 없으면 경고
        if self.learner.model is None:
            logger.warning("⚠️ Model not trained yet. Using technical analysis only.")
        
        # 배치 내 코인 분석
        analyses = []
        analyzed_count = 0
        for ticker in target_tickers:
            analysis = self.analyze_coin(ticker)
            time.sleep(0.15) # 💤 API Rate Limit 방지 (0.15초 대기)
            if analysis:
                analyses.append(analysis)
                analyzed_count += 1
        
        logger.info(f"📊 Successfully analyzed {analyzed_count}/{len(target_tickers)} coins (Batch)")
        
        # 🔄 다음 배치를 위해 인덱스 업데이트
        self.scan_index += self.batch_size
        if self.scan_index >= total_coins:
            self.scan_index = 0
            logger.info("🔄 Completed full market scan. Resetting to start.")
        else:
            logger.info(f"🔜 Next Scan: {self.scan_index+1}~{min(self.scan_index+self.batch_size, total_coins)}")
        
        if not analyses:
            logger.warning("⚠️ No valid coin analysis results")
            return []
        
        # 점수 기준 정렬
        analyses.sort(key=lambda x: x['score'], reverse=True)
        
        # 상위 N개 선택
        top_recommendations = analyses[:top_n]
        
        # 로깅
        logger.info(f"✅ Top {top_n} Recommendations:")
        for i, rec in enumerate(top_recommendations, 1):
            logger.info(
                f"   {i}. {rec['ticker']}: "
                f"Score={rec['score']:.1f}, "
                f"Confidence={rec['confidence']:.2%}, "
                f"Recommend={'✅' if rec['recommendation'] else '⚠️'}"
            )
        
        return top_recommendations
    
    def get_best_coin(self) -> Optional[str]:
        """
        현재 가장 추천되는 단일 코인 반환
        
        Returns:
            ticker: 최고 점수 코인 티커 (없으면 None)
        """
        recommendations = self.get_top_recommendations(top_n=1)
        
        if recommendations and recommendations[0]['recommendation']:
            return recommendations[0]['ticker']
        
        return None


if __name__ == "__main__":
    # 테스트 코드
    print("=" * 60)
    print("Coin Selector Test")
    print("=" * 60)
    
    memory = TradeMemory()
    learner = ModelLearner()
    
    class MockExchange:
        def __init__(self):
            self.exchange_name = "test_exchange"
        def get_tickers(self):
            return ["BTC", "ETH"]
        def get_ohlcv(self, ticker):
            # Return dummy DataFrame
            import pandas as pd
            import numpy as np
            dates = pd.date_range(end=pd.Timestamp.now(), periods=50, freq='D')
            data = pd.DataFrame(index=dates, columns=['open', 'high', 'low', 'close', 'volume'])
            data[:] = 100
            return data
        def get_current_price(self, ticker):
            return 1000

    exchange = MockExchange()
    selector = CoinSelector(learner, memory, exchange)
    print("\n✅ CoinSelector created")
    
    # 단일 코인 분석
    print("\n📊 Analyzing BTC...")
    btc_analysis = selector.analyze_coin("BTC")
    if btc_analysis:
        print(f"   Score: {btc_analysis['score']:.1f}/100")
        print(f"   Confidence: {btc_analysis['confidence']:.2%}")
        print(f"   Recommend: {'✅ YES' if btc_analysis['recommendation'] else '❌ NO'}")
    
    print("\n" + "=" * 60)
    print("✅ Test Complete!")
    print("=" * 60)
