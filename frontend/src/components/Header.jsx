import React, { useState } from 'react';
import { useThermaML } from '../context/ThermaMLContext';
import { 
  Flame, 
  Activity, 
  Layers, 
  Settings, 
  Server, 
  CheckCircle2, 
  Globe, 
  Database,
  X
} from 'lucide-react';

export const Header = () => {
  const { useMock, baseUrl, handleConfigChange } = useThermaML();
  const [showConfigModal, setShowConfigModal] = useState(false);
  const [tempMock, setTempMock] = useState(useMock);
  const [tempUrl, setTempUrl] = useState(baseUrl);

  const handleSaveConfig = (e) => {
    e.preventDefault();
    handleConfigChange(tempMock, tempUrl);
    setShowConfigModal(false);
  };

  return (
    <header className="header-wrapper" role="banner">
      <div className="header-container">
        {/* Brand & Identity */}
        <div className="header-brand">
          <div className="brand-icon-wrapper" aria-hidden="true">
            <Flame size={24} />
          </div>
          <div className="brand-titles">
            <h1>
              ThermaML
              <span className="badge badge-orange" style={{ fontSize: '10px', padding: '2px 8px' }}>
                REGRESSION
              </span>
            </h1>
            <p>Urban Heat Regression & Climate Resilience System</p>
          </div>
        </div>

        {/* System Metadata Tags */}
        <div className="header-meta-tags">
          <div className="badge badge-cyan" title="Regression Target Variable">
            <Activity size={13} aria-hidden="true" />
            <span>Target: daily_temperature</span>
          </div>

          <div className="badge badge-purple" title="Input Feature Version">
            <Layers size={13} aria-hidden="true" />
            <span>daily-temperature-v1</span>
          </div>

          <div 
            className={`badge ${useMock ? 'badge-emerald' : 'badge-amber'}`} 
            style={{ cursor: 'pointer' }}
            onClick={() => {
              setTempMock(useMock);
              setTempUrl(baseUrl);
              setShowConfigModal(true);
            }}
            role="button"
            tabIndex={0}
            onKeyDown={(e) => {
              if (e.key === 'Enter' || e.key === ' ') {
                setTempMock(useMock);
                setTempUrl(baseUrl);
                setShowConfigModal(true);
              }
            }}
            title="Click to configure backend API connection settings"
            aria-label={`API Status: ${useMock ? 'Mock Engine Active' : 'Live REST API'}`}
          >
            <span className="status-dot" style={{ color: useMock ? '#34d399' : '#fbbf24' }} />
            <span>{useMock ? 'Mock Engine' : 'Live REST API'}</span>
          </div>
        </div>

        {/* Action / Settings Button */}
        <div className="header-actions">
          <button 
            className="btn btn-outline"
            style={{ padding: '8px 14px', fontSize: '13px' }}
            onClick={() => {
              setTempMock(useMock);
              setTempUrl(baseUrl);
              setShowConfigModal(true);
            }}
            aria-label="Open API settings"
          >
            <Settings size={15} aria-hidden="true" />
            <span>API Settings</span>
          </button>
        </div>
      </div>

      {/* API Configuration Modal */}
      {showConfigModal && (
        <div 
          style={{
            position: 'fixed',
            inset: 0,
            background: 'rgba(0, 0, 0, 0.75)',
            backdropFilter: 'blur(10px)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            zIndex: 1000,
            padding: '20px',
            animation: 'tabFadeIn 0.25s ease-out'
          }}
          onClick={() => setShowConfigModal(false)}
          role="dialog"
          aria-modal="true"
          aria-labelledby="modal-settings-title"
        >
          <div 
            className="glass-panel"
            style={{
              width: '100%',
              maxWidth: '480px',
              padding: '28px',
              background: '#0f172a',
              border: '1px solid var(--border-glow)',
              boxShadow: '0 20px 50px rgba(0, 0, 0, 0.8)'
            }}
            onClick={e => e.stopPropagation()}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
              <h2 id="modal-settings-title" style={{ fontSize: '18px', display: 'flex', alignItems: 'center', gap: '8px', color: 'var(--text-white)' }}>
                <Server size={20} color="#38bdf8" />
                Backend Connection Settings
              </h2>
              <button 
                className="btn btn-ghost" 
                style={{ padding: '6px' }}
                onClick={() => setShowConfigModal(false)}
                aria-label="Close modal"
              >
                <X size={18} />
              </button>
            </div>

            <form onSubmit={handleSaveConfig} style={{ display: 'flex', flexDirection: 'column', gap: '18px' }}>
              <div>
                <label style={{ display: 'block', fontSize: '13px', color: 'var(--text-secondary)', marginBottom: '8px' }}>
                  Execution Mode
                </label>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px' }}>
                  <button
                    type="button"
                    className={`btn ${tempMock ? 'btn-primary' : 'btn-outline'}`}
                    onClick={() => setTempMock(true)}
                  >
                    <Database size={15} />
                    Mock Engine
                  </button>
                  <button
                    type="button"
                    className={`btn ${!tempMock ? 'btn-primary' : 'btn-outline'}`}
                    onClick={() => setTempMock(false)}
                  >
                    <Globe size={15} />
                    Live REST API
                  </button>
                </div>
              </div>

              <div>
                <label style={{ display: 'block', fontSize: '13px', color: 'var(--text-secondary)', marginBottom: '8px' }}>
                  REST Base URL
                </label>
                <input 
                  type="text" 
                  className="form-input"
                  value={tempUrl}
                  onChange={e => setTempUrl(e.target.value)}
                  placeholder="http://localhost:8000/api"
                />
                <span style={{ fontSize: '11px', color: 'var(--text-muted)', marginTop: '4px', display: 'block' }}>
                  Endpoints expected: /dates, /tiles, /models, /predict, /compare
                </span>
              </div>

              <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '10px', marginTop: '10px' }}>
                <button 
                  type="button" 
                  className="btn btn-outline"
                  onClick={() => setShowConfigModal(false)}
                >
                  Cancel
                </button>
                <button type="submit" className="btn btn-primary">
                  <CheckCircle2 size={16} />
                  Save & Apply
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </header>
  );
};
