import copy
import json
from datetime import datetime, timezone
from pathlib import Path

from data.fetch_and_cache import (
    CITIES,
    build_heatmap_payload,
    check_credit_balance,
    submit_heatmap_request,
)
from data.validate_data import validate_heatmap


BASE_DIR = Path(__file__).resolve().parent
CITY = "phoenix"
DATE = "2023-07-15"
START_TIME = "12:00"
FILTER_TYPE = 1
TILE_ID = 426

EXISTING_HEATMAP_FILE = (
    BASE_DIR
    / CITY
    / "raw"
    / "heatmaps"
    / "phoenix_2023-07-15_60m_tcm.json"
)
RAW_OUTPUT_FILE = (
    BASE_DIR
    / CITY
    / "raw"
    / "heatmaps"
    / "phoenix_2023-07-15_12-00_tile_426_tcm.json"
)
ENVIRONMENT_FILE = (
    BASE_DIR
    / CITY
    / "raw"
    / "environment"
    / "phoenix_2023-07-15_environment_20_points.json"
)
USAGE_LOG_FILE = (
    BASE_DIR
    / CITY
    / "processed"
    / "api_usage_log.jsonl"
)


def now_utc():
    return datetime.now(timezone.utc).isoformat()


def load_json(path):

    with open(path, "r", encoding="utf-8") as file:
        return json.load(file)


def find_cached_tile():

    data = load_json(EXISTING_HEATMAP_FILE)
    features = data["map_data"]["features"]

    for feature in features:

        if int(feature["properties"]["tile_id"]) == TILE_ID:
            return data, feature

    raise ValueError(f"Cached heatmap tile {TILE_ID} was not found.")


def feature_center(feature):

    polygon = feature["geometry"]["coordinates"][0]

    return (
        sum(point[1] for point in polygon) / len(polygon),
        sum(point[0] for point in polygon) / len(polygon),
    )


def find_feature(result, tile_id):

    features = result.get("map_data", result).get("features", [])

    for feature in features:

        properties = feature.get("properties", {})
        if properties.get("tile_id") == tile_id:
            return feature

    return None


def temporal_keys(value, path=""):

    keys = []

    if isinstance(value, dict):

        for key, child in value.items():

            key_path = f"{path}.{key}" if path else key
            normalized = key.lower()

            if any(
                term in normalized
                for term in (
                    "timestamp",
                    "start_time",
                    "end_time",
                    "datetime",
                    "date_time",
                )
            ):
                keys.append(key_path)

            keys.extend(temporal_keys(child, key_path))

    elif isinstance(value, list):

        for index, child in enumerate(value):
            keys.extend(temporal_keys(child, f"{path}[{index}]"))

    return keys


def compare_temperature_fields(single_day_feature, single_hour_feature):

    fields = (
        "average_temperature",
        "min_temperature",
        "max_temperature",
    )
    comparison = {}

    for field in fields:

        single_day = single_day_feature["properties"].get(field)
        single_hour = single_hour_feature["properties"].get(field)

        comparison[field] = {
            "single_day": single_day,
            "single_hour": single_hour,
            "difference": (
                single_hour - single_day
                if single_day is not None and single_hour is not None
                else None
            ),
        }

    return comparison


def environment_at_noon():

    results = load_json(ENVIRONMENT_FILE)

    for result in results:

        if int(result["tile"]["tile_id"]) != TILE_ID:
            continue

        environment = result["environment"]
        timestamps = environment["metadata"]["timestamps"]
        timestamp = f"{DATE}T{START_TIME}:00-07:00"

        if timestamp not in timestamps:
            return {
                "timestamp": timestamp,
                "present": False,
            }

        index = timestamps.index(timestamp)
        location = environment["locations"][0]

        return {
            "timestamp": timestamp,
            "present": True,
            "index": index,
            "values": {
                name: values[index]
                for name, values in location["parameters"].items()
                if isinstance(values, list)
            },
        }

    return {
        "timestamp": f"{DATE}T{START_TIME}:00-07:00",
        "present": False,
        "reason": "Tile 426 environment record was not found.",
    }


def append_usage_log(entry):

    USAGE_LOG_FILE.parent.mkdir(parents=True, exist_ok=True)

    with open(USAGE_LOG_FILE, "a", encoding="utf-8") as file:
        file.write(json.dumps(entry, sort_keys=True) + "\n")


def main():

    existing_data, cached_tile = find_cached_tile()

    if RAW_OUTPUT_FILE.exists():
        raise RuntimeError(
            f"Refusing to overwrite existing file: {RAW_OUTPUT_FILE}"
        )

    base_config = copy.deepcopy(CITIES[CITY])
    base_config["date"] = DATE
    base_config["polygon"] = cached_tile["geometry"]["coordinates"][0]

    payload = build_heatmap_payload(
        base_config,
        filter_type=FILTER_TYPE,
        start_time=START_TIME,
    )

    if payload["date_time"] != {
        "start_date": DATE,
        "start_time": START_TIME,
        "filter_type": FILTER_TYPE,
    }:
        raise ValueError(
            f"Unexpected Single Hour date_time payload: "
            f"{payload['date_time']}"
        )

    request_metadata = {
        "city": CITY,
        "tile_id": TILE_ID,
        "date": DATE,
        "start_time": START_TIME,
        "filter_type": FILTER_TYPE,
        "granularity": 60,
        "analytic_type": "tcm",
        "aoi_source": str(EXISTING_HEATMAP_FILE),
        "aoi_is_cached_tile_geometry": True,
        "analysis_field_omitted": True,
    }

    credits_before = check_credit_balance()
    if credits_before is None:
        raise RuntimeError("Could not determine starting credits.")

    request_started_at = now_utc()
    response_metadata = submit_heatmap_request(payload)
    request_finished_at = now_utc()
    result = response_metadata["result"]

    RAW_OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(RAW_OUTPUT_FILE, "x", encoding="utf-8") as file:
        json.dump(result, file, indent=2)

    credits_after = check_credit_balance()
    if credits_after is None:
        raise RuntimeError("Could not determine ending credits.")

    validation_report = validate_heatmap(
        RAW_OUTPUT_FILE
    )
    returned_feature = find_feature(result, TILE_ID)

    if returned_feature is None:
        raise ValueError(
            f"Response did not contain requested tile_id {TILE_ID}."
        )

    returned_center = feature_center(returned_feature)
    requested_center = feature_center(cached_tile)

    if returned_center != requested_center:
        raise ValueError(
            "Returned tile geometry does not exactly match cached tile 426."
        )

    comparison = compare_temperature_fields(
        cached_tile,
        returned_feature,
    )
    environment_noon = environment_at_noon()
    temporal_metadata = temporal_keys(result)

    credits_before_used = credits_before["used"]
    credits_after_used = credits_after["used"]
    credit_delta = credits_after_used - credits_before_used

    audit_entry = {
        "recorded_at_utc": now_utc(),
        "request_started_at_utc": request_started_at,
        "request_finished_at_utc": request_finished_at,
        "request": request_metadata,
        "payload": payload,
        "activity_id": response_metadata.get("activity_id"),
        "submission_response": response_metadata.get(
            "submission_response"
        ),
        "raw_response_file": str(RAW_OUTPUT_FILE),
        "response_feature_count": validation_report["feature_count"],
        "returned_tile_id": TILE_ID,
        "returned_tile_center": returned_center,
        "requested_tile_center": requested_center,
        "temperature_comparison": comparison,
        "response_temporal_metadata_keys": temporal_metadata,
        "environment_at_12": environment_noon,
        "credits_before_used": credits_before_used,
        "credits_after_used": credits_after_used,
        "credit_delta": credit_delta,
        "credits_remaining_after": credits_after["remaining"],
    }

    append_usage_log(audit_entry)

    print("SINGLE-HOUR HEATMAP VALIDATION COMPLETE")
    print(f"Tile: {TILE_ID}")
    print(f"Date/time: {DATE} {START_TIME}")
    print(f"Returned features: {validation_report['feature_count']}")
    print(
        "Single Day vs Single Hour: "
        f"{comparison}"
    )
    print(f"Response temporal metadata keys: {temporal_metadata}")
    print(f"Environment 12:00: {environment_noon}")
    print(f"Credits before used: {credits_before_used}")
    print(f"Credits after used: {credits_after_used}")
    print(f"Credit delta: {credit_delta}")
    print(
        "Credits remaining: "
        f"{credits_after['remaining']}"
    )
    print(f"Raw response: {RAW_OUTPUT_FILE}")
    print(f"Usage log: {USAGE_LOG_FILE}")


if __name__ == "__main__":
    main()
