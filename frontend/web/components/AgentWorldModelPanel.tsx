"use client";
import React, { useState, useEffect, useCallback } from 'react';
import { API_BASE as API_ROOT } from '../utils/api';

const API_BASE = API_ROOT + '/agent';

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
    <div className="h-full flex flex-col bg-[#1a1a1a] text-white">
      <div className="flex gap-1 p-3 border-b border-[#2a2a2a]">
        {tabs.map(t => <button key={t} onClick={() => setActiveTab(t)} className={`px-4 py-2 rounded text-sm font-medium ${activeTab === t ? 'bg-[#f97316] text-black' : 'bg-[#0d0d0d] text-[#ccc] hover:bg-[#2a2a2a]'}`}>{t.charAt(0).toUpperCase()+t.slice(1)}</button>)}
      </div>
      {message && <div className="mx-4 mt-2 p-2 bg-[#0d0d0d] border border-[#2a2a2a] rounded text-sm text-[#f97316]">{message}</div>}
      <div className="flex-1 overflow-auto p-4">
        {activeTab === 'overview' && (
          <div className="space-y-4">
            <h2 className="text-lg font-bold text-[#f97316]">World Model</h2>
            <div className="grid grid-cols-3 gap-4">
              <div className="bg-[#0d0d0d] p-4 rounded border border-[#2a2a2a]"><h3 className="text-[#f97316] text-sm">Agents</h3><p className="text-2xl">{stats.total_agents||0}</p></div>
              <div className="bg-[#0d0d0d] p-4 rounded border border-[#2a2a2a]"><h3 className="text-[#f97316] text-sm">Transitions</h3><p className="text-2xl">{stats.total_transitions||0}</p></div>
              <div className="bg-[#0d0d0d] p-4 rounded border border-[#2a2a2a]"><h3 className="text-[#f97316] text-sm">Predictions</h3><p className="text-2xl">{stats.total_predictions||0}</p></div>
            </div>
          </div>
        )}
        {activeTab === 'world' && (
          <div className="space-y-4">
            <h2 className="text-lg font-bold text-[#f97316]">Initialize World</h2>
            <input className="w-full bg-[#0d0d0d] border border-[#2a2a2a] rounded px-3 py-2 text-sm" placeholder="Agent ID" value={agentId} onChange={e => setAgentId(e.target.value)} />
            <button className="px-4 py-2 bg-[#f97316] text-black rounded text-sm" onClick={async () => { const r = await handleSubmit(`${API_BASE}/world-model/initialize-world`, {agent_id: agentId, initial_state: {health: 100, position: [0,0]}}); if (r) setResult(r); }}>Initialize</button>
            {result && <pre className="bg-[#0d0d0d] p-4 rounded border border-[#2a2a2a] text-xs overflow-auto">{JSON.stringify(result, null, 2)}</pre>}
          </div>
        )}
        {activeTab === 'predict' && (
          <div className="space-y-4">
            <h2 className="text-lg font-bold text-[#f97316]">Predict Outcome</h2>
            <input className="w-full bg-[#0d0d0d] border border-[#2a2a2a] rounded px-3 py-2 text-sm" placeholder="Agent ID" value={agentId} onChange={e => setAgentId(e.target.value)} />
            <input className="w-full bg-[#0d0d0d] border border-[#2a2a2a] rounded px-3 py-2 text-sm" placeholder="Action Name" value={actionName} onChange={e => setActionName(e.target.value)} />
            <button className="px-4 py-2 bg-[#f97316] text-black rounded text-sm" onClick={async () => { const r = await handleSubmit(`${API_BASE}/world-model/predict`, {agent_id: agentId, action_name: actionName}); if (r) setResult(r); }}>Predict</button>
            {result && <pre className="bg-[#0d0d0d] p-4 rounded border border-[#2a2a2a] text-xs overflow-auto">{JSON.stringify(result, null, 2)}</pre>}
          </div>
        )}
        {activeTab === 'simulate' && (
          <div className="space-y-4">
            <h2 className="text-lg font-bold text-[#f97316]">Simulate Sequence</h2>
            <input className="w-full bg-[#0d0d0d] border border-[#2a2a2a] rounded px-3 py-2 text-sm" placeholder="Agent ID" value={agentId} onChange={e => setAgentId(e.target.value)} />
            <button className="px-4 py-2 bg-[#f97316] text-black rounded text-sm" onClick={async () => { const r = await handleSubmit(`${API_BASE}/world-model/simulate`, {agent_id: agentId, actions: [["move", {x: 10, y: 0}], ["attack", {target: "enemy1"}]]}); if (r) setResult(r); }}>Simulate</button>
            {result && <pre className="bg-[#0d0d0d] p-4 rounded border border-[#2a2a2a] text-xs overflow-auto">{JSON.stringify(result, null, 2)}</pre>}
          </div>
        )}
      </div>
    </div>
  );
}