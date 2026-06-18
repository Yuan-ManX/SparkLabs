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
import AgentMetacognitionPanel from './AgentMetacognitionPanel';
import AgentPredictiveIntelligencePanel from './AgentPredictiveIntelligencePanel';
import AgentCausalReasoningPanel from './AgentCausalReasoningPanel';
import AgentMultiObjectiveOptimizerPanel from './AgentMultiObjectiveOptimizerPanel';
import EngineVolumetricRenderingPanel from './EngineVolumetricRenderingPanel';
import EngineCrowdDynamicsPanel from './EngineCrowdDynamicsPanel';
import EngineFluidDynamicsPanel from './EngineFluidDynamicsPanel';
import AgentWorldPerceptionPanel from './AgentWorldPerceptionPanel';
import AgentDynamicNarrativePanel from './AgentDynamicNarrativePanel';
import EngineProceduralAnimationPanel from './EngineProceduralAnimationPanel';
import EngineObjectPoolPanel from './EngineObjectPoolPanel';
import EngineRuntimeScriptingPanel from './EngineRuntimeScriptingPanel';
import AgentFunctionDispatcherPanel from './AgentFunctionDispatcherPanel';
import AgentWorldInteractionPanel from './AgentWorldInteractionPanel';
import EngineSpriteBatcherPanel from './EngineSpriteBatcherPanel';
import EngineVisualEventSheetPanel from './EngineVisualEventSheetPanel';
import EngineNodeComposerPanel from './EngineNodeComposerPanel';
import EngineParticlePanel from './EngineParticlePanel';
import EngineTilemapPanel from './EngineTilemapPanel';
import EngineInputPanel from './EngineInputPanel';
import EngineCameraPanel from './EngineCameraPanel';
import EngineAnimationPanel from './EngineAnimationPanel';
import EngineScenePanel from './EngineScenePanel';
import AgentCreativeDirectorPanel from './AgentCreativeDirectorPanel';
import AgentLiveDebuggerPanel from './AgentLiveDebuggerPanel';
import AgentGameCodeGeneratorPanel from './AgentGameCodeGeneratorPanel';
import AgentBalanceOptimizerPanel from './AgentBalanceOptimizerPanel';
import EngineNetworkReplicationPanel from './EngineNetworkReplicationPanel';
import EngineTerrainSystemPanel from './EngineTerrainSystemPanel';
import AgentEngineOrchestratorPanel from './AgentEngineOrchestratorPanel';
import AgentDashboard from './AgentDashboard';
import AgentLearningLoopPanel from './AgentLearningLoopPanel';
import AgentMemoryGraphPanel from './AgentMemoryGraphPanel';
import AgentQuestGeneratorPanel from './AgentQuestGeneratorPanel';
import AgentStoryForgePanel from './AgentStoryForgePanel';
import AgentToolForgePanel from './AgentToolForgePanel';
import AgentWorldArchitectPanel from './AgentWorldArchitectPanel';
import AgentEmergentNarrativePanel from './AgentEmergentNarrativePanel';
import AgentEmotionSynthesisPanel from './AgentEmotionSynthesisPanel';
import AgentSelfEvolutionPanel from './AgentSelfEvolutionPanel';
import AgentSkillAccumulatorPanel from './AgentSkillAccumulatorPanel';
import AgentLayeredMemoryPanel from './AgentLayeredMemoryPanel';
import AgentWorldSimulatorPanel from './AgentWorldSimulatorPanel';
import AgentEmergentStorytellerPanel from './AgentEmergentStorytellerPanel';
import EngineNodeEditorPanel from './EngineNodeEditorPanel';
import EngineSceneSerializerPanel from './EngineSceneSerializerPanel';
import EngineSignalBusPanel from './EngineSignalBusPanel';
import AgentTheoryOfMindPanel from './AgentTheoryOfMindPanel';
import AgentCounterfactualSimulatorPanel from './AgentCounterfactualSimulatorPanel';
import AgentSkillLifecyclePanel from './AgentSkillLifecyclePanel';
import AgentTimelineBrancherPanel from './AgentTimelineBrancherPanel';
import EngineEcosystemDynamicsPanel from './EngineEcosystemDynamicsPanel';
import EngineCivilizationEvolutionPanel from './EngineCivilizationEvolutionPanel';
import EngineProceduralCityPanel from './EngineProceduralCityPanel';
import EngineFlowStateMonitorPanel from './EngineFlowStateMonitorPanel';
import AgentDialogueEnginePanel from './AgentDialogueEnginePanel';
import AgentIntentRouterPanel from './AgentIntentRouterPanel';
import AgentGatewayPanel from './AgentGatewayPanel';
import AgentEnvironmentManagerPanel from './AgentEnvironmentManagerPanel';
import AgentGodModeControllerPanel from './AgentGodModeControllerPanel';
import AgenticCodingPanel from './AgenticCodingPanel';
import ConversationMemoryPanel from './ConversationMemoryPanel';
import ContextWeaverPanel from './ContextWeaverPanel';
import KnowledgeSynthesisPanel from './KnowledgeSynthesisPanel';
import LearningLoopPanel from './LearningLoopPanel';
import ReflectionLoopPanel from './ReflectionLoopPanel';
import MemoryHierarchyPanel from './MemoryHierarchyPanel';
import MemoryConsolidatorPanel from './MemoryConsolidatorPanel';
import MemoryOrchestratorPanel from './MemoryOrchestratorPanel';
import IntentCascadePanel from './IntentCascadePanel';
import BehaviorDesignerPanel from './BehaviorDesignerPanel';
import ReasoningChainPanel from './ReasoningChainPanel';
import ChainOfThoughtPanel from './ChainOfThoughtPanel';
import DelegationFrameworkPanel from './DelegationFrameworkPanel';
import CollaborationProtocolPanel from './CollaborationProtocolPanel';
import SwarmPlannerPanel from './SwarmPlannerPanel';
import MultiAgentCoordinatorPanel from './MultiAgentCoordinatorPanel';
import SkillForgePanel from './SkillForgePanel';
import SkillsHubPanel from './SkillsHubPanel';
import CapabilityRegistryPanel from './CapabilityRegistryPanel';
import SelfOptimizationPanel from './SelfOptimizationPanel';
import PlaytestOrchestratorPanel from './PlaytestOrchestratorPanel';
import PlaytestSimulatorPanel from './PlaytestSimulatorPanel';
import BugForensicsPanel from './BugForensicsPanel';
import HeatmapAnalyzerPanel from './HeatmapAnalyzerPanel';
import GameplayEcosystemPanel from './GameplayEcosystemPanel';
import GameDesignIntelligencePanel from './GameDesignIntelligencePanel';
import GameForecasterPanel from './GameForecasterPanel';
import GameReasonerPanel from './GameReasonerPanel';
import EconomySimulatorPanel from './EconomySimulatorPanel';
import MonetizationDesignerPanel from './MonetizationDesignerPanel';
import SocialSimulationPanel from './SocialSimulationPanel';
import SimulationControllerPanel from './SimulationControllerPanel';
import WorldBuilderPanel from './WorldBuilderPanel';
import WorldComposerPanel from './WorldComposerPanel';
import WorldSimulationPanel from './WorldSimulationPanel';
import ABTestRunnerPanel from './ABTestRunnerPanel';
import ExperimentFrameworkPanel from './ExperimentFrameworkPanel';
import FederatedLearnerPanel from './FederatedLearnerPanel';
import TestingDashboard from './TestingDashboard';
import ECSPanel from './ECSPanel';
import RenderPipelinePanel from './RenderPipelinePanel';
import RenderLayerPanel from './RenderLayerPanel';
import RenderPassPanel from './RenderPassPanel';
import AudioSynthesisPanel from './AudioSynthesisPanel';
import AudioLayeringPanel from './AudioLayeringPanel';
import InteractiveAudioPanel from './InteractiveAudioPanel';
import ProceduralAudioPanel from './ProceduralAudioPanel';
import PhysicsWorld2DPanel from './PhysicsWorld2DPanel';
import PhysicsMaterialPanel from './PhysicsMaterialPanel';
import BehaviorLibraryPanel from './BehaviorLibraryPanel';
import PostProcessingPanel from './PostProcessingPanel';
import GPUBatchRenderingPanel from './GPUBatchRenderingPanel';
import OcclusionCullingPanel from './OcclusionCullingPanel';
import LODSystemPanel from './LODSystemPanel';
import LODGatePanel from './LODGatePanel';
import LightCullingPanel from './LightCullingPanel';
import Lighting2DPanel from './Lighting2DPanel';
import ShadowCastingPanel from './ShadowCastingPanel';
import SkyboxRendererPanel from './SkyboxRendererPanel';
import TrailRendererPanel from './TrailRendererPanel';
import DecalSystemPanel from './DecalSystemPanel';
import WaterSimulationPanel from './WaterSimulationPanel';
import WeatherSystemPanel from './WeatherSystemPanel';
import BiomeGenerationPanel from './BiomeGenerationPanel';
import ProceduralWorldPanel from './ProceduralWorldPanel';
import ProceduralDungeonPanel from './ProceduralDungeonPanel';
import ProceduralSynthesisPanel from './ProceduralSynthesisPanel';
import TextureAtlasPanel from './TextureAtlasPanel';
import PrefabComposerPanel from './PrefabComposerPanel';
import ComponentAssemblerPanel from './ComponentAssemblerPanel';
import EntityBlueprintPanel from './EntityBlueprintPanel';
import CustomObjectTypesPanel from './CustomObjectTypesPanel';
import SpriteAnimatorPanel from './SpriteAnimatorPanel';
import SkeletonDeformerPanel from './SkeletonDeformerPanel';
import SignalBusPanel from './SignalBusPanel';
import StateSynchronizerPanel from './StateSynchronizerPanel';
import StateMachineEnginePanel from './StateMachineEnginePanel';
import VisualScriptingPanel from './VisualScriptingPanel';
import VisualScriptRuntimePanel from './VisualScriptRuntimePanel';
import EventScriptingPanel from './EventScriptingPanel';
import NavMeshForgePanel from './NavMeshForgePanel';
import PathfindingPanel from './PathfindingPanel';
import SpatialClusterPanel from './SpatialClusterPanel';
import GestureRecognizerPanel from './GestureRecognizerPanel';
import InputAbstractionPanel from './InputAbstractionPanel';
import InputMapPanel from './InputMapPanel';
import CameraControllerPanel from './CameraControllerPanel';
import ParallaxBackgroundPanel from './ParallaxBackgroundPanel';
import ParticleEmitterPanel from './ParticleEmitterPanel';
import SceneStackPanel from './SceneStackPanel';
import SceneTransitionPanel from './SceneTransitionPanel';
import ImportPipelinePanel from './ImportPipelinePanel';
import BuildExporter from './BuildExporter';
import ProjectExporterPanel from './ProjectExporterPanel';
import PlatformLayerPanel from './PlatformLayerPanel';
import ResourceSerializerPanel from './ResourceSerializerPanel';
import ProfileLoaderPanel from './ProfileLoaderPanel';
import ProgressiveLoadingPanel from './ProgressiveLoadingPanel';
import AssetStreamerPanel from './AssetStreamerPanel';
import AssetBundlerPanel from './AssetBundlerPanel';
import AssetHarmonizerPanel from './AssetHarmonizerPanel';
import AssetSynthesizerPanel from './AssetSynthesizerPanel';
import MaterialGraphPanel from './MaterialGraphPanel';
import FrameComposerPanel from './FrameComposerPanel';
import FrameTimerPanel from './FrameTimerPanel';
import GameRuntimeOrchestratorPanel from './GameRuntimeOrchestratorPanel';
import GameStateAnalyzerPanel from './GameStateAnalyzerPanel';
import TileBrushPanel from './TileBrushPanel';
import TileMapOptimizerPanel from './TileMapOptimizerPanel';
import TileMapRuntimePanel from './TileMapRuntimePanel';
import EngineEnvironmentManagerPanel from './EngineEnvironmentManagerPanel';
import SecurityScannerPanel from './SecurityScannerPanel';
import AuditTrailPanel from './AuditTrailPanel';
import VerificationPipelinePanel from './VerificationPipelinePanel';
import PersonaVaultPanel from './PersonaVaultPanel';
import PersonalitySystemPanel from './PersonalitySystemPanel';
import AgentCronSchedulerPanel from './AgentCronSchedulerPanel';
import DocumentSynthesizerPanel from './DocumentSynthesizerPanel';
import DeveloperOraclePanel from './DeveloperOraclePanel';
import PromptOptimizerPanel from './PromptOptimizerPanel';
import ProviderSwitchPanel from './ProviderSwitchPanel';
import StreamingScrubberPanel from './StreamingScrubberPanel';
import SessionNexusPanel from './SessionNexusPanel';
import SessionSnapshotPanel from './SessionSnapshotPanel';
import ToolRegistryPanel from './ToolRegistryPanel';
import TelemetryPipelinePanel from './TelemetryPipelinePanel';
import JournalSystemPanel from './JournalSystemPanel';
import KanbanCoordinatorPanel from './KanbanCoordinatorPanel';
import LocalizationHubPanel from './LocalizationHubPanel';
import ExtensionSdkPanel from './ExtensionSdkPanel';
import InsightsGeneratorPanel from './InsightsGeneratorPanel';
import EcosystemHubPanel from './EcosystemHubPanel';
import InteractionSynthesisPanel from './InteractionSynthesisPanel';
import InteractionDesignerPanel from './InteractionDesignerPanel';
import NarrativeBranchPanel from './NarrativeBranchPanel';
import ConcurrencyManagerPanel from './ConcurrencyManagerPanel';
import DelegationBrokerPanel from './DelegationBrokerPanel';
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
      case 'metacognition': return <AgentMetacognitionPanel />;
      case 'predictive-intelligence': return <AgentPredictiveIntelligencePanel />;
      case 'causal-reasoning': return <AgentCausalReasoningPanel />;
      case 'multi-objective': return <AgentMultiObjectiveOptimizerPanel />;
      case 'volumetric-rendering': return <EngineVolumetricRenderingPanel />;
      case 'crowd-dynamics': return <EngineCrowdDynamicsPanel />;
      case 'fluid-dynamics': return <EngineFluidDynamicsPanel />;
      case 'world-perception': return <AgentWorldPerceptionPanel />;
      case 'dynamic-narrative': return <AgentDynamicNarrativePanel />;
      case 'procedural-animation': return <EngineProceduralAnimationPanel />;
      case 'object-pool': return <EngineObjectPoolPanel />;
      case 'runtime-scripting': return <EngineRuntimeScriptingPanel />;
      case 'function-dispatcher': return <AgentFunctionDispatcherPanel />;
      case 'world-interaction': return <AgentWorldInteractionPanel />;
      case 'sprite-batcher': return <EngineSpriteBatcherPanel />;
      case 'visual-event-sheet': return <EngineVisualEventSheetPanel />;
      case 'node-composer': return <EngineNodeComposerPanel />;
      case 'particle-system': return <EngineParticlePanel />;
      case 'tilemap-system': return <EngineTilemapPanel />;
      case 'input-mapping': return <EngineInputPanel />;
      case 'camera-system': return <EngineCameraPanel />;
      case 'animation-controller': return <EngineAnimationPanel />;
      case 'scene-transition': return <EngineScenePanel />;
      case 'creative-director': return <AgentCreativeDirectorPanel />;
      case 'live-debugger': return <AgentLiveDebuggerPanel />;
      case 'game-code-generator': return <AgentGameCodeGeneratorPanel />;
      case 'balance-optimizer': return <AgentBalanceOptimizerPanel />;
      case 'network-replication': return <EngineNetworkReplicationPanel />;
      case 'terrain-system': return <EngineTerrainSystemPanel />;
      case 'agent-engine-orchestrator': return <AgentEngineOrchestratorPanel />;
      case 'agent-dashboard': return <AgentDashboard />;
      case 'learning-loop-panel': return <AgentLearningLoopPanel />;
      case 'memory-graph': return <AgentMemoryGraphPanel />;
      case 'quest-generator': return <AgentQuestGeneratorPanel />;
      case 'story-forge': return <AgentStoryForgePanel />;
      case 'tool-forge': return <AgentToolForgePanel />;
      case 'world-architect': return <AgentWorldArchitectPanel />;
      case 'emergent-narrative': return <AgentEmergentNarrativePanel />;
      case 'emotion-synthesis': return <AgentEmotionSynthesisPanel />;
      case 'self-evolution': return <AgentSelfEvolutionPanel />;
      case 'skill-accumulator': return <AgentSkillAccumulatorPanel />;
      case 'layered-memory': return <AgentLayeredMemoryPanel />;
      case 'world-simulator': return <AgentWorldSimulatorPanel />;
      case 'emergent-storyteller': return <AgentEmergentStorytellerPanel />;
      case 'node-editor-panel': return <EngineNodeEditorPanel />;
      case 'scene-serializer': return <EngineSceneSerializerPanel />;
      case 'engine-signal-bus': return <EngineSignalBusPanel />;
      case 'dialogue-engine': return <AgentDialogueEnginePanel />;
      case 'intent-router': return <AgentIntentRouterPanel />;
      case 'agent-gateway': return <AgentGatewayPanel />;
      case 'environment-manager': return <AgentEnvironmentManagerPanel />;
      case 'god-mode': return <AgentGodModeControllerPanel />;
      case 'agentic-coding': return <AgenticCodingPanel />;
      case 'conversation-memory': return <ConversationMemoryPanel />;
      case 'context-weaver': return <ContextWeaverPanel />;
      case 'knowledge-synthesis': return <KnowledgeSynthesisPanel />;
      case 'reflection-loop': return <ReflectionLoopPanel />;
      case 'memory-hierarchy': return <MemoryHierarchyPanel />;
      case 'memory-consolidator': return <MemoryConsolidatorPanel />;
      case 'memory-orchestrator': return <MemoryOrchestratorPanel />;
      case 'intent-cascade': return <IntentCascadePanel />;
      case 'behavior-designer': return <BehaviorDesignerPanel />;
      case 'reasoning-chain': return <ReasoningChainPanel />;
      case 'chain-of-thought': return <ChainOfThoughtPanel />;
      case 'delegation-framework': return <DelegationFrameworkPanel />;
      case 'collaboration-protocol': return <CollaborationProtocolPanel />;
      case 'swarm-planner': return <SwarmPlannerPanel />;
      case 'multi-agent-coordinator': return <MultiAgentCoordinatorPanel />;
      case 'skill-forge': return <SkillForgePanel />;
      case 'skills-hub': return <SkillsHubPanel />;
      case 'capability-registry': return <CapabilityRegistryPanel />;
      case 'self-optimization': return <SelfOptimizationPanel />;
      case 'playtest-orchestrator': return <PlaytestOrchestratorPanel />;
      case 'playtest-simulator': return <PlaytestSimulatorPanel />;
      case 'bug-forensics': return <BugForensicsPanel />;
      case 'heatmap-analyzer': return <HeatmapAnalyzerPanel />;
      case 'gameplay-ecosystem': return <GameplayEcosystemPanel />;
      case 'game-design-intelligence': return <GameDesignIntelligencePanel />;
      case 'game-forecaster': return <GameForecasterPanel />;
      case 'game-reasoner': return <GameReasonerPanel />;
      case 'economy-simulator': return <EconomySimulatorPanel />;
      case 'monetization-designer': return <MonetizationDesignerPanel />;
      case 'social-simulation': return <SocialSimulationPanel />;
      case 'simulation-controller': return <SimulationControllerPanel />;
      case 'world-builder-panel': return <WorldBuilderPanel />;
      case 'world-composer': return <WorldComposerPanel />;
      case 'world-simulation': return <WorldSimulationPanel />;
      case 'ab-test-runner': return <ABTestRunnerPanel />;
      case 'experiment-framework': return <ExperimentFrameworkPanel />;
      case 'federated-learner': return <FederatedLearnerPanel />;
      case 'testing-dashboard': return <TestingDashboard />;
      case 'ecs-system': return <ECSPanel />;
      case 'render-pipeline': return <RenderPipelinePanel />;
      case 'render-layer': return <RenderLayerPanel />;
      case 'render-pass': return <RenderPassPanel />;
      case 'audio-synthesis': return <AudioSynthesisPanel />;
      case 'audio-layering': return <AudioLayeringPanel />;
      case 'interactive-audio': return <InteractiveAudioPanel />;
      case 'procedural-audio': return <ProceduralAudioPanel />;
      case 'physics-world-2d': return <PhysicsWorld2DPanel />;
      case 'physics-material': return <PhysicsMaterialPanel />;
      case 'behavior-library': return <BehaviorLibraryPanel />;
      case 'post-processing': return <PostProcessingPanel />;
      case 'gpu-batch-rendering': return <GPUBatchRenderingPanel />;
      case 'occlusion-culling': return <OcclusionCullingPanel />;
      case 'lod-system': return <LODSystemPanel />;
      case 'lod-gate': return <LODGatePanel />;
      case 'light-culling': return <LightCullingPanel />;
      case 'lighting-2d': return <Lighting2DPanel />;
      case 'shadow-casting': return <ShadowCastingPanel />;
      case 'skybox-renderer': return <SkyboxRendererPanel />;
      case 'trail-renderer': return <TrailRendererPanel />;
      case 'decal-system': return <DecalSystemPanel />;
      case 'water-simulation': return <WaterSimulationPanel />;
      case 'weather-system': return <WeatherSystemPanel />;
      case 'biome-generation': return <BiomeGenerationPanel />;
      case 'procedural-world': return <ProceduralWorldPanel />;
      case 'procedural-dungeon': return <ProceduralDungeonPanel />;
      case 'procedural-synthesis': return <ProceduralSynthesisPanel />;
      case 'texture-atlas': return <TextureAtlasPanel />;
      case 'prefab-composer': return <PrefabComposerPanel />;
      case 'component-assembler': return <ComponentAssemblerPanel />;
      case 'entity-blueprint': return <EntityBlueprintPanel />;
      case 'custom-object-types': return <CustomObjectTypesPanel />;
      case 'sprite-animator': return <SpriteAnimatorPanel />;
      case 'skeleton-deformer': return <SkeletonDeformerPanel />;
      case 'signal-bus': return <SignalBusPanel />;
      case 'state-synchronizer': return <StateSynchronizerPanel />;
      case 'state-machine-engine': return <StateMachineEnginePanel />;
      case 'visual-scripting-panel': return <VisualScriptingPanel />;
      case 'visual-script-runtime': return <VisualScriptRuntimePanel />;
      case 'event-scripting': return <EventScriptingPanel />;
      case 'navmesh-forge': return <NavMeshForgePanel />;
      case 'pathfinding': return <PathfindingPanel />;
      case 'spatial-cluster': return <SpatialClusterPanel />;
      case 'gesture-recognizer': return <GestureRecognizerPanel />;
      case 'input-abstraction': return <InputAbstractionPanel />;
      case 'input-map': return <InputMapPanel />;
      case 'camera-controller': return <CameraControllerPanel />;
      case 'parallax-background': return <ParallaxBackgroundPanel />;
      case 'particle-emitter': return <ParticleEmitterPanel />;
      case 'scene-stack': return <SceneStackPanel />;
      case 'import-pipeline': return <ImportPipelinePanel />;
      case 'build-exporter': return <BuildExporter />;
      case 'project-exporter': return <ProjectExporterPanel />;
      case 'platform-layer': return <PlatformLayerPanel />;
      case 'resource-serializer': return <ResourceSerializerPanel />;
      case 'profile-loader': return <ProfileLoaderPanel />;
      case 'progressive-loading': return <ProgressiveLoadingPanel />;
      case 'asset-streamer': return <AssetStreamerPanel />;
      case 'asset-bundler': return <AssetBundlerPanel />;
      case 'asset-harmonizer': return <AssetHarmonizerPanel />;
      case 'asset-synthesizer': return <AssetSynthesizerPanel />;
      case 'material-graph': return <MaterialGraphPanel />;
      case 'frame-composer': return <FrameComposerPanel />;
      case 'frame-timer': return <FrameTimerPanel />;
      case 'game-runtime-orchestrator': return <GameRuntimeOrchestratorPanel />;
      case 'game-state-analyzer': return <GameStateAnalyzerPanel />;
      case 'tile-brush': return <TileBrushPanel />;
      case 'tile-map-optimizer': return <TileMapOptimizerPanel />;
      case 'tile-map-runtime': return <TileMapRuntimePanel />;
      case 'engine-environment-manager': return <EngineEnvironmentManagerPanel />;
      case 'security-scanner': return <SecurityScannerPanel />;
      case 'audit-trail': return <AuditTrailPanel />;
      case 'verification-pipeline': return <VerificationPipelinePanel />;
      case 'persona-vault': return <PersonaVaultPanel />;
      case 'personality-system': return <PersonalitySystemPanel />;
      case 'agent-cron-scheduler': return <AgentCronSchedulerPanel />;
      case 'document-synthesizer': return <DocumentSynthesizerPanel />;
      case 'developer-oracle': return <DeveloperOraclePanel />;
      case 'prompt-optimizer': return <PromptOptimizerPanel />;
      case 'provider-switch': return <ProviderSwitchPanel />;
      case 'streaming-scrubber': return <StreamingScrubberPanel />;
      case 'session-nexus': return <SessionNexusPanel />;
      case 'session-snapshot': return <SessionSnapshotPanel />;
      case 'tool-registry': return <ToolRegistryPanel />;
      case 'telemetry-pipeline': return <TelemetryPipelinePanel />;
      case 'journal-system': return <JournalSystemPanel />;
      case 'kanban-coordinator': return <KanbanCoordinatorPanel />;
      case 'localization-hub': return <LocalizationHubPanel />;
      case 'extension-sdk': return <ExtensionSdkPanel />;
      case 'insights-generator': return <InsightsGeneratorPanel />;
      case 'ecosystem-hub': return <EcosystemHubPanel />;
      case 'interaction-synthesis': return <InteractionSynthesisPanel />;
      case 'interaction-designer': return <InteractionDesignerPanel />;
      case 'narrative-branch': return <NarrativeBranchPanel />;
      case 'concurrency-manager': return <ConcurrencyManagerPanel />;
      case 'delegation-broker': return <DelegationBrokerPanel />;
      case 'theory-of-mind': return <AgentTheoryOfMindPanel />;
      case 'counterfactual-simulator': return <AgentCounterfactualSimulatorPanel />;
      case 'skill-lifecycle': return <AgentSkillLifecyclePanel />;
      case 'timeline-brancher': return <AgentTimelineBrancherPanel />;
      case 'ecosystem-dynamics': return <EngineEcosystemDynamicsPanel />;
      case 'civilization-evolution': return <EngineCivilizationEvolutionPanel />;
      case 'procedural-city': return <EngineProceduralCityPanel />;
      case 'flow-state-monitor': return <EngineFlowStateMonitorPanel />;
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
