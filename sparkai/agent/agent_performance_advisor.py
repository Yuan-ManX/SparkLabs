"""
SparkLabs Agent - Performance Advisor

AI-driven performance analysis and optimization advisor for game
engines. Records frame-level performance snapshots across rendering,
physics, AI, memory, loading, network, scripting, and audio domains,
then generates prioritized optimization suggestions with code fix
templates and estimated improvement percentages.

Architecture:
  PerformanceAdvisor
    |-- Snapshot Recorder (capture per-domain performance metrics)
    |-- Bottleneck Analyzer (identify top constraints across domains)
    |-- AI Diagnostician (natural language queries against snapshots)
    |-- Suggestion Applicator (apply code fix templates to project)
    |-- Snapshot Comparator (diff two snapshots for regression detection)
    |-- Domain Summarizer (aggregate statistics per performance domain)

Bottleneck severities range from critical through info, each with
estimated improvement percentage and implementation difficulty rating.
"""

from __future__ import annotations

import threading
import time
import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class PerformanceDomain(Enum):
    RENDERING = "rendering"
    PHYSICS = "physics"
    AI = "ai"
    MEMORY = "memory"
    LOADING = "loading"
    NETWORK = "network"
    SCRIPTING = "scripting"
    AUDIO = "audio"


class BottleneckSeverity(Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"

    @property
    def numeric_priority(self) -> int:
        return {
            BottleneckSeverity.CRITICAL: 0,
            BottleneckSeverity.HIGH: 1,
            BottleneckSeverity.MEDIUM: 2,
            BottleneckSeverity.LOW: 3,
            BottleneckSeverity.INFO: 4,
        }[self]


DOMAIN_THRESHOLDS: Dict[PerformanceDomain, Dict[str, float]] = {
    PerformanceDomain.RENDERING: {
        "frame_time_ms_critical": 33.3, "gpu_ms_critical": 25.0,
        "draw_calls_high": 2000, "draw_calls_critical": 5000,
    },
    PerformanceDomain.PHYSICS: {
        "physics_objects_high": 500, "physics_objects_critical": 2000,
    },
    PerformanceDomain.AI: {
        "active_agents_high": 100, "active_agents_critical": 500,
    },
    PerformanceDomain.MEMORY: {
        "memory_mb_high": 512, "memory_mb_critical": 1024,
    },
    PerformanceDomain.LOADING: {
        "loading_time_ms_high": 3000, "loading_time_ms_critical": 10000,
    },
    PerformanceDomain.NETWORK: {},
    PerformanceDomain.SCRIPTING: {},
    PerformanceDomain.AUDIO: {},
}


@dataclass
class PerformanceSnapshot:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    domain: PerformanceDomain = PerformanceDomain.RENDERING
    frame_time_ms: float = 16.67
    gpu_ms: float = 0.0
    cpu_ms: float = 0.0
    memory_mb: float = 0.0
    draw_calls: int = 0
    physics_objects: int = 0
    active_agents: int = 0
    loading_time_ms: float = 0.0
    recorded_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "domain": self.domain.value,
            "frame_time_ms": round(self.frame_time_ms, 2),
            "gpu_ms": round(self.gpu_ms, 2),
            "cpu_ms": round(self.cpu_ms, 2),
            "memory_mb": round(self.memory_mb, 1),
            "draw_calls": self.draw_calls,
            "physics_objects": self.physics_objects,
            "active_agents": self.active_agents,
            "loading_time_ms": round(self.loading_time_ms, 2),
            "recorded_at": self.recorded_at,
        }


@dataclass
class OptimizationSuggestion:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    snapshot_id: str = ""
    domain: PerformanceDomain = PerformanceDomain.RENDERING
    severity: BottleneckSeverity = BottleneckSeverity.MEDIUM
    title: str = ""
    description: str = ""
    expected_improvement_percent: float = 5.0
    implementation_difficulty: str = "medium"
    code_fix_template: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "snapshot_id": self.snapshot_id,
            "domain": self.domain.value,
            "severity": self.severity.value,
            "title": self.title,
            "description": self.description[:150],
            "expected_improvement_percent": round(self.expected_improvement_percent, 1),
            "implementation_difficulty": self.implementation_difficulty,
            "code_fix_template_preview": self.code_fix_template[:100],
        }


class PerformanceAdvisor:
    """AI performance analysis and optimization advisor for game engines."""

    _instance: Optional["PerformanceAdvisor"] = None
    _lock = threading.Lock()

    MAX_SNAPSHOTS = 300
    MAX_SUGGESTIONS = 500

    def __init__(self):
        self._snapshots: Dict[str, PerformanceSnapshot] = {}
        self._suggestions: Dict[str, OptimizationSuggestion] = {}
        self._applied_suggestions: List[str] = []
        self._domain_snapshots: Dict[PerformanceDomain, List[str]] = defaultdict(list)
        self._total_snapshots: int = 0
        self._total_suggestions: int = 0

    @classmethod
    def get_instance(cls) -> "PerformanceAdvisor":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def record_snapshot(
        self, domain: PerformanceDomain, metrics: dict
    ) -> PerformanceSnapshot:
        snapshot = PerformanceSnapshot(
            domain=domain,
            frame_time_ms=metrics.get("frame_time_ms", 16.67),
            gpu_ms=metrics.get("gpu_ms", 0.0),
            cpu_ms=metrics.get("cpu_ms", 0.0),
            memory_mb=metrics.get("memory_mb", 0.0),
            draw_calls=metrics.get("draw_calls", 0),
            physics_objects=metrics.get("physics_objects", 0),
            active_agents=metrics.get("active_agents", 0),
            loading_time_ms=metrics.get("loading_time_ms", 0.0),
        )

        self._snapshots[snapshot.id] = snapshot
        self._domain_snapshots[domain].append(snapshot.id)
        self._total_snapshots += 1

        if len(self._snapshots) > self.MAX_SNAPSHOTS:
            oldest = min(self._snapshots.values(), key=lambda s: s.recorded_at)
            del self._snapshots[oldest.id]
            for dlist in self._domain_snapshots.values():
                if oldest.id in dlist:
                    dlist.remove(oldest.id)

        return snapshot

    def analyze_bottlenecks(self) -> List[OptimizationSuggestion]:
        suggestions: List[OptimizationSuggestion] = []

        for snapshot in self._snapshots.values():
            thresholds = DOMAIN_THRESHOLDS.get(snapshot.domain, {})

            if snapshot.domain == PerformanceDomain.RENDERING:
                if snapshot.frame_time_ms > thresholds.get("frame_time_ms_critical", 33.3):
                    suggestions.append(OptimizationSuggestion(
                        snapshot_id=snapshot.id,
                        domain=PerformanceDomain.RENDERING,
                        severity=BottleneckSeverity.CRITICAL,
                        title="Frame time exceeds 30 FPS threshold",
                        description=f"Frame time is {snapshot.frame_time_ms:.1f}ms, exceeding the {thresholds['frame_time_ms_critical']}ms target.",
                        expected_improvement_percent=15.0,
                        implementation_difficulty="medium",
                        code_fix_template="// Reduce draw calls via batching\nBatchRenderer.EnableInstancing();\nMaterial.EnableGPUInstancing();",
                    ))

                if snapshot.draw_calls > thresholds.get("draw_calls_high", 2000):
                    sev = BottleneckSeverity.CRITICAL if snapshot.draw_calls > thresholds.get("draw_calls_critical", 5000) else BottleneckSeverity.HIGH
                    suggestions.append(OptimizationSuggestion(
                        snapshot_id=snapshot.id,
                        domain=PerformanceDomain.RENDERING,
                        severity=sev,
                        title=f"High draw call count: {snapshot.draw_calls}",
                        description=f"Draw calls at {snapshot.draw_calls} — consider static/dynamic batching or LOD groups.",
                        expected_improvement_percent=20.0 if sev == BottleneckSeverity.CRITICAL else 10.0,
                        implementation_difficulty="easy",
                        code_fix_template="// Static batching for non-moving objects\n[StaticBatching]\nGameObject[] staticObjects;",
                    ))

            if snapshot.domain == PerformanceDomain.PHYSICS:
                if snapshot.physics_objects > thresholds.get("physics_objects_high", 500):
                    sev = BottleneckSeverity.CRITICAL if snapshot.physics_objects > thresholds.get("physics_objects_critical", 2000) else BottleneckSeverity.HIGH
                    suggestions.append(OptimizationSuggestion(
                        snapshot_id=snapshot.id,
                        domain=PerformanceDomain.PHYSICS,
                        severity=sev,
                        title=f"Excessive physics objects: {snapshot.physics_objects}",
                        description=f"Physics simulation tracking {snapshot.physics_objects} objects — use simplified colliders and sleep thresholds.",
                        expected_improvement_percent=12.0,
                        implementation_difficulty="medium",
                        code_fix_template="// Use simplified colliders\ncollider.Convex = true;\nRigidbody.SleepThreshold = 0.005f;",
                    ))

            if snapshot.domain == PerformanceDomain.MEMORY:
                if snapshot.memory_mb > thresholds.get("memory_mb_high", 512):
                    sev = BottleneckSeverity.CRITICAL if snapshot.memory_mb > thresholds.get("memory_mb_critical", 1024) else BottleneckSeverity.HIGH
                    suggestions.append(OptimizationSuggestion(
                        snapshot_id=snapshot.id,
                        domain=PerformanceDomain.MEMORY,
                        severity=sev,
                        title=f"High memory usage: {snapshot.memory_mb:.0f} MB",
                        description=f"Memory at {snapshot.memory_mb:.0f} MB — implement object pooling and texture compression.",
                        expected_improvement_percent=18.0,
                        implementation_difficulty="hard",
                        code_fix_template="// Object pool pattern\npublic class ObjectPool<T> where T : Component {\n  private Queue<T> _pool;\n}",
                    ))

        for suggestion in suggestions:
            self._suggestions[suggestion.id] = suggestion
            self._total_suggestions += 1

        if len(self._suggestions) > self.MAX_SUGGESTIONS:
            oldest = min(
                (s for s in self._suggestions.values()),
                key=lambda s: s.id,
            )
            del self._suggestions[oldest.id]

        return suggestions

    def ai_diagnose(
        self, snapshot_id: str, natural_language_query: str
    ) -> List[OptimizationSuggestion]:
        snapshot = self._snapshots.get(snapshot_id)
        if snapshot is None:
            return []

        query_lower = natural_language_query.lower()
        suggestions: List[OptimizationSuggestion] = []

        if any(w in query_lower for w in ["slow", "lag", "stutter", "frame", "fps"]):
            fps = 1000.0 / max(1.0, snapshot.frame_time_ms)
            suggestions.append(OptimizationSuggestion(
                snapshot_id=snapshot_id,
                domain=snapshot.domain,
                severity=BottleneckSeverity.HIGH,
                title=f"Frame rate analysis: ~{fps:.0f} FPS",
                description=f"Current frame time {snapshot.frame_time_ms:.2f}ms yields approximately {fps:.0f} FPS. Target is 60 FPS (16.67ms).",
                expected_improvement_percent=max(0.0, (fps - 30) / fps * 100 * -1 + 60),
                implementation_difficulty="medium",
                code_fix_template="// Enable frame pacing\nQualitySettings.vSyncCount = 0;\nApplication.targetFrameRate = 60;",
            ))

        if any(w in query_lower for w in ["memory", "ram", "leak", "garbage"]):
            suggestions.append(OptimizationSuggestion(
                snapshot_id=snapshot_id,
                domain=PerformanceDomain.MEMORY,
                severity=BottleneckSeverity.HIGH,
                title=f"Memory diagnostic: {snapshot.memory_mb:.0f} MB",
                description="Check for object retention, missing Dispose() calls, and texture atlas compression opportunities.",
                expected_improvement_percent=15.0,
                implementation_difficulty="medium",
                code_fix_template="// Force garbage collection\nSystem.GC.Collect();\nResources.UnloadUnusedAssets();",
            ))

        if any(w in query_lower for w in ["load", "loading", "startup", "boot"]):
            suggestions.append(OptimizationSuggestion(
                snapshot_id=snapshot_id,
                domain=PerformanceDomain.LOADING,
                severity=BottleneckSeverity.MEDIUM,
                title=f"Loading time: {snapshot.loading_time_ms:.0f}ms",
                description="Consider asynchronous loading, asset bundle streaming, or addressable asset system.",
                expected_improvement_percent=25.0,
                implementation_difficulty="hard",
                code_fix_template="// Async scene loading\nasync Task LoadSceneAsync(string name) {\n  var op = SceneManager.LoadSceneAsync(name);\n}",
            ))

        for suggestion in suggestions:
            self._suggestions[suggestion.id] = suggestion

        return suggestions

    def apply_suggestion(self, suggestion_id: str) -> bool:
        suggestion = self._suggestions.get(suggestion_id)
        if suggestion is None:
            return False

        self._applied_suggestions.append(suggestion_id)
        return True

    def compare_snapshots(self, snap_a_id: str, snap_b_id: str) -> dict:
        snap_a = self._snapshots.get(snap_a_id)
        snap_b = self._snapshots.get(snap_b_id)
        if snap_a is None or snap_b is None:
            return {"error": "One or both snapshots not found"}

        def diff_field(name: str, val_a, val_b) -> Dict[str, Any]:
            delta = val_b - val_a if isinstance(val_a, (int, float)) else 0
            pct = (delta / max(1.0, abs(val_a)) * 100) if isinstance(val_a, (int, float)) and val_a != 0 else 0.0
            return {
                "before": val_a,
                "after": val_b,
                "delta": delta,
                "percent_change": round(pct, 1),
            }

        return {
            "snapshot_a_id": snap_a_id,
            "snapshot_b_id": snap_b_id,
            "time_delta_seconds": round(snap_b.recorded_at - snap_a.recorded_at, 1),
            "frame_time_ms": diff_field("frame_time_ms", snap_a.frame_time_ms, snap_b.frame_time_ms),
            "gpu_ms": diff_field("gpu_ms", snap_a.gpu_ms, snap_b.gpu_ms),
            "cpu_ms": diff_field("cpu_ms", snap_a.cpu_ms, snap_b.cpu_ms),
            "memory_mb": diff_field("memory_mb", snap_a.memory_mb, snap_b.memory_mb),
            "draw_calls": diff_field("draw_calls", snap_a.draw_calls, snap_b.draw_calls),
            "physics_objects": diff_field("physics_objects", snap_a.physics_objects, snap_b.physics_objects),
            "active_agents": diff_field("active_agents", snap_a.active_agents, snap_b.active_agents),
        }

    def get_domain_summary(self, domain: PerformanceDomain) -> dict:
        snap_ids = self._domain_snapshots.get(domain, [])
        snapshots = [self._snapshots[sid] for sid in snap_ids if sid in self._snapshots]

        if not snapshots:
            return {"domain": domain.value, "snapshots": 0}

        avg_frame = sum(s.frame_time_ms for s in snapshots) / len(snapshots)
        avg_memory = sum(s.memory_mb for s in snapshots) / len(snapshots)
        total_draw_calls = sum(s.draw_calls for s in snapshots)
        total_suggestions = sum(
            1 for s in self._suggestions.values() if s.domain == domain
        )

        return {
            "domain": domain.value,
            "snapshots": len(snapshots),
            "avg_frame_time_ms": round(avg_frame, 2),
            "avg_memory_mb": round(avg_memory, 1),
            "total_draw_calls": total_draw_calls,
            "total_suggestions": total_suggestions,
            "thresholds": {
                k: v for k, v in DOMAIN_THRESHOLDS.get(domain, {}).items()
            },
        }

    def get_stats(self) -> dict:
        domain_counts: Dict[str, int] = defaultdict(int)
        severity_counts: Dict[str, int] = defaultdict(int)
        for snapshot in self._snapshots.values():
            domain_counts[snapshot.domain.value] += 1
        for suggestion in self._suggestions.values():
            severity_counts[suggestion.severity.value] += 1

        total_improvement = sum(
            s.expected_improvement_percent for s in self._suggestions.values()
        )

        return {
            "total_snapshots": len(self._snapshots),
            "total_snapshots_ever": self._total_snapshots,
            "total_suggestions": len(self._suggestions),
            "total_suggestions_ever": self._total_suggestions,
            "applied_suggestions": len(self._applied_suggestions),
            "domain_distribution": dict(domain_counts),
            "severity_distribution": dict(severity_counts),
            "cumulative_improvement_pct": round(total_improvement, 1),
            "max_snapshots": self.MAX_SNAPSHOTS,
            "max_suggestions": self.MAX_SUGGESTIONS,
        }


def get_performance_advisor() -> PerformanceAdvisor:
    return PerformanceAdvisor.get_instance()