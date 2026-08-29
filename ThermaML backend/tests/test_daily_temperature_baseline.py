import numpy as np
import json
import pickle

import pandas as pd

from data.daily_temperature_pipeline import (
    build_daily_temperature_dataset,
    make_expanding_date_splits,
    make_chronological_split,
)
from models.linear_regression import create_linear_regression_model
from models.inference import load_model, predict
from models.random_forest import create_random_forest_model


def test_daily_temperature_dataset_has_scalar_target_and_no_target_leakage():
    df = build_daily_temperature_dataset()

    assert {"tile_id", "date", "temperature"}.issubset(df.columns)
    assert df["temperature"].notna().all()
    assert "methane_ppb" not in df.columns
    assert "co2_ppm" not in df.columns
    assert all(not col.startswith("temperature_") for col in df.columns if col != "temperature")


def test_chronological_split_keeps_dates_in_order_and_separates_by_date():
    df = build_daily_temperature_dataset()
    split = make_chronological_split(df)

    expected = sorted(set(split["train_dates"] + split["validation_dates"] + split["test_dates"]))
    assert split["train_dates"]
    assert split["validation_dates"]
    assert split["test_dates"]
    assert split["train_dates"] + split["validation_dates"] + split["test_dates"] == expected
    assert all(date in df["date"].unique() for date in expected)


def test_expanding_folds_keep_all_rows_for_held_out_dates_out_of_training():
    df = build_daily_temperature_dataset()
    splits = make_expanding_date_splits(df)

    for split in splits:
        train_dates = set(split["train_dates"])
        test_dates = set(split["test_dates"])
        train_rows = df[df["date"].isin(train_dates)]
        test_rows = df[df["date"].isin(test_dates)]

        assert train_dates.isdisjoint(test_dates)
        assert len(test_rows) > 0
        assert set(test_rows["date"]).isdisjoint(set(train_rows["date"]))
        assert set(test_rows["tile_id"]).issubset(set(df["tile_id"]))
        assert set(test_rows[["tile_id", "date"]].itertuples(index=False, name=None)).isdisjoint(
            set(train_rows[["tile_id", "date"]].itertuples(index=False, name=None))
        )


def test_linear_regression_model_can_be_created_independently():
    model = create_linear_regression_model()
    model.fit(pd.DataFrame({"feature": [0.0, 1.0]}), pd.Series([39.0, 40.0]))

    assert model.named_steps["scaler"].__class__.__name__ == "StandardScaler"
    assert model.named_steps["model"].__class__.__name__ == "LinearRegression"


def test_random_forest_model_can_train_and_predict_without_scaling():
    df = build_daily_temperature_dataset()
    features = df.drop(columns=["tile_id", "date", "temperature"]).select_dtypes("number")
    model = create_random_forest_model()
    model.fit(features, df["temperature"])
    prediction = model.predict(features.iloc[[0]])[0]

    assert not hasattr(model, "named_steps")
    assert np.isfinite(prediction)


def test_model_artifact_can_load_and_predict(tmp_path):
    artifact_dir = tmp_path / "random_forest"
    artifact_dir.mkdir()
    features = pd.DataFrame({"feature_a": [0.0, 1.0, 2.0], "feature_b": [1.0, 1.0, 1.0]})
    model = create_random_forest_model()
    model.fit(features, pd.Series([39.0, 40.0, 41.0]))
    with open(artifact_dir / "model.joblib", "wb") as handle:
        pickle.dump(model, handle)
    with open(artifact_dir / "metadata.json", "w", encoding="utf-8") as handle:
        json.dump({
            "model_name": "random_forest",
            "target": "temperature",
            "task": "daily_temperature_regression",
            "features": ["feature_a", "feature_b"],
            "feature_version": "test",
            "units": "celsius",
        }, handle)

    loaded_model, metadata = load_model("random_forest", models_dir=tmp_path)
    result = predict("random_forest", {"feature_a": 1.5, "feature_b": 1.0}, models_dir=tmp_path)

    assert loaded_model is not None
    assert metadata["features"] == ["feature_a", "feature_b"]
    assert np.isfinite(result["prediction"])
    assert result["unit"] == "celsius"
    assert result["model"] == "random_forest"
