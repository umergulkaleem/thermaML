import collect_phoenix_environment_tiles_8_844 as collector


collector.TILES = (420, 814)
collector.OUTPUT_DIR = collector.BASE_DIR / "phoenix" / "raw" / "environment_tiles_420_814"
collector.REPORT_FILE = collector.BASE_DIR / "phoenix" / "processed" / "phoenix_environment_tiles_420_814_report.json"
collector.RECOVERY_ACTIVITIES = {
    ("2023-04-01", 814): "fbd39377-ff36-4747-8d62-56421c3893ff",
    ("2023-07-01", 420): "8df5f79b-6d91-4195-be8d-391de388f8d2",
    ("2023-07-01", 814): "92678c29-5c98-4d36-bcf2-8ec6a15ea2d3",
    ("2023-09-01", 420): "85e11456-65de-4e37-84d0-ce7dfbd4cae5",
    ("2023-12-15", 420): "0bc24c63-a036-477c-af09-0b0675244be3",
    ("2024-01-15", 420): "306c5be2-be4d-4a32-b438-1e4230b004ac",
}


if __name__ == "__main__":
    result = collector.collect()
    print({
        "successful_request_count": result["successful_request_count"],
        "successful_observation_count": result["successful_observation_count"],
        "output_directory": result["output_directory"],
    })
