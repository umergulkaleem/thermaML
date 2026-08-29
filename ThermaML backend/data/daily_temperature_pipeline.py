import json
import math
import pickle
from collections import OrderedDict
from datetime import datetime
from pathlib import Path
from statistics import mean

import pandas as pd
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

from models.linear_regression import create_linear_regression_model
from models.registry import get_model_factory


BASE_DIR = Path(__file__).resolve().parent
RAW_ENVIRONMENT_DIRS = [
    BASE_DIR / "phoenix" / "raw" / "environment",
    BASE_DIR / "phoenix" / "raw" / "environment_tiles_8_844",
    BASE_DIR / "phoenix" / "raw" / "environment_tiles_420_814",
]
EXCLUDED_PARAMETERS = {"methane_ppb", "co2_ppm"}
VALID_TILES = {7, 426, 8, 844, 420, 814}
TARGET_COLUMN = "temperature"
# The name of the hourly parameter used to derive the daily scalar target.
# locations[0].temperature is the static geographic tile temperature (constant
# per tile, never varying by date) — it was the input sent in the request
# payload and is echoed back verbatim. The real daily thermal signal is the
# mean of the 24-hour apparent_temperature_celsius readings.
_TARGET_PARAMETER = "apparent_temperature_celsius"
FEATURE_VERSION = "daily-temperature-v2"


def _read_json(path: Path):
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def _extract_date_from_filename(path: Path):
    stem = path.stem
    match = __import__("re").search(r"(\d{4}-\d{2}-\d{2})", stem)
    if match:
        return match.group(1)
    return None


def _extract_tile_id(data: dict, path: Path):
    if isinstance(data.get("tile"), dict):
        tile_id = data["tile"].get("tile_id")
        if tile_id is not None:
            return int(tile_id)
    if isinstance(data.get("location_id"), str):
        match = __import__("re").search(r"tile_(\d+)", data["location_id"]) 
        if match:
            return int(match.group(1))
    match = __import__("re").search(r"tile_(\d+)", path.stem)
    if match:
        return int(match.group(1))
    raise ValueError(f"Unable to determine tile_id from {path}")


def _safe_float(value):
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(numeric):
        return None
    return numeric


def _summarize_parameter(values):
    numeric = [float(value) for value in values if value is not None]
    if not numeric:
        return {}
    summary = OrderedDict()
    summary["mean"] = float(mean(numeric))
    summary["min"] = float(min(numeric))
    summary["max"] = float(max(numeric))
    return summary


def _build_record_from_file(path: Path):
    if path.name == "phoenix_spatial_test_tiles.json":
        return

    raw = _read_json(path)
    records = raw if isinstance(raw, list) else [raw]

    for record in records:
        if not isinstance(record, dict):
            continue

        payload = record.get("raw_api_response")
        if isinstance(payload, dict):
            location_payload = payload.get("locations", [{}])[0]
            metadata = payload.get("metadata", {})
            date = payload.get("date")
            if date is None:
                timestamps = metadata.get("timestamps", [])
                if timestamps:
                    date = timestamps[0][:10]
            tile_id = _extract_tile_id(record, path)
        else:
            environment = record.get("environment")
            if isinstance(environment, dict):
                location_payload = (environment.get("locations") or [{}])[0]
                metadata = environment.get("metadata", {})
                timestamps = metadata.get("timestamps", [])
                tile_bucket = record.get("tile") or {}
                date = tile_bucket.get("date")
                if date is None and timestamps:
                    date = timestamps[0][:10]
                tile_id = tile_bucket.get("tile_id")
                if tile_id is None:
                    tile_id = _extract_tile_id(record, path)
                tile_id = int(tile_id)
            else:
                location_payload = record.get("locations", [{}])[0]
                metadata = record.get("metadata", {})
                timestamps = metadata.get("timestamps", [])
                date = record.get("date")
                if date is None and timestamps:
                    date = timestamps[0][:10]
                tile_id = _extract_tile_id(record, path)

        if not isinstance(location_payload, dict):
            continue

        if date is None:
            date = _extract_date_from_filename(path)
        if date is None:
            continue

        parameters = location_payload.get("parameters") or {}

        # Derive the daily scalar target from the mean of the 24-hour
        # apparent_temperature_celsius readings.  The locations[0].temperature
        # field is the static geographic tile temperature that was sent in the
        # request_payload and is echoed back unchanged for every date — it has
        # no temporal variation and is scientifically inappropriate as a target.
        target_values = parameters.get(_TARGET_PARAMETER)
        if isinstance(target_values, list):
            numeric_target = [v for v in target_values if v is not None]
            temperature = float(mean(numeric_target)) if numeric_target else None
        else:
            # Fallback: try the static field (old-format files without parameters)
            temperature = _safe_float(location_payload.get("temperature"))

        if temperature is None:
            continue

        row = {
            "tile_id": int(tile_id),
            "date": date,
            TARGET_COLUMN: float(temperature),
        }

        for name, values in parameters.items():
            if name in EXCLUDED_PARAMETERS:
                continue
            if not isinstance(values, list):
                continue
            summary = _summarize_parameter(values)
            for stat, value in summary.items():
                row[f"{name}_{stat}"] = value

        yield row


def build_daily_temperature_dataset():
    rows = []
    seen = set()
    for env_dir in RAW_ENVIRONMENT_DIRS:
        if not env_dir.exists():
            continue
        for path in sorted(env_dir.glob("*.json")):
            for row in _build_record_from_file(path):
                key = (row["tile_id"], row["date"])
                if key in seen:
                    continue
                seen.add(key)
                rows.append(row)

    if not rows:
        raise RuntimeError("No valid daily environmental rows were found.")

    df = pd.DataFrame(rows)
    if df.empty:
        raise RuntimeError("No valid daily environmental rows were found.")
    df = df[df["tile_id"].isin(VALID_TILES)].copy()
    df["date"] = pd.to_datetime(df["date"]).dt.strftime("%Y-%m-%d")
    df = df.sort_values(["date", "tile_id"]).reset_index(drop=True)

    # Keep tile metadata for later spatial work while using the scalar temperature as target.
    df["tile_id"] = df["tile_id"].astype(int)
    return df


def _date_features(df: pd.DataFrame) -> pd.DataFrame:
    enriched = df.copy()
    enriched["date"] = pd.to_datetime(enriched["date"])
    enriched["month"] = enriched["date"].dt.month
    enriched["day_of_year"] = enriched["date"].dt.dayofyear
    enriched["sin_day_of_year"] = (2 * math.pi * enriched["day_of_year"] / 365).map(math.sin)
    enriched["cos_day_of_year"] = (2 * math.pi * enriched["day_of_year"] / 365).map(math.cos)
    return enriched


def make_chronological_split(df: pd.DataFrame):
    dates = sorted(df["date"].unique())
    if len(dates) < 6:
        raise ValueError("At least six dates are required for a chronological validation split.")

    train_dates = dates[:-4]
    validation_dates = dates[-4:-2]
    test_dates = dates[-2:]

    return {
        "train_dates": train_dates,
        "validation_dates": validation_dates,
        "test_dates": test_dates,
    }


def _feature_matrix(df: pd.DataFrame):
    """Build feature matrix, target series, and ordered feature name list.

    Target leakage protection
    -------------------------
    The target is defined as mean(apparent_temperature_celsius) over 24 hours.
    Therefore ALL apparent_temperature_celsius statistics (mean, min, max) are
    excluded from the feature matrix to prevent the model from receiving the
    answer it is meant to predict.

    Excluded variables
    ------------------
    - apparent_temperature_celsius_* : target source (leakage)
    - methane_ppb_*                  : all nulls in dataset (EXCLUDED_PARAMETERS)
    - co2_ppm_*                      : all nulls in dataset (EXCLUDED_PARAMETERS)
    - date                           : used only for splitting
    - temperature                    : target column itself

    Features kept
    -------------
    - heat_index_celsius_{mean,min,max}
    - relative_humidity_percent_{mean,min,max}
    - precipitation_mm_{mean,min,max}
    - cloud_cover_octas_{mean,min,max}
    - wet_bulb_temperature_celsius_{mean,min,max}
    - air_quality:idx_{mean,min,max}
    - air_quality_no2:idx, _o3:idx, _pm10:idx, _pm2p5:idx, _so2:idx stats
    - aqi_us_co_{mean,min,max}
    - tile_id  (integer; lets model learn per-tile baseline offsets)
    - month, day_of_year, sin_day_of_year, cos_day_of_year
    """
    date_enriched = _date_features(df)
    # Columns to never use as features.
    exclude_exact = {"date", TARGET_COLUMN}
    # Prefixes that generate target leakage: apparent_temperature_celsius
    # statistics are derived from the same hourly series whose mean is the
    # target. All three summary stats (mean, min, max) are excluded.
    leakage_prefix = "apparent_temperature_celsius"

    feature_cols = [
        col for col in date_enriched.columns
        if col not in exclude_exact
        and not col.startswith(leakage_prefix)
        and col.startswith((
            "heat_index", "relative_humidity",
            "precipitation", "cloud_cover", "wet_bulb_temperature",
            "air_quality", "aqi_us_co",
        ))
    ]
    # Tile identity and calendar features.
    feature_cols += ["tile_id", "month", "day_of_year", "sin_day_of_year", "cos_day_of_year"]
    feature_cols = sorted(set(feature_cols))
    return date_enriched[feature_cols], date_enriched[TARGET_COLUMN], feature_cols


def _save_pickle(path: Path, obj):
    with open(path, "wb") as handle:
        pickle.dump(obj, handle)


def _build_experiment_directory(base_dir: Path):
    exp_dirs = sorted(base_dir.glob("exp_*"))
    next_index = len(exp_dirs) + 1
    exp_dir = base_dir / f"exp_{next_index:03d}_linear_regression"
    exp_dir.mkdir(parents=True, exist_ok=False)
    return exp_dir


def _build_temporal_experiment_directory(base_dir: Path, model_name: str):
    exp_dirs = sorted(base_dir.glob("exp_*"))
    next_index = len(exp_dirs) + 1
    exp_dir = base_dir / f"exp_{next_index:03d}_{model_name}_temporal_cv"
    exp_dir.mkdir(parents=True, exist_ok=False)
    return exp_dir


def make_expanding_date_splits(df: pd.DataFrame, test_dates_per_fold=2, max_folds=6):
    dates = sorted(pd.to_datetime(df["date"]).dt.strftime("%Y-%m-%d").unique())
    initial_train_count = len(dates) - (test_dates_per_fold * max_folds)
    if test_dates_per_fold < 1 or max_folds < 1 or initial_train_count < 2:
        raise ValueError("Not enough dates for the requested expanding splits.")

    splits = []
    for fold_index in range(max_folds):
        train_end = initial_train_count + (fold_index * test_dates_per_fold)
        test_dates = dates[train_end:train_end + test_dates_per_fold]
        if len(test_dates) < test_dates_per_fold:
            break
        splits.append({
            "fold_id": fold_index + 1,
            "train_dates": dates[:train_end],
            "test_dates": test_dates,
        })
    return splits


def _metric_values(actual, predicted):
    return {
        "mae": float(mean_absolute_error(actual, predicted)),
        "rmse": float(mean_squared_error(actual, predicted) ** 0.5),
        "r2": float(r2_score(actual, predicted)),
    }


def run_temporal_evaluation(model_name="linear_regression", output_dir: str | None = None):
    df = build_daily_temperature_dataset()
    splits = make_expanding_date_splits(df)
    model_factory = get_model_factory(model_name)
    df["date"] = pd.to_datetime(df["date"])
    fold_metrics = []
    prediction_frames = []
    feature_names = None

    for split in splits:
        train_df = df[df["date"].dt.strftime("%Y-%m-%d").isin(split["train_dates"])].copy()
        test_df = df[df["date"].dt.strftime("%Y-%m-%d").isin(split["test_dates"])].copy()
        X_train, y_train, feature_names = _feature_matrix(train_df)
        X_test, y_test, _ = _feature_matrix(test_df)
        model = model_factory()
        model.fit(X_train, y_train)
        predicted = model.predict(X_test)
        naive_prediction = float(y_train.mean())
        naive_predicted = [naive_prediction] * len(y_test)
        fold_metrics.append({
            "fold_id": split["fold_id"],
            "train_start_date": split["train_dates"][0],
            "train_end_date": split["train_dates"][-1],
            "test_start_date": split["test_dates"][0],
            "test_end_date": split["test_dates"][-1],
            "train_sample_count": int(len(train_df)),
            "test_sample_count": int(len(test_df)),
            "test_date_count": int(test_df["date"].dt.strftime("%Y-%m-%d").nunique()),
            "test_target_mean": float(y_test.mean()),
            "test_target_std": float(y_test.std(ddof=1)),
            model_name: _metric_values(y_test, predicted),
            "naive_baseline": _metric_values(y_test, naive_predicted),
        })
        prediction_frames.append(pd.DataFrame({
            "fold": split["fold_id"],
            "tile_id": test_df["tile_id"].astype(int).to_numpy(),
            "date": test_df["date"].dt.strftime("%Y-%m-%d").to_numpy(),
            "actual_temperature": y_test.to_numpy(),
            "predicted_temperature": predicted,
            "residual": predicted - y_test.to_numpy(),
            "naive_prediction": naive_predicted,
        }))

    predictions = pd.concat(prediction_frames, ignore_index=True)
    model_summary = pd.DataFrame([fold[model_name] for fold in fold_metrics])
    naive_summary = pd.DataFrame([fold["naive_baseline"] for fold in fold_metrics])
    actual = predictions["actual_temperature"]
    linear_predicted = predictions["predicted_temperature"]
    naive_predicted = predictions["naive_prediction"]

    def aggregate(summary, pooled_predicted):
        return {
            "mean_mae": float(summary["mae"].mean()),
            "std_mae": float(summary["mae"].std(ddof=0)),
            "mean_rmse": float(summary["rmse"].mean()),
            "std_rmse": float(summary["rmse"].std(ddof=0)),
            "mean_r2": float(summary["r2"].mean()),
            "std_r2": float(summary["r2"].std(ddof=0)),
            "pooled_mae": float(mean_absolute_error(actual, pooled_predicted)),
            "pooled_rmse": float(mean_squared_error(actual, pooled_predicted) ** 0.5),
            "pooled_r2": float(r2_score(actual, pooled_predicted)),
        }

    metrics = {
        "target": TARGET_COLUMN,
        "task": "daily tile/date regression",
        "fold_count": len(fold_metrics),
        "number_of_tiles": int(df["tile_id"].nunique()),
        "number_of_dates": int(df["date"].dt.strftime("%Y-%m-%d").nunique()),
        "number_of_features": int(len(feature_names)),
        "primary_metrics": ["mae", "rmse"],
        model_name: aggregate(model_summary, linear_predicted),
        "naive_baseline": aggregate(naive_summary, naive_predicted),
    }

    base_output = Path(output_dir) if output_dir else BASE_DIR.parent / "experiments"
    base_output.mkdir(parents=True, exist_ok=True)
    exp_dir = _build_temporal_experiment_directory(base_output, model_name)
    final_model = model_factory()
    final_features, final_target, _ = _feature_matrix(df)
    final_model.fit(final_features, final_target)
    _save_pickle(exp_dir / "model.joblib", final_model)
    predictions.to_csv(exp_dir / "predictions.csv", index=False)
    with open(exp_dir / "features.json", "w", encoding="utf-8") as handle:
        json.dump({"feature_names": feature_names}, handle, indent=2)
    with open(exp_dir / "fold_metrics.json", "w", encoding="utf-8") as handle:
        json.dump(fold_metrics, handle, indent=2)
    with open(exp_dir / "metrics.json", "w", encoding="utf-8") as handle:
        json.dump(metrics, handle, indent=2)
    with open(exp_dir / "split.json", "w", encoding="utf-8") as handle:
        json.dump({"folds": splits}, handle, indent=2)
    with open(exp_dir / "config.json", "w", encoding="utf-8") as handle:
        json.dump({
            "experiment_id": exp_dir.name,
            "model_name": model_name,
            "evaluation": "expanding chronological date folds",
            "target": TARGET_COLUMN,
            "feature_names": feature_names,
            "test_dates_per_fold": 2,
            "fold_count": len(fold_metrics),
            "model_configuration": {
                "scaler": "StandardScaler" if model_name == "linear_regression" else None,
                "estimator": model_name,
            },
        }, handle, indent=2)
    trained_model_dir = base_output.parent / "trained_models" / model_name
    trained_model_dir.mkdir(parents=True, exist_ok=True)
    _save_pickle(trained_model_dir / "model.joblib", final_model)
    with open(trained_model_dir / "metadata.json", "w", encoding="utf-8") as handle:
        json.dump({
            "model_name": model_name,
            "target": TARGET_COLUMN,
            "task": "daily_temperature_regression",
            "features": feature_names,
            "feature_version": FEATURE_VERSION,
            "units": "celsius",
            "preprocessing": "StandardScaler" if model_name == "linear_regression" else "none",
            "target_derivation": f"mean of 24-hour {_TARGET_PARAMETER} hourly readings",
        }, handle, indent=2)
    return metrics, fold_metrics, exp_dir


def train_linear_regression_experiment(output_dir: str | None = None):
    df = build_daily_temperature_dataset()
    split = make_chronological_split(df)

    df["date"] = pd.to_datetime(df["date"])
    train_df = df[df["date"].dt.strftime("%Y-%m-%d").isin(split["train_dates"])].copy()
    validation_df = df[df["date"].dt.strftime("%Y-%m-%d").isin(split["validation_dates"])].copy()
    test_df = df[df["date"].dt.strftime("%Y-%m-%d").isin(split["test_dates"])].copy()

    X_train, y_train, feature_names = _feature_matrix(train_df)
    X_val, y_val, _ = _feature_matrix(validation_df)
    X_test, y_test, _ = _feature_matrix(test_df)

    model = create_linear_regression_model()
    model.fit(X_train, y_train)
    val_pred = model.predict(X_val)
    test_pred = model.predict(X_test)

    rmse = float(mean_squared_error(y_test, test_pred) ** 0.5)
    metrics = {
        "target": TARGET_COLUMN,
        "temperature_unit": "Celsius",
        "training_samples": int(len(train_df)),
        "validation_samples": int(len(validation_df)),
        "test_samples": int(len(test_df)),
        "number_of_tiles": int(df["tile_id"].nunique()),
        "number_of_dates": int(df["date"].dt.strftime("%Y-%m-%d").nunique()),
        "number_of_features": int(len(feature_names)),
        "mae": float(mean_absolute_error(y_test, test_pred)),
        "rmse": rmse,
        "r2": float(r2_score(y_test, test_pred)),
    }

    base_output = Path(output_dir) if output_dir else BASE_DIR.parent / "experiments"
    base_output.mkdir(parents=True, exist_ok=True)
    exp_dir = _build_experiment_directory(base_output)

    model_path = exp_dir / "model.joblib"
    _save_pickle(model_path, model)

    predictions = pd.DataFrame({
        "tile_id": test_df["tile_id"].astype(int).reset_index(drop=True),
        "date": test_df["date"].dt.strftime("%Y-%m-%d").reset_index(drop=True),
        "actual_temperature": pd.Series(y_test.to_numpy(), name="actual_temperature").reset_index(drop=True),
        "predicted_temperature": pd.Series(test_pred, name="predicted_temperature").reset_index(drop=True),
        "residual": pd.Series(test_pred - y_test.to_numpy(), name="residual").reset_index(drop=True),
        "split": "test",
    })
    predictions.to_csv(exp_dir / "predictions.csv", index=False)

    with open(exp_dir / "metrics.json", "w", encoding="utf-8") as handle:
        json.dump(metrics, handle, indent=2)

    with open(exp_dir / "features.json", "w", encoding="utf-8") as handle:
        json.dump({"feature_names": feature_names}, handle, indent=2)

    with open(exp_dir / "split.json", "w", encoding="utf-8") as handle:
        json.dump(
            {
                "train_dates": split["train_dates"],
                "validation_dates": split["validation_dates"],
                "test_dates": split["test_dates"],
                "sample_counts": {
                    "train": int(len(train_df)),
                    "validation": int(len(validation_df)),
                    "test": int(len(test_df)),
                },
            },
            handle,
            indent=2,
        )

    config = {
        "experiment_id": exp_dir.name,
        "model_name": "LinearRegression",
        "target": TARGET_COLUMN,
        "task": "daily tile/date temperature regression",
        "feature_names": feature_names,
        "train_dates": split["train_dates"],
        "validation_dates": split["validation_dates"],
        "test_dates": split["test_dates"],
        "sample_counts": {
            "train": int(len(train_df)),
            "validation": int(len(validation_df)),
            "test": int(len(test_df)),
        },
        "temperature_unit": "Celsius",
        "model_configuration": {
            "scaler": "StandardScaler",
            "estimator": "LinearRegression",
            "random_seed": 42,
        },
    }
    with open(exp_dir / "config.json", "w", encoding="utf-8") as handle:
        json.dump(config, handle, indent=2)

    summary = {
        "experiment_id": exp_dir.name,
        "target": TARGET_COLUMN,
        "train_dates": split["train_dates"],
        "validation_dates": split["validation_dates"],
        "test_dates": split["test_dates"],
        "training_samples": int(len(train_df)),
        "validation_samples": int(len(validation_df)),
        "test_samples": int(len(test_df)),
        "features": feature_names,
        "mae": metrics["mae"],
        "rmse": metrics["rmse"],
        "r2": metrics["r2"],
    }
    return summary, exp_dir


def main():
    summary, exp_dir = train_linear_regression_experiment()
    print("Experiment:", exp_dir.name)
    print("Target: temperature")
    print("Task: daily tile/date regression")
    print("Train dates:", summary["train_dates"])
    print("Validation dates:", summary["validation_dates"])
    print("Test dates:", summary["test_dates"])
    print("Training samples:", summary["training_samples"])
    print("Validation samples:", summary["validation_samples"])
    print("Test samples:", summary["test_samples"])
    print("Number of features:", len(summary["features"]))
    print(f"MAE: {summary['mae']:.4f} C")
    print(f"RMSE: {summary['rmse']:.4f} C")
    print(f"R²: {summary['r2']:.4f}")


if __name__ == "__main__":
    main()
