import React, { useState, useEffect, useCallback } from 'react';
import { agentApi, studioApi, commandsApi, loopApi, meshApi, forgeApi, healthApi, protocolApi } from '../utils/api';
import AgentLearningLoopPanel from './AgentLearningLoopPanel';
import AgentCronSchedulerPanel from './AgentCronSchedulerPanel';
import AgentMemoryGraphPanel from './AgentMemoryGraphPanel';
import AgentContextCompressorPanel from './AgentContextCompressorPanel';
import AgentToolForgePanel from './AgentToolForgePanel';
import AgentGatewayPanel from './AgentGatewayPanel';
import SessionSnapshotPanel from './SessionSnapshotPanel';
import TrajectoryCompressorPanel from './TrajectoryCompressorPanel';
import SkillsHubPanel from './SkillsHubPanel';
import PersonalitySystemPanel from './PersonalitySystemPanel';
import InsightsGeneratorPanel from './InsightsGeneratorPanel';
import ProviderSwitchPanel from './ProviderSwitchPanel';
import ResourceSerializerPanel from './ResourceSerializerPanel';
import InputMapPanel from './InputMapPanel';
import AnimationTreePanel from './AnimationTreePanel';
import CustomObjectTypesPanel from './CustomObjectTypesPanel';
import TileMapOptimizerPanel from './TileMapOptimizerPanel';
import ChainOfThoughtPanel from './ChainOfThoughtPanel';
import ConversationMemoryPanel from './ConversationMemoryPanel';
import SelfOptimizationPanel from './SelfOptimizationPanel';
import CollaborationProtocolPanel from './CollaborationProtocolPanel';
import KnowledgeSynthesisPanel from './KnowledgeSynthesisPanel';
import CapabilityRegistryPanel from './CapabilityRegistryPanel';
import PhysicsMaterialPanel from './PhysicsMaterialPanel';
import GestureRecognizerPanel from './GestureRecognizerPanel';
import ShadowCastingPanel from './ShadowCastingPanel';
import EntityBlueprintPanel from './EntityBlueprintPanel';
import SceneTransitionPanel from './SceneTransitionPanel';
import AudioLayeringPanel from './AudioLayeringPanel';
import ExperimentFrameworkPanel from './ExperimentFrameworkPanel';
import TelemetryPipelinePanel from './TelemetryPipelinePanel';
import AuditTrailPanel from './AuditTrailPanel';
import JournalSystemPanel from './JournalSystemPanel';
import DocumentSynthesizerPanel from './DocumentSynthesizerPanel';
import SimulationRunnerPanel from './SimulationRunnerPanel';
import MaterialGraphPanel from './MaterialGraphPanel';
import OcclusionCullingPanel from './OcclusionCullingPanel';
import LODSystemPanel from './LODSystemPanel';
import DecalSystemPanel from './DecalSystemPanel';
import PostProcessingPanel from './PostProcessingPanel';
import SkeletonDeformerPanel from './SkeletonDeformerPanel';
import AgenticCodingPanel from './AgenticCodingPanel';
import GameReasonerPanel from './GameReasonerPanel';
import NarrativeBranchPanel from './NarrativeBranchPanel';
import ConcurrencyManagerPanel from './ConcurrencyManagerPanel';
import VerificationPipelinePanel from './VerificationPipelinePanel';
import PlaytestSimulatorPanel from './PlaytestSimulatorPanel';
import Lighting2DPanel from './Lighting2DPanel';
import ParallaxBackgroundPanel from './ParallaxBackgroundPanel';
import BehaviorLibraryPanel from './BehaviorLibraryPanel';
import AnimationCurvePanel from './AnimationCurvePanel';
import RenderLayerPanel from './RenderLayerPanel';
import StateSynchronizerPanel from './StateSynchronizerPanel';
import SkillSynthesizerPanel from './SkillSynthesizerPanel';
import SecurityScannerPanel from './SecurityScannerPanel';
import DelegationFrameworkPanel from './DelegationFrameworkPanel';
import KanbanCoordinatorPanel from './KanbanCoordinatorPanel';
import StreamingScrubberPanel from './StreamingScrubberPanel';
import TrajectoryGeneratorPanel from './TrajectoryGeneratorPanel';
import VisualScriptRuntimePanel from './VisualScriptRuntimePanel';
import ExtensionSdkPanel from './ExtensionSdkPanel';
import SignalBusPanel from './SignalBusPanel';
import PrefabComposerPanel from './PrefabComposerPanel';
import InteractiveAudioPanel from './InteractiveAudioPanel';
import ImportPipelinePanel from './ImportPipelinePanel';
import DeveloperOraclePanel from './DeveloperOraclePanel';
import ContextWeaverPanel from './ContextWeaverPanel';
import SessionNexusPanel from './SessionNexusPanel';
import PersonaVaultPanel from './PersonaVaultPanel';
import VoiceBridgePanel from './VoiceBridgePanel';
import EcosystemHubPanel from './EcosystemHubPanel';
import FrameComposerPanel from './FrameComposerPanel';
import SpatialClusterPanel from './SpatialClusterPanel';
import AssetStreamerPanel from './AssetStreamerPanel';
import DeterministicReplayPanel from './DeterministicReplayPanel';
import InputAbstractionPanel from './InputAbstractionPanel';
import ProfileLoaderPanel from './ProfileLoaderPanel';
import IntentCascadePanel from './IntentCascadePanel';
import GameForecasterPanel from './GameForecasterPanel';
import AssetSynthesizerPanel from './AssetSynthesizerPanel';
import TutorialOrchestratorPanel from './TutorialOrchestratorPanel';
import SkyboxRendererPanel from './SkyboxRendererPanel';
import TrailRendererPanel from './TrailRendererPanel';
import ProceduralAudioPanel from './ProceduralAudioPanel';
import TextureAtlasPanel from './TextureAtlasPanel';
import ABTestRunnerPanel from './ABTestRunnerPanel';
import HeatmapAnalyzerPanel from './HeatmapAnalyzerPanel';
import BugForensicsPanel from './BugForensicsPanel';
import AccessibilityAuditorPanel from './AccessibilityAuditorPanel';
import TileBrushPanel from './TileBrushPanel';
import SpriteAnimatorPanel from './SpriteAnimatorPanel';
import LightCullingPanel from './LightCullingPanel';
import RenderPassPanel from './RenderPassPanel';
import FederatedLearnerPanel from './FederatedLearnerPanel';
import SwarmPlannerPanel from './SwarmPlannerPanel';
import WorldComposerPanel from './WorldComposerPanel';
import PlaytestOrchestratorPanel from './PlaytestOrchestratorPanel';
import ParticleEmitterPanel from './ParticleEmitterPanel';
import LODGatePanel from './LODGatePanel';
import SceneStackPanel from './SceneStackPanel';
import NavMeshForgePanel from './NavMeshForgePanel';
import ReasoningChainPanel from './ReasoningChainPanel';
import MemoryHierarchyPanel from './MemoryHierarchyPanel';
import ToolRegistryPanel from './ToolRegistryPanel';
import PromptLibraryPanel from './PromptLibraryPanel';
import ReflectionLoopPanel from './ReflectionLoopPanel';
import ProceduralSynthesisPanel from './ProceduralSynthesisPanel';
import AssetBundlerPanel from './AssetBundlerPanel';
import DeterministicRecorderPanel from './DeterministicRecorderPanel';
import LocalizationHubPanel from './LocalizationHubPanel';
import SkillForgePanel from './SkillForgePanel';
import MemoryConsolidatorPanel from './MemoryConsolidatorPanel';
import DelegationBrokerPanel from './DelegationBrokerPanel';
import EventScriptingPanel from './EventScriptingPanel';
import ComponentAssemblerPanel from './ComponentAssemblerPanel';
import GameDesignIntelligencePanel from './GameDesignIntelligencePanel';
import GameStateAnalyzerPanel from './GameStateAnalyzerPanel';
import InteractionSynthesisPanel from './InteractionSynthesisPanel';
import GameRuntimeOrchestratorPanel from './GameRuntimeOrchestratorPanel';
import GameplayEcosystemPanel from './GameplayEcosystemPanel';
import BiomeGenerationPanel from './BiomeGenerationPanel';
import CreativeDirectorPanel from './CreativeDirectorPanel';
import ProceduralDungeonPanel from './ProceduralDungeonPanel';
import SocialSimulationPanel from './SocialSimulationPanel';
import AdaptiveContentPanel from './AdaptiveContentPanel';
import MonetizationDesignerPanel from './MonetizationDesignerPanel';
import ProgressiveLoadingPanel from './ProgressiveLoadingPanel';
import WorldBuilderPanel from './WorldBuilderPanel';
import BehaviorDesignerPanel from './BehaviorDesignerPanel';
import QuestComposerPanel from './QuestComposerPanel';
import MultiAgentCoordinatorPanel from './MultiAgentCoordinatorPanel';
import TileMapRuntimePanel from './TileMapRuntimePanel';
import ECSPanel from './ECSPanel';
import PhysicsWorld2DPanel from './PhysicsWorld2DPanel';
import VisualScriptingPanel from './VisualScriptingPanel';
import MemoryOrchestratorPanel from './MemoryOrchestratorPanel';
import SimulationControllerPanel from './SimulationControllerPanel';
import TimelineManagerPanel from './TimelineManagerPanel';
import SkillGeneratorPanel from './SkillGeneratorPanel';

type TabId = 'agents' | 'agentic_coding' | 'animation_curve' | 'animation_tree' | 'audio_layering' | 'audit_trail' | 'behavior_library' | 'capability_registry' | 'chain_of_thought' | 'collaboration_protocol' | 'commands' | 'concurrency_manager' | 'context_compressor' | 'conversation_memory' | 'cron_scheduler' | 'custom_object_types' | 'decal_system' | 'delegation-framework' | 'document_synthesizer' | 'entity_blueprint' | 'experiment_framework' | 'extension-sdk' | 'forge' | 'game_reasoner' | 'gateway' | 'gesture_recognizer' | 'health' | 'import-pipeline' | 'input_map' | 'insights_generator' | 'interactive-audio' | 'journal_system' | 'kanban-coordinator' | 'knowledge_synthesis' | 'learning_loop' | 'lighting_2d' | 'lod_system' | 'material_graph' | 'memory_graph' | 'mesh' | 'narrative_branch' | 'occlusion_culling' | 'parallax_background' | 'personality_system' | 'physics_material' | 'pipeline' | 'playtest_simulator' | 'post_processing' | 'prefab-composer' | 'provider_switch' | 'render_layer' | 'resource_serializer' | 'scene_transition' | 'security-scanner' | 'self_optimization' | 'session_snapshot' | 'shadow_casting' | 'signal-bus' | 'simulation_runner' | 'skeleton_deformer' | 'skill-synthesizer' | 'skills_hub' | 'state_synchronizer' | 'streaming-scrubber' | 'studio' | 'telemetry_pipeline' | 'tile_map_optimizer' | 'tool_forge' | 'trajectory-generator' | 'trajectory_compressor' | 'verification_pipeline' | 'visual-script-runtime' | 'developer-oracle' | 'context-weaver' | 'session-nexus' | 'persona-vault' | 'voice-bridge' | 'ecosystem-hub' | 'frame-composer' | 'spatial-cluster' | 'asset-streamer' | 'deterministic-replay' | 'input-abstraction' | 'profile-loader' | 'intent-cascade' | 'game-forecaster' | 'asset-synthesizer' | 'tutorial-orchestrator' | 'skybox-renderer' | 'trail-renderer' | 'procedural-audio' | 'texture-atlas'
  | 'ab-test-runner' | 'heatmap-analyzer' | 'bug-forensics' | 'accessibility-auditor'
  | 'tile-brush' | 'sprite-animator' | 'light-culling' | 'render-pass'
  | 'federated-learner' | 'swarm-planner' | 'world-composer' | 'playtest-orchestrator'
  | 'particle-emitter' | 'lod-gate' | 'scene-stack' | 'navmesh-forge'
  | 'reasoning-chain' | 'memory-hierarchy' | 'tool-registry' | 'prompt-library' | 'reflection-loop' | 'procedural-synthesis' | 'asset-bundler' | 'deterministic-recorder' | 'localization-hub'
  | 'skill-forge' | 'memory-consolidator' | 'delegation-broker' | 'event-scripting-runtime' | 'component-assembler'
  | 'game-design-intelligence' | 'game-state-analyzer'
  | 'interaction-synthesis' | 'runtime-orchestrator'
  | 'gameplay-ecosystem' | 'biome-generation'
  | 'creative-director' | 'procedural-dungeon'
  | 'social-simulation' | 'adaptive-content' | 'monetization-designer' | 'progressive-loading'
  | 'world-builder' | 'behavior-designer' | 'quest-composer' | 'multi-agent-coordinator'
  | 'tilemap-runtime' | 'ecs' | 'physics-world-2d' | 'visual-scripting'
  | 'memory-orchestrator' | 'simulation-controller' | 'timeline-manager' | 'skill-generator';

const TAB_CONFIG: { id: TabId; label: string; icon: string }[] = [
  { id: 'commands', label: 'Commands', icon: '⌨' },
  { id: 'agents', label: 'Agents', icon: '🤖' },
  { id: 'studio', label: 'Studio', icon: '🎬' },
  { id: 'pipeline', label: 'Pipeline', icon: '🔄' },
  { id: 'mesh', label: 'Mesh', icon: '🕸' },
  { id: 'forge', label: 'Forge', icon: '⚒' },
  { id: 'health', label: 'Health', icon: '💓' },
  { id: 'learning_loop', label: 'Learn', icon: '🧠' },
  { id: 'cron_scheduler', label: 'Cron', icon: '⏰' },
  { id: 'memory_graph', label: 'Memory', icon: '🕸' },
  { id: 'context_compressor', label: 'Context', icon: '📦' },
  { id: 'tool_forge', label: 'Tools', icon: '🔨' },
  { id: 'gateway', label: 'Gateway', icon: '🌐' },
  { id: 'session_snapshot', label: 'Snapshots', icon: '💾' },
  { id: 'trajectory_compressor', label: 'Trajectory', icon: '📐' },
  { id: 'skills_hub', label: 'Skills Hub', icon: '🏪' },
  { id: 'personality_system', label: 'Personality', icon: '🎭' },
  { id: 'insights_generator', label: 'Insights', icon: '📊' },
  { id: 'provider_switch', label: 'Providers', icon: '🔄' },
  { id: 'resource_serializer', label: 'Resources', icon: '📦' },
  { id: 'input_map', label: 'Input Map', icon: '🎮' },
  { id: 'animation_tree', label: 'Anim Tree', icon: '🌳' },
  { id: 'custom_object_types', label: 'Obj Types', icon: '🧩' },
  { id: 'tile_map_optimizer', label: 'Tile Maps', icon: '🗺️' },
  { id: 'chain_of_thought', label: 'Chain of Thought', icon: '🧠' },
  { id: 'conversation_memory', label: 'Conv Memory', icon: '💬' },
  { id: 'self_optimization', label: 'Optimization', icon: '⚡' },
  { id: 'collaboration_protocol', label: 'Collaboration', icon: '🤝' },
  { id: 'knowledge_synthesis', label: 'Knowledge', icon: '📚' },
  { id: 'capability_registry', label: 'Capabilities', icon: '🏷️' },
  { id: 'physics_material', label: 'Physics', icon: '⚛️' },
  { id: 'gesture_recognizer', label: 'Gestures', icon: '👆' },
  { id: 'shadow_casting', label: 'Shadows', icon: '🔦' },
  { id: 'entity_blueprint', label: 'Blueprints', icon: '📋' },
  { id: 'scene_transition', label: 'Transitions', icon: '🎬' },
  { id: 'audio_layering', label: 'Audio Mix', icon: '🔊' },
  { id: 'experiment_framework', label: 'Experiments', icon: '🧪' },
  { id: 'telemetry_pipeline', label: 'Telemetry', icon: '📡' },
  { id: 'audit_trail', label: 'Audit Trail', icon: '📝' },
  { id: 'journal_system', label: 'Journal', icon: '📓' },
  { id: 'document_synthesizer', label: 'Documents', icon: '📄' },
  { id: 'simulation_runner', label: 'Simulation', icon: '🔬' },
  { id: 'material_graph', label: 'Material Graph', icon: '🎨' },
  { id: 'occlusion_culling', label: 'Occlusion', icon: '👁️' },
  { id: 'lod_system', label: 'LOD System', icon: '📐' },
  { id: 'decal_system', label: 'Decals', icon: '🖼️' },
  { id: 'post_processing', label: 'Post FX', icon: '✨' },
  { id: 'skeleton_deformer', label: 'Skeleton', icon: '🦴' },
  { id: 'agentic_coding', label: 'AI Coding', icon: '🤖' },
  { id: 'game_reasoner', label: 'Game Reason', icon: '🎮' },
  { id: 'narrative_branch', label: 'Narrative', icon: '📖' },
  { id: 'concurrency_manager', label: 'Concurrency', icon: '🔄' },
  { id: 'verification_pipeline', label: 'Verify', icon: '🔍' },
  { id: 'playtest_simulator', label: 'Playtest', icon: '🕹️' },
  { id: 'lighting_2d', label: 'Lighting 2D', icon: '💡' },
  { id: 'parallax_background', label: 'Parallax', icon: '🌄' },
  { id: 'behavior_library', label: 'Behaviors', icon: '📚' },
  { id: 'animation_curve', label: 'Anim Curve', icon: '📈' },
  { id: 'render_layer', label: 'Render Layers', icon: '🎭' },
  { id: 'state_synchronizer', label: 'Sync', icon: '🔄' },
  { id: 'skill-synthesizer', label: 'Skill Synth', icon: '🧠' },
  { id: 'security-scanner', label: 'Security', icon: '🔒' },
  { id: 'delegation-framework', label: 'Delegate', icon: '🤝' },
  { id: 'kanban-coordinator', label: 'Kanban', icon: '📋' },
  { id: 'streaming-scrubber', label: 'Scrubber', icon: '🧹' },
  { id: 'trajectory-generator', label: 'Trajectory', icon: '📊' },
  { id: 'visual-script-runtime', label: 'Visual Script', icon: '📐' },
  { id: 'extension-sdk', label: 'Extensions', icon: '🔌' },
  { id: 'signal-bus', label: 'Signals', icon: '📡' },
  { id: 'prefab-composer', label: 'Prefabs', icon: '🧩' },
  { id: 'interactive-audio', label: 'Interactive Audio', icon: '🎵' },
  { id: 'import-pipeline', label: 'Import', icon: '📥' },
  { id: 'developer-oracle', label: 'Dev Oracle 🔮', icon: '🔮' },
  { id: 'context-weaver', label: 'Context Weave 🕸️', icon: '🕸️' },
  { id: 'session-nexus', label: 'Session Nexus 🔗', icon: '🔗' },
  { id: 'persona-vault', label: 'Persona Vault 🎭', icon: '🎭' },
  { id: 'voice-bridge', label: 'Voice Bridge 🎤', icon: '🎤' },
  { id: 'ecosystem-hub', label: 'Ecosystem Hub 🌐', icon: '🌐' },
  { id: 'frame-composer', label: 'Frame Composer 🎬', icon: '🎬' },
  { id: 'spatial-cluster', label: 'Spatial Cluster 📦', icon: '📦' },
  { id: 'asset-streamer', label: 'Asset Streamer 📡', icon: '📡' },
  { id: 'deterministic-replay', label: 'Replay System ⏪', icon: '⏪' },
  { id: 'input-abstraction', label: 'Input Layer 🎮', icon: '🎮' },
  { id: 'profile-loader', label: 'Profile Config ⚙️', icon: '⚙️' },
  { id: 'intent-cascade', label: 'Intent Cascade 🎯', icon: '🎯' },
  { id: 'game-forecaster', label: 'Game Forecaster 🔮', icon: '🔮' },
  { id: 'asset-synthesizer', label: 'Asset Synthesizer 🎨', icon: '🎨' },
  { id: 'tutorial-orchestrator', label: 'Tutorial Creator 📚', icon: '📚' },
  { id: 'skybox-renderer', label: 'Skybox Renderer 🌌', icon: '🌌' },
  { id: 'trail-renderer', label: 'Trail Renderer ✨', icon: '✨' },
  { id: 'procedural-audio', label: 'Procedural Audio 🔊', icon: '🔊' },
  { id: 'texture-atlas', label: 'Texture Atlas 🗺️', icon: '🗺️' },
  { id: 'ab-test-runner', label: 'AB Test 🔬', icon: '🔬' },
  { id: 'heatmap-analyzer', label: 'Heatmap 📊', icon: '📊' },
  { id: 'bug-forensics', label: 'Bug Forensics 🪲', icon: '🪲' },
  { id: 'accessibility-auditor', label: 'Accessibility ♿', icon: '♿' },
  { id: 'tile-brush', label: 'Tile Brush 🖌️', icon: '🖌️' },
  { id: 'sprite-animator', label: 'Sprite Anim 🎞️', icon: '🎞️' },
  { id: 'light-culling', label: 'Light Culling 💡', icon: '💡' },
  { id: 'render-pass', label: 'Render Pass 🎨', icon: '🎨' },
  { id: 'federated-learner', label: 'Fed Learner 🤖', icon: '🤖' },
  { id: 'swarm-planner', label: 'Swarm 🐝', icon: '🐝' },
  { id: 'world-composer', label: 'World Comp 🌍', icon: '🌍' },
  { id: 'playtest-orchestrator', label: 'Play Orch 🎭', icon: '🎭' },
  { id: 'particle-emitter', label: 'Particles ✨', icon: '✨' },
  { id: 'lod-gate', label: 'LOD Gate 🚪', icon: '🚪' },
  { id: 'scene-stack', label: 'Scene Stack 📚', icon: '📚' },
  { id: 'navmesh-forge', label: 'NavMesh 🧭', icon: '🧭' },
  { id: 'reasoning-chain', label: 'Reasoning 🧠', icon: '🧠' },
  { id: 'memory-hierarchy', label: 'Memory 💾', icon: '💾' },
  { id: 'tool-registry', label: 'Tools 🔧', icon: '🔧' },
  { id: 'prompt-library', label: 'Prompts 📝', icon: '📝' },
  { id: 'reflection-loop', label: 'Reflect 🔄', icon: '🔄' },
  { id: 'procedural-synthesis', label: 'Proc Gen 🌿', icon: '🌿' },
  { id: 'asset-bundler', label: 'Bundler 📦', icon: '📦' },
  { id: 'deterministic-recorder', label: 'Record 🎬', icon: '🎬' },
  { id: 'localization-hub', label: 'Locales 🌐', icon: '🌐' },
  { id: 'skill-forge', label: 'Skill Forge ⚒️', icon: '⚒️' },
  { id: 'memory-consolidator', label: 'Memory Cons 💾', icon: '💾' },
  { id: 'delegation-broker', label: 'Delegation 📋', icon: '📋' },
  { id: 'event-scripting-runtime', label: 'Event Script 📜', icon: '📜' },
  { id: 'component-assembler', label: 'Components 🧩', icon: '🧩' },
  { id: 'game-design-intelligence', label: 'Game Design 🎲', icon: '🎲' },
  { id: 'game-state-analyzer', label: 'State Analyzer 🔧', icon: '🔧' },
  { id: 'interaction-synthesis', label: 'Interaction Synthesis 🔗', icon: '🔗' },
  { id: 'runtime-orchestrator', label: 'Runtime Orchestrator ⚙️', icon: '⚙️' },
  { id: 'gameplay-ecosystem', label: 'Ecosystem Simulator 🌍', icon: '🌍' },
  { id: 'biome-generation', label: 'Biome Generation 🏔️', icon: '🏔️' },
  { id: 'creative-director', label: 'Creative Director 🎨', icon: '🎨' },
  { id: 'procedural-dungeon', label: 'Dungeon Generator 🏰', icon: '🏰' },
  { id: 'social-simulation', label: 'Social Simulation 👥', icon: '👥' },
  { id: 'adaptive-content', label: 'Adaptive Content 🎯', icon: '🎯' },
  { id: 'monetization-designer', label: 'Monetization Designer 💰', icon: '💰' },
  { id: 'progressive-loading', label: 'Progressive Loading 📦', icon: '📦' },
  { id: 'world-builder', label: 'World Builder 🗺️', icon: '🗺️' },
  { id: 'behavior-designer', label: 'Behavior Designer 🧠', icon: '🧠' },
  { id: 'quest-composer', label: 'Quest Composer 📜', icon: '📜' },
  { id: 'multi-agent-coordinator', label: 'Multi-Agent Coordinator 🤝', icon: '🤝' },
  { id: 'tilemap-runtime', label: 'TileMap Runtime 🗾', icon: '🗾' },
  { id: 'ecs', label: 'ECS ⚙️', icon: '⚙️' },
  { id: 'physics-world-2d', label: 'Physics World 2D ⚡', icon: '⚡' },
  { id: 'visual-scripting', label: 'Visual Scripting 📊', icon: '📊' },
  { id: 'memory-orchestrator', label: 'Memory Orch 🧠', icon: '🧠' },
  { id: 'simulation-controller', label: 'Simulation 🌐', icon: '🌐' },
  { id: 'timeline-manager', label: 'Timeline ⏳', icon: '⏳' },
  { id: 'skill-generator', label: 'Skill Gen ⚡', icon: '⚡' },
];

const STUDIO_TIERS: { tier: string; agents: { type: string; label: string }[] }[] = [
  {
    tier: 'Directors',
    agents: [
      { type: 'CreativeDirector', label: 'Creative Director' },
      { type: 'TechnicalDirector', label: 'Technical Director' },
      { type: 'Producer', label: 'Producer' },
    ],
  },
  {
    tier: 'Leads',
    agents: [
      { type: 'GameDesigner', label: 'Game Designer' },
      { type: 'LeadProgrammer', label: 'Lead Programmer' },
      { type: 'ArtDirector', label: 'Art Director' },
      { type: 'NarrativeDirector', label: 'Narrative Director' },
      { type: 'QALead', label: 'QA Lead' },
    ],
  },
  {
    tier: 'Specialists',
    agents: [
      { type: 'GameplayProgrammer', label: 'Gameplay Programmer' },
      { type: 'EngineProgrammer', label: 'Engine Programmer' },
      { type: 'AIProgrammer', label: 'AI Programmer' },
      { type: 'LevelDesigner', label: 'Level Designer' },
      { type: 'WorldBuilder', label: 'World Builder' },
      { type: 'SoundDesigner', label: 'Sound Designer' },
      { type: 'Writer', label: 'Writer' },
      { type: 'QATester', label: 'QA Tester' },
    ],
  },
];

const PIPELINE_STAGES = ['Analyze', 'Design', 'Scaffold', 'Implement', 'Integrate', 'Validate'];

const AgentPanel: React.FC = () => {
  const [activeTab, setActiveTab] = useState<TabId>('commands');
  const [agents, setAgents] = useState<any[]>([]);
  const [commands, setCommands] = useState<any[]>([]);
  const [commandCategories, setCommandCategories] = useState<string[]>([]);
  const [pipelinePrompt, setPipelinePrompt] = useState('');
  const [pipelineRunning, setPipelineRunning] = useState(false);
  const [pipelineResult, setPipelineResult] = useState<any>(null);
  const [meshNodes, setMeshNodes] = useState<any[]>([]);
  const [meshClusters, setMeshClusters] = useState<any[]>([]);
  const [meshTopology, setMeshTopology] = useState<any>(null);
  const [forgeStats, setForgeStats] = useState<any>(null);
  const [forgeEvolutions, setForgeEvolutions] = useState<any[]>([]);
  const [healthReport, setHealthReport] = useState<any>(null);
  const [inputValue, setInputValue] = useState('');
  const [chatMessages, setChatMessages] = useState<{ role: string; content: string }[]>([]);
  const [selectedAgentId, setSelectedAgentId] = useState<string | null>(null);

  useEffect(() => {
    loadCommands();
    loadAgents();
    loadMeshData();
    loadForgeData();
    loadHealthData();
  }, []);

  const loadCommands = async () => {
    try {
      const res: any = await commandsApi.list();
      setCommands(res.commands || []);
      const cats = [...new Set((res.commands || []).map((c: any) => c.category))] as string[];
      setCommandCategories(cats);
    } catch {}
  };

  const loadAgents = async () => {
    try {
      const res: any = await agentApi.list();
      setAgents(res.agents || res || []);
    } catch {}
  };

  const loadMeshData = async () => {
    try {
      const [topoRes, nodesRes, clustersRes]: any[] = await Promise.all([
        meshApi.topology(),
        meshApi.nodes(),
        meshApi.clusters(),
      ]);
      setMeshTopology(topoRes);
      setMeshNodes(nodesRes.nodes || []);
      setMeshClusters(clustersRes.clusters || []);
    } catch {}
  };

  const loadForgeData = async () => {
    try {
      const [statsRes, evoRes]: any[] = await Promise.all([
        forgeApi.stats(),
        forgeApi.evolutions(),
      ]);
      setForgeStats(statsRes);
      setForgeEvolutions(evoRes.evolutions || []);
    } catch {}
  };

  const loadHealthData = async () => {
    try {
      const res: any = await healthApi.check();
      setHealthReport(res);
    } catch {}
  };

  const handleCreateStudioAgent = async (type: string) => {
    try {
      await studioApi.create(type);
      loadAgents();
      loadMeshData();
    } catch {}
  };

  const handleDeleteAgent = async (agentId: string) => {
    try {
      await agentApi.delete(agentId);
      loadAgents();
      loadMeshData();
    } catch {}
  };

  const handleRunPipeline = async () => {
    if (!pipelinePrompt.trim()) return;
    setPipelineRunning(true);
    try {
      const res: any = await loopApi.pipelineRun(pipelinePrompt);
      setPipelineResult(res);
    } catch (e: any) {
      setPipelineResult({ error: e.message });
    }
    setPipelineRunning(false);
  };

  const handleRegisterMeshNode = async () => {
    const id = `agent_${Date.now()}`;
    try {
      await meshApi.register(id, `Agent ${meshNodes.length + 1}`, 'specialist', ['reasoning']);
      loadMeshData();
    } catch {}
  };

  const handleForgeSkill = async () => {
    const name = `skill_${Date.now()}`;
    try {
      await forgeApi.forgeSkill(name, 'general', `Auto-generated skill`, 'Execute task');
      loadForgeData();
    } catch {}
  };

  const handleSendMessage = async () => {
    if (!inputValue.trim()) return;
    const msg = inputValue;
    setChatMessages(prev => [...prev, { role: 'user', content: msg }]);
    setInputValue('');

    if (msg.startsWith('/')) {
      try {
        const res: any = await commandsApi.parse(msg);
        setChatMessages(prev => [...prev, { role: 'agent', content: JSON.stringify(res, null, 2) }]);
      } catch {
        setChatMessages(prev => [...prev, { role: 'agent', content: 'Command execution failed' }]);
      }
    } else {
      setChatMessages(prev => [...prev, { role: 'agent', content: 'LLM connection required for free-form prompts. Use /commands for available actions.' }]);
    }
  };

  const renderCommandsTab = () => (
    <div className="p-3 space-y-3 overflow-y-auto h-full">
      {commandCategories.map(cat => (
        <div key={cat}>
          <h4 className="text-[10px] font-bold text-[#888] uppercase tracking-wider mb-1">{cat}</h4>
          <div className="flex flex-wrap gap-1">
            {commands.filter((c: any) => c.category === cat).map((c: any) => (
              <button
                key={c.name}
                onClick={() => setInputValue(`/${c.name} `)}
                className="text-[10px] px-2 py-0.5 bg-[#1e1e1e] hover:bg-[#2a2a2a] text-[#ccc] rounded border border-[#333] transition-colors"
              >
                /{c.name}
              </button>
            ))}
          </div>
        </div>
      ))}
    </div>
  );

  const renderAgentsTab = () => (
    <div className="p-3 space-y-2 overflow-y-auto h-full">
      {agents.length === 0 ? (
        <div className="text-[11px] text-[#666] text-center py-4">No agents created yet. Use Studio tab to create agents.</div>
      ) : (
        agents.map((agent: any) => (
          <div
            key={agent.id}
            onClick={() => setSelectedAgentId(agent.id)}
            className={`flex items-center justify-between p-2 rounded border cursor-pointer transition-colors ${
              selectedAgentId === agent.id ? 'border-blue-500 bg-blue-500/10' : 'border-[#333] bg-[#1a1a1a] hover:bg-[#222]'
            }`}
          >
            <div className="flex items-center gap-2">
              <span className="text-[10px] px-1.5 py-0.5 rounded bg-green-500/20 text-green-400">{agent.state || 'idle'}</span>
              <span className="text-[11px] text-[#ccc]">{agent.name}</span>
            </div>
            <button
              onClick={(e) => { e.stopPropagation(); handleDeleteAgent(agent.id); }}
              className="text-[10px] text-red-400 hover:text-red-300 px-1"
            >
              ✕
            </button>
          </div>
        ))
      )}
    </div>
  );

  const renderStudioTab = () => (
    <div className="p-3 space-y-3 overflow-y-auto h-full">
      {STUDIO_TIERS.map(({ tier, agents: tierAgents }) => (
        <div key={tier}>
          <h4 className="text-[10px] font-bold text-[#888] uppercase tracking-wider mb-1">{tier}</h4>
          <div className="grid grid-cols-2 gap-1">
            {tierAgents.map(({ type, label }) => (
              <button
                key={type}
                onClick={() => handleCreateStudioAgent(type)}
                className="text-[10px] px-2 py-1.5 bg-[#1e1e1e] hover:bg-[#2a2a2a] text-[#ccc] rounded border border-[#333] transition-colors text-left"
              >
                {label}
              </button>
            ))}
          </div>
        </div>
      ))}
    </div>
  );

  const renderPipelineTab = () => (
    <div className="p-3 space-y-3 overflow-y-auto h-full">
      <div>
        <textarea
          value={pipelinePrompt}
          onChange={(e) => setPipelinePrompt(e.target.value)}
          placeholder="Describe the game you want to create..."
          className="w-full h-20 bg-[#1a1a1a] border border-[#333] rounded p-2 text-[11px] text-[#ccc] resize-none focus:border-blue-500 outline-none"
        />
        <button
          onClick={handleRunPipeline}
          disabled={pipelineRunning || !pipelinePrompt.trim()}
          className="w-full mt-1 py-1.5 bg-gradient-to-r from-orange-600 to-orange-500 text-white text-[11px] rounded font-medium disabled:opacity-50"
        >
          {pipelineRunning ? 'Running Pipeline...' : 'Run Pipeline'}
        </button>
      </div>
      <div className="space-y-1">
        {PIPELINE_STAGES.map((stage, i) => (
          <div key={stage} className="flex items-center gap-2 text-[10px]">
            <span className="w-4 h-4 rounded-full bg-[#333] flex items-center justify-center text-[8px]">{i + 1}</span>
            <span className="text-[#aaa]">{stage}</span>
          </div>
        ))}
      </div>
      {pipelineResult && (
        <div className="bg-[#1a1a1a] border border-[#333] rounded p-2">
          <h4 className="text-[10px] font-bold text-[#888] mb-1">Result</h4>
          <pre className="text-[9px] text-[#aaa] overflow-auto max-h-40 whitespace-pre-wrap">
            {JSON.stringify(pipelineResult, null, 2)}
          </pre>
        </div>
      )}
    </div>
  );

  const renderMeshTab = () => (
    <div className="p-3 space-y-3 overflow-y-auto h-full">
      <div className="flex items-center justify-between">
        <h4 className="text-[10px] font-bold text-[#888] uppercase tracking-wider">Network Topology</h4>
        <button onClick={handleRegisterMeshNode} className="text-[9px] px-2 py-1 bg-blue-600 hover:bg-blue-500 text-white rounded">
          + Register Node
        </button>
      </div>
      {meshTopology && (
        <div className="grid grid-cols-2 gap-1">
          <div className="bg-[#1a1a1a] border border-[#333] rounded p-2 text-center">
            <div className="text-[14px] font-bold text-blue-400">{meshTopology.node_count || 0}</div>
            <div className="text-[9px] text-[#666]">Nodes</div>
          </div>
          <div className="bg-[#1a1a1a] border border-[#333] rounded p-2 text-center">
            <div className="text-[14px] font-bold text-green-400">{meshTopology.available_nodes || 0}</div>
            <div className="text-[9px] text-[#666]">Available</div>
          </div>
          <div className="bg-[#1a1a1a] border border-[#333] rounded p-2 text-center">
            <div className="text-[14px] font-bold text-orange-400">{meshTopology.connection_count || 0}</div>
            <div className="text-[9px] text-[#666]">Connections</div>
          </div>
          <div className="bg-[#1a1a1a] border border-[#333] rounded p-2 text-center">
            <div className="text-[14px] font-bold text-purple-400">{meshTopology.active_clusters || 0}</div>
            <div className="text-[9px] text-[#666]">Clusters</div>
          </div>
        </div>
      )}
      <div>
        <h4 className="text-[10px] font-bold text-[#888] uppercase tracking-wider mb-1">Nodes</h4>
        {meshNodes.map((node: any) => (
          <div key={node.agent_id} className="flex items-center justify-between p-1.5 bg-[#1a1a1a] border border-[#333] rounded mb-1">
            <div className="flex items-center gap-2">
              <span className={`w-2 h-2 rounded-full ${node.is_available ? 'bg-green-500' : 'bg-red-500'}`} />
              <span className="text-[10px] text-[#ccc]">{node.name}</span>
            </div>
            <span className="text-[9px] text-[#666]">{node.role}</span>
          </div>
        ))}
      </div>
      {meshClusters.length > 0 && (
        <div>
          <h4 className="text-[10px] font-bold text-[#888] uppercase tracking-wider mb-1">Clusters</h4>
          {meshClusters.map((cluster: any) => (
            <div key={cluster.id} className="p-2 bg-[#1a1a1a] border border-[#333] rounded mb-1">
              <div className="text-[10px] text-[#ccc] font-medium">{cluster.name}</div>
              <div className="text-[9px] text-[#666]">{cluster.goal}</div>
              <div className="text-[9px] text-[#888] mt-1">{cluster.member_count} members</div>
            </div>
          ))}
        </div>
      )}
    </div>
  );

  const renderForgeTab = () => (
    <div className="p-3 space-y-3 overflow-y-auto h-full">
      <div className="flex items-center justify-between">
        <h4 className="text-[10px] font-bold text-[#888] uppercase tracking-wider">Skill Forge</h4>
        <button onClick={handleForgeSkill} className="text-[9px] px-2 py-1 bg-orange-600 hover:bg-orange-500 text-white rounded">
          + Forge Skill
        </button>
      </div>
      {forgeStats && (
        <div className="grid grid-cols-3 gap-1">
          <div className="bg-[#1a1a1a] border border-[#333] rounded p-2 text-center">
            <div className="text-[14px] font-bold text-orange-400">{forgeStats.total_skills || 0}</div>
            <div className="text-[9px] text-[#666]">Skills</div>
          </div>
          <div className="bg-[#1a1a1a] border border-[#333] rounded p-2 text-center">
            <div className="text-[14px] font-bold text-blue-400">{forgeStats.total_blueprints || 0}</div>
            <div className="text-[9px] text-[#666]">Blueprints</div>
          </div>
          <div className="bg-[#1a1a1a] border border-[#333] rounded p-2 text-center">
            <div className="text-[14px] font-bold text-green-400">{Math.round((forgeStats.avg_reliability || 0) * 100)}%</div>
            <div className="text-[9px] text-[#666]">Reliability</div>
          </div>
        </div>
      )}
      <div>
        <h4 className="text-[10px] font-bold text-[#888] uppercase tracking-wider mb-1">Evolutions</h4>
        {forgeEvolutions.map((evo: any) => (
          <div key={evo.skill_name} className="p-2 bg-[#1a1a1a] border border-[#333] rounded mb-1">
            <div className="flex items-center justify-between">
              <span className="text-[10px] text-[#ccc]">{evo.skill_name}</span>
              <span className={`text-[9px] px-1.5 py-0.5 rounded ${
                evo.maturity === 'core' ? 'bg-green-500/20 text-green-400' :
                evo.maturity === 'proven' ? 'bg-blue-500/20 text-blue-400' :
                evo.maturity === 'validated' ? 'bg-yellow-500/20 text-yellow-400' :
                'bg-gray-500/20 text-gray-400'
              }`}>{evo.maturity}</span>
            </div>
            <div className="flex items-center gap-3 mt-1">
              <span className="text-[9px] text-[#666]">Success: {Math.round(evo.success_rate * 100)}%</span>
              <span className="text-[9px] text-[#666]">Execs: {evo.total_executions}</span>
              <span className="text-[9px] text-[#666]">Rel: {Math.round(evo.reliability_score * 100)}%</span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );

  const renderHealthTab = () => (
    <div className="p-3 space-y-3 overflow-y-auto h-full">
      <div className="flex items-center justify-between">
        <h4 className="text-[10px] font-bold text-[#888] uppercase tracking-wider">System Health</h4>
        <button onClick={loadHealthData} className="text-[9px] px-2 py-1 bg-[#333] hover:bg-[#444] text-[#ccc] rounded">
          Refresh
        </button>
      </div>
      {healthReport ? (
        <>
          <div className={`p-2 rounded border text-center ${
            healthReport.overall_status === 'healthy' ? 'bg-green-500/10 border-green-500/30' :
            healthReport.overall_status === 'degraded' ? 'bg-yellow-500/10 border-yellow-500/30' :
            'bg-red-500/10 border-red-500/30'
          }`}>
            <div className="text-[12px] font-bold capitalize">{healthReport.overall_status}</div>
            <div className="text-[9px] text-[#888]">{healthReport.summary}</div>
          </div>
          <div className="space-y-1">
            {(healthReport.checks || []).map((check: any) => (
              <div key={check.name} className="flex items-center justify-between p-1.5 bg-[#1a1a1a] border border-[#333] rounded">
                <div className="flex items-center gap-2">
                  <span className={`w-2 h-2 rounded-full ${
                    check.status === 'healthy' ? 'bg-green-500' :
                    check.status === 'degraded' ? 'bg-yellow-500' :
                    'bg-red-500'
                  }`} />
                  <span className="text-[10px] text-[#ccc]">{check.name}</span>
                </div>
                <span className="text-[9px] text-[#666]">{check.duration_ms?.toFixed(0)}ms</span>
              </div>
            ))}
          </div>
        </>
      ) : (
        <div className="text-[11px] text-[#666] text-center py-4">Loading health data...</div>
      )}
    </div>
  );

  const renderTabContent = () => {
    switch (activeTab) {
      case 'commands': return renderCommandsTab();
      case 'agents': return renderAgentsTab();
      case 'studio': return renderStudioTab();
      case 'pipeline': return renderPipelineTab();
      case 'mesh': return renderMeshTab();
      case 'forge': return renderForgeTab();
      case 'health': return renderHealthTab();
      case 'learning_loop': return <AgentLearningLoopPanel />;
      case 'cron_scheduler': return <AgentCronSchedulerPanel />;
      case 'memory_graph': return <AgentMemoryGraphPanel />;
      case 'context_compressor': return <AgentContextCompressorPanel />;
      case 'tool_forge': return <AgentToolForgePanel />;
      case 'gateway': return <AgentGatewayPanel />;
      case 'session_snapshot': return <SessionSnapshotPanel />;
      case 'trajectory_compressor': return <TrajectoryCompressorPanel />;
      case 'skills_hub': return <SkillsHubPanel />;
      case 'personality_system': return <PersonalitySystemPanel />;
      case 'insights_generator': return <InsightsGeneratorPanel />;
      case 'provider_switch': return <ProviderSwitchPanel />;
      case 'resource_serializer': return <ResourceSerializerPanel />;
      case 'input_map': return <InputMapPanel />;
      case 'animation_tree': return <AnimationTreePanel />;
      case 'custom_object_types': return <CustomObjectTypesPanel />;
      case 'tile_map_optimizer': return <TileMapOptimizerPanel />;
      case 'chain_of_thought': return <ChainOfThoughtPanel />;
      case 'conversation_memory': return <ConversationMemoryPanel />;
      case 'self_optimization': return <SelfOptimizationPanel />;
      case 'collaboration_protocol': return <CollaborationProtocolPanel />;
      case 'knowledge_synthesis': return <KnowledgeSynthesisPanel />;
      case 'capability_registry': return <CapabilityRegistryPanel />;
      case 'physics_material': return <PhysicsMaterialPanel />;
      case 'gesture_recognizer': return <GestureRecognizerPanel />;
      case 'shadow_casting': return <ShadowCastingPanel />;
      case 'entity_blueprint': return <EntityBlueprintPanel />;
      case 'scene_transition': return <SceneTransitionPanel />;
      case 'audio_layering': return <AudioLayeringPanel />;
      case 'experiment_framework': return <ExperimentFrameworkPanel />;
      case 'telemetry_pipeline': return <TelemetryPipelinePanel />;
      case 'audit_trail': return <AuditTrailPanel />;
      case 'journal_system': return <JournalSystemPanel />;
      case 'document_synthesizer': return <DocumentSynthesizerPanel />;
      case 'simulation_runner': return <SimulationRunnerPanel />;
      case 'material_graph': return <MaterialGraphPanel />;
      case 'occlusion_culling': return <OcclusionCullingPanel />;
      case 'lod_system': return <LODSystemPanel />;
      case 'decal_system': return <DecalSystemPanel />;
      case 'post_processing': return <PostProcessingPanel />;
      case 'skeleton_deformer': return <SkeletonDeformerPanel />;
      case 'agentic_coding': return <AgenticCodingPanel />;
      case 'game_reasoner': return <GameReasonerPanel />;
      case 'narrative_branch': return <NarrativeBranchPanel />;
      case 'concurrency_manager': return <ConcurrencyManagerPanel />;
      case 'verification_pipeline': return <VerificationPipelinePanel />;
      case 'playtest_simulator': return <PlaytestSimulatorPanel />;
      case 'lighting_2d': return <Lighting2DPanel />;
      case 'parallax_background': return <ParallaxBackgroundPanel />;
      case 'behavior_library': return <BehaviorLibraryPanel />;
      case 'animation_curve': return <AnimationCurvePanel />;
      case 'render_layer': return <RenderLayerPanel />;
      case 'state_synchronizer': return <StateSynchronizerPanel />;
      case 'skill-synthesizer': return <SkillSynthesizerPanel />;
      case 'security-scanner': return <SecurityScannerPanel />;
      case 'delegation-framework': return <DelegationFrameworkPanel />;
      case 'kanban-coordinator': return <KanbanCoordinatorPanel />;
      case 'streaming-scrubber': return <StreamingScrubberPanel />;
      case 'trajectory-generator': return <TrajectoryGeneratorPanel />;
      case 'visual-script-runtime': return <VisualScriptRuntimePanel />;
      case 'extension-sdk': return <ExtensionSdkPanel />;
      case 'signal-bus': return <SignalBusPanel />;
      case 'prefab-composer': return <PrefabComposerPanel />;
      case 'interactive-audio': return <InteractiveAudioPanel />;
      case 'import-pipeline': return <ImportPipelinePanel />;
      case 'developer-oracle': return <DeveloperOraclePanel />;
      case 'context-weaver': return <ContextWeaverPanel />;
      case 'session-nexus': return <SessionNexusPanel />;
      case 'persona-vault': return <PersonaVaultPanel />;
      case 'voice-bridge': return <VoiceBridgePanel />;
      case 'ecosystem-hub': return <EcosystemHubPanel />;
      case 'frame-composer': return <FrameComposerPanel />;
      case 'spatial-cluster': return <SpatialClusterPanel />;
      case 'asset-streamer': return <AssetStreamerPanel />;
      case 'deterministic-replay': return <DeterministicReplayPanel />;
      case 'input-abstraction': return <InputAbstractionPanel />;
      case 'profile-loader': return <ProfileLoaderPanel />;
      case 'intent-cascade': return <IntentCascadePanel />;
      case 'game-forecaster': return <GameForecasterPanel />;
      case 'asset-synthesizer': return <AssetSynthesizerPanel />;
      case 'tutorial-orchestrator': return <TutorialOrchestratorPanel />;
      case 'skybox-renderer': return <SkyboxRendererPanel />;
      case 'trail-renderer': return <TrailRendererPanel />;
      case 'procedural-audio': return <ProceduralAudioPanel />;
      case 'texture-atlas': return <TextureAtlasPanel />;
      case 'ab-test-runner': return <ABTestRunnerPanel />;
      case 'heatmap-analyzer': return <HeatmapAnalyzerPanel />;
      case 'bug-forensics': return <BugForensicsPanel />;
      case 'accessibility-auditor': return <AccessibilityAuditorPanel />;
      case 'tile-brush': return <TileBrushPanel />;
      case 'sprite-animator': return <SpriteAnimatorPanel />;
      case 'light-culling': return <LightCullingPanel />;
      case 'render-pass': return <RenderPassPanel />;
      case 'federated-learner': return <FederatedLearnerPanel />;
      case 'swarm-planner': return <SwarmPlannerPanel />;
      case 'world-composer': return <WorldComposerPanel />;
      case 'playtest-orchestrator': return <PlaytestOrchestratorPanel />;
      case 'particle-emitter': return <ParticleEmitterPanel />;
      case 'lod-gate': return <LODGatePanel />;
      case 'scene-stack': return <SceneStackPanel />;
      case 'navmesh-forge': return <NavMeshForgePanel />;
      case 'reasoning-chain': return <ReasoningChainPanel />;
      case 'memory-hierarchy': return <MemoryHierarchyPanel />;
      case 'tool-registry': return <ToolRegistryPanel />;
      case 'prompt-library': return <PromptLibraryPanel />;
      case 'reflection-loop': return <ReflectionLoopPanel />;
      case 'procedural-synthesis': return <ProceduralSynthesisPanel />;
      case 'asset-bundler': return <AssetBundlerPanel />;
      case 'deterministic-recorder': return <DeterministicRecorderPanel />;
      case 'localization-hub': return <LocalizationHubPanel />;
      case 'skill-forge': return <SkillForgePanel />;
      case 'memory-consolidator': return <MemoryConsolidatorPanel />;
      case 'delegation-broker': return <DelegationBrokerPanel />;
      case 'event-scripting-runtime': return <EventScriptingPanel />;
      case 'component-assembler': return <ComponentAssemblerPanel />;
      case 'game-design-intelligence': return <GameDesignIntelligencePanel />;
      case 'game-state-analyzer': return <GameStateAnalyzerPanel />;
      case 'interaction-synthesis': return <InteractionSynthesisPanel />;
      case 'runtime-orchestrator': return <GameRuntimeOrchestratorPanel />;
      case 'gameplay-ecosystem': return <GameplayEcosystemPanel />;
      case 'biome-generation': return <BiomeGenerationPanel />;
      case 'creative-director': return <CreativeDirectorPanel />;
      case 'procedural-dungeon': return <ProceduralDungeonPanel />;
      case 'social-simulation': return <SocialSimulationPanel />;
      case 'adaptive-content': return <AdaptiveContentPanel />;
      case 'monetization-designer': return <MonetizationDesignerPanel />;
      case 'progressive-loading': return <ProgressiveLoadingPanel />;
      case 'world-builder': return <WorldBuilderPanel />;
      case 'behavior-designer': return <BehaviorDesignerPanel />;
      case 'quest-composer': return <QuestComposerPanel />;
      case 'multi-agent-coordinator': return <MultiAgentCoordinatorPanel />;
      case 'tilemap-runtime': return <TileMapRuntimePanel />;
      case 'ecs': return <ECSPanel />;
      case 'physics-world-2d': return <PhysicsWorld2DPanel />;
      case 'visual-scripting': return <VisualScriptingPanel />;
      case 'memory-orchestrator': return <MemoryOrchestratorPanel />;
      case 'simulation-controller': return <SimulationControllerPanel />;
      case 'timeline-manager': return <TimelineManagerPanel />;
      case 'skill-generator': return <SkillGeneratorPanel />;
      default: return null;
    }
  };

  return (
    <div className="h-full flex flex-col bg-[#0d0d0d]">
      <div className="flex border-b border-[#1e1e1e] overflow-x-auto">
        {TAB_CONFIG.map(tab => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={`flex items-center gap-1 px-3 py-2 text-[10px] whitespace-nowrap transition-colors border-b-2 ${
              activeTab === tab.id
                ? 'text-blue-400 border-blue-500 bg-blue-500/5'
                : 'text-[#666] border-transparent hover:text-[#999] hover:bg-[#151515]'
            }`}
          >
            <span>{tab.icon}</span>
            <span>{tab.label}</span>
          </button>
        ))}
      </div>

      <div className="flex-1 overflow-hidden">
        {renderTabContent()}
      </div>

      <div className="border-t border-[#1e1e1e] p-2">
        <div className="flex gap-1">
          <input
            type="text"
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleSendMessage()}
            placeholder="Type / for commands..."
            className="flex-1 bg-[#1a1a1a] border border-[#333] rounded px-2 py-1.5 text-[11px] text-[#ccc] outline-none focus:border-blue-500"
          />
          <button
            onClick={handleSendMessage}
            className="px-3 py-1.5 bg-blue-600 hover:bg-blue-500 text-white text-[10px] rounded"
          >
            Send
          </button>
        </div>
        {chatMessages.length > 0 && (
          <div className="mt-2 max-h-24 overflow-y-auto space-y-1">
            {chatMessages.map((msg, i) => (
              <div key={i} className={`text-[9px] ${msg.role === 'user' ? 'text-blue-400' : 'text-[#aaa]'}`}>
                <span className="font-bold">{msg.role === 'user' ? '>' : 'AI'}</span> {msg.content}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

export default AgentPanel;
