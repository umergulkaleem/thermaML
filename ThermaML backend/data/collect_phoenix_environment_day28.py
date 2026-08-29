import json
from pathlib import Path

import collect_phoenix_environment_day1 as base


DATES = tuple(f"{date[:8]}28" for date in base.DATES)
OUTPUT_DIR = base.BASE_DIR / "phoenix" / "raw" / "environment_day28"
REPORT_FILE = base.BASE_DIR / "phoenix" / "processed" / "phoenix_environment_day28_report.json"


def load_existing_requests(planned):
    requests = []
    for date, tile_id in planned:
        path = OUTPUT_DIR / f"phoenix_{date}_environment_tile_{tile_id}.json"
        if not path.exists():
            continue
        artifact = base.load_json(path)
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
    return requests


def collect():
    tiles = base.load_tiles()
    planned = [(date, tile_id) for date in DATES for tile_id in base.TILES]
    existing = load_existing_requests(planned)
    completed = {(item["date"], item["tile_id"]) for item in existing}
    pending = [item for item in planned if item not in completed]
    report = {
        "city": base.CITY,
        "dates": list(DATES),
        "tiles": list(base.TILES),
        "output_directory": str(OUTPUT_DIR),
        "estimated_request_count": len(planned),
        "estimated_credit_cost": len(planned) * base.ENVIRONMENT_COST,
        "requests": existing,
    }
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    for date, tile_id in pending:
        persisted_before = base.persisted_usage()
        if persisted_before + base.ENVIRONMENT_COST > base.CREDIT_LIMIT:
            raise RuntimeError("Persisted usage would exceed the 500,000-credit limit.")
        live_before = base.live_used(base.check_credit_balance())
        if live_before + base.ENVIRONMENT_COST > base.CREDIT_LIMIT:
            raise RuntimeError("Live usage would exceed the 500,000-credit limit.")

        tile = dict(tiles[tile_id])
        payload = {
            "latitude": tile["latitude"],
            "longitude": tile["longitude"],
            "temperature": tile["temperature"],
            "date_time": {"start_date": date, "filter_type": 3},
        }
        response = base.submit_environment_request(tile, return_metadata=True, request_date=date)
        if not response or response.get("result") is None:
            raise RuntimeError(f"No environmental result returned for {date}, tile {tile_id}.")
        validation = base.validate_result(response["result"], date, tile)
        live_after = base.live_used(base.check_credit_balance())
        delta = live_after - live_before
        if delta < 0 or delta > base.ENVIRONMENT_COST:
            raise RuntimeError(f"Unexpected credit delta for {date}, tile {tile_id}: {delta}.")

        path = OUTPUT_DIR / f"phoenix_{date}_environment_tile_{tile_id}.json"
        artifact = {
            "city": base.CITY,
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
