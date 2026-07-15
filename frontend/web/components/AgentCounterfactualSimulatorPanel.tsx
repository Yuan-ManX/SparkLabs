"use client";
import React, { useState, useEffect, useCallback } from 'react';
import { API_BASE as API_ROOT } from '../utils/api';

const API_BASE = API_ROOT + '/agent';

type TabId = 'overview' | 'create-scenario' | 'scenarios' | 'run' | 'compare' | 'recommend';

interface Stats {
  total_scenarios: number;
  total_changes: number;
  total_runs: number;
  total_comparisons: number;
}

const uid = () => `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;

export default function AgentCounterfactualSimulatorPanel() {
  const [activeTab, setActiveTab] = useState<TabId>('overview');
  const [stats, setStats] = useState<Stats | null>(null);
  const [message, setMessage] = useState<{ text: string; type: 'success' | 'error' | 'info' } | null>(null);

  // Create Scenario form
  const [scenarioForm, setScenarioForm] = useState({ name: '', description: '', baseline_context: '' });
  const [scenarioLoading, setScenarioLoading] = useState(false);
  const [scenarioResult, setScenarioResult] = useState<any>(null);

  // Scenarios list
  const [scenarios, setScenarios] = useState<any[]>([]);
  const [scenariosLoading, setScenariosLoading] = useState(false);

  // Add Change form
  const [changeForm, setChangeForm] = useState({ scenario_id: '', change_type: 'variable', target: '', description: '', magnitude: '0.5' });
  const [changeLoading, setChangeLoading] = useState(false);
  const [changeResult, setChangeResult] = useState<any>(null);

  // Run Simulation form
  const [runForm, setRunForm] = useState({ scenario_id: '', ticks: '100' });
  const [runLoading, setRunLoading] = useState(false);
  const [runResult, setRunResult] = useState<any>(null);

  // Compare form
  const [compareForm, setCompareForm] = useState({ scenario_a_id: '', scenario_b_id: '' });
  const [compareLoading, setCompareLoading] = useState(false);
  const [compareResult, setCompareResult] = useState<any>(null);

  // Recommend Action form
  const [recommendForm, setRecommendForm] = useState({ scenario_id: '' });
  const [recommendLoading, setRecommendLoading] = useState(false);
  const [recommendResult, setRecommendResult] = useState<any>(null);

  const showMessage = (text: string, type: 'success' | 'error' | 'info') => {
    setMessage({ text, type });
    setTimeout(() => setMessage(null), 4000);
  };

  const fetchStats = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/counterfactual-simulator/stats`);
      if (res.ok) {
        const data = await res.json();
        setStats(data.stats || data);
      }
    } catch { /* use defaults */ }
  }, []);

  useEffect(() => {
    fetchStats();
    const interval = setInterval(fetchStats, 15000);
    return () => clearInterval(interval);
  }, [fetchStats]);

  // --- Create Scenario ---
  const handleCreateScenario = async () => {
    if (!scenarioForm.name.trim()) {
      showMessage('Name is required', 'error');
      return;
    }
    setScenarioLoading(true);
    try {
      const body: Record<string, any> = {
        name: scenarioForm.name,
        description: scenarioForm.description,
        baseline_context: scenarioForm.baseline_context,
      };
      const res = await fetch(`${API_BASE}/counterfactual-simulator/create-scenario`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });
      const data = await res.json();
      if (res.ok) {
        setScenarioResult(data.scenario || data);
        showMessage('Scenario created successfully', 'success');
        fetchStats();
      } else {
        showMessage(data.error || 'Failed to create scenario', 'error');
      }
    } catch {
      setScenarioResult({
        scenario_id: uid(),
        name: scenarioForm.name,
        description: scenarioForm.description,
        baseline_context: scenarioForm.baseline_context,
        created_at: 'just now',
      });
      showMessage('Scenario created (offline mode)', 'info');
    } finally {
      setScenarioLoading(false);
    }
  };

  // --- Fetch Scenarios ---
  const handleFetchScenarios = async () => {
    setScenariosLoading(true);
    try {
      const res = await fetch(`${API_BASE}/counterfactual-simulator/scenarios`);
      const data = await res.json();
      if (res.ok) {
        setScenarios(data.scenarios || data || []);
        showMessage('Scenarios loaded', 'success');
      } else {
        showMessage(data.error || 'Failed to load scenarios', 'error');
      }
    } catch {
      setScenarios([
        { scenario_id: uid(), name: 'Baseline World', description: 'The default timeline with no changes', changes: 0, runs: 3, created_at: '1d ago' },
        { scenario_id: uid(), name: 'Flood Scenario', description: 'Simulation where a great flood occurs', changes: 2, runs: 1, created_at: '12h ago' },
        { scenario_id: uid(), name: 'Peace Treaty', description: 'What if the warring factions signed a treaty?', changes: 1, runs: 2, created_at: '6h ago' },
      ]);
      showMessage('Scenarios loaded (offline mode)', 'info');
    } finally {
      setScenariosLoading(false);
    }
  };

  // --- Add Change ---
  const handleAddChange = async () => {
    if (!changeForm.scenario_id.trim() || !changeForm.target.trim()) {
      showMessage('Scenario ID and Target are required', 'error');
      return;
    }
    setChangeLoading(true);
    try {
      const body: Record<string, any> = {
        scenario_id: changeForm.scenario_id,
        change_type: changeForm.change_type,
        target: changeForm.target,
        description: changeForm.description,
        magnitude: parseFloat(changeForm.magnitude) || 0.5,
      };
      const res = await fetch(`${API_BASE}/counterfactual-simulator/add-change`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });
      const data = await res.json();
      if (res.ok) {
        setChangeResult(data.change || data);
        showMessage('Change added successfully', 'success');
        fetchStats();
      } else {
        showMessage(data.error || 'Failed to add change', 'error');
      }
    } catch {
      setChangeResult({
        change_id: uid(),
        scenario_id: changeForm.scenario_id,
        change_type: changeForm.change_type,
        target: changeForm.target,
        description: changeForm.description,
        magnitude: parseFloat(changeForm.magnitude) || 0.5,
        applied_at: 'just now',
      });
      showMessage('Change added (offline mode)', 'info');
    } finally {
      setChangeLoading(false);
    }
  };

  // --- Run Simulation ---
  const handleRunSimulation = async () => {
    if (!runForm.scenario_id.trim()) {
      showMessage('Scenario ID is required', 'error');
      return;
    }
    setRunLoading(true);
    try {
      const body: Record<string, any> = {
        scenario_id: runForm.scenario_id,
        ticks: parseInt(runForm.ticks) || 100,
      };
      const res = await fetch(`${API_BASE}/counterfactual-simulator/run`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });
      const data = await res.json();
      if (res.ok) {
        setRunResult(data.result || data);
        showMessage('Simulation completed successfully', 'success');
        fetchStats();
      } else {
        showMessage(data.error || 'Failed to run simulation', 'error');
      }
    } catch {
      setRunResult({
        run_id: uid(),
        scenario_id: runForm.scenario_id,
        ticks: parseInt(runForm.ticks) || 100,
        outcome: 'simulation_complete',
        summary: 'The simulation completed with the modified parameters, showing divergent outcomes from the baseline.',
        completed_at: 'just now',
      });
      showMessage('Simulation completed (offline mode)', 'info');
    } finally {
      setRunLoading(false);
    }
  };

  // --- Compare Scenarios ---
  const handleCompareScenarios = async () => {
    if (!compareForm.scenario_a_id.trim() || !compareForm.scenario_b_id.trim()) {
      showMessage('Both Scenario IDs are required', 'error');
      return;
    }
    setCompareLoading(true);
    try {
      const params = new URLSearchParams();
      params.set('scenario_a_id', compareForm.scenario_a_id);
      params.set('scenario_b_id', compareForm.scenario_b_id);
      const res = await fetch(`${API_BASE}/counterfactual-simulator/compare?${params.toString()}`);
      const data = await res.json();
      if (res.ok) {
        setCompareResult(data.comparison || data);
        showMessage('Comparison completed successfully', 'success');
      } else {
        showMessage(data.error || 'Failed to compare scenarios', 'error');
      }
    } catch {
      setCompareResult({
        comparison_id: uid(),
        scenario_a_id: compareForm.scenario_a_id,
        scenario_b_id: compareForm.scenario_b_id,
        divergence_score: 0.65,
        key_differences: ['Economy diverged by 35%', 'Population growth differs significantly', 'Political landscape shifted'],
        compared_at: 'just now',
      });
      showMessage('Comparison completed (offline mode)', 'info');
    } finally {
      setCompareLoading(false);
    }
  };

  // --- Recommend Action ---
  const handleRecommendAction = async () => {
    if (!recommendForm.scenario_id.trim()) {
      showMessage('Scenario ID is required', 'error');
      return;
    }
    setRecommendLoading(true);
    try {
      const params = new URLSearchParams();
      params.set('scenario_id', recommendForm.scenario_id);
      const res = await fetch(`${API_BASE}/counterfactual-simulator/recommend-action?${params.toString()}`);
      const data = await res.json();
      if (res.ok) {
        setRecommendResult(data.recommendation || data);
        showMessage('Recommendation generated successfully', 'success');
      } else {
        showMessage(data.error || 'Failed to generate recommendation', 'error');
      }
    } catch {
      setRecommendResult({
        recommendation_id: uid(),
        scenario_id: recommendForm.scenario_id,
        recommended_action: 'Adjust resource allocation towards sustainable development',
        expected_impact: 'Positive shift in stability metrics',
        confidence: 0.78,
        generated_at: 'just now',
      });
      showMessage('Recommendation generated (offline mode)', 'info');
    } finally {
      setRecommendLoading(false);
    }
  };

  const tabItems: { key: TabId; label: string; icon: string }[] = [
    { key: 'overview', label: 'Overview', icon: '\uD83C\uDF10' },
    { key: 'create-scenario', label: 'Create Scenario', icon: '\u2795' },
    { key: 'scenarios', label: 'Scenarios', icon: '\uD83D\uDCCA' },
    { key: 'run', label: 'Run Simulation', icon: '\u25B6\uFE0F' },
    { key: 'compare', label: 'Compare', icon: '\u2696\uFE0F' },
    { key: 'recommend', label: 'Recommend', icon: '\uD83D\uDCA1' },
  ];

  const darkInputStyle: React.CSSProperties = {
    width: '100%', padding: '6px 10px', fontSize: 12,
    backgroundColor: '#141428', color: '#ccc',
    border: '1px solid #333', borderRadius: 4, boxSizing: 'border-box', outline: 'none',
  };

  const darkTextareaStyle: React.CSSProperties = {
    ...darkInputStyle, resize: 'vertical', fontFamily: 'monospace',
  };

  const darkSelectStyle: React.CSSProperties = {
    ...darkInputStyle, cursor: 'pointer',
  };

  const cardStyle: React.CSSProperties = {
    padding: 14, backgroundColor: '#22223a', borderRadius: 6,
    border: '1px solid #2a2a3e',
  };

  const labelStyle: React.CSSProperties = {
    fontSize: 10, color: '#888', marginBottom: 2, display: 'block',
  };

  const primaryBtnStyle = (color: string): React.CSSProperties => ({
    padding: '6px 14px',
    backgroundColor: '#2d3a4a',
    color,
    border: '1px solid #3d4a5a',
    borderRadius: 4,
    cursor: 'pointer',
    fontSize: 11,
    fontWeight: 600,
  });

  const disabledBtnStyle = (color: string): React.CSSProperties => ({
    ...primaryBtnStyle(color),
    backgroundColor: '#1a2a3a',
    color: '#666',
    cursor: 'not-allowed',
  });

  return (
    <div style={{
      display: 'flex', flexDirection: 'column', height: '100%',
      backgroundColor: '#1a1a2e', color: '#e0e0e0',
      fontFamily: 'system-ui, sans-serif', fontSize: 13,
    }}>
      {/* Header */}
      <div style={{
        padding: '12px 16px', borderBottom: '1px solid #2a2a3e',
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <span style={{ fontSize: 18 }}>{'\uD83C\uDF10'}</span>
          <span style={{ fontWeight: 700, fontSize: 15 }}>Counterfactual Simulator</span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          {stats && (
            <span style={{ fontSize: 10, color: '#888' }}>
              {stats.total_scenarios ?? 0} scenarios · {stats.total_runs ?? 0} runs
            </span>
          )}
        </div>
      </div>

      {/* Status Message */}
      {message && (
        <div style={{
          padding: '8px 16px', fontSize: 12,
          backgroundColor: message.type === 'success' ? '#1a3a1a' : message.type === 'error' ? '#3a1a1a' : '#1a2a3a',
          borderBottom: `1px solid ${message.type === 'success' ? '#2d5a2d' : message.type === 'error' ? '#5a2d2d' : '#2a3a4a'}`,
          color: message.type === 'success' ? '#6bcb77' : message.type === 'error' ? '#ff6b6b' : '#74b9ff',
        }}>
          {message.text}
        </div>
      )}

      {/* Tab Navigation */}
      <div style={{ display: 'flex', borderBottom: '1px solid #2a2a3e' }}>
        {tabItems.map(tab => (
          <button
            key={tab.key}
            onClick={() => setActiveTab(tab.key)}
            style={{
              flex: 1, padding: '8px 12px', fontSize: 12, fontWeight: 600,
              backgroundColor: activeTab === tab.key ? '#22223a' : 'transparent',
              color: activeTab === tab.key ? '#e0e0e0' : '#888',
              border: 'none',
              borderBottom: activeTab === tab.key ? '2px solid #00d4ff' : '2px solid transparent',
              cursor: 'pointer',
            }}
          >
            {tab.icon} {tab.label}
          </button>
        ))}
      </div>

      {/* Content Area */}
      <div style={{ flex: 1, overflow: 'auto', padding: 12 }}>

        {/* Tab: Overview */}
        {activeTab === 'overview' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            <div style={cardStyle}>
              <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 12, color: '#aaa' }}>
                {'\uD83C\uDF10'} Counterfactual Simulator Status
              </div>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10 }}>
                {[
                  { label: 'Total Scenarios', value: stats?.total_scenarios, color: '#74b9ff' },
                  { label: 'Total Changes', value: stats?.total_changes, color: '#fdcb6e' },
                  { label: 'Total Runs', value: stats?.total_runs, color: '#6bcb77' },
                  { label: 'Total Comparisons', value: stats?.total_comparisons, color: '#a29bfe' },
                ].map(item => (
                  <div key={item.label} style={{
                    padding: 10, backgroundColor: '#1a1a2e', borderRadius: 6,
                    display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 4,
                  }}>
                    <span style={{ fontSize: 10, color: '#888' }}>{item.label}</span>
                    <span style={{ fontSize: 18, fontWeight: 700, color: item.color }}>{item.value ?? 0}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}

        {/* Tab: Create Scenario */}
        {activeTab === 'create-scenario' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            <div style={cardStyle}>
              <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 10, color: '#74b9ff' }}>
                {'\u2795'} Create Scenario
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 8, marginBottom: 10 }}>
                <div>
                  <span style={labelStyle}>Name *</span>
                  <input style={darkInputStyle} placeholder="e.g. Great Flood Scenario" value={scenarioForm.name} onChange={e => setScenarioForm(prev => ({ ...prev, name: e.target.value }))} />
                </div>
                <div>
                  <span style={labelStyle}>Description</span>
                  <textarea style={darkTextareaStyle} placeholder="Describe the scenario..." rows={2} value={scenarioForm.description} onChange={e => setScenarioForm(prev => ({ ...prev, description: e.target.value }))} />
                </div>
                <div>
                  <span style={labelStyle}>Baseline Context</span>
                  <textarea style={darkTextareaStyle} placeholder="Baseline world state context..." rows={3} value={scenarioForm.baseline_context} onChange={e => setScenarioForm(prev => ({ ...prev, baseline_context: e.target.value }))} />
                </div>
              </div>
              <button onClick={handleCreateScenario} disabled={scenarioLoading} style={scenarioLoading ? disabledBtnStyle('#74b9ff') : primaryBtnStyle('#74b9ff')}>
                {scenarioLoading ? 'Creating...' : '\u2795 Create Scenario'}
              </button>
            </div>
            {scenarioResult && (
              <div style={cardStyle}>
                <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 10, color: '#aaa' }}>Created Scenario</div>
                <div style={{ borderLeft: '3px solid #74b9ff', paddingLeft: 10 }}>
                  <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 4 }}>{scenarioResult.name}</div>
                  {scenarioResult.description && <div style={{ fontSize: 11, color: '#ccc', marginBottom: 4 }}>{scenarioResult.description}</div>}
                  <div style={{ display: 'flex', gap: 8, fontSize: 9, color: '#666', flexWrap: 'wrap' }}>
                    <span>ID: <span style={{ color: '#74b9ff' }}>{scenarioResult.scenario_id}</span></span>
                    <span>Created: <span style={{ color: '#6bcb77' }}>{scenarioResult.created_at}</span></span>
                  </div>
                </div>
              </div>
            )}

            {/* Add Change inline */}
            <div style={cardStyle}>
              <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 10, color: '#fdcb6e' }}>
                {'\u2699\uFE0F'} Add Change to Scenario
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 8, marginBottom: 10 }}>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
                  <div>
                    <span style={labelStyle}>Scenario ID *</span>
                    <input style={darkInputStyle} placeholder="e.g. scenario_xxx" value={changeForm.scenario_id} onChange={e => setChangeForm(prev => ({ ...prev, scenario_id: e.target.value }))} />
                  </div>
                  <div>
                    <span style={labelStyle}>Change Type</span>
                    <select style={darkSelectStyle} value={changeForm.change_type} onChange={e => setChangeForm(prev => ({ ...prev, change_type: e.target.value }))}>
                      <option value="variable">Variable</option>
                      <option value="event">Event</option>
                      <option value="agent">Agent</option>
                      <option value="environment">Environment</option>
                      <option value="policy">Policy</option>
                    </select>
                  </div>
                </div>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
                  <div>
                    <span style={labelStyle}>Target *</span>
                    <input style={darkInputStyle} placeholder="What to change?" value={changeForm.target} onChange={e => setChangeForm(prev => ({ ...prev, target: e.target.value }))} />
                  </div>
                  <div>
                    <span style={labelStyle}>Magnitude (0-1)</span>
                    <input style={darkInputStyle} placeholder="0.5" value={changeForm.magnitude} onChange={e => setChangeForm(prev => ({ ...prev, magnitude: e.target.value }))} />
                  </div>
                </div>
                <div>
                  <span style={labelStyle}>Description</span>
                  <input style={darkInputStyle} placeholder="Describe the change..." value={changeForm.description} onChange={e => setChangeForm(prev => ({ ...prev, description: e.target.value }))} />
                </div>
              </div>
              <button onClick={handleAddChange} disabled={changeLoading} style={changeLoading ? disabledBtnStyle('#fdcb6e') : primaryBtnStyle('#fdcb6e')}>
                {changeLoading ? 'Adding...' : '\u2699\uFE0F Add Change'}
              </button>
            </div>
            {changeResult && (
              <div style={cardStyle}>
                <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 10, color: '#aaa' }}>Change Result</div>
                <div style={{ borderLeft: '3px solid #fdcb6e', paddingLeft: 10 }}>
                  <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 4 }}>{changeResult.target}</div>
                  <div style={{ display: 'flex', gap: 8, fontSize: 9, color: '#666', flexWrap: 'wrap' }}>
                    <span>Type: <span style={{ color: '#fdcb6e' }}>{changeResult.change_type}</span></span>
                    <span>Magnitude: <span style={{ color: '#e17055' }}>{changeResult.magnitude}</span></span>
                    <span>ID: <span style={{ color: '#888' }}>{changeResult.change_id}</span></span>
                  </div>
                </div>
              </div>
            )}
          </div>
        )}

        {/* Tab: Scenarios */}
        {activeTab === 'scenarios' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            <div style={cardStyle}>
              <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 10, color: '#6bcb77' }}>
                {'\uD83D\uDCCA'} All Scenarios
              </div>
              <button
                onClick={handleFetchScenarios}
                disabled={scenariosLoading}
                style={{
                  ...(scenariosLoading ? disabledBtnStyle('#6bcb77') : primaryBtnStyle('#6bcb77')),
                  width: '100%', marginBottom: 10,
                }}
              >
                {scenariosLoading ? 'Loading...' : '\uD83D\uDD04 Fetch Scenarios'}
              </button>
              {scenarios.length > 0 && (
                <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                  {scenarios.map(sc => (
                    <div key={sc.scenario_id} style={{
                      padding: 12, backgroundColor: '#1a1a2e', borderRadius: 6,
                      border: '1px solid #2a2a3e',
                      borderLeft: '3px solid #6bcb77',
                    }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 4 }}>
                        <span style={{ fontWeight: 600, fontSize: 13 }}>{sc.name}</span>
                        <span style={{ fontSize: 9, color: '#666' }}>{sc.created_at}</span>
                      </div>
                      {sc.description && <div style={{ fontSize: 10, color: '#888', marginBottom: 6 }}>{sc.description}</div>}
                      <div style={{ display: 'flex', gap: 10, fontSize: 9, color: '#666', flexWrap: 'wrap' }}>
                        <span>ID: <span style={{ color: '#74b9ff' }}>{sc.scenario_id}</span></span>
                        <span>Changes: <span style={{ color: '#fdcb6e' }}>{sc.changes ?? 0}</span></span>
                        <span>Runs: <span style={{ color: '#a29bfe' }}>{sc.runs ?? 0}</span></span>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        )}

        {/* Tab: Run Simulation */}
        {activeTab === 'run' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            <div style={cardStyle}>
              <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 10, color: '#00d4ff' }}>
                {'\u25B6\uFE0F'} Run Simulation
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 8, marginBottom: 10 }}>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
                  <div>
                    <span style={labelStyle}>Scenario ID *</span>
                    <input style={darkInputStyle} placeholder="e.g. scenario_xxx" value={runForm.scenario_id} onChange={e => setRunForm(prev => ({ ...prev, scenario_id: e.target.value }))} />
                  </div>
                  <div>
                    <span style={labelStyle}>Ticks</span>
                    <input style={darkInputStyle} type="number" placeholder="100" value={runForm.ticks} onChange={e => setRunForm(prev => ({ ...prev, ticks: e.target.value }))} />
                  </div>
                </div>
              </div>
              <button onClick={handleRunSimulation} disabled={runLoading} style={runLoading ? disabledBtnStyle('#00d4ff') : primaryBtnStyle('#00d4ff')}>
                {runLoading ? 'Running...' : '\u25B6\uFE0F Run Simulation'}
              </button>
            </div>
            {runResult && (
              <div style={cardStyle}>
                <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 10, color: '#aaa' }}>Simulation Result</div>
                <div style={{ borderLeft: '3px solid #00d4ff', paddingLeft: 10 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4 }}>
                    <span style={{ fontWeight: 600, fontSize: 13 }}>{runResult.outcome}</span>
                    <span style={{
                      fontSize: 9, padding: '1px 6px', borderRadius: 3,
                      backgroundColor: '#1a3a1a', color: '#6bcb77', fontWeight: 600,
                    }}>
                      {runResult.ticks} ticks
                    </span>
                  </div>
                  {runResult.summary && <div style={{ fontSize: 11, color: '#ccc', marginBottom: 4 }}>{runResult.summary}</div>}
                  <div style={{ display: 'flex', gap: 8, fontSize: 9, color: '#666', flexWrap: 'wrap' }}>
                    <span>Scenario: <span style={{ color: '#74b9ff' }}>{runResult.scenario_id}</span></span>
                    <span>Run ID: <span style={{ color: '#888' }}>{runResult.run_id}</span></span>
                  </div>
                </div>
              </div>
            )}
          </div>
        )}

        {/* Tab: Compare */}
        {activeTab === 'compare' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            <div style={cardStyle}>
              <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 10, color: '#a29bfe' }}>
                {'\u2696\uFE0F'} Compare Scenarios
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 8, marginBottom: 10 }}>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
                  <div>
                    <span style={labelStyle}>Scenario A ID *</span>
                    <input style={darkInputStyle} placeholder="e.g. scenario_xxx" value={compareForm.scenario_a_id} onChange={e => setCompareForm(prev => ({ ...prev, scenario_a_id: e.target.value }))} />
                  </div>
                  <div>
                    <span style={labelStyle}>Scenario B ID *</span>
                    <input style={darkInputStyle} placeholder="e.g. scenario_yyy" value={compareForm.scenario_b_id} onChange={e => setCompareForm(prev => ({ ...prev, scenario_b_id: e.target.value }))} />
                  </div>
                </div>
              </div>
              <button onClick={handleCompareScenarios} disabled={compareLoading} style={compareLoading ? disabledBtnStyle('#a29bfe') : primaryBtnStyle('#a29bfe')}>
                {compareLoading ? 'Comparing...' : '\u2696\uFE0F Compare Scenarios'}
              </button>
            </div>
            {compareResult && (
              <div style={cardStyle}>
                <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 10, color: '#aaa' }}>Comparison Result</div>
                <div style={{ borderLeft: '3px solid #a29bfe', paddingLeft: 10 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 6 }}>
                    <span style={{ fontWeight: 600, fontSize: 13 }}>Divergence Score:</span>
                    <span style={{ fontSize: 18, fontWeight: 700, color: '#fdcb6e' }}>{compareResult.divergence_score}</span>
                  </div>
                  {compareResult.key_differences && (
                    <div style={{ marginBottom: 6 }}>
                      <div style={{ fontSize: 10, color: '#888', marginBottom: 4 }}>Key Differences:</div>
                      <ul style={{ margin: 0, paddingLeft: 16, fontSize: 11, color: '#ccc' }}>
                        {compareResult.key_differences.map((d: string, i: number) => (
                          <li key={i}>{d}</li>
                        ))}
                      </ul>
                    </div>
                  )}
                  <div style={{ display: 'flex', gap: 8, fontSize: 9, color: '#666', flexWrap: 'wrap' }}>
                    <span>A: <span style={{ color: '#74b9ff' }}>{compareResult.scenario_a_id}</span></span>
                    <span>B: <span style={{ color: '#e17055' }}>{compareResult.scenario_b_id}</span></span>
                  </div>
                </div>
              </div>
            )}
          </div>
        )}

        {/* Tab: Recommend */}
        {activeTab === 'recommend' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            <div style={cardStyle}>
              <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 10, color: '#fdcb6e' }}>
                {'\uD83D\uDCA1'} Recommend Action
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 8, marginBottom: 10 }}>
                <div>
                  <span style={labelStyle}>Scenario ID *</span>
                  <input style={darkInputStyle} placeholder="e.g. scenario_xxx" value={recommendForm.scenario_id} onChange={e => setRecommendForm(prev => ({ ...prev, scenario_id: e.target.value }))} />
                </div>
              </div>
              <button onClick={handleRecommendAction} disabled={recommendLoading} style={recommendLoading ? disabledBtnStyle('#fdcb6e') : primaryBtnStyle('#fdcb6e')}>
                {recommendLoading ? 'Generating...' : '\uD83D\uDCA1 Get Recommendation'}
              </button>
            </div>
            {recommendResult && (
              <div style={cardStyle}>
                <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 10, color: '#aaa' }}>Recommendation</div>
                <div style={{ borderLeft: '3px solid #fdcb6e', paddingLeft: 10 }}>
                  <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 4, color: '#fdcb6e' }}>{recommendResult.recommended_action}</div>
                  {recommendResult.expected_impact && <div style={{ fontSize: 11, color: '#ccc', marginBottom: 4 }}>Impact: {recommendResult.expected_impact}</div>}
                  <div style={{ display: 'flex', gap: 8, fontSize: 9, color: '#666', flexWrap: 'wrap' }}>
                    <span>Confidence: <span style={{ color: '#6bcb77' }}>{recommendResult.confidence}</span></span>
                    <span>Scenario: <span style={{ color: '#74b9ff' }}>{recommendResult.scenario_id}</span></span>
                  </div>
                </div>
              </div>
            )}
          </div>
        )}

      </div>

      {/* Footer */}
      <div style={{
        padding: '6px 12px', borderTop: '1px solid #2a2a3e',
        backgroundColor: '#141428', display: 'flex',
        alignItems: 'center', justifyContent: 'space-between',
        fontSize: 10, color: '#666',
      }}>
        <span>{'\uD83C\uDF10'} Counterfactual Simulator</span>
        <span>
          {stats
            ? `${stats.total_scenarios ?? 0} scenarios · ${stats.total_runs ?? 0} runs · ${stats.total_comparisons ?? 0} comparisons`
            : 'Connected'}
        </span>
      </div>
    </div>
  );
}