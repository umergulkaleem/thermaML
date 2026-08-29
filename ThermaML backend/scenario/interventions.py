TREE_CANOPY_MAX_PERCENT = 30.0
TREE_COOLING_C_PER_PERCENT = 0.14
TREE_COST_PER_TREE_USD = 1088.0
COOL_ROOF_MAX_PERCENT = 100.0
COOL_ROOF_EFFECT_AT_FULL_C = 0.3
COOL_ROOF_DEFAULT_COST_PER_SQFT_USD = 1.15
COOL_PAVEMENT_MAX_PERCENT = 100.0
COOL_PAVEMENT_SURFACE_EFFECT_F = (10.5, 12.0)
COOL_PAVEMENT_DEFAULT_COST_PER_SQFT_USD = 3.0
FEATURE_VERSION = "features_v1"
SCENARIO_VERSION = "phoenix-heat-mitigation-v1"


def get_available_interventions():
    return [
        {
            "name": "tree_canopy",
            "input": "tree_canopy_increase_percent",
            "unit": "percentage points",
            "valid_range": [0, TREE_CANOPY_MAX_PERCENT],
            "required_quantity": "number_of_trees",
            "impact": "Estimated 0.14 degrees C air-temperature reduction per percentage point.",
            "cost_basis": "$1,088 per tree when number_of_trees is supplied.",
            "source": "Middel, Chhetri, and Quay (2015), DOI 10.1016/j.ufug.2014.09.010.",
            "limitation": "Phoenix residential-neighborhood study result; not a universal citywide law.",
        },
        {
            "name": "cool_roof",
            "input": "cool_roof_coverage_percent",
            "unit": "percent of relevant roof area",
            "valid_range": [0, COOL_ROOF_MAX_PERCENT],
            "required_quantity": "roof_area_sqft",
            "impact": "Simplified interpolation to a 0.3 degrees C neighborhood air effect at full coverage.",
            "cost_basis": "roof_area_sqft times configurable cost per square foot.",
            "source": "Middel, Chhetri, and Quay (2015); DOE cool-roof guidance.",
            "limitation": "Modeled neighborhood scenario; installation cost varies by roof type.",
        },
        {
            "name": "cool_pavement",
            "input": "cool_pavement_coverage_percent",
            "unit": "percent of selected paved area",
            "valid_range": [0, COOL_PAVEMENT_MAX_PERCENT],
            "required_quantity": "paved_area_sqft",
            "impact": "Estimated 10.5-12 degrees F pavement surface-temperature reduction at full coverage.",
            "cost_basis": "paved_area_sqft times configurable cost per square foot.",
            "source": "City of Phoenix Cool Pavement Program and EPA Heat Island database.",
            "limitation": "Surface-temperature result, not an equivalent air-temperature prediction.",
        },
    ]


def _number(value, name):
    if isinstance(value, bool):
        raise ValueError(f"{name} must be numeric")
    try:
        return float(value)
    except (TypeError, ValueError):
        raise ValueError(f"{name} must be numeric")


def _percent(value, name, maximum):
    value = _number(value, name)
    if not 0 <= value <= maximum:
        raise ValueError(f"{name} must be between 0 and {maximum}")
    return value


def validate_scenario(scenario):
    if not isinstance(scenario, dict):
        raise ValueError("scenario must be a dictionary")
    return {
        "tree_canopy_increase_percent": _percent(
            scenario.get("tree_canopy_increase_percent", 0),
            "tree_canopy_increase_percent",
            TREE_CANOPY_MAX_PERCENT,
        ),
        "cool_roof_coverage_percent": _percent(
            scenario.get("cool_roof_coverage_percent", 0),
            "cool_roof_coverage_percent",
            COOL_ROOF_MAX_PERCENT,
        ),
        "cool_pavement_coverage_percent": _percent(
            scenario.get("cool_pavement_coverage_percent", 0),
            "cool_pavement_coverage_percent",
            COOL_PAVEMENT_MAX_PERCENT,
        ),
        "number_of_trees": scenario.get("number_of_trees"),
        "roof_area_sqft": scenario.get("roof_area_sqft"),
        "paved_area_sqft": scenario.get("paved_area_sqft"),
        "cool_roof_cost_per_sqft": scenario.get(
            "cool_roof_cost_per_sqft", COOL_ROOF_DEFAULT_COST_PER_SQFT_USD
        ),
        "cool_pavement_cost_per_sqft": scenario.get(
            "cool_pavement_cost_per_sqft", COOL_PAVEMENT_DEFAULT_COST_PER_SQFT_USD
        ),
    }


def _optional_nonnegative(value, name):
    if value is None or value == "":
        return None
    value = _number(value, name)
    if value < 0:
        raise ValueError(f"{name} must be non-negative")
    return value


def estimate_heat_mitigation(baseline_temperature_c, scenario):
    baseline = _number(baseline_temperature_c, "baseline_temperature_c")
    values = validate_scenario(scenario)
    number_of_trees = _optional_nonnegative(values["number_of_trees"], "number_of_trees")
    roof_area = _optional_nonnegative(values["roof_area_sqft"], "roof_area_sqft")
    paved_area = _optional_nonnegative(values["paved_area_sqft"], "paved_area_sqft")
    roof_cost = _optional_nonnegative(
        values["cool_roof_cost_per_sqft"], "cool_roof_cost_per_sqft"
    )
    pavement_cost = _optional_nonnegative(
        values["cool_pavement_cost_per_sqft"], "cool_pavement_cost_per_sqft"
    )

    tree_effect = values["tree_canopy_increase_percent"] * TREE_COOLING_C_PER_PERCENT
    roof_effect = (
        values["cool_roof_coverage_percent"] / 100
    ) * COOL_ROOF_EFFECT_AT_FULL_C
    pavement_low_c = COOL_PAVEMENT_SURFACE_EFFECT_F[0] * 5 / 9
    pavement_high_c = COOL_PAVEMENT_SURFACE_EFFECT_F[1] * 5 / 9
    pavement_fraction = values["cool_pavement_coverage_percent"] / 100

    tree_cost = (
        0.0 if values["tree_canopy_increase_percent"] == 0
        else (None if number_of_trees is None else number_of_trees * TREE_COST_PER_TREE_USD)
    )
    roof_total_cost = (
        0.0 if values["cool_roof_coverage_percent"] == 0
        else (None if roof_area is None or roof_cost is None else roof_area * roof_cost)
    )
    pavement_total_cost = (
        0.0 if values["cool_pavement_coverage_percent"] == 0
        else (None if paved_area is None or pavement_cost is None else paved_area * pavement_cost)
    )

    return {
        "scenario_version": SCENARIO_VERSION,
        "feature_version": FEATURE_VERSION,
        "baseline_temperature_c": baseline,
        "estimated_temperature_after_air_effects_c": baseline - tree_effect - roof_effect,
        "interventions": {
            "tree_canopy": {
                "selected": values["tree_canopy_increase_percent"] > 0,
                "input_percent": values["tree_canopy_increase_percent"],
                "estimated_effect_c": tree_effect,
                "estimated_cost_usd": tree_cost,
                "cost_basis": "number_of_trees * $1,088/tree",
            },
            "cool_roof": {
                "selected": values["cool_roof_coverage_percent"] > 0,
                "input_percent": values["cool_roof_coverage_percent"],
                "estimated_effect_c": roof_effect,
                "estimated_cost_usd": roof_total_cost,
                "cost_basis": "roof_area_sqft * configurable cost_per_sqft",
            },
            "cool_pavement": {
                "selected": values["cool_pavement_coverage_percent"] > 0,
                "input_percent": values["cool_pavement_coverage_percent"],
                "estimated_surface_effect_c_range": [
                    pavement_fraction * pavement_low_c,
                    pavement_fraction * pavement_high_c,
                ],
                "estimated_cost_usd": pavement_total_cost,
                "cost_basis": "paved_area_sqft * configurable cost_per_sqft",
            },
        },
        "limitations": [
            "Scenario effects are evidence-based approximations, not causal ML estimates.",
            "Tree and cool-roof air effects are combined additively for planning only.",
            "Cool pavement remains a surface-temperature effect and is excluded from air temperature.",
            "Interactions between interventions are not modeled.",
        ],
    }
