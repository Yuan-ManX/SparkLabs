"use client";
import React, { useState, useEffect, useCallback } from 'react';

const API_BASE = 'http://localhost:8000/api/agent';

export default function AgentPlaytestingPanel() {
  const [activeTab, setActiveTab] = useState('overview');
  const [stats, setStats] = useState<any>({});
  const [message, setMessage] = useState('');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<any>(null);

  // Session form
  const [gameId, setGameId] = useState('');
  const [testTypes, setTestTypes] = useState<string[]>(['functional']);
  const [gameConfig, setGameConfig] = useState('{}');

  // Run test suite
  const [runSessionId, setRunSessionId] = useState('');

  // Simulate
  const [simSessionId, setSimSessionId] = useState('');
  const [durationSeconds, setDurationSeconds] = useState('60');

  // Bug report
  const [bugSessionId, setBugSessionId] = useState('');
  const [bugTitle, setBugTitle] = useState('');
  const [bugDescription, setBugDescription] = useState('');
  const [bugSeverity, setBugSeverity] = useState('medium');
  const [bugCategory, setBugCategory] = useState('gameplay');
  const [bugRepro, setBugRepro] = useState('');
  const [bugExpected, setBugExpected] = useState('');
  const [bugActual, setBugActual] = useState('');
  const [bugLocation, setBugLocation] = useState('');

  const fetchStats = useCallback(async () => {
    try { const r = await fetch(`${API_BASE}/playtesting/stats`); if (r.ok) setStats(await r.json()); } catch (e) { console.error(e); }
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

  const testTypeOptions = ['functional', 'balance', 'performance', 'usability', 'completion', 'stress', 'regression', 'exploratory'];

  const toggleTestType = (t: string) => {
    setTestTypes(prev => prev.includes(t) ? prev.filter(x => x !== t) : [...prev, t]);
  };

  const severityColors: Record<string, string> = {
    low: 'bg-blue-900 text-blue-300',
    medium: 'bg-yellow-900 text-yellow-300',
    high: 'bg-orange-900 text-orange-300',
    critical: 'bg-red-900 text-red-300',
  };

  const tabs = ['overview', 'sessions', 'simulate', 'bugs'];

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
            <h2 className="text-lg font-bold text-[#00d4ff]">Playtesting System</h2>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <div className="bg-[#0f0f23] p-4 rounded border border-[#2a2a4a]">
                <h3 className="text-[#00d4ff] text-xs">Total Sessions</h3>
                <p className="text-2xl font-bold mt-1">{stats.stats?.total_sessions ?? stats.total_sessions ?? 0}</p>
              </div>
              <div className="bg-[#0f0f23] p-4 rounded border border-[#2a2a4a]">
                <h3 className="text-[#00d4ff] text-xs">Total Tests</h3>
                <p className="text-2xl font-bold mt-1">{stats.stats?.total_tests ?? stats.total_tests ?? 0}</p>
              </div>
              <div className="bg-[#0f0f23] p-4 rounded border border-[#2a2a4a]">
                <h3 className="text-[#00d4ff] text-xs">Bugs Found</h3>
                <p className="text-2xl font-bold mt-1">{stats.stats?.bugs_found ?? stats.bugs_found ?? 0}</p>
              </div>
              <div className="bg-[#0f0f23] p-4 rounded border border-[#2a2a4a]">
                <h3 className="text-[#00d4ff] text-xs">Pass Rate</h3>
                <p className="text-2xl font-bold mt-1">
                  {stats.stats?.pass_rate != null
                    ? (stats.stats.pass_rate * 100).toFixed(1) + '%'
                    : stats.pass_rate != null
                      ? (stats.pass_rate * 100).toFixed(1) + '%'
                      : 'N/A'}
                </p>
              </div>
            </div>
            {Object.keys(stats).length > 0 && (
              <div className="bg-[#0f0f23] p-4 rounded border border-[#2a2a4a]">
                <h3 className="text-[#00d4ff] text-sm mb-2">All Stats</h3>
                <pre className="text-xs text-gray-300 overflow-auto">{JSON.stringify(stats, null, 2)}</pre>
              </div>
            )}
          </div>
        )}

        {/* Sessions Tab */}
        {activeTab === 'sessions' && (
          <div className="space-y-6">
            <div className="bg-[#0f0f23] border border-[#2a2a4a] rounded-lg p-4">
              <h2 className="text-lg font-bold text-[#00d4ff] mb-3">Create Playtesting Session</h2>
              <div className="space-y-3">
                <div>
                  <label className="text-xs text-gray-400 mb-1 block">Game ID</label>
                  <input type="text" value={gameId} onChange={e => setGameId(e.target.value)}
                    placeholder="game_abc123" className="w-full bg-[#1a1a2e] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none" />
                </div>
                <div>
                  <label className="text-xs text-gray-400 mb-1 block">Test Types</label>
                  <div className="flex flex-wrap gap-2">
                    {testTypeOptions.map(t => (
                      <label key={t} className="flex items-center gap-1.5 cursor-pointer">
                        <input type="checkbox" checked={testTypes.includes(t)} onChange={() => toggleTestType(t)}
                          className="accent-[#00d4ff]" />
                        <span className="text-xs text-gray-300 capitalize">{t}</span>
                      </label>
                    ))}
                  </div>
                </div>
                <div>
                  <label className="text-xs text-gray-400 mb-1 block">Game Config (JSON)</label>
                  <textarea value={gameConfig} onChange={e => setGameConfig(e.target.value)}
                    rows={4} placeholder='{"difficulty": "normal", "version": "1.0.0"}'
                    className="w-full bg-[#1a1a2e] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm font-mono focus:border-[#00d4ff] focus:outline-none" />
                </div>
                <button
                  onClick={async () => {
                    if (!gameId.trim()) { setMessage('Game ID required'); return; }
                    let config = {};
                    try { config = JSON.parse(gameConfig || '{}'); } catch { setMessage('Invalid game config JSON'); return; }
                    await handlePost(`${API_BASE}/playtesting/create-session`, { game_id: gameId, test_types: testTypes, game_config: config });
                  }}
                  disabled={loading}
                  className="px-4 py-2 bg-[#00d4ff] text-black rounded text-sm font-medium hover:bg-[#00b8e6] disabled:opacity-50">
                  Create Session
                </button>
              </div>
            </div>

            <div className="bg-[#0f0f23] border border-[#2a2a4a] rounded-lg p-4">
              <h2 className="text-lg font-bold text-[#00d4ff] mb-3">Run Test Suite</h2>
              <div className="flex gap-3 items-end">
                <div className="flex-1">
                  <label className="text-xs text-gray-400 mb-1 block">Session ID</label>
                  <input type="text" value={runSessionId} onChange={e => setRunSessionId(e.target.value)}
                    placeholder="session_abc123" className="w-full bg-[#1a1a2e] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none" />
                </div>
                <button
                  onClick={async () => {
                    if (!runSessionId.trim()) { setMessage('Session ID required'); return; }
                    await handlePost(`${API_BASE}/playtesting/run-test-suite`, { session_id: runSessionId });
                  }}
                  disabled={loading}
                  className="px-4 py-2 bg-[#00ff88] text-black rounded text-sm font-medium hover:bg-[#00cc6a] disabled:opacity-50">
                  Run Test Suite
                </button>
              </div>
            </div>

            {result && (
              <div className="bg-[#0f0f23] border border-[#2a2a4a] rounded-lg p-4">
                <h2 className="text-lg font-bold text-[#00d4ff] mb-3">Test Results</h2>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-3">
                  <div className="bg-[#1a1a2e] p-3 rounded border border-[#2a2a4a]">
                    <span className="text-xs text-gray-400">Score</span>
                    <p className="text-xl font-bold text-[#00ff88]">{result.score ?? 'N/A'}</p>
                  </div>
                  <div className="bg-[#1a1a2e] p-3 rounded border border-[#2a2a4a]">
                    <span className="text-xs text-gray-400">Fun Rating</span>
                    <p className="text-xl font-bold text-[#00d4ff]">{result.fun_rating ?? 'N/A'}</p>
                  </div>
                  <div className="bg-[#1a1a2e] p-3 rounded border border-[#2a2a4a]">
                    <span className="text-xs text-gray-400">Balance Score</span>
                    <p className="text-xl font-bold text-[#00d4ff]">{result.balance_score ?? 'N/A'}</p>
                  </div>
                  <div className="bg-[#1a1a2e] p-3 rounded border border-[#2a2a4a]">
                    <span className="text-xs text-gray-400">Recommendations</span>
                    <p className="text-sm text-white mt-1">
                      {Array.isArray(result.recommendations) ? result.recommendations.length : 0}
                    </p>
                  </div>
                </div>
                {result.recommendations && Array.isArray(result.recommendations) && (
                  <div className="space-y-1">
                    {result.recommendations.map((r: string, i: number) => (
                      <div key={i} className="text-xs text-gray-300 bg-[#1a1a2e] p-2 rounded border border-[#2a2a4a]">• {r}</div>
                    ))}
                  </div>
                )}
              </div>
            )}
          </div>
        )}

        {/* Simulate Tab */}
        {activeTab === 'simulate' && (
          <div className="space-y-6">
            <div className="bg-[#0f0f23] border border-[#2a2a4a] rounded-lg p-4">
              <h2 className="text-lg font-bold text-[#00d4ff] mb-3">Simulate Gameplay</h2>
              <div className="space-y-3">
                <div>
                  <label className="text-xs text-gray-400 mb-1 block">Session ID</label>
                  <input type="text" value={simSessionId} onChange={e => setSimSessionId(e.target.value)}
                    placeholder="session_abc123" className="w-full bg-[#1a1a2e] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none" />
                </div>
                <div>
                  <label className="text-xs text-gray-400 mb-1 block">Duration (seconds)</label>
                  <input type="number" value={durationSeconds} onChange={e => setDurationSeconds(e.target.value)}
                    min="1" placeholder="60" className="w-full bg-[#1a1a2e] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none" />
                </div>
                <button
                  onClick={async () => {
                    if (!simSessionId.trim()) { setMessage('Session ID required'); return; }
                    await handlePost(`${API_BASE}/playtesting/simulate`, { session_id: simSessionId, duration_seconds: parseInt(durationSeconds) || 60 });
                  }}
                  disabled={loading}
                  className="px-4 py-2 bg-[#00d4ff] text-black rounded text-sm font-medium hover:bg-[#00b8e6] disabled:opacity-50">
                  Start Simulation
                </button>
              </div>
            </div>

            {result && (
              <div className="bg-[#0f0f23] border border-[#2a2a4a] rounded-lg p-4">
                <h2 className="text-lg font-bold text-[#00d4ff] mb-3">Simulation Metrics</h2>
                <div className="grid grid-cols-2 gap-4">
                  <div className="bg-[#1a1a2e] p-3 rounded border border-[#2a2a4a]">
                    <span className="text-xs text-gray-400">Movement</span>
                    <p className="text-xl font-bold text-white">{result.movement ?? '0'}%</p>
                    <div className="mt-1 h-1.5 bg-[#2a2a4a] rounded-full">
                      <div className="h-full bg-[#00d4ff] rounded-full" style={{ width: `${Math.min(result.movement || 0, 100)}%` }} />
                    </div>
                  </div>
                  <div className="bg-[#1a1a2e] p-3 rounded border border-[#2a2a4a]">
                    <span className="text-xs text-gray-400">Combat</span>
                    <p className="text-xl font-bold text-white">{result.combat ?? '0'}%</p>
                    <div className="mt-1 h-1.5 bg-[#2a2a4a] rounded-full">
                      <div className="h-full bg-[#ff6b6b] rounded-full" style={{ width: `${Math.min(result.combat || 0, 100)}%` }} />
                    </div>
                  </div>
                  <div className="bg-[#1a1a2e] p-3 rounded border border-[#2a2a4a]">
                    <span className="text-xs text-gray-400">Collectibles</span>
                    <p className="text-xl font-bold text-white">{result.collectibles ?? '0'}%</p>
                    <div className="mt-1 h-1.5 bg-[#2a2a4a] rounded-full">
                      <div className="h-full bg-[#ffd93d] rounded-full" style={{ width: `${Math.min(result.collectibles || 0, 100)}%` }} />
                    </div>
                  </div>
                  <div className="bg-[#1a1a2e] p-3 rounded border border-[#2a2a4a]">
                    <span className="text-xs text-gray-400">Exploration</span>
                    <p className="text-xl font-bold text-white">{result.exploration ?? '0'}%</p>
                    <div className="mt-1 h-1.5 bg-[#2a2a4a] rounded-full">
                      <div className="h-full bg-[#00ff88] rounded-full" style={{ width: `${Math.min(result.exploration || 0, 100)}%` }} />
                    </div>
                  </div>
                </div>
                {result.raw && (
                  <pre className="mt-4 text-xs text-gray-300 bg-[#1a1a2e] p-3 rounded border border-[#2a2a4a] overflow-auto">{JSON.stringify(result, null, 2)}</pre>
                )}
              </div>
            )}
          </div>
        )}

        {/* Bugs Tab */}
        {activeTab === 'bugs' && (
          <div className="space-y-6">
            <div className="bg-[#0f0f23] border border-[#2a2a4a] rounded-lg p-4">
              <h2 className="text-lg font-bold text-[#00d4ff] mb-3">Report Bug</h2>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-xs text-gray-400 mb-1 block">Session ID</label>
                  <input type="text" value={bugSessionId} onChange={e => setBugSessionId(e.target.value)}
                    placeholder="session_abc123" className="w-full bg-[#1a1a2e] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none" />
                </div>
                <div>
                  <label className="text-xs text-gray-400 mb-1 block">Title</label>
                  <input type="text" value={bugTitle} onChange={e => setBugTitle(e.target.value)}
                    placeholder="Player falls through floor" className="w-full bg-[#1a1a2e] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none" />
                </div>
                <div className="col-span-2">
                  <label className="text-xs text-gray-400 mb-1 block">Description</label>
                  <textarea value={bugDescription} onChange={e => setBugDescription(e.target.value)}
                    rows={2} placeholder="Describe the bug..." className="w-full bg-[#1a1a2e] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none" />
                </div>
                <div>
                  <label className="text-xs text-gray-400 mb-1 block">Severity</label>
                  <select value={bugSeverity} onChange={e => setBugSeverity(e.target.value)}
                    className="w-full bg-[#1a1a2e] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none">
                    <option value="low">Low</option>
                    <option value="medium">Medium</option>
                    <option value="high">High</option>
                    <option value="critical">Critical</option>
                  </select>
                </div>
                <div>
                  <label className="text-xs text-gray-400 mb-1 block">Category</label>
                  <select value={bugCategory} onChange={e => setBugCategory(e.target.value)}
                    className="w-full bg-[#1a1a2e] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none">
                    <option value="gameplay">Gameplay</option>
                    <option value="graphics">Graphics</option>
                    <option value="audio">Audio</option>
                    <option value="ui">UI</option>
                    <option value="physics">Physics</option>
                    <option value="networking">Networking</option>
                    <option value="performance">Performance</option>
                    <option value="other">Other</option>
                  </select>
                </div>
                <div>
                  <label className="text-xs text-gray-400 mb-1 block">Location</label>
                  <input type="text" value={bugLocation} onChange={e => setBugLocation(e.target.value)}
                    placeholder="Level 3, near waterfall" className="w-full bg-[#1a1a2e] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none" />
                </div>
                <div>
                  <label className="text-xs text-gray-400 mb-1 block">Reproduction Steps</label>
                  <textarea value={bugRepro} onChange={e => setBugRepro(e.target.value)}
                    rows={2} placeholder="1. Step one&#10;2. Step two" className="w-full bg-[#1a1a2e] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none" />
                </div>
                <div>
                  <label className="text-xs text-gray-400 mb-1 block">Expected Behavior</label>
                  <textarea value={bugExpected} onChange={e => setBugExpected(e.target.value)}
                    rows={2} placeholder="What should happen" className="w-full bg-[#1a1a2e] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none" />
                </div>
                <div>
                  <label className="text-xs text-gray-400 mb-1 block">Actual Behavior</label>
                  <textarea value={bugActual} onChange={e => setBugActual(e.target.value)}
                    rows={2} placeholder="What actually happens" className="w-full bg-[#1a1a2e] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none" />
                </div>
              </div>
              <button
                onClick={async () => {
                  if (!bugSessionId.trim()) { setMessage('Session ID required'); return; }
                  if (!bugTitle.trim()) { setMessage('Bug title required'); return; }
                  await handlePost(`${API_BASE}/playtesting/report-bug`, {
                    session_id: bugSessionId, title: bugTitle, description: bugDescription,
                    severity: bugSeverity, category: bugCategory, reproduction_steps: bugRepro,
                    expected: bugExpected, actual: bugActual, location: bugLocation,
                  });
                  setBugTitle(''); setBugDescription(''); setBugRepro(''); setBugExpected(''); setBugActual(''); setBugLocation('');
                }}
                disabled={loading}
                className="mt-3 px-4 py-2 bg-[#00d4ff] text-black rounded text-sm font-medium hover:bg-[#00b8e6] disabled:opacity-50">
                Report Bug
              </button>
            </div>

            {result && (result.bugs || result.title) && (
              <div className="bg-[#0f0f23] border border-[#2a2a4a] rounded-lg p-4">
                <h2 className="text-lg font-bold text-[#00d4ff] mb-3">Bugs</h2>
                <div className="space-y-2">
                  {(Array.isArray(result.bugs) ? result.bugs : [result]).map((bug: any, i: number) => (
                    <div key={bug.id || i} className="bg-[#1a1a2e] border border-[#2a2a4a] rounded-lg p-3">
                      <div className="flex items-center justify-between mb-1">
                        <span className="text-white text-sm font-medium">{bug.title || 'Untitled Bug'}</span>
                        <span className={`text-xs px-2 py-0.5 rounded font-mono ${severityColors[bug.severity] || 'bg-gray-700 text-gray-300'}`}>
                          {bug.severity || 'unknown'}
                        </span>
                      </div>
                      <div className="flex items-center gap-4 text-xs text-gray-400">
                        <span>Category: <span className="text-white">{bug.category || 'N/A'}</span></span>
                        {bug.location && <span>Location: <span className="text-white">{bug.location}</span></span>}
                      </div>
                      {bug.description && <p className="text-xs text-gray-400 mt-1">{bug.description}</p>}
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

      </div>
    </div>
  );
}