import pytest

from scenario.interventions import (
    FEATURE_VERSION,
    TREE_COOLING_C_PER_PERCENT,
    estimate_heat_mitigation,
    validate_scenario,
)


def test_scenario_input_validation():
    values = validate_scenario({
        "tree_canopy_increase_percent": 10,
        "cool_roof_coverage_percent": 50,
        "cool_pavement_coverage_percent": 50,
    })

    assert values["tree_canopy_increase_percent"] == 10
    with pytest.raises(ValueError):
        validate_scenario({"tree_canopy_increase_percent": 31})
    with pytest.raises(ValueError):
        validate_scenario({"cool_roof_coverage_percent": -1})


def test_tree_canopy_effect_and_cost():
    result = estimate_heat_mitigation(
        39.4,
        {"tree_canopy_increase_percent": 10, "number_of_trees": 10},
    )

    assert result["interventions"]["tree_canopy"]["estimated_effect_c"] == 10 * TREE_COOLING_C_PER_PERCENT
    assert result["interventions"]["tree_canopy"]["estimated_cost_usd"] == 10880


def test_cool_roof_effect_and_area_cost():
    result = estimate_heat_mitigation(
        39.4,
        {"cool_roof_coverage_percent": 50, "roof_area_sqft": 1000},
    )
    roof = result["interventions"]["cool_roof"]

    assert roof["estimated_effect_c"] == 0.15
    assert roof["estimated_cost_usd"] == 1150


def test_cool_pavement_is_surface_only():
    result = estimate_heat_mitigation(
        39.4,
        {"cool_pavement_coverage_percent": 50, "paved_area_sqft": 1000},
    )
    pavement = result["interventions"]["cool_pavement"]

    assert len(pavement["estimated_surface_effect_c_range"]) == 2
    assert pavement["estimated_cost_usd"] == 3000
    assert result["estimated_temperature_after_air_effects_c"] == 39.4


def test_costs_are_unknown_without_required_quantity_or_area():
    result = estimate_heat_mitigation(
        39.4,
        {
            "tree_canopy_increase_percent": 10,
            "cool_roof_coverage_percent": 50,
            "cool_pavement_coverage_percent": 50,
        },
    )

    assert result["interventions"]["tree_canopy"]["estimated_cost_usd"] is None
    assert result["interventions"]["cool_roof"]["estimated_cost_usd"] is None
    assert result["interventions"]["cool_pavement"]["estimated_cost_usd"] is None


def test_scenario_version_is_separate_from_model_features():
    result = estimate_heat_mitigation(39.4, {})

    assert result["feature_version"] == FEATURE_VERSION
    assert "tree_canopy_increase_percent" not in result["feature_version"]
    assert "tree_canopy_increase_percent" not in result["interventions"]
