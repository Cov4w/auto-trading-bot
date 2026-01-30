# 🚀 Quick Start Guide - AI Coin Selection

## 🎯 새로운 기능: AI 기반 코인 자동 선택

빗썸 상장 20개 주요 코인을 실시간 분석하여 **승률이 가장 높을 것으로 예측되는 상위 5개 코인**을 AI가 자동으로 추천합니다!

---

## ✨ 주요 기능

### 1. 자동 코인 분석
- 20개 주요 코인을 동시에 분석
- AI 확신도, RSI, 볼린저밴드, 거래량 등 종합 평가
- **100점 만점** 종합 점수 산출

### 2. 실시간 추천
- 매매 주기마다 가장 유망한 코인 자동 선택
- 고정 티커가 아닌 **시장 상황에 따른 동적 선택**

### 3. 과거 승률 반영
- 각 코인별 과거 매매 승률 데이터 활용
- 실전 데이터 기반 점수 조정

---

## 🔧 설정 방법

### 1. `.env` 파일 설정

```bash
# AI 코인 선택 활성화
USE_AI_COIN_SELECTION=true

# 기본 티커 (AI 실패 시 폴백)
TICKER=BTC
```

### 2. 추천 코인 분석 대상

현재 20개 코인이 분석 대상입니다 (`coin_selector.py`):

```python
CANDIDATE_COINS = [
    "BTC", "ETH", "XRP", "SOL", "DOGE",
    "ADA", "AVAX", "MATIC", "DOT", "LINK",
    "UNI", "ATOM", "NEAR", "APT", "ARB",
    "OP", "SUI", "STX", "INJ", "TIA"
]
```

원하는 코인을 추가/제거할 수 있습니다!

---

## 📊 대시보드 사용법

### 1. 봇 시작
1. Streamlit 대시보드 실행: `streamlit run app.py`
2. 왼쪽 사이드바에서 **"▶️ START"** 클릭

### 2. 코인 추천 업데이트
- 사이드바 **"🔄 Update Coin Recommendations"** 버튼 클릭
- AI가 20개 코인을 실시간 분석
- **상위 5개** 추천 코인 표시

### 3. 추천 결과 보기

**AI Recommended Coins (Top 5)** 패널에서 확인:

| 컬럼 | 설명 |
|------|------|
| **Rank** | 순위 (#1 ~ #5) |
| **Coin** | 코인 티커 |
| **Score** | AI 종합 점수 (0~100점) |
| **AI Confidence** | XGBoost 상승 확률 |
| **RSI** | 상대강도지수 (과매도 포착) |
| **BB Position** | 볼린저밴드 위치 (0~1) |
| **Price** | 현재 가격 |
| **Status** | ✅ 강력 추천 / ⚠️ 주의 |

### 4. 자동 매매
- 봇이 실행 중일 때, 매매 주기마다 **#1 코인에 자동 진입**
- 고정 BTC가 아닌 AI가 선택한 최적 코인으로 매매

---

## 🎓 점수 계산 방식

### 종합 점수 구성 (100점 만점)

1. **AI 확신도 (40점)**
   - XGBoost 모델의 상승 예측 확률
   - 높을수록 AI가 확신하는 상승 패턴

2. **기술적 지표 강도 (30점)**
   - RSI < 30: 강한 과매도 (10점)
   - BB 하단 20% 이내: 반등 기회 (10점)
   - MACD 골든 크로스: 상승 전환 (10점)

3. **과거 승률 (20점)**
   - 해당 코인의 과거 매매 성공률
   - 승률 100% = 20점

4. **거래량/변동성 (10점)**
   - 거래량 비율 (5점)
   - ATR 변동성 (5점)

### 추천 기준

✅ **강력 추천 조건**:
- AI 상승 예측 (prediction == 1)
- 확신도 > 60%
- 종합 점수 > 60점
- RSI < 40 OR BB 하단 30% 이내

---

## 🔥 실전 사용 예시

### 시나리오 1: 아침 장 시작
```bash
1. 대시보드 접속
2. "🔄 Update Coin Recommendations" 클릭
3. AI 분석 결과:
   #1 DOGE (Score: 85.2, Confidence: 78%)
   #2 XRP (Score: 78.1, Confidence: 71%)
   ...
4. "▶️ START" 클릭 → DOGE에 자동 매수 진입
```

### 시나리오 2: 60초마다 자동 재평가
```bash
- 봇 실행 중
- 포지션 없는 상태
- 60초마다 AI가 최적 코인 재분석
- 조건 만족 시 즉시 매수
```

### 시나리오 3: 수동 분석
```bash
- 봇 중지 상태
- "🔄 Update" 버튼으로 수동 분석
- 추천 결과만 확인하고 직접 매매
```

---

## ⚙️ 고급 설정

### 1. 분석 대상 코인 변경

`coin_selector.py` 파일 수정:

```python
CANDIDATE_COINS = [
    "BTC", "ETH",  # 메이저만
    # 또는
    "DOGE", "SHIB", "PEPE"  # 밈코인만
]
```

### 2. 점수 가중치 조정

`coin_selector.py`의 `_calculate_score()` 함수:

```python
ai_score = confidence * 50  # AI 비중 증가 (40 → 50)
```

### 3. 추천 개수 변경

`trading_bot.py`:

```python
self.recommended_coins = self.coin_selector.get_top_recommendations(top_n=10)
```

---

## 📈 성과 추적

### Dashboard에서 확인
- **AI Recommended Coins**: 각 코인별 점수 및 추천 상태
- **Strong Buy**: 80점 이상 강력 매수 코인 개수
- **Avg Confidence**: 평균 AI 확신도
- **Recommended**: 실제 매수 추천 코인 개수 (5개 중)

### 코인별 승률 분석
```sql
SELECT ticker, 
       COUNT(*) as trades,
       AVG(is_profitable) as win_rate
FROM trades
WHERE status = 'closed'
GROUP BY ticker
ORDER BY win_rate DESC;
```

---

## 🚨 주의사항

1. **초기 학습 필요**
   - 모델이 학습되기 전에는 추천 정확도가 낮을 수 있음
   - 최소 30~50건 매매 후 성능 향상

2. **시장 변동성**
   - 급등/급락 시 AI 예측 외의 요인 고려 필요
   - 손절 설정은 반드시 유지

3. **API 호출 제한**
   - 20개 코인 동시 분석 시 API 호출 증가
   - 빗썸 API Rate Limit 주의

---

## 🎯 추천 전략

### Conservative (보수적)
```env
MODEL_CONFIDENCE_THRESHOLD=0.75  # 높은 확신도만
TARGET_PROFIT=0.015              # 1.5% 목표
STOP_LOSS=0.01                   # 1% 손절
```

### Aggressive (공격적)
```env
MODEL_CONFIDENCE_THRESHOLD=0.6   # 낮은 문턱
TARGET_PROFIT=0.03               # 3% 목표
STOP_LOSS=0.025                  # 2.5% 손절
```

### Balanced (균형)
```env
MODEL_CONFIDENCE_THRESHOLD=0.7   # 기본값
TARGET_PROFIT=0.02               # 2% 목표
STOP_LOSS=0.02                   # 2% 손절
```

---

## 🔄 자주 묻는 질문 (FAQ)

**Q1. 추천 코인이 안 나와요**
- 모델 학습이 안 되었을 수 있음 → 초기 학습 대기
- 모든 코인이 조건 미달 → 시장 상황이 불안정

**Q2. #1 코인이 계속 바뀌나요?**
- 네! 60초마다 재평가하여 가장 유망한 코인 선택
- 시장은 계속 변하므로 동적 선택이 유리

**Q3. 수동으로 티커 고정하고 싶어요**
```env
USE_AI_COIN_SELECTION=false
TICKER=BTC  # BTC만 거래
```

**Q4. 추천 로직을 이해하고 싶어요**
- `coin_selector.py` 파일의 주석 참고
- `_calculate_score()` 함수에 상세 설명

---

## 🚀 다음 단계

1. ✅ 의존성 설치: `pip install -r requirements.txt`
2. ✅ `.env` 설정: `USE_AI_COIN_SELECTION=true`
3. ✅ 대시보드 실행: `streamlit run app.py`
4. ✅ 추천 업데이트: 사이드바 버튼 클릭
5. ✅ 봇 시작: START 버튼

---

**Happy Trading! 🎉**

AI가 24/7 시장을 모니터링하며 최적의 매매 기회를 찾아드립니다.
