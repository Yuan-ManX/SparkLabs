"""
SparkLabs Backend - Motivation Chemistry & Quantum State Routes

REST API endpoints for:
  - AgentMotivationChemistryEngine: NPC motivations as reactive chemical compounds
  - EngineQuantumStateProjector: quantum superposition for game objects

Routes use /motivation-chemistry/ and /quantum-state/ prefixes.
"""

from __future__ import annotations

from fastapi import APIRouter, Query
from pydantic import BaseModel
from typing import Any, Dict, List, Optional

router = APIRouter()


# =============================================================================
# Request Models - Motivation Chemistry
# =============================================================================

class SimulateChemistryRequest(BaseModel):
    cycles: int = 10


class CreateSolutionRequest(BaseModel):
    npc_id: str
    initial_concentrations: Optional[Dict[str, float]] = None


class ApplyCatalystRequest(BaseModel):
    catalyst_type: str
    intensity: float = 0.5
    description: str = ""


# =============================================================================
# Request Models - Quantum State
# =============================================================================

class SimulateQuantumRequest(BaseModel):
    cycles: int = 10


class RegisterQuantumObjectRequest(BaseModel):
    object_id: str
    object_type: str
    states: List[Dict[str, Any]]


class EntangleRequest(BaseModel):
    object_b: str
    link_type: str = "correlated"


class ObserveRequest(BaseModel):
    observation_type: str = "player_interact"
    observer: str = "player"


class QueueObservationRequest(BaseModel):
    observation_type: str = "player_interact"
    observer: str = "player"


# =============================================================================
# Motivation Chemistry Routes
# =============================================================================

@router.get("/motivation-chemistry/status")
async def chemistry_status():
    from sparkai.agent.agent_motivation_chemistry_engine import AgentMotivationChemistryEngine
    engine = AgentMotivationChemistryEngine.get_instance()
    return {"status": "ok", "data": engine.get_status()}


@router.post("/motivation-chemistry/solutions")
async def chemistry_create_solution(req: CreateSolutionRequest):
    from sparkai.agent.agent_motivation_chemistry_engine import AgentMotivationChemistryEngine
    engine = AgentMotivationChemistryEngine.get_instance()
    result = engine.create_solution(req.npc_id, req.initial_concentrations)
    return {"status": "ok", "data": result}


@router.get("/motivation-chemistry/solutions")
async def chemistry_list_solutions(limit: int = Query(20, ge=1, le=200)):
    from sparkai.agent.agent_motivation_chemistry_engine import AgentMotivationChemistryEngine
    engine = AgentMotivationChemistryEngine.get_instance()
    return {"status": "ok", "data": engine.list_solutions(limit=limit)}


@router.get("/motivation-chemistry/solutions/{npc_id}")
async def chemistry_get_solution(npc_id: str):
    from sparkai.agent.agent_motivation_chemistry_engine import AgentMotivationChemistryEngine
    engine = AgentMotivationChemistryEngine.get_instance()
    result = engine.get_solution(npc_id)
    if result is None:
        return {"status": "error", "message": "Solution not found"}
    return {"status": "ok", "data": result}


@router.delete("/motivation-chemistry/solutions/{npc_id}")
async def chemistry_remove_solution(npc_id: str):
    from sparkai.agent.agent_motivation_chemistry_engine import AgentMotivationChemistryEngine
    engine = AgentMotivationChemistryEngine.get_instance()
    return {"status": "ok", "data": engine.remove_solution(npc_id)}


@router.post("/motivation-chemistry/solutions/{npc_id}/catalysts")
async def chemistry_apply_catalyst(npc_id: str, req: ApplyCatalystRequest):
    from sparkai.agent.agent_motivation_chemistry_engine import AgentMotivationChemistryEngine
    engine = AgentMotivationChemistryEngine.get_instance()
    result = engine.apply_catalyst(npc_id, req.catalyst_type, req.intensity, req.description)
    return {"status": "ok", "data": result}


@router.get("/motivation-chemistry/catalysts")
async def chemistry_list_catalysts(
    npc_id: Optional[str] = Query(None),
    limit: int = Query(20, ge=1, le=200),
):
    from sparkai.agent.agent_motivation_chemistry_engine import AgentMotivationChemistryEngine
    engine = AgentMotivationChemistryEngine.get_instance()
    return {"status": "ok", "data": engine.list_catalyst_events(npc_id=npc_id, limit=limit)}


@router.get("/motivation-chemistry/compounds")
async def chemistry_list_compounds(
    npc_id: Optional[str] = Query(None),
    limit: int = Query(20, ge=1, le=200),
):
    from sparkai.agent.agent_motivation_chemistry_engine import AgentMotivationChemistryEngine
    engine = AgentMotivationChemistryEngine.get_instance()
    return {"status": "ok", "data": engine.list_compounds(npc_id=npc_id, limit=limit)}


@router.post("/motivation-chemistry/cycle")
async def chemistry_run_cycle():
    from sparkai.agent.agent_motivation_chemistry_engine import AgentMotivationChemistryEngine
    engine = AgentMotivationChemistryEngine.get_instance()
    return {"status": "ok", "data": engine.run_cycle()}


@router.post("/motivation-chemistry/simulate")
async def chemistry_simulate(req: SimulateChemistryRequest):
    from sparkai.agent.agent_motivation_chemistry_engine import AgentMotivationChemistryEngine
    engine = AgentMotivationChemistryEngine.get_instance()
    return {"status": "ok", "data": engine.simulate(cycles=req.cycles)}


@router.post("/motivation-chemistry/reset")
async def chemistry_reset():
    from sparkai.agent.agent_motivation_chemistry_engine import AgentMotivationChemistryEngine
    engine = AgentMotivationChemistryEngine.get_instance()
    return {"status": "ok", "data": engine.reset()}


# =============================================================================
# Quantum State Routes
# =============================================================================

@router.get("/quantum-state/status")
async def quantum_status():
    from sparkai.engine.engine_quantum_state_projector import EngineQuantumStateProjector
    projector = EngineQuantumStateProjector.get_instance()
    return {"status": "ok", "data": projector.get_status()}


@router.post("/quantum-state/objects")
async def quantum_register_object(req: RegisterQuantumObjectRequest):
    from sparkai.engine.engine_quantum_state_projector import EngineQuantumStateProjector
    projector = EngineQuantumStateProjector.get_instance()
    result = projector.register_object(req.object_id, req.object_type, req.states)
    return {"status": "ok", "data": result}


@router.get("/quantum-state/objects")
async def quantum_list_objects(
    object_type: Optional[str] = Query(None),
    superposition_only: bool = Query(False),
    limit: int = Query(20, ge=1, le=200),
):
    from sparkai.engine.engine_quantum_state_projector import EngineQuantumStateProjector
    projector = EngineQuantumStateProjector.get_instance()
    return {"status": "ok", "data": projector.list_objects(
        object_type=object_type, superposition_only=superposition_only, limit=limit)}


@router.get("/quantum-state/objects/{object_id}")
async def quantum_get_object(object_id: str):
    from sparkai.engine.engine_quantum_state_projector import EngineQuantumStateProjector
    projector = EngineQuantumStateProjector.get_instance()
    result = projector.get_object(object_id)
    if result is None:
        return {"status": "error", "message": "Object not found"}
    return {"status": "ok", "data": result}


@router.delete("/quantum-state/objects/{object_id}")
async def quantum_remove_object(object_id: str):
    from sparkai.engine.engine_quantum_state_projector import EngineQuantumStateProjector
    projector = EngineQuantumStateProjector.get_instance()
    return {"status": "ok", "data": projector.remove_object(object_id)}


@router.post("/quantum-state/objects/{object_id}/entangle")
async def quantum_entangle(object_id: str, req: EntangleRequest):
    from sparkai.engine.engine_quantum_state_projector import EngineQuantumStateProjector
    projector = EngineQuantumStateProjector.get_instance()
    result = projector.entangle_objects(object_id, req.object_b, req.link_type)
    return {"status": "ok", "data": result}


@router.post("/quantum-state/objects/{object_id}/observe")
async def quantum_observe(object_id: str, req: ObserveRequest):
    from sparkai.engine.engine_quantum_state_projector import EngineQuantumStateProjector
    projector = EngineQuantumStateProjector.get_instance()
    result = projector.observe(object_id, req.observation_type, req.observer)
    return {"status": "ok", "data": result}


@router.post("/quantum-state/objects/{object_id}/queue-observation")
async def quantum_queue_observation(object_id: str, req: QueueObservationRequest):
    from sparkai.engine.engine_quantum_state_projector import EngineQuantumStateProjector
    projector = EngineQuantumStateProjector.get_instance()
    result = projector.queue_observation(object_id, req.observation_type, req.observer)
    return {"status": "ok", "data": result}


@router.post("/quantum-state/objects/{object_id}/reset-superposition")
async def quantum_reset_superposition(object_id: str):
    from sparkai.engine.engine_quantum_state_projector import EngineQuantumStateProjector
    projector = EngineQuantumStateProjector.get_instance()
    return {"status": "ok", "data": projector.reset_superposition(object_id)}


@router.get("/quantum-state/entanglements")
async def quantum_list_entanglements(limit: int = Query(20, ge=1, le=200)):
    from sparkai.engine.engine_quantum_state_projector import EngineQuantumStateProjector
    projector = EngineQuantumStateProjector.get_instance()
    return {"status": "ok", "data": projector.list_entanglements(limit=limit)}


@router.get("/quantum-state/collapses")
async def quantum_list_collapses(
    object_id: Optional[str] = Query(None),
    limit: int = Query(20, ge=1, le=200),
):
    from sparkai.engine.engine_quantum_state_projector import EngineQuantumStateProjector
    projector = EngineQuantumStateProjector.get_instance()
    return {"status": "ok", "data": projector.list_collapse_events(object_id=object_id, limit=limit)}


@router.post("/quantum-state/cycle")
async def quantum_run_cycle():
    from sparkai.engine.engine_quantum_state_projector import EngineQuantumStateProjector
    projector = EngineQuantumStateProjector.get_instance()
    return {"status": "ok", "data": projector.run_cycle()}


@router.post("/quantum-state/simulate")
async def quantum_simulate(req: SimulateQuantumRequest):
    from sparkai.engine.engine_quantum_state_projector import EngineQuantumStateProjector
    projector = EngineQuantumStateProjector.get_instance()
    return {"status": "ok", "data": projector.simulate(cycles=req.cycles)}


@router.post("/quantum-state/reset")
async def quantum_reset():
    from sparkai.engine.engine_quantum_state_projector import EngineQuantumStateProjector
    projector = EngineQuantumStateProjector.get_instance()
    return {"status": "ok", "data": projector.reset()}
