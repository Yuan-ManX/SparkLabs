"use client";
import React, { useState, useEffect, useCallback } from 'react';
import { API_BASE as API_ROOT } from '../utils/api';

const API_BASE = API_ROOT + '/engine';

const SERIALIZE_FORMATS = ['json', 'yaml', 'binary', 'msgpack'];
const SCENE_LAYERS = ['background', 'terrain', 'props', 'characters', 'lighting', 'effects', 'ui', 'audio', 'triggers', 'debug'];

export default function EngineSceneSerializerPanel() {
  const [activeTab, setActiveTab] = useState('overview');
  const [stats, setStats] = useState<any>({});
  const [message, setMessage] = useState('');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<any>(null);
  const [scenes, setScenes] = useState<any[]>([]);

  // Create scene form
  const [sceneName, setSceneName] = useState('');
  const [sceneEntities, setSceneEntities] = useState('');
  const [sceneLayers, setSceneLayers] = useState('');
  const [sceneSettings, setSceneSettings] = useState('');
  const [sceneMetadata, setSceneMetadata] = useState('');
  const [sceneAssetRefs, setSceneAssetRefs] = useState('');
  const [selectedLayers, setSelectedLayers] = useState<string[]>([]);

  // Serialize form
  const [serSceneId, setSerSceneId] = useState('');
  const [serFormat, setSerFormat] = useState('json');
  const [serIncludeMeta, setSerIncludeMeta] = useState(true);

  // Deserialize form
  const [deserData, setDeserData] = useState('');
  const [deserName, setDeserName] = useState('');

  // Diff form
  const [diffSourceId, setDiffSourceId] = useState('');
  const [diffTargetId, setDiffTargetId] = useState('');

  // Savepoint form
  const [svSceneId, setSvSceneId] = useState('');
  const [svLabel, setSvLabel] = useState('');
  const [svDescription, setSvDescription] = useState('');

  const tabs = ['overview', 'create-scene', 'serialize', 'deserialize', 'diff', 'savepoint', 'scenes'];

  const fetchStats = useCallback(async () => {
    try { const r = await fetch(`${API_BASE}/scene-serializer/stats`); if (r.ok) setStats(await r.json()); } catch (e) {}
  }, []);

  const fetchScenes = useCallback(async () => {
    try { const r = await fetch(`${API_BASE}/scene-serializer/scenes`); if (r.ok) setScenes(await r.json()); } catch (e) {}
  }, []);

  useEffect(() => {
    fetchStats();
    fetchScenes();
    const i = setInterval(() => { fetchStats(); fetchScenes(); }, 15000);
    return () => clearInterval(i);
  }, [fetchStats, fetchScenes]);

  const handlePost = async (url: string, body: any) => {
    setLoading(true); setMessage('');
    try {
      const r = await fetch(url, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });
      const data = await r.json();
      setResult(data);
      setMessage(r.ok ? 'Success' : data.message || data.detail || data.error || 'Failed');
      fetchStats();
      fetchScenes();
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
      fetchScenes();
    } catch (e: any) { setMessage(e.message); }
    finally { setLoading(false); }
  };

  const toggleLayer = (layer: string) => {
    setSelectedLayers(prev => prev.includes(layer) ? prev.filter(l => l !== layer) : [...prev, layer]);
  };

  const inputCls = 'w-full bg-[#1a1a2e] border border-[#2a2a4a] rounded px-3 py-2 text-sm text-white placeholder-gray-500 outline-none focus:border-[#00d4ff]';
  const selectCls = 'w-full bg-[#1a1a2e] border border-[#2a2a4a] rounded px-3 py-2 text-sm text-white outline-none focus:border-[#00d4ff]';
  const cardCls = 'bg-[#0f0f23] p-4 rounded border border-[#2a2a4a]';
  const btnPrimary = 'bg-[#00d4ff] text-black px-4 py-2 rounded text-sm font-medium hover:bg-[#00b8e0] disabled:opacity-50 transition-colors';
  const btnSuccess = 'bg-[#00ff88] text-black px-4 py-2 rounded text-sm font-medium hover:bg-[#00e67a] disabled:opacity-50 transition-colors';
  const btnWarning = 'bg-amber-500 text-black px-4 py-2 rounded text-sm font-medium hover:bg-amber-600 disabled:opacity-50 transition-colors';

  const buildCreateBody = () => {
    const body: any = { name: sceneName };
    if (sceneEntities) { try { body.entities = JSON.parse(sceneEntities); } catch {} }
    if (sceneSettings) { try { body.settings = JSON.parse(sceneSettings); } catch {} }
    if (sceneMetadata) { try { body.metadata = JSON.parse(sceneMetadata); } catch {} }
    if (sceneAssetRefs) { try { body.asset_references = JSON.parse(sceneAssetRefs); } catch {} }
    // Prefer layer checkboxes; fall back to text input
    const layers = selectedLayers.length > 0 ? selectedLayers : (sceneLayers ? sceneLayers.split(',').map(s => s.trim()).filter(Boolean) : undefined);
    if (layers) body.layers = layers;
    return body;
  };

  return (
    <div className="h-full flex flex-col bg-[#1a1a2e] text-white">
      <div className="flex gap-1 p-3 border-b border-[#2a2a4a] flex-wrap">
        {tabs.map(t => (
          <button key={t} onClick={() => setActiveTab(t)}
            className={`px-4 py-2 rounded text-sm font-medium transition-colors ${activeTab === t ? 'bg-[#00d4ff] text-black' : 'bg-[#0f0f23] text-[#ccc] hover:bg-[#2a2a4a]'}`}>
            {t.split('-').map(w => w.charAt(0).toUpperCase() + w.slice(1)).join(' ')}
          </button>
        ))}
      </div>

      {message && (
        <div className="mx-4 mt-2 p-2 rounded text-sm border bg-[#0f0f23] border-[#00ff88] text-[#00ff88]">{message}</div>
      )}

      <div className="flex-1 overflow-auto p-4">

        {/* OVERVIEW TAB */}
        {activeTab === 'overview' && (
          <div className="space-y-4">
            <h2 className="text-lg font-bold text-[#00d4ff]">Scene Serializer Overview</h2>
            <div className="grid grid-cols-4 gap-4">
              {[
                { label: 'Total Scenes', value: stats.total_scenes, color: 'text-[#00d4ff]' },
                { label: 'Total Savepoints', value: stats.total_savepoints, color: 'text-[#00ff88]' },
                { label: 'Serializations', value: stats.total_serializations, color: 'text-amber-300' },
                { label: 'Deserializations', value: stats.total_deserializations, color: 'text-purple-300' },
              ].map(s => (
                <div key={s.label} className="bg-[#0f0f23] p-4 rounded border border-[#2a2a4a]">
                  <h3 className="text-xs text-[#999]">{s.label}</h3>
                  <p className={`text-2xl font-bold ${s.color}`}>{s.value ?? 0}</p>
                </div>
              ))}
            </div>
            {stats.scene_count !== undefined && (
              <div className="grid grid-cols-4 gap-4">
                {[
                  { label: 'Active Scenes', value: stats.active_scenes, color: 'text-[#00d4ff]' },
                  { label: 'Archived Scenes', value: stats.archived_scenes, color: 'text-[#999]' },
                  { label: 'Avg Scene Size', value: stats.avg_scene_size, color: 'text-amber-300', suffix: ' KB' },
                  { label: 'Total Diffs', value: stats.total_diffs, color: 'text-pink-300' },
                ].map(s => (
                  <div key={s.label} className="bg-[#0f0f23] p-4 rounded border border-[#2a2a4a]">
                    <h3 className="text-xs text-[#999]">{s.label}</h3>
                    <p className={`text-2xl font-bold ${s.color}`}>{s.value ?? 0}{s.suffix || ''}</p>
                  </div>
                ))}
              </div>
            )}
            {stats.by_format && (
              <div className={cardCls}>
                <h3 className="text-sm font-bold text-[#ccc] mb-2">By Format</h3>
                <div className="space-y-1">
                  {Object.entries(stats.by_format).map(([k, v]) => (
                    <div key={k} className="flex justify-between text-xs"><span className="text-[#999] uppercase">{k}</span><span className="text-[#00d4ff]">{v as any}</span></div>
                  ))}
                </div>
              </div>
            )}
            {stats.recent_activity && Array.isArray(stats.recent_activity) && (
              <div className={cardCls}>
                <h3 className="text-sm font-bold text-[#ccc] mb-2">Recent Activity</h3>
                <div className="space-y-1">
                  {stats.recent_activity.map((act: any, i: number) => (
                    <div key={i} className="flex justify-between text-xs">
                      <span className="text-[#999]">{act.action ?? act.type}</span>
                      <span className="text-[#00d4ff]">{act.scene_name ?? act.scene_id ?? '—'}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

        {/* CREATE SCENE TAB */}
        {activeTab === 'create-scene' && (
          <div className="space-y-4">
            <h2 className="text-lg font-bold text-[#00d4ff]">Create Scene</h2>
            <div className={cardCls + ' space-y-3'}>
              <input className={inputCls} placeholder="Scene Name" value={sceneName} onChange={e => setSceneName(e.target.value)} />
              <div>
                <label className="text-xs text-[#999] mb-1 block">Layers</label>
                <div className="flex flex-wrap gap-2 mb-2">
                  {SCENE_LAYERS.map(l => (
                    <label key={l} className={`flex items-center gap-1 px-3 py-1 rounded text-xs cursor-pointer border transition-colors ${selectedLayers.includes(l) ? 'bg-[#00d4ff]/20 border-[#00d4ff] text-[#00d4ff]' : 'bg-[#1a1a2e] border-[#2a2a4a] text-[#999] hover:border-[#00d4ff]/50'}`}>
                      <input type="checkbox" checked={selectedLayers.includes(l)} onChange={() => toggleLayer(l)} className="sr-only" />
                      {l.charAt(0).toUpperCase() + l.slice(1)}
                    </label>
                  ))}
                </div>
                <input className={inputCls} placeholder="Or enter layers (comma-separated)" value={sceneLayers} onChange={e => setSceneLayers(e.target.value)} />
              </div>
              <textarea className={inputCls + ' resize-none'} rows={3} placeholder="Entities (JSON array)" value={sceneEntities} onChange={e => setSceneEntities(e.target.value)} />
              <textarea className={inputCls + ' resize-none'} rows={2} placeholder="Settings (JSON)" value={sceneSettings} onChange={e => setSceneSettings(e.target.value)} />
              <textarea className={inputCls + ' resize-none'} rows={2} placeholder="Metadata (JSON)" value={sceneMetadata} onChange={e => setSceneMetadata(e.target.value)} />
              <textarea className={inputCls + ' resize-none'} rows={2} placeholder="Asset References (JSON)" value={sceneAssetRefs} onChange={e => setSceneAssetRefs(e.target.value)} />
              <button
                className={`w-full ${btnPrimary}`}
                disabled={loading}
                onClick={() => handlePost(`${API_BASE}/scene-serializer/create-scene`, buildCreateBody())}>
                {loading ? 'Creating...' : 'Create Scene'}
              </button>
            </div>
            {result && activeTab === 'create-scene' && result.scene_id && (
              <div className={`${cardCls} border-l-4 border-[#00d4ff]`}>
                <div className="flex justify-between items-center">
                  <h3 className="text-sm font-bold text-white">{result.name ?? sceneName}</h3>
                  <span className="text-xs px-2 py-0.5 bg-[#1a1a2e] rounded border border-[#2a2a4a] text-[#00d4ff] font-mono">{result.scene_id}</span>
                </div>
                {result.layers && (
                  <div className="flex gap-1 mt-2 flex-wrap">
                    {result.layers.map((l: string, i: number) => (
                      <span key={i} className="text-[10px] px-2 py-0.5 bg-[#1a1a2e] rounded border border-[#2a2a4a] text-[#999] capitalize">{l}</span>
                    ))}
                  </div>
                )}
              </div>
            )}
          </div>
        )}

        {/* SERIALIZE TAB */}
        {activeTab === 'serialize' && (
          <div className="space-y-4">
            <h2 className="text-lg font-bold text-[#00ff88]">Serialize Scene</h2>
            <div className={cardCls + ' space-y-3'}>
              <input className={inputCls} placeholder="Scene ID" value={serSceneId} onChange={e => setSerSceneId(e.target.value)} />
              <select className={selectCls} value={serFormat} onChange={e => setSerFormat(e.target.value)}>
                {SERIALIZE_FORMATS.map(f => <option key={f} value={f}>{f.toUpperCase()}</option>)}
              </select>
              <label className="flex items-center gap-2 text-sm text-[#999] cursor-pointer">
                <input type="checkbox" checked={serIncludeMeta} onChange={e => setSerIncludeMeta(e.target.checked)} className="accent-[#00d4ff]" />
                Include Metadata
              </label>
              <button
                className={`w-full ${btnSuccess}`}
                disabled={loading}
                onClick={() => handlePost(`${API_BASE}/scene-serializer/serialize`, {
                  scene_id: serSceneId, format: serFormat, include_metadata: serIncludeMeta,
                })}>
                {loading ? 'Serializing...' : 'Serialize Scene'}
              </button>
            </div>
            {result && activeTab === 'serialize' && result.data !== undefined && (
              <div className={cardCls}>
                <h3 className="text-sm font-bold text-[#00ff88] mb-2">Serialized Output</h3>
                <div className="flex gap-4 mb-2 text-xs text-[#999]">
                  <span>Format: <span className="text-white uppercase">{result.format ?? serFormat}</span></span>
                  <span>Size: <span className="text-white">{result.size ?? 'N/A'}</span></span>
                </div>
                <pre className="bg-[#1a1a2e] p-3 rounded border border-[#2a2a4a] text-xs text-[#ccc] overflow-auto max-h-64 font-mono whitespace-pre-wrap">
                  {typeof result.data === 'string' ? result.data : JSON.stringify(result.data, null, 2)}
                </pre>
              </div>
            )}
          </div>
        )}

        {/* DESERIALIZE TAB */}
        {activeTab === 'deserialize' && (
          <div className="space-y-4">
            <h2 className="text-lg font-bold text-purple-300">Deserialize Scene</h2>
            <div className={cardCls + ' space-y-3'}>
              <textarea className={inputCls + ' resize-none'} rows={6} placeholder="Serialized Data (JSON string or object)" value={deserData} onChange={e => setDeserData(e.target.value)} />
              <input className={inputCls} placeholder="Scene Name" value={deserName} onChange={e => setDeserName(e.target.value)} />
              <button
                className={`w-full px-4 py-2 bg-purple-500 text-white rounded text-sm font-medium hover:bg-purple-600 transition-colors disabled:opacity-50`}
                disabled={loading}
                onClick={() => {
                  let parsed = deserData;
                  try { parsed = JSON.parse(deserData); } catch {}
                  handlePost(`${API_BASE}/scene-serializer/deserialize`, {
                    data: parsed, scene_name: deserName,
                  });
                }}>
                {loading ? 'Deserializing...' : 'Deserialize'}
              </button>
            </div>
            {result && activeTab === 'deserialize' && result.scene_id && (
              <div className={`${cardCls} border-l-4 border-purple-500`}>
                <div className="flex justify-between items-center">
                  <h3 className="text-sm font-bold text-white">{result.scene_name ?? deserName}</h3>
                  <span className="text-xs px-2 py-0.5 bg-[#1a1a2e] rounded border border-[#2a2a4a] text-purple-300 font-mono">{result.scene_id}</span>
                </div>
                {result.layers && (
                  <div className="flex gap-1 mt-2 flex-wrap">
                    {result.layers.map((l: string, i: number) => (
                      <span key={i} className="text-[10px] px-2 py-0.5 bg-[#1a1a2e] rounded border border-[#2a2a4a] text-[#999] capitalize">{l}</span>
                    ))}
                  </div>
                )}
              </div>
            )}
          </div>
        )}

        {/* DIFF TAB */}
        {activeTab === 'diff' && (
          <div className="space-y-4">
            <h2 className="text-lg font-bold text-amber-300">Diff Scenes</h2>
            <div className={cardCls + ' space-y-3'}>
              <div className="grid grid-cols-2 gap-3">
                <input className={inputCls} placeholder="Source Scene ID" value={diffSourceId} onChange={e => setDiffSourceId(e.target.value)} />
                <input className={inputCls} placeholder="Target Scene ID" value={diffTargetId} onChange={e => setDiffTargetId(e.target.value)} />
              </div>
              <button
                className={`w-full ${btnWarning}`}
                disabled={loading}
                onClick={() => handlePost(`${API_BASE}/scene-serializer/diff`, {
                  source_scene_id: diffSourceId, target_scene_id: diffTargetId,
                })}>
                {loading ? 'Computing Diff...' : 'Compute Diff'}
              </button>
            </div>
            {result && activeTab === 'diff' && (
              <div className={cardCls}>
                <h3 className="text-sm font-bold text-amber-300 mb-2">Diff Result</h3>
                {result.changes !== undefined && (
                  <div className="flex gap-4 mb-2 text-xs">
                    <span className="text-[#00ff88]">+{result.additions ?? 0} additions</span>
                    <span className="text-red-400">-{result.removals ?? 0} removals</span>
                    <span className="text-amber-300">~{result.modifications ?? 0} modifications</span>
                  </div>
                )}
                {result.diff && (
                  <pre className="bg-[#1a1a2e] p-3 rounded border border-[#2a2a4a] text-xs font-mono overflow-auto max-h-64 whitespace-pre-wrap">
                    {typeof result.diff === 'string' ? result.diff : JSON.stringify(result.diff, null, 2)}
                  </pre>
                )}
                {result.changes && Array.isArray(result.changes) && (
                  <div className="space-y-1 mt-2">
                    {result.changes.map((ch: any, i: number) => (
                      <div key={i} className="flex items-center gap-2 text-xs py-1 border-b border-[#2a2a4a]/50">
                        <span className={`w-12 px-1 py-0.5 rounded text-center text-[10px] font-medium ${ch.type === 'added' ? 'bg-[#00ff88]/20 text-[#00ff88]' : ch.type === 'removed' ? 'bg-red-500/20 text-red-400' : 'bg-amber-500/20 text-amber-400'}`}>
                          {ch.type ?? ch.op}
                        </span>
                        <span className="text-[#999]">{ch.path ?? ch.key}</span>
                        {ch.value !== undefined && <span className="text-[#ccc] font-mono">{JSON.stringify(ch.value)}</span>}
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}
          </div>
        )}

        {/* SAVEPOINT TAB */}
        {activeTab === 'savepoint' && (
          <div className="space-y-4">
            <h2 className="text-lg font-bold text-pink-300">Create Savepoint</h2>
            <div className={cardCls + ' space-y-3'}>
              <input className={inputCls} placeholder="Scene ID" value={svSceneId} onChange={e => setSvSceneId(e.target.value)} />
              <input className={inputCls} placeholder="Savepoint Label" value={svLabel} onChange={e => setSvLabel(e.target.value)} />
              <textarea className={inputCls + ' resize-none'} rows={3} placeholder="Description" value={svDescription} onChange={e => setSvDescription(e.target.value)} />
              <button
                className={`w-full px-4 py-2 bg-pink-500 text-white rounded text-sm font-medium hover:bg-pink-600 transition-colors disabled:opacity-50`}
                disabled={loading}
                onClick={() => handlePost(`${API_BASE}/scene-serializer/create-savepoint`, {
                  scene_id: svSceneId, label: svLabel, description: svDescription,
                })}>
                {loading ? 'Creating Savepoint...' : 'Create Savepoint'}
              </button>
            </div>
            {result && activeTab === 'savepoint' && (result.savepoint_id || result.timestamp) && (
              <div className={`${cardCls} border-l-4 border-pink-500`}>
                <div className="flex justify-between items-center">
                  <h3 className="text-sm font-bold text-white">{result.label ?? svLabel}</h3>
                  <span className="text-xs px-2 py-0.5 bg-[#1a1a2e] rounded border border-[#2a2a4a] text-pink-300 font-mono">{result.savepoint_id ?? result.timestamp}</span>
                </div>
                {result.description && <p className="text-xs text-[#999] mt-1">{result.description}</p>}
                <div className="flex gap-3 mt-2 text-[10px] text-[#666]">
                  {result.scene_id && <span>Scene: {result.scene_id}</span>}
                  {result.created_at && <span>Created: {result.created_at}</span>}
                </div>
              </div>
            )}
          </div>
        )}

        {/* SCENES TAB */}
        {activeTab === 'scenes' && (
          <div className="space-y-4">
            <div className="flex justify-between items-center">
              <h2 className="text-lg font-bold text-[#00d4ff]">All Scenes</h2>
              <button
                className="px-3 py-1.5 bg-[#0f0f23] border border-[#2a2a4a] rounded text-xs text-[#ccc] hover:border-[#00d4ff] transition-colors"
                onClick={() => handleGet(`${API_BASE}/scene-serializer/scenes`)}>
                Refresh
              </button>
            </div>
            {scenes && Array.isArray(scenes) && scenes.length > 0 ? (
              <div className="space-y-2">
                {scenes.map((scene: any, i: number) => (
                  <div key={i} className={cardCls + ' flex justify-between items-start'}>
                    <div>
                      <h3 className="text-sm font-bold text-white">{scene.name ?? 'Unnamed Scene'}</h3>
                      <div className="flex gap-2 mt-1 text-[10px] text-[#666]">
                        <span className="text-[#00d4ff] font-mono">{scene.scene_id ?? scene.id}</span>
                        {scene.entity_count !== undefined && <span>{scene.entity_count} entities</span>}
                        {scene.savepoint_count !== undefined && <span>{scene.savepoint_count} savepoints</span>}
                        {scene.size && <span>{scene.size}</span>}
                      </div>
                      {scene.layers && Array.isArray(scene.layers) && (
                        <div className="flex gap-1 mt-2 flex-wrap">
                          {scene.layers.map((l: string, j: number) => (
                            <span key={j} className="text-[10px] px-2 py-0.5 bg-[#1a1a2e] rounded border border-[#2a2a4a] text-[#999] capitalize">{l}</span>
                          ))}
                        </div>
                      )}
                    </div>
                    <div className="flex flex-col items-end gap-1">
                      {scene.created_at && <span className="text-[10px] text-[#666]">{scene.created_at}</span>}
                      {scene.status && (
                        <span className={`text-[10px] px-2 py-0.5 rounded border ${scene.status === 'active' ? 'text-[#00ff88] border-[#00ff88]/30' : 'text-[#999] border-[#2a2a4a]'} capitalize`}>
                          {scene.status}
                        </span>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className={cardCls}>
                <p className="text-sm text-[#666] text-center py-8">No scenes found. Click Refresh or create a scene first.</p>
              </div>
            )}
          </div>
        )}

      </div>
    </div>
  );
}