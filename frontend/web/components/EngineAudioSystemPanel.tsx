"use client";
import React, { useState, useEffect, useCallback } from 'react';
import { API_BASE as API_ROOT } from '../utils/api';

const API_BASE = API_ROOT + '/engine';

const AUDIO_CATEGORIES = ['sfx', 'music', 'ambient', 'voice', 'ui', 'footstep', 'weapon', 'environment', 'vehicle', 'magic'];
const PRIORITIES = ['low', 'medium', 'high', 'critical', 'always'];
const PLAYBACK_MODES = ['once', 'loop', 'ping_pong', 'random', 'sequential'];

export default function EngineAudioSystemPanel() {
  const [activeTab, setActiveTab] = useState('overview');
  const [stats, setStats] = useState<any>({});
  const [message, setMessage] = useState('');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<any>(null);

  // Load asset form
  const [assetName, setAssetName] = useState('');
  const [assetCategory, setAssetCategory] = useState('sfx');
  const [assetFilePath, setAssetFilePath] = useState('');
  const [assetDuration, setAssetDuration] = useState('3.0');
  const [assetVolume, setAssetVolume] = useState('1.0');
  const [assetPitch, setAssetPitch] = useState('1.0');
  const [assetPriority, setAssetPriority] = useState('medium');
  const [assetPlaybackMode, setAssetPlaybackMode] = useState('once');
  const [assetIs3d, setAssetIs3d] = useState(false);
  const [assetTags, setAssetTags] = useState('');

  // Play audio form
  const [playAssetId, setPlayAssetId] = useState('');
  const [playVolume, setPlayVolume] = useState('1.0');
  const [playPitch, setPlayPitch] = useState('1.0');
  const [playLoop, setPlayLoop] = useState(false);

  // Random playback form
  const [randCategory, setRandCategory] = useState('sfx');
  const [randVolume, setRandVolume] = useState('1.0');

  // Stop audio form
  const [stopInstanceId, setStopInstanceId] = useState('');

  // Channel form
  const [chName, setChName] = useState('');
  const [chCategory, setChCategory] = useState('sfx');
  const [chVolume, setChVolume] = useState('1.0');

  const tabs = ['overview', 'assets', 'playback', 'channels'];

  const fetchStats = useCallback(async () => {
    try { const r = await fetch(`${API_BASE}/audio-system/stats`); if (r.ok) setStats(await r.json()); } catch (e) {}
  }, []);

  useEffect(() => { fetchStats(); const i = setInterval(fetchStats, 15000); return () => clearInterval(i); }, [fetchStats]);

  const handlePost = async (url: string, body: any) => {
    setLoading(true); setMessage('');
    try {
      const r = await fetch(url, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });
      const data = await r.json();
      setResult(data);
      setMessage(r.ok ? 'Success' : data.message || data.error || 'Failed');
      fetchStats();
    } catch (e: any) { setMessage(e.message); }
    finally { setLoading(false); }
  };

  const handleGet = async (url: string) => {
    setLoading(true); setMessage('');
    try {
      const r = await fetch(url);
      const data = await r.json();
      setResult(data);
      setMessage(r.ok ? 'Success' : data.message || 'Failed');
      fetchStats();
    } catch (e: any) { setMessage(e.message); }
    finally { setLoading(false); }
  };

  const inputCls = 'w-full bg-[#1a1a2e] border border-[#2a2a4a] rounded px-3 py-2 text-sm text-white placeholder-gray-500 outline-none focus:border-[#00d4ff]';
  const selectCls = 'w-full bg-[#1a1a2e] border border-[#2a2a4a] rounded px-3 py-2 text-sm text-white outline-none focus:border-[#00d4ff]';
  const cardCls = 'bg-[#0d0d0d] p-4 rounded border border-[#2a2a4a]';

  return (
    <div className="h-full flex flex-col bg-[#1a1a2e] text-white">
      <div className="flex gap-1 p-3 border-b border-[#2a2a4a]">
        {tabs.map(t => (
          <button key={t} onClick={() => setActiveTab(t)}
            className={`px-4 py-2 rounded text-sm font-medium transition-colors ${activeTab === t ? 'bg-[#00d4ff] text-black' : 'bg-[#0d0d0d] text-[#ccc] hover:bg-[#2a2a4a]'}`}>
            {t.charAt(0).toUpperCase() + t.slice(1)}
          </button>
        ))}
      </div>

      {message && (
        <div className="mx-4 mt-2 p-2 rounded text-sm border bg-[#0d0d0d] border-[#00ff88] text-[#00ff88]">{message}</div>
      )}

      <div className="flex-1 overflow-auto p-4">

        {/* OVERVIEW TAB */}
        {activeTab === 'overview' && (
          <div className="space-y-4">
            <h2 className="text-lg font-bold text-[#00d4ff]">Audio System Overview</h2>
            <div className="grid grid-cols-4 gap-4">
              {[
                { label: 'Total Assets', value: stats.total_assets, color: 'text-[#00d4ff]' },
                { label: 'Active Instances', value: stats.active_instances, color: 'text-[#00ff88]' },
                { label: 'Total Channels', value: stats.total_channels, color: 'text-amber-300' },
                { label: 'Categories', value: stats.categories ? Object.keys(stats.categories).length : 0, color: 'text-pink-300', suffix: ' categories' },
              ].map(s => (
                <div key={s.label} className="bg-[#0d0d0d] p-4 rounded border border-[#2a2a4a]">
                  <h3 className="text-xs text-[#999]">{s.label}</h3>
                  <p className={`text-2xl font-bold ${s.color}`}>{s.value ?? 0}{s.suffix || ''}</p>
                </div>
              ))}
            </div>
            {stats.categories && (
              <div className={cardCls}>
                <h3 className="text-sm font-bold text-[#ccc] mb-2">Assets by Category</h3>
                <div className="grid grid-cols-3 gap-2">
                  {Object.entries(stats.categories).map(([k, v]) => (
                    <div key={k} className="flex justify-between text-xs"><span className="text-[#999] capitalize">{k}</span><span className="text-[#00d4ff]">{v as any}</span></div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

        {/* ASSETS TAB */}
        {activeTab === 'assets' && (
          <div className="space-y-4">
            <h2 className="text-lg font-bold text-[#00d4ff]">Load Audio Asset</h2>
            <div className={cardCls + ' space-y-3'}>
              <input className={inputCls} placeholder="Asset Name" value={assetName} onChange={e => setAssetName(e.target.value)} />
              <div className="grid grid-cols-2 gap-3">
                <select className={selectCls} value={assetCategory} onChange={e => setAssetCategory(e.target.value)}>
                  {AUDIO_CATEGORIES.map(c => <option key={c} value={c}>{c.charAt(0).toUpperCase() + c.slice(1)}</option>)}
                </select>
                <input className={inputCls} placeholder="File Path" value={assetFilePath} onChange={e => setAssetFilePath(e.target.value)} />
              </div>
              <div className="grid grid-cols-3 gap-3">
                <input className={inputCls} placeholder="Duration (s)" type="number" step="0.1" value={assetDuration} onChange={e => setAssetDuration(e.target.value)} />
                <input className={inputCls} placeholder="Volume (0-1)" type="number" step="0.1" min="0" max="1" value={assetVolume} onChange={e => setAssetVolume(e.target.value)} />
                <input className={inputCls} placeholder="Pitch" type="number" step="0.1" value={assetPitch} onChange={e => setAssetPitch(e.target.value)} />
              </div>
              <div className="grid grid-cols-2 gap-3">
                <select className={selectCls} value={assetPriority} onChange={e => setAssetPriority(e.target.value)}>
                  {PRIORITIES.map(p => <option key={p} value={p}>{p.charAt(0).toUpperCase() + p.slice(1)}</option>)}
                </select>
                <select className={selectCls} value={assetPlaybackMode} onChange={e => setAssetPlaybackMode(e.target.value)}>
                  {PLAYBACK_MODES.map(m => <option key={m} value={m}>{m.replace('_', ' ').replace(/\b\w/g, l => l.toUpperCase())}</option>)}
                </select>
              </div>
              <div className="flex items-center gap-2">
                <label className="flex items-center gap-2 text-sm text-[#999] cursor-pointer">
                  <input type="checkbox" checked={assetIs3d} onChange={e => setAssetIs3d(e.target.checked)} className="accent-[#00d4ff]" />
                  3D Audio
                </label>
              </div>
              <input className={inputCls} placeholder="Tags (comma-separated)" value={assetTags} onChange={e => setAssetTags(e.target.value)} />
              <button
                className="w-full px-4 py-2 bg-[#00d4ff] text-black rounded text-sm font-medium hover:bg-[#00b8e6] transition-colors disabled:opacity-50"
                disabled={loading}
                onClick={() => handlePost(`${API_BASE}/audio-system/load-asset`, {
                  name: assetName, category: assetCategory, file_path: assetFilePath,
                  duration: parseFloat(assetDuration), volume: parseFloat(assetVolume),
                  pitch: parseFloat(assetPitch), priority: assetPriority,
                  playback_mode: assetPlaybackMode, is_3d: assetIs3d, tags: assetTags,
                })}>
                {loading ? 'Loading...' : 'Load Asset'}
              </button>
            </div>
          </div>
        )}

        {/* PLAYBACK TAB */}
        {activeTab === 'playback' && (
          <div className="space-y-6">
            <h2 className="text-lg font-bold text-[#00ff88]">Play Audio</h2>
            <div className={cardCls + ' space-y-3'}>
              <input className={inputCls} placeholder="Asset ID" value={playAssetId} onChange={e => setPlayAssetId(e.target.value)} />
              <div className="grid grid-cols-3 gap-3">
                <input className={inputCls} placeholder="Volume (0-1)" type="number" step="0.1" min="0" max="1" value={playVolume} onChange={e => setPlayVolume(e.target.value)} />
                <input className={inputCls} placeholder="Pitch" type="number" step="0.1" value={playPitch} onChange={e => setPlayPitch(e.target.value)} />
                <div className="flex items-center">
                  <label className="flex items-center gap-2 text-sm text-[#999] cursor-pointer">
                    <input type="checkbox" checked={playLoop} onChange={e => setPlayLoop(e.target.checked)} className="accent-[#00ff88]" />
                    Loop
                  </label>
                </div>
              </div>
              <button
                className="w-full px-4 py-2 bg-[#00ff88] text-black rounded text-sm font-medium hover:bg-[#00cc6a] transition-colors disabled:opacity-50"
                disabled={loading}
                onClick={() => handlePost(`${API_BASE}/audio-system/play`, {
                  asset_id: playAssetId, volume: parseFloat(playVolume), pitch: parseFloat(playPitch), loop: playLoop,
                })}>
                {loading ? 'Playing...' : 'Play Audio'}
              </button>
            </div>

            <h2 className="text-lg font-bold text-amber-300">Play Random from Category</h2>
            <div className={cardCls + ' space-y-3'}>
              <div className="grid grid-cols-2 gap-3">
                <select className={selectCls} value={randCategory} onChange={e => setRandCategory(e.target.value)}>
                  {AUDIO_CATEGORIES.map(c => <option key={c} value={c}>{c.charAt(0).toUpperCase() + c.slice(1)}</option>)}
                </select>
                <input className={inputCls} placeholder="Volume (0-1)" type="number" step="0.1" min="0" max="1" value={randVolume} onChange={e => setRandVolume(e.target.value)} />
              </div>
              <button
                className="w-full px-4 py-2 bg-amber-500 text-black rounded text-sm font-medium hover:bg-amber-600 transition-colors disabled:opacity-50"
                disabled={loading}
                onClick={() => handlePost(`${API_BASE}/audio-system/random`, {
                  category: randCategory, volume: parseFloat(randVolume),
                })}>
                {loading ? 'Playing...' : 'Play Random'}
              </button>
            </div>

            <h2 className="text-lg font-bold text-red-400">Stop Audio</h2>
            <div className={cardCls + ' space-y-3'}>
              <input className={inputCls} placeholder="Instance ID" value={stopInstanceId} onChange={e => setStopInstanceId(e.target.value)} />
              <button
                className="w-full px-4 py-2 bg-red-500 text-white rounded text-sm font-medium hover:bg-red-600 transition-colors disabled:opacity-50"
                disabled={loading}
                onClick={() => handlePost(`${API_BASE}/audio-system/stop`, { instance_id: stopInstanceId })}>
                {loading ? 'Stopping...' : 'Stop Audio'}
              </button>
            </div>

            <div className={cardCls}>
              <h3 className="text-sm font-bold text-[#ccc] mb-3">Active Instances</h3>
              <button
                className="px-4 py-2 bg-[#00d4ff] text-black rounded text-sm font-medium hover:bg-[#00b8e6] transition-colors disabled:opacity-50"
                disabled={loading}
                onClick={() => handleGet(`${API_BASE}/audio-system/active`)}>
                {loading ? 'Loading...' : 'Refresh Active Instances'}
              </button>
              {result && activeTab === 'playback' && Array.isArray(result.instances) && (
                <div className="mt-3 space-y-2">
                  {result.instances.map((inst: any, i: number) => (
                    <div key={i} className="bg-[#1a1a2e] p-2 rounded border border-[#2a2a4a] flex justify-between items-center text-xs">
                      <span className="text-white">{inst.asset_name ?? inst.id}</span>
                      <div className="flex gap-2">
                        <span className="text-[#666]">Vol: {inst.volume}</span>
                        <span className="text-[#666]">{inst.loop ? '🔁' : '▶'}</span>
                        <span className="text-[#00ff88]">{inst.state ?? 'playing'}</span>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        )}

        {/* CHANNELS TAB */}
        {activeTab === 'channels' && (
          <div className="space-y-4">
            <h2 className="text-lg font-bold text-purple-300">Create Channel</h2>
            <div className={cardCls + ' space-y-3'}>
              <input className={inputCls} placeholder="Channel Name" value={chName} onChange={e => setChName(e.target.value)} />
              <div className="grid grid-cols-2 gap-3">
                <select className={selectCls} value={chCategory} onChange={e => setChCategory(e.target.value)}>
                  {AUDIO_CATEGORIES.map(c => <option key={c} value={c}>{c.charAt(0).toUpperCase() + c.slice(1)}</option>)}
                </select>
                <input className={inputCls} placeholder="Volume (0-1)" type="number" step="0.1" min="0" max="1" value={chVolume} onChange={e => setChVolume(e.target.value)} />
              </div>
              <button
                className="w-full px-4 py-2 bg-orange-500 text-white rounded text-sm font-medium hover:bg-orange-600 transition-colors disabled:opacity-50"
                disabled={loading}
                onClick={() => handlePost(`${API_BASE}/audio-system/create-channel`, {
                  name: chName, category: chCategory, volume: parseFloat(chVolume),
                })}>
                {loading ? 'Creating...' : 'Create Channel'}
              </button>
            </div>

            {result && activeTab === 'channels' && Array.isArray(result.channels) && (
              <div className={cardCls}>
                <h3 className="text-sm font-bold text-[#ccc] mb-3">Channel List</h3>
                <div className="space-y-2">
                  {result.channels.map((ch: any, i: number) => (
                    <div key={i} className="bg-[#1a1a2e] p-3 rounded border border-[#2a2a4a] flex justify-between items-center">
                      <div>
                        <span className="text-sm text-white">{ch.name}</span>
                        <span className="text-xs text-[#666] ml-2 capitalize">{ch.category}</span>
                      </div>
                      <div className="flex items-center gap-3">
                        <div className="flex items-center gap-1">
                          <span className="text-xs text-[#666]">Vol:</span>
                          <div className="w-16 bg-[#2a2a4a] rounded-full h-1.5 overflow-hidden">
                            <div className="h-full bg-purple-400 rounded-full" style={{ width: `${(ch.volume ?? 1) * 100}%` }} />
                          </div>
                        </div>
                        <span className="text-xs text-purple-300">{ch.volume?.toFixed(1) ?? '1.0'}</span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

      </div>
    </div>
  );
}