"use client";
import React, { useState, useEffect, useCallback } from 'react';

const API_BASE = 'http://localhost:8000/api/agent';

export default function AgentProceduralStorytellerPanel() {
  const [activeTab, setActiveTab] = useState('overview');
  const [stats, setStats] = useState<any>({});
  const [storyName, setStoryName] = useState('');
  const [protagonistId, setProtagonistId] = useState('');
  const [storylineId, setStorylineId] = useState('');
  const [eventType, setEventType] = useState('');
  const [result, setResult] = useState<any>(null);
  const [message, setMessage] = useState('');

  const fetchStats = useCallback(async () => {
    try { const r = await fetch(`${API_BASE}/procedural-storyteller/stats`); if (r.ok) setStats(await r.json()); } catch (e) { console.error(e); }
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

  const tabs = ['overview', 'create', 'advance', 'events'];

  return (
    <div className="h-full flex flex-col bg-[#1a1a2e] text-white">
      <div className="flex gap-1 p-3 border-b border-[#2a2a4a]">
        {tabs.map(t => <button key={t} onClick={() => setActiveTab(t)} className={`px-4 py-2 rounded text-sm font-medium ${activeTab === t ? 'bg-[#00d4ff] text-black' : 'bg-[#0f0f23] text-gray-300 hover:bg-[#2a2a4a]'}`}>{t.charAt(0).toUpperCase()+t.slice(1)}</button>)}
      </div>
      {message && <div className="mx-4 mt-2 p-2 bg-[#0f0f23] border border-[#2a2a4a] rounded text-sm text-[#00d4ff]">{message}</div>}
      <div className="flex-1 overflow-auto p-4">
        {activeTab === 'overview' && (
          <div className="space-y-4">
            <h2 className="text-lg font-bold text-[#00d4ff]">Procedural Storyteller</h2>
            <div className="grid grid-cols-3 gap-4">
              <div className="bg-[#0f0f23] p-4 rounded border border-[#2a2a4a]"><h3 className="text-[#00d4ff] text-sm">Storylines</h3><p className="text-2xl">{stats.total_storylines||0}</p></div>
              <div className="bg-[#0f0f23] p-4 rounded border border-[#2a2a4a]"><h3 className="text-[#00d4ff] text-sm">Active</h3><p className="text-2xl">{stats.active_storylines||0}</p></div>
              <div className="bg-[#0f0f23] p-4 rounded border border-[#2a2a4a]"><h3 className="text-[#00d4ff] text-sm">Events</h3><p className="text-2xl">{stats.total_events||0}</p></div>
              <div className="bg-[#0f0f23] p-4 rounded border border-[#2a2a4a]"><h3 className="text-[#00d4ff] text-sm">Active Events</h3><p className="text-2xl">{stats.active_events||0}</p></div>
              <div className="bg-[#0f0f23] p-4 rounded border border-[#2a2a4a]"><h3 className="text-[#00d4ff] text-sm">Character Arcs</h3><p className="text-2xl">{stats.total_character_arcs||0}</p></div>
            </div>
          </div>
        )}
        {activeTab === 'create' && (
          <div className="space-y-4">
            <h2 className="text-lg font-bold text-[#00d4ff]">Create Storyline</h2>
            <input className="w-full bg-[#0f0f23] border border-[#2a2a4a] rounded px-3 py-2 text-sm" placeholder="Story Name" value={storyName} onChange={e => setStoryName(e.target.value)} />
            <input className="w-full bg-[#0f0f23] border border-[#2a2a4a] rounded px-3 py-2 text-sm" placeholder="Protagonist ID" value={protagonistId} onChange={e => setProtagonistId(e.target.value)} />
            <select className="w-full bg-[#0f0f23] border border-[#2a2a4a] rounded px-3 py-2 text-sm">
              <option value="heroes_journey">Hero's Journey</option><option value="mystery">Mystery</option><option value="redemption">Redemption</option>
            </select>
            <button className="px-4 py-2 bg-[#00d4ff] text-black rounded text-sm" onClick={async () => { const r = await handleSubmit(`${API_BASE}/procedural-storyteller/create-storyline`, {name: storyName, arc: 'heroes_journey', protagonist_id: protagonistId}); if (r?.storyline_id) setStorylineId(r.storyline_id); }}>Create</button>
          </div>
        )}
        {activeTab === 'advance' && (
          <div className="space-y-4">
            <h2 className="text-lg font-bold text-[#00d4ff]">Advance Story</h2>
            <input className="w-full bg-[#0f0f23] border border-[#2a2a4a] rounded px-3 py-2 text-sm" placeholder="Storyline ID" value={storylineId} onChange={e => setStorylineId(e.target.value)} />
            <button className="px-4 py-2 bg-[#00d4ff] text-black rounded text-sm" onClick={async () => { const r = await handleSubmit(`${API_BASE}/procedural-storyteller/advance-story`, {storyline_id: storylineId}); if (r) setResult(r); }}>Advance</button>
            {result && <pre className="bg-[#0f0f23] p-4 rounded border border-[#2a2a4a] text-xs overflow-auto">{JSON.stringify(result, null, 2)}</pre>}
          </div>
        )}
        {activeTab === 'events' && (
          <div className="space-y-4">
            <h2 className="text-lg font-bold text-[#00d4ff]">Generate World Event</h2>
            <input className="w-full bg-[#0f0f23] border border-[#2a2a4a] rounded px-3 py-2 text-sm" placeholder="Event Description" value={eventType} onChange={e => setEventType(e.target.value)} />
            <button className="px-4 py-2 bg-[#00d4ff] text-black rounded text-sm" onClick={async () => { const r = await handleSubmit(`${API_BASE}/procedural-storyteller/generate-event`, {event_type: 'world_change', description: eventType}); if (r) setResult(r); }}>Generate</button>
            {result && <pre className="bg-[#0f0f23] p-4 rounded border border-[#2a2a4a] text-xs overflow-auto">{JSON.stringify(result, null, 2)}</pre>}
          </div>
        )}
      </div>
    </div>
  );
}