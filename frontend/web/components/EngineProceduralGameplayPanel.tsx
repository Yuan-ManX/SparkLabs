"use client";
import React, { useState, useEffect, useCallback } from 'react';

const API_BASE = 'http://localhost:8000/api/engine';

export default function EngineProceduralGameplayPanel() {
  const [activeTab, setActiveTab] = useState('overview');
  const [stats, setStats] = useState<any>({});
  const [message, setMessage] = useState('');
  const [loading, setLoading] = useState(false);

  // Session state
  const [sessName, setSessName] = useState('');
  const [sessConfig, setSessConfig] = useState('');

  // Mechanic state
  const [mechSessionId, setMechSessionId] = useState('');
  const [mechType, setMechType] = useState('combat');
  const [mechConstraints, setMechConstraints] = useState('');
  const [mechResult, setMechResult] = useState<any>(null);

  // Event state
  const [eventSessionId, setEventSessionId] = useState('');
  const [eventType, setEventType] = useState('combat');
  const [eventContext, setEventContext] = useState('');
  const [eventResult, setEventResult] = useState<any>(null);

  // Encounter state
  const [encSessionId, setEncSessionId] = useState('');
  const [encType, setEncType] = useState('combat');
  const [encDifficulty, setEncDifficulty] = useState('medium');
  const [encResult, setEncResult] = useState<any>(null);
  const [adaptSessionId, setAdaptSessionId] = useState('');
  const [adaptEncounterId, setAdaptEncounterId] = useState('');
  const [adaptTarget, setAdaptTarget] = useState('0.5');
  const [adaptResult, setAdaptResult] = useState<any>(null);

  const MECHANIC_TYPES = ['combat', 'movement', 'puzzle', 'resource', 'social', 'stealth', 'exploration', 'crafting'];
  const EVENT_TYPES = ['combat', 'exploration', 'dialogue', 'puzzle', 'ambient', 'story', 'random'];
  const ENCOUNTER_TYPES = ['combat', 'social', 'exploration', 'puzzle', 'boss', 'ambient'];
  const DIFFICULTY_OPTIONS = ['easy', 'medium', 'hard', 'expert', 'adaptive'];

  const fetchStats = useCallback(async () => {
    try { const r = await fetch(`${API_BASE}/procedural-gameplay/stats`); if (r.ok) setStats(await r.json()); } catch (e) { console.error(e); }
  }, []);

  useEffect(() => { fetchStats(); const i = setInterval(fetchStats, 15000); return () => clearInterval(i); }, [fetchStats]);

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

  const tabs = ['overview', 'session', 'mechanic', 'event', 'encounter'];

  return (
    <div className="h-full flex flex-col bg-[#1a1a2e] text-white">
      <div className="flex gap-1 p-3 border-b border-[#2a2a4a]">
        {tabs.map(t => <button key={t} onClick={() => setActiveTab(t)} className={`px-4 py-2 rounded text-sm font-medium ${activeTab === t ? 'bg-[#00d4ff] text-black' : 'bg-[#0f0f23] text-gray-300 hover:bg-[#2a2a4a]'}`}>{t.charAt(0).toUpperCase()+t.slice(1)}</button>)}
      </div>
      {message && <div className="mx-4 mt-2 p-2 bg-[#0f0f23] border border-[#2a2a4a] rounded text-sm text-[#00d4ff]">{message}</div>}
      <div className="flex-1 overflow-auto p-4">
        {activeTab === 'overview' && (
          <div className="space-y-4">
            <h2 className="text-lg font-bold text-[#00d4ff]">Procedural Gameplay</h2>
            <div className="grid grid-cols-2 gap-4">
              <div className="bg-[#0f0f23] p-4 rounded border border-[#2a2a4a]"><h3 className="text-[#00d4ff] text-sm">Total Sessions</h3><p className="text-2xl">{stats.total_sessions ?? 0}</p></div>
              <div className="bg-[#0f0f23] p-4 rounded border border-[#2a2a4a]"><h3 className="text-[#00d4ff] text-sm">Total Mechanics</h3><p className="text-2xl">{stats.total_mechanics ?? 0}</p></div>
              <div className="bg-[#0f0f23] p-4 rounded border border-[#2a2a4a]"><h3 className="text-[#00d4ff] text-sm">Total Events</h3><p className="text-2xl">{stats.total_events ?? 0}</p></div>
              <div className="bg-[#0f0f23] p-4 rounded border border-[#2a2a4a]"><h3 className="text-[#00d4ff] text-sm">Total Encounters</h3><p className="text-2xl">{stats.total_encounters ?? 0}</p></div>
            </div>
            {Object.keys(stats).length > 0 && (
              <div className="bg-[#0f0f23] p-4 rounded border border-[#2a2a4a]">
                <h3 className="text-[#00d4ff] text-sm mb-2">All Stats</h3>
                <pre className="text-xs text-gray-300 overflow-auto">{JSON.stringify(stats, null, 2)}</pre>
              </div>
            )}
          </div>
        )}

        {activeTab === 'session' && (
          <div className="space-y-4">
            <h2 className="text-lg font-bold text-[#00d4ff]">Create Session</h2>
            <div className="bg-[#0f0f23] p-4 rounded border border-[#2a2a4a] space-y-3">
              <div>
                <label className="text-xs text-gray-400 mb-1 block">Session Name</label>
                <input type="text" value={sessName} onChange={e => setSessName(e.target.value)} placeholder="Forest Run #1" className="w-full bg-[#1a1a2e] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none" />
              </div>
              <div>
                <label className="text-xs text-gray-400 mb-1 block">Config (JSON)</label>
                <textarea value={sessConfig} onChange={e => setSessConfig(e.target.value)} placeholder='{"seed": 12345, "biome": "forest", "player_level": 5}' rows={3} className="w-full bg-[#1a1a2e] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none font-mono" />
              </div>
              <button
                onClick={async () => {
                  if (!sessName.trim()) { setMessage('Session name required'); return; }
                  let config = {};
                  try { if (sessConfig.trim()) config = JSON.parse(sessConfig); } catch { setMessage('Invalid config JSON'); return; }
                  await handleSubmit(`${API_BASE}/procedural-gameplay/create-session`, { name: sessName, config });
                  setSessName(''); setSessConfig('');
                  fetchStats();
                }}
                disabled={loading}
                className="px-4 py-2 bg-[#00d4ff] text-black rounded text-sm font-medium hover:bg-[#00b8e6] disabled:opacity-50"
              >
                Create Session
              </button>
            </div>
          </div>
        )}

        {activeTab === 'mechanic' && (
          <div className="space-y-4">
            <h2 className="text-lg font-bold text-[#00d4ff]">Generate Mechanic</h2>
            <div className="bg-[#0f0f23] p-4 rounded border border-[#2a2a4a] space-y-3">
              <div>
                <label className="text-xs text-gray-400 mb-1 block">Session ID</label>
                <input type="text" value={mechSessionId} onChange={e => setMechSessionId(e.target.value)} placeholder="sess_abc123" className="w-full bg-[#1a1a2e] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none" />
              </div>
              <div>
                <label className="text-xs text-gray-400 mb-1 block">Mechanic Type</label>
                <select value={mechType} onChange={e => setMechType(e.target.value)} className="w-full bg-[#1a1a2e] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none">
                  {MECHANIC_TYPES.map(m => <option key={m} value={m}>{m}</option>)}
                </select>
              </div>
              <div>
                <label className="text-xs text-gray-400 mb-1 block">Constraints (JSON)</label>
                <textarea value={mechConstraints} onChange={e => setMechConstraints(e.target.value)} placeholder='{"max_complexity": 3, "player_count": 1}' rows={2} className="w-full bg-[#1a1a2e] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none font-mono" />
              </div>
              <button
                onClick={async () => {
                  if (!mechSessionId.trim()) { setMessage('Session ID required'); return; }
                  let constraints = {};
                  try { if (mechConstraints.trim()) constraints = JSON.parse(mechConstraints); } catch { setMessage('Invalid constraints JSON'); return; }
                  const result = await handleSubmit(`${API_BASE}/procedural-gameplay/generate-mechanic`, { session_id: mechSessionId, mechanic_type: mechType, constraints });
                  if (result) setMechResult(result);
                  fetchStats();
                }}
                disabled={loading}
                className="px-4 py-2 bg-[#00d4ff] text-black rounded text-sm font-medium hover:bg-[#00b8e6] disabled:opacity-50"
              >
                Generate Mechanic
              </button>
            </div>

            {mechResult && (
              <div className="bg-[#0f0f23] p-4 rounded border border-[#2a2a4a]">
                <h3 className="text-[#00d4ff] text-sm font-medium mb-2">Generated Mechanic</h3>
                <pre className="text-xs text-gray-300 overflow-auto max-h-64">{JSON.stringify(mechResult, null, 2)}</pre>
              </div>
            )}
          </div>
        )}

        {activeTab === 'event' && (
          <div className="space-y-4">
            <h2 className="text-lg font-bold text-[#00d4ff]">Generate Event</h2>
            <div className="bg-[#0f0f23] p-4 rounded border border-[#2a2a4a] space-y-3">
              <div>
                <label className="text-xs text-gray-400 mb-1 block">Session ID</label>
                <input type="text" value={eventSessionId} onChange={e => setEventSessionId(e.target.value)} placeholder="sess_abc123" className="w-full bg-[#1a1a2e] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none" />
              </div>
              <div>
                <label className="text-xs text-gray-400 mb-1 block">Event Type</label>
                <select value={eventType} onChange={e => setEventType(e.target.value)} className="w-full bg-[#1a1a2e] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none">
                  {EVENT_TYPES.map(e => <option key={e} value={e}>{e}</option>)}
                </select>
              </div>
              <div>
                <label className="text-xs text-gray-400 mb-1 block">Context (JSON)</label>
                <textarea value={eventContext} onChange={e => setEventContext(e.target.value)} placeholder='{"location": "dark_forest", "time": "night"}' rows={2} className="w-full bg-[#1a1a2e] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none font-mono" />
              </div>
              <button
                onClick={async () => {
                  if (!eventSessionId.trim()) { setMessage('Session ID required'); return; }
                  let context = {};
                  try { if (eventContext.trim()) context = JSON.parse(eventContext); } catch { setMessage('Invalid context JSON'); return; }
                  const result = await handleSubmit(`${API_BASE}/procedural-gameplay/generate-event`, { session_id: eventSessionId, event_type: eventType, context });
                  if (result) setEventResult(result);
                  fetchStats();
                }}
                disabled={loading}
                className="px-4 py-2 bg-[#00d4ff] text-black rounded text-sm font-medium hover:bg-[#00b8e6] disabled:opacity-50"
              >
                Generate Event
              </button>
            </div>

            {eventResult && (
              <div className="bg-[#0f0f23] p-4 rounded border border-[#2a2a4a]">
                <h3 className="text-[#00d4ff] text-sm font-medium mb-2">Generated Event</h3>
                <pre className="text-xs text-gray-300 overflow-auto max-h-64">{JSON.stringify(eventResult, null, 2)}</pre>
              </div>
            )}
          </div>
        )}

        {activeTab === 'encounter' && (
          <div className="space-y-4">
            <h2 className="text-lg font-bold text-[#00d4ff]">Generate Encounter</h2>
            <div className="bg-[#0f0f23] p-4 rounded border border-[#2a2a4a] space-y-3">
              <div>
                <label className="text-xs text-gray-400 mb-1 block">Session ID</label>
                <input type="text" value={encSessionId} onChange={e => setEncSessionId(e.target.value)} placeholder="sess_abc123" className="w-full bg-[#1a1a2e] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none" />
              </div>
              <div>
                <label className="text-xs text-gray-400 mb-1 block">Encounter Type</label>
                <select value={encType} onChange={e => setEncType(e.target.value)} className="w-full bg-[#1a1a2e] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none">
                  {ENCOUNTER_TYPES.map(e => <option key={e} value={e}>{e}</option>)}
                </select>
              </div>
              <div>
                <label className="text-xs text-gray-400 mb-1 block">Difficulty</label>
                <select value={encDifficulty} onChange={e => setEncDifficulty(e.target.value)} className="w-full bg-[#1a1a2e] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none">
                  {DIFFICULTY_OPTIONS.map(d => <option key={d} value={d}>{d}</option>)}
                </select>
              </div>
              <button
                onClick={async () => {
                  if (!encSessionId.trim()) { setMessage('Session ID required'); return; }
                  const result = await handleSubmit(`${API_BASE}/procedural-gameplay/generate-encounter`, { session_id: encSessionId, encounter_type: encType, difficulty: encDifficulty });
                  if (result) setEncResult(result);
                  fetchStats();
                }}
                disabled={loading}
                className="px-4 py-2 bg-[#00d4ff] text-black rounded text-sm font-medium hover:bg-[#00b8e6] disabled:opacity-50"
              >
                Generate Encounter
              </button>
            </div>

            {encResult && (
              <div className="bg-[#0f0f23] p-4 rounded border border-[#2a2a4a]">
                <h3 className="text-[#00d4ff] text-sm font-medium mb-2">Generated Encounter</h3>
                <pre className="text-xs text-gray-300 overflow-auto max-h-64">{JSON.stringify(encResult, null, 2)}</pre>
              </div>
            )}

            <div className="bg-[#0f0f23] p-4 rounded border border-[#2a2a4a] space-y-3 mt-4">
              <h3 className="text-sm font-medium text-[#00d4ff]">Adapt Difficulty</h3>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-xs text-gray-400 mb-1 block">Session ID</label>
                  <input type="text" value={adaptSessionId} onChange={e => setAdaptSessionId(e.target.value)} placeholder="sess_abc123" className="w-full bg-[#1a1a2e] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none" />
                </div>
                <div>
                  <label className="text-xs text-gray-400 mb-1 block">Encounter ID</label>
                  <input type="text" value={adaptEncounterId} onChange={e => setAdaptEncounterId(e.target.value)} placeholder="enc_abc123" className="w-full bg-[#1a1a2e] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none" />
                </div>
              </div>
              <div>
                <label className="text-xs text-gray-400 mb-1 block">Target Win Rate</label>
                <input type="number" value={adaptTarget} onChange={e => setAdaptTarget(e.target.value)} step="0.01" min="0" max="1" className="w-full bg-[#1a1a2e] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none" />
              </div>
              <button
                onClick={async () => {
                  if (!adaptSessionId.trim() || !adaptEncounterId.trim()) { setMessage('Session ID and Encounter ID required'); return; }
                  const result = await handleSubmit(`${API_BASE}/procedural-gameplay/adapt-difficulty`, { session_id: adaptSessionId, encounter_id: adaptEncounterId, target_win_rate: parseFloat(adaptTarget) || 0.5 });
                  if (result) setAdaptResult(result);
                  fetchStats();
                }}
                disabled={loading}
                className="px-4 py-2 bg-[#00d4ff] text-black rounded text-sm font-medium hover:bg-[#00b8e6] disabled:opacity-50"
              >
                Adapt Difficulty
              </button>
            </div>

            {adaptResult && (
              <div className="bg-[#0f0f23] p-4 rounded border border-[#2a2a4a]">
                <h3 className="text-[#00d4ff] text-sm font-medium mb-2">Adaptation Result</h3>
                <pre className="text-xs text-gray-300 overflow-auto max-h-64">{JSON.stringify(adaptResult, null, 2)}</pre>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}