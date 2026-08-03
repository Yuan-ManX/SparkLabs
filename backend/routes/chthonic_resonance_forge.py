"""
SparkLabs Backend - Chthonic Resonance Forge Routes

REST endpoints for the Chthonic Resonance Forge engine.
"""
from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional

router = APIRouter()  # NO prefix here - prefix added in app.py


# =============================================================================
# Request Models
# =============================================================================

class RegisterResonanceRequest(BaseModel):
    entity_id: str
    label: str
    depth: float = 100.0
    fundamental_frequency: float = 7.83
    harmonic_amplitude: float = 0.5
    resonance_class: Optional[str] = None    # bedrock/magma/tectonic/crystalline/void
    note: str = ""


class ForgeResonanceRequest(BaseModel):
    resonance_id: str
    target_depth: Optional[float] = None
    target_frequency: Optional[float] = None


# =============================================================================
# Routes
# =============================================================================

@router.post("/chthonic-resonance-forge/register")
async def crf_register(req: RegisterResonanceRequest):
    from sparkai.engine.engine_chthonic_resonance_forge import (
        ChthonicResonanceForge,
    )
    forge = ChthonicResonanceForge.get_instance()
    result = forge.register_resonance(
        entity_id=req.entity_id,
        label=req.label,
        depth=req.depth,
        fundamental_frequency=req.fundamental_frequency,
        harmonic_amplitude=req.harmonic_amplitude,
        resonance_class=req.resonance_class,
        note=req.note,
    )
    if "error" in result:
        return {"status": "error", "detail": result["error"]}
    return {"status": "ok", "data": result}


@router.get("/chthonic-resonance-forge/status")
async def crf_status():
    from sparkai.engine.engine_chthonic_resonance_forge import (
        ChthonicResonanceForge,
    )
    forge = ChthonicResonanceForge.get_instance()
    return {"status": "ok", "data": forge.get_status()}


@router.get("/chthonic-resonance-forge/list")
async def crf_list(limit: int = 10):
    from sparkai.engine.engine_chthonic_resonance_forge import (
        ChthonicResonanceForge,
    )
    forge = ChthonicResonanceForge.get_instance()
    return {"status": "ok", "data": forge.get_resonances(limit=limit)}


@router.get("/chthonic-resonance-forge/get-by-id/{resonance_id}")
async def crf_get_by_id(resonance_id: str):
    from sparkai.engine.engine_chthonic_resonance_forge import (
        ChthonicResonanceForge,
    )
    forge = ChthonicResonanceForge.get_instance()
    result = forge.get_resonance(resonance_id)
    if "error" in result:
        return {"status": "error", "detail": result["error"]}
    return {"status": "ok", "data": result}


@router.post("/chthonic-resonance-forge/cycle")
async def crf_cycle():
    from sparkai.engine.engine_chthonic_resonance_forge import (
        ChthonicResonanceForge,
    )
    forge = ChthonicResonanceForge.get_instance()
    return {"status": "ok", "data": forge.cycle()}


@router.get("/chthonic-resonance-forge/events")
async def crf_events(limit: int = 20):
    from sparkai.engine.engine_chthonic_resonance_forge import (
        ChthonicResonanceForge,
    )
    forge = ChthonicResonanceForge.get_instance()
    return {"status": "ok", "data": forge.get_events_log(limit=limit)}


@router.post("/chthonic-resonance-forge/simulate")
async def crf_simulate(cycles: int = 5):
    from sparkai.engine.engine_chthonic_resonance_forge import (
        ChthonicResonanceForge,
    )
    forge = ChthonicResonanceForge.get_instance()
    return {"status": "ok", "data": forge.simulate(cycles=cycles)}


@router.post("/chthonic-resonance-forge/reset")
async def crf_reset():
    from sparkai.engine.engine_chthonic_resonance_forge import (
        ChthonicResonanceForge,
    )
    forge = ChthonicResonanceForge.get_instance()
    return {"status": "ok", "data": forge.reset()}


@router.post("/chthonic-resonance-forge/forge")
async def crf_forge(req: ForgeResonanceRequest):
    from sparkai.engine.engine_chthonic_resonance_forge import (
        ChthonicResonanceForge,
    )
    forge = ChthonicResonanceForge.get_instance()
    result = forge.forge_resonance(
        resonance_id=req.resonance_id,
        target_depth=req.target_depth,
        target_frequency=req.target_frequency,
    )
    if "error" in result:
        return {"status": "error", "detail": result["error"]}
    return {"status": "ok", "data": result}
