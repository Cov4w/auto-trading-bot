# 🤖 Self-Evolving Trading System

> **Renaissance Technologies 스타일의 자가 진화 암호화폐 자동매매 시스템**
> 
> 실전 매매 데이터를 통해 스스로 학습하고 진화하는 AI 트레이딩 봇

<div align="center">

![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)
![XGBoost](https://img.shields.io/badge/XGBoost-2.0-green.svg)
![Streamlit](https://img.shields.io/badge/Streamlit-1.29-red.svg)
![License](https://img.shields.io/badge/License-MIT-yellow.svg)

</div>

---

## 🌟 핵심 특징

### 1. 🧠 Continuous Learning (지속 학습)
- 매매가 종료될 때마다 결과를 학습 데이터로 축적
- N건(기본 10건) 누적 시 XGBoost 모델 자동 재학습
- 시간이 지날수록 실전 패턴에 최적화되는 **Self-Evolving** 메커니즘

### 2. 🎯 Hybrid Strategy
- **XGBoost**: 추세 예측 (상승 확률 > 70%)
- **Mean Reversion**: 타이밍 포착 (RSI < 30 또는 Bollinger Band 하단)
- 두 전략의 AND 조합으로 False Positive 최소화

### 3. 🎯 AI Coin Selection (NEW!)
- 빗썸 상장 **20개 주요 코인 실시간 분석**
- AI 확신도, 기술적 지표, 과거 승률 종합 평가
- **승률이 가장 높을 코인**을 자동 선택하여 매매
-상위 5개 추천 코인 대시보드 표시
- 상세 가이드: [COIN_SELECTION_GUIDE.md](COIN_SELECTION_GUIDE.md)

### 4. 📊 Premium Dashboard
- **Real-time Monitoring**: 실시간 시세 및 포지션 추적
- **Learning Metrics**: AI 모델 정확도, 누적 학습 데이터 수, 승률 변화
- **Dual-Axis Chart**: 누적 수익률 vs 모델 정확도 동시 시각화
- **Signal Visualization**: 캔들스틱 차트 위에 매수/매도 시그널 + 확신도 표시
- **🔥 Coin Recommendations**: AI 추천 상위 5개 코인 + 종합 점수

### 5. 💾 Persistence
- **SQLite**: 매매 기록 영구 저장
- **Joblib**: 학습된 모델 자동 저장/로드
- 프로그램 재시작 후에도 기존 학습 상태 유지

### 6. ⚡ M3 Optimized
- Apple Silicon(M3) 고속 연산 최적화
- XGBoost `n_jobs=-1` 설정으로 모든 코어 활용

---

## 🏗️ 시스템 아키텍처

```
┌─────────────────────────────────────────────────────────┐
│                   Streamlit Dashboard                    │
│  (실시간 시각화 + AI 학습 진행도 + 봇 제어 인터페이스)      │
└────────────────────┬────────────────────────────────────┘
                     │
          ┌──────────▼──────────┐
          │   Trading Bot Core   │
          │  (매매 로직 + 신호)    │
          └──────────┬──────────┘
                     │
        ┌────────────┴────────────┐
        │                         │
   ┌────▼─────┐          ┌───────▼────────┐
   │  Model    │          │  Trade Memory   │
   │  Learner  │◄────────►│  (SQLite DB)    │
   │(XGBoost)  │          │                 │
   └───────────┘          └─────────────────┘
        │
        │ Retrain Every N Trades
        │
   ┌────▼──────────────┐
   │  Feature Engineer  │
   │ (Technical Indicators) │
   └───────────────────┘
```

---

## 📦 설치 방법

### 1. Prerequisites
- Python 3.10 이상
- Bithumb API 키 (Connect Key + Secret Key)

### 2. Clone Repository
```bash
git clone <repository-url>
cd bitThumb_std
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Environment Setup
`.env.example`을 복사하여 `.env` 파일 생성 후 API 키 입력:

```bash
cp .env.example .env
```

`.env` 파일 편집:
```env
# Bithumb API Credentials
BITHUMB_CONNECT_KEY=your_actual_connect_key_here
BITHUMB_SECRET_KEY=your_actual_secret_key_here

# Trading Configuration
TICKER=BTC  # 거래할 암호화폐
TRADE_AMOUNT=10000  # 1회 매수 금액 (KRW)
TARGET_PROFIT=0.02  # 목표 수익률 (2%)
STOP_LOSS=0.02  # 손절률 (2%)

# Learning Configuration
RETRAIN_THRESHOLD=10  # N건의 매매 후 모델 재학습
MODEL_CONFIDENCE_THRESHOLD=0.7  # 매수 신호 확신도 임계값
```

---

## 🚀 실행 방법

### Dashboard 실행
```bash
streamlit run app.py
```

브라우저에서 자동으로 `http://localhost:8501` 이 열립니다.

### 봇 시작
1. 좌측 사이드바 **"▶️ START"** 버튼 클릭
2. 봇이 백그라운드에서 60초 주기로 시장 모니터링 시작
3. 매수 신호 감지 시 자동 주문 실행 (현재는 데모 모드)

### 강제 재학습
- 사이드바 **"🎓 Retrain Model Now"** 버튼으로 언제든지 수동 재학습 가능

---

## 📚 주요 모듈 설명

### 1. `data_manager.py`
**TradeMemory**: 매매 기록 저장소
- SQLite DB에 진입/청산 데이터 저장
- 학습용 특징(Features) + 라벨(Profit/Loss) 관리

**ModelLearner**: XGBoost 모델 관리
- 초기 학습 (Cold Start)
- 점진적 재학습 (Incremental Update)
- 모델 저장/로드

**FeatureEngineer**: 기술적 지표 추출
- RSI, MACD, Bollinger Bands, EMA, ATR 등
- OHLCV 데이터 → ML 특징 변환

### 2. `trading_bot.py`
**TradingBot**: 자가 진화 트레이딩 봇
- 실시간 가격 모니터링 (60초 주기)
- 매수 조건: XGBoost 상승 예측 + (RSI < 30 OR BB 하단)
- 매도 조건: 목표가/손절가/BB 상단
- **매도 후 자동 학습 트리거** (N건 누적 시)

### 3. `app.py`
**Streamlit Dashboard**
- AI 학습 메트릭 실시간 표시
- 성능 이중 축 차트 (수익률 vs 승률)
- 캔들스틱 + 매매 시그널 시각화
- 봇 제어 인터페이스

---

## 🎓 Learning Mechanism (핵심!)

### Cold Start (초기 학습)
1. 과거 30일 OHLCV 데이터 수집
2. 각 시점의 기술적 지표 추출
3. 라벨: 다음 날 상승 여부 (1: 상승, 0: 하락)
4. XGBoost 모델 학습

### Continuous Learning (지속 학습)
```python
매수 진입
   ↓
특징 저장 (RSI, MACD, BB, ...)
   ↓
매도 청산
   ↓
결과 기록 (Profit: 1, Loss: 0)
   ↓
TradeMemory DB 저장
   ↓
누적 건수 % RETRAIN_THRESHOLD == 0?
   ↓ YES
모델 재학습 (전체 실전 데이터 사용)
   ↓
새로운 모델 저장
   ↓
다음 매매부터 업데이트된 모델 사용
```

### 왜 Self-Evolving인가?
- 백테스트 데이터가 아닌 **실전 매매 결과**로 학습
- 시장 변화에 자동 적응
- 승률이 낮은 패턴은 자연스럽게 가중치 감소
- 승률이 높은 패턴은 가중치 증가

---

## 📊 Dashboard 주요 UI

### 1. AI Learning Metrics
| Metric | Description |
|--------|-------------|
| 🎯 Model Accuracy | 현재 모델의 테스트 정확도 |
| 📚 Learning Samples | 누적된 학습 데이터 개수 |
| 🏆 Win Rate | 전체 매매 승률 |
| 🕐 Last Trained | 마지막 재학습 시점 |

### 2. Performance Chart (Dual-Axis)
- **Primary Y-Axis**: 누적 수익률 (%)
- **Secondary Y-Axis**: 최근 10회 승률 이동평균 (%)
- **X-Axis**: 매매 번호
→ AI가 학습할수록 승률이 올라가는지 한눈에 확인!

### 3. Candlestick with Signals
- 🔵 파란 삼각형 (▲): 매수 시그널 (툴팁에 확신도 표시)
- 🟢 초록 삼각형 (▼): 수익 매도
- 🔴 빨강 삼각형 (▼): 손절 매도

---

## ⚙️ 파라미터 튜닝 가이드

### Trading Parameters
```python
TRADE_AMOUNT = 10000  # 소액으로 시작 권장
TARGET_PROFIT = 0.02  # 낮을수록 보수적 (1~3% 권장)
STOP_LOSS = 0.02      # 리스크 관리 필수
```

### Learning Parameters
```python
RETRAIN_THRESHOLD = 10  # 너무 작으면 과적합 위험, 10~20 권장
MODEL_CONFIDENCE_THRESHOLD = 0.7  # 높을수록 보수적 (0.6~0.8 권장)
```

### XGBoost Hyperparameters (`data_manager.py`)
```python
n_estimators = 100     # 트리 개수 (50~200)
max_depth = 5          # 트리 깊이 (3~7)
learning_rate = 0.1    # 학습률 (0.01~0.3)
```

---

## 🔒 리스크 관리

### 1. 데모 모드 (기본값)
- `trading_bot.py`의 실제 주문 코드는 주석 처리됨
- 실전 매매 전 충분한 시뮬레이션 필수

### 2. 실전 모드 활성화
다음 줄의 주석을 해제:
```python
# trading_bot.py - _execute_buy()
order = self.bithumb.buy_market_order(self.ticker, self.trade_amount)

# trading_bot.py - _execute_sell()
order = self.bithumb.sell_market_order(self.ticker, self.current_position['amount'])
```

**⚠️ 경고**: 실전 매매는 본인 책임입니다. 소액으로 시작하세요!

### 3. 포지션 크기 제한
```python
MAX_POSITION_SIZE = 0.3  # 총 자산의 30% 이내
```

---

## 🧪 테스트 실행

### 1. Data Manager Test
```bash
python data_manager.py
```

### 2. Trading Bot Test
```bash
python trading_bot.py
```

### 3. Full Integration Test
```bash
streamlit run app.py
```

---

## 📁 프로젝트 구조

```
bitThumb_std/
├── app.py                 # Streamlit Dashboard
├── trading_bot.py         # Trading Core Engine
├── data_manager.py        # Data & Model Manager
├── requirements.txt       # Dependencies
├── .env.example          # Environment Template
├── .gitignore
├── README.md
├── data/                 # SQLite DB (자동 생성)
│   └── trade_memory.db
└── models/               # AI Models (자동 생성)
    └── xgb_model.pkl
```

---

## 🚧 향후 개선 사항

- [ ] **Multi-Ticker Support**: BTC, ETH, XRP 동시 운용
- [ ] **Advanced Strategies**: LSTM, Transformer 모델 추가
- [ ] **Backtesting Module**: 과거 데이터로 전략 검증
- [ ] **Telegram Bot**: 매매 알림 및 원격 제어
- [ ] **Portfolio Optimization**: Kelly Criterion 기반 포지션 크기 자동 조정
- [ ] **Ensemble Learning**: 여러 모델의 투표(Voting) 방식

---

## 📄 라이선스

MIT License

---

## 🙏 크레딧

- **XGBoost**: Tianqi Chen et al.
- **Streamlit**: Streamlit Inc.
- **pybithumb**: warlog95
- **Technical Indicators**: ta (Dario Lopez Padial)

---

## 📞 문의

프로젝트에 대한 질문이나 제안은 Issue를 통해 남겨주세요!

---

<div align="center">

**Made with ❤️ for Algorithmic Trading**

*"The market is a device for transferring money from the impatient to the patient."*  
— Warren Buffett

</div>
