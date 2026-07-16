"use client";
import React, { useState, useEffect, useCallback } from 'react';
import { API_BASE as API_ROOT } from '../utils/api';

const API_BASE = API_ROOT + '/engine';

export default function EngineGameLoopPanel() {
  const [activeTab, setActiveTab] = useState('overview');
  const [stats, setStats] = useState<any>({});
  const [frameTiming, setFrameTiming] = useState<any>(null);
  const [message, setMessage] = useState('');

  const fetchStats = useCallback(async () => {
    try { const r = await fetch(`${API_BASE}/game-loop/stats`); if (r.ok) setStats(await r.json()); } catch (e) { console.error(e); }
  }, []);

  useEffect(() => { fetchStats(); const i = setInterval(fetchStats, 5000); return () => clearInterval(i); }, [fetchStats]);

  const handleSubmit = async (url: string, body: any) => {
    try {
      const r = await fetch(url, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body||{}) });
      const data = await r.json();
      setMessage(r.ok ? 'Success' : data.error || 'Failed');
      return data;
    } catch (e: any) { setMessage(e.message); }
  };

  const tabs = ['overview', 'controls', 'timing'];

  return (
    <div className="h-full flex flex-col bg-[#1a1a2e] text-white">
      <div className="flex gap-1 p-3 border-b border-[#2a2a4a]">
        {tabs.map(t => <button key={t} onClick={() => setActiveTab(t)} className={`px-4 py-2 rounded text-sm font-medium ${activeTab === t ? 'bg-[#00d4ff] text-black' : 'bg-[#0d0d0d] text-[#ccc] hover:bg-[#2a2a4a]'}`}>{t.charAt(0).toUpperCase()+t.slice(1)}</button>)}
      </div>
      {message && <div className="mx-4 mt-2 p-2 bg-[#0d0d0d] border border-[#2a2a4a] rounded text-sm text-[#00d4ff]">{message}</div>}
      <div className="flex-1 overflow-auto p-4">
        {activeTab === 'overview' && (
          <div className="space-y-4">
            <h2 className="text-lg font-bold text-[#00d4ff]">Game Loop</h2>
            <div className="grid grid-cols-3 gap-4">
              <div className="bg-[#0d0d0d] p-4 rounded border border-[#2a2a4a]"><h3 className="text-[#00d4ff] text-sm">State</h3><p className="text-2xl">{stats.state||'stopped'}</p></div>
              <div className="bg-[#0d0d0d] p-4 rounded border border-[#2a2a4a]"><h3 className="text-[#00d4ff] text-sm">FPS</h3><p className="text-2xl">{(stats.fps||0).toFixed(1)}</p></div>
              <div className="bg-[#0d0d0d] p-4 rounded border border-[#2a2a4a]"><h3 className="text-[#00d4ff] text-sm">Frames</h3><p className="text-2xl">{stats.frame_count||0}</p></div>
              <div className="bg-[#0d0d0d] p-4 rounded border border-[#2a2a4a]"><h3 className="text-[#00d4ff] text-sm">Delta Time</h3><p className="text-2xl">{((stats.delta_time||0)*1000).toFixed(2)}ms</p></div>
              <div className="bg-[#0d0d0d] p-4 rounded border border-[#2a2a4a]"><h3 className="text-[#00d4ff] text-sm">Layers</h3><p className="text-2xl">{stats.update_layers||0}</p></div>
              <div className="bg-[#0d0d0d] p-4 rounded border border-[#2a2a4a]"><h3 className="text-[#00d4ff] text-sm">Callbacks</h3><p className="text-2xl">{stats.total_callbacks||0}</p></div>
            </div>
          </div>
        )}
        {activeTab === 'controls' && (
          <div className="space-y-4">
            <h2 className="text-lg font-bold text-[#00d4ff]">Loop Controls</h2>
            <div className="flex gap-2">
              <button className="px-4 py-2 bg-green-600 text-white rounded text-sm" onClick={() => handleSubmit(`${API_BASE}/game-loop/start`, {})}>Start</button>
              <button className="px-4 py-2 bg-yellow-600 text-white rounded text-sm" onClick={() => handleSubmit(`${API_BASE}/game-loop/pause`, {})}>Pause</button>
              <button className="px-4 py-2 bg-orange-600 text-white rounded text-sm" onClick={() => handleSubmit(`${API_BASE}/game-loop/resume`, {})}>Resume</button>
              <button className="px-4 py-2 bg-red-600 text-white rounded text-sm" onClick={() => handleSubmit(`${API_BASE}/game-loop/stop`, {})}>Stop</button>
            </div>
          </div>
        )}
        {activeTab === 'timing' && (
          <div className="space-y-4">
            <h2 className="text-lg font-bold text-[#00d4ff]">Frame Timing</h2>
            <button className="px-4 py-2 bg-[#00d4ff] text-black rounded text-sm" onClick={async () => { const r = await fetch(`${API_BASE}/game-loop/frame-timing`); if (r.ok) setFrameTiming(await r.json()); }}>Fetch</button>
            {frameTiming && <pre className="bg-[#0d0d0d] p-4 rounded border border-[#2a2a4a] text-xs overflow-auto">{JSON.stringify(frameTiming, null, 2)}</pre>}
          </div>
        )}
      </div>
    </div>
  );
}