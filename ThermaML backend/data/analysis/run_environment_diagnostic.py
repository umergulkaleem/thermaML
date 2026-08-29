import json
from pathlib import Path

from data.spatial_sampling import haversine_km


BASE_DIR = Path(__file__).resolve().parent.parent

HEATMAP_FILE = (
    BASE_DIR
    / "phoenix"
    / "raw"
    / "heatmaps"
    / "phoenix_2023-07-15_60m_tcm.json"
)

SELECTED_FILE = (
    BASE_DIR
    / "phoenix"
    / "raw"
    / "environment"
    / "phoenix_spatial_test_tiles.json"
)

ENVIRONMENT_FILE = (
    BASE_DIR
    / "phoenix"
    / "raw"
    / "environment"
    / "phoenix_2023-07-15_environment_20_points.json"
)

OUTPUT_FILE = (
    BASE_DIR
    / "phoenix"
    / "processed"
    / "phoenix_environment_diagnostic.json"
)


def load_json(path):

    with open(path, "r", encoding="utf-8") as file:
        return json.load(file)


def load_environment_records(path):

    raw_results = load_json(path)

    if not isinstance(raw_results, list):
        raise ValueError(f"Environment file must contain a list: {path}")

    records = []

    for result_index, result in enumerate(raw_results):

        tile = result.get("tile", {})
        environments = result.get("environment", {}).get("locations", [])

        if not tile or not environments:
            raise ValueError(
                f"Environment result {result_index} is incomplete: {path}"
            )

        for location in environments:

            records.append({
                "tile_id": int(tile["tile_id"]),
                "latitude": float(location["lat"]),
                "longitude": float(location["lon"]),
                "heatmap_temperature": tile.get("average_temperature"),
                "environment_temperature": location.get("temperature"),
                "parameters": location.get("parameters", {}),
            })

    return records


def selected_tiles(path):

    data = load_json(path)

    if not isinstance(data, dict):
        raise ValueError(f"Selected tile file must contain an object: {path}")

    return list(data.values())


def numeric_difference(first, second):

    if first is None or second is None:
        return None

    difference = abs(float(first) - float(second))

    return {
        "difference": float(first) - float(second),
        "absolute_difference": difference,
    }


def compare_series(first, second):

    if not isinstance(first, list) or not isinstance(second, list):
        return None

    if len(first) != len(second):
        return {
            "comparable": False,
            "length_a": len(first),
            "length_b": len(second),
        }

    differences = []

    for first_value, second_value in zip(first, second):

        if first_value is None or second_value is None:
            continue

        differences.append(
            abs(float(first_value) - float(second_value))
        )

    return {
        "comparable": True,
        "hour_count": len(first),
        "exact_equal": first == second,
        "differing_hour_count": sum(
            first_value != second_value
            for first_value, second_value in zip(first, second)
        ),
        "mean_absolute_difference": (
            sum(differences) / len(differences)
            if differences
            else None
        ),
        "maximum_absolute_difference": (
            max(differences)
            if differences
            else None
        ),
    }


def build_diagnostic():

    selected = selected_tiles(SELECTED_FILE)
    records = load_environment_records(ENVIRONMENT_FILE)
    records_by_tile = {
        record["tile_id"]: record
        for record in records
    }

    selected_results = []
    for tile in selected:

        tile_id = int(tile["tile_id"])
        record = records_by_tile.get(tile_id)
        result = {
            "tile_id": tile_id,
            "latitude": tile["latitude"],
            "longitude": tile["longitude"],
            "heatmap_temperature": tile.get("average_temperature"),
            "environment_record_available": record is not None,
        }

        if record is None:
            selected_results.append(result)
            continue

        result["distance_km"] = haversine_km(
            float(tile["latitude"]),
            float(tile["longitude"]),
            record["latitude"],
            record["longitude"],
        )
        result["environment_temperature"] = record[
            "environment_temperature"
        ]
        result["temperature_comparison"] = numeric_difference(
            record["environment_temperature"],
            tile.get("average_temperature"),
        )
        selected_results.append(result)

    comparable_records = [
        record
        for record in records
        if record["parameters"]
    ]

    variable_names = sorted({
        variable
        for record in comparable_records
        for variable in record["parameters"]
        if isinstance(record["parameters"][variable], list)
    })

    pairwise = []

    for first_index, first in enumerate(comparable_records):

        for second in comparable_records[first_index + 1:]:

            variables = {}
            for variable in variable_names:
                comparison = compare_series(
                    first["parameters"].get(variable),
                    second["parameters"].get(variable),
                )
                if comparison is not None:
                    variables[variable] = comparison

            pairwise.append({
                "tile_a": first["tile_id"],
                "tile_b": second["tile_id"],
                "distance_km": haversine_km(
                    first["latitude"],
                    first["longitude"],
                    second["latitude"],
                    second["longitude"],
                ),
                "variables": variables,
            })

    return {
        "method": "cached_environment_spatial_diagnostic",
        "heatmap_file": str(HEATMAP_FILE),
        "selected_file": str(SELECTED_FILE),
        "environment_file": str(ENVIRONMENT_FILE),
        "selected_tiles": selected_results,
        "cached_environment_record_count": len(records),
        "pairwise_comparisons": pairwise,
    }


def main():

    diagnostic = build_diagnostic()
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)

    with open(OUTPUT_FILE, "w", encoding="utf-8") as file:
        json.dump(diagnostic, file, indent=2)

    available = [
        item
        for item in diagnostic["selected_tiles"]
        if item["environment_record_available"]
    ]
    pending = [
        item["tile_id"]
        for item in diagnostic["selected_tiles"]
        if not item["environment_record_available"]
    ]

    print("ENVIRONMENT SPATIAL DIAGNOSTIC")
    print(f"Selected tiles: {len(diagnostic['selected_tiles'])}")
    print(f"Cached selected records: {len(available)}")
    print(f"Pending selected tile IDs: {pending}")
    print(f"Pairwise cached comparisons: {len(diagnostic['pairwise_comparisons'])}")
    print(f"Saved: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
