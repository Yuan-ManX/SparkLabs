"""
SparkAI Agent - Engine Bridge"""

from __future__ import annotations

import uuid
import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


def _get_engine():
    from sparkai.engine.engine import SparkEngine
    return SparkEngine.get_instance()


def _get_or_create_world(engine, name: str = "Default World"):
    world = engine.get_active_world()
    if world is None:
        world = engine.create_world(name)
    return world


async def bridge_create_world(params: Dict[str, Any]) -> Dict[str, Any]:
    engine = _get_engine()
    name = params.get("name", "World")
    world = engine.create_world(name)
    return {
        "action": "create_world",
        "world_id": world.id,
        "name": name,
        "status": "created",
    }


async def bridge_create_entity(params: Dict[str, Any]) -> Dict[str, Any]:
    engine = _get_engine()
    world = _get_or_create_world(engine)
    name = params.get("name", "Entity")
    position = params.get("position", [0, 0, 0])
    components = params.get("components", [])
    tags = params.get("tags", [])

    entity = world.create_entity(name=name)
    for comp_type in components:
        try:
            from sparkai.engine.ecs.component import ComponentRegistry
            comp_cls = ComponentRegistry.get(comp_type)
            if comp_cls:
                entity.add_component(comp_cls())
        except Exception:
            pass
    for tag in tags:
        entity.add_tag(tag)

    transform = entity.get_component("transform")
    if transform:
        try:
            transform.position = position
        except Exception:
            pass

    return {
        "action": "create_entity",
        "entity_id": entity.id,
        "name": name,
        "position": position,
        "components": list(components),
        "tags": tags,
        "status": "created",
    }


async def bridge_add_component(params: Dict[str, Any]) -> Dict[str, Any]:
    engine = _get_engine()
    entity_id = params.get("entity_id", "")
    component_type = params.get("component_type", "")

    world = engine.get_active_world()
    if not world:
        return {"action": "add_component", "error": "No active world", "status": "error"}

    entity = world.entities.get_entity(entity_id)
    if not entity:
        return {"action": "add_component", "error": f"Entity {entity_id} not found", "status": "error"}

    try:
        from sparkai.engine.ecs.component import ComponentRegistry
        comp_cls = ComponentRegistry.get(component_type)
        if comp_cls:
            entity.add_component(comp_cls())
        return {
            "action": "add_component",
            "entity_id": entity_id,
            "component_type": component_type,
            "status": "added",
        }
    except Exception as e:
        return {"action": "add_component", "error": str(e), "status": "error"}


async def bridge_remove_component(params: Dict[str, Any]) -> Dict[str, Any]:
    engine = _get_engine()
    entity_id = params.get("entity_id", "")
    component_type = params.get("component_type", "")

    world = engine.get_active_world()
    if not world:
        return {"action": "remove_component", "error": "No active world", "status": "error"}

    entity = world.entities.get_entity(entity_id)
    if not entity:
        return {"action": "remove_component", "error": f"Entity {entity_id} not found", "status": "error"}

    entity.remove_component(component_type)
    return {
        "action": "remove_component",
        "entity_id": entity_id,
        "component_type": component_type,
        "status": "removed",
    }


async def bridge_create_scene(params: Dict[str, Any]) -> Dict[str, Any]:
    engine = _get_engine()
    name = params.get("name", "Untitled Scene")
    scene = engine.create_scene(name)
    return {
        "action": "create_scene",
        "scene_id": scene.id,
        "name": name,
        "status": "created",
    }


async def bridge_query_entities(params: Dict[str, Any]) -> Dict[str, Any]:
    engine = _get_engine()
    world = engine.get_active_world()
    if not world:
        return {"action": "query_entities", "entities": [], "status": "empty"}

    filter_criteria = params.get("filter", {})
    entities = world.entities.query()
    results = []
    for e in entities[:50]:
        results.append({
            "id": e.id,
            "name": e.name,
            "components": list(e.get_components().keys()),
            "tags": list(e.tags),
        })
    return {
        "action": "query_entities",
        "count": len(entities),
        "entities": results,
        "status": "queried",
    }


async def bridge_list_scenes(params: Dict[str, Any]) -> Dict[str, Any]:
    engine = _get_engine()
    scenes = engine.list_scenes()
    return {
        "action": "list_scenes",
        "count": len(scenes),
        "scenes": scenes,
        "status": "listed",
    }


async def bridge_get_world_state(params: Dict[str, Any]) -> Dict[str, Any]:
    engine = _get_engine()
    world = engine.get_active_world()
    if not world:
        return {"action": "get_world_state", "world": None, "status": "empty"}
    return {
        "action": "get_world_state",
        "world": world.get_status(),
        "status": "active",
    }


async def bridge_spawn_prefab(params: Dict[str, Any]) -> Dict[str, Any]:
    engine = _get_engine()
    prefab_name = params.get("prefab", "")
    position = params.get("position", [0, 0, 0])
    world = _get_or_create_world(engine)

    entity = world.create_entity(name=prefab_name or "Prefab")
    for tag in params.get("tags", []):
        entity.add_tag(tag)
    return {
        "action": "spawn_prefab",
        "entity_id": entity.id,
        "prefab": prefab_name,
        "position": position,
        "status": "spawned",
    }


async def bridge_set_physics(params: Dict[str, Any]) -> Dict[str, Any]:
    engine = _get_engine()
    gravity = params.get("gravity", [0, -9.81, 0])
    try:
        engine._physics_system.set_gravity(gravity)
    except Exception:
        pass
    return {
        "action": "set_physics",
        "gravity": gravity,
        "status": "configured",
    }


async def bridge_trigger_signal(params: Dict[str, Any]) -> Dict[str, Any]:
    engine = _get_engine()
    signal_name = params.get("signal", "")
    signal_data = params.get("data", None)
    count = engine._signal_bus.emit(signal_name, signal_data)
    return {
        "action": "trigger_signal",
        "signal": signal_name,
        "listeners": count,
        "status": "emitted",
    }


async def bridge_get_console_logs(params: Dict[str, Any]) -> Dict[str, Any]:
    engine = _get_engine()
    console = engine._console_system
    logs = console.get_logs(params.get("limit", 50))
    return {
        "action": "get_console_logs",
        "count": len(logs),
        "logs": [log.to_dict() for log in logs],
        "status": "retrieved",
    }


async def bridge_toggle_game_loop(params: Dict[str, Any]) -> Dict[str, Any]:
    engine = _get_engine()
    gl = engine._game_loop
    action = params.get("action", "start")
    if action == "start":
        gl.start()
    elif action == "stop":
        gl.stop()
    elif action == "pause":
        gl.pause()
    elif action == "resume":
        gl.resume()
    return {
        "action": "toggle_game_loop",
        "state": gl.get_statistics(),
        "status": action,
    }


async def bridge_perform_game_action(params: Dict[str, Any]) -> Dict[str, Any]:
    engine = _get_engine()
    action_type = params.get("action_type", "")
    target = params.get("target", "")
    world = engine.get_active_world()
    if not world:
        return {"action": "perform_game_action", "error": "No active world", "status": "error"}

    if action_type == "destroy" and target:
        world.destroy_entity(target)
        return {"action": "perform_game_action", "entity_id": target, "status": "destroyed"}

    return {
        "action": "perform_game_action",
        "action_type": action_type,
        "target": target,
        "status": "executed",
    }


async def bridge_simulate_world(params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Predict the consequences of the current world state by stepping the
    engine forward in a sandbox.

    By default the simulation is rolled back (predictive "what-if"). Set
    `commit: true` to keep the simulated outcome. Returns the before/after
    state, the diff, and a concise summary the agent can reason over.
    """
    engine = _get_engine()
    frames = int(params.get("frames", 60))
    delta_time = float(params.get("delta_time", 1.0 / 60.0))
    commit = bool(params.get("commit", False))
    try:
        result = engine.simulate_frames(
            frames=frames, delta_time=delta_time, commit=commit,
        )
        result["action"] = "simulate_world"
        result["status"] = "committed" if commit else "rolled_back"
        return result
    except Exception as exc:
        logger.warning("simulate_world failed: %s", exc)
        return {
            "action": "simulate_world",
            "status": "error",
            "error": str(exc),
        }


async def bridge_create_checkpoint(params: Dict[str, Any]) -> Dict[str, Any]:
    """Snapshot the current world so it can be restored or diffed later."""
    engine = _get_engine()
    reason = params.get("reason", "checkpoint")
    cp = engine.create_checkpoint(reason=reason)
    return {
        "action": "create_checkpoint",
        "checkpoint_id": cp["id"],
        "reason": reason,
        "scene_count": len(cp.get("scenes", [])),
        "status": "created",
    }


async def bridge_restore_checkpoint(params: Dict[str, Any]) -> Dict[str, Any]:
    """Restore the world to a previously captured checkpoint (rollback)."""
    engine = _get_engine()
    cp_id = params.get("checkpoint_id", "")
    ok = engine.restore_checkpoint(cp_id)
    return {
        "action": "restore_checkpoint",
        "checkpoint_id": cp_id,
        "status": "restored" if ok else "not_found",
    }


async def bridge_list_checkpoints(params: Dict[str, Any]) -> Dict[str, Any]:
    """List all captured world checkpoints."""
    engine = _get_engine()
    checkpoints = engine.list_checkpoints()
    return {
        "action": "list_checkpoints",
        "count": len(checkpoints),
        "checkpoints": checkpoints,
        "status": "listed",
    }


async def bridge_add_logic_event(params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Register a structured GameLogicIR event on the engine runtime.

    `event` is a dict with name, description, enabled, priority,
    conditions and actions. Registering rules lets the built game
    respond to world state (e.g. collect coin -> score, reach win).
    """
    engine = _get_engine()
    event_data = params.get("event", {}) or {}
    try:
        from sparkai.engine.game_logic_ir import (
            GameEvent, GameAction, Condition, Expression, ConditionOperator, ActionType,
        )
    except Exception as exc:
        return {"action": "add_logic_event", "status": "error", "error": str(exc)}

    try:
        op = ConditionOperator(event_data.get("condition_operator", "less_than"))
    except ValueError:
        op = ConditionOperator.LESS_THAN

    try:
        atype = ActionType(event_data.get("action_type", "custom"))
    except ValueError:
        atype = ActionType.CUSTOM

    event = GameEvent(
        name=event_data.get("name", "Untitled Event"),
        description=event_data.get("description", ""),
        enabled=event_data.get("enabled", True),
        priority=event_data.get("priority", 0),
    )
    # Condition: left variable vs right literal (default)
    event.conditions.append(Condition(
        left=Expression(type="variable", variable_path=event_data.get("variable_path", "game.tick")),
        operator=op,
        right=Expression(type="literal", value=event_data.get("value", 0)),
    ))
    # Action (default: add score to the target entity)
    event.actions.append(GameAction(
        action_type=atype,
        target=event_data.get("target", ""),
        params=event_data.get("params", {}),
    ))
    try:
        event_id = engine.add_logic_event(event)
        return {
            "action": "add_logic_event",
            "event_id": event_id,
            "event_name": event.name,
            "status": "registered",
        }
    except Exception as exc:
        return {"action": "add_logic_event", "status": "error", "error": str(exc)}


async def bridge_list_logic_events(params: Dict[str, Any]) -> Dict[str, Any]:
    """List all GameLogicIR events registered on the engine runtime."""
    engine = _get_engine()
    events = engine.export_logic_events()
    return {
        "action": "list_logic_events",
        "count": len(events),
        "events": events,
        "status": "listed",
    }


def get_engine_bridge_handlers() -> Dict[str, Any]:
    return {
        "create_world": bridge_create_world,
        "create_entity": bridge_create_entity,
        "add_component": bridge_add_component,
        "remove_component": bridge_remove_component,
        "create_scene": bridge_create_scene,
        "query_entities": bridge_query_entities,
        "list_scenes": bridge_list_scenes,
        "get_world_state": bridge_get_world_state,
        "spawn_prefab": bridge_spawn_prefab,
        "set_physics": bridge_set_physics,
        "trigger_signal": bridge_trigger_signal,
        "get_console_logs": bridge_get_console_logs,
        "toggle_game_loop": bridge_toggle_game_loop,
        "perform_game_action": bridge_perform_game_action,
        # Predictive simulation & checkpointing
        "simulate_world": bridge_simulate_world,
        "create_checkpoint": bridge_create_checkpoint,
        "restore_checkpoint": bridge_restore_checkpoint,
        "list_checkpoints": bridge_list_checkpoints,
        # GameLogicIR rule authoring
        "add_logic_event": bridge_add_logic_event,
        "list_logic_events": bridge_list_logic_events,
    }
