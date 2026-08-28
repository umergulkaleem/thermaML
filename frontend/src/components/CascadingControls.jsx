import React from 'react';
import { useThermaML } from '../context/ThermaMLContext';
import { 
  Calendar, 
  MapPin, 
  Cpu, 
  ChevronLeft, 
  ChevronRight, 
  Shuffle, 
  Sparkles,
  Loader2
} from 'lucide-react';

export const CascadingControls = () => {
  const {
    availableDates,
    selectedDate,
    setSelectedDate,
    availableTiles,
    selectedTileId,
    setSelectedTileId,
    selectedModel,
    setSelectedModel,
    loading,
    showToast
  } = useThermaML();

  // Helper to format date with season tag
  const formatDateLabel = (dateStr) => {
    if (!dateStr) return '';
    const parts = dateStr.split('-');
    const month = parseInt(parts[1], 10);
    let season = '';
    if (month >= 6 && month <= 8) season = '🔥 Summer';
    else if (month >= 9 && month <= 11) season = '🍂 Autumn';
    else if (month === 12 || month <= 2) season = '❄️ Winter';
    else season = '🌱 Spring';
    return `${dateStr} (${season})`;
  };

  // Step through dates
  const currentIndex = availableDates.indexOf(selectedDate);
  const handlePrevDate = () => {
    if (currentIndex > 0) {
      setSelectedDate(availableDates[currentIndex - 1]);
    }
  };

  const handleNextDate = () => {
    if (currentIndex < availableDates.length - 1) {
      setSelectedDate(availableDates[currentIndex + 1]);
    }
  };

  // Pick a random valid date and tile
  const handleRandomSample = () => {
    if (availableDates.length === 0) return;
    const randomDate = availableDates[Math.floor(Math.random() * availableDates.length)];
    setSelectedDate(randomDate);
    showToast(`Sampled date: ${randomDate}`, 'info');
  };

  return (
    <section className="glass-panel controls-bar" aria-label="Dataset Query Controls">
      {/* 1. Strictly Cascading Date Selector */}
      <div className="control-group">
        <label className="control-label" htmlFor="select-date">
          <span>Observation Date</span>
          <span className="control-label-info">{availableDates.length} Exact Dates</span>
        </label>
        <div className="control-input-wrapper">
          <Calendar className="input-icon" aria-hidden="true" />
          <select 
            id="select-date"
            className="form-select"
            value={selectedDate}
            onChange={(e) => setSelectedDate(e.target.value)}
            disabled={loading.init || availableDates.length === 0}
            aria-label="Select observation date"
          >
            {availableDates.map(date => (
              <option key={date} value={date}>
                {formatDateLabel(date)}
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* Date Stepper Helpers */}
      <div className="control-group" style={{ maxWidth: '90px' }}>
        <div className="control-label">
          <span>Step</span>
        </div>
        <div className="date-step-btns">
          <button 
            className="btn btn-outline" 
            style={{ padding: '8px 10px', width: '40px', minHeight: '42px' }}
            onClick={handlePrevDate}
            disabled={currentIndex <= 0}
            title="Previous observed date"
            aria-label="Previous date"
          >
            <ChevronLeft size={16} />
          </button>
          <button 
            className="btn btn-outline" 
            style={{ padding: '8px 10px', width: '40px', minHeight: '42px' }}
            onClick={handleNextDate}
            disabled={currentIndex >= availableDates.length - 1}
            title="Next observed date"
            aria-label="Next date"
          >
            <ChevronRight size={16} />
          </button>
        </div>
      </div>

      {/* 2. Strictly Filtered Observed Tiles Selector */}
      <div className="control-group">
        <label className="control-label" htmlFor="select-tile">
          <span style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
            Observed Tile
            {loading.prediction && <Loader2 size={11} className="animate-spin" style={{ animation: 'spin 1s linear infinite' }} />}
          </span>
          <span className="control-label-info">{availableTiles.length} Observed</span>
        </label>
        <div className="control-input-wrapper">
          <MapPin className="input-icon" aria-hidden="true" />
          <select 
            id="select-tile"
            className="form-select"
            value={selectedTileId}
            onChange={(e) => setSelectedTileId(Number(e.target.value))}
            disabled={loading.init || availableTiles.length === 0}
            aria-label="Select observed tile"
          >
            {availableTiles.map(tile => (
              <option key={tile.tile_id} value={tile.tile_id}>
                Tile #{tile.tile_id} - {tile.name || `Region ${tile.tile_id}`}
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* 3. Available Models Selector */}
      <div className="control-group">
        <label className="control-label" htmlFor="select-model">
          <span>Regression Model</span>
          <span className="control-label-info">Active Artifact</span>
        </label>
        <div className="control-input-wrapper">
          <Cpu className="input-icon" aria-hidden="true" />
          <select 
            id="select-model"
            className="form-select"
            value={selectedModel}
            onChange={(e) => setSelectedModel(e.target.value)}
            aria-label="Select ML regression model"
          >
            <option value="random_forest">Random Forest (Ensemble)</option>
            <option value="linear_regression">Linear Regression (Parametric)</option>
          </select>
        </div>
      </div>

      {/* Quick Action Controls */}
      <div className="quick-actions">
        <button 
          className="btn btn-outline" 
          onClick={handleRandomSample}
          title="Pick a random valid observation date"
          aria-label="Random date sample"
          style={{ minHeight: '42px' }}
        >
          <Shuffle size={14} aria-hidden="true" />
          <span>Random</span>
        </button>
      </div>
    </section>
  );
};
