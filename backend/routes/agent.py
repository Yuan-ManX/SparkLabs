"""
SparkLabs Backend - Agent Routes

API endpoints for agent creation, management, skills,
studio hierarchy, and toolset operations.
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

router = APIRouter()

_orchestrator = AgentOrchestrator()

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
