"use client";
import React, { useState, useEffect, useCallback } from 'react';
import { API_BASE as API_ROOT } from '../utils/api';

const API_BASE = API_ROOT + '/agent';

export default function AgentContentForgePanel() {
  const [activeTab, setActiveTab] = useState('overview');
  const [stats, setStats] = useState<any>({});
  const [assets, setAssets] = useState<any[]>([]);
  const [templates, setTemplates] = useState<any[]>([]);
  const [selectedAsset, setSelectedAsset] = useState<any>(null);
  const [message, setMessage] = useState('');
  const [loading, setLoading] = useState(false);

  // Generate form
  const [genContentType, setGenContentType] = useState('dialogue');
  const [genStyle, setGenStyle] = useState('neutral');
  const [genQuality, setGenQuality] = useState('high');
  const [genBatchSize, setGenBatchSize] = useState('1');
  const [genTags, setGenTags] = useState('');

  // Asset filters
  const [assetFilterType, setAssetFilterType] = useState('');
  const [assetFilterStatus, setAssetFilterStatus] = useState('');
  const [assetFilterStyle, setAssetFilterStyle] = useState('');

  // Template form
  const [tplName, setTplName] = useState('');
  const [tplContentType, setTplContentType] = useState('dialogue');
  const [tplStructure, setTplStructure] = useState('{}');

  const fetchStats = useCallback(async () => {
    try { const r = await fetch(`${API_BASE}/content-forge/stats`); if (r.ok) setStats(await r.json()); } catch (e) { console.error(e); }
  }, []);

  const fetchAssets = useCallback(async (filters?: Record<string, string>) => {
    try {
      const params = new URLSearchParams();
      if (filters) Object.entries(filters).forEach(([k, v]) => { if (v) params.append(k, v); });
      const qs = params.toString();
      const r = await fetch(`${API_BASE}/content-forge/assets${qs ? '?' + qs : ''}`);
      if (r.ok) { const d = await r.json(); setAssets(d.assets || d || []); }
    } catch (e) { console.error(e); }
  }, []);

  const fetchTemplates = useCallback(async () => {
    try { const r = await fetch(`${API_BASE}/content-forge/templates`); if (r.ok) { const d = await r.json(); setTemplates(d.templates || d || []); } } catch (e) { console.error(e); }
  }, []);

  useEffect(() => {
    fetchStats();
    fetchAssets();
    fetchTemplates();
    const i = setInterval(fetchStats, 15000);
    return () => clearInterval(i);
  }, [fetchStats, fetchAssets, fetchTemplates]);

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

  const contentTypes = ['dialogue', 'quest', 'item', 'character', 'environment', 'lore', 'tutorial'];
  const styles = ['neutral', 'dramatic', 'humorous', 'dark', 'whimsical', 'formal', 'casual'];
  const qualities = ['low', 'medium', 'high', 'premium'];
  const statuses = ['draft', 'review', 'approved', 'published', 'archived'];

  const tabs = ['overview', 'generate', 'assets', 'templates'];

  return (
    <div className="h-full flex flex-col bg-[#1a1a2e] text-white">
      <div className="flex gap-1 p-3 border-b border-[#2a2a4a]">
        {tabs.map(t => (
          <button key={t} onClick={() => setActiveTab(t)}
            className={`px-4 py-2 rounded text-sm font-medium ${activeTab === t ? 'bg-[#00d4ff] text-black' : 'bg-[#0f0f23] text-[#ccc] hover:bg-[#2a2a4a]'}`}>
            {t.charAt(0).toUpperCase() + t.slice(1)}
          </button>
        ))}
      </div>
      {message && <div className="mx-4 mt-2 p-2 bg-[#0f0f23] border border-[#2a2a4a] rounded text-sm text-[#00d4ff]">{message}</div>}
      <div className="flex-1 overflow-auto p-4">

        {/* Overview Tab */}
        {activeTab === 'overview' && (
          <div className="space-y-4">
            <h2 className="text-lg font-bold text-[#00d4ff]">Content Forge Stats</h2>
            <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
              {Object.entries(stats).filter(([k]) => k !== 'by_type' && k !== 'by_status').map(([key, value]) => (
                <div key={key} className="bg-[#0f0f23] p-4 rounded border border-[#2a2a4a]">
                  <h3 className="text-[#00d4ff] text-xs capitalize">{key.replace(/_/g, ' ')}</h3>
                  <p className="text-2xl font-bold mt-1">
                    {typeof value === 'number' ? value.toLocaleString() : String(value)}
                  </p>
                </div>
              ))}
            </div>

            {stats.by_type && (
              <div className="bg-[#0f0f23] border border-[#2a2a4a] rounded-lg p-4">
                <h3 className="text-[#00d4ff] text-sm font-medium mb-3">By Type</h3>
                <div className="space-y-2">
                  {Object.entries(stats.by_type).map(([key, value]) => (
                    <div key={key} className="flex justify-between bg-[#1a1a2e] rounded px-3 py-2">
                      <span className="text-[#999] text-xs capitalize">{key}</span>
                      <span className="text-white text-xs font-mono">{String(value)}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {stats.by_status && (
              <div className="bg-[#0f0f23] border border-[#2a2a4a] rounded-lg p-4">
                <h3 className="text-[#00d4ff] text-sm font-medium mb-3">By Status</h3>
                <div className="space-y-2">
                  {Object.entries(stats.by_status).map(([key, value]) => (
                    <div key={key} className="flex justify-between bg-[#1a1a2e] rounded px-3 py-2">
                      <span className="text-[#999] text-xs capitalize">{key}</span>
                      <span className="text-white text-xs font-mono">{String(value)}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

        {/* Generate Tab */}
        {activeTab === 'generate' && (
          <div className="space-y-4">
            <div className="bg-[#0f0f23] border border-[#2a2a4a] rounded-lg p-4">
              <h2 className="text-lg font-bold text-[#00d4ff] mb-3">Generate Content</h2>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-xs text-[#999] mb-1 block">Content Type</label>
                  <select value={genContentType} onChange={e => setGenContentType(e.target.value)}
                    className="w-full bg-[#1a1a2e] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none">
                    {contentTypes.map(t => <option key={t} value={t}>{t}</option>)}
                  </select>
                </div>
                <div>
                  <label className="text-xs text-[#999] mb-1 block">Style</label>
                  <select value={genStyle} onChange={e => setGenStyle(e.target.value)}
                    className="w-full bg-[#1a1a2e] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none">
                    {styles.map(s => <option key={s} value={s}>{s}</option>)}
                  </select>
                </div>
                <div>
                  <label className="text-xs text-[#999] mb-1 block">Quality</label>
                  <select value={genQuality} onChange={e => setGenQuality(e.target.value)}
                    className="w-full bg-[#1a1a2e] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none">
                    {qualities.map(q => <option key={q} value={q}>{q}</option>)}
                  </select>
                </div>
                <div>
                  <label className="text-xs text-[#999] mb-1 block">Batch Size</label>
                  <input type="number" value={genBatchSize} onChange={e => setGenBatchSize(e.target.value)}
                    min="1" max="100" className="w-full bg-[#1a1a2e] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none" />
                </div>
                <div className="col-span-2">
                  <label className="text-xs text-[#999] mb-1 block">Tags (comma-separated)</label>
                  <input type="text" value={genTags} onChange={e => setGenTags(e.target.value)}
                    placeholder="fantasy, combat, npc" className="w-full bg-[#1a1a2e] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none" />
                </div>
              </div>
              <button onClick={async () => {
                const result = await handleSubmit(`${API_BASE}/content-forge/generate`, {
                  content_type: genContentType,
                  style: genStyle,
                  quality: genQuality,
                  batch_size: parseInt(genBatchSize) || 1,
                  tags: genTags.split(',').map(s => s.trim()).filter(Boolean),
                });
                if (result) fetchAssets();
              }} disabled={loading}
                className="mt-3 px-4 py-2 bg-[#00d4ff] text-black rounded text-sm font-medium hover:bg-[#00b8e6] disabled:opacity-50">
                {loading ? 'Generating...' : 'Generate Content'}
              </button>
            </div>
          </div>
        )}

        {/* Assets Tab */}
        {activeTab === 'assets' && (
          <div className="space-y-4">
            <div className="bg-[#0f0f23] border border-[#2a2a4a] rounded-lg p-4">
              <h2 className="text-lg font-bold text-[#00d4ff] mb-3">Filters</h2>
              <div className="grid grid-cols-3 gap-3">
                <div>
                  <label className="text-xs text-[#999] mb-1 block">Type</label>
                  <select value={assetFilterType} onChange={e => setAssetFilterType(e.target.value)}
                    className="w-full bg-[#1a1a2e] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none">
                    <option value="">All Types</option>
                    {contentTypes.map(t => <option key={t} value={t}>{t}</option>)}
                  </select>
                </div>
                <div>
                  <label className="text-xs text-[#999] mb-1 block">Status</label>
                  <select value={assetFilterStatus} onChange={e => setAssetFilterStatus(e.target.value)}
                    className="w-full bg-[#1a1a2e] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none">
                    <option value="">All Statuses</option>
                    {statuses.map(s => <option key={s} value={s}>{s}</option>)}
                  </select>
                </div>
                <div>
                  <label className="text-xs text-[#999] mb-1 block">Style</label>
                  <select value={assetFilterStyle} onChange={e => setAssetFilterStyle(e.target.value)}
                    className="w-full bg-[#1a1a2e] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none">
                    <option value="">All Styles</option>
                    {styles.map(s => <option key={s} value={s}>{s}</option>)}
                  </select>
                </div>
              </div>
              <button onClick={() => fetchAssets({ type: assetFilterType, status: assetFilterStatus, style: assetFilterStyle })}
                className="mt-3 px-4 py-2 bg-[#00d4ff] text-black rounded text-sm font-medium hover:bg-[#00b8e6]">
                Apply Filters
              </button>
            </div>

            <div className="bg-[#0f0f23] border border-[#2a2a4a] rounded-lg p-4">
              <h2 className="text-lg font-bold text-[#00d4ff] mb-3">Assets ({assets.length})</h2>
              {assets.length > 0 ? (
                <div className="space-y-2">
                  {assets.map((a, i) => (
                    <div key={a.id || i} className="bg-[#1a1a2e] border border-[#2a2a4a] rounded-lg p-3">
                      <div className="flex items-center justify-between">
                        <span className="text-white text-sm font-medium">{a.name || a.id || `Asset ${i + 1}`}</span>
                        <div className="flex gap-1">
                          <span className="text-xs bg-[#0f0f23] text-[#00d4ff] px-2 py-0.5 rounded">{a.content_type || a.type || 'unknown'}</span>
                          <span className={`text-xs px-2 py-0.5 rounded ${
                            (a.status || '') === 'approved' ? 'bg-green-900 text-green-300' :
                            (a.status || '') === 'published' ? 'bg-blue-900 text-blue-300' :
                            'bg-[#1a1a1a] text-[#ccc]'
                          }`}>{a.status || 'draft'}</span>
                        </div>
                      </div>
                      <div className="flex items-center gap-4 text-xs text-[#999] mt-1">
                        <span>Style: <span className="text-white">{a.style || 'N/A'}</span></span>
                        <span>Quality: <span className="text-white">{a.quality || 'N/A'}</span></span>
                      </div>
                      <div className="flex gap-2 mt-2">
                        <button onClick={() => setSelectedAsset(selectedAsset?.id === a.id ? null : a)}
                          className="text-xs px-3 py-1 bg-[#0f0f23] text-[#ccc] rounded hover:bg-[#2a2a4a]">
                          {selectedAsset?.id === a.id ? 'Hide Details' : 'View Details'}
                        </button>
                        <button onClick={async () => {
                          await handleSubmit(`${API_BASE}/content-forge/assets/${a.id}/assess-quality`, {});
                          fetchAssets();
                        }}
                          className="text-xs px-3 py-1 bg-[#0f0f23] text-[#00d4ff] rounded hover:bg-[#2a2a4a]">
                          Assess Quality
                        </button>
                      </div>
                      {selectedAsset?.id === a.id && (
                        <div className="mt-2 bg-[#0f0f23] rounded p-3">
                          <pre className="text-xs text-[#ccc] font-mono whitespace-pre-wrap overflow-auto max-h-48">
                            {JSON.stringify(a, null, 2)}
                          </pre>
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              ) : (
                <div className="text-[#999] text-xs">No assets found</div>
              )}
            </div>
          </div>
        )}

        {/* Templates Tab */}
        {activeTab === 'templates' && (
          <div className="space-y-4">
            <div className="bg-[#0f0f23] border border-[#2a2a4a] rounded-lg p-4">
              <h2 className="text-lg font-bold text-[#00d4ff] mb-3">Add Template</h2>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-xs text-[#999] mb-1 block">Template Name</label>
                  <input type="text" value={tplName} onChange={e => setTplName(e.target.value)}
                    placeholder="dialogue_template_1" className="w-full bg-[#1a1a2e] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none" />
                </div>
                <div>
                  <label className="text-xs text-[#999] mb-1 block">Content Type</label>
                  <select value={tplContentType} onChange={e => setTplContentType(e.target.value)}
                    className="w-full bg-[#1a1a2e] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none">
                    {contentTypes.map(t => <option key={t} value={t}>{t}</option>)}
                  </select>
                </div>
                <div className="col-span-2">
                  <label className="text-xs text-[#999] mb-1 block">Template Structure (JSON)</label>
                  <textarea value={tplStructure} onChange={e => setTplStructure(e.target.value)}
                    rows={4} placeholder='{"fields": ["name", "description", "dialog"]}'
                    className="w-full bg-[#1a1a2e] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm font-mono focus:border-[#00d4ff] focus:outline-none" />
                </div>
              </div>
              <button onClick={async () => {
                if (!tplName.trim()) { setMessage('Template name required'); return; }
                let structure = {};
                try { structure = JSON.parse(tplStructure || '{}'); } catch { setMessage('Invalid JSON structure'); return; }
                await handleSubmit(`${API_BASE}/content-forge/add-template`, {
                  name: tplName, content_type: tplContentType, structure,
                });
                setTplName(''); setTplStructure('{}');
                fetchTemplates();
              }} disabled={loading}
                className="mt-3 px-4 py-2 bg-[#00d4ff] text-black rounded text-sm font-medium hover:bg-[#00b8e6] disabled:opacity-50">
                Add Template
              </button>
            </div>

            <div className="bg-[#0f0f23] border border-[#2a2a4a] rounded-lg p-4">
              <h2 className="text-lg font-bold text-[#00d4ff] mb-3">Templates ({templates.length})</h2>
              {templates.length > 0 ? (
                <div className="space-y-2">
                  {templates.map((t, i) => (
                    <div key={t.id || i} className="bg-[#1a1a2e] border border-[#2a2a4a] rounded-lg p-3">
                      <div className="flex items-center justify-between">
                        <span className="text-white text-sm font-medium">{t.name}</span>
                        <span className="text-xs bg-[#0f0f23] text-[#00d4ff] px-2 py-0.5 rounded">{t.content_type || 'unknown'}</span>
                      </div>
                      {t.structure && (
                        <div className="mt-1 bg-[#0f0f23] rounded p-2">
                          <pre className="text-xs text-[#ccc] font-mono whitespace-pre-wrap">
                            {JSON.stringify(t.structure, null, 2)}
                          </pre>
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              ) : (
                <div className="text-[#999] text-xs">No templates available</div>
              )}
            </div>
          </div>
        )}

      </div>
    </div>
  );
}