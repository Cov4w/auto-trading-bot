
import os
import jwt
import uuid
import hashlib
from urllib.parse import urlencode
import requests
from dotenv import load_dotenv

load_dotenv()

access_key = os.getenv("UPBIT_ACCESS_KEY")
secret_key = os.getenv("UPBIT_SECRET_KEY")

server_url = 'https://api.upbit.com'

def get_balance_raw():
    payload = {
        'access_key': access_key,
        'nonce': str(uuid.uuid4()),
    }

    try:
        jwt_token = jwt.encode(payload, secret_key, algorithm='HS256')
        # PyJWT 2.0+ returns str. If < 2.0 returns bytes.
        if isinstance(jwt_token, bytes):
             jwt_token = jwt_token.decode('utf-8')
             
        authorize_token = 'Bearer {}'.format(jwt_token)
        headers = {"Authorization": authorize_token}

        res = requests.get(server_url + "/v1/accounts", headers=headers)
        
        print(f"Status Code: {res.status_code}")
        print(f"Response: {res.text}")
        
        data = res.json()
        if isinstance(data, list):
            for account in data:
                print(f"Currency: {account['currency']}, Balance: {account['balance']}")
        else:
            print("Error parsing response or error message received.")

    except Exception as e:
        print(f"Raw Request Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    if not access_key or not secret_key:
        print("No keys found.")
    else:
        get_balance_raw()
