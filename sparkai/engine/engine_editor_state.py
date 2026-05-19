"""
SparkLabs Engine - Editor State Machine

Centralized editor workflow state management for agent-driven editing
sessions. Tracks active tools, selection context, viewport camera,
and editing mode transitions. Provides agents with full awareness of
the current editor environment.

Architecture:
  EditorStateMachine
    |-- ToolRegistry (active tool tracking and switching)
    |-- SelectionManager (entity/scene selection context)
    |-- ViewportState (camera and rendering state)
    |-- ModeController (edit/play/pause/step modes)
    |-- ContextBroadcaster (state change notifications)

Editor Modes:
  - EDIT: full editing capabilities with agent assistance
  - PLAY: runtime game preview with debugging
  - PAUSE: frozen state for inspection
  - STEP: frame-by-frame advancement
  - SIMULATE: physics-only preview mode
"""

from __future__ import annotations

import threading
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple


class EditorMode(Enum):
    EDIT = "edit"
    PLAY = "play"
    PAUSE = "pause"
    STEP = "step"
    SIMULATE = "simulate"
    BUILD = "build"


class ActiveTool(Enum):
    SELECT = "select"
    MOVE = "move"
    ROTATE = "rotate"
    SCALE = "scale"
    PAINT = "paint"
    TERRAIN = "terrain"
    TILE = "tile"
    SPLINE = "spline"
    TEXT = "text"
    MEASURE = "measure"


class SelectionScope(Enum):
    ENTITY = "entity"
    COMPONENT = "component"
    VERTEX = "vertex"
    EDGE = "edge"
    FACE = "face"
    MATERIAL = "material"
    LIGHT = "light"


class InteractionMode(Enum):
    NORMAL = "normal"
    AGENT_GUIDED = "agent_guided"
    COLLABORATIVE = "collaborative"
    TUTORIAL = "tutorial"
    MACRO_PLAYBACK = "macro_playback"


@dataclass
class ViewportState:
    camera_position: Tuple[float, float, float] = (0.0, 10.0, 20.0)
    camera_rotation: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    orthographic: bool = False
    grid_visible: bool = True
    wireframe_mode: bool = False
    gizmos_visible: bool = True
    render_scale: float = 1.0
    aspect_ratio: float = 1.778

    def to_dict(self) -> Dict[str, Any]:
        return {
            "camera_position": list(self.camera_position),
            "camera_rotation": list(self.camera_rotation),
            "orthographic": self.orthographic,
            "grid_visible": self.grid_visible,
            "wireframe_mode": self.wireframe_mode,
            "gizmos_visible": self.gizmos_visible,
            "render_scale": self.render_scale,
            "aspect_ratio": self.aspect_ratio,
        }


@dataclass
class SelectionSnapshot:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    entity_ids: List[str] = field(default_factory=list)
    component_ids: List[str] = field(default_factory=list)
    primary_entity: Optional[str] = None
    scope: SelectionScope = SelectionScope.ENTITY
    bounds_center: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    bounds_size: Tuple[float, float, float] = (1.0, 1.0, 1.0)
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "entity_count": len(self.entity_ids),
            "component_count": len(self.component_ids),
            "primary_entity": self.primary_entity,
            "scope": self.scope.value,
            "bounds_center": list(self.bounds_center),
            "bounds_size": list(self.bounds_size),
            "timestamp": self.timestamp,
        }


@dataclass
class EditorSnapshot:
    mode: EditorMode = EditorMode.EDIT
    active_tool: ActiveTool = ActiveTool.SELECT
    interaction: InteractionMode = InteractionMode.NORMAL
    current_scene: str = ""
    viewport: ViewportState = field(default_factory=ViewportState)
    selection: SelectionSnapshot = field(default_factory=SelectionSnapshot)
    is_dirty: bool = False
    last_saved: float = 0.0
    session_elapsed: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "mode": self.mode.value,
            "active_tool": self.active_tool.value,
            "interaction": self.interaction.value,
            "current_scene": self.current_scene,
            "viewport": self.viewport.to_dict(),
            "selection": self.selection.to_dict(),
            "is_dirty": self.is_dirty,
            "last_saved": self.last_saved,
            "session_elapsed": self.session_elapsed,
        }


class EditorStateMachine:
    """
    Editor state coordinator providing agents with full environmental
    awareness of the editing workspace.

    Manages mode transitions, tool state, selection context, and
    interaction modes. Emits events on every state change for reactive
    UI updates and agent-driven workflows.
    """

    _instance: Optional["EditorStateMachine"] = None
    _lock: threading.RLock = threading.RLock()

    MAX_SNAPSHOTS = 100

    def __init__(self):
        self._state = EditorSnapshot()
        self._snapshots: List[EditorSnapshot] = []
        self._event_listeners: Dict[str, List[Callable]] = {}
        self._mode_history: List[Tuple[EditorMode, float]] = []
        self._tool_history: List[Tuple[ActiveTool, float]] = []
        self._custom_state: Dict[str, Any] = {}
        self._locked: bool = False
        self._total_mode_changes: int = 0
        self._total_tool_changes: int = 0
        self._total_selections: int = 0
        self._take_snapshot()

    @classmethod
    def get_instance(cls) -> "EditorStateMachine":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    # ------------------------------------------------------------------
    # Mode Management
    # ------------------------------------------------------------------

    def set_mode(self, mode: EditorMode) -> Dict[str, Any]:
        if self._locked:
            return {"error": "State machine locked", "current_mode": self._state.mode.value}

        previous = self._state.mode
        if previous == mode:
            return {"unchanged": True, "mode": mode.value}

        self._state.mode = mode
        self._mode_history.append((mode, time.time()))
        self._total_mode_changes += 1

        if len(self._mode_history) > 50:
            self._mode_history = self._mode_history[-50:]

        self._take_snapshot()

        change = {"action": "mode_changed", "previous": previous.value, "current": mode.value}
        self._emit("mode_change", change)
        return change

    def get_mode(self) -> EditorMode:
        return self._state.mode

    def is_in_mode(self, *modes: EditorMode) -> bool:
        return self._state.mode in modes

    # ------------------------------------------------------------------
    # Tool Management
    # ------------------------------------------------------------------

    def set_tool(self, tool: ActiveTool) -> Dict[str, Any]:
        if self._locked:
            return {"error": "State machine locked"}

        previous = self._state.active_tool
        if previous == tool:
            return {"unchanged": True, "tool": tool.value}

        self._state.active_tool = tool
        self._tool_history.append((tool, time.time()))
        self._total_tool_changes += 1

        if len(self._tool_history) > 50:
            self._tool_history = self._tool_history[-50:]

        change = {"action": "tool_changed", "previous": previous.value, "current": tool.value}
        self._emit("tool_change", change)
        return change

    def get_tool(self) -> ActiveTool:
        return self._state.active_tool

    # ------------------------------------------------------------------
    # Selection Management
    # ------------------------------------------------------------------

    def select(
        self,
        entity_ids: List[str],
        scope: SelectionScope = SelectionScope.ENTITY,
        primary_entity: Optional[str] = None,
    ) -> Dict[str, Any]:
        with self._lock:
            selection = SelectionSnapshot(
                entity_ids=list(entity_ids),
                scope=scope,
                primary_entity=primary_entity or (entity_ids[0] if entity_ids else None),
            )
            self._state.selection = selection
            self._total_selections += 1

        result = {"action": "selection_changed", "entity_count": len(entity_ids)}
        self._emit("selection_change", result)
        return result

    def clear_selection(self) -> Dict[str, Any]:
        self._state.selection = SelectionSnapshot()
        result = {"action": "selection_cleared"}
        self._emit("selection_change", result)
        return result

    def get_selection(self) -> SelectionSnapshot:
        return self._state.selection

    def get_selected_entities(self) -> List[str]:
        return list(self._state.selection.entity_ids)

    # ------------------------------------------------------------------
    # Interaction Mode
    # ------------------------------------------------------------------

    def set_interaction(self, mode: InteractionMode) -> Dict[str, Any]:
        previous = self._state.interaction
        self._state.interaction = mode
        change = {"action": "interaction_changed", "previous": previous.value, "current": mode.value}
        self._emit("interaction_change", change)
        return change

    def get_interaction(self) -> InteractionMode:
        return self._state.interaction

    # ------------------------------------------------------------------
    # Viewport Control
    # ------------------------------------------------------------------

    def update_viewport(
        self,
        position: Optional[Tuple[float, float, float]] = None,
        rotation: Optional[Tuple[float, float, float]] = None,
        orthographic: Optional[bool] = None,
        render_scale: Optional[float] = None,
    ) -> Dict[str, Any]:
        vp = self._state.viewport
        if position:
            vp.camera_position = position
        if rotation:
            vp.camera_rotation = rotation
        if orthographic is not None:
            vp.orthographic = orthographic
        if render_scale is not None:
            vp.render_scale = max(0.1, min(4.0, render_scale))

        result = {"action": "viewport_updated", "viewport": vp.to_dict()}
        self._emit("viewport_change", result)
        return result

    def get_viewport(self) -> ViewportState:
        return self._state.viewport

    # ------------------------------------------------------------------
    # Scene Context
    # ------------------------------------------------------------------

    def set_scene(self, scene_name: str) -> None:
        self._state.current_scene = scene_name
        self._state.is_dirty = True
        self._emit("scene_change", {"scene": scene_name})

    def get_scene(self) -> str:
        return self._state.current_scene

    def mark_saved(self) -> None:
        self._state.is_dirty = False
        self._state.last_saved = time.time()
        self._emit("file_saved", {"timestamp": self._state.last_saved})

    def mark_dirty(self) -> None:
        self._state.is_dirty = True
        self._emit("file_dirty", {})

    def is_dirty(self) -> bool:
        return self._state.is_dirty

    # ------------------------------------------------------------------
    # Locking (prevents changes during agent operations)
    # ------------------------------------------------------------------

    def lock(self) -> None:
        self._locked = True
        self._emit("state_locked", {})

    def unlock(self) -> None:
        self._locked = False
        self._emit("state_unlocked", {})

    def is_locked(self) -> bool:
        return self._locked

    # ------------------------------------------------------------------
    # Custom State
    # ------------------------------------------------------------------

    def set_custom(self, key: str, value: Any) -> None:
        self._custom_state[key] = value
        self._emit("custom_state_change", {"key": key})

    def get_custom(self, key: str, default: Any = None) -> Any:
        return self._custom_state.get(key, default)

    def clear_custom(self) -> None:
        self._custom_state.clear()

    # ------------------------------------------------------------------
    # Snapshots
    # ------------------------------------------------------------------

    def _take_snapshot(self) -> None:
        snap = EditorSnapshot(
            mode=self._state.mode,
            active_tool=self._state.active_tool,
            interaction=self._state.interaction,
            current_scene=self._state.current_scene,
            viewport=ViewportState(
                camera_position=self._state.viewport.camera_position,
                camera_rotation=self._state.viewport.camera_rotation,
                orthographic=self._state.viewport.orthographic,
                grid_visible=self._state.viewport.grid_visible,
                wireframe_mode=self._state.viewport.wireframe_mode,
                gizmos_visible=self._state.viewport.gizmos_visible,
                render_scale=self._state.viewport.render_scale,
                aspect_ratio=self._state.viewport.aspect_ratio,
            ),
            selection=SelectionSnapshot(
                entity_ids=list(self._state.selection.entity_ids),
                scope=self._state.selection.scope,
                primary_entity=self._state.selection.primary_entity,
            ),
            is_dirty=self._state.is_dirty,
            last_saved=self._state.last_saved,
            session_elapsed=time.time(),
        )
        self._snapshots.append(snap)
        while len(self._snapshots) > self.MAX_SNAPSHOTS:
            self._snapshots.pop(0)

    def get_recent_snapshots(self, count: int = 10) -> List[Dict[str, Any]]:
        return [s.to_dict() for s in self._snapshots[-count:]]

    # ------------------------------------------------------------------
    # Full State
    # ------------------------------------------------------------------

    def get_full_state(self) -> Dict[str, Any]:
        state = self._state.to_dict()
        state["locked"] = self._locked
        state["custom_state_keys"] = list(self._custom_state.keys())
        return state

    # ------------------------------------------------------------------
    # Events
    # ------------------------------------------------------------------

    def on(self, event: str, callback: Callable) -> None:
        if event not in self._event_listeners:
            self._event_listeners[event] = []
        self._event_listeners[event].append(callback)

    def _emit(self, event: str, data: Dict[str, Any]) -> None:
        for listener in self._event_listeners.get(event, []):
            try:
                listener(data)
            except Exception:
                pass

    # ------------------------------------------------------------------
    # Stats
    # ------------------------------------------------------------------

    def get_stats(self) -> Dict[str, Any]:
        return {
            "mode": self._state.mode.value,
            "tool": self._state.active_tool.value,
            "interaction": self._state.interaction.value,
            "scene": self._state.current_scene,
            "selection_count": len(self._state.selection.entity_ids),
            "is_dirty": self._state.is_dirty,
            "is_locked": self._locked,
            "total_mode_changes": self._total_mode_changes,
            "total_tool_changes": self._total_tool_changes,
            "total_selections": self._total_selections,
            "snapshot_count": len(self._snapshots),
            "custom_state_keys": len(self._custom_state),
            "tool_history_recent": [
                t.value for t, _ in self._tool_history[-5:]
            ],
            "mode_history_recent": [
                m.value for m, _ in self._mode_history[-5:]
            ],
        }


def get_editor_state() -> EditorStateMachine:
    return EditorStateMachine.get_instance()