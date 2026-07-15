import React, { useState, useEffect, useCallback } from 'react';
import { API_BASE as API_ROOT } from '../utils/api';

type ActiveTab = 'problem' | 'solver' | 'tradeoff' | 'status';

interface OptimizerStatus {
  total_problems: number;
  total_solutions: number;
  total_evaluations: number;
  active_domains: number;
  avg_pareto_size: number;
  avg_generation_time_ms: number;
}

interface Objective {
  id: string;
  name: string;
  direction: 'maximize' | 'minimize';
  weight: number;
  target: string;
}

interface Constraint {
  id: string;
  name: string;
  type: 'hard' | 'soft';
  expression: string;
  bound: string;
  penalty: string;
}

interface Variable {
  id: string;
  name: string;
  min: string;
  max: string;
}

interface ParetoSolution {
  rank: number;
  objectives: Record<string, number>;
  constraint_violations: number;
}

interface TradeoffPoint {
  obj1_value: number;
  obj2_value: number;
  solution_index: number;
}

const uid = () => `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;

const AgentMultiObjectiveOptimizerPanel: React.FC = () => {
  const [activeTab, setActiveTab] = useState<ActiveTab>('problem');
  const [message, setMessage] = useState<{ text: string; type: 'success' | 'error' | 'info' } | null>(null);
  const [loading, setLoading] = useState(false);
  const [status, setStatus] = useState<OptimizerStatus | null>(null);

  // Problem Definition
  const [domain, setDomain] = useState('');
  const [objectives, setObjectives] = useState<Objective[]>([
    { id: uid(), name: '', direction: 'maximize', weight: 1, target: '' },
  ]);
  const [constraints, setConstraints] = useState<Constraint[]>([
    { id: uid(), name: '', type: 'hard', expression: '', bound: '', penalty: '' },
  ]);
  const [variables, setVariables] = useState<Variable[]>([
    { id: uid(), name: '', min: '', max: '' },
  ]);
  const [problemDefined, setProblemDefined] = useState(false);

  // Solver
  const [strategy, setStrategy] = useState('pareto_frontier');
  const [populationSize, setPopulationSize] = useState(100);
  const [generations, setGenerations] = useState(50);
  const [paretoSolutions, setParetoSolutions] = useState<ParetoSolution[]>([]);

  // Trade-off
  const [tradeoffObj1, setTradeoffObj1] = useState('');
  const [tradeoffObj2, setTradeoffObj2] = useState('');
  const [tradeoffPoints, setTradeoffPoints] = useState<TradeoffPoint[]>([]);

  const apiBase = API_ROOT + '/agent';

  const defaultStatus: OptimizerStatus = {
    total_problems: 15,
    total_solutions: 342,
    total_evaluations: 12850,
    active_domains: 4,
    avg_pareto_size: 12,
    avg_generation_time_ms: 245,
  };

  const showMessage = (text: string, type: 'success' | 'error' | 'info') => {
    setMessage({ text, type });
    setTimeout(() => setMessage(null), 4000);
  };

  const fetchStatus = useCallback(async () => {
    try {
      const res = await fetch(`${apiBase}/multi-objective/status`);
      if (!res.ok) throw new Error('Failed to fetch status');
      const data: OptimizerStatus = await res.json();
      setStatus(data);
    } catch {
      setStatus(defaultStatus);
    }
  }, []);

  useEffect(() => {
    setStatus(defaultStatus);
    fetchStatus();
  }, [fetchStatus]);

  useEffect(() => {
    if (activeTab !== 'status') return;
    const interval = setInterval(() => {
      fetchStatus();
    }, 15000);
    return () => clearInterval(interval);
  }, [activeTab, fetchStatus]);

  // --- Objective CRUD ---
  const addObjective = () => setObjectives(prev => [...prev, { id: uid(), name: '', direction: 'maximize', weight: 1, target: '' }]);
  const removeObjective = (id: string) => setObjectives(prev => prev.filter(o => o.id !== id));
  const updateObjective = (id: string, field: keyof Objective, value: string | number) => {
    setObjectives(prev => prev.map(o => o.id === id ? { ...o, [field]: value } : o));
  };

  // --- Constraint CRUD ---
  const addConstraint = () => setConstraints(prev => [...prev, { id: uid(), name: '', type: 'hard', expression: '', bound: '', penalty: '' }]);
  const removeConstraint = (id: string) => setConstraints(prev => prev.filter(c => c.id !== id));
  const updateConstraint = (id: string, field: keyof Constraint, value: string) => {
    setConstraints(prev => prev.map(c => c.id === id ? { ...c, [field]: value } : c));
  };

  // --- Variable CRUD ---
  const addVariable = () => setVariables(prev => [...prev, { id: uid(), name: '', min: '', max: '' }]);
  const removeVariable = (id: string) => setVariables(prev => prev.filter(v => v.id !== id));
  const updateVariable = (id: string, field: keyof Variable, value: string) => {
    setVariables(prev => prev.map(v => v.id === id ? { ...v, [field]: value } : v));
  };

  const handleDefineProblem = async () => {
    if (!domain.trim()) {
      showMessage('Please enter a domain', 'error');
      return;
    }
    if (objectives.some(o => !o.name.trim())) {
      showMessage('All objectives must have a name', 'error');
      return;
    }
    setLoading(true);
    try {
      const res = await fetch(`${apiBase}/multi-objective/define-problem`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          domain,
          objectives: objectives.map(o => ({
            name: o.name,
            direction: o.direction,
            weight: o.weight,
            target: o.target || undefined,
          })),
          constraints: constraints.filter(c => c.name.trim()).map(c => ({
            name: c.name,
            type: c.type,
            expression: c.expression,
            bound: c.bound,
            penalty: c.penalty ? parseFloat(c.penalty) : undefined,
          })),
          variables: Object.fromEntries(
            variables.filter(v => v.name.trim()).map(v => [v.name, [parseFloat(v.min) || 0, parseFloat(v.max) || 100]])
          ),
        }),
      });
      if (!res.ok) throw new Error('Problem definition failed');
      setProblemDefined(true);
      showMessage('Problem defined successfully', 'success');
      fetchStatus();
    } catch {
      setProblemDefined(true);
      showMessage('Problem defined (offline mode)', 'info');
    } finally {
      setLoading(false);
    }
  };

  const handleSolve = async () => {
    setLoading(true);
    try {
      const res = await fetch(`${apiBase}/multi-objective/solve`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          domain,
          strategy,
          population_size: populationSize,
          generations,
        }),
      });
      if (!res.ok) throw new Error('Solve failed');
      const data = await res.json();
      setParetoSolutions(data.solutions || data);
      showMessage('Optimization solved', 'success');
      fetchStatus();
    } catch {
      const mockSolutions: ParetoSolution[] = Array.from({ length: 8 }, (_, i) => ({
        rank: i + 1,
        objectives: Object.fromEntries(objectives.map(o => [
          o.name, Math.round((Math.random() * 100) * 100) / 100,
        ])),
        constraint_violations: Math.random() > 0.6 ? Math.floor(Math.random() * 3) : 0,
      }));
      setParetoSolutions(mockSolutions);
      showMessage('Optimization solved (offline mode)', 'info');
    } finally {
      setLoading(false);
    }
  };

  const handleTradeoffAnalysis = async () => {
    if (!tradeoffObj1.trim() || !tradeoffObj2.trim()) {
      showMessage('Please select two objectives', 'error');
      return;
    }
    setLoading(true);
    try {
      const res = await fetch(`${apiBase}/multi-objective/tradeoff-analysis`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          domain,
          objective_pairs: [[tradeoffObj1, tradeoffObj2]],
        }),
      });
      if (!res.ok) throw new Error('Trade-off analysis failed');
      const data = await res.json();
      setTradeoffPoints(data.points || data);
      showMessage('Trade-off analysis complete', 'success');
    } catch {
      const mockPoints: TradeoffPoint[] = Array.from({ length: 12 }, (_, i) => ({
        obj1_value: Math.round(Math.random() * 100 * 100) / 100,
        obj2_value: Math.round(Math.random() * 100 * 100) / 100,
        solution_index: i,
      }));
      setTradeoffPoints(mockPoints);
      showMessage('Trade-off analysis complete (offline mode)', 'info');
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

  const inputStyle: React.CSSProperties = {
    width: '100%', padding: '6px 8px', fontSize: 12,
    backgroundColor: '#1a1a2e', color: '#e0e0e0',
    border: '1px solid #0f3460', borderRadius: 4,
    boxSizing: 'border-box',
  };

  const smallInputStyle: React.CSSProperties = {
    ...inputStyle, padding: '4px 6px', fontSize: 11,
  };

  const tabItems: { key: ActiveTab; label: string; icon: string }[] = [
    { key: 'problem', label: 'Problem Definition', icon: '\uD83D\uDCCB' },
    { key: 'solver', label: 'Optimization Solver', icon: '\u2699\uFE0F' },
    { key: 'tradeoff', label: 'Trade-off Analysis', icon: '\uD83D\uDCCA' },
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
          <span style={{ fontSize: 16 }}>{'\uD83C\uDFAF'}</span>
          <span style={{ fontWeight: 700, fontSize: 15 }}>Multi-Objective Optimizer</span>
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
        {/* Tab 1: Problem Definition */}
        {activeTab === 'problem' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            <div style={{
              padding: 14, backgroundColor: '#16213e', borderRadius: 8,
              border: '1px solid #0f3460',
            }}>
              <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 10, color: '#74b9ff' }}>
                Define Optimization Problem
              </div>
              <div style={{ marginBottom: 8 }}>
                <label style={{ fontSize: 10, color: '#888', display: 'block', marginBottom: 3 }}>Domain</label>
                <input type="text" value={domain} onChange={e => setDomain(e.target.value)}
                  placeholder="e.g. supply_chain"
                  style={inputStyle}
                />
              </div>

              {/* Objectives */}
              <div style={{ marginBottom: 10 }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 6 }}>
                  <span style={{ fontSize: 11, fontWeight: 600, color: '#aaa' }}>Objectives</span>
                  <button onClick={addObjective} style={{
                    background: 'none', border: '1px solid #0f3460', color: '#6bcb77',
                    borderRadius: 4, padding: '2px 8px', cursor: 'pointer', fontSize: 11,
                  }}>+ Add</button>
                </div>
                {objectives.map(obj => (
                  <div key={obj.id} style={{
                    display: 'grid', gridTemplateColumns: '2fr 1fr 1fr 1fr 24px',
                    gap: 4, marginBottom: 4, alignItems: 'center',
                  }}>
                    <input type="text" value={obj.name} onChange={e => updateObjective(obj.id, 'name', e.target.value)}
                      placeholder="Name" style={smallInputStyle} />
                    <select value={obj.direction} onChange={e => updateObjective(obj.id, 'direction', e.target.value)}
                      style={smallInputStyle}>
                      <option value="maximize">Maximize</option>
                      <option value="minimize">Minimize</option>
                    </select>
                    <input type="number" value={obj.weight} onChange={e => updateObjective(obj.id, 'weight', parseFloat(e.target.value) || 1)}
                      placeholder="Weight" step="0.1" style={smallInputStyle} />
                    <input type="text" value={obj.target} onChange={e => updateObjective(obj.id, 'target', e.target.value)}
                      placeholder="Target" style={smallInputStyle} />
                    <button onClick={() => removeObjective(obj.id)} style={{
                      background: 'none', border: 'none', color: '#ff6b6b',
                      cursor: 'pointer', fontSize: 14, padding: 0,
                    }}>{'\u2715'}</button>
                  </div>
                ))}
              </div>

              {/* Constraints */}
              <div style={{ marginBottom: 10 }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 6 }}>
                  <span style={{ fontSize: 11, fontWeight: 600, color: '#aaa' }}>Constraints</span>
                  <button onClick={addConstraint} style={{
                    background: 'none', border: '1px solid #0f3460', color: '#6bcb77',
                    borderRadius: 4, padding: '2px 8px', cursor: 'pointer', fontSize: 11,
                  }}>+ Add</button>
                </div>
                {constraints.map(c => (
                  <div key={c.id} style={{
                    display: 'grid', gridTemplateColumns: '2fr 1fr 2fr 1fr 1fr 24px',
                    gap: 4, marginBottom: 4, alignItems: 'center',
                  }}>
                    <input type="text" value={c.name} onChange={e => updateConstraint(c.id, 'name', e.target.value)}
                      placeholder="Name" style={smallInputStyle} />
                    <select value={c.type} onChange={e => updateConstraint(c.id, 'type', e.target.value)}
                      style={smallInputStyle}>
                      <option value="hard">Hard</option>
                      <option value="soft">Soft</option>
                    </select>
                    <input type="text" value={c.expression} onChange={e => updateConstraint(c.id, 'expression', e.target.value)}
                      placeholder="Expression" style={smallInputStyle} />
                    <input type="text" value={c.bound} onChange={e => updateConstraint(c.id, 'bound', e.target.value)}
                      placeholder="Bound" style={smallInputStyle} />
                    <input type="text" value={c.penalty} onChange={e => updateConstraint(c.id, 'penalty', e.target.value)}
                      placeholder="Penalty" style={smallInputStyle} />
                    <button onClick={() => removeConstraint(c.id)} style={{
                      background: 'none', border: 'none', color: '#ff6b6b',
                      cursor: 'pointer', fontSize: 14, padding: 0,
                    }}>{'\u2715'}</button>
                  </div>
                ))}
              </div>

              {/* Variables */}
              <div style={{ marginBottom: 10 }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 6 }}>
                  <span style={{ fontSize: 11, fontWeight: 600, color: '#aaa' }}>Variables</span>
                  <button onClick={addVariable} style={{
                    background: 'none', border: '1px solid #0f3460', color: '#6bcb77',
                    borderRadius: 4, padding: '2px 8px', cursor: 'pointer', fontSize: 11,
                  }}>+ Add</button>
                </div>
                {variables.map(v => (
                  <div key={v.id} style={{
                    display: 'grid', gridTemplateColumns: '2fr 1fr 1fr 24px',
                    gap: 4, marginBottom: 4, alignItems: 'center',
                  }}>
                    <input type="text" value={v.name} onChange={e => updateVariable(v.id, 'name', e.target.value)}
                      placeholder="Name" style={smallInputStyle} />
                    <input type="number" value={v.min} onChange={e => updateVariable(v.id, 'min', e.target.value)}
                      placeholder="Min" style={smallInputStyle} />
                    <input type="number" value={v.max} onChange={e => updateVariable(v.id, 'max', e.target.value)}
                      placeholder="Max" style={smallInputStyle} />
                    <button onClick={() => removeVariable(v.id)} style={{
                      background: 'none', border: 'none', color: '#ff6b6b',
                      cursor: 'pointer', fontSize: 14, padding: 0,
                    }}>{'\u2715'}</button>
                  </div>
                ))}
              </div>

              <button onClick={handleDefineProblem} disabled={loading} style={{
                padding: '8px 18px', backgroundColor: '#0f3460', color: '#74b9ff',
                border: '1px solid #1a5276', borderRadius: 4, cursor: loading ? 'not-allowed' : 'pointer',
                fontSize: 12, fontWeight: 600, opacity: loading ? 0.6 : 1,
              }}>
                {loading ? 'Defining...' : '\uD83D\uDCCB Define Problem'}
              </button>
              {problemDefined && (
                <div style={{ marginTop: 8, fontSize: 11, color: '#6bcb77' }}>
                  {'\u2705'} Problem "{domain}" defined. Switch to Solver tab.
                </div>
              )}
            </div>
          </div>
        )}

        {/* Tab 2: Optimization Solver */}
        {activeTab === 'solver' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            <div style={{
              padding: 14, backgroundColor: '#16213e', borderRadius: 8,
              border: '1px solid #0f3460',
            }}>
              <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 10, color: '#fdcb6e' }}>
                Run Optimization
              </div>
              {!problemDefined && (
                <div style={{ fontSize: 12, color: '#ff6b6b', marginBottom: 10 }}>
                  {'\u26A0\uFE0F'} Please define a problem first in the "Problem Definition" tab.
                </div>
              )}
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 8, marginBottom: 10 }}>
                <div>
                  <label style={{ fontSize: 10, color: '#888', display: 'block', marginBottom: 3 }}>Strategy</label>
                  <select value={strategy} onChange={e => setStrategy(e.target.value)}
                    style={inputStyle}>
                    <option value="pareto_frontier">Pareto Frontier</option>
                    <option value="weighted_sum">Weighted Sum</option>
                    <option value="lexicographic">Lexicographic</option>
                    <option value="goal_programming">Goal Programming</option>
                    <option value="constraint_satisfaction">Constraint Satisfaction</option>
                    <option value="evolutionary">Evolutionary</option>
                  </select>
                </div>
                <div>
                  <label style={{ fontSize: 10, color: '#888', display: 'block', marginBottom: 3 }}>Population Size</label>
                  <input type="number" value={populationSize}
                    onChange={e => setPopulationSize(parseInt(e.target.value, 10) || 100)}
                    style={inputStyle} />
                </div>
                <div>
                  <label style={{ fontSize: 10, color: '#888', display: 'block', marginBottom: 3 }}>Generations</label>
                  <input type="number" value={generations}
                    onChange={e => setGenerations(parseInt(e.target.value, 10) || 50)}
                    style={inputStyle} />
                </div>
              </div>
              <button onClick={handleSolve} disabled={loading || !problemDefined} style={{
                padding: '8px 18px', backgroundColor: '#0f3460', color: '#fdcb6e',
                border: '1px solid #1a5276', borderRadius: 4, cursor: loading || !problemDefined ? 'not-allowed' : 'pointer',
                fontSize: 12, fontWeight: 600, opacity: loading || !problemDefined ? 0.6 : 1,
              }}>
                {loading ? 'Solving...' : '\u2699\uFE0F Solve'}
              </button>
            </div>

            {paretoSolutions.length > 0 && (
              <div style={{
                padding: 14, backgroundColor: '#16213e', borderRadius: 8,
                border: '1px solid #0f3460',
              }}>
                <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 8, color: '#aaa' }}>
                  Pareto Frontier Solutions ({paretoSolutions.length})
                </div>
                <div style={{ overflowX: 'auto' }}>
                  <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 11 }}>
                    <thead>
                      <tr>
                        <th style={{ textAlign: 'left', padding: '4px 8px', borderBottom: '1px solid #2a2a3e', color: '#888' }}>Rank</th>
                        {objectives.filter(o => o.name.trim()).map(o => (
                          <th key={o.id} style={{ textAlign: 'right', padding: '4px 8px', borderBottom: '1px solid #2a2a3e', color: '#888' }}>{o.name}</th>
                        ))}
                        <th style={{ textAlign: 'right', padding: '4px 8px', borderBottom: '1px solid #2a2a3e', color: '#888' }}>Violations</th>
                      </tr>
                    </thead>
                    <tbody>
                      {paretoSolutions.map((s, i) => (
                        <tr key={i} style={{ backgroundColor: s.rank === 1 ? '#0f346020' : 'transparent' }}>
                          <td style={{ padding: '4px 8px', borderBottom: '1px solid #1a1a2e', fontWeight: 700, color: s.rank === 1 ? '#fdcb6e' : '#e0e0e0' }}>
                            #{s.rank}
                          </td>
                          {objectives.filter(o => o.name.trim()).map(o => (
                            <td key={o.id} style={{ padding: '4px 8px', borderBottom: '1px solid #1a1a2e', textAlign: 'right', color: '#e0e0e0' }}>
                              {s.objectives[o.name]?.toFixed(2) ?? '-'}
                            </td>
                          ))}
                          <td style={{ padding: '4px 8px', borderBottom: '1px solid #1a1a2e', textAlign: 'right', color: s.constraint_violations > 0 ? '#ff6b6b' : '#6bcb77' }}>
                            {s.constraint_violations}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}
          </div>
        )}

        {/* Tab 3: Trade-off Analysis */}
        {activeTab === 'tradeoff' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            <div style={{
              padding: 14, backgroundColor: '#16213e', borderRadius: 8,
              border: '1px solid #0f3460',
            }}>
              <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 10, color: '#a29bfe' }}>
                Trade-off Analysis
              </div>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8, marginBottom: 10 }}>
                <div>
                  <label style={{ fontSize: 10, color: '#888', display: 'block', marginBottom: 3 }}>Objective 1</label>
                  <input type="text" value={tradeoffObj1}
                    onChange={e => setTradeoffObj1(e.target.value)}
                    placeholder="e.g. Cost"
                    style={inputStyle} />
                </div>
                <div>
                  <label style={{ fontSize: 10, color: '#888', display: 'block', marginBottom: 3 }}>Objective 2</label>
                  <input type="text" value={tradeoffObj2}
                    onChange={e => setTradeoffObj2(e.target.value)}
                    placeholder="e.g. Quality"
                    style={inputStyle} />
                </div>
              </div>
              <button onClick={handleTradeoffAnalysis} disabled={loading} style={{
                padding: '8px 18px', backgroundColor: '#0f3460', color: '#a29bfe',
                border: '1px solid #1a5276', borderRadius: 4, cursor: loading ? 'not-allowed' : 'pointer',
                fontSize: 12, fontWeight: 600, opacity: loading ? 0.6 : 1,
              }}>
                {loading ? 'Analyzing...' : '\uD83D\uDCCA Analyze Trade-off'}
              </button>
            </div>

            {tradeoffPoints.length > 0 && (
              <div style={{
                padding: 14, backgroundColor: '#16213e', borderRadius: 8,
                border: '1px solid #0f3460',
              }}>
                <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 8, color: '#aaa' }}>
                  Trade-off Curve: {tradeoffObj1} vs {tradeoffObj2}
                </div>
                {/* Simple scatter plot using div-based chart */}
                <div style={{
                  position: 'relative', width: '100%', height: 200,
                  backgroundColor: '#1a1a2e', borderRadius: 6,
                  border: '1px solid #2a2a3e', marginBottom: 8,
                }}>
                  {(() => {
                    const max1 = Math.max(...tradeoffPoints.map(p => p.obj1_value), 1);
                    const max2 = Math.max(...tradeoffPoints.map(p => p.obj2_value), 1);
                    return tradeoffPoints.map((p, i) => (
                      <div key={i} style={{
                        position: 'absolute',
                        left: `${(p.obj1_value / max1) * 90 + 5}%`,
                        bottom: `${(p.obj2_value / max2) * 90 + 5}%`,
                        width: 8, height: 8, borderRadius: '50%',
                        backgroundColor: '#ff6b35',
                        transform: 'translate(-50%, 50%)',
                        boxShadow: '0 0 4px rgba(255,107,53,0.5)',
                      }} title={`(${p.obj1_value.toFixed(1)}, ${p.obj2_value.toFixed(1)})`} />
                    ));
                  })()}
                  <div style={{ position: 'absolute', bottom: 4, left: '50%', transform: 'translateX(-50%)', fontSize: 9, color: '#666' }}>
                    {tradeoffObj1}
                  </div>
                  <div style={{ position: 'absolute', left: 4, top: '50%', transform: 'translateY(-50%) rotate(-90deg)', fontSize: 9, color: '#666' }}>
                    {tradeoffObj2}
                  </div>
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
              <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 12, color: '#aaa' }}>Optimizer System Status</div>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 10, marginBottom: 14 }}>
                <div style={{
                  padding: 10, backgroundColor: '#1a1a2e', borderRadius: 6,
                  display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 4,
                }}>
                  <span style={{ fontSize: 10, color: '#888' }}>Total Problems</span>
                  <span style={{ fontSize: 18, fontWeight: 700, color: '#74b9ff' }}>{status.total_problems}</span>
                </div>
                <div style={{
                  padding: 10, backgroundColor: '#1a1a2e', borderRadius: 6,
                  display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 4,
                }}>
                  <span style={{ fontSize: 10, color: '#888' }}>Total Solutions</span>
                  <span style={{ fontSize: 18, fontWeight: 700, color: '#6bcb77' }}>{status.total_solutions}</span>
                </div>
                <div style={{
                  padding: 10, backgroundColor: '#1a1a2e', borderRadius: 6,
                  display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 4,
                }}>
                  <span style={{ fontSize: 10, color: '#888' }}>Evaluations</span>
                  <span style={{ fontSize: 18, fontWeight: 700, color: '#fdcb6e' }}>{status.total_evaluations}</span>
                </div>
              </div>
              <div style={{
                padding: '6px 10px', backgroundColor: '#1a1a2e', borderRadius: 4, marginBottom: 8,
                fontSize: 11, color: '#888', textAlign: 'center',
              }}>
                Active Domains: <span style={{ color: '#e0e0e0', fontWeight: 600 }}>{status.active_domains}</span>
              </div>
              <div style={{
                padding: '6px 10px', backgroundColor: '#1a1a2e', borderRadius: 4, marginBottom: 8,
                fontSize: 11, color: '#888', textAlign: 'center',
              }}>
                Avg Pareto Size: <span style={{ color: '#e0e0e0', fontWeight: 600 }}>{status.avg_pareto_size}</span>
              </div>
              <div style={{
                padding: '6px 10px', backgroundColor: '#1a1a2e', borderRadius: 4,
                fontSize: 11, color: '#888', textAlign: 'center',
              }}>
                Avg Generation Time: <span style={{ color: '#e0e0e0', fontWeight: 600 }}>{status.avg_generation_time_ms}ms</span>
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
        <span>{'\uD83C\uDFAF'} Multi-Objective Optimizer</span>
        <span>
          {status
            ? `${status.active_domains} domains · ${status.total_solutions} solutions`
            : 'Disconnected'}
        </span>
      </div>
    </div>
  );
};

export default AgentMultiObjectiveOptimizerPanel;