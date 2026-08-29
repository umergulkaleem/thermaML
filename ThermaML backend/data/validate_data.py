import json
import math
from pathlib import Path

from data.process_models import load_heatmap_features, parse_feature
from data.spatial_sampling import haversine_km


BASE_DIR = Path(__file__).resolve().parent

HEATMAP_FILE = (
    BASE_DIR
    / "phoenix"
    / "raw"
    / "heatmaps"
    / "phoenix_2023-07-15_60m_tcm.json"
)

ENVIRONMENT_FILE = (
    BASE_DIR
    / "phoenix"
    / "raw"
    / "environment"
    / "phoenix_2023-07-15_environment_20_points.json"
)

REPORT_FILE = (
    BASE_DIR
    / "phoenix"
    / "processed"
    / "phoenix_data_validation.json"
)


def load_json(path):

    with open(path, "r", encoding="utf-8") as file:
        return json.load(file)


def validate_heatmap(path):

    raw_json = load_json(path)
    features = load_heatmap_features(raw_json, str(path))
    parsed_features = [
        parse_feature(feature, index, str(path))
        for index, feature in enumerate(features)
    ]

    tile_ids = [feature["tile_id"] for feature in parsed_features]

    if len(tile_ids) != len(set(tile_ids)):
        raise ValueError(f"Duplicate heatmap tile IDs: {path}")

    return {
        "feature_count": len(parsed_features),
        "tile_ids": tile_ids,
        "features": parsed_features,
    }


def validate_hourly_parameters(location, result_index, location_index):

    parameters = location.get("parameters")

    if not isinstance(parameters, dict):
        raise ValueError(
            f"Environment result {result_index}, location "
            f"{location_index} is missing parameters."
        )

    list_parameters = {
        name: values
        for name, values in parameters.items()
        if isinstance(values, list)
    }

    if not list_parameters:
        raise ValueError(
            f"Environment result {result_index}, location "
            f"{location_index} has no hourly parameters."
        )

    lengths = {
        len(values)
        for values in list_parameters.values()
    }

    if len(lengths) != 1:
        raise ValueError(
            f"Environment result {result_index}, location "
            f"{location_index} has inconsistent hourly lengths: {lengths}"
        )

    return {
        "parameter_count": len(list_parameters),
        "hour_count": lengths.pop(),
        "parameter_names": sorted(list_parameters),
        "null_counts": {
            name: sum(value is None for value in values)
            for name, values in list_parameters.items()
        },
    }


def validate_environment(path, heatmap):

    raw_results = load_json(path)

    if not isinstance(raw_results, list):
        raise ValueError(f"Environment file must contain a list: {path}")

    heatmap_by_tile = {
        feature["tile_id"]: feature
        for feature in heatmap["features"]
    }
    records = []
    seen_tile_ids = set()

    for result_index, result in enumerate(raw_results):

        if not isinstance(result, dict):
            raise ValueError(
                f"Environment result {result_index} is not an object."
            )

        tile = result.get("tile")
        environment = result.get("environment")

        if not isinstance(tile, dict) or not isinstance(environment, dict):
            raise ValueError(
                f"Environment result {result_index} lacks tile/environment."
            )

        tile_id = tile.get("tile_id")
        if tile_id is None:
            raise ValueError(
                f"Environment result {result_index} lacks tile_id."
            )

        tile_id = int(tile_id)
        if tile_id in seen_tile_ids:
            raise ValueError(
                f"Duplicate environment tile_id: {tile_id}"
            )
        seen_tile_ids.add(tile_id)

        if tile_id not in heatmap_by_tile:
            raise ValueError(
                f"Environment tile_id {tile_id} is absent from heatmap."
            )

        locations = environment.get("locations")
        if not isinstance(locations, list) or not locations:
            raise ValueError(
                f"Environment result {result_index} has no locations."
            )

        metadata = environment.get("metadata")
        timestamps = (
            metadata.get("timestamps")
            if isinstance(metadata, dict)
            else None
        )

        if not isinstance(timestamps, list) or not timestamps:
            raise ValueError(
                f"Environment result {result_index} lacks timestamps."
            )

        location_reports = []

        for location_index, location in enumerate(locations):

            for field in ("lat", "lon", "temperature"):
                if field not in location:
                    raise ValueError(
                        f"Environment result {result_index}, location "
                        f"{location_index} lacks {field}."
                    )

            numeric_values = (
                location["lat"],
                location["lon"],
                location["temperature"],
            )

            try:
                numeric_values = [
                    float(value)
                    for value in numeric_values
                ]
            except (TypeError, ValueError) as error:
                raise ValueError(
                    f"Environment result {result_index}, location "
                    f"{location_index} has non-numeric coordinates or "
                    "temperature."
                ) from error

            if not all(math.isfinite(value) for value in numeric_values):
                raise ValueError(
                    f"Environment result {result_index}, location "
                    f"{location_index} has non-finite values."
                )

            parameter_report = validate_hourly_parameters(
                location,
                result_index,
                location_index,
            )

            distance_km = haversine_km(
                float(tile["latitude"]),
                float(tile["longitude"]),
                float(location["lat"]),
                float(location["lon"]),
            )

            location_reports.append({
                "distance_from_tile_center_km": distance_km,
                **parameter_report,
            })

        hour_count = location_reports[0]["hour_count"]
        if len(timestamps) != hour_count:
            raise ValueError(
                f"Environment result {result_index} timestamp count "
                f"{len(timestamps)} does not match hourly count "
                f"{hour_count}."
            )

        records.append({
            "tile_id": tile_id,
            "location_count": len(locations),
            "locations": location_reports,
        })

    return {
        "result_count": len(raw_results),
        "records": records,
    }


def validate_files(heatmap_path=HEATMAP_FILE, environment_path=ENVIRONMENT_FILE):

    heatmap = validate_heatmap(heatmap_path)
    environment = validate_environment(environment_path, heatmap)

    return {
        "heatmap": {
            "path": str(heatmap_path),
            "feature_count": heatmap["feature_count"],
        },
        "environment": {
            "path": str(environment_path),
            "result_count": environment["result_count"],
            "records": environment["records"],
        },
    }


def main():

    report = validate_files()
    REPORT_FILE.parent.mkdir(parents=True, exist_ok=True)

    with open(REPORT_FILE, "w", encoding="utf-8") as file:
        json.dump(report, file, indent=2)

    print("DATA VALIDATION PASSED")
    print(f"Heatmap features: {report['heatmap']['feature_count']}")
    print(f"Environment results: {report['environment']['result_count']}")
    print(f"Saved: {REPORT_FILE}")


if __name__ == "__main__":
    main()
