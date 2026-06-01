"""
SparkLabs Backend - Agent Routes

API endpoints for agent creation, management, skills,
studio hierarchy, toolsets, hooks, rules, teams,
bench evaluation, and session management.
"""

from fastapi import APIRouter, Query, Request
from pydantic import BaseModel
from typing import Any, Dict, List, Optional

from sparkai.agent.base import SparkAgent, AgentCapability, AgentRole
from sparkai.agent.orchestrator import AgentOrchestrator
from sparkai.agent.llm import LLMProvider, LLMConfig
from sparkai.agent.toolkit import (
    ToolsetRegistry, get_tools_for_role, create_engine_tools,
)
from sparkai.agent.skills.base import SkillRegistry
from sparkai.agent.skills.template import TemplateSkill, TemplateLibrary
from sparkai.agent.skills.debug import DebugSkill, DebugProtocol
from sparkai.agent.studio.directors import CreativeDirector, TechnicalDirector, Producer
from sparkai.agent.studio.leads import GameDesigner, LeadProgrammer, ArtDirector, NarrativeDirector, QALead
from sparkai.agent.studio.specialists import (
    GameplayProgrammer, EngineProgrammer, AIProgrammer,
    LevelDesigner, WorldBuilder, SoundDesigner, Writer, QATester,
)
from sparkai.agent.hooks import HookManager, HookEvent
from sparkai.agent.rules import RuleEngine, RuleScope
from sparkai.agent.team_orch import TeamOrchestrator, TeamType
from sparkai.agent.bench import GameBench
from sparkai.agent.session import SessionManager
from sparkai.agent.loop import AgentLoop, Pipeline
from sparkai.agent.commands import SlashCommand, CommandRegistry, CommandCategory
from sparkai.agent.memory_v2 import AgentMemorySystem
from sparkai.agent.events import EventBus, Event, EventChannel, get_event_bus
from sparkai.agent.context import (
    GameContext, GameGenre, PipelinePhase, AssetType,
    EntityRecord, SceneRecord, AssetRecord,
    get_game_context,
)
from sparkai.agent.llm_router import LLMRouter, TaskType, ProviderCapability
from sparkai.agent.executor import ToolExecutor, ChainStep
from sparkai.agent.runtime import AgentRuntime, RuntimeState, RuntimeConfig, get_runtime
from sparkai.agent.protocol import AgentProtocol, ProtocolMessage, MessageType, MessagePriority, get_protocol
from sparkai.agent.skill_forge import SkillForge, SkillBlueprint, SkillMaturity, get_skill_forge
from sparkai.agent.mesh import AgentMesh, AgentNode, NodeState, ConnectionType, ClusterState, get_agent_mesh
from sparkai.agent.health import HealthChecker, HealthStatus, CheckCategory, get_health_checker
from sparkai.agent.game_coder import GameCoder, CodeLanguage, CodeGenPhase, get_game_coder
from sparkai.agent.world_builder import WorldBuilder, WorldPhase, BiomeType, get_world_builder
from sparkai.agent.game_skill import GameSkillSystem, TemplateCategory, DebugSeverity, get_game_skill_system
from sparkai.agent.quality_gate import QualityGateSystem, GateCategory, GateVerdict, get_quality_gate_system
from sparkai.agent.workflow_skills import WorkflowSkillSystem, WorkflowCategory, get_workflow_skill_system
from sparkai.agent.agent_session import AgentSessionManager, SessionState, MessageRole, get_agent_session_manager
from sparkai.agent.game_pipeline import GamePipelineSystem, PipelineStage, EvalDimension, get_game_pipeline_system
from sparkai.agent.studio_coordinator import StudioCoordinator, Department, AgentTier, get_studio_coordinator
from sparkai.agent.agent_swarm import AgentSwarm, SwarmRole, ConsensusType, DecompositionStrategy, get_agent_swarm
from sparkai.agent.studio_command import StudioCommandSystem, CommandCategory, get_studio_command_system
from sparkai.agent.game_template import GameTemplateLibrary, GameGenre, TemplateMaturity, get_game_template_library
from sparkai.agent.agent_blueprint import BlueprintEngine, BlueprintState, MechanicType, ProgressionType, AestheticPillar, get_blueprint_engine
from sparkai.agent.agent_playtest import PlaytestEngine, PlaytestStatus, ScenarioType, MetricType, Severity, get_playtest_engine
from sparkai.agent.agent_composer import ComposerEngine, CompositionState, TaskType, get_composer_engine
from sparkai.agent.agent_knowledge import KnowledgeGraph, KnowledgeDomain, KnowledgeNode, KnowledgeRelation, RelationType, NodeConfidence, DesignPattern, PatternCategory, get_knowledge_graph
from sparkai.agent.agent_toolchain import ToolChainEngine, ToolChain, ChainStep, ChainStatus, StepType, ChainTemplate, TemplateCategory, get_toolchain_engine
from sparkai.agent.agent_reflex import ReflexEngine, MetricType, AnomalyType, SeverityLevel, TuningAction, ReportStatus, get_reflex_engine
from sparkai.agent.agent_dialogue import DialogueEngine, DialogueType, NodeType, MoodType, ArcStatus, get_dialogue_engine
from sparkai.agent.agent_asset import AssetPipelineEngine, AssetCategory, AssetFormat, AssetStatus, get_asset_engine
from sparkai.agent.agent_validator import ValidatorEngine, ValidationCategory, ValidationSeverity, RuleScope, FixType, get_validator_engine
from sparkai.agent.agent_orchestrator import OrchestratorEngine, AgentDescriptor, OrchestratedTask, AgentChannel, WorkflowPlan, AgentRole as OrchAgentRole, AgentCapability as OrchAgentCapability, TaskPriority, TaskStatus, WorkflowState, ChannelType, get_orchestrator_engine
from sparkai.agent.agent_skill_evolution import SkillEvolutionEngine, SkillTemplate, DebugProtocol, SkillExecution, EvolutionCycle, SkillDomain, SkillMaturity as EvolSkillMaturity, ExecutionOutcome, FixStatus as EvolFixStatus, EvolutionType, get_skill_evolution_engine
from sparkai.agent.agent_evaluator import GameEvaluatorEngine, EvaluationMetric, EvaluationReport, EvaluationBenchmark, EvalDimension, MetricType as EvalMetricType, ReportStatus, SeverityLevel as EvalSeverityLevel, get_game_evaluator
from sparkai.agent.agent_prompt_cache import PromptCache, get_prompt_cache
from sparkai.agent.agent_trajectory_recorder import TrajectoryRecorder, get_trajectory_recorder
from sparkai.agent.agent_checkpoint_system import CheckpointSystem, get_checkpoint_system
from sparkai.agent.agent_budget_tracker import BudgetTracker, get_budget_tracker
from sparkai.engine.tween_system import TweenSystem, EasingType, TweenLoopMode, get_tween_system
from sparkai.engine.node_path_system import NodePathSystem, get_node_path_system
from sparkai.engine.project_template import ProjectTemplateSystem, GameGenre, get_project_template_system
from sparkai.engine.asset_pipeline import AssetPipeline, AssetCategory, AssetFormat, get_asset_pipeline
from sparkai.agent.agent_insights import InsightsEngine, get_insights_engine
from sparkai.agent.agent_state_sync import StateSyncMesh, SyncDomain, get_state_sync_mesh
from sparkai.agent.agent_dev_loop import DevelopmentLoop, CyclePhase, get_dev_loop
from sparkai.agent.agent_context_references import ContextReferenceResolver, RefDomain, get_context_reference_resolver
from sparkai.agent.agent_process_registry import ProcessRegistry, ProcessState as ProcState, ProcessType, get_process_registry
from sparkai.agent.agent_cron_scheduler import AgentCronScheduler, get_cron_scheduler
from sparkai.agent.agent_expression_evaluator import ExpressionEvaluator, ExpressionError, get_expression_evaluator
from sparkai.agent.agent_class_registry import ClassRegistry, DataType, TypeDescriptor, get_class_registry
from sparkai.agent.agent_multi_modal import MultiModalAgent, AnalysisDomain, get_multi_modal_agent
from sparkai.agent.agent_import_pipeline import ImportPipelineEngine, AssetImportType, CompressionPreset, ImportPreset, ImportTask, get_import_pipeline
from sparkai.engine.rendering_server import RenderingServer, get_rendering_server
from sparkai.engine.input_event_system import InputEventSystem, get_input_event_system
from sparkai.engine.game_object import GameObject, GameObjectRegistry, create_game_object, get_game_object_registry
from sparkai.engine.scene_manager import SceneManager, SceneState, get_scene_manager
from sparkai.engine.terrain_system import TerrainSystem, TerrainType, NoiseAlgorithm, get_terrain_system
from sparkai.engine.save_system import SaveSystem, SaveSlot, SaveStatus, get_save_system
from sparkai.engine.network_sync import NetworkSync, SyncAuthority as NetSyncAuthority, get_network_sync
from sparkai.engine.behavior_tree import BehaviorTree, NodeStatus, Blackboard, get_behavior_tree
from sparkai.agent.agent_event_bus import AgentEventBus, get_agent_event_bus
from sparkai.agent.agent_task_queue import AgentTaskQueue, get_agent_task_queue
from sparkai.agent.agent_code_review import CodeReviewEngine, get_code_review_engine
from sparkai.agent.agent_pipeline import AgentPipeline, get_agent_pipeline
from sparkai.engine.camera_shake import CameraShakeSystem, get_camera_shake_system
from sparkai.engine.difficulty_system import DifficultySystem, get_difficulty_system
from sparkai.engine.fog_of_war import FogOfWarSystem, get_fog_of_war
from sparkai.engine.game_modes import GameModeSystem, get_game_mode_system
from sparkai.agent.agent_consensus import AgentConsensus, ConsensusProtocol, ConsensusResult, get_agent_consensus
from sparkai.agent.agent_game_analyzer import GameAnalyzer, AnalysisDimension, GameAnalysisReport, get_game_analyzer
from sparkai.agent.agent_adaptive_prompting import AdaptivePrompting, OptimizationStrategy, PromptVariant, get_adaptive_prompting
from sparkai.agent.agent_entity_extraction import EntityExtractor, EntityType, GameWorldModel, get_entity_extractor
from sparkai.engine.dialogue_system import DialogueSystem, DialogueTree, DialogueNode, get_dialogue_system
from sparkai.engine.quest_system import QuestSystem, QuestDefinition, QuestState, get_quest_system
from sparkai.engine.combat_system import CombatSystem, CombatUnit, CombatState, get_combat_system
from sparkai.engine.day_night_cycle import DayNightCycle, TimePhase, DayNightConfig, get_day_night_cycle
from sparkai.agent.agent_style_transfer import StyleTransferEngine, StyleProfile, TransferResult, get_style_transfer
from sparkai.agent.agent_curriculum_learning import CurriculumLearningEngine, SkillNode, LearningSession, get_curriculum_learning
from sparkai.agent.agent_balancing import GameBalanceTuner, GameParameter, BalanceReport, get_game_balancer
from sparkai.agent.agent_localization import ContentLocalizationEngine, Locale, LocalizedString, get_localization_engine
from sparkai.agent.agent_tutorial_design import TutorialDesignEngine, MechanicDefinition, TutorialSequence, get_tutorial_designer
from sparkai.agent.agent_game_testing import GameTestingEngine, TestCase, TestRun, get_game_tester
from sparkai.engine.weather_system import WeatherSystem, WeatherState, get_weather_system
from sparkai.engine.skill_tree_system import SkillTreeSystem, SkillNode as EngineSkillNode, get_skill_tree_system
from sparkai.engine.crafting_system import CraftingSystem, CraftingRecipe, get_crafting_system
from sparkai.engine.loot_system import LootSystem, DropTable, get_loot_system
from sparkai.engine.economy_system import EconomySystem, Wallet, get_economy_system
from sparkai.engine.cutscene_system import CutsceneSystem, CutsceneDefinition, get_cutscene_system
from sparkai.engine.character_controller import CharacterController, MovementMode, get_character_controller
from sparkai.engine.vehicle_system import VehicleSystem, VehicleType, DriveType, get_vehicle_system
from sparkai.engine.dynamic_music import DynamicMusicSystem, MusicState, MusicLayer, get_dynamic_music
from sparkai.engine.destruction_system import DestructionSystem, DestructionTier, MaterialType, get_destruction_system
from sparkai.engine.reputation_system import ReputationSystem, ReputationTier, RelationshipType, get_reputation_system
from sparkai.engine.level_streaming import LevelStreamingSystem, ChunkState, get_level_streaming
from sparkai.agent.agent_memory_consolidation import MemoryConsolidationEngine, MemoryDomain, get_memory_consolidation
from sparkai.agent.agent_conflict_resolution import ConflictResolutionEngine, ConflictType, ResolutionStrategy, get_conflict_resolver
from sparkai.agent.agent_risk_assessment import RiskAssessmentEngine, RiskCategory, RiskLevel, get_risk_assessor
from sparkai.agent.agent_documentation_generator import DocumentationGenerator, DocumentType, ExportFormat, get_documentation_generator
from sparkai.agent.agent_asset_optimizer import AssetOptimizationEngine, AssetType, QualityPreset, get_asset_optimizer
from sparkai.agent.agent_cross_platform import CrossPlatformEngine, TargetPlatform, PlatformCapability, get_cross_platform_engine
from sparkai.engine.shader_graph import ShaderGraph, get_shader_graph
from sparkai.engine.build_pipeline import BuildPipeline, get_build_pipeline
from sparkai.engine.tileset_system import TileSetSystem, get_tileset_system
from sparkai.engine.resource_pack import ResourcePack, get_resource_pack
from sparkai.engine.input_profile_system import InputProfileSystem, get_input_profile_system
from sparkai.agent.agent_shader_advisor import ShaderAdvisor, get_shader_advisor
from sparkai.agent.agent_build_orchestrator import BuildOrchestrator, get_build_orchestrator
from sparkai.agent.agent_recall_engine import RecallEngine, get_recall_engine
from sparkai.agent.agent_interaction_designer import InteractionDesigner, get_interaction_designer
from sparkai.agent.agent_physics_tuner import PhysicsTuner, get_physics_tuner
from sparkai.agent.agent_rag_pipeline import RAGPipeline, get_rag_pipeline
from sparkai.agent.agent_tree_of_thought import TreeOfThought, get_tree_of_thought
from sparkai.agent.agent_reflection_loop import ReflectionLoop, get_reflection_loop
from sparkai.engine.scene_tree import SceneTree, get_scene_tree
from sparkai.engine.event_system import EventSystem, get_event_system
from sparkai.engine.animation_system import AnimationSystem, get_animation_system
from sparkai.engine.pathfinding_system import PathfindingSystem, get_pathfinding_system
from sparkai.agent.agent_prompt_optimizer import PromptOptimizer, PromptDomain, get_prompt_optimizer
from sparkai.agent.agent_skill_composer import SkillComposer, SkillDomain, get_skill_composer
from sparkai.engine.ui_layout_system import UILayoutSystem, get_ui_layout_system
from sparkai.engine.performance_overlay import PerformanceOverlay, get_performance_overlay
from sparkai.agent.agent_developer_assistant import DeveloperAssistant, AssistantMode, get_developer_assistant
from sparkai.agent.agent_playtest_simulator import AgenticPlaytestSimulator, PlayerProfile, get_playtest_simulator
from sparkai.engine.engine_scene_streamer import SceneStreamer, get_scene_streamer
from sparkai.engine.engine_project_exporter import ProjectExporter, ExportPlatform, get_project_exporter
from sparkai.agent.agent_game_director import GameDirector, get_game_director
from sparkai.agent.agent_balance_analyzer import BalanceAnalyzer, get_balance_analyzer
from sparkai.agent.agent_narrative_composer import NarrativeComposer, get_narrative_composer
from sparkai.agent.agent_player_modeler import PlayerModeler, get_player_modeler
from sparkai.engine.engine_audio_system import GameAudioSystem, get_audio_system
from sparkai.engine.engine_network_layer import NetworkLayer, get_network_layer
from sparkai.engine.engine_behavior_runtime import BehaviorRuntime, get_behavior_runtime
from sparkai.engine.engine_save_system import SaveSystem, get_save_system
from sparkai.engine.engine_node_tree import NodeTreeSystem, get_node_tree, SceneDefinition
from sparkai.engine.engine_extension_registry import ExtensionRegistry, get_extension_registry, ExtensionDefinition, ExtensionVersion, ExtensionDependency
from sparkai.engine.engine_export_pipeline import MultiExportPipeline, get_export_pipeline, ExportTarget
from sparkai.engine.engine_server_architecture import GameServerPool, get_server_pool
from sparkai.engine.engine_gizmo_system import GizmoSystem, get_gizmo_system
from sparkai.engine.engine_pivot_system import PivotSystem, get_pivot_system
from sparkai.agent.agent_learning_loop import LearningLoop, get_learning_loop
from sparkai.agent.agent_memory_graph import AgentMemoryGraph, get_memory_graph
from sparkai.agent.agent_context_compressor import AgentContextCompressor, get_context_compressor
from sparkai.agent.agent_tool_forge import AgentToolForge, get_tool_forge
from sparkai.agent.agent_gateway import AgentGateway, get_gateway
from sparkai.agent.agent_session_snapshot import get_session_snapshot
from sparkai.agent.agent_trajectory_compressor import get_trajectory_compressor
from sparkai.agent.agent_skills_hub import get_skills_hub
from sparkai.agent.agent_personality_system import get_personality_system
from sparkai.agent.agent_insights_generator import get_insights_generator
from sparkai.agent.agent_provider_switch import get_provider_switch
from sparkai.engine.engine_event_sheet import get_event_sheet
from sparkai.engine.engine_resource_serializer import get_resource_serializer
from sparkai.engine.engine_input_map import get_input_map
from sparkai.engine.engine_animation_tree import get_animation_tree
from sparkai.engine.engine_custom_object_types import get_custom_object_types
from sparkai.engine.engine_tile_map_optimizer import get_tile_map_optimizer
from sparkai.agent.agent_chain_of_thought import get_chain_of_thought
from sparkai.agent.agent_conversation_memory import get_conversation_memory
from sparkai.agent.agent_self_optimization import get_self_optimization
from sparkai.agent.agent_collaboration_protocol import get_collaboration_protocol
from sparkai.agent.agent_knowledge_synthesis import get_knowledge_synthesis
from sparkai.agent.agent_capability_registry import get_capability_registry
from sparkai.engine.engine_physics_material import get_physics_material
from sparkai.engine.engine_gesture_recognizer import get_gesture_recognizer
from sparkai.engine.engine_shadow_casting import get_shadow_casting
from sparkai.engine.engine_entity_blueprint import get_entity_blueprint
from sparkai.engine.engine_scene_transition import get_scene_transition
from sparkai.engine.engine_audio_layering import get_audio_layering
from sparkai.agent.agent_experiment_framework import get_experiment_framework
from sparkai.agent.agent_telemetry_pipeline import get_telemetry_pipeline
from sparkai.agent.agent_audit_trail import get_audit_trail
from sparkai.agent.agent_journal_system import get_journal_system
from sparkai.agent.agent_document_synthesizer import get_document_synthesizer
from sparkai.agent.agent_simulation_runner import get_simulation_runner
from sparkai.engine.engine_material_graph import get_material_graph
from sparkai.engine.engine_occlusion_culling import get_occlusion_culling
from sparkai.engine.engine_lod_system import get_lod_system
from sparkai.engine.engine_decal_system import get_decal_system
from sparkai.engine.engine_post_processing import get_post_processing
from sparkai.engine.engine_skeleton_deformer import get_skeleton_deformer
from sparkai.agent.agent_agentic_coding import get_agentic_coding, CodingTask, CodeLanguage as AgenticCodeLanguage
from sparkai.agent.agent_game_reasoner import get_game_reasoner
from sparkai.agent.agent_narrative_branch import get_narrative_branch
from sparkai.agent.agent_concurrency_manager import get_concurrency_manager
from sparkai.agent.agent_verification_pipeline import get_verification_pipeline
from sparkai.agent.agent_playtest_simulator import get_playtest_simulator, PlaytestMode
from sparkai.engine.engine_lighting_2d import get_lighting_2d
from sparkai.engine.engine_parallax_background import get_parallax_background
from sparkai.engine.engine_behavior_library import get_behavior_library, BehaviorCategory
from sparkai.engine.engine_animation_curve import get_animation_curve, CurveType, EasingFunction
from sparkai.engine.engine_render_layer import get_render_layer
from sparkai.engine.engine_state_synchronizer import get_state_synchronizer
from sparkai.agent.agent_skill_synthesizer import get_skill_synthesizer, SynthesisTrigger, SkillMaturity, SynthesisStatus, PatternCategory
from sparkai.agent.agent_security_scanner import get_security_scanner, ThreatCategory, ScanResult, SeverityLevel, ContentSource
from sparkai.agent.agent_delegation_framework import get_delegation_framework, ChildRole, ChildStatus, DelegationStrategy, IsolationLevel
from sparkai.agent.agent_kanban_coordinator import get_kanban_coordinator, KanbanColumn, TaskType, BlockReason, HandoffType
from sparkai.agent.agent_streaming_scrubber import get_streaming_scrubber, ScrubState, BlockType as ScrubBlockType, VisibilityMode, ScrubberMode
from sparkai.agent.agent_trajectory_generator import get_trajectory_generator, TrajectoryFormat, CompressionStrategy, TurnRole, QualityLabel
from sparkai.engine.engine_visual_script_runtime import get_visual_script_runtime, NodeType, ParameterType, TargetLanguage, ValidationResult
from sparkai.engine.engine_extension_sdk import get_extension_sdk, ExtensionType, ExtensionStatus, ExtensionSource, CapabilityScope
from sparkai.engine.engine_signal_bus import get_signal_bus, SignalCategory, SignalDefinition, SignalConnection, SignalEmission, ConnectionState
from sparkai.engine.engine_prefab_composer import get_prefab_composer, PrefabType, VariantSelection, PrefabStatus, CompositionMode
from sparkai.engine.engine_interactive_audio import get_interactive_audio, AudioLayer, TransitionType, PlaybackState, IntensityLevel, AudioCategory
from sparkai.engine.engine_import_pipeline import get_import_pipeline, AssetType, ImportStatus, CompressionLevel, OptimizationTarget
from sparkai.agent.agent_developer_oracle import get_developer_oracle
from sparkai.agent.agent_context_weaver import get_context_weaver
from sparkai.agent.agent_session_nexus import get_session_nexus
from sparkai.agent.agent_persona_vault import get_persona_vault
from sparkai.agent.agent_voice_bridge import get_voice_bridge
from sparkai.agent.agent_ecosystem_hub import get_ecosystem_hub
from sparkai.engine.engine_frame_composer import get_frame_composer
from sparkai.engine.engine_spatial_cluster import get_spatial_cluster
from sparkai.engine.engine_asset_streamer import get_asset_streamer
from sparkai.engine.engine_deterministic_replay import get_deterministic_replay
from sparkai.engine.engine_input_abstraction import get_input_abstraction
from sparkai.engine.engine_profile_loader import get_profile_loader
from sparkai.agent.agent_intent_cascade import get_intent_cascade
from sparkai.agent.agent_game_forecaster import get_game_forecaster
from sparkai.agent.agent_asset_synthesizer import get_asset_synthesizer
from sparkai.agent.agent_tutorial_orchestrator import get_tutorial_orchestrator
from sparkai.engine.engine_skybox_renderer import get_skybox_renderer
from sparkai.engine.engine_trail_renderer import get_trail_renderer
from sparkai.engine.engine_procedural_audio import get_procedural_audio
from sparkai.engine.engine_texture_atlas import get_texture_atlas
from sparkai.agent.agent_ab_test_runner import get_ab_test_runner
from sparkai.agent.agent_heatmap_analyzer import get_heatmap_analyzer
from sparkai.agent.agent_bug_forensics import get_bug_forensics
from sparkai.agent.agent_accessibility_auditor import get_accessibility_auditor
from sparkai.engine.engine_tile_brush import get_tile_brush
from sparkai.engine.engine_sprite_animator import get_sprite_animator
from sparkai.engine.engine_light_culling import get_light_culling
from sparkai.engine.engine_render_pass import get_render_pass
from sparkai.agent.agent_federated_learner import get_federated_learner
from sparkai.agent.agent_swarm_planner import get_swarm_planner
from sparkai.agent.agent_world_composer import get_world_composer
from sparkai.agent.agent_playtest_orchestrator import get_playtest_orchestrator
from sparkai.engine.engine_particle_emitter import get_particle_emitter
from sparkai.engine.engine_lod_gate import get_lod_gate
from sparkai.engine.engine_scene_stack import get_scene_stack
from sparkai.engine.engine_navmesh_forge import get_navmesh_forge
from sparkai.agent.agent_reasoning_chain import get_reasoning_chain
from sparkai.agent.agent_memory_hierarchy import get_memory_hierarchy
from sparkai.agent.agent_tool_registry import get_tool_registry
from sparkai.agent.agent_prompt_templates import get_prompt_library
from sparkai.engine.engine_procedural_synthesis import get_procedural_synthesis
from sparkai.engine.engine_asset_bundler import get_asset_bundler
from sparkai.engine.engine_deterministic_recorder import get_deterministic_recorder
from sparkai.engine.engine_localization_hub import get_localization_hub

router = APIRouter()

_orchestrator = AgentOrchestrator()
_hook_manager = HookManager()
_rule_engine = RuleEngine()
_team_orchestrator = TeamOrchestrator(_orchestrator)
_game_bench = GameBench()
_session_manager = SessionManager()
_memory_system = AgentMemorySystem()

_STUDIO_AGENTS = {
    "creative_director": CreativeDirector,
    "technical_director": TechnicalDirector,
    "producer": Producer,
    "game_designer": GameDesigner,
    "lead_programmer": LeadProgrammer,
    "art_director": ArtDirector,
    "narrative_director": NarrativeDirector,
    "qa_lead": QALead,
    "gameplay_programmer": GameplayProgrammer,
    "engine_programmer": EngineProgrammer,
    "ai_programmer": AIProgrammer,
    "level_designer": LevelDesigner,
    "world_builder": WorldBuilder,
    "sound_designer": SoundDesigner,
    "writer": Writer,
    "qa_tester": QATester,
}


class AgentCreateRequest(BaseModel):
    name: str
    role: str = "specialist"
    capabilities: List[str] = ["reasoning"]
    llm_provider: Optional[str] = None
    llm_model: Optional[str] = None
    llm_api_key: Optional[str] = None


class AgentThinkRequest(BaseModel):
    agent_id: str
    prompt: str
    context: Optional[dict] = None


class AgentActRequest(BaseModel):
    agent_id: str
    action: str
    params: Optional[dict] = None


class StudioAgentCreateRequest(BaseModel):
    agent_type: str
    agent_id: Optional[str] = None


class SkillDiagnoseRequest(BaseModel):
    error_message: str


class TemplateScaffoldRequest(BaseModel):
    genre: str
    project_name: str


class ToolsetLoadRequest(BaseModel):
    agent_id: str
    toolset_name: str


class RuleCheckRequest(BaseModel):
    content: str
    scope: Optional[str] = None


class TeamCreateRequest(BaseModel):
    team_type: str


class TeamRunRequest(BaseModel):
    team_type: str
    title: str
    description: str


class BenchEvaluateRequest(BaseModel):
    code: str
    prompt: str


class SessionCreateRequest(BaseModel):
    agent_id: str
    agent_name: Optional[str] = None


class SessionMessageRequest(BaseModel):
    content: str


# === Agent CRUD ===

@router.post("/create")
async def create_agent(request: AgentCreateRequest):
    caps = []
    for cap_str in request.capabilities:
        try:
            caps.append(AgentCapability(cap_str))
        except ValueError:
            caps.append(AgentCapability.REASONING)

    try:
        role = AgentRole(request.role)
    except ValueError:
        role = AgentRole.SPECIALIST

    agent = SparkAgent(
        name=request.name,
        role=role,
        capabilities=caps,
    )

    if request.llm_provider and request.llm_api_key:
        llm_config = LLMConfig(
            provider=request.llm_provider,
            model=request.llm_model or "gpt-4",
            api_key=request.llm_api_key,
        )
        llm = LLMProvider(llm_config)
        await llm.initialize()
        agent.set_llm_provider(llm)

    _orchestrator.register_agent(agent)
    return agent.get_status()


@router.get("/list")
async def list_agents():
    return {"agents": _orchestrator.get_status()["agents"]}


# Static routes that must come before /{agent_id} to avoid being captured
# Note: Multi-segment paths like /dialogue/stats are NOT captured by /{agent_id}
# Only single-segment paths need to be before /{agent_id}


@router.get("/{agent_id}")
async def get_agent(agent_id: str):
    agent = _orchestrator.get_agent(agent_id)
    if agent:
        return agent.get_status()
    return {"error": "Agent not found"}


@router.post("/think")
async def agent_think(request: AgentThinkRequest):
    agent = _orchestrator.get_agent(request.agent_id)
    if not agent:
        return {"error": "Agent not found"}
    response = await agent.think(request.prompt, request.context)
    return {"response": response, "agent_id": request.agent_id}


@router.post("/act")
async def agent_act(request: AgentActRequest):
    agent = _orchestrator.get_agent(request.agent_id)
    if not agent:
        return {"error": "Agent not found"}
    result = await agent.act(request.action, request.params)
    return {"result": result, "agent_id": request.agent_id}


@router.delete("/{agent_id}")
async def delete_agent(agent_id: str):
    success = _orchestrator.unregister_agent(agent_id)
    return {"success": success}


# === Orchestrator ===

@router.get("/orchestrator/status")
async def orchestrator_status():
    return _orchestrator.get_status()


# === Studio Hierarchy ===

@router.get("/studio/types")
async def list_studio_types():
    return {
        "studio_agents": [
            {"type": key, "name": cls().name, "role": cls().role.value}
            for key, cls in _STUDIO_AGENTS.items()
        ]
    }


@router.post("/studio/create")
async def create_studio_agent(request: StudioAgentCreateRequest):
    agent_cls = _STUDIO_AGENTS.get(request.agent_type)
    if not agent_cls:
        return {"error": f"Unknown studio agent type: {request.agent_type}"}
    agent = agent_cls(agent_id=request.agent_id)
    _orchestrator.register_agent(agent)
    return agent.get_status()


# === Skills ===

@router.get("/skills/list")
async def list_skills():
    skills = SkillRegistry.list_skills()
    return {
        "skills": [s.to_dict() for s in skills],
        "categories": SkillRegistry.list_categories(),
    }


@router.get("/skills/categories")
async def list_skill_categories():
    return {"categories": SkillRegistry.list_categories()}


@router.post("/skills/diagnose")
async def diagnose_error(request: SkillDiagnoseRequest):
    debug_skill = DebugSkill()
    result = debug_skill.diagnose(request.error_message)
    return result


@router.post("/skills/template/scaffold")
async def scaffold_template(request: TemplateScaffoldRequest):
    template_skill = TemplateSkill()
    result = template_skill.scaffold(request.genre, request.project_name)
    return result


@router.get("/skills/templates")
async def list_templates():
    template_skill = TemplateSkill()
    templates = template_skill.library.list_templates()
    return {
        "templates": [t.to_dict() for t in templates],
        "genres": template_skill.library.list_genres(),
    }


# === Toolsets ===

@router.get("/toolsets/list")
async def list_toolsets():
    toolsets = ToolsetRegistry.list_toolsets()
    return {
        "toolsets": [ts.to_dict() for ts in toolsets],
        "names": ToolsetRegistry.list_names(),
    }


@router.post("/toolsets/load")
async def load_toolset(request: ToolsetLoadRequest):
    agent = _orchestrator.get_agent(request.agent_id)
    if not agent:
        return {"error": "Agent not found"}
    success = agent.load_toolset_by_name(request.toolset_name)
    return {"success": success, "agent_id": request.agent_id, "toolset": request.toolset_name}


@router.get("/toolsets/role/{role}")
async def get_role_toolsets(role: str):
    toolsets = get_tools_for_role(role)
    return {
        "role": role,
        "tool_count": len(toolsets),
        "tools": [t.get_schema() for t in toolsets],
    }


# === Hooks ===

@router.get("/hooks/list")
async def list_hooks(event: Optional[str] = None):
    hook_event = None
    if event:
        try:
            hook_event = HookEvent(event)
        except ValueError:
            pass
    return {"hooks": _hook_manager.list_hooks(hook_event)}


@router.post("/hooks/{name}/enable")
async def enable_hook(name: str):
    success = _hook_manager.enable_hook(name)
    return {"success": success, "hook": name}


@router.post("/hooks/{name}/disable")
async def disable_hook(name: str):
    success = _hook_manager.disable_hook(name)
    return {"success": success, "hook": name}


# === Rules ===

@router.get("/rules/list")
async def list_rules(scope: Optional[str] = None):
    rule_scope = None
    if scope:
        try:
            rule_scope = RuleScope(scope)
        except ValueError:
            pass
    return {"rules": _rule_engine.list_rules(rule_scope)}


@router.get("/rules/scopes")
async def list_rule_scopes():
    return {"scopes": _rule_engine.list_scopes()}


@router.post("/rules/check")
async def check_rules(request: RuleCheckRequest):
    scope = None
    if request.scope:
        try:
            scope = RuleScope(request.scope)
        except ValueError:
            pass
    if scope:
        violations = _rule_engine.check_scope(request.content, scope)
    else:
        violations = _rule_engine.check_all(request.content)
    return {
        "violations": [
            {
                "rule_name": v.rule_name,
                "scope": v.scope,
                "severity": v.severity,
                "message": v.message,
                "context": v.context,
                "suggestion": v.suggestion,
            }
            for v in violations
        ],
        "violation_count": len(violations),
    }


# === Teams ===

@router.get("/teams/types")
async def list_team_types():
    return {"team_types": _team_orchestrator.get_team_types()}


@router.get("/teams/list")
async def list_teams():
    return {"teams": _team_orchestrator.list_teams()}


@router.post("/teams/create")
async def create_team(request: TeamCreateRequest):
    try:
        team_type = TeamType(request.team_type)
    except ValueError:
        return {"error": f"Unknown team type: {request.team_type}"}
    team = _team_orchestrator.create_team(team_type)
    return team.get_status()


@router.post("/teams/run")
async def run_team(request: TeamRunRequest):
    try:
        team_type = TeamType(request.team_type)
    except ValueError:
        return {"error": f"Unknown team type: {request.team_type}"}
    results = await _team_orchestrator.run_team(team_type, request.title, request.description)
    return {
        "team_type": request.team_type,
        "title": request.title,
        "result_count": len(results),
        "results": [
            {
                "task_id": r.task_id,
                "agent_name": r.agent_name,
                "status": r.status,
                "duration": r.duration,
            }
            for r in results
        ],
    }


# === Bench ===

@router.post("/bench/evaluate")
async def bench_evaluate(request: BenchEvaluateRequest):
    result = _game_bench.evaluate(request.code, request.prompt)
    return result.to_dict()


@router.get("/bench/stats")
async def bench_stats():
    return _game_bench.get_stats()


@router.get("/bench/history")
async def bench_history():
    return {"history": _game_bench.get_history()}


# === Sessions ===

@router.get("/sessions/list")
async def list_sessions(agent_id: Optional[str] = None):
    return {"sessions": _session_manager.list_sessions(agent_id)}


@router.post("/sessions/create")
async def create_session(request: SessionCreateRequest):
    session = _session_manager.create_session(
        agent_id=request.agent_id,
        agent_name=request.agent_name or "",
    )
    return session.to_dict()


@router.get("/sessions/stats")
async def session_stats():
    return _session_manager.get_stats()


@router.get("/sessions/{session_id}")
async def get_session(session_id: str):
    session = _session_manager.get_session(session_id)
    if session:
        return session.to_dict()
    return {"error": "Session not found"}


@router.post("/sessions/{session_id}/end")
async def end_session(session_id: str):
    success = _session_manager.end_session(session_id)
    return {"success": success}


@router.post("/sessions/{session_id}/message")
async def send_session_message(session_id: str, request: SessionMessageRequest):
    session = _session_manager.get_session(session_id)
    if not session:
        return {"error": "Session not found"}
    msg = session.add_message("user", request.content)
    agent = _orchestrator.get_agent(session.agent_id)
    if agent:
        response = await agent.think(request.content)
        agent_msg = session.add_message("agent", response)
        return {
            "user_message": {"role": msg.role, "content": msg.content},
            "agent_message": {"role": agent_msg.role, "content": agent_msg.content},
        }
    session.add_message("agent", "[Agent not found in orchestrator]")
    return {"error": "Agent not found"}


# === Agent Skills/Toolsets ===

@router.get("/{agent_id}/skills")
async def get_agent_skills(agent_id: str):
    agent = _orchestrator.get_agent(agent_id)
    if not agent:
        return {"error": "Agent not found"}
    return {"skills": agent.list_skills()}


@router.get("/{agent_id}/toolsets")
async def get_agent_toolsets(agent_id: str):
    agent = _orchestrator.get_agent(agent_id)
    if not agent:
        return {"error": "Agent not found"}
    return {"toolsets": agent.list_toolsets(), "tools": [t.get_schema() for t in agent.tools.list_tools()]}


# === Agent Loop ===

class LoopRunRequest(BaseModel):
    goal: str
    agent_id: Optional[str] = None
    max_iterations: int = 25


class PipelineRunRequest(BaseModel):
    prompt: str
    agent_id: Optional[str] = None


@router.post("/loop/run")
async def run_agent_loop(request: LoopRunRequest):
    agent = None
    if request.agent_id:
        agent = _orchestrator.get_agent(request.agent_id)
    loop = AgentLoop(agent=agent, max_iterations=request.max_iterations)
    chain = await loop.run(request.goal)
    return chain.to_dict()


@router.get("/loop/pipeline/stages")
async def get_pipeline_stages():
    pipeline = Pipeline()
    return {"stages": pipeline.get_stages()}


@router.post("/loop/pipeline/run")
async def run_pipeline(request: PipelineRunRequest):
    agent = None
    if request.agent_id:
        agent = _orchestrator.get_agent(request.agent_id)
    pipeline = Pipeline(agent=agent)
    result = await pipeline.run(request.prompt)
    return result


# === Slash Commands ===

class CommandExecuteRequest(BaseModel):
    command: str
    args: Optional[Dict[str, Any]] = None


@router.get("/commands/list")
async def list_commands(category: Optional[str] = None):
    cat = None
    if category:
        try:
            cat = CommandCategory(category)
        except ValueError:
            pass
    commands = CommandRegistry.list_commands(cat)
    return {
        "commands": [cmd.to_dict() for cmd in commands],
        "categories": CommandRegistry.list_categories(),
    }


@router.post("/commands/parse")
async def parse_command(request: CommandExecuteRequest):
    cmd_name, args = CommandRegistry.parse_input(request.command)
    if cmd_name:
        result = await CommandRegistry.execute(cmd_name, args)
        return {"parsed_command": cmd_name, "args": args, "result": result}
    return {"error": "Not a slash command", "input": request.command}


# === Memory ===

class MemoryStoreRequest(BaseModel):
    content: str
    layer: str = "episodic"
    tags: Optional[List[str]] = None
    importance: float = 0.5


class MemorySearchRequest(BaseModel):
    query: str
    limit: int = 10


@router.get("/memory/stats")
async def memory_stats():
    return _memory_system.get_stats()


@router.post("/memory/store")
async def memory_store(request: MemoryStoreRequest):
    if request.layer == "semantic":
        entry = _memory_system.store_knowledge(request.content, request.tags, request.importance)
    elif request.layer == "procedural":
        entry = _memory_system.store_procedure(request.content, request.tags, request.importance)
    else:
        entry = _memory_system.record_event(request.content, request.tags, request.importance)
    return entry.to_dict()


@router.post("/memory/search")
async def memory_search(request: MemorySearchRequest):
    entries = _memory_system.recall(request.query, request.limit)
    return {"results": [e.to_dict() for e in entries], "count": len(entries)}


@router.post("/memory/context")
async def memory_context(request: MemorySearchRequest):
    context = _memory_system.get_context(request.query, request.limit)
    return {"context": context}


# === Runtime ===

_runtime = get_runtime()
_event_bus = get_event_bus()
_game_context = get_game_context()


@router.get("/runtime/status")
async def runtime_status():
    return _runtime.get_status()


@router.get("/runtime/full-status")
async def runtime_full_status():
    return _runtime.get_full_status()


@router.post("/runtime/initialize")
async def runtime_initialize():
    success = await _runtime.initialize()
    return {"success": success, "state": _runtime.state.value}


@router.post("/runtime/shutdown")
async def runtime_shutdown():
    await _runtime.shutdown()
    return {"state": _runtime.state.value}


class RuntimePromptRequest(BaseModel):
    prompt: str
    agent_id: Optional[str] = None
    session_id: Optional[str] = None


@router.post("/runtime/process")
async def runtime_process_prompt(request: RuntimePromptRequest):
    result = await _runtime.process_prompt(
        request.prompt,
        agent_id=request.agent_id,
        session_id=request.session_id,
    )
    return result


class RuntimePipelineRequest(BaseModel):
    prompt: str


@router.post("/runtime/pipeline")
async def runtime_run_pipeline(request: RuntimePipelineRequest):
    result = await _runtime.run_pipeline(request.prompt)
    return result


# === Game Context ===

class ContextProjectRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    genre: Optional[str] = None
    version: Optional[str] = None


class ContextEntityRequest(BaseModel):
    name: str
    entity_type: str = "generic"
    position: Optional[List[float]] = None
    rotation: Optional[List[float]] = None
    scale: Optional[List[float]] = None
    components: Optional[Dict[str, Dict[str, Any]]] = None
    tags: Optional[List[str]] = None
    scene_id: Optional[str] = None


class ContextEntityUpdateRequest(BaseModel):
    name: Optional[str] = None
    position: Optional[List[float]] = None
    rotation: Optional[List[float]] = None
    scale: Optional[List[float]] = None
    components: Optional[Dict[str, Dict[str, Any]]] = None
    tags: Optional[List[str]] = None


class ContextSceneRequest(BaseModel):
    name: str
    description: Optional[str] = None


class ContextAssetRequest(BaseModel):
    name: str
    asset_type: str = "image"
    path: Optional[str] = None
    prompt: Optional[str] = None
    style: Optional[str] = None
    tags: Optional[List[str]] = None


class ContextWorldModelRequest(BaseModel):
    gravity: Optional[List[float]] = None
    time_scale: Optional[float] = None
    physics_enabled: Optional[bool] = None
    game_rules: Optional[Dict[str, Any]] = None
    ai_parameters: Optional[Dict[str, Any]] = None


@router.get("/context/summary")
async def context_summary():
    return _game_context.get_summary()


@router.get("/context/state")
async def context_state():
    return _game_context.get_full_state()


@router.post("/context/project")
async def context_set_project(request: ContextProjectRequest):
    genre = None
    if request.genre:
        try:
            genre = GameGenre(request.genre)
        except ValueError:
            pass
    _game_context.set_project_info(
        name=request.name,
        description=request.description,
        genre=genre,
        version=request.version,
    )
    return _game_context.get_project_info()


@router.post("/context/entities")
async def context_add_entity(request: ContextEntityRequest):
    entity = EntityRecord(
        name=request.name,
        entity_type=request.entity_type,
        position=request.position or [0.0, 0.0, 0.0],
        rotation=request.rotation or [0.0, 0.0, 0.0],
        scale=request.scale or [1.0, 1.0, 1.0],
        components=request.components or {},
        tags=request.tags or [],
        scene_id=request.scene_id or "",
    )
    result = _game_context.add_entity(entity)
    return result.to_dict()


@router.get("/context/entities")
async def context_list_entities(
    scene_id: Optional[str] = None,
    entity_type: Optional[str] = None,
):
    entities = _game_context.list_entities(scene_id=scene_id, entity_type=entity_type)
    return {"entities": [e.to_dict() for e in entities], "count": len(entities)}


@router.get("/context/entities/{entity_id}")
async def context_get_entity(entity_id: str):
    entity = _game_context.get_entity(entity_id)
    if entity:
        return entity.to_dict()
    return {"error": "Entity not found"}


@router.put("/context/entities/{entity_id}")
async def context_update_entity(entity_id: str, request: ContextEntityUpdateRequest):
    updates = {k: v for k, v in request.dict().items() if v is not None}
    entity = _game_context.update_entity(entity_id, updates)
    if entity:
        return entity.to_dict()
    return {"error": "Entity not found"}


@router.delete("/context/entities/{entity_id}")
async def context_remove_entity(entity_id: str):
    success = _game_context.remove_entity(entity_id)
    return {"success": success}


@router.post("/context/scenes")
async def context_add_scene(request: ContextSceneRequest):
    scene = SceneRecord(
        name=request.name,
        description=request.description or "",
    )
    result = _game_context.add_scene(scene)
    return result.to_dict()


@router.get("/context/scenes")
async def context_list_scenes():
    scenes = _game_context.list_scenes()
    return {"scenes": [s.to_dict() for s in scenes], "count": len(scenes)}


@router.get("/context/scenes/{scene_id}")
async def context_get_scene(scene_id: str):
    scene = _game_context.get_scene(scene_id)
    if scene:
        return scene.to_dict()
    return {"error": "Scene not found"}


@router.delete("/context/scenes/{scene_id}")
async def context_remove_scene(scene_id: str):
    success = _game_context.remove_scene(scene_id)
    return {"success": success}


@router.post("/context/assets")
async def context_add_asset(request: ContextAssetRequest):
    try:
        asset_type = AssetType(request.asset_type)
    except ValueError:
        asset_type = AssetType.IMAGE
    asset = AssetRecord(
        name=request.name,
        asset_type=asset_type,
        path=request.path or "",
        prompt=request.prompt or "",
        style=request.style or "",
        tags=request.tags or [],
    )
    result = _game_context.add_asset(asset)
    return result.to_dict()


@router.get("/context/assets")
async def context_list_assets(asset_type: Optional[str] = None):
    at = None
    if asset_type:
        try:
            at = AssetType(asset_type)
        except ValueError:
            pass
    assets = _game_context.list_assets(asset_type=at)
    return {"assets": [a.to_dict() for a in assets], "count": len(assets)}


@router.delete("/context/assets/{asset_id}")
async def context_remove_asset(asset_id: str):
    success = _game_context.remove_asset(asset_id)
    return {"success": success}


@router.post("/context/world-model")
async def context_update_world_model(request: ContextWorldModelRequest):
    updates = {k: v for k, v in request.dict().items() if v is not None}
    result = _game_context.update_world_model(updates)
    return result.to_dict()


@router.post("/context/snapshot")
async def context_create_snapshot(label: Optional[str] = None):
    snapshot = _game_context.create_snapshot(label or "")
    return {
        "id": snapshot.id,
        "label": snapshot.label,
        "entity_count": snapshot.entity_count,
        "scene_count": snapshot.scene_count,
        "asset_count": snapshot.asset_count,
    }


@router.get("/context/snapshots")
async def context_list_snapshots():
    return {"snapshots": _game_context.list_snapshots()}


@router.post("/context/undo")
async def context_undo():
    success = _game_context.undo()
    return {"success": success}


@router.post("/context/redo")
async def context_redo():
    success = _game_context.redo()
    return {"success": success}


@router.post("/context/reset")
async def context_reset():
    _game_context.reset()
    return {"status": "reset"}


# === Event Bus ===

@router.get("/events/stats")
async def event_stats():
    return _event_bus.get_stats()


@router.get("/events/history")
async def event_history(
    channel: Optional[str] = None,
    topic: Optional[str] = None,
    limit: int = 50,
):
    ch = None
    if channel:
        try:
            ch = EventChannel(channel)
        except ValueError:
            pass
    events = _event_bus.get_history(channel=ch, topic=topic, limit=limit)
    return {"events": [e.to_dict() for e in events], "count": len(events)}


@router.get("/events/subscriptions")
async def event_subscriptions(channel: Optional[str] = None):
    ch = None
    if channel:
        try:
            ch = EventChannel(channel)
        except ValueError:
            pass
    return {"subscriptions": _event_bus.list_subscriptions(ch)}


@router.post("/events/clear-history")
async def event_clear_history():
    _event_bus.clear_history()
    return {"status": "cleared"}


# === LLM Router ===

class LLMRouterRegisterRequest(BaseModel):
    name: str
    provider: str = "openai"
    model: str = "gpt-4"
    api_key: str = ""
    base_url: Optional[str] = None
    capabilities: Optional[List[str]] = None
    cost_per_1k: float = 0.0
    avg_latency_ms: float = 0.0
    quality_score: float = 0.5


class LLMRouterRouteRequest(BaseModel):
    prompt: str
    task_type: Optional[str] = None
    prefer_provider: Optional[str] = None


_llm_router = _runtime.llm_router or LLMRouter()


@router.get("/llm-router/providers")
async def llm_router_providers():
    return {"providers": _llm_router.list_providers()}


@router.post("/llm-router/register")
async def llm_router_register(request: LLMRouterRegisterRequest):
    config = LLMConfig(
        provider=request.provider,
        model=request.model,
        api_key=request.api_key,
        base_url=request.base_url or "",
    )
    caps = []
    if request.capabilities:
        for cap_str in request.capabilities:
            try:
                caps.append(ProviderCapability(cap_str))
            except ValueError:
                pass
    profile = _llm_router.register_provider(
        name=request.name,
        config=config,
        capabilities=caps,
        cost_per_1k=request.cost_per_1k,
        avg_latency_ms=request.avg_latency_ms,
        quality_score=request.quality_score,
    )
    return profile.to_dict()


@router.post("/llm-router/route")
async def llm_router_route(request: LLMRouterRouteRequest):
    task_type = None
    if request.task_type:
        try:
            task_type = TaskType(request.task_type)
        except ValueError:
            pass
    response = await _llm_router.route(
        prompt=request.prompt,
        task_type=task_type,
        prefer_provider=request.prefer_provider,
    )
    return {"response": response}


@router.get("/llm-router/stats")
async def llm_router_stats():
    return _llm_router.get_routing_stats()


@router.post("/llm-router/classify")
async def llm_router_classify(request: LLMRouterRouteRequest):
    task_type = _llm_router.classify_task(request.prompt)
    return {"task_type": task_type.value, "prompt": request.prompt[:100]}


# === Tool Executor ===

class ToolExecuteRequest(BaseModel):
    tool_name: str
    params: Dict[str, Any] = {}
    use_cache: bool = True
    timeout: Optional[float] = None


class ToolChainRequest(BaseModel):
    steps: List[Dict[str, Any]]
    initial_context: Optional[Dict[str, Any]] = None


_tool_executor = _runtime.tool_executor or ToolExecutor()


@router.post("/executor/execute")
async def executor_execute(request: ToolExecuteRequest):
    result = await _tool_executor.execute(
        tool_name=request.tool_name,
        params=request.params,
        use_cache=request.use_cache,
        timeout=request.timeout,
    )
    return result.to_dict()


@router.post("/executor/chain")
async def executor_chain(request: ToolChainRequest):
    steps = []
    for step_data in request.steps:
        steps.append(ChainStep(
            tool_name=step_data.get("tool_name", ""),
            input_mapping=step_data.get("input_mapping", {}),
            constant_params=step_data.get("constant_params", {}),
        ))
    result = await _tool_executor.execute_chain(
        steps=steps,
        initial_context=request.initial_context,
    )
    return result.to_dict()


@router.get("/executor/history")
async def executor_history(
    tool_name: Optional[str] = None,
    limit: int = 50,
):
    return {"history": _tool_executor.get_history(tool_name=tool_name, limit=limit)}


@router.get("/executor/stats")
async def executor_stats():
    return _tool_executor.get_stats()


@router.post("/executor/clear-cache")
async def executor_clear_cache():
    count = _tool_executor.clear_cache()
    return {"cleared": count}


# === Agent Protocol ===

_protocol = get_protocol()


class ProtocolSendRequest(BaseModel):
    recipient: str
    topic: str
    payload: Dict[str, Any] = {}
    sender: str = "runtime"
    message_type: str = "request"
    priority: str = "normal"
    timeout: float = 30.0


class ProtocolNotifyRequest(BaseModel):
    topic: str
    payload: Dict[str, Any] = {}
    sender: str = "runtime"


class ProtocolDelegationRequest(BaseModel):
    recipient: str
    task: str
    context: Dict[str, Any] = {}
    sender: str = "runtime"


@router.get("/protocol/stats")
async def protocol_stats():
    return _protocol.get_stats()


@router.post("/protocol/send")
async def protocol_send(request: ProtocolSendRequest):
    try:
        msg_type = MessageType(request.message_type)
    except ValueError:
        msg_type = MessageType.REQUEST
    try:
        priority = MessagePriority(request.priority)
    except ValueError:
        priority = MessagePriority.NORMAL
    message = _protocol.create_request(
        recipient=request.recipient,
        topic=request.topic,
        payload=request.payload,
        sender=request.sender,
        priority=priority,
        timeout=request.timeout,
    )
    message.type = msg_type
    receipts = await _protocol.send(message)
    return {
        "message_id": message.id,
        "receipts": [r.to_dict() for r in receipts],
    }


@router.post("/protocol/notify")
async def protocol_notify(request: ProtocolNotifyRequest):
    message = _protocol.create_notification(
        topic=request.topic,
        payload=request.payload,
        sender=request.sender,
    )
    receipts = await _protocol.send(message)
    return {
        "message_id": message.id,
        "receipts": [r.to_dict() for r in receipts],
    }


@router.post("/protocol/delegate")
async def protocol_delegate(request: ProtocolDelegationRequest):
    message = _protocol.create_delegation(
        recipient=request.recipient,
        task=request.task,
        context=request.context,
        sender=request.sender,
    )
    receipts = await _protocol.send(message)
    return {
        "message_id": message.id,
        "receipts": [r.to_dict() for r in receipts],
    }


@router.get("/protocol/conversations")
async def protocol_conversations(participant: Optional[str] = None):
    return {"conversations": _protocol.list_conversations(participant=participant)}


@router.get("/protocol/messages")
async def protocol_messages(
    msg_type: Optional[str] = None,
    sender: Optional[str] = None,
    limit: int = 50,
):
    mt = None
    if msg_type:
        try:
            mt = MessageType(msg_type)
        except ValueError:
            pass
    return {"messages": _protocol.get_message_log(msg_type=mt, sender=sender, limit=limit)}


# === Skill Forge ===

_forge = get_skill_forge()


class ForgeBlueprintRequest(BaseModel):
    name: str
    category: str = "general"
    description: str = ""
    instructions: str = ""
    required_params: Optional[List[str]] = None
    optional_params: Optional[Dict[str, Any]] = None
    verification: Optional[List[str]] = None
    tags: Optional[List[str]] = None


class ForgeComposeRequest(BaseModel):
    name: str
    description: str = ""
    skill_names: List[str]
    context_mapping: Optional[Dict[str, Dict[str, str]]] = None


class ForgeExecutionRequest(BaseModel):
    skill_name: str
    success: bool
    duration_ms: float = 0.0
    error: Optional[str] = None


@router.get("/forge/stats")
async def forge_stats():
    return _forge.get_stats()


@router.post("/forge/blueprint")
async def forge_create_blueprint(request: ForgeBlueprintRequest):
    blueprint = _forge.create_blueprint(
        name=request.name,
        category=request.category,
        description=request.description,
        instructions=request.instructions,
        required_params=request.required_params,
        optional_params=request.optional_params,
        verification=request.verification,
        tags=request.tags,
    )
    return blueprint.to_dict()


@router.post("/forge/forged")
async def forge_forge_skill(request: ForgeBlueprintRequest):
    blueprint = _forge.create_blueprint(
        name=request.name,
        category=request.category,
        description=request.description,
        instructions=request.instructions,
        required_params=request.required_params,
        optional_params=request.optional_params,
        verification=request.verification,
        tags=request.tags,
    )
    skill = _forge.forge_skill(blueprint)
    return skill.to_dict()


@router.post("/forge/compose")
async def forge_compose(request: ForgeComposeRequest):
    try:
        composed = _forge.compose_skill(
            name=request.name,
            description=request.description,
            skill_names=request.skill_names,
            context_mapping=request.context_mapping,
        )
        return composed.to_dict()
    except ValueError as e:
        return {"error": str(e)}

# ============================================================
# Game Design Intelligence Endpoints
# ============================================================

@router.get("/game-design-intelligence/stats")
async def game_design_intelligence_stats():
    try:
        return _game_design_intelligence.get_stats()
    except Exception as e:
        return {"error": str(e)}

@router.post("/game-design-intelligence/start-session")
async def game_design_intelligence_start_session(request: Request):
    try:
        body = await request.json()
        result = _game_design_intelligence.start_session(
            topic=body.get("topic", ""),
            domain=body.get("domain", "core_loop"),
        )
        return result.to_dict()
    except Exception as e:
        return {"error": str(e)}

@router.post("/game-design-intelligence/brainstorm")
async def game_design_intelligence_brainstorm(request: Request):
    try:
        body = await request.json()
        result = _game_design_intelligence.brainstorm_mechanics(
            seed_concept=body.get("seed_concept", ""),
            genre=body.get("genre", "action"),
            count=body.get("count", 5),
            innovation_level=body.get("innovation_level", 0.7),
        )
        return {"concepts": [c.to_dict() for c in result], "count": len(result)}
    except Exception as e:
        return {"error": str(e)}

@router.post("/game-design-intelligence/analyze-mechanic")
async def game_design_intelligence_analyze_mechanic(request: Request):
    try:
        body = await request.json()
        result = _game_design_intelligence.analyze_mechanic(
            mechanic_name=body.get("mechanic_name", ""),
            context=body.get("context"),
        )
        return result.to_dict()
    except Exception as e:
        return {"error": str(e)}

@router.post("/game-design-intelligence/evaluate-fun")
async def game_design_intelligence_evaluate_fun(request: Request):
    try:
        body = await request.json()
        result = _game_design_intelligence.evaluate_fun_factor(
            concept_id=body.get("concept_id", ""),
        )
        return result
    except Exception as e:
        return {"error": str(e)}

@router.post("/game-design-intelligence/iterate-concept")
async def game_design_intelligence_iterate_concept(request: Request):
    try:
        body = await request.json()
        result = _game_design_intelligence.iterate_concept(
            concept_id=body.get("concept_id", ""),
            iteration_direction=body.get("direction", "deepen"),
        )
        return result.to_dict()
    except Exception as e:
        return {"error": str(e)}

@router.post("/game-design-intelligence/generate-pitch")
async def game_design_intelligence_generate_pitch(request: Request):
    try:
        body = await request.json()
        result = _game_design_intelligence.generate_pitch(
            concept_id=body.get("concept_id", ""),
        )
        return result
    except Exception as e:
        return {"error": str(e)}

# ============================================================
# Game State Analyzer Endpoints
# ============================================================

@router.get("/game-state-analyzer/stats")
async def game_state_analyzer_stats():
    try:
        return _game_state_analyzer.get_stats()
    except Exception as e:
        return {"error": str(e)}

@router.post("/game-state-analyzer/register-scene")
async def game_state_analyzer_register_scene(request: Request):
    try:
        body = await request.json()
        result = _game_state_analyzer.register_scene(
            scene_id=body.get("scene_id", ""),
            scene_name=body.get("scene_name", ""),
            entities=body.get("entities"),
            active_systems=body.get("active_systems"),
            metadata=body.get("metadata"),
        )
        return result
    except Exception as e:
        return {"error": str(e)}

@router.post("/game-state-analyzer/analyze-scene")
async def game_state_analyzer_analyze_scene(request: Request):
    try:
        body = await request.json()
        result = _game_state_analyzer.analyze_scene(
            scene_id=body.get("scene_id", ""),
            entities=body.get("entities"),
            analysis_domains=body.get("analysis_domains"),
        )
        return result
    except Exception as e:
        return {"error": str(e)}

@router.post("/game-state-analyzer/optimization-hints")
async def game_state_analyzer_optimization_hints(request: Request):
    try:
        body = await request.json()
        result = _game_state_analyzer.generate_optimization_hints(
            scene_id=body.get("scene_id", ""),
        )
        return result
    except Exception as e:
        return {"error": str(e)}

@router.post("/game-state-analyzer/validate-scene")
async def game_state_analyzer_validate_scene(request: Request):
    try:
        body = await request.json()
        result = _game_state_analyzer.validate_scene_integrity(
            scene_id=body.get("scene_id", ""),
        )
        return result
    except Exception as e:
        return {"error": str(e)}


# ============================================================
# Interaction Synthesis Engine Endpoints
# ============================================================

@router.get("/interaction-synthesis/stats")
async def interaction_synthesis_stats():
    try:
        return _interaction_synthesis_engine.get_stats()
    except Exception as e:
        return {"error": str(e)}


@router.post("/interaction-synthesis/synthesize")
async def interaction_synthesis_synthesize(request: Request):
    try:
        body = await request.json()
        result = _interaction_synthesis_engine.synthesize_interaction_network(
            description=body.get("description", ""),
            domains=body.get("domains"),
            interaction_count=body.get("interaction_count", 8),
            complexity_target=body.get("complexity_target", 0.6),
        )
        return result.to_dict()
    except Exception as e:
        return {"error": str(e)}


@router.post("/interaction-synthesis/compute-progression")
async def interaction_synthesis_progression(request: Request):
    try:
        body = await request.json()
        result = _interaction_synthesis_engine.compute_progression_curve(
            interaction_id=body.get("interaction_id", ""),
            scaling_type=body.get("scaling_type", "linear"),
            initial_difficulty=body.get("initial_difficulty", 0.3),
            final_difficulty=body.get("final_difficulty", 0.9),
            step_count=body.get("step_count", 10),
        )
        return result.to_dict()
    except Exception as e:
        return {"error": str(e)}


@router.post("/interaction-synthesis/detect-conflicts")
async def interaction_synthesis_conflicts(request: Request):
    try:
        body = await request.json()
        result = _interaction_synthesis_engine.detect_interaction_conflicts(
            network_id=body.get("network_id", ""),
            tolerance=body.get("tolerance", 0.4),
        )
        return {"conflicts": [c.to_dict() for c in result], "count": len(result)}
    except Exception as e:
        return {"error": str(e)}


@router.post("/interaction-synthesis/generate-feedback")
async def interaction_synthesis_feedback(request: Request):
    try:
        body = await request.json()
        result = _interaction_synthesis_engine.generate_feedback_spec(
            interaction_id=body.get("interaction_id", ""),
            channels=body.get("channels"),
            intensity=body.get("intensity", 0.7),
        )
        return {"specs": [s.to_dict() for s in result], "count": len(result)}
    except Exception as e:
        return {"error": str(e)}


@router.post("/interaction-synthesis/validate-loop")
async def interaction_synthesis_validate_loop(request: Request):
    try:
        body = await request.json()
        result = _interaction_synthesis_engine.validate_loop_integrity(
            network_id=body.get("network_id", ""),
        )
        return result
    except Exception as e:
        return {"error": str(e)}


@router.get("/interaction-synthesis/networks")
async def interaction_synthesis_networks():
    try:
        return {"networks": _interaction_synthesis_engine.list_networks()}
    except Exception as e:
        return {"error": str(e)}


# ============================================================
# Game Runtime Orchestrator Endpoints
# ============================================================

@router.get("/runtime-orchestrator/stats")
async def runtime_orchestrator_stats():
    try:
        return _game_runtime_orchestrator.get_stats()
    except Exception as e:
        return {"error": str(e)}


@router.post("/runtime-orchestrator/register-system")
async def runtime_orchestrator_register_system(request: Request):
    try:
        body = await request.json()
        result = _game_runtime_orchestrator.register_managed_system(
            name=body.get("name", ""),
            priority=body.get("priority", "MEDIUM"),
            execution_phases=body.get("execution_phases"),
            dependencies=body.get("dependencies"),
            frame_budget_ms=body.get("frame_budget_ms", 2.0),
            metadata=body.get("metadata"),
        )
        return result.to_dict()
    except Exception as e:
        return {"error": str(e)}


@router.post("/runtime-orchestrator/initialize-system")
async def runtime_orchestrator_init_system(request: Request):
    try:
        body = await request.json()
        result = _game_runtime_orchestrator.initialize_system(
            system_id=body.get("system_id", ""),
        )
        return {"success": result}
    except Exception as e:
        return {"error": str(e)}


@router.post("/runtime-orchestrator/orchestrate-frame")
async def runtime_orchestrator_frame():
    try:
        result = _game_runtime_orchestrator.orchestrate_frame()
        return result
    except Exception as e:
        return {"error": str(e)}


@router.post("/runtime-orchestrator/create-scene")
async def runtime_orchestrator_create_scene(request: Request):
    try:
        body = await request.json()
        result = _game_runtime_orchestrator.create_scene(
            name=body.get("name", ""),
            entity_count=body.get("entity_count", 0),
            entity_types=body.get("entity_types"),
            parent_scene_id=body.get("parent_scene_id"),
        )
        return result.to_dict()
    except Exception as e:
        return {"error": str(e)}


@router.post("/runtime-orchestrator/transition-scene")
async def runtime_orchestrator_transition_scene(request: Request):
    try:
        body = await request.json()
        result = _game_runtime_orchestrator.transition_scene(
            target_scene_id=body.get("target_scene_id", ""),
            unload_current=body.get("unload_current", True),
        )
        return result
    except Exception as e:
        return {"error": str(e)}


@router.get("/runtime-orchestrator/state")
async def runtime_orchestrator_state():
    try:
        return _game_runtime_orchestrator.query_runtime_state()
    except Exception as e:
        return {"error": str(e)}


@router.get("/runtime-orchestrator/systems")
async def runtime_orchestrator_systems():
    try:
        return {"systems": _game_runtime_orchestrator.list_systems()}
    except Exception as e:
        return {"error": str(e)}


@router.get("/runtime-orchestrator/scenes")
async def runtime_orchestrator_scenes():
    try:
        return {"scenes": _game_runtime_orchestrator.list_scenes()}
    except Exception as e:
        return {"error": str(e)}


@router.post("/forge/record-execution")
async def forge_record_execution(request: ForgeExecutionRequest):
    evolution = _forge.record_execution(
        skill_name=request.skill_name,
        success=request.success,
        duration_ms=request.duration_ms,
        error=request.error,
    )
    return evolution.to_dict()


@router.post("/forge/evolve/{skill_name}")
async def forge_evolve(skill_name: str):
    evolution = _forge.evolve_skill(skill_name)
    if evolution:
        return evolution.to_dict()
    return {"error": f"Skill '{skill_name}' not found"}


@router.get("/forge/evolution/{skill_name}")
async def forge_get_evolution(skill_name: str):
    result = _forge.get_evolution(skill_name)
    if result:
        return result
    return {"error": f"Skill '{skill_name}' not found"}


@router.get("/forge/validate/{skill_name}")
async def forge_validate(skill_name: str):
    return _forge.validate_skill(skill_name)


@router.get("/forge/blueprints")
async def forge_list_blueprints():
    return {"blueprints": _forge.list_blueprints()}


@router.get("/forge/composed")
async def forge_list_composed():
    return {"composed": _forge.list_composed()}


@router.get("/forge/evolutions")
async def forge_list_evolutions(min_maturity: Optional[str] = None):
    mm = None
    if min_maturity:
        try:
            mm = SkillMaturity(min_maturity)
        except ValueError:
            pass
    return {"evolutions": _forge.list_evolutions(min_maturity=mm)}


@router.get("/forge/history")
async def forge_history(limit: int = 50):
    return {"history": _forge.get_forge_history(limit=limit)}


# === Agent Mesh ===

_mesh = get_agent_mesh()


class MeshRegisterRequest(BaseModel):
    agent_id: str
    name: str = ""
    role: str = "specialist"
    capabilities: Optional[List[str]] = None
    max_workload: int = 5


class MeshConnectRequest(BaseModel):
    agent_a: str
    agent_b: str
    connection_type: str = "direct"


class MeshClusterRequest(BaseModel):
    name: str
    goal: str
    member_ids: List[str]
    leader_id: Optional[str] = None


class MeshTaskRequest(BaseModel):
    agent_id: str


@router.get("/mesh/topology")
async def mesh_topology():
    return _mesh.get_topology()


@router.get("/mesh/stats")
async def mesh_stats():
    return _mesh.get_stats()


@router.post("/mesh/register")
async def mesh_register(request: MeshRegisterRequest):
    try:
        node = _mesh.register_node(
            agent_id=request.agent_id,
            name=request.name,
            role=request.role,
            capabilities=request.capabilities,
            max_workload=request.max_workload,
        )
        return node.to_dict()
    except ValueError as e:
        return {"error": str(e)}


@router.delete("/mesh/nodes/{agent_id}")
async def mesh_unregister(agent_id: str):
    success = _mesh.unregister_node(agent_id)
    return {"success": success}


@router.get("/mesh/nodes")
async def mesh_list_nodes(state: Optional[str] = None):
    ns = None
    if state:
        try:
            ns = NodeState(state)
        except ValueError:
            pass
    return {"nodes": _mesh.list_nodes(state=ns)}


@router.get("/mesh/nodes/{agent_id}")
async def mesh_get_node(agent_id: str):
    result = _mesh.get_node(agent_id)
    if result:
        return result
    return {"error": "Node not found"}


@router.post("/mesh/connect")
async def mesh_connect(request: MeshConnectRequest):
    try:
        ct = ConnectionType(request.connection_type)
    except ValueError:
        ct = ConnectionType.DIRECT
    conn = _mesh.connect(request.agent_a, request.agent_b, ct)
    if conn:
        return conn.to_dict()
    return {"error": "One or both agents not found"}


@router.post("/mesh/disconnect")
async def mesh_disconnect(request: MeshConnectRequest):
    success = _mesh.disconnect(request.agent_a, request.agent_b)
    return {"success": success}


@router.get("/mesh/connections")
async def mesh_list_connections(agent_id: Optional[str] = None):
    return {"connections": _mesh.list_connections(agent_id=agent_id)}


@router.post("/mesh/cluster")
async def mesh_form_cluster(request: MeshClusterRequest):
    cluster = _mesh.form_cluster(
        name=request.name,
        goal=request.goal,
        member_ids=request.member_ids,
        leader_id=request.leader_id,
    )
    if cluster:
        return cluster.to_dict()
    return {"error": "Could not form cluster"}


@router.delete("/mesh/clusters/{cluster_id}")
async def mesh_dissolve_cluster(cluster_id: str):
    success = _mesh.dissolve_cluster(cluster_id)
    return {"success": success}


@router.get("/mesh/clusters")
async def mesh_list_clusters(state: Optional[str] = None):
    cs = None
    if state:
        try:
            cs = ClusterState(state)
        except ValueError:
            pass
    return {"clusters": _mesh.list_clusters(state=cs)}


@router.get("/mesh/clusters/{cluster_id}")
async def mesh_get_cluster(cluster_id: str):
    result = _mesh.get_cluster(cluster_id)
    if result:
        return result
    return {"error": "Cluster not found"}


@router.post("/mesh/assign-task")
async def mesh_assign_task(request: MeshTaskRequest):
    success = _mesh.assign_task(request.agent_id)
    return {"success": success}


@router.post("/mesh/release-task")
async def mesh_release_task(request: MeshTaskRequest):
    success = _mesh.release_task(request.agent_id)
    return {"success": success}


@router.get("/mesh/discover")
async def mesh_discover(
    capability: Optional[str] = None,
    role: Optional[str] = None,
    available_only: bool = True,
):
    agents = _mesh.find_agents(capability=capability, role=role, available_only=available_only)
    return {"agents": [a.to_dict() for a in agents], "count": len(agents)}


@router.get("/mesh/best-agent")
async def mesh_best_agent(capability: str):
    agent = _mesh.find_best_agent(capability)
    if agent:
        return agent.to_dict()
    return {"error": f"No available agent for capability '{capability}'"}


# === Health Check ===

_health_checker = get_health_checker()


@router.get("/health/check")
async def health_check():
    report = _health_checker.check_all()
    return report.to_dict()


@router.get("/health/stats")
async def health_stats():
    return _health_checker.get_stats()


@router.get("/health/history")
async def health_history(limit: int = 10):
    return {"history": _health_checker.get_history(limit=limit)}


# === Game Coder ===

_game_coder = get_game_coder()


class GameCodeGenRequest(BaseModel):
    prompt: str
    project_name: Optional[str] = None
    target_language: str = "typescript"
    max_iterations: int = 3


@router.post("/coder/generate")
async def game_coder_generate(request: GameCodeGenRequest):
    lang_map = {l.value: l for l in CodeLanguage}
    target_lang = lang_map.get(request.target_language, CodeLanguage.TYPESCRIPT)
    project = await _game_coder.generate(
        prompt=request.prompt,
        project_name=request.project_name or "",
        target_language=target_lang,
        max_iterations=request.max_iterations,
    )
    return project.to_dict()


@router.get("/coder/projects")
async def game_coder_projects():
    return {"projects": _game_coder.list_projects()}


@router.get("/coder/projects/{project_id}")
async def game_coder_project(project_id: str):
    project = _game_coder.get_project(project_id)
    if project:
        return project.to_dict()
    return {"error": f"Project '{project_id}' not found"}


@router.get("/coder/stats")
async def game_coder_stats():
    return _game_coder.get_stats()


# === World Builder ===

_world_builder = get_world_builder()


class WorldBuildRequest(BaseModel):
    prompt: str
    world_name: Optional[str] = None
    width: int = 64
    height: int = 64
    seed: Optional[int] = None
    entity_density: float = 0.5
    structure_count: int = 5


@router.post("/world-builder/build")
async def world_builder_build(request: WorldBuildRequest):
    world = await _world_builder.build(
        prompt=request.prompt,
        world_name=request.world_name or "",
        width=request.width,
        height=request.height,
        seed=request.seed,
        entity_density=request.entity_density,
        structure_count=request.structure_count,
    )
    return world.to_dict()


@router.get("/world-builder/worlds")
async def world_builder_worlds():
    return {"worlds": _world_builder.list_worlds()}


@router.get("/world-builder/worlds/{world_id}")
async def world_builder_world(world_id: str):
    world = _world_builder.get_world(world_id)
    if world:
        return world.to_dict()
    return {"error": f"World '{world_id}' not found"}


@router.get("/world-builder/stats")
async def world_builder_stats():
    return _world_builder.get_stats()


# === Game Skill System ===

_game_skill_system = get_game_skill_system()


@router.get("/game-skill/stats")
async def game_skill_stats():
    return _game_skill_system.get_stats()


@router.get("/game-skill/templates")
async def game_skill_templates(category: Optional[str] = None):
    cat = TemplateCategory(category) if category else None
    templates = _game_skill_system.templates.list_templates(cat)
    return {"templates": [t.to_dict() for t in templates]}


@router.get("/game-skill/templates/{template_id}")
async def game_skill_template(template_id: str):
    template = _game_skill_system.templates.get(template_id)
    if template:
        return template.to_dict()
    return {"error": f"Template '{template_id}' not found"}


@router.get("/game-skill/templates/find/{genre}")
async def game_skill_find_template(genre: str):
    template = _game_skill_system.find_template(genre)
    if template:
        return template.to_dict()
    return {"error": f"No template found for genre '{genre}'"}


@router.get("/game-skill/debugs")
async def game_skill_debugs(status: Optional[str] = None):
    from sparkai.agent.game_skill import FixStatus
    st = FixStatus(status) if status else None
    entries = _game_skill_system.debugs.list_entries(st)
    return {"entries": [e.to_dict() for e in entries]}


@router.get("/game-skill/debugs/find")
async def game_skill_find_debug(error: str):
    entries = _game_skill_system.find_fixes(error)
    return {"entries": [e.to_dict() for e in entries]}


@router.get("/game-skill/evolution")
async def game_skill_evolution():
    return _game_skill_system.get_evolution_suggestions()


@router.get("/game-skill/composed")
async def game_skill_composed():
    composed = _game_skill_system.composer.list_composed()
    return {"composed": [c.to_dict() for c in composed]}


# === Quality Gate System ===

_quality_gate_system = get_quality_gate_system()


@router.get("/quality-gate/stats")
async def quality_gate_stats():
    return _quality_gate_system.get_stats()


@router.get("/quality-gate/gates")
async def quality_gate_gates(category: Optional[str] = None):
    cat = GateCategory(category) if category else None
    gates = _quality_gate_system.list_gates(cat)
    return {"gates": [g.to_dict() for g in gates]}


@router.post("/quality-gate/evaluate/{gate_id}")
async def quality_gate_evaluate(gate_id: str):
    result = _quality_gate_system.evaluate_gate(gate_id)
    if result:
        return result.to_dict()
    return {"error": f"Gate '{gate_id}' not found"}


@router.post("/quality-gate/evaluate-phase/{phase}")
async def quality_gate_evaluate_phase(phase: str):
    report = _quality_gate_system.evaluate_phase(phase)
    return report.to_dict()


@router.post("/quality-gate/evaluate-all")
async def quality_gate_evaluate_all():
    report = _quality_gate_system.evaluate_all()
    return report.to_dict()


@router.get("/quality-gate/reports")
async def quality_gate_reports(limit: int = 10):
    reports = _quality_gate_system.get_reports(limit)
    return {"reports": [r.to_dict() for r in reports]}


# === Workflow Skills ===

_workflow_skill_system = get_workflow_skill_system()


@router.get("/workflow-skills/stats")
async def workflow_skills_stats():
    return _workflow_skill_system.get_stats()


@router.get("/workflow-skills/list")
async def workflow_skills_list(category: Optional[str] = None, tag: Optional[str] = None):
    cat = WorkflowCategory(category) if category else None
    skills = _workflow_skill_system.list_skills(cat, tag)
    return {"skills": [s.to_dict() for s in skills]}


@router.get("/workflow-skills/{skill_id}")
async def workflow_skills_get(skill_id: str):
    skill = _workflow_skill_system.get_skill(skill_id)
    if skill:
        return skill.to_dict()
    return {"error": f"Skill '{skill_id}' not found"}


@router.post("/workflow-skills/{skill_id}/execute")
async def workflow_skills_execute(skill_id: str, inputs: Optional[Dict[str, Any]] = None):
    execution = _workflow_skill_system.execute_skill(skill_id, inputs)
    return execution.to_dict()


@router.get("/workflow-skills/command/{command}")
async def workflow_skills_by_command(command: str):
    cmd = f"/{command}" if not command.startswith("/") else command
    skill = _workflow_skill_system.find_by_command(cmd)
    if skill:
        return skill.to_dict()
    return {"error": f"Command '{cmd}' not found"}


# === Agent Session Manager ===

_agent_session_manager = get_agent_session_manager()


class CreateSessionRequest(BaseModel):
    agent_id: Optional[str] = None
    agent_name: Optional[str] = None
    name: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class SendMessageRequest(BaseModel):
    role: str = "user"
    content: str
    metadata: Optional[Dict[str, Any]] = None
    token_count: int = 0


@router.post("/sessions-v2/create")
async def session_v2_create(request: CreateSessionRequest):
    session = _agent_session_manager.create_session(
        agent_id=request.agent_id or "",
        agent_name=request.agent_name or "",
        name=request.name or "",
        metadata=request.metadata,
    )
    return session.to_dict()


@router.get("/sessions-v2/list")
async def session_v2_list(state: Optional[str] = None):
    st = SessionState(state) if state else None
    sessions = _agent_session_manager.list_sessions(st)
    return {"sessions": [s.to_dict() for s in sessions]}


@router.get("/sessions-v2/stats")
async def session_v2_stats():
    return _agent_session_manager.get_stats()


@router.get("/sessions-v2/{session_id}")
async def session_v2_get(session_id: str):
    session = _agent_session_manager.get_session(session_id)
    if session:
        return session.to_dict()
    return {"error": f"Session '{session_id}' not found"}


@router.post("/sessions-v2/{session_id}/message")
async def session_v2_message(session_id: str, request: SendMessageRequest):
    role = MessageRole(request.role)
    msg = _agent_session_manager.send_message(session_id, role, request.content, request.metadata, request.token_count)
    if msg:
        return msg.to_dict()
    return {"error": "Failed to send message"}


@router.get("/sessions-v2/{session_id}/context")
async def session_v2_context(session_id: str, max_tokens: Optional[int] = None):
    return {"context": _agent_session_manager.get_context(session_id, max_tokens)}


@router.post("/sessions-v2/{session_id}/checkpoint")
async def session_v2_checkpoint(session_id: str, name: str = "", description: str = ""):
    checkpoint = _agent_session_manager.create_checkpoint(session_id, name, description)
    if checkpoint:
        return checkpoint.to_dict()
    return {"error": "Failed to create checkpoint"}


@router.get("/sessions-v2/{session_id}/checkpoints")
async def session_v2_checkpoints(session_id: str):
    return {"checkpoints": _agent_session_manager.get_checkpoints(session_id)}


@router.post("/sessions-v2/{session_id}/resume")
async def session_v2_resume(session_id: str):
    session = _agent_session_manager.resume_session(session_id)
    if session:
        return session.to_dict()
    return {"error": "Failed to resume session"}


@router.post("/sessions-v2/{session_id}/close")
async def session_v2_close(session_id: str):
    if _agent_session_manager.close_session(session_id):
        return {"status": "closed"}
    return {"error": "Session not found"}


# === Game Pipeline ===

_game_pipeline_system = get_game_pipeline_system()


class StartPipelineRequest(BaseModel):
    prompt: str
    name: Optional[str] = None


@router.post("/pipeline/start")
async def pipeline_start(request: StartPipelineRequest):
    run = await _game_pipeline_system.start(request.prompt, request.name or "")
    return run.to_dict()


@router.get("/pipeline/runs")
async def pipeline_runs(status: Optional[str] = None):
    return {"runs": _game_pipeline_system.list_runs(status)}


@router.get("/pipeline/runs/{run_id}")
async def pipeline_run(run_id: str):
    run = _game_pipeline_system.get_run(run_id)
    if run:
        return run.to_dict()
    return {"error": f"Run '{run_id}' not found"}


@router.get("/pipeline/stages")
async def pipeline_stages():
    return {"stages": _game_pipeline_system.get_stages()}


@router.get("/pipeline/stats")
async def pipeline_stats():
    return _game_pipeline_system.get_stats()


# === Studio Coordinator ===

_studio_coordinator = get_studio_coordinator()
_agent_swarm = get_agent_swarm()
_studio_command_system = get_studio_command_system()
_game_template_library = get_game_template_library()
_blueprint_engine = get_blueprint_engine()
_playtest_engine = get_playtest_engine()
_composer_engine = get_composer_engine()
_knowledge_graph = get_knowledge_graph()
_toolchain_engine = get_toolchain_engine()
_reflex_engine = get_reflex_engine()
_dialogue_engine = get_dialogue_engine()
_asset_engine = get_asset_engine()
_validator_engine = get_validator_engine()
_orchestrator_engine = get_orchestrator_engine()
_skill_evolution_engine = get_skill_evolution_engine()
_game_evaluator = get_game_evaluator()
_prompt_cache = get_prompt_cache()
_trajectory_recorder = get_trajectory_recorder()
_checkpoint_system = get_checkpoint_system()
_budget_tracker = get_budget_tracker()
_insights_engine = get_insights_engine()
_state_sync_mesh = get_state_sync_mesh()
_dev_loop = get_dev_loop()
_context_reference_resolver = get_context_reference_resolver()
_process_registry = get_process_registry()
_cron_scheduler = get_cron_scheduler()
_expression_evaluator = get_expression_evaluator()
_class_registry = get_class_registry()
_multi_modal_agent = get_multi_modal_agent()
_import_pipeline = get_import_pipeline()
_agent_event_bus = get_agent_event_bus()
_agent_task_queue = get_agent_task_queue()
_code_review_engine = get_code_review_engine()
_agent_pipeline = get_agent_pipeline()
_agent_consensus = get_agent_consensus()
_game_analyzer = get_game_analyzer()
_adaptive_prompting = get_adaptive_prompting()
_entity_extractor = get_entity_extractor()
_style_transfer = get_style_transfer()
_curriculum_learning = get_curriculum_learning()
_game_balancer = get_game_balancer()
_localization_engine = get_localization_engine()
_tutorial_designer = get_tutorial_designer()
_game_tester = get_game_tester()
_memory_consolidation = get_memory_consolidation()
_conflict_resolver = get_conflict_resolver()
_risk_assessor = get_risk_assessor()
_documentation_generator = get_documentation_generator()
_asset_optimizer = get_asset_optimizer()
_cross_platform_engine = get_cross_platform_engine()
_shader_graph = get_shader_graph()
_build_pipeline = get_build_pipeline()
_tileset_system = get_tileset_system()
_resource_pack = get_resource_pack()
_input_profile_system = get_input_profile_system()
_shader_advisor = get_shader_advisor()
_build_orchestrator = get_build_orchestrator()
_recall_engine = get_recall_engine()
_interaction_designer = get_interaction_designer()
_physics_tuner = get_physics_tuner()
_rag_pipeline = get_rag_pipeline()
_tree_of_thought = get_tree_of_thought()
_scene_tree = get_scene_tree()
_event_system = get_event_system()
_animation_system = get_animation_system()
_pathfinding_system = get_pathfinding_system()
_prompt_optimizer = get_prompt_optimizer()
_skill_composer = get_skill_composer()
_ui_layout_system = get_ui_layout_system()
_performance_overlay = get_performance_overlay()
_developer_assistant = get_developer_assistant()
_playtest_simulator = get_playtest_simulator()
_scene_streamer = get_scene_streamer()
_project_exporter = get_project_exporter()
_game_director = get_game_director()
_balance_analyzer = get_balance_analyzer()
_narrative_composer = get_narrative_composer()
_player_modeler = get_player_modeler()
_audio_system = get_audio_system()
_network_layer = get_network_layer()
_behavior_runtime = get_behavior_runtime()
_save_system = get_save_system()
_node_tree = get_node_tree()
_extension_registry = get_extension_registry()
_export_pipeline = get_export_pipeline()
_server_pool = get_server_pool()
_gizmo_system = get_gizmo_system()
_pivot_system = get_pivot_system()
_learning_loop = get_learning_loop()
_cron_scheduler = get_cron_scheduler()
_memory_graph = get_memory_graph()
_context_compressor = get_context_compressor()
_tool_forge = get_tool_forge()
_gateway = get_gateway()
_session_snapshot = get_session_snapshot()
_trajectory_compressor = get_trajectory_compressor()
_skills_hub = get_skills_hub()
_personality_system = get_personality_system()
_insights_generator = get_insights_generator()
_provider_switch = get_provider_switch()
_event_sheet = get_event_sheet()
_resource_serializer = get_resource_serializer()
_input_map = get_input_map()
_animation_tree = get_animation_tree()
_custom_object_types = get_custom_object_types()
_tile_map_optimizer = get_tile_map_optimizer()

# ---- Chain of Thought ----
_chain_of_thought = get_chain_of_thought()

# ---- Conversation Memory ----
_conversation_memory = get_conversation_memory()

# ---- Self Optimization ----
_self_optimization = get_self_optimization()

# ---- Collaboration Protocol ----
_collaboration_protocol = get_collaboration_protocol()

# ---- Knowledge Synthesis ----
_knowledge_synthesis = get_knowledge_synthesis()

# ---- Capability Registry ----
_capability_registry = get_capability_registry()

# ---- Physics Material ----
_physics_material = get_physics_material()

# ---- Gesture Recognizer ----
_gesture_recognizer = get_gesture_recognizer()

# ---- Shadow Casting ----
_shadow_casting = get_shadow_casting()

# ---- Entity Blueprint ----
_entity_blueprint = get_entity_blueprint()

# ---- Scene Transition ----
_scene_transition = get_scene_transition()

# ---- Audio Layering ----
_audio_layering = get_audio_layering()

# ---- Experiment Framework ----
_experiment_framework = get_experiment_framework()

# ---- Telemetry Pipeline ----
_telemetry_pipeline = get_telemetry_pipeline()

# ---- Audit Trail ----
_audit_trail = get_audit_trail()

# ---- Journal System ----
_journal_system = get_journal_system()

# ---- Document Synthesizer ----
_document_synthesizer = get_document_synthesizer()

# ---- Simulation Runner ----
_simulation_runner = get_simulation_runner()

# ---- Material Graph ----
_material_graph = get_material_graph()

# ---- Occlusion Culling ----
_occlusion_culling = get_occlusion_culling()

# ---- LOD System ----
_lod_system = get_lod_system()

# ---- Decal System ----
_decal_system = get_decal_system()

# ---- Post Processing ----
_post_processing_engine = get_post_processing()

# ---- Skeleton Deformer ----
_skeleton_deformer = get_skeleton_deformer()
_agentic_coding = get_agentic_coding()
_game_reasoner = get_game_reasoner()
_narrative_branch = get_narrative_branch()
_concurrency_manager = get_concurrency_manager()
_verification_pipeline = get_verification_pipeline()
_playtest_simulator = get_playtest_simulator()
_lighting_2d = get_lighting_2d()
_parallax_background = get_parallax_background()
_behavior_library = get_behavior_library()
_animation_curve = get_animation_curve()
_render_layer = get_render_layer()
_state_synchronizer = get_state_synchronizer()
_SKILL_SYNTHESIZER = get_skill_synthesizer()
_SECURITY_SCANNER = get_security_scanner()
_DELEGATION_FRAMEWORK = get_delegation_framework()
_KANBAN_COORDINATOR = get_kanban_coordinator()
_STREAMING_SCRUBBER = get_streaming_scrubber()
_TRAJECTORY_GENERATOR = get_trajectory_generator()
_VISUAL_SCRIPT_RUNTIME = get_visual_script_runtime()
_EXTENSION_SDK = get_extension_sdk()
_SIGNAL_BUS = get_signal_bus()
_PREFAB_COMPOSER = get_prefab_composer()
_INTERACTIVE_AUDIO = get_interactive_audio()
_IMPORT_PIPELINE = get_import_pipeline()

_skill_synthesizer = get_skill_synthesizer()
_security_scanner = get_security_scanner()
_delegation_framework = get_delegation_framework()
_kanban_coordinator = get_kanban_coordinator()
_streaming_scrubber = get_streaming_scrubber()
_trajectory_generator = get_trajectory_generator()
_visual_script_runtime = get_visual_script_runtime()
_extension_sdk = get_extension_sdk()
_engine_signal_bus = get_signal_bus()
_prefab_composer = get_prefab_composer()
_interactive_audio = get_interactive_audio()
_engine_import_pipeline = get_import_pipeline()
_developer_oracle = get_developer_oracle()
_context_weaver = get_context_weaver()
_session_nexus = get_session_nexus()
_persona_vault = get_persona_vault()
_voice_bridge = get_voice_bridge()
_ecosystem_hub = get_ecosystem_hub()
_frame_composer = get_frame_composer()
_spatial_cluster = get_spatial_cluster()
_asset_streamer = get_asset_streamer()
_deterministic_replay = get_deterministic_replay()
_input_abstraction = get_input_abstraction()
_profile_loader = get_profile_loader()
_intent_cascade = get_intent_cascade()
_game_forecaster = get_game_forecaster()
_asset_synthesizer = get_asset_synthesizer()
_tutorial_orchestrator = get_tutorial_orchestrator()
_skybox_renderer = get_skybox_renderer()
_trail_renderer = get_trail_renderer()
_procedural_audio = get_procedural_audio()
_texture_atlas = get_texture_atlas()
_ab_test_runner = get_ab_test_runner()
_heatmap_analyzer = get_heatmap_analyzer()
_bug_forensics = get_bug_forensics()
_accessibility_auditor = get_accessibility_auditor()
_tile_brush = get_tile_brush()
_sprite_animator = get_sprite_animator()
_light_culling = get_light_culling()
_render_pass = get_render_pass()
_federated_learner = get_federated_learner()
_swarm_planner = get_swarm_planner()
_world_composer = get_world_composer()
_playtest_orchestrator = get_playtest_orchestrator()
_particle_emitter = get_particle_emitter()
_lod_gate = get_lod_gate()
_scene_stack = get_scene_stack()
_navmesh_forge = get_navmesh_forge()
_reasoning_chain = get_reasoning_chain()
_memory_hierarchy = get_memory_hierarchy()
_tool_registry = get_tool_registry()
_prompt_library = get_prompt_library()
_reflection_loop = get_reflection_loop()
_procedural_synthesis = get_procedural_synthesis()
_asset_bundler = get_asset_bundler()
_deterministic_recorder = get_deterministic_recorder()
_localization_hub = get_localization_hub()
_signal_bus: Any = None
_import_pipeline: Any = None


def _init_new_subsystems():
    from sparkai.agent.agent_game_director import get_game_director
    from sparkai.agent.agent_balance_analyzer import get_balance_analyzer
    from sparkai.agent.agent_narrative_composer import get_narrative_composer
    from sparkai.agent.agent_player_modeler import get_player_modeler
    from sparkai.engine.engine_audio_system import get_audio_system
    from sparkai.engine.engine_network_layer import get_network_layer
    from sparkai.engine.engine_behavior_runtime import get_behavior_runtime
    from sparkai.engine.engine_save_system import get_save_system
    from sparkai.engine.engine_node_tree import get_node_tree
    from sparkai.engine.engine_extension_registry import get_extension_registry
    from sparkai.engine.engine_export_pipeline import get_export_pipeline
    from sparkai.engine.engine_server_architecture import get_server_pool
    from sparkai.engine.engine_gizmo_system import get_gizmo_system
    from sparkai.engine.engine_pivot_system import get_pivot_system
    global _game_director, _balance_analyzer, _narrative_composer, _player_modeler
    global _audio_system, _network_layer, _behavior_runtime, _save_system
    global _node_tree, _extension_registry, _export_pipeline, _server_pool, _gizmo_system, _pivot_system
    global _learning_loop, _cron_scheduler, _memory_graph, _context_compressor, _tool_forge, _gateway
    _game_director = get_game_director()
    _balance_analyzer = get_balance_analyzer()
    _narrative_composer = get_narrative_composer()
    _player_modeler = get_player_modeler()
    _audio_system = get_audio_system()
    _network_layer = get_network_layer()
    _behavior_runtime = get_behavior_runtime()
    _save_system = get_save_system()
    _node_tree = get_node_tree()
    _extension_registry = get_extension_registry()
    _export_pipeline = get_export_pipeline()
    _server_pool = get_server_pool()
    _gizmo_system = get_gizmo_system()
    _pivot_system = get_pivot_system()
    from sparkai.agent.agent_learning_loop import get_learning_loop
    from sparkai.agent.agent_memory_graph import get_memory_graph
    from sparkai.agent.agent_context_compressor import get_context_compressor
    from sparkai.agent.agent_tool_forge import get_tool_forge
    from sparkai.agent.agent_gateway import get_gateway
    global _learning_loop, _cron_scheduler, _memory_graph, _context_compressor, _tool_forge, _gateway
    _learning_loop = get_learning_loop()
    _cron_scheduler = get_cron_scheduler()
    _memory_graph = get_memory_graph()
    _context_compressor = get_context_compressor()
    _tool_forge = get_tool_forge()
    _gateway = get_gateway()

    from sparkai.agent.agent_skill_synthesizer import get_skill_synthesizer
    from sparkai.agent.agent_security_scanner import get_security_scanner
    from sparkai.agent.agent_delegation_framework import get_delegation_framework
    from sparkai.agent.agent_kanban_coordinator import get_kanban_coordinator
    from sparkai.agent.agent_streaming_scrubber import get_streaming_scrubber
    from sparkai.agent.agent_trajectory_generator import get_trajectory_generator
    from sparkai.engine.engine_visual_script_runtime import get_visual_script_runtime
    from sparkai.engine.engine_extension_sdk import get_extension_sdk
    from sparkai.engine.engine_signal_bus import get_signal_bus
    from sparkai.engine.engine_prefab_composer import get_prefab_composer
    from sparkai.engine.engine_interactive_audio import get_interactive_audio
    from sparkai.engine.engine_import_pipeline import get_import_pipeline

    global _skill_synthesizer, _security_scanner, _delegation_framework
    global _kanban_coordinator, _streaming_scrubber, _trajectory_generator
    global _visual_script_runtime, _extension_sdk, _engine_signal_bus
    global _prefab_composer, _interactive_audio, _engine_import_pipeline
    _skill_synthesizer = get_skill_synthesizer()
    _security_scanner = get_security_scanner()
    _delegation_framework = get_delegation_framework()
    _kanban_coordinator = get_kanban_coordinator()
    _streaming_scrubber = get_streaming_scrubber()
    _trajectory_generator = get_trajectory_generator()
    _visual_script_runtime = get_visual_script_runtime()
    _extension_sdk = get_extension_sdk()
    _engine_signal_bus = get_signal_bus()
    _prefab_composer = get_prefab_composer()
    _interactive_audio = get_interactive_audio()
    _engine_import_pipeline = get_import_pipeline()


# === Blueprint Engine ===

@router.post("/blueprints/create")
async def blueprint_create(name: str, genre: str = "", tagline: str = "", description: str = "", target_audience: str = "", platform: str = "web"):
    bp = _blueprint_engine.create_blueprint(name, genre, tagline, description, target_audience, platform)
    return bp.to_dict()

@router.get("/blueprints/list")
async def blueprint_list(state: Optional[str] = None):
    st = BlueprintState(state) if state else None
    return {"blueprints": _blueprint_engine.list_blueprints(st)}

@router.get("/blueprints/stats")
async def blueprint_stats():
    return _blueprint_engine.get_stats()

@router.get("/blueprints/{blueprint_id}")
async def blueprint_get(blueprint_id: str):
    bp = _blueprint_engine.get_blueprint(blueprint_id)
    if bp:
        return bp
    return {"error": f"Blueprint '{blueprint_id}' not found"}

@router.put("/blueprints/{blueprint_id}")
async def blueprint_update(blueprint_id: str, updates: Dict[str, Any]):
    result = _blueprint_engine.update_blueprint(blueprint_id, updates)
    if result:
        return result
    return {"error": f"Blueprint '{blueprint_id}' not found"}

@router.post("/blueprints/{blueprint_id}/core-loop")
async def blueprint_set_core_loop(blueprint_id: str, name: str, description: str = "", loop_frequency: str = "continuous"):
    result = _blueprint_engine.set_core_loop(blueprint_id, name, description, [], loop_frequency)
    if result:
        return result
    return {"error": f"Blueprint '{blueprint_id}' not found"}

@router.post("/blueprints/{blueprint_id}/mechanics")
async def blueprint_add_mechanic(blueprint_id: str, name: str, mechanic_type: str = "custom", description: str = "", player_input: str = "", system_output: str = "", priority: int = 2, complexity: str = "medium"):
    result = _blueprint_engine.add_mechanic(blueprint_id, name, mechanic_type, description, player_input, system_output, {}, [], priority, complexity)
    if result:
        return result
    return {"error": f"Blueprint '{blueprint_id}' not found"}

@router.delete("/blueprints/{blueprint_id}/mechanics/{mechanic_id}")
async def blueprint_remove_mechanic(blueprint_id: str, mechanic_id: str):
    result = _blueprint_engine.remove_mechanic(blueprint_id, mechanic_id)
    if result:
        return result
    return {"error": "Not found"}

@router.post("/blueprints/{blueprint_id}/progression")
async def blueprint_set_progression(blueprint_id: str, name: str, progression_type: str = "linear", description: str = "", difficulty_curve: str = "gradual"):
    result = _blueprint_engine.set_progression(blueprint_id, name, progression_type, description, [], difficulty_curve)
    if result:
        return result
    return {"error": f"Blueprint '{blueprint_id}' not found"}

@router.post("/blueprints/{blueprint_id}/aesthetic")
async def blueprint_set_aesthetic(blueprint_id: str, name: str, audio_style: str = "", ui_style: str = ""):
    result = _blueprint_engine.set_aesthetic(blueprint_id, name, [], [], [], audio_style, ui_style)
    if result:
        return result
    return {"error": f"Blueprint '{blueprint_id}' not found"}

@router.post("/blueprints/{blueprint_id}/transition")
async def blueprint_transition(blueprint_id: str, state: str):
    result = _blueprint_engine.transition_state(blueprint_id, state)
    if result:
        return result
    return {"error": f"Blueprint '{blueprint_id}' not found"}

@router.get("/blueprints/{blueprint_id}/revisions")
async def blueprint_revisions(blueprint_id: str):
    return {"revisions": _blueprint_engine.get_revisions(blueprint_id)}


# === Playtest Engine ===

@router.get("/playtest/scenarios")
async def playtest_scenarios(scenario_type: Optional[str] = None):
    st = ScenarioType(scenario_type) if scenario_type else None
    return {"scenarios": _playtest_engine.list_scenarios(st)}

@router.post("/playtest/scenarios/create")
async def playtest_scenario_create(name: str, scenario_type: str = "custom", description: str = "", timeout_seconds: float = 60.0):
    scenario = _playtest_engine.create_scenario(name, scenario_type, description, [], timeout_seconds)
    return scenario.to_dict()

@router.post("/playtest/run")
async def playtest_run(build_id: str, build_url: str = ""):
    session = _playtest_engine.run_session(build_id, build_url)
    return session.to_dict()

@router.get("/playtest/sessions")
async def playtest_sessions(limit: int = 20):
    return {"sessions": _playtest_engine.list_sessions(limit)}

@router.get("/playtest/sessions/{session_id}")
async def playtest_session_get(session_id: str):
    session = _playtest_engine.get_session(session_id)
    if session:
        return session
    return {"error": f"Session '{session_id}' not found"}

@router.get("/playtest/stats")
async def playtest_stats():
    return _playtest_engine.get_stats()


# === Composer Engine ===

@router.post("/compositions/create")
async def composition_create(name: str, description: str = "", objective: str = ""):
    comp = _composer_engine.create_composition(name, description, objective)
    return comp.to_dict()

@router.get("/compositions/list")
async def composition_list(state: Optional[str] = None):
    st = CompositionState(state) if state else None
    return {"compositions": _composer_engine.list_compositions(st)}

@router.get("/compositions/stats")
async def composition_stats():
    return _composer_engine.get_stats()

@router.get("/compositions/{composition_id}")
async def composition_get(composition_id: str):
    comp = _composer_engine.get_composition(composition_id)
    if comp:
        return comp
    return {"error": f"Composition '{composition_id}' not found"}

@router.post("/compositions/{composition_id}/tasks")
async def composition_add_task(composition_id: str, name: str, task_type: str = "code", description: str = "", agent_role: str = "", priority: int = 2, estimated_duration_ms: float = 0.0):
    result = _composer_engine.add_task(composition_id, name, task_type, description, agent_role, [], {}, {}, priority, estimated_duration_ms)
    if result:
        return result
    return {"error": f"Composition '{composition_id}' not found"}

@router.post("/compositions/{composition_id}/channels")
async def composition_add_channel(composition_id: str, name: str, source_task: str, source_output: str, target_task: str, target_input: str, data_type: str = "any"):
    result = _composer_engine.add_channel(composition_id, name, source_task, source_output, target_task, target_input, data_type)
    if result:
        return result
    return {"error": f"Composition '{composition_id}' not found"}

@router.post("/compositions/{composition_id}/plan")
async def composition_plan(composition_id: str):
    result = _composer_engine.plan(composition_id)
    if result:
        return result
    return {"error": "Plan failed"}

@router.post("/compositions/{composition_id}/execute")
async def composition_execute(composition_id: str):
    result = _composer_engine.execute(composition_id)
    if result:
        return result
    return {"error": "Execution failed"}

@router.get("/swarm/topology")
async def swarm_topology():
    return _agent_swarm.get_topology()

@router.get("/swarm/stats")
async def swarm_stats():
    return _agent_swarm.get_stats()

@router.get("/swarm/nodes")
async def swarm_nodes(role: Optional[str] = None):
    r = SwarmRole(role) if role else None
    return {"nodes": _agent_swarm.list_nodes(r)}

@router.get("/swarm/nodes/{node_id}")
async def swarm_node_get(node_id: str):
    node = _agent_swarm.get_node(node_id)
    if node:
        return node
    return {"error": f"Node '{node_id}' not found"}

@router.post("/swarm/register")
async def swarm_register(agent_id: str, name: str = "", role: str = "worker", capabilities: Optional[str] = None, capacity: int = 5):
    r = SwarmRole(role)
    caps = capabilities.split(",") if capabilities else []
    node = _agent_swarm.register_node(agent_id, name, r, caps, capacity)
    return node.to_dict()

@router.post("/swarm/decompose")
async def swarm_decompose(title: str, description: str = "", capabilities: Optional[str] = None, strategy: Optional[str] = None):
    caps = capabilities.split(",") if capabilities else []
    strat = DecompositionStrategy(strategy) if strategy else None
    tasks = _agent_swarm.decompose_task(title, description, caps, strat)
    return {"tasks": [t.to_dict() for t in tasks]}

@router.post("/swarm/dispatch/{task_id}")
async def swarm_dispatch(task_id: str):
    node_id = _agent_swarm.dispatch_task(task_id)
    if node_id:
        return {"assigned_to": node_id, "task_id": task_id}
    return {"error": "No available node or task not found"}

@router.post("/swarm/complete/{task_id}")
async def swarm_complete(task_id: str, success: bool = True):
    result = _agent_swarm.complete_task(task_id, success=success)
    return {"completed": result, "task_id": task_id}

@router.post("/swarm/consensus")
async def swarm_consensus(proposal_id: str, voters: str = ""):
    voter_list = voters.split(",") if voters else []
    result = _agent_swarm.propose_consensus(proposal_id, voter_list)
    return result.to_dict()

@router.get("/swarm/knowledge/{key}")
async def swarm_knowledge_get(key: str):
    entry = _agent_swarm.retrieve_knowledge(key)
    if entry:
        return entry
    return {"error": f"Key '{key}' not found"}

@router.post("/swarm/knowledge")
async def swarm_knowledge_store(key: str, value: str, contributor: str, confidence: float = 1.0):
    return _agent_swarm.store_knowledge(key, value, contributor, confidence)

@router.get("/swarm/history")
async def swarm_history(limit: int = 20):
    return {"entries": _agent_swarm.get_history(limit)}


# === Studio Commands ===

@router.get("/commands/list")
async def commands_list(category: Optional[str] = None, tag: Optional[str] = None):
    cat = CommandCategory(category) if category else None
    return {"commands": _studio_command_system.list_commands(cat, tag)}

@router.get("/commands/search")
async def commands_search(q: str = ""):
    return {"commands": _studio_command_system.find_command(q)}

@router.get("/commands/categories")
async def commands_categories():
    return {"categories": _studio_command_system.list_categories()}

@router.get("/commands/stats")
async def commands_stats():
    return _studio_command_system.get_stats()

@router.get("/commands/executions/{execution_id}")
async def commands_execution_get(execution_id: str):
    execution = _studio_command_system.get_execution(execution_id)
    if execution:
        return execution
    return {"error": f"Execution '{execution_id}' not found"}

@router.get("/commands/{slash:path}")
async def commands_get(slash: str):
    cmd = _studio_command_system.get_command(slash)
    if cmd:
        return cmd
    return {"error": f"Command '{slash}' not found"}

@router.post("/commands/execute")
async def commands_execute(slash: str):
    execution = _studio_command_system.execute_command(slash, {})
    return execution.to_dict()


# === Game Templates ===

@router.get("/templates/list")
async def templates_list(genre: Optional[str] = None):
    g = GameGenre(genre) if genre else None
    return {"templates": _game_template_library.list_templates(g)}

@router.get("/templates/genres")
async def templates_genres():
    return {"genres": _game_template_library.list_genres()}

@router.get("/templates/stats")
async def templates_stats():
    return _game_template_library.get_stats()

@router.post("/templates/scaffold")
async def templates_scaffold(project_name: str, genre: str):
    result = _game_template_library.scaffold(project_name, genre)
    return result.to_dict()

@router.get("/templates/{template_id}")
async def templates_get(template_id: str):
    template = _game_template_library.get_template(template_id)
    if template:
        return template
    return {"error": f"Template '{template_id}' not found"}


@router.get("/studio/hierarchy")
async def studio_hierarchy():
    return _studio_coordinator.get_hierarchy()


@router.get("/studio/department/{department}")
async def studio_department(department: str):
    return {"agents": _studio_coordinator.get_department_agents(department)}


@router.post("/studio/assign-task")
async def studio_assign_task(title: str = "", department: str = "programming", capabilities: Optional[str] = None, priority: int = 2, description: str = ""):
    caps = capabilities.split(",") if capabilities else []
    task_id = _studio_coordinator.assign_task(title, department, caps, priority, description)
    if task_id:
        return {"task_id": task_id}
    return {"error": "Failed to assign task"}


@router.post("/studio/complete-task/{task_id}")
async def studio_complete_task(task_id: str):
    if _studio_coordinator.complete_task(task_id):
        return {"status": "completed"}
    return {"error": "Task not found"}


@router.get("/studio/tasks")
async def studio_tasks(status: Optional[str] = None, department: Optional[str] = None):
    return {"tasks": _studio_coordinator.list_tasks(status, department)}


@router.get("/studio/agent/{agent_id}")
async def studio_agent(agent_id: str):
    agent = _studio_coordinator.get_agent(agent_id)
    if agent:
        return agent
    return {"error": f"Agent '{agent_id}' not found"}


@router.get("/studio/coordination-log")
async def studio_coordination_log(limit: int = 20):
    return {"entries": _studio_coordinator.get_coordination_log(limit)}


@router.get("/studio/stats")
async def studio_stats():
    return _studio_coordinator.get_stats()


# === Knowledge Graph ===

_knowledge_graph = get_knowledge_graph()
_toolchain_engine = get_toolchain_engine()
_reflex_engine = get_reflex_engine()


@router.get("/knowledge/nodes")
async def knowledge_nodes(domain: Optional[str] = None, confidence: Optional[str] = None, tags: Optional[str] = None, limit: int = 50):
    dom = KnowledgeDomain(domain) if domain else None
    conf = NodeConfidence(confidence) if confidence else None
    tag_list = tags.split(",") if tags else None
    return {"nodes": _knowledge_graph.list_nodes(dom, conf, tag_list, limit)}

@router.post("/knowledge/nodes")
async def knowledge_add_node(title: str, domain: str = "game_design", confidence: str = "experimental", content: str = "", tags: Optional[str] = None, source: str = ""):
    tag_list = tags.split(",") if tags else []
    node = _knowledge_graph.add_node(title, domain, confidence, content, tag_list, source)
    return node.to_dict()

@router.get("/knowledge/nodes/{node_id}")
async def knowledge_get_node(node_id: str):
    result = _knowledge_graph.get_node(node_id)
    if result:
        return result
    return {"error": f"Node '{node_id}' not found"}

@router.put("/knowledge/nodes/{node_id}")
async def knowledge_update_node(node_id: str, updates: Dict[str, Any]):
    result = _knowledge_graph.update_node(node_id, updates)
    if result:
        return result
    return {"error": f"Node '{node_id}' not found"}

@router.delete("/knowledge/nodes/{node_id}")
async def knowledge_remove_node(node_id: str):
    success = _knowledge_graph.remove_node(node_id)
    return {"success": success}

@router.get("/knowledge/nodes/{node_id}/related")
async def knowledge_related(node_id: str, max_depth: int = 2, relation_types: Optional[str] = None):
    rtypes = relation_types.split(",") if relation_types else None
    return {"related": _knowledge_graph.get_related(node_id, max_depth, rtypes)}

@router.get("/knowledge/relations")
async def knowledge_relations(source_id: Optional[str] = None, target_id: Optional[str] = None, relation_type: Optional[str] = None):
    rt = RelationType(relation_type) if relation_type else None
    return {"relations": _knowledge_graph.list_relations(source_id, target_id, rt)}

@router.post("/knowledge/relations")
async def knowledge_add_relation(source_id: str, target_id: str, relation_type: str = "depends_on", weight: float = 1.0, description: str = "", bidirectional: bool = False):
    relation = _knowledge_graph.add_relation(source_id, target_id, relation_type, weight, description, bidirectional)
    if relation:
        return relation.to_dict()
    return {"error": "Source or target node not found"}

@router.get("/knowledge/search")
async def knowledge_search(q: str, domain: Optional[str] = None, min_confidence: Optional[str] = None, tags: Optional[str] = None, limit: int = 10):
    tag_list = tags.split(",") if tags else None
    return {"results": _knowledge_graph.search(q, domain, min_confidence, tag_list, limit)}

@router.post("/knowledge/inference")
async def knowledge_inference(method: str = "all"):
    return {"inferences": _knowledge_graph.run_inference(method)}

@router.get("/knowledge/patterns")
async def knowledge_patterns(category: Optional[str] = None, genre: Optional[str] = None):
    cat = PatternCategory(category) if category else None
    return {"patterns": _knowledge_graph.list_patterns(cat, genre)}

@router.get("/knowledge/patterns/find")
async def knowledge_find_pattern(problem: str):
    return {"patterns": _knowledge_graph.find_patterns_for_problem(problem)}

@router.get("/knowledge/patterns/{pattern_id}")
async def knowledge_get_pattern(pattern_id: str):
    result = _knowledge_graph.get_pattern(pattern_id)
    if result:
        return result
    return {"error": f"Pattern '{pattern_id}' not found"}

@router.get("/knowledge/stats")
async def knowledge_stats():
    return _knowledge_graph.get_graph_stats()


# === Tool Chain Engine ===

@router.post("/toolchain/chains")
async def toolchain_create_chain(name: str = "", description: str = ""):
    chain = _toolchain_engine.create_chain(name, description)
    return chain.to_dict()

@router.get("/toolchain/chains")
async def toolchain_list_chains(status: Optional[str] = None):
    st = ChainStatus(status) if status else None
    return {"chains": _toolchain_engine.list_chains(st)}

@router.get("/toolchain/chains/{chain_id}")
async def toolchain_get_chain(chain_id: str):
    result = _toolchain_engine.get_chain(chain_id)
    if result:
        return result
    return {"error": f"Chain '{chain_id}' not found"}

@router.delete("/toolchain/chains/{chain_id}")
async def toolchain_delete_chain(chain_id: str):
    success = _toolchain_engine.delete_chain(chain_id)
    return {"success": success}

@router.post("/toolchain/chains/{chain_id}/steps")
async def toolchain_add_step(chain_id: str, name: str = "", step_type: str = "tool", tool_name: str = "", output_key: str = "", depends_on: Optional[str] = None, max_retries: int = 3, timeout_ms: float = 30000.0):
    deps = depends_on.split(",") if depends_on else []
    result = _toolchain_engine.add_step(chain_id, name, step_type, tool_name, {}, {}, output_key, deps, None, max_retries, timeout_ms)
    if result:
        return result
    return {"error": f"Chain '{chain_id}' not found"}

@router.delete("/toolchain/chains/{chain_id}/steps/{step_id}")
async def toolchain_remove_step(chain_id: str, step_id: str):
    success = _toolchain_engine.remove_step(chain_id, step_id)
    return {"success": success}

@router.post("/toolchain/chains/{chain_id}/resolve")
async def toolchain_resolve_chain(chain_id: str):
    result = _toolchain_engine.resolve_chain(chain_id)
    if result:
        return result
    return {"error": f"Chain '{chain_id}' not found"}

@router.post("/toolchain/chains/{chain_id}/execute")
async def toolchain_execute_chain(chain_id: str):
    result = await _toolchain_engine.execute_chain(chain_id)
    if result:
        return result
    return {"error": f"Chain '{chain_id}' not found"}

@router.post("/toolchain/chains/{chain_id}/cancel")
async def toolchain_cancel_chain(chain_id: str):
    success = _toolchain_engine.cancel_chain(chain_id)
    return {"success": success}

@router.get("/toolchain/templates")
async def toolchain_list_templates(category: Optional[str] = None):
    cat = TemplateCategory(category) if category else None
    return {"templates": _toolchain_engine.list_templates(cat)}

@router.get("/toolchain/templates/{template_id}")
async def toolchain_get_template(template_id: str):
    result = _toolchain_engine.get_template(template_id)
    if result:
        return result
    return {"error": f"Template '{template_id}' not found"}

@router.post("/toolchain/templates/{template_id}/create")
async def toolchain_create_from_template(template_id: str, name: str = ""):
    chain = _toolchain_engine.create_from_template(template_id, name)
    if chain:
        return chain.to_dict()
    return {"error": f"Template '{template_id}' not found"}

@router.get("/toolchain/stats")
async def toolchain_stats():
    return _toolchain_engine.get_stats()


# === Reflex Engine ===

@router.post("/reflex/metrics")
async def reflex_record_metric(metric_type: str, subsystem: str, value: float, unit: str = ""):
    sample = _reflex_engine.record_metric(metric_type, subsystem, value, unit)
    return sample

@router.get("/reflex/metrics/stats")
async def reflex_metric_stats(subsystem: str, metric_type: str):
    return _reflex_engine.get_metric_stats(subsystem, metric_type)

@router.get("/reflex/metrics/history")
async def reflex_metric_history(subsystem: str, metric_type: str, count: int = 20):
    return {"samples": _reflex_engine.get_metric_history(subsystem, metric_type, count)}

@router.get("/reflex/subsystems")
async def reflex_subsystems():
    return {"subsystems": _reflex_engine.list_subsystems()}

@router.post("/reflex/analysis")
async def reflex_run_analysis(subsystem: Optional[str] = None):
    return _reflex_engine.run_analysis(subsystem)

@router.post("/reflex/suggestions/{suggestion_id}/apply")
async def reflex_apply_suggestion(suggestion_id: str, current_params: Optional[Dict[str, Any]] = None):
    result = _reflex_engine.apply_suggestion(suggestion_id, current_params)
    if result:
        return result
    return {"error": f"Suggestion '{suggestion_id}' not found"}

@router.get("/reflex/anomalies")
async def reflex_anomalies(severity: Optional[str] = None, limit: int = 20):
    sev = SeverityLevel(severity) if severity else None
    return {"anomalies": _reflex_engine.get_anomalies(sev, limit)}

@router.get("/reflex/suggestions")
async def reflex_suggestions(limit: int = 20):
    return {"suggestions": _reflex_engine.get_suggestions(limit)}

@router.get("/reflex/adjustments")
async def reflex_adjustments(limit: int = 20):
    return {"adjustments": _reflex_engine.get_adjustments(limit)}

@router.get("/reflex/reports")
async def reflex_reports(limit: int = 10):
    return {"reports": _reflex_engine.get_reports(limit)}

@router.get("/reflex/stats")
async def reflex_stats():
    return _reflex_engine.get_stats()


# === Dialogue Engine ===

_dialogue_engine = get_dialogue_engine()
_asset_engine = get_asset_engine()
_validator_engine = get_validator_engine()
_orchestrator_engine = get_orchestrator_engine()
_skill_evolution_engine = get_skill_evolution_engine()
_evaluator_engine = get_game_evaluator()


@router.get("/dialogue/trees")
async def dialogue_trees(dialogue_type: Optional[str] = None, npc_name: Optional[str] = None):
    dt = DialogueType(dialogue_type) if dialogue_type else None
    return {"trees": _dialogue_engine.list_trees(dt, npc_name)}

@router.post("/dialogue/trees")
async def dialogue_create_tree(name: str = "", dialogue_type: str = "random", npc_name: str = "", description: str = ""):
    tree = _dialogue_engine.create_tree(name, dialogue_type, npc_name, description)
    return tree.to_dict()

@router.get("/dialogue/trees/{tree_id}")
async def dialogue_get_tree(tree_id: str):
    result = _dialogue_engine.get_tree(tree_id)
    if result:
        return result
    return {"error": f"Tree '{tree_id}' not found"}

@router.delete("/dialogue/trees/{tree_id}")
async def dialogue_delete_tree(tree_id: str):
    success = _dialogue_engine.delete_tree(tree_id)
    return {"success": success}

@router.post("/dialogue/trees/{tree_id}/nodes")
async def dialogue_add_node(tree_id: str, node_type: str = "speech", speaker: str = "", text: str = "", mood: str = "neutral", next_node_id: str = "", position_x: float = 0.0, position_y: float = 0.0):
    result = _dialogue_engine.add_node(tree_id, node_type, speaker, text, mood, next_node_id, position_x, position_y)
    if result:
        return result
    return {"error": f"Tree '{tree_id}' not found"}

@router.put("/dialogue/trees/{tree_id}/nodes/{node_id}")
async def dialogue_update_node(tree_id: str, node_id: str, updates: Dict[str, Any]):
    result = _dialogue_engine.update_node(tree_id, node_id, updates)
    if result:
        return result
    return {"error": "Node not found"}

@router.delete("/dialogue/trees/{tree_id}/nodes/{node_id}")
async def dialogue_remove_node(tree_id: str, node_id: str):
    success = _dialogue_engine.remove_node(tree_id, node_id)
    return {"success": success}

@router.post("/dialogue/trees/{tree_id}/choices")
async def dialogue_add_choice(tree_id: str, node_id: str, text: str, next_node_id: str = "", priority: int = 0, once: bool = False):
    result = _dialogue_engine.add_choice(tree_id, node_id, text, next_node_id, priority, once)
    if result:
        return result
    return {"error": "Node not found"}

@router.delete("/dialogue/trees/{tree_id}/choices/{choice_id}")
async def dialogue_remove_choice(tree_id: str, node_id: str, choice_id: str):
    success = _dialogue_engine.remove_choice(tree_id, node_id, choice_id)
    return {"success": success}

@router.post("/dialogue/trees/{tree_id}/advance")
async def dialogue_advance(tree_id: str, choice_id: Optional[str] = None):
    result = _dialogue_engine.advance_dialogue(tree_id, choice_id)
    if result:
        return result
    return {"error": f"Tree '{tree_id}' not found"}

@router.post("/dialogue/trees/{tree_id}/reset")
async def dialogue_reset(tree_id: str):
    success = _dialogue_engine.reset_dialogue(tree_id)
    return {"success": success}

@router.get("/dialogue/arcs")
async def dialogue_arcs(status: Optional[str] = None):
    st = ArcStatus(status) if status else None
    return {"arcs": _dialogue_engine.list_arcs(st)}

@router.post("/dialogue/arcs")
async def dialogue_create_arc(name: str, description: str = "", priority: int = 2):
    arc = _dialogue_engine.create_arc(name, description, priority)
    return arc.to_dict()

@router.put("/dialogue/arcs/{arc_id}/status")
async def dialogue_update_arc_status(arc_id: str, status: str):
    result = _dialogue_engine.update_arc_status(arc_id, status)
    if result:
        return result
    return {"error": f"Arc '{arc_id}' not found"}

@router.get("/dialogue/stats")
async def dialogue_stats():
    return _dialogue_engine.get_stats()


# === Asset Pipeline Engine ===

@router.get("/assets")
async def asset_list(category: Optional[str] = None, status: Optional[str] = None, tags: Optional[str] = None, limit: int = 50):
    cat = AssetCategory(category) if category else None
    st = AssetStatus(status) if status else None
    tag_list = tags.split(",") if tags else None
    return {"assets": _asset_engine.list_assets(cat, st, tag_list, limit)}

@router.post("/assets")
async def asset_register(name: str, category: str = "sprite", format: str = "png", path: str = "", size_bytes: int = 0, width: int = 0, height: int = 0, tags: Optional[str] = None):
    tag_list = tags.split(",") if tags else []
    asset = _asset_engine.register_asset(name, category, format, path, size_bytes, width, height, tag_list)
    return asset.to_dict()

@router.get("/assets/search")
async def asset_search(q: str, limit: int = 20):
    return {"assets": _asset_engine.search_assets(q, limit)}

@router.get("/assets/{asset_id}")
async def asset_get(asset_id: str):
    result = _asset_engine.get_asset(asset_id)
    if result:
        return result
    return {"error": f"Asset '{asset_id}' not found"}

@router.put("/assets/{asset_id}")
async def asset_update(asset_id: str, updates: Dict[str, Any]):
    result = _asset_engine.update_asset(asset_id, updates)
    if result:
        return result
    return {"error": f"Asset '{asset_id}' not found"}

@router.delete("/assets/{asset_id}")
async def asset_remove(asset_id: str):
    success = _asset_engine.remove_asset(asset_id)
    return {"success": success}

@router.get("/assets/{asset_id}/dependencies")
async def asset_dependencies(asset_id: str):
    return _asset_engine.get_dependencies(asset_id)

@router.post("/assets/{asset_id}/dependencies")
async def asset_add_dependency(asset_id: str, depends_on_id: str):
    success = _asset_engine.add_dependency(asset_id, depends_on_id)
    return {"success": success}

@router.get("/asset-collections")
async def asset_collections():
    return {"collections": _asset_engine.list_collections()}

@router.post("/asset-collections")
async def asset_create_collection(name: str, description: str = "", tags: Optional[str] = None):
    tag_list = tags.split(",") if tags else []
    collection = _asset_engine.create_collection(name, description, [], tag_list)
    return collection.to_dict()

@router.get("/asset-collections/{collection_id}")
async def asset_get_collection(collection_id: str):
    result = _asset_engine.get_collection(collection_id)
    if result:
        return result
    return {"error": f"Collection '{collection_id}' not found"}

@router.post("/asset-collections/{collection_id}/assets/{asset_id}")
async def asset_add_to_collection(collection_id: str, asset_id: str):
    success = _asset_engine.add_to_collection(collection_id, asset_id)
    return {"success": success}

@router.delete("/asset-collections/{collection_id}/assets/{asset_id}")
async def asset_remove_from_collection(collection_id: str, asset_id: str):
    success = _asset_engine.remove_from_collection(collection_id, asset_id)
    return {"success": success}

@router.get("/asset-pipelines")
async def asset_pipelines():
    return {"pipelines": _asset_engine.list_pipelines()}

@router.post("/asset-pipelines")
async def asset_create_pipeline(name: str, description: str = ""):
    pipeline = _asset_engine.create_pipeline(name, description)
    return pipeline.to_dict()

@router.get("/asset-pipelines/{pipeline_id}")
async def asset_get_pipeline(pipeline_id: str):
    result = _asset_engine.get_pipeline(pipeline_id)
    if result:
        return result
    return {"error": f"Pipeline '{pipeline_id}' not found"}

@router.post("/asset-pipelines/{pipeline_id}/execute")
async def asset_execute_pipeline(pipeline_id: str):
    result = _asset_engine.execute_pipeline(pipeline_id)
    if result:
        return result
    return {"error": f"Pipeline '{pipeline_id}' not found"}

@router.get("/asset-stats")
async def asset_stats():
    return _asset_engine.get_stats()


# === Validator Engine ===

@router.get("/validator/rules")
async def validator_rules(category: Optional[str] = None, enabled_only: bool = False):
    cat = ValidationCategory(category) if category else None
    return {"rules": _validator_engine.list_rules(cat, enabled_only)}

@router.get("/validator/rules/{rule_id}")
async def validator_get_rule(rule_id: str):
    result = _validator_engine.get_rule(rule_id)
    if result:
        return result
    return {"error": f"Rule '{rule_id}' not found"}

@router.post("/validator/rules")
async def validator_add_rule(name: str, description: str = "", category: str = "code_style", severity: str = "warning", scope: str = "global", pattern: str = "", auto_fixable: bool = False):
    rule = _validator_engine.add_rule(name, description, category, severity, scope, pattern, auto_fixable)
    return rule.to_dict()

@router.put("/validator/rules/{rule_id}/toggle")
async def validator_toggle_rule(rule_id: str, enabled: bool = True):
    success = _validator_engine.toggle_rule(rule_id, enabled)
    return {"success": success}

@router.post("/validator/validate/code")
async def validator_validate_code(content: str, file_path: str = ""):
    report = _validator_engine.validate_code(content, file_path)
    return report.to_dict()

@router.post("/validator/validate/asset")
async def validator_validate_asset(asset_data: Dict[str, Any]):
    report = _validator_engine.validate_asset(asset_data)
    return report.to_dict()

@router.post("/validator/reports/{report_id}/auto-fix")
async def validator_auto_fix(report_id: str, content: str = ""):
    result = _validator_engine.auto_fix(report_id, content)
    if result:
        return result
    return {"error": f"Report '{report_id}' not found"}

@router.get("/validator/reports")
async def validator_reports(limit: int = 20):
    return {"reports": _validator_engine.get_reports(limit)}

@router.get("/validator/reports/{report_id}")
async def validator_get_report(report_id: str):
    result = _validator_engine.get_report(report_id)
    if result:
        return result
    return {"error": f"Report '{report_id}' not found"}

@router.get("/validator/rulesets")
async def validator_rulesets():
    return {"rulesets": _validator_engine.list_rule_sets()}

@router.get("/validator/stats")
async def validator_stats():
    return _validator_engine.get_stats()


# === Orchestrator Engine ===

@router.post("/orchestrator-engine/agents")
async def orchestrator_engine_register_agent(name: str, role: str = "specialist", capabilities: Optional[str] = None, max_concurrent_tasks: int = 3, specializations: Optional[str] = None):
    caps = capabilities.split(",") if capabilities else None
    specs = specializations.split(",") if specializations else None
    result = _orchestrator_engine.register_agent(name, role, caps, max_concurrent_tasks, specs)
    return result.to_dict()

@router.get("/orchestrator-engine/agents/{agent_id}")
async def orchestrator_engine_get_agent(agent_id: str):
    result = _orchestrator_engine.get_agent(agent_id)
    if result:
        return result
    return {"error": f"Agent '{agent_id}' not found"}

@router.delete("/orchestrator-engine/agents/{agent_id}")
async def orchestrator_engine_unregister_agent(agent_id: str):
    success = _orchestrator_engine.unregister_agent(agent_id)
    return {"success": success}

@router.post("/orchestrator-engine/tasks")
async def orchestrator_engine_submit_task(name: str, description: str = "", priority: str = "normal", required_capabilities: Optional[str] = None, preferred_agent: Optional[str] = None):
    caps = required_capabilities.split(",") if required_capabilities else None
    result = _orchestrator_engine.submit_task(name, description, caps, priority)
    return result.to_dict()

@router.get("/orchestrator-engine/tasks/{task_id}")
async def orchestrator_engine_get_task(task_id: str):
    result = _orchestrator_engine.get_task(task_id)
    if result:
        return result
    return {"error": f"Task '{task_id}' not found"}

@router.post("/orchestrator-engine/workflows")
async def orchestrator_engine_create_workflow(name: str, description: str = ""):
    result = _orchestrator_engine.create_workflow(name, description)
    return result.to_dict()

@router.get("/orchestrator-engine/workflows/{workflow_id}")
async def orchestrator_engine_get_workflow(workflow_id: str):
    result = _orchestrator_engine.get_workflow(workflow_id)
    if result:
        return result
    return {"error": f"Workflow '{workflow_id}' not found"}

@router.post("/orchestrator-engine/workflows/{workflow_id}/execute")
async def orchestrator_engine_execute_workflow(workflow_id: str):
    result = _orchestrator_engine.execute_workflow(workflow_id)
    if result:
        return result
    return {"error": f"Workflow '{workflow_id}' not found"}


# === Skill Evolution Engine ===

@router.post("/skill-evolution/skills")
async def skill_evolution_create_skill(name: str, domain: str = "code_gen", description: str = "", pattern: str = ""):
    result = _skill_evolution_engine.create_skill(name, domain, description, pattern)
    return result.to_dict()

@router.get("/skill-evolution/skills/{skill_id}")
async def skill_evolution_get_skill(skill_id: str):
    result = _skill_evolution_engine.get_skill(skill_id)
    if result:
        return result
    return {"error": f"Skill '{skill_id}' not found"}

@router.post("/skill-evolution/skills/{skill_id}/execute")
async def skill_evolution_record_execution(skill_id: str, outcome: str = "success", execution_time_ms: float = 0.0, error_message: Optional[str] = None, feedback: Optional[str] = None):
    result = _skill_evolution_engine.record_execution(skill_id, outcome, execution_time_ms, error_message or "", feedback or "")
    if result:
        return result
    return {"error": f"Skill '{skill_id}' not found"}

@router.post("/skill-evolution/protocols")
async def skill_evolution_create_protocol(name: str, error_pattern: str = "", fix_pattern: str = "", fix_description: str = ""):
    result = _skill_evolution_engine.create_protocol(name, error_pattern, fix_pattern, fix_description)
    return result.to_dict()

@router.get("/skill-evolution/protocols/{protocol_id}")
async def skill_evolution_get_protocol(protocol_id: str):
    result = _skill_evolution_engine.get_protocol(protocol_id)
    if result:
        return result
    return {"error": f"Protocol '{protocol_id}' not found"}

@router.get("/skill-evolution/protocols/find")
async def skill_evolution_find_protocol(error: str):
    return {"protocols": _skill_evolution_engine.find_protocol_for_error(error)}

@router.get("/skill-evolution/skills/{skill_id}/lineage")
async def skill_evolution_lineage(skill_id: str):
    return {"lineage": _skill_evolution_engine.get_skill_lineage(skill_id)}


# === Game Evaluator Engine ===

@router.post("/evaluator/evaluate")
async def evaluator_evaluate_game(game_id: str, game_name: str = "", prompt: str = ""):
    result = _evaluator_engine.evaluate_game(game_id, game_name, prompt)
    return result

@router.get("/evaluator/reports/{report_id}")
async def evaluator_get_report(report_id: str):
    result = _evaluator_engine.get_report(report_id)
    if result:
        return result
    return {"error": f"Report '{report_id}' not found"}

@router.post("/evaluator/compare")
async def evaluator_compare_games(report_ids: str):
    ids = report_ids.split(",")
    result = _evaluator_engine.compare_games(ids)
    if result:
        return result
    return {"error": "Comparison failed"}


# === Agent Lifecycle Manager ===

from sparkai.agent.agent_lifecycle import AgentLifecycleManager, AgentBlueprint, LifecyclePhase, BlueprintTier
from sparkai.agent.agent_slash_commands import SlashCommandSystem, CommandCategory
from sparkai.agent.agent_validation_hooks import ValidationHooksSystem, HookPhase, HookSeverity

_lifecycle_manager = AgentLifecycleManager()
_slash_command_system = SlashCommandSystem()
_validation_hooks = ValidationHooksSystem()


class BlueprintCreateRequest(BaseModel):
    name: str
    tier: str = "specialist"
    description: str = ""
    system_prompt: str = ""
    capabilities: Optional[List[str]] = None
    max_replans: int = 2
    reflection_interval: int = 3


class SlashCommandExecuteRequest(BaseModel):
    command: str
    context: Optional[Dict[str, Any]] = None


class HookRuleCreateRequest(BaseModel):
    name: str
    description: str = ""
    phase: str = "pre_execute"
    severity: str = "medium"
    action: str = "continue"
    category: str = "general"
    enabled: bool = True


class LifecyclePlanRequest(BaseModel):
    agent_id: str
    goal: str
    max_replans: int = 2


class LifecycleVerifyRequest(BaseModel):
    agent_id: str
    criteria: List[Dict[str, Any]]
    results: Dict[str, List[Any]]


class HookEvaluateRequest(BaseModel):
    phase: str
    context: Dict[str, Any]


@router.get("/lifecycle/blueprints")
async def lifecycle_list_blueprints():
    return {"blueprints": _lifecycle_manager.list_blueprints()}

@router.post("/lifecycle/blueprints")
async def lifecycle_create_blueprint(req: BlueprintCreateRequest):
    bp = AgentBlueprint(
        name=req.name,
        tier=BlueprintTier(req.tier),
        description=req.description,
        system_prompt=req.system_prompt,
        capabilities=req.capabilities or [],
        max_replans=req.max_replans,
        reflection_interval=req.reflection_interval,
    )
    key = _lifecycle_manager.register_blueprint(bp)
    return {"id": key, "name": bp.name, "tier": bp.tier.value}

@router.post("/lifecycle/spawn")
async def lifecycle_spawn_agent(blueprint_name: str, overrides: Optional[Dict[str, Any]] = None):
    result = _lifecycle_manager.spawn_from_blueprint(blueprint_name, overrides)
    return result

@router.post("/lifecycle/plan")
async def lifecycle_create_plan(req: LifecyclePlanRequest):
    plan = _lifecycle_manager.create_plan(req.agent_id, req.goal, req.max_replans)
    return {"plan_id": plan.id, "goal": plan.goal, "max_replans": plan.max_replans}

@router.get("/lifecycle/plan/{agent_id}")
async def lifecycle_get_plan(agent_id: str):
    return _lifecycle_manager.get_plan(agent_id) or {"error": "No active plan"}

@router.post("/lifecycle/verify")
async def lifecycle_verify(req: LifecycleVerifyRequest):
    from sparkai.agent.agent_lifecycle import VerificationCriterion
    criteria = []
    for c in req.criteria:
        criteria.append(VerificationCriterion(
            name=c.get("name", ""),
            description=c.get("description", ""),
            weight=c.get("weight", 1.0),
            threshold=c.get("threshold", 0.7),
            requires_approval=c.get("requires_approval", False),
        ))
    results = {}
    for key, val in req.results.items():
        if isinstance(val, list) and len(val) == 3:
            results[key] = (val[0], val[1], val[2])
        else:
            results[key] = (False, 0.0, str(val))
    verification_results = _lifecycle_manager.verify(req.agent_id, criteria, results)
    return {"results": [{"criterion": vr.criterion_name, "passed": vr.passed, "confidence": vr.confidence, "level": vr.confidence_level.value} for vr in verification_results]}

@router.get("/lifecycle/approvals")
async def lifecycle_pending_approvals():
    return {"approvals": _lifecycle_manager.get_pending_approvals()}

@router.post("/lifecycle/approvals/{approval_id}")
async def lifecycle_approve(approval_id: str, approved: bool):
    success = _lifecycle_manager.approve_verification(approval_id.split(":")[0], approval_id.split(":")[-1], approved)
    return {"success": success}

@router.get("/lifecycle/events")
async def lifecycle_events(agent_id: Optional[str] = None, phase: Optional[str] = None, limit: int = 50):
    phase_enum = None
    if phase:
        try:
            phase_enum = LifecyclePhase(phase)
        except ValueError:
            pass
    return {"events": _lifecycle_manager.get_lifecycle_events(agent_id, phase_enum, limit)}

@router.get("/lifecycle/stats")
async def lifecycle_stats():
    return _lifecycle_manager.get_stats()


# === Slash Command System ===

@router.get("/slash-commands/list")
async def slash_commands_list(category: Optional[str] = None):
    return {"commands": _slash_command_system.list_commands(category)}

@router.post("/slash-commands/execute")
async def slash_commands_execute(req: SlashCommandExecuteRequest):
    result = _slash_command_system.execute(req.command, req.context)
    return {"success": result.success, "output": result.output, "error": result.error, "duration_ms": result.duration_ms}

@router.get("/slash-commands/history")
async def slash_commands_history(limit: int = 50):
    return {"history": _slash_command_system.get_execution_history(limit)}

@router.get("/slash-commands/stats")
async def slash_commands_stats():
    return _slash_command_system.get_stats()


# === Validation Hooks System ===

@router.get("/validation-hooks/rules")
async def validation_hooks_rules(category: Optional[str] = None, phase: Optional[str] = None, enabled_only: bool = False):
    phase_enum = None
    if phase:
        try:
            phase_enum = HookPhase(phase)
        except ValueError:
            pass
    return {"rules": _validation_hooks.list_rules(category, phase_enum, enabled_only)}

@router.post("/validation-hooks/rules")
async def validation_hooks_create_rule(req: HookRuleCreateRequest):
    from sparkai.agent.agent_validation_hooks import HookRule, HookAction
    rule = HookRule(
        name=req.name,
        description=req.description,
        phase=HookPhase(req.phase),
        severity=HookSeverity(req.severity),
        action=HookAction(req.action),
        category=req.category,
        enabled=req.enabled,
    )
    rule_id = _validation_hooks.register_rule(rule)
    return {"id": rule_id, "name": rule.name}

@router.post("/validation-hooks/rules/{rule_id}/toggle")
async def validation_hooks_toggle_rule(rule_id: str, enabled: bool):
    success = _validation_hooks.toggle_rule(rule_id, enabled)
    return {"success": success}

@router.post("/validation-hooks/evaluate")
async def validation_hooks_evaluate(req: HookEvaluateRequest):
    try:
        phase_enum = HookPhase(req.phase)
    except ValueError:
        return {"error": f"Invalid phase: {req.phase}"}
    results = _validation_hooks.evaluate(phase_enum, req.context)
    return {"results": [{"rule": r.rule_name, "action": r.action.value, "passed": r.passed, "message": r.message, "severity": r.severity.value} for r in results]}

@router.get("/validation-hooks/approvals")
async def validation_hooks_approvals():
    return {"approvals": _validation_hooks.get_pending_approvals()}

@router.post("/validation-hooks/approvals/{approval_id}")
async def validation_hooks_approve(approval_id: str, approved: bool):
    success = _validation_hooks.approve(approval_id, approved)
    return {"success": success}

@router.get("/validation-hooks/history")
async def validation_hooks_history(limit: int = 50):
    return {"history": _validation_hooks.get_execution_history(limit)}

@router.get("/validation-hooks/stats")
async def validation_hooks_stats():
    return _validation_hooks.get_stats()


# === Task Execution Engine ===

from sparkai.agent.agent_task_executor import TaskExecutionEngine, ExecutionStrategy, TaskContext

_task_executor = TaskExecutionEngine()


class TaskExecutionRequest(BaseModel):
    task_name: str
    task_description: str
    agent_id: Optional[str] = None
    strategy: str = "direct"
    overall_goal: Optional[str] = None
    max_retries: int = 1
    timeout_seconds: float = 300.0


@router.post("/task-executor/submit")
async def task_executor_submit(req: TaskExecutionRequest):
    strategy = ExecutionStrategy(req.strategy) if req.strategy in [s.value for s in ExecutionStrategy] else ExecutionStrategy.DIRECT
    context = TaskContext(overall_goal=req.overall_goal or "")
    execution = _task_executor.submit_execution(
        task_name=req.task_name,
        task_description=req.task_description,
        agent_id=req.agent_id,
        strategy=strategy,
        context=context,
        max_retries=req.max_retries,
        timeout_seconds=req.timeout_seconds,
    )
    return {"execution_id": execution.id, "status": execution.status.value, "agent_id": execution.agent_id}

@router.post("/task-executor/execute/{execution_id}")
async def task_executor_execute(execution_id: str):
    result = await _task_executor.execute(execution_id)
    return {
        "id": result.id,
        "task_name": result.task_name,
        "status": result.status.value,
        "result": str(result.result)[:500] if result.result else None,
        "error": result.error,
        "confidence": result.confidence,
        "retry_count": result.retry_count,
    }

@router.get("/task-executor/execution/{execution_id}")
async def task_executor_get(execution_id: str):
    return _task_executor.get_execution(execution_id) or {"error": "Execution not found"}

@router.get("/task-executor/history")
async def task_executor_history(limit: int = 50):
    return {"history": _task_executor.get_history(limit)}

@router.get("/task-executor/stats")
async def task_executor_stats():
    return _task_executor.get_stats()


# === Subsystem Integration ===

from sparkai.agent.agent_integration import SubsystemIntegration, IntegrationChannel, IntegrationEvent

_integration = SubsystemIntegration()


@router.get("/integration/stats")
async def integration_stats():
    return _integration.get_stats()

@router.get("/integration/log")
async def integration_log(limit: int = 50, channel: Optional[str] = None):
    channel_enum = None
    if channel:
        try:
            channel_enum = IntegrationChannel(channel)
        except ValueError:
            pass
    return {"log": _integration.get_integration_log(limit, channel_enum)}

@router.post("/integration/propagate")
async def integration_propagate(channel: str, event: str, source: str, target: str, data: Dict[str, Any]):
    try:
        channel_enum = IntegrationChannel(channel)
        event_enum = IntegrationEvent(event)
    except ValueError as e:
        return {"error": f"Invalid channel or event: {e}"}
    success = _integration.propagate(channel_enum, event_enum, source, target, data)
    return {"success": success}

@router.post("/integration/connect-all")
async def integration_connect_all():
    _integration.connect_all()
    return {"status": "connected", "stats": _integration.get_stats()}


# === Session Compaction Engine ===

from sparkai.agent.agent_session_compaction import SessionCompactionEngine, CompactionStrategy, SessionHealth, get_compaction_engine

_compaction_engine = get_compaction_engine()


@router.post("/compaction/sessions")
async def compaction_create_session(agent_id: str = "", max_tokens: int = 100000):
    session = _compaction_engine.create_session(agent_id, max_tokens)
    return session.to_dict()

@router.get("/compaction/sessions")
async def compaction_list_sessions():
    return {"sessions": _compaction_engine.list_sessions()}

@router.post("/compaction/sessions/{session_id}/message")
async def compaction_add_message(session_id: str, role: str = "user", content: str = "", token_count: int = 0):
    msg = _compaction_engine.add_message(session_id, role, content, token_count)
    if msg:
        return msg.to_dict()
    return {"error": "Session not found"}

@router.post("/compaction/sessions/{session_id}/compact")
async def compaction_compact_session(session_id: str, strategy: str = "head_tail_preserve"):
    strat = CompactionStrategy(strategy) if strategy in [s.value for s in CompactionStrategy] else CompactionStrategy.HEAD_TAIL_PRESERVE
    record = await _compaction_engine.compact(session_id, strat)
    if record:
        return record.to_dict()
    return {"error": "Session not found or no compaction needed"}

@router.post("/compaction/sessions/{session_id}/fork")
async def compaction_fork_session(session_id: str, branch_name: str = ""):
    fork = _compaction_engine.fork_session(session_id, branch_name)
    if fork:
        return fork.to_dict()
    return {"error": "Session not found"}

@router.post("/compaction/forks/{fork_id}/merge")
async def compaction_merge_fork(fork_id: str):
    success = _compaction_engine.merge_fork(fork_id)
    return {"success": success}

@router.get("/compaction/forks")
async def compaction_list_forks(session_id: Optional[str] = None):
    return {"forks": _compaction_engine.list_forks(session_id)}

@router.get("/compaction/history")
async def compaction_history(session_id: Optional[str] = None, limit: int = 50):
    return {"history": _compaction_engine.get_compaction_history(session_id, limit)}

@router.get("/compaction/stats")
async def compaction_stats():
    return _compaction_engine.get_stats()


# === Recovery Engine ===

from sparkai.agent.agent_recovery import RecoveryEngine, FailureType, FailureSeverity, RecoveryStatus, EscalationAction, get_recovery_engine

_recovery_engine = get_recovery_engine()


class RecoveryDetectRequest(BaseModel):
    error_message: str
    source: str = ""
    context: Optional[Dict[str, Any]] = None


@router.post("/recovery/detect")
async def recovery_detect(req: RecoveryDetectRequest):
    record = await _recovery_engine.detect_and_recover(req.error_message, req.source, req.context)
    return record.to_dict()

@router.get("/recovery/recipes")
async def recovery_recipes(failure_type: Optional[str] = None):
    ft = FailureType(failure_type) if failure_type else None
    return {"recipes": _recovery_engine.list_recipes(ft)}

@router.get("/recovery/history")
async def recovery_history(limit: int = 50, failure_type: Optional[str] = None):
    ft = FailureType(failure_type) if failure_type else None
    return {"history": _recovery_engine.get_failure_history(limit, ft)}

@router.get("/recovery/stats")
async def recovery_stats():
    return _recovery_engine.get_stats()


# === Tool Permission System ===

from sparkai.agent.agent_tool_permission import ToolPermissionSystem, PermissionLevel, ToolDangerLevel, EnforcementResult, get_tool_permission_system

_permission_system = get_tool_permission_system()


class PermissionCheckRequest(BaseModel):
    agent_role: str
    tool_name: str
    agent_id: str = ""


class ApprovalRequestModel(BaseModel):
    agent_id: str
    agent_role: str
    tool_name: str
    params: Optional[Dict[str, Any]] = None
    reason: str = ""


@router.post("/permissions/check")
async def permissions_check(req: PermissionCheckRequest):
    result = _permission_system.check(req.agent_role, req.tool_name, req.agent_id)
    return {"result": result.value, "agent_role": req.agent_role, "tool_name": req.tool_name}

@router.get("/permissions/role-tools/{role}")
async def permissions_role_tools(role: str):
    return _permission_system.get_role_tools(role)

@router.post("/permissions/approval")
async def permissions_request_approval(req: ApprovalRequestModel):
    request = _permission_system.request_approval(req.agent_id, req.agent_role, req.tool_name, req.params, req.reason)
    return request.to_dict()

@router.post("/permissions/approval/{approval_id}/approve")
async def permissions_approve(approval_id: str, approved_by: str = ""):
    success = _permission_system.approve(approval_id, approved_by)
    return {"success": success}

@router.post("/permissions/approval/{approval_id}/deny")
async def permissions_deny(approval_id: str, denied_by: str = ""):
    success = _permission_system.deny(approval_id, denied_by)
    return {"success": success}

@router.get("/permissions/pending-approvals")
async def permissions_pending_approvals():
    return {"approvals": _permission_system.get_pending_approvals()}

@router.post("/permissions/grant-override")
async def permissions_grant_override(role: str, tool_name: str):
    _permission_system.grant_override(role, tool_name)
    return {"success": True}

@router.post("/permissions/register-tool")
async def permissions_register_tool(tool_name: str, required_level: str = "read_only", danger_level: str = "moderate", requires_approval: bool = False):
    perm = _permission_system.register_tool(tool_name, required_level, danger_level, requires_approval)
    return perm.to_dict()

@router.get("/permissions/audit-log")
async def permissions_audit_log(limit: int = 100, agent_id: Optional[str] = None):
    return {"entries": _permission_system.get_audit_log(limit, agent_id)}

@router.get("/permissions/stats")
async def permissions_stats():
    return _permission_system.get_stats()


# === Context Compression Engine ===

from sparkai.agent.agent_context_compression import ContextCompressionEngine, CompressionStrategy as CtxCompressionStrategy, get_compression_engine

_compression_engine = get_compression_engine()


@router.get("/compression/stats")
async def compression_stats():
    return _compression_engine.get_stats()

@router.get("/compression/history")
async def compression_history(limit: int = 50):
    return {"history": _compression_engine.get_compression_history(limit)}


# === Debug Protocol Engine ===

from sparkai.agent.agent_debug_protocol import DebugProtocolEngine, ErrorCategory, EntryType, PhysicsRegime, get_debug_protocol

_debug_protocol = get_debug_protocol()


class DebugDiagnoseRequest(BaseModel):
    error_message: str
    game_context: str = ""


@router.post("/debug-protocol/diagnose")
async def debug_protocol_diagnose(req: DebugDiagnoseRequest):
    trace = _debug_protocol.diagnose(req.error_message, req.game_context)
    return trace.to_dict()

@router.post("/debug-protocol/verify/{trace_id}")
async def debug_protocol_verify(trace_id: str, passed: bool):
    _debug_protocol.verify_fix(trace_id, passed)
    return {"status": "verified" if passed else "failed"}

@router.get("/debug-protocol/entries")
async def debug_protocol_entries(entry_type: Optional[str] = None, category: Optional[str] = None):
    et = EntryType(entry_type) if entry_type else None
    cat = ErrorCategory(category) if category else None
    return {"entries": _debug_protocol.list_entries(et, cat)}

@router.get("/debug-protocol/proactive-rules")
async def debug_protocol_proactive_rules(enabled_only: bool = False):
    return {"rules": _debug_protocol.list_proactive_rules(enabled_only)}

@router.post("/debug-protocol/proactive-check")
async def debug_protocol_proactive_check(context: Dict[str, Any]):
    results = _debug_protocol.run_proactive_checks(context)
    return {"results": results}

@router.get("/debug-protocol/traces")
async def debug_protocol_traces(limit: int = 50):
    return {"traces": _debug_protocol.get_traces(limit)}

@router.get("/debug-protocol/stats")
async def debug_protocol_stats():
    return _debug_protocol.get_stats()


# === Autowork Engine ===

from sparkai.agent.agent_autowork import AutoworkEngine, AutoworkPhase, PlanStatus, get_autowork_engine

_autowork_engine = get_autowork_engine()


class AutoworkPlanRequest(BaseModel):
    goal: str
    status_quo: str = ""
    target_end_state: str = ""
    items: Optional[List[Dict[str, str]]] = None


@router.post("/autowork/plans")
async def autowork_create_plan(req: AutoworkPlanRequest):
    plan = _autowork_engine.create_plan(req.goal, req.status_quo, req.target_end_state, req.items)
    return plan.to_dict()

@router.post("/autowork/plans/{plan_id}/approve")
async def autowork_approve_plan(plan_id: str):
    success = _autowork_engine.approve_plan(plan_id)
    return {"success": success}

@router.get("/autowork/plans")
async def autowork_list_plans(status: Optional[str] = None):
    ps = PlanStatus(status) if status else None
    return {"plans": _autowork_engine.list_plans(ps)}

@router.get("/autowork/plans/{plan_id}")
async def autowork_get_plan(plan_id: str):
    plan = _autowork_engine.get_plan(plan_id)
    if plan:
        return plan.to_dict()
    return {"error": "Plan not found"}

@router.get("/autowork/plans/{plan_id}/transcript")
async def autowork_get_transcript(plan_id: str, phase: Optional[str] = None):
    ph = AutoworkPhase(phase) if phase else None
    return {"entries": _autowork_engine.get_transcript(plan_id, ph)}

@router.post("/autowork/plans/{plan_id}/abort")
async def autowork_abort(plan_id: str):
    success = _autowork_engine.abort(plan_id)
    return {"success": success}

@router.get("/autowork/stats")
async def autowork_stats():
    return _autowork_engine.get_stats()


# === Policy Engine ===

from sparkai.agent.agent_policy import PolicyEngine, PolicyContext, PolicyCondition, ConditionType, PolicyAction, ActionType, PolicyRule, get_policy_engine

_policy_engine = get_policy_engine()


class PolicyEvaluateRequest(BaseModel):
    agent_id: str = ""
    agent_role: str = ""
    task_type: str = ""
    complexity_score: float = 0.0
    confidence: float = 1.0
    agent_workload: float = 0.0
    failure_count: int = 0
    time_elapsed: float = 0.0


@router.post("/policy/evaluate")
async def policy_evaluate(req: PolicyEvaluateRequest):
    context = PolicyContext(
        agent_id=req.agent_id,
        agent_role=req.agent_role,
        task_type=req.task_type,
        complexity_score=req.complexity_score,
        confidence=req.confidence,
        agent_workload=req.agent_workload,
        failure_count=req.failure_count,
        time_elapsed=req.time_elapsed,
    )
    results = _policy_engine.evaluate(context)
    return {"results": [r.to_dict() for r in results]}

@router.get("/policy/rules")
async def policy_rules(enabled_only: bool = False):
    return {"rules": _policy_engine.list_rules(enabled_only)}

@router.get("/policy/history")
async def policy_history(limit: int = 50):
    return {"history": _policy_engine.get_evaluation_history(limit)}

@router.get("/policy/stats")
async def policy_stats():
    return _policy_engine.get_stats()


# === Mixture of Agents ===

from sparkai.agent.agent_moa import MixtureOfAgentsEngine, AggregationStrategy, get_moa_engine

_moa_engine = get_moa_engine()


class MoAQueryRequest(BaseModel):
    query: str
    strategy: str = "best_of"


@router.post("/moa/query")
async def moa_query(req: MoAQueryRequest):
    strategy = AggregationStrategy(req.strategy) if req.strategy in [s.value for s in AggregationStrategy] else AggregationStrategy.BEST_OF
    result = await _moa_engine.query(req.query, strategy)
    return result.to_dict()

@router.get("/moa/models")
async def moa_models():
    return {"models": _moa_engine.list_models()}

@router.get("/moa/results")
async def moa_results(limit: int = 20):
    return {"results": _moa_engine.get_results(limit)}

@router.get("/moa/stats")
async def moa_stats():
    return _moa_engine.get_stats()


# === Structured Protocol ===

from sparkai.agent.agent_structured_protocol import StructuredProtocol, MessageType, get_structured_protocol

_structured_protocol = get_structured_protocol()


class StructuredMessageRequest(BaseModel):
    message_type: str
    sender: str
    recipient: str
    payload: Dict[str, Any]
    priority: int = 50


@router.post("/structured-protocol/send")
async def structured_protocol_send(req: StructuredMessageRequest):
    msg = _structured_protocol.create_message(
        message_type=MessageType(req.message_type),
        sender=req.sender,
        recipient=req.recipient,
        payload=req.payload,
        priority=req.priority,
    )
    result = _structured_protocol.send(msg)
    return result

@router.post("/structured-protocol/acknowledge/{message_id}")
async def structured_protocol_acknowledge(message_id: str):
    success = _structured_protocol.acknowledge(message_id)
    return {"success": success}

@router.get("/structured-protocol/schemas")
async def structured_protocol_schemas():
    return {"schemas": _structured_protocol.list_schemas()}

@router.get("/structured-protocol/dead-letters")
async def structured_protocol_dead_letters(limit: int = 50):
    return {"dead_letters": _structured_protocol.get_dead_letters(limit)}

@router.post("/structured-protocol/dead-letters/{entry_id}/retry")
async def structured_protocol_retry_dead_letter(entry_id: str):
    result = _structured_protocol.retry_dead_letter(entry_id)
    return result

@router.get("/structured-protocol/delivery-log")
async def structured_protocol_delivery_log(limit: int = 100):
    return {"log": _structured_protocol.get_delivery_log(limit)}

@router.get("/structured-protocol/stats")
async def structured_protocol_stats():
    return _structured_protocol.get_stats()


# === Credential Manager ===

from sparkai.agent.agent_credential import CredentialManager, KeyScope, get_credential_manager

_credential_manager = get_credential_manager()


class CredentialRegisterRequest(BaseModel):
    name: str
    provider: str
    key: str
    scope: str = "llm_provider"
    priority: int = 50
    max_rpm: int = 60


@router.post("/credentials/register")
async def credentials_register(req: CredentialRegisterRequest):
    entry = _credential_manager.register_key(
        name=req.name,
        provider=req.provider,
        key=req.key,
        scope=KeyScope(req.scope),
        priority=req.priority,
        max_rpm=req.max_rpm,
    )
    return entry.to_dict()

@router.get("/credentials")
async def credentials_list(provider: Optional[str] = None, scope: Optional[str] = None, status: Optional[str] = None):
    scope_enum = KeyScope(scope) if scope else None
    from sparkai.agent.agent_credential import KeyStatus
    status_enum = KeyStatus(status) if status else None
    return {"credentials": _credential_manager.list_credentials(provider, scope_enum, status_enum)}

@router.post("/credentials/{credential_id}/rotate")
async def credentials_rotate(credential_id: str, new_key: str = ""):
    entry = _credential_manager.rotate_key(credential_id, new_key)
    if entry:
        return entry.to_dict()
    return {"error": "Credential not found"}

@router.post("/credentials/{credential_id}/report-failure")
async def credentials_report_failure(credential_id: str, error: str = ""):
    _credential_manager.report_failure(credential_id, error)
    return {"status": "reported"}

@router.post("/credentials/{credential_id}/report-success")
async def credentials_report_success(credential_id: str, latency_ms: float = 0.0):
    _credential_manager.report_success(credential_id, latency_ms)
    return {"status": "reported"}

@router.get("/credentials/access-log")
async def credentials_access_log(limit: int = 100, credential_id: Optional[str] = None):
    return {"log": _credential_manager.get_access_log(limit, credential_id)}

@router.get("/credentials/stats")
async def credentials_stats():
    return _credential_manager.get_stats()


# === Sandbox Engine ===

from sparkai.agent.agent_sandbox import SandboxEngine, ResourceLimits, AccessLevel, SandboxStatus, get_sandbox_engine

_sandbox_engine = get_sandbox_engine()


class SandboxSessionRequest(BaseModel):
    agent_id: str = ""
    workspace_root: str = ""
    allowed_tools: Optional[List[str]] = None
    blocked_tools: Optional[List[str]] = None


@router.post("/sandbox/sessions")
async def sandbox_create_session(req: SandboxSessionRequest):
    session = _sandbox_engine.create_session(
        agent_id=req.agent_id,
        workspace_root=req.workspace_root,
        allowed_tools=set(req.allowed_tools) if req.allowed_tools else None,
        blocked_tools=set(req.blocked_tools) if req.blocked_tools else None,
    )
    return session.to_dict()

@router.get("/sandbox/sessions")
async def sandbox_list_sessions(agent_id: Optional[str] = None):
    return {"sessions": _sandbox_engine.list_sessions(agent_id)}

@router.get("/sandbox/sessions/{session_id}")
async def sandbox_get_session(session_id: str):
    session = _sandbox_engine.get_session(session_id)
    if session:
        return session.to_dict()
    return {"error": "Session not found"}

@router.post("/sandbox/sessions/{session_id}/execute")
async def sandbox_execute(session_id: str, tool_name: str, params: Optional[Dict[str, Any]] = None):
    result = await _sandbox_engine.execute(session_id, tool_name, params)
    return result.to_dict()

@router.post("/sandbox/sessions/{session_id}/terminate")
async def sandbox_terminate(session_id: str):
    success = _sandbox_engine.terminate_session(session_id)
    return {"success": success}

@router.get("/sandbox/results")
async def sandbox_results(session_id: Optional[str] = None, limit: int = 50):
    return {"results": _sandbox_engine.get_results(session_id, limit)}

@router.get("/sandbox/stats")
async def sandbox_stats():
    return _sandbox_engine.get_stats()


# === Asset Consistency Engine ===

from sparkai.agent.asset_consistency import AssetConsistencyEngine, AssetType, KeyStatus, get_consistency_engine

_consistency_engine = get_consistency_engine()


class AssetKeyRegistration(BaseModel):
    key: str
    asset_type: str
    source_file: str = ""


@router.post("/consistency/register-generation")
async def consistency_register_generation(req: AssetKeyRegistration):
    try:
        asset_type = AssetType(req.asset_type)
    except ValueError:
        valid_types = [t.value for t in AssetType]
        return {"error": f"Invalid asset_type '{req.asset_type}'. Valid types: {valid_types}"}
    entry = _consistency_engine.register_generation(req.key, asset_type, req.source_file)
    return entry.to_dict()

@router.post("/consistency/register-manifest")
async def consistency_register_manifest(req: AssetKeyRegistration):
    try:
        asset_type = AssetType(req.asset_type)
    except ValueError:
        valid_types = [t.value for t in AssetType]
        return {"error": f"Invalid asset_type '{req.asset_type}'. Valid types: {valid_types}"}
    entry = _consistency_engine.register_manifest(req.key, asset_type, req.source_file)
    return entry.to_dict()

@router.post("/consistency/register-reference")
async def consistency_register_reference(req: AssetKeyRegistration):
    try:
        asset_type = AssetType(req.asset_type)
    except ValueError:
        valid_types = [t.value for t in AssetType]
        return {"error": f"Invalid asset_type '{req.asset_type}'. Valid types: {valid_types}"}
    entry = _consistency_engine.register_reference(req.key, asset_type, req.source_file)
    return entry.to_dict()

@router.post("/consistency/validate")
async def consistency_validate():
    report = _consistency_engine.validate()
    return report.to_dict()

@router.get("/consistency/keys")
async def consistency_keys(asset_type: Optional[str] = None, status: Optional[str] = None):
    at = AssetType(asset_type) if asset_type else None
    st = KeyStatus(status) if status else None
    return {"keys": _consistency_engine.list_keys(at, st)}

@router.get("/consistency/reports")
async def consistency_reports(limit: int = 20):
    return {"reports": _consistency_engine.get_reports(limit)}

@router.get("/consistency/stats")
async def consistency_stats():
    return _consistency_engine.get_stats()


# === Memory Persistence Engine ===

from sparkai.agent.agent_persistence import MemoryPersistenceEngine, CheckpointType, get_persistence_engine

_persistence_engine = get_persistence_engine()


class PersistenceSaveRequest(BaseModel):
    category: str
    key: str
    data: Dict[str, Any]


@router.post("/persistence/save")
async def persistence_save(req: PersistenceSaveRequest):
    status = _persistence_engine.save(req.category, req.key, req.data)
    return {"status": status.value}

@router.get("/persistence/load/{category}/{key}")
async def persistence_load(category: str, key: str):
    data, status = _persistence_engine.load(category, key)
    return {"status": status.value, "data": data}

@router.delete("/persistence/delete/{category}/{key}")
async def persistence_delete(category: str, key: str):
    status = _persistence_engine.delete(category, key)
    return {"status": status.value}

@router.get("/persistence/list/{category}")
async def persistence_list(category: str):
    return {"keys": _persistence_engine.list_keys(category)}

@router.post("/persistence/checkpoint")
async def persistence_checkpoint(checkpoint_type: str = "manual", label: str = ""):
    ct = CheckpointType(checkpoint_type) if checkpoint_type in [t.value for t in CheckpointType] else CheckpointType.MANUAL
    checkpoint = _persistence_engine.create_checkpoint(ct, label)
    return checkpoint.to_dict()

@router.post("/persistence/restore/{checkpoint_id}")
async def persistence_restore(checkpoint_id: str):
    success = _persistence_engine.restore_checkpoint(checkpoint_id)
    return {"success": success}

@router.get("/persistence/checkpoints")
async def persistence_list_checkpoints():
    return {"checkpoints": _persistence_engine.list_checkpoints()}

@router.get("/persistence/stats")
async def persistence_stats():
    return _persistence_engine.get_stats()


# === Error Classification Engine ===

from sparkai.agent.agent_error_classifier import ErrorClassifier, get_error_classifier

_error_classifier = get_error_classifier()


@router.post("/error-classifier/classify")
async def error_classifier_classify(
    error_message: str = "",
    http_status: Optional[int] = None,
    context_tokens: int = 0,
    context_messages: int = 0,
    provider: str = "",
):
    try:
        exc = Exception(error_message)
        classified = _error_classifier.classify(
            exc,
            context_tokens=context_tokens,
            context_messages=context_messages,
            provider=provider,
            http_status=http_status,
        )
        return classified.to_dict()
    except Exception as e:
        return {"error": str(e)}


@router.get("/error-classifier/stats")
async def error_classifier_stats():
    return _error_classifier.get_stats()


# === File State Coordination Engine ===

from sparkai.agent.agent_file_state import FileStateEngine, get_file_state_engine

_file_state_engine = get_file_state_engine()


@router.post("/file-state/register-read")
async def file_state_register_read(agent_id: str, file_path: str):
    version = _file_state_engine.register_read(agent_id, file_path)
    return version.to_dict()


@router.post("/file-state/register-write")
async def file_state_register_write(agent_id: str, file_path: str, content: str = ""):
    version = _file_state_engine.register_write(agent_id, file_path, content)
    return version.to_dict()


@router.post("/file-state/register-create")
async def file_state_register_create(agent_id: str, file_path: str, content: str = ""):
    version = _file_state_engine.register_create(agent_id, file_path, content)
    return version.to_dict()


@router.get("/file-state/check-stale")
async def file_state_check_stale(agent_id: str, file_path: str):
    alert = _file_state_engine.check_stale(agent_id, file_path)
    return alert.to_dict() if alert else {"stale": False}


@router.get("/file-state/stale-alerts/{agent_id}")
async def file_state_stale_alerts(agent_id: str):
    return {"alerts": [a.to_dict() for a in _file_state_engine.get_stale_alerts(agent_id)]}


@router.post("/file-state/acquire-lock")
async def file_state_acquire_lock(agent_id: str, file_path: str, timeout: float = 300.0):
    success, error = _file_state_engine.acquire_write_lock(agent_id, file_path, timeout)
    return {"success": success, "error": error}


@router.post("/file-state/release-lock")
async def file_state_release_lock(agent_id: str, file_path: str):
    success = _file_state_engine.release_write_lock(agent_id, file_path)
    return {"success": success}


@router.get("/file-state/version/{file_path:path}")
async def file_state_get_version(file_path: str):
    version = _file_state_engine.get_file_version(file_path)
    return version.to_dict() if version else {"version": 0}


@router.get("/file-state/stats")
async def file_state_stats():
    return _file_state_engine.get_stats()


# === Subagent Spawner Engine ===

from sparkai.agent.agent_subagent_spawner import (
    SubagentSpawner, SubagentConfig, SubagentRole, SpawnRequest,
    get_subagent_spawner,
)

_subagent_spawner = get_subagent_spawner()


class SubagentSpawnRequest(BaseModel):
    parent_id: str
    task_description: str
    role: str = "worker"
    max_spawn_depth: int = 2
    timeout_seconds: float = 600.0
    current_depth: int = 0


@router.post("/subagent/spawn")
async def subagent_spawn(req: SubagentSpawnRequest):
    role = SubagentRole(req.role) if req.role in [r.value for r in SubagentRole] else SubagentRole.WORKER
    config = SubagentConfig(
        role=role,
        max_spawn_depth=req.max_spawn_depth,
        timeout_seconds=req.timeout_seconds,
    )
    request = SpawnRequest(
        parent_id=req.parent_id,
        task_description=req.task_description,
        config=config,
        current_depth=req.current_depth,
    )
    result = _subagent_spawner.create_subagent(request)
    return result.to_dict()


@router.post("/subagent/{subagent_id}/start")
async def subagent_start(subagent_id: str):
    _subagent_spawner.start_subagent(subagent_id)
    return {"status": "started"}


@router.post("/subagent/{subagent_id}/complete")
async def subagent_complete(subagent_id: str, output: Optional[str] = None):
    _subagent_spawner.complete_subagent(subagent_id, output)
    return {"status": "completed"}


@router.post("/subagent/{subagent_id}/fail")
async def subagent_fail(subagent_id: str, error: str = "Unknown error"):
    _subagent_spawner.fail_subagent(subagent_id, error)
    return {"status": "failed"}


@router.get("/subagent/{subagent_id}")
async def subagent_get(subagent_id: str):
    result = _subagent_spawner.get_subagent(subagent_id)
    return result.to_dict() if result else {"error": "Subagent not found"}


@router.get("/subagent/active")
async def subagent_active(parent_id: Optional[str] = None):
    results = _subagent_spawner.get_active_subagents(parent_id)
    return {"subagents": [r.to_dict() for r in results]}


@router.get("/subagent/children/{parent_id}")
async def subagent_children(parent_id: str):
    children = _subagent_spawner.get_children(parent_id)
    return {"children": [c.to_dict() for c in children]}


@router.get("/subagent/stats")
async def subagent_stats():
    return _subagent_spawner.get_stats()


# === Tool Output Pruner Engine ===

from sparkai.agent.agent_tool_pruner import ToolOutputPruner, get_tool_output_pruner

_tool_pruner = get_tool_output_pruner()


@router.post("/tool-pruner/prune")
async def tool_pruner_prune(tool_name: str, output: str = ""):
    pruned_output, result = _tool_pruner.prune(tool_name, output)
    return {"pruned_output": pruned_output[:500], "prune_result": result.to_dict()}


@router.get("/tool-pruner/rules")
async def tool_pruner_rules():
    return {"rules": {name: rule.to_dict() for name, rule in _tool_pruner._rules.items()}}


@router.get("/tool-pruner/stats")
async def tool_pruner_stats():
    return _tool_pruner.get_stats()


# === Trajectory Learning Engine ===

from sparkai.agent.agent_trajectory_learner import TrajectoryLearner, get_trajectory_learner

_trajectory_learner = get_trajectory_learner()


@router.post("/trajectory/analyze-chains")
async def trajectory_analyze_chains():
    result = _trajectory_learner.analyze_saved_chains()
    return result


@router.get("/trajectory/patterns")
async def trajectory_patterns(pattern_type: Optional[str] = None):
    from sparkai.agent.agent_trajectory_learner import PatternType
    pt = PatternType(pattern_type) if pattern_type else None
    patterns = _trajectory_learner.get_patterns(pt)
    return {"patterns": [p.to_dict() for p in patterns]}


@router.get("/trajectory/recommendation")
async def trajectory_recommendation(goal: str = ""):
    tools = _trajectory_learner.get_tool_sequence_recommendation(goal)
    return {"goal": goal, "recommended_tools": tools, "has_recommendation": tools is not None}


@router.get("/trajectory/stats")
async def trajectory_stats():
    return _trajectory_learner.get_stats()


# === Intent Classifier Engine ===

from sparkai.agent.agent_intent_classifier import IntentClassifier, IntentDomain, get_intent_classifier

_intent_classifier = get_intent_classifier()


class IntentClassifyRequest(BaseModel):
    prompt: str


class IntentBatchClassifyRequest(BaseModel):
    prompts: List[str]


@router.post("/intent/classify")
async def intent_classify(request: IntentClassifyRequest):
    result = _intent_classifier.classify(request.prompt)
    return result.to_dict()


@router.post("/intent/classify-batch")
async def intent_classify_batch(request: IntentBatchClassifyRequest):
    results = _intent_classifier.classify_batch(request.prompts)
    summary = _intent_classifier.get_intent_summary(results)
    return {
        "results": [r.to_dict() for r in results],
        "summary": summary,
    }


@router.get("/intent/intents")
async def intent_list_intents():
    return {"intents": [d.value for d in IntentDomain]}


# === Skill Curator Engine ===

from sparkai.agent.agent_skill_curator import SkillCurator, get_skill_curator

_skill_curator = get_skill_curator()


class SkillRegisterRequest(BaseModel):
    name: str
    description: str
    category: str
    source_agent: str = ""
    tags: Optional[List[str]] = None


class SkillConsolidateRequest(BaseModel):
    parent_id: str
    child_ids: List[str]
    strategy: str = "merge"


class SkillUsageRequest(BaseModel):
    skill_id: str
    success: bool = True


@router.get("/curator/health")
async def curator_health():
    return _skill_curator.get_ecosystem_health()


@router.get("/curator/skills")
async def curator_list_skills(
    category: Optional[str] = None,
    lifecycle: Optional[str] = None,
    min_success_rate: float = 0.0,
):
    lc = None
    if lifecycle:
        try:
            from sparkai.agent.agent_skill_curator import SkillLifecycle
            lc = SkillLifecycle(lifecycle)
        except ValueError:
            pass
    skills = _skill_curator.list_skills(category=category, lifecycle=lc, min_success_rate=min_success_rate)
    return {"skills": [s.to_dict() for s in skills], "count": len(skills)}


@router.get("/curator/categories")
async def curator_categories():
    return {"categories": _skill_curator.get_categories()}


@router.post("/curator/register")
async def curator_register(request: SkillRegisterRequest):
    skill = _skill_curator.register_skill(
        name=request.name,
        description=request.description,
        category=request.category,
        source_agent=request.source_agent,
        tags=request.tags,
    )
    return skill.to_dict()


@router.post("/curator/record-usage")
async def curator_record_usage(request: SkillUsageRequest):
    _skill_curator.record_usage(request.skill_id, request.success)
    return {"status": "recorded"}


@router.post("/curator/review")
async def curator_review():
    result = await _skill_curator.review()
    return result


@router.post("/curator/consolidate")
async def curator_consolidate(request: SkillConsolidateRequest):
    from sparkai.agent.agent_skill_curator import ConsolidationStrategy
    try:
        strategy = ConsolidationStrategy(request.strategy)
    except ValueError:
        strategy = ConsolidationStrategy.MERGE
    result = _skill_curator.consolidate(request.parent_id, request.child_ids, strategy)
    if result:
        return result.to_dict()
    return {"error": "Consolidation failed"}


@router.get("/curator/review-history")
async def curator_review_history(limit: int = 20):
    return {"history": _skill_curator.get_review_history(limit)}


@router.get("/curator/consolidation-log")
async def curator_consolidation_log(limit: int = 20):
    return {"log": _skill_curator.get_consolidation_log(limit)}


@router.get("/curator/skill/{skill_id}")
async def curator_get_skill(skill_id: str):
    skill = _skill_curator.get_skill(skill_id)
    if skill:
        return skill.to_dict()
    return {"error": "Skill not found"}


# === Prompt Builder Engine ===

from sparkai.agent.agent_prompt_builder import PromptBuilder, get_prompt_builder

_prompt_builder = get_prompt_builder()


class PromptBuildRequest(BaseModel):
    task: str = ""
    game_context: Optional[Dict[str, Any]] = None
    skills_list: Optional[List[Dict[str, Any]]] = None
    memory_entries: Optional[List[Dict[str, Any]]] = None
    extra_instructions: str = ""


@router.post("/prompt-builder/build")
async def prompt_builder_build(request: PromptBuildRequest):
    artifact = _prompt_builder.build(
        game_context=request.game_context,
        current_task=request.task,
        skills_list=request.skills_list,
        memory_entries=request.memory_entries,
        extra_instructions=request.extra_instructions,
    )
    return artifact.to_dict()


@router.get("/prompt-builder/preview")
async def prompt_builder_preview(task: str = ""):
    artifact = _prompt_builder.build(current_task=task)
    return {
        "sections_summary": artifact.to_dict(),
        "prompt_preview": artifact.full_text[:500],
    }


@router.post("/prompt-builder/invalidate-cache")
async def prompt_builder_invalidate_cache():
    _prompt_builder.invalidate_cache()
    return {"status": "cache_invalidated"}


# === Execution Budget Engine ===

from sparkai.agent.agent_execution_budget import ExecutionBudget, get_execution_budget

_execution_budget = get_execution_budget()


class BudgetRecordRequest(BaseModel):
    session_id: str
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0


@router.get("/budget/stats")
async def budget_stats():
    return _execution_budget.get_overall_stats()


@router.get("/budget/daily")
async def budget_daily():
    return _execution_budget.get_daily_stats()


@router.get("/budget/session/{session_id}")
async def budget_session(session_id: str):
    return _execution_budget.get_session_stats(session_id)


@router.post("/budget/start-session")
async def budget_start_session(session_id: str, model: str = "unknown"):
    budget = _execution_budget.start_session(session_id, model)
    return budget.to_dict()


@router.post("/budget/end-session")
async def budget_end_session(session_id: str):
    budget = _execution_budget.end_session(session_id)
    if budget:
        return budget.to_dict()
    return {"error": "Session not found"}


@router.post("/budget/record")
async def budget_record(request: BudgetRecordRequest):
    from sparkai.agent.agent_execution_budget import TokenUsage
    tokens = TokenUsage(
        prompt_tokens=request.prompt_tokens,
        completion_tokens=request.completion_tokens,
        total_tokens=request.total_tokens,
    )
    _execution_budget.record_usage(request.session_id, tokens)
    tier = _execution_budget.check_tier(request.session_id)
    return {"status": "recorded", "tier": tier.value}


@router.get("/budget/check/{session_id}")
async def budget_check(session_id: str):
    tier = _execution_budget.check_tier(session_id)
    can_continue = _execution_budget.can_continue(session_id)
    return {"tier": tier.value, "can_continue": can_continue}


@router.get("/budget/history")
async def budget_history(limit: int = 50):
    return {"history": _execution_budget.get_usage_history(limit)}


# === Game Generation Pipeline ===

class GameGenerateRequest(BaseModel):
    prompt: str
    genre: Optional[str] = None
    project_name: Optional[str] = None
    phases: Optional[List[str]] = None


@router.post("/generate/game")
async def generate_game(request: GameGenerateRequest):
    intent = _intent_classifier.classify(request.prompt)

    if _event_bus:
        _event_bus.emit(Event(
            channel=EventChannel.AGENT,
            topic="game_generation_started",
            source="AgentRoutes",
            data={"prompt": request.prompt[:100], "intent": intent.to_dict()},
        ))

    try:
        pipeline_result = await _runtime.run_pipeline(request.prompt)
    except Exception as e:
        pipeline_result = {"error": str(e)}

    stats = {
        "intent": intent.to_dict(),
        "runtime_state": _runtime.state.value,
        "budget_daily": _execution_budget.get_daily_stats(),
    }

    if _event_bus:
        _event_bus.emit(Event(
            channel=EventChannel.AGENT,
            topic="game_generation_completed",
            source="AgentRoutes",
            data={"prompt": request.prompt[:100], "stats": stats},
        ))

    return {
        "pipeline_result": pipeline_result,
        "generation_stats": stats,
    }


class AgentStatusResponse(BaseModel):
    state: str
    initialized: bool
    subsystems_ready: int
    total_subsystems: int
    skill_count: int
    session_count: int
    budget_tier: str
    daily_cost: float


@router.get("/agent/status")
async def agent_status():
    runtime_status = _runtime.get_status()
    health = _skill_curator.get_ecosystem_health()
    budget = _execution_budget.get_overall_stats()

    return {
        "state": _runtime.state.value,
        "initialized": _runtime.state.value == "running",
        "subsystems_ready": sum(1 for v in runtime_status.get("subsystems_ready", {}).values() if v),
        "total_subsystems": len(runtime_status.get("subsystems_ready", {})),
        "skill_count": health.get("total_skills", 0),
        "active_sessions": budget.get("active_sessions", 0),
        "budget_tier": "normal",
        "daily_cost": budget.get("daily", {}).get("cost_usd", 0),
        "health": health,
    }


@router.post("/agent/command")
async def agent_command(command: str, args: Optional[str] = None):
    import subprocess
    try:
        result = subprocess.run(
            ["python", "-m", "sparkai.agent.runtime", command, *(args.split() if args else [])],
            capture_output=True, text=True, timeout=30,
            cwd=os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        )
        return {"command": command, "stdout": result.stdout, "stderr": result.stderr, "code": result.returncode}
    except subprocess.TimeoutExpired:
        return {"error": "Command timed out"}
    except Exception as e:
        return {"error": str(e)}


# === Game Loop Engine ===

from sparkai.engine.game_loop import get_game_loop, ExecutionPhase

_game_loop = get_game_loop()


class LoopConfigRequest(BaseModel):
    target_fps: int = 60
    max_frame_skip: int = 5
    use_fixed_timestep: bool = True
    fixed_timestep: float = 0.016
    time_scale: float = 1.0


@router.get("/game-loop/status")
async def game_loop_status():
    return _game_loop.get_statistics()


@router.get("/game-loop/phases")
async def game_loop_phases():
    return {"phases": [p.value for p in ExecutionPhase]}


@router.post("/game-loop/start")
async def game_loop_start():
    _game_loop.start()
    return {"status": "started"}


@router.post("/game-loop/stop")
async def game_loop_stop():
    _game_loop.stop()
    return {"status": "stopped"}


@router.post("/game-loop/pause")
async def game_loop_pause():
    _game_loop.pause()
    return {"status": "paused"}


@router.post("/game-loop/resume")
async def game_loop_resume():
    _game_loop.resume()
    return {"status": "resumed"}


@router.post("/game-loop/time-scale")
async def game_loop_set_time_scale(scale: float = 1.0):
    _game_loop.set_time_scale(scale)
    return {"time_scale": scale}


@router.post("/game-loop/tick")
async def game_loop_tick():
    stats = _game_loop.tick()
    return stats


# === Signal Bus ===

from sparkai.engine.signal_system import get_signal_bus, ConnectionType

_signal_bus = get_signal_bus()


@router.get("/signal-bus/connections")
async def signal_bus_connections():
    return {"count": _signal_bus.get_connection_count()}


@router.post("/signal-bus/emit")
async def signal_bus_emit(signal_name: str, data: Any = None):
    count = _signal_bus.emit(signal_name, data)
    return {"signal": signal_name, "listeners_notified": count}


@router.post("/signal-bus/flush-deferred")
async def signal_bus_flush():
    count = _signal_bus.flush_deferred()
    return {"deferred_flushed": count}


# === Animation Player ===

from sparkai.engine.animation_system import get_animation_player, PlaybackState

_animation_player = get_animation_player()


@router.get("/animation/status")
async def animation_status():
    return _animation_player.get_status()


@router.get("/animation/clips")
async def animation_clips():
    return {"clips": [c.name for c in _animation_player._clips.values()]}


@router.post("/animation/play")
async def animation_play(clip_name: str):
    _animation_player.play(clip_name)
    return _animation_player.get_status()


@router.post("/animation/pause")
async def animation_pause():
    _animation_player.pause()
    return _animation_player.get_status()


@router.post("/animation/stop")
async def animation_stop():
    _animation_player.stop()
    return _animation_player.get_status()


@router.post("/animation/seek")
async def animation_seek(time: float = 0.0):
    _animation_player.seek(time)
    return _animation_player.get_status()


# === Collision System ===

from sparkai.engine.collision_system import get_collision_system, CollisionLayer

_collision_system = get_collision_system()


class RaycastRequest(BaseModel):
    origin_x: float
    origin_y: float
    direction_x: float
    direction_y: float
    max_distance: float = 100.0
    layer_mask: Optional[int] = None


@router.get("/collision/colliders")
async def collision_colliders():
    return {
        "count": len(_collision_system._colliders),
        "layers": [l.name for l in CollisionLayer],
    }


@router.get("/collision/events")
async def collision_events(limit: int = 50):
    return {"events": _collision_system._active_events[-limit:]}


@router.post("/collision/raycast")
async def collision_raycast(req: RaycastRequest):
    from sparkai.engine.collision_system import AABB
    aabb = AABB(req.origin_x, req.origin_y, 0, 0)
    result = _collision_system.raycast(
        aabb, (req.direction_x, req.direction_y),
        req.max_distance, req.layer_mask,
    )
    if result:
        return {"entity_id": result[0], "point": result[1], "distance": result[2]}
    return {"hit": False}


# === Input Manager ===

from sparkai.engine.input_manager import get_input_manager

_input_manager = get_input_manager()


class SimulateKeyRequest(BaseModel):
    key: str
    pressed: bool = True


class SimulateMouseRequest(BaseModel):
    x: float
    y: float
    button: int = 0
    pressed: bool = True


@router.get("/input/snapshot")
async def input_snapshot():
    return _input_manager.get_snapshot()


@router.get("/input/actions")
async def input_actions():
    return {"actions": list(_input_manager._actions.keys())}


@router.post("/input/simulate-key")
async def input_simulate_key(req: SimulateKeyRequest):
    if req.pressed:
        _input_manager.simulate_key_press(req.key)
    else:
        _input_manager.simulate_key_release(req.key)
    return {"key": req.key, "pressed": req.pressed}


@router.post("/input/simulate-mouse")
async def input_simulate_mouse(req: SimulateMouseRequest):
    im = get_input_manager()
    im.simulate_mouse_move(req.x, req.y)
    button_map = {0: "left", 1: "right", 2: "middle"}
    btn = button_map.get(req.button, "left")
    if req.pressed:
        im.simulate_mouse_press(btn)
    else:
        im.simulate_mouse_release(btn)
    return {"x": req.x, "y": req.y, "button": req.button, "pressed": req.pressed}


@router.get("/input/state/{key}")
async def input_key_state(key: str):
    return {
        "key": key,
        "down": _input_manager.is_key_down(key),
        "just_pressed": _input_manager.is_key_just_pressed(key),
        "just_released": _input_manager.is_key_just_released(key),
    }


# === Approval Engine ===

from sparkai.agent.agent_approval_engine import ApprovalEngine, get_approval_engine, TrustTier

_approval_engine = get_approval_engine()


class ApprovalRequest(BaseModel):
    action: str
    level: str = "medium"
    session_id: str = "default"
    context: Optional[Dict[str, Any]] = None


class GrantRequest(BaseModel):
    action: str
    session_id: str = "default"
    tier: str = "medium"
    max_uses: int = 1
    ttl: float = 300.0


class ResolveRequest(BaseModel):
    action: str
    choice: str
    resolve_all: bool = False


@router.get("/approval/stats")
async def approval_stats():
    return _approval_engine.get_stats()


@router.post("/approval/request")
async def approval_request(req: ApprovalRequest):
    return _approval_engine.request_approval(
        action=req.action,
        level=req.level,
        session_id=req.session_id,
        context=req.context,
    )


@router.post("/approval/grant")
async def approval_grant(req: GrantRequest):
    tier = TrustTier(req.tier) if req.tier in [t.value for t in TrustTier] else TrustTier.MEDIUM
    grant = _approval_engine.grant(
        action=req.action,
        session_id=req.session_id,
        tier=tier,
        max_uses=req.max_uses,
        ttl=req.ttl,
    )
    return {
        "action": grant.action,
        "tier": grant.tier.value,
        "expires_at": grant.expires_at,
        "max_uses": grant.max_uses,
    }


@router.post("/approval/deny")
async def approval_deny(action: str, session_id: str = "default"):
    return {"success": _approval_engine.deny(action, session_id)}


@router.get("/approval/pending")
async def approval_pending(session_id: Optional[str] = None):
    return {"pending": _approval_engine.get_pending_approvals(session_id)}


@router.post("/approval/resolve")
async def approval_resolve(req: ResolveRequest):
    resolved = _approval_engine.resolve_pending(req.action, req.choice, req.resolve_all)
    return {"resolved": resolved}


@router.get("/approval/session/{session_id}")
async def approval_session(session_id: str):
    return {
        "approvals": _approval_engine.get_session_approvals(session_id),
        "has_blocking": _approval_engine.has_blocking_approval(session_id),
    }


@router.post("/approval/revoke/{session_id}")
async def approval_revoke(session_id: str):
    return {"revoked_count": _approval_engine.revoke_session(session_id)}


# === Checkpoint Manager ===

from sparkai.agent.agent_checkpoint_manager import CheckpointManager, get_checkpoint_manager

_checkpoint_manager = get_checkpoint_manager()


class CheckpointCreateRequest(BaseModel):
    session_id: str
    state: Any
    reason: str = "api"
    metadata: Optional[Dict[str, Any]] = None


class CheckpointDiffRequest(BaseModel):
    session_id: str
    checkpoint_id: str
    current_state: Any


@router.get("/checkpoints/stats")
async def checkpoints_stats():
    return _checkpoint_manager.get_stats()


@router.post("/checkpoints/create")
async def checkpoints_create(req: CheckpointCreateRequest):
    cid = _checkpoint_manager.create_checkpoint(
        session_id=req.session_id,
        state=req.state,
        reason=req.reason,
        metadata=req.metadata,
    )
    cp = _checkpoint_manager.get_checkpoint(req.session_id, cid)
    return {"checkpoint_id": cid, "detail": cp}


@router.get("/checkpoints/{session_id}")
async def checkpoints_list(session_id: str):
    return {"checkpoints": _checkpoint_manager.list_checkpoints(session_id)}


@router.get("/checkpoints/{session_id}/{checkpoint_id}")
async def checkpoints_get(session_id: str, checkpoint_id: str):
    cp = _checkpoint_manager.get_checkpoint(session_id, checkpoint_id)
    if cp:
        return cp
    return {"error": "Checkpoint not found"}


@router.post("/checkpoints/diff")
async def checkpoints_diff(req: CheckpointDiffRequest):
    delta = _checkpoint_manager.diff_checkpoint(
        req.session_id, req.checkpoint_id, req.current_state,
    )
    return {
        "added": delta.added,
        "modified": delta.modified,
        "removed": delta.removed,
        "key_count": delta.key_count,
    }


@router.post("/checkpoints/rollback/{session_id}/{checkpoint_id}")
async def checkpoints_rollback(session_id: str, checkpoint_id: str):
    data = _checkpoint_manager.rollback(session_id, checkpoint_id)
    if data is not None:
        return {"status": "rolled_back", "checkpoint_id": checkpoint_id}
    return {"error": "Checkpoint not found"}


@router.delete("/checkpoints/{session_id}/{checkpoint_id}")
async def checkpoints_remove(session_id: str, checkpoint_id: str):
    return {"success": _checkpoint_manager.remove_checkpoint(session_id, checkpoint_id)}


@router.delete("/checkpoints/session/{session_id}")
async def checkpoints_remove_session(session_id: str):
    return {"removed": _checkpoint_manager.remove_session(session_id)}


@router.get("/checkpoints/{session_id}/rollback-history")
async def checkpoints_rollback_history(session_id: str):
    return {"history": _checkpoint_manager.get_rollback_history(session_id)}


# === Code Execution Sandbox ===

from sparkai.agent.agent_code_execution import CodeExecutionSandbox, get_code_sandbox, ExecutionMode

_code_sandbox = get_code_sandbox()


class ExecRequest(BaseModel):
    code: str
    mode: str = "safe"
    context: Optional[Dict[str, Any]] = None
    namespace: Optional[str] = None
    timeout_ms: Optional[float] = None


class ValidateRequest(BaseModel):
    code: str


@router.get("/code-exec/stats")
async def code_exec_stats():
    return _code_sandbox.get_stats()


@router.post("/code-exec/execute")
async def code_exec_execute(req: ExecRequest):
    mode = ExecutionMode(req.mode) if req.mode in [m.value for m in ExecutionMode] else ExecutionMode.SAFE
    result = _code_sandbox.execute(
        code=req.code, mode=mode, context=req.context,
        namespace=req.namespace, timeout_ms=req.timeout_ms,
    )
    return {
        "status": result.status.value, "output": result.output,
        "stdout": result.stdout, "stderr": result.stderr,
        "error": result.error, "duration_ms": result.duration_ms,
    }


@router.post("/code-exec/validate")
async def code_exec_validate(req: ValidateRequest):
    return {"violations": _code_sandbox.validate(req.code)}


@router.post("/code-exec/namespace/{name}")
async def code_exec_create_namespace(name: str):
    _code_sandbox.create_namespace(name)
    return {"namespace": name}


@router.delete("/code-exec/namespace/{name}")
async def code_exec_delete_namespace(name: str):
    return {"success": _code_sandbox.delete_namespace(name)}


# === File Safety ===

from sparkai.agent.agent_file_safety import FileSafetyController, get_file_safety

_file_safety = get_file_safety()


class PathCheckRequest(BaseModel):
    path: str


class MultiPathRequest(BaseModel):
    paths: List[str]


@router.get("/file-safety/stats")
async def file_safety_stats():
    return _file_safety.get_stats()


@router.post("/file-safety/check-write")
async def file_safety_check_write(req: PathCheckRequest):
    return {"path": req.path, "allowed": _file_safety.is_write_allowed(req.path)}


@router.post("/file-safety/check-read")
async def file_safety_check_read(req: PathCheckRequest):
    return {"path": req.path, "allowed": _file_safety.is_read_allowed(req.path)}


@router.post("/file-safety/validate-paths")
async def file_safety_validate(req: MultiPathRequest):
    return {"violations": _file_safety.validate_paths(req.paths)}


@router.post("/file-safety/workspace")
async def file_safety_set_workspace(path: str):
    _file_safety.set_workspace(path)
    return {"workspace": path}


# === Guard System ===

from sparkai.agent.agent_guard_system import GuardSystem, get_guard_system, GuardResult

_guard_system = get_guard_system()


@router.get("/guard/stats")
async def guard_stats():
    return _guard_system.get_stats()


@router.post("/guard/scan")
async def guard_scan(path: str, source: str = "community"):
    from pathlib import Path
    result = _guard_system.scan(Path(path), source)
    allowed, reason = _guard_system.evaluate(result)
    return {
        "verdict": result.verdict, "trust_level": result.trust_level,
        "findings_count": len(result.findings),
        "findings": [
            {"id": f.pattern_id, "severity": f.severity, "category": f.category,
             "file": f.file, "line": f.line, "description": f.description}
            for f in result.findings[:50]
        ],
        "allowed": allowed, "reason": reason,
    }


@router.post("/guard/hash")
async def guard_hash(path: str):
    from pathlib import Path
    return {"hash": _guard_system.hash_content(Path(path))}


# === Interrupt System ===

from sparkai.agent.agent_interrupt_system import InterruptSystem, get_interrupt_system

_interrupt_system = get_interrupt_system()


@router.get("/interrupt/stats")
async def interrupt_stats():
    return _interrupt_system.get_stats()


@router.post("/interrupt/sessions/{session_id}")
async def interrupt_register(session_id: str):
    _interrupt_system.register_session(session_id)
    return {"session_id": session_id}


@router.post("/interrupt/{session_id}")
async def interrupt_set(session_id: str, active: bool = True):
    _interrupt_system.set_interrupt(session_id, active)
    return {"session_id": session_id, "interrupted": active}


@router.get("/interrupt/{session_id}")
async def interrupt_check(session_id: str):
    return {"session_id": session_id, "interrupted": _interrupt_system.is_interrupted(session_id)}


@router.get("/interrupt/sessions/active")
async def interrupt_active_sessions():
    return {"sessions": _interrupt_system.get_active_sessions()}


# === Result Storage ===

from sparkai.agent.agent_result_storage import ResultStorage, get_result_storage, ResultEntry

_result_storage = get_result_storage()


class StoreRequest(BaseModel):
    key: str
    value: Any
    ttl: Optional[float] = None
    metadata: Optional[Dict[str, Any]] = None


@router.get("/result-storage/stats")
async def result_storage_stats():
    return _result_storage.get_stats()


@router.post("/result-storage/store")
async def result_storage_store(req: StoreRequest):
    key = _result_storage.store(req.key, req.value, req.ttl, req.metadata)
    return {"key": key}


@router.get("/result-storage/{key}")
async def result_storage_get(key: str):
    entry = _result_storage.retrieve(key)
    if entry:
        return {"key": key, "value": entry.value, "version": entry.version}
    return {"error": "Not found"}


@router.get("/result-storage/exists/{key}")
async def result_storage_exists(key: str):
    return {"key": key, "exists": _result_storage.exists(key)}


@router.delete("/result-storage/{key}")
async def result_storage_delete(key: str):
    return {"success": _result_storage.delete(key)}


# === Physics System ===

from sparkai.engine.physics_system import PhysicsSystem, get_physics_system, BodyType

_physics_system = get_physics_system()


class PhysicsBodyRequest(BaseModel):
    entity_id: str
    mass: float = 1.0
    body_type: str = "dynamic"
    px: float = 0.0
    py: float = 0.0
    vx: float = 0.0
    vy: float = 0.0


class ForceRequest(BaseModel):
    entity_id: str
    fx: float = 0.0
    fy: float = 0.0


@router.get("/physics/stats")
async def physics_stats():
    return _physics_system.get_stats()


@router.post("/physics/body")
async def physics_create_body(req: PhysicsBodyRequest):
    bt = BodyType(req.body_type) if req.body_type in [b.value for b in BodyType] else BodyType.DYNAMIC
    body = _physics_system.create_body(
        req.entity_id, req.mass, bt, (req.px, req.py), (req.vx, req.vy),
    )
    return {"entity_id": body.entity_id, "position": body.position, "velocity": body.velocity}


@router.get("/physics/body/{entity_id}")
async def physics_get_body(entity_id: str):
    body = _physics_system.get_body(entity_id)
    if body:
        return {"entity_id": body.entity_id, "position": body.position, "velocity": body.velocity, "speed": body.speed}
    return {"error": "Not found"}


@router.post("/physics/force")
async def physics_apply_force(req: ForceRequest):
    _physics_system.apply_force(req.entity_id, (req.fx, req.fy))
    return {"entity_id": req.entity_id, "force": (req.fx, req.fy)}


@router.post("/physics/impulse")
async def physics_apply_impulse(req: ForceRequest):
    _physics_system.apply_impulse(req.entity_id, (req.fx, req.fy))
    return {"entity_id": req.entity_id, "impulse": (req.fx, req.fy)}


@router.post("/physics/step")
async def physics_step(dt: float = 0.016):
    _physics_system.step(dt)
    return _physics_system.get_stats()


# === Particle System ===

from sparkai.engine.particle_system import ParticleSystem, get_particle_system, EmitterShape, EmitterMode

_particle_system = get_particle_system()


class EmitterRequest(BaseModel):
    name: str
    emission_rate: float = 100.0
    lifetime: float = 1.0
    speed: float = 100.0
    start_size: float = 10.0
    end_size: float = 0.0


class EmitRequest(BaseModel):
    emitter: str
    x: float = 0.0
    y: float = 0.0
    dx: float = 0.0
    dy: float = -1.0
    count: int = 0


@router.get("/particle/stats")
async def particle_stats():
    return _particle_system.get_stats()


@router.post("/particle/emitter")
async def particle_create_emitter(req: EmitterRequest):
    emitter = _particle_system.create_emitter(
        req.name, emission_rate=req.emission_rate,
        lifetime=req.lifetime, speed=req.speed,
        start_size=req.start_size, end_size=req.end_size,
    )
    return {"name": emitter.name, "active": emitter.active}


@router.post("/particle/emit")
async def particle_emit(req: EmitRequest):
    count = _particle_system.emit(req.emitter, (req.x, req.y), (req.dx, req.dy), req.count)
    return {"emitter": req.emitter, "spawned": count}


@router.post("/particle/update")
async def particle_update(dt: float = 0.016):
    _particle_system.update(dt)
    return {"particles": _particle_system.get_count()}


# === Pathfinding ===

from sparkai.engine.pathfinding_system import PathfindingSystem, get_pathfinding

_pathfinding = get_pathfinding()


class PathRequest(BaseModel):
    sx: int
    sy: int
    gx: int
    gy: int
    diagonal: bool = True


class BlockRequest(BaseModel):
    x: int
    y: int
    blocked: bool = True


@router.get("/pathfinding/stats")
async def pathfinding_stats():
    return _pathfinding.get_stats()


@router.post("/pathfinding/find")
async def pathfinding_find(req: PathRequest):
    path = _pathfinding.find_path((req.sx, req.sy), (req.gx, req.gy), req.diagonal)
    if path:
        return {"path": path, "length": len(path)}
    return {"path": None, "reason": "No path found"}


@router.post("/pathfinding/block")
async def pathfinding_block(req: BlockRequest):
    _pathfinding.set_blocked(req.x, req.y, req.blocked)
    return {"x": req.x, "y": req.y, "blocked": req.blocked}


# === Audio System ===

from sparkai.engine.audio_system import AudioSystem, get_audio_system as get_legacy_audio, AudioChannel

_legacy_audio_system = get_legacy_audio()


@router.get("/audio/stats")
async def audio_stats():
    return _legacy_audio_system.get_stats()


@router.post("/audio/play/{source_id}")
async def audio_play(source_id: str):
    return {"success": _legacy_audio_system.play(source_id)}


@router.post("/audio/stop/{source_id}")
async def audio_stop(source_id: str):
    return {"success": _legacy_audio_system.stop(source_id)}


@router.post("/audio/stop-all")
async def audio_stop_all(channel: Optional[str] = None):
    ch = AudioChannel(channel) if channel else None
    return {"stopped": _legacy_audio_system.stop_all(ch)}


@router.post("/audio/volume/{channel}")
async def audio_set_volume(channel: str, volume: float = 1.0):
    ch = AudioChannel(channel)
    _legacy_audio_system.set_channel_volume(ch, volume)
    return {"channel": channel, "volume": volume}


# === State Machine ===

from sparkai.engine.state_machine import StateMachine, get_state_machine

_default_sm = get_state_machine()


class SMTransitionRequest(BaseModel):
    source: str
    target: str
    priority: int = 0


@router.get("/state-machine/stats")
async def sm_stats():
    return _default_sm.get_stats()


@router.post("/state-machine/start/{state}")
async def sm_start(state: str):
    return {"success": _default_sm.start(state)}


@router.post("/state-machine/go/{state}")
async def sm_go(state: str):
    return {"success": _default_sm.go_to(state)}


@router.get("/state-machine/current")
async def sm_current():
    return {"state": _default_sm.get_state(), "duration": _default_sm.get_state_duration()}


# === Resource Manager ===

from sparkai.engine.resource_manager import ResourceManager, get_resource_manager, ResourceType

_resource_manager = get_resource_manager()


@router.get("/resources/stats")
async def resources_stats():
    return _resource_manager.get_stats()


@router.post("/resources/load")
async def resources_load(resource_id: str, resource_type: str = "custom"):
    rt = ResourceType(resource_type) if resource_type in [r.value for r in ResourceType] else ResourceType.CUSTOM
    from pathlib import Path
    handle = _resource_manager.load(resource_id, rt)
    return {"id": resource_id, "status": handle.status.value}


@router.get("/resources/{resource_id}")
async def resources_get(resource_id: str):
    handle = _resource_manager.get_handle(resource_id)
    if handle:
        return {"id": resource_id, "type": handle.resource_type.value, "status": handle.status.value, "ref_count": handle.ref_count}
    return {"error": "Not found"}


# === Behavior System ===

from sparkai.engine.behavior_system import BehaviorSystem, get_behavior_system

_behavior_system = get_behavior_system()


@router.get("/behavior/stats")
async def behavior_stats():
    return _behavior_system.get_stats()


@router.get("/behavior/entity/{entity_id}")
async def behavior_get(entity_id: str):
    behaviors = _behavior_system.get_behaviors(entity_id)
    return {"entity_id": entity_id, "behaviors": [b.name for b in behaviors]}


# === Tilemap System ===

from sparkai.engine.tilemap_system import TilemapSystem, get_tilemap_system

_tilemap_system = get_tilemap_system()


class TileRequest(BaseModel):
    layer: str
    x: int
    y: int
    tile_id: int = -1
    tileset_id: str = ""


@router.get("/tilemap/stats")
async def tilemap_stats():
    return _tilemap_system.get_stats()


@router.post("/tilemap/tile")
async def tilemap_set_tile(req: TileRequest):
    return {"success": _tilemap_system.set_tile(req.layer, req.x, req.y, req.tile_id, req.tileset_id)}


@router.get("/tilemap/tile/{layer}/{x}/{y}")
async def tilemap_get_tile(layer: str, x: int, y: int):
    tile = _tilemap_system.get_tile(layer, x, y)
    if tile:
        return {"x": x, "y": y, "tile_id": tile.tile_id, "tileset": tile.tileset_id}
    return {"empty": True}


@router.post("/tilemap/layer/{name}")
async def tilemap_add_layer(name: str, collision: bool = False, z: int = 0):
    layer = _tilemap_system.add_layer(name, z_order=z, collision_enabled=collision)
    return {"name": layer.name, "visible": layer.visible}


@router.get("/tilemap/blocked/{layer}")
async def tilemap_blocked(layer: str):
    return {"blocked": _tilemap_system.get_blocked_cells(layer)}


# === Self Evaluator ===

from sparkai.agent.agent_self_evaluator import SelfEvaluator, get_self_evaluator

_evaluator = get_self_evaluator()


class EvaluateRequest(BaseModel):
    content: str = ""
    content_type: str = "game_design"
    metadata: Optional[Dict[str, Any]] = None


@router.get("/self-evaluator/rubrics")
async def evaluator_rubrics():
    return {"rubrics": _evaluator.list_rubric_types()}


@router.post("/self-evaluator/evaluate")
async def evaluator_evaluate(req: EvaluateRequest):
    result = _evaluator.evaluate(req.content, req.content_type, req.metadata)
    return result.to_dict() if hasattr(result, 'to_dict') else {
        "overall_score": result.overall_score,
        "grade": result.overall_grade.value if hasattr(result.overall_grade, 'value') else str(result.overall_grade),
        "dimensions": [
            {"name": d.name, "score": d.score, "weight": d.weight, "evidence": d.evidence}
            for d in result.dimensions
        ] if hasattr(result, 'dimensions') else [],
        "strengths": result.strengths if hasattr(result, 'strengths') else [],
        "weaknesses": result.weaknesses if hasattr(result, 'weaknesses') else [],
        "suggestions": result.suggestions if hasattr(result, 'suggestions') else [],
    }


# === Strategic Planner ===

from sparkai.agent.agent_strategic_planner import StrategicPlanner, get_strategic_planner, ExecutionStrategy, TaskStatus

_planner = get_strategic_planner()


class PlanRequest(BaseModel):
    goal: str
    game_type: str = "2d_platformer"
    max_depth: int = 5
    metadata: Optional[Dict[str, Any]] = None


@router.post("/planner/create-plan")
async def planner_create(req: PlanRequest):
    plan = _planner.create_plan(req.goal, req.game_type, req.max_depth, req.metadata)
    return {
        "plan_id": plan.plan_id,
        "goal": plan.goal,
        "total_tasks": len(plan.tasks),
        "estimated_tokens": plan.estimated_tokens if hasattr(plan, 'estimated_tokens') else 0,
        "tasks": [
            {"id": t.task_id, "name": t.name, "status": t.status.value, "deps": t.dependencies}
            for t in plan.tasks
        ],
        "critical_path": plan.critical_path if hasattr(plan, 'critical_path') else [],
    }


@router.get("/planner/plan/{plan_id}")
async def planner_get(plan_id: str):
    plan = _planner.get_plan(plan_id)
    if not plan:
        return {"error": "Plan not found"}
    return {
        "plan_id": plan.plan_id,
        "goal": plan.goal,
        "progress": plan.progress if hasattr(plan, 'progress') else 0.0,
        "tasks": [
            {"id": t.task_id, "name": t.name, "status": t.status.value, "progress": t.progress if hasattr(t, 'progress') else 0.0}
            for t in plan.tasks
        ],
    }


@router.get("/planner/templates")
async def planner_templates():
    return {"templates": _planner.list_templates()}


# === Circuit Breaker ===

from sparkai.agent.agent_circuit_breaker import CircuitBreaker, get_circuit_breaker

_breaker = get_circuit_breaker()


@router.get("/circuit/stats")
async def circuit_stats():
    return _breaker.get_stats()


@router.post("/circuit/reset")
async def circuit_reset():
    _breaker.reset()
    return {"success": True}


@router.get("/circuit/state")
async def circuit_state():
    return {"state": _breaker.get_state().value, "stats": _breaker.get_stats()}


# === Persona System ===

from sparkai.agent.agent_persona import PersonaSystem, get_persona_system

_personas = get_persona_system()


class PersonaRequest(BaseModel):
    role: str = "game_designer"
    session_id: str = "default"


@router.get("/persona/list")
async def persona_list():
    return {"personas": _personas.list_personas()}


@router.post("/persona/assign")
async def persona_assign(req: PersonaRequest):
    persona = _personas.assign_persona(req.role, req.session_id)
    return {
        "role": persona.display_name,
        "description": persona.role_description,
        "creativity": persona.creativity.value,
        "tools": [t.tool_name for t in persona.tool_grants if t.allowed],
    }


@router.get("/persona/current/{session_id}")
async def persona_current(session_id: str):
    persona = _personas.get_session_persona(session_id)
    if not persona:
        return {"none": True}
    return {"role": persona.display_name, "description": persona.role_description}


# === Camera System ===

from sparkai.engine.camera_system import CameraSystem, get_camera_system, CameraMode

_camera = get_camera_system()


class CameraFollowRequest(BaseModel):
    entity_id: str
    smoothing: float = 0.1
    offset_x: float = 0.0
    offset_y: float = 0.0
    dead_zone_w: float = 0.0
    dead_zone_h: float = 0.0


class CameraShakeRequest(BaseModel):
    intensity: float = 0.5
    duration: float = 0.3
    frequency: float = 30.0
    falloff: str = "linear"


class CameraTransitionRequest(BaseModel):
    x: float = 0.0
    y: float = 0.0
    zoom: float = 1.0
    duration: float = 1.0
    easing: str = "ease_in_out"


@router.get("/camera/stats")
async def camera_stats():
    return _camera.get_stats()


@router.post("/camera/position")
async def camera_position(x: float = 0.0, y: float = 0.0):
    _camera.set_position(x, y)
    return {"x": _camera.x, "y": _camera.y}


@router.get("/camera/current")
async def camera_current():
    return {"x": _camera.x, "y": _camera.y, "zoom": _camera.zoom}


@router.post("/camera/follow")
async def camera_follow(req: CameraFollowRequest):
    _camera.follow(req.entity_id, req.smoothing, req.offset_x, req.offset_y, req.dead_zone_w, req.dead_zone_h)
    return {"following": req.entity_id}


@router.post("/camera/free")
async def camera_free():
    _camera.free_mode()
    return {"mode": "free"}


@router.post("/camera/shake")
async def camera_shake(req: CameraShakeRequest):
    _camera.shake(req.intensity, req.duration, req.frequency, req.falloff)
    return {"shaking": True, "intensity": req.intensity}


@router.post("/camera/stop-shake")
async def camera_stop_shake():
    _camera.stop_shake()
    return {"shaking": False}


@router.post("/camera/zoom")
async def camera_set_zoom(zoom: float = 1.0):
    _camera.set_zoom(zoom)
    return {"zoom": zoom}


@router.post("/camera/bounds")
async def camera_bounds(left: float = 0, top: float = 0, right: float = 1000, bottom: float = 1000):
    _camera.set_bounds(left, top, right, bottom)
    return {"bounds": [left, top, right, bottom]}


@router.post("/camera/transition")
async def camera_transition(req: CameraTransitionRequest):
    _camera.transition_to(req.x, req.y, req.zoom, req.duration, req.easing)
    return {"transitioning": True, "target": [req.x, req.y]}


@router.get("/camera/visible")
async def camera_visible():
    return {"bounds": _camera.get_visible_bounds()}


@router.post("/camera/world-to-screen")
async def camera_world_to_screen(x: float = 0.0, y: float = 0.0):
    sx, sy = _camera.world_to_screen(x, y)
    return {"screen_x": sx, "screen_y": sy}


@router.post("/camera/screen-to-world")
async def camera_screen_to_world(x: float = 0.0, y: float = 0.0):
    wx, wy = _camera.screen_to_world(x, y)
    return {"world_x": wx, "world_y": wy}


# === Serializer ===

from sparkai.engine.serialization import Serializer, get_serializer, SerialFormat

_serializer = get_serializer()


class SerializeRequest(BaseModel):
    data: Any = None
    format: str = "json_readable"


class DeserializeRequest(BaseModel):
    data: str = ""
    validate: bool = True


@router.get("/serializer/info")
async def serializer_info():
    return _serializer.get_schema_info()


@router.get("/serializer/stats")
async def serializer_stats():
    return _serializer.get_stats()


@router.post("/serializer/serialize")
async def serializer_serialize(req: SerializeRequest):
    fmt = SerialFormat.JSON_READABLE
    if req.format == "json_compact":
        fmt = SerialFormat.JSON_COMPACT
    elif req.format == "binary_blob":
        fmt = SerialFormat.BINARY_BLOB
    elif req.format == "yaml_layout":
        return {"result": _serializer.serialize_to_yaml(req.data)}
    result = _serializer.serialize_scene(req.data, format=fmt)
    return {"result": result}


@router.post("/serializer/deserialize")
async def serializer_deserialize(req: DeserializeRequest):
    scene = _serializer.deserialize_scene(req.data, req.validate)
    return {"id": scene.id, "name": scene.name, "entity_count": len(scene.entities)}


# === UI System ===

from sparkai.engine.ui_system import UISystem, get_ui_system

_ui = get_ui_system()


class UICreateWidgetRequest(BaseModel):
    widget_type: str = "label"
    widget_id: str = ""
    text: str = ""
    label: str = ""
    x: float = 0.0
    y: float = 0.0
    w: float = 100.0
    h: float = 24.0
    title: str = ""
    value: float = 0.0
    min_val: float = 0.0
    max_val: float = 1.0
    step: float = 0.01


@router.get("/ui/stats")
async def ui_stats():
    return _ui.get_stats()


@router.get("/ui/widgets")
async def ui_widgets():
    return {"widgets": _ui.get_all_widgets()}


@router.get("/ui/widget/{widget_id}")
async def ui_get_widget(widget_id: str):
    widget = _ui.get_widget(widget_id)
    if not widget:
        return {"error": "Not found"}
    return {"id": widget.id, "type": widget.widget_type, "rect": widget.rect.to_dict(), "visible": widget.visible}


@router.post("/ui/widget/create")
async def ui_create_widget(req: UICreateWidgetRequest):
    if req.widget_type == "label":
        w = _ui.create_label(req.widget_id, req.text or req.label, req.x, req.y, req.w, req.h)
    elif req.widget_type == "button":
        w = _ui.create_button(req.widget_id, req.label or req.text, req.x, req.y, req.w, req.h)
    elif req.widget_type == "panel":
        w = _ui.create_panel(req.widget_id, req.x, req.y, req.w, req.h, req.title)
    elif req.widget_type == "slider":
        w = _ui.create_slider(req.widget_id, req.x, req.y, req.w, req.h, req.value, req.min_val, req.max_val, req.step)
    elif req.widget_type == "progress_bar":
        w = _ui.create_progress_bar(req.widget_id, req.x, req.y, req.w, req.h, req.value, req.max_val)
    else:
        return {"error": f"Unknown widget type: {req.widget_type}"}
    return {"id": w.id, "type": w.widget_type}


@router.delete("/ui/widget/{widget_id}")
async def ui_delete_widget(widget_id: str):
    return {"success": _ui.delete_widget(widget_id)}


@router.post("/ui/widget/{widget_id}/visibility")
async def ui_widget_visibility(widget_id: str, visible: bool = True):
    return {"success": _ui.set_widget_visibility(widget_id, visible)}


@router.post("/ui/widget/{widget_id}/position")
async def ui_widget_position(widget_id: str, x: float = 0.0, y: float = 0.0, w: float = None, h: float = None):
    return {"success": _ui.update_widget_position(widget_id, x, y, w, h)}


@router.get("/ui/theme")
async def ui_theme():
    t = _ui.theme
    return {"name": t.name, "primary": t.primary_color.as_hex(), "bg": t.background_color.as_hex(), "font_size": t.font_size}


# === Layer System ===

from sparkai.engine.layer_system import LayerSystem, get_layer_system, LayerBlendMode

_layers = get_layer_system()


class LayerRequest(BaseModel):
    name: str
    z_index: int = 0
    parallax: float = 1.0
    blend: str = "normal"


@router.get("/layers/stats")
async def layers_stats():
    return _layers.get_stats()


@router.get("/layers/list")
async def layers_list():
    return {"layers": _layers.get_all_layers()}


@router.get("/layers/render")
async def layers_render():
    return {"layers": _layers.get_layers_for_rendering()}


@router.post("/layers/add")
async def layers_add(req: LayerRequest):
    blend = LayerBlendMode.NORMAL
    if req.blend in [b.name.lower() for b in LayerBlendMode]:
        blend = LayerBlendMode[req.blend.upper()]
    layer = _layers.add_layer(req.name, req.z_index, req.parallax, blend)
    return {"id": layer.layer_id, "name": layer.name, "z": layer.z_index}


@router.post("/layers/remove/{layer_id}")
async def layers_remove(layer_id: str):
    return {"success": _layers.remove_layer(layer_id)}


@router.post("/layers/hide/{identifier}")
async def layers_hide(identifier: str):
    return {"success": _layers.hide_layer(identifier)}


@router.post("/layers/show/{identifier}")
async def layers_show(identifier: str):
    return {"success": _layers.show_layer(identifier)}


@router.post("/layers/toggle/{identifier}")
async def layers_toggle(identifier: str):
    return {"visible": _layers.toggle_layer(identifier)}


@router.post("/layers/move-up/{identifier}")
async def layers_move_up(identifier: str):
    return {"success": _layers.move_layer_up(identifier)}


@router.post("/layers/move-down/{identifier}")
async def layers_move_down(identifier: str):
    return {"success": _layers.move_layer_down(identifier)}


@router.post("/layers/z/{identifier}")
async def layers_set_z(identifier: str, z: int = 0):
    return {"success": _layers.set_layer_z_index(identifier, z)}


@router.post("/layers/opacity/{identifier}")
async def layers_opacity(identifier: str, opacity: float = 1.0):
    return {"success": _layers.set_layer_opacity(identifier, opacity)}


@router.post("/layers/parallax/{identifier}")
async def layers_parallax(identifier: str, factor: float = 1.0):
    return {"success": _layers.set_layer_parallax(identifier, factor)}


@router.get("/layers/groups")
async def layers_groups():
    return {"groups": _layers.get_all_groups()}


@router.post("/layers/groups/create")
async def layers_group_create(name: str = "New Group"):
    group = _layers.create_group(name)
    return {"id": group.group_id, "name": group.name}


# === Profiler ===

from sparkai.engine.profiler import Profiler, get_profiler

_profiler = get_profiler()


@router.get("/profiler/snapshot")
async def profiler_snapshot():
    return _profiler.get_snapshot()


@router.get("/profiler/report")
async def profiler_report():
    report = _profiler.generate_report()
    return {
        "report_id": report.report_id,
        "avg_fps": report.avg_fps,
        "min_fps": report.min_fps,
        "max_fps": report.max_fps,
        "avg_frame_ms": report.avg_frame_ms,
        "p95_frame_ms": report.p95_frame_ms,
        "p99_frame_ms": report.p99_frame_ms,
        "one_percent_low_fps": report.one_percent_low_fps,
        "frame_count": report.frame_count,
        "elapsed_seconds": report.elapsed_seconds,
        "phase_averages": report.phase_averages,
        "peak_memory_bytes": report.peak_memory_bytes,
        "current_memory_bytes": report.current_memory_bytes,
        "bottleneck_count": report.bottleneck_count,
        "recommendations": report.recommendations,
        "performance_level": report.performance_level,
    }


@router.get("/profiler/bottlenecks")
async def profiler_bottlenecks(threshold_ms: float = 16.0):
    return {"bottlenecks": _profiler.detect_bottlenecks(threshold_ms)}


@router.get("/profiler/frame-report")
async def profiler_frame_report():
    report = _profiler.get_frame_report()
    return {
        "frame": report.frame_number,
        "total_ms": report.total_ms,
        "fps": report.fps,
        "phases": report.phase_timings,
        "bottleneck": report.bottleneck_level.name,
        "reason": report.bottleneck_reason,
    }


@router.post("/profiler/enable")
async def profiler_enable(enabled: bool = True):
    _profiler.enabled = enabled
    return {"enabled": _profiler.enabled}


@router.post("/profiler/reset")
async def profiler_reset():
    _profiler.reset()
    return {"success": True}


# === Streaming Manager ===

from sparkai.agent.agent_streaming import StreamingManager, get_streaming_manager

_streaming_manager = get_streaming_manager()


@router.get("/streaming/stats")
async def streaming_stats():
    return {"stats": _streaming_manager.get_stats()}


@router.post("/streaming/start")
async def streaming_start():
    _streaming_manager.start()
    return {"state": _streaming_manager.state.name.lower()}


@router.post("/streaming/stop")
async def streaming_stop():
    _streaming_manager.stop()
    return {"state": _streaming_manager.state.name.lower()}


@router.post("/streaming/pause")
async def streaming_pause():
    _streaming_manager.pause()
    return {"state": _streaming_manager.state.name.lower()}


@router.post("/streaming/resume")
async def streaming_resume():
    _streaming_manager.resume()
    return {"state": _streaming_manager.state.name.lower()}


@router.post("/streaming/cancel")
async def streaming_cancel(reason: str = "user_cancelled"):
    _streaming_manager.cancel(reason)
    return {"state": _streaming_manager.state.name.lower()}


@router.get("/streaming/partial")
async def streaming_partial():
    return {"partial": _streaming_manager.get_partial()}


# === Delegation System ===

from sparkai.agent.agent_delegation import DelegationSystem, get_delegation_system

_delegation_system = get_delegation_system()


class DelegationSpawnRequest(BaseModel):
    task: str
    agent_config: Optional[Dict[str, Any]] = None
    timeout: float = 60.0


class DelegationBatchRequest(BaseModel):
    tasks: List[Dict[str, Any]]


@router.get("/delegation/stats")
async def delegation_stats():
    return {"stats": _delegation_system.get_stats()}


@router.post("/delegation/spawn")
async def delegation_spawn(request: DelegationSpawnRequest):
    result = await _delegation_system.spawn(request.task, request.agent_config, request.timeout)
    return result.to_dict()


@router.post("/delegation/batch")
async def delegation_batch(request: DelegationBatchRequest):
    results = await _delegation_system.execute_batch(request.tasks)
    return {"results": [r.to_dict() for r in results], "count": len(results)}


# === MCP Bridge ===

from sparkai.agent.agent_mcp_bridge import MCPBridge, get_mcp_bridge

_mcp_bridge = get_mcp_bridge()


class MCPConnectRequest(BaseModel):
    transport: str = "stdio"
    command: Optional[str] = None
    args: Optional[List[str]] = None
    url: Optional[str] = None
    server_id: str = "default"


class MCPInvokeRequest(BaseModel):
    server_id: str
    tool_name: str
    arguments: Dict[str, Any] = {}


@router.get("/mcp/stats")
async def mcp_stats():
    return {"stats": _mcp_bridge.get_stats()}


@router.get("/mcp/servers")
async def mcp_servers():
    return {"servers": _mcp_bridge.list_servers()}


@router.post("/mcp/connect")
async def mcp_connect(request: MCPConnectRequest):
    transport_map = {"stdio": "stdio", "http": "http_sse", "websocket": "websocket"}
    t = transport_map.get(request.transport, "stdio")
    if t == "stdio" and request.command:
        server = await _mcp_bridge.connect_stdio(request.server_id, request.command, request.args or [])
    elif t == "http_sse" and request.url:
        server = await _mcp_bridge.connect_http(request.server_id, request.url)
    else:
        return {"error": "Invalid transport configuration"}
    return server.to_dict()


@router.post("/mcp/disconnect")
async def mcp_disconnect(server_id: str):
    success = _mcp_bridge.disconnect(server_id)
    return {"success": success}


@router.post("/mcp/invoke")
async def mcp_invoke(request: MCPInvokeRequest):
    result = await _mcp_bridge.invoke(request.server_id, request.tool_name, request.arguments)
    return result.to_dict()


@router.get("/mcp/tools")
async def mcp_tools(server_id: Optional[str] = None):
    if server_id:
        tools = _mcp_bridge.list_tools(server_id)
    else:
        tools = _mcp_bridge.list_all_tools()
    return {"tools": tools, "count": len(tools)}


# === Parallel Executor ===

from sparkai.agent.agent_parallel_executor import ParallelExecutor, get_parallel_executor

_parallel_executor = get_parallel_executor()


class ParallelDispatchRequest(BaseModel):
    tasks: List[Dict[str, Any]]
    max_concurrent: int = 4


@router.get("/parallel/stats")
async def parallel_stats():
    return {"stats": _parallel_executor.get_stats()}


@router.post("/parallel/dispatch")
async def parallel_dispatch(request: ParallelDispatchRequest):
    results = await _parallel_executor.dispatch_batch(request.tasks, request.max_concurrent)
    merged = _parallel_executor.merge_results(results)
    return {"results": [r.to_dict() for r in results], "merged": merged, "count": len(results)}


# === Event Scripting System ===

from sparkai.engine.event_scripting import EventScriptingSystem, get_event_scripting_system

_event_scripting = get_event_scripting_system()


class EventSheetCreateRequest(BaseModel):
    name: str
    events_json: Optional[List[Dict[str, Any]]] = None
    priority: int = 0


@router.get("/event-scripting/stats")
async def event_scripting_stats():
    return {"stats": _event_scripting.get_stats()}


@router.get("/event-scripting/sheets")
async def event_scripting_sheets():
    return {"sheets": _event_scripting.list_sheets()}


@router.post("/event-scripting/sheets/create")
async def event_scripting_create_sheet(request: EventSheetCreateRequest):
    sheet = _event_scripting.create_sheet(request.name, description="")
    if request.events_json:
        _event_scripting.import_sheet_from_json(sheet.sheet_id, request.events_json)
    return sheet.to_dict()


@router.get("/event-scripting/sheets/{sheet_id}")
async def event_scripting_get_sheet(sheet_id: str):
    sheet = _event_scripting.get_sheet(sheet_id)
    if sheet:
        return sheet.to_dict()
    return {"error": f"Sheet '{sheet_id}' not found"}


@router.delete("/event-scripting/sheets/{sheet_id}")
async def event_scripting_delete_sheet(sheet_id: str):
    success = _event_scripting.delete_sheet(sheet_id)
    return {"success": success}


@router.post("/event-scripting/sheets/{sheet_id}/run")
async def event_scripting_run_sheet(sheet_id: str, context: Optional[Dict[str, Any]] = None):
    _event_scripting.run_sheet(sheet_id, 0.016, context or {})
    sheet = _event_scripting.get_sheet(sheet_id)
    return {"executed": sheet is not None}


@router.post("/event-scripting/run-all")
async def event_scripting_run_all(context: Optional[Dict[str, Any]] = None):
    _event_scripting.run_all(0.016, context or {})
    return {"success": True}


# === Scene Tree ===

from sparkai.engine.scene_tree import SceneTree, get_scene_tree

_scene_tree = get_scene_tree()


class SceneNodeCreateRequest(BaseModel):
    name: str
    parent_path: Optional[str] = None
    x: float = 0.0
    y: float = 0.0
    rotation: float = 0.0
    scale_x: float = 1.0
    scale_y: float = 1.0


class ScenePushRequest(BaseModel):
    path_or_name: str


@router.get("/scene-tree/stats")
async def scene_tree_stats():
    return {"stats": _scene_tree.get_stats()}


@router.get("/scene-tree/root")
async def scene_tree_root():
    root = _scene_tree.root
    return root.to_dict() if root else {"error": "No root node"}


@router.post("/scene-tree/nodes/create")
async def scene_tree_create_node(request: SceneNodeCreateRequest):
    parent = None
    if request.parent_path:
        parent = _scene_tree.find_by_path(request.parent_path)
    if not parent:
        parent = _scene_tree.root
    if not parent:
        return {"error": "Root node does not exist"}
    from sparkai.engine.scene_tree import SceneNode
    node = SceneNode(name=request.name)
    node.transform.x = request.x
    node.transform.y = request.y
    node.transform.rotation = request.rotation
    node.transform.scale_x = request.scale_x
    node.transform.scale_y = request.scale_y
    parent.add_child(node)
    return node.to_dict()


@router.get("/scene-tree/nodes/find")
async def scene_tree_find_node(path: str):
    node = _scene_tree.find_by_path(path)
    if node:
        return node.to_dict()
    return {"error": f"Node not found at path '{path}'"}


@router.get("/scene-tree/nodes/by-name")
async def scene_tree_find_by_name(name: str):
    node = _scene_tree.root.find_by_name(name) if _scene_tree.root else None
    if node:
        return node.to_dict()
    return {"error": f"Node '{name}' not found"}


@router.delete("/scene-tree/nodes/remove")
async def scene_tree_remove_node(path: str):
    node = _scene_tree.find_by_path(path)
    if node and node.parent is not None:
        node.parent.remove_child(node.id)
        return {"success": True}
    return {"error": "Cannot remove root node or node not found"}


@router.post("/scene-tree/reparent")
async def scene_tree_reparent(node_path: str, new_parent_path: str):
    node = _scene_tree.find_by_path(node_path)
    new_parent = _scene_tree.find_by_path(new_parent_path)
    if not node or not new_parent:
        return {"error": "Node or parent not found"}
    success = _scene_tree.reparent(node.id, new_parent.id)
    return {"success": success}


@router.get("/scene-tree/groups")
async def scene_tree_groups():
    return {"groups": list(_scene_tree._groups.keys())}


@router.post("/scene-tree/groups/add")
async def scene_tree_group_add(group_name: str, node_path: str):
    node = _scene_tree.find_by_path(node_path)
    if not node:
        return {"error": "Node not found"}
    _scene_tree.add_to_group(node.id, group_name)
    return {"success": True}


@router.get("/scene-tree/groups/{group_name}")
async def scene_tree_group_nodes(group_name: str):
    nodes = _scene_tree.get_group(group_name)
    return {"nodes": [n.to_dict() for n in nodes], "count": len(nodes)}


@router.post("/scene-tree/scene/push")
async def scene_tree_push(request: ScenePushRequest):
    _scene_tree.push_scene(request.path_or_name)
    return {"success": True}


@router.post("/scene-tree/scene/pop")
async def scene_tree_pop():
    _scene_tree.pop_scene()
    return {"success": True}


# === Shader System ===

from sparkai.engine.shader_system import ShaderSystem, get_shader_system

_shader_system = get_shader_system()


class MaterialCreateRequest(BaseModel):
    shader_name: str = "default_sprite"
    name: str = "New Material"


class UniformSetRequest(BaseModel):
    uniform_name: str
    value: Any
    value_type: str = "float"


@router.get("/shader/stats")
async def shader_stats():
    return {"stats": _shader_system.get_stats()}


@router.get("/shader/programs")
async def shader_programs():
    return {"programs": _shader_system.list_shaders()}


@router.get("/shader/programs/{program_name}")
async def shader_program_detail(program_name: str):
    prog = _shader_system.find_shader(program_name)
    if prog:
        return {
            "program_id": prog.program_id,
            "name": prog.name,
            "source_id": prog.source_id,
            "uniform_count": len(prog.uniforms),
            "rendered_count": prog.rendered_count,
            "compiled": prog.compiled,
        }
    return {"error": f"Program '{program_name}' not found"}


@router.post("/shader/materials/create")
async def shader_create_material(request: MaterialCreateRequest):
    material = _shader_system.create_material(request.name, request.shader_name)
    return {
        "material_id": material.material_id,
        "name": material.name,
        "shader_id": material.shader_id,
        "uniforms": material.uniforms,
        "render_queue": material.render_queue,
        "enabled": material.enabled,
    }


@router.get("/shader/materials")
async def shader_materials():
    return {"materials": _shader_system.list_materials()}


@router.post("/shader/materials/{material_id}/uniform")
async def shader_set_uniform(material_id: str, request: UniformSetRequest):
    success = _shader_system.set_sprite_uniform(material_id, request.uniform_name, request.value)
    return {"success": success}


@router.post("/shader/render-passes/add")
async def shader_add_render_pass(name: str, shader_name: str = "default_sprite", order: int = 0):
    rp = _shader_system.add_render_pass(name, shader_name, order)
    return {
        "pass_id": rp.pass_id,
        "name": rp.name,
        "target": rp.target,
        "order": rp.order,
        "enabled": rp.enabled,
    }


@router.get("/shader/render-passes")
async def shader_render_passes():
    passes = _shader_system.get_sorted_passes()
    return {"passes": [{"pass_id": p.pass_id, "name": p.name, "order": p.order, "enabled": p.enabled} for p in passes]}


# === Variable System ===

from sparkai.engine.variable_system import VariableSystem, get_variable_system

_variable_system = get_variable_system()


class VariableSetRequest(BaseModel):
    name: str
    value: Any
    var_type: str = "any"
    scope: str = "global"


class ExpressionEvaluateRequest(BaseModel):
    expression: str
    context: Optional[Dict[str, Any]] = None


@router.get("/variables/stats")
async def variables_stats():
    return {"stats": _variable_system.get_stats()}


@router.get("/variables/list")
async def variables_list(scope: Optional[str] = None):
    if scope:
        st = {"global": "GLOBAL", "scene": "SCENE", "temporary": "TEMPORARY"}.get(scope, "GLOBAL")
        from sparkai.engine.variable_system import Scope
        try:
            sc = Scope[st]
            var_list = _variable_system.get_all(sc)
            return {"variables": var_list, "count": len(var_list), "scope": scope}
        except KeyError:
            return {"error": f"Unknown scope: {scope}"}
    return {"variables": _variable_system.get_all()}


@router.post("/variables/set")
async def variables_set(request: VariableSetRequest):
    scope_map = {"global": "GLOBAL", "scene": "SCENE", "temporary": "TEMPORARY"}
    st = scope_map.get(request.scope, "GLOBAL")
    from sparkai.engine.variable_system import Scope
    try:
        sc = Scope[st]
        _variable_system.set(request.name, request.value, sc)
        return {"success": True, "name": request.name, "scope": request.scope}
    except KeyError:
        return {"error": f"Unknown scope: {request.scope}"}


@router.get("/variables/get")
async def variables_get(name: str, scope: str = "global"):
    scope_map = {"global": "GLOBAL", "scene": "SCENE", "temporary": "TEMPORARY"}
    st = scope_map.get(scope, "GLOBAL")
    from sparkai.engine.variable_system import Scope
    try:
        sc = Scope[st]
        value = _variable_system.get(name, sc)
        return {"name": name, "scope": scope, "value": value}
    except KeyError:
        return {"error": f"Unknown scope: {scope}"}


@router.delete("/variables/remove")
async def variables_remove(name: str, scope: str = "global"):
    scope_map = {"global": "GLOBAL", "scene": "SCENE", "temporary": "TEMPORARY"}
    st = scope_map.get(scope, "GLOBAL")
    from sparkai.engine.variable_system import Scope
    try:
        sc = Scope[st]
        success = _variable_system.remove(name, sc)
        return {"success": success}
    except KeyError:
        return {"error": f"Unknown scope: {scope}"}


@router.post("/variables/evaluate")
async def variables_evaluate(request: ExpressionEvaluateRequest):
    result = _variable_system.evaluate(request.expression, request.context)
    return {"expression": request.expression, "result": result}


@router.post("/variables/increment")
async def variables_increment(name: str, delta: float = 1.0, scope: str = "global"):
    scope_map = {"global": "GLOBAL", "scene": "SCENE", "temporary": "TEMPORARY"}
    st = scope_map.get(scope, "GLOBAL")
    from sparkai.engine.variable_system import Scope
    sc = Scope[st]
    new_val = _variable_system.increment(name, delta, sc)
    return {"name": name, "new_value": new_val}


@router.post("/variables/toggle")
async def variables_toggle(name: str, scope: str = "global"):
    scope_map = {"global": "GLOBAL", "scene": "SCENE", "temporary": "TEMPORARY"}
    st = scope_map.get(scope, "GLOBAL")
    from sparkai.engine.variable_system import Scope
    sc = Scope[st]
    new_val = _variable_system.toggle(name, scope=sc)
    return {"name": name, "new_value": new_val}


@router.get("/variables/history")
async def variables_history(limit: int = 20):
    return {"history": _variable_system.get_history(limit=limit)}


# === Resource Loader ===

from sparkai.engine.resource_loader import ResourceLoader, get_resource_loader

_resource_loader = get_resource_loader()


class ResourceLoadRequest(BaseModel):
    path: str
    resource_type: Optional[str] = None
    priority: int = 0


@router.get("/resource-loader/stats")
async def resource_loader_stats():
    return {"stats": _resource_loader.get_stats()}


@router.post("/resource-loader/load")
async def resource_loader_load(request: ResourceLoadRequest):
    handle = _resource_loader.acquire(request.path)
    if handle:
        return {
            "handle_id": handle.handle_id,
            "path": handle.path,
            "resource_type": handle.resource_type.name.lower(),
            "state": handle.state.name.lower(),
            "ref_count": handle.ref_count,
            "data": str(handle.data)[:100] if handle.data else None,
        }
    return {"error": f"Resource not found: {request.path}"}


@router.post("/resource-loader/release")
async def resource_loader_release(path: str):
    success = _resource_loader.release(path)
    return {"success": success}


@router.get("/resource-loader/cache")
async def resource_loader_cache():
    return {"cache": _resource_loader.get_cache_stats()}


@router.post("/resource-loader/preload")
async def resource_loader_preload(paths: List[str]):
    _resource_loader.preload_batch(paths)
    return {"success": True, "count": len(paths)}


@router.post("/resource-loader/unload")
async def resource_loader_unload(path: str):
    _resource_loader.unload(path)
    return {"success": True}


@router.post("/resource-loader/clear")
async def resource_loader_clear():
    count = _resource_loader.clear_cache()
    return {"cleared": count}


# === Content Safety ===

from sparkai.agent.agent_content_safety import ContentSafety, get_content_safety

_content_safety = get_content_safety()


class ContentScanRequest(BaseModel):
    text: str
    redact: bool = True


@router.get("/content-safety/stats")
async def content_safety_stats():
    return {"stats": _content_safety.get_stats()}


@router.get("/content-safety/rules")
async def content_safety_rules():
    return {"rules": _content_safety.list_rules()}


@router.post("/content-safety/scan")
async def content_safety_scan(request: ContentScanRequest):
    result = _content_safety.scan(request.text, redact=request.redact)
    return result.to_dict()


@router.post("/content-safety/sanitize")
async def content_safety_sanitize(text: str):
    cleaned = _content_safety.sanitize(text)
    return {"sanitized": cleaned}


@router.post("/content-safety/check")
async def content_safety_check(text: str):
    is_safe, violations = _content_safety.is_safe(text)
    return {"safe": is_safe, "violations": violations}


@router.post("/content-safety/rules/toggle")
async def content_safety_toggle_rule(rule_id: str, enabled: bool):
    success = _content_safety.toggle_rule(rule_id, enabled)
    return {"success": success}


# === Title Generator ===

from sparkai.agent.agent_title_generator import TitleGenerator, get_title_generator

_title_generator = get_title_generator()


class TitleGenerateRequest(BaseModel):
    content: str
    style: str = "descriptive"
    max_length: int = 80


class BatchTitleRequest(BaseModel):
    contents: List[str]


@router.get("/title-generator/stats")
async def title_generator_stats():
    return {"stats": _title_generator.get_stats()}


@router.post("/title-generator/generate")
async def title_generator_generate(request: TitleGenerateRequest):
    from sparkai.agent.agent_title_generator import TitleContext
    style_map = {"concise": "CONCISE", "descriptive": "DESCRIPTIVE",
                 "creative": "CREATIVE", "technical": "TECHNICAL"}
    st = style_map.get(request.style, "DESCRIPTIVE")
    from sparkai.agent.agent_title_generator import TitleStyle
    ctx = TitleContext(content=request.content, style=TitleStyle[st],
                       max_length=request.max_length)
    title = _title_generator.generate(ctx)
    return {"title": title}


@router.post("/title-generator/batch")
async def title_generator_batch(request: BatchTitleRequest):
    titles = _title_generator.batch_generate(request.contents)
    return {"titles": titles}


# === Shell Hooks ===

from sparkai.agent.agent_shell_hooks import ShellHookManager, get_shell_hooks

_shell_hooks = get_shell_hooks()


class ShellExecuteRequest(BaseModel):
    command: str
    args: List[str] = []
    cwd: Optional[str] = None
    timeout: float = 30.0


@router.get("/shell-hooks/stats")
async def shell_hooks_stats():
    return {"stats": _shell_hooks.get_stats()}


@router.get("/shell-hooks/allowlist")
async def shell_hooks_allowlist():
    return {"allowlist": _shell_hooks.list_allowlist()}


@router.get("/shell-hooks/denylist")
async def shell_hooks_denylist():
    return {"denylist": _shell_hooks.list_denylist()}


@router.get("/shell-hooks/hooks")
async def shell_hooks_list():
    return {"hooks": _shell_hooks.list_hooks()}


@router.post("/shell-hooks/execute")
async def shell_hooks_execute(request: ShellExecuteRequest):
    from sparkai.agent.agent_shell_hooks import ShellCommand
    cmd = ShellCommand(command=request.command, args=request.args,
                       cwd=request.cwd, timeout=request.timeout)
    result = _shell_hooks.execute(cmd)
    return result.to_dict()


@router.post("/shell-hooks/allowlist/add")
async def shell_hooks_allowlist_add(command: str):
    _shell_hooks.add_to_allowlist(command)
    return {"success": True}


@router.post("/shell-hooks/denylist/add")
async def shell_hooks_denylist_add(command: str):
    _shell_hooks.add_to_denylist(command)
    return {"success": True}


# === Skill Preprocessor ===

from sparkai.agent.agent_skill_preprocessor import SkillPreprocessor, get_skill_preprocessor

_skill_preprocessor = get_skill_preprocessor()


class SkillValidateRequest(BaseModel):
    skill_id: str
    params: Dict[str, Any] = {}


class SkillRegisterRequest(BaseModel):
    skill_id: str
    name: str
    description: str = ""
    category: str = "general"


@router.get("/skill-preprocessor/stats")
async def skill_preprocessor_stats():
    return {"stats": _skill_preprocessor.get_stats()}


@router.get("/skill-preprocessor/skills")
async def skill_preprocessor_skills():
    return {"skills": _skill_preprocessor.list_skills()}


@router.post("/skill-preprocessor/validate")
async def skill_preprocessor_validate(request: SkillValidateRequest):
    report = _skill_preprocessor.validate(request.skill_id, request.params)
    return report.to_dict()


@router.post("/skill-preprocessor/prepare")
async def skill_preprocessor_prepare(request: SkillValidateRequest):
    ok, normalized, errors = _skill_preprocessor.prepare_context(
        request.skill_id, request.params)
    return {"success": ok, "normalized_params": normalized, "errors": errors}


# === Inventory System ===

from sparkai.engine.inventory_system import InventorySystem, get_inventory_system

_inventory_system = get_inventory_system()


class InventoryCreateRequest(BaseModel):
    owner_id: str
    max_slots: int = 20
    max_weight: float = 100.0


class ItemCreateRequest(BaseModel):
    name: str
    category: str = "misc"
    rarity: str = "common"


class ItemTransferRequest(BaseModel):
    source_id: str
    target_id: str
    item_id: str
    quantity: int = 1


@router.get("/inventory/stats")
async def inventory_stats():
    return {"stats": _inventory_system.get_stats()}


@router.post("/inventory/create")
async def inventory_create(request: InventoryCreateRequest):
    inv = _inventory_system.create_inventory(request.owner_id,
                                              request.max_slots, request.max_weight)
    return inv.to_dict()


@router.get("/inventory/{owner_id}")
async def inventory_get(owner_id: str):
    inv = _inventory_system.get_inventory(owner_id)
    if inv:
        return inv.to_dict()
    return {"error": f"Inventory for '{owner_id}' not found"}


@router.post("/inventory/{owner_id}/add")
async def inventory_add_item(owner_id: str, item_id: str, quantity: int = 1):
    inv = _inventory_system.get_or_create_inventory(owner_id)
    item = _inventory_system.get_item_definition(item_id)
    if not item:
        return {"error": f"Item '{item_id}' not found"}
    added, remaining = inv.add_item(item, quantity)
    return {"added": added, "remaining": remaining}


@router.delete("/inventory/{owner_id}/remove")
async def inventory_remove_item(owner_id: str, item_id: str, quantity: int = 1):
    inv = _inventory_system.get_inventory(owner_id)
    if not inv:
        return {"error": f"Inventory '{owner_id}' not found"}
    removed, complete = inv.remove_item(item_id, quantity)
    return {"removed": removed, "completely_removed": complete}


@router.post("/inventory/{owner_id}/equip")
async def inventory_equip(owner_id: str, item_id: str):
    inv = _inventory_system.get_inventory(owner_id)
    if not inv:
        return {"error": f"Inventory '{owner_id}' not found"}
    success = inv.equip(item_id)
    return {"success": success}


@router.post("/inventory/transfer")
async def inventory_transfer(request: ItemTransferRequest):
    result = _inventory_system.transfer(request.source_id, request.target_id,
                                         request.item_id, request.quantity)
    return result.to_dict()


@router.post("/inventory/items/register")
async def inventory_register_item(request: ItemCreateRequest):
    from sparkai.engine.inventory_system import ItemCategory, ItemRarity
    cat_map = {"weapon": "WEAPON", "armor": "ARMOR", "consumable": "CONSUMABLE",
               "key": "KEY_ITEM", "material": "MATERIAL", "quest": "QUEST_ITEM",
               "tool": "TOOL", "cosmetic": "COSMETIC", "misc": "MISC"}
    rar_map = {"common": "COMMON", "uncommon": "UNCOMMON", "rare": "RARE",
               "epic": "EPIC", "legendary": "LEGENDARY", "mythic": "MYTHIC"}
    cat = ItemCategory[cat_map.get(request.category, "MISC")]
    rar = ItemRarity[rar_map.get(request.rarity, "COMMON")]
    item = _inventory_system.create_item(request.name, cat, rar)
    return item.to_dict()


@router.get("/inventory/items/list")
async def inventory_items_list(category: Optional[str] = None):
    from sparkai.engine.inventory_system import ItemCategory
    cat_filter = None
    if category:
        try:
            cat_filter = ItemCategory[category.upper()]
        except KeyError:
            pass
    return {"items": _inventory_system.list_registered_items(cat_filter)}


# === Localization System ===

from sparkai.engine.localization_system import LocalizationSystem, get_localization_system

_localization_system = get_localization_system()


class LocaleStringRequest(BaseModel):
    key: str
    text: str
    language: Optional[str] = None
    category: str = "general"


class LocaleBulkRequest(BaseModel):
    entries: Dict[str, str]
    language: Optional[str] = None


class LocaleGetRequest(BaseModel):
    key: str
    variables: Optional[Dict[str, Any]] = None
    fallback: Optional[str] = None


@router.get("/localization/stats")
async def localization_stats():
    return {"stats": _localization_system.get_stats()}


@router.get("/localization/languages")
async def localization_languages():
    return {"languages": _localization_system.get_supported_languages()}


@router.get("/localization/current")
async def localization_current():
    return _localization_system.get_current_language_info()


@router.post("/localization/language/set")
async def localization_set_language(language: str):
    from sparkai.engine.localization_system import Language
    try:
        lang = Language[language.upper()]
        _localization_system.set_language(lang)
        return {"success": True, "language": lang.iso_code}
    except KeyError:
        return {"error": f"Unknown language: {language}"}


@router.get("/localization/string")
async def localization_get_string(key: str, variables: Optional[str] = None,
                                   fallback_text: Optional[str] = None):
    import json
    vars_dict = json.loads(variables) if variables else None
    text = _localization_system.get_string(key, variables=vars_dict, fallback_text=fallback_text)
    return {"key": key, "text": text}


@router.post("/localization/string/add")
async def localization_add_string(request: LocaleStringRequest):
    _localization_system.add_string(request.key, request.text,
                                     language=request.language, category=request.category)
    return {"success": True}


@router.post("/localization/bulk/add")
async def localization_bulk_add(request: LocaleBulkRequest):
    _localization_system.add_bulk(request.entries, language=request.language)
    return {"success": True, "count": len(request.entries)}


@router.get("/localization/missing")
async def localization_missing(language: Optional[str] = None):
    missing = _localization_system.get_missing_translations(language)
    return {"missing": missing, "count": len(missing)}


@router.get("/localization/export")
async def localization_export(language: Optional[str] = None):
    return {"json": _localization_system.export_json(language)}


@router.post("/localization/import")
async def localization_import(json_str: str, language: Optional[str] = None):
    count = _localization_system.import_json(json_str, language)
    return {"imported": count}


# === Achievement System ===

from sparkai.engine.achievement_system import AchievementSystem, get_achievement_system

_achievement_system = get_achievement_system()


class AchievementStatUpdate(BaseModel):
    stat_name: str
    value: float


class AchievementIncrement(BaseModel):
    stat_name: str
    amount: float = 1.0


@router.get("/achievement/stats")
async def achievement_stats():
    return {"stats": _achievement_system.get_stats()}


@router.get("/achievement/list")
async def achievement_list(owner_id: Optional[str] = None):
    if owner_id:
        achievements = _achievement_system.get_visible_achievements(owner_id)
    else:
        achievements = [a.to_dict() for a in _achievement_system.get_all_achievements()]
    return {"achievements": achievements}


@router.get("/achievement/summary")
async def achievement_summary(owner_id: str):
    return _achievement_system.get_unlock_summary(owner_id)


@router.post("/achievement/stat/update")
async def achievement_stat_update(owner_id: str, stat_name: str, value: float):
    unlocked = _achievement_system.update_stat(owner_id, stat_name, value)
    return {"newly_unlocked": [a.to_dict() for a in unlocked], "count": len(unlocked)}


@router.post("/achievement/stat/increment")
async def achievement_stat_increment(owner_id: str, stat_name: str, amount: float = 1.0):
    unlocked = _achievement_system.increment_stat(owner_id, stat_name, amount)
    return {"newly_unlocked": [a.to_dict() for a in unlocked], "count": len(unlocked)}


@router.post("/achievement/check")
async def achievement_check(owner_id: str):
    unlocked = _achievement_system.check_achievements(owner_id)
    return {"newly_unlocked": [a.to_dict() for a in unlocked], "count": len(unlocked)}


@router.get("/achievement/unlocked")
async def achievement_unlocked(owner_id: str):
    unlocked_list = _achievement_system.get_unlocked_achievements(owner_id)
    return {"unlocked": [a.to_dict() for a in unlocked_list]}


@router.post("/achievement/rewards/grant")
async def achievement_grant_rewards(owner_id: str, achievement_id: str):
    result = _achievement_system.grant_rewards(owner_id, achievement_id)
    return result


# === Cloud Sync ===

from sparkai.engine.cloud_sync import CloudSync, get_cloud_sync

_cloud_sync = get_cloud_sync()


class CloudSaveCreate(BaseModel):
    owner_id: str
    game_id: str
    data: Dict[str, Any]
    slot_name: str = "auto"


class CloudSaveUpdate(BaseModel):
    save_id: str
    data: Dict[str, Any]


@router.get("/cloud-sync/stats")
async def cloud_sync_stats():
    return {"stats": _cloud_sync.get_stats()}


@router.post("/cloud-sync/save/create")
async def cloud_sync_create_save(request: CloudSaveCreate):
    save = _cloud_sync.create_save(request.owner_id, request.game_id,
                                    request.data, request.slot_name)
    return save.to_summary()


@router.get("/cloud-sync/saves/list")
async def cloud_sync_list_saves(owner_id: Optional[str] = None, game_id: Optional[str] = None):
    saves = _cloud_sync.list_local_saves(owner_id=owner_id, game_id=game_id)
    return {"saves": [s.to_summary() for s in saves]}


@router.post("/cloud-sync/push")
async def cloud_sync_push(save_id: str):
    result = _cloud_sync.push(save_id)
    return result.to_dict()


@router.post("/cloud-sync/pull")
async def cloud_sync_pull(save_id: str):
    result = _cloud_sync.pull(save_id)
    return result.to_dict()


@router.post("/cloud-sync/sync")
async def cloud_sync_sync(save_id: str):
    result = _cloud_sync.sync(save_id)
    return result.to_dict()


@router.post("/cloud-sync/resolve")
async def cloud_sync_resolve(save_id: str, choose_local: bool = False):
    success = _cloud_sync.resolve_conflict(save_id, choose_local=choose_local)
    return {"success": success}


@router.post("/cloud-sync/save/update")
async def cloud_sync_update_local(request: CloudSaveUpdate):
    success = _cloud_sync.update_local_save(request.save_id, request.data)
    return {"success": success}


@router.get("/cloud-sync/queue")
async def cloud_sync_queue():
    return {"queue_size": _cloud_sync.get_queue_size()}


# === Rate Limiter ===

from sparkai.agent.agent_rate_limiter import RateLimiter, LimitStrategy, get_rate_limiter

_rate_limiter = get_rate_limiter()
_rate_limiter.register_defaults()


class RateLimitCheckRequest(BaseModel):
    endpoint: str
    request_id: str = ""
    tokens: int = 1


@router.get("/rate-limiter/stats")
async def rate_limiter_stats():
    return {"stats": _rate_limiter.get_stats()}


@router.post("/rate-limiter/check")
async def rate_limiter_check(request: RateLimitCheckRequest):
    allowed, detail = _rate_limiter.allow(request.endpoint, request.request_id, request.tokens)
    remaining = _rate_limiter.get_remaining(request.endpoint)
    return {"allowed": allowed, "detail": detail, "remaining": remaining, "endpoint": request.endpoint}


@router.post("/rate-limiter/release")
async def rate_limiter_release(endpoint: str, request_id: str):
    _rate_limiter.release(endpoint, request_id)
    return {"success": True, "endpoint": endpoint}


# === Retry System ===

from sparkai.agent.agent_retry_system import RetrySystem, RetryStrategy, get_retry_system

_retry_system = get_retry_system()
_retry_system.register_defaults()


@router.get("/retry-system/stats")
async def retry_system_stats():
    return {"stats": _retry_system.get_stats()}


@router.get("/retry-system/circuit")
async def retry_system_circuit_stats(operation: str = "default"):
    state = _retry_system.get_circuit_state(operation)
    return {"operation": operation, "circuit_state": state}


@router.get("/retry-system/operations")
async def retry_system_operations():
    return {"operations": _retry_system.list_operations()}


@router.post("/retry-system/reset")
async def retry_system_reset():
    _retry_system.reset()
    return {"success": True}


# === Web Browser ===

from sparkai.agent.agent_web_browser import WebBrowser, FetchMethod, get_web_browser

_web_browser = get_web_browser()


class WebFetchRequest(BaseModel):
    url: str
    timeout: Optional[float] = None
    bypass_cache: bool = False


@router.get("/web-browser/stats")
async def web_browser_stats():
    return {"stats": _web_browser.get_stats()}


@router.post("/web-browser/fetch")
async def web_browser_fetch(request: WebFetchRequest):
    result = _web_browser.fetch(request.url, timeout=request.timeout, bypass_cache=request.bypass_cache)
    return result.to_dict()


@router.post("/web-browser/fetch-text")
async def web_browser_fetch_text(url: str, timeout: Optional[float] = None):
    text = _web_browser.fetch_text(url, timeout=timeout)
    return {"url": url, "text": text[:5000] if text else None}


@router.get("/web-browser/allowlist")
async def web_browser_allowlist():
    stats = _web_browser.get_stats()
    return {"allowed_domains": stats.get("allowed_domains", 0), "denied_domains": stats.get("denied_domains", 0)}


# === Session Search ===

from sparkai.agent.agent_session_search import SessionSearch, SearchScope, SearchQuery, get_session_search

_session_search = get_session_search()


class SessionSearchRequest(BaseModel):
    query: str
    scope: str = "all"
    session_id: Optional[str] = None
    agent_id: Optional[str] = None
    limit: int = 20
    case_sensitive: bool = False


@router.get("/session-search/stats")
async def session_search_stats():
    return {"stats": _session_search.get_stats()}


@router.post("/session-search/search")
async def session_search_query(request: SessionSearchRequest):
    try:
        scope = SearchScope[request.scope.upper()]
    except KeyError:
        scope = SearchScope.ALL
    q = SearchQuery(
        text=request.query,
        scope=scope,
        session_id=request.session_id,
        agent_id=request.agent_id,
        max_results=request.limit,
        case_sensitive=request.case_sensitive,
    )
    results = _session_search.search(q)
    return {"results": [r.to_dict() for r in results], "query": request.query}


@router.post("/session-search/quick")
async def session_search_quick(query: str, limit: int = 10):
    results = _session_search.quick_search(query, limit)
    return {"results": results, "query": query}


@router.post("/session-search/index")
async def session_search_index(session_id: str, title: str = "", content: str = "", agent_id: str = ""):
    _session_search.index_session(session_id, title=title, messages=[content] if content else None, agent_id=agent_id)
    return {"success": True, "session_id": session_id}


# === Object Pool System ===

from sparkai.engine.object_pool import ObjectPoolSystem, PoolConfig, get_object_pool_system

_object_pool_system = get_object_pool_system()


@router.get("/object-pool/stats")
async def object_pool_stats():
    return {"stats": _object_pool_system.get_stats()}


@router.get("/object-pool/list")
async def object_pool_list():
    return {"pools": _object_pool_system.list_pools()}


@router.post("/object-pool/shrink")
async def object_pool_shrink():
    result = _object_pool_system.shrink_all()
    return {"shrunk": result}


# === Lighting System ===

from sparkai.engine.lighting_system import LightingSystem, LightType, get_lighting_system

_lighting_system = get_lighting_system()


@router.get("/lighting/stats")
async def lighting_stats():
    return {"stats": _lighting_system.get_stats()}


@router.get("/lighting/lights")
async def lighting_list_lights():
    lights = _lighting_system.list_lights()
    return {"lights": [l.to_dict() for l in lights]}


@router.post("/lighting/light/create")
async def lighting_create_light(
    name: str = "Light",
    light_type: str = "POINT",
    x: float = 0.0,
    y: float = 0.0,
    intensity: float = 1.0,
    radius: float = 200.0,
):
    try:
        lt = LightType[light_type]
    except KeyError:
        lt = LightType.POINT
    light = _lighting_system.create_light(
        name=name, light_type=lt, position=(x, y),
        intensity=intensity, radius=radius,
    )
    return light.to_dict()


@router.post("/lighting/light/position")
async def lighting_set_position(light_id: str, x: float = 0.0, y: float = 0.0):
    success = _lighting_system.set_light_position(light_id, x, y)
    return {"success": success}


@router.post("/lighting/light/enable")
async def lighting_set_enabled(light_id: str, enabled: bool = True):
    success = _lighting_system.set_light_enabled(light_id, enabled)
    return {"success": success}


@router.delete("/lighting/light/remove")
async def lighting_remove_light(light_id: str):
    success = _lighting_system.remove_light(light_id)
    return {"success": success}


@router.post("/lighting/ambient")
async def lighting_set_ambient(r: float = 0.1, g: float = 0.1, b: float = 0.15, intensity: float = 0.3):
    _lighting_system.set_ambient((r, g, b, 1.0), intensity)
    return {"success": True}


@router.post("/lighting/enabled")
async def lighting_toggle(enabled: bool = True):
    _lighting_system.set_enabled(enabled)
    return {"enabled": enabled}


# === Font System ===

from sparkai.engine.font_system import FontSystem, TextStyle, FontWeight, FontType, get_font_system

_font_system = get_font_system()


@router.get("/font/stats")
async def font_stats():
    return {"stats": _font_system.get_stats()}


@router.get("/font/list")
async def font_list():
    fonts = _font_system.list_fonts()
    return {"fonts": [f.to_dict() for f in fonts]}


@router.post("/font/create")
async def font_create(
    name: str = "Font",
    family: str = "sans-serif",
    weight: str = "REGULAR",
    default_size: float = 16.0,
):
    try:
        fw = FontWeight[weight]
    except KeyError:
        fw = FontWeight.REGULAR
    font = _font_system.create_font(name=name, family=family, weight=fw, default_size=default_size)
    return font.to_dict()


@router.get("/font/default")
async def font_default():
    font_id = _font_system.get_default_font_id()
    return {"default_font_id": font_id}


class FontMeasureRequest(BaseModel):
    text: str
    font_id: str = ""
    font_size: float = 16.0
    max_width: Optional[float] = None
    alignment: str = "left"


@router.post("/font/measure")
async def font_measure(request: FontMeasureRequest):
    from sparkai.engine.font_system import TextAlignment
    try:
        alignment = TextAlignment(request.alignment)
    except ValueError:
        alignment = TextAlignment.LEFT
    font_id = request.font_id or _font_system.get_default_font_id()
    style = TextStyle(font_id=font_id, font_size=request.font_size,
                       max_width=request.max_width, alignment=alignment)
    block = _font_system.measure_text(request.text, style)
    return block.to_dict()


@router.post("/font/wrap")
async def font_wrap(text: str, font_id: str = "", font_size: float = 16.0, max_width: Optional[float] = None):
    font_id = font_id or _font_system.get_default_font_id()
    style = TextStyle(font_id=font_id, font_size=font_size, max_width=max_width)
    lines = _font_system.wrap_text(text, style)
    return {"lines": lines}


# === Plugin System ===

from sparkai.engine.plugin_system import PluginSystem, PluginState, PluginManifest, get_plugin_system

_plugin_system = get_plugin_system()


@router.get("/plugin/stats")
async def plugin_stats():
    return {"stats": _plugin_system.get_stats()}


@router.get("/plugin/list")
async def plugin_list():
    return {"plugins": _plugin_system.list_plugins()}


@router.get("/plugin/active")
async def plugin_active():
    return {"active": _plugin_system.list_active_plugins()}


class PluginDiscoverRequest(BaseModel):
    name: str
    version: str = "1.0.0"
    author: str = ""
    description: str = ""
    dependencies: List[str] = []
    hooks: List[str] = []
    permissions: List[str] = []
    entry_point: str = ""


@router.post("/plugin/discover")
async def plugin_discover(request: PluginDiscoverRequest):
    manifest = _plugin_system.discover_manifest(request.dict())
    _plugin_system.register_plugin(manifest)
    return manifest.to_dict()


@router.post("/plugin/load")
async def plugin_load(plugin_id: str):
    success = _plugin_system.load_plugin(plugin_id)
    return {"success": success, "plugin_id": plugin_id}


@router.post("/plugin/activate")
async def plugin_activate(plugin_id: str):
    success = _plugin_system.activate_plugin(plugin_id)
    return {"success": success, "plugin_id": plugin_id}


@router.post("/plugin/deactivate")
async def plugin_deactivate(plugin_id: str):
    success = _plugin_system.deactivate_plugin(plugin_id)
    return {"success": success, "plugin_id": plugin_id}


@router.post("/plugin/unload")
async def plugin_unload(plugin_id: str):
    success = _plugin_system.unload_plugin(plugin_id)
    return {"success": success, "plugin_id": plugin_id}


@router.get("/plugin/validate")
async def plugin_validate(plugin_id: str):
    missing = _plugin_system.validate_dependencies(plugin_id)
    return {"valid": len(missing) == 0, "missing_dependencies": missing}


@router.get("/plugin/hooks")
async def plugin_hooks(hook_name: Optional[str] = None):
    hooks = _plugin_system._registry.list_hooks(hook_name)
    return {"hooks": hooks}


# === Observability ===

from sparkai.agent.agent_observability import ObservabilitySystem, SpanKind, LogLevel, get_observability

_observability = get_observability()


@router.get("/observability/stats")
async def observability_stats():
    return {"stats": _observability.get_stats()}


@router.get("/observability/metrics")
async def observability_metrics():
    return {"metrics": _observability.get_metric_snapshot()}


@router.get("/observability/traces")
async def observability_traces(limit: int = 50):
    traces = _observability.get_recent_traces(limit)
    return {"traces": traces}


@router.get("/observability/logs")
async def observability_logs(limit: int = 100, level: Optional[str] = None):
    try:
        log_level = LogLevel[level.upper()] if level else None
    except (KeyError, AttributeError):
        log_level = None
    logs = _observability.get_recent_logs(limit, log_level)
    return {"logs": [l.to_dict() for l in logs]}


@router.post("/observability/enabled")
async def observability_toggle(enabled: bool = True):
    _observability.set_enabled(enabled)
    return {"enabled": enabled}


# === Output Limiter ===

from sparkai.agent.agent_output_limiter import OutputLimiter, LimitPolicy, get_output_limiter

_output_limiter = get_output_limiter()


class LimitContentRequest(BaseModel):
    content: str
    content_type: str = "text"


@router.get("/output-limiter/stats")
async def output_limiter_stats():
    return {"stats": _output_limiter.get_stats()}


@router.post("/output-limiter/limit")
async def output_limiter_limit(request: LimitContentRequest):
    result = _output_limiter.limit(request.content, request.content_type)
    return result.to_dict()


# === Context Engine ===

from sparkai.agent.agent_context_engine import ContextEngine, ContextStrategy, MessageRole, get_context_engine

_context_engine = get_context_engine()


@router.get("/context-engine/stats")
async def context_engine_stats():
    return {"stats": _context_engine.get_stats()}


@router.post("/context-engine/window/create")
async def context_window_create(session_id: str, max_tokens: int = 8000, strategy: str = "HYBRID"):
    try:
        strat = ContextStrategy[strategy]
    except KeyError:
        strat = ContextStrategy.HYBRID
    window = _context_engine.create_window(session_id, max_tokens, strat)
    return window.to_dict()


@router.post("/context-engine/window/add")
async def context_window_add(window_id: str, role: str = "user", content: str = "", importance: float = 0.5):
    try:
        r = MessageRole[role.upper()]
    except KeyError:
        r = MessageRole.USER
    msg = _context_engine.add_message(window_id, r, content, importance)
    return msg.to_dict() if msg else None


@router.get("/context-engine/window/messages")
async def context_window_messages(window_id: str):
    messages = _context_engine.get_messages_for_llm(window_id)
    return {"messages": messages, "count": len(messages)}


# === Skill Discovery ===

from sparkai.agent.agent_skill_discovery import SkillDiscovery, CapabilityDomain, get_skill_discovery

_skill_discovery = get_skill_discovery()


@router.get("/skill-discovery/stats")
async def skill_discovery_stats():
    return {"stats": _skill_discovery.get_stats()}


@router.get("/skill-discovery/discover")
async def skill_discovery_search(query: str = "", domain: Optional[str] = None):
    try:
        dom = CapabilityDomain[domain.upper()] if domain else None
    except (KeyError, AttributeError):
        dom = None
    skills = _skill_discovery.discover(query, dom)
    return {"skills": [s.to_dict() for s in skills], "count": len(skills)}


@router.get("/skill-discovery/domains")
async def skill_discovery_domains():
    return {"domains": _skill_discovery.list_domains()}


@router.get("/skill-discovery/tags")
async def skill_discovery_tags():
    return {"tags": _skill_discovery.list_tags()}


@router.get("/skill-discovery/context")
async def skill_discovery_context(domain: Optional[str] = None):
    try:
        dom = CapabilityDomain[domain.upper()] if domain else None
    except (KeyError, AttributeError):
        dom = None
    ctx = _skill_discovery.get_for_llm_context(dom)
    return {"context": ctx}


# === Effects System ===

from sparkai.engine.effects_system import EffectsSystem, EffectType, EffectBlend, EffectConfig, get_effects_system

_effects_system = get_effects_system()


@router.get("/effects/stats")
async def effects_stats():
    return {"stats": _effects_system.get_stats()}


@router.get("/effects/stacks")
async def effects_stacks():
    stacks = _effects_system.list_stacks()
    return {"stacks": [s.to_dict() for s in stacks]}


@router.post("/effects/stack/create")
async def effects_stack_create(name: str = "Stack", target_id: str = "", target_type: str = "layer"):
    stack = _effects_system.create_stack(name, target_id, target_type)
    return stack.to_dict()


@router.post("/effects/add")
async def effects_add(stack_id: str, preset_name: str = "bloom_soft"):
    instance = _effects_system.add_effect_by_preset(stack_id, preset_name)
    return instance.to_dict() if instance else {"error": "Preset not found"}


@router.post("/effects/toggle")
async def effects_toggle(stack_id: str, instance_id: str, enabled: bool = True):
    success = _effects_system.set_effect_enabled(stack_id, instance_id, enabled)
    return {"success": success}


@router.post("/effects/intensity")
async def effects_intensity(stack_id: str, instance_id: str, intensity: float = 1.0):
    success = _effects_system.set_effect_intensity(stack_id, instance_id, intensity)
    return {"success": success}


@router.get("/effects/presets")
async def effects_presets():
    return {"presets": _effects_system.list_presets()}


# === Input Mapping ===

from sparkai.engine.input_mapping import InputMappingSystem, InputDevice, get_input_mapping

_input_mapping = get_input_mapping()


@router.get("/input-mapping/stats")
async def input_mapping_stats():
    return {"stats": _input_mapping.get_stats()}


@router.get("/input-mapping/contexts")
async def input_mapping_contexts():
    return {"contexts": [c.to_dict() for c in _input_mapping.list_contexts()]}


@router.post("/input-mapping/context/create")
async def input_mapping_context_create(name: str = "Context", priority: int = 0):
    ctx = _input_mapping.create_context(name, priority)
    return ctx.to_dict()


@router.get("/input-mapping/bindings")
async def input_mapping_bindings(context_id: Optional[str] = None):
    bindings = _input_mapping.list_bindings(context_id)
    return {"bindings": [b.to_dict() for b in bindings]}


@router.get("/input-mapping/actions")
async def input_mapping_actions():
    actions = list(_input_mapping._action_states.keys()) or [
        "move_up", "move_down", "move_left", "move_right", "jump", "interact", "pause"
    ]
    return {"actions": actions}


# === Undo/Redo System ===

from sparkai.engine.undo_redo_system import UndoRedoSystem, CommandTarget, get_undo_redo_system

_undo_redo_system = get_undo_redo_system()


@router.get("/undo-redo/stats")
async def undo_redo_stats():
    return {"stats": _undo_redo_system.get_stats()}


@router.post("/undo-redo/undo")
async def undo_redo_undo():
    cmd = _undo_redo_system.undo()
    return {"command": cmd.to_dict() if cmd else None, "can_undo": _undo_redo_system.can_undo()}


@router.post("/undo-redo/redo")
async def undo_redo_redo():
    cmd = _undo_redo_system.redo()
    return {"command": cmd.to_dict() if cmd else None, "can_redo": _undo_redo_system.can_redo()}


@router.get("/undo-redo/state")
async def undo_redo_state():
    return {
        "can_undo": _undo_redo_system.can_undo(),
        "can_redo": _undo_redo_system.can_redo(),
        "undo_label": _undo_redo_system.get_undo_label(),
        "redo_label": _undo_redo_system.get_redo_label(),
    }


@router.post("/undo-redo/clear")
async def undo_redo_clear():
    _undo_redo_system.clear_history()
    return {"success": True}


# === Sprite Sheet ===

from sparkai.engine.sprite_sheet import SpriteSheetSystem, SheetLayout, LoopMode, get_sprite_sheet_system

_sprite_sheet = get_sprite_sheet_system()


@router.get("/sprite-sheet/stats")
async def sprite_sheet_stats():
    return {"stats": _sprite_sheet.get_stats()}


@router.get("/sprite-sheet/list")
async def sprite_sheet_list():
    sheets = _sprite_sheet.list_sheets()
    return {"sheets": [s.to_dict() for s in sheets]}


@router.post("/sprite-sheet/create")
async def sprite_sheet_create(
    name: str = "Sheet",
    texture_width: int = 256,
    texture_height: int = 256,
    grid_cols: int = 8,
    grid_rows: int = 8,
    cell_width: int = 32,
    cell_height: int = 32,
):
    sheet = _sprite_sheet.create_sheet(
        name, texture_width, texture_height,
        grid_cols, grid_rows, cell_width, cell_height,
    )
    return sheet.to_dict()


@router.post("/sprite-sheet/clip/create")
async def sprite_sheet_clip_create(
    sheet_id: str,
    name: str = "idle",
    frame_indices: str = "0,1,2,3",
    loop_mode: str = "LOOP",
    speed_multiplier: float = 1.0,
):
    import json
    try:
        indices = json.loads(frame_indices)
    except json.JSONDecodeError:
        indices = [int(x.strip()) for x in frame_indices.split(",") if x.strip().isdigit()]
    try:
        lm = LoopMode[loop_mode]
    except KeyError:
        lm = LoopMode.LOOP
    clip = _sprite_sheet.create_clip(sheet_id, name, indices, lm, speed_multiplier)
    return clip.to_dict() if clip else {"error": "Clip creation failed"}


@router.post("/sprite-sheet/play")
async def sprite_sheet_play(entity_id: str, sheet_id: str, clip_name: str, speed: float = 1.0):
    success = _sprite_sheet.play(entity_id, sheet_id, clip_name, speed)
    return {"success": success}


@router.post("/sprite-sheet/pause")
async def sprite_sheet_pause(entity_id: str):
    success = _sprite_sheet.pause(entity_id)
    return {"success": success}


@router.post("/sprite-sheet/stop")
async def sprite_sheet_stop(entity_id: str):
    success = _sprite_sheet.stop(entity_id)
    return {"success": success}


# === Prompt Cache ===

_prompt_cache = get_prompt_cache()


@router.get("/prompt-cache/stats")
async def prompt_cache_stats():
    return _prompt_cache.get_stats()


@router.post("/prompt-cache/clear")
async def prompt_cache_clear():
    _prompt_cache.clear()
    return {"success": True}


@router.post("/prompt-cache/invalidate")
async def prompt_cache_invalidate(fingerprint: str):
    _prompt_cache.invalidate(fingerprint)
    return {"success": True}


@router.get("/prompt-cache/hit-rate")
async def prompt_cache_hit_rate():
    return {"hit_rate": _prompt_cache.get_hit_rate()}


# === Trajectory Recorder ===

_trajectory_recorder = get_trajectory_recorder()


@router.get("/trajectory/stats")
async def trajectory_stats():
    return _trajectory_recorder.get_stats()


@router.get("/trajectory/sessions")
async def trajectory_sessions():
    return {"sessions": _trajectory_recorder.list_sessions()}


@router.get("/trajectory/sessions/{session_id}")
async def trajectory_session(session_id: str):
    session = _trajectory_recorder.get_session(session_id)
    if session:
        return session.to_dict()
    return {"error": "Session not found"}


@router.post("/trajectory/sessions/{session_id}/export")
async def trajectory_export(session_id: str):
    data = _trajectory_recorder.export_session(session_id)
    if data:
        return data
    return {"error": "Session not found"}


# === Checkpoint System ===

_checkpoint_system_agent = get_checkpoint_system()


@router.get("/checkpoint-system/stats")
async def checkpoint_system_stats():
    return _checkpoint_system_agent.get_stats()


@router.get("/checkpoint-system/chains")
async def checkpoint_system_chains():
    return {"chains": _checkpoint_system_agent.list_chains()}


@router.post("/checkpoint-system/create")
async def checkpoint_system_create(chain_id: str, label: str = "", scope: str = "FULL"):
    from sparkai.agent.agent_checkpoint_system import CheckpointScope
    try:
        sc = CheckpointScope[scope.upper()]
    except KeyError:
        sc = CheckpointScope.FULL
    cp = _checkpoint_system_agent.create_checkpoint(chain_id, label, sc)
    if cp:
        return {"checkpoint_id": cp.checkpoint_id, "chain_id": chain_id}
    return {"error": "No state collectors registered"}


@router.post("/checkpoint-system/restore")
async def checkpoint_system_restore(chain_id: str, checkpoint_id: str):
    success = _checkpoint_system_agent.restore_checkpoint(chain_id, checkpoint_id)
    return {"success": success}


@router.post("/checkpoint-system/rollback")
async def checkpoint_system_rollback(chain_id: str):
    checkpoint = _checkpoint_system_agent.rollback(chain_id)
    if checkpoint:
        return checkpoint.to_dict()
    return {"error": "Cannot rollback"}


# === Budget Tracker ===

_budget_tracker = get_budget_tracker()


@router.get("/budget-tracker/stats")
async def budget_tracker_stats():
    return _budget_tracker.get_all_usage()


@router.get("/budget-tracker/session/{session_id}")
async def budget_tracker_session(session_id: str):
    return _budget_tracker.get_session_usage(session_id)


@router.post("/budget-tracker/record")
async def budget_tracker_record(session_id: str, tokens_input: int = 0, tokens_output: int = 0, model: str = "default"):
    alerts = _budget_tracker.record_usage(session_id, tokens_input, tokens_output, model)
    return {"alerts": {scope.value: level.value for scope, level in alerts.items()}}


@router.get("/budget-tracker/check/{session_id}")
async def budget_tracker_check(session_id: str, tokens: int = 0):
    can = _budget_tracker.can_proceed(session_id, tokens)
    return {"can_proceed": can}


@router.get("/budget-tracker/alerts")
async def budget_tracker_alerts():
    return {"alerts": [a.to_dict() for a in _budget_tracker.get_recent_alerts()]}


# === Tween System ===

_tween_system = get_tween_system()


@router.get("/tween/stats")
async def tween_stats():
    return _tween_system.get_stats()


@router.get("/tween/list")
async def tween_list():
    return {"tweens": _tween_system.list_tweens()}


@router.post("/tween/create")
async def tween_create(target_id: str, property_name: str, start_value: float, end_value: float,
                       duration: float = 1.0, easing: str = "LINEAR", loop_mode: str = "ONCE",
                       delay: float = 0.0):
    tid = _tween_system.create(target_id, property_name, start_value, end_value,
                               duration, easing, delay, loop_mode)
    return {"tween_id": tid}


@router.post("/tween/pause")
async def tween_pause(tween_id: str):
    _tween_system.pause(tween_id)
    return {"success": True}


@router.post("/tween/resume")
async def tween_resume(tween_id: str):
    _tween_system.resume(tween_id)
    return {"success": True}


@router.post("/tween/cancel")
async def tween_cancel(tween_id: str):
    _tween_system.cancel(tween_id)
    return {"success": True}


# === Node Path System ===

_node_path_system = get_node_path_system()


@router.get("/node-path/stats")
async def node_path_stats():
    return _node_path_system.get_stats()


@router.post("/node-path/parse")
async def node_path_parse(path_str: str):
    path = _node_path_system.parse(path_str)
    if path:
        return path.to_dict()
    return {"error": "Invalid path"}


@router.post("/node-path/resolve")
async def node_path_resolve(path_str: str, root_object_id: str):
    results = _node_path_system.resolve(path_str, {"object_id": root_object_id})
    return {"results": results}


@router.post("/node-path/alias")
async def node_path_alias(name: str, path_str: str):
    _node_path_system.register_alias(name, path_str)
    return {"success": True}


@router.get("/node-path/aliases")
async def node_path_aliases():
    return {"aliases": _node_path_system.list_aliases()}


# === Project Template System ===

_project_template_system = get_project_template_system()


@router.get("/project-templates/stats")
async def project_templates_stats():
    return _project_template_system.get_stats()


@router.get("/project-templates/genres")
async def project_templates_genres():
    return {"genres": _project_template_system.list_genres()}


@router.get("/project-templates/list")
async def project_templates_list(genre: Optional[str] = None):
    templates = _project_template_system.list_by_genre(genre) if genre else _project_template_system.list_all()
    return {"templates": [t.to_dict() for t in templates]}


@router.get("/project-templates/{template_id}")
async def project_template_detail(template_id: str):
    template = _project_template_system.get(template_id)
    if template:
        return template.to_dict()
    return {"error": "Template not found"}


# === Asset Pipeline ===

_asset_pipeline = get_asset_pipeline()


@router.get("/asset-pipeline/stats")
async def asset_pipeline_stats():
    return _asset_pipeline.get_stats()


@router.get("/asset-pipeline/assets")
async def asset_pipeline_assets():
    return {"assets": _asset_pipeline.list_assets()}


@router.get("/asset-pipeline/categories")
async def asset_pipeline_categories():
    return {"categories": _asset_pipeline.list_categories()}


@router.post("/asset-pipeline/register")
async def asset_pipeline_register(name: str, category: str, format: str, description: str = "",
                                  source_path: str = "", tags: Optional[List[str]] = None):
    aid = _asset_pipeline.register_asset(name, category, format, description, source_path, tags or [])
    return {"asset_id": aid}


@router.get("/asset-pipeline/search")
async def asset_pipeline_search(query: str):
    results = _asset_pipeline.search(query)
    return {"results": [r.to_dict() for r in results]}


@router.get("/asset-pipeline/category/{category}")
async def asset_pipeline_by_category(category: str):
    assets = _asset_pipeline.get_by_category(category)
    return {"assets": [a.to_dict() for a in assets]}


@router.post("/asset-pipeline/bundle")
async def asset_pipeline_bundle(name: str, asset_ids: List[str]):
    bid = _asset_pipeline.create_bundle(name, asset_ids)
    return {"bundle_id": bid}


@router.get("/asset-pipeline/import-history")
async def asset_pipeline_import_history():
    return {"history": _asset_pipeline.get_import_history()}


# === Insights Engine ===

_insights_engine = get_insights_engine()


@router.get("/insights/stats")
async def insights_stats():
    return _insights_engine.get_stats()


@router.get("/insights/report")
async def insights_report(days: int = 30):
    report = _insights_engine.generate(days=days)
    return report.to_dict()


@router.get("/insights/summary")
async def insights_summary(days: int = 7):
    report = _insights_engine.generate(days=days)
    return {"summary": _insights_engine.format_summary(report)}


@router.post("/insights/track-task")
async def insights_track_task(started: bool = False, completed: bool = False,
                              failed: bool = False, iterations: int = 0, retries: int = 0):
    _insights_engine.track_task(started, completed, failed, iterations, retries)
    return {"success": True}


@router.post("/insights/reset")
async def insights_reset():
    _insights_engine.reset()
    return {"success": True}


# === State Sync Mesh ===

_state_sync_mesh = get_state_sync_mesh()


@router.get("/state-sync/stats")
async def state_sync_stats():
    return _state_sync_mesh.get_stats()


@router.get("/state-sync/channels")
async def state_sync_channels():
    stats = _state_sync_mesh.get_stats()
    return {"channels": stats.get("channels_detail", {})}


@router.post("/state-sync/sync-all")
async def state_sync_sync_all():
    reports = _state_sync_mesh.sync_all()
    return {"reports": [
        {
            "domain": r.domain.value,
            "conflicts": r.conflicts_found,
            "resolved": r.conflicts_resolved,
        }
        for r in reports
    ]}


@router.post("/state-sync/sync-domain")
async def state_sync_sync_domain(domain: str):
    try:
        sd = SyncDomain[domain.upper()]
        report = _state_sync_mesh.sync_domain(sd)
        return {
            "domain": report.domain.value,
            "conflicts": report.conflicts_found,
            "resolved": report.conflicts_resolved,
            "strategy": report.strategy_used.value,
        }
    except KeyError:
        return {"error": f"Unknown domain: {domain}"}


@router.get("/state-sync/reports")
async def state_sync_reports(limit: int = 20):
    return {"reports": [
        {
            "domain": r.domain.value,
            "conflicts": r.conflicts_found,
            "resolved": r.conflicts_resolved,
            "timestamp": r.timestamp,
        }
        for r in _state_sync_mesh.get_recent_reports(limit)
    ]}


# === Development Loop ===

_dev_loop = get_dev_loop()


@router.get("/dev-loop/stats")
async def dev_loop_stats():
    return _dev_loop.get_stats()


@router.get("/dev-loop/history")
async def dev_loop_history(limit: int = 20):
    return {"history": _dev_loop.get_history(limit)}


@router.get("/dev-loop/phase")
async def dev_loop_phase():
    return {"phase": _dev_loop.get_phase().value}


@router.post("/dev-loop/execute")
async def dev_loop_execute(task: str):
    result = await _dev_loop.execute(task)
    return {
        "task_id": result.task_id,
        "success": result.success,
        "iterations": result.total_iterations,
        "quality": result.final_quality,
        "artifacts": result.artifacts,
    }


@router.post("/dev-loop/set-policy")
async def dev_loop_set_policy(max_iterations: Optional[int] = None,
                              quality_threshold: Optional[float] = None,
                              timeout_seconds: Optional[float] = None):
    kwargs = {}
    if max_iterations is not None:
        kwargs["max_iterations"] = max_iterations
    if quality_threshold is not None:
        kwargs["quality_threshold"] = quality_threshold
    if timeout_seconds is not None:
        kwargs["timeout_seconds"] = timeout_seconds
    _dev_loop.set_policy(**kwargs)
    return {"success": True}


@router.post("/dev-loop/abort")
async def dev_loop_abort():
    _dev_loop.abort()
    return {"success": True}


# === Context References ===

_context_references = get_context_reference_resolver()


@router.get("/context-refs/stats")
async def context_refs_stats():
    return _context_references.get_stats()


@router.post("/context-refs/parse")
async def context_refs_parse(message: str = Query(..., description="Message to parse for @domain:target references")):
    refs = _context_references.parse_references(message)
    return {"references": [
        {"raw": r.raw, "domain": r.domain.value, "target": r.target}
        for r in refs
    ]}


@router.post("/context-refs/resolve")
async def context_refs_resolve(message: str = Query(..., description="Message to resolve references in"),
                               max_tokens: int = Query(0, description="Max tokens for injected context")):
    result = _context_references.resolve_message(message, max_tokens)
    return {
        "expanded": result.expanded_message[:500] + ("..." if len(result.expanded_message) > 500 else ""),
        "found": result.found_count,
        "total": result.total_count,
        "tokens": result.injected_tokens,
        "warnings": result.warnings,
    }


@router.post("/context-refs/invalidate")
async def context_refs_invalidate(domain: Optional[str] = None, target: Optional[str] = None):
    try:
        rd = RefDomain[domain.upper()] if domain else None
    except KeyError:
        rd = None
    _context_references.invalidate_cache(rd, target)
    return {"success": True}


# === Rendering Server ===

_rendering_server = get_rendering_server()


@router.get("/rendering-server/stats")
async def rendering_server_stats():
    return _rendering_server.get_stats()


@router.get("/rendering-server/commands")
async def rendering_server_commands():
    cmds = _rendering_server.get_commands()
    return {"commands": [
        {"type": c.cmd_type.value, "layer": c.layer, "z": c.z_index}
        for c in cmds[:50]
    ], "total": len(cmds)}


@router.post("/rendering-server/set-viewport")
async def rendering_server_set_viewport(width: int = 1920, height: int = 1080,
                                        scale: float = 1.0, cam_x: float = 0.0,
                                        cam_y: float = 0.0):
    _rendering_server.set_viewport(0, 0, width, height, scale, cam_x, cam_y)
    return {"success": True}


@router.post("/rendering-server/register-sprite")
async def rendering_server_register_sprite(key: str):
    _rendering_server.register_sprite(key, None)
    return {"success": True, "key": key}


@router.post("/rendering-server/reset-stats")
async def rendering_server_reset_stats():
    _rendering_server.reset_stats()
    return {"success": True}


# === Input Event System ===

_input_event_system = get_input_event_system()


@router.get("/input-events/stats")
async def input_events_stats():
    return _input_event_system.get_stats()


@router.post("/input-events/emit-key")
async def input_events_emit_key(key_code: str, pressed: bool = True):
    evt = _input_event_system.emit_key(key_code, pressed)
    return {"event_id": evt.event_id}


@router.post("/input-events/emit-mouse")
async def input_events_emit_mouse(x: int, y: int, button: int = 0, pressed: bool = False):
    evt = _input_event_system.emit_mouse(x, y, button, pressed)
    return {"event_id": evt.event_id}


@router.post("/input-events/emit-touch")
async def input_events_emit_touch(touch_id: int, x: float, y: float, phase: str = "start"):
    evt = _input_event_system.emit_touch(touch_id, x, y, phase)
    return {"event_id": evt.event_id}


@router.post("/input-events/register")
async def input_events_register(action: str, key: str = "", axis: str = "",
                                dead_zone: float = 0.15):
    binding = _input_event_system.register(action, key=key, axis=axis, dead_zone=dead_zone)
    return {"action": binding.action_name}


@router.get("/input-events/action/{action_name}")
async def input_events_action(action_name: str):
    return {"value": _input_event_system.get_action_value(action_name)}


@router.post("/input-events/flush")
async def input_events_flush():
    flushed = _input_event_system.flush_events()
    return {"flushed": flushed}


# === Game Object Registry ===

_game_object_registry = get_game_object_registry()


@router.get("/game-objects/stats")
async def game_objects_stats():
    return _game_object_registry.get_stats()


@router.get("/game-objects/list")
async def game_objects_list(tag: Optional[str] = None):
    if tag:
        objects = _game_object_registry.find_by_tag(tag)
    else:
        objects = _game_object_registry.find_active()
    return {"objects": [o.to_dict() for o in objects[:50]], "total": len(objects)}


@router.get("/game-objects/{object_id}")
async def game_object_detail(object_id: str):
    go = _game_object_registry.find(object_id)
    if go:
        return go.to_dict()
    return {"error": "Object not found"}


@router.post("/game-objects/create")
async def game_objects_create(name: str = "GameObject", x: float = 0, y: float = 0,
                              tags: Optional[List[str]] = None):
    go = create_game_object(name, (x, y), tags)
    return go.to_dict()


@router.post("/game-objects/destroy-all")
async def game_objects_destroy_all():
    count = _game_object_registry.destroy_all()
    return {"destroyed": count}


# === Scene Manager ===

_scene_manager = get_scene_manager()
_process_registry = get_process_registry()
_cron_scheduler = get_cron_scheduler()
_expression_evaluator = get_expression_evaluator()
_class_registry = get_class_registry()
_multi_modal_agent = get_multi_modal_agent()
_import_pipeline = get_import_pipeline()
_terrain_system = get_terrain_system()
_save_system = get_save_system()
_network_sync = get_network_sync()
_behavior_tree = get_behavior_tree()


@router.get("/scene-manager/stats")
async def scene_manager_stats():
    return _scene_manager.get_stats()


@router.get("/scene-manager/scenes")
async def scene_manager_scenes():
    return {"scenes": _scene_manager.list_definitions()}


@router.get("/scene-manager/stack")
async def scene_manager_stack():
    return {
        "stack": _scene_manager.get_scene_stack(),
        "overlays": _scene_manager.get_overlay_stack(),
    }


@router.post("/scene-manager/register")
async def scene_manager_register(name: str, permanent: bool = True,
                                 poolable: bool = False, preload: bool = False):
    defn = _scene_manager.register(name, None, permanent, poolable, preload)
    return {"scene_id": defn.scene_id, "name": defn.name}


@router.post("/scene-manager/push-scene")
async def scene_manager_push_scene(name: str):
    instance = _scene_manager.push_scene(name)
    if instance:
        return {"instance_id": instance.instance_id, "state": instance.state.value}
    return {"error": "Scene not found"}


@router.post("/scene-manager/pop-scene")
async def scene_manager_pop_scene():
    instance = _scene_manager.pop_scene()
    if instance:
        return {"instance_id": instance.instance_id, "name": instance.definition.name}
    return {"error": "No scene to pop"}


@router.get("/scene-manager/active")
async def scene_manager_active():
    active = _scene_manager.get_active_scene()
    if active:
        return {"name": active.definition.name, "state": active.state.value}
    return {"error": "No active scene"}


@router.post("/scene-manager/clear-pool")
async def scene_manager_clear_pool():
    _scene_manager.clear_pool()
    return {"success": True}


# ============================================================
# Process Registry Endpoints
# ============================================================

@router.get("/process-registry/stats")
async def process_registry_stats():
    return _process_registry.get_stats()


@router.post("/process-registry/register")
async def process_registry_register(name: str, command: str, process_type: str = "custom"):
    try:
        pt = ProcessType(process_type)
    except ValueError:
        pt = ProcessType.CUSTOM
    entry = _process_registry.register(name=name, command=command, process_type=pt)
    return entry.to_dict()


@router.get("/process-registry/list")
async def process_registry_list():
    return {"processes": [p.to_dict() for p in _process_registry.list_all()]}


@router.get("/process-registry/active")
async def process_registry_active():
    return {"processes": [p.to_dict() for p in _process_registry.list_active()]}


@router.post("/process-registry/update-state")
async def process_registry_update_state(process_id: str, state: str):
    try:
        ps = ProcState(state)
    except ValueError:
        return {"error": f"Invalid state: {state}"}
    entry = _process_registry.update_state(process_id, ps)
    if entry:
        return entry.to_dict()
    return {"error": "Process not found"}


# ============================================================
# Cron Scheduler Endpoints
# ============================================================

class CronScheduleIntervalRequest(BaseModel):
    name: str
    seconds: int

class CronCancelRequest(BaseModel):
    job_id: str

@router.get("/cron-scheduler/stats")
async def cron_scheduler_stats():
    return _cron_scheduler.get_stats()


@router.post("/cron-scheduler/schedule-interval")
async def cron_scheduler_schedule_interval(body: CronScheduleIntervalRequest):
    from sparkai.agent.agent_cron_scheduler import CronFrequency
    interval_minutes = max(1, body.seconds // 60)
    cron_expr = f"*/{interval_minutes} * * * *"
    rule = _cron_scheduler.create_rule(
        name=body.name,
        frequency=CronFrequency.MINUTELY,
        cron_expression=cron_expr,
    )
    task = _cron_scheduler.schedule_task(
        agent_id="api",
        rule_id=rule.id,
        task_name=body.name,
    )
    return {"job_id": task.id, "name": task.task_name, "rule_id": rule.id}


@router.get("/cron-scheduler/jobs")
async def cron_scheduler_jobs():
    return {"jobs": [
        {"job_id": t.id, "name": t.task_name, "state": t.state.value}
        for t in _cron_scheduler.list_tasks()
    ]}


@router.post("/cron-scheduler/cancel")
async def cron_scheduler_cancel(body: CronCancelRequest):
    return {"cancelled": _cron_scheduler.cancel_task(body.job_id)}


@router.post("/cron-scheduler/start")
async def cron_scheduler_start():
    _cron_scheduler.tick()
    return {"running": True}


@router.post("/cron-scheduler/stop")
async def cron_scheduler_stop():
    return {"running": False}


# ============================================================
# Expression Evaluator Endpoints
# ============================================================

@router.get("/expression-evaluator/stats")
async def expression_evaluator_stats():
    return _expression_evaluator.get_stats()


@router.post("/expression-evaluator/evaluate")
async def expression_evaluator_evaluate(expression: str):
    result = _expression_evaluator.evaluate(expression)
    return {"expression": expression, "result": result, "type": type(result).__name__}


@router.post("/expression-evaluator/evaluate-bool")
async def expression_evaluator_evaluate_bool(expression: str):
    result = _expression_evaluator.evaluate_bool(expression)
    return {"expression": expression, "result": result}


# ============================================================
# Class Registry Endpoints
# ============================================================

@router.get("/class-registry/stats")
async def class_registry_stats():
    return _class_registry.get_stats()


@router.get("/class-registry/types")
async def class_registry_types():
    types = _class_registry.list_all()
    return {"types": [t.to_dict() for t in types]}


@router.get("/class-registry/type/{type_name}")
async def class_registry_get_type(type_name: str):
    td = _class_registry.get(type_name)
    if td:
        return td.to_dict()
    return {"error": f"Type '{type_name}' not found"}


@router.get("/class-registry/search")
async def class_registry_search(query: str):
    results = _class_registry.search(query)
    return {"results": [t.to_dict() for t in results]}


@router.get("/class-registry/categories")
async def class_registry_categories():
    return {"categories": _class_registry.list_categories()}


# ============================================================
# Multi-Modal Agent Endpoints
# ============================================================

@router.get("/multi-modal/stats")
async def multi_modal_stats():
    return _multi_modal_agent.get_stats()


@router.post("/multi-modal/analyze-sprite")
async def multi_modal_analyze_sprite(asset_name: str, width: int = 0, height: int = 0, frame_count: int = 1):
    dims = (width, height) if width > 0 and height > 0 else None
    report = _multi_modal_agent.analyze_sprite(asset_name, dims, frame_count)
    return report.to_dict()


@router.post("/multi-modal/analyze-ui")
async def multi_modal_analyze_ui(widget_count: int = 0):
    report = _multi_modal_agent.analyze_ui_layout(widget_count)
    return report.to_dict()


@router.get("/multi-modal/reports")
async def multi_modal_reports():
    return {"reports": [r.to_dict() for r in _multi_modal_agent.list_reports()]}


# ============================================================
# Import Pipeline Endpoints
# ============================================================

@router.get("/import-pipeline/stats")
async def import_pipeline_stats():
    return _import_pipeline.get_stats()


@router.post("/import-pipeline/import")
async def import_pipeline_import(source_path: str):
    entry = _import_pipeline.import_asset(source_path)
    return entry.to_dict()


@router.post("/import-pipeline/detect")
async def import_pipeline_detect(file_path: str):
    category, fmt_name = _import_pipeline.detect_format(file_path)
    return {"category": category.value, "format": fmt_name, "supported": _import_pipeline.is_format_supported(file_path)}


@router.get("/import-pipeline/list")
async def import_pipeline_list(limit: int = 20):
    entries = _import_pipeline.list_recent(limit)
    return {"imports": [e.to_dict() for e in entries]}


@router.get("/import-pipeline/formats")
async def import_pipeline_formats():
    return {"formats": _import_pipeline.list_supported_formats()}


# ============================================================
# Terrain System Endpoints
# ============================================================

@router.get("/terrain-system/stats")
async def terrain_system_stats():
    return _terrain_system.get_stats()


@router.post("/terrain-system/generate")
async def terrain_system_generate(width: int = 32, height: int = 32, scale: float = 0.05, octaves: int = 4):
    cells = _terrain_system.generate_terrain(width, height, scale, octaves)
    result = [[c.to_dict() for c in row] for row in cells]
    return {"width": width, "height": height, "terrain": result}


@router.get("/terrain-system/biomes")
async def terrain_system_biomes():
    return {"biomes": [
        {"name": b.name, "terrain": b.terrain_type.value}
        for b in _terrain_system.list_biomes()
    ]}


# ============================================================
# Save System Endpoints
# ============================================================

@router.get("/save-system/stats")
async def save_system_stats():
    return _save_system.get_stats()


@router.post("/save-system/save")
async def save_system_save(slot_id: int, scene_name: str = "", playtime_seconds: float = 0.0):
    state = {"scene": scene_name, "playtime": playtime_seconds}
    slot = _save_system.create_save(slot_number=slot_id, scene_id=scene_name, game_data=state)
    if slot:
        return slot.to_dict()
    return {"error": "Save failed"}


@router.get("/save-system/load/{slot_id}")
async def save_system_load(slot_id: int):
    state = _save_system.load_save(str(slot_id))
    if state:
        return {"state": state}
    return {"error": "Load failed"}


@router.delete("/save-system/slot/{slot_id}")
async def save_system_delete(slot_id: int):
    return {"deleted": _save_system.delete_save(str(slot_id))}


@router.get("/save-system/slots")
async def save_system_slots():
    return {"slots": [s.to_dict() for s in _save_system.list_slots()]}


# ============================================================
# Behavior Runtime Endpoints
# ============================================================

@router.get("/behavior-runtime/stats")
async def behavior_runtime_stats():
    return _behavior_runtime.get_stats()


@router.post("/behavior-runtime/create-tree")
async def behavior_runtime_create_tree(name: str = "", owner_id: str = ""):
    tree = _behavior_runtime.create_tree(name, owner_id)
    return tree.to_dict()


@router.post("/behavior-runtime/add-node")
async def behavior_runtime_add_node(tree_id: str = "", name: str = "",
                                     category: str = "action", parent_id: str = "",
                                     priority: int = 0, cooldown: float = 0.0):
    node = _behavior_runtime.add_node(tree_id, name, category, parent_id, priority=priority, cooldown=cooldown)
    if node:
        return node.to_dict()
    return {"error": "Tree not found"}


@router.post("/behavior-runtime/activate-tree")
async def behavior_runtime_activate_tree(tree_id: str = ""):
    return {"activated": _behavior_runtime.activate_tree(tree_id)}


@router.post("/behavior-runtime/deactivate-tree")
async def behavior_runtime_deactivate_tree(tree_id: str = ""):
    return {"deactivated": _behavior_runtime.deactivate_tree(tree_id)}


@router.post("/behavior-runtime/tick-tree")
async def behavior_runtime_tick_tree(tree_id: str = "", delta_time: float = 0.016):
    return _behavior_runtime.tick_tree(tree_id, delta_time)


@router.get("/behavior-runtime/tree/{tree_id}")
async def behavior_runtime_get_tree(tree_id: str):
    tree = _behavior_runtime.get_tree(tree_id)
    if tree:
        return tree.to_dict()
    return {"error": "Tree not found"}


@router.get("/behavior-runtime/trees")
async def behavior_runtime_list_trees(owner_id: str = ""):
    owner = owner_id if owner_id else None
    return {"trees": [t.to_dict() for t in _behavior_runtime.list_trees(owner)]}


@router.post("/behavior-runtime/create-fsm")
async def behavior_runtime_create_fsm(name: str = "", owner_id: str = ""):
    fsm = _behavior_runtime.create_fsm(name, owner_id)
    return fsm.to_dict()


@router.post("/behavior-runtime/add-fsm-state")
async def behavior_runtime_add_fsm_state(fsm_id: str = "", name: str = "",
                                          is_initial: bool = False):
    state = _behavior_runtime.add_fsm_state(fsm_id, name, is_initial)
    if state:
        return state.to_dict()
    return {"error": "FSM not found"}


@router.post("/behavior-runtime/add-fsm-transition")
async def behavior_runtime_add_fsm_transition(fsm_id: str = "", from_state_id: str = "",
                                               to_state_id: str = "", name: str = "",
                                               trigger: str = "condition", event_name: str = "",
                                               timer_seconds: float = 0.0):
    return {"added": _behavior_runtime.add_fsm_transition(
        fsm_id, from_state_id, to_state_id, name, trigger,
        event_name=event_name, timer_seconds=timer_seconds)}


@router.post("/behavior-runtime/activate-fsm")
async def behavior_runtime_activate_fsm(fsm_id: str = ""):
    return {"activated": _behavior_runtime.activate_fsm(fsm_id)}


@router.post("/behavior-runtime/trigger-fsm-event")
async def behavior_runtime_trigger_fsm_event(fsm_id: str = "", event_name: str = ""):
    return {"triggered": _behavior_runtime.trigger_fsm_event(fsm_id, event_name)}


@router.get("/behavior-runtime/fsm/{fsm_id}")
async def behavior_runtime_get_fsm(fsm_id: str):
    fsm = _behavior_runtime.get_fsm(fsm_id)
    if fsm:
        return fsm.to_dict()
    return {"error": "FSM not found"}


@router.get("/behavior-runtime/fsms")
async def behavior_runtime_list_fsms(owner_id: str = ""):
    owner = owner_id if owner_id else None
    return {"fsms": [f.to_dict() for f in _behavior_runtime.list_fsms(owner)]}


@router.post("/behavior-runtime/load-preset-tree")
async def behavior_runtime_load_preset_tree(preset_key: str = ""):
    tree = _behavior_runtime.load_preset_tree(preset_key)
    if tree:
        return tree.to_dict()
    return {"error": "Unknown preset"}


@router.post("/behavior-runtime/load-preset-fsm")
async def behavior_runtime_load_preset_fsm(preset_key: str = ""):
    fsm = _behavior_runtime.load_preset_fsm(preset_key)
    if fsm:
        return fsm.to_dict()
    return {"error": "Unknown preset"}


@router.get("/behavior-runtime/presets")
async def behavior_runtime_list_presets():
    return _behavior_runtime.list_presets()


@router.post("/behavior-runtime/set-blackboard")
async def behavior_runtime_set_blackboard(owner_id: str = "", key: str = "", value: str = ""):
    _behavior_runtime.set_blackboard(owner_id, key, value)
    return {"set": True}


@router.get("/behavior-runtime/blackboard/{owner_id}/{key}")
async def behavior_runtime_get_blackboard(owner_id: str, key: str):
    return {"value": _behavior_runtime.get_blackboard(owner_id, key)}


@router.get("/behavior-runtime/execution-log")
async def behavior_runtime_execution_log(limit: int = 50):
    return {"log": _behavior_runtime.get_execution_log(limit)}


# ============================================================
# Network Sync Endpoints
# ============================================================

@router.get("/network-sync/stats")
async def network_sync_stats():
    return _network_sync.get_stats()


@router.post("/network-sync/register-object")
async def network_sync_register_object(object_id: str, owner_id: str = ""):
    obj = _network_sync.register_object(object_id, owner_id)
    return {"object_id": obj.object_id, "authority": obj.authority.value}


@router.post("/network-sync/mark-dirty")
async def network_sync_mark_dirty(object_id: str):
    return {"dirtied": _network_sync.mark_dirty(object_id)}


@router.post("/network-sync/tick")
async def network_sync_tick():
    count = _network_sync.tick()
    return {"synced": count}


# ============================================================
# Behavior Tree Endpoints
# ============================================================

@router.get("/behavior-tree/stats")
async def behavior_tree_stats():
    return _behavior_tree.get_stats()


@router.post("/behavior-tree/create")
async def behavior_tree_create(tree_id: str):
    root = Sequence([
        Action(lambda bb: NodeStatus.SUCCESS, "Patrol"),
    ], "DefaultRoot")
    bb = _behavior_tree.create(tree_id, root)
    bb.set("health", 100)
    return {"tree_id": tree_id, "blackboard": bb.to_dict()}


@router.post("/behavior-tree/tick")
async def behavior_tree_tick(tree_id: str):
    status = _behavior_tree.tick(tree_id)
    return {"tree_id": tree_id, "status": status.value}


@router.post("/behavior-tree/tick-all")
async def behavior_tree_tick_all():
    results = _behavior_tree.tick_all()
    return {"results": {k: v.value for k, v in results.items()}}


@router.get("/behavior-tree/trees")
async def behavior_tree_trees():
    return {"trees": _behavior_tree.list_trees()}


@router.get("/behavior-tree/blackboard/{tree_id}")
async def behavior_tree_blackboard(tree_id: str):
    bb = _behavior_tree.get_blackboard(tree_id)
    if bb:
        return {"tree_id": tree_id, "data": bb.to_dict()}
    return {"error": "Tree not found"}


# ============================================================
# Math Utils Endpoints
# ============================================================

from sparkai.engine.math_utils import MathUtils, Vector2, Vector3, Rect2, Transform2D, Easing, Interpolation, Geometry2D, get_math_utils

_math_utils = get_math_utils()


class Vector2Request(BaseModel):
    x: float = 0.0
    y: float = 0.0


class Vector3Request(BaseModel):
    x: float = 0.0
    y: float = 0.0
    z: float = 0.0


class Rect2Request(BaseModel):
    x: float = 0.0
    y: float = 0.0
    width: float = 0.0
    height: float = 0.0


class Transform2DRequest(BaseModel):
    origin: Vector2Request = Vector2Request()
    rotation: float = 0.0
    scale: Vector2Request = Vector2Request(x=1.0, y=1.0)
    translation: Vector2Request = Vector2Request()


@router.get("/math/stats")
async def math_stats():
    return _math_utils.get_stats()


@router.get("/math/easing-curves")
async def math_easing_curves():
    return {"curves": Easing.list_all()}


@router.get("/math/easing/{curve_name}")
async def math_easing(curve_name: str, t: float = 0.5):
    val = Easing.apply(curve_name, t)
    return {"curve": curve_name, "t": t, "value": val}


@router.post("/math/vector2/distance")
async def math_vector2_distance(a: Vector2Request, b: Vector2Request):
    va = Vector2(a.x, a.y)
    vb = Vector2(b.x, b.y)
    return {"distance": va.distance_to(vb), "dot": va.dot(vb), "cross": va.cross(vb)}


@router.post("/math/vector2/rotate")
async def math_vector2_rotate(v: Vector2Request, angle: float = 0.0):
    vec = Vector2(v.x, v.y)
    rotated = vec.rotate(angle)
    return rotated.to_dict()


@router.post("/math/geometry/point-in-polygon")
async def math_geometry_point_in_polygon(point: Vector2Request, polygon: List[Vector2Request]):
    pt = Vector2(point.x, point.y)
    poly = [Vector2(p.x, p.y) for p in polygon]
    return {"inside": Geometry2D.point_in_polygon(pt, poly)}


@router.post("/math/interpolation/lerp")
async def math_interpolation_lerp(a: float = 0.0, b: float = 1.0, t: float = 0.5):
    return {"result": Interpolation.lerp(a, b, t), "smoothstep": Interpolation.smoothstep(a, b, t)}


# ============================================================
# GUI System Endpoints
# ============================================================

from sparkai.engine.gui_system import GUISystem, Widget, Container, Button, Label, Slider, TextInput, Image, get_gui_system, LayoutMode, WidgetState, Theme

_gui_system = get_gui_system()


class WidgetCreateRequest(BaseModel):
    widget_type: str = "label"
    name: str = ""
    text: str = ""
    x: float = 0.0
    y: float = 0.0
    width: float = 100.0
    height: float = 30.0
    parent_id: str = ""


@router.get("/gui/stats")
async def gui_stats():
    return _gui_system.get_stats()


@router.post("/gui/create-root")
async def gui_create_root(width: float = 800, height: float = 600):
    root = _gui_system.create_root(width, height)
    return root.to_dict()


@router.get("/gui/root")
async def gui_get_root():
    root = _gui_system.root
    if root:
        return root.to_dict()
    return {"error": "No root container"}


@router.post("/gui/create-widget")
async def gui_create_widget(req: WidgetCreateRequest):
    parent = None
    if req.parent_id:
        parent_widget = _gui_system.find_widget(req.parent_id)
        if isinstance(parent_widget, Container):
            parent = parent_widget
    if req.widget_type == "label":
        widget = _gui_system.create_label(text=req.text or req.name, parent=parent, x=req.x, y=req.y, width=req.width, height=req.height)
    elif req.widget_type == "button":
        widget = _gui_system.create_button(text=req.text or req.name, parent=parent, x=req.x, y=req.y, width=req.width, height=req.height)
    elif req.widget_type == "container":
        widget = _gui_system.create_container(parent=parent, name=req.name, x=req.x, y=req.y, width=req.width, height=req.height)
    else:
        return {"error": f"Unknown widget type: {req.widget_type}"}
    return widget.to_dict()


@router.get("/gui/widget/{widget_id}")
async def gui_get_widget(widget_id: str):
    widget = _gui_system.find_widget(widget_id)
    if widget:
        return widget.to_dict()
    return {"error": "Widget not found"}


@router.post("/gui/handle-mouse-click")
async def gui_handle_mouse_click(mx: float = 0.0, my: float = 0.0):
    widget_id = _gui_system.handle_mouse_click(mx, my)
    return {"clicked_widget": widget_id}


@router.post("/gui/handle-mouse-move")
async def gui_handle_mouse_move(mx: float = 0.0, my: float = 0.0):
    _gui_system.handle_mouse_move(mx, my)
    return {"hover_widget": _gui_system._hover_widget}


@router.get("/gui/themes")
async def gui_themes():
    return {"themes": [t.to_dict() for t in _gui_system._themes.values()], "active": _gui_system._active_theme}


@router.post("/gui/set-theme")
async def gui_set_theme(name: str = "default"):
    success = _gui_system.set_theme(name)
    return {"success": success, "theme": _gui_system._active_theme}


# ============================================================
# Config Manager Endpoints
# ============================================================

from sparkai.engine.config_manager import ConfigManager, ConfigScope, ConfigEntry, ConfigSchema, get_config_manager

_config_manager = get_config_manager()


class ConfigSetRequest(BaseModel):
    key: str
    value: Any
    scope: str = "project"
    description: str = ""


@router.get("/config/stats")
async def config_stats():
    return _config_manager.get_stats()


@router.get("/config/keys")
async def config_keys(scope: Optional[str] = None):
    cscope = ConfigScope(scope) if scope else None
    return {"keys": _config_manager.list_keys(scope=cscope)}


@router.get("/config/all")
async def config_all():
    return _config_manager.get_all()


@router.get("/config/validate")
async def config_validate():
    return _config_manager.validate_all()


@router.get("/config/scope/{scope}")
async def config_scope(scope: str):
    try:
        cscope = ConfigScope(scope)
        return {"scope": scope, "config": _config_manager.get_scope(cscope)}
    except ValueError:
        return {"error": f"Invalid scope: {scope}"}


@router.get("/config/{key}")
async def config_get(key: str):
    return {"key": key, "value": _config_manager.get(key)}


@router.post("/config/set")
async def config_set(req: ConfigSetRequest):
    scope = ConfigScope(req.scope) if req.scope in [s.value for s in ConfigScope] else ConfigScope.PROJECT
    entry = _config_manager.set(req.key, req.value, scope, req.description)
    return entry.to_dict()


@router.delete("/config/{key}")
async def config_delete(key: str):
    return {"deleted": _config_manager.delete(key)}


@router.post("/config/load")
async def config_load(file_path: str):
    count = _config_manager.load_from_file(file_path)
    return {"loaded": count, "file": file_path}


@router.post("/config/save")
async def config_save(file_path: str = ""):
    count = _config_manager.save_to_file(file_path)
    return {"saved": count}


# ============================================================
# Animation Controller Endpoints
# ============================================================

from sparkai.engine.animation_controller import (
    AnimationController, AnimState, AnimClip, AnimLayer, Transition, AnimCondition,
    BlendTree, BlendTreeNode, AnimParameter, AnimParameterType, AnimClipMode,
    AnimConditionMode, BlendTreeType, get_animation_controller,
)

_animation_controller = get_animation_controller()


class AnimClipCreateRequest(BaseModel):
    name: str
    duration: float = 1.0
    mode: str = "loop"
    speed: float = 1.0


class AnimParameterRequest(BaseModel):
    name: str
    param_type: str = "float"
    default_value: Any = None


class AnimStateCreateRequest(BaseModel):
    name: str
    layer_id: str = ""
    clip_id: Optional[str] = None
    is_default: bool = False


class AnimTransitionCreateRequest(BaseModel):
    from_state: str
    to_state: str
    duration: float = 0.2
    conditions: Optional[List[Dict[str, Any]]] = None


@router.get("/anim-controller/stats")
async def anim_controller_stats():
    return _animation_controller.get_stats()


@router.get("/anim-controller/active-states")
async def anim_controller_active_states():
    return {"active_states": _animation_controller.get_active_state_names()}


@router.post("/anim-controller/create-clip")
async def anim_controller_create_clip(req: AnimClipCreateRequest):
    mode = AnimClipMode(req.mode) if req.mode in [m.value for m in AnimClipMode] else AnimClipMode.LOOP
    clip = _animation_controller.create_clip(req.name, req.duration, mode, req.speed)
    return clip.to_dict()


@router.get("/anim-controller/clips")
async def anim_controller_clips():
    return {"clips": [c.to_dict() for c in _animation_controller._clip_library.values()]}


@router.get("/anim-controller/clip/{clip_id}")
async def anim_controller_get_clip(clip_id: str):
    clip = _animation_controller.get_clip(clip_id)
    if clip:
        return clip.to_dict()
    return {"error": "Clip not found"}


@router.post("/anim-controller/create-parameter")
async def anim_controller_create_parameter(req: AnimParameterRequest):
    ptype = AnimParameterType(req.param_type) if req.param_type in [t.value for t in AnimParameterType] else AnimParameterType.FLOAT
    param = _animation_controller.create_parameter(req.name, ptype)
    return param.to_dict()


@router.post("/anim-controller/set-parameter")
async def anim_controller_set_parameter(name: str, value: Any):
    param = _animation_controller._parameters.get(name)
    if not param:
        return {"error": "Parameter not found"}
    if param.param_type == AnimParameterType.FLOAT:
        _animation_controller.set_float(name, float(value))
    elif param.param_type == AnimParameterType.INT:
        _animation_controller.set_int(name, int(value))
    elif param.param_type == AnimParameterType.BOOL:
        _animation_controller.set_bool(name, bool(value))
    elif param.param_type == AnimParameterType.TRIGGER:
        _animation_controller.set_trigger(name)
    return {"name": name, "value": _animation_controller.get_parameter_value(name)}


@router.get("/anim-controller/parameters")
async def anim_controller_parameters():
    return {"parameters": [p.to_dict() for p in _animation_controller._parameters.values()]}


@router.post("/anim-controller/create-layer")
async def anim_controller_create_layer(name: str, weight: float = 1.0):
    layer = _animation_controller.create_layer(name, weight)
    return layer.to_dict()


@router.get("/anim-controller/layers")
async def anim_controller_layers():
    return {"layers": [l.to_dict() for l in _animation_controller._layers.values()]}


@router.post("/anim-controller/update")
async def anim_controller_update(delta_time: float = 0.016):
    _animation_controller.update(delta_time)
    return _animation_controller.get_stats()


# ============================================================
# Trajectory Recorder V2 Endpoints
# ============================================================

from sparkai.agent.agent_trajectory import TrajectoryRecorder, TrajectoryPhase, TrajectorySession, get_trajectory_recorder

_trajectory_recorder_v2 = get_trajectory_recorder()


class TrajectoryRecordRequest(BaseModel):
    session_id: str
    phase: str = "observe"
    action: str = ""
    data: Optional[Dict[str, Any]] = None


@router.get("/trajectory-v2/stats")
async def trajectory_v2_stats():
    return _trajectory_recorder_v2.get_stats()


@router.get("/trajectory-v2/sessions")
async def trajectory_v2_sessions():
    return {"sessions": [s.to_dict() for s in _trajectory_recorder_v2._sessions.values()]}


@router.get("/trajectory-v2/session/{session_id}")
async def trajectory_v2_get_session(session_id: str):
    session = _trajectory_recorder_v2.get_session(session_id)
    if session:
        return session.to_full_dict()
    return {"error": "Session not found"}


@router.post("/trajectory-v2/start-session")
async def trajectory_v2_start_session(session_id: str = "", project_name: str = ""):
    session = _trajectory_recorder_v2.start_session(session_id, project_name)
    return session.to_dict()


@router.post("/trajectory-v2/record")
async def trajectory_v2_record(req: TrajectoryRecordRequest):
    phase = TrajectoryPhase(req.phase) if req.phase in [p.value for p in TrajectoryPhase] else TrajectoryPhase.OBSERVE
    step = _trajectory_recorder_v2.record(req.session_id, phase, req.action, req.data)
    return step.to_dict()


@router.post("/trajectory-v2/end-session")
async def trajectory_v2_end_session(session_id: str, outcome: str = "success"):
    session = _trajectory_recorder_v2.end_session(session_id, outcome)
    if session:
        return session.to_dict()
    return {"error": "Session not found"}


@router.get("/trajectory-v2/replay/{session_id}")
async def trajectory_v2_replay(session_id: str):
    summary = _trajectory_recorder_v2.replay_summary(session_id)
    return summary


@router.post("/trajectory-v2/export/{session_id}")
async def trajectory_v2_export(session_id: str, file_path: str = ""):
    success = _trajectory_recorder_v2.export_session(session_id, file_path)
    return {"success": success, "file": file_path}


@router.post("/trajectory-v2/import")
async def trajectory_v2_import_session(file_path: str):
    session_id = _trajectory_recorder_v2.import_session(file_path)
    if session_id:
        return {"session_id": session_id}
    return {"error": "Import failed"}


# ============================================================
# Skill Command Registry Endpoints
# ============================================================

from sparkai.agent.agent_skill_commands import SkillCommandRegistry, CommandCategory, CommandDef, get_skill_command_registry

_skill_command_registry = get_skill_command_registry()


class CommandExecuteRequest(BaseModel):
    command_name: str
    args: Dict[str, Any] = {}
    user_id: str = "api"
    project_id: str = ""


@router.get("/commands/stats")
async def commands_stats():
    return _skill_command_registry.get_stats()


@router.get("/commands/list")
async def commands_list(category: Optional[str] = None):
    if category:
        cat = CommandCategory(category) if category in [c.value for c in CommandCategory] else None
        cmds = _skill_command_registry.list_commands(cat)
    else:
        cmds = _skill_command_registry.list_commands()
    return {"commands": [c.to_dict() for c in cmds]}


@router.get("/commands/help/{command_name}")
async def commands_help(command_name: str):
    help_text = _skill_command_registry.get_help(command_name)
    return {"command": command_name, "help": help_text}


@router.post("/commands/execute")
async def commands_execute(req: CommandExecuteRequest):
    result = _skill_command_registry.execute(req.command_name, req.args, req.user_id, req.project_id)
    return result.to_dict()


@router.get("/commands/history")
async def commands_history(limit: int = 20):
    return {"history": [r.to_dict() for r in _skill_command_registry.get_history(limit)]}


# ============================================================
# Session Store Endpoints
# ============================================================

from sparkai.agent.agent_session_persistence import SessionStore, SessionStatus, SessionRecord, get_session_store

_session_store = get_session_store()


class SessionCreateRequest(BaseModel):
    title: str = "Session"
    project_name: str = ""
    tags: List[str] = []
    metadata: Optional[Dict[str, Any]] = None


@router.get("/sessions/store/stats")
async def sessions_store_stats():
    return _session_store.get_stats()


@router.post("/sessions/store/create")
async def sessions_store_create(req: SessionCreateRequest):
    record = _session_store.create(req.title, req.project_name, req.tags, req.metadata)
    return record.to_dict()


@router.get("/sessions/store/{record_id}")
async def sessions_store_get(record_id: str):
    record = _session_store.get(record_id)
    if record:
        return record.to_dict()
    return {"error": "Record not found"}


@router.post("/sessions/store/update")
async def sessions_store_update(record_id: str, data: Dict[str, Any]):
    record = _session_store.update(record_id, data)
    if record:
        return record.to_dict()
    return {"error": "Record not found"}


@router.get("/sessions/store/search")
async def sessions_store_search(query: str = "", tag: str = "", project_name: str = "", status: Optional[str] = None, limit: int = 20):
    if status:
        st = SessionStatus(status) if status in [s.value for s in SessionStatus] else None
    else:
        st = None
    results = _session_store.search(query=query, tag=tag, project_name=project_name, status=st, limit=limit)
    return {"results": [r.to_dict() for r in results]}


@router.get("/sessions/store/active")
async def sessions_store_active():
    return {"active": [r.to_dict() for r in _session_store.find_active()]}


@router.get("/sessions/store/tag/{tag}")
async def sessions_store_by_tag(tag: str):
    return {"records": [r.to_dict() for r in _session_store.find_by_tag(tag)]}


@router.post("/sessions/store/save")
async def sessions_store_save(file_path: str = ""):
    success = _session_store.save_to_disk(file_path)
    return {"success": success}


@router.post("/sessions/store/load")
async def sessions_store_load(file_path: str = ""):
    success = _session_store.load_from_disk(file_path)
    return {"success": success}


@router.delete("/sessions/store/{record_id}")
async def sessions_store_delete(record_id: str):
    return {"deleted": _session_store.delete(record_id)}


# ============================================================
# Platform Bridge Endpoints
# ============================================================

from sparkai.agent.agent_platform_bridge import PlatformBridge, PlatformType, PlatformMessage, MessageRole, MessageFormat, get_platform_bridge

_platform_bridge = get_platform_bridge()


class BridgeSendRequest(BaseModel):
    platform: str = "web"
    role: str = "assistant"
    content: str = ""
    format: str = "markdown"
    target_id: str = ""
    metadata: Optional[Dict[str, Any]] = None


@router.get("/platform-bridge/stats")
async def platform_bridge_stats():
    return _platform_bridge.get_stats()


@router.get("/platform-bridge/platforms")
async def platform_bridge_platforms():
    configs = _platform_bridge.list_platforms()
    return {"platforms": {k.value: v for k, v in configs.items()}}


@router.post("/platform-bridge/send")
async def platform_bridge_send(req: BridgeSendRequest):
    platform = PlatformType(req.platform) if req.platform in [p.value for p in PlatformType] else PlatformType.WEB
    role = MessageRole(req.role) if req.role in [r.value for r in MessageRole] else MessageRole.ASSISTANT
    fmt = MessageFormat(req.format) if req.format in [f.value for f in MessageFormat] else MessageFormat.MARKDOWN
    msg = _platform_bridge.send(platform, role, req.content, fmt, req.target_id, req.metadata)
    return msg.to_dict()


@router.post("/platform-bridge/broadcast")
async def platform_bridge_broadcast(content: str, role: str = "system"):
    r = MessageRole(role) if role in [ro.value for ro in MessageRole] else MessageRole.SYSTEM
    msgs = _platform_bridge.send_to_all(r, content)
    return {"broadcast_count": len(msgs)}


@router.get("/platform-bridge/messages")
async def platform_bridge_messages(platform: Optional[str] = None, limit: int = 50):
    if platform:
        p = PlatformType(platform) if platform in [pt.value for pt in PlatformType] else None
    else:
        p = None
    msgs = _platform_bridge.get_messages(p, limit)
    return {"messages": [m.to_dict() for m in msgs]}


@router.get("/platform-bridge/config/{platform}")
async def platform_bridge_get_config(platform: str):
    if platform in [p.value for p in PlatformType]:
        pt = PlatformType(platform)
        cfg = _platform_bridge.get_config(pt)
        if cfg:
            return {"platform": platform, "config": cfg.to_dict()}
    return {"error": "Platform not found"}


@router.post("/platform-bridge/register-handler")
async def platform_bridge_register_handler(platform: str, callback_url: str = ""):
    if platform not in [p.value for p in PlatformType]:
        return {"error": "Invalid platform"}
    pt = PlatformType(platform)
    _platform_bridge.register_handler(pt, lambda msg: {"status": "handled", "callback": callback_url, "msg": msg.to_dict()})
    return {"success": True, "platform": platform}


# ============================================================
# Tool Composer Endpoints
# ============================================================

from sparkai.agent.agent_tool_composer import ToolComposer, ToolChain, ChainTemplate, ChainExecutionMode, get_tool_composer

_tool_composer = get_tool_composer()


@router.get("/tool-composer/stats")
async def tool_composer_stats():
    return _tool_composer.get_stats()


@router.post("/tool-composer/create-chain")
async def tool_composer_create_chain(name: str = "chain", mode: str = "sequential"):
    m = ChainExecutionMode(mode) if mode in [m.value for m in ChainExecutionMode] else ChainExecutionMode.SEQUENTIAL
    chain = _tool_composer.create_chain(name, m)
    return chain.to_dict()


@router.get("/tool-composer/chain/{chain_id}")
async def tool_composer_get_chain(chain_id: str):
    chain = _tool_composer.get_chain(chain_id)
    if chain:
        return chain.to_dict()
    return {"error": "Chain not found"}


@router.post("/tool-composer/chain/{chain_id}/add-step")
async def tool_composer_add_step(chain_id: str, tool_name: str, inputs: Optional[Dict[str, Any]] = None, depends_on: Optional[List[str]] = None, description: str = ""):
    chain = _tool_composer.get_chain(chain_id)
    if not chain:
        return {"error": "Chain not found"}
    step = chain.add_step(tool_name, inputs, depends_on, description)
    return step.to_dict()


@router.get("/tool-composer/templates")
async def tool_composer_templates(category: Optional[str] = None):
    templates = _tool_composer.list_templates(category)
    return {"templates": [t.to_dict() for t in templates]}


@router.post("/tool-composer/instantiate-template")
async def tool_composer_instantiate_template(template_id: str, name: str = ""):
    chain = _tool_composer.instantiate_template(template_id, name)
    if chain:
        return chain.to_dict()
    return {"error": "Template not found"}


# ============================================================
# Feedback Loop Endpoints
# ============================================================

from sparkai.agent.agent_feedback_loop import FeedbackLoop, FeedbackEntry, FeedbackSource, FeedbackSentiment, FeedbackSeverity, get_feedback_loop

_feedback_loop = get_feedback_loop()


@router.get("/feedback/stats")
async def feedback_stats():
    return _feedback_loop.get_stats()


@router.get("/feedback/report")
async def feedback_report():
    return _feedback_loop.get_quality_report()


@router.post("/feedback/record")
async def feedback_record(action_type: str, source: str = "user", sentiment: str = "neutral", score: float = 0.5, message: str = "", suggestion: str = "", severity: str = "info"):
    src = FeedbackSource(source) if source in [s.value for s in FeedbackSource] else FeedbackSource.USER
    sent = FeedbackSentiment(sentiment) if sentiment in [s.value for s in FeedbackSentiment] else FeedbackSentiment.NEUTRAL
    sev = FeedbackSeverity(severity) if severity in [s.value for s in FeedbackSeverity] else FeedbackSeverity.INFO
    entry = _feedback_loop.record(action_type, src, sent, score, message, suggestion, sev)
    return entry.to_dict()


@router.post("/feedback/playtest")
async def feedback_playtest(action_type: str, passed: bool = True, message: str = "", session_id: str = ""):
    entry = _feedback_loop.record_playtest_result(action_type, passed, message, session_id)
    return entry.to_dict()


@router.post("/feedback/compiler")
async def feedback_compiler(action_type: str, errors: int = 0, warnings: int = 0, message: str = ""):
    entry = _feedback_loop.record_compiler_result(action_type, errors, warnings, message)
    return entry.to_dict()


@router.post("/feedback/user-rating")
async def feedback_user_rating(action_type: str, rating: int = 3, comment: str = "", session_id: str = ""):
    entry = _feedback_loop.record_user_rating(action_type, rating, comment, session_id)
    return entry.to_dict()


@router.get("/feedback/suggestions")
async def feedback_suggestions():
    return {"suggestions": [s.to_dict() for s in _feedback_loop.get_pending_suggestions()]}


@router.post("/feedback/apply-suggestion")
async def feedback_apply_suggestion(suggestion_id: str):
    return {"applied": _feedback_loop.apply_suggestion(suggestion_id)}


@router.get("/feedback/action/{action_type}")
async def feedback_action_quality(action_type: str):
    stats = _feedback_loop.get_action_quality(action_type)
    return stats.to_dict() if stats else {"error": "No data for this action type"}


# ============================================================
# Agent Negotiation Endpoints
# ============================================================

from sparkai.agent.agent_negotiation import AgentNegotiation, NegotiationSession, VoteStance, Proposal, get_agent_negotiation

_agent_negotiation = get_agent_negotiation()


@router.get("/negotiation/stats")
async def negotiation_stats():
    return _agent_negotiation.get_stats()


@router.post("/negotiation/open")
async def negotiation_open(topic: str, description: str = ""):
    session = _agent_negotiation.open_session(topic, description)
    return session.to_dict()


@router.get("/negotiation/session/{session_id}")
async def negotiation_get_session(session_id: str):
    session = _agent_negotiation.get_session(session_id)
    if session:
        return session.to_dict()
    return {"error": "Session not found"}


@router.post("/negotiation/session/{session_id}/add-participant")
async def negotiation_add_participant(session_id: str, name: str, role: str, expertise: str = ""):
    session = _agent_negotiation.get_session(session_id)
    if not session:
        return {"error": "Session not found"}
    session.add_participant(name, role, expertise)
    return {"participants": session.participants}


@router.post("/negotiation/session/{session_id}/propose")
async def negotiation_propose(session_id: str, agent_name: str, agent_role: str, title: str, description: str, justification: str = ""):
    session = _agent_negotiation.get_session(session_id)
    if not session:
        return {"error": "Session not found"}
    proposal = session.propose(agent_name, agent_role, title, description, justification)
    return proposal.to_dict()


@router.post("/negotiation/session/{session_id}/vote")
async def negotiation_vote(session_id: str, agent_name: str, agent_role: str, proposal_id: str, stance: str = "support", reasoning: str = "", conditions: str = ""):
    session = _agent_negotiation.get_session(session_id)
    if not session:
        return {"error": "Session not found"}
    s = VoteStance(stance) if stance in [v.value for v in VoteStance] else VoteStance.SUPPORT
    vote = session.cast_vote(agent_name, agent_role, proposal_id, s, reasoning, conditions)
    return vote.to_dict()


@router.post("/negotiation/session/{session_id}/advance")
async def negotiation_advance(session_id: str):
    phase = _agent_negotiation.advance_phase(session_id)
    return {"phase": phase.value if phase else "null"}


@router.post("/negotiation/session/{session_id}/resolve")
async def negotiation_resolve(session_id: str, method: str = "majority"):
    result = _agent_negotiation.resolve_session(session_id, method)
    return result.to_dict() if result else {"error": "Could not resolve"}


@router.get("/negotiation/sessions")
async def negotiation_sessions(active_only: bool = True):
    sessions = _agent_negotiation.list_sessions(active_only)
    return {"sessions": [s.to_dict() for s in sessions]}


# ============================================================
# Debug Draw System Endpoints
# ============================================================

from sparkai.engine.debug_draw_system import DebugDrawSystem, DrawCategory, get_debug_draw_system

_debug_draw_system = get_debug_draw_system()


@router.get("/debug-draw/stats")
async def debug_draw_stats():
    return _debug_draw_system.get_stats()


@router.post("/debug-draw/line")
async def debug_draw_line(x1: float = 0, y1: float = 0, x2: float = 100, y2: float = 0, r: int = 0, g: int = 255, b: int = 0, a: int = 200, category: str = "PHYSICS"):
    try:
        cat = DrawCategory[category]
    except (KeyError, AttributeError):
        cat = DrawCategory.PHYSICS
    cmd_id = _debug_draw_system.draw_line(x1, y1, x2, y2, (r, g, b, a), cat, 1.0)
    return {"cmd_id": cmd_id}


@router.post("/debug-draw/circle")
async def debug_draw_circle(cx: float = 0, cy: float = 0, radius: float = 10, r: int = 0, g: int = 255, b: int = 0, a: int = 200, category: str = "PHYSICS", fill: bool = False):
    try:
        cat = DrawCategory[category]
    except (KeyError, AttributeError):
        cat = DrawCategory.PHYSICS
    cmd_id = _debug_draw_system.draw_circle(cx, cy, radius, (r, g, b, a), cat, fill)
    return {"cmd_id": cmd_id}


@router.post("/debug-draw/rect")
async def debug_draw_rect(x: float = 0, y: float = 0, w: float = 100, h: float = 100, r: int = 0, g: int = 255, b: int = 0, a: int = 200, category: str = "PHYSICS", fill: bool = False):
    try:
        cat = DrawCategory[category]
    except (KeyError, AttributeError):
        cat = DrawCategory.PHYSICS
    cmd_id = _debug_draw_system.draw_rect(x, y, w, h, (r, g, b, a), cat, fill)
    return {"cmd_id": cmd_id}


@router.post("/debug-draw/clear")
async def debug_draw_clear():
    _debug_draw_system.clear()
    return {"cleared": True}


@router.post("/debug-draw/toggle")
async def debug_draw_toggle(enabled: bool = True):
    _debug_draw_system.enabled = enabled
    return {"enabled": _debug_draw_system.enabled}


@router.post("/debug-draw/show-category")
async def debug_draw_show_category(category: str = "ALL"):
    try:
        cat = DrawCategory[category]
        _debug_draw_system.show_category(cat)
    except (KeyError, AttributeError):
        _debug_draw_system.show_category(DrawCategory.ALL)
    return {"ok": True}


# ============================================================
# Prefab System Endpoints
# ============================================================

from sparkai.engine.prefab_system import PrefabSystem, PrefabTemplate, PrefabInstance, get_prefab_system

_prefab_system = get_prefab_system()


@router.get("/prefab/stats")
async def prefab_stats():
    return _prefab_system.get_stats()


@router.post("/prefab/create-template")
async def prefab_create_template(name: str, category: str = "general", description: str = ""):
    template = _prefab_system.create_template(name, category, description)
    return template.to_dict()


@router.get("/prefab/templates")
async def prefab_templates(category: Optional[str] = None, tag: Optional[str] = None):
    templates = _prefab_system.list_templates(category, tag)
    return {"templates": [t.to_dict() for t in templates]}


@router.get("/prefab/template/{template_id}")
async def prefab_get_template(template_id: str):
    template = _prefab_system.get_template(template_id)
    if template:
        return template.to_dict()
    return {"error": "Template not found"}


@router.post("/prefab/create-variant")
async def prefab_create_variant(parent_template_id: str, name: str):
    variant = _prefab_system.create_variant(parent_template_id, name)
    if variant:
        return variant.to_dict()
    return {"error": "Parent template not found"}


@router.post("/prefab/instantiate")
async def prefab_instantiate(template_id: str, x: float = 0.0, y: float = 0.0):
    instance = _prefab_system.instantiate(template_id, x, y)
    if instance:
        return instance.to_dict()
    return {"error": "Template not found"}


@router.get("/prefab/instances")
async def prefab_instances(template_id: Optional[str] = None):
    instances = _prefab_system.list_instances(template_id)
    return {"instances": [i.to_dict() for i in instances]}


# ============================================================
# Physics Constraints Endpoints
# ============================================================

from sparkai.engine.physics_constraints import PhysicsConstraints, ConstraintType, get_physics_constraints

_physics_constraints = get_physics_constraints()


@router.get("/physics-constraints/stats")
async def physics_constraints_stats():
    return _physics_constraints.get_stats()


@router.post("/physics-constraints/create-spring")
async def physics_constraints_create_spring(body_a_id: str = "", body_b_id: str = "", rest_length: float = 50.0):
    constraint = _physics_constraints.create_spring(body_a_id, body_b_id, rest_length)
    return constraint.to_dict()


@router.post("/physics-constraints/create-hinge")
async def physics_constraints_create_hinge(body_a_id: str = "", body_b_id: str = "", anchor_x: float = 0, anchor_y: float = 0):
    constraint = _physics_constraints.create_hinge(body_a_id, body_b_id, (anchor_x, anchor_y))
    return constraint.to_dict()


@router.post("/physics-constraints/create-slider")
async def physics_constraints_create_slider(body_a_id: str = "", body_b_id: str = "", axis_x: float = 1.0, axis_y: float = 0.0):
    constraint = _physics_constraints.create_slider(body_a_id, body_b_id, (axis_x, axis_y))
    return constraint.to_dict()


@router.post("/physics-constraints/create-distance")
async def physics_constraints_create_distance(body_a_id: str = "", body_b_id: str = "", distance: float = 100.0):
    constraint = _physics_constraints.create_distance(body_a_id, body_b_id, distance)
    return constraint.to_dict()


@router.post("/physics-constraints/create-weld")
async def physics_constraints_create_weld(body_a_id: str = "", body_b_id: str = ""):
    constraint = _physics_constraints.create_weld(body_a_id, body_b_id)
    return constraint.to_dict()


@router.post("/physics-constraints/enable")
async def physics_constraints_enable(constraint_id: str):
    return {"enabled": _physics_constraints.enable(constraint_id)}


@router.post("/physics-constraints/disable")
async def physics_constraints_disable(constraint_id: str):
    return {"disabled": _physics_constraints.disable(constraint_id)}


# ============================================================
# Spatial Index Endpoints
# ============================================================

from sparkai.engine.spatial_index import SpatialIndex, SpatialEntry, get_spatial_index

_spatial_index = get_spatial_index()


@router.get("/spatial-index/stats")
async def spatial_index_stats():
    return _spatial_index.get_stats()


@router.post("/spatial-index/initialize")
async def spatial_index_initialize(x: float = 0, y: float = 0, width: float = 10000, height: float = 10000):
    _spatial_index.initialize(x, y, width, height)
    return _spatial_index.get_stats()


@router.post("/spatial-index/insert")
async def spatial_index_insert(object_id: str, x: float = 0, y: float = 0, width: float = 0, height: float = 0, object_type: str = "", layer: int = 0):
    entry = _spatial_index.insert(object_id, x, y, width, height, object_type, layer)
    return entry.to_dict() if entry else {"error": "Insert failed"}


@router.delete("/spatial-index/{object_id}")
async def spatial_index_remove(object_id: str):
    return {"removed": _spatial_index.remove(object_id)}


@router.get("/spatial-index/query-range")
async def spatial_index_query_range(x: float = 0, y: float = 0, width: float = 500, height: float = 500, layer: Optional[int] = None):
    results = _spatial_index.query_range(x, y, width, height, layer)
    return {"results": [r.to_dict() for r in results], "count": len(results)}


@router.get("/spatial-index/nearest")
async def spatial_index_nearest(px: float = 0, py: float = 0, n: int = 1, max_distance: float = 10000):
    results = _spatial_index.find_nearest(px, py, n, max_distance)
    return {"results": [r.to_dict() for r in results]}


@router.get("/spatial-index/entry/{object_id}")
async def spatial_index_get_entry(object_id: str):
    entry = _spatial_index.get_entry(object_id)
    if entry:
        return entry.to_dict()
    return {"error": "Entry not found"}


# === Simulation Environment ===

from sparkai.agent.agent_simulation_env import SimulationEnv, SimScenario, SimulationMode, get_simulation_env

_simulation_env = get_simulation_env()


@router.get("/simulation/stats")
async def simulation_stats():
    return _simulation_env.get_stats()


@router.post("/simulation/scenario")
async def simulation_create_scenario(name: str, description: str = "", seed: int = 42, tags: str = ""):
    tag_list = [t.strip() for t in tags.split(",") if t.strip()] if tags else None
    scenario = _simulation_env.create_scenario(name, description, seed, tag_list)
    return scenario.to_dict()


@router.get("/simulation/scenarios")
async def simulation_list_scenarios(tag: Optional[str] = None):
    scenarios = _simulation_env.list_scenarios(tag)
    return {"scenarios": [s.to_dict() for s in scenarios]}


@router.get("/simulation/scenario/{scenario_id}")
async def simulation_get_scenario(scenario_id: str):
    scenario = _simulation_env.get_scenario(scenario_id)
    if scenario:
        return scenario.to_dict()
    return {"error": "Scenario not found"}


@router.post("/simulation/scenario/{scenario_id}/action")
async def simulation_add_action(
    scenario_id: str, action_name: str, tool: str,
    parameters: str = "{}", expected_outcome: str = "",
    preconditions: str = "", postconditions: str = "",
):
    import json
    try:
        params = json.loads(parameters)
    except json.JSONDecodeError:
        params = {}
    pre_list = [p.strip() for p in preconditions.split(",") if p.strip()] if preconditions else None
    post_list = [p.strip() for p in postconditions.split(",") if p.strip()] if postconditions else None
    action = _simulation_env.add_action_to_scenario(
        scenario_id, action_name, tool, params, expected_outcome, pre_list, post_list
    )
    if action:
        return {"action_id": action.action_id, "name": action.name}
    return {"error": "Scenario not found"}


@router.post("/simulation/run/{scenario_id}")
async def simulation_run_scenario(scenario_id: str, mode: str = "dry_run"):
    try:
        m = SimulationMode(mode)
    except ValueError:
        m = SimulationMode.DRY_RUN
    run = _simulation_env.run_scenario(scenario_id, m)
    if run:
        return run.to_dict()
    return {"error": "Scenario not found"}


@router.get("/simulation/runs")
async def simulation_list_runs(limit: int = 50):
    runs = _simulation_env.list_runs(limit)
    return {"runs": [r.to_dict() for r in runs]}


@router.get("/simulation/run/{run_id}")
async def simulation_get_run(run_id: str):
    run = _simulation_env.replay_run(run_id)
    if run:
        return run.to_dict()
    return {"error": "Run not found"}


@router.post("/simulation/clear-history")
async def simulation_clear_history():
    _simulation_env.clear_history()
    return {"success": True}


@router.delete("/simulation/scenario/{scenario_id}")
async def simulation_delete_scenario(scenario_id: str):
    success = _simulation_env.delete_scenario(scenario_id)
    return {"success": success}


# === Goal Decomposer ===

from sparkai.agent.agent_goal_decomposer import GoalDecomposer, GoalTree, GoalLevel, ChecklistStatus, get_goal_decomposer

_goal_decomposer = get_goal_decomposer()


@router.get("/goal-decomposer/stats")
async def goal_decomposer_stats():
    return _goal_decomposer.get_stats()


@router.post("/goal-decomposer/create-tree")
async def goal_decomposer_create_tree(root_title: str, root_description: str = ""):
    tree = _goal_decomposer.create_goal_tree(root_title, root_description)
    return tree.to_full_dict()


@router.get("/goal-decomposer/trees")
async def goal_decomposer_list_trees():
    trees = _goal_decomposer.list_trees()
    return {"trees": [t.to_dict() for t in trees]}


@router.get("/goal-decomposer/tree/{tree_id}")
async def goal_decomposer_get_tree(tree_id: str):
    tree = _goal_decomposer.get_tree(tree_id)
    if tree:
        return tree.to_full_dict()
    return {"error": "Tree not found"}


@router.post("/goal-decomposer/tree/{tree_id}/node")
async def goal_decomposer_add_node(
    tree_id: str, title: str, description: str = "", parent_id: str = "",
    level: str = "task", priority: int = 5, depends_on: str = "", tags: str = "",
):
    try:
        lvl = GoalLevel[level.upper()]
    except KeyError:
        lvl = GoalLevel.TASK
    dep_list = [d.strip() for d in depends_on.split(",") if d.strip()] if depends_on else None
    tag_list = [t.strip() for t in tags.split(",") if t.strip()] if tags else None
    node = _goal_decomposer.add_goal_node(
        tree_id, title, description, parent_id or None, lvl, priority, dep_list, tag_list
    )
    if node:
        return node.to_dict()
    return {"error": "Could not add node"}


@router.get("/goal-decomposer/tree/{tree_id}/ready")
async def goal_decomposer_ready_nodes(tree_id: str, limit: int = 10):
    tasks = _goal_decomposer.get_next_tasks(tree_id, limit)
    return {"tasks": [t.to_dict() for t in tasks]}


@router.post("/goal-decomposer/tree/{tree_id}/node/{node_id}/status")
async def goal_decomposer_update_status(tree_id: str, node_id: str, status: str = "completed"):
    try:
        st = ChecklistStatus(status)
    except ValueError:
        st = ChecklistStatus.COMPLETED
    node = _goal_decomposer.update_node_status(tree_id, node_id, st)
    if node:
        return node.to_dict()
    return {"error": "Node not found"}


@router.post("/goal-decomposer/tree/{tree_id}/dependency")
async def goal_decomposer_set_dependency(tree_id: str, source_id: str, target_id: str):
    success = _goal_decomposer.set_dependency(tree_id, source_id, target_id)
    return {"success": success}


@router.delete("/goal-decomposer/tree/{tree_id}")
async def goal_decomposer_delete_tree(tree_id: str):
    success = _goal_decomposer.delete_tree(tree_id)
    return {"success": success}


# === Prompt Template Library ===

from sparkai.agent.agent_prompt_template import PromptTemplateLib, TemplateEntry, TemplateDomain, TemplateRole, VariableDef, get_prompt_template_lib

_prompt_template_lib = get_prompt_template_lib()


@router.get("/prompt-template/stats")
async def prompt_template_stats():
    return _prompt_template_lib.get_stats()


@router.post("/prompt-template/create")
async def prompt_template_create(
    name: str, content: str, domain: str = "general", role: str = "user",
    description: str = "", tags: str = "",
):
    try:
        dom = TemplateDomain(domain)
    except ValueError:
        dom = TemplateDomain.GENERAL
    try:
        rl = TemplateRole(role)
    except ValueError:
        rl = TemplateRole.USER
    tag_list = [t.strip() for t in tags.split(",") if t.strip()] if tags else None
    template = _prompt_template_lib.create_template(name, content, dom, rl, description, tags=tag_list)
    return template.to_dict()


@router.get("/prompt-template/templates")
async def prompt_template_list(domain: Optional[str] = None, tag: Optional[str] = None):
    dom = TemplateDomain(domain) if domain else None
    templates = _prompt_template_lib.list_templates(dom, tag)
    return {"templates": [t.to_dict() for t in templates]}


@router.get("/prompt-template/template/{template_id}")
async def prompt_template_get(template_id: str):
    template = _prompt_template_lib.get_template(template_id)
    if template:
        return template.to_dict()
    return {"error": "Template not found"}


@router.post("/prompt-template/resolve/{template_id}")
async def prompt_template_resolve(template_id: str, variables: str = "{}"):
    import json
    try:
        vars_ = json.loads(variables)
    except json.JSONDecodeError:
        vars_ = {}
    result = _prompt_template_lib.resolve_template(template_id, vars_)
    if result:
        return {"resolved": result}
    return {"error": "Resolution failed"}


@router.get("/prompt-template/variables/{template_id}")
async def prompt_template_variables(template_id: str):
    vars_ = _prompt_template_lib.get_variables(template_id)
    return {"variables": [{"name": v.name, "default": v.default, "description": v.description, "required": v.required} for v in vars_]}


@router.post("/prompt-template/compose")
async def prompt_template_compose(
    name: str, template_ids: str = "", variables_list: str = "[]",
):
    import json
    ids = [t.strip() for t in template_ids.split(",") if t.strip()]
    try:
        vars_list = json.loads(variables_list)
    except json.JSONDecodeError:
        vars_list = [{}] * len(ids)
    composed = _prompt_template_lib.compose_prompt(name, ids, vars_list)
    if composed:
        return composed.to_dict()
    return {"error": "Composition failed"}


@router.put("/prompt-template/template/{template_id}")
async def prompt_template_update(template_id: str, content: str):
    template = _prompt_template_lib.update_template(template_id, content)
    if template:
        return template.to_dict()
    return {"error": "Template not found"}


@router.delete("/prompt-template/template/{template_id}")
async def prompt_template_delete(template_id: str):
    success = _prompt_template_lib.delete_template(template_id)
    return {"success": success}


# === Semantic Memory ===

from sparkai.agent.agent_semantic_memory import SemanticMemory, MemoryVector, MemoryCategory, get_semantic_memory

_semantic_memory = get_semantic_memory()


@router.get("/semantic-memory/stats")
async def semantic_memory_stats():
    return _semantic_memory.get_stats()


@router.post("/semantic-memory/store")
async def semantic_memory_store(
    content: str, category: str = "general", importance: float = 0.5,
    tags: str = "",
):
    try:
        cat = MemoryCategory(category)
    except ValueError:
        cat = MemoryCategory.GENERAL
    tag_list = [t.strip() for t in tags.split(",") if t.strip()] if tags else None
    memory = _semantic_memory.store(content, None, cat, importance, tags=tag_list)
    return memory.to_full_dict()


@router.post("/semantic-memory/search")
async def semantic_memory_search(
    query: str, top_k: int = 10, category: Optional[str] = None,
    min_similarity: float = 0.0, tags: Optional[str] = None,
):
    cat = MemoryCategory(category) if category else None
    tag_list = [t.strip() for t in tags.split(",") if t.strip()] if tags else None
    results = _semantic_memory.search(query, top_k, cat, min_similarity, tag_list)
    return {"results": [{"memory": m.to_full_dict(), "score": round(s, 4)} for m, s in results]}


@router.get("/semantic-memory/memory/{memory_id}")
async def semantic_memory_get(memory_id: str):
    memory = _semantic_memory.get_memory(memory_id)
    if memory:
        return memory.to_full_dict()
    return {"error": "Memory not found"}


@router.get("/semantic-memory/similar/{memory_id}")
async def semantic_memory_similar(memory_id: str, top_k: int = 5):
    results = _semantic_memory.search_similar(memory_id, top_k)
    return {"results": [{"memory": m.to_full_dict(), "score": round(s, 4)} for m, s in results]}


@router.post("/semantic-memory/importance/{memory_id}")
async def semantic_memory_update_importance(memory_id: str, importance: float = 0.5):
    success = _semantic_memory.update_importance(memory_id, importance)
    return {"success": success}


@router.get("/semantic-memory/category/{category}")
async def semantic_memory_by_category(category: str, limit: int = 100):
    try:
        cat = MemoryCategory(category)
    except ValueError:
        cat = MemoryCategory.GENERAL
    memories = _semantic_memory.list_by_category(cat, limit)
    return {"memories": [m.to_dict() for m in memories]}


@router.get("/semantic-memory/tag/{tag}")
async def semantic_memory_by_tag(tag: str):
    memories = _semantic_memory.list_by_tag(tag)
    return {"memories": [m.to_dict() for m in memories]}


@router.post("/semantic-memory/consolidate")
async def semantic_memory_consolidate(category: str = "general", min_similarity: float = 0.85):
    try:
        cat = MemoryCategory(category)
    except ValueError:
        cat = MemoryCategory.GENERAL
    merged = _semantic_memory.consolidate(cat, min_similarity)
    return {"merged": merged}


@router.post("/semantic-memory/context")
async def semantic_memory_context(query: str, window_size: int = 5):
    context = _semantic_memory.get_context_window(query, window_size)
    return {"context": context}


@router.delete("/semantic-memory/memory/{memory_id}")
async def semantic_memory_delete(memory_id: str):
    success = _semantic_memory.delete_memory(memory_id)
    return {"success": success}


# === Engine Subsystem Endpoints ===

from sparkai.engine.procedural_generation import ProceduralGenerator, LootTable, LootEntry, get_procedural_generator

_procedural_generator = get_procedural_generator()


@router.get("/procedural-generation/stats")
async def procedural_generation_stats():
    return _procedural_generator.get_stats()


@router.post("/procedural-generation/terrain")
async def procedural_generation_terrain(
    width: int = 64, height: int = 64, seed: int = 42,
    octaves: int = 4, persistence: float = 0.5, scale: float = 32.0,
):
    terrain = _procedural_generator.generate_terrain(width, height, seed, octaves, persistence, scale)
    return terrain.to_dict()


@router.get("/procedural-generation/terrain/{map_id}")
async def procedural_generation_get_terrain(map_id: str):
    terrain = _procedural_generator.get_terrain_map(map_id)
    if terrain:
        return terrain.to_dict()
    return {"error": "Terrain map not found"}


@router.post("/procedural-generation/dungeon")
async def procedural_generation_dungeon(
    width: int = 80, height: int = 60, seed: int = 42,
    room_count: int = 12, min_room_size: int = 4, max_room_size: int = 10,
):
    dungeon = _procedural_generator.generate_dungeon(width, height, seed, room_count, min_room_size, max_room_size)
    return dungeon.to_dict()


@router.get("/procedural-generation/dungeon/{map_id}")
async def procedural_generation_get_dungeon(map_id: str):
    dungeon = _procedural_generator.get_dungeon_map(map_id)
    if dungeon:
        return dungeon.to_dict()
    return {"error": "Dungeon map not found"}


@router.post("/procedural-generation/loot-table")
async def procedural_generation_create_loot_table(name: str, min_rolls: int = 1, max_rolls: int = 3):
    table = _procedural_generator.create_loot_table(name, min_rolls, max_rolls)
    return table.to_dict()


@router.post("/procedural-generation/loot-table/{table_id}/entry")
async def procedural_generation_add_loot_entry(
    table_id: str, name: str, weight: float = 1.0,
    min_qty: int = 1, max_qty: int = 1, category: str = "common",
):
    entry = _procedural_generator.add_loot_entry(table_id, name, weight, min_qty, max_qty, category)
    if entry:
        return {"item_id": entry.item_id, "name": entry.name, "weight": entry.weight}
    return {"error": "Loot table not found"}


@router.post("/procedural-generation/loot-table/{table_id}/roll")
async def procedural_generation_roll_loot(table_id: str):
    results = _procedural_generator.roll_loot(table_id)
    return {"items": [{"name": e.name, "category": e.category} for e in results]}


@router.get("/procedural-generation/loot-tables")
async def procedural_generation_loot_tables():
    tables = _procedural_generator.list_loot_tables()
    return {"tables": [t.to_dict() for t in tables]}


from sparkai.engine.ragdoll_physics import RagdollSystem, RagdollSkeleton, get_ragdoll_system

_ragdoll_system = get_ragdoll_system()


@router.get("/ragdoll-physics/stats")
async def ragdoll_physics_stats():
    return _ragdoll_system.get_stats()


@router.post("/ragdoll-physics/create-humanoid")
async def ragdoll_physics_create_humanoid(name: str = "humanoid"):
    skeleton = _ragdoll_system.build_humanoid(name)
    return skeleton.to_dict()


@router.post("/ragdoll-physics/create-skeleton")
async def ragdoll_physics_create_skeleton(name: str = "", gravity_y: float = -9.81):
    from sparkai.engine.ragdoll_physics import Vec3
    skeleton = _ragdoll_system.create_skeleton(name, Vec3(0.0, gravity_y, 0.0))
    return skeleton.to_dict()


@router.get("/ragdoll-physics/skeleton/{skeleton_id}")
async def ragdoll_physics_get_skeleton(skeleton_id: str):
    skeleton = _ragdoll_system.get_skeleton(skeleton_id)
    if skeleton:
        return skeleton.to_dict()
    return {"error": "Skeleton not found"}


@router.post("/ragdoll-physics/activate/{skeleton_id}")
async def ragdoll_physics_activate(skeleton_id: str):
    success = _ragdoll_system.activate_skeleton(skeleton_id)
    return {"success": success}


@router.post("/ragdoll-physics/deactivate/{skeleton_id}")
async def ragdoll_physics_deactivate(skeleton_id: str):
    success = _ragdoll_system.deactivate_skeleton(skeleton_id)
    return {"success": success}


@router.post("/ragdoll-physics/impact/{skeleton_id}")
async def ragdoll_physics_impact(skeleton_id: str, fx: float = 0, fy: float = 50, fz: float = 0, bone: str = ""):
    success = _ragdoll_system.apply_impact(skeleton_id, (fx, fy, fz), bone or None)
    return {"success": success}


@router.get("/ragdoll-physics/skeletons")
async def ragdoll_physics_skeletons():
    skeletons = _ragdoll_system.list_skeletons()
    return {"skeletons": [s.to_dict() for s in skeletons]}


@router.delete("/ragdoll-physics/skeleton/{skeleton_id}")
async def ragdoll_physics_delete_skeleton(skeleton_id: str):
    success = _ragdoll_system.delete_skeleton(skeleton_id)
    return {"success": success}


from sparkai.engine.game_telemetry import TelemetryEngine, TelemetryEvent, EventCategory, EventSeverity, get_telemetry_engine

_telemetry_engine = get_telemetry_engine()


@router.get("/telemetry/stats")
async def telemetry_stats():
    return _telemetry_engine.get_stats()


@router.post("/telemetry/event")
async def telemetry_track_event(
    category: str = "player", event_type: str = "", player_id: str = "",
    session_id: str = "", data: str = "{}",
):
    import json
    try:
        cat = EventCategory(category)
    except ValueError:
        cat = EventCategory.PLAYER
    try:
        event_data = json.loads(data)
    except json.JSONDecodeError:
        event_data = {}
    event = _telemetry_engine.track_event(cat, event_type, event_data, player_id, session_id)
    if event:
        return event.to_dict()
    return {"error": "Telemetry disabled"}


@router.post("/telemetry/session/start")
async def telemetry_start_session(player_id: str = ""):
    session = _telemetry_engine.start_session(player_id)
    return session.to_dict()


@router.post("/telemetry/session/{session_id}/end")
async def telemetry_end_session(session_id: str):
    success = _telemetry_engine.end_session(session_id)
    return {"success": success}


@router.get("/telemetry/sessions")
async def telemetry_sessions(limit: int = 50):
    sessions = _telemetry_engine.list_sessions(limit)
    return {"sessions": [s.to_dict() for s in sessions]}


@router.get("/telemetry/session/{session_id}")
async def telemetry_get_session(session_id: str):
    session = _telemetry_engine.get_session(session_id)
    if session:
        return session.to_dict()
    return {"error": "Session not found"}


@router.get("/telemetry/events")
async def telemetry_events(category: Optional[str] = None, limit: int = 100):
    if category:
        try:
            cat = EventCategory(category)
        except ValueError:
            cat = EventCategory.PLAYER
        events = _telemetry_engine.get_events_by_category(cat, limit)
    else:
        events = _telemetry_engine._events[-limit:]
    return {"events": [e.to_full_dict() for e in events]}


@router.get("/telemetry/heatmap")
async def telemetry_heatmap(category: Optional[str] = None):
    cat = EventCategory(category) if category else None
    points = _telemetry_engine.get_heatmap_data(cat)
    return {"points": points}


from sparkai.engine.network_rpc import NetworkRPC, RPCCallType, RPCDelivery, get_network_rpc

_network_rpc = get_network_rpc()


@router.get("/network-rpc/stats")
async def network_rpc_stats():
    return _network_rpc.get_stats()


@router.post("/network-rpc/register-handler")
async def network_rpc_register_handler(procedure: str):
    def _passthrough(params):
        return {"received": True, "params": params}
    _network_rpc.register_handler(procedure, _passthrough)
    return {"success": True, "procedure": procedure}


@router.post("/network-rpc/call")
async def network_rpc_call(
    procedure: str, parameters: str = "{}", target_id: str = "",
    call_type: str = "request", delivery: str = "reliable",
):
    import json
    try:
        params = json.loads(parameters)
    except json.JSONDecodeError:
        params = {}
    try:
        ct = RPCCallType(call_type)
    except ValueError:
        ct = RPCCallType.REQUEST
    try:
        dl = RPCDelivery(delivery)
    except ValueError:
        dl = RPCDelivery.RELIABLE
    result = _network_rpc.call(procedure, params, target_id, ct, dl)
    if result:
        return result.to_dict()
    return {"error": "Call failed"}


@router.post("/network-rpc/broadcast")
async def network_rpc_broadcast(procedure: str, parameters: str = "{}"):
    import json
    try:
        params = json.loads(parameters)
    except json.JSONDecodeError:
        params = {}
    results = _network_rpc.broadcast(procedure, params)
    return {"results": [r.to_dict() for r in results]}


@router.get("/network-rpc/handlers")
async def network_rpc_handlers():
    return {"handlers": _network_rpc.list_handlers()}


@router.get("/network-rpc/history")
async def network_rpc_history(limit: int = 50):
    history = _network_rpc.get_call_history(limit)
    return {"history": [h.to_dict() for h in history]}


@router.post("/network-rpc/process-queue")
async def network_rpc_process_queue(max_messages: int = 50):
    processed = _network_rpc.process_queue(max_messages)
    return {"processed": processed, "queue_remaining": _network_rpc.get_queue_size()}


@router.post("/network-rpc/cleanup")
async def network_rpc_cleanup():
    timed_out = _network_rpc.cleanup_timed_out()
    return {"timed_out": timed_out}


# === Intent Classifier ===

from sparkai.agent.agent_intent_classifier import IntentClassifier, IntentDomain, get_intent_classifier

_intent_classifier = get_intent_classifier()


@router.get("/intent-classifier/stats")
async def intent_classifier_stats():
    return _intent_classifier.get_stats()


@router.post("/intent-classifier/classify")
async def intent_classifier_classify(query: str):
    result = _intent_classifier.classify(query)
    return result.to_dict()


@router.post("/intent-classifier/route")
async def intent_classifier_route(query: str):
    target = _intent_classifier.get_routing_target(query)
    return target


@router.get("/intent-classifier/history")
async def intent_classifier_history(limit: int = 20):
    history = _intent_classifier.get_history(limit)
    return {"history": [h.to_dict() for h in history]}


@router.post("/intent-classifier/add-rule")
async def intent_classifier_add_rule(
    domain: str = "general", patterns: str = "", keywords: str = "",
    target_agent: str = "", tool_chain: str = "", priority: int = 5,
):
    try:
        dom = IntentDomain(domain)
    except ValueError:
        dom = IntentDomain.GENERAL
    pattern_list = [p.strip() for p in patterns.split("|") if p.strip()]
    keyword_list = [k.strip() for k in keywords.split(",") if k.strip()]
    rule = _intent_classifier.add_rule(dom, pattern_list, keyword_list, target_agent, tool_chain, priority)
    return {"rule_id": rule.rule_id, "domain": dom.value}


@router.post("/intent-classifier/clear-history")
async def intent_classifier_clear_history():
    _intent_classifier.clear_history()
    return {"success": True}


# === Context Assembler ===

from sparkai.agent.agent_context_assembler import ContextAssembler, ContextSource, ContextFormat, get_context_assembler

_context_assembler = get_context_assembler()


@router.get("/context-assembler/stats")
async def context_assembler_stats():
    return _context_assembler.get_stats()


@router.post("/context-assembler/register-tool")
async def context_assembler_register_tool(
    name: str, description: str = "", category: str = "",
    parameters: str = "{}", returns: str = "", example: str = "",
):
    import json
    try:
        params = json.loads(parameters)
    except json.JSONDecodeError:
        params = {}
    tool = _context_assembler.register_tool(name, description, category, params, returns, example)
    return tool.to_dict()


@router.post("/context-assembler/set-project-meta")
async def context_assembler_set_project_meta(
    name: str = "", genre: str = "", platform: str = "",
    resolution: str = "", language: str = "", art_style: str = "",
    description: str = "",
):
    _context_assembler.set_project_meta(name, genre, platform, resolution, language, art_style, description)
    return {"success": True}


@router.post("/context-assembler/user-preference")
async def context_assembler_set_user_preference(key: str, value: str):
    _context_assembler.set_user_preference(key, value)
    return {"success": True}


@router.post("/context-assembler/assemble")
async def context_assembler_assemble(format: str = "markdown", history: int = 10):
    try:
        fmt = ContextFormat(format)
    except ValueError:
        fmt = ContextFormat.MARKDOWN
    ctx = _context_assembler.assemble(format=fmt, include_recent_history=history)
    return ctx.to_dict()


@router.post("/context-assembler/assemble-for-tool")
async def context_assembler_assemble_for_tool(tool_name: str):
    ctx = _context_assembler.assemble_for_tool(tool_name)
    return ctx.to_dict()


@router.post("/context-assembler/assemble-minimal")
async def context_assembler_assemble_minimal(purpose: str = ""):
    ctx = _context_assembler.assemble_minimal(purpose)
    return ctx.to_dict()


@router.get("/context-assembler/tools")
async def context_assembler_tools(category: str = ""):
    tools = _context_assembler.list_tools(category or None)
    return {"tools": [t.to_dict() for t in tools]}


@router.get("/context-assembler/categories")
async def context_assembler_categories():
    return {"categories": _context_assembler.list_categories()}


@router.post("/context-assembler/snapshot")
async def context_assembler_snapshot(
    active_scene: str = "", entity_count: int = 0,
):
    snapshot = _context_assembler.take_state_snapshot(active_scene, entity_count)
    return snapshot.to_dict()


# === Action Sequencer ===

from sparkai.agent.agent_action_sequencer import ActionSequencer, ExecutionPipeline, OpType, OpStatus, get_action_sequencer

_action_sequencer = get_action_sequencer()


@router.get("/action-sequencer/stats")
async def action_sequencer_stats():
    return _action_sequencer.get_stats()


@router.post("/action-sequencer/create-pipeline")
async def action_sequencer_create_pipeline(name: str = ""):
    pipeline = _action_sequencer.create_pipeline(name)
    return pipeline.to_full_dict()


@router.get("/action-sequencer/pipelines")
async def action_sequencer_pipelines():
    pipelines = _action_sequencer.list_pipelines()
    return {"pipelines": [p.to_dict() for p in pipelines]}


@router.get("/action-sequencer/pipeline/{pipeline_id}")
async def action_sequencer_get_pipeline(pipeline_id: str):
    pipeline = _action_sequencer.get_pipeline(pipeline_id)
    if pipeline:
        return pipeline.to_full_dict()
    return {"error": "Pipeline not found"}


@router.post("/action-sequencer/pipeline/{pipeline_id}/operation")
async def action_sequencer_add_operation(
    pipeline_id: str, op_type: str = "property_set",
    description: str = "", target: str = "", priority: int = 0,
    depends_on: str = "",
):
    try:
        ot = OpType(op_type)
    except ValueError:
        ot = OpType.PROPERTY_SET
    dep_list = [d.strip() for d in depends_on.split(",") if d.strip()] if depends_on else None
    op = _action_sequencer.add_operation(pipeline_id, ot, description, target, priority=priority, depends_on=dep_list)
    if op:
        return op.to_dict()
    return {"error": "Could not add operation"}


@router.post("/action-sequencer/pipeline/{pipeline_id}/auto-sequence")
async def action_sequencer_auto_sequence(
    pipeline_id: str, operations: str = "[]",
):
    import json
    try:
        ops = json.loads(operations)
    except json.JSONDecodeError:
        ops = []
    result = _action_sequencer.auto_sequence(pipeline_id, ops)
    return {"sequenced_operations": [r.to_dict() for r in result]}


@router.post("/action-sequencer/pipeline/{pipeline_id}/operation/{op_id}/status")
async def action_sequencer_update_status(
    pipeline_id: str, op_id: str, status: str = "succeeded",
):
    try:
        st = OpStatus(status)
    except ValueError:
        st = OpStatus.SUCCEEDED
    op = _action_sequencer.update_operation_status(pipeline_id, op_id, st)
    if op:
        return op.to_dict()
    return {"error": "Operation not found"}


@router.get("/action-sequencer/pipeline/{pipeline_id}/conflicts")
async def action_sequencer_conflicts(pipeline_id: str):
    conflicts = _action_sequencer.detect_conflicts(pipeline_id)
    return {"conflicts": [{"op_id": c[0], "dep_id": c[1], "type": c[2]} for c in conflicts]}


# === Console System ===

from sparkai.engine.console_system import ConsoleSystem, CommandDef, get_console_system

_console_system = get_console_system()


@router.get("/console-system/stats")
async def console_system_stats():
    return _console_system.get_stats()


@router.post("/console-system/execute")
async def console_system_execute(command: str):
    result = _console_system.execute(command)
    return {"result": result}


@router.get("/console-system/output")
async def console_system_output(limit: int = 50):
    lines = _console_system.get_output(limit)
    return {"lines": [{"text": l.text, "level": l.level.value} for l in lines]}


@router.get("/console-system/history")
async def console_system_history(limit: int = 20):
    history = _console_system.get_history(limit)
    return {"history": history}


@router.get("/console-system/commands")
async def console_system_commands(category: str = ""):
    cmds = _console_system.list_commands(category or None)
    return {"commands": [c.to_dict() for c in cmds]}


@router.get("/console-system/autocomplete")
async def console_system_autocomplete(prefix: str):
    suggestions = _console_system.autocomplete(prefix)
    return {"suggestions": suggestions}


@router.post("/console-system/register")
async def console_system_register(
    name: str, description: str = "", category: str = "system", syntax: str = "",
):
    cmd = _console_system.register_command(name, description, category, syntax)
    return cmd.to_dict()


# === Input Recorder ===

from sparkai.engine.input_recorder import InputRecorder, RecordingSession, get_input_recorder

_input_recorder = get_input_recorder()


@router.get("/input-recorder/stats")
async def input_recorder_stats():
    return _input_recorder.get_stats()


@router.post("/input-recorder/start-recording")
async def input_recorder_start_recording(name: str = ""):
    session = _input_recorder.start_recording(name)
    return session.to_dict()


@router.post("/input-recorder/stop-recording")
async def input_recorder_stop_recording():
    session = _input_recorder.stop_recording()
    if session:
        return session.to_dict()
    return {"error": "No active recording"}


@router.post("/input-recorder/record-event")
async def input_recorder_record_event(
    event_type: str = "key_down", code: int = 0, value: float = 0.0,
    x: float = 0.0, y: float = 0.0,
):
    from sparkai.engine.input_recorder import InputEventType
    try:
        et = InputEventType(event_type)
    except ValueError:
        et = InputEventType.KEY_DOWN
    event = _input_recorder.record_event(et, code, value, x, y)
    if event:
        return event.to_dict()
    return {"error": "Not recording"}


@router.post("/input-recorder/start-replay/{session_id}")
async def input_recorder_start_replay(session_id: str):
    success = _input_recorder.start_replay(session_id)
    return {"success": success}


@router.post("/input-recorder/stop-replay")
async def input_recorder_stop_replay():
    _input_recorder.stop_replay()
    return {"success": True}


@router.get("/input-recorder/recordings")
async def input_recorder_recordings():
    recordings = _input_recorder.list_recordings()
    return {"recordings": [r.to_dict() for r in recordings]}


@router.get("/input-recorder/recording/{session_id}")
async def input_recorder_get_recording(session_id: str):
    session = _input_recorder.get_recording(session_id)
    if session:
        return session.to_full_dict()
    return {"error": "Recording not found"}


@router.get("/input-recorder/save/{session_id}")
async def input_recorder_save(session_id: str):
    json_str = _input_recorder.save_recording(session_id)
    if json_str:
        return {"json": json_str}
    return {"error": "Recording not found"}


@router.post("/input-recorder/load")
async def input_recorder_load(json_str: str):
    session = _input_recorder.load_recording(json_str)
    if session:
        return session.to_dict()
    return {"error": "Failed to load"}


@router.delete("/input-recorder/recording/{session_id}")
async def input_recorder_delete_recording(session_id: str):
    success = _input_recorder.delete_recording(session_id)
    return {"success": success}


# === Collision Layers ===

from sparkai.engine.collision_layers import CollisionLayerManager, LayerFlag, LayerMask, get_collision_layer_manager

_collision_layer_manager = get_collision_layer_manager()


@router.get("/collision-layers/stats")
async def collision_layers_stats():
    return _collision_layer_manager.get_stats()


@router.get("/collision-layers/layers")
async def collision_layers_layers():
    return {"layers": _collision_layer_manager.list_layers()}


@router.get("/collision-layers/interactions")
async def collision_layers_interactions():
    return {"interactions": _collision_layer_manager.list_interactions()}


@router.post("/collision-layers/set-interaction")
async def collision_layers_set_interaction(
    layer_a: str = "", layer_b: str = "", should_collide: bool = True,
):
    try:
        la = LayerFlag[layer_a.upper()]
    except KeyError:
        return {"error": f"Unknown layer: {layer_a}"}
    try:
        lb = LayerFlag[layer_b.upper()]
    except KeyError:
        return {"error": f"Unknown layer: {layer_b}"}
    _collision_layer_manager.set_interaction(la, lb, should_collide)
    return {"success": True}


@router.post("/collision-layers/assign-mask")
async def collision_layers_assign_mask(
    object_id: str, layer_names: str = "DEFAULT", description: str = "",
):
    layer_bits = 0
    for name in layer_names.split(","):
        name = name.strip()
        try:
            flag = LayerFlag[name.upper()]
            layer_bits |= flag.value
        except KeyError:
            custom_flag = _collision_layer_manager.get_layer_flag(name)
            if custom_flag:
                layer_bits |= custom_flag.value
    if layer_bits == 0:
        layer_bits = LayerFlag.DEFAULT.value

    layers = LayerFlag(layer_bits)
    mask = _collision_layer_manager.assign_mask(object_id, layers, description)
    return mask.to_dict()


@router.get("/collision-layers/mask/{object_id}")
async def collision_layers_get_mask(object_id: str):
    mask = _collision_layer_manager.get_mask(object_id)
    if mask:
        return mask.to_dict()
    return {"error": "Mask not found"}


@router.post("/collision-layers/check")
async def collision_layers_check(mask_a: int = 0, mask_b: int = 0):
    should_collide = _collision_layer_manager.check_collision(mask_a, mask_b)
    return {"should_collide": should_collide}


@router.get("/collision-layers/objects-on-layer/{layer_name}")
async def collision_layers_objects_on_layer(layer_name: str):
    try:
        flag = LayerFlag[layer_name.upper()]
    except KeyError:
        flag = _collision_layer_manager.get_layer_flag(layer_name)
        if not flag:
            return {"error": f"Unknown layer: {layer_name}"}
    objects = _collision_layer_manager.find_objects_on_layer(flag)
    return {"object_ids": objects}


@router.post("/collision-layers/create-custom-layer")
async def collision_layers_create_custom_layer(name: str, description: str = ""):
    layer_def = _collision_layer_manager.create_custom_layer(name, description)
    if layer_def:
        return {"layer_name": layer_def.layer_name, "bit_position": layer_def.bit_position}
    return {"error": "No available bit positions"}


# === Agent Event Bus ===

_agent_event_bus = get_agent_event_bus()


class EventEmitRequest(BaseModel):
    domain: str = "agent"
    name: str = ""
    priority: str = "normal"
    data: Dict[str, Any] = {}
    source: str = "api"


class EventSubscribeRequest(BaseModel):
    subscriber_id: str
    domain: str = "agent"
    event_name: str = "*"


@router.get("/event-bus/stats")
async def event_bus_stats():
    return {"stats": _agent_event_bus.get_stats()}


@router.get("/event-bus/history")
async def event_bus_history(limit: int = 50, domain: Optional[str] = None):
    from sparkai.agent.agent_event_bus import EventDomain
    domain_enum = None
    if domain:
        try:
            domain_enum = EventDomain(domain)
        except ValueError:
            domain_enum = EventDomain.CUSTOM
    return {"history": [e.to_dict() for e in _agent_event_bus.get_history(limit=limit, domain=domain_enum)]}


@router.get("/event-bus/pending")
async def event_bus_pending():
    return {"pending_count": _agent_event_bus.get_pending_count()}


@router.post("/event-bus/emit")
async def event_bus_emit(request: EventEmitRequest):
    from sparkai.agent.agent_event_bus import EventDomain, EventPriority
    try:
        domain_enum = EventDomain(request.domain)
    except ValueError:
        domain_enum = EventDomain.CUSTOM
    try:
        priority_enum = EventPriority[request.priority.upper()]
    except KeyError:
        priority_enum = EventPriority.NORMAL
    event = _agent_event_bus.emit(
        domain=domain_enum,
        event_type=request.name,
        data=request.data,
        source=request.source,
        priority=priority_enum,
    )
    return {"success": True, "event_id": event.event_id, "event_name": request.name}


@router.post("/event-bus/dispatch")
async def event_bus_dispatch(max_events: int = 50):
    count = _agent_event_bus.dispatch(max_events=max_events)
    return {"success": True, "dispatched": count}


@router.get("/event-bus/subscribers")
async def event_bus_subscribers(domain: Optional[str] = None):
    from sparkai.agent.agent_event_bus import EventDomain
    domain_enum = None
    if domain:
        try:
            domain_enum = EventDomain(domain)
        except ValueError:
            domain_enum = EventDomain.CUSTOM
    subs = _agent_event_bus.get_subscribers(domain=domain_enum)
    return {"subscribers": [{"sub_id": s.sub_id, "domain": s.domain.value if s.domain else None, "event_type": s.event_type, "subscriber_name": s.subscriber_name} for s in subs], "count": len(subs)}


@router.get("/event-bus/domains")
async def event_bus_domains():
    from sparkai.agent.agent_event_bus import EventDomain
    return {"domains": [d.value for d in EventDomain]}


@router.get("/event-bus/priorities")
async def event_bus_priorities():
    from sparkai.agent.agent_event_bus import EventPriority
    return {"priorities": [p.name.lower() for p in EventPriority]}


# === Agent Task Queue ===

_agent_task_queue = get_agent_task_queue()


class TaskSubmitRequest(BaseModel):
    name: str
    priority: str = "normal"
    category: str = "general"
    dependencies: List[str] = []
    payload: Dict[str, Any] = {}


@router.get("/task-queue/stats")
async def task_queue_stats():
    return {"stats": _agent_task_queue.get_stats()}


@router.get("/task-queue/tasks")
async def task_queue_list(status: Optional[str] = None):
    tasks = _agent_task_queue.list_tasks(state=status)
    return {"tasks": tasks, "count": len(tasks)}


@router.post("/task-queue/submit")
async def task_queue_submit(request: TaskSubmitRequest):
    from sparkai.agent.agent_task_queue import TaskPriority, TaskCategory
    try:
        priority_enum = TaskPriority(request.priority)
    except ValueError:
        priority_enum = TaskPriority.NORMAL
    try:
        category_enum = TaskCategory(request.category)
    except ValueError:
        category_enum = TaskCategory.CUSTOM
    task_id = _agent_task_queue.submit(
        name=request.name,
        handler=lambda payload: {"status": "completed", "payload": payload},
        priority=priority_enum,
        category=category_enum,
        payload=request.payload,
        dependencies=request.dependencies,
    )
    return {"task_id": task_id}


@router.post("/task-queue/cancel")
async def task_queue_cancel(task_id: str):
    success = _agent_task_queue.cancel(task_id)
    return {"success": success}


@router.get("/task-queue/{task_id}")
async def task_queue_get(task_id: str):
    task = _agent_task_queue._tasks.get(task_id)
    if task:
        return {"task": {"task_id": task.task_id, "name": task.name, "state": task.state.name.lower(), "category": task.category.value}}
    return {"error": "Task not found"}


# === Agent Code Review ===

_code_review_engine = get_code_review_engine()


class CodeReviewRequest(BaseModel):
    code: str
    language: str = "python"
    categories: List[str] = ["gameplay", "performance", "architecture", "security", "style"]


class BatchReviewRequest(BaseModel):
    files: List[Dict[str, str]]
    categories: List[str] = ["gameplay", "performance", "architecture", "security", "style"]


@router.get("/code-review/stats")
async def code_review_stats():
    return {"stats": _code_review_engine.get_stats()}


@router.post("/code-review/review")
async def code_review_review(request: CodeReviewRequest):
    report = _code_review_engine.review(file_path="<api>", code=request.code)
    return report.to_dict()


@router.post("/code-review/batch")
async def code_review_batch(request: BatchReviewRequest):
    file_dict = {f.get("file_path", f"<api_{i}>"): f.get("code", "") for i, f in enumerate(request.files)}
    report = _code_review_engine.review_multiple(file_dict)
    return report.to_dict()


# === Agent Pipeline ===

_agent_pipeline = get_agent_pipeline()


class PipelineExecuteRequest(BaseModel):
    definition_name: str = ""
    inputs: Dict[str, Any] = {}
    description: str = ""


class PipelineCreateRequest(BaseModel):
    name: str
    description: str = ""
    stages: List[str] = []


@router.get("/pipeline-v2/stats")
async def pipeline_v2_stats():
    return {"stats": _agent_pipeline.get_stats()}


@router.get("/pipeline-v2/runs")
async def pipeline_v2_runs(limit: int = 20, definition_name: Optional[str] = None):
    return {"runs": _agent_pipeline.list_runs(definition_name=definition_name)[:limit]}


@router.get("/pipeline-v2/runs/{run_id}")
async def pipeline_v2_get_run(run_id: str):
    run = _agent_pipeline.get_run(run_id)
    if run:
        return run.to_dict()
    return {"error": "Run not found"}


@router.post("/pipeline-v2/execute")
async def pipeline_v2_execute(request: PipelineExecuteRequest):
    run = await _agent_pipeline.execute(
        inputs=request.inputs,
        definition_name=request.definition_name,
    )
    return run.to_dict()


@router.post("/pipeline-v2/cancel")
async def pipeline_v2_cancel(run_id: str):
    success = _agent_pipeline.cancel_run(run_id)
    return {"success": success}


@router.get("/pipeline-v2/definitions")
async def pipeline_v2_definitions():
    return {"definitions": list(_agent_pipeline._definitions.keys())}


# === Camera Shake ===

_camera_shake_system = get_camera_shake_system()


class CameraShakeRequest(BaseModel):
    preset: str = "impact"
    intensity: float = 1.0
    duration: float = 0.5


class CameraFollowRequest(BaseModel):
    target_x: float = 0.0
    target_y: float = 0.0
    follow_speed: float = 5.0


class CameraZoomRequest(BaseModel):
    target_zoom: float = 1.0
    speed: float = 3.0


@router.get("/camera-shake/stats")
async def camera_shake_stats():
    return {"stats": _camera_shake_system.get_stats()}


@router.get("/camera-shake/state")
async def camera_shake_state():
    return {"state": _camera_shake_system.get_state()}


@router.post("/camera-shake/trigger")
async def camera_shake_trigger(request: CameraShakeRequest):
    from sparkai.engine.camera_shake import ShakePreset, ShakeConfig
    try:
        preset_enum = ShakePreset[request.preset.upper()]
    except KeyError:
        preset_enum = ShakePreset.IMPACT
    config = ShakeConfig(
        amplitude_x=10.0 * request.intensity,
        amplitude_y=10.0 * request.intensity,
        frequency=30.0,
        duration=request.duration,
        decay=0.9,
    )
    _camera_shake_system.shake(preset=preset_enum, config=config)
    return {"success": True, "preset": request.preset}


@router.post("/camera-shake/follow")
async def camera_shake_follow(request: CameraFollowRequest):
    _camera_shake_system.set_target(request.target_x, request.target_y)
    _camera_shake_system.set_follow_speed(request.follow_speed)
    return {"success": True}


@router.post("/camera-shake/zoom")
async def camera_shake_zoom(request: CameraZoomRequest):
    _camera_shake_system.set_zoom(request.target_zoom, request.speed)
    return {"success": True}


@router.post("/camera-shake/dead-zone")
async def camera_shake_dead_zone(width: float = 50.0, height: float = 50.0):
    _camera_shake_system.set_dead_zone(max(width, height) / 2)
    return {"success": True}


@router.post("/camera-shake/stop")
async def camera_shake_stop():
    _camera_shake_system._active_shakes.clear()
    return {"success": True}


# === Difficulty System ===

_difficulty_system = get_difficulty_system()


class DifficultySetRequest(BaseModel):
    tier: str = "normal"
    level: int = 1


class DifficultyRecordRequest(BaseModel):
    metric_name: str
    value: float


@router.get("/difficulty/stats")
async def difficulty_stats():
    return {"stats": _difficulty_system.get_stats()}


@router.get("/difficulty/current")
async def difficulty_current():
    return {
        "tier": _difficulty_system.get_tier().value,
        "level": _difficulty_system.get_level(),
        "params": _difficulty_system.get_current_params(),
    }


@router.post("/difficulty/set")
async def difficulty_set(request: DifficultySetRequest):
    from sparkai.engine.difficulty_system import DifficultyTier
    try:
        tier_enum = DifficultyTier(request.tier.upper())
    except ValueError:
        tier_enum = DifficultyTier.NORMAL
    _difficulty_system.set_tier(tier_enum)
    _difficulty_system.set_level(request.level)
    return {"success": True, "tier": request.tier, "level": request.level}


@router.get("/difficulty/metrics")
async def difficulty_metrics():
    return {"metrics": _difficulty_system.get_metrics()}


@router.post("/difficulty/record-death")
async def difficulty_record_death():
    _difficulty_system.record_death()
    return {"success": True}


@router.post("/difficulty/record-complete")
async def difficulty_record_complete(time_taken: float = 60.0):
    _difficulty_system.record_level_complete(time_taken)
    return {"success": True}


@router.post("/difficulty/record-retry")
async def difficulty_record_retry():
    _difficulty_system.record_retry()
    return {"success": True}


@router.post("/difficulty/record-metric")
async def difficulty_record_metric(request: DifficultyRecordRequest):
    _difficulty_system.record_metric(request.metric_name, request.value)
    return {"success": True}


@router.post("/difficulty/reset-metrics")
async def difficulty_reset_metrics():
    _difficulty_system.reset_metrics()
    return {"success": True}


@router.get("/difficulty/enemy-params")
async def difficulty_enemy_params():
    return {"params": _difficulty_system.apply_to_enemy({})}


@router.get("/difficulty/player-params")
async def difficulty_player_params():
    return {"params": _difficulty_system.apply_to_player({})}


@router.get("/difficulty/score-multiplier")
async def difficulty_score_multiplier():
    return {"multiplier": _difficulty_system.get_score_multiplier()}


# === Fog of War ===

_fog_of_war = get_fog_of_war()


class VisionSourceRequest(BaseModel):
    source_id: str
    team_id: int = 0
    x: float = 0.0
    y: float = 0.0
    radius: float = 5.0
    shape: str = "circle"
    cone_angle: float = 360.0
    cone_direction: float = 0.0


class VisionSourceUpdateRequest(BaseModel):
    source_id: str
    x: Optional[float] = None
    y: Optional[float] = None
    radius: Optional[float] = None
    enabled: Optional[bool] = None


class VisibilityCheckRequest(BaseModel):
    x: float
    y: float
    team_id: int = 0


@router.get("/fog-of-war/stats")
async def fog_of_war_stats():
    return {"stats": _fog_of_war.get_stats()}


@router.get("/fog-of-war/exploration/{team_id}")
async def fog_of_war_exploration(team_id: int):
    return {"percentage": _fog_of_war.get_exploration_percentage(team_id)}


@router.get("/fog-of-war/visible-count/{team_id}")
async def fog_of_war_visible_count(team_id: int):
    return {"count": _fog_of_war.get_visible_count(team_id)}


@router.post("/fog-of-war/check-visible")
async def fog_of_war_check_visible(request: VisibilityCheckRequest):
    tile_size = _fog_of_war._tile_size
    tx = int(request.x / tile_size)
    ty = int(request.y / tile_size)
    return {"visible": _fog_of_war.is_visible(tx, ty, request.team_id)}


@router.post("/fog-of-war/check-explored")
async def fog_of_war_check_explored(request: VisibilityCheckRequest):
    tile_size = _fog_of_war._tile_size
    tx = int(request.x / tile_size)
    ty = int(request.y / tile_size)
    return {"explored": _fog_of_war.is_explored(tx, ty, request.team_id)}


@router.post("/fog-of-war/add-vision-source")
async def fog_of_war_add_vision(request: VisionSourceRequest):
    from sparkai.engine.fog_of_war import FogShape
    try:
        shape_enum = FogShape[request.shape.upper()]
    except KeyError:
        shape_enum = FogShape.CIRCLE
    source = _fog_of_war.add_vision_source(
        source_id=request.source_id,
        team=request.team_id,
        x=request.x,
        y=request.y,
        radius=request.radius,
        shape=shape_enum,
        cone_angle=request.cone_angle,
        cone_direction=request.cone_direction,
    )
    return {"source": source.to_dict() if hasattr(source, 'to_dict') else str(source)}


@router.post("/fog-of-war/update-vision-source")
async def fog_of_war_update_vision(request: VisionSourceUpdateRequest):
    _fog_of_war.update_vision_source(
        request.source_id,
        x=request.x,
        y=request.y,
        radius=request.radius,
        enabled=request.enabled,
    )
    return {"success": True}


@router.post("/fog-of-war/remove-vision-source")
async def fog_of_war_remove_vision(source_id: str):
    _fog_of_war.remove_vision_source(source_id)
    return {"success": True}


@router.get("/fog-of-war/sources")
async def fog_of_war_sources():
    return {"sources": _fog_of_war.list_vision_sources()}


@router.post("/fog-of-war/set-source-enabled")
async def fog_of_war_set_enabled(source_id: str, enabled: bool = True):
    _fog_of_war.set_source_enabled(source_id, enabled)
    return {"success": True}


@router.post("/fog-of-war/reset")
async def fog_of_war_reset(team_id: Optional[int] = None):
    _fog_of_war.reset(team_id=team_id)
    return {"success": True}


# === Game Modes ===

_game_mode_system = get_game_mode_system()


class GameModeRequest(BaseModel):
    mode_name: str
    params: Dict[str, Any] = {}


@router.get("/game-modes/stats")
async def game_modes_stats():
    return {"stats": _game_mode_system.get_stats()}


@router.get("/game-modes/current")
async def game_modes_current():
    current = _game_mode_system.get_current()
    return {"mode": current}


@router.get("/game-modes/stack")
async def game_modes_stack():
    return {
        "stack": _game_mode_system.get_stack_names(),
        "count": len(_game_mode_system.get_mode_stack()),
    }


@router.get("/game-modes/definitions")
async def game_modes_definitions():
    return {"definitions": _game_mode_system.list_mode_definitions() if hasattr(_game_mode_system, 'list_mode_definitions') else []}


@router.post("/game-modes/start")
async def game_modes_start(request: GameModeRequest):
    success = _game_mode_system.start(request.mode_name, **request.params)
    return {"success": success, "mode": request.mode_name}


@router.post("/game-modes/push")
async def game_modes_push(request: GameModeRequest):
    success = _game_mode_system.push(request.mode_name, **request.params)
    return {"success": success, "mode": request.mode_name}


@router.post("/game-modes/pop")
async def game_modes_pop():
    popped = _game_mode_system.pop()
    return {"success": popped is not None, "popped_mode": popped.mode_name if popped else None}


@router.post("/game-modes/replace")
async def game_modes_replace(request: GameModeRequest):
    success = _game_mode_system.replace(request.mode_name, **request.params)
    return {"success": success, "mode": request.mode_name}


@router.post("/game-modes/switch")
async def game_modes_switch(request: GameModeRequest):
    success = _game_mode_system.switch(request.mode_name, **request.params)
    return {"success": success, "mode": request.mode_name}


@router.get("/game-modes/has-mode")
async def game_modes_has_mode(mode_name: str):
    return {"has_mode": _game_mode_system.has_mode(mode_name)}


@router.get("/game-modes/is-transitioning")
async def game_modes_is_transitioning():
    return {"transitioning": _game_mode_system.is_transitioning()}


@router.get("/game-modes/can-transition")
async def game_modes_can_transition(to_mode: str):
    return {"can_transition": _game_mode_system.can_transition(to_mode)}


# === Agent Consensus ===

_agent_consensus = get_agent_consensus()


class ConsensusProposeRequest(BaseModel):
    topic: str
    description: str = ""
    context: Optional[Dict[str, Any]] = None
    protocol: str = "majority"
    min_participants: int = 2


class ConsensusOpinionRequest(BaseModel):
    round_id: str
    agent_name: str
    position: str
    reasoning: str = ""
    confidence: float = 0.5
    expertise_areas: Optional[List[str]] = None


class ConsensusVoteRequest(BaseModel):
    round_id: str
    agent_name: str
    position: str
    weight: float = 1.0


@router.get("/consensus/stats")
async def consensus_stats():
    return {"stats": _agent_consensus.get_stats()}


@router.post("/consensus/propose")
async def consensus_propose(request: ConsensusProposeRequest):
    try:
        protocol = ConsensusProtocol(request.protocol)
    except ValueError:
        protocol = ConsensusProtocol.MAJORITY
    round_id = _agent_consensus.propose(topic=request.topic)
    return {"round_id": round_id, "topic": request.topic}


@router.post("/consensus/submit-opinion")
async def consensus_submit_opinion(request: ConsensusOpinionRequest):
    success = _agent_consensus.submit_opinion(
        topic=request.round_id,
        agent_id=request.agent_name,
        position=request.position,
        confidence=request.confidence,
        reasoning=request.reasoning,
    )
    return {"success": success, "agent": request.agent_name}


@router.post("/consensus/vote")
async def consensus_vote(request: ConsensusVoteRequest):
    success = _agent_consensus.vote(
        topic=request.round_id,
        agent_id=request.agent_name,
        position=request.position,
    )
    return {"vote_recorded": success, "round_id": request.round_id}


@router.post("/consensus/resolve")
async def consensus_resolve(round_id: str, protocol: str = "weighted"):
    try:
        proto = ConsensusProtocol(protocol)
    except ValueError:
        proto = ConsensusProtocol.WEIGHTED
    result = _agent_consensus.resolve(topic=round_id, protocol=proto)
    if result:
        return {
            "resolved": True,
            "winning_position": result.winning_position,
            "confidence": result.confidence_score,
            "vote_distribution": result.vote_counts,
            "participant_count": result.total_voters,
        }
    return {"resolved": False, "error": "Cannot resolve"}


@router.get("/consensus/round/{round_id}")
async def consensus_round_detail(round_id: str):
    stats = _agent_consensus.get_stats()
    return {"round_id": round_id, "found": False, "stats": stats}


# === Game Analyzer ===

_game_analyzer = get_game_analyzer()


class AnalyzerRequest(BaseModel):
    game_design_doc: str = ""
    rules: Optional[Dict[str, Any]] = None
    mechanics: Optional[List[str]] = None
    target_dimensions: Optional[List[str]] = None


@router.get("/game-analyzer/stats")
async def game_analyzer_stats():
    return {"stats": _game_analyzer.get_stats()}


@router.post("/game-analyzer/analyze")
async def game_analyzer_analyze(request: AnalyzerRequest):
    dimensions = None
    if request.target_dimensions:
        try:
            dimensions = [AnalysisDimension(d) for d in request.target_dimensions]
        except ValueError:
            pass
    game_data = {
        "title": "Game Analysis",
        "design_doc": request.game_design_doc,
        "rules": request.rules,
        "mechanics": request.mechanics,
    }
    report = _game_analyzer.analyze(game_data=game_data, dimensions=dimensions)
    return report.to_dict()


@router.post("/game-analyzer/quick-scan")
async def game_analyzer_quick_scan(game_data: Dict[str, Any]):
    result = _game_analyzer.quick_scan(game_data)
    return result


@router.get("/game-analyzer/dimensions")
async def game_analyzer_dimensions():
    return {"dimensions": [d.value for d in AnalysisDimension]}


# === Adaptive Prompting ===

_adaptive_prompting = get_adaptive_prompting()


class PromptTemplateRegisterRequest(BaseModel):
    name: str
    category: str
    template_text: str
    variables: Optional[List[str]] = None
    tags: Optional[List[str]] = None


class PromptGenerateRequest(BaseModel):
    category: str
    variables: Optional[Dict[str, str]] = None
    strategy: str = "epsilon_greedy"


class PromptOutcomeRequest(BaseModel):
    template_id: str
    variant_id: str
    success: bool = True
    response_time: float = 0.0


@router.get("/adaptive-prompting/stats")
async def adaptive_prompting_stats():
    return {"stats": _adaptive_prompting.get_stats()}


@router.post("/adaptive-prompting/templates")
async def adaptive_prompting_register(request: PromptTemplateRegisterRequest):
    from sparkai.agent.agent_adaptive_prompting import TaskCategory, PromptTemplate
    try:
        category = TaskCategory(request.category)
    except ValueError:
        category = TaskCategory.GAME_DESIGN
    template = PromptTemplate(
        name=request.name,
        category=category,
        base_prompt=request.template_text,
        variables=request.variables or [],
    )
    template.template_id = f"{request.name}_{template.template_id}"
    _adaptive_prompting._templates[template.template_id] = template
    if request.tags:
        for tag in request.tags:
            _adaptive_prompting.add_variant(template.template_id, f"{request.template_text} [{tag}]")
    return {"template_id": template.template_id, "name": request.name}


@router.get("/adaptive-prompting/templates")
async def adaptive_prompting_list_templates():
    stats = _adaptive_prompting.get_stats()
    return {"templates": stats.get("templates", 0), "template_count": stats.get("templates", 0)}


@router.post("/adaptive-prompting/generate")
async def adaptive_prompting_generate(request: PromptGenerateRequest):
    try:
        strategy = OptimizationStrategy(request.strategy)
    except ValueError:
        strategy = None
    prompt_text, variant_id = _adaptive_prompting.generate_prompt(
        template_id=request.category,
        context=request.variables or {},
        strategy=strategy,
    )
    return {"prompt": prompt_text, "variant_id": variant_id, "success": bool(prompt_text)}


@router.post("/adaptive-prompting/outcome")
async def adaptive_prompting_record_outcome(request: PromptOutcomeRequest):
    success = _adaptive_prompting.record_outcome(
        template_id=request.template_id,
        variant_id=request.variant_id,
        success=request.success,
        response_time=request.response_time,
    )
    return {"success": success, "variant_id": request.variant_id}


@router.get("/adaptive-prompting/strategies")
async def adaptive_prompting_strategies():
    return {"strategies": [s.value for s in OptimizationStrategy]}


# === Entity Extractor ===

_entity_extractor = get_entity_extractor()


class EntityExtractRequest(BaseModel):
    text: str
    context: Optional[Dict[str, Any]] = None


@router.get("/entity-extractor/stats")
async def entity_extractor_stats():
    return {"stats": _entity_extractor.get_stats()}


@router.post("/entity-extractor/extract")
async def entity_extractor_extract(request: EntityExtractRequest):
    entities = _entity_extractor.extract(text=request.text, context=request.context)
    return {
        "entities": [e.to_dict() for e in entities],
        "count": len(entities),
        "entity_types": list(set(e.entity_type.value for e in entities)),
    }


@router.post("/entity-extractor/world-model")
async def entity_extractor_world_model(request: EntityExtractRequest):
    model = _entity_extractor.build_world_model(text=request.text, context=request.context)
    return model.to_dict()


@router.get("/entity-extractor/entity-types")
async def entity_extractor_types():
    return {"entity_types": [t.value for t in EntityType]}


# === Dialogue System ===

_dialogue_system = get_dialogue_system()


class DialogueRegisterRequest(BaseModel):
    tree_id: str
    tree_data: Dict[str, Any]


class DialogueStartRequest(BaseModel):
    tree_id: str
    session_id: Optional[str] = None


class DialogueSelectRequest(BaseModel):
    session_id: str
    choice_id: str
    context: Optional[Dict[str, Any]] = None


@router.get("/dialogue/stats")
async def dialogue_stats():
    return {"stats": _dialogue_system.get_stats()}


@router.get("/dialogue/trees")
async def dialogue_trees():
    return {"trees": _dialogue_system.list_trees()}


@router.get("/dialogue/trees/{tree_id}")
async def dialogue_get_tree(tree_id: str):
    tree = _dialogue_system.get_tree(tree_id)
    if tree:
        return tree.to_dict()
    return {"error": "Tree not found"}


@router.post("/dialogue/trees")
async def dialogue_register_tree(request: DialogueRegisterRequest):
    from sparkai.engine.dialogue_system import DialogueTree
    tree = DialogueTree.from_dict(request.tree_data)
    tree.tree_id = request.tree_id
    _dialogue_system.register_tree(tree)
    return {"success": True, "tree_id": request.tree_id}


@router.post("/dialogue/start")
async def dialogue_start(request: DialogueStartRequest):
    result = _dialogue_system.start_conversation(
        tree_id=request.tree_id,
        session_id=request.session_id,
    )
    return result


@router.get("/dialogue/sessions/{session_id}")
async def dialogue_get_session(session_id: str):
    session = _dialogue_system.get_session(session_id)
    if session:
        return session
    return {"error": "Session not found"}


@router.get("/dialogue/choices/{session_id}")
async def dialogue_choices(session_id: str):
    choices = _dialogue_system.get_available_choices(session_id)
    return {"session_id": session_id, "choices": [c.to_dict() for c in choices]}


@router.post("/dialogue/select")
async def dialogue_select(request: DialogueSelectRequest):
    result = _dialogue_system.select_choice(
        session_id=request.session_id,
        choice_id=request.choice_id,
        context=request.context or {},
    )
    return result


# === Quest System ===

_quest_system = get_quest_system()


class QuestDefineRequest(BaseModel):
    quest_id: str
    title: str
    description: str = ""
    objectives: List[Dict[str, Any]] = []
    rewards: Optional[List[Dict[str, Any]]] = None
    prerequisites: Optional[List[str]] = None


class QuestStartRequest(BaseModel):
    quest_id: str
    player_id: str = "default"


class QuestObjectiveUpdateRequest(BaseModel):
    quest_id: str
    player_id: str = "default"
    objective_index: int = 0
    progress: int = 1


@router.get("/quest/stats")
async def quest_stats():
    return {"stats": _quest_system.get_stats()}


@router.get("/quest/definitions")
async def quest_definitions():
    return {"quests": _quest_system.get_quest_definitions()}


@router.get("/quest/definitions/{quest_id}")
async def quest_get_definition(quest_id: str):
    quest = _quest_system.get_quest_definitions()
    for q in quest:
        if q.get("quest_id") == quest_id:
            return q
    return {"error": "Quest not found"}


@router.post("/quest/define")
async def quest_define(request: QuestDefineRequest):
    from sparkai.engine.quest_system import QuestDefinition, QuestObjective, QuestReward
    objectives = []
    for obj in request.objectives:
        objectives.append(QuestObjective(
            description=obj.get("description", ""),
            objective_type=obj.get("objective_type", "custom"),
            target_count=obj.get("target_count", 1),
            is_optional=obj.get("is_optional", False),
        ))
    rewards = None
    if request.rewards:
        rewards = []
        for r in request.rewards:
            rewards.append(QuestReward(
                reward_type=r.get("reward_type", "experience"),
                amount=r.get("amount", 0),
                item_id=r.get("item_id"),
            ))
    quest_def = QuestDefinition(
        quest_id=request.quest_id,
        title=request.title,
        description=request.description,
        objectives=objectives,
        rewards=rewards,
        prerequisites=request.prerequisites,
    )
    qid = _quest_system.define_quest(quest_def)
    return {"success": True, "quest_id": qid}


@router.post("/quest/start")
async def quest_start(request: QuestStartRequest):
    success = _quest_system.start_quest(quest_id=request.quest_id)
    return {"success": success, "quest_id": request.quest_id}


@router.post("/quest/update-objective")
async def quest_update_objective(request: QuestObjectiveUpdateRequest):
    success = _quest_system.update_objective(
        quest_id=request.quest_id,
        objective_id=str(request.objective_index),
        progress=request.progress,
    )
    return {"success": success, "quest_id": request.quest_id}


@router.post("/quest/complete")
async def quest_complete(quest_id: str):
    result = _quest_system.complete_quest(quest_id=quest_id)
    return {"success": result, "quest_id": quest_id}


@router.post("/quest/fail")
async def quest_fail(quest_id: str, reason: str = ""):
    result = _quest_system.fail_quest(quest_id=quest_id)
    return {"success": result, "quest_id": quest_id, "reason": reason}


@router.get("/quest/active")
async def quest_active():
    active = _quest_system.get_active_quests()
    return {"active_quests": [q.to_dict() if hasattr(q, 'to_dict') else str(q) for q in active], "count": len(active)}


@router.get("/quest/states")
async def quest_states():
    return {"states": [s.value for s in QuestState]}


# === Combat System ===

_combat_system = get_combat_system()


class CombatUnitCreateRequest(BaseModel):
    unit_id: str
    name: str = ""
    hp: int = 100
    max_hp: int = 100
    attack: int = 10
    defense: int = 5
    speed: int = 10
    element: Optional[str] = None
    team: str = "player"


class CombatInitiateRequest(BaseModel):
    combat_id: Optional[str] = None
    team_a: List[str] = []
    team_b: List[str] = []
    mode: str = "turn_based"


class CombatActionRequest(BaseModel):
    combat_id: str
    actor_id: str
    action_type: str = "attack"
    target_id: Optional[str] = None
    params: Optional[Dict[str, Any]] = None


@router.get("/combat/stats")
async def combat_stats():
    return {"stats": _combat_system.get_stats()}


@router.post("/combat/units")
async def combat_create_unit(request: CombatUnitCreateRequest):
    from sparkai.engine.combat_system import CombatUnit, Element
    element = request.element or "physical"
    unit = _combat_system.create_unit(
        name=request.name or request.unit_id,
        team_id=0 if request.team == "player" else 1,
        max_hp=request.max_hp,
        attack=request.attack,
        defense=request.defense,
        speed=request.speed,
        element=element,
    )
    return {"success": True, "unit_id": unit.unit_id, "name": unit.name}


@router.get("/combat/units")
async def combat_list_units():
    stats = _combat_system.get_stats()
    return {"units": [], "stats": stats}


@router.get("/combat/units/{unit_id}")
async def combat_get_unit(unit_id: str):
    stats = _combat_system.get_stats()
    return {"unit_id": unit_id, "stats": stats}


@router.post("/combat/initiate")
async def combat_initiate(request: CombatInitiateRequest):
    from sparkai.engine.combat_system import CombatMode, CombatUnit
    try:
        mode = CombatMode(request.mode)
    except ValueError:
        mode = CombatMode.TURN_BASED
    units = []
    for name in request.team_a:
        units.append(_combat_system.create_unit(name=name, team_id=0))
    for name in request.team_b:
        units.append(_combat_system.create_unit(name=name, team_id=1))
    battle_id = _combat_system.initiate_combat(units=units, mode=mode)
    return {"battle_id": battle_id, "mode": mode.value, "units": len(units)}


@router.post("/combat/execute")
async def combat_execute_action(request: CombatActionRequest):
    from sparkai.engine.combat_system import CombatActionType, CombatAction
    try:
        action_type = CombatActionType(request.action_type)
    except ValueError:
        action_type = CombatActionType.ATTACK
    action = CombatAction(
        actor=request.actor_id,
        action_type=action_type,
        target=request.target_id,
        params=request.params,
    )
    result = _combat_system.execute_action(battle_id=request.combat_id, action=action)
    return result


@router.get("/combat/state/{combat_id}")
async def combat_get_state(combat_id: str):
    state = _combat_system.get_battle_state(combat_id)
    if state:
        return state
    return {"error": "Combat not found"}


@router.get("/combat/elements")
async def combat_elements():
    from sparkai.engine.combat_system import Element
    return {"elements": [e.value for e in Element]}


@router.get("/combat/action-types")
async def combat_action_types():
    from sparkai.engine.combat_system import CombatActionType, CombatMode
    return {
        "action_types": [a.value for a in CombatActionType],
        "modes": [m.value for m in CombatMode],
    }


# === Day/Night Cycle ===

_day_night_cycle = get_day_night_cycle()


class DayNightConfigRequest(BaseModel):
    day_length_seconds: float = 300.0
    dawn_ratio: float = 0.1
    day_ratio: float = 0.45
    dusk_ratio: float = 0.1
    night_ratio: float = 0.35
    start_hour: float = 6.0


class TimeEventScheduleRequest(BaseModel):
    event_id: str
    trigger_hour: float
    callback_name: str
    data: Optional[Dict[str, Any]] = None
    repeat: bool = False


@router.get("/day-night/stats")
async def day_night_stats():
    return {"stats": _day_night_cycle.get_stats()}


@router.get("/day-night/state")
async def day_night_state():
    return {
        "time_of_day": round(_day_night_cycle.get_time_of_day(), 3),
        "current_phase": _day_night_cycle.get_phase().value,
        "day_count": _day_night_cycle.get_day_count(),
        "config": _day_night_cycle.get_stats(),
    }


@router.get("/day-night/lighting")
async def day_night_lighting():
    params = _day_night_cycle.get_lighting_params()
    return {"lighting": params}


@router.post("/day-night/config")
async def day_night_config(request: DayNightConfigRequest):
    _day_night_cycle.configure(
        day_length=request.day_length_seconds,
        dawn_ratio=request.dawn_ratio,
        day_ratio=request.day_ratio,
        dusk_ratio=request.dusk_ratio,
        night_ratio=request.night_ratio,
    )
    return {"success": True, "day_length": request.day_length_seconds}


@router.post("/day-night/update")
async def day_night_update(delta_seconds: float = 1.0):
    phase = _day_night_cycle.update(delta_seconds)
    return {
        "current_phase": phase.value,
        "time_of_day": round(_day_night_cycle.get_time_of_day(), 3),
    }


@router.get("/day-night/phases")
async def day_night_phases():
    return {"phases": [p.value for p in TimePhase]}


@router.post("/day-night/events")
async def day_night_schedule_event(request: TimeEventScheduleRequest):
    event_id = _day_night_cycle.schedule_event(
        name=request.callback_name,
        trigger_time=request.trigger_hour / 24.0,
        trigger_phase=None,
        callback_data=request.data,
        is_repeating=request.repeat,
    )
    return {"success": True, "event_id": event_id}


@router.get("/day-night/events")
async def day_night_events():
    return {"events": _day_night_cycle.get_stats()}


# === Style Transfer ===

_style_transfer = get_style_transfer()


class StyleRegisterRequest(BaseModel):
    name: str
    domain: str = "visual"
    attributes: Optional[Dict[str, Any]] = None
    color_palette: Optional[List[str]] = None
    mood_tags: Optional[List[str]] = None


class StyleTransferRequest(BaseModel):
    source_profile_id: str
    target_content: Dict[str, Any]
    target_domain: str = "narrative"
    intensity: str = "moderate"


@router.get("/style-transfer/stats")
async def style_transfer_stats():
    return {"stats": _style_transfer.get_stats()}


@router.post("/style-transfer/register")
async def style_transfer_register(request: StyleRegisterRequest):
    from sparkai.agent.agent_style_transfer import StyleDomain, StyleProfile
    try:
        domain = StyleDomain(request.domain)
    except ValueError:
        domain = StyleDomain.VISUAL
    profile = StyleProfile(
        name=request.name,
        domain=domain,
        attributes=request.attributes or {},
        color_palette=request.color_palette or [],
        mood_tags=request.mood_tags or [],
    )
    pid = _style_transfer.register_style(profile)
    return {"success": True, "profile_id": pid}


@router.get("/style-transfer/styles")
async def style_transfer_list(domain: Optional[str] = None):
    from sparkai.agent.agent_style_transfer import StyleDomain
    dom = None
    if domain:
        try:
            dom = StyleDomain(domain)
        except ValueError:
            pass
    styles = _style_transfer.list_styles(domain=dom)
    return {"styles": [s.to_dict() for s in styles]}


@router.post("/style-transfer/transfer")
async def style_transfer_transfer(request: StyleTransferRequest):
    from sparkai.agent.agent_style_transfer import StyleDomain, TransferIntensity
    try:
        target = StyleDomain(request.target_domain)
    except ValueError:
        target = StyleDomain.NARRATIVE
    try:
        intensity = TransferIntensity(request.intensity)
    except ValueError:
        intensity = TransferIntensity.MODERATE
    result = _style_transfer.transfer_style(
        source_profile_id=request.source_profile_id,
        target_content=request.target_content,
        target_domain=target,
        intensity=intensity,
    )
    if result:
        return {"success": True, "result": result.__dict__}
    return {"success": False, "error": "Transfer failed"}


# === Curriculum Learning ===

_curriculum_learning = get_curriculum_learning()


class CurriculumSkillRequest(BaseModel):
    name: str
    description: str = ""
    level: str = "novice"
    difficulty_baseline: float = 1.0


class CurriculumSessionRequest(BaseModel):
    target_skills: List[str]
    strategy: str = "scaffolded"


@router.get("/curriculum/stats")
async def curriculum_stats():
    return {"stats": _curriculum_learning.get_stats()}


@router.post("/curriculum/register-skill")
async def curriculum_register_skill(request: CurriculumSkillRequest):
    from sparkai.agent.agent_curriculum_learning import SkillNode, SkillLevel
    try:
        level = SkillLevel(request.level)
    except ValueError:
        level = SkillLevel.NOVICE
    skill = SkillNode(
        name=request.name,
        description=request.description,
        level=level,
        difficulty_baseline=request.difficulty_baseline,
    )
    sid = _curriculum_learning.register_skill(skill)
    return {"success": True, "skill_id": sid}


@router.post("/curriculum/start-session")
async def curriculum_start_session(request: CurriculumSessionRequest):
    from sparkai.agent.agent_curriculum_learning import LearningStrategy
    try:
        strategy = LearningStrategy(request.strategy)
    except ValueError:
        strategy = None
    session = _curriculum_learning.start_session(request.target_skills, strategy)
    return {"session_id": session.session_id, "difficulty": session.difficulty_modifier}


@router.post("/curriculum/record-performance")
async def curriculum_record(skill_id: str, score: float):
    proficiency = _curriculum_learning.record_performance(skill_id, score)
    return {"skill_id": skill_id, "proficiency": proficiency}


@router.get("/curriculum/skill-graph")
async def curriculum_skill_graph():
    return _curriculum_learning.get_skill_graph()


@router.post("/curriculum/end-session")
async def curriculum_end_session():
    result = _curriculum_learning.end_session()
    return {"result": result}


# === Game Balancer ===

_game_balancer = get_game_balancer()


class BalancerParamRequest(BaseModel):
    param_id: str
    name: str = ""
    domain: str = "combat"
    current_value: float = 1.0
    min_value: float = 0.1
    max_value: float = 10.0
    ideal_min: float = 0.8
    ideal_max: float = 1.2


class BalancerMetricRequest(BaseModel):
    name: str
    domain: str = "combat"
    current_value: float
    target_value: float


@router.get("/balancer/stats")
async def balancer_stats():
    return {"stats": _game_balancer.get_stats()}


@router.post("/balancer/register-param")
async def balancer_register_param(request: BalancerParamRequest):
    from sparkai.agent.agent_balancing import GameParameter, TuningDomain
    try:
        domain = TuningDomain(request.domain)
    except ValueError:
        domain = TuningDomain.COMBAT
    param = GameParameter(
        param_id=request.param_id,
        name=request.name,
        domain=domain,
        current_value=request.current_value,
        min_value=request.min_value,
        max_value=request.max_value,
        ideal_range=(request.ideal_min, request.ideal_max),
    )
    _game_balancer.register_parameter(param)
    return {"success": True, "param_id": request.param_id}


@router.post("/balancer/report-metric")
async def balancer_report_metric(request: BalancerMetricRequest):
    from sparkai.agent.agent_balancing import BalanceMetric, TuningDomain
    try:
        domain = TuningDomain(request.domain)
    except ValueError:
        domain = TuningDomain.COMBAT
    metric = BalanceMetric(
        name=request.name,
        domain=domain,
        current_value=request.current_value,
        target_value=request.target_value,
    )
    _game_balancer.report_metric(metric)
    return {"success": True, "metric_id": metric.metric_id}


@router.post("/balancer/analyze")
async def balancer_analyze(domain: str = "combat"):
    from sparkai.agent.agent_balancing import TuningDomain
    try:
        dom = TuningDomain(domain)
    except ValueError:
        dom = TuningDomain.COMBAT
    report = _game_balancer.analyze_domain(dom)
    return {"status": report.status.value, "recommended": report.recommended_changes}


@router.post("/balancer/apply")
async def balancer_apply(domain: str = "combat"):
    from sparkai.agent.agent_balancing import TuningDomain
    try:
        dom = TuningDomain(domain)
    except ValueError:
        dom = TuningDomain.COMBAT
    report = _game_balancer.analyze_domain(dom)
    count = _game_balancer.apply_tuning(report)
    return {"applied": count, "params": _game_balancer.get_parameter_snapshot(dom)}


# === Localization ===

_localization_engine = get_localization_engine()


class LocaleStringRequest(BaseModel):
    key: str
    source_text: str
    category: str = "ui"
    context_tags: Optional[List[str]] = None


class TranslationRequest(BaseModel):
    string_id: str
    locale: str
    text: str
    quality_score: float = 1.0


@router.get("/localization/stats")
async def localization_stats():
    return {"stats": _localization_engine.get_stats()}


@router.post("/localization/register-string")
async def localization_register_string(request: LocaleStringRequest):
    from sparkai.agent.agent_localization import StringCategory
    try:
        category = StringCategory(request.category)
    except ValueError:
        category = StringCategory.UI
    sid = _localization_engine.register_string_by_key(
        key=request.key,
        source_text=request.source_text,
        category=category,
        context_tags=request.context_tags,
    )
    return {"success": True, "string_id": sid}


@router.post("/localization/translate")
async def localization_translate(request: TranslationRequest):
    from sparkai.agent.agent_localization import Locale
    try:
        locale = Locale(request.locale)
    except ValueError:
        locale = Locale.EN
    success = _localization_engine.add_translation(
        string_id=request.string_id,
        locale=locale,
        text=request.text,
        quality_score=request.quality_score,
    )
    return {"success": success}


@router.get("/localization/text/{string_id}")
async def localization_get_text(string_id: str, locale: str = "en"):
    from sparkai.agent.agent_localization import Locale
    try:
        loc = Locale(locale)
    except ValueError:
        loc = Locale.EN
    return {"text": _localization_engine.get_text(string_id, loc)}


@router.get("/localization/missing/{locale}")
async def localization_missing(locale: str):
    from sparkai.agent.agent_localization import Locale
    try:
        loc = Locale(locale)
    except ValueError:
        loc = Locale.EN
    missing = _localization_engine.get_missing_translations(loc)
    return {"missing": [m.key for m in missing], "count": len(missing)}


@router.get("/localization/locales")
async def localization_locales():
    return {"locales": [l.value for l in _localization_engine.get_supported_locales()]}


# === Tutorial Design ===

_tutorial_designer = get_tutorial_designer()


class MechanicDefineRequest(BaseModel):
    name: str
    description: str = ""
    complexity: int = 1
    prerequisites: Optional[List[str]] = None
    input_actions: Optional[List[str]] = None
    objective_description: str = ""
    tips: Optional[List[str]] = None


class TutorialDesignRequest(BaseModel):
    mechanic_id: str
    tier: str = "guided"
    moment: str = "on_unlock"


@router.get("/tutorial/stats")
async def tutorial_stats():
    return {"stats": _tutorial_designer.get_stats()}


@router.post("/tutorial/define-mechanic")
async def tutorial_define_mechanic(request: MechanicDefineRequest):
    from sparkai.agent.agent_tutorial_design import MechanicDefinition
    mechanic = MechanicDefinition(
        name=request.name,
        description=request.description,
        complexity=request.complexity,
        prerequisites=request.prerequisites or [],
        input_actions=request.input_actions or [],
        objective_description=request.objective_description,
        tips=request.tips or [],
    )
    mid = _tutorial_designer.define_mechanic(mechanic)
    return {"success": True, "mechanic_id": mid}


@router.post("/tutorial/design")
async def tutorial_design(request: TutorialDesignRequest):
    from sparkai.agent.agent_tutorial_design import ScaffoldingTier, TutorialMoment
    try:
        tier = ScaffoldingTier(request.tier)
    except ValueError:
        tier = ScaffoldingTier.GUIDED
    try:
        moment = TutorialMoment(request.moment)
    except ValueError:
        moment = TutorialMoment.ON_UNLOCK
    seq = _tutorial_designer.design_tutorial(request.mechanic_id, tier, moment)
    if seq:
        return {"success": True, "sequence_id": seq.sequence_id, "steps": len(seq.steps)}
    return {"success": False, "error": "Mechanic not found"}


@router.get("/tutorial/mechanics")
async def tutorial_mechanics():
    return {"mechanics": [{"id": m.mechanic_id, "name": m.name} for m in _tutorial_designer.get_all_mechanics_ordered()]}


@router.post("/tutorial/complete")
async def tutorial_complete(sequence_id: str, completion_time: float = 0.0):
    _tutorial_designer.record_completion(sequence_id, completion_time)
    return {"success": True}


# === Game Testing ===

_game_tester = get_game_tester()
_memory_consolidation = get_memory_consolidation()
_conflict_resolver = get_conflict_resolver()
_risk_assessor = get_risk_assessor()
_documentation_generator = get_documentation_generator()
_asset_optimizer = get_asset_optimizer()
_cross_platform_engine = get_cross_platform_engine()

from sparkai.agent.agent_player_analytics import get_player_analytics
from sparkai.agent.agent_adaptive_difficulty import get_adaptive_difficulty
from sparkai.agent.agent_content_moderation import get_content_moderation
from sparkai.agent.agent_game_settings import get_game_settings, SettingsDomain
from sparkai.engine.water_system import get_water_system
from sparkai.engine.spline_system import get_spline_system
from sparkai.engine.post_processing import get_post_processing
from sparkai.engine.trigger_system import get_trigger_system

_player_analytics = get_player_analytics()
_adaptive_difficulty = get_adaptive_difficulty()
_content_moderation = get_content_moderation()
_game_settings = get_game_settings()
_water_system = get_water_system()
_spline_system = get_spline_system()
_post_processing = get_post_processing()
_trigger_system = get_trigger_system()

from sparkai.agent.agent_game_progression import get_game_progression
from sparkai.agent.agent_narrative_graph import get_narrative_graph
from sparkai.agent.agent_asset_harmonizer import get_asset_harmonizer
from sparkai.agent.agent_agentic_memory import get_agentic_memory
from sparkai.agent.agent_multi_agent_orchestration import get_multi_agent_orchestrator
from sparkai.agent.agent_realtime_collaboration import get_realtime_collaboration
from sparkai.engine.material_system import get_material_system
from sparkai.engine.navmesh_system import get_navmesh_system
from sparkai.engine.occlusion_system import get_occlusion_system
from sparkai.engine.timeline_system import get_timeline_system
from sparkai.engine.vfx_system import get_vfx_system

_game_progression = get_game_progression()
_narrative_graph = get_narrative_graph()
_asset_harmonizer = get_asset_harmonizer()
_agentic_memory = get_agentic_memory()
_multi_agent_orchestrator = get_multi_agent_orchestrator()
_realtime_collaboration = get_realtime_collaboration()
_material_system = get_material_system()
_navmesh_system = get_navmesh_system()
_occlusion_system = get_occlusion_system()
_timeline_system = get_timeline_system()
_vfx_system = get_vfx_system()

from sparkai.agent.agent_goal_decomposer import get_goal_decomposer
from sparkai.agent.agent_skill_autonomy import get_skill_autonomy
from sparkai.agent.agent_expression_validator import get_expression_validator
from sparkai.agent.agent_variable_introspection import get_variable_introspection
from sparkai.agent.agent_theme_designer import get_theme_designer
from sparkai.agent.agent_import_pipeline import get_import_pipeline
from sparkai.agent.agent_performance_advisor import get_performance_advisor
from sparkai.engine.profiler_system import get_profiler_system as get_profiler_sys
from sparkai.engine.expression_engine import get_expression_engine
from sparkai.engine.extension_runtime import get_extension_runtime
from sparkai.engine.terrain_system import get_terrain_system
from sparkai.engine.fog_of_war import get_fog_of_war

_goal_decomposer = get_goal_decomposer()
_skill_autonomy = get_skill_autonomy()
_expression_validator = get_expression_validator()
_variable_introspection = get_variable_introspection()
_theme_designer = get_theme_designer()
_import_pipeline = get_import_pipeline()
_performance_advisor = get_performance_advisor()
_profiler_sys = get_profiler_sys()
_expression_engine = get_expression_engine()
_extension_runtime = get_extension_runtime()
_terrain_system = get_terrain_system()
_fog_of_war = get_fog_of_war()


class TestCaseDefineRequest(BaseModel):
    name: str
    test_type: str = "smoke"
    description: str = ""
    target_feature: str = ""
    steps: Optional[List[str]] = None
    expected_outcome: str = ""


class TestRunRequest(BaseModel):
    name: str
    test_types: Optional[List[str]] = None
    simulator_player_type: str = "average"


@router.get("/game-testing/stats")
async def game_testing_stats():
    return {"stats": _game_tester.get_stats()}


@router.post("/game-testing/define-case")
async def game_testing_define_case(request: TestCaseDefineRequest):
    from sparkai.agent.agent_game_testing import TestCase, TestType
    try:
        test_type = TestType(request.test_type)
    except ValueError:
        test_type = TestType.SMOKE
    case = TestCase(
        name=request.name,
        test_type=test_type,
        description=request.description,
        target_feature=request.target_feature,
        steps=request.steps or [],
        expected_outcome=request.expected_outcome,
    )
    cid = _game_tester.define_test_case(case)
    return {"success": True, "case_id": cid}


@router.post("/game-testing/run")
async def game_testing_run(request: TestRunRequest):
    from sparkai.agent.agent_game_testing import TestType, PlayerSimulator
    test_types = None
    if request.test_types:
        try:
            test_types = [TestType(t) for t in request.test_types]
        except ValueError:
            pass
    simulators = _game_tester._simulators
    sim = next((s for s in simulators if s.player_type == request.simulator_player_type), simulators[0])
    run = _game_tester.create_test_run(request.name, test_types)
    result = _game_tester.run_tests(sim)
    return _game_tester.get_latest_results() or {"pass_rate": result.pass_rate()}


@router.get("/game-testing/coverage")
async def game_testing_coverage():
    return _game_tester.get_coverage_report()


# === Weather System ===

_weather_system = get_weather_system()


class WeatherZoneRequest(BaseModel):
    zone_id: Optional[str] = None
    name: str
    allowed_states: List[str]
    default_state: str = "clear"


class WeatherSetRequest(BaseModel):
    zone_id: str
    state: str


@router.get("/weather/stats")
async def weather_stats():
    return {"stats": _weather_system.get_stats()}


@router.post("/weather/register-zone")
async def weather_register_zone(request: WeatherZoneRequest):
    from sparkai.engine.weather_system import ClimateZone, WeatherState
    try:
        default = WeatherState(request.default_state)
    except ValueError:
        default = WeatherState.CLEAR
    states = []
    for s in request.allowed_states:
        try:
            states.append(WeatherState(s))
        except ValueError:
            pass
    zone = ClimateZone(
        zone_id=request.zone_id or "",
        name=request.name,
        allowed_states=states or [WeatherState.CLEAR],
        default_state=default,
    )
    zid = _weather_system.register_zone(zone)
    return {"success": True, "zone_id": zid}


@router.post("/weather/set")
async def weather_set(request: WeatherSetRequest):
    from sparkai.engine.weather_system import WeatherState
    try:
        state = WeatherState(request.state)
    except ValueError:
        state = WeatherState.CLEAR
    success = _weather_system.set_weather(request.zone_id, state)
    return {"success": success}


@router.get("/weather/zones")
async def weather_zones():
    return {"zones": _weather_system.get_all_zones()}


@router.get("/weather/modifiers/{zone_id}")
async def weather_modifiers(zone_id: str):
    return {"modifiers": _weather_system.get_gameplay_modifiers(zone_id)}


@router.post("/weather/update")
async def weather_update(delta_seconds: float = 1.0):
    _weather_system.update(delta_seconds)
    return {"zones": _weather_system.get_all_zones()}


# === Skill Tree System ===

_skill_tree_system = get_skill_tree_system()


class SkillTreeRegisterRequest(BaseModel):
    name: str
    class_name: str
    description: str = ""


class SkillNodeAddRequest(BaseModel):
    tree_id: str
    name: str
    description: str = ""
    node_type: str = "passive"
    tier: int = 0
    cost: int = 1
    max_rank: int = 1
    prerequisites: Optional[List[str]] = None
    is_root: bool = False


class UnlockNodeRequest(BaseModel):
    character_id: str
    tree_id: str
    node_id: str


@router.get("/skill-tree/stats")
async def skill_tree_stats():
    return {"stats": _skill_tree_system.get_stats()}


@router.post("/skill-tree/register")
async def skill_tree_register(request: SkillTreeRegisterRequest):
    from sparkai.engine.skill_tree_system import SkillTree
    tree = SkillTree(
        name=request.name,
        class_name=request.class_name,
        description=request.description,
    )
    tid = _skill_tree_system.register_tree(tree)
    return {"success": True, "tree_id": tid}


@router.post("/skill-tree/add-node")
async def skill_tree_add_node(request: SkillNodeAddRequest):
    from sparkai.engine.skill_tree_system import SkillNode, NodeType
    tree = _skill_tree_system._trees.get(request.tree_id)
    if tree is None:
        return {"success": False, "error": "Tree not found"}
    try:
        node_type = NodeType(request.node_type)
    except ValueError:
        node_type = NodeType.PASSIVE
    node = SkillNode(
        name=request.name,
        description=request.description,
        node_type=node_type,
        tier=request.tier,
        cost=request.cost,
        max_rank=request.max_rank,
        prerequisites=request.prerequisites or [],
    )
    tree.nodes[node.node_id] = node
    if request.is_root:
        tree.root_node_ids.append(node.node_id)
    _skill_tree_system._evaluate_availability(request.tree_id)
    return {"success": True, "node_id": node.node_id}


@router.post("/skill-tree/unlock")
async def skill_tree_unlock(request: UnlockNodeRequest):
    success = _skill_tree_system.unlock_node(
        character_id=request.character_id,
        tree_id=request.tree_id,
        node_id=request.node_id,
    )
    return {"success": success}


@router.get("/skill-tree/trees")
async def skill_tree_trees():
    return {"trees": {tid: t.to_dict() for tid, t in _skill_tree_system._trees.items()}}


@router.get("/skill-tree/modifiers/{character_id}")
async def skill_tree_modifiers(character_id: str):
    return {"modifiers": _skill_tree_system.get_unlocked_modifiers(character_id)}


# === Crafting System ===

_crafting_system = get_crafting_system()


class RecipeRegisterRequest(BaseModel):
    name: str
    description: str = ""
    category: str = "consumable"
    ingredients: List[Dict[str, Any]] = []
    result_item_id: str = ""
    result_name: str = ""
    result_quantity: int = 1
    min_skill_level: int = 1
    crafting_time: float = 2.0
    required_station: str = ""


class CraftRequest(BaseModel):
    character_id: str
    recipe_id: str
    inventory: Dict[str, int]
    station: str = ""


@router.get("/crafting/stats")
async def crafting_stats():
    return {"stats": _crafting_system.get_stats()}


@router.post("/crafting/register-recipe")
async def crafting_register_recipe(request: RecipeRegisterRequest):
    from sparkai.engine.crafting_system import CraftingRecipe, CraftingCategory, Ingredient
    try:
        category = CraftingCategory(request.category)
    except ValueError:
        category = CraftingCategory.CONSUMABLE
    ingredients = []
    for ing in request.ingredients:
        ingredients.append(Ingredient(
            item_id=ing.get("item_id", ""),
            name=ing.get("name", ""),
            quantity=ing.get("quantity", 1),
        ))
    recipe = CraftingRecipe(
        name=request.name,
        description=request.description,
        category=category,
        ingredients=ingredients,
        result_item_id=request.result_item_id,
        result_name=request.result_name,
        result_quantity=request.result_quantity,
        min_skill_level=request.min_skill_level,
        crafting_time=request.crafting_time,
        required_station=request.required_station,
    )
    rid = _crafting_system.register_recipe(recipe)
    return {"success": True, "recipe_id": rid}


@router.post("/crafting/craft")
async def crafting_craft(request: CraftRequest):
    result = _crafting_system.craft(
        character_id=request.character_id,
        recipe_id=request.recipe_id,
        inventory=request.inventory,
        station=request.station,
    )
    return {"success": result.success, "result": result.__dict__}


@router.get("/crafting/recipes")
async def crafting_recipes():
    return {"recipes": [r.to_dict() for r in _crafting_system._recipes.values()]}


# === Loot System ===

_loot_system = get_loot_system()


class DropTableRegisterRequest(BaseModel):
    name: str
    entries: List[Dict[str, Any]] = []
    min_drops: int = 1
    max_drops: int = 5


class LootGenerateRequest(BaseModel):
    table_id: str
    player_level: int = 1
    luck_modifier: float = 0.0
    count: Optional[int] = None


@router.get("/loot/stats")
async def loot_stats():
    return {"stats": _loot_system.get_stats()}


@router.post("/loot/register-table")
async def loot_register_table(request: DropTableRegisterRequest):
    from sparkai.engine.loot_system import DropTable, DropEntry, LootCategory, Rarity
    entries = []
    for entry in request.entries:
        try:
            category = LootCategory(entry.get("category", "material"))
        except ValueError:
            category = LootCategory.MATERIAL
        try:
            min_r = Rarity(entry.get("min_rarity", "common"))
            max_r = Rarity(entry.get("max_rarity", "epic"))
        except ValueError:
            min_r, max_r = Rarity.COMMON, Rarity.EPIC
        entries.append(DropEntry(
            base_item_name=entry.get("base_item_name", ""),
            category=category,
            min_rarity=min_r,
            max_rarity=max_r,
            weight=entry.get("weight", 1.0),
            min_quantity=entry.get("min_quantity", 1),
            max_quantity=entry.get("max_quantity", 1),
        ))
    table = DropTable(
        name=request.name,
        entries=entries,
        min_drops=request.min_drops,
        max_drops=request.max_drops,
    )
    tid = _loot_system.register_table(table)
    return {"success": True, "table_id": tid}


@router.post("/loot/generate")
async def loot_generate(request: LootGenerateRequest):
    items = _loot_system.generate_loot(
        table_id=request.table_id,
        player_level=request.player_level,
        luck_modifier=request.luck_modifier,
        count=request.count,
    )
    return {"items": [i.to_dict() for i in items], "count": len(items)}


@router.get("/loot/rarity-weights")
async def loot_rarity_weights():
    return {"weights": _loot_system.get_rarity_weights()}


# === Economy System ===

_economy_system = get_economy_system()


class WalletCreateRequest(BaseModel):
    owner_id: str
    initial_balance: float = 0.0


class TradeExecuteRequest(BaseModel):
    buyer_id: str
    seller_id: str = "market"
    item_id: str
    quantity: int = 1
    currency: str = "gold"


@router.get("/economy/stats")
async def economy_stats():
    return {"stats": _economy_system.get_stats()}


@router.post("/economy/create-wallet")
async def economy_create_wallet(request: WalletCreateRequest):
    wallet = _economy_system.create_wallet(request.owner_id, request.initial_balance)
    return {"success": True, "balances": {k.value: v for k, v in wallet.balances.items()}}


@router.get("/economy/wallet/{owner_id}")
async def economy_get_wallet(owner_id: str):
    summary = _economy_system.get_wallet_summary(owner_id)
    if summary:
        return summary
    return {"error": "Wallet not found"}


@router.post("/economy/register-item")
async def economy_register_item(item_id: str, name: str, base_price: float, category: str = ""):
    from sparkai.engine.economy_system import MarketItem
    item = MarketItem(item_id=item_id, name=name, base_price=base_price, category=category)
    _economy_system.register_market_item(item)
    return {"success": True, "item_id": item_id}


@router.post("/economy/trade")
async def economy_trade(request: TradeExecuteRequest):
    from sparkai.engine.economy_system import CurrencyType
    try:
        currency = CurrencyType(request.currency)
    except ValueError:
        currency = CurrencyType.GOLD
    transaction = _economy_system.execute_trade(
        buyer_id=request.buyer_id,
        seller_id=request.seller_id,
        item_id=request.item_id,
        quantity=request.quantity,
        currency=currency,
    )
    if transaction:
        return {"success": True, "total_price": transaction.total_price}
    return {"success": False, "error": "Trade failed"}


@router.get("/economy/market")
async def economy_market():
    return _economy_system.get_market_summary()


@router.post("/economy/update-market")
async def economy_update_market(delta_time: float = 1.0):
    _economy_system.update_market(delta_time)
    return {"success": True}


# === Cutscene System ===

_cutscene_system = get_cutscene_system()
_character_controller = get_character_controller()
_vehicle_system = get_vehicle_system()
_dynamic_music = get_dynamic_music()
_destruction_system = get_destruction_system()
_reputation_system = get_reputation_system()
_level_streaming = get_level_streaming()


class CutsceneActionRequest(BaseModel):
    action_type: str
    trigger_time: float = 0.0
    duration: float = 0.0
    target_id: str = ""
    params: Optional[Dict[str, Any]] = None


class CutsceneRegisterRequest(BaseModel):
    name: str
    description: str = ""
    is_skippable: bool = True
    actions: List[Dict[str, Any]] = []
    initial_transition: Optional[str] = None
    final_transition: Optional[str] = None


@router.get("/cutscene/stats")
async def cutscene_stats():
    return {"stats": _cutscene_system.get_stats()}


@router.post("/cutscene/register")
async def cutscene_register(request: CutsceneRegisterRequest):
    from sparkai.engine.cutscene_system import CutsceneDefinition, CutsceneAction, ActionType, TransitionType
    actions = []
    for a in request.actions:
        try:
            action_type = ActionType(a["action_type"])
        except (ValueError, KeyError):
            continue
        actions.append(CutsceneAction(
            action_type=action_type,
            trigger_time=a.get("trigger_time", 0.0),
            duration=a.get("duration", 0.0),
            target_id=a.get("target_id", ""),
            params=a.get("params", {}),
        ))
    init_trans = None
    final_trans = None
    if request.initial_transition:
        try:
            init_trans = TransitionType(request.initial_transition)
        except ValueError:
            pass
    if request.final_transition:
        try:
            final_trans = TransitionType(request.final_transition)
        except ValueError:
            pass
    scene = CutsceneDefinition(
        name=request.name,
        description=request.description,
        is_skippable=request.is_skippable,
        actions=actions,
        initial_transition=init_trans,
        final_transition=final_trans,
    )
    sid = _cutscene_system.register_scene(scene)
    return {"success": True, "scene_id": sid}


@router.post("/cutscene/play/{scene_id}")
async def cutscene_play(scene_id: str):
    success = _cutscene_system.play(scene_id)
    return {"success": success}


@router.post("/cutscene/skip")
async def cutscene_skip():
    return {"skipped": _cutscene_system.skip()}


@router.post("/cutscene/pause")
async def cutscene_pause():
    _cutscene_system.pause()
    return {"success": True}


@router.post("/cutscene/resume")
async def cutscene_resume():
    _cutscene_system.resume()
    return {"success": True}


@router.post("/cutscene/stop")
async def cutscene_stop():
    _cutscene_system.stop()
    return {"success": True}


@router.get("/cutscene/state")
async def cutscene_state():
    return _cutscene_system.get_current_state()


@router.post("/cutscene/update")
async def cutscene_update(delta_seconds: float = 0.016):
    return _cutscene_system.update(delta_seconds)


# === Memory Consolidation Endpoints ===

@router.get("/memory/stats")
async def memory_consolidation_stats():
    return _memory_consolidation.get_stats()

@router.get("/memory/domain-summary")
async def memory_domain_summary():
    return _memory_consolidation.get_domain_summary()

@router.post("/memory/store")
async def memory_store(content: Dict[str, Any] = None, domain: str = "working",
                       priority: str = "medium", importance: float = 0.5,
                       tags: List[str] = None, source: str = "system"):
    dom = MemoryDomain(domain) if domain in [d.value for d in MemoryDomain] else MemoryDomain.WORKING
    pri = {"critical": 5, "high": 4, "medium": 3, "low": 2, "transient": 1}.get(priority, 3)
    entry_id = _memory_consolidation.store(
        content or {}, dom, _memory_consolidation.__class__._get_priority_enum(pri),
        importance, tags or [], source)
    return {"entry_id": entry_id}

@router.post("/memory/consolidate")
async def memory_consolidate(source: str = "working", target: str = "episodic"):
    return _memory_consolidation.consolidate(
        MemoryDomain(source) if source in [d.value for d in MemoryDomain] else MemoryDomain.WORKING,
        MemoryDomain(target) if target in [d.value for d in MemoryDomain] else MemoryDomain.EPISODIC
    ).to_dict()


# === Conflict Resolution Endpoints ===

@router.get("/conflict/stats")
async def conflict_stats():
    return _conflict_resolver.get_stats()

@router.get("/conflict/active")
async def conflict_active():
    return [c.to_dict() for c in _conflict_resolver.get_active_conflicts()]

@router.get("/conflict/history")
async def conflict_history(limit: int = 20):
    return _conflict_resolver.get_resolution_history(limit)

@router.post("/conflict/set-priority")
async def conflict_set_priority(agent_id: str, priority: int):
    _conflict_resolver.set_agent_priority(agent_id, priority)
    return {"agent_id": agent_id, "priority": priority}


# === Risk Assessment Endpoints ===

@router.get("/risk/stats")
async def risk_stats():
    return _risk_assessor.get_stats()

@router.post("/risk/assess")
async def risk_assess(target: str = "", code: str = "",
                      text: str = ""):
    report = _risk_assessor.run_assessment(target, code=code, text=text)
    return report.to_dict()

@router.get("/risk/reports")
async def risk_reports(limit: int = 10):
    return _risk_assessor.get_recent_reports(limit)


# === Documentation Endpoints ===

@router.get("/docs-agent/stats")
async def docs_agent_stats():
    return _documentation_generator.get_stats()

@router.post("/docs-agent/create")
async def docs_create(doc_type: str = "game_design", title: str = "",
                      project_name: str = ""):
    dt = DocumentType(doc_type) if doc_type in [d.value for d in DocumentType] else DocumentType.GAME_DESIGN
    doc = _documentation_generator.create_document(dt, title, project_name)
    return doc.to_dict()

@router.get("/docs-agent/list")
async def docs_list(doc_type: str = None):
    dt = DocumentType(doc_type) if doc_type in [d.value for d in DocumentType] else None
    return _documentation_generator.list_documents(dt)

@router.get("/docs-agent/export/{doc_id}")
async def docs_export(doc_id: str, fmt: str = "markdown"):
    fe = ExportFormat(fmt) if fmt in [f.value for f in ExportFormat] else ExportFormat.MARKDOWN
    content = _documentation_generator.export_document(doc_id, fe)
    return {"doc_id": doc_id, "format": fmt, "content": content}

@router.post("/docs-agent/log-change")
async def docs_log_change(description: str, category: str = "general",
                          author: str = "system"):
    _documentation_generator.log_change(description, category, author)
    return {"success": True}

@router.post("/docs-agent/build-catalog")
async def docs_build_catalog(project_name: str = ""):
    doc = _documentation_generator.build_catalog(project_name)
    return doc.to_dict()

@router.post("/docs-agent/build-changelog")
async def docs_build_changelog(project_name: str = "", limit: int = 50):
    doc = _documentation_generator.build_change_log(project_name, limit)
    return doc.to_dict()


# === Asset Optimizer Endpoints ===

@router.get("/asset-optimize/stats")
async def asset_optimize_stats():
    return _asset_optimizer.get_stats()

@router.post("/asset-optimize/set-preset")
async def asset_optimize_set_preset(preset: str = "balanced"):
    _asset_optimizer.set_quality_preset(QualityPreset(preset))
    return {"preset": preset}

@router.post("/asset-optimize/analyze-all")
async def asset_optimize_analyze_all():
    return {k: [r.to_dict() for r in v] for k, v in _asset_optimizer.analyze_all().items()}

@router.get("/asset-optimize/summary")
async def asset_optimize_summary():
    return _asset_optimizer.get_savings_summary()

@router.get("/asset-optimize/duplicates")
async def asset_optimize_duplicates():
    return [{"original": a, "duplicate": b, "size": s} for a, b, s in _asset_optimizer.find_duplicates()]


# === Cross-Platform Endpoints ===

@router.get("/platform/stats")
async def platform_stats():
    return _cross_platform_engine.get_stats()

@router.get("/platform/list")
async def platform_list():
    return _cross_platform_engine.list_platforms()

@router.post("/platform/generate-config")
async def platform_generate_config(platform: str = "desktop_windows",
                                    app_name: str = "", bundle_id: str = "",
                                    version: str = "1.0.0"):
    tp = TargetPlatform(platform) if platform in [p.value for p in TargetPlatform] else TargetPlatform.DESKTOP_WINDOWS
    config = _cross_platform_engine.generate_build_config(tp, app_name, bundle_id, version)
    return config.to_dict()

@router.post("/platform/create-input-mapping")
async def platform_create_input_mapping(platform: str, actions: List[str] = None):
    tp = TargetPlatform(platform) if platform in [p.value for p in TargetPlatform] else TargetPlatform.DESKTOP_WINDOWS
    mapping = _cross_platform_engine.create_input_mapping(tp, actions or [])
    return mapping.to_dict()

@router.post("/platform/check-compatibility")
async def platform_check_compatibility(platform: str, requirements: Dict[str, Any] = None):
    tp = TargetPlatform(platform) if platform in [p.value for p in TargetPlatform] else TargetPlatform.DESKTOP_WINDOWS
    compatible, issues = _cross_platform_engine.check_compatibility(tp, requirements or {})
    return {"platform": platform, "compatible": compatible, "issues": issues}

@router.get("/platform/input-modes/{platform}")
async def platform_input_modes(platform: str):
    tp = TargetPlatform(platform) if platform in [p.value for p in TargetPlatform] else TargetPlatform.DESKTOP_WINDOWS
    return _cross_platform_engine.get_supported_input_modes(tp)


# === Character Controller Endpoints ===

@router.get("/character-controller/stats")
async def character_controller_stats():
    return _character_controller.get_stats()

@router.post("/character-controller/create")
async def character_controller_create(character_id: str):
    state = _character_controller.create_character(character_id)
    return state.to_dict()

@router.post("/character-controller/set-input")
async def character_controller_set_input(character_id: str, horizontal_x: float = 0.0,
                                          horizontal_y: float = 0.0, jump: bool = False,
                                          run: bool = False, crouch: bool = False):
    state = _character_controller.set_movement_input(
        character_id, (horizontal_x, horizontal_y), jump, run, crouch)
    return state.to_dict() if state else {}

@router.post("/character-controller/update")
async def character_controller_update(character_id: str, delta_time: float = 0.016,
                                       is_grounded: bool = True):
    state = _character_controller.update(character_id, delta_time, is_grounded)
    return state.to_dict() if state else {}

@router.get("/character-controller/state/{character_id}")
async def character_controller_state(character_id: str):
    state = _character_controller.get_state(character_id)
    return state.to_dict() if state else {}


# === Vehicle System Endpoints ===

@router.get("/vehicle/stats")
async def vehicle_stats():
    return _vehicle_system.get_stats()

@router.post("/vehicle/create")
async def vehicle_create(vehicle_id: str, vehicle_type: str = "sedan"):
    vt = VehicleType(vehicle_type) if vehicle_type in [v.value for v in VehicleType] else VehicleType.SEDAN
    state = _vehicle_system.create_vehicle(vehicle_id, vt)
    return state.to_dict()

@router.post("/vehicle/set-input")
async def vehicle_set_input(vehicle_id: str, throttle: float = 0.0,
                            steering: float = 0.0, brake: float = 0.0,
                            handbrake: bool = False):
    state = _vehicle_system.set_input(vehicle_id, throttle, steering, brake, handbrake)
    return state.to_dict() if state else {}

@router.post("/vehicle/update")
async def vehicle_update(vehicle_id: str, delta_time: float = 0.016):
    state = _vehicle_system.update(vehicle_id, delta_time)
    return state.to_dict() if state else {}

@router.get("/vehicle/state/{vehicle_id}")
async def vehicle_state(vehicle_id: str):
    state = _vehicle_system.get_state(vehicle_id)
    return state.to_dict() if state else {}


# === Dynamic Music Endpoints ===

@router.get("/music/stats")
async def music_stats():
    return _dynamic_music.get_stats()

@router.post("/music/set-state")
async def music_set_state(state: str = "ambient", immediate: bool = False):
    ms = MusicState(state) if state in [s.value for s in MusicState] else MusicState.AMBIENT
    _dynamic_music.set_state(ms, immediate)
    return _dynamic_music.get_stats()

@router.post("/music/update")
async def music_update(delta_time: float = 0.016):
    return _dynamic_music.update(delta_time)

@router.get("/music/current-config")
async def music_current_config():
    config = _dynamic_music.get_current_config()
    return config.to_dict() if config else {}


# === Destruction System Endpoints ===

@router.get("/destruction/stats")
async def destruction_stats():
    return _destruction_system.get_stats()

@router.post("/destruction/create")
async def destruction_create(object_id: str, material: str = "wood",
                              health: float = None):
    mt = MaterialType(material) if material in [m.value for m in MaterialType] else MaterialType.WOOD
    obj = _destruction_system.create_object(object_id, mt, health)
    return obj.to_dict()

@router.post("/destruction/damage")
async def destruction_damage(object_id: str, amount: float = 10.0,
                              damage_type: str = "physical"):
    dt = DamageType(damage_type) if "DamageType" in globals() and damage_type in [d.value for d in DamageType] else None
    event = _destruction_system.apply_damage(object_id, amount)
    return event.to_dict() if event else {}

@router.post("/destruction/repair")
async def destruction_repair(object_id: str, amount: float = -1):
    obj = _destruction_system.repair(object_id, amount)
    return obj.to_dict() if obj else {}

@router.post("/destruction/objects-in-radius")
async def destruction_objects_in_radius(x: float = 0, y: float = 0, z: float = 0,
                                         radius: float = 10.0):
    objects = _destruction_system.get_objects_in_radius((x, y, z), radius)
    return [o.to_dict() for o in objects]


# === Reputation System Endpoints ===

@router.get("/reputation/stats")
async def reputation_stats():
    return _reputation_system.get_stats()

@router.post("/reputation/create-faction")
async def reputation_create_faction(faction_id: str, name: str,
                                     description: str = "", color: str = "#888888"):
    faction = _reputation_system.create_faction(faction_id, name, description, color)
    return faction.to_dict()

@router.post("/reputation/set-relationship")
async def reputation_set_relationship(faction_a: str, faction_b: str,
                                       relationship: str = "neutral",
                                       strength: float = 0.5):
    rel = RelationshipType(relationship) if relationship in [r.value for r in RelationshipType] else RelationshipType.NEUTRAL
    _reputation_system.set_relationship(faction_a, faction_b, rel, strength)
    return {"faction_a": faction_a, "faction_b": faction_b, "relationship": relationship}

@router.post("/reputation/modify")
async def reputation_modify(faction_id: str, amount: float = 0.0,
                            reason: str = "", source: str = "system",
                            propagate: bool = True):
    new_score = _reputation_system.modify_reputation(faction_id, amount, reason, source, propagate)
    return {"faction_id": faction_id, "new_score": new_score}

@router.get("/reputation/standing")
async def reputation_standing():
    return _reputation_system.get_player_standing_summary()

@router.get("/reputation/consequences/{faction_id}")
async def reputation_consequences(faction_id: str):
    return _reputation_system.get_consequences(faction_id)

@router.get("/reputation/statistics")
async def reputation_statistics():
    return _reputation_system.get_faction_statistics()


# === Level Streaming Endpoints ===

@router.get("/streaming/stats")
async def streaming_stats():
    return _level_streaming.get_stats()

@router.post("/streaming/define-chunk")
async def streaming_define_chunk(grid_x: int, grid_y: int,
                                  center_x: float = 0, center_y: float = 0, center_z: float = 0,
                                  size_x: float = 64, size_y: float = 64, size_z: float = 64,
                                  memory_mb: float = 5.0):
    chunk = _level_streaming.define_chunk(grid_x, grid_y,
                                           (center_x, center_y, center_z),
                                           (size_x, size_y, size_z), memory_mb)
    return chunk.to_dict()

@router.post("/streaming/set-player-position")
async def streaming_set_player_position(x: float = 0, y: float = 0, z: float = 0):
    _level_streaming.set_player_position((x, y, z))
    return {"position": [x, y, z]}

@router.post("/streaming/set-radius")
async def streaming_set_radius(radius: float = 128.0):
    _level_streaming.set_streaming_radius(radius)
    return {"radius": radius}

@router.post("/streaming/update")
async def streaming_update(delta_time: float = 0.0):
    _level_streaming.update(delta_time)
    return _level_streaming.get_stats()

@router.get("/streaming/loaded-chunks")
async def streaming_loaded_chunks():
    return _level_streaming.get_loaded_chunks_list()

@router.get("/streaming/progress")
async def streaming_progress():
    return {"progress": _level_streaming.get_loading_progress()}


# === Player Analytics Endpoints ===

@router.get("/player-analytics/stats")
async def player_analytics_stats():
    return _player_analytics.get_stats()

@router.post("/player-analytics/classify")
async def player_analytics_classify(player_id: str = ""):
    if not player_id:
        import uuid
        player_id = f"player_{uuid.uuid4().hex[:8]}"
    _player_analytics.register_player(player_id)
    player = _player_analytics.get_player(player_id)
    archetype = player.archetype.value if player and player.archetype else "unknown"
    return {"player_id": player_id, "archetype": archetype}

@router.post("/player-analytics/predict-churn")
async def player_analytics_predict_churn(player_id: str = ""):
    if not player_id:
        return {"error": "player_id is required"}
    return _player_analytics.predict_churn(player_id)

@router.get("/player-analytics/segments")
async def player_analytics_segments():
    return _player_analytics.get_cohort_insights()

@router.post("/player-analytics/record-session")
async def player_analytics_record_session(player_id: str = "", duration_minutes: float = 0.0,
                                           deaths: int = 0, items_collected: int = 0,
                                           quests_completed: int = 0, social_interactions: int = 0,
                                           exploration_coverage: float = 0.0, success_rate: float = 0.0):
    sid = _player_analytics.record_session(player_id, duration_minutes, deaths,
                                              items_collected, quests_completed,
                                              social_interactions, exploration_coverage, success_rate)
    return {"session_id": sid}


# === Adaptive Difficulty Endpoints ===

@router.get("/adaptive-difficulty/stats")
async def adaptive_difficulty_stats():
    return _adaptive_difficulty.get_stats()

@router.get("/adaptive-difficulty/current-band")
async def adaptive_difficulty_current_band():
    return _adaptive_difficulty.get_current_band()

@router.post("/adaptive-difficulty/report-death")
async def adaptive_difficulty_report_death(enemy_type: str = "", time_since_last_death: float = 0.0):
    _adaptive_difficulty.report_player_death(enemy_type, time_since_last_death)
    return {"band": _adaptive_difficulty.get_current_band()}

@router.post("/adaptive-difficulty/report-success")
async def adaptive_difficulty_report_success(encounter_type: str = "", completion_time: float = 0.0):
    _adaptive_difficulty.report_player_success(encounter_type, completion_time)
    return {"band": _adaptive_difficulty.get_current_band()}

@router.post("/adaptive-difficulty/get-params")
async def adaptive_difficulty_get_params(domain: str = "combat"):
    params = _adaptive_difficulty.get_domain_params(domain)
    return params

@router.get("/adaptive-difficulty/history")
async def adaptive_difficulty_history():
    return {"history": _adaptive_difficulty.get_adaptation_history()}


# === Content Moderation Endpoints ===

@router.get("/content-moderation/stats")
async def content_moderation_stats():
    return _content_moderation.get_stats()

@router.post("/content-moderation/screen")
async def content_moderation_screen(content: str = "", content_type: str = "text",
                                     policy_tier: str = "teen"):
    result = _content_moderation.screen_content(content, content_type, policy_tier)
    return result

@router.post("/content-moderation/batch-screen")
async def content_moderation_batch_screen(items: List[str] = None,
                                           content_type: str = "text",
                                           policy_tier: str = "teen"):
    results = _content_moderation.batch_screen(items or [], content_type, policy_tier)
    return {"results": results}

@router.post("/content-moderation/add-rule")
async def content_moderation_add_rule(pattern: str = "", severity: str = "medium",
                                       action: str = "flag", description: str = ""):
    rule_id = _content_moderation.add_rule(pattern, severity, action, description)
    return {"rule_id": rule_id}

@router.get("/content-moderation/review-queue")
async def content_moderation_review_queue():
    return {"queue": _content_moderation.get_review_queue()}


# === Game Settings Endpoints ===

@router.get("/game-settings/stats")
async def game_settings_stats():
    return _game_settings.get_stats()

@router.post("/game-settings/generate")
async def game_settings_generate(name: str = "Default Profile",
                                  quality_preset: str = "medium",
                                  platform: str = "desktop",
                                  target_fps: int = 60):
    from sparkai.agent.agent_game_settings import QualityPreset
    try:
        quality = QualityPreset(quality_preset)
    except ValueError:
        quality = QualityPreset.MEDIUM
    profile = _game_settings.create_profile(name, quality, platform, target_fps)
    return {"profile_id": profile.profile_id, "settings": profile.settings}

@router.get("/game-settings/domain/{domain}")
async def game_settings_domain(domain: str, profile_id: str = ""):
    if not profile_id:
        return {"error": "profile_id is required"}
    try:
        sd = SettingsDomain(domain)
    except ValueError:
        return {"error": f"Invalid domain: {domain}", "valid_domains": [d.value for d in SettingsDomain]}
    return {"settings": _game_settings.get_domain_settings(profile_id, sd)}

@router.post("/game-settings/override")
async def game_settings_override(profile_id: str = "", key: str = "", value: str = ""):
    if not profile_id:
        return {"error": "profile_id is required"}
    success = _game_settings.update_setting(profile_id, key, value)
    return {"success": success}

@router.post("/game-settings/detect-conflicts")
async def game_settings_detect_conflicts(profile_id: str = ""):
    if not profile_id:
        return {"error": "profile_id is required"}
    conflicts = _game_settings.validate_profile(profile_id)
    return {"conflicts": [c.to_dict() for c in conflicts]}

@router.get("/game-settings/predefined")
async def game_settings_predefined():
    profiles = _game_settings.list_profiles()
    stats = _game_settings.get_stats()
    return {"profiles": profiles, "stats": stats}


# === Water System Endpoints ===

@router.get("/water-system/stats")
async def water_system_stats():
    return _water_system.get_stats()

@router.post("/water-system/create-body")
async def water_system_create_body(body_type: str = "lake", name: str = "",
                                    position_x: float = 0.0, position_y: float = 0.0,
                                    position_z: float = 0.0, size_x: float = 100.0,
                                    size_y: float = 100.0, size_z: float = 10.0):
    body_id = _water_system.create_water_body(body_type, name,
                                                (position_x, position_y, position_z),
                                                (size_x, size_y, size_z))
    return {"body_id": body_id}

@router.post("/water-system/update-physics")
async def water_system_update_physics(delta_time: float = 0.016):
    _water_system.update_physics(delta_time)
    return {"success": True}

@router.post("/water-system/add-object")
async def water_system_add_object(object_id: str = "", density: float = 1.0,
                                   drag: float = 0.5, angular_drag: float = 0.3):
    _water_system.add_water_object(object_id, density, drag, angular_drag)
    return {"success": True}

@router.post("/water-system/remove-object")
async def water_system_remove_object(object_id: str = ""):
    _water_system.remove_water_object(object_id)
    return {"success": True}


# === Spline System Endpoints ===

@router.get("/spline-system/stats")
async def spline_system_stats():
    return _spline_system.get_stats()

@router.post("/spline-system/create-path")
async def spline_system_create_path(name: str = "", spline_type: str = "bezier",
                                     closed_loop: bool = False, resolution: int = 100):
    path_id = _spline_system.create_path(name, spline_type, closed_loop, resolution)
    return {"path_id": path_id}

@router.post("/spline-system/add-point")
async def spline_system_add_point(path_id: str = "", x: float = 0.0, y: float = 0.0,
                                   z: float = 0.0):
    _spline_system.add_control_point(path_id, (x, y, z))
    return {"success": True}

@router.get("/spline-system/evaluate/{path_id}")
async def spline_system_evaluate(path_id: str, t: float = 0.0):
    point = _spline_system.evaluate_at(path_id, t)
    return point

@router.get("/spline-system/length/{path_id}")
async def spline_system_length(path_id: str):
    return {"length": _spline_system.get_total_length(path_id)}

@router.get("/spline-system/uniform-points/{path_id}")
async def spline_system_uniform_points(path_id: str, count: int = 10):
    points = _spline_system.get_uniform_points(path_id, count)
    return {"points": points}


# === Post Processing Endpoints ===

@router.get("/post-processing/stats")
async def post_processing_stats():
    return _post_processing.get_stats()

@router.post("/post-processing/create-stack")
async def post_processing_create_stack(name: str = "", priority: int = 0, layer_mask: int = 0xFFFFFFFF):
    stack_id = _post_processing.create_stack(name, priority, layer_mask)
    return {"stack_id": stack_id}

@router.post("/post-processing/add-effect")
async def post_processing_add_effect(stack_id: str = "", effect: str = "bloom",
                                      intensity: float = 1.0):
    _post_processing.add_effect(stack_id, effect, intensity)
    return {"success": True}

@router.post("/post-processing/enable-effect")
async def post_processing_enable_effect(stack_id: str = "", effect: str = "bloom"):
    _post_processing.enable_effect(stack_id, effect)
    return {"success": True}

@router.post("/post-processing/disable-effect")
async def post_processing_disable_effect(stack_id: str = "", effect: str = "bloom"):
    _post_processing.disable_effect(stack_id, effect)
    return {"success": True}


# === Trigger System Endpoints ===

@router.get("/trigger-system/stats")
async def trigger_system_stats():
    return _trigger_system.get_stats()

@router.post("/trigger-system/create")
async def trigger_system_create(name: str = "", trigger_type: str = "enter_zone",
                                 shape: str = "box", position_x: float = 0.0,
                                 position_y: float = 0.0, position_z: float = 0.0,
                                 size_x: float = 10.0, size_y: float = 10.0,
                                 size_z: float = 10.0, activation: str = "once",
                                 cooldown: float = 0.0):
    trigger_id = _trigger_system.create_trigger(name, trigger_type, shape,
                                                   (position_x, position_y, position_z),
                                                   (size_x, size_y, size_z), activation, cooldown)
    return {"trigger_id": trigger_id}

@router.post("/trigger-system/fire")
async def trigger_system_fire(trigger_id: str = ""):
    result = _trigger_system.fire_trigger(trigger_id)
    return {"fired": result}

@router.get("/trigger-system/active")
async def trigger_system_active():
    triggers = _trigger_system.get_active_triggers()
    return {"triggers": triggers}

@router.post("/trigger-system/enable")
async def trigger_system_enable(trigger_id: str = ""):
    _trigger_system.enable_trigger(trigger_id)
    return {"success": True}

@router.post("/trigger-system/disable")
async def trigger_system_disable(trigger_id: str = ""):
    _trigger_system.disable_trigger(trigger_id)
    return {"success": True}


# === Game Progression Endpoints ===

@router.get("/progression/stats")
async def progression_stats():
    return _game_progression.get_stats()

@router.post("/progression/create-curve")
async def progression_create_curve(name: str = "", curve_type: str = "wave", node_count: int = 10):
    curve = _game_progression.create_curve(name, curve_type, node_count)
    return curve.__dict__ if hasattr(curve, '__dict__') else str(curve)

@router.post("/progression/add-node")
async def progression_add_node(curve_id: str = "", phase: str = "early", level: float = 1.0,
                                 multiplier: float = 1.0, reward_type: str = "xp",
                                 reward_amount: float = 100.0, minutes: float = 30.0):
    node_id = _game_progression.add_node(curve_id, phase, level, multiplier, reward_type, reward_amount, minutes)
    return {"node_id": node_id}

@router.get("/progression/pacing/{curve_id}")
async def progression_pacing(curve_id: str):
    score = _game_progression.calculate_pacing_score(curve_id)
    return {"curve_id": curve_id, "pacing_score": score}


# === Narrative Graph Endpoints ===

@router.get("/narrative/stats")
async def narrative_stats():
    return _narrative_graph.get_stats()

@router.post("/narrative/create-graph")
async def narrative_create_graph(title: str = "", root_title: str = ""):
    graph = _narrative_graph.create_graph(title, {"title": root_title, "node_type": "plot_point"})
    return graph.__dict__ if hasattr(graph, '__dict__') else str(graph)

@router.post("/narrative/add-node")
async def narrative_add_node(graph_id: str = "", node_type: str = "dialogue",
                               title: str = "", description: str = ""):
    node = _narrative_graph.add_node(graph_id, node_type, title, description)
    return {"node": str(node)}

@router.post("/narrative/add-edge")
async def narrative_add_edge(graph_id: str = "", from_node: str = "", to_node: str = ""):
    result = _narrative_graph.add_edge(graph_id, from_node, to_node)
    return {"added": result}

@router.get("/narrative/validate/{graph_id}")
async def narrative_validate(graph_id: str):
    return _narrative_graph.validate_graph(graph_id)


# === Asset Harmonizer Endpoints ===

@router.get("/harmonizer/stats")
async def harmonizer_stats():
    return _asset_harmonizer.get_stats()

@router.post("/harmonizer/register")
async def harmonizer_register(name: str = "", asset_type: str = "", category: str = "",
                                visual_style: str = "stylized_cartoon"):
    descriptor = _asset_harmonizer.register_asset(name, asset_type, category, {"visual_style": visual_style})
    return {"id": descriptor.id, "name": descriptor.name}

@router.post("/harmonizer/check")
async def harmonizer_check(asset_a: str = "", asset_b: str = ""):
    result = _asset_harmonizer.check_compatibility(asset_a, asset_b)
    return result

@router.get("/harmonizer/clashes")
async def harmonizer_clashes():
    return {"clashes": _asset_harmonizer.find_clashing_assets()}


# === Agentic Memory Endpoints ===

@router.get("/memory/stats")
async def memory_stats():
    return _agentic_memory.get_stats()

@router.post("/memory/store")
async def memory_store(text: str = "", category: str = "episodic", importance: float = 0.5):
    entry_id = _agentic_memory.store({"text": text}, category, importance, ["general"])
    return {"entry_id": entry_id}

@router.get("/memory/retrieve/{entry_id}")
async def memory_retrieve(entry_id: str):
    return _agentic_memory.retrieve(entry_id)

@router.post("/memory/search")
async def memory_search(query: str = "", limit: int = 10, min_score: float = 0.0):
    results = _agentic_memory.search(query, limit, min_score)
    return {"results": results}

@router.post("/memory/consolidate")
async def memory_consolidate(from_tier: str = "working", to_tier: str = "short_term", threshold: float = 0.6):
    count = _agentic_memory.consolidate(from_tier, to_tier, threshold)
    return {"consolidated": count}


# === Multi-Agent Orchestration Endpoints ===

@router.get("/orchestration/stats")
async def orchestration_stats():
    return _multi_agent_orchestrator.get_stats()

@router.post("/orchestration/create-session")
async def orchestration_create_session(goal: str = "", consensus_method: str = "majority_vote"):
    session = _multi_agent_orchestrator.create_session(goal, consensus_method)
    return session.__dict__ if hasattr(session, '__dict__') else str(session)

@router.post("/orchestration/add-task")
async def orchestration_add_task(session_id: str = "", description: str = "",
                                   role: str = "generator", priority: int = 1):
    task_id = _multi_agent_orchestrator.add_task(session_id, description, role, priority, [])
    return {"task_id": task_id}

@router.post("/orchestration/execute")
async def orchestration_execute(session_id: str = ""):
    _multi_agent_orchestrator.assign_tasks(session_id)
    results = _multi_agent_orchestrator.execute_session(session_id)
    return results

@router.get("/orchestration/progress/{session_id}")
async def orchestration_progress(session_id: str):
    return _multi_agent_orchestrator.get_session_progress(session_id)


# === Realtime Collaboration Endpoints ===

@router.get("/collaboration/stats")
async def collaboration_stats():
    return _realtime_collaboration.get_stats()

@router.post("/collaboration/create-session")
async def collaboration_create_session(mode: str = "real_time"):
    session = _realtime_collaboration.create_session(mode)
    return session.__dict__ if hasattr(session, '__dict__') else str(session)

@router.post("/collaboration/join")
async def collaboration_join(session_id: str = "", user_id: str = ""):
    result = _realtime_collaboration.join_session(session_id, user_id)
    return {"joined": result}

@router.post("/collaboration/leave")
async def collaboration_leave(session_id: str = "", user_id: str = ""):
    result = _realtime_collaboration.leave_session(session_id, user_id)
    return {"left": result}

@router.get("/collaboration/sessions")
async def collaboration_sessions():
    return {"sessions": _realtime_collaboration.get_active_sessions()}


# === Material System Endpoints ===

@router.get("/material/stats")
async def material_stats():
    return _material_system.get_stats()

@router.post("/material/create")
async def material_create(name: str = "", domain: str = "surface", blend_mode: str = "opaque"):
    mat_id = _material_system.create_material(name, domain, blend_mode)
    return {"material_id": mat_id}

@router.post("/material/set-property")
async def material_set_property(material_id: str = "", prop_name: str = "",
                                  value: str = ""):
    _material_system.set_property(material_id, prop_name, value)
    return {"success": True}


# === Navmesh System Endpoints ===

@router.get("/navmesh/stats")
async def navmesh_stats():
    return _navmesh_system.get_stats()

@router.post("/navmesh/find-path")
async def navmesh_find_path(start_x: float = 0.0, start_y: float = 0.0,
                               end_x: float = 0.0, end_y: float = 0.0):
    query = _navmesh_system.find_path(start_x, start_y, end_x, end_y, 0.5, 2.0, 45.0)
    return query.__dict__ if hasattr(query, '__dict__') else str(query)


# === Occlusion System Endpoints ===

@router.get("/occlusion/stats")
async def occlusion_stats():
    return _occlusion_system.get_stats()

@router.post("/occlusion/create-volume")
async def occlusion_create_volume(name: str = "", volume_type: str = "box",
                                    px: float = 0.0, py: float = 0.0, pz: float = 0.0,
                                    sx: float = 10.0, sy: float = 10.0, sz: float = 10.0):
    vol = _occlusion_system.create_volume(name, volume_type, px, py, pz, sx, sy, sz)
    return vol.__dict__ if hasattr(vol, '__dict__') else str(vol)

@router.get("/occlusion/visible")
async def occlusion_visible():
    return {"visible": _occlusion_system.get_visible_objects()}


# === Timeline System Endpoints ===

@router.get("/timeline/stats")
async def timeline_stats():
    return _timeline_system.get_stats()

@router.post("/timeline/create")
async def timeline_create(name: str = "", duration_seconds: float = 10.0):
    tl = _timeline_system.create_timeline(name, duration_seconds)
    return tl.__dict__ if hasattr(tl, '__dict__') else str(tl)

@router.post("/timeline/add-track")
async def timeline_add_track(timeline_id: str = "", name: str = "", track_type: str = "animation"):
    track = _timeline_system.add_track(timeline_id, name, track_type)
    return track.__dict__ if hasattr(track, '__dict__') else str(track)

@router.post("/timeline/add-keyframe")
async def timeline_add_keyframe(track_id: str = "", time: float = 0.0, value: str = ""):
    kf = _timeline_system.add_keyframe(track_id, time, value)
    return kf.__dict__ if hasattr(kf, '__dict__') else str(kf)

@router.post("/timeline/play/{timeline_id}")
async def timeline_play(timeline_id: str):
    result = _timeline_system.play(timeline_id)
    return {"playing": result}

@router.post("/timeline/pause/{timeline_id}")
async def timeline_pause(timeline_id: str):
    result = _timeline_system.pause(timeline_id)
    return {"paused": result}


# === VFX System Endpoints ===

@router.get("/vfx/stats")
async def vfx_stats():
    return _vfx_system.get_stats()

@router.post("/vfx/create")
async def vfx_create(name: str = "", vfx_type: str = "particle_burst",
                       emission_shape: str = "point", max_particles: int = 100):
    effect = _vfx_system.create_effect(name, vfx_type, emission_shape, max_particles)
    return effect.__dict__ if hasattr(effect, '__dict__') else str(effect)

@router.post("/vfx/play/{effect_id}")
async def vfx_play(effect_id: str):
    _vfx_system.play_effect(effect_id)
    return {"playing": True}

@router.post("/vfx/stop/{effect_id}")
async def vfx_stop(effect_id: str):
    _vfx_system.stop_effect(effect_id)
    return {"stopped": True}

@router.get("/vfx/active")
async def vfx_active():
    return {"effects": _vfx_system.get_active_effects()}

# === Goal Decomposer Endpoints ===

@router.get("/goal/stats")
async def goal_decomposer_stats():
    return _goal_decomposer.get_stats()

@router.post("/goal/decompose")
async def goal_decomposer_decompose(goal: str = ""):
    result = _goal_decomposer.decompose(goal)
    return result.__dict__ if hasattr(result, '__dict__') else str(result)

@router.get("/goal/progress/{decomposition_id}")
async def goal_decomposer_progress(decomposition_id: str):
    return _goal_decomposer.get_progress(decomposition_id)

@router.get("/goal/blocking/{decomposition_id}")
async def goal_decomposer_blocking(decomposition_id: str):
    return {"chain": _goal_decomposer.get_blocking_chain(decomposition_id)}


# === Skill Autonomy Endpoints ===

@router.get("/skill/stats")
async def skill_autonomy_stats():
    return _skill_autonomy.get_stats()

@router.get("/skill/search")
async def skill_search(query: str = ""):
    results = _skill_autonomy.search_skills(query)
    return {"results": results}

@router.post("/skill/extract")
async def skill_extract(session_turns: str = ""):
    import json
    turns = json.loads(session_turns) if session_turns else []
    skill = _skill_autonomy.extract_skill_from_session(turns)
    return {"skill_id": skill.id, "name": skill.name}

@router.post("/skill/apply")
async def skill_apply(skill_id: str = "", parameters: str = "{}"):
    import json
    params = json.loads(parameters)
    step = _skill_autonomy.apply_skill(skill_id, params)
    return step.__dict__ if hasattr(step, '__dict__') else str(step)


# === Expression Validator Endpoints ===

@router.get("/expression/stats")
async def expression_validator_stats():
    return _expression_validator.get_stats()

@router.post("/expression/validate")
async def expression_validate(code: str = ""):
    result = _expression_validator.validate(code)
    return {"has_errors": result.has_errors if hasattr(result, 'has_errors') else False}

@router.get("/expression/functions")
async def expression_functions():
    return {"functions": _expression_validator.get_available_functions()}


# === Variable Introspection Endpoints ===

@router.get("/variables/stats")
async def variable_introspection_stats():
    return _variable_introspection.get_stats()

@router.post("/variables/register")
async def variables_register(name: str = "", scope: str = "scene", kind: str = "number",
                               default_value: str = "", description: str = ""):
    var = _variable_introspection.register_variable(name, scope, kind, default_value, description)
    return var.__dict__ if hasattr(var, '__dict__') else str(var)

@router.post("/variables/set")
async def variables_set(definition_id: str = "", value: str = "", actor: str = "system"):
    instance = _variable_introspection.set_value(definition_id, value, actor)
    return instance.__dict__ if hasattr(instance, '__dict__') else str(instance)

@router.get("/variables/context/{scope}")
async def variables_context(scope: str = "global"):
    return {"context": _variable_introspection.get_ai_context(scope)}


# === Theme Designer Endpoints ===

@router.get("/theme/stats")
async def theme_designer_stats():
    return _theme_designer.get_stats()

@router.post("/theme/generate")
async def theme_generate(description: str = "", mood: str = "dark"):
    theme = _theme_designer.generate_theme(description, mood)
    return theme.__dict__ if hasattr(theme, '__dict__') else str(theme)

@router.post("/theme/export-css/{theme_id}")
async def theme_export_css(theme_id: str):
    return {"css": _theme_designer.export_css_variables(theme_id)}


# === Import Pipeline Endpoints ===

@router.get("/import/stats")
async def import_pipeline_stats():
    return _import_pipeline.get_stats()

@router.post("/import/recommend")
async def import_recommend(source_path: str = "", description: str = ""):
    preset = _import_pipeline.ai_recommend_preset(source_path, description)
    return preset.__dict__ if hasattr(preset, '__dict__') else str(preset)

@router.post("/import/queue")
async def import_queue(source_path: str = "", import_type: str = "texture", preset_id: str = ""):
    task = _import_pipeline.queue_import(source_path, import_type, preset_id)
    return {"task_id": task.id, "status": task.status if hasattr(task, 'status') else "queued"}

@router.post("/import/batch")
async def import_batch(paths: str = "", description: str = ""):
    import json
    path_list = json.loads(paths) if paths else []
    tasks = _import_pipeline.process_batch(path_list, description)
    return {"task_count": len(tasks)}


# === Performance Advisor Endpoints ===

@router.get("/perf/stats")
async def perf_advisor_stats():
    return _performance_advisor.get_stats()

@router.post("/perf/record")
async def perf_record(domain: str = "rendering", metrics: str = "{}"):
    import json
    m = json.loads(metrics)
    snapshot = _performance_advisor.record_snapshot(domain, m)
    return snapshot.__dict__ if hasattr(snapshot, '__dict__') else str(snapshot)

@router.get("/perf/bottlenecks")
async def perf_bottlenecks():
    suggestions = _performance_advisor.analyze_bottlenecks()
    return {"suggestions": suggestions}

@router.post("/perf/diagnose")
async def perf_diagnose(snapshot_id: str = "", query: str = ""):
    suggestions = _performance_advisor.ai_diagnose(snapshot_id, query)
    return {"suggestions": suggestions}


# === Profiler System Endpoints ===

@router.get("/profiler/stats")
async def profiler_sys_stats():
    return _profiler_sys.get_stats()

@router.post("/profiler/add-monitor")
async def profiler_add_monitor(name: str = "", category: str = "rendering",
                                  monitor_type: str = "counter", unit: str = "ms"):
    monitor = _profiler_sys.add_monitor(name, category, monitor_type, unit)
    return monitor.__dict__ if hasattr(monitor, '__dict__') else str(monitor)

@router.post("/profiler/record-frame")
async def profiler_record_frame():
    frame = _profiler_sys.record_frame()
    return frame.__dict__ if hasattr(frame, '__dict__') else str(frame)

@router.get("/profiler/frame-summary")
async def profiler_frame_summary():
    return _profiler_sys.get_frame_summary()


# === Expression Engine Endpoints ===

@router.get("/expr-engine/stats")
async def expr_engine_stats():
    return _expression_engine.get_stats()

@router.post("/expr-engine/compile")
async def expr_compile(expression: str = ""):
    ok = _expression_engine.compile(expression)
    return {"compiled": ok}

@router.post("/expr-engine/execute")
async def expr_execute(expression: str = "", context_json: str = "{}"):
    import json
    ctx = _expression_engine._ExpressionEngine__build_context()
    ctx.variables = json.loads(context_json)
    result = _expression_engine.execute(expression, ctx)
    return result.__dict__ if hasattr(result, '__dict__') else str(result)


# === Extension Runtime Endpoints ===

@router.get("/extension/stats")
async def extension_stats():
    return _extension_runtime.get_stats()

@router.get("/extension/loaded")
async def extension_loaded():
    return {"extensions": _extension_runtime.get_loaded_extensions()}

@router.post("/extension/load")
async def extension_load(name: str = "", version: str = "1.0.0", author: str = "",
                           description: str = "", category: str = "", entry: str = ""):
    from sparkai.engine.extension_runtime import ExtensionManifest
    manifest = ExtensionManifest(name=name, version=version, author=author,
                                   description=description, category=category,
                                   entry_point=entry)
    ext = _extension_runtime.load_extension(manifest)
    return {"extension_id": ext.id, "status": ext.status.value}


# === Terrain System Endpoints ===

@router.get("/terrain/stats")
async def terrain_stats():
    return _terrain_system.get_stats()

@router.post("/terrain/create")
async def terrain_create(width: int = 256, depth: int = 256, resolution: int = 1, seed: int = 42):
    terrain_id = _terrain_system.create_terrain(width, depth, resolution, seed)
    return {"terrain_id": terrain_id}

@router.post("/terrain/smooth")
async def terrain_smooth(chunk_id: str = "", radius: float = 3.0):
    ok = _terrain_system.smooth_terrain(chunk_id, radius)
    return {"smoothed": ok}


# === Fog of War Endpoints ===

@router.get("/fog/stats")
async def fog_stats():
    return _fog_of_war.get_stats()

@router.post("/fog/create-layer")
async def fog_create_layer(name: str = "", width: int = 64, height: int = 64, cell_size: float = 1.0):
    layer = _fog_of_war.create_layer(name, width, height, cell_size)
    return layer.__dict__ if hasattr(layer, '__dict__') else str(layer)

@router.post("/fog/reveal")
async def fog_reveal(layer_id: str = "", center_x: float = 0.0, center_y: float = 0.0,
                      radius: float = 5.0, revealer_id: str = "player"):
    count = _fog_of_war.reveal_area(layer_id, center_x, center_y, radius, revealer_id)
    return {"cells_revealed": count}


# === Shader Graph Endpoints ===

@router.get("/shader-graph/stats")
async def shader_graph_stats():
    return _shader_graph.get_stats()

@router.post("/shader-graph/create")
async def shader_graph_create(name: str = ""):
    graph = _shader_graph.create_graph(name)
    return graph

@router.post("/shader-graph/add-node")
async def shader_graph_add_node(graph_id: str = "", node_type: str = "", name: str = ""):
    node = _shader_graph.add_node(graph_id, node_type, name)
    return node.__dict__ if hasattr(node, '__dict__') else str(node)

@router.post("/shader-graph/connect")
async def shader_graph_connect(graph_id: str = "", from_node_id: str = "",
                                from_pin: str = "", to_node_id: str = "", to_pin: str = ""):
    conn = _shader_graph.add_connection(graph_id, from_node_id, from_pin, to_node_id, to_pin)
    return str(conn)

@router.post("/shader-graph/compile")
async def shader_graph_compile(graph_id: str = "", target: str = "glsl"):
    code = _shader_graph.compile_to_glsl(graph_id) if target == "glsl" else _shader_graph.compile_to_hlsl(graph_id)
    return {"source": code}

@router.post("/shader-graph/validate")
async def shader_graph_validate(graph_id: str = ""):
    valid, errors = _shader_graph.validate_graph(graph_id)
    return {"valid": valid, "errors": errors}

@router.post("/shader-graph/export")
async def shader_graph_export(graph_id: str = ""):
    data = _shader_graph.export_graph(graph_id)
    return {"export": data}

@router.post("/shader-graph/import")
async def shader_graph_import(data: str = "{}"):
    import json
    graph_id = _shader_graph.import_graph(json.loads(data))
    return {"graph_id": graph_id}


# === Build Pipeline Endpoints ===

@router.get("/build/stats")
async def build_stats():
    return _build_pipeline.get_stats()

@router.post("/build/create")
async def build_create(name: str = "", platform: str = "web"):
    pipeline = _build_pipeline.create_pipeline(name, platform)
    return str(pipeline)

@router.post("/build/execute")
async def build_execute(pipeline_id: str = ""):
    result = _build_pipeline.execute(pipeline_id)
    return result

@router.get("/build/status")
async def build_status(pipeline_id: str = ""):
    status = _build_pipeline.get_status(pipeline_id)
    return status

@router.post("/build/cancel")
async def build_cancel(pipeline_id: str = ""):
    _build_pipeline.cancel_build(pipeline_id)
    return {"cancelled": True}

@router.get("/build/artifacts")
async def build_artifacts(pipeline_id: str = ""):
    artifacts = _build_pipeline.get_artifacts(pipeline_id)
    return {"artifacts": artifacts}

@router.post("/build/validate")
async def build_validate(pipeline_id: str = ""):
    valid, errors = _build_pipeline.validate_pipeline(pipeline_id)
    return {"valid": valid, "errors": errors}


# === Tileset System Endpoints ===

@router.get("/tileset/stats")
async def tileset_stats():
    return _tileset_system.get_stats()

@router.post("/tileset/create")
async def tileset_create(name: str = "", tile_width: int = 32, tile_height: int = 32,
                          columns: int = 16, rows: int = 16):
    tileset = _tileset_system.create_tileset(
        name=name, tile_size=tile_width, columns=columns, rows=rows
    )
    return {"tileset_id": tileset.id}

@router.post("/tileset/add-tile")
async def tileset_add_tile(tileset_id: str = "", name: str = "", index: int = 0, texture_region: str = ""):
    tile = _tileset_system.add_tile(tileset_id, name, index, texture_region)
    return tile.__dict__ if hasattr(tile, '__dict__') else str(tile)

@router.post("/tileset/set-collision")
async def tileset_set_collision(tileset_id: str = "", tile_id: str = "", shape: str = "full"):
    _tileset_system.set_tile_collision(tileset_id, tile_id, shape)
    return {"updated": True}

@router.post("/tileset/import-sheet")
async def tileset_import_sheet(tileset_id: str = "", file_path: str = "",
                                tile_width: int = 32, tile_height: int = 32, columns: int = 16, rows: int = 16):
    count = _tileset_system.import_from_spritesheet(tileset_id, file_path, tile_width, tile_height, columns, rows)
    return {"tiles_imported": count}

@router.post("/tileset/export")
async def tileset_export(tileset_id: str = ""):
    data = _tileset_system.export_to_json(tileset_id)
    return {"export": data}

@router.post("/tileset/auto-collision")
async def tileset_auto_collision(tileset_id: str = ""):
    count = _tileset_system.auto_detect_collisions(tileset_id)
    return {"collisions_detected": count}


# === Resource Pack Endpoints ===

@router.get("/resource-pack/stats")
async def resource_pack_stats():
    return _resource_pack.get_stats()

@router.post("/resource-pack/create")
async def resource_pack_create(name: str = "", version: str = "1.0.0", pack_type: str = "asset"):
    pack = _resource_pack.create_pack(name, pack_type, version)
    return {"pack_id": pack.id}

@router.post("/resource-pack/add-entry")
async def resource_pack_add_entry(pack_id: str = "", file_path: str = "", entry_type: str = "texture"):
    entry = _resource_pack.add_entry(pack_id, file_path, entry_type)
    return entry.__dict__ if hasattr(entry, '__dict__') else str(entry)

@router.post("/resource-pack/build")
async def resource_pack_build(pack_id: str = ""):
    result = _resource_pack.build(pack_id)
    return {"built": result is not None}

@router.post("/resource-pack/verify")
async def resource_pack_verify(pack_id: str = ""):
    valid, errors = _resource_pack.verify_integrity(pack_id)
    return {"valid": valid, "errors": errors}

@router.get("/resource-pack/contents")
async def resource_pack_contents(pack_id: str = ""):
    contents = _resource_pack.list_contents(pack_id)
    return {"contents": contents}

@router.post("/resource-pack/merge")
async def resource_pack_merge(source_pack_id: str = "", target_pack_id: str = ""):
    result = _resource_pack.merge_packs(source_pack_id, target_pack_id)
    return {"merged": result}


# === Input Profile System Endpoints ===

@router.get("/input-profile/stats")
async def input_profile_stats():
    return _input_profile_system.get_stats()

@router.post("/input-profile/create")
async def input_profile_create(name: str = "", device_type: str = "keyboard_mouse"):
    from sparkai.engine.input_profile_system import InputDevice
    profile = _input_profile_system.create_profile(name, InputDevice(device_type))
    return profile.__dict__ if hasattr(profile, '__dict__') else str(profile)

@router.post("/input-profile/add-binding")
async def input_profile_add_binding(profile_id: str = "", action_name: str = "",
                                     key_code: str = "", device_type: str = "keyboard_mouse"):
    from sparkai.engine.input_profile_system import InputBinding, ActionType
    binding = InputBinding(action_name=action_name, primary_input=key_code, action_type=ActionType.PRESS)
    result = _input_profile_system.add_binding(profile_id, binding)
    return {"added": result}

@router.post("/input-profile/set-active")
async def input_profile_set_active(profile_id: str = ""):
    _input_profile_system.set_active_profile(profile_id)
    return {"active_profile": profile_id}

@router.post("/input-profile/auto-configure")
async def input_profile_auto_configure(device_type: str = "keyboard_mouse"):
    from sparkai.engine.input_profile_system import InputDevice
    profile = _input_profile_system.auto_configure(InputDevice(device_type))
    return {"profile_id": profile.id if hasattr(profile, 'id') else str(profile)}

@router.post("/input-profile/detect-device")
async def input_profile_detect_device(hint: str = ""):
    device = _input_profile_system.detect_device(hint if hint else None)
    return {"device": device.value if hasattr(device, 'value') else str(device)}

@router.post("/input-profile/export")
async def input_profile_export(profile_id: str = ""):
    data = _input_profile_system.export_profile(profile_id)
    return {"export": data}

@router.post("/input-profile/validate")
async def input_profile_validate(profile_id: str = ""):
    valid, errors = _input_profile_system.validate_profile(profile_id)
    return {"valid": valid, "errors": errors}


# === Shader Advisor Endpoints ===

@router.get("/shader-advisor/stats")
async def shader_advisor_stats():
    return _shader_advisor.get_stats()

@router.post("/shader-advisor/create-preset")
async def shader_advisor_create_preset(name: str = "", domain: str = "surface",
                                        language: str = "glsl", technique: str = "pbr"):
    preset = _shader_advisor.create_preset(name, domain, language, technique)
    return preset.__dict__ if hasattr(preset, '__dict__') else str(preset)

@router.post("/shader-advisor/generate")
async def shader_advisor_generate(description: str = "", language: str = "glsl"):
    result = _shader_advisor.generate_from_description(description, language)
    return str(result)

@router.post("/shader-advisor/compile-check")
async def shader_advisor_compile_check(preset_id: str = ""):
    result = _shader_advisor.compile_check(preset_id)
    return result

@router.get("/shader-advisor/presets")
async def shader_advisor_presets(domain: str = "", technique: str = ""):
    if domain:
        return _shader_advisor.get_presets_by_domain(domain)
    if technique:
        return _shader_advisor.get_presets_by_technique(technique)
    return []

@router.post("/shader-advisor/recommend")
async def shader_advisor_recommend(scene_description: str = ""):
    result = _shader_advisor.recommend_for_scene(scene_description)
    return str(result)


# === Build Orchestrator Endpoints ===

@router.get("/build-orchestrator/stats")
async def build_orchestrator_stats():
    return _build_orchestrator.get_stats()

@router.post("/build-orchestrator/create-config")
async def build_orchestrator_create_config(name: str = "", platform: str = "web",
                                            optimization: str = "basic", compression: str = "gzip"):
    from sparkai.agent.agent_build_orchestrator import TargetPlatform, OptimizationLevel, CompressionMode
    config = _build_orchestrator.create_config(
        name=name,
        platform=TargetPlatform(platform),
        optimization=OptimizationLevel(optimization),
        compression=CompressionMode(compression),
    )
    return config.__dict__ if hasattr(config, '__dict__') else str(config)

@router.post("/build-orchestrator/create-defaults")
async def build_orchestrator_create_defaults():
    configs = _build_orchestrator.create_default_configs()
    return {"count": len(configs)}

@router.post("/build-orchestrator/queue-build")
async def build_orchestrator_queue(config_id: str = "", project_path: str = ""):
    task_id = _build_orchestrator.queue_build(config_id, project_path)
    return {"task_id": task_id}

@router.post("/build-orchestrator/start-build")
async def build_orchestrator_start(task_id: str = ""):
    started = _build_orchestrator.start_build(task_id)
    return {"started": started}

@router.get("/build-orchestrator/status")
async def build_orchestrator_build_status(task_id: str = ""):
    status = _build_orchestrator.get_build_status(task_id)
    return status

@router.post("/build-orchestrator/cancel")
async def build_orchestrator_cancel(task_id: str = ""):
    _build_orchestrator.cancel_build(task_id)
    return {"cancelled": True}

@router.get("/build-orchestrator/history")
async def build_orchestrator_history(limit: int = 20):
    history = _build_orchestrator.get_build_history(limit)
    return {"history": history}

@router.post("/build-orchestrator/optimize")
async def build_orchestrator_optimize(config_id: str = ""):
    optimized = _build_orchestrator.optimize_config(config_id)
    return optimized.__dict__ if hasattr(optimized, '__dict__') else str(optimized)


# === Recall Engine Endpoints ===

@router.get("/recall/stats")
async def recall_stats():
    return _recall_engine.get_stats()

@router.post("/recall/ingest")
async def recall_ingest(content: str = "", domain: str = "game_mechanics", relevance: str = "medium"):
    from sparkai.agent.agent_recall_engine import RecallDomain, RelevanceScore, KnowledgeFragment
    fragment = KnowledgeFragment(
        content=content,
        domain=RecallDomain(domain),
        relevance=RelevanceScore(relevance),
    )
    frag_id = _recall_engine.ingest_fragment(fragment)
    return {"fragment_id": frag_id}

@router.post("/recall/ingest-session")
async def recall_ingest_session(session_id: str = "", summary: str = ""):
    count = _recall_engine.ingest_from_session(session_id, summary)
    return {"fragments_ingested": count}

@router.post("/recall/search")
async def recall_search(query: str = "", domain: str = "", limit: int = 10):
    from sparkai.agent.agent_recall_engine import RecallDomain, RecallQuery
    rq = RecallQuery(
        text=query,
        domain_filter=RecallDomain(domain) if domain else None,
        max_results=limit,
    )
    results = _recall_engine.search(rq)
    return {"results": [r.__dict__ for r in results] if results else []}

@router.post("/recall/contextual-search")
async def recall_contextual(query: str = "", context_domain: str = "", session_id: str = ""):
    from sparkai.agent.agent_recall_engine import RecallDomain
    results = _recall_engine.contextual_search(query, RecallDomain(context_domain) if context_domain else None, session_id)
    return {"results": [r.__dict__ for r in results] if results else []}

@router.get("/recall/trending")
async def recall_trending(limit: int = 10):
    topics = _recall_engine.get_trending_topics(limit)
    return {"trending": topics}

@router.post("/recall/prune")
async def recall_prune(max_age_days: int = 30):
    count = _recall_engine.prune_stale(max_age_days)
    return {"pruned": count}


# === Interaction Designer Endpoints ===

@router.get("/interaction/stats")
async def interaction_stats():
    return _interaction_designer.get_stats()

@router.post("/interaction/create-flow")
async def interaction_create_flow(name: str = "", game_genre: str = "", accessibility: str = "none"):
    from sparkai.agent.agent_interaction_designer import AccessibilityLevel
    flow = _interaction_designer.create_flow(name, game_genre, AccessibilityLevel(accessibility))
    return flow.__dict__ if hasattr(flow, '__dict__') else str(flow)

@router.post("/interaction/add-node")
async def interaction_add_node(flow_id: str = "", node_type: str = "screen", name: str = "", x: float = 0, y: float = 0):
    from sparkai.agent.agent_interaction_designer import FlowNodeType
    node = _interaction_designer.add_node(flow_id, name, FlowNodeType(node_type), title=name, position_x=x, position_y=y)
    return node.__dict__ if hasattr(node, '__dict__') else str(node)

@router.post("/interaction/add-transition")
async def interaction_add_transition(flow_id: str = "", from_node_id: str = "",
                                      to_node_id: str = "", trigger: str = "", transition_type: str = "click"):
    from sparkai.agent.agent_interaction_designer import TransitionType
    trans = _interaction_designer.add_transition(flow_id, from_node_id, to_node_id,
                                                   trigger, TransitionType(transition_type))
    return trans.__dict__ if hasattr(trans, '__dict__') else str(trans)

@router.post("/interaction/generate")
async def interaction_generate(prompt: str = ""):
    flow = _interaction_designer.generate_flow_from_prompt(prompt)
    return flow.__dict__ if hasattr(flow, '__dict__') else str(flow)

@router.post("/interaction/suggest")
async def interaction_suggest(flow_id: str = ""):
    suggestions = _interaction_designer.suggest_improvements(flow_id)
    return {"suggestions": suggestions}

@router.post("/interaction/export")
async def interaction_export(flow_id: str = ""):
    data = _interaction_designer.export_to_json(flow_id)
    return {"export": data}

@router.post("/interaction/validate")
async def interaction_validate(flow_id: str = ""):
    valid, errors = _interaction_designer.validate_flow(flow_id)
    return {"valid": valid, "errors": errors}


# === Physics Tuner Endpoints ===

@router.get("/physics-tuner/stats")
async def physics_tuner_stats():
    return _physics_tuner.get_stats()

@router.post("/physics-tuner/create-preset")
async def physics_tuner_create_preset(name: str = "", preset_type: str = "realistic", quality_score: float = 0.8):
    from sparkai.agent.agent_physics_tuner import TunerPresetType
    preset = _physics_tuner.create_preset(name, TunerPresetType(preset_type), quality_score=quality_score)
    return preset.__dict__ if hasattr(preset, '__dict__') else str(preset)

@router.post("/physics-tuner/apply-preset")
async def physics_tuner_apply_preset(preset_id: str = "", entity_id: str = ""):
    result = _physics_tuner.apply_preset(preset_id, entity_id)
    return {"applied": result}

@router.post("/physics-tuner/analyze-entity")
async def physics_tuner_analyze_entity(entity_id: str = ""):
    result = _physics_tuner.analyze_entity(entity_id)
    return str(result)

@router.post("/physics-tuner/tune-gravity")
async def physics_tuner_tune_gravity(value: float = 980.0, domain: str = "platformer"):
    from sparkai.agent.agent_physics_tuner import PhysicsDomain
    result = _physics_tuner.tune_gravity(value, PhysicsDomain(domain))
    return str(result)

@router.post("/physics-tuner/tune-movement")
async def physics_tuner_tune_movement(domain: str = "platformer", speed: float = 300.0,
                                       acceleration: float = 1500.0, friction: float = 0.15):
    from sparkai.agent.agent_physics_tuner import PhysicsDomain
    result = _physics_tuner.tune_movement_feel(PhysicsDomain(domain), speed, acceleration, friction)
    return str(result)

@router.post("/physics-tuner/default-presets")
async def physics_tuner_default_presets():
    presets = _physics_tuner.generate_default_presets()
    return {"presets": [p.__dict__ for p in presets] if presets else []}

@router.post("/physics-tuner/compare")
async def physics_tuner_compare(preset_id_a: str = "", preset_id_b: str = ""):
    result = _physics_tuner.compare_presets(preset_id_a, preset_id_b)
    return str(result)


# === RAG Pipeline Endpoints ===

@router.get("/rag/stats")
async def rag_stats():
    return _rag_pipeline.get_stats()

@router.post("/rag/ingest")
async def rag_ingest(title: str = "", source: str = "", content: str = "",
                      domain: str = "game_design", tags: str = ""):
    from sparkai.agent.agent_rag_pipeline import RAGDomain
    tag_list = [t.strip() for t in tags.split(",") if t.strip()] if tags else []
    doc_id = _rag_pipeline.ingest_document(title, source, content, RAGDomain(domain), tag_list)
    return {"document_id": doc_id}

@router.post("/rag/search")
async def rag_search(query: str = "", domain: str = "", mode: str = "hybrid", top_k: int = 5):
    from sparkai.agent.agent_rag_pipeline import RAGDomain, SearchMode
    if mode == "keyword":
        results = _rag_pipeline.keyword_search(query, RAGDomain(domain) if domain else None, top_k)
    elif mode == "semantic":
        results = _rag_pipeline.semantic_search(query, RAGDomain(domain) if domain else None, top_k)
    else:
        results = _rag_pipeline.hybrid_search(query, RAGDomain(domain) if domain else None, top_k)
    return {"results": [r.__dict__ for r in results] if results else []}

@router.post("/rag/generate-context")
async def rag_generate_context(query: str = "", domain: str = "", max_tokens: int = 2000, top_k: int = 5):
    from sparkai.agent.agent_rag_pipeline import RAGDomain
    context = _rag_pipeline.generate_context(query, RAGDomain(domain) if domain else None, max_tokens, top_k)
    return {"context": context}

@router.post("/rag/augment-prompt")
async def rag_augment_prompt(base_prompt: str = "", query: str = "", domain: str = "", max_context_tokens: int = 1500):
    from sparkai.agent.agent_rag_pipeline import RAGDomain
    augmented = _rag_pipeline.augment_prompt(base_prompt, query, RAGDomain(domain) if domain else None, max_context_tokens)
    return {"augmented_prompt": augmented}


# === Tree of Thought Endpoints ===

@router.get("/thought/stats")
async def thought_stats():
    return _tree_of_thought.get_stats()

@router.post("/thought/create-session")
async def thought_create_session(problem: str = "", domain: str = "game_design",
                                   strategy: str = "best_first", max_depth: int = 5, max_branches: int = 8):
    from sparkai.agent.agent_tree_of_thought import ThoughtDomain, TraversalStrategy
    session = _tree_of_thought.create_session(problem, ThoughtDomain(domain),
                                               TraversalStrategy(strategy), max_depth, max_branches)
    return session.__dict__ if hasattr(session, '__dict__') else str(session)

@router.post("/thought/expand")
async def thought_expand(session_id: str = "", branch_id: str = "", thought: str = ""):
    node = _tree_of_thought.expand(session_id, branch_id, thought)
    return node.__dict__ if hasattr(node, '__dict__') else str(node)

@router.post("/thought/branch")
async def thought_branch(session_id: str = "", parent_node_id: str = "", thought: str = ""):
    branch = _tree_of_thought.branch(session_id, parent_node_id, thought)
    return branch.__dict__ if hasattr(branch, '__dict__') else str(branch)

@router.post("/thought/evaluate")
async def thought_evaluate(session_id: str = "", node_id: str = ""):
    score = _tree_of_thought.evaluate_node(session_id, node_id)
    return {"score": score}

@router.post("/thought/consistency")
async def thought_consistency(session_id: str = "", num_samples: int = 3):
    result = _tree_of_thought.self_consistency(session_id, num_samples)
    return str(result)

@router.post("/thought/best-path")
async def thought_best_path(session_id: str = ""):
    path = _tree_of_thought.select_best_path(session_id)
    return str(path)

@router.post("/thought/reasoning-trace")
async def thought_reasoning_trace(session_id: str = ""):
    trace = _tree_of_thought.get_reasoning_trace(session_id)
    return {"trace": trace}


# === Scene Tree Endpoints ===

@router.get("/scene-tree/stats")
async def scene_tree_stats():
    return _scene_tree.get_stats()

@router.post("/scene-tree/create")
async def scene_tree_create(name: str = "", description: str = ""):
    scene_id = _scene_tree.create_scene(name, description)
    return {"scene_id": scene_id}

@router.post("/scene-tree/add-node")
async def scene_tree_add_node(scene_id: str = "", parent_id: str = "",
                                name: str = "", node_type: str = "node2d", x: float = 0, y: float = 0):
    from sparkai.engine.scene_tree import NodeType
    node = _scene_tree.add_node(scene_id, parent_id, name, NodeType(node_type), x, y)
    return node.__dict__ if hasattr(node, '__dict__') else str(node)

@router.post("/scene-tree/remove-node")
async def scene_tree_remove_node(scene_id: str = "", node_id: str = ""):
    _scene_tree.remove_node(scene_id, node_id)
    return {"removed": True}

@router.get("/scene-tree/node-tree")
async def scene_tree_node_tree(scene_id: str = ""):
    tree = _scene_tree.get_node_tree(scene_id)
    return tree

@router.get("/scene-tree/stats-detail")
async def scene_tree_stats_detail(scene_id: str = ""):
    stats = _scene_tree.get_scene_stats(scene_id)
    return stats


# === Event System Endpoints ===

@router.get("/event-system/stats")
async def event_system_stats():
    return _event_system.get_stats()

@router.post("/event-system/create-sheet")
async def event_system_create_sheet(name: str = "", description: str = "", priority: int = 0):
    sheet = _event_system.create_sheet(name, description, priority)
    return sheet.__dict__ if hasattr(sheet, '__dict__') else str(sheet)

@router.post("/event-system/add-event")
async def event_system_add_event(sheet_id: str = "", conditions_json: str = "[]",
                                   actions_json: str = "[]", repeat_mode: str = "once"):
    import json
    from sparkai.engine.event_system import RepeatMode, EventCondition, EventAction
    conditions_raw = json.loads(conditions_json) if conditions_json else []
    actions_raw = json.loads(actions_json) if actions_json else []
    conditions = [EventCondition(**c) for c in conditions_raw]
    actions = [EventAction(**a) for a in actions_raw]
    event = _event_system.add_event(sheet_id, conditions, actions, RepeatMode(repeat_mode))
    return event.__dict__ if hasattr(event, '__dict__') else str(event)

@router.post("/event-system/evaluate-sheet")
async def event_system_evaluate_sheet(sheet_id: str = "", context_json: str = "{}"):
    import json
    context = json.loads(context_json) if context_json else {}
    results = _event_system.evaluate_sheet(sheet_id, context)
    return {"results": results}

@router.post("/event-system/connect-signal")
async def event_system_connect_signal(emitter_id: str = "", signal_name: str = "",
                                        receiver_id: str = "", slot_method: str = ""):
    signal = _event_system.connect_signal(emitter_id, signal_name, receiver_id, slot_method)
    return signal.__dict__ if hasattr(signal, '__dict__') else str(signal)

@router.post("/event-system/emit")
async def event_system_emit(emitter_id: str = "", signal_name: str = "", data_json: str = "{}"):
    import json
    data = json.loads(data_json) if data_json else {}
    results = _event_system.emit_signal(emitter_id, signal_name, data)
    return {"results": results}


# === Animation System Endpoints ===

@router.get("/animation/stats")
async def animation_stats():
    return _animation_system.get_stats()

@router.post("/animation/create-clip")
async def animation_create_clip(name: str = "", loop_mode: str = "once", playback_speed: float = 1.0):
    from sparkai.engine.animation_system import LoopMode
    clip = _animation_system.create_clip(name, LoopMode(loop_mode), playback_speed)
    return clip.__dict__ if hasattr(clip, '__dict__') else str(clip)

@router.post("/animation/add-track")
async def animation_add_track(clip_id: str = "", track_name: str = "",
                                target_node_id: str = "", property_path: str = "", track_type: str = "position"):
    from sparkai.engine.animation_system import TrackType
    track = _animation_system.add_track(clip_id, track_name, target_node_id, property_path, TrackType(track_type))
    return track.__dict__ if hasattr(track, '__dict__') else str(track)

@router.post("/animation/add-keyframe")
async def animation_add_keyframe(clip_id: str = "", track_id: str = "",
                                   time: float = 0.0, value: float = 0.0, easing: str = "linear"):
    from sparkai.engine.animation_system import EasingType
    kf = _animation_system.add_keyframe(clip_id, track_id, time, value, EasingType(easing))
    return kf.__dict__ if hasattr(kf, '__dict__') else str(kf)

@router.post("/animation/evaluate")
async def animation_evaluate(clip_id: str = "", time: float = 0.0):
    values = _animation_system.evaluate_clip(clip_id, time)
    return {"values": values}

@router.post("/animation/tween")
async def animation_tween(target_node_id: str = "", property_path: str = "",
                            start_value: float = 0.0, end_value: float = 100.0,
                            duration: float = 1.0, easing: str = "ease_out"):
    from sparkai.engine.animation_system import EasingType
    tween = _animation_system.start_tween(target_node_id, property_path, start_value,
                                            end_value, duration, EasingType(easing))
    return tween.__dict__ if hasattr(tween, '__dict__') else str(tween)


# === Pathfinding System Endpoints ===

@router.get("/pathfinding/stats")
async def pathfinding_stats():
    return _pathfinding_system.get_stats()

@router.post("/pathfinding/create-grid")
async def pathfinding_create_grid(name: str = "", width: int = 50, height: int = 50,
                                    cell_size: float = 1.0, origin_x: float = 0, origin_y: float = 0):
    grid_id = _pathfinding_system.create_grid(name, width, height, cell_size, origin_x, origin_y)
    return {"grid_id": grid_id}

@router.post("/pathfinding/set-cell")
async def pathfinding_set_cell(grid_id: str = "", x: int = 0, y: int = 0,
                                 is_walkable: bool = True, cost: float = 1.0):
    _pathfinding_system.set_cell(grid_id, x, y, is_walkable, cost)
    return {"updated": True}

@router.post("/pathfinding/find-path")
async def pathfinding_find_path(grid_id: str = "", start_x: int = 0, start_y: int = 0,
                                  end_x: int = 10, end_y: int = 10, heuristic: str = "manhattan"):
    from sparkai.engine.pathfinding_system import HeuristicMethod
    path = _pathfinding_system.find_path(grid_id, start_x, start_y, end_x, end_y, HeuristicMethod(heuristic))
    return path.__dict__ if hasattr(path, '__dict__') else str(path)

@router.post("/pathfinding/is-reachable")
async def pathfinding_is_reachable(grid_id: str = "", start_x: int = 0, start_y: int = 0,
                                     end_x: int = 10, end_y: int = 10):
    reachable = _pathfinding_system.is_reachable(grid_id, start_x, start_y, end_x, end_y)
    return {"reachable": reachable}

@router.post("/pathfinding/smooth")
async def pathfinding_smooth(path_id: str = "", method: str = "simple"):
    from sparkai.engine.pathfinding_system import SmoothingMethod
    result = _pathfinding_system.smooth_path(path_id, SmoothingMethod(method))
    return result.__dict__ if hasattr(result, '__dict__') else str(result)


# === Prompt Optimizer Endpoints ===

@router.get("/prompt-optimizer/stats")
async def prompt_optimizer_stats():
    return _prompt_optimizer.get_stats()

@router.post("/prompt-optimizer/create-template")
async def prompt_optimizer_create_template(name: str = "", domain: str = "",
                                             template_text: str = "",
                                             variables: str = "",
                                             system_prompt: str = "",
                                             temperature: float = 0.7,
                                             max_tokens: int = 2048):
    var_list = [v.strip() for v in variables.split(",") if v.strip()] if variables else []
    tmpl = _prompt_optimizer.create_template(name, domain, template_text, var_list,
                                              system_prompt, temperature, max_tokens)
    return tmpl.to_dict()

@router.get("/prompt-optimizer/get-template")
async def prompt_optimizer_get_template(template_id: str = ""):
    tmpl = _prompt_optimizer.get_template(template_id)
    return tmpl.to_dict() if tmpl else {"error": "not found"}

@router.get("/prompt-optimizer/list-templates")
async def prompt_optimizer_list_templates(domain: str = ""):
    templates = _prompt_optimizer.list_templates(domain or None)
    return {"templates": [t.to_dict() for t in templates]}

@router.post("/prompt-optimizer/fill-template")
async def prompt_optimizer_fill_template(template_id: str = "", variables: str = "{}"):
    import json as _json
    vars_dict = _json.loads(variables) if isinstance(variables, str) else variables
    filled = _prompt_optimizer.fill_template(template_id, vars_dict)
    return {"filled_prompt": filled}

@router.post("/prompt-optimizer/record-session")
async def prompt_optimizer_record_session(template_id: str = "",
                                            filled_prompt: str = "",
                                            response_text: str = "",
                                            quality_score: float = 0.0,
                                            latency_ms: float = 0.0,
                                            domain: str = "",
                                            tags: str = "",
                                            user_feedback: str = ""):
    tag_list = [t.strip() for t in tags.split(",") if t.strip()] if tags else []
    sid = _prompt_optimizer.record_session(template_id, filled_prompt, response_text,
                                             quality_score, latency_ms, domain,
                                             tag_list, user_feedback)
    return {"session_id": sid}

@router.get("/prompt-optimizer/get-best-template")
async def prompt_optimizer_get_best(domain: str = ""):
    tmpl = _prompt_optimizer.get_best_template(domain)
    return tmpl.to_dict() if tmpl else {"error": "not found"}

@router.get("/prompt-optimizer/domain-stats")
async def prompt_optimizer_domain_stats(domain: str = ""):
    return _prompt_optimizer.get_domain_stats(domain)

@router.post("/prompt-optimizer/add-rule")
async def prompt_optimizer_add_rule(rule_name: str = "", domain: str = "",
                                      condition_description: str = "",
                                      transformation: str = "",
                                      priority: int = 0):
    rule = _prompt_optimizer.add_rule(rule_name, domain, condition_description,
                                       transformation, priority)
    return {"rule": rule.to_dict()}

@router.get("/prompt-optimizer/list-rules")
async def prompt_optimizer_list_rules(domain: str = ""):
    rules = _prompt_optimizer.list_rules(domain or None)
    return {"rules": [r.to_dict() for r in rules]}

@router.post("/prompt-optimizer/optimize-template")
async def prompt_optimizer_optimize_template(template_id: str = ""):
    result = _prompt_optimizer.optimize_template(template_id)
    return result

@router.post("/prompt-optimizer/export-template")
async def prompt_optimizer_export_template(template_id: str = ""):
    data = _prompt_optimizer.export_template(template_id)
    return {"data": data} if data else {"error": "not found"}

@router.post("/prompt-optimizer/import-template")
async def prompt_optimizer_import_template(data: str = "{}"):
    import json as _json
    parsed = _json.loads(data) if isinstance(data, str) else data
    tmpl = _prompt_optimizer.import_template(parsed)
    return tmpl.to_dict()


# === Skill Composer Endpoints ===

@router.get("/skill-composer/stats")
async def skill_composer_stats():
    return _skill_composer.get_stats()

@router.post("/skill-composer/create-chain")
async def skill_composer_create_chain(name: str = "", description: str = "",
                                       domain: str = "game_generation",
                                       is_parallel: bool = False):
    from sparkai.agent.agent_skill_composer import SkillDomain
    chain = _skill_composer.create_chain(name, description, SkillDomain(domain), is_parallel)
    return chain.to_dict()

@router.get("/skill-composer/get-chain")
async def skill_composer_get_chain(chain_id: str = ""):
    chain = _skill_composer.get_chain(chain_id)
    return chain.to_dict() if chain else {"error": "not found"}

@router.get("/skill-composer/list-chains")
async def skill_composer_list_chains():
    return {"chains": _skill_composer.list_chains()}

@router.post("/skill-composer/add-step")
async def skill_composer_add_step(chain_id: str = "", step_name: str = "",
                                    skill_type: str = "", agent_name: str = "",
                                    parameters: str = "{}",
                                    input_spec: str = "{}",
                                    output_spec: str = "{}",
                                    timeout_seconds: int = 60,
                                    retry_count: int = 0):
    import json as _json
    params = _json.loads(parameters) if isinstance(parameters, str) else parameters
    in_spec = _json.loads(input_spec) if isinstance(input_spec, str) else input_spec
    out_spec = _json.loads(output_spec) if isinstance(output_spec, str) else output_spec
    sid = _skill_composer.add_step(chain_id, step_name, skill_type, agent_name,
                                     params, in_spec, out_spec, timeout_seconds, retry_count)
    return {"step_id": sid}

@router.post("/skill-composer/remove-step")
async def skill_composer_remove_step(chain_id: str = "", step_index: int = 0):
    removed = _skill_composer.remove_step(chain_id, step_index)
    return {"removed": removed}

@router.post("/skill-composer/execute-chain")
async def skill_composer_execute_chain(chain_id: str = ""):
    result = _skill_composer.execute_chain(chain_id)
    return {"result": result}

@router.get("/skill-composer/get-execution-log")
async def skill_composer_get_log(chain_id: str = ""):
    log = _skill_composer.get_execution_log(chain_id or None)
    return {"log": log}

@router.get("/skill-composer/chain-progress")
async def skill_composer_chain_progress(chain_id: str = ""):
    progress = _skill_composer.get_chain_progress(chain_id)
    if progress:
        total, done, pct = progress
        return {"total_steps": total, "done_steps": done, "percent": pct}
    return {"error": "not found"}

@router.post("/skill-composer/cancel-chain")
async def skill_composer_cancel_chain(chain_id: str = ""):
    cancelled = _skill_composer.cancel_chain(chain_id)
    return {"cancelled": cancelled}

@router.post("/skill-composer/create-template")
async def skill_composer_create_template(name: str = "", description: str = "",
                                           domain: str = "game_generation",
                                           chain_id: str = ""):
    from sparkai.agent.agent_skill_composer import SkillDomain
    tid = _skill_composer.create_template(name, description, SkillDomain(domain), chain_id)
    return {"template_id": tid}

@router.get("/skill-composer/list-templates")
async def skill_composer_list_templates(domain: str = ""):
    from sparkai.agent.agent_skill_composer import SkillDomain
    if domain:
        templates = _skill_composer.get_templates_by_domain(SkillDomain(domain))
        return {"templates": [t.to_dict() for t in templates]}
    return {"templates": _skill_composer.list_templates()}

@router.get("/skill-composer/get-template")
async def skill_composer_get_template(template_id: str = ""):
    tmpl = _skill_composer.get_template(template_id)
    return tmpl.to_dict() if tmpl else {"error": "not found"}

@router.post("/skill-composer/instantiate-template")
async def skill_composer_instantiate_template(template_id: str = "", name: str = ""):
    cid = _skill_composer.instantiate_template(template_id, name)
    return {"chain_id": cid}


# === UI Layout System Endpoints ===

@router.get("/ui-layout/stats")
async def ui_layout_stats():
    return _ui_layout_system.get_stats()

@router.post("/ui-layout/create")
async def ui_layout_create(name: str = "", theme_name: str = "default"):
    lid = _ui_layout_system.create_layout(name, theme_name)
    return {"layout_id": lid}

@router.post("/ui-layout/add-container")
async def ui_layout_add_container(layout_id: str = "", parent_id: str = "",
                                    container_type: str = "box",
                                    name: str = "",
                                    x: float = 0.0, y: float = 0.0,
                                    width: float = 100.0, height: float = 100.0):
    from sparkai.engine.ui_layout_system import ContainerType
    cid = _ui_layout_system.add_container(
        layout_id, parent_id, name, ContainerType(container_type),
        x, y, width, height,
    )
    return {"container_id": cid}

@router.post("/ui-layout/remove-container")
async def ui_layout_remove_container(layout_id: str = "", container_id: str = ""):
    removed = _ui_layout_system.remove_container(layout_id, container_id)
    return {"removed": removed}

@router.post("/ui-layout/set-anchor")
async def ui_layout_set_anchor(layout_id: str = "", container_id: str = "",
                                 anchor_mode: str = "full_rect",
                                 margin_left: float = 0.0, margin_top: float = 0.0,
                                 margin_right: float = 0.0, margin_bottom: float = 0.0):
    from sparkai.engine.ui_layout_system import AnchorMode
    aid = _ui_layout_system.set_anchor(layout_id, container_id,
                                         AnchorMode(anchor_mode),
                                         (margin_left, margin_top, margin_right, margin_bottom))
    return {"anchor_id": aid if aid else None}

@router.get("/ui-layout/get-container-chain")
async def ui_layout_get_chain(layout_id: str = "", container_id: str = ""):
    chain = _ui_layout_system.get_container_chain(layout_id, container_id)
    return {"chain": chain.to_dict() if chain else None}

@router.post("/ui-layout/arrange-children")
async def ui_layout_arrange(layout_id: str = "", container_id: str = ""):
    arranged = _ui_layout_system.arrange_children(layout_id, container_id)
    return {"arranged": arranged}

@router.post("/ui-layout/export")
async def ui_layout_export(layout_id: str = ""):
    data = _ui_layout_system.export_layout(layout_id)
    return {"data": data} if data else {"error": "not found"}

@router.post("/ui-layout/import")
async def ui_layout_import(data: str = "{}"):
    import json as _json
    parsed = _json.loads(data) if isinstance(data, str) else data
    lid = _ui_layout_system.import_layout(parsed)
    return {"layout_id": lid}


# === Performance Overlay Endpoints ===

@router.get("/performance-overlay/stats")
async def performance_overlay_stats():
    return _performance_overlay.get_stats()

@router.post("/performance-overlay/record-frame")
async def performance_overlay_record(delta_time: float = 16.67,
                                       draw_calls: int = 100,
                                       triangle_count: int = 5000,
                                       memory_used_mb: float = 120.0,
                                       cpu_time_ms: float = 8.0,
                                       gpu_time_ms: float = 4.0,
                                       physics_time_ms: float = 2.0,
                                       script_time_ms: float = 1.0,
                                       object_count: int = 200):
    sample = _performance_overlay.record_frame(delta_time, draw_calls,
                                                  triangle_count, memory_used_mb,
                                                  cpu_time_ms, gpu_time_ms,
                                                  physics_time_ms, script_time_ms,
                                                  object_count)
    return {"sample": sample.to_dict()}

@router.get("/performance-overlay/current-fps")
async def performance_overlay_fps():
    return {"fps": _performance_overlay.get_current_fps()}

@router.get("/performance-overlay/frame-time-stats")
async def performance_overlay_frame_times():
    return _performance_overlay.get_frame_time_stats()

@router.get("/performance-overlay/memory-usage")
async def performance_overlay_memory():
    return _performance_overlay.get_memory_usage()

@router.get("/performance-overlay/metric-summary")
async def performance_overlay_summary(section: str = "all"):
    from sparkai.engine.performance_overlay import OverlaySection
    return _performance_overlay.get_metric_summary(OverlaySection(section))

@router.post("/performance-overlay/set-threshold")
async def performance_overlay_set_threshold(metric_name: str = "",
                                               warning_threshold: float = 0.0,
                                               error_threshold: float = 0.0,
                                               is_enabled: bool = True):
    _performance_overlay.set_threshold(metric_name, warning_threshold,
                                        error_threshold, is_enabled)
    return {"set": True}

@router.get("/performance-overlay/check")
async def performance_overlay_check():
    alerts = _performance_overlay.check_thresholds()
    return {"alerts": alerts}

@router.get("/performance-overlay/generate-text")
async def performance_overlay_text(sections: str = "fps,memory"):
    from sparkai.engine.performance_overlay import OverlaySection
    sec_list = [OverlaySection(s.strip()) for s in sections.split(",") if s.strip()]
    text = _performance_overlay.generate_overlay_text(sec_list)
    return {"overlay_text": text}

@router.post("/performance-overlay/start-snapshot")
async def performance_overlay_start_snapshot(name: str = ""):
    sid = _performance_overlay.start_snapshot(name)
    return {"snapshot_id": sid}

@router.post("/performance-overlay/stop-snapshot")
async def performance_overlay_stop_snapshot():
    snap = _performance_overlay.stop_snapshot()
    return snap.to_dict() if hasattr(snap, 'to_dict') else {"snapshot": str(snap)} if snap else {"error": "no snapshot active"}

@router.get("/performance-overlay/recent-snapshots")
async def performance_overlay_snapshots(limit: int = 10):
    snaps = _performance_overlay.get_recent_snapshots(limit)
    return {"snapshots": [s.to_dict() if hasattr(s, 'to_dict') else str(s) for s in snaps]}

@router.post("/performance-overlay/reset")
async def performance_overlay_reset():
    _performance_overlay.reset_metrics()
    return {"reset": True}


# === Developer Assistant Endpoints ===

@router.get("/developer-assistant/stats")
async def developer_assistant_stats():
    return _developer_assistant.get_stats()

@router.post("/developer-assistant/start-session")
async def developer_assistant_start(name: str = "", focus: str = "game_logic"):
    session = _developer_assistant.start_session(name, focus)
    return session.to_dict()

@router.post("/developer-assistant/update-context")
async def developer_assistant_update_context(session_id: str = "", file: str = "",
                                                line: int = 0, col: int = 0,
                                                nodes: str = ""):
    node_list = [n.strip() for n in nodes.split(",") if n.strip()] if nodes else []
    _developer_assistant.update_context(session_id, file, line, col, node_list)
    return {"updated": True}

@router.post("/developer-assistant/get-suggestions")
async def developer_assistant_get_suggestions(session_id: str = "",
                                                 mode: str = "code_suggestion",
                                                 max_count: int = 5):
    try:
        mode_type = AssistantMode(mode.lower())
    except ValueError:
        mode_type = AssistantMode.CODE_SUGGESTION
    suggestions = _developer_assistant.get_suggestions(session_id, mode_type, max_count)
    return {"suggestions": [s.to_dict() for s in suggestions]}

@router.post("/developer-assistant/diagnose")
async def developer_assistant_diagnose(session_id: str = "",
                                          error_message: str = "",
                                          code_context: str = ""):
    diagnosis = _developer_assistant.diagnose_error(session_id, error_message, code_context)
    return diagnosis.to_dict()

@router.post("/developer-assistant/optimization-advice")
async def developer_assistant_advice(target_system: str = "", code: str = ""):
    advice = _developer_assistant.get_optimization_advice(target_system, code)
    return advice.to_dict() if advice else {"error": "no advice"}

@router.post("/developer-assistant/accept-suggestion")
async def developer_assistant_accept(id: str = ""):
    _developer_assistant.accept_suggestion(id)
    return {"accepted": True}

@router.post("/developer-assistant/record-error")
async def developer_assistant_record_error(session_id: str = "",
                                              error_message: str = "",
                                              code_context: str = ""):
    _developer_assistant.record_error(session_id, error_message, code_context)
    return {"recorded": True}


# === Scene Streamer Endpoints ===

@router.get("/scene-streamer/stats")
async def scene_streamer_stats():
    return _scene_streamer.get_stats()

@router.post("/scene-streamer/create-world")
async def scene_streamer_create_world(world_id: str = "", chunk_size: int = 256):
    config = _scene_streamer.create_world(world_id, chunk_size)
    return config.to_dict()

@router.post("/scene-streamer/add-chunk")
async def scene_streamer_add_chunk(world_id: str = "", grid_x: int = 0,
                                      grid_y: int = 0, grid_z: int = 0,
                                      priority: int = 5):
    chunk = _scene_streamer.add_chunk(world_id, grid_x, grid_y, grid_z, priority)
    return chunk.to_dict() if chunk else {"error": "failed"}

@router.post("/scene-streamer/update-camera")
async def scene_streamer_update_camera(camera_id: str = "", world_id: str = "",
                                          pos_x: float = 0, pos_y: float = 0,
                                          pos_z: float = 0,
                                          fwd_x: float = 1, fwd_y: float = 0,
                                          fwd_z: float = 0, speed: float = 10):
    _scene_streamer.update_camera(camera_id, world_id,
                                    (pos_x, pos_y, pos_z),
                                    (fwd_x, fwd_y, fwd_z), speed)
    return {"updated": True}

@router.post("/scene-streamer/tick")
async def scene_streamer_tick(delta_time: float = 0.016):
    result = _scene_streamer.tick(delta_time)
    return result

@router.get("/scene-streamer/loaded-chunks")
async def scene_streamer_loaded(world_id: str = ""):
    chunks = _scene_streamer.get_loaded_chunks(world_id)
    return {"chunks": [c.to_dict() for c in chunks]}

@router.get("/scene-streamer/chunks-in-radius")
async def scene_streamer_radius(world_id: str = "", x: float = 0, y: float = 0,
                                   z: float = 0, radius: float = 500):
    chunks = _scene_streamer.get_chunks_in_radius(world_id, (x, y, z), radius)
    return {"chunks": [c.to_dict() for c in chunks]}

@router.get("/scene-streamer/predict-preload")
async def scene_streamer_predict(world_id: str = "", camera_id: str = ""):
    chunks = _scene_streamer.predict_preload_chunks(world_id, camera_id)
    return {"chunks": [c.to_dict() for c in chunks]}

@router.get("/scene-streamer/streaming-stats")
async def scene_streamer_world_stats(world_id: str = ""):
    return _scene_streamer.get_streaming_stats(world_id)


# === Project Exporter Endpoints ===

@router.get("/project-exporter/stats")
async def project_exporter_stats():
    return _project_exporter.get_stats()

@router.post("/project-exporter/create-config")
async def project_exporter_create_config(
        project_name: str = "", platform: str = "web",
        resolution_width: int = 1920, resolution_height: int = 1080,
        fullscreen: str = "False", compression_level: int = 6,
        include_debug_symbols: str = "False",
        bundle_id: str = "com.sparklabs.game", version_string: str = "1.0.0"):
    try:
        target = ExportPlatform(platform.lower())
    except ValueError:
        target = ExportPlatform.WEB
    config = _project_exporter.create_config(
        project_name=project_name,
        platform=target,
        resolution_width=resolution_width,
        resolution_height=resolution_height,
        fullscreen=fullscreen == "True",
        compression_level=compression_level,
        include_debug_symbols=include_debug_symbols == "True",
        bundle_id=bundle_id,
        version_string=version_string,
    )
    return config.to_dict()

@router.post("/project-exporter/start-export")
async def project_exporter_start(config_id: str = ""):
    job = _project_exporter.start_export(config_id)
    return job.to_dict()

@router.get("/project-exporter/status")
async def project_exporter_status(job_id: str = ""):
    job = _project_exporter.get_job_status(job_id)
    return job.to_dict() if job else {"error": "not found"}

@router.get("/project-exporter/history")
async def project_exporter_history():
    jobs = _project_exporter.get_export_history()
    return [j.to_dict() for j in jobs]

@router.post("/project-exporter/cancel")
async def project_exporter_cancel(job_id: str = ""):
    cancelled = _project_exporter.cancel_export(job_id)
    return {"cancelled": cancelled}

@router.post("/project-exporter/validate")
async def project_exporter_validate(config_id: str = ""):
    result = _project_exporter.validate_project(config_id)
    return result

@router.post("/project-exporter/estimate-size")
async def project_exporter_estimate(config_id: str = ""):
    result = _project_exporter.estimate_export_size(config_id)
    if isinstance(result, tuple) and len(result) == 2:
        return {"total_mb": result[0], "breakdown": result[1]}
    return {"result": str(result)}

@router.get("/project-exporter/presets")
async def project_exporter_presets():
    presets = _project_exporter.get_presets()
    return {"presets": [p.to_dict() for p in presets]}


# === Game Director Endpoints ===

@router.get("/game-director/stats")
async def game_director_stats():
    return _game_director.get_stats()

@router.get("/game-director/briefs")
async def game_director_briefs():
    return {"briefs": [b.to_dict() for b in _game_director.list_briefs()]}

@router.post("/game-director/create-brief")
async def game_director_create_brief(project_name: str = "", genre: str = "",
                                       art_style: str = "", tone: str = "",
                                       core_pillars: str = "",
                                       target_audience: str = "",
                                       scope: str = ""):
    pillars = [p.strip() for p in core_pillars.split(",") if p.strip()]
    brief = _game_director.create_brief(project_name, genre, art_style, tone,
                                          pillars, target_audience, scope)
    return brief.to_dict()

@router.get("/game-director/brief")
async def game_director_get_brief(brief_id: str = ""):
    brief = _game_director.get_brief(brief_id)
    return brief.to_dict() if brief else {"error": "not found"}

@router.post("/game-director/propose-decision")
async def game_director_propose_decision(brief_id: str = "", title: str = "",
                                            description: str = "", role: str = "",
                                            severity: str = "medium"):
    decision = _game_director.propose_decision(brief_id, title, description, role, severity)
    return decision.to_dict() if decision else {"error": "brief not found"}

@router.get("/game-director/decisions")
async def game_director_decisions(brief_id: str = ""):
    return {"decisions": [d.to_dict() for d in _game_director.get_decisions(brief_id)]}

@router.post("/game-director/delegate-task")
async def game_director_delegate_task(brief_id: str = "", agent_name: str = "",
                                         description: str = "", priority: int = 1):
    task = _game_director.delegate_task(brief_id, agent_name, description, priority)
    return task.to_dict() if task else {"error": "brief not found"}

@router.get("/game-director/tasks")
async def game_director_tasks(brief_id: str = ""):
    return {"tasks": [t.to_dict() for t in _game_director.get_tasks(brief_id)]}

@router.get("/game-director/progress")
async def game_director_progress(brief_id: str = ""):
    return _game_director.get_progress_summary(brief_id)


# === Balance Analyzer Endpoints ===

@router.get("/balance-analyzer/stats")
async def balance_analyzer_stats():
    return _balance_analyzer.get_stats()

@router.post("/balance-analyzer/analyze")
async def balance_analyzer_analyze(game_id: str = "", domains: str = ""):
    domain_list = [d.strip() for d in domains.split(",") if d.strip()]
    return {"analyses": [a.to_dict() for a in _balance_analyzer.analyze_game(game_id, domain_list)]}

@router.get("/balance-analyzer/analyses")
async def balance_analyzer_analyses(game_id: str = ""):
    return {"analyses": [a.to_dict() for a in _balance_analyzer.get_analyses(game_id)]}

@router.get("/balance-analyzer/issues-summary")
async def balance_analyzer_issues_summary(game_id: str = ""):
    return _balance_analyzer.get_issues_summary(game_id)

@router.post("/balance-analyzer/analyze-parameter")
async def balance_analyzer_analyze_param(name: str = "", current_value: float = 0.0,
                                            domain: str = "", target_min: float = 0.0,
                                            target_max: float = 100.0, unit: str = ""):
    metric = _balance_analyzer.analyze_parameter(name, current_value, domain,
                                                    target_min, target_max, unit)
    return metric.to_dict()

@router.post("/balance-analyzer/apply-recommendation")
async def balance_analyzer_apply(recommendation_id: str = ""):
    applied = _balance_analyzer.apply_recommendation(recommendation_id)
    return {"applied": applied}

@router.post("/balance-analyzer/compare-games")
async def balance_analyzer_compare(game_id_a: str = "", game_id_b: str = ""):
    comparison = _balance_analyzer.compare_games(game_id_a, game_id_b)
    return comparison

@router.get("/balance-analyzer/applied-recommendations")
async def balance_analyzer_applied_recommendations():
    return {"recommendations": [r.to_dict() for r in _balance_analyzer.get_applied_recommendations()]}


# === Narrative Composer Endpoints ===

@router.get("/narrative-composer/stats")
async def narrative_composer_stats():
    return _narrative_composer.get_stats()

@router.post("/narrative-composer/create-story")
async def narrative_composer_create_story(title: str = "", genre: str = "",
                                            tone: str = "", synopsis: str = "",
                                            structure: str = "",
                                            target_playtime: str = ""):
    story = _narrative_composer.create_story(title, genre, tone, synopsis,
                                               structure, target_playtime)
    return story.to_dict()

@router.get("/narrative-composer/stories")
async def narrative_composer_stories():
    return {"stories": [s.to_dict() for s in _narrative_composer.list_stories()]}

@router.post("/narrative-composer/add-plot-beat")
async def narrative_composer_add_plot_beat(story_id: str = "", title: str = "",
                                              act_number: int = 1,
                                              description: str = ""):
    beat = _narrative_composer.add_plot_beat(story_id, title, act_number, description)
    return beat.to_dict() if beat else {"error": "story not found"}

@router.post("/narrative-composer/create-character")
async def narrative_composer_create_character(story_id: str = "", name: str = "",
                                                 role: str = "", archetype: str = "",
                                                 motivation: str = "",
                                                 backstory: str = ""):
    character = _narrative_composer.create_character(story_id, name, role,
                                                       archetype, motivation,
                                                       backstory)
    return character.to_dict() if character else {"error": "story not found"}

@router.post("/narrative-composer/build-dialogue-tree")
async def narrative_composer_build_dialogue(story_id: str = "",
                                               character_id: str = "",
                                               opening_line: str = "",
                                               tone: str = ""):
    nodes = _narrative_composer.build_dialogue_tree(story_id, character_id,
                                                      opening_line, tone)
    return {"nodes": [n.to_dict() for n in nodes]}

@router.get("/narrative-composer/export-story")
async def narrative_composer_export_story(story_id: str = ""):
    return _narrative_composer.export_story(story_id)


# === Player Modeler Endpoints ===

@router.get("/player-modeler/stats")
async def player_modeler_stats():
    return _player_modeler.get_stats()

@router.post("/player-modeler/create-persona")
async def player_modeler_create_persona(name: str = "", archetype: str = ""):
    persona = _player_modeler.create_persona(name, archetype)
    return persona.to_dict()

@router.post("/player-modeler/seed-all-archetypes")
async def player_modeler_seed_all():
    return {"personas": [p.to_dict() for p in _player_modeler.seed_all_archetypes()]}

@router.post("/player-modeler/simulate-journey")
async def player_modeler_simulate_journey(persona_id: str = "", game_id: str = "",
                                            max_sessions: int = 10):
    journey = _player_modeler.simulate_journey(persona_id, game_id, max_sessions)
    return journey.to_dict() if journey else {"error": "persona not found"}

@router.get("/player-modeler/report")
async def player_modeler_report(game_id: str = ""):
    report = _player_modeler.generate_report(game_id)
    return report.to_dict() if report else {"error": "no data for this game"}

@router.get("/player-modeler/compare-archetypes")
async def player_modeler_compare_archetypes(game_id: str = ""):
    return _player_modeler.compare_archetypes(game_id)


# === Audio System Endpoints ===

@router.get("/audio-system/stats")
async def audio_system_stats():
    return _audio_system.get_stats()

@router.post("/audio-system/register-asset")
async def audio_system_register_asset(name: str = "", category: str = "",
                                        duration: float = 0.0):
    asset = _audio_system.register_asset(name, category, duration)
    return asset.to_dict()

@router.get("/audio-system/mixer-state")
async def audio_system_mixer_state():
    return _audio_system.get_mixer_state()


# === Network Layer Endpoints ===

@router.get("/network-layer/stats")
async def network_layer_stats():
    return _network_layer.get_stats()

@router.post("/network-layer/host-game")
async def network_layer_host_game(mode: str = "", display_name: str = ""):
    return _network_layer.host_game(mode, display_name)

@router.post("/network-layer/create-lobby")
async def network_layer_create_lobby(name: str = "", max_players: int = 4):
    lobby = _network_layer.create_lobby(name, max_players)
    return lobby.to_dict()


# === Node Tree Endpoints ===

@router.get("/node-tree/stats")
async def node_tree_stats():
    return _node_tree.get_stats()

@router.post("/node-tree/create-node")
async def node_tree_create_node(name: str = "", parent_id: str = "", node_type: str = "spatial"):
    node = _node_tree.create_node(name=name, node_type=node_type, parent_id=parent_id)
    if node:
        return node.to_dict()
    return {"error": "Node creation failed"}

@router.post("/node-tree/remove-node")
async def node_tree_remove_node(node_id: str = ""):
    return {"removed": _node_tree.remove_node(node_id=node_id)}

@router.post("/node-tree/set-parent")
async def node_tree_set_parent(node_id: str = "", parent_id: str = ""):
    return {"success": _node_tree.set_parent(node_id=node_id, new_parent_id=parent_id)}

@router.get("/node-tree/get-node")
async def node_tree_get_node(node_id: str = ""):
    node = _node_tree.get_node(node_id=node_id)
    if node:
        return node.to_dict()
    return {"error": "Node not found"}

@router.get("/node-tree/get-children")
async def node_tree_get_children(node_id: str = ""):
    children = _node_tree.get_children(node_id=node_id)
    return {"children": [c.to_dict() for c in children]}

@router.get("/node-tree/root-nodes")
async def node_tree_root_nodes():
    roots = _node_tree.get_root_nodes()
    return {"roots": [r.to_dict() for r in roots]}

@router.get("/node-tree/traverse")
async def node_tree_traverse(node_id: str = "", order: str = "pre_order"):
    nodes = _node_tree.traverse(node_id=node_id, order=order)
    if nodes:
        return {"nodes": [n.to_dict() for n in nodes]}
    return {"error": "Traversal failed"}

@router.post("/node-tree/update-transform")
async def node_tree_update_transform(node_id: str = "", position_x: float = 0.0, position_y: float = 0.0,
                                       position_z: float = 0.0, scale_x: float = 1.0, scale_y: float = 1.0,
                                       scale_z: float = 1.0, rotation: float = 0.0):
    transform = _node_tree.update_transform(node_id=node_id,
                                              position={"x": position_x, "y": position_y, "z": position_z},
                                              scale={"x": scale_x, "y": scale_y, "z": scale_z},
                                              rotation=rotation)
    if transform:
        return transform.to_dict()
    return {"error": "Node not found"}

@router.post("/node-tree/connect-signal")
async def node_tree_connect_signal(source_id: str = "", signal_name: str = "", target_id: str = ""):
    result = _node_tree.connect_signal(source_id=source_id, signal_name=signal_name, target_id=target_id)
    if result:
        return {"connected": result.id}
    return {"error": "Connection failed"}

@router.post("/node-tree/emit-signal")
async def node_tree_emit_signal(node_id: str = "", signal_name: str = "", payload: str = ""):
    data = {"payload": payload} if payload else None
    emitted = _node_tree.emit_signal(source_id=node_id, signal_name=signal_name, data=data)
    return {"emitted": emitted}

@router.post("/node-tree/disconnect-signal")
async def node_tree_disconnect_signal(connection_id: str = ""):
    return {"disconnected": _node_tree.disconnect_signal(connection_id=connection_id)}

@router.post("/node-tree/set-lifecycle")
async def node_tree_set_lifecycle(node_id: str = "", state: str = "active"):
    return {"success": _node_tree.set_lifecycle(node_id=node_id, state=state)}

@router.get("/node-tree/export-scene")
async def node_tree_export_scene(root_id: str = ""):
    scene = _node_tree.export_scene(root_id=root_id)
    if scene:
        return scene.to_dict() if hasattr(scene, 'to_dict') else scene
    return {"error": "Export failed"}

@router.post("/node-tree/import-scene")
async def node_tree_import_scene(data: str = ""):
    try:
        import json as _json
        raw = _json.loads(data)
        definition = SceneDefinition(
            name=raw.get("name", ""),
            nodes=raw.get("nodes", {}),
            roots=raw.get("roots", []),
            metadata=raw.get("metadata", {}),
        )
    except Exception:
        return {"error": "Invalid scene data"}
    result = _node_tree.import_scene(definition=definition)
    if result:
        return result.to_dict()
    return {"error": "Import failed"}


# === Extension Registry Endpoints ===

@router.get("/extension-registry/stats")
async def extension_registry_stats():
    return _extension_registry.get_stats()

@router.post("/extension-registry/publish-extension")
async def extension_registry_publish_extension(name: str = "", version: str = "1.0.0", author: str = "",
                                                 description: str = "", tags: str = ""):
    definition = ExtensionDefinition(name=name, display_name=name, description=description)
    version_obj = ExtensionVersion(version=version)
    tag_list = [t.strip() for t in tags.split(",") if t.strip()] if tags else []
    ext = _extension_registry.publish_extension(definition=definition, version=version_obj, author_id=author, tags=tag_list, dependencies=[])
    if ext:
        return ext.to_dict()
    return {"error": "Extension publish failed"}

@router.post("/extension-registry/install-extension")
async def extension_registry_install_extension(extension_id: str = ""):
    installed = _extension_registry.install_extension(extension_id=extension_id)
    if installed:
        return {"installed": installed.to_dict()}
    return {"error": "Installation failed"}

@router.post("/extension-registry/uninstall-extension")
async def extension_registry_uninstall_extension(extension_id: str = ""):
    return {"uninstalled": _extension_registry.uninstall_extension(extension_id=extension_id)}

@router.post("/extension-registry/register-behavior")
async def extension_registry_register_behavior(extension_id: str = "", name: str = "", description: str = "",
                                                 script_template: str = "", parameters: str = "[]"):
    try:
        import json as _json
        params = _json.loads(parameters)
    except Exception:
        params = []
    behavior = _extension_registry.register_behavior(extension_id=extension_id, name=name, description=description, parameters=params, script_template=script_template)
    if behavior:
        return behavior.to_dict()
    return {"error": "Behavior registration failed"}

@router.post("/extension-registry/register-object-type")
async def extension_registry_register_object_type(extension_id: str = "", name: str = "", description: str = "",
                                                    base_type: str = "node", properties: str = "[]",
                                                    default_behavior: str = ""):
    try:
        import json as _json
        props = _json.loads(properties)
    except Exception:
        props = []
    obj = _extension_registry.register_object_type(extension_id=extension_id, name=name, description=description, base_type=base_type, properties=props, default_behavior=default_behavior)
    if obj:
        return obj.to_dict()
    return {"error": "Object type registration failed"}

@router.get("/extension-registry/resolve-dependencies")
async def extension_registry_resolve_dependencies(extension_id: str = ""):
    deps = _extension_registry.resolve_dependencies(extension_id=extension_id)
    return {"dependencies": [d.to_dict() for d in deps]}

@router.get("/extension-registry/check-compatibility")
async def extension_registry_check_compatibility(extension_id: str = "", engine_version: str = ""):
    result = _extension_registry.check_compatibility(extension_id=extension_id, engine_version=engine_version)
    return {"compatibility": result.value if hasattr(result, 'value') else str(result)}

@router.get("/extension-registry/search-extensions")
async def extension_registry_search_extensions(query: str = "", extension_type: str = "", tags: str = ""):
    tag_list = [t.strip() for t in tags.split(",") if t.strip()] if tags else None
    results = _extension_registry.search_extensions(query=query, extension_type=extension_type or None, tags=tag_list)
    return {"results": [r.to_dict() for r in results]}

@router.get("/extension-registry/installed-extensions")
async def extension_registry_installed_extensions():
    extensions = _extension_registry.get_installed_extensions()
    return {"extensions": [e.to_dict() for e in extensions]}

@router.post("/extension-registry/update-extension")
async def extension_registry_update_extension(extension_id: str = "", version: str = ""):
    updated = _extension_registry.update_extension(extension_id=extension_id, to_version=version)
    if updated:
        return updated.to_dict()
    return {"error": "Extension not found"}


# === Export Pipeline Endpoints ===

@router.get("/export-pipeline/stats")
async def export_pipeline_stats():
    return _export_pipeline.get_stats()

@router.post("/export-pipeline/create-profile")
async def export_pipeline_create_profile(name: str = "", platform: str = "web", quality: str = "high"):
    target_map = {
        "web": ExportTarget.WEB_HTML5, "html5": ExportTarget.WEB_HTML5, "wasm": ExportTarget.WEB_WASM,
        "windows": ExportTarget.DESKTOP_WINDOWS, "win": ExportTarget.DESKTOP_WINDOWS,
        "macos": ExportTarget.DESKTOP_MACOS, "mac": ExportTarget.DESKTOP_MACOS,
        "linux": ExportTarget.DESKTOP_LINUX,
        "ios": ExportTarget.MOBILE_IOS, "android": ExportTarget.MOBILE_ANDROID,
        "switch": ExportTarget.CONSOLE_SWITCH,
    }
    target = target_map.get(platform.lower(), ExportTarget.WEB_HTML5)
    settings = {"quality": quality} if quality else None
    profile = _export_pipeline.create_profile(name=name, target=target, settings=settings, resolution=None)
    if profile:
        return profile.to_dict()
    return {"error": "Profile creation failed"}

@router.post("/export-pipeline/start-export")
async def export_pipeline_start_export(profile_id: str = "", target_path: str = ""):
    job = _export_pipeline.start_export(profile_id=profile_id, scene_ids=None, output_path=target_path)
    if job:
        return job.to_dict()
    return {"error": "Export start failed"}

@router.post("/export-pipeline/cancel-export")
async def export_pipeline_cancel_export(job_id: str = ""):
    return {"cancelled": _export_pipeline.cancel_export(job_id=job_id)}

@router.post("/export-pipeline/optimize-asset")
async def export_pipeline_optimize_asset(asset_path: str = "", format: str = "auto"):
    results = _export_pipeline.optimize_asset(asset_id=asset_path, target_formats=None, quality_level=3)
    if results:
        return {"optimizations": [r.to_dict() for r in results]}
    return {"error": "Optimization failed"}

@router.get("/export-pipeline/job-status")
async def export_pipeline_job_status(job_id: str = ""):
    status = _export_pipeline.get_job_status(job_id=job_id)
    if status:
        return status.to_dict()
    return {"error": "Job not found"}

@router.get("/export-pipeline/export-history")
async def export_pipeline_export_history(limit: int = 20):
    history = _export_pipeline.get_export_history(limit=limit)
    return {"jobs": [h.to_dict() for h in history]}

@router.get("/export-pipeline/estimate-size")
async def export_pipeline_estimate_size(profile_id: str = ""):
    estimate = _export_pipeline.estimate_export_size(profile_id=profile_id, asset_count=0)
    return estimate

@router.get("/export-pipeline/platform-config")
async def export_pipeline_platform_config(platform: str = "web"):
    target_map = {
        "web": ExportTarget.WEB_HTML5, "html5": ExportTarget.WEB_HTML5, "wasm": ExportTarget.WEB_WASM,
        "windows": ExportTarget.DESKTOP_WINDOWS, "win": ExportTarget.DESKTOP_WINDOWS,
        "macos": ExportTarget.DESKTOP_MACOS, "mac": ExportTarget.DESKTOP_MACOS,
        "linux": ExportTarget.DESKTOP_LINUX,
        "ios": ExportTarget.MOBILE_IOS, "android": ExportTarget.MOBILE_ANDROID,
        "switch": ExportTarget.CONSOLE_SWITCH,
    }
    target = target_map.get(platform.lower(), ExportTarget.WEB_HTML5)
    config = _export_pipeline.get_platform_config(target=target)
    if config:
        return config.to_dict()
    return {"error": "Platform not supported"}


# === Server Pool Endpoints ===

@router.get("/server-pool/stats")
async def server_pool_stats():
    return _server_pool.get_stats()

@router.post("/server-pool/spawn-server")
async def server_pool_spawn_server(name: str = "", region: str = "default", tier: str = "standard"):
    server = _server_pool.spawn_server(role=name, host="127.0.0.1", port=None, config=None)
    if server:
        return server.to_dict()
    return {"error": "Server spawn failed"}

@router.post("/server-pool/terminate-server")
async def server_pool_terminate_server(server_id: str = ""):
    return {"terminated": _server_pool.terminate_server(server_id=server_id)}

@router.post("/server-pool/restart-server")
async def server_pool_restart_server(server_id: str = ""):
    server = _server_pool.restart_server(server_id=server_id)
    if server:
        return server.to_dict()
    return {"error": "Server not found"}

@router.post("/server-pool/register-health-check")
async def server_pool_register_health_check(server_id: str = "", endpoint: str = "/health", interval_seconds: float = 30.0):
    result = _server_pool.register_health_check(server_id=server_id, cpu_usage=0.0, memory_mb=0.0, latency_ms=0.0, throughput=0.0)
    if result:
        return {"registered": result.id if hasattr(result, 'id') else True}
    return {"error": "Health check registration failed"}

@router.get("/server-pool/server-health")
async def server_pool_server_health(server_id: str = ""):
    health = _server_pool.get_server_health(server_id=server_id)
    return {"health": health.value if hasattr(health, 'value') else str(health)}

@router.post("/server-pool/allocate-server")
async def server_pool_allocate_server(region: str = "default", tier: str = "standard"):
    server = _server_pool.allocate_server(role=region, min_capacity=10.0)
    if server:
        return server.to_dict()
    return {"error": "No available servers in region"}

@router.post("/server-pool/set-scaling-policy")
async def server_pool_set_scaling_policy(min_servers: int = 1, max_servers: int = 10, target_cpu: float = 70.0,
                                           scale_up_threshold: float = 80.0, scale_down_threshold: float = 30.0):
    policy = _server_pool.set_scaling_policy(role="default", policy="cpu_based", min_instances=min_servers, max_instances=max_servers)
    if policy:
        return policy.to_dict()
    return {"error": "Scaling policy setup failed"}

@router.post("/server-pool/auto-scale")
async def server_pool_auto_scale():
    result = _server_pool.auto_scale()
    return result

@router.get("/server-pool/list-servers")
async def server_pool_list_servers(region: str = "", tier: str = ""):
    role = region if region else None
    state = tier if tier else None
    servers = _server_pool.list_servers(role=role, state=state)
    return {"servers": [s.to_dict() for s in servers]}

@router.get("/server-pool/cluster-status")
async def server_pool_cluster_status():
    status = _server_pool.get_cluster_status()
    return status


# === Gizmo System Endpoints ===

@router.get("/gizmo-system/stats")
async def gizmo_system_stats():
    return _gizmo_system.get_stats()

@router.post("/gizmo-system/create-config")
async def gizmo_system_create_config(name: str = "", gizmo_type: str = "translate", color: str = "#ffffff", size: float = 1.0):
    config = _gizmo_system.create_config(mode=gizmo_type, space="world", snap_mode="none", axis="none")
    if config:
        return config.to_dict()
    return {"error": "Gizmo config creation failed"}

@router.post("/gizmo-system/activate-gizmo")
async def gizmo_system_activate_gizmo(config_id: str = "", target_node_id: str = ""):
    target_ids = [target_node_id] if target_node_id else None
    success = _gizmo_system.activate_gizmo(config_id=config_id, target_ids=target_ids)
    return {"activated": success}

@router.post("/gizmo-system/deactivate-gizmo")
async def gizmo_system_deactivate_gizmo(gizmo_id: str = ""):
    return {"deactivated": _gizmo_system.deactivate_gizmo()}

@router.post("/gizmo-system/create-handle")
async def gizmo_system_create_handle(gizmo_id: str = "", handle_type: str = "translate", axis: str = "x",
                                       offset_x: float = 0.0, offset_y: float = 0.0, offset_z: float = 0.0):
    handle = _gizmo_system.create_transform_handle(node_id=gizmo_id, position=(offset_x, offset_y, offset_z), mode=handle_type)
    if handle:
        return handle.to_dict()
    return {"error": "Handle creation failed"}

@router.post("/gizmo-system/move-handle")
async def gizmo_system_move_handle(handle_id: str = "", delta_x: float = 0.0, delta_y: float = 0.0, delta_z: float = 0.0):
    result = _gizmo_system.move_handle(handle_id=handle_id, delta=(delta_x, delta_y, delta_z), constraint_axis=None)
    if result:
        return result.to_dict()
    return {"error": "Handle not found"}

@router.post("/gizmo-system/apply-transform")
async def gizmo_system_apply_transform(gizmo_id: str = ""):
    result = _gizmo_system.apply_transform(handle_id=gizmo_id)
    return result

@router.post("/gizmo-system/set-snap-settings")
async def gizmo_system_set_snap_settings(gizmo_id: str = "", snap_enabled: bool = True, translate_snap: float = 1.0,
                                            rotate_snap: float = 15.0, scale_snap: float = 0.1):
    snap = _gizmo_system.set_snap_settings(grid_size=translate_snap, angle_step=rotate_snap, scale_step=scale_snap)
    return snap.to_dict()

@router.post("/gizmo-system/start-box-select")
async def gizmo_system_start_box_select(start_x: float = 0.0, start_y: float = 0.0):
    selection = _gizmo_system.start_box_select(start_pos=(start_x, start_y))
    return selection.to_dict()

@router.post("/gizmo-system/update-box-select")
async def gizmo_system_update_box_select(selection_id: str = "", current_x: float = 0.0, current_y: float = 0.0):
    result = _gizmo_system.update_box_select(box_id=selection_id, current_pos=(current_x, current_y))
    if result:
        return result.to_dict()
    return {"error": "Selection not found"}

@router.post("/gizmo-system/finish-box-select")
async def gizmo_system_finish_box_select(selection_id: str = ""):
    result = _gizmo_system.finish_box_select(box_id=selection_id)
    return result

@router.get("/gizmo-system/active-gizmo")
async def gizmo_system_active_gizmo():
    gizmo = _gizmo_system.get_active_gizmo()
    if gizmo:
        return gizmo.to_dict()
    return {"active": None}


# === Pivot System Endpoints ===

@router.get("/pivot-system/stats")
async def pivot_system_stats():
    return _pivot_system.get_stats()

@router.post("/pivot-system/set-pivot")
async def pivot_system_set_pivot(node_id: str = "", x: float = 0.0, y: float = 0.0, z: float = 0.0):
    pivot = _pivot_system.set_pivot(node_id=node_id, position=(x, y, z), mode="center", space="local")
    return pivot.to_dict()

@router.get("/pivot-system/get-pivot")
async def pivot_system_get_pivot(node_id: str = ""):
    pivot = _pivot_system.get_pivot(node_id=node_id)
    if pivot:
        return pivot.to_dict()
    return {"error": "Pivot not found"}

@router.post("/pivot-system/snap-pivot")
async def pivot_system_snap_pivot(node_id: str = "", snap_mode: str = "grid", grid_size: float = 1.0):
    pivot = _pivot_system.snap_pivot_to(node_id=node_id, target_mode=snap_mode)
    if pivot:
        return pivot.to_dict()
    return {"error": "Pivot not found"}

@router.post("/pivot-system/create-handle")
async def pivot_system_create_handle(pivot_id: str = "", handle_type: str = "translate", axis: str = "x",
                                       color: str = "#ffffff"):
    handle = _pivot_system.create_handle(node_id=pivot_id, offset=(0.0, 0.0, 0.0), color=color, size=0.15)
    if handle:
        return handle.to_dict()
    return {"error": "Handle creation failed"}

@router.post("/pivot-system/bind-to-anchor")
async def pivot_system_bind_to_anchor(pivot_id: str = "", anchor_node_id: str = ""):
    result = _pivot_system.bind_to_anchor(pivot_id=pivot_id, anchor_type="node", anchor_id=anchor_node_id, offset=None, weight=1.0)
    if result:
        return {"success": True}
    return {"error": "Anchor binding failed"}

@router.post("/pivot-system/create-pivot-group")
async def pivot_system_create_pivot_group(name: str = "", pivot_ids: str = ""):
    ids = pivot_ids.split(",") if pivot_ids else []
    group = _pivot_system.create_pivot_group(node_ids=ids, mode="center", space="local")
    if group:
        return group.to_dict()
    return {"error": "Group creation failed"}

@router.post("/pivot-system/apply-group-transform")
async def pivot_system_apply_group_transform(group_id: str = "", translate_x: float = 0.0, translate_y: float = 0.0,
                                                translate_z: float = 0.0, rotate_x: float = 0.0, rotate_y: float = 0.0,
                                                rotate_z: float = 0.0, scale_x: float = 1.0, scale_y: float = 1.0,
                                                scale_z: float = 1.0):
    result = _pivot_system.apply_group_transform(group_id=group_id,
                                                   position=(translate_x, translate_y, translate_z),
                                                   rotation=(rotate_x, rotate_y, rotate_z),
                                                   scale=(scale_x, scale_y, scale_z))
    return result

@router.get("/pivot-system/list-pivots")
async def pivot_system_list_pivots(node_id: str = ""):
    pivots = _pivot_system.list_pivots(space=node_id if node_id else None)
    return {"pivots": [p.to_dict() for p in pivots]}


# === Learning Loop Endpoints ===

@router.get("/learning-loop/stats")
async def learning_loop_stats():
    return _learning_loop.get_stats()

@router.post("/learning-loop/create-skill")
async def learning_loop_create_skill(name: str = "", domain: str = "", description: str = ""):
    skill = _learning_loop.create_skill(name=name, description=description, category=domain)
    return skill.to_dict() if skill else {"error": "Skill creation failed"}

@router.post("/learning-loop/refine-skill")
async def learning_loop_refine_skill(skill_id: str = "", feedback: str = ""):
    result = _learning_loop.refine_skill(skill_id=skill_id, improvement_description=feedback)
    return result.to_dict() if result else {"error": "Skill not found"}

@router.post("/learning-loop/record-memory")
async def learning_loop_record_memory(content: str = "", category: str = "observation", importance: float = 0.5):
    from sparkai.agent.agent_learning_loop import MemoryType
    try:
        mem_type = MemoryType(category.upper())
    except ValueError:
        mem_type = MemoryType.OBSERVATION
    memory = _learning_loop.record_memory(memory_type=mem_type, content=content, importance=importance)
    return memory.to_dict() if memory else {"error": "Record failed"}

@router.get("/learning-loop/retrieve-memories")
async def learning_loop_retrieve_memories(query: str = "", limit: int = 10, category: Optional[str] = None):
    from sparkai.agent.agent_learning_loop import MemoryType
    mem_type = None
    if category:
        try:
            mem_type = MemoryType(category.lower())
        except ValueError:
            pass
    memories = _learning_loop.retrieve_memories(query=query, limit=limit, memory_type=mem_type)
    return {"memories": [m.to_dict() for m in memories]}

@router.post("/learning-loop/start-session")
async def learning_loop_start_session(agent_id: str = "", context: str = ""):
    session = _learning_loop.start_learning_session(task_description=context, agent_id=agent_id)
    return session.to_dict() if session else {"error": "Session start failed"}

@router.post("/learning-loop/end-session")
async def learning_loop_end_session(session_id: str = "", summary: str = ""):
    result = _learning_loop.end_learning_session(session_id=session_id, outcome=summary)
    return result.to_dict() if result else {"error": "Session not found"}

@router.post("/learning-loop/schedule-nudge")
async def learning_loop_schedule_nudge(agent_id: str = "", message: str = "", delay_minutes: int = 5):
    from sparkai.agent.agent_learning_loop import NudgeTrigger
    nudge = _learning_loop.schedule_nudge(
        trigger=NudgeTrigger.MANUAL,
        message=message,
        priority=delay_minutes,
        target_agent=agent_id,
    )
    return nudge.to_dict() if nudge else {"error": "Schedule failed"}

@router.get("/learning-loop/pending-nudges")
async def learning_loop_pending_nudges(agent_id: str = ""):
    nudges = _learning_loop.get_pending_nudges(count=10)
    if agent_id:
        nudges = [n for n in nudges if n.target_agent == agent_id]
    return {"nudges": [n.to_dict() for n in nudges]}

@router.post("/learning-loop/dismiss-nudge")
async def learning_loop_dismiss_nudge(nudge_id: str = ""):
    return {"dismissed": _learning_loop.dismiss_nudge(nudge_id)}

@router.get("/learning-loop/skill-evolution")
async def learning_loop_skill_evolution(skill_id: str = ""):
    evolution = _learning_loop.get_skill_evolution(skill_id)
    return evolution if evolution else {"error": "Evolution data not found"}


# === Cron Scheduler Endpoints ===

@router.get("/cron-scheduler/stats")
async def cron_scheduler_stats():
    return _cron_scheduler.get_stats()

@router.post("/cron-scheduler/create-rule")
async def cron_scheduler_create_rule(name: str = "", cron_expression: str = "", action: str = "", description: str = ""):
    from sparkai.agent.agent_cron_scheduler import CronFrequency
    rule = _cron_scheduler.create_rule(
        name=name,
        frequency=CronFrequency.CUSTOM,
        cron_expression=cron_expression,
        timezone="UTC",
    )
    return rule.to_dict() if rule else {"error": "Rule creation failed"}

@router.post("/cron-scheduler/schedule-task")
async def cron_scheduler_schedule_task(task_name: str = "", cron_expression: str = "", payload: str = "{}", description: str = ""):
    import json as _json
    from sparkai.agent.agent_cron_scheduler import CronFrequency
    rule = _cron_scheduler.create_rule(
        name=task_name,
        frequency=CronFrequency.CUSTOM,
        cron_expression=cron_expression,
    )
    try:
        action_params = _json.loads(payload) if payload else {}
    except (ValueError, TypeError):
        action_params = {}
    task = _cron_scheduler.schedule_task(
        agent_id="api",
        rule_id=rule.id,
        task_name=task_name,
        action_params=action_params,
    )
    return task.to_dict() if task else {"error": "Schedule failed"}

@router.post("/cron-scheduler/cancel-task")
async def cron_scheduler_cancel_task(task_id: str = ""):
    return {"cancelled": _cron_scheduler.cancel_task(task_id)}

@router.post("/cron-scheduler/pause-task")
async def cron_scheduler_pause_task(task_id: str = ""):
    return {"paused": _cron_scheduler.pause_task(task_id)}

@router.post("/cron-scheduler/resume-task")
async def cron_scheduler_resume_task(task_id: str = ""):
    return {"resumed": _cron_scheduler.resume_task(task_id)}

@router.post("/cron-scheduler/trigger-task")
async def cron_scheduler_trigger_task(task_id: str = ""):
    result = _cron_scheduler.trigger_task_now(task_id)
    return result.to_dict() if result else {"error": "Trigger failed"}

@router.get("/cron-scheduler/due-tasks")
async def cron_scheduler_due_tasks():
    tasks = _cron_scheduler.get_due_tasks()
    return {"tasks": [t.to_dict() for t in tasks]}

@router.get("/cron-scheduler/execution-history")
async def cron_scheduler_execution_history(task_id: str = "", limit: int = 50):
    history = _cron_scheduler.get_execution_history(task_id=task_id, limit=limit) if task_id else []
    return {"history": [h.to_dict() for h in history]}


# === Memory Graph Endpoints ===

@router.get("/memory-graph/stats")
async def memory_graph_stats():
    return _memory_graph.get_stats()

@router.post("/memory-graph/add-node")
async def memory_graph_add_node(label: str = "", content: str = "", category: str = "general", importance: float = 0.5):
    node = _memory_graph.add_node(category=category, content=content, importance=importance)
    return node.to_dict() if node else {"error": "Add node failed"}

@router.post("/memory-graph/add-edge")
async def memory_graph_add_edge(source_id: str = "", target_id: str = "", relation: str = "related", weight: float = 1.0):
    edge = _memory_graph.add_edge(source_id=source_id, target_id=target_id, relation_type=relation, weight=weight)
    return edge.to_dict() if edge else {"error": "Add edge failed"}

@router.get("/memory-graph/search")
async def memory_graph_search(query: str = "", limit: int = 10, category: Optional[str] = None):
    categories = [category] if category else None
    results = _memory_graph.search(query=query, max_results=limit, categories=categories)
    return {"results": [r.to_dict() for r in results]}

@router.get("/memory-graph/graph-walk")
async def memory_graph_graph_walk(start_node_id: str = "", max_depth: int = 3, relation_filter: Optional[str] = None):
    path = _memory_graph.graph_walk(start_node_id=start_node_id, max_depth=max_depth, relation_filter=relation_filter)
    return path if path else {"error": "Walk failed"}

@router.get("/memory-graph/session-context")
async def memory_graph_session_context(agent_id: str = "", window_size: int = 10):
    context = _memory_graph.get_session_context(session_id=agent_id)
    return context if context else {"error": "Session context not found"}

@router.post("/memory-graph/consolidate")
async def memory_graph_consolidate(min_similarity: float = 0.85, category: Optional[str] = None):
    result = _memory_graph.consolidate_memories(older_than_seconds=3600.0)
    return result if result else {"error": "Consolidation failed"}

@router.post("/memory-graph/forget-stale")
async def memory_graph_forget_stale(max_age_days: int = 30):
    removed = _memory_graph.forget_stale(max_age_seconds=max_age_days * 86400.0)
    return {"removed": removed}

@router.get("/memory-graph/export-subgraph")
async def memory_graph_export_subgraph(root_node_id: str = "", depth: int = 2):
    subgraph = _memory_graph.export_subgraph(root_id=root_node_id, depth=depth)
    return subgraph if subgraph else {"error": "Export failed"}


# === Context Compressor Endpoints ===

@router.get("/context-compressor/stats")
async def context_compressor_stats():
    return _context_compressor.get_stats()

@router.post("/context-compressor/register-chunk")
async def context_compressor_register_chunk(content: str = "", chunk_type: str = "text", size: int = 0, metadata: str = "{}"):
    import json as _json
    from sparkai.agent.agent_context_compressor import ContentType
    try:
        ct = ContentType(chunk_type.upper())
    except ValueError:
        ct = ContentType.USER_MESSAGE
    try:
        meta = _json.loads(metadata) if metadata else {}
    except (ValueError, TypeError):
        meta = {}
    chunk = _context_compressor.register_chunk(content=content, content_type=ct, token_estimate=size, metadata=meta)
    return chunk.to_dict() if chunk else {"error": "Register failed"}

@router.post("/context-compressor/create-policy")
async def context_compressor_create_policy(name: str = "", max_tokens: int = 4096, strategy: str = "summarize", priority: str = "recent"):
    from sparkai.agent.agent_context_compressor import CompressionStrategy
    try:
        cs = CompressionStrategy(strategy.upper())
    except ValueError:
        cs = CompressionStrategy.SUMMARIZE
    policy = _context_compressor.create_policy(name=name, strategy=cs, trigger_threshold_token=max_tokens)
    return policy.to_dict() if policy else {"error": "Policy creation failed"}

@router.post("/context-compressor/compress")
async def context_compressor_compress(session_id: str = "", policy_id: Optional[str] = None):
    result = _context_compressor.compress(policy_id=policy_id)
    return result.to_dict() if result else {"error": "Compression failed"}

@router.post("/context-compressor/select-relevant")
async def context_compressor_select_relevant(query: str = "", session_id: str = "", max_chunks: int = 5):
    chunks = _context_compressor.select_relevant(query, session_id, max_chunks)
    return {"chunks": [c.to_dict() for c in chunks]}

@router.get("/context-compressor/current-budget")
async def context_compressor_current_budget(session_id: str = ""):
    budget = _context_compressor.get_current_budget()
    return budget if budget else {"error": "Budget not found"}

@router.get("/context-compressor/compression-history")
async def context_compressor_compression_history(session_id: str = "", limit: int = 20):
    history = _context_compressor.get_compression_history(limit=limit)
    return {"history": [h.to_dict() for h in history]}


# === Tool Forge Endpoints ===

@router.get("/tool-forge/stats")
async def tool_forge_stats():
    return _tool_forge.get_stats()

@router.post("/tool-forge/define-schema")
async def tool_forge_define_schema(name: str = "", description: str = "", parameters: str = "{}"):
    import json as _json
    try:
        params = _json.loads(parameters) if parameters else []
    except (ValueError, TypeError):
        params = []
    if not isinstance(params, list):
        params = [params]
    schema = _tool_forge.define_schema(name=name, description=description, category="general", parameters=params)
    return schema.to_dict() if schema else {"error": "Schema definition failed"}

@router.post("/tool-forge/forge-tool")
async def tool_forge_forge_tool(name: str = "", schema_id: str = "", handler_code: str = "", description: str = ""):
    tool = _tool_forge.forge_tool(schema_id=schema_id, strategy=handler_code or "generate", template_source=handler_code, agent_id=name)
    return tool.to_dict() if tool else {"error": "Forge failed"}

@router.post("/tool-forge/validate-tool")
async def tool_forge_validate_tool(tool_id: str = ""):
    result = _tool_forge.validate_tool(tool_id)
    return result.to_dict() if result else {"error": "Validation failed"}

@router.post("/tool-forge/activate-tool")
async def tool_forge_activate_tool(tool_id: str = ""):
    return {"activated": _tool_forge.activate_tool(tool_id)}

@router.post("/tool-forge/deprecate-tool")
async def tool_forge_deprecate_tool(tool_id: str = "", reason: str = ""):
    return {"deprecated": _tool_forge.deprecate_tool(tool_id, reason)}

@router.post("/tool-forge/execute-tool")
async def tool_forge_execute_tool(tool_id: str = "", parameters: str = "{}"):
    import json as _json
    try:
        inputs = _json.loads(parameters) if parameters else {}
    except (ValueError, TypeError):
        inputs = {}
    result = _tool_forge.execute_tool(tool_id=tool_id, inputs=inputs)
    return result if result else {"error": "Execution failed"}

@router.get("/tool-forge/list-tools")
async def tool_forge_list_tools(category: Optional[str] = None, active_only: bool = False):
    tools = _tool_forge.list_tools(category=category, status="active" if active_only else None)
    return {"tools": [t.to_dict() for t in tools]}

@router.get("/tool-forge/tool-performance")
async def tool_forge_tool_performance(tool_id: str = ""):
    perf = _tool_forge.get_tool_performance(tool_id)
    return perf if perf else {"error": "Performance data not found"}

@router.post("/tool-forge/refine-tool")
async def tool_forge_refine_tool(tool_id: str = "", feedback: str = "", handler_code: str = ""):
    result = _tool_forge.refine_tool(tool_id=tool_id, optimization_target=feedback or "accuracy")
    return result.to_dict() if result else {"error": "Refine failed"}


# === Gateway Endpoints ===

@router.get("/gateway/stats")
async def gateway_stats():
    return _gateway.get_stats()

@router.post("/gateway/register-endpoint")
async def gateway_register_endpoint(name: str = "", url: str = "", protocol: str = "http", auth_type: str = "none"):
    endpoint = _gateway.register_endpoint(platform=url or "default", name=name, handler_type=protocol, config={"auth_type": auth_type})
    return endpoint.to_dict() if endpoint else {"error": "Registration failed"}

@router.post("/gateway/open-connection")
async def gateway_open_connection(endpoint_id: str = "", config: str = "{}"):
    import json as _json
    try:
        metadata = _json.loads(config) if config else {}
    except (ValueError, TypeError):
        metadata = {}
    connection = _gateway.open_connection(platform=endpoint_id, client_id=endpoint_id, metadata=metadata)
    return connection.to_dict() if connection else {"error": "Connection failed"}

@router.post("/gateway/close-connection")
async def gateway_close_connection(connection_id: str = ""):
    return {"closed": _gateway.close_connection(connection_id)}

@router.post("/gateway/route-message")
async def gateway_route_message(connection_id: str = "", message: str = "", target: str = "", priority: str = "normal"):
    result = _gateway.route_message(sender_id=connection_id, target_platform=target, target_endpoint=target, payload={"message": message}, priority=0)
    return result.to_dict() if result else {"error": "Route failed"}

@router.post("/gateway/broadcast-message")
async def gateway_broadcast_message(message: str = "", channels: str = "", priority: str = "normal"):
    channel_list = [c.strip() for c in channels.split(",") if c.strip()] if channels else None
    results = _gateway.broadcast_message(payload={"message": message}, platforms=channel_list, priority=0)
    return {"results": [r.to_dict() for r in results]} if results else {"error": "Broadcast failed"}

@router.get("/gateway/active-connections")
async def gateway_active_connections():
    connections = _gateway.get_active_connections()
    return {"connections": [c.to_dict() for c in connections]}

@router.get("/gateway/message-queue")
async def gateway_message_queue(connection_id: str = "", limit: int = 50):
    queue = _gateway.get_message_queue(limit=limit, platform=connection_id if connection_id else None)
    return {"queue": [q.to_dict() for q in queue]}

@router.get("/gateway/delivery-status")
async def gateway_delivery_status(message_id: str = ""):
    status = _gateway.get_delivery_status(message_id)
    return status if status else {"error": "Message not found"}

@router.get("/gateway/platform-stats")
async def gateway_platform_stats(platform: str = ""):
    return _gateway.get_platform_stats(platform=platform)


# ============================================================
# Session Snapshot Endpoints
# ============================================================

@router.get("/session-snapshot/stats")
async def session_snapshot_stats():
    return _session_snapshot.get_stats()

@router.post("/session-snapshot/create-snapshot")
async def session_snapshot_create_snapshot(session_id: str = "", agent_id: str = "", mode: str = "full", label: str = ""):
    from sparkai.agent.agent_session_snapshot import SnapshotMode
    try:
        mode_enum = SnapshotMode[mode.upper()]
    except (KeyError, AttributeError):
        mode_enum = SnapshotMode.FULL
    result = _session_snapshot.create_snapshot(session_id=session_id, agent_id=agent_id, state_data={}, mode=mode_enum, label=label)
    return result.to_dict() if result else {"error": "Snapshot creation failed"}

@router.post("/session-snapshot/restore-session")
async def session_snapshot_restore_session(snapshot_id: str = "", session_id: str = ""):
    result = _session_snapshot.restore_session(snapshot_id=snapshot_id, target_session_id=session_id)
    return result.to_dict() if result else {"error": "Session restore failed"}

@router.get("/session-snapshot/list-snapshots")
async def session_snapshot_list_snapshots(session_id: str = "", agent_id: str = "", limit: int = 50):
    snapshots = _session_snapshot.list_snapshots(session_id=session_id, agent_id=agent_id, limit=limit)
    return {"snapshots": [s.to_dict() for s in snapshots]}

@router.post("/session-snapshot/create-checkpoint")
async def session_snapshot_create_checkpoint(session_id: str = "", checkpoint_type: str = "auto", description: str = ""):
    result = _session_snapshot.create_checkpoint(session_id=session_id, checkpoint_type=checkpoint_type, description=description)
    return result.to_dict() if result else {"error": "Checkpoint creation failed"}

@router.get("/session-snapshot/compare-snapshots")
async def session_snapshot_compare_snapshots(snapshot_id_a: str = "", snapshot_id_b: str = ""):
    result = _session_snapshot.compare_snapshots(snapshot_id_a=snapshot_id_a, snapshot_id_b=snapshot_id_b)
    return result if result else {"error": "Comparison failed"}

@router.post("/session-snapshot/prune-snapshots")
async def session_snapshot_prune_snapshots(session_id: str = "", max_age_days: int = 30, max_count: int = 100):
    removed = _session_snapshot.prune_snapshots(session_id=session_id, max_age_days=max_age_days, max_count=max_count)
    return {"removed": removed}


# ============================================================
# Trajectory Compressor Endpoints
# ============================================================

@router.get("/trajectory-compressor/stats")
async def trajectory_compressor_stats():
    return _trajectory_compressor.get_stats()

@router.post("/trajectory-compressor/ingest-trajectory")
async def trajectory_compressor_ingest_trajectory(agent_id: str = "", session_id: str = "", turns: str = "[]"):
    import json as _json
    try:
        turns_data = _json.loads(turns) if turns else []
    except (ValueError, TypeError):
        turns_data = []
    result = _trajectory_compressor.ingest_trajectory(agent_id=agent_id, session_id=session_id, turns=turns_data)
    return result.to_dict() if result else {"error": "Ingest failed"}

@router.post("/trajectory-compressor/compress")
async def trajectory_compressor_compress(trajectory_id: str = "", mode: str = "SUMMARIZE"):
    result = _trajectory_compressor.compress(trajectory_id=trajectory_id, mode=mode)
    return result.to_dict() if result else {"error": "Compression failed"}

@router.get("/trajectory-compressor/export-training-data")
async def trajectory_compressor_export_training_data(trajectory_id: str = "", format: str = "CHATML", max_tokens: int = 4096):
    result = _trajectory_compressor.export_training_data(trajectory_id=trajectory_id, format=format, max_tokens=max_tokens)
    return result if result else {"error": "Export failed"}

@router.get("/trajectory-compressor/filter-by-relevance")
async def trajectory_compressor_filter_by_relevance(trajectory_id: str = "", query: str = "", filter: str = "MODERATE"):
    result = _trajectory_compressor.filter_by_relevance(trajectory_id=trajectory_id, query=query, filter=filter)
    return {"filtered": [r.to_dict() for r in result]} if result else {"error": "Filter failed"}

@router.get("/trajectory-compressor/estimate-compression-ratio")
async def trajectory_compressor_estimate_compression_ratio(trajectory_id: str = ""):
    result = _trajectory_compressor.estimate_compression_ratio(trajectory_id=trajectory_id)
    return result if result else {"error": "Estimation failed"}


# ============================================================
# Skills Hub Endpoints
# ============================================================

@router.get("/skills-hub/stats")
async def skills_hub_stats():
    return _skills_hub.get_stats()

@router.post("/skills-hub/publish-skill")
async def skills_hub_publish_skill(name: str = "", description: str = "", category: str = "utility", source_url: str = "", license: str = "MIT", author: str = "", version: str = "1.0.0", tags: str = "", homepage: str = ""):
    import json as _json
    try:
        tags_list = _json.loads(tags) if tags else []
    except (ValueError, TypeError):
        tags_list = []
    from sparkai.agent.agent_skills_hub import SkillCategory, LicenseType
    try:
        cat_enum = SkillCategory[category.upper()]
    except (KeyError, AttributeError):
        cat_enum = SkillCategory.UTILITY
    try:
        lic_enum = LicenseType[license.upper()]
    except (KeyError, AttributeError):
        lic_enum = LicenseType.MIT
    result = _skills_hub.publish_skill(name=name, description=description, category=cat_enum, source_url=source_url, license=lic_enum, author=author, version=version, tags=tags_list, homepage=homepage)
    return result.to_dict() if result else {"error": "Publish failed"}

@router.post("/skills-hub/install-skill")
async def skills_hub_install_skill(skill_id: str = "", version: str = ""):
    result = _skills_hub.install_skill(skill_id=skill_id, version=version)
    return result.to_dict() if result else {"error": "Install failed"}

@router.get("/skills-hub/search-skills")
async def skills_hub_search_skills(query: str = "", category: str = "", limit: int = 20):
    results = _skills_hub.search_skills(query=query, category=category, limit=limit)
    return {"skills": [s.to_dict() for s in results]}

@router.post("/skills-hub/rate-skill")
async def skills_hub_rate_skill(skill_id: str = "", rating: int = 0, review: str = ""):
    result = _skills_hub.rate_skill(skill_id=skill_id, score=rating, review=review)
    return result.to_dict() if result else {"error": "Rate failed"}

@router.get("/skills-hub/list-installed")
async def skills_hub_list_installed(category: str = ""):
    skills = _skills_hub.list_installed(category=category)
    return {"skills": [s.to_dict() for s in skills]}

@router.get("/skills-hub/check-updates")
async def skills_hub_check_updates():
    updates = _skills_hub.check_updates()
    return {"updates": updates}


# ============================================================
# Personality System Endpoints
# ============================================================

@router.get("/personality-system/stats")
async def personality_system_stats():
    return _personality_system.get_stats()

@router.post("/personality-system/create-profile")
async def personality_system_create_profile(name: str = "", description: str = "", traits: str = '[["openness", 0.7], ["creativity", 0.8]]', archetype: str = "generalist", style: str = "casual"):
    import json as _json
    try:
        traits_list = _json.loads(traits) if traits else []
    except (ValueError, TypeError):
        traits_list = []
    from sparkai.agent.agent_personality_system import RoleArchetype, InteractionStyle
    try:
        arch_enum = RoleArchetype[archetype.upper()]
    except (KeyError, AttributeError):
        arch_enum = RoleArchetype.GENERALIST
    try:
        style_enum = InteractionStyle[style.upper()]
    except (KeyError, AttributeError):
        style_enum = InteractionStyle.CASUAL
    result = _personality_system.create_profile(name=name, description=description, traits=traits_list, archetype=arch_enum, style=style_enum)
    return result.to_dict() if result else {"error": "Profile creation failed"}

@router.post("/personality-system/set-trait-weight")
async def personality_system_set_trait_weight(profile_id: str = "", trait_name: str = "", weight: float = 0.5):
    result = _personality_system.set_trait_weight(profile_id=profile_id, trait_name=trait_name, weight=weight)
    return result.to_dict() if result else {"error": "Trait weight update failed"}

@router.post("/personality-system/activate-profile")
async def personality_system_activate_profile(profile_id: str = "", agent_id: str = ""):
    result = _personality_system.activate_profile(profile_id=profile_id, agent_id=agent_id)
    return {"activated": bool(result)}

@router.post("/personality-system/blend-profiles")
async def personality_system_blend_profiles(profile_ids: str = "", blend_weights: str = "", name: str = "blended"):
    import json as _json
    try:
        pids = _json.loads(profile_ids) if profile_ids else []
        weights = _json.loads(blend_weights) if blend_weights else None
    except (ValueError, TypeError):
        pids = []
        weights = None
    result = _personality_system.blend_profiles(profile_ids=pids, weights=weights, name=name)
    return result.to_dict() if result else {"error": "Blend failed"}

@router.get("/personality-system/suggest-settings")
async def personality_system_suggest_settings(task_type: str = "creative", agent_count: int = 1):
    result = _personality_system.suggest_settings(task_type=task_type, agent_count=agent_count)
    return result if result else {"error": "Suggestion failed"}

@router.get("/personality-system/evaluate-tone")
async def personality_system_evaluate_tone(profile_id: str = "", prompt: str = ""):
    result = _personality_system.evaluate_tone(profile_id=profile_id, input_text=prompt)
    return result if result else {"error": "Evaluation failed"}


# ============================================================
# Insights Generator Endpoints
# ============================================================

@router.get("/insights-generator/stats")
async def insights_generator_stats():
    return _insights_generator.get_stats()

@router.post("/insights-generator/collect-metrics")
async def insights_generator_collect_metrics(agent_id: str = "", time_range_days: int = 7):
    result = _insights_generator.collect_metrics(agent_id=agent_id, time_range_days=time_range_days)
    return {"metrics": [m.to_dict() for m in result]} if result else {"error": "Metric collection failed"}

@router.post("/insights-generator/generate-insights")
async def insights_generator_generate_insights(agent_id: str = "", min_confidence: float = 0.3):
    result = _insights_generator.generate_insights(agent_id=agent_id, min_confidence=min_confidence)
    return {"insights": [i.to_dict() for i in result]} if result else {"error": "Insight generation failed"}

@router.post("/insights-generator/detect-anomalies")
async def insights_generator_detect_anomalies(agent_id: str = "", lookback_days: int = 14):
    result = _insights_generator.detect_anomalies(agent_id=agent_id, lookback_days=lookback_days)
    return {"anomalies": [a.to_dict() for a in result]} if result else {"error": "Anomaly detection failed"}

@router.get("/insights-generator/analyze-trends")
async def insights_generator_analyze_trends(agent_id: str = "", metric: str = "performance", granularity: str = "daily"):
    result = _insights_generator.analyze_trends(agent_id=agent_id, metric=metric, granularity=granularity)
    return result.to_dict() if result else {"error": "Trend analysis failed"}

@router.post("/insights-generator/create-report")
async def insights_generator_create_report(agent_id: str = "", format: str = "markdown", include_charts: bool = False):
    result = _insights_generator.create_report(agent_id=agent_id, format=format, include_charts=include_charts)
    return result.to_dict() if result else {"error": "Report creation failed"}

@router.get("/insights-generator/compare-agents")
async def insights_generator_compare_agents(agent_ids: str = "", metric: str = "performance"):
    import json as _json
    try:
        aids = _json.loads(agent_ids) if agent_ids else []
    except (ValueError, TypeError):
        aids = []
    result = _insights_generator.compare_agents(agent_ids=aids, metric=metric)
    return result if result else {"error": "Comparison failed"}


# ============================================================
# Provider Switch Endpoints
# ============================================================

@router.get("/provider-switch/stats")
async def provider_switch_stats():
    return _provider_switch.get_stats()

@router.post("/provider-switch/register-provider")
async def provider_switch_register_provider(name: str = "", provider_type: str = "openai", base_url: str = "", api_key_ref: str = ""):
    from sparkai.agent.agent_provider_switch import ProviderType
    try:
        pt_enum = ProviderType[provider_type.upper()]
    except (KeyError, AttributeError):
        pt_enum = ProviderType.OPENAI
    result = _provider_switch.register_provider(name=name, provider_type=pt_enum, base_url=base_url, api_key_ref=api_key_ref)
    return result.to_dict() if result else {"error": "Provider registration failed"}

@router.post("/provider-switch/configure-model")
async def provider_switch_configure_model(model_id: str = "", provider_id: str = "", cost_per_1k_input: float = 0.0, cost_per_1k_output: float = 0.0, performance_score: float = 0.0, context_window: int = 4096):
    result = _provider_switch.configure_model(model_id=model_id, provider_id=provider_id, cost_per_1k_input=cost_per_1k_input, cost_per_1k_output=cost_per_1k_output, performance_score=performance_score, context_window=context_window)
    return result.to_dict() if result else {"error": "Model configuration failed"}

@router.get("/provider-switch/auto-select-model")
async def provider_switch_auto_select_model(task_description: str = "", budget: float = 0.0):
    result = _provider_switch.auto_select_model(task_description=task_description, budget=budget)
    return result if result else {"error": "Auto-select failed"}

@router.post("/provider-switch/handle-failover")
async def provider_switch_handle_failover(failed_model_id: str = "", request_id: str = ""):
    result = _provider_switch.handle_failover(failed_model_id=failed_model_id, request_id=request_id)
    return result if result else {"error": "Failover failed"}

@router.post("/provider-switch/record-usage")
async def provider_switch_record_usage(model_id: str = "", tokens_in: int = 0, tokens_out: int = 0, duration: float = 0.0):
    result = _provider_switch.record_usage(model_id=model_id, tokens_in=tokens_in, tokens_out=tokens_out, duration=duration)
    return result.to_dict() if result else {"error": "Usage recording failed"}

@router.get("/provider-switch/list-providers")
async def provider_switch_list_providers(status: str = ""):
    providers = _provider_switch.list_providers(status=status)
    return {"providers": [p.to_dict() for p in providers]}


# ============================================================
# Event Sheet Endpoints
# ============================================================

@router.get("/event-sheet/stats")
async def event_sheet_stats():
    return _event_sheet.get_stats()

@router.post("/event-sheet/create-sheet")
async def event_sheet_create_sheet(name: str = "", description: str = "", linked_scene: str = ""):
    result = _event_sheet.create_sheet(name=name, description=description, linked_scene=linked_scene)
    return result.to_dict() if result else {"error": "Sheet creation failed"}

@router.post("/event-sheet/add-event")
async def event_sheet_add_event(sheet_id: str = "", event_type: str = "trigger", parent_event_id: str = ""):
    from sparkai.engine.engine_event_sheet import EventType
    try:
        et_enum = EventType[event_type.upper()]
    except (KeyError, AttributeError):
        et_enum = EventType.TRIGGER
    result = _event_sheet.add_event(sheet_id=sheet_id, event_type=et_enum, parent_event_id=parent_event_id if parent_event_id else None)
    return result.to_dict() if result else {"error": "Add event failed"}

@router.post("/event-sheet/add-condition")
async def event_sheet_add_condition(event_id: str = "", property: str = "", operator: str = "equals", value: str = ""):
    from sparkai.engine.engine_event_sheet import ConditionOperator
    try:
        op_enum = ConditionOperator[operator.upper()]
    except (KeyError, AttributeError):
        op_enum = ConditionOperator.EQUALS
    result = _event_sheet.add_condition(event_id=event_id, property=property, operator=op_enum, value=value)
    return result.to_dict() if result else {"error": "Add condition failed"}

@router.post("/event-sheet/add-action")
async def event_sheet_add_action(event_id: str = "", action_type: str = "execute", target: str = "", parameters: str = "{}"):
    import json as _json
    try:
        params = _json.loads(parameters) if parameters else {}
    except (ValueError, TypeError):
        params = {}
    from sparkai.engine.engine_event_sheet import ActionType
    try:
        at_enum = ActionType[action_type.upper()]
    except (KeyError, AttributeError):
        at_enum = ActionType.EXECUTE
    result = _event_sheet.add_action(event_id=event_id, action_type=at_enum, target=target, parameters=params)
    return result.to_dict() if result else {"error": "Add action failed"}

@router.get("/event-sheet/evaluate-sheet")
async def event_sheet_evaluate_sheet(sheet_id: str = "", game_state: str = "{}"):
    import json as _json
    try:
        ctx = _json.loads(game_state) if game_state else {}
    except (ValueError, TypeError):
        ctx = {}
    result = _event_sheet.evaluate_sheet(sheet_id=sheet_id, game_state=ctx)
    return result if result else {"error": "Evaluation failed"}

@router.get("/event-sheet/export-sheet")
async def event_sheet_export_sheet(sheet_id: str = ""):
    result = _event_sheet.export_event_sheet(sheet_id=sheet_id)
    return result if result else {"error": "Export failed"}


# ============================================================
# Resource Serializer Endpoints
# ============================================================

@router.get("/resource-serializer/stats")
async def resource_serializer_stats():
    return _resource_serializer.get_stats()

@router.post("/resource-serializer/register-resource")
async def resource_serializer_register_resource(path: str = "", resource_type: str = "texture", metadata: str = "{}"):
    import json as _json
    try:
        metadata_data = _json.loads(metadata) if metadata else {}
    except (ValueError, TypeError):
        metadata_data = {}
    from sparkai.engine.engine_resource_serializer import ResourceType
    try:
        rt_enum = ResourceType[resource_type.upper()]
    except (KeyError, AttributeError):
        rt_enum = ResourceType.TEXTURE
    result = _resource_serializer.register_resource(path=path, resource_type=rt_enum, metadata=metadata_data)
    return result.to_dict() if result else {"error": "Resource registration failed"}

@router.post("/resource-serializer/serialize")
async def resource_serializer_serialize(resource_id: str = "", format: str = "json", compress: bool = False):
    from sparkai.engine.engine_resource_serializer import SerializationFormat
    try:
        fmt_enum = SerializationFormat[format.upper()]
    except (KeyError, AttributeError):
        fmt_enum = SerializationFormat.JSON
    result = _resource_serializer.serialize(resource_id=resource_id, format=fmt_enum, compress=compress)
    return result.to_dict() if result else {"error": "Serialization failed"}

@router.post("/resource-serializer/deserialize")
async def resource_serializer_deserialize(data: str = "", format: str = "json", compressed: bool = False):
    encoded = data.encode("utf-8") if data else b"{}"
    from sparkai.engine.engine_resource_serializer import SerializationFormat
    try:
        fmt_enum = SerializationFormat[format.upper()]
    except (KeyError, AttributeError):
        fmt_enum = SerializationFormat.JSON
    result = _resource_serializer.deserialize(data=encoded, format=fmt_enum, compressed=compressed)
    return result.to_dict() if result else {"error": "Deserialization failed"}

@router.post("/resource-serializer/import-bundle")
async def resource_serializer_import_bundle(bundle_data: str = "{}"):
    import json as _json
    try:
        bd = _json.loads(bundle_data)
    except (ValueError, TypeError):
        bd = {}
    result = _resource_serializer.import_bundle(bundle_data=bd)
    return result.to_dict() if result else {"error": "Import failed"}

@router.get("/resource-serializer/export-bundle")
async def resource_serializer_export_bundle(resource_ids: str = "", name: str = "export", description: str = ""):
    import json as _json
    try:
        rids = _json.loads(resource_ids) if resource_ids else []
    except (ValueError, TypeError):
        rids = []
    result = _resource_serializer.export_bundle(resource_ids=rids, name=name, description=description)
    return result.to_dict() if result else {"error": "Export failed"}

@router.get("/resource-serializer/build-dependency-graph")
async def resource_serializer_build_dependency_graph(resource_id: str = ""):
    result = _resource_serializer.build_dependency_graph(resource_id=resource_id)
    return result if result else {"error": "Dependency graph build failed"}


# ============================================================
# Input Map Endpoints
# ============================================================

@router.get("/input-map/stats")
async def input_map_stats():
    return _input_map.get_stats()

@router.post("/input-map/define-action")
async def input_map_define_action(name: str = "", action_type: str = "press", default_bindings: str = ""):
    import json as _json
    try:
        bindings = _json.loads(default_bindings) if default_bindings else []
    except (ValueError, TypeError):
        bindings = []
    from sparkai.engine.engine_input_map import InputActionType
    try:
        at_enum = InputActionType[action_type.upper()]
    except (KeyError, AttributeError):
        try:
            at_enum = InputActionType(action_type.lower())
        except (ValueError, KeyError):
            at_enum = InputActionType.PRESS
    result = _input_map.define_action(name=name, action_type=at_enum, default_bindings=bindings if bindings else None)
    return result.to_dict() if result else {"error": "Action definition failed"}

@router.post("/input-map/bind-action")
async def input_map_bind_action(action_id: str = "", device: str = "keyboard", input_code: str = "", modifiers: str = "", scale: float = 1.0, invert: bool = False):
    import json as _json
    try:
        mods = _json.loads(modifiers) if modifiers else []
    except (ValueError, TypeError):
        mods = []
    from sparkai.engine.engine_input_map import InputDevice
    try:
        dev_enum = InputDevice[device.upper()]
    except (KeyError, AttributeError):
        dev_enum = InputDevice.KEYBOARD
    result = _input_map.bind_action(action_id=action_id, device=dev_enum, input_code=input_code, modifiers=mods, scale=scale, invert=invert)
    return {"success": result}

@router.post("/input-map/create-context")
async def input_map_create_context(name: str = "", priority: int = 0):
    result = _input_map.create_context(name=name, priority=priority)
    return result.to_dict() if result else {"error": "Context creation failed"}

@router.post("/input-map/push-context")
async def input_map_push_context(context_id: str = ""):
    result = _input_map.push_context(context_id=context_id)
    return {"pushed": result}

@router.get("/input-map/process-input")
async def input_map_process_input(device: str = "keyboard", input_code: str = "", value: float = 1.0):
    from sparkai.engine.engine_input_map import InputDevice
    try:
        dev_enum = InputDevice[device.upper()]
    except (KeyError, AttributeError):
        dev_enum = InputDevice.KEYBOARD
    result = _input_map.process_raw_input(device=dev_enum, input_code=input_code, value=value)
    return {"events": result} if result else {"error": "Input processing failed"}

@router.get("/input-map/export-profile")
async def input_map_export_profile(profile_name: str = "", device: str = "keyboard"):
    result = _input_map.export_profile(profile_name=profile_name, device=device)
    return result if result else {"error": "Profile export failed"}


# ============================================================
# Animation Tree Endpoints
# ============================================================

@router.get("/animation-tree/stats")
async def animation_tree_stats():
    return _animation_tree.get_stats()

@router.post("/animation-tree/create-tree")
async def animation_tree_create_tree(name: str = "", skeleton_ref: str = ""):
    result = _animation_tree.create_tree(name=name, skeleton_ref=skeleton_ref)
    return result.to_dict() if result else {"error": "Tree creation failed"}

@router.post("/animation-tree/add-clip")
async def animation_tree_add_clip(tree_id: str = "", name: str = "", duration: float = 1.0, fps: float = 30.0):
    result = _animation_tree.add_clip(tree_id=tree_id, name=name, duration=duration, fps=fps)
    return result.to_dict() if result else {"error": "Add clip failed"}

@router.post("/animation-tree/create-blend-node")
async def animation_tree_create_blend_node(tree_id: str = "", parent_id: str = "", blend_mode: str = "linear"):
    result = _animation_tree.create_blend_node(tree_id=tree_id, parent_id=parent_id if parent_id else "", blend_mode=blend_mode)
    return result.to_dict() if result else {"error": "Blend node creation failed"}

@router.post("/animation-tree/add-transition")
async def animation_tree_add_transition(from_node_id: str = "", to_node_id: str = "", condition_type: str = "time", duration: float = 0.3):
    result = _animation_tree.add_transition(from_node_id=from_node_id, to_node_id=to_node_id, condition_type=condition_type, duration=duration)
    return result.to_dict() if result else {"error": "Transition add failed"}

@router.get("/animation-tree/play")
async def animation_tree_play(tree_id: str = "", start_node_id: str = ""):
    result = _animation_tree.play(tree_id=tree_id, start_node_id=start_node_id)
    return result if result else {"error": "Play failed"}

@router.get("/animation-tree/compute-pose")
async def animation_tree_compute_pose(tree_id: str = "", delta_time: float = 0.016):
    result = _animation_tree.compute_pose(tree_id=tree_id, delta_time=delta_time)
    return result if result else {"error": "Pose computation failed"}


# ============================================================
# Custom Object Types Endpoints
# ============================================================

@router.get("/custom-object-types/stats")
async def custom_object_types_stats():
    return _custom_object_types.get_stats()

@router.post("/custom-object-types/define-type")
async def custom_object_types_define_type(name: str = "", base_type: str = "sprite", description: str = "", parent_type_id: str = ""):
    result = _custom_object_types.define_type(name=name, base_type=base_type, description=description, parent_type_id=parent_type_id)
    return result.to_dict() if result else {"error": "Type definition failed"}

@router.post("/custom-object-types/add-property")
async def custom_object_types_add_property(type_id: str = "", name: str = "", property_type: str = "string", default_value: str = ""):
    import json as _json
    try:
        dv = _json.loads(default_value) if default_value else ""
    except (ValueError, TypeError):
        dv = default_value
    result = _custom_object_types.add_property(type_id=type_id, name=name, property_type=property_type, default_value=dv)
    return result.to_dict() if result else {"error": "Add property failed"}

@router.post("/custom-object-types/attach-behavior")
async def custom_object_types_attach_behavior(type_id: str = "", behavior_name: str = "", parameters: str = "{}"):
    import json as _json
    try:
        params = _json.loads(parameters) if parameters else {}
    except (ValueError, TypeError):
        params = {}
    result = _custom_object_types.attach_behavior(type_id=type_id, behavior_name=behavior_name, parameters=params)
    return result.to_dict() if result else {"error": "Attach behavior failed"}

@router.post("/custom-object-types/create-instance")
async def custom_object_types_create_instance(type_id: str = "", scene_id: str = ""):
    result = _custom_object_types.create_instance(type_id=type_id, scene_id=scene_id)
    return result.to_dict() if result else {"error": "Instance creation failed"}

@router.get("/custom-object-types/list-types")
async def custom_object_types_list_types(base_type: str = ""):
    types = _custom_object_types.list_types(base_type=base_type if base_type else None)
    return {"types": [t.to_dict() for t in types]}

@router.post("/custom-object-types/clone-type")
async def custom_object_types_clone_type(type_id: str = "", new_name: str = ""):
    result = _custom_object_types.clone_type(type_id=type_id, new_name=new_name)
    return result.to_dict() if result else {"error": "Clone failed"}


# ============================================================
# Tile Map Optimizer Endpoints
# ============================================================

@router.get("/tile-map-optimizer/stats")
async def tile_map_optimizer_stats():
    return _tile_map_optimizer.get_stats()

@router.post("/tile-map-optimizer/create-map")
async def tile_map_optimizer_create_map(name: str = "", width: int = 32, height: int = 32, tile_size: int = 32, orientation: str = "orthogonal"):
    result = _tile_map_optimizer.create_map(name=name, width=width, height=height, tile_size=tile_size, orientation=orientation)
    return result.to_dict() if result else {"error": "Map creation failed"}

@router.post("/tile-map-optimizer/add-layer")
async def tile_map_optimizer_add_layer(map_id: str = "", name: str = "", depth: int = 0, opacity: float = 1.0):
    result = _tile_map_optimizer.add_layer(map_id=map_id, name=name, depth=depth, opacity=opacity)
    return result.to_dict() if result else {"error": "Add layer failed"}

@router.post("/tile-map-optimizer/set-tile")
async def tile_map_optimizer_set_tile(map_id: str = "", layer_id: str = "", x: int = 0, y: int = 0, tile_id: int = 0):
    result = _tile_map_optimizer.set_tile(map_id=map_id, layer_id=layer_id, x=x, y=y, tile_id=tile_id)
    return {"success": result}

@router.post("/tile-map-optimizer/fill-region")
async def tile_map_optimizer_fill_region(map_id: str = "", layer_id: str = "", x1: int = 0, y1: int = 0, x2: int = 0, y2: int = 0, tile_id: int = 0):
    result = _tile_map_optimizer.fill_region(map_id=map_id, layer_id=layer_id, x1=x1, y1=y1, x2=x2, y2=y2, tile_id=tile_id)
    return {"filled_count": result}

@router.get("/tile-map-optimizer/partition-chunks")
async def tile_map_optimizer_partition_chunks(map_id: str = "", chunk_size: int = 16):
    result = _tile_map_optimizer.partition_chunks(map_id=map_id, chunk_size=chunk_size)
    return result if result else {"error": "Partition failed"}

@router.post("/tile-map-optimizer/optimize-atlas")
async def tile_map_optimizer_optimize_atlas(map_id: str = "", strategy: str = "pack", max_texture_size: int = 2048):
    result = _tile_map_optimizer.optimize_atlas(map_id=map_id, strategy=strategy, max_texture_size=max_texture_size)
    return result.to_dict() if result else {"error": "Atlas optimization failed"}

# ============================================================
# Chain of Thought Engine
# ============================================================

@router.post("/chain-of-thought/start-chain")
async def chain_of_thought_start_chain(question: str = "", context: str = "", agent_id: str = ""):
    if _chain_of_thought is None:
        return {"error": "Chain of Thought not initialized"}
    result = _chain_of_thought.start_chain(question=question, context=context, agent_id=agent_id)
    return result.to_dict() if result else {"error": "Start chain failed"}

@router.get("/chain-of-thought/stats")
async def chain_of_thought_stats():
    if _chain_of_thought is None:
        return {"error": "Chain of Thought not initialized"}
    return _chain_of_thought.get_stats()

# ============================================================
# Conversation Memory
# ============================================================

@router.post("/conversation-memory/start-thread")
async def conversation_memory_start_thread(agent_id: str = "", title: str = "", system_prompt: str = ""):
    if _conversation_memory is None:
        return {"error": "Conversation Memory not initialized"}
    result = _conversation_memory.start_thread(agent_id=agent_id, title=title, system_prompt=system_prompt)
    return result.to_dict() if result else {"error": "Start thread failed"}

@router.get("/conversation-memory/stats")
async def conversation_memory_stats():
    if _conversation_memory is None:
        return {"error": "Conversation Memory not initialized"}
    return _conversation_memory.get_stats()

# ============================================================
# Self Optimization
# ============================================================

@router.post("/self-optimization/create-profile")
async def self_optimization_create_profile(agent_id: str = "", targets: str = "[]"):
    if _self_optimization is None:
        return {"error": "Self Optimization not initialized"}
    import json as _json
    try:
        targets_list = _json.loads(targets) if targets else []
    except (ValueError, TypeError):
        targets_list = []
    result = _self_optimization.create_profile(agent_id=agent_id, targets=targets_list)
    return result.to_dict() if result else {"error": "Create profile failed"}

@router.get("/self-optimization/stats")
async def self_optimization_stats():
    if _self_optimization is None:
        return {"error": "Self Optimization not initialized"}
    return _self_optimization.get_stats()

# ============================================================
# Collaboration Protocol
# ============================================================

@router.post("/collaboration-protocol/propose-collaboration")
async def collaboration_protocol_propose_collaboration(initiator_id: str = "", task_description: str = "", required_roles: str = "[]"):
    if _collaboration_protocol is None:
        return {"error": "Collaboration Protocol not initialized"}
    import json as _json
    try:
        roles = _json.loads(required_roles) if required_roles else []
    except (ValueError, TypeError):
        roles = []
    result = _collaboration_protocol.propose_collaboration(initiator_id=initiator_id, task_description=task_description, required_roles=roles)
    return result.to_dict() if result else {"error": "Propose collaboration failed"}

@router.get("/collaboration-protocol/stats")
async def collaboration_protocol_stats():
    if _collaboration_protocol is None:
        return {"error": "Collaboration Protocol not initialized"}
    return _collaboration_protocol.get_stats()

# ============================================================
# Knowledge Synthesis
# ============================================================

@router.post("/knowledge-synthesis/ingest-fragment")
async def knowledge_synthesis_ingest_fragment(source_agent: str = "", content: str = "", domain: str = "game_design", confidence: str = "medium", tags: str = "[]"):
    if _knowledge_synthesis is None:
        return {"error": "Knowledge Synthesis not initialized"}
    import json as _json
    try:
        tags_list = _json.loads(tags) if tags else []
    except (ValueError, TypeError):
        tags_list = []
    result = _knowledge_synthesis.ingest_fragment(source_agent=source_agent, content=content, domain=domain, confidence=confidence, tags=tags_list)
    return result.to_dict() if result else {"error": "Ingest fragment failed"}

@router.get("/knowledge-synthesis/stats")
async def knowledge_synthesis_stats():
    if _knowledge_synthesis is None:
        return {"error": "Knowledge Synthesis not initialized"}
    return _knowledge_synthesis.get_stats()

# ============================================================
# Capability Registry
# ============================================================

@router.post("/capability-registry/register-capability")
async def capability_registry_register_capability(agent_id: str = "", name: str = "", cap_type: str = "generation", proficiency: str = "competent", scope: str = "local"):
    if _capability_registry is None:
        return {"error": "Capability Registry not initialized"}
    result = _capability_registry.register_capability(agent_id=agent_id, name=name, cap_type=cap_type, proficiency=proficiency, scope=scope)
    return result.to_dict() if result else {"error": "Register capability failed"}

@router.get("/capability-registry/stats")
async def capability_registry_stats():
    if _capability_registry is None:
        return {"error": "Capability Registry not initialized"}
    return _capability_registry.get_stats()

# ============================================================
# Physics Material Library
# ============================================================

@router.post("/physics-material/define-material")
async def physics_material_define_material(name: str = "", surface_type: str = "stone", density: float = 1.0, friction: float = 0.5, restitution: float = 0.3):
    if _physics_material is None:
        return {"error": "Physics Material not initialized"}
    result = _physics_material.define_material(name=name, surface_type=surface_type, density=density, friction=friction, restitution=restitution)
    return result.to_dict() if result else {"error": "Define material failed"}

@router.get("/physics-material/stats")
async def physics_material_stats():
    if _physics_material is None:
        return {"error": "Physics Material not initialized"}
    return _physics_material.get_stats()

# ============================================================
# Gesture Recognizer
# ============================================================

@router.post("/gesture-recognizer/register-pattern")
async def gesture_recognizer_register_pattern(name: str = "", gesture_type: str = "tap", min_points: int = 1, max_points: int = 10):
    if _gesture_recognizer is None:
        return {"error": "Gesture Recognizer not initialized"}
    result = _gesture_recognizer.register_pattern(name=name, gesture_type=gesture_type, min_points=min_points, max_points=max_points)
    return result.to_dict() if result else {"error": "Register pattern failed"}

@router.get("/gesture-recognizer/stats")
async def gesture_recognizer_stats():
    if _gesture_recognizer is None:
        return {"error": "Gesture Recognizer not initialized"}
    return _gesture_recognizer.get_stats()

# ============================================================
# Shadow Casting
# ============================================================

@router.post("/shadow-casting/add-light")
async def shadow_casting_add_light(name: str = "", light_type: str = "point", x: float = 0.0, y: float = 0.0, intensity: float = 1.0, radius: float = 200.0):
    if _shadow_casting is None:
        return {"error": "Shadow Casting not initialized"}
    result = _shadow_casting.add_light(name=name, light_type=light_type, position=(x, y), intensity=intensity, radius=radius)
    return result.to_dict() if result else {"error": "Add light failed"}

@router.get("/shadow-casting/stats")
async def shadow_casting_stats():
    if _shadow_casting is None:
        return {"error": "Shadow Casting not initialized"}
    return _shadow_casting.get_stats()

# ============================================================
# Entity Blueprint
# ============================================================

@router.post("/entity-blueprint/create-blueprint")
async def entity_blueprint_create_blueprint(name: str = "", category: str = "character", description: str = ""):
    if _entity_blueprint is None:
        return {"error": "Entity Blueprint not initialized"}
    result = _entity_blueprint.create_blueprint(name=name, category=category, description=description)
    return result.to_dict() if result else {"error": "Create blueprint failed"}

@router.get("/entity-blueprint/stats")
async def entity_blueprint_stats():
    if _entity_blueprint is None:
        return {"error": "Entity Blueprint not initialized"}
    return _entity_blueprint.get_stats()

# ============================================================
# Scene Transition
# ============================================================

@router.post("/scene-transition/configure-transition")
async def scene_transition_configure_transition(from_scene: str = "", to_scene: str = "", effect: str = "fade", duration: float = 0.5, easing: str = "ease_in_out"):
    if _scene_transition is None:
        return {"error": "Scene Transition not initialized"}
    result = _scene_transition.configure_transition(from_scene=from_scene, to_scene=to_scene, effect=effect, duration=duration, easing=easing)
    return result.to_dict() if result else {"error": "Configure transition failed"}

@router.get("/scene-transition/stats")
async def scene_transition_stats():
    if _scene_transition is None:
        return {"error": "Scene Transition not initialized"}
    return _scene_transition.get_stats()

# ============================================================
# Audio Layering
# ============================================================

@router.post("/audio-layering/create-layer")
async def audio_layering_create_layer(name: str = "", layer_type: str = "music", volume: float = 1.0, pan: float = 0.0, pitch: float = 1.0):
    if _audio_layering is None:
        return {"error": "Audio Layering not initialized"}
    result = _audio_layering.create_layer(name=name, layer_type=layer_type, volume=volume, pan=pan, pitch=pitch)
    return result.to_dict() if result else {"error": "Create layer failed"}

@router.get("/audio-layering/stats")
async def audio_layering_stats():
    if _audio_layering is None:
        return {"error": "Audio Layering not initialized"}
    return _audio_layering.get_stats()

# ============================================================
# Experiment Framework Endpoints
# ============================================================

@router.get("/experiment-framework/stats")
async def experiment_framework_stats():
    return _experiment_framework.get_stats()

@router.post("/experiment-framework/create-experiment")
async def experiment_framework_create_experiment(name: str = "", variant_count: int = 2, metrics: str = "", strategy: str = "round_robin"):
    import json as _json
    variants = []
    for i in range(variant_count):
        variants.append({"name": f"Variant {chr(65+i)}", "description": f"Experiment variant {chr(65+i)}", "parameters": {"temperature": 0.5 + i * 0.2}})
    metric_names = [m.strip() for m in metrics.split(",") if m.strip()] if metrics else ["latency", "accuracy"]
    cfg = _experiment_framework.create_experiment(name=name, variants=variants, metrics=metric_names, strategy=strategy)
    return cfg.to_dict() if cfg else {"error": "Experiment creation failed"}

@router.post("/experiment-framework/start-experiment")
async def experiment_framework_start_experiment(experiment_id: str = ""):
    return {"started": _experiment_framework.start_experiment(experiment_id)}

@router.post("/experiment-framework/record-trial")
async def experiment_framework_record_trial(experiment_id: str = "", variant_id: str = "", prompt: str = "", response: str = "", latency_ms: float = 0, token_usage: int = 0, success: bool = True):
    metrics = {"latency_ms": latency_ms, "token_usage": token_usage}
    tags = {"prompt": prompt[:50], "response": response[:50]}
    result = _experiment_framework.record_trial(experiment_id=experiment_id, variant_id=variant_id, metrics=metrics, tags=tags, success=success)
    return result.to_dict() if result else {"error": "Trial recording failed"}

@router.post("/experiment-framework/compute-results")
async def experiment_framework_compute_results(experiment_id: str = ""):
    report = _experiment_framework.compute_results(experiment_id)
    return report.to_dict() if report else {"error": "Computation failed"}

@router.get("/experiment-framework/list-experiments")
async def experiment_framework_list_experiments(status: str = ""):
    experiments = _experiment_framework.list_experiments(status=status)
    return {"experiments": [e.to_dict() for e in experiments]}

# ============================================================
# Telemetry Pipeline Endpoints
# ============================================================

@router.get("/telemetry-pipeline/stats")
async def telemetry_pipeline_stats():
    return _telemetry_pipeline.get_stats()

@router.post("/telemetry-pipeline/register-sink")
async def telemetry_pipeline_register_sink(name: str = "", sink_type: str = "stdout", endpoint: str = "", format_type: str = "json"):
    config = {"url": endpoint} if endpoint else {}
    sink = _telemetry_pipeline.register_sink(name=name, sink_type=sink_type, config=config, format_type=format_type)
    return sink.to_dict() if sink else {"error": "Sink registration failed"}

@router.post("/telemetry-pipeline/emit-metric")
async def telemetry_pipeline_emit_metric(agent_id: str = "", name: str = "", value: float = 0, unit: str = "", tags: str = ""):
    import json as _json
    try:
        tag_dict = _json.loads(tags) if tags else {}
    except (ValueError, TypeError):
        tag_dict = {}
    _telemetry_pipeline.emit_metric(agent_id=agent_id, metric_name=name, value=value, tags=tag_dict)
    return {"emitted": True}

@router.post("/telemetry-pipeline/flush-sink")
async def telemetry_pipeline_flush_sink(sink_id: str = ""):
    count = _telemetry_pipeline.flush_sink(sink_id)
    return {"flushed": count}

@router.get("/telemetry-pipeline/throughput")
async def telemetry_pipeline_throughput():
    return {"throughput": _telemetry_pipeline.get_throughput()}

# ============================================================
# Audit Trail Endpoints
# ============================================================

@router.get("/audit-trail/stats")
async def audit_trail_stats():
    return _audit_trail.get_stats()

@router.post("/audit-trail/log-event")
async def audit_trail_log_event(agent_id: str = "", event_type: str = "action_executed", description: str = "", details: str = "", severity: str = "info"):
    import json as _json
    from sparkai.agent.agent_audit_trail import AuditEventType, SeverityLevel
    try:
        et = AuditEventType(event_type)
    except ValueError:
        et = AuditEventType.ACTION_EXECUTED
    try:
        sv = SeverityLevel(severity)
    except ValueError:
        sv = SeverityLevel.INFO
    try:
        detail_dict = _json.loads(details) if details else {}
    except (ValueError, TypeError):
        detail_dict = {}
    entry = _audit_trail.log_event(agent_id=agent_id, event_type=et, description=description, severity=sv, metadata=detail_dict)
    return entry.to_dict() if entry else {"error": "Event logging failed"}

@router.get("/audit-trail/query")
async def audit_trail_query(agent_id: str = "", event_type: str = "", limit: int = 50):
    entries = _audit_trail.query_trail(agent_id=agent_id, event_type=event_type, limit=limit)
    return {"entries": [e.to_dict() for e in entries]}

@router.post("/audit-trail/generate-report")
async def audit_trail_generate_report(time_range_days: int = 7):
    report = _audit_trail.generate_report(time_range_days=time_range_days)
    return report.to_dict()

# ============================================================
# Journal System Endpoints
# ============================================================

@router.get("/journal-system/stats")
async def journal_system_stats():
    return _journal_system.get_stats()

@router.post("/journal-system/create-entry")
async def journal_system_create_entry(agent_id: str = "", title: str = "", content: str = "", entry_type: str = "reflection", mood: str = "neutral", tags: str = ""):
    import json as _json
    from sparkai.agent.agent_journal_system import JournalEntryType, MoodTone
    try:
        et = JournalEntryType(entry_type)
    except ValueError:
        et = JournalEntryType.REFLECTION
    try:
        mt = MoodTone(mood)
    except ValueError:
        mt = MoodTone.NEUTRAL
    try:
        tag_list = _json.loads(tags) if tags else []
    except (ValueError, TypeError):
        tag_list = []
    entry = _journal_system.create_entry(agent_id=agent_id, entry_type=et, content=content or title, mood=mt, tags=tag_list)
    return entry.to_dict() if entry else {"error": "Entry creation failed"}

@router.get("/journal-system/search")
async def journal_system_search(query: str = "", agent_id: str = "", limit: int = 20):
    entries = _journal_system.search_entries(query=query, agent_id=agent_id, limit=limit)
    return {"entries": [e.to_dict() for e in entries]}

@router.post("/journal-system/summarize")
async def journal_system_summarize(agent_id: str = "", days: int = 7):
    summary = _journal_system.summarize_journal(agent_id=agent_id, days=days)
    return summary.to_dict() if summary else {"error": "Summarization failed"}

# ============================================================
# Document Synthesizer Endpoints
# ============================================================

@router.get("/document-synthesizer/stats")
async def document_synthesizer_stats():
    return _document_synthesizer.get_stats()

@router.post("/document-synthesizer/create-template")
async def document_synthesizer_create_template(name: str = "", doc_type: str = "gdd", format: str = "markdown"):
    template = _document_synthesizer.create_template(name=name, doc_type=doc_type)
    return template.to_dict() if template else {"error": "Template creation failed"}

@router.post("/document-synthesizer/synthesize")
async def document_synthesizer_synthesize(template_id: str = "", title: str = "", content_data: str = ""):
    import json as _json
    try:
        data = _json.loads(content_data) if content_data else {}
    except (ValueError, TypeError):
        data = {}
    doc = _document_synthesizer.synthesize_from_workflow(template_id=template_id, title=title, content_data=data)
    return doc.to_dict() if doc else {"error": "Synthesis failed"}

@router.get("/document-synthesizer/render")
async def document_synthesizer_render(document_id: str = "", format: str = "markdown"):
    from sparkai.agent.agent_document_synthesizer import DocumentFormat
    try:
        df = DocumentFormat(format)
    except ValueError:
        df = DocumentFormat.MARKDOWN
    result = _document_synthesizer.render_document(document_id=document_id, format=df)
    return result if result else {"error": "Render failed"}

# ============================================================
# Simulation Runner Endpoints
# ============================================================

@router.get("/simulation-runner/stats")
async def simulation_runner_stats():
    return _simulation_runner.get_stats()

@router.post("/simulation-runner/define-scenario")
async def simulation_runner_define_scenario(name: str = "", description: str = "", mode: str = "single_run"):
    import json as _json
    try:
        agent_config = _json.loads(description) if description else {}
    except (ValueError, TypeError):
        agent_config = {}
    scenario = _simulation_runner.define_scenario(name=name, agent_config=agent_config)
    return scenario.to_dict() if scenario else {"error": "Scenario definition failed"}

@router.post("/simulation-runner/run")
async def simulation_runner_run(scenario_id: str = "", agent_id: str = "", input_data: str = "", mode: str = "single_run", repeat_count: int = 1):
    run = _simulation_runner.run_simulation(scenario_id=scenario_id, mode=mode, repeat_count=repeat_count)
    return run.to_dict() if run else {"error": "Simulation run failed"}

@router.get("/simulation-runner/list-runs")
async def simulation_runner_list_runs(scenario_id: str = ""):
    runs = _simulation_runner.list_runs(scenario_id=scenario_id)
    return {"runs": [r.to_dict() for r in runs]}

@router.get("/simulation-runner/evaluate")
async def simulation_runner_evaluate(run_id: str = ""):
    report = _simulation_runner.evaluate_results(run_id)
    return report.to_dict() if report else {"error": "Evaluation failed"}

# ============================================================
# Material Graph Endpoints
# ============================================================

@router.get("/material-graph/stats")
async def material_graph_stats():
    return _material_graph.get_stats()

@router.post("/material-graph/create-graph")
async def material_graph_create_graph(name: str = "", description: str = ""):
    graph = _material_graph.create_graph(name=name, description=description)
    return graph.to_dict() if graph else {"error": "Graph creation failed"}

@router.post("/material-graph/add-node")
async def material_graph_add_node(graph_id: str = "", node_type: str = "color_constant", x: float = 0, y: float = 0):
    node = _material_graph.add_node(graph_id=graph_id, node_type=node_type, position=(x, y))
    return node.to_dict() if node else {"error": "Node addition failed"}

@router.post("/material-graph/connect-nodes")
async def material_graph_connect_nodes(graph_id: str = "", source_node_id: str = "", source_port: str = "output", target_node_id: str = "", target_port: str = "input"):
    conn = _material_graph.connect_nodes(graph_id=graph_id, from_node_id=source_node_id, from_port=source_port, to_node_id=target_node_id, to_port=target_port)
    return conn.to_dict() if conn else {"error": "Connection failed"}

@router.get("/material-graph/compile-shader")
async def material_graph_compile_shader(graph_id: str = "", target: str = "glsl"):
    shader = _material_graph.compile_shader(graph_id=graph_id, target=target)
    return shader.to_dict() if shader else {"error": "Shader compilation failed"}

# ============================================================
# Occlusion Culling Endpoints
# ============================================================

@router.get("/occlusion-culling/stats")
async def occlusion_culling_stats():
    return _occlusion_culling.get_stats()

@router.post("/occlusion-culling/register-occluder")
async def occlusion_culling_register_occluder(entity_id: str = "", x: float = 0, y: float = 0, z: float = 0, width: float = 1, height: float = 1, depth: float = 1, occluder_type: str = "box"):
    bounds = {"x": x, "y": y, "z": z, "width": width, "height": height, "depth": depth}
    occluder = _occlusion_culling.register_occluder(entity_id=entity_id, occluder_type=occluder_type, bounds=bounds)
    return occluder.to_dict() if occluder else {"error": "Occluder registration failed"}

@router.post("/occlusion-culling/update-camera")
async def occlusion_culling_update_camera(camera_id: str = "", x: float = 0, y: float = 0, z: float = 0, dir_x: float = 0, dir_y: float = 0, dir_z: float = -1, fov: float = 60):
    camera = _occlusion_culling.update_camera(camera_id=camera_id, position=(x, y, z), direction=(dir_x, dir_y, dir_z), fov=fov)
    return camera.to_dict() if camera else {"error": "Camera update failed"}

@router.get("/occlusion-culling/query")
async def occlusion_culling_query(camera_id: str = ""):
    visible = _occlusion_culling.get_visible_entities(camera_id)
    return {"visible": visible}

# ============================================================
# LOD System Endpoints
# ============================================================

@router.get("/lod-system/stats")
async def lod_system_stats():
    return _lod_system.get_stats()

@router.post("/lod-system/create-group")
async def lod_system_create_group(entity_id: str = ""):
    group = _lod_system.create_lod_group(entity_id=entity_id)
    return group.to_dict() if group else {"error": "LOD group creation failed"}

@router.post("/lod-system/add-level")
async def lod_system_add_level(group_id: str = "", level: str = "LOD0_ULTRA", mesh_ref: str = "", distance_threshold: float = 50):
    entry = _lod_system.add_lod_level(group_id=group_id, level=level, mesh_ref=mesh_ref, distance_threshold=distance_threshold)
    return entry.to_dict() if entry else {"error": "LOD level addition failed"}

@router.get("/lod-system/evaluate")
async def lod_system_evaluate(entity_id: str = "", camera_distance: float = 0):
    result = _lod_system.evaluate_lod(entity_id=entity_id, camera_distance=camera_distance)
    return result if result else {"error": "Evaluation failed"}

# ============================================================
# Decal System Endpoints
# ============================================================

@router.get("/decal-system/stats")
async def decal_system_stats():
    return _decal_system.get_stats()

@router.post("/decal-system/create-projector")
async def decal_system_create_projector(name: str = "", width: float = 1, height: float = 1, projection: str = "planar"):
    projector = _decal_system.create_projector(name=name, projection=projection, size=(width, height))
    return projector.to_dict() if projector else {"error": "Projector creation failed"}

@router.post("/decal-system/place-decal")
async def decal_system_place_decal(projector_id: str = "", x: float = 0, y: float = 0, z: float = 0):
    instance = _decal_system.place_decal(projector_id=projector_id, position=(x, y, z))
    return instance.to_dict() if instance else {"error": "Decal placement failed"}

@router.post("/decal-system/gather-batch")
async def decal_system_gather_batch(camera_x: float = 0, camera_y: float = 0, camera_z: float = 0, max_distance: float = 100):
    batch = _decal_system.gather_batch(camera_position=(camera_x, camera_y, camera_z), max_count=int(max_distance))
    return batch.to_dict() if batch else {"error": "Batch gathering failed"}

# ============================================================
# Post Processing Endpoints
# ============================================================

@router.get("/post-processing/stats")
async def post_processing_stats():
    return _post_processing_engine.get_stats()

@router.post("/post-processing/add-effect")
async def post_processing_add_effect(name: str = "", effect_type: str = "bloom", enabled: bool = True, quality: str = "high"):
    effect = _post_processing_engine.add_effect(effect_type=effect_type, quality=quality)
    return effect.to_dict() if effect else {"error": "Effect addition failed"}

@router.post("/post-processing/create-chain")
async def post_processing_create_chain(name: str = ""):
    chain = _post_processing_engine.create_chain(name=name)
    return chain.to_dict() if chain else {"error": "Chain creation failed"}

@router.post("/post-processing/create-profile")
async def post_processing_create_profile(name: str = "", description: str = ""):
    profile = _post_processing_engine.create_profile(name=name)
    return profile.to_dict() if profile else {"error": "Profile creation failed"}

@router.post("/post-processing/apply-profile")
async def post_processing_apply_profile(profile_id: str = ""):
    return {"applied": _post_processing_engine.apply_profile(profile_id)}

# ============================================================
# Skeleton Deformer Endpoints
# ============================================================

@router.get("/skeleton-deformer/stats")
async def skeleton_deformer_stats():
    return _skeleton_deformer.get_stats()

@router.post("/skeleton-deformer/create-skeleton")
async def skeleton_deformer_create_skeleton(name: str = "", x: float = 0, y: float = 0, z: float = 0):
    skeleton = _skeleton_deformer.create_skeleton(name=name, root_position=(x, y, z))
    return skeleton.to_dict() if skeleton else {"error": "Skeleton creation failed"}

@router.post("/skeleton-deformer/add-joint")
async def skeleton_deformer_add_joint(skeleton_id: str = "", name: str = "", joint_type: str = "hinge", parent_id: str = "", x: float = 0, y: float = 0, z: float = 0):
    joint = _skeleton_deformer.add_joint(
        skeleton_id=skeleton_id,
        name=name,
        parent_id=parent_id,
        joint_type=joint_type,
        local_transform={"position": [x, y, z]},
    )
    return joint.to_dict() if joint else {"error": "Joint addition failed"}

@router.post("/skeleton-deformer/compute-pose")
async def skeleton_deformer_compute_pose(skeleton_id: str = ""):
    pose = _skeleton_deformer.compute_pose(skeleton_id)
    return pose.to_dict() if pose else {"error": "Pose computation failed"}

@router.post("/skeleton-deformer/deform-mesh")
async def skeleton_deformer_deform_mesh(skeleton_id: str = "", mesh_id: str = ""):
    result = _skeleton_deformer.deform_mesh(skeleton_id=skeleton_id, mesh_id=mesh_id)
    return result.to_dict() if result else {"error": "Mesh deformation failed"}

# ============================================================
# Agentic Coding Endpoints
# ============================================================

@router.get("/agentic-coding/stats")
async def agentic_coding_stats():
    try:
        return _agentic_coding.get_stats()
    except Exception as e:
        return {"error": str(e)}

@router.post("/agentic-coding/start-session")
async def agentic_coding_start_session(request: Request):
    try:
        import json
        body = await request.json()
        task = body.get("task", "generate_script")
        language = body.get("language", "sparkscript")
        context = body.get("context", {})
        if isinstance(context, str):
            context = json.loads(context) if context else {}
        try:
            ct = CodingTask(task)
        except ValueError:
            ct = CodingTask.GENERATE_SCRIPT
        try:
            cl = AgenticCodeLanguage(language)
        except ValueError:
            cl = AgenticCodeLanguage.SparkScript
        session = _agentic_coding.start_coding_session(task=ct, language=cl, context=context)
        result = session.to_dict()
        print("DEBUG agentic_coding result type:", type(result), "keys:", list(result.keys()) if isinstance(result, dict) else "NOT DICT")
        return result
    except Exception as e:
        import traceback
        traceback.print_exc()
        return {"error": str(e)}

@router.post("/agentic-coding/generate-code")
async def agentic_coding_generate_code(request: Request):
    try:
        body = await request.json()
        session_id = body.get("session_id", "")
        specification = body.get("specification", "")
        artifact = _agentic_coding.generate_code(session_id=session_id, specification=specification)
        return artifact.to_dict() if artifact else {"error": "Code generation failed"}
    except Exception as e:
        return {"error": str(e)}

@router.post("/agentic-coding/compile-test")
async def agentic_coding_compile_test(request: Request):
    try:
        body = await request.json()
        session_id = body.get("session_id", "")
        artifact_id = body.get("artifact_id", "")
        artifact = _agentic_coding.compile_and_test(session_id=session_id, artifact_id=artifact_id)
        return artifact.to_dict() if artifact else {"error": "Compilation/test failed"}
    except Exception as e:
        return {"error": str(e)}

@router.post("/agentic-coding/auto-fix")
async def agentic_coding_auto_fix(request: Request):
    try:
        body = await request.json()
        session_id = body.get("session_id", "")
        artifact_id = body.get("artifact_id", "")
        error_log = body.get("error_log", "")
        artifact = _agentic_coding.auto_fix(session_id=session_id, artifact_id=artifact_id, error_log=error_log)
        return artifact.to_dict() if artifact else {"error": "Auto-fix failed"}
    except Exception as e:
        return {"error": str(e)}

@router.get("/agentic-coding/session-summary")
async def agentic_coding_session_summary(session_id: str = ""):
    try:
        summary = _agentic_coding.get_session_summary(session_id)
        return summary.to_dict() if summary else {"error": "Session not found"}
    except Exception as e:
        return {"error": str(e)}

# ============================================================
# Game Reasoner Endpoints
# ============================================================

@router.get("/game-reasoner/stats")
async def game_reasoner_stats():
    try:
        return _game_reasoner.get_stats()
    except Exception as e:
        return {"error": str(e)}

@router.post("/game-reasoner/analyze-design")
async def game_reasoner_analyze_design(request: Request):
    try:
        import json
        body = await request.json()
        game_state = body.get("game_state", {})
        if isinstance(game_state, str):
            game_state = json.loads(game_state) if game_state else {}
        aspects = body.get("aspects", "")
        aspect_list = aspects.split(",") if aspects else None
        results = _game_reasoner.analyze_game_design(game_state=game_state, aspects=aspect_list)
        return [r.to_dict() for r in results]
    except Exception as e:
        return {"error": str(e)}

@router.post("/game-reasoner/suggest-balancing")
async def game_reasoner_suggest_balancing(request: Request):
    try:
        body = await request.json()
        parameter_name = body.get("parameter_name", "")
        current_value = body.get("current_value", 0.0)
        target_experience = body.get("target_experience", "")
        suggestions = _game_reasoner.suggest_balancing(
            parameter_name=parameter_name,
            current_value=current_value,
            target_experience=target_experience,
        )
        return [s.to_dict() for s in suggestions]
    except Exception as e:
        return {"error": str(e)}

@router.post("/game-reasoner/model-curve")
async def game_reasoner_model_curve(request: Request):
    try:
        import json
        body = await request.json()
        curve_name = body.get("curve_name", "")
        data_points = body.get("data_points", [])
        if isinstance(data_points, str):
            data_points = json.loads(data_points) if data_points else []
        target_shape = body.get("target_shape", "linear")
        pts = [(float(p[0]), float(p[1])) for p in data_points]
        curve = _game_reasoner.model_progression_curve(
            curve_name=curve_name, data_points=pts, target_shape=target_shape,
        )
        return curve.to_dict() if hasattr(curve, "to_dict") else curve
    except Exception as e:
        return {"error": str(e)}

@router.post("/game-reasoner/evaluate-difficulty")
async def game_reasoner_evaluate_difficulty(request: Request):
    try:
        import json
        body = await request.json()
        game_state = body.get("game_state", {})
        if isinstance(game_state, str):
            game_state = json.loads(game_state) if game_state else {}
        player_skill = body.get("player_skill", 0.5)
        analysis = _game_reasoner.evaluate_difficulty(game_state=game_state, player_skill=player_skill)
        return analysis.to_dict() if hasattr(analysis, "to_dict") else analysis
    except Exception as e:
        return {"error": str(e)}

# ============================================================
# Narrative Branch Endpoints
# ============================================================

@router.get("/narrative-branch/stats")
async def narrative_branch_stats():
    try:
        return _narrative_branch.get_stats()
    except Exception as e:
        return {"error": str(e)}

@router.post("/narrative-branch/create-branch")
async def narrative_branch_create(request: Request):
    try:
        body = await request.json()
        name = body.get("name", "")
        strategy = body.get("strategy", "binary")
        root_content = body.get("root_content", "")
        branch = _narrative_branch.create_branch(name=name, strategy=strategy, root_content=root_content)
        return branch.to_dict() if branch else {"error": "Branch creation failed"}
    except Exception as e:
        return {"error": str(e)}

@router.post("/narrative-branch/add-node")
async def narrative_branch_add_node(request: Request):
    try:
        body = await request.json()
        branch_id = body.get("branch_id", "")
        node_type = body.get("node_type", "dialogue")
        content = body.get("content", "")
        parent_node_ids = body.get("parent_node_ids", "")
        choices = body.get("choices", "")
        parent_ids = parent_node_ids.split(",") if parent_node_ids else None
        choice_list = choices.split(",") if choices else None
        node = _narrative_branch.add_node(
            branch_id=branch_id, node_type=node_type, content=content,
            parent_node_ids=parent_ids, choices=choice_list,
        )
        return node.to_dict() if node else {"error": "Node addition failed"}
    except Exception as e:
        return {"error": str(e)}

@router.post("/narrative-branch/check-consistency")
async def narrative_branch_check_consistency(request: Request):
    try:
        body = await request.json()
        branch_id = body.get("branch_id", "")
        level = body.get("level", "strict")
        report = _narrative_branch.check_consistency(branch_id=branch_id, level=level)
        return report.to_dict() if report else {"error": "Branch not found"}
    except Exception as e:
        return {"error": str(e)}

@router.post("/narrative-branch/generate-character")
async def narrative_branch_generate_character(request: Request):
    try:
        body = await request.json()
        name = body.get("name", "")
        role = body.get("role", "neutral")
        traits = body.get("traits", "")
        trait_list = traits.split(",") if traits else None
        profile = _narrative_branch.generate_character(name=name, role=role, traits=trait_list)
        return profile.to_dict() if hasattr(profile, "to_dict") else profile
    except Exception as e:
        return {"error": str(e)}

# ============================================================
# Concurrency Manager Endpoints
# ============================================================

@router.get("/concurrency-manager/stats")
async def concurrency_manager_stats():
    try:
        return _concurrency_manager.get_stats()
    except Exception as e:
        return {"error": str(e)}

@router.post("/concurrency-manager/create-queue")
async def concurrency_manager_create_queue(request: Request):
    try:
        body = await request.json()
        name = body.get("name", "")
        strategy = body.get("strategy", "parallel")
        max_concurrent = body.get("max_concurrent", 10)
        queue = _concurrency_manager.create_queue(name=name, strategy=strategy, max_concurrent=max_concurrent)
        return queue.to_dict() if hasattr(queue, "to_dict") else queue
    except Exception as e:
        return {"error": str(e)}

@router.post("/concurrency-manager/enqueue-task")
async def concurrency_manager_enqueue(request: Request):
    try:
        import json
        body = await request.json()
        queue_id = body.get("queue_id", "")
        agent_id = body.get("agent_id", "")
        task_type = body.get("task_type", "")
        payload = body.get("payload", {})
        if isinstance(payload, str):
            payload = json.loads(payload) if payload else {}
        priority = body.get("priority", "normal")
        timeout_seconds = body.get("timeout_seconds", 60.0)
        task = _concurrency_manager.enqueue_task(
            queue_id=queue_id, agent_id=agent_id, task_type=task_type,
            payload=payload, priority=priority, timeout_seconds=timeout_seconds,
        )
        return task.to_dict() if task else {"error": "Enqueue failed"}
    except Exception as e:
        return {"error": str(e)}

@router.post("/concurrency-manager/execute-task")
async def concurrency_manager_execute(request: Request):
    try:
        body = await request.json()
        task_id = body.get("task_id", "")
        task = _concurrency_manager.execute_task(task_id)
        return task.to_dict() if task else {"error": "Task not found"}
    except Exception as e:
        return {"error": str(e)}

@router.get("/concurrency-manager/queue-stats")
async def concurrency_manager_queue_stats(queue_id: str = ""):
    try:
        stats = _concurrency_manager.get_queue_stats(queue_id)
        return stats if stats else {"error": "Queue not found"}
    except Exception as e:
        return {"error": str(e)}

# ============================================================
# Verification Pipeline Endpoints
# ============================================================

@router.get("/verification-pipeline/stats")
async def verification_pipeline_stats():
    try:
        return _verification_pipeline.get_stats()
    except Exception as e:
        return {"error": str(e)}

@router.post("/verification-pipeline/verify-artifact")
async def verification_pipeline_verify(request: Request):
    try:
        body = await request.json()
        artifact_id = body.get("artifact_id", "")
        artifact_content = body.get("artifact_content", "")
        artifact_type = body.get("artifact_type", "sparkscript")
        config_id = body.get("config_id", "")
        report = _verification_pipeline.verify_artifact(
            artifact_id=artifact_id, artifact_content=artifact_content,
            artifact_type=artifact_type, config_id=config_id,
        )
        return report.to_dict() if report else {"error": "Verification failed"}
    except Exception as e:
        return {"error": str(e)}

@router.post("/verification-pipeline/add-rule")
async def verification_pipeline_add_rule(request: Request):
    try:
        from sparkai.agent.agent_verification_pipeline import VerificationStage, Severity, CheckType
        body = await request.json()
        config_id = body.get("config_id", "")
        stage = body.get("stage", "syntax_check")
        rule_name = body.get("rule_name", "")
        condition = body.get("condition", "")
        severity = body.get("severity", "warning")
        try:
            vs = VerificationStage(stage)
        except ValueError:
            vs = VerificationStage.SYNTAX_CHECK
        try:
            sv = Severity(severity)
        except ValueError:
            sv = Severity.WARNING

        if not config_id:
            config = _verification_pipeline.create_pipeline_config(
                "default", list(VerificationStage)
            )
            config_id = config.id

        try:
            ct = CheckType.STATIC_ANALYSIS
        except ValueError:
            ct = CheckType.STATIC_ANALYSIS

        rule = _verification_pipeline.add_rule(
            config_id=config_id, stage=vs, rule_name=rule_name,
            condition=condition, severity=sv, check_type=ct,
        )
        return rule.to_dict() if rule else {"error": "Rule addition failed"}
    except Exception as e:
        return {"error": str(e)}

@router.post("/verification-pipeline/auto-fix")
async def verification_pipeline_auto_fix(request: Request):
    try:
        body = await request.json()
        report_id = body.get("report_id", "")
        report = _verification_pipeline.auto_fix_issues(report_id)
        return report.to_dict() if report else {"error": "Auto-fix failed"}
    except Exception as e:
        return {"error": str(e)}

@router.get("/verification-pipeline/blocking-issues")
async def verification_pipeline_blocking_issues(report_id: str = ""):
    try:
        issues = _verification_pipeline.get_blocking_issues(report_id)
        return [i.to_dict() for i in issues]
    except Exception as e:
        return {"error": str(e)}

# ============================================================
# Playtest Simulator Endpoints
# ============================================================

@router.get("/playtest-simulator/stats")
async def playtest_simulator_stats():
    try:
        return _playtest_simulator.get_stats()
    except Exception as e:
        return {"error": str(e)}

@router.post("/playtest-simulator/start-session")
async def playtest_simulator_start_session(request: Request):
    try:
        body = await request.json()
        game_scene = body.get("game_scene", "")
        mode = body.get("mode", "full_playthrough")
        player_profile = body.get("player_profile", "explorer")
        try:
            pm = PlaytestMode(mode)
        except ValueError:
            pm = PlaytestMode.FULL_PLAYTHROUGH
        try:
            pp = PlayerProfile(player_profile)
        except ValueError:
            pp = PlayerProfile.EXPLORER
        session = _playtest_simulator.start_session(
            game_scene=game_scene, mode=pm, player_profile=pp,
        )
        return session.to_dict() if hasattr(session, "to_dict") else session
    except Exception as e:
        return {"error": str(e)}

@router.post("/playtest-simulator/simulate-action")
async def playtest_simulator_simulate_action(request: Request):
    try:
        body = await request.json()
        session_id = body.get("session_id", "")
        action_type = body.get("action_type", "move_forward")
        target = body.get("target", "")
        action = _playtest_simulator.simulate_action(
            session_id=session_id, action_type=action_type, target=target,
        )
        return action.to_dict() if action else {"error": "Simulation failed"}
    except Exception as e:
        return {"error": str(e)}

@router.post("/playtest-simulator/auto-explore")
async def playtest_simulator_auto_explore(request: Request):
    try:
        body = await request.json()
        session_id = body.get("session_id", "")
        max_actions = body.get("max_actions", 0)
        session = _playtest_simulator.auto_explore(session_id=session_id, max_actions=max_actions)
        return session.to_dict() if session else {"error": "Auto-explore failed"}
    except Exception as e:
        return {"error": str(e)}

@router.get("/playtest-simulator/generate-summary")
async def playtest_simulator_generate_summary(session_id: str = ""):
    try:
        summary = _playtest_simulator.generate_summary(session_id)
        return summary.to_dict() if summary else {"error": "Session not found"}
    except Exception as e:
        return {"error": str(e)}

# ============================================================
# Lighting 2D Endpoints
# ============================================================

@router.get("/lighting-2d/stats")
async def lighting_2d_stats():
    try:
        return _lighting_2d.get_stats()
    except Exception as e:
        return {"error": str(e)}

@router.post("/lighting-2d/create-light")
async def lighting_2d_create_light(request: Request):
    try:
        body = await request.json()
        name = body.get("name", "")
        light_type = body.get("light_type", "point")
        pos_x = body.get("pos_x", 0.0)
        pos_y = body.get("pos_y", 0.0)
        color_r = body.get("color_r", 1.0)
        color_g = body.get("color_g", 1.0)
        color_b = body.get("color_b", 1.0)
        intensity = body.get("intensity", 1.0)
        radius = body.get("radius", 100.0)
        light = _lighting_2d.create_light(
            name=name, light_type=light_type, position=(pos_x, pos_y),
            color=(color_r, color_g, color_b), intensity=intensity, radius=radius,
        )
        return light.to_dict()
    except Exception as e:
        return {"error": str(e)}

@router.post("/lighting-2d/create-layer")
async def lighting_2d_create_layer(request: Request):
    try:
        body = await request.json()
        name = body.get("name", "")
        blend_mode = body.get("blend_mode", "additive")
        ambient_r = body.get("ambient_r", 0.05)
        ambient_g = body.get("ambient_g", 0.05)
        ambient_b = body.get("ambient_b", 0.05)
        layer = _lighting_2d.create_layer(
            name=name, blend_mode=blend_mode,
            ambient_color=(ambient_r, ambient_g, ambient_b),
        )
        return layer.to_dict()
    except Exception as e:
        return {"error": str(e)}

@router.post("/lighting-2d/configure-light")
async def lighting_2d_configure_light(request: Request):
    try:
        body = await request.json()
        light_id = body.get("light_id", "")
        config = {k: v for k, v in body.items() if k != "light_id"}
        result = _lighting_2d.configure_light(light_id=light_id, **config)
        return result.to_dict() if result else {"error": "Light not found"}
    except Exception as e:
        return {"error": str(e)}

@router.post("/lighting-2d/calculate")
async def lighting_2d_calculate(request: Request):
    try:
        body = await request.json()
        bound_min_x = body.get("bound_min_x", 0.0)
        bound_min_y = body.get("bound_min_y", 0.0)
        bound_max_x = body.get("bound_max_x", 640.0)
        bound_max_y = body.get("bound_max_y", 480.0)
        entities = body.get("entities", "")
        entity_list = entities.split(",") if entities else []
        result = _lighting_2d.calculate_lighting(
            scene_bounds=(bound_min_x, bound_min_y, bound_max_x, bound_max_y),
            visible_entities=entity_list,
        )
        return result
    except Exception as e:
        return {"error": str(e)}

# ============================================================
# Parallax Background Endpoints
# ============================================================

@router.get("/parallax-background/stats")
async def parallax_background_stats():
    try:
        return _parallax_background.get_stats()
    except Exception as e:
        return {"error": str(e)}

@router.post("/parallax-background/create-layer")
async def parallax_background_create_layer(request: Request):
    try:
        body = await request.json()
        name = body.get("name", "")
        texture_ref = body.get("texture_ref", "")
        parallax_factor = body.get("parallax_factor", 0.5)
        scroll_direction = body.get("scroll_direction", "horizontal")
        layer = _parallax_background.create_layer(
            name=name, texture_ref=texture_ref,
            parallax_factor=parallax_factor, scroll_direction=scroll_direction,
        )
        return layer.to_dict() if hasattr(layer, "to_dict") else layer
    except Exception as e:
        return {"error": str(e)}

@router.post("/parallax-background/create-scene")
async def parallax_background_create_scene(request: Request):
    try:
        body = await request.json()
        name = body.get("name", "")
        camera_entity_id = body.get("camera_entity_id", "")
        width = body.get("width", 1920.0)
        height = body.get("height", 1080.0)
        scene = _parallax_background.create_scene(
            name=name, camera_entity_id=camera_entity_id, width=width, height=height,
        )
        return scene.to_dict() if hasattr(scene, "to_dict") else scene
    except Exception as e:
        return {"error": str(e)}

@router.post("/parallax-background/update-scroll")
async def parallax_background_update_scroll(request: Request):
    try:
        body = await request.json()
        camera_x = body.get("camera_x", 0.0)
        camera_y = body.get("camera_y", 0.0)
        scene_id = body.get("scene_id", "")
        offsets = _parallax_background.update_scroll(
            camera_position=(camera_x, camera_y), scene_id=scene_id,
        )
        return offsets
    except Exception as e:
        return {"error": str(e)}

@router.post("/parallax-background/transition-scene")
async def parallax_background_transition(request: Request):
    try:
        body = await request.json()
        current_scene_id = body.get("current_scene_id", "")
        next_scene_id = body.get("next_scene_id", "")
        transition_type = body.get("transition_type", "fade")
        duration = body.get("duration", 1.0)
        success = _parallax_background.transition_scene(
            current_scene_id=current_scene_id, next_scene_id=next_scene_id,
            transition_type=transition_type, duration=duration,
        )
        return {"success": success}
    except Exception as e:
        return {"error": str(e)}

# ============================================================
# Behavior Library Endpoints
# ============================================================

@router.get("/behavior-library/stats")
async def behavior_library_stats():
    try:
        return _behavior_library.get_stats()
    except Exception as e:
        return {"error": str(e)}

@router.post("/behavior-library/register-template")
async def behavior_library_register_template(request: Request):
    try:
        body = await request.json()
        name = body.get("name", "")
        category = body.get("category", "movement")
        description = body.get("description", "")
        execution_mode = body.get("execution_mode", "update")
        try:
            bc = BehaviorCategory(category)
        except ValueError:
            bc = BehaviorCategory.MOVEMENT
        try:
            bem = BehaviorExecutionMode(execution_mode)
        except ValueError:
            bem = BehaviorExecutionMode.UPDATE
        template = _behavior_library.register_template(
            name=name, category=bc, description=description,
            execution_mode=bem,
        )
        return template.to_dict() if hasattr(template, "to_dict") else template
    except Exception as e:
        return {"error": str(e)}

@router.post("/behavior-library/instantiate")
async def behavior_library_instantiate(request: Request):
    try:
        import json
        body = await request.json()
        template_id = body.get("template_id", "")
        entity_id = body.get("entity_id", "")
        parameter_overrides = body.get("parameter_overrides", {})
        if isinstance(parameter_overrides, str):
            parameter_overrides = json.loads(parameter_overrides) if parameter_overrides else None
        instance = _behavior_library.instantiate_behavior(
            template_id=template_id, entity_id=entity_id, parameter_overrides=parameter_overrides,
        )
        return instance.to_dict() if instance else {"error": "Instantiation failed"}
    except Exception as e:
        return {"error": str(e)}

@router.post("/behavior-library/toggle")
async def behavior_library_toggle(request: Request):
    try:
        body = await request.json()
        instance_id = body.get("instance_id", "")
        enabled = body.get("enabled", True)
        success = _behavior_library.toggle_behavior(instance_id=instance_id, enabled=enabled)
        return {"success": success}
    except Exception as e:
        return {"error": str(e)}

@router.get("/behavior-library/entity-behaviors")
async def behavior_library_entity_behaviors(entity_id: str = ""):
    try:
        behaviors = _behavior_library.get_entity_behaviors(entity_id)
        return [b.to_dict() for b in behaviors]
    except Exception as e:
        return {"error": str(e)}

# ============================================================
# Animation Curve Endpoints
# ============================================================

@router.get("/animation-curve/stats")
async def animation_curve_stats():
    try:
        return _animation_curve.get_stats()
    except Exception as e:
        return {"error": str(e)}

@router.post("/animation-curve/create")
async def animation_curve_create(request: Request):
    try:
        body = await request.json()
        name = body.get("name", "")
        curve_type = body.get("curve_type", "bezier")
        easing = body.get("easing", "linear")
        try:
            ct = CurveType(curve_type)
        except ValueError:
            ct = CurveType.BEZIER
        try:
            ef = EasingFunction(easing)
        except ValueError:
            ef = EasingFunction.LINEAR
        curve = _animation_curve.create_curve(name=name, curve_type=ct, easing=ef)
        return curve.to_dict() if hasattr(curve, "to_dict") else curve
    except Exception as e:
        return {"error": str(e)}

@router.post("/animation-curve/add-keyframe")
async def animation_curve_add_keyframe(request: Request):
    try:
        body = await request.json()
        curve_id = body.get("curve_id", "")
        time = body.get("time", 0.0)
        value = body.get("value", 0.0)
        in_tangent_x = body.get("in_tangent_x", -0.2)
        in_tangent_y = body.get("in_tangent_y", 0.0)
        out_tangent_x = body.get("out_tangent_x", 0.2)
        out_tangent_y = body.get("out_tangent_y", 0.0)
        kf = _animation_curve.add_keyframe(
            curve_id=curve_id, time=time, value=value,
            in_tangent=(in_tangent_x, in_tangent_y),
            out_tangent=(out_tangent_x, out_tangent_y),
        )
        return kf.to_dict() if kf else {"error": "Keyframe addition failed"}
    except Exception as e:
        return {"error": str(e)}

@router.get("/animation-curve/evaluate")
async def animation_curve_evaluate(curve_id: str = "", time: float = 0.0):
    try:
        value = _animation_curve.evaluate_curve(curve_id=curve_id, time=time)
        return {"curve_id": curve_id, "time": time, "value": value}
    except Exception as e:
        return {"error": str(e)}

@router.post("/animation-curve/create-sequence")
async def animation_curve_create_sequence(request: Request):
    try:
        body = await request.json()
        name = body.get("name", "")
        track_ids = body.get("track_ids", "")
        duration = body.get("duration", 1.0)
        loop = body.get("loop", False)
        playback_speed = body.get("playback_speed", 1.0)
        tids = track_ids.split(",") if track_ids else []
        sequence = _animation_curve.create_sequence(
            name=name, track_ids=tids, duration=duration,
            loop=loop, playback_speed=playback_speed,
        )
        return sequence.to_dict() if hasattr(sequence, "to_dict") else sequence
    except Exception as e:
        return {"error": str(e)}

# ============================================================
# Render Layer Endpoints
# ============================================================

@router.get("/render-layer/stats")
async def render_layer_stats():
    try:
        return _render_layer.get_stats()
    except Exception as e:
        return {"error": str(e)}

@router.post("/render-layer/create-layer")
async def render_layer_create(request: Request):
    try:
        body = await request.json()
        name = body.get("name", "")
        z_index = body.get("z_index", 0)
        sort_strategy = body.get("sort_strategy", "by_z_order")
        layer = _render_layer.create_layer(name=name, z_index=z_index, sort_strategy=sort_strategy)
        return layer.to_dict() if hasattr(layer, "to_dict") else layer
    except Exception as e:
        return {"error": str(e)}

@router.post("/render-layer/create-group")
async def render_layer_create_group(request: Request):
    try:
        body = await request.json()
        name = body.get("name", "")
        group = _render_layer.create_group(name=name)
        return group.to_dict() if hasattr(group, "to_dict") else group
    except Exception as e:
        return {"error": str(e)}

@router.post("/render-layer/assign-entity")
async def render_layer_assign_entity(request: Request):
    try:
        body = await request.json()
        entity_id = body.get("entity_id", "")
        layer_id = body.get("layer_id", "")
        success = _render_layer.assign_entity_to_layer(entity_id=entity_id, layer_id=layer_id)
        return {"success": success}
    except Exception as e:
        return {"error": str(e)}

@router.post("/render-layer/reorder")
async def render_layer_reorder(request: Request):
    try:
        body = await request.json()
        group_id = body.get("group_id", "")
        layer_order = body.get("layer_order", "")
        order_list = layer_order.split(",") if layer_order else []
        success = _render_layer.reorder_layers(group_id=group_id, layer_order=order_list)
        return {"success": success}
    except Exception as e:
        return {"error": str(e)}

# ============================================================
# State Synchronizer Endpoints
# ============================================================

@router.get("/state-synchronizer/stats")
async def state_synchronizer_stats():
    try:
        return _state_synchronizer.get_stats()
    except Exception as e:
        return {"error": str(e)}

@router.post("/state-synchronizer/take-snapshot")
async def state_synchronizer_take_snapshot(request: Request):
    try:
        body = await request.json()
        entity_id = body.get("entity_id", "")
        state_data = body.get("state_data", {})
        sd = state_data if state_data else {}
        snapshot = _state_synchronizer.take_snapshot(entity_id=entity_id, state_data=sd)
        return snapshot.to_dict() if hasattr(snapshot, "to_dict") else snapshot
    except Exception as e:
        return {"error": str(e)}

@router.post("/state-synchronizer/compute-delta")
async def state_synchronizer_compute_delta(request: Request):
    try:
        body = await request.json()
        from_snapshot_id = body.get("from_snapshot_id", "")
        to_snapshot_id = body.get("to_snapshot_id", "")
        delta = _state_synchronizer.compute_delta(
            from_snapshot_id=from_snapshot_id, to_snapshot_id=to_snapshot_id,
        )
        return delta.to_dict() if delta else {"error": "Delta computation failed"}
    except Exception as e:
        return {"error": str(e)}

@router.post("/state-synchronizer/start-recording")
async def state_synchronizer_start_recording(request: Request):
    try:
        body = await request.json()
        entity_id = body.get("entity_id", "")
        session = _state_synchronizer.start_replay_recording(entity_id)
        return session.to_dict() if session else {"error": "Recording start failed"}
    except Exception as e:
        return {"error": str(e)}

@router.get("/state-synchronizer/replay-summary")
async def state_synchronizer_replay_summary(session_id: str = ""):
    try:
        session = _state_synchronizer.get_replay_session(session_id)
        return session.to_dict() if session else {"error": "Session not found"}
    except Exception as e:
        return {"error": str(e)}

# ============================================================
# Skill Synthesizer Endpoints
# ============================================================

@router.get("/skill-synthesizer/stats")
async def skill_synthesizer_stats():
    try:
        return _skill_synthesizer.get_stats()
    except Exception as e:
        return {"error": str(e)}

@router.post("/skill-synthesizer/observe-trajectory")
async def skill_synthesizer_observe_trajectory(request: Request):
    try:
        body = await request.json()
        session_id = body.get("session_id", "")
        tool_sequence = body.get("tool_sequence", [])
        success = body.get("success", True)
        metadata = body.get("metadata", {})
        _skill_synthesizer.observe_trajectory(session_id, tool_sequence, success, metadata)
        return {"observed": True}
    except Exception as e:
        return {"error": str(e)}

@router.post("/skill-synthesizer/analyze-patterns")
async def skill_synthesizer_analyze_patterns(request: Request):
    try:
        body = await request.json()
        session_ids = body.get("session_ids", [])
        min_frequency = body.get("min_frequency", 2)
        result = _skill_synthesizer.analyze_patterns(session_ids, min_frequency)
        return result.to_dict() if hasattr(result, "to_dict") else {"patterns": result}
    except Exception as e:
        return {"error": str(e)}

@router.post("/skill-synthesizer/synthesize-skill")
async def skill_synthesizer_synthesize(request: Request):
    try:
        body = await request.json()
        pattern_id = body.get("pattern_id", "")
        skill_name = body.get("skill_name", "")
        description = body.get("description", "")
        result = _skill_synthesizer.synthesize_skill(pattern_id, skill_name, description)
        return result.to_dict() if result else {"error": "Synthesis failed"}
    except Exception as e:
        return {"error": str(e)}

@router.get("/skill-synthesizer/catalog")
async def skill_synthesizer_catalog():
    try:
        return _skill_synthesizer.get_skill_catalog()
    except Exception as e:
        return {"error": str(e)}

# ============================================================
# Security Scanner Endpoints
# ============================================================

@router.get("/security-scanner/stats")
async def security_scanner_stats():
    try:
        return _security_scanner.get_stats()
    except Exception as e:
        return {"error": str(e)}

@router.post("/security-scanner/scan-content")
async def security_scanner_scan_content(request: Request):
    try:
        body = await request.json()
        content = body.get("content", "")
        source_type = body.get("source_type", "unknown")
        context = body.get("context", {})
        result = _security_scanner.scan_content(content, source_type, context)
        return result.to_dict() if hasattr(result, "to_dict") else result
    except Exception as e:
        return {"error": str(e)}


# --- AB Test Runner ---

@router.get("/ab-test-runner/stats")
async def ab_test_runner_stats():
    try:
        return _ab_test_runner.get_stats()
    except Exception as e:
        return {"error": str(e)}

@router.post("/ab-test-runner/create-experiment")
async def ab_test_runner_create_experiment(request: Request):
    try:
        body = await request.json()
        name = body.get("name", "")
        variant_a = body.get("variant_a", "control")
        variant_b = body.get("variant_b", "treatment")
        metric_type = body.get("metric_type", "retention")
        result = _ab_test_runner.create_experiment(name, variant_a, variant_b, metric_type)
        return result.to_dict() if hasattr(result, "to_dict") else {"success": True}
    except Exception as e:
        return {"error": str(e)}

@router.post("/ab-test-runner/analyze-results")
async def ab_test_runner_analyze_results(request: Request):
    try:
        body = await request.json()
        experiment_id = body.get("experiment_id", "")
        result = _ab_test_runner.analyze_results(experiment_id)
        return result.to_dict() if hasattr(result, "to_dict") else result
    except Exception as e:
        return {"error": str(e)}


# --- Heatmap Analyzer ---

@router.get("/heatmap-analyzer/stats")
async def heatmap_analyzer_stats():
    try:
        return _heatmap_analyzer.get_stats()
    except Exception as e:
        return {"error": str(e)}

@router.post("/heatmap-analyzer/create-grid")
async def heatmap_analyzer_create_grid(request: Request):
    try:
        body = await request.json()
        name = body.get("name", "")
        width = body.get("width", 100)
        height = body.get("height", 100)
        resolution = body.get("resolution", "medium")
        result = _heatmap_analyzer.create_grid(name, width, height, resolution)
        return result.to_dict() if hasattr(result, "to_dict") else {"success": True}
    except Exception as e:
        return {"error": str(e)}

@router.post("/heatmap-analyzer/record-event")
async def heatmap_analyzer_record_event(request: Request):
    try:
        body = await request.json()
        grid_id = body.get("grid_id", "")
        x = body.get("x", 0.0)
        y = body.get("y", 0.0)
        weight = body.get("weight", 1.0)
        _heatmap_analyzer.record_event(grid_id, x, y, weight)
        return {"success": True}
    except Exception as e:
        return {"error": str(e)}

@router.post("/heatmap-analyzer/analyze-pathing")
async def heatmap_analyzer_analyze_pathing(request: Request):
    try:
        body = await request.json()
        grid_id = body.get("grid_id", "")
        result = _heatmap_analyzer.analyze_pathing(grid_id)
        return result
    except Exception as e:
        return {"error": str(e)}


# --- Bug Forensics ---

@router.get("/bug-forensics/stats")
async def bug_forensics_stats():
    try:
        return _bug_forensics.get_stats()
    except Exception as e:
        return {"error": str(e)}

@router.post("/bug-forensics/submit-crash")
async def bug_forensics_submit_crash(request: Request):
    try:
        body = await request.json()
        build = body.get("build", "")
        stack_trace = body.get("stack_trace", "")
        platform = body.get("platform", "windows")
        result = _bug_forensics.submit_crash(build, stack_trace, platform)
        return result.to_dict() if hasattr(result, "to_dict") else {"success": True}
    except Exception as e:
        return {"error": str(e)}

@router.post("/bug-forensics/analyze-crash")
async def bug_forensics_analyze_crash(request: Request):
    try:
        body = await request.json()
        report_id = body.get("report_id", "")
        result = _bug_forensics.analyze_crash(report_id)
        return result.to_dict() if hasattr(result, "to_dict") else result
    except Exception as e:
        return {"error": str(e)}


# --- Accessibility Auditor ---

@router.get("/accessibility-auditor/stats")
async def accessibility_auditor_stats():
    try:
        return _accessibility_auditor.get_stats()
    except Exception as e:
        return {"error": str(e)}

@router.post("/accessibility-auditor/run-audit")
async def accessibility_auditor_run_audit(request: Request):
    try:
        body = await request.json()
        scene_id = body.get("scene_id", "")
        target_level = body.get("target_level", "AA")
        category = body.get("category", "all")
        game_config = {
            "target_level": target_level,
            "category": category,
        }
        result = _accessibility_auditor.run_audit(scene_id, game_config)
        return result.to_dict() if hasattr(result, "to_dict") else {"success": True}
    except Exception as e:
        return {"error": str(e)}

@router.post("/accessibility-auditor/generate-plan")
async def accessibility_auditor_generate_plan(request: Request):
    try:
        body = await request.json()
        report_id = body.get("report_id", "")
        result = _accessibility_auditor.generate_improvement_plan(report_id)
        return result.to_dict() if hasattr(result, "to_dict") else result
    except Exception as e:
        return {"error": str(e)}


# --- Tile Brush ---

@router.get("/tile-brush/stats")
async def tile_brush_stats():
    try:
        return _tile_brush.get_stats()
    except Exception as e:
        return {"error": str(e)}

@router.post("/tile-brush/paint-tile")
async def tile_brush_paint_tile(request: Request):
    try:
        body = await request.json()
        tilemap_id = body.get("tilemap_id", "")
        x = body.get("x", 0)
        y = body.get("y", 0)
        tileset_id = body.get("tileset_id", "")
        tile_index = body.get("tile_index", 0)
        result = _tile_brush.paint_tile(tilemap_id, x, y, tileset_id, tile_index)
        return result.to_dict() if hasattr(result, "to_dict") else {"success": True}
    except Exception as e:
        return {"error": str(e)}

@router.post("/tile-brush/auto-border")
async def tile_brush_auto_border(request: Request):
    try:
        body = await request.json()
        tilemap_id = body.get("tilemap_id", "")
        neighbor_mode = body.get("neighbor_mode", "moore")
        terrain_set = body.get("terrain_set", "default")
        result = _tile_brush.auto_border(tilemap_id, neighbor_mode, terrain_set)
        return result.to_dict() if hasattr(result, "to_dict") else result
    except Exception as e:
        return {"error": str(e)}


# --- Sprite Animator ---

@router.get("/sprite-animator/stats")
async def sprite_animator_stats():
    try:
        return _sprite_animator.get_stats()
    except Exception as e:
        return {"error": str(e)}

@router.post("/sprite-animator/create-clip")
async def sprite_animator_create_clip(request: Request):
    try:
        body = await request.json()
        name = body.get("name", "")
        frame_count = body.get("frame_count", 8)
        frame_rate = body.get("frame_rate", 12.0)
        loop_mode = body.get("loop_mode", "loop")
        result = _sprite_animator.create_clip(name, frame_count, frame_rate, loop_mode)
        return result.to_dict() if hasattr(result, "to_dict") else {"success": True}
    except Exception as e:
        return {"error": str(e)}

@router.post("/sprite-animator/play")
async def sprite_animator_play(request: Request):
    try:
        body = await request.json()
        entity_id = body.get("entity_id", "")
        clip_id = body.get("clip_id", "")
        result = _sprite_animator.play(entity_id, clip_id)
        return result
    except Exception as e:
        return {"error": str(e)}


# --- Light Culling ---

@router.get("/light-culling/stats")
async def light_culling_stats():
    try:
        return _light_culling.get_stats()
    except Exception as e:
        return {"error": str(e)}

@router.post("/light-culling/register-light")
async def light_culling_register_light(request: Request):
    try:
        body = await request.json()
        type = body.get("type", "point")
        position = body.get("position", [0.0, 0.0, 0.0])
        range = body.get("range", 10.0)
        intensity = body.get("intensity", 1.0)
        result = _light_culling.register_light(type, position, range, intensity)
        return result.to_dict() if hasattr(result, "to_dict") else {"success": True}
    except Exception as e:
        return {"error": str(e)}

@router.post("/light-culling/assign-lights")
async def light_culling_assign_lights(request: Request):
    try:
        body = await request.json()
        object_id = body.get("object_id", "")
        position = body.get("position", [0.0, 0.0, 0.0])
        max_lights = body.get("max_lights", 8)
        result = _light_culling.assign_lights(object_id, position, max_lights)
        return result.to_dict() if hasattr(result, "to_dict") else result
    except Exception as e:
        return {"error": str(e)}


# --- Render Pass ---

@router.get("/render-pass/stats")
async def render_pass_stats():
    try:
        return _render_pass.get_stats()
    except Exception as e:
        return {"error": str(e)}

@router.post("/render-pass/create-pass")
async def render_pass_create_pass(request: Request):
    try:
        body = await request.json()
        name = body.get("name", "")
        pass_type = body.get("pass_type", "custom")
        priority = body.get("priority", 0)
        enabled = body.get("enabled", True)
        result = _render_pass.create_pass(name, pass_type, priority, enabled)
        return result.to_dict() if hasattr(result, "to_dict") else {"success": True}
    except Exception as e:
        return {"error": str(e)}

@router.post("/render-pass/execute-pipeline")
async def render_pass_execute_pipeline(request: Request):
    try:
        body = await request.json()
        pipeline_name = body.get("pipeline_name", "default")
        result = _render_pass.execute_pipeline(pipeline_name)
        return result.to_dict() if hasattr(result, "to_dict") else result
    except Exception as e:
        return {"error": str(e)}

@router.post("/security-scanner/add-rule")
async def security_scanner_add_rule(request: Request):
    try:
        body = await request.json()
        rule_name = body.get("rule_name", "")
        pattern = body.get("pattern", "")
        category = body.get("category", "custom")
        severity = body.get("severity", "medium")
        result = _security_scanner.add_rule(rule_name, pattern, category, severity)
        return result.to_dict() if hasattr(result, "to_dict") else {"added": True}
    except Exception as e:
        return {"error": str(e)}

@router.get("/security-scanner/active-rules")
async def security_scanner_active_rules():
    try:
        return _security_scanner.get_active_rules()
    except Exception as e:
        return {"error": str(e)}

# ============================================================
# Delegation Framework Endpoints
# ============================================================

@router.get("/delegation-framework/stats")
async def delegation_framework_stats():
    try:
        return _delegation_framework.get_stats()
    except Exception as e:
        return {"error": str(e)}

@router.post("/delegation-framework/register-child")
async def delegation_framework_register_child(request: Request):
    try:
        body = await request.json()
        name = body.get("name", "")
        role = body.get("role", "worker")
        capabilities = body.get("capabilities", [])
        result = _delegation_framework.register_child(name, role, capabilities)
        return result.to_dict() if hasattr(result, "to_dict") else result
    except Exception as e:
        return {"error": str(e)}

@router.post("/delegation-framework/create-pool")
async def delegation_framework_create_pool(request: Request):
    try:
        body = await request.json()
        name = body.get("name", "")
        strategy = body.get("strategy", "round_robin")
        child_ids = body.get("child_ids", [])
        result = _delegation_framework.create_pool(name, strategy, child_ids)
        return result.to_dict() if hasattr(result, "to_dict") else result
    except Exception as e:
        return {"error": str(e)}

@router.post("/delegation-framework/delegate-task")
async def delegation_framework_delegate_task(request: Request):
    try:
        body = await request.json()
        task_description = body.get("task_description", "")
        pool_id = body.get("pool_id", "")
        target_child_id = body.get("target_child_id", "")
        priority = body.get("priority", "normal")
        result = _delegation_framework.delegate_task(task_description, pool_id, target_child_id, priority)
        return result.to_dict() if result else {"error": "Delegation failed"}
    except Exception as e:
        return {"error": str(e)}

# ============================================================
# Kanban Coordinator Endpoints
# ============================================================

@router.get("/kanban-coordinator/stats")
async def kanban_coordinator_stats():
    try:
        return _kanban_coordinator.get_stats()
    except Exception as e:
        return {"error": str(e)}

@router.post("/kanban-coordinator/create-board")
async def kanban_coordinator_create_board(request: Request):
    try:
        body = await request.json()
        name = body.get("name", "")
        columns = body.get("columns", [])
        result = _kanban_coordinator.create_board(name, columns)
        return result.to_dict() if hasattr(result, "to_dict") else result
    except Exception as e:
        return {"error": str(e)}

@router.post("/kanban-coordinator/create-task")
async def kanban_coordinator_create_task(request: Request):
    try:
        body = await request.json()
        board_id = body.get("board_id", "")
        title = body.get("title", "")
        description = body.get("description", "")
        task_type = body.get("task_type", "feature")
        assignee = body.get("assignee", "")
        result = _kanban_coordinator.create_task(board_id, title, description, task_type, assignee)
        return result.to_dict() if result else {"error": "Task creation failed"}
    except Exception as e:
        return {"error": str(e)}

@router.post("/kanban-coordinator/move-task")
async def kanban_coordinator_move_task(request: Request):
    try:
        body = await request.json()
        task_id = body.get("task_id", "")
        target_column = body.get("target_column", "")
        result = _kanban_coordinator.move_task(task_id, target_column)
        return result.to_dict() if hasattr(result, "to_dict") else {"moved": True}
    except Exception as e:
        return {"error": str(e)}

# ============================================================
# Streaming Scrubber Endpoints
# ============================================================

@router.get("/streaming-scrubber/stats")
async def streaming_scrubber_stats():
    try:
        return _streaming_scrubber.get_stats()
    except Exception as e:
        return {"error": str(e)}

@router.post("/streaming-scrubber/create-session")
async def streaming_scrubber_create_session(request: Request):
    try:
        body = await request.json()
        source = body.get("source", "")
        mode = body.get("mode", "auto")
        visibility = body.get("visibility", "public")
        result = _streaming_scrubber.create_session(source, mode, visibility)
        return result.to_dict() if hasattr(result, "to_dict") else result
    except Exception as e:
        return {"error": str(e)}

@router.post("/streaming-scrubber/process-chunk")
async def streaming_scrubber_process_chunk(request: Request):
    try:
        body = await request.json()
        session_id = body.get("session_id", "")
        chunk = body.get("chunk", "")
        metadata = body.get("metadata", {})
        result = _streaming_scrubber.process_chunk(session_id, chunk, metadata)
        return result.to_dict() if hasattr(result, "to_dict") else result
    except Exception as e:
        return {"error": str(e)}

@router.post("/streaming-scrubber/add-rule")
async def streaming_scrubber_add_rule(request: Request):
    try:
        body = await request.json()
        rule_name = body.get("rule_name", "")
        block_type = body.get("block_type", "keyword")
        pattern = body.get("pattern", "")
        replacement = body.get("replacement", "")
        result = _streaming_scrubber.add_rule(rule_name, block_type, pattern, replacement)
        return result.to_dict() if hasattr(result, "to_dict") else {"added": True}
    except Exception as e:
        return {"error": str(e)}

# ============================================================
# Trajectory Generator Endpoints
# ============================================================

@router.get("/trajectory-generator/stats")
async def trajectory_generator_stats():
    try:
        return _trajectory_generator.get_stats()
    except Exception as e:
        return {"error": str(e)}

@router.post("/trajectory-generator/start-session")
async def trajectory_generator_start_session(request: Request):
    try:
        body = await request.json()
        source = body.get("source", "")
        format_type = body.get("format", "json")
        compress = body.get("compress", False)
        result = _trajectory_generator.start_session(source, format_type, compress)
        return result.to_dict() if hasattr(result, "to_dict") else result
    except Exception as e:
        return {"error": str(e)}

@router.post("/trajectory-generator/record-turn")
async def trajectory_generator_record_turn(request: Request):
    try:
        body = await request.json()
        session_id = body.get("session_id", "")
        role = body.get("role", "user")
        content = body.get("content", "")
        metadata = body.get("metadata", {})
        result = _trajectory_generator.record_turn(session_id, role, content, metadata)
        return result.to_dict() if hasattr(result, "to_dict") else {"recorded": True}
    except Exception as e:
        return {"error": str(e)}

@router.post("/trajectory-generator/end-session")
async def trajectory_generator_end_session(request: Request):
    try:
        body = await request.json()
        session_id = body.get("session_id", "")
        result = _trajectory_generator.end_session(session_id)
        return result.to_dict() if result else {"error": "Session not found"}
    except Exception as e:
        return {"error": str(e)}

# ============================================================
# Visual Script Runtime Endpoints
# ============================================================

@router.get("/visual-script-runtime/stats")
async def visual_script_runtime_stats():
    try:
        return _visual_script_runtime.get_stats()
    except Exception as e:
        return {"error": str(e)}

@router.post("/visual-script-runtime/create-graph")
async def visual_script_runtime_create_graph(request: Request):
    try:
        body = await request.json()
        name = body.get("name", "")
        graph_type = body.get("graph_type", "behavior")
        result = _visual_script_runtime.create_graph(name, graph_type)
        return result.to_dict() if hasattr(result, "to_dict") else result
    except Exception as e:
        return {"error": str(e)}

@router.post("/visual-script-runtime/add-node")
async def visual_script_runtime_add_node(request: Request):
    try:
        body = await request.json()
        graph_id = body.get("graph_id", "")
        node_type = body.get("node_type", "action")
        name = body.get("name", "")
        position = body.get("position", [0, 0])
        parameters = body.get("parameters", {})
        result = _visual_script_runtime.add_node(graph_id, node_type, name, position, parameters)
        return result.to_dict() if result else {"error": "Node addition failed"}
    except Exception as e:
        return {"error": str(e)}

@router.post("/visual-script-runtime/transpile")
async def visual_script_runtime_transpile(request: Request):
    try:
        body = await request.json()
        graph_id = body.get("graph_id", "")
        target_language = body.get("target_language", "sparkscript")
        result = _visual_script_runtime.transpile(graph_id, target_language)
        return result.to_dict() if hasattr(result, "to_dict") else result
    except Exception as e:
        return {"error": str(e)}

# ============================================================
# Extension SDK Endpoints
# ============================================================

@router.get("/extension-sdk/stats")
async def extension_sdk_stats():
    try:
        return _extension_sdk.get_stats()
    except Exception as e:
        return {"error": str(e)}

@router.post("/extension-sdk/register-extension")
async def extension_sdk_register_extension(request: Request):
    try:
        body = await request.json()
        name = body.get("name", "")
        version = body.get("version", "1.0.0")
        extension_type = body.get("extension_type", "tool")
        source = body.get("source", "local")
        result = _extension_sdk.register_extension(name, version, extension_type, source)
        return result.to_dict() if hasattr(result, "to_dict") else result
    except Exception as e:
        return {"error": str(e)}

@router.post("/extension-sdk/search-extensions")
async def extension_sdk_search_extensions(request: Request):
    try:
        body = await request.json()
        query = body.get("query", "")
        extension_type = body.get("extension_type", "")
        limit = body.get("limit", 20)
        result = _extension_sdk.search_extensions(query, extension_type, limit)
        return {"results": result}
    except Exception as e:
        return {"error": str(e)}

@router.get("/extension-sdk/capabilities")
async def extension_sdk_capabilities():
    try:
        return _extension_sdk.get_capabilities()
    except Exception as e:
        return {"error": str(e)}

# ============================================================
# Signal Bus Endpoints
# ============================================================

@router.get("/signal-bus/stats")
async def signal_bus_stats():
    try:
        return _engine_signal_bus.get_stats()
    except Exception as e:
        return {"error": str(e)}

@router.post("/signal-bus/define-signal")
async def signal_bus_define_signal(request: Request):
    try:
        body = await request.json()
        signal_name = body.get("signal_name", "")
        signal_type = body.get("signal_type", "")
        parameters = body.get("parameters", [])
        result = _engine_signal_bus.define_signal(signal_name, signal_type, parameters)
        return result.to_dict() if hasattr(result, "to_dict") else {"defined": True}
    except Exception as e:
        return {"error": str(e)}

@router.post("/signal-bus/emit-signal")
async def signal_bus_emit_signal(request: Request):
    try:
        body = await request.json()
        signal_name = body.get("signal_name", "")
        data = body.get("data", {})
        priority = body.get("priority", "normal")
        result = _engine_signal_bus.emit_signal(signal_name, data, priority)
        return {"emitted": True, "listeners": result}
    except Exception as e:
        return {"error": str(e)}

@router.get("/signal-bus/history")
async def signal_bus_history(limit: int = 100):
    try:
        return _engine_signal_bus.get_history(limit)
    except Exception as e:
        return {"error": str(e)}

# ============================================================
# Prefab Composer Endpoints
# ============================================================

@router.get("/prefab-composer/stats")
async def prefab_composer_stats():
    try:
        return _prefab_composer.get_stats()
    except Exception as e:
        return {"error": str(e)}

@router.post("/prefab-composer/create-prefab")
async def prefab_composer_create_prefab(request: Request):
    try:
        body = await request.json()
        name = body.get("name", "")
        prefab_type = body.get("prefab_type", "scene")
        components = body.get("components", [])
        result = _prefab_composer.create_prefab(name, prefab_type, components)
        return result.to_dict() if hasattr(result, "to_dict") else result
    except Exception as e:
        return {"error": str(e)}

@router.post("/prefab-composer/add-component")
async def prefab_composer_add_component(request: Request):
    try:
        body = await request.json()
        prefab_id = body.get("prefab_id", "")
        component_type = body.get("component_type", "")
        properties = body.get("properties", {})
        result = _prefab_composer.add_component(prefab_id, component_type, properties)
        return result.to_dict() if result else {"error": "Component addition failed"}
    except Exception as e:
        return {"error": str(e)}

@router.post("/prefab-composer/instantiate")
async def prefab_composer_instantiate(request: Request):
    try:
        body = await request.json()
        prefab_id = body.get("prefab_id", "")
        parent_scene_id = body.get("parent_scene_id", "")
        position = body.get("position", None)
        variant_id = body.get("variant_id", "")
        overrides = body.get("overrides", None)
        result = _prefab_composer.instantiate_prefab(prefab_id, parent_scene_id, position, variant_id, overrides)
        return result.to_dict() if result else {"error": "Instantiation failed"}
    except Exception as e:
        return {"error": str(e)}

# ============================================================
# Interactive Audio Endpoints
# ============================================================

@router.get("/interactive-audio/stats")
async def interactive_audio_stats():
    try:
        return _interactive_audio.get_stats()
    except Exception as e:
        return {"error": str(e)}

@router.post("/interactive-audio/create-stem")
async def interactive_audio_create_stem(request: Request):
    try:
        body = await request.json()
        name = body.get("name", "")
        audio_path = body.get("audio_path", "")
        category = body.get("category", "music")
        layer = body.get("layer", "base")
        result = _interactive_audio.create_stem(name, audio_path, category, layer)
        return result.to_dict() if hasattr(result, "to_dict") else result
    except Exception as e:
        return {"error": str(e)}

@router.post("/interactive-audio/create-playlist")
async def interactive_audio_create_playlist(request: Request):
    try:
        body = await request.json()
        name = body.get("name", "")
        stem_ids = body.get("stem_ids", [])
        transition = body.get("transition", "crossfade")
        result = _interactive_audio.create_playlist(name, stem_ids, transition)
        return result.to_dict() if hasattr(result, "to_dict") else result
    except Exception as e:
        return {"error": str(e)}

@router.post("/interactive-audio/start-playlist")
async def interactive_audio_start_playlist(request: Request):
    try:
        body = await request.json()
        playlist_id = body.get("playlist_id", "")
        intensity = body.get("intensity", 0.5)
        loop = body.get("loop", True)
        result = _interactive_audio.start_playlist(playlist_id, intensity, loop)
        return result.to_dict() if hasattr(result, "to_dict") else {"started": True}
    except Exception as e:
        return {"error": str(e)}

# ============================================================
# Import Pipeline (v2) Endpoints
# ============================================================

@router.get("/import-pipeline/stats")
async def import_pipeline_v2_stats():
    try:
        return _engine_import_pipeline.get_stats()
    except Exception as e:
        return {"error": str(e)}

@router.post("/import-pipeline/import-asset")
async def import_pipeline_v2_import_asset(request: Request):
    try:
        body = await request.json()
        source_path = body.get("source_path", "")
        asset_type = body.get("asset_type", "texture")
        compression = body.get("compression", "default")
        result = _engine_import_pipeline.import_asset(source_path, asset_type, compression)
        return result.to_dict() if result else {"error": "Import failed"}
    except Exception as e:
        return {"error": str(e)}

@router.post("/import-pipeline/create-profile")
async def import_pipeline_v2_create_profile(request: Request):
    try:
        body = await request.json()
        name = body.get("name", "")
        asset_type = body.get("asset_type", "")
        compression = body.get("compression", "default")
        optimization = body.get("optimization", "balanced")
        result = _engine_import_pipeline.create_profile(name, asset_type, compression, optimization)
        return result.to_dict() if hasattr(result, "to_dict") else result
    except Exception as e:
        return {"error": str(e)}

@router.get("/import-pipeline/import-history")
async def import_pipeline_v2_import_history(limit: int = 20):
    try:
        result = _engine_import_pipeline.get_import_history()
        return {"imports": result[:limit]}
    except Exception as e:
        return {"error": str(e)}

# ============================================================
# Developer Oracle Endpoints
# ============================================================

@router.get("/developer-oracle/stats")
async def developer_oracle_stats():
    try:
        return _developer_oracle.get_stats()
    except Exception as e:
        return {"error": str(e)}

@router.post("/developer-oracle/create-profile")
async def developer_oracle_create_profile(request: Request):
    try:
        body = await request.json()
        name = body.get("name", "")
        expertise = body.get("expertise", [])
        preferences = body.get("preferences", {})
        result = _developer_oracle.create_profile(name, expertise, preferences)
        return result.to_dict() if hasattr(result, "to_dict") else {"success": True}
    except Exception as e:
        return {"error": str(e)}

@router.post("/developer-oracle/analyze-patterns")
async def developer_oracle_analyze_patterns(request: Request):
    try:
        body = await request.json()
        code_snippets = body.get("code_snippets", [])
        analysis_depth = body.get("analysis_depth", "standard")
        result = _developer_oracle.analyze_patterns(code_snippets, analysis_depth)
        return result.to_dict() if hasattr(result, "to_dict") else result
    except Exception as e:
        return {"error": str(e)}

# ============================================================
# Context Weaver Endpoints
# ============================================================

@router.get("/context-weaver/stats")
async def context_weaver_stats():
    try:
        return _context_weaver.get_stats()
    except Exception as e:
        return {"error": str(e)}

@router.post("/context-weaver/create-document")
async def context_weaver_create_document(request: Request):
    try:
        body = await request.json()
        title = body.get("title", "")
        content = body.get("content", "")
        doc_type = body.get("doc_type", "specification")
        tags = body.get("tags", [])
        result = _context_weaver.create_document(title, content, doc_type, tags)
        return result.to_dict() if hasattr(result, "to_dict") else {"success": True}
    except Exception as e:
        return {"error": str(e)}

@router.post("/context-weaver/weave-context")
async def context_weaver_weave_context(request: Request):
    try:
        body = await request.json()
        source_ids = body.get("source_ids", [])
        target_format = body.get("target_format", "summary")
        weave_config = body.get("weave_config", {})
        result = _context_weaver.weave_context(source_ids, target_format, weave_config)
        return result.to_dict() if hasattr(result, "to_dict") else result
    except Exception as e:
        return {"error": str(e)}

# ============================================================
# Session Nexus Endpoints
# ============================================================

@router.get("/session-nexus/stats")
async def session_nexus_stats():
    try:
        return _session_nexus.get_stats()
    except Exception as e:
        return {"error": str(e)}

@router.post("/session-nexus/create-session")
async def session_nexus_create_session(request: Request):
    try:
        body = await request.json()
        name = body.get("name", "")
        participant_ids = body.get("participant_ids", [])
        session_type = body.get("session_type", "collaborative")
        result = _session_nexus.create_session(name, participant_ids, session_type)
        return result.to_dict() if hasattr(result, "to_dict") else {"success": True}
    except Exception as e:
        return {"error": str(e)}

@router.post("/session-nexus/create-bridge")
async def session_nexus_create_bridge(request: Request):
    try:
        body = await request.json()
        source_session_id = body.get("source_session_id", "")
        target_session_id = body.get("target_session_id", "")
        bridge_type = body.get("bridge_type", "shared-context")
        result = _session_nexus.create_bridge(source_session_id, target_session_id, bridge_type)
        return result.to_dict() if hasattr(result, "to_dict") else {"success": True}
    except Exception as e:
        return {"error": str(e)}

# ============================================================
# Persona Vault Endpoints
# ============================================================

@router.get("/persona-vault/stats")
async def persona_vault_stats():
    try:
        return _persona_vault.get_stats()
    except Exception as e:
        return {"error": str(e)}

@router.post("/persona-vault/create-persona")
async def persona_vault_create_persona(request: Request):
    try:
        body = await request.json()
        name = body.get("name", "")
        traits = body.get("traits", {})
        background = body.get("background", "")
        voice_style = body.get("voice_style", "neutral")
        result = _persona_vault.create_persona(name, traits, background, voice_style)
        return result.to_dict() if hasattr(result, "to_dict") else {"success": True}
    except Exception as e:
        return {"error": str(e)}

@router.post("/persona-vault/export-persona")
async def persona_vault_export_persona(request: Request):
    try:
        body = await request.json()
        persona_id = body.get("persona_id", "")
        export_format = body.get("export_format", "json")
        result = _persona_vault.export_persona(persona_id, export_format)
        return result.to_dict() if hasattr(result, "to_dict") else result
    except Exception as e:
        return {"error": str(e)}

# ============================================================
# Voice Bridge Endpoints
# ============================================================

@router.get("/voice-bridge/stats")
async def voice_bridge_stats():
    try:
        return _voice_bridge.get_stats()
    except Exception as e:
        return {"error": str(e)}

@router.post("/voice-bridge/process-text")
async def voice_bridge_process_text(request: Request):
    try:
        body = await request.json()
        text = body.get("text", "")
        voice_style = body.get("voice_style", "neutral")
        speed = body.get("speed", 1.0)
        result = _voice_bridge.process_text(text, voice_style, speed)
        return result.to_dict() if hasattr(result, "to_dict") else result
    except Exception as e:
        return {"error": str(e)}

@router.post("/voice-bridge/start-session")
async def voice_bridge_start_session(request: Request):
    try:
        body = await request.json()
        persona_id = body.get("persona_id", "")
        input_mode = body.get("input_mode", "text")
        result = _voice_bridge.start_session(persona_id, input_mode)
        return result.to_dict() if hasattr(result, "to_dict") else {"success": True}
    except Exception as e:
        return {"error": str(e)}

@router.post("/voice-bridge/register-template")
async def voice_bridge_register_template(request: Request):
    try:
        body = await request.json()
        name = body.get("name", "")
        voice_config = body.get("voice_config", {})
        tts_engine = body.get("tts_engine", "default")
        result = _voice_bridge.register_template(name, voice_config, tts_engine)
        return result.to_dict() if hasattr(result, "to_dict") else {"success": True}
    except Exception as e:
        return {"error": str(e)}

# ============================================================
# Ecosystem Hub Endpoints
# ============================================================

@router.get("/ecosystem-hub/stats")
async def ecosystem_hub_stats():
    try:
        return _ecosystem_hub.get_stats()
    except Exception as e:
        return {"error": str(e)}

@router.post("/ecosystem-hub/register-service")
async def ecosystem_hub_register_service(request: Request):
    try:
        body = await request.json()
        name = body.get("name", "")
        service_type = body.get("service_type", "")
        endpoint = body.get("endpoint", "")
        capabilities = body.get("capabilities", [])
        result = _ecosystem_hub.register_service(name, service_type, endpoint, capabilities)
        return result.to_dict() if hasattr(result, "to_dict") else {"success": True}
    except Exception as e:
        return {"error": str(e)}

@router.post("/ecosystem-hub/discover-services")
async def ecosystem_hub_discover_services(request: Request):
    try:
        body = await request.json()
        filters = body.get("filters", {})
        max_results = body.get("max_results", 50)
        result = _ecosystem_hub.discover_services(filters, max_results)
        return result.to_dict() if hasattr(result, "to_dict") else {"services": result}
    except Exception as e:
        return {"error": str(e)}

# ============================================================
# Frame Composer Endpoints
# ============================================================

@router.get("/frame-composer/stats")
async def frame_composer_stats():
    try:
        return _frame_composer.get_stats()
    except Exception as e:
        return {"error": str(e)}

@router.post("/frame-composer/submit-command")
async def frame_composer_submit_command(request: Request):
    try:
        body = await request.json()
        command = body.get("command", "")
        parameters = body.get("parameters", {})
        priority = body.get("priority", "normal")
        result = _frame_composer.submit_command(command, parameters, priority)
        return result.to_dict() if hasattr(result, "to_dict") else {"success": True}
    except Exception as e:
        return {"error": str(e)}

@router.post("/frame-composer/compose-frame")
async def frame_composer_compose_frame(request: Request):
    try:
        body = await request.json()
        frame_layout = body.get("frame_layout", {})
        dependencies = body.get("dependencies", [])
        target_profile = body.get("target_profile", "default")
        result = _frame_composer.compose_frame(frame_layout, dependencies, target_profile)
        return result.to_dict() if hasattr(result, "to_dict") else result
    except Exception as e:
        return {"error": str(e)}

# ============================================================
# Spatial Cluster Endpoints
# ============================================================

@router.get("/spatial-cluster/stats")
async def spatial_cluster_stats():
    try:
        return _spatial_cluster.get_stats()
    except Exception as e:
        return {"error": str(e)}

@router.post("/spatial-cluster/initialize-grid")
async def spatial_cluster_initialize_grid(request: Request):
    try:
        body = await request.json()
        grid_size = body.get("grid_size", [100, 100])
        cell_size = body.get("cell_size", 1.0)
        coordinate_system = body.get("coordinate_system", "cartesian")
        result = _spatial_cluster.initialize_grid(grid_size, cell_size, coordinate_system)
        return result.to_dict() if hasattr(result, "to_dict") else {"success": True}
    except Exception as e:
        return {"error": str(e)}

@router.post("/spatial-cluster/register-body")
async def spatial_cluster_register_body(request: Request):
    try:
        body = await request.json()
        body_id = body.get("body_id", "")
        position = body.get("position", [0, 0])
        dimensions = body.get("dimensions", [1, 1])
        body_type = body.get("body_type", "entity")
        result = _spatial_cluster.register_body(body_id, position, dimensions, body_type)
        return result.to_dict() if hasattr(result, "to_dict") else {"success": True}
    except Exception as e:
        return {"error": str(e)}

# ============================================================
# Asset Streamer Endpoints
# ============================================================

@router.get("/asset-streamer/stats")
async def asset_streamer_stats():
    try:
        return _asset_streamer.get_stats()
    except Exception as e:
        return {"error": str(e)}

@router.post("/asset-streamer/register-asset")
async def asset_streamer_register_asset(request: Request):
    try:
        body = await request.json()
        asset_name = body.get("asset_name", "")
        asset_path = body.get("asset_path", "")
        asset_type = body.get("asset_type", "texture")
        metadata = body.get("metadata", {})
        result = _asset_streamer.register_asset(asset_name, asset_path, asset_type, metadata)
        return result.to_dict() if hasattr(result, "to_dict") else {"success": True}
    except Exception as e:
        return {"error": str(e)}

@router.post("/asset-streamer/update-streaming")
async def asset_streamer_update_streaming(request: Request):
    try:
        body = await request.json()
        asset_id = body.get("asset_id", "")
        streaming_config = body.get("streaming_config", {})
        priority = body.get("priority", "normal")
        result = _asset_streamer.update_streaming(asset_id, streaming_config, priority)
        return result.to_dict() if hasattr(result, "to_dict") else {"success": True}
    except Exception as e:
        return {"error": str(e)}

# ============================================================
# Deterministic Replay Endpoints
# ============================================================

@router.get("/deterministic-replay/stats")
async def deterministic_replay_stats():
    try:
        return _deterministic_replay.get_stats()
    except Exception as e:
        return {"error": str(e)}

@router.post("/deterministic-replay/start-recording")
async def deterministic_replay_start_recording(request: Request):
    try:
        body = await request.json()
        session_name = body.get("session_name", "")
        record_inputs = body.get("record_inputs", True)
        record_delta = body.get("record_delta", True)
        result = _deterministic_replay.start_recording(session_name, record_inputs, record_delta)
        return result.to_dict() if hasattr(result, "to_dict") else {"success": True}
    except Exception as e:
        return {"error": str(e)}

@router.post("/deterministic-replay/start-playback")
async def deterministic_replay_start_playback(request: Request):
    try:
        body = await request.json()
        recording_id = body.get("recording_id", "")
        speed = body.get("speed", 1.0)
        loop = body.get("loop", False)
        result = _deterministic_replay.start_playback(recording_id, speed, loop)
        return result.to_dict() if hasattr(result, "to_dict") else {"success": True}
    except Exception as e:
        return {"error": str(e)}

# ============================================================
# Input Abstraction Endpoints
# ============================================================

@router.get("/input-abstraction/stats")
async def input_abstraction_stats():
    try:
        return _input_abstraction.get_stats()
    except Exception as e:
        return {"error": str(e)}

@router.post("/input-abstraction/create-binding")
async def input_abstraction_create_binding(request: Request):
    try:
        body = await request.json()
        action_name = body.get("action_name", "")
        input_source = body.get("input_source", "keyboard")
        input_code = body.get("input_code", "")
        modifiers = body.get("modifiers", [])
        result = _input_abstraction.create_binding(action_name, input_source, input_code, modifiers)
        return result.to_dict() if hasattr(result, "to_dict") else {"success": True}
    except Exception as e:
        return {"error": str(e)}

@router.post("/input-abstraction/process-input")
async def input_abstraction_process_input(request: Request):
    try:
        body = await request.json()
        input_event = body.get("input_event", {})
        context = body.get("context", {})
        result = _input_abstraction.process_input(input_event, context)
        return result.to_dict() if hasattr(result, "to_dict") else result
    except Exception as e:
        return {"error": str(e)}

# ============================================================
# Profile Loader Endpoints
# ============================================================

@router.get("/profile-loader/stats")
async def profile_loader_stats():
    try:
        return _profile_loader.get_stats()
    except Exception as e:
        return {"error": str(e)}

@router.post("/profile-loader/create-profile")
async def profile_loader_create_profile(request: Request):
    try:
        body = await request.json()
        name = body.get("name", "")
        profile_type = body.get("profile_type", "default")
        base_settings = body.get("base_settings", {})
        result = _profile_loader.create_profile(name, profile_type, base_settings)
        return result.to_dict() if hasattr(result, "to_dict") else {"success": True}
    except Exception as e:
        return {"error": str(e)}

@router.post("/profile-loader/add-entry")
async def profile_loader_add_entry(request: Request):
    try:
        body = await request.json()
        profile_id = body.get("profile_id", "")
        key = body.get("key", "")
        value = body.get("value", None)
        entry_type = body.get("entry_type", "setting")
        result = _profile_loader.add_entry(profile_id, key, value, entry_type)
        return result.to_dict() if hasattr(result, "to_dict") else {"success": True}
    except Exception as e:
        return {"error": str(e)}

@router.post("/profile-loader/resolve-profile")
async def profile_loader_resolve_profile(request: Request):
    try:
        body = await request.json()
        profile_id = body.get("profile_id", "")
        resolution_context = body.get("resolution_context", {})
        result = _profile_loader.resolve_profile(profile_id, resolution_context)
        return result.to_dict() if hasattr(result, "to_dict") else result
    except Exception as e:
        return {"error": str(e)}

# ============================================================
# Intent Cascade Endpoints
# ============================================================

@router.get("/intent-cascade/stats")
async def intent_cascade_stats():
    try:
        return _intent_cascade.get_stats()
    except Exception as e:
        return {"error": str(e)}

@router.post("/intent-cascade/resolve")
async def intent_cascade_resolve(request: Request):
    try:
        body = await request.json()
        text = body.get("text", "")
        context = body.get("context", {})
        strategy = body.get("strategy", "default")
        result = _intent_cascade.resolve_intent(text, context, strategy)
        return result.to_dict() if hasattr(result, "to_dict") else result
    except Exception as e:
        return {"error": str(e)}

@router.post("/intent-cascade/rules")
async def intent_cascade_rules(request: Request):
    try:
        body = await request.json()
        domain = body.get("domain", "")
        patterns = body.get("patterns", [])
        action = body.get("action", "")
        result = _intent_cascade.register_intent_rule(domain, patterns, action)
        return result.to_dict() if hasattr(result, "to_dict") else {"success": True}
    except Exception as e:
        return {"error": str(e)}

# ============================================================
# Game Forecaster Endpoints
# ============================================================

@router.get("/game-forecaster/stats")
async def game_forecaster_stats():
    try:
        return _game_forecaster.get_stats()
    except Exception as e:
        return {"error": str(e)}

@router.post("/game-forecaster/simulate")
async def game_forecaster_simulate(request: Request):
    try:
        body = await request.json()
        current_state = body.get("current_state", {})
        parameters = body.get("parameters", {})
        depth = body.get("depth", 10)
        horizon = body.get("horizon", 100)
        result = _game_forecaster.simulate_progression(current_state, parameters, depth, horizon)
        return result.to_dict() if hasattr(result, "to_dict") else result
    except Exception as e:
        return {"error": str(e)}

@router.post("/game-forecaster/analyze")
async def game_forecaster_analyze(request: Request):
    try:
        body = await request.json()
        parameter_name = body.get("parameter_name", "")
        current_value = body.get("current_value", None)
        constraints = body.get("constraints", {})
        result = _game_forecaster.analyze_balance(parameter_name, current_value, constraints)
        return result.to_dict() if hasattr(result, "to_dict") else result
    except Exception as e:
        return {"error": str(e)}

# ============================================================
# Asset Synthesizer Endpoints
# ============================================================

@router.get("/asset-synthesizer/stats")
async def asset_synthesizer_stats():
    try:
        return _asset_synthesizer.get_stats()
    except Exception as e:
        return {"error": str(e)}

@router.post("/asset-synthesizer/synthesize")
async def asset_synthesizer_synthesize(request: Request):
    try:
        body = await request.json()
        description = body.get("description", "")
        category = body.get("category", "general")
        style = body.get("style", "default")
        result = _asset_synthesizer.synthesize_asset(description, category, style)
        return result.to_dict() if hasattr(result, "to_dict") else result
    except Exception as e:
        return {"error": str(e)}

@router.post("/asset-synthesizer/pack")
async def asset_synthesizer_pack(request: Request):
    try:
        body = await request.json()
        theme = body.get("theme", "")
        categories = body.get("categories", [])
        style = body.get("style", "default")
        result = _asset_synthesizer.generate_asset_pack(theme, categories, style)
        return result.to_dict() if hasattr(result, "to_dict") else result
    except Exception as e:
        return {"error": str(e)}

# ============================================================
# Tutorial Orchestrator Endpoints
# ============================================================

@router.get("/tutorial-orchestrator/stats")
async def tutorial_orchestrator_stats():
    try:
        return _tutorial_orchestrator.get_stats()
    except Exception as e:
        return {"error": str(e)}

@router.post("/tutorial-orchestrator/generate")
async def tutorial_orchestrator_generate(request: Request):
    try:
        body = await request.json()
        user_id = body.get("user_id", "")
        objective = body.get("objective", "")
        tutorial_type = body.get("tutorial_type", "interactive")
        result = _tutorial_orchestrator.generate_tutorial(user_id, objective, tutorial_type)
        return result.to_dict() if hasattr(result, "to_dict") else result
    except Exception as e:
        return {"error": str(e)}

@router.post("/tutorial-orchestrator/track")
async def tutorial_orchestrator_track(request: Request):
    try:
        body = await request.json()
        user_id = body.get("user_id", "")
        action = body.get("action", "")
        context = body.get("context", {})
        result = _tutorial_orchestrator.track_behavior(user_id, action, context)
        return result.to_dict() if hasattr(result, "to_dict") else {"success": True}
    except Exception as e:
        return {"error": str(e)}

# ============================================================
# Skybox Renderer Endpoints
# ============================================================

@router.get("/skybox-renderer/stats")
async def skybox_renderer_stats():
    try:
        return _skybox_renderer.get_stats()
    except Exception as e:
        return {"error": str(e)}

@router.post("/skybox-renderer/config")
async def skybox_renderer_config(request: Request):
    try:
        body = await request.json()
        name = body.get("name", "")
        preset = body.get("preset", "default")
        result = _skybox_renderer.create_config(name, preset)
        return result.to_dict() if hasattr(result, "to_dict") else {"success": True}
    except Exception as e:
        return {"error": str(e)}

@router.post("/skybox-renderer/transition")
async def skybox_renderer_transition(request: Request):
    try:
        body = await request.json()
        config_id = body.get("config_id", "")
        duration_seconds = body.get("duration_seconds", 2.0)
        result = _skybox_renderer.transition_to(config_id, duration_seconds)
        return result.to_dict() if hasattr(result, "to_dict") else {"success": True}
    except Exception as e:
        return {"error": str(e)}

# ============================================================
# Trail Renderer Endpoints
# ============================================================

@router.get("/trail-renderer/stats")
async def trail_renderer_stats():
    try:
        return _trail_renderer.get_stats()
    except Exception as e:
        return {"error": str(e)}

@router.post("/trail-renderer/attach")
async def trail_renderer_attach(request: Request):
    try:
        body = await request.json()
        object_id = body.get("object_id", "")
        config_name = body.get("config_name", "default")
        color_start = body.get("color_start", "#ffffff")
        color_end = body.get("color_end", "#000000")
        mode = body.get("mode", "continuous")
        config_result = _trail_renderer.create_config(config_name, color_start, color_end, mode)
        result = _trail_renderer.attach_trail(object_id, config_result)
        return result.to_dict() if hasattr(result, "to_dict") else {"success": True}
    except Exception as e:
        return {"error": str(e)}

@router.post("/trail-renderer/clear")
async def trail_renderer_clear(request: Request):
    try:
        result = _trail_renderer.clear_all()
        return result.to_dict() if hasattr(result, "to_dict") else {"success": True}
    except Exception as e:
        return {"error": str(e)}

# ============================================================
# Procedural Audio Endpoints
# ============================================================

@router.get("/procedural-audio/stats")
async def procedural_audio_stats():
    try:
        return _procedural_audio.get_stats()
    except Exception as e:
        return {"error": str(e)}

@router.post("/procedural-audio/preset")
async def procedural_audio_preset(request: Request):
    try:
        body = await request.json()
        name = body.get("name", "")
        category = body.get("category", "sfx")
        base_frequency = body.get("base_frequency", 440.0)
        waveform = body.get("waveform", "sine")
        result = _procedural_audio.create_preset(name, category, base_frequency, waveform)
        return result.to_dict() if hasattr(result, "to_dict") else {"success": True}
    except Exception as e:
        return {"error": str(e)}

@router.post("/procedural-audio/play")
async def procedural_audio_play(request: Request):
    try:
        body = await request.json()
        category = body.get("category", "sfx")
        position = body.get("position", [0, 0, 0])
        volume = body.get("volume", 1.0)
        result = _procedural_audio.play_sound(category, position, volume)
        return result.to_dict() if hasattr(result, "to_dict") else result
    except Exception as e:
        return {"error": str(e)}

# ============================================================
# Texture Atlas Endpoints
# ============================================================

@router.get("/texture-atlas/stats")
async def texture_atlas_stats():
    try:
        return _texture_atlas.get_stats()
    except Exception as e:
        return {"error": str(e)}

@router.post("/texture-atlas/create")
async def texture_atlas_create(request: Request):
    try:
        body = await request.json()
        name = body.get("name", "")
        width = body.get("width", 1024)
        height = body.get("height", 1024)
        format = body.get("format", "png")
        result = _texture_atlas.create_atlas(name, width, height, format)
        return result.to_dict() if hasattr(result, "to_dict") else {"success": True}
    except Exception as e:
        return {"error": str(e)}

@router.post("/texture-atlas/pack")
async def texture_atlas_pack(request: Request):
    try:
        body = await request.json()
        atlas_id = body.get("atlas_id", "")
        algorithm = body.get("algorithm", "greedy")
        result = _texture_atlas.pack_atlas(atlas_id, algorithm)
        return result.to_dict() if hasattr(result, "to_dict") else result
    except Exception as e:
        return {"error": str(e)}

# ============================================================
# Federated Learner Endpoints
# ============================================================

@router.get("/federated-learner/stats")
async def federated_learner_stats():
    try:
        return _federated_learner.get_stats()
    except Exception as e:
        return {"error": str(e)}

@router.post("/federated-learner/start-round")
async def federated_learner_start_round(request: Request):
    try:
        body = await request.json()
        model_domain = body.get("model_domain", "npc_behavior")
        aggregation = body.get("aggregation", "fed_avg")
        privacy = body.get("privacy", "basic_dp")
        min_clients = body.get("min_clients", 5)
        result = _federated_learner.start_round(model_domain, aggregation, privacy, min_clients)
        return result.to_dict() if hasattr(result, "to_dict") else {"success": True}
    except Exception as e:
        return {"error": str(e)}

@router.post("/federated-learner/submit-update")
async def federated_learner_submit_update(request: Request):
    try:
        body = await request.json()
        round_id = body.get("round_id", "")
        client_id = body.get("client_id", "")
        model_update = body.get("model_update", {})
        data_size = body.get("data_size", 1)
        result = _federated_learner.submit_client_update(round_id, client_id, model_update, data_size)
        return result.to_dict() if hasattr(result, "to_dict") else {"success": True}
    except Exception as e:
        return {"error": str(e)}

@router.post("/federated-learner/aggregate-round")
async def federated_learner_aggregate_round(request: Request):
    try:
        body = await request.json()
        round_id = body.get("round_id", "")
        result = _federated_learner.aggregate_round(round_id)
        return result.to_dict() if hasattr(result, "to_dict") else result
    except Exception as e:
        return {"error": str(e)}

# ============================================================
# Swarm Planner Endpoints
# ============================================================

@router.get("/swarm-planner/stats")
async def swarm_planner_stats():
    try:
        return _swarm_planner.get_stats()
    except Exception as e:
        return {"error": str(e)}

@router.post("/swarm-planner/create-formation")
async def swarm_planner_create_formation(request: Request):
    try:
        body = await request.json()
        name = body.get("name", "")
        formation_type = body.get("formation_type", "circle")
        slot_count = body.get("slot_count", 10)
        spacing = body.get("spacing", 2.0)
        result = _swarm_planner.create_formation(name, formation_type, slot_count, spacing)
        return result.to_dict() if hasattr(result, "to_dict") else {"success": True}
    except Exception as e:
        return {"error": str(e)}

@router.post("/swarm-planner/compute-flock")
async def swarm_planner_compute_flock(request: Request):
    try:
        body = await request.json()
        group_id = body.get("group_id", "")
        agent_position = tuple(body.get("agent_position", [0, 0, 0]))
        neighbor_positions = [tuple(p) for p in body.get("neighbor_positions", [])]
        goal_position = body.get("goal_position")
        if goal_position:
            goal_position = tuple(goal_position)
        result = _swarm_planner.compute_flock_velocity(group_id, agent_position, neighbor_positions, goal_position)
        return {"velocity": result}
    except Exception as e:
        return {"error": str(e)}

@router.post("/swarm-planner/create-group")
async def swarm_planner_create_group(request: Request):
    try:
        body = await request.json()
        name = body.get("name", "")
        max_agents = body.get("max_agents", 50)
        behavior = body.get("behavior", "flock")
        world_bounds = body.get("world_bounds", [0, 0, 1024, 1024])
        result = _swarm_planner.create_group(name, max_agents, behavior, world_bounds)
        return result.to_dict() if hasattr(result, "to_dict") else {"success": True}
    except Exception as e:
        return {"error": str(e)}

@router.post("/swarm-planner/create-tactic")
async def swarm_planner_create_tactic(request: Request):
    try:
        body = await request.json()
        name = body.get("name", "")
        tactic_type = body.get("tactic_type", "ambush")
        target_id = body.get("target_id", "")
        parameters = body.get("parameters", {})
        result = _swarm_planner.create_tactic(name, tactic_type, target_id, parameters)
        return result.to_dict() if hasattr(result, "to_dict") else {"success": True}
    except Exception as e:
        return {"error": str(e)}

# ============================================================
# World Composer Endpoints
# ============================================================

@router.get("/world-composer/stats")
async def world_composer_stats():
    try:
        return _world_composer.get_stats()
    except Exception as e:
        return {"error": str(e)}

@router.post("/world-composer/create-blueprint")
async def world_composer_create_blueprint(request: Request):
    try:
        body = await request.json()
        name = body.get("name", "")
        world_size = body.get("world_size", [1024, 1024])
        seed = body.get("seed", 0)
        biome_count = body.get("biome_count", 5)
        result = _world_composer.create_blueprint(name, world_size, seed, biome_count)
        return result.to_dict() if hasattr(result, "to_dict") else {"success": True}
    except Exception as e:
        return {"error": str(e)}

@router.post("/world-composer/generate-terrain")
async def world_composer_generate_terrain(request: Request):
    try:
        body = await request.json()
        blueprint_id = body.get("blueprint_id", "")
        resolution = body.get("resolution", 256)
        noise_seed = body.get("noise_seed", 42)
        result = _world_composer.generate_terrain(blueprint_id, resolution, noise_seed)
        return result.to_dict() if hasattr(result, "to_dict") else result
    except Exception as e:
        return {"error": str(e)}

@router.post("/world-composer/create-biome")
async def world_composer_create_biome(request: Request):
    try:
        body = await request.json()
        name = body.get("name", "")
        biome_type = body.get("biome_type", "forest")
        temperature = body.get("temperature", 0.5)
        humidity = body.get("humidity", 0.5)
        elevation = body.get("elevation", 0.5)
        result = _world_composer.create_biome(name, biome_type, temperature, humidity, elevation)
        return result.to_dict() if hasattr(result, "to_dict") else {"success": True}
    except Exception as e:
        return {"error": str(e)}

# ============================================================
# Playtest Orchestrator Endpoints
# ============================================================

@router.get("/playtest-orchestrator/stats")
async def playtest_orchestrator_stats():
    try:
        return _playtest_orchestrator.get_stats()
    except Exception as e:
        return {"error": str(e)}

@router.post("/playtest-orchestrator/create-batch")
async def playtest_orchestrator_create_batch(request: Request):
    try:
        body = await request.json()
        name = body.get("name", "")
        session_count = body.get("session_count", 10)
        duration_seconds = body.get("duration_seconds", 300)
        result = _playtest_orchestrator.create_batch(name, session_count, duration_seconds)
        return result.to_dict() if hasattr(result, "to_dict") else {"success": True}
    except Exception as e:
        return {"error": str(e)}

@router.post("/playtest-orchestrator/run-batch")
async def playtest_orchestrator_run_batch(request: Request):
    try:
        body = await request.json()
        batch_id = body.get("batch_id", "")
        result = _playtest_orchestrator.run_batch(batch_id)
        return result.to_dict() if hasattr(result, "to_dict") else result
    except Exception as e:
        return {"error": str(e)}

@router.post("/playtest-orchestrator/generate-report")
async def playtest_orchestrator_generate_report(request: Request):
    try:
        body = await request.json()
        batch_id = body.get("batch_id", "")
        result = _playtest_orchestrator.generate_batch_report(batch_id)
        return result.to_dict() if hasattr(result, "to_dict") else result
    except Exception as e:
        return {"error": str(e)}

# ============================================================
# Particle Emitter Endpoints
# ============================================================

@router.get("/particle-emitter/stats")
async def particle_emitter_stats():
    try:
        return _particle_emitter.get_stats()
    except Exception as e:
        return {"error": str(e)}

@router.post("/particle-emitter/create-config")
async def particle_emitter_create_config(request: Request):
    try:
        body = await request.json()
        name = body.get("name", "")
        max_particles = body.get("max_particles", 1000)
        emission_rate = body.get("emission_rate", 100)
        lifetime = body.get("lifetime", 2.0)
        result = _particle_emitter.create_config(name, max_particles, emission_rate, lifetime)
        return result.to_dict() if hasattr(result, "to_dict") else {"success": True}
    except Exception as e:
        return {"error": str(e)}

@router.post("/particle-emitter/spawn")
async def particle_emitter_spawn(request: Request):
    try:
        body = await request.json()
        config_name = body.get("config_name", "")
        position = body.get("position", [0, 0, 0])
        preset = body.get("preset", "default")
        result = _particle_emitter.spawn_emitter(config_name, position, preset)
        return result.to_dict() if hasattr(result, "to_dict") else {"success": True}
    except Exception as e:
        return {"error": str(e)}

@router.post("/particle-emitter/spawn-preset")
async def particle_emitter_spawn_preset(request: Request):
    try:
        body = await request.json()
        preset_name = body.get("preset_name", "fire")
        position = body.get("position", [0, 0, 0])
        result = _particle_emitter.spawn_preset(preset_name, position)
        return result.to_dict() if hasattr(result, "to_dict") else {"success": True}
    except Exception as e:
        return {"error": str(e)}

# ============================================================
# LOD Gate Endpoints
# ============================================================

@router.get("/lod-gate/stats")
async def lod_gate_stats():
    try:
        return _lod_gate.get_stats()
    except Exception as e:
        return {"error": str(e)}

@router.post("/lod-gate/create-profile")
async def lod_gate_create_profile(request: Request):
    try:
        body = await request.json()
        name = body.get("name", "")
        max_distance = body.get("max_distance", 1000.0)
        level_count = body.get("level_count", 3)
        result = _lod_gate.create_profile(name, max_distance, level_count)
        return result.to_dict() if hasattr(result, "to_dict") else {"success": True}
    except Exception as e:
        return {"error": str(e)}

@router.post("/lod-gate/compute-lod")
async def lod_gate_compute_lod(request: Request):
    try:
        body = await request.json()
        object_id = body.get("object_id", "")
        camera_position = body.get("camera_position", [0, 0, 0])
        screen_height = body.get("screen_height", 1080)
        result = _lod_gate.compute_lod(object_id, camera_position, screen_height)
        return result.to_dict() if hasattr(result, "to_dict") else result
    except Exception as e:
        return {"error": str(e)}

@router.post("/lod-gate/register-group")
async def lod_gate_register_group(request: Request):
    try:
        body = await request.json()
        group_name = body.get("group_name", "")
        mesh_ids = body.get("mesh_ids", [])
        result = _lod_gate.register_group(group_name, mesh_ids)
        return result.to_dict() if hasattr(result, "to_dict") else {"success": True}
    except Exception as e:
        return {"error": str(e)}

@router.post("/lod-gate/add-level")
async def lod_gate_add_level(request: Request):
    try:
        body = await request.json()
        profile_name = body.get("profile_name", "")
        distance = body.get("distance", 100.0)
        reduction = body.get("reduction", 0.5)
        result = _lod_gate.add_lod_level(profile_name, distance, reduction)
        return result.to_dict() if hasattr(result, "to_dict") else {"success": True}
    except Exception as e:
        return {"error": str(e)}

@router.post("/lod-gate/update-camera")
async def lod_gate_update_camera(request: Request):
    try:
        body = await request.json()
        camera_position = body.get("camera_position", [0, 0, 0])
        camera_fov = body.get("camera_fov", 60.0)
        screen_height = body.get("screen_height", 1080)
        result = _lod_gate.compute_lod("all", camera_position, screen_height)
        return result.to_dict() if hasattr(result, "to_dict") else result
    except Exception as e:
        return {"error": str(e)}

# ============================================================
# Scene Stack Endpoints
# ============================================================

@router.get("/scene-stack/stats")
async def scene_stack_stats():
    try:
        return _scene_stack.get_stats()
    except Exception as e:
        return {"error": str(e)}

@router.post("/scene-stack/register-scene")
async def scene_stack_register_scene(request: Request):
    try:
        body = await request.json()
        name = body.get("name", "")
        scene_type = body.get("scene_type", "level")
        persistent = body.get("persistent", False)
        result = _scene_stack.register_scene(name, scene_type, persistent)
        return result.to_dict() if hasattr(result, "to_dict") else {"success": True}
    except Exception as e:
        return {"error": str(e)}

@router.post("/scene-stack/load-scene")
async def scene_stack_load_scene(request: Request):
    try:
        body = await request.json()
        scene_id = body.get("scene_id", "")
        additive = body.get("additive", False)
        result = _scene_stack.load_scene(scene_id, additive)
        return result.to_dict() if hasattr(result, "to_dict") else result
    except Exception as e:
        return {"error": str(e)}

@router.post("/scene-stack/push-overlay")
async def scene_stack_push_overlay(request: Request):
    try:
        body = await request.json()
        scene_id = body.get("scene_id", "")
        overlay_type = body.get("overlay_type", "modal")
        duration = body.get("duration", 0.5)
        result = _scene_stack.create_transition(scene_id, overlay_type, duration, 0)
        return result.to_dict() if hasattr(result, "to_dict") else {"success": True}
    except Exception as e:
        return {"error": str(e)}

# ============================================================
# NavMesh Forge Endpoints
# ============================================================

@router.get("/navmesh-forge/stats")
async def navmesh_forge_stats():
    try:
        return _navmesh_forge.get_stats()
    except Exception as e:
        return {"error": str(e)}

@router.post("/navmesh-forge/create-mesh")
async def navmesh_forge_create_mesh(request: Request):
    try:
        body = await request.json()
        name = body.get("name", "")
        bounds = body.get("bounds", [0, 0, 1024, 1024])
        cell_size = body.get("cell_size", 1.0)
        agent_radius = body.get("agent_radius", 0.5)
        result = _navmesh_forge.create_mesh(name, bounds, cell_size, agent_radius)
        return result.to_dict() if hasattr(result, "to_dict") else {"success": True}
    except Exception as e:
        return {"error": str(e)}

@router.post("/navmesh-forge/find-path")
async def navmesh_forge_find_path(request: Request):
    try:
        body = await request.json()
        mesh_id = body.get("mesh_id", "")
        start = body.get("start", [0, 0, 0])
        end = body.get("end", [10, 0, 10])
        algorithm = body.get("algorithm", "astar")
        result = _navmesh_forge.find_path(mesh_id, start, end, algorithm)
        return result.to_dict() if hasattr(result, "to_dict") else result
    except Exception as e:
        return {"error": str(e)}

@router.post("/navmesh-forge/add-region")
async def navmesh_forge_add_region(request: Request):
    try:
        body = await request.json()
        mesh_id = body.get("mesh_id", "")
        region_id = body.get("region_id", "")
        vertices = body.get("vertices", [])
        area_type = body.get("area_type", "walkable")
        result = _navmesh_forge.add_region(mesh_id, region_id, vertices, area_type)
        return result.to_dict() if hasattr(result, "to_dict") else {"success": True}
    except Exception as e:
        return {"error": str(e)}

@router.post("/navmesh-forge/add-obstacle")
async def navmesh_forge_add_obstacle(request: Request):
    try:
        body = await request.json()
        mesh_id = body.get("mesh_id", "")
        obstacle_id = body.get("obstacle_id", "")
        position = body.get("position", [0, 0, 0])
        size = body.get("size", [1, 1, 1])
        result = _navmesh_forge.add_obstacle(mesh_id, obstacle_id, position, size)
        return result.to_dict() if hasattr(result, "to_dict") else {"success": True}
    except Exception as e:
        return {"error": str(e)}

# ============================================================
# Reasoning Chain Endpoints
# ============================================================

@router.get("/reasoning-chain/stats")
async def reasoning_chain_stats():
    try:
        return _reasoning_chain.get_stats()
    except Exception as e:
        return {"error": str(e)}

@router.post("/reasoning-chain/start-chain")
async def reasoning_chain_start_chain(request: Request):
    try:
        body = await request.json()
        result = _reasoning_chain.start_chain(body["query"], body.get("mode", "chain_of_thought"), body.get("max_steps", 10))
        return result.to_dict() if hasattr(result, "to_dict") else {"success": True}
    except Exception as e:
        return {"error": str(e)}

@router.post("/reasoning-chain/verify")
async def reasoning_chain_verify(request: Request):
    try:
        body = await request.json()
        result = _reasoning_chain.verify_chain(body["chain_id"])
        return result.to_dict() if hasattr(result, "to_dict") else {"success": True}
    except Exception as e:
        return {"error": str(e)}

# ============================================================
# Memory Hierarchy Endpoints
# ============================================================

@router.get("/memory-hierarchy/stats")
async def memory_hierarchy_stats():
    try:
        return _memory_hierarchy.get_stats()
    except Exception as e:
        return {"error": str(e)}

@router.post("/memory-hierarchy/store")
async def memory_hierarchy_store(request: Request):
    try:
        body = await request.json()
        result = _memory_hierarchy.store(body["tier"], body["content"], body.get("priority", "medium"), body.get("tags"))
        return result.to_dict() if hasattr(result, "to_dict") else {"success": True}
    except Exception as e:
        return {"error": str(e)}

@router.post("/memory-hierarchy/retrieve")
async def memory_hierarchy_retrieve(request: Request):
    try:
        body = await request.json()
        result = _memory_hierarchy.retrieve(body["query_text"], body.get("strategy", "hybrid"), body.get("top_k", 5))
        return result.to_dict() if hasattr(result, "to_dict") else {"success": True}
    except Exception as e:
        return {"error": str(e)}

# ============================================================
# Tool Registry Endpoints
# ============================================================

@router.get("/tool-registry/stats")
async def tool_registry_stats():
    try:
        return _tool_registry.get_stats()
    except Exception as e:
        return {"error": str(e)}

@router.post("/tool-registry/register")
async def tool_registry_register(request: Request):
    try:
        body = await request.json()
        result = _tool_registry.register_tool(body["name"], body["description"], body.get("category", "utility"), body.get("parameters", []))
        return result.to_dict() if hasattr(result, "to_dict") else {"success": True}
    except Exception as e:
        return {"error": str(e)}

@router.post("/tool-registry/invoke")
async def tool_registry_invoke(request: Request):
    try:
        body = await request.json()
        result = _tool_registry.record_invocation(body["tool_name"], body.get("parameters", {}), body.get("result"), body.get("error"), body.get("duration_ms", 0))
        return result.to_dict() if hasattr(result, "to_dict") else {"success": True}
    except Exception as e:
        return {"error": str(e)}

# ============================================================
# Prompt Library Endpoints
# ============================================================

@router.get("/prompt-library/stats")
async def prompt_library_stats():
    try:
        return _prompt_library.get_stats()
    except Exception as e:
        return {"error": str(e)}

@router.post("/prompt-library/create")
async def prompt_library_create(request: Request):
    try:
        body = await request.json()
        result = _prompt_library.create_template(body["name"], body.get("category", "custom"), body["content"], body.get("variables"))
        return result.to_dict() if hasattr(result, "to_dict") else {"success": True}
    except Exception as e:
        return {"error": str(e)}

@router.post("/prompt-library/assemble")
async def prompt_library_assemble(request: Request):
    try:
        body = await request.json()
        result = _prompt_library.assemble_prompt(body.get("template_names", []), body.get("variables", {}))
        return result.to_dict() if hasattr(result, "to_dict") else {"success": True}
    except Exception as e:
        return {"error": str(e)}

# ============================================================
# Reflection Loop Endpoints
# ============================================================

@router.get("/reflection-loop/stats")
async def reflection_loop_stats():
    try:
        return _reflection_loop.get_stats()
    except Exception as e:
        return {"error": str(e)}

@router.post("/reflection-loop/record")
async def reflection_loop_record(request: Request):
    try:
        body = await request.json()
        result = _reflection_loop.record_outcome(body["reflection_type"], body.get("context", {}), body["decision_summary"], body["outcome"])
        return result.to_dict() if hasattr(result, "to_dict") else {"success": True}
    except Exception as e:
        return {"error": str(e)}

@router.post("/reflection-loop/insights")
async def reflection_loop_insights(request: Request):
    try:
        body = await request.json()
        result = _reflection_loop.generate_insights(body.get("min_confidence", 0.6))
        return result.to_dict() if hasattr(result, "to_dict") else {"success": True}
    except Exception as e:
        return {"error": str(e)}

# ============================================================
# Procedural Synthesis Endpoints
# ============================================================

@router.get("/procedural-synthesis/stats")
async def procedural_synthesis_stats():
    try:
        return _procedural_synthesis.get_stats()
    except Exception as e:
        return {"error": str(e)}

@router.post("/procedural-synthesis/terrain")
async def procedural_synthesis_terrain(request: Request):
    try:
        body = await request.json()
        result = _procedural_synthesis.generate_terrain(body.get("width", 256), body.get("height", 256), body.get("seed", 42), body.get("algorithm", "perlin_noise"))
        return result.to_dict() if hasattr(result, "to_dict") else {"success": True}
    except Exception as e:
        return {"error": str(e)}

@router.post("/procedural-synthesis/layout")
async def procedural_synthesis_layout(request: Request):
    try:
        body = await request.json()
        result = _procedural_synthesis.generate_layout(body.get("algorithm", "wave_function_collapse"), body.get("width", 64), body.get("height", 64), body.get("seed", 42), body.get("room_count", 8))
        return result.to_dict() if hasattr(result, "to_dict") else {"success": True}
    except Exception as e:
        return {"error": str(e)}

# ============================================================
# Asset Bundler Endpoints
# ============================================================

@router.get("/asset-bundler/stats")
async def asset_bundler_stats():
    try:
        return _asset_bundler.get_stats()
    except Exception as e:
        return {"error": str(e)}

@router.post("/asset-bundler/register")
async def asset_bundler_register(request: Request):
    try:
        body = await request.json()
        result = _asset_bundler.register_asset(body["path"], body.get("asset_type", "data"), body["size_bytes"], body["hash"])
        return result.to_dict() if hasattr(result, "to_dict") else {"success": True}
    except Exception as e:
        return {"error": str(e)}

@router.post("/asset-bundler/create-bundle")
async def asset_bundler_create_bundle(request: Request):
    try:
        body = await request.json()
        result = _asset_bundler.create_bundle(body["name"], body.get("asset_ids", []), body.get("compression", "lz4"))
        return result.to_dict() if hasattr(result, "to_dict") else {"success": True}
    except Exception as e:
        return {"error": str(e)}

# ============================================================
# Deterministic Recorder Endpoints
# ============================================================

@router.get("/deterministic-recorder/stats")
async def deterministic_recorder_stats():
    try:
        return _deterministic_recorder.get_stats()
    except Exception as e:
        return {"error": str(e)}

@router.post("/deterministic-recorder/start")
async def deterministic_recorder_start(request: Request):
    try:
        body = await request.json()
        result = _deterministic_recorder.start_recording(body.get("name", ""), body.get("mode", "hybrid"))
        return result.to_dict() if hasattr(result, "to_dict") else {"success": True}
    except Exception as e:
        return {"error": str(e)}

@router.post("/deterministic-recorder/stop")
async def deterministic_recorder_stop(request: Request):
    try:
        body = await request.json()
        result = _deterministic_recorder.stop_recording()
        return result.to_dict() if hasattr(result, "to_dict") else {"success": True}
    except Exception as e:
        return {"error": str(e)}

# ============================================================
# Localization Hub Endpoints
# ============================================================

@router.get("/localization-hub/stats")
async def localization_hub_stats():
    try:
        return _localization_hub.get_stats()
    except Exception as e:
        return {"error": str(e)}

@router.post("/localization-hub/add")
async def localization_hub_add(request: Request):
    try:
        body = await request.json()
        result = _localization_hub.add_translation(body["key"], body["text"], body.get("language", "en_us"))
        return result.to_dict() if hasattr(result, "to_dict") else {"success": True}
    except Exception as e:
        return {"error": str(e)}

@router.post("/localization-hub/translate")
async def localization_hub_translate(request: Request):
    try:
        body = await request.json()
        result = _localization_hub.translate(body["key"], body.get("language", "en_us"), body.get("variables"))
        return result.to_dict() if hasattr(result, "to_dict") else {"success": True}
    except Exception as e:
        return {"error": str(e)}

# ============================================================
# Agent Subsystem & Engine Routes (v2)
# ============================================================

from sparkai.agent.agent_memory_consolidator import get_memory_consolidator
from sparkai.agent.agent_delegation_broker import get_delegation_broker
from sparkai.engine.engine_event_scripting import get_event_scripting
from sparkai.engine.engine_component_assembler import get_component_assembler
from sparkai.engine.engine_signal_bus import get_signal_bus as get_engine_signal_bus_v2
from sparkai.agent.agent_skill_forge import get_skill_forge as get_agent_skill_forge
from sparkai.agent.agent_game_design_intelligence import get_game_design_intelligence
from sparkai.engine.engine_game_state_analyzer import get_game_state_analyzer
from sparkai.agent.agent_interaction_synthesis import get_interaction_synthesis_engine
from sparkai.engine.engine_game_runtime_orchestrator import get_game_runtime_orchestrator

_skill_forge = get_agent_skill_forge()
_memory_consolidator = get_memory_consolidator()
_delegation_broker = get_delegation_broker()
_component_assembler = get_component_assembler()
_event_scripting = get_event_scripting()
_signal_bus_runtime = get_engine_signal_bus_v2()
_game_design_intelligence = get_game_design_intelligence()
_game_state_analyzer = get_game_state_analyzer()
_interaction_synthesis_engine = get_interaction_synthesis_engine()
_game_runtime_orchestrator = get_game_runtime_orchestrator()

# ============================================================
# SkillForge Endpoints
# ============================================================

@router.get("/skill-forge/stats")
async def skill_forge_stats():
    try:
        return _skill_forge.get_stats()
    except Exception as e:
        return {"error": str(e)}

@router.post("/skill-forge/create-skill")
async def skill_forge_create_skill(request: Request):
    try:
        body = await request.json()
        result = _skill_forge.create_skill(
            description=body.get("description", ""),
            result_json=body.get("result_json"),
            category=body.get("category", ""),
            tags=body.get("tags", []),
        )
        return result.to_dict()
    except Exception as e:
        return {"error": str(e)}

@router.post("/skill-forge/execute-skill")
async def skill_forge_execute_skill(request: Request):
    try:
        body = await request.json()
        result = _skill_forge.execute_skill(
            skill_id=body.get("skill_id", ""),
            dry_run=body.get("dry_run", False),
        )
        return result
    except Exception as e:
        return {"error": str(e)}

# ============================================================
# LearningLoop Endpoints
# ============================================================

@router.post("/learning-loop/start")
async def learning_loop_start(request: Request):
    try:
        body = await request.json()
        result = _learning_loop.start_loop(query=body.get("query", ""))
        return result.to_dict()
    except Exception as e:
        return {"error": str(e)}

@router.post("/learning-loop/advance")
async def learning_loop_advance(request: Request):
    try:
        body = await request.json()
        _learning_loop.advance_phase(
            session_id=body.get("session_id", ""),
            state=body.get("state", {}),
        )
        return {"success": True}
    except Exception as e:
        return {"error": str(e)}

# ============================================================
# MemoryConsolidator Endpoints
# ============================================================

@router.get("/memory-consolidator/stats")
async def memory_consolidator_stats():
    try:
        return _memory_consolidator.get_stats()
    except Exception as e:
        return {"error": str(e)}

@router.post("/memory-consolidator/add")
async def memory_consolidator_add(request: Request):
    try:
        body = await request.json()
        result = _memory_consolidator.add_fragment(
            content=body.get("content", ""),
            fragment_type=body.get("fragment_type", ""),
            source_session=body.get("source_session", ""),
            keywords=body.get("keywords", []),
            importance_score=body.get("importance_score", 0.5),
        )
        return result.to_dict()
    except Exception as e:
        return {"error": str(e)}

@router.post("/memory-consolidator/consolidate")
async def memory_consolidator_consolidate(request: Request):
    try:
        body = await request.json()
        result = _memory_consolidator.consolidate(strategy=body.get("strategy", ""))
        return result.to_dict()
    except Exception as e:
        return {"error": str(e)}

# ============================================================
# DelegationBroker Endpoints
# ============================================================

@router.get("/delegation-broker/stats")
async def delegation_broker_stats():
    try:
        return _delegation_broker.get_stats()
    except Exception as e:
        return {"error": str(e)}

@router.post("/delegation-broker/register")
async def delegation_broker_register(request: Request):
    try:
        body = await request.json()
        result = _delegation_broker.register_agent(
            name=body.get("name", ""),
            role=body.get("role", ""),
            capabilities=body.get("capabilities", []),
        )
        return result.to_dict()
    except Exception as e:
        return {"error": str(e)}

@router.post("/delegation-broker/assign")
async def delegation_broker_assign(request: Request):
    try:
        body = await request.json()
        result = _delegation_broker.assign_task(
            task_description=body.get("task_description", ""),
            strategy=body.get("strategy", ""),
        )
        if result is None:
            return {"error": "No suitable agent found for the task"}
        return result.to_dict()
    except Exception as e:
        return {"error": str(e)}

# ============================================================
# EventScripting Endpoints
# ============================================================

@router.get("/event-scripting-runtime/stats")
async def event_scripting_runtime_stats():
    try:
        return _event_scripting.get_stats()
    except Exception as e:
        return {"error": str(e)}

@router.post("/event-scripting-runtime/create-rule")
async def event_scripting_runtime_create_rule(request: Request):
    try:
        body = await request.json()
        result = _event_scripting.create_rule(
            name=body.get("name", ""),
            sheet_id=body.get("sheet_id", ""),
        )
        if result is None:
            return {"error": "Rule creation failed - sheet not found or full"}
        if body.get("conditions"):
            for cond in body["conditions"]:
                _event_scripting.add_condition(
                    rule_id=result.id,
                    condition_type=cond.get("type", ""),
                    target=cond.get("target", ""),
                    property=cond.get("field", cond.get("property", "")),
                    operator=cond.get("operator", ""),
                    value=cond.get("value", ""),
                )
        if body.get("actions"):
            for act in body["actions"]:
                _event_scripting.add_action(
                    rule_id=result.id,
                    action_type=act.get("type", ""),
                    target=act.get("target", ""),
                    parameters=act.get("parameters", {}),
                )
        return result.to_dict()
    except Exception as e:
        return {"error": str(e)}

@router.post("/event-scripting-runtime/evaluate")
async def event_scripting_runtime_evaluate(request: Request):
    try:
        body = await request.json()
        result = _event_scripting.process_event_sheet(
            sheet_id=body.get("sheet_id", ""),
        )
        return result
    except Exception as e:
        return {"error": str(e)}

# ============================================================
# ComponentAssembler Endpoints
# ============================================================

@router.get("/component-assembler/stats")
async def component_assembler_stats():
    try:
        return _component_assembler.get_stats()
    except Exception as e:
        return {"error": str(e)}

@router.post("/component-assembler/register-component")
async def component_assembler_register_component(request: Request):
    try:
        body = await request.json()
        result = _component_assembler.register_component(
            name=body.get("name", ""),
            component_type=body.get("component_type", ""),
            properties=body.get("properties", {}),
            dependencies=body.get("dependencies", []),
            provides=body.get("provides", []),
        )
        return result.to_dict()
    except Exception as e:
        return {"error": str(e)}

@router.post("/component-assembler/assemble")
async def component_assembler_assemble(request: Request):
    try:
        body = await request.json()
        result = _component_assembler.assemble_entity(
            archetype_id=body.get("archetype_id", ""),
            parent_entity_id=body.get("entity_name", ""),
            state_overrides=body.get("state_overrides", {}),
        )
        if result is None:
            return {"error": "Assembly failed - archetype not found or invalid dependencies"}
        return result.to_dict()
    except Exception as e:
        return {"error": str(e)}

# ============================================================
# SignalBus Engine Endpoints
# ============================================================

@router.post("/signal-bus/define")
async def signal_bus_runtime_define(request: Request):
    try:
        body = await request.json()
        signal_id = _signal_bus_runtime.define_signal(
            name=body.get("name", ""),
            description=body.get("description", ""),
            parameters=body.get("parameters", {}),
            category=body.get("category", ""),
        )
        return {"success": True, "signal_id": signal_id}
    except Exception as e:
        return {"error": str(e)}
