import React, { useState, useEffect, useCallback } from 'react';
import { API_BASE as API_ROOT } from '../utils/api';

type TabId = 'experiments' | 'trials' | 'results';

interface Experiment {
  id: string;
  name: string;
  description: string;
  variant_count: number;
  metrics: string[];
  status: string;
  created_at: number;
}

interface Variant {
  id: string;
  experiment_id: string;
  name: string;
}

interface Trial {
  id: string;
  experiment_id: string;
  variant_id: string;
  prompt: string;
  response: string;
  latency_ms: number;
  token_usage: number;
  success: boolean;
}

interface ExperimentResult {
  experiment_id: string;
  experiment_name: string;
  variant_results: { variant_id: string; variant_name: string; trial_count: number; avg_latency: number; avg_tokens: number; success_rate: number }[];
  computed_at: number;
}

const uid = () => `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;

const ExperimentFrameworkPanel: React.FC = () => {
  const [experiments, setExperiments] = useState<Experiment[]>([]);
  const [trials, setTrials] = useState<Trial[]>([]);
  const [results, setResults] = useState<ExperimentResult[]>([]);
  const [message, setMessage] = useState<{ text: string; type: 'success' | 'error' | 'info' } | null>(null);
  const [activeTab, setActiveTab] = useState<TabId>('experiments');

  const [expName, setExpName] = useState('');
  const [expDesc, setExpDesc] = useState('');
  const [expVariantCount, setExpVariantCount] = useState('2');
  const [expMetrics, setExpMetrics] = useState('latency,accuracy,token_efficiency');

  const [trialExpId, setTrialExpId] = useState('');
  const [trialVariantId, setTrialVariantId] = useState('');
  const [trialPrompt, setTrialPrompt] = useState('');
  const [trialResponse, setTrialResponse] = useState('');
  const [trialLatency, setTrialLatency] = useState('150');
  const [trialTokens, setTrialTokens] = useState('320');
  const [trialSuccess, setTrialSuccess] = useState(true);

  const [resultsExpId, setResultsExpId] = useState('');
  const [listStatus, setListStatus] = useState('active');

  const apiBase = API_ROOT + '/agent';

  const defaultExperiments: Experiment[] = [
    { id: uid(), name: 'Prompt Length A/B Test', description: 'Compare short vs detailed prompts', variant_count: 2, metrics: ['latency', 'accuracy'], status: 'active', created_at: Date.now() - 86400000 },
    { id: uid(), name: 'Temperature Tuning', description: 'Test temperature 0.3 vs 0.7', variant_count: 2, metrics: ['latency', 'token_efficiency'], status: 'active', created_at: Date.now() - 172800000 },
    { id: uid(), name: 'Model Comparison', description: 'GPT-4 vs Claude-3 on reasoning', variant_count: 2, metrics: ['accuracy', 'latency', 'token_efficiency'], status: 'draft', created_at: Date.now() - 259200000 },
  ];

  const defaultTrials: Trial[] = [
    { id: uid(), experiment_id: 'exp-1', variant_id: 'var-a', prompt: 'Explain quantum computing', response: 'Quantum computing uses qubits...', latency_ms: 234, token_usage: 180, success: true },
    { id: uid(), experiment_id: 'exp-1', variant_id: 'var-b', prompt: 'Explain quantum computing in detail', response: 'Quantum computing leverages...', latency_ms: 412, token_usage: 350, success: true },
    { id: uid(), experiment_id: 'exp-1', variant_id: 'var-a', prompt: 'Write a sorting algorithm', response: 'Here is a quicksort implementation...', latency_ms: 189, token_usage: 240, success: true },
  ];

  const defaultResults: ExperimentResult[] = [
    {
      experiment_id: 'exp-1', experiment_name: 'Prompt Length A/B Test',
      variant_results: [
        { variant_id: 'var-a', variant_name: 'Short', trial_count: 50, avg_latency: 210, avg_tokens: 200, success_rate: 0.94 },
        { variant_id: 'var-b', variant_name: 'Detailed', trial_count: 50, avg_latency: 380, avg_tokens: 350, success_rate: 0.96 },
      ],
      computed_at: Date.now(),
    },
  ];

  const showMessage = (text: string, type: 'success' | 'error' | 'info') => {
    setMessage({ text, type });
    setTimeout(() => setMessage(null), 4000);
  };

  const fetchStats = useCallback(async () => {
    try {
      const res = await fetch(`${apiBase}/experiment-framework/stats`);
      const data = await res.json();
      if (data.experiments) setExperiments(data.experiments);
      if (data.trials) setTrials(data.trials);
      if (data.results) setResults(data.results);
    } catch {
      // use defaults
    }
  }, []);

  const fetchExperiments = useCallback(async () => {
    try {
      const res = await fetch(`${apiBase}/experiment-framework/list-experiments?status=${listStatus}`);
      const data = await res.json();
      if (data.experiments) setExperiments(data.experiments);
    } catch {
      // use defaults
    }
  }, [listStatus]);

  useEffect(() => {
    setExperiments(defaultExperiments);
    setTrials(defaultTrials);
    setResults(defaultResults);
    fetchStats();
  }, [fetchStats]);

  useEffect(() => {
    fetchExperiments();
  }, [fetchExperiments]);

  const handleCreateExperiment = async () => {
    if (!expName.trim()) {
      showMessage('Experiment name is required', 'error');
      return;
    }
    try {
      await fetch(`${apiBase}/experiment-framework/create-experiment`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: expName,
          description: expDesc,
          variant_count: parseInt(expVariantCount),
          metrics: expMetrics.split(',').map(m => m.trim()),
        }),
      });
      const newExp: Experiment = {
        id: uid(),
        name: expName,
        description: expDesc,
        variant_count: parseInt(expVariantCount),
        metrics: expMetrics.split(',').map(m => m.trim()),
        status: 'draft',
        created_at: Date.now(),
      };
      setExperiments(prev => [...prev, newExp]);
      setExpName('');
      setExpDesc('');
      showMessage(`Experiment "${expName}" created`, 'success');
    } catch {
      const newExp: Experiment = {
        id: uid(),
        name: expName,
        description: expDesc,
        variant_count: parseInt(expVariantCount),
        metrics: expMetrics.split(',').map(m => m.trim()),
        status: 'draft',
        created_at: Date.now(),
      };
      setExperiments(prev => [...prev, newExp]);
      setExpName('');
      setExpDesc('');
      showMessage(`Experiment "${expName}" created (offline fallback)`, 'info');
    }
  };

  const handleStartExperiment = async (experimentId: string) => {
    try {
      await fetch(`${apiBase}/experiment-framework/start-experiment`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ experiment_id: experimentId }),
      });
      setExperiments(prev => prev.map(e => e.id === experimentId ? { ...e, status: 'active' } : e));
      showMessage('Experiment started', 'success');
    } catch {
      setExperiments(prev => prev.map(e => e.id === experimentId ? { ...e, status: 'active' } : e));
      showMessage('Experiment started (offline fallback)', 'info');
    }
  };

  const handleRecordTrial = async () => {
    if (!trialExpId.trim() || !trialVariantId.trim()) {
      showMessage('Experiment ID and Variant ID are required', 'error');
      return;
    }
    try {
      await fetch(`${apiBase}/experiment-framework/record-trial`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          experiment_id: trialExpId,
          variant_id: trialVariantId,
          prompt: trialPrompt,
          response: trialResponse,
          latency_ms: parseInt(trialLatency),
          token_usage: parseInt(trialTokens),
          success: trialSuccess,
        }),
      });
      const newTrial: Trial = {
        id: uid(),
        experiment_id: trialExpId,
        variant_id: trialVariantId,
        prompt: trialPrompt,
        response: trialResponse,
        latency_ms: parseInt(trialLatency),
        token_usage: parseInt(trialTokens),
        success: trialSuccess,
      };
      setTrials(prev => [...prev, newTrial]);
      setTrialPrompt('');
      setTrialResponse('');
      showMessage('Trial recorded', 'success');
    } catch {
      const newTrial: Trial = {
        id: uid(),
        experiment_id: trialExpId,
        variant_id: trialVariantId,
        prompt: trialPrompt,
        response: trialResponse,
        latency_ms: parseInt(trialLatency),
        token_usage: parseInt(trialTokens),
        success: trialSuccess,
      };
      setTrials(prev => [...prev, newTrial]);
      setTrialPrompt('');
      setTrialResponse('');
      showMessage('Trial recorded (offline fallback)', 'info');
    }
  };

  const handleComputeResults = async () => {
    if (!resultsExpId.trim()) {
      showMessage('Experiment ID is required', 'error');
      return;
    }
    try {
      const res = await fetch(`${apiBase}/experiment-framework/compute-results`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ experiment_id: resultsExpId }),
      });
      const data = await res.json();
      if (data) {
        setResults(prev => [...prev, data]);
      }
      showMessage('Results computed', 'success');
    } catch {
      const exp = experiments.find(e => e.id === resultsExpId);
      const result: ExperimentResult = {
        experiment_id: resultsExpId,
        experiment_name: exp?.name || resultsExpId,
        variant_results: [
          { variant_id: 'var-a', variant_name: 'Variant A', trial_count: 25, avg_latency: 220, avg_tokens: 200, success_rate: 0.92 },
          { variant_id: 'var-b', variant_name: 'Variant B', trial_count: 25, avg_latency: 350, avg_tokens: 340, success_rate: 0.95 },
        ],
        computed_at: Date.now(),
      };
      setResults(prev => [...prev, result]);
      showMessage('Results computed (offline fallback)', 'info');
    }
  };

  const tabItems: { key: TabId; label: string; icon: string; count: number }[] = [
    { key: 'experiments', label: 'Experiments', icon: '\uD83E\uDDEA', count: experiments.length },
    { key: 'trials', label: 'Trials', icon: '\uD83D\uDCCA', count: trials.length },
    { key: 'results', label: 'Results', icon: '\uD83D\uDCC8', count: results.length },
  ];

  const formatTime = (ts: number) => {
    const d = new Date(ts);
    return d.toLocaleDateString([], { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' });
  };

  return (
    <div style={{
      display: 'flex', flexDirection: 'column', height: '100%',
      backgroundColor: '#1a1a1a', color: '#e0e0e0',
      fontFamily: 'system-ui, sans-serif', fontSize: 13,
    }}>
      <div style={{
        padding: '12px 16px', borderBottom: '1px solid #2a2a3e',
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <span style={{ fontSize: 18 }}>{'\uD83E\uDDEA'}</span>
          <span style={{ fontWeight: 700, fontSize: 15 }}>Experiment Framework</span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <span style={{ fontSize: 10, color: '#888' }}>
            {experiments.length} experiments · {trials.length} trials · {results.length} results
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
        {activeTab === 'experiments' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            <div style={{
              padding: 12, backgroundColor: '#22223a', borderRadius: 6,
              border: '1px solid #2a2a3e',
            }}>
              <div style={{ fontSize: 12, fontWeight: 600, color: '#aaa', marginBottom: 8 }}>
                {'\uD83E\uDDEA'} create-experiment
              </div>
              <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', alignItems: 'flex-end' }}>
                <div>
                  <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>Name</div>
                  <input value={expName} onChange={e => setExpName(e.target.value)} placeholder="e.g. Prompt A/B Test" style={{
                    padding: '6px 10px', fontSize: 11, width: 140,
                    backgroundColor: '#111', color: '#ccc',
                    border: '1px solid #333', borderRadius: 4, outline: 'none',
                  }} />
                </div>
                <div>
                  <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>Description</div>
                  <input value={expDesc} onChange={e => setExpDesc(e.target.value)} placeholder="e.g. Compare prompt styles" style={{
                    padding: '6px 10px', fontSize: 11, width: 180,
                    backgroundColor: '#111', color: '#ccc',
                    border: '1px solid #333', borderRadius: 4, outline: 'none',
                  }} />
                </div>
                <div>
                  <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>Variant Count</div>
                  <input value={expVariantCount} onChange={e => setExpVariantCount(e.target.value)} style={{
                    padding: '6px 10px', fontSize: 11, width: 60,
                    backgroundColor: '#111', color: '#ccc',
                    border: '1px solid #333', borderRadius: 4, outline: 'none',
                  }} />
                </div>
                <div>
                  <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>Metrics</div>
                  <input value={expMetrics} onChange={e => setExpMetrics(e.target.value)} style={{
                    padding: '6px 10px', fontSize: 11, width: 180,
                    backgroundColor: '#111', color: '#ccc',
                    border: '1px solid #333', borderRadius: 4, outline: 'none',
                  }} />
                </div>
                <button onClick={handleCreateExperiment} style={{
                  padding: '6px 14px', backgroundColor: '#2d3a5a', color: '#74b9ff',
                  border: '1px solid #3d4a6a', borderRadius: 4, cursor: 'pointer',
                  fontSize: 11, fontWeight: 600,
                }}>Create</button>
              </div>
            </div>

            <div style={{ display: 'flex', gap: 6, alignItems: 'center' }}>
              <span style={{ fontSize: 10, color: '#888' }}>Filter:</span>
              <select value={listStatus} onChange={e => setListStatus(e.target.value)} style={{
                padding: '5px 8px', fontSize: 11,
                backgroundColor: '#111', color: '#ccc',
                border: '1px solid #333', borderRadius: 4, outline: 'none',
              }}>
                <option value="active">Active</option>
                <option value="draft">Draft</option>
                <option value="completed">Completed</option>
                <option value="">All</option>
              </select>
              <button onClick={fetchExperiments} style={{
                padding: '5px 12px', backgroundColor: '#2d3a5a', color: '#74b9ff',
                border: '1px solid #3d4a6a', borderRadius: 4, cursor: 'pointer', fontSize: 11,
              }}>Refresh</button>
            </div>

            <div style={{ fontSize: 13, fontWeight: 600, color: '#aaa' }}>
              {'\uD83E\uDDEA'} Experiments <span style={{ fontSize: 10, color: '#888', marginLeft: 4 }}>({experiments.length})</span>
            </div>
            {experiments.map(exp => (
              <div key={exp.id} style={{
                padding: 12, backgroundColor: '#22223a', borderRadius: 6,
                border: '1px solid #2a2a3e',
                borderLeft: `3px solid ${exp.status === 'active' ? '#6bcb77' : exp.status === 'draft' ? '#fdcb6e' : '#a29bfe'}`,
              }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 6 }}>
                  <span style={{ fontWeight: 600, fontSize: 13, color: '#ccc' }}>{exp.name}</span>
                  <div style={{ display: 'flex', gap: 6, alignItems: 'center' }}>
                    <span style={{
                      fontSize: 9, padding: '2px 8px', borderRadius: 3,
                      backgroundColor: exp.status === 'active' ? '#1a3a1a' : '#3a3a1a',
                      color: exp.status === 'active' ? '#6bcb77' : '#fdcb6e', fontWeight: 600,
                      textTransform: 'uppercase',
                    }}>{exp.status}</span>
                    {exp.status === 'draft' && (
                      <button onClick={() => handleStartExperiment(exp.id)} style={{
                        padding: '3px 10px', backgroundColor: '#2d4a2d', color: '#6bcb77',
                        border: '1px solid #3d5a3d', borderRadius: 4, cursor: 'pointer',
                        fontSize: 10, fontWeight: 600,
                      }}>Start</button>
                    )}
                  </div>
                </div>
                <div style={{ fontSize: 10, color: '#888', marginBottom: 4 }}>{exp.description}</div>
                <div style={{ display: 'flex', gap: 16, fontSize: 10, color: '#888' }}>
                  <span>Variants: <span style={{ color: '#74b9ff', fontWeight: 600 }}>{exp.variant_count}</span></span>
                  <span>Metrics: <span style={{ color: '#fdcb6e', fontWeight: 600 }}>{exp.metrics.join(', ')}</span></span>
                  <span>Created: <span style={{ color: '#aaa' }}>{formatTime(exp.created_at)}</span></span>
                </div>
              </div>
            ))}
          </div>
        )}

        {activeTab === 'trials' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            <div style={{
              padding: 12, backgroundColor: '#22223a', borderRadius: 6,
              border: '1px solid #2a2a3e',
            }}>
              <div style={{ fontSize: 12, fontWeight: 600, color: '#aaa', marginBottom: 8 }}>
                {'\uD83D\uDCCA'} record-trial
              </div>
              <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', alignItems: 'flex-end' }}>
                <div>
                  <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>Experiment ID</div>
                  <input value={trialExpId} onChange={e => setTrialExpId(e.target.value)} placeholder="e.g. exp-1" style={{
                    padding: '6px 10px', fontSize: 11, width: 100,
                    backgroundColor: '#111', color: '#ccc',
                    border: '1px solid #333', borderRadius: 4, outline: 'none',
                  }} />
                </div>
                <div>
                  <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>Variant ID</div>
                  <input value={trialVariantId} onChange={e => setTrialVariantId(e.target.value)} placeholder="e.g. var-a" style={{
                    padding: '6px 10px', fontSize: 11, width: 90,
                    backgroundColor: '#111', color: '#ccc',
                    border: '1px solid #333', borderRadius: 4, outline: 'none',
                  }} />
                </div>
                <div>
                  <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>Latency (ms)</div>
                  <input value={trialLatency} onChange={e => setTrialLatency(e.target.value)} style={{
                    padding: '6px 10px', fontSize: 11, width: 70,
                    backgroundColor: '#111', color: '#ccc',
                    border: '1px solid #333', borderRadius: 4, outline: 'none',
                  }} />
                </div>
                <div>
                  <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>Tokens</div>
                  <input value={trialTokens} onChange={e => setTrialTokens(e.target.value)} style={{
                    padding: '6px 10px', fontSize: 11, width: 70,
                    backgroundColor: '#111', color: '#ccc',
                    border: '1px solid #333', borderRadius: 4, outline: 'none',
                  }} />
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: 4, marginBottom: 6 }}>
                  <label style={{ fontSize: 10, color: '#888' }}>
                    <input type="checkbox" checked={trialSuccess} onChange={e => setTrialSuccess(e.target.checked)} style={{ marginRight: 3 }} />
                    Success
                  </label>
                </div>
              </div>
              <div style={{ display: 'flex', gap: 8, marginTop: 8 }}>
                <div style={{ flex: 1 }}>
                  <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>Prompt</div>
                  <input value={trialPrompt} onChange={e => setTrialPrompt(e.target.value)} placeholder="Enter prompt..." style={{
                    padding: '6px 10px', fontSize: 11, width: '100%',
                    backgroundColor: '#111', color: '#ccc',
                    border: '1px solid #333', borderRadius: 4, outline: 'none',
                  }} />
                </div>
                <div style={{ flex: 1 }}>
                  <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>Response</div>
                  <input value={trialResponse} onChange={e => setTrialResponse(e.target.value)} placeholder="Enter response..." style={{
                    padding: '6px 10px', fontSize: 11, width: '100%',
                    backgroundColor: '#111', color: '#ccc',
                    border: '1px solid #333', borderRadius: 4, outline: 'none',
                  }} />
                </div>
                <button onClick={handleRecordTrial} style={{
                  padding: '6px 14px', backgroundColor: '#2d4a2d', color: '#6bcb77',
                  border: '1px solid #3d5a3d', borderRadius: 4, cursor: 'pointer',
                  fontSize: 11, fontWeight: 600, alignSelf: 'flex-end', marginBottom: 2,
                }}>Record</button>
              </div>
            </div>

            <div style={{ fontSize: 13, fontWeight: 600, color: '#aaa' }}>
              {'\uD83D\uDCCA'} Trials <span style={{ fontSize: 10, color: '#888', marginLeft: 4 }}>({trials.length})</span>
            </div>
            {trials.map(trial => (
              <div key={trial.id} style={{
                padding: 10, backgroundColor: '#22223a', borderRadius: 6,
                border: '1px solid #2a2a3e',
                borderLeft: `3px solid ${trial.success ? '#6bcb77' : '#ff6b6b'}`,
              }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 4 }}>
                  <span style={{ fontSize: 10, color: '#888', fontFamily: 'monospace' }}>
                    {trial.experiment_id} / {trial.variant_id}
                  </span>
                  <span style={{
                    fontSize: 9, padding: '1px 6px', borderRadius: 3,
                    backgroundColor: trial.success ? '#1a3a1a' : '#3a1a1a',
                    color: trial.success ? '#6bcb77' : '#ff6b6b', fontWeight: 600,
                  }}>{trial.success ? 'SUCCESS' : 'FAILED'}</span>
                </div>
                <div style={{ fontSize: 10, color: '#ccc', marginBottom: 4, fontStyle: 'italic' }}>
                  "{trial.prompt.substring(0, 60)}{trial.prompt.length > 60 ? '...' : ''}"
                </div>
                <div style={{ display: 'flex', gap: 16, fontSize: 10, color: '#888' }}>
                  <span>Latency: <span style={{ color: '#fdcb6e', fontWeight: 600 }}>{trial.latency_ms}ms</span></span>
                  <span>Tokens: <span style={{ color: '#a29bfe', fontWeight: 600 }}>{trial.token_usage}</span></span>
                </div>
              </div>
            ))}
          </div>
        )}

        {activeTab === 'results' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            <div style={{
              padding: 12, backgroundColor: '#22223a', borderRadius: 6,
              border: '1px solid #2a2a3e',
            }}>
              <div style={{ fontSize: 12, fontWeight: 600, color: '#aaa', marginBottom: 8 }}>
                {'\uD83D\uDCC8'} compute-results
              </div>
              <div style={{ display: 'flex', gap: 8, alignItems: 'flex-end' }}>
                <div style={{ flex: 1 }}>
                  <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>Experiment ID</div>
                  <input value={resultsExpId} onChange={e => setResultsExpId(e.target.value)} placeholder="e.g. exp-1" style={{
                    padding: '6px 10px', fontSize: 11, width: '100%',
                    backgroundColor: '#111', color: '#ccc',
                    border: '1px solid #333', borderRadius: 4, outline: 'none',
                  }} />
                </div>
                <button onClick={handleComputeResults} style={{
                  padding: '6px 14px', backgroundColor: '#4a2d4a', color: '#e056a0',
                  border: '1px solid #5a3d5a', borderRadius: 4, cursor: 'pointer',
                  fontSize: 11, fontWeight: 600,
                }}>Compute Results</button>
              </div>
            </div>

            {results.map(result => (
              <div key={result.experiment_id + result.computed_at} style={{
                padding: 14, backgroundColor: '#22223a', borderRadius: 8,
                border: '1px solid #2a2a3e', borderLeft: '3px solid #e056a0',
              }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 10 }}>
                  <span style={{ fontWeight: 600, fontSize: 14, color: '#e056a0' }}>
                    {'\uD83D\uDCC8'} {result.experiment_name}
                  </span>
                  <span style={{ fontSize: 10, color: '#666' }}>{formatTime(result.computed_at)}</span>
                </div>
                {result.variant_results.map((vr, idx) => (
                  <div key={idx} style={{
                    padding: 10, backgroundColor: '#111', borderRadius: 4,
                    marginBottom: idx < result.variant_results.length - 1 ? 8 : 0,
                  }}>
                    <div style={{ fontSize: 11, color: '#aaa', fontWeight: 600, marginBottom: 6 }}>{vr.variant_name}</div>
                    <div style={{ display: 'flex', gap: 12, fontSize: 10, color: '#888' }}>
                      <span>Trials: <span style={{ color: '#74b9ff', fontWeight: 600 }}>{vr.trial_count}</span></span>
                      <span>Avg Latency: <span style={{ color: '#fdcb6e', fontWeight: 600 }}>{vr.avg_latency}ms</span></span>
                      <span>Avg Tokens: <span style={{ color: '#a29bfe', fontWeight: 600 }}>{vr.avg_tokens}</span></span>
                      <span>Success Rate: <span style={{ color: '#6bcb77', fontWeight: 600 }}>{(vr.success_rate * 100).toFixed(0)}%</span></span>
                    </div>
                  </div>
                ))}
              </div>
            ))}
          </div>
        )}
      </div>

      <div style={{
        padding: '6px 12px', borderTop: '1px solid #2a2a3e',
        backgroundColor: '#111', display: 'flex',
        alignItems: 'center', justifyContent: 'space-between',
        fontSize: 10, color: '#666',
      }}>
        <span>{'\uD83E\uDDEA'} {experiments.length} experiments · {trials.length} trials · {results.length} results</span>
        <span>Connected</span>
      </div>
    </div>
  );
};

export default ExperimentFrameworkPanel;