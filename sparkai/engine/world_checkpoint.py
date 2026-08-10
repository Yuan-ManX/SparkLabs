"""
SparkLabs Engine - World Checkpoint & Predictive Simulation"""

from __future__ import annotations

import uuid
import time
import copy
import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

_MAX_CHECKPOINTS = 64


@dataclass
class WorldCheckpoint:
    """Serialized snapshot of all scenes and their entities."""

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    reason: str = "checkpoint"
    created_at: float = field(default_factory=time.time)
    scenes: List[Dict[str, Any]] = field(default_factory=list)
    active_scene_id: Optional[str] = None
    engine_tick: int = 0
    score: float = 0.0
    logic_events: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "reason": self.reason,
            "created_at": self.created_at,
            "scene_count": len(self.scenes),
            "active_scene_id": self.active_scene_id,
            "engine_tick": self.engine_tick,
            "score": self.score,
            "logic_events": len(self.logic_events),
        }

    def full_dict(self) -> Dict[str, Any]:
        """Full serialized payload, used for diffing and debugging."""
        data = self.to_dict()
        data["scenes"] = self.scenes
        data["logic_events"] = self.logic_events
        return data


def _serialize_entity(entity) -> Dict[str, Any]:
    return {
        "id": entity.id,
        "name": entity.name,
        "scene_id": entity.scene_id,
        "position": list(entity.position),
        "rotation": list(entity.rotation),
        "scale": list(entity.scale),
        "tags": list(entity.tags),
        "components": copy.deepcopy(dict(entity.components)),
        "properties": copy.deepcopy(dict(entity.properties)),
    }


def _serialize_scene(scene) -> Dict[str, Any]:
    return {
        "id": scene.id,
        "name": scene.name,
        "entities": [_serialize_entity(e) for e in scene.entities.values()],
    }


class WorldCheckpointService:
    """
    Manages a bounded history of world checkpoints.

    Thread-safe for the single-threaded engine loop. Provides a sandbox
    API so agents can step the world forward and inspect outcomes.
    """

    def __init__(self, max_checkpoints: int = _MAX_CHECKPOINTS):
        self._max = max_checkpoints
        self._checkpoints: Dict[str, WorldCheckpoint] = {}

    # ------------------------------------------------------------------
    # Checkpoint management
    # ------------------------------------------------------------------

    def capture_checkpoint(
        self,
        engine,
        reason: str = "checkpoint",
        include_logic: bool = True,
    ) -> WorldCheckpoint:
        """
        Snapshot the current world state from a live SparkEngine.

        Captures all scenes + entities, the active scene id, current
        tick, and the serialized logic-event registry so the sandbox can
        reproduce behavior before rolling back.
        """
        scenes = [_serialize_scene(s) for s in engine._scenes.values()]
        cp = WorldCheckpoint(
            reason=reason,
            scenes=scenes,
            active_scene_id=engine._active_scene_id,
            engine_tick=getattr(engine, "_frame_count", 0),
            score=float(
                engine._game_logic_runtime.context.get("game", {}).get("score", 0)
            ),
        )
        if include_logic:
            try:
                cp.logic_events = engine._game_logic_runtime.export_events()
            except Exception:
                cp.logic_events = []
        self._checkpoints[cp.id] = cp
        # Bound history (FIFO eviction)
        while len(self._checkpoints) > self._max:
            oldest = min(self._checkpoints.values(), key=lambda c: c.created_at)
            del self._checkpoints[oldest.id]
        logger.debug("Captured checkpoint %s (%s)", cp.id, reason)
        return cp

    def restore_checkpoint(self, engine, checkpoint_id: str) -> bool:
        """
        Restore the world to a captured checkpoint.

        Entity IDs are preserved, so any logic-event targets or scene
        references that were valid at capture time remain valid after
        restore. Returns False if the checkpoint is unknown.
        """
        cp = self._checkpoints.get(checkpoint_id)
        if cp is None:
            return False

        scene_by_id = cp.active_scene_id if cp.active_scene_id else None
        restored_ids: Dict[str, str] = {}  # new id -> original id

        new_scenes: Dict[str, Any] = {}
        for scene_data in cp.scenes:
            scene_id = scene_data["id"]
            new_scenes[scene_id] = scene_data

        # Rebuild engine._scenes preserving ids
        engine._scenes.clear()
        for scene_data in cp.scenes:
            scene = _rebuild_scene(scene_data, restored_ids)
            engine._scenes[scene.id] = scene

        # Restore active scene if it still exists
        if scene_by_id in engine._scenes:
            engine._active_scene_id = scene_by_id
        elif engine._scenes:
            engine._active_scene_id = next(iter(engine._scenes))

        # Restore engine tick and score bookkeeping
        if hasattr(engine, "_frame_count"):
            engine._frame_count = cp.engine_tick
        try:
            engine._game_logic_runtime.set_context("game", {"score": cp.score})
        except Exception:
            pass

        # Restore the logic-event registry so post-simulate rollback is faithful
        try:
            engine._game_logic_runtime._events = []
            engine._game_logic_runtime._compiled = []
            if cp.logic_events:
                for ev_dict in cp.logic_events:
                    engine._game_logic_runtime.add_event(_event_from_dict(ev_dict))
        except Exception as exc:
            logger.warning("Logic restore failed for checkpoint %s: %s", cp.id, exc)

        logger.debug("Restored checkpoint %s", cp.id)
        return True

    def discard_checkpoint(self, checkpoint_id: str) -> bool:
        return self._checkpoints.pop(checkpoint_id, None) is not None

    def clear_checkpoints(self) -> int:
        count = len(self._checkpoints)
        self._checkpoints.clear()
        return count

    def list_checkpoints(self) -> List[Dict[str, Any]]:
        return [cp.to_dict() for cp in sorted(
            self._checkpoints.values(), key=lambda c: c.created_at, reverse=True,
        )]

    def get_checkpoint(self, checkpoint_id: str) -> Optional[WorldCheckpoint]:
        return self._checkpoints.get(checkpoint_id)

    # ------------------------------------------------------------------
    # Sandbox predictive simulation
    # ------------------------------------------------------------------

    def simulate_frames(
        self,
        engine,
        frames: int = 60,
        delta_time: float = 1.0 / 60.0,
        commit: bool = False,
        reason: str = "predictive-simulation",
    ) -> Dict[str, Any]:
        """
        Step the world forward `frames` frames while recording a diff.

        By default the simulation is rolled back (predictive): the world
        returns to its pre-simulation state. Pass `commit=True` to keep
        the simulated outcome.

        Returns:
          {
            checkpoint_id, committed, frames_run, delta_time,
            before, after, diff, summary
          }
        """
        before_cp = self.capture_checkpoint(engine, reason="sandbox-before")
        if not engine._running:
            engine.start()

        before_state = _flatten_entity_state(engine)
        for _ in range(max(1, int(frames))):
            engine.update(delta_time)
        after_state = _flatten_entity_state(engine)
        if not commit:
            engine.stop()
            self.restore_checkpoint(engine, before_cp.id)
            self.discard_checkpoint(before_cp.id)
        else:
            after_cp = self.capture_checkpoint(engine, reason="sandbox-commit")
            self.discard_checkpoint(before_cp.id)

        diff = _diff_entity_state(before_state, after_state)
        result = {
            "checkpoint_id": before_cp.id,
            "committed": commit,
            "frames_run": max(1, int(frames)),
            "delta_time": delta_time,
            "before": before_state,
            "after": after_state,
            "diff": diff,
            "summary": _summarize_diff(diff),
        }
        return result

    def get_statistics(self) -> Dict[str, Any]:
        return {
            "total_checkpoints": len(self._checkpoints),
            "max_checkpoints": self._max,
        }


def _event_from_dict(data: Dict[str, Any]):
    """Rebuild a GameEvent (with conditions + actions) from its dict form."""
    from sparkai.engine.game_logic_ir import (
        GameEvent, Condition, GameAction, Expression, ConditionOperator, ActionType,
    )

    def _expr(d):
        if not d:
            return Expression()
        return Expression(
            type=d.get("type", "literal"),
            value=d.get("value"),
            variable_path=d.get("variable_path", ""),
            operator=d.get("operator", ""),
            operands=[_expr(o) for o in d.get("operands", [])],
        )

    event = GameEvent(
        id=data.get("id", ""),
        name=data.get("name", "Untitled Event"),
        description=data.get("description", ""),
        enabled=data.get("enabled", True),
        trigger_count=data.get("trigger_count", 0),
        max_triggers=data.get("max_triggers", -1),
        cooldown_ms=data.get("cooldown_ms", 0),
        priority=data.get("priority", 0),
    )
    for c in data.get("conditions", []):
        op_name = c.get("operator", "equals")
        try:
            op = ConditionOperator(op_name)
        except ValueError:
            op = ConditionOperator.EQUALS
        event.conditions.append(Condition(
            id=c.get("id", ""),
            left=_expr(c.get("left")),
            operator=op,
            right=_expr(c.get("right")),
        ))
    for a in data.get("actions", []):
        type_name = a.get("action_type", "custom")
        try:
            atype = ActionType(type_name)
        except ValueError:
            atype = ActionType.CUSTOM
        event.actions.append(GameAction(
            id=a.get("id", ""),
            action_type=atype,
            target=a.get("target", ""),
            params=copy.deepcopy(a.get("params", {})),
            delay_ms=a.get("delay_ms", 0),
            repeat_count=a.get("repeat_count", 1),
        ))
    return event


def _rebuild_scene(scene_data: Dict[str, Any], restored_ids: Dict[str, str]):
    from sparkai.engine.engine import Scene, SceneEntity

    scene = Scene(name=scene_data["name"], id=scene_data["id"])
    for ent_data in scene_data.get("entities", []):
        entity = SceneEntity(
            name=ent_data["name"],
            id=ent_data["id"],
            scene_id=scene.id,
            position=list(ent_data.get("position", [0.0, 0.0, 0.0])),
            rotation=list(ent_data.get("rotation", [0.0, 0.0, 0.0])),
            scale=list(ent_data.get("scale", [1.0, 1.0, 1.0])),
            tags=list(ent_data.get("tags", [])),
            components=copy.deepcopy(dict(ent_data.get("components", {}))),
            properties=copy.deepcopy(dict(ent_data.get("properties", {}))),
        )
        scene.entities[entity.id] = entity
    return scene


def _flatten_entity_state(engine) -> Dict[str, Dict[str, Any]]:
    """Flatten all scene entities into {entity_id: {props}} for diffing."""
    state: Dict[str, Dict[str, Any]] = {}
    for scene in engine._scenes.values():
        for entity in scene.entities.values():
            state[entity.id] = {
                "name": entity.name,
                "position": list(entity.position),
                "rotation": list(entity.rotation),
                "scale": list(entity.scale),
                "properties": copy.deepcopy(dict(entity.properties)),
            }
    return state


def _diff_entity_state(
    before: Dict[str, Dict[str, Any]],
    after: Dict[str, Dict[str, Any]],
) -> List[Dict[str, Any]]:
    diffs: List[Dict[str, Any]] = []
    for eid, before_ent in before.items():
        after_ent = after.get(eid)
        if after_ent is None:
            diffs.append({"entity_id": eid, "entity_name": before_ent["name"], "change": "removed"})
            continue
        changes: List[str] = []
        if before_ent["position"] != after_ent["position"]:
            changes.append("position")
        if before_ent["properties"] != after_ent["properties"]:
            changed_props = sorted(
                set(before_ent["properties"]) | set(after_ent["properties"])
            )
            changes.append(f"properties:{len(changed_props)}")
        if changes:
            diffs.append({
                "entity_id": eid,
                "entity_name": after_ent["name"],
                "change": ",".join(changes),
            })
    # New entities
    for eid, after_ent in after.items():
        if eid not in before:
            diffs.append({"entity_id": eid, "entity_name": after_ent["name"], "change": "added"})
    return diffs


def _summarize_diff(diffs: List[Dict[str, Any]]) -> str:
    if not diffs:
        return "No observable world change across the simulated frames."
    parts = [f"{d['change']}:{d['entity_name']}" for d in diffs[:8]]
    if len(diffs) > 8:
        parts.append(f"+{len(diffs) - 8} more")
    return "; ".join(parts)


_instance: Optional[WorldCheckpointService] = None


def get_world_checkpoint_service() -> WorldCheckpointService:
    """Return the process-wide WorldCheckpointService singleton."""
    global _instance
    if _instance is None:
        _instance = WorldCheckpointService()
    return _instance
