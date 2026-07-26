"""
SparkLabs Backend - Emotional Resonance & Temporal Flow Routes

REST API endpoints for:
  - AgentEmotionalResonanceField: NPC emotions as acoustic wave phenomena
  - EngineTemporalFlowRegulator: game time as fluid medium

Routes use /emotional-resonance/ and /temporal-flow/ prefixes.
"""

from __future__ import annotations

from fastapi import APIRouter, Query
from pydantic import BaseModel
from typing import Any, Dict, List, Optional

router = APIRouter()


# =============================================================================
# Request Models - Emotional Resonance
# =============================================================================

class RegisterNPCRequest(BaseModel):
    npc_id: str
    initial_emotions: Optional[Dict[str, float]] = None


class CoupleNPCsRequest(BaseModel):
    target_id: str
    coupling_strength: float = 0.5
    is_amplifier: bool = True


class EmitEmotionRequest(BaseModel):
    emotion: str
    amplitude: float = 0.5


class SimulateResonanceRequest(BaseModel):
    cycles: int = 10


# =============================================================================
# Request Models - Temporal Flow
# =============================================================================

class RegisterRegionRequest(BaseModel):
    region_id: str
    label: str
    region_type: str = "normal"
    flow_rate: Optional[float] = None
    viscosity: Optional[float] = None
    density: Optional[float] = None


class SetFlowRateRequest(BaseModel):
    flow_rate: float
    description: str = ""


class LinkRegionsRequest(BaseModel):
    target_id: str
    flow_differential: float = 0.1


class SimulateTemporalRequest(BaseModel):
    cycles: int = 10


# =============================================================================
# Emotional Resonance Routes
# =============================================================================

@router.get("/emotional-resonance/status")
async def emotional_resonance_status():
    from sparkai.agent.agent_emotional_resonance_field import AgentEmotionalResonanceField
    field = AgentEmotionalResonanceField.get_instance()
    return {"status": "ok", "data": field.get_status()}


@router.post("/emotional-resonance/npcs")
async def emotional_resonance_register_npc(req: RegisterNPCRequest):
    from sparkai.agent.agent_emotional_resonance_field import AgentEmotionalResonanceField
    field = AgentEmotionalResonanceField.get_instance()
    result = field.register_npc(req.npc_id, req.initial_emotions)
    if "error" in result:
        return {"status": "error", "detail": result["error"]}
    return {"status": "ok", "data": result}


@router.get("/emotional-resonance/npcs/{npc_id}")
async def emotional_resonance_get_npc(npc_id: str):
    from sparkai.agent.agent_emotional_resonance_field import AgentEmotionalResonanceField
    field = AgentEmotionalResonanceField.get_instance()
    result = field.get_npc(npc_id)
    if "error" in result:
        return {"status": "error", "detail": result["error"]}
    return {"status": "ok", "data": result}


@router.get("/emotional-resonance/npcs")
async def emotional_resonance_list_npcs(limit: int = Query(20, ge=1, le=100)):
    from sparkai.agent.agent_emotional_resonance_field import AgentEmotionalResonanceField
    field = AgentEmotionalResonanceField.get_instance()
    return {"status": "ok", "data": field.list_npcs(limit)}


@router.delete("/emotional-resonance/npcs/{npc_id}")
async def emotional_resonance_remove_npc(npc_id: str):
    from sparkai.agent.agent_emotional_resonance_field import AgentEmotionalResonanceField
    field = AgentEmotionalResonanceField.get_instance()
    result = field.remove_npc(npc_id)
    return {"status": "ok", "data": result}


@router.post("/emotional-resonance/npcs/{npc_id}/couplings")
async def emotional_resonance_couple_npcs(npc_id: str, req: CoupleNPCsRequest):
    from sparkai.agent.agent_emotional_resonance_field import AgentEmotionalResonanceField
    field = AgentEmotionalResonanceField.get_instance()
    result = field.couple_npcs(npc_id, req.target_id, req.coupling_strength, req.is_amplifier)
    if "error" in result:
        return {"status": "error", "detail": result["error"]}
    return {"status": "ok", "data": result}


@router.delete("/emotional-resonance/npcs/{npc_id}/couplings/{target_id}")
async def emotional_resonance_uncouple_npcs(npc_id: str, target_id: str):
    from sparkai.agent.agent_emotional_resonance_field import AgentEmotionalResonanceField
    field = AgentEmotionalResonanceField.get_instance()
    result = field.uncouple_npcs(npc_id, target_id)
    if "error" in result:
        return {"status": "error", "detail": result["error"]}
    return {"status": "ok", "data": result}


@router.get("/emotional-resonance/npcs/{npc_id}/couplings")
async def emotional_resonance_get_couplings(npc_id: str):
    from sparkai.agent.agent_emotional_resonance_field import AgentEmotionalResonanceField
    field = AgentEmotionalResonanceField.get_instance()
    result = field.get_couplings(npc_id)
    if "error" in result:
        return {"status": "error", "detail": result["error"]}
    return {"status": "ok", "data": result}


@router.post("/emotional-resonance/npcs/{npc_id}/emotions")
async def emotional_resonance_emit_emotion(npc_id: str, req: EmitEmotionRequest):
    from sparkai.agent.agent_emotional_resonance_field import AgentEmotionalResonanceField
    field = AgentEmotionalResonanceField.get_instance()
    result = field.emit_emotion(npc_id, req.emotion, req.amplitude)
    if "error" in result:
        return {"status": "error", "detail": result["error"]}
    return {"status": "ok", "data": result}


@router.post("/emotional-resonance/cycle")
async def emotional_resonance_run_cycle():
    from sparkai.agent.agent_emotional_resonance_field import AgentEmotionalResonanceField
    field = AgentEmotionalResonanceField.get_instance()
    return {"status": "ok", "data": field.run_cycle()}


@router.post("/emotional-resonance/simulate")
async def emotional_resonance_simulate(req: SimulateResonanceRequest):
    from sparkai.agent.agent_emotional_resonance_field import AgentEmotionalResonanceField
    field = AgentEmotionalResonanceField.get_instance()
    cycles = max(1, min(100, int(req.cycles)))
    return {"status": "ok", "data": field.simulate(cycles)}


@router.get("/emotional-resonance/interactions")
async def emotional_resonance_get_interactions(
    npc_id: Optional[str] = Query(None),
    limit: int = Query(20, ge=1, le=100),
):
    from sparkai.agent.agent_emotional_resonance_field import AgentEmotionalResonanceField
    field = AgentEmotionalResonanceField.get_instance()
    return {"status": "ok", "data": field.get_interactions(npc_id, limit)}


@router.get("/emotional-resonance/chords")
async def emotional_resonance_get_chords(
    npc_id: Optional[str] = Query(None),
    limit: int = Query(20, ge=1, le=100),
):
    from sparkai.agent.agent_emotional_resonance_field import AgentEmotionalResonanceField
    field = AgentEmotionalResonanceField.get_instance()
    return {"status": "ok", "data": field.get_chords(npc_id, limit)}


@router.post("/emotional-resonance/reset")
async def emotional_resonance_reset():
    from sparkai.agent.agent_emotional_resonance_field import AgentEmotionalResonanceField
    field = AgentEmotionalResonanceField.get_instance()
    return {"status": "ok", "data": field.reset()}


# =============================================================================
# Temporal Flow Routes
# =============================================================================

@router.get("/temporal-flow/status")
async def temporal_flow_status():
    from sparkai.engine.engine_temporal_flow_regulator import EngineTemporalFlowRegulator
    regulator = EngineTemporalFlowRegulator.get_instance()
    return {"status": "ok", "data": regulator.get_status()}


@router.post("/temporal-flow/regions")
async def temporal_flow_register_region(req: RegisterRegionRequest):
    from sparkai.engine.engine_temporal_flow_regulator import EngineTemporalFlowRegulator
    regulator = EngineTemporalFlowRegulator.get_instance()
    result = regulator.register_region(
        req.region_id, req.label, req.region_type,
        req.flow_rate, req.viscosity, req.density,
    )
    if "error" in result:
        return {"status": "error", "detail": result["error"]}
    return {"status": "ok", "data": result}


@router.get("/temporal-flow/regions/{region_id}")
async def temporal_flow_get_region(region_id: str):
    from sparkai.engine.engine_temporal_flow_regulator import EngineTemporalFlowRegulator
    regulator = EngineTemporalFlowRegulator.get_instance()
    result = regulator.get_region(region_id)
    if "error" in result:
        return {"status": "error", "detail": result["error"]}
    return {"status": "ok", "data": result}


@router.get("/temporal-flow/regions")
async def temporal_flow_list_regions():
    from sparkai.engine.engine_temporal_flow_regulator import EngineTemporalFlowRegulator
    regulator = EngineTemporalFlowRegulator.get_instance()
    return {"status": "ok", "data": regulator.list_regions()}


@router.delete("/temporal-flow/regions/{region_id}")
async def temporal_flow_remove_region(region_id: str):
    from sparkai.engine.engine_temporal_flow_regulator import EngineTemporalFlowRegulator
    regulator = EngineTemporalFlowRegulator.get_instance()
    result = regulator.remove_region(region_id)
    if "error" in result:
        return {"status": "error", "detail": result["error"]}
    return {"status": "ok", "data": result}


@router.put("/temporal-flow/regions/{region_id}/flow-rate")
async def temporal_flow_set_flow_rate(region_id: str, req: SetFlowRateRequest):
    from sparkai.engine.engine_temporal_flow_regulator import EngineTemporalFlowRegulator
    regulator = EngineTemporalFlowRegulator.get_instance()
    result = regulator.set_flow_rate(region_id, req.flow_rate, req.description)
    if "error" in result:
        return {"status": "error", "detail": result["error"]}
    return {"status": "ok", "data": result}


@router.post("/temporal-flow/regions/{region_id}/links")
async def temporal_flow_link_regions(region_id: str, req: LinkRegionsRequest):
    from sparkai.engine.engine_temporal_flow_regulator import EngineTemporalFlowRegulator
    regulator = EngineTemporalFlowRegulator.get_instance()
    result = regulator.link_regions(region_id, req.target_id, req.flow_differential)
    if "error" in result:
        return {"status": "error", "detail": result["error"]}
    return {"status": "ok", "data": result}


@router.delete("/temporal-flow/regions/{region_id}/links/{target_id}")
async def temporal_flow_unlink_regions(region_id: str, target_id: str):
    from sparkai.engine.engine_temporal_flow_regulator import EngineTemporalFlowRegulator
    regulator = EngineTemporalFlowRegulator.get_instance()
    result = regulator.unlink_regions(region_id, target_id)
    if "error" in result:
        return {"status": "error", "detail": result["error"]}
    return {"status": "ok", "data": result}


@router.get("/temporal-flow/regions/{region_id}/links")
async def temporal_flow_get_links(region_id: str):
    from sparkai.engine.engine_temporal_flow_regulator import EngineTemporalFlowRegulator
    regulator = EngineTemporalFlowRegulator.get_instance()
    result = regulator.get_currents(region_id)
    if "error" in result:
        return {"status": "error", "detail": result["error"]}
    return {"status": "ok", "data": result}


@router.post("/temporal-flow/cycle")
async def temporal_flow_run_cycle():
    from sparkai.engine.engine_temporal_flow_regulator import EngineTemporalFlowRegulator
    regulator = EngineTemporalFlowRegulator.get_instance()
    return {"status": "ok", "data": regulator.run_cycle()}


@router.post("/temporal-flow/simulate")
async def temporal_flow_simulate(req: SimulateTemporalRequest):
    from sparkai.engine.engine_temporal_flow_regulator import EngineTemporalFlowRegulator
    regulator = EngineTemporalFlowRegulator.get_instance()
    cycles = max(1, min(100, int(req.cycles)))
    return {"status": "ok", "data": regulator.simulate(cycles)}


@router.get("/temporal-flow/events")
async def temporal_flow_get_events(
    region_id: Optional[str] = Query(None),
    limit: int = Query(20, ge=1, le=100),
):
    from sparkai.engine.engine_temporal_flow_regulator import EngineTemporalFlowRegulator
    regulator = EngineTemporalFlowRegulator.get_instance()
    return {"status": "ok", "data": regulator.get_events(region_id, limit)}


@router.post("/temporal-flow/reset")
async def temporal_flow_reset():
    from sparkai.engine.engine_temporal_flow_regulator import EngineTemporalFlowRegulator
    regulator = EngineTemporalFlowRegulator.get_instance()
    return {"status": "ok", "data": regulator.reset()}
