import os
import time
import json
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
        "FORTYGUARD_API_KEY is missing from .env"
    )


HEADERS = {
    "api-key": API_KEY,
    "Content-Type": "application/json"
}


# ============================================================
# CITY CONFIGURATION
# ============================================================

CITIES = {

    "phoenix": {

        "display_name": "Phoenix, AZ",

        "date": "2023-07-15",

        "polygon": [

            [-112.0850, 33.4450],

            [-112.0650, 33.4450],

            [-112.0650, 33.4600],

            [-112.0850, 33.4600],

            [-112.0850, 33.4450]
        ]
    }
}


# ============================================================
# API SETTINGS
# ============================================================

GRANULARITY = 60

ANALYTIC_TYPE = "tcm"

POLL_INTERVAL = 4

MAX_ATTEMPTS = 30


# ------------------------------------------------------------
# IMPORTANT
#
# We are NOT requesting environmental data for all 845
# tiles yet.
#
# First experiment = 20 spatially distributed points.
#
# After measuring the real credit cost, we decide whether
# full environmental coverage is affordable.
# ------------------------------------------------------------

ENV_SAMPLE_POINTS = 20


# ============================================================
# DIRECTORY HELPERS
# ============================================================

def get_city_directories(city):

    city_dir = os.path.join(
        BASE_DIR,
        city
    )

    raw_heatmap_dir = os.path.join(
        city_dir,
        "raw",
        "heatmaps"
    )

    raw_environment_dir = os.path.join(
        city_dir,
        "raw",
        "environment"
    )

    processed_dir = os.path.join(
        city_dir,
        "processed"
    )

    os.makedirs(
        raw_heatmap_dir,
        exist_ok=True
    )

    os.makedirs(
        raw_environment_dir,
        exist_ok=True
    )

    os.makedirs(
        processed_dir,
        exist_ok=True
    )

    return (
        raw_heatmap_dir,
        raw_environment_dir,
        processed_dir
    )


# ============================================================
# CREDIT CHECK
# ============================================================

def check_credit_balance():

    url = (
        f"{BASE_URL}/v1/system/"
        "fetch-api-key-usage"
    )

    response = requests.post(

        url,

        headers=HEADERS,

        json={
            "api_key": API_KEY
        },

        timeout=30
    )

    if response.status_code != 200:

        print(
            f"[ERROR] Credit check failed "
            f"({response.status_code})"
        )

        print(response.text)

        return None

    data = response.json()

    summary = data.get(
        "credit_summary",
        {}
    )

    total = summary.get(
        "total_available_credits",
        0
    )

    used = summary.get(
        "cycle_credits_used",
        0
    )

    remaining = summary.get(
        "cycle_remaining_credits",
        0
    )

    print()
    print("=" * 60)
    print("FORTYGUARD CREDIT STATUS")
    print("=" * 60)

    print(
        f"Total available : {total:,}"
    )

    print(
        f"Credits used    : {used:,}"
    )

    print(
        f"Credits left    : {remaining:,}"
    )

    print("=" * 60)

    return {

        "total_available": total,

        "used": used,

        "remaining": remaining
    }


# ============================================================
# POLL ASYNC TASK
# ============================================================

def poll_task_result(activity_id):

    url = (
        f"{BASE_URL}/v1/status/"
        f"{activity_id}"
    )

    for attempt in range(
        1,
        MAX_ATTEMPTS + 1
    ):

        print(
            f"Polling task "
            f"{activity_id} "
            f"({attempt}/{MAX_ATTEMPTS})..."
        )

        response = requests.get(
            url,
            headers=HEADERS,
            timeout=30
        )

        if response.status_code != 200:

            print(
                f"Status request failed "
                f"({response.status_code})"
            )

            time.sleep(POLL_INTERVAL)

            continue

        response_json = response.json()

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

        if status in [
            "completed",
            "success",
            "done",
            "succeeded"
        ]:

            print(
                "[SUCCESS] Task completed."
            )

            return data.get(
                "result",
                data
            )

        if status in [
            "failed",
            "error"
        ]:

            raise RuntimeError(
                "FortyGuard task failed:\n"
                + json.dumps(
                    response_json,
                    indent=2
                )
            )

        print(
            f"Current status: "
            f"{status or 'processing'}"
        )

        time.sleep(
            POLL_INTERVAL
        )

    raise TimeoutError(
        "FortyGuard task timed out."
    )


# ============================================================
# HEATMAP PAYLOAD
# ============================================================

def build_heatmap_payload(
    city_config,
    filter_type=3,
    start_time=None,
    end_time=None
):

    if filter_type == 1 and not start_time:

        raise ValueError(
            "Single Hour heatmaps require start_time."
        )

    if filter_type == 2 and (
        not start_time
        or not end_time
    ):

        raise ValueError(
            "Range of Hours heatmaps require start_time and end_time."
        )

    date_time = {

        "start_date": city_config[
            "date"
        ],

        "filter_type": filter_type
    }

    if start_time is not None:

        date_time["start_time"] = start_time

    if end_time is not None:

        date_time["end_time"] = end_time

    return {

        "polygon_aoi": {

            "type": "FeatureCollection",

            "features": [

                {

                    "type": "Feature",

                    "properties": {

                        "region":
                            city_config[
                                "display_name"
                            ]
                    },

                    "geometry": {

                        "type": "Polygon",

                        "coordinates": [

                            city_config[
                                "polygon"
                            ]
                        ]
                    }
                }
            ]
        },

        "granularity":
            GRANULARITY,

        "date_time": date_time,

        "analytic_type":
            ANALYTIC_TYPE
    }


def submit_heatmap_request(payload):

    response = requests.post(

        f"{BASE_URL}/v1/heatmap",

        headers=HEADERS,

        json=payload,

        timeout=60
    )

    if response.status_code not in [
        200,
        202
    ]:

        raise RuntimeError(
            f"Heatmap request failed: "
            f"{response.status_code}\n"
            f"{response.text}"
        )

    response_json = response.json()

    activity_id = (

        response_json
        .get("data", {})
        .get("activity_id")

        or response_json.get(
            "activity_id"
        )
    )

    if not activity_id:

        return {
            "activity_id": None,
            "submission_response": response_json,
            "result": response_json
        }

    return {
        "activity_id": activity_id,
        "submission_response": response_json,
        "result": poll_task_result(activity_id)
    }


# ============================================================
# EXTRACT HEATMAP TILES
# ============================================================

def extract_heatmap_tiles(result):

    map_data = result.get(
        "map_data",
        result
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

        # ----------------------------------------------------
        # CENTROID
        # ----------------------------------------------------

        longitude = sum(
            point[0]
            for point in polygon
        ) / len(polygon)

        latitude = sum(
            point[1]
            for point in polygon
        ) / len(polygon)

        # ----------------------------------------------------
        # TEMPERATURE DATA
        # ----------------------------------------------------

        average_temp = properties.get(
            "average_temperature"
        )

        min_temp = properties.get(
            "min_temperature"
        )

        max_temp = properties.get(
            "max_temperature"
        )

        tile_id = properties.get(
            "tile_id",
            feature.get("id")
        )

        tiles.append({

            "tile_id": tile_id,

            "latitude":
                float(latitude),

            "longitude":
                float(longitude),

            "average_temperature":
                (
                    float(average_temp)
                    if average_temp is not None
                    else None
                ),

            "min_temperature":
                (
                    float(min_temp)
                    if min_temp is not None
                    else None
                ),

            "max_temperature":
                (
                    float(max_temp)
                    if max_temp is not None
                    else None
                ),

            "geometry":
                geometry
        })

    return tiles


# ============================================================
# SELECT SPATIALLY DISTRIBUTED TILES
# ============================================================

def select_spatial_samples(
    tiles,
    sample_count
):

    if len(tiles) <= sample_count:

        return tiles

    # --------------------------------------------------------
    # Instead of taking the first 20 tiles, divide the tile
    # list into approximately equal spatial sections.
    #
    # This gives us points distributed across the area.
    # --------------------------------------------------------

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
# FETCH ENVIRONMENTAL DATA
# ============================================================

def fetch_environment_for_tile(
    tile,
    city_config
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
                city_config[
                    "date"
                ],

            "filter_type": 3
        }

        # ----------------------------------------------------
        # IMPORTANT:
        # We intentionally DO NOT specify "analysis".
        #
        # According to the API documentation, omitting it
        # returns all available environmental parameters.
        # ----------------------------------------------------
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
            "[ERROR] Environmental request failed:"
        )

        print(
            response.status_code,
            response.text
        )

        return None

    response_json = response.json()

    # --------------------------------------------------------
    # Some FortyGuard POST endpoints are asynchronous.
    # If an activity ID is returned, poll it.
    # --------------------------------------------------------

    activity_id = (

        response_json
        .get("data", {})
        .get("activity_id")

        or response_json.get(
            "activity_id"
        )
    )

    if activity_id:

        return poll_task_result(
            activity_id
        )

    return response_json


# ============================================================
# FETCH COMPLETE PHOENIX PILOT
# ============================================================

def fetch_phoenix():

    city = "phoenix"

    config = CITIES[city]

    (
        heatmap_dir,
        environment_dir,
        _
    ) = get_city_directories(
        city
    )

    # ========================================================
    # CREDIT CHECK BEFORE EVERYTHING
    # ========================================================

    print()
    print("=" * 70)
    print("STARTING PHOENIX DATA PILOT")
    print("=" * 70)

    credits_before = (
        check_credit_balance()
    )

    if credits_before is None:

        raise RuntimeError(
            "Could not determine credits."
        )

    # ========================================================
    # HEATMAP
    # ========================================================

    heatmap_filename = (

        f"{city}_"
        f"{config['date']}_"
        f"{GRANULARITY}m_"
        f"{ANALYTIC_TYPE}.json"
    )

    heatmap_path = os.path.join(
        heatmap_dir,
        heatmap_filename
    )

    # --------------------------------------------------------
    # If it already exists, DO NOT request it again.
    # --------------------------------------------------------

    if os.path.exists(
        heatmap_path
    ):

        print()
        print(
            "[INFO] Heatmap already exists."
        )

        print(
            heatmap_path
        )

        with open(
            heatmap_path,
            "r",
            encoding="utf-8"
        ) as f:

            heatmap_result = json.load(f)

    else:

        print()
        print(
            "STEP 1: Requesting Phoenix heatmap"
        )

        payload = build_heatmap_payload(
            config
        )

        response = requests.post(

            f"{BASE_URL}/v1/heatmap",

            headers=HEADERS,

            json=payload,

            timeout=60
        )

        if response.status_code not in [
            200,
            202
        ]:

            raise RuntimeError(
                f"Heatmap request failed: "
                f"{response.status_code}\n"
                f"{response.text}"
            )

        response_json = (
            response.json()
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

            raise RuntimeError(
                "No heatmap activity ID."
            )

        print(
            f"Activity ID: {activity_id}"
        )

        heatmap_result = (
            poll_task_result(
                activity_id
            )
        )

        with open(
            heatmap_path,
            "w",
            encoding="utf-8"
        ) as f:

            json.dump(
                heatmap_result,
                f,
                indent=2
            )

        print(
            f"[SAVED] {heatmap_path}"
        )

    # ========================================================
    # EXTRACT TILES
    # ========================================================

    tiles = extract_heatmap_tiles(
        heatmap_result
    )

    print()
    print(
        f"Heatmap tiles: "
        f"{len(tiles):,}"
    )

    # ========================================================
    # SELECT ENVIRONMENTAL SAMPLE
    # ========================================================

    selected_tiles = (
        select_spatial_samples(
            tiles,
            ENV_SAMPLE_POINTS
        )
    )

    print()
    print(
        "Environmental pilot:"
    )

    print(
        f"Total heatmap tiles : "
        f"{len(tiles):,}"
    )

    print(
        f"Environmental points: "
        f"{len(selected_tiles):,}"
    )

    # ========================================================
    # ENVIRONMENTAL DATA
    # ========================================================

    environment_results = []

    for index, tile in enumerate(
        selected_tiles,
        start=1
    ):

        print()
        print(
            f"Environmental request "
            f"{index}/{len(selected_tiles)}"
        )

        print(
            f"Tile       : {tile['tile_id']}"
        )

        print(
            f"Coordinates : "
            f"{tile['latitude']:.6f}, "
            f"{tile['longitude']:.6f}"
        )

        result = (
            fetch_environment_for_tile(
                tile,
                config
            )
        )

        if result is None:

            print(
                "[WARNING] No result returned."
            )

            continue

        environment_results.append({

            "tile": tile,

            "environment": result
        })

    # ========================================================
    # SAVE ENVIRONMENTAL DATA
    # ========================================================

    environment_filename = (

        f"{city}_"
        f"{config['date']}_"
        f"environment_"
        f"{len(environment_results)}"
        f"_points.json"
    )

    environment_path = os.path.join(
        environment_dir,
        environment_filename
    )

    with open(
        environment_path,
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            environment_results,
            f,
            indent=2
        )

    print()
    print(
        f"[SAVED] Environmental data:"
    )

    print(
        environment_path
    )

    # ========================================================
    # FINAL CREDIT CHECK
    # ========================================================

    print()
    print(
        "FINAL CREDIT CHECK"
    )

    credits_after = (
        check_credit_balance()
    )

    if credits_after:

        total_consumed = (

            credits_after["used"]
            -
            credits_before["used"]
        )

        print()
        print("=" * 70)
        print("PHOENIX PILOT COST")
        print("=" * 70)

        print(
            f"Credits before : "
            f"{credits_before['used']:,}"
        )

        print(
            f"Credits after  : "
            f"{credits_after['used']:,}"
        )

        print(
            f"Total consumed : "
            f"{total_consumed:,}"
        )

        print(
            f"Heatmap tiles  : "
            f"{len(tiles):,}"
        )

        print(
            f"Environment pts: "
            f"{len(environment_results):,}"
        )

        print("=" * 70)

    return {

        "heatmap_tiles":
            tiles,

        "environment":
            environment_results
    }


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":

    fetch_phoenix()