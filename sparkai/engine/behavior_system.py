"""
SparkLabs Engine - Behavior System

Modular behavior component system for extending game entity
capabilities. Behaviors are attachable/detachable modules that
provide specialized logic — physics, pathfinding, AI decision
making, rendering effects — without modifying the core entity.

Architecture:
  BehaviorSystem
    |-- Behavior (base: name, lifecycle hooks, activation)
    |-- BehaviorHost (entity adapter that manages behaviors)
    |-- BehaviorScheduler (ordered pre/post-step execution)

Lifecycle Hooks:
  - on_attach(entity): called when added to an entity
  - on_detach(entity): called when removed
  - on_activate(entity): called on activation
  - on_deactivate(entity): called on deactivation
  - step_pre(dt, entity): before entity update
  - step_post(dt, entity): after entity update

Usage:
    bs = BehaviorSystem()
    jump_behavior = JumpBehavior(jump_force=500.0)
    bs.attach("player", jump_behavior)
    bs.step_pre(0.016)
    # entity processing happens here
    bs.step_post(0.016)
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Set


class Behavior(ABC):
    """
    Abstract behavior that can be attached to game entities.

    Behaviors are modular, reusable logic modules that extend
    entity functionality. Each behavior has a name, activation
    state, and optional lifecycle hooks.

    Subclass and override:
        on_attach, on_detach, on_activate, on_deactivate,
        step_pre, step_post
    """

    def __init__(self, name: str = ""):
        self.name = name or self.__class__.__name__
        self._active: bool = True
        self._host_entity_id: Optional[str] = None
        self._properties: Dict[str, Any] = {}

    @property
    def active(self) -> bool:
        return self._active

    @property
    def host_entity_id(self) -> Optional[str]:
        return self._host_entity_id

    def set_property(self, key: str, value: Any) -> None:
        self._properties[key] = value

    def get_property(self, key: str, default: Any = None) -> Any:
        return self._properties.get(key, default)

    def on_attach(self, entity: Any) -> None:
        pass

    def on_detach(self, entity: Any) -> None:
        pass

    def activate(self) -> None:
        self._active = True
        if self._host_entity_id:
            self.on_activate(self._host_entity_id)

    def deactivate(self) -> None:
        self._active = False
        if self._host_entity_id:
            self.on_deactivate(self._host_entity_id)

    def on_activate(self, entity: Any) -> None:
        pass

    def on_deactivate(self, entity: Any) -> None:
        pass

    def step_pre(self, dt: float, entity: Any) -> None:
        pass

    def step_post(self, dt: float, entity: Any) -> None:
        pass


@dataclass
class BehaviorEntry:
    behavior: Behavior = field(default_factory=Behavior)
    priority: int = 0
    attached_at: float = 0.0


class BehaviorSystem:
    """
    Behavior composition system for game entities.

    Manages the attachment and lifecycle of behaviors on entities.
    Executes behaviors in order during pre-step and post-step phases,
    supporting activation/deactivation and priority ordering.

    Usage:
        bs = BehaviorSystem()
        
        # Define a custom behavior
        class Rotator(Behavior):
            def step_pre(self, dt, entity):
                entity.rotation += 90 * dt
        
        # Attach to entity
        bs.attach("target_dummy", Rotator("spin"), priority=5)
        
        # Execute in game loop
        bs.step_pre(0.016)  # all behaviors pre-update
        # ... entity processing ...
        bs.step_post(0.016)  # all behaviors post-update
    """

    def __init__(self):
        self._entity_behaviors: Dict[str, List[BehaviorEntry]] = {}
        self._behavior_index: Dict[str, Set[str]] = {}
        self._total_attached: int = 0
        self._total_detached: int = 0

    def attach(
        self, entity_id: str, behavior: Behavior, priority: int = 0,
    ) -> None:
        if entity_id not in self._entity_behaviors:
            self._entity_behaviors[entity_id] = []

        behavior._host_entity_id = entity_id

        entry = BehaviorEntry(behavior=behavior, priority=priority)
        self._entity_behaviors[entity_id].append(entry)
        self._entity_behaviors[entity_id].sort(key=lambda e: -e.priority)

        behavior_name = behavior.name
        self._behavior_index.setdefault(behavior_name, set()).add(entity_id)

        self._total_attached += 1
        behavior.on_attach(entity_id)

    def detach(self, entity_id: str, behavior_name: str) -> Optional[Behavior]:
        entries = self._entity_behaviors.get(entity_id, [])
        for i, entry in enumerate(entries):
            if entry.behavior.name == behavior_name:
                behavior = entry.behavior
                behavior.on_detach(entity_id)
                behavior._host_entity_id = None
                entries.pop(i)
                self._behavior_index.get(behavior_name, set()).discard(entity_id)
                if not entries:
                    del self._entity_behaviors[entity_id]
                self._total_detached += 1
                return behavior
        return None

    def detach_all(self, entity_id: str) -> int:
        entries = self._entity_behaviors.pop(entity_id, [])
        for entry in entries:
            behavior = entry.behavior
            behavior.on_detach(entity_id)
            behavior._host_entity_id = None
            self._behavior_index.get(behavior.name, set()).discard(entity_id)
        self._total_detached += len(entries)
        return len(entries)

    def get_behaviors(self, entity_id: str) -> List[Behavior]:
        entries = self._entity_behaviors.get(entity_id, [])
        return [e.behavior for e in entries]

    def get_behavior(self, entity_id: str, name: str) -> Optional[Behavior]:
        for entry in self._entity_behaviors.get(entity_id, []):
            if entry.behavior.name == name:
                return entry.behavior
        return None

    def has_behavior(self, entity_id: str, name: str) -> bool:
        return self.get_behavior(entity_id, name) is not None

    def find_entities_with(self, behavior_name: str) -> Set[str]:
        return self._behavior_index.get(behavior_name, set()).copy()

    def activate(self, entity_id: str, behavior_name: str) -> bool:
        behavior = self.get_behavior(entity_id, behavior_name)
        if behavior:
            behavior.activate()
            return True
        return False

    def deactivate(self, entity_id: str, behavior_name: str) -> bool:
        behavior = self.get_behavior(entity_id, behavior_name)
        if behavior:
            behavior.deactivate()
            return True
        return False

    def step_pre(self, dt: float, entity_getter: Optional[Callable[[str], Any]] = None) -> None:
        for entity_id, entries in self._entity_behaviors.items():
            entity = entity_getter(entity_id) if entity_getter else entity_id
            for entry in entries:
                if entry.behavior.active:
                    try:
                        entry.behavior.step_pre(dt, entity)
                    except Exception:
                        pass

    def step_post(self, dt: float, entity_getter: Optional[Callable[[str], Any]] = None) -> None:
        for entity_id, entries in self._entity_behaviors.items():
            entity = entity_getter(entity_id) if entity_getter else entity_id
            for entry in entries:
                if entry.behavior.active:
                    try:
                        entry.behavior.step_post(dt, entity)
                    except Exception:
                        pass

    def get_stats(self) -> dict:
        total_behaviors = sum(len(es) for es in self._entity_behaviors.values())
        return {
            "entities": len(self._entity_behaviors),
            "behaviors": total_behaviors,
            "avg_per_entity": round(
                total_behaviors / max(len(self._entity_behaviors), 1), 1,
            ),
            "attached": self._total_attached,
            "detached": self._total_detached,
            "behavior_types": list(self._behavior_index.keys()),
        }

    def clear(self) -> None:
        for entity_id, entries in list(self._entity_behaviors.items()):
            for entry in entries:
                entry.behavior.on_detach(entity_id)
                entry.behavior._host_entity_id = None
        self._entity_behaviors.clear()
        self._behavior_index.clear()
        self._total_attached = 0
        self._total_detached = 0


_global_behavior_system: Optional[BehaviorSystem] = None


def get_behavior_system() -> BehaviorSystem:
    global _global_behavior_system
    if _global_behavior_system is None:
        _global_behavior_system = BehaviorSystem()
    return _global_behavior_system
