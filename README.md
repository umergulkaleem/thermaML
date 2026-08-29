# ThermaML

### Data-Driven Urban Heat Modeling and Heat-Mitigation Decision Support

ThermaML is a research-oriented machine learning decision-support system for modeling local daily thermal variation across a small study area ($N=6$ urban tiles in Phoenix, Arizona across 37 observation dates) and evaluating physical heat-mitigation interventions.

The project connects **FortyGuard environmental API observations**, feature engineering, classical ML models, expanding-window temporal cross-validation, and an evidence-based intervention layer into an interactive decision-support workflow.

---

## FortyGuard API Integration & Data Source

ThermaML is powered directly by environmental observations retrieved via the **FortyGuard Environmental & Heatmap API**:

```text
┌──────────────────────────────────────────────────────────────────────────┐
│                           FortyGuard API                                 │
│                                                                          │
│  • Endpoint: https://api.fortyguard.com/v1/environment                   │
│  • Study Location: Phoenix, AZ (Tiles: 7, 426, 8, 844, 420, 814)         │
│  • Temporal Horizon: 37 discrete dates (2023-01-01 to 2024-01-28)        │
└────────────────────────────────────┬─────────────────────────────────────┘
                                     │
                                     ▼
┌──────────────────────────────────────────────────────────────────────────┐
│                   Raw Hourly Meteorological Fields                       │
│                                                                          │
│  • apparent_temperature_celsius (Derived Target: 24h Daily Mean)         │
│  • air_temperature_celsius, relative_humidity_percent                    │
│  • wind_speed_mps, wind_direction_degrees, solar_radiation_wm2           │
│  • surface_temperature, elevation_m, tile coordinates                   │
└────────────────────────────────────┬─────────────────────────────────────┘
                                     │
                                     ▼
┌──────────────────────────────────────────────────────────────────────────┐
│              ThermaML Feature Engineering Pipeline (features_v1)          │
│                                                                          │
│  • Daily summary statistics: mean, min, max per meteorological feature   │
│  • Curated dataset: 160 tile-date records, 82 distinct daily targets     │
│  • Target Range: 1.96°C to 38.84°C daily apparent temperature            │
└──────────────────────────────────────────────────────────────────────────┘
```



## Research Question & Scope

> **Can date-aligned FortyGuard environmental observations model local daily urban temperature variation across selected Phoenix tiles ($N=6$), and can the resulting models be coupled with evidence-based mitigation scenarios to support urban planning decisions?**

ThermaML evaluates this question on 160 curated observation records using classical regression models under strict chronological expanding-window validation.

---

## Empirical Model Evaluation

Models were evaluated using a 6-fold expanding-window chronological cross-validation where **all training dates strictly precede evaluation dates** (`max(train_dates) < min(test_dates)`), preventing temporal data leakage.

### Fold-by-Fold & Pooled Performance

| Fold | Training Date Range | Evaluation Date Range | Linear Regression MAE | Random Forest MAE | Naive Baseline MAE |
| :---: | :--- | :--- | :---: | :---: | :---: |
| **1** | 2023-01-01 → 2023-09-28 | 2023-10-01 → 2023-10-15 | 3.722 °C | **2.979 °C** | 3.508 °C |
| **2** | 2023-01-01 → 2023-10-15 | 2023-10-28 → 2023-11-01 | 9.738 °C | **5.192 °C** | 2.664 °C |
| **3** | 2023-01-01 → 2023-11-01 | 2023-11-15 → 2023-11-28 | 1.886 °C | **1.644 °C** | 2.809 °C |
| **4** | 2023-01-01 → 2023-11-28 | 2023-12-01 → 2023-12-15 | 6.138 °C | **4.582 °C** | 10.216 °C |
| **5** | 2023-01-01 → 2023-12-15 | 2023-12-28 → 2024-01-01 | 5.164 °C | **2.148 °C** | 12.064 °C |
| **6** | 2023-01-01 → 2024-01-01 | 2024-01-15 → 2024-01-28 | 3.445 °C | **0.977 °C** | 10.178 °C |
| **POOLED** | **Full 2023-2024 Span** | **All Evaluation Folds** | **4.751 °C** | **2.826 °C** | **6.828 °C** |

### Summary Metrics

| Model | Pooled MAE | Pooled RMSE | Pooled R² | Status |
| :--- | :---: | :---: | :---: | :--- |
| **Random Forest Regressor** | **2.826 °C** | **3.549 °C** | **0.682** | **Primary Baseline** |
| **Linear Regression** | 4.751 °C | 5.880 °C | 0.126 | Parametric Baseline |
| **Naive Historical Mean** | 6.828 °C | — | — | Unskilled Baseline |

*Note: Spatial Graph Neural Networks (GNNs) represent an exploratory research direction for larger metropolitan grids; production inference strictly uses the validated Random Forest and Linear Regression model artifacts.*

---

## Heat-Mitigation Intervention Engine

ThermaML couples model baseline predictions with an evidence-based scenario layer:

```text
                  FortyGuard Observations
                            │
                            ▼
                  Random Forest Model
                            │
                            ▼
              Baseline Temperature (°C)
                            │
             ┌──────────────┼──────────────┐
             ▼              ▼              ▼
        Tree Canopy     Cool Roofs   Cool Pavement
        (+0.14°C/%)    (+0.3°C max)  (Surface only)
             │              │              │
             └──────────────┼──────────────┘
                            ▼
                Simulated Thermal State
                 + CapEx Investment ($)
```

### Intervention Parameters
1. **Tree Canopy Expansion**:
   - Estimated Effect: `0.14 °C ambient air cooling` per percentage point increase (up to 30%).
   - Planning Cost: `$1,088 per mature tree` (based on Phoenix urban forestry research).
2. **High-Albedo Cool Roofs**:
   - Estimated Effect: Up to `0.30 °C ambient air cooling` at 100% roof retrofit.
   - Planning Cost: `$1.15 / sq ft`.
3. **Reflective Cool Pavement**:
   - Estimated Effect: `10.5–12.0 °F pavement surface-temperature reduction` (strictly treated as surface cooling and never subtracted from air temperature).
   - Planning Cost: `$3.00 / sq ft`.

---

## Interactive Decision-Support Application

The project includes a full-stack interface connecting the FastAPI backend to a React/Vite dashboard:

```text
Select Date (37 dates) ──► Select Observed Tile (6 tiles) ──► Select Model (RF / LR)
                                                                       │
                                                                       ▼
                                                             Predicted Temperature
                                                            (3 decimal precision)
                                                                       │
                                                                       ▼
                                                            Compare Baseline Models
                                                                       │
                                                                       ▼
                                                             Simulate Interventions
                                                            (Live Cooling & CapEx)
```

---

## Running Locally

### 1. Backend (FastAPI)
```bash
cd "ThermaML backend"
python -m uvicorn api.server:app --host 0.0.0.0 --port 8000
```
API available at `http://localhost:8000`.

### 2. Frontend (React + Vite)
```bash
cd frontend
npm install
npm run dev
```
Dashboard available at `http://localhost:5173`. Configured via `frontend/.env` (`VITE_API_URL=http://localhost:8000/api`).

### 3. Automated Test Suite
```bash
cd "ThermaML backend"
python -m pytest -q
```
All **44/44 unit tests** pass covering model inference, date/tile discovery, intervention calculations, and frontend contracts.

---

## Scientific Positioning & Limitations

- **Scope**: Research prototype evaluated on $N=6$ Phoenix tiles across 37 observation dates.
- **Target Resolution**: Mean daily apparent temperature derived from FortyGuard hourly series.
- **Intervention Interpretation**: Physical scenario approximations for planning support, not causal estimates.
- **References**:
  - *Middel, A., Chhetri, N., & Quay, R. (2015)*: Urban forestry and cool roofs in Phoenix residential neighborhoods.
  - *Rahmatollahi et al. (2026)*: Machine learning and attribution of urban heat in the Phoenix metropolitan.
  - *Amaripadath et al. (2024)*: Multi-criteria decision support for heat stress management.
