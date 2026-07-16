"""
SparkLabs Engine - Behavior Composer

A behavior composition system that allows
attaching composable, reusable behavior components to game objects. Behaviors can
be mixed and matched on game objects, providing a flexible architecture for
building complex game entity logic without deep inheritance hierarchies.

Architecture:
  BehaviorComposerEngine (singleton)
    |-- BehaviorTemplateLibrary (manages behavior template definitions)
    |-- BehaviorInstanceManager (manages behavior instance lifecycle)
    |-- BehaviorSlotManager (manages behavior slots on objects)
    |-- BehaviorConflictResolver (resolves conflicts between behaviors)
    |-- BehaviorEventBus (routes events between behaviors)

Usage:
    composer = get_behavior_composer()
    instance = composer.create_instance("PlatformerMovement", "player_1")
    composer.attach_behavior("player_1", instance.instance_id)
    composer.update_composition("player_1", 0.016)
"""

from __future__ import annotations

import datetime
import json
import math
import random
import threading
import time
import uuid
from collections import defaultdict, deque
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple

_time_module = time


# ---------------------------------------------------------------------------
# Domain Enums
# ---------------------------------------------------------------------------


class BehaviorCategory(Enum):
    """Classification of behaviors by domain."""
    MOVEMENT = "movement"
    PHYSICS = "physics"
    RENDERING = "rendering"
    INPUT = "input"
    AI = "ai"
    COMBAT = "combat"
    INTERACTION = "interaction"
    ANIMATION = "animation"
    AUDIO = "audio"
    UI = "ui"
    NETWORK = "network"
    CUSTOM = "custom"


class BehaviorPriority(Enum):
    """Execution priority for behaviors within a composition."""
    CRITICAL = "critical"
    HIGH = "high"
    NORMAL = "normal"
    LOW = "low"
    BACKGROUND = "background"


class BehaviorLifecycle(Enum):
    """Lifecycle states for a behavior instance."""
    CREATED = "created"
    INITIALIZED = "initialized"
    ACTIVE = "active"
    PAUSED = "paused"
    DEACTIVATED = "deactivated"
    DESTROYED = "destroyed"


class UpdateOrder(Enum):
    """Order in which behaviors are updated during a frame."""
    PRE_UPDATE = "pre_update"
    UPDATE = "update"
    POST_UPDATE = "post_update"
    LATE_UPDATE = "late_update"


class CompositionMode(Enum):
    """Execution strategy for behaviors within a composition."""
    SEQUENTIAL = "sequential"
    PARALLEL = "parallel"
    SELECTIVE = "selective"
    PRIORITY_BASED = "priority_based"


# ---------------------------------------------------------------------------
# Data Classes
# ---------------------------------------------------------------------------


@dataclass
class BehaviorTemplate:
    """A reusable behavior definition that can be instantiated on game objects."""
    template_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    name: str = ""
    category: BehaviorCategory = BehaviorCategory.CUSTOM
    description: str = ""
    parameters: Dict[str, Any] = field(default_factory=dict)
    default_values: Dict[str, Any] = field(default_factory=dict)
    required_components: List[str] = field(default_factory=list)
    conflicts_with: List[str] = field(default_factory=list)
    update_order: UpdateOrder = UpdateOrder.UPDATE
    version: str = "1.0.0"


@dataclass
class BehaviorInstance:
    """A runtime instance of a behavior template bound to a game object."""
    instance_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    template: Optional[BehaviorTemplate] = None
    owner_object_id: str = ""
    parameter_values: Dict[str, Any] = field(default_factory=dict)
    state: BehaviorLifecycle = BehaviorLifecycle.CREATED
    priority: BehaviorPriority = BehaviorPriority.NORMAL
    enabled: bool = True
    created_at: float = field(default_factory=_time_module.time)
    last_updated: float = field(default_factory=_time_module.time)


@dataclass
class BehaviorSlot:
    """A named slot on a game object that can hold one or more behaviors."""
    slot_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    slot_name: str = ""
    accepted_categories: List[BehaviorCategory] = field(default_factory=list)
    current_behavior: str = ""
    max_behaviors: int = 1
    is_required: bool = False


@dataclass
class BehaviorComposition:
    """The complete behavior assembly for a single game object."""
    composition_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    object_id: str = ""
    slots: Dict[str, BehaviorSlot] = field(default_factory=dict)
    active_behaviors: Set[str] = field(default_factory=set)
    execution_order: List[str] = field(default_factory=list)
    composition_mode: CompositionMode = CompositionMode.PARALLEL
    state: BehaviorLifecycle = BehaviorLifecycle.CREATED


@dataclass
class BehaviorEvent:
    """An event generated by a behavior that can be routed to other behaviors."""
    event_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    source_behavior_id: str = ""
    event_type: str = ""
    event_data: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=_time_module.time)
    propagation_target: str = ""


@dataclass
class BehaviorReport:
    """A diagnostic report for a behavior composition on a game object."""
    report_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    composition_id: str = ""
    behavior_count: int = 0
    active_count: int = 0
    error_count: int = 0
    performance_metrics: Dict[str, Any] = field(default_factory=dict)
    conflicts: List[Dict[str, Any]] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Behavior Template Library
# ---------------------------------------------------------------------------


class BehaviorTemplateLibrary:
    """Manages behavior template definitions and provides search/discovery."""

    def __init__(self) -> None:
        self._templates: Dict[str, BehaviorTemplate] = {}
        self._category_index: Dict[BehaviorCategory, List[str]] = defaultdict(list)
        self._name_index: Dict[str, str] = {}

    def register(self, template: BehaviorTemplate) -> str:
        self._templates[template.template_id] = template
        self._category_index[template.category].append(template.template_id)
        self._name_index[template.name.lower()] = template.template_id
        return template.template_id

    def get(self, template_id: str) -> Optional[BehaviorTemplate]:
        return self._templates.get(template_id)

    def get_by_name(self, name: str) -> Optional[BehaviorTemplate]:
        tid = self._name_index.get(name.lower())
        return self._templates.get(tid) if tid else None

    def list_by_category(self, category: Optional[BehaviorCategory] = None) -> List[BehaviorTemplate]:
        if category is None:
            return list(self._templates.values())
        ids = self._category_index.get(category, [])
        return [self._templates[tid] for tid in ids if tid in self._templates]

    def count(self) -> int:
        return len(self._templates)

    def preload_builtins(self) -> None:
        """Register the standard set of 10 built-in behavior templates."""
        builtins = [
            BehaviorTemplate(name="PlatformerMovement", category=BehaviorCategory.MOVEMENT,
                description="Side-scrolling platformer movement with gravity, jump, and ground detection.",
                parameters={"speed": {"type": "float", "default": 200.0}, "jump_force": {"type": "float", "default": 400.0}, "gravity": {"type": "float", "default": 980.0}},
                default_values={"speed": 200.0, "jump_force": 400.0, "gravity": 980.0}, update_order=UpdateOrder.PRE_UPDATE),
            BehaviorTemplate(name="TopDownMovement", category=BehaviorCategory.MOVEMENT,
                description="Top-down 8-directional movement with acceleration and friction.",
                parameters={"speed": {"type": "float", "default": 150.0}, "acceleration": {"type": "float", "default": 800.0}, "friction": {"type": "float", "default": 600.0}},
                default_values={"speed": 150.0, "acceleration": 800.0, "friction": 600.0},
                conflicts_with=["PlatformerMovement"], update_order=UpdateOrder.PRE_UPDATE),
            BehaviorTemplate(name="PhysicsBody", category=BehaviorCategory.PHYSICS,
                description="Rigid body physics simulation with mass, velocity, and collision response.",
                parameters={"mass": {"type": "float", "default": 1.0}, "linear_damping": {"type": "float", "default": 0.1}, "gravity_scale": {"type": "float", "default": 1.0}},
                default_values={"mass": 1.0, "linear_damping": 0.1, "gravity_scale": 1.0}, update_order=UpdateOrder.UPDATE),
            BehaviorTemplate(name="SpriteRenderer", category=BehaviorCategory.RENDERING,
                description="Renders a 2D sprite with support for animation, flipping, and tinting.",
                parameters={"texture_path": {"type": "string", "default": ""}, "opacity": {"type": "float", "default": 1.0}, "flip_x": {"type": "bool", "default": False}},
                default_values={"texture_path": "", "opacity": 1.0, "flip_x": False}, update_order=UpdateOrder.LATE_UPDATE),
            BehaviorTemplate(name="HealthSystem", category=BehaviorCategory.COMBAT,
                description="Manages health points, damage, healing, and death events.",
                parameters={"max_hp": {"type": "float", "default": 100.0}, "current_hp": {"type": "float", "default": 100.0}, "invincibility_duration": {"type": "float", "default": 0.5}},
                default_values={"max_hp": 100.0, "current_hp": 100.0, "invincibility_duration": 0.5}, update_order=UpdateOrder.UPDATE),
            BehaviorTemplate(name="Damageable", category=BehaviorCategory.COMBAT,
                description="Allows an object to receive damage with configurable damage modifiers.",
                parameters={"damage_multiplier": {"type": "float", "default": 1.0}, "armor": {"type": "float", "default": 0.0}},
                default_values={"damage_multiplier": 1.0, "armor": 0.0}, required_components=["HealthSystem"], update_order=UpdateOrder.UPDATE),
            BehaviorTemplate(name="Collectible", category=BehaviorCategory.INTERACTION,
                description="Makes an object collectible by the player with pickup effects.",
                parameters={"collectible_type": {"type": "string", "default": "generic"}, "value": {"type": "int", "default": 1}},
                default_values={"collectible_type": "generic", "value": 1}, update_order=UpdateOrder.POST_UPDATE),
            BehaviorTemplate(name="Interactive", category=BehaviorCategory.INTERACTION,
                description="Enables player interaction with the object through a configurable prompt.",
                parameters={"interaction_range": {"type": "float", "default": 64.0}, "prompt_text": {"type": "string", "default": "Interact"}, "single_use": {"type": "bool", "default": False}},
                default_values={"interaction_range": 64.0, "prompt_text": "Interact", "single_use": False}, update_order=UpdateOrder.UPDATE),
            BehaviorTemplate(name="PatrolAI", category=BehaviorCategory.AI,
                description="Simple patrol AI that moves between waypoints with configurable wait times.",
                parameters={"waypoints": {"type": "list", "default": []}, "patrol_speed": {"type": "float", "default": 100.0}, "patrol_mode": {"type": "string", "default": "loop"}},
                default_values={"waypoints": [], "patrol_speed": 100.0, "patrol_mode": "loop"},
                required_components=["TopDownMovement"], update_order=UpdateOrder.UPDATE),
            BehaviorTemplate(name="ChaseAI", category=BehaviorCategory.AI,
                description="Chase behavior that pursues a target with configurable detection range and speed.",
                parameters={"chase_speed": {"type": "float", "default": 200.0}, "detection_range": {"type": "float", "default": 300.0}, "target_tag": {"type": "string", "default": "Player"}},
                default_values={"chase_speed": 200.0, "detection_range": 300.0, "target_tag": "Player"},
                required_components=["TopDownMovement"], conflicts_with=["PatrolAI"], update_order=UpdateOrder.UPDATE),
        ]
        for template in builtins:
            self.register(template)


# ---------------------------------------------------------------------------
# Behavior Instance Manager
# ---------------------------------------------------------------------------


class BehaviorInstanceManager:
    """Manages the lifecycle of behavior instances with indexed lookups."""

    def __init__(self) -> None:
        self._instances: Dict[str, BehaviorInstance] = {}
        self._instances_by_object: Dict[str, List[str]] = defaultdict(list)
        self._instances_by_template: Dict[str, List[str]] = defaultdict(list)

    def create(self, template: BehaviorTemplate, object_id: str,
               params: Optional[Dict[str, Any]] = None) -> BehaviorInstance:
        param_values = dict(template.default_values)
        if params:
            param_values.update(params)
        instance = BehaviorInstance(
            template=template, owner_object_id=object_id, parameter_values=param_values,
            state=BehaviorLifecycle.CREATED, created_at=_time_module.time(), last_updated=_time_module.time())
        self._instances[instance.instance_id] = instance
        self._instances_by_object[object_id].append(instance.instance_id)
        self._instances_by_template[template.template_id].append(instance.instance_id)
        return instance

    def get(self, instance_id: str) -> Optional[BehaviorInstance]:
        return self._instances.get(instance_id)

    def get_by_object(self, object_id: str) -> List[BehaviorInstance]:
        ids = self._instances_by_object.get(object_id, [])
        return [self._instances[iid] for iid in ids if iid in self._instances]

    def get_by_template(self, template_id: str) -> List[BehaviorInstance]:
        ids = self._instances_by_template.get(template_id, [])
        return [self._instances[iid] for iid in ids if iid in self._instances]

    def set_state(self, instance_id: str, state: BehaviorLifecycle) -> bool:
        instance = self._instances.get(instance_id)
        if instance is None:
            return False
        instance.state = state
        instance.last_updated = _time_module.time()
        return True

    def set_enabled(self, instance_id: str, enabled: bool) -> bool:
        instance = self._instances.get(instance_id)
        if instance is None:
            return False
        instance.enabled = enabled
        instance.last_updated = _time_module.time()
        return True

    def set_priority(self, instance_id: str, priority: BehaviorPriority) -> bool:
        instance = self._instances.get(instance_id)
        if instance is None:
            return False
        instance.priority = priority
        instance.last_updated = _time_module.time()
        return True

    def update_params(self, instance_id: str, params: Dict[str, Any]) -> bool:
        instance = self._instances.get(instance_id)
        if instance is None:
            return False
        instance.parameter_values.update(params)
        instance.last_updated = _time_module.time()
        return True

    def destroy(self, instance_id: str) -> bool:
        instance = self._instances.pop(instance_id, None)
        if instance is None:
            return False
        obj_list = self._instances_by_object.get(instance.owner_object_id, [])
        if instance_id in obj_list:
            obj_list.remove(instance_id)
        if instance.template:
            tmpl_list = self._instances_by_template.get(instance.template.template_id, [])
            if instance_id in tmpl_list:
                tmpl_list.remove(instance_id)
        return True

    def count(self) -> int:
        return len(self._instances)

    def count_active(self) -> int:
        return sum(1 for inst in self._instances.values() if inst.state == BehaviorLifecycle.ACTIVE)


# ---------------------------------------------------------------------------
# Behavior Slot Manager
# ---------------------------------------------------------------------------


class BehaviorSlotManager:
    """Manages named behavior slots on game objects with category constraints."""

    def __init__(self) -> None:
        self._object_slots: Dict[str, Dict[str, BehaviorSlot]] = defaultdict(dict)

    def create_slot(self, object_id: str, slot_name: str,
                    accepted_categories: Optional[List[BehaviorCategory]] = None,
                    max_behaviors: int = 1, is_required: bool = False) -> BehaviorSlot:
        slot = BehaviorSlot(slot_name=slot_name, accepted_categories=accepted_categories or [],
                            max_behaviors=max_behaviors, is_required=is_required)
        self._object_slots[object_id][slot_name] = slot
        return slot

    def ensure_default_slot(self, object_id: str) -> BehaviorSlot:
        if object_id not in self._object_slots:
            self._object_slots[object_id] = {}
        if "default" not in self._object_slots[object_id]:
            self._object_slots[object_id]["default"] = BehaviorSlot(
                slot_name="default", accepted_categories=list(BehaviorCategory),
                max_behaviors=999, is_required=False)
        return self._object_slots[object_id]["default"]

    def get_slot(self, object_id: str, slot_name: str) -> Optional[BehaviorSlot]:
        return self._object_slots.get(object_id, {}).get(slot_name)

    def get_slots(self, object_id: str) -> Dict[str, BehaviorSlot]:
        return dict(self._object_slots.get(object_id, {}))

    def remove_slot(self, object_id: str, slot_name: str) -> bool:
        slots = self._object_slots.get(object_id, {})
        if slot_name not in slots:
            return False
        del slots[slot_name]
        if not slots:
            del self._object_slots[object_id]
        return True

    def remove_object(self, object_id: str) -> None:
        self._object_slots.pop(object_id, None)


# ---------------------------------------------------------------------------
# Behavior Conflict Resolver
# ---------------------------------------------------------------------------


class BehaviorConflictResolver:
    """Resolves conflicts between incompatible behaviors on the same object."""

    def __init__(self) -> None:
        self._conflict_log: List[Dict[str, Any]] = []

    def check_conflict(self, template: BehaviorTemplate,
                       existing_instances: List[BehaviorInstance]) -> List[BehaviorInstance]:
        conflicts = []
        for inst in existing_instances:
            if inst.template is None:
                continue
            if inst.template.template_id in template.conflicts_with:
                conflicts.append(inst)
            if template.template_id in inst.template.conflicts_with:
                conflicts.append(inst)
        return conflicts

    def resolve(self, new_template: BehaviorTemplate,
                conflicting_instances: List[BehaviorInstance],
                strategy: str = "replace") -> Tuple[bool, List[str]]:
        removed: List[str] = []
        if strategy == "replace":
            for inst in conflicting_instances:
                removed.append(inst.instance_id)
            self._log_conflict("replace", new_template.template_id,
                              [i.instance_id for i in conflicting_instances])
            return True, removed
        elif strategy == "reject":
            self._log_conflict("reject", new_template.template_id,
                              [i.instance_id for i in conflicting_instances])
            return False, []
        elif strategy == "warn":
            self._log_conflict("warn", new_template.template_id,
                              [i.instance_id for i in conflicting_instances])
            return True, []
        return True, []

    def _log_conflict(self, resolution: str, new_template_id: str,
                      conflicting_ids: List[str]) -> None:
        self._conflict_log.append({
            "timestamp": _time_module.time(), "resolution": resolution,
            "new_template_id": new_template_id, "conflicting_instance_ids": conflicting_ids})

    def get_conflict_log(self, limit: int = 50) -> List[Dict[str, Any]]:
        return self._conflict_log[-limit:]

    def clear_log(self) -> None:
        self._conflict_log.clear()


# ---------------------------------------------------------------------------
# Behavior Event Bus
# ---------------------------------------------------------------------------


class BehaviorEventBus:
    """Routes events between behaviors for decoupled inter-behavior communication."""

    def __init__(self) -> None:
        self._event_queue: deque[BehaviorEvent] = deque()
        self._event_history: deque[BehaviorEvent] = deque(maxlen=500)
        self._listeners: Dict[str, List[str]] = defaultdict(list)

    def register_listener(self, behavior_id: str, event_type: str) -> None:
        if behavior_id not in self._listeners[event_type]:
            self._listeners[event_type].append(behavior_id)

    def unregister_listener(self, behavior_id: str, event_type: str) -> None:
        listeners = self._listeners.get(event_type, [])
        if behavior_id in listeners:
            listeners.remove(behavior_id)

    def unregister_all(self, behavior_id: str) -> None:
        for event_type in list(self._listeners.keys()):
            self.unregister_listener(behavior_id, event_type)

    def emit(self, source_behavior_id: str, event_type: str,
             data: Optional[Dict[str, Any]] = None,
             propagation_target: str = "") -> List[BehaviorEvent]:
        event = BehaviorEvent(source_behavior_id=source_behavior_id, event_type=event_type,
                              event_data=data or {}, propagation_target=propagation_target)
        self._event_queue.append(event)
        return [event]

    def process_events(self) -> List[BehaviorEvent]:
        dispatched: List[BehaviorEvent] = []
        while self._event_queue:
            event = self._event_queue.popleft()
            self._event_history.append(event)
            dispatched.append(event)
        return dispatched

    def get_recent_events(self, limit: int = 50) -> List[BehaviorEvent]:
        return list(self._event_history)[-limit:]

    def get_event_count(self) -> int:
        return len(self._event_history)

    def clear(self) -> None:
        self._event_queue.clear()
        self._event_history.clear()


# ---------------------------------------------------------------------------
# Behavior Composer Engine (Singleton)
# ---------------------------------------------------------------------------


class BehaviorComposerEngine:
    """Main singleton orchestrating behavior composition on game objects.

    Coordinates template library, instance manager, slot manager, conflict
    resolver, and event bus to provide a unified interface for attaching,
    detaching, and executing behaviors on game objects.
    """

    _instance: Optional["BehaviorComposerEngine"] = None
    _lock = threading.RLock()

    def __new__(cls) -> "BehaviorComposerEngine":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self) -> None:
        if self._initialized:
            return
        self._initialized = True
        self._template_library = BehaviorTemplateLibrary()
        self._instance_manager = BehaviorInstanceManager()
        self._slot_manager = BehaviorSlotManager()
        self._conflict_resolver = BehaviorConflictResolver()
        self._event_bus = BehaviorEventBus()
        self._compositions: Dict[str, BehaviorComposition] = {}
        self._registration_count: int = 0
        self._creation_count: int = 0
        self._attach_count: int = 0
        self._update_count: int = 0
        self._event_count: int = 0
        self._template_library.preload_builtins()

    @classmethod
    def get_instance(cls) -> "BehaviorComposerEngine":
        """Return the singleton BehaviorComposerEngine instance."""
        return cls()

    # ------------------------------------------------------------------
    # Template Management
    # ------------------------------------------------------------------

    def register_template(self, template: BehaviorTemplate) -> str:
        with self._lock:
            tid = self._template_library.register(template)
            self._registration_count += 1
            return tid

    def list_templates(self, category: Optional[BehaviorCategory] = None) -> List[BehaviorTemplate]:
        return self._template_library.list_by_category(category)

    def get_template(self, template_id: str) -> Optional[BehaviorTemplate]:
        return self._template_library.get(template_id)

    def get_template_by_name(self, name: str) -> Optional[BehaviorTemplate]:
        return self._template_library.get_by_name(name)

    # ------------------------------------------------------------------
    # Instance Management
    # ------------------------------------------------------------------

    def create_instance(self, template_id: str, object_id: str,
                        params: Optional[Dict[str, Any]] = None) -> Optional[BehaviorInstance]:
        with self._lock:
            template = self._template_library.get(template_id)
            if template is None:
                return None
            instance = self._instance_manager.create(template, object_id, params)
            self._creation_count += 1
            return instance

    def get_instance(self, instance_id: str) -> Optional[BehaviorInstance]:
        return self._instance_manager.get(instance_id)

    def get_object_instances(self, object_id: str) -> List[BehaviorInstance]:
        return self._instance_manager.get_by_object(object_id)

    def set_instance_state(self, instance_id: str, state: BehaviorLifecycle) -> bool:
        return self._instance_manager.set_state(instance_id, state)

    def set_instance_enabled(self, instance_id: str, enabled: bool) -> bool:
        return self._instance_manager.set_enabled(instance_id, enabled)

    def set_instance_priority(self, instance_id: str, priority: BehaviorPriority) -> bool:
        return self._instance_manager.set_priority(instance_id, priority)

    def update_instance_params(self, instance_id: str, params: Dict[str, Any]) -> bool:
        return self._instance_manager.update_params(instance_id, params)

    # ------------------------------------------------------------------
    # Behavior Attachment / Detachment
    # ------------------------------------------------------------------

    def attach_behavior(self, object_id: str, instance_id: str,
                        slot_name: str = "default") -> bool:
        with self._lock:
            instance = self._instance_manager.get(instance_id)
            if instance is None or instance.owner_object_id != object_id:
                return False

            self._slot_manager.ensure_default_slot(object_id)
            slot = self._slot_manager.get_slot(object_id, slot_name)
            if slot is None:
                slot = self._slot_manager.create_slot(object_id, slot_name)

            template = instance.template
            if template is None:
                return False

            if slot.accepted_categories and template.category not in slot.accepted_categories:
                return False

            existing = self._instance_manager.get_by_object(object_id)
            active_existing = [i for i in existing if i.instance_id != instance_id]
            conflicts = self._conflict_resolver.check_conflict(template, active_existing)
            if conflicts:
                allowed, removed = self._conflict_resolver.resolve(template, conflicts, "replace")
                if not allowed:
                    return False
                for removed_id in removed:
                    self.detach_behavior(object_id, removed_id)

            slot.current_behavior = instance_id
            instance.state = BehaviorLifecycle.ACTIVE
            instance.last_updated = _time_module.time()

            composition = self._ensure_composition(object_id)
            composition.active_behaviors.add(instance_id)
            self._rebuild_execution_order(composition)

            self._event_bus.register_listener(instance_id, "on_activate")
            self._event_bus.register_listener(instance_id, "on_deactivate")
            self._attach_count += 1
            return True

    def detach_behavior(self, object_id: str, instance_id: str) -> bool:
        with self._lock:
            instance = self._instance_manager.get(instance_id)
            if instance is None:
                return False

            for slot in self._slot_manager.get_slots(object_id).values():
                if slot.current_behavior == instance_id:
                    slot.current_behavior = ""

            composition = self._compositions.get(object_id)
            if composition:
                composition.active_behaviors.discard(instance_id)
                if instance_id in composition.execution_order:
                    composition.execution_order.remove(instance_id)

            self._event_bus.unregister_all(instance_id)
            instance.state = BehaviorLifecycle.DEACTIVATED
            instance.last_updated = _time_module.time()
            return True

    # ------------------------------------------------------------------
    # Composition Management
    # ------------------------------------------------------------------

    def create_composition(self, object_id: str,
                           mode: CompositionMode = CompositionMode.PARALLEL) -> BehaviorComposition:
        with self._lock:
            composition = BehaviorComposition(
                object_id=object_id, composition_mode=mode, state=BehaviorLifecycle.INITIALIZED)
            self._compositions[object_id] = composition
            self._slot_manager.ensure_default_slot(object_id)
            return composition

    def get_composition(self, object_id: str) -> Optional[BehaviorComposition]:
        return self._compositions.get(object_id)

    def _ensure_composition(self, object_id: str) -> BehaviorComposition:
        if object_id not in self._compositions:
            return self.create_composition(object_id)
        return self._compositions[object_id]

    def _rebuild_execution_order(self, composition: BehaviorComposition) -> None:
        order_map = {UpdateOrder.PRE_UPDATE: 0, UpdateOrder.UPDATE: 1,
                     UpdateOrder.POST_UPDATE: 2, UpdateOrder.LATE_UPDATE: 3}
        priority_map = {BehaviorPriority.CRITICAL: 0, BehaviorPriority.HIGH: 1,
                        BehaviorPriority.NORMAL: 2, BehaviorPriority.LOW: 3,
                        BehaviorPriority.BACKGROUND: 4}
        ordered: List[Tuple[int, int, str]] = []
        for bid in composition.active_behaviors:
            inst = self._instance_manager.get(bid)
            if inst is None or inst.template is None:
                continue
            ordered.append((order_map.get(inst.template.update_order, 1),
                           priority_map.get(inst.priority, 2), bid))
        ordered.sort(key=lambda x: (x[0], x[1]))
        composition.execution_order = [oid for _, _, oid in ordered]

    def update_composition(self, composition_id: str, delta_time: float) -> None:
        composition = self._compositions.get(composition_id)
        if composition is None:
            return
        behaviors_to_update = [bid for bid in composition.execution_order
                               if bid in composition.active_behaviors]
        mode = composition.composition_mode
        for bid in behaviors_to_update:
            inst = self._instance_manager.get(bid)
            if inst is None or not inst.enabled:
                continue
            if inst.state != BehaviorLifecycle.ACTIVE:
                continue
            if mode == CompositionMode.PRIORITY_BASED and inst.priority not in (
                    BehaviorPriority.CRITICAL, BehaviorPriority.HIGH):
                continue
            inst.last_updated = _time_module.time()
        self._update_count += 1

    # ------------------------------------------------------------------
    # Event System
    # ------------------------------------------------------------------

    def send_event(self, behavior_id: str, event_type: str,
                   data: Optional[Dict[str, Any]] = None) -> List[BehaviorEvent]:
        events = self._event_bus.emit(behavior_id, event_type, data)
        self._event_bus.process_events()
        self._event_count += len(events)
        return events

    def register_event_listener(self, behavior_id: str, event_type: str) -> None:
        self._event_bus.register_listener(behavior_id, event_type)

    def unregister_event_listener(self, behavior_id: str, event_type: str) -> None:
        self._event_bus.unregister_listener(behavior_id, event_type)

    # ------------------------------------------------------------------
    # Reporting & Diagnostics
    # ------------------------------------------------------------------

    def get_behavior_report(self, object_id: str) -> BehaviorReport:
        composition = self._compositions.get(object_id)
        comp_id = composition.composition_id if composition else ""
        all_instances = self._instance_manager.get_by_object(object_id)
        active_count = sum(1 for i in all_instances if i.state == BehaviorLifecycle.ACTIVE)
        error_count = sum(1 for i in all_instances if i.state == BehaviorLifecycle.DESTROYED)

        conflicts: List[Dict[str, Any]] = []
        for i, inst_a in enumerate(all_instances):
            for inst_b in all_instances[i + 1:]:
                if inst_a.template and inst_b.template:
                    if inst_a.template.template_id in inst_b.template.conflicts_with:
                        conflicts.append({
                            "instance_a": inst_a.instance_id, "instance_b": inst_b.instance_id,
                            "template_a": inst_a.template.name, "template_b": inst_b.template.name})

        return BehaviorReport(
            composition_id=comp_id, behavior_count=len(all_instances),
            active_count=active_count, error_count=error_count,
            performance_metrics={"memory_estimate_bytes": len(all_instances) * 1024,
                                "event_queue_size": self._event_bus.get_event_count()},
            conflicts=conflicts)

    def get_stats(self) -> Dict[str, Any]:
        category_distribution: Dict[str, int] = {}
        for cat in BehaviorCategory:
            category_distribution[cat.value] = len(self._template_library.list_by_category(cat))

        lifecycle_distribution: Dict[str, int] = {}
        for state in BehaviorLifecycle:
            lifecycle_distribution[state.value] = sum(
                1 for inst in self._instance_manager._instances.values() if inst.state == state)

        return {
            "total_templates": self._template_library.count(),
            "total_instances": self._instance_manager.count(),
            "active_instances": self._instance_manager.count_active(),
            "total_compositions": len(self._compositions),
            "registration_count": self._registration_count,
            "creation_count": self._creation_count,
            "attach_count": self._attach_count,
            "update_count": self._update_count,
            "event_count": self._event_count,
            "category_distribution": category_distribution,
            "lifecycle_distribution": lifecycle_distribution,
            "conflict_log_entries": len(self._conflict_resolver.get_conflict_log()),
        }

    # ------------------------------------------------------------------
    # Cleanup
    # ------------------------------------------------------------------

    def reset(self) -> None:
        with self._lock:
            self._template_library = BehaviorTemplateLibrary()
            self._instance_manager = BehaviorInstanceManager()
            self._slot_manager = BehaviorSlotManager()
            self._conflict_resolver = BehaviorConflictResolver()
            self._event_bus = BehaviorEventBus()
            self._compositions.clear()
            self._registration_count = 0
            self._creation_count = 0
            self._attach_count = 0
            self._update_count = 0
            self._event_count = 0
            self._template_library.preload_builtins()


# ---------------------------------------------------------------------------
# Module Accessor
# ---------------------------------------------------------------------------


def get_behavior_composer() -> BehaviorComposerEngine:
    """Return the singleton BehaviorComposerEngine instance."""
    return BehaviorComposerEngine.get_instance()