"use client";
import React, { useState, useEffect, useCallback } from 'react';

const API_BASE = 'http://localhost:8000/api/agent';

export default function AgentWorldModelPanel() {
  const [activeTab, setActiveTab] = useState('overview');
  const [stats, setStats] = useState<any>({});
  const [agentId, setAgentId] = useState('');
  const [actionName, setActionName] = useState('');
  const [result, setResult] = useState<any>(null);
  const [message, setMessage] = useState('');

  const fetchStats = useCallback(async () => {
    try { const r = await fetch(`${API_BASE}/world-model/stats`); if (r.ok) setStats(await r.json()); } catch (e) { console.error(e); }
  }, []);

  useEffect(() => { fetchStats(); const i = setInterval(fetchStats, 15000); return () => clearInterval(i); }, [fetchStats]);

  const handleSubmit = async (url: string, body: any) => {
    try {
      const r = await fetch(url, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });
      const data = await r.json();
      setMessage(r.ok ? 'Success' : data.error || 'Failed');
      return data;
    } catch (e: any) { setMessage(e.message); }
  };

  const tabs = ['overview', 'world', 'predict', 'simulate'];

  return (
    <div className="h-full flex flex-col bg-[#1a1a2e] text-white">
      <div className="flex gap-1 p-3 border-b border-[#2a2a4a]">
        {tabs.map(t => <button key={t} onClick={() => setActiveTab(t)} className={`px-4 py-2 rounded text-sm font-medium ${activeTab === t ? 'bg-[#00d4ff] text-black' : 'bg-[#0f0f23] text-gray-300 hover:bg-[#2a2a4a]'}`}>{t.charAt(0).toUpperCase()+t.slice(1)}</button>)}
      </div>
      {message && <div className="mx-4 mt-2 p-2 bg-[#0f0f23] border border-[#2a2a4a] rounded text-sm text-[#00d4ff]">{message}</div>}
      <div className="flex-1 overflow-auto p-4">
        {activeTab === 'overview' && (
          <div className="space-y-4">
            <h2 className="text-lg font-bold text-[#00d4ff]">World Model</h2>
            <div className="grid grid-cols-3 gap-4">
              <div className="bg-[#0f0f23] p-4 rounded border border-[#2a2a4a]"><h3 className="text-[#00d4ff] text-sm">Agents</h3><p className="text-2xl">{stats.total_agents||0}</p></div>
              <div className="bg-[#0f0f23] p-4 rounded border border-[#2a2a4a]"><h3 className="text-[#00d4ff] text-sm">Transitions</h3><p className="text-2xl">{stats.total_transitions||0}</p></div>
              <div className="bg-[#0f0f23] p-4 rounded border border-[#2a2a4a]"><h3 className="text-[#00d4ff] text-sm">Predictions</h3><p className="text-2xl">{stats.total_predictions||0}</p></div>
            </div>
          </div>
        )}
        {activeTab === 'world' && (
          <div className="space-y-4">
            <h2 className="text-lg font-bold text-[#00d4ff]">Initialize World</h2>
            <input className="w-full bg-[#0f0f23] border border-[#2a2a4a] rounded px-3 py-2 text-sm" placeholder="Agent ID" value={agentId} onChange={e => setAgentId(e.target.value)} />
            <button className="px-4 py-2 bg-[#00d4ff] text-black rounded text-sm" onClick={async () => { const r = await handleSubmit(`${API_BASE}/world-model/initialize-world`, {agent_id: agentId, initial_state: {health: 100, position: [0,0]}}); if (r) setResult(r); }}>Initialize</button>
            {result && <pre className="bg-[#0f0f23] p-4 rounded border border-[#2a2a4a] text-xs overflow-auto">{JSON.stringify(result, null, 2)}</pre>}
          </div>
        )}
        {activeTab === 'predict' && (
          <div className="space-y-4">
            <h2 className="text-lg font-bold text-[#00d4ff]">Predict Outcome</h2>
            <input className="w-full bg-[#0f0f23] border border-[#2a2a4a] rounded px-3 py-2 text-sm" placeholder="Agent ID" value={agentId} onChange={e => setAgentId(e.target.value)} />
            <input className="w-full bg-[#0f0f23] border border-[#2a2a4a] rounded px-3 py-2 text-sm" placeholder="Action Name" value={actionName} onChange={e => setActionName(e.target.value)} />
            <button className="px-4 py-2 bg-[#00d4ff] text-black rounded text-sm" onClick={async () => { const r = await handleSubmit(`${API_BASE}/world-model/predict`, {agent_id: agentId, action_name: actionName}); if (r) setResult(r); }}>Predict</button>
            {result && <pre className="bg-[#0f0f23] p-4 rounded border border-[#2a2a4a] text-xs overflow-auto">{JSON.stringify(result, null, 2)}</pre>}
          </div>
        )}
        {activeTab === 'simulate' && (
          <div className="space-y-4">
            <h2 className="text-lg font-bold text-[#00d4ff]">Simulate Sequence</h2>
            <input className="w-full bg-[#0f0f23] border border-[#2a2a4a] rounded px-3 py-2 text-sm" placeholder="Agent ID" value={agentId} onChange={e => setAgentId(e.target.value)} />
            <button className="px-4 py-2 bg-[#00d4ff] text-black rounded text-sm" onClick={async () => { const r = await handleSubmit(`${API_BASE}/world-model/simulate`, {agent_id: agentId, actions: [["move", {x: 10, y: 0}], ["attack", {target: "enemy1"}]]}); if (r) setResult(r); }}>Simulate</button>
            {result && <pre className="bg-[#0f0f23] p-4 rounded border border-[#2a2a4a] text-xs overflow-auto">{JSON.stringify(result, null, 2)}</pre>}
          </div>
        )}
      </div>
    </div>
  );
}