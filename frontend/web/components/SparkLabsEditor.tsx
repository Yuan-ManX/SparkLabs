import React, { useState, useCallback, useRef, useEffect } from 'react';
import EditorToolbar from './EditorToolbar';
import SceneOutliner, { SceneNode } from './SceneOutliner';
import GameViewport from './GameViewport';
import PropertyEditor, { PropertySection } from './PropertyEditor';
import NodeGraphEditor from './NodeGraphEditor';
import AssetLibrary from './AssetLibrary';
import AIPromptBar from './AIPromptBar';
import ConsolePanel from './ConsolePanel';
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
import GamePreview from './GamePreview';
import NodeCanvas from './NodeCanvas';
import StudioPanel from './StudioPanel';
import PipelineView from './PipelineView';
import AssetBrowser from './AssetBrowser';
import TimelineEditor from './TimelineEditor';
import BlueprintEditor from './BlueprintEditor';
import PlaytestPanel from './PlaytestPanel';
import CompositionGraph from './CompositionGraph';
import KnowledgeExplorer from './KnowledgeExplorer';
import PerformanceMonitor from './PerformanceMonitor';
import DialogueEditor from './DialogueEditor';
import AssetPipeline from './AssetPipeline';
import ValidationPanel from './ValidationPanel';
import OrchestratorPanel from './OrchestratorPanel';
import SkillEvolution from './SkillEvolution';
import GameEvaluator from './GameEvaluator';
import ScriptEditor from './ScriptEditor';
import SettingsPanel from './SettingsPanel';
import { LifecyclePanel, SlashCommandsPanel, ValidationHooksPanel } from './LifecyclePanels';
import { TaskExecutorPanel } from './TaskExecutorPanel';
import NotificationToast, { Toast } from './NotificationToast';
import KeyboardShortcuts, { ShortcutDef } from './KeyboardShortcuts';

type TransformTool = 'move' | 'rotate' | 'scale';
type LeftPanelTab = 'scene' | 'assets' | 'nodes';
type RightPanelTab = 'inspector' | 'ai-config';
type BottomPanelTab = 'console' | 'timeline' | 'ai-assistant';

const defaultSceneNodes: SceneNode[] = [
  {
    id: 'root', name: 'Main World', icon: 'fa-globe', iconColor: '#f97316', type: 'group', visible: true, locked: false, parentId: null,
    children: [
      { id: 'camera', name: 'Main Camera', icon: 'fa-video', iconColor: '#4ade80', type: 'entity', visible: true, locked: false, parentId: 'root', children: [] },
      { id: 'light', name: 'Directional Light', icon: 'fa-sun', iconColor: '#fbbf24', type: 'entity', visible: true, locked: false, parentId: 'root', children: [] },
      { id: 'ai-core', name: 'AI Core', icon: 'fa-microchip', iconColor: '#f97316', type: 'entity', visible: true, locked: false, parentId: 'root', children: [] },
      { id: 'neural-net', name: 'Neural Network', icon: 'fa-circle-nodes', iconColor: '#f97316', type: 'entity', visible: true, locked: false, parentId: 'root', children: [] },
      { id: 'terrain', name: 'Terrain', icon: 'fa-mountain', iconColor: '#4ade80', type: 'entity', visible: true, locked: false, parentId: 'root', children: [] },
      {
        id: 'actors', name: 'Actors', icon: 'fa-users', iconColor: '#60a5fa', type: 'group', visible: true, locked: false, parentId: 'root',
        children: [
          { id: 'player', name: 'Player', icon: 'fa-person', iconColor: '#22c55e', type: 'entity', visible: true, locked: false, parentId: 'actors', children: [] },
          { id: 'npc', name: 'AI Agent - NPC', icon: 'fa-robot', iconColor: '#c084fc', type: 'entity', visible: true, locked: false, parentId: 'actors', children: [] },
        ],
      },
      { id: 'environment', name: 'Environment', icon: 'fa-tree', iconColor: '#4ade80', type: 'entity', visible: true, locked: false, parentId: 'root', children: [] },
    ],
  },
];

const defaultPropertySections: PropertySection[] = [
  {
    id: 'transform', label: 'Transform', icon: 'fa-arrows-up-down-left-right', color: '#f97316',
    fields: [
      { key: 'position', label: 'Position', type: 'vector3', value: [0, 0, 0] },
      { key: 'rotation', label: 'Rotation', type: 'vector3', value: [0, 0, 0] },
      { key: 'scale', label: 'Scale', type: 'vector3', value: [1, 1, 1] },
    ],
  },
  {
    id: 'neural', label: 'Neural Component', icon: 'fa-brain', color: '#8b5cf6',
    fields: [
      { key: 'ai_model', label: 'AI Model', type: 'select', value: 'gpt-4', options: [{ label: 'GPT-4', value: 'gpt-4' }, { label: 'Claude 3', value: 'claude-3' }, { label: 'SparkAI', value: 'sparkai' }] },
      { key: 'behavior', label: 'Behavior', type: 'select', value: 'autonomous', options: [{ label: 'Autonomous', value: 'autonomous' }, { label: 'Scripted', value: 'scripted' }, { label: 'Hybrid', value: 'hybrid' }] },
      { key: 'awareness', label: 'Awareness', type: 'slider', value: 75, min: 0, max: 100 },
      { key: 'memory', label: 'Memory', type: 'slider', value: 60, min: 0, max: 100 },
    ],
  },
  {
    id: 'rendering', label: 'Rendering', icon: 'fa-paintbrush', color: '#06b6d4',
    fields: [
      { key: 'material', label: 'Material', type: 'select', value: 'standard', options: [{ label: 'Standard', value: 'standard' }, { label: 'Unlit', value: 'unlit' }, { label: 'Neural', value: 'neural' }] },
      { key: 'color', label: 'Color', type: 'color', value: '#f97316' },
      { key: 'cast_shadow', label: 'Cast Shadow', type: 'checkbox', value: true },
    ],
  },
  {
    id: 'physics', label: 'Physics', icon: 'fa-atom', color: '#ef4444',
    fields: [
      { key: 'body_type', label: 'Body Type', type: 'select', value: 'dynamic', options: [{ label: 'Dynamic', value: 'dynamic' }, { label: 'Static', value: 'static' }, { label: 'Kinematic', value: 'kinematic' }] },
      { key: 'mass', label: 'Mass', type: 'number', value: 1.0, step: 0.1, min: 0 },
      { key: 'gravity_scale', label: 'Gravity Scale', type: 'slider', value: 1.0, min: 0, max: 5, step: 0.1 },
    ],
  },
];

interface PanelSizes {
  left: number;
  right: number;
  bottom: number;
}

const DEFAULT_PANEL_SIZES: PanelSizes = { left: 260, right: 300, bottom: 180 };
const MIN_PANEL_SIZES: PanelSizes = { left: 180, right: 200, bottom: 80 };

const ResizableHandle: React.FC<{
  direction: 'vertical' | 'horizontal';
  onMouseDown: (e: React.MouseEvent) => void;
}> = ({ direction, onMouseDown }) => (
  <div
    className={`sl-resize-handle ${
      direction === 'vertical'
        ? 'w-[3px] cursor-col-resize bg-[#1a1a1a]'
        : 'h-[3px] cursor-row-resize bg-[#1a1a1a]'
    } flex-shrink-0 relative group`}
    onMouseDown={onMouseDown}
  >
    <div
      className={`${
        direction === 'vertical'
          ? 'w-1 h-6 -ml-[1px] top-1/2 -translate-y-1/2'
          : 'h-1 w-6 -mt-[1px] left-1/2 -translate-x-1/2'
      } absolute opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center`}
    >
      <div className={`${direction === 'vertical' ? 'w-0.5 h-3' : 'h-0.5 w-3'} bg-[#444] rounded-full`} />
    </div>
  </div>
);

const SparkLabsEditor: React.FC<{ onGoHome?: () => void }> = ({ onGoHome }) => {
  const [currentTool, setCurrentTool] = useState<TransformTool>('move');
  const [isPlaying, setIsPlaying] = useState(false);
  const [selectedEntity, setSelectedEntity] = useState<string | null>('ai-core');
  const [selectedEntityName, setSelectedEntityName] = useState<string | null>('AI Core');
  const [sceneNodes, setSceneNodes] = useState<SceneNode[]>(defaultSceneNodes);
  const [propertySections, setPropertySections] = useState<PropertySection[]>(defaultPropertySections);
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
  const [panelSizes, setPanelSizes] = useState<PanelSizes>(DEFAULT_PANEL_SIZES);
  const [leftTab, setLeftTab] = useState<LeftPanelTab>('scene');
  const [rightTab, setRightTab] = useState<RightPanelTab>('inspector');
  const [bottomTab, setBottomTab] = useState<BottomPanelTab>('console');
  const [fps, setFps] = useState(60);
  const [toasts, setToasts] = useState<Toast[]>([]);
  const containerRef = useRef<HTMLDivElement>(null);
  const resizingRef = useRef<{ type: 'left' | 'right' | 'bottom'; startX: number; startSize: number } | null>(null);
  const fpsFrameRef = useRef<number>(0);
  const fpsLastTimeRef = useRef<number>(performance.now());
  const fpsCountRef = useRef<number>(0);

  useEffect(() => {
    const measureFps = (now: number) => {
      fpsCountRef.current++;
      if (now - fpsLastTimeRef.current >= 1000) {
        setFps(fpsCountRef.current);
        fpsCountRef.current = 0;
        fpsLastTimeRef.current = now;
      }
      fpsFrameRef.current = requestAnimationFrame(measureFps);
    };
    fpsFrameRef.current = requestAnimationFrame(measureFps);
    return () => cancelAnimationFrame(fpsFrameRef.current);
  }, []);

  const addLog = useCallback((type: ConsoleLine['type'], message: string) => {
    setLogs((prev) => [...prev, { type, message }]);
  }, []);

  const addToast = useCallback((toast: Omit<Toast, 'id'>) => {
    const id = `toast_${Date.now()}`;
    setToasts((prev) => [...prev, { ...toast, id }]);
  }, []);

  const dismissToast = useCallback((id: string) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  }, []);

  useEffect(() => {
    const handleMouseMove = (e: MouseEvent) => {
      if (!resizingRef.current || !containerRef.current) return;
      const { type, startX, startSize } = resizingRef.current;
      const delta = e.clientX - startX;
      if (type === 'left') {
        setPanelSizes((prev) => ({ ...prev, left: Math.max(MIN_PANEL_SIZES.left, startSize + delta) }));
      } else if (type === 'right') {
        setPanelSizes((prev) => ({ ...prev, right: Math.max(MIN_PANEL_SIZES.right, startSize - delta) }));
      } else if (type === 'bottom') {
        const dy = e.clientY - startX;
        setPanelSizes((prev) => ({ ...prev, bottom: Math.max(MIN_PANEL_SIZES.bottom, startSize - dy) }));
      }
    };
    const handleMouseUp = () => {
      resizingRef.current = null;
      document.body.style.cursor = '';
      document.body.style.userSelect = '';
    };
    window.addEventListener('mousemove', handleMouseMove);
    window.addEventListener('mouseup', handleMouseUp);
    return () => {
      window.removeEventListener('mousemove', handleMouseMove);
      window.removeEventListener('mouseup', handleMouseUp);
    };
  }, []);

  const startResize = useCallback((type: 'left' | 'right' | 'bottom', e: React.MouseEvent) => {
    e.preventDefault();
    const startX = type === 'bottom' ? e.clientY : e.clientX;
    const startSize = type === 'left' ? panelSizes.left : type === 'right' ? panelSizes.right : panelSizes.bottom;
    resizingRef.current = { type, startX, startSize };
    document.body.style.cursor = type === 'bottom' ? 'row-resize' : 'col-resize';
    document.body.style.userSelect = 'none';
  }, [panelSizes]);

  const handleSelectEntity = useCallback((id: string, name: string) => {
    setSelectedEntity(id);
    setSelectedEntityName(name);
    addLog('info', `[Editor] Selected: ${name}`);
  }, [addLog]);

  const handleAddEntity = useCallback(() => {
    const newEntity: SceneNode = {
      id: `entity_${Date.now()}`,
      name: 'New Entity',
      icon: 'fa-cube',
      iconColor: '#60a5fa',
      type: 'entity',
      visible: true,
      locked: false,
      parentId: 'root',
      children: [],
    };
    setSceneNodes((prev) =>
      prev.map((n) =>
        n.id === 'root' ? { ...n, children: [...n.children, newEntity] } : n
      )
    );
    addLog('success', '[Editor] Entity added to scene');
  }, [addLog]);

  const handleDeleteEntity = useCallback((id: string) => {
    const removeRecursive = (nodes: SceneNode[]): SceneNode[] =>
      nodes.filter((n) => n.id !== id).map((n) => ({ ...n, children: removeRecursive(n.children) }));
    setSceneNodes((prev) => removeRecursive(prev));
    addLog('info', `[Editor] Entity deleted`);
  }, [addLog]);

  const handleToggleVisibility = useCallback((id: string) => {
    const toggle = (nodes: SceneNode[]): SceneNode[] =>
      nodes.map((n) => (n.id === id ? { ...n, visible: !n.visible } : { ...n, children: toggle(n.children) }));
    setSceneNodes((prev) => toggle(prev));
  }, []);

  const handleToggleLock = useCallback((id: string) => {
    const toggle = (nodes: SceneNode[]): SceneNode[] =>
      nodes.map((n) => (n.id === id ? { ...n, locked: !n.locked } : { ...n, children: toggle(n.children) }));
    setSceneNodes((prev) => toggle(prev));
  }, []);

  const handleReorder = useCallback((dragId: string, dropId: string, position: 'before' | 'after' | 'inside') => {
    addLog('info', `[Editor] Reordered ${dragId} ${position} ${dropId}`);
  }, [addLog]);

  const handleFieldChange = useCallback((sectionId: string, fieldKey: string, value: unknown) => {
    setPropertySections((prev) =>
      prev.map((s) =>
        s.id === sectionId
          ? { ...s, fields: s.fields.map((f) => (f.key === fieldKey ? { ...f, value } : f)) }
          : s
      )
    );
  }, []);

  const handleAIGenerate = useCallback(() => {
    setActiveMode('dashboard');
  }, []);

  const handleAIPrompt = useCallback((prompt: string) => {
    addLog('info', `[AI] Processing prompt: "${prompt.substring(0, 50)}..."`);
    setIsGenerating(true);
    const phases = ['Analyzing prompt', 'Building neural graph', 'Generating world geometry', 'Placing AI agents', 'Configuring behaviors', 'Rendering scene'];
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

  const handleQuickAction = useCallback((action: string) => {
    const prompts: Record<string, string> = {
      world: 'Generate a rich game world with terrain and structures',
      character: 'Create a playable character with animations and abilities',
      mechanic: 'Add a core game mechanic with scoring and progression',
      level: 'Build a complete level with challenges and rewards',
      dialogue: 'Write engaging dialogue for NPCs in the scene',
      fix: 'Analyze and fix any issues in the current game',
    };
    handleAIPrompt(prompts[action] || action);
  }, [handleAIPrompt]);

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
      case 'dashboard': return null;
      case 'game-studio': return <GameEditor />;
      case 'templates': return <GameGenerator />;
      case 'story': return <StoryEditor />;
      case 'asset': return <AssetGenerator />;
      case 'voice': return <VoiceSynthesizer />;
      case 'storyboard': return <StoryboardEditor />;
      case 'video': return <VideoRenderer />;
      case 'workflow': return <WorkflowEditor />;
      case 'npc': return <NPCDesigner />;
      case 'agent': return <AgentPanel />;
      case 'game-preview': return <GamePreview />;
      case 'node-canvas': return <NodeCanvas />;
      case 'studio': return <StudioPanel />;
      case 'pipeline': return <PipelineView />;
      case 'asset-browser': return <AssetBrowser />;
      case 'timeline': return <TimelineEditor />;
      case 'blueprint': return <BlueprintEditor />;
      case 'playtest': return <PlaytestPanel />;
      case 'composition-graph': return <CompositionGraph />;
      case 'knowledge': return <KnowledgeExplorer />;
      case 'performance': return <PerformanceMonitor />;
      case 'dialogue': return <DialogueEditor />;
      case 'assets': return <AssetPipeline />;
      case 'validator': return <ValidationPanel />;
      case 'orchestrator': return <OrchestratorPanel />;
      case 'skill-evolution': return <SkillEvolution />;
      case 'evaluator': return <GameEvaluator />;
      case 'lifecycle': return <LifecyclePanel />;
      case 'slash-commands': return <SlashCommandsPanel />;
      case 'validation-hooks': return <ValidationHooksPanel />;
      case 'task-executor': return <TaskExecutorPanel />;
      case 'script-editor': return <ScriptEditor />;
      case 'settings': return <SettingsPanel />;
      default: return <WelcomeDashboard onModeSwitch={handleModeSwitch} onAIPrompt={handleAIPrompt} />;
    }
  };

  const isEditorMode = activeMode === 'dashboard';

  const entityCount = sceneNodes.reduce((acc, n) => acc + 1 + n.children.length, 0);

  const shortcuts: ShortcutDef[] = [
    { key: '1', ctrl: true, label: 'Move Tool', category: 'Tools', action: () => handleToolChange('move') },
    { key: '2', ctrl: true, label: 'Rotate Tool', category: 'Tools', action: () => handleToolChange('rotate') },
    { key: '3', ctrl: true, label: 'Scale Tool', category: 'Tools', action: () => handleToolChange('scale') },
    { key: 'p', ctrl: true, label: 'Toggle Play', category: 'Game', action: handleTogglePlay },
    { key: 'e', ctrl: true, label: 'Script Editor', category: 'View', action: () => handleModeSwitch('script-editor') },
    { key: ',', ctrl: true, label: 'Settings', category: 'View', action: () => handleModeSwitch('settings') },
    { key: 'd', ctrl: true, label: 'Dashboard', category: 'View', action: () => handleModeSwitch('dashboard') },
  ];

  return (
    <div className="relative h-screen">
      <KeyboardShortcuts shortcuts={shortcuts} />
      <NotificationToast toasts={toasts} onDismiss={dismissToast} />
      <div className="grid h-full" style={{ gridTemplateRows: '40px 1fr 24px' }}>
      <EditorToolbar
        currentTool={currentTool}
        onToolChange={handleToolChange}
        onAIGenerate={handleAIGenerate}
        isPlaying={isPlaying}
        onTogglePlay={handleTogglePlay}
        onModeSwitch={handleModeSwitch}
        activeMode={activeMode}
        onGoHome={onGoHome}
      />

      {isEditorMode ? (
        <div ref={containerRef} className="flex overflow-hidden">
          <div style={{ width: panelSizes.left }} className="flex-shrink-0 flex flex-col overflow-hidden">
            <div className="sl-tab-bar">
              {([['scene', 'Scene', 'fa-sitemap'], ['assets', 'Assets', 'fa-folder-open'], ['nodes', 'Nodes', 'fa-diagram-project']] as const).map(([id, label, icon]) => (
                <button
                  key={id}
                  onClick={() => setLeftTab(id)}
                  className={`sl-tab ${leftTab === id ? 'active' : ''}`}
                >
                  <i className={`fa-solid ${icon} text-[9px]`} />
                  {label}
                </button>
              ))}
            </div>
            <div className="flex-1 overflow-hidden">
              {leftTab === 'scene' && (
                <SceneOutliner
                  selectedId={selectedEntity}
                  onSelect={handleSelectEntity}
                  onAddEntity={handleAddEntity}
                  onDeleteEntity={handleDeleteEntity}
                  onToggleVisibility={handleToggleVisibility}
                  onToggleLock={handleToggleLock}
                  onReorder={handleReorder}
                  nodes={sceneNodes}
                />
              )}
              {leftTab === 'assets' && <AssetLibrary />}
              {leftTab === 'nodes' && <NodeGraphEditor />}
            </div>
          </div>

          <ResizableHandle direction="vertical" onMouseDown={(e) => startResize('left', e)} />

          <div className="flex-1 flex flex-col overflow-hidden min-w-0">
            <div className="flex-1 overflow-hidden">
              <GameViewport
                isPlaying={isPlaying}
                isGenerating={isGenerating}
                generatingStatus={generatingStatus}
                onTogglePlay={handleTogglePlay}
                onStep={() => addLog('info', '[Engine] Step frame')}
                onTogglePause={() => addLog('info', '[Engine] Pause toggled')}
                fps={fps}
              />
            </div>

            <ResizableHandle direction="horizontal" onMouseDown={(e) => startResize('bottom', e)} />

            <div style={{ height: panelSizes.bottom }} className="flex-shrink-0 flex flex-col overflow-hidden">
              <div className="sl-tab-bar">
                {([['console', 'Console', 'fa-terminal'], ['timeline', 'Timeline', 'fa-film'], ['ai-assistant', 'AI Assistant', 'fa-wand-magic-sparkles']] as const).map(([id, label, icon]) => (
                  <button
                    key={id}
                    onClick={() => setBottomTab(id)}
                    className={`sl-tab ${bottomTab === id ? 'active' : ''}`}
                  >
                    <i className={`fa-solid ${icon} text-[9px]`} />
                    {label}
                  </button>
                ))}
              </div>
              <div className="flex-1 overflow-hidden">
                {bottomTab === 'console' && (
                  <ConsolePanel logs={logs} onAddLog={addLog} onAIGenerate={handleAIPrompt} />
                )}
                {bottomTab === 'timeline' && <TimelineEditor />}
                {bottomTab === 'ai-assistant' && (
                  <div className="h-full flex flex-col bg-[#111]">
                    <div className="flex-1 overflow-y-auto p-3 space-y-2">
                      <div className="text-[11px] text-[#666] text-center py-4">
                        <i className="fa-solid fa-wand-magic-sparkles text-orange-500 text-lg mb-2 block" />
                        AI Assistant ready. Describe what you want to create.
                      </div>
                    </div>
                    <div className="p-2 border-t border-[#1e1e1e]">
                      <AIPromptBar
                        onPrompt={handleAIPrompt}
                        onQuickAction={handleQuickAction}
                        isGenerating={isGenerating}
                      />
                    </div>
                  </div>
                )}
              </div>
            </div>
          </div>

          <ResizableHandle direction="vertical" onMouseDown={(e) => startResize('right', e)} />

          <div style={{ width: panelSizes.right }} className="flex-shrink-0 flex flex-col overflow-hidden">
            <div className="sl-tab-bar">
              {([['inspector', 'Inspector', 'fa-sliders'], ['ai-config', 'AI Config', 'fa-brain']] as const).map(([id, label, icon]) => (
                <button
                  key={id}
                  onClick={() => setRightTab(id)}
                  className={`sl-tab ${rightTab === id ? 'active' : ''}`}
                >
                  <i className={`fa-solid ${icon} text-[9px]`} />
                  {label}
                </button>
              ))}
            </div>
            <div className="flex-1 overflow-hidden">
              {rightTab === 'inspector' && (
                <PropertyEditor
                  selectedName={selectedEntityName}
                  sections={propertySections}
                  onFieldChange={handleFieldChange}
                />
              )}
              {rightTab === 'ai-config' && (
                <div className="sl-panel h-full">
                  <div className="p-3 space-y-3">
                    <div className="sl-property-section">
                      <div className="sl-property-section-header">
                        <i className="fa-solid fa-brain text-[10px] text-purple-500" />
                        <span>Generation Mode</span>
                      </div>
                      <div className="grid grid-cols-3 gap-1.5 px-2 py-2">
                        {(['World', 'Character', 'Mechanic'] as const).map((mode) => (
                          <button
                            key={mode}
                            className="px-2 py-1.5 text-[10px] rounded bg-[#0d0d0d] border border-[#2a2a2a] text-[#888] hover:border-orange-500/40 hover:text-orange-400 transition-all"
                          >
                            {mode}
                          </button>
                        ))}
                      </div>
                    </div>
                    <div className="sl-property-section">
                      <div className="sl-property-section-header">
                        <i className="fa-solid fa-sliders text-[10px] text-orange-500" />
                        <span>Neural Parameters</span>
                      </div>
                      <div className="space-y-2 px-2 py-2">
                        {(['Creativity', 'Coherence', 'Detail'] as const).map((param) => (
                          <div key={param} className="sl-property-row">
                            <span className="sl-property-label !w-20">{param}</span>
                            <input type="range" min={0} max={100} defaultValue={70} className="flex-1 accent-orange-500" />
                            <span className="text-[10px] text-[#555] w-6 text-right">70</span>
                          </div>
                        ))}
                      </div>
                    </div>
                    <div className="px-2">
                      <textarea
                        placeholder="Describe your world model..."
                        className="sl-property-input w-full h-20 resize-none"
                      />
                    </div>
                    <div className="px-2">
                      <button className="w-full py-2 bg-gradient-to-r from-orange-500 to-red-600 text-white rounded-lg text-[12px] font-semibold hover:opacity-90 transition-all flex items-center justify-center gap-2">
                        <i className="fa-solid fa-wand-magic-sparkles text-[10px]" />
                        Generate with AI
                      </button>
                    </div>
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      ) : (
        <div className="flex flex-col overflow-hidden">
          <div className="px-3 py-1.5 border-b border-[#1e1e1e] bg-[#0d0d0d]">
            <AIPromptBar
              onPrompt={handleAIPrompt}
              onQuickAction={handleQuickAction}
              isGenerating={isGenerating}
            />
          </div>
          <div className="flex-1 overflow-hidden">
            {renderModePanel()}
          </div>
        </div>
      )}

      <div className="bg-[#0d0d0d] border-t border-[#1e1e1e] flex items-center px-3 text-[10px] text-[#444] font-mono h-6">
        <div className="flex items-center gap-1.5">
          <div className="w-1.5 h-1.5 bg-green-500 rounded-full pulse-dot" />
          <span className="text-[#666]">SparkLabs Engine v17.0.0</span>
        </div>
        <div className="w-px h-3 bg-[#1e1e1e] mx-2" />
        <span>Scene: Main World</span>
        <div className="w-px h-3 bg-[#1e1e1e] mx-2" />
        <span>Entities: {entityCount}</span>
        <div className="flex-1" />
        <span>WebGL 2.0</span>
        <div className="w-px h-3 bg-[#1e1e1e] mx-2" />
        <span className={fps >= 55 ? 'text-green-600' : 'text-yellow-600'}>{fps} FPS</span>
        <div className="w-px h-3 bg-[#1e1e1e] mx-2" />
        <span className="text-orange-500">AI Ready</span>
      </div>
      </div>
    </div>
  );
};

export default SparkLabsEditor;
