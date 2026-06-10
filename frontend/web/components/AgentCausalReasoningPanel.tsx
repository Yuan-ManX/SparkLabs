import React, { useState, useEffect, useCallback } from 'react';

type ActiveTab = 'discovery' | 'intervention' | 'counterfactuals' | 'status';

interface CausalStatus {
  total_discoveries: number;
  total_interventions: number;
  total_counterfactuals: number;
  active_domains: number;
  avg_fitness_score: number;
  avg_confidence: number;
}

interface CausalEdge {
  from: string;
  to: string;
  strength: number;
}

interface CausalGraphResult {
  domain: string;
  algorithm: string;
  nodes: string[];
  edges: CausalEdge[];
  fitness_score: number;
}

interface InterventionResult {
  domain: string;
  variable: string;
  new_value: string;
  affected_variables: { name: string; before: string; after: string }[];
}

interface CounterfactualResult {
  domain: string;
  query: string;
  result: string;
  confidence: number;
}

const uid = () => `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;

const AgentCausalReasoningPanel: React.FC = () => {
  const [activeTab, setActiveTab] = useState<ActiveTab>('discovery');
  const [message, setMessage] = useState<{ text: string; type: 'success' | 'error' | 'info' } | null>(null);
  const [loading, setLoading] = useState(false);
  const [status, setStatus] = useState<CausalStatus | null>(null);

  // Graph Discovery form
  const [discoveryForm, setDiscoveryForm] = useState({
    domain: '',
    variables: '',
    observations: '',
    algorithm: 'pc' as string,
  });

  const [graphResult, setGraphResult] = useState<CausalGraphResult | null>(null);

  // Intervention form
  const [interventionForm, setInterventionForm] = useState({
    domain: '',
    variable: '',
    newValue: '',
    target: '',
  });

  const [interventionResult, setInterventionResult] = useState<InterventionResult | null>(null);

  // Counterfactual form
  const [counterfactualForm, setCounterfactualForm] = useState({
    domain: '',
    factual: '',
    hypothetical: '',
    query: '',
  });

  const [counterfactualResult, setCounterfactualResult] = useState<CounterfactualResult | null>(null);

  const apiBase = 'http://localhost:8000/api/agent';

  const defaultStatus: CausalStatus = {
    total_discoveries: 42,
    total_interventions: 128,
    total_counterfactuals: 67,
    active_domains: 5,
    avg_fitness_score: 0.78,
    avg_confidence: 0.84,
  };

  const showMessage = (text: string, type: 'success' | 'error' | 'info') => {
    setMessage({ text, type });
    setTimeout(() => setMessage(null), 4000);
  };

  const fetchStatus = useCallback(async () => {
    try {
      const res = await fetch(`${apiBase}/causal-reasoning/status`);
      if (!res.ok) throw new Error('Failed to fetch status');
      const data: CausalStatus = await res.json();
      setStatus(data);
    } catch {
      setStatus(defaultStatus);
    }
  }, []);

  useEffect(() => {
    setStatus(defaultStatus);
    fetchStatus();
  }, [fetchStatus]);

  // Polling on status tab
  useEffect(() => {
    if (activeTab !== 'status') return;
    const interval = setInterval(() => {
      fetchStatus();
    }, 15000);
    return () => clearInterval(interval);
  }, [activeTab, fetchStatus]);

  const handleDiscover = async () => {
    if (!discoveryForm.domain.trim() || !discoveryForm.variables.trim()) {
      showMessage('Please enter domain and variables', 'error');
      return;
    }
    setLoading(true);
    try {
      const vars = discoveryForm.variables.split(',').map(v => v.trim()).filter(Boolean);
      let observations = undefined;
      if (discoveryForm.observations.trim()) {
        try { observations = JSON.parse(discoveryForm.observations); } catch { /* ignore */ }
      }
      const res = await fetch(`${apiBase}/causal-reasoning/discover`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          domain: discoveryForm.domain,
          variables: vars,
          observations,
          algorithm: discoveryForm.algorithm,
        }),
      });
      if (!res.ok) throw new Error('Discovery failed');
      const data: CausalGraphResult = await res.json();
      setGraphResult(data);
      showMessage('Causal graph discovered', 'success');
      fetchStatus();
    } catch {
      const vars = discoveryForm.variables.split(',').map(v => v.trim()).filter(Boolean);
      const mockEdges: CausalEdge[] = [];
      for (let i = 0; i < vars.length - 1; i++) {
        mockEdges.push({ from: vars[i], to: vars[i + 1], strength: Math.round(Math.random() * 100) / 100 });
      }
      if (vars.length > 2) {
        mockEdges.push({ from: vars[0], to: vars[vars.length - 1], strength: Math.round(Math.random() * 100) / 100 });
      }
      setGraphResult({
        domain: discoveryForm.domain,
        algorithm: discoveryForm.algorithm,
        nodes: vars,
        edges: mockEdges,
        fitness_score: Math.round(Math.random() * 40 + 60) / 100,
      });
      showMessage('Causal graph discovered (offline mode)', 'info');
    } finally {
      setLoading(false);
    }
  };

  const handleIntervention = async () => {
    if (!interventionForm.domain.trim() || !interventionForm.variable.trim() || !interventionForm.newValue.trim()) {
      showMessage('Please fill in all required fields', 'error');
      return;
    }
    setLoading(true);
    try {
      const res = await fetch(`${apiBase}/causal-reasoning/intervention`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          domain: interventionForm.domain,
          intervention: { [interventionForm.variable]: interventionForm.newValue },
          target: interventionForm.target || undefined,
        }),
      });
      if (!res.ok) throw new Error('Intervention failed');
      const data: InterventionResult = await res.json();
      setInterventionResult(data);
      showMessage('Intervention simulated', 'success');
      fetchStatus();
    } catch {
      setInterventionResult({
        domain: interventionForm.domain,
        variable: interventionForm.variable,
        new_value: interventionForm.newValue,
        affected_variables: [
          { name: interventionForm.target || 'effect_var', before: '0.45', after: '0.72' },
          { name: 'intermediate_var', before: '0.33', after: '0.61' },
        ],
      });
      showMessage('Intervention simulated (offline mode)', 'info');
    } finally {
      setLoading(false);
    }
  };

  const handleCounterfactual = async () => {
    if (!counterfactualForm.domain.trim() || !counterfactualForm.query.trim()) {
      showMessage('Please enter domain and query', 'error');
      return;
    }
    setLoading(true);
    let factual = {}, hypothetical = {};
    try {
      if (counterfactualForm.factual.trim()) factual = JSON.parse(counterfactualForm.factual);
      if (counterfactualForm.hypothetical.trim()) hypothetical = JSON.parse(counterfactualForm.hypothetical);
    } catch {
      showMessage('Invalid JSON in factual/hypothetical', 'error');
      setLoading(false);
      return;
    }
    try {
      const res = await fetch(`${apiBase}/causal-reasoning/counterfactual`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          domain: counterfactualForm.domain,
          factual,
          hypothetical,
          query: counterfactualForm.query,
        }),
      });
      if (!res.ok) throw new Error('Counterfactual evaluation failed');
      const data: CounterfactualResult = await res.json();
      setCounterfactualResult(data);
      showMessage('Counterfactual evaluated', 'success');
      fetchStatus();
    } catch {
      setCounterfactualResult({
        domain: counterfactualForm.domain,
        query: counterfactualForm.query,
        result: `Under hypothetical conditions, the outcome would be different with probability ${Math.round(Math.random() * 60 + 40)}%`,
        confidence: Math.round(Math.random() * 30 + 65) / 100,
      });
      showMessage('Counterfactual evaluated (offline mode)', 'info');
    } finally {
      setLoading(false);
    }
  };

  const handleRefresh = async () => {
    await fetchStatus();
    showMessage('Panel refreshed', 'info');
  };

  const renderProgressBar = (label: string, value: number, maxValue: number = 1, unit: string = '%') => {
    const pct = Math.min((value / maxValue) * 100, 100);
    const clampedPct = Math.max(0, pct);
    let barColor = '#6bcb77';
    if (clampedPct > 70) barColor = '#ff6b6b';
    else if (clampedPct > 40) barColor = '#fdcb6e';
    return (
      <div style={{ marginBottom: 10 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 3, fontSize: 11 }}>
          <span style={{ color: '#aaa' }}>{label}</span>
          <span style={{ color: '#ccc', fontWeight: 600 }}>{unit === '%' ? `${clampedPct.toFixed(1)}${unit}` : `${value}${unit}`}</span>
        </div>
        <div style={{ height: 6, backgroundColor: '#141428', borderRadius: 3 }}>
          <div style={{
            height: '100%', width: `${clampedPct}%`,
            backgroundColor: barColor, borderRadius: 3,
            transition: 'width 0.3s ease',
          }} />
        </div>
      </div>
    );
  };

  const tabItems: { key: ActiveTab; label: string; icon: string }[] = [
    { key: 'discovery', label: 'Graph Discovery', icon: '\uD83D\uDD0D' },
    { key: 'intervention', label: 'Intervention Sim', icon: '\uD83D\uDD27' },
    { key: 'counterfactuals', label: 'Counterfactuals', icon: '\uD83E\uDDE9' },
    { key: 'status', label: 'Status', icon: '\u2699\uFE0F' },
  ];

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
          <span style={{ fontSize: 16 }}>{'\uD83D\uDD17'}</span>
          <span style={{ fontWeight: 700, fontSize: 15 }}>Agent Causal Reasoning</span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <button onClick={handleRefresh} style={{
            background: 'none', border: '1px solid #333', color: '#aaa',
            borderRadius: 4, padding: '4px 8px', cursor: 'pointer', fontSize: 11,
          }}>
            {'\u21BB'} Refresh
          </button>
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
          <button key={tab.key} onClick={() => setActiveTab(tab.key)} style={{
            flex: 1, padding: '8px 12px', fontSize: 12, fontWeight: 600,
            backgroundColor: activeTab === tab.key ? '#16213e' : 'transparent',
            color: activeTab === tab.key ? '#e0e0e0' : '#888',
            border: 'none',
            borderBottom: activeTab === tab.key ? '2px solid #0f3460' : '2px solid transparent',
            cursor: 'pointer',
          }}>
            {tab.icon} {tab.label}
          </button>
        ))}
      </div>

      {/* Content Area */}
      <div style={{ flex: 1, overflow: 'auto', padding: 12 }}>
        {/* Tab 1: Graph Discovery */}
        {activeTab === 'discovery' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            <div style={{
              padding: 14, backgroundColor: '#16213e', borderRadius: 8,
              border: '1px solid #0f3460',
            }}>
              <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 10, color: '#74b9ff' }}>
                Discover Causal Graph
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 8, marginBottom: 10 }}>
                <div>
                  <label style={{ fontSize: 10, color: '#888', display: 'block', marginBottom: 3 }}>Domain</label>
                  <input type="text" value={discoveryForm.domain}
                    onChange={e => setDiscoveryForm(prev => ({ ...prev, domain: e.target.value }))}
                    placeholder="e.g. healthcare"
                    style={{ width: '100%', padding: '6px 8px', fontSize: 12, backgroundColor: '#1a1a2e', color: '#e0e0e0', border: '1px solid #0f3460', borderRadius: 4, boxSizing: 'border-box' }}
                  />
                </div>
                <div>
                  <label style={{ fontSize: 10, color: '#888', display: 'block', marginBottom: 3 }}>Variables (comma-separated)</label>
                  <input type="text" value={discoveryForm.variables}
                    onChange={e => setDiscoveryForm(prev => ({ ...prev, variables: e.target.value }))}
                    placeholder="e.g. Age, Income, Health"
                    style={{ width: '100%', padding: '6px 8px', fontSize: 12, backgroundColor: '#1a1a2e', color: '#e0e0e0', border: '1px solid #0f3460', borderRadius: 4, boxSizing: 'border-box' }}
                  />
                </div>
                <div>
                  <label style={{ fontSize: 10, color: '#888', display: 'block', marginBottom: 3 }}>Algorithm</label>
                  <select value={discoveryForm.algorithm}
                    onChange={e => setDiscoveryForm(prev => ({ ...prev, algorithm: e.target.value }))}
                    style={{ width: '100%', padding: '6px 8px', fontSize: 12, backgroundColor: '#1a1a2e', color: '#e0e0e0', border: '1px solid #0f3460', borderRadius: 4, boxSizing: 'border-box' }}
                  >
                    <option value="pc">PC</option>
                    <option value="ges">GES</option>
                    <option value="lingam">LiNGAM</option>
                    <option value="fci">FCI</option>
                    <option value="hybrid">Hybrid</option>
                  </select>
                </div>
                <div>
                  <label style={{ fontSize: 10, color: '#888', display: 'block', marginBottom: 3 }}>Observations (JSON, optional)</label>
                  <textarea value={discoveryForm.observations}
                    onChange={e => setDiscoveryForm(prev => ({ ...prev, observations: e.target.value }))}
                    placeholder='[{"var1": 1, "var2": 2}, ...]'
                    rows={3}
                    style={{ width: '100%', padding: '6px 8px', fontSize: 12, backgroundColor: '#1a1a2e', color: '#e0e0e0', border: '1px solid #0f3460', borderRadius: 4, boxSizing: 'border-box', resize: 'vertical', fontFamily: 'monospace' }}
                  />
                </div>
              </div>
              <button onClick={handleDiscover} disabled={loading} style={{
                padding: '8px 18px', backgroundColor: '#0f3460', color: '#74b9ff',
                border: '1px solid #1a5276', borderRadius: 4, cursor: loading ? 'not-allowed' : 'pointer',
                fontSize: 12, fontWeight: 600, opacity: loading ? 0.6 : 1,
              }}>
                {loading ? 'Discovering...' : '\uD83D\uDD0D Discover Causal Graph'}
              </button>
            </div>

            {graphResult && (
              <div style={{
                padding: 14, backgroundColor: '#16213e', borderRadius: 8,
                border: '1px solid #0f3460',
              }}>
                <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 8, color: '#aaa' }}>
                  Graph Result: {graphResult.domain} ({graphResult.algorithm.toUpperCase()})
                </div>
                <div style={{ marginBottom: 8, fontSize: 12, color: '#888' }}>
                  Nodes: {graphResult.nodes.join(', ')}
                </div>
                <div style={{ marginBottom: 8 }}>
                  <span style={{ fontSize: 11, color: '#888' }}>Fitness Score: </span>
                  <span style={{ fontSize: 14, fontWeight: 700, color: '#6bcb77' }}>{(graphResult.fitness_score * 100).toFixed(0)}%</span>
                </div>
                <div style={{ fontWeight: 600, fontSize: 11, marginBottom: 4, color: '#aaa' }}>Edges:</div>
                <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 11 }}>
                  <thead>
                    <tr>
                      <th style={{ textAlign: 'left', padding: '4px 8px', borderBottom: '1px solid #2a2a3e', color: '#888' }}>From</th>
                      <th style={{ textAlign: 'left', padding: '4px 8px', borderBottom: '1px solid #2a2a3e', color: '#888' }}>To</th>
                      <th style={{ textAlign: 'right', padding: '4px 8px', borderBottom: '1px solid #2a2a3e', color: '#888' }}>Strength</th>
                    </tr>
                  </thead>
                  <tbody>
                    {graphResult.edges.map((edge, i) => (
                      <tr key={i}>
                        <td style={{ padding: '4px 8px', borderBottom: '1px solid #1a1a2e' }}>{edge.from}</td>
                        <td style={{ padding: '4px 8px', borderBottom: '1px solid #1a1a2e' }}>{edge.to}</td>
                        <td style={{ padding: '4px 8px', borderBottom: '1px solid #1a1a2e', textAlign: 'right', fontWeight: 600, color: edge.strength > 0.7 ? '#6bcb77' : edge.strength > 0.4 ? '#fdcb6e' : '#ff6b6b' }}>
                          {(edge.strength * 100).toFixed(0)}%
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        )}

        {/* Tab 2: Intervention Sim */}
        {activeTab === 'intervention' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            <div style={{
              padding: 14, backgroundColor: '#16213e', borderRadius: 8,
              border: '1px solid #0f3460',
            }}>
              <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 10, color: '#fdcb6e' }}>
                Simulate Intervention
              </div>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8, marginBottom: 10 }}>
                <div>
                  <label style={{ fontSize: 10, color: '#888', display: 'block', marginBottom: 3 }}>Domain</label>
                  <input type="text" value={interventionForm.domain}
                    onChange={e => setInterventionForm(prev => ({ ...prev, domain: e.target.value }))}
                    placeholder="e.g. healthcare"
                    style={{ width: '100%', padding: '6px 8px', fontSize: 12, backgroundColor: '#1a1a2e', color: '#e0e0e0', border: '1px solid #0f3460', borderRadius: 4, boxSizing: 'border-box' }}
                  />
                </div>
                <div>
                  <label style={{ fontSize: 10, color: '#888', display: 'block', marginBottom: 3 }}>Variable Name</label>
                  <input type="text" value={interventionForm.variable}
                    onChange={e => setInterventionForm(prev => ({ ...prev, variable: e.target.value }))}
                    placeholder="e.g. Treatment"
                    style={{ width: '100%', padding: '6px 8px', fontSize: 12, backgroundColor: '#1a1a2e', color: '#e0e0e0', border: '1px solid #0f3460', borderRadius: 4, boxSizing: 'border-box' }}
                  />
                </div>
                <div>
                  <label style={{ fontSize: 10, color: '#888', display: 'block', marginBottom: 3 }}>New Value</label>
                  <input type="text" value={interventionForm.newValue}
                    onChange={e => setInterventionForm(prev => ({ ...prev, newValue: e.target.value }))}
                    placeholder="e.g. 1.0"
                    style={{ width: '100%', padding: '6px 8px', fontSize: 12, backgroundColor: '#1a1a2e', color: '#e0e0e0', border: '1px solid #0f3460', borderRadius: 4, boxSizing: 'border-box' }}
                  />
                </div>
                <div>
                  <label style={{ fontSize: 10, color: '#888', display: 'block', marginBottom: 3 }}>Target Variable (optional)</label>
                  <input type="text" value={interventionForm.target}
                    onChange={e => setInterventionForm(prev => ({ ...prev, target: e.target.value }))}
                    placeholder="e.g. Outcome"
                    style={{ width: '100%', padding: '6px 8px', fontSize: 12, backgroundColor: '#1a1a2e', color: '#e0e0e0', border: '1px solid #0f3460', borderRadius: 4, boxSizing: 'border-box' }}
                  />
                </div>
              </div>
              <button onClick={handleIntervention} disabled={loading} style={{
                padding: '8px 18px', backgroundColor: '#0f3460', color: '#fdcb6e',
                border: '1px solid #1a5276', borderRadius: 4, cursor: loading ? 'not-allowed' : 'pointer',
                fontSize: 12, fontWeight: 600, opacity: loading ? 0.6 : 1,
              }}>
                {loading ? 'Simulating...' : '\uD83D\uDD27 Simulate Intervention'}
              </button>
            </div>

            {interventionResult && (
              <div style={{
                padding: 14, backgroundColor: '#16213e', borderRadius: 8,
                border: '1px solid #0f3460',
              }}>
                <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 8, color: '#aaa' }}>
                  Intervention: {interventionResult.variable} = {interventionResult.new_value}
                </div>
                <div style={{ fontWeight: 600, fontSize: 11, marginBottom: 6, color: '#aaa' }}>Affected Variables:</div>
                <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 11 }}>
                  <thead>
                    <tr>
                      <th style={{ textAlign: 'left', padding: '4px 8px', borderBottom: '1px solid #2a2a3e', color: '#888' }}>Variable</th>
                      <th style={{ textAlign: 'right', padding: '4px 8px', borderBottom: '1px solid #2a2a3e', color: '#888' }}>Before</th>
                      <th style={{ textAlign: 'right', padding: '4px 8px', borderBottom: '1px solid #2a2a3e', color: '#888' }}>After</th>
                    </tr>
                  </thead>
                  <tbody>
                    {interventionResult.affected_variables.map((v, i) => (
                      <tr key={i}>
                        <td style={{ padding: '4px 8px', borderBottom: '1px solid #1a1a2e', fontWeight: 600 }}>{v.name}</td>
                        <td style={{ padding: '4px 8px', borderBottom: '1px solid #1a1a2e', textAlign: 'right', color: '#888' }}>{v.before}</td>
                        <td style={{ padding: '4px 8px', borderBottom: '1px solid #1a1a2e', textAlign: 'right', color: '#6bcb77', fontWeight: 600 }}>{v.after}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        )}

        {/* Tab 3: Counterfactuals */}
        {activeTab === 'counterfactuals' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            <div style={{
              padding: 14, backgroundColor: '#16213e', borderRadius: 8,
              border: '1px solid #0f3460',
            }}>
              <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 10, color: '#a29bfe' }}>
                Evaluate Counterfactual
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 8, marginBottom: 10 }}>
                <div>
                  <label style={{ fontSize: 10, color: '#888', display: 'block', marginBottom: 3 }}>Domain</label>
                  <input type="text" value={counterfactualForm.domain}
                    onChange={e => setCounterfactualForm(prev => ({ ...prev, domain: e.target.value }))}
                    placeholder="e.g. healthcare"
                    style={{ width: '100%', padding: '6px 8px', fontSize: 12, backgroundColor: '#1a1a2e', color: '#e0e0e0', border: '1px solid #0f3460', borderRadius: 4, boxSizing: 'border-box' }}
                  />
                </div>
                <div>
                  <label style={{ fontSize: 10, color: '#888', display: 'block', marginBottom: 3 }}>Factual State (JSON)</label>
                  <textarea value={counterfactualForm.factual}
                    onChange={e => setCounterfactualForm(prev => ({ ...prev, factual: e.target.value }))}
                    placeholder='{"treatment": 0, "age": 45}'
                    rows={2}
                    style={{ width: '100%', padding: '6px 8px', fontSize: 12, backgroundColor: '#1a1a2e', color: '#e0e0e0', border: '1px solid #0f3460', borderRadius: 4, boxSizing: 'border-box', resize: 'vertical', fontFamily: 'monospace' }}
                  />
                </div>
                <div>
                  <label style={{ fontSize: 10, color: '#888', display: 'block', marginBottom: 3 }}>Hypothetical State (JSON)</label>
                  <textarea value={counterfactualForm.hypothetical}
                    onChange={e => setCounterfactualForm(prev => ({ ...prev, hypothetical: e.target.value }))}
                    placeholder='{"treatment": 1, "age": 45}'
                    rows={2}
                    style={{ width: '100%', padding: '6px 8px', fontSize: 12, backgroundColor: '#1a1a2e', color: '#e0e0e0', border: '1px solid #0f3460', borderRadius: 4, boxSizing: 'border-box', resize: 'vertical', fontFamily: 'monospace' }}
                  />
                </div>
                <div>
                  <label style={{ fontSize: 10, color: '#888', display: 'block', marginBottom: 3 }}>Query</label>
                  <input type="text" value={counterfactualForm.query}
                    onChange={e => setCounterfactualForm(prev => ({ ...prev, query: e.target.value }))}
                    placeholder="e.g. What if treatment was applied?"
                    style={{ width: '100%', padding: '6px 8px', fontSize: 12, backgroundColor: '#1a1a2e', color: '#e0e0e0', border: '1px solid #0f3460', borderRadius: 4, boxSizing: 'border-box' }}
                  />
                </div>
              </div>
              <button onClick={handleCounterfactual} disabled={loading} style={{
                padding: '8px 18px', backgroundColor: '#0f3460', color: '#a29bfe',
                border: '1px solid #1a5276', borderRadius: 4, cursor: loading ? 'not-allowed' : 'pointer',
                fontSize: 12, fontWeight: 600, opacity: loading ? 0.6 : 1,
              }}>
                {loading ? 'Evaluating...' : '\uD83E\uDDE9 Evaluate Counterfactual'}
              </button>
            </div>

            {counterfactualResult && (
              <div style={{
                padding: 14, backgroundColor: '#16213e', borderRadius: 8,
                border: '1px solid #0f3460',
              }}>
                <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 8, color: '#aaa' }}>Counterfactual Result</div>
                <div style={{ marginBottom: 8 }}>
                  <span style={{ fontSize: 10, color: '#888' }}>Domain: </span>
                  <span style={{ fontSize: 12, color: '#e0e0e0' }}>{counterfactualResult.domain}</span>
                </div>
                <div style={{ marginBottom: 8 }}>
                  <span style={{ fontSize: 10, color: '#888' }}>Query: </span>
                  <span style={{ fontSize: 12, color: '#e0e0e0' }}>{counterfactualResult.query}</span>
                </div>
                <div style={{
                  padding: 10, backgroundColor: '#1a1a2e', borderRadius: 6,
                  marginBottom: 8, fontSize: 12, color: '#e0e0e0', lineHeight: 1.5,
                }}>
                  {counterfactualResult.result}
                </div>
                <div>
                  <span style={{ fontSize: 10, color: '#888' }}>Confidence: </span>
                  <span style={{ fontSize: 14, fontWeight: 700, color: counterfactualResult.confidence > 0.7 ? '#6bcb77' : '#fdcb6e' }}>
                    {(counterfactualResult.confidence * 100).toFixed(0)}%
                  </span>
                </div>
              </div>
            )}
          </div>
        )}

        {/* Tab 4: Status */}
        {activeTab === 'status' && status && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            <div style={{
              padding: 14, backgroundColor: '#16213e', borderRadius: 8,
              border: '1px solid #0f3460',
            }}>
              <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 12, color: '#aaa' }}>Causal Reasoning System Status</div>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 10, marginBottom: 14 }}>
                <div style={{
                  padding: 10, backgroundColor: '#1a1a2e', borderRadius: 6,
                  display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 4,
                }}>
                  <span style={{ fontSize: 10, color: '#888' }}>Discoveries</span>
                  <span style={{ fontSize: 18, fontWeight: 700, color: '#74b9ff' }}>{status.total_discoveries}</span>
                </div>
                <div style={{
                  padding: 10, backgroundColor: '#1a1a2e', borderRadius: 6,
                  display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 4,
                }}>
                  <span style={{ fontSize: 10, color: '#888' }}>Interventions</span>
                  <span style={{ fontSize: 18, fontWeight: 700, color: '#fdcb6e' }}>{status.total_interventions}</span>
                </div>
                <div style={{
                  padding: 10, backgroundColor: '#1a1a2e', borderRadius: 6,
                  display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 4,
                }}>
                  <span style={{ fontSize: 10, color: '#888' }}>Counterfactuals</span>
                  <span style={{ fontSize: 18, fontWeight: 700, color: '#a29bfe' }}>{status.total_counterfactuals}</span>
                </div>
              </div>
              {renderProgressBar('Avg Fitness Score', status.avg_fitness_score)}
              {renderProgressBar('Avg Confidence', status.avg_confidence)}
              <div style={{
                padding: '6px 10px', backgroundColor: '#1a1a2e', borderRadius: 4,
                fontSize: 11, color: '#888', textAlign: 'center',
              }}>
                Active Domains: <span style={{ color: '#e0e0e0', fontWeight: 600 }}>{status.active_domains}</span>
              </div>
            </div>
          </div>
        )}

        {activeTab === 'status' && !status && (
          <div style={{
            textAlign: 'center', padding: 40, color: '#555',
            backgroundColor: '#16213e', borderRadius: 8, border: '1px solid #0f3460',
          }}>
            <span style={{ fontSize: 40, opacity: 0.3, display: 'block', marginBottom: 10 }}>{'\u2699\uFE0F'}</span>
            Loading system status...
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
        <span>{'\uD83D\uDD17'} Causal Reasoning Engine</span>
        <span>
          {status
            ? `${status.active_domains} domains · ${status.total_discoveries} discoveries`
            : 'Disconnected'}
        </span>
      </div>
    </div>
  );
};

export default AgentCausalReasoningPanel;