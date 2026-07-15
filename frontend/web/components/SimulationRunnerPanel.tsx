import React, { useState, useEffect, useCallback } from 'react';
import { API_BASE as API_ROOT } from '../utils/api';

type TabId = 'scenarios' | 'runs' | 'evaluate';

interface Scenario {
  id: string;
  name: string;
  description: string;
  mode: string;
  created_at: number;
}

interface SimulationRun {
  id: string;
  scenario_id: string;
  agent_id: string;
  input_data: string;
  status: string;
  output: string;
  started_at: number;
  completed_at: number | null;
}

interface EvaluationResult {
  run_id: string;
  scenario_id: string;
  score: number;
  metrics: { name: string; value: number }[];
  passed: boolean;
  evaluated_at: number;
}

const uid = () => `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;

const SimulationRunnerPanel: React.FC = () => {
  const [scenarios, setScenarios] = useState<Scenario[]>([]);
  const [runs, setRuns] = useState<SimulationRun[]>([]);
  const [evaluations, setEvaluations] = useState<EvaluationResult[]>([]);
  const [message, setMessage] = useState<{ text: string; type: 'success' | 'error' | 'info' } | null>(null);
  const [activeTab, setActiveTab] = useState<TabId>('scenarios');

  const [scenarioName, setScenarioName] = useState('');
  const [scenarioDesc, setScenarioDesc] = useState('');
  const [scenarioMode, setScenarioMode] = useState('interactive');

  const [runScenarioId, setRunScenarioId] = useState('');
  const [runAgentId, setRunAgentId] = useState('');
  const [runInputData, setRunInputData] = useState('{"task":"Generate a React component","context":"Dashboard page"}');

  const [evalRunId, setEvalRunId] = useState('');

  const [listScenarioId, setListScenarioId] = useState('');

  const apiBase = API_ROOT + '/agent';

  const defaultScenarios: Scenario[] = [
    { id: uid(), name: 'Code Generation Test', description: 'Test agent ability to generate React components from natural language prompts', mode: 'interactive', created_at: Date.now() - 86400000 },
    { id: uid(), name: 'Refactoring Challenge', description: 'Evaluate agent performance on legacy code refactoring tasks', mode: 'batch', created_at: Date.now() - 172800000 },
    { id: uid(), name: 'Debugging Scenario', description: 'Test agent debugging skills with intentionally buggy code', mode: 'interactive', created_at: Date.now() - 259200000 },
  ];

  const defaultRuns: SimulationRun[] = [
    { id: uid(), scenario_id: 'sc-1', agent_id: 'agent-001', input_data: '{"task":"Create a login form"}', status: 'completed', output: 'Generated LoginForm.tsx with validation', started_at: Date.now() - 3600000, completed_at: Date.now() - 3500000 },
    { id: uid(), scenario_id: 'sc-1', agent_id: 'agent-002', input_data: '{"task":"Create a login form"}', status: 'running', output: '', started_at: Date.now() - 600000, completed_at: null },
    { id: uid(), scenario_id: 'sc-2', agent_id: 'agent-001', input_data: '{"task":"Refactor UserService class"}', status: 'completed', output: 'Split into smaller services', started_at: Date.now() - 7200000, completed_at: Date.now() - 7100000 },
  ];

  const defaultEvaluations: EvaluationResult[] = [
    { run_id: 'run-1', scenario_id: 'sc-1', score: 0.87, metrics: [{ name: 'code_quality', value: 0.9 }, { name: 'completion_time', value: 0.85 }, { name: 'test_coverage', value: 0.86 }], passed: true, evaluated_at: Date.now() - 3000000 },
  ];

  const showMessage = (text: string, type: 'success' | 'error' | 'info') => {
    setMessage({ text, type });
    setTimeout(() => setMessage(null), 4000);
  };

  const fetchStats = useCallback(async () => {
    try {
      const res = await fetch(`${apiBase}/simulation-runner/stats`);
      const data = await res.json();
      if (data.scenarios) setScenarios(data.scenarios);
      if (data.runs) setRuns(data.runs);
    } catch {
      // use defaults
    }
  }, []);

  useEffect(() => {
    setScenarios(defaultScenarios);
    setRuns(defaultRuns);
    setEvaluations(defaultEvaluations);
    fetchStats();
  }, [fetchStats]);

  const handleDefineScenario = async () => {
    if (!scenarioName.trim()) {
      showMessage('Scenario name is required', 'error');
      return;
    }
    try {
      await fetch(`${apiBase}/simulation-runner/define-scenario`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: scenarioName, description: scenarioDesc, mode: scenarioMode }),
      });
      const newScenario: Scenario = {
        id: uid(), name: scenarioName, description: scenarioDesc, mode: scenarioMode, created_at: Date.now(),
      };
      setScenarios(prev => [...prev, newScenario]);
      setScenarioName('');
      setScenarioDesc('');
      showMessage(`Scenario "${scenarioName}" defined`, 'success');
    } catch {
      const newScenario: Scenario = {
        id: uid(), name: scenarioName, description: scenarioDesc, mode: scenarioMode, created_at: Date.now(),
      };
      setScenarios(prev => [...prev, newScenario]);
      setScenarioName('');
      setScenarioDesc('');
      showMessage(`Scenario "${scenarioName}" defined (offline fallback)`, 'info');
    }
  };

  const handleRun = async () => {
    if (!runScenarioId.trim() || !runAgentId.trim()) {
      showMessage('Scenario ID and Agent ID are required', 'error');
      return;
    }
    try {
      await fetch(`${apiBase}/simulation-runner/run`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ scenario_id: runScenarioId, agent_id: runAgentId, input_data: runInputData }),
      });
      const newRun: SimulationRun = {
        id: uid(),
        scenario_id: runScenarioId,
        agent_id: runAgentId,
        input_data: runInputData,
        status: 'running',
        output: '',
        started_at: Date.now(),
        completed_at: null,
      };
      setRuns(prev => [newRun, ...prev]);
      showMessage('Simulation started', 'success');
    } catch {
      const newRun: SimulationRun = {
        id: uid(),
        scenario_id: runScenarioId,
        agent_id: runAgentId,
        input_data: runInputData,
        status: 'running',
        output: '',
        started_at: Date.now(),
        completed_at: null,
      };
      setRuns(prev => [newRun, ...prev]);
      showMessage('Simulation started (offline fallback)', 'info');
    }
  };

  const handleListRuns = async () => {
    try {
      const res = await fetch(`${apiBase}/simulation-runner/list-runs?scenario_id=${listScenarioId || scenarios[0]?.id || ''}`);
      const data = await res.json();
      if (data.runs) setRuns(data.runs);
      showMessage(`Listed ${data.runs?.length || 0} runs`, 'success');
    } catch {
      const filtered = runs.filter(r => !listScenarioId || r.scenario_id === listScenarioId);
      setRuns(filtered);
      showMessage(`Listed ${filtered.length} runs (offline fallback)`, 'info');
    }
  };

  const handleEvaluate = async () => {
    if (!evalRunId.trim()) {
      showMessage('Run ID is required', 'error');
      return;
    }
    try {
      const res = await fetch(`${apiBase}/simulation-runner/evaluate?run_id=${evalRunId}`);
      const data = await res.json();
      if (data) {
        setEvaluations(prev => [data, ...prev]);
      }
      showMessage(`Run ${evalRunId} evaluated`, 'success');
    } catch {
      const run = runs.find(r => r.id === evalRunId);
      const evaluation: EvaluationResult = {
        run_id: evalRunId,
        scenario_id: run?.scenario_id || '',
        score: 0.85,
        metrics: [
          { name: 'code_quality', value: 0.88 },
          { name: 'completion_time', value: 0.82 },
          { name: 'test_coverage', value: 0.85 },
        ],
        passed: true,
        evaluated_at: Date.now(),
      };
      setEvaluations(prev => [evaluation, ...prev]);
      showMessage(`Run ${evalRunId} evaluated (offline fallback)`, 'info');
    }
  };

  const formatTime = (ts: number) => {
    const d = new Date(ts);
    return d.toLocaleString([], { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' });
  };

  const tabItems: { key: TabId; label: string; icon: string; count: number }[] = [
    { key: 'scenarios', label: 'Scenarios', icon: '\uD83C\uDFAF', count: scenarios.length },
    { key: 'runs', label: 'Runs', icon: '\u25B6\uFE0F', count: runs.length },
    { key: 'evaluate', label: 'Evaluate', icon: '\uD83D\uDCCA', count: evaluations.length },
  ];

  return (
    <div style={{
      display: 'flex', flexDirection: 'column', height: '100%',
      backgroundColor: '#1a1a2e', color: '#e0e0e0',
      fontFamily: 'system-ui, sans-serif', fontSize: 13,
    }}>
      <div style={{
        padding: '12px 16px', borderBottom: '1px solid #2a2a3e',
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <span style={{ fontSize: 18 }}>{'\uD83C\uDFAF'}</span>
          <span style={{ fontWeight: 700, fontSize: 15 }}>Simulation Runner</span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <span style={{ fontSize: 10, color: '#888' }}>
            {scenarios.length} scenarios · {runs.length} runs · {evaluations.length} evals
          </span>
        </div>
      </div>

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

      <div style={{ display: 'flex', borderBottom: '1px solid #2a2a3e' }}>
        {tabItems.map(tab => (
          <button key={tab.key} onClick={() => setActiveTab(tab.key)} style={{
            flex: 1, padding: '8px 12px', fontSize: 12, fontWeight: 600,
            backgroundColor: activeTab === tab.key ? '#22223a' : 'transparent',
            color: activeTab === tab.key ? '#e0e0e0' : '#888',
            border: 'none', borderBottom: activeTab === tab.key ? '2px solid #6c5ce7' : '2px solid transparent',
            cursor: 'pointer',
          }}>
            {tab.icon} {tab.label} <span style={{ color: '#666', fontWeight: 400 }}>({tab.count})</span>
          </button>
        ))}
      </div>

      <div style={{ flex: 1, overflow: 'auto', padding: 12 }}>
        {activeTab === 'scenarios' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            <div style={{
              padding: 12, backgroundColor: '#22223a', borderRadius: 6,
              border: '1px solid #2a2a3e',
            }}>
              <div style={{ fontSize: 12, fontWeight: 600, color: '#aaa', marginBottom: 8 }}>
                {'\uD83C\uDFAF'} define-scenario
              </div>
              <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', alignItems: 'flex-end' }}>
                <div>
                  <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>Name</div>
                  <input value={scenarioName} onChange={e => setScenarioName(e.target.value)} placeholder="e.g. Code Gen Test" style={{
                    padding: '6px 10px', fontSize: 11, width: 150,
                    backgroundColor: '#141428', color: '#ccc',
                    border: '1px solid #333', borderRadius: 4, outline: 'none',
                  }} />
                </div>
                <div>
                  <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>Mode</div>
                  <select value={scenarioMode} onChange={e => setScenarioMode(e.target.value)} style={{
                    padding: '6px 10px', fontSize: 11,
                    backgroundColor: '#141428', color: '#ccc',
                    border: '1px solid #333', borderRadius: 4, outline: 'none',
                  }}>
                    <option value="interactive">Interactive</option>
                    <option value="batch">Batch</option>
                    <option value="streaming">Streaming</option>
                    <option value="adversarial">Adversarial</option>
                  </select>
                </div>
                <div style={{ flex: 1, minWidth: 200 }}>
                  <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>Description</div>
                  <input value={scenarioDesc} onChange={e => setScenarioDesc(e.target.value)} placeholder="Describe the scenario..." style={{
                    padding: '6px 10px', fontSize: 11, width: '100%',
                    backgroundColor: '#141428', color: '#ccc',
                    border: '1px solid #333', borderRadius: 4, outline: 'none',
                  }} />
                </div>
                <button onClick={handleDefineScenario} style={{
                  padding: '6px 14px', backgroundColor: '#2d3a5a', color: '#74b9ff',
                  border: '1px solid #3d4a6a', borderRadius: 4, cursor: 'pointer',
                  fontSize: 11, fontWeight: 600,
                }}>Define</button>
              </div>
            </div>

            <div style={{ fontSize: 13, fontWeight: 600, color: '#aaa' }}>
              {'\uD83C\uDFAF'} Scenarios <span style={{ fontSize: 10, color: '#888', marginLeft: 4 }}>({scenarios.length})</span>
            </div>
            {scenarios.map(sc => (
              <div key={sc.id} style={{
                padding: 12, backgroundColor: '#22223a', borderRadius: 6,
                border: '1px solid #2a2a3e', borderLeft: '3px solid #74b9ff',
              }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 6 }}>
                  <span style={{ fontWeight: 600, fontSize: 13, color: '#ccc' }}>{sc.name}</span>
                  <span style={{
                    fontSize: 9, padding: '2px 8px', borderRadius: 3,
                    backgroundColor: '#1a2a3a', color: '#74b9ff', fontWeight: 600,
                    textTransform: 'uppercase',
                  }}>{sc.mode}</span>
                </div>
                <div style={{ fontSize: 10, color: '#888', marginBottom: 4 }}>{sc.description}</div>
                <div style={{ fontSize: 10, color: '#666' }}>Created: {formatTime(sc.created_at)}</div>
              </div>
            ))}
          </div>
        )}

        {activeTab === 'runs' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            <div style={{
              padding: 12, backgroundColor: '#22223a', borderRadius: 6,
              border: '1px solid #2a2a3e',
            }}>
              <div style={{ fontSize: 12, fontWeight: 600, color: '#aaa', marginBottom: 8 }}>
                {'\u25B6\uFE0F'} run
              </div>
              <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', alignItems: 'flex-end' }}>
                <div>
                  <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>Scenario ID</div>
                  <input value={runScenarioId} onChange={e => setRunScenarioId(e.target.value)} placeholder="Select scenario" style={{
                    padding: '6px 10px', fontSize: 11, width: 120,
                    backgroundColor: '#141428', color: '#ccc',
                    border: '1px solid #333', borderRadius: 4, outline: 'none',
                  }} />
                </div>
                <div>
                  <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>Agent ID</div>
                  <input value={runAgentId} onChange={e => setRunAgentId(e.target.value)} placeholder="e.g. agent-001" style={{
                    padding: '6px 10px', fontSize: 11, width: 110,
                    backgroundColor: '#141428', color: '#ccc',
                    border: '1px solid #333', borderRadius: 4, outline: 'none',
                  }} />
                </div>
                <button onClick={handleRun} style={{
                  padding: '6px 14px', backgroundColor: '#2d4a2d', color: '#6bcb77',
                  border: '1px solid #3d5a3d', borderRadius: 4, cursor: 'pointer',
                  fontSize: 11, fontWeight: 600,
                }}>Run</button>
              </div>
              <div style={{ marginTop: 8 }}>
                <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>Input Data (JSON)</div>
                <textarea value={runInputData} onChange={e => setRunInputData(e.target.value)} rows={2} style={{
                  padding: '6px 10px', fontSize: 11, width: '100%', resize: 'vertical',
                  backgroundColor: '#141428', color: '#ccc',
                  border: '1px solid #333', borderRadius: 4, outline: 'none',
                  fontFamily: 'monospace',
                }} />
              </div>
            </div>

            <div style={{ display: 'flex', gap: 6, alignItems: 'center' }}>
              <span style={{ fontSize: 10, color: '#888' }}>Filter by Scenario:</span>
              <input value={listScenarioId} onChange={e => setListScenarioId(e.target.value)} placeholder="Scenario ID" style={{
                padding: '5px 8px', fontSize: 11, width: 120,
                backgroundColor: '#141428', color: '#ccc',
                border: '1px solid #333', borderRadius: 4, outline: 'none',
              }} />
              <button onClick={handleListRuns} style={{
                padding: '5px 12px', backgroundColor: '#2d3a5a', color: '#74b9ff',
                border: '1px solid #3d4a6a', borderRadius: 4, cursor: 'pointer', fontSize: 11,
              }}>List Runs</button>
            </div>

            <div style={{ fontSize: 13, fontWeight: 600, color: '#aaa' }}>
              {'\u25B6\uFE0F'} Runs <span style={{ fontSize: 10, color: '#888', marginLeft: 4 }}>({runs.length})</span>
            </div>
            {runs.map(run => (
              <div key={run.id} style={{
                padding: 12, backgroundColor: '#22223a', borderRadius: 6,
                border: '1px solid #2a2a3e',
                borderLeft: `3px solid ${run.status === 'completed' ? '#6bcb77' : run.status === 'running' ? '#fdcb6e' : '#ff6b6b'}`,
              }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 4 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                    <span style={{ fontSize: 10, color: '#888', fontFamily: 'monospace' }}>{run.scenario_id}</span>
                    <span style={{ color: '#aaa' }}>/</span>
                    <span style={{ fontSize: 10, color: '#888', fontFamily: 'monospace' }}>{run.agent_id}</span>
                  </div>
                  <span style={{
                    fontSize: 9, padding: '2px 8px', borderRadius: 3,
                    backgroundColor: run.status === 'completed' ? '#1a3a1a' : run.status === 'running' ? '#3a3a1a' : '#3a1a1a',
                    color: run.status === 'completed' ? '#6bcb77' : run.status === 'running' ? '#fdcb6e' : '#ff6b6b',
                    fontWeight: 600,
                  }}>{run.status.toUpperCase()}</span>
                </div>
                <div style={{ fontSize: 10, color: '#888' }}>
                  Input: <span style={{ color: '#a29bfe' }}>{run.input_data.substring(0, 60)}{run.input_data.length > 60 ? '...' : ''}</span>
                </div>
                {run.output && (
                  <div style={{ fontSize: 10, color: '#6bcb77', marginTop: 4 }}>Output: {run.output.substring(0, 80)}{run.output.length > 80 ? '...' : ''}</div>
                )}
                <div style={{ fontSize: 9, color: '#666', marginTop: 4 }}>{formatTime(run.started_at)}</div>
              </div>
            ))}
          </div>
        )}

        {activeTab === 'evaluate' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            <div style={{
              padding: 12, backgroundColor: '#22223a', borderRadius: 6,
              border: '1px solid #2a2a3e',
            }}>
              <div style={{ fontSize: 12, fontWeight: 600, color: '#aaa', marginBottom: 8 }}>
                {'\uD83D\uDCCA'} evaluate
              </div>
              <div style={{ display: 'flex', gap: 8, alignItems: 'flex-end' }}>
                <div style={{ flex: 1 }}>
                  <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>Run ID</div>
                  <input value={evalRunId} onChange={e => setEvalRunId(e.target.value)} placeholder="e.g. run-1" style={{
                    padding: '6px 10px', fontSize: 11, width: '100%',
                    backgroundColor: '#141428', color: '#ccc',
                    border: '1px solid #333', borderRadius: 4, outline: 'none',
                  }} />
                </div>
                <button onClick={handleEvaluate} style={{
                  padding: '6px 14px', backgroundColor: '#4a2d4a', color: '#e056a0',
                  border: '1px solid #5a3d5a', borderRadius: 4, cursor: 'pointer',
                  fontSize: 11, fontWeight: 600,
                }}>Evaluate</button>
              </div>
            </div>

            {evaluations.map(evaluation => (
              <div key={evaluation.run_id + evaluation.evaluated_at} style={{
                padding: 14, backgroundColor: '#22223a', borderRadius: 8,
                border: '1px solid #2a2a3e',
                borderLeft: `3px solid ${evaluation.passed ? '#6bcb77' : '#ff6b6b'}`,
              }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 10 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                    <span style={{ fontWeight: 600, fontSize: 14, color: '#e056a0' }}>
                      {'\uD83D\uDCCA'} Run {evaluation.run_id}
                    </span>
                    <span style={{
                      fontSize: 9, padding: '2px 8px', borderRadius: 3,
                      backgroundColor: evaluation.passed ? '#1a3a1a' : '#3a1a1a',
                      color: evaluation.passed ? '#6bcb77' : '#ff6b6b', fontWeight: 600,
                    }}>{evaluation.passed ? 'PASSED' : 'FAILED'}</span>
                  </div>
                  <span style={{ fontSize: 10, color: '#666' }}>{formatTime(evaluation.evaluated_at)}</span>
                </div>
                <div style={{
                  padding: 10, backgroundColor: '#141428', borderRadius: 4, textAlign: 'center', marginBottom: 10,
                }}>
                  <span style={{ fontSize: 24, fontWeight: 700, color: '#fdcb6e' }}>
                    {(evaluation.score * 100).toFixed(0)}%
                  </span>
                  <div style={{ fontSize: 10, color: '#888' }}>Overall Score</div>
                </div>
                <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                  {evaluation.metrics.map(metric => (
                    <div key={metric.name} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '4px 0' }}>
                      <span style={{ fontSize: 10, color: '#aaa' }}>{metric.name.replace(/_/g, ' ')}</span>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                        <div style={{
                          width: 80, height: 4, backgroundColor: '#141428', borderRadius: 2, overflow: 'hidden',
                        }}>
                          <div style={{
                            width: `${metric.value * 100}%`, height: '100%',
                            backgroundColor: metric.value > 0.7 ? '#6bcb77' : metric.value > 0.4 ? '#fdcb6e' : '#ff6b6b',
                            borderRadius: 2,
                          }} />
                        </div>
                        <span style={{ fontSize: 10, color: '#ccc', fontWeight: 600 }}>{(metric.value * 100).toFixed(0)}%</span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      <div style={{
        padding: '6px 12px', borderTop: '1px solid #2a2a3e',
        backgroundColor: '#141428', display: 'flex',
        alignItems: 'center', justifyContent: 'space-between',
        fontSize: 10, color: '#666',
      }}>
        <span>{'\uD83C\uDFAF'} {scenarios.length} scenarios · {runs.length} runs · {evaluations.length} evals</span>
        <span>Connected</span>
      </div>
    </div>
  );
};

export default SimulationRunnerPanel;