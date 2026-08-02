"""
SparkLabs Backend - Cognitive Dissonance Resolver Routes

REST endpoints for the Cognitive Dissonance Resolver agent.
"""
from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional

router = APIRouter()


# =============================================================================
# Request Models
# =============================================================================

class RegisterConflictRequest(BaseModel):
    entity_id: str
    belief_a: str
    belief_b: str
    severity: Optional[str] = None        # low/moderate/high/critical/catastrophic
    centrality: Optional[str] = None      # peripheral/supporting/core/axiomatic


class SimulateRequest(BaseModel):
    cycles: int = 5


# =============================================================================
# Routes
# =============================================================================

@router.post("/cognitive-dissonance-resolver/register")
async def cognitive_dissonance_register_conflict(req: RegisterConflictRequest):
    from sparkai.agent.agent_cognitive_dissonance_resolver import (
        CognitiveDissonanceResolver, ConflictSeverity, BeliefCentrality,
    )
    resolver = CognitiveDissonanceResolver.get_instance()
    severity = None
    if req.severity is not None:
        try:
            severity = ConflictSeverity(req.severity)
        except ValueError:
            return {"status": "error", "detail": f"Invalid severity: {req.severity}"}
    centrality = None
    if req.centrality is not None:
        try:
            centrality = BeliefCentrality(req.centrality)
        except ValueError:
            return {"status": "error", "detail": f"Invalid centrality: {req.centrality}"}
    result = resolver.register_conflict(
        entity_id=req.entity_id,
        belief_a=req.belief_a,
        belief_b=req.belief_b,
        severity=severity,
        centrality=centrality,
    )
    if "error" in result:
        return {"status": "error", "detail": result["error"]}
    return {"status": "ok", "data": result}


@router.get("/cognitive-dissonance-resolver/status")
async def cognitive_dissonance_get_status():
    from sparkai.agent.agent_cognitive_dissonance_resolver import (
        CognitiveDissonanceResolver,
    )
    resolver = CognitiveDissonanceResolver.get_instance()
    return {"status": "ok", "data": resolver.get_status()}


@router.get("/cognitive-dissonance-resolver/conflicts")
async def cognitive_dissonance_get_conflicts(limit: int = 50):
    from sparkai.agent.agent_cognitive_dissonance_resolver import (
        CognitiveDissonanceResolver,
    )
    resolver = CognitiveDissonanceResolver.get_instance()
    return {"status": "ok", "data": resolver.get_conflicts(limit=limit)}


@router.get("/cognitive-dissonance-resolver/conflicts/{conflict_id}")
async def cognitive_dissonance_get_conflict(conflict_id: str):
    from sparkai.agent.agent_cognitive_dissonance_resolver import (
        CognitiveDissonanceResolver,
    )
    resolver = CognitiveDissonanceResolver.get_instance()
    result = resolver.get_conflict(conflict_id)
    if "error" in result:
        return {"status": "error", "detail": result["error"]}
    return {"status": "ok", "data": result}


@router.post("/cognitive-dissonance-resolver/cycle")
async def cognitive_dissonance_cycle():
    from sparkai.agent.agent_cognitive_dissonance_resolver import (
        CognitiveDissonanceResolver,
    )
    resolver = CognitiveDissonanceResolver.get_instance()
    return {"status": "ok", "data": resolver.cycle()}


@router.get("/cognitive-dissonance-resolver/events")
async def cognitive_dissonance_get_events(limit: int = 50):
    from sparkai.agent.agent_cognitive_dissonance_resolver import (
        CognitiveDissonanceResolver,
    )
    resolver = CognitiveDissonanceResolver.get_instance()
    return {"status": "ok", "data": resolver.get_events_log(limit=limit)}


@router.post("/cognitive-dissonance-resolver/simulate")
async def cognitive_dissonance_simulate(req: SimulateRequest):
    from sparkai.agent.agent_cognitive_dissonance_resolver import (
        CognitiveDissonanceResolver,
    )
    resolver = CognitiveDissonanceResolver.get_instance()
    return {"status": "ok", "data": resolver.simulate(cycles=req.cycles)}


@router.post("/cognitive-dissonance-resolver/reset")
async def cognitive_dissonance_reset():
    from sparkai.agent.agent_cognitive_dissonance_resolver import (
        CognitiveDissonanceResolver,
    )
    resolver = CognitiveDissonanceResolver.get_instance()
    return {"status": "ok", "data": resolver.reset()}
