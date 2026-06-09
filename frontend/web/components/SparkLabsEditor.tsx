import React, { useCallback, useRef, useEffect } from 'react';
import EditorToolbar from './EditorToolbar';
import SceneOutliner from './SceneOutliner';
import GameViewport from './GameViewport';
import PropertyEditor from './PropertyEditor';
import NodeGraphEditor from './NodeGraphEditor';
import AssetLibrary from './AssetLibrary';
import AIPromptBar from './AIPromptBar';
import ConsolePanel from './ConsolePanel';
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
import SceneDirectorPanel from './SceneDirectorPanel';
import WorldStreamerPanel from './WorldStreamerPanel';
import AgentIntelligenceCorePanel from './AgentIntelligenceCorePanel';
import EngineUnificationCorePanel from './EngineUnificationCorePanel';
import { LifecyclePanel, SlashCommandsPanel, ValidationHooksPanel } from './LifecyclePanels';
import { TaskExecutorPanel } from './TaskExecutorPanel';
import NotificationToast from './NotificationToast';
import KeyboardShortcuts from './KeyboardShortcuts';
import { useEditorStore } from '../store/editorStore';
import { processAIPrompt, initializeEditorBackend, startWorldInBackend, stopWorldInBackend } from '../services/aiService';
import { sceneBridge } from '../services/sceneBridge';
import { useWebSocket } from '../hooks/useWebSocket';
import type { ViewMode } from '../types';
import type { ShortcutDef } from './KeyboardShortcuts';

type TransformTool = 'move' | 'rotate' | 'scale';

const MIN_PANEL_SIZES = { left: 180, right: 200, bottom: 80 };

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
  const store = useEditorStore();
  const {
    activeMode, currentTool, isPlaying, isPaused, selectedEntity, selectedEntityName,
    sceneNodes, propertySections, logs, aiGeneration, fps,
    leftTab, rightTab, bottomTab,
    leftPanelWidth, rightPanelWidth, bottomPanelHeight,
    backendConnected,
    setActiveMode, setCurrentTool, togglePlay, togglePause,
    selectEntity, addSceneNode, removeSceneNode, reorderNodes, toggleNodeVisibility, toggleNodeLock,
    updatePropertyField, addLog, pushHistory, undo, redo,
    setLeftTab, setRightTab, setBottomTab,
    setLeftPanelWidth, setRightPanelWidth, setBottomPanelHeight,
  } = store;

  const containerRef = useRef<HTMLDivElement>(null);
  const resizingRef = useRef<{ type: 'left' | 'right' | 'bottom'; startX: number; startSize: number } | null>(null);
  const fpsFrameRef = useRef<number>(0);
  const fpsLastTimeRef = useRef<number>(performance.now());
  const fpsCountRef = useRef<number>(0);
  const [toasts, setToasts] = React.useState<{ id: string; type: 'success' | 'error' | 'warning' | 'info'; title: string; message?: string; duration?: number }[]>([]);

  useEffect(() => {
    initializeEditorBackend();
  }, []);

  const ws = useWebSocket();

  useEffect(() => {
    const measureFps = (now: number) => {
      fpsCountRef.current++;
      if (now - fpsLastTimeRef.current >= 1000) {
        useEditorStore.getState().setFps(fpsCountRef.current);
        fpsCountRef.current = 0;
        fpsLastTimeRef.current = now;
      }
      fpsFrameRef.current = requestAnimationFrame(measureFps);
    };
    fpsFrameRef.current = requestAnimationFrame(measureFps);
    return () => cancelAnimationFrame(fpsFrameRef.current);
  }, []);

  const addToast = useCallback((toast: { type: 'success' | 'error' | 'warning' | 'info'; title: string; message?: string; duration?: number }) => {
    const id = `toast_${Date.now()}`;
    setToasts((prev) => [...prev, { ...toast, id }]);
    setTimeout(() => setToasts((prev) => prev.filter((t) => t.id !== id)), toast.duration || 3000);
  }, []);

  useEffect(() => {
    const handleMouseMove = (e: MouseEvent) => {
      if (!resizingRef.current || !containerRef.current) return;
      const { type, startX, startSize } = resizingRef.current;
      const delta = e.clientX - startX;
      if (type === 'left') {
        setLeftPanelWidth(Math.max(MIN_PANEL_SIZES.left, startSize + delta));
      } else if (type === 'right') {
        setRightPanelWidth(Math.max(MIN_PANEL_SIZES.right, startSize - delta));
      } else if (type === 'bottom') {
        const dy = e.clientY - startX;
        setBottomPanelHeight(Math.max(MIN_PANEL_SIZES.bottom, startSize - dy));
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
  }, [setLeftPanelWidth, setRightPanelWidth, setBottomPanelHeight]);

  const startResize = useCallback((type: 'left' | 'right' | 'bottom', e: React.MouseEvent) => {
    e.preventDefault();
    const startX = type === 'bottom' ? e.clientY : e.clientX;
    const startSize = type === 'left' ? leftPanelWidth : type === 'right' ? rightPanelWidth : bottomPanelHeight;
    resizingRef.current = { type, startX, startSize };
    document.body.style.cursor = type === 'bottom' ? 'row-resize' : 'col-resize';
    document.body.style.userSelect = 'none';
  }, [leftPanelWidth, rightPanelWidth, bottomPanelHeight]);

  const handleSelectEntity = useCallback((id: string, name: string) => {
    selectEntity(id, name);
    addLog('info', `[Editor] Selected: ${name}`);
  }, [selectEntity, addLog]);

  const handleAddEntity = useCallback(() => {
    pushHistory();
    const newEntity = {
      id: `entity_${Date.now()}`,
      name: 'New Entity',
      icon: 'fa-cube',
      iconColor: '#60a5fa',
      type: 'entity' as const,
      visible: true,
      locked: false,
      parentId: 'root',
      children: [],
    };
    addSceneNode(newEntity, 'root');
    addLog('success', '[Editor] Entity added to scene');
  }, [addSceneNode, addLog]);

  const handleDeleteEntity = useCallback((id: string) => {
    pushHistory();
    removeSceneNode(id);
    addLog('info', '[Editor] Entity deleted');
  }, [removeSceneNode, addLog]);

  const handleReorder = useCallback((dragId: string, dropId: string, position: 'before' | 'after' | 'inside') => {
    pushHistory();
    reorderNodes(dragId, dropId, position);
    addLog('info', `[Editor] Reordered ${dragId} ${position} ${dropId}`);
  }, [reorderNodes, addLog]);

  const handleFieldChange = useCallback((sectionId: string, fieldKey: string, value: unknown) => {
    updatePropertyField(sectionId, fieldKey, value);

    if (sectionId === 'transform' && selectedEntity) {
      const sections = useEditorStore.getState().propertySections;
      const transformSection = sections.find((s) => s.id === 'transform');
      if (transformSection) {
        const posField = transformSection.fields.find((f) => f.key === 'position');
        const rotField = transformSection.fields.find((f) => f.key === 'rotation');
        const sclField = transformSection.fields.find((f) => f.key === 'scale');

        const pos = (fieldKey === 'position' ? value : posField?.value) as number[] | undefined;
        const rot = (fieldKey === 'rotation' ? value : rotField?.value) as number[] | undefined;
        const scl = (fieldKey === 'scale' ? value : sclField?.value) as number[] | undefined;

        sceneBridge.updateEntityTransform(
          selectedEntity,
          pos as [number, number, number] | undefined,
          rot as [number, number, number] | undefined,
          scl as [number, number, number] | undefined,
        );
      }
    }
  }, [updatePropertyField, selectedEntity]);

  const handleAIGenerate = useCallback(() => {
    setActiveMode('dashboard');
  }, [setActiveMode]);

  const handleAIPrompt = useCallback(async (prompt: string) => {
    await processAIPrompt(prompt);
  }, []);

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

  const handleTogglePlay = useCallback(async () => {
    const willPlay = !isPlaying;
    togglePlay();
    addLog(willPlay ? 'success' : 'info', willPlay ? '[Engine] Play mode started' : '[Engine] Play mode stopped');

    if (willPlay) {
      try {
        const { initializeEditorBackend, createWorldInBackend, startWorldInBackend } = await import('../services/aiService');
        await initializeEditorBackend();
        const wId = await createWorldInBackend('PlayWorld');
        if (wId) {
          await startWorldInBackend();
          addLog('success', '[Engine] Game runtime executing');
        }
        if (ws.send) {
          ws.send({ type: 'engine_command', command: 'start' });
        }
      } catch (e) {
        addLog('warn', '[Engine] Running in simulation mode');
      }
    } else {
      try {
        const { stopWorldInBackend } = await import('../services/aiService');
        await stopWorldInBackend();
        if (ws.send) {
          ws.send({ type: 'engine_command', command: 'stop' });
        }
      } catch {
        addLog('info', '[Engine] Stopped (standalone)');
      }
    }
  }, [isPlaying, togglePlay, addLog, ws]);

  const handleToolChange = useCallback((tool: TransformTool) => {
    setCurrentTool(tool);
    addLog('info', `[Editor] Tool changed to: ${tool}`);
  }, [setCurrentTool, addLog]);

  const handleModeSwitch = useCallback((mode: string) => {
    setActiveMode(mode as ViewMode);
    addLog('info', `[Editor] Switched to ${mode}`);
  }, [setActiveMode, addLog]);

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
      case 'scene-director': return <SceneDirectorPanel />;
      case 'world-streamer': return <WorldStreamerPanel />;
      case 'intelligence-core': return <AgentIntelligenceCorePanel />;
      case 'engine-unification': return <EngineUnificationCorePanel />;
      default: return <WelcomeDashboard onModeSwitch={handleModeSwitch} onAIPrompt={handleAIPrompt} />;
    }
  };

  const isEditorMode = activeMode === 'dashboard';
  const entityCount = sceneNodes.reduce((acc, n) => acc + 1 + n.children.length, 0);

  const shortcuts: ShortcutDef[] = [
    { key: 'z', ctrl: true, label: 'Undo', category: 'Edit', action: () => undo() },
    { key: 'z', ctrl: true, shift: true, label: 'Redo', category: 'Edit', action: () => redo() },
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
      <NotificationToast toasts={toasts} onDismiss={(id) => setToasts((prev) => prev.filter((t) => t.id !== id))} />
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
          <div style={{ width: leftPanelWidth }} className="flex-shrink-0 flex flex-col overflow-hidden">
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
                  onToggleVisibility={toggleNodeVisibility}
                  onToggleLock={toggleNodeLock}
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
                isGenerating={aiGeneration.isGenerating}
                generatingStatus={aiGeneration.phase || aiGeneration.status}
                onTogglePlay={handleTogglePlay}
                onStep={() => {
                  addLog('info', '[Engine] Step frame');
                  if (ws.send) ws.send({ type: 'engine_command', command: 'step' });
                }}
                onTogglePause={() => { togglePause(); addLog('info', '[Engine] Pause toggled'); }}
                fps={fps}
              />
            </div>

            <ResizableHandle direction="horizontal" onMouseDown={(e) => startResize('bottom', e)} />

            <div style={{ height: bottomPanelHeight }} className="flex-shrink-0 flex flex-col overflow-hidden">
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
                        isGenerating={aiGeneration.isGenerating}
                      />
                    </div>
                  </div>
                )}
              </div>
            </div>
          </div>

          <ResizableHandle direction="vertical" onMouseDown={(e) => startResize('right', e)} />

          <div style={{ width: rightPanelWidth }} className="flex-shrink-0 flex flex-col overflow-hidden">
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
                      <button
                        onClick={() => handleAIPrompt('Generate based on current configuration')}
                        className="w-full py-2 bg-gradient-to-r from-orange-500 to-red-600 text-white rounded-lg text-[12px] font-semibold hover:opacity-90 transition-all flex items-center justify-center gap-2"
                      >
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
              isGenerating={aiGeneration.isGenerating}
            />
          </div>
          <div className="flex-1 overflow-hidden">
            {renderModePanel()}
          </div>
        </div>
      )}

      <div className="bg-[#0d0d0d] border-t border-[#1e1e1e] flex items-center px-3 text-[10px] text-[#444] font-mono h-6">
        <div className="flex items-center gap-1.5">
          <div className={`w-1.5 h-1.5 rounded-full pulse-dot ${backendConnected ? 'bg-green-500' : 'bg-yellow-500'}`} />
          <span className="text-[#666]">SparkLabs Engine v17.0.0</span>
        </div>
        <div className="w-px h-3 bg-[#1e1e1e] mx-2" />
        <span>Scene: Main World</span>
        <div className="w-px h-3 bg-[#1e1e1e] mx-2" />
        <span>Entities: {entityCount}</span>
        <div className="w-px h-3 bg-[#1e1e1e] mx-2" />
        <span>WebGL 2.0</span>
        <div className="w-px h-3 bg-[#1e1e1e] mx-2" />
        <span className={fps >= 55 ? 'text-green-600' : 'text-yellow-600'}>{fps} FPS</span>
        <div className="w-px h-3 bg-[#1e1e1e] mx-2" />
        <span className={backendConnected ? 'text-green-500' : 'text-yellow-500'}>
          {backendConnected ? 'Backend Connected' : 'Standalone Mode'}
        </span>
        <div className="flex-1" />
        <span className="text-orange-500">AI Ready</span>
      </div>
      </div>
    </div>
  );
};

export default SparkLabsEditor;
