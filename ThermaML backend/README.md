# ThermaML

ThermaML evaluates daily tile/date temperature regression for a small Phoenix environmental dataset. Current models are Linear Regression and Random Forest. The target is a daily scalar temperature in degrees Celsius, not an hourly forecast.

## Running Locally

**Backend** (FastAPI on port 8000):
```bash
cd "ThermaML backend"
python -m uvicorn api.server:app --host 0.0.0.0 --port 8000
```

**Frontend** (Vite on port 5173):
```bash
cd frontend
npm run dev
```

To use a custom backend URL, set `VITE_API_URL` in `frontend/.env`:
```
VITE_API_URL=http://localhost:8000/api
```

**Available models:** `linear_regression`, `random_forest`  
**GNN:** documented but not available in this release.

**Daily prediction limitation:** Only dates and tiles present in the training dataset are supported (2023-01-01 to 2024-01-28, 6 Phoenix tiles). Arbitrary future dates and hourly forecasts are not supported.

**Scenario simulator:** After obtaining a baseline prediction, the scenario engine applies evidence-based air-temperature effects for tree canopy (+0.14 °C/% point) and cool roofs (+0.3 °C at full coverage). Cool pavement is a surface-temperature reduction only and is never subtracted from air temperature.



## Heat-Mitigation Scenario Features

The scenario engine in `scenario/interventions.py` operates after an ML model produces a baseline temperature. Intervention inputs are not training features and their effects are not learned causally by the current models.

### Tree canopy / shade

- Input: `tree_canopy_increase_percent`, percentage points, configured from 0 to 30.
- Impact: estimated air-temperature reduction of 0.14 degrees C per percentage point, based on the Phoenix neighborhood study by Middel, Chhetri, and Quay (2015).
- Cost: number of trees multiplied by $1,088 per tree when `number_of_trees` is provided. No area-based tree cost is invented.
- Source: Middel, A., Chhetri, N., & Quay, R. (2015), DOI `10.1016/j.ufug.2014.09.010`; [ScienceDirect](https://www.sciencedirect.com/science/article/pii/S161886671400106X) and [ASU record](https://asu.elsevierpure.com/en/publications/urban-forestry-and-cool-roofs-assessment-of-heat-mitigation-strat/).
- Limitation: this is an evidence-based Phoenix residential-neighborhood result, not a universal citywide law. The configured range is an approximation.

### Cool roofs

- Input: `cool_roof_coverage_percent`, percentage of relevant roof area, from 0 to 100.
- Impact: simplified linear interpolation to a 0.3 degrees C neighborhood air-temperature effect at full coverage, based on Middel, Chhetri, and Quay (2015).
- Cost: `roof_area_sqft` multiplied by configurable `cool_roof_cost_per_sqft`; the default planning value is $1.15 per square foot, the midpoint of the DOE example range of $0.80-$1.50 per square foot.
- Source: [ScienceDirect Phoenix study](https://www.sciencedirect.com/science/article/pii/S161886671400106X) and [DOE cool-roof guidance](https://www1.eere.energy.gov/buildings/publications/pdfs/corporate/coolroofguide.pdf).
- Limitation: the 0.3 degrees C result is a modeled neighborhood scenario, not an exact effect at every coverage level or location. Installation cost varies by roof type and contractor.

### Cool pavement

- Input: `cool_pavement_coverage_percent`, percentage of selected paved area, from 0 to 100.
- Impact: retained as an estimated pavement surface-temperature reduction range of 10.5-12 degrees F, converted to Celsius. It is not subtracted from air temperature.
- Cost: `paved_area_sqft` multiplied by configurable `cool_pavement_cost_per_sqft`; the default planning value is $3.00 per square foot.
- Source: [City of Phoenix Cool Pavement Program](https://www.phoenix.gov/administration/departments/streets/initiatives/pavement-maintenance/cool-pavement-program.html), [EPA Heat Island Community Actions Database](https://www.epa.gov/heatislands/heat-island-community-actions-database), and [Phoenix feasibility study](https://www.phoenix.gov/content/dam/phoenix/streetssite/documents/3rd%20st_lincoln%20st%20to%20washington%20st_design%20concept%20report.pdf).
- Limitation: the cited effect is a pavement surface-temperature result, not an equivalent air-temperature prediction. Cost is a planning estimate, not a guaranteed current contractor price.

Combined tree and roof air effects are presented as a simplified planning approximation. Intervention interactions are not modeled, and the scenario layer does not establish causal intervention effects.

## Lightweight Spatial Model

A lightweight GNN was assessed as a possible exploratory baseline but was not implemented in this environment. Neither PyTorch nor PyTorch Geometric is installed, and no existing tensor or graph dependency is available. Installing a large dependency was outside this experiment's scope.

The six existing Phoenix tile coordinates were verified in the raw environmental records:

| Tile |      Latitude |       Longitude |
| ---: | ------------: | --------------: |
|    7 | 33.4449877169 | -112.0652745924 |
|  426 | 33.4525027099 | -112.0751393914 |
|    8 | 33.4453610910 | -112.0848233711 |
|  844 | 33.4596435957 | -112.0654538190 |
|  420 | 33.4524687519 | -112.0790481332 |
|  814 | 33.4594740686 | -112.0849991266 |

No graph, GNN artifact, temporal GNN evaluation, or spatial holdout was created because the required implementation dependency is unavailable. These six locations would form only a very small exploratory graph and cannot support claims of city-scale spatial generalization.

## Frontend Integration

Frontend clients should use the backend discovery helpers to populate available dates and tiles, then let the user select one of the saved models: Linear Regression or Random Forest. The backend returns a daily tile/date temperature prediction, and `compare_models` returns both model predictions plus the naive reference for the same row without retraining.

The scenario operation accepts tree canopy, cool-roof, and cool-pavement selections with their required quantities. It returns the baseline model temperature, evidence-based scenario estimates, costs when quantities are supplied, and scientific limitations. Interventions are scenario approximations, not causal ML predictions; cool pavement remains a surface-temperature effect.

The current target is daily temperature. Only dates and tiles with available environmental observations are supported. This is not an hourly or arbitrary-future forecasting API. See [docs/frontend_contract.md](docs/frontend_contract.md) for the frontend-facing operations and response shapes.
