import json
import math
from pathlib import Path
from statistics import mean, median, stdev


# ============================================================
# CONFIG
# ============================================================

BASE_DIR = Path(__file__).resolve().parent.parent

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


# ============================================================
# HELPERS
# ============================================================

def haversine_km(lat1, lon1, lat2, lon2):
    """
    Calculate distance between two latitude/longitude points.
    """

    R = 6371.0

    lat1 = math.radians(lat1)
    lat2 = math.radians(lat2)

    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)

    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(lat1)
        * math.cos(lat2)
        * math.sin(dlon / 2) ** 2
    )

    return 2 * R * math.asin(math.sqrt(a))


def safe_stats(values):
    """
    Return basic statistics while ignoring None values.
    """

    values = [v for v in values if v is not None]

    if not values:
        return None

    result = {
        "count": len(values),
        "min": min(values),
        "max": max(values),
        "mean": mean(values),
        "median": median(values),
    }

    if len(values) > 1:
        result["std"] = stdev(values)
    else:
        result["std"] = 0.0

    return result


def flatten_environment(environment_data):
    """
    Convert the environmental JSON containing multiple
    tile/environment records into one list of locations.
    """

    records = []

    # --------------------------------------------------------
    # Case 1: File contains a list of environmental results
    # --------------------------------------------------------

    if isinstance(environment_data, list):

        results = environment_data

    # --------------------------------------------------------
    # Case 2: File contains a single environmental result
    # --------------------------------------------------------

    elif isinstance(environment_data, dict):

        results = [environment_data]

    else:

        raise ValueError(
            f"Unexpected environment data type: "
            f"{type(environment_data)}"
        )

    # --------------------------------------------------------
    # Process every environmental result
    # --------------------------------------------------------

    for result in results:

        environment = result.get("environment", {})

        locations = environment.get("locations", [])

        for location in locations:

            parameters = location.get("parameters", {})

            record = {
                "latitude": location.get("lat"),
                "longitude": location.get("lon"),
                "elevation": location.get("elevation"),
                "temperature": location.get("temperature"),
            }

            # ----------------------------------------------
            # Hourly environmental variables
            # ----------------------------------------------

            for key, values in parameters.items():

                if not isinstance(values, list):
                    continue

                valid_values = [
                    value
                    for value in values
                    if value is not None
                ]

                if valid_values:

                    record[key] = values

            # ----------------------------------------------
            # Solar irradiance
            # ----------------------------------------------

            solar = location.get(
                "solar_irradiance",
                {}
            )

            if solar:

                clear_sky = solar.get(
                    "clear_sky",
                    {}
                )

                record["solar_ghi"] = clear_sky.get(
                    "ghi"
                )

                record["solar_dni"] = clear_sky.get(
                    "dni"
                )

                record["solar_dhi"] = clear_sky.get(
                    "dhi"
                )

            # ----------------------------------------------
            # Keep the tile ID if available
            # ----------------------------------------------

            tile = result.get("tile", {})

            record["tile_id"] = tile.get(
                "tile_id"
            )

            records.append(record)

    return records
def get_tile_center(feature):
    """
    Calculate the approximate center of a heatmap polygon.
    """

    coordinates = feature["geometry"]["coordinates"][0]

    lons = [point[0] for point in coordinates]
    lats = [point[1] for point in coordinates]

    return mean(lats), mean(lons)


# ============================================================
# LOAD DATA
# ============================================================

print("=" * 70)
print("PHOENIX ENVIRONMENTAL COVERAGE ANALYSIS")
print("=" * 70)

print()
print("Loading heatmap...")
print(HEATMAP_FILE)

with open(HEATMAP_FILE, "r", encoding="utf-8") as f:
    heatmap_data = json.load(f)


print()
print("Loading environmental data...")
print(ENVIRONMENT_FILE)

with open(ENVIRONMENT_FILE, "r", encoding="utf-8") as f:
    environment_data = json.load(f)


# ============================================================
# HEATMAP TILES
# ============================================================

features = heatmap_data["map_data"]["features"]

heatmap_tiles = []

for feature in features:

    properties = feature["properties"]

    lat, lon = get_tile_center(feature)

    heatmap_tiles.append(
        {
            "tile_id": properties["tile_id"],
            "latitude": lat,
            "longitude": lon,
            "average_temperature": properties.get(
                "average_temperature"
            ),
            "min_temperature": properties.get(
                "min_temperature"
            ),
            "max_temperature": properties.get(
                "max_temperature"
            ),
        }
    )


# ============================================================
# ENVIRONMENTAL POINTS
# ============================================================

environment_points = flatten_environment(environment_data)

print()
print("=" * 70)
print("ENVIRONMENT RECORD CHECK")
print("=" * 70)

print(
    f"Environmental records loaded: "
    f"{len(environment_points)}"
)

for point in environment_points:
    print(
        f"Tile {point.get('tile_id')} | "
        f"Lat {point.get('latitude')} | "
        f"Lon {point.get('longitude')}"
    )
print()
print("=" * 70)
print("DATASET SIZE")
print("=" * 70)

print(f"Heatmap tiles             : {len(heatmap_tiles)}")
print(f"Environmental locations   : {len(environment_points)}")


# ============================================================
# ENVIRONMENTAL COVERAGE
# ============================================================

print()
print("=" * 70)
print("ENVIRONMENTAL SPATIAL COVERAGE")
print("=" * 70)


if not environment_points:
    print("No environmental points found.")
    raise SystemExit


distances = []

nearest_assignments = []

for tile in heatmap_tiles:

    nearest_point = None
    nearest_distance = float("inf")

    for point_index, point in enumerate(environment_points):

        distance = haversine_km(
            tile["latitude"],
            tile["longitude"],
            point["latitude"],
            point["longitude"],
        )

        if distance < nearest_distance:
            nearest_distance = distance
            nearest_point = point_index

    distances.append(nearest_distance)

    nearest_assignments.append(
        {
            "tile_id": tile["tile_id"],
            "environment_point": nearest_point,
            "distance_km": nearest_distance,
        }
    )


distance_stats = safe_stats(distances)

print(f"Minimum distance            : {distance_stats['min']:.4f} km")
print(f"Maximum distance            : {distance_stats['max']:.4f} km")
print(f"Mean distance               : {distance_stats['mean']:.4f} km")
print(f"Median distance             : {distance_stats['median']:.4f} km")
print(f"Distance standard deviation : {distance_stats['std']:.4f} km")


# ============================================================
# COVERAGE THRESHOLDS
# ============================================================

print()
print("=" * 70)
print("HEATMAP TILE COVERAGE")
print("=" * 70)

thresholds = [0.1, 0.25, 0.5, 1.0, 2.0]

for threshold in thresholds:

    covered = sum(
        1
        for distance in distances
        if distance <= threshold
    )

    percentage = (
        covered / len(heatmap_tiles) * 100
    )

    print(
        f"Within {threshold:>4.2f} km : "
        f"{covered:>4}/{len(heatmap_tiles)} "
        f"({percentage:>6.2f}%)"
    )


# ============================================================
# ENVIRONMENTAL VARIABLE ANALYSIS
# ============================================================

print()
print("=" * 70)
print("ENVIRONMENTAL VARIABLE VARIATION")
print("=" * 70)


# Variables that contain hourly arrays
hourly_variables = [
    "heat_index_celsius",
    "apparent_temperature_celsius",
    "relative_humidity_percent",
    "precipitation_mm",
    "cloud_cover_octas",
    "wet_bulb_temperature_celsius",
    "air_quality:idx",
    "air_quality_pm2p5:idx",
    "air_quality_pm10:idx",
    "air_quality_no2:idx",
    "aqi_us_co",
    "air_quality_o3:idx",
    "air_quality_so2:idx",
]


# For spatial variation, calculate the mean over 24 hours
# at each environmental point.

spatial_variable_values = {}

for variable in hourly_variables:

    values = []

    for point in environment_points:

        series = point.get(variable)

        if not series:
            continue

        valid = [
            x for x in series
            if x is not None
        ]

        if valid:
            values.append(mean(valid))

    spatial_variable_values[variable] = values


for variable, values in spatial_variable_values.items():

    stats = safe_stats(values)

    if stats is None:
        continue

    print()
    print(variable)

    print(f"  locations : {stats['count']}")
    print(f"  min       : {stats['min']:.4f}")
    print(f"  max       : {stats['max']:.4f}")
    print(f"  mean      : {stats['mean']:.4f}")
    print(f"  median    : {stats['median']:.4f}")
    print(f"  std       : {stats['std']:.4f}")


# ============================================================
# ELEVATION VARIATION
# ============================================================

print()
print("=" * 70)
print("ELEVATION")
print("=" * 70)

elevation_values = [
    point["elevation"]
    for point in environment_points
    if point.get("elevation") is not None
]

elevation_stats = safe_stats(elevation_values)

if elevation_stats:

    print(f"Min    : {elevation_stats['min']:.2f} m")
    print(f"Max    : {elevation_stats['max']:.2f} m")
    print(f"Mean   : {elevation_stats['mean']:.2f} m")
    print(f"Median : {elevation_stats['median']:.2f} m")
    print(f"Std    : {elevation_stats['std']:.2f} m")


# ============================================================
# SOLAR IRRADIANCE
# ============================================================

print()
print("=" * 70)
print("SOLAR IRRADIANCE")
print("=" * 70)

for variable in [
    "solar_ghi",
    "solar_dni",
    "solar_dhi",
]:

    values = [
        point.get(variable)
        for point in environment_points
        if point.get(variable) is not None
    ]

    stats = safe_stats(values)

    if stats:

        print()
        print(variable)

        print(f"  min    : {stats['min']:.2f}")
        print(f"  max    : {stats['max']:.2f}")
        print(f"  mean   : {stats['mean']:.2f}")
        print(f"  median : {stats['median']:.2f}")
        print(f"  std    : {stats['std']:.2f}")


# ============================================================
# HEATMAP TEMPERATURE VS ENVIRONMENT TEMPERATURE
# ============================================================

print()
print("=" * 70)
print("HEATMAP VS ENVIRONMENT TEMPERATURE")
print("=" * 70)


temperature_differences = []

for point in environment_points:

    env_temp = point.get("temperature")

    if env_temp is None:
        continue

    nearest_tile = None
    nearest_distance = float("inf")

    for tile in heatmap_tiles:

        distance = haversine_km(
            point["latitude"],
            point["longitude"],
            tile["latitude"],
            tile["longitude"],
        )

        if distance < nearest_distance:

            nearest_distance = distance
            nearest_tile = tile

    if nearest_tile:

        heatmap_temp = nearest_tile.get(
            "average_temperature"
        )

        if heatmap_temp is not None:

            difference = env_temp - heatmap_temp

            temperature_differences.append(
                difference
            )

            print(
                f"Tile {nearest_tile['tile_id']:>4} | "
                f"distance={nearest_distance:.4f} km | "
                f"heatmap={heatmap_temp:.4f} | "
                f"environment={env_temp:.4f} | "
                f"difference={difference:.4f}"
            )


if temperature_differences:

    stats = safe_stats(temperature_differences)

    print()
    print(
        f"Temperature difference mean   : "
        f"{stats['mean']:.6f}"
    )

    print(
        f"Temperature difference median : "
        f"{stats['median']:.6f}"
    )

    print(
        f"Temperature difference std    : "
        f"{stats['std']:.6f}"
    )


# ============================================================
# NULL VARIABLE CHECK
# ============================================================

print()
print("=" * 70)
print("NULL / MISSING VARIABLES")
print("=" * 70)

for variable in [
    "methane_ppb",
    "co2_ppm",
]:

    total = 0
    missing = 0

    for point in environment_points:

        values = point.get(variable)

        if values is None:
            continue

        total += len(values)

        missing += sum(
            1
            for value in values
            if value is None
        )

    if total:

        percentage = (
            missing / total * 100
        )

        print(
            f"{variable:<25} "
            f"{missing}/{total} missing "
            f"({percentage:.2f}%)"
        )


# ============================================================
# ENVIRONMENT POINT DISTRIBUTION
# ============================================================

print()
print("=" * 70)
print("ENVIRONMENT POINT LOCATIONS")
print("=" * 70)

for index, point in enumerate(environment_points):

    print(
        f"{index + 1:>2}. "
        f"lat={point['latitude']:.6f}, "
        f"lon={point['longitude']:.6f}, "
        f"elevation={point.get('elevation')}"
    )


# ============================================================
# RECOMMENDATION
# ============================================================

print()
print("=" * 70)
print("INITIAL SAMPLING ASSESSMENT")
print("=" * 70)

print()
print(
    "This analysis does NOT automatically decide the final "
    "sampling density."
)

print(
    "Use the spatial coverage, environmental variation, and "
    "temperature comparison above to decide whether the "
    "current pilot is sufficient."
)

print()
print("Important:")
print(
    "Do NOT request environmental data for all 845 heatmap "
    "tiles before evaluating this pilot."
)

print()
print("=" * 70)
print("ANALYSIS COMPLETE")
print("=" * 70)