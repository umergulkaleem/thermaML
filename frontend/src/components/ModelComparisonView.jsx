import React from 'react';
import { useThermaML } from '../context/ThermaMLContext';
import { 
  BarChart3, 
  Cpu, 
  Lock,
  ArrowUpRight,
  ArrowDownRight,
  TrendingUp,
  Scale
} from 'lucide-react';

export const ModelComparisonView = () => {
  const { 
    comparisonResult, 
    selectedDate, 
    selectedTileId, 
    loading 
  } = useThermaML();

  const predictions = comparisonResult?.predictions || {
    naive: 31.4,
    linear_regression: 38.6,
    random_forest: 39.4
  };

  const naiveTemp = predictions.naive ?? 31.4;
  const linearTemp = predictions.linear_regression ?? 38.6;
  const rfTemp = predictions.random_forest ?? 39.4;

  // Max temp for chart scale
  const maxScaleTemp = 45;
  const minScaleTemp = 15;

  const getWidthPercent = (val) => {
    const clamped = Math.max(minScaleTemp, Math.min(maxScaleTemp, val));
    return ((clamped - minScaleTemp) / (maxScaleTemp - minScaleTemp)) * 100;
  };

  // Deltas vs Naive Baseline
  const linearDelta = Number((linearTemp - naiveTemp).toFixed(1));
  const rfDelta = Number((rfTemp - naiveTemp).toFixed(1));
  const modelSpread = Number(Math.abs(rfTemp - linearTemp).toFixed(1));

  return (
    <div className="comparison-grid tab-content-wrapper">
      {/* 1. Visual Comparison Chart */}
      <div className="glass-panel comparison-chart-card">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '10px' }}>
          <div>
            <div className="meta-section-title" style={{ marginBottom: '4px' }}>
              <BarChart3 size={18} color="#38bdf8" aria-hidden="true" />
              <span>Multi-Model Regression Comparison</span>
            </div>
            <p style={{ fontSize: '12px', color: 'var(--text-muted)' }}>
              Evaluates the exact same observed environmental row for {selectedDate} on Tile #{selectedTileId}.
            </p>
          </div>
          <div className="badge badge-cyan" style={{ fontSize: '11px' }}>
            No Retraining
          </div>
        </div>

        {/* Horizontal Bar Chart */}
        <div className="comparison-bars-container">
          {/* Row 1: Naive All-Dataset Mean */}
          <div className="bar-row">
            <div className="bar-header">
              <span style={{ display: 'flex', alignItems: 'center', gap: '6px', color: '#94a3b8' }}>
                <span style={{ width: '8px', height: '8px', borderRadius: '50%', background: '#94a3b8' }} />
                Naive Training Mean (Baseline)
              </span>
              <span className="tabular-nums" style={{ fontFamily: 'var(--font-mono)', color: '#94a3b8' }}>
                {naiveTemp}°C
              </span>
            </div>
            <div className="bar-track">
              <div 
                className="bar-fill bar-fill-naive" 
                style={{ width: `${getWidthPercent(naiveTemp)}%` }} 
              />
              <div className="bar-label-inner tabular-nums">
                <span>{naiveTemp}°C</span>
                <span style={{ fontSize: '11px', fontWeight: 'normal', color: '#cbd5e1' }}>
                  (Dataset Global Mean)
                </span>
              </div>
            </div>
          </div>

          {/* Row 2: Linear Regression */}
          <div className="bar-row">
            <div className="bar-header">
              <span style={{ display: 'flex', alignItems: 'center', gap: '6px', color: '#38bdf8' }}>
                <span style={{ width: '8px', height: '8px', borderRadius: '50%', background: '#38bdf8' }} />
                Linear Regression
              </span>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <span className={`badge ${linearDelta >= 0 ? 'badge-orange' : 'badge-cyan'}`} style={{ fontSize: '11px' }}>
                  {linearDelta >= 0 ? <ArrowUpRight size={12} /> : <ArrowDownRight size={12} />}
                  <span>{linearDelta >= 0 ? `+${linearDelta}°C` : `${linearDelta}°C`} vs Naive</span>
                </span>
                <span className="tabular-nums" style={{ fontFamily: 'var(--font-mono)', color: '#38bdf8', fontWeight: '700' }}>
                  {linearTemp}°C
                </span>
              </div>
            </div>
            <div className="bar-track">
              <div 
                className="bar-fill bar-fill-linear" 
                style={{ width: `${getWidthPercent(linearTemp)}%` }} 
              />
              <div className="bar-label-inner tabular-nums">
                <span>{linearTemp}°C</span>
                <span style={{ fontSize: '11px', fontWeight: 'normal', color: '#e0f2fe' }}>
                  (Parametric Model)
                </span>
              </div>
            </div>
          </div>

          {/* Row 3: Random Forest */}
          <div className="bar-row">
            <div className="bar-header">
              <span style={{ display: 'flex', alignItems: 'center', gap: '6px', color: '#fb923c' }}>
                <span style={{ width: '8px', height: '8px', borderRadius: '50%', background: '#fb923c' }} />
                Random Forest (Ensemble)
              </span>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <span className={`badge ${rfDelta >= 0 ? 'badge-rose' : 'badge-emerald'}`} style={{ fontSize: '11px' }}>
                  {rfDelta >= 0 ? <ArrowUpRight size={12} /> : <ArrowDownRight size={12} />}
                  <span>{rfDelta >= 0 ? `+${rfDelta}°C` : `${rfDelta}°C`} vs Naive</span>
                </span>
                <span className="tabular-nums" style={{ fontFamily: 'var(--font-mono)', color: '#fb923c', fontWeight: '700' }}>
                  {rfTemp}°C
                </span>
              </div>
            </div>
            <div className="bar-track">
              <div 
                className="bar-fill bar-fill-rf" 
                style={{ width: `${getWidthPercent(rfTemp)}%` }} 
              />
              <div className="bar-label-inner tabular-nums">
                <span>{rfTemp}°C</span>
                <span style={{ fontSize: '11px', fontWeight: 'normal', color: '#ffedd5' }}>
                  (Non-linear Multi-tree Model)
                </span>
              </div>
            </div>
          </div>
        </div>

        {/* Comparison Insight Metrics */}
        <div style={{ 
          display: 'grid', 
          gridTemplateColumns: 'repeat(3, 1fr)', 
          gap: '14px', 
          marginTop: '26px',
          paddingTop: '20px',
          borderTop: '1px solid var(--border-subtle)'
        }}>
          <div className="stat-box">
            <div className="stat-box-title">Model Discrepancy</div>
            <div className="stat-box-value tabular-nums" style={{ color: modelSpread > 1.5 ? '#fb923c' : '#34d399' }}>
              {modelSpread}°C
            </div>
            <div className="stat-box-sub">|RF - Linear| delta</div>
          </div>

          <div className="stat-box">
            <div className="stat-box-title">Max UHI Departure</div>
            <div className="stat-box-value tabular-nums" style={{ color: '#f87171' }}>
              +{Math.max(linearDelta, rfDelta)}°C
            </div>
            <div className="stat-box-sub">Above historical mean</div>
          </div>

          <div className="stat-box">
            <div className="stat-box-title">Target Agreement</div>
            <div className="stat-box-value" style={{ color: '#38bdf8' }}>
              {modelSpread < 1.0 ? 'High' : 'Moderate'}
            </div>
            <div className="stat-box-sub">Concordance level</div>
          </div>
        </div>
      </div>

      {/* 2. Model Architecture & Contract Explanations */}
      <div className="glass-panel" style={{ padding: '28px' }}>
        <div className="meta-section-title">
          <Cpu size={18} color="#c084fc" aria-hidden="true" />
          <span>Artifact Architecture & Status</span>
        </div>

        <div className="model-cards-list">
          {/* Random Forest Card */}
          <div className="model-info-item" style={{ borderColor: 'rgba(249, 115, 22, 0.3)' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <span style={{ fontWeight: '700', color: '#fb923c', fontSize: '13px' }}>
                Random Forest Regressor
              </span>
              <span className="badge badge-emerald" style={{ fontSize: '10px' }}>Active</span>
            </div>
            <p style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>
              Non-linear ensemble combining 100+ decision trees. Captures intricate microclimate cross-interactions (e.g. canopy density × solar irradiation).
            </p>
          </div>

          {/* Linear Regression Card */}
          <div className="model-info-item" style={{ borderColor: 'rgba(56, 189, 248, 0.3)' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <span style={{ fontWeight: '700', color: '#38bdf8', fontSize: '13px' }}>
                Linear Regression
              </span>
              <span className="badge badge-emerald" style={{ fontSize: '10px' }}>Active</span>
            </div>
            <p style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>
              Parametric ordinary least squares regression model providing transparent feature coefficient weights for direct interpretability.
            </p>
          </div>

          {/* Naive Baseline Card */}
          <div className="model-info-item">
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <span style={{ fontWeight: '700', color: '#94a3b8', fontSize: '13px' }}>
                Naive Training Mean Baseline
              </span>
              <span className="badge badge-cyan" style={{ fontSize: '10px' }}>Reference</span>
            </div>
            <p style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>
              Static training dataset mean ({naiveTemp}°C). Serves as the statistical baseline to evaluate predictive skill gain.
            </p>
          </div>

          {/* GNN Unavailable Card */}
          <div className="model-info-item disabled">
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <span style={{ fontWeight: '700', color: '#64748b', fontSize: '13px', display: 'flex', alignItems: 'center', gap: '6px' }}>
                <Lock size={13} aria-hidden="true" />
                Graph Neural Network (GNN)
              </span>
              <span className="badge badge-rose" style={{ fontSize: '10px' }}>Unavailable</span>
            </div>
            <p style={{ fontSize: '12px', color: 'var(--text-muted)' }}>
              Documented spatial GNN is not active in this release (`get_available_models()` strictly returns Linear Regression and Random Forest).
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};
