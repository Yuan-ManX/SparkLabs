"""
SparkLabs Backend - Cognitive Fusion API Routes

REST API endpoints for the cognitive fusion layer that integrates
the CognitiveGameEngine, CognitiveSkillForge, and AdaptivePhysicsDirector.

Endpoints:
  GET  /cognitive-fusion/status       - Combined status of all three modules
  POST /cognitive-fusion/tick         - Run one fused cognitive tick
  POST /cognitive-fusion/tick-batch   - Run N fused ticks in sequence
  POST /cognitive-fusion/start        - Start the fusion layer
  POST /cognitive-fusion/pause        - Pause the fusion layer
  POST /cognitive-fusion/resume       - Resume the fusion layer
  POST /cognitive-fusion/reset        - Reset all three modules
  GET  /cognitive-fusion/history      - List recent fusion tick results
  GET  /cognitive-fusion/full         - Full status of all three subsystems

  # Skill Forge endpoints
  GET  /cognitive-fusion/skills       - List skills (filterable by tier/status)
  GET  /cognitive-fusion/skills/{id}  - Get a single skill by ID
  POST /cognitive-fusion/skills/reset - Reset the skill forge

  # Physics Director endpoints
  GET  /cognitive-fusion/physics      - Physics director status
  GET  /cognitive-fusion/physics/history - Physics adjustment history
  GET  /cognitive-fusion/physics/profiles - List persisted physics profiles
  POST /cognitive-fusion/physics/genre - Set the current genre
  POST /cognitive-fusion/physics/reset - Reset the physics director
"""

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional

router = APIRouter()


class TickBatchRequest(BaseModel):
    count: int = 10
    dt: float = 1.0 / 60.0


class SetGenreRequest(BaseModel):
    genre: str = "generic"


class ListSkillsRequest(BaseModel):
    tier: Optional[str] = None
    status_filter: Optional[str] = None
    limit: int = 20


def _get_fusion():
    from sparkai.engine.engine_cognitive_fusion import get_fusion_layer
    return get_fusion_layer()


# =============================================================================
# Fusion Layer Endpoints
# =============================================================================

@router.get("/cognitive-fusion/status")
async def fusion_status():
    """Get the combined status of all three modules."""
    try:
        return JSONResponse({
            "status": "success",
            "data": _get_fusion().status(),
        })
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JSONResponse(
            {"status": "error", "message": str(e)}, status_code=500
        )


@router.get("/cognitive-fusion/full")
async def fusion_full_status():
    """Get the full status of all three subsystems."""
    try:
        return JSONResponse({
            "status": "success",
            "data": _get_fusion().full_status(),
        })
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JSONResponse(
            {"status": "error", "message": str(e)}, status_code=500
        )


@router.post("/cognitive-fusion/tick")
async def fusion_tick():
    """Run one fused cognitive tick."""
    try:
        fusion = _get_fusion()
        if fusion._engine._state.value == "cold":
            fusion.initialize()
        result = fusion.fused_tick()
        return JSONResponse({
            "status": "success",
            "data": result.to_dict(),
        })
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JSONResponse(
            {"status": "error", "message": str(e)}, status_code=500
        )


@router.post("/cognitive-fusion/tick-batch")
async def fusion_tick_batch(req: TickBatchRequest):
    """Run N fused ticks in sequence."""
    try:
        fusion = _get_fusion()
        if fusion._engine._state.value == "cold":
            fusion.initialize()
        return JSONResponse({
            "status": "success",
            "data": fusion.fused_batch(req.count, req.dt),
        })
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JSONResponse(
            {"status": "error", "message": str(e)}, status_code=500
        )


@router.post("/cognitive-fusion/start")
async def fusion_start():
    """Start the fusion layer."""
    try:
        fusion = _get_fusion()
        fusion.initialize()
        return JSONResponse({
            "status": "success",
            "data": {"engine_state": fusion._engine._state.value},
        })
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JSONResponse(
            {"status": "error", "message": str(e)}, status_code=500
        )


@router.post("/cognitive-fusion/pause")
async def fusion_pause():
    try:
        fusion = _get_fusion()
        fusion.pause()
        return JSONResponse({
            "status": "success",
            "data": {"engine_state": fusion._engine._state.value},
        })
    except Exception as e:
        return JSONResponse(
            {"status": "error", "message": str(e)}, status_code=500
        )


@router.post("/cognitive-fusion/resume")
async def fusion_resume():
    try:
        fusion = _get_fusion()
        fusion.resume()
        return JSONResponse({
            "status": "success",
            "data": {"engine_state": fusion._engine._state.value},
        })
    except Exception as e:
        return JSONResponse(
            {"status": "error", "message": str(e)}, status_code=500
        )


@router.post("/cognitive-fusion/reset")
async def fusion_reset():
    """Reset all three modules to initial state."""
    try:
        fusion = _get_fusion()
        fusion.reset()
        return JSONResponse({
            "status": "success",
            "data": {"engine_state": fusion._engine._state.value},
        })
    except Exception as e:
        return JSONResponse(
            {"status": "error", "message": str(e)}, status_code=500
        )


@router.get("/cognitive-fusion/history")
async def fusion_history(limit: int = 10):
    """List recent fusion tick results."""
    try:
        return JSONResponse({
            "status": "success",
            "data": _get_fusion().history(limit=min(max(1, limit), 64)),
        })
    except Exception as e:
        return JSONResponse(
            {"status": "error", "message": str(e)}, status_code=500
        )


# =============================================================================
# Skill Forge Endpoints
# =============================================================================

@router.get("/cognitive-fusion/forge/skills")
async def list_skills(
    tier: Optional[str] = None,
    status_filter: Optional[str] = None,
    limit: int = 20,
):
    """List skills in the forge, optionally filtered by tier and/or status."""
    try:
        from sparkai.agent.agent_cognitive_skill_forge import get_skill_forge
        forge = get_skill_forge()
        return JSONResponse({
            "status": "success",
            "data": forge.list_skills(
                tier=tier, status_filter=status_filter,
                limit=min(max(1, limit), 100),
            ),
        })
    except Exception as e:
        return JSONResponse(
            {"status": "error", "message": str(e)}, status_code=500
        )


@router.get("/cognitive-fusion/skills/{skill_id}")
async def get_skill(skill_id: str):
    """Get a single skill by ID."""
    try:
        from sparkai.agent.agent_cognitive_skill_forge import get_skill_forge
        forge = get_skill_forge()
        skill = forge.get_skill(skill_id)
        if skill is None:
            return JSONResponse(
                {"status": "error", "message": f"Skill {skill_id} not found"},
                status_code=404,
            )
        return JSONResponse({"status": "success", "data": skill})
    except Exception as e:
        return JSONResponse(
            {"status": "error", "message": str(e)}, status_code=500
        )


@router.post("/cognitive-fusion/forge/reset")
async def reset_skill_forge():
    """Reset the skill forge to empty state."""
    try:
        from sparkai.agent.agent_cognitive_skill_forge import get_skill_forge
        get_skill_forge().reset()
        return JSONResponse({"status": "success"})
    except Exception as e:
        return JSONResponse(
            {"status": "error", "message": str(e)}, status_code=500
        )


# =============================================================================
# Physics Director Endpoints
# =============================================================================

@router.get("/cognitive-fusion/physics")
async def physics_status():
    """Get the physics director status."""
    try:
        from sparkai.engine.engine_adaptive_physics_director import get_physics_director
        return JSONResponse({
            "status": "success",
            "data": get_physics_director().status(),
        })
    except Exception as e:
        return JSONResponse(
            {"status": "error", "message": str(e)}, status_code=500
        )


@router.get("/cognitive-fusion/physics/history")
async def physics_history(limit: int = 10):
    """Get the physics adjustment history."""
    try:
        from sparkai.engine.engine_adaptive_physics_director import get_physics_director
        return JSONResponse({
            "status": "success",
            "data": get_physics_director().history(limit=min(max(1, limit), 32)),
        })
    except Exception as e:
        return JSONResponse(
            {"status": "error", "message": str(e)}, status_code=500
        )


@router.get("/cognitive-fusion/physics/profiles")
async def physics_profiles():
    """List persisted physics profiles."""
    try:
        from sparkai.engine.engine_adaptive_physics_director import get_physics_director
        return JSONResponse({
            "status": "success",
            "data": get_physics_director().list_profiles(),
        })
    except Exception as e:
        return JSONResponse(
            {"status": "error", "message": str(e)}, status_code=500
        )


@router.post("/cognitive-fusion/physics/genre")
async def physics_set_genre(req: SetGenreRequest):
    """Set the current genre for physics profile matching."""
    try:
        from sparkai.engine.engine_adaptive_physics_director import get_physics_director
        get_physics_director().set_genre(req.genre)
        return JSONResponse({
            "status": "success",
            "data": {"genre": get_physics_director()._current_genre.value},
        })
    except Exception as e:
        return JSONResponse(
            {"status": "error", "message": str(e)}, status_code=500
        )


@router.post("/cognitive-fusion/physics/reset")
async def physics_reset():
    """Reset the physics director."""
    try:
        from sparkai.engine.engine_adaptive_physics_director import get_physics_director
        get_physics_director().reset()
        return JSONResponse({"status": "success"})
    except Exception as e:
        return JSONResponse(
            {"status": "error", "message": str(e)}, status_code=500
        )
