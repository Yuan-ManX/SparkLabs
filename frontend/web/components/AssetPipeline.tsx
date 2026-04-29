import React, { useState, useEffect, useCallback } from 'react';
import { assetApi } from '../utils/api';

type TabType = 'assets' | 'collections' | 'pipelines';

const CATEGORY_COLORS: Record<string, string> = {
  sprite: '#f59e0b',
  texture: '#22c55e',
  model_3d: '#3b82f6',
  audio: '#ec4899',
  music: '#8b5cf6',
  font: '#06b6d4',
  shader: '#ef4444',
  animation: '#f97316',
  particle: '#84cc16',
  ui: '#14b8a6',
  data: '#6366f1',
  scene: '#eab308',
  script: '#a855f7',
  prefab: '#64748b',
};

const STATUS_COLORS: Record<string, string> = {
  imported: '#3b82f6',
  processing: '#f59e0b',
  ready: '#22c55e',
  error: '#ef4444',
  deprecated: '#6b7280',
  archived: '#9ca3af',
};

const AssetPipeline: React.FC = () => {
  const [activeTab, setActiveTab] = useState<TabType>('assets');
  const [assets, setAssets] = useState<any[]>([]);
  const [collections, setCollections] = useState<any[]>([]);
  const [pipelines, setPipelines] = useState<any[]>([]);
  const [selectedAsset, setSelectedAsset] = useState<any>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [filterCategory, setFilterCategory] = useState('');
  const [stats, setStats] = useState<any>(null);
  const [loading, setLoading] = useState(false);

  const loadAssets = useCallback(async () => {
    setLoading(true);
    try {
      const res = await assetApi.listAssets(filterCategory || undefined);
      setAssets((res as any)?.assets || (res as any) || []);
    } catch (e) { /* ignore */ }
    setLoading(false);
  }, [filterCategory]);

  const loadCollections = useCallback(async () => {
    try {
      const res = await assetApi.listCollections();
      setCollections((res as any)?.collections || (res as any) || []);
    } catch (e) { /* ignore */ }
  }, []);

  const loadPipelines = useCallback(async () => {
    try {
      const res = await assetApi.listPipelines();
      setPipelines((res as any)?.pipelines || (res as any) || []);
    } catch (e) { /* ignore */ }
  }, []);

  const loadStats = useCallback(async () => {
    try {
      const res = await assetApi.stats();
      setStats(res);
    } catch (e) { /* ignore */ }
  }, []);

  useEffect(() => {
    loadAssets();
    loadCollections();
    loadPipelines();
    loadStats();
  }, [loadAssets, loadCollections, loadPipelines, loadStats]);

  const handleSearch = async () => {
    if (!searchQuery.trim()) return;
    setLoading(true);
    try {
      const res = await assetApi.search(searchQuery);
      setAssets((res as any)?.assets || (res as any) || []);
    } catch (e) { /* ignore */ }
    setLoading(false);
  };

  const handleSelectAsset = async (id: string) => {
    try {
      const asset = await assetApi.getAsset(id);
      setSelectedAsset(asset);
    } catch (e) { /* ignore */ }
  };

  const formatSize = (bytes: number) => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1048576) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / 1048576).toFixed(1)} MB`;
  };

  const tabs: { key: TabType; label: string; icon: string }[] = [
    { key: 'assets', label: 'Assets', icon: 'fa-image' },
    { key: 'collections', label: 'Collections', icon: 'fa-folder' },
    { key: 'pipelines', label: 'Pipelines', icon: 'fa-gears' },
  ];

  return (
    <div className="h-full flex flex-col bg-[#111] text-[#e0e0e0]">
      <div className="flex items-center gap-1 px-4 py-2 border-b border-[#1e1e1e]">
        {tabs.map(tab => (
          <button
            key={tab.key}
            onClick={() => setActiveTab(tab.key)}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded text-[11px] transition-colors ${
              activeTab === tab.key
                ? 'bg-orange-500/15 text-orange-500 border border-orange-500/30'
                : 'text-[#888] hover:text-[#ccc] hover:bg-[#1a1a1a]'
            }`}
          >
            <i className={`fa-solid ${tab.icon} text-[10px]`} />
            {tab.label}
          </button>
        ))}
        <div className="flex-1" />
        {stats && (
          <div className="flex items-center gap-3 text-[10px] text-[#666]">
            <span>{stats.total_assets || 0} assets</span>
            <span>{formatSize(stats.total_size_bytes || 0)}</span>
          </div>
        )}
      </div>

      <div className="flex-1 flex overflow-hidden">
        <div className="w-72 border-r border-[#1e1e1e] overflow-y-auto">
          {activeTab === 'assets' && (
            <div className="p-3 border-b border-[#1e1e1e]">
              <div className="flex gap-1.5">
                <input
                  type="text"
                  value={searchQuery}
                  onChange={e => setSearchQuery(e.target.value)}
                  onKeyDown={e => e.key === 'Enter' && handleSearch()}
                  placeholder="Search assets..."
                  className="flex-1 bg-[#1a1a1a] border border-[#2a2a2a] rounded px-2.5 py-1.5 text-[11px] text-[#e0e0e0] placeholder-[#555] focus:border-orange-500/50 focus:outline-none"
                />
                <button onClick={handleSearch} className="px-2.5 py-1.5 bg-orange-500/15 text-orange-500 rounded text-[11px]">
                  <i className="fa-solid fa-magnifying-glass text-[10px]" />
                </button>
              </div>
              <select
                value={filterCategory}
                onChange={e => setFilterCategory(e.target.value)}
                className="w-full mt-2 bg-[#1a1a1a] border border-[#2a2a2a] rounded px-2 py-1 text-[10px] text-[#999] focus:outline-none"
              >
                <option value="">All Categories</option>
                {Object.keys(CATEGORY_COLORS).map(c => (
                  <option key={c} value={c}>{c.replace('_', ' ')}</option>
                ))}
              </select>
            </div>
          )}

          <div className="p-2">
            {loading ? (
              <div className="text-[#555] text-[11px] text-center py-6">Loading...</div>
            ) : activeTab === 'assets' ? (
              assets.map((asset: any) => {
                const catColor = CATEGORY_COLORS[asset.category] || '#666';
                const statusColor = STATUS_COLORS[asset.status] || '#666';
                return (
                  <div
                    key={asset.id}
                    onClick={() => handleSelectAsset(asset.id)}
                    className={`p-2.5 rounded-lg mb-1.5 cursor-pointer transition-colors ${
                      selectedAsset?.id === asset.id ? 'bg-orange-500/10 border border-orange-500/30' : 'bg-[#1a1a1a] hover:bg-[#222] border border-transparent'
                    }`}
                  >
                    <div className="flex items-center gap-1.5">
                      <div className="w-2 h-2 rounded-full" style={{ backgroundColor: catColor }} />
                      <span className="text-[11px] font-medium flex-1 truncate">{asset.name}</span>
                    </div>
                    <div className="flex items-center gap-1.5 mt-0.5">
                      <span className="text-[9px]" style={{ color: statusColor }}>{asset.status}</span>
                      <span className="text-[9px] text-[#555]">· {asset.format}</span>
                      <span className="text-[9px] text-[#555]">· {formatSize(asset.size_bytes)}</span>
                    </div>
                  </div>
                );
              })
            ) : activeTab === 'collections' ? (
              collections.map((col: any) => (
                <div key={col.id} className="p-2.5 rounded-lg mb-1.5 bg-[#1a1a1a] border border-transparent">
                  <div className="text-[11px] font-medium">{col.name}</div>
                  <div className="text-[10px] text-[#666] mt-0.5">{col.asset_count} assets</div>
                </div>
              ))
            ) : (
              pipelines.map((pipe: any) => (
                <div key={pipe.id} className="p-2.5 rounded-lg mb-1.5 bg-[#1a1a1a] border border-transparent">
                  <div className="text-[11px] font-medium">{pipe.name}</div>
                  <div className="text-[10px] text-[#666] mt-0.5">{pipe.steps?.length || 0} steps · {pipe.status}</div>
                </div>
              ))
            )}
          </div>
        </div>

        <div className="flex-1 overflow-y-auto p-4">
          {selectedAsset ? (
            <div className="space-y-4">
              <div>
                <div className="flex items-center gap-2">
                  <div className="w-3 h-3 rounded-full" style={{ backgroundColor: CATEGORY_COLORS[selectedAsset.category] || '#666' }} />
                  <h3 className="text-[14px] font-bold">{selectedAsset.name}</h3>
                </div>
                <div className="flex items-center gap-2 mt-1">
                  <span className="text-[10px]" style={{ color: STATUS_COLORS[selectedAsset.status] || '#666' }}>{selectedAsset.status}</span>
                  <span className="text-[10px] text-[#555]">{selectedAsset.category} · {selectedAsset.format}</span>
                </div>
              </div>

              <div className="grid grid-cols-3 gap-3">
                <div className="bg-[#0a0a0a] rounded-lg border border-[#2a2a2a] p-3">
                  <div className="text-[10px] text-[#666] mb-1">Size</div>
                  <div className="text-[14px] font-bold text-blue-400">{formatSize(selectedAsset.size_bytes)}</div>
                </div>
                <div className="bg-[#0a0a0a] rounded-lg border border-[#2a2a2a] p-3">
                  <div className="text-[10px] text-[#666] mb-1">Dimensions</div>
                  <div className="text-[14px] font-bold text-green-400">
                    {selectedAsset.width && selectedAsset.height
                      ? `${selectedAsset.width}×${selectedAsset.height}`
                      : 'N/A'}
                  </div>
                </div>
                <div className="bg-[#0a0a0a] rounded-lg border border-[#2a2a2a] p-3">
                  <div className="text-[10px] text-[#666] mb-1">Version</div>
                  <div className="text-[14px] font-bold text-purple-400">v{selectedAsset.version}</div>
                </div>
              </div>

              <div className="bg-[#0a0a0a] rounded-lg border border-[#2a2a2a] p-3">
                <h4 className="text-[11px] font-semibold text-[#999] mb-1.5">Path</h4>
                <code className="text-[11px] text-[#ccc] bg-[#151515] px-2 py-1 rounded">{selectedAsset.path}</code>
              </div>

              {selectedAsset.tags && selectedAsset.tags.length > 0 && (
                <div className="flex flex-wrap gap-1">
                  {selectedAsset.tags.map((tag: string) => (
                    <span key={tag} className="text-[9px] px-2 py-0.5 bg-[#1a1a1a] border border-[#2a2a2a] rounded text-[#888]">
                      {tag}
                    </span>
                  ))}
                </div>
              )}

              {selectedAsset.dependencies && selectedAsset.dependencies.length > 0 && (
                <div className="bg-[#0a0a0a] rounded-lg border border-[#2a2a2a] p-3">
                  <h4 className="text-[11px] font-semibold text-[#999] mb-2">Dependencies ({selectedAsset.dependencies.length})</h4>
                  <div className="space-y-1">
                    {selectedAsset.dependencies.map((dep: string) => (
                      <div key={dep} className="flex items-center gap-2 p-1.5 bg-[#151515] rounded text-[10px]">
                        <i className="fa-solid fa-arrow-right text-[8px] text-[#555]" />
                        <span className="text-[#888]">{dep}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          ) : (
            <div className="flex items-center justify-center h-full text-[#555] text-[12px]">
              <div className="text-center">
                <i className="fa-solid fa-image text-[32px] mb-3 text-[#333]" />
                <p>Select an asset to view details</p>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default AssetPipeline;
