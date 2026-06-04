import React, { useState, useEffect, useCallback } from 'react';

const API_BASE = 'http://localhost:8000/api/agent';

interface EmotionProfile {
  agent_id: string;
  mood: string;
  pleasure: number;
  arousal: number;
  dominance: number;
}

const AgentEmotionSynthesisPanel: React.FC = () => {
  const [stats, setStats] = useState<any>(null);
  const [profiles, setProfiles] = useState<EmotionProfile[]>([]);
  const [agentId, setAgentId] = useState('');
  const [eventType, setEventType] = useState('achievement');
  const [intensity, setIntensity] = useState('0.5');
  const [result, setResult] = useState<string | null>(null);

  const fetchData = useCallback(async () => {
    try {
      const [statsRes, profilesRes] = await Promise.all([
        fetch(`${API_BASE}/emotion-synthesis/stats`).then(r => r.json()),
        fetch(`${API_BASE}/emotion-synthesis/profiles`).then(r => r.json()),
      ]);
      setStats(statsRes);
      setProfiles(Array.isArray(profilesRes) ? profilesRes : []);
    } catch {}
  }, []);

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 15000);
    return () => clearInterval(interval);
  }, [fetchData]);

  const triggerEvent = async () => {
    if (!agentId.trim()) return;
    try {
      const res = await fetch(`${API_BASE}/emotion-synthesis/trigger-event`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ agent_id: agentId, event: eventType, intensity: parseFloat(intensity) }),
      });
      const data = await res.json();
      if (data.error) setResult(`Error: ${data.error}`);
      else setResult(`Emotion updated: pleasure=${data.pleasure?.toFixed(2)}, arousal=${data.arousal?.toFixed(2)}`);
      fetchData();
    } catch {}
  };

  const moodColors: Record<string, string> = {
    joyful: '#facc15', melancholic: '#60a5fa', irritable: '#f87171',
    serene: '#34d399', anxious: '#fbbf24', energetic: '#fb923c',
    fatigued: '#9ca3af', neutral: '#6b7280',
  };

  return (
    <div className="h-full flex flex-col bg-[#0d0d0d]">
      <div className="flex items-center justify-between p-3 border-b border-[#1e1e1e]">
        <div className="flex items-center gap-2">
          <span className="text-lg">🎭</span>
          <span className="text-[12px] font-semibold text-[#ccc]">Emotion Synthesis</span>
        </div>
        <button onClick={fetchData} className="text-[9px] px-2 py-1 bg-[#333] hover:bg-[#444] text-[#ccc] rounded">
          Refresh
        </button>
      </div>

      <div className="flex-1 overflow-y-auto p-3 space-y-3">
        {stats && (
          <div className="grid grid-cols-3 gap-2">
            <div className="bg-[#1a1a1a] border border-[#333] rounded p-2 text-center">
              <div className="text-[16px] font-bold text-purple-400">{stats.profile_count || 0}</div>
              <div className="text-[9px] text-[#666]">Profiles</div>
            </div>
            <div className="bg-[#1a1a1a] border border-[#333] rounded p-2 text-center">
              <div className="text-[16px] font-bold text-amber-400">{stats.event_count || 0}</div>
              <div className="text-[9px] text-[#666]">Events</div>
            </div>
            <div className="bg-[#1a1a1a] border border-[#333] rounded p-2 text-center">
              <div className="text-[16px] font-bold text-cyan-400">{stats.memory_count || 0}</div>
              <div className="text-[9px] text-[#666]">Memories</div>
            </div>
          </div>
        )}

        <div className="bg-[#1a1a1a] border border-[#333] rounded p-3">
          <div className="text-[11px] font-semibold text-[#aaa] mb-2">Trigger Emotion Event</div>
          <div className="space-y-2">
            <input
              type="text" placeholder="Agent ID" value={agentId}
              onChange={e => setAgentId(e.target.value)}
              className="w-full bg-[#111] border border-[#333] rounded p-1.5 text-[11px] text-[#ccc] outline-none"
            />
            <select value={eventType} onChange={e => setEventType(e.target.value)}
              className="w-full bg-[#111] border border-[#333] rounded p-1.5 text-[11px] text-[#ccc] outline-none">
              {['achievement', 'failure', 'social_bond', 'social_rejection', 'threat', 'safety', 'surprise', 'loss', 'gain'].map(ev =>
                <option key={ev} value={ev}>{ev.replace(/_/g, ' ')}</option>
              )}
            </select>
            <div className="flex items-center gap-2">
              <span className="text-[10px] text-[#666] w-14">Intensity:</span>
              <input type="range" min="0" max="1" step="0.1" value={intensity}
                onChange={e => setIntensity(e.target.value)} className="flex-1 accent-purple-500" />
              <span className="text-[10px] text-[#888] w-6">{intensity}</span>
            </div>
            <button onClick={triggerEvent}
              className="w-full bg-purple-600 hover:bg-purple-700 text-white text-[11px] py-1.5 rounded transition-colors">
              Trigger Event
            </button>
          </div>
          {result && <div className="mt-2 p-2 bg-[#111] rounded text-[10px] text-[#aaa]">{result}</div>}
        </div>

        <div className="text-[10px] font-semibold text-[#888]">Agent Profiles</div>
        <div className="space-y-1.5">
          {profiles.map(p => (
            <div key={p.agent_id} className="bg-[#1a1a1a] border border-[#333] rounded p-2 flex items-center justify-between">
              <div>
                <div className="text-[11px] text-[#ccc]">{p.agent_id}</div>
                <span className="text-[9px] px-1.5 py-0.5 rounded" style={{ background: moodColors[p.mood] + '30', color: moodColors[p.mood] }}>
                  {p.mood}
                </span>
              </div>
              <div className="flex gap-3 text-[10px]">
                <span style={{ color: p.pleasure > 0 ? '#34d399' : '#f87171' }}>P: {p.pleasure?.toFixed(2)}</span>
                <span style={{ color: '#60a5fa' }}>A: {p.arousal?.toFixed(2)}</span>
                <span style={{ color: '#fbbf24' }}>D: {p.dominance?.toFixed(2)}</span>
              </div>
            </div>
          ))}
          {profiles.length === 0 && <div className="text-[10px] text-[#555] text-center py-4">No agent profiles yet</div>}
        </div>
      </div>
    </div>
  );
};

export default AgentEmotionSynthesisPanel;