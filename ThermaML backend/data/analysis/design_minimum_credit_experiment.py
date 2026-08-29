import json
from pathlib import Path

from data.spatial_sampling import pairwise_distances
from data.validate_data import (
    ENVIRONMENT_FILE,
    HEATMAP_FILE,
    validate_heatmap,
)


BASE_DIR = Path(__file__).resolve().parent.parent
SELECTED_FILE = (
    BASE_DIR
    / "phoenix"
    / "raw"
    / "environment"
    / "phoenix_spatial_test_tiles.json"
)
DESIGN_FILE = (
    BASE_DIR
    / "phoenix"
    / "processed"
    / "phoenix_minimum_credit_experiment.json"
)

CREDIT_LIMIT = 1_000_000
RESERVE_FRACTION = 0.50
HISTORICAL_HEATMAP_COST = 4_220


def load_json(path):

    with open(path, "r", encoding="utf-8") as file:
        return json.load(file)


def main():

    heatmap = validate_heatmap(HEATMAP_FILE)
    selected_data = load_json(SELECTED_FILE)
    selected_tiles = list(selected_data.values())
    selected_ids = {
        int(tile["tile_id"])
        for tile in selected_tiles
    }

    environment_results = load_json(ENVIRONMENT_FILE)
    cached_ids = {
        int(result["tile"]["tile_id"])
        for result in environment_results
    }
    pending_ids = sorted(selected_ids - cached_ids)
    pairwise = pairwise_distances(selected_tiles)

    design = {
        "method": "minimum_credit_spatial_environment_diagnostic",
        "data_is_local_only": True,
        "heatmap_file": str(HEATMAP_FILE),
        "selected_file": str(SELECTED_FILE),
        "environment_file": str(ENVIRONMENT_FILE),
        "heatmap_tile_count": heatmap["feature_count"],
        "selected_tile_ids": sorted(selected_ids),
        "cached_selected_tile_ids": sorted(selected_ids & cached_ids),
        "new_environment_requests_required": len(pending_ids),
        "new_environment_tile_ids": pending_ids,
        "date_policy": "Use the same existing diagnostic date.",
        "request_policy": (
            "Reuse the existing env_params payload and omit analysis."
        ),
        "historical_heatmap_cost_credits": HISTORICAL_HEATMAP_COST,
        "environment_request_cost_credits": None,
        "environment_cost_status": "Unknown; no measurement is recorded.",
        "credit_limit_credits": CREDIT_LIMIT,
        "maximum_project_spend_at_50_percent_credits": int(
            CREDIT_LIMIT * RESERVE_FRACTION
        ),
        "live_credit_balance_required_before_request": True,
        "estimated_new_environment_cost_formula": (
            f"{len(pending_ids)} * C, where C is the measured cost of one "
            "env_params request"
        ),
        "approval_required_before_request": True,
        "scientific_purpose": (
            "Test whether geographically separated locations receive "
            "meaningfully different environmental hourly series."
        ),
        "pairwise_distances_km": pairwise,
        "minimum_pairwise_distance_km": min(
            item["distance_km"]
            for item in pairwise
        ),
        "maximum_pairwise_distance_km": max(
            item["distance_km"]
            for item in pairwise
        ),
    }

    DESIGN_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(DESIGN_FILE, "w", encoding="utf-8") as file:
        json.dump(design, file, indent=2)

    print("MINIMUM-CREDIT EXPERIMENT DESIGN")
    print(f"Heatmap tiles available locally: {heatmap['feature_count']}")
    print(f"Selected tile IDs: {sorted(selected_ids)}")
    print(f"Already cached: {sorted(selected_ids & cached_ids)}")
    print(f"New requests required: {len(pending_ids)}")
    print(f"New request tile IDs: {pending_ids}")
    print("Environmental request cost: UNKNOWN")
    print("Live credit check required before any request: YES")
    print(f"Saved: {DESIGN_FILE}")


if __name__ == "__main__":
    main()
