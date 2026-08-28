/**
 * ThermaML Frontend Service Layer
 * 
 * Implements the system behavior defined in frontend_contract.md:
 * 1. Discovery: get_available_dates, get_available_tiles, get_available_models, get_available_interventions
 * 2. Prediction: predict_for_date_tile
 * 3. Model Comparison: compare_models
 * 4. Scenario Prediction: predict_scenario_for_date_tile
 * 
 * Supports switching between local mock engine and real backend REST endpoints.
 */

export let USE_MOCK_API = true;
export let BASE_URL = 'http://localhost:8000/api';

export function setApiConfig(useMock, baseUrl) {
  if (typeof useMock === 'boolean') USE_MOCK_API = useMock;
  if (baseUrl) BASE_URL = baseUrl;
}

export function getApiConfig() {
  return { USE_MOCK_API, BASE_URL };
}

// -----------------------------------------------------------------------------
// 37 EXACT DATES (2023-01-01 to 2024-01-28)
// Strictly adhering to contract specifications: exactly 37 dates in the model-ready dataset.
// -----------------------------------------------------------------------------
export const AVAILABLE_DATES = [
  '2023-01-01', '2023-01-11', '2023-01-21', '2023-01-31',
  '2023-02-10', '2023-02-20', '2023-03-02', '2023-03-12',
  '2023-03-22', '2023-04-01', '2023-04-11', '2023-04-21',
  '2023-05-01', '2023-05-11', '2023-05-21', '2023-05-31',
  '2023-06-10', '2023-06-20', '2023-06-30', '2023-07-10',
  '2023-07-20', '2023-07-30', '2023-08-09', '2023-08-19',
  '2023-08-29', '2023-09-08', '2023-09-18', '2023-09-28',
  '2023-10-08', '2023-10-18', '2023-10-28', '2023-11-07',
  '2023-11-17', '2023-11-27', '2023-12-07', '2023-12-27',
  '2024-01-28'
];

// All possible observed geographic tiles in the region with topological metadata
export const ALL_TILE_METADATA = {
  101: { name: 'Downtown Financial Core', urbanDensity: 0.92, baseCanopy: 8.5, baseRoof: 45.0, basePavement: 42.0, elevationM: 45, lat: 34.052, lon: -118.243 },
  108: { name: 'High-Density Residential North', urbanDensity: 0.78, baseCanopy: 14.0, baseRoof: 38.0, basePavement: 35.0, elevationM: 52, lat: 34.061, lon: -118.252 },
  204: { name: 'Industrial Logistics Hub', urbanDensity: 0.88, baseCanopy: 4.2, baseRoof: 58.0, basePavement: 36.0, elevationM: 38, lat: 34.035, lon: -118.225 },
  305: { name: 'Midtown Commercial Corridor', urbanDensity: 0.81, baseCanopy: 11.5, baseRoof: 41.0, basePavement: 38.0, elevationM: 60, lat: 34.058, lon: -118.289 },
  412: { name: 'Suburban Parkway West', urbanDensity: 0.45, baseCanopy: 28.0, baseRoof: 25.0, basePavement: 22.0, elevationM: 95, lat: 34.072, lon: -118.341 },
  426: { name: 'Central Transit Crossroads', urbanDensity: 0.85, baseCanopy: 9.0, baseRoof: 44.0, basePavement: 40.0, elevationM: 50, lat: 34.050, lon: -118.260 },
  510: { name: 'Civic Center & Government Plaza', urbanDensity: 0.75, baseCanopy: 18.0, baseRoof: 35.0, basePavement: 32.0, elevationM: 65, lat: 34.055, lon: -118.245 },
  620: { name: 'Mixed-Use Waterfront District', urbanDensity: 0.62, baseCanopy: 22.0, baseRoof: 30.0, basePavement: 28.0, elevationM: 25, lat: 34.028, lon: -118.270 },
  715: { name: 'Tech Campus & Innovation Park', urbanDensity: 0.58, baseCanopy: 25.5, baseRoof: 32.0, basePavement: 26.0, elevationM: 70, lat: 34.068, lon: -118.305 },
  802: { name: 'South Rail & Distribution Yard', urbanDensity: 0.89, baseCanopy: 3.5, baseRoof: 52.0, basePavement: 43.0, elevationM: 40, lat: 34.015, lon: -118.210 },
  940: { name: 'Hillside Foothill Community', urbanDensity: 0.32, baseCanopy: 38.0, baseRoof: 20.0, basePavement: 18.0, elevationM: 185, lat: 34.095, lon: -118.280 }
};

// Date-to-observed-tiles mapping (simulating variable satellite/sensor coverage for each date)
function generateDateTilesMap() {
  const map = {};
  const allTileIds = Object.keys(ALL_TILE_METADATA).map(Number);
  
  AVAILABLE_DATES.forEach((dateStr, index) => {
    // Keep tile 426 (mentioned in contract) and core tiles consistently observed
    const observed = [426, 101, 204, 305];
    allTileIds.forEach(id => {
      if (!observed.includes(id)) {
        const hash = (index * 13 + id * 7) % 10;
        if (hash >= 3) {
          observed.push(id);
        }
      }
    });
    map[dateStr] = observed.sort((a, b) => a - b);
  });
  return map;
}

export const DATE_TILES_MAP = generateDateTilesMap();

// Available models per contract: Linear Regression and Random Forest. GNN is unavailable.
export const AVAILABLE_MODELS = ['linear_regression', 'random_forest'];

// Intervention metadata definition
export const INTERVENTION_METADATA = {
  tree_canopy: {
    id: 'tree_canopy',
    name: 'Tree Canopy Expansion',
    unit: '%',
    min: 0,
    max: 100,
    defaultDelta: 15,
    unitCost: 350,
    unitCostLabel: '$350 per tree',
    coolingFactorAir: 0.045, // ~0.045°C air reduction per +1% canopy cover
    impactTarget: 'Air Temperature',
    description: 'Increases urban evapotranspiration and solar shading, lowering ambient air temperature.'
  },
  cool_roof: {
    id: 'cool_roof',
    name: 'High-Albedo Cool Roof Coating',
    unit: '%',
    min: 0,
    max: 100,
    defaultDelta: 25,
    unitCostSqFt: 1.85,
    unitCostLabel: '$1.85 / sq ft',
    coolingFactorAir: 0.028, // ~0.028°C air reduction per +1% cool roof
    impactTarget: 'Air Temperature',
    description: 'Reflective membrane roofs reflect incoming solar irradiance and reduce heat storage in building envelopes.'
  },
  cool_pavement: {
    id: 'cool_pavement',
    name: 'Reflective Cool Pavement',
    unit: '%',
    min: 0,
    max: 100,
    defaultDelta: 20,
    unitCostSqFt: 0.75,
    unitCostLabel: '$0.75 / sq ft',
    coolingFactorAir: 0.0, // 0.0°C! Direct ambient air is strictly untouched per contract!
    coolingFactorSurface: 0.35, // ~0.35°C surface reduction per +1% cool pavement
    impactTarget: 'Surface Temperature Range Only',
    isSurfaceOnly: true,
    description: 'Specialty permeable/reflective asphalt coatings reduce surface pavement temp by up to 12°C. Does NOT lower ambient air temperature directly.'
  }
};

// Simulated base mean temperature across all dataset rows (for naive baseline)
const DATASET_ALL_TIME_MEAN_C = 31.4;

// Helper: realistic physics-informed temperature synthesis for mock regression
function calculateMockTemperatures(dateStr, tileId) {
  const meta = ALL_TILE_METADATA[tileId] || { urbanDensity: 0.7, elevationM: 50 };
  
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
  const linearPred = Number((trueBase - 0.3 + Math.sin(tileId) * 0.4).toFixed(1));
  
  // Random forest prediction: captures non-linear interactions
  const rfPred = Number((trueBase + (meta.urbanDensity > 0.8 ? 0.4 : -0.2) + Math.cos(dayOfYear) * 0.3).toFixed(1));
  
  // Naive baseline prediction: all-dataset training mean reference
  const naivePred = Number(DATASET_ALL_TIME_MEAN_C.toFixed(1));
  
  return {
    naive: naivePred,
    linear_regression: linearPred,
    random_forest: rfPred
  };
}

// Simulated network delay
const delay = (ms = 180) => new Promise(res => setTimeout(res, ms));

// =============================================================================
// CONTRACT FUNCTION 1: Discovery
// =============================================================================

/**
 * Returns the 37 exact dates present in the model-ready dataset.
 */
export async function get_available_dates() {
  if (!USE_MOCK_API) {
    try {
      const res = await fetch(`${BASE_URL}/dates`);
      if (!res.ok) throw new Error(`HTTP error ${res.status}`);
      return await res.json();
    } catch (err) {
      console.warn('API error in get_available_dates, falling back to mock:', err);
    }
  }
  await delay(120);
  return [...AVAILABLE_DATES];
}

/**
 * Returns only tiles observed for that date.
 * Throws ValueError if date is invalid.
 */
export async function get_available_tiles(date) {
  if (!date || !AVAILABLE_DATES.includes(date)) {
    throw new Error(`ValueError: Date '${date}' is not available in the model-ready dataset (37 dates available between 2023-01-01 and 2024-01-28).`);
  }

  if (!USE_MOCK_API) {
    try {
      const res = await fetch(`${BASE_URL}/tiles?date=${encodeURIComponent(date)}`);
      if (!res.ok) throw new Error(`HTTP error ${res.status}`);
      return await res.json();
    } catch (err) {
      console.warn('API error in get_available_tiles, falling back to mock:', err);
    }
  }

  await delay(100);
  const tiles = DATE_TILES_MAP[date] || [426, 101, 204];
  return tiles.map(id => ({
    tile_id: id,
    ...(ALL_TILE_METADATA[id] || { name: `Tile #${id}`, urbanDensity: 0.7, elevationM: 50 })
  }));
}

/**
 * Returns list of available models.
 */
export async function get_available_models() {
  if (!USE_MOCK_API) {
    try {
      const res = await fetch(`${BASE_URL}/models`);
      if (!res.ok) throw new Error(`HTTP error ${res.status}`);
      return await res.json();
    } catch (err) {
      console.warn('API error in get_available_models, falling back to mock:', err);
    }
  }
  await delay(80);
  return [...AVAILABLE_MODELS];
}

/**
 * Returns intervention metadata and constraints.
 */
export async function get_available_interventions() {
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
  // Validate model
  if (!AVAILABLE_MODELS.includes(model_name)) {
    if (model_name === 'gnn') {
      throw new Error("ValueError: The documented Graph Neural Network (GNN) model is currently unavailable in this release. Please select 'linear_regression' or 'random_forest'.");
    }
    throw new Error(`ValueError: Invalid model '${model_name}'. Available models: ${AVAILABLE_MODELS.join(', ')}`);
  }

  // Validate date
  if (!AVAILABLE_DATES.includes(date)) {
    throw new Error(`ValueError: Date '${date}' not found in model-ready dataset.`);
  }

  // Validate tile for date
  const validTiles = DATE_TILES_MAP[date] || [];
  const numericTileId = Number(tile_id);
  if (!validTiles.includes(numericTileId)) {
    throw new Error(`ValueError: Tile ${numericTileId} was not observed on date '${date}'. Available tiles on this date: ${validTiles.join(', ')}`);
  }

  if (!USE_MOCK_API) {
    try {
      const res = await fetch(`${BASE_URL}/predict`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ model: model_name, date, tile_id: numericTileId })
      });
      if (!res.ok) {
        const errorData = await res.json().catch(() => ({}));
        throw new Error(errorData.detail || `HTTP error ${res.status}`);
      }
      return await res.json();
    } catch (err) {
      console.warn('API error in predict_for_date_tile, falling back to mock:', err);
    }
  }

  await delay(160);
  const temps = calculateMockTemperatures(date, numericTileId);
  const predicted_temperature_c = temps[model_name] ?? temps.random_forest;

  return {
    model: model_name,
    tile_id: numericTileId,
    date: date,
    predicted_temperature_c: predicted_temperature_c,
    target: "daily_temperature",
    feature_version: "daily-temperature-v1"
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
  if (!AVAILABLE_DATES.includes(date)) {
    throw new Error(`ValueError: Date '${date}' is not available in the model-ready dataset.`);
  }
  const numericTileId = Number(tile_id);
  const validTiles = DATE_TILES_MAP[date] || [];
  if (!validTiles.includes(numericTileId)) {
    throw new Error(`ValueError: Tile ${numericTileId} was not observed on date '${date}'.`);
  }

  if (!USE_MOCK_API) {
    try {
      const res = await fetch(`${BASE_URL}/compare?date=${encodeURIComponent(date)}&tile_id=${numericTileId}`);
      if (!res.ok) {
        const errorData = await res.json().catch(() => ({}));
        throw new Error(errorData.detail || `HTTP error ${res.status}`);
      }
      return await res.json();
    } catch (err) {
      console.warn('API error in compare_models, falling back to mock:', err);
    }
  }

  await delay(200);
  const predictions = calculateMockTemperatures(date, numericTileId);

  return {
    date: date,
    tile_id: numericTileId,
    predictions: predictions
  };
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
export async function predict_scenario_for_date_tile(model_name, date, tile_id, scenario) {
  // First obtain baseline prediction
  const baselinePrediction = await predict_for_date_tile(model_name, date, tile_id);
  const baselineTempC = baselinePrediction.predicted_temperature_c;

  const {
    canopy_pct = 0,
    roof_pct = 0,
    pavement_pct = 0,
    number_of_trees = null,
    roof_area_sqft = null,
    paved_area_sqft = null
  } = scenario || {};

  // Air temperature cooling deltas
  const canopyAirDeltaC = Number((Number(canopy_pct || 0) * INTERVENTION_METADATA.tree_canopy.coolingFactorAir).toFixed(2));
  const roofAirDeltaC = Number((Number(roof_pct || 0) * INTERVENTION_METADATA.cool_roof.coolingFactorAir).toFixed(2));
  
  // Total air cooling is sum of canopy + cool roof only
  const totalAirCoolingC = Number((canopyAirDeltaC + roofAirDeltaC).toFixed(2));
  const postInterventionTempC = Number((baselineTempC - totalAirCoolingC).toFixed(2));

  // Cool pavement surface effect
  const pavementSurfaceDeltaC = Number((Number(pavement_pct || 0) * INTERVENTION_METADATA.cool_pavement.coolingFactorSurface).toFixed(2));

  // Cost calculations - null if quantities omitted
  const hasTreeCount = number_of_trees !== null && number_of_trees !== undefined && number_of_trees !== '';
  const treeCost = hasTreeCount
    ? Number((Number(number_of_trees) * INTERVENTION_METADATA.tree_canopy.unitCost).toFixed(2))
    : null;

  const hasRoofArea = roof_area_sqft !== null && roof_area_sqft !== undefined && roof_area_sqft !== '';
  const roofCost = hasRoofArea
    ? Number((Number(roof_area_sqft) * INTERVENTION_METADATA.cool_roof.unitCostSqFt * (Number(roof_pct || 0) / 100)).toFixed(2))
    : null;

  const hasPavementArea = paved_area_sqft !== null && paved_area_sqft !== undefined && paved_area_sqft !== '';
  const pavementCost = hasPavementArea
    ? Number((Number(paved_area_sqft) * INTERVENTION_METADATA.cool_pavement.unitCostSqFt * (Number(pavement_pct || 0) / 100)).toFixed(2))
    : null;

  const hasAnyCost = treeCost !== null || roofCost !== null || pavementCost !== null;
  const totalCost = hasAnyCost
    ? Number(((treeCost || 0) + (roofCost || 0) + (pavementCost || 0)).toFixed(2))
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
        estimated_cost_usd: treeCost
      },
      cool_roof: {
        applied_pct: Number(roof_pct || 0),
        ambient_cooling_c: roofAirDeltaC,
        roof_area_sqft: hasRoofArea ? Number(roof_area_sqft) : null,
        estimated_cost_usd: roofCost
      },
      cool_pavement: {
        applied_pct: Number(pavement_pct || 0),
        ambient_cooling_c: 0.0, // Strictly 0 per contract
        surface_temp_reduction_c: pavementSurfaceDeltaC,
        paved_area_sqft: hasPavementArea ? Number(paved_area_sqft) : null,
        estimated_cost_usd: pavementCost,
        note: "Surface temp reduction only; does not decrease ambient air temperature."
      }
    },
    costs: {
      tree_canopy_usd: treeCost,
      cool_roof_usd: roofCost,
      cool_pavement_usd: pavementCost,
      total_estimated_usd: totalCost,
      status: totalCost === null ? "quantities_omitted" : "calculated"
    },
    physical_limitations: [
      "Tree canopy and cool-roof effects are used in the approximate air-temperature scenario result.",
      "Cool pavement remains a surface-temperature range and is never subtracted from air temperature.",
      "Missing required physical quantities produce null costs without raising an exception."
    ]
  };
}
