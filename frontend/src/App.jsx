import React, { useState } from 'react';
import { ThermaMLProvider, useThermaML } from './context/ThermaMLContext';
import { Header } from './components/Header';
import { CascadingControls } from './components/CascadingControls';
import { SinglePredictionView } from './components/SinglePredictionView';
import { ModelComparisonView } from './components/ModelComparisonView';
import { ScenarioSimulatorView } from './components/ScenarioSimulatorView';
import { ApiContractExplorer } from './components/ApiContractExplorer';
import { 
  Gauge, 
  BarChart3, 
  Sliders, 
  Code2, 
  AlertCircle, 
  X, 
  Info,
  CheckCircle2,
  ExternalLink
} from 'lucide-react';
import './App.css';

const DashboardContent = () => {
  const [activeTab, setActiveTab] = useState('single');
  const { error, clearError, toast } = useThermaML();

  return (
    <>
      <Header />

      <main className="dashboard-container">
        {/* Error Alert Banner */}
        {error && (
          <div className="error-alert-banner">
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
              <AlertCircle size={18} color="#ef4444" />
              <span>{error}</span>
            </div>
            <button 
              className="btn btn-ghost" 
              style={{ padding: '2px', color: '#fca5a5' }}
              onClick={clearError}
            >
              <X size={16} />
            </button>
          </div>
        )}

        {/* Cascading Controls */}
        <CascadingControls />

        {/* Navigation Tabs */}
        <nav className="dashboard-tabs">
          <button 
            className={`tab-btn ${activeTab === 'single' ? 'active' : ''}`}
            onClick={() => setActiveTab('single')}
          >
            <Gauge size={16} />
            <span>Single Prediction</span>
          </button>

          <button 
            className={`tab-btn ${activeTab === 'comparison' ? 'active' : ''}`}
            onClick={() => setActiveTab('comparison')}
          >
            <BarChart3 size={16} />
            <span>Model Comparison</span>
          </button>

          <button 
            className={`tab-btn ${activeTab === 'simulator' ? 'active' : ''}`}
            onClick={() => setActiveTab('simulator')}
          >
            <Sliders size={16} />
            <span>Scenario Simulator</span>
          </button>

          <button 
            className={`tab-btn ${activeTab === 'explorer' ? 'active' : ''}`}
            onClick={() => setActiveTab('explorer')}
          >
            <Code2 size={16} />
            <span>API Explorer</span>
          </button>
        </nav>

        {/* Tab Views */}
        {activeTab === 'single' && (
          <SinglePredictionView onNavigateToSimulator={() => setActiveTab('simulator')} />
        )}

        {activeTab === 'comparison' && (
          <ModelComparisonView />
        )}

        {activeTab === 'simulator' && (
          <ScenarioSimulatorView />
        )}

        {activeTab === 'explorer' && (
          <ApiContractExplorer />
        )}
      </main>

      {/* Toast Notification */}
      {toast && (
        <div className="toast-notification">
          <CheckCircle2 size={18} color="#38bdf8" />
          <span style={{ fontSize: '13px', color: 'var(--text-white)' }}>{toast.message}</span>
        </div>
      )}

      {/* System Footer */}
      <footer style={{
        marginTop: 'auto',
        borderTop: '1px solid var(--border-subtle)',
        padding: '24px 28px',
        background: 'rgba(7, 9, 14, 0.95)',
        textAlign: 'center',
        fontSize: '12px',
        color: 'var(--text-muted)'
      }}>
        <div style={{ maxWidth: '1440px', margin: '0 auto', display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '12px' }}>
          <div>
            <strong>ThermaML Urban Heat Regression</strong> &bull; Dataset Scope: 37 Dates (2023-01-01 to 2024-01-28) &bull; Target: <code>daily_temperature</code>
          </div>
          <div>
            Contract Conformance: <code>frontend_contract.md</code> &bull; Version 1.0.0
          </div>
        </div>
      </footer>
    </>
  );
};

export default function App() {
  return (
    <ThermaMLProvider>
      <DashboardContent />
    </ThermaMLProvider>
  );
}
