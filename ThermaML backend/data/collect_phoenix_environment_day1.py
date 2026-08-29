import json
import math
from datetime import datetime
from pathlib import Path

from resume_enviornment import check_credit_balance, recover_activity, submit_environment_request


BASE_DIR = Path(__file__).resolve().parent
CITY = "phoenix"
CREDIT_LIMIT = 500_000
ENVIRONMENT_COST = 2_900
TILES = (7, 426)
DATES = (
    "2023-01-01",
    "2023-02-01",
    "2023-03-01",
    "2023-04-01",
    "2023-05-01",
    "2023-06-01",
    "2023-07-01",
    "2023-09-01",
    "2023-10-01",
    "2023-11-01",
    "2023-12-01",
    "2024-01-01",
)
SOURCE_DATE = "2023-06-15"
ENVIRONMENT_DIR = BASE_DIR / "phoenix" / "raw" / "environment_day1"
SOURCE_DIR = BASE_DIR / "phoenix" / "raw" / "environment"
USAGE_LOG = BASE_DIR / "phoenix" / "processed" / "api_usage_log.jsonl"
REPORT_FILE = BASE_DIR / "phoenix" / "processed" / "phoenix_environment_day1_report.json"
RECOVERY_ACTIVITIES = {
    ("2023-04-01", 426): "e431f4b4-40cc-4669-a569-ae1eef7db709",
    ("2023-06-01", 426): "587ddc6d-3620-46ca-aead-212db75da10b",
    ("2023-10-01", 426): "62998ecd-4290-4687-af34-d29b478d9f1b",
}


def load_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def persisted_usage():
    values = []
    if USAGE_LOG.exists():
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
    tiles = {}
    for tile_id in TILES:
        path = SOURCE_DIR / f"phoenix_{SOURCE_DATE}_environment_tile_{tile_id}.json"
        records = load_json(path)
        record = next(item for item in records if item["tile"]["tile_id"] == tile_id)
        tile = record["tile"]
        location = record["environment"]["locations"][0]
        tiles[tile_id] = {
            "tile_id": tile_id,
            "latitude": float(location["lat"]),
            "longitude": float(location["lon"]),
            "temperature": float(location["temperature"]),
            "average_temperature": float(location["temperature"]),
            "source_coordinate_file": str(path),
            "polygon": tile.get("polygon"),
        }
    return tiles


def validate_result(result, date, tile):
    if not isinstance(result, dict):
        raise ValueError("Environmental API result is not an object.")
    metadata = result.get("metadata")
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
    pending = [
        (date, tile_id)
        for date, tile_id in planned
        if not (ENVIRONMENT_DIR / f"phoenix_{date}_environment_tile_{tile_id}.json").exists()
    ]

    existing_requests = []
    for date, tile_id in planned:
        output_path = ENVIRONMENT_DIR / f"phoenix_{date}_environment_tile_{tile_id}.json"
        if output_path.exists():
            artifact = load_json(output_path)
            existing_requests.append({
                "date": date,
                "tile_id": tile_id,
                "output_file": str(output_path),
                "activity_id": artifact.get("activity_id"),
                "credits_before": artifact.get("credits_before"),
                "credits_after": artifact.get("credits_after"),
                "credit_delta": artifact.get("credit_delta"),
                "validation": artifact.get("validation"),
            })

    report = {
        "city": CITY,
        "dates": list(DATES),
        "tiles": list(TILES),
        "output_directory": str(ENVIRONMENT_DIR),
        "estimated_request_count": len(planned),
        "estimated_credit_cost": len(planned) * ENVIRONMENT_COST,
        "requests": existing_requests,
    }
    ENVIRONMENT_DIR.mkdir(parents=True, exist_ok=True)

    for date, tile_id in pending:
        persisted_before = persisted_usage()
        if persisted_before + ENVIRONMENT_COST > CREDIT_LIMIT:
            raise RuntimeError("Persisted usage would exceed the 500,000-credit limit.")
        live_before_summary = check_credit_balance()
        live_before = live_used(live_before_summary)
        if live_before + ENVIRONMENT_COST > CREDIT_LIMIT:
            raise RuntimeError("Live usage would exceed the 500,000-credit limit.")

        tile = dict(tiles[tile_id])
        payload = {
            "latitude": tile["latitude"],
            "longitude": tile["longitude"],
            "temperature": tile["temperature"],
            "date_time": {"start_date": date, "filter_type": 3},
        }
        recovery_activity_id = RECOVERY_ACTIVITIES.get((date, tile_id))
        if recovery_activity_id:
            recovered_result = recover_activity(recovery_activity_id)
            response = {
                "activity_id": recovery_activity_id,
                "result": recovered_result,
            }
        else:
            response = submit_environment_request(tile, return_metadata=True, request_date=date)
        if not response or response.get("result") is None:
            report["requests"].append({
                "date": date,
                "tile_id": tile_id,
                "status": "pending",
                "activity_id": response.get("activity_id") if response else None,
            })
            REPORT_FILE.write_text(json.dumps(report, indent=2), encoding="utf-8")
            continue
        validation = validate_result(response["result"], date, tile)
        live_after_summary = check_credit_balance()
        live_after = live_used(live_after_summary)
        delta = live_after - live_before
        if delta < 0 or delta > ENVIRONMENT_COST:
            raise RuntimeError(f"Unexpected credit delta for {date}, tile {tile_id}: {delta}.")

        output_path = ENVIRONMENT_DIR / f"phoenix_{date}_environment_tile_{tile_id}.json"
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
        with output_path.open("x", encoding="utf-8") as file:
            json.dump(artifact, file, indent=2)
        report["requests"].append({
            "date": date,
            "tile_id": tile_id,
            "output_file": str(output_path),
            "activity_id": response.get("activity_id"),
            "credits_before": live_before,
            "credits_after": live_after,
            "credit_delta": delta,
            "validation": validation,
        })
        REPORT_FILE.write_text(json.dumps(report, indent=2), encoding="utf-8")

    report["successful_request_count"] = len(report["requests"])
    report["successful_observation_count"] = len(report["requests"]) * 24
    REPORT_FILE.write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report


if __name__ == "__main__":
    result = collect()
    print(json.dumps({
        "successful_request_count": result["successful_request_count"],
        "successful_observation_count": result["successful_observation_count"],
        "output_directory": result["output_directory"],
    }, indent=2))
