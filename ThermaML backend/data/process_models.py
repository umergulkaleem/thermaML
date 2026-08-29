import os
import json
import glob
import math


# ============================================================
# PATHS
# ============================================================

BASE_DIR = os.path.dirname(
    os.path.abspath(__file__)
)


def load_heatmap_features(raw_json, source_path):

    if not isinstance(raw_json, dict):

        raise ValueError(
            f"Heatmap must be a JSON object: {source_path}"
        )

    map_data = raw_json.get(
        "map_data"
    )

    if not isinstance(map_data, dict):

        raise ValueError(
            f"Missing object 'map_data': {source_path}"
        )

    features = map_data.get(
        "features"
    )

    if not isinstance(features, list) or not features:

        raise ValueError(
            f"Missing non-empty 'map_data.features': "
            f"{source_path}"
        )

    return features


def parse_feature(feature, feature_index, source_path):

    if not isinstance(feature, dict):

        raise ValueError(
            f"Feature {feature_index} is not an object: "
            f"{source_path}"
        )

    properties = feature.get(
        "properties"
    )

    geometry = feature.get(
        "geometry"
    )

    if not isinstance(properties, dict):

        raise ValueError(
            f"Feature {feature_index} is missing properties: "
            f"{source_path}"
        )

    if not isinstance(geometry, dict):

        raise ValueError(
            f"Feature {feature_index} is missing geometry: "
            f"{source_path}"
        )

    tile_id = properties.get(
        "tile_id",
        feature.get("id")
    )

    if tile_id is None:

        raise ValueError(
            f"Feature {feature_index} is missing tile_id: "
            f"{source_path}"
        )

    try:
        tile_id = int(tile_id)
    except (TypeError, ValueError) as error:

        raise ValueError(
            f"Feature {feature_index} has invalid tile_id "
            f"{tile_id!r}: {source_path}"
        ) from error

    average_temperature = properties.get(
        "average_temperature"
    )

    if average_temperature is None:

        raise ValueError(
            f"Feature {feature_index} is missing required "
            f"average_temperature: {source_path}"
        )

    try:
        average_temperature = float(
            average_temperature
        )
    except (TypeError, ValueError) as error:

        raise ValueError(
            f"Feature {feature_index} has invalid "
            f"average_temperature: {source_path}"
        ) from error

    if not math.isfinite(average_temperature):

        raise ValueError(
            f"Feature {feature_index} has non-finite "
            f"average_temperature: {source_path}"
        )

    coordinates = geometry.get(
        "coordinates"
    )

    if not isinstance(coordinates, list) or not coordinates:

        raise ValueError(
            f"Feature {feature_index} has invalid coordinates: "
            f"{source_path}"
        )

    polygon = coordinates[0]

    if not isinstance(polygon, list) or len(polygon) < 3:

        raise ValueError(
            f"Feature {feature_index} has an invalid polygon: "
            f"{source_path}"
        )

    points = []

    for point in polygon:

        if (
            not isinstance(point, list)
            or len(point) < 2
        ):

            raise ValueError(
                f"Feature {feature_index} has an invalid "
                f"polygon point: {source_path}"
            )

        try:
            longitude = float(point[0])
            latitude = float(point[1])
        except (TypeError, ValueError) as error:

            raise ValueError(
                f"Feature {feature_index} has non-numeric "
                f"coordinates: {source_path}"
            ) from error

        if not math.isfinite(longitude) or not math.isfinite(latitude):

            raise ValueError(
                f"Feature {feature_index} has non-finite "
                f"coordinates: {source_path}"
            )

        points.append((longitude, latitude))

    return {
        "tile_id": tile_id,
        "polygon": points,
        "geometry": geometry,
        "average_temperature": average_temperature,
        "min_temperature": properties.get(
            "min_temperature"
        ),
        "max_temperature": properties.get(
            "max_temperature"
        )
    }


# ============================================================
# PROCESS ONE CITY
# ============================================================

def process_city(city):

    city_dir = os.path.join(
        BASE_DIR,
        city
    )

    raw_dir = os.path.join(
        city_dir,
        "raw",
        "heatmaps"
    )

    processed_dir = os.path.join(
        city_dir,
        "processed"
    )

    os.makedirs(
        processed_dir,
        exist_ok=True
    )

    raw_files = glob.glob(
        os.path.join(
            raw_dir,
            "*.json"
        )
    )

    if not raw_files:

        raise FileNotFoundError(
            f"No raw heatmap files found for "
            f"{city} at {raw_dir}"
        )

    all_nodes = []

    # --------------------------------------------------------
    # PROCESS EVERY HEATMAP FILE
    # --------------------------------------------------------

    for raw_file in raw_files:

        print()
        print(
            f"Processing: "
            f"{os.path.basename(raw_file)}"
        )

        with open(
            raw_file,
            "r",
            encoding="utf-8"
        ) as f:

            raw_json = json.load(f)

        features = load_heatmap_features(
            raw_json,
            raw_file
        )

        # Extract date from filename
        filename = os.path.basename(
            raw_file
        )

        date = filename.split("_")[1]

        for idx, feature in enumerate(
            features
        ):

            parsed_feature = parse_feature(
                feature,
                idx,
                raw_file
            )

            polygon = parsed_feature[
                "polygon"
            ]

            # ------------------------------------------------
            # CENTROID
            # ------------------------------------------------

            lon = sum(
                point[0]
                for point in polygon
            ) / len(polygon)

            lat = sum(
                point[1]
                for point in polygon
            ) / len(polygon)

            # ------------------------------------------------
            # NODE
            # ------------------------------------------------

            node = {

                "node_id": (
                    f"{city}_"
                    f"{date}_"
                    f"{parsed_feature['tile_id']}"
                ),

                "city": city,

                "date": date,

                "tile_id": parsed_feature[
                    "tile_id"
                ],

                "lat": float(lat),

                "lon": float(lon),

                "baseline_temp": parsed_feature[
                    "average_temperature"
                ],

                "min_temperature": parsed_feature[
                    "min_temperature"
                ],

                "max_temperature": parsed_feature[
                    "max_temperature"
                ]
            }

            all_nodes.append(node)

    # ========================================================
    # SAVE
    # ========================================================

    output_path = os.path.join(
        processed_dir,
        f"{city}_nodes.json"
    )

    with open(
        output_path,
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            all_nodes,
            f,
            indent=2
        )

    print()
    print("=" * 60)
    print("PROCESSING COMPLETE")
    print("=" * 60)

    print(
        f"City       : {city}"
    )

    print(
        f"Files      : {len(raw_files)}"
    )

    print(
        f"Nodes      : {len(all_nodes):,}"
    )

    print(
        f"Output     : {output_path}"
    )

    print("=" * 60)


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":

    # Only Phoenix for now.

    process_city("phoenix")