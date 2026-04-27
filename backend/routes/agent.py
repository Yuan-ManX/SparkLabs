"""
SparkLabs Backend - Agent Routes
"""

from fastapi import APIRouter
from pydantic import BaseModel
from typing import List, Optional

from sparkai.agent.base import SparkAgent, AgentCapability
from sparkai.agent.orchestrator import AgentOrchestrator
from sparkai.agent.llm import LLMProvider, LLMConfig
from sparkai.agent.toolkit import create_engine_tools

router = APIRouter()

_orchestrator = AgentOrchestrator()


class AgentCreateRequest(BaseModel):
    name: str
    role: str = "general"
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


@router.post("/create")
async def create_agent(request: AgentCreateRequest):
    caps = []
    for cap_str in request.capabilities:
        try:
            caps.append(AgentCapability(cap_str))
        except ValueError:
            caps.append(AgentCapability.REASONING)

    agent = SparkAgent(
        name=request.name,
        role=request.role,
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

    for tool in create_engine_tools():
        agent.register_tool(tool)

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


@router.get("/orchestrator/status")
async def orchestrator_status():
    return _orchestrator.get_status()


@router.delete("/{agent_id}")
async def delete_agent(agent_id: str):
    success = _orchestrator.unregister_agent(agent_id)
    return {"success": success}
