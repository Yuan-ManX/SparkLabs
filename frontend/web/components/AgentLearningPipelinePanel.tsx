"use client";
import React, { useState, useEffect, useCallback } from 'react';
import { API_BASE as API_ROOT } from '../utils/api';

const API_BASE = API_ROOT + '/agent';

export default function AgentLearningPipelinePanel() {
  const [activeTab, setActiveTab] = useState('overview');
  const [stats, setStats] = useState<any>({});
  const [message, setMessage] = useState('');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<any>(null);

  // Start session
  const [ssPlayerId, setSsPlayerId] = useState('');
  const [ssMetadata, setSsMetadata] = useState('{}');

  // Record observation
  const [obsSessionId, setObsSessionId] = useState('');
  const [obsPlayerId, setObsPlayerId] = useState('');
  const [obsType, setObsType] = useState('player_action');
  const [obsData, setObsData] = useState('{}');

  // End session
  const [endSessionId, setEndSessionId] = useState('');
  const [endPlayerId, setEndPlayerId] = useState('');
  const [endOutcome, setEndOutcome] = useState('{}');

  // Analyze patterns
  const [analyzePlayerId, setAnalyzePlayerId] = useState('');

  // Build profile
  const [profilePlayerId, setProfilePlayerId] = useState('');

  const fetchStats = useCallback(async () => {
    try { const r = await fetch(`${API_BASE}/learning-pipeline/stats`); if (r.ok) setStats(await r.json()); } catch (e) { console.error(e); }
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

  const obsTypeOptions = [
    'player_action', 'game_event', 'performance', 'interaction',
    'progression', 'error', 'engagement', 'retention',
  ];

  const confidenceColors: Record<string, string> = {
    LOW: 'bg-yellow-900 text-yellow-300',
    MEDIUM: 'bg-orange-900 text-orange-300',
    HIGH: 'bg-green-900 text-green-300',
    VERY_HIGH: 'bg-blue-900 text-blue-300',
    low: 'bg-yellow-900 text-yellow-300',
    medium: 'bg-orange-900 text-orange-300',
    high: 'bg-green-900 text-green-300',
    very_high: 'bg-blue-900 text-blue-300',
  };

  const tabs = ['overview', 'sessions', 'insights', 'profiles'];

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
            <h2 className="text-lg font-bold text-[#00d4ff]">Learning Pipeline</h2>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <div className="bg-[#0f0f23] p-4 rounded border border-[#2a2a4a]">
                <h3 className="text-[#00d4ff] text-xs">Total Sessions</h3>
                <p className="text-2xl font-bold mt-1">{stats.total_sessions ?? 0}</p>
              </div>
              <div className="bg-[#0f0f23] p-4 rounded border border-[#2a2a4a]">
                <h3 className="text-[#00d4ff] text-xs">Total Observations</h3>
                <p className="text-2xl font-bold mt-1">{stats.total_observations ?? 0}</p>
              </div>
              <div className="bg-[#0f0f23] p-4 rounded border border-[#2a2a4a]">
                <h3 className="text-[#00d4ff] text-xs">Insights Generated</h3>
                <p className="text-2xl font-bold mt-1">{stats.insights_generated ?? 0}</p>
              </div>
              <div className="bg-[#0f0f23] p-4 rounded border border-[#2a2a4a]">
                <h3 className="text-[#00d4ff] text-xs">Player Profiles</h3>
                <p className="text-2xl font-bold mt-1">{stats.player_profiles ?? 0}</p>
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

        {/* Sessions Tab */}
        {activeTab === 'sessions' && (
          <div className="space-y-6">
            <div className="bg-[#0f0f23] border border-[#2a2a4a] rounded-lg p-4">
              <h2 className="text-lg font-bold text-[#00d4ff] mb-3">Start Learning Session</h2>
              <div className="space-y-3">
                <div>
                  <label className="text-xs text-[#999] mb-1 block">Player ID</label>
                  <input type="text" value={ssPlayerId} onChange={e => setSsPlayerId(e.target.value)}
                    placeholder="player_abc123" className="w-full bg-[#1a1a2e] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none" />
                </div>
                <div>
                  <label className="text-xs text-[#999] mb-1 block">Metadata (JSON)</label>
                  <textarea value={ssMetadata} onChange={e => setSsMetadata(e.target.value)}
                    rows={3} placeholder='{"level": 5, "region": "US"}' className="w-full bg-[#1a1a2e] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm font-mono focus:border-[#00d4ff] focus:outline-none" />
                </div>
                <button
                  onClick={async () => {
                    if (!ssPlayerId.trim()) { setMessage('Player ID required'); return; }
                    let meta = {};
                    try { meta = JSON.parse(ssMetadata || '{}'); } catch { setMessage('Invalid metadata JSON'); return; }
                    await handlePost(`${API_BASE}/learning-pipeline/start-session`, { player_id: ssPlayerId, metadata: meta });
                  }}
                  disabled={loading}
                  className="px-4 py-2 bg-[#00d4ff] text-black rounded text-sm font-medium hover:bg-[#00b8e6] disabled:opacity-50">
                  Start Session
                </button>
              </div>
            </div>

            <div className="bg-[#0f0f23] border border-[#2a2a4a] rounded-lg p-4">
              <h2 className="text-lg font-bold text-[#00d4ff] mb-3">Record Observation</h2>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-xs text-[#999] mb-1 block">Session ID</label>
                  <input type="text" value={obsSessionId} onChange={e => setObsSessionId(e.target.value)}
                    placeholder="session_abc123" className="w-full bg-[#1a1a2e] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none" />
                </div>
                <div>
                  <label className="text-xs text-[#999] mb-1 block">Player ID</label>
                  <input type="text" value={obsPlayerId} onChange={e => setObsPlayerId(e.target.value)}
                    placeholder="player_abc123" className="w-full bg-[#1a1a2e] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none" />
                </div>
                <div>
                  <label className="text-xs text-[#999] mb-1 block">Observation Type</label>
                  <select value={obsType} onChange={e => setObsType(e.target.value)}
                    className="w-full bg-[#1a1a2e] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none">
                    {obsTypeOptions.map(o => (
                      <option key={o} value={o}>{o.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())}</option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="text-xs text-[#999] mb-1 block">Data (JSON)</label>
                  <textarea value={obsData} onChange={e => setObsData(e.target.value)}
                    rows={3} placeholder='{"action": "jump", "position": [10, 20]}' className="w-full bg-[#1a1a2e] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm font-mono focus:border-[#00d4ff] focus:outline-none" />
                </div>
              </div>
              <button
                onClick={async () => {
                  if (!obsSessionId.trim()) { setMessage('Session ID required'); return; }
                  if (!obsPlayerId.trim()) { setMessage('Player ID required'); return; }
                  let data = {};
                  try { data = JSON.parse(obsData || '{}'); } catch { setMessage('Invalid data JSON'); return; }
                  await handlePost(`${API_BASE}/learning-pipeline/record-observation`, { session_id: obsSessionId, player_id: obsPlayerId, obs_type: obsType, data });
                  setObsData('{}');
                }}
                disabled={loading}
                className="mt-3 px-4 py-2 bg-[#00d4ff] text-black rounded text-sm font-medium hover:bg-[#00b8e6] disabled:opacity-50">
                Record Observation
              </button>
            </div>

            <div className="bg-[#0f0f23] border border-[#2a2a4a] rounded-lg p-4">
              <h2 className="text-lg font-bold text-[#00d4ff] mb-3">End Session</h2>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-xs text-[#999] mb-1 block">Session ID</label>
                  <input type="text" value={endSessionId} onChange={e => setEndSessionId(e.target.value)}
                    placeholder="session_abc123" className="w-full bg-[#1a1a2e] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none" />
                </div>
                <div>
                  <label className="text-xs text-[#999] mb-1 block">Player ID</label>
                  <input type="text" value={endPlayerId} onChange={e => setEndPlayerId(e.target.value)}
                    placeholder="player_abc123" className="w-full bg-[#1a1a2e] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none" />
                </div>
                <div className="col-span-2">
                  <label className="text-xs text-[#999] mb-1 block">Outcome (JSON)</label>
                  <textarea value={endOutcome} onChange={e => setEndOutcome(e.target.value)}
                    rows={3} placeholder='{"result": "completed", "score": 850}' className="w-full bg-[#1a1a2e] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm font-mono focus:border-[#00d4ff] focus:outline-none" />
                </div>
              </div>
              <button
                onClick={async () => {
                  if (!endSessionId.trim()) { setMessage('Session ID required'); return; }
                  if (!endPlayerId.trim()) { setMessage('Player ID required'); return; }
                  let outcome = {};
                  try { outcome = JSON.parse(endOutcome || '{}'); } catch { setMessage('Invalid outcome JSON'); return; }
                  await handlePost(`${API_BASE}/learning-pipeline/end-session`, { session_id: endSessionId, player_id: endPlayerId, outcome });
                }}
                disabled={loading}
                className="mt-3 px-4 py-2 bg-[#ff6b6b] text-black rounded text-sm font-medium hover:bg-[#ee5555] disabled:opacity-50">
                End Session
              </button>
            </div>
          </div>
        )}

        {/* Insights Tab */}
        {activeTab === 'insights' && (
          <div className="space-y-6">
            <div className="bg-[#0f0f23] border border-[#2a2a4a] rounded-lg p-4">
              <h2 className="text-lg font-bold text-[#00d4ff] mb-3">Analyze Player Patterns</h2>
              <div className="flex gap-3 items-end">
                <div className="flex-1">
                  <label className="text-xs text-[#999] mb-1 block">Player ID</label>
                  <input type="text" value={analyzePlayerId} onChange={e => setAnalyzePlayerId(e.target.value)}
                    placeholder="player_abc123" className="w-full bg-[#1a1a2e] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none" />
                </div>
                <button
                  onClick={async () => {
                    if (!analyzePlayerId.trim()) { setMessage('Player ID required'); return; }
                    await handlePost(`${API_BASE}/learning-pipeline/analyze-patterns`, { player_id: analyzePlayerId });
                  }}
                  disabled={loading}
                  className="px-4 py-2 bg-[#00d4ff] text-black rounded text-sm font-medium hover:bg-[#00b8e6] disabled:opacity-50">
                  Analyze
                </button>
              </div>
            </div>

            {result && (result.insights || result.patterns) && (
              <div className="bg-[#0f0f23] border border-[#2a2a4a] rounded-lg p-4">
                <h2 className="text-lg font-bold text-[#00d4ff] mb-3">Insights</h2>
                <div className="space-y-2">
                  {(Array.isArray(result.insights) ? result.insights : Array.isArray(result.patterns) ? result.patterns : [result]).map((insight: any, i: number) => (
                    <div key={insight.id || i} className="bg-[#1a1a2e] border border-[#2a2a4a] rounded-lg p-3">
                      <div className="flex items-center justify-between mb-1">
                        <span className="text-white text-sm font-medium">{insight.name || insight.pattern || `Insight ${i + 1}`}</span>
                        <span className={`text-xs px-2 py-0.5 rounded font-mono ${confidenceColors[insight.confidence] || 'bg-[#1a1a1a] text-[#ccc]'}`}>
                          {insight.confidence || 'UNKNOWN'}
                        </span>
                      </div>
                      <div className="flex items-center gap-4 text-xs text-[#999]">
                        <span>Type: <span className="text-white">{insight.type || 'N/A'}</span></span>
                        <span>Frequency: <span className="text-white">{insight.frequency ?? 'N/A'}</span></span>
                      </div>
                      {insight.description && <p className="text-xs text-[#999] mt-1">{insight.description}</p>}
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

        {/* Profiles Tab */}
        {activeTab === 'profiles' && (
          <div className="space-y-6">
            <div className="bg-[#0f0f23] border border-[#2a2a4a] rounded-lg p-4">
              <h2 className="text-lg font-bold text-[#00d4ff] mb-3">Build Player Profile</h2>
              <div className="flex gap-3 items-end">
                <div className="flex-1">
                  <label className="text-xs text-[#999] mb-1 block">Player ID</label>
                  <input type="text" value={profilePlayerId} onChange={e => setProfilePlayerId(e.target.value)}
                    placeholder="player_abc123" className="w-full bg-[#1a1a2e] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none" />
                </div>
                <button
                  onClick={async () => {
                    if (!profilePlayerId.trim()) { setMessage('Player ID required'); return; }
                    await handlePost(`${API_BASE}/learning-pipeline/player-profile`, { player_id: profilePlayerId });
                  }}
                  disabled={loading}
                  className="px-4 py-2 bg-[#00d4ff] text-black rounded text-sm font-medium hover:bg-[#00b8e6] disabled:opacity-50">
                  Build Profile
                </button>
              </div>
            </div>

            {result && (result.profile || result.skill_level != null || result.engagement_score != null) && (
              <div className="bg-[#0f0f23] border border-[#2a2a4a] rounded-lg p-4">
                <h2 className="text-lg font-bold text-[#00d4ff] mb-3">Player Profile</h2>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-4">
                  <div className="bg-[#1a1a2e] p-3 rounded border border-[#2a2a4a]">
                    <span className="text-xs text-[#999]">Skill Level</span>
                    <p className="text-xl font-bold text-[#00ff88]">{result.skill_level ?? result.profile?.skill_level ?? 'N/A'}</p>
                  </div>
                  <div className="bg-[#1a1a2e] p-3 rounded border border-[#2a2a4a]">
                    <span className="text-xs text-[#999]">Engagement Score</span>
                    <p className="text-xl font-bold text-[#00d4ff]">{result.engagement_score ?? result.profile?.engagement_score ?? 'N/A'}</p>
                  </div>
                  <div className="bg-[#1a1a2e] p-3 rounded border border-[#2a2a4a]">
                    <span className="text-xs text-[#999]">Segments</span>
                    <p className="text-xl font-bold text-white">
                      {Array.isArray(result.segments ?? result.profile?.segments) ? (result.segments ?? result.profile?.segments).length : 0}
                    </p>
                  </div>
                  <div className="bg-[#1a1a2e] p-3 rounded border border-[#2a2a4a]">
                    <span className="text-xs text-[#999]">Preferred Actions</span>
                    <p className="text-xl font-bold text-white">
                      {Array.isArray(result.preferred_actions ?? result.profile?.preferred_actions) ? (result.preferred_actions ?? result.profile?.preferred_actions).length : 0}
                    </p>
                  </div>
                </div>
                {(result.segments ?? result.profile?.segments) && (
                  <div className="mb-3">
                    <h3 className="text-xs text-[#999] mb-2">Segments</h3>
                    <div className="flex flex-wrap gap-2">
                      {(Array.isArray(result.segments) ? result.segments : (result.profile?.segments || [])).map((s: string, i: number) => (
                        <span key={i} className="text-xs bg-[#1a1a2e] text-[#00d4ff] px-2 py-1 rounded border border-[#2a2a4a]">{s}</span>
                      ))}
                    </div>
                  </div>
                )}
                {(result.preferred_actions ?? result.profile?.preferred_actions) && (
                  <div>
                    <h3 className="text-xs text-[#999] mb-2">Preferred Actions</h3>
                    <div className="flex flex-wrap gap-2">
                      {(Array.isArray(result.preferred_actions) ? result.preferred_actions : (result.profile?.preferred_actions || [])).map((a: string, i: number) => (
                        <span key={i} className="text-xs bg-[#1a1a2e] text-[#00ff88] px-2 py-1 rounded border border-[#2a2a4a]">{a}</span>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>
        )}

      </div>
    </div>
  );
}