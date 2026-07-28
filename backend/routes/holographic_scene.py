"""
SparkLabs Backend - Holographic Scene Composer Routes

REST API endpoints for EngineHolographicSceneComposer: multi-layer semantic
scene projection with PROJECT/FOCUS/BLEND/REFRACT/RESOLVE cycle.
"""

from __future__ import annotations

from fastapi import APIRouter, Query
from pydantic import BaseModel
from typing import Any, Dict, List, Optional

router = APIRouter()


# =============================================================================
# Request Models
# =============================================================================

class RegisterLayerRequest(BaseModel):
    layer_id: str
    label: str
    layer_type: str
    intensity: float = 0.5
    frequency: float = 0.5
    weight: float = 1.0
    color: str = "#888888"
    description: str = ""


class SetIntensityRequest(BaseModel):
    intensity: float


class SetWeightRequest(BaseModel):
    weight: float


class RefractRequest(BaseModel):
    target_layer: str
    bend_factor: float = 0.3
    direction: str = "amplify"


class AddElementRequest(BaseModel):
    element_id: str
    label: str
    layer_ids: Optional[List[str]] = None
    position: List[float] = [0.0, 0.0, 0.0]
    properties: Optional[Dict[str, Any]] = None


class SimulateRequest(BaseModel):
    cycles: int = 10


# =============================================================================
# Layer Routes
# =============================================================================

@router.get("/holographic-scene/status")
async def holographic_scene_status():
    from sparkai.engine.engine_holographic_scene_composer import EngineHolographicSceneComposer
    composer = EngineHolographicSceneComposer.get_instance()
    return {"status": "ok", "data": composer.get_status()}


@router.post("/holographic-scene/layers")
async def holographic_scene_register_layer(req: RegisterLayerRequest):
    from sparkai.engine.engine_holographic_scene_composer import (
        EngineHolographicSceneComposer, SemanticLayerType,
    )
    composer = EngineHolographicSceneComposer.get_instance()
    try:
        lt = SemanticLayerType(req.layer_type)
    except ValueError:
        return {"status": "error", "detail": f"Invalid layer_type: {req.layer_type}"}
    result = composer.register_layer(
        layer_id=req.layer_id,
        label=req.label,
        layer_type=lt,
        intensity=req.intensity,
        frequency=req.frequency,
        weight=req.weight,
        color=req.color,
        description=req.description,
    )
    if "error" in result:
        return {"status": "error", "detail": result["error"]}
    return {"status": "ok", "data": result}


@router.get("/holographic-scene/layers")
async def holographic_scene_list_layers():
    from sparkai.engine.engine_holographic_scene_composer import EngineHolographicSceneComposer
    composer = EngineHolographicSceneComposer.get_instance()
    return {"status": "ok", "data": composer.list_layers()}


@router.get("/holographic-scene/layers/{layer_id}")
async def holographic_scene_get_layer(layer_id: str):
    from sparkai.engine.engine_holographic_scene_composer import EngineHolographicSceneComposer
    composer = EngineHolographicSceneComposer.get_instance()
    result = composer.get_layer(layer_id)
    if result is None:
        return {"status": "error", "detail": f"Layer not found: {layer_id}"}
    return {"status": "ok", "data": result}


@router.delete("/holographic-scene/layers/{layer_id}")
async def holographic_scene_remove_layer(layer_id: str):
    from sparkai.engine.engine_holographic_scene_composer import EngineHolographicSceneComposer
    composer = EngineHolographicSceneComposer.get_instance()
    result = composer.remove_layer(layer_id)
    if "error" in result:
        return {"status": "error", "detail": result["error"]}
    return {"status": "ok", "data": result}


@router.put("/holographic-scene/layers/{layer_id}/intensity")
async def holographic_scene_set_intensity(layer_id: str, req: SetIntensityRequest):
    from sparkai.engine.engine_holographic_scene_composer import EngineHolographicSceneComposer
    composer = EngineHolographicSceneComposer.get_instance()
    result = composer.set_layer_intensity(layer_id, req.intensity)
    if "error" in result:
        return {"status": "error", "detail": result["error"]}
    return {"status": "ok", "data": result}


@router.put("/holographic-scene/layers/{layer_id}/weight")
async def holographic_scene_set_weight(layer_id: str, req: SetWeightRequest):
    from sparkai.engine.engine_holographic_scene_composer import EngineHolographicSceneComposer
    composer = EngineHolographicSceneComposer.get_instance()
    result = composer.set_layer_weight(layer_id, req.weight)
    if "error" in result:
        return {"status": "error", "detail": result["error"]}
    return {"status": "ok", "data": result}


# =============================================================================
# Focus Routes
# =============================================================================

@router.post("/holographic-scene/focus/clear")
async def holographic_scene_clear_focus():
    from sparkai.engine.engine_holographic_scene_composer import EngineHolographicSceneComposer
    composer = EngineHolographicSceneComposer.get_instance()
    return {"status": "ok", "data": composer.clear_focus()}


@router.post("/holographic-scene/focus/{layer_id}")
async def holographic_scene_focus(layer_id: str):
    from sparkai.engine.engine_holographic_scene_composer import EngineHolographicSceneComposer
    composer = EngineHolographicSceneComposer.get_instance()
    result = composer.focus_layer(layer_id)
    if "error" in result:
        return {"status": "error", "detail": result["error"]}
    return {"status": "ok", "data": result}


# =============================================================================
# Refraction Routes
# =============================================================================

@router.post("/holographic-scene/layers/{source_layer}/refractions")
async def holographic_scene_refract(source_layer: str, req: RefractRequest):
    from sparkai.engine.engine_holographic_scene_composer import EngineHolographicSceneComposer
    composer = EngineHolographicSceneComposer.get_instance()
    result = composer.refract(
        source_layer=source_layer,
        target_layer=req.target_layer,
        bend_factor=req.bend_factor,
        direction=req.direction,
    )
    if "error" in result:
        return {"status": "error", "detail": result["error"]}
    return {"status": "ok", "data": result}


@router.delete("/holographic-scene/layers/{source_layer}/refractions/{target_layer}")
async def holographic_scene_unrefract(source_layer: str, target_layer: str):
    from sparkai.engine.engine_holographic_scene_composer import EngineHolographicSceneComposer
    composer = EngineHolographicSceneComposer.get_instance()
    result = composer.unrefract(source_layer, target_layer)
    if "error" in result:
        return {"status": "error", "detail": result["error"]}
    return {"status": "ok", "data": result}


@router.get("/holographic-scene/refractions")
async def holographic_scene_get_refractions(layer_id: Optional[str] = Query(None)):
    from sparkai.engine.engine_holographic_scene_composer import EngineHolographicSceneComposer
    composer = EngineHolographicSceneComposer.get_instance()
    return {"status": "ok", "data": composer.get_refractions(layer_id)}


# =============================================================================
# Element Routes
# =============================================================================

@router.post("/holographic-scene/elements")
async def holographic_scene_add_element(req: AddElementRequest):
    from sparkai.engine.engine_holographic_scene_composer import EngineHolographicSceneComposer
    composer = EngineHolographicSceneComposer.get_instance()
    pos = tuple(req.position) if len(req.position) == 3 else (0.0, 0.0, 0.0)
    result = composer.add_element(
        element_id=req.element_id,
        label=req.label,
        layer_ids=req.layer_ids,
        position=pos,
        properties=req.properties,
    )
    if "error" in result:
        return {"status": "error", "detail": result["error"]}
    return {"status": "ok", "data": result}


@router.get("/holographic-scene/elements")
async def holographic_scene_get_elements(limit: int = Query(50, ge=1, le=200)):
    from sparkai.engine.engine_holographic_scene_composer import EngineHolographicSceneComposer
    composer = EngineHolographicSceneComposer.get_instance()
    return {"status": "ok", "data": composer.get_elements(limit)}


# =============================================================================
# Scene Query Routes
# =============================================================================

@router.get("/holographic-scene/scenes")
async def holographic_scene_get_scenes(limit: int = Query(10, ge=1, le=50)):
    from sparkai.engine.engine_holographic_scene_composer import EngineHolographicSceneComposer
    composer = EngineHolographicSceneComposer.get_instance()
    return {"status": "ok", "data": composer.get_scenes(limit)}


@router.get("/holographic-scene/events")
async def holographic_scene_events(limit: int = Query(50, ge=1, le=200)):
    from sparkai.engine.engine_holographic_scene_composer import EngineHolographicSceneComposer
    composer = EngineHolographicSceneComposer.get_instance()
    return {"status": "ok", "data": composer.get_events_log(limit)}


# =============================================================================
# Cycle Routes
# =============================================================================

@router.post("/holographic-scene/cycle")
async def holographic_scene_cycle():
    from sparkai.engine.engine_holographic_scene_composer import EngineHolographicSceneComposer
    composer = EngineHolographicSceneComposer.get_instance()
    return {"status": "ok", "data": composer.cycle()}


@router.post("/holographic-scene/simulate")
async def holographic_scene_simulate(req: SimulateRequest):
    from sparkai.engine.engine_holographic_scene_composer import EngineHolographicSceneComposer
    composer = EngineHolographicSceneComposer.get_instance()
    result = composer.simulate(req.cycles)
    if "error" in result:
        return {"status": "error", "detail": result["error"]}
    return {"status": "ok", "data": result}


@router.post("/holographic-scene/reset")
async def holographic_scene_reset():
    from sparkai.engine.engine_holographic_scene_composer import EngineHolographicSceneComposer
    composer = EngineHolographicSceneComposer.get_instance()
    return {"status": "ok", "data": composer.reset()}
