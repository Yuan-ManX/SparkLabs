"""
SparkLabs Engine - Profiler System

Real-time performance monitoring and instrumentation for the AI-native
game engine. Tracks rendering, physics, scripting, AI, memory, network,
audio, animation, UI, and IO subsystems with frame-level granularity.

Architecture:
  ProfilerSystem
    |-- ProfilerMonitor (individual metric tracker with stats)
    |-- ProfilerFrame (aggregated per-frame timing data)
    |-- Monitor Registry (named monitor management)
    |-- Frame History (rolling buffer of recent frames)

Monitor Types:
  - COUNTER: cumulative event counts (draw calls, collisions, etc.)
  - GAUGE: instantaneous value snapshots (FPS, memory usage)
  - HISTOGRAM: distribution of values (frame time spread)
  - TIMER: scoped timing blocks (system step durations)
  - MEMORY: allocation tracking with peak detection
"""

from __future__ import annotations

import time
import uuid
from collections import deque
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple


class ProfilerCategory(Enum):
    RENDERING = "rendering"
    PHYSICS = "physics"
    SCRIPTING = "scripting"
    AI = "ai"
    MEMORY = "memory"
    NETWORK = "network"
    AUDIO = "audio"
    ANIMATION = "animation"
    UI = "ui"
    IO = "io"


class MonitorType(Enum):
    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    TIMER = "timer"
    MEMORY = "memory"


@dataclass
class ProfilerMonitor:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = ""
    category: ProfilerCategory = ProfilerCategory.RENDERING
    monitor_type: MonitorType = MonitorType.GAUGE
    current_value: float = 0.0
    min_value: float = float("inf")
    max_value: float = float("-inf")
    average: float = 0.0
    sample_count: int = 0
    unit: str = "ms"

    def record_sample(self, value: float) -> None:
        self.current_value = value
        self.sample_count += 1
        if value < self.min_value:
            self.min_value = value
        if value > self.max_value:
            self.max_value = value
        self.average = ((self.average * (self.sample_count - 1)) + value) / self.sample_count

    def reset(self) -> None:
        self.current_value = 0.0
        self.min_value = float("inf")
        self.max_value = float("-inf")
        self.average = 0.0
        self.sample_count = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "category": self.category.value,
            "monitor_type": self.monitor_type.value,
            "current_value": round(self.current_value, 4),
            "min_value": round(self.min_value, 4) if self.min_value != float("inf") else 0.0,
            "max_value": round(self.max_value, 4) if self.max_value != float("-inf") else 0.0,
            "average": round(self.average, 4),
            "sample_count": self.sample_count,
            "unit": self.unit,
        }


@dataclass
class ProfilerFrame:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    frame_number: int = 0
    monitors: List[ProfilerMonitor] = field(default_factory=list)
    total_frame_time_ms: float = 0.0
    fps: float = 0.0
    recorded_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "frame_number": self.frame_number,
            "total_frame_time_ms": round(self.total_frame_time_ms, 4),
            "fps": round(self.fps, 2),
            "recorded_at": self.recorded_at,
            "monitor_count": len(self.monitors),
        }


class ProfilerSystem:
    """
    Real-time performance profiler with per-category monitors.

    Tracks subsystem performance across frames with rolling history.
    Supports named event markers and aggregated statistical reporting.
    Use start_profiling() / stop_profiling() to control capture.

    Usage:
        prof = get_profiler_system()
        prof.start_profiling()
        mon = prof.add_monitor("draw_calls", ProfilerCategory.RENDERING, MonitorType.COUNTER, "calls")
        mon.record_sample(124.0)
        frame = prof.record_frame()
        stats = prof.get_stats()
    """

    _instance: Optional["ProfilerSystem"] = None

    def __init__(self):
        self._monitors: Dict[str, ProfilerMonitor] = {}
        self._frame_history: deque = deque(maxlen=300)
        self._frame_counter: int = 0
        self._is_profiling: bool = False
        self._events: List[Dict[str, Any]] = []
        self._start_time: float = 0.0
        self._last_frame_time: float = time.time()

    @classmethod
    def get_instance(cls) -> "ProfilerSystem":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def add_monitor(
        self,
        name: str,
        category: ProfilerCategory,
        monitor_type: MonitorType,
        unit: str = "ms",
    ) -> ProfilerMonitor:
        monitor = ProfilerMonitor(
            name=name,
            category=category,
            monitor_type=monitor_type,
            unit=unit,
        )
        self._monitors[monitor.id] = monitor
        return monitor

    def remove_monitor(self, monitor_id: str) -> bool:
        if monitor_id in self._monitors:
            del self._monitors[monitor_id]
            return True
        return False

    def get_monitor(self, monitor_id: str) -> Optional[ProfilerMonitor]:
        return self._monitors.get(monitor_id)

    def list_monitors(self) -> List[ProfilerMonitor]:
        return list(self._monitors.values())

    def list_monitors_by_category(self, category: ProfilerCategory) -> List[ProfilerMonitor]:
        return [m for m in self._monitors.values() if m.category == category]

    def record_sample(self, monitor_id: str, value: float) -> bool:
        monitor = self._monitors.get(monitor_id)
        if monitor is None:
            return False
        monitor.record_sample(value)
        return True

    def record_frame(self) -> ProfilerFrame:
        self._frame_counter += 1
        now = time.time()
        frame_time = now - self._last_frame_time
        self._last_frame_time = now

        fps = 1.0 / frame_time if frame_time > 0 else 0.0

        frame = ProfilerFrame(
            frame_number=self._frame_counter,
            monitors=list(self._monitors.values()),
            total_frame_time_ms=frame_time * 1000.0,
            fps=fps,
        )
        self._frame_history.append(frame)
        return frame

    def get_frame_summary(self) -> dict:
        total_frames = len(self._frame_history)
        if total_frames == 0:
            return {"frame_count": 0, "avg_fps": 0, "avg_frame_time_ms": 0, "min_fps": 0, "max_fps": 0}

        fps_values = [f.fps for f in self._frame_history if f.fps > 0]
        time_values = [f.total_frame_time_ms for f in self._frame_history]

        return {
            "frame_count": total_frames,
            "avg_fps": round(sum(fps_values) / len(fps_values), 2) if fps_values else 0.0,
            "avg_frame_time_ms": round(sum(time_values) / len(time_values), 4) if time_values else 0.0,
            "min_fps": round(min(fps_values), 2) if fps_values else 0.0,
            "max_fps": round(max(fps_values), 2) if fps_values else 0.0,
            "total_time_ms": round(sum(time_values), 2) if time_values else 0.0,
        }

    def get_monitor_history(self, monitor_id: str, frames: int = 60) -> list:
        monitor = self._monitors.get(monitor_id)
        if monitor is None:
            return []

        recent = list(self._frame_history)[-frames:]
        result = []
        for frame in recent:
            matched = next((m for m in frame.monitors if m.id == monitor_id), None)
            if matched:
                result.append({
                    "frame": frame.frame_number,
                    "value": matched.current_value,
                    "average": matched.average,
                })
        return result

    def start_profiling(self) -> None:
        self._is_profiling = True
        self._start_time = time.time()
        for monitor in self._monitors.values():
            monitor.reset()
        self._frame_history.clear()
        self._frame_counter = 0
        self._events.clear()

    def stop_profiling(self) -> None:
        self._is_profiling = False

    def mark_event(self, name: str, data: Optional[dict] = None) -> None:
        event = {
            "name": name,
            "timestamp": time.time(),
            "frame_number": self._frame_counter,
            "data": data or {},
        }
        self._events.append(event)

    def get_events(self) -> List[Dict[str, Any]]:
        return list(self._events)

    def get_category_breakdown(self) -> Dict[str, float]:
        breakdown: Dict[str, float] = {}
        category_totals: Dict[ProfilerCategory, List[float]] = {}

        for monitor in self._monitors.values():
            if monitor.sample_count > 0:
                if monitor.category not in category_totals:
                    category_totals[monitor.category] = []
                category_totals[monitor.category].append(monitor.current_value)

        for cat, values in category_totals.items():
            breakdown[cat.value] = round(sum(values), 4)

        return breakdown

    def get_stats(self) -> Dict[str, Any]:
        return {
            "is_profiling": self._is_profiling,
            "frame_count": self._frame_counter,
            "monitor_count": len(self._monitors),
            "history_size": len(self._frame_history),
            "event_count": len(self._events),
            "elapsed_time_s": round(time.time() - self._start_time, 2) if self._is_profiling else 0.0,
            "frame_summary": self.get_frame_summary(),
            "category_breakdown": self.get_category_breakdown(),
            "monitors": [m.to_dict() for m in self._monitors.values()],
        }

    def reset(self) -> None:
        self._monitors.clear()
        self._frame_history.clear()
        self._frame_counter = 0
        self._is_profiling = False
        self._events.clear()
        self._start_time = 0.0


def get_profiler_system() -> ProfilerSystem:
    return ProfilerSystem.get_instance()