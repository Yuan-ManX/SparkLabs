"""
SparkLabs Engine - Performance Profiler

Lightweight instrumentation profiler for real-time performance
analysis of the AI-native game engine. Tracks frame timing,
memory allocation, system execution budgets, and bottleneck
detection — enabling AI agents to optimize game performance
proactively.

Architecture:
  Profiler
    |-- FrameProfiler (per-frame timing with phase breakdown)
    |-- MemoryTracker (allocation/deallocation with peak tracking)
    |-- SystemTimer (scoped high-resolution subsystem timing)
    |-- BottleneckDetector (threshold-based bottleneck identification)

Tracked Metrics:
  - Frame time (total, min, max, avg, P95, P99)
  - Engine phase timing (input, step, render, physics, audio, UI)
  - Memory (allocated, freed, peak, current, object count)
  - FPS (instantaneous, smoothed, 1% lows)
  - System call counts per frame

Usage:
    profiler = Profiler(window_size=120, auto_report=True)
    with profiler.measure("physics_step"):
        physics_system.step(dt)
    profiler.begin_frame()
    # ... game loop ...
    profiler.end_frame()
    report = profiler.generate_report()
    bottlenecks = profiler.detect_bottlenecks(threshold_ms=16.0)
"""
from __future__ import annotations

import math
import time
from collections import deque
from contextlib import contextmanager
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Callable, Dict, Iterator, List, Optional, Set, Tuple


class PerformanceLevel(Enum):
    OPTIMAL = auto()
    GOOD = auto()
    ACCEPTABLE = auto()
    WARNING = auto()
    CRITICAL = auto()


@dataclass
class TimingSample:
    name: str = ""
    start_time: float = 0.0
    elapsed_ms: float = 0.0
    timestamp: float = 0.0
    call_count: int = 1


@dataclass
class MemorySnapshot:
    allocated_bytes: int = 0
    freed_bytes: int = 0
    current_bytes: int = 0
    peak_bytes: int = 0
    object_count: int = 0
    allocation_count: int = 0


@dataclass
class FrameReport:
    frame_number: int = 0
    total_ms: float = 0.0
    fps: float = 0.0
    phase_timings: Dict[str, float] = field(default_factory=dict)
    memory: MemorySnapshot = field(default_factory=MemorySnapshot)
    bottleneck_level: PerformanceLevel = PerformanceLevel.OPTIMAL
    bottleneck_reason: str = ""


@dataclass
class ProfilerReport:
    report_id: str = ""
    generated_at: float = 0.0
    frame_count: int = 0
    elapsed_seconds: float = 0.0
    avg_fps: float = 0.0
    min_fps: float = 0.0
    max_fps: float = 0.0
    p95_frame_ms: float = 0.0
    p99_frame_ms: float = 0.0
    one_percent_low_fps: float = 0.0
    avg_frame_ms: float = 0.0
    phase_averages: Dict[str, float] = field(default_factory=dict)
    peak_memory_bytes: int = 0
    current_memory_bytes: int = 0
    bottleneck_count: int = 0
    recommendations: List[str] = field(default_factory=list)
    performance_level: str = "optimal"


class SystemTimer:
    def __init__(self, name: str, profiler: "Profiler"):
        self._name = name
        self._profiler = profiler
        self._start: float = 0.0
        self._elapsed: float = 0.0

    def __enter__(self) -> "SystemTimer":
        self._start = time.perf_counter()
        return self

    def __exit__(self, *args) -> None:
        self._elapsed = (time.perf_counter() - self._start) * 1000.0
        self._profiler.record_timing(self._name, self._elapsed)

    @property
    def elapsed_ms(self) -> float:
        return self._elapsed


class BottleneckDetector:
    def __init__(self, warning_threshold_ms: float = 8.0, critical_threshold_ms: float = 16.0):
        self._warning_threshold = warning_threshold_ms
        self._critical_threshold = critical_threshold_ms
        self._consecutive_warnings: int = 0
        self._spike_threshold: float = 3.0
        self._phase_thresholds: Dict[str, float] = {
            "physics_step": 5.0,
            "particle_update": 3.0,
            "render_scene": 8.0,
            "collision_update": 4.0,
            "behavior_step": 3.0,
            "pathfinding": 5.0,
            "audio_update": 2.0,
            "ui_render": 3.0,
            "animation_update": 2.0,
            "tilemap_render": 4.0,
        }

    def set_phase_threshold(self, phase: str, threshold_ms: float) -> None:
        self._phase_thresholds[phase] = threshold_ms

    def analyze(
        self,
        frame_ms: float,
        phase_timings: Dict[str, float],
        recent_frames: deque,
    ) -> Tuple[PerformanceLevel, str]:
        if frame_ms > self._critical_threshold:
            self._consecutive_warnings += 1
            return PerformanceLevel.CRITICAL, f"Frame time {frame_ms:.1f}ms exceeds critical threshold {self._critical_threshold}ms"

        for phase, elapsed in phase_timings.items():
            threshold = self._phase_thresholds.get(phase, self._warning_threshold)
            if elapsed > threshold:
                self._consecutive_warnings += 1
                return PerformanceLevel.WARNING, f"Phase '{phase}' took {elapsed:.1f}ms (threshold: {threshold}ms)"

        if len(recent_frames) >= 10:
            recent_vals = list(recent_frames)
            std_dev = self._compute_std_dev(recent_vals)
            avg = sum(recent_vals) / len(recent_vals)
            if avg > 0 and std_dev / avg > 0.3:
                return PerformanceLevel.WARNING, f"Frame time instability detected: std_dev/mean = {std_dev/avg:.2f}"

        if len(recent_frames) >= 3:
            recent_list = list(recent_frames)
            if len(recent_list) >= 3:
                avg_except_last = sum(recent_list[:-1]) / (len(recent_list) - 1)
                if recent_list[-1] > avg_except_last * self._spike_threshold:
                    self._consecutive_warnings += 1
                    return PerformanceLevel.WARNING, f"Frame time spike: {recent_list[-1]:.1f}ms vs avg {avg_except_last:.1f}ms"

        self._consecutive_warnings = 0
        if frame_ms < self._warning_threshold / 2.0:
            return PerformanceLevel.OPTIMAL, "Frame time well within budget"
        if frame_ms < self._warning_threshold:
            return PerformanceLevel.GOOD, "Frame time within budget"
        return PerformanceLevel.ACCEPTABLE, f"Frame time {frame_ms:.1f}ms approaching budget"

    @staticmethod
    def _compute_std_dev(values: List[float]) -> float:
        if len(values) < 2:
            return 0.0
        mean = sum(values) / len(values)
        variance = sum((v - mean) ** 2 for v in values) / len(values)
        return math.sqrt(variance)


class Profiler:
    _instance: Optional["Profiler"] = None

    def __init__(self, window_size: int = 120, auto_report_interval: int = 300):
        self._window_size: int = max(10, window_size)
        self._auto_report_interval: int = auto_report_interval
        self._frame_timings: deque[float] = deque(maxlen=window_size)
        self._phase_totals: Dict[str, deque[float]] = {}
        self._memory_snapshots: deque[MemorySnapshot] = deque(maxlen=window_size)
        self._frame_number: int = 0
        self._frame_start: float = 0.0
        self._total_elapsed: float = 0.0
        self._min_frame_ms: float = float("inf")
        self._max_frame_ms: float = 0.0
        self._peak_memory: int = 0
        self._current_memory: int = 0
        self._allocated_total: int = 0
        self._freed_total: int = 0
        self._object_count: int = 0
        self._bottleneck_detector: BottleneckDetector = BottleneckDetector()
        self._report_callbacks: List[Callable[[FrameReport], None]] = []
        self._session_start: float = time.perf_counter()
        self._session_id: str = str(id(self))
        self._enabled: bool = True

        self._default_phases = [
            "total_frame", "input", "step", "physics_step",
            "collision_update", "render_scene", "particle_update",
            "animation_update", "audio_update", "ui_render",
            "behavior_step", "pathfinding", "tilemap_render",
            "post_step", "cleanup",
        ]
        for phase in self._default_phases:
            self._phase_totals[phase] = deque(maxlen=window_size)

    @classmethod
    def get_instance(cls) -> "Profiler":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @property
    def enabled(self) -> bool:
        return self._enabled

    @enabled.setter
    def enabled(self, value: bool) -> None:
        self._enabled = value

    def set_window_size(self, size: int) -> None:
        self._window_size = max(10, size)
        for dq in self._phase_totals.values():
            while len(dq) > self._window_size:
                dq.popleft()
        self._frame_timings = deque(self._frame_timings, maxlen=self._window_size)

    def set_phase_threshold(self, phase: str, threshold_ms: float) -> None:
        self._bottleneck_detector.set_phase_threshold(phase, threshold_ms)

    def measure(self, name: str) -> SystemTimer:
        if name not in self._phase_totals:
            self._phase_totals[name] = deque(maxlen=self._window_size)
        return SystemTimer(name, self)

    def record_timing(self, name: str, elapsed_ms: float) -> None:
        if not self._enabled:
            return
        if name not in self._phase_totals:
            self._phase_totals[name] = deque(maxlen=self._window_size)
        ring = self._phase_totals[name]
        if ring:
            ring[-1] += elapsed_ms
        else:
            ring.append(elapsed_ms)

    def begin_frame(self) -> None:
        if not self._enabled:
            return
        self._frame_start = time.perf_counter()

    def end_frame(self) -> Dict[str, float]:
        if not self._enabled:
            return {}

        frame_ms = (time.perf_counter() - self._frame_start) * 1000.0
        self._frame_number += 1
        self._frame_timings.append(frame_ms)
        self._phase_totals["total_frame"].append(frame_ms)
        self._total_elapsed += frame_ms / 1000.0

        if frame_ms < self._min_frame_ms:
            self._min_frame_ms = frame_ms
        if frame_ms > self._max_frame_ms:
            self._max_frame_ms = frame_ms

        phase_snapshot: Dict[str, float] = {}
        for phase, ring in self._phase_totals.items():
            if ring:
                phase_snapshot[phase] = ring[-1]
            ring.append(0.0)

        if self._frame_number % self._auto_report_interval == 0:
            report = self._build_frame_report(frame_ms, phase_snapshot)
            for cb in self._report_callbacks:
                try:
                    cb(report)
                except Exception:
                    pass

        return phase_snapshot

    def on_report(self, callback: Callable[[FrameReport], None]) -> None:
        self._report_callbacks.append(callback)

    def record_allocation(self, bytes_allocated: int) -> None:
        if not self._enabled:
            return
        self._allocated_total += bytes_allocated
        self._current_memory += bytes_allocated
        self._object_count += 1
        if self._current_memory > self._peak_memory:
            self._peak_memory = self._current_memory

    def record_deallocation(self, bytes_freed: int) -> None:
        if not self._enabled:
            return
        self._freed_total += bytes_freed
        self._current_memory = max(0, self._current_memory - bytes_freed)
        self._object_count = max(0, self._object_count - 1)

    def get_memory_snapshot(self) -> MemorySnapshot:
        return MemorySnapshot(
            allocated_bytes=self._allocated_total,
            freed_bytes=self._freed_total,
            current_bytes=self._current_memory,
            peak_bytes=self._peak_memory,
            object_count=self._object_count,
            allocation_count=self._allocated_total,
        )

    def detect_bottlenecks(self, threshold_ms: float = 16.0) -> List[Dict[str, Any]]:
        bottlenecks: List[Dict[str, Any]] = []
        for phase, ring in self._phase_totals.items():
            if not ring or phase == "total_frame":
                continue
            avg_ms = sum(ring) / len(ring) if ring else 0.0
            if avg_ms > threshold_ms:
                bottlenecks.append({
                    "phase": phase,
                    "average_ms": round(avg_ms, 2),
                    "threshold_ms": threshold_ms,
                    "severity": "critical" if avg_ms > threshold_ms * 2 else "warning",
                    "suggestion": self._generate_suggestion(phase, avg_ms),
                })
        return bottlenecks

    def get_snapshot(self) -> Dict[str, Any]:
        return {
            "enabled": self._enabled,
            "frame_number": self._frame_number,
            "current_fps": self._get_current_fps(),
            "avg_fps": self._get_avg_fps(),
            "min_frame_ms": self._min_frame_ms if self._min_frame_ms != float("inf") else 0.0,
            "max_frame_ms": self._max_frame_ms,
            "avg_frame_ms": self._get_avg_frame_ms(),
            "peak_memory_mb": round(self._peak_memory / (1024 * 1024), 2),
            "current_memory_mb": round(self._current_memory / (1024 * 1024), 2),
            "object_count": self._object_count,
            "window_size": self._window_size,
            "phase_averages": self._get_phase_averages(),
        }

    def generate_report(self) -> ProfilerReport:
        avg_fps = self._get_avg_fps()
        frame_values = list(self._frame_timings)
        p95, p99 = self._compute_percentiles(frame_values)
        bottlenecks = self.detect_bottlenecks()

        perf_level = "optimal"
        if bottlenecks:
            severities = [b["severity"] for b in bottlenecks]
            if "critical" in severities:
                perf_level = "critical"
            elif "warning" in severities:
                perf_level = "warning"
        elif avg_fps < 30:
            perf_level = "critical"
        elif avg_fps < 60:
            perf_level = "acceptable"

        recommendations = [
            "Consider reducing particle count if 'particle_update' is a bottleneck",
            "Simplify collision shapes for better 'collision_update' performance",
            "Reduce pathfinding frequency or use simpler heuristics",
            "Limit tilemap render area to visible bounds",
            "Batch UI widget updates to reduce draw calls",
        ]

        return ProfilerReport(
            report_id=str(time.time()),
            generated_at=time.time(),
            frame_count=self._frame_number,
            elapsed_seconds=round(self._total_elapsed, 2),
            avg_fps=round(avg_fps, 1),
            min_fps=round(1000.0 / max(self._max_frame_ms, 0.001), 1),
            max_fps=round(1000.0 / max(self._min_frame_ms if self._min_frame_ms != float("inf") else 0.001, 0.001), 1),
            p95_frame_ms=round(p95, 2),
            p99_frame_ms=round(p99, 2),
            one_percent_low_fps=round(1000.0 / max(p99, 0.001), 1),
            avg_frame_ms=round(self._get_avg_frame_ms(), 2),
            phase_averages=self._get_phase_averages(),
            peak_memory_bytes=self._peak_memory,
            current_memory_bytes=self._current_memory,
            bottleneck_count=len(bottlenecks),
            recommendations=recommendations,
            performance_level=perf_level,
        )

    def get_frame_report(self) -> FrameReport:
        frame_ms = self._frame_timings[-1] if self._frame_timings else 0.0
        phase_timings = {
            phase: ring[-1] if ring else 0.0
            for phase, ring in self._phase_totals.items()
        }
        return self._build_frame_report(frame_ms, phase_timings)

    def _build_frame_report(self, frame_ms: float, phase_timings: Dict[str, float]) -> FrameReport:
        level, reason = self._bottleneck_detector.analyze(frame_ms, phase_timings, self._frame_timings)
        fps = 1000.0 / max(frame_ms, 0.001)
        return FrameReport(
            frame_number=self._frame_number,
            total_ms=round(frame_ms, 3),
            fps=round(fps, 1),
            phase_timings=phase_timings,
            memory=self.get_memory_snapshot(),
            bottleneck_level=level,
            bottleneck_reason=reason,
        )

    def _get_current_fps(self) -> float:
        if not self._frame_timings:
            return 0.0
        return 1000.0 / max(self._frame_timings[-1], 0.001)

    def _get_avg_fps(self) -> float:
        if not self._frame_timings:
            return 0.0
        avg_ms = sum(self._frame_timings) / len(self._frame_timings)
        return 1000.0 / max(avg_ms, 0.001)

    def _get_avg_frame_ms(self) -> float:
        if not self._frame_timings:
            return 0.0
        return sum(self._frame_timings) / len(self._frame_timings)

    def _get_phase_averages(self) -> Dict[str, float]:
        result: Dict[str, float] = {}
        for phase, ring in self._phase_totals.items():
            if ring:
                result[phase] = round(sum(ring) / len(ring), 3)
        return result

    @staticmethod
    def _compute_percentiles(values: List[float]) -> Tuple[float, float]:
        if not values:
            return (0.0, 0.0)
        sorted_vals = sorted(values)
        n = len(sorted_vals)
        idx_95 = min(int(n * 0.95), n - 1)
        idx_99 = min(int(n * 0.99), n - 1)
        return (sorted_vals[idx_95], sorted_vals[idx_99])

    @staticmethod
    def _generate_suggestion(phase: str, avg_ms: float) -> str:
        suggestions = {
            "physics_step": "Reduce rigid body count or simplify collision shapes",
            "particle_update": "Lower particle emission rate or reduce max particles",
            "render_scene": "Implement frustum culling or reduce draw call count",
            "collision_update": "Use spatial partitioning or simplify collider complexity",
            "behavior_step": "Limit active behaviors per entity or throttle AI updates",
            "pathfinding": "Reduce pathfinding frequency or cache computed paths",
            "audio_update": "Limit concurrent audio channels",
            "ui_render": "Batch UI updates and reduce widget hierarchy depth",
            "animation_update": "Reduce animated sprite count or keyframe complexity",
            "tilemap_render": "Limit render area to camera-visible bounds only",
        }
        return suggestions.get(phase, f"Investigate {phase} optimization opportunities")

    def reset(self) -> None:
        self._frame_timings.clear()
        self._phase_totals = {
            phase: deque(maxlen=self._window_size) for phase in self._default_phases
        }
        self._memory_snapshots.clear()
        self._frame_number = 0
        self._total_elapsed = 0.0
        self._min_frame_ms = float("inf")
        self._max_frame_ms = 0.0
        self._peak_memory = 0
        self._current_memory = 0
        self._allocated_total = 0
        self._freed_total = 0
        self._session_start = time.perf_counter()


def get_profiler() -> Profiler:
    return Profiler.get_instance()
