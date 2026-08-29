# ThermaML

### Data-Driven Urban Heat Modeling and Heat-Mitigation Decision Support

ThermaML is a research-oriented machine learning system for modeling local daily thermal conditions and exploring evidence-based heat-mitigation strategies.

The system uses environmental observations obtained through the **FortyGuard API**, transforms date-aligned hourly environmental measurements into daily features, evaluates classical machine learning regression models using chronological validation, and connects model predictions to an evidence-based heat-mitigation scenario engine.

The current study focuses on **six urban tiles in Phoenix, Arizona across 37 observation dates**, providing a controlled and reproducible experimental setting for investigating data-driven urban thermal modeling and decision support.

> **Current scope:** ThermaML is a research prototype for daily tile-level thermal estimation. It is not currently an hourly forecasting system or a city-wide urban heat model.

---

## What ThermaML Does

```text
                    FortyGuard API
                          │
                          ▼
              Date-Specific Environmental
                   Observations
                          │
                          ▼
                  Hourly Measurements
                          │
                          ▼
               Daily Feature Engineering
                          │
                          ▼
                 Tile-Date Dataset
                          │
                 ┌────────┴────────┐
                 ▼                 ▼
          Linear Regression   Random Forest
                 │                 │
                 └────────┬────────┘
                          ▼
                Daily Thermal Prediction
                          │
                          ▼
              Heat-Mitigation Scenarios
                 ┌────────┼────────┐
                 ▼        ▼        ▼
             Tree Canopy Cool Roof Cool Pavement
                 │        │        │
                 └────────┼────────┘
                          ▼
                Decision-Support Output
```

The project separates **machine learning prediction** from **intervention simulation**. The ML models learn relationships from environmental observations, while intervention effects are supplied through published scientific evidence and public planning sources rather than being learned as causal effects from the dataset.

---

# Research Motivation

Urban heat varies with meteorological conditions, surface characteristics, and local environmental context. Data-driven models can potentially help characterize this variation and provide a computational basis for exploring heat-management strategies.

ThermaML investigates this problem through a reproducible pipeline that combines:

* environmental observations
* daily feature engineering
* supervised regression
* chronological temporal validation
* model comparison
* evidence-based mitigation scenarios
* interactive decision support

A central design principle is maintaining a distinction between **what the data-driven model predicts** and **what the intervention literature suggests may happen under a mitigation scenario**.

---

# Research Question

> **Can date-aligned environmental observations from the FortyGuard API be used to model local daily thermal variation across selected Phoenix urban tiles, and can those predictions be coupled with evidence-based mitigation scenarios to support heat-management decisions?**

The current implementation evaluates this question using Linear Regression and Random Forest on a small Phoenix study area.

---

# FortyGuard API Usage

**FortyGuard is the primary environmental data source for ThermaML.**

The project uses the FortyGuard Environmental API to obtain date-specific environmental observations for selected Phoenix urban tiles.

The API is not simply used as an external reference. Its environmental observations form the underlying dataset used for feature engineering and model development.

### Data acquisition workflow

```text
FortyGuard Environmental API
             │
             ▼
       Phoenix Tile
             │
             ▼
    Date-specific request
             │
             ▼
   24-hour environmental series
             │
             ▼
       Data validation
             │
             ▼
     Daily aggregation
             │
             ▼
       Model-ready data
```

### Study configuration

| Component               | Configuration                        |
| ----------------------- | ------------------------------------ |
| Data source             | FortyGuard Environmental API         |
| Study region            | Phoenix, Arizona                     |
| Spatial units           | 6 urban tiles                        |
| Tile IDs                | `7`, `426`, `8`, `844`, `420`, `814` |
| Observation dates       | 37                                   |
| Date range              | `2023-01-01` to `2024-01-28`         |
| Raw temporal resolution | Hourly                               |
| Curated observations    | 160 tile-date records                |

### Environmental variables

The retrieved observations include environmental and meteorological variables such as:

* apparent temperature
* air temperature
* relative humidity
* wind speed
* wind direction
* solar radiation
* surface temperature
* elevation
* latitude
* longitude

The raw hourly observations are converted into date-aligned daily records before being supplied to the regression models.

---

# Study at a Glance

| Component               | Description                                     |
| ----------------------- | ----------------------------------------------- |
| Study area              | Phoenix, Arizona                                |
| Spatial units           | 6 urban tiles                                   |
| Observation dates       | 37                                              |
| Tile-date records       | 160                                             |
| Raw temporal resolution | Hourly                                          |
| ML target               | 24-hour mean apparent temperature               |
| Target unit             | °C                                              |
| Models                  | Linear Regression, Random Forest                |
| Primary model           | Random Forest                                   |
| Validation              | Expanding-window chronological cross-validation |
| Primary metric          | MAE                                             |
| Scenario layer          | Tree canopy, cool roofs, cool pavement          |

The dataset contains **160 tile-date observations and 82 distinct daily target values** across the six selected tiles.

---

# Target Definition

The machine learning target is:

> **24-hour mean apparent temperature (°C)**

For each tile and observation date, the hourly apparent-temperature observations are aggregated into a single daily target.

This produces a date-specific thermal target with meaningful temporal variation across the study period.

The target definition is important because ThermaML is designed around **daily thermal estimation**, not hourly temperature forecasting.

```text
24 hourly apparent-temperature observations
                    │
                    ▼
             Daily aggregation
                    │
                    ▼
       Mean apparent temperature
                    │
                    ▼
              ML target (°C)
```

---

# Feature Engineering

ThermaML converts hourly environmental observations into structured daily tile-date records.

For relevant environmental variables, daily summary statistics are calculated, including:

* mean
* minimum
* maximum

This transforms the raw hourly observations into a compact feature representation suitable for classical regression.

The resulting feature set is versioned as:

```text
features_v1
```

The feature-engineering process is deterministic, allowing the model-ready dataset to be reproduced from the same underlying observations.

---

# Machine Learning Models

ThermaML currently evaluates two regression approaches.

## Linear Regression

Linear Regression provides a transparent parametric baseline.

It evaluates whether a linear relationship between the engineered environmental features and daily thermal conditions can adequately explain the observed variation.

## Random Forest

Random Forest provides a nonlinear ensemble model capable of representing nonlinear relationships and interactions between environmental variables.

Random Forest is the primary model in the current implementation because it achieved the strongest performance among the evaluated models.

---

# Temporal Validation

For environmental data, random train-test splitting can produce overly optimistic results when observations from later dates influence model evaluation.

ThermaML therefore uses **expanding-window chronological cross-validation**.

The fundamental constraint is:

```text
Maximum training date < Minimum evaluation date
```

The evaluation process follows:

```text
Historical observations
          │
          ▼
       Training
          │
          ▼
   Later observations
          │
          ▼
      Evaluation
          │
          ▼
     Expand window
          │
          ▼
      Next fold
```

This ensures that each evaluation period occurs after the corresponding training period.

The approach provides a more realistic assessment of temporal generalization than a random split.

---

# Model Evaluation

## Pooled Results

| Model                 |   Pooled MAE |  Pooled RMSE | Pooled R² |
| --------------------- | -----------: | -----------: | --------: |
| **Random Forest**     | **2.826 °C** | **3.549 °C** | **0.682** |
| Linear Regression     |     4.751 °C |     5.880 °C |     0.126 |
| Naive Historical Mean |     6.828 °C |            — |         — |

Under the pooled chronological evaluation, **Random Forest achieved the lowest MAE** among the evaluated approaches.

It also outperformed the naive historical-mean reference.

These results indicate that the environmental features contain useful information for modeling daily thermal variation within the current study dataset.

However, the results should be interpreted within the scope of the six selected Phoenix tiles and should not be treated as evidence of city-wide predictive performance.

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

The variation between folds demonstrates that predictive performance changes across different temporal periods, reinforcing the importance of chronological evaluation.

---

# Heat-Mitigation Decision Support

ThermaML adds a separate scenario layer after generating a baseline ML prediction.

```text
Environmental Features
          │
          ▼
     ML Prediction
          │
          ▼
 Baseline Temperature
          │
     ┌────┼────┐
     ▼    ▼    ▼
   Trees Roof Pavement
     │    │    │
     └────┼────┘
          ▼
   Scenario Estimates
          │
          ▼
  Planning Cost Estimates
```

The intervention engine does **not** retrain the machine learning models.

It also does not claim to estimate causal intervention effects from the training dataset.

Instead, it applies values derived from published research, government guidance, and public planning information.

---

# Intervention Parameters and Sources

## 1. Tree Canopy Expansion

### Model input

```text
tree_canopy_increase_percent
```

Configured range:

```text
0–30 percentage points
```

### Estimated thermal effect

```text
0.14 °C air-temperature reduction
per percentage-point increase
```

### Cost

```text
$1,088 per mature tree
```

### Source of the thermal effect

The **0.14 °C per percentage-point value** is based on:

**Middel, A., Chhetri, N., & Quay, R. (2015)**
*Urban forestry and cool roofs: Assessment of heat mitigation strategies in Phoenix residential neighborhoods.*

DOI:

```text
10.1016/j.ufug.2014.09.010
```

The study evaluates heat-mitigation strategies in Phoenix residential neighborhoods and provides the scientific basis for the configured tree-canopy effect.

### Source of the tree cost

The **$1,088 per mature tree** planning value is based on the Phoenix urban forestry cost assumption used by the project.

It is treated as a **planning estimate**, not a guaranteed current implementation cost.

### Interpretation

The 0.14 °C value is not treated as a universal physical law. It is an evidence-based approximation derived from a Phoenix-specific study and applied within the configured scenario range.

---

# 2. Cool Roofs

### Model input

```text
cool_roof_coverage_percent
```

Configured range:

```text
0–100%
```

### Estimated thermal effect

At full modeled coverage:

```text
≈ 0.30 °C air-temperature reduction
```

The scenario engine uses simplified linear interpolation between zero coverage and the modeled full-coverage effect.

### Cost

```text
$1.15 / sq ft
```

### Source of the thermal effect

The **0.30 °C modeled neighborhood air-temperature effect** is based on:

**Middel, A., Chhetri, N., & Quay, R. (2015)**
*Urban forestry and cool roofs: Assessment of heat mitigation strategies in Phoenix residential neighborhoods.*

DOI:

```text
10.1016/j.ufug.2014.09.010
```

### Source of the cost

The **$1.15/sq ft** planning value is the midpoint of the U.S. Department of Energy example range of approximately **$0.80–$1.50 per square foot** for cool-roof implementation.

Source:

**U.S. Department of Energy, Cool Roofs Guide**

### Interpretation

The modeled 0.30 °C effect is treated as a neighborhood-level scenario approximation. Actual cooling depends on roof materials, building characteristics, urban morphology, weather, and implementation conditions.

---

# 3. Cool Pavement

### Model input

```text
cool_pavement_coverage_percent
```

Configured range:

```text
0–100%
```

### Estimated effect

The project retains the reported pavement surface-temperature reduction as:

```text
10.5–12.0 °F
```

approximately:

```text
5.8–6.7 °C
```

### Critical modeling distinction

The cool-pavement effect is a **surface-temperature reduction**.

It is **not treated as an equivalent air-temperature reduction**.

Therefore:

```text
Baseline air temperature
        +
Cool pavement scenario
        =
Air temperature unchanged by pavement effect

Surface temperature
        ↓
Estimated reduction of approximately 5.8–6.7 °C
```

ThermaML deliberately does not subtract the pavement effect from the ML air-temperature prediction.

### Cost

```text
$3.00 / sq ft
```

### Sources

The cool-pavement scenario is informed by:

* **City of Phoenix Cool Pavement Program**
* **U.S. Environmental Protection Agency Heat Island Community Actions Database**
* **City of Phoenix cool-pavement feasibility/planning documentation**

These sources provide the basis for treating cool pavement as a surface-temperature intervention rather than directly converting its effect into an air-temperature reduction.

---

# Intervention Cost Model

When the required quantities are provided, ThermaML estimates planning costs.

### Trees

```text
Tree Cost
= Number of Trees × $1,088
```

### Cool Roofs

```text
Roof Cost
= Roof Area × $1.15/sq ft
```

### Cool Pavement

```text
Pavement Cost
= Paved Area × $3.00/sq ft
```

These values are **planning assumptions**, not contractor quotations.

Actual implementation costs can vary substantially according to materials, location, labor, project scale, site preparation, and procurement.

---

# Interactive Decision-Support Application

ThermaML includes a full-stack interactive application consisting of:

* React
* Vite
* FastAPI
* Python machine learning backend

The frontend communicates with the FastAPI backend through HTTP endpoints.

### Application workflow

```text
Select Date
    │
    ▼
Select Phoenix Tile
    │
    ▼
Select Model
    │
    ▼
Generate Prediction
    │
    ├───────────────┐
    ▼               ▼
Model Comparison   Scenario Simulator
    │               │
    │               ├── Tree Canopy
    │               ├── Cool Roof
    │               └── Cool Pavement
    │
    ▼
Decision-Support Output
```

The frontend obtains available dates, tiles, models, and interventions through backend discovery endpoints rather than relying on hardcoded production metadata.

### Supported models

* Linear Regression
* Random Forest

---

# Backend API

The FastAPI backend exposes the core application operations.

### Discovery

```text
GET /api/dates
GET /api/tiles
GET /api/models
GET /api/interventions
```

### Prediction

```text
POST /api/predict
```

### Scenario simulation

```text
POST /api/scenario
```

### Model comparison

```text
GET /api/compare
```

The backend is the authoritative source for available dates, tiles, model names, predictions, and scenario calculations.

---

# Research Contribution

ThermaML is not intended to introduce a new machine learning algorithm.

Its contribution is an integrated and reproducible framework connecting:

1. FortyGuard environmental observations
2. date-aligned data processing
3. daily target construction
4. environmental feature engineering
5. classical machine learning
6. chronological model evaluation
7. naive-baseline comparison
8. evidence-based intervention scenarios
9. planning-cost estimation
10. interactive decision support

This architecture creates a foundation for future research involving larger spatial datasets, longer temporal coverage, uncertainty quantification, and spatial/spatiotemporal modeling.

---

# Spatial Modeling and Future Extension

Urban thermal conditions are inherently spatial, making spatial modeling a natural extension of ThermaML.

The current study includes six geographically distinct Phoenix tiles. These locations provide an initial basis for future spatial experiments but are insufficient for claiming city-scale spatial generalization.

A lightweight Graph Neural Network was considered as an exploratory direction.

Future work can investigate:

* larger spatial tile networks
* graph-based urban representations
* spatial holdout validation
* spatiotemporal models
* cross-location generalization
* metropolitan-scale datasets

The current release does not report GNN performance and does not claim GNN-based spatial generalization.

---

# Limitations

The results should be interpreted within the scope of the current experimental design.

### Limited spatial coverage

The study contains only six Phoenix tiles.

Therefore, the reported model performance does not establish city-wide predictive capability.

### Limited temporal coverage

The curated dataset contains 37 observation dates.

A longer observation period would provide stronger evidence for seasonal and temporal generalization.

### Daily target resolution

The target is the 24-hour mean apparent temperature.

The current system does not provide hourly temperature forecasting.

### Observed-date inference

The current inference system operates on dates represented in the available environmental dataset.

It should not be interpreted as an arbitrary future-date forecasting service.

### Intervention assumptions

Intervention effects are evidence-based scenario approximations rather than causal estimates learned from the ML dataset.

### Small sample size

With 160 tile-date records, the current dataset is appropriate for a controlled prototype but remains small for drawing broad generalization claims.

### Spatial generalization

No claim is made that a model trained on the six selected Phoenix tiles will generalize to other neighborhoods or cities.

---

# Future Research

The current framework can be extended through:

* additional FortyGuard observations
* larger spatial tile coverage
* longer temporal observation periods
* spatial holdout validation
* spatiotemporal machine learning
* Graph Neural Networks on larger spatial grids
* uncertainty quantification
* calibrated prediction intervals
* cross-city transfer evaluation
* urban morphology features
* land-surface characteristics
* physically informed intervention models
* causal inference for mitigation effects

These extensions could move ThermaML from a small empirical prototype toward a broader urban thermal modeling and decision-support framework.

---

# Reproducibility

## Requirements

The backend requires Python and the dependencies listed in the backend project.

The frontend requires Node.js and npm.

---

## Start the Backend

```bash
cd "ThermaML backend"

python -m uvicorn api.server:app --host 0.0.0.0 --port 8000
```

The API will be available at:

```text
http://localhost:8000
```

---

## Start the Frontend

```bash
cd frontend

npm install
npm run dev
```

The Vite development server will provide the interactive dashboard.

The frontend API configuration is controlled through:

```text
frontend/.env
```

Example:

```text
VITE_API_URL=http://localhost:8000/api
```

---

## Run Tests

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
│   │   └── server.py
│   │
│   ├── models/
│   │   ├── inference.py
│   │   └── ...
│   │
│   ├── scenario/
│   │   └── interventions.py
│   │
│   ├── pipelines/
│   │   └── ...
│   │
│   ├── tests/
│   │   └── ...
│   │
│   ├── trained_models/
│   │   └── ...
│   │
│   └── README.md
│
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   ├── context/
│   │   ├── services/
│   │   └── ...
│   │
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

## Urban Forestry and Cool Roofs

Middel, A., Chhetri, N., & Quay, R. (2015).

*Urban forestry and cool roofs: Assessment of heat mitigation strategies in Phoenix residential neighborhoods.*

DOI:

`10.1016/j.ufug.2014.09.010`

[ScienceDirect](https://www.sciencedirect.com/science/article/pii/S161886671400106X)

[Arizona State University Research Record](https://asu.elsevierpure.com/en/publications/urban-forestry-and-cool-roofs-assessment-of-heat-mitigation-strat/)

---

## Cool Roof Guidance

U.S. Department of Energy.

*Cool Roofs Guide.*

https://www1.eere.energy.gov/buildings/publications/pdfs/corporate/coolroofguide.pdf

---

## Cool Pavement

City of Phoenix.

*Cool Pavement Program.*

https://www.phoenix.gov/administration/departments/streets/initiatives/pavement-maintenance/cool-pavement-program.html

U.S. Environmental Protection Agency.

*Heat Island Community Actions Database.*

https://www.epa.gov/heatislands/heat-island-community-actions-database

City of Phoenix.

*Cool Pavement feasibility/planning documentation.*

https://www.phoenix.gov/content/dam/phoenix/streetssite/documents/3rd%20st_lincoln%20st%20to%20washington%20st_design%20concept%20report.pdf

---

## Urban Heat and Machine Learning

Rahmatollahi et al. (2026).

*Machine learning and attribution of urban heat in the Phoenix metropolitan area.*

---

## Heat-Stress Decision Support

Amaripadath et al. (2024).

*Multi-criteria decision support for heat stress management.*

---

# Citation

If you use ThermaML, its dataset-processing methodology, model evaluation framework, or intervention scenario design in academic work, please cite the repository and the underlying scientific sources listed above.

---

# License

See the repository license for terms of use.
