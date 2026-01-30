"""
Data & Model Manager
=====================
학습 데이터 저장소(TradeMemory)와 모델 관리(ModelLearner) 클래스를 제공합니다.
이는 'Self-Evolving Trading System'의 핵심 두뇌 역할을 수행합니다.

Core Concepts:
- TradeMemory: 매매 결과를 영구 저장 (SQLite)
- ModelLearner: XGBoost 모델의 학습/재학습/예측 관리
- Feature Engineering: 기술적 지표를 기반으로 한 특징 추출
"""

import sqlite3
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from pathlib import Path
import joblib
from typing import Dict, Tuple, Optional
import logging

# Machine Learning
import xgboost as xgb
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, classification_report

# Technical Indicators
from ta.trend import SMAIndicator, EMAIndicator, MACD
from ta.momentum import RSIIndicator, StochasticOscillator
from ta.volatility import BollingerBands, AverageTrueRange

# Setup Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class TradeMemory:
    """
    매매 기록 및 학습 데이터 영구 저장소
    
    매매가 완료될 때마다 진입 시점의 특징(Features)과 결과(Profit/Loss)를
    SQLite DB에 저장하여 모델이 실전 데이터로 학습할 수 있도록 합니다.
    """
    
    def __init__(self, db_path: str = "data/trade_memory.db"):
        self.db_path = db_path
        # 디렉토리 생성
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._init_database()
        logger.info(f"✅ TradeMemory initialized at {db_path}")
    
    def _init_database(self):
        """데이터베이스 테이블 초기화"""
        with sqlite3.connect(self.db_path) as conn:
            # 매매 기록 테이블
            conn.execute("""
                CREATE TABLE IF NOT EXISTS trades (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    ticker TEXT NOT NULL,
                    entry_price REAL NOT NULL,
                    exit_price REAL,
                    profit_rate REAL,
                    is_profitable INTEGER,  -- 1: 수익, 0: 손실
                    
                    -- Technical Features (진입 시점)
                    rsi REAL,
                    macd REAL,
                    macd_signal REAL,
                    bb_position REAL,  -- Bollinger Band 상대 위치
                    volume_ratio REAL,
                    price_change_5m REAL,
                    price_change_15m REAL,
                    ema_9 REAL,
                    ema_21 REAL,
                    atr REAL,
                    
                    -- Model Prediction
                    model_confidence REAL,
                    
                    -- Status
                    status TEXT DEFAULT 'closed'  -- open, closed
                )
            """)
            
            # 모델 성능 추적 테이블
            conn.execute("""
                CREATE TABLE IF NOT EXISTS model_performance (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    total_trades INTEGER,
                    win_rate REAL,
                    accuracy REAL,
                    avg_profit REAL,
                    model_version TEXT
                )
            """)
            conn.commit()
    
    def save_trade_entry(self, ticker: str, entry_price: float, 
                        features: Dict, model_confidence: float) -> int:
        """
        매수 진입 시점 데이터 저장
        
        Args:
            ticker: 거래 티커
            entry_price: 진입 가격
            features: 기술적 지표 특징들
            model_confidence: 모델 확신도
        
        Returns:
            trade_id: 저장된 거래 ID
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                INSERT INTO trades (
                    timestamp, ticker, entry_price, model_confidence,
                    rsi, macd, macd_signal, bb_position, volume_ratio,
                    price_change_5m, price_change_15m, ema_9, ema_21, atr,
                    status
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'open')
            """, (
                datetime.now().isoformat(),
                ticker,
                entry_price,
                model_confidence,
                features.get('rsi', 0),
                features.get('macd', 0),
                features.get('macd_signal', 0),
                features.get('bb_position', 0),
                features.get('volume_ratio', 0),
                features.get('price_change_5m', 0),
                features.get('price_change_15m', 0),
                features.get('ema_9', 0),
                features.get('ema_21', 0),
                features.get('atr', 0)
            ))
            conn.commit()
            trade_id = cursor.lastrowid
            logger.info(f"💾 Trade Entry Saved: ID={trade_id}, Price={entry_price:,.0f}")
            return trade_id
    
    def update_trade_exit(self, trade_id: int, exit_price: float):
        """
        매도 완료 시점 데이터 업데이트 및 결과 기록
        
        이 함수 호출 후 모델 재학습이 트리거될 수 있습니다.
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                # 진입 가격 조회
                result = conn.execute(
                    "SELECT entry_price FROM trades WHERE id = ?", 
                    (trade_id,)
                ).fetchone()
                
                # 🛡️ Safety: DB에 해당 거래 기록이 없을 경우 (수동 지갑 추가 등)
                if not result:
                    logger.warning(f"⚠️ Trade ID={trade_id} not found in DB. Skipping update.")
                    return
                
                entry_price = result[0]
                
                # 수익률 계산
                profit_rate = (exit_price - entry_price) / entry_price
                
                # 🔥 수수료(약 0.1%) 고려하여 실질 수익일 때만 승리로 인정
                # 업비트: 0.05% + 0.05% = 0.1%
                is_profitable = 1 if profit_rate > 0.001 else 0
                
                # 업데이트
                conn.execute("""
                    UPDATE trades 
                    SET exit_price = ?,
                        profit_rate = ?,
                        is_profitable = ?,
                        status = 'closed'
                    WHERE id = ?
                """, (exit_price, profit_rate, is_profitable, trade_id))
                conn.commit()
                
                emoji = "📈" if is_profitable else "📉"
                logger.info(
                    f"{emoji} Trade Closed: ID={trade_id}, "
                    f"Profit={profit_rate*100:.2f}%"
                )
        except Exception as e:
            logger.error(f"❌ Failed to update trade exit: {e}")
    
    def get_learning_data(self, min_samples: int = 30) -> Optional[Tuple[pd.DataFrame, pd.Series]]:
        """
        모델 학습용 데이터 반환
        
        Returns:
            (X, y): 특징 데이터프레임과 라벨 시리즈
                    데이터가 부족하면 None 반환
        """
        with sqlite3.connect(self.db_path) as conn:
            df = pd.read_sql_query("""
                SELECT 
                    rsi, macd, macd_signal, bb_position, volume_ratio,
                    price_change_5m, price_change_15m, ema_9, ema_21, atr,
                    is_profitable
                FROM trades
                WHERE status = 'closed' AND is_profitable IS NOT NULL
            """, conn)
        
        if len(df) < min_samples:
            logger.warning(f"⚠️ Insufficient data: {len(df)}/{min_samples}")
            return None
        
        X = df.drop('is_profitable', axis=1)
        y = df['is_profitable']
        
        logger.info(f"📊 Learning Data Loaded: {len(df)} samples")
        return X, y
    
    def get_statistics(self) -> Dict:
        """현재 매매 통계 반환"""
        with sqlite3.connect(self.db_path) as conn:
            stats = conn.execute("""
                SELECT 
                    COUNT(*) as total_trades,
                    SUM(CASE WHEN is_profitable = 1 THEN 1 ELSE 0 END) as wins,
                    AVG(profit_rate) as avg_profit,
                    MAX(profit_rate) as max_profit,
                    MIN(profit_rate) as max_loss
                FROM trades
                WHERE status = 'closed'
            """).fetchone()
        
        total, wins, avg_profit, max_profit, max_loss = stats
        win_rate = (wins / total * 100) if total > 0 else 0
        
        return {
            "total_trades": total or 0,
            "win_rate": win_rate,
            "avg_profit_pct": (avg_profit or 0) * 100,
            "max_profit_pct": (max_profit or 0) * 100,
            "max_loss_pct": (max_loss or 0) * 100
        }


class ModelLearner:
    """
    XGBoost 모델 학습 및 관리
    
    Features:
    - 초기 학습 (Cold Start)
    - 점진적 재학습 (Incremental Update)
    - 모델 영구 저장/로드
    - 예측 및 확신도 제공
    """
    
    def __init__(self, model_path: str = "models/xgb_model.pkl"):
        self.model_path = model_path
        self.model: Optional[xgb.XGBClassifier] = None
        self.metrics = {
            "accuracy": 0.0,
            "last_trained": None,
            "total_samples": 0
        }
        
        # 디렉토리 생성
        Path(model_path).parent.mkdir(parents=True, exist_ok=True)
        
        # 기존 모델 로드 시도
        self.load_model()
        logger.info("✅ ModelLearner initialized")
    
    def train_initial_model(self, X: pd.DataFrame, y: pd.Series):
        """
        초기 모델 학습 (Cold Start)
        
        과거 30일 데이터 또는 최소 30개 샘플로 시작
        """
        logger.info("🎓 Starting Initial Model Training...")
        
        # Train-Test Split
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42, stratify=y
        )
        
        # XGBoost Model with M3 Optimization
        self.model = xgb.XGBClassifier(
            n_estimators=100,
            max_depth=5,
            learning_rate=0.1,
            objective='binary:logistic',
            eval_metric='logloss',
            n_jobs=-1,  # M3 최적화: 모든 코어 사용
            random_state=42,
            tree_method='hist'  # 빠른 학습
        )
        
        # 학습 수행
        self.model.fit(
            X_train, y_train,
            eval_set=[(X_test, y_test)],
            verbose=False
        )
        
        # 평가
        y_pred = self.model.predict(X_test)
        accuracy = accuracy_score(y_test, y_pred)
        
        # 메트릭 업데이트
        self.metrics = {
            "accuracy": accuracy,
            "last_trained": datetime.now().isoformat(),
            "total_samples": len(X)
        }
        
        # 모델 저장
        self.save_model()
        
        logger.info(f"✅ Initial Training Complete - Accuracy: {accuracy:.2%}")
        logger.info(f"📊 Classification Report:\n{classification_report(y_test, y_pred)}")
    
    def retrain_model(self, X: pd.DataFrame, y: pd.Series):
        """
        모델 재학습 (Incremental Update)
        
        새로운 매매 데이터를 포함하여 모델을 업데이트합니다.
        XGBoost는 기본적으로 incremental learning을 완벽 지원하지 않지만,
        전체 데이터로 재학습하는 방식으로 구현합니다.
        """
        logger.info("🔄 Retraining Model with New Data...")
        
        # 전체 데이터로 재학습
        self.train_initial_model(X, y)
        
        logger.info(f"✅ Retraining Complete - New Accuracy: {self.metrics['accuracy']:.2%}")
    
    def predict(self, features: pd.DataFrame) -> Tuple[int, float]:
        """
        예측 수행
        
        Returns:
            (prediction, confidence): 
                - prediction: 0 (하락) 또는 1 (상승)
                - confidence: 확신도 (0.0 ~ 1.0)
        """
        if self.model is None:
            logger.warning("⚠️ Model not trained yet!")
            return 0, 0.0
        
        # 예측
        prediction = self.model.predict(features)[0]
        probabilities = self.model.predict_proba(features)[0]
        confidence = probabilities[1]  # 상승 확률
        
        return int(prediction), float(confidence)
    
    def save_model(self):
        """모델을 디스크에 저장"""
        if self.model is not None:
            joblib.dump({
                "model": self.model,
                "metrics": self.metrics
            }, self.model_path)
            logger.info(f"💾 Model saved to {self.model_path}")
    
    def load_model(self):
        """저장된 모델 로드"""
        if Path(self.model_path).exists():
            data = joblib.load(self.model_path)
            self.model = data["model"]
            self.metrics = data["metrics"]
            logger.info(f"📂 Model loaded from {self.model_path}")
            logger.info(f"   Accuracy: {self.metrics['accuracy']:.2%}")
        else:
            logger.info("ℹ️  No existing model found. Will train from scratch.")


class FeatureEngineer:
    """
    기술적 지표 기반 특징 추출
    
    과거 데이터를 받아 Machine Learning에 사용할 특징(Features)을 생성합니다.
    """
    
    @staticmethod
    def extract_features(df: pd.DataFrame) -> Dict:
        """
        OHLCV 데이터로부터 기술적 지표 추출
        
        Args:
            df: OHLCV 컬럼을 가진 DataFrame (close, high, low, volume)
        
        Returns:
            features: 추출된 특징 딕셔너리
        """
        # 최소 데이터 검증
        if len(df) < 30:
            logger.warning("⚠️ Insufficient data for feature extraction")
            return {}
        
        close = df['close']
        high = df['high']
        low = df['low']
        volume = df['volume']
        
        # 1. RSI (Relative Strength Index)
        rsi = RSIIndicator(close, window=14).rsi().iloc[-1]
        
        # 2. MACD
        macd_indicator = MACD(close)
        macd = macd_indicator.macd().iloc[-1]
        macd_signal = macd_indicator.macd_signal().iloc[-1]
        
        # 3. Bollinger Bands
        bb = BollingerBands(close, window=20, window_dev=2)
        bb_high = bb.bollinger_hband().iloc[-1]
        bb_low = bb.bollinger_lband().iloc[-1]
        current_price = close.iloc[-1]
        # BB 내 상대 위치 (0: 하단, 0.5: 중간, 1: 상단)
        bb_position = (current_price - bb_low) / (bb_high - bb_low) if bb_high != bb_low else 0.5
        
        # 4. Volume Ratio
        volume_ma = volume.rolling(window=20).mean().iloc[-1]
        volume_ratio = volume.iloc[-1] / volume_ma if volume_ma > 0 else 1.0
        
        # 5. Price Change
        price_change_5m = (close.iloc[-1] - close.iloc[-5]) / close.iloc[-5] if len(close) >= 5 else 0
        price_change_15m = (close.iloc[-1] - close.iloc[-15]) / close.iloc[-15] if len(close) >= 15 else 0
        
        # 6. EMA (Exponential Moving Average)
        ema_9 = EMAIndicator(close, window=9).ema_indicator().iloc[-1]
        ema_21 = EMAIndicator(close, window=21).ema_indicator().iloc[-1]
        
        # 7. ATR (Average True Range) - 변동성 측정
        atr = AverageTrueRange(high, low, close, window=14).average_true_range().iloc[-1]
        
        features = {
            'rsi': rsi,
            'macd': macd,
            'macd_signal': macd_signal,
            'bb_position': bb_position,
            'volume_ratio': volume_ratio,
            'price_change_5m': price_change_5m,
            'price_change_15m': price_change_15m,
            'ema_9': ema_9,
            'ema_21': ema_21,
            'atr': atr
        }
        
        return features
    
    @staticmethod
    def features_to_dataframe(features: Dict) -> pd.DataFrame:
        """특징 딕셔너리를 DataFrame으로 변환 (모델 입력용)"""
        return pd.DataFrame([features])


if __name__ == "__main__":
    # 테스트 코드
    print("=" * 60)
    print("Data & Model Manager Test")
    print("=" * 60)
    
    # TradeMemory 테스트
    memory = TradeMemory()
    print("\n✅ TradeMemory created")
    
    # ModelLearner 테스트
    learner = ModelLearner()
    print("✅ ModelLearner created")
    
    # 통계 확인
    stats = memory.get_statistics()
    print(f"\n📊 Current Statistics:")
    print(f"   Total Trades: {stats['total_trades']}")
    print(f"   Win Rate: {stats['win_rate']:.2f}%")
    
    print("\n" + "=" * 60)
    print("✅ All tests passed!")
    print("=" * 60)
