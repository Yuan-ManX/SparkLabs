"""
Engine Game Loop - Core game loop with fixed timestep update and variable rendering.
Provides deterministic simulation, frame timing, and update scheduling
for the SparkLabs AI-native game engine.
"""

import threading
import time as _time_module
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Any, Callable


class LoopState(Enum):
    """States of the game loop."""
    STOPPED = "stopped"
    RUNNING = "running"
    PAUSED = "paused"
    STEPPING = "stepping"


@dataclass
class FrameTiming:
    """Timing information for a single frame."""
    frame_id: int = 0
    delta_time: float = 0.0
    fixed_delta_time: float = 0.016
    total_time: float = 0.0
    fps: float = 0.0
    update_time: float = 0.0
    render_time: float = 0.0
    fixed_updates: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "frame_id": self.frame_id,
            "delta_time": self.delta_time,
            "fixed_delta_time": self.fixed_delta_time,
            "total_time": self.total_time,
            "fps": self.fps,
            "update_time": self.update_time,
            "render_time": self.render_time,
            "fixed_updates": self.fixed_updates,
        }


@dataclass
class UpdateLayer:
    """An update layer with specific priority and fixed timestep."""
    layer_id: int = 0
    name: str = ""
    priority: int = 0
    fixed_timestep: float = 0.016
    accumulator: float = 0.0
    is_active: bool = True


class EngineGameLoop:
    """
    Core game loop system for the SparkLabs game engine.
    Implements fixed timestep game loop with variable rendering,
    update layers, and performance monitoring.
    """

    _instance = None
    _lock = threading.RLock()
    _initialized = False

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if not self._initialized:
            self._state: LoopState = LoopState.STOPPED
            self._frame_timing = FrameTiming()
            self._update_layers: Dict[int, UpdateLayer] = {}
            self._update_callbacks: Dict[int, List[Callable[[float], None]]] = {}
            self._render_callbacks: List[Callable[[float], None]] = []
            self._fixed_update_callbacks: Dict[int, List[Callable[[float], None]]] = {}
            self._start_callbacks: List[Callable[[], None]] = []
            self._stop_callbacks: List[Callable[[], None]] = []
            self._frame_count: int = 0
            self._start_time: float = 0.0
            self._last_frame_time: float = 0.0
            self._fps_samples: List[float] = []
            self._max_fps: int = 60
            self._target_frame_time: float = 1.0 / 60.0
            self._initialized = True

    @classmethod
    def get_instance(cls) -> 'EngineGameLoop':
        return cls()

    def create_update_layer(self, name: str, priority: int = 0,
                            fixed_timestep: float = 0.016) -> UpdateLayer:
        """Create an update layer with specific priority."""
        layer = UpdateLayer(
            layer_id=priority,
            name=name,
            priority=priority,
            fixed_timestep=fixed_timestep,
        )
        self._update_layers[priority] = layer
        self._update_callbacks[priority] = []
        self._fixed_update_callbacks[priority] = []
        return layer

    def on_update(self, callback: Callable[[float], None], layer: int = 0):
        """Register a variable update callback."""
        self._update_callbacks.setdefault(layer, []).append(callback)

    def on_fixed_update(self, callback: Callable[[float], None], layer: int = 0):
        """Register a fixed timestep update callback."""
        self._fixed_update_callbacks.setdefault(layer, []).append(callback)

    def on_render(self, callback: Callable[[float], None]):
        """Register a render callback."""
        self._render_callbacks.append(callback)

    def on_start(self, callback: Callable[[], None]):
        """Register a callback for loop start."""
        self._start_callbacks.append(callback)

    def on_stop(self, callback: Callable[[], None]):
        """Register a callback for loop stop."""
        self._stop_callbacks.append(callback)

    def start(self):
        """Start the game loop."""
        self._state = LoopState.RUNNING
        self._start_time = _time_module.time()
        self._last_frame_time = self._start_time
        self._frame_count = 0

        for callback in self._start_callbacks:
            callback()

    def stop(self):
        """Stop the game loop."""
        self._state = LoopState.STOPPED
        for callback in self._stop_callbacks:
            callback()

    def pause(self):
        """Pause the game loop."""
        if self._state == LoopState.RUNNING:
            self._state = LoopState.PAUSED

    def resume(self):
        """Resume the game loop."""
        if self._state == LoopState.PAUSED:
            self._state = LoopState.RUNNING

    def step(self):
        """Perform a single step of the game loop."""
        self._state = LoopState.STEPPING
        self._tick()
        self._state = LoopState.PAUSED

    def set_max_fps(self, max_fps: int):
        """Set the maximum frames per second."""
        self._max_fps = max_fps
        self._target_frame_time = 1.0 / max_fps

    def _tick(self):
        """Execute one tick of the game loop."""
        current_time = _time_module.time()
        frame_delta = current_time - self._last_frame_time
        self._last_frame_time = current_time

        if frame_delta > 0.25:
            frame_delta = 0.25

        total_time = current_time - self._start_time

        self._frame_count += 1
        self._fps_samples.append(1.0 / max(frame_delta, 0.0001))
        if len(self._fps_samples) > 60:
            self._fps_samples = self._fps_samples[-30:]

        update_start = _time_module.time()

        sorted_layers = sorted(self._update_layers.items(), key=lambda x: x[1].priority)
        fixed_updates = 0

        for priority, layer in sorted_layers:
            if not layer.is_active:
                continue

            layer.accumulator += frame_delta

            while layer.accumulator >= layer.fixed_timestep:
                layer.accumulator -= layer.fixed_timestep
                fixed_updates += 1

                for callback in self._fixed_update_callbacks.get(priority, []):
                    callback(layer.fixed_timestep)

            for callback in self._update_callbacks.get(priority, []):
                callback(frame_delta)

        update_end = _time_module.time()

        render_start = _time_module.time()
        for callback in self._render_callbacks:
            callback(frame_delta)
        render_end = _time_module.time()

        self._frame_timing = FrameTiming(
            frame_id=self._frame_count,
            delta_time=frame_delta,
            fixed_delta_time=0.016,
            total_time=total_time,
            fps=sum(self._fps_samples) / len(self._fps_samples) if self._fps_samples else 0.0,
            update_time=update_end - update_start,
            render_time=render_end - render_start,
            fixed_updates=fixed_updates,
        )

    def run_frame(self):
        """Run a single frame of the game loop."""
        if self._state == LoopState.RUNNING or self._state == LoopState.STEPPING:
            self._tick()

    def get_frame_timing(self) -> FrameTiming:
        """Get current frame timing information."""
        return self._frame_timing

    def get_fps(self) -> float:
        """Get current FPS."""
        if not self._fps_samples:
            return 0.0
        return sum(self._fps_samples) / len(self._fps_samples)

    def get_state(self) -> LoopState:
        """Get current loop state."""
        return self._state

    def get_stats(self) -> Dict[str, Any]:
        """Get game loop statistics."""
        return {
            "state": self._state.value,
            "frame_count": self._frame_count,
            "fps": self.get_fps(),
            "total_time": _time_module.time() - self._start_time if self._start_time > 0 else 0.0,
            "delta_time": self._frame_timing.delta_time,
            "update_layers": len(self._update_layers),
            "total_callbacks": sum(len(c) for c in self._update_callbacks.values()) + len(self._render_callbacks),
            "fixed_updates": self._frame_timing.fixed_updates,
        }


def get_game_loop() -> EngineGameLoop:
    return EngineGameLoop.get_instance()