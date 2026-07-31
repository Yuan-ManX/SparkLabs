"""
SparkLabs Backend - Perspective Lattice Projector Routes

REST endpoints for the Engine Perspective Lattice Projector.
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


class OrientSceneRequest(BaseModel):
    anchor_x: float = 0.0
    anchor_y: float = 0.0
    anchor_z: float = 0.0
    framing: str = "default"


class AddPerspectiveRequest(BaseModel):
    node_id: str
    kind: str = "camera"               # camera/audio/narrative/social/spatial
    weight: float = 0.5                 # 0.0-1.0
    focus_target: str = ""


class SimulateRequest(BaseModel):
    cycles: int = 5


# =============================================================================
# Routes
# =============================================================================

@router.post("/perspective-lattice/scenes")
async def lattice_register_scene(req: RegisterSceneRequest):
    from sparkai.engine.engine_perspective_lattice_projector import (
        EnginePerspectiveLatticeProjector,
    )
    projector = EnginePerspectiveLatticeProjector.get_instance()
    result = projector.register_scene(scene_id=req.scene_id)
    if "error" in result:
        return {"status": "error", "detail": result["error"]}
    return {"status": "ok", "data": result}


@router.post("/perspective-lattice/scenes/{scene_id}/orient")
async def lattice_orient_scene(scene_id: str, req: OrientSceneRequest):
    from sparkai.engine.engine_perspective_lattice_projector import (
        EnginePerspectiveLatticeProjector,
    )
    projector = EnginePerspectiveLatticeProjector.get_instance()
    result = projector.orient_scene(
        scene_id=scene_id,
        anchor_x=req.anchor_x,
        anchor_y=req.anchor_y,
        anchor_z=req.anchor_z,
        framing=req.framing,
    )
    if "error" in result:
        return {"status": "error", "detail": result["error"]}
    return {"status": "ok", "data": result}


@router.post("/perspective-lattice/scenes/{scene_id}/perspectives")
async def lattice_add_perspective(scene_id: str, req: AddPerspectiveRequest):
    from sparkai.engine.engine_perspective_lattice_projector import (
        EnginePerspectiveLatticeProjector, PerspectiveKind,
    )
    projector = EnginePerspectiveLatticeProjector.get_instance()
    try:
        kind = PerspectiveKind(req.kind)
    except ValueError:
        return {"status": "error", "detail": f"Invalid kind: {req.kind}"}
    result = projector.add_perspective(
        scene_id=scene_id,
        node_id=req.node_id,
        kind=kind,
        weight=req.weight,
        focus_target=req.focus_target,
    )
    if "error" in result:
        return {"status": "error", "detail": result["error"]}
    return {"status": "ok", "data": result}


@router.get("/perspective-lattice/scenes/{scene_id}")
async def lattice_get_scene_state(scene_id: str):
    from sparkai.engine.engine_perspective_lattice_projector import (
        EnginePerspectiveLatticeProjector,
    )
    projector = EnginePerspectiveLatticeProjector.get_instance()
    result = projector.get_scene_state(scene_id)
    if "error" in result:
        return {"status": "error", "detail": result["error"]}
    return {"status": "ok", "data": result}


@router.get("/perspective-lattice/scenes/{scene_id}/nodes")
async def lattice_get_nodes(scene_id: str, limit: int = 20):
    from sparkai.engine.engine_perspective_lattice_projector import (
        EnginePerspectiveLatticeProjector,
    )
    projector = EnginePerspectiveLatticeProjector.get_instance()
    result = projector.get_nodes(scene_id, limit=limit)
    if "error" in result:
        return {"status": "error", "detail": result["error"]}
    return {"status": "ok", "data": result}


@router.get("/perspective-lattice/scenes/{scene_id}/edges")
async def lattice_get_edges(scene_id: str, limit: int = 30):
    from sparkai.engine.engine_perspective_lattice_projector import (
        EnginePerspectiveLatticeProjector,
    )
    projector = EnginePerspectiveLatticeProjector.get_instance()
    result = projector.get_edges(scene_id, limit=limit)
    if "error" in result:
        return {"status": "error", "detail": result["error"]}
    return {"status": "ok", "data": result}


@router.get("/perspective-lattice/events")
async def lattice_get_events(limit: int = 50):
    from sparkai.engine.engine_perspective_lattice_projector import (
        EnginePerspectiveLatticeProjector,
    )
    projector = EnginePerspectiveLatticeProjector.get_instance()
    return {"status": "ok", "data": projector.get_events_log(limit=limit)}


@router.get("/perspective-lattice/status")
async def lattice_get_status():
    from sparkai.engine.engine_perspective_lattice_projector import (
        EnginePerspectiveLatticeProjector,
    )
    projector = EnginePerspectiveLatticeProjector.get_instance()
    return {"status": "ok", "data": projector.get_status()}


@router.post("/perspective-lattice/cycle")
async def lattice_cycle():
    from sparkai.engine.engine_perspective_lattice_projector import (
        EnginePerspectiveLatticeProjector,
    )
    projector = EnginePerspectiveLatticeProjector.get_instance()
    return {"status": "ok", "data": projector.cycle()}


@router.post("/perspective-lattice/simulate")
async def lattice_simulate(req: SimulateRequest):
    from sparkai.engine.engine_perspective_lattice_projector import (
        EnginePerspectiveLatticeProjector,
    )
    projector = EnginePerspectiveLatticeProjector.get_instance()
    return {"status": "ok", "data": projector.simulate(cycles=req.cycles)}


@router.post("/perspective-lattice/reset")
async def lattice_reset():
    from sparkai.engine.engine_perspective_lattice_projector import (
        EnginePerspectiveLatticeProjector,
    )
    projector = EnginePerspectiveLatticeProjector.get_instance()
    return {"status": "ok", "data": projector.reset()}
