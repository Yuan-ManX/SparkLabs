"use client";
import React, { useState, useEffect, useCallback } from 'react';

const API_BASE = 'http://localhost:8000/api/agent';

export default function AgentSelfEvolutionPanel() {
  const [activeTab, setActiveTab] = useState('overview');
  const [stats, setStats] = useState<any>({});
  const [message, setMessage] = useState('');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<any>(null);

  // Capture Trace form
  const [ctAgentId, setCtAgentId] = useState('');
  const [ctTaskDesc, setCtTaskDesc] = useState('');
  const [ctStrategyType, setCtStrategyType] = useState('');
  const [ctStrategyVersion, setCtStrategyVersion] = useState('1.0');
  const [ctOutcome, setCtOutcome] = useState('success');
  const [ctDurationMs, setCtDurationMs] = useState('');
  const [ctMetrics, setCtMetrics] = useState('');
  const [ctContextSnapshot, setCtContextSnapshot] = useState('');
  const [ctErrorDetails, setCtErrorDetails] = useState('');

  // Analyze form
  const [azStrategyType, setAzStrategyType] = useState('');

  // Evolve form
  const [evStrategyType, setEvStrategyType] = useState('');
  const [evTargetImprovement, setEvTargetImprovement] = useState('');

  // Validate form
  const [valStrategyId, setValStrategyId] = useState('');
  const [valTestConditions, setValTestConditions] = useState('');

  // Traces form
  const [trStrategyType, setTrStrategyType] = useState('');
  const [trLimit, setTrLimit] = useState('50');

  const tabs = ['overview', 'capture-trace', 'analyze', 'evolve', 'validate', 'traces'];

  const fetchStats = useCallback(async () => {
    try { const r = await fetch(`${API_BASE}/self-evolution/stats`); if (r.ok) setStats(await r.json()); } catch (e) {}
  }, []);

  useEffect(() => { fetchStats(); const i = setInterval(fetchStats, 15000); return () => clearInterval(i); }, [fetchStats]);

  const handlePost = async (url: string, body: any) => {
    setLoading(true); setMessage('');
    try {
      const r = await fetch(url, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });
      const data = await r.json();
      setResult(data);
      setMessage(r.ok ? 'Success' : data.message || data.error || 'Failed');
      fetchStats();
    } catch (e: any) { setMessage(e.message); }
    finally { setLoading(false); }
  };

  const handleGet = async (url: string) => {
    setLoading(true); setMessage('');
    try {
      const r = await fetch(url);
      const data = await r.json();
      setResult(data);
      setMessage(r.ok ? 'Success' : data.message || 'Failed');
      fetchStats();
    } catch (e: any) { setMessage(e.message); }
    finally { setLoading(false); }
  };

  const inputCls = 'w-full bg-[#1a1a2e] border border-[#2a2a4a] rounded px-3 py-2 text-sm text-white placeholder-gray-500 outline-none focus:border-[#00d4ff]';
  const selectCls = 'w-full bg-[#1a1a2e] border border-[#2a2a4a] rounded px-3 py-2 text-sm text-white outline-none focus:border-[#00d4ff]';
  const cardCls = 'bg-[#0f0f23] p-4 rounded border border-[#2a2a4a]';

  const outcomeColor = (o: string) => {
    switch (o) {
      case 'success': return 'text-[#00ff88]';
      case 'failure': return 'text-red-400';
      case 'partial': return 'text-amber-300';
      default: return 'text-gray-400';
    }
  };

  return (
    <div className="h-full flex flex-col bg-[#1a1a2e] text-white">
      <div className="flex gap-1 p-3 border-b border-[#2a2a4a]">
        {tabs.map(t => (
          <button key={t} onClick={() => setActiveTab(t)}
            className={`px-4 py-2 rounded text-sm font-medium transition-colors ${activeTab === t ? 'bg-[#00d4ff] text-black' : 'bg-[#0f0f23] text-gray-300 hover:bg-[#2a2a4a]'}`}>
            {t.split('-').map(w => w.charAt(0).toUpperCase() + w.slice(1)).join(' ')}
          </button>
        ))}
      </div>

      {message && (
        <div className="mx-4 mt-2 p-2 rounded text-sm border bg-[#0f0f23] border-[#00ff88] text-[#00ff88]">{message}</div>
      )}

      <div className="flex-1 overflow-auto p-4">

        {/* OVERVIEW TAB */}
        {activeTab === 'overview' && (
          <div className="space-y-4">
            <h2 className="text-lg font-bold text-[#00d4ff]">Self-Evolution Overview</h2>
            <div className="grid grid-cols-4 gap-4">
              {[
                { label: 'Total Strategies', value: stats.total_strategies, color: 'text-[#00d4ff]' },
                { label: 'Total Traces', value: stats.total_traces, color: 'text-[#00ff88]' },
                { label: 'Total Evolutions', value: stats.total_evolutions, color: 'text-amber-300' },
                { label: 'Success Rate', value: stats.success_rate ? `${(stats.success_rate * 100).toFixed(1)}%` : '0%', color: 'text-pink-300' },
              ].map(s => (
                <div key={s.label} className="bg-[#0f0f23] p-4 rounded border border-[#2a2a4a]">
                  <h3 className="text-xs text-gray-400">{s.label}</h3>
                  <p className={`text-2xl font-bold ${s.color}`}>{s.value ?? 0}</p>
                </div>
              ))}
            </div>
            {stats.strategies_by_type && (
              <div className={cardCls}>
                <h3 className="text-sm font-bold text-gray-300 mb-2">Strategies by Type</h3>
                <div className="grid grid-cols-3 gap-2">
                  {Object.entries(stats.strategies_by_type).map(([k, v]) => (
                    <div key={k} className="flex justify-between text-xs"><span className="text-gray-400">{k}</span><span className="text-[#00d4ff]">{v as any}</span></div>
                  ))}
                </div>
              </div>
            )}
            {result && activeTab === 'overview' && (
              <div className={cardCls}>
                <pre className="bg-[#1a1a2e] p-3 rounded border border-[#2a2a4a] text-xs text-gray-400 overflow-auto max-h-96">{JSON.stringify(result, null, 2)}</pre>
              </div>
            )}
          </div>
        )}

        {/* CAPTURE TRACE TAB */}
        {activeTab === 'capture-trace' && (
          <div className="space-y-4">
            <h2 className="text-lg font-bold text-[#00ff88]">Capture Trace</h2>
            <div className={cardCls + ' space-y-3'}>
              <input className={inputCls} placeholder="Agent ID" value={ctAgentId} onChange={e => setCtAgentId(e.target.value)} />
              <textarea className={inputCls + ' resize-none'} rows={2} placeholder="Task Description" value={ctTaskDesc} onChange={e => setCtTaskDesc(e.target.value)} />
              <div className="grid grid-cols-2 gap-3">
                <input className={inputCls} placeholder="Strategy Type" value={ctStrategyType} onChange={e => setCtStrategyType(e.target.value)} />
                <input className={inputCls} placeholder="Strategy Version" value={ctStrategyVersion} onChange={e => setCtStrategyVersion(e.target.value)} />
              </div>
              <div className="grid grid-cols-2 gap-3">
                <select className={selectCls} value={ctOutcome} onChange={e => setCtOutcome(e.target.value)}>
                  <option value="success">Success</option>
                  <option value="failure">Failure</option>
                  <option value="partial">Partial</option>
                </select>
                <input className={inputCls} placeholder="Duration (ms)" type="number" value={ctDurationMs} onChange={e => setCtDurationMs(e.target.value)} />
              </div>
              <textarea className={inputCls + ' resize-none'} rows={2} placeholder="Metrics (JSON)" value={ctMetrics} onChange={e => setCtMetrics(e.target.value)} />
              <textarea className={inputCls + ' resize-none'} rows={2} placeholder="Context Snapshot (JSON)" value={ctContextSnapshot} onChange={e => setCtContextSnapshot(e.target.value)} />
              <textarea className={inputCls + ' resize-none'} rows={2} placeholder="Error Details (optional)" value={ctErrorDetails} onChange={e => setCtErrorDetails(e.target.value)} />
              <button
                className="w-full px-4 py-2 bg-[#00ff88] text-black rounded text-sm font-medium hover:bg-[#00cc6a] transition-colors disabled:opacity-50"
                disabled={loading}
                onClick={() => handlePost(`${API_BASE}/self-evolution/capture-trace`, {
                  agent_id: ctAgentId,
                  task_description: ctTaskDesc,
                  strategy_type: ctStrategyType,
                  strategy_version: ctStrategyVersion,
                  outcome: ctOutcome,
                  duration_ms: parseInt(ctDurationMs) || 0,
                  metrics: ctMetrics,
                  context_snapshot: ctContextSnapshot,
                  error_details: ctErrorDetails || undefined,
                })}>
                {loading ? 'Capturing...' : 'Capture Trace'}
              </button>
            </div>
          </div>
        )}

        {/* ANALYZE TAB */}
        {activeTab === 'analyze' && (
          <div className="space-y-4">
            <h2 className="text-lg font-bold text-[#00d4ff]">Analyze Strategies</h2>
            <div className={cardCls + ' space-y-3'}>
              <input className={inputCls} placeholder="Strategy Type" value={azStrategyType} onChange={e => setAzStrategyType(e.target.value)} />
              <button
                className="w-full px-4 py-2 bg-[#00d4ff] text-black rounded text-sm font-medium hover:bg-[#00b8e6] transition-colors disabled:opacity-50"
                disabled={loading}
                onClick={() => handlePost(`${API_BASE}/self-evolution/analyze`, {
                  strategy_type: azStrategyType,
                })}>
                {loading ? 'Analyzing...' : 'Run Analysis'}
              </button>
            </div>
            {result && activeTab === 'analyze' && (
              <div className={cardCls + ' space-y-3'}>
                {result.analysis && (
                  <div>
                    <h3 className="text-sm font-bold text-[#00d4ff] mb-2">Analysis Results</h3>
                    <p className="text-xs text-gray-300">{result.analysis}</p>
                  </div>
                )}
                {result.recommendations && Array.isArray(result.recommendations) && (
                  <div>
                    <h3 className="text-sm font-bold text-[#00ff88] mb-2">Recommendations</h3>
                    <ul className="list-disc list-inside text-xs text-gray-300 space-y-1">
                      {result.recommendations.map((r: string, i: number) => <li key={i}>{r}</li>)}
                    </ul>
                  </div>
                )}
                {result.performance_metrics && (
                  <div>
                    <h3 className="text-sm font-bold text-amber-300 mb-2">Performance Metrics</h3>
                    <div className="grid grid-cols-2 gap-2">
                      {Object.entries(result.performance_metrics).map(([k, v]) => (
                        <div key={k} className="flex justify-between text-xs bg-[#1a1a2e] p-2 rounded border border-[#2a2a4a]">
                          <span className="text-gray-400">{k}</span>
                          <span className="text-white">{String(v)}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
                <pre className="bg-[#1a1a2e] p-3 rounded border border-[#2a2a4a] text-xs text-gray-400 overflow-auto max-h-48">{JSON.stringify(result, null, 2)}</pre>
              </div>
            )}
          </div>
        )}

        {/* EVOLVE TAB */}
        {activeTab === 'evolve' && (
          <div className="space-y-4">
            <h2 className="text-lg font-bold text-amber-300">Evolve Strategy</h2>
            <div className={cardCls + ' space-y-3'}>
              <input className={inputCls} placeholder="Strategy Type" value={evStrategyType} onChange={e => setEvStrategyType(e.target.value)} />
              <input className={inputCls} placeholder="Target Improvement (e.g. 0.15 for 15%)" value={evTargetImprovement} onChange={e => setEvTargetImprovement(e.target.value)} />
              <button
                className="w-full px-4 py-2 bg-amber-500 text-black rounded text-sm font-medium hover:bg-amber-600 transition-colors disabled:opacity-50"
                disabled={loading}
                onClick={() => handlePost(`${API_BASE}/self-evolution/evolve`, {
                  strategy_type: evStrategyType,
                  target_improvement: parseFloat(evTargetImprovement) || 0.1,
                })}>
                {loading ? 'Evolving...' : 'Evolve Strategy'}
              </button>
            </div>
            {result && activeTab === 'evolve' && (
              <div className={cardCls + ' space-y-3'}>
                {result.evolved_strategy && (
                  <div>
                    <h3 className="text-sm font-bold text-amber-300 mb-2">Evolved Strategy</h3>
                    <div className="bg-[#1a1a2e] p-3 rounded border border-[#2a2a4a] space-y-2">
                      {typeof result.evolved_strategy === 'object' ? (
                        Object.entries(result.evolved_strategy).map(([k, v]) => (
                          <div key={k} className="flex justify-between text-xs">
                            <span className="text-gray-400">{k}</span>
                            <span className="text-white">{typeof v === 'object' ? JSON.stringify(v) : String(v)}</span>
                          </div>
                        ))
                      ) : (
                        <p className="text-xs text-gray-300">{String(result.evolved_strategy)}</p>
                      )}
                    </div>
                  </div>
                )}
                {result.improvement_estimate !== undefined && (
                  <div className="flex items-center gap-2">
                    <span className="text-xs text-gray-400">Estimated Improvement:</span>
                    <span className="text-sm font-bold text-[#00ff88]">+{(result.improvement_estimate * 100).toFixed(1)}%</span>
                  </div>
                )}
                <pre className="bg-[#1a1a2e] p-3 rounded border border-[#2a2a4a] text-xs text-gray-400 overflow-auto max-h-48">{JSON.stringify(result, null, 2)}</pre>
              </div>
            )}
          </div>
        )}

        {/* VALIDATE TAB */}
        {activeTab === 'validate' && (
          <div className="space-y-4">
            <h2 className="text-lg font-bold text-pink-300">Validate Strategy</h2>
            <div className={cardCls + ' space-y-3'}>
              <input className={inputCls} placeholder="Strategy ID" value={valStrategyId} onChange={e => setValStrategyId(e.target.value)} />
              <textarea className={inputCls + ' resize-none'} rows={3} placeholder="Test Conditions (JSON)" value={valTestConditions} onChange={e => setValTestConditions(e.target.value)} />
              <button
                className="w-full px-4 py-2 bg-pink-500 text-white rounded text-sm font-medium hover:bg-pink-600 transition-colors disabled:opacity-50"
                disabled={loading}
                onClick={() => handlePost(`${API_BASE}/self-evolution/validate`, {
                  strategy_id: valStrategyId,
                  test_conditions: valTestConditions,
                })}>
                {loading ? 'Validating...' : 'Validate Strategy'}
              </button>
            </div>

            {result && activeTab === 'validate' && (
              <div className={cardCls + ' space-y-3'}>
                <div className="flex items-center gap-2">
                  <h3 className="text-sm font-bold text-white">Validation Results</h3>
                  {result.valid !== undefined && (
                    <span className={`text-xs px-2 py-0.5 rounded ${result.valid ? 'bg-[#00ff88]/20 text-[#00ff88]' : 'bg-red-500/20 text-red-300'}`}>
                      {result.valid ? 'Valid' : 'Invalid'}
                    </span>
                  )}
                </div>
                {result.score !== undefined && (
                  <div className="flex items-center gap-2">
                    <span className="text-xs text-gray-400">Score:</span>
                    <span className="text-sm font-bold text-[#00d4ff]">{(result.score * 100).toFixed(1)}%</span>
                  </div>
                )}
                {result.issues && Array.isArray(result.issues) && result.issues.length > 0 && (
                  <div>
                    <h4 className="text-xs font-semibold text-red-400 mb-1">Issues</h4>
                    <ul className="list-disc list-inside text-xs text-red-300 space-y-0.5">
                      {result.issues.map((issue: string, i: number) => <li key={i}>{issue}</li>)}
                    </ul>
                  </div>
                )}
                {result.test_results && Array.isArray(result.test_results) && (
                  <div>
                    <h4 className="text-xs font-semibold text-[#00d4ff] mb-1">Test Results</h4>
                    <div className="space-y-2">
                      {result.test_results.map((t: any, i: number) => (
                        <div key={i} className="bg-[#1a1a2e] p-2 rounded border border-[#2a2a4a]">
                          <div className="flex justify-between text-xs">
                            <span className="text-gray-300">{t.condition || t.name || `Test ${i + 1}`}</span>
                            <span className={outcomeColor(t.outcome || t.result)}>{t.outcome || t.result || 'N/A'}</span>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
                <pre className="bg-[#1a1a2e] p-3 rounded border border-[#2a2a4a] text-xs text-gray-400 overflow-auto max-h-48">{JSON.stringify(result, null, 2)}</pre>
              </div>
            )}
          </div>
        )}

        {/* TRACES TAB */}
        {activeTab === 'traces' && (
          <div className="space-y-4">
            <h2 className="text-lg font-bold text-purple-300">Trace History</h2>
            <div className={cardCls + ' space-y-3'}>
              <div className="grid grid-cols-2 gap-3">
                <input className={inputCls} placeholder="Strategy Type (optional)" value={trStrategyType} onChange={e => setTrStrategyType(e.target.value)} />
                <input className={inputCls} placeholder="Limit" type="number" value={trLimit} onChange={e => setTrLimit(e.target.value)} />
              </div>
              <div className="flex gap-3">
                <button
                  className="flex-1 px-4 py-2 bg-purple-500 text-white rounded text-sm font-medium hover:bg-purple-600 transition-colors disabled:opacity-50"
                  disabled={loading}
                  onClick={() => {
                    const params = new URLSearchParams({ limit: trLimit });
                    if (trStrategyType) params.set('strategy_type', trStrategyType);
                    handleGet(`${API_BASE}/self-evolution/traces?${params}`);
                  }}>
                  {loading ? 'Loading...' : 'Load Traces'}
                </button>
                <button
                  className="px-4 py-2 bg-[#00d4ff] text-black rounded text-sm font-medium hover:bg-[#00b8e6] transition-colors disabled:opacity-50"
                  disabled={loading}
                  onClick={() => handlePost(`${API_BASE}/self-evolution/consolidate`, {})}>
                  {loading ? 'Consolidating...' : 'Consolidate'}
                </button>
              </div>
            </div>

            {result && activeTab === 'traces' && Array.isArray(result.traces) && (
              <div className="space-y-2">
                <h3 className="text-sm font-bold text-gray-300">
                  {result.traces.length} Trace{result.traces.length !== 1 ? 's' : ''}
                  {result.total !== undefined && <span className="text-xs text-gray-500 ml-2">(total: {result.total})</span>}
                </h3>
                {result.traces.map((trace: any, i: number) => (
                  <div key={trace.id || i} className="bg-[#0f0f23] p-3 rounded border border-[#2a2a4a]">
                    <div className="flex justify-between items-start mb-2">
                      <div>
                        <span className="text-sm font-medium text-white">{trace.task_description || trace.strategy_type || `Trace ${i + 1}`}</span>
                        {trace.strategy_version && <span className="text-xs text-gray-500 ml-2">v{trace.strategy_version}</span>}
                      </div>
                      <span className={`text-xs px-2 py-0.5 rounded ${trace.outcome === 'success' ? 'bg-[#00ff88]/20 text-[#00ff88]' : trace.outcome === 'failure' ? 'bg-red-500/20 text-red-300' : 'bg-amber-500/20 text-amber-300'}`}>
                        {trace.outcome || 'unknown'}
                      </span>
                    </div>
                    <div className="grid grid-cols-3 gap-2 text-xs">
                      {trace.agent_id && (
                        <div>
                          <span className="text-gray-500">Agent: </span>
                          <span className="text-gray-300">{trace.agent_id}</span>
                        </div>
                      )}
                      {trace.strategy_type && (
                        <div>
                          <span className="text-gray-500">Strategy: </span>
                          <span className="text-gray-300">{trace.strategy_type}</span>
                        </div>
                      )}
                      {trace.duration_ms !== undefined && (
                        <div>
                          <span className="text-gray-500">Duration: </span>
                          <span className="text-gray-300">{trace.duration_ms}ms</span>
                        </div>
                      )}
                    </div>
                    {trace.metrics && (
                      <div className="mt-2">
                        <span className="text-[10px] text-gray-500">Metrics: </span>
                        <span className="text-[10px] text-gray-400">
                          {typeof trace.metrics === 'string' ? trace.metrics : JSON.stringify(trace.metrics)}
                        </span>
                      </div>
                    )}
                    {trace.error_details && (
                      <div className="mt-1">
                        <span className="text-[10px] text-red-400">Error: </span>
                        <span className="text-[10px] text-red-300">{trace.error_details}</span>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}

            {result && activeTab === 'traces' && !Array.isArray(result.traces) && (
              <div className={cardCls}>
                <pre className="bg-[#1a1a2e] p-3 rounded border border-[#2a2a4a] text-xs text-gray-400 overflow-auto max-h-96">{JSON.stringify(result, null, 2)}</pre>
              </div>
            )}
          </div>
        )}

      </div>
    </div>
  );
}