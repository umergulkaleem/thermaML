/**
 * ThermaML Frontend Service Layer
 *
 * Implements the system behavior defined in frontend_contract.md:
 * 1. Discovery: get_available_dates, get_available_tiles, get_available_models, get_available_interventions
 * 2. Prediction: predict_for_date_tile
 * 3. Model Comparison: compare_models
 * 4. Scenario Prediction: predict_scenario_for_date_tile
 *
 * Live mode (USE_MOCK_API = false): calls FastAPI backend exclusively — no fallback to mock.
 * Mock mode (USE_MOCK_API = true): uses built-in simulation engine, no network calls.
 */

// Read API base URL from Vite env var; fall back to localhost for local dev.
const DEFAULT_BASE_URL =
  (typeof import.meta !== "undefined" && import.meta.env?.VITE_API_URL) ||
  "http://localhost:8000/api";

export let USE_MOCK_API = false;
export let BASE_URL = DEFAULT_BASE_URL;

export function setApiConfig(useMock, baseUrl) {
  if (typeof useMock === "boolean") USE_MOCK_API = useMock;
  if (baseUrl) BASE_URL = baseUrl;
}

export function getApiConfig() {
  return { USE_MOCK_API, BASE_URL };
}

function normalizeTileList(rawTiles) {
  if (Array.isArray(rawTiles)) {
    return rawTiles.map((tile) => {
      const tileId = Number(tile?.tile_id ?? tile ?? 0);
      return {
        tile_id: tileId,
        name: tile?.name || `Tile #${tileId}`,
      };
    });
  }
  return [];
}

// Real Phoenix tile IDs (used in mock mode — identical to backend data)
export const MOCK_TILE_IDS = [7, 426, 8, 844, 420, 814];

function normalizeScenario(scenario = {}) {
  const parseQuantity = (val) => {
    if (val === null || val === undefined || val === "") return null;
    const num = Number(val);
    return isNaN(num) ? null : num;
  };

  return {
    tree_canopy_increase_percent: Number(
      scenario.tree_canopy_increase_percent ?? scenario.canopy_pct ?? 0,
    ),
    cool_roof_coverage_percent: Number(
      scenario.cool_roof_coverage_percent ?? scenario.roof_pct ?? 0,
    ),
    cool_pavement_coverage_percent: Number(
      scenario.cool_pavement_coverage_percent ?? scenario.pavement_pct ?? 0,
    ),
    number_of_trees: parseQuantity(scenario.number_of_trees),
    roof_area_sqft: parseQuantity(scenario.roof_area_sqft),
    paved_area_sqft: parseQuantity(scenario.paved_area_sqft),
  };
}

// -----------------------------------------------------------------------------
// 37 EXACT DATES (2023-01-01 to 2024-01-28)
// Strictly adhering to contract specifications: exactly 37 dates in the model-ready dataset.
// -----------------------------------------------------------------------------
export const AVAILABLE_DATES = [
  "2023-01-01",
  "2023-01-11",
  "2023-01-21",
  "2023-01-31",
  "2023-02-10",
  "2023-02-20",
  "2023-03-02",
  "2023-03-12",
  "2023-03-22",
  "2023-04-01",
  "2023-04-11",
  "2023-04-21",
  "2023-05-01",
  "2023-05-11",
  "2023-05-21",
  "2023-05-31",
  "2023-06-10",
  "2023-06-20",
  "2023-06-30",
  "2023-07-10",
  "2023-07-20",
  "2023-07-30",
  "2023-08-09",
  "2023-08-19",
  "2023-08-29",
  "2023-09-08",
  "2023-09-18",
  "2023-09-28",
  "2023-10-08",
  "2023-10-18",
  "2023-10-28",
  "2023-11-07",
  "2023-11-17",
  "2023-11-27",
  "2023-12-07",
  "2023-12-27",
  "2024-01-28",
];

// ---------------------------------------------------------------------------
// Legacy mock tile metadata (kept for reference; not used in live mode)
// ---------------------------------------------------------------------------
export const ALL_TILE_METADATA = {
  101: {
    name: "Downtown Financial Core",
    urbanDensity: 0.92,
    baseCanopy: 8.5,
    baseRoof: 45.0,
    basePavement: 42.0,
    elevationM: 45,
    lat: 34.052,
    lon: -118.243,
  },
  108: {
    name: "High-Density Residential North",
    urbanDensity: 0.78,
    baseCanopy: 14.0,
    baseRoof: 38.0,
    basePavement: 35.0,
    elevationM: 52,
    lat: 34.061,
    lon: -118.252,
  },
  204: {
    name: "Industrial Logistics Hub",
    urbanDensity: 0.88,
    baseCanopy: 4.2,
    baseRoof: 58.0,
    basePavement: 36.0,
    elevationM: 38,
    lat: 34.035,
    lon: -118.225,
  },
  305: {
    name: "Midtown Commercial Corridor",
    urbanDensity: 0.81,
    baseCanopy: 11.5,
    baseRoof: 41.0,
    basePavement: 38.0,
    elevationM: 60,
    lat: 34.058,
    lon: -118.289,
  },
  412: {
    name: "Suburban Parkway West",
    urbanDensity: 0.45,
    baseCanopy: 28.0,
    baseRoof: 25.0,
    basePavement: 22.0,
    elevationM: 95,
    lat: 34.072,
    lon: -118.341,
  },
  426: {
    name: "Central Transit Crossroads",
    urbanDensity: 0.85,
    baseCanopy: 9.0,
    baseRoof: 44.0,
    basePavement: 40.0,
    elevationM: 50,
    lat: 34.05,
    lon: -118.26,
  },
  510: {
    name: "Civic Center & Government Plaza",
    urbanDensity: 0.75,
    baseCanopy: 18.0,
    baseRoof: 35.0,
    basePavement: 32.0,
    elevationM: 65,
    lat: 34.055,
    lon: -118.245,
  },
  620: {
    name: "Mixed-Use Waterfront District",
    urbanDensity: 0.62,
    baseCanopy: 22.0,
    baseRoof: 30.0,
    basePavement: 28.0,
    elevationM: 25,
    lat: 34.028,
    lon: -118.27,
  },
  715: {
    name: "Tech Campus & Innovation Park",
    urbanDensity: 0.58,
    baseCanopy: 25.5,
    baseRoof: 32.0,
    basePavement: 26.0,
    elevationM: 70,
    lat: 34.068,
    lon: -118.305,
  },
  802: {
    name: "South Rail & Distribution Yard",
    urbanDensity: 0.89,
    baseCanopy: 3.5,
    baseRoof: 52.0,
    basePavement: 43.0,
    elevationM: 40,
    lat: 34.015,
    lon: -118.21,
  },
  940: {
    name: "Hillside Foothill Community",
    urbanDensity: 0.32,
    baseCanopy: 38.0,
    baseRoof: 20.0,
    basePavement: 18.0,
    elevationM: 185,
    lat: 34.095,
    lon: -118.28,
  },
};

// In mock mode every date has all six real tiles available
export const DATE_TILES_MAP = Object.fromEntries(
  AVAILABLE_DATES.map((d) => [d, [...MOCK_TILE_IDS]])
);

// Available models per contract: Linear Regression and Random Forest. GNN is unavailable.
export const AVAILABLE_MODELS = ["linear_regression", "random_forest"];

// Intervention metadata matching backend constants in scenario/interventions.py
export const INTERVENTION_METADATA = {
  tree_canopy: {
    id: "tree_canopy",
    name: "Tree Canopy Expansion",
    unit: "%",
    min: 0,
    max: 30,
    defaultDelta: 15,
    unitCost: 1088,              // backend: TREE_COST_PER_TREE_USD = 1088.0
    unitCostLabel: "$1,088 per tree",
    coolingFactorAir: 0.14,      // backend: TREE_COOLING_C_PER_PERCENT = 0.14
    impactTarget: "Air Temperature",
    description:
      "Increases urban evapotranspiration and solar shading, lowering ambient air temperature.",
  },
  cool_roof: {
    id: "cool_roof",
    name: "High-Albedo Cool Roof Coating",
    unit: "%",
    min: 0,
    max: 100,
    defaultDelta: 25,
    unitCostSqFt: 1.15,          // backend: COOL_ROOF_DEFAULT_COST_PER_SQFT_USD = 1.15
    unitCostLabel: "$1.15 / sq ft",
    coolingFactorAtFull: 0.3,    // backend: COOL_ROOF_EFFECT_AT_FULL_C = 0.3
    impactTarget: "Air Temperature",
    description:
      "Reflective membrane roofs reflect incoming solar irradiance and reduce heat storage in building envelopes.",
  },
  cool_pavement: {
    id: "cool_pavement",
    name: "Reflective Cool Pavement",
    unit: "%",
    min: 0,
    max: 100,
    defaultDelta: 20,
    unitCostSqFt: 3.0,           // backend: COOL_PAVEMENT_DEFAULT_COST_PER_SQFT_USD = 3.0
    unitCostLabel: "$3.00 / sq ft",
    coolingFactorAir: 0.0,       // surface effect only — never subtracted from air temp
    surfaceEffectFRange: [10.5, 12.0], // backend: COOL_PAVEMENT_SURFACE_EFFECT_F
    impactTarget: "Surface Temperature Range Only",
    isSurfaceOnly: true,
    description:
      "Specialty reflective pavement reduces surface temperature 10.5–12°F. Does NOT lower ambient air temperature.",
  },
};

// Simulated base mean temperature across all dataset rows (for naive baseline)
const DATASET_ALL_TIME_MEAN_C = 31.4;

// Helper: realistic physics-informed temperature synthesis for mock regression
function calculateMockTemperatures(dateStr, tileId) {
  const meta = ALL_TILE_METADATA[tileId] || {
    urbanDensity: 0.7,
    elevationM: 50,
  };

  // Calculate day of year
  const d = new Date(dateStr);
  const startOfYear = new Date(d.getFullYear(), 0, 1);
  const dayOfYear = Math.floor((d - startOfYear) / (1000 * 60 * 60 * 24)) + 1;

  // Seasonal temperature wave (peak around July day 200)
  const seasonalAngle = ((dayOfYear - 200) / 365) * 2 * Math.PI;
  const seasonalBase = 28.5 + 9.5 * Math.cos(seasonalAngle);

  // Urban heat island (UHI) intensity modifier (+0.5 to +4.5°C based on density)
  const uhiEffect = meta.urbanDensity * 4.2;

  // Elevation lapse rate (-0.015°C per meter relative to baseline)
  const elevationEffect = -(meta.elevationM - 40) * 0.015;

  // Deterministic local weather perturbation for the specific date
  const hash = Math.sin(dayOfYear * 99.7 + tileId * 13.3) * 1.5;

  const trueBase = seasonalBase + uhiEffect + elevationEffect + hash;

  // Linear regression prediction: captures smooth linear trends
  const linearPred = Number(
    (trueBase - 0.3 + Math.sin(tileId) * 0.4).toFixed(3),
  );

  // Random forest prediction: captures non-linear interactions
  const rfPred = Number(
    (
      trueBase +
      (meta.urbanDensity > 0.8 ? 0.4 : -0.2) +
      Math.cos(dayOfYear) * 0.3
    ).toFixed(3),
  );

  // Naive baseline prediction: all-dataset training mean reference
  const naivePred = Number(DATASET_ALL_TIME_MEAN_C.toFixed(3));

  return {
    naive: naivePred,
    linear_regression: linearPred,
    random_forest: rfPred,
  };
}

// Simulated network delay
const delay = (ms = 180) => new Promise((res) => setTimeout(res, ms));

// =============================================================================
// CONTRACT FUNCTION 1: Discovery
// =============================================================================

/**
 * Returns the 37 exact dates present in the model-ready dataset.
 */
export async function get_available_dates() {
  if (!USE_MOCK_API) {
    const res = await fetch(`${BASE_URL}/dates`);
    if (!res.ok) {
      const body = await res.json().catch(() => ({}));
      throw new Error(body.detail || `Failed to load dates (HTTP ${res.status})`);
    }
    return await res.json();
  }
  await delay(120);
  return [...AVAILABLE_DATES];
}

/**
 * Returns only tiles observed for that date.
 * Throws ValueError if date is invalid.
 */
export async function get_available_tiles(date) {
  if (!date) {
    throw new Error("Date is required to load available tiles.");
  }

  if (!USE_MOCK_API) {
    const res = await fetch(
      `${BASE_URL}/tiles?date=${encodeURIComponent(date)}`,
    );
    if (!res.ok) {
      const body = await res.json().catch(() => ({}));
      throw new Error(body.detail || `Failed to load tiles (HTTP ${res.status})`);
    }
    const payload = await res.json();
    const tiles = Array.isArray(payload) ? payload : [payload];
    return normalizeTileList(tiles);
  }

  await delay(100);
  return MOCK_TILE_IDS.map((id) => ({ tile_id: id, name: `Tile #${id}` }));
}

/**
 * Returns list of available models.
 */
export async function get_available_models() {
  if (!USE_MOCK_API) {
    const res = await fetch(`${BASE_URL}/models`);
    if (!res.ok) {
      const body = await res.json().catch(() => ({}));
      throw new Error(body.detail || `Failed to load models (HTTP ${res.status})`);
    }
    return await res.json();
  }
  await delay(80);
  return [...AVAILABLE_MODELS];
}

/**
 * Returns intervention metadata and constraints.
 */
export async function get_available_interventions() {
  if (!USE_MOCK_API) {
    const res = await fetch(`${BASE_URL}/interventions`);
    if (!res.ok) {
      const body = await res.json().catch(() => ({}));
      throw new Error(body.detail || `Failed to load interventions (HTTP ${res.status})`);
    }
    const payload = await res.json();
    if (Array.isArray(payload)) {
      return Object.fromEntries(payload.map((item) => [item.name, item]));
    }
    return payload;
  }
  await delay(80);
  return { ...INTERVENTION_METADATA };
}

// =============================================================================
// CONTRACT FUNCTION 2: Prediction
// =============================================================================

/**
 * Predicts daily temperature for a specific date, tile, and model.
 * Matches JSON contract:
 * {
 *   "model": "random_forest",
 *   "tile_id": 426,
 *   "date": "YYYY-MM-DD",
 *   "predicted_temperature_c": 39.4,
 *   "target": "daily_temperature",
 *   "feature_version": "daily-temperature-v1"
 * }
 */
export async function predict_for_date_tile(model_name, date, tile_id) {
  const numericTileId = Number(tile_id);

  if (!USE_MOCK_API) {
    const res = await fetch(`${BASE_URL}/predict`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        model: model_name,
        date,
        tile_id: numericTileId,
      }),
    });
    if (!res.ok) {
      const body = await res.json().catch(() => ({}));
      throw new Error(body.detail || body.message || `Prediction failed (HTTP ${res.status})`);
    }
    return await res.json();
  }

  // Mock path
  await delay(160);
  const temps = calculateMockTemperatures(date, numericTileId);
  const predicted_temperature_c = temps[model_name] ?? temps.random_forest;
  return {
    model: model_name,
    tile_id: numericTileId,
    date,
    predicted_temperature_c,
    target: "daily_temperature",
    feature_version: "daily-temperature-v1",
  };
}

// =============================================================================
// CONTRACT FUNCTION 3: Model Comparison
// =============================================================================

/**
 * Scored by Linear Regression, Random Forest, and training-mean Naive reference.
 * Matches JSON contract:
 * {
 *   "date": "YYYY-MM-DD",
 *   "tile_id": 426,
 *   "predictions": {
 *     "naive": 39.4,
 *     "linear_regression": 39.4,
 *     "random_forest": 39.4
 *   }
 * }
 */
export async function compare_models(date, tile_id) {
  const numericTileId = Number(tile_id);

  if (!USE_MOCK_API) {
    const res = await fetch(
      `${BASE_URL}/compare?date=${encodeURIComponent(date)}&tile_id=${numericTileId}`,
    );
    if (!res.ok) {
      const body = await res.json().catch(() => ({}));
      throw new Error(body.detail || `Comparison failed (HTTP ${res.status})`);
    }
    return await res.json();
  }

  // Mock path
  await delay(200);
  const predictions = calculateMockTemperatures(date, numericTileId);
  return { date, tile_id: numericTileId, predictions };
}

// =============================================================================
// CONTRACT FUNCTION 4: Scenario Prediction
// =============================================================================

/**
 * Runs what-if urban cooling scenario.
 * Tree canopy & cool roof reduce ambient air temperature.
 * Cool pavement impacts surface temperature range ONLY and is NEVER subtracted from air temperature.
 * Missing required quantities produce null costs.
 */
export async function predict_scenario_for_date_tile(
  model_name,
  date,
  tile_id,
  scenario,
) {
  const numericTileId = Number(tile_id);
  const normalizedScenario = normalizeScenario(scenario || {});

  if (!USE_MOCK_API) {
    const res = await fetch(`${BASE_URL}/scenario`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        model: model_name,
        date,
        tile_id: numericTileId,
        scenario: normalizedScenario,
      }),
    });
    if (!res.ok) {
      const body = await res.json().catch(() => ({}));
      throw new Error(body.detail || body.message || `Scenario failed (HTTP ${res.status})`);
    }
    return await res.json();
  }

  // First obtain baseline prediction
  const baselinePrediction = await predict_for_date_tile(
    model_name,
    date,
    tile_id,
  );
  const baselineTempC = baselinePrediction.predicted_temperature_c;

  const {
    canopy_pct = 0,
    roof_pct = 0,
    pavement_pct = 0,
    number_of_trees = null,
    roof_area_sqft = null,
    paved_area_sqft = null,
  } = scenario || {};

  // Air temperature cooling deltas
  const canopyAirDeltaC = Number(
    (
      Number(canopy_pct || 0) *
      INTERVENTION_METADATA.tree_canopy.coolingFactorAir
    ).toFixed(3),
  );
  const roofAirDeltaC = Number(
    (
      Number(roof_pct || 0) * INTERVENTION_METADATA.cool_roof.coolingFactorAir
    ).toFixed(3),
  );

  // Total air cooling is sum of canopy + cool roof only
  const totalAirCoolingC = Number((canopyAirDeltaC + roofAirDeltaC).toFixed(3));
  const postInterventionTempC = Number(
    (baselineTempC - totalAirCoolingC).toFixed(3),
  );

  // Cool pavement surface effect
  const pavementSurfaceDeltaC = Number(
    (
      Number(pavement_pct || 0) *
      INTERVENTION_METADATA.cool_pavement.coolingFactorSurface
    ).toFixed(3),
  );

  // Cost calculations - null if quantities omitted, 0 if intervention is 0%
  const canopyPercent = Number(canopy_pct || 0);
  const roofPercent = Number(roof_pct || 0);
  const pavementPercent = Number(pavement_pct || 0);

  const hasTreeCount =
    number_of_trees !== null &&
    number_of_trees !== undefined &&
    number_of_trees !== "" &&
    !isNaN(Number(number_of_trees));
  const treeCost = canopyPercent === 0
    ? 0.0
    : (hasTreeCount
      ? Number(
          (
            Number(number_of_trees) * INTERVENTION_METADATA.tree_canopy.unitCost
          ).toFixed(2),
        )
      : null);

  const hasRoofArea =
    roof_area_sqft !== null &&
    roof_area_sqft !== undefined &&
    roof_area_sqft !== "" &&
    !isNaN(Number(roof_area_sqft));
  const roofCost = roofPercent === 0
    ? 0.0
    : (hasRoofArea
      ? Number(
          (
            Number(roof_area_sqft) *
            INTERVENTION_METADATA.cool_roof.unitCostSqFt
          ).toFixed(2),
        )
      : null);

  const hasPavementArea =
    paved_area_sqft !== null &&
    paved_area_sqft !== undefined &&
    paved_area_sqft !== "" &&
    !isNaN(Number(paved_area_sqft));
  const pavementCost = pavementPercent === 0
    ? 0.0
    : (hasPavementArea
      ? Number(
          (
            Number(paved_area_sqft) *
            INTERVENTION_METADATA.cool_pavement.unitCostSqFt
          ).toFixed(2),
        )
      : null);

  const hasAnyCost =
    treeCost !== null || roofCost !== null || pavementCost !== null;
  const totalCost = hasAnyCost
    ? Number(
        ((treeCost || 0) + (roofCost || 0) + (pavementCost || 0)).toFixed(2),
      )
    : null;

  return {
    model: model_name,
    date: date,
    tile_id: Number(tile_id),
    target: "daily_temperature",
    feature_version: "daily-temperature-v1",
    baseline_temperature_c: baselineTempC,
    post_intervention_temperature_c: postInterventionTempC,
    total_ambient_cooling_c: totalAirCoolingC,
    interventions: {
      tree_canopy: {
        applied_pct: Number(canopy_pct || 0),
        ambient_cooling_c: canopyAirDeltaC,
        number_of_trees: hasTreeCount ? Number(number_of_trees) : null,
        estimated_cost_usd: treeCost,
      },
      cool_roof: {
        applied_pct: Number(roof_pct || 0),
        ambient_cooling_c: roofAirDeltaC,
        roof_area_sqft: hasRoofArea ? Number(roof_area_sqft) : null,
        estimated_cost_usd: roofCost,
      },
      cool_pavement: {
        applied_pct: Number(pavement_pct || 0),
        ambient_cooling_c: 0.0, // Strictly 0 per contract
        surface_temp_reduction_c: pavementSurfaceDeltaC,
        paved_area_sqft: hasPavementArea ? Number(paved_area_sqft) : null,
        estimated_cost_usd: pavementCost,
        note: "Surface temp reduction only; does not decrease ambient air temperature.",
      },
    },
    costs: {
      tree_canopy_usd: treeCost,
      cool_roof_usd: roofCost,
      cool_pavement_usd: pavementCost,
      total_estimated_usd: totalCost,
      status: totalCost === null ? "quantities_omitted" : "calculated",
    },
    physical_limitations: [
      "Tree canopy and cool-roof effects are used in the approximate air-temperature scenario result.",
      "Cool pavement remains a surface-temperature range and is never subtracted from air temperature.",
      "Missing required physical quantities produce null costs without raising an exception.",
    ],
  };
}
