import json
import math
from pathlib import Path

from spatial_sampling import (
    pairwise_distances,
    select_farthest_points,
)


HEATMAP_FILE = Path(
    "data/phoenix/raw/heatmaps/phoenix_2023-07-15_60m_tcm.json"
)

OUTPUT_FILE = Path(
    "data/phoenix/raw/environment/phoenix_spatial_test_tiles.json"
)


def haversine_km(lat1, lon1, lat2, lon2):
    """Calculate distance between two geographic points in km."""

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


def polygon_centroid(coordinates):
    """
    Calculate a simple centroid from polygon vertices.

    For these small ~60 m tiles, averaging the vertices is
    sufficiently accurate for selecting spatial sample points.
    """

    points = coordinates[0]

    lons = [point[0] for point in points]
    lats = [point[1] for point in points]

    return (
        sum(lats) / len(lats),
        sum(lons) / len(lons)
    )


def load_tiles(path):

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    features = data["map_data"]["features"]

    tiles = []

    for feature in features:

        properties = feature["properties"]
        geometry = feature["geometry"]

        latitude, longitude = polygon_centroid(
            geometry["coordinates"]
        )

        tiles.append({
            "tile_id": properties["tile_id"],
            "latitude": latitude,
            "longitude": longitude,
            "average_temperature": properties[
                "average_temperature"
            ],
            "min_temperature": properties[
                "min_temperature"
            ],
            "max_temperature": properties[
                "max_temperature"
            ]
        })

    return tiles


tiles = load_tiles(HEATMAP_FILE)

print("=" * 70)
print("SPATIAL TILE SELECTION")
print("=" * 70)

print("\nTotal tiles found:", len(tiles))


# ---------------------------------------------------------
# Find geographic bounding box
# ---------------------------------------------------------

min_lat = min(tile["latitude"] for tile in tiles)
max_lat = max(tile["latitude"] for tile in tiles)

min_lon = min(tile["longitude"] for tile in tiles)
max_lon = max(tile["longitude"] for tile in tiles)


center_lat = (min_lat + max_lat) / 2
center_lon = (min_lon + max_lon) / 2


print("\nGeographic extent:")
print(f"Minimum latitude : {min_lat:.8f}")
print(f"Maximum latitude : {max_lat:.8f}")
print(f"Minimum longitude: {min_lon:.8f}")
print(f"Maximum longitude: {max_lon:.8f}")

print("\nApproximate geographic center:")
print(f"Latitude : {center_lat:.8f}")
print(f"Longitude: {center_lon:.8f}")


# ---------------------------------------------------------
# Find closest tile to a geographic target
# ---------------------------------------------------------

def closest_tile(target_lat, target_lon):

    return min(
        tiles,
        key=lambda tile: haversine_km(
            target_lat,
            target_lon,
            tile["latitude"],
            tile["longitude"]
        )
    )


selected_tiles = select_farthest_points(
    tiles,
    5
)

selected = {
    f"POINT_{index}": tile
    for index, tile in enumerate(
        selected_tiles,
        start=1
    )
}


# ---------------------------------------------------------
# Make sure we didn't accidentally select duplicate tiles
# ---------------------------------------------------------

unique_tile_ids = {
    tile["tile_id"]
    for tile in selected.values()
}

if len(unique_tile_ids) != len(selected):

    print("\nWARNING:")
    print(
        "Some geographic targets selected the same tile."
    )

    print(
        "We will inspect the result before making any API request."
    )


# ---------------------------------------------------------
# Print selected tiles
# ---------------------------------------------------------

print("\n" + "=" * 70)
print("SELECTED TILES")
print("=" * 70)

for label, tile in selected.items():

    print(
        f"{label:8s} "
        f"tile_id={tile['tile_id']:>4} "
        f"lat={tile['latitude']:.8f} "
        f"lon={tile['longitude']:.8f} "
        f"temp={tile['average_temperature']:.4f}"
    )


# ---------------------------------------------------------
# Pairwise distances
# ---------------------------------------------------------

print("\n" + "=" * 70)
print("PAIRWISE DISTANCES")
print("=" * 70)

distances = pairwise_distances(selected_tiles)

for item in distances:

    print(
        f"{item['tile_a']:>4} -> "
        f"{item['tile_b']:>4}: "
        f"{item['distance_km']:.3f} km"
    )


# ---------------------------------------------------------
# Save selected tiles
# ---------------------------------------------------------

OUTPUT_FILE.parent.mkdir(
    parents=True,
    exist_ok=True
)

with open(
    OUTPUT_FILE,
    "w",
    encoding="utf-8"
) as f:

    json.dump(
        selected,
        f,
        indent=2
    )


print("\n" + "=" * 70)
print("SAVED")
print("=" * 70)

print(OUTPUT_FILE)