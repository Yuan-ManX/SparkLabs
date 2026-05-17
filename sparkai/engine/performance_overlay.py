"""
SparkLabs Engine - Performance Debug Overlay System

Real-time performance metrics overlay for the AI-native game engine.
Tracks frame timing, memory usage, draw calls, object counts, and
subsystem CPU/GPU budgets. Provides rolling-frame statistics, snapshot
profiling, threshold-based alerts, and formatted overlay text output
for on-screen rendering.

Architecture:
  PerformanceOverlay (singleton)
    |-- FrameSample (per-frame metrics datum)
    |-- MetricThreshold (configurable warning/error limit)
    |-- ProfilingSnapshot (named capture window with stddev stats)
    |-- Rolling Window (last 300 frames for trend analysis)
    |-- Threshold Evaluator (OK/WARNING/ERROR per metric)

Usage:
    po = get_performance_overlay()
    po.record_frame(16.6, 124, 8432, 156.3, 8.2, 12.1, 3.4, 1.2, 512)
    fps = po.get_current_fps()
    text = po.generate_overlay_text([OverlaySection.FPS, OverlaySection.MEMORY])
    alerts = po.check_thresholds()
    po.start_snapshot("boss_fight")
    po.stop_snapshot()
"""

from __future__ import annotations

import math
import threading
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class OverlaySection(Enum):
    FPS = "fps"
    FRAME_TIME = "frame_time"
    MEMORY = "memory"
    DRAW_CALLS = "draw_calls"
    OBJECTS = "objects"
    PHYSICS = "physics"
    SCRIPT_CPU = "script_cpu"
    GPU_TIME = "gpu_time"
    ALL = "all"


class MetricSeverity(Enum):
    OK = "ok"
    WARNING = "warning"
    ERROR = "error"


@dataclass
class FrameSample:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    frame_number: int = 0
    delta_time: float = 0.0
    fps: float = 0.0
    draw_calls: int = 0
    triangle_count: int = 0
    memory_used_mb: float = 0.0
    cpu_time_ms: float = 0.0
    gpu_time_ms: float = 0.0
    physics_time_ms: float = 0.0
    script_time_ms: float = 0.0
    object_count: int = 0
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "frame_number": self.frame_number,
            "delta_time": self.delta_time,
            "fps": self.fps,
            "draw_calls": self.draw_calls,
            "triangle_count": self.triangle_count,
            "memory_used_mb": self.memory_used_mb,
            "cpu_time_ms": self.cpu_time_ms,
            "gpu_time_ms": self.gpu_time_ms,
            "physics_time_ms": self.physics_time_ms,
            "script_time_ms": self.script_time_ms,
            "object_count": self.object_count,
            "timestamp": self.timestamp,
        }


@dataclass
class MetricThreshold:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    metric_name: str = ""
    warning_threshold: float = 0.0
    error_threshold: float = 0.0
    is_enabled: bool = True

    def evaluate(self, value: float) -> MetricSeverity:
        if not self.is_enabled:
            return MetricSeverity.OK
        if self.metric_name == "fps":
            if value <= self.error_threshold:
                return MetricSeverity.ERROR
            if value <= self.warning_threshold:
                return MetricSeverity.WARNING
            return MetricSeverity.OK
        if value >= self.error_threshold:
            return MetricSeverity.ERROR
        if value >= self.warning_threshold:
            return MetricSeverity.WARNING
        return MetricSeverity.OK


@dataclass
class ProfilingSnapshot:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = ""
    samples: List[FrameSample] = field(default_factory=list)
    avg_fps: float = 0.0
    min_fps: float = 0.0
    max_fps: float = 0.0
    fps_stddev: float = 0.0
    sample_count: int = 0
    duration_seconds: float = 0.0
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "samples": [s.to_dict() for s in self.samples],
            "avg_fps": self.avg_fps,
            "min_fps": self.min_fps,
            "max_fps": self.max_fps,
            "fps_stddev": self.fps_stddev,
            "sample_count": self.sample_count,
            "duration_seconds": self.duration_seconds,
            "timestamp": self.timestamp,
        }


class PerformanceOverlay:
    """
    Real-time performance debug overlay for in-game metrics display.

    Collects per-frame timing and resource data in a rolling window
    of the last 300 frames. Evaluates configurable thresholds for
    alerting and produces formatted overlay text for on-screen
    rendering. Supports named profiling snapshots for capturing
    specific code paths or scene regions.

    Usage:
        po = get_performance_overlay()
        po.record_frame(delta_time=16.67, draw_calls=200, ...)
        fps = po.get_current_fps()
        alerts = po.check_thresholds()
    """

    _instance: Optional["PerformanceOverlay"] = None
    _lock: threading.RLock = threading.RLock()

    MAX_SAMPLES: int = 300

    def __init__(self) -> None:
        self._samples: List[FrameSample] = []
        self._thresholds: Dict[str, MetricThreshold] = {}
        self._snapshots: List[ProfilingSnapshot] = []
        self._sample_count: int = 0
        self._snapshot_count: int = 0
        self._is_capturing: bool = False
        self._capture_buffer: List[FrameSample] = []
        self._capture_start_time: float = 0.0
        self._capture_name: str = ""

        self._init_default_thresholds()

    def _init_default_thresholds(self) -> None:
        self._thresholds["fps"] = MetricThreshold(
            metric_name="fps", warning_threshold=45.0, error_threshold=30.0
        )
        self._thresholds["frame_time"] = MetricThreshold(
            metric_name="frame_time", warning_threshold=22.0, error_threshold=33.0
        )
        self._thresholds["memory"] = MetricThreshold(
            metric_name="memory", warning_threshold=500.0, error_threshold=1000.0
        )
        self._thresholds["draw_calls"] = MetricThreshold(
            metric_name="draw_calls", warning_threshold=2000.0, error_threshold=5000.0
        )
        self._thresholds["objects"] = MetricThreshold(
            metric_name="objects", warning_threshold=5000.0, error_threshold=10000.0
        )

    @classmethod
    def get_instance(cls) -> "PerformanceOverlay":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    # ------------------------------------------------------------------
    # Frame Recording
    # ------------------------------------------------------------------

    def record_frame(
        self,
        delta_time: float,
        draw_calls: int,
        triangle_count: int,
        memory_used_mb: float,
        cpu_time_ms: float,
        gpu_time_ms: float,
        physics_time_ms: float,
        script_time_ms: float,
        object_count: int,
    ) -> FrameSample:
        with self._lock:
            self._sample_count += 1
            fps = 1000.0 / delta_time if delta_time > 0 else 0.0

            sample = FrameSample(
                frame_number=self._sample_count,
                delta_time=delta_time,
                fps=fps,
                draw_calls=draw_calls,
                triangle_count=triangle_count,
                memory_used_mb=memory_used_mb,
                cpu_time_ms=cpu_time_ms,
                gpu_time_ms=gpu_time_ms,
                physics_time_ms=physics_time_ms,
                script_time_ms=script_time_ms,
                object_count=object_count,
            )
            self._samples.append(sample)

            while len(self._samples) > self.MAX_SAMPLES:
                self._samples.pop(0)

            if self._is_capturing:
                self._capture_buffer.append(sample)

            return sample

    # ------------------------------------------------------------------
    # Current Metrics
    # ------------------------------------------------------------------

    def get_current_fps(self) -> float:
        with self._lock:
            recent = self._samples[-60:]
            if not recent:
                return 0.0
            return sum(s.fps for s in recent) / len(recent)

    def get_frame_time_stats(self) -> Dict[str, float]:
        with self._lock:
            if not self._samples:
                return {"avg_ms": 0.0, "min_ms": 0.0, "max_ms": 0.0}
            times = [s.delta_time for s in self._samples]
            return {
                "avg_ms": round(sum(times) / len(times), 2),
                "min_ms": round(min(times), 2),
                "max_ms": round(max(times), 2),
            }

    def get_memory_usage(self) -> Dict[str, float]:
        with self._lock:
            if not self._samples:
                return {"current_mb": 0.0, "peak_mb": 0.0}
            current = self._samples[-1].memory_used_mb
            peak = max(s.memory_used_mb for s in self._samples)
            return {"current_mb": round(current, 2), "peak_mb": round(peak, 2)}

    # ------------------------------------------------------------------
    # Metric Summary
    # ------------------------------------------------------------------

    def get_metric_summary(self, overlay_section: OverlaySection) -> Dict[str, Any]:
        with self._lock:
            if not self._samples:
                return {
                    "section": overlay_section.value,
                    "current": 0.0,
                    "avg": 0.0,
                    "min": 0.0,
                    "max": 0.0,
                    "severity": MetricSeverity.OK.value,
                }
            return self._compute_section_summary(overlay_section)

    def _compute_section_summary(self, section: OverlaySection) -> Dict[str, Any]:
        samples = self._samples
        current: float
        values: List[float]
        threshold: Optional[MetricThreshold]

        if section == OverlaySection.FPS:
            values = [s.fps for s in samples]
            current = samples[-1].fps
            threshold = self._thresholds.get("fps")
        elif section == OverlaySection.FRAME_TIME:
            values = [s.delta_time for s in samples]
            current = samples[-1].delta_time
            threshold = self._thresholds.get("frame_time")
        elif section == OverlaySection.MEMORY:
            values = [s.memory_used_mb for s in samples]
            current = samples[-1].memory_used_mb
            threshold = self._thresholds.get("memory")
        elif section == OverlaySection.DRAW_CALLS:
            values = [float(s.draw_calls) for s in samples]
            current = float(samples[-1].draw_calls)
            threshold = self._thresholds.get("draw_calls")
        elif section == OverlaySection.OBJECTS:
            values = [float(s.object_count) for s in samples]
            current = float(samples[-1].object_count)
            threshold = self._thresholds.get("objects")
        elif section == OverlaySection.PHYSICS:
            values = [s.physics_time_ms for s in samples]
            current = samples[-1].physics_time_ms
            threshold = None
        elif section == OverlaySection.SCRIPT_CPU:
            values = [s.script_time_ms for s in samples]
            current = samples[-1].script_time_ms
            threshold = None
        elif section == OverlaySection.GPU_TIME:
            values = [s.gpu_time_ms for s in samples]
            current = samples[-1].gpu_time_ms
            threshold = None
        elif section == OverlaySection.ALL:
            return self._compute_all_sections_summary()
        else:
            return {
                "section": section.value,
                "current": 0.0,
                "avg": 0.0,
                "min": 0.0,
                "max": 0.0,
                "severity": MetricSeverity.OK.value,
            }

        severity = MetricSeverity.OK
        if threshold is not None:
            severity = threshold.evaluate(current)

        return {
            "section": section.value,
            "current": round(current, 2),
            "avg": round(sum(values) / len(values), 2) if values else 0.0,
            "min": round(min(values), 2) if values else 0.0,
            "max": round(max(values), 2) if values else 0.0,
            "severity": severity.value,
        }

    def _compute_all_sections_summary(self) -> Dict[str, Any]:
        individual_sections = [
            OverlaySection.FPS,
            OverlaySection.FRAME_TIME,
            OverlaySection.MEMORY,
            OverlaySection.DRAW_CALLS,
            OverlaySection.OBJECTS,
            OverlaySection.PHYSICS,
            OverlaySection.SCRIPT_CPU,
            OverlaySection.GPU_TIME,
        ]
        result: Dict[str, Any] = {
            "section": OverlaySection.ALL.value,
            "sections": {},
        }
        for sec in individual_sections:
            result["sections"][sec.value] = self._compute_section_summary(sec)
        return result

    # ------------------------------------------------------------------
    # Profiling Snapshots
    # ------------------------------------------------------------------

    def start_snapshot(self, name: str) -> str:
        with self._lock:
            if self._is_capturing:
                return ""
            self._is_capturing = True
            self._capture_buffer = list(self._samples)
            self._capture_start_time = time.time()
            self._capture_name = name
            return self._capture_name

    def stop_snapshot(self) -> Optional[ProfilingSnapshot]:
        with self._lock:
            if not self._is_capturing:
                return None
            self._is_capturing = False
            self._snapshot_count += 1

            captured = self._capture_buffer
            self._capture_buffer = []

            snapshot = self._build_snapshot(self._capture_name, captured)
            self._snapshots.append(snapshot)

            while len(self._snapshots) > 50:
                self._snapshots.pop(0)

            return snapshot

    def _build_snapshot(
        self, name: str, captured: List[FrameSample]
    ) -> ProfilingSnapshot:
        if not captured:
            return ProfilingSnapshot(name=name)

        fps_values = [s.fps for s in captured]
        avg_val = sum(fps_values) / len(fps_values)
        min_val = min(fps_values)
        max_val = max(fps_values)

        variance = sum((f - avg_val) ** 2 for f in fps_values) / len(fps_values)
        stddev_val = math.sqrt(variance)

        duration = 0.0
        if len(captured) > 1:
            duration = captured[-1].timestamp - captured[0].timestamp

        return ProfilingSnapshot(
            name=name,
            samples=list(captured),
            avg_fps=round(avg_val, 2),
            min_fps=round(min_val, 2),
            max_fps=round(max_val, 2),
            fps_stddev=round(stddev_val, 2),
            sample_count=len(captured),
            duration_seconds=round(duration, 3),
        )

    def get_recent_snapshots(self, limit: int = 10) -> List[ProfilingSnapshot]:
        with self._lock:
            return list(self._snapshots[-limit:])

    # ------------------------------------------------------------------
    # Threshold Management
    # ------------------------------------------------------------------

    def set_threshold(
        self, metric_name: str, warning: float, error: float
    ) -> MetricThreshold:
        with self._lock:
            existing = self._thresholds.get(metric_name)
            if existing is not None:
                existing.warning_threshold = warning
                existing.error_threshold = error
                existing.is_enabled = True
                return existing

            threshold = MetricThreshold(
                metric_name=metric_name,
                warning_threshold=warning,
                error_threshold=error,
            )
            self._thresholds[metric_name] = threshold
            return threshold

    def check_thresholds(self) -> List[Dict[str, Any]]:
        with self._lock:
            if not self._samples:
                return []

            latest = self._samples[-1]
            alerts: List[Dict[str, Any]] = []

            metric_map = {
                "fps": ("FPS", latest.fps),
                "frame_time": ("Frame Time", latest.delta_time),
                "memory": ("Memory", latest.memory_used_mb),
                "draw_calls": ("Draw Calls", float(latest.draw_calls)),
                "objects": ("Objects", float(latest.object_count)),
            }

            for metric_name, (label, value) in metric_map.items():
                threshold = self._thresholds.get(metric_name)
                if threshold is None or not threshold.is_enabled:
                    continue
                severity = threshold.evaluate(value)
                if severity != MetricSeverity.OK:
                    alerts.append({
                        "metric": label,
                        "metric_key": metric_name,
                        "current_value": value,
                        "warning_threshold": threshold.warning_threshold,
                        "error_threshold": threshold.error_threshold,
                        "severity": severity.value,
                    })

            return alerts

    # ------------------------------------------------------------------
    # Overlay Text Generation
    # ------------------------------------------------------------------

    def generate_overlay_text(self, sections: List[OverlaySection]) -> str:
        with self._lock:
            if not self._samples:
                return "Performance Overlay\n===\nNo data recorded"

            lines: List[str] = ["Performance Overlay", "==="]
            display_set = sections if sections else [OverlaySection.ALL]

            for section in display_set:
                summary = self._compute_section_summary(section)
                lines.extend(self._format_section_lines(section, summary))

            return "\n".join(lines)

    def _format_section_lines(
        self, section: OverlaySection, summary: Dict[str, Any]
    ) -> List[str]:
        if section == OverlaySection.ALL:
            result: List[str] = []
            for sec_name, sec_data in summary.get("sections", {}).items():
                result.append(
                    f"  {sec_name}: {sec_data.get('current', 0)} "
                    f"[{sec_data.get('severity', 'ok')}]"
                )
            return result

        severity = summary.get("severity", MetricSeverity.OK.value)
        current = summary.get("current", 0)
        avg = summary.get("avg", 0)
        min_v = summary.get("min", 0)
        max_v = summary.get("max", 0)
        unit = self._unit_for_section(section)

        return [
            f"  {section.value}: {current}{unit} "
            f"(avg:{avg} min:{min_v} max:{max_v}) [{severity.upper()}]",
        ]

    def _unit_for_section(self, section: OverlaySection) -> str:
        unit_map = {
            OverlaySection.FPS: " fps",
            OverlaySection.FRAME_TIME: "ms",
            OverlaySection.MEMORY: "MB",
            OverlaySection.DRAW_CALLS: "",
            OverlaySection.OBJECTS: "",
            OverlaySection.PHYSICS: "ms",
            OverlaySection.SCRIPT_CPU: "ms",
            OverlaySection.GPU_TIME: "ms",
        }
        return unit_map.get(section, "")

    # ------------------------------------------------------------------
    # Reset & Stats
    # ------------------------------------------------------------------

    def reset_metrics(self) -> None:
        with self._lock:
            self._samples.clear()
            self._sample_count = 0
            self._is_capturing = False
            self._capture_buffer.clear()

    def get_stats(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "total_samples": self._sample_count,
                "active_snapshots": len(self._snapshots),
                "threshold_count": len(self._thresholds),
                "rolling_window_size": len(self._samples),
            }


def get_performance_overlay() -> PerformanceOverlay:
    return PerformanceOverlay.get_instance()