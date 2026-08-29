import math


def haversine_km(lat1, lon1, lat2, lon2):
    """Return the great-circle distance between two coordinates in km."""

    radius_km = 6371.0

    lat1 = math.radians(lat1)
    lat2 = math.radians(lat2)
    delta_lat = lat2 - lat1
    delta_lon = math.radians(lon2 - lon1)

    value = (
        math.sin(delta_lat / 2) ** 2
        + math.cos(lat1)
        * math.cos(lat2)
        * math.sin(delta_lon / 2) ** 2
    )

    return 2 * radius_km * math.asin(math.sqrt(value))


def _validate_tiles(tiles):

    if not tiles:
        raise ValueError("At least one tile is required.")

    tile_ids = []

    for tile in tiles:

        for field in ("tile_id", "latitude", "longitude"):

            if field not in tile:
                raise ValueError(
                    f"Tile is missing required field '{field}'."
                )

        tile_ids.append(int(tile["tile_id"]))

    if len(tile_ids) != len(set(tile_ids)):
        raise ValueError("Tile IDs must be unique.")


def select_farthest_points(tiles, sample_count):
    """Select spatially separated existing tiles deterministically.

    The first point is the tile nearest the geographic center. Each next
    point maximizes its distance to the already selected set.
    """

    _validate_tiles(tiles)

    if sample_count < 1:
        raise ValueError("sample_count must be at least one.")

    if sample_count >= len(tiles):
        return list(tiles)

    center_latitude = sum(
        float(tile["latitude"])
        for tile in tiles
    ) / len(tiles)

    center_longitude = sum(
        float(tile["longitude"])
        for tile in tiles
    ) / len(tiles)

    first = min(
        tiles,
        key=lambda tile: (
            haversine_km(
                float(tile["latitude"]),
                float(tile["longitude"]),
                center_latitude,
                center_longitude,
            ),
            int(tile["tile_id"]),
        ),
    )

    selected = [first]
    selected_ids = {int(first["tile_id"])}

    while len(selected) < sample_count:

        candidates = [
            tile
            for tile in tiles
            if int(tile["tile_id"]) not in selected_ids
        ]

        next_tile = max(
            candidates,
            key=lambda tile: (
                min(
                    haversine_km(
                        float(tile["latitude"]),
                        float(tile["longitude"]),
                        float(selected_tile["latitude"]),
                        float(selected_tile["longitude"]),
                    )
                    for selected_tile in selected
                ),
                -int(tile["tile_id"]),
            ),
        )

        selected.append(next_tile)
        selected_ids.add(int(next_tile["tile_id"]))

    return selected


def pairwise_distances(tiles):

    distances = []

    for first_index, first in enumerate(tiles):

        for second in tiles[first_index + 1:]:

            distances.append({
                "tile_a": int(first["tile_id"]),
                "tile_b": int(second["tile_id"]),
                "distance_km": haversine_km(
                    float(first["latitude"]),
                    float(first["longitude"]),
                    float(second["latitude"]),
                    float(second["longitude"]),
                ),
            })

    return distances
