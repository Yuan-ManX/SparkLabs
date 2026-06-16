"use client";
import React, { useState, useEffect, useCallback } from 'react';

const API_BASE = 'http://localhost:8000/api/engine';

export default function EngineDeploymentPanel() {
  const [activeTab, setActiveTab] = useState('overview');
  const [stats, setStats] = useState<any>({});
  const [message, setMessage] = useState('');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<any>(null);

  // Create config
  const [ccName, setCcName] = useState('');
  const [ccPlatform, setCcPlatform] = useState('web');
  const [ccOptimization, setCcOptimization] = useState('standard');
  const [ccTargetRes, setCcTargetRes] = useState('1920x1080');
  const [ccCompression, setCcCompression] = useState(true);
  const [ccIncludeAssets, setCcIncludeAssets] = useState('');
  const [ccExcludePatterns, setCcExcludePatterns] = useState('');
  const [ccCustomFlags, setCcCustomFlags] = useState('{}');

  // Queue build
  const [qbConfigId, setQbConfigId] = useState('');

  // Execute build
  const [ebJobId, setEbJobId] = useState('');

  // Builds list
  const [builds, setBuilds] = useState<any[]>([]);
  const [buildFilter, setBuildFilter] = useState({ platform: '', status: '' });

  const fetchStats = useCallback(async () => {
    try { const r = await fetch(`${API_BASE}/deployment-orchestrator/stats`); if (r.ok) setStats(await r.json()); } catch (e) { console.error(e); }
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
      setMessage(r.ok ? 'Success' : data.message || data.error || 'Failed');
      fetchStats();
    } catch (e: any) { setMessage(e.message); }
    finally { setLoading(false); }
  };

  const platformOptions = ['web', 'windows', 'macos', 'linux', 'ios', 'android', 'html5', 'pwa', 'steam', 'epic', 'itch'];
  const optimizationOptions = ['none', 'basic', 'standard', 'aggressive', 'maximum'];

  const statusColors: Record<string, string> = {
    completed: 'bg-green-900 text-green-300',
    success: 'bg-green-900 text-green-300',
    building: 'bg-blue-900 text-blue-300',
    queued: 'bg-yellow-900 text-yellow-300',
    failed: 'bg-red-900 text-red-300',
    cancelled: 'bg-gray-700 text-gray-300',
  };

  const platformBadgeColors: Record<string, string> = {
    web: 'bg-blue-900 text-blue-300',
    windows: 'bg-sky-900 text-sky-300',
    macos: 'bg-gray-700 text-gray-300',
    linux: 'bg-orange-900 text-orange-300',
    ios: 'bg-gray-700 text-gray-300',
    android: 'bg-green-900 text-green-300',
    html5: 'bg-red-900 text-red-300',
    pwa: 'bg-purple-900 text-purple-300',
    steam: 'bg-indigo-900 text-indigo-300',
    epic: 'bg-gray-700 text-gray-300',
    itch: 'bg-pink-900 text-pink-300',
  };

  const fetchBuilds = async () => {
    let url = `${API_BASE}/deployment-orchestrator/builds`;
    const params = new URLSearchParams();
    if (buildFilter.platform) params.set('platform', buildFilter.platform);
    if (buildFilter.status) params.set('status', buildFilter.status);
    if (params.toString()) url += '?' + params.toString();
    try {
      const r = await fetch(url);
      if (r.ok) {
        const d = await r.json();
        setBuilds(Array.isArray(d) ? d : d.builds || []);
      }
    } catch (e) { console.error(e); }
  };

  const tabs = ['overview', 'configs', 'build', 'deploy'];

  return (
    <div className="h-full flex flex-col bg-[#1a1a2e] text-white">
      <div className="flex gap-1 p-3 border-b border-[#2a2a4a]">
        {tabs.map(t => (
          <button key={t} onClick={() => setActiveTab(t)}
            className={`px-4 py-2 rounded text-sm font-medium ${activeTab === t ? 'bg-[#00d4ff] text-black' : 'bg-[#0f0f23] text-gray-300 hover:bg-[#2a2a4a]'}`}>
            {t.charAt(0).toUpperCase() + t.slice(1)}
          </button>
        ))}
      </div>
      {message && <div className="mx-4 mt-2 p-2 bg-[#0f0f23] border border-[#2a2a4a] rounded text-sm text-[#00d4ff]">{message}</div>}
      <div className="flex-1 overflow-auto p-4">

        {/* Overview Tab */}
        {activeTab === 'overview' && (
          <div className="space-y-4">
            <h2 className="text-lg font-bold text-[#00d4ff]">Deployment Orchestrator</h2>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <div className="bg-[#0f0f23] p-4 rounded border border-[#2a2a4a]">
                <h3 className="text-[#00d4ff] text-xs">Total Configs</h3>
                <p className="text-2xl font-bold mt-1">{stats.total_configs ?? 0}</p>
              </div>
              <div className="bg-[#0f0f23] p-4 rounded border border-[#2a2a4a]">
                <h3 className="text-[#00d4ff] text-xs">Total Builds</h3>
                <p className="text-2xl font-bold mt-1">{stats.total_builds ?? 0}</p>
              </div>
              <div className="bg-[#0f0f23] p-4 rounded border border-[#2a2a4a]">
                <h3 className="text-[#00d4ff] text-xs">Successful Builds</h3>
                <p className="text-2xl font-bold mt-1 text-[#00ff88]">{stats.successful_builds ?? 0}</p>
              </div>
              <div className="bg-[#0f0f23] p-4 rounded border border-[#2a2a4a]">
                <h3 className="text-[#00d4ff] text-xs">Failed Builds</h3>
                <p className="text-2xl font-bold mt-1 text-[#ff6b6b]">{stats.failed_builds ?? 0}</p>
              </div>
            </div>
            {Object.keys(stats).length > 0 && (
              <div className="bg-[#0f0f23] p-4 rounded border border-[#2a2a4a]">
                <h3 className="text-[#00d4ff] text-sm mb-2">All Stats</h3>
                <pre className="text-xs text-gray-300 overflow-auto">{JSON.stringify(stats, null, 2)}</pre>
              </div>
            )}
          </div>
        )}

        {/* Configs Tab */}
        {activeTab === 'configs' && (
          <div className="space-y-6">
            <div className="bg-[#0f0f23] border border-[#2a2a4a] rounded-lg p-4">
              <h2 className="text-lg font-bold text-[#00d4ff] mb-3">Create Deployment Config</h2>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-xs text-gray-400 mb-1 block">Config Name</label>
                  <input type="text" value={ccName} onChange={e => setCcName(e.target.value)}
                    placeholder="production_web_build" className="w-full bg-[#1a1a2e] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none" />
                </div>
                <div>
                  <label className="text-xs text-gray-400 mb-1 block">Platform</label>
                  <select value={ccPlatform} onChange={e => setCcPlatform(e.target.value)}
                    className="w-full bg-[#1a1a2e] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none">
                    {platformOptions.map(p => (
                      <option key={p} value={p}>{p.charAt(0).toUpperCase() + p.slice(1)}</option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="text-xs text-gray-400 mb-1 block">Optimization Level</label>
                  <select value={ccOptimization} onChange={e => setCcOptimization(e.target.value)}
                    className="w-full bg-[#1a1a2e] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none">
                    {optimizationOptions.map(o => (
                      <option key={o} value={o}>{o.charAt(0).toUpperCase() + o.slice(1)}</option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="text-xs text-gray-400 mb-1 block">Target Resolution</label>
                  <input type="text" value={ccTargetRes} onChange={e => setCcTargetRes(e.target.value)}
                    placeholder="1920x1080" className="w-full bg-[#1a1a2e] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none" />
                </div>
                <div className="flex items-center gap-2">
                  <label className="flex items-center gap-2 cursor-pointer">
                    <input type="checkbox" checked={ccCompression} onChange={e => setCcCompression(e.target.checked)}
                      className="accent-[#00d4ff]" />
                    <span className="text-xs text-gray-300">Enable Compression</span>
                  </label>
                </div>
                <div>
                  <label className="text-xs text-gray-400 mb-1 block">Include Assets (comma-separated)</label>
                  <input type="text" value={ccIncludeAssets} onChange={e => setCcIncludeAssets(e.target.value)}
                    placeholder="*.png,*.wav,*.json" className="w-full bg-[#1a1a2e] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none" />
                </div>
                <div>
                  <label className="text-xs text-gray-400 mb-1 block">Exclude Patterns (comma-separated)</label>
                  <input type="text" value={ccExcludePatterns} onChange={e => setCcExcludePatterns(e.target.value)}
                    placeholder="*.psd,*.blend,node_modules" className="w-full bg-[#1a1a2e] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none" />
                </div>
                <div className="col-span-2">
                  <label className="text-xs text-gray-400 mb-1 block">Custom Flags (JSON)</label>
                  <textarea value={ccCustomFlags} onChange={e => setCcCustomFlags(e.target.value)}
                    rows={3} placeholder='{"debug": false, "sourcemaps": true}' className="w-full bg-[#1a1a2e] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm font-mono focus:border-[#00d4ff] focus:outline-none" />
                </div>
              </div>
              <button
                onClick={async () => {
                  if (!ccName.trim()) { setMessage('Config name required'); return; }
                  let flags = {};
                  try { flags = JSON.parse(ccCustomFlags || '{}'); } catch { setMessage('Invalid custom flags JSON'); return; }
                  await handlePost(`${API_BASE}/deployment-orchestrator/create-config`, {
                    name: ccName, platform: ccPlatform, optimization_level: ccOptimization,
                    target_resolution: ccTargetRes, compression: ccCompression,
                    include_assets: ccIncludeAssets.split(',').map(s => s.trim()).filter(Boolean),
                    exclude_patterns: ccExcludePatterns.split(',').map(s => s.trim()).filter(Boolean),
                    custom_flags: flags,
                  });
                  setCcName(''); setCcCustomFlags('{}'); setCcIncludeAssets(''); setCcExcludePatterns('');
                }}
                disabled={loading}
                className="mt-3 px-4 py-2 bg-[#00d4ff] text-black rounded text-sm font-medium hover:bg-[#00b8e6] disabled:opacity-50">
                Create Config
              </button>
            </div>

            {result && result.id && (
              <div className="bg-[#0f0f23] border border-[#2a2a4a] rounded-lg p-4">
                <h2 className="text-lg font-bold text-[#00d4ff] mb-3">Config Created</h2>
                <div className="grid grid-cols-2 gap-3 text-xs">
                  <div className="bg-[#1a1a2e] p-2 rounded border border-[#2a2a4a]">
                    <span className="text-gray-400">ID: </span><span className="text-white font-mono">{result.id}</span>
                  </div>
                  <div className="bg-[#1a1a2e] p-2 rounded border border-[#2a2a4a]">
                    <span className="text-gray-400">Platform: </span><span className="text-white">{result.platform}</span>
                  </div>
                </div>
              </div>
            )}
          </div>
        )}

        {/* Build Tab */}
        {activeTab === 'build' && (
          <div className="space-y-6">
            <div className="bg-[#0f0f23] border border-[#2a2a4a] rounded-lg p-4">
              <h2 className="text-lg font-bold text-[#00d4ff] mb-3">Queue Build</h2>
              <div className="flex gap-3 items-end">
                <div className="flex-1">
                  <label className="text-xs text-gray-400 mb-1 block">Config ID</label>
                  <input type="text" value={qbConfigId} onChange={e => setQbConfigId(e.target.value)}
                    placeholder="config_abc123" className="w-full bg-[#1a1a2e] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none" />
                </div>
                <button
                  onClick={async () => {
                    if (!qbConfigId.trim()) { setMessage('Config ID required'); return; }
                    await handlePost(`${API_BASE}/deployment-orchestrator/queue-build`, { config_id: qbConfigId });
                  }}
                  disabled={loading}
                  className="px-4 py-2 bg-[#00d4ff] text-black rounded text-sm font-medium hover:bg-[#00b8e6] disabled:opacity-50">
                  Queue Build
                </button>
              </div>
            </div>

            {result && result.job_id && (
              <div className="bg-[#0f0f23] border border-[#2a2a4a] rounded-lg p-4">
                <h2 className="text-lg font-bold text-[#00d4ff] mb-3">Build Queued</h2>
                <p className="text-sm text-gray-300">Job ID: <span className="text-[#00d4ff] font-mono">{result.job_id}</span></p>
              </div>
            )}

            <div className="bg-[#0f0f23] border border-[#2a2a4a] rounded-lg p-4">
              <h2 className="text-lg font-bold text-[#00d4ff] mb-3">Execute Build</h2>
              <div className="flex gap-3 items-end">
                <div className="flex-1">
                  <label className="text-xs text-gray-400 mb-1 block">Job ID</label>
                  <input type="text" value={ebJobId} onChange={e => setEbJobId(e.target.value)}
                    placeholder="build_abc123" className="w-full bg-[#1a1a2e] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none" />
                </div>
                <button
                  onClick={async () => {
                    if (!ebJobId.trim()) { setMessage('Job ID required'); return; }
                    await handlePost(`${API_BASE}/deployment-orchestrator/execute-build`, { job_id: ebJobId });
                  }}
                  disabled={loading}
                  className="px-4 py-2 bg-[#00ff88] text-black rounded text-sm font-medium hover:bg-[#00cc6a] disabled:opacity-50">
                  Execute Build
                </button>
              </div>
            </div>

            {result && result.status && (
              <div className="bg-[#0f0f23] border border-[#2a2a4a] rounded-lg p-4">
                <h2 className="text-lg font-bold text-[#00d4ff] mb-3">Build Progress</h2>
                <div className="space-y-3">
                  <div className="flex items-center justify-between">
                    <span className="text-xs text-gray-400">Status</span>
                    <span className={`text-xs px-2 py-0.5 rounded font-mono ${statusColors[result.status] || 'bg-gray-700 text-gray-300'}`}>{result.status}</span>
                  </div>
                  {result.progress != null && (
                    <div>
                      <div className="flex justify-between text-xs mb-1">
                        <span className="text-gray-400">Progress</span>
                        <span className="text-[#00d4ff]">{result.progress}%</span>
                      </div>
                      <div className="h-2 bg-[#2a2a4a] rounded-full overflow-hidden">
                        <div className="h-full bg-[#00d4ff] rounded-full transition-all" style={{ width: `${result.progress}%` }} />
                      </div>
                    </div>
                  )}
                  {result.errors && result.errors.length > 0 && (
                    <div>
                      <span className="text-xs text-red-400 block mb-1">Errors ({result.errors.length})</span>
                      <div className="space-y-1">
                        {result.errors.map((e: string, i: number) => (
                          <div key={i} className="text-xs text-red-300 bg-[#1a1a2e] p-2 rounded border border-red-900">{e}</div>
                        ))}
                      </div>
                    </div>
                  )}
                  {result.warnings && result.warnings.length > 0 && (
                    <div>
                      <span className="text-xs text-yellow-400 block mb-1">Warnings ({result.warnings.length})</span>
                      <div className="space-y-1">
                        {result.warnings.map((w: string, i: number) => (
                          <div key={i} className="text-xs text-yellow-300 bg-[#1a1a2e] p-2 rounded border border-yellow-900">{w}</div>
                        ))}
                      </div>
                    </div>
                  )}
                  <button
                    onClick={async () => {
                      if (!ebJobId.trim() && !result.job_id) { setMessage('No job ID available'); return; }
                      await handlePost(`${API_BASE}/deployment-orchestrator/optimize-assets`, { job_id: ebJobId || result.job_id });
                    }}
                    disabled={loading}
                    className="px-4 py-2 bg-[#0f0f23] border border-[#2a2a4a] rounded text-sm text-gray-300 hover:bg-[#2a2a4a] disabled:opacity-50">
                    Optimize Assets
                  </button>
                </div>
              </div>
            )}
          </div>
        )}

        {/* Deploy Tab */}
        {activeTab === 'deploy' && (
          <div className="space-y-6">
            <div className="bg-[#0f0f23] border border-[#2a2a4a] rounded-lg p-4">
              <h2 className="text-lg font-bold text-[#00d4ff] mb-3">Build List</h2>
              <div className="flex gap-3 mb-3">
                <div className="flex-1">
                  <label className="text-xs text-gray-400 mb-1 block">Platform Filter</label>
                  <select value={buildFilter.platform} onChange={e => setBuildFilter(prev => ({ ...prev, platform: e.target.value }))}
                    className="w-full bg-[#1a1a2e] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none">
                    <option value="">All Platforms</option>
                    {platformOptions.map(p => (
                      <option key={p} value={p}>{p.charAt(0).toUpperCase() + p.slice(1)}</option>
                    ))}
                  </select>
                </div>
                <div className="flex-1">
                  <label className="text-xs text-gray-400 mb-1 block">Status Filter</label>
                  <select value={buildFilter.status} onChange={e => setBuildFilter(prev => ({ ...prev, status: e.target.value }))}
                    className="w-full bg-[#1a1a2e] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none">
                    <option value="">All Statuses</option>
                    <option value="queued">Queued</option>
                    <option value="building">Building</option>
                    <option value="completed">Completed</option>
                    <option value="failed">Failed</option>
                    <option value="cancelled">Cancelled</option>
                  </select>
                </div>
                <div className="flex items-end">
                  <button onClick={fetchBuilds}
                    className="px-4 py-2 bg-[#00d4ff] text-black rounded text-sm font-medium hover:bg-[#00b8e6]">
                    Search
                  </button>
                </div>
              </div>
            </div>

            {builds.length > 0 ? (
              <div className="space-y-2">
                {builds.map((b: any, i: number) => (
                  <div key={b.id || i} className="bg-[#0f0f23] border border-[#2a2a4a] rounded-lg p-3">
                    <div className="flex items-center justify-between mb-2">
                      <div className="flex items-center gap-2">
                        <span className="text-white text-sm font-medium">{b.name || b.id || `Build ${i + 1}`}</span>
                        <span className={`text-xs px-2 py-0.5 rounded ${platformBadgeColors[b.platform] || 'bg-gray-700 text-gray-300'}`}>
                          {b.platform || 'unknown'}
                        </span>
                      </div>
                      <span className={`text-xs px-2 py-0.5 rounded font-mono ${statusColors[b.status] || 'bg-gray-700 text-gray-300'}`}>
                        {b.status || 'unknown'}
                      </span>
                    </div>
                    <div className="flex items-center gap-4 text-xs text-gray-400">
                      {b.file_size != null && <span>Size: <span className="text-white">{typeof b.file_size === 'number' ? (b.file_size / 1024 / 1024).toFixed(1) + ' MB' : b.file_size}</span></span>}
                      {b.duration != null && <span>Duration: <span className="text-white">{typeof b.duration === 'number' ? b.duration.toFixed(1) + 's' : b.duration}</span></span>}
                      {b.config_id && <span>Config: <span className="text-white font-mono">{b.config_id}</span></span>}
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="text-gray-400 text-sm text-center py-4">No builds found. Use the filters above to search.</div>
            )}

            {result && Array.isArray(result) && builds.length === 0 && (
              <div className="bg-[#0f0f23] border border-[#2a2a4a] rounded-lg p-4">
                <h3 className="text-[#00d4ff] text-sm mb-2">Raw Results</h3>
                <pre className="text-xs text-gray-300 overflow-auto">{JSON.stringify(result, null, 2)}</pre>
              </div>
            )}
          </div>
        )}

      </div>
    </div>
  );
}