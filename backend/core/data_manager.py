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
import os

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


# 프로젝트 루트 경로 찾기 (backend/core/data_manager.py -> ../../)
def get_project_root() -> Path:
    """프로젝트 루트 경로 반환 (backend/core에서 2단계 위)"""
    current_file = Path(__file__).resolve()
    # backend/core/data_manager.py -> backend/core -> backend -> project_root
    project_root = current_file.parent.parent.parent
    return project_root


PROJECT_ROOT = get_project_root()


class TradeMemory:
    """
    매매 기록 및 학습 데이터 영구 저장소
    
    매매가 완료될 때마다 진입 시점의 특징(Features)과 결과(Profit/Loss)를
    SQLite DB에 저장하여 모델이 실전 데이터로 학습할 수 있도록 합니다.
    """
    
    def __init__(self, db_path: str = None):
        # 기본 경로는 프로젝트 루트의 data/trade_memory.db
        if db_path is None:
            db_path = str(PROJECT_ROOT / "data" / "trade_memory.db")
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
                    profit_class INTEGER,   -- 🆕 0: 큰손실, 1: 소폭, 2: 좋은수익
                    
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
                    
                    -- 🆕 Time Features (시간 특징)
                    hour_of_day INTEGER,    -- 0-23
                    day_of_week INTEGER,    -- 0-6 (월-일)
                    
                    -- 🆕 Momentum Features (모멘텀 특징)
                    rsi_change REAL,        -- RSI 변화량 (5분)
                    volume_trend REAL,      -- 거래량 추세
                    
                    -- 🆕 Sequence Features (시계열 특징)
                    rsi_prev_5m REAL,       -- 5분 전 RSI
                    bb_position_prev_5m REAL,  -- 5분 전 BB 위치
                    
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
                    hour_of_day, day_of_week, rsi_change, volume_trend,
                    rsi_prev_5m, bb_position_prev_5m,
                    status
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'open')
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
                features.get('atr', 0),
                features.get('hour_of_day', 0),
                features.get('day_of_week', 0),
                features.get('rsi_change', 0),
                features.get('volume_trend', 0),
                features.get('rsi_prev_5m', 0),
                features.get('bb_position_prev_5m', 0)
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
                
                # 🆕 profit_class: 3단계 분류 (수익률 크기 반영)
                # 0: 큰 손실 (< -0.5%)
                # 1: 소폭/본전 (-0.5% ~ +0.5%)
                # 2: 좋은 수익 (> +0.5%)
                if profit_rate < -0.005:
                    profit_class = 0  # Big loss
                elif profit_rate > 0.005:
                    profit_class = 2  # Good profit
                else:
                    profit_class = 1  # Neutral
                
                # 업데이트
                conn.execute("""
                    UPDATE trades 
                    SET exit_price = ?,
                        profit_rate = ?,
                        is_profitable = ?,
                        profit_class = ?,
                        status = 'closed'
                    WHERE id = ?
                """, (exit_price, profit_rate, is_profitable, profit_class, trade_id))
                conn.commit()
                
                class_emoji = ["🔴", "⚪", "🟢"][profit_class]
                logger.info(
                    f"{class_emoji} Trade Closed: ID={trade_id}, "
                    f"Profit={profit_rate*100:.2f}% (Class={profit_class})"
                )
        except Exception as e:
            logger.error(f"❌ Failed to update trade exit: {e}")
    
    def get_learning_data(self, min_samples: int = 30, limit: int = 500) -> Optional[Tuple[pd.DataFrame, pd.Series, np.ndarray]]:
        """
        모델 학습용 데이터 반환 (시간 가중치 포함)
        🆕 Time-Weighted Learning: 최근 데이터에 더 높은 가중치 부여

        Args:
            min_samples: 최소 데이터 수
            limit: 최대 데이터 수 (125 → 500으로 증가, 오래된 데이터 삭제하지 않음)

        Returns:
            (X, y, sample_weights): 특징 데이터프레임, 라벨 시리즈, 샘플 가중치 배열
        """
        with sqlite3.connect(self.db_path) as conn:
            df = pd.read_sql_query("""
                SELECT
                    rsi, macd, macd_signal, bb_position, volume_ratio,
                    price_change_5m, price_change_15m, ema_9, ema_21, atr,
                    COALESCE(hour_of_day, 12) as hour_of_day,
                    COALESCE(day_of_week, 0) as day_of_week,
                    COALESCE(rsi_change, 0) as rsi_change,
                    COALESCE(volume_trend, 0) as volume_trend,
                    COALESCE(rsi_prev_5m, rsi) as rsi_prev_5m,
                    COALESCE(bb_position_prev_5m, bb_position) as bb_position_prev_5m,
                    COALESCE(profit_class,
                        CASE
                            WHEN profit_rate < -0.005 THEN 0
                            WHEN profit_rate > 0.005 THEN 2
                            ELSE 1
                        END
                    ) as profit_class,
                    timestamp
                FROM trades
                WHERE status = 'closed' AND is_profitable IS NOT NULL
                ORDER BY timestamp DESC
                LIMIT ?
            """, conn, params=(limit,))

            # 최신순(DESC)으로 가져왔으므로 다시 시간순(ASC)으로 정렬
            df = df.iloc[::-1].reset_index(drop=True)

        if len(df) < min_samples:
            logger.warning(f"⚠️ Insufficient data: {len(df)}/{min_samples}")
            return None

        # 🆕 시간 기반 가중치 계산 (Exponential Time Decay)
        from datetime import datetime as dt

        # timestamp를 datetime으로 변환
        df['timestamp'] = pd.to_datetime(df['timestamp'])

        # 가장 최근 거래 시간 기준으로 일수 차이 계산
        latest_time = df['timestamp'].max()
        df['days_old'] = (latest_time - df['timestamp']).dt.total_seconds() / 86400  # 초 -> 일

        # Exponential decay 가중치 계산
        # weight = exp(-decay_rate * days_old)
        # decay_rate = 0.02: 약 35일마다 가중치 절반으로 감소
        decay_rate = 0.02
        sample_weights = np.exp(-decay_rate * df['days_old'].values)

        # 최소 가중치 0.1 보장 (완전히 무시되지 않도록)
        sample_weights = np.maximum(sample_weights, 0.1)

        logger.info(f"📊 Learning Data Loaded: {len(df)} samples (16 features, 3-class label)")
        logger.info(f"⚖️  Sample Weights: min={sample_weights.min():.3f}, max={sample_weights.max():.3f}, "
                   f"mean={sample_weights.mean():.3f}")
        logger.info(f"📅 Data Age Range: {df['days_old'].min():.1f} ~ {df['days_old'].max():.1f} days")

        # timestamp와 days_old 컬럼 제거
        X = df.drop(['profit_class', 'timestamp', 'days_old'], axis=1)
        y = df['profit_class']

        return X, y, sample_weights
    
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
        win_rate = (wins / total * 100) if total and total > 0 else 0

        result = {
            "total_trades": total or 0,
            "win_rate": win_rate,
            "avg_profit_pct": (avg_profit or 0) * 100,
            "max_profit_pct": (max_profit or 0) * 100,
            "max_loss_pct": (max_loss or 0) * 100
        }

        # JSON 직렬화를 위해 nan/inf 값 정제
        return sanitize_dict_for_json(result)
    
    def get_open_positions(self) -> list:
        """
        열린 포지션(open) 조회 - 재시작 시 보유 시간 유지용
        
        Returns:
            list: [{"id": trade_id, "ticker": ticker, "entry_price": price, "entry_time": timestamp}, ...]
        """
        with sqlite3.connect(self.db_path) as conn:
            rows = conn.execute("""
                SELECT id, ticker, entry_price, timestamp
                FROM trades
                WHERE status = 'open'
            """).fetchall()
        
        positions = []
        for row in rows:
            positions.append({
                "id": row[0],
                "ticker": row[1],
                "entry_price": row[2],
                "entry_time": row[3]  # ISO format string
            })
        
        logger.info(f"📂 Found {len(positions)} open positions in DB")
        return positions


class ModelLearner:
    """
    XGBoost 모델 학습 및 관리
    
    Features:
    - 초기 학습 (Cold Start)
    - 점진적 재학습 (Incremental Update)
    - 모델 영구 저장/로드
    - 예측 및 확신도 제공
    """
    
    def __init__(self, model_path: str = None):
        # 기본 경로는 프로젝트 루트의 models/xgb_model.pkl
        if model_path is None:
            model_path = str(PROJECT_ROOT / "models" / "xgb_model.pkl")
        self.model_path = model_path
        self.model: Optional[xgb.XGBClassifier] = None
        self.scaler: Optional[object] = None  # 🆕 StandardScaler 저장
        self.pca: Optional[object] = None     # 🆕 PCA 객체 저장
        self.use_pca = True                   # PCA 사용 여부
        self.pca_components = 0.95            # 95% 분산 보존
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
    
    def train_initial_model(self, X: pd.DataFrame, y: pd.Series, sample_weights: np.ndarray = None):
        """
        초기 모델 학습 (Cold Start)
        🆕 시간 가중치를 반영한 학습

        Args:
            X: 특징 데이터
            y: 라벨
            sample_weights: 샘플별 가중치 (최근 데이터 우선)
        """
        logger.info("🎓 Starting Initial Model Training...")

        # 🛡️ NaN 처리 (학습 전 결측치 중앙값으로 대체 - Outlier Detection 전에 수행)
        # 0으로 대체하면 정보 왜곡 가능, 중앙값이 더 안정적
        X = X.fillna(X.median())

        # 🔥 Outlier Detection (이상값 제거)
        original_samples = len(X)
        if original_samples >= 30:  # 충분한 데이터가 있을 때만 적용
            from sklearn.ensemble import IsolationForest

            outlier_detector = IsolationForest(
                contamination=0.1,  # 데이터의 10%를 이상값으로 간주
                random_state=42,
                n_jobs=-1
            )

            # 이상값 감지 (-1: 이상값, 1: 정상값)
            is_inlier = outlier_detector.fit_predict(X)

            # 정상 데이터만 필터링
            X_clean = X[is_inlier == 1]
            y_clean = y[is_inlier == 1]

            # 🆕 가중치도 함께 필터링
            if sample_weights is not None:
                sample_weights_clean = sample_weights[is_inlier == 1]
            else:
                sample_weights_clean = None

            outliers_removed = original_samples - len(X_clean)
            logger.info(f"🧹 Outlier Detection:")
            logger.info(f"   Total Samples: {original_samples}")
            logger.info(f"   Outliers Removed: {outliers_removed} ({outliers_removed/original_samples*100:.1f}%)")
            logger.info(f"   Clean Samples: {len(X_clean)}")

            X = X_clean
            y = y_clean
            sample_weights = sample_weights_clean
        else:
            logger.info(f"⚠️ Skipping outlier detection (need 30+ samples, got {original_samples})")
        
        # 🔧 클래스 분포 확인 및 리매핑
        unique_classes = sorted(y.unique())
        logger.info(f"📊 Class distribution: {dict(y.value_counts())}")
        
        # 클래스가 3개 미만이면 존재하는 클래스만으로 학습
        num_classes = len(unique_classes)
        if num_classes < 3:
            logger.warning(f"⚠️ Only {num_classes} classes present. Remapping to 0-{num_classes-1}")
            # 클래스 리매핑 (0, 2 → 0, 1)
            class_map = {c: i for i, c in enumerate(unique_classes)}
            y = y.map(class_map)

        # Train-Test Split (클래스가 충분하면 stratify 사용)
        # 🆕 sample_weights도 함께 분할
        try:
            # 각 클래스별 최소 2개 이상 있어야 stratify 가능
            can_stratify = all(y.value_counts() >= 2)
            if can_stratify:
                if sample_weights is not None:
                    X_train, X_test, y_train, y_test, weights_train, weights_test = train_test_split(
                        X, y, sample_weights, test_size=0.2, random_state=42, stratify=y
                    )
                else:
                    X_train, X_test, y_train, y_test = train_test_split(
                        X, y, test_size=0.2, random_state=42, stratify=y
                    )
                    weights_train, weights_test = None, None
            else:
                logger.warning("⚠️ Not enough samples per class for stratify. Using random split.")
                if sample_weights is not None:
                    X_train, X_test, y_train, y_test, weights_train, weights_test = train_test_split(
                        X, y, sample_weights, test_size=0.2, random_state=42
                    )
                else:
                    X_train, X_test, y_train, y_test = train_test_split(
                        X, y, test_size=0.2, random_state=42
                    )
                    weights_train, weights_test = None, None
        except Exception as e:
            logger.warning(f"⚠️ Stratify failed: {e}. Using random split.")
            if sample_weights is not None:
                X_train, X_test, y_train, y_test, weights_train, weights_test = train_test_split(
                    X, y, sample_weights, test_size=0.2, random_state=42
                )
            else:
                X_train, X_test, y_train, y_test = train_test_split(
                    X, y, test_size=0.2, random_state=42
                )
                weights_train, weights_test = None, None
        
        # 🔧 Feature Normalization (StandardScaler)
        from sklearn.preprocessing import StandardScaler
        
        self.scaler = StandardScaler()
        X_train_scaled = self.scaler.fit_transform(X_train)  # 학습 데이터로 fit + transform
        X_test_scaled = self.scaler.transform(X_test)        # 테스트 데이터는 transform만
        
        
        logger.info("🔧 Feature Normalization Applied (StandardScaler)")
        
        # 🆕 PCA Dimensionality Reduction
        # 🆕 PCA Dimensionality Reduction
        # 🔥 데이터가 충분할 때만 PCA 적용 (100개 이상)
        if self.use_pca and len(X_train) >= 100:
            from sklearn.decomposition import PCA
            self.pca = PCA(n_components=self.pca_components)
            X_train_final = self.pca.fit_transform(X_train_scaled)
            X_test_final = self.pca.transform(X_test_scaled)
            
            n_features_ = self.pca.n_components_
            explained_var_ = sum(self.pca.explained_variance_ratio_)
            logger.info(f"🧬 PCA Applied: {X_train.shape[1]} -> {n_features_} features (Var={explained_var_:.1%})")
        else:
            if self.use_pca:
                logger.info(f"⚠️ Not enough data for PCA ({len(X_train)} samples). Skipping PCA.")
            self.pca = None
            X_train_final = X_train_scaled
            X_test_final = X_test_scaled
        
        # 🆕 XGBoost Multi-Class Model (동적 클래스 수)
        self.model = xgb.XGBClassifier(
            n_estimators=100,
            max_depth=3 if len(X_train) < 100 else 5,  # 데이터 적을 땐 얕은 트리
            learning_rate=0.1,
            objective='multi:softprob' if num_classes > 2 else 'binary:logistic',
            eval_metric='mlogloss' if num_classes > 2 else 'logloss',
            num_class=num_classes if num_classes > 2 else None,
            n_jobs=-1,  # M3 최적화: 모든 코어 사용
            random_state=42,
            tree_method='hist'  # 빠른 학습
        )
        
        # 학습 수행 (정규화된 데이터 + 시간 가중치 사용)
        fit_params = {
            'eval_set': [(X_test_final, y_test)],
            'verbose': False
        }

        # 🆕 시간 가중치 추가
        if weights_train is not None:
            fit_params['sample_weight'] = weights_train
            logger.info(f"⚖️  Using time-weighted samples (recent data prioritized)")

        self.model.fit(X_train_final, y_train, **fit_params)
        
        # 평가
        y_pred = self.model.predict(X_test_final)
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
    
    def retrain_model(self, X: pd.DataFrame, y: pd.Series, sample_weights: np.ndarray = None):
        """
        모델 재학습 (Incremental Update)
        🆕 시간 가중치를 반영한 재학습

        새로운 매매 데이터를 포함하여 모델을 업데이트합니다.
        XGBoost는 기본적으로 incremental learning을 완벽 지원하지 않지만,
        전체 데이터로 재학습하는 방식으로 구현합니다.
        """
        logger.info("🔄 Retraining Model with New Data...")

        # 전체 데이터로 재학습 (시간 가중치 포함)
        self.train_initial_model(X, y, sample_weights)

        logger.info(f"✅ Retraining Complete - New Accuracy: {self.metrics['accuracy']:.2%}")
    
    def predict(self, features: pd.DataFrame) -> Tuple[int, float]:
        """
        예측 수행 (3-class 분류)
        
        Returns:
            (prediction, confidence): 
                - prediction: 0 (큰손실), 1 (소폭), 2 (좋은수익)
                - confidence: "좋은 수익" 확률 (class 2의 확률)
        """
        if self.model is None:
            logger.warning("⚠️ Model not trained yet!")
            return 0, 0.0
        
        # 🆕 16개 특징 확인 및 누락된 특징 채우기
        expected_features = [
            'rsi', 'macd', 'macd_signal', 'bb_position', 'volume_ratio',
            'price_change_5m', 'price_change_15m', 'ema_9', 'ema_21', 'atr',
            'hour_of_day', 'day_of_week', 'rsi_change', 'volume_trend',
            'rsi_prev_5m', 'bb_position_prev_5m'
        ]
        
        # 누락된 특징 기본값 채우기
        for feat in expected_features:
            if feat not in features.columns:
                if feat == 'hour_of_day':
                    features[feat] = 12  # 정오
                elif feat == 'day_of_week':
                    features[feat] = 0   # 월요일
                elif feat == 'rsi_prev_5m':
                    features[feat] = features.get('rsi', 50)
                elif feat == 'bb_position_prev_5m':
                    features[feat] = features.get('bb_position', 0.5)
                else:
                    features[feat] = 0
        
        # 특징 순서 맞추기
        features = features[expected_features]
        
        # 🛡️ NaN 처리 (PCA 오류 방지)
        features = features.fillna(0)
        
        # 🔧 Feature Normalization 적용 (학습 시와 동일한 Scaler 사용)
        if self.scaler is not None:
            features_scaled = self.scaler.transform(features)
        else:
            # Scaler 없으면 원본 사용 (하위 호환)
            features_scaled = features
        
        # 🆕 PCA Dimensionality Reduction 적용
        if self.pca is not None:
            features_final = self.pca.transform(features_scaled)
        else:
            features_final = features_scaled
        
        # 예측
        prediction = self.model.predict(features_final)[0]
        probabilities = self.model.predict_proba(features_final)[0]
        
        # 🆕 Class 2 (좋은 수익) 확률을 confidence로 사용
        # probabilities: [P(loss), P(neutral), P(profit)]
        confidence = probabilities[2] if len(probabilities) == 3 else probabilities[1]
        
        return int(prediction), float(confidence)
    
    def save_model(self):
        """모델을 디스크에 저장"""
        if self.model is not None:
            joblib.dump({
                "model": self.model,
                "scaler": self.scaler,  # 🆕 Scaler도 함께 저장
                "pca": self.pca,        # 🆕 PCA 저장
                "metrics": self.metrics
            }, self.model_path)
            logger.info(f"💾 Model saved to {self.model_path}")
    
    def load_model(self):
        """저장된 모델 로드"""
        if Path(self.model_path).exists():
            data = joblib.load(self.model_path)
            self.model = data["model"]
            self.scaler = data.get("scaler", None)  # 🆕 Scaler 로드 (하위 호환)
            self.pca = data.get("pca", None)        # 🆕 PCA 로드 (하위 호환)
            self.metrics = data["metrics"]
            logger.info(f"📂 Model loaded from {self.model_path}")
            logger.info(f"   Accuracy: {self.metrics['accuracy']:.2%}")
            if self.scaler:
                logger.info("   ✅ Scaler loaded (Feature Normalization enabled)")
        else:
            logger.info("ℹ️  No existing model found. Will train from scratch.")


def sanitize_float(value):
    """
    JSON 직렬화를 위해 float 값 정제
    nan, inf, -inf를 None 또는 0으로 변환
    """
    if isinstance(value, float):
        if np.isnan(value) or np.isinf(value):
            return 0.0
    return value


def sanitize_dict_for_json(data):
    """
    딕셔너리 내의 모든 값을 JSON-safe하게 변환
    재귀적으로 중첩된 딕셔너리와 리스트도 처리
    - float: nan/inf를 0.0으로 변환
    - datetime: ISO 문자열로 변환
    - numpy 타입: Python 기본 타입으로 변환
    """
    if isinstance(data, dict):
        return {k: sanitize_dict_for_json(v) for k, v in data.items()}
    elif isinstance(data, (list, tuple)):
        return [sanitize_dict_for_json(item) for item in data]
    elif isinstance(data, np.ndarray):
        return [sanitize_dict_for_json(item) for item in data.tolist()]
    elif isinstance(data, float):
        return sanitize_float(data)
    elif isinstance(data, np.floating):
        return sanitize_float(float(data))
    elif isinstance(data, np.integer):
        return int(data)
    elif isinstance(data, np.bool_):
        return bool(data)
    elif isinstance(data, datetime):
        return data.isoformat()
    return data


class FeatureEngineer:
    """
    기술적 지표 기반 특징 추출

    과거 데이터를 받아 Machine Learning에 사용할 특징(Features)을 생성합니다.
    """

    @staticmethod
    def extract_features(df: pd.DataFrame) -> Dict:
        """
        OHLCV 데이터로부터 기술적 지표 추출 (확장 버전)
        
        Args:
            df: OHLCV 컬럼을 가진 DataFrame (close, high, low, volume)
        
        Returns:
            features: 추출된 특징 딕셔너리 (16개 특징)
        """
        from datetime import datetime
        
        # 최소 데이터 검증
        if len(df) < 30:
            logger.warning("⚠️ Insufficient data for feature extraction")
            return {}
        
        close = df['close']
        high = df['high']
        low = df['low']
        volume = df['volume']
        
        # 1. RSI (Relative Strength Index)
        rsi_series = RSIIndicator(close, window=14).rsi()
        rsi = rsi_series.iloc[-1]
        
        # 2. MACD
        macd_indicator = MACD(close)
        macd = macd_indicator.macd().iloc[-1]
        macd_signal = macd_indicator.macd_signal().iloc[-1]
        
        # 3. Bollinger Bands
        bb = BollingerBands(close, window=20, window_dev=2)
        bb_high = bb.bollinger_hband()
        bb_low = bb.bollinger_lband()
        current_price = close.iloc[-1]
        # BB 내 상대 위치 (0: 하단, 0.5: 중간, 1: 상단)
        bb_h = bb_high.iloc[-1]
        bb_l = bb_low.iloc[-1]
        bb_position = (current_price - bb_l) / (bb_h - bb_l) if bb_h != bb_l else 0.5
        
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
        
        # ============ 🆕 NEW FEATURES ============
        
        # 8. Time Features (시간 특징)
        now = datetime.now()
        hour_of_day = now.hour        # 0-23
        day_of_week = now.weekday()   # 0-6 (월-일)
        
        # 9. Momentum Features (모멘텀 특징)
        # RSI 변화량 (5분 전 대비)
        rsi_prev_5m = rsi_series.iloc[-5] if len(rsi_series) >= 5 else rsi
        rsi_change = rsi - rsi_prev_5m
        
        # 거래량 추세 (최근 5개 vs 이전 5개)
        if len(volume) >= 10:
            recent_vol = volume.iloc[-5:].mean()
            prev_vol = volume.iloc[-10:-5].mean()
            volume_trend = (recent_vol - prev_vol) / prev_vol if prev_vol > 0 else 0
        else:
            volume_trend = 0
        
        # 10. Sequence Features (시계열 특징)
        # 5분 전 BB 위치
        if len(bb_high) >= 5 and len(bb_low) >= 5:
            bb_h_5m = bb_high.iloc[-5]
            bb_l_5m = bb_low.iloc[-5]
            price_5m = close.iloc[-5]
            bb_position_prev_5m = (price_5m - bb_l_5m) / (bb_h_5m - bb_l_5m) if bb_h_5m != bb_l_5m else 0.5
        else:
            bb_position_prev_5m = bb_position
        
        features = {
            # 기존 특징 (10개)
            'rsi': rsi,
            'macd': macd,
            'macd_signal': macd_signal,
            'bb_position': bb_position,
            'volume_ratio': volume_ratio,
            'price_change_5m': price_change_5m,
            'price_change_15m': price_change_15m,
            'ema_9': ema_9,
            'ema_21': ema_21,
            'atr': atr,
            # 🆕 시간 특징 (2개)
            'hour_of_day': hour_of_day,
            'day_of_week': day_of_week,
            # 🆕 모멘텀 특징 (2개)
            'rsi_change': rsi_change,
            'volume_trend': volume_trend,
            # 🆕 시계열 특징 (2개)
            'rsi_prev_5m': rsi_prev_5m,
            'bb_position_prev_5m': bb_position_prev_5m
        }

        # JSON 직렬화를 위해 nan/inf 값 정제
        return sanitize_dict_for_json(features)
    
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
