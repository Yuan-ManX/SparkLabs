"""
SparkLabs Backend - Belief Ecosystem & Phase Transition Routes

REST API endpoints for:
  - AgentBeliefEcosystemEvolver: NPC beliefs as competing species
  - EnginePhaseTransitionCatalyst: thermodynamic phase transitions

Routes use /belief-ecosystem/ and /phase-transition/ prefixes.
"""

from __future__ import annotations

from fastapi import APIRouter, Query
from pydantic import BaseModel
from typing import Any, Dict, List, Optional

router = APIRouter()


# =============================================================================
# Request Models - Belief Ecosystem
# =============================================================================

class SimulateEcosystemRequest(BaseModel):
    cycles: int = 10


class CreateEcosystemRequest(BaseModel):
    npc_id: str
    beliefs: Optional[List[Dict[str, Any]]] = None


class IntroduceBeliefRequest(BaseModel):
    belief_id: str
    label: str
    niche: str = "worldview"
    initial_population: float = 0.2
    fitness: float = 0.5
    description: str = ""


# =============================================================================
# Request Models - Phase Transition
# =============================================================================

class RegisterSystemRequest(BaseModel):
    system_id: str
    label: str
    initial_phase: str = "solid"
    initial_energy: float = 0.0
    base_dissipation: float = 0.02
    properties: Optional[Dict[str, Any]] = None


class SetThresholdsRequest(BaseModel):
    rise_thresholds: Optional[Dict[str, float]] = None
    fall_thresholds: Optional[Dict[str, float]] = None


class LinkSystemsRequest(BaseModel):
    target_id: str
    coupling: float = 0.5
    direction: str = "upward"


class FireCatalystRequest(BaseModel):
    catalyst_type: str
    target_system_ids: Optional[List[str]] = None
    energy_delta: Optional[float] = None
    description: str = ""


class SimulatePhaseRequest(BaseModel):
    cycles: int = 10


# =============================================================================
# Belief Ecosystem Routes
# =============================================================================

@router.get("/belief-ecosystem/status")
async def belief_ecosystem_status():
    from sparkai.agent.agent_belief_ecosystem_evolver import AgentBeliefEcosystemEvolver
    evolver = AgentBeliefEcosystemEvolver.get_instance()
    return {"status": "ok", "data": evolver.get_status()}


@router.post("/belief-ecosystem/ecosystems")
async def belief_ecosystem_create(req: CreateEcosystemRequest):
    from sparkai.agent.agent_belief_ecosystem_evolver import AgentBeliefEcosystemEvolver
    evolver = AgentBeliefEcosystemEvolver.get_instance()
    result = evolver.create_ecosystem(req.npc_id, req.beliefs)
    if "error" in result:
        return {"status": "error", "detail": result["error"]}
    return {"status": "ok", "data": result}


@router.get("/belief-ecosystem/ecosystems/{npc_id}")
async def belief_ecosystem_get(npc_id: str):
    from sparkai.agent.agent_belief_ecosystem_evolver import AgentBeliefEcosystemEvolver
    evolver = AgentBeliefEcosystemEvolver.get_instance()
    result = evolver.get_ecosystem(npc_id)
    if result is None:
        return {"status": "error", "detail": f"Ecosystem not found: {npc_id}"}
    return {"status": "ok", "data": result}


@router.get("/belief-ecosystem/ecosystems")
async def belief_ecosystem_list(limit: int = Query(20, ge=1, le=200)):
    from sparkai.agent.agent_belief_ecosystem_evolver import AgentBeliefEcosystemEvolver
    evolver = AgentBeliefEcosystemEvolver.get_instance()
    return {"status": "ok", "data": evolver.list_ecosystems(limit)}


@router.delete("/belief-ecosystem/ecosystems/{npc_id}")
async def belief_ecosystem_remove(npc_id: str):
    from sparkai.agent.agent_belief_ecosystem_evolver import AgentBeliefEcosystemEvolver
    evolver = AgentBeliefEcosystemEvolver.get_instance()
    result = evolver.remove_ecosystem(npc_id)
    if "error" in result:
        return {"status": "error", "detail": result["error"]}
    return {"status": "ok", "data": result}


@router.post("/belief-ecosystem/ecosystems/{npc_id}/beliefs")
async def belief_ecosystem_introduce(npc_id: str, req: IntroduceBeliefRequest):
    from sparkai.agent.agent_belief_ecosystem_evolver import AgentBeliefEcosystemEvolver
    evolver = AgentBeliefEcosystemEvolver.get_instance()
    result = evolver.introduce_belief(
        npc_id=npc_id,
        belief_id=req.belief_id,
        label=req.label,
        niche=req.niche,
        initial_population=req.initial_population,
        fitness=req.fitness,
        description=req.description,
    )
    if "error" in result:
        return {"status": "error", "detail": result["error"]}
    return {"status": "ok", "data": result}


@router.post("/belief-ecosystem/cycle")
async def belief_ecosystem_cycle():
    from sparkai.agent.agent_belief_ecosystem_evolver import AgentBeliefEcosystemEvolver
    evolver = AgentBeliefEcosystemEvolver.get_instance()
    return {"status": "ok", "data": evolver.run_cycle()}


@router.post("/belief-ecosystem/simulate")
async def belief_ecosystem_simulate(req: SimulateEcosystemRequest):
    from sparkai.agent.agent_belief_ecosystem_evolver import AgentBeliefEcosystemEvolver
    evolver = AgentBeliefEcosystemEvolver.get_instance()
    return {"status": "ok", "data": evolver.simulate(req.cycles)}


@router.get("/belief-ecosystem/invasions")
async def belief_ecosystem_invasions(
    npc_id: Optional[str] = Query(None),
    limit: int = Query(20, ge=1, le=200),
):
    from sparkai.agent.agent_belief_ecosystem_evolver import AgentBeliefEcosystemEvolver
    evolver = AgentBeliefEcosystemEvolver.get_instance()
    return {"status": "ok", "data": evolver.list_invasions(npc_id, limit)}


@router.get("/belief-ecosystem/beliefs")
async def belief_ecosystem_beliefs(
    npc_id: Optional[str] = Query(None),
    niche: Optional[str] = Query(None),
    limit: int = Query(20, ge=1, le=200),
):
    from sparkai.agent.agent_belief_ecosystem_evolver import AgentBeliefEcosystemEvolver
    evolver = AgentBeliefEcosystemEvolver.get_instance()
    return {"status": "ok", "data": evolver.list_beliefs(npc_id, niche, limit)}


@router.get("/belief-ecosystem/relationships")
async def belief_ecosystem_relationships(
    npc_id: Optional[str] = Query(None),
    limit: int = Query(20, ge=1, le=200),
):
    from sparkai.agent.agent_belief_ecosystem_evolver import AgentBeliefEcosystemEvolver
    evolver = AgentBeliefEcosystemEvolver.get_instance()
    return {"status": "ok", "data": evolver.list_relationships(npc_id, limit)}


@router.post("/belief-ecosystem/reset")
async def belief_ecosystem_reset():
    from sparkai.agent.agent_belief_ecosystem_evolver import AgentBeliefEcosystemEvolver
    evolver = AgentBeliefEcosystemEvolver.get_instance()
    return {"status": "ok", "data": evolver.reset()}


# =============================================================================
# Phase Transition Routes
# =============================================================================

@router.get("/phase-transition/status")
async def phase_transition_status():
    from sparkai.engine.engine_phase_transition_catalyst import EnginePhaseTransitionCatalyst
    catalyst = EnginePhaseTransitionCatalyst.get_instance()
    return {"status": "ok", "data": catalyst.get_status()}


@router.post("/phase-transition/systems")
async def phase_transition_register_system(req: RegisterSystemRequest):
    from sparkai.engine.engine_phase_transition_catalyst import EnginePhaseTransitionCatalyst
    catalyst = EnginePhaseTransitionCatalyst.get_instance()
    result = catalyst.register_system(
        system_id=req.system_id,
        label=req.label,
        initial_phase=req.initial_phase,
        initial_energy=req.initial_energy,
        base_dissipation=req.base_dissipation,
        properties=req.properties,
    )
    if "error" in result:
        return {"status": "error", "detail": result["error"]}
    return {"status": "ok", "data": result}


@router.get("/phase-transition/systems/{system_id}")
async def phase_transition_get_system(system_id: str):
    from sparkai.engine.engine_phase_transition_catalyst import EnginePhaseTransitionCatalyst
    catalyst = EnginePhaseTransitionCatalyst.get_instance()
    result = catalyst.get_system(system_id)
    if "error" in result:
        return {"status": "error", "detail": result["error"]}
    return {"status": "ok", "data": result}


@router.get("/phase-transition/systems")
async def phase_transition_list_systems():
    from sparkai.engine.engine_phase_transition_catalyst import EnginePhaseTransitionCatalyst
    catalyst = EnginePhaseTransitionCatalyst.get_instance()
    return {"status": "ok", "data": catalyst.list_systems()}


@router.delete("/phase-transition/systems/{system_id}")
async def phase_transition_remove_system(system_id: str):
    from sparkai.engine.engine_phase_transition_catalyst import EnginePhaseTransitionCatalyst
    catalyst = EnginePhaseTransitionCatalyst.get_instance()
    result = catalyst.remove_system(system_id)
    if "error" in result:
        return {"status": "error", "detail": result["error"]}
    return {"status": "ok", "data": result}


@router.put("/phase-transition/systems/{system_id}/thresholds")
async def phase_transition_set_thresholds(system_id: str, req: SetThresholdsRequest):
    from sparkai.engine.engine_phase_transition_catalyst import EnginePhaseTransitionCatalyst
    catalyst = EnginePhaseTransitionCatalyst.get_instance()
    result = catalyst.set_thresholds(
        system_id=system_id,
        rise_thresholds=req.rise_thresholds,
        fall_thresholds=req.fall_thresholds,
    )
    if "error" in result:
        return {"status": "error", "detail": result["error"]}
    return {"status": "ok", "data": result}


@router.post("/phase-transition/systems/{system_id}/links")
async def phase_transition_link_systems(system_id: str, req: LinkSystemsRequest):
    from sparkai.engine.engine_phase_transition_catalyst import EnginePhaseTransitionCatalyst
    catalyst = EnginePhaseTransitionCatalyst.get_instance()
    result = catalyst.link_systems(
        source_id=system_id,
        target_id=req.target_id,
        coupling=req.coupling,
        direction=req.direction,
    )
    if "error" in result:
        return {"status": "error", "detail": result["error"]}
    return {"status": "ok", "data": result}


@router.delete("/phase-transition/systems/{system_id}/links/{target_id}")
async def phase_transition_unlink_systems(system_id: str, target_id: str):
    from sparkai.engine.engine_phase_transition_catalyst import EnginePhaseTransitionCatalyst
    catalyst = EnginePhaseTransitionCatalyst.get_instance()
    result = catalyst.unlink_systems(system_id, target_id)
    if "error" in result:
        return {"status": "error", "detail": result["error"]}
    return {"status": "ok", "data": result}


@router.get("/phase-transition/systems/{system_id}/links")
async def phase_transition_list_links(system_id: str):
    from sparkai.engine.engine_phase_transition_catalyst import EnginePhaseTransitionCatalyst
    catalyst = EnginePhaseTransitionCatalyst.get_instance()
    result = catalyst.list_links(system_id)
    if "error" in result:
        return {"status": "error", "detail": result["error"]}
    return {"status": "ok", "data": result}


@router.post("/phase-transition/catalysts")
async def phase_transition_fire_catalyst(req: FireCatalystRequest):
    from sparkai.engine.engine_phase_transition_catalyst import EnginePhaseTransitionCatalyst
    catalyst = EnginePhaseTransitionCatalyst.get_instance()
    result = catalyst.fire_catalyst(
        catalyst_type=req.catalyst_type,
        target_system_ids=req.target_system_ids,
        energy_delta=req.energy_delta,
        description=req.description,
    )
    if "error" in result:
        return {"status": "error", "detail": result["error"]}
    return {"status": "ok", "data": result}


@router.get("/phase-transition/catalysts")
async def phase_transition_list_catalysts(limit: int = Query(20, ge=1, le=200)):
    from sparkai.engine.engine_phase_transition_catalyst import EnginePhaseTransitionCatalyst
    catalyst = EnginePhaseTransitionCatalyst.get_instance()
    return {"status": "ok", "data": catalyst.list_catalysts(limit)}


@router.post("/phase-transition/cycle")
async def phase_transition_cycle():
    from sparkai.engine.engine_phase_transition_catalyst import EnginePhaseTransitionCatalyst
    catalyst = EnginePhaseTransitionCatalyst.get_instance()
    return {"status": "ok", "data": catalyst.run_cycle()}


@router.post("/phase-transition/simulate")
async def phase_transition_simulate(req: SimulatePhaseRequest):
    """Run multiple cycles in sequence."""
    from sparkai.engine.engine_phase_transition_catalyst import EnginePhaseTransitionCatalyst
    catalyst = EnginePhaseTransitionCatalyst.get_instance()
    cycles = max(1, min(100, int(req.cycles)))
    return {"status": "ok", "data": catalyst.simulate(cycles)}


@router.get("/phase-transition/history")
async def phase_transition_history(limit: int = Query(20, ge=1, le=200)):
    from sparkai.engine.engine_phase_transition_catalyst import EnginePhaseTransitionCatalyst
    catalyst = EnginePhaseTransitionCatalyst.get_instance()
    return {"status": "ok", "data": catalyst.get_history(limit)}


@router.post("/phase-transition/reset")
async def phase_transition_reset():
    from sparkai.engine.engine_phase_transition_catalyst import EnginePhaseTransitionCatalyst
    catalyst = EnginePhaseTransitionCatalyst.get_instance()
    return {"status": "ok", "data": catalyst.reset()}
