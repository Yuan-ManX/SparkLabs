import React, { useState, useCallback, useRef, useEffect } from 'react';

interface AssetItem {
  id: string;
  name: string;
  type: 'sprite' | 'texture' | 'model' | 'audio' | 'script' | 'prefab' | 'scene' | 'shader';
  tags: string[];
  thumbnail?: string;
  size: string;
  modified: string;
}

const TYPE_ICONS: Record<string, { icon: string; color: string }> = {
  sprite: { icon: 'fa-image', color: '#22c55e' },
  texture: { icon: 'fa-palette', color: '#8b5cf6' },
  model: { icon: 'fa-cube', color: '#3b82f6' },
  audio: { icon: 'fa-music', color: '#f59e0b' },
  script: { icon: 'fa-code', color: '#06b6d4' },
  prefab: { icon: 'fa-puzzle-piece', color: '#ec4899' },
  scene: { icon: 'fa-film', color: '#f97316' },
  shader: { icon: 'fa-wand-magic-sparkles', color: '#ef4444' },
};

const SEED_ASSETS: AssetItem[] = [
  { id: 'a1', name: 'player_idle.png', type: 'sprite', tags: ['character', 'player'], size: '24 KB', modified: '2 min ago' },
  { id: 'a2', name: 'player_run.png', type: 'sprite', tags: ['character', 'player'], size: '48 KB', modified: '2 min ago' },
  { id: 'a3', name: 'grass_tile.png', type: 'texture', tags: ['terrain', 'tile'], size: '12 KB', modified: '5 min ago' },
  { id: 'a4', name: 'stone_tile.png', type: 'texture', tags: ['terrain', 'tile'], size: '12 KB', modified: '5 min ago' },
  { id: 'a5', name: 'hero.glb', type: 'model', tags: ['character', '3d'], size: '2.4 MB', modified: '10 min ago' },
  { id: 'a6', name: 'enemy.glb', type: 'model', tags: ['character', '3d'], size: '1.8 MB', modified: '10 min ago' },
  { id: 'a7', name: 'jump.wav', type: 'audio', tags: ['sfx', 'player'], size: '32 KB', modified: '15 min ago' },
  { id: 'a8', name: 'bgm_forest.mp3', type: 'audio', tags: ['music', 'ambient'], size: '3.2 MB', modified: '15 min ago' },
  { id: 'a9', name: 'PlayerController.js', type: 'script', tags: ['gameplay', 'player'], size: '8 KB', modified: '1 min ago' },
  { id: 'a10', name: 'EnemyAI.js', type: 'script', tags: ['gameplay', 'ai'], size: '12 KB', modified: '3 min ago' },
  { id: 'a11', name: 'Coin.prefab', type: 'prefab', tags: ['item', 'collectible'], size: '4 KB', modified: '8 min ago' },
  { id: 'a12', name: 'Level1.scene', type: 'scene', tags: ['level', 'world'], size: '56 KB', modified: '20 min ago' },
  { id: 'a13', name: 'water.shader', type: 'shader', tags: ['material', 'effect'], size: '2 KB', modified: '30 min ago' },
  { id: 'a14', name: 'skybox.png', type: 'texture', tags: ['environment', 'sky'], size: '256 KB', modified: '1 hr ago' },
];

const AssetLibrary: React.FC = () => {
  const [assets, setAssets] = useState<AssetItem[]>(SEED_ASSETS);
  const [searchQuery, setSearchQuery] = useState('');
  const [typeFilter, setTypeFilter] = useState<string>('all');
  const [viewMode, setViewMode] = useState<'grid' | 'list'>('grid');
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [dragItem, setDragItem] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const filteredAssets = assets.filter((a) => {
    if (typeFilter !== 'all' && a.type !== typeFilter) return false;
    if (searchQuery) {
      const q = searchQuery.toLowerCase();
      return a.name.toLowerCase().includes(q) || a.tags.some((t) => t.toLowerCase().includes(q));
    }
    return true;
  });

  const handleImport = useCallback(() => {
    fileInputRef.current?.click();
  }, []);

  const handleFileChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (!files) return;
    const newAssets: AssetItem[] = Array.from(files).map((file) => {
      const ext = file.name.split('.').pop()?.toLowerCase() || '';
      let type: AssetItem['type'] = 'script';
      if (['png', 'jpg', 'jpeg', 'gif', 'svg', 'webp'].includes(ext)) type = 'sprite';
      else if (['glb', 'gltf', 'fbx', 'obj'].includes(ext)) type = 'model';
      else if (['wav', 'mp3', 'ogg', 'flac'].includes(ext)) type = 'audio';
      else if (['js', 'ts', 'py', 'lua'].includes(ext)) type = 'script';
      return {
        id: `a_${Date.now()}_${Math.random().toString(36).slice(2, 6)}`,
        name: file.name,
        type,
        tags: [],
        size: `${(file.size / 1024).toFixed(0)} KB`,
        modified: 'Just now',
      };
    });
    setAssets((prev) => [...prev, ...newAssets]);
    e.target.value = '';
  }, []);

  const handleDragStart = useCallback((id: string) => {
    setDragItem(id);
  }, []);

  const handleDragEnd = useCallback(() => {
    setDragItem(null);
  }, []);

  const selectedAsset = assets.find((a) => a.id === selectedId);

  return (
    <div className="sl-panel h-full">
      <div className="sl-panel-header">
        <i className="fa-solid fa-folder-open text-[10px] text-orange-500" />
        <span className="sl-panel-header-title">Assets</span>
        <div className="sl-panel-header-actions">
          <button className="sl-panel-header-btn" onClick={handleImport} title="Import Asset">
            <i className="fa-solid fa-file-import" />
          </button>
          <button className="sl-panel-header-btn" onClick={() => setViewMode(viewMode === 'grid' ? 'list' : 'grid')} title="Toggle View">
            <i className={`fa-solid ${viewMode === 'grid' ? 'fa-list' : 'fa-grip'}`} />
          </button>
        </div>
      </div>
      <input ref={fileInputRef} type="file" multiple className="hidden" onChange={handleFileChange} />
      <div className="px-2 py-1 border-b border-[#1e1e1e] flex gap-1">
        <input
          type="text"
          placeholder="Search assets..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          className="sl-property-input flex-1"
        />
        <select
          value={typeFilter}
          onChange={(e) => setTypeFilter(e.target.value)}
          className="sl-property-input w-24"
        >
          <option value="all">All</option>
          {Object.keys(TYPE_ICONS).map((type) => (
            <option key={type} value={type}>{type.charAt(0).toUpperCase() + type.slice(1)}</option>
          ))}
        </select>
      </div>
      <div className="flex-1 overflow-y-auto p-2">
        {viewMode === 'grid' ? (
          <div className="grid grid-cols-3 gap-1.5">
            {filteredAssets.map((asset) => {
              const typeInfo = TYPE_ICONS[asset.type];
              const isSelected = selectedId === asset.id;
              return (
                <div
                  key={asset.id}
                  className={`p-2 rounded-lg cursor-pointer border transition-all ${
                    isSelected ? 'border-orange-500/40 bg-orange-500/5' : 'border-[#1e1e1e] bg-[#0d0d0d] hover:border-[#2a2a2a] hover:bg-[#161616]'
                  }`}
                  onClick={() => setSelectedId(asset.id)}
                  draggable
                  onDragStart={() => handleDragStart(asset.id)}
                  onDragEnd={handleDragEnd}
                >
                  <div className="w-full aspect-square rounded bg-[#1a1a1a] flex items-center justify-center mb-1.5">
                    <i className={`fa-solid ${typeInfo.icon} text-lg`} style={{ color: typeInfo.color }} />
                  </div>
                  <div className="text-[10px] text-[#999] truncate">{asset.name}</div>
                  <div className="text-[9px] text-[#444]">{asset.size}</div>
                </div>
              );
            })}
          </div>
        ) : (
          <div className="space-y-0.5">
            {filteredAssets.map((asset) => {
              const typeInfo = TYPE_ICONS[asset.type];
              const isSelected = selectedId === asset.id;
              return (
                <div
                  key={asset.id}
                  className={`flex items-center gap-2 px-2 py-1.5 rounded cursor-pointer transition-all ${
                    isSelected ? 'bg-orange-500/10 text-orange-400' : 'hover:bg-[#1a1a1a] text-[#999]'
                  }`}
                  onClick={() => setSelectedId(asset.id)}
                  draggable
                  onDragStart={() => handleDragStart(asset.id)}
                  onDragEnd={handleDragEnd}
                >
                  <i className={`fa-solid ${typeInfo.icon} text-[10px] w-4 text-center`} style={{ color: typeInfo.color }} />
                  <span className="flex-1 text-[11px] truncate">{asset.name}</span>
                  <span className="text-[9px] text-[#444]">{asset.size}</span>
                  <span className="text-[9px] text-[#333]">{asset.modified}</span>
                </div>
              );
            })}
          </div>
        )}
      </div>
      {selectedAsset && (
        <div className="border-t border-[#1e1e1e] px-3 py-2 bg-[#0d0d0d]">
          <div className="flex items-center gap-2 mb-1">
            <i className={`fa-solid ${TYPE_ICONS[selectedAsset.type].icon} text-[10px]`} style={{ color: TYPE_ICONS[selectedAsset.type].color }} />
            <span className="text-[11px] font-semibold text-[#ddd]">{selectedAsset.name}</span>
          </div>
          <div className="flex gap-3 text-[9px] text-[#555]">
            <span>Type: {selectedAsset.type}</span>
            <span>Size: {selectedAsset.size}</span>
            <span>Modified: {selectedAsset.modified}</span>
          </div>
          {selectedAsset.tags.length > 0 && (
            <div className="flex gap-1 mt-1">
              {selectedAsset.tags.map((tag) => (
                <span key={tag} className="sl-badge bg-[#1a1a1a] text-[#666]">{tag}</span>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default AssetLibrary;
