import React, { useState } from 'react';
import { useThermaML } from '../context/ThermaMLContext';
import { 
  Code2, 
  Copy, 
  Check, 
  AlertOctagon, 
  Sparkles
} from 'lucide-react';
import { predict_for_date_tile } from '../services/api';

export const ApiContractExplorer = () => {
  const { 
    singlePrediction, 
    comparisonResult, 
    scenarioResult, 
    availableDates, 
    availableTiles, 
    selectedDate, 
    selectedTileId,
    showToast
  } = useThermaML();

  const [activeEndpoint, setActiveEndpoint] = useState('predict');
  const [copied, setCopied] = useState(false);
  const [customErrorOutput, setCustomErrorOutput] = useState(null);

  // Determine current active payload
  let currentPayload = {};
  if (activeEndpoint === 'predict') currentPayload = singlePrediction;
  else if (activeEndpoint === 'compare') currentPayload = comparisonResult;
  else if (activeEndpoint === 'scenario') currentPayload = scenarioResult;
  else if (activeEndpoint === 'dates') currentPayload = { count: availableDates.length, dates: availableDates };
  else if (activeEndpoint === 'tiles') currentPayload = { date: selectedDate, observed_tiles: availableTiles };

  const handleCopyJson = () => {
    navigator.clipboard.writeText(JSON.stringify(customErrorOutput || currentPayload, null, 2));
    setCopied(true);
    showToast('JSON payload copied to clipboard', 'info');
    setTimeout(() => setCopied(false), 2000);
  };

  // Test error handling by requesting invalid model (GNN)
  const handleTestGnnError = async () => {
    try {
      setCustomErrorOutput(null);
      await predict_for_date_tile('gnn', selectedDate, selectedTileId);
    } catch (err) {
      setCustomErrorOutput({
        status: 'error_caught',
        exception_type: 'ValueError',
        message: err.message
      });
      showToast('Successfully caught and handled ValueError exception', 'info');
    }
  };

  // Test invalid date
  const handleTestInvalidDate = async () => {
    try {
      setCustomErrorOutput(null);
      await predict_for_date_tile('random_forest', '2025-09-99', selectedTileId);
    } catch (err) {
      setCustomErrorOutput({
        status: 'error_caught',
        exception_type: 'ValueError',
        message: err.message
      });
      showToast('Successfully caught invalid date error', 'info');
    }
  };

  return (
    <div className="glass-panel api-explorer-card tab-content-wrapper">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px', flexWrap: 'wrap', gap: '12px' }}>
        <div>
          <div className="meta-section-title" style={{ marginBottom: '4px' }}>
            <Code2 size={18} color="#38bdf8" aria-hidden="true" />
            <span>API Contract & Schema Explorer</span>
          </div>
          <p style={{ fontSize: '12px', color: 'var(--text-muted)' }}>
            Inspect live JSON payloads conforming to specifications defined in <code>frontend_contract.md</code>.
          </p>
        </div>

        <button 
          className="btn btn-outline" 
          onClick={handleCopyJson} 
          style={{ fontSize: '12px', minHeight: '38px' }}
          aria-label="Copy JSON payload to clipboard"
        >
          {copied ? <Check size={14} color="#34d399" aria-hidden="true" /> : <Copy size={14} aria-hidden="true" />}
          <span>{copied ? 'Copied to Clipboard' : 'Copy JSON'}</span>
        </button>
      </div>

      {/* Endpoint Selector Tabs */}
      <div style={{ display: 'flex', gap: '8px', marginBottom: '16px', flexWrap: 'wrap' }} role="tablist" aria-label="API Contract Endpoints">
        <button 
          className={`btn ${activeEndpoint === 'predict' ? 'btn-primary' : 'btn-outline'}`}
          style={{ fontSize: '12px', padding: '6px 14px', minHeight: '38px' }}
          onClick={() => { setActiveEndpoint('predict'); setCustomErrorOutput(null); }}
          role="tab"
          aria-selected={activeEndpoint === 'predict'}
        >
          predict_for_date_tile()
        </button>

        <button 
          className={`btn ${activeEndpoint === 'compare' ? 'btn-primary' : 'btn-outline'}`}
          style={{ fontSize: '12px', padding: '6px 14px', minHeight: '38px' }}
          onClick={() => { setActiveEndpoint('compare'); setCustomErrorOutput(null); }}
          role="tab"
          aria-selected={activeEndpoint === 'compare'}
        >
          compare_models()
        </button>

        <button 
          className={`btn ${activeEndpoint === 'scenario' ? 'btn-primary' : 'btn-outline'}`}
          style={{ fontSize: '12px', padding: '6px 14px', minHeight: '38px' }}
          onClick={() => { setActiveEndpoint('scenario'); setCustomErrorOutput(null); }}
          role="tab"
          aria-selected={activeEndpoint === 'scenario'}
        >
          predict_scenario_for_date_tile()
        </button>

        <button 
          className={`btn ${activeEndpoint === 'dates' ? 'btn-primary' : 'btn-outline'}`}
          style={{ fontSize: '12px', padding: '6px 14px', minHeight: '38px' }}
          onClick={() => { setActiveEndpoint('dates'); setCustomErrorOutput(null); }}
          role="tab"
          aria-selected={activeEndpoint === 'dates'}
        >
          get_available_dates()
        </button>

        <button 
          className={`btn ${activeEndpoint === 'tiles' ? 'btn-primary' : 'btn-outline'}`}
          style={{ fontSize: '12px', padding: '6px 14px', minHeight: '38px' }}
          onClick={() => { setActiveEndpoint('tiles'); setCustomErrorOutput(null); }}
          role="tab"
          aria-selected={activeEndpoint === 'tiles'}
        >
          get_available_tiles()
        </button>
      </div>

      {/* Code Viewer */}
      <pre className="json-code-block" tabIndex={0} aria-label="JSON Response Preview">
        <code>{JSON.stringify(customErrorOutput || currentPayload, null, 2)}</code>
      </pre>

      {/* Edge Case Exception Testing Panel */}
      <div style={{ 
        marginTop: '22px', 
        paddingTop: '18px', 
        borderTop: '1px solid var(--border-subtle)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        flexWrap: 'wrap',
        gap: '12px'
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <AlertOctagon size={16} color="#fbbf24" aria-hidden="true" />
          <span style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>
            Exception Testing (Contract ValueError Verification):
          </span>
        </div>

        <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
          <button 
            className="btn btn-outline"
            style={{ fontSize: '11px', padding: '6px 12px', color: '#f87171', minHeight: '36px' }}
            onClick={handleTestGnnError}
            aria-label="Test GNN model unavailable error"
          >
            Test GNN Unavailable Error
          </button>

          <button 
            className="btn btn-outline"
            style={{ fontSize: '11px', padding: '6px 12px', color: '#fb923c', minHeight: '36px' }}
            onClick={handleTestInvalidDate}
            aria-label="Test out-of-bounds date error"
          >
            Test Out-of-Bounds Date
          </button>
        </div>
      </div>
    </div>
  );
};
