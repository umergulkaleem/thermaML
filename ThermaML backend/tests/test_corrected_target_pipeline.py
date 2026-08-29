"""
Regression tests for the corrected target pipeline.

These tests were added after diagnosing that locations[0]["temperature"] is a
static geographic tile temperature (constant per tile, not date-varying) and
therefore invalid as a temporal ML target.

The corrected target is mean(apparent_temperature_celsius hourly values) for the
exact tile/date, which ranges from ~2°C to ~39°C across the dataset.
"""
import json
import math
from pathlib import Path

import numpy as np
import pytest

from data.daily_temperature_pipeline import (
    FEATURE_VERSION,
    VALID_TILES,
    _TARGET_PARAMETER,
    _feature_matrix,
    build_daily_temperature_dataset,
)


# ---------------------------------------------------------------------------
# Target correctness
# ---------------------------------------------------------------------------

def test_target_varies_by_date_for_same_tile():
    """Different dates must produce different target values for tile 8."""
    df = build_daily_temperature_dataset()
    tile8 = df[df["tile_id"] == 8]
    assert tile8["temperature"].nunique() > 5, (
        "Target for tile 8 should have many distinct values across dates; "
        "if it is near-constant the static locations[0].temperature bug has returned."
    )


def test_target_range_is_consistent_with_apparent_temperature():
    """
    Mean apparent_temperature_celsius across Phoenix dates should produce
    targets in a plausible range for Arizona (winter nights ~2°C to summer
    afternoons ~40°C).
    """
    df = build_daily_temperature_dataset()
    assert df["temperature"].min() > -10, "Target below -10°C is implausible for Phoenix."
    assert df["temperature"].max() < 50, "Target above 50°C is implausible."
    assert df["temperature"].std() > 5, (
        "Target std < 5°C suggests near-constant values — "
        "the static tile temperature bug may have returned."
    )


def test_static_tile_temperature_not_used_as_target():
    """
    The known static tile temperatures (constant per tile, sent in the
    request_payload) must NOT be the dataset target.

    Tile 8 static value: 39.4325
    Tile 844 static value: 39.3848
    etc.

    If the target for any (tile, date) pair equals the known static value
    exactly, the bug has returned.
    """
    KNOWN_STATIC_TEMPS = {
        7: 39.3804,
        8: 39.4325,
        420: 39.4395,
        426: 39.4270,
        814: 39.4538,
        844: 39.3848,
    }
    df = build_daily_temperature_dataset()
    for tile_id, static_val in KNOWN_STATIC_TEMPS.items():
        tile_rows = df[df["tile_id"] == tile_id]
        if tile_rows.empty:
            continue
        # All rows for this tile must differ from the static value.
        matching = tile_rows[(tile_rows["temperature"] - static_val).abs() < 0.001]
        assert matching.empty, (
            f"Tile {tile_id}: target value {static_val:.4f} looks like the "
            "static locations[0].temperature. The old target bug may have returned."
        )


def test_target_is_finite_for_all_records():
    df = build_daily_temperature_dataset()
    assert df["temperature"].notna().all(), "Target contains NaN values."
    assert df["temperature"].apply(math.isfinite).all(), "Target contains inf values."


def test_tile_date_pairs_are_unique():
    """No duplicate (tile_id, date) combinations allowed."""
    df = build_daily_temperature_dataset()
    duplicates = df.duplicated(subset=["tile_id", "date"])
    assert not duplicates.any(), (
        f"Duplicate tile/date pairs found:\n{df[duplicates][['tile_id', 'date']]}"
    )


def test_all_six_phoenix_tiles_present_in_dataset():
    df = build_daily_temperature_dataset()
    found = set(df["tile_id"].unique())
    assert VALID_TILES == found or VALID_TILES.issubset(found), (
        f"Expected tiles {VALID_TILES}, found {found}"
    )


# ---------------------------------------------------------------------------
# Leakage protection
# ---------------------------------------------------------------------------

def test_apparent_temperature_not_in_feature_matrix():
    """
    apparent_temperature_celsius statistics (mean/min/max) must NOT appear as
    features because the target IS the mean of this same variable.
    Including it would be direct target leakage.
    """
    df = build_daily_temperature_dataset()
    _, _, feature_cols = _feature_matrix(df)
    leakage_cols = [c for c in feature_cols if "apparent_temperature" in c]
    assert not leakage_cols, (
        f"Target leakage detected: {leakage_cols} are in the feature matrix "
        "but are derived from the same series as the target."
    )


def test_target_column_not_in_feature_matrix():
    """The target column itself must not appear as an input feature."""
    df = build_daily_temperature_dataset()
    _, _, feature_cols = _feature_matrix(df)
    assert "temperature" not in feature_cols, (
        "Target column 'temperature' must not appear in the feature matrix."
    )


def test_feature_version_is_v2():
    """
    Feature version must be 'daily-temperature-v2' (or later) to indicate
    the corrected pipeline. v1 corresponds to the old static-target pipeline.
    """
    assert FEATURE_VERSION.startswith("daily-temperature-v"), (
        f"Unexpected feature version: {FEATURE_VERSION}"
    )
    version_num = int(FEATURE_VERSION.split("-v")[-1])
    assert version_num >= 2, (
        f"Feature version {FEATURE_VERSION} predates the target correction; "
        "saved model artifacts may correspond to the old static-target pipeline."
    )


# ---------------------------------------------------------------------------
# Date/tile alignment
# ---------------------------------------------------------------------------

def test_target_values_for_tile8_specific_dates():
    """
    Spot-check that tile 8 targets match the expected values derived from the
    raw apparent_temperature_celsius hourly observations. Values were computed
    directly from the raw JSON files and must not change unless raw data changes.

    Expected (tolerance ±0.01°C):
      2023-01-01  → ~8.81°C
      2023-05-01  → ~24.33°C
      2023-05-28  → ~25.99°C
      2024-01-28  → ~11.42°C
    """
    df = build_daily_temperature_dataset()
    t8 = df[df["tile_id"] == 8].set_index("date")["temperature"]

    expected = {
        "2023-01-01": 8.8125,
        "2023-05-01": 24.3250,
        "2023-05-28": 25.9875,
        "2024-01-28": 11.4208,
    }
    for date, expected_val in expected.items():
        if date not in t8.index:
            continue
        actual = t8[date]
        assert abs(actual - expected_val) < 0.02, (
            f"Tile 8, {date}: expected ~{expected_val:.4f}°C, got {actual:.4f}°C. "
            "Target may not be coming from the correct date's observations."
        )


def test_winter_target_lower_than_summer_for_tile8():
    """
    A basic sanity check: January temperatures must be lower than July for
    Phoenix tile 8 (daily mean apparent temperature).
    """
    df = build_daily_temperature_dataset()
    t8 = df[df["tile_id"] == 8].copy()
    t8["month"] = t8["date"].str[5:7].astype(int)

    jan = t8[t8["month"] == 1]["temperature"].mean()
    jul = t8[t8["month"] == 7]["temperature"].mean()

    assert jan < jul, (
        f"January mean {jan:.2f}°C should be less than July mean {jul:.2f}°C for Phoenix. "
        "If they are similar, the target may still be using the static tile temperature."
    )


# ---------------------------------------------------------------------------
# Saved model artifact integrity
# ---------------------------------------------------------------------------

def test_saved_model_metadata_uses_correct_feature_version():
    """Saved model metadata must declare the corrected feature version."""
    models_dir = (
        Path(__file__).resolve().parent.parent / "trained_models"
    )
    for model_name in ["linear_regression", "random_forest"]:
        meta_path = models_dir / model_name / "metadata.json"
        if not meta_path.exists():
            pytest.skip(f"Model artifact {meta_path} not found; run retraining first.")
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        fv = meta.get("feature_version", "")
        assert fv == FEATURE_VERSION, (
            f"{model_name}: metadata feature_version is '{fv}'; "
            f"expected '{FEATURE_VERSION}'. "
            "The saved artifact corresponds to the old pipeline."
        )


def test_saved_model_features_exclude_apparent_temperature():
    """Saved model feature list must not contain apparent_temperature columns."""
    models_dir = (
        Path(__file__).resolve().parent.parent / "trained_models"
    )
    for model_name in ["linear_regression", "random_forest"]:
        meta_path = models_dir / model_name / "metadata.json"
        if not meta_path.exists():
            pytest.skip(f"Model artifact {meta_path} not found.")
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        leakage = [f for f in meta["features"] if "apparent_temperature" in f]
        assert not leakage, (
            f"{model_name}: saved metadata lists apparent_temperature features "
            f"{leakage} — target leakage in the saved artifact."
        )
