import React, { useState, useMemo, useEffect } from 'react';

// A single tab within a hub
interface HubTab {
  modeId: string;
  label: string;
  icon: string;
}

// Configuration for each hub
interface HubConfig {
  title: string;
  icon: string;
  tabs: HubTab[];
}

// All hub configurations - maps hub IDs to their tab layouts
const HUB_CONFIGS: Record<string, HubConfig> = {
  'agent-hub': {
    title: 'AI Agent Hub',
    icon: 'fa-brain',
    tabs: [
      { modeId: 'agent-studio', label: 'Studio', icon: 'fa-brain' },
      { modeId: 'agent-cognition', label: 'Cognition', icon: 'fa-lightbulb' },
      { modeId: 'agent-memory', label: 'Memory', icon: 'fa-database' },
      { modeId: 'agent-reasoning', label: 'Reasoning', icon: 'fa-diagram-project' },
      { modeId: 'agent-emotion', label: 'Emotion', icon: 'fa-heart' },
      { modeId: 'agent-dialogue', label: 'Dialogue', icon: 'fa-comments' },
      { modeId: 'agent-swarm', label: 'Swarm', icon: 'fa-sitemap' },
      { modeId: 'agent-testing', label: 'Tester', icon: 'fa-bug-slash' },
      { modeId: 'conductor-intelligence', label: 'Conductor', icon: 'fa-wand-magic-sparkles' },
      { modeId: 'ai-game-studio', label: 'Game Studio', icon: 'fa-users-gear' },
      { modeId: 'game-mutator', label: 'Mutator', icon: 'fa-dna' },
      { modeId: 'game-critic', label: 'Critic', icon: 'fa-star-half-stroke' },
      { modeId: 'game-healer', label: 'Healer', icon: 'fa-heart-pulse' },
      { modeId: 'game-evolver', label: 'Evolver', icon: 'fa-dna' },
      { modeId: 'game-composer', label: 'Composer', icon: 'fa-music' },
      { modeId: 'game-analytics', label: 'Analytics', icon: 'fa-chart-line' },
      { modeId: 'game-fusion', label: 'Fusion', icon: 'fa-code-merge' },
      { modeId: 'game-polish', label: 'Polish', icon: 'fa-wand-magic-sparkles' },
      { modeId: 'game-publisher', label: 'Publisher', icon: 'fa-rocket' },
      { modeId: 'game-sentinel', label: 'Sentinel', icon: 'fa-shield-halved' },
    ],
  },
  'world-hub': {
    title: 'World Hub',
    icon: 'fa-globe',
    tabs: [
      { modeId: 'world-builder', label: 'World Builder', icon: 'fa-globe' },
      { modeId: 'terrain-gen', label: 'Terrain', icon: 'fa-mountain' },
      { modeId: 'biome-gen', label: 'Biomes', icon: 'fa-tree' },
      { modeId: 'weather-sim', label: 'Weather', icon: 'fa-cloud' },
      { modeId: 'water-sim', label: 'Water', icon: 'fa-water' },
      { modeId: 'ecosystem', label: 'Ecosystem', icon: 'fa-seedling' },
      { modeId: 'reality-bubble', label: 'Reality Bubble', icon: 'fa-atom' },
      { modeId: 'semantic-indexer', label: 'Semantic Index', icon: 'fa-diagram-project' },
    ],
  },
  'character-hub': {
    title: 'Character Hub',
    icon: 'fa-person',
    tabs: [
      { modeId: 'char-forge', label: 'Forge', icon: 'fa-person' },
      { modeId: 'npc-designer', label: 'NPC Designer', icon: 'fa-robot' },
      { modeId: 'personality', label: 'Personality', icon: 'fa-masks-theater' },
      { modeId: 'animation', label: 'Animation', icon: 'fa-person-running' },
      { modeId: 'voice-actor', label: 'Voice', icon: 'fa-microphone' },
    ],
  },
  'narrative-hub': {
    title: 'Narrative Hub',
    icon: 'fa-book-open',
    tabs: [
      { modeId: 'narrative-engine', label: 'Engine', icon: 'fa-book-open' },
      { modeId: 'story-director', label: 'Director', icon: 'fa-clapperboard' },
      { modeId: 'frame-architect', label: 'Frames', icon: 'fa-video' },
      { modeId: 'story-editor', label: 'Editor', icon: 'fa-pen-fancy' },
      { modeId: 'dialogue-tree', label: 'Dialogue', icon: 'fa-comments' },
      { modeId: 'quest-designer', label: 'Quests', icon: 'fa-flag' },
    ],
  },
  'game-systems-hub': {
    title: 'Game Systems',
    icon: 'fa-bolt',
    tabs: [
      { modeId: 'combat-system', label: 'Combat', icon: 'fa-bolt' },
      { modeId: 'difficulty-ai', label: 'Difficulty', icon: 'fa-gauge-high' },
      { modeId: 'economy-sim', label: 'Economy', icon: 'fa-coins' },
      { modeId: 'balance-opt', label: 'Balance', icon: 'fa-scale-balanced' },
    ],
  },
  'render-hub': {
    title: 'Render Hub',
    icon: 'fa-microchip',
    tabs: [
      { modeId: 'render-pipeline', label: 'Pipeline', icon: 'fa-microchip' },
      { modeId: 'lighting', label: 'Lighting', icon: 'fa-lightbulb' },
      { modeId: 'materials', label: 'Materials', icon: 'fa-palette' },
      { modeId: 'particles', label: 'Particles', icon: 'fa-fire' },
      { modeId: 'post-fx', label: 'Post FX', icon: 'fa-wand-sparkles' },
      { modeId: 'camera-ctrl', label: 'Camera', icon: 'fa-video' },
    ],
  },
  'physics-hub': {
    title: 'Physics Hub',
    icon: 'fa-atom',
    tabs: [
      { modeId: 'physics-engine', label: 'Engine', icon: 'fa-atom' },
      { modeId: 'game-physics', label: 'Game Physics', icon: 'fa-atom' },
      { modeId: 'collision-det', label: 'Collision', icon: 'fa-bomb' },
      { modeId: 'fluid-sim', label: 'Fluid', icon: 'fa-droplet' },
      { modeId: 'cloth-sim', label: 'Cloth', icon: 'fa-shirt' },
      { modeId: 'ik-system', label: 'IK', icon: 'fa-bone' },
    ],
  },
  'audio-hub': {
    title: 'Audio Hub',
    icon: 'fa-volume-high',
    tabs: [
      { modeId: 'audio-engine', label: 'Engine', icon: 'fa-volume-high' },
      { modeId: 'music-gen', label: 'Music Gen', icon: 'fa-music' },
      { modeId: 'music-conductor', label: 'Conductor', icon: 'fa-headphones-simple' },
      { modeId: 'sfx-gen', label: 'SFX', icon: 'fa-bell' },
      { modeId: 'voice-synth', label: 'Voice', icon: 'fa-microphone-lines' },
    ],
  },
  'asset-hub': {
    title: 'Asset Hub',
    icon: 'fa-folder-open',
    tabs: [
      { modeId: 'asset-gen', label: 'Generator', icon: 'fa-folder-open' },
      { modeId: 'asset-sync', label: 'Synthesizer', icon: 'fa-wand-magic-sparkles' },
      { modeId: 'import-export', label: 'Import/Export', icon: 'fa-file-import' },
      { modeId: 'build-pipeline', label: 'Build', icon: 'fa-arrows-spin' },
    ],
  },
  'qa-hub': {
    title: 'QA Hub',
    icon: 'fa-clipboard-check',
    tabs: [
      { modeId: 'qa-dashboard', label: 'Dashboard', icon: 'fa-clipboard-check' },
      { modeId: 'playtest-sim', label: 'Playtest', icon: 'fa-gamepad' },
      { modeId: 'bug-hunter', label: 'Bug Hunter', icon: 'fa-bug' },
      { modeId: 'perf-monitor', label: 'Performance', icon: 'fa-gauge' },
      { modeId: 'security-scan', label: 'Security', icon: 'fa-shield' },
    ],
  },
  'system-hub': {
    title: 'System Hub',
    icon: 'fa-gear',
    tabs: [
      { modeId: 'node-editor', label: 'Node Editor', icon: 'fa-diagram-project' },
      { modeId: 'signal-bus', label: 'Signal Bus', icon: 'fa-tower-broadcast' },
      { modeId: 'state-machine', label: 'State Machine', icon: 'fa-sitemap' },
      { modeId: 'visual-script', label: 'Visual Script', icon: 'fa-code' },
      { modeId: 'event-system', label: 'Events', icon: 'fa-bolt' },
      { modeId: 'llm-router', label: 'LLM Router', icon: 'fa-route' },
      { modeId: 'chat-editor', label: 'Chat', icon: 'fa-comments' },
      { modeId: 'model-chat', label: 'Model Chat', icon: 'fa-robot' },
      { modeId: 'coordination-hub', label: 'Coord Hub', icon: 'fa-network-wired' },
      { modeId: 'cognitive-mesh', label: 'Cognitive Mesh', icon: 'fa-brain' },
      { modeId: 'live-tuner', label: 'Live Tuner', icon: 'fa-gauge-high' },
      { modeId: 'temporal-director', label: 'Temporal Dir', icon: 'fa-hourglass-half' },
      { modeId: 'predictive-prefetcher', label: 'Prefetch', icon: 'fa-forward-fast' },
      { modeId: 'memory-dream', label: 'Memory Dream', icon: 'fa-moon' },
      { modeId: 'ai-workflow', label: 'AI Workflow', icon: 'fa-diagram-project' },
    ],
  },
  'cognition-lab': {
    title: 'Cognition Lab',
    icon: 'fa-atom',
    tabs: [
      { modeId: 'memory-crystal', label: 'Crystal', icon: 'fa-gem' },
      { modeId: 'spatial-mycelium', label: 'Mycelium', icon: 'fa-network-wired' },
      { modeId: 'narrative-tectonic', label: 'Tectonic', icon: 'fa-mountain' },
      { modeId: 'quantum-field', label: 'Quantum Field', icon: 'fa-atom' },
      { modeId: 'holographic-cognition', label: 'Holographic', icon: 'fa-wave-square' },
      { modeId: 'temporal-crystal', label: 'Temporal', icon: 'fa-gem' },
      { modeId: 'belief-ecosystem', label: 'Belief Eco', icon: 'fa-tree' },
      { modeId: 'phase-transition', label: 'Phase', icon: 'fa-fire-flame-curved' },
      { modeId: 'emotional-resonance', label: 'Emo Resonance', icon: 'fa-wave-square' },
      { modeId: 'temporal-flow', label: 'Temp Flow', icon: 'fa-hourglass-half' },
      { modeId: 'cognitive-tide', label: 'Cog Tide', icon: 'fa-water' },
      { modeId: 'chromatic-aurora', label: 'Aurora', icon: 'fa-rainbow' },
      { modeId: 'consciousness-stratum', label: 'Stratum', icon: 'fa-layer-group' },
      { modeId: 'probability-mist', label: 'Mist', icon: 'fa-cloud' },
      { modeId: 'narrative-resonance', label: 'Nar Resonance', icon: 'fa-wave-square' },
      { modeId: 'emergence-pattern', label: 'Emergence', icon: 'fa-shapes' },
      { modeId: 'persona-lifecycle', label: 'Persona', icon: 'fa-infinity' },
      { modeId: 'spatial-harmonics', label: 'Harmonics', icon: 'fa-compass-drafting' },
      { modeId: 'motivation-chemistry', label: 'Chemistry', icon: 'fa-flask-vial' },
      { modeId: 'quantum-state', label: 'Quantum State', icon: 'fa-atom' },
    ],
  },
};

interface UnifiedHubPanelProps {
  hubId: string;
  renderPanel: (modeId: string) => React.ReactNode;
}

const UnifiedHubPanel: React.FC<UnifiedHubPanelProps> = ({ hubId, renderPanel }) => {
  const config = HUB_CONFIGS[hubId];
  const [activeTabIndex, setActiveTabIndex] = useState(0);
  const [tabSearch, setTabSearch] = useState('');
  const [recentlyVisited, setRecentlyVisited] = useState<Set<string>>(new Set());

  // Reset active tab when hub changes
  useEffect(() => {
    setActiveTabIndex(0);
    setTabSearch('');
  }, [hubId]);

  // Filter tabs by search
  const filteredTabs = useMemo(() => {
    if (!config) return [];
    const search = tabSearch.toLowerCase().trim();
    if (!search) return config.tabs;
    return config.tabs.filter(
      (t) => t.label.toLowerCase().includes(search) || t.modeId.toLowerCase().includes(search)
    );
  }, [config, tabSearch]);

  if (!config) {
    return (
      <div className="flex items-center justify-center h-full bg-[#0d0d0d] text-gray-500">
        <div className="text-center">
          <i className="fas fa-exclamation-triangle text-2xl mb-2" />
          <div className="text-sm">Unknown hub: {hubId}</div>
        </div>
      </div>
    );
  }

  // Ensure activeTabIndex is valid after filtering
  const safeIndex = Math.min(activeTabIndex, Math.max(0, filteredTabs.length - 1));
  const activeTab = filteredTabs[safeIndex];
  const visitedCount = recentlyVisited.size;
  const totalCount = config.tabs.length;
  const progressPct = totalCount > 0 ? Math.round((visitedCount / totalCount) * 100) : 0;

  const handleTabClick = (index: number, modeId: string) => {
    setActiveTabIndex(index);
    setRecentlyVisited((prev) => {
      const next = new Set(prev);
      next.add(modeId);
      return next;
    });
  };

  return (
    <div className="flex h-full bg-[#0d0d0d] text-white">
      {/* Left Sidebar - Module Navigator */}
      <div className="flex flex-col w-48 border-r border-[#1e1e1e] bg-[#0a0a0a] shrink-0">
        {/* Hub Title */}
        <div className="px-3 py-3 border-b border-[#1e1e1e] shrink-0">
          <div className="flex items-center gap-2">
            <div className="w-6 h-6 flex items-center justify-center bg-gradient-to-br from-[#1a1a1a] to-[#0d0d0d] border border-[#2a2a2a]">
              <i className={`fas ${config.icon} text-white text-[10px]`} />
            </div>
            <div className="min-w-0 flex-1">
              <div className="text-[11px] font-bold tracking-wide uppercase text-white truncate">
                {config.title}
              </div>
              <div className="text-[9px] text-gray-600 mt-0.5 flex items-center gap-1">
                <span>{totalCount} modules</span>
                <span className="text-gray-700">·</span>
                <span className="text-gray-500">{visitedCount} visited</span>
              </div>
            </div>
          </div>
          {/* Progress bar */}
          <div className="mt-2 h-0.5 bg-[#1a1a1a] overflow-hidden">
            <div
              className="h-full bg-gradient-to-r from-gray-600 to-gray-400 transition-all duration-300"
              style={{ width: `${progressPct}%` }}
            />
          </div>
        </div>

        {/* Search */}
        <div className="px-2 py-2 border-b border-[#1e1e1e] shrink-0">
          <div className="relative">
            <i className="fas fa-search absolute left-2 top-1/2 -translate-y-1/2 text-[9px] text-gray-600" />
            <input
              type="text"
              value={tabSearch}
              onChange={(e) => setTabSearch(e.target.value)}
              placeholder="Filter modules..."
              className="w-full bg-[#1a1a1a] border border-[#2a2a2a] text-white text-[10px] pl-6 pr-6 py-1.5 focus:outline-none focus:border-[#444] placeholder-gray-700 transition-colors"
            />
            {tabSearch && (
              <button
                onClick={() => setTabSearch('')}
                className="absolute right-1.5 top-1/2 -translate-y-1/2 text-gray-600 hover:text-gray-400 transition-colors"
                title="Clear filter"
              >
                <i className="fas fa-times text-[9px]" />
              </button>
            )}
          </div>
        </div>

        {/* Tab List - scrollable */}
        <div className="flex-1 overflow-y-auto py-1 custom-scroll">
          {filteredTabs.map((tab, index) => {
            const isActive = index === safeIndex;
            const isVisited = recentlyVisited.has(tab.modeId);
            return (
              <button
                key={tab.modeId}
                onClick={() => handleTabClick(index, tab.modeId)}
                className={`group w-full flex items-center gap-2 px-3 py-1.5 text-[11px] font-medium transition-all border-l-2 text-left ${
                  isActive
                    ? 'border-white text-white bg-[#161616]'
                    : 'border-transparent text-gray-500 hover:text-gray-300 hover:bg-[#121212]'
                }`}
              >
                <i className={`fas ${tab.icon} text-[10px] w-3 text-center shrink-0 ${isActive ? 'text-white' : 'text-gray-600 group-hover:text-gray-400'}`} />
                <span className="truncate flex-1">{tab.label}</span>
                {/* Status indicator */}
                <span className="shrink-0 flex items-center justify-center">
                  {isActive ? (
                    <span className="w-1.5 h-1.5 rounded-full bg-white animate-pulse" title="Active" />
                  ) : isVisited ? (
                    <span className="w-1 h-1 rounded-full bg-gray-500" title="Visited" />
                  ) : (
                    <span className="w-1 h-1 rounded-full bg-gray-800" title="Not visited" />
                  )}
                </span>
              </button>
            );
          })}
          {filteredTabs.length === 0 && (
            <div className="text-center text-gray-700 text-[10px] py-8">
              <i className="fas fa-search-minus text-lg mb-2 opacity-30 block" />
              No modules found
            </div>
          )}
        </div>

        {/* Footer Status Bar */}
        <div className="px-3 py-2 border-t border-[#1e1e1e] shrink-0 bg-[#0a0a0a]">
          <div className="flex items-center justify-between text-[9px]">
            <div className="flex items-center gap-1.5">
              <span className="w-1.5 h-1.5 rounded-full bg-green-500 animate-pulse" />
              <span className="text-gray-500 uppercase tracking-wider font-medium">Online</span>
            </div>
            <div className="text-gray-600 font-mono">
              {safeIndex + 1}/{filteredTabs.length || 0}
            </div>
          </div>
        </div>
      </div>

      {/* Right Content Area - Active Panel */}
      <div className="flex-1 overflow-hidden bg-[#0d0d0d] min-w-0 relative">
        {activeTab ? (
          <div className="h-full flex flex-col">
            {/* Subtle active module indicator strip */}
            <div className="h-px bg-gradient-to-r from-transparent via-[#2a2a2a] to-transparent shrink-0" />
            <div className="flex-1 overflow-hidden">
              {renderPanel(activeTab.modeId)}
            </div>
          </div>
        ) : (
          <div className="flex items-center justify-center h-full text-gray-600 text-sm">
            <div className="text-center">
              <i className="fas fa-cube text-3xl mb-3 opacity-30" />
              <div>Select a module to begin</div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default UnifiedHubPanel;
