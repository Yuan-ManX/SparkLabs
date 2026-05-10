"""
SparkLabs Backend - Agent Routes

API endpoints for agent creation, management, skills,
studio hierarchy, toolsets, hooks, rules, teams,
bench evaluation, and session management.
"""

from fastapi import APIRouter, Query
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
from sparkai.agent.agent_cron_scheduler import CronScheduler, ScheduleType, JobState, get_cron_scheduler
from sparkai.agent.agent_expression_evaluator import ExpressionEvaluator, ExpressionError, get_expression_evaluator
from sparkai.agent.agent_class_registry import ClassRegistry, DataType, TypeDescriptor, get_class_registry
from sparkai.agent.agent_multi_modal import MultiModalAgent, AnalysisDomain, get_multi_modal_agent
from sparkai.agent.agent_import_pipeline import ImportPipeline, AssetCategory as ImportAssetCategory, ImportStatus, get_import_pipeline
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

from sparkai.engine.audio_system import AudioSystem, get_audio_system, AudioChannel

_audio_system = get_audio_system()


@router.get("/audio/stats")
async def audio_stats():
    return _audio_system.get_stats()


@router.post("/audio/play/{source_id}")
async def audio_play(source_id: str):
    return {"success": _audio_system.play(source_id)}


@router.post("/audio/stop/{source_id}")
async def audio_stop(source_id: str):
    return {"success": _audio_system.stop(source_id)}


@router.post("/audio/stop-all")
async def audio_stop_all(channel: Optional[str] = None):
    ch = AudioChannel(channel) if channel else None
    return {"stopped": _audio_system.stop_all(ch)}


@router.post("/audio/volume/{channel}")
async def audio_set_volume(channel: str, volume: float = 1.0):
    ch = AudioChannel(channel)
    _audio_system.set_channel_volume(ch, volume)
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

@router.get("/cron-scheduler/stats")
async def cron_scheduler_stats():
    return _cron_scheduler.get_stats()


@router.post("/cron-scheduler/schedule-interval")
async def cron_scheduler_schedule_interval(name: str, seconds: int):
    def job():
        return f"Cron job '{name}' executed"
    job_obj = _cron_scheduler.schedule_interval(name, seconds, job)
    return {"job_id": job_obj.job_id, "name": job_obj.name, "next_run_at": job_obj.next_run_at}


@router.get("/cron-scheduler/jobs")
async def cron_scheduler_jobs():
    return {"jobs": [
        {"job_id": j.job_id, "name": j.name, "state": j.state.value}
        for j in _cron_scheduler._jobs.values()
    ]}


@router.post("/cron-scheduler/cancel")
async def cron_scheduler_cancel(job_id: str):
    return {"cancelled": _cron_scheduler.cancel(job_id)}


@router.post("/cron-scheduler/start")
async def cron_scheduler_start():
    _cron_scheduler.start()
    return {"running": True}


@router.post("/cron-scheduler/stop")
async def cron_scheduler_stop():
    _cron_scheduler.stop()
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
    slot = _save_system.save(slot_id, state, scene_name=scene_name, playtime_seconds=playtime_seconds)
    if slot:
        return slot.to_dict()
    return {"error": "Save failed"}


@router.get("/save-system/load/{slot_id}")
async def save_system_load(slot_id: int):
    state = _save_system.load(slot_id)
    if state:
        return {"state": state}
    return {"error": "Load failed"}


@router.delete("/save-system/slot/{slot_id}")
async def save_system_delete(slot_id: int):
    return {"deleted": _save_system.delete(slot_id)}


@router.get("/save-system/slots")
async def save_system_slots():
    return {"slots": [s.to_dict() for s in _save_system.list_slots()]}


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
# Reasoning Chain Endpoints
# ============================================================

from sparkai.agent.agent_reasoning_chain import ReasoningChain, ReasoningTrace, ReasoningPhase, DecisionConfidence, get_reasoning_chain

_reasoning_chain = get_reasoning_chain()


@router.get("/reasoning/stats")
async def reasoning_stats():
    return _reasoning_chain.get_stats()


@router.post("/reasoning/begin")
async def reasoning_begin(goal: str):
    trace = _reasoning_chain.begin(goal)
    return trace.to_dict()


@router.get("/reasoning/active")
async def reasoning_active():
    active = _reasoning_chain.active
    if active:
        return active.to_full_dict()
    return {"active": False}


@router.post("/reasoning/think")
async def reasoning_think(thought: str, phase: str = "analyze"):
    p = ReasoningPhase(phase) if phase in [ph.value for ph in ReasoningPhase] else ReasoningPhase.ANALYZE
    step = _reasoning_chain.think(thought, p)
    return step.to_dict() if step else {"error": "No active trace"}


@router.post("/reasoning/decide")
async def reasoning_decide(question: str, chosen: str, rationale: str, alternatives: str = "", confidence: str = "medium"):
    alts = [a.strip() for a in alternatives.split(",")] if alternatives else []
    conf = DecisionConfidence(confidence) if confidence in [c.value for c in DecisionConfidence] else DecisionConfidence.MEDIUM
    decision = _reasoning_chain.decide(question, chosen, rationale, alts, conf)
    return decision.to_dict() if decision else {"error": "No active trace"}


@router.post("/reasoning/finish")
async def reasoning_finish(outcome: str = "", success: bool = True):
    trace = _reasoning_chain.finish(outcome, success)
    return trace.to_dict() if trace else {"error": "No active trace"}


@router.get("/reasoning/history")
async def reasoning_history(limit: int = 10):
    return {"traces": [t.to_dict() for t in _reasoning_chain.get_history(limit)]}


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

from sparkai.agent.agent_goal_decomposer import GoalDecomposer, GoalTree, GoalLevel, GoalStatus, get_goal_decomposer

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
        st = GoalStatus(status)
    except ValueError:
        st = GoalStatus.COMPLETED
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
