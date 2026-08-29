import os
import json
import time
import math
import requests

from dotenv import load_dotenv


# ============================================================
# ENVIRONMENT
# ============================================================

BASE_DIR = os.path.dirname(
    os.path.abspath(__file__)
)

PROJECT_DIR = os.path.dirname(BASE_DIR)

load_dotenv(
    os.path.join(
        PROJECT_DIR,
        ".env"
    )
)

API_KEY = os.getenv(
    "FORTYGUARD_API_KEY"
)

BASE_URL = os.getenv(
    "FORTYGUARD_BASE_URL",
    "https://api.fortyguard.com"
)

if not API_KEY:
    raise ValueError(
        "FORTYGUARD_API_KEY is missing."
    )


HEADERS = {
    "api-key": API_KEY,
    "Content-Type": "application/json"
}


# ============================================================
# CONFIG
# ============================================================

CITY = "phoenix"

DATE = "2023-07-15"

HEATMAP_PATH = os.path.join(
    BASE_DIR,
    "phoenix",
    "raw",
    "heatmaps",
    "phoenix_2023-07-15_60m_tcm.json"
)

ENVIRONMENT_DIR = os.path.join(
    BASE_DIR,
    "phoenix",
    "raw",
    "environment"
)

ENVIRONMENT_PATH = os.path.join(
    ENVIRONMENT_DIR,
    "phoenix_2023-07-15_environment_20_points.json"
)

SAMPLE_COUNT = 20

POLL_INTERVAL = 4

MAX_ATTEMPTS = 30


# ============================================================
# REQUESTS THAT WE KNOW ALREADY COMPLETED
# ============================================================
#
# These came directly from your terminal output.
#
# We do NOT request them again.
# ============================================================

COMPLETED_TILE_IDS = {
    73,
    79,
    85,
    91,
    97,
    228,
    234,
    240,
    246,
    252
}


# ============================================================
# REQUEST 11
# ============================================================
#
# This request was submitted and charged.
#
# The Python process crashed while handling/polling it.
#
# Therefore we try to recover the existing task instead
# of submitting a new environmental request.
# ============================================================

RECOVER_ACTIVITY_ID = (
    "3874f42e-562e-4f0a-8145-217b907918aa"
)

RECOVER_TILE_ID = 414


# ============================================================
# CREDIT CHECK
# ============================================================

def check_credit_balance():

    response = requests.post(

        f"{BASE_URL}/v1/system/"
        "fetch-api-key-usage",

        headers=HEADERS,

        json={
            "api_key": API_KEY
        },

        timeout=30
    )

    if response.status_code != 200:

        print(
            "[ERROR] Credit check failed:",
            response.status_code
        )

        print(response.text)

        return None

    data = response.json()

    summary = data.get(
        "credit_summary",
        {}
    )

    print()
    print("=" * 60)
    print("CREDIT STATUS")
    print("=" * 60)

    print(
        f"Credits used : "
        f"{summary.get('cycle_credits_used', 0):,}"
    )

    print(
        f"Credits left : "
        f"{summary.get('cycle_remaining_credits', 0):,}"
    )

    print("=" * 60)

    return summary


# ============================================================
# LOAD HEATMAP
# ============================================================

def load_heatmap():

    if not os.path.exists(
        HEATMAP_PATH
    ):

        raise FileNotFoundError(
            f"Heatmap not found:\n"
            f"{HEATMAP_PATH}"
        )

    with open(
        HEATMAP_PATH,
        "r",
        encoding="utf-8"
    ) as f:

        return json.load(f)


# ============================================================
# EXTRACT TILES
# ============================================================

def extract_tiles(
    heatmap_result
):

    map_data = heatmap_result.get(
        "map_data",
        heatmap_result
    )

    features = map_data.get(
        "features",
        []
    )

    tiles = []

    for feature in features:

        properties = feature.get(
            "properties",
            {}
        )

        geometry = feature.get(
            "geometry",
            {}
        )

        coordinates = geometry.get(
            "coordinates",
            []
        )

        if not coordinates:
            continue

        polygon = coordinates[0]

        if not polygon:
            continue

        latitude = sum(
            point[1]
            for point in polygon
        ) / len(polygon)

        longitude = sum(
            point[0]
            for point in polygon
        ) / len(polygon)

        tile_id = properties.get(
            "tile_id",
            feature.get("id")
        )

        tiles.append({

            "tile_id": int(tile_id),

            "latitude": float(
                latitude
            ),

            "longitude": float(
                longitude
            ),

            "average_temperature": (
                float(
                    properties[
                        "average_temperature"
                    ]
                )
                if properties.get(
                    "average_temperature"
                ) is not None
                else None
            ),

            "min_temperature": (
                float(
                    properties[
                        "min_temperature"
                    ]
                )
                if properties.get(
                    "min_temperature"
                ) is not None
                else None
            ),

            "max_temperature": (
                float(
                    properties[
                        "max_temperature"
                    ]
                )
                if properties.get(
                    "max_temperature"
                ) is not None
                else None
            ),

            "geometry": geometry
        })

    return tiles


# ============================================================
# SELECT SAME 20 SPATIAL POINTS
# ============================================================

def select_spatial_samples(
    tiles,
    sample_count
):

    if len(tiles) <= sample_count:

        return tiles

    grid_size = math.ceil(
        math.sqrt(sample_count)
    )

    lats = [
        tile["latitude"]
        for tile in tiles
    ]

    lons = [
        tile["longitude"]
        for tile in tiles
    ]

    min_lat = min(lats)
    max_lat = max(lats)

    min_lon = min(lons)
    max_lon = max(lons)

    selected = []

    for row in range(grid_size):

        for col in range(grid_size):

            if len(selected) >= sample_count:
                break

            target_lat = (

                min_lat
                +
                (
                    row + 0.5
                )
                / grid_size
                *
                (
                    max_lat - min_lat
                )
            )

            target_lon = (

                min_lon
                +
                (
                    col + 0.5
                )
                / grid_size
                *
                (
                    max_lon - min_lon
                )
            )

            nearest = min(

                tiles,

                key=lambda tile:

                (
                    tile["latitude"]
                    - target_lat
                ) ** 2

                +

                (
                    tile["longitude"]
                    - target_lon
                ) ** 2
            )

            if nearest not in selected:

                selected.append(
                    nearest
                )

    return selected


# ============================================================
# POLL EXISTING ACTIVITY
# ============================================================

def recover_activity(
    activity_id
):

    url = (
        f"{BASE_URL}/v1/status/"
        f"{activity_id}"
    )

    for attempt in range(
        1,
        MAX_ATTEMPTS + 1
    ):

        print(
            f"Recovering activity "
            f"{activity_id} "
            f"({attempt}/{MAX_ATTEMPTS})"
        )

        try:

            response = requests.get(
                url,
                headers=HEADERS,
                timeout=30
            )

            print(
                "HTTP status:",
                response.status_code
            )

            if response.status_code != 200:

                print(
                    response.text
                )

                time.sleep(
                    POLL_INTERVAL
                )

                continue

            response_json = (
                response.json()
            )

            # ------------------------------------------------
            # Print the raw structure so we don't make
            # assumptions about the API response.
            # ------------------------------------------------

            data = response_json.get(
                "data",
                response_json
            )

            status = str(
                data.get(
                    "status",
                    response_json.get(
                        "status",
                        ""
                    )
                )
            ).lower()

            print(
                "Status:",
                status
            )

            if status in [
                "completed",
                "success",
                "done",
                "succeeded"
            ]:

                print(
                    "[SUCCESS] "
                    "Recovered activity."
                )

                return data.get(
                    "result",
                    data
                )

            if status in [
                "failed",
                "error"
            ]:

                print(
                    "[FAILED] "
                    "Existing activity failed."
                )

                print(
                    json.dumps(
                        response_json,
                        indent=2
                    )
                )

                return None

        except Exception as e:

            print(
                "[WARNING] "
                f"Recovery error: {e}"
            )

        time.sleep(
            POLL_INTERVAL
        )

    return None


# ============================================================
# CREATE NEW ENVIRONMENT REQUEST
# ============================================================

def submit_environment_request(
    tile,
    return_metadata=False,
    request_date=None,
):

    payload = {

        "latitude":
            tile["latitude"],

        "longitude":
            tile["longitude"],

        "temperature":
            tile["average_temperature"],

        "date_time": {

            "start_date":
                request_date or DATE,

            "filter_type": 3
        }

        # analysis intentionally omitted.
        #
        # According to the API documentation this means
        # all available environmental parameters.
    }

    response = requests.post(

        f"{BASE_URL}/v1/env_params",

        headers=HEADERS,

        json=payload,

        timeout=60
    )

    if response.status_code not in [
        200,
        202
    ]:

        print(
            "[ERROR] Environmental request failed"
        )

        print(
            response.status_code
        )

        print(
            response.text
        )

        return None

    response_json = (
        response.json()
    )

    print(
        "Raw submission response:"
    )

    print(
        json.dumps(
            response_json,
            indent=2
        )
    )

    activity_id = (

        response_json
        .get("data", {})
        .get("activity_id")

        or response_json.get(
            "activity_id"
        )
    )

    if not activity_id:

        # If the API ever returns the result
        # directly, preserve it.

        if return_metadata:
            return {
                "activity_id": None,
                "submission_response": response_json,
                "result": response_json
            }

        return response_json

    print(
        "Activity ID:",
        activity_id
    )

    result = recover_activity(
        activity_id
    )

    if return_metadata:
        return {
            "activity_id": activity_id,
            "submission_response": response_json,
            "result": result
        }

    return result


# ============================================================
# SAVE RESULTS IMMEDIATELY
# ============================================================

def save_results(results):

    os.makedirs(
        ENVIRONMENT_DIR,
        exist_ok=True
    )

    with open(
        ENVIRONMENT_PATH,
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            results,
            f,
            indent=2
        )


# ============================================================
# MAIN
# ============================================================

def main():

    print()
    print("=" * 70)
    print("RESUMING PHOENIX ENVIRONMENTAL PILOT")
    print("=" * 70)

    credits_before = (
        check_credit_balance()
    )

    # --------------------------------------------------------
    # LOAD HEATMAP
    # --------------------------------------------------------

    heatmap = load_heatmap()

    tiles = extract_tiles(
        heatmap
    )

    print(
        f"\nHeatmap tiles: {len(tiles):,}"
    )

    # --------------------------------------------------------
    # RECREATE THE SAME 20 POINTS
    # --------------------------------------------------------

    selected_tiles = (
        select_spatial_samples(
            tiles,
            SAMPLE_COUNT
        )
    )

    print(
        "\nSelected environmental tiles:"
    )

    for tile in selected_tiles:

        print(
            tile["tile_id"],
            end=" "
        )

    print()

    # --------------------------------------------------------
    # LOAD PARTIAL RESULTS IF THEY EXIST
    # --------------------------------------------------------

    results = []

    if os.path.exists(
        ENVIRONMENT_PATH
    ):

        print(
            "\n[INFO] Existing environment "
            "file found."
        )

        with open(
            ENVIRONMENT_PATH,
            "r",
            encoding="utf-8"
        ) as f:

            results = json.load(f)

    # --------------------------------------------------------
    # KNOWN COMPLETED REQUESTS
    # --------------------------------------------------------

    completed_ids = set(
        COMPLETED_TILE_IDS
    )

    # Add anything already saved
    # in the partial file.

    for item in results:

        tile = item.get(
            "tile",
            {}
        )

        tile_id = tile.get(
            "tile_id"
        )

        if tile_id is not None:

            completed_ids.add(
                int(tile_id)
            )

    # --------------------------------------------------------
    # RECOVER REQUEST 11
    # --------------------------------------------------------

    if (
        RECOVER_TILE_ID
        not in completed_ids
    ):

        print()
        print("=" * 60)
        print(
            "RECOVERING REQUEST 11"
        )
        print("=" * 60)

        recovered = recover_activity(
            RECOVER_ACTIVITY_ID
        )

        if recovered is not None:

            tile_414 = next(
                (
                    tile
                    for tile
                    in selected_tiles
                    if tile["tile_id"]
                    == RECOVER_TILE_ID
                ),
                None
            )

            if tile_414 is not None:

                results.append({

                    "tile": tile_414,

                    "environment":
                        recovered
                })

                save_results(
                    results
                )

                completed_ids.add(
                    RECOVER_TILE_ID
                )

                print(
                    "[SAVED] Recovered "
                    "tile 414."
                )

        else:

            print(
                "[WARNING] Could not recover "
                "tile 414."
            )

            print(
                "We will NOT automatically "
                "submit it again."
            )

    # --------------------------------------------------------
    # CONTINUE WITH REMAINING POINTS
    # --------------------------------------------------------

    for index, tile in enumerate(
        selected_tiles,
        start=1
    ):

        tile_id = int(
            tile["tile_id"]
        )

        if tile_id in completed_ids:

            print()
            print(
                f"[SKIP] Tile "
                f"{tile_id} already completed."
            )

            continue

        print()
        print("=" * 60)

        print(
            f"NEW ENVIRONMENT REQUEST"
        )

        print(
            f"Tile: {tile_id}"
        )

        print(
            f"Coordinates: "
            f"{tile['latitude']:.6f}, "
            f"{tile['longitude']:.6f}"
        )

        print("=" * 60)

        result = (
            submit_environment_request(
                tile
            )
        )

        if result is None:

            print(
                "[WARNING] No result."
            )

            continue

        results.append({

            "tile": tile,

            "environment": result
        })

        # ----------------------------------------------------
        # SAVE IMMEDIATELY
        #
        # This is the major improvement over the old code.
        # If request 17 crashes, requests 1-16 are already
        # safely stored.
        # ----------------------------------------------------

        save_results(
            results
        )

        completed_ids.add(
            tile_id
        )

        print(
            "[SAVED] Result immediately."
        )

    # ========================================================
    # FINAL CREDIT CHECK
    # ========================================================

    print()
    print("=" * 70)
    print("PILOT COMPLETE")
    print("=" * 70)

    credits_after = (
        check_credit_balance()
    )

    if (
        credits_before
        and credits_after
    ):

        consumed = (

            credits_after[
                "cycle_credits_used"
            ]

            -

            credits_before[
                "cycle_credits_used"
            ]
        )

        print(
            f"\nCredits consumed "
            f"during this run: "
            f"{consumed:,}"
        )

    print(
        f"Environmental results saved: "
        f"{len(results)}"
    )

    print(
        f"Output:\n"
        f"{ENVIRONMENT_PATH}"
    )


if __name__ == "__main__":

    main()