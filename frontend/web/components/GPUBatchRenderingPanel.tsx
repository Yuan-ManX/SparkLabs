import React, { useState, useEffect, useCallback } from 'react';
import { API_BASE as API_ROOT } from '../utils/api';

const API_BASE = API_ROOT + '/agent';

const GPUBatchRenderingPanel: React.FC = () => {
  const [stats, setStats] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [layerName, setLayerName] = useState('');
  const [maxSprites, setMaxSprites] = useState(1000);
  const [result, setResult] = useState<any>(null);
  const [qualityPreset, setQualityPreset] = useState('high');

  const fetchStats = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/gpu-rendering/stats`);
      setStats(await res.json());
    } catch {}
  }, []);

  useEffect(() => {
    fetchStats();
    const interval = setInterval(fetchStats, 15000);
    return () => clearInterval(interval);
  }, [fetchStats]);

  const handleCreateLayer = async () => {
    if (!layerName.trim()) return;
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/gpu-rendering/create-sprite-layer`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: layerName, max_sprites: maxSprites }),
      });
      setResult(await res.json());
      setLayerName('');
      fetchStats();
    } catch {}
    setLoading(false);
  };

  const handleSetQuality = async () => {
    setLoading(true);
    try {
      await fetch(`${API_BASE}/gpu-rendering/set-quality`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ preset: qualityPreset }),
      });
      fetchStats();
    } catch {}
    setLoading(false);
  };

  return (
    <div className="h-full flex flex-col bg-[#0d0d0d]">
      <div className="flex items-center justify-between p-3 border-b border-[#1e1e1e]">
        <div className="flex items-center gap-2">
          <span className="text-lg">🎮</span>
          <span className="text-[12px] font-semibold text-[#ccc]">GPU Batch Rendering</span>
        </div>
        <button onClick={fetchStats} className="text-[9px] px-2 py-1 bg-[#333] hover:bg-[#444] text-[#ccc] rounded">
          Refresh
        </button>
      </div>

      <div className="flex-1 overflow-y-auto p-3 space-y-3">
        {/* Stats */}
        {stats && (
          <div className="grid grid-cols-4 gap-2">
            <div className="bg-[#1a1a1a] border border-[#333] rounded p-2 text-center">
              <div className="text-[14px] font-bold text-blue-400">{stats.total_layers || 0}</div>
              <div className="text-[9px] text-[#666]">Layers</div>
            </div>
            <div className="bg-[#1a1a1a] border border-[#333] rounded p-2 text-center">
              <div className="text-[14px] font-bold text-green-400">{stats.total_sprites || 0}</div>
              <div className="text-[9px] text-[#666]">Sprites</div>
            </div>
            <div className="bg-[#1a1a1a] border border-[#333] rounded p-2 text-center">
              <div className="text-[14px] font-bold text-orange-400">{stats.draw_calls || 0}</div>
              <div className="text-[9px] text-[#666]">Draw Calls</div>
            </div>
            <div className="bg-[#1a1a1a] border border-[#333] rounded p-2 text-center">
              <div className="text-[14px] font-bold text-purple-400 capitalize">{stats.quality_preset || 'N/A'}</div>
              <div className="text-[9px] text-[#666]">Quality</div>
            </div>
          </div>
        )}

        {/* Create Sprite Layer */}
        <div className="bg-[#1a1a1a] border border-[#333] rounded p-3">
          <h4 className="text-[10px] font-bold text-[#888] uppercase tracking-wider mb-2">Create Sprite Layer</h4>
          <div className="flex gap-2 mb-2">
            <input
              type="text"
              value={layerName}
              onChange={(e) => setLayerName(e.target.value)}
              placeholder="Layer name..."
              className="flex-1 bg-[#0d0d0d] border border-[#333] rounded px-2 py-1.5 text-[11px] text-[#ccc] outline-none focus:border-orange-500"
            />
            <input
              type="number"
              value={maxSprites}
              onChange={(e) => setMaxSprites(Number(e.target.value))}
              min={1}
              max={1000000}
              className="w-24 bg-[#0d0d0d] border border-[#333] rounded px-2 py-1.5 text-[11px] text-[#ccc] outline-none focus:border-orange-500"
              placeholder="Max"
            />
          </div>
          <button
            onClick={handleCreateLayer}
            disabled={loading || !layerName.trim()}
            className="w-full py-1.5 bg-orange-600 hover:bg-orange-500 text-white text-[10px] rounded font-medium disabled:opacity-50"
          >
            {loading ? 'Creating...' : 'Create Layer'}
          </button>
        </div>

        {/* Quality Settings */}
        <div className="bg-[#1a1a1a] border border-[#333] rounded p-3">
          <h4 className="text-[10px] font-bold text-[#888] uppercase tracking-wider mb-2">Quality Settings</h4>
          <div className="flex gap-2">
            <select
              value={qualityPreset}
              onChange={(e) => setQualityPreset(e.target.value)}
              className="flex-1 bg-[#0d0d0d] border border-[#333] rounded px-2 py-1.5 text-[11px] text-[#ccc] outline-none"
            >
              <option value="low">Low</option>
              <option value="medium">Medium</option>
              <option value="high">High</option>
              <option value="ultra">Ultra</option>
            </select>
            <button
              onClick={handleSetQuality}
              disabled={loading}
              className="px-3 py-1.5 bg-orange-600 hover:bg-orange-500 text-white text-[10px] rounded font-medium disabled:opacity-50"
            >
              Apply
            </button>
          </div>
        </div>

        {/* Detailed Stats */}
        {stats && (
          <div className="bg-[#1a1a1a] border border-[#333] rounded p-2">
            <h4 className="text-[10px] font-bold text-[#888] uppercase tracking-wider mb-2">GPU Stats</h4>
            <div className="grid grid-cols-2 gap-1.5">
              {Object.entries(stats).filter(([k]) => !['total_layers', 'total_sprites', 'draw_calls', 'quality_preset'].includes(k)).map(([key, value]) => (
                <div key={key} className="flex justify-between text-[10px] p-1.5 bg-[#111] rounded">
                  <span className="text-[#888] capitalize">{key.replace(/_/g, ' ')}</span>
                  <span className="text-[#aaa]">
                    {typeof value === 'number' ? value.toFixed(1) : String(value)}
                  </span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Result */}
        {result && (
          <div className="bg-[#1a1a1a] border border-[#333] rounded p-2">
            <h4 className="text-[10px] font-bold text-[#888] uppercase tracking-wider mb-2">Result</h4>
            <pre className="text-[9px] text-[#aaa] overflow-auto max-h-40 whitespace-pre-wrap">
              {JSON.stringify(result, null, 2)}
            </pre>
          </div>
        )}
      </div>
    </div>
  );
};

export default GPUBatchRenderingPanel;