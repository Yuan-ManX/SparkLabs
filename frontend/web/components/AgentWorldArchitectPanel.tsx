import React, { useState, useEffect, useCallback } from 'react';

const API_BASE = 'http://localhost:8000/api/agent';

const AgentWorldArchitectPanel: React.FC = () => {
  const [stats, setStats] = useState<any>(null);
  const [worlds, setWorlds] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [worldName, setWorldName] = useState('');
  const [settingType, setSettingType] = useState('fantasy');
  const [selectedWorld, setSelectedWorld] = useState<any>(null);
  const [characters, setCharacters] = useState<any[]>([]);

  const fetchData = useCallback(async () => {
    try {
      const [statsRes, worldsRes] = await Promise.all([
        fetch(`${API_BASE}/world-architect/stats`).then(r => r.json()),
        fetch(`${API_BASE}/world-architect/worlds?limit=10`).then(r => r.json()),
      ]);
      setStats(statsRes);
      setWorlds(Array.isArray(worldsRes) ? worldsRes : []);
    } catch {}
  }, []);

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 15000);
    return () => clearInterval(interval);
  }, [fetchData]);

  const handleCreateWorld = async () => {
    if (!worldName.trim()) return;
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/world-architect/create-world`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: worldName, setting_type: settingType }),
      });
      const data = await res.json();
      setSelectedWorld(data);
      setWorldName('');
      fetchData();
    } catch {}
    setLoading(false);
  };

  const handleGenerateCharacters = async () => {
    if (!selectedWorld?.id) return;
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/world-architect/generate-characters`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ world_id: selectedWorld.id, count: 5 }),
      });
      const data = await res.json();
      setCharacters(Array.isArray(data) ? data : []);
    } catch {}
    setLoading(false);
  };

  const handleEvolveWorld = async () => {
    if (!selectedWorld?.id) return;
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/world-architect/evolve-world`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ world_id: selectedWorld.id, steps: 1 }),
      });
      setSelectedWorld(await res.json());
      fetchData();
    } catch {}
    setLoading(false);
  };

  return (
    <div className="h-full flex flex-col bg-[#0d0d0d]">
      <div className="flex items-center justify-between p-3 border-b border-[#1e1e1e]">
        <div className="flex items-center gap-2">
          <span className="text-lg">🌍</span>
          <span className="text-[12px] font-semibold text-[#ccc]">World Architect</span>
        </div>
        <button onClick={fetchData} className="text-[9px] px-2 py-1 bg-[#333] hover:bg-[#444] text-[#ccc] rounded">
          Refresh
        </button>
      </div>

      <div className="flex-1 overflow-y-auto p-3 space-y-3">
        {/* Stats */}
        {stats && (
          <div className="grid grid-cols-4 gap-2">
            <div className="bg-[#1a1a1a] border border-[#333] rounded p-2 text-center">
              <div className="text-[14px] font-bold text-blue-400">{stats.total_worlds || 0}</div>
              <div className="text-[9px] text-[#666]">Worlds</div>
            </div>
            <div className="bg-[#1a1a1a] border border-[#333] rounded p-2 text-center">
              <div className="text-[14px] font-bold text-green-400">{stats.total_characters || 0}</div>
              <div className="text-[9px] text-[#666]">Characters</div>
            </div>
            <div className="bg-[#1a1a1a] border border-[#333] rounded p-2 text-center">
              <div className="text-[14px] font-bold text-orange-400">{stats.total_rules || 0}</div>
              <div className="text-[9px] text-[#666]">Rules</div>
            </div>
            <div className="bg-[#1a1a1a] border border-[#333] rounded p-2 text-center">
              <div className="text-[14px] font-bold text-purple-400">{stats.merged_worlds || 0}</div>
              <div className="text-[9px] text-[#666]">Merged</div>
            </div>
          </div>
        )}

        {/* Create World */}
        <div className="bg-[#1a1a1a] border border-[#333] rounded p-3">
          <h4 className="text-[10px] font-bold text-[#888] uppercase tracking-wider mb-2">Create World</h4>
          <div className="flex gap-2 mb-2">
            <input
              type="text"
              value={worldName}
              onChange={(e) => setWorldName(e.target.value)}
              placeholder="World name..."
              className="flex-1 bg-[#0d0d0d] border border-[#333] rounded px-2 py-1.5 text-[11px] text-[#ccc] outline-none focus:border-orange-500"
            />
            <select
              value={settingType}
              onChange={(e) => setSettingType(e.target.value)}
              className="bg-[#0d0d0d] border border-[#333] rounded px-2 py-1.5 text-[11px] text-[#ccc] outline-none"
            >
              <option value="fantasy">Fantasy</option>
              <option value="sci-fi">Sci-Fi</option>
              <option value="horror">Horror</option>
              <option value="modern">Modern</option>
              <option value="post-apocalyptic">Post-Apocalyptic</option>
              <option value="steampunk">Steampunk</option>
            </select>
          </div>
          <button
            onClick={handleCreateWorld}
            disabled={loading || !worldName.trim()}
            className="w-full py-1.5 bg-orange-600 hover:bg-orange-500 text-white text-[10px] rounded font-medium disabled:opacity-50"
          >
            {loading ? 'Creating...' : 'Create World'}
          </button>
        </div>

        {/* Selected World */}
        {selectedWorld && (
          <div className="bg-[#1a1a1a] border border-orange-500/30 rounded p-2">
            <h4 className="text-[10px] font-bold text-orange-400 uppercase tracking-wider mb-2">
              {selectedWorld.name || 'World'}
            </h4>
            <div className="flex gap-2 mb-2">
              <button
                onClick={handleGenerateCharacters}
                disabled={loading}
                className="flex-1 py-1.5 bg-blue-600 hover:bg-blue-500 text-white text-[9px] rounded font-medium disabled:opacity-50"
              >
                Generate Characters
              </button>
              <button
                onClick={handleEvolveWorld}
                disabled={loading}
                className="flex-1 py-1.5 bg-purple-600 hover:bg-purple-500 text-white text-[9px] rounded font-medium disabled:opacity-50"
              >
                Evolve World
              </button>
            </div>
            <pre className="text-[9px] text-[#aaa] overflow-auto max-h-24 whitespace-pre-wrap">
              {JSON.stringify(selectedWorld, null, 2)}
            </pre>
          </div>
        )}

        {/* Characters */}
        {characters.length > 0 && (
          <div>
            <h4 className="text-[10px] font-bold text-[#888] uppercase tracking-wider mb-2">
              Characters ({characters.length})
            </h4>
            <div className="space-y-1">
              {characters.map((char, i) => (
                <div key={i} className="p-2 bg-[#1a1a1a] border border-[#333] rounded">
                  <div className="flex items-center justify-between">
                    <span className="text-[10px] text-[#ccc] font-medium">{char.name || `Character ${i + 1}`}</span>
                    <span className="text-[9px] text-[#666]">{char.role || char.archetype || ''}</span>
                  </div>
                  {char.description && (
                    <div className="text-[9px] text-[#888] mt-1">{char.description}</div>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Worlds List */}
        <div>
          <h4 className="text-[10px] font-bold text-[#888] uppercase tracking-wider mb-2">
            Worlds ({worlds.length})
          </h4>
          <div className="space-y-1">
            {worlds.map((world) => (
              <div
                key={world.id}
                onClick={() => setSelectedWorld(world)}
                className={`p-2 rounded border cursor-pointer transition-colors ${
                  selectedWorld?.id === world.id
                    ? 'border-orange-500 bg-orange-500/10'
                    : 'border-[#333] bg-[#1a1a1a] hover:bg-[#222]'
                }`}
              >
                <div className="flex items-center justify-between">
                  <span className="text-[10px] text-[#ccc]">{world.name}</span>
                  <span className="text-[9px] text-[#666]">{world.setting_type || ''}</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
};

export default AgentWorldArchitectPanel;