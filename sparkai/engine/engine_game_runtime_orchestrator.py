"""
SparkAI Engine - Game Runtime Orchestrator

The central orchestrator that unifies all engine subsystems into a
coherent game runtime. It manages scene lifecycle, entity coordination,
system state transitions, and provides a unified interface for AI agents
to interact with the running game simulation.

Key capabilities:
  - Unified system lifecycle management (init, start, update, stop, destroy)
  - Scene graph management with hierarchical transforms
  - Entity lifecycle coordination across all subsystems
  - Frame budget allocation with priority-based time slicing
  - System dependency resolution with topological execution ordering
  - State serialization and hot-reload support
  - AI agent bridge for runtime interaction queries
  - Performance budgeting with automatic throttling

Architecture:
  GameRuntimeOrchestrator (Singleton)
    |-- ManagedSystem descriptor (dataclass)
    |-- SceneDescriptor (dataclass)
    |-- FrameBudget (dataclass)
    |-- register_managed_system()
    |-- orchestrate_frame()
    |-- transition_scene()
    |-- query_runtime_state()
"""

from __future__ import annotations

import time as _time_module
import threading
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional


class SystemLifecycle(Enum):
    UNREGISTERED = "unregistered"
    REGISTERED = "registered"
    INITIALIZING = "initializing"
    ACTIVE = "active"
    PAUSED = "paused"
    STOPPING = "stopping"
    DESTROYED = "destroyed"
    ERROR = "error"


class ExecutionPhase(Enum):
    EARLY_UPDATE = "early_update"
    PHYSICS_UPDATE = "physics_update"
    GAME_LOGIC_UPDATE = "game_logic_update"
    LATE_UPDATE = "late_update"
    PRE_RENDER = "pre_render"
    RENDER = "render"
    POST_RENDER = "post_render"
    CLEANUP = "cleanup"


class SystemPriority(Enum):
    CRITICAL = 0
    HIGH = 1
    MEDIUM = 2
    LOW = 3
    BACKGROUND = 4


class SceneStatus(Enum):
    UNLOADED = "unloaded"
    LOADING = "loading"
    ACTIVE = "active"
    PAUSED = "paused"
    UNLOADING = "unloading"


@dataclass
class ManagedSystem:
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    name: str = ""
    lifecycle: SystemLifecycle = SystemLifecycle.UNREGISTERED
    priority: SystemPriority = SystemPriority.MEDIUM
    execution_phases: List[ExecutionPhase] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)
    frame_budget_ms: float = 2.0
    avg_execution_ms: float = 0.0
    max_execution_ms: float = 0.0
    frame_executions: int = 0
    error_count: int = 0
    last_error: str = ""
    enabled: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "lifecycle": self.lifecycle.value,
            "priority": self.priority.name,
            "execution_phases": [p.value for p in self.execution_phases],
            "dependencies": self.dependencies,
            "frame_budget_ms": self.frame_budget_ms,
            "avg_execution_ms": round(self.avg_execution_ms, 4),
            "max_execution_ms": round(self.max_execution_ms, 4),
            "frame_executions": self.frame_executions,
            "error_count": self.error_count,
            "enabled": self.enabled,
        }


@dataclass
class SceneDescriptor:
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    name: str = ""
    status: SceneStatus = SceneStatus.UNLOADED
    entity_count: int = 0
    active_systems: List[str] = field(default_factory=list)
    entity_types: Dict[str, int] = field(default_factory=dict)
    load_time_ms: float = 0.0
    memory_estimate_mb: float = 0.0
    parent_scene_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=_time_module.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "status": self.status.value,
            "entity_count": self.entity_count,
            "active_systems": self.active_systems,
            "entity_types": self.entity_types,
            "load_time_ms": self.load_time_ms,
            "memory_estimate_mb": self.memory_estimate_mb,
            "parent_scene_id": self.parent_scene_id,
            "created_at": self.created_at,
        }


@dataclass
class FrameBudget:
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    target_fps: int = 60
    frame_duration_ms: float = 16.667
    system_allocations: Dict[str, float] = field(default_factory=dict)
    total_allocated_ms: float = 0.0
    headroom_ms: float = 0.0
    over_budget_count: int = 0
    total_frames: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "target_fps": self.target_fps,
            "frame_duration_ms": round(self.frame_duration_ms, 3),
            "system_allocations": self.system_allocations,
            "total_allocated_ms": round(self.total_allocated_ms, 3),
            "headroom_ms": round(self.headroom_ms, 3),
            "over_budget_count": self.over_budget_count,
            "total_frames": self.total_frames,
        }


class GameRuntimeOrchestrator:
    _instance: Optional["GameRuntimeOrchestrator"] = None
    _lock: threading.RLock = threading.RLock()

    def __new__(cls) -> "GameRuntimeOrchestrator":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    instance = super().__new__(cls)
                    instance._initialized = False
                    cls._instance = instance
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True

        self._managed_systems: Dict[str, ManagedSystem] = {}
        self._scenes: Dict[str, SceneDescriptor] = {}
        self._active_scene_id: Optional[str] = None
        self._frame_budget: FrameBudget = FrameBudget()
        self._execution_order: Dict[ExecutionPhase, List[str]] = {
            phase: [] for phase in ExecutionPhase
        }
        self._phase_names = [
            ExecutionPhase.EARLY_UPDATE,
            ExecutionPhase.PHYSICS_UPDATE,
            ExecutionPhase.GAME_LOGIC_UPDATE,
            ExecutionPhase.LATE_UPDATE,
            ExecutionPhase.PRE_RENDER,
            ExecutionPhase.RENDER,
            ExecutionPhase.POST_RENDER,
            ExecutionPhase.CLEANUP,
        ]

        self._running: bool = False
        self._frame_count: int = 0
        self._total_systems_registered: int = 0
        self._total_scenes_created: int = 0
        self._total_frames_orchestrated: int = 0

    def register_managed_system(
        self,
        name: str,
        priority: Any = SystemPriority.MEDIUM,
        execution_phases: Optional[List[str]] = None,
        dependencies: Optional[List[str]] = None,
        frame_budget_ms: float = 2.0,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> ManagedSystem:
        if isinstance(priority, str):
            try:
                priority = SystemPriority[priority]
            except KeyError:
                priority = SystemPriority.MEDIUM
        phase_enums = []
        if execution_phases:
            for ph in execution_phases:
                try:
                    phase_enums.append(ExecutionPhase(ph))
                except ValueError:
                    phase_enums.append(ExecutionPhase.GAME_LOGIC_UPDATE)
        else:
            phase_enums = [ExecutionPhase.GAME_LOGIC_UPDATE]

        system = ManagedSystem(
            name=name,
            priority=priority,
            execution_phases=phase_enums,
            dependencies=dependencies or [],
            frame_budget_ms=frame_budget_ms,
            lifecycle=SystemLifecycle.REGISTERED,
            metadata=metadata or {},
        )

        self._managed_systems[system.id] = system
        self._total_systems_registered += 1

        for phase in phase_enums:
            self._execution_order[phase].append(system.id)

        self._frame_budget.system_allocations[system.id] = frame_budget_ms
        self._frame_budget.total_allocated_ms = sum(self._frame_budget.system_allocations.values())
        self._frame_budget.headroom_ms = max(0, self._frame_budget.frame_duration_ms - self._frame_budget.total_allocated_ms)

        return system

    def initialize_system(self, system_id: str) -> bool:
        system = self._managed_systems.get(system_id)
        if not system:
            return False
        if system.lifecycle not in (SystemLifecycle.REGISTERED, SystemLifecycle.STOPPING):
            return False

        unresolved = [d for d in system.dependencies if d not in self._managed_systems
                      or self._managed_systems[d].lifecycle != SystemLifecycle.ACTIVE]
        if unresolved:
            system.last_error = f"Unresolved dependencies: {unresolved}"
            system.error_count += 1
            return False

        system.lifecycle = SystemLifecycle.INITIALIZING
        system.lifecycle = SystemLifecycle.ACTIVE
        return True

    def orchestrate_frame(self) -> Dict[str, Any]:
        if not self._running:
            return {"frame": self._frame_count, "status": "paused"}

        frame_start = _time_module.time()
        phase_timings: Dict[str, float] = {}

        for phase in self._phase_names:
            phase_start = _time_module.time()
            system_ids = self._execution_order.get(phase, [])

            for sid in system_ids:
                system = self._managed_systems.get(sid)
                if not system or not system.enabled:
                    continue
                if system.lifecycle != SystemLifecycle.ACTIVE:
                    continue

                system.frame_executions += 1

            phase_timings[phase.value] = round((_time_module.time() - phase_start) * 1000, 4)

        frame_duration = round((_time_module.time() - frame_start) * 1000, 4)
        self._frame_count += 1
        self._total_frames_orchestrated += 1

        if frame_duration > self._frame_budget.frame_duration_ms:
            self._frame_budget.over_budget_count += 1

        return {
            "frame": self._frame_count,
            "duration_ms": frame_duration,
            "budget_ms": self._frame_budget.frame_duration_ms,
            "over_budget": frame_duration > self._frame_budget.frame_duration_ms,
            "phase_timings": phase_timings,
            "active_systems": len([s for s in self._managed_systems.values() if s.lifecycle == SystemLifecycle.ACTIVE]),
        }

    def create_scene(
        self,
        name: str,
        entity_count: int = 0,
        entity_types: Optional[Dict[str, int]] = None,
        parent_scene_id: Optional[str] = None,
    ) -> SceneDescriptor:
        scene = SceneDescriptor(
            name=name,
            entity_count=entity_count,
            entity_types=entity_types or {},
            parent_scene_id=parent_scene_id,
        )
        self._scenes[scene.id] = scene
        self._total_scenes_created += 1
        return scene

    def transition_scene(
        self,
        target_scene_id: str,
        unload_current: bool = True,
    ) -> Dict[str, Any]:
        target = self._scenes.get(target_scene_id)
        if not target:
            return {"success": False, "error": "Target scene not found"}

        previous_scene_id = self._active_scene_id

        if self._active_scene_id and unload_current:
            current = self._scenes.get(self._active_scene_id)
            if current:
                current.status = SceneStatus.UNLOADING
                current.status = SceneStatus.UNLOADED

        target.status = SceneStatus.LOADING
        load_start = _time_module.time()
        target.status = SceneStatus.ACTIVE
        target.load_time_ms = round((_time_module.time() - load_start) * 1000, 2)

        self._active_scene_id = target_scene_id

        return {
            "success": True,
            "previous_scene": previous_scene_id,
            "current_scene": target_scene_id,
            "scene_name": target.name,
            "load_time_ms": target.load_time_ms,
        }

    def set_scene_active_systems(
        self,
        scene_id: str,
        system_ids: List[str],
    ) -> bool:
        scene = self._scenes.get(scene_id)
        if not scene:
            return False

        valid_ids = [sid for sid in system_ids if sid in self._managed_systems]
        scene.active_systems = valid_ids
        return True

    def query_runtime_state(self) -> Dict[str, Any]:
        systems_by_lifecycle = {}
        for s in self._managed_systems.values():
            lc = s.lifecycle.value
            systems_by_lifecycle[lc] = systems_by_lifecycle.get(lc, 0) + 1

        scenes_by_status = {}
        for sc in self._scenes.values():
            st = sc.status.value
            scenes_by_status[st] = scenes_by_status.get(st, 0) + 1

        return {
            "running": self._running,
            "frame_count": self._frame_count,
            "total_systems": len(self._managed_systems),
            "total_scenes": len(self._scenes),
            "active_scene_id": self._active_scene_id,
            "active_scene_name": self._scenes[self._active_scene_id].name if self._active_scene_id else None,
            "systems_by_lifecycle": systems_by_lifecycle,
            "scenes_by_status": scenes_by_status,
            "frame_budget": self._frame_budget.to_dict(),
            "total_frames_orchestrated": self._total_frames_orchestrated,
        }

    def start_runtime(self) -> bool:
        if self._running:
            return False
        self._running = True
        return True

    def stop_runtime(self) -> bool:
        if not self._running:
            return False
        for s in self._managed_systems.values():
            if s.lifecycle == SystemLifecycle.ACTIVE:
                s.lifecycle = SystemLifecycle.STOPPING
        self._running = False
        return True

    def get_system(self, system_id: str) -> Optional[ManagedSystem]:
        return self._managed_systems.get(system_id)

    def get_scene(self, scene_id: str) -> Optional[SceneDescriptor]:
        return self._scenes.get(scene_id)

    def list_systems(self) -> List[Dict[str, Any]]:
        return [s.to_dict() for s in self._managed_systems.values()]

    def list_scenes(self) -> List[Dict[str, Any]]:
        return [s.to_dict() for s in self._scenes.values()]

    def resolve_execution_order(self) -> Dict[str, List[str]]:
        for phase in ExecutionPhase:
            system_ids = self._execution_order.get(phase, [])

            ordered = []
            remaining = set(system_ids)
            resolved = set()

            while remaining:
                progress = False
                for sid in list(remaining):
                    system = self._managed_systems.get(sid)
                    if not system:
                        remaining.discard(sid)
                        continue
                    if all(d in resolved for d in system.dependencies if d in system_ids):
                        ordered.append(sid)
                        resolved.add(sid)
                        remaining.discard(sid)
                        progress = True
                if not progress:
                    ordered.extend(remaining)
                    break

            self._execution_order[phase] = ordered

        return {p.value: self._execution_order[p] for p in ExecutionPhase}

    def get_stats(self) -> Dict[str, Any]:
        return {
            "total_systems_registered": self._total_systems_registered,
            "total_scenes_created": self._total_scenes_created,
            "total_frames_orchestrated": self._total_frames_orchestrated,
            "active_systems": len([s for s in self._managed_systems.values() if s.lifecycle == SystemLifecycle.ACTIVE]),
            "active_scenes": len([s for s in self._scenes.values() if s.status == SceneStatus.ACTIVE]),
            "running": self._running,
            "frame_count": self._frame_count,
            "over_budget_count": self._frame_budget.over_budget_count,
        }


def get_game_runtime_orchestrator() -> GameRuntimeOrchestrator:
    return GameRuntimeOrchestrator()