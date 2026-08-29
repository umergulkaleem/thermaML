import json
import math
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from statistics import mean, pstdev


BASE_DIR = Path(__file__).resolve().parent
CITY = "phoenix"
HEATMAP_DIR = BASE_DIR / CITY / "raw" / "heatmaps"
ENVIRONMENT_DIR = BASE_DIR / CITY / "raw" / "environment"
OUTPUT_FILE = BASE_DIR / CITY / "processed" / "phoenix_date_tile_dataset.json"
COVERAGE_FILE = BASE_DIR / CITY / "processed" / "phoenix_dataset_coverage.json"
ENVIRONMENT_TILE_IDS = (426, 7)
EXCLUDED_PARAMETERS = {"methane_ppb", "co2_ppm"}
AGGREGATION_RULES = {
    "precipitation_mm": "sum",
    "heat_index_celsius": "mean_min_max",
    "default": "mean_min_max",
}


def load_json(path):
    with open(path, "r", encoding="utf-8") as file:
        return json.load(file)


def environment_path(date, tile_id):
    preferred = ENVIRONMENT_DIR / f"phoenix_{date}_environment_tile_{tile_id}.json"
    if preferred.exists():
        return preferred
    if date == "2023-07-15":
        legacy = ENVIRONMENT_DIR / "phoenix_2023-07-15_environment_20_points.json"
        if legacy.exists():
            return legacy
    return None


def load_environment_record(path, tile_id):
    raw = load_json(path)
    if not isinstance(raw, list):
        raise ValueError(f"Environment file must contain a list: {path}")
    for record in raw:
        if int(record.get("tile", {}).get("tile_id", -1)) == tile_id:
            return record
    raise ValueError(f"Tile {tile_id} is missing from {path}")


def validate_environment_record(record, date, tile_id):
    environment = record.get("environment", {})
    if not isinstance(environment, dict):
        raise ValueError(f"{date} tile {tile_id}: environment response is incomplete")
    metadata = environment.get("metadata", {})
    timestamps = metadata.get("timestamps")
    locations = environment.get("locations")
    if not isinstance(timestamps, list) or len(timestamps) != 24:
        raise ValueError(f"{date} tile {tile_id}: expected 24 timestamps")
    parsed = [datetime.fromisoformat(value.replace("Z", "+00:00")) for value in timestamps]
    if len(set(parsed)) != 24 or {value.date().isoformat() for value in parsed} != {date}:
        raise ValueError(f"{date} tile {tile_id}: invalid or duplicate timestamps")
    if not isinstance(locations, list) or len(locations) != 1:
        raise ValueError(f"{date} tile {tile_id}: expected one location")
    location = locations[0]
    parameters = location.get("parameters", {})
    valid_parameters = {}
    for name, values in parameters.items():
        if name in EXCLUDED_PARAMETERS or not isinstance(values, list):
            continue
        if len(values) != 24:
            raise ValueError(f"{date} tile {tile_id}: {name} is not hourly")
        numeric = [float(value) for value in values if value is not None]
        if not all(math.isfinite(value) for value in numeric):
            raise ValueError(f"{date} tile {tile_id}: {name} has non-finite values")
        valid_parameters[name] = values
    return {
        "tile_id": tile_id,
        "latitude": float(location["lat"]),
        "longitude": float(location["lon"]),
        "timestamps": timestamps,
        "parameters": valid_parameters,
        "raw_file": None,
    }


def summarize_series(values, rule):
    numeric = [float(value) for value in values if value is not None]
    if not numeric:
        return {"mean": None, "min": None, "max": None, "std": None, "sum": None, "valid_count": 0}
    result = {
        "mean": mean(numeric),
        "min": min(numeric),
        "max": max(numeric),
        "std": pstdev(numeric) if len(numeric) > 1 else 0.0,
        "sum": sum(numeric) if rule == "sum" else None,
        "valid_count": len(numeric),
    }
    return result


def daily_features(environment):
    features = {}
    for name, values in environment["parameters"].items():
        if name in EXCLUDED_PARAMETERS:
            continue
        rule = AGGREGATION_RULES.get(name, AGGREGATION_RULES["default"])
        summary = summarize_series(values, rule)
        for statistic in ("mean", "min", "max", "std", "sum", "valid_count"):
            value = summary[statistic]
            if value is not None:
                features[f"env_tile_{environment['tile_id']}_{name}_{statistic}"] = value
    return features


def heatmap_records(path, date):
    raw = load_json(path)
    features = raw.get("map_data", {}).get("features", [])
    if len(features) != 845:
        raise ValueError(f"{path.name}: expected 845 heatmap features")
    records = []
    seen = set()
    for feature in features:
        properties = feature.get("properties", {})
        tile_id = int(properties["tile_id"])
        if tile_id in seen or not 0 <= tile_id <= 844:
            raise ValueError(f"{path.name}: invalid or duplicate tile {tile_id}")
        seen.add(tile_id)
        polygon = feature["geometry"]["coordinates"][0]
        records.append({
            "date": date,
            "city": CITY,
            "tile_id": tile_id,
            "latitude": mean(point[1] for point in polygon),
            "longitude": mean(point[0] for point in polygon),
            "average_temperature": float(properties["average_temperature"]),
            "min_temperature": float(properties["min_temperature"]),
            "max_temperature": float(properties["max_temperature"]),
        })
    if seen != set(range(845)):
        raise ValueError(f"{path.name}: heatmap grid is incomplete")
    return records


def assemble():
    complete_dates = []
    incomplete_dates = {}
    dataset = []
    heatmap_files = sorted(HEATMAP_DIR.glob("phoenix_*_60m_tcm.json"))
    for heatmap_file in heatmap_files:
        date = heatmap_file.name.split("_")[1]
        if date == "2023-07-15" and "00-23" in heatmap_file.name:
            continue
        environments = []
        missing = []
        try:
            for tile_id in ENVIRONMENT_TILE_IDS:
                path = environment_path(date, tile_id)
                if path is None:
                    missing.append(tile_id)
                    continue
                environment = validate_environment_record(load_environment_record(path, tile_id), date, tile_id)
                environment["raw_file"] = str(path)
                environments.append(environment)
            if missing:
                incomplete_dates[date] = {"missing_environment_tiles": missing}
                continue
            context = {}
            raw_environment_files = {}
            for environment in environments:
                context.update(daily_features(environment))
                raw_environment_files[str(environment["tile_id"])] = environment["raw_file"]
            for record in heatmap_records(heatmap_file, date):
                dataset.append({
                    **record,
                    "environment_resolution": "two representative hourly locations summarized by date",
                    "environment_raw_files": raw_environment_files,
                    "environment_daily_features": context,
                })
            complete_dates.append(date)
        except (KeyError, TypeError, ValueError) as error:
            incomplete_dates[date] = {"validation_error": str(error)}

    report = {
        "city": CITY,
        "target_resolution": "date x tile",
        "hourly_heatmap_targets_created": False,
        "complete_dates": sorted(complete_dates),
        "incomplete_dates": incomplete_dates,
        "complete_date_count": len(complete_dates),
        "heatmap_rows_created": len(dataset),
        "environment_rows_per_complete_date": 48,
        "environment_parameters_excluded_from_modeling": sorted(EXCLUDED_PARAMETERS),
        "aggregation_rules": AGGREGATION_RULES,
        "raw_hourly_environment_preserved": True,
        "dataset_file": str(OUTPUT_FILE),
    }
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as file:
        json.dump(dataset, file, indent=2)
    with open(COVERAGE_FILE, "w", encoding="utf-8") as file:
        json.dump(report, file, indent=2)
    return report


def main():
    report = assemble()
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
