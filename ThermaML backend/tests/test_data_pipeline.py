import copy
import unittest

from data.process_models import parse_feature
from data.spatial_sampling import pairwise_distances, select_farthest_points
from data.validate_data import (
    HEATMAP_FILE,
    ENVIRONMENT_FILE,
    validate_files,
    validate_heatmap,
)
from data.measure_range_of_hours_heatmap import (
    assert_credit_safety,
    build_proposed_payload,
    spatial_correspondence,
    validate_temporal_response,
)
from data.collect_phoenix_historical import (
    DATE_COST,
    build_availability_plan,
    credit_guard,
    load_selected_dates,
    validate_environment_result,
)
from data.assemble_phoenix_dataset import daily_features, summarize_series


class DataPipelineTests(unittest.TestCase):

    def test_cached_files_validate_and_associate(self):

        report = validate_files(
            HEATMAP_FILE,
            ENVIRONMENT_FILE,
        )

        self.assertEqual(report["heatmap"]["feature_count"], 845)
        self.assertEqual(report["environment"]["result_count"], 9)

    def test_heatmap_temperatures_are_required(self):

        heatmap = validate_heatmap(HEATMAP_FILE)
        feature = copy.deepcopy(
            load_raw_features()[0]
        )
        del feature["properties"]["average_temperature"]

        with self.assertRaises(ValueError):
            parse_feature(feature, 0, "test-heatmap.json")

        self.assertIsNotNone(heatmap["features"][0]["average_temperature"])

    def test_farthest_point_sample_is_unique_and_separated(self):

        parsed = validate_heatmap(HEATMAP_FILE)["features"]
        tiles = [
            {
                "tile_id": feature["tile_id"],
                "latitude": sum(
                    point[1]
                    for point in feature["polygon"]
                ) / len(feature["polygon"]),
                "longitude": sum(
                    point[0]
                    for point in feature["polygon"]
                ) / len(feature["polygon"]),
            }
            for feature in parsed
        ]

        selected = select_farthest_points(tiles, 5)
        distances = pairwise_distances(selected)

        self.assertEqual(len(selected), 5)
        self.assertEqual(
            len({tile["tile_id"] for tile in selected}),
            5,
        )
        self.assertGreater(
            min(item["distance_km"] for item in distances),
            1.0,
        )

    def test_range_scalar_temperature_is_not_hourly(self):

        result = {
            "map_data": {"features": [{
                "id": "0",
                "properties": {"tile_id": 0, "average_temperature": 41.2},
                "geometry": {"coordinates": [[[0, 0], [1, 0], [1, 1], [0, 0]]]},
            }]},
        }

        report = validate_temporal_response(result)

        self.assertEqual(report["temperature_observation_counts"], [1])
        self.assertFalse(report["has_24_hourly_observations"])
        self.assertFalse(report["usable_for_hourly_targets"])

    def test_range_payload_uses_documented_fields(self):

        payload = build_proposed_payload()

        self.assertEqual(payload["granularity"], 60)
        self.assertEqual(payload["analytic_type"], "tcm")
        self.assertEqual(
            payload["date_time"],
            {
                "start_date": "2023-07-15",
                "start_time": "00:00",
                "end_time": "23:00",
                "filter_type": 2,
            },
        )

    def test_temporal_validator_rejects_duplicate_timestamps(self):

        result = {
            "map_data": {"features": [{
                "properties": {
                    "average_temperature": [40.0, 41.0],
                    "timestamps": [
                        "2023-07-15T00:00:00-07:00",
                        "2023-07-15T00:00:00-07:00",
                    ],
                },
                "geometry": {"coordinates": [[[0, 0], [1, 0], [1, 1]]]},
            }]},
        }

        report = validate_temporal_response(result, expected_observations=2)

        self.assertEqual(len(report["duplicate_timestamps"]), 1)
        self.assertFalse(report["usable_for_hourly_targets"])

    def test_temporal_validator_reports_missing_temperature(self):

        result = {"map_data": {"features": [{
            "properties": {"tile_id": 1},
            "geometry": {"coordinates": [[[0, 0], [1, 0], [1, 1]]]},
        }]}}

        report = validate_temporal_response(result)

        self.assertEqual(report["missing_temperature_features"], [0])
        self.assertFalse(report["usable_for_hourly_targets"])

    def test_spatial_correspondence_rejects_distant_match(self):

        cached = {"map_data": {"features": [{
            "properties": {"tile_id": 426},
            "geometry": {"coordinates": [[[0, 0], [0.001, 0], [0.001, 0.001], [0, 0]]]},
        }]}}
        returned = {"map_data": {"features": [{
            "properties": {"tile_id": 0, "average_temperature": 41.2},
            "geometry": {"coordinates": [[[0.01, 0.01], [0.011, 0.01], [0.011, 0.011], [0.01, 0.01]]]},
        }]}}

        report = spatial_correspondence(returned, cached)

        self.assertEqual(report["matches"][0]["returned_tile_id"], 0)
        self.assertIsNone(report["matches"][0]["matched_cached_tile_id"])
        self.assertFalse(report["all_matches_reliable"])

    def test_credit_safety_requires_known_cost_and_respects_ceiling(self):

        with self.assertRaises(ValueError):
            assert_credit_safety(None)
        with self.assertRaises(RuntimeError):
            assert_credit_safety(498_000)
        self.assertTrue(assert_credit_safety(91_760)["safe"])

    def test_collection_credit_guard_uses_two_environment_requests_per_date(self):

        report = credit_guard(95_980, 29)

        self.assertEqual(DATE_COST, 10_020)
        self.assertEqual(report["maximum_cost"], 290_580)
        self.assertEqual(report["projected_usage"], 386_560)
        self.assertEqual(report["remaining_safety_margin"], 113_440)

    def test_selected_dates_are_not_authorized_until_availability_is_verified(self):

        verified_dates, selection = load_selected_dates()

        self.assertEqual(verified_dates, ["2023-07-15"])
        self.assertFalse(selection["availability_verified"])

    def test_environment_validation_requires_24_unique_same_date_timestamps(self):

        timestamps = [f"2023-07-15T{hour:02d}:00:00-07:00" for hour in range(24)]
        result = {
            "metadata": {"timestamps": timestamps},
            "locations": [{
                "lat": 33.45250270988613,
                "lon": -112.07513939144442,
                "temperature": 39.427,
                "parameters": {
                    "relative_humidity_percent": [40.0] * 24,
                    "methane_ppb": [None] * 24,
                    "co2_ppm": [None] * 24,
                },
            }],
        }
        tile = {
            "tile_id": 426,
            "latitude": 33.45250270988613,
            "longitude": -112.07513939144442,
            "date": "2023-07-15",
        }

        report = validate_environment_result(result, tile)

        self.assertEqual(report["hour_count"], 24)
        self.assertEqual(report["null_counts"]["methane_ppb"], 24)

    def test_availability_plan_requires_one_full_heatmap_per_unresolved_date(self):

        selection = {
            "verified_dates": ["2023-07-15"],
            "candidate_dates": ["2023-01-15", "2024-01-15"],
        }
        plan = build_availability_plan(
            selection,
            {"credits_used": 95_980},
        )

        self.assertFalse(
            plan["availability_mechanism"]["separate_metadata_endpoint_found"]
        )
        self.assertEqual(
            plan["verification"]["requests_required_for_unresolved_dates"],
            2,
        )
        self.assertEqual(
            plan["verification"]["worst_case_verification_credits"],
            8_440,
        )
        self.assertEqual(
            plan["credit_safety"]["projected_usage_after_verification"],
            104_420,
        )

    def test_environment_features_are_daily_summaries_not_repeated_targets(self):

        environment = {
            "tile_id": 426,
            "parameters": {
                "relative_humidity_percent": [40.0, 50.0],
                "precipitation_mm": [1.0, 2.0],
                "methane_ppb": [None, None],
            },
        }

        features = daily_features(environment)

        self.assertEqual(
            features["env_tile_426_relative_humidity_percent_mean"],
            45.0,
        )
        self.assertEqual(
            features["env_tile_426_precipitation_mm_sum"],
            3.0,
        )
        self.assertNotIn("methane_ppb", " ".join(features))
        self.assertEqual(summarize_series([None, 2.0], "mean")["valid_count"], 1)


def load_raw_features():

    import json

    with open(HEATMAP_FILE, "r", encoding="utf-8") as file:
        return json.load(file)["map_data"]["features"]


if __name__ == "__main__":
    unittest.main()
