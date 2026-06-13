"use client";
import React, { useState, useEffect, useCallback } from 'react';

const API_BASE = 'http://localhost:8000/api/agent';

export default function AgentAdaptiveCognitionPanel() {
  const [activeTab, setActiveTab] = useState('overview');
  const [stats, setStats] = useState<any>({});
  const [strategies, setStrategies] = useState<any[]>([]);
  const [experiences, setExperiences] = useState<any[]>([]);
  const [cognitiveState, setCognitiveState] = useState<any>({});
  const [message, setMessage] = useState('');
  const [loading, setLoading] = useState(false);

  // Strategy form
  const [strategyName, setStrategyName] = useState('');
  const [strategyType, setStrategyType] = useState('learning');
  const [strategyConfig, setStrategyConfig] = useState('{}');

  // Experience form
  const [expContext, setExpContext] = useState('');
  const [expAction, setExpAction] = useState('');
  const [expOutcome, setExpOutcome] = useState('');
  const [expReward, setExpReward] = useState('0');

  // State form
  const [stateUpdate, setStateUpdate] = useState<Record<string, number>>({});

  const fetchStats = useCallback(async () => {
    try { const r = await fetch(`${API_BASE}/adaptive-cognition/stats`); if (r.ok) setStats(await r.json()); } catch (e) { console.error(e); }
  }, []);

  const fetchStrategies = useCallback(async () => {
    try { const r = await fetch(`${API_BASE}/adaptive-cognition/strategies`); if (r.ok) { const d = await r.json(); setStrategies(d.strategies || d || []); } } catch (e) { console.error(e); }
  }, []);

  const fetchExperiences = useCallback(async () => {
    try { const r = await fetch(`${API_BASE}/adaptive-cognition/experiences`); if (r.ok) { const d = await r.json(); setExperiences(d.experiences || d || []); } } catch (e) { console.error(e); }
  }, []);

  const fetchCognitiveState = useCallback(async () => {
    try { const r = await fetch(`${API_BASE}/adaptive-cognition/cognitive-state`); if (r.ok) { const d = await r.json(); setCognitiveState(d); setStateUpdate(d.params || d); } } catch (e) { console.error(e); }
  }, []);

  useEffect(() => {
    fetchStats();
    fetchStrategies();
    fetchExperiences();
    fetchCognitiveState();
    const i = setInterval(fetchStats, 15000);
    return () => clearInterval(i);
  }, [fetchStats, fetchStrategies, fetchExperiences, fetchCognitiveState]);

  const handleSubmit = async (url: string, body: any) => {
    setLoading(true);
    try {
      const r = await fetch(url, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });
      const data = await r.json();
      setMessage(r.ok ? 'Success' : data.error || 'Failed');
      setLoading(false);
      return data;
    } catch (e: any) { setMessage(e.message); setLoading(false); }
  };

  const handleGet = async (url: string) => {
    try { const r = await fetch(url); if (r.ok) return await r.json(); } catch (e) { console.error(e); }
    return null;
  };

  const tabs = ['overview', 'strategies', 'experiences', 'state'];

  return (
    <div className="h-full flex flex-col bg-[#1a1a2e] text-white">
      <div className="flex gap-1 p-3 border-b border-[#2a2a4a]">
        {tabs.map(t => (
          <button key={t} onClick={() => setActiveTab(t)}
            className={`px-4 py-2 rounded text-sm font-medium ${activeTab === t ? 'bg-[#00d4ff] text-black' : 'bg-[#0f0f23] text-gray-300 hover:bg-[#2a2a4a]'}`}>
            {t.charAt(0).toUpperCase() + t.slice(1)}
          </button>
        ))}
      </div>
      {message && <div className="mx-4 mt-2 p-2 bg-[#0f0f23] border border-[#2a2a4a] rounded text-sm text-[#00d4ff]">{message}</div>}
      <div className="flex-1 overflow-auto p-4">

        {/* Overview Tab */}
        {activeTab === 'overview' && (
          <div className="space-y-4">
            <h2 className="text-lg font-bold text-[#00d4ff]">Adaptive Cognition System</h2>
            <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
              {Object.entries(stats).map(([key, value]) => (
                <div key={key} className="bg-[#0f0f23] p-4 rounded border border-[#2a2a4a]">
                  <h3 className="text-[#00d4ff] text-xs capitalize">{key.replace(/_/g, ' ')}</h3>
                  <p className="text-2xl font-bold mt-1">
                    {typeof value === 'number' ? value.toLocaleString() : String(value)}
                  </p>
                </div>
              ))}
              {Object.keys(stats).length === 0 && (
                <div className="col-span-full text-gray-400 text-sm">No stats available</div>
              )}
            </div>
          </div>
        )}

        {/* Strategies Tab */}
        {activeTab === 'strategies' && (
          <div className="space-y-4">
            <div className="bg-[#0f0f23] border border-[#2a2a4a] rounded-lg p-4">
              <h2 className="text-lg font-bold text-[#00d4ff] mb-3">Register Strategy</h2>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-xs text-gray-400 mb-1 block">Strategy Name</label>
                  <input type="text" value={strategyName} onChange={e => setStrategyName(e.target.value)}
                    placeholder="exploration_strategy" className="w-full bg-[#1a1a2e] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none" />
                </div>
                <div>
                  <label className="text-xs text-gray-400 mb-1 block">Strategy Type</label>
                  <select value={strategyType} onChange={e => setStrategyType(e.target.value)}
                    className="w-full bg-[#1a1a2e] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none">
                    <option value="learning">Learning</option>
                    <option value="exploration">Exploration</option>
                    <option value="exploitation">Exploitation</option>
                    <option value="adaptive">Adaptive</option>
                    <option value="heuristic">Heuristic</option>
                  </select>
                </div>
                <div className="col-span-2">
                  <label className="text-xs text-gray-400 mb-1 block">Configuration (JSON)</label>
                  <textarea value={strategyConfig} onChange={e => setStrategyConfig(e.target.value)}
                    rows={3} placeholder='{"learning_rate": 0.01, "epsilon": 0.1}'
                    className="w-full bg-[#1a1a2e] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm font-mono focus:border-[#00d4ff] focus:outline-none" />
                </div>
              </div>
              <button onClick={async () => {
                if (!strategyName.trim()) { setMessage('Strategy name required'); return; }
                let config = {};
                try { config = JSON.parse(strategyConfig || '{}'); } catch { setMessage('Invalid JSON config'); return; }
                await handleSubmit(`${API_BASE}/adaptive-cognition/register-strategy`,
                  { name: strategyName, type: strategyType, config });
                setStrategyName('');
                setStrategyConfig('{}');
                fetchStrategies();
              }} disabled={loading}
                className="mt-3 px-4 py-2 bg-[#00d4ff] text-black rounded text-sm font-medium hover:bg-[#00b8e6] disabled:opacity-50">
                Register Strategy
              </button>
            </div>

            <div className="bg-[#0f0f23] border border-[#2a2a4a] rounded-lg p-4">
              <h2 className="text-lg font-bold text-[#00d4ff] mb-3">Strategies ({strategies.length})</h2>
              {strategies.length > 0 ? (
                <div className="space-y-2">
                  {strategies.map((s, i) => (
                    <div key={s.id || i} className="bg-[#1a1a2e] border border-[#2a2a4a] rounded-lg p-3">
                      <div className="flex items-center justify-between">
                        <span className="text-white text-sm font-medium">{s.name || s.id}</span>
                        <span className="text-xs bg-[#0f0f23] text-[#00d4ff] px-2 py-0.5 rounded">{s.type || 'unknown'}</span>
                      </div>
                      {s.config && <div className="mt-1 text-xs text-gray-400 font-mono">{JSON.stringify(s.config)}</div>}
                    </div>
                  ))}
                </div>
              ) : (
                <div className="text-gray-400 text-xs">No strategies registered</div>
              )}
            </div>
          </div>
        )}

        {/* Experiences Tab */}
        {activeTab === 'experiences' && (
          <div className="space-y-4">
            <div className="bg-[#0f0f23] border border-[#2a2a4a] rounded-lg p-4">
              <h2 className="text-lg font-bold text-[#00d4ff] mb-3">Record Experience</h2>
              <div className="grid grid-cols-2 gap-3">
                <div className="col-span-2">
                  <label className="text-xs text-gray-400 mb-1 block">Context</label>
                  <input type="text" value={expContext} onChange={e => setExpContext(e.target.value)}
                    placeholder="e.g. combat_scenario_1" className="w-full bg-[#1a1a2e] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none" />
                </div>
                <div>
                  <label className="text-xs text-gray-400 mb-1 block">Action</label>
                  <input type="text" value={expAction} onChange={e => setExpAction(e.target.value)}
                    placeholder="e.g. attack_heavy" className="w-full bg-[#1a1a2e] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none" />
                </div>
                <div>
                  <label className="text-xs text-gray-400 mb-1 block">Reward</label>
                  <input type="number" value={expReward} onChange={e => setExpReward(e.target.value)}
                    step="0.01" placeholder="0.0" className="w-full bg-[#1a1a2e] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none" />
                </div>
                <div className="col-span-2">
                  <label className="text-xs text-gray-400 mb-1 block">Outcome</label>
                  <input type="text" value={expOutcome} onChange={e => setExpOutcome(e.target.value)}
                    placeholder="e.g. enemy_defeated" className="w-full bg-[#1a1a2e] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none" />
                </div>
              </div>
              <button onClick={async () => {
                if (!expContext.trim() || !expAction.trim()) { setMessage('Context and action required'); return; }
                await handleSubmit(`${API_BASE}/adaptive-cognition/record-experience`, {
                  context: expContext, action: expAction, outcome: expOutcome,
                  reward: parseFloat(expReward) || 0,
                });
                setExpContext(''); setExpAction(''); setExpOutcome(''); setExpReward('0');
                fetchExperiences();
              }} disabled={loading}
                className="mt-3 px-4 py-2 bg-[#00d4ff] text-black rounded text-sm font-medium hover:bg-[#00b8e6] disabled:opacity-50">
                Record Experience
              </button>
            </div>

            <div className="bg-[#0f0f23] border border-[#2a2a4a] rounded-lg p-4">
              <h2 className="text-lg font-bold text-[#00d4ff] mb-3">Experiences ({experiences.length})</h2>
              {experiences.length > 0 ? (
                <div className="space-y-2">
                  {experiences.map((e, i) => (
                    <div key={e.id || i} className="bg-[#1a1a2e] border border-[#2a2a4a] rounded-lg p-3">
                      <div className="flex items-center justify-between">
                        <span className="text-white text-sm font-medium">{e.context || e.action}</span>
                        <span className={`text-xs font-mono px-2 py-0.5 rounded ${(e.reward || 0) > 0 ? 'bg-green-900 text-green-300' : 'bg-red-900 text-red-300'}`}>
                          Reward: {e.reward ?? 0}
                        </span>
                      </div>
                      <div className="flex items-center gap-4 text-xs text-gray-400 mt-1">
                        <span>Action: <span className="text-white">{e.action}</span></span>
                        <span>Outcome: <span className="text-white">{e.outcome || 'N/A'}</span></span>
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="text-gray-400 text-xs">No experiences recorded</div>
              )}
            </div>
          </div>
        )}

        {/* State Tab */}
        {activeTab === 'state' && (
          <div className="space-y-4">
            <div className="bg-[#0f0f23] border border-[#2a2a4a] rounded-lg p-4">
              <h2 className="text-lg font-bold text-[#00d4ff] mb-3">Cognitive State</h2>
              {Object.keys(cognitiveState).length > 0 ? (
                <div className="space-y-3">
                  {Object.entries(cognitiveState).filter(([k]) => k !== 'params' && k !== 'state').map(([key, value]) => (
                    <div key={key} className="flex justify-between bg-[#1a1a2e] rounded px-3 py-2">
                      <span className="text-gray-400 text-xs capitalize">{key.replace(/_/g, ' ')}</span>
                      <span className="text-white text-xs font-mono">{String(value)}</span>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="text-gray-400 text-xs">Loading cognitive state...</div>
              )}
            </div>

            <div className="bg-[#0f0f23] border border-[#2a2a4a] rounded-lg p-4">
              <h2 className="text-lg font-bold text-[#00d4ff] mb-3">Update State Parameters</h2>
              {Object.keys(stateUpdate).length > 0 ? (
                <div className="space-y-4">
                  {Object.entries(stateUpdate).map(([key, value]) => (
                    <div key={key}>
                      <div className="flex justify-between mb-1">
                        <label className="text-xs text-gray-400 capitalize">{key.replace(/_/g, ' ')}</label>
                        <span className="text-xs text-[#00d4ff] font-mono">
                          {typeof value === 'number' ? value.toFixed(2) : String(value)}
                        </span>
                      </div>
                      <input type="range" min="0" max="100" step="1"
                        value={typeof value === 'number' ? Math.round(value * 100) : 50}
                        onChange={e => setStateUpdate(prev => ({ ...prev, [key]: parseInt(e.target.value) / 100 }))}
                        className="w-full accent-[#00d4ff]" />
                    </div>
                  ))}
                  <button onClick={async () => {
                    await handleSubmit(`${API_BASE}/adaptive-cognition/update-state`, stateUpdate);
                    fetchCognitiveState();
                  }} disabled={loading}
                    className="mt-3 px-4 py-2 bg-[#00d4ff] text-black rounded text-sm font-medium hover:bg-[#00b8e6] disabled:opacity-50">
                    Update State
                  </button>
                </div>
              ) : (
                <div className="text-gray-400 text-xs">No adjustable parameters available</div>
              )}
            </div>
          </div>
        )}

      </div>
    </div>
  );
}