"""
SparkLabs Backend - Quantum Reality Forge Routes

REST endpoints for the Engine Quantum Reality Forge.
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Any, Dict, List, Optional

router = APIRouter()


# =============================================================================
# Request Models
# =============================================================================

class RegisterRegionRequest(BaseModel):
    region_id: str
    label: str
    temperature: float = 1.0


class SuperposeRequest(BaseModel):
    entity_label: str
    possibility_class: str  # spatial, temporal, identity, event, relation, state
    state_description: str
    raw_weight: float = 0.5
    energy: float = 0.5
    tags: List[str] = Field(default_factory=list)


class EntangleRequest(BaseModel):
    region_a: str
    entity_a: str
    region_b: str
    entity_b: str
    entanglement_type: str  # correlated, anti, conditional, resonant, causal
    strength: float = 0.5


class ObserveRequest(BaseModel):
    observer: str
    entity_label: str


class SimulateRequest(BaseModel):
    cycles: int = 5


# =============================================================================
# Routes
# =============================================================================

@router.post("/quantum-forge/regions")
async def quantum_forge_register_region(req: RegisterRegionRequest):
    from sparkai.engine.engine_quantum_reality_forge import (
        EngineQuantumRealityForge,
    )
    forge = EngineQuantumRealityForge.get_instance()
    result = forge.register_region(req.region_id, req.label, req.temperature)
    if "error" in result:
        return {"status": "error", "detail": result["error"]}
    return {"status": "ok", "data": result}


@router.delete("/quantum-forge/regions/{region_id}")
async def quantum_forge_remove_region(region_id: str):
    from sparkai.engine.engine_quantum_reality_forge import (
        EngineQuantumRealityForge,
    )
    forge = EngineQuantumRealityForge.get_instance()
    result = forge.remove_region(region_id)
    if "error" in result:
        return {"status": "error", "detail": result["error"]}
    return {"status": "ok", "data": result}


@router.post("/quantum-forge/regions/{region_id}/superpose")
async def quantum_forge_superpose(region_id: str, req: SuperposeRequest):
    from sparkai.engine.engine_quantum_reality_forge import (
        EngineQuantumRealityForge, PossibilityClass,
    )
    forge = EngineQuantumRealityForge.get_instance()
    try:
        pclass = PossibilityClass(req.possibility_class)
    except ValueError:
        return {"status": "error", "detail": f"Invalid possibility_class: {req.possibility_class}"}
    result = forge.superpose(
        region_id=region_id,
        entity_label=req.entity_label,
        possibility_class=pclass,
        state_description=req.state_description,
        raw_weight=req.raw_weight,
        energy=req.energy,
        tags=req.tags,
    )
    if "error" in result:
        return {"status": "error", "detail": result["error"]}
    return {"status": "ok", "data": result}


@router.post("/quantum-forge/entanglements")
async def quantum_forge_entangle(req: EntangleRequest):
    from sparkai.engine.engine_quantum_reality_forge import (
        EngineQuantumRealityForge, EntanglementType,
    )
    forge = EngineQuantumRealityForge.get_instance()
    try:
        etype = EntanglementType(req.entanglement_type)
    except ValueError:
        return {"status": "error", "detail": f"Invalid entanglement_type: {req.entanglement_type}"}
    result = forge.entangle(
        region_a=req.region_a,
        entity_a=req.entity_a,
        region_b=req.region_b,
        entity_b=req.entity_b,
        entanglement_type=etype,
        strength=req.strength,
    )
    if "error" in result:
        return {"status": "error", "detail": result["error"]}
    return {"status": "ok", "data": result}


@router.post("/quantum-forge/regions/{region_id}/observe")
async def quantum_forge_observe(region_id: str, req: ObserveRequest):
    from sparkai.engine.engine_quantum_reality_forge import (
        EngineQuantumRealityForge,
    )
    forge = EngineQuantumRealityForge.get_instance()
    result = forge.observe(region_id, req.observer, req.entity_label)
    if "error" in result:
        return {"status": "error", "detail": result["error"]}
    return {"status": "ok", "data": result}


@router.post("/quantum-forge/cycle")
async def quantum_forge_cycle():
    from sparkai.engine.engine_quantum_reality_forge import (
        EngineQuantumRealityForge,
    )
    forge = EngineQuantumRealityForge.get_instance()
    return {"status": "ok", "data": forge.cycle()}


@router.post("/quantum-forge/simulate")
async def quantum_forge_simulate(req: SimulateRequest):
    from sparkai.engine.engine_quantum_reality_forge import (
        EngineQuantumRealityForge,
    )
    forge = EngineQuantumRealityForge.get_instance()
    return {"status": "ok", "data": forge.simulate(req.cycles)}


@router.get("/quantum-forge/regions/{region_id}")
async def quantum_forge_get_region(region_id: str):
    from sparkai.engine.engine_quantum_reality_forge import (
        EngineQuantumRealityForge,
    )
    forge = EngineQuantumRealityForge.get_instance()
    result = forge.get_region_state(region_id)
    if "error" in result:
        return {"status": "error", "detail": result["error"]}
    return {"status": "ok", "data": result}


@router.get("/quantum-forge/entanglements")
async def quantum_forge_get_entanglements(region_id: Optional[str] = None):
    from sparkai.engine.engine_quantum_reality_forge import (
        EngineQuantumRealityForge,
    )
    forge = EngineQuantumRealityForge.get_instance()
    return {"status": "ok", "data": forge.get_entanglements(region_id)}


@router.get("/quantum-forge/collapses")
async def quantum_forge_get_collapses(limit: int = 20):
    from sparkai.engine.engine_quantum_reality_forge import (
        EngineQuantumRealityForge,
    )
    forge = EngineQuantumRealityForge.get_instance()
    return {"status": "ok", "data": forge.get_collapses(limit)}


@router.get("/quantum-forge/events")
async def quantum_forge_get_events(limit: int = 50):
    from sparkai.engine.engine_quantum_reality_forge import (
        EngineQuantumRealityForge,
    )
    forge = EngineQuantumRealityForge.get_instance()
    return {"status": "ok", "data": forge.get_events_log(limit)}


@router.get("/quantum-forge/status")
async def quantum_forge_status():
    from sparkai.engine.engine_quantum_reality_forge import (
        EngineQuantumRealityForge,
    )
    forge = EngineQuantumRealityForge.get_instance()
    return {"status": "ok", "data": forge.get_status()}


@router.post("/quantum-forge/reset")
async def quantum_forge_reset():
    from sparkai.engine.engine_quantum_reality_forge import (
        EngineQuantumRealityForge,
    )
    forge = EngineQuantumRealityForge.get_instance()
    return {"status": "ok", "data": forge.reset()}
