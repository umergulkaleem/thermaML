import json
import pickle
from pathlib import Path

import pandas as pd

from data.daily_temperature_pipeline import _feature_matrix, build_daily_temperature_dataset
from models.registry import get_available_models
from scenario.interventions import estimate_heat_mitigation


DEFAULT_MODELS_DIR = Path(__file__).resolve().parent.parent / "trained_models"


def load_model(model_name, models_dir=None):
    model_dir = Path(models_dir) if models_dir else DEFAULT_MODELS_DIR
    artifact_dir = model_dir / model_name
    with open(artifact_dir / "model.joblib", "rb") as handle:
        model = pickle.load(handle)
    with open(artifact_dir / "metadata.json", "r", encoding="utf-8") as handle:
        metadata = json.load(handle)
    return model, metadata


def predict(model_name, input_features, models_dir=None):
    model, metadata = load_model(model_name, models_dir=models_dir)
    feature_names = metadata["features"]
    missing_features = [name for name in feature_names if name not in input_features]
    if missing_features:
        raise ValueError(f"Missing features: {missing_features}")
    feature_row = pd.DataFrame([[input_features[name] for name in feature_names]], columns=feature_names)
    prediction = float(model.predict(feature_row)[0])
    return {
        "prediction": prediction,
        "unit": metadata["units"],
        "model": model_name,
    }


def predict_with_scenario(model_name, input_features, scenario, models_dir=None):
    baseline = predict(model_name, input_features, models_dir=models_dir)
    result = estimate_heat_mitigation(baseline["prediction"], scenario)
    result["model"] = model_name
    return result


def get_available_dates():
    df = build_daily_temperature_dataset()
    return sorted(df["date"].unique().tolist())


def get_available_tiles(date=None):
    df = build_daily_temperature_dataset()
    if date is not None:
        date = str(pd.to_datetime(date).date())
        if date not in set(df["date"]):
            raise ValueError("No model-ready environmental data is available for this date.")
        df = df[df["date"] == date]
    return sorted(df["tile_id"].astype(int).unique().tolist())


def _get_model_ready_row(date, tile_id):
    date = str(pd.to_datetime(date).date())
    df = build_daily_temperature_dataset()
    matches = df[(df["date"] == date) & (df["tile_id"] == int(tile_id))]
    if matches.empty:
        if date not in set(df["date"]):
            raise ValueError("No model-ready environmental data is available for this date.")
        raise ValueError(f"Tile {tile_id} is not available in the current dataset.")
    features, _, _ = _feature_matrix(matches)
    return date, int(tile_id), features.iloc[0].to_dict()


def predict_for_date_tile(model_name, date, tile_id, models_dir=None):
    if model_name not in get_available_models():
        raise ValueError(f"Model '{model_name}' is not available.")
    date, tile_id, features = _get_model_ready_row(date, tile_id)
    result = predict(model_name, features, models_dir=models_dir)
    _, metadata = load_model(model_name, models_dir=models_dir)
    return {
        "model": model_name,
        "tile_id": tile_id,
        "date": date,
        "predicted_temperature_c": result["prediction"],
        "target": "daily_temperature",
        "feature_version": metadata.get("feature_version", "features_v1"),
    }


def compare_models(date, tile_id, models_dir=None):
    date, tile_id, features = _get_model_ready_row(date, tile_id)
    predictions = {"naive": float(build_daily_temperature_dataset()["temperature"].mean())}
    for model_name in get_available_models():
        predictions[model_name] = predict(model_name, features, models_dir=models_dir)["prediction"]
    return {"date": date, "tile_id": tile_id, "predictions": predictions}


def predict_scenario_for_date_tile(model_name, date, tile_id, scenario, models_dir=None):
    date, tile_id, features = _get_model_ready_row(date, tile_id)
    if model_name not in get_available_models():
        raise ValueError(f"Model '{model_name}' is not available.")
    baseline = predict(model_name, features, models_dir=models_dir)["prediction"]
    result = estimate_heat_mitigation(baseline, scenario)
    return {
        "model": model_name,
        "date": date,
        "tile_id": tile_id,
        "baseline_temperature_c": baseline,
        "scenario_temperature_c": result["estimated_temperature_after_air_effects_c"],
        "interventions": result["interventions"],
        "limitations": result["limitations"],
        "feature_version": result["feature_version"],
    }
