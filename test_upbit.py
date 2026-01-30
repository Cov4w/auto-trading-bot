
import os
import pyupbit
from dotenv import load_dotenv

load_dotenv()

access_key = os.getenv("UPBIT_ACCESS_KEY")
secret_key = os.getenv("UPBIT_SECRET_KEY")

print(f"Access Key Loaded: {'Yes' if access_key else 'No'}")
print(f"Secret Key Loaded: {'Yes' if secret_key else 'No'}")

if not access_key or not secret_key:
    print("Keys are missing.")
else:
    try:
        upbit = pyupbit.Upbit(access_key, secret_key)
        print("Upbit client created.")
        
        print("Attempting to get KRW balance...")
        krw_balance = upbit.get_balance("KRW")
        print(f"KRW Balance: {krw_balance}, Type: {type(krw_balance)}")
        
        print("Attempting to get BTC balance...")
        btc_balance = upbit.get_balance("KRW-BTC")
        print(f"BTC Balance: {btc_balance}, Type: {type(btc_balance)}")
        
    except Exception as e:
        print(f"An error occurred: {e}")
        import traceback
        traceback.print_exc()
