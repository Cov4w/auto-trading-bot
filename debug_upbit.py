
import pyupbit
import logging
import sys

# Setup Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("debug")

print("Testing pyupbit with dummy keys...")

access_key = "your_upbit_access_key"
secret_key = "your_upbit_secret_key"

try:
    upbit = pyupbit.Upbit(access_key, secret_key)
    print("Upbit client created.")
    
    print("Getting balance for KRW...")
    try:
        krw = upbit.get_balance("KRW")
        print(f"KRW Balance: {krw} (Type: {type(krw)})")
    except Exception as e:
        print(f"get_balance(KRW) failed: {e}")
        # Print stack trace
        import traceback
        traceback.print_exc()

    print("Getting balance for KRW-BTC...")
    try:
        btc = upbit.get_balance("KRW-BTC")
        print(f"BTC Balance: {btc} (Type: {type(btc)})")
    except Exception as e:
        print(f"get_balance(KRW-BTC) failed: {e}")
        import traceback
        traceback.print_exc()

    print("Getting tickers...")
    try:
        tickers = pyupbit.get_tickers(fiat="KRW")
        print(f"Tickers: {len(tickers)} found. Sample: {tickers[:3]}")
    except Exception as e:
        print(f"get_tickers failed: {e}")
        import traceback
        traceback.print_exc()

except Exception as e:
    print(f"General failure: {e}")
    import traceback
    traceback.print_exc()
