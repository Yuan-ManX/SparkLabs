"""
SparkLabs Engine - Object Behavior Library

Collection of pre-built reusable game object behaviors that can be
attached to any game entity. Behaviors are parameterized templates
that define movement, combat, interaction, AI, physics, animation,
UI, trigger, camera, and audio logic. Instances are created from
templates with entity-specific parameter overrides.

Architecture:
  ObjectBehaviorLibrary
    |-- BehaviorTemplate (named reusable behavior with typed parameters)
    |-- BehaviorParameter (typed parameter with defaults and constraints)
    |-- BehaviorInstance (entity-bound instance with overridden values)
    |-- Builtin Templates (10 curated behaviors for common game logic)
"""

from __future__ import annotations

import json
import math
import threading
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Domain Enumerations
# ---------------------------------------------------------------------------


class BehaviorCategory(Enum):
    MOVEMENT = "movement"
    COMBAT = "combat"
    INTERACTION = "interaction"
    AI = "ai"
    PHYSICS = "physics"
    ANIMATION = "animation"
    UI = "ui"
    TRIGGER = "trigger"
    CAMERA = "camera"
    AUDIO = "audio"


class BehaviorExecutionMode(Enum):
    UPDATE = "update"
    FIXED_UPDATE = "fixed_update"
    LATE_UPDATE = "late_update"
    EVENT_DRIVEN = "event_driven"
    COROUTINE = "coroutine"


class BehaviorParameterType(Enum):
    FLOAT = "float"
    INT = "int"
    BOOL = "bool"
    STRING = "string"
    VECTOR2 = "vector2"
    VECTOR3 = "vector3"
    COLOR = "color"
    ENUM = "enum"
    GAMEOBJECT = "gameobject"
    CURVE = "curve"


# ---------------------------------------------------------------------------
# Data Classes
# ---------------------------------------------------------------------------


@dataclass
class BehaviorParameter:
    """Typed parameter definition with defaults, constraints, and description."""

    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = ""
    param_type: BehaviorParameterType = BehaviorParameterType.FLOAT
    default_value: Any = 0.0
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    description: str = ""
    required: bool = False
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "param_type": self.param_type.value,
            "default_value": self.default_value,
            "min_value": self.min_value,
            "max_value": self.max_value,
            "description": self.description,
            "required": self.required,
            "created_at": self.created_at,
        }


@dataclass
class BehaviorTemplate:
    """Named, categorized behavior with typed parameters and execution settings."""

    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = ""
    category: BehaviorCategory = BehaviorCategory.MOVEMENT
    description: str = ""
    parameters: Dict[str, BehaviorParameter] = field(default_factory=dict)
    execution_mode: BehaviorExecutionMode = BehaviorExecutionMode.UPDATE
    priority: int = 0
    tags: List[str] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "category": self.category.value,
            "description": self.description,
            "parameters": {k: v.to_dict() for k, v in self.parameters.items()},
            "execution_mode": self.execution_mode.value,
            "priority": self.priority,
            "tags": list(self.tags),
            "created_at": self.created_at,
        }


@dataclass
class BehaviorInstance:
    """Entity-bound behavior instance with parameter overrides and runtime state."""

    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    template_id: str = ""
    entity_id: str = ""
    parameter_values: Dict[str, Any] = field(default_factory=dict)
    enabled: bool = True
    execution_order: int = 0
    state: Dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "template_id": self.template_id,
            "entity_id": self.entity_id,
            "parameter_values": dict(self.parameter_values),
            "enabled": self.enabled,
            "execution_order": self.execution_order,
            "state": dict(self.state),
            "created_at": self.created_at,
        }


# ---------------------------------------------------------------------------
# Object Behavior Library (Singleton)
# ---------------------------------------------------------------------------


class ObjectBehaviorLibrary:
    """Collection of pre-built reusable game object behaviors."""

    _instance: Optional["ObjectBehaviorLibrary"] = None
    _lock = threading.RLock()

    def __init__(self) -> None:
        self._templates: Dict[str, BehaviorTemplate] = {}
        self._instances: Dict[str, BehaviorInstance] = {}
        self._entity_index: Dict[str, List[str]] = {}
        self._builtins_registered: bool = False

    @classmethod
    def get_instance(cls) -> "ObjectBehaviorLibrary":
        """Thread-safe singleton accessor."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    # ------------------------------------------------------------------
    # Template Registration
    # ------------------------------------------------------------------

    def register_template(
        self,
        name: str,
        category: BehaviorCategory,
        description: str = "",
        parameters: Optional[List[BehaviorParameter]] = None,
        execution_mode: BehaviorExecutionMode = BehaviorExecutionMode.UPDATE,
        priority: int = 0,
        tags: Optional[List[str]] = None,
    ) -> BehaviorTemplate:
        """Register a new behavior template in the library."""
        param_map: Dict[str, BehaviorParameter] = {}
        for p in (parameters or []):
            param_map[p.name] = p
        template = BehaviorTemplate(
            name=name,
            category=category,
            description=description,
            parameters=param_map,
            execution_mode=execution_mode,
            priority=priority,
            tags=tags or [],
        )
        self._templates[template.id] = template
        return template

    def unregister_template(self, template_id: str) -> bool:
        """Remove a behavior template and all its instances."""
        if template_id not in self._templates:
            return False
        instance_ids = [
            iid for iid, inst in self._instances.items()
            if inst.template_id == template_id
        ]
        for iid in instance_ids:
            self._remove_instance_from_index(iid)
            del self._instances[iid]
        del self._templates[template_id]
        return True

    def get_template(self, template_id: str) -> Optional[BehaviorTemplate]:
        """Retrieve a template by id."""
        return self._templates.get(template_id)

    # ------------------------------------------------------------------
    # Instance Management
    # ------------------------------------------------------------------

    def instantiate_behavior(
        self,
        template_id: str,
        entity_id: str,
        parameter_overrides: Optional[Dict[str, Any]] = None,
    ) -> Optional[BehaviorInstance]:
        """Create a behavior instance bound to an entity with optional overrides."""
        template = self._templates.get(template_id)
        if template is None:
            return None
        parameter_values: Dict[str, Any] = {}
        for pname, pdef in template.parameters.items():
            parameter_values[pname] = pdef.default_value
        if parameter_overrides:
            for key, value in parameter_overrides.items():
                if key in template.parameters:
                    parameter_values[key] = value
        instance = BehaviorInstance(
            template_id=template_id,
            entity_id=entity_id,
            parameter_values=parameter_values,
            execution_order=len(self._get_entity_instance_ids(entity_id)),
        )
        self._instances[instance.id] = instance
        self._index_instance(entity_id, instance.id)
        return instance

    def apply_behavior(self, instance_id: str) -> bool:
        """Activate a behavior instance on its entity."""
        instance = self._instances.get(instance_id)
        if instance is None:
            return False
        instance.enabled = True
        return True

    def remove_behavior(self, instance_id: str) -> bool:
        """Detach a behavior instance from its entity."""
        instance = self._instances.get(instance_id)
        if instance is None:
            return False
        self._remove_instance_from_index(instance_id)
        del self._instances[instance_id]
        return True

    def get_entity_behaviors(self, entity_id: str) -> List[BehaviorInstance]:
        """Return all behavior instances attached to an entity."""
        instance_ids = self._entity_index.get(entity_id, [])
        return [
            self._instances[iid] for iid in instance_ids
            if iid in self._instances
        ]

    def update_behavior_parameter(
        self, instance_id: str, param_name: str, new_value: Any
    ) -> bool:
        """Update a parameter value on a behavior instance."""
        instance = self._instances.get(instance_id)
        if instance is None:
            return False
        template = self._templates.get(instance.template_id)
        if template is None or param_name not in template.parameters:
            return False
        instance.parameter_values[param_name] = new_value
        return True

    def toggle_behavior(self, instance_id: str, enabled: bool) -> bool:
        """Enable or disable a behavior instance."""
        instance = self._instances.get(instance_id)
        if instance is None:
            return False
        instance.enabled = enabled
        return True

    # ------------------------------------------------------------------
    # Search and Discovery
    # ------------------------------------------------------------------

    def search_templates(
        self,
        category: Optional[BehaviorCategory] = None,
        tags: Optional[List[str]] = None,
        name_query: str = "",
    ) -> List[BehaviorTemplate]:
        """Search behavior templates by category, tags, or name substring."""
        results = list(self._templates.values())
        if category is not None:
            results = [t for t in results if t.category == category]
        if tags:
            results = [
                t for t in results
                if any(tag in t.tags for tag in tags)
            ]
        if name_query:
            q = name_query.lower()
            results = [
                t for t in results
                if q in t.name.lower() or q in t.description.lower()
            ]
        results.sort(key=lambda t: t.name)
        return results

    # ------------------------------------------------------------------
    # Clone and Transfer
    # ------------------------------------------------------------------

    def clone_behavior(
        self, instance_id: str, target_entity_id: str
    ) -> Optional[BehaviorInstance]:
        """Clone a behavior instance to another entity."""
        source = self._instances.get(instance_id)
        if source is None:
            return None
        cloned = BehaviorInstance(
            template_id=source.template_id,
            entity_id=target_entity_id,
            parameter_values=dict(source.parameter_values),
            execution_order=len(self._get_entity_instance_ids(target_entity_id)),
            state=dict(source.state),
        )
        self._instances[cloned.id] = cloned
        self._index_instance(target_entity_id, cloned.id)
        return cloned

    # ------------------------------------------------------------------
    # Import / Export
    # ------------------------------------------------------------------

    def export_template(self, template_id: str) -> Dict[str, Any]:
        """Serialize a behavior template to a portable dictionary."""
        template = self._templates.get(template_id)
        if template is None:
            return {}
        return {
            "version": 1,
            "template": template.to_dict(),
        }

    def import_template(self, config: Dict[str, Any]) -> Optional[BehaviorTemplate]:
        """Deserialize and register a behavior template from a config dict."""
        tdata = config.get("template", {})
        if not tdata:
            return None
        category_raw = tdata.get("category", "movement")
        try:
            category = BehaviorCategory(category_raw.lower())
        except ValueError:
            category = BehaviorCategory.MOVEMENT
        exec_raw = tdata.get("execution_mode", "update")
        try:
            execution_mode = BehaviorExecutionMode(exec_raw.lower())
        except ValueError:
            execution_mode = BehaviorExecutionMode.UPDATE
        parameters: List[BehaviorParameter] = []
        for pdata in tdata.get("parameters", {}).values():
            if isinstance(pdata, dict):
                ptype_raw = pdata.get("param_type", "float")
                try:
                    ptype = BehaviorParameterType(ptype_raw.lower())
                except ValueError:
                    ptype = BehaviorParameterType.FLOAT
                parameters.append(BehaviorParameter(
                    name=pdata.get("name", ""),
                    param_type=ptype,
                    default_value=pdata.get("default_value", 0.0),
                    min_value=pdata.get("min_value"),
                    max_value=pdata.get("max_value"),
                    description=pdata.get("description", ""),
                    required=pdata.get("required", False),
                ))
        template = BehaviorTemplate(
            name=tdata.get("name", "imported"),
            category=category,
            description=tdata.get("description", ""),
            parameters={p.name: p for p in parameters},
            execution_mode=execution_mode,
            priority=tdata.get("priority", 0),
            tags=tdata.get("tags", []),
        )
        self._templates[template.id] = template
        return template

    # ------------------------------------------------------------------
    # Built-in Behaviors
    # ------------------------------------------------------------------

    def get_builtin_templates(self) -> List[BehaviorTemplate]:
        """Return the set of built-in behavior templates."""
        if not self._builtins_registered:
            self._register_builtins()
            self._builtins_registered = True
        builtin_names = {
            "PlatformMovement", "FollowTarget", "AutoRotate",
            "HealthSystem", "Collectible", "PatrolPath",
            "DestroyOnTrigger", "ScreenWrap", "FloatBobbing", "TimerEvent",
        }
        return [t for t in self._templates.values() if t.name in builtin_names]

    def _register_builtins(self) -> None:
        """Register all ten built-in behavior templates."""
        self._register_platform_movement()
        self._register_follow_target()
        self._register_auto_rotate()
        self._register_health_system()
        self._register_collectible()
        self._register_patrol_path()
        self._register_destroy_on_trigger()
        self._register_screen_wrap()
        self._register_float_bobbing()
        self._register_timer_event()

    def _register_platform_movement(self) -> None:
        params = [
            BehaviorParameter(name="speed", param_type=BehaviorParameterType.FLOAT,
                              default_value=200.0, min_value=0.0, description="Movement speed"),
            BehaviorParameter(name="movement_mode", param_type=BehaviorParameterType.ENUM,
                              default_value="top_down", description="top_down, platformer, grid"),
            BehaviorParameter(name="gravity", param_type=BehaviorParameterType.FLOAT,
                              default_value=980.0, min_value=0.0, description="Gravity strength"),
            BehaviorParameter(name="jump_force", param_type=BehaviorParameterType.FLOAT,
                              default_value=400.0, min_value=0.0, description="Jump impulse"),
            BehaviorParameter(name="grid_size", param_type=BehaviorParameterType.INT,
                              default_value=32, min_value=1, description="Grid cell size"),
        ]
        self.register_template(
            name="PlatformMovement",
            category=BehaviorCategory.MOVEMENT,
            description="Top-down, platformer, and grid-based movement with configurable speed and physics.",
            parameters=params,
            execution_mode=BehaviorExecutionMode.FIXED_UPDATE,
            tags=["movement", "platformer", "top_down", "grid"],
        )

    def _register_follow_target(self) -> None:
        params = [
            BehaviorParameter(name="target_entity_id", param_type=BehaviorParameterType.GAMEOBJECT,
                              default_value="", description="Entity to follow"),
            BehaviorParameter(name="follow_mode", param_type=BehaviorParameterType.ENUM,
                              default_value="smooth", description="smooth, snap, offset"),
            BehaviorParameter(name="follow_speed", param_type=BehaviorParameterType.FLOAT,
                              default_value=5.0, min_value=0.0, description="Smooth follow speed"),
            BehaviorParameter(name="offset_x", param_type=BehaviorParameterType.FLOAT,
                              default_value=0.0, description="Horizontal offset"),
            BehaviorParameter(name="offset_y", param_type=BehaviorParameterType.FLOAT,
                              default_value=0.0, description="Vertical offset"),
            BehaviorParameter(name="min_distance", param_type=BehaviorParameterType.FLOAT,
                              default_value=1.0, min_value=0.0, description="Minimum follow distance"),
        ]
        self.register_template(
            name="FollowTarget",
            category=BehaviorCategory.MOVEMENT,
            description="Smooth follow, snap, or offset-based following of a target entity.",
            parameters=params,
            execution_mode=BehaviorExecutionMode.UPDATE,
            tags=["movement", "follow", "camera"],
        )

    def _register_auto_rotate(self) -> None:
        params = [
            BehaviorParameter(name="rotation_mode", param_type=BehaviorParameterType.ENUM,
                              default_value="constant", description="constant, look_at, oscillation"),
            BehaviorParameter(name="rotation_speed", param_type=BehaviorParameterType.FLOAT,
                              default_value=90.0, description="Degrees per second"),
            BehaviorParameter(name="look_at_target", param_type=BehaviorParameterType.GAMEOBJECT,
                              default_value="", description="Target for look-at mode"),
            BehaviorParameter(name="oscillation_amplitude", param_type=BehaviorParameterType.FLOAT,
                              default_value=30.0, description="Oscillation angle range"),
            BehaviorParameter(name="oscillation_frequency", param_type=BehaviorParameterType.FLOAT,
                              default_value=1.0, min_value=0.0, description="Oscillation frequency"),
        ]
        self.register_template(
            name="AutoRotate",
            category=BehaviorCategory.MOVEMENT,
            description="Constant-speed rotation, look-at-target tracking, or angle oscillation.",
            parameters=params,
            execution_mode=BehaviorExecutionMode.UPDATE,
            tags=["rotation", "movement"],
        )

    def _register_health_system(self) -> None:
        params = [
            BehaviorParameter(name="max_hp", param_type=BehaviorParameterType.FLOAT,
                              default_value=100.0, min_value=1.0, description="Maximum health"),
            BehaviorParameter(name="current_hp", param_type=BehaviorParameterType.FLOAT,
                              default_value=100.0, min_value=0.0, description="Current health"),
            BehaviorParameter(name="invincible_duration", param_type=BehaviorParameterType.FLOAT,
                              default_value=0.0, min_value=0.0, description="Seconds of invincibility after hit"),
            BehaviorParameter(name="auto_heal_rate", param_type=BehaviorParameterType.FLOAT,
                              default_value=0.0, min_value=0.0, description="HP regenerated per second"),
            BehaviorParameter(name="death_delay", param_type=BehaviorParameterType.FLOAT,
                              default_value=0.0, min_value=0.0, description="Delay before death event fires"),
        ]
        self.register_template(
            name="HealthSystem",
            category=BehaviorCategory.COMBAT,
            description="HP management with damage, heal, invincibility frames, and death events.",
            parameters=params,
            execution_mode=BehaviorExecutionMode.UPDATE,
            tags=["combat", "health", "damage"],
        )

    def _register_collectible(self) -> None:
        params = [
            BehaviorParameter(name="collection_radius", param_type=BehaviorParameterType.FLOAT,
                              default_value=32.0, min_value=0.0, description="Pickup detection radius"),
            BehaviorParameter(name="auto_collect", param_type=BehaviorParameterType.BOOL,
                              default_value=True, description="Whether to auto-collect on overlap"),
            BehaviorParameter(name="collect_fly_speed", param_type=BehaviorParameterType.FLOAT,
                              default_value=400.0, min_value=0.0, description="Fly-toward-player speed"),
            BehaviorParameter(name="inventory_item_id", param_type=BehaviorParameterType.STRING,
                              default_value="", description="Item to add to inventory"),
            BehaviorParameter(name="destroy_on_collect", param_type=BehaviorParameterType.BOOL,
                              default_value=True, description="Remove entity after collection"),
        ]
        self.register_template(
            name="Collectible",
            category=BehaviorCategory.INTERACTION,
            description="Pickup detection with auto-collect, inventory integration, and fly-to-player.",
            parameters=params,
            execution_mode=BehaviorExecutionMode.UPDATE,
            tags=["interaction", "collectible", "inventory"],
        )

    def _register_patrol_path(self) -> None:
        params = [
            BehaviorParameter(name="waypoints", param_type=BehaviorParameterType.STRING,
                              default_value="[]", description="JSON array of {x, y} points"),
            BehaviorParameter(name="patrol_speed", param_type=BehaviorParameterType.FLOAT,
                              default_value=100.0, min_value=0.0, description="Movement speed between waypoints"),
            BehaviorParameter(name="pause_at_waypoint", param_type=BehaviorParameterType.FLOAT,
                              default_value=0.5, min_value=0.0, description="Seconds to pause at each waypoint"),
            BehaviorParameter(name="patrol_loop", param_type=BehaviorParameterType.BOOL,
                              default_value=True, description="Whether to loop or ping-pong"),
        ]
        self.register_template(
            name="PatrolPath",
            category=BehaviorCategory.AI,
            description="Waypoint-based patrol with configurable speed, pause durations, and loop mode.",
            parameters=params,
            execution_mode=BehaviorExecutionMode.UPDATE,
            tags=["ai", "patrol", "waypoint", "movement"],
        )

    def _register_destroy_on_trigger(self) -> None:
        params = [
            BehaviorParameter(name="target_tags", param_type=BehaviorParameterType.STRING,
                              default_value="", description="Comma-separated tags that trigger destruction"),
            BehaviorParameter(name="destroy_delay", param_type=BehaviorParameterType.FLOAT,
                              default_value=0.0, min_value=0.0, description="Seconds before destruction"),
            BehaviorParameter(name="spawn_effect_on_destroy", param_type=BehaviorParameterType.STRING,
                              default_value="", description="Effect prefab to spawn on destruction"),
        ]
        self.register_template(
            name="DestroyOnTrigger",
            category=BehaviorCategory.TRIGGER,
            description="Self-destruct when triggered by entities with matching tags.",
            parameters=params,
            execution_mode=BehaviorExecutionMode.EVENT_DRIVEN,
            tags=["trigger", "destroy", "collision"],
        )

    def _register_screen_wrap(self) -> None:
        params = [
            BehaviorParameter(name="wrap_horizontal", param_type=BehaviorParameterType.BOOL,
                              default_value=True, description="Wrap on horizontal edges"),
            BehaviorParameter(name="wrap_vertical", param_type=BehaviorParameterType.BOOL,
                              default_value=True, description="Wrap on vertical edges"),
        ]
        self.register_template(
            name="ScreenWrap",
            category=BehaviorCategory.MOVEMENT,
            description="Wrap entity position around screen edges in horizontal and vertical axes.",
            parameters=params,
            execution_mode=BehaviorExecutionMode.LATE_UPDATE,
            tags=["movement", "wrap", "screen"],
        )

    def _register_float_bobbing(self) -> None:
        params = [
            BehaviorParameter(name="amplitude", param_type=BehaviorParameterType.FLOAT,
                              default_value=10.0, min_value=0.0, description="Vertical bob amplitude"),
            BehaviorParameter(name="frequency", param_type=BehaviorParameterType.FLOAT,
                              default_value=2.0, min_value=0.0, description="Bob frequency in Hz"),
            BehaviorParameter(name="phase_offset", param_type=BehaviorParameterType.FLOAT,
                              default_value=0.0, description="Phase offset in radians"),
        ]
        self.register_template(
            name="FloatBobbing",
            category=BehaviorCategory.MOVEMENT,
            description="Sinusoidal vertical floating movement with configurable amplitude and frequency.",
            parameters=params,
            execution_mode=BehaviorExecutionMode.UPDATE,
            tags=["movement", "bobbing", "floating"],
        )

    def _register_timer_event(self) -> None:
        params = [
            BehaviorParameter(name="interval", param_type=BehaviorParameterType.FLOAT,
                              default_value=1.0, min_value=0.0, description="Timer interval in seconds"),
            BehaviorParameter(name="repeat", param_type=BehaviorParameterType.BOOL,
                              default_value=True, description="Whether the timer repeats"),
            BehaviorParameter(name="event_name", param_type=BehaviorParameterType.STRING,
                              default_value="timer_tick", description="Event name to dispatch"),
            BehaviorParameter(name="start_immediately", param_type=BehaviorParameterType.BOOL,
                              default_value=True, description="Fire first event immediately"),
        ]
        self.register_template(
            name="TimerEvent",
            category=BehaviorCategory.UI,
            description="Trigger named events on a configurable timer interval.",
            parameters=params,
            execution_mode=BehaviorExecutionMode.UPDATE,
            tags=["timer", "event", "utility"],
        )

    # ------------------------------------------------------------------
    # Index Helpers
    # ------------------------------------------------------------------

    def _index_instance(self, entity_id: str, instance_id: str) -> None:
        if entity_id not in self._entity_index:
            self._entity_index[entity_id] = []
        if instance_id not in self._entity_index[entity_id]:
            self._entity_index[entity_id].append(instance_id)

    def _remove_instance_from_index(self, instance_id: str) -> None:
        instance = self._instances.get(instance_id)
        if instance is None:
            return
        eid = instance.entity_id
        if eid in self._entity_index and instance_id in self._entity_index[eid]:
            self._entity_index[eid].remove(instance_id)
            if not self._entity_index[eid]:
                del self._entity_index[eid]

    def _get_entity_instance_ids(self, entity_id: str) -> List[str]:
        return self._entity_index.get(entity_id, [])

    # ------------------------------------------------------------------
    # Statistics
    # ------------------------------------------------------------------

    def get_stats(self) -> Dict[str, Any]:
        category_counts: Dict[str, int] = {}
        for t in self._templates.values():
            k = t.category.value
            category_counts[k] = category_counts.get(k, 0) + 1
        enabled_count = sum(1 for i in self._instances.values() if i.enabled)
        return {
            "total_templates": len(self._templates),
            "total_instances": len(self._instances),
            "enabled_instances": enabled_count,
            "disabled_instances": len(self._instances) - enabled_count,
            "unique_entities": len(self._entity_index),
            "category_distribution": category_counts,
            "builtins_registered": self._builtins_registered,
        }


# ---------------------------------------------------------------------------
# Module Accessor
# ---------------------------------------------------------------------------


def get_behavior_library() -> ObjectBehaviorLibrary:
    """Return the singleton ObjectBehaviorLibrary instance."""
    return ObjectBehaviorLibrary.get_instance()