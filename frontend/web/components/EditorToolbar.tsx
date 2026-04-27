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
}

const modes = [
  { id: 'dashboard', label: 'Dashboard' },
  { id: 'game-studio', label: 'Game Studio' },
  { id: 'templates', label: 'Templates' },
  { id: 'story', label: 'Story' },
  { id: 'asset', label: 'Assets' },
  { id: 'npc', label: 'NPC' },
  { id: 'workflow', label: 'Workflow' },
  { id: 'agent', label: 'Agent' },
];

const EditorToolbar: React.FC<EditorToolbarProps> = ({
  currentTool,
  onToolChange,
  onAIGenerate,
  isPlaying,
  onTogglePlay,
  onModeSwitch,
  activeMode,
}) => {
  const [showModeMenu, setShowModeMenu] = useState(false);

  return (
    <div className="h-10 bg-[#111] border-b border-[#1e1e1e] flex items-center px-3 gap-2 shrink-0">
      <div className="flex items-center gap-2 mr-4">
        <div className="w-[22px] h-[22px] bg-gradient-to-br from-orange-500 to-red-600 rounded-full flex items-center justify-center">
          <i className="fa-solid fa-fire text-white text-[10px]" />
        </div>
        <span className="font-bold text-[13px]">
          <span className="bg-gradient-to-r from-orange-500 via-red-500 to-yellow-400 bg-clip-text text-transparent">Spark</span>
          <span className="text-[#e0e0e0]">Labs</span>
        </span>
      </div>

      <div className="w-px h-5 bg-[#2a2a2a]" />

      <div className="relative">
        <button
          onClick={() => setShowModeMenu(!showModeMenu)}
          className="px-2 py-1 text-[11px] text-[#999] hover:text-[#ddd] hover:bg-[#222] rounded transition-colors"
        >
          Mode ▾
        </button>
        {showModeMenu && (
          <div className="absolute top-full left-0 mt-1 bg-[#1a1a1a] border border-[#2a2a2a] rounded-lg py-1 z-50 min-w-[140px]">
            {modes.map((mode) => (
              <button
                key={mode.id}
                onClick={() => { onModeSwitch(mode.id); setShowModeMenu(false); }}
                className={`w-full text-left px-3 py-1.5 text-[11px] hover:bg-[#222] transition-colors ${
                  activeMode === mode.id ? 'text-orange-500' : 'text-[#999]'
                }`}
              >
                {mode.label}
              </button>
            ))}
          </div>
        )}
      </div>

      <button className="px-2 py-1 text-[11px] text-[#999] hover:text-[#ddd] hover:bg-[#222] rounded transition-colors">
        File
      </button>
      <button className="px-2 py-1 text-[11px] text-[#999] hover:text-[#ddd] hover:bg-[#222] rounded transition-colors">
        Edit
      </button>
      <button className="px-2 py-1 text-[11px] text-[#999] hover:text-[#ddd] hover:bg-[#222] rounded transition-colors">
        View
      </button>
      <button className="px-2 py-1 text-[11px] text-[#999] hover:text-[#ddd] hover:bg-[#222] rounded transition-colors">
        Game
      </button>

      <div className="w-px h-5 bg-[#2a2a2a]" />

      {(['move', 'rotate', 'scale'] as TransformTool[]).map((tool) => (
        <button
          key={tool}
          onClick={() => onToolChange(tool)}
          className={`flex items-center gap-1 px-2.5 py-1.5 rounded text-[12px] transition-all ${
            currentTool === tool
              ? 'bg-orange-500/15 border border-orange-500/40 text-orange-500'
              : 'bg-[#1a1a1a] border border-[#2a2a2a] text-[#999] hover:bg-[#222] hover:text-[#ddd] hover:border-[#3a3a3a]'
          }`}
        >
          <i className={`fa-solid ${
            tool === 'move' ? 'fa-arrows-up-down-left-right' :
            tool === 'rotate' ? 'fa-rotate' : 'fa-expand'
          } text-[10px]`} />
          {tool.charAt(0).toUpperCase() + tool.slice(1)}
        </button>
      ))}

      <div className="flex-1" />

      <button
        onClick={onAIGenerate}
        className="flex items-center gap-1.5 px-4 py-1.5 bg-gradient-to-r from-orange-500 to-red-600 text-white rounded-lg text-[12px] font-semibold hover:opacity-90 hover:-translate-y-px transition-all"
      >
        <i className="fa-solid fa-wand-magic-sparkles" />
        AI Generate
      </button>

      <button
        onClick={onTogglePlay}
        className={`flex items-center gap-1.5 px-4 py-1.5 rounded-lg text-[12px] font-semibold text-white hover:opacity-90 hover:-translate-y-px transition-all ${
          isPlaying
            ? 'bg-gradient-to-r from-red-600 to-red-700'
            : 'bg-gradient-to-r from-green-500 to-green-600'
        }`}
      >
        <i className={`fa-solid ${isPlaying ? 'fa-stop' : 'fa-play'}`} />
        {isPlaying ? 'Stop' : 'Play'}
      </button>

      <div className="w-px h-5 bg-[#2a2a2a]" />

      <div className="w-6 h-6 bg-gradient-to-br from-orange-500 to-red-600 rounded-full flex items-center justify-center text-[10px] font-bold text-white">
        S
      </div>
    </div>
  );
};

export default EditorToolbar;
