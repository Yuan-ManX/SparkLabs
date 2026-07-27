"""
SparkLabs Backend - Reality Substrate Routes

REST API endpoints for the EngineRealitySubstrateField, the foundational
coherence layer that measures alignment across engine and cognition
subsystems.
"""

from __future__ import annotations

from fastapi import APIRouter, Query
from pydantic import BaseModel
from typing import Any, Dict, List, Optional

router = APIRouter()


# =============================================================================
# Request Models
# =============================================================================

class RegisterResonatorRequest(BaseModel):
    resonator_id: str
    domain: str = "custom"
    label: str
    frequency: float = 1.0
    amplitude: float = 0.5
    damping: float = 0.05
    coupling: float = 0.3


class LinkResonatorsRequest(BaseModel):
    target_id: str
    strength: float = 0.5
    phase_offset: float = 0.0


class EmitPulseRequest(BaseModel):
    pulse_type: str
    amplitude: float = 0.5


class SimulateRequest(BaseModel):
    cycles: int = 10


class SetAmplitudeRequest(BaseModel):
    amplitude: float


class PinRequest(BaseModel):
    pinned: bool = True


# =============================================================================
# Routes
# =============================================================================

@router.get("/reality-substrate/status")
async def substrate_status():
    from sparkai.engine.engine_reality_substrate_field import EngineRealitySubstrateField
    substrate = EngineRealitySubstrateField.get_instance()
    return {"status": "ok", "data": substrate.get_status()}


@router.post("/reality-substrate/resonators")
async def substrate_register(req: RegisterResonatorRequest):
    from sparkai.engine.engine_reality_substrate_field import (
        EngineRealitySubstrateField, ResonatorDomain,
    )
    substrate = EngineRealitySubstrateField.get_instance()
    try:
        domain = ResonatorDomain(req.domain)
    except ValueError:
        domain = ResonatorDomain.CUSTOM
    result = substrate.register_resonator(
        resonator_id=req.resonator_id,
        domain=domain,
        label=req.label,
        frequency=req.frequency,
        amplitude=req.amplitude,
        damping=req.damping,
        coupling=req.coupling,
    )
    if "error" in result:
        return {"status": "error", "detail": result["error"]}
    return {"status": "ok", "data": result}


@router.delete("/reality-substrate/resonators/{resonator_id}")
async def substrate_remove(resonator_id: str):
    from sparkai.engine.engine_reality_substrate_field import EngineRealitySubstrateField
    substrate = EngineRealitySubstrateField.get_instance()
    result = substrate.remove_resonator(resonator_id)
    if "error" in result:
        return {"status": "error", "detail": result["error"]}
    return {"status": "ok", "data": result}


@router.get("/reality-substrate/resonators")
async def substrate_list_resonators(limit: int = Query(50, ge=1, le=200)):
    from sparkai.engine.engine_reality_substrate_field import EngineRealitySubstrateField
    substrate = EngineRealitySubstrateField.get_instance()
    return {"status": "ok", "data": substrate.list_resonators(limit)}


@router.get("/reality-substrate/resonators/{resonator_id}")
async def substrate_get_resonator(resonator_id: str):
    from sparkai.engine.engine_reality_substrate_field import EngineRealitySubstrateField
    substrate = EngineRealitySubstrateField.get_instance()
    data = substrate.get_resonator(resonator_id)
    if data is None:
        return {"status": "error", "detail": f"Resonator not found: {resonator_id}"}
    return {"status": "ok", "data": data}


@router.post("/reality-substrate/resonators/{source_id}/links")
async def substrate_link(source_id: str, req: LinkResonatorsRequest):
    from sparkai.engine.engine_reality_substrate_field import EngineRealitySubstrateField
    substrate = EngineRealitySubstrateField.get_instance()
    result = substrate.link_resonators(
        source_id=source_id,
        target_id=req.target_id,
        strength=req.strength,
        phase_offset=req.phase_offset,
    )
    if "error" in result:
        return {"status": "error", "detail": result["error"]}
    return {"status": "ok", "data": result}


@router.delete("/reality-substrate/links/{source_id}/{target_id}")
async def substrate_unlink(source_id: str, target_id: str):
    from sparkai.engine.engine_reality_substrate_field import EngineRealitySubstrateField
    substrate = EngineRealitySubstrateField.get_instance()
    result = substrate.unlink_resonators(source_id, target_id)
    if "error" in result:
        return {"status": "error", "detail": result["error"]}
    return {"status": "ok", "data": result}


@router.get("/reality-substrate/links")
async def substrate_list_links(limit: int = Query(50, ge=1, le=200)):
    from sparkai.engine.engine_reality_substrate_field import EngineRealitySubstrateField
    substrate = EngineRealitySubstrateField.get_instance()
    return {"status": "ok", "data": substrate.list_links(limit)}


@router.post("/reality-substrate/resonators/{resonator_id}/pulses")
async def substrate_emit_pulse(resonator_id: str, req: EmitPulseRequest):
    from sparkai.engine.engine_reality_substrate_field import (
        EngineRealitySubstrateField, PulseType,
    )
    substrate = EngineRealitySubstrateField.get_instance()
    try:
        pulse_type = PulseType(req.pulse_type)
    except ValueError:
        return {"status": "error", "detail": f"Unknown pulse type: {req.pulse_type}"}
    result = substrate.emit_pulse(resonator_id, pulse_type, req.amplitude)
    if "error" in result:
        return {"status": "error", "detail": result["error"]}
    return {"status": "ok", "data": result}


@router.get("/reality-substrate/pulses")
async def substrate_list_pulses(limit: int = Query(30, ge=1, le=200)):
    from sparkai.engine.engine_reality_substrate_field import EngineRealitySubstrateField
    substrate = EngineRealitySubstrateField.get_instance()
    return {"status": "ok", "data": substrate.list_pulses(limit)}


@router.post("/reality-substrate/cycle")
async def substrate_cycle():
    from sparkai.engine.engine_reality_substrate_field import EngineRealitySubstrateField
    substrate = EngineRealitySubstrateField.get_instance()
    return {"status": "ok", "data": substrate.cycle()}


@router.post("/reality-substrate/simulate")
async def substrate_simulate(req: SimulateRequest):
    from sparkai.engine.engine_reality_substrate_field import EngineRealitySubstrateField
    substrate = EngineRealitySubstrateField.get_instance()
    return {"status": "ok", "data": substrate.simulate(req.cycles)}


@router.get("/reality-substrate/coherence-history")
async def substrate_coherence_history(limit: int = Query(50, ge=1, le=200)):
    from sparkai.engine.engine_reality_substrate_field import EngineRealitySubstrateField
    substrate = EngineRealitySubstrateField.get_instance()
    return {"status": "ok", "data": substrate.get_coherence_history(limit)}


@router.get("/reality-substrate/domain-summary")
async def substrate_domain_summary():
    from sparkai.engine.engine_reality_substrate_field import EngineRealitySubstrateField
    substrate = EngineRealitySubstrateField.get_instance()
    return {"status": "ok", "data": substrate.get_domain_summary()}


@router.put("/reality-substrate/resonators/{resonator_id}/amplitude")
async def substrate_set_amplitude(resonator_id: str, req: SetAmplitudeRequest):
    from sparkai.engine.engine_reality_substrate_field import EngineRealitySubstrateField
    substrate = EngineRealitySubstrateField.get_instance()
    result = substrate.set_resonator_amplitude(resonator_id, req.amplitude)
    if "error" in result:
        return {"status": "error", "detail": result["error"]}
    return {"status": "ok", "data": result}


@router.put("/reality-substrate/resonators/{resonator_id}/pin")
async def substrate_pin(resonator_id: str, req: PinRequest):
    from sparkai.engine.engine_reality_substrate_field import EngineRealitySubstrateField
    substrate = EngineRealitySubstrateField.get_instance()
    result = substrate.pin_resonator(resonator_id, req.pinned)
    if "error" in result:
        return {"status": "error", "detail": result["error"]}
    return {"status": "ok", "data": result}


@router.get("/reality-substrate/events")
async def substrate_events(limit: int = Query(50, ge=1, le=200)):
    from sparkai.engine.engine_reality_substrate_field import EngineRealitySubstrateField
    substrate = EngineRealitySubstrateField.get_instance()
    return {"status": "ok", "data": substrate.get_events(limit)}


@router.post("/reality-substrate/reset")
async def substrate_reset():
    from sparkai.engine.engine_reality_substrate_field import EngineRealitySubstrateField
    substrate = EngineRealitySubstrateField.get_instance()
    return {"status": "ok", "data": substrate.reset()}
