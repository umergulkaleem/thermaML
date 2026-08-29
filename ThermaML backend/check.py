import os
import time
import requests
import json

API_KEY = os.getenv("FORTYGUARD_API_KEY", "YOUR_API_KEY_HERE")
BASE_URL = "https://api.fortyguard.com"

HEADERS = {
    "api-key": API_KEY,
    "Content-Type": "application/json"
}

def get_credit_balance():
    """Inspects available credits before initiating data downloads."""
    url = f"{BASE_URL}/v1/system/fetch-api-key-usage"
    try:
        res = requests.post(url, headers=HEADERS, json={})
        if res.status_code == 200:
            print("Credit Status:")
            print(json.dumps(res.json(), indent=2))
            return res.json()
        print(f"Credit Check Error ({res.status_code}): {res.text}")
    except Exception as e:
        print(f"Network error: {e}")
    return None

def test_single_aoi_probe(city_name, polygon_coords, test_date="2023-07-15"):
    """
    Executes a single small test query (1 AOI) to confirm GeoJSON schema 
    and verify the resulting node/cell density.
    """
    url = f"{BASE_URL}/v1/heatmap"
    payload = {
        "polygon_aoi": {
            "type": "FeatureCollection",
            "features": [{
                "type": "Feature",
                "properties": {"city": city_name},
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [polygon_coords]  # First and last coord must match
                }
            }]
        },
        "granularity": 60,  # 60m grid resolution
        "date_time": {
            "start_date": test_date,
            "filter_type": 3  # Single Day
        },
        "analytic_type": "tcm"
    }

    print(f"\nSubmitting probe request for {city_name}...")
    res = requests.post(url, headers=HEADERS, json=payload)
    
    if res.status_code != 200:
        print(f"Submission failed ({res.status_code}): {res.text}")
        return

    activity_id = res.json().get("activity_id")
    print(f"Task submitted. Activity ID: {activity_id}. Polling status...")

    status_url = f"{BASE_URL}/v1/status/{activity_id}"
    for _ in range(30):
        time.sleep(3)
        poll_res = requests.get(status_url, headers=HEADERS)
        if poll_res.status_code == 200:
            data = poll_res.json()
            if data.get("status") in ["COMPLETED", "SUCCESS", "done"]:
                result_data = data.get("data", data)
                features = result_data.get("features", [])
                print(f"\nProbe Success!")
                print(f"Total Spatial Grid Tiles Returned: {len(features):,}")
                print(f"Sample Tile Properties: {features[0].get('properties') if features else 'None'}")
                return
    print("Polling timed out.")

if __name__ == "__main__":
    # 1. Check balance first
    get_credit_balance()

    # 2. Test Phoenix Downtown Core (~1 sq mile bounding polygon)
    phoenix_test_box = [
        [-112.0850, 33.4450],
        [-112.0650, 33.4450],
        [-112.0650, 33.4600],
        [-112.0850, 33.4600],
        [-112.0850, 33.4450]
    ]
    # Uncomment when your API key is live to run the probe:
    # test_single_aoi_probe("Phoenix_Downtown_Core", phoenix_test_box)