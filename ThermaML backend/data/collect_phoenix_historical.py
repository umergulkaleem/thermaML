import argparse
import json
import math
from collections import Counter
from datetime import datetime
from pathlib import Path
import sys
import re

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

try:
    from data.fetch_and_cache import (
        CITIES,
        build_heatmap_payload,
        check_credit_balance,
        submit_heatmap_request,
    )
    from data.validate_data import validate_heatmap, validate_environment
except ModuleNotFoundError:
    from fetch_and_cache import (
        CITIES,
        build_heatmap_payload,
        check_credit_balance,
        submit_heatmap_request,
    )
    from validate_data import validate_heatmap, validate_environment


BASE_DIR = Path(__file__).resolve().parent
CITY = "phoenix"
HEATMAP_COST = 4_220
ENVIRONMENT_COST = 2_900
DATE_COST = HEATMAP_COST + 2 * ENVIRONMENT_COST
PREFERRED_CEILING = 500_000
ENVIRONMENT_ONLY_CEILING = 300_000
REFERENCE_HEATMAP = BASE_DIR / CITY / "raw" / "heatmaps" / "phoenix_2023-07-15_60m_tcm.json"
SELECTED_DATES_FILE = BASE_DIR / CITY / "metadata" / "selected_dates.json"
USAGE_LOG_FILE = BASE_DIR / CITY / "processed" / "api_usage_log.jsonl"
MANIFEST_FILE = BASE_DIR / CITY / "metadata" / "collection_manifest.json"
REPORT_FILE = BASE_DIR / CITY / "processed" / "phoenix_collection_report.json"
AVAILABILITY_PLAN_FILE = BASE_DIR / CITY / "metadata" / "availability_verification_plan.json"


def load_json(path):
    with open(path, "r", encoding="utf-8") as file:
        return json.load(file)


def load_selected_dates():
    selected = load_json(SELECTED_DATES_FILE)
    verified = selected.get("verified_dates", [])
    candidates = selected.get("candidate_dates", [])
    schedule = verified + candidates
    if len(schedule) != selected.get("target_date_count"):
        raise ValueError("Selected date schedule does not contain the target date count.")
    if len(schedule) != len(set(schedule)):
        raise ValueError("Selected date schedule contains duplicates.")
    for value in schedule:
        datetime.strptime(value, "%Y-%m-%d")
    if selected.get("availability_verified") is not True:
        return verified, selected
    if len(verified) != selected.get("target_date_count"):
        raise ValueError("Selected dates must contain exactly the target date count.")
    if len(verified) != len(set(verified)):
        raise ValueError("Selected dates contain duplicates.")
    for value in verified:
        datetime.strptime(value, "%Y-%m-%d")
    return sorted(verified), selected


def latest_persisted_usage():
    latest = None
    if not USAGE_LOG_FILE.exists():
        return None
    with open(USAGE_LOG_FILE, "r", encoding="utf-8") as file:
        for line in file:
            if not line.strip():
                continue
            entry = json.loads(line)
            used = entry.get("credits_after_used")
            if used is None:
                continue
            candidate = {
                "credits_used": int(used),
                "recorded_at_utc": entry.get("recorded_at_utc"),
            }
            if latest is None or candidate["credits_used"] > latest["credits_used"]:
                latest = candidate
    return latest


def credit_guard(current_used, remaining_dates):
    if current_used is None:
        raise RuntimeError("Persisted credit usage is unavailable.")
    maximum_cost = remaining_dates * DATE_COST
    projected = current_used + maximum_cost
    if projected > PREFERRED_CEILING:
        raise RuntimeError(
            f"Collection needs {maximum_cost:,} credits and would reach {projected:,}, "
            f"above the {PREFERRED_CEILING:,}-credit ceiling."
        )
    return {
        "current_used": current_used,
        "remaining_dates": remaining_dates,
        "maximum_cost": maximum_cost,
        "projected_usage": projected,
        "remaining_safety_margin": PREFERRED_CEILING - projected,
    }


def build_availability_plan(selection, persisted_usage):
    verified_dates = sorted(set(selection.get("verified_dates", [])))
    unresolved_dates = sorted(set(selection.get("candidate_dates", [])))
    verification_requests = len(unresolved_dates)
    verification_cost = verification_requests * HEATMAP_COST
    final_heatmap_requests = verification_requests
    final_environment_requests = verification_requests * 2
    final_collection_cost = (
        final_heatmap_requests * HEATMAP_COST
        + final_environment_requests * ENVIRONMENT_COST
    )
    current_used = persisted_usage["credits_used"] if persisted_usage else None
    projected_usage = current_used + verification_cost if current_used is not None else None
    return {
        "city": CITY,
        "status": "verification_planning_only",
        "availability_mechanism": {
            "separate_metadata_endpoint_found": False,
            "separate_calendar_or_date_catalog_found": False,
            "documented_supported_date_query_found": False,
            "evidence": [
                "The repository implements only POST /v1/heatmap for heatmap data.",
                "No historical availability endpoint or date-list metadata is present in the repository.",
                "The existing payload supports start_date but provides no availability-only operation.",
            ],
            "conclusion": (
                "Availability requires a full-AOI filter_type 3 heatmap request; "
                "there is no cheaper defensible verification mechanism in the repository."
            ),
        },
        "verified_dates": verified_dates,
        "unresolved_candidate_dates": unresolved_dates,
        "proposed_final_schedule": sorted(verified_dates + unresolved_dates),
        "date_selection_rationale": (
            "Deterministic monthly-15th dates distributed across January 2023 through "
            "June 2025, preserving the verified 2023-07-15 date. This is a proposed "
            "coverage schedule, not evidence that those dates are supported."
        ),
        "verification": {
            "request_type": "full Phoenix AOI heatmap",
            "filter_type": 3,
            "granularity": 60,
            "analytic_type": "tcm",
            "requests_required_for_unresolved_dates": verification_requests,
            "credits_per_verification_request": HEATMAP_COST,
            "worst_case_verification_credits": verification_cost,
            "environment_requests_during_verification": 0,
            "raw_response_policy": "Preserve each response and payload; validate the 845-tile grid before accepting a date.",
        },
        "conditional_final_collection": {
            "accepted_additional_dates": verification_requests,
            "heatmap_requests": final_heatmap_requests,
            "environment_requests": final_environment_requests,
            "worst_case_credits": final_collection_cost,
            "projected_usage_after_heatmaps_and_environment": (
                current_used + final_collection_cost
                if current_used is not None
                else None
            ),
            "remaining_margin_under_preferred_ceiling": (
                PREFERRED_CEILING - current_used - final_collection_cost
                if current_used is not None
                else None
            ),
            "no_double_counting_note": (
                "A successful verification heatmap is retained as the final heatmap artifact; "
                "only its two environment requests follow."
            ),
        },
        "credit_safety": {
            "persisted_usage": current_used,
            "preferred_ceiling": PREFERRED_CEILING,
            "projected_usage_after_verification": projected_usage,
            "remaining_margin_after_verification": (
                PREFERRED_CEILING - projected_usage
                if projected_usage is not None
                else None
            ),
            "safe_under_preferred_ceiling": (
                projected_usage is not None
                and projected_usage <= PREFERRED_CEILING
            ),
            "live_balance_required_before_authorized_verification": True,
        },
        "accepted_date_requirements": [
            "exactly 845 features",
            "tile IDs 0 through 844 with no duplicates or missing IDs",
            "geometry identical to the cached Phoenix reference grid",
            "numeric average_temperature, min_temperature, and max_temperature",
        ],
        "next_phase": (
            "Stop after this plan. After explicit authorization, verify unresolved dates "
            "sequentially with one full-AOI request per date; only accepted dates enter "
            "the final schedule and later receive two environmental requests."
        ),
    }


def save_availability_plan(plan):
    AVAILABILITY_PLAN_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(AVAILABILITY_PLAN_FILE, "w", encoding="utf-8") as file:
        json.dump(plan, file, indent=2)


def reference_features():
    report = validate_heatmap(REFERENCE_HEATMAP)
    return report["features"], {feature["tile_id"]: feature for feature in report["features"]}


def with_tile_center(tile, date):
    polygon = tile["polygon"]
    return {
        **tile,
        "date": date,
        "latitude": sum(point[1] for point in polygon) / len(polygon),
        "longitude": sum(point[0] for point in polygon) / len(polygon),
    }


def validate_collected_heatmap(path, reference_by_id, expected_date):
    report = validate_heatmap(path)
    if report["feature_count"] != len(reference_by_id):
        raise ValueError(f"Expected {len(reference_by_id)} heatmap features, got {report['feature_count']}.")
    returned_ids = set(report["tile_ids"])
    reference_ids = set(reference_by_id)
    if returned_ids != reference_ids:
        raise ValueError("Heatmap tile IDs do not match the reference grid.")

    geometry_mismatches = []
    for feature in report["features"]:
        reference = reference_by_id[feature["tile_id"]]
        if feature["polygon"] != reference["polygon"]:
            geometry_mismatches.append(feature["tile_id"])
    if geometry_mismatches:
        raise ValueError(f"Heatmap geometry mismatch for tiles: {geometry_mismatches[:10]}")
    return {
        "date": expected_date,
        "feature_count": report["feature_count"],
        "expected_feature_count": len(reference_by_id),
        "missing_tile_ids": sorted(reference_ids - returned_ids),
        "duplicate_tile_ids": [],
        "geometry_mismatches": geometry_mismatches,
        "missing_temperature_tiles": [
            feature["tile_id"]
            for feature in report["features"]
            if any(feature[field] is None for field in ("average_temperature", "min_temperature", "max_temperature"))
        ],
        "temperature_range": {
            "min": min(feature["min_temperature"] for feature in report["features"]),
            "max": max(feature["max_temperature"] for feature in report["features"]),
        },
    }


def validate_environment_result(result, tile):
    locations = result.get("locations") if isinstance(result, dict) else None
    metadata = result.get("metadata") if isinstance(result, dict) else None
    timestamps = metadata.get("timestamps") if isinstance(metadata, dict) else None
    if not isinstance(locations, list) or len(locations) != 1:
        raise ValueError("Environment response must contain exactly one location.")
    if not isinstance(timestamps, list) or len(timestamps) != 24:
        raise ValueError("Environment response must contain 24 timestamps.")
    parsed = []
    for timestamp in timestamps:
        parsed.append(datetime.fromisoformat(str(timestamp).replace("Z", "+00:00")))
    if len(set(parsed)) != 24:
        raise ValueError("Environment response contains duplicate timestamps.")
    if {value.date().isoformat() for value in parsed} != {tile["date"]}:
        raise ValueError("Environment timestamps do not cover the requested date.")

    location = locations[0]
    for field in ("lat", "lon", "temperature"):
        if field not in location or location[field] is None or not math.isfinite(float(location[field])):
            raise ValueError(f"Environment location has invalid {field}.")
    if abs(float(location["lat"]) - float(tile["latitude"])) > 0.001 or abs(float(location["lon"]) - float(tile["longitude"])) > 0.001:
        raise ValueError("Environment coordinates do not correspond to the requested tile.")

    parameters = location.get("parameters", {})
    if not isinstance(parameters, dict):
        raise ValueError("Environment parameters are missing.")
    parameter_lengths = {len(values) for values in parameters.values() if isinstance(values, list)}
    if parameter_lengths != {24}:
        raise ValueError(f"Environmental parameter arrays are not all hourly: {parameter_lengths}")
    null_excluded = {
        name: sum(value is None for value in values)
        for name, values in parameters.items()
        if name in {"methane_ppb", "co2_ppm"}
        and isinstance(values, list)
    }
    return {
        "tile_id": tile["tile_id"],
        "location_count": len(locations),
        "hour_count": 24,
        "timestamps": timestamps,
        "parameter_names": sorted(parameters),
        "null_counts": null_excluded,
        "model_excluded_parameters": ["methane_ppb", "co2_ppm"],
    }


def load_manifest():
    if not MANIFEST_FILE.exists():
        return {"city": CITY, "records": []}
    return load_json(MANIFEST_FILE)


def save_manifest(manifest):
    MANIFEST_FILE.parent.mkdir(parents=True, exist_ok=True)
    temporary = MANIFEST_FILE.with_suffix(".tmp")
    with open(temporary, "w", encoding="utf-8") as file:
        json.dump(manifest, file, indent=2)
    temporary.replace(MANIFEST_FILE)


def append_audit(entry):
    USAGE_LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(USAGE_LOG_FILE, "a", encoding="utf-8") as file:
        file.write(json.dumps(entry, sort_keys=True) + "\n")


def verify_historical_dates(selection, reference_by_id):
    candidates = sorted(set(selection.get("candidate_dates", [])))
    results = []
    for index, date in enumerate(candidates):
        persisted = latest_persisted_usage()
        remaining = len(candidates) - index
        if persisted is None:
            raise RuntimeError("Persisted usage became unavailable during verification.")
        credit_guard(persisted["credits_used"], remaining)
        credits_before = check_credit_balance()
        if credits_before is None:
            raise RuntimeError("Live credit check failed before date verification.")
        if credits_before["used"] + remaining * HEATMAP_COST > PREFERRED_CEILING:
            raise RuntimeError("Live credit safety check failed before date verification.")

        config = dict(CITIES[CITY])
        config["date"] = date
        payload = build_heatmap_payload(config, filter_type=3)
        heatmap_path, _ = raw_paths(date, 426)
        result = {"date": date, "status": "failed", "payload": payload, "raw_response_file": str(heatmap_path)}
        try:
            response = submit_heatmap_request(payload)
            heatmap_path.parent.mkdir(parents=True, exist_ok=True)
            with open(heatmap_path, "x", encoding="utf-8") as file:
                json.dump(response["result"], file, indent=2)
            validation = validate_collected_heatmap(heatmap_path, reference_by_id, date)
            result.update({"status": "accepted", "activity_id": response.get("activity_id"), "validation": validation})
        except Exception as error:
            result["error"] = str(error)
        credits_after = check_credit_balance()
        result["credits_before_used"] = credits_before["used"]
        result["credits_after_used"] = credits_after["used"] if credits_after else None
        result["credit_delta"] = credits_after["used"] - credits_before["used"] if credits_after else None
        if result["credit_delta"] is not None and result["credit_delta"] > HEATMAP_COST:
            result["status"] = "cost_discrepancy"
            result["error"] = (
                f"Measured heatmap cost {result['credit_delta']} exceeds "
                f"known reference {HEATMAP_COST}."
            )
        append_audit({"city": CITY, "date": date, "request_type": "availability_verification", **result})
        results.append(result)
        if result["status"] == "cost_discrepancy":
            raise RuntimeError(result["error"])

    verification_file = BASE_DIR / CITY / "metadata" / "availability_verification_results.json"
    with open(verification_file, "w", encoding="utf-8") as file:
        json.dump(results, file, indent=2)
    return results


def raw_paths(date, tile_id):
    heatmap = BASE_DIR / CITY / "raw" / "heatmaps" / f"phoenix_{date}_60m_tcm.json"
    environment = BASE_DIR / CITY / "raw" / "environment" / f"phoenix_{date}_environment_tile_{tile_id}.json"
    return heatmap, environment


def existing_environment_path(date, tile_id):
    _, preferred = raw_paths(date, tile_id)
    candidates = [preferred]
    if date == "2023-07-15":
        if tile_id == 7:
            candidates.append(BASE_DIR / CITY / "raw" / "environment" / f"{CITY}_{date}_environment_tile_7.json")
        candidates.append(BASE_DIR / CITY / "raw" / "environment" / f"{CITY}_{date}_environment_20_points.json")
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return None


def load_environment_record(path, tile_id):
    raw = load_json(path)
    if not isinstance(raw, list):
        raise ValueError("Environment artifact must contain a list.")
    for record in raw:
        if int(record.get("tile", {}).get("tile_id", -1)) == tile_id:
            return record
    raise ValueError(f"Environment tile {tile_id} was not found in {path}.")


def inspect_existing_date(date, reference_by_id):
    heatmap_path, _ = raw_paths(date, 426)
    if not heatmap_path.exists():
        return None
    try:
        heatmap_report = validate_collected_heatmap(heatmap_path, reference_by_id, date)
    except (OSError, ValueError):
        return None
    environment_reports = []
    environment_files = []
    for tile_id in (426, 7):
        environment_path = existing_environment_path(date, tile_id)
        if environment_path is None:
            return None
        tile = next(feature for feature in reference_by_id.values() if feature["tile_id"] == tile_id)
        record = load_environment_record(environment_path, tile_id)
        environment_reports.append(validate_environment_result(record["environment"], with_tile_center(tile, date)))
        environment_files.append(str(environment_path))
    return {
        "date": date,
        "heatmap_status": "reused_valid",
        "environment_status": "reused_valid",
        "heatmap_tiles": heatmap_report["feature_count"],
        "environment_locations": [426, 7],
        "raw_files": [str(heatmap_path), *environment_files],
        "validation": {"heatmap": heatmap_report, "environment": environment_reports},
        "credits_used": 0,
    }


def collect_date(date, reference_by_id, live_used):
    manifest_record = {"date": date, "heatmap_status": "failed", "environment_status": "not_started"}
    config = dict(CITIES[CITY])
    config["date"] = date
    payload = build_heatmap_payload(config, filter_type=3)
    heatmap_path, _ = raw_paths(date, 426)
    response = None
    credits_before = None
    credits_after_heatmap = None
    if heatmap_path.exists():
        heatmap_validation = validate_collected_heatmap(heatmap_path, reference_by_id, date)
        manifest_record["heatmap_status"] = "reused_valid"
    else:
        credits_before = {"used": live_used}
        response = submit_heatmap_request(payload)
        heatmap_path.parent.mkdir(parents=True, exist_ok=True)
        with open(heatmap_path, "x", encoding="utf-8") as file:
            json.dump(response["result"], file, indent=2)
        credits_after_heatmap = check_credit_balance()
        append_audit({
            "city": CITY,
            "date": date,
            "request_type": "heatmap",
            "payload": payload,
            "activity_id": response.get("activity_id"),
            "raw_response_file": str(heatmap_path),
            "credits_before_used": credits_before["used"],
            "credits_after_used": credits_after_heatmap["used"] if credits_after_heatmap else None,
            "credit_delta": credits_after_heatmap["used"] - credits_before["used"] if credits_after_heatmap else None,
        })
        if credits_after_heatmap is None:
            raise RuntimeError("Could not measure heatmap credit delta after saving the raw response.")
        if credits_after_heatmap["used"] - credits_before["used"] > HEATMAP_COST:
            raise RuntimeError("Measured heatmap cost exceeded the known 4,220-credit reference.")
        heatmap_validation = validate_collected_heatmap(heatmap_path, reference_by_id, date)
        manifest_record["heatmap_status"] = "success"

    try:
        from data.resume_enviornment import submit_environment_request
    except ModuleNotFoundError:
        from resume_enviornment import submit_environment_request
    environment_reports = []
    environment_files = []
    for tile_id in (426, 7):
        tile = next(feature for feature in reference_by_id.values() if feature["tile_id"] == tile_id)
        environment_path = existing_environment_path(date, tile_id)
        if environment_path is not None:
            record = load_environment_record(environment_path, tile_id)
            environment_reports.append(validate_environment_result(record["environment"], with_tile_center(tile, date)))
            environment_files.append(str(environment_path))
            continue
        _, environment_path = raw_paths(date, tile_id)
        tile_request = with_tile_center(tile, date)
        before_environment = {
            "used": (
                credits_after_heatmap["used"]
                if credits_after_heatmap
                else live_used
            )
        }
        environment_response = submit_environment_request(tile_request, return_metadata=True, request_date=date)
        raw_record = [{"tile": tile_request, "environment": environment_response["result"]}]
        environment_path.parent.mkdir(parents=True, exist_ok=True)
        with open(environment_path, "x", encoding="utf-8") as file:
            json.dump(raw_record, file, indent=2)
        environment_reports.append(validate_environment_result(raw_record[0]["environment"], tile_request))
        environment_files.append(str(environment_path))
        after_environment = check_credit_balance()
        if after_environment is None:
            raise RuntimeError("Could not measure environment credit delta after saving the raw response.")
        if after_environment["used"] - before_environment["used"] > ENVIRONMENT_COST:
            raise RuntimeError("Measured environment cost exceeded the known 2,900-credit reference.")
        append_audit({
            "city": CITY,
            "date": date,
            "request_type": "environment",
            "tile_id": tile_id,
            "payload": {"latitude": tile["latitude"], "longitude": tile["longitude"], "temperature": tile["average_temperature"], "date_time": {"start_date": date, "filter_type": 3}},
            "activity_id": environment_response.get("activity_id"),
            "raw_response_file": str(environment_path),
            "credits_before_used": before_environment["used"],
            "credits_after_used": after_environment["used"] if after_environment else None,
            "credit_delta": after_environment["used"] - before_environment["used"] if after_environment else None,
        })
    manifest_record.update({
        "environment_status": "success",
        "heatmap_tiles": heatmap_validation["feature_count"],
        "environment_locations": [426, 7],
        "raw_files": [str(heatmap_path), *environment_files],
        "heatmap_activity_id": response.get("activity_id") if response else None,
        "heatmap_credit_delta": credits_after_heatmap["used"] - credits_before["used"] if credits_after_heatmap and credits_before else 0,
        "validation": {"heatmap": heatmap_validation, "environment": environment_reports},
    })
    return manifest_record


def build_report(manifest, persisted_usage):
    records = manifest.get("records", [])
    successful = [record for record in records if record.get("heatmap_status") in {"success", "reused_valid"} and record.get("environment_status") in {"success", "reused_valid"}]
    dates = sorted(record["date"] for record in successful)
    month_counts = Counter(date[:7] for date in dates)
    return {
        "city": CITY,
        "dates_requested": len(records),
        "successful_dates": len(successful),
        "failed_dates": len(records) - len(successful),
        "unique_tiles": 845 if successful else 0,
        "observations_per_tile": len(successful),
        "date_range": {"start": dates[0], "end": dates[-1]} if dates else None,
        "dates_by_month": dict(sorted(month_counts.items())),
        "temperature_distribution": "available in each validated heatmap record; no aggregation performed by collector",
        "environmental_coverage": {"locations_per_successful_date": 2, "tile_ids": [426, 7]},
        "missing_values": "raw environmental nulls preserved; methane_ppb and co2_ppm excluded from modeling",
        "total_persisted_credits": persisted_usage["credits_used"] if persisted_usage else None,
        "remaining_project_budget": PREFERRED_CEILING - persisted_usage["credits_used"] if persisted_usage else None,
        "chronological_split": {
            "method": "70/15/15 by sorted successful dates",
            "train_dates": dates[: int(len(dates) * 0.70)],
            "validation_dates": dates[int(len(dates) * 0.70): int(len(dates) * 0.85)],
            "test_dates": dates[int(len(dates) * 0.85):],
        },
    }


def existing_heatmap_dates():
    dates = []
    pattern = re.compile(r"^phoenix_(\d{4}-\d{2}-\d{2})_60m_tcm\.json$")
    for path in sorted((BASE_DIR / CITY / "raw" / "heatmaps").glob("phoenix_*_60m_tcm.json")):
        match = pattern.match(path.name)
        if match:
            dates.append(match.group(1))
    return sorted(set(dates))


def collect_environment_only(dates, reference_by_id, live_used):
    results = []
    for date in dates:
        heatmap_path, _ = raw_paths(date, 426)
        try:
            heatmap_validation = validate_collected_heatmap(heatmap_path, reference_by_id, date)
        except Exception as error:
            results.append({"date": date, "status": "failed", "error": f"Heatmap validation: {error}"})
            continue

        record = {
            "date": date,
            "heatmap_status": "reused_valid",
            "environment_status": "pending",
            "heatmap_tiles": heatmap_validation["feature_count"],
            "environment_locations": [],
            "raw_files": [str(heatmap_path)],
            "validation": {"heatmap": heatmap_validation, "environment": []},
            "credits_used": 0,
        }
        for tile_id in (426, 7):
            existing_path = existing_environment_path(date, tile_id)
            tile = reference_by_id[tile_id]
            if existing_path is not None:
                try:
                    environment_record = load_environment_record(existing_path, tile_id)
                    environment_validation = validate_environment_result(
                        environment_record["environment"],
                        with_tile_center(tile, date),
                    )
                    record["environment_locations"].append(tile_id)
                    record["raw_files"].append(str(existing_path))
                    record["validation"]["environment"].append(environment_validation)
                    continue
                except Exception as error:
                    record.setdefault("validation_failures", []).append(str(error))

            try:
                before = {"used": live_used}
                tile_request = with_tile_center(tile, date)
                from data.resume_enviornment import submit_environment_request
                response = submit_environment_request(
                    tile_request,
                    return_metadata=True,
                    request_date=date,
                )
                _, environment_path = raw_paths(date, tile_id)
                raw_record = [{"tile": tile_request, "environment": response["result"]}]
                environment_path.parent.mkdir(parents=True, exist_ok=True)
                with open(environment_path, "x", encoding="utf-8") as file:
                    json.dump(raw_record, file, indent=2)
                validation = validate_environment_result(raw_record[0]["environment"], tile_request)
                after = check_credit_balance()
                if after is None:
                    raise RuntimeError("Could not measure environment credit delta.")
                delta = after["used"] - before["used"]
                if delta > ENVIRONMENT_COST:
                    raise RuntimeError(f"Environment cost {delta} exceeded {ENVIRONMENT_COST}.")
                append_audit({
                    "city": CITY,
                    "date": date,
                    "request_type": "environment_only",
                    "tile_id": tile_id,
                    "payload": {"latitude": tile_request["latitude"], "longitude": tile_request["longitude"], "temperature": tile_request["average_temperature"], "date_time": {"start_date": date, "filter_type": 3}},
                    "activity_id": response.get("activity_id"),
                    "raw_response_file": str(environment_path),
                    "credits_before_used": before["used"],
                    "credits_after_used": after["used"],
                    "credit_delta": delta,
                    "validation": validation,
                })
                live_used = after["used"]
                record["environment_locations"].append(tile_id)
                record["raw_files"].append(str(environment_path))
                record["validation"]["environment"].append(validation)
                record["credits_used"] += delta
            except Exception as error:
                record.setdefault("validation_failures", []).append(
                    f"tile {tile_id}: {error}"
                )
                record["environment_status"] = "failed"
                results.append(record)
                break
        else:
            record["environment_status"] = (
                "success" if len(record["environment_locations"]) == 2 else "failed"
            )
            results.append(record)
    return results


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--authorize", action="store_true")
    parser.add_argument("--authorize-availability", action="store_true")
    parser.add_argument("--environment-only", action="store_true")
    args = parser.parse_args()
    dates, selection = load_selected_dates()
    schedule = sorted(set(dates + selection.get("candidate_dates", [])))
    collection_dates = schedule if args.authorize else dates
    persisted = latest_persisted_usage()
    reference, reference_by_id = reference_features()
    if args.environment_only:
        heatmap_dates = existing_heatmap_dates()
        missing_requests = 0
        reusable_dates = []
        for date in heatmap_dates:
            missing = 0
            for tile_id in (426, 7):
                path = existing_environment_path(date, tile_id)
                if path is None:
                    missing += 1
                    continue
                try:
                    record = load_environment_record(path, tile_id)
                    validate_environment_result(record["environment"], with_tile_center(reference_by_id[tile_id], date))
                except Exception:
                    missing += 1
            missing_requests += missing
            if missing == 0:
                reusable_dates.append(date)
        persisted = latest_persisted_usage()
        maximum_cost = missing_requests * ENVIRONMENT_COST
        projected = persisted["credits_used"] + maximum_cost if persisted else None
        print(json.dumps({
            "mode": "environment_only",
            "heatmap_dates": heatmap_dates,
            "environment_requests_required": missing_requests,
            "environment_cost_per_request": ENVIRONMENT_COST,
            "maximum_environment_credits": maximum_cost,
            "persisted_usage": persisted["credits_used"] if persisted else None,
            "projected_usage": projected,
            "ceiling": ENVIRONMENT_ONLY_CEILING,
            "remaining_margin": ENVIRONMENT_ONLY_CEILING - projected if projected is not None else None,
            "reusable_complete_dates": reusable_dates,
            "authorized": args.authorize,
            "heatmap_requests": 0,
        }, indent=2))
        if not args.authorize:
            return
        if persisted is None or projected > ENVIRONMENT_ONLY_CEILING:
            raise RuntimeError("Environment-only credit safety check failed.")
        live = check_credit_balance()
        if live is None or live["used"] + maximum_cost > ENVIRONMENT_ONLY_CEILING:
            raise RuntimeError("Live environment-only credit preflight failed.")
        results = collect_environment_only(heatmap_dates, reference_by_id, live["used"])
        manifest = load_manifest()
        manifest["environment_only_dates"] = heatmap_dates
        manifest["environment_only_records"] = results
        save_manifest(manifest)
        print(json.dumps({
            "mode": "environment_only",
            "successful_dates": [item["date"] for item in results if item.get("environment_status") == "success"],
            "failed_dates": [item["date"] for item in results if item.get("environment_status") != "success"],
            "environment_requests": sum(item.get("credits_used", 0) > 0 for item in results),
        }, indent=2))
        return
    availability_plan = build_availability_plan(selection, persisted)
    save_availability_plan(availability_plan)
    existing = []
    pending = []
    for date in sorted(set(collection_dates)):
        record = inspect_existing_date(date, reference_by_id)
        (existing if record else pending).append(record or date)
    guard = credit_guard(persisted["credits_used"] if persisted else None, len(pending))
    print(json.dumps({
        "selected_dates": schedule,
        "requestable_verified_dates": dates,
        "expected_api_requests": len(pending) * 3,
        "maximum_possible_credits": guard["maximum_cost"],
        "current_persisted_usage": guard["current_used"],
        "projected_maximum_usage": guard["projected_usage"],
        "remaining_safety_margin": guard["remaining_safety_margin"],
        "existing_valid_dates_skipped": [record["date"] for record in existing],
        "availability_verified": selection.get("availability_verified", False),
        "availability_plan_file": str(AVAILABILITY_PLAN_FILE),
        "availability_verification_requests": availability_plan["verification"]["requests_required_for_unresolved_dates"],
        "availability_verification_credits": availability_plan["verification"]["worst_case_verification_credits"],
        "conditional_final_heatmap_requests": availability_plan["conditional_final_collection"]["heatmap_requests"],
        "conditional_final_environment_requests": availability_plan["conditional_final_collection"]["environment_requests"],
        "conditional_final_collection_credits": availability_plan["conditional_final_collection"]["worst_case_credits"],
        "conditional_final_projected_usage": availability_plan["conditional_final_collection"]["projected_usage_after_heatmaps_and_environment"],
        "authorize_availability": args.authorize_availability,
        "authorized": args.authorize,
    }, indent=2))
    if args.authorize_availability:
        results = verify_historical_dates(selection, reference_by_id)
        print(json.dumps({
            "verification_completed": True,
            "accepted_dates": [result["date"] for result in results if result["status"] == "accepted"],
            "rejected_dates": [result["date"] for result in results if result["status"] != "accepted"],
        }, indent=2))
        return
    if not args.authorize:
        return
    live_credits = check_credit_balance()
    if live_credits is None:
        raise RuntimeError("Live credit preflight failed; refusing collection.")
    if live_credits["used"] + guard["maximum_cost"] > PREFERRED_CEILING:
        raise RuntimeError("Live credit preflight cannot safely cover the remaining collection.")
    manifest = load_manifest()
    manifest.setdefault("city", CITY)
    manifest["scheduled_dates"] = schedule
    manifest.setdefault("records", [])
    known_dates = {record["date"] for record in manifest["records"]}
    for record in existing:
        if record["date"] not in known_dates:
            manifest["records"].append(record)
    for date in pending:
        remaining = sum(1 for candidate in pending if candidate >= date)
        current = latest_persisted_usage()
        credit_guard(current["credits_used"] if current else None, remaining)
        try:
            record = collect_date(date, reference_by_id, live_credits["used"])
        except Exception as error:
            record = {"date": date, "heatmap_status": "failed", "environment_status": "failed", "error": str(error)}
        manifest["records"] = [item for item in manifest["records"] if item["date"] != date]
        manifest["records"].append(record)
        save_manifest(manifest)
    report = build_report(manifest, latest_persisted_usage())
    REPORT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(REPORT_FILE, "w", encoding="utf-8") as file:
        json.dump(report, file, indent=2)
    save_manifest(manifest)


if __name__ == "__main__":
    main()
