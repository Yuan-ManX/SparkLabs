"""
SparkLabs Backend - Game Logic IR API Routes

REST API for managing structured game logic: events, conditions,
actions, and the runtime logic execution engine.

When the SparkEngine is importable, the API delegates to the engine's
own GameLogicRuntime so that events registered through the API actually
fire inside the running simulation. Otherwise it falls back to a
standalone runtime (useful for offline tests / pre-flight validation).
"""

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Any, Dict, List, Optional

router = APIRouter()

_runtime = None
_engine_runtime = None
_engine_checked = False


def _get_engine_runtime():
    """Return the SparkEngine's global GameLogicRuntime, if available."""
    global _engine_runtime, _engine_checked
    if not _engine_checked:
        _engine_checked = True
        try:
            from sparkai.engine.engine import SparkEngine
            _engine_runtime = SparkEngine.get_instance().game_logic_runtime
        except Exception:
            _engine_runtime = None
    return _engine_runtime


def _get_runtime():
    """Prefer the engine's runtime; fall back to a standalone one."""
    eng = _get_engine_runtime()
    if eng is not None:
        return eng
    global _runtime
    if _runtime is None:
        from sparkai.engine.game_logic_ir import GameLogicRuntime, GameLogicCompiler
        _runtime = GameLogicRuntime(GameLogicCompiler())
    return _runtime


class CreateEventRequest(BaseModel):
    name: str = "Untitled Event"
    description: str = ""
    conditions: List[Dict[str, Any]] = []
    actions: List[Dict[str, Any]] = []
    enabled: bool = True
    priority: int = 0
    max_triggers: int = -1
    cooldown_ms: int = 0


class CreateFromNLRequest(BaseModel):
    description: str


class EvaluateRequest(BaseModel):
    context: Dict[str, Any] = {}
    delta_time: float = 0.016


@router.get("/logic/status")
async def logic_status():
    """Get game logic runtime status."""
    try:
        rt = _get_runtime()
        return JSONResponse({"status": "success", "data": rt.get_statistics()})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.get("/logic/events")
async def list_events():
    """List all game logic events."""
    try:
        rt = _get_runtime()
        return JSONResponse({
            "status": "success",
            "data": rt.export_events(),
        })
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.post("/logic/events")
async def create_event(req: CreateEventRequest):
    """Create a new game logic event."""
    try:
        from sparkai.engine.game_logic_ir import (
            GameEvent, Condition, ActionType, ConditionOperator, Expression,
        )
        rt = _get_runtime()

        event = GameEvent(
            name=req.name,
            description=req.description,
            enabled=req.enabled,
            priority=req.priority,
            max_triggers=req.max_triggers,
            cooldown_ms=req.cooldown_ms,
        )

        for cond_data in req.conditions:
            condition = Condition(
                operator=ConditionOperator(cond_data.get("operator", "equals")),
            )
            event.conditions.append(condition)

        for action_data in req.actions:
            from sparkai.engine.game_logic_ir import GameAction
            action = GameAction(
                action_type=ActionType(action_data.get("action_type", "custom")),
                target=action_data.get("target", ""),
                params=action_data.get("params", {}),
                delay_ms=action_data.get("delay_ms", 0),
                repeat_count=action_data.get("repeat_count", 1),
            )
            event.actions.append(action)

        event_id = rt.add_event(event)
        return JSONResponse({
            "status": "success",
            "data": {"event_id": event_id, "event": event.to_dict()},
        })
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.post("/logic/events/nl")
async def create_event_from_nl(req: CreateFromNLRequest):
    """Create a game logic event from natural language description."""
    try:
        from sparkai.engine.game_logic_ir import create_event_from_nl
        rt = _get_runtime()
        event = create_event_from_nl(req.description)
        event_id = rt.add_event(event)
        return JSONResponse({
            "status": "success",
            "data": {
                "event_id": event_id,
                "event": event.to_dict(),
                "trigger_count": len(event.conditions),
                "action_count": len(event.actions),
            },
        })
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.delete("/logic/events/{event_id}")
async def delete_event(event_id: str):
    """Delete a game logic event."""
    try:
        rt = _get_runtime()
        ok = rt.remove_event(event_id)
        return JSONResponse({
            "status": "success" if ok else "error",
            "data": {"removed": ok},
        })
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.post("/logic/evaluate")
async def evaluate_logic(req: EvaluateRequest):
    """Evaluate all game logic events against the given context."""
    try:
        rt = _get_runtime()
        rt.update_context(req.context)
        triggered = rt.tick(req.delta_time)
        return JSONResponse({
            "status": "success",
            "data": {
                "triggered": triggered,
                "triggered_count": len(triggered),
                "statistics": rt.get_statistics(),
            },
        })
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.post("/logic/context")
async def set_context(req: Dict[str, Any]):
    """Set the game logic context."""
    try:
        rt = _get_runtime()
        updates = req.get("context", req)
        for key, value in updates.items():
            rt.set_context(key, value)
        return JSONResponse({
            "status": "success",
            "data": {"context_keys": list(rt.context.keys())},
        })
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.get("/logic/actions")
async def list_action_types():
    """List all available action types."""
    try:
        from sparkai.engine.game_logic_ir import ActionType
        return JSONResponse({
            "status": "success",
            "data": [
                {"value": t.value, "label": t.value.replace("_", " ").title()}
                for t in ActionType
            ],
        })
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.get("/logic/operators")
async def list_condition_operators():
    """List all available condition operators."""
    try:
        from sparkai.engine.game_logic_ir import ConditionOperator
        return JSONResponse({
            "status": "success",
            "data": [
                {"value": t.value, "label": t.value.replace("_", " ").title()}
                for t in ConditionOperator
            ],
        })
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.get("/logic/action-log")
async def get_action_log(limit: int = 50):
    """Get the action execution log."""
    try:
        rt = _get_runtime()
        return JSONResponse({
            "status": "success",
            "data": rt.get_action_log(limit),
        })
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.post("/logic/import")
async def import_events(req: List[Dict[str, Any]]):
    """Import game logic events from serialized data."""
    try:
        rt = _get_runtime()
        imported = rt.import_events(req)
        return JSONResponse({
            "status": "success",
            "data": {"imported_count": len(imported), "event_ids": imported},
        })
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.get("/logic/export")
async def export_events():
    """Export all game logic events."""
    try:
        rt = _get_runtime()
        return JSONResponse({
            "status": "success",
            "data": rt.export_events(),
        })
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.get("/logic/action-errors")
async def get_action_errors(limit: int = 50):
    """Get the action execution error log."""
    try:
        rt = _get_runtime()
        return JSONResponse({
            "status": "success",
            "data": rt.get_action_errors(limit),
        })
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.get("/logic/engine-status")
async def engine_logic_status():
    """
    Return whether logic events fire inside the running SparkEngine.

    `runtime_source` is "engine" when the API is wired into SparkEngine,
    or "standalone" when running on a detached runtime (e.g. in tests).
    """
    try:
        eng_rt = _get_engine_runtime()
        return JSONResponse({
            "status": "success",
            "data": {
                "runtime_source": "engine" if eng_rt is not None else "standalone",
                "statistics": eng_rt.get_statistics() if eng_rt is not None else None,
            },
        })
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


class SceneLogicRequest(BaseModel):
    scene_id: str
    event: Dict[str, Any]


@router.post("/logic/scene-events")
async def add_scene_event(req: SceneLogicRequest):
    """Register a logic event with a specific scene's isolated runtime."""
    try:
        from sparkai.engine.engine import SparkEngine
        from sparkai.engine.game_logic_ir import (
            GameEvent, Condition, ActionType, ConditionOperator, GameAction,
        )
        engine = SparkEngine.get_instance()
        rt = engine.ensure_scene_logic_runtime(req.scene_id)
        if rt is None:
            return JSONResponse({
                "status": "error",
                "message": f"Unknown scene_id: {req.scene_id}",
            }, status_code=404)

        ev_data = req.event
        event = GameEvent(
            name=ev_data.get("name", "Untitled Event"),
            description=ev_data.get("description", ""),
            enabled=ev_data.get("enabled", True),
            priority=ev_data.get("priority", 0),
            max_triggers=ev_data.get("max_triggers", -1),
            cooldown_ms=ev_data.get("cooldown_ms", 0),
        )
        for cond_data in ev_data.get("conditions", []):
            event.conditions.append(Condition(
                operator=ConditionOperator(cond_data.get("operator", "equals")),
            ))
        for action_data in ev_data.get("actions", []):
            event.actions.append(GameAction(
                action_type=ActionType(action_data.get("action_type", "custom")),
                target=action_data.get("target", ""),
                params=action_data.get("params", {}),
                delay_ms=action_data.get("delay_ms", 0),
                repeat_count=action_data.get("repeat_count", 1),
            ))
        event_id = rt.add_event(event)
        return JSONResponse({
            "status": "success",
            "data": {"event_id": event_id, "event": event.to_dict(), "scene_id": req.scene_id},
        })
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.get("/logic/scene-events/{scene_id}")
async def list_scene_events(scene_id: str):
    """List logic events registered with a specific scene's runtime."""
    try:
        from sparkai.engine.engine import SparkEngine
        engine = SparkEngine.get_instance()
        rt = engine.get_scene_logic_runtime(scene_id)
        if rt is None:
            return JSONResponse({
                "status": "success",
                "data": [],
                "note": "scene has no isolated runtime",
            })
        return JSONResponse({"status": "success", "data": rt.export_events()})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.delete("/logic/scene-events/{scene_id}/{event_id}")
async def delete_scene_event(scene_id: str, event_id: str):
    """Delete a logic event from a specific scene's runtime."""
    try:
        from sparkai.engine.engine import SparkEngine
        engine = SparkEngine.get_instance()
        rt = engine.get_scene_logic_runtime(scene_id)
        if rt is None:
            return JSONResponse({
                "status": "error",
                "message": f"Scene {scene_id} has no isolated runtime",
            }, status_code=404)
        ok = rt.remove_event(event_id)
        return JSONResponse({"status": "success" if ok else "error", "data": {"removed": ok}})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)
