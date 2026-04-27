import React, { useState, useCallback } from 'react';
import EditorToolbar from './EditorToolbar';
import SceneHierarchy from './SceneHierarchy';
import Viewport3D from './Viewport3D';
import InspectorPanel from './InspectorPanel';
import ConsolePanel from './ConsolePanel';
import type { SceneEntity } from './SceneHierarchy';
import type { ConsoleLine } from './ConsolePanel';
import type { ViewMode } from '../types';

import WelcomeDashboard from './WelcomeDashboard';
import GameEditor from './GameEditor';
import GameGenerator from './GameGenerator';
import StoryEditor from './StoryEditor';
import AssetGenerator from './AssetGenerator';
import VoiceSynthesizer from './VoiceSynthesizer';
import StoryboardEditor from './StoryboardEditor';
import VideoRenderer from './VideoRenderer';
import WorkflowEditor from './WorkflowEditor';
import NPCDesigner from './NPCDesigner';
import AgentPanel from './AgentPanel';

type TransformTool = 'move' | 'rotate' | 'scale';

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

const SparkLabsEditor: React.FC = () => {
  const [currentTool, setCurrentTool] = useState<TransformTool>('move');
  const [isPlaying, setIsPlaying] = useState(false);
  const [selectedEntity, setSelectedEntity] = useState<string | null>('ai-core');
  const [selectedEntityName, setSelectedEntityName] = useState<string | null>('AI Core');
  const [entities, setEntities] = useState<SceneEntity[]>(defaultEntities);
  const [isGenerating, setIsGenerating] = useState(false);
  const [generatingStatus, setGeneratingStatus] = useState('');
  const [activeMode, setActiveMode] = useState<ViewMode>('dashboard');
  const [logs, setLogs] = useState<ConsoleLine[]>([
    { type: 'info', message: '[SparkLabs] Editor initialized' },
    { type: 'success', message: '[SparkLabs] Neural Core loaded' },
    { type: 'info', message: '[SparkLabs] Scene "Main World" ready' },
    { type: 'info', message: '[SparkLabs] AI Agent system online' },
    { type: 'success', message: '[SparkLabs] 7 entities in scene' },
    { type: 'info', message: '[SparkLabs] Viewport renderer: WebGL 2.0' },
  ]);

  const addLog = useCallback((type: ConsoleLine['type'], message: string) => {
    setLogs((prev) => [...prev, { type, message }]);
  }, []);

  const handleSelectEntity = useCallback((id: string, name: string) => {
    setSelectedEntity(id);
    setSelectedEntityName(name);
    addLog('info', `[Editor] Selected: ${name}`);
  }, [addLog]);

  const handleAddEntity = useCallback(() => {
    const newEntity: SceneEntity = {
      id: `entity_${Date.now()}`,
      name: 'New Entity',
      icon: 'fa-cube',
      iconColor: '#60a5fa',
    };
    setEntities((prev) => [...prev, newEntity]);
    addLog('success', '[Editor] Entity added to scene');
  }, [addLog]);

  const handleAIGenerate = useCallback(() => {
    setActiveMode('dashboard');
  }, []);

  const handleAIPrompt = useCallback((prompt: string) => {
    addLog('info', `[AI] Processing prompt: "${prompt.substring(0, 50)}..."`);
    setIsGenerating(true);

    const phases = [
      'Analyzing prompt',
      'Building neural graph',
      'Generating world geometry',
      'Placing AI agents',
      'Configuring behaviors',
      'Rendering scene',
    ];

    let phase = 0;
    const interval = setInterval(() => {
      if (phase < phases.length) {
        setGeneratingStatus(phases[phase]);
        addLog('info', `[AI] ${phases[phase]}...`);
        phase++;
      } else {
        clearInterval(interval);
        setIsGenerating(false);
        setGeneratingStatus('');
        addLog('success', '[AI] World generated successfully');
        addLog('success', '[AI] 3 new entities added to scene');
      }
    }, 800);
  }, [addLog]);

  const handleTogglePlay = useCallback(() => {
    setIsPlaying((prev) => {
      const next = !prev;
      addLog(next ? 'success' : 'info', next ? '[Engine] Play mode started' : '[Engine] Play mode stopped');
      return next;
    });
  }, [addLog]);

  const handleToolChange = useCallback((tool: TransformTool) => {
    setCurrentTool(tool);
    addLog('info', `[Editor] Tool changed to: ${tool}`);
  }, [addLog]);

  const handleModeSwitch = useCallback((mode: string) => {
    setActiveMode(mode as ViewMode);
    addLog('info', `[Editor] Switched to ${mode}`);
  }, [addLog]);

  const renderModePanel = () => {
    switch (activeMode) {
      case 'dashboard':
        return <WelcomeDashboard />;
      case 'game-studio':
        return <GameEditor />;
      case 'templates':
        return <GameGenerator />;
      case 'story':
        return <StoryEditor />;
      case 'asset':
        return <AssetGenerator />;
      case 'voice':
        return <VoiceSynthesizer />;
      case 'storyboard':
        return <StoryboardEditor />;
      case 'video':
        return <VideoRenderer />;
      case 'workflow':
        return <WorkflowEditor />;
      case 'npc':
        return <NPCDesigner />;
      case 'agent':
        return <AgentPanel />;
      default:
        return <WelcomeDashboard />;
    }
  };

  const isEditorMode = activeMode === 'dashboard';

  return (
    <div className="grid h-screen" style={{ gridTemplateRows: '40px 1fr 24px' }}>
      <EditorToolbar
        currentTool={currentTool}
        onToolChange={handleToolChange}
        onAIGenerate={handleAIGenerate}
        isPlaying={isPlaying}
        onTogglePlay={handleTogglePlay}
        onModeSwitch={handleModeSwitch}
        activeMode={activeMode}
      />

      {isEditorMode ? (
        <div className="grid overflow-hidden" style={{ gridTemplateColumns: '220px 1fr 280px' }}>
          <SceneHierarchy
            selectedEntity={selectedEntity}
            onSelectEntity={handleSelectEntity}
            onAddEntity={handleAddEntity}
            entities={entities}
          />

          <div className="grid overflow-hidden" style={{ gridTemplateRows: '1fr 180px' }}>
            <Viewport3D
              isPlaying={isPlaying}
              isGenerating={isGenerating}
              generatingStatus={generatingStatus}
            />
            <ConsolePanel
              logs={logs}
              onAddLog={addLog}
              onAIGenerate={handleAIPrompt}
            />
          </div>

          <InspectorPanel selectedEntityName={selectedEntityName} />
        </div>
      ) : (
        <div className="overflow-hidden">
          {renderModePanel()}
        </div>
      )}

      <div className="bg-[#111] border-t border-[#1e1e1e] flex items-center px-3 text-[10px] text-[#555] font-mono">
        <div className="flex items-center gap-1.5">
          <div className="w-1.5 h-1.5 bg-green-500 rounded-full animate-pulse" />
          <span>SparkLabs Engine v1.0.0</span>
        </div>
        <div className="w-px h-3 bg-[#2a2a2a] mx-2" />
        <span>Scene: Main World</span>
        <div className="w-px h-3 bg-[#2a2a2a] mx-2" />
        <span>Entities: {entities.length}</span>
        <div className="flex-1" />
        <span>WebGL 2.0</span>
        <div className="w-px h-3 bg-[#2a2a2a] mx-2" />
        <span>60 FPS</span>
        <div className="w-px h-3 bg-[#2a2a2a] mx-2" />
        <span className="text-orange-500">AI Ready</span>
      </div>
    </div>
  );
};

export default SparkLabsEditor;
