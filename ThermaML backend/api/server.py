from __future__ import annotations

from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from models.inference import (
    compare_models,
    get_available_dates,
    get_available_tiles,
    predict_for_date_tile,
    predict_scenario_for_date_tile,
)
from models.registry import get_available_models
from scenario.interventions import get_available_interventions

app = FastAPI(title="ThermaML Backend", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class PredictBody(BaseModel):
    model: str
    date: str
    tile_id: int


class ScenarioBody(BaseModel):
    model: str
    date: str
    tile_id: int
    scenario: dict[str, Any]


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/dates")
def api_get_dates() -> list[str]:
    return get_available_dates()


@app.get("/api/tiles")
def api_get_tiles(date: str | None = None):
    try:
        if date is None:
            return get_available_tiles()
        return get_available_tiles(date)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/api/models")
def api_get_models() -> list[str]:
    return get_available_models()


@app.get("/api/interventions")
def api_get_interventions():
    return get_available_interventions()


@app.post("/api/predict")
def api_predict(payload: PredictBody):
    try:
        return predict_for_date_tile(payload.model, payload.date, payload.tile_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/api/compare")
def api_compare(date: str, tile_id: int):
    try:
        return compare_models(date, tile_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/api/scenario")
def api_scenario(payload: ScenarioBody):
    try:
        result = predict_scenario_for_date_tile(
            payload.model,
            payload.date,
            payload.tile_id,
            payload.scenario,
        )
        intervention_payload = result["interventions"]
        tree_effect = intervention_payload["tree_canopy"]["estimated_effect_c"]
        roof_effect = intervention_payload["cool_roof"]["estimated_effect_c"]
        pavement_effect = intervention_payload["cool_pavement"]["estimated_surface_effect_c_range"][1]

        tree_cost = intervention_payload["tree_canopy"]["estimated_cost_usd"]
        roof_cost = intervention_payload["cool_roof"]["estimated_cost_usd"]
        pavement_cost = intervention_payload["cool_pavement"]["estimated_cost_usd"]
        has_any_cost = any(c is not None for c in (tree_cost, roof_cost, pavement_cost))

        return {
            **result,
            "post_intervention_temperature_c": result["scenario_temperature_c"],
            "total_ambient_cooling_c": round(
                float(
                    result["baseline_temperature_c"]
                    - result["scenario_temperature_c"]
                ),
                6,
            ),
            "interventions": {
                "tree_canopy": {
                    **intervention_payload["tree_canopy"],
                    "ambient_cooling_c": tree_effect,
                },
                "cool_roof": {
                    **intervention_payload["cool_roof"],
                    "ambient_cooling_c": roof_effect,
                },
                "cool_pavement": {
                    **intervention_payload["cool_pavement"],
                    "ambient_cooling_c": 0.0,
                    "surface_temp_reduction_c": pavement_effect,
                },
            },
            "costs": {
                "tree_canopy_usd": tree_cost,
                "cool_roof_usd": roof_cost,
                "cool_pavement_usd": pavement_cost,
                "total_estimated_usd": (
                    (tree_cost or 0.0) + (roof_cost or 0.0) + (pavement_cost or 0.0)
                ) if has_any_cost else None,
                "status": "calculated" if has_any_cost else "quantities_omitted",
            },
            "physical_limitations": result["limitations"],
        }
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
