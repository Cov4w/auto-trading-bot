# 🤖 Self-Evolving Trading System

> **Renaissance Technologies 스타일의 자가 진화 암호화폐 자동매매 시스템**
>
> 실전 매매 데이터를 통해 스스로 학습하고 진화하는 AI 트레이딩 봇

<div align="center">

![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)
![FastAPI](https://img.shields.io/badge/FastAPI-0.104-green.svg)
![React](https://img.shields.io/badge/React-18.2-61dafb.svg)
![XGBoost](https://img.shields.io/badge/XGBoost-2.0-orange.svg)
![License](https://img.shields.io/badge/License-MIT-yellow.svg)
![Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20macOS%20%7C%20Linux-lightgrey.svg)

</div>

---

## ⚡ 빠른 시작 (Quick Start)

### Windows 사용자
```bash
# 1. Repository 클론
git clone https://github.com/Cov4w/auto-trading-bot.git
cd auto-trading-bot

# 2. 자동 설치 (Python, Node.js 필요)
setup.bat

# 3. API 키 설정
# backend\.env 파일에서 UPBIT_ACCESS_KEY와 UPBIT_SECRET_KEY 입력

# 4. 실행
start_dev.bat

# 5. 브라우저에서 http://localhost:5173 접속 후 로그인
```

### macOS/Linux 사용자
```bash
# 1. Repository 클론
git clone https://github.com/Cov4w/auto-trading-bot.git
cd auto-trading-bot

# 2. 실행 권한 부여
chmod +x setup.sh start_dev.sh

# 3. 자동 설치 (Python3, Node.js 필요)
./setup.sh

# 4. API 키 설정
nano backend/.env
# UPBIT_ACCESS_KEY와 UPBIT_SECRET_KEY 입력 후 저장

# 5. 실행
./start_dev.sh

# 6. 브라우저에서 http://localhost:5173 접속 후 로그인
```

**필수 요구사항**: Python 3.10+, Node.js 16+, Upbit API 키

---

## 🌟 핵심 특징

### 1. 🧠 Continuous Learning (지속 학습)
- 매매가 종료될 때마다 결과를 학습 데이터로 축적
- **시간 가중치 학습**: 최근 데이터에 높은 가중치 부여 (Exponential Time Decay)
- 500개의 매매 기록을 유지하며 점진적으로 학습
- 시간이 지날수록 실전 패턴에 최적화되는 **Self-Evolving** 메커니즘

### 2. 🎯 Multi-Layer Entry Strategy
- **5단계 필터링**: BTC 상관관계 → 거래량 검증 → 추세 확인 → AI 시그널 → 기술적 지표
- **XGBoost 3-Class Model**: 손실/보합/이익 예측 (정확도 기반 진입 결정)
- **Trend Filter**: EMA 골든크로스 + 15분 가격 변화 확인
- **Volume Filter**: 24시간 거래량 1억원 이상 코인만 거래
- **BTC Correlation**: BTC 3% 이상 하락 시 알트코인 진입 차단

### 3. 🎯 AI Coin Selection
- Upbit 상장 **전체 코인 실시간 분석**
- AI 확신도, 기술적 지표, 과거 승률 종합 평가
- **승률이 가장 높을 코인**을 자동 선택하여 매매
- 상위 5개 추천 코인 대시보드 표시

### 4. 📊 Modern Dashboard (FastAPI + React)
- **JWT Authentication**: 안전한 사용자 인증 시스템
- **Real-time WebSocket**: 실시간 시세 및 포지션 추적
- **Learning Metrics**: AI 모델 정확도, 누적 학습 데이터 수, 승률 변화
- **Interactive Charts**: 수익률 차트, 캔들스틱, 매매 시그널
- **Responsive Design**: 모바일/태블릿/데스크톱 지원

### 5. 🛡️ Advanced Risk Management
- **MDD 모니터링**: 30초 주기 급락 감지 (5% 도달 시 긴급 매도)
- **Kelly Criterion**: 과학적 포지션 사이징
- **Trailing Stop**: 수익 보호 및 추가 이익 극대화
- **Flash Crash Detection**: 1분 내 7% 급락 시 긴급 청산
- **Cooldown System**: 손절 후 1시간 재진입 금지

### 6. 💾 Persistence & Scalability
- **SQLite**: 매매 기록 및 사용자 데이터 영구 저장
- **Model Versioning**: 학습된 모델 자동 저장/로드
- **RESTful API**: 확장 가능한 마이크로서비스 아키텍처
- **Docker Support** (예정): 컨테이너 기반 배포

### 7. 🌍 Cross-Platform Support
- **Windows**: `.bat` 스크립트로 원클릭 설치
- **macOS/Linux**: `.sh` 스크립트로 원클릭 설치
- **Conda/Venv**: 둘 다 지원 (자동 감지)
- **pathlib**: 플랫폼 독립적 경로 처리

---

## 🏗️ 시스템 아키텍처

```
┌─────────────────────────────────────────────────────────┐
│              React Frontend (TypeScript)                 │
│  • JWT Authentication  • WebSocket  • Charts            │
└────────────────────┬────────────────────────────────────┘
                     │ REST API / WebSocket
          ┌──────────▼──────────┐
          │   FastAPI Backend    │
          │  • Auth Routes       │
          │  • Bot Routes        │
          │  • Data Routes       │
          └──────────┬──────────┘
                     │
        ┌────────────┴────────────┐
        │                         │
   ┌────▼─────┐          ┌───────▼────────┐
   │ Trading  │          │  Data Manager   │
   │   Bot    │◄────────►│  + AI Model     │
   │  Core    │          │  (XGBoost)      │
   └──────────┘          └─────────────────┘
        │                         │
        │                    ┌────▼──────────┐
        │                    │ Time-Weighted │
        │                    │   Learning    │
        │                    │  (500 trades) │
        │                    └───────────────┘
        │
   ┌────▼──────────────┐
   │  Upbit Exchange   │
   │   API Integration │
   └───────────────────┘
```

---

## 📦 설치 방법

### 지원 플랫폼
- ✅ **Windows 10/11**
- ✅ **macOS 11+ (Intel/Apple Silicon)**
- ✅ **Linux (Ubuntu 20.04+)**

### 사전 요구사항
- **Python 3.10+**
- **Node.js 16+**
- **Upbit API 키** (Connect Key + Secret Key)
- **(선택) Anaconda/Miniconda**

---

### 🪟 Windows 설치

#### 1. Repository 클론
```bash
git clone https://github.com/Cov4w/auto-trading-bot.git
cd auto-trading-bot
```

#### 2. 자동 설치
```bash
setup.bat
```

스크립트가 자동으로:
- Python/Node.js 확인
- Conda 환경 감지 (있으면 `upBit` 환경 사용)
- Backend 의존성 설치 (`backend/requirements.txt`)
- Frontend 의존성 설치 (`npm install`)
- `.env` 파일 생성
- Admin 사용자 생성 (선택)

#### 3. API 키 설정
`backend\.env` 파일 편집:
```env
UPBIT_ACCESS_KEY=your_access_key_here
UPBIT_SECRET_KEY=your_secret_key_here
```

#### 4. 개발 서버 시작
```bash
start_dev.bat
```

두 개의 창이 열립니다:
- **Backend**: http://localhost:8000
- **Frontend**: http://localhost:5173

---

### 🍎 macOS/Linux 설치

#### 1. Repository 클론
```bash
git clone https://github.com/Cov4w/auto-trading-bot.git
cd auto-trading-bot
```

#### 2. 실행 권한 부여
```bash
chmod +x setup.sh start_dev.sh
```

#### 3. 자동 설치
```bash
./setup.sh
```

스크립트가 자동으로:
- Python3/Node.js 확인
- Conda 환경 감지 (있으면 `upBit` 환경 사용)
- Backend 의존성 설치
- Frontend 의존성 설치
- `.env` 파일 생성
- Admin 사용자 생성 (선택)

#### 4. API 키 설정
```bash
nano backend/.env
# 또는
vim backend/.env
```

```env
UPBIT_ACCESS_KEY=your_access_key_here
UPBIT_SECRET_KEY=your_secret_key_here
```

#### 5. 개발 서버 시작
```bash
./start_dev.sh
```

---

### 🐍 Conda 환경 사용 (추천)

#### Windows
```bash
conda create -n upBit python=3.10
conda activate upBit
setup.bat
```

#### macOS/Linux
```bash
conda create -n upBit python=3.10
conda activate upBit
./setup.sh
```

---

## 🚀 사용 방법

### 1. 로그인
- Frontend (http://localhost:5173) 접속
- 설치 시 생성한 Admin 계정으로 로그인

### 2. 봇 시작
- Dashboard에서 **"Start Bot"** 버튼 클릭
- 봇이 백그라운드에서 실시간 시장 모니터링 시작

### 3. 실시간 모니터링
- **Balance**: 잔고 및 수익률
- **Positions**: 현재 포지션 (진입가, 수익률, 목표가)
- **Recommendations**: AI 추천 코인 상위 5개
- **Statistics**: 총 거래 수, 승률, MDD

### 4. 수동 제어
- **Retrain Model**: 즉시 AI 모델 재학습
- **Update Recommendations**: 추천 코인 목록 갱신
- **Stop Bot**: 봇 중지

---

## 📚 주요 모듈 설명

### Backend (`/backend`)

#### `main.py`
- FastAPI 앱 초기화
- CORS 설정
- 라우터 등록 (Auth, Bot, Data)

#### `core/trading_bot.py`
- **TradingBot**: 핵심 매매 엔진
- 5단계 진입 필터링
- 4단계 청산 전략
- MDD 모니터링 (30초 주기)

#### `core/data_manager.py`
- **TradeMemory**: SQLite 매매 기록 관리
- **ModelLearner**: XGBoost 학습/예측
- **시간 가중치 학습**: 최근 500개 데이터 우선 학습

#### `core/auth.py`
- JWT 토큰 생성/검증
- 비밀번호 해싱 (bcrypt)

#### `core/database.py`
- 사용자 DB 관리 (SQLite)

#### `routers/`
- `auth.py`: 로그인/회원가입/프로필
- `bot.py`: 봇 시작/중지/재학습/설정
- `data.py`: 잔고/거래내역/추천코인/OHLCV
- `websocket.py`: 실시간 업데이트

### Frontend (`/frontend`)

#### `src/pages/Dashboard.tsx`
- 메인 대시보드
- 4개 섹션: 잔고, 설정, 성과, 추천

#### `src/contexts/AuthContext.tsx`
- JWT 인증 상태 관리
- LocalStorage 토큰 저장

#### `src/components/`
- `ControlPanel`: 봇 제어 버튼
- `ModelPerformance`: AI 성과 차트
- `TradingSettings`: 매매 파라미터 설정

---

## 🎓 Learning Mechanism

### 시간 가중치 학습 (Time-Weighted Learning)

```python
# 최근 500개 거래 데이터 사용
# Exponential Time Decay 가중치 적용

weight = max(0.1, exp(-0.02 * days_old))

# 예시:
# 오늘 거래: 가중치 1.00 (100%)
# 30일 전: 가중치 0.55 (55%)
# 60일 전: 가중치 0.30 (30%)
# 최소 가중치: 0.1 (완전히 무시 안 함)
```

### 학습 프로세스

```
매수 진입
   ↓
특징 저장 (16개 기술 지표)
   ↓
매도 청산
   ↓
결과 분류 (Class 0: 손실, Class 1: 보합, Class 2: 이익)
   ↓
TradeMemory DB 저장
   ↓
시간 가중치 계산
   ↓
XGBoost 재학습 (최신 데이터 우선)
   ↓
새로운 모델 저장
   ↓
다음 매매부터 업데이트된 모델 사용
```

---

## ⚙️ 고급 설정

### Trading Parameters (`backend/.env`)

```env
# Position Sizing
KELLY_FRACTION=0.5           # Kelly Criterion (0.25~1.0)
MAX_POSITION_SIZE=0.3        # 최대 포지션 크기 (총 자산의 30%)

# Entry Filters
MIN_VOLUME_24H=100000000     # 최소 거래량 (1억원)
BTC_CORRELATION_THRESHOLD=-0.03  # BTC 하락 임계값 (-3%)

# Exit Strategy
TARGET_PROFIT=0.03           # 목표 수익률 (3%)
STOP_LOSS=0.02              # 손절률 (2%)
TRAILING_STOP=0.015         # 트레일링 스톱 (1.5%)

# Risk Management
MDD_THRESHOLD=0.05          # MDD 임계값 (5%)
MDD_CHECK_INTERVAL=30       # MDD 체크 주기 (30초)
COOLDOWN_PERIOD=3600        # 손절 후 대기 시간 (1시간)
```

### Model Hyperparameters (`core/data_manager.py`)

```python
xgb_params = {
    'objective': 'multi:softprob',  # 3-class 분류
    'num_class': 3,
    'n_estimators': 100,           # 트리 개수
    'max_depth': 5,                # 트리 깊이
    'learning_rate': 0.1,          # 학습률
    'subsample': 0.8,              # 샘플링 비율
    'colsample_bytree': 0.8,       # 피처 샘플링
    'random_state': 42,
    'n_jobs': -1                   # 모든 CPU 코어 사용
}
```

---

## 🔒 보안 & 리스크 관리

### 1. JWT 인증
- Access Token 유효 기간: 24시간
- bcrypt 비밀번호 해싱
- CORS 허용 도메인 제한

### 2. API Key 보안
- `.env` 파일은 `.gitignore`에 포함
- 환경 변수로만 관리
- **절대 커밋하지 마세요!**

### 3. 거래 리스크
- **Demo Mode**: 기본적으로 실제 거래 안 함
- **Small Start**: 소액으로 시작 권장
- **Stop Loss**: 필수 설정
- **MDD Monitoring**: 자동 손실 제한

### 4. 실전 모드 활성화 (주의!)

`backend/core/trading_bot.py`에서 주석 해제:

```python
# _execute_buy()
order = self.exchange.buy_market_order(ticker, krw_amount)

# _execute_sell()
order = self.exchange.sell_market_order(ticker, amount)
```

**⚠️ 경고**: 실전 매매는 본인 책임입니다!

---

## 🧪 테스트

### Backend 테스트
```bash
cd backend
conda activate upBit

# 데이터 매니저 테스트
python -m pytest tests/test_data_manager.py

# 트레이딩 봇 테스트
python -m pytest tests/test_trading_bot.py
```

### API 문서
- http://localhost:8000/docs (Swagger UI)
- http://localhost:8000/redoc (ReDoc)

---

## 📁 프로젝트 구조

```
bitThumb_std/
├── backend/
│   ├── main.py                  # FastAPI 앱
│   ├── core/
│   │   ├── trading_bot.py       # 매매 엔진
│   │   ├── data_manager.py      # AI 학습
│   │   ├── auth.py              # JWT 인증
│   │   └── database.py          # 사용자 DB
│   ├── routers/
│   │   ├── auth.py              # 인증 API
│   │   ├── bot.py               # 봇 제어 API
│   │   ├── data.py              # 데이터 API
│   │   └── websocket.py         # WebSocket
│   ├── models/
│   │   └── schemas.py           # Pydantic 모델
│   ├── requirements.txt
│   ├── .env.example
│   └── create_admin.py
├── frontend/
│   ├── src/
│   │   ├── pages/
│   │   │   ├── Dashboard.tsx
│   │   │   └── Login.tsx
│   │   ├── components/
│   │   │   ├── ControlPanel.tsx
│   │   │   ├── ModelPerformance.tsx
│   │   │   └── TradingSettings.tsx
│   │   ├── contexts/
│   │   │   └── AuthContext.tsx
│   │   └── App.tsx
│   ├── package.json
│   └── vite.config.ts
├── docs/
│   ├── improvements/           # 개선 이력
│   ├── manual/                 # 사용 매뉴얼
│   └── ALGORITHM_ANALYSIS_2026.md
├── setup.bat                   # Windows 설치
├── setup.sh                    # macOS/Linux 설치
├── start_dev.bat              # Windows 실행
├── start_dev.sh               # macOS/Linux 실행
├── .env.example
├── .gitignore
└── README.md
```

---

## 📊 성과 분석

### 알고리즘 평가 (2026-02-03 기준)

| 항목 | 점수 | 등급 |
|------|------|------|
| Entry Strategy | 95/100 | A |
| Exit Strategy | 90/100 | A- |
| AI Learning | 82/100 | B+ |
| Risk Management | 92/100 | A- |
| **Overall** | **88/100** | **A-** |

### 주요 개선 사항 (v2.1.0)
1. ✅ 시간 가중치 학습 (125 → 500 거래)
2. ✅ 추세 필터 (EMA + 15분 변화)
3. ✅ 거래량 검증 (1억원 이상)
4. ✅ BTC 상관관계 관리
5. ✅ MDD 체크 주기 단축 (60s → 30s)
6. ✅ NaN 처리 개선 (median)
7. ✅ JWT 인증 시스템

---

## 🚧 향후 개선 사항

### High Priority
- [ ] **Ensemble Model**: XGBoost + LightGBM + RandomForest
- [ ] **Backtesting**: 과거 데이터로 전략 검증
- [ ] **Feature Importance**: 하위 10% 특징 제거

### Medium Priority
- [ ] **Multi-Ticker**: 여러 코인 동시 운용
- [ ] **Telegram Bot**: 매매 알림 및 원격 제어
- [ ] **Docker**: 컨테이너 기반 배포

### Low Priority
- [ ] **LSTM/Transformer**: 딥러닝 모델 추가
- [ ] **Sentiment Analysis**: 뉴스/SNS 감성 분석
- [ ] **Portfolio Optimization**: Markowitz 포트폴리오

---

## 📄 라이선스

MIT License - 자유롭게 사용, 수정, 배포 가능

---

## 🙏 크레딧

- **FastAPI**: Sebastián Ramírez
- **React**: Meta (Facebook)
- **XGBoost**: Tianqi Chen et al.
- **pyupbit**: Brayden Jo
- **Technical Indicators**: pandas-ta

---

## 📞 문의 & 기여

### Issues
프로젝트에 대한 질문이나 버그 리포트:
- GitHub Issues: https://github.com/Cov4w/auto-trading-bot/issues

### Pull Requests
기여는 언제나 환영합니다!
1. Fork the repository
2. Create your feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

### Support
- Email: covachoi708@gmail.com
- Discord: (추가 예정)

---

## 📖 추가 문서

- [알고리즘 상세 분석](docs/ALGORITHM_ANALYSIS_2026.md)
- [코드 검수 리포트](CODE_REVIEW_REPORT.md)
- [개선 사항 적용 내역](docs/improvements/13-improvements-20260203-applied.md)
- [로그인 시스템 설정](docs/LOGIN_SETUP.md)

---

<div align="center">

**Made with ❤️ for Algorithmic Trading**

*"In God we trust. All others must bring data."*
— W. Edwards Deming

### ⭐ Star this repo if you find it useful!

</div>
