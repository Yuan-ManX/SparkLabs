"""
SparkLabs Backend - Perceptual Grain Modulator Routes

REST endpoints for the Engine Perceptual Grain Modulator.
"""
from fastapi import APIRouter
from pydantic import BaseModel
from typing import Any, Dict, List, Optional

router = APIRouter()


# =============================================================================
# Request Models
# =============================================================================

class RegisterSceneRequest(BaseModel):
    scene_id: str


class ReportDemandRequest(BaseModel):
    signal: str                          # attention_load/emotional_weight/narrative_velocity/sensorimotor_demand/scene_density
    value: float = 0.5                   # 0.0-1.0
    note: str = ""


class SimulateRequest(BaseModel):
    cycles: int = 5


# =============================================================================
# Routes
# =============================================================================

@router.post("/perceptual-grain-modulator/scenes")
async def grain_register_scene(req: RegisterSceneRequest):
    from sparkai.engine.engine_perceptual_grain_modulator import (
        EnginePerceptualGrainModulator,
    )
    modulator = EnginePerceptualGrainModulator.get_instance()
    result = modulator.register_scene(scene_id=req.scene_id)
    if "error" in result:
        return {"status": "error", "detail": result["error"]}
    return {"status": "ok", "data": result}


@router.post("/perceptual-grain-modulator/scenes/{scene_id}/demand")
async def grain_report_demand(scene_id: str, req: ReportDemandRequest):
    from sparkai.engine.engine_perceptual_grain_modulator import (
        EnginePerceptualGrainModulator,
    )
    modulator = EnginePerceptualGrainModulator.get_instance()
    result = modulator.report_demand(
        scene_id=scene_id,
        signal=req.signal,
        value=req.value,
        note=req.note,
    )
    if "error" in result:
        return {"status": "error", "detail": result["error"]}
    return {"status": "ok", "data": result}


@router.post("/perceptual-grain-modulator/cycle")
async def grain_cycle():
    from sparkai.engine.engine_perceptual_grain_modulator import (
        EnginePerceptualGrainModulator,
    )
    modulator = EnginePerceptualGrainModulator.get_instance()
    return {"status": "ok", "data": modulator.cycle()}


@router.get("/perceptual-grain-modulator/scenes/{scene_id}/signature")
async def grain_get_signature(scene_id: str):
    from sparkai.engine.engine_perceptual_grain_modulator import (
        EnginePerceptualGrainModulator,
    )
    modulator = EnginePerceptualGrainModulator.get_instance()
    result = modulator.get_signature(scene_id)
    if "error" in result:
        return {"status": "error", "detail": result["error"]}
    return {"status": "ok", "data": result}


@router.get("/perceptual-grain-modulator/status")
async def grain_get_status():
    from sparkai.engine.engine_perceptual_grain_modulator import (
        EnginePerceptualGrainModulator,
    )
    modulator = EnginePerceptualGrainModulator.get_instance()
    return {"status": "ok", "data": modulator.get_status()}


@router.get("/perceptual-grain-modulator/scenes")
async def grain_get_scenes():
    from sparkai.engine.engine_perceptual_grain_modulator import (
        EnginePerceptualGrainModulator,
    )
    modulator = EnginePerceptualGrainModulator.get_instance()
    return {"status": "ok", "data": modulator.get_scenes()}


@router.get("/perceptual-grain-modulator/events")
async def grain_get_events(limit: int = 50):
    from sparkai.engine.engine_perceptual_grain_modulator import (
        EnginePerceptualGrainModulator,
    )
    modulator = EnginePerceptualGrainModulator.get_instance()
    return {"status": "ok", "data": modulator.get_events_log(limit=limit)}


@router.post("/perceptual-grain-modulator/simulate")
async def grain_simulate(req: SimulateRequest):
    from sparkai.engine.engine_perceptual_grain_modulator import (
        EnginePerceptualGrainModulator,
    )
    modulator = EnginePerceptualGrainModulator.get_instance()
    return {"status": "ok", "data": modulator.simulate(cycles=req.cycles)}


@router.post("/perceptual-grain-modulator/reset")
async def grain_reset():
    from sparkai.engine.engine_perceptual_grain_modulator import (
        EnginePerceptualGrainModulator,
    )
    modulator = EnginePerceptualGrainModulator.get_instance()
    return {"status": "ok", "data": modulator.reset()}
