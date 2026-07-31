"""
SparkLabs Backend - Narrative Momentum Governor Routes

REST endpoints for the Agent Narrative Momentum Governor.
"""
from fastapi import APIRouter
from pydantic import BaseModel
from typing import Any, Dict, List, Optional

router = APIRouter()


# =============================================================================
# Request Models
# =============================================================================

class RegisterStoryRequest(BaseModel):
    story_id: str
    target: str = "climax"                  # climax/cooldown/exploration/convergence


class SetTargetRequest(BaseModel):
    story_id: str
    target: str                             # climax/cooldown/exploration/convergence


class LogBeatRequest(BaseModel):
    story_id: str
    beat_id: str
    tension_delta: float                    # signed: positive=rising, negative=falling
    weight: float = 0.5                     # 0.0-1.0


class SimulateRequest(BaseModel):
    cycles: int = 5


# =============================================================================
# Routes
# =============================================================================

@router.post("/narrative-momentum/stories")
async def momentum_register_story(req: RegisterStoryRequest):
    from sparkai.agent.agent_narrative_momentum_governor import (
        AgentNarrativeMomentumGovernor, GovernorTarget,
    )
    gov = AgentNarrativeMomentumGovernor.get_instance()
    try:
        target = GovernorTarget(req.target)
    except ValueError:
        return {"status": "error", "detail": f"Invalid target: {req.target}"}
    result = gov.register_story(story_id=req.story_id, target=target)
    if "error" in result:
        return {"status": "error", "detail": result["error"]}
    return {"status": "ok", "data": result}


@router.post("/narrative-momentum/targets")
async def momentum_set_target(req: SetTargetRequest):
    from sparkai.agent.agent_narrative_momentum_governor import (
        AgentNarrativeMomentumGovernor, GovernorTarget,
    )
    gov = AgentNarrativeMomentumGovernor.get_instance()
    try:
        target = GovernorTarget(req.target)
    except ValueError:
        return {"status": "error", "detail": f"Invalid target: {req.target}"}
    result = gov.set_target(story_id=req.story_id, target=target)
    if "error" in result:
        return {"status": "error", "detail": result["error"]}
    return {"status": "ok", "data": result}


@router.post("/narrative-momentum/beats")
async def momentum_log_beat(req: LogBeatRequest):
    from sparkai.agent.agent_narrative_momentum_governor import (
        AgentNarrativeMomentumGovernor,
    )
    gov = AgentNarrativeMomentumGovernor.get_instance()
    result = gov.log_beat(
        story_id=req.story_id,
        beat_id=req.beat_id,
        tension_delta=req.tension_delta,
        weight=req.weight,
    )
    if "error" in result:
        return {"status": "error", "detail": result["error"]}
    return {"status": "ok", "data": result}


@router.get("/narrative-momentum/stories/{story_id}")
async def momentum_get_story_state(story_id: str):
    from sparkai.agent.agent_narrative_momentum_governor import (
        AgentNarrativeMomentumGovernor,
    )
    gov = AgentNarrativeMomentumGovernor.get_instance()
    result = gov.get_story_state(story_id)
    if "error" in result:
        return {"status": "error", "detail": result["error"]}
    return {"status": "ok", "data": result}


@router.get("/narrative-momentum/stories/{story_id}/beats")
async def momentum_get_beats(story_id: str, limit: int = 20):
    from sparkai.agent.agent_narrative_momentum_governor import (
        AgentNarrativeMomentumGovernor,
    )
    gov = AgentNarrativeMomentumGovernor.get_instance()
    result = gov.get_beats(story_id, limit=limit)
    if "error" in result:
        return {"status": "error", "detail": result["error"]}
    return {"status": "ok", "data": result}


@router.get("/narrative-momentum/stories/{story_id}/decisions")
async def momentum_get_decisions(story_id: str, limit: int = 20):
    from sparkai.agent.agent_narrative_momentum_governor import (
        AgentNarrativeMomentumGovernor,
    )
    gov = AgentNarrativeMomentumGovernor.get_instance()
    result = gov.get_decisions(story_id, limit=limit)
    if "error" in result:
        return {"status": "error", "detail": result["error"]}
    return {"status": "ok", "data": result}


@router.get("/narrative-momentum/events")
async def momentum_get_events(limit: int = 50):
    from sparkai.agent.agent_narrative_momentum_governor import (
        AgentNarrativeMomentumGovernor,
    )
    gov = AgentNarrativeMomentumGovernor.get_instance()
    return {"status": "ok", "data": gov.get_events_log(limit=limit)}


@router.get("/narrative-momentum/status")
async def momentum_get_status():
    from sparkai.agent.agent_narrative_momentum_governor import (
        AgentNarrativeMomentumGovernor,
    )
    gov = AgentNarrativeMomentumGovernor.get_instance()
    return {"status": "ok", "data": gov.get_status()}


@router.post("/narrative-momentum/cycle")
async def momentum_cycle():
    from sparkai.agent.agent_narrative_momentum_governor import (
        AgentNarrativeMomentumGovernor,
    )
    gov = AgentNarrativeMomentumGovernor.get_instance()
    return {"status": "ok", "data": gov.cycle()}


@router.post("/narrative-momentum/simulate")
async def momentum_simulate(req: SimulateRequest):
    from sparkai.agent.agent_narrative_momentum_governor import (
        AgentNarrativeMomentumGovernor,
    )
    gov = AgentNarrativeMomentumGovernor.get_instance()
    return {"status": "ok", "data": gov.simulate(cycles=req.cycles)}


@router.post("/narrative-momentum/reset")
async def momentum_reset():
    from sparkai.agent.agent_narrative_momentum_governor import (
        AgentNarrativeMomentumGovernor,
    )
    gov = AgentNarrativeMomentumGovernor.get_instance()
    return {"status": "ok", "data": gov.reset()}
