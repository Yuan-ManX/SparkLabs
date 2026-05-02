"""
SparkAI Agent - Runtime

The unified execution engine that orchestrates all agent systems
into a cohesive AI-native game engine. The runtime is the top-level
entry point that initializes, connects, and manages all subsystems.

Runtime architecture:
  AgentRuntime
    |-- Event Bus (inter-module communication)
    |-- Game Context (game state management)
    |-- LLM Router (intelligent model selection)
    |-- Tool Executor (validated tool execution)
    |-- Agent Orchestrator (multi-agent coordination)
    |-- Session Manager (persistent sessions)
    |-- Memory System (episodic/semantic/procedural)
    |-- Command Registry (slash commands)
    |-- Hook Manager (event-driven validation)
    |-- Rule Engine (coding standards)
    |-- Team Orchestrator (team workflows)
    |-- Game Bench (quality evaluation)
    |-- Pipeline (game generation)
    |-- Agent Protocol (inter-agent messaging)
    |-- Skill Forge (dynamic skill creation/evolution)
    |-- Agent Mesh (collaboration network)
    |-- Health Checker (runtime diagnostics)
    |-- Game Coder (end-to-end code generation)
    |-- World Builder (procedural world generation)
    |-- Game Skill System (template + debug skill evolution)
    |-- Quality Gate System (automated quality verification)
    |-- Workflow Skill System (structured dev workflow commands)
    |-- Agent Session Manager (deep session management with threading)
    |-- Game Pipeline System (end-to-end game creation pipeline)
    |-- Studio Coordinator (full studio hierarchy coordination)
    |-- Agent Swarm (collective intelligence and consensus)
    |-- Studio Command System (35+ slash commands for game dev)
    |-- Game Template Library (16 genre templates with scaffolding)
    |-- Blueprint Engine (spec-driven game design system)
    |-- Playtest Engine (automated playtesting and evaluation)
    |-- Composer Engine (multi-agent task composition)
    |-- Knowledge Graph (structured knowledge base)
    |-- Tool Chain Engine (dynamic tool composition)
    |-- Reflex Engine (self-improving feedback loop)
    |-- Dialogue Engine (NPC conversations and narrative)
    |-- Asset Pipeline Engine (game asset management)
    |-- Validator Engine (code and asset validation)
    |-- Orchestrator Engine (unified agent orchestration)
    |-- Skill Evolution Engine (skill learning and adaptation)
    |-- Game Evaluator Engine (game quality evaluation)
    |-- Session Compaction Engine (context window management)
    |-- Recovery Engine (automatic failure recovery)
    |-- Tool Permission System (role-based access control)
    |-- Context Compression Engine (pluggable compression)
    |-- Debug Protocol Engine (self-improving debug knowledge)
    |-- Autowork Engine (three-phase plan/execute/verify enforcement)
    |-- Policy Engine (declarative condition/action rule system)
    |-- Mixture of Agents Engine (multi-model parallel reasoning)
    |-- Structured Protocol Engine (schema-validated message contracts)
    |-- Credential Manager (key pooling, rotation, access auditing)
    |-- Sandbox Engine (isolated tool execution with resource limits)
    |-- Asset Consistency Engine (key chain validation across generation)
    |-- Memory Persistence Engine (disk-based state checkpointing)
    |-- Skill Curator (autonomous skill lifecycle management)
    |-- Prompt Builder (layered system prompt construction)
    |-- Intent Classifier (prompt intent detection and routing)
    |-- Execution Budget (token/cost tracking and enforcement)
    |-- Approval Engine (action gate with trust tier escalation)
    |-- Checkpoint Manager (session state snapshot and rollback)
    |-- Game Loop (ordered execution phases with time management)
    |-- Signal Bus (decoupled signal/slot communication)
    |-- Animation Player (keyframe playback and tweening)
    |-- Collision System (spatial hash broad-phase detection)
    |-- Input Manager (unified keyboard/mouse/touch input)
    |-- Code Execution Sandbox (isolated code execution with AST validation)
    |-- File Safety Controller (path-based access control)
    |-- Guard System (content threat scanning and trust tiering)
    |-- Interrupt System (thread-scoped session interruption)
    |-- Result Storage (structured tool output caching and query)
    |-- Physics System (rigid body 2D dynamics with constraints)
    |-- Particle System (configurable emitter engine)
    |-- Pathfinding System (A* grid-based navigation)
    |-- Audio System (channels, 3D spatial, playback)
    |-- State Machine (hierarchical FSM with transitions)
    |-- Resource Manager (lazy-loading asset cache with ref counting)
    |-- Behavior System (modular entity behavior composition)
    |-- Tilemap System (multi-layer grid map engine)
    |-- Self Evaluator (quality assessment with dimension rubrics)
    |-- Strategic Planner (task decomposition with DAG dependency management)
    |-- Circuit Breaker (API resilience with sliding window failure tracking)
    |-- Persona System (role-based agent profiles with tool grants)
    |-- Camera System (dynamic 2D viewport with parallax and shake)
    |-- Serializer (schema-versioned scene/entity serialization)
    |-- UI System (retained-mode widget tree with theme support)
    |-- Layer System (z-ordered rendering with blend modes)
    |-- Profiler (frame timing, memory tracking, bottleneck detection)
    |-- Streaming Manager (real-time chunked response streaming)
    |-- Delegation System (isolated subagent spawning and execution)
    |-- MCP Bridge (model context protocol server integration)
    |-- Parallel Executor (multi-provider concurrent task dispatch)
    |-- Event Scripting System (condition/action event sheets)
    |-- Scene Tree (hierarchical node graph with groups)
    |-- Shader System (built-in 2D shaders with materials)
    |-- Variable System (scoped typed variables with expressions)
    |-- Resource Loader (LRU-cached asset loading pipeline)
    |-- Content Safety (PII redaction, unsafe content filtering)
    |-- Title Generator (dynamic project/session/asset naming)
    |-- Shell Hooks (sandboxed command execution with hooks)
    |-- Skill Preprocessor (parameter validation and normalization)
    |-- Inventory System (item management with categories/equipping)
    |-- Localization System (multi-language string tables)
    |-- Achievement System (progress tracking and unlock rewards)
    |-- Cloud Sync (cloud save with conflict resolution)
    |-- Rate Limiter (multi-strategy API rate limiting)
    |-- Retry System (exponential backoff with circuit breaker)
    |-- Web Browser (controlled URL fetching with domain safety)
    |-- Session Search (inverted index full-text session search)
    |-- Object Pool System (pre-allocated object reuse with strategies)
    |-- Lighting System (2D dynamic lighting with point/directional lights)
    |-- Font System (font management with glyph metrics and layout)
    |-- Plugin System (extensible plugin architecture with hooks)
    |-- Observability (distributed tracing, metrics, logging)
    |-- Output Limiter (content size control and sanitization)
    |-- Context Engine (context window management and compaction)
    |-- Skill Discovery (dynamic tool/capability discovery)
    |-- Effects System (post-processing visual pipeline)
    |-- Input Mapping (action-based rebindable controls)
    |-- Undo/Redo System (editor command history)
    |-- Sprite Sheet (frame-based sprite animation)
    |-- Prompt Cache (LLM response caching with fingerprinting)
    |-- Trajectory Recorder (full session event timeline logging)
    |-- Checkpoint System (state snapshot with rollback/rollforward)
    |-- Budget Tracker (token cost tracking with alert thresholds)
    |-- Tween System (19-curve property animation library)
    |-- Node Path System (path-based game object referencing)
    |-- Project Template System (12-genre game scaffolding)
    |-- Asset Pipeline (end-to-end asset lifecycle management)

The runtime provides a single initialization point and unified
API for all engine operations. It manages the lifecycle of all
subsystems and ensures they are properly connected.
"""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

from sparkai.agent.events import EventBus, Event, EventChannel, get_event_bus
from sparkai.agent.context import GameContext, get_game_context, PipelinePhase
from sparkai.agent.llm_router import LLMRouter, TaskType
from sparkai.agent.executor import ToolExecutor, ExecutionResult, ChainStep
from sparkai.agent.orchestrator import AgentOrchestrator
from sparkai.agent.session import SessionManager, AgentSession
from sparkai.agent.memory_v2 import AgentMemorySystem
from sparkai.agent.commands import CommandRegistry, SlashCommand
from sparkai.agent.hooks import HookManager
from sparkai.agent.rules import RuleEngine
from sparkai.agent.team_orch import TeamOrchestrator
from sparkai.agent.bench import GameBench
from sparkai.agent.loop import AgentLoop, Pipeline
from sparkai.agent.base import SparkAgent, AgentRole, AgentCapability
from sparkai.agent.llm import LLMProvider, LLMConfig
from sparkai.agent.toolkit import ToolRegistry, ToolsetRegistry
from sparkai.agent.protocol import AgentProtocol, ProtocolMessage, MessageType, get_protocol
from sparkai.agent.skill_forge import SkillForge, SkillBlueprint, get_skill_forge
from sparkai.agent.mesh import AgentMesh, AgentNode, NodeState, get_agent_mesh
from sparkai.agent.health import HealthChecker, HealthReport, HealthStatus, get_health_checker
from sparkai.agent.game_coder import GameCoder, get_game_coder
from sparkai.agent.world_builder import WorldBuilder, get_world_builder
from sparkai.agent.game_skill import GameSkillSystem, get_game_skill_system
from sparkai.agent.quality_gate import QualityGateSystem, get_quality_gate_system
from sparkai.agent.workflow_skills import WorkflowSkillSystem, get_workflow_skill_system
from sparkai.agent.agent_session import AgentSessionManager, get_agent_session_manager
from sparkai.agent.game_pipeline import GamePipelineSystem, get_game_pipeline_system
from sparkai.agent.studio_coordinator import StudioCoordinator, get_studio_coordinator
from sparkai.agent.agent_swarm import AgentSwarm, get_agent_swarm
from sparkai.agent.studio_command import StudioCommandSystem, get_studio_command_system
from sparkai.agent.game_template import GameTemplateLibrary, get_game_template_library
from sparkai.agent.agent_blueprint import BlueprintEngine, get_blueprint_engine
from sparkai.agent.agent_playtest import PlaytestEngine, get_playtest_engine
from sparkai.agent.agent_composer import ComposerEngine, get_composer_engine
from sparkai.agent.agent_knowledge import KnowledgeGraph, get_knowledge_graph
from sparkai.agent.agent_toolchain import ToolChainEngine, get_toolchain_engine
from sparkai.agent.agent_reflex import ReflexEngine, get_reflex_engine
from sparkai.agent.agent_dialogue import DialogueEngine, get_dialogue_engine
from sparkai.agent.agent_asset import AssetPipelineEngine, get_asset_engine
from sparkai.agent.agent_validator import ValidatorEngine, get_validator_engine
from sparkai.agent.agent_orchestrator import OrchestratorEngine, get_orchestrator_engine
from sparkai.agent.agent_skill_evolution import SkillEvolutionEngine, get_skill_evolution_engine
from sparkai.agent.agent_evaluator import GameEvaluatorEngine, get_game_evaluator
from sparkai.agent.agent_lifecycle import AgentLifecycleManager
from sparkai.agent.agent_slash_commands import SlashCommandSystem
from sparkai.agent.agent_validation_hooks import ValidationHooksSystem
from sparkai.agent.agent_task_executor import TaskExecutionEngine, ExecutionStrategy, TaskContext
from sparkai.agent.agent_integration import SubsystemIntegration, IntegrationChannel, IntegrationEvent
from sparkai.agent.agent_session_compaction import SessionCompactionEngine, get_compaction_engine
from sparkai.agent.agent_recovery import RecoveryEngine, get_recovery_engine
from sparkai.agent.agent_tool_permission import ToolPermissionSystem, get_tool_permission_system
from sparkai.agent.agent_context_compression import ContextCompressionEngine, get_compression_engine
from sparkai.agent.agent_debug_protocol import DebugProtocolEngine, get_debug_protocol
from sparkai.agent.agent_autowork import AutoworkEngine, get_autowork_engine
from sparkai.agent.agent_policy import PolicyEngine, get_policy_engine
from sparkai.agent.agent_moa import MixtureOfAgentsEngine, get_moa_engine
from sparkai.agent.agent_structured_protocol import StructuredProtocol, get_structured_protocol
from sparkai.agent.agent_credential import CredentialManager, get_credential_manager
from sparkai.agent.agent_sandbox import SandboxEngine, get_sandbox_engine
from sparkai.agent.asset_consistency import AssetConsistencyEngine, get_consistency_engine
from sparkai.agent.agent_persistence import MemoryPersistenceEngine, get_persistence_engine
from sparkai.agent.agent_error_classifier import ErrorClassifier, get_error_classifier
from sparkai.agent.agent_file_state import FileStateEngine, get_file_state_engine
from sparkai.agent.agent_subagent_spawner import SubagentSpawner, get_subagent_spawner
from sparkai.agent.agent_tool_pruner import ToolOutputPruner, get_tool_output_pruner
from sparkai.agent.agent_trajectory_learner import TrajectoryLearner, get_trajectory_learner
from sparkai.agent.agent_skill_curator import SkillCurator, get_skill_curator
from sparkai.agent.agent_prompt_builder import PromptBuilder, get_prompt_builder
from sparkai.agent.agent_intent_classifier import IntentClassifier, get_intent_classifier
from sparkai.agent.agent_execution_budget import ExecutionBudget, get_execution_budget
from sparkai.agent.agent_approval_engine import ApprovalEngine, get_approval_engine
from sparkai.agent.agent_checkpoint_manager import CheckpointManager, get_checkpoint_manager
from sparkai.agent.agent_code_execution import CodeExecutionSandbox, get_code_sandbox, ExecutionMode
from sparkai.agent.agent_file_safety import FileSafetyController, get_file_safety
from sparkai.agent.agent_guard_system import GuardSystem, get_guard_system
from sparkai.agent.agent_interrupt_system import InterruptSystem, get_interrupt_system
from sparkai.agent.agent_result_storage import ResultStorage, get_result_storage
from sparkai.agent.agent_self_evaluator import SelfEvaluator, get_self_evaluator
from sparkai.agent.agent_strategic_planner import StrategicPlanner, get_strategic_planner
from sparkai.agent.agent_circuit_breaker import CircuitBreaker, get_circuit_breaker
from sparkai.agent.agent_persona import PersonaSystem, get_persona_system
from sparkai.agent.agent_streaming import StreamingManager, StreamState, get_streaming_manager
from sparkai.agent.agent_delegation import DelegationSystem, DelegationPolicy, get_delegation_system
from sparkai.agent.agent_mcp_bridge import MCPBridge, TransportType, ServerState, get_mcp_bridge
from sparkai.agent.agent_parallel_executor import ParallelExecutor, TaskType as ParallelTaskType, ProviderTier, get_parallel_executor
from sparkai.agent.agent_content_safety import ContentSafety, SensitivityLevel, get_content_safety
from sparkai.agent.agent_title_generator import TitleGenerator, TitleStyle, get_title_generator
from sparkai.agent.agent_shell_hooks import ShellHookManager, ShellPermission, get_shell_hooks
from sparkai.agent.agent_skill_preprocessor import SkillPreprocessor, ValidationResult, get_skill_preprocessor
from sparkai.agent.agent_rate_limiter import RateLimiter, LimitStrategy, get_rate_limiter
from sparkai.agent.agent_retry_system import RetrySystem, RetryStrategy, get_retry_system
from sparkai.agent.agent_web_browser import WebBrowser, FetchMethod, get_web_browser
from sparkai.agent.agent_session_search import SessionSearch, SearchScope, get_session_search
from sparkai.agent.agent_observability import ObservabilitySystem, SpanKind, get_observability
from sparkai.agent.agent_output_limiter import OutputLimiter, LimitPolicy, get_output_limiter
from sparkai.agent.agent_context_engine import ContextEngine, ContextStrategy, get_context_engine
from sparkai.agent.agent_skill_discovery import SkillDiscovery, CapabilityDomain, get_skill_discovery
from sparkai.agent.agent_prompt_cache import PromptCache, get_prompt_cache
from sparkai.agent.agent_trajectory_recorder import TrajectoryRecorder, get_trajectory_recorder
from sparkai.agent.agent_checkpoint_system import CheckpointSystem, get_checkpoint_system
from sparkai.agent.agent_budget_tracker import BudgetTracker, get_budget_tracker

from sparkai.engine.game_loop import GameLoop, get_game_loop, ExecutionPhase
from sparkai.engine.signal_system import SignalBus, get_signal_bus
from sparkai.engine.animation_system import AnimationPlayer, get_animation_player
from sparkai.engine.collision_system import CollisionSystem, get_collision_system
from sparkai.engine.input_manager import InputManager, get_input_manager
from sparkai.engine.physics_system import PhysicsSystem, get_physics_system
from sparkai.engine.particle_system import ParticleSystem, get_particle_system
from sparkai.engine.pathfinding_system import PathfindingSystem, get_pathfinding
from sparkai.engine.audio_system import AudioSystem, get_audio_system
from sparkai.engine.state_machine import StateMachine, get_state_machine
from sparkai.engine.resource_manager import ResourceManager, get_resource_manager
from sparkai.engine.behavior_system import BehaviorSystem, get_behavior_system
from sparkai.engine.tilemap_system import TilemapSystem, get_tilemap_system
from sparkai.engine.camera_system import CameraSystem, get_camera_system
from sparkai.engine.serialization import Serializer, get_serializer
from sparkai.engine.ui_system import UISystem, get_ui_system
from sparkai.engine.layer_system import LayerSystem, get_layer_system
from sparkai.engine.profiler import Profiler, get_profiler
from sparkai.engine.event_scripting import EventScriptingSystem, get_event_scripting_system
from sparkai.engine.scene_tree import SceneTree, get_scene_tree
from sparkai.engine.shader_system import ShaderSystem, get_shader_system
from sparkai.engine.variable_system import VariableSystem, get_variable_system
from sparkai.engine.resource_loader import ResourceLoader, get_resource_loader
from sparkai.engine.inventory_system import InventorySystem, Item, ItemCategory, get_inventory_system
from sparkai.engine.localization_system import LocalizationSystem, Language, get_localization_system
from sparkai.engine.achievement_system import AchievementSystem, Achievement, AchievementState, get_achievement_system
from sparkai.engine.cloud_sync import CloudSync, SyncState, SyncOperation, get_cloud_sync
from sparkai.engine.object_pool import ObjectPoolSystem, PoolConfig, get_object_pool_system
from sparkai.engine.lighting_system import LightingSystem, LightType, get_lighting_system
from sparkai.engine.font_system import FontSystem, TextStyle, get_font_system
from sparkai.engine.plugin_system import PluginSystem, PluginState, get_plugin_system
from sparkai.engine.effects_system import EffectsSystem, EffectType, get_effects_system
from sparkai.engine.input_mapping import InputMappingSystem, InputDevice, get_input_mapping
from sparkai.engine.undo_redo_system import UndoRedoSystem, CommandTarget, get_undo_redo_system
from sparkai.engine.sprite_sheet import SpriteSheetSystem, SheetLayout, get_sprite_sheet_system
from sparkai.engine.tween_system import TweenSystem, get_tween_system
from sparkai.engine.node_path_system import NodePathSystem, get_node_path_system
from sparkai.engine.project_template import ProjectTemplateSystem, get_project_template_system
from sparkai.engine.asset_pipeline import AssetPipeline, get_asset_pipeline


class RuntimeState(Enum):
    UNINITIALIZED = "uninitialized"
    INITIALIZING = "initializing"
    RUNNING = "running"
    PAUSED = "paused"
    STOPPING = "stopping"
    STOPPED = "stopped"
    ERROR = "error"


@dataclass
class RuntimeConfig:
    """Configuration for the SparkLabs Agent Runtime."""
    max_agents: int = 100
    max_sessions: int = 50
    max_concurrent_tasks: int = 10
    default_llm_provider: str = "openai"
    default_llm_model: str = "gpt-4"
    cache_ttl: float = 300.0
    session_ttl: float = 3600.0
    enable_hooks: bool = True
    enable_rules: bool = True
    enable_memory: bool = True
    enable_caching: bool = True
    enable_mesh: bool = True
    enable_protocol: bool = True
    enable_forge: bool = True
    enable_health: bool = True


class AgentRuntime:
    """
    Unified execution engine for the SparkLabs AI-Native Game Engine.

    The runtime is the central orchestrator that initializes and manages
    all 137 subsystems. It provides a single entry point for all engine
    operations and ensures proper lifecycle management.

    Usage:
        runtime = AgentRuntime()
        await runtime.initialize()
        result = await runtime.process_prompt("Create a platformer game")
        await runtime.shutdown()
    """

    def __init__(self, config: Optional[RuntimeConfig] = None):
        self.config = config or RuntimeConfig()
        self.state = RuntimeState.UNINITIALIZED
        self._start_time: Optional[float] = None
        self._initialized_at: Optional[float] = None

        self._event_bus: Optional[EventBus] = None
        self._game_context: Optional[GameContext] = None
        self._llm_router: Optional[LLMRouter] = None
        self._tool_executor: Optional[ToolExecutor] = None
        self._orchestrator: Optional[AgentOrchestrator] = None
        self._session_manager: Optional[SessionManager] = None
        self._memory_system: Optional[AgentMemorySystem] = None
        self._command_registry: Optional[CommandRegistry] = None
        self._hook_manager: Optional[HookManager] = None
        self._rule_engine: Optional[RuleEngine] = None
        self._team_orchestrator: Optional[TeamOrchestrator] = None
        self._game_bench: Optional[GameBench] = None
        self._pipeline: Optional[Pipeline] = None
        self._protocol: Optional[AgentProtocol] = None
        self._skill_forge: Optional[SkillForge] = None
        self._mesh: Optional[AgentMesh] = None
        self._health_checker: Optional[HealthChecker] = None
        self._game_coder: Optional[GameCoder] = None
        self._world_builder: Optional[WorldBuilder] = None
        self._game_skill_system: Optional[GameSkillSystem] = None
        self._quality_gate_system: Optional[QualityGateSystem] = None
        self._workflow_skill_system: Optional[WorkflowSkillSystem] = None
        self._agent_session_manager: Optional[AgentSessionManager] = None
        self._game_pipeline_system: Optional[GamePipelineSystem] = None
        self._studio_coordinator: Optional[StudioCoordinator] = None
        self._agent_swarm: Optional[AgentSwarm] = None
        self._studio_command_system: Optional[StudioCommandSystem] = None
        self._game_template_library: Optional[GameTemplateLibrary] = None
        self._blueprint_engine: Optional[BlueprintEngine] = None
        self._playtest_engine: Optional[PlaytestEngine] = None
        self._composer_engine: Optional[ComposerEngine] = None
        self._knowledge_graph: Optional[KnowledgeGraph] = None
        self._toolchain_engine: Optional[ToolChainEngine] = None
        self._reflex_engine: Optional[ReflexEngine] = None
        self._dialogue_engine: Optional[DialogueEngine] = None
        self._asset_engine: Optional[AssetPipelineEngine] = None
        self._validator_engine: Optional[ValidatorEngine] = None
        self._orchestrator_engine: Optional[OrchestratorEngine] = None
        self._skill_evolution_engine: Optional[SkillEvolutionEngine] = None
        self._evaluator_engine: Optional[GameEvaluatorEngine] = None
        self._lifecycle_manager: Optional[AgentLifecycleManager] = None
        self._slash_command_system: Optional[SlashCommandSystem] = None
        self._validation_hooks: Optional[ValidationHooksSystem] = None
        self._task_executor: Optional[TaskExecutionEngine] = None
        self._integration: Optional[SubsystemIntegration] = None
        self._compaction_engine: Optional[SessionCompactionEngine] = None
        self._recovery_engine: Optional[RecoveryEngine] = None
        self._permission_system: Optional[ToolPermissionSystem] = None
        self._compression_engine: Optional[ContextCompressionEngine] = None
        self._debug_protocol: Optional[DebugProtocolEngine] = None
        self._autowork_engine: Optional[AutoworkEngine] = None
        self._policy_engine: Optional[PolicyEngine] = None
        self._moa_engine: Optional[MixtureOfAgentsEngine] = None
        self._structured_protocol: Optional[StructuredProtocol] = None
        self._credential_manager: Optional[CredentialManager] = None
        self._sandbox_engine: Optional[SandboxEngine] = None
        self._consistency_engine: Optional[AssetConsistencyEngine] = None
        self._persistence_engine: Optional[MemoryPersistenceEngine] = None
        self._error_classifier: Optional[ErrorClassifier] = None
        self._file_state_engine: Optional[FileStateEngine] = None
        self._subagent_spawner: Optional[SubagentSpawner] = None
        self._tool_pruner: Optional[ToolOutputPruner] = None
        self._trajectory_learner: Optional[TrajectoryLearner] = None
        self._skill_curator: Optional[SkillCurator] = None
        self._prompt_builder: Optional[PromptBuilder] = None
        self._intent_classifier: Optional[IntentClassifier] = None
        self._execution_budget: Optional[ExecutionBudget] = None
        self._approval_engine: Optional[ApprovalEngine] = None
        self._checkpoint_manager: Optional[CheckpointManager] = None
        self._game_loop: Optional[GameLoop] = None
        self._signal_bus: Optional[SignalBus] = None
        self._animation_player: Optional[AnimationPlayer] = None
        self._collision_system: Optional[CollisionSystem] = None
        self._input_manager: Optional[InputManager] = None
        self._code_sandbox: Optional[CodeExecutionSandbox] = None
        self._file_safety: Optional[FileSafetyController] = None
        self._guard_system: Optional[GuardSystem] = None
        self._interrupt_system: Optional[InterruptSystem] = None
        self._result_storage: Optional[ResultStorage] = None
        self._physics_system: Optional[PhysicsSystem] = None
        self._particle_system: Optional[ParticleSystem] = None
        self._pathfinding: Optional[PathfindingSystem] = None
        self._audio_system: Optional[AudioSystem] = None
        self._state_machine: Optional[StateMachine] = None
        self._resource_manager: Optional[ResourceManager] = None
        self._behavior_system: Optional[BehaviorSystem] = None
        self._tilemap_system: Optional[TilemapSystem] = None
        self._self_evaluator: Optional[SelfEvaluator] = None
        self._strategic_planner: Optional[StrategicPlanner] = None
        self._circuit_breaker: Optional[CircuitBreaker] = None
        self._persona_system: Optional[PersonaSystem] = None
        self._camera_system: Optional[CameraSystem] = None
        self._serializer: Optional[Serializer] = None
        self._ui_system: Optional[UISystem] = None
        self._layer_system: Optional[LayerSystem] = None
        self._profiler: Optional[Profiler] = None
        self._streaming_manager: Optional[StreamingManager] = None
        self._delegation_system: Optional[DelegationSystem] = None
        self._mcp_bridge: Optional[MCPBridge] = None
        self._parallel_executor: Optional[ParallelExecutor] = None
        self._event_scripting: Optional[EventScriptingSystem] = None
        self._scene_tree: Optional[SceneTree] = None
        self._shader_system: Optional[ShaderSystem] = None
        self._variable_system: Optional[VariableSystem] = None
        self._resource_loader: Optional[ResourceLoader] = None
        self._content_safety: Optional[ContentSafety] = None
        self._title_generator: Optional[TitleGenerator] = None
        self._shell_hooks: Optional[ShellHookManager] = None
        self._skill_preprocessor: Optional[SkillPreprocessor] = None
        self._inventory_system: Optional[InventorySystem] = None
        self._localization_system: Optional[LocalizationSystem] = None
        self._achievement_system: Optional[AchievementSystem] = None
        self._cloud_sync: Optional[CloudSync] = None
        self._rate_limiter: Optional[RateLimiter] = None
        self._retry_system: Optional[RetrySystem] = None
        self._web_browser: Optional[WebBrowser] = None
        self._session_search: Optional[SessionSearch] = None
        self._object_pool_system: Optional[ObjectPoolSystem] = None
        self._lighting_system: Optional[LightingSystem] = None
        self._font_system: Optional[FontSystem] = None
        self._plugin_system: Optional[PluginSystem] = None
        self._observability: Optional[ObservabilitySystem] = None
        self._output_limiter: Optional[OutputLimiter] = None
        self._context_engine: Optional[ContextEngine] = None
        self._skill_discovery: Optional[SkillDiscovery] = None
        self._effects_system: Optional[EffectsSystem] = None
        self._input_mapping: Optional[InputMappingSystem] = None
        self._undo_redo_system: Optional[UndoRedoSystem] = None
        self._sprite_sheet: Optional[SpriteSheetSystem] = None
        self._prompt_cache: Optional[PromptCache] = None
        self._trajectory_recorder: Optional[TrajectoryRecorder] = None
        self._checkpoint_system: Optional[CheckpointSystem] = None
        self._budget_tracker: Optional[BudgetTracker] = None
        self._tween_system: Optional[TweenSystem] = None
        self._node_path_system: Optional[NodePathSystem] = None
        self._project_template_system: Optional[ProjectTemplateSystem] = None
        self._asset_pipeline: Optional[AssetPipeline] = None

        self._agents: Dict[str, SparkAgent] = {}
        self._operation_count: int = 0
        self._error_count: int = 0

    async def initialize(self) -> bool:
        """
        Initialize all runtime subsystems.
        Must be called before any other operations.
        """
        if self.state == RuntimeState.RUNNING:
            return True

        self.state = RuntimeState.INITIALIZING

        try:
            self._event_bus = get_event_bus()
            self._game_context = get_game_context()
            self._llm_router = LLMRouter()
            self._tool_executor = ToolExecutor(cache_ttl=self.config.cache_ttl)
            self._orchestrator = AgentOrchestrator()
            self._session_manager = SessionManager(session_ttl=self.config.session_ttl)
            self._memory_system = AgentMemorySystem()
            self._command_registry = CommandRegistry()
            self._hook_manager = HookManager() if self.config.enable_hooks else None
            self._rule_engine = RuleEngine() if self.config.enable_rules else None
            self._team_orchestrator = TeamOrchestrator(self._orchestrator)
            self._game_bench = GameBench()
            self._pipeline = Pipeline()
            self._protocol = get_protocol() if self.config.enable_protocol else None
            self._skill_forge = get_skill_forge() if self.config.enable_forge else None
            self._mesh = get_agent_mesh() if self.config.enable_mesh else None
            self._health_checker = get_health_checker() if self.config.enable_health else None
            self._game_coder = get_game_coder()
            self._world_builder = get_world_builder()
            self._game_skill_system = get_game_skill_system()
            self._quality_gate_system = get_quality_gate_system()
            self._workflow_skill_system = get_workflow_skill_system()
            self._agent_session_manager = get_agent_session_manager()
            self._game_pipeline_system = get_game_pipeline_system()
            self._studio_coordinator = get_studio_coordinator()
            self._agent_swarm = get_agent_swarm()
            self._studio_command_system = get_studio_command_system()
            self._game_template_library = get_game_template_library()
            self._blueprint_engine = get_blueprint_engine()
            self._playtest_engine = get_playtest_engine()
            self._composer_engine = get_composer_engine()
            self._knowledge_graph = get_knowledge_graph()
            self._toolchain_engine = get_toolchain_engine()
            self._reflex_engine = get_reflex_engine()
            self._dialogue_engine = get_dialogue_engine()
            self._asset_engine = get_asset_engine()
            self._validator_engine = get_validator_engine()
            self._orchestrator_engine = get_orchestrator_engine()
            self._skill_evolution_engine = get_skill_evolution_engine()
            self._evaluator_engine = get_game_evaluator()
            self._lifecycle_manager = AgentLifecycleManager()
            self._slash_command_system = SlashCommandSystem()
            self._validation_hooks = ValidationHooksSystem()
            self._task_executor = TaskExecutionEngine()
            self._integration = SubsystemIntegration()
            self._compaction_engine = get_compaction_engine()
            self._recovery_engine = get_recovery_engine()
            self._permission_system = get_tool_permission_system()
            self._compression_engine = get_compression_engine()
            self._debug_protocol = get_debug_protocol()
            self._autowork_engine = get_autowork_engine()
            self._policy_engine = get_policy_engine()
            self._moa_engine = get_moa_engine()
            self._structured_protocol = get_structured_protocol()
            self._credential_manager = get_credential_manager()
            self._sandbox_engine = get_sandbox_engine()
            self._consistency_engine = get_consistency_engine()
            self._persistence_engine = get_persistence_engine()
            self._error_classifier = get_error_classifier()
            self._file_state_engine = get_file_state_engine()
            self._subagent_spawner = get_subagent_spawner()
            self._tool_pruner = get_tool_output_pruner()
            self._trajectory_learner = get_trajectory_learner()
            self._skill_curator = get_skill_curator()
            self._prompt_builder = get_prompt_builder()
            self._intent_classifier = get_intent_classifier()
            self._execution_budget = get_execution_budget()
            self._approval_engine = get_approval_engine()
            self._checkpoint_manager = get_checkpoint_manager()
            self._game_loop = get_game_loop()
            self._signal_bus = get_signal_bus()
            self._animation_player = get_animation_player()
            self._collision_system = get_collision_system()
            self._input_manager = get_input_manager()
            self._code_sandbox = get_code_sandbox()
            self._file_safety = get_file_safety()
            self._guard_system = get_guard_system()
            self._interrupt_system = get_interrupt_system()
            self._result_storage = get_result_storage()
            self._physics_system = get_physics_system()
            self._particle_system = get_particle_system()
            self._pathfinding = get_pathfinding()
            self._audio_system = get_audio_system()
            self._state_machine = get_state_machine()
            self._resource_manager = get_resource_manager()
            self._behavior_system = get_behavior_system()
            self._tilemap_system = get_tilemap_system()
            self._self_evaluator = get_self_evaluator()
            self._strategic_planner = get_strategic_planner()
            self._circuit_breaker = get_circuit_breaker()
            self._persona_system = get_persona_system()
            self._camera_system = get_camera_system()
            self._serializer = get_serializer()
            self._ui_system = get_ui_system()
            self._layer_system = get_layer_system()
            self._profiler = get_profiler()
            self._streaming_manager = get_streaming_manager()
            self._delegation_system = get_delegation_system()
            self._mcp_bridge = get_mcp_bridge()
            self._parallel_executor = get_parallel_executor()
            self._event_scripting = get_event_scripting_system()
            self._scene_tree = get_scene_tree()
            self._shader_system = get_shader_system()
            self._variable_system = get_variable_system()
            self._resource_loader = get_resource_loader()
            self._content_safety = get_content_safety()
            self._title_generator = get_title_generator()
            self._shell_hooks = get_shell_hooks()
            self._skill_preprocessor = get_skill_preprocessor()
            self._inventory_system = get_inventory_system()
            self._localization_system = get_localization_system()
            self._achievement_system = get_achievement_system()
            self._cloud_sync = get_cloud_sync()
            self._rate_limiter = get_rate_limiter()
            self._retry_system = get_retry_system()
            self._web_browser = get_web_browser()
            self._session_search = get_session_search()
            self._object_pool_system = get_object_pool_system()
            self._lighting_system = get_lighting_system()
            self._font_system = get_font_system()
            self._plugin_system = get_plugin_system()
            self._observability = get_observability()
            self._output_limiter = get_output_limiter()
            self._context_engine = get_context_engine()
            self._skill_discovery = get_skill_discovery()
            self._effects_system = get_effects_system()
            self._input_mapping = get_input_mapping()
            self._undo_redo_system = get_undo_redo_system()
            self._sprite_sheet = get_sprite_sheet_system()
            self._prompt_cache = get_prompt_cache()
            self._trajectory_recorder = get_trajectory_recorder()
            self._checkpoint_system = get_checkpoint_system()
            self._budget_tracker = get_budget_tracker()
            self._tween_system = get_tween_system()
            self._node_path_system = get_node_path_system()
            self._project_template_system = get_project_template_system()
            self._asset_pipeline = get_asset_pipeline()

            # Wire credential manager into LLM router for key rotation on API failures
            if self._llm_router and self._credential_manager:
                self._llm_router.set_credential_manager(self._credential_manager)

            # Register remaining recovery action handlers
            if self._recovery_engine:
                def _rotate_credential(ctx):
                    if self._credential_manager:
                        provider = ctx.get("provider", "default")
                        self._credential_manager.rotate_key(provider)
                    return True

                def _escalate(ctx):
                    reason = ctx.get("reason", "recovery_limit_exceeded")
                    import logging
                    logging.getLogger(__name__).error("Recovery escalation triggered: %s", reason)
                    self.emit("agent.escalated", {"reason": reason, "context": ctx})
                    return False

                self._recovery_engine.register_action_handler("rotate_credential", _rotate_credential)
                self._recovery_engine.register_action_handler("escalate", _escalate)
            self._integration.register_subsystem("protocol", self._protocol)
            self._integration.register_subsystem("orchestrator", self._orchestrator)
            self._integration.register_subsystem("studio", self._studio_coordinator)
            self._integration.register_subsystem("swarm", self._agent_swarm)
            self._integration.register_subsystem("skills", self._skill_forge)
            self._integration.register_subsystem("executor", self._task_executor)
            self._integration.register_subsystem("evaluator", self._evaluator_engine)
            self._integration.register_subsystem("playtest", self._playtest_engine)
            self._integration.register_subsystem("sandbox", self._sandbox_engine)
            self._integration.register_subsystem("consistency", self._consistency_engine)
            self._integration.register_subsystem("persistence", self._persistence_engine)
            self._integration.register_subsystem("error_classifier", self._error_classifier)
            self._integration.register_subsystem("file_state", self._file_state_engine)
            self._integration.register_subsystem("subagent_spawner", self._subagent_spawner)
            self._integration.register_subsystem("tool_pruner", self._tool_pruner)
            self._integration.register_subsystem("trajectory_learner", self._trajectory_learner)
            self._integration.register_subsystem("skill_curator", self._skill_curator)
            self._integration.register_subsystem("prompt_builder", self._prompt_builder)
            self._integration.register_subsystem("intent_classifier", self._intent_classifier)
            self._integration.register_subsystem("execution_budget", self._execution_budget)
            self._integration.register_subsystem("approval_engine", self._approval_engine)
            self._integration.register_subsystem("checkpoint_manager", self._checkpoint_manager)
            self._integration.register_subsystem("game_loop", self._game_loop)
            self._integration.register_subsystem("signal_bus", self._signal_bus)
            self._integration.register_subsystem("animation_player", self._animation_player)
            self._integration.register_subsystem("collision_system", self._collision_system)
            self._integration.register_subsystem("input_manager", self._input_manager)
            self._integration.register_subsystem("code_sandbox", self._code_sandbox)
            self._integration.register_subsystem("file_safety", self._file_safety)
            self._integration.register_subsystem("guard_system", self._guard_system)
            self._integration.register_subsystem("interrupt_system", self._interrupt_system)
            self._integration.register_subsystem("result_storage", self._result_storage)
            self._integration.register_subsystem("physics_system", self._physics_system)
            self._integration.register_subsystem("particle_system", self._particle_system)
            self._integration.register_subsystem("pathfinding", self._pathfinding)
            self._integration.register_subsystem("audio_system", self._audio_system)
            self._integration.register_subsystem("state_machine", self._state_machine)
            self._integration.register_subsystem("resource_manager", self._resource_manager)
            self._integration.register_subsystem("behavior_system", self._behavior_system)
            self._integration.register_subsystem("tilemap_system", self._tilemap_system)
            self._integration.register_subsystem("self_evaluator", self._self_evaluator)
            self._integration.register_subsystem("strategic_planner", self._strategic_planner)
            self._integration.register_subsystem("circuit_breaker", self._circuit_breaker)
            self._integration.register_subsystem("persona_system", self._persona_system)
            self._integration.register_subsystem("camera_system", self._camera_system)
            self._integration.register_subsystem("serializer", self._serializer)
            self._integration.register_subsystem("ui_system", self._ui_system)
            self._integration.register_subsystem("layer_system", self._layer_system)
            self._integration.register_subsystem("profiler", self._profiler)
            self._integration.register_subsystem("streaming_manager", self._streaming_manager)
            self._integration.register_subsystem("delegation_system", self._delegation_system)
            self._integration.register_subsystem("mcp_bridge", self._mcp_bridge)
            self._integration.register_subsystem("parallel_executor", self._parallel_executor)
            self._integration.register_subsystem("event_scripting", self._event_scripting)
            self._integration.register_subsystem("scene_tree", self._scene_tree)
            self._integration.register_subsystem("shader_system", self._shader_system)
            self._integration.register_subsystem("variable_system", self._variable_system)
            self._integration.register_subsystem("resource_loader", self._resource_loader)
            self._integration.register_subsystem("content_safety", self._content_safety)
            self._integration.register_subsystem("title_generator", self._title_generator)
            self._integration.register_subsystem("shell_hooks", self._shell_hooks)
            self._integration.register_subsystem("skill_preprocessor", self._skill_preprocessor)
            self._integration.register_subsystem("inventory_system", self._inventory_system)
            self._integration.register_subsystem("localization_system", self._localization_system)
            self._integration.register_subsystem("achievement_system", self._achievement_system)
            self._integration.register_subsystem("cloud_sync", self._cloud_sync)
            self._integration.register_subsystem("rate_limiter", self._rate_limiter)
            self._integration.register_subsystem("retry_system", self._retry_system)
            self._integration.register_subsystem("web_browser", self._web_browser)
            self._integration.register_subsystem("session_search", self._session_search)
            self._integration.register_subsystem("object_pool_system", self._object_pool_system)
            self._integration.register_subsystem("lighting_system", self._lighting_system)
            self._integration.register_subsystem("font_system", self._font_system)
            self._integration.register_subsystem("plugin_system", self._plugin_system)
            self._integration.register_subsystem("observability", self._observability)
            self._integration.register_subsystem("output_limiter", self._output_limiter)
            self._integration.register_subsystem("context_engine", self._context_engine)
            self._integration.register_subsystem("skill_discovery", self._skill_discovery)
            self._integration.register_subsystem("effects_system", self._effects_system)
            self._integration.register_subsystem("input_mapping", self._input_mapping)
            self._integration.register_subsystem("undo_redo_system", self._undo_redo_system)
            self._integration.register_subsystem("sprite_sheet", self._sprite_sheet)
            self._integration.register_subsystem("prompt_cache", self._prompt_cache)
            self._integration.register_subsystem("trajectory_recorder", self._trajectory_recorder)
            self._integration.register_subsystem("checkpoint_system", self._checkpoint_system)
            self._integration.register_subsystem("budget_tracker", self._budget_tracker)
            self._integration.register_subsystem("tween_system", self._tween_system)
            self._integration.register_subsystem("node_path_system", self._node_path_system)
            self._integration.register_subsystem("project_template_system", self._project_template_system)
            self._integration.register_subsystem("asset_pipeline", self._asset_pipeline)
            self._integration.connect_all()

            self._recovery_engine.register_action_handler("compact_session", lambda params: self._compression_engine and self._compression_engine.compress(params.get("session_id", "default"), params.get("max_tokens", 4000)) is not None)
            self._recovery_engine.register_action_handler("compress_context", lambda params: self._compression_engine and self._compression_engine.compress(params.get("session_id", "default"), params.get("max_tokens", 4000)) is not None)
            self._recovery_engine.register_action_handler("review_skills", lambda params: self._skill_curator and self._skill_curator.review() is not None)
            self._recovery_engine.register_action_handler("check_budget", lambda params: self._execution_budget and self._execution_budget.check_tier(params.get("session_id", "default")) is not None)
            self._recovery_engine.register_action_handler("classify_intent", lambda params: self._intent_classifier and self._intent_classifier.classify(params.get("prompt", "")) is not None)
            self._recovery_engine.register_action_handler("check_approval", lambda params: self._approval_engine and self._approval_engine.request_approval(params.get("action", ""), params.get("level", "low")) is not None)
            self._recovery_engine.register_action_handler("create_checkpoint", lambda params: self._checkpoint_manager and self._checkpoint_manager.create_checkpoint(params.get("session_id", "default"), params) is not None)
            self._recovery_engine.register_action_handler("flush_cache", lambda params: self._prompt_cache and self._prompt_cache.clear() is None)
            self._recovery_engine.register_action_handler("record_event", lambda params: self._trajectory_recorder and self._trajectory_recorder.record_event(params.get("event_type", "ERROR"), params.get("data", {}), params.get("session_id", "default")) is not None)
            self._recovery_engine.register_action_handler("create_snapshot", lambda params: self._checkpoint_system and self._checkpoint_system.create_checkpoint("recovery", params, CheckpointScope.FULL.value) is not None)
            self._recovery_engine.register_action_handler("check_budget_tracker", lambda params: self._budget_tracker and self._budget_tracker.can_proceed(params.get("session_id", "default"), params.get("tokens", 0)) is not None)

            if self._protocol and self._event_bus:
                self._event_bus.subscribe(
                    EventChannel.AGENT,
                    topic="*",
                    handler=self._on_agent_event,
                )

            self._event_bus.emit(Event(
                channel=EventChannel.RUNTIME,
                topic="initialized",
                source="AgentRuntime",
                data={"config": {
                    "max_agents": self.config.max_agents,
                    "max_sessions": self.config.max_sessions,
                    "subsystems": 137,
                }},
            ))

            self.state = RuntimeState.RUNNING
            self._initialized_at = time.time()
            return True

        except Exception as e:
            self.state = RuntimeState.ERROR
            return False

    def _on_agent_event(self, event: Event) -> None:
        """Handle agent events from the event bus and relay to protocol."""
        if self._protocol and event.channel == EventChannel.AGENT:
            if event.topic in ("created", "removed", "prompt_processed"):
                self._protocol.create_notification(
                    topic=f"agent.{event.topic}",
                    payload=event.data,
                    sender="AgentRuntime",
                )

    async def shutdown(self) -> None:
        """Gracefully shut down all runtime subsystems."""
        if self.state != RuntimeState.RUNNING:
            return

        self.state = RuntimeState.STOPPING

        if self._event_bus:
            self._event_bus.emit(Event(
                channel=EventChannel.RUNTIME,
                topic="shutdown",
                source="AgentRuntime",
            ))

        if self._mesh:
            for agent_id in list(self._agents.keys()):
                self._mesh.unregister_node(agent_id)

        self._agents.clear()
        self.state = RuntimeState.STOPPED

    # === Agent Management ===

    async def create_agent(
        self,
        name: str,
        role: AgentRole = AgentRole.SPECIALIST,
        capabilities: Optional[List[AgentCapability]] = None,
        llm_config: Optional[LLMConfig] = None,
    ) -> SparkAgent:
        """Create and register a new agent in the runtime."""
        if len(self._agents) >= self.config.max_agents:
            raise ValueError(f"Maximum agent count reached ({self.config.max_agents})")

        agent = SparkAgent(
            name=name,
            role=role,
            capabilities=capabilities,
        )

        if llm_config:
            provider = LLMProvider(llm_config)
            agent.set_llm_provider(provider)

        self._agents[agent.id] = agent
        self._orchestrator.register_agent(agent)

        if self._mesh:
            cap_names = [c.value for c in (capabilities or [])]
            self._mesh.register_node(
                agent_id=agent.id,
                name=name,
                role=role.value,
                capabilities=cap_names,
            )

        if self._protocol:
            self._protocol.register_agent(agent.id, self._make_agent_handler(agent))

        if self._event_bus:
            self._event_bus.emit(Event(
                channel=EventChannel.AGENT,
                topic="created",
                source="AgentRuntime",
                data={"agent_id": agent.id, "name": name, "role": role.value},
            ))

        return agent

    def _make_agent_handler(self, agent: SparkAgent) -> Callable:
        """Create a protocol message handler for an agent."""
        async def handler(message: ProtocolMessage) -> None:
            if message.type == MessageType.REQUEST:
                response = await agent.think(str(message.payload))
                reply = message.create_response({"response": response})
                self._protocol.receive_response(reply)
            elif message.type == MessageType.DELEGATION:
                task = message.payload.get("task", "")
                response = await agent.think(task)
                reply = message.create_response({"result": response})
                self._protocol.receive_response(reply)
        return handler

    def get_agent(self, agent_id: str) -> Optional[SparkAgent]:
        return self._agents.get(agent_id)

    def list_agents(self) -> List[Dict[str, Any]]:
        return [a.get_status() for a in self._agents.values()]

    def remove_agent(self, agent_id: str) -> bool:
        if agent_id in self._agents:
            agent = self._agents[agent_id]
            self._orchestrator.unregister_agent(agent_id)

            if self._mesh:
                self._mesh.unregister_node(agent_id)

            if self._protocol:
                self._protocol.unregister_agent(agent_id)

            del self._agents[agent_id]

            if self._event_bus:
                self._event_bus.emit(Event(
                    channel=EventChannel.AGENT,
                    topic="removed",
                    source="AgentRuntime",
                    data={"agent_id": agent_id},
                ))
            return True
        return False

    # === Prompt Processing ===

    async def process_prompt(
        self,
        prompt: str,
        agent_id: Optional[str] = None,
        session_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Process a user prompt through the full AI pipeline.

        1. Check if it's a slash command
        2. If agent specified, route to that agent
        3. Otherwise, find the best agent via mesh or create one
        4. Execute the agent loop
        5. Record in memory and skill forge
        6. Return the result
        """
        self._operation_count += 1
        start_time = time.time()

        if prompt.startswith("/"):
            return await self._process_command(prompt, session_id)

        agent = None
        if agent_id:
            agent = self._agents.get(agent_id)

        if not agent:
            if self._mesh:
                task_type = self._llm_router.classify_task(prompt) if self._llm_router else TaskType.CHAT
                capability_map = {
                    TaskType.CODE_GENERATION: "code_generation",
                    TaskType.GAME_DESIGN: "game_design",
                    TaskType.NARRATIVE: "narrative",
                    TaskType.DEBUGGING: "debugging",
                    TaskType.REVIEW: "review",
                }
                cap = capability_map.get(task_type)
                if cap:
                    best_node = self._mesh.find_best_agent(cap)
                    if best_node:
                        agent = self._agents.get(best_node.agent_id)

            if not agent:
                if not self._agents:
                    agent = await self.create_agent(
                        name="SparkAssistant",
                        role=AgentRole.LEAD,
                        capabilities=[
                            AgentCapability.REASONING,
                            AgentCapability.CODE_GENERATION,
                            AgentCapability.WORLD_BUILDING,
                        ],
                    )
                else:
                    idle_agents = [a for a in self._agents.values() if a.state.value == "idle"]
                    agent = idle_agents[0] if idle_agents else list(self._agents.values())[0]

        if self._mesh:
            self._mesh.assign_task(agent.id)

        try:
            response = await agent.think(prompt)

            if self._memory_system:
                self._memory_system.record_event(
                    event_type="prompt_processed",
                    content=prompt,
                    tags=["user_input", agent.role.value],
                    importance=0.6,
                )

            if self._skill_forge:
                self._skill_forge.record_execution(
                    skill_name="prompt_processing",
                    success=True,
                    duration_ms=(time.time() - start_time) * 1000,
                )

            if self._event_bus:
                self._event_bus.emit(Event(
                    channel=EventChannel.AGENT,
                    topic="prompt_processed",
                    source="AgentRuntime",
                    data={"agent_id": agent.id, "prompt_length": len(prompt)},
                ))

            return {
                "response": response,
                "agent_id": agent.id,
                "agent_name": agent.name,
                "duration_ms": (time.time() - start_time) * 1000,
            }

        except Exception as e:
            self._error_count += 1

            if self._skill_forge:
                self._skill_forge.record_execution(
                    skill_name="prompt_processing",
                    success=False,
                    duration_ms=(time.time() - start_time) * 1000,
                    error=str(e),
                )

            return {
                "error": str(e),
                "agent_id": agent.id if agent else None,
                "duration_ms": (time.time() - start_time) * 1000,
            }

        finally:
            if self._mesh and agent:
                self._mesh.release_task(agent.id)

    async def _process_command(
        self,
        command_input: str,
        session_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Process a slash command input."""
        if not self._command_registry:
            return {"error": "Command system not initialized"}

        result = await self._command_registry.parse_input(command_input)
        return {
            "type": "command",
            "input": command_input,
            "result": result,
        }

    # === Pipeline Execution ===

    async def run_pipeline(self, prompt: str) -> Dict[str, Any]:
        """Run the full game generation pipeline."""
        if not self._pipeline or not self._game_context:
            return {"error": "Pipeline or context not initialized"}

        self._game_context.update_pipeline(
            phase=PipelinePhase.ANALYZING,
            current_stage="starting",
        )

        if self._event_bus:
            self._event_bus.emit(Event(
                channel=EventChannel.PIPELINE,
                topic="started",
                source="AgentRuntime",
                data={"prompt": prompt[:200]},
            ))

        agent = None
        if self._agents:
            directors = [a for a in self._agents.values() if a.role == AgentRole.DIRECTOR]
            agent = directors[0] if directors else list(self._agents.values())[0]

        self._pipeline.agent = agent
        result = await self._pipeline.run(prompt)

        completed = result.get("completed_stages", 0) == result.get("total_stages", 0)
        self._game_context.update_pipeline(
            phase=PipelinePhase.COMPLETED if completed else PipelinePhase.FAILED,
            current_stage="completed" if completed else "failed",
            stage_result=result,
        )

        if self._skill_forge:
            self._skill_forge.record_execution(
                skill_name="pipeline",
                success=completed,
                duration_ms=result.get("duration_ms", 0),
            )

        if self._event_bus:
            self._event_bus.emit(Event(
                channel=EventChannel.PIPELINE,
                topic="completed" if completed else "failed",
                source="AgentRuntime",
                data={"stages_completed": result.get("completed_stages", 0)},
            ))

        return result

    # === Tool Execution ===

    async def execute_tool(
        self,
        tool_name: str,
        params: Dict[str, Any],
    ) -> ExecutionResult:
        """Execute a tool through the runtime's tool executor."""
        if not self._tool_executor:
            return ExecutionResult(
                tool_name=tool_name,
                error="Tool executor not initialized",
            )

        result = await self._tool_executor.execute(tool_name, params)

        if self._event_bus:
            self._event_bus.emit(Event(
                channel=EventChannel.AGENT,
                topic="tool_executed",
                source="AgentRuntime",
                data={
                    "tool_name": tool_name,
                    "status": result.status.value if result.status else "unknown",
                },
            ))

        return result

    # === Session Management ===

    async def create_session(
        self,
        agent_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> AgentSession:
        """Create a new agent session."""
        if not self._session_manager:
            raise RuntimeError("Session manager not initialized")
        return self._session_manager.create_session(
            agent_id=agent_id or "",
            agent_name="",
            metadata=metadata,
        )

    async def send_session_message(
        self,
        session_id: str,
        message: str,
    ) -> Dict[str, Any]:
        """Send a message in a session and get the agent's response."""
        if not self._session_manager:
            return {"error": "Session manager not initialized"}

        session = self._session_manager.get(session_id)
        if not session:
            return {"error": f"Session '{session_id}' not found"}

        session.add_message("user", message)

        agent = None
        if session.agent_id:
            agent = self._agents.get(session.agent_id)

        if agent:
            response = await agent.think(message)
            session.add_message("agent", response)
            return {"response": response, "agent_id": agent.id}
        else:
            result = await self.process_prompt(message)
            session.add_message("agent", result.get("response", ""))
            return result

    # === Health Check ===

    def check_health(self) -> Dict[str, Any]:
        """Run a health check on all subsystems."""
        if not self._health_checker:
            return {"error": "Health checker not initialized"}
        report = self._health_checker.check_all(self)
        return report.to_dict()

    # === Subsystem Accessors ===

    @property
    def event_bus(self) -> Optional[EventBus]:
        return self._event_bus

    @property
    def game_context(self) -> Optional[GameContext]:
        return self._game_context

    @property
    def llm_router(self) -> Optional[LLMRouter]:
        return self._llm_router

    @property
    def tool_executor(self) -> Optional[ToolExecutor]:
        return self._tool_executor

    @property
    def orchestrator(self) -> Optional[AgentOrchestrator]:
        return self._orchestrator

    @property
    def session_manager(self) -> Optional[SessionManager]:
        return self._session_manager

    @property
    def memory_system(self) -> Optional[AgentMemorySystem]:
        return self._memory_system

    @property
    def command_registry(self) -> Optional[CommandRegistry]:
        return self._command_registry

    @property
    def hook_manager(self) -> Optional[HookManager]:
        return self._hook_manager

    @property
    def rule_engine(self) -> Optional[RuleEngine]:
        return self._rule_engine

    @property
    def team_orchestrator(self) -> Optional[TeamOrchestrator]:
        return self._team_orchestrator

    @property
    def game_bench(self) -> Optional[GameBench]:
        return self._game_bench

    @property
    def pipeline(self) -> Optional[Pipeline]:
        return self._pipeline

    @property
    def protocol(self) -> Optional[AgentProtocol]:
        return self._protocol

    @property
    def skill_forge(self) -> Optional[SkillForge]:
        return self._skill_forge

    @property
    def mesh(self) -> Optional[AgentMesh]:
        return self._mesh

    @property
    def health_checker(self) -> Optional[HealthChecker]:
        return self._health_checker

    @property
    def skill_curator(self) -> Optional[SkillCurator]:
        return self._skill_curator

    @property
    def prompt_builder(self) -> Optional[PromptBuilder]:
        return self._prompt_builder

    @property
    def intent_classifier(self) -> Optional[IntentClassifier]:
        return self._intent_classifier

    @property
    def execution_budget(self) -> Optional[ExecutionBudget]:
        return self._execution_budget

    @property
    def approval_engine(self) -> Optional[ApprovalEngine]:
        return self._approval_engine

    @property
    def checkpoint_manager(self) -> Optional[CheckpointManager]:
        return self._checkpoint_manager

    @property
    def game_loop(self) -> Optional[GameLoop]:
        return self._game_loop

    @property
    def signal_bus(self) -> Optional[SignalBus]:
        return self._signal_bus

    @property
    def animation_player(self) -> Optional[AnimationPlayer]:
        return self._animation_player

    @property
    def collision_system(self) -> Optional[CollisionSystem]:
        return self._collision_system

    @property
    def input_manager(self) -> Optional[InputManager]:
        return self._input_manager

    @property
    def code_sandbox(self) -> Optional[CodeExecutionSandbox]:
        return self._code_sandbox

    @property
    def file_safety(self) -> Optional[FileSafetyController]:
        return self._file_safety

    @property
    def guard_system(self) -> Optional[GuardSystem]:
        return self._guard_system

    @property
    def interrupt_system(self) -> Optional[InterruptSystem]:
        return self._interrupt_system

    @property
    def result_storage(self) -> Optional[ResultStorage]:
        return self._result_storage

    @property
    def physics_system(self) -> Optional[PhysicsSystem]:
        return self._physics_system

    @property
    def particle_system(self) -> Optional[ParticleSystem]:
        return self._particle_system

    @property
    def pathfinding(self) -> Optional[PathfindingSystem]:
        return self._pathfinding

    @property
    def audio_system(self) -> Optional[AudioSystem]:
        return self._audio_system

    @property
    def state_machine(self) -> Optional[StateMachine]:
        return self._state_machine

    @property
    def resource_manager(self) -> Optional[ResourceManager]:
        return self._resource_manager

    @property
    def behavior_system(self) -> Optional[BehaviorSystem]:
        return self._behavior_system

    @property
    def tilemap_system(self) -> Optional[TilemapSystem]:
        return self._tilemap_system

    @property
    def self_evaluator(self) -> Optional[SelfEvaluator]:
        return self._self_evaluator

    @property
    def strategic_planner(self) -> Optional[StrategicPlanner]:
        return self._strategic_planner

    @property
    def circuit_breaker(self) -> Optional[CircuitBreaker]:
        return self._circuit_breaker

    @property
    def persona_system(self) -> Optional[PersonaSystem]:
        return self._persona_system

    @property
    def camera_system(self) -> Optional[CameraSystem]:
        return self._camera_system

    @property
    def serializer(self) -> Optional[Serializer]:
        return self._serializer

    @property
    def ui_system(self) -> Optional[UISystem]:
        return self._ui_system

    @property
    def layer_system(self) -> Optional[LayerSystem]:
        return self._layer_system

    @property
    def profiler(self) -> Optional[Profiler]:
        return self._profiler

    @property
    def streaming_manager(self) -> Optional[StreamingManager]:
        return self._streaming_manager

    @property
    def delegation_system(self) -> Optional[DelegationSystem]:
        return self._delegation_system

    @property
    def mcp_bridge(self) -> Optional[MCPBridge]:
        return self._mcp_bridge

    @property
    def parallel_executor(self) -> Optional[ParallelExecutor]:
        return self._parallel_executor

    @property
    def event_scripting(self) -> Optional[EventScriptingSystem]:
        return self._event_scripting

    @property
    def scene_tree(self) -> Optional[SceneTree]:
        return self._scene_tree

    @property
    def shader_system(self) -> Optional[ShaderSystem]:
        return self._shader_system

    @property
    def variable_system(self) -> Optional[VariableSystem]:
        return self._variable_system

    @property
    def resource_loader(self) -> Optional[ResourceLoader]:
        return self._resource_loader

    @property
    def content_safety(self) -> Optional[ContentSafety]:
        return self._content_safety

    @property
    def title_generator(self) -> Optional[TitleGenerator]:
        return self._title_generator

    @property
    def shell_hooks(self) -> Optional[ShellHookManager]:
        return self._shell_hooks

    @property
    def skill_preprocessor(self) -> Optional[SkillPreprocessor]:
        return self._skill_preprocessor

    @property
    def inventory_system(self) -> Optional[InventorySystem]:
        return self._inventory_system

    @property
    def localization_system(self) -> Optional[LocalizationSystem]:
        return self._localization_system

    @property
    def achievement_system(self) -> Optional[AchievementSystem]:
        return self._achievement_system

    @property
    def cloud_sync(self) -> Optional[CloudSync]:
        return self._cloud_sync

    @property
    def rate_limiter(self) -> Optional[RateLimiter]:
        return self._rate_limiter

    @property
    def retry_system(self) -> Optional[RetrySystem]:
        return self._retry_system

    @property
    def web_browser(self) -> Optional[WebBrowser]:
        return self._web_browser

    @property
    def session_search(self) -> Optional[SessionSearch]:
        return self._session_search

    @property
    def object_pool_system(self) -> Optional[ObjectPoolSystem]:
        return self._object_pool_system

    @property
    def lighting_system(self) -> Optional[LightingSystem]:
        return self._lighting_system

    @property
    def font_system(self) -> Optional[FontSystem]:
        return self._font_system

    @property
    def plugin_system(self) -> Optional[PluginSystem]:
        return self._plugin_system

    @property
    def observability(self) -> Optional[ObservabilitySystem]:
        return self._observability

    @property
    def output_limiter(self) -> Optional[OutputLimiter]:
        return self._output_limiter

    @property
    def context_engine(self) -> Optional[ContextEngine]:
        return self._context_engine

    @property
    def skill_discovery(self) -> Optional[SkillDiscovery]:
        return self._skill_discovery

    @property
    def effects_system(self) -> Optional[EffectsSystem]:
        return self._effects_system

    @property
    def input_mapping(self) -> Optional[InputMappingSystem]:
        return self._input_mapping

    @property
    def undo_redo_system(self) -> Optional[UndoRedoSystem]:
        return self._undo_redo_system

    @property
    def sprite_sheet(self) -> Optional[SpriteSheetSystem]:
        return self._sprite_sheet

    @property
    def prompt_cache(self) -> Optional[PromptCache]:
        return self._prompt_cache

    @property
    def trajectory_recorder(self) -> Optional[TrajectoryRecorder]:
        return self._trajectory_recorder

    @property
    def checkpoint_system(self) -> Optional[CheckpointSystem]:
        return self._checkpoint_system

    @property
    def budget_tracker(self) -> Optional[BudgetTracker]:
        return self._budget_tracker

    @property
    def tween_system(self) -> Optional[TweenSystem]:
        return self._tween_system

    @property
    def node_path_system(self) -> Optional[NodePathSystem]:
        return self._node_path_system

    @property
    def project_template_system(self) -> Optional[ProjectTemplateSystem]:
        return self._project_template_system

    @property
    def asset_pipeline(self) -> Optional[AssetPipeline]:
        return self._asset_pipeline

    # === Runtime Status ===

    def get_status(self) -> Dict[str, Any]:
        return {
            "state": self.state.value,
            "uptime_seconds": (
                time.time() - self._initialized_at
                if self._initialized_at
                else 0
            ),
            "agent_count": len(self._agents),
            "operation_count": self._operation_count,
            "error_count": self._error_count,
            "subsystems": {
                "event_bus": self._event_bus is not None,
                "game_context": self._game_context is not None,
                "llm_router": self._llm_router is not None,
                "tool_executor": self._tool_executor is not None,
                "orchestrator": self._orchestrator is not None,
                "session_manager": self._session_manager is not None,
                "memory_system": self._memory_system is not None,
                "command_registry": self._command_registry is not None,
                "hook_manager": self._hook_manager is not None,
                "rule_engine": self._rule_engine is not None,
                "team_orchestrator": self._team_orchestrator is not None,
                "game_bench": self._game_bench is not None,
                "pipeline": self._pipeline is not None,
                "protocol": self._protocol is not None,
                "skill_forge": self._skill_forge is not None,
                "mesh": self._mesh is not None,
                "health_checker": self._health_checker is not None,
                "game_coder": self._game_coder is not None,
                "world_builder": self._world_builder is not None,
                "game_skill_system": self._game_skill_system is not None,
                "quality_gate_system": self._quality_gate_system is not None,
                "workflow_skill_system": self._workflow_skill_system is not None,
                "agent_session_manager": self._agent_session_manager is not None,
                "game_pipeline_system": self._game_pipeline_system is not None,
                "studio_coordinator": self._studio_coordinator is not None,
                "agent_swarm": self._agent_swarm is not None,
                "studio_command_system": self._studio_command_system is not None,
                "game_template_library": self._game_template_library is not None,
                "blueprint_engine": self._blueprint_engine is not None,
                "playtest_engine": self._playtest_engine is not None,
                "composer_engine": self._composer_engine is not None,
                "knowledge_graph": self._knowledge_graph is not None,
                "toolchain_engine": self._toolchain_engine is not None,
                "reflex_engine": self._reflex_engine is not None,
                "dialogue_engine": self._dialogue_engine is not None,
                "asset_engine": self._asset_engine is not None,
                "validator_engine": self._validator_engine is not None,
                "orchestrator_engine": self._orchestrator_engine is not None,
                "skill_evolution_engine": self._skill_evolution_engine is not None,
                "evaluator_engine": self._evaluator_engine is not None,
                "lifecycle_manager": self._lifecycle_manager is not None,
                "slash_command_system": self._slash_command_system is not None,
                "validation_hooks": self._validation_hooks is not None,
                "task_executor": self._task_executor is not None,
                "integration": self._integration is not None,
                "compaction_engine": self._compaction_engine is not None,
                "recovery_engine": self._recovery_engine is not None,
                "permission_system": self._permission_system is not None,
                "compression_engine": self._compression_engine is not None,
                "debug_protocol": self._debug_protocol is not None,
                "autowork_engine": self._autowork_engine is not None,
                "policy_engine": self._policy_engine is not None,
                "moa_engine": self._moa_engine is not None,
                "structured_protocol": self._structured_protocol is not None,
                "credential_manager": self._credential_manager is not None,
                "sandbox_engine": self._sandbox_engine is not None,
                "consistency_engine": self._consistency_engine is not None,
                "persistence_engine": self._persistence_engine is not None,
                "error_classifier": self._error_classifier is not None,
                "file_state_engine": self._file_state_engine is not None,
                "subagent_spawner": self._subagent_spawner is not None,
                "tool_pruner": self._tool_pruner is not None,
                "trajectory_learner": self._trajectory_learner is not None,
                "skill_curator": self._skill_curator is not None,
                "prompt_builder": self._prompt_builder is not None,
                "intent_classifier": self._intent_classifier is not None,
                "execution_budget": self._execution_budget is not None,
                "approval_engine": self._approval_engine is not None,
                "checkpoint_manager": self._checkpoint_manager is not None,
                "game_loop": self._game_loop is not None,
                "signal_bus": self._signal_bus is not None,
                "animation_player": self._animation_player is not None,
                "collision_system": self._collision_system is not None,
                "input_manager": self._input_manager is not None,
                "code_sandbox": self._code_sandbox is not None,
                "file_safety": self._file_safety is not None,
                "guard_system": self._guard_system is not None,
                "interrupt_system": self._interrupt_system is not None,
                "result_storage": self._result_storage is not None,
                "physics_system": self._physics_system is not None,
                "particle_system": self._particle_system is not None,
                "pathfinding": self._pathfinding is not None,
                "audio_system": self._audio_system is not None,
                "state_machine": self._state_machine is not None,
                "resource_manager": self._resource_manager is not None,
                "behavior_system": self._behavior_system is not None,
                "tilemap_system": self._tilemap_system is not None,
                "self_evaluator": self._self_evaluator is not None,
                "strategic_planner": self._strategic_planner is not None,
                "circuit_breaker": self._circuit_breaker is not None,
                "persona_system": self._persona_system is not None,
                "camera_system": self._camera_system is not None,
                "serializer": self._serializer is not None,
                "ui_system": self._ui_system is not None,
                "layer_system": self._layer_system is not None,
                "profiler": self._profiler is not None,
                "streaming_manager": self._streaming_manager is not None,
                "delegation_system": self._delegation_system is not None,
                "mcp_bridge": self._mcp_bridge is not None,
                "parallel_executor": self._parallel_executor is not None,
                "event_scripting": self._event_scripting is not None,
                "scene_tree": self._scene_tree is not None,
                "shader_system": self._shader_system is not None,
                "variable_system": self._variable_system is not None,
                "resource_loader": self._resource_loader is not None,
                "content_safety": self._content_safety is not None,
                "title_generator": self._title_generator is not None,
                "shell_hooks": self._shell_hooks is not None,
                "skill_preprocessor": self._skill_preprocessor is not None,
                "inventory_system": self._inventory_system is not None,
                "localization_system": self._localization_system is not None,
                "achievement_system": self._achievement_system is not None,
                "cloud_sync": self._cloud_sync is not None,
                "rate_limiter": self._rate_limiter is not None,
                "retry_system": self._retry_system is not None,
                "web_browser": self._web_browser is not None,
                "session_search": self._session_search is not None,
                "object_pool_system": self._object_pool_system is not None,
                "lighting_system": self._lighting_system is not None,
                "font_system": self._font_system is not None,
                "plugin_system": self._plugin_system is not None,
                "observability": self._observability is not None,
                "output_limiter": self._output_limiter is not None,
                "context_engine": self._context_engine is not None,
                "skill_discovery": self._skill_discovery is not None,
                "effects_system": self._effects_system is not None,
                "input_mapping": self._input_mapping is not None,
                "undo_redo_system": self._undo_redo_system is not None,
                "sprite_sheet": self._sprite_sheet is not None,
                "prompt_cache": self._prompt_cache is not None,
                "trajectory_recorder": self._trajectory_recorder is not None,
                "checkpoint_system": self._checkpoint_system is not None,
                "budget_tracker": self._budget_tracker is not None,
                "tween_system": self._tween_system is not None,
                "node_path_system": self._node_path_system is not None,
                "project_template_system": self._project_template_system is not None,
                "asset_pipeline": self._asset_pipeline is not None,
            },
        }

    def get_full_status(self) -> Dict[str, Any]:
        status = self.get_status()
        if self._event_bus:
            status["event_stats"] = self._event_bus.get_stats()
        if self._game_context:
            status["game_context"] = self._game_context.get_summary()
        if self._llm_router:
            status["llm_routing_stats"] = self._llm_router.get_routing_stats()
        if self._tool_executor:
            status["tool_executor_stats"] = self._tool_executor.get_stats()
        if self._session_manager:
            status["session_stats"] = self._session_manager.get_stats()
        if self._memory_system:
            status["memory_stats"] = self._memory_system.get_stats()
        if self._protocol:
            status["protocol_stats"] = self._protocol.get_stats()
        if self._skill_forge:
            status["forge_stats"] = self._skill_forge.get_stats()
        if self._mesh:
            status["mesh_stats"] = self._mesh.get_stats()
        if self._health_checker:
            status["health_stats"] = self._health_checker.get_stats()
        if self._game_coder:
            status["game_coder_stats"] = self._game_coder.get_stats()
        if self._world_builder:
            status["world_builder_stats"] = self._world_builder.get_stats()
        if self._game_skill_system:
            status["game_skill_stats"] = self._game_skill_system.get_stats()
        if self._quality_gate_system:
            status["quality_gate_stats"] = self._quality_gate_system.get_stats()
        if self._workflow_skill_system:
            status["workflow_skill_stats"] = self._workflow_skill_system.get_stats()
        if self._agent_session_manager:
            status["agent_session_stats"] = self._agent_session_manager.get_stats()
        if self._game_pipeline_system:
            status["game_pipeline_stats"] = self._game_pipeline_system.get_stats()
        if self._studio_coordinator:
            status["studio_coordinator_stats"] = self._studio_coordinator.get_stats()
        if self._agent_swarm:
            status["agent_swarm_stats"] = self._agent_swarm.get_stats()
        if self._studio_command_system:
            status["studio_command_stats"] = self._studio_command_system.get_stats()
        if self._game_template_library:
            status["game_template_stats"] = self._game_template_library.get_stats()
        if self._blueprint_engine:
            status["blueprint_stats"] = self._blueprint_engine.get_stats()
        if self._playtest_engine:
            status["playtest_stats"] = self._playtest_engine.get_stats()
        if self._composer_engine:
            status["composer_stats"] = self._composer_engine.get_stats()
        if self._knowledge_graph:
            status["knowledge_stats"] = self._knowledge_graph.get_graph_stats()
        if self._toolchain_engine:
            status["toolchain_stats"] = self._toolchain_engine.get_stats()
        if self._reflex_engine:
            status["reflex_stats"] = self._reflex_engine.get_stats()
        if self._dialogue_engine:
            status["dialogue_stats"] = self._dialogue_engine.get_stats()
        if self._asset_engine:
            status["asset_stats"] = self._asset_engine.get_stats()
        if self._validator_engine:
            status["validator_stats"] = self._validator_engine.get_stats()
        if self._orchestrator_engine:
            status["orchestrator_engine_stats"] = self._orchestrator_engine.get_stats()
        if self._skill_evolution_engine:
            status["skill_evolution_stats"] = self._skill_evolution_engine.get_stats()
        if self._evaluator_engine:
            status["evaluator_stats"] = self._evaluator_engine.get_stats()
        if self._lifecycle_manager:
            status["lifecycle_stats"] = self._lifecycle_manager.get_stats()
        if self._slash_command_system:
            status["slash_command_stats"] = self._slash_command_system.get_stats()
        if self._validation_hooks:
            status["validation_hooks_stats"] = self._validation_hooks.get_stats()
        if self._task_executor:
            status["task_executor_stats"] = self._task_executor.get_stats()
        if self._integration:
            status["integration_stats"] = self._integration.get_stats()
        if self._compaction_engine:
            status["compaction_stats"] = self._compaction_engine.get_stats()
        if self._recovery_engine:
            status["recovery_stats"] = self._recovery_engine.get_stats()
        if self._permission_system:
            status["permission_stats"] = self._permission_system.get_stats()
        if self._compression_engine:
            status["compression_stats"] = self._compression_engine.get_stats()
        if self._debug_protocol:
            status["debug_protocol_stats"] = self._debug_protocol.get_stats()
        if self._autowork_engine:
            status["autowork_stats"] = self._autowork_engine.get_stats()
        if self._policy_engine:
            status["policy_stats"] = self._policy_engine.get_stats()
        if self._moa_engine:
            status["moa_stats"] = self._moa_engine.get_stats()
        if self._structured_protocol:
            status["structured_protocol_stats"] = self._structured_protocol.get_stats()
        if self._credential_manager:
            status["credential_stats"] = self._credential_manager.get_stats()
        if self._sandbox_engine:
            status["sandbox_stats"] = self._sandbox_engine.get_stats()
        if self._consistency_engine:
            status["consistency_stats"] = self._consistency_engine.get_stats()
        if self._persistence_engine:
            status["persistence_stats"] = self._persistence_engine.get_stats()
        if self._error_classifier:
            status["error_classifier_stats"] = self._error_classifier.get_stats()
        if self._file_state_engine:
            status["file_state_stats"] = self._file_state_engine.get_stats()
        if self._subagent_spawner:
            status["subagent_spawner_stats"] = self._subagent_spawner.get_stats()
        if self._tool_pruner:
            status["tool_pruner_stats"] = self._tool_pruner.get_stats()
        if self._trajectory_learner:
            status["trajectory_learner_stats"] = self._trajectory_learner.get_stats()
        if self._skill_curator:
            status["skill_curator_stats"] = self._skill_curator.get_ecosystem_health()
        if self._prompt_builder:
            status["prompt_builder_stats"] = {"ready": True}
        if self._intent_classifier:
            status["intent_classifier_stats"] = {"ready": True}
        if self._execution_budget:
            status["execution_budget_stats"] = self._execution_budget.get_overall_stats()
        if self._approval_engine:
            status["approval_engine_stats"] = self._approval_engine.get_stats()
        if self._checkpoint_manager:
            status["checkpoint_manager_stats"] = self._checkpoint_manager.get_stats()
        if self._game_loop:
            status["game_loop_stats"] = self._game_loop.get_statistics()
        if self._signal_bus:
            status["signal_bus_stats"] = {"connections": self._signal_bus.get_connection_count()}
        if self._animation_player:
            status["animation_player_stats"] = self._animation_player.get_status()
        if self._collision_system:
            status["collision_system_stats"] = {"colliders": len(self._collision_system._colliders)}
        if self._input_manager:
            status["input_manager_stats"] = self._input_manager.get_snapshot()
        if self._code_sandbox:
            status["code_sandbox_stats"] = self._code_sandbox.get_stats()
        if self._file_safety:
            status["file_safety_stats"] = self._file_safety.get_stats()
        if self._guard_system:
            status["guard_system_stats"] = self._guard_system.get_stats()
        if self._interrupt_system:
            status["interrupt_system_stats"] = self._interrupt_system.get_stats()
        if self._result_storage:
            status["result_storage_stats"] = self._result_storage.get_stats()
        if self._physics_system:
            status["physics_system_stats"] = self._physics_system.get_stats()
        if self._particle_system:
            status["particle_system_stats"] = self._particle_system.get_stats()
        if self._pathfinding:
            status["pathfinding_stats"] = self._pathfinding.get_stats()
        if self._audio_system:
            status["audio_system_stats"] = self._audio_system.get_stats()
        if self._state_machine:
            status["state_machine_stats"] = self._state_machine.get_stats()
        if self._resource_manager:
            status["resource_manager_stats"] = self._resource_manager.get_stats()
        if self._behavior_system:
            status["behavior_system_stats"] = self._behavior_system.get_stats()
        if self._tilemap_system:
            status["tilemap_system_stats"] = self._tilemap_system.get_stats()
        if self._streaming_manager:
            status["streaming_manager_stats"] = {"ready": True}
        if self._delegation_system:
            status["delegation_system_stats"] = self._delegation_system.get_stats()
        if self._mcp_bridge:
            status["mcp_bridge_stats"] = self._mcp_bridge.get_stats()
        if self._parallel_executor:
            status["parallel_executor_stats"] = self._parallel_executor.get_stats()
        if self._event_scripting:
            status["event_scripting_stats"] = self._event_scripting.get_stats()
        if self._scene_tree:
            status["scene_tree_stats"] = self._scene_tree.get_stats()
        if self._shader_system:
            status["shader_system_stats"] = self._shader_system.get_stats()
        if self._variable_system:
            status["variable_system_stats"] = self._variable_system.get_stats()
        if self._resource_loader:
            status["resource_loader_stats"] = self._resource_loader.get_stats()
        if self._content_safety:
            status["content_safety_stats"] = self._content_safety.get_stats()
        if self._title_generator:
            status["title_generator_stats"] = self._title_generator.get_stats()
        if self._shell_hooks:
            status["shell_hooks_stats"] = self._shell_hooks.get_stats()
        if self._skill_preprocessor:
            status["skill_preprocessor_stats"] = self._skill_preprocessor.get_stats()
        if self._inventory_system:
            status["inventory_system_stats"] = self._inventory_system.get_stats()
        if self._localization_system:
            status["localization_system_stats"] = self._localization_system.get_stats()
        if self._achievement_system:
            status["achievement_system_stats"] = self._achievement_system.get_stats()
        if self._cloud_sync:
            status["cloud_sync_stats"] = self._cloud_sync.get_stats()
        if self._rate_limiter:
            status["rate_limiter_stats"] = self._rate_limiter.get_stats()
        if self._retry_system:
            status["retry_system_stats"] = self._retry_system.get_stats()
        if self._web_browser:
            status["web_browser_stats"] = self._web_browser.get_stats()
        if self._session_search:
            status["session_search_stats"] = self._session_search.get_stats()
        if self._object_pool_system:
            status["object_pool_stats"] = self._object_pool_system.get_stats()
        if self._lighting_system:
            status["lighting_stats"] = self._lighting_system.get_stats()
        if self._font_system:
            status["font_system_stats"] = self._font_system.get_stats()
        if self._plugin_system:
            status["plugin_system_stats"] = self._plugin_system.get_stats()
        if self._observability:
            status["observability_stats"] = self._observability.get_stats()
        if self._output_limiter:
            status["output_limiter_stats"] = self._output_limiter.get_stats()
        if self._context_engine:
            status["context_engine_stats"] = self._context_engine.get_stats()
        if self._skill_discovery:
            status["skill_discovery_stats"] = self._skill_discovery.get_stats()
        if self._effects_system:
            status["effects_system_stats"] = self._effects_system.get_stats()
        if self._input_mapping:
            status["input_mapping_stats"] = self._input_mapping.get_stats()
        if self._undo_redo_system:
            status["undo_redo_stats"] = self._undo_redo_system.get_stats()
        if self._sprite_sheet:
            status["sprite_sheet_stats"] = self._sprite_sheet.get_stats()
        if self._prompt_cache:
            status["prompt_cache_stats"] = self._prompt_cache.get_stats()
        if self._trajectory_recorder:
            status["trajectory_recorder_stats"] = self._trajectory_recorder.get_stats()
        if self._checkpoint_system:
            status["checkpoint_system_stats"] = self._checkpoint_system.get_stats()
        if self._budget_tracker:
            status["budget_tracker_stats"] = self._budget_tracker.get_all_usage()
        if self._tween_system:
            status["tween_system_stats"] = self._tween_system.get_stats()
        if self._node_path_system:
            status["node_path_system_stats"] = self._node_path_system.get_stats()
        if self._project_template_system:
            status["project_template_system_stats"] = self._project_template_system.get_stats()
        if self._asset_pipeline:
            status["asset_pipeline_stats"] = self._asset_pipeline.get_stats()
        return status


_global_runtime: Optional[AgentRuntime] = None


def get_runtime() -> AgentRuntime:
    """Get the global AgentRuntime singleton."""
    global _global_runtime
    if _global_runtime is None:
        _global_runtime = AgentRuntime()
    return _global_runtime


def reset_runtime() -> None:
    """Reset the global AgentRuntime singleton."""
    global _global_runtime
    _global_runtime = None
