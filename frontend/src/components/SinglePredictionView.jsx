import React from 'react';
import { useThermaML } from '../context/ThermaMLContext';
import { 
  Thermometer, 
  Flame, 
  MapPin, 
  Layers, 
  AlertTriangle, 
  CheckCircle, 
  ArrowRight,
  Activity,
  Compass
} from 'lucide-react';

export const SinglePredictionView = ({ onNavigateToSimulator }) => {
  const { 
    singlePrediction, 
    selectedModel, 
    selectedTileId, 
    activeTileMeta, 
    loading 
  } = useThermaML();

  const tempC = singlePrediction?.predicted_temperature_c ?? 31.4;
  const tempF = Number(((tempC * 9/5) + 32).toFixed(1));

  // Determine heat classification
  const getHeatClassification = (temp) => {
    if (temp >= 40.0) {
      return {
        label: 'Extreme Heat Emergency',
        color: '#ef4444',
        badgeClass: 'badge-rose',
        glowColor: 'rgba(239, 68, 68, 0.4)',
        icon: Flame,
        description: 'Dangerous thermal threshold with severe heat stress for vulnerable populations.'
      };
    }
    if (temp >= 35.0) {
      return {
        label: 'High Urban Heat Stress',
        color: '#f97316',
        badgeClass: 'badge-orange',
        glowColor: 'rgba(249, 115, 22, 0.38)',
        icon: AlertTriangle,
        description: 'Significant urban heat island amplification observed across impervious surfaces.'
      };
    }
    if (temp >= 30.0) {
      return {
        label: 'Elevated Heat Load',
        color: '#f59e0b',
        badgeClass: 'badge-amber',
        glowColor: 'rgba(245, 158, 11, 0.35)',
        icon: Activity,
        description: 'Typical warm conditions; shading and vegetative cover recommended.'
      };
    }
    if (temp >= 24.0) {
      return {
        label: 'Moderate Thermal State',
        color: '#10b981',
        badgeClass: 'badge-emerald',
        glowColor: 'rgba(16, 185, 129, 0.35)',
        icon: CheckCircle,
        description: 'Comfortable thermal range within safe municipal parameters.'
      };
    }
    return {
      label: 'Cool / Temperate',
      color: '#06b6d4',
      badgeClass: 'badge-cyan',
      glowColor: 'rgba(6, 182, 212, 0.35)',
      icon: Thermometer,
      description: 'Cool conditions with minimal solar heat retention.'
    };
  };

  const heatInfo = getHeatClassification(tempC);
  const HeatIcon = heatInfo.icon;

  // Circular gauge math (from 10°C to 45°C, spanning 240 degrees)
  const minTemp = 10;
  const maxTemp = 45;
  const clampedTemp = Math.max(minTemp, Math.min(maxTemp, tempC));
  const tempRatio = (clampedTemp - minTemp) / (maxTemp - minTemp);
  const totalAngle = 240;
  const startAngle = 150; // starts bottom-left

  const radius = 92;
  const cx = 135;
  const cy = 135;
  const circumference = 2 * Math.PI * radius;
  const arcLength = (totalAngle / 360) * circumference;
  const strokeDashoffset = arcLength * (1 - tempRatio);

  return (
    <div className="single-prediction-grid tab-content-wrapper">
      {/* 1. Interactive Thermal Gauge Card */}
      <div className="glass-panel gauge-card" style={{ '--glow-color': heatInfo.glowColor }}>
        <div style={{ position: 'relative', width: '270px', height: '270px' }}>
          <svg className="thermal-gauge-svg" viewBox="0 0 270 270" aria-hidden="true">
            <defs>
              <linearGradient id="thermalArcGrad" x1="0%" y1="0%" x2="100%" y2="100%">
                <stop offset="0%" stopColor="#06b6d4" />
                <stop offset="35%" stopColor="#10b981" />
                <stop offset="65%" stopColor="#f59e0b" />
                <stop offset="100%" stopColor="#ef4444" />
              </linearGradient>
            </defs>

            {/* Background Track */}
            <circle
              cx={cx}
              cy={cy}
              r={radius}
              fill="none"
              stroke="rgba(255, 255, 255, 0.08)"
              strokeWidth="15"
              strokeDasharray={`${arcLength} ${circumference}`}
              strokeDashoffset="0"
              transform={`rotate(${startAngle} ${cx} ${cy})`}
              strokeLinecap="round"
            />

            {/* Active Temperature Arc */}
            <circle
              cx={cx}
              cy={cy}
              r={radius}
              fill="none"
              stroke="url(#thermalArcGrad)"
              strokeWidth="15"
              strokeDasharray={`${arcLength} ${circumference}`}
              strokeDashoffset={loading.prediction ? arcLength : strokeDashoffset}
              transform={`rotate(${startAngle} ${cx} ${cy})`}
              strokeLinecap="round"
              style={{ transition: 'stroke-dashoffset 0.8s cubic-bezier(0.16, 1, 0.3, 1)' }}
            />

            {/* Tick Markers */}
            <text x="50" y="235" fill="#94a3b8" fontSize="12" fontFamily="var(--font-mono)">10°C</text>
            <text x="135" y="36" fill="#94a3b8" fontSize="12" textAnchor="middle" fontFamily="var(--font-mono)">27.5°C</text>
            <text x="220" y="235" fill="#94a3b8" fontSize="12" textAnchor="end" fontFamily="var(--font-mono)">45°C</text>
          </svg>

          {/* Central Readout */}
          <div className="gauge-readout" style={{ inset: 0 }}>
            <span style={{ fontSize: '11px', textTransform: 'uppercase', letterSpacing: '1px', color: 'var(--text-muted)' }}>
              Predicted Daily Temp
            </span>
            <div style={{ display: 'flex', alignItems: 'baseline', marginTop: '4px' }}>
              {loading.prediction ? (
                <div className="skeleton-box" style={{ width: '100px', height: '52px', margin: '4px auto' }} />
              ) : (
                <>
                  <span className="gauge-temp-value tabular-nums">{tempC}</span>
                  <span className="gauge-temp-unit">°C</span>
                </>
              )}
            </div>
            <span className="gauge-temp-secondary tabular-nums">
              {loading.prediction ? 'Calculating...' : `${tempF}°F`}
            </span>
          </div>
        </div>

        {/* Severity Classification Badge */}
        <div className="gauge-badge-wrapper">
          <div className={`badge ${heatInfo.badgeClass}`} style={{ fontSize: '13px', padding: '6px 16px' }}>
            <HeatIcon size={16} aria-hidden="true" />
            <span>{heatInfo.label}</span>
          </div>
          <p style={{ fontSize: '12px', color: 'var(--text-muted)', marginTop: '10px', maxWidth: '320px' }}>
            {heatInfo.description}
          </p>
        </div>
      </div>

      {/* 2. Metadata & Environmental Diagnostics Card */}
      <div className="glass-panel prediction-meta-card">
        <div>
          <div className="meta-section-title">
            <Layers size={18} color="#38bdf8" aria-hidden="true" />
            <span>Tile & Prediction Metadata</span>
          </div>

          <div className="meta-stats-grid">
            <div className="stat-box">
              <div className="stat-box-title">Observation Target</div>
              <div className="stat-box-value" style={{ color: '#38bdf8' }}>
                {singlePrediction?.target || 'daily_temperature'}
              </div>
              <div className="stat-box-sub">Regression metric (°C)</div>
            </div>

            <div className="stat-box">
              <div className="stat-box-title">Feature Version</div>
              <div className="stat-box-value" style={{ color: '#c084fc' }}>
                {singlePrediction?.feature_version || 'daily-temperature-v1'}
              </div>
              <div className="stat-box-sub">Model feature pipeline</div>
            </div>

            <div className="stat-box">
              <div className="stat-box-title">Active Model</div>
              <div className="stat-box-value" style={{ textTransform: 'capitalize', color: '#fb923c' }}>
                {selectedModel.replace('_', ' ')}
              </div>
              <div className="stat-box-sub">Scored on observed row</div>
            </div>

            <div className="stat-box">
              <div className="stat-box-title">Geographic Tile</div>
              <div className="stat-box-value">
                Tile #{selectedTileId}
              </div>
              <div className="stat-box-sub">{activeTileMeta?.name || 'Urban Sector'}</div>
            </div>
          </div>
        </div>

        {/* Environmental Baseline Attributes */}
        <div style={{ marginTop: '16px' }}>
          <div className="meta-section-title">
            <MapPin size={18} color="#10b981" aria-hidden="true" />
            <span>Tile Environmental Baseline</span>
          </div>

          <div className="meta-stats-grid">
            <div className="stat-box">
              <div className="stat-box-title">Urban Density</div>
              <div className="stat-box-value tabular-nums">
                {activeTileMeta ? `${Math.round(activeTileMeta.urbanDensity * 100)}%` : '75%'}
              </div>
              <div className="stat-box-sub">Impervious surface index</div>
            </div>

            <div className="stat-box">
              <div className="stat-box-title">Existing Tree Canopy</div>
              <div className="stat-box-value tabular-nums" style={{ color: '#34d399' }}>
                {activeTileMeta?.baseCanopy ? `${activeTileMeta.baseCanopy}%` : '12.0%'}
              </div>
              <div className="stat-box-sub">Vegetative shade cover</div>
            </div>

            <div className="stat-box">
              <div className="stat-box-title">Roof Coverage</div>
              <div className="stat-box-value tabular-nums">
                {activeTileMeta?.baseRoof ? `${activeTileMeta.baseRoof}%` : '42.0%'}
              </div>
              <div className="stat-box-sub">Standard albedo surface</div>
            </div>

            <div className="stat-box">
              <div className="stat-box-title">Elevation</div>
              <div className="stat-box-value tabular-nums">
                {activeTileMeta?.elevationM ? `${activeTileMeta.elevationM} m` : '50 m'}
              </div>
              <div className="stat-box-sub">Lapse rate adjusted</div>
            </div>
          </div>
        </div>

        {/* Quick CTA to Simulator */}
        <div style={{ 
          marginTop: '14px',
          padding: '16px 20px', 
          background: 'rgba(56, 189, 248, 0.08)', 
          border: '1px solid rgba(56, 189, 248, 0.25)',
          borderRadius: 'var(--radius-sm)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          gap: '12px',
          flexWrap: 'wrap'
        }}>
          <div>
            <div style={{ fontSize: '13px', fontWeight: '700', color: 'var(--text-white)' }}>
              Simulate Cooling Interventions
            </div>
            <div style={{ fontSize: '12px', color: 'var(--text-muted)' }}>
              Apply canopy expansion and cool roof retrofits to this tile.
            </div>
          </div>
          <button 
            className="btn btn-primary" 
            style={{ padding: '8px 16px', fontSize: '13px' }}
            onClick={onNavigateToSimulator}
          >
            <span>Open Simulator</span>
            <ArrowRight size={14} aria-hidden="true" />
          </button>
        </div>
      </div>
    </div>
  );
};
