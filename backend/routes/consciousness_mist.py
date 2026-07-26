"""
SparkLabs Backend - Consciousness Stratum & Probability Mist Routes

REST API endpoints for:
  - AgentConsciousnessStratumFormer: consciousness as geological strata
  - EngineProbabilityMistDiffuser: uncertainty as diffusing mist

Routes use /consciousness-stratum/ and /probability-mist/ prefixes.
"""

from __future__ import annotations

from fastapi import APIRouter, Query
from pydantic import BaseModel
from typing import Any, Dict, List, Optional

router = APIRouter()


# =============================================================================
# Request Models - Consciousness Stratum
# =============================================================================

class RegisterDepositRequest(BaseModel):
    deposit_id: str
    label: str
    layer: str = "reflexive"
    mass: Optional[float] = None
    emotional_charge: float = 0.3


class SetDepositMassRequest(BaseModel):
    mass: float


class SimulateStratumRequest(BaseModel):
    cycles: int = 10


# =============================================================================
# Request Models - Probability Mist
# =============================================================================

class RegisterMistRegionRequest(BaseModel):
    region_id: str
    label: str
    mist_type: str = "fog"
    density: Optional[float] = None
    viscosity: Optional[float] = None
    volatility: Optional[float] = None
    is_source: bool = False


class SetMistDensityRequest(BaseModel):
    density: float
    description: str = ""


class LinkMistRegionsRequest(BaseModel):
    target_id: str
    flow_rate: float = 0.5


class SimulateMistRequest(BaseModel):
    cycles: int = 10


# =============================================================================
# Consciousness Stratum Routes
# =============================================================================

@router.get("/consciousness-stratum/status")
async def consciousness_stratum_status():
    from sparkai.agent.agent_consciousness_stratum_former import AgentConsciousnessStratumFormer
    former = AgentConsciousnessStratumFormer.get_instance()
    return {"status": "ok", "data": former.get_status()}


@router.post("/consciousness-stratum/deposits")
async def consciousness_stratum_register_deposit(req: RegisterDepositRequest):
    from sparkai.agent.agent_consciousness_stratum_former import AgentConsciousnessStratumFormer
    former = AgentConsciousnessStratumFormer.get_instance()
    result = former.register_deposit(
        req.deposit_id, req.label, req.layer, req.mass, req.emotional_charge,
    )
    if "error" in result:
        return {"status": "error", "detail": result["error"]}
    return {"status": "ok", "data": result}


@router.get("/consciousness-stratum/deposits/{deposit_id}")
async def consciousness_stratum_get_deposit(deposit_id: str):
    from sparkai.agent.agent_consciousness_stratum_former import AgentConsciousnessStratumFormer
    former = AgentConsciousnessStratumFormer.get_instance()
    result = former.get_deposit(deposit_id)
    if "error" in result:
        return {"status": "error", "detail": result["error"]}
    return {"status": "ok", "data": result}


@router.get("/consciousness-stratum/deposits")
async def consciousness_stratum_list_deposits(
    layer: Optional[str] = Query(None),
    limit: int = Query(30, ge=1, le=100),
):
    from sparkai.agent.agent_consciousness_stratum_former import AgentConsciousnessStratumFormer
    former = AgentConsciousnessStratumFormer.get_instance()
    return {"status": "ok", "data": former.list_deposits(layer, limit)}


@router.delete("/consciousness-stratum/deposits/{deposit_id}")
async def consciousness_stratum_remove_deposit(deposit_id: str):
    from sparkai.agent.agent_consciousness_stratum_former import AgentConsciousnessStratumFormer
    former = AgentConsciousnessStratumFormer.get_instance()
    result = former.remove_deposit(deposit_id)
    return {"status": "ok", "data": result}


@router.put("/consciousness-stratum/deposits/{deposit_id}/mass")
async def consciousness_stratum_set_deposit_mass(deposit_id: str, req: SetDepositMassRequest):
    from sparkai.agent.agent_consciousness_stratum_former import AgentConsciousnessStratumFormer
    former = AgentConsciousnessStratumFormer.get_instance()
    result = former.set_deposit_mass(deposit_id, req.mass)
    if "error" in result:
        return {"status": "error", "detail": result["error"]}
    return {"status": "ok", "data": result}


@router.get("/consciousness-stratum/crystals/{crystal_id}")
async def consciousness_stratum_get_crystal(crystal_id: str):
    from sparkai.agent.agent_consciousness_stratum_former import AgentConsciousnessStratumFormer
    former = AgentConsciousnessStratumFormer.get_instance()
    result = former.get_crystal(crystal_id)
    if "error" in result:
        return {"status": "error", "detail": result["error"]}
    return {"status": "ok", "data": result}


@router.get("/consciousness-stratum/crystals")
async def consciousness_stratum_list_crystals(
    layer: Optional[str] = Query(None),
    limit: int = Query(30, ge=1, le=100),
):
    from sparkai.agent.agent_consciousness_stratum_former import AgentConsciousnessStratumFormer
    former = AgentConsciousnessStratumFormer.get_instance()
    return {"status": "ok", "data": former.list_crystals(layer, limit)}


@router.delete("/consciousness-stratum/crystals/{crystal_id}")
async def consciousness_stratum_remove_crystal(crystal_id: str):
    from sparkai.agent.agent_consciousness_stratum_former import AgentConsciousnessStratumFormer
    former = AgentConsciousnessStratumFormer.get_instance()
    result = former.remove_crystal(crystal_id)
    return {"status": "ok", "data": result}


@router.get("/consciousness-stratum/faults/{fault_id}")
async def consciousness_stratum_get_fault(fault_id: str):
    from sparkai.agent.agent_consciousness_stratum_former import AgentConsciousnessStratumFormer
    former = AgentConsciousnessStratumFormer.get_instance()
    result = former.get_fault(fault_id)
    if "error" in result:
        return {"status": "error", "detail": result["error"]}
    return {"status": "ok", "data": result}


@router.get("/consciousness-stratum/faults")
async def consciousness_stratum_list_faults(limit: int = Query(30, ge=1, le=100)):
    from sparkai.agent.agent_consciousness_stratum_former import AgentConsciousnessStratumFormer
    former = AgentConsciousnessStratumFormer.get_instance()
    return {"status": "ok", "data": former.list_faults(limit)}


@router.post("/consciousness-stratum/cycle")
async def consciousness_stratum_run_cycle():
    from sparkai.agent.agent_consciousness_stratum_former import AgentConsciousnessStratumFormer
    former = AgentConsciousnessStratumFormer.get_instance()
    return {"status": "ok", "data": former.run_cycle()}


@router.post("/consciousness-stratum/simulate")
async def consciousness_stratum_simulate(req: SimulateStratumRequest):
    from sparkai.agent.agent_consciousness_stratum_former import AgentConsciousnessStratumFormer
    former = AgentConsciousnessStratumFormer.get_instance()
    cycles = max(1, min(100, int(req.cycles)))
    return {"status": "ok", "data": former.simulate(cycles)}


@router.get("/consciousness-stratum/events")
async def consciousness_stratum_get_events(
    layer: Optional[str] = Query(None),
    limit: int = Query(20, ge=1, le=100),
):
    from sparkai.agent.agent_consciousness_stratum_former import AgentConsciousnessStratumFormer
    former = AgentConsciousnessStratumFormer.get_instance()
    return {"status": "ok", "data": former.get_events(layer, limit)}


@router.post("/consciousness-stratum/reset")
async def consciousness_stratum_reset():
    from sparkai.agent.agent_consciousness_stratum_former import AgentConsciousnessStratumFormer
    former = AgentConsciousnessStratumFormer.get_instance()
    return {"status": "ok", "data": former.reset()}


# =============================================================================
# Probability Mist Routes
# =============================================================================

@router.get("/probability-mist/status")
async def probability_mist_status():
    from sparkai.engine.engine_probability_mist_diffuser import EngineProbabilityMistDiffuser
    diffuser = EngineProbabilityMistDiffuser.get_instance()
    return {"status": "ok", "data": diffuser.get_status()}


@router.post("/probability-mist/regions")
async def probability_mist_register_region(req: RegisterMistRegionRequest):
    from sparkai.engine.engine_probability_mist_diffuser import EngineProbabilityMistDiffuser
    diffuser = EngineProbabilityMistDiffuser.get_instance()
    result = diffuser.register_region(
        req.region_id, req.label, req.mist_type,
        req.density, req.viscosity, req.volatility, req.is_source,
    )
    if "error" in result:
        return {"status": "error", "detail": result["error"]}
    return {"status": "ok", "data": result}


@router.get("/probability-mist/regions/{region_id}")
async def probability_mist_get_region(region_id: str):
    from sparkai.engine.engine_probability_mist_diffuser import EngineProbabilityMistDiffuser
    diffuser = EngineProbabilityMistDiffuser.get_instance()
    result = diffuser.get_region(region_id)
    if "error" in result:
        return {"status": "error", "detail": result["error"]}
    return {"status": "ok", "data": result}


@router.get("/probability-mist/regions")
async def probability_mist_list_regions():
    from sparkai.engine.engine_probability_mist_diffuser import EngineProbabilityMistDiffuser
    diffuser = EngineProbabilityMistDiffuser.get_instance()
    return {"status": "ok", "data": diffuser.list_regions()}


@router.delete("/probability-mist/regions/{region_id}")
async def probability_mist_remove_region(region_id: str):
    from sparkai.engine.engine_probability_mist_diffuser import EngineProbabilityMistDiffuser
    diffuser = EngineProbabilityMistDiffuser.get_instance()
    result = diffuser.remove_region(region_id)
    return {"status": "ok", "data": result}


@router.put("/probability-mist/regions/{region_id}/density")
async def probability_mist_set_density(region_id: str, req: SetMistDensityRequest):
    from sparkai.engine.engine_probability_mist_diffuser import EngineProbabilityMistDiffuser
    diffuser = EngineProbabilityMistDiffuser.get_instance()
    result = diffuser.set_region_density(region_id, req.density, req.description)
    if "error" in result:
        return {"status": "error", "detail": result["error"]}
    return {"status": "ok", "data": result}


@router.post("/probability-mist/regions/{region_id}/links")
async def probability_mist_link_regions(region_id: str, req: LinkMistRegionsRequest):
    from sparkai.engine.engine_probability_mist_diffuser import EngineProbabilityMistDiffuser
    diffuser = EngineProbabilityMistDiffuser.get_instance()
    result = diffuser.link_regions(region_id, req.target_id, req.flow_rate)
    if "error" in result:
        return {"status": "error", "detail": result["error"]}
    return {"status": "ok", "data": result}


@router.delete("/probability-mist/regions/{region_id}/links/{target_id}")
async def probability_mist_unlink_regions(region_id: str, target_id: str):
    from sparkai.engine.engine_probability_mist_diffuser import EngineProbabilityMistDiffuser
    diffuser = EngineProbabilityMistDiffuser.get_instance()
    result = diffuser.unlink_regions(region_id, target_id)
    return {"status": "ok", "data": result}


@router.get("/probability-mist/regions/{region_id}/links")
async def probability_mist_get_links(region_id: str):
    from sparkai.engine.engine_probability_mist_diffuser import EngineProbabilityMistDiffuser
    diffuser = EngineProbabilityMistDiffuser.get_instance()
    result = diffuser.get_channels(region_id)
    if "error" in result:
        return {"status": "error", "detail": result["error"]}
    return {"status": "ok", "data": result}


@router.post("/probability-mist/cycle")
async def probability_mist_run_cycle():
    from sparkai.engine.engine_probability_mist_diffuser import EngineProbabilityMistDiffuser
    diffuser = EngineProbabilityMistDiffuser.get_instance()
    return {"status": "ok", "data": diffuser.run_cycle()}


@router.post("/probability-mist/simulate")
async def probability_mist_simulate(req: SimulateMistRequest):
    from sparkai.engine.engine_probability_mist_diffuser import EngineProbabilityMistDiffuser
    diffuser = EngineProbabilityMistDiffuser.get_instance()
    cycles = max(1, min(100, int(req.cycles)))
    return {"status": "ok", "data": diffuser.simulate(cycles)}


@router.get("/probability-mist/events")
async def probability_mist_get_events(
    region_id: Optional[str] = Query(None),
    limit: int = Query(20, ge=1, le=100),
):
    from sparkai.engine.engine_probability_mist_diffuser import EngineProbabilityMistDiffuser
    diffuser = EngineProbabilityMistDiffuser.get_instance()
    return {"status": "ok", "data": diffuser.get_events(region_id, limit)}


@router.get("/probability-mist/outcomes")
async def probability_mist_get_outcomes(limit: int = Query(20, ge=1, le=100)):
    from sparkai.engine.engine_probability_mist_diffuser import EngineProbabilityMistDiffuser
    diffuser = EngineProbabilityMistDiffuser.get_instance()
    return {"status": "ok", "data": diffuser.get_outcomes(limit)}


@router.post("/probability-mist/reset")
async def probability_mist_reset():
    from sparkai.engine.engine_probability_mist_diffuser import EngineProbabilityMistDiffuser
    diffuser = EngineProbabilityMistDiffuser.get_instance()
    return {"status": "ok", "data": diffuser.reset()}
