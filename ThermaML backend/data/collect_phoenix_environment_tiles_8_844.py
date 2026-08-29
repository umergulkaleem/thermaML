import json
import math
from datetime import datetime
from pathlib import Path

try:
    from data import resume_enviornment as base
    from data.resume_enviornment import check_credit_balance, submit_environment_request
except ModuleNotFoundError:
    import resume_enviornment as base
    from resume_enviornment import check_credit_balance, submit_environment_request


BASE_DIR = Path(__file__).resolve().parent
CITY = "phoenix"
CREDIT_LIMIT = 1_000_000
ENVIRONMENT_COST = 2_900
TILES = (8, 844)
BASE_DATES = (
    "2023-01",
    "2023-02",
    "2023-03",
    "2023-04",
    "2023-05",
    "2023-06",
    "2023-07",
    "2023-09",
    "2023-10",
    "2023-11",
    "2023-12",
    "2024-01",
)
DATES = tuple(f"{month}-{day:02d}" for month in BASE_DATES for day in (1, 15, 28))
HEATMAP_FILE = BASE_DIR / "phoenix" / "raw" / "heatmaps" / "phoenix_2023-07-15_60m_tcm.json"
OUTPUT_DIR = BASE_DIR / "phoenix" / "raw" / "environment_tiles_8_844"
REPORT_FILE = BASE_DIR / "phoenix" / "processed" / "phoenix_environment_tiles_8_844_report.json"
USAGE_LOG = BASE_DIR / "phoenix" / "processed" / "api_usage_log.jsonl"
RECOVERY_ACTIVITIES = {
    ("2023-03-01", 844): "03fed301-c06d-4537-8456-be74a3990774",
    ("2023-09-01", 8): "73a5eed1-c19f-4611-969f-17aadd87f98d",
    ("2023-11-01", 8): "6db1b03d-4b2b-4d4d-877b-584f4c151fae",
}


def load_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def persisted_usage():
    values = []
    for line in USAGE_LOG.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        entry = json.loads(line)
        if entry.get("credits_after_used") is not None:
            values.append(int(entry["credits_after_used"]))
    if not values:
        raise RuntimeError("Persisted credit usage is unavailable.")
    return max(values)


def live_used(summary):
    if not summary:
        raise RuntimeError("Live credit check returned no summary.")
    for key in ("used", "cycle_credits_used", "credits_used"):
        if summary.get(key) is not None:
            return int(summary[key])
    raise RuntimeError("Live credit response has no usage value.")


def load_tiles():
    data = load_json(HEATMAP_FILE)
    result = {}
    for feature in data["map_data"]["features"]:
        properties = feature["properties"]
        tile_id = int(properties["tile_id"])
        if tile_id not in TILES:
            continue
        polygon = feature["geometry"]["coordinates"][0]
        result[tile_id] = {
            "tile_id": tile_id,
            "latitude": sum(point[1] for point in polygon) / len(polygon),
            "longitude": sum(point[0] for point in polygon) / len(polygon),
            "temperature": float(properties["average_temperature"]),
            "average_temperature": float(properties["average_temperature"]),
            "polygon": polygon,
        }
    if set(result) != set(TILES):
        raise RuntimeError("Selected tiles are missing from the cached Phoenix heatmap.")
    return result


def submit_environment_request_fast(tile, date):
    payload = {
        "latitude": tile["latitude"],
        "longitude": tile["longitude"],
        "temperature": tile["temperature"],
        "date_time": {"start_date": date, "filter_type": 3},
    }
    response = base_requests_post(payload)
    activity_id = response.get("data", {}).get("activity_id") or response.get("activity_id")
    if not activity_id:
        return {"activity_id": None, "result": response, "payload": payload}
    for _ in range(3):
        status_response = base_requests_get(activity_id)
        data = status_response.get("data", status_response)
        status = str(data.get("status", status_response.get("status", ""))).lower()
        if status in {"completed", "success", "done", "succeeded"}:
            return {"activity_id": activity_id, "result": data.get("result", data), "payload": payload}
    return {"activity_id": activity_id, "result": None, "payload": payload}


def recover_activity_fast(activity_id):
    for _ in range(3):
        status_response = base_requests_get(activity_id)
        data = status_response.get("data", status_response)
        status = str(data.get("status", status_response.get("status", ""))).lower()
        if status in {"completed", "success", "done", "succeeded"}:
            return data.get("result", data)
    return None


def base_requests_post(payload):
    import requests
    response = requests.post(f"{base.BASE_URL}/v1/env_params", headers=base.HEADERS, json=payload, timeout=60)
    response.raise_for_status()
    return response.json()


def base_requests_get(activity_id):
    import requests
    response = requests.get(f"{base.BASE_URL}/v1/status/{activity_id}", headers=base.HEADERS, timeout=30)
    response.raise_for_status()
    return response.json()


def validate_result(result, date, tile):
    metadata = result.get("metadata") if isinstance(result, dict) else None
    timestamps = metadata.get("timestamps") if isinstance(metadata, dict) else None
    if not isinstance(timestamps, list) or len(timestamps) != 24:
        raise ValueError("Expected exactly 24 timestamps.")
    parsed = [datetime.fromisoformat(str(value).replace("Z", "+00:00")) for value in timestamps]
    if len(set(parsed)) != 24 or {value.date().isoformat() for value in parsed} != {date}:
        raise ValueError("Timestamps are duplicated or cover the wrong date.")
    locations = result.get("locations")
    if not isinstance(locations, list) or len(locations) != 1:
        raise ValueError("Expected exactly one returned location.")
    location = locations[0]
    for field in ("lat", "lon", "temperature"):
        if field not in location or location[field] is None or not math.isfinite(float(location[field])):
            raise ValueError(f"Invalid location field: {field}.")
    if abs(float(location["lat"]) - tile["latitude"]) > 0.001 or abs(float(location["lon"]) - tile["longitude"]) > 0.001:
        raise ValueError("Returned coordinates do not match the requested tile.")
    parameters = location.get("parameters")
    if not isinstance(parameters, dict) or not parameters:
        raise ValueError("Environmental parameters are missing.")
    for name, values in parameters.items():
        if not isinstance(values, list) or len(values) != 24:
            raise ValueError(f"Parameter {name} does not contain 24 values.")
        for value in values:
            if value is not None and not math.isfinite(float(value)):
                raise ValueError(f"Parameter {name} contains a non-numeric value.")
    return {
        "hour_count": 24,
        "parameter_names": sorted(parameters),
        "null_counts": {name: sum(value is None for value in values) for name, values in parameters.items()},
    }


def collect():
    tiles = load_tiles()
    planned = [(date, tile_id) for date in DATES for tile_id in TILES]
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    requests = []
    for date, tile_id in planned:
        path = OUTPUT_DIR / f"phoenix_{date}_environment_tile_{tile_id}.json"
        if path.exists():
            artifact = load_json(path)
            requests.append({
                "date": date,
                "tile_id": tile_id,
                "status": "success",
                "output_file": str(path),
                "activity_id": artifact.get("activity_id"),
                "credits_before": artifact.get("credits_before"),
                "credits_after": artifact.get("credits_after"),
                "credit_delta": artifact.get("credit_delta"),
                "validation": artifact.get("validation"),
            })
    if REPORT_FILE.exists():
        previous_report = load_json(REPORT_FILE)
        requests.extend(
            item for item in previous_report.get("requests", [])
            if item.get("status") == "pending"
        )

    report = {
        "city": CITY,
        "tiles": list(TILES),
        "dates": list(DATES),
        "source_heatmap": str(HEATMAP_FILE),
        "output_directory": str(OUTPUT_DIR),
        "credit_limit": CREDIT_LIMIT,
        "estimated_request_count": len(planned),
        "estimated_credit_cost": len(planned) * ENVIRONMENT_COST,
        "requests": requests,
    }
    completed = {
        (item["date"], item["tile_id"])
        for item in requests
        if item.get("status") == "success"
    }
    for date, tile_id in planned:
        if (date, tile_id) in completed:
            continue
        persisted_before = persisted_usage()
        if persisted_before + ENVIRONMENT_COST > CREDIT_LIMIT:
            raise RuntimeError("Persisted usage would exceed the 1,000,000-credit limit.")
        live_before = live_used(check_credit_balance())
        if live_before + ENVIRONMENT_COST > CREDIT_LIMIT:
            raise RuntimeError("Live usage would exceed the 1,000,000-credit limit.")
        tile = tiles[tile_id]
        payload = {
            "latitude": tile["latitude"],
            "longitude": tile["longitude"],
            "temperature": tile["temperature"],
            "date_time": {"start_date": date, "filter_type": 3},
        }
        recovery_id = RECOVERY_ACTIVITIES.get((date, tile_id))
        if recovery_id:
            response = {
                "activity_id": recovery_id,
                "result": recover_activity_fast(recovery_id),
            }
        else:
            response = submit_environment_request_fast(tile, date)
        if not response or response.get("result") is None:
            pending_item = next(
                (
                    item for item in report["requests"]
                    if item["date"] == date and item["tile_id"] == tile_id
                ),
                None,
            )
            if pending_item is None:
                report["requests"].append({
                    "date": date,
                    "tile_id": tile_id,
                    "status": "pending",
                    "activity_id": response.get("activity_id") if response else recovery_id,
                })
            else:
                pending_item.update({
                    "status": "pending",
                    "activity_id": response.get("activity_id") if response else recovery_id,
                })
            REPORT_FILE.write_text(json.dumps(report, indent=2), encoding="utf-8")
            continue
        validation = validate_result(response["result"], date, tile)
        live_after = live_used(check_credit_balance())
        delta = live_after - live_before
        if delta < 0 or delta > ENVIRONMENT_COST:
            raise RuntimeError(f"Unexpected credit delta for {date}, tile {tile_id}: {delta}.")
        path = OUTPUT_DIR / f"phoenix_{date}_environment_tile_{tile_id}.json"
        artifact = {
            "city": CITY,
            "location_id": f"tile_{tile_id}",
            "latitude": tile["latitude"],
            "longitude": tile["longitude"],
            "date": date,
            "activity_id": response.get("activity_id"),
            "credits_before": live_before,
            "credits_after": live_after,
            "credit_delta": delta,
            "request_payload": payload,
            "validation": validation,
            "raw_api_response": response["result"],
        }
        with path.open("x", encoding="utf-8") as file:
            json.dump(artifact, file, indent=2)
        report["requests"].append({
            "date": date,
            "tile_id": tile_id,
            "status": "success",
            "output_file": str(path),
            "activity_id": response.get("activity_id"),
            "credits_before": live_before,
            "credits_after": live_after,
            "credit_delta": delta,
            "validation": validation,
        })
        REPORT_FILE.write_text(json.dumps(report, indent=2), encoding="utf-8")
    report["successful_request_count"] = len([item for item in report["requests"] if item.get("status") == "success"])
    report["successful_observation_count"] = report["successful_request_count"] * 24
    REPORT_FILE.write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report


if __name__ == "__main__":
    result = collect()
    print(json.dumps({
        "successful_request_count": result["successful_request_count"],
        "successful_observation_count": result["successful_observation_count"],
        "output_directory": result["output_directory"],
    }, indent=2))
