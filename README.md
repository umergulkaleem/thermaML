**Submission Note:** > This repository was created before the hackathon
> kickoff date solely to add a teammate as a collaborator. All project
> commits, code, data collection, model training, and documentation were
> completed after the official kickoff. No project work exists in this
> repo prior to the hackathon start date.

# ThermaML
### Data-Driven Urban Heat Modeling & Mitigation Decision Support

> **City sustainability offices spend millions on heat mitigation — trees, cool roofs, reflective pavement — with no way to compare interventions before committing budget. ThermaML changes that.**

Built on the FortyGuard API's street-level temperature data, ThermaML predicts daily thermal conditions across urban tiles and tells planners exactly which interventions to buy, where to deploy them, and what temperature drop to expect per dollar spent — backed by peer-reviewed science, not guesswork.

**Live Demo →** `https://therma-ml.vercel.app/`  
**Track:** Track 1 — Resilient Cities & Infrastructure · Secondary: Track 5 — Model Designing  
**Study Area:** Phoenix · Jan 2023 – Jan 2024  
**Stack:** Python · FastAPI · React · Vite · FortyGuard Environmental API

---

## The Problem

Phoenix recorded peak temperatures above 110°F across dozens of consecutive days in 2023. Standard weather grids average conditions across kilometers — they cannot see the 8°C difference between a shaded park block and an exposed concrete corridor two streets away.

City planners making shade investment decisions are working blind. They pick a neighborhood, allocate budget, plant trees or coat pavement, and check results two summers later with no model, no counterfactual, and no proof the money was spent in the right place.

**ThermaML gives planners the model before the shovel hits the ground.**

---

## Who This Is For

**Primary user — City Sustainability Officer / Urban Planner**  
You have a heat mitigation budget. You need to know: which tiles are hottest, which interventions cool them most, and what the cost breakdown looks like before you go to council. ThermaML gives you that answer in one dashboard.

**Secondary user — Climate Researcher**  
You need a reproducible, temporally honest ML pipeline for urban thermal modeling that separates data-driven prediction from evidence-based intervention effects. ThermaML is designed for exactly that — and every component is documented for extension.

---

## What ThermaML Does

```
FortyGuard API
      │
      ▼
24-Hour Hourly Environmental Series
      │
      ▼
Daily Feature Engineering (mean · min · max per variable)
      │
      ▼
ML Core ──────────────────────────────────────┐
  ├── Linear Regression (transparent baseline) │
  └── Random Forest (primary model)            │
      │                                        │
      ▼                                        ▼
Daily Thermal Prediction            Model Comparison View
      │
      ▼
Evidence-Based Intervention Engine
  ├── Tree Canopy   → -0.14°C per 1% canopy (Middel et al. 2015)
  ├── Cool Roofs    → -0.30°C at full coverage (DOE)
  └── Cool Pavement → -5.8 to -6.7°C surface temp (City of Phoenix)
      │
      ▼
Budget Cost Estimator
      │
      ▼
Interactive Decision Dashboard (React + FastAPI)
```

**The key design principle:** ML models learn from data. Intervention effects come from published science. These two layers are kept strictly separate — the system never claims to have learned causal intervention effects from 160 observations.

---

## Study Configuration

| Component | Detail |
|---|---|
| Data source | FortyGuard Environmental API |
| Study region | Phoenix|
| Spatial units | 6 urban tiles (IDs: 7, 426, 8, 844, 420, 814) |
| Observation dates | 37 |
| Date range | 2023-01-01 → 2024-01-28 |
| Raw resolution | Hourly |
| Curated records | 160 tile-date observations |
| ML target | 24-hour mean apparent temperature (°C) |
| Models | Linear Regression, Random Forest |
| Validation | Expanding-window chronological cross-validation |
| Primary metric | MAE (°C) |

---

## Environmental Variables (via FortyGuard API)

Each tile-date record is built from hourly observations of:

- Apparent temperature
- Air temperature
- Relative humidity
- Wind speed and direction
- Solar radiation
- Surface temperature
- Elevation · Latitude · Longitude

These are aggregated into daily mean, minimum, and maximum features (`features_v1`) before being passed to the regression models.

---

## Validation: Why Chronological CV Matters

Random train-test splits allow future observations to leak into training — producing accuracy numbers that are impossible to reproduce in deployment.

ThermaML uses **expanding-window chronological cross-validation** with a hard constraint:

```
max(training date) < min(evaluation date)
```

Every fold extends the training window forward in time and evaluates on the next unseen period. This is the only honest way to evaluate a model on time-ordered environmental data.

### 6-Fold Results

| Fold | Training Range | Eval Range | LR MAE | RF MAE | Naive MAE |
|---|---|---|---|---|---|
| 1 | 2023-01-01 → 2023-09-28 | 2023-10-01 → 2023-10-15 | 3.722°C | **2.979°C** | 3.508°C |
| 2 | 2023-01-01 → 2023-10-15 | 2023-10-28 → 2023-11-01 | 9.738°C | **5.192°C** | 2.664°C |
| 3 | 2023-01-01 → 2023-11-01 | 2023-11-15 → 2023-11-28 | 1.886°C | **1.644°C** | 2.809°C |
| 4 | 2023-01-01 → 2023-11-28 | 2023-12-01 → 2023-12-15 | 6.138°C | **4.582°C** | 10.216°C |
| 5 | 2023-01-01 → 2023-12-15 | 2023-12-28 → 2024-01-01 | 5.164°C | **2.148°C** | 12.064°C |
| 6 | 2023-01-01 → 2024-01-01 | 2024-01-15 → 2024-01-28 | 3.445°C | **0.977°C** | 10.178°C |
| **Pooled** | Full study span | All eval folds | 4.751°C | **2.826°C** | 6.828°C |

---

## Model Performance

| Model | MAE | RMSE | R² |
|---|---|---|---|
| **Random Forest** | **2.826°C** | **3.549°C** | **0.682** |
| Linear Regression | 4.751°C | 5.880°C | 0.126 |
| Naive Historical Mean | 6.828°C | — | — |

**Random Forest beats the naive baseline by 58.6%.** In practical terms: the model correctly identifies which tiles require priority intervention across the full validation period — not by chance, but because the FortyGuard environmental features carry genuine predictive signal for daily thermal conditions.

Linear Regression remains in the system as a transparent parametric baseline. Its interpretability is a feature — planners can inspect which variables drive the prediction linearly before relying on the ensemble model.

---

## Evidence-Based Intervention Engine

After ML prediction generates a baseline temperature, a separate scenario layer applies intervention effects derived from peer-reviewed research and public planning guidance.

**This layer does not retrain the models. It does not claim causal effects learned from 160 observations. It applies science to a model-generated baseline.**

### Tree Canopy Expansion
- **Effect:** −0.14°C per 1 percentage-point increase in canopy cover
- **Range:** 0–30 percentage points
- **Cost:** $1,088 per mature tree
- **Source:** Middel, A., Chhetri, N., & Quay, R. (2015). *Urban forestry and cool roofs: Assessment of heat mitigation strategies in Phoenix residential neighborhoods.* [DOI: 10.1016/j.ufug.2014.09.010](https://doi.org/10.1016/j.ufug.2014.09.010)

### Cool Roofs
- **Effect:** −0.30°C neighborhood air temperature at full coverage
- **Range:** 0–100% coverage (linear interpolation)
- **Cost:** $1.15/sqft (DOE midpoint estimate)
- **Source:** Middel et al. (2015) + [U.S. DOE Cool Roofs Guide](https://www1.eere.energy.gov/buildings/publications/pdfs/corporate/coolroofguide.pdf)

### Cool Pavement
- **Effect:** −5.8°C to −6.7°C **surface temperature** reduction
- **Critical distinction:** This is a surface temperature effect, not an air temperature effect. ThermaML deliberately does not subtract the pavement value from the ML air-temperature prediction — to do so would misrepresent the science.
- **Cost:** $3.00/sqft
- **Sources:** [City of Phoenix Cool Pavement Program](https://www.phoenix.gov/administration/departments/streets/initiatives/pavement-maintenance/cool-pavement-program.html) · [EPA Heat Island Community Actions Database](https://www.epa.gov/heatislands/heat-island-community-actions-database)

---

## Budget Decision Engine

Given a tile, a baseline ML temperature prediction, and a budget, ThermaML outputs a ranked intervention plan.

```
Trees:          N trees  × $1,088 / tree
Cool Roofs:     Area     × $1.15  / sqft
Cool Pavement:  Area     × $3.00  / sqft
```

**Example output:**
```
Tile 7 · Baseline: 38.4°C predicted
Scenario: +15% canopy (500 trees) + 40% cool roof coverage
Estimated cost:    $544,000 trees + $230,000 roofs = $774,000
Predicted cooling: −2.1°C (canopy) + −0.12°C (roofs) = −2.22°C air temp
Surface temp note: cool pavement at this site → −6.1°C surface reduction
```

Cost values are planning estimates based on Phoenix urban forestry data and DOE guidance — not contractor quotations. Actual costs vary by materials, labor, site conditions, and project scale.

---

## Architecture

### Backend — FastAPI + Python

```
ThermaML backend/
├── api/
│   └── server.py          # FastAPI application
├── models/
│   └── inference.py       # LR + RF prediction
├── scenario/
│   └── interventions.py   # evidence-based scenario engine
├── pipelines/             # feature engineering pipeline
├── trained_models/        # serialized model artifacts
└── tests/                 # full backend test suite
```

**API Endpoints**

```
Discovery
  GET  /api/dates           available observation dates
  GET  /api/tiles           available Phoenix tile IDs
  GET  /api/models          available ML models
  GET  /api/interventions   available scenario types

Prediction
  POST /api/predict         generate daily thermal prediction

Scenario
  POST /api/scenario        run intervention scenario on prediction

Comparison
  GET  /api/compare         compare LR vs RF on selected tile/date
```

The backend is the single source of truth for all metadata, predictions, and scenario calculations. The frontend never hardcodes dates, tile IDs, or model names.

### Frontend — React + Vite

```
frontend/
├── src/
│   ├── components/        # prediction panel, scenario sliders, comparison view
│   ├── context/           # global state
│   └── services/          # API client layer
```

**Frontend capabilities:**
- Date and tile selector (populated from backend discovery endpoints)
- Model selector (Linear Regression / Random Forest)
- Live prediction display with model comparison
- Scenario simulator — sliders for canopy %, roof coverage %, pavement coverage %
- Cost estimator output with planning totals
- Side-by-side model comparison view

---

## Quickstart

**Requirements:** Python 3.9+, Node.js 18+, npm

```bash
# 1. Clone the repo
git clone https://github.com/umergulkaleem/thermaML.git
cd ThermaML

# 2. Start the backend
cd "ThermaML backend"
python -m uvicorn api.server:app --host 0.0.0.0 --port 8000

# 3. Start the frontend (new terminal)
cd frontend
npm install
npm run dev

# 4. Run the test suite
cd "ThermaML backend"
python -m pytest -q
```


Frontend available at `https://therma-ml.vercel.app/`

---

## Limitations — Read Before Citing Results

These are stated explicitly because research integrity matters more than making the numbers look bigger than they are.

**Spatial coverage:** Six Phoenix tiles. Results do not establish city-wide predictive capability. Do not generalise to other neighborhoods or cities without retraining on appropriate data.

**Temporal coverage:** 37 observation dates, 160 tile-date records. This is a controlled prototype dataset — sufficient for a reproducible empirical study, insufficient for broad seasonal generalisation claims.

**Daily resolution only:** The ML target is the 24-hour mean apparent temperature. ThermaML is not an hourly forecasting system.

**Intervention effects are not causal:** The tree canopy, cool roof, and cool pavement values come from published literature applied to model predictions. They are evidence-based approximations, not causal estimates derived from this dataset.

**Inference is observation-bound:** The current system runs inference on dates within the study dataset. It is not an arbitrary future-date forecasting service.

---

## Roadmap

The current release is a validated, reproducible prototype. The architecture is explicitly designed for these extensions:

**Spatial scale**
- Graph Neural Networks on larger Phoenix tile networks — the tile graph structure is defined and the validation framework supports spatial holdout
- Cross-city transfer experiments (Dallas, Miami, Las Vegas)
- Metropolitan-scale FortyGuard datasets

**Temporal depth**
- Multi-year observation periods for seasonal generalisation
- Conformal prediction intervals for calibrated uncertainty
- Spatiotemporal models combining spatial and temporal signals

**Decision science**
- Causal inference methods for intervention effect estimation
- Urban morphology and land-surface features
- Physically-informed mitigation models
- Integration with public vulnerability indices (CDC SVI, US Census)

---

## Scientific References

Middel, A., Chhetri, N., & Quay, R. (2015). Urban forestry and cool roofs: Assessment of heat mitigation strategies in Phoenix residential neighborhoods. *Urban Forestry & Urban Greening.* https://doi.org/10.1016/j.ufug.2014.09.010

U.S. Department of Energy. Cool Roofs Guide. https://www1.eere.energy.gov/buildings/publications/pdfs/corporate/coolroofguide.pdf

City of Phoenix. Cool Pavement Program. https://www.phoenix.gov/administration/departments/streets/initiatives/pavement-maintenance/cool-pavement-program.html

U.S. Environmental Protection Agency. Heat Island Community Actions Database. https://www.epa.gov/heatislands/heat-island-community-actions-database

Rahmatollahi et al. (2026). Machine learning and attribution of urban heat in the Phoenix metropolitan area.

Amaripadath et al. (2024). Multi-criteria decision support for heat stress management.

---

## Hackathon Submission

**Event:** FortyGuard Hackathon 2026  
**Track:** Track 1 — Resilient Cities & Infrastructure (primary) · Track 5 — Model Designing (secondary)  
**API usage:** FortyGuard Environmental API — date-specific tile observations forming the full model-ready dataset  
**AI tools used:** [declare here per submission form requirements]

---

## License

See `LICENSE` for terms of use.
