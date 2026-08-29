import React, {
  createContext,
  useContext,
  useState,
  useEffect,
  useCallback,
} from "react";
import {
  get_available_dates,
  get_available_tiles,
  get_available_models,
  get_available_interventions,
  predict_for_date_tile,
  compare_models,
  predict_scenario_for_date_tile,
  setApiConfig,
  getApiConfig,
  USE_MOCK_API,
  BASE_URL,
} from "../services/api";

const ThermaMLContext = createContext(null);

export const ThermaMLProvider = ({ children }) => {
  // Config state
  const [useMock, setUseMock] = useState(USE_MOCK_API);
  const [baseUrl, setBaseUrl] = useState(BASE_URL);

  // Selection states
  const [availableDates, setAvailableDates] = useState([]);
  const [selectedDate, setSelectedDate] = useState("2024-01-28");

  const [availableTiles, setAvailableTiles] = useState([]);
  const [selectedTileId, setSelectedTileId] = useState(8);

  const [availableModels, setAvailableModels] = useState([]);
  const [selectedModel, setSelectedModel] = useState("random_forest");

  const [interventionsMeta, setInterventionsMeta] = useState(null);

  // Result states
  const [singlePrediction, setSinglePrediction] = useState(null);
  const [comparisonResult, setComparisonResult] = useState(null);
  const [scenarioResult, setScenarioResult] = useState(null);

  // Scenario Simulator Inputs
  const [scenarioInputs, setScenarioInputs] = useState({
    canopy_pct: 15,
    roof_pct: 25,
    pavement_pct: 20,
    number_of_trees: 120,
    roof_area_sqft: 20000,
    paved_area_sqft: 35000,
  });

  // UI status
  const [loading, setLoading] = useState({
    init: true,
    prediction: false,
    comparison: false,
    scenario: false,
  });
  const [error, setError] = useState(null);
  const [toast, setToast] = useState(null);

  const showToast = (message, type = "info") => {
    setToast({ message, type, id: Date.now() });
    setTimeout(() => setToast(null), 4000);
  };

  const clearError = () => setError(null);

  // Toggle API mode
  const handleConfigChange = (mockMode, newUrl) => {
    setUseMock(mockMode);
    setBaseUrl(newUrl);
    setApiConfig(mockMode, newUrl);
    showToast(
      mockMode
        ? "Switched to Built-in Mock Engine"
        : `Switched to Live REST API (${newUrl})`,
      "info",
    );
  };

  // 1. Initial Data Discovery
  useEffect(() => {
    let isMounted = true;
    async function initDiscovery() {
      try {
        setLoading((prev) => ({ ...prev, init: true }));
        const [dates, models, interventions] = await Promise.all([
          get_available_dates(),
          get_available_models(),
          get_available_interventions(),
        ]);

        if (isMounted) {
          setAvailableDates(dates);
          setAvailableModels(models);
          setInterventionsMeta(interventions);

          const defaultDate = dates.includes("2024-01-28")
            ? "2024-01-28"
            : dates[dates.length - 1];
          setSelectedDate(defaultDate);
        }
      } catch (err) {
        if (isMounted) {
          setError(`Initialization failed: ${err.message}`);
        }
      } finally {
        if (isMounted) setLoading((prev) => ({ ...prev, init: false }));
      }
    }
    initDiscovery();
    return () => {
      isMounted = false;
    };
  }, [useMock, baseUrl]);

  // 2. Cascading: When selectedDate changes, fetch available tiles
  useEffect(() => {
    let isMounted = true;
    if (!selectedDate) return;

    async function fetchTilesForDate() {
      try {
        const tiles = await get_available_tiles(selectedDate);
        if (isMounted) {
          setAvailableTiles(tiles);
          // Check if current tile is valid for this date
          const tileExists = tiles.some(
            (t) => Number(t.tile_id) === Number(selectedTileId),
          );
          if (!tileExists && tiles.length > 0) {
            setSelectedTileId(tiles[0].tile_id);
          }
        }
      } catch (err) {
        if (isMounted) {
          setError(err.message);
        }
      }
    }

    fetchTilesForDate();
    return () => {
      isMounted = false;
    };
  }, [selectedDate, useMock, baseUrl]);

  // 3. Fetch Single Prediction
  const fetchSinglePrediction = useCallback(
    async (
      model = selectedModel,
      date = selectedDate,
      tileId = selectedTileId,
    ) => {
      if (!model || !date || !tileId) return;
      try {
        setLoading((prev) => ({ ...prev, prediction: true }));
        setError(null);
        const res = await predict_for_date_tile(model, date, tileId);
        setSinglePrediction(res);
      } catch (err) {
        setError(err.message);
        setSinglePrediction(null);
      } finally {
        setLoading((prev) => ({ ...prev, prediction: false }));
      }
    },
    [selectedModel, selectedDate, selectedTileId, useMock, baseUrl],
  );

  // 4. Fetch Model Comparison
  const fetchModelComparison = useCallback(
    async (date = selectedDate, tileId = selectedTileId) => {
      if (!date || !tileId) return;
      try {
        setLoading((prev) => ({ ...prev, comparison: true }));
        setError(null);
        const res = await compare_models(date, tileId);
        setComparisonResult(res);
      } catch (err) {
        setError(err.message);
        setComparisonResult(null);
      } finally {
        setLoading((prev) => ({ ...prev, comparison: false }));
      }
    },
    [selectedDate, selectedTileId, useMock, baseUrl],
  );

  // 5. Fetch Scenario Simulation
  const fetchScenarioSimulation = useCallback(
    async (
      model = selectedModel,
      date = selectedDate,
      tileId = selectedTileId,
      scenario = scenarioInputs,
    ) => {
      if (!model || !date || !tileId) return;
      try {
        setLoading((prev) => ({ ...prev, scenario: true }));
        setError(null);
        const res = await predict_scenario_for_date_tile(
          model,
          date,
          tileId,
          scenario,
        );
        setScenarioResult(res);
      } catch (err) {
        setError(err.message);
        setScenarioResult(null);
      } finally {
        setLoading((prev) => ({ ...prev, scenario: false }));
      }
    },
    [
      selectedModel,
      selectedDate,
      selectedTileId,
      scenarioInputs,
      useMock,
      baseUrl,
    ],
  );

  // Automatically refresh prediction + comparison when primary context changes.
  // Scenario is NOT auto-triggered — it runs only when the user clicks "Run Simulation".
  useEffect(() => {
    if (selectedDate && selectedTileId && selectedModel) {
      fetchSinglePrediction(selectedModel, selectedDate, selectedTileId);
      fetchModelComparison(selectedDate, selectedTileId);
      fetchScenarioSimulation(selectedModel, selectedDate, selectedTileId, scenarioInputs);
    }
  }, [
    selectedDate,
    selectedTileId,
    selectedModel,
    fetchSinglePrediction,
    fetchModelComparison,
    fetchScenarioSimulation,
  ]);

  // Get active tile metadata object
  const activeTileMeta =
    availableTiles.find((t) => Number(t.tile_id) === Number(selectedTileId)) ||
    null;

  return (
    <ThermaMLContext.Provider
      value={{
        // Configuration
        useMock,
        baseUrl,
        handleConfigChange,

        // Selections
        availableDates,
        selectedDate,
        setSelectedDate,

        availableTiles,
        selectedTileId,
        setSelectedTileId,
        activeTileMeta,

        availableModels,
        selectedModel,
        setSelectedModel,

        interventionsMeta,

        // Results
        singlePrediction,
        comparisonResult,
        scenarioResult,

        // Scenario Simulator Controls
        scenarioInputs,
        setScenarioInputs,
        fetchScenarioSimulation,

        // Actions
        fetchSinglePrediction,
        fetchModelComparison,

        // UI States
        loading,
        error,
        clearError,
        toast,
        showToast,
      }}
    >
      {children}
    </ThermaMLContext.Provider>
  );
};

export const useThermaML = () => {
  const context = useContext(ThermaMLContext);
  if (!context) {
    throw new Error("useThermaML must be used within a ThermaMLProvider");
  }
  return context;
};
