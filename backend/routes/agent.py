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

router = APIRouter()

_orchestrator = AgentOrchestrator()
_hook_manager = HookManager()
_rule_engine = RuleEngine()
_team_orchestrator = TeamOrchestrator(_orchestrator)
_game_bench = GameBench()
_session_manager = SessionManager()

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
