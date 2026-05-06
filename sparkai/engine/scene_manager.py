"""
SparkLabs Engine - Scene Lifecycle Manager

Central scene manager that handles the complete lifecycle of game
scenes — asynchronous loading/unloading, transitions, pooling, and
overlay stacks. Designed for AI-driven scene management where the
agent needs to construct and swap scenes dynamically.

Architecture:
  SceneManager
    |-- ScenePool (pre-loaded reusable scene instances)
    |-- SceneStack (active scene stack with overlay support)
    |-- TransitionController (fade/wipe/slide animations)
    |-- AsyncLoader (background scene loading with progress)
    |-- SceneGroup (parallel scene group management)
    |-- EventHooks (on_before_load, on_loaded, on_unload, on_transition)

Transition Types:
  - NONE: instant swap, no animation
  - FADE: fade out → load → fade in
  - WIPE_LEFT/RIGHT/UP/DOWN: directional screen wipe
  - SLIDE_LEFT/RIGHT/UP/DOWN: slide current scene out, new in
  - DISSOLVE: pixel dissolve effect from random order
  - ZOOM_IN/OUT: scale transition with blur

Scene Lifecycle:
  PENDING    → scene requested but loading has not started
  LOADING    → asset loading and scene construction in progress
  LOADED     → scene fully constructed but not yet activated
  ACTIVE     → scene is receiving Update calls and rendering
  FROZEN     → scene is still loaded but paused (backgrounded)
  UNLOADING  → scene destruction in progress
  UNLOADED   → scene removed from memory
  POOLED     → scene returned to pool for later reuse

Usage:
    sm = SceneManager()
    sm.register_scene("MainMenu", menu_builder)
    sm.register_scene("Level1", level1_builder)
    sm.register_scene("Shop", {shop_builder, permanent=False})
    await sm.load_scene("MainMenu")
    await sm.transition_to("Level1", transition="FADE", duration=1.5)
    sm.push_overlay("Shop")
    sm.pop_overlay()
"""

from __future__ import annotations

import asyncio
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple


class SceneState(Enum):
    PENDING = "pending"
    LOADING = "loading"
    LOADED = "loaded"
    ACTIVE = "active"
    FROZEN = "frozen"
    UNLOADING = "unloading"
    UNLOADED = "unloaded"
    POOLED = "pooled"


class TransitionType(Enum):
    NONE = "none"
    FADE = "fade"
    WIPE_LEFT = "wipe_left"
    WIPE_RIGHT = "wipe_right"
    WIPE_UP = "wipe_up"
    WIPE_DOWN = "wipe_down"
    SLIDE_LEFT = "slide_left"
    SLIDE_RIGHT = "slide_right"
    SLIDE_UP = "slide_up"
    SLIDE_DOWN = "slide_down"
    DISSOLVE = "dissolve"
    ZOOM_IN = "zoom_in"
    ZOOM_OUT = "zoom_out"


@dataclass
class SceneDefinition:
    scene_id: str = field(default_factory=lambda: f"scene_{uuid.uuid4().hex[:8]}")
    name: str = ""
    builder: Optional[Callable[[], Any]] = None
    permanent: bool = True
    poolable: bool = False
    preload: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SceneInstance:
    definition: SceneDefinition = field(default_factory=SceneDefinition)
    instance_id: str = field(default_factory=lambda: f"inst_{uuid.uuid4().hex[:8]}")
    state: SceneState = SceneState.PENDING
    scene_object: Any = None
    load_progress: float = 0.0
    loaded_at: float = 0.0
    activated_at: float = 0.0
    objects_count: int = 0
    _grouped: bool = False
    _frozen_snapshot: Optional[Dict[str, Any]] = None


@dataclass
class TransitionConfig:
    transition_type: TransitionType = TransitionType.FADE
    duration_seconds: float = 0.5
    color: str = "#000000"
    ease_in: bool = True
    ease_out: bool = True
    skip_on_error: bool = True


class SceneManager:
    """Central scene lifecycle manager with transitions and pooling."""

    _instance: Optional["SceneManager"] = None

    def __init__(self):
        self._definitions: Dict[str, SceneDefinition] = {}
        self._instances: Dict[str, SceneInstance] = {}
        self._scene_stack: List[SceneInstance] = []
        self._overlay_stack: List[SceneInstance] = []
        self._scene_pool: Dict[str, List[Any]] = {}
        self._transitioning: bool = False
        self._current_transition: Optional[TransitionConfig] = None
        self._hooks: Dict[str, List[Callable]] = {
            "before_load": [],
            "after_load": [],
            "before_activate": [],
            "after_activate": [],
            "before_unload": [],
            "after_unload": [],
            "transition_start": [],
            "transition_end": [],
        }
        self._total_loads: int = 0
        self._total_unloads: int = 0
        self._MAX_POOL_SIZE = 5
        self._enabled: bool = True

    @classmethod
    def get_instance(cls) -> "SceneManager":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def register(self, name: str, builder: Optional[Callable[[], Any]] = None,
                 permanent: bool = True, poolable: bool = False,
                 preload: bool = False, metadata: Optional[Dict] = None) -> SceneDefinition:
        defn = SceneDefinition(
            name=name, builder=builder, permanent=permanent,
            poolable=poolable, preload=preload, metadata=metadata or {},
        )
        self._definitions[name] = defn
        if preload:
            self._preload_async(name)
        return defn

    def _preload_async(self, name: str) -> None:
        asyncio.create_task(self.load_scene(name))

    def hook(self, event: str, callback: Callable) -> None:
        if event in self._hooks:
            self._hooks[event].append(callback)

    def _fire_hook(self, event: str, *args) -> None:
        for cb in self._hooks.get(event, []):
            try:
                cb(*args)
            except Exception:
                pass

    async def _build_scene(self, definition: SceneDefinition) -> Any:
        if definition.builder:
            result = definition.builder()
            if asyncio.iscoroutine(result):
                return await result
            return result
        return {}

    async def load_scene(self, scene_name: str) -> Optional[SceneInstance]:
        if not self._enabled:
            return None

        definition = self._definitions.get(scene_name)
        if not definition:
            return None

        cached = self._scene_pool.get(scene_name, [])
        from_pool = None
        if cached:
            from_pool = cached.pop(0)

        instance = SceneInstance(
            definition=definition,
            state=SceneState.LOADING,
        )

        self._fire_hook("before_load", instance)

        try:
            scene_obj = from_pool or await self._build_scene(definition)
            instance.scene_object = scene_obj
            instance.load_progress = 1.0
            instance.loaded_at = time.time()
            instance.state = SceneState.LOADED
            instance.objects_count = len(scene_obj) if isinstance(scene_obj, (list, dict)) else 1
        except Exception:
            instance.state = SceneState.UNLOADED
            return None

        self._instances[instance.instance_id] = instance
        self._total_loads += 1

        self._fire_hook("after_load", instance)
        return instance

    async def transition_to(self, scene_name: str,
                            transition: str = "FADE",
                            duration: float = 0.5) -> Optional[SceneInstance]:
        try:
            t_type = TransitionType[transition.upper()]
        except KeyError:
            t_type = TransitionType.NONE

        config = TransitionConfig(
            transition_type=t_type,
            duration_seconds=duration,
        )

        self._transitioning = True
        self._current_transition = config
        self._fire_hook("transition_start", config)

        new_scene = await self.load_scene(scene_name)
        if not new_scene:
            self._transitioning = False
            return None

        for old_scene in reversed(self._scene_stack):
            await self.unload_scene(old_scene)

        self._scene_stack.append(new_scene)
        new_scene.state = SceneState.ACTIVE
        new_scene.activated_at = time.time()

        self._fire_hook("after_activate", new_scene)

        await asyncio.sleep(duration)
        self._transitioning = False
        self._fire_hook("transition_end", new_scene)

        return new_scene

    async def unload_scene(self, scene: SceneInstance) -> None:
        if scene.state in (SceneState.UNLOADING, SceneState.UNLOADED):
            return

        self._fire_hook("before_unload", scene)
        scene.state = SceneState.UNLOADING

        if scene.definition.poolable:
            pool = self._scene_pool.setdefault(scene.definition.name, [])
            if len(pool) < self._MAX_POOL_SIZE:
                scene.state = SceneState.POOLED
                pool.append(scene.scene_object)
                scene.scene_object = None
                self._total_unloads += 1
                self._fire_hook("after_unload", scene)
                return

        scene.scene_object = None
        scene.state = SceneState.UNLOADED
        self._total_unloads += 1
        self._instances.pop(scene.instance_id, None)
        self._fire_hook("after_unload", scene)

    def push_overlay(self, scene_name: str) -> Optional[SceneInstance]:
        instance = self._instances.get(scene_name)
        if not instance:
            return None
        self._overlay_stack.append(instance)
        instance.state = SceneState.ACTIVE
        return instance

    def pop_overlay(self) -> Optional[SceneInstance]:
        if not self._overlay_stack:
            return None
        instance = self._overlay_stack.pop()
        if self._scene_stack:
            instance.state = SceneState.FROZEN
        return instance

    def push_scene(self, scene_name: str) -> Optional[SceneInstance]:
        defn = self._definitions.get(scene_name)
        if not defn:
            return None
        instance = SceneInstance(definition=defn, state=SceneState.ACTIVE)
        self._scene_stack.append(instance)
        return instance

    def pop_scene(self) -> Optional[SceneInstance]:
        if not self._scene_stack:
            return None
        return self._scene_stack.pop()

    def get_active_scene(self) -> Optional[SceneInstance]:
        if self._scene_stack:
            return self._scene_stack[-1]
        return None

    def get_active_overlay(self) -> Optional[SceneInstance]:
        if self._overlay_stack:
            return self._overlay_stack[-1]
        return None

    def is_transitioning(self) -> bool:
        return self._transitioning

    def get_current_transition(self) -> Optional[TransitionConfig]:
        return self._current_transition

    def update_pool(self) -> None:
        for name in list(self._scene_pool.keys()):
            pool = self._scene_pool[name]
            while len(pool) > self._MAX_POOL_SIZE:
                pool.pop(0)

    def clear_pool(self) -> None:
        self._scene_pool.clear()

    def list_definitions(self) -> List[Dict[str, Any]]:
        return [
            {
                "name": d.name,
                "permanent": d.permanent,
                "poolable": d.poolable,
                "preload": d.preload,
            }
            for d in self._definitions.values()
        ]

    def get_scene_stack(self) -> List[str]:
        return [s.definition.name for s in self._scene_stack]

    def get_overlay_stack(self) -> List[str]:
        return [s.definition.name for s in self._overlay_stack]

    def get_scene_instance(self, instance_id: str) -> Optional[SceneInstance]:
        return self._instances.get(instance_id)

    def get_local_objects(self) -> List[Any]:
        active = self.get_active_scene()
        if active and active.scene_object:
            if isinstance(active.scene_object, dict):
                return [active.scene_object]
            return active.scene_object
        return []

    def get_stats(self) -> Dict[str, Any]:
        return {
            "definitions": len(self._definitions),
            "instances": len(self._instances),
            "stack_depth": len(self._scene_stack),
            "overlay_depth": len(self._overlay_stack),
            "pool_size": sum(len(v) for v in self._scene_pool.values()),
            "pool_scenes": len(self._scene_pool),
            "total_loads": self._total_loads,
            "total_unloads": self._total_unloads,
            "transitioning": self._transitioning,
            "current_transition": self._current_transition.transition_type.value
                if self._current_transition else "none",
            "enabled": self._enabled,
            "stack": self.get_scene_stack(),
            "overlays": self.get_overlay_stack(),
        }

    def set_enabled(self, enabled: bool) -> None:
        self._enabled = enabled

    def set_max_pool_size(self, size: int) -> None:
        self._MAX_POOL_SIZE = max(1, size)

    def reset(self) -> None:
        self._scene_stack.clear()
        self._overlay_stack.clear()
        self._scene_pool.clear()
        self._instances.clear()
        self._definitions.clear()
        self._transitioning = False


def get_scene_manager() -> SceneManager:
    return SceneManager.get_instance()
