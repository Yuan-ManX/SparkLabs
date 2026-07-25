"""
SparkLabs Backend - Persona Lifecycle & Spatial Harmonics Routes

REST API endpoints for:
  - AgentPersonaLifecycleManager: NPC persona lifecycle from germination to legacy
  - EngineSpatialHarmonicsResonator: spatial resonance field modeling for locations

Routes use /persona-lifecycle/ and /spatial-harmonics/ prefixes.
"""

from __future__ import annotations

from fastapi import APIRouter, Query
from pydantic import BaseModel
from typing import Any, Dict, List, Optional

router = APIRouter()


# =============================================================================
# Request Models - Persona Lifecycle
# =============================================================================

class SimulateLifecycleRequest(BaseModel):
    cycles: int = 10


class CreatePersonaRequest(BaseModel):
    persona_id: str
    name: str
    archetype: str
    initial_traits: Optional[Dict[str, float]] = None
    theme: Optional[str] = None
    arc_type: Optional[str] = None


class RecordLifeEventRequest(BaseModel):
    category: str
    description: str
    trait_deltas: Optional[Dict[str, float]] = None
    relationship_changes: Optional[Dict[str, int]] = None
    narrative_weight: float = 0.5


class AddRelationshipRequest(BaseModel):
    target_name: str
    strength: float


# =============================================================================
# Request Models - Spatial Harmonics
# =============================================================================

class SimulateHarmonicsRequest(BaseModel):
    cycles: int = 10


class RegisterLocationRequest(BaseModel):
    location_id: str
    name: str
    position: List[float]
    frequencies: Optional[Dict[str, float]] = None
    influence_radius: float = 20.0
    mutability: float = 0.3


class MeasureResonanceRequest(BaseModel):
    event_type: str


class RecordFieldEventRequest(BaseModel):
    event_type: str
    intensity: float = 0.5
    description: str = ""


class FindResonantRequest(BaseModel):
    event_type: str
    limit: int = 5


# =============================================================================
# Persona Lifecycle Routes
# =============================================================================

@router.get("/persona-lifecycle/status")
async def persona_lifecycle_status():
    from sparkai.agent.agent_persona_lifecycle_manager import AgentPersonaLifecycleManager
    manager = AgentPersonaLifecycleManager.get_instance()
    return {"status": "ok", "data": manager.get_status()}


@router.post("/persona-lifecycle/personas")
async def persona_lifecycle_create(req: CreatePersonaRequest):
    from sparkai.agent.agent_persona_lifecycle_manager import AgentPersonaLifecycleManager
    manager = AgentPersonaLifecycleManager.get_instance()
    result = manager.create_persona(
        persona_id=req.persona_id,
        name=req.name,
        archetype=req.archetype,
        initial_traits=req.initial_traits,
        theme=req.theme,
        arc_type=req.arc_type,
    )
    return {"status": "ok", "data": result}


@router.get("/persona-lifecycle/personas")
async def persona_lifecycle_list_personas(
    stage: Optional[str] = Query(None),
    limit: int = Query(20, ge=1, le=200),
):
    from sparkai.agent.agent_persona_lifecycle_manager import AgentPersonaLifecycleManager
    manager = AgentPersonaLifecycleManager.get_instance()
    return {"status": "ok", "data": manager.list_personas(stage=stage, limit=limit)}


@router.get("/persona-lifecycle/personas/{persona_id}")
async def persona_lifecycle_get_persona(persona_id: str):
    from sparkai.agent.agent_persona_lifecycle_manager import AgentPersonaLifecycleManager
    manager = AgentPersonaLifecycleManager.get_instance()
    result = manager.get_persona(persona_id)
    if result is None:
        return {"status": "error", "message": "Persona not found"}
    return {"status": "ok", "data": result}


@router.post("/persona-lifecycle/personas/{persona_id}/events")
async def persona_lifecycle_record_event(persona_id: str, req: RecordLifeEventRequest):
    from sparkai.agent.agent_persona_lifecycle_manager import AgentPersonaLifecycleManager
    manager = AgentPersonaLifecycleManager.get_instance()
    result = manager.record_event(
        persona_id=persona_id,
        category=req.category,
        description=req.description,
        trait_deltas=req.trait_deltas,
        relationship_changes=req.relationship_changes,
        narrative_weight=req.narrative_weight,
    )
    return {"status": "ok", "data": result}


@router.get("/persona-lifecycle/personas/{persona_id}/events")
async def persona_lifecycle_list_events(
    persona_id: str,
    limit: int = Query(20, ge=1, le=200),
):
    from sparkai.agent.agent_persona_lifecycle_manager import AgentPersonaLifecycleManager
    manager = AgentPersonaLifecycleManager.get_instance()
    return {"status": "ok", "data": manager.list_events(persona_id, limit=limit)}


@router.post("/persona-lifecycle/personas/{persona_id}/relationships")
async def persona_lifecycle_add_relationship(persona_id: str, req: AddRelationshipRequest):
    from sparkai.agent.agent_persona_lifecycle_manager import AgentPersonaLifecycleManager
    manager = AgentPersonaLifecycleManager.get_instance()
    result = manager.add_relationship(
        persona_id=persona_id,
        target_name=req.target_name,
        strength=req.strength,
    )
    return {"status": "ok", "data": result}


@router.get("/persona-lifecycle/legacies")
async def persona_lifecycle_list_legacies(limit: int = Query(20, ge=1, le=200)):
    from sparkai.agent.agent_persona_lifecycle_manager import AgentPersonaLifecycleManager
    manager = AgentPersonaLifecycleManager.get_instance()
    return {"status": "ok", "data": manager.list_legacies(limit=limit)}


@router.post("/persona-lifecycle/cycle")
async def persona_lifecycle_run_cycle():
    from sparkai.agent.agent_persona_lifecycle_manager import AgentPersonaLifecycleManager
    manager = AgentPersonaLifecycleManager.get_instance()
    return {"status": "ok", "data": manager.run_cycle()}


@router.post("/persona-lifecycle/simulate")
async def persona_lifecycle_simulate(req: SimulateLifecycleRequest):
    from sparkai.agent.agent_persona_lifecycle_manager import AgentPersonaLifecycleManager
    manager = AgentPersonaLifecycleManager.get_instance()
    return {"status": "ok", "data": manager.simulate(cycles=req.cycles)}


@router.post("/persona-lifecycle/reset")
async def persona_lifecycle_reset():
    from sparkai.agent.agent_persona_lifecycle_manager import AgentPersonaLifecycleManager
    manager = AgentPersonaLifecycleManager.get_instance()
    return {"status": "ok", "data": manager.reset()}


# =============================================================================
# Spatial Harmonics Routes
# =============================================================================

@router.get("/spatial-harmonics/status")
async def harmonics_status():
    from sparkai.engine.engine_spatial_harmonics_resonator import EngineSpatialHarmonicsResonator
    resonator = EngineSpatialHarmonicsResonator.get_instance()
    return {"status": "ok", "data": resonator.get_status()}


@router.post("/spatial-harmonics/locations")
async def harmonics_register_location(req: RegisterLocationRequest):
    from sparkai.engine.engine_spatial_harmonics_resonator import EngineSpatialHarmonicsResonator
    resonator = EngineSpatialHarmonicsResonator.get_instance()
    if len(req.position) < 3:
        return {"status": "error", "message": "Position must have at least 3 coordinates"}
    result = resonator.register_location(
        location_id=req.location_id,
        name=req.name,
        position=(float(req.position[0]), float(req.position[1]), float(req.position[2])),
        frequencies=req.frequencies,
        influence_radius=req.influence_radius,
        mutability=req.mutability,
    )
    return {"status": "ok", "data": result}


@router.delete("/spatial-harmonics/locations/{location_id}")
async def harmonics_remove_location(location_id: str):
    from sparkai.engine.engine_spatial_harmonics_resonator import EngineSpatialHarmonicsResonator
    resonator = EngineSpatialHarmonicsResonator.get_instance()
    return {"status": "ok", "data": resonator.remove_location(location_id)}


@router.get("/spatial-harmonics/locations")
async def harmonics_list_locations(limit: int = Query(20, ge=1, le=200)):
    from sparkai.engine.engine_spatial_harmonics_resonator import EngineSpatialHarmonicsResonator
    resonator = EngineSpatialHarmonicsResonator.get_instance()
    return {"status": "ok", "data": resonator.list_locations(limit=limit)}


@router.get("/spatial-harmonics/locations/{location_id}")
async def harmonics_get_location(location_id: str):
    from sparkai.engine.engine_spatial_harmonics_resonator import EngineSpatialHarmonicsResonator
    resonator = EngineSpatialHarmonicsResonator.get_instance()
    result = resonator.get_location(location_id)
    if result is None:
        return {"status": "error", "message": "Location not found"}
    return {"status": "ok", "data": result}


@router.post("/spatial-harmonics/locations/{location_id}/measure")
async def harmonics_measure_resonance(location_id: str, req: MeasureResonanceRequest):
    from sparkai.engine.engine_spatial_harmonics_resonator import EngineSpatialHarmonicsResonator
    resonator = EngineSpatialHarmonicsResonator.get_instance()
    result = resonator.measure_resonance(location_id, req.event_type)
    return {"status": "ok", "data": result}


@router.post("/spatial-harmonics/locations/{location_id}/events")
async def harmonics_record_field_event(location_id: str, req: RecordFieldEventRequest):
    from sparkai.engine.engine_spatial_harmonics_resonator import EngineSpatialHarmonicsResonator
    resonator = EngineSpatialHarmonicsResonator.get_instance()
    result = resonator.record_field_event(
        location_id=location_id,
        event_type=req.event_type,
        intensity=req.intensity,
        description=req.description,
    )
    return {"status": "ok", "data": result}


@router.post("/spatial-harmonics/resonant")
async def harmonics_find_resonant(req: FindResonantRequest):
    from sparkai.engine.engine_spatial_harmonics_resonator import EngineSpatialHarmonicsResonator
    resonator = EngineSpatialHarmonicsResonator.get_instance()
    result = resonator.find_resonant_locations(req.event_type, limit=req.limit)
    return {"status": "ok", "data": result}


@router.post("/spatial-harmonics/cycle")
async def harmonics_run_cycle():
    from sparkai.engine.engine_spatial_harmonics_resonator import EngineSpatialHarmonicsResonator
    resonator = EngineSpatialHarmonicsResonator.get_instance()
    return {"status": "ok", "data": resonator.run_cycle()}


@router.post("/spatial-harmonics/simulate")
async def harmonics_simulate(req: SimulateHarmonicsRequest):
    from sparkai.engine.engine_spatial_harmonics_resonator import EngineSpatialHarmonicsResonator
    resonator = EngineSpatialHarmonicsResonator.get_instance()
    return {"status": "ok", "data": resonator.simulate(cycles=req.cycles)}


@router.get("/spatial-harmonics/readings")
async def harmonics_list_readings(limit: int = Query(20, ge=1, le=200)):
    from sparkai.engine.engine_spatial_harmonics_resonator import EngineSpatialHarmonicsResonator
    resonator = EngineSpatialHarmonicsResonator.get_instance()
    return {"status": "ok", "data": resonator.list_readings(limit=limit)}


@router.get("/spatial-harmonics/events")
async def harmonics_list_events(limit: int = Query(20, ge=1, le=200)):
    from sparkai.engine.engine_spatial_harmonics_resonator import EngineSpatialHarmonicsResonator
    resonator = EngineSpatialHarmonicsResonator.get_instance()
    return {"status": "ok", "data": resonator.list_events(limit=limit)}


@router.post("/spatial-harmonics/reset")
async def harmonics_reset():
    from sparkai.engine.engine_spatial_harmonics_resonator import EngineSpatialHarmonicsResonator
    resonator = EngineSpatialHarmonicsResonator.get_instance()
    return {"status": "ok", "data": resonator.reset()}
