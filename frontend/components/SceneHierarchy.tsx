import React, { useState } from 'react';

interface SceneEntity {
  id: string;
  name: string;
  icon: string;
  iconColor: string;
}

const defaultEntities: SceneEntity[] = [
  { id: 'camera', name: 'Main Camera', icon: 'fa-video', iconColor: '#4ade80' },
  { id: 'light', name: 'Directional Light', icon: 'fa-sun', iconColor: '#fbbf24' },
  { id: 'ai-core', name: 'AI Core', icon: 'fa-microchip', iconColor: '#f97316' },
  { id: 'neural-net', name: 'Neural Network', icon: 'fa-circle-nodes', iconColor: '#f97316' },
  { id: 'terrain', name: 'Terrain', icon: 'fa-mountain', iconColor: '#4ade80' },
  { id: 'player-spawn', name: 'Player Spawn', icon: 'fa-location-dot', iconColor: '#60a5fa' },
  { id: 'npc', name: 'AI Agent - NPC', icon: 'fa-robot', iconColor: '#c084fc' },
  { id: 'environment', name: 'Environment', icon: 'fa-tree', iconColor: '#4ade80' },
];

interface SceneHierarchyProps {
  selectedEntity: string | null;
  onSelectEntity: (id: string, name: string) => void;
  onAddEntity: () => void;
  entities: SceneEntity[];
}

const SceneHierarchy: React.FC<SceneHierarchyProps> = ({
  selectedEntity,
  onSelectEntity,
  onAddEntity,
  entities,
}) => {
  const [activeTab, setActiveTab] = useState<'scene' | 'assets'>('scene');

  return (
    <div className="flex flex-col overflow-hidden bg-[#111] border-r border-[#1e1e1e]">
      <div className="flex items-center gap-1.5 px-3 py-2 bg-[#161616] border-b border-[#1e1e1e] text-[11px] font-semibold uppercase tracking-wider text-[#888]">
        <i className="fa-solid fa-sitemap text-orange-500 text-[10px]" />
        Scene Hierarchy
      </div>

      <div className="flex border-b border-[#1e1e1e]">
        <button
          onClick={() => setActiveTab('scene')}
          className={`px-3.5 py-1.5 text-[11px] cursor-pointer border-b-2 transition-colors ${
            activeTab === 'scene' ? 'text-orange-500 border-orange-500' : 'text-[#666] border-transparent hover:text-[#aaa]'
          }`}
        >
          Scene
        </button>
        <button
          onClick={() => setActiveTab('assets')}
          className={`px-3.5 py-1.5 text-[11px] cursor-pointer border-b-2 transition-colors ${
            activeTab === 'assets' ? 'text-orange-500 border-orange-500' : 'text-[#666] border-transparent hover:text-[#aaa]'
          }`}
        >
          Assets
        </button>
      </div>

      {activeTab === 'scene' ? (
        <>
          <div className="flex-1 overflow-y-auto py-1">
            {entities.map((entity) => (
              <div
                key={entity.id}
                onClick={() => onSelectEntity(entity.id, entity.name)}
                className={`flex items-center gap-2 px-2.5 py-1.5 text-[12px] cursor-pointer border-l-2 transition-all ${
                  selectedEntity === entity.id
                    ? 'bg-orange-500/8 border-l-orange-500 text-orange-500'
                    : 'border-l-transparent hover:bg-[#1a1a1a] text-[#ccc]'
                }`}
              >
                <i className={`fa-solid ${entity.icon} text-[10px]`} style={{ color: entity.iconColor }} />
                <span>{entity.name}</span>
              </div>
            ))}
          </div>

          <div className="p-2 border-t border-[#1e1e1e]">
            <button
              onClick={onAddEntity}
              className="w-full flex items-center justify-center gap-1 py-1.5 text-[11px] font-medium text-orange-500 border border-orange-500/30 rounded-md hover:bg-orange-500/10 hover:border-orange-500/50 transition-all"
            >
              <i className="fa-solid fa-plus" />
              Add Entity
            </button>
          </div>
        </>
      ) : (
        <div className="flex-1 overflow-y-auto p-3">
          <div className="grid grid-cols-2 gap-2">
            {['Materials', 'Textures', 'Meshes', 'Scripts', 'Audio', 'Prefabs'].map((cat) => (
              <div
                key={cat}
                className="bg-[#161616] border border-[#222] rounded-lg p-2 cursor-pointer hover:border-orange-500/30 hover:bg-[#1a1a1a] transition-all"
              >
                <div className="text-[10px] text-[#888] uppercase tracking-wider mb-1">{cat}</div>
                <div className="text-[11px] text-[#ccc]">0 items</div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

export default SceneHierarchy;
export type { SceneEntity };
