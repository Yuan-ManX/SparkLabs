import React, { useState, useRef, useEffect, useMemo } from 'react';
import { useEditorStore } from '../store/editorStore';
import ModelSettingsPanel from './ModelSettingsPanel';

type TransformTool = 'move' | 'rotate' | 'scale';

interface EditorToolbarProps {
  currentTool: TransformTool;
  onToolChange: (tool: TransformTool) => void;
  onAIGenerate: () => void;
  isPlaying: boolean;
  onTogglePlay: () => void;
  onModeSwitch: (mode: string) => void;
  activeMode: string;
  onGoHome?: () => void;
}

interface ModeItem {
  id: string;
  label: string;
  icon: string;
  cat?: 'agent' | 'engine' | 'creative' | 'system' | 'core';
}

interface ModeGroup {
  label: string;
  cat: 'agent' | 'engine' | 'creative' | 'system' | 'core';
  items: ModeItem[];
}

export const modeGroups: ModeGroup[] = [
  {
    label: 'Core',
    cat: 'core',
    items: [
      { id: 'dashboard', label: 'Editor', icon: 'fa-grip' },
      { id: 'ai-native-engine', label: 'AI Native Engine', icon: 'fa-microchip' },
      { id: 'agent-engine-unified', label: 'Unified Core', icon: 'fa-atom' },
    ],
  },
  {
    label: 'AI Agent Studio',
    cat: 'agent',
    items: [
      { id: 'agent-studio', label: 'Agent Studio', icon: 'fa-brain' },
      { id: 'agent-cognition', label: 'Cognition', icon: 'fa-lightbulb' },
      { id: 'agent-memory', label: 'Memory', icon: 'fa-database' },
      { id: 'agent-reasoning', label: 'Reasoning', icon: 'fa-diagram-project' },
      { id: 'agent-emotion', label: 'Emotion', icon: 'fa-heart' },
      { id: 'agent-dialogue', label: 'Dialogue', icon: 'fa-comments' },
      { id: 'agent-swarm', label: 'Swarm', icon: 'fa-sitemap' },
      { id: 'agent-testing', label: 'Auto Tester', icon: 'fa-bug-slash' },
    ],
  },
  {
    label: 'World & Environment',
    cat: 'engine',
    items: [
      { id: 'world-builder', label: 'World Builder', icon: 'fa-globe' },
      { id: 'terrain-gen', label: 'Terrain', icon: 'fa-mountain' },
      { id: 'biome-gen', label: 'Biomes', icon: 'fa-tree' },
      { id: 'weather-sim', label: 'Weather', icon: 'fa-cloud' },
      { id: 'water-sim', label: 'Water', icon: 'fa-water' },
      { id: 'ecosystem', label: 'Ecosystem', icon: 'fa-seedling' },
    ],
  },
  {
    label: 'Character & NPC',
    cat: 'creative',
    items: [
      { id: 'char-forge', label: 'Character Forge', icon: 'fa-person' },
      { id: 'npc-designer', label: 'NPC Designer', icon: 'fa-robot' },
      { id: 'personality', label: 'Personality', icon: 'fa-masks-theater' },
      { id: 'animation', label: 'Animation', icon: 'fa-person-running' },
      { id: 'voice-actor', label: 'Voice Actor', icon: 'fa-microphone' },
    ],
  },
  {
    label: 'Narrative & Story',
    cat: 'creative',
    items: [
      { id: 'narrative-engine', label: 'Narrative Engine', icon: 'fa-book-open' },
      { id: 'story-editor', label: 'Story Editor', icon: 'fa-pen-fancy' },
      { id: 'dialogue-tree', label: 'Dialogue Tree', icon: 'fa-comments' },
      { id: 'quest-designer', label: 'Quest Designer', icon: 'fa-flag' },
    ],
  },
  {
    label: 'Combat & Balance',
    cat: 'engine',
    items: [
      { id: 'combat-system', label: 'Combat System', icon: 'fa-bolt' },
      { id: 'difficulty-ai', label: 'Difficulty AI', icon: 'fa-gauge-high' },
      { id: 'economy-sim', label: 'Economy', icon: 'fa-coins' },
      { id: 'balance-opt', label: 'Balance Optimizer', icon: 'fa-scale-balanced' },
    ],
  },
  {
    label: 'Visual & Render',
    cat: 'engine',
    items: [
      { id: 'render-pipeline', label: 'Render Pipeline', icon: 'fa-microchip' },
      { id: 'lighting', label: 'Lighting', icon: 'fa-lightbulb' },
      { id: 'materials', label: 'Materials', icon: 'fa-palette' },
      { id: 'particles', label: 'Particles', icon: 'fa-fire' },
      { id: 'post-fx', label: 'Post FX', icon: 'fa-wand-sparkles' },
      { id: 'camera-ctrl', label: 'Camera', icon: 'fa-video' },
    ],
  },
  {
    label: 'Physics & Simulation',
    cat: 'engine',
    items: [
      { id: 'physics-engine', label: 'Physics Engine', icon: 'fa-atom' },
      { id: 'collision-det', label: 'Collision', icon: 'fa-bomb' },
      { id: 'fluid-sim', label: 'Fluid', icon: 'fa-droplet' },
      { id: 'cloth-sim', label: 'Cloth', icon: 'fa-shirt' },
      { id: 'ik-system', label: 'Inverse Kinematics', icon: 'fa-bone' },
    ],
  },
  {
    label: 'Audio & Music',
    cat: 'engine',
    items: [
      { id: 'audio-engine', label: 'Audio Engine', icon: 'fa-volume-high' },
      { id: 'music-gen', label: 'Music Gen', icon: 'fa-music' },
      { id: 'sfx-gen', label: 'SFX Gen', icon: 'fa-bell' },
      { id: 'voice-synth', label: 'Voice Synth', icon: 'fa-microphone-lines' },
    ],
  },
  {
    label: 'Asset & Pipeline',
    cat: 'system',
    items: [
      { id: 'asset-gen', label: 'Asset Generator', icon: 'fa-folder-open' },
      { id: 'asset-sync', label: 'Asset Synthesizer', icon: 'fa-wand-magic-sparkles' },
      { id: 'import-export', label: 'Import / Export', icon: 'fa-file-import' },
      { id: 'build-pipeline', label: 'Build Pipeline', icon: 'fa-arrows-spin' },
    ],
  },
  {
    label: 'Testing & QA',
    cat: 'system',
    items: [
      { id: 'qa-dashboard', label: 'QA Dashboard', icon: 'fa-clipboard-check' },
      { id: 'playtest-sim', label: 'Playtest Sim', icon: 'fa-gamepad' },
      { id: 'bug-hunter', label: 'Bug Hunter', icon: 'fa-bug' },
      { id: 'perf-monitor', label: 'Performance', icon: 'fa-gauge' },
      { id: 'security-scan', label: 'Security', icon: 'fa-shield' },
    ],
  },
  {
    label: 'System & Tools',
    cat: 'system',
    items: [
      { id: 'node-editor', label: 'Node Editor', icon: 'fa-diagram-project' },
      { id: 'signal-bus', label: 'Signal Bus', icon: 'fa-tower-broadcast' },
      { id: 'state-machine', label: 'State Machine', icon: 'fa-sitemap' },
      { id: 'visual-script', label: 'Visual Script', icon: 'fa-code' },
      { id: 'event-system', label: 'Event System', icon: 'fa-bolt' },
      { id: 'llm-router', label: 'LLM Router', icon: 'fa-route' },
    ],
  },
];

const categoryConfig: Record<string, { label: string; color: string; icon: string }> = {
  core: { label: 'Core', color: 'text-[#e2e8f0]', icon: 'fa-cube' },
  agent: { label: 'AI Agents', color: 'text-orange-500', icon: 'fa-brain' },
  engine: { label: 'Game Engine', color: 'text-sky-400', icon: 'fa-microchip' },
  creative: { label: 'Creative Tools', color: 'text-purple-400', icon: 'fa-wand-magic-sparkles' },
  system: { label: 'System & Testing', color: 'text-green-400', icon: 'fa-gear' },
};

const EditorToolbar: React.FC<EditorToolbarProps> = ({
  currentTool,
  onToolChange,
  onAIGenerate,
  isPlaying,
  onTogglePlay,
  onModeSwitch,
  activeMode,
  onGoHome,
}) => {
  const [showModeMenu, setShowModeMenu] = useState(false);
  const [showFileMenu, setShowFileMenu] = useState(false);
  const [showViewMenu, setShowViewMenu] = useState(false);
  const [modeSearch, setModeSearch] = useState('');
  const [activeCategory, setActiveCategory] = useState<string>('all');
  const [showSettings, setShowSettings] = useState(false);
  const modeMenuRef = useRef<HTMLDivElement>(null);
  const searchRef = useRef<HTMLInputElement>(null);

  // Right sidebar collapse state from editor store
  const rightPanelCollapsed = useEditorStore((s) => s.rightPanelCollapsed);
  const setRightPanelCollapsed = useEditorStore((s) => s.setRightPanelCollapsed);

  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (modeMenuRef.current && !modeMenuRef.current.contains(e.target as Node)) {
        setShowModeMenu(false);
        setShowFileMenu(false);
        setShowViewMenu(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  useEffect(() => {
    if (showModeMenu && searchRef.current) {
      searchRef.current.focus();
    }
  }, [showModeMenu]);

  const closeAllMenus = () => {
    setShowModeMenu(false);
    setShowFileMenu(false);
    setShowViewMenu(false);
    setModeSearch('');
    setActiveCategory('all');
  };

  const activeModeItem = modeGroups.flatMap((g) => g.items).find((i) => i.id === activeMode);

  const filteredGroups = useMemo(() => {
    const search = modeSearch.toLowerCase().trim();
    return modeGroups
      .filter((g) => activeCategory === 'all' || g.cat === activeCategory)
      .map((g) => ({
        ...g,
        items: g.items.filter((i) =>
          !search || i.label.toLowerCase().includes(search) || i.id.toLowerCase().includes(search)
        ),
      }))
      .filter((g) => g.items.length > 0);
  }, [modeSearch, activeCategory]);

  const totalModes = modeGroups.reduce((sum, g) => sum + g.items.length, 0);

  return (
    <div className="h-10 bg-[#0d0d0d] border-b border-[#1e1e1e] flex items-center px-2 gap-1 shrink-0">
      <div className="flex items-center gap-2 mr-2 cursor-pointer" onClick={onGoHome}>
        <div className="w-[22px] h-[22px] bg-gradient-to-br from-orange-500 to-red-600 rounded-md flex items-center justify-center">
          <i className="fa-solid fa-fire text-white text-[10px]" />
        </div>
        <span className="font-bold text-[13px]">
          <span className="bg-gradient-to-r from-orange-500 via-red-500 to-yellow-400 bg-clip-text text-transparent">Spark</span>
          <span className="text-[#e0e0e0]">Labs</span>
        </span>
      </div>

      <div className="w-px h-5 bg-[#1e1e1e]" />

      <div className="relative">
        <button
          onClick={() => { closeAllMenus(); setShowFileMenu(!showFileMenu); }}
          className="px-2 py-1 text-[11px] text-[#777] hover:text-[#ccc] hover:bg-[#1a1a1a] rounded transition-colors"
        >
          File
        </button>
        {showFileMenu && (
          <div className="absolute top-full left-0 mt-1 bg-[#161616] border border-[#2a2a2a] rounded-lg py-1 z-50 min-w-[160px] shadow-xl">
            <button className="w-full text-left px-3 py-1.5 text-[11px] text-[#999] hover:bg-[#222] flex items-center gap-2">
              <i className="fa-solid fa-file-circle-plus text-[9px] text-[#555] w-4" /> New Project
            </button>
            <button className="w-full text-left px-3 py-1.5 text-[11px] text-[#999] hover:bg-[#222] flex items-center gap-2">
              <i className="fa-solid fa-folder-open text-[9px] text-[#555] w-4" /> Open Project
            </button>
            <button className="w-full text-left px-3 py-1.5 text-[11px] text-[#999] hover:bg-[#222] flex items-center gap-2">
              <i className="fa-solid fa-floppy-disk text-[9px] text-[#555] w-4" /> Save
            </button>
            <div className="border-t border-[#2a2a2a] my-1" />
            <button className="w-full text-left px-3 py-1.5 text-[11px] text-[#999] hover:bg-[#222] flex items-center gap-2">
              <i className="fa-solid fa-file-export text-[9px] text-[#555] w-4" /> Export Game
            </button>
          </div>
        )}
      </div>

      <button className="px-2 py-1 text-[11px] text-[#777] hover:text-[#ccc] hover:bg-[#1a1a1a] rounded transition-colors">
        Edit
      </button>

      <div className="relative">
        <button
          onClick={() => { closeAllMenus(); setShowViewMenu(!showViewMenu); }}
          className="px-2 py-1 text-[11px] text-[#777] hover:text-[#ccc] hover:bg-[#1a1a1a] rounded transition-colors"
        >
          View
        </button>
        {showViewMenu && (
          <div className="absolute top-full left-0 mt-1 bg-[#161616] border border-[#2a2a2a] rounded-lg py-1 z-50 min-w-[160px] shadow-xl">
            <button className="w-full text-left px-3 py-1.5 text-[11px] text-[#999] hover:bg-[#222] flex items-center gap-2">
              <i className="fa-solid fa-sitemap text-[9px] text-[#555] w-4" /> Scene Hierarchy
            </button>
            <button className="w-full text-left px-3 py-1.5 text-[11px] text-[#999] hover:bg-[#222] flex items-center gap-2">
              <i className="fa-solid fa-sliders text-[9px] text-[#555] w-4" /> Inspector
            </button>
            <button className="w-full text-left px-3 py-1.5 text-[11px] text-[#999] hover:bg-[#222] flex items-center gap-2">
              <i className="fa-solid fa-terminal text-[9px] text-[#555] w-4" /> Console
            </button>
            <button className="w-full text-left px-3 py-1.5 text-[11px] text-[#999] hover:bg-[#222] flex items-center gap-2">
              <i className="fa-solid fa-diagram-project text-[9px] text-[#555] w-4" /> Node Graph
            </button>
          </div>
        )}
      </div>

      <div className="w-px h-5 bg-[#1e1e1e]" />

      {(['move', 'rotate', 'scale'] as TransformTool[]).map((tool) => (
        <button
          key={tool}
          onClick={() => onToolChange(tool)}
          className={`flex items-center gap-1 px-2 py-1 rounded text-[11px] transition-all ${
            currentTool === tool
              ? 'bg-orange-500/12 border border-orange-500/30 text-orange-500'
              : 'border border-transparent text-[#666] hover:bg-[#1a1a1a] hover:text-[#aaa]'
          }`}
        >
          <i className={`fa-solid ${
            tool === 'move' ? 'fa-arrows-up-down-left-right' :
            tool === 'rotate' ? 'fa-rotate' : 'fa-expand'
          } text-[9px]`} />
          <span className="hidden lg:inline">{tool.charAt(0).toUpperCase() + tool.slice(1)}</span>
        </button>
      ))}

      <div className="w-px h-5 bg-[#1e1e1e]" />

      {/* Mode selector with search */}
      <div className="relative" ref={modeMenuRef}>
        <button
          onClick={() => { closeAllMenus(); setShowModeMenu(!showModeMenu); }}
          className="flex items-center gap-1.5 px-2 py-1 text-[11px] text-[#999] hover:text-[#ddd] hover:bg-[#1a1a1a] rounded transition-colors"
        >
          {activeModeItem ? (
            <>
              <i className={`fa-solid ${activeModeItem.icon} text-[9px] text-orange-500`} />
              <span>{activeModeItem.label}</span>
            </>
          ) : (
            <>
              <i className="fa-solid fa-layer-group text-[9px]" />
              <span>Modules</span>
            </>
          )}
          <i className="fa-solid fa-chevron-down text-[7px] text-[#555]" />
        </button>
        {showModeMenu && (
          <div className="absolute top-full left-0 mt-1 bg-[#0d0d0d] border border-[#222] rounded-lg z-50 w-[420px] shadow-2xl">
            {/* Search bar */}
            <div className="p-2.5 border-b border-[#1a1a1a]">
              <div className="relative">
                <i className="fa-solid fa-magnifying-glass absolute left-3 top-1/2 -translate-y-1/2 text-[10px] text-[#444]" />
                <input
                  ref={searchRef}
                  type="text"
                  value={modeSearch}
                  onChange={(e) => setModeSearch(e.target.value)}
                  placeholder={`Search ${totalModes} modules...`}
                  className="w-full bg-[#0a0a0a] border border-[#1e1e1e] rounded-lg pl-8 pr-3 py-1.5 text-[11px] text-[#ccc] placeholder-[#444] outline-none focus:border-orange-900/40"
                />
              </div>
              {/* Category tabs */}
              <div className="flex items-center gap-1 mt-2">
                <button
                  onClick={() => setActiveCategory('all')}
                  className={`px-2 py-0.5 rounded text-[9px] font-medium transition-colors ${
                    activeCategory === 'all' ? 'bg-[#222] text-[#ddd]' : 'text-[#555] hover:text-[#777]'
                  }`}
                >
                  All
                </button>
                {Object.entries(categoryConfig).map(([key, cfg]) => (
                  <button
                    key={key}
                    onClick={() => setActiveCategory(key)}
                    className={`px-2 py-0.5 rounded text-[9px] font-medium transition-colors flex items-center gap-1 ${
                      activeCategory === key ? 'bg-[#222] text-[#ddd]' : 'text-[#555] hover:text-[#777]'
                    }`}
                  >
                    <i className={`fa-solid ${cfg.icon} text-[7px]`} />
                    {cfg.label}
                  </button>
                ))}
              </div>
            </div>
            {/* Results */}
            <div className="max-h-[60vh] overflow-y-auto p-1.5">
              {filteredGroups.length === 0 ? (
                <div className="py-8 text-center text-[11px] text-[#444]">
                  <i className="fa-solid fa-magnifying-glass-minus text-lg mb-2 opacity-30" />
                  <div>No modules found for "{modeSearch}"</div>
                </div>
              ) : (
                filteredGroups.map((group) => {
                  const cfg = categoryConfig[group.cat] || categoryConfig.system;
                  return (
                    <div key={group.label} className="mb-1">
                      <div className="flex items-center gap-1.5 px-2 py-1">
                        <i className={`fa-solid ${cfg.icon} text-[8px] ${cfg.color}`} />
                        <span className="text-[9px] font-bold text-[#555] uppercase tracking-wider">{group.label}</span>
                        <span className="text-[8px] text-[#333]">({group.items.length})</span>
                      </div>
                      <div className="grid grid-cols-2 gap-0.5">
                        {group.items.map((item) => (
                          <button
                            key={item.id}
                            onClick={() => { onModeSwitch(item.id); closeAllMenus(); }}
                            className={`flex items-center gap-2 px-2 py-1.5 rounded text-[10px] transition-colors text-left ${
                              activeMode === item.id
                                ? 'bg-orange-500/10 text-orange-500 border border-orange-500/20'
                                : 'text-[#888] hover:bg-[#141414] border border-transparent'
                            }`}
                          >
                            <i className={`fa-solid ${item.icon} text-[9px] ${activeMode === item.id ? 'text-orange-500' : 'text-[#555]'} flex-shrink-0 w-3 text-center`} />
                            <span className="truncate">{item.label}</span>
                          </button>
                        ))}
                      </div>
                    </div>
                  );
                })
              )}
            </div>
          </div>
        )}
      </div>

      <div className="flex-1" />

      <button
        onClick={() => { if (!isPlaying) onTogglePlay(); }}
        className="flex items-center gap-1.5 px-3 py-1.5 rounded-md text-[11px] font-semibold text-white hover:opacity-90 hover:-translate-y-px transition-all bg-gradient-to-r from-green-500 to-green-600"
      >
        <i className="fa-solid fa-play text-[9px]" />
        Play Game
      </button>

      <button
        onClick={() => { if (isPlaying) onTogglePlay(); }}
        className="flex items-center gap-1.5 px-3 py-1.5 bg-gradient-to-r from-orange-500 to-red-600 text-white rounded-md text-[11px] font-semibold hover:opacity-90 hover:-translate-y-px transition-all"
      >
        <i className="fa-solid fa-stop text-[9px]" />
        <span className="hidden md:inline">Stop Game</span>
      </button>

      <div className="w-px h-5 bg-[#1e1e1e]" />

      {/* Model API Settings button */}
      <button
        onClick={() => setShowSettings(true)}
        className="w-7 h-7 rounded-md bg-[#1a1a1a] hover:bg-[#222] flex items-center justify-center text-[#888] hover:text-orange-500 cursor-pointer transition-colors"
        title="Model API Settings"
      >
        <i className="fa-solid fa-sliders text-[10px]" />
      </button>

      {/* Right sidebar toggle — collapses/expands the inspector panel */}
      <button
        onClick={() => setRightPanelCollapsed(!rightPanelCollapsed)}
        className="w-7 h-7 rounded-md bg-[#1a1a1a] hover:bg-[#222] flex items-center justify-center text-[#888] hover:text-orange-500 cursor-pointer transition-colors"
        title={rightPanelCollapsed ? 'Show Inspector Panel' : 'Hide Inspector Panel'}
      >
        <i className={`fa-solid ${rightPanelCollapsed ? 'fa-chevron-left' : 'fa-chevron-right'} text-[9px]`} />
      </button>

      {showSettings && <ModelSettingsPanel onClose={() => setShowSettings(false)} />}
    </div>
  );
};

export default EditorToolbar;
