"use client";
import React, { useState, useEffect, useCallback } from 'react';
import { API_BASE as API_ROOT } from '../utils/api';

const API_BASE = API_ROOT + '/engine';

export default function EngineResourceCachePanel() {
  const [activeTab, setActiveTab] = useState('overview');
  const [stats, setStats] = useState<any>({});
  const [resourceId, setResourceId] = useState('');
  const [resourcePath, setResourcePath] = useState('');
  const [result, setResult] = useState<any>(null);
  const [message, setMessage] = useState('');

  const fetchStats = useCallback(async () => {
    try { const r = await fetch(`${API_BASE}/resource-cache/stats`); if (r.ok) setStats(await r.json()); } catch (e) { console.error(e); }
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

  const tabs = ['overview', 'load', 'groups'];

  return (
    <div className="h-full flex flex-col bg-[#1a1a2e] text-white">
      <div className="flex gap-1 p-3 border-b border-[#2a2a4a]">
        {tabs.map(t => <button key={t} onClick={() => setActiveTab(t)} className={`px-4 py-2 rounded text-sm font-medium ${activeTab === t ? 'bg-[#00d4ff] text-black' : 'bg-[#0f0f23] text-[#ccc] hover:bg-[#2a2a4a]'}`}>{t.charAt(0).toUpperCase()+t.slice(1)}</button>)}
      </div>
      {message && <div className="mx-4 mt-2 p-2 bg-[#0f0f23] border border-[#2a2a4a] rounded text-sm text-[#00d4ff]">{message}</div>}
      <div className="flex-1 overflow-auto p-4">
        {activeTab === 'overview' && (
          <div className="space-y-4">
            <h2 className="text-lg font-bold text-[#00d4ff]">Resource Cache</h2>
            <div className="grid grid-cols-3 gap-4">
              <div className="bg-[#0f0f23] p-4 rounded border border-[#2a2a4a]"><h3 className="text-[#00d4ff] text-sm">Total</h3><p className="text-2xl">{stats.total_resources||0}</p></div>
              <div className="bg-[#0f0f23] p-4 rounded border border-[#2a2a4a]"><h3 className="text-[#00d4ff] text-sm">Loaded</h3><p className="text-2xl">{stats.loaded_resources||0}</p></div>
              <div className="bg-[#0f0f23] p-4 rounded border border-[#2a2a4a]"><h3 className="text-[#00d4ff] text-sm">Failed</h3><p className="text-2xl">{stats.failed_resources||0}</p></div>
              <div className="bg-[#0f0f23] p-4 rounded border border-[#2a2a4a]"><h3 className="text-[#00d4ff] text-sm">Cache Size</h3><p className="text-2xl">{((stats.cache_size_bytes||0)/1024).toFixed(1)}KB</p></div>
              <div className="bg-[#0f0f23] p-4 rounded border border-[#2a2a4a]"><h3 className="text-[#00d4ff] text-sm">Usage</h3><p className="text-2xl">{(stats.cache_usage_percent||0).toFixed(1)}%</p></div>
              <div className="bg-[#0f0f23] p-4 rounded border border-[#2a2a4a]"><h3 className="text-[#00d4ff] text-sm">Groups</h3><p className="text-2xl">{stats.total_groups||0}</p></div>
            </div>
          </div>
        )}
        {activeTab === 'load' && (
          <div className="space-y-4">
            <h2 className="text-lg font-bold text-[#00d4ff]">Load Resource</h2>
            <input className="w-full bg-[#0f0f23] border border-[#2a2a4a] rounded px-3 py-2 text-sm" placeholder="Resource Path" value={resourcePath} onChange={e => setResourcePath(e.target.value)} />
            <button className="px-4 py-2 bg-[#00d4ff] text-black rounded text-sm" onClick={async () => { const r = await handleSubmit(`${API_BASE}/resource-cache/load`, {path: resourcePath, resource_type: 'data'}); if (r?.resource_id) setResourceId(r.resource_id); setResult(r); }}>Load</button>
            {result && <pre className="bg-[#0f0f23] p-4 rounded border border-[#2a2a4a] text-xs overflow-auto">{JSON.stringify(result, null, 2)}</pre>}
          </div>
        )}
        {activeTab === 'groups' && (
          <div className="space-y-4">
            <h2 className="text-lg font-bold text-[#00d4ff]">Resource Groups</h2>
            <button className="px-4 py-2 bg-[#00d4ff] text-black rounded text-sm" onClick={async () => { const r = await handleSubmit(`${API_BASE}/resource-cache/create-group`, {name: 'Level1', resource_paths: []}); if (r) setResult(r); }}>Create Group</button>
            {result && <pre className="bg-[#0f0f23] p-4 rounded border border-[#2a2a4a] text-xs overflow-auto">{JSON.stringify(result, null, 2)}</pre>}
          </div>
        )}
      </div>
    </div>
  );
}