"""
SparkAI Engine - Frame Timer System

Precision frame timing and pacing system for game loop
synchronization. Provides high-resolution delta time calculation,
frame rate smoothing, fixed timestep accumulation, and performance
profiling with min/max/avg frame time tracking.

Supports adaptive frame pacing, VSync emulation, and configurable
target frame rates for consistent game simulation across hardware.
"""

from __future__ import annotations

import threading
import time as _time_module
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class FramePacingMode(str, Enum):
    UNLIMITED = "unlimited"
    FIXED = "fixed"
    ADAPTIVE = "adaptive"
    VSYNC = "vsync"


class TimerState(str, Enum):
    STOPPED = "stopped"
    RUNNING = "running"
    PAUSED = "paused"
    THROTTLED = "throttled"


# ---------------------------------------------------------------------------
# Data Classes
# ---------------------------------------------------------------------------

@dataclass
class FrameSnapshot:
    """A single frame timing snapshot."""
    snapshot_id: int = 0
    frame_number: int = 0
    delta_time: float = 0.0
    elapsed_time: float = 0.0
    frame_start: float = 0.0
    frame_end: float = 0.0
    sleep_time: float = 0.0
    accumulator: float = 0.0
    is_fixed_update: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "frame_number": self.frame_number,
            "delta_time_ms": round(self.delta_time * 1000, 3),
            "elapsed_time_s": round(self.elapsed_time, 3),
            "fps": round(1.0 / max(self.delta_time, 0.0001), 1),
            "sleep_time_ms": round(self.sleep_time * 1000, 3),
            "is_fixed_update": self.is_fixed_update,
        }


@dataclass
class FrameTimingStats:
    """Aggregated frame timing statistics."""
    stats_id: int = 0
    total_frames: int = 0
    total_fixed_updates: int = 0
    min_delta_s: float = float("inf")
    max_delta_s: float = 0.0
    avg_delta_s: float = 0.0
    min_fps: float = float("inf")
    max_fps: float = 0.0
    avg_fps: float = 0.0
    total_elapsed_s: float = 0.0
    sleep_overhead_pct: float = 0.0
    frame_drops: int = 0
    jitter_ms: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        def safe_round(val: float, n: int) -> Any:
            if val == float("inf") or val == float("-inf"):
                return None
            return round(val, n)

        return {
            "total_frames": self.total_frames,
            "total_fixed_updates": self.total_fixed_updates,
            "min_delta_ms": safe_round(self.min_delta_s * 1000, 3),
            "max_delta_ms": round(self.max_delta_s * 1000, 3),
            "avg_delta_ms": round(self.avg_delta_s * 1000, 3),
            "min_fps": safe_round(self.min_fps, 1),
            "max_fps": round(self.max_fps, 1),
            "avg_fps": round(self.avg_fps, 1),
            "total_elapsed_s": round(self.total_elapsed_s, 3),
            "sleep_overhead_pct": round(self.sleep_overhead_pct, 2),
            "frame_drops": self.frame_drops,
            "jitter_ms": round(self.jitter_ms, 3),
        }


# ---------------------------------------------------------------------------
# Frame Timer
# ---------------------------------------------------------------------------

class EngineFrameTimer:
    """
    High-precision frame timer for game loop synchronization.

    Manages delta time calculation, fixed timestep accumulation,
    frame pacing, and comprehensive performance profiling across
    the entire game loop lifecycle.
    """

    _instance: Optional["EngineFrameTimer"] = None
    _lock = threading.RLock()

    def __new__(cls) -> "EngineFrameTimer":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    @classmethod
    def get_instance(cls) -> "EngineFrameTimer":
        if cls._instance is None:
            cls._instance = cls()
            cls._instance._initialize()
        return cls._instance

    def _initialize(self) -> None:
        if self._initialized:
            return
        self._initialized = True
        self._state: TimerState = TimerState.STOPPED
        self._pacing_mode: FramePacingMode = FramePacingMode.FIXED
        self._target_fps: int = 60
        self._target_frame_time: float = 1.0 / 60.0
        self._fixed_timestep: float = 1.0 / 60.0
        self._accumulator: float = 0.0
        self._max_accumulator: float = 0.2  # 200ms max accumulation
        self._frame_count: int = 0
        self._fixed_update_count: int = 0
        self._total_elapsed: float = 0.0
        self._last_frame_time: float = 0.0
        self._start_time: float = 0.0
        self._pause_time: float = 0.0
        self._total_paused: float = 0.0
        self._history: List[FrameSnapshot] = []
        self._max_history: int = 3600  # 1 minute at 60fps
        self._delta_samples: List[float] = []
        self._max_delta_samples: int = 600
        self._sleep_per_frame: float = 0.0
        self._total_sleep: float = 0.0

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def start(self) -> bool:
        """Start the frame timer."""
        with self._lock:
            if self._state == TimerState.RUNNING:
                return False
            self._state = TimerState.RUNNING
            self._start_time = _time_module.perf_counter()
            self._last_frame_time = self._start_time
            self._frame_count = 0
            self._total_elapsed = 0.0
            return True

    def stop(self) -> bool:
        """Stop the frame timer."""
        with self._lock:
            self._state = TimerState.STOPPED
            return True

    def pause(self) -> bool:
        """Pause the frame timer."""
        with self._lock:
            if self._state != TimerState.RUNNING:
                return False
            self._state = TimerState.PAUSED
            self._pause_time = _time_module.perf_counter()
            return True

    def resume(self) -> bool:
        """Resume the frame timer from paused state."""
        with self._lock:
            if self._state != TimerState.PAUSED:
                return False
            self._state = TimerState.RUNNING
            self._total_paused += _time_module.perf_counter() - self._pause_time
            return True

    # ------------------------------------------------------------------
    # Frame Timing
    # ------------------------------------------------------------------

    def tick(self) -> FrameSnapshot:
        """
        Advance one frame and return the frame snapshot.

        Calculates delta time, handles frame pacing, and accumulates
        time for fixed-step updates.
        """
        with self._lock:
            if self._state != TimerState.RUNNING:
                return FrameSnapshot()

            self._frame_count += 1
            frame_start = _time_module.perf_counter()

            # Calculate delta time
            delta = frame_start - self._last_frame_time
            self._last_frame_time = frame_start

            # Clamp delta to avoid spiral of death
            delta = min(delta, self._max_accumulator)

            # Frame pacing
            sleep_time = 0.0
            if self._pacing_mode in (FramePacingMode.FIXED, FramePacingMode.ADAPTIVE):
                sleep_time = max(0, self._target_frame_time - delta)
                if sleep_time > 0:
                    # Simulated sleep (in real engine, this would be actual sleep)
                    self._total_sleep += sleep_time

            # Accumulate for fixed timestep
            self._accumulator += delta
            is_fixed = False
            if self._accumulator >= self._fixed_timestep:
                self._accumulator = min(self._accumulator, self._max_accumulator)
                is_fixed = True
                self._fixed_update_count += 1

            self._total_elapsed += delta

            snapshot = FrameSnapshot(
                snapshot_id=self._frame_count,
                frame_number=self._frame_count,
                delta_time=delta,
                elapsed_time=self._total_elapsed,
                frame_start=frame_start,
                frame_end=frame_start + sleep_time,
                sleep_time=sleep_time,
                accumulator=self._accumulator,
                is_fixed_update=is_fixed,
            )

            # Track history
            self._history.append(snapshot)
            if len(self._history) > self._max_history:
                self._history = self._history[-self._max_history:]

            # Track delta samples for stats
            self._delta_samples.append(delta)
            if len(self._delta_samples) > self._max_delta_samples:
                self._delta_samples = self._delta_samples[-self._max_delta_samples:]

            return snapshot

    def consume_fixed_accumulator(self) -> Tuple[bool, float]:
        """Consume one fixed timestep from the accumulator."""
        with self._lock:
            if self._accumulator >= self._fixed_timestep:
                self._accumulator -= self._fixed_timestep
                return True, self._fixed_timestep
            return False, 0.0

    # ------------------------------------------------------------------
    # Configuration
    # ------------------------------------------------------------------

    def set_target_fps(self, fps: int) -> None:
        """Set the target frame rate."""
        with self._lock:
            self._target_fps = max(1, min(fps, 360))
            self._target_frame_time = 1.0 / self._target_fps

    def set_fixed_timestep(self, timestep: float) -> None:
        """Set the fixed update timestep in seconds."""
        with self._lock:
            self._fixed_timestep = max(0.001, min(timestep, 0.1))

    def set_pacing_mode(self, mode: FramePacingMode) -> None:
        """Set the frame pacing mode."""
        with self._lock:
            self._pacing_mode = mode

    # ------------------------------------------------------------------
    # Statistics
    # ------------------------------------------------------------------

    def get_stats(self) -> FrameTimingStats:
        """Get aggregated frame timing statistics."""
        with self._lock:
            samples = self._delta_samples
            if not samples:
                return FrameTimingStats()

            avg_delta = sum(samples) / len(samples)
            jitter = 0.0
            if len(samples) > 1:
                diffs = [abs(samples[i] - samples[i - 1]) for i in range(1, len(samples))]
                jitter = sum(diffs) / len(diffs)
            drops = sum(1 for d in samples if d > self._target_frame_time * 1.5)

            return FrameTimingStats(
                total_frames=self._frame_count,
                total_fixed_updates=self._fixed_update_count,
                min_delta_s=min(samples) if samples else 0,
                max_delta_s=max(samples) if samples else 0,
                avg_delta_s=avg_delta,
                min_fps=1.0 / max(max(samples), 0.0001) if samples else 0,
                max_fps=1.0 / max(min(samples), 0.0001) if samples else 0,
                avg_fps=1.0 / max(avg_delta, 0.0001),
                total_elapsed_s=self._total_elapsed,
                sleep_overhead_pct=(self._total_sleep / max(self._total_elapsed, 0.0001)) * 100,
                frame_drops=drops,
                jitter_ms=jitter * 1000,
            )

    def get_current_state(self) -> Dict[str, Any]:
        """Get the current timer state."""
        with self._lock:
            return {
                "state": self._state.value,
                "pacing_mode": self._pacing_mode.value,
                "target_fps": self._target_fps,
                "target_frame_time_ms": round(self._target_frame_time * 1000, 3),
                "fixed_timestep_ms": round(self._fixed_timestep * 1000, 3),
                "frame_count": self._frame_count,
                "fixed_updates": self._fixed_update_count,
                "accumulator_ms": round(self._accumulator * 1000, 3),
                "total_elapsed_s": round(self._total_elapsed, 3),
                "total_paused_s": round(self._total_paused, 3),
            }

    def get_recent_history(self, count: int = 60) -> List[Dict[str, Any]]:
        """Get recent frame timing history."""
        with self._lock:
            recent = self._history[-count:]
            return [s.to_dict() for s in recent]

    def simulate_frames(self, num_frames: int = 60) -> List[FrameSnapshot]:
        """Simulate a number of frames for testing."""
        with self._lock:
            if self._state != TimerState.RUNNING:
                self.start()
            snapshots: List[FrameSnapshot] = []
            for _ in range(num_frames):
                snap = self.tick()
                snapshots.append(snap)
            return snapshots


# ---------------------------------------------------------------------------
# Module-level accessor
# ---------------------------------------------------------------------------

def get_frame_timer() -> EngineFrameTimer:
    return EngineFrameTimer.get_instance()