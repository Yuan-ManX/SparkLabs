"use client";
import React, { useState, useEffect, useCallback } from 'react';
import { API_BASE as API_ROOT } from '../utils/api';

const API_BASE = API_ROOT + '/agent';

export default function AgentBehaviorTreePanel() {
  const [activeTab, setActiveTab] = useState('overview');
  const [stats, setStats] = useState<any>({});
  const [treeName, setTreeName] = useState('');
  const [agentId, setAgentId] = useState('');
  const [treeId, setTreeId] = useState('');
  const [treeData, setTreeData] = useState<any>(null);
  const [message, setMessage] = useState('');

  const fetchStats = useCallback(async () => {
    try { const r = await fetch(`${API_BASE}/behavior-tree/stats`); if (r.ok) setStats(await r.json()); } catch (e) { console.error(e); }
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

  const tabs = ['overview', 'create', 'tick', 'inspect'];

  return (
    <div className="h-full flex flex-col bg-[#1a1a2e] text-white">
      <div className="flex gap-1 p-3 border-b border-[#2a2a4a]">
        {tabs.map(t => <button key={t} onClick={() => setActiveTab(t)} className={`px-4 py-2 rounded text-sm font-medium ${activeTab === t ? 'bg-[#00d4ff] text-black' : 'bg-[#0f0f23] text-[#ccc] hover:bg-[#2a2a4a]'}`}>{t.charAt(0).toUpperCase()+t.slice(1)}</button>)}
      </div>
      {message && <div className="mx-4 mt-2 p-2 bg-[#0f0f23] border border-[#2a2a4a] rounded text-sm text-[#00d4ff]">{message}</div>}
      <div className="flex-1 overflow-auto p-4">
        {activeTab === 'overview' && (
          <div className="space-y-4">
            <h2 className="text-lg font-bold text-[#00d4ff]">Behavior Tree System</h2>
            <div className="grid grid-cols-3 gap-4">
              <div className="bg-[#0f0f23] p-4 rounded border border-[#2a2a4a]"><h3 className="text-[#00d4ff] text-sm">Total Trees</h3><p className="text-2xl">{stats.total_trees||0}</p></div>
              <div className="bg-[#0f0f23] p-4 rounded border border-[#2a2a4a]"><h3 className="text-[#00d4ff] text-sm">Active</h3><p className="text-2xl">{stats.active_trees||0}</p></div>
              <div className="bg-[#0f0f23] p-4 rounded border border-[#2a2a4a]"><h3 className="text-[#00d4ff] text-sm">Total Ticks</h3><p className="text-2xl">{stats.total_ticks||0}</p></div>
            </div>
          </div>
        )}
        {activeTab === 'create' && (
          <div className="space-y-4">
            <h2 className="text-lg font-bold text-[#00d4ff]">Create Behavior Tree</h2>
            <input className="w-full bg-[#0f0f23] border border-[#2a2a4a] rounded px-3 py-2 text-sm" placeholder="Tree Name" value={treeName} onChange={e => setTreeName(e.target.value)} />
            <input className="w-full bg-[#0f0f23] border border-[#2a2a4a] rounded px-3 py-2 text-sm" placeholder="Agent ID" value={agentId} onChange={e => setAgentId(e.target.value)} />
            <button className="px-4 py-2 bg-[#00d4ff] text-black rounded text-sm" onClick={async () => { const r = await handleSubmit(`${API_BASE}/behavior-tree/create-tree`, {name: treeName, agent_id: agentId}); if (r?.tree_id) setTreeId(r.tree_id); }}>Create</button>
          </div>
        )}
        {activeTab === 'tick' && (
          <div className="space-y-4">
            <h2 className="text-lg font-bold text-[#00d4ff]">Execute Tick</h2>
            <input className="w-full bg-[#0f0f23] border border-[#2a2a4a] rounded px-3 py-2 text-sm" placeholder="Tree ID" value={treeId} onChange={e => setTreeId(e.target.value)} />
            <button className="px-4 py-2 bg-[#00d4ff] text-black rounded text-sm" onClick={async () => { const r = await handleSubmit(`${API_BASE}/behavior-tree/tick`, {tree_id: treeId}); if (r) setTreeData(r); }}>Tick</button>
            {treeData && <pre className="bg-[#0f0f23] p-4 rounded border border-[#2a2a4a] text-xs overflow-auto">{JSON.stringify(treeData, null, 2)}</pre>}
          </div>
        )}
        {activeTab === 'inspect' && (
          <div className="space-y-4">
            <h2 className="text-lg font-bold text-[#00d4ff]">Inspect Tree</h2>
            <input className="w-full bg-[#0f0f23] border border-[#2a2a4a] rounded px-3 py-2 text-sm" placeholder="Tree ID" value={treeId} onChange={e => setTreeId(e.target.value)} />
            <button className="px-4 py-2 bg-[#00d4ff] text-black rounded text-sm" onClick={async () => { const r = await fetch(`${API_BASE}/behavior-tree/tree?tree_id=${treeId}`); if (r.ok) setTreeData(await r.json()); }}>Fetch</button>
            {treeData && <pre className="bg-[#0f0f23] p-4 rounded border border-[#2a2a4a] text-xs overflow-auto">{JSON.stringify(treeData, null, 2)}</pre>}
          </div>
        )}
      </div>
    </div>
  );
}