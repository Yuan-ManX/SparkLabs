"use client";
import React, { useState, useEffect, useCallback } from 'react';
import { API_BASE as API_ROOT } from '../utils/api';

const API_BASE = API_ROOT + '/engine';

export default function EngineNetworkLayerPanel() {
  const [activeTab, setActiveTab] = useState('overview');
  const [stats, setStats] = useState<any>({});
  const [message, setMessage] = useState('');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<any>(null);

  // Create session
  const [csName, setCsName] = useState('');
  const [csTopology, setCsTopology] = useState('client_server');
  const [csMaxPlayers, setCsMaxPlayers] = useState('16');
  const [csSyncStrategy, setCsSyncStrategy] = useState('delta');
  const [csTickRate, setCsTickRate] = useState('30');

  // Connect player
  const [connSessionId, setConnSessionId] = useState('');
  const [connPlayerId, setConnPlayerId] = useState('');
  const [connIpAddress, setConnIpAddress] = useState('');

  // Disconnect
  const [discSessionId, setDiscSessionId] = useState('');
  const [discPlayerId, setDiscPlayerId] = useState('');

  // Matchmaking
  const [mmPlayerId, setMmPlayerId] = useState('');
  const [mmPreferences, setMmPreferences] = useState('{}');
  const [mmSkillRange, setMmSkillRange] = useState('200');
  const [mmRegion, setMmRegion] = useState('us-east');

  // Sync
  const [syncSessionId, setSyncSessionId] = useState('');

  const fetchStats = useCallback(async () => {
    try { const r = await fetch(`${API_BASE}/network-layer/stats`); if (r.ok) setStats(await r.json()); } catch (e) { console.error(e); }
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

  const topologyOptions = ['client_server', 'peer_to_peer', 'authoritative_server', 'hybrid', 'dedicated_server'];
  const syncStrategyOptions = ['full_state', 'delta', 'interpolation', 'prediction', 'rollback', 'snapshot'];
  const regionOptions = ['us-east', 'us-west', 'eu-west', 'eu-central', 'ap-southeast', 'ap-northeast', 'sa-east', 'global'];

  const tabs = ['overview', 'sessions', 'matchmaking', 'sync'];

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
            <h2 className="text-lg font-bold text-[#00d4ff]">Network Layer</h2>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <div className="bg-[#0f0f23] p-4 rounded border border-[#2a2a4a]">
                <h3 className="text-[#00d4ff] text-xs">Total Sessions</h3>
                <p className="text-2xl font-bold mt-1">{stats.total_sessions ?? 0}</p>
              </div>
              <div className="bg-[#0f0f23] p-4 rounded border border-[#2a2a4a]">
                <h3 className="text-[#00d4ff] text-xs">Active Connections</h3>
                <p className="text-2xl font-bold mt-1 text-[#00ff88]">{stats.active_connections ?? 0}</p>
              </div>
              <div className="bg-[#0f0f23] p-4 rounded border border-[#2a2a4a]">
                <h3 className="text-[#00d4ff] text-xs">Total Packets</h3>
                <p className="text-2xl font-bold mt-1">{stats.total_packets ?? 0}</p>
              </div>
              <div className="bg-[#0f0f23] p-4 rounded border border-[#2a2a4a]">
                <h3 className="text-[#00d4ff] text-xs">Matchmaking Queries</h3>
                <p className="text-2xl font-bold mt-1">{stats.matchmaking_queries ?? 0}</p>
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
              <h2 className="text-lg font-bold text-[#00d4ff] mb-3">Create Network Session</h2>
              <div className="grid grid-cols-2 gap-3">
                <div className="col-span-2">
                  <label className="text-xs text-[#999] mb-1 block">Session Name</label>
                  <input type="text" value={csName} onChange={e => setCsName(e.target.value)}
                    placeholder="deathmatch_lobby_01" className="w-full bg-[#1a1a2e] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none" />
                </div>
                <div>
                  <label className="text-xs text-[#999] mb-1 block">Topology</label>
                  <select value={csTopology} onChange={e => setCsTopology(e.target.value)}
                    className="w-full bg-[#1a1a2e] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none">
                    {topologyOptions.map(t => (
                      <option key={t} value={t}>{t.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())}</option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="text-xs text-[#999] mb-1 block">Sync Strategy</label>
                  <select value={csSyncStrategy} onChange={e => setCsSyncStrategy(e.target.value)}
                    className="w-full bg-[#1a1a2e] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none">
                    {syncStrategyOptions.map(s => (
                      <option key={s} value={s}>{s.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())}</option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="text-xs text-[#999] mb-1 block">Max Players</label>
                  <input type="number" value={csMaxPlayers} onChange={e => setCsMaxPlayers(e.target.value)}
                    min="1" placeholder="16" className="w-full bg-[#1a1a2e] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none" />
                </div>
                <div>
                  <label className="text-xs text-[#999] mb-1 block">Tick Rate</label>
                  <input type="number" value={csTickRate} onChange={e => setCsTickRate(e.target.value)}
                    min="1" placeholder="30" className="w-full bg-[#1a1a2e] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none" />
                </div>
              </div>
              <button
                onClick={async () => {
                  if (!csName.trim()) { setMessage('Session name required'); return; }
                  await handlePost(`${API_BASE}/network-layer/create-session`, {
                    name: csName, topology: csTopology, max_players: parseInt(csMaxPlayers) || 16,
                    sync_strategy: csSyncStrategy, tick_rate: parseInt(csTickRate) || 30,
                  });
                  setCsName('');
                }}
                disabled={loading}
                className="mt-3 px-4 py-2 bg-[#00d4ff] text-black rounded text-sm font-medium hover:bg-[#00b8e6] disabled:opacity-50">
                Create Session
              </button>
            </div>

            <div className="bg-[#0f0f23] border border-[#2a2a4a] rounded-lg p-4">
              <h2 className="text-lg font-bold text-[#00d4ff] mb-3">Connect Player</h2>
              <div className="grid grid-cols-3 gap-3">
                <div>
                  <label className="text-xs text-[#999] mb-1 block">Session ID</label>
                  <input type="text" value={connSessionId} onChange={e => setConnSessionId(e.target.value)}
                    placeholder="session_abc123" className="w-full bg-[#1a1a2e] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none" />
                </div>
                <div>
                  <label className="text-xs text-[#999] mb-1 block">Player ID</label>
                  <input type="text" value={connPlayerId} onChange={e => setConnPlayerId(e.target.value)}
                    placeholder="player_abc123" className="w-full bg-[#1a1a2e] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none" />
                </div>
                <div>
                  <label className="text-xs text-[#999] mb-1 block">IP Address</label>
                  <input type="text" value={connIpAddress} onChange={e => setConnIpAddress(e.target.value)}
                    placeholder="192.168.1.100" className="w-full bg-[#1a1a2e] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none" />
                </div>
              </div>
              <button
                onClick={async () => {
                  if (!connSessionId.trim()) { setMessage('Session ID required'); return; }
                  if (!connPlayerId.trim()) { setMessage('Player ID required'); return; }
                  await handlePost(`${API_BASE}/network-layer/connect`, {
                    session_id: connSessionId, player_id: connPlayerId, ip_address: connIpAddress,
                  });
                }}
                disabled={loading}
                className="mt-3 px-4 py-2 bg-[#00ff88] text-black rounded text-sm font-medium hover:bg-[#00cc6a] disabled:opacity-50">
                Connect
              </button>
            </div>

            <div className="bg-[#0f0f23] border border-[#2a2a4a] rounded-lg p-4">
              <h2 className="text-lg font-bold text-[#00d4ff] mb-3">Disconnect Player</h2>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-xs text-[#999] mb-1 block">Session ID</label>
                  <input type="text" value={discSessionId} onChange={e => setDiscSessionId(e.target.value)}
                    placeholder="session_abc123" className="w-full bg-[#1a1a2e] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none" />
                </div>
                <div>
                  <label className="text-xs text-[#999] mb-1 block">Player ID</label>
                  <input type="text" value={discPlayerId} onChange={e => setDiscPlayerId(e.target.value)}
                    placeholder="player_abc123" className="w-full bg-[#1a1a2e] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none" />
                </div>
              </div>
              <button
                onClick={async () => {
                  if (!discSessionId.trim()) { setMessage('Session ID required'); return; }
                  if (!discPlayerId.trim()) { setMessage('Player ID required'); return; }
                  await handlePost(`${API_BASE}/network-layer/disconnect`, { session_id: discSessionId, player_id: discPlayerId });
                }}
                disabled={loading}
                className="mt-3 px-4 py-2 bg-[#ff6b6b] text-black rounded text-sm font-medium hover:bg-[#ee5555] disabled:opacity-50">
                Disconnect
              </button>
            </div>
          </div>
        )}

        {/* Matchmaking Tab */}
        {activeTab === 'matchmaking' && (
          <div className="space-y-6">
            <div className="bg-[#0f0f23] border border-[#2a2a4a] rounded-lg p-4">
              <h2 className="text-lg font-bold text-[#00d4ff] mb-3">Find Match</h2>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-xs text-[#999] mb-1 block">Player ID</label>
                  <input type="text" value={mmPlayerId} onChange={e => setMmPlayerId(e.target.value)}
                    placeholder="player_abc123" className="w-full bg-[#1a1a2e] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none" />
                </div>
                <div>
                  <label className="text-xs text-[#999] mb-1 block">Region</label>
                  <select value={mmRegion} onChange={e => setMmRegion(e.target.value)}
                    className="w-full bg-[#1a1a2e] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none">
                    {regionOptions.map(r => (
                      <option key={r} value={r}>{r.toUpperCase()}</option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="text-xs text-[#999] mb-1 block">Skill Range</label>
                  <input type="number" value={mmSkillRange} onChange={e => setMmSkillRange(e.target.value)}
                    min="0" placeholder="200" className="w-full bg-[#1a1a2e] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none" />
                </div>
                <div>
                  <label className="text-xs text-[#999] mb-1 block">Preferences (JSON)</label>
                  <textarea value={mmPreferences} onChange={e => setMmPreferences(e.target.value)}
                    rows={3} placeholder='{"mode": "ranked", "map": "dust2"}' className="w-full bg-[#1a1a2e] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm font-mono focus:border-[#00d4ff] focus:outline-none" />
                </div>
              </div>
              <button
                onClick={async () => {
                  if (!mmPlayerId.trim()) { setMessage('Player ID required'); return; }
                  let prefs = {};
                  try { prefs = JSON.parse(mmPreferences || '{}'); } catch { setMessage('Invalid preferences JSON'); return; }
                  await handlePost(`${API_BASE}/network-layer/find-match`, {
                    player_id: mmPlayerId, preferences: prefs,
                    skill_range: parseInt(mmSkillRange) || 200, region: mmRegion,
                  });
                }}
                disabled={loading}
                className="mt-3 px-4 py-2 bg-[#00d4ff] text-black rounded text-sm font-medium hover:bg-[#00b8e6] disabled:opacity-50">
                Find Match
              </button>
            </div>

            {result && (result.matched_players || result.match_id) && (
              <div className="bg-[#0f0f23] border border-[#2a2a4a] rounded-lg p-4">
                <h2 className="text-lg font-bold text-[#00d4ff] mb-3">Match Results</h2>
                {result.match_id && (
                  <div className="mb-3 text-sm">
                    <span className="text-[#999]">Match ID: </span>
                    <span className="text-[#00d4ff] font-mono">{result.match_id}</span>
                  </div>
                )}
                {result.matched_players && (
                  <div className="space-y-2">
                    {(Array.isArray(result.matched_players) ? result.matched_players : []).map((p: any, i: number) => (
                      <div key={p.id || i} className="bg-[#1a1a2e] border border-[#2a2a4a] rounded-lg p-3">
                        <div className="flex items-center justify-between mb-1">
                          <span className="text-white text-sm font-medium">{p.name || p.id || `Player ${i + 1}`}</span>
                          <span className="text-xs text-[#00ff88] font-mono">{p.skill_score != null ? p.skill_score : 'N/A'}</span>
                        </div>
                        <div className="flex items-center gap-4 text-xs text-[#999]">
                          {p.latency != null && <span>Latency: <span className="text-white">{p.latency}ms</span></span>}
                          {p.region && <span>Region: <span className="text-white">{p.region}</span></span>}
                        </div>
                      </div>
                    ))}
                  </div>
                )}
                {result.latency_estimates && (
                  <div className="mt-3">
                    <h3 className="text-xs text-[#999] mb-2">Latency Estimates</h3>
                    <div className="grid grid-cols-3 gap-2">
                      {Object.entries(result.latency_estimates).map(([key, value]) => (
                        <div key={key} className="bg-[#1a1a2e] p-2 rounded border border-[#2a2a4a] text-xs">
                          <span className="text-[#999] capitalize">{key}: </span>
                          <span className="text-white">{String(value)}ms</span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>
        )}

        {/* Sync Tab */}
        {activeTab === 'sync' && (
          <div className="space-y-6">
            <div className="bg-[#0f0f23] border border-[#2a2a4a] rounded-lg p-4">
              <h2 className="text-lg font-bold text-[#00d4ff] mb-3">Sync Game State</h2>
              <div className="flex gap-3 items-end">
                <div className="flex-1">
                  <label className="text-xs text-[#999] mb-1 block">Session ID</label>
                  <input type="text" value={syncSessionId} onChange={e => setSyncSessionId(e.target.value)}
                    placeholder="session_abc123" className="w-full bg-[#1a1a2e] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none" />
                </div>
                <button
                  onClick={async () => {
                    if (!syncSessionId.trim()) { setMessage('Session ID required'); return; }
                    await handlePost(`${API_BASE}/network-layer/sync`, { session_id: syncSessionId });
                  }}
                  disabled={loading}
                  className="px-4 py-2 bg-[#00d4ff] text-black rounded text-sm font-medium hover:bg-[#00b8e6] disabled:opacity-50">
                  Sync
                </button>
              </div>
            </div>

            {result && (
              <div className="bg-[#0f0f23] border border-[#2a2a4a] rounded-lg p-4">
                <h2 className="text-lg font-bold text-[#00d4ff] mb-3">Sync Results</h2>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-4">
                  <div className="bg-[#1a1a2e] p-3 rounded border border-[#2a2a4a]">
                    <span className="text-xs text-[#999]">Full State Size</span>
                    <p className="text-xl font-bold text-white">
                      {result.full_state_size != null
                        ? (result.full_state_size > 1024 ? (result.full_state_size / 1024).toFixed(1) + ' KB' : result.full_state_size + ' B')
                        : 'N/A'}
                    </p>
                  </div>
                  <div className="bg-[#1a1a2e] p-3 rounded border border-[#2a2a4a]">
                    <span className="text-xs text-[#999]">Delta Size</span>
                    <p className="text-xl font-bold text-[#00ff88]">
                      {result.delta_size != null
                        ? (result.delta_size > 1024 ? (result.delta_size / 1024).toFixed(1) + ' KB' : result.delta_size + ' B')
                        : 'N/A'}
                    </p>
                  </div>
                  <div className="bg-[#1a1a2e] p-3 rounded border border-[#2a2a4a]">
                    <span className="text-xs text-[#999]">Compression Ratio</span>
                    <p className="text-xl font-bold text-[#00d4ff]">
                      {result.compression_ratio != null ? (result.compression_ratio * 100).toFixed(1) + '%' : 'N/A'}
                    </p>
                  </div>
                  <div className="bg-[#1a1a2e] p-3 rounded border border-[#2a2a4a]">
                    <span className="text-xs text-[#999]">Entity Count</span>
                    <p className="text-xl font-bold text-white">{result.entity_count ?? 'N/A'}</p>
                  </div>
                </div>
                {result.entities && (
                  <div>
                    <h3 className="text-xs text-[#999] mb-2">Synced Entities</h3>
                    <div className="flex flex-wrap gap-2">
                      {(Array.isArray(result.entities) ? result.entities : []).map((e: any, i: number) => (
                        <span key={i} className="text-xs bg-[#1a1a2e] text-[#00d4ff] px-2 py-1 rounded border border-[#2a2a4a]">
                          {typeof e === 'string' ? e : e.id || e.name || `Entity ${i + 1}`}
                        </span>
                      ))}
                    </div>
                  </div>
                )}
                {!result.full_state_size && !result.delta_size && !result.entity_count && (
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