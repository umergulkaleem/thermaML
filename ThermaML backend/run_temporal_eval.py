"""
Temporal evaluation script for both Linear Regression and Random Forest.
Runs expanding chronological cross-validation and prints fold-by-fold results.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from data.daily_temperature_pipeline import (
    build_daily_temperature_dataset,
    make_expanding_date_splits,
    _feature_matrix,
    _metric_values,
)
from models.registry import get_model_factory
import pandas as pd
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score


def run_eval(model_name):
    print(f"\n{'='*60}")
    print(f"  Temporal Evaluation: {model_name}")
    print(f"{'='*60}")

    df = build_daily_temperature_dataset()
    splits = make_expanding_date_splits(df)
    model_factory = get_model_factory(model_name)
    df["date"] = pd.to_datetime(df["date"])

    all_actual = []
    all_predicted = []
    all_naive = []

    header = f"{'Fold':>4}  {'Train Range':>23}  {'Test Range':>23}  {'MAE':>6}  {'RMSE':>6}  {'R2':>6}  {'NaiveMAE':>8}"
    print(header)
    print("-" * len(header))

    for split in splits:
        train_df = df[df["date"].dt.strftime("%Y-%m-%d").isin(split["train_dates"])].copy()
        test_df = df[df["date"].dt.strftime("%Y-%m-%d").isin(split["test_dates"])].copy()
        X_train, y_train, _ = _feature_matrix(train_df)
        X_test, y_test, _ = _feature_matrix(test_df)

        model = model_factory()
        model.fit(X_train, y_train)
        predicted = model.predict(X_test)
        naive_val = float(y_train.mean())
        naive_pred = [naive_val] * len(y_test)

        m = _metric_values(y_test, predicted)
        naive_m = _metric_values(y_test, naive_pred)

        all_actual.extend(y_test.tolist())
        all_predicted.extend(predicted.tolist())
        all_naive.extend(naive_pred)

        train_range = f"{split['train_dates'][0]} -> {split['train_dates'][-1]}"
        test_range = f"{split['test_dates'][0]} -> {split['test_dates'][-1]}"
        print(f"{split['fold_id']:>4}  {train_range:>23}  {test_range:>23}  {m['mae']:>6.3f}  {m['rmse']:>6.3f}  {m['r2']:>6.3f}  {naive_m['mae']:>8.3f}")

    pooled_mae = mean_absolute_error(all_actual, all_predicted)
    pooled_rmse = mean_squared_error(all_actual, all_predicted) ** 0.5
    pooled_r2 = r2_score(all_actual, all_predicted)
    naive_pooled_mae = mean_absolute_error(all_actual, all_naive)

    print("-" * len(header))
    print(f"\nPooled MAE  : {pooled_mae:.3f} C")
    print(f"Pooled RMSE : {pooled_rmse:.3f} C")
    print(f"Pooled R2   : {pooled_r2:.3f}")
    print(f"Naive MAE   : {naive_pooled_mae:.3f} C")


if __name__ == "__main__":
    run_eval("linear_regression")
    run_eval("random_forest")
