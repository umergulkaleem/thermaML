import os
import requests
import json

API_KEY = os.getenv("FORTYGUARD_API_KEY", "34d165823b075d845ff08e96ec6c477f")
BASE_URL = os.getenv("FORTYGUARD_BASE_URL", "https://api.fortyguard.com")

HEADERS = {
    "api-key": API_KEY,
    "Content-Type": "application/json"
}

def check_credit_status():
    url = f"{BASE_URL}/v1/system/fetch-api-key-usage"
    
    # Endpoint requires api_key in the JSON payload body
    payload = {
        "api_key": API_KEY
    }
    
    try:
        response = requests.post(url, headers=HEADERS, json=payload)
        
        if response.status_code == 200:
            data = response.json()
            print("=== API USAGE & CREDIT STATUS ===")
            print(json.dumps(data, indent=2))
            return data
        else:
            print(f"Request failed ({response.status_code}): {response.text}")
            return None
            
    except requests.exceptions.RequestException as e:
        print(f"Connection error: {e}")
        return None

if __name__ == "__main__":
    check_credit_status()