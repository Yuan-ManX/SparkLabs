"""
SparkLabs Backend - Chrono-Perception Forge Routes

REST endpoints for the Agent Chrono-Perception Forge.
"""
from fastapi import APIRouter
from pydantic import BaseModel
from typing import Any, Dict, List, Optional

router = APIRouter()


# =============================================================================
# Request Models
# =============================================================================

class RegisterAgentRequest(BaseModel):
    agent_id: str
    distortion_sensitivity: float = 0.5
    recovery_rate: float = 0.3
    baseline_rate: float = 1.0


class ExperienceMomentRequest(BaseModel):
    episode_id: str
    context: str = "routine"        # combat/pursuit/social/exploration/routine/waiting/grief/joy/meditation/crisis/revelation/trance
    objective_duration: float = 1.0
    intensity: float = 0.5
    focus: float = 0.5
    novelty: float = 0.5
    label: str = ""


class SynchronizeGroupRequest(BaseModel):
    group_id: str
    member_ids: List[str]
    trigger_event: str = ""


class SimulateRequest(BaseModel):
    cycles: int = 5


# =============================================================================
# Routes
# =============================================================================

@router.post("/chrono-perception/agents")
async def forge_register_agent(req: RegisterAgentRequest):
    from sparkai.agent.agent_chrono_perception_forge import (
        AgentChronoPerceptionForge,
    )
    forge = AgentChronoPerceptionForge.get_instance()
    result = forge.register_agent(
        agent_id=req.agent_id,
        distortion_sensitivity=req.distortion_sensitivity,
        recovery_rate=req.recovery_rate,
        baseline_rate=req.baseline_rate,
    )
    if "error" in result:
        return {"status": "error", "detail": result["error"]}
    return {"status": "ok", "data": result}


@router.delete("/chrono-perception/agents/{agent_id}")
async def forge_remove_agent(agent_id: str):
    from sparkai.agent.agent_chrono_perception_forge import (
        AgentChronoPerceptionForge,
    )
    forge = AgentChronoPerceptionForge.get_instance()
    result = forge.remove_agent(agent_id)
    if "error" in result:
        return {"status": "error", "detail": result["error"]}
    return {"status": "ok", "data": result}


@router.post("/chrono-perception/agents/{agent_id}/moments")
async def forge_experience_moment(agent_id: str, req: ExperienceMomentRequest):
    from sparkai.agent.agent_chrono_perception_forge import (
        AgentChronoPerceptionForge, TemporalContext,
    )
    forge = AgentChronoPerceptionForge.get_instance()
    try:
        context = TemporalContext(req.context)
    except ValueError:
        return {"status": "error", "detail": f"Invalid context: {req.context}"}
    result = forge.experience_moment(
        agent_id=agent_id,
        episode_id=req.episode_id,
        context=context,
        objective_duration=req.objective_duration,
        intensity=req.intensity,
        focus=req.focus,
        novelty=req.novelty,
        label=req.label,
    )
    if "error" in result:
        return {"status": "error", "detail": result["error"]}
    return {"status": "ok", "data": result}


@router.post("/chrono-perception/synchronize")
async def forge_synchronize_group(req: SynchronizeGroupRequest):
    from sparkai.agent.agent_chrono_perception_forge import (
        AgentChronoPerceptionForge,
    )
    forge = AgentChronoPerceptionForge.get_instance()
    result = forge.synchronize_group(
        group_id=req.group_id,
        member_ids=req.member_ids,
        trigger_event=req.trigger_event,
    )
    if "error" in result:
        return {"status": "error", "detail": result["error"]}
    return {"status": "ok", "data": result}


@router.get("/chrono-perception/agents/{agent_id}")
async def forge_get_agent_state(agent_id: str):
    from sparkai.agent.agent_chrono_perception_forge import (
        AgentChronoPerceptionForge,
    )
    forge = AgentChronoPerceptionForge.get_instance()
    result = forge.get_agent_state(agent_id)
    if "error" in result:
        return {"status": "error", "detail": result["error"]}
    return {"status": "ok", "data": result}


@router.get("/chrono-perception/agents/{agent_id}/episodes/{episode_id}")
async def forge_get_episode(agent_id: str, episode_id: str):
    from sparkai.agent.agent_chrono_perception_forge import (
        AgentChronoPerceptionForge,
    )
    forge = AgentChronoPerceptionForge.get_instance()
    result = forge.get_episode(agent_id, episode_id)
    if "error" in result:
        return {"status": "error", "detail": result["error"]}
    return {"status": "ok", "data": result}


@router.get("/chrono-perception/sync-groups")
async def forge_get_sync_groups():
    from sparkai.agent.agent_chrono_perception_forge import (
        AgentChronoPerceptionForge,
    )
    forge = AgentChronoPerceptionForge.get_instance()
    return {"status": "ok", "data": forge.get_sync_groups()}


@router.get("/chrono-perception/events")
async def forge_get_events(limit: int = 50):
    from sparkai.agent.agent_chrono_perception_forge import (
        AgentChronoPerceptionForge,
    )
    forge = AgentChronoPerceptionForge.get_instance()
    return {"status": "ok", "data": forge.get_events_log(limit=limit)}


@router.get("/chrono-perception/status")
async def forge_get_status():
    from sparkai.agent.agent_chrono_perception_forge import (
        AgentChronoPerceptionForge,
    )
    forge = AgentChronoPerceptionForge.get_instance()
    return {"status": "ok", "data": forge.get_status()}


@router.post("/chrono-perception/cycle")
async def forge_cycle():
    from sparkai.agent.agent_chrono_perception_forge import (
        AgentChronoPerceptionForge,
    )
    forge = AgentChronoPerceptionForge.get_instance()
    return {"status": "ok", "data": forge.cycle()}


@router.post("/chrono-perception/simulate")
async def forge_simulate(req: SimulateRequest):
    from sparkai.agent.agent_chrono_perception_forge import (
        AgentChronoPerceptionForge,
    )
    forge = AgentChronoPerceptionForge.get_instance()
    return {"status": "ok", "data": forge.simulate(cycles=req.cycles)}


@router.post("/chrono-perception/reset")
async def forge_reset():
    from sparkai.agent.agent_chrono_perception_forge import (
        AgentChronoPerceptionForge,
    )
    forge = AgentChronoPerceptionForge.get_instance()
    return {"status": "ok", "data": forge.reset()}
