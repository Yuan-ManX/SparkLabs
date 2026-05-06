"""
SparkLabs Engine - Game Object Lifecycle Model

Full lifecycle manager for game entities with a component-based
architecture. Every GameObject goes through Awake → Start → Update
→ LateUpdate → Destroy phases, enabling AI agents to create and
manage game entities predictably.

Architecture:
  GameObject
    |-- Transform (position, rotation, scale in scene)
    |-- Component (attachable behaviors with lifecycle hooks)
    |-- Scene (parent scene reference for hierarchy)
    |-- Tags (string tags for group lookup and filtering)
    |-- Children (parent-child transform hierarchy)
    |-- Lifecycle (state machine: INACTIVE → AWAKE → ACTIVE → DESTROYED)

GameObject Lifecycle:
  INACTIVE   → entity registered but not yet initialized
  AWAKE      → Awake() called when scene loads / first frame
  ACTIVE     → Update() every frame, LateUpdate() after physics
  PAUSED     → entity still exists but does not receive Update
  DESTROYED  → OnDestroy() called, removed from scene, marked for GC

Component Lifecycle (parallel):
  Awake()       → called once on object spawn (INACTIVE → AWAKE)
  Start()       → called next frame after Awake (AWAKE → ACTIVE)
  Update(dt)    → called every frame while ACTIVE
  LateUpdate(dt)→ called every frame after Update, for camera/follow
  OnDisable()   → when component disabled
  OnDestroy()   → cleanup before removal

Usage:
    go = GameObject("Player", tags=["player", "character"])
    go.transform.position = (100, 200)
    go.add_component(SpriteRenderer)
    go.add_component(PlatformerController)
    go.start()
    # ... per frame:
    go.update(dt)
    go.late_update(dt)
    go.destroy()
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Type


class ObjectLifecycle(Enum):
    INACTIVE = "inactive"
    AWAKE = "awake"
    ACTIVE = "active"
    PAUSED = "paused"
    DESTROYED = "destroyed"


@dataclass
class Transform:
    x: float = 0.0
    y: float = 0.0
    z: float = 0.0
    rotation: float = 0.0
    scale_x: float = 1.0
    scale_y: float = 1.0

    @property
    def position(self) -> tuple:
        return (self.x, self.y)

    @position.setter
    def set_position(self, value: tuple) -> None:
        self.x, self.y = value

    def translate(self, dx: float, dy: float) -> None:
        self.x += dx
        self.y += dy

    def to_dict(self) -> Dict[str, float]:
        return {"x": self.x, "y": self.y, "z": self.z,
                "rotation": self.rotation, "scale_x": self.scale_x, "scale_y": self.scale_y}


@dataclass
class Component:
    name: str = ""
    enabled: bool = True
    game_object: Any = None
    awake_done: bool = False
    start_done: bool = False

    def awake(self) -> None:
        pass

    def start(self) -> None:
        pass

    def update(self, dt: float) -> None:
        pass

    def late_update(self, dt: float) -> None:
        pass

    def on_enable(self) -> None:
        pass

    def on_disable(self) -> None:
        pass

    def on_destroy(self) -> None:
        pass


@dataclass
class GameObject:
    object_id: str = field(default_factory=lambda: f"obj_{uuid.uuid4().hex[:12]}")
    name: str = "GameObject"
    transform: Transform = field(default_factory=Transform)
    tags: List[str] = field(default_factory=list)
    layer: int = 0
    active: bool = True
    _lifecycle: ObjectLifecycle = ObjectLifecycle.INACTIVE
    _components: List[Component] = field(default_factory=list)
    _component_index: Dict[Type, Component] = field(default_factory=dict)
    _children: List["GameObject"] = field(default_factory=list)
    _parent: Optional["GameObject"] = None
    _scene_ref: Optional[Any] = None
    _destroyed_at: float = 0.0
    _created_at: float = field(default_factory=time.time)

    @property
    def lifecycle(self) -> ObjectLifecycle:
        return self._lifecycle

    @property
    def components(self) -> List[Component]:
        return self._components

    @property
    def children(self) -> List["GameObject"]:
        return self._children

    @property
    def parent(self) -> Optional["GameObject"]:
        return self._parent

    def set_position(self, x: float, y: float) -> None:
        self.transform.x = x
        self.transform.y = y

    def set_scale(self, sx: float, sy: float) -> None:
        self.transform.scale_x = sx
        self.transform.scale_y = sy

    def set_parent(self, parent: "GameObject") -> None:
        if self._parent:
            self._parent._children.remove(self)
        self._parent = parent
        parent._children.append(self)

    def add_child(self, child: "GameObject") -> None:
        self._children.append(child)
        child._parent = self

    def remove_child(self, child: "GameObject") -> None:
        if child in self._children:
            self._children.remove(child)
            child._parent = None

    def add_component(self, comp_type: Type[Component],
                      **kwargs) -> Component:
        if comp_type in self._component_index:
            return self._component_index[comp_type]

        comp = comp_type(**kwargs)
        comp.game_object = self
        if not comp.name:
            comp.name = comp_type.__name__

        self._components.append(comp)
        self._component_index[comp_type] = comp

        if self._lifecycle == ObjectLifecycle.ACTIVE:
            comp.awake()
            comp.awake_done = True
            comp.start()
            comp.start_done = True

        return comp

    def get_component(self, comp_type: Type[Component]) -> Optional[Component]:
        return self._component_index.get(comp_type)

    def remove_component(self, comp_type: Type[Component]) -> None:
        comp = self._component_index.pop(comp_type, None)
        if comp:
            if comp in self._components:
                self._components.remove(comp)
            comp.on_destroy()

    def has_tag(self, tag: str) -> bool:
        return tag in self.tags

    def add_tag(self, tag: str) -> None:
        if tag not in self.tags:
            self.tags.append(tag)

    def remove_tag(self, tag: str) -> None:
        if tag in self.tags:
            self.tags.remove(tag)

    def awake(self) -> None:
        if self._lifecycle != ObjectLifecycle.INACTIVE:
            return
        self._lifecycle = ObjectLifecycle.AWAKE
        for comp in self._components:
            if comp.enabled and self.active:
                comp.awake()
                comp.awake_done = True

    def start(self) -> None:
        if self._lifecycle != ObjectLifecycle.AWAKE:
            return
        self._lifecycle = ObjectLifecycle.ACTIVE
        for comp in self._components:
            if comp.enabled and self.active and not comp.start_done:
                comp.start()
                comp.start_done = True

    def update(self, dt: float) -> None:
        if self._lifecycle != ObjectLifecycle.ACTIVE:
            return
        if not self.active:
            return
        for comp in self._components:
            if comp.enabled:
                comp.update(dt)

    def late_update(self, dt: float) -> None:
        if self._lifecycle != ObjectLifecycle.ACTIVE:
            return
        if not self.active:
            return
        for comp in self._components:
            if comp.enabled:
                comp.late_update(dt)

    def pause(self) -> None:
        if self._lifecycle == ObjectLifecycle.ACTIVE:
            self._lifecycle = ObjectLifecycle.PAUSED

    def resume(self) -> None:
        if self._lifecycle == ObjectLifecycle.PAUSED:
            self._lifecycle = ObjectLifecycle.ACTIVE

    def set_active(self, active: bool) -> None:
        if active == self.active:
            return
        self.active = active
        if active:
            for comp in self._components:
                comp.on_enable()
        else:
            for comp in self._components:
                comp.on_disable()

    def destroy(self) -> None:
        if self._lifecycle == ObjectLifecycle.DESTROYED:
            return
        for child in list(self._children):
            child.destroy()
        for comp in self._components:
            comp.on_destroy()
        self._lifecycle = ObjectLifecycle.DESTROYED
        self._destroyed_at = time.time()
        if self._parent:
            self._parent.remove_child(self)
        self._components.clear()
        self._component_index.clear()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "object_id": self.object_id,
            "name": self.name,
            "lifecycle": self._lifecycle.value,
            "active": self.active,
            "transform": self.transform.to_dict(),
            "tags": self.tags,
            "layer": self.layer,
            "component_count": len(self._components),
            "child_count": len(self._children),
            "has_parent": self._parent is not None,
            "components": [c.name for c in self._components],
        }

    def get_active_components(self) -> Dict[str, bool]:
        return {
            comp.name: comp.enabled
            for comp in self._components
        }


class GameObjectRegistry:
    """Global registry for GameObject lookup by ID, tag, or type."""

    _instance: Optional["GameObjectRegistry"] = None

    def __init__(self):
        self._objects: Dict[str, GameObject] = {}
        self._by_tag: Dict[str, Set[str]] = {}
        self._total_created: int = 0
        self._total_destroyed: int = 0
        self._MAX_OBJECTS = 50000

    @classmethod
    def get_instance(cls) -> "GameObjectRegistry":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def register(self, go: GameObject) -> None:
        if len(self._objects) >= self._MAX_OBJECTS:
            return
        self._objects[go.object_id] = go
        self._total_created += 1
        for tag in go.tags:
            if tag not in self._by_tag:
                self._by_tag[tag] = set()
            self._by_tag[tag].add(go.object_id)

    def unregister(self, go: GameObject) -> None:
        self._objects.pop(go.object_id, None)
        self._total_destroyed += 1
        for tag in go.tags:
            bucket = self._by_tag.get(tag)
            if bucket:
                bucket.discard(go.object_id)

    def find(self, object_id: str) -> Optional[GameObject]:
        return self._objects.get(object_id)

    def find_by_name(self, name: str) -> List[GameObject]:
        return [g for g in self._objects.values() if g.name == name]

    def find_by_tag(self, tag: str) -> List[GameObject]:
        ids = self._by_tag.get(tag, set())
        return [self._objects[oid] for oid in ids if oid in self._objects]

    def find_active(self) -> List[GameObject]:
        return [g for g in self._objects.values()
                if g._lifecycle == ObjectLifecycle.ACTIVE]

    def destroy_all(self) -> int:
        count = len(self._objects)
        for go in list(self._objects.values()):
            go.destroy()
            self.unregister(go)
        return count

    def update_all(self, dt: float) -> None:
        for go in list(self._objects.values()):
            if go._lifecycle == ObjectLifecycle.ACTIVE:
                go.update(dt)
                go.late_update(dt)

    def get_stats(self) -> Dict[str, Any]:
        by_lifecycle = {lc.value: 0 for lc in ObjectLifecycle}
        for go in self._objects.values():
            by_lifecycle[go._lifecycle.value] += 1

        return {
            "total_objects": len(self._objects),
            "total_created": self._total_created,
            "total_destroyed": self._total_destroyed,
            "max_objects": self._MAX_OBJECTS,
            "tags_indexed": len(self._by_tag),
            "by_lifecycle": by_lifecycle,
            "active_objects": sum(1 for g in self._objects.values()
                                  if g._lifecycle == ObjectLifecycle.ACTIVE),
        }


def get_game_object_registry() -> GameObjectRegistry:
    return GameObjectRegistry.get_instance()


def create_game_object(name: str = "GameObject",
                       position: tuple = (0, 0),
                       tags: Optional[List[str]] = None,
                       layer: int = 0) -> GameObject:
    go = GameObject(name=name, tags=tags or [], layer=layer)
    go.set_position(position[0], position[1])
    registry = GameObjectRegistry.get_instance()
    registry.register(go)
    go.awake()
    go.start()
    return go


def destroy_game_object(go: GameObject) -> None:
    registry = GameObjectRegistry.get_instance()
    registry.unregister(go)
    go.destroy()
