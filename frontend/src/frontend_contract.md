# ThermaML Frontend Contract

The current system performs daily tile/date regression using available environmental observations. It is not an hourly or arbitrary-future forecasting API.

## Discovery

`get_available_dates()` returns the 37 dates present in the model-ready dataset, from `2023-01-01` through `2024-01-28`. `get_available_tiles(date)` returns only tiles observed for that date. Do not populate controls with dates or tiles outside these helpers.

`get_available_models()` returns `linear_regression` and `random_forest`. The documented GNN is not available.

## Prediction

Call `predict_for_date_tile(model_name, date, tile_id)`:

```json
{
  "model": "random_forest",
  "tile_id": 426,
  "date": "YYYY-MM-DD",
  "predicted_temperature_c": 39.4,
  "target": "daily_temperature",
  "feature_version": "daily-temperature-v1"
}
```

The date and tile must be available in the model-ready dataset. The value is a model prediction for an observed daily environmental feature row, not a guarantee of future forecasting.

## Model comparison

Call `compare_models(date, tile_id)`. It returns the same observed row scored by the saved Linear Regression and Random Forest artifacts, plus the all-dataset training-mean reference:

```json
{
  "date": "YYYY-MM-DD",
  "tile_id": 426,
  "predictions": {
    "naive": 39.4,
    "linear_regression": 39.4,
    "random_forest": 39.4
  }
}
```

No model is retrained during comparison.

## Scenario prediction

Call `predict_scenario_for_date_tile(model_name, date, tile_id, scenario)`. The scenario may include canopy, roof, and pavement percentages plus `number_of_trees`, `roof_area_sqft`, and `paved_area_sqft` for cost calculation. It returns the baseline model prediction, intervention inputs, estimated effects, costs, and limitations.

Tree canopy and cool-roof effects are used in the approximate air-temperature scenario result. Cool pavement remains a surface-temperature range and is never subtracted from air temperature. Missing required quantities produce `null` costs.

Invalid requests raise clear `ValueError` messages for unavailable models, dates, or tiles. Intervention ranges and metadata are available from `get_available_interventions()`.
