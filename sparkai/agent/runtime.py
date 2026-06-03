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
    |-- Insights Engine (session analytics + token cost reporting)
    |-- State Sync Mesh (bidirectional agent↔engine coherence)
    |-- Development Loop (Plan→Code→Test→Iterate cycle)
    |-- Context References (@asset:@scene:@script: resolution)
    |-- Rendering Server (batched 2D draw pipeline with culling)
    |-- Input Event System (action-mapped event dispatch)
    |-- GameObject Model (full Awake/Start/Update/Destroy lifecycle)
    |-- Scene Manager (async transitions, pooling, overlay stack)
    |-- Process Registry (background process lifecycle management)
    |-- Cron Scheduler (scheduled automation for game dev workflows)
    |-- Expression Evaluator (safe math/logic/string expression engine)
    |-- Class Registry (meta-object reflection for game entity types)
    |-- Multi-Modal Agent (image/sprite/screenshot visual analysis)
    |-- Import Pipeline (format detection, conversion, asset registration)
    |-- Terrain System (procedural 2D heightmap/biome generation)
    |-- Save System (versioned save/load with integrity verification)
    |-- Network Sync (multiplayer state replication and sync)
    |-- Behavior Tree (composable NPC AI decision trees)

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
from sparkai.agent.agent_insights import InsightsEngine, get_insights_engine
from sparkai.agent.agent_state_sync import StateSyncMesh, SyncDomain, get_state_sync_mesh
from sparkai.agent.agent_dev_loop import DevelopmentLoop, CyclePhase, get_dev_loop
from sparkai.agent.agent_context_references import ContextReferenceResolver, RefDomain, get_context_reference_resolver
from sparkai.agent.agent_process_registry import ProcessRegistry, ProcessState as ProcState, ProcessType, get_process_registry
from sparkai.agent.agent_cron_scheduler import AgentCronScheduler, CronFrequency, get_cron_scheduler
from sparkai.agent.agent_expression_evaluator import ExpressionEvaluator, ExpressionError, get_expression_evaluator
from sparkai.agent.agent_class_registry import ClassRegistry, DataType, TypeDescriptor, get_class_registry
from sparkai.agent.agent_multi_modal import MultiModalAgent, AnalysisDomain, get_multi_modal_agent
from sparkai.agent.agent_import_pipeline import ImportPipelineEngine, AssetImportType, ImportTask, get_import_pipeline
from sparkai.agent.agent_prompt_optimizer import PromptOptimizer, PromptDomain, PromptTemplate, PromptSession, get_prompt_optimizer
from sparkai.agent.agent_skill_composer import SkillComposer, SkillDomain, SkillStep, SkillChain, get_skill_composer
from sparkai.agent.agent_developer_assistant import DeveloperAssistant, AssistantMode, DeveloperSession, Suggestion, get_developer_assistant
from sparkai.agent.agent_game_director import GameDirector, get_game_director
from sparkai.agent.agent_balance_analyzer import BalanceAnalyzer, get_balance_analyzer
from sparkai.agent.agent_narrative_composer import NarrativeComposer, get_narrative_composer
from sparkai.agent.agent_player_modeler import PlayerModeler, get_player_modeler
from sparkai.agent.agent_memory_graph import AgentMemoryGraph, get_memory_graph
from sparkai.agent.agent_context_compressor import AgentContextCompressor, get_context_compressor
from sparkai.agent.agent_tool_forge import AgentToolForge, get_tool_forge
from sparkai.agent.agent_gateway import AgentGateway, get_gateway
from sparkai.engine.engine_audio_system import GameAudioSystem, get_audio_system
from sparkai.engine.engine_network_layer import NetworkLayer, get_network_layer
from sparkai.engine.engine_behavior_runtime import BehaviorRuntime, get_behavior_runtime
from sparkai.engine.engine_save_system import SaveSystem, get_save_system
from sparkai.engine.engine_node_tree import NodeTreeSystem, get_node_tree
from sparkai.engine.engine_extension_registry import ExtensionRegistry, get_extension_registry
from sparkai.engine.engine_export_pipeline import MultiExportPipeline, get_export_pipeline
from sparkai.engine.engine_server_architecture import GameServerPool, get_server_pool
from sparkai.engine.engine_gizmo_system import GizmoSystem, get_gizmo_system
from sparkai.engine.engine_pivot_system import PivotSystem, get_pivot_system
from sparkai.agent.agent_session_snapshot import SessionSnapshotSystem, get_session_snapshot
from sparkai.agent.agent_trajectory_compressor import TrajectoryCompressor, get_trajectory_compressor
from sparkai.agent.agent_skills_hub import SkillsHub, get_skills_hub
from sparkai.agent.agent_personality_system import PersonalitySystem, get_personality_system
from sparkai.agent.agent_insights_generator import InsightsGenerator, get_insights_generator
from sparkai.agent.agent_provider_switch import ProviderSwitch, get_provider_switch
from sparkai.agent.agent_chain_of_thought import ChainOfThoughtEngine, get_chain_of_thought
from sparkai.agent.agent_conversation_memory import ConversationMemoryEngine, get_conversation_memory
from sparkai.agent.agent_self_optimization import SelfOptimizationEngine, get_self_optimization
from sparkai.agent.agent_collaboration_protocol import CollaborationProtocolEngine, get_collaboration_protocol
from sparkai.agent.agent_knowledge_synthesis import KnowledgeSynthesisEngine, get_knowledge_synthesis
from sparkai.agent.agent_capability_registry import CapabilityRegistryEngine, get_capability_registry
from sparkai.engine.engine_event_sheet import EventSheetRuntime, get_event_sheet
from sparkai.engine.engine_resource_serializer import ResourceSerializer, get_resource_serializer
from sparkai.engine.engine_input_map import InputMapSystem, get_input_map
from sparkai.engine.engine_animation_tree import AnimationTreeRuntime, get_animation_tree
from sparkai.engine.engine_custom_object_types import CustomObjectTypeSystem, get_custom_object_types
from sparkai.engine.engine_tile_map_optimizer import TileMapOptimizer, get_tile_map_optimizer

from sparkai.agent.agent_experiment_framework import AgentExperimentFramework, get_experiment_framework
from sparkai.agent.agent_telemetry_pipeline import AgentTelemetryPipeline, get_telemetry_pipeline
from sparkai.agent.agent_audit_trail import AgentAuditTrail, get_audit_trail
from sparkai.agent.agent_journal_system import AgentJournalSystem, get_journal_system
from sparkai.agent.agent_document_synthesizer import AgentDocumentSynthesizer, get_document_synthesizer
from sparkai.agent.agent_simulation_runner import AgentSimulationRunner, get_simulation_runner
from sparkai.agent.agent_agentic_coding import AgenticCodingFramework, get_agentic_coding
from sparkai.agent.agent_game_reasoner import GameDesignReasoner, get_game_reasoner
from sparkai.agent.agent_narrative_branch import NarrativeBranchSystem, get_narrative_branch
from sparkai.agent.agent_concurrency_manager import AgentConcurrencyManager, get_concurrency_manager
from sparkai.agent.agent_verification_pipeline import AgentVerificationPipeline, get_verification_pipeline
from sparkai.agent.agent_playtest_simulator import AgenticPlaytestSimulator, get_playtest_simulator
from sparkai.agent.agent_skill_synthesizer import SkillSynthesizer, get_skill_synthesizer
from sparkai.agent.agent_security_scanner import SecurityScanner, get_security_scanner
from sparkai.agent.agent_delegation_framework import DelegationFramework, get_delegation_framework
from sparkai.agent.agent_kanban_coordinator import KanbanCoordinator, get_kanban_coordinator
from sparkai.agent.agent_streaming_scrubber import StreamingScrubber, get_streaming_scrubber
from sparkai.agent.agent_trajectory_generator import TrajectoryGenerator, get_trajectory_generator
from sparkai.agent.agent_developer_oracle import DeveloperOracle, get_developer_oracle
from sparkai.agent.agent_context_weaver import ContextWeaver, get_context_weaver
from sparkai.agent.agent_session_nexus import SessionNexus, get_session_nexus
from sparkai.agent.agent_persona_vault import PersonaVault, get_persona_vault
from sparkai.agent.agent_voice_bridge import VoiceBridge, get_voice_bridge
from sparkai.agent.agent_ecosystem_hub import EcosystemHub, get_ecosystem_hub
from sparkai.agent.agent_intent_cascade import IntentCascade, get_intent_cascade
from sparkai.agent.agent_game_forecaster import GameForecaster, get_game_forecaster
from sparkai.agent.agent_asset_synthesizer import AssetSynthesizer, get_asset_synthesizer
from sparkai.agent.agent_tutorial_orchestrator import TutorialOrchestrator, get_tutorial_orchestrator
from sparkai.agent.agent_ab_test_runner import ABTestRunner, get_ab_test_runner
from sparkai.agent.agent_heatmap_analyzer import HeatmapAnalyzer, get_heatmap_analyzer
from sparkai.agent.agent_bug_forensics import BugForensics, get_bug_forensics
from sparkai.agent.agent_accessibility_auditor import AccessibilityAuditor, get_accessibility_auditor
from sparkai.agent.agent_federated_learner import FederatedLearner, get_federated_learner
from sparkai.agent.agent_swarm_planner import SwarmPlanner, get_swarm_planner
from sparkai.agent.agent_world_composer import WorldComposer, get_world_composer
from sparkai.agent.agent_playtest_orchestrator import PlaytestOrchestrator, get_playtest_orchestrator
from sparkai.agent.agent_reasoning_chain import ReasoningChain, get_reasoning_chain
from sparkai.agent.agent_memory_hierarchy import MemoryHierarchy, get_memory_hierarchy
from sparkai.agent.agent_tool_registry import ToolRegistry, get_tool_registry
from sparkai.agent.agent_prompt_templates import PromptLibrary, get_prompt_library
from sparkai.agent.agent_reflection_loop import ReflectionLoop, get_reflection_loop
from sparkai.agent.agent_skill_forge import SkillForge, get_skill_forge
from sparkai.agent.agent_memory_consolidator import MemoryConsolidator, get_memory_consolidator
from sparkai.agent.agent_delegation_broker import DelegationBroker, get_delegation_broker
from sparkai.agent.agent_game_design_intelligence import GameDesignIntelligence, get_game_design_intelligence
from sparkai.agent.agent_interaction_synthesis import InteractionSynthesisEngine, get_interaction_synthesis_engine
from sparkai.agent.agent_gameplay_ecosystem import GameplayEcosystemSimulator, get_gameplay_ecosystem_simulator
from sparkai.agent.agent_creative_director import AgentCreativeDirector, get_creative_director
from sparkai.agent.agent_social_simulation import AgentSocialSimulation, get_agent_social_simulation
from sparkai.agent.agent_monetization_designer import AgentMonetizationDesigner, get_monetization_designer
from sparkai.agent.agent_world_builder import AgentWorldBuilder, get_agent_world_builder
from sparkai.agent.agent_behavior_designer import AgentBehaviorDesigner, get_agent_behavior_designer
from sparkai.agent.agent_quest_composer import AgentQuestComposer, get_agent_quest_composer
from sparkai.agent.agent_multi_agent_coordinator import AgentMultiAgentCoordinator, get_multi_agent_coordinator
from sparkai.agent.agent_memory_orchestrator import AgentMemoryOrchestrator, get_memory_orchestrator
from sparkai.agent.agent_simulation_controller import AgentSimulationController, get_simulation_controller
from sparkai.agent.agent_timeline_manager import AgentTimelineManager, get_timeline_manager
from sparkai.agent.agent_skill_generator import AgentSkillGenerator, get_skill_generator
from sparkai.agent.agent_learning_loop import AgentLearningLoop, get_learning_loop
from sparkai.agent.agent_social_dynamics import AgentSocialDynamics, get_social_dynamics
from sparkai.agent.agent_emergent_narrative import AgentEmergentNarrative, get_emergent_narrative
from sparkai.engine.engine_procedural_world import EngineProceduralWorld, get_procedural_world
from sparkai.engine.engine_render_pipeline import EngineRenderPipeline, get_render_pipeline
from sparkai.engine.engine_physics_dynamics import EnginePhysicsDynamics, get_engine_physics_dynamics
from sparkai.engine.engine_audio_spatial import EngineAudioSpatial, get_audio_spatial
from sparkai.engine.engine_behavior_orchestrator import EngineBehaviorOrchestrator, get_engine_behavior_orchestrator
from sparkai.agent.agent_cross_module_orchestrator import AgentCrossModuleOrchestrator, get_cross_module_orchestrator

from sparkai.engine.game_loop import GameLoop, get_game_loop, ExecutionPhase
from sparkai.engine.signal_system import SignalBus, get_signal_bus
from sparkai.engine.animation_system import AnimationPlayer, get_animation_player
from sparkai.engine.collision_system import CollisionSystem, get_collision_system
from sparkai.engine.input_manager import InputManager, get_input_manager
from sparkai.engine.physics_system import PhysicsSystem, get_physics_system
from sparkai.engine.particle_system import ParticleSystem, get_particle_system
from sparkai.engine.pathfinding_system import PathfindingSystem, get_pathfinding
from sparkai.engine.audio_system import AudioSystem as LegacyAudioSystem
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
from sparkai.engine.rendering_server import RenderingServer, get_rendering_server
from sparkai.engine.input_event_system import InputEventSystem, get_input_event_system
from sparkai.engine.game_object import GameObject, GameObjectRegistry, get_game_object_registry
from sparkai.engine.scene_manager import SceneManager, SceneState, get_scene_manager
from sparkai.engine.terrain_system import TerrainSystem, TerrainType, NoiseAlgorithm, get_terrain_system
from sparkai.engine.ui_layout_system import UILayoutSystem, UILayout, UIContainer, UIAnchor, get_ui_layout_system
from sparkai.engine.performance_overlay import PerformanceOverlay, FrameSample, MetricThreshold, get_performance_overlay
from sparkai.engine.engine_scene_streamer import SceneStreamer, WorldChunk, StreamingConfig, get_scene_streamer
from sparkai.engine.engine_project_exporter import ProjectExporter, ExportConfig, ExportJob, get_project_exporter
from sparkai.engine.save_system import SaveSystem, SaveSlot, SaveStatus, get_save_system
from sparkai.engine.network_sync import NetworkSync, SyncAuthority as NetSyncAuthority, get_network_sync
from sparkai.engine.behavior_tree import BehaviorTree, NodeStatus, Blackboard, get_behavior_tree
from sparkai.engine.math_utils import MathUtils, Vector2, Vector3, Rect2, Transform2D, get_math_utils
from sparkai.engine.gui_system import GUISystem, Widget, Container, Button, Label, get_gui_system
from sparkai.engine.config_manager import ConfigManager, ConfigScope, ConfigEntry, get_config_manager
from sparkai.engine.animation_controller import AnimationController, AnimState, AnimClip, get_animation_controller
from sparkai.agent.agent_trajectory import TrajectoryRecorder, TrajectoryPhase, TrajectorySession, get_trajectory_recorder
from sparkai.agent.agent_skill_commands import SkillCommandRegistry, CommandCategory, CommandDef, get_skill_command_registry
from sparkai.agent.agent_session_persistence import SessionStore, SessionStatus, SessionRecord, get_session_store
from sparkai.agent.agent_platform_bridge import PlatformBridge, PlatformType, PlatformMessage, get_platform_bridge
from sparkai.agent.agent_tool_composer import ToolComposer, ToolChain, ChainTemplate, get_tool_composer
from sparkai.agent.agent_feedback_loop import FeedbackLoop, FeedbackEntry, FeedbackSource, get_feedback_loop
from sparkai.agent.agent_negotiation import AgentNegotiation, NegotiationSession, VoteStance, get_agent_negotiation
from sparkai.agent.agent_simulation_env import SimulationEnv, SimScenario, SimulationMode, get_simulation_env
from sparkai.agent.agent_goal_decomposer import GoalDecomposer, GoalTree, GoalNode, GoalLevel, ChecklistStatus, GoalDecomposition, get_goal_decomposer
from sparkai.agent.agent_prompt_template import PromptTemplateLib, TemplateEntry, TemplateDomain, get_prompt_template_lib
from sparkai.agent.agent_semantic_memory import SemanticMemory, MemoryVector, MemoryCategory, get_semantic_memory
from sparkai.agent.agent_intent_classifier import IntentClassifier, IntentDomain, ClassificationResult, get_intent_classifier
from sparkai.agent.agent_context_assembler import ContextAssembler, ContextSource, AssembledContext, get_context_assembler
from sparkai.agent.agent_action_sequencer import ActionSequencer, ExecutionPipeline, OpType, get_action_sequencer
from sparkai.agent.agent_event_bus import AgentEventBus, EventPriority, EventDomain, get_agent_event_bus
from sparkai.agent.agent_task_queue import AgentTaskQueue, TaskPriority, TaskState, TaskCategory, get_agent_task_queue
from sparkai.agent.agent_code_review import CodeReviewEngine, ReviewSeverity, ReviewCategory, ReviewReport, get_code_review_engine
from sparkai.agent.agent_pipeline import AgentPipeline, StageStatus, PipelineStatus, PipelineRun, get_agent_pipeline
from sparkai.agent.agent_consensus import AgentConsensus, ConsensusProtocol, DeliberationPhase, ConsensusResult, get_agent_consensus
from sparkai.agent.agent_game_analyzer import GameAnalyzer, AnalysisDimension, IssueSeverity, GameAnalysisReport, get_game_analyzer
from sparkai.agent.agent_adaptive_prompting import AdaptivePrompting, OptimizationStrategy, PromptVariant, get_adaptive_prompting
from sparkai.agent.agent_entity_extraction import EntityExtractor, EntityType, GameWorldModel, get_entity_extractor
from sparkai.agent.agent_style_transfer import StyleTransferEngine, StyleProfile, TransferResult, get_style_transfer
from sparkai.agent.agent_curriculum_learning import CurriculumLearningEngine, SkillNode, LearningSession, get_curriculum_learning
from sparkai.agent.agent_balancing import GameBalanceTuner, GameParameter, BalanceReport, get_game_balancer
from sparkai.agent.agent_localization import ContentLocalizationEngine, Locale, LocalizedString, get_localization_engine
from sparkai.agent.agent_tutorial_design import TutorialDesignEngine, MechanicDefinition, TutorialSequence, get_tutorial_designer
from sparkai.agent.agent_game_testing import GameTestingEngine, TestCase, TestRun, get_game_tester
from sparkai.agent.agent_memory_consolidation import MemoryConsolidationEngine, MemoryDomain, get_memory_consolidation
from sparkai.agent.agent_conflict_resolution import ConflictResolutionEngine, ConflictType, ResolutionStrategy, get_conflict_resolver
from sparkai.agent.agent_risk_assessment import RiskAssessmentEngine, RiskCategory, RiskLevel, get_risk_assessor
from sparkai.agent.agent_documentation_generator import DocumentationGenerator, DocumentType, ExportFormat, get_documentation_generator
from sparkai.agent.agent_asset_optimizer import AssetOptimizationEngine, AssetType, QualityPreset, get_asset_optimizer
from sparkai.agent.agent_cross_platform import CrossPlatformEngine, TargetPlatform, PlatformCapability, get_cross_platform_engine
from sparkai.agent.agent_player_analytics import PlayerAnalyticsEngine, PlayerArchetype, SessionQuality, get_player_analytics
from sparkai.agent.agent_adaptive_difficulty import AdaptiveDifficultyEngine, DifficultyBand, FlowZone, get_adaptive_difficulty
from sparkai.agent.agent_content_moderation import ContentModerationEngine, PolicyTier, ModerationAction, get_content_moderation
from sparkai.agent.agent_game_settings import GameSettingsEngine, SettingsDomain, QualityPreset, get_game_settings
from sparkai.agent.agent_game_progression import GameProgressionEngine, ProgressionPhase, ProgressionCurve, get_game_progression
from sparkai.agent.agent_narrative_graph import NarrativeGraphEngine, NarrativeNodeType, NarrativeGraph, get_narrative_graph
from sparkai.agent.agent_asset_harmonizer import AssetHarmonizer, AssetDescriptor, AssetDimension, get_asset_harmonizer
from sparkai.agent.agent_agentic_memory import AgenticMemory, MemoryEntry, MemoryTier, get_agentic_memory
from sparkai.agent.agent_multi_agent_orchestration import MultiAgentOrchestrator, OrchestrationRole, OrchestrationSession, get_multi_agent_orchestrator
from sparkai.agent.agent_realtime_collaboration import RealtimeCollaborationEngine, CollaborationMode, CollaborationSession, get_realtime_collaboration
from sparkai.agent.agent_skill_autonomy import SkillAutonomyEngine, SkillDomain, AutonomousSkill, get_skill_autonomy
from sparkai.agent.agent_expression_validator import ExpressionValidator, ExpressionType, ExpressionValidationResult, get_expression_validator
from sparkai.agent.agent_variable_introspection import VariableIntrospectionEngine, VariableScope, VariableDefinition, get_variable_introspection
from sparkai.agent.agent_theme_designer import ThemeDesigner, StyleMood, ThemeDefinition, get_theme_designer
from sparkai.agent.agent_performance_advisor import PerformanceAdvisor, PerformanceDomain, PerformanceSnapshot, get_performance_advisor
from sparkai.agent.agent_shader_advisor import ShaderAdvisor, ShaderDomain, ShaderPreset, get_shader_advisor
from sparkai.agent.agent_build_orchestrator import BuildOrchestrator, TargetPlatform, BuildConfig, get_build_orchestrator
from sparkai.agent.agent_recall_engine import RecallEngine, RecallDomain, KnowledgeFragment, get_recall_engine
from sparkai.agent.agent_interaction_designer import InteractionDesigner, InteractionPattern, InteractionFlow, get_interaction_designer
from sparkai.agent.agent_physics_tuner import PhysicsTuner, PhysicsDomain as TunerPhysicsDomain, TunerPreset, get_physics_tuner
from sparkai.agent.agent_rag_pipeline import RAGPipeline, get_rag_pipeline
from sparkai.agent.agent_tree_of_thought import TreeOfThought, get_tree_of_thought
from sparkai.engine.camera_shake import CameraShakeSystem, ShakePreset, CameraMode, get_camera_shake_system
from sparkai.engine.difficulty_system import DifficultySystem, DifficultyTier, DifficultyParams, get_difficulty_system
from sparkai.engine.fog_of_war import FogOfWarSystem, TileVisibility, FogShape, get_fog_of_war
from sparkai.engine.game_modes import GameModeSystem, BuiltInMode, ModeLayer, get_game_mode_system


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
    all 145 subsystems. It provides a single entry point for all engine
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
        self._audio_system: Optional[GameAudioSystem] = None
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
        self._insights_engine: Optional[InsightsEngine] = None
        self._state_sync_mesh: Optional[StateSyncMesh] = None
        self._dev_loop: Optional[DevelopmentLoop] = None
        self._context_references: Optional[ContextReferenceResolver] = None
        self._rendering_server: Optional[RenderingServer] = None
        self._input_event_system: Optional[InputEventSystem] = None
        self._game_object_registry: Optional[GameObjectRegistry] = None
        self._scene_manager: Optional[SceneManager] = None
        self._process_registry: Optional[ProcessRegistry] = None
        self._cron_scheduler: Optional[AgentCronScheduler] = None
        self._expression_evaluator: Optional[ExpressionEvaluator] = None
        self._class_registry: Optional[ClassRegistry] = None
        self._multi_modal_agent: Optional[MultiModalAgent] = None
        self._import_pipeline: Optional[ImportPipelineEngine] = None
        self._terrain_system: Optional[TerrainSystem] = None
        self._save_system: Optional[SaveSystem] = None
        self._node_tree: Optional[NodeTreeSystem] = None
        self._extension_registry: Optional[ExtensionRegistry] = None
        self._export_pipeline: Optional[MultiExportPipeline] = None
        self._server_pool: Optional[GameServerPool] = None
        self._gizmo_system: Optional[GizmoSystem] = None
        self._pivot_system: Optional[PivotSystem] = None
        self._network_sync: Optional[NetworkSync] = None
        self._behavior_tree: Optional[BehaviorTree] = None
        self._math_utils: Optional[MathUtils] = None
        self._gui_system: Optional[GUISystem] = None
        self._config_manager: Optional[ConfigManager] = None
        self._animation_controller: Optional[AnimationController] = None
        self._trajectory_recorder_v2: Optional[TrajectoryRecorder] = None
        self._skill_command_registry: Optional[SkillCommandRegistry] = None
        self._session_store: Optional[SessionStore] = None
        self._platform_bridge: Optional[PlatformBridge] = None
        self._tool_composer: Optional[ToolComposer] = None
        self._feedback_loop: Optional[FeedbackLoop] = None
        self._agent_negotiation: Optional[AgentNegotiation] = None
        self._simulation_env: Optional[SimulationEnv] = None
        self._goal_decomposer: Optional[GoalDecomposer] = None
        self._prompt_template_lib: Optional[PromptTemplateLib] = None
        self._semantic_memory: Optional[SemanticMemory] = None
        self._intent_classifier: Optional[IntentClassifier] = None
        self._context_assembler: Optional[ContextAssembler] = None
        self._action_sequencer: Optional[ActionSequencer] = None
        self._agent_event_bus: Optional[AgentEventBus] = None
        self._agent_task_queue: Optional[AgentTaskQueue] = None
        self._code_review_engine: Optional[CodeReviewEngine] = None
        self._agent_pipeline_sys: Optional[AgentPipeline] = None
        self._agent_consensus: Optional[AgentConsensus] = None
        self._game_analyzer: Optional[GameAnalyzer] = None
        self._adaptive_prompting: Optional[AdaptivePrompting] = None
        self._entity_extractor: Optional[EntityExtractor] = None
        self._style_transfer: Optional[StyleTransferEngine] = None
        self._curriculum_learning: Optional[CurriculumLearningEngine] = None
        self._game_balancer: Optional[GameBalanceTuner] = None
        self._localization_engine: Optional[ContentLocalizationEngine] = None
        self._tutorial_designer: Optional[TutorialDesignEngine] = None
        self._game_tester: Optional[GameTestingEngine] = None
        self._memory_consolidation: Optional[MemoryConsolidationEngine] = None
        self._conflict_resolver: Optional[ConflictResolutionEngine] = None
        self._risk_assessor: Optional[RiskAssessmentEngine] = None
        self._documentation_generator: Optional[DocumentationGenerator] = None
        self._asset_optimizer: Optional[AssetOptimizationEngine] = None
        self._cross_platform_engine: Optional[CrossPlatformEngine] = None
        self._player_analytics: Optional[PlayerAnalyticsEngine] = None
        self._adaptive_difficulty: Optional[AdaptiveDifficultyEngine] = None
        self._content_moderation: Optional[ContentModerationEngine] = None
        self._game_settings: Optional[GameSettingsEngine] = None
        self._game_progression: Optional[GameProgressionEngine] = None
        self._narrative_graph: Optional[NarrativeGraphEngine] = None
        self._asset_harmonizer: Optional[AssetHarmonizer] = None
        self._agentic_memory: Optional[AgenticMemory] = None
        self._multi_agent_orchestrator: Optional[MultiAgentOrchestrator] = None
        self._realtime_collaboration: Optional[RealtimeCollaborationEngine] = None
        self._goal_decomposer: Optional[GoalDecomposer] = None
        self._skill_autonomy: Optional[SkillAutonomyEngine] = None
        self._expression_validator: Optional[ExpressionValidator] = None
        self._variable_introspection: Optional[VariableIntrospectionEngine] = None
        self._theme_designer: Optional[ThemeDesigner] = None
        self._performance_advisor: Optional[PerformanceAdvisor] = None
        self._shader_advisor: Optional[ShaderAdvisor] = None
        self._build_orchestrator: Optional[BuildOrchestrator] = None
        self._recall_engine: Optional[RecallEngine] = None
        self._interaction_designer: Optional[InteractionDesigner] = None
        self._physics_tuner: Optional[PhysicsTuner] = None
        self._rag_pipeline: Optional[RAGPipeline] = None
        self._tree_of_thought: Optional[TreeOfThought] = None
        self._prompt_optimizer: Optional[PromptOptimizer] = None
        self._skill_composer: Optional[SkillComposer] = None
        self._ui_layout_system: Optional[UILayoutSystem] = None
        self._performance_overlay: Optional[PerformanceOverlay] = None
        self._developer_assistant: Optional[DeveloperAssistant] = None
        self._playtest_simulator: Optional[AgenticPlaytestSimulator] = None
        self._scene_streamer: Optional[SceneStreamer] = None
        self._project_exporter: Optional[ProjectExporter] = None
        self._camera_shake_system: Optional[CameraShakeSystem] = None
        self._difficulty_system: Optional[DifficultySystem] = None
        self._fog_of_war: Optional[FogOfWarSystem] = None
        self._game_mode_system: Optional[GameModeSystem] = None
        self._game_director: Optional[GameDirector] = None
        self._balance_analyzer: Optional[BalanceAnalyzer] = None
        self._narrative_composer: Optional[NarrativeComposer] = None
        self._player_modeler: Optional[PlayerModeler] = None
        self._learning_loop: Optional[LearningLoop] = None
        self._cron_scheduler: Optional[AgentCronScheduler] = None
        self._memory_graph: Optional[AgentMemoryGraph] = None
        self._context_compressor: Optional[AgentContextCompressor] = None
        self._tool_forge: Optional[AgentToolForge] = None
        self._gateway: Optional[AgentGateway] = None
        self._audio_system: Optional[GameAudioSystem] = None
        self._network_layer: Optional[NetworkLayer] = None
        self._behavior_runtime: Optional[BehaviorRuntime] = None
        self._save_system: Optional[SaveSystem] = None
        self._session_snapshot: Optional[SessionSnapshotSystem] = None
        self._trajectory_compressor: Optional[TrajectoryCompressor] = None
        self._skills_hub: Optional[SkillsHub] = None
        self._personality_system: Optional[PersonalitySystem] = None
        self._insights_generator: Optional[InsightsGenerator] = None
        self._provider_switch: Optional[ProviderSwitch] = None
        self._chain_of_thought: Optional[ChainOfThoughtEngine] = None
        self._conversation_memory: Optional[ConversationMemoryEngine] = None
        self._self_optimization: Optional[SelfOptimizationEngine] = None
        self._collaboration_protocol: Optional[CollaborationProtocolEngine] = None
        self._knowledge_synthesis: Optional[KnowledgeSynthesisEngine] = None
        self._capability_registry: Optional[CapabilityRegistryEngine] = None
        self._event_sheet: Optional[EventSheetRuntime] = None
        self._resource_serializer: Optional[ResourceSerializer] = None
        self._input_map: Optional[InputMapSystem] = None
        self._animation_tree: Optional[AnimationTreeRuntime] = None
        self._custom_object_types: Optional[CustomObjectTypeSystem] = None
        self._tile_map_optimizer: Optional[TileMapOptimizer] = None
        self._experiment_framework: Optional[AgentExperimentFramework] = None
        self._telemetry_pipeline: Optional[AgentTelemetryPipeline] = None
        self._audit_trail: Optional[AgentAuditTrail] = None
        self._journal_system: Optional[AgentJournalSystem] = None
        self._document_synthesizer: Optional[AgentDocumentSynthesizer] = None
        self._simulation_runner: Optional[AgentSimulationRunner] = None
        self._agentic_coding: Optional[AgenticCodingFramework] = None
        self._game_reasoner: Optional[GameDesignReasoner] = None
        self._narrative_branch: Optional[NarrativeBranchSystem] = None
        self._concurrency_manager: Optional[AgentConcurrencyManager] = None
        self._verification_pipeline: Optional[AgentVerificationPipeline] = None
        self._playtest_simulator: Optional[AgenticPlaytestSimulator] = None
        self._skill_synthesizer: Optional[SkillSynthesizer] = None
        self._security_scanner: Optional[SecurityScanner] = None
        self._delegation_framework: Optional[DelegationFramework] = None
        self._kanban_coordinator: Optional[KanbanCoordinator] = None
        self._streaming_scrubber: Optional[StreamingScrubber] = None
        self._trajectory_generator: Optional[TrajectoryGenerator] = None
        self._developer_oracle: Optional[DeveloperOracle] = None
        self._context_weaver: Optional[ContextWeaver] = None
        self._session_nexus: Optional[SessionNexus] = None
        self._persona_vault: Optional[PersonaVault] = None
        self._voice_bridge: Optional[VoiceBridge] = None
        self._ecosystem_hub: Optional[EcosystemHub] = None
        self._intent_cascade: Optional[IntentCascade] = None
        self._game_forecaster: Optional[GameForecaster] = None
        self._asset_synthesizer: Optional[AssetSynthesizer] = None
        self._tutorial_orchestrator: Optional[TutorialOrchestrator] = None
        self._ab_test_runner: Optional[ABTestRunner] = None
        self._heatmap_analyzer: Optional[HeatmapAnalyzer] = None
        self._bug_forensics: Optional[BugForensics] = None
        self._accessibility_auditor: Optional[AccessibilityAuditor] = None
        self._federated_learner: Optional[FederatedLearner] = None
        self._swarm_planner: Optional[SwarmPlanner] = None
        self._world_composer: Optional[WorldComposer] = None
        self._playtest_orchestrator: Optional[PlaytestOrchestrator] = None
        self._reasoning_chain: Optional[ReasoningChain] = None
        self._memory_hierarchy: Optional[MemoryHierarchy] = None
        self._tool_registry: Optional[ToolRegistry] = None
        self._prompt_library: Optional[PromptLibrary] = None
        self._reflection_loop: Optional[ReflectionLoop] = None
        self._skill_forge: Optional[SkillForge] = None
        self._learning_loop: Optional[LearningLoop] = None
        self._memory_consolidator: Optional[MemoryConsolidator] = None
        self._delegation_broker: Optional[DelegationBroker] = None
        self._game_design_intelligence: Optional[GameDesignIntelligence] = None
        self._interaction_synthesis_engine: Optional[InteractionSynthesisEngine] = None
        self._gameplay_ecosystem: Optional[GameplayEcosystemSimulator] = None
        self._creative_director: Optional[AgentCreativeDirector] = None
        self._social_simulation: Optional[AgentSocialSimulation] = None
        self._monetization_designer: Optional[AgentMonetizationDesigner] = None
        self._world_builder: Optional[AgentWorldBuilder] = None
        self._behavior_designer: Optional[AgentBehaviorDesigner] = None
        self._quest_composer: Optional[AgentQuestComposer] = None
        self._multi_agent_coordinator: Optional[AgentMultiAgentCoordinator] = None
        self._memory_orchestrator: Optional[AgentMemoryOrchestrator] = None
        self._simulation_controller: Optional[AgentSimulationController] = None
        self._timeline_manager: Optional[AgentTimelineManager] = None
        self._skill_generator: Optional[AgentSkillGenerator] = None
        self._learning_loop: Optional[AgentLearningLoop] = None
        self._social_dynamics: Optional[AgentSocialDynamics] = None
        self._emergent_narrative: Optional[AgentEmergentNarrative] = None
        self._procedural_world: Optional[EngineProceduralWorld] = None
        self._render_pipeline: Optional[EngineRenderPipeline] = None
        self._physics_dynamics: Optional[EnginePhysicsDynamics] = None
        self._audio_spatial: Optional[EngineAudioSpatial] = None
        self._behavior_orchestrator: Optional[EngineBehaviorOrchestrator] = None
        self._cross_module_orchestrator: Optional[AgentCrossModuleOrchestrator] = None
        self._session_snapshot_ok: bool = False
        self._trajectory_compressor_ok: bool = False
        self._skills_hub_ok: bool = False
        self._personality_system_ok: bool = False
        self._insights_generator_ok: bool = False
        self._provider_switch_ok: bool = False
        self._chain_of_thought_ok: bool = False
        self._conversation_memory_ok: bool = False
        self._self_optimization_ok: bool = False
        self._collaboration_protocol_ok: bool = False
        self._knowledge_synthesis_ok: bool = False
        self._capability_registry_ok: bool = False
        self._event_sheet_ok: bool = False
        self._resource_serializer_ok: bool = False
        self._input_map_ok: bool = False
        self._animation_tree_ok: bool = False
        self._custom_object_types_ok: bool = False
        self._tile_map_optimizer_ok: bool = False
        self._experiment_framework_ok: bool = False
        self._telemetry_pipeline_ok: bool = False
        self._audit_trail_ok: bool = False
        self._journal_system_ok: bool = False
        self._document_synthesizer_ok: bool = False
        self._simulation_runner_ok: bool = False
        self._agentic_coding_ok: bool = False
        self._game_reasoner_ok: bool = False
        self._narrative_branch_ok: bool = False
        self._concurrency_manager_ok: bool = False
        self._verification_pipeline_ok: bool = False
        self._playtest_simulator_ok: bool = False
        self._skill_synthesizer_ok: bool = False
        self._security_scanner_ok: bool = False
        self._delegation_framework_ok: bool = False
        self._kanban_coordinator_ok: bool = False
        self._streaming_scrubber_ok: bool = False
        self._trajectory_generator_ok: bool = False

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
            self._insights_engine = get_insights_engine()
            self._state_sync_mesh = get_state_sync_mesh()
            self._dev_loop = get_dev_loop()
            self._context_references = get_context_reference_resolver()
            self._rendering_server = get_rendering_server()
            self._input_event_system = get_input_event_system()
            self._game_object_registry = get_game_object_registry()
            self._scene_manager = get_scene_manager()
            self._process_registry = get_process_registry()
            self._cron_scheduler = get_cron_scheduler()
            self._expression_evaluator = get_expression_evaluator()
            self._class_registry = get_class_registry()
            self._multi_modal_agent = get_multi_modal_agent()
            self._import_pipeline = get_import_pipeline()
            self._terrain_system = get_terrain_system()
            self._save_system = get_save_system()
            self._node_tree = get_node_tree()
            self._extension_registry = get_extension_registry()
            self._export_pipeline = get_export_pipeline()
            self._server_pool = get_server_pool()
            self._gizmo_system = get_gizmo_system()
            self._pivot_system = get_pivot_system()
            self._network_sync = get_network_sync()
            self._behavior_tree = get_behavior_tree()
            self._math_utils = get_math_utils()
            self._gui_system = get_gui_system()
            self._config_manager = get_config_manager()
            self._animation_controller = get_animation_controller()
            self._trajectory_recorder_v2 = get_trajectory_recorder()
            self._skill_command_registry = get_skill_command_registry()
            self._session_store = get_session_store()
            self._platform_bridge = get_platform_bridge()
            self._tool_composer = get_tool_composer()
            self._feedback_loop = get_feedback_loop()
            self._agent_negotiation = get_agent_negotiation()
            self._simulation_env = get_simulation_env()
            self._goal_decomposer = get_goal_decomposer()
            self._prompt_template_lib = get_prompt_template_lib()
            self._semantic_memory = get_semantic_memory()
            self._intent_classifier = get_intent_classifier()
            self._context_assembler = get_context_assembler()
            self._action_sequencer = get_action_sequencer()
            self._agent_event_bus = get_agent_event_bus()
            self._agent_task_queue = get_agent_task_queue()
            self._agent_task_queue.start()
            self._code_review_engine = get_code_review_engine()
            self._agent_pipeline_sys = get_agent_pipeline()
            self._agent_consensus = get_agent_consensus()
            self._game_analyzer = get_game_analyzer()
            self._adaptive_prompting = get_adaptive_prompting()
            self._entity_extractor = get_entity_extractor()
            self._style_transfer = get_style_transfer()
            self._curriculum_learning = get_curriculum_learning()
            self._game_balancer = get_game_balancer()
            self._localization_engine = get_localization_engine()
            self._tutorial_designer = get_tutorial_designer()
            self._game_tester = get_game_tester()
            self._memory_consolidation = get_memory_consolidation()
            self._conflict_resolver = get_conflict_resolver()
            self._risk_assessor = get_risk_assessor()
            self._documentation_generator = get_documentation_generator()
            self._asset_optimizer = get_asset_optimizer()
            self._cross_platform_engine = get_cross_platform_engine()
            self._player_analytics = get_player_analytics()
            self._adaptive_difficulty = get_adaptive_difficulty()
            self._content_moderation = get_content_moderation()
            self._game_settings = get_game_settings()
            self._game_progression = get_game_progression()
            self._narrative_graph = get_narrative_graph()
            self._asset_harmonizer = get_asset_harmonizer()
            self._agentic_memory = get_agentic_memory()
            self._multi_agent_orchestrator = get_multi_agent_orchestrator()
            self._realtime_collaboration = get_realtime_collaboration()
            self._goal_decomposer = get_goal_decomposer()
            self._skill_autonomy = get_skill_autonomy()
            self._expression_validator = get_expression_validator()
            self._variable_introspection = get_variable_introspection()
            self._theme_designer = get_theme_designer()
            self._performance_advisor = get_performance_advisor()
            self._shader_advisor = get_shader_advisor()
            self._build_orchestrator = get_build_orchestrator()
            self._recall_engine = get_recall_engine()
            self._interaction_designer = get_interaction_designer()
            self._physics_tuner = get_physics_tuner()
            self._camera_shake_system = get_camera_shake_system()
            self._difficulty_system = get_difficulty_system()
            self._fog_of_war = get_fog_of_war()
            self._game_mode_system = get_game_mode_system()
            self._rag_pipeline = get_rag_pipeline()
            self._tree_of_thought = get_tree_of_thought()
            self._prompt_optimizer = get_prompt_optimizer()
            self._skill_composer = get_skill_composer()
            self._ui_layout_system = get_ui_layout_system()
            self._performance_overlay = get_performance_overlay()
            self._developer_assistant = get_developer_assistant()
            self._playtest_simulator = get_playtest_simulator()
            self._game_director = get_game_director()
            self._balance_analyzer = get_balance_analyzer()
            self._narrative_composer = get_narrative_composer()
            self._player_modeler = get_player_modeler()
            self._learning_loop = get_learning_loop()
            self._cron_scheduler = get_cron_scheduler()
            self._memory_graph = get_memory_graph()
            self._context_compressor = get_context_compressor()
            self._tool_forge = get_tool_forge()
            self._gateway = get_gateway()
            self._audio_system = get_audio_system()
            self._network_layer = get_network_layer()
            self._behavior_runtime = get_behavior_runtime()
            self._save_system = get_save_system()
            self._scene_streamer = get_scene_streamer()
            self._project_exporter = get_project_exporter()
            self._session_snapshot = get_session_snapshot()
            self._trajectory_compressor = get_trajectory_compressor()
            self._skills_hub = get_skills_hub()
            self._personality_system = get_personality_system()
            self._insights_generator = get_insights_generator()
            self._provider_switch = get_provider_switch()
            self._chain_of_thought = get_chain_of_thought()
            self._conversation_memory = get_conversation_memory()
            self._self_optimization = get_self_optimization()
            self._collaboration_protocol = get_collaboration_protocol()
            self._knowledge_synthesis = get_knowledge_synthesis()
            self._capability_registry = get_capability_registry()
            self._event_sheet = get_event_sheet()
            self._resource_serializer = get_resource_serializer()
            self._input_map = get_input_map()
            self._animation_tree = get_animation_tree()
            self._custom_object_types = get_custom_object_types()
            self._tile_map_optimizer = get_tile_map_optimizer()
            self._experiment_framework = get_experiment_framework()
            self._telemetry_pipeline = get_telemetry_pipeline()
            self._audit_trail = get_audit_trail()
            self._journal_system = get_journal_system()
            self._document_synthesizer = get_document_synthesizer()
            self._simulation_runner = get_simulation_runner()
            self._agentic_coding = get_agentic_coding()
            self._game_reasoner = get_game_reasoner()
            self._narrative_branch = get_narrative_branch()
            self._concurrency_manager = get_concurrency_manager()
            self._verification_pipeline = get_verification_pipeline()
            self._playtest_simulator = get_playtest_simulator()
            self._skill_synthesizer = get_skill_synthesizer()
            self._security_scanner = get_security_scanner()
            self._delegation_framework = get_delegation_framework()
            self._kanban_coordinator = get_kanban_coordinator()
            self._streaming_scrubber = get_streaming_scrubber()
            self._trajectory_generator = get_trajectory_generator()
            self._developer_oracle = get_developer_oracle()
            self._context_weaver = get_context_weaver()
            self._session_nexus = get_session_nexus()
            self._persona_vault = get_persona_vault()
            self._voice_bridge = get_voice_bridge()
            self._ecosystem_hub = get_ecosystem_hub()
            self._intent_cascade = get_intent_cascade()
            self._game_forecaster = get_game_forecaster()
            self._asset_synthesizer = get_asset_synthesizer()
            self._tutorial_orchestrator = get_tutorial_orchestrator()
            self._ab_test_runner = get_ab_test_runner()
            self._heatmap_analyzer = get_heatmap_analyzer()
            self._bug_forensics = get_bug_forensics()
            self._accessibility_auditor = get_accessibility_auditor()
            self._federated_learner = get_federated_learner()
            self._swarm_planner = get_swarm_planner()
            self._world_composer = get_world_composer()
            self._playtest_orchestrator = get_playtest_orchestrator()
            self._reasoning_chain = get_reasoning_chain()
            self._memory_hierarchy = get_memory_hierarchy()
            self._tool_registry = get_tool_registry()
            self._prompt_library = get_prompt_library()
            self._reflection_loop = get_reflection_loop()
            self._skill_forge = get_skill_forge()
            self._learning_loop = get_learning_loop()
            self._memory_consolidator = get_memory_consolidator()
            self._delegation_broker = get_delegation_broker()
            self._game_design_intelligence = get_game_design_intelligence()
            self._interaction_synthesis_engine = get_interaction_synthesis_engine()
            self._gameplay_ecosystem = get_gameplay_ecosystem_simulator()
            self._creative_director = get_creative_director()
            self._social_simulation = get_agent_social_simulation()
            self._monetization_designer = get_monetization_designer()
            self._world_builder = get_agent_world_builder()
            self._behavior_designer = get_agent_behavior_designer()
            self._quest_composer = get_agent_quest_composer()
            self._multi_agent_coordinator = get_multi_agent_coordinator()
            self._memory_orchestrator = get_memory_orchestrator()
            self._simulation_controller = get_simulation_controller()
            self._timeline_manager = get_timeline_manager()
            self._skill_generator = get_skill_generator()
            self._learning_loop = get_learning_loop()
            self._social_dynamics = get_social_dynamics()
            self._emergent_narrative = get_emergent_narrative()
            self._procedural_world = get_procedural_world()
            self._render_pipeline = get_render_pipeline()
            self._physics_dynamics = get_engine_physics_dynamics()
            self._audio_spatial = get_audio_spatial()
            self._behavior_orchestrator = get_engine_behavior_orchestrator()
            self._cross_module_orchestrator = get_cross_module_orchestrator()
            self._session_snapshot_ok = self._session_snapshot is not None
            self._trajectory_compressor_ok = self._trajectory_compressor is not None
            self._skills_hub_ok = self._skills_hub is not None
            self._personality_system_ok = self._personality_system is not None
            self._insights_generator_ok = self._insights_generator is not None
            self._provider_switch_ok = self._provider_switch is not None
            self._chain_of_thought_ok = self._chain_of_thought is not None
            self._conversation_memory_ok = self._conversation_memory is not None
            self._self_optimization_ok = self._self_optimization is not None
            self._collaboration_protocol_ok = self._collaboration_protocol is not None
            self._knowledge_synthesis_ok = self._knowledge_synthesis is not None
            self._capability_registry_ok = self._capability_registry is not None
            self._event_sheet_ok = self._event_sheet is not None
            self._resource_serializer_ok = self._resource_serializer is not None
            self._input_map_ok = self._input_map is not None
            self._animation_tree_ok = self._animation_tree is not None
            self._custom_object_types_ok = self._custom_object_types is not None
            self._tile_map_optimizer_ok = self._tile_map_optimizer is not None
            self._experiment_framework_ok = self._experiment_framework is not None
            self._telemetry_pipeline_ok = self._telemetry_pipeline is not None
            self._audit_trail_ok = self._audit_trail is not None
            self._journal_system_ok = self._journal_system is not None
            self._document_synthesizer_ok = self._document_synthesizer is not None
            self._simulation_runner_ok = self._simulation_runner is not None
            self._agentic_coding_ok = self._agentic_coding is not None
            self._game_reasoner_ok = self._game_reasoner is not None
            self._narrative_branch_ok = self._narrative_branch is not None
            self._concurrency_manager_ok = self._concurrency_manager is not None
            self._verification_pipeline_ok = self._verification_pipeline is not None
            self._playtest_simulator_ok = self._playtest_simulator is not None
            self._skill_synthesizer_ok = self._skill_synthesizer is not None
            self._security_scanner_ok = self._security_scanner is not None
            self._delegation_framework_ok = self._delegation_framework is not None
            self._kanban_coordinator_ok = self._kanban_coordinator is not None
            self._streaming_scrubber_ok = self._streaming_scrubber is not None
            self._trajectory_generator_ok = self._trajectory_generator is not None
            self._developer_oracle_ok = self._developer_oracle is not None
            self._context_weaver_ok = self._context_weaver is not None
            self._session_nexus_ok = self._session_nexus is not None
            self._persona_vault_ok = self._persona_vault is not None
            self._voice_bridge_ok = self._voice_bridge is not None
            self._ecosystem_hub_ok = self._ecosystem_hub is not None
            self._intent_cascade_ok = self._intent_cascade is not None
            self._game_forecaster_ok = self._game_forecaster is not None
            self._asset_synthesizer_ok = self._asset_synthesizer is not None
            self._tutorial_orchestrator_ok = self._tutorial_orchestrator is not None
            self._ab_test_runner_ok = self._ab_test_runner is not None
            self._heatmap_analyzer_ok = self._heatmap_analyzer is not None
            self._bug_forensics_ok = self._bug_forensics is not None
            self._accessibility_auditor_ok = self._accessibility_auditor is not None
            self._federated_learner_ok = self._federated_learner is not None
            self._swarm_planner_ok = self._swarm_planner is not None
            self._world_composer_ok = self._world_composer is not None
            self._playtest_orchestrator_ok = self._playtest_orchestrator is not None
            self._reasoning_chain_ok = self._reasoning_chain is not None
            self._memory_hierarchy_ok = self._memory_hierarchy is not None
            self._tool_registry_ok = self._tool_registry is not None
            self._prompt_library_ok = self._prompt_library is not None
            self._reflection_loop_ok = self._reflection_loop is not None
            self._skill_forge_ok = self._skill_forge is not None
            self._learning_loop_ok = self._learning_loop is not None
            self._memory_consolidator_ok = self._memory_consolidator is not None
            self._delegation_broker_ok = self._delegation_broker is not None
            self._game_design_intelligence_ok = self._game_design_intelligence is not None
            self._interaction_synthesis_engine_ok = self._interaction_synthesis_engine is not None
            self._gameplay_ecosystem_ok = self._gameplay_ecosystem is not None
            self._creative_director_ok = self._creative_director is not None
            self._social_simulation_ok = self._social_simulation is not None
            self._monetization_designer_ok = self._monetization_designer is not None
            self._world_builder_ok = self._world_builder is not None
            self._behavior_designer_ok = self._behavior_designer is not None
            self._quest_composer_ok = self._quest_composer is not None
            self._multi_agent_coordinator_ok = self._multi_agent_coordinator is not None
            self._memory_orchestrator_ok = self._memory_orchestrator is not None
            self._simulation_controller_ok = self._simulation_controller is not None
            self._timeline_manager_ok = self._timeline_manager is not None
            self._skill_generator_ok = self._skill_generator is not None
            self._learning_loop_ok = self._learning_loop is not None
            self._social_dynamics_ok = self._social_dynamics is not None
            self._emergent_narrative_ok = self._emergent_narrative is not None
            self._procedural_world_ok = self._procedural_world is not None
            self._render_pipeline_ok = self._render_pipeline is not None

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
            self._integration.register_subsystem("insights_engine", self._insights_engine)
            self._integration.register_subsystem("state_sync_mesh", self._state_sync_mesh)
            self._integration.register_subsystem("dev_loop", self._dev_loop)
            self._integration.register_subsystem("context_references", self._context_references)
            self._integration.register_subsystem("rendering_server", self._rendering_server)
            self._integration.register_subsystem("input_event_system", self._input_event_system)
            self._integration.register_subsystem("game_object_registry", self._game_object_registry)
            self._integration.register_subsystem("scene_manager", self._scene_manager)
            self._integration.register_subsystem("process_registry", self._process_registry)
            self._integration.register_subsystem("cron_scheduler", self._cron_scheduler)
            self._integration.register_subsystem("expression_evaluator", self._expression_evaluator)
            self._integration.register_subsystem("class_registry", self._class_registry)
            self._integration.register_subsystem("multi_modal_agent", self._multi_modal_agent)
            self._integration.register_subsystem("import_pipeline", self._import_pipeline)
            self._integration.register_subsystem("terrain_system", self._terrain_system)
            self._integration.register_subsystem("save_system", self._save_system)
            self._integration.register_subsystem("node_tree", self._node_tree)
            self._integration.register_subsystem("extension_registry", self._extension_registry)
            self._integration.register_subsystem("export_pipeline", self._export_pipeline)
            self._integration.register_subsystem("server_pool", self._server_pool)
            self._integration.register_subsystem("gizmo_system", self._gizmo_system)
            self._integration.register_subsystem("pivot_system", self._pivot_system)
            self._integration.register_subsystem("network_sync", self._network_sync)
            self._integration.register_subsystem("behavior_tree", self._behavior_tree)
            self._integration.register_subsystem("math_utils", self._math_utils)
            self._integration.register_subsystem("gui_system", self._gui_system)
            self._integration.register_subsystem("config_manager", self._config_manager)
            self._integration.register_subsystem("animation_controller", self._animation_controller)
            self._integration.register_subsystem("trajectory_recorder_v2", self._trajectory_recorder_v2)
            self._integration.register_subsystem("skill_command_registry", self._skill_command_registry)
            self._integration.register_subsystem("session_store", self._session_store)
            self._integration.register_subsystem("platform_bridge", self._platform_bridge)
            self._integration.register_subsystem("reasoning_chain", self._reasoning_chain)
            self._integration.register_subsystem("tool_composer", self._tool_composer)
            self._integration.register_subsystem("feedback_loop", self._feedback_loop)
            self._integration.register_subsystem("agent_negotiation", self._agent_negotiation)
            self._integration.register_subsystem("simulation_env", self._simulation_env)
            self._integration.register_subsystem("goal_decomposer", self._goal_decomposer)
            self._integration.register_subsystem("prompt_template_lib", self._prompt_template_lib)
            self._integration.register_subsystem("semantic_memory", self._semantic_memory)
            self._integration.register_subsystem("intent_classifier", self._intent_classifier)
            self._integration.register_subsystem("context_assembler", self._context_assembler)
            self._integration.register_subsystem("action_sequencer", self._action_sequencer)
            self._integration.register_subsystem("agent_event_bus", self._agent_event_bus)
            self._integration.register_subsystem("agent_task_queue", self._agent_task_queue)
            self._integration.register_subsystem("code_review_engine", self._code_review_engine)
            self._integration.register_subsystem("agent_pipeline_sys", self._agent_pipeline_sys)
            self._integration.register_subsystem("camera_shake_system", self._camera_shake_system)
            self._integration.register_subsystem("difficulty_system", self._difficulty_system)
            self._integration.register_subsystem("fog_of_war", self._fog_of_war)
            self._integration.register_subsystem("game_mode_system", self._game_mode_system)
            self._integration.register_subsystem("agent_consensus", self._agent_consensus)
            self._integration.register_subsystem("game_analyzer", self._game_analyzer)
            self._integration.register_subsystem("adaptive_prompting", self._adaptive_prompting)
            self._integration.register_subsystem("entity_extractor", self._entity_extractor)
            self._integration.register_subsystem("style_transfer", self._style_transfer)
            self._integration.register_subsystem("curriculum_learning", self._curriculum_learning)
            self._integration.register_subsystem("game_balancer", self._game_balancer)
            self._integration.register_subsystem("localization_engine", self._localization_engine)
            self._integration.register_subsystem("tutorial_designer", self._tutorial_designer)
            self._integration.register_subsystem("game_tester", self._game_tester)
            self._integration.register_subsystem("player_analytics", self._player_analytics)
            self._integration.register_subsystem("adaptive_difficulty", self._adaptive_difficulty)
            self._integration.register_subsystem("content_moderation", self._content_moderation)
            self._integration.register_subsystem("game_settings", self._game_settings)
            self._integration.register_subsystem("game_progression", self._game_progression)
            self._integration.register_subsystem("narrative_graph", self._narrative_graph)
            self._integration.register_subsystem("asset_harmonizer", self._asset_harmonizer)
            self._integration.register_subsystem("agentic_memory", self._agentic_memory)
            self._integration.register_subsystem("multi_agent_orchestrator", self._multi_agent_orchestrator)
            self._integration.register_subsystem("realtime_collaboration", self._realtime_collaboration)
            self._integration.register_subsystem("goal_decomposer", self._goal_decomposer)
            self._integration.register_subsystem("skill_autonomy", self._skill_autonomy)
            self._integration.register_subsystem("expression_validator", self._expression_validator)
            self._integration.register_subsystem("variable_introspection", self._variable_introspection)
            self._integration.register_subsystem("theme_designer", self._theme_designer)
            self._integration.register_subsystem("performance_advisor", self._performance_advisor)
            self._integration.register_subsystem("shader_advisor", self._shader_advisor)
            self._integration.register_subsystem("build_orchestrator", self._build_orchestrator)
            self._integration.register_subsystem("recall_engine", self._recall_engine)
            self._integration.register_subsystem("interaction_designer", self._interaction_designer)
            self._integration.register_subsystem("physics_tuner", self._physics_tuner)
            self._integration.register_subsystem("rag_pipeline", self._rag_pipeline)
            self._integration.register_subsystem("tree_of_thought", self._tree_of_thought)
            self._integration.register_subsystem("reflection_loop", self._reflection_loop)
            self._integration.register_subsystem("prompt_optimizer", self._prompt_optimizer)
            self._integration.register_subsystem("skill_composer", self._skill_composer)
            self._integration.register_subsystem("ui_layout_system", self._ui_layout_system)
            self._integration.register_subsystem("performance_overlay", self._performance_overlay)
            self._integration.register_subsystem("developer_assistant", self._developer_assistant)
            self._integration.register_subsystem("playtest_simulator", self._playtest_simulator)
            self._integration.register_subsystem("game_director", self._game_director)
            self._integration.register_subsystem("balance_analyzer", self._balance_analyzer)
            self._integration.register_subsystem("narrative_composer", self._narrative_composer)
            self._integration.register_subsystem("player_modeler", self._player_modeler)
            self._integration.register_subsystem("learning_loop", self._learning_loop)
            self._integration.register_subsystem("cron_scheduler", self._cron_scheduler)
            self._integration.register_subsystem("memory_graph", self._memory_graph)
            self._integration.register_subsystem("context_compressor", self._context_compressor)
            self._integration.register_subsystem("tool_forge", self._tool_forge)
            self._integration.register_subsystem("gateway", self._gateway)
            self._integration.register_subsystem("audio_system", self._audio_system)
            self._integration.register_subsystem("network_layer", self._network_layer)
            self._integration.register_subsystem("behavior_runtime", self._behavior_runtime)
            self._integration.register_subsystem("save_system", self._save_system)
            self._integration.register_subsystem("scene_streamer", self._scene_streamer)
            self._integration.register_subsystem("project_exporter", self._project_exporter)
            self._integration.register_subsystem("session_snapshot", self._session_snapshot)
            self._integration.register_subsystem("trajectory_compressor", self._trajectory_compressor)
            self._integration.register_subsystem("skills_hub", self._skills_hub)
            self._integration.register_subsystem("personality_system", self._personality_system)
            self._integration.register_subsystem("insights_generator", self._insights_generator)
            self._integration.register_subsystem("provider_switch", self._provider_switch)
            self._integration.register_subsystem("chain_of_thought", self._chain_of_thought)
            self._integration.register_subsystem("conversation_memory", self._conversation_memory)
            self._integration.register_subsystem("self_optimization", self._self_optimization)
            self._integration.register_subsystem("collaboration_protocol", self._collaboration_protocol)
            self._integration.register_subsystem("knowledge_synthesis", self._knowledge_synthesis)
            self._integration.register_subsystem("capability_registry", self._capability_registry)
            self._integration.register_subsystem("event_sheet", self._event_sheet)
            self._integration.register_subsystem("resource_serializer", self._resource_serializer)
            self._integration.register_subsystem("input_map", self._input_map)
            self._integration.register_subsystem("animation_tree", self._animation_tree)
            self._integration.register_subsystem("custom_object_types", self._custom_object_types)
            self._integration.register_subsystem("tile_map_optimizer", self._tile_map_optimizer)
            self._integration.register_subsystem("experiment_framework", self._experiment_framework)
            self._integration.register_subsystem("telemetry_pipeline", self._telemetry_pipeline)
            self._integration.register_subsystem("audit_trail", self._audit_trail)
            self._integration.register_subsystem("journal_system", self._journal_system)
            self._integration.register_subsystem("document_synthesizer", self._document_synthesizer)
            self._integration.register_subsystem("simulation_runner", self._simulation_runner)
            self._integration.register_subsystem("agentic_coding", self._agentic_coding)
            self._integration.register_subsystem("game_reasoner", self._game_reasoner)
            self._integration.register_subsystem("narrative_branch", self._narrative_branch)
            self._integration.register_subsystem("concurrency_manager", self._concurrency_manager)
            self._integration.register_subsystem("verification_pipeline", self._verification_pipeline)
            self._integration.register_subsystem("playtest_simulator", self._playtest_simulator)
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
                    "subsystems": 187,
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
    def audio_system(self) -> Optional[GameAudioSystem]:
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

    @property
    def insights_engine(self) -> Optional[InsightsEngine]:
        return self._insights_engine

    @property
    def state_sync_mesh(self) -> Optional[StateSyncMesh]:
        return self._state_sync_mesh

    @property
    def dev_loop(self) -> Optional[DevelopmentLoop]:
        return self._dev_loop

    @property
    def context_references(self) -> Optional[ContextReferenceResolver]:
        return self._context_references

    @property
    def rendering_server(self) -> Optional[RenderingServer]:
        return self._rendering_server

    @property
    def input_event_system(self) -> Optional[InputEventSystem]:
        return self._input_event_system

    @property
    def game_object_registry(self) -> Optional[GameObjectRegistry]:
        return self._game_object_registry

    @property
    def scene_manager(self) -> Optional[SceneManager]:
        return self._scene_manager

    @property
    def process_registry(self) -> Optional[ProcessRegistry]:
        return self._process_registry

    @property
    def cron_scheduler(self) -> Optional[AgentCronScheduler]:
        return self._cron_scheduler

    @property
    def expression_evaluator(self) -> Optional[ExpressionEvaluator]:
        return self._expression_evaluator

    @property
    def class_registry(self) -> Optional[ClassRegistry]:
        return self._class_registry

    @property
    def multi_modal_agent(self) -> Optional[MultiModalAgent]:
        return self._multi_modal_agent

    @property
    def import_pipeline(self) -> Optional[ImportPipelineEngine]:
        return self._import_pipeline

    @property
    def terrain_system(self) -> Optional[TerrainSystem]:
        return self._terrain_system

    @property
    def save_system(self) -> Optional[SaveSystem]:
        return self._save_system

    @property
    def network_sync(self) -> Optional[NetworkSync]:
        return self._network_sync

    @property
    def behavior_tree(self) -> Optional[BehaviorTree]:
        return self._behavior_tree

    @property
    def math_utils(self) -> Optional[MathUtils]:
        return self._math_utils

    @property
    def gui_system(self) -> Optional[GUISystem]:
        return self._gui_system

    @property
    def config_manager(self) -> Optional[ConfigManager]:
        return self._config_manager

    @property
    def animation_controller(self) -> Optional[AnimationController]:
        return self._animation_controller

    @property
    def trajectory_recorder_v2(self) -> Optional[TrajectoryRecorder]:
        return self._trajectory_recorder_v2

    @property
    def skill_command_registry(self) -> Optional[SkillCommandRegistry]:
        return self._skill_command_registry

    @property
    def session_store(self) -> Optional[SessionStore]:
        return self._session_store

    @property
    def platform_bridge(self) -> Optional[PlatformBridge]:
        return self._platform_bridge

    @property
    def reasoning_chain(self) -> Optional[ReasoningChain]:
        return self._reasoning_chain

    @property
    def tool_composer(self) -> Optional[ToolComposer]:
        return self._tool_composer

    @property
    def feedback_loop(self) -> Optional[FeedbackLoop]:
        return self._feedback_loop

    @property
    def agent_negotiation(self) -> Optional[AgentNegotiation]:
        return self._agent_negotiation

    @property
    def simulation_env(self) -> Optional[SimulationEnv]:
        return self._simulation_env

    @property
    def goal_decomposer(self) -> Optional[GoalDecomposer]:
        return self._goal_decomposer

    @property
    def prompt_template_lib(self) -> Optional[PromptTemplateLib]:
        return self._prompt_template_lib

    @property
    def semantic_memory(self) -> Optional[SemanticMemory]:
        return self._semantic_memory

    @property
    def intent_classifier(self) -> Optional[IntentClassifier]:
        return self._intent_classifier

    @property
    def context_assembler(self) -> Optional[ContextAssembler]:
        return self._context_assembler

    @property
    def action_sequencer(self) -> Optional[ActionSequencer]:
        return self._action_sequencer

    @property
    def agent_event_bus(self) -> Optional[AgentEventBus]:
        return self._agent_event_bus

    @property
    def agent_task_queue(self) -> Optional[AgentTaskQueue]:
        return self._agent_task_queue

    @property
    def code_review_engine(self) -> Optional[CodeReviewEngine]:
        return self._code_review_engine

    @property
    def agent_pipeline_sys(self) -> Optional[AgentPipeline]:
        return self._agent_pipeline_sys

    @property
    def camera_shake_system(self) -> Optional[CameraShakeSystem]:
        return self._camera_shake_system

    @property
    def difficulty_system(self) -> Optional[DifficultySystem]:
        return self._difficulty_system

    @property
    def fog_of_war(self) -> Optional[FogOfWarSystem]:
        return self._fog_of_war

    @property
    def game_mode_system(self) -> Optional[GameModeSystem]:
        return self._game_mode_system

    @property
    def agent_consensus(self) -> Optional[AgentConsensus]:
        return self._agent_consensus

    @property
    def game_analyzer(self) -> Optional[GameAnalyzer]:
        return self._game_analyzer

    @property
    def adaptive_prompting(self) -> Optional[AdaptivePrompting]:
        return self._adaptive_prompting

    @property
    def entity_extractor(self) -> Optional[EntityExtractor]:
        return self._entity_extractor

    @property
    def style_transfer(self) -> Optional[StyleTransferEngine]:
        return self._style_transfer

    @property
    def curriculum_learning(self) -> Optional[CurriculumLearningEngine]:
        return self._curriculum_learning

    @property
    def game_balancer(self) -> Optional[GameBalanceTuner]:
        return self._game_balancer

    @property
    def localization_engine(self) -> Optional[ContentLocalizationEngine]:
        return self._localization_engine

    @property
    def tutorial_designer(self) -> Optional[TutorialDesignEngine]:
        return self._tutorial_designer

    @property
    def game_tester(self) -> Optional[GameTestingEngine]:
        return self._game_tester

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
                "insights_engine": self._insights_engine is not None,
                "state_sync_mesh": self._state_sync_mesh is not None,
                "dev_loop": self._dev_loop is not None,
                "context_references": self._context_references is not None,
                "rendering_server": self._rendering_server is not None,
                "input_event_system": self._input_event_system is not None,
                "game_object_registry": self._game_object_registry is not None,
                "scene_manager": self._scene_manager is not None,
                "process_registry": self._process_registry is not None,
                "cron_scheduler": self._cron_scheduler is not None,
                "expression_evaluator": self._expression_evaluator is not None,
                "class_registry": self._class_registry is not None,
                "multi_modal_agent": self._multi_modal_agent is not None,
                "import_pipeline": self._import_pipeline is not None,
                "terrain_system": self._terrain_system is not None,
                "save_system": self._save_system is not None,
                "node_tree": self._node_tree is not None,
                "extension_registry": self._extension_registry is not None,
                "export_pipeline": self._export_pipeline is not None,
                "server_pool": self._server_pool is not None,
                "gizmo_system": self._gizmo_system is not None,
                "pivot_system": self._pivot_system is not None,
                "network_sync": self._network_sync is not None,
                "behavior_tree": self._behavior_tree is not None,
                "math_utils": self._math_utils is not None,
                "gui_system": self._gui_system is not None,
                "config_manager": self._config_manager is not None,
                "animation_controller": self._animation_controller is not None,
                "trajectory_recorder_v2": self._trajectory_recorder_v2 is not None,
                "skill_command_registry": self._skill_command_registry is not None,
                "session_store": self._session_store is not None,
                "platform_bridge": self._platform_bridge is not None,
                "tool_composer": self._tool_composer is not None,
                "feedback_loop": self._feedback_loop is not None,
                "agent_negotiation": self._agent_negotiation is not None,
                "simulation_env": self._simulation_env is not None,
                "goal_decomposer": self._goal_decomposer is not None,
                "prompt_template_lib": self._prompt_template_lib is not None,
                "semantic_memory": self._semantic_memory is not None,
                "intent_classifier": self._intent_classifier is not None,
                "context_assembler": self._context_assembler is not None,
                "action_sequencer": self._action_sequencer is not None,
                "agent_event_bus": self._agent_event_bus is not None,
                "agent_task_queue": self._agent_task_queue is not None,
                "code_review_engine": self._code_review_engine is not None,
                "agent_pipeline_sys": self._agent_pipeline_sys is not None,
                "camera_shake_system": self._camera_shake_system is not None,
                "difficulty_system": self._difficulty_system is not None,
                "fog_of_war": self._fog_of_war is not None,
                "game_mode_system": self._game_mode_system is not None,
                "player_analytics": self._player_analytics is not None,
                "adaptive_difficulty": self._adaptive_difficulty is not None,
                "content_moderation": self._content_moderation is not None,
                "game_settings": self._game_settings is not None,
                "game_progression": self._game_progression is not None,
                "narrative_graph": self._narrative_graph is not None,
                "asset_harmonizer": self._asset_harmonizer is not None,
                "agentic_memory": self._agentic_memory is not None,
                "multi_agent_orchestrator": self._multi_agent_orchestrator is not None,
                "realtime_collaboration": self._realtime_collaboration is not None,
                "goal_decomposer": self._goal_decomposer is not None,
                "skill_autonomy": self._skill_autonomy is not None,
                "expression_validator": self._expression_validator is not None,
                "variable_introspection": self._variable_introspection is not None,
                "theme_designer": self._theme_designer is not None,
                "performance_advisor": self._performance_advisor is not None,
                "shader_advisor": self._shader_advisor is not None,
                "build_orchestrator": self._build_orchestrator is not None,
                "recall_engine": self._recall_engine is not None,
                "interaction_designer": self._interaction_designer is not None,
                "physics_tuner": self._physics_tuner is not None,
                "rag_pipeline": self._rag_pipeline is not None,
                "tree_of_thought": self._tree_of_thought is not None,
                "prompt_optimizer": self._prompt_optimizer is not None,
                "skill_composer": self._skill_composer is not None,
                "ui_layout_system": self._ui_layout_system is not None,
                "performance_overlay": self._performance_overlay is not None,
                "developer_assistant": self._developer_assistant is not None,
                "playtest_simulator": self._playtest_simulator is not None,
                "scene_streamer": self._scene_streamer is not None,
                "project_exporter": self._project_exporter is not None,
                "game_director": self._game_director is not None,
                "balance_analyzer": self._balance_analyzer is not None,
                "narrative_composer": self._narrative_composer is not None,
                "player_modeler": self._player_modeler is not None,
                "learning_loop": self._learning_loop is not None,
                "cron_scheduler": self._cron_scheduler is not None,
                "memory_graph": self._memory_graph is not None,
                "context_compressor": self._context_compressor is not None,
                "tool_forge": self._tool_forge is not None,
                "gateway": self._gateway is not None,
                "audio_system": self._audio_system is not None,
                "network_layer": self._network_layer is not None,
                "behavior_runtime": self._behavior_runtime is not None,
                "save_system": self._save_system is not None,
                "session_snapshot": self._session_snapshot is not None,
                "trajectory_compressor": self._trajectory_compressor is not None,
                "skills_hub": self._skills_hub is not None,
                "personality_system": self._personality_system is not None,
                "insights_generator": self._insights_generator is not None,
                "provider_switch": self._provider_switch is not None,
                "chain_of_thought": self._chain_of_thought is not None,
                "conversation_memory": self._conversation_memory is not None,
                "self_optimization": self._self_optimization is not None,
                "collaboration_protocol": self._collaboration_protocol is not None,
                "knowledge_synthesis": self._knowledge_synthesis is not None,
                "capability_registry": self._capability_registry is not None,
                "event_sheet": self._event_sheet is not None,
                "resource_serializer": self._resource_serializer is not None,
                "input_map": self._input_map is not None,
                "animation_tree": self._animation_tree is not None,
                "custom_object_types": self._custom_object_types is not None,
                "tile_map_optimizer": self._tile_map_optimizer is not None,
                "experiment_framework": self._experiment_framework is not None,
                "telemetry_pipeline": self._telemetry_pipeline is not None,
                "audit_trail": self._audit_trail is not None,
                "journal_system": self._journal_system is not None,
                "document_synthesizer": self._document_synthesizer is not None,
                "simulation_runner": self._simulation_runner is not None,
                "agentic_coding": self._agentic_coding is not None,
                "game_reasoner": self._game_reasoner is not None,
                "narrative_branch": self._narrative_branch is not None,
                "concurrency_manager": self._concurrency_manager is not None,
                "verification_pipeline": self._verification_pipeline is not None,
                "playtest_simulator": self._playtest_simulator is not None,
                "skill_synthesizer": self._skill_synthesizer is not None,
                "security_scanner": self._security_scanner is not None,
                "delegation_framework": self._delegation_framework is not None,
                "kanban_coordinator": self._kanban_coordinator is not None,
                "streaming_scrubber": self._streaming_scrubber is not None,
                "trajectory_generator": self._trajectory_generator is not None,
                "developer_oracle": self._developer_oracle is not None,
                "context_weaver": self._context_weaver is not None,
                "session_nexus": self._session_nexus is not None,
                "persona_vault": self._persona_vault is not None,
                "voice_bridge": self._voice_bridge is not None,
                "ecosystem_hub": self._ecosystem_hub is not None,
                "intent_cascade": self._intent_cascade is not None,
                "game_forecaster": self._game_forecaster is not None,
                "asset_synthesizer": self._asset_synthesizer is not None,
                "tutorial_orchestrator": self._tutorial_orchestrator is not None,
                "ab_test_runner": self._ab_test_runner is not None,
                "heatmap_analyzer": self._heatmap_analyzer is not None,
                "bug_forensics": self._bug_forensics is not None,
                "accessibility_auditor": self._accessibility_auditor is not None,
                "federated_learner": self._federated_learner is not None,
                "swarm_planner": self._swarm_planner is not None,
                "world_composer": self._world_composer is not None,
                "playtest_orchestrator": self._playtest_orchestrator is not None,
                "reasoning_chain": self._reasoning_chain is not None,
                "memory_hierarchy": self._memory_hierarchy is not None,
                "tool_registry": self._tool_registry is not None,
                "prompt_library": self._prompt_library is not None,
                "reflection_loop": self._reflection_loop is not None,
            "skill_forge": self._skill_forge is not None,
            "learning_loop": self._learning_loop is not None,
            "memory_consolidator": self._memory_consolidator is not None,
            "delegation_broker": self._delegation_broker is not None,
            "game_design_intelligence": self._game_design_intelligence is not None,
            "interaction_synthesis_engine": self._interaction_synthesis_engine is not None,
            "gameplay_ecosystem": self._gameplay_ecosystem is not None,
            "creative_director": self._creative_director is not None,
            "social_simulation": self._social_simulation is not None,
            "monetization_designer": self._monetization_designer is not None,
            "world_builder": self._world_builder is not None,
            "behavior_designer": self._behavior_designer is not None,
            "quest_composer": self._quest_composer is not None,
            "multi_agent_coordinator": self._multi_agent_coordinator is not None,
            "memory_orchestrator": self._memory_orchestrator is not None,
            "simulation_controller": self._simulation_controller is not None,
            "timeline_manager": self._timeline_manager is not None,
            "skill_generator": self._skill_generator is not None,
            "learning_loop": self._learning_loop is not None,
            "social_dynamics": self._social_dynamics is not None,
            "emergent_narrative": self._emergent_narrative is not None,
            "procedural_world": self._procedural_world is not None,
            "render_pipeline": self._render_pipeline is not None,
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
        if self._insights_engine:
            status["insights_stats"] = self._insights_engine.get_stats()
        if self._state_sync_mesh:
            status["state_sync_stats"] = self._state_sync_mesh.get_stats()
        if self._dev_loop:
            status["dev_loop_stats"] = self._dev_loop.get_stats()
        if self._context_references:
            status["context_references_stats"] = self._context_references.get_stats()
        if self._rendering_server:
            status["rendering_server_stats"] = self._rendering_server.get_stats()
        if self._input_event_system:
            status["input_event_system_stats"] = self._input_event_system.get_stats()
        if self._game_object_registry:
            status["game_object_registry_stats"] = self._game_object_registry.get_stats()
        if self._scene_manager:
            status["scene_manager_stats"] = self._scene_manager.get_stats()
        if self._process_registry:
            status["process_registry_stats"] = self._process_registry.get_stats()
        if self._cron_scheduler:
            status["cron_scheduler_stats"] = self._cron_scheduler.get_stats()
        if self._expression_evaluator:
            status["expression_evaluator_stats"] = self._expression_evaluator.get_stats()
        if self._class_registry:
            status["class_registry_stats"] = self._class_registry.get_stats()
        if self._multi_modal_agent:
            status["multi_modal_stats"] = self._multi_modal_agent.get_stats()
        if self._import_pipeline:
            status["import_pipeline_stats"] = self._import_pipeline.get_stats()
        if self._terrain_system:
            status["terrain_system_stats"] = self._terrain_system.get_stats()
        if self._save_system:
            status["save_system_stats"] = self._save_system.get_stats()
        if self._node_tree:
            status["node_tree_stats"] = self._node_tree.get_stats()
        if self._extension_registry:
            status["extension_registry_stats"] = self._extension_registry.get_stats()
        if self._export_pipeline:
            status["export_pipeline_stats"] = self._export_pipeline.get_stats()
        if self._server_pool:
            status["server_pool_stats"] = self._server_pool.get_stats()
        if self._gizmo_system:
            status["gizmo_system_stats"] = self._gizmo_system.get_stats()
        if self._pivot_system:
            status["pivot_system_stats"] = self._pivot_system.get_stats()
        if self._network_sync:
            status["network_sync_stats"] = self._network_sync.get_stats()
        if self._behavior_tree:
            status["behavior_tree_stats"] = self._behavior_tree.get_stats()
        if self._math_utils:
            status["math_utils_stats"] = self._math_utils.get_stats()
        if self._gui_system:
            status["gui_system_stats"] = self._gui_system.get_stats()
        if self._config_manager:
            status["config_manager_stats"] = self._config_manager.get_stats()
        if self._animation_controller:
            status["animation_controller_stats"] = self._animation_controller.get_stats()
        if self._trajectory_recorder_v2:
            status["trajectory_recorder_v2_stats"] = self._trajectory_recorder_v2.get_stats()
        if self._skill_command_registry:
            status["skill_command_registry_stats"] = self._skill_command_registry.get_stats()
        if self._session_store:
            status["session_store_stats"] = self._session_store.get_stats()
        if self._platform_bridge:
            status["platform_bridge_stats"] = self._platform_bridge.get_stats()
        if self._tool_composer:
            status["tool_composer_stats"] = self._tool_composer.get_stats()
        if self._feedback_loop:
            status["feedback_loop_stats"] = self._feedback_loop.get_stats()
        if self._agent_negotiation:
            status["agent_negotiation_stats"] = self._agent_negotiation.get_stats()
        if self._simulation_env:
            status["simulation_env_stats"] = self._simulation_env.get_stats()
        if self._goal_decomposer:
            status["goal_decomposer_stats"] = self._goal_decomposer.get_stats()
        if self._prompt_template_lib:
            status["prompt_template_lib_stats"] = self._prompt_template_lib.get_stats()
        if self._semantic_memory:
            status["semantic_memory_stats"] = self._semantic_memory.get_stats()
        if self._intent_classifier:
            status["intent_classifier_stats"] = self._intent_classifier.get_stats()
        if self._context_assembler:
            status["context_assembler_stats"] = self._context_assembler.get_stats()
        if self._action_sequencer:
            status["action_sequencer_stats"] = self._action_sequencer.get_stats()
        if self._agent_event_bus:
            status["agent_event_bus_stats"] = self._agent_event_bus.get_stats()
        if self._agent_task_queue:
            status["agent_task_queue_stats"] = self._agent_task_queue.get_stats()
        if self._code_review_engine:
            status["code_review_engine_stats"] = self._code_review_engine.get_stats()
        if self._agent_pipeline_sys:
            status["agent_pipeline_stats"] = self._agent_pipeline_sys.get_stats()
        if self._camera_shake_system:
            status["camera_shake_stats"] = self._camera_shake_system.get_stats()
        if self._difficulty_system:
            status["difficulty_system_stats"] = self._difficulty_system.get_stats()
        if self._fog_of_war:
            status["fog_of_war_stats"] = self._fog_of_war.get_stats()
        if self._game_mode_system:
            status["game_mode_system_stats"] = self._game_mode_system.get_stats()
        if self._agent_consensus:
            status["agent_consensus_stats"] = self._agent_consensus.get_stats()
        if self._game_analyzer:
            status["game_analyzer_stats"] = self._game_analyzer.get_stats()
        if self._adaptive_prompting:
            status["adaptive_prompting_stats"] = self._adaptive_prompting.get_stats()
        if self._entity_extractor:
            status["entity_extractor_stats"] = self._entity_extractor.get_stats()
        if self._style_transfer:
            status["style_transfer_stats"] = self._style_transfer.get_stats()
        if self._curriculum_learning:
            status["curriculum_learning_stats"] = self._curriculum_learning.get_stats()
        if self._game_balancer:
            status["game_balancer_stats"] = self._game_balancer.get_stats()
        if self._localization_engine:
            status["localization_engine_stats"] = self._localization_engine.get_stats()
        if self._tutorial_designer:
            status["tutorial_designer_stats"] = self._tutorial_designer.get_stats()
        if self._game_tester:
            status["game_tester_stats"] = self._game_tester.get_stats()
        if self._memory_consolidation:
            status["memory_consolidation_stats"] = self._memory_consolidation.get_stats()
        if self._conflict_resolver:
            status["conflict_resolution_stats"] = self._conflict_resolver.get_stats()
        if self._risk_assessor:
            status["risk_assessment_stats"] = self._risk_assessor.get_stats()
        if self._documentation_generator:
            status["documentation_stats"] = self._documentation_generator.get_stats()
        if self._asset_optimizer:
            status["asset_optimizer_stats"] = self._asset_optimizer.get_stats()
        if self._cross_platform_engine:
            status["cross_platform_stats"] = self._cross_platform_engine.get_stats()
        if self._player_analytics:
            status["player_analytics_stats"] = self._player_analytics.get_stats()
        if self._adaptive_difficulty:
            status["adaptive_difficulty_stats"] = self._adaptive_difficulty.get_stats()
        if self._content_moderation:
            status["content_moderation_stats"] = self._content_moderation.get_stats()
        if self._game_settings:
            status["game_settings_stats"] = self._game_settings.get_stats()
        if self._game_progression:
            status["game_progression_stats"] = self._game_progression.get_stats()
        if self._narrative_graph:
            status["narrative_graph_stats"] = self._narrative_graph.get_stats()
        if self._asset_harmonizer:
            status["asset_harmonizer_stats"] = self._asset_harmonizer.get_stats()
        if self._agentic_memory:
            status["agentic_memory_stats"] = self._agentic_memory.get_stats()
        if self._multi_agent_orchestrator:
            status["orchestrator_stats"] = self._multi_agent_orchestrator.get_stats()
        if self._realtime_collaboration:
            status["collaboration_stats"] = self._realtime_collaboration.get_stats()
        if self._goal_decomposer:
            status["goal_decomposer_stats"] = self._goal_decomposer.get_stats()
        if self._skill_autonomy:
            status["skill_autonomy_stats"] = self._skill_autonomy.get_stats()
        if self._expression_validator:
            status["expression_validator_stats"] = self._expression_validator.get_stats()
        if self._variable_introspection:
            status["variable_introspection_stats"] = self._variable_introspection.get_stats()
        if self._theme_designer:
            status["theme_designer_stats"] = self._theme_designer.get_stats()
        if self._performance_advisor:
            status["performance_advisor_stats"] = self._performance_advisor.get_stats()
        if self._shader_advisor:
            status["shader_advisor_stats"] = self._shader_advisor.get_stats()
        if self._build_orchestrator:
            status["build_orchestrator_stats"] = self._build_orchestrator.get_stats()
        if self._recall_engine:
            status["recall_engine_stats"] = self._recall_engine.get_stats()
        if self._interaction_designer:
            status["interaction_designer_stats"] = self._interaction_designer.get_stats()
        if self._physics_tuner:
            status["physics_tuner_stats"] = self._physics_tuner.get_stats()
        if self._rag_pipeline:
            status["rag_pipeline_stats"] = self._rag_pipeline.get_stats()
        if self._tree_of_thought:
            status["tree_of_thought_stats"] = self._tree_of_thought.get_stats()
        if self._prompt_optimizer:
            status["prompt_optimizer_stats"] = self._prompt_optimizer.get_stats()
        if self._skill_composer:
            status["skill_composer_stats"] = self._skill_composer.get_stats()
        if self._ui_layout_system:
            status["ui_layout_system_stats"] = self._ui_layout_system.get_stats()
        if self._performance_overlay:
            status["performance_overlay_stats"] = self._performance_overlay.get_stats()
        if self._developer_assistant:
            status["developer_assistant_stats"] = self._developer_assistant.get_stats()
        if self._playtest_simulator:
            status["playtest_simulator_stats"] = self._playtest_simulator.get_stats()
        if self._scene_streamer:
            status["scene_streamer_stats"] = self._scene_streamer.get_stats()
        if self._project_exporter:
            status["project_exporter_stats"] = self._project_exporter.get_stats()
        if self._game_director:
            status["game_director_stats"] = self._game_director.get_stats()
        if self._balance_analyzer:
            status["balance_analyzer_stats"] = self._balance_analyzer.get_stats()
        if self._narrative_composer:
            status["narrative_composer_stats"] = self._narrative_composer.get_stats()
        if self._player_modeler:
            status["player_modeler_stats"] = self._player_modeler.get_stats()
        if self._learning_loop:
            status["learning_loop_stats"] = self._learning_loop.get_stats()
        if self._cron_scheduler:
            status["cron_scheduler_stats"] = self._cron_scheduler.get_stats()
        if self._memory_graph:
            status["memory_graph_stats"] = self._memory_graph.get_stats()
        if self._context_compressor:
            status["context_compressor_stats"] = self._context_compressor.get_stats()
        if self._tool_forge:
            status["tool_forge_stats"] = self._tool_forge.get_stats()
        if self._gateway:
            status["gateway_stats"] = self._gateway.get_stats()
        if self._audio_system:
            status["audio_system_stats"] = self._audio_system.get_stats()
        if self._network_layer:
            status["network_layer_stats"] = self._network_layer.get_stats()
        if self._behavior_runtime:
            status["behavior_runtime_stats"] = self._behavior_runtime.get_stats()
        if self._save_system:
            status["save_system_stats"] = self._save_system.get_stats()
        if self._session_snapshot:
            status["session_snapshot_stats"] = self._session_snapshot.get_stats()
        if self._trajectory_compressor:
            status["trajectory_compressor_stats"] = self._trajectory_compressor.get_stats()
        if self._skills_hub:
            status["skills_hub_stats"] = self._skills_hub.get_stats()
        if self._personality_system:
            status["personality_system_stats"] = self._personality_system.get_stats()
        if self._insights_generator:
            status["insights_generator_stats"] = self._insights_generator.get_stats()
        if self._provider_switch:
            status["provider_switch_stats"] = self._provider_switch.get_stats()
        if self._chain_of_thought:
            status["chain_of_thought_stats"] = self._chain_of_thought.get_stats()
        if self._conversation_memory:
            status["conversation_memory_stats"] = self._conversation_memory.get_stats()
        if self._self_optimization:
            status["self_optimization_stats"] = self._self_optimization.get_stats()
        if self._collaboration_protocol:
            status["collaboration_protocol_stats"] = self._collaboration_protocol.get_stats()
        if self._knowledge_synthesis:
            status["knowledge_synthesis_stats"] = self._knowledge_synthesis.get_stats()
        if self._capability_registry:
            status["capability_registry_stats"] = self._capability_registry.get_stats()
        if self._event_sheet:
            status["event_sheet_stats"] = self._event_sheet.get_stats()
        if self._resource_serializer:
            status["resource_serializer_stats"] = self._resource_serializer.get_stats()
        if self._input_map:
            status["input_map_stats"] = self._input_map.get_stats()
        if self._animation_tree:
            status["animation_tree_stats"] = self._animation_tree.get_stats()
        if self._custom_object_types:
            status["custom_object_types_stats"] = self._custom_object_types.get_stats()
        if self._tile_map_optimizer:
            status["tile_map_optimizer_stats"] = self._tile_map_optimizer.get_stats()
        if self._experiment_framework:
            status["experiment_framework_stats"] = self._experiment_framework.get_stats()
        if self._telemetry_pipeline:
            status["telemetry_pipeline_stats"] = self._telemetry_pipeline.get_stats()
        if self._audit_trail:
            status["audit_trail_stats"] = self._audit_trail.get_stats()
        if self._journal_system:
            status["journal_system_stats"] = self._journal_system.get_stats()
        if self._document_synthesizer:
            status["document_synthesizer_stats"] = self._document_synthesizer.get_stats()
        if self._simulation_runner:
            status["simulation_runner_stats"] = self._simulation_runner.get_stats()
        if self._agentic_coding:
            status["agentic_coding_stats"] = self._agentic_coding.get_stats()
        if self._game_reasoner:
            status["game_reasoner_stats"] = self._game_reasoner.get_stats()
        if self._narrative_branch:
            status["narrative_branch_stats"] = self._narrative_branch.get_stats()
        if self._concurrency_manager:
            status["concurrency_manager_stats"] = self._concurrency_manager.get_stats()
        if self._verification_pipeline:
            status["verification_pipeline_stats"] = self._verification_pipeline.get_stats()
        if self._playtest_simulator:
            status["playtest_simulator_stats"] = self._playtest_simulator.get_stats()
        if self._skill_synthesizer:
            status["skill_synthesizer_stats"] = self._skill_synthesizer.get_stats()
        if self._security_scanner:
            status["security_scanner_stats"] = self._security_scanner.get_stats()
        if self._delegation_framework:
            status["delegation_framework_stats"] = self._delegation_framework.get_stats()
        if self._kanban_coordinator:
            status["kanban_coordinator_stats"] = self._kanban_coordinator.get_stats()
        if self._streaming_scrubber:
            status["streaming_scrubber_stats"] = self._streaming_scrubber.get_stats()
        if self._trajectory_generator:
            status["trajectory_generator_stats"] = self._trajectory_generator.get_stats()
        if self._developer_oracle:
            status["developer_oracle_stats"] = self._developer_oracle.get_stats()
        if self._context_weaver:
            status["context_weaver_stats"] = self._context_weaver.get_stats()
        if self._session_nexus:
            status["session_nexus_stats"] = self._session_nexus.get_stats()
        if self._persona_vault:
            status["persona_vault_stats"] = self._persona_vault.get_stats()
        if self._voice_bridge:
            status["voice_bridge_stats"] = self._voice_bridge.get_stats()
        if self._ecosystem_hub:
            status["ecosystem_hub_stats"] = self._ecosystem_hub.get_stats()
        if self._intent_cascade:
            status["intent_cascade_stats"] = self._intent_cascade.get_stats()
        if self._game_forecaster:
            status["game_forecaster_stats"] = self._game_forecaster.get_stats()
        if self._asset_synthesizer:
            status["asset_synthesizer_stats"] = self._asset_synthesizer.get_stats()
        if self._tutorial_orchestrator:
            status["tutorial_orchestrator_stats"] = self._tutorial_orchestrator.get_stats()
        if self._ab_test_runner:
            status["ab_test_runner_stats"] = self._ab_test_runner.get_stats()
        if self._heatmap_analyzer:
            status["heatmap_analyzer_stats"] = self._heatmap_analyzer.get_stats()
        if self._bug_forensics:
            status["bug_forensics_stats"] = self._bug_forensics.get_stats()
        if self._accessibility_auditor:
            status["accessibility_auditor_stats"] = self._accessibility_auditor.get_stats()
        if self._federated_learner:
            status["federated_learner_stats"] = self._federated_learner.get_stats()
        if self._swarm_planner:
            status["swarm_planner_stats"] = self._swarm_planner.get_stats()
        if self._world_composer:
            status["world_composer_stats"] = self._world_composer.get_stats()
        if self._playtest_orchestrator:
            status["playtest_orchestrator_stats"] = self._playtest_orchestrator.get_stats()
        if self._reasoning_chain:
            status["reasoning_chain_stats"] = self._reasoning_chain.get_stats()
        if self._memory_hierarchy:
            status["memory_hierarchy_stats"] = self._memory_hierarchy.get_stats()
        if self._tool_registry:
            status["tool_registry_stats"] = self._tool_registry.get_stats()
        if self._prompt_library:
            status["prompt_library_stats"] = self._prompt_library.get_stats()
        if self._reflection_loop:
            status["reflection_loop_stats"] = self._reflection_loop.get_stats()
        if self._skill_forge:
            status["skill_forge_stats"] = self._skill_forge.get_stats()
        if self._learning_loop:
            status["learning_loop_stats"] = self._learning_loop.get_stats()
        if self._memory_consolidator:
            status["memory_consolidator_stats"] = self._memory_consolidator.get_stats()
        if self._delegation_broker:
            status["delegation_broker_stats"] = self._delegation_broker.get_stats()
        if self._game_design_intelligence:
            status["game_design_intelligence_stats"] = self._game_design_intelligence.get_stats()
        if self._interaction_synthesis_engine:
            status["interaction_synthesis_engine_stats"] = self._interaction_synthesis_engine.get_stats()
        if self._gameplay_ecosystem:
            status["gameplay_ecosystem_stats"] = self._gameplay_ecosystem.get_stats()
        if self._creative_director:
            status["creative_director_stats"] = self._creative_director.get_stats()
        if self._social_simulation:
            status["social_simulation_stats"] = self._social_simulation.get_stats()
        if self._monetization_designer:
            status["monetization_designer_stats"] = self._monetization_designer.get_stats()
        if self._world_builder:
            status["world_builder_stats"] = self._world_builder.get_stats()
        if self._behavior_designer:
            status["behavior_designer_stats"] = self._behavior_designer.get_stats()
        if self._quest_composer:
            status["quest_composer_stats"] = self._quest_composer.get_stats()
        if self._multi_agent_coordinator:
            status["multi_agent_coordinator_stats"] = self._multi_agent_coordinator.get_stats()
        if self._memory_orchestrator:
            status["memory_orchestrator_stats"] = self._memory_orchestrator.get_stats()
        if self._simulation_controller:
            status["simulation_controller_stats"] = self._simulation_controller.get_stats()
        if self._timeline_manager:
            status["timeline_manager_stats"] = self._timeline_manager.get_stats()
        if self._skill_generator:
            status["skill_generator_stats"] = self._skill_generator.get_stats()
        if self._learning_loop:
            status["learning_loop_stats"] = self._learning_loop.get_stats()
        if self._social_dynamics:
            status["social_dynamics_stats"] = self._social_dynamics.get_stats()
        if self._emergent_narrative:
            status["emergent_narrative_stats"] = self._emergent_narrative.get_stats()
        if self._procedural_world:
            status["procedural_world_stats"] = self._procedural_world.get_stats()
        if self._render_pipeline:
            status["render_pipeline_stats"] = self._render_pipeline.get_stats()
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
