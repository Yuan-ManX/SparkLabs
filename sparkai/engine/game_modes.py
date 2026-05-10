"""
SparkLabs Engine - Game Modes System

Game mode state machine for defining and transitioning between
distinct gameplay phases. Supports mode lifecycle hooks, mode-specific
configuration, and conditional transitions for AI-native games.

Architecture:
  GameModeSystem
    |-- ModeDefinition (state configuration with hooks)
    |-- ModeStack (hierarchical mode overlay)
    |-- TransitionEngine (condition-based mode switching)
    |-- ModeConfig (per-mode game rule parameters)
    |-- ModeEventBus (mode-change notifications)

Built-in Game Modes:
  - MAIN_MENU: title screen and settings
  - PLAYING: active gameplay
  - PAUSED: pause menu overlay
  - GAME_OVER: defeat or victory screen
  - CUTSCENE: cinematic sequence
  - EDITOR: level/scene editing
  - LOADING: asset loading transition
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Callable, Dict, List, Optional, Set, Tuple


class BuiltInMode(Enum):
    MAIN_MENU = "main_menu"
    PLAYING = "playing"
    PAUSED = "paused"
    GAME_OVER = "game_over"
    CUTSCENE = "cutscene"
    EDITOR = "editor"
    LOADING = "loading"


class ModeLayer(Enum):
    BASE = "base"
    OVERLAY = "overlay"
    MODAL = "modal"


@dataclass
class ModeDefinition:
    name: str = ""
    layer: ModeLayer = ModeLayer.BASE
    allow_input: bool = True
    allow_updates: bool = True
    allow_rendering: bool = True
    pause_game_time: bool = False
    keep_audio: bool = False
    keep_physics: bool = False
    transition_in_time: float = 0.3
    transition_out_time: float = 0.3
    config: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "layer": self.layer.value,
            "allow_input": self.allow_input,
            "allow_updates": self.allow_updates,
            "allow_rendering": self.allow_rendering,
            "pause_game_time": self.pause_game_time,
            "transition_in_time": self.transition_in_time,
            "transition_out_time": self.transition_out_time,
            "config": self.config,
        }


BUILTIN_MODE_DEFINITIONS: Dict[BuiltInMode, ModeDefinition] = {
    BuiltInMode.MAIN_MENU: ModeDefinition(
        name="main_menu",
        layer=ModeLayer.BASE,
        allow_updates=False,
        keep_audio=True,
    ),
    BuiltInMode.PLAYING: ModeDefinition(
        name="playing",
        layer=ModeLayer.BASE,
        allow_input=True,
        allow_updates=True,
        allow_rendering=True,
    ),
    BuiltInMode.PAUSED: ModeDefinition(
        name="paused",
        layer=ModeLayer.OVERLAY,
        allow_updates=False,
        allow_rendering=True,
        pause_game_time=True,
        keep_audio=True,
    ),
    BuiltInMode.GAME_OVER: ModeDefinition(
        name="game_over",
        layer=ModeLayer.MODAL,
        allow_input=True,
        allow_updates=False,
        pause_game_time=True,
        transition_in_time=0.5,
    ),
    BuiltInMode.CUTSCENE: ModeDefinition(
        name="cutscene",
        layer=ModeLayer.MODAL,
        allow_updates=True,
        keep_audio=True,
        transition_in_time=0.5,
        transition_out_time=0.5,
    ),
    BuiltInMode.EDITOR: ModeDefinition(
        name="editor",
        layer=ModeLayer.BASE,
        allow_input=True,
        allow_updates=True,
        allow_rendering=True,
        keep_physics=False,
    ),
    BuiltInMode.LOADING: ModeDefinition(
        name="loading",
        layer=ModeLayer.MODAL,
        allow_input=False,
        allow_updates=False,
        allow_rendering=True,
    ),
}


@dataclass
class ModeSnapshot:
    mode_name: str = ""
    layer: ModeLayer = ModeLayer.BASE
    entered_at: float = field(default_factory=time.time)
    elapsed: float = 0.0
    config: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "mode_name": self.mode_name,
            "layer": self.layer.value,
            "elapsed": round(self.elapsed, 3),
            "config": self.config,
        }


class TransitionPhase(Enum):
    NONE = "none"
    EXITING = "exiting"
    ENTERING = "entering"


class GameModeSystem:
    """
    Game mode state machine for AI-native games.

    Manages transitions between gameplay modes (menu, playing,
    paused, game over, etc.) with lifecycle hooks for enter/exit
    events. Supports mode stacking for overlays and modal states.

    Usage:
        modes = GameModeSystem()
        modes.start(BuiltInMode.MAIN_MENU)
        modes.push(BuiltInMode.PLAYING)
        modes.push(BuiltInMode.PAUSED)
        modes.pop()
        current = modes.get_current()
        print(current.name)
    """

    _instance: Optional["GameModeSystem"] = None

    def __init__(self):
        self._definitions: Dict[str, ModeDefinition] = {}
        self._stack: List[ModeSnapshot] = []
        self._current_transition: TransitionPhase = TransitionPhase.NONE
        self._transition_start: float = 0.0
        self._transition_from: Optional[str] = None
        self._transition_to: Optional[str] = None
        self._mode_change_count: int = 0

        self._enter_hooks: Dict[str, List[Callable[[ModeSnapshot], None]]] = {}
        self._exit_hooks: Dict[str, List[Callable[[ModeSnapshot], None]]] = {}
        self._transition_hooks: Dict[str, List[Callable[[str, str], None]]] = {}

        self._register_builtin()

    @classmethod
    def get_instance(cls) -> "GameModeSystem":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def _register_builtin(self) -> None:
        for mode, definition in BUILTIN_MODE_DEFINITIONS.items():
            self.register_mode(definition)

    def register_mode(self, definition: ModeDefinition) -> None:
        self._definitions[definition.name] = definition

    def unregister_mode(self, name: str) -> bool:
        if name in self._definitions:
            if any(s.mode_name == name for s in self._stack):
                return False
            del self._definitions[name]
            return True
        return False

    def register_enter_hook(self, mode_name: str, hook: Callable[[ModeSnapshot], None]) -> None:
        if mode_name not in self._enter_hooks:
            self._enter_hooks[mode_name] = []
        self._enter_hooks[mode_name].append(hook)

    def register_exit_hook(self, mode_name: str, hook: Callable[[ModeSnapshot], None]) -> None:
        if mode_name not in self._exit_hooks:
            self._exit_hooks[mode_name] = []
        self._exit_hooks[mode_name].append(hook)

    def register_transition_hook(
        self,
        from_mode: str,
        to_mode: str,
        hook: Callable[[str, str], None],
    ) -> None:
        key = f"{from_mode}->{to_mode}"
        if key not in self._transition_hooks:
            self._transition_hooks[key] = []
        self._transition_hooks[key].append(hook)

    def start(self, mode_name: str, config: Optional[Dict[str, Any]] = None) -> bool:
        self._stack.clear()
        return self.push(mode_name, config=config)

    def push(self, mode_name: str, config: Optional[Dict[str, Any]] = None) -> bool:
        definition = self._definitions.get(mode_name)
        if definition is None:
            return False

        for existing in self._stack:
            existing_def = self._definitions.get(existing.mode_name)
            if existing_def and existing_def.layer == ModeLayer.MODAL:
                return False

        if self._stack:
            prev = self._stack[-1]
            self._fire_exit_hooks(prev.mode_name, prev)
            self._fire_transition_hooks(prev.mode_name, mode_name)

        snapshot = ModeSnapshot(
            mode_name=mode_name,
            layer=definition.layer,
            config=config or {},
        )
        self._stack.append(snapshot)
        self._mode_change_count += 1
        self._fire_enter_hooks(mode_name, snapshot)

        return True

    def pop(self) -> Optional[ModeSnapshot]:
        if not self._stack:
            return None

        current = self._stack.pop()
        definition = self._definitions.get(current.mode_name)
        if definition and definition.transition_out_time > 0:
            self._transition_from = current.mode_name

        self._fire_exit_hooks(current.mode_name, current)

        if self._stack:
            new_current = self._stack[-1]
            self._fire_enter_hooks(new_current.mode_name, new_current)

        self._mode_change_count += 1
        return current

    def replace(self, mode_name: str, config: Optional[Dict[str, Any]] = None) -> bool:
        self.pop()
        return self.push(mode_name, config=config)

    def switch(self, from_mode: str, to_mode: str, config: Optional[Dict[str, Any]] = None) -> bool:
        current = self.get_current()
        if not current or current.mode_name != from_mode:
            return False
        self.pop()
        return self.push(to_mode, config=config)

    def get_current(self) -> Optional[ModeSnapshot]:
        return self._stack[-1] if self._stack else None

    def get_mode_stack(self) -> List[ModeSnapshot]:
        return list(self._stack)

    def get_stack_names(self) -> List[str]:
        return [s.mode_name for s in self._stack]

    def has_mode(self, mode_name: str) -> bool:
        return any(s.mode_name == mode_name for s in self._stack)

    def get_mode_definition(self, mode_name: str) -> Optional[ModeDefinition]:
        return self._definitions.get(mode_name)

    def can_transition(self, mode_name: str) -> bool:
        definition = self._definitions.get(mode_name)
        if definition is None:
            return False
        for existing in self._stack:
            existing_def = self._definitions.get(existing.mode_name)
            if existing_def and existing_def.layer == ModeLayer.MODAL:
                return False
        return True

    def update(self, dt: float) -> None:
        for snapshot in self._stack:
            snapshot.elapsed += dt

        if self._current_transition == TransitionPhase.EXITING:
            elapsed = time.time() - self._transition_start
            if self._transition_from:
                definition = self._definitions.get(self._transition_from)
                if definition:
                    if elapsed >= definition.transition_out_time:
                        self._current_transition = TransitionPhase.NONE
                        self._transition_from = None

        elif self._current_transition == TransitionPhase.ENTERING:
            elapsed = time.time() - self._transition_start
            if self._transition_to:
                definition = self._definitions.get(self._transition_to)
                if definition:
                    if elapsed >= definition.transition_in_time:
                        self._current_transition = TransitionPhase.NONE
                        self._transition_to = None

    def is_transitioning(self) -> bool:
        return self._current_transition != TransitionPhase.NONE

    def _fire_enter_hooks(self, mode_name: str, snapshot: ModeSnapshot) -> None:
        hooks = self._enter_hooks.get(mode_name, [])
        hooks.extend(self._enter_hooks.get("*", []))
        for hook in hooks:
            try:
                hook(snapshot)
            except Exception:
                pass

    def _fire_exit_hooks(self, mode_name: str, snapshot: ModeSnapshot) -> None:
        hooks = self._exit_hooks.get(mode_name, [])
        hooks.extend(self._exit_hooks.get("*", []))
        for hook in hooks:
            try:
                hook(snapshot)
            except Exception:
                pass

    def _fire_transition_hooks(self, from_mode: str, to_mode: str) -> None:
        key = f"{from_mode}->{to_mode}"
        wildcard = f"*->{to_mode}"
        hooks = self._transition_hooks.get(key, [])
        hooks.extend(self._transition_hooks.get(wildcard, []))
        for hook in hooks:
            try:
                hook(from_mode, to_mode)
            except Exception:
                pass

    def get_stats(self) -> Dict[str, Any]:
        stack = self.get_stack_names()
        return {
            "current_mode": stack[-1] if stack else None,
            "stack": stack,
            "stack_depth": len(self._stack),
            "transitioning": self.is_transitioning(),
            "registered_modes": len(self._definitions),
            "mode_change_count": self._mode_change_count,
        }


def get_game_mode_system() -> GameModeSystem:
    return GameModeSystem.get_instance()