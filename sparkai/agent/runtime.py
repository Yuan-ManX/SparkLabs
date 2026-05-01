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
    all 55 subsystems. It provides a single entry point for all engine
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
            self._integration.connect_all()

            self._recovery_engine.register_action_handler("compact_session", lambda params: self._compression_engine and self._compression_engine.compress(params.get("session_id", "default"), params.get("max_tokens", 4000)) is not None)
            self._recovery_engine.register_action_handler("compress_context", lambda params: self._compression_engine and self._compression_engine.compress(params.get("session_id", "default"), params.get("max_tokens", 4000)) is not None)

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
                    "subsystems": 63,
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
