"""
SparkLabs Engine - Trigger System

Interactive spatial event triggering for AI-native games.
Manages volume-based and event-driven triggers with configurable
activation modes, tag-based filtering, and script binding for
quest progression, cutscene initiation, and gameplay logic.

Architecture:
  TriggerSystem
    |-- TriggerRegistry (trigger definition and spatial map)
    |-- OverlapDetector (volume-to-entity intersection tests)
    |-- ActivationController (mode and cooldown state machine)
    |-- ScriptBinder (on-activate and on-deactivate callbacks)

Trigger Types:
  - ENTER_ZONE, EXIT_ZONE, INTERACT, PROXIMITY
  - TIMER, COLLISION, CUSTOM_EVENT, CONDITIONAL

Trigger Shapes:
  - BOX, SPHERE, CYLINDER, CAPSULE, CONE, MESH

Activation Modes:
  - ONCE, REPEATABLE, COOLDOWN, TOGGLE
"""

from __future__ import annotations

import math
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple


class TriggerType(Enum):
    ENTER_ZONE = "enter_zone"
    EXIT_ZONE = "exit_zone"
    INTERACT = "interact"
    PROXIMITY = "proximity"
    TIMER = "timer"
    COLLISION = "collision"
    CUSTOM_EVENT = "custom_event"
    CONDITIONAL = "conditional"


class TriggerShape(Enum):
    BOX = "box"
    SPHERE = "sphere"
    CYLINDER = "cylinder"
    CAPSULE = "capsule"
    CONE = "cone"
    MESH = "mesh"


class TriggerActivation(Enum):
    ONCE = "once"
    REPEATABLE = "repeatable"
    COOLDOWN = "cooldown"
    TOGGLE = "toggle"


@dataclass
class TriggerEvent:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = ""
    trigger_type: TriggerType = TriggerType.ENTER_ZONE
    trigger_shape: TriggerShape = TriggerShape.BOX
    position_x: float = 0.0
    position_y: float = 0.0
    position_z: float = 0.0
    size_x: float = 1.0
    size_y: float = 1.0
    size_z: float = 1.0
    activation_mode: TriggerActivation = TriggerActivation.ONCE
    cooldown_seconds: float = 0.0
    required_tags: List[str] = field(default_factory=list)
    target_entities: List[str] = field(default_factory=list)
    on_activate_script: str = ""
    on_deactivate_script: str = ""
    enabled: bool = True
    firing_count: int = 0

    _last_fire_time: float = field(default=0.0, repr=False)
    _is_toggled_on: bool = field(default=False, repr=False)

    @property
    def position(self) -> Tuple[float, float, float]:
        return (self.position_x, self.position_y, self.position_z)

    @property
    def size(self) -> Tuple[float, float, float]:
        return (self.size_x, self.size_y, self.size_z)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "trigger_type": self.trigger_type.value,
            "trigger_shape": self.trigger_shape.value,
            "activation_mode": self.activation_mode.value,
            "enabled": self.enabled,
            "firing_count": self.firing_count,
            "position": list(self.position),
            "size": list(self.size),
        }

    def can_activate(self, current_time: float) -> bool:
        if not self.enabled:
            return False

        if self.activation_mode == TriggerActivation.ONCE:
            return self.firing_count == 0

        if self.activation_mode == TriggerActivation.COOLDOWN:
            if self.firing_count == 0:
                return True
            elapsed = current_time - self._last_fire_time
            return elapsed >= self.cooldown_seconds

        if self.activation_mode == TriggerActivation.TOGGLE:
            return True

        return True


class TriggerSystem:
    _instance: Optional[TriggerSystem] = None

    def __init__(self):
        self._triggers: Dict[str, TriggerEvent] = {}
        self._active_triggers: Dict[str, List[str]] = {}
        self._entity_overlaps: Dict[str, Dict[str, bool]] = {}
        self._on_activate_callbacks: Dict[str, List[Callable[[TriggerEvent], None]]] = {}
        self._on_deactivate_callbacks: Dict[str, List[Callable[[TriggerEvent], None]]] = {}
        self._total_firings: int = 0

    @classmethod
    def get_instance(cls) -> TriggerSystem:
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def create_trigger(
        self,
        name: str,
        trigger_type: TriggerType = TriggerType.ENTER_ZONE,
        trigger_shape: TriggerShape = TriggerShape.BOX,
        position: Tuple[float, float, float] = (0.0, 0.0, 0.0),
        size: Tuple[float, float, float] = (1.0, 1.0, 1.0),
        activation_mode: TriggerActivation = TriggerActivation.ONCE,
        cooldown_seconds: float = 0.0,
        required_tags: Optional[List[str]] = None,
        on_activate_script: str = "",
        on_deactivate_script: str = "",
    ) -> str:
        trigger = TriggerEvent(
            name=name,
            trigger_type=trigger_type,
            trigger_shape=trigger_shape,
            position_x=position[0],
            position_y=position[1],
            position_z=position[2],
            size_x=size[0],
            size_y=size[1],
            size_z=size[2],
            activation_mode=activation_mode,
            cooldown_seconds=cooldown_seconds,
            required_tags=required_tags or [],
            on_activate_script=on_activate_script,
            on_deactivate_script=on_deactivate_script,
        )
        self._triggers[trigger.id] = trigger
        self._active_triggers[trigger.id] = []
        self._entity_overlaps[trigger.id] = {}
        self._on_activate_callbacks[trigger.id] = []
        self._on_deactivate_callbacks[trigger.id] = []
        return trigger.id

    def remove_trigger(self, trigger_id: str) -> bool:
        if trigger_id not in self._triggers:
            return False
        del self._triggers[trigger_id]
        self._active_triggers.pop(trigger_id, None)
        self._entity_overlaps.pop(trigger_id, None)
        self._on_activate_callbacks.pop(trigger_id, None)
        self._on_deactivate_callbacks.pop(trigger_id, None)
        return True

    def enable_trigger(self, trigger_id: str) -> bool:
        trigger = self._triggers.get(trigger_id)
        if trigger is None:
            return False
        trigger.enabled = True
        return True

    def disable_trigger(self, trigger_id: str) -> bool:
        trigger = self._triggers.get(trigger_id)
        if trigger is None:
            return False
        trigger.enabled = False
        return True

    def check_overlaps(
        self,
        trigger_id: str,
        entity_id: str,
        entity_position: Tuple[float, float, float],
        entity_tags: Optional[List[str]] = None,
    ) -> bool:
        trigger = self._triggers.get(trigger_id)
        if trigger is None or not trigger.enabled:
            return False

        entity_tags = entity_tags or []

        if trigger.required_tags:
            if not any(tag in entity_tags for tag in trigger.required_tags):
                return False

        tx, ty, tz = trigger.position
        tsx, tsy, tsz = trigger.size
        ex, ey, ez = entity_position

        if trigger.trigger_shape == TriggerShape.BOX:
            half_x = tsx / 2
            half_y = tsy / 2
            half_z = tsz / 2
            return (
                abs(ex - tx) <= half_x
                and abs(ey - ty) <= half_y
                and abs(ez - tz) <= half_z
            )

        if trigger.trigger_shape == TriggerShape.SPHERE:
            radius = tsx / 2
            dx = ex - tx
            dy = ey - ty
            dz = ez - tz
            return (dx * dx + dy * dy + dz * dz) <= (radius * radius)

        if trigger.trigger_shape == TriggerShape.CYLINDER:
            radius = tsx / 2
            half_height = tsy / 2
            dx = ex - tx
            dz = ez - tz
            return (
                (dx * dx + dz * dz) <= (radius * radius)
                and abs(ey - ty) <= half_height
            )

        if trigger.trigger_shape == TriggerShape.CAPSULE:
            radius = tsx / 2
            half_length = tsy / 2
            dx = ex - tx
            dy = max(0.0, abs(ey - ty) - half_length)
            dz = ez - tz
            return (dx * dx + dy * dy + dz * dz) <= (radius * radius)

        if trigger.trigger_shape == TriggerShape.CONE:
            radius_at_base = tsx / 2
            half_height = tsy / 2
            dy = ey - ty
            if dy < -half_height or dy > half_height:
                return False
            t = (dy + half_height) / (2 * half_height)
            current_radius = radius_at_base * (1.0 - t)
            dx = ex - tx
            dz = ez - tz
            return (dx * dx + dz * dz) <= (current_radius * current_radius)

        if trigger.trigger_shape == TriggerShape.MESH:
            half_x = tsx / 2
            half_y = tsy / 2
            half_z = tsz / 2
            return (
                abs(ex - tx) <= half_x
                and abs(ey - ty) <= half_y
                and abs(ez - tz) <= half_z
            )

        return False

    def fire_trigger(
        self,
        trigger_id: str,
        entity_id: str = "",
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        trigger = self._triggers.get(trigger_id)
        if trigger is None:
            return {"fired": False, "reason": "trigger not found"}

        if not trigger.can_activate(time.time()):
            return {"fired": False, "reason": "cannot activate"}

        trigger.firing_count += 1
        trigger._last_fire_time = time.time()
        self._total_firings += 1

        if trigger.activation_mode == TriggerActivation.TOGGLE:
            trigger._is_toggled_on = not trigger._is_toggled_on

        if entity_id:
            if entity_id not in self._active_triggers[trigger_id]:
                self._active_triggers[trigger_id].append(entity_id)

        for callback in self._on_activate_callbacks.get(trigger_id, []):
            callback(trigger)

        return {
            "fired": True,
            "trigger_id": trigger_id,
            "trigger_name": trigger.name,
            "firing_count": trigger.firing_count,
        }

    def get_active_triggers(self) -> List[Dict[str, Any]]:
        active = []
        for trigger_id, trigger in self._triggers.items():
            if trigger.enabled:
                active.append(trigger.to_dict())
        return active

    def get_trigger(self, trigger_id: str) -> Optional[TriggerEvent]:
        return self._triggers.get(trigger_id)

    def get_entities_in_trigger(self, trigger_id: str) -> List[str]:
        return list(self._active_triggers.get(trigger_id, []))

    def bind_activate_callback(
        self, trigger_id: str, callback: Callable[[TriggerEvent], None]
    ) -> bool:
        if trigger_id not in self._triggers:
            return False
        self._on_activate_callbacks.setdefault(trigger_id, []).append(callback)
        return True

    def bind_deactivate_callback(
        self, trigger_id: str, callback: Callable[[TriggerEvent], None]
    ) -> bool:
        if trigger_id not in self._triggers:
            return False
        self._on_deactivate_callbacks.setdefault(trigger_id, []).append(callback)
        return True

    def clear_callbacks(self, trigger_id: str) -> bool:
        if trigger_id not in self._triggers:
            return False
        self._on_activate_callbacks[trigger_id] = []
        self._on_deactivate_callbacks[trigger_id] = []
        return True

    def reset_trigger(self, trigger_id: str) -> bool:
        trigger = self._triggers.get(trigger_id)
        if trigger is None:
            return False
        trigger.firing_count = 0
        trigger._last_fire_time = 0.0
        trigger._is_toggled_on = False
        self._active_triggers[trigger_id] = []
        self._entity_overlaps[trigger_id] = {}
        return True

    def get_all_triggers(self) -> Dict[str, TriggerEvent]:
        return dict(self._triggers)

    def get_stats(self) -> Dict[str, Any]:
        trigger_details = {}
        for trigger_id, trigger in self._triggers.items():
            activation_state = "active"
            if trigger.activation_mode == TriggerActivation.ONCE and trigger.firing_count > 0:
                activation_state = "consumed"
            elif trigger.activation_mode == TriggerActivation.TOGGLE:
                activation_state = "on" if trigger._is_toggled_on else "off"
            trigger_details[trigger_id] = {
                "name": trigger.name,
                "type": trigger.trigger_type.value,
                "activation_mode": trigger.activation_mode.value,
                "enabled": trigger.enabled,
                "firing_count": trigger.firing_count,
                "state": activation_state,
            }
        return {
            "total_triggers": len(self._triggers),
            "total_firings": self._total_firings,
            "triggers": trigger_details,
        }


def get_trigger_system() -> TriggerSystem:
    return TriggerSystem.get_instance()