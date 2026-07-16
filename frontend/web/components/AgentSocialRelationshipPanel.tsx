"use client";
import React, { useState, useEffect, useCallback } from 'react';
import { API_BASE as API_ROOT } from '../utils/api';

const API_BASE = API_ROOT + '/agent';

export default function AgentSocialRelationshipPanel() {
  const [activeTab, setActiveTab] = useState('overview');
  const [stats, setStats] = useState<any>({});
  const [agentId, setAgentId] = useState('');
  const [targetId, setTargetId] = useState('');
  const [result, setResult] = useState<any>(null);
  const [message, setMessage] = useState('');

  const fetchStats = useCallback(async () => {
    try { const r = await fetch(`${API_BASE}/social-relationship/stats`); if (r.ok) setStats(await r.json()); } catch (e) { console.error(e); }
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

  const tabs = ['overview', 'register', 'relationship', 'interact', 'network'];

  return (
    <div className="h-full flex flex-col bg-[#1a1a2e] text-white">
      <div className="flex gap-1 p-3 border-b border-[#2a2a4a]">
        {tabs.map(t => <button key={t} onClick={() => setActiveTab(t)} className={`px-4 py-2 rounded text-sm font-medium ${activeTab === t ? 'bg-[#00d4ff] text-black' : 'bg-[#0d0d0d] text-[#ccc] hover:bg-[#2a2a4a]'}`}>{t.charAt(0).toUpperCase()+t.slice(1)}</button>)}
      </div>
      {message && <div className="mx-4 mt-2 p-2 bg-[#0d0d0d] border border-[#2a2a4a] rounded text-sm text-[#00d4ff]">{message}</div>}
      <div className="flex-1 overflow-auto p-4">
        {activeTab === 'overview' && (
          <div className="space-y-4">
            <h2 className="text-lg font-bold text-[#00d4ff]">Social Relationship System</h2>
            <div className="grid grid-cols-3 gap-4">
              <div className="bg-[#0d0d0d] p-4 rounded border border-[#2a2a4a]"><h3 className="text-[#00d4ff] text-sm">Agents</h3><p className="text-2xl">{stats.total_agents||0}</p></div>
              <div className="bg-[#0d0d0d] p-4 rounded border border-[#2a2a4a]"><h3 className="text-[#00d4ff] text-sm">Relationships</h3><p className="text-2xl">{stats.total_relationships||0}</p></div>
              <div className="bg-[#0d0d0d] p-4 rounded border border-[#2a2a4a]"><h3 className="text-[#00d4ff] text-sm">Groups</h3><p className="text-2xl">{stats.total_groups||0}</p></div>
              <div className="bg-[#0d0d0d] p-4 rounded border border-[#2a2a4a]"><h3 className="text-[#00d4ff] text-sm">Interactions</h3><p className="text-2xl">{stats.total_interactions||0}</p></div>
              <div className="bg-[#0d0d0d] p-4 rounded border border-[#2a2a4a]"><h3 className="text-[#00d4ff] text-sm">Network Density</h3><p className="text-2xl">{(stats.avg_network_density||0).toFixed(3)}</p></div>
            </div>
          </div>
        )}
        {activeTab === 'register' && (
          <div className="space-y-4">
            <h2 className="text-lg font-bold text-[#00d4ff]">Register Agent</h2>
            <input className="w-full bg-[#0d0d0d] border border-[#2a2a4a] rounded px-3 py-2 text-sm" placeholder="Agent ID" value={agentId} onChange={e => setAgentId(e.target.value)} />
            <button className="px-4 py-2 bg-[#00d4ff] text-black rounded text-sm" onClick={async () => await handleSubmit(`${API_BASE}/social-relationship/register-agent`, {agent_id: agentId})}>Register</button>
          </div>
        )}
        {activeTab === 'relationship' && (
          <div className="space-y-4">
            <h2 className="text-lg font-bold text-[#00d4ff]">Create Relationship</h2>
            <input className="w-full bg-[#0d0d0d] border border-[#2a2a4a] rounded px-3 py-2 text-sm" placeholder="Source Agent ID" value={agentId} onChange={e => setAgentId(e.target.value)} />
            <input className="w-full bg-[#0d0d0d] border border-[#2a2a4a] rounded px-3 py-2 text-sm" placeholder="Target Agent ID" value={targetId} onChange={e => setTargetId(e.target.value)} />
            <button className="px-4 py-2 bg-[#00d4ff] text-black rounded text-sm" onClick={async () => { const r = await handleSubmit(`${API_BASE}/social-relationship/create-relationship`, {source_id: agentId, target_id: targetId}); if (r) setResult(r); }}>Create</button>
            {result && <pre className="bg-[#0d0d0d] p-4 rounded border border-[#2a2a4a] text-xs overflow-auto">{JSON.stringify(result, null, 2)}</pre>}
          </div>
        )}
        {activeTab === 'interact' && (
          <div className="space-y-4">
            <h2 className="text-lg font-bold text-[#00d4ff]">Process Interaction</h2>
            <input className="w-full bg-[#0d0d0d] border border-[#2a2a4a] rounded px-3 py-2 text-sm" placeholder="Source Agent ID" value={agentId} onChange={e => setAgentId(e.target.value)} />
            <input className="w-full bg-[#0d0d0d] border border-[#2a2a4a] rounded px-3 py-2 text-sm" placeholder="Target Agent ID" value={targetId} onChange={e => setTargetId(e.target.value)} />
            <select className="w-full bg-[#0d0d0d] border border-[#2a2a4a] rounded px-3 py-2 text-sm">
              <option>help</option><option>gift</option><option>compliment</option><option>insult</option><option>cooperate</option>
            </select>
            <button className="px-4 py-2 bg-[#00d4ff] text-black rounded text-sm" onClick={async () => { const r = await handleSubmit(`${API_BASE}/social-relationship/process-interaction`, {source_id: agentId, target_id: targetId, action: 'help'}); if (r) setResult(r); }}>Interact</button>
            {result && <pre className="bg-[#0d0d0d] p-4 rounded border border-[#2a2a4a] text-xs overflow-auto">{JSON.stringify(result, null, 2)}</pre>}
          </div>
        )}
        {activeTab === 'network' && (
          <div className="space-y-4">
            <h2 className="text-lg font-bold text-[#00d4ff]">Social Network</h2>
            <input className="w-full bg-[#0d0d0d] border border-[#2a2a4a] rounded px-3 py-2 text-sm" placeholder="Agent ID" value={agentId} onChange={e => setAgentId(e.target.value)} />
            <button className="px-4 py-2 bg-[#00d4ff] text-black rounded text-sm" onClick={async () => { const r = await fetch(`${API_BASE}/social-relationship/relationships?agent_id=${agentId}`); if (r.ok) setResult(await r.json()); }}>Fetch</button>
            {result && <pre className="bg-[#0d0d0d] p-4 rounded border border-[#2a2a4a] text-xs overflow-auto">{JSON.stringify(result, null, 2)}</pre>}
          </div>
        )}
      </div>
    </div>
  );
}