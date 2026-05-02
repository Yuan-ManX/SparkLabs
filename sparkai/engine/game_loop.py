"""
SparkLabs Engine - Game Loop

Core game loop with time management, frame stepping, and execution
phases. Drives the simulation with configurable time scaling and
fixed/variable timestep support. Orchestrates the processing order:
input gathering, behavior updates, physics, rendering, and AI.

Architecture:
  GameLoop
    |-- TimeManager (delta time, time scale, fixed step)
    |-- ExecutionPhases (ordered processing stages)
    |-- FrameStats (FPS, frame time, draw calls)
    |-- LifecycleHooks (start/stop/pause/resume/single-step)

Execution Phases (ordered per frame):
  1. INPUT    - gather input events
  2. PRE_STEP - pre-behavior processing
  3. STEP     - main behavior/physics tick
  4. POST_STEP- post-behavior processing
  5. RENDER   - render to display buffers
  6. AI       - agent observation/decision
  7. CLEANUP  - garbage collection, event cleanup
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from enum import Enum, auto
from typing import Any, Callable, Dict, List, Optional


class ExecutionPhase(Enum):
    INPUT = auto()
    PRE_STEP = auto()
    STEP = auto()
    POST_STEP = auto()
    RENDER = auto()
    AI = auto()
    CLEANUP = auto()


@dataclass
class FrameStats:
    fps: float = 60.0
    delta_time: float = 0.016
    frame_count: int = 0
    total_time: float = 0.0
    target_fps: int = 60
    smoothed_fps: float = 60.0
    frame_times: List[float] = None

    def __post_init__(self):
        if self.frame_times is None:
            self.frame_times = []

    def record_frame_time(self, dt: float) -> None:
        self.frame_times.append(dt)
        if len(self.frame_times) > 60:
            self.frame_times.pop(0)

    def update(self, dt: float, now: float) -> None:
        self.delta_time = dt
        self.frame_count += 1
        self.total_time += dt
        self.record_frame_time(dt)
        if self.frame_times:
            avg_dt = sum(self.frame_times) / len(self.frame_times)
            self.smoothed_fps = 1.0 / max(avg_dt, 0.001)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "fps": round(self.smoothed_fps, 1),
            "delta_time": round(self.delta_time, 4),
            "frame_count": self.frame_count,
            "total_time": round(self.total_time, 2),
            "target_fps": self.target_fps,
        }


@dataclass
class LoopConfig:
    target_fps: int = 60
    max_delta_time: float = 0.1
    time_scale: float = 1.0
    use_fixed_timestep: bool = False
    fixed_timestep: float = 0.016
    max_frame_skip: int = 5
    auto_sleep: bool = False
    sleep_threshold_frames: int = 300
    emit_stats_interval: float = 1.0


class TimeManager:
    """
    Game time controller with scaling and fixed-timestep support.

    Manages delta time calculation, time scaling for slow-motion
    or fast-forward effects, and fixed-timestep accumulation
    for deterministic physics simulation.
    """

    def __init__(self, config: Optional[LoopConfig] = None):
        self._config = config or LoopConfig()
        self._time_scale: float = self._config.time_scale
        self._last_time: float = 0.0
        self._accumulator: float = 0.0
        self._started: bool = False

    @property
    def time_scale(self) -> float:
        return self._time_scale

    @time_scale.setter
    def time_scale(self, value: float) -> None:
        self._time_scale = max(0.0, min(value, 10.0))

    def start(self) -> None:
        self._last_time = time.time()
        self._accumulator = 0.0
        self._started = True

    def stop(self) -> None:
        self._started = False

    def get_scaled_delta(self) -> float:
        if not self._started:
            return 0.0
        now = time.time()
        raw_dt = now - self._last_time
        self._last_time = now
        scaled = raw_dt * self._time_scale
        return min(scaled, self._config.max_delta_time)

    def get_fixed_updates(self, delta: float) -> int:
        self._accumulator += delta
        updates = 0
        fixed = self._config.fixed_timestep
        while self._accumulator >= fixed and updates < self._config.max_frame_skip:
            self._accumulator -= fixed
            updates += 1
        return updates

    def pause(self) -> None:
        self._started = False

    def resume(self) -> None:
        self._last_time = time.time()
        self._started = True


class GameLoop:
    """
    Core game simulation loop.

    Drives the engine frame by frame with ordered execution phases.
    Supports variable and fixed timestep modes, time scaling,
    auto-sleep when idle, and detailed frame statistics.

    Usage:
        loop = GameLoop()
        loop.register_phase_handler(ExecutionPhase.STEP, my_step_handler)

        def my_game():
            while loop.running:
                loop.tick()

        # Run in background with controlled FPS
        loop.run_in_thread(target_fps=60)

    Phase handlers receive (delta_time: float, frame_stats: FrameStats).
    """

    def __init__(self, config: Optional[LoopConfig] = None):
        self._config = config or LoopConfig()
        self._time_manager = TimeManager(self._config)
        self._stats = FrameStats(target_fps=self._config.target_fps)
        self._running: bool = False
        self._paused: bool = False
        self._idle_frames: int = 0
        self._last_stats_emit: float = 0.0
        self._handlers: Dict[ExecutionPhase, List[Callable]] = {
            phase: [] for phase in ExecutionPhase
        }
        self._tick_callbacks: List[Callable] = []
        self._frame_boundaries: List[Callable] = []

    @property
    def running(self) -> bool:
        return self._running

    @property
    def paused(self) -> bool:
        return self._paused

    @property
    def stats(self) -> FrameStats:
        return self._stats

    @property
    def time_manager(self) -> TimeManager:
        return self._time_manager

    def register_phase_handler(self, phase: ExecutionPhase, handler: Callable[[float, FrameStats], None]) -> None:
        self._handlers[phase].append(handler)

    def register_tick_callback(self, callback: Callable[[float], None]) -> None:
        self._tick_callbacks.append(callback)

    def register_frame_boundary(self, callback: Callable[[int], None]) -> None:
        self._frame_boundaries.append(callback)

    def start(self) -> None:
        self._running = True
        self._paused = False
        self._time_manager.start()
        for handler in self._handlers.get(ExecutionPhase.INPUT, []):
            handler(0.0, self._stats)

    def stop(self) -> None:
        self._running = False
        self._time_manager.stop()

    def pause(self) -> None:
        self._paused = True
        self._time_manager.pause()

    def resume(self) -> None:
        self._paused = False
        self._time_manager.resume()

    def single_step(self) -> None:
        dt = self._config.fixed_timestep
        self._execute_frame(dt)

    def tick(self) -> Optional[FrameStats]:
        if not self._running:
            return None
        if self._paused:
            return None

        dt = self._time_manager.get_scaled_delta()
        if dt <= 0.0:
            return None

        if self._config.use_fixed_timestep:
            updates = self._time_manager.get_fixed_updates(dt)
            for _ in range(updates):
                self._execute_frame(self._config.fixed_timestep)
        else:
            self._execute_frame(dt)

        if self._config.auto_sleep:
            if dt < 0.001:
                self._idle_frames += 1
            else:
                self._idle_frames = 0
            if self._idle_frames >= self._config.sleep_threshold_frames:
                time.sleep(0.05)

        return self._stats

    def _execute_frame(self, dt: float) -> None:
        now = time.time()
        self._stats.update(dt, now)

        for callback in self._tick_callbacks:
            callback(dt)

        for phase in ExecutionPhase:
            for handler in self._handlers.get(phase, []):
                handler(dt, self._stats)

        for callback in self._frame_boundaries:
            callback(self._stats.frame_count)

        if now - self._last_stats_emit >= self._config.emit_stats_interval:
            self._last_stats_emit = now

    def run_forever(self, target_fps: Optional[int] = None) -> None:
        target_fps = target_fps or self._config.target_fps
        frame_duration = 1.0 / target_fps
        self.start()
        try:
            while self._running:
                frame_start = time.time()
                self.tick()
                elapsed = time.time() - frame_start
                sleep_time = frame_duration - elapsed
                if sleep_time > 0.001:
                    time.sleep(sleep_time)
        except KeyboardInterrupt:
            self.stop()

    def get_statistics(self) -> Dict[str, Any]:
        return self._stats.to_dict()


_global_game_loop: Optional[GameLoop] = None


def get_game_loop() -> GameLoop:
    global _global_game_loop
    if _global_game_loop is None:
        _global_game_loop = GameLoop()
    return _global_game_loop
