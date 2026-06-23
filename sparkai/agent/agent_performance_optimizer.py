"""
SparkLabs Agent - Performance Optimizer

AI-driven performance optimization engine for the SparkLabs AI-native
game engine. Monitors game runtime performance metrics across multiple
domains (frame rate, memory, CPU, GPU, network, I/O, physics, AI,
rendering, audio), detects bottlenecks, and generates optimization
recommendations using AI-driven analysis.

Architecture:
  PerformanceOptimizerEngine
    |-- Metric Recorder (collect per-domain performance metrics)
    |-- Bottleneck Detector (identify constraints via threshold analysis)
    |-- Suggestion Generator (AI-driven optimization recommendations)
    |-- Snapshot Engine (point-in-time performance snapshots)
    |-- Report Generator (comprehensive optimization reports)

Bottleneck types span CPU-bound, GPU-bound, memory-bound, I/O-bound,
and network-bound categories, each with severity ratings from critical
to info. Optimization strategies include batch processing, object
pooling, LOD optimization, culling, memory compaction, load balancing,
cache optimization, and async operation patterns.
"""

from __future__ import annotations

import threading
import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class MetricDomain(Enum):
    """Performance measurement domains within the game engine."""
    FRAME_RATE = "frame_rate"
    MEMORY = "memory"
    CPU = "cpu"
    GPU = "gpu"
    NETWORK = "network"
    IO = "io"
    PHYSICS = "physics"
    AI = "ai"
    RENDERING = "rendering"
    AUDIO = "audio"


class BottleneckType(Enum):
    """Classification of performance bottleneck root causes."""
    CPU_BOUND = "cpu_bound"
    GPU_BOUND = "gpu_bound"
    MEMORY_BOUND = "memory_bound"
    IO_BOUND = "io_bound"
    NETWORK_BOUND = "network_bound"
    BALANCED = "balanced"


class OptimizationStrategy(Enum):
    """Available optimization techniques for resolving bottlenecks."""
    BATCH_PROCESSING = "batch_processing"
    OBJECT_POOLING = "object_pooling"
    LOD_OPTIMIZATION = "lod_optimization"
    CULLING = "culling"
    MEMORY_COMPACTION = "memory_compaction"
    LOAD_BALANCING = "load_balancing"
    CACHE_OPTIMIZATION = "cache_optimization"
    ASYNC_OPERATION = "async_operation"


class SeverityLevel(Enum):
    """Severity of performance issues and optimization urgency."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"

    @property
    def numeric_priority(self) -> int:
        mapping = {
            SeverityLevel.CRITICAL: 0,
            SeverityLevel.HIGH: 1,
            SeverityLevel.MEDIUM: 2,
            SeverityLevel.LOW: 3,
            SeverityLevel.INFO: 4,
        }
        return mapping[self]


# ---------------------------------------------------------------------------
# Domain-to-Bottleneck Mapping
# ---------------------------------------------------------------------------

_DOMAIN_BOTTLENECK_MAP: Dict[MetricDomain, BottleneckType] = {
    MetricDomain.FRAME_RATE: BottleneckType.GPU_BOUND,
    MetricDomain.MEMORY: BottleneckType.MEMORY_BOUND,
    MetricDomain.CPU: BottleneckType.CPU_BOUND,
    MetricDomain.GPU: BottleneckType.GPU_BOUND,
    MetricDomain.NETWORK: BottleneckType.NETWORK_BOUND,
    MetricDomain.IO: BottleneckType.IO_BOUND,
    MetricDomain.PHYSICS: BottleneckType.CPU_BOUND,
    MetricDomain.AI: BottleneckType.CPU_BOUND,
    MetricDomain.RENDERING: BottleneckType.GPU_BOUND,
    MetricDomain.AUDIO: BottleneckType.CPU_BOUND,
}


# ---------------------------------------------------------------------------
# Optimization Strategy Templates
# ---------------------------------------------------------------------------

_STRATEGY_TEMPLATES: Dict[OptimizationStrategy, Dict[str, Any]] = {
    OptimizationStrategy.BATCH_PROCESSING: {
        "description": "Combine multiple small operations into larger batches to reduce overhead.",
        "estimated_improvement": 15.0,
        "complexity": "medium",
        "risk_level": "low",
        "prerequisites": ["Identify compatible operations", "Analyze batch size trade-offs"],
    },
    OptimizationStrategy.OBJECT_POOLING: {
        "description": "Pre-allocate and reuse objects instead of frequent allocation/deallocation.",
        "estimated_improvement": 20.0,
        "complexity": "medium",
        "risk_level": "low",
        "prerequisites": ["Identify frequently created/destroyed objects", "Design pool lifecycle"],
    },
    OptimizationStrategy.LOD_OPTIMIZATION: {
        "description": "Use lower-detail models for distant objects to reduce rendering load.",
        "estimated_improvement": 25.0,
        "complexity": "high",
        "risk_level": "medium",
        "prerequisites": ["Generate LOD meshes", "Configure distance thresholds"],
    },
    OptimizationStrategy.CULLING: {
        "description": "Skip rendering or processing of objects outside the visible area.",
        "estimated_improvement": 30.0,
        "complexity": "medium",
        "risk_level": "low",
        "prerequisites": ["Implement frustum/occlusion culling", "Spatial data structure"],
    },
    OptimizationStrategy.MEMORY_COMPACTION: {
        "description": "Reorganize memory layout to reduce fragmentation and improve cache locality.",
        "estimated_improvement": 10.0,
        "complexity": "high",
        "risk_level": "high",
        "prerequisites": ["Profile memory allocation patterns", "Design custom allocator"],
    },
    OptimizationStrategy.LOAD_BALANCING: {
        "description": "Distribute workload evenly across available CPU cores or threads.",
        "estimated_improvement": 20.0,
        "complexity": "medium",
        "risk_level": "medium",
        "prerequisites": ["Identify parallelizable workloads", "Implement task scheduler"],
    },
    OptimizationStrategy.CACHE_OPTIMIZATION: {
        "description": "Improve data access patterns to maximize CPU cache utilization.",
        "estimated_improvement": 15.0,
        "complexity": "high",
        "risk_level": "medium",
        "prerequisites": ["Profile cache misses", "Reorganize data structures"],
    },
    OptimizationStrategy.ASYNC_OPERATION: {
        "description": "Move blocking operations to asynchronous execution paths.",
        "estimated_improvement": 20.0,
        "complexity": "medium",
        "risk_level": "medium",
        "prerequisites": ["Identify blocking calls", "Implement async patterns"],
    },
}


# ===========================================================================
# Dataclasses
# ===========================================================================


@dataclass
class PerformanceMetric:
    """A single performance measurement recorded at a point in time."""

    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    domain: MetricDomain = MetricDomain.FRAME_RATE
    name: str = ""
    value: float = 0.0
    unit: str = ""
    threshold_warning: float = 0.0
    threshold_critical: float = 0.0
    timestamp: str = field(
        default_factory=lambda: datetime.utcnow().isoformat() + "Z"
    )
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "domain": self.domain.value,
            "name": self.name,
            "value": self.value,
            "unit": self.unit,
            "threshold_warning": self.threshold_warning,
            "threshold_critical": self.threshold_critical,
            "timestamp": self.timestamp,
            "metadata": self.metadata,
        }


@dataclass
class Bottleneck:
    """A detected performance bottleneck within a specific domain."""

    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    bottleneck_type: BottleneckType = BottleneckType.BALANCED
    domain: MetricDomain = MetricDomain.FRAME_RATE
    severity: SeverityLevel = SeverityLevel.MEDIUM
    description: str = ""
    affected_systems: List[str] = field(default_factory=list)
    impact_score: float = 0.0
    detected_at: str = field(
        default_factory=lambda: datetime.utcnow().isoformat() + "Z"
    )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "bottleneck_type": self.bottleneck_type.value,
            "domain": self.domain.value,
            "severity": self.severity.value,
            "description": self.description,
            "affected_systems": self.affected_systems,
            "impact_score": round(self.impact_score, 2),
            "detected_at": self.detected_at,
        }


@dataclass
class OptimizationSuggestion:
    """An AI-driven recommendation for resolving a performance bottleneck."""

    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    strategy: OptimizationStrategy = OptimizationStrategy.BATCH_PROCESSING
    target_system: str = ""
    description: str = ""
    estimated_improvement: float = 0.0
    complexity: str = "medium"
    risk_level: str = "low"
    prerequisites: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "strategy": self.strategy.value,
            "target_system": self.target_system,
            "description": self.description[:200],
            "estimated_improvement": round(self.estimated_improvement, 1),
            "complexity": self.complexity,
            "risk_level": self.risk_level,
            "prerequisites": self.prerequisites,
        }


@dataclass
class PerformanceSnapshot:
    """A point-in-time capture of overall game engine performance."""

    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    metrics: List[str] = field(default_factory=list)
    bottlenecks: List[str] = field(default_factory=list)
    fps: float = 0.0
    frame_time: float = 0.0
    memory_usage: float = 0.0
    cpu_usage: float = 0.0
    gpu_usage: float = 0.0
    timestamp: str = field(
        default_factory=lambda: datetime.utcnow().isoformat() + "Z"
    )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "metric_count": len(self.metrics),
            "bottleneck_count": len(self.bottlenecks),
            "fps": round(self.fps, 1),
            "frame_time": round(self.frame_time, 2),
            "memory_usage": round(self.memory_usage, 1),
            "cpu_usage": round(self.cpu_usage, 1),
            "gpu_usage": round(self.gpu_usage, 1),
            "timestamp": self.timestamp,
        }


@dataclass
class OptimizationReport:
    """A comprehensive optimization analysis and recommendation report."""

    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    snapshot_id: str = ""
    suggestions: List[str] = field(default_factory=list)
    overall_score: float = 0.0
    generated_at: str = field(
        default_factory=lambda: datetime.utcnow().isoformat() + "Z"
    )
    summary: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "snapshot_id": self.snapshot_id,
            "suggestion_count": len(self.suggestions),
            "overall_score": round(self.overall_score, 2),
            "generated_at": self.generated_at,
            "summary": self.summary[:300],
        }


# ===========================================================================
# Performance Optimizer Engine
# ===========================================================================


class PerformanceOptimizerEngine:
    """AI-driven performance optimization engine for the SparkLabs game engine.

    Monitors game runtime performance metrics, detects bottlenecks across
    multiple domains, and generates optimization recommendations.
    Supports named instances for multi-environment monitoring.
    """

    _instances: Dict[str, "PerformanceOptimizerEngine"] = {}
    _lock = threading.RLock()

    _DEFAULT_MAX_METRICS: int = 500
    _DEFAULT_MAX_BOTTLENECKS: int = 200
    _DEFAULT_MAX_SUGGESTIONS: int = 300
    _DEFAULT_MAX_SNAPSHOTS: int = 100
    _DEFAULT_MAX_REPORTS: int = 50

    def __init__(self, name: str = "default") -> None:
        self._name: str = name
        self._max_metrics: int = self._DEFAULT_MAX_METRICS
        self._metrics: Dict[str, PerformanceMetric] = {}
        self._metrics_by_domain: Dict[MetricDomain, List[str]] = defaultdict(list)
        self._bottlenecks: Dict[str, Bottleneck] = {}
        self._suggestions: Dict[str, OptimizationSuggestion] = {}
        self._suggestions_by_bottleneck: Dict[str, List[str]] = defaultdict(list)
        self._snapshots: Dict[str, PerformanceSnapshot] = {}
        self._reports: Dict[str, OptimizationReport] = {}
        self._applied_suggestions: List[str] = []
        self._stats: Dict[str, Any] = {
            "total_metrics_recorded": 0,
            "total_bottlenecks_detected": 0,
            "total_suggestions_generated": 0,
            "total_snapshots_taken": 0,
            "total_reports_generated": 0,
            "total_suggestions_applied": 0,
        }

    # ------------------------------------------------------------------
    # Singleton Access
    # ------------------------------------------------------------------

    @classmethod
    def get_instance(cls, name: str = "default") -> "PerformanceOptimizerEngine":
        """Get or create a named PerformanceOptimizerEngine instance.

        Uses double-checked locking for thread-safe singleton access.
        Each unique name creates a separate engine instance, allowing
        distinct monitoring environments (e.g., development, staging,
        production).
        """
        if name not in cls._instances:
            with cls._lock:
                if name not in cls._instances:
                    cls._instances[name] = cls(name=name)
        return cls._instances[name]

    # ------------------------------------------------------------------
    # Metric Recording
    # ------------------------------------------------------------------

    def record_metric(
        self,
        domain: MetricDomain,
        name: str,
        value: float,
        unit: str = "",
        threshold_warning: float = 0.0,
        threshold_critical: float = 0.0,
    ) -> PerformanceMetric:
        """Record a single performance metric measurement.

        Args:
            domain: The performance domain this metric belongs to.
            name: Human-readable metric name.
            value: The measured numeric value.
            unit: Unit of measurement (e.g., "ms", "MB", "%").
            threshold_warning: Warning-level threshold value.
            threshold_critical: Critical-level threshold value.

        Returns:
            The created PerformanceMetric instance.
        """
        metric = PerformanceMetric(
            domain=domain,
            name=name,
            value=value,
            unit=unit,
            threshold_warning=threshold_warning,
            threshold_critical=threshold_critical,
        )

        with self._lock:
            self._metrics[metric.id] = metric
            self._metrics_by_domain[domain].append(metric.id)
            self._stats["total_metrics_recorded"] += 1

            # Enforce max metrics limit
            if len(self._metrics) > self._max_metrics:
                self._evict_oldest_metrics()

        return metric

    def _evict_oldest_metrics(self) -> None:
        """Remove the oldest metrics when the collection exceeds the limit."""
        if not self._metrics:
            return
        sorted_ids = sorted(
            self._metrics.keys(),
            key=lambda mid: self._metrics[mid].timestamp,
        )
        excess = len(self._metrics) - self._max_metrics
        for metric_id in sorted_ids[:excess]:
            metric = self._metrics.pop(metric_id, None)
            if metric:
                domain_list = self._metrics_by_domain.get(metric.domain, [])
                if metric_id in domain_list:
                    domain_list.remove(metric_id)

    # ------------------------------------------------------------------
    # Bottleneck Detection
    # ------------------------------------------------------------------

    def detect_bottlenecks(self) -> List[Bottleneck]:
        """Analyze recorded metrics and detect performance bottlenecks.

        Compares each metric against its warning and critical thresholds
        to determine severity. Metrics exceeding critical thresholds
        produce CRITICAL bottlenecks; those exceeding warning thresholds
        produce HIGH bottlenecks; borderline cases produce MEDIUM.

        Returns:
            List of detected Bottleneck instances.
        """
        bottlenecks: List[Bottleneck] = []

        with self._lock:
            for metric in self._metrics.values():
                severity: Optional[SeverityLevel] = None

                if metric.threshold_critical > 0 and metric.value >= metric.threshold_critical:
                    severity = SeverityLevel.CRITICAL
                elif metric.threshold_warning > 0 and metric.value >= metric.threshold_warning:
                    severity = SeverityLevel.HIGH
                elif metric.threshold_warning > 0 and metric.value >= metric.threshold_warning * 0.8:
                    severity = SeverityLevel.MEDIUM
                elif metric.threshold_warning > 0 and metric.value >= metric.threshold_warning * 0.5:
                    severity = SeverityLevel.LOW
                else:
                    continue

                bottleneck_type = _DOMAIN_BOTTLENECK_MAP.get(
                    metric.domain, BottleneckType.BALANCED
                )

                overhead_pct = (
                    (metric.value / metric.threshold_critical * 100)
                    if metric.threshold_critical > 0
                    else (metric.value / max(metric.threshold_warning, 0.001) * 100)
                )

                impact_score = min(100.0, max(0.0, overhead_pct))

                bottleneck = Bottleneck(
                    bottleneck_type=bottleneck_type,
                    domain=metric.domain,
                    severity=severity,
                    description=(
                        f"{metric.name}: {metric.value}{metric.unit} "
                        f"(warning: {metric.threshold_warning}{metric.unit}, "
                        f"critical: {metric.threshold_critical}{metric.unit})"
                    ),
                    affected_systems=[metric.name],
                    impact_score=impact_score,
                )

                self._bottlenecks[bottleneck.id] = bottleneck
                bottlenecks.append(bottleneck)
                self._stats["total_bottlenecks_detected"] += 1

            # Enforce max bottlenecks limit
            if len(self._bottlenecks) > self._DEFAULT_MAX_BOTTLENECKS:
                self._evict_oldest_bottlenecks()

        return bottlenecks

    def _evict_oldest_bottlenecks(self) -> None:
        """Remove the oldest bottlenecks when the collection exceeds the limit."""
        if not self._bottlenecks:
            return
        sorted_ids = sorted(
            self._bottlenecks.keys(),
            key=lambda bid: self._bottlenecks[bid].detected_at,
        )
        excess = len(self._bottlenecks) - self._DEFAULT_MAX_BOTTLENECKS
        for bottleneck_id in sorted_ids[:excess]:
            self._bottlenecks.pop(bottleneck_id, None)

    # ------------------------------------------------------------------
    # Suggestion Generation
    # ------------------------------------------------------------------

    def generate_suggestions(
        self, bottleneck_id: str = ""
    ) -> List[OptimizationSuggestion]:
        """Generate optimization suggestions for a detected bottleneck.

        Uses AI-driven strategy selection based on the bottleneck type
        and domain. If no bottleneck_id is provided, generates suggestions
        for all undiagnosed bottlenecks.

        Args:
            bottleneck_id: The ID of the bottleneck to address, or empty
                           string to generate suggestions for all bottlenecks.

        Returns:
            List of OptimizationSuggestion instances.
        """
        suggestions: List[OptimizationSuggestion] = []

        if bottleneck_id:
            target_bottlenecks = [self._bottlenecks.get(bottleneck_id)]
        else:
            target_bottlenecks = list(self._bottlenecks.values())

        with self._lock:
            for bottleneck in target_bottlenecks:
                if bottleneck is None:
                    continue

                strategies = self._select_strategies(bottleneck)

                for strategy in strategies:
                    template = _STRATEGY_TEMPLATES.get(strategy, {})
                    suggestion = OptimizationSuggestion(
                        strategy=strategy,
                        target_system=bottleneck.domain.value,
                        description=template.get("description", ""),
                        estimated_improvement=template.get("estimated_improvement", 0.0),
                        complexity=template.get("complexity", "medium"),
                        risk_level=template.get("risk_level", "low"),
                        prerequisites=list(template.get("prerequisites", [])),
                    )

                    self._suggestions[suggestion.id] = suggestion
                    self._suggestions_by_bottleneck[bottleneck.id].append(suggestion.id)
                    suggestions.append(suggestion)
                    self._stats["total_suggestions_generated"] += 1

            # Enforce max suggestions limit
            if len(self._suggestions) > self._DEFAULT_MAX_SUGGESTIONS:
                self._evict_oldest_suggestions()

        return suggestions

    def _select_strategies(
        self, bottleneck: Bottleneck
    ) -> List[OptimizationStrategy]:
        """Select appropriate optimization strategies for a bottleneck type.

        Args:
            bottleneck: The bottleneck to analyze.

        Returns:
            List of applicable OptimizationStrategy values.
        """
        strategy_map: Dict[BottleneckType, List[OptimizationStrategy]] = {
            BottleneckType.CPU_BOUND: [
                OptimizationStrategy.ASYNC_OPERATION,
                OptimizationStrategy.LOAD_BALANCING,
                OptimizationStrategy.CACHE_OPTIMIZATION,
            ],
            BottleneckType.GPU_BOUND: [
                OptimizationStrategy.CULLING,
                OptimizationStrategy.LOD_OPTIMIZATION,
                OptimizationStrategy.BATCH_PROCESSING,
            ],
            BottleneckType.MEMORY_BOUND: [
                OptimizationStrategy.MEMORY_COMPACTION,
                OptimizationStrategy.OBJECT_POOLING,
            ],
            BottleneckType.IO_BOUND: [
                OptimizationStrategy.ASYNC_OPERATION,
                OptimizationStrategy.CACHE_OPTIMIZATION,
            ],
            BottleneckType.NETWORK_BOUND: [
                OptimizationStrategy.ASYNC_OPERATION,
                OptimizationStrategy.BATCH_PROCESSING,
            ],
            BottleneckType.BALANCED: [
                OptimizationStrategy.BATCH_PROCESSING,
            ],
        }
        return strategy_map.get(bottleneck.bottleneck_type, [])

    def _evict_oldest_suggestions(self) -> None:
        """Remove the oldest suggestions when the collection exceeds the limit."""
        if not self._suggestions:
            return
        # Use ID as a proxy for creation order (hex UUIDs are time-based)
        sorted_ids = sorted(self._suggestions.keys())
        excess = len(self._suggestions) - self._DEFAULT_MAX_SUGGESTIONS
        for suggestion_id in sorted_ids[:excess]:
            self._suggestions.pop(suggestion_id, None)

    # ------------------------------------------------------------------
    # Snapshot
    # ------------------------------------------------------------------

    def take_snapshot(self) -> PerformanceSnapshot:
        """Capture a point-in-time performance snapshot of the engine.

        Aggregates current metrics and bottlenecks into a single
        snapshot with computed FPS, frame time, memory, CPU, and
        GPU usage values.

        Returns:
            A PerformanceSnapshot with current engine state.
        """
        with self._lock:
            metric_ids = list(self._metrics.keys())
            bottleneck_ids = list(self._bottlenecks.keys())

            fps, frame_time = self._compute_fps()
            memory_usage = self._compute_domain_average(MetricDomain.MEMORY)
            cpu_usage = self._compute_domain_average(MetricDomain.CPU)
            gpu_usage = self._compute_domain_average(MetricDomain.GPU)

            snapshot = PerformanceSnapshot(
                metrics=metric_ids,
                bottlenecks=bottleneck_ids,
                fps=fps,
                frame_time=frame_time,
                memory_usage=memory_usage,
                cpu_usage=cpu_usage,
                gpu_usage=gpu_usage,
            )

            self._snapshots[snapshot.id] = snapshot
            self._stats["total_snapshots_taken"] += 1

            # Enforce max snapshots limit
            if len(self._snapshots) > self._DEFAULT_MAX_SNAPSHOTS:
                self._evict_oldest_snapshots()

        return snapshot

    def _compute_fps(self) -> tuple:
        """Compute current FPS and frame time from recorded metrics."""
        frame_metrics = self._metrics_by_domain.get(MetricDomain.FRAME_RATE, [])
        if not frame_metrics:
            return (0.0, 0.0)

        values = []
        for mid in frame_metrics[-10:]:
            metric = self._metrics.get(mid)
            if metric:
                values.append(metric.value)

        if not values:
            return (0.0, 0.0)

        avg_frame_time = sum(values) / len(values)
        fps = 1000.0 / max(avg_frame_time, 0.001)
        return (fps, avg_frame_time)

    def _compute_domain_average(self, domain: MetricDomain) -> float:
        """Compute the average value for metrics in a given domain."""
        domain_metrics = self._metrics_by_domain.get(domain, [])
        if not domain_metrics:
            return 0.0

        values = []
        for mid in domain_metrics[-20:]:
            metric = self._metrics.get(mid)
            if metric:
                values.append(metric.value)

        if not values:
            return 0.0

        return sum(values) / len(values)

    def _evict_oldest_snapshots(self) -> None:
        """Remove the oldest snapshots when the collection exceeds the limit."""
        if not self._snapshots:
            return
        sorted_ids = sorted(
            self._snapshots.keys(),
            key=lambda sid: self._snapshots[sid].timestamp,
        )
        excess = len(self._snapshots) - self._DEFAULT_MAX_SNAPSHOTS
        for snapshot_id in sorted_ids[:excess]:
            self._snapshots.pop(snapshot_id, None)

    # ------------------------------------------------------------------
    # Report Generation
    # ------------------------------------------------------------------

    def generate_report(self) -> OptimizationReport:
        """Generate a comprehensive optimization report.

        Takes a snapshot of current performance state, analyzes all
        bottlenecks, generates suggestions, and produces a scored
        report with a human-readable summary.

        Returns:
            An OptimizationReport with overall score and suggestions.
        """
        snapshot = self.take_snapshot()
        bottlenecks = self.detect_bottlenecks()
        all_suggestions: List[OptimizationSuggestion] = []

        for bottleneck in bottlenecks:
            suggestions = self.generate_suggestions(bottleneck.id)
            all_suggestions.extend(suggestions)

        suggestion_ids = [s.id for s in all_suggestions]

        overall_score = self._compute_overall_score(snapshot, bottlenecks)

        summary_parts: List[str] = []
        if bottlenecks:
            severity_counts: Dict[str, int] = defaultdict(int)
            for b in bottlenecks:
                severity_counts[b.severity.value] += 1
            summary_parts.append(
                f"Detected {len(bottlenecks)} bottlenecks: "
                + ", ".join(f"{v} {k}" for k, v in sorted(severity_counts.items()))
            )
        else:
            summary_parts.append("No bottlenecks detected. Performance is healthy.")

        if all_suggestions:
            summary_parts.append(
                f"Generated {len(all_suggestions)} optimization suggestions."
            )

        report = OptimizationReport(
            snapshot_id=snapshot.id,
            suggestions=suggestion_ids,
            overall_score=overall_score,
            summary=" ".join(summary_parts),
        )

        with self._lock:
            self._reports[report.id] = report
            self._stats["total_reports_generated"] += 1

            # Enforce max reports limit
            if len(self._reports) > self._DEFAULT_MAX_REPORTS:
                self._evict_oldest_reports()

        return report

    def _compute_overall_score(
        self,
        snapshot: PerformanceSnapshot,
        bottlenecks: List[Bottleneck],
    ) -> float:
        """Compute an overall performance score from 0.0 (worst) to 100.0 (best).

        Factors in bottleneck severity, count, and impact scores to
        produce a normalized health score.
        """
        if not bottlenecks:
            return 100.0

        severity_weights = {
            SeverityLevel.CRITICAL: 0.25,
            SeverityLevel.HIGH: 0.20,
            SeverityLevel.MEDIUM: 0.15,
            SeverityLevel.LOW: 0.10,
            SeverityLevel.INFO: 0.05,
        }

        total_penalty = 0.0
        for b in bottlenecks:
            weight = severity_weights.get(b.severity, 0.05)
            total_penalty += weight * (b.impact_score / 100.0)

        total_penalty = min(total_penalty, 1.0)
        return round(100.0 * (1.0 - total_penalty), 2)

    def _evict_oldest_reports(self) -> None:
        """Remove the oldest reports when the collection exceeds the limit."""
        if not self._reports:
            return
        sorted_ids = sorted(
            self._reports.keys(),
            key=lambda rid: self._reports[rid].generated_at,
        )
        excess = len(self._reports) - self._DEFAULT_MAX_REPORTS
        for report_id in sorted_ids[:excess]:
            self._reports.pop(report_id, None)

    # ------------------------------------------------------------------
    # Query Methods
    # ------------------------------------------------------------------

    def get_metric_history(
        self, domain: MetricDomain, limit: int = 50
    ) -> List[PerformanceMetric]:
        """Retrieve recent metric history for a specific domain.

        Args:
            domain: The performance domain to query.
            limit: Maximum number of metrics to return.

        Returns:
            List of PerformanceMetric instances, most recent first.
        """
        with self._lock:
            metric_ids = self._metrics_by_domain.get(domain, [])
            metrics = [
                self._metrics[mid]
                for mid in metric_ids[-limit:]
                if mid in self._metrics
            ]
            metrics.reverse()
        return metrics

    def get_snapshot(self, snapshot_id: str) -> Optional[PerformanceSnapshot]:
        """Retrieve a specific snapshot by ID."""
        return self._snapshots.get(snapshot_id)

    def get_report(self, report_id: str) -> Optional[OptimizationReport]:
        """Retrieve a specific report by ID."""
        return self._reports.get(report_id)

    def get_bottleneck(self, bottleneck_id: str) -> Optional[Bottleneck]:
        """Retrieve a specific bottleneck by ID."""
        return self._bottlenecks.get(bottleneck_id)

    def get_suggestion(self, suggestion_id: str) -> Optional[OptimizationSuggestion]:
        """Retrieve a specific suggestion by ID."""
        return self._suggestions.get(suggestion_id)

    # ------------------------------------------------------------------
    # Suggestion Application
    # ------------------------------------------------------------------

    def apply_suggestion(self, suggestion_id: str) -> bool:
        """Mark an optimization suggestion as applied.

        Args:
            suggestion_id: The ID of the suggestion to apply.

        Returns:
            True if the suggestion was found and applied, False otherwise.
        """
        with self._lock:
            suggestion = self._suggestions.get(suggestion_id)
            if suggestion is None:
                return False
            if suggestion_id in self._applied_suggestions:
                return False
            self._applied_suggestions.append(suggestion_id)
            self._stats["total_suggestions_applied"] += 1
        return True

    # ------------------------------------------------------------------
    # Stats & Reset
    # ------------------------------------------------------------------

    def get_stats(self) -> dict:
        """Return comprehensive engine statistics.

        Returns:
            Dictionary with current engine state and cumulative counters.
        """
        with self._lock:
            domain_distribution: Dict[str, int] = defaultdict(int)
            for metric in self._metrics.values():
                domain_distribution[metric.domain.value] += 1

            severity_distribution: Dict[str, int] = defaultdict(int)
            for bottleneck in self._bottlenecks.values():
                severity_distribution[bottleneck.severity.value] += 1

            strategy_distribution: Dict[str, int] = defaultdict(int)
            for suggestion in self._suggestions.values():
                strategy_distribution[suggestion.strategy.value] += 1

            return {
                "name": self._name,
                "metrics_count": len(self._metrics),
                "bottlenecks_count": len(self._bottlenecks),
                "suggestions_count": len(self._suggestions),
                "snapshots_count": len(self._snapshots),
                "reports_count": len(self._reports),
                "applied_suggestions": len(self._applied_suggestions),
                "domain_distribution": dict(domain_distribution),
                "severity_distribution": dict(severity_distribution),
                "strategy_distribution": dict(strategy_distribution),
                "max_metrics": self._max_metrics,
                **self._stats,
            }

    def reset(self) -> None:
        """Reset all internal state, clearing metrics, bottlenecks,
        suggestions, snapshots, reports, and statistics counters."""
        with self._lock:
            self._metrics.clear()
            self._metrics_by_domain.clear()
            self._bottlenecks.clear()
            self._suggestions.clear()
            self._suggestions_by_bottleneck.clear()
            self._snapshots.clear()
            self._reports.clear()
            self._applied_suggestions.clear()
            self._stats = {
                "total_metrics_recorded": 0,
                "total_bottlenecks_detected": 0,
                "total_suggestions_generated": 0,
                "total_snapshots_taken": 0,
                "total_reports_generated": 0,
                "total_suggestions_applied": 0,
            }


# ===========================================================================
# Module-Level Getter
# ===========================================================================


def get_performance_optimizer(
    name: str = "default",
) -> PerformanceOptimizerEngine:
    """Get or create a named PerformanceOptimizerEngine instance.

    Args:
        name: Identifier for the optimizer instance. Create distinct
              instances for different environments (e.g., "development",
              "staging", "production").

    Returns:
        A PerformanceOptimizerEngine singleton for the given name.
    """
    return PerformanceOptimizerEngine.get_instance(name=name)