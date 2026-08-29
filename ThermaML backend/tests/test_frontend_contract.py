import numpy as np
import pytest

from models.inference import (
    compare_models,
    get_available_dates,
    get_available_tiles,
    predict_for_date_tile,
    predict_scenario_for_date_tile,
)
from models.registry import get_available_models
from scenario.interventions import get_available_interventions


def test_frontend_discovery_returns_observed_values():
    dates = get_available_dates()

    assert len(dates) == 37
    assert dates == sorted(dates)
    assert get_available_models() == ["linear_regression", "random_forest"]
    assert get_available_tiles(dates[-1])


def test_frontend_prediction_and_comparison_use_saved_models():
    date = get_available_dates()[-1]
    tile_id = get_available_tiles(date)[0]
    prediction = predict_for_date_tile("random_forest", date, tile_id)
    comparison = compare_models(date, tile_id)

    assert prediction["date"] == date
    assert prediction["tile_id"] == tile_id
    assert np.isfinite(prediction["predicted_temperature_c"])
    assert set(comparison["predictions"]) == {"naive", "linear_regression", "random_forest"}
    assert all(np.isfinite(value) for value in comparison["predictions"].values())


def test_frontend_scenario_prediction_keeps_pavement_surface_only():
    date = get_available_dates()[-1]
    tile_id = get_available_tiles(date)[0]
    result = predict_scenario_for_date_tile(
        "random_forest",
        date,
        tile_id,
        {
            "tree_canopy_increase_percent": 10,
            "cool_roof_coverage_percent": 50,
            "cool_pavement_coverage_percent": 50,
            "number_of_trees": 10,
        },
    )

    assert result["model"] == "random_forest"
    assert result["interventions"]["cool_pavement"]["estimated_surface_effect_c_range"]
    assert "Cool pavement" in result["limitations"][2]
    assert result["interventions"]["cool_roof"]["estimated_cost_usd"] is None


def test_frontend_rejects_invalid_model_date_and_tile():
    date = get_available_dates()[0]
    tile_id = get_available_tiles(date)[0]

    with pytest.raises(ValueError, match="Model 'xyz' is not available"):
        predict_for_date_tile("xyz", date, tile_id)
    with pytest.raises(ValueError, match="No model-ready environmental data"):
        predict_for_date_tile("random_forest", "2099-01-01", tile_id)
    with pytest.raises(ValueError, match="Tile 999 is not available"):
        predict_for_date_tile("random_forest", date, 999)


def test_intervention_metadata_is_frontend_ready():
    interventions = get_available_interventions()

    assert {item["name"] for item in interventions} == {"tree_canopy", "cool_roof", "cool_pavement"}
    assert all(item["input"] and item["valid_range"] and item["limitation"] for item in interventions)
