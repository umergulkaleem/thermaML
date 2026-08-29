import argparse
import json
import math
from datetime import datetime
from pathlib import Path

try:
    from data.spatial_sampling import haversine_km
except ModuleNotFoundError:
    from spatial_sampling import haversine_km


BASE_DIR = Path(__file__).resolve().parent
CITY = "phoenix"
DATE = "2023-07-15"
START_TIME = "00:00"
END_TIME = "23:00"
FILTER_TYPE = 2
GRANULARITY = 60
ANALYTIC_TYPE = "tcm"
EXPECTED_COST = 4220
PROJECT_CEILING = 500_000
MAX_MATCH_DISTANCE_M = 5.0
AMBIGUITY_MARGIN_M = 1.0

HEATMAP_FILE = BASE_DIR / CITY / "raw" / "heatmaps" / (
    "phoenix_2023-07-15_60m_tcm.json"
)
USAGE_LOG_FILE = BASE_DIR / CITY / "processed" / "api_usage_log.jsonl"
ARTIFACT_STEM = "phoenix_2023-07-15_00-23_60m_tcm"
RAW_OUTPUT_FILE = BASE_DIR / CITY / "raw" / "heatmaps" / f"{ARTIFACT_STEM}.json"
PAYLOAD_FILE = BASE_DIR / CITY / "processed" / f"{ARTIFACT_STEM}_payload.json"
TEMPORAL_REPORT_FILE = BASE_DIR / CITY / "processed" / f"{ARTIFACT_STEM}_temporal.json"
SPATIAL_REPORT_FILE = BASE_DIR / CITY / "processed" / f"{ARTIFACT_STEM}_spatial.json"
VALIDATION_REPORT_FILE = BASE_DIR / CITY / "processed" / f"{ARTIFACT_STEM}_validation.json"


def load_json(path):
    with open(path, "r", encoding="utf-8") as file:
        return json.load(file)


def heatmap_features(result):
    map_data = result.get("map_data", result)
    if not isinstance(map_data, dict) or not isinstance(map_data.get("features"), list):
        raise ValueError("Heatmap response must contain a features list.")
    return map_data["features"]


def _walk(value, path=""):
    if isinstance(value, dict):
        for key, child in value.items():
            child_path = f"{path}.{key}" if path else key
            yield child_path, key, child
            yield from _walk(child, child_path)
    elif isinstance(value, list):
        for index, child in enumerate(value):
            yield from _walk(child, f"{path}[{index}]")


def _is_temporal_key(key):
    normalized = key.lower()
    return any(term in normalized for term in ("timestamp", "datetime", "date_time", "start_time", "end_time"))


def _is_temperature_key(key):
    return "temperature" in key.lower()


def validate_temporal_response(result, expected_observations=24):
    features = heatmap_features(result)
    temporal_fields = []
    temperature_fields = []
    timestamp_values = []
    temperature_lengths = []
    missing_temperature_features = []
    tile_ids = []
    geometry_types = []
    stats_fields = []

    for feature_index, feature in enumerate(features):
        if not isinstance(feature, dict):
            raise ValueError(f"Feature {feature_index} is not an object.")
        feature_has_temperature = False
        properties = feature.get("properties", {})
        if isinstance(properties, dict) and "tile_id" in properties:
            tile_ids.append(properties["tile_id"])
        geometry = feature.get("geometry")
        if isinstance(geometry, dict) and "type" in geometry:
            geometry_types.append(geometry["type"])
        for path, key, value in _walk(feature):
            if _is_temporal_key(key):
                temporal_fields.append(path)
                if isinstance(value, list):
                    timestamp_values.extend(value)
                elif isinstance(value, str):
                    timestamp_values.append(value)
            if _is_temperature_key(key):
                feature_has_temperature = True
                temperature_fields.append(path)
                if isinstance(value, list):
                    temperature_lengths.append(len(value))
                elif isinstance(value, (int, float)) and math.isfinite(float(value)):
                    temperature_lengths.append(1)
        if not feature_has_temperature:
            missing_temperature_features.append(feature_index)

    if isinstance(result, dict):
        stats_data = result.get("stats_data")
        if isinstance(stats_data, dict):
            stats_fields = sorted(stats_data)

    parsed_timestamps = []
    invalid_timestamps = []
    for value in timestamp_values:
        try:
            parsed_timestamps.append(datetime.fromisoformat(str(value).replace("Z", "+00:00")).isoformat())
        except (TypeError, ValueError):
            invalid_timestamps.append(value)

    duplicate_timestamps = sorted({value for value in parsed_timestamps if parsed_timestamps.count(value) > 1})
    observed_counts = sorted(set(temperature_lengths))
    has_24_observations = expected_observations in observed_counts
    return {
        "response_type": type(result).__name__,
        "top_level_keys": sorted(result) if isinstance(result, dict) else [],
        "feature_count": len(features),
        "first_feature": features[0] if features else None,
        "geometry_types": sorted(set(geometry_types)),
        "tile_ids": tile_ids,
        "stats_fields": stats_fields,
        "temporal_fields": sorted(set(temporal_fields)),
        "temperature_fields": sorted(set(temperature_fields)),
        "missing_temperature_features": missing_temperature_features,
        "temperature_observation_counts": observed_counts,
        "timestamp_count": len(timestamp_values),
        "invalid_timestamps": invalid_timestamps,
        "duplicate_timestamps": duplicate_timestamps,
        "has_24_hourly_observations": has_24_observations,
        "usable_for_hourly_targets": bool(
            has_24_observations
            and not missing_temperature_features
            and not invalid_timestamps
            and not duplicate_timestamps
        ),
    }


def feature_center(feature):
    polygon = feature.get("geometry", {}).get("coordinates", [[]])[0]
    if not polygon:
        raise ValueError("Feature has no polygon coordinates.")
    return (
        sum(point[1] for point in polygon) / len(polygon),
        sum(point[0] for point in polygon) / len(polygon),
    )


def spatial_correspondence(result, cached_result):
    returned = heatmap_features(result)
    cached = heatmap_features(cached_result)
    matches = []
    used_cached_ids = set()

    for feature in returned:
        returned_center = feature_center(feature)
        candidates = []
        for cached_feature in cached:
            cached_center = feature_center(cached_feature)
            distance_m = haversine_km(*returned_center, *cached_center) * 1000
            candidates.append((distance_m, cached_feature, cached_center))
        candidates.sort(key=lambda item: item[0])
        nearest_distance, nearest, nearest_center = candidates[0]
        second_distance = candidates[1][0] if len(candidates) > 1 else None
        ambiguous = second_distance is not None and second_distance - nearest_distance < AMBIGUITY_MARGIN_M
        returned_id = feature.get("properties", {}).get("tile_id", feature.get("id"))
        matched_id = nearest.get("properties", {}).get("tile_id", nearest.get("id"))
        reliable = nearest_distance <= MAX_MATCH_DISTANCE_M and not ambiguous and matched_id not in used_cached_ids
        if reliable:
            used_cached_ids.add(matched_id)
        matches.append({
            "returned_tile_id": returned_id,
            "matched_cached_tile_id": matched_id if reliable else None,
            "returned_center": returned_center,
            "matched_center": nearest_center,
            "nearest_distance_m": nearest_distance,
            "second_nearest_distance_m": second_distance,
            "ambiguous": ambiguous,
            "reliable": reliable,
        })

    return {
        "returned_feature_count": len(returned),
        "cached_feature_count": len(cached),
        "matches": matches,
        "all_matches_reliable": bool(matches) and all(match["reliable"] for match in matches),
        "same_spatial_grid": bool(matches) and all(match["reliable"] for match in matches),
    }


def latest_persisted_usage(path=USAGE_LOG_FILE):
    latest = None
    if not path.exists():
        return None
    with open(path, "r", encoding="utf-8") as file:
        for line in file:
            if not line.strip():
                continue
            entry = json.loads(line)
            used = entry.get("credits_after_used")
            if used is None and entry.get("credits_before_used") is not None and entry.get("credit_cost") is not None:
                used = entry["credits_before_used"] + entry["credit_cost"]
            if used is not None:
                latest = {"credits_used": int(used), "entry": entry}
    return latest


def assert_credit_safety(current_used, expected_cost=EXPECTED_COST, ceiling=PROJECT_CEILING):
    if current_used is None:
        raise ValueError("Current persisted credit usage is unknown.")
    if expected_cost is None or expected_cost <= 0:
        raise ValueError("Expected request cost is unknown.")
    if current_used + expected_cost > ceiling:
        raise RuntimeError(
            f"Request would exceed the {ceiling:,}-credit research ceiling."
        )
    return {
        "current_project_usage": current_used,
        "expected_cost": expected_cost,
        "remaining_allowed_budget": ceiling - current_used,
        "safe": True,
    }


def build_proposed_payload():
    try:
        from data.fetch_and_cache import CITIES, build_heatmap_payload
    except ModuleNotFoundError:
        from fetch_and_cache import CITIES, build_heatmap_payload

    cached = load_json(HEATMAP_FILE)
    features = heatmap_features(cached)
    city_config = dict(CITIES[CITY])
    city_config["date"] = DATE
    payload = build_heatmap_payload(
        city_config,
        filter_type=FILTER_TYPE,
        start_time=START_TIME,
        end_time=END_TIME,
    )
    payload["_expected_cached_feature_count"] = len(features)
    return payload


def _write_new(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "x", encoding="utf-8") as file:
        json.dump(value, file, indent=2)


def execute_authorized_request():
    persisted = latest_persisted_usage()
    if persisted is None:
        raise RuntimeError("No persisted usage is available; refusing request.")
    safety = assert_credit_safety(persisted["credits_used"])
    try:
        from data.fetch_and_cache import check_credit_balance, submit_heatmap_request
    except ModuleNotFoundError:
        from fetch_and_cache import check_credit_balance, submit_heatmap_request

    credits_before = check_credit_balance()
    if credits_before is None:
        raise RuntimeError("Live credit check failed; refusing request.")
    if credits_before["used"] + EXPECTED_COST > PROJECT_CEILING:
        raise RuntimeError("Live usage would exceed the research ceiling.")

    payload = build_proposed_payload()
    payload.pop("_expected_cached_feature_count")
    _write_new(PAYLOAD_FILE, payload)
    response_metadata = submit_heatmap_request(payload)
    result = response_metadata["result"]
    _write_new(RAW_OUTPUT_FILE, result)
    credits_after = check_credit_balance()
    if credits_after is None:
        raise RuntimeError("Ending live credit check failed.")

    cached = load_json(HEATMAP_FILE)
    temporal = validate_temporal_response(result)
    spatial = spatial_correspondence(result, cached)
    validation = {
        "temporal": temporal,
        "spatial": spatial,
        "hourly_targets_usable": temporal["usable_for_hourly_targets"] and spatial["all_matches_reliable"],
    }
    _write_new(TEMPORAL_REPORT_FILE, temporal)
    _write_new(SPATIAL_REPORT_FILE, spatial)
    _write_new(VALIDATION_REPORT_FILE, validation)
    audit = {
        "recorded_at_utc": datetime.now().astimezone().isoformat(),
        "request": {"city": CITY, "date": DATE, "start_time": START_TIME, "end_time": END_TIME, "filter_type": FILTER_TYPE, "granularity": GRANULARITY, "analytic_type": ANALYTIC_TYPE},
        "payload_file": str(PAYLOAD_FILE),
        "raw_response_file": str(RAW_OUTPUT_FILE),
        "activity_id": response_metadata.get("activity_id"),
        "credits_before_used": credits_before["used"],
        "credits_after_used": credits_after["used"],
        "credit_delta": credits_after["used"] - credits_before["used"],
        "credits_remaining_after": credits_after["remaining"],
        "expected_cost_guard": safety,
    }
    with open(USAGE_LOG_FILE, "a", encoding="utf-8") as file:
        file.write(json.dumps(audit, sort_keys=True) + "\n")
    return validation


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--authorize", action="store_true")
    args = parser.parse_args()
    payload = build_proposed_payload()
    persisted = latest_persisted_usage()
    current_used = persisted["credits_used"] if persisted else None
    safety = assert_credit_safety(current_used)
    payload.pop("_expected_cached_feature_count")
    print(json.dumps({
        "endpoint": "/v1/heatmap",
        "payload": payload,
        "aoi": "Phoenix city polygon from existing CITIES configuration",
        "expected_returned_features": 845,
        "known_measured_request_cost": EXPECTED_COST,
        "worst_case_cost": EXPECTED_COST,
        "current_project_usage": current_used,
        "remaining_allowed_budget": safety["remaining_allowed_budget"],
        "safe_to_execute_by_persisted_usage": safety["safe"],
        "authorized": args.authorize,
    }, indent=2))
    if args.authorize:
        execute_authorized_request()


if __name__ == "__main__":
    main()