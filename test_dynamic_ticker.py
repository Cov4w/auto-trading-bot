#!/usr/bin/env python3
"""
동적 티커 관리 테스트
"""

import sys
import os

# 프로젝트 루트를 Python 경로에 추가
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from core.trading_bot import TradingBot

def test_dynamic_ticker_management():
    """동적 티커 관리 로직 테스트"""
    print("=" * 60)
    print("🧪 Dynamic Ticker Management Test")
    print("=" * 60)

    # TradingBot 인스턴스 생성
    bot = TradingBot()

    # 초기 상태
    print(f"\n📊 Initial State:")
    print(f"   Tickers: {bot.tickers}")
    print(f"   Absence Count: {bot.ticker_absence_count}")

    # 시나리오 1: Top 5에 새로운 코인 진입
    print("\n" + "=" * 60)
    print("시나리오 1: Top 5에 새로운 코인 진입")
    print("=" * 60)

    mock_recs_1 = [
        {'ticker': 'BTC', 'score': 95.0, 'confidence': 0.85, 'features': {'rsi': 65.0}},
        {'ticker': 'ETH', 'score': 90.0, 'confidence': 0.80, 'features': {'rsi': 60.0}},
        {'ticker': 'XRP', 'score': 85.0, 'confidence': 0.75, 'features': {'rsi': 55.0}},
        {'ticker': 'ADA', 'score': 80.0, 'confidence': 0.70, 'features': {'rsi': 50.0}},
        {'ticker': 'SOL', 'score': 75.0, 'confidence': 0.65, 'features': {'rsi': 45.0}},
    ]

    bot._manage_tickers_dynamically(mock_recs_1)
    print(f"\n📊 After Update:")
    print(f"   Tickers: {bot.tickers}")
    print(f"   Absence Count: {bot.ticker_absence_count}")

    # 시나리오 2: BTC가 Top 5에서 빠짐 (1회차)
    print("\n" + "=" * 60)
    print("시나리오 2: BTC가 Top 5에서 빠짐 (1회차)")
    print("=" * 60)

    mock_recs_2 = [
        {'ticker': 'ETH', 'score': 92.0, 'confidence': 0.82, 'features': {'rsi': 62.0}},
        {'ticker': 'XRP', 'score': 88.0, 'confidence': 0.78, 'features': {'rsi': 58.0}},
        {'ticker': 'ADA', 'score': 83.0, 'confidence': 0.73, 'features': {'rsi': 53.0}},
        {'ticker': 'SOL', 'score': 78.0, 'confidence': 0.68, 'features': {'rsi': 48.0}},
        {'ticker': 'DOT', 'score': 74.0, 'confidence': 0.64, 'features': {'rsi': 44.0}},  # 신규 진입
    ]

    bot._manage_tickers_dynamically(mock_recs_2)
    print(f"\n📊 After Update:")
    print(f"   Tickers: {bot.tickers}")
    print(f"   Absence Count: {bot.ticker_absence_count}")
    print(f"   ℹ️ BTC should have absence count = 1")

    # 시나리오 3: BTC가 다시 Top 5에서 빠짐 (2회차 → 제거)
    print("\n" + "=" * 60)
    print("시나리오 3: BTC가 다시 Top 5에서 빠짐 (2회차 → 제거)")
    print("=" * 60)

    mock_recs_3 = [
        {'ticker': 'ETH', 'score': 94.0, 'confidence': 0.84, 'features': {'rsi': 64.0}},
        {'ticker': 'XRP', 'score': 90.0, 'confidence': 0.80, 'features': {'rsi': 60.0}},
        {'ticker': 'ADA', 'score': 85.0, 'confidence': 0.75, 'features': {'rsi': 55.0}},
        {'ticker': 'SOL', 'score': 80.0, 'confidence': 0.70, 'features': {'rsi': 50.0}},
        {'ticker': 'DOT', 'score': 76.0, 'confidence': 0.66, 'features': {'rsi': 46.0}},
    ]

    bot._manage_tickers_dynamically(mock_recs_3)
    print(f"\n📊 After Update:")
    print(f"   Tickers: {bot.tickers}")
    print(f"   Absence Count: {bot.ticker_absence_count}")
    print(f"   ℹ️ BTC should be removed from tickers")

    # 시나리오 4: ETH에 포지션 추가 후 Top 5 이탈 (제거 안 됨 확인)
    print("\n" + "=" * 60)
    print("시나리오 4: ETH에 포지션 추가 후 Top 5 이탈 (제거 방지)")
    print("=" * 60)

    # ETH 포지션 시뮬레이션
    bot.positions['ETH'] = {
        'entry_price': 3000,
        'amount': 0.1,
        'entry_time': '2026-02-04 10:00:00'
    }
    print(f"   ✅ Added ETH position: {bot.positions['ETH']}")

    mock_recs_4 = [
        {'ticker': 'XRP', 'score': 92.0, 'confidence': 0.82, 'features': {'rsi': 62.0}},
        {'ticker': 'ADA', 'score': 87.0, 'confidence': 0.77, 'features': {'rsi': 57.0}},
        {'ticker': 'SOL', 'score': 82.0, 'confidence': 0.72, 'features': {'rsi': 52.0}},
        {'ticker': 'DOT', 'score': 78.0, 'confidence': 0.68, 'features': {'rsi': 48.0}},
        {'ticker': 'AVAX', 'score': 74.0, 'confidence': 0.64, 'features': {'rsi': 44.0}},
    ]

    # ETH 2회 연속 이탈 시키기
    bot._manage_tickers_dynamically(mock_recs_4)
    print(f"\n📊 After 1st Absence:")
    print(f"   Tickers: {bot.tickers}")
    print(f"   Absence Count: {bot.ticker_absence_count}")

    bot._manage_tickers_dynamically(mock_recs_4)
    print(f"\n📊 After 2nd Absence:")
    print(f"   Tickers: {bot.tickers}")
    print(f"   Absence Count: {bot.ticker_absence_count}")
    print(f"   ℹ️ ETH should still be in tickers (has active position)")

    # 최종 결과
    print("\n" + "=" * 60)
    print("✅ Test Complete!")
    print("=" * 60)
    print(f"Final Tickers: {bot.tickers}")
    print(f"Final Positions: {list(bot.positions.keys())}")
    print(f"Final Absence Count: {bot.ticker_absence_count}")

if __name__ == "__main__":
    test_dynamic_ticker_management()
