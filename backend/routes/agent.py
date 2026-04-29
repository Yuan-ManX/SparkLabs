"""
SparkLabs Backend - Agent Routes

API endpoints for agent creation, management, skills,
studio hierarchy, toolsets, hooks, rules, teams,
bench evaluation, and session management.
"""

from fastapi import APIRouter
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
@router.get("/asset-stats")
async def asset_stats_early():
    return _asset_engine.get_stats()

@router.get("/asset-collections")
async def asset_collections_early():
    return {"collections": _asset_engine.list_collections()}

@router.post("/asset-collections")
async def asset_create_collection_early(name: str = "", description: str = "", tags: Optional[str] = None):
    tag_list = tags.split(",") if tags else []
    collection = _asset_engine.create_collection(name, description, [], tag_list)
    return collection.to_dict()

@router.get("/asset-pipelines")
async def asset_pipelines_early():
    return {"pipelines": _asset_engine.list_pipelines()}

@router.post("/asset-pipelines")
async def asset_create_pipeline_early(name: str = "", description: str = ""):
    pipeline = _asset_engine.create_pipeline(name, description)
    return pipeline.to_dict()

@router.get("/dialogue/stats")
async def dialogue_stats_early():
    return _dialogue_engine.get_stats()

@router.get("/dialogue/arcs")
async def dialogue_arcs_early(status: Optional[str] = None):
    st = ArcStatus(status) if status else None
    return {"arcs": _dialogue_engine.list_arcs(st)}

@router.get("/validator/stats")
async def validator_stats_early():
    return _validator_engine.get_stats()

@router.get("/validator/rules")
async def validator_rules_early(category: Optional[str] = None, enabled_only: bool = False):
    cat = ValidationCategory(category) if category else None
    return {"rules": _validator_engine.list_rules(cat, enabled_only)}

@router.get("/validator/rulesets")
async def validator_rulesets_early():
    return {"rulesets": _validator_engine.list_rule_sets()}

@router.get("/validator/reports")
async def validator_reports_early(limit: int = 20):
    return {"reports": _validator_engine.get_reports(limit)}

@router.get("/orchestrator-engine/stats")
async def orchestrator_engine_stats_early():
    return _orchestrator_engine.get_stats()

@router.get("/orchestrator-engine/agents")
async def orchestrator_engine_agents_early(role: Optional[str] = None, capability: Optional[str] = None):
    role_enum = OrchAgentRole(role) if role else None
    cap_enum = OrchAgentCapability(capability) if capability else None
    return {"agents": _orchestrator_engine.list_agents(role_enum, cap_enum)}

@router.get("/orchestrator-engine/tasks")
async def orchestrator_engine_tasks_early(status: Optional[str] = None, priority: Optional[str] = None):
    status_enum = TaskStatus(status) if status else None
    return {"tasks": _orchestrator_engine.list_tasks(status_enum)}

@router.get("/orchestrator-engine/workflows")
async def orchestrator_engine_workflows_early(state: Optional[str] = None):
    state_enum = WorkflowState(state) if state else None
    return {"workflows": _orchestrator_engine.list_workflows(state_enum)}

@router.get("/skill-evolution/stats")
async def skill_evolution_stats_early():
    return _skill_evolution_engine.get_stats()

@router.get("/skill-evolution/skills")
async def skill_evolution_skills_early(domain: Optional[str] = None, maturity: Optional[str] = None):
    domain_enum = SkillDomain(domain) if domain else None
    maturity_enum = EvolSkillMaturity(maturity) if maturity else None
    return {"skills": _skill_evolution_engine.list_skills(domain_enum, maturity_enum)}

@router.get("/skill-evolution/protocols")
async def skill_evolution_protocols_early(status: Optional[str] = None):
    status_enum = EvolFixStatus(status) if status else None
    return {"protocols": _skill_evolution_engine.list_protocols(status_enum)}

@router.get("/skill-evolution/evolution-history")
async def skill_evolution_evolution_history_early(skill_id: Optional[str] = None, limit: int = 20):
    return {"history": _skill_evolution_engine.get_evolution_history(skill_id, limit)}

@router.get("/skill-evolution/execution-history")
async def skill_evolution_execution_history_early(skill_id: Optional[str] = None, limit: int = 20):
    return {"history": _skill_evolution_engine.get_execution_history(skill_id, limit)}

@router.get("/evaluator/stats")
async def evaluator_stats_early():
    return _evaluator_engine.get_stats()

@router.get("/evaluator/reports")
async def evaluator_reports_early(game_id: Optional[str] = None, limit: int = 20):
    return {"reports": _evaluator_engine.list_reports(game_id, limit)}

@router.get("/evaluator/benchmarks")
async def evaluator_benchmarks_early(dimension: Optional[str] = None):
    dim_enum = EvalDimension(dimension) if dimension else None
    return {"benchmarks": _evaluator_engine.list_benchmarks(dim_enum)}


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
