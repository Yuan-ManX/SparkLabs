"use client";
import React, { useState, useEffect, useCallback } from 'react';
import { API_BASE as API_ROOT } from '../utils/api';

const API_BASE = API_ROOT + '/agent';

export default function AgentDynamicDifficultyPanel() {
  const [activeTab, setActiveTab] = useState('overview');
  const [stats, setStats] = useState<any>({});
  const [message, setMessage] = useState('');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<any>(null);

  // Create profile
  const [cpPlayerId, setCpPlayerId] = useState('');
  const [baselineDifficulty, setBaselineDifficulty] = useState('0.5');
  const [cpStrategy, setCpStrategy] = useState('gradual');

  // Update metrics
  const [umPlayerId, setUmPlayerId] = useState('');
  const [metrics, setMetrics] = useState({
    deaths_per_minute: '0', kill_efficiency: '0', completion_speed: '0',
    accuracy: '0', resource_efficiency: '0', damage_taken: '0',
    damage_dealt: '0', combo_rate: '0', exploration_rate: '0',
  });

  // Adjust difficulty
  const [adjPlayerId, setAdjPlayerId] = useState('');

  // History
  const [histPlayerId, setHistPlayerId] = useState('');

  const fetchStats = useCallback(async () => {
    try { const r = await fetch(`${API_BASE}/dynamic-difficulty/stats`); if (r.ok) setStats(await r.json()); } catch (e) { console.error(e); }
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
      setMessage(r.ok ? 'Success' : data.message || data.error || 'Failed');
      fetchStats();
    } catch (e: any) { setMessage(e.message); }
    finally { setLoading(false); }
  };

  const strategyOptions = ['gradual', 'aggressive', 'conservative', 'adaptive', 'predictive'];

  const metricFields = [
    { key: 'deaths_per_minute', label: 'Deaths/Minute' },
    { key: 'kill_efficiency', label: 'Kill Efficiency' },
    { key: 'completion_speed', label: 'Completion Speed' },
    { key: 'accuracy', label: 'Accuracy' },
    { key: 'resource_efficiency', label: 'Resource Efficiency' },
    { key: 'damage_taken', label: 'Damage Taken' },
    { key: 'damage_dealt', label: 'Damage Dealt' },
    { key: 'combo_rate', label: 'Combo Rate' },
    { key: 'exploration_rate', label: 'Exploration Rate' },
  ];

  const tabs = ['overview', 'profiles', 'adjust', 'history'];

  return (
    <div className="h-full flex flex-col bg-[#1a1a2e] text-white">
      <div className="flex gap-1 p-3 border-b border-[#2a2a4a]">
        {tabs.map(t => (
          <button key={t} onClick={() => setActiveTab(t)}
            className={`px-4 py-2 rounded text-sm font-medium ${activeTab === t ? 'bg-[#00d4ff] text-black' : 'bg-[#0f0f23] text-[#ccc] hover:bg-[#2a2a4a]'}`}>
            {t.charAt(0).toUpperCase() + t.slice(1)}
          </button>
        ))}
      </div>
      {message && <div className="mx-4 mt-2 p-2 bg-[#0f0f23] border border-[#2a2a4a] rounded text-sm text-[#00d4ff]">{message}</div>}
      <div className="flex-1 overflow-auto p-4">

        {/* Overview Tab */}
        {activeTab === 'overview' && (
          <div className="space-y-4">
            <h2 className="text-lg font-bold text-[#00d4ff]">Dynamic Difficulty System</h2>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <div className="bg-[#0f0f23] p-4 rounded border border-[#2a2a4a]">
                <h3 className="text-[#00d4ff] text-xs">Total Profiles</h3>
                <p className="text-2xl font-bold mt-1">{stats.total_profiles ?? 0}</p>
              </div>
              <div className="bg-[#0f0f23] p-4 rounded border border-[#2a2a4a]">
                <h3 className="text-[#00d4ff] text-xs">Total Adjustments</h3>
                <p className="text-2xl font-bold mt-1">{stats.total_adjustments ?? 0}</p>
              </div>
              <div className="bg-[#0f0f23] p-4 rounded border border-[#2a2a4a]">
                <h3 className="text-[#00d4ff] text-xs">Players Struggling</h3>
                <p className="text-2xl font-bold mt-1 text-[#ff6b6b]">{stats.players_struggling ?? 0}</p>
              </div>
              <div className="bg-[#0f0f23] p-4 rounded border border-[#2a2a4a]">
                <h3 className="text-[#00d4ff] text-xs">Players Bored</h3>
                <p className="text-2xl font-bold mt-1 text-[#ffd93d]">{stats.players_bored ?? 0}</p>
              </div>
            </div>
            {Object.keys(stats).length > 0 && (
              <div className="bg-[#0f0f23] p-4 rounded border border-[#2a2a4a]">
                <h3 className="text-[#00d4ff] text-sm mb-2">All Stats</h3>
                <pre className="text-xs text-[#ccc] overflow-auto">{JSON.stringify(stats, null, 2)}</pre>
              </div>
            )}
          </div>
        )}

        {/* Profiles Tab */}
        {activeTab === 'profiles' && (
          <div className="space-y-6">
            <div className="bg-[#0f0f23] border border-[#2a2a4a] rounded-lg p-4">
              <h2 className="text-lg font-bold text-[#00d4ff] mb-3">Create Difficulty Profile</h2>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-xs text-[#999] mb-1 block">Player ID</label>
                  <input type="text" value={cpPlayerId} onChange={e => setCpPlayerId(e.target.value)}
                    placeholder="player_abc123" className="w-full bg-[#1a1a2e] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none" />
                </div>
                <div>
                  <label className="text-xs text-[#999] mb-1 block">Strategy</label>
                  <select value={cpStrategy} onChange={e => setCpStrategy(e.target.value)}
                    className="w-full bg-[#1a1a2e] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none">
                    {strategyOptions.map(s => (
                      <option key={s} value={s}>{s.charAt(0).toUpperCase() + s.slice(1)}</option>
                    ))}
                  </select>
                </div>
                <div className="col-span-2">
                  <label className="text-xs text-[#999] mb-1 block">Baseline Difficulty</label>
                  <div className="flex items-center gap-3">
                    <input type="range" min="0" max="1" step="0.01"
                      value={baselineDifficulty} onChange={e => setBaselineDifficulty(e.target.value)}
                      className="flex-1 accent-[#00d4ff]" />
                    <span className="text-[#00d4ff] text-sm font-mono w-12 text-right">{baselineDifficulty}</span>
                  </div>
                </div>
              </div>
              <button
                onClick={async () => {
                  if (!cpPlayerId.trim()) { setMessage('Player ID required'); return; }
                  await handlePost(`${API_BASE}/dynamic-difficulty/create-profile`, {
                    player_id: cpPlayerId, baseline_difficulty: parseFloat(baselineDifficulty), strategy: cpStrategy,
                  });
                }}
                disabled={loading}
                className="mt-3 px-4 py-2 bg-[#00d4ff] text-black rounded text-sm font-medium hover:bg-[#00b8e6] disabled:opacity-50">
                Create Profile
              </button>
            </div>

            <div className="bg-[#0f0f23] border border-[#2a2a4a] rounded-lg p-4">
              <h2 className="text-lg font-bold text-[#00d4ff] mb-3">Update Player Metrics</h2>
              <div className="grid grid-cols-3 gap-3">
                {metricFields.map(({ key, label }) => (
                  <div key={key}>
                    <label className="text-xs text-[#999] mb-1 block">{label}</label>
                    <input type="number" step="0.01"
                      value={metrics[key as keyof typeof metrics]}
                      onChange={e => setMetrics(prev => ({ ...prev, [key]: e.target.value }))}
                      placeholder="0.0" className="w-full bg-[#1a1a2e] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none" />
                  </div>
                ))}
              </div>
              <button
                onClick={async () => {
                  if (!umPlayerId.trim()) { setMessage('Player ID required'); return; }
                  const numMetrics: Record<string, number> = {};
                  for (const { key } of metricFields) {
                    numMetrics[key] = parseFloat(metrics[key as keyof typeof metrics]) || 0;
                  }
                  await handlePost(`${API_BASE}/dynamic-difficulty/update-metrics`, { player_id: umPlayerId, metrics: numMetrics });
                }}
                disabled={loading}
                className="mt-3 px-4 py-2 bg-[#00d4ff] text-black rounded text-sm font-medium hover:bg-[#00b8e6] disabled:opacity-50">
                Update Metrics
              </button>
            </div>
          </div>
        )}

        {/* Adjust Tab */}
        {activeTab === 'adjust' && (
          <div className="space-y-6">
            <div className="bg-[#0f0f23] border border-[#2a2a4a] rounded-lg p-4">
              <h2 className="text-lg font-bold text-[#00d4ff] mb-3">Adjust Difficulty</h2>
              <div className="flex gap-3 items-end">
                <div className="flex-1">
                  <label className="text-xs text-[#999] mb-1 block">Player ID</label>
                  <input type="text" value={adjPlayerId} onChange={e => setAdjPlayerId(e.target.value)}
                    placeholder="player_abc123" className="w-full bg-[#1a1a2e] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none" />
                </div>
                <button
                  onClick={async () => {
                    if (!adjPlayerId.trim()) { setMessage('Player ID required'); return; }
                    await handlePost(`${API_BASE}/dynamic-difficulty/adjust`, { player_id: adjPlayerId });
                  }}
                  disabled={loading}
                  className="px-4 py-2 bg-[#00ff88] text-black rounded text-sm font-medium hover:bg-[#00cc6a] disabled:opacity-50">
                  Adjust
                </button>
              </div>
            </div>

            {result && (result.adjustments || result.parameter_changes) && (
              <div className="bg-[#0f0f23] border border-[#2a2a4a] rounded-lg p-4">
                <h2 className="text-lg font-bold text-[#00d4ff] mb-3">Adjustment Results</h2>
                {result.player_state && (
                  <div className="mb-3 flex items-center gap-2">
                    <span className="text-xs text-[#999]">Player State:</span>
                    <span className="text-xs bg-[#1a1a2e] text-[#00d4ff] px-2 py-0.5 rounded border border-[#2a2a4a]">{result.player_state}</span>
                  </div>
                )}
                <div className="space-y-2">
                  {(Array.isArray(result.adjustments) ? result.adjustments : Array.isArray(result.parameter_changes) ? result.parameter_changes : [result]).map((adj: any, i: number) => (
                    <div key={i} className="bg-[#1a1a2e] border border-[#2a2a4a] rounded-lg p-3">
                      <div className="flex items-center justify-between mb-2">
                        <span className="text-white text-sm font-medium">{adj.parameter || adj.name || `Change ${i + 1}`}</span>
                        <span className={`text-xs px-2 py-0.5 rounded ${(adj.new_value ?? 0) > (adj.old_value ?? 0) ? 'bg-green-900 text-green-300' : 'bg-red-900 text-red-300'}`}>
                          {(adj.old_value ?? 0).toFixed(2)} → {(adj.new_value ?? 0).toFixed(2)}
                        </span>
                      </div>
                      <div className="h-2 bg-[#2a2a4a] rounded-full overflow-hidden">
                        <div className="h-full bg-[#00d4ff] rounded-full transition-all"
                          style={{ width: `${Math.min((adj.new_value ?? 0) * 100, 100)}%` }} />
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

        {/* History Tab */}
        {activeTab === 'history' && (
          <div className="space-y-6">
            <div className="bg-[#0f0f23] border border-[#2a2a4a] rounded-lg p-4">
              <h2 className="text-lg font-bold text-[#00d4ff] mb-3">Get Player Profile & History</h2>
              <div className="flex gap-3 items-end">
                <div className="flex-1">
                  <label className="text-xs text-[#999] mb-1 block">Player ID</label>
                  <input type="text" value={histPlayerId} onChange={e => setHistPlayerId(e.target.value)}
                    placeholder="player_abc123" className="w-full bg-[#1a1a2e] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none" />
                </div>
                <button
                  onClick={async () => {
                    if (!histPlayerId.trim()) { setMessage('Player ID required'); return; }
                    await handleGet(`${API_BASE}/dynamic-difficulty/profile?player_id=${histPlayerId}`);
                  }}
                  disabled={loading}
                  className="px-4 py-2 bg-[#00d4ff] text-black rounded text-sm font-medium hover:bg-[#00b8e6] disabled:opacity-50">
                  Get Profile
                </button>
              </div>
            </div>

            {result && (
              <div className="bg-[#0f0f23] border border-[#2a2a4a] rounded-lg p-4">
                <h2 className="text-lg font-bold text-[#00d4ff] mb-3">Profile & History</h2>
                {result.difficulty_history && (
                  <div className="mb-4">
                    <h3 className="text-xs text-[#999] mb-2">Difficulty History</h3>
                    <div className="space-y-1">
                      {(Array.isArray(result.difficulty_history) ? result.difficulty_history : []).map((h: any, i: number) => (
                        <div key={i} className="flex items-center justify-between bg-[#1a1a2e] p-2 rounded border border-[#2a2a4a] text-xs">
                          <span className="text-[#999]">{h.timestamp || `Entry ${i + 1}`}</span>
                          <span className="text-[#00d4ff] font-mono">{h.value ?? JSON.stringify(h)}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
                {result.parameter_values && (
                  <div className="mb-4">
                    <h3 className="text-xs text-[#999] mb-2">Parameter Values</h3>
                    <div className="grid grid-cols-3 gap-2">
                      {Object.entries(result.parameter_values).map(([key, value]) => (
                        <div key={key} className="bg-[#1a1a2e] p-2 rounded border border-[#2a2a4a]">
                          <span className="text-xs text-[#999] capitalize block">{key.replace(/_/g, ' ')}</span>
                          <span className="text-sm text-white font-mono">{String(value)}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
                {result.state_transitions && (
                  <div>
                    <h3 className="text-xs text-[#999] mb-2">State Transitions</h3>
                    <div className="space-y-1">
                      {(Array.isArray(result.state_transitions) ? result.state_transitions : []).map((st: any, i: number) => (
                        <div key={i} className="flex items-center gap-2 bg-[#1a1a2e] p-2 rounded border border-[#2a2a4a] text-xs">
                          <span className="text-[#999]">{st.from}</span>
                          <span className="text-[#00d4ff]">→</span>
                          <span className="text-white">{st.to}</span>
                          {st.reason && <span className="text-[#666] ml-auto">{st.reason}</span>}
                        </div>
                      ))}
                    </div>
                  </div>
                )}
                {!result.difficulty_history && !result.parameter_values && !result.state_transitions && (
                  <pre className="text-xs text-[#ccc] overflow-auto">{JSON.stringify(result, null, 2)}</pre>
                )}
              </div>
            )}
          </div>
        )}

      </div>
    </div>
  );
}