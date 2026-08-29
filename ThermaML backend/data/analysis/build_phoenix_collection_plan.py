import json
from datetime import datetime
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent
OUTPUT_FILE = BASE_DIR / "collection_plan.json"
USAGE_LOG_FILE = BASE_DIR / "phoenix" / "processed" / "api_usage_log.jsonl"
ENVIRONMENT_DIAGNOSTIC_FILE = (
    BASE_DIR / "phoenix" / "processed" / "phoenix_environment_diagnostic.json"
)

HEATMAP_COST = 4_220
ENVIRONMENT_COST = 2_900
PREFERRED_CEILING = 500_000
HARD_PROJECT_CEILING = 1_000_000
TARGET_DATE_COUNT = 20
VERIFIED_DATES = ["2023-07-15"]
ENVIRONMENT_SAMPLES_PER_NEW_DATE = 2
ENVIRONMENT_SAMPLE_TILE_IDS = [426, 7]


def load_json(path):
    with open(path, "r", encoding="utf-8") as file:
        return json.load(file)


def latest_persisted_usage():
    if not USAGE_LOG_FILE.exists():
        return None

    entries = []
    with open(USAGE_LOG_FILE, "r", encoding="utf-8") as file:
        for line in file:
            if not line.strip():
                continue
            entry = json.loads(line)
            used = entry.get("credits_after_used")
            if used is None:
                continue
            recorded_at = entry.get("recorded_at_utc", "")
            entries.append((recorded_at, int(used), entry))

    if not entries:
        return None

    recorded_at, used, entry = max(
        entries,
        key=lambda item: datetime.fromisoformat(item[0].replace("Z", "+00:00")),
    )
    return {
        "credits_used": used,
        "recorded_at_utc": recorded_at,
        "activity_id": entry.get("activity_id"),
    }


def environmental_spatial_summary():
    diagnostic = load_json(ENVIRONMENT_DIAGNOSTIC_FILE)
    pairwise = diagnostic.get("pairwise_comparisons", [])
    summary = {}

    for pair in pairwise:
        for variable, comparison in pair.get("variables", {}).items():
            if not comparison.get("comparable"):
                continue
            variable_summary = summary.setdefault(
                variable,
                {
                    "comparisons": 0,
                    "nonidentical_comparisons": 0,
                    "max_absolute_difference": 0.0,
                },
            )
            variable_summary["comparisons"] += 1
            variable_summary["nonidentical_comparisons"] += int(
                not comparison["exact_equal"]
            )
            maximum = comparison.get("maximum_absolute_difference")
            if maximum is not None:
                variable_summary["max_absolute_difference"] = max(
                    variable_summary["max_absolute_difference"],
                    maximum,
                )

    valid_shared = [
        variable
        for variable, values in summary.items()
        if values["nonidentical_comparisons"] == 0
        and variable not in {"methane_ppb", "co2_ppm"}
    ]
    spatially_varying = [
        variable
        for variable, values in summary.items()
        if values["nonidentical_comparisons"] > 0
    ]
    return {
        "variable_summary": summary,
        "valid_shared_variables": sorted(valid_shared),
        "spatially_varying_variables": sorted(spatially_varying),
        "excluded_all_null_variables": ["methane_ppb", "co2_ppm"],
    }


def build_plan():
    usage = latest_persisted_usage()
    if usage is None:
        raise RuntimeError("Persisted API usage is unavailable; cannot plan safely.")

    spatial_summary = environmental_spatial_summary()
    existing_date_count = len(VERIFIED_DATES)
    new_date_count = TARGET_DATE_COUNT - existing_date_count
    heatmap_requests = new_date_count
    environment_requests = new_date_count * ENVIRONMENT_SAMPLES_PER_NEW_DATE
    heatmap_credits = heatmap_requests * HEATMAP_COST
    environment_credits = environment_requests * ENVIRONMENT_COST
    new_credits = heatmap_credits + environment_credits
    cumulative_after = usage["credits_used"] + new_credits

    return {
        "status": "planning_only_no_api_requests_made",
        "data_resolution": {
            "target": "date x spatial tile",
            "heatmap_observation": "scalar average_temperature, min_temperature, max_temperature per tile/date",
            "hourly_heatmap_targets_available": False,
            "research_limitation": (
                "The available FortyGuard heatmap response provides date-scoped "
                "scalar temperature summaries per spatial cell rather than "
                "hourly hyperlocal target observations."
            ),
        },
        "credit_safety": {
            "persisted_usage_source": str(USAGE_LOG_FILE),
            "persisted_credits_used_before_plan": usage["credits_used"],
            "persisted_usage_recorded_at_utc": usage["recorded_at_utc"],
            "preferred_cumulative_ceiling": PREFERRED_CEILING,
            "hard_project_ceiling": HARD_PROJECT_CEILING,
            "known_full_phoenix_heatmap_cost": HEATMAP_COST,
            "known_environment_request_cost": ENVIRONMENT_COST,
            "planned_new_credits": new_credits,
            "projected_cumulative_usage": cumulative_after,
            "remaining_preferred_budget_after_plan": PREFERRED_CEILING - cumulative_after,
            "safe_under_preferred_ceiling": cumulative_after <= PREFERRED_CEILING,
            "cost_status": "conditional_until_dates_are_verified",
        },
        "phoenix": {
            "target_date_count": TARGET_DATE_COUNT,
            "verified_dates": VERIFIED_DATES,
            "historical_date_availability_verified": False,
            "new_dates_required": new_date_count,
            "candidate_dates": [],
            "date_availability_blocker": (
                "Historical date availability is not established from local evidence; "
                "no dates are invented and no exploratory request is authorized."
            ),
            "heatmap_request_count_if_dates_are_verified": heatmap_requests,
            "heatmap_request_cost": HEATMAP_COST,
            "heatmap_credits_if_dates_are_verified": heatmap_credits,
            "spatial_tile_count_per_date": 845,
            "existing_tile_date_observations": 845,
            "new_tile_date_observations_if_complete": new_date_count * 845,
            "total_tile_date_observations_if_complete": TARGET_DATE_COUNT * 845,
        },
        "environment": {
            "cached_same_date_records": 9,
            "sampling_strategy": (
                "Two representative locations per new date: central tile 426 and "
                "edge tile 7. Preserve environmental data as sampled/regional context; "
                "do not treat it as 60 m resolution for every heatmap tile."
            ),
            "sample_tile_ids": ENVIRONMENT_SAMPLE_TILE_IDS,
            "samples_per_new_date": ENVIRONMENT_SAMPLES_PER_NEW_DATE,
            "new_environment_request_count_if_dates_are_verified": environment_requests,
            "environment_request_cost": ENVIRONMENT_COST,
            "environment_credits_if_dates_are_verified": environment_credits,
            "valid_shared_variables": spatial_summary["valid_shared_variables"],
            "spatially_varying_variables": spatial_summary["spatially_varying_variables"],
            "excluded_all_null_variables": spatial_summary["excluded_all_null_variables"],
            "aggregation_policy": {
                "continuous_shared_variables": "daily mean, with source hourly series preserved",
                "precipitation_mm": "daily sum, with source hourly series preserved",
                "heat_index_celsius": "daily maximum and daily mean from the two sampled locations",
                "spatial_sampling": "retain both sampled-location summaries; do not broadcast as independent tile measurements",
            },
            "spatial_evidence": spatial_summary["variable_summary"],
        },
        "splits": {
            "method": "chronological by date, never random row splitting",
            "provisional_date_counts_for_20_dates": {
                "train": 12,
                "validation": 4,
                "test": 4,
            },
            "date_ranges": None,
            "status": "Ranges remain unresolved until 19 additional dates are verified and ordered.",
        },
        "expected_models": [
            "Linear Regression",
            "Random Forest",
            "lightweight geographic-neighbor GNN",
        ],
        "tucson": {
            "status": "blocked; do not collect",
            "reason": "No verified Tucson AOI or measured Tucson heatmap cost.",
        },
        "blocking_unknowns": [
            "Historical Phoenix date availability is unverified.",
            "Exact date list and chronological split ranges are therefore unresolved.",
            "Environmental sampling is a documented methodological choice, not a demonstrated 60 m environmental field.",
        ],
        "next_step": (
            "Verify a proposed Phoenix date list through documented API support or an "
            "explicitly authorized non-collection mechanism, then recalculate this plan "
            "from the persisted usage before any request."
        ),
    }


def main():
    plan = build_plan()
    with open(OUTPUT_FILE, "w", encoding="utf-8") as file:
        json.dump(plan, file, indent=2)

    print("PHOENIX COLLECTION PLAN")
    print(f"Persisted usage: {plan['credit_safety']['persisted_credits_used_before_plan']:,}")
    print(f"Target dates: {plan['phoenix']['target_date_count']}")
    print(f"Verified dates: {len(plan['phoenix']['verified_dates'])}")
    print(
        "Conditional new requests: "
        f"{plan['phoenix']['heatmap_request_count_if_dates_are_verified']} heatmaps + "
        f"{plan['environment']['new_environment_request_count_if_dates_are_verified']} environment"
    )
    print(f"Conditional new credits: {plan['credit_safety']['planned_new_credits']:,}")
    print(
        "Safe under preferred ceiling: "
        f"{plan['credit_safety']['safe_under_preferred_ceiling']}"
    )
    print("Execution status: BLOCKED pending verified historical dates")
    print(f"Saved: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
