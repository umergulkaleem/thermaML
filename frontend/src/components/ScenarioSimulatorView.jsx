import React, { useState } from 'react';
import { useThermaML } from '../context/ThermaMLContext';
import { 
  Sliders, 
  TreePine, 
  Building2, 
  Layers, 
  DollarSign, 
  AlertTriangle, 
  Sparkles, 
  RotateCcw, 
  TrendingDown
} from 'lucide-react';

export const ScenarioSimulatorView = () => {
  const {
    selectedModel,
    selectedDate,
    selectedTileId,
    scenarioInputs,
    setScenarioInputs,
    scenarioResult,
    fetchScenarioSimulation,
    loading
  } = useThermaML();

  const [activePreset, setActivePreset] = useState(null);

  // Helper for manual quantity inputs
  const handleInputChange = (field, value) => {
    setActivePreset(null);
    setScenarioInputs(prev => ({
      ...prev,
      [field]: value
    }));
  };

  // Helper for slider changes: scales quantities proportionally if user adjusts sliders
  const handleSliderChange = (field, val) => {
    setActivePreset(null);
    setScenarioInputs(prev => {
      const next = { ...prev, [field]: val };
      if (field === 'canopy_pct') {
        next.number_of_trees = val === 0 ? 0 : Math.round(val * 8);
      } else if (field === 'roof_pct') {
        next.roof_area_sqft = val === 0 ? 0 : Math.round(val * 800);
      } else if (field === 'pavement_pct') {
        next.paved_area_sqft = val === 0 ? 0 : Math.round(val * 1750);
      }
      return next;
    });
  };

  // Preset scenarios
  const applyPreset = (presetType) => {
    setActivePreset(presetType);
    let newInputs;
    switch (presetType) {
      case 'pocket_park':
        newInputs = {
          canopy_pct: 20,
          roof_pct: 0,
          pavement_pct: 10,
          number_of_trees: 160,
          roof_area_sqft: 0,
          paved_area_sqft: 15000,
        };
        break;
      case 'cool_roofs':
        newInputs = {
          canopy_pct: 5,
          roof_pct: 45,
          pavement_pct: 0,
          number_of_trees: 30,
          roof_area_sqft: 35000,
          paved_area_sqft: 0,
        };
        break;
      case 'district_resilience':
        newInputs = {
          canopy_pct: 25,
          roof_pct: 35,
          pavement_pct: 30,
          number_of_trees: 220,
          roof_area_sqft: 40000,
          paved_area_sqft: 50000,
        };
        break;
      case 'reset':
      default:
        setActivePreset(null);
        newInputs = {
          canopy_pct: 0,
          roof_pct: 0,
          pavement_pct: 0,
          number_of_trees: 0,
          roof_area_sqft: 0,
          paved_area_sqft: 0,
        };
        break;
    }
    setScenarioInputs(newInputs);
    fetchScenarioSimulation(selectedModel, selectedDate, selectedTileId, newInputs);
  };

  const baselineTemp = scenarioResult?.baseline_temperature_c ?? 39.4;
  const postTemp = scenarioResult?.post_intervention_temperature_c ?? 37.8;
  const totalCooling = scenarioResult?.total_ambient_cooling_c ?? 1.6;

  const baselineTempDisplay = typeof baselineTemp === 'number' ? baselineTemp.toFixed(3) : baselineTemp;
  const postTempDisplay = typeof postTemp === 'number' ? postTemp.toFixed(3) : postTemp;
  const totalCoolingDisplay = typeof totalCooling === 'number' ? totalCooling.toFixed(3) : totalCooling;

  const interventions = scenarioResult?.interventions || {};
  const canopyEffect = interventions.tree_canopy?.ambient_cooling_c ?? 0.68;
  const roofEffect = interventions.cool_roof?.ambient_cooling_c ?? 0.70;
  const pavementSurfaceEffect = interventions.cool_pavement?.surface_temp_reduction_c ?? 7.0;

  const canopyEffectDisplay = typeof canopyEffect === 'number' ? canopyEffect.toFixed(3) : canopyEffect;
  const roofEffectDisplay = typeof roofEffect === 'number' ? roofEffect.toFixed(3) : roofEffect;
  const pavementSurfaceEffectDisplay = typeof pavementSurfaceEffect === 'number' ? pavementSurfaceEffect.toFixed(3) : pavementSurfaceEffect;

  const costs = scenarioResult?.costs || {};

  // Live calculation of costs based on active inputs
  const parseNum = (val) => {
    if (val === null || val === undefined || val === '') return null;
    const num = Number(val);
    return isNaN(num) || num < 0 ? null : num;
  };

  const canopyPct = Number(scenarioInputs.canopy_pct || 0);
  const roofPct = Number(scenarioInputs.roof_pct || 0);
  const pavementPct = Number(scenarioInputs.pavement_pct || 0);

  const treeCount = parseNum(scenarioInputs.number_of_trees);
  const roofArea = parseNum(scenarioInputs.roof_area_sqft);
  const pavedArea = parseNum(scenarioInputs.paved_area_sqft);

  const currentTreeCost = canopyPct === 0
    ? 0
    : (treeCount !== null ? treeCount * 1088 : (costs.tree_canopy_usd ?? null));
  const currentRoofCost = roofPct === 0
    ? 0
    : (roofArea !== null ? roofArea * 1.15 : (costs.cool_roof_usd ?? null));
  const currentPavementCost = pavementPct === 0
    ? 0
    : (pavedArea !== null ? pavedArea * 3.0 : (costs.cool_pavement_usd ?? null));

  const hasAnyCost = currentTreeCost !== null || currentRoofCost !== null || currentPavementCost !== null;
  const currentTotalCost = hasAnyCost
    ? (currentTreeCost || 0) + (currentRoofCost || 0) + (currentPavementCost || 0)
    : null;

  const formatCost = (val) => {
    if (val === null || val === undefined) return <span className="cost-null-tag">N/A (quantities omitted)</span>;
    return `$${val.toLocaleString(undefined, { minimumFractionDigits: 0, maximumFractionDigits: 2 })}`;
  };

  return (
    <div className="simulator-layout tab-content-wrapper">
      {/* 1. Interactive Intervention Controls */}
      <div className="glass-panel sim-controls-card">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '18px' }}>
          <div className="meta-section-title" style={{ marginBottom: 0 }}>
            <Sliders size={18} color="#38bdf8" aria-hidden="true" />
            <span>Scenario Intervention Parameters</span>
          </div>
          <button 
            className="btn btn-ghost" 
            style={{ fontSize: '12px', padding: '6px 12px' }}
            onClick={() => applyPreset('reset')}
            title="Reset all interventions to 0"
            aria-label="Reset all sliders and inputs"
          >
            <RotateCcw size={13} aria-hidden="true" />
            <span>Reset</span>
          </button>
          <button
            className="btn btn-primary"
            style={{ fontSize: '12px', padding: '6px 14px' }}
            onClick={() => fetchScenarioSimulation(selectedModel, selectedDate, selectedTileId, scenarioInputs)}
            disabled={loading.scenario}
            aria-label="Run scenario simulation"
          >
            {loading.scenario ? 'Running...' : '▶ Run Simulation'}
          </button>
        </div>

        {/* Quick Presets */}
        <div className="preset-pills">
          <span style={{ fontSize: '12px', color: 'var(--text-muted)', alignSelf: 'center', marginRight: '4px' }}>
            Presets:
          </span>
          <button 
            className={`preset-btn ${activePreset === 'pocket_park' ? 'btn-primary' : ''}`}
            onClick={() => applyPreset('pocket_park')}
            style={activePreset === 'pocket_park' ? { background: 'linear-gradient(135deg, #0284c7 0%, #0369a1 100%)', color: '#fff', borderColor: '#38bdf8' } : {}}
          >
            🌳 Pocket Park (+20% Canopy)
          </button>
          <button 
            className={`preset-btn ${activePreset === 'cool_roofs' ? 'btn-primary' : ''}`}
            onClick={() => applyPreset('cool_roofs')}
            style={activePreset === 'cool_roofs' ? { background: 'linear-gradient(135deg, #0284c7 0%, #0369a1 100%)', color: '#fff', borderColor: '#38bdf8' } : {}}
          >
            🏢 Cool Roofs (+45% Albedo)
          </button>
          <button 
            className={`preset-btn ${activePreset === 'district_resilience' ? 'btn-primary' : ''}`}
            onClick={() => applyPreset('district_resilience')}
            style={activePreset === 'district_resilience' ? { background: 'linear-gradient(135deg, #0284c7 0%, #0369a1 100%)', color: '#fff', borderColor: '#38bdf8' } : {}}
          >
            🏙️ District Resilience (All 3)
          </button>
        </div>

        {/* Intervention 1: Tree Canopy */}
        <div className="intervention-group">
          <div className="intervention-header">
            <span style={{ display: 'flex', alignItems: 'center', gap: '8px', fontWeight: '700', color: '#34d399', fontSize: '13px' }}>
              <TreePine size={16} aria-hidden="true" />
              Tree Canopy Cover Expansion
            </span>
            <span className="badge badge-emerald">Ambient Air Cooling</span>
          </div>

          <div className="slider-container">
            <input
              type="range"
              min="0"
              max="100"
              step="1"
              value={scenarioInputs.canopy_pct}
              onChange={(e) => handleSliderChange('canopy_pct', Number(e.target.value))}
              aria-label="Tree Canopy Cover percentage"
            />
            <span className="slider-val-badge tabular-nums">+{scenarioInputs.canopy_pct}%</span>
          </div>

          <div className="quantity-input-row">
            <label htmlFor="input-trees">Number of Trees (for CapEx):</label>
            <input
              id="input-trees"
              type="number"
              min="0"
              placeholder="e.g. 150"
              className="form-input quantity-input tabular-nums"
              value={scenarioInputs.number_of_trees ?? ''}
              onChange={(e) => handleInputChange('number_of_trees', e.target.value === '' ? null : Number(e.target.value))}
            />
            <span style={{ fontSize: '11px', color: 'var(--text-muted)' }}>@ $1,088 / mature tree</span>
          </div>
        </div>

        {/* Intervention 2: Cool Roofs */}
        <div className="intervention-group">
          <div className="intervention-header">
            <span style={{ display: 'flex', alignItems: 'center', gap: '8px', fontWeight: '700', color: '#38bdf8', fontSize: '13px' }}>
              <Building2 size={16} aria-hidden="true" />
              High-Albedo Cool Roof Coating
            </span>
            <span className="badge badge-cyan">Ambient Air Cooling</span>
          </div>

          <div className="slider-container">
            <input
              type="range"
              min="0"
              max="100"
              step="1"
              value={scenarioInputs.roof_pct}
              onChange={(e) => handleSliderChange('roof_pct', Number(e.target.value))}
              aria-label="Cool Roof Coating percentage"
            />
            <span className="slider-val-badge tabular-nums" style={{ color: '#38bdf8', borderColor: 'rgba(56, 189, 248, 0.4)', background: 'rgba(56, 189, 248, 0.12)' }}>
              +{scenarioInputs.roof_pct}%
            </span>
          </div>

          <div className="quantity-input-row">
            <label htmlFor="input-roof-area">Roof Area sq ft (for CapEx):</label>
            <input
              id="input-roof-area"
              type="number"
              min="0"
              placeholder="e.g. 25000"
              className="form-input quantity-input tabular-nums"
              value={scenarioInputs.roof_area_sqft ?? ''}
              onChange={(e) => handleInputChange('roof_area_sqft', e.target.value === '' ? null : Number(e.target.value))}
            />
            <span style={{ fontSize: '11px', color: 'var(--text-muted)' }}>@ $1.15 / sqft</span>
          </div>
        </div>

        {/* Intervention 3: Cool Pavement */}
        <div className="intervention-group" style={{ borderColor: 'rgba(245, 158, 11, 0.3)' }}>
          <div className="intervention-header">
            <span style={{ display: 'flex', alignItems: 'center', gap: '8px', fontWeight: '700', color: '#fbbf24', fontSize: '13px' }}>
              <Layers size={16} aria-hidden="true" />
              Reflective Cool Pavement
            </span>
            <span className="badge badge-amber">Surface Temp Only</span>
          </div>

          <div className="slider-container">
            <input
              type="range"
              min="0"
              max="100"
              step="1"
              value={scenarioInputs.pavement_pct}
              onChange={(e) => handleSliderChange('pavement_pct', Number(e.target.value))}
              aria-label="Cool Pavement percentage"
            />
            <span className="slider-val-badge tabular-nums" style={{ color: '#fbbf24', borderColor: 'rgba(245, 158, 11, 0.4)', background: 'rgba(245, 158, 11, 0.12)' }}>
              +{scenarioInputs.pavement_pct}%
            </span>
          </div>

          <div className="quantity-input-row">
            <label htmlFor="input-pavement-area">Paved Area sq ft (for CapEx):</label>
            <input
              id="input-pavement-area"
              type="number"
              min="0"
              placeholder="e.g. 40000"
              className="form-input quantity-input tabular-nums"
              value={scenarioInputs.paved_area_sqft ?? ''}
              onChange={(e) => handleInputChange('paved_area_sqft', e.target.value === '' ? null : Number(e.target.value))}
            />
            <span style={{ fontSize: '11px', color: 'var(--text-muted)' }}>@ $3.00 / sqft</span>
          </div>
        </div>
      </div>

      {/* 2. Simulation Results & Financial CapEx Breakdown */}
      <div className="glass-panel sim-results-card">
        <div className="meta-section-title" style={{ marginBottom: 0 }}>
          <Sparkles size={18} color="#10b981" aria-hidden="true" />
          <span>Simulated Thermal Impact & CapEx</span>
        </div>

        {/* Thermal Differential Banner */}
        <div className="thermal-comparison-banner">
          <div className="temp-pillar">
            <h3>Predicted Baseline</h3>
            <div className="temp-val tabular-nums">{baselineTempDisplay}°C</div>
            <span style={{ fontSize: '11px', color: 'var(--text-muted)' }}>Tile #{selectedTileId}</span>
          </div>

          <div className="temp-diff-badge">
            <TrendingDown size={20} aria-hidden="true" />
            <span className="tabular-nums">-{totalCoolingDisplay}°C</span>
            <span style={{ fontSize: '10px', textTransform: 'uppercase', letterSpacing: '0.5px' }}>Air Cooling</span>
          </div>

          <div className="temp-pillar">
            <h3>Post-Intervention</h3>
            <div className="temp-val cooled tabular-nums">{postTempDisplay}°C</div>
            <span style={{ fontSize: '11px', color: '#34d399' }}>Simulated Ambient</span>
          </div>
        </div>

        {/* Breakdown of Cooling Channels */}
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '12px' }}>
          <div className="stat-box">
            <div className="stat-box-title" style={{ color: '#34d399' }}>Canopy Air Delta</div>
            <div className="stat-box-value tabular-nums" style={{ color: '#34d399' }}>-{canopyEffectDisplay}°C</div>
            <div className="stat-box-sub">Evapotranspiration</div>
          </div>

          <div className="stat-box">
            <div className="stat-box-title" style={{ color: '#38bdf8' }}>Cool Roof Delta</div>
            <div className="stat-box-value tabular-nums" style={{ color: '#38bdf8' }}>-{roofEffectDisplay}°C</div>
            <div className="stat-box-sub">Albedo reflection</div>
          </div>

          <div className="stat-box">
            <div className="stat-box-title" style={{ color: '#fbbf24' }}>Pavement Surface Delta</div>
            <div className="stat-box-value tabular-nums" style={{ color: '#fbbf24' }}>-{pavementSurfaceEffectDisplay}°C</div>
            <div className="stat-box-sub">Direct surface temp</div>
          </div>
        </div>

        {/* Physical Limitations Notice Banner */}
        <div className="physics-alert" role="alert">
          <AlertTriangle size={20} aria-hidden="true" />
          <div>
            <strong style={{ display: 'block', color: '#fbbf24', marginBottom: '3px' }}>
              Physical Constraint & Limitations Notice
            </strong>
            Tree canopy and cool-roof interventions reduce ambient air temperature. 
            <strong> Cool pavement reduces surface temperature range only</strong> and is strictly never subtracted from ambient air temperature per system physics.
          </div>
        </div>

        {/* Capital Expenditure (CapEx) Breakdown */}
        <div className="cost-breakdown-card">
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '13px', fontWeight: '700', marginBottom: '10px', color: 'var(--text-white)' }}>
            <DollarSign size={16} color="#34d399" aria-hidden="true" />
            <span>Estimated Intervention CapEx</span>
          </div>

          <div className="cost-row">
            <span style={{ color: 'var(--text-secondary)' }}>
              Tree Planting & Establishment ({treeCount !== null ? `${treeCount.toLocaleString()} trees` : 'quantity omitted'})
            </span>
            <span className="tabular-nums" style={{ fontFamily: 'var(--font-mono)' }}>{formatCost(currentTreeCost)}</span>
          </div>

          <div className="cost-row">
            <span style={{ color: 'var(--text-secondary)' }}>
              Cool Roof Coating ({roofArea !== null ? `${roofArea.toLocaleString()} sqft` : 'area omitted'} @ {scenarioInputs.roof_pct}%)
            </span>
            <span className="tabular-nums" style={{ fontFamily: 'var(--font-mono)' }}>{formatCost(currentRoofCost)}</span>
          </div>

          <div className="cost-row">
            <span style={{ color: 'var(--text-secondary)' }}>
              Cool Pavement Sealcoat ({pavedArea !== null ? `${pavedArea.toLocaleString()} sqft` : 'area omitted'} @ {scenarioInputs.pavement_pct}%)
            </span>
            <span className="tabular-nums" style={{ fontFamily: 'var(--font-mono)' }}>{formatCost(currentPavementCost)}</span>
          </div>

          <div className="cost-row">
            <span>Total Estimated Capital Investment</span>
            <span className="tabular-nums" style={{ fontFamily: 'var(--font-mono)', color: '#34d399', fontSize: '17px' }}>
              {formatCost(currentTotalCost)}
            </span>
          </div>
        </div>
      </div>
    </div>
  );
};
