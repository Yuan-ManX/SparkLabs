"use client";
import React, { useState, useEffect, useCallback } from 'react';
import { API_BASE as API_ROOT } from '../utils/api';

const API_BASE = API_ROOT + '/engine';

export default function EngineCollisionSystemPanel() {
  const [activeTab, setActiveTab] = useState('overview');
  const [stats, setStats] = useState<any>({});
  const [bodyId, setBodyId] = useState('');
  const [result, setResult] = useState<any>(null);
  const [message, setMessage] = useState('');

  const fetchStats = useCallback(async () => {
    try { const r = await fetch(`${API_BASE}/collision-system/stats`); if (r.ok) setStats(await r.json()); } catch (e) { console.error(e); }
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

  const tabs = ['overview', 'bodies', 'raycast', 'overlap'];

  return (
    <div className="h-full flex flex-col bg-[#1a1a1a] text-white">
      <div className="flex gap-1 p-3 border-b border-[#2a2a2a]">
        {tabs.map(t => <button key={t} onClick={() => setActiveTab(t)} className={`px-4 py-2 rounded text-sm font-medium ${activeTab === t ? 'bg-[#f97316] text-black' : 'bg-[#0d0d0d] text-[#ccc] hover:bg-[#2a2a2a]'}`}>{t.charAt(0).toUpperCase()+t.slice(1)}</button>)}
      </div>
      {message && <div className="mx-4 mt-2 p-2 bg-[#0d0d0d] border border-[#2a2a2a] rounded text-sm text-[#f97316]">{message}</div>}
      <div className="flex-1 overflow-auto p-4">
        {activeTab === 'overview' && (
          <div className="space-y-4">
            <h2 className="text-lg font-bold text-[#f97316]">Collision System</h2>
            <div className="grid grid-cols-3 gap-4">
              <div className="bg-[#0d0d0d] p-4 rounded border border-[#2a2a2a]"><h3 className="text-[#f97316] text-sm">Total Bodies</h3><p className="text-2xl">{stats.total_bodies||0}</p></div>
              <div className="bg-[#0d0d0d] p-4 rounded border border-[#2a2a2a]"><h3 className="text-[#f97316] text-sm">Static</h3><p className="text-2xl">{stats.static_bodies||0}</p></div>
              <div className="bg-[#0d0d0d] p-4 rounded border border-[#2a2a2a]"><h3 className="text-[#f97316] text-sm">Dynamic</h3><p className="text-2xl">{stats.dynamic_bodies||0}</p></div>
              <div className="bg-[#0d0d0d] p-4 rounded border border-[#2a2a2a]"><h3 className="text-[#f97316] text-sm">Triggers</h3><p className="text-2xl">{stats.trigger_bodies||0}</p></div>
              <div className="bg-[#0d0d0d] p-4 rounded border border-[#2a2a2a]"><h3 className="text-[#f97316] text-sm">Collisions</h3><p className="text-2xl">{stats.recent_collisions||0}</p></div>
            </div>
          </div>
        )}
        {activeTab === 'bodies' && (
          <div className="space-y-4">
            <h2 className="text-lg font-bold text-[#f97316]">Create Body</h2>
            <button className="px-4 py-2 bg-[#f97316] text-black rounded text-sm" onClick={async () => { const r = await handleSubmit(`${API_BASE}/collision-system/create-body`, {entity_id: 'test', shape: 'aabb', position: [0,0], size: [1,1]}); if (r?.body_id) setBodyId(r.body_id); setResult(r); }}>Create</button>
            {bodyId && <p className="text-sm text-[#999]">Body ID: {bodyId}</p>}
            {result && <pre className="bg-[#0d0d0d] p-4 rounded border border-[#2a2a2a] text-xs overflow-auto">{JSON.stringify(result, null, 2)}</pre>}
          </div>
        )}
        {activeTab === 'raycast' && (
          <div className="space-y-4">
            <h2 className="text-lg font-bold text-[#f97316]">Raycast</h2>
            <button className="px-4 py-2 bg-[#f97316] text-black rounded text-sm" onClick={async () => { const r = await handleSubmit(`${API_BASE}/collision-system/raycast`, {origin: [0,0], direction: [1,0], max_distance: 100}); if (r) setResult(r); }}>Cast Ray</button>
            {result && <pre className="bg-[#0d0d0d] p-4 rounded border border-[#2a2a2a] text-xs overflow-auto">{JSON.stringify(result, null, 2)}</pre>}
          </div>
        )}
        {activeTab === 'overlap' && (
          <div className="space-y-4">
            <h2 className="text-lg font-bold text-[#f97316]">Overlap Area</h2>
            <button className="px-4 py-2 bg-[#f97316] text-black rounded text-sm" onClick={async () => { const r = await handleSubmit(`${API_BASE}/collision-system/overlap-area`, {shape: 'aabb', position: [0,0], size: [10,10]}); if (r) setResult(r); }}>Query</button>
            {result && <pre className="bg-[#0d0d0d] p-4 rounded border border-[#2a2a2a] text-xs overflow-auto">{JSON.stringify(result, null, 2)}</pre>}
          </div>
        )}
      </div>
    </div>
  );
}