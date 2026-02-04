#!/usr/bin/env python3
"""
동적 티커 관리 테스트 (출처 범위 추적 포함)
"""

import sys
import os

# 프로젝트 루트를 Python 경로에 추가
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from core.trading_bot import TradingBot

def test_dynamic_ticker_management():
    """동적 티커 관리 로직 테스트 (출처 범위 추적)"""
    print("=" * 80)
    print("🧪 Dynamic Ticker Management Test (Origin Range Tracking)")
    print("=" * 80)

    # TradingBot 인스턴스 생성
    bot = TradingBot()

    # 초기 상태
    print(f"\n📊 Initial State:")
    print(f"   Tickers: {bot.tickers}")
    print(f"   Absence Count: {bot.ticker_absence_count}")
    print(f"   Origin Ranges: {bot.ticker_origin_range}")

    # 시나리오 1: 범위 0-50에서 BTC, ETH, XRP 추가
    print("\n" + "=" * 80)
    print("시나리오 1: 범위 0-50 스캔 - BTC, ETH, XRP 추가")
    print("=" * 80)

    # coin_selector.scan_index 시뮬레이션 (0-50)
    bot.coin_selector.scan_index = 50
    bot.coin_selector.batch_size = 50

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
    print(f"   Origin Ranges: {bot.ticker_origin_range}")
    print(f"   Absence Count: {bot.ticker_absence_count}")

    # 시나리오 2: 범위 50-100 스캔 - CTC, BTC 추가 (XRP는 체크 안 됨)
    print("\n" + "=" * 80)
    print("시나리오 2: 범위 50-100 스캔 - CTC, BTC 추가 (다른 범위 코인은 체크 안 됨)")
    print("=" * 80)

    # coin_selector.scan_index 시뮬레이션 (50-100)
    bot.coin_selector.scan_index = 100

    mock_recs_2 = [
        {'ticker': 'CTC', 'score': 92.0, 'confidence': 0.82, 'features': {'rsi': 62.0}},
        {'ticker': 'BTC', 'score': 88.0, 'confidence': 0.78, 'features': {'rsi': 58.0}},
        {'ticker': 'MATIC', 'score': 83.0, 'confidence': 0.73, 'features': {'rsi': 53.0}},
        {'ticker': 'AVAX', 'score': 78.0, 'confidence': 0.68, 'features': {'rsi': 48.0}},
        {'ticker': 'DOT', 'score': 74.0, 'confidence': 0.64, 'features': {'rsi': 44.0}},
    ]

    bot._manage_tickers_dynamically(mock_recs_2)
    print(f"\n📊 After Update:")
    print(f"   Tickers: {bot.tickers}")
    print(f"   Origin Ranges: {bot.ticker_origin_range}")
    print(f"   Absence Count: {bot.ticker_absence_count}")
    print(f"   ℹ️ XRP, ETH, ADA, SOL (from range 0-50) should NOT have absence count")

    # 시나리오 3: 다시 범위 50-100 스캔 - CTC 이탈 (1회차)
    print("\n" + "=" * 80)
    print("시나리오 3: 범위 50-100 재스캔 - CTC 이탈 (1회차)")
    print("=" * 80)

    bot.coin_selector.scan_index = 100  # 같은 범위 재스캔

    mock_recs_3 = [
        {'ticker': 'BTC', 'score': 90.0, 'confidence': 0.80, 'features': {'rsi': 60.0}},
        {'ticker': 'MATIC', 'score': 85.0, 'confidence': 0.75, 'features': {'rsi': 55.0}},
        {'ticker': 'AVAX', 'score': 80.0, 'confidence': 0.70, 'features': {'rsi': 50.0}},
        {'ticker': 'DOT', 'score': 75.0, 'confidence': 0.65, 'features': {'rsi': 45.0}},
        {'ticker': 'LINK', 'score': 70.0, 'confidence': 0.60, 'features': {'rsi': 40.0}},
    ]

    bot._manage_tickers_dynamically(mock_recs_3)
    print(f"\n📊 After Update:")
    print(f"   Tickers: {bot.tickers}")
    print(f"   Absence Count: {bot.ticker_absence_count}")
    print(f"   ℹ️ CTC (from 50-100) should have absence count = 1")

    # 시나리오 4: 다시 범위 50-100 스캔 - CTC 이탈 (2회차 → 제거)
    print("\n" + "=" * 80)
    print("시나리오 4: 범위 50-100 재스캔 - CTC 이탈 (2회차 → 제거)")
    print("=" * 80)

    bot.coin_selector.scan_index = 100  # 같은 범위 재스캔

    bot._manage_tickers_dynamically(mock_recs_3)  # 같은 추천
    print(f"\n📊 After Update:")
    print(f"   Tickers: {bot.tickers}")
    print(f"   Absence Count: {bot.ticker_absence_count}")
    print(f"   Origin Ranges: {bot.ticker_origin_range}")
    print(f"   ℹ️ CTC should be removed (2 consecutive absences in origin range 50-100)")

    # 시나리오 5: 범위 0-50 재스캔 - XRP 이탈 (1회차)
    print("\n" + "=" * 80)
    print("시나리오 5: 범위 0-50 재스캔 - XRP 이탈 (1회차)")
    print("=" * 80)

    bot.coin_selector.scan_index = 50

    mock_recs_5 = [
        {'ticker': 'BTC', 'score': 95.0, 'confidence': 0.85, 'features': {'rsi': 65.0}},
        {'ticker': 'ETH', 'score': 90.0, 'confidence': 0.80, 'features': {'rsi': 60.0}},
        {'ticker': 'ADA', 'score': 85.0, 'confidence': 0.75, 'features': {'rsi': 55.0}},
        {'ticker': 'SOL', 'score': 80.0, 'confidence': 0.70, 'features': {'rsi': 50.0}},
        {'ticker': 'UNI', 'score': 75.0, 'confidence': 0.65, 'features': {'rsi': 45.0}},
    ]

    bot._manage_tickers_dynamically(mock_recs_5)
    print(f"\n📊 After Update:")
    print(f"   Tickers: {bot.tickers}")
    print(f"   Absence Count: {bot.ticker_absence_count}")
    print(f"   ℹ️ XRP (from 0-50) should have absence count = 1")

    # 시나리오 6: ETH에 포지션 추가 후 2회 연속 이탈 (제거 방지)
    print("\n" + "=" * 80)
    print("시나리오 6: ETH에 포지션 추가 후 2회 연속 이탈 (제거 방지)")
    print("=" * 80)

    bot.positions['ETH'] = {
        'entry_price': 3000,
        'amount': 0.1,
        'entry_time': '2026-02-04 10:00:00'
    }
    print(f"   ✅ Added ETH position: {bot.positions['ETH']}")

    mock_recs_6 = [
        {'ticker': 'BTC', 'score': 95.0, 'confidence': 0.85, 'features': {'rsi': 65.0}},
        {'ticker': 'ADA', 'score': 90.0, 'confidence': 0.80, 'features': {'rsi': 60.0}},
        {'ticker': 'SOL', 'score': 85.0, 'confidence': 0.75, 'features': {'rsi': 55.0}},
        {'ticker': 'UNI', 'score': 80.0, 'confidence': 0.70, 'features': {'rsi': 50.0}},
        {'ticker': 'ATOM', 'score': 75.0, 'confidence': 0.65, 'features': {'rsi': 45.0}},
    ]

    # 1회차 이탈
    bot._manage_tickers_dynamically(mock_recs_6)
    print(f"\n📊 After 1st Absence:")
    print(f"   Tickers: {bot.tickers}")
    print(f"   Absence Count: {bot.ticker_absence_count}")

    # 2회차 이탈
    bot.coin_selector.scan_index = 50  # 같은 범위 재스캔
    bot._manage_tickers_dynamically(mock_recs_6)
    print(f"\n📊 After 2nd Absence:")
    print(f"   Tickers: {bot.tickers}")
    print(f"   Absence Count: {bot.ticker_absence_count}")
    print(f"   ℹ️ ETH should still be in tickers (has active position)")

    # 최종 결과
    print("\n" + "=" * 80)
    print("✅ Test Complete!")
    print("=" * 80)
    print(f"Final Tickers: {bot.tickers}")
    print(f"Final Origin Ranges: {bot.ticker_origin_range}")
    print(f"Final Positions: {list(bot.positions.keys())}")
    print(f"Final Absence Count: {bot.ticker_absence_count}")

if __name__ == "__main__":
    test_dynamic_ticker_management()
