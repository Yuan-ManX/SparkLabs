"use client";
import React, { useState, useEffect, useCallback } from 'react';
import { API_BASE as API_ROOT } from '../utils/api';

const API_BASE = API_ROOT + '/engine';

const ASSET_TYPES = ['sprite', 'sprite_sheet', 'tilemap', 'audio_sfx', 'audio_music', 'ui_element', 'font', 'particle', 'shader', 'level', 'animation', 'prefab'];

interface PipelineStats {
  total_profiles: number;
  total_requests: number;
  total_assets: number;
  generation_success_rate: number;
}

interface StyleProfile {
  id: string;
  name: string;
  theme: string;
  mood: string;
  art_style: string;
  resolution: string;
  pixel_scale: number;
  color_palette: string[];
  created_at: number;
}

interface AssetRequest {
  id: string;
  request_id: string;
  asset_type: string;
  name: string;
  style_profile_id: string;
  parameters: Record<string, any>;
  status: string;
  created_at: number;
}

interface Asset {
  id: string;
  asset_id: string;
  asset_type: string;
  name: string;
  style_profile_id: string;
  url: string;
  metadata: Record<string, any>;
  created_at: number;
}

const uid = () => `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;

export default function EngineAssetPipelinePanel() {
  const [activeTab, setActiveTab] = useState('overview');
  const [stats, setStats] = useState<PipelineStats>({ total_profiles: 0, total_requests: 0, total_assets: 0, generation_success_rate: 0 });
  const [message, setMessage] = useState('');
  const [loading, setLoading] = useState(false);
  const [styleProfiles, setStyleProfiles] = useState<StyleProfile[]>([]);
  const [assets, setAssets] = useState<Asset[]>([]);

  // Style profile form state
  const [profileName, setProfileName] = useState('');
  const [profileTheme, setProfileTheme] = useState('');
  const [profileMood, setProfileMood] = useState('');
  const [profileArtStyle, setProfileArtStyle] = useState('pixel');
  const [profileResolution, setProfileResolution] = useState('1920x1080');
  const [profilePixelScale, setProfilePixelScale] = useState<number>(1);
  const [profileColorPalette, setProfileColorPalette] = useState('');

  // Asset request form state
  const [requestAssetType, setRequestAssetType] = useState('sprite');
  const [requestName, setRequestName] = useState('');
  const [requestStyleProfileId, setRequestStyleProfileId] = useState('');
  const [requestParameters, setRequestParameters] = useState('');

  // Generate form state
  const [genRequestId, setGenRequestId] = useState('');

  // Batch generate state
  const [batchRequestIds, setBatchRequestIds] = useState('');

  // Asset filter state
  const [assetFilterType, setAssetFilterType] = useState('all');
  const [assetFilterProfileId, setAssetFilterProfileId] = useState('');

  const fetchStats = useCallback(async () => {
    try {
      const r = await fetch(`${API_BASE}/asset-pipeline/stats`);
      if (r.ok) {
        const data = await r.json();
        setStats(data.stats || data);
      }
    } catch (e) { console.error(e); }
  }, []);

  const fetchStyleProfiles = useCallback(async () => {
    try {
      const r = await fetch(`${API_BASE}/asset-pipeline/style-profiles`);
      if (r.ok) setStyleProfiles(await r.json());
    } catch (e) { console.error(e); }
  }, []);

  const fetchAssets = useCallback(async () => {
    try {
      const params = new URLSearchParams();
      if (assetFilterType !== 'all') params.set('asset_type', assetFilterType);
      if (assetFilterProfileId) params.set('style_profile_id', assetFilterProfileId);
      const r = await fetch(`${API_BASE}/asset-pipeline/assets?${params}`);
      if (r.ok) setAssets(await r.json());
    } catch (e) { console.error(e); }
  }, [assetFilterType, assetFilterProfileId]);

  useEffect(() => {
    fetchStats();
    fetchStyleProfiles();
    fetchAssets();
    const i = setInterval(fetchStats, 15000);
    return () => clearInterval(i);
  }, [fetchStats, fetchStyleProfiles, fetchAssets]);

  const handleSubmit = async (url: string, body: any) => {
    setLoading(true); setMessage('');
    try {
      const r = await fetch(url, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });
      const data = await r.json();
      setMessage(r.ok ? 'Success' : data.detail || data.message || 'Failed');
      fetchStats();
      fetchStyleProfiles();
      fetchAssets();
      return data;
    } catch (e: any) { setMessage(e.message); }
    finally { setLoading(false); }
  };

  const createStyleProfile = async () => {
    let palette: string[] = [];
    try {
      palette = profileColorPalette ? JSON.parse(profileColorPalette) : [];
    } catch { setMessage('Invalid JSON for color palette'); return; }
    await handleSubmit(`${API_BASE}/asset-pipeline/create-style-profile`, {
      name: profileName,
      theme: profileTheme,
      mood: profileMood,
      art_style: profileArtStyle,
      resolution: profileResolution,
      pixel_scale: profilePixelScale,
      color_palette: palette,
    });
    setProfileName(''); setProfileTheme(''); setProfileMood(''); setProfileColorPalette('');
  };

  const requestAsset = async () => {
    let params: Record<string, any> = {};
    try {
      params = requestParameters ? JSON.parse(requestParameters) : {};
    } catch { setMessage('Invalid JSON for parameters'); return; }
    await handleSubmit(`${API_BASE}/asset-pipeline/request-asset`, {
      asset_type: requestAssetType,
      name: requestName,
      style_profile_id: requestStyleProfileId,
      parameters: params,
    });
    setRequestName(''); setRequestParameters('');
  };

  const generateAsset = async () => {
    await handleSubmit(`${API_BASE}/asset-pipeline/generate-asset`, { request_id: genRequestId });
    setGenRequestId('');
  };

  const batchGenerate = async () => {
    const ids = batchRequestIds.split(',').map(s => s.trim()).filter(Boolean);
    await handleSubmit(`${API_BASE}/asset-pipeline/batch-generate`, { request_ids: ids });
    setBatchRequestIds('');
  };

  const tabs = ['overview', 'styles', 'generate', 'assets'];

  const getAssetTypeColor = (type: string) => {
    const colors: Record<string, string> = {
      sprite: 'bg-blue-900/50 text-blue-300',
      sprite_sheet: 'bg-cyan-900/50 text-cyan-300',
      tilemap: 'bg-green-900/50 text-green-300',
      audio_sfx: 'bg-purple-900/50 text-purple-300',
      audio_music: 'bg-pink-900/50 text-pink-300',
      ui_element: 'bg-yellow-900/50 text-yellow-300',
      font: 'bg-indigo-900/50 text-indigo-300',
      particle: 'bg-orange-900/50 text-orange-300',
      shader: 'bg-red-900/50 text-red-300',
      level: 'bg-teal-900/50 text-teal-300',
      animation: 'bg-rose-900/50 text-rose-300',
      prefab: 'bg-amber-900/50 text-amber-300',
    };
    return colors[type] || 'bg-[#1a1a1a]/50 text-[#ccc]';
  };

  const ART_STYLES = ['pixel', 'cartoon', 'realistic', 'low_poly', 'voxel', 'hand_drawn', 'vector', 'isometric', 'sketch', 'abstract'];
  const RESOLUTIONS = ['320x180', '640x360', '960x540', '1280x720', '1920x1080', '2560x1440', '3840x2160', 'custom'];

  const overviewContent = (
    <div>
      <h2 className="text-lg font-semibold mb-4 text-[#00d4ff]">Asset Pipeline Overview</h2>
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
        {[
          { label: 'Style Profiles', value: stats.total_profiles, color: '#00d4ff' },
          { label: 'Total Requests', value: stats.total_requests, color: '#fdcb6e' },
          { label: 'Total Assets', value: stats.total_assets, color: '#6bcb77' },
          { label: 'Success Rate', value: `${Math.round(stats.generation_success_rate * 100)}%`, color: stats.generation_success_rate >= 0.8 ? '#6bcb77' : '#ff9f43' },
        ].map(s => (
          <div key={s.label} className="bg-[#0f0f23] border border-[#2a2a4a] rounded-lg p-4 text-center">
            <div className="text-2xl font-bold" style={{ color: s.color }}>{s.value}</div>
            <div className="text-xs text-[#999] mt-1">{s.label}</div>
          </div>
        ))}
      </div>
      <div className="bg-[#0f0f23] border border-[#2a2a4a] rounded-lg p-4">
        <h3 className="text-sm font-medium text-[#ccc] mb-3">Supported Asset Types</h3>
        <div className="flex flex-wrap gap-2">
          {ASSET_TYPES.map(type => (
            <span key={type} className={`px-2 py-1 rounded text-xs ${getAssetTypeColor(type)} capitalize`}>{type.replace(/_/g, ' ')}</span>
          ))}
        </div>
      </div>
    </div>
  );

  const stylesContent = (
    <div>
      <h2 className="text-lg font-semibold mb-4 text-[#00d4ff]">Style Profiles</h2>

      {/* Create Style Profile Form */}
      <div className="bg-[#0f0f23] border border-[#2a2a4a] rounded-lg p-4 mb-6">
        <h3 className="text-sm font-medium text-[#ccc] mb-3">Create Style Profile</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3 mb-3">
          <input
            type="text" placeholder="Profile Name"
            value={profileName}
            onChange={e => setProfileName(e.target.value)}
            className="bg-[#1a1a2e] border border-[#2a2a4a] rounded px-3 py-2 text-sm text-white placeholder-gray-500 focus:border-[#00d4ff] outline-none"
          />
          <input
            type="text" placeholder="Theme"
            value={profileTheme}
            onChange={e => setProfileTheme(e.target.value)}
            className="bg-[#1a1a2e] border border-[#2a2a4a] rounded px-3 py-2 text-sm text-white placeholder-gray-500 focus:border-[#00d4ff] outline-none"
          />
          <input
            type="text" placeholder="Mood"
            value={profileMood}
            onChange={e => setProfileMood(e.target.value)}
            className="bg-[#1a1a2e] border border-[#2a2a4a] rounded px-3 py-2 text-sm text-white placeholder-gray-500 focus:border-[#00d4ff] outline-none"
          />
          <select
            value={profileArtStyle}
            onChange={e => setProfileArtStyle(e.target.value)}
            className="bg-[#1a1a2e] border border-[#2a2a4a] rounded px-3 py-2 text-sm text-white focus:border-[#00d4ff] outline-none"
          >
            {ART_STYLES.map(s => (
              <option key={s} value={s} className="bg-[#1a1a2e] capitalize">{s.replace(/_/g, ' ')}</option>
            ))}
          </select>
          <select
            value={profileResolution}
            onChange={e => setProfileResolution(e.target.value)}
            className="bg-[#1a1a2e] border border-[#2a2a4a] rounded px-3 py-2 text-sm text-white focus:border-[#00d4ff] outline-none"
          >
            {RESOLUTIONS.map(r => (
              <option key={r} value={r} className="bg-[#1a1a2e]">{r}</option>
            ))}
          </select>
          <input
            type="number" placeholder="Pixel Scale" min={1} max={32}
            value={profilePixelScale}
            onChange={e => setProfilePixelScale(Number(e.target.value))}
            className="bg-[#1a1a2e] border border-[#2a2a4a] rounded px-3 py-2 text-sm text-white placeholder-gray-500 focus:border-[#00d4ff] outline-none"
          />
        </div>
        <div className="mb-3">
          <textarea
            placeholder='Color Palette (JSON) e.g. ["#ff0000", "#00ff00", "#0000ff"]'
            value={profileColorPalette}
            onChange={e => setProfileColorPalette(e.target.value)}
            rows={2}
            className="w-full bg-[#1a1a2e] border border-[#2a2a4a] rounded px-3 py-2 text-sm text-white placeholder-gray-500 focus:border-[#00d4ff] outline-none resize-none font-mono"
          />
        </div>
        <button
          onClick={createStyleProfile} disabled={loading || !profileName}
          className="bg-[#00d4ff] text-black px-4 py-2 rounded text-sm font-medium hover:bg-[#00b8e0] disabled:opacity-50 transition-colors"
        >
          Create Profile
        </button>
      </div>

      {/* Style Profiles List */}
      <div>
        <h3 className="text-sm font-medium text-[#ccc] mb-3">Profiles ({styleProfiles.length})</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {styleProfiles.map(p => (
            <div key={p.id} className="bg-[#0f0f23] border border-[#2a2a4a] rounded-lg p-4">
              <div className="flex items-center justify-between mb-3">
                <h4 className="text-sm font-medium text-white">{p.name}</h4>
                <span className="px-2 py-0.5 bg-[#1a1a2e] border border-[#2a2a4a] rounded text-xs text-[#00d4ff] capitalize">{p.art_style?.replace(/_/g, ' ')}</span>
              </div>
              <div className="grid grid-cols-2 gap-2 mb-3">
                <div>
                  <span className="text-xs text-[#666]">Theme</span>
                  <p className="text-xs text-[#ccc]">{p.theme || '-'}</p>
                </div>
                <div>
                  <span className="text-xs text-[#666]">Mood</span>
                  <p className="text-xs text-[#ccc]">{p.mood || '-'}</p>
                </div>
                <div>
                  <span className="text-xs text-[#666]">Resolution</span>
                  <p className="text-xs text-[#ccc]">{p.resolution}</p>
                </div>
                <div>
                  <span className="text-xs text-[#666]">Pixel Scale</span>
                  <p className="text-xs text-[#ccc]">{p.pixel_scale}x</p>
                </div>
              </div>
              {p.color_palette && p.color_palette.length > 0 && (
                <div>
                  <span className="text-xs text-[#666] block mb-1">Palette</span>
                  <div className="flex gap-1 flex-wrap">
                    {p.color_palette.map((color, i) => (
                      <div key={i} className="flex items-center gap-1">
                        <div className="w-4 h-4 rounded border border-[#2a2a4a]" style={{ backgroundColor: color }} />
                        <span className="text-xs text-[#666]">{color}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          ))}
        </div>
        {styleProfiles.length === 0 && (
          <div className="text-center text-[#666] py-8">No style profiles yet. Create one above.</div>
        )}
      </div>
    </div>
  );

  const generateContent = (
    <div>
      <h2 className="text-lg font-semibold mb-4 text-[#00d4ff]">Generate Assets</h2>

      {/* Request Asset Form */}
      <div className="bg-[#0f0f23] border border-[#2a2a4a] rounded-lg p-4 mb-4">
        <h3 className="text-sm font-medium text-[#ccc] mb-3">Request Asset</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3 mb-3">
          <select
            value={requestAssetType}
            onChange={e => setRequestAssetType(e.target.value)}
            className="bg-[#1a1a2e] border border-[#2a2a4a] rounded px-3 py-2 text-sm text-white focus:border-[#00d4ff] outline-none"
          >
            {ASSET_TYPES.map(t => (
              <option key={t} value={t} className="bg-[#1a1a2e] capitalize">{t.replace(/_/g, ' ')}</option>
            ))}
          </select>
          <input
            type="text" placeholder="Asset Name"
            value={requestName}
            onChange={e => setRequestName(e.target.value)}
            className="bg-[#1a1a2e] border border-[#2a2a4a] rounded px-3 py-2 text-sm text-white placeholder-gray-500 focus:border-[#00d4ff] outline-none"
          />
          <input
            type="text" placeholder="Style Profile ID"
            value={requestStyleProfileId}
            onChange={e => setRequestStyleProfileId(e.target.value)}
            className="bg-[#1a1a2e] border border-[#2a2a4a] rounded px-3 py-2 text-sm text-white placeholder-gray-500 focus:border-[#00d4ff] outline-none"
          />
        </div>
        <div className="mb-3">
          <textarea
            placeholder='Parameters (JSON) e.g. {"width": 64, "height": 64}'
            value={requestParameters}
            onChange={e => setRequestParameters(e.target.value)}
            rows={2}
            className="w-full bg-[#1a1a2e] border border-[#2a2a4a] rounded px-3 py-2 text-sm text-white placeholder-gray-500 focus:border-[#00d4ff] outline-none resize-none font-mono"
          />
        </div>
        <button
          onClick={requestAsset} disabled={loading || !requestName || !requestStyleProfileId}
          className="bg-[#00d4ff] text-black px-4 py-2 rounded text-sm font-medium hover:bg-[#00b8e0] disabled:opacity-50 transition-colors"
        >
          Request Asset
        </button>
      </div>

      {/* Generate Asset */}
      <div className="bg-[#0f0f23] border border-[#2a2a4a] rounded-lg p-4 mb-4">
        <h3 className="text-sm font-medium text-[#ccc] mb-3">Generate Single Asset</h3>
        <div className="flex gap-3 items-end">
          <input
            type="text" placeholder="Request ID"
            value={genRequestId}
            onChange={e => setGenRequestId(e.target.value)}
            className="flex-1 bg-[#1a1a2e] border border-[#2a2a4a] rounded px-3 py-2 text-sm text-white placeholder-gray-500 focus:border-[#00d4ff] outline-none"
          />
          <button
            onClick={generateAsset} disabled={loading || !genRequestId}
            className="bg-[#6bcb77] text-black px-4 py-2 rounded text-sm font-medium hover:bg-[#5ab867] disabled:opacity-50 transition-colors"
          >
            Generate
          </button>
        </div>
      </div>

      {/* Batch Generate */}
      <div className="bg-[#0f0f23] border border-[#2a2a4a] rounded-lg p-4">
        <h3 className="text-sm font-medium text-[#ccc] mb-3">Batch Generate</h3>
        <div className="mb-3">
          <input
            type="text" placeholder="Request IDs (comma-separated)"
            value={batchRequestIds}
            onChange={e => setBatchRequestIds(e.target.value)}
            className="w-full bg-[#1a1a2e] border border-[#2a2a4a] rounded px-3 py-2 text-sm text-white placeholder-gray-500 focus:border-[#00d4ff] outline-none"
          />
        </div>
        <button
          onClick={batchGenerate} disabled={loading || !batchRequestIds}
          className="bg-[#fdcb6e] text-black px-4 py-2 rounded text-sm font-medium hover:bg-[#e8b94e] disabled:opacity-50 transition-colors"
        >
          Batch Generate
        </button>
      </div>
    </div>
  );

  const assetsContent = (
    <div>
      <h2 className="text-lg font-semibold mb-4 text-[#00d4ff]">Assets</h2>

      {/* Filters */}
      <div className="bg-[#0f0f23] border border-[#2a2a4a] rounded-lg p-4 mb-4">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          <div>
            <label className="text-xs text-[#666] block mb-1">Asset Type</label>
            <select
              value={assetFilterType}
              onChange={e => setAssetFilterType(e.target.value)}
              className="w-full bg-[#1a1a2e] border border-[#2a2a4a] rounded px-3 py-2 text-sm text-white focus:border-[#00d4ff] outline-none"
            >
              <option value="all" className="bg-[#1a1a2e]">All Types</option>
              {ASSET_TYPES.map(t => (
                <option key={t} value={t} className="bg-[#1a1a2e] capitalize">{t.replace(/_/g, ' ')}</option>
              ))}
            </select>
          </div>
          <div>
            <label className="text-xs text-[#666] block mb-1">Style Profile ID</label>
            <input
              type="text" placeholder="Filter by profile ID"
              value={assetFilterProfileId}
              onChange={e => setAssetFilterProfileId(e.target.value)}
              className="w-full bg-[#1a1a2e] border border-[#2a2a4a] rounded px-3 py-2 text-sm text-white placeholder-gray-500 focus:border-[#00d4ff] outline-none"
            />
          </div>
        </div>
      </div>

      {/* Assets Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {assets.map(a => (
          <div key={a.id || a.asset_id} className="bg-[#0f0f23] border border-[#2a2a4a] rounded-lg p-4">
            <div className="flex items-start justify-between mb-2">
              <div>
                <h4 className="text-sm font-medium text-white">{a.name}</h4>
                <span className="text-xs text-[#666]">{a.asset_id}</span>
              </div>
              <span className={`px-2 py-0.5 rounded text-xs capitalize ${getAssetTypeColor(a.asset_type)}`}>{a.asset_type.replace(/_/g, ' ')}</span>
            </div>
            <div className="flex flex-wrap gap-2 mb-3 text-xs text-[#999]">
              <span>Profile: {a.style_profile_id}</span>
            </div>
            {a.url && (
              <div className="bg-[#1a1a2e] border border-[#2a2a4a] rounded p-3 flex items-center justify-center mb-2">
                <img src={a.url} alt={a.name} className="max-h-32 object-contain" />
              </div>
            )}
            {a.metadata && Object.keys(a.metadata).length > 0 && (
              <div className="mt-2">
                <span className="text-xs text-[#666] block mb-1">Metadata</span>
                <div className="flex flex-wrap gap-1">
                  {Object.entries(a.metadata).slice(0, 6).map(([k, v]) => (
                    <span key={k} className="px-2 py-0.5 bg-[#1a1a2e] border border-[#2a2a4a] rounded text-xs">
                      <span className="text-[#666]">{k}:</span>{' '}
                      <span className="text-[#ccc]">{String(v)}</span>
                    </span>
                  ))}
                </div>
              </div>
            )}
          </div>
        ))}
      </div>
      {assets.length === 0 && (
        <div className="text-center text-[#666] py-8">No assets found. Generate some in the Generate tab.</div>
      )}
    </div>
  );

  return (
    <div className="h-full flex flex-col bg-[#1a1a2e] text-white">
      <div className="flex gap-1 p-3 border-b border-[#2a2a4a]">
        {tabs.map(t => (
          <button key={t} onClick={() => setActiveTab(t)}
            className={`px-4 py-2 rounded text-sm font-medium transition-colors ${activeTab === t ? 'bg-[#00d4ff] text-black' : 'bg-[#0f0f23] text-[#ccc] hover:bg-[#2a2a4a]'}`}>
            {t.charAt(0).toUpperCase() + t.slice(1)}
          </button>
        ))}
      </div>
      {message && <div className="mx-4 mt-2 p-2 bg-[#0f0f23] border border-[#2a2a4a] rounded text-sm text-[#00d4ff]">{message}</div>}
      <div className="flex-1 overflow-auto p-4">
        {activeTab === 'overview' && overviewContent}
        {activeTab === 'styles' && stylesContent}
        {activeTab === 'generate' && generateContent}
        {activeTab === 'assets' && assetsContent}
      </div>
    </div>
  );
}