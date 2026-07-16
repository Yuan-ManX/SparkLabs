"use client";
import React, { useState, useEffect, useCallback } from 'react';
import { API_BASE as API_ROOT } from '../utils/api';

const API_BASE = API_ROOT + '/agent';

export default function AgentEmotionSystemPanel() {
  const [activeTab, setActiveTab] = useState('overview');
  const [stats, setStats] = useState<any>({});
  const [agentId, setAgentId] = useState('');
  const [agentState, setAgentState] = useState<any>(null);
  const [message, setMessage] = useState('');
  const [eventType, setEventType] = useState('reward');
  const [eventIntensity, setEventIntensity] = useState(0.5);

  const fetchStats = useCallback(async () => {
    try {
      const r = await fetch(`${API_BASE}/emotion-system/stats`);
      if (r.ok) setStats(await r.json());
    } catch (e) { console.error(e); }
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

  const tabs = ['overview', 'register', 'events', 'state'];

  return (
    <div className="h-full flex flex-col bg-[#1a1a2e] text-white">
      <div className="flex gap-1 p-3 border-b border-[#2a2a4a]">
        {tabs.map(t => <button key={t} onClick={() => setActiveTab(t)} className={`px-4 py-2 rounded text-sm font-medium ${activeTab === t ? 'bg-[#00d4ff] text-black' : 'bg-[#0d0d0d] text-[#ccc] hover:bg-[#2a2a4a]'}`}>{t.charAt(0).toUpperCase()+t.slice(1)}</button>)}
      </div>
      {message && <div className="mx-4 mt-2 p-2 bg-[#0d0d0d] border border-[#2a2a4a] rounded text-sm text-[#00d4ff]">{message}</div>}
      <div className="flex-1 overflow-auto p-4">
        {activeTab === 'overview' && (
          <div className="space-y-4">
            <h2 className="text-lg font-bold text-[#00d4ff]">Emotion System</h2>
            <div className="grid grid-cols-3 gap-4">
              <div className="bg-[#0d0d0d] p-4 rounded border border-[#2a2a4a]"><h3 className="text-[#00d4ff] text-sm">Agents</h3><p className="text-2xl">{stats.total_agents||0}</p></div>
              <div className="bg-[#0d0d0d] p-4 rounded border border-[#2a2a4a]"><h3 className="text-[#00d4ff] text-sm">Relationships</h3><p className="text-2xl">{stats.total_relationships||0}</p></div>
              <div className="bg-[#0d0d0d] p-4 rounded border border-[#2a2a4a]"><h3 className="text-[#00d4ff] text-sm">Active</h3><p className="text-2xl">{stats.active_agents||0}</p></div>
            </div>
            {stats.mood_distribution && <div className="bg-[#0d0d0d] p-4 rounded border border-[#2a2a4a]"><h3 className="text-[#00d4ff] mb-2">Mood Distribution</h3>{Object.entries(stats.mood_distribution).map(([k,v]) => <div key={k} className="flex justify-between text-sm"><span>{k}</span><span className="text-[#00d4ff]">{v as number}</span></div>)}</div>}
          </div>
        )}
        {activeTab === 'register' && (
          <div className="space-y-4">
            <h2 className="text-lg font-bold text-[#00d4ff]">Register Agent</h2>
            <input className="w-full bg-[#0d0d0d] border border-[#2a2a4a] rounded px-3 py-2 text-sm" placeholder="Agent ID" value={agentId} onChange={e => setAgentId(e.target.value)} />
            <button className="px-4 py-2 bg-[#00d4ff] text-black rounded text-sm" onClick={async () => { const r = await handleSubmit(`${API_BASE}/emotion-system/register-agent`, {agent_id: agentId}); if (r?.agent_id) setAgentId(r.agent_id); }}>Register</button>
          </div>
        )}
        {activeTab === 'events' && (
          <div className="space-y-4">
            <h2 className="text-lg font-bold text-[#00d4ff]">Process Event</h2>
            <input className="w-full bg-[#0d0d0d] border border-[#2a2a4a] rounded px-3 py-2 text-sm" placeholder="Agent ID" value={agentId} onChange={e => setAgentId(e.target.value)} />
            <select className="w-full bg-[#0d0d0d] border border-[#2a2a4a] rounded px-3 py-2 text-sm" value={eventType} onChange={e => setEventType(e.target.value)}>
              <option value="reward">Reward</option><option value="threat">Threat</option><option value="loss">Loss</option><option value="social">Social</option>
            </select>
            <label className="text-sm text-[#999]">Intensity: {eventIntensity}</label>
            <input type="range" min="0" max="1" step="0.1" value={eventIntensity} onChange={e => setEventIntensity(parseFloat(e.target.value))} className="w-full" />
            <button className="px-4 py-2 bg-[#00d4ff] text-black rounded text-sm" onClick={async () => { const r = await handleSubmit(`${API_BASE}/emotion-system/process-event`, {agent_id: agentId, event_type: eventType, intensity: eventIntensity}); if (r) setAgentState(r); }}>Process</button>
          </div>
        )}
        {activeTab === 'state' && (
          <div className="space-y-4">
            <h2 className="text-lg font-bold text-[#00d4ff]">Agent State</h2>
            <input className="w-full bg-[#0d0d0d] border border-[#2a2a4a] rounded px-3 py-2 text-sm" placeholder="Agent ID" value={agentId} onChange={e => setAgentId(e.target.value)} />
            <button className="px-4 py-2 bg-[#00d4ff] text-black rounded text-sm" onClick={async () => { const r = await fetch(`${API_BASE}/emotion-system/agent-state?agent_id=${agentId}`); if (r.ok) setAgentState(await r.json()); }}>Fetch</button>
            {agentState && <pre className="bg-[#0d0d0d] p-4 rounded border border-[#2a2a4a] text-xs overflow-auto">{JSON.stringify(agentState, null, 2)}</pre>}
          </div>
        )}
      </div>
    </div>
  );
}