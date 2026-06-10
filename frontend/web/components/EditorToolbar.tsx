import React, { useState } from 'react';

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

const modeGroups = [
  {
    label: 'Core',
    items: [
      { id: 'dashboard', label: 'Editor', icon: 'fa-gamepad' },
      { id: 'game-preview', label: 'Preview', icon: 'fa-eye' },
      { id: 'game-studio', label: 'Studio', icon: 'fa-code' },
    ],
  },
  {
    label: 'Design',
    items: [
      { id: 'blueprint', label: 'Blueprint', icon: 'fa-drafting-compass' },
      { id: 'story', label: 'Story', icon: 'fa-book' },
      { id: 'storyboard', label: 'Storyboard', icon: 'fa-film' },
      { id: 'npc', label: 'NPC', icon: 'fa-robot' },
      { id: 'dialogue', label: 'Dialogue', icon: 'fa-comments' },
    ],
  },
  {
    label: 'Create',
    items: [
      { id: 'templates', label: 'Templates', icon: 'fa-puzzle-piece' },
      { id: 'asset', label: 'Asset Gen', icon: 'fa-image' },
      { id: 'voice', label: 'Voice', icon: 'fa-microphone' },
      { id: 'video', label: 'Video', icon: 'fa-video' },
    ],
  },
  {
    label: 'Visual',
    items: [
      { id: 'node-canvas', label: 'Nodes', icon: 'fa-diagram-project' },
      { id: 'workflow', label: 'Workflow', icon: 'fa-share-nodes' },
      { id: 'timeline', label: 'Timeline', icon: 'fa-clock' },
    ],
  },
  {
    label: 'AI',
    items: [
      { id: 'agent', label: 'Agent', icon: 'fa-brain' },
      { id: 'intelligence-core', label: 'Intel Core', icon: 'fa-microchip' },
      { id: 'orchestrator', label: 'Orchestrate', icon: 'fa-sitemap' },
      { id: 'skill-evolution', label: 'Skills', icon: 'fa-chart-line' },
      { id: 'studio', label: 'Studio AI', icon: 'fa-users-gear' },
      { id: 'function-dispatcher', label: 'Dispatcher', icon: 'fa-arrow-right-arrow-left' },
      { id: 'world-interaction', label: 'World AI', icon: 'fa-globe' },
    ],
  },
  {
    label: 'Engine',
    items: [
      { id: 'sprite-batcher', label: 'Batcher', icon: 'fa-layer-group' },
      { id: 'visual-event-sheet', label: 'Events', icon: 'fa-list-check' },
      { id: 'node-composer', label: 'Nodes', icon: 'fa-cubes' },
    ],
  },
  {
    label: 'Pipeline',
    items: [
      { id: 'pipeline', label: 'Pipeline', icon: 'fa-arrows-spin' },
      { id: 'assets', label: 'Assets', icon: 'fa-folder-open' },
      { id: 'asset-browser', label: 'Library', icon: 'fa-box-open' },
      { id: 'playtest', label: 'Playtest', icon: 'fa-gamepad' },
    ],
  },
  {
    label: 'Quality',
    items: [
      { id: 'validator', label: 'Validator', icon: 'fa-check-double' },
      { id: 'evaluator', label: 'Evaluator', icon: 'fa-star' },
      { id: 'performance', label: 'Perf', icon: 'fa-gauge-high' },
    ],
  },
  {
    label: 'System',
    items: [
      { id: 'engine-unification', label: 'Engine Core', icon: 'fa-cogs' },
      { id: 'composition-graph', label: 'Graph', icon: 'fa-project-diagram' },
      { id: 'knowledge', label: 'Knowledge', icon: 'fa-lightbulb' },
      { id: 'lifecycle', label: 'Lifecycle', icon: 'fa-rotate' },
      { id: 'slash-commands', label: 'Commands', icon: 'fa-terminal' },
      { id: 'validation-hooks', label: 'Hooks', icon: 'fa-shield-halved' },
      { id: 'task-executor', label: 'Executor', icon: 'fa-bolt' },
      { id: 'script-editor', label: 'Script Editor', icon: 'fa-code' },
      { id: 'settings', label: 'Settings', icon: 'fa-gear' },
    ],
  },
];

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

  const closeAllMenus = () => {
    setShowModeMenu(false);
    setShowFileMenu(false);
    setShowViewMenu(false);
  };

  const activeModeItem = modeGroups.flatMap((g) => g.items).find((i) => i.id === activeMode);

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

      <div className="relative">
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
              <span>Mode</span>
            </>
          )}
          <i className="fa-solid fa-chevron-down text-[7px] text-[#555]" />
        </button>
        {showModeMenu && (
          <div className="absolute top-full left-0 mt-1 bg-[#161616] border border-[#2a2a2a] rounded-lg py-1 z-50 min-w-[180px] shadow-xl max-h-[70vh] overflow-y-auto">
            {modeGroups.map((group) => (
              <div key={group.label}>
                <div className="px-3 py-1 text-[9px] font-bold text-[#444] uppercase tracking-wider">{group.label}</div>
                {group.items.map((item) => (
                  <button
                    key={item.id}
                    onClick={() => { onModeSwitch(item.id); closeAllMenus(); }}
                    className={`w-full text-left px-3 py-1.5 text-[11px] hover:bg-[#222] transition-colors flex items-center gap-2 ${
                      activeMode === item.id ? 'text-orange-500 bg-orange-500/5' : 'text-[#888]'
                    }`}
                  >
                    <i className={`fa-solid ${item.icon} text-[9px] w-4 text-center ${activeMode === item.id ? 'text-orange-500' : 'text-[#555]'}`} />
                    {item.label}
                  </button>
                ))}
                <div className="border-t border-[#1e1e1e] my-0.5" />
              </div>
            ))}
          </div>
        )}
      </div>

      <div className="flex-1" />

      <button
        onClick={onAIGenerate}
        className="flex items-center gap-1.5 px-3 py-1.5 bg-gradient-to-r from-orange-500 to-red-600 text-white rounded-md text-[11px] font-semibold hover:opacity-90 hover:-translate-y-px transition-all"
      >
        <i className="fa-solid fa-wand-magic-sparkles text-[9px]" />
        <span className="hidden md:inline">AI Generate</span>
      </button>

      <button
        onClick={onTogglePlay}
        className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md text-[11px] font-semibold text-white hover:opacity-90 hover:-translate-y-px transition-all ${
          isPlaying
            ? 'bg-gradient-to-r from-red-600 to-red-700'
            : 'bg-gradient-to-r from-green-500 to-green-600'
        }`}
      >
        <i className={`fa-solid ${isPlaying ? 'fa-stop' : 'fa-play'} text-[9px]`} />
        {isPlaying ? 'Stop' : 'Play'}
      </button>

      <div className="w-px h-5 bg-[#1e1e1e]" />

      <div className="w-7 h-7 bg-gradient-to-br from-orange-500 to-red-600 rounded-md flex items-center justify-center text-[10px] font-bold text-white cursor-pointer">
        S
      </div>
    </div>
  );
};

export default EditorToolbar;
