import json
from pathlib import Path

from build_phoenix_collection_plan import main as build_phoenix_plan


BASE_DIR = Path(__file__).resolve().parent.parent
OUTPUT_FILE = BASE_DIR / "collection_plan.json"

ENVIRONMENT_COST = 2_900
OBSERVED_HEATMAP_COST = 4_220
DOCUMENTED_PROJECT_SPEND = ENVIRONMENT_COST + OBSERVED_HEATMAP_COST
CURRENT_CYCLE_USED_SNAPSHOT = 84_640
CURRENT_REMAINING_SNAPSHOT = 1_912_460
PRESERVATION_FRACTION = 0.50
HARD_PROJECT_CEILING = 1_000_000

DATES_PER_CITY = 20
LOCATIONS_PER_DATE = 5


def phoenix_plan():

    existing_dates = 1
    existing_selected_records = 2
    new_dates = DATES_PER_CITY - existing_dates
    total_environment_records = DATES_PER_CITY * LOCATIONS_PER_DATE
    new_environment_requests = (
        total_environment_records - existing_selected_records
    )
    new_heatmap_requests = new_dates

    return {
        "dates": DATES_PER_CITY,
        "locations_per_date": LOCATIONS_PER_DATE,
        "existing_dates_reused": existing_dates,
        "existing_environment_records_reused": existing_selected_records,
        "new_environment_requests": new_environment_requests,
        "new_heatmap_requests": new_heatmap_requests,
        "estimated_environment_credits": (
            new_environment_requests * ENVIRONMENT_COST
        ),
        "estimated_heatmap_credits": (
            new_heatmap_requests * OBSERVED_HEATMAP_COST
        ),
        "estimated_new_credits": (
            new_environment_requests * ENVIRONMENT_COST
            + new_heatmap_requests * OBSERVED_HEATMAP_COST
        ),
        "estimate_status": (
            "Environment cost measured; heatmap cost observed on Phoenix "
            "only and not guaranteed."
        ),
    }


def tucson_plan():

    environment_requests = DATES_PER_CITY * LOCATIONS_PER_DATE
    heatmap_requests = DATES_PER_CITY
    environment_credits = environment_requests * ENVIRONMENT_COST
    heatmap_credits_scenario = heatmap_requests * OBSERVED_HEATMAP_COST

    return {
        "dates": DATES_PER_CITY,
        "locations_per_date": LOCATIONS_PER_DATE,
        "new_environment_requests": environment_requests,
        "new_heatmap_requests": heatmap_requests,
        "estimated_environment_credits": environment_credits,
        "estimated_heatmap_credits_scenario": heatmap_credits_scenario,
        "estimated_new_credits_scenario": (
            environment_credits + heatmap_credits_scenario
        ),
        "heatmap_tile_count": None,
        "heatmap_cost": None,
        "status": (
            "Blocked pending a defensible Tucson AOI and one measured "
            "Tucson heatmap request cost."
        ),
    }


def main():

    phoenix = phoenix_plan()
    tucson = tucson_plan()
    total_new_scenario = (
        phoenix["estimated_new_credits"]
        + tucson["estimated_new_credits_scenario"]
    )
    conservative_total = CURRENT_CYCLE_USED_SNAPSHOT + total_new_scenario
    preservation_ceiling = int(
        CURRENT_REMAINING_SNAPSHOT * PRESERVATION_FRACTION
    )

    plan = {
        "status": "planning_only_no_api_requests_made",
        "cost_basis": {
            "observed_environment_request_credits": ENVIRONMENT_COST,
            "observed_phoenix_heatmap_request_credits": (
                OBSERVED_HEATMAP_COST
            ),
            "documented_project_spend_lower_bound": (
                DOCUMENTED_PROJECT_SPEND
            ),
            "current_cycle_used_snapshot": CURRENT_CYCLE_USED_SNAPSHOT,
            "current_remaining_snapshot": CURRENT_REMAINING_SNAPSHOT,
            "preservation_ceiling_at_snapshot": preservation_ceiling,
            "hard_project_ceiling": HARD_PROJECT_CEILING,
        },
        "diagnostic_decision": {
            "remaining_same_date_tiles": [844, 8, 814],
            "separate_diagnostic_requests_necessary": False,
            "reason": (
                "Tile 7 is 1.24 km from tile 426 and differs in five "
                "environmental series; the remaining tiles can be included "
                "as part of the historical collection instead."
            ),
        },
        "phoenix": phoenix,
        "tucson": tucson,
        "combined_scenario": {
            "estimated_new_requests": (
                phoenix["new_environment_requests"]
                + phoenix["new_heatmap_requests"]
                + tucson["new_environment_requests"]
                + tucson["new_heatmap_requests"]
            ),
            "estimated_new_credits": total_new_scenario,
            "conservative_total_against_current_cycle_used": (
                conservative_total
            ),
            "under_preservation_ceiling": (
                total_new_scenario <= preservation_ceiling
            ),
            "under_hard_project_ceiling_using_current_snapshot": (
                conservative_total <= HARD_PROJECT_CEILING
            ),
        },
        "blocking_unknowns": [
            "Tucson study polygon has not been provided or documented.",
            "Tucson heatmap tile count and cost are unmeasured.",
            "Historical date availability has not been established.",
            "The current heatmap response is a scalar per tile/date; hourly "
            "hyperlocal target support is not established.",
        ],
        "recommended_next_step": (
            "Do not execute the full plan. Establish a documented Tucson "
            "AOI and verify the heatmap temporal semantics first."
        ),
    }

    with open(OUTPUT_FILE, "w", encoding="utf-8") as file:
        json.dump(plan, file, indent=2)

    print("COLLECTION PLAN")
    print(f"Phoenix estimated new credits: {phoenix['estimated_new_credits']:,}")
    print(
        "Tucson scenario estimated new credits: "
        f"{tucson['estimated_new_credits_scenario']:,}"
    )
    print(f"Combined scenario: {total_new_scenario:,}")
    print(f"Current-snapshot conservative total: {conservative_total:,}")
    print(f"Preservation ceiling: {preservation_ceiling:,}")
    print("Execution status: BLOCKED pending Tucson AOI and capability checks")
    print(f"Saved: {OUTPUT_FILE}")


if __name__ == "__main__":
    build_phoenix_plan()
