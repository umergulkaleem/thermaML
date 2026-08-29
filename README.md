# ThermaML

### Data-Driven Urban Heat Modeling and Heat-Mitigation Decision Support

ThermaML is a research-oriented machine learning system for modeling local daily thermal conditions across selected urban locations and evaluating potential heat-mitigation strategies.

The system transforms hourly environmental observations into date-aligned daily features, evaluates classical machine learning models using chronological validation, and connects model predictions with an evidence-based intervention simulator.

The current study focuses on **six urban tiles in Phoenix, Arizona across 37 observation dates**, providing a reproducible prototype for data-driven urban heat analysis and decision support.

---

## Research Motivation

Urban heat is influenced by meteorological conditions, surface characteristics, and local spatial context. Understanding this variation can help identify areas of elevated thermal exposure and support evaluation of potential mitigation strategies.

ThermaML investigates whether environmental observations can provide useful predictions of local daily thermal conditions while maintaining a strict separation between:

* **data-driven ML predictions**, learned from environmental observations
* **model evaluation**, performed using chronological validation
* **intervention scenarios**, based on published physical evidence rather than learned causal relationships

This distinction is central to the design of the system.

---

## Research Question

> **Can date-aligned environmental observations from the FortyGuard API be used to model local daily thermal variation across selected Phoenix urban tiles, and can those predictions be coupled with evidence-based mitigation scenarios to support heat-management decisions?**

The current implementation evaluates this question using classical regression models on a small Phoenix study area.

---

## Study at a Glance

| Component               | Description                                     |
| ----------------------- | ----------------------------------------------- |
| Study area              | Phoenix, Arizona                                |
| Spatial units           | 6 urban tiles                                   |
| Observation dates       | 37                                              |
| Tile-date observations  | 160                                             |
| Raw temporal resolution | Hourly                                          |
| ML target               | 24-hour mean apparent temperature               |
| Target unit             | °C                                              |
| Models                  | Linear Regression, Random Forest                |
| Primary model           | Random Forest                                   |
| Validation              | Expanding-window chronological cross-validation |
| Primary metric          | Mean Absolute Error (MAE)                       |

The current dataset contains **160 tile-date observations and 82 distinct daily target values** across the six selected tiles.

---

## System Overview

```text
              FortyGuard Environmental API
                         │
                         ▼
               Hourly Environmental Data
                         │
                         ▼
                Data Preparation
                         │
                         ▼
              Daily Feature Engineering
                         │
                         ▼
              ┌──────────────────────┐
              │   Regression Models  │
              │                      │
              │ Linear Regression    │
              │ Random Forest        │
              └──────────┬───────────┘
                         │
                         ▼
          Expanding-Window Temporal Validation
                         │
                         ▼
              Daily Thermal Prediction
                         │
                         ▼
              Heat-Mitigation Scenarios
                         │
                         ▼
             Interactive Decision Support
```

---

# Data Source

ThermaML uses environmental observations retrieved through the **FortyGuard Environmental & Heatmap API**.

### Study configuration

* **Region:** Phoenix, Arizona
* **Tiles:** `7`, `426`, `8`, `844`, `420`, `814`
* **Observation dates:** 37
* **Date range:** `2023-01-01` to `2024-01-28`
* **Raw temporal resolution:** hourly environmental observations
* **Curated dataset:** 160 tile-date records

The raw environmental observations contain meteorological and environmental variables including:

* apparent temperature
* air temperature
* relative humidity
* wind speed
* wind direction
* solar radiation
* surface temperature
* elevation
* geographic coordinates

The hourly observations are transformed into daily summary features before model training.

---

# Target Definition

The machine learning target is:

> **24-hour mean apparent temperature (°C)**

For each tile and observation date, the hourly apparent-temperature observations are aggregated to produce a single daily target.

This target was selected because it provides meaningful temporal variation across the observation period while remaining compatible with the available date-aligned environmental observations.

The current system therefore performs **daily tile-level thermal estimation**, not hourly forecasting.

---

# Feature Engineering

ThermaML converts hourly environmental observations into date-aligned daily features.

For relevant environmental variables, daily summary statistics are calculated, including:

* mean
* minimum
* maximum

This produces a structured tile-date dataset suitable for classical regression.

The resulting feature set is versioned as:

`features_v1`

The feature engineering process is deterministic so that the same raw observations can reproduce the model-ready dataset.

---

# Machine Learning Models

ThermaML currently evaluates two regression approaches.

### Linear Regression

Linear Regression provides a simple parametric baseline and establishes whether a linear relationship between environmental features and the daily thermal target is sufficient to explain the observed variation.

### Random Forest

Random Forest provides a nonlinear ensemble baseline capable of modeling interactions and nonlinear relationships between environmental variables.

Random Forest is the primary model in the current implementation because it achieved the strongest performance among the evaluated approaches.

---

# Temporal Validation

Random train-test splitting can introduce temporal leakage when environmental observations from later dates influence predictions for earlier dates.

To reduce this risk, ThermaML uses **expanding-window chronological cross-validation**.

The validation principle is:

```text
Training dates < Evaluation dates
```

For every evaluation fold:

```text
Past observations
       │
       ▼
   Training
       │
       ▼
Future observations
       │
       ▼
  Evaluation
```

The training period therefore always precedes the evaluation period.

This provides a more realistic evaluation of how the models perform when applied to later observations.

---

# Model Evaluation

## Key Results

| Model                 |   Pooled MAE |  Pooled RMSE | Pooled R² |
| --------------------- | -----------: | -----------: | --------: |
| **Random Forest**     | **2.826 °C** | **3.549 °C** | **0.682** |
| Linear Regression     |     4.751 °C |     5.880 °C |     0.126 |
| Naive Historical Mean |     6.828 °C |            — |         — |

Under the pooled chronological evaluation, **Random Forest achieved the lowest MAE** among the evaluated approaches.

The Random Forest result also outperformed the naive historical-mean baseline, providing evidence that the environmental feature set contains useful information for modeling variation in the daily target within this study dataset.

These results should be interpreted within the scope of the current six-tile Phoenix study and should not be treated as evidence of city-wide generalization.

---

## Fold-by-Fold Evaluation

|       Fold | Training Date Range     | Evaluation Date Range    | Linear Regression MAE | Random Forest MAE | Naive Baseline MAE |
| ---------: | ----------------------- | ------------------------ | --------------------: | ----------------: | -----------------: |
|          1 | 2023-01-01 → 2023-09-28 | 2023-10-01 → 2023-10-15  |              3.722 °C |      **2.979 °C** |           3.508 °C |
|          2 | 2023-01-01 → 2023-10-15 | 2023-10-28 → 2023-11-01  |              9.738 °C |      **5.192 °C** |           2.664 °C |
|          3 | 2023-01-01 → 2023-11-01 | 2023-11-15 → 2023-11-28  |              1.886 °C |      **1.644 °C** |           2.809 °C |
|          4 | 2023-01-01 → 2023-11-28 | 2023-12-01 → 2023-12-15  |              6.138 °C |      **4.582 °C** |          10.216 °C |
|          5 | 2023-01-01 → 2023-12-15 | 2023-12-28 → 2024-01-01  |              5.164 °C |      **2.148 °C** |          12.064 °C |
|          6 | 2023-01-01 → 2024-01-01 | 2024-01-15 → 2024-01-28  |              3.445 °C |      **0.977 °C** |          10.178 °C |
| **Pooled** | **Full study span**     | **All evaluation folds** |          **4.751 °C** |      **2.826 °C** |       **6.828 °C** |

The variation between folds demonstrates that model performance is not uniform across time. This is one reason chronological evaluation is important for the current dataset.

---

# Prediction and Intervention Simulation

A key design principle in ThermaML is that **ML prediction and intervention simulation are separate components**.

### ML prediction

The machine learning model estimates the baseline thermal condition using environmental observations.

```text
Environmental Features
          │
          ▼
    Random Forest
          │
          ▼
Baseline Daily Temperature
```

### Intervention simulation

The intervention layer is applied **after** the baseline prediction.

```text
Baseline Prediction
        │
        ├── Tree Canopy
        │
        ├── Cool Roof
        │
        └── Cool Pavement
                │
                ▼
       Scenario Estimate
       + Planning Costs
```

The intervention layer does **not** train the ML model and does not claim to learn causal intervention effects from the dataset.

Instead, it applies evidence-based approximations from published research and public guidance.

---

# Heat-Mitigation Decision Support

ThermaML currently supports three intervention scenarios.

## 1. Tree Canopy Expansion

**Input**

`tree_canopy_increase_percent`

Configured range:

`0–30 percentage points`

**Estimated effect**

`0.14 °C air-temperature reduction per percentage point`

**Planning cost**

`$1,088 per mature tree`

The effect is based on published Phoenix residential-neighborhood research and is treated as a planning approximation rather than a universal city-wide relationship.

**Source**

Middel, A., Chhetri, N., & Quay, R. (2015).

DOI:

`10.1016/j.ufug.2014.09.010`

---

## 2. Cool Roofs

**Input**

`cool_roof_coverage_percent`

Configured range:

`0–100%`

**Estimated effect**

Up to approximately:

`0.30 °C`

at full modeled coverage.

**Planning cost**

`$1.15 / sq ft`

The effect is represented using a simplified interpolation for scenario analysis. Actual effects depend on roof characteristics, neighborhood configuration, weather conditions, and implementation details.

---

## 3. Cool Pavement

**Input**

`cool_pavement_coverage_percent`

Configured range:

`0–100%`

**Estimated effect**

`10.5–12.0 °F` pavement surface-temperature reduction.

This corresponds approximately to:

`5.8–6.7 °C`

The crucial distinction is that this is a **surface-temperature effect**, not an equivalent air-temperature reduction.

Therefore, ThermaML does **not subtract the cool-pavement effect from the predicted air temperature**.

**Planning cost**

`$3.00 / sq ft`

---

# Cost and Scenario Modeling

When the required quantities are supplied, ThermaML estimates planning costs.

Examples include:

```text
Tree cost
= number of trees × $1,088

Cool-roof cost
= roof area × $1.15/sq ft

Cool-pavement cost
= paved area × $3.00/sq ft
```

These are planning estimates rather than contractor quotations or guaranteed implementation costs.

---

# Interactive Decision-Support Application

ThermaML includes a React/Vite frontend connected to a FastAPI backend.

The interface allows a user to:

1. Select an available observation date.
2. Select an available Phoenix tile.
3. Select a trained model.
4. Generate a daily thermal prediction.
5. Compare Linear Regression, Random Forest, and the naive reference.
6. Configure heat-mitigation interventions.
7. View estimated thermal effects and planning costs.

The application obtains available dates, tiles, models, and intervention information from the backend rather than relying on hardcoded tile metadata.

### Current supported models

* Linear Regression
* Random Forest

The current application operates on dates and tiles represented in the available environmental dataset.

---

# Research Contribution

ThermaML is not intended to introduce a new machine learning algorithm.

Its contribution is an integrated and reproducible workflow that connects:

1. environmental observations
2. date-aligned feature engineering
3. daily thermal target construction
4. classical regression modeling
5. chronological temporal validation
6. comparison against a naive baseline
7. evidence-based heat-mitigation scenarios
8. interactive decision support

This provides a foundation for extending the study toward larger spatial datasets, richer temporal coverage, uncertainty-aware prediction, and spatial/spatiotemporal modeling.

---

# Spatial Modeling: Future Direction

Spatial machine learning is a natural extension of the current study because the environmental observations are associated with geographic tile locations.

A lightweight Graph Neural Network was considered as an exploratory direction. However, the current study does not report GNN results or claim spatial generalization.

The six selected Phoenix tiles provide a useful starting point for spatial experimentation, but a substantially larger spatial dataset would be required to evaluate spatial generalization reliably.

Future spatial modeling could investigate:

* graph-based representations of urban tiles
* spatial holdout validation
* spatiotemporal models
* cross-location generalization
* larger metropolitan grids

---

# Research Limitations

The current findings should be interpreted within the scope of the available dataset.

### Limited spatial coverage

The study contains only six Phoenix tiles. The results therefore do not establish city-wide predictive performance.

### Limited temporal coverage

The curated dataset contains 37 observation dates. More dates would provide a stronger basis for evaluating seasonal and temporal generalization.

### Daily target resolution

The current target is a 24-hour mean apparent temperature. The system does not currently provide hourly temperature forecasts.

### Observed-date inference

The current inference system operates on dates represented in the available environmental dataset. It should not be described as an arbitrary future-date forecasting system.

### Intervention uncertainty

The intervention layer uses evidence-based approximations. It does not estimate causal intervention effects from the ML training data.

### Spatial generalization

No claim is made that a model trained on the six selected tiles will generalize to other Phoenix neighborhoods or other cities.

---

# Future Research

Several extensions can build on the current framework:

* Expand the number of spatial tiles.
* Increase the temporal observation period.
* Evaluate spatial holdout performance.
* Investigate spatiotemporal machine learning models.
* Explore Graph Neural Networks on larger spatial grids.
* Add uncertainty quantification and calibrated prediction intervals.
* Evaluate transferability across additional urban environments.
* Incorporate additional urban morphology and land-surface features.
* Develop more rigorous physically informed intervention models.
* Investigate causal methods for estimating intervention effects.

These extensions would allow the system to move from a small empirical prototype toward a more comprehensive urban heat modeling framework.

---

# Reproducibility

## Backend

```bash
cd "ThermaML backend"
python -m uvicorn api.server:app --host 0.0.0.0 --port 8000
```

The FastAPI backend provides model discovery, date/tile discovery, prediction, model comparison, and scenario simulation endpoints.

## Frontend

```bash
cd frontend
npm install
npm run dev
```

The frontend uses:

```text
VITE_API_URL=http://localhost:8000/api
```

## Tests

```bash
cd "ThermaML backend"
python -m pytest -q
```

The backend test suite covers model inference, discovery operations, intervention calculations, API behavior, and frontend contract compatibility.

---

# Project Structure

```text
ThermaML/
│
├── ThermaML backend/
│   ├── api/
│   ├── models/
│   ├── scenario/
│   ├── pipelines/
│   ├── tests/
│   ├── trained_models/
│   └── README.md
│
├── frontend/
│   ├── src/
│   ├── public/
│   └── package.json
│
├── docs/
│   └── frontend_contract.md
│
└── README.md
```

---

# Scientific References

### Urban forestry and cool roofs

Middel, A., Chhetri, N., & Quay, R. (2015). *Urban forestry and cool roofs: Assessment of heat mitigation strategies in Phoenix residential neighborhoods.*

DOI: `10.1016/j.ufug.2014.09.010`

[ScienceDirect](https://www.sciencedirect.com/science/article/pii/S161886671400106X)

[Arizona State University Research Record](https://asu.elsevierpure.com/en/publications/urban-forestry-and-cool-roofs-assessment-of-heat-mitigation-strat/)

### Machine learning and urban heat

Rahmatollahi et al. (2026). *Machine learning and attribution of urban heat in the Phoenix metropolitan area.*

### Decision support for heat management

Amaripadath et al. (2024). *Multi-criteria decision support for heat stress management.*

### Cool roofs

U.S. Department of Energy. *Cool Roofs Guide.*

### Cool pavement

City of Phoenix. *Cool Pavement Program.*

EPA. *Heat Island Community Actions Database.*

---

# License

See the repository license for terms of use.
