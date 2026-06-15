"use client";
import React, { useState, useEffect, useCallback } from 'react';

const API_BASE = 'http://localhost:8000/api/engine';

export default function EngineAIGameRuntimePanel() {
  const [activeTab, setActiveTab] = useState('overview');
  const [stats, setStats] = useState<any>({});
  const [message, setMessage] = useState('');
  const [loading, setLoading] = useState(false);

  // Agent form state
  const [regName, setRegName] = useState('');
  const [regType, setRegType] = useState('npc');
  const [regConfig, setRegConfig] = useState('');
  const [agents, setAgents] = useState<any[]>([]);

  // Action submission state
  const [actAgentId, setActAgentId] = useState('');
  const [actAction, setActAction] = useState('');
  const [actParams, setActParams] = useState('');

  // Hook state
  const [hookName, setHookName] = useState('');
  const [hookEvent, setHookEvent] = useState('on_tick');
  const [hookHandler, setHookHandler] = useState('');

  // Pending actions state
  const [pendingActions, setPendingActions] = useState<any[]>([]);
  const [execHookAgentId, setExecHookAgentId] = useState('');

  const AGENT_TYPES = ['npc', 'player', 'environmental', 'system', 'quest_giver', 'merchant', 'enemy', 'ally'];
  const HOOK_EVENTS = ['on_tick', 'on_spawn', 'on_death', 'on_damage', 'on_interact', 'on_move', 'on_idle', 'on_dialogue'];

  const fetchStats = useCallback(async () => {
    try { const r = await fetch(`${API_BASE}/ai-game-runtime/stats`); if (r.ok) setStats(await r.json()); } catch (e) { console.error(e); }
  }, []);

  const fetchAgents = useCallback(async () => {
    try { const r = await fetch(`${API_BASE}/ai-game-runtime/agents`); if (r.ok) { const d = await r.json(); setAgents(d.agents || d || []); } } catch (e) { console.error(e); }
  }, []);

  const fetchPendingActions = useCallback(async () => {
    try { const r = await fetch(`${API_BASE}/ai-game-runtime/pending-actions`); if (r.ok) { const d = await r.json(); setPendingActions(d.actions || d || []); } } catch (e) { console.error(e); }
  }, []);

  useEffect(() => { fetchStats(); fetchAgents(); fetchPendingActions(); const i = setInterval(fetchStats, 15000); return () => clearInterval(i); }, [fetchStats, fetchAgents, fetchPendingActions]);

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

  const tabs = ['overview', 'agents', 'hooks', 'actions'];

  return (
    <div className="h-full flex flex-col bg-[#1a1a2e] text-white">
      <div className="flex gap-1 p-3 border-b border-[#2a2a4a]">
        {tabs.map(t => <button key={t} onClick={() => setActiveTab(t)} className={`px-4 py-2 rounded text-sm font-medium ${activeTab === t ? 'bg-[#00d4ff] text-black' : 'bg-[#0f0f23] text-gray-300 hover:bg-[#2a2a4a]'}`}>{t.charAt(0).toUpperCase()+t.slice(1)}</button>)}
      </div>
      {message && <div className="mx-4 mt-2 p-2 bg-[#0f0f23] border border-[#2a2a4a] rounded text-sm text-[#00d4ff]">{message}</div>}
      <div className="flex-1 overflow-auto p-4">
        {activeTab === 'overview' && (
          <div className="space-y-4">
            <h2 className="text-lg font-bold text-[#00d4ff]">AI Game Runtime</h2>
            <div className="grid grid-cols-2 gap-4">
              <div className="bg-[#0f0f23] p-4 rounded border border-[#2a2a4a]"><h3 className="text-[#00d4ff] text-sm">Total Agents</h3><p className="text-2xl">{stats.total_agents ?? 0}</p></div>
              <div className="bg-[#0f0f23] p-4 rounded border border-[#2a2a4a]"><h3 className="text-[#00d4ff] text-sm">Total Hooks</h3><p className="text-2xl">{stats.total_hooks ?? 0}</p></div>
              <div className="bg-[#0f0f23] p-4 rounded border border-[#2a2a4a]"><h3 className="text-[#00d4ff] text-sm">Total Actions</h3><p className="text-2xl">{stats.total_actions ?? 0}</p></div>
              <div className="bg-[#0f0f23] p-4 rounded border border-[#2a2a4a]"><h3 className="text-[#00d4ff] text-sm">Pending Actions</h3><p className="text-2xl">{stats.pending_actions ?? 0}</p></div>
            </div>
          </div>
        )}

        {activeTab === 'agents' && (
          <div className="space-y-4">
            <h2 className="text-lg font-bold text-[#00d4ff]">Agents</h2>

            <div className="bg-[#0f0f23] p-4 rounded border border-[#2a2a4a] space-y-3">
              <h3 className="text-sm font-medium text-[#00d4ff]">Register Agent</h3>
              <div>
                <label className="text-xs text-gray-400 mb-1 block">Agent Name</label>
                <input type="text" value={regName} onChange={e => setRegName(e.target.value)} placeholder="guard_npc_01" className="w-full bg-[#1a1a2e] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none" />
              </div>
              <div>
                <label className="text-xs text-gray-400 mb-1 block">Agent Type</label>
                <select value={regType} onChange={e => setRegType(e.target.value)} className="w-full bg-[#1a1a2e] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none">
                  {AGENT_TYPES.map(t => <option key={t} value={t}>{t}</option>)}
                </select>
              </div>
              <div>
                <label className="text-xs text-gray-400 mb-1 block">Config (JSON)</label>
                <textarea value={regConfig} onChange={e => setRegConfig(e.target.value)} placeholder='{"health": 100, "speed": 5, "team": "guard"}' rows={3} className="w-full bg-[#1a1a2e] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none font-mono" />
              </div>
              <button
                onClick={async () => {
                  if (!regName.trim()) { setMessage('Agent name required'); return; }
                  let config = {};
                  try { if (regConfig.trim()) config = JSON.parse(regConfig); } catch { setMessage('Invalid config JSON'); return; }
                  await handleSubmit(`${API_BASE}/ai-game-runtime/register-agent`, { name: regName, agent_type: regType, config });
                  setRegName(''); setRegConfig('');
                  fetchAgents(); fetchStats();
                }}
                disabled={loading}
                className="px-4 py-2 bg-[#00d4ff] text-black rounded text-sm font-medium hover:bg-[#00b8e6] disabled:opacity-50"
              >
                Register Agent
              </button>
            </div>

            <div className="bg-[#0f0f23] p-4 rounded border border-[#2a2a4a] space-y-3">
              <h3 className="text-sm font-medium text-[#00d4ff]">Submit Action</h3>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-xs text-gray-400 mb-1 block">Agent ID</label>
                  <input type="text" value={actAgentId} onChange={e => setActAgentId(e.target.value)} placeholder="agent_abc123" className="w-full bg-[#1a1a2e] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none" />
                </div>
                <div>
                  <label className="text-xs text-gray-400 mb-1 block">Action</label>
                  <input type="text" value={actAction} onChange={e => setActAction(e.target.value)} placeholder="move_to" className="w-full bg-[#1a1a2e] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none" />
                </div>
              </div>
              <div>
                <label className="text-xs text-gray-400 mb-1 block">Parameters (JSON)</label>
                <textarea value={actParams} onChange={e => setActParams(e.target.value)} placeholder='{"x": 10, "y": 20}' rows={2} className="w-full bg-[#1a1a2e] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none font-mono" />
              </div>
              <button
                onClick={async () => {
                  if (!actAgentId.trim() || !actAction.trim()) { setMessage('Agent ID and action required'); return; }
                  let params = {};
                  try { if (actParams.trim()) params = JSON.parse(actParams); } catch { setMessage('Invalid parameters JSON'); return; }
                  await handleSubmit(`${API_BASE}/ai-game-runtime/submit-action`, { agent_id: actAgentId, action: actAction, parameters: params });
                  setActAgentId(''); setActAction(''); setActParams('');
                  fetchPendingActions(); fetchStats();
                }}
                disabled={loading}
                className="px-4 py-2 bg-[#00d4ff] text-black rounded text-sm font-medium hover:bg-[#00b8e6] disabled:opacity-50"
              >
                Submit Action
              </button>
            </div>

            <div>
              <div className="flex items-center justify-between mb-2">
                <h3 className="text-sm font-medium text-[#00d4ff]">Registered Agents ({agents.length})</h3>
                <button onClick={fetchAgents} className="px-3 py-1 bg-[#0f0f23] border border-[#2a2a4a] rounded text-xs text-gray-300 hover:bg-[#2a2a4a]">Refresh</button>
              </div>
              {agents.length > 0 ? (
                <div className="space-y-2">
                  {agents.map((a: any, i: number) => (
                    <div key={a.id || i} className="bg-[#0f0f23] p-3 rounded border border-[#2a2a4a] flex items-center justify-between">
                      <div>
                        <span className="text-white text-sm font-medium">{a.name || a.id}</span>
                        <span className="text-xs bg-[#1a1a2e] text-gray-300 px-2 py-0.5 rounded ml-2">{a.agent_type || a.type}</span>
                      </div>
                      <span className={`text-xs px-2 py-0.5 rounded ${a.status === 'active' ? 'bg-green-900 text-green-300' : 'bg-gray-700 text-gray-300'}`}>{a.status || 'idle'}</span>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="text-gray-400 text-xs">No agents registered</div>
              )}
            </div>
          </div>
        )}

        {activeTab === 'hooks' && (
          <div className="space-y-4">
            <h2 className="text-lg font-bold text-[#00d4ff]">Add Hook</h2>
            <div className="bg-[#0f0f23] p-4 rounded border border-[#2a2a4a] space-y-3">
              <div>
                <label className="text-xs text-gray-400 mb-1 block">Hook Name</label>
                <input type="text" value={hookName} onChange={e => setHookName(e.target.value)} placeholder="patrol_behavior" className="w-full bg-[#1a1a2e] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none" />
              </div>
              <div>
                <label className="text-xs text-gray-400 mb-1 block">Event</label>
                <select value={hookEvent} onChange={e => setHookEvent(e.target.value)} className="w-full bg-[#1a1a2e] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none">
                  {HOOK_EVENTS.map(e => <option key={e} value={e}>{e}</option>)}
                </select>
              </div>
              <div>
                <label className="text-xs text-gray-400 mb-1 block">Handler (JSON with logic description)</label>
                <textarea value={hookHandler} onChange={e => setHookHandler(e.target.value)} placeholder='{"logic": "patrol between waypoints", "priority": 5}' rows={3} className="w-full bg-[#1a1a2e] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none font-mono" />
              </div>
              <button
                onClick={async () => {
                  if (!hookName.trim()) { setMessage('Hook name required'); return; }
                  let handler = {};
                  try { if (hookHandler.trim()) handler = JSON.parse(hookHandler); } catch { setMessage('Invalid handler JSON'); return; }
                  await handleSubmit(`${API_BASE}/ai-game-runtime/add-hook`, { name: hookName, event: hookEvent, handler });
                  setHookName(''); setHookHandler('');
                  fetchStats();
                }}
                disabled={loading}
                className="px-4 py-2 bg-[#00d4ff] text-black rounded text-sm font-medium hover:bg-[#00b8e6] disabled:opacity-50"
              >
                Add Hook
              </button>
            </div>
          </div>
        )}

        {activeTab === 'actions' && (
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <h2 className="text-lg font-bold text-[#00d4ff]">Pending Actions</h2>
              <button onClick={fetchPendingActions} className="px-3 py-1 bg-[#0f0f23] border border-[#2a2a4a] rounded text-xs text-gray-300 hover:bg-[#2a2a4a]">Refresh</button>
            </div>

            {pendingActions.length > 0 ? (
              <div className="space-y-2">
                {pendingActions.map((a: any, i: number) => (
                  <div key={a.id || i} className="bg-[#0f0f23] p-3 rounded border border-[#2a2a4a]">
                    <div className="flex items-center justify-between mb-1">
                      <span className="text-white text-sm font-medium">{a.action || a.type || `Action #${i + 1}`}</span>
                      <span className="text-xs bg-yellow-900 text-yellow-300 px-2 py-0.5 rounded">pending</span>
                    </div>
                    <div className="text-xs text-gray-400">
                      <span>Agent: <span className="text-white">{a.agent_id || 'N/A'}</span></span>
                      {a.parameters && <span className="ml-4">Params: <span className="text-white font-mono">{JSON.stringify(a.parameters)}</span></span>}
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="text-gray-400 text-sm">No pending actions</div>
            )}

            <div className="bg-[#0f0f23] p-4 rounded border border-[#2a2a4a] space-y-3 mt-4">
              <h3 className="text-sm font-medium text-[#00d4ff]">Execute Hooks</h3>
              <div>
                <label className="text-xs text-gray-400 mb-1 block">Agent ID</label>
                <input type="text" value={execHookAgentId} onChange={e => setExecHookAgentId(e.target.value)} placeholder="agent_abc123" className="w-full bg-[#1a1a2e] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none" />
              </div>
              <button
                onClick={async () => {
                  if (!execHookAgentId.trim()) { setMessage('Agent ID required'); return; }
                  const result = await handleSubmit(`${API_BASE}/ai-game-runtime/execute-hooks`, { agent_id: execHookAgentId });
                  if (result) setMessage(`Executed hooks: ${JSON.stringify(result)}`);
                  fetchPendingActions(); fetchStats();
                }}
                disabled={loading}
                className="px-4 py-2 bg-[#00d4ff] text-black rounded text-sm font-medium hover:bg-[#00b8e6] disabled:opacity-50"
              >
                Execute Hooks
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}