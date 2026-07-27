"""
SparkLabs Backend - Cognitive Genesis Routes

REST API endpoints for the AgentCognitiveGenesisProtocol, which bootstraps
new agents from seed patterns and grows them through developmental stages.
"""

from __future__ import annotations

from fastapi import APIRouter, Query
from pydantic import BaseModel
from typing import Any, Dict, List, Optional

router = APIRouter()


# =============================================================================
# Request Models
# =============================================================================

class PlantSeedRequest(BaseModel):
    seed_id: str
    label: str
    parent_seed_id: Optional[str] = None
    temperament: Optional[Dict[str, float]] = None
    aptitudes: Optional[Dict[str, float]] = None


class ExerciseFacultyRequest(BaseModel):
    faculty: str
    intensity: float = 0.3


class ImprintRequest(BaseModel):
    imprint_id: str
    description: str
    faculty: str
    valence: float
    intensity: float


class SimulateRequest(BaseModel):
    cycles: int = 10


# =============================================================================
# Routes
# =============================================================================

@router.get("/cognitive-genesis/status")
async def genesis_status():
    from sparkai.agent.agent_cognitive_genesis_protocol import AgentCognitiveGenesisProtocol
    protocol = AgentCognitiveGenesisProtocol.get_instance()
    return {"status": "ok", "data": protocol.get_status()}


@router.post("/cognitive-genesis/seeds")
async def genesis_plant_seed(req: PlantSeedRequest):
    from sparkai.agent.agent_cognitive_genesis_protocol import (
        AgentCognitiveGenesisProtocol, TemperamentProfile, CognitiveFaculty,
    )
    protocol = AgentCognitiveGenesisProtocol.get_instance()
    # Build temperament from request
    temperament = None
    if req.temperament:
        temperament = TemperamentProfile(
            openness=req.temperament.get("openness", 0.5),
            resilience=req.temperament.get("resilience", 0.5),
            sociability=req.temperament.get("sociability", 0.5),
            aggressiveness=req.temperament.get("aggressiveness", 0.5),
            focus=req.temperament.get("focus", 0.5),
            adaptability=req.temperament.get("adaptability", 0.5),
            empathy=req.temperament.get("empathy", 0.5),
            playfulness=req.temperament.get("playfulness", 0.5),
        )
    # Build aptitudes from request
    aptitudes = None
    if req.aptitudes:
        aptitudes = {}
        for k, v in req.aptitudes.items():
            try:
                aptitudes[CognitiveFaculty(k)] = v
            except ValueError:
                continue
    result = protocol.plant_seed(
        seed_id=req.seed_id,
        label=req.label,
        parent_seed_id=req.parent_seed_id,
        temperament=temperament,
        aptitudes=aptitudes,
    )
    if "error" in result:
        return {"status": "error", "detail": result["error"]}
    return {"status": "ok", "data": result}


@router.delete("/cognitive-genesis/seeds/{seed_id}")
async def genesis_remove_seed(seed_id: str):
    from sparkai.agent.agent_cognitive_genesis_protocol import AgentCognitiveGenesisProtocol
    protocol = AgentCognitiveGenesisProtocol.get_instance()
    result = protocol.remove_seed(seed_id)
    if "error" in result:
        return {"status": "error", "detail": result["error"]}
    return {"status": "ok", "data": result}


@router.get("/cognitive-genesis/seeds")
async def genesis_list_seeds(limit: int = Query(50, ge=1, le=200)):
    from sparkai.agent.agent_cognitive_genesis_protocol import AgentCognitiveGenesisProtocol
    protocol = AgentCognitiveGenesisProtocol.get_instance()
    return {"status": "ok", "data": protocol.list_seeds(limit)}


@router.get("/cognitive-genesis/seeds/{seed_id}")
async def genesis_get_seed(seed_id: str):
    from sparkai.agent.agent_cognitive_genesis_protocol import AgentCognitiveGenesisProtocol
    protocol = AgentCognitiveGenesisProtocol.get_instance()
    data = protocol.get_seed(seed_id)
    if data is None:
        return {"status": "error", "detail": f"Seed not found: {seed_id}"}
    return {"status": "ok", "data": data}


@router.post("/cognitive-genesis/seeds/{seed_id}/activate")
async def genesis_activate(seed_id: str):
    from sparkai.agent.agent_cognitive_genesis_protocol import AgentCognitiveGenesisProtocol
    protocol = AgentCognitiveGenesisProtocol.get_instance()
    result = protocol.activate_seed(seed_id)
    if "error" in result:
        return {"status": "error", "detail": result["error"]}
    return {"status": "ok", "data": result}


@router.post("/cognitive-genesis/seeds/{seed_id}/exercise")
async def genesis_exercise(seed_id: str, req: ExerciseFacultyRequest):
    from sparkai.agent.agent_cognitive_genesis_protocol import (
        AgentCognitiveGenesisProtocol, CognitiveFaculty,
    )
    protocol = AgentCognitiveGenesisProtocol.get_instance()
    try:
        faculty = CognitiveFaculty(req.faculty)
    except ValueError:
        return {"status": "error", "detail": f"Unknown faculty: {req.faculty}"}
    result = protocol.exercise_faculty(seed_id, faculty, req.intensity)
    if "error" in result:
        return {"status": "error", "detail": result["error"]}
    return {"status": "ok", "data": result}


@router.post("/cognitive-genesis/seeds/{seed_id}/imprints")
async def genesis_imprint(seed_id: str, req: ImprintRequest):
    from sparkai.agent.agent_cognitive_genesis_protocol import (
        AgentCognitiveGenesisProtocol, CognitiveFaculty,
    )
    protocol = AgentCognitiveGenesisProtocol.get_instance()
    try:
        faculty = CognitiveFaculty(req.faculty)
    except ValueError:
        return {"status": "error", "detail": f"Unknown faculty: {req.faculty}"}
    result = protocol.imprint(
        seed_id=seed_id,
        imprint_id=req.imprint_id,
        description=req.description,
        faculty=faculty,
        valence=req.valence,
        intensity=req.intensity,
    )
    if "error" in result:
        return {"status": "error", "detail": result["error"]}
    return {"status": "ok", "data": result}


@router.get("/cognitive-genesis/seeds/{seed_id}/imprints")
async def genesis_list_imprints(seed_id: str, limit: int = Query(30, ge=1, le=200)):
    from sparkai.agent.agent_cognitive_genesis_protocol import AgentCognitiveGenesisProtocol
    protocol = AgentCognitiveGenesisProtocol.get_instance()
    return {"status": "ok", "data": protocol.get_imprints(seed_id, limit)}


@router.post("/cognitive-genesis/cycle")
async def genesis_cycle():
    from sparkai.agent.agent_cognitive_genesis_protocol import AgentCognitiveGenesisProtocol
    protocol = AgentCognitiveGenesisProtocol.get_instance()
    return {"status": "ok", "data": protocol.cycle()}


@router.post("/cognitive-genesis/simulate")
async def genesis_simulate(req: SimulateRequest):
    from sparkai.agent.agent_cognitive_genesis_protocol import AgentCognitiveGenesisProtocol
    protocol = AgentCognitiveGenesisProtocol.get_instance()
    return {"status": "ok", "data": protocol.simulate(req.cycles)}


@router.get("/cognitive-genesis/roster")
async def genesis_roster():
    from sparkai.agent.agent_cognitive_genesis_protocol import AgentCognitiveGenesisProtocol
    protocol = AgentCognitiveGenesisProtocol.get_instance()
    return {"status": "ok", "data": protocol.get_integrated_roster()}


@router.get("/cognitive-genesis/events")
async def genesis_events(limit: int = Query(50, ge=1, le=200)):
    from sparkai.agent.agent_cognitive_genesis_protocol import AgentCognitiveGenesisProtocol
    protocol = AgentCognitiveGenesisProtocol.get_instance()
    return {"status": "ok", "data": protocol.get_events(limit)}


@router.post("/cognitive-genesis/reset")
async def genesis_reset():
    from sparkai.agent.agent_cognitive_genesis_protocol import AgentCognitiveGenesisProtocol
    protocol = AgentCognitiveGenesisProtocol.get_instance()
    return {"status": "ok", "data": protocol.reset()}
