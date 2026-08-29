import json
import math
from datetime import datetime, timezone
from pathlib import Path

from data.resume_enviornment import (
    check_credit_balance,
    load_heatmap,
    extract_tiles,
    submit_environment_request,
)
from data.validate_data import validate_environment


BASE_DIR = Path(__file__).resolve().parent
CITY = "phoenix"
DATE = "2023-07-15"
TILE_ID = 7

ENVIRONMENT_DIR = (
    BASE_DIR
    / CITY
    / "raw"
    / "environment"
)
EXISTING_ENVIRONMENT_FILE = (
    ENVIRONMENT_DIR
    / f"{CITY}_{DATE}_environment_20_points.json"
)
RAW_OUTPUT_FILE = (
    ENVIRONMENT_DIR
    / f"{CITY}_{DATE}_environment_tile_{TILE_ID}.json"
)
USAGE_LOG_FILE = (
    BASE_DIR
    / CITY
    / "processed"
    / "api_usage_log.jsonl"
)


def now_utc():
    return datetime.now(timezone.utc).isoformat()


def load_cached_tile_ids():

    with open(EXISTING_ENVIRONMENT_FILE, "r", encoding="utf-8") as file:
        results = json.load(file)

    return {
        int(result["tile"]["tile_id"])
        for result in results
    }


def find_tile():

    tiles = extract_tiles(load_heatmap())

    for tile in tiles:
        if int(tile["tile_id"]) == TILE_ID:
            return tile

    raise ValueError(f"Tile {TILE_ID} is absent from the cached heatmap.")


def append_usage_log(entry):

    USAGE_LOG_FILE.parent.mkdir(parents=True, exist_ok=True)

    with open(USAGE_LOG_FILE, "a", encoding="utf-8") as file:
        file.write(json.dumps(entry, sort_keys=True) + "\n")


def main():

    tile = find_tile()
    cached_tile_ids = load_cached_tile_ids()

    if TILE_ID in cached_tile_ids:
        raise RuntimeError(
            f"Refusing duplicate request: tile {TILE_ID} is already cached."
        )

    credits_before = check_credit_balance()
    if credits_before is None:
        raise RuntimeError("Could not determine starting credits.")

    request_started_at = now_utc()
    request_metadata = {
        "city": CITY,
        "date": DATE,
        "tile_id": TILE_ID,
        "latitude": tile["latitude"],
        "longitude": tile["longitude"],
        "heatmap_average_temperature": tile["average_temperature"],
        "analysis_field_omitted": True,
    }

    response_metadata = submit_environment_request(
        tile,
        return_metadata=True,
    )
    request_finished_at = now_utc()

    result = response_metadata.get("result")
    if result is None:
        raise RuntimeError("Environmental request returned no result.")

    raw_record = [{
        "tile": tile,
        "environment": result,
    }]

    ENVIRONMENT_DIR.mkdir(parents=True, exist_ok=True)
    with open(RAW_OUTPUT_FILE, "x", encoding="utf-8") as file:
        json.dump(raw_record, file, indent=2)

    validation_error = None
    try:
        validation_report = validate_environment(
            RAW_OUTPUT_FILE,
            {
                "features": [
                    {
                        "tile_id": TILE_ID,
                        "latitude": tile["latitude"],
                        "longitude": tile["longitude"],
                    }
                ]
            },
        )
        schema_valid = True
    except Exception as error:
        validation_report = None
        validation_error = str(error)
        schema_valid = False

    location = result.get("locations", [{}])[0]
    environment_temperature = location.get("temperature")
    temperature_matches = (
        environment_temperature == tile["average_temperature"]
    )
    parameters = location.get("parameters", {})

    credits_after = check_credit_balance()
    if credits_after is None:
        raise RuntimeError("Could not determine ending credits.")

    credits_before_used = credits_before["cycle_credits_used"]
    credits_after_used = credits_after["cycle_credits_used"]
    credit_cost = credits_after_used - credits_before_used

    audit_entry = {
        "recorded_at_utc": now_utc(),
        "request_started_at_utc": request_started_at,
        "request_finished_at_utc": request_finished_at,
        "request": request_metadata,
        "activity_id": response_metadata.get("activity_id"),
        "submission_response": response_metadata.get(
            "submission_response"
        ),
        "raw_response_file": str(RAW_OUTPUT_FILE),
        "schema_valid": schema_valid,
        "schema_validation_error": validation_error,
        "schema_validation_report": validation_report,
        "environment_temperature": environment_temperature,
        "temperature_matches_heatmap": temperature_matches,
        "all_returned_parameters_preserved": True,
        "returned_parameter_count": len(parameters),
        "returned_parameter_names": sorted(parameters),
        "credits_before_used": credits_before_used,
        "credits_after_used": credits_after_used,
        "credit_cost": credit_cost,
        "credits_remaining_after": credits_after[
            "cycle_remaining_credits"
        ],
    }

    append_usage_log(audit_entry)

    print("ENVIRONMENT REQUEST COST MEASUREMENT COMPLETE")
    print(f"Tile ID: {TILE_ID}")
    print(f"Latitude: {tile['latitude']}")
    print(f"Longitude: {tile['longitude']}")
    print(
        "Heatmap average temperature: "
        f"{tile['average_temperature']}"
    )
    print(f"Date: {DATE}")
    print(f"Credits before: {credits_before_used}")
    print(f"Credits after: {credits_after_used}")
    print(f"Exact environmental request cost: {credit_cost}")
    print(f"Raw response saved: {RAW_OUTPUT_FILE}")
    print(f"Schema validation passed: {schema_valid}")
    print(f"Temperature matches heatmap: {temperature_matches}")
    print(
        "All returned environmental parameters preserved: "
        "True"
    )
    print(
        "Returned parameter count: "
        f"{len(parameters)}"
    )
    print(
        "Remaining credits: "
        f"{credits_after['cycle_remaining_credits']}"
    )
    print(f"Usage log: {USAGE_LOG_FILE}")


if __name__ == "__main__":
    main()
