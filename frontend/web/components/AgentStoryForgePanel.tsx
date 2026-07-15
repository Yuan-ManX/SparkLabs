import React, { useState, useEffect, useCallback } from 'react';
import { API_BASE as API_ROOT } from '../utils/api';

const API_BASE = API_ROOT + '/agent';

interface StoryArc {
  arc_id: string;
  title: string;
  arc_type: string;
  genre: string;
  protagonist: string;
  beat_count: number;
}

interface StoryBeat {
  beat_id: string;
  phase: string;
  description: string;
}

const AgentStoryForgePanel: React.FC = () => {
  const [stats, setStats] = useState<any>(null);
  const [arcs, setArcs] = useState<StoryArc[]>([]);
  const [beats, setBeats] = useState<StoryBeat[]>([]);
  const [activeTab, setActiveTab] = useState<'create' | 'arcs' | 'beats'>('arcs');
  const [title, setTitle] = useState('');
  const [arcType, setArcType] = useState('heroes_journey');
  const [genre, setGenre] = useState('fantasy');
  const [protagonist, setProtagonist] = useState('Hero');
  const [selectedArcId, setSelectedArcId] = useState('');
  const [beatCount, setBeatCount] = useState('8');
  const [message, setMessage] = useState<string | null>(null);

  const fetchData = useCallback(async () => {
    try {
      const [statsRes, arcsRes] = await Promise.all([
        fetch(`${API_BASE}/story-forge/stats`).then(r => r.json()),
        fetch(`${API_BASE}/story-forge/arcs`).then(r => r.json()),
      ]);
      setStats(statsRes);
      setArcs(Array.isArray(arcsRes) ? arcsRes : []);
    } catch {}
  }, []);

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 15000);
    return () => clearInterval(interval);
  }, [fetchData]);

  const createArc = async () => {
    if (!title.trim()) return;
    try {
      const res = await fetch(`${API_BASE}/story-forge/create-arc`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ title, arc_type: arcType, genre, protagonist }),
      });
      const data = await res.json();
      if (data.error) setMessage(`Error: ${data.error}`);
      else setMessage(`Arc "${data.title}" created successfully`);
      setTitle(''); fetchData();
    } catch {}
  };

  const generateBeats = async () => {
    if (!selectedArcId) return;
    try {
      const res = await fetch(`${API_BASE}/story-forge/generate-beats`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ arc_id: selectedArcId, beat_count: parseInt(beatCount) }),
      });
      const data = await res.json();
      if (data.error) setMessage(`Error: ${data.error}`);
      else { setBeats(Array.isArray(data) ? data : []); setActiveTab('beats'); }
    } catch {}
  };

  return (
    <div className="h-full flex flex-col bg-[#0d0d0d]">
      <div className="flex items-center justify-between p-3 border-b border-[#1e1e1e]">
        <div className="flex items-center gap-2">
          <span className="text-lg">📖</span>
          <span className="text-[12px] font-semibold text-[#ccc]">Story Forge</span>
        </div>
        <button onClick={fetchData} className="text-[9px] px-2 py-1 bg-[#333] hover:bg-[#444] text-[#ccc] rounded">
          Refresh
        </button>
      </div>

      <div className="flex border-b border-[#1e1e1e]">
        {(['arcs', 'create', 'beats'] as const).map(tab => (
          <button key={tab} onClick={() => setActiveTab(tab)}
            className={`flex-1 text-[10px] py-2 ${activeTab === tab ? 'bg-[#1a1a1a] text-[#ccc] border-b border-orange-500' : 'text-[#666] hover:text-[#999]'}`}>
            {tab === 'arcs' ? 'Story Arcs' : tab === 'create' ? 'New Arc' : 'Beats'}
          </button>
        ))}
      </div>

      <div className="flex-1 overflow-y-auto p-3 space-y-3">
        {stats && (
          <div className="grid grid-cols-3 gap-2">
            <div className="bg-[#1a1a1a] border border-[#333] rounded p-2 text-center">
              <div className="text-[16px] font-bold text-orange-400">{stats.arc_count || 0}</div>
              <div className="text-[9px] text-[#666]">Arcs</div>
            </div>
            <div className="bg-[#1a1a1a] border border-[#333] rounded p-2 text-center">
              <div className="text-[16px] font-bold text-pink-400">{stats.character_count || 0}</div>
              <div className="text-[9px] text-[#666]">Characters</div>
            </div>
            <div className="bg-[#1a1a1a] border border-[#333] rounded p-2 text-center">
              <div className="text-[16px] font-bold text-green-400">{stats.twist_count || 0}</div>
              <div className="text-[9px] text-[#666]">Twists</div>
            </div>
          </div>
        )}

        {activeTab === 'create' && (
          <div className="bg-[#1a1a1a] border border-[#333] rounded p-3 space-y-2">
            <input type="text" placeholder="Arc Title" value={title}
              onChange={e => setTitle(e.target.value)}
              className="w-full bg-[#111] border border-[#333] rounded p-1.5 text-[11px] text-[#ccc] outline-none" />
            <select value={arcType} onChange={e => setArcType(e.target.value)}
              className="w-full bg-[#111] border border-[#333] rounded p-1.5 text-[11px] text-[#ccc] outline-none">
              {['heroes_journey', 'rags_to_riches', 'tragedy', 'comedy', 'rebirth', 'voyage_and_return', 'overcoming_monster', 'quest'].map(t =>
                <option key={t} value={t}>{t.replace(/_/g, ' ')}</option>
              )}
            </select>
            <select value={genre} onChange={e => setGenre(e.target.value)}
              className="w-full bg-[#111] border border-[#333] rounded p-1.5 text-[11px] text-[#ccc] outline-none">
              {['fantasy', 'sci_fi', 'horror', 'mystery', 'romance', 'adventure', 'thriller', 'comedy', 'drama'].map(g =>
                <option key={g} value={g}>{g.replace(/_/g, ' ')}</option>
              )}
            </select>
            <input type="text" placeholder="Protagonist" value={protagonist}
              onChange={e => setProtagonist(e.target.value)}
              className="w-full bg-[#111] border border-[#333] rounded p-1.5 text-[11px] text-[#ccc] outline-none" />
            <button onClick={createArc}
              className="w-full bg-orange-600 hover:bg-orange-700 text-white text-[11px] py-1.5 rounded transition-colors">
              Create Story Arc
            </button>
          </div>
        )}

        {activeTab === 'arcs' && (
          <div className="space-y-1.5">
            {arcs.map(arc => (
              <div key={arc.arc_id} onClick={() => setSelectedArcId(arc.arc_id)}
                className={`bg-[#1a1a1a] border rounded p-2 cursor-pointer ${selectedArcId === arc.arc_id ? 'border-orange-500' : 'border-[#333]'}`}>
                <div className="text-[11px] font-semibold text-[#ccc]">{arc.title}</div>
                <div className="flex gap-2 mt-1">
                  <span className="text-[9px] px-1.5 py-0.5 bg-[#222] rounded text-orange-400">{arc.arc_type}</span>
                  <span className="text-[9px] px-1.5 py-0.5 bg-[#222] rounded text-blue-400">{arc.genre}</span>
                  <span className="text-[9px] text-[#666]">{arc.protagonist}</span>
                </div>
              </div>
            ))}
            {arcs.length === 0 && <div className="text-[10px] text-[#555] text-center py-4">No story arcs yet</div>}
            {selectedArcId && (
              <div className="flex items-center gap-2 mt-3">
                <input type="number" min="1" max="20" value={beatCount}
                  onChange={e => setBeatCount(e.target.value)}
                  className="w-16 bg-[#111] border border-[#333] rounded p-1 text-[11px] text-[#ccc] outline-none" />
                <button onClick={generateBeats}
                  className="flex-1 bg-orange-600 hover:bg-orange-700 text-white text-[10px] py-1.5 rounded">
                  Generate {beatCount} Beats
                </button>
              </div>
            )}
          </div>
        )}

        {activeTab === 'beats' && (
          <div className="space-y-1.5">
            {beats.map((beat, idx) => (
              <div key={beat.beat_id || idx} className="bg-[#1a1a1a] border border-[#333] rounded p-2">
                <div className="flex items-center gap-2">
                  <span className="text-[9px] bg-emerald-600 text-white px-1.5 py-0.5 rounded">{idx + 1}</span>
                  <span className="text-[10px] font-semibold text-emerald-400">{beat.phase}</span>
                </div>
                <div className="text-[10px] text-[#aaa] mt-1">{beat.description}</div>
              </div>
            ))}
            {beats.length === 0 && <div className="text-[10px] text-[#555] text-center py-4">No beats generated</div>}
          </div>
        )}

        {message && <div className="p-2 bg-[#111] rounded text-[10px] text-[#aaa]">{message}</div>}
      </div>
    </div>
  );
};

export default AgentStoryForgePanel;