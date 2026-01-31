"""
Streamlit Dashboard
===================
Self-Evolving Trading System의 웹 대시보드

Features:
- 실시간 시세 및 캔들스틱 차트
- AI 학습 진행도 모니터링
- 매매 성과 분석
- 봇 제어 인터페이스
"""

import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
from datetime import datetime, timedelta
import time
import os

from trading_bot import TradingBot
from data_manager import TradeMemory

# Page Configuration
st.set_page_config(
    page_title="🤖 자가 진화 트레이딩 봇",
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for Premium Design
st.markdown("""
<style>
    /* Import Modern Font */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
    
    /* Global Styles */
    * {
        font-family: 'Inter', sans-serif;
    }
    
    /* Main Container */
    .main {
        background: linear-gradient(135deg, #0f0c29 0%, #302b63 50%, #24243e 100%);
        color: white;
    }
    
    /* Metric Cards */
    .metric-card {
        background: rgba(255, 255, 255, 0.05);
        backdrop-filter: blur(10px);
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 16px;
        padding: 20px;
        margin: 10px 0;
        box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
        transition: transform 0.3s ease, box-shadow 0.3s ease;
    }
    
    .metric-card:hover {
        transform: translateY(-5px);
        box-shadow: 0 12px 48px rgba(0, 0, 0, 0.5);
    }
    
    /* Headers */
    h1, h2, h3 {
        background: linear-gradient(90deg, #00d4ff 0%, #7b2ff7 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-weight: 700;
    }
    
    /* Buttons */
    .stButton > button {
        background: linear-gradient(90deg, #00d4ff 0%, #7b2ff7 100%);
        color: white;
        border: none;
        border-radius: 12px;
        padding: 12px 24px;
        font-weight: 600;
        transition: all 0.3s ease;
    }
    
    .stButton > button:hover {
        transform: scale(1.05);
        box-shadow: 0 8px 24px rgba(123, 47, 247, 0.4);
    }
    
    /* Status Indicators */
    .status-running {
        color: #00ff88;
        font-weight: 600;
        animation: pulse 2s infinite;
    }
    
    .status-stopped {
        color: #ff4444;
        font-weight: 600;
    }
    
    @keyframes pulse {
        0%, 100% { opacity: 1; }
        50% { opacity: 0.6; }
    }
    
    /* Sidebar */
    .css-1d391kg {
        background: rgba(0, 0, 0, 0.3);
    }
</style>
""", unsafe_allow_html=True)

# Initialize Shared Bot Instance (Singleton)
@st.cache_resource
def get_bot():
    """트레이딩 봇 싱글톤 인스턴스 반환"""
    return TradingBot()

bot = get_bot()
memory = bot.memory  # 봇 내부의 memory 객체 사용

def render_header():
    """헤더 렌더링"""
    col1, col2 = st.columns([3, 1])
    
    with col1:
        st.title("🤖 Self-Evolving Trading System")
        st.caption("Renaissance Technologies Style • Powered by AI & Continuous Learning")
    
    with col2:
        # 실시간 시간
        st.metric("🕐 현재 시각", datetime.now().strftime("%H:%M:%S"))

def render_control_panel():
    """제어 패널"""
    st.sidebar.header("⚙️ Control Center")
    
    # Exchange Selection
    current_exchange = bot.exchange_name.capitalize()
    selected_exchange = st.sidebar.selectbox(
        "Exchange",
        ["Bithumb", "Upbit"],
        index=0 if current_exchange == "Bithumb" else 1
    )
    
    # Exchange 변경 시 봇 재초기화
    if selected_exchange.lower() != bot.exchange_name:
        os.environ["EXCHANGE"] = selected_exchange.lower()
        # 기존 봇 중지 및 캐시 초기화
        if bot.is_running:
            bot.stop()
        st.cache_resource.clear()
        st.rerun()
    
    status = bot.get_status()
    
    # 봇 상태 표시
    if status['is_running']:
        st.sidebar.markdown('<p class="status-running">● RUNNING</p>', unsafe_allow_html=True)
    else:
        st.sidebar.markdown('<p class="status-stopped">● STOPPED</p>', unsafe_allow_html=True)
    
    st.sidebar.divider()
    
    # 시작/중지 버튼
    col1, col2 = st.sidebar.columns(2)
    
    with col1:
        if st.button("▶️ START", use_container_width=True, disabled=status['is_running']):
            bot.start()
            st.rerun()
    
    with col2:
        if st.button("⏸️ STOP", use_container_width=True, disabled=not status['is_running']):
            bot.stop()
            st.rerun()
    
    st.sidebar.divider()
    
    # 강제 재학습 버튼
    if st.sidebar.button("🎓 지금 모델 재학습", use_container_width=True):
        with st.spinner("모델 재학습 중..."):
            bot.force_retrain()
            st.success("✅ 재학습 완료!")
            time.sleep(1)
            st.rerun()
    
    st.sidebar.divider()
    
    # 🔥 AI 코인 추천 업데이트 (Async)
    if status.get('is_updating_recommendations', False):
        st.sidebar.info("🔄 AI가 시장 분석 중... (백그라운드)")
    else:
        if st.sidebar.button("🔄 코인 추천 업데이트", use_container_width=True):
            bot.update_recommendations_async()
            st.rerun()
    
    st.sidebar.divider()
    
    
    # 💰 계좌 정보
    st.sidebar.subheader("💰 계좌 정보")
    
    balance_info = bot.get_account_balance()
    
    if balance_info['api_ok']:
        st.sidebar.metric("주문 가능 금액", f"{balance_info['krw_balance']:,.0f} KRW")
        st.sidebar.metric("총 평가액", f"{balance_info['total_value']:,.0f} KRW")
        
        if balance_info['holdings']:
            st.sidebar.caption("📦 보유 코인")
            for holding in balance_info['holdings']:
                st.sidebar.text(f"{holding['ticker']}: {holding['amount']:.4f}")
                st.sidebar.caption(f"  {holding['value']:,.0f} KRW")
    else:
        st.sidebar.warning("⚠️ API 키가 유효하지 않습니다")
        st.sidebar.caption("빗썸에서 API 키를 재발급 받으세요")
    
    # 설정 정보 (실시간 조정 가능)
    st.sidebar.subheader("📊 Configuration")
    
    # 1. AI Selection Toggle
    # use_ai = st.sidebar.checkbox("AI Coin Selection", value=status['use_ai_selection'])
    # if use_ai != bot.use_ai_selection:
    #     bot.use_ai_selection = use_ai
    
    # 2. Trade Amount (KRW)
    new_amount = st.sidebar.number_input(
        "Trade Amount (KRW)",
        min_value=1000,
        max_value=1000000,
        value=int(bot.trade_amount),
        step=1000,
        help="주문당 매수 금액 (업비트 최소 5,000원 권장)",
        key="input_trade_amount"
    )
    if new_amount != bot.trade_amount:
        bot.trade_amount = new_amount
        st.toast(f"✅ 매수 금액 업데이트: {new_amount:,.0f} KRW")

    # 3. Target & Stop Loss (With Presets)
    st.sidebar.caption("🎯 매매 전략 (빠른 설정)")
    col1, col2, col3 = st.sidebar.columns(3)
    
    if col1.button("⚡ 초단타", help="익절 0.8% / 손절 1.5%", use_container_width=True, key="btn_preset_scalp"):
        bot.target_profit = 0.008
        bot.stop_loss = 0.015
        st.rerun()
        
    if col2.button("🛡️ 스윙", help="익절 3.0% / 손절 5.0%", use_container_width=True, key="btn_preset_swing"):
        bot.target_profit = 0.03
        bot.stop_loss = 0.05
        st.rerun()
        
    if col3.button("🚀 불장", help="익절 10% / 손절 10%", use_container_width=True, key="btn_preset_bull"):
        bot.target_profit = 0.1
        bot.stop_loss = 0.1
        st.rerun()

    # Manual Fine-tuning
    new_target = st.sidebar.number_input(
        "목표 수익률 (Target %)",
        min_value=0.5,
        max_value=100.0,
        value=float(bot.target_profit * 100),
        step=0.1,
        format="%.1f",
        key="input_target_profit"
    )
    if abs((new_target/100) - bot.target_profit) > 0.0001:
        bot.target_profit = new_target / 100
    
    new_stop = st.sidebar.number_input(
        "손절 제한 (Stop Loss %)",
        min_value=0.3,  # 🔧 0.5 → 0.3 (더 타이트한 손절 허용)
        max_value=50.0,
        value=float(bot.stop_loss * 100),
        step=0.1,
        format="%.1f",
        key="input_stop_loss"
    )
    if abs((new_stop/100) - bot.stop_loss) > 0.0001:
        bot.stop_loss = new_stop / 100
    
    new_rebuy = st.sidebar.number_input(
        "재매수 하락폭 (Rebuy Threshold %)",
        min_value=0.0,
        max_value=10.0,
        value=float(bot.rebuy_threshold * 100),
        step=0.1,
        format="%.1f",
        help="익절 후 가격이 이만큼 하락해야 재매수 허용 (1.5% 권장)",
        key="input_rebuy_threshold"
    )
    if abs((new_rebuy/100) - bot.rebuy_threshold) > 0.0001:
        bot.rebuy_threshold = new_rebuy / 100
        
    st.sidebar.divider()
    st.sidebar.text(f"Active Tickers: {', '.join(status['tickers'])}")

def render_ai_metrics():
    """AI 학습 메트릭"""
    st.header("🧠 AI 학습 지표")
    
    status = bot.get_status()
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        accuracy = status['model_accuracy']
        delta = "+5.2%" if accuracy > 0.5 else None  # 예시
        st.metric(
            label="🎯 모델 정확도",
            value=f"{accuracy:.2%}",
            delta=delta
        )
    
    with col2:
        st.metric(
            label="📚 학습 데이터 수",
            value=f"{status['total_learning_samples']:,}",
            delta=f"+{bot.retrain_threshold}" if status['total_trades'] > 0 else None
        )
    
    with col3:
        st.metric(
            label="🏆 승률 (전체)",
            value=f"{status['win_rate']:.1f}%",
            delta=f"{status['win_rate'] - 50:.1f}%" if status['total_trades'] > 0 else None
        )
    
    with col4:
        last_trained = status.get('last_trained')
        if last_trained:
            trained_time = datetime.fromisoformat(last_trained)
            time_ago = datetime.now() - trained_time
            st.metric(
                label="🕐 마지막 학습",
                value=f"{time_ago.seconds // 3600}h ago"
            )
        else:
            st.metric(label="🕐 마지막 학습", value="없음")

def render_performance_chart():
    """성능 이중 축 차트"""
    st.header("📈 수익률 & 학습 진행도")
    
    # 매매 기록 조회
    import sqlite3
    conn = sqlite3.connect(memory.db_path)
    df_trades = pd.read_sql_query("""
        SELECT 
            id,
            timestamp,
            profit_rate,
            is_profitable,
            model_confidence
        FROM trades
        WHERE status = 'closed'
        ORDER BY timestamp
        """, conn)
    conn.close()
    
    if len(df_trades) == 0:
        st.info("📊 매매 데이터가 아직 없습니다. 봇을 시작하면 데이터가 누적됩니다.")
        return
    
    # 누적 수익률 계산
    df_trades['cumulative_return'] = (1 + df_trades['profit_rate']).cumprod() - 1
    
    # 승률 계산 (이동 평균)
    df_trades['win_rate_ma'] = df_trades['is_profitable'].rolling(window=10, min_periods=1).mean() * 100
    
    # Plotly 이중 축 차트
    fig = make_subplots(
        rows=1, cols=1,
        specs=[[{"secondary_y": True}]]
    )
    
    # 누적 수익률
    fig.add_trace(
        go.Scatter(
            x=df_trades['id'],
            y=df_trades['cumulative_return'] * 100,
            name="Cumulative Return (%)",
            line=dict(color='#00d4ff', width=3),
            fill='tozeroy',
            fillcolor='rgba(0, 212, 255, 0.1)'
        ),
        secondary_y=False
    )
    
    # 승률 이동평균
    fig.add_trace(
        go.Scatter(
            x=df_trades['id'],
            y=df_trades['win_rate_ma'],
            name="Win Rate MA-10 (%)",
            line=dict(color='#7b2ff7', width=3, dash='dot')
        ),
        secondary_y=True
    )
    
    # 레이아웃
    fig.update_layout(
        title="성과 추적: 수익률 vs. 승률",
        xaxis_title="매매 번호",
        template="plotly_dark",
        hovermode='x unified',
        height=400,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        )
    )
    
    fig.update_yaxes(title_text="Cumulative Return (%)", secondary_y=False)
    fig.update_yaxes(title_text="Win Rate (%)", secondary_y=True)
    
    st.plotly_chart(fig, use_container_width=True)

def render_candlestick_chart():
    """캔들스틱 차트 with 매매 시그널"""
    st.header("📊 실시간 시세 & 매매 신호")
    
    tickers = bot.tickers
    
    if not tickers:
        st.info("선택된 코인이 없습니다.")
        return
        
    for ticker in tickers:
        with st.container():
            st.subheader(f"📈 {ticker} Chart")
            
            # 최근 데이터 (일봉)
            df = bot.exchange.get_ohlcv(ticker)
        
            if df is None or len(df) == 0:
                st.error(f"❌ {ticker}: 시장 데이터를 불러올 수 없습니다")
                st.divider()
                continue
            
            # 캔들스틱 차트
            fig = go.Figure()
            
            fig.add_trace(go.Candlestick(
                x=df.index,
                open=df['open'],
                high=df['high'],
                low=df['low'],
                close=df['close'],
                name=ticker,
                increasing_line_color='#00ff88',
                decreasing_line_color='#ff4444'
            ))
            
            # 매수/매도 시그널 마커 추가 (해당 티커만)
            import sqlite3
            conn = sqlite3.connect(memory.db_path)
            signals = pd.read_sql_query(f"""
                SELECT timestamp, entry_price, exit_price, model_confidence, is_profitable
                FROM trades
                WHERE status = 'closed' AND ticker = '{ticker}'
                ORDER BY timestamp DESC
                LIMIT 20
            """, conn)
            conn.close()
            
            if len(signals) > 0:
                signals['timestamp'] = pd.to_datetime(signals['timestamp'])
                
                # 매수 마커
                fig.add_trace(go.Scatter(
                    x=signals['timestamp'],
                    y=signals['entry_price'],
                    mode='markers',
                    marker=dict(
                        symbol='triangle-up',
                        size=15,
                        color='#00d4ff',
                        line=dict(color='white', width=2)
                    ),
                    name='Buy Signal',
                    text=[f"Confidence: {c:.1%}" for c in signals['model_confidence']],
                    hovertemplate='<b>BUY</b><br>Price: %{y:,.0f}<br>%{text}<extra></extra>'
                ))
                
                # 매도 마커
                colors = ['#00ff88' if p else '#ff4444' for p in signals['is_profitable']]
                fig.add_trace(go.Scatter(
                    x=signals['timestamp'],
                    y=signals['exit_price'],
                    mode='markers',
                    marker=dict(
                        symbol='triangle-down',
                        size=15,
                        color=colors,
                        line=dict(color='white', width=2)
                    ),
                    name='Sell Signal',
                    hovertemplate='<b>SELL</b><br>Price: %{y:,.0f}<extra></extra>'
                ))
            
            # 레이아웃
            fig.update_layout(
                title=f"{ticker}/KRW - 일봉 차트",
                xaxis_title="시간",
                yaxis_title="가격 (KRW)",
                template="plotly_dark",
                height=500,
                xaxis_rangeslider_visible=False
            )
            
            st.plotly_chart(fig, use_container_width=True)
            st.divider()

def render_recent_trades():
    """최근 매매 내역"""
    st.header("📜 최근 매매 내역")
    
    import sqlite3
    conn = sqlite3.connect(memory.db_path)
    df = pd.read_sql_query("""
        SELECT 
            timestamp,
            entry_price,
            exit_price,
            profit_rate,
            is_profitable,
            model_confidence
        FROM trades
        WHERE status = 'closed'
        ORDER BY timestamp DESC
        LIMIT 10
    """, conn)
    conn.close()
    
    if len(df) == 0:
        st.info("아직 완료된 매매가 없습니다.")
        return
    
    # 데이터 포맷팅
    df['timestamp'] = pd.to_datetime(df['timestamp']).dt.strftime("%m-%d %H:%M")
    df['profit_rate'] = df['profit_rate'].apply(lambda x: f"{x*100:+.2f}%")
    df['model_confidence'] = df['model_confidence'].apply(lambda x: f"{x:.1%}")
    df['result'] = df['is_profitable'].apply(lambda x: "✅ Profit" if x else "❌ Loss")
    
    # 컬럼 이름 변경
    df = df.rename(columns={
        'timestamp': 'Time',
        'entry_price': 'Entry',
        'exit_price': 'Exit',
        'profit_rate': 'P/L',
        'model_confidence': 'Confidence',
        'result': 'Result'
    })
    
    # 표시
    st.dataframe(
        df[['Time', 'Entry', 'Exit', 'P/L', 'Confidence', 'Result']],
        use_container_width=True,
        hide_index=True
    )

def render_current_position():
    """현재 포지션 정보"""
    status = bot.get_status()
    positions = status.get('positions', {})
    
    ifPositions = len(positions) > 0
    
    if ifPositions:
        st.info(f"🔵 **현재 {len(positions)}개 포지션 보유 중**")
        
        for ticker, position in list(positions.items()):
            with st.container():
                st.markdown(f"#### 🏷️ {ticker}")
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    st.metric("진입 가격", f"{position['entry_price']:,.0f} KRW")
                
                with col2:
                    current_price = bot.exchange.get_current_price(ticker)
                    if current_price and current_price > 0:
                        profit = (current_price - position['entry_price']) / position['entry_price']
                        st.metric(
                            "현재 수익률",
                            f"{profit*100:+.2f}%",
                            delta=f"{current_price:,.0f} KRW"
                        )
                    else:
                        st.metric(
                            "현재 수익률",
                            "❌ 조회 실패",
                            delta="Price API Error"
                        )
                
                with col3:
                    entry_time = position.get('entry_time')
                    if entry_time:
                        duration = datetime.now() - entry_time
                        st.metric("보유 시간", f"{duration.seconds // 60} 분")
                st.divider()
    else:
        st.success("✅ 보유 포지션 없음")

def render_coin_recommendations():
    """🔥 AI 추천 코인 패널"""
    st.header("🎯 AI 추천 코인 (상위 5개)")
    
    status = bot.get_status()
    
    if not status['use_ai_selection']:
        st.warning("⚠️ AI Coin Selection is disabled. Enable it in .env (USE_AI_COIN_SELECTION=true)")
        return
    
    recommended_coins = status.get('recommended_coins', [])
    
    if not recommended_coins:
        st.info("📊 사이드바의 '🔄 코인 추천 업데이트' 버튼을 눌러 코인을 분석하세요.")
        return
    
    # 추천 코인 테이블 생성
    recommendations_data = []
    
    for i, rec in enumerate(recommended_coins, 1):
        # 추천 상태 이모지
        recommend_emoji = "✅" if rec['recommendation'] else "⚠️"
        
        recommendations_data.append({
            "순위": f"#{i}",
            "코인": rec['ticker'],
            "점수": f"{rec['score']:.1f}/100",
            "AI 확신도": f"{rec['confidence']:.1%}",
            "RSI": f"{rec['features']['rsi']:.1f}",
            "BB 위치": f"{rec['features']['bb_position']:.2f}",
            "현재가": f"{rec['current_price']:,.0f} KRW" if rec['current_price'] else "N/A",
            "상태": recommend_emoji
        })
    
    df_recommendations = pd.DataFrame(recommendations_data)
    
    # 스타일링된 테이블
    st.dataframe(
        df_recommendations,
        use_container_width=True,
        hide_index=True,
        column_config={
            "점수": st.column_config.ProgressColumn(
                "점수",
                help="AI 종합 점수 (100점 만점)",
                format="%s",
                min_value=0,
                max_value=100,
            ),
        }
    )
    
    # 추천 요약
    col1, col2, col3 = st.columns(3)
    
    with col1:
        strong_buy_count = sum(1 for r in recommended_coins if r['score'] >= 80)
        st.metric("🔥 강력 매수", f"{strong_buy_count}")
    
    with col2:
        avg_confidence = sum(r['confidence'] for r in recommended_coins) / len(recommended_coins)
        st.metric("📈 평균 확신도", f"{avg_confidence:.1%}")
    
    with col3:
        recommend_count = sum(1 for r in recommended_coins if r['recommendation'])
        st.metric("✅ 추천", f"{recommend_count}/5")
    
    st.divider()
    
    # 🔥 코인 선택 버튼
    st.subheader("💰 매매할 코인 선택")
    st.caption("아래 버튼을 클릭하여 원하는 코인으로 자동 매매를 시작하세요")
    
    cols = st.columns(5)
    for i, rec in enumerate(recommended_coins):
        with cols[i]:
            ticker = rec['ticker']
            score = rec['score']
            confidence = rec['confidence']
            
            # 현재 선택된 코인 표시
            is_selected = (ticker in status['tickers'])
            
            if is_selected:
                st.success(f"✅ **{ticker}**\n현재 감시 중")
            else:
                st.info(f"**{ticker}**\n점수: {score:.0f}\n확신도: {confidence:.0%}")
            
            # 매매 시작 버튼
            if st.button(
                f"🚫 해제" if is_selected else f"🚀 추가",
                key=f"select_{ticker}",
                use_container_width=True,
                type="primary" if is_selected else "secondary"
            ):
                # 티커 토글
                bot.toggle_ticker(ticker)
                
                if is_selected:
                     st.warning(f"➖ {ticker} 제외됨")
                else:
                     st.success(f"➕ {ticker} 추가됨")
                
                time.sleep(0.5)
                st.rerun()

def main():
    """메인 함수"""
    try:
        # 헤더
        render_header()
        
        # 제어 패널 (사이드바)
        render_control_panel()
        
        # 현재 포지션
        render_current_position()
        
        st.divider()
        
        # 🔥 AI 추천 코인
        render_coin_recommendations()
        
        st.divider()
        
        # AI 메트릭
        render_ai_metrics()
        
        st.divider()
        
        # 성능 차트
        render_performance_chart()
        
        st.divider()
        
        # 캔들스틱 차트
        render_candlestick_chart()
        
        st.divider()
        
        # 최근 매매
        render_recent_trades()
        
        # 자동 새로고침 (10초마다)
        if bot.get_status()['is_running']:
            time.sleep(10)
            st.rerun()
            
    except Exception as e:
        st.error(f"❌ An error occurred: {e}")
        st.exception(e)

if __name__ == "__main__":
    main()
