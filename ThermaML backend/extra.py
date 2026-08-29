import os
import time
import json
import requests
from dotenv import load_dotenv

# Load environment variables from the root .env file
load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

API_KEY = os.getenv("FORTYGUARD_API_KEY")
BASE_URL = os.getenv("FORTYGUARD_BASE_URL", "https://api.fortyguard.com")

HEADERS = {
    "api-key": API_KEY,
    "Content-Type": "application/json"
}

# Resolve directory paths relative to this script
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
RAW_DATA_DIR = os.path.join(CURRENT_DIR, "raw")
PROCESSED_DATA_DIR = os.path.join(CURRENT_DIR, "processed")

os.makedirs(RAW_DATA_DIR, exist_ok=True)
os.makedirs(PROCESSED_DATA_DIR, exist_ok=True)

PHOENIX_CONFIG = {
    "city": "Phoenix, AZ",
    "date": "2023-07-15",
    "polygon": [
        [-112.0850, 33.4450],
        [-112.0650, 33.4450],
        [-112.0650, 33.4600],
        [-112.0850, 33.4600],
        [-112.0850, 33.4450]
    ]
}

def check_credit_balance():
    """Queries usage endpoint to verify remaining API credits."""
    url = f"{BASE_URL}/v1/system/fetch-api-key-usage"
    try:
        res = requests.post(url, headers=HEADERS, json={"api_key": API_KEY})
        if res.status_code == 200:
            summary = res.json().get("credit_summary", {})
            print("\n================ CREDIT STATUS ================")
            print(f"Total Available : {summary.get('total_available_credits', 0):,}")
            print(f"Credits Used    : {summary.get('cycle_credits_used', 0):,}")
            print(f"Credits Left    : {summary.get('cycle_remaining_credits', 0):,}")
            print("===============================================\n")
            return summary
        else:
            print(f"Credit balance fetch failed ({res.status_code}): {res.text}")
    except Exception as e:
        print(f"Credit check connection error: {e}")
    return None

def poll_task_result(activity_id, max_attempts=30, interval=4):
    """Polls the status endpoint until the async heatmap task finishes."""
    status_url = f"{BASE_URL}/v1/status/{activity_id}"
    
    for attempt in range(1, max_attempts + 1):
        print(f"Polling task {activity_id} (Attempt {attempt}/{max_attempts})...")
        res = requests.get(status_url, headers=HEADERS)
        
        if res.status_code == 200:
            resp_json = res.json()
            data_field = resp_json.get("data", resp_json)
            status = str(data_field.get("status", resp_json.get("status", ""))).lower()
            
            if status in ["completed", "success", "done", "succeeded"]:
                print("[✓] Task processing completed!")
                result = data_field.get("result", data_field)
                return result
            elif status in ["failed", "error"]:
                raise RuntimeError(f"Server Task Failed: {resp_json}")
            else:
                print(f"  -> Current status: {status if status else 'Processing'}...")
        else:
            print(f"  -> HTTP {res.status_code}: {res.text}")

        time.sleep(interval)
    raise TimeoutError(f"Task {activity_id} timed out.")

def fetch_and_save_phoenix():
    output_path = os.path.join(RAW_DATA_DIR, "phoenix_downtown_60m.json")

    print("--- Step 1: Initial Credit Check ---")
    check_credit_balance()

    print("--- Step 2: Submitting Heatmap Request for Phoenix ---")
    payload = {
        "polygon_aoi": {
            "type": "FeatureCollection",
            "features": [{
                "type": "Feature",
                "properties": {"region": "phoenix_downtown"},
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [PHOENIX_CONFIG["polygon"]]
                }
            }]
        },
        "granularity": 60,
        "date_time": {
            "start_date": PHOENIX_CONFIG["date"],
            "filter_type": 3
        },
        "analytic_type": "tcm"
    }

    res = requests.post(f"{BASE_URL}/v1/heatmap", headers=HEADERS, json=payload)
    if res.status_code not in [200, 202]:
        print(f"Request submission failed ({res.status_code}): {res.text}")
        return

    res_json = res.json()
    activity_id = res_json.get("data", {}).get("activity_id") or res_json.get("activity_id")
    print(f"Task queued. Activity ID: {activity_id}")

    print("\n--- Step 3: Polling and Downloading Heatmap Data ---")
    result_payload = poll_task_result(activity_id)

    # Save to data/raw/
    with open(output_path, "w") as f:
        json.dump(result_payload, f, indent=2)

    # Extract spatial features
    map_data = result_payload.get("map_data", result_payload)
    features = map_data.get("features", [])
    print(f"\n[SUCCESS] Saved {len(features):,} spatial grid tiles to: {output_path}")

    print("\n--- Step 4: Final Credit Check ---")
    check_credit_balance()

if __name__ == "__main__":
    fetch_and_save_phoenix()