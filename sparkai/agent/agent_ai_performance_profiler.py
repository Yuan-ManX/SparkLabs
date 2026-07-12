"""
SparkLabs Agent - AI Performance Profiler

A comprehensive AI-driven performance profiling agent for the SparkLabs
AI-native game engine. The profiler continuously monitors CPU, GPU, memory,
render, physics, audio, IO, network, script, and AI subsystems; identifies
bottlenecks through threshold-based and statistical analysis; generates
targeted optimization suggestions; and can automatically apply and revert
optimizations while measuring their real impact.

The agent combines real-time frame-by-frame profiling with AI-driven
diagnosis. Bottlenecks are not merely flagged; they are correlated with
hotspots, ranked by impact, and paired with concrete optimization plans
spanning caching, batching, level-of-detail, culling, streaming, deferral,
parallelism, compression, merging, splitting, reordering, and precomputation.

Architecture:
  AIPerformanceProfiler (singleton)
    |-- ProfileSample, Bottleneck, OptimizationSuggestion, ProfileSession,
        FrameMetrics, Hotspot, PerformanceBaseline, OptimizationResult,
        ProfilerConfig, ProfilerStats, ProfilerSnapshot, ProfilerEvent
    |-- ProfileCategory, BottleneckSeverity, OptimizationType, ProfileStatus,
        MetricType, OptimizationStatus, ProfileSessionType, HotspotType

Core Capabilities:
  - start_session / stop_session / get_session / list_sessions /
    remove_session: profiling session lifecycle with continuous, snapshot,
    benchmark, stress-test, and comparison modes.
  - record_sample / get_sample / list_samples / remove_sample: low-level
    metric sample ingestion across all subsystem categories.
  - identify_bottleneck / get_bottleneck / list_bottlenecks /
    remove_bottleneck: threshold-driven bottleneck detection that escalates
    severity based on how far a metric exceeds its budget.
  - suggest_optimization / get_optimization / list_optimizations /
    remove_optimization: AI-generated optimization plans tied to bottlenecks,
    each carrying expected gain, risk, effort, and confidence.
  - apply_optimization / revert_optimization: execute optimizations, measure
    before/after deltas, and roll back changes that regress performance.
  - record_frame_metrics / get_frame_metrics: per-frame telemetry capture that
    feeds trend analysis and performance prediction.
  - register_hotspot / get_hotspot / list_hotspots / remove_hotspot:
    code-level hot region tracking that explains where time is spent inside
    a frame.
  - create_baseline / get_baseline / list_baselines / compare_baselines:
    performance baselines for regression detection and build-to-build
    comparison.
  - auto_diagnose: holistic AI diagnosis that ranks bottlenecks, infers root
    causes from hotspot correlation, and produces a health score.
  - auto_optimize: automatically applies the highest-impact pending
    optimizations that clear the configured confidence threshold.
  - predict_performance: linear-regression projection of frame time, FPS,
    memory, and draw calls over a future horizon.
  - list_events / get_status / get_stats / get_snapshot / get_config /
    set_config / tick / reset: observability, tuning, and lifecycle control.

The class implements the singleton pattern with double-checked locking
using ``threading.RLock``; consumers should obtain the instance through
:meth:`AIPerformanceProfiler.get_instance` or the module-level
:func:`get_ai_performance_profiler` factory.
"""

from __future__ import annotations

import math
import threading
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Capacity Constants
# ---------------------------------------------------------------------------

_MAX_PROFILES: int = 50000
_MAX_SESSIONS: int = 2000
_MAX_SAMPLES: int = 50000
_MAX_BOTTLENECKS: int = 20000
_MAX_OPTIMIZATIONS: int = 20000
_MAX_RESULTS: int = 20000
_MAX_HOTSPOTS: int = 10000
_MAX_BASELINES: int = 2000
_MAX_FRAME_METRICS: int = 60000
_MAX_EVENTS: int = 20000

# Scoring and severity bounds.
_IMPACT_MIN: float = 0.0
_IMPACT_MAX: float = 1.0
_CONFIDENCE_MIN: float = 0.0
_CONFIDENCE_MAX: float = 1.0
_HEALTH_MIN: float = 0.0
_HEALTH_MAX: float = 100.0

# Severity weight used when computing a composite health score. Higher
# severities contribute more penalty.
_SEVERITY_WEIGHTS: Dict[str, float] = {
    "info": 0.02,
    "low": 0.08,
    "medium": 0.18,
    "high": 0.32,
    "critical": 0.55,
    "blocking": 0.85,
}

# Per-metric budget thresholds. Each entry maps a metric type to a tuple of
# (threshold_value, comparison_operator, default_severity). A sample whose
# value crosses the threshold is flagged as a bottleneck, with severity
# escalated based on the overshoot ratio.
_METRIC_THRESHOLDS: Dict[str, Tuple[float, str, str]] = {
    "frame_time": (16.6, ">", "low"),        # ms; 16.6ms ~= 60 FPS budget
    "gpu_time": (16.6, ">", "low"),
    "cpu_time": (16.6, ">", "low"),
    "draw_calls": (2000.0, ">", "low"),
    "triangles": (3_000_000.0, ">", "low"),
    "vertices": (3_000_000.0, ">", "low"),
    "memory_usage": (2048.0, ">", "medium"),  # MB
    "network_latency": (80.0, ">", "medium"),  # ms
    "io_time": (8.0, ">", "low"),
    "script_time": (6.0, ">", "low"),
    "physics_time": (5.0, ">", "low"),
    "audio_time": (3.0, ">", "low"),
    "render_time": (10.0, ">", "low"),
}

# Default metric type associated with each profiling category. Used when a
# bottleneck or sample is created without an explicit metric.
_CATEGORY_DEFAULT_METRIC: Dict[str, str] = {
    "cpu": "cpu_time",
    "gpu": "gpu_time",
    "memory": "memory_usage",
    "network": "network_latency",
    "render": "render_time",
    "physics": "physics_time",
    "audio": "audio_time",
    "io": "io_time",
    "script": "script_time",
    "loading": "io_time",
    "input": "frame_time",
    "ai": "script_time",
}

# Optimization templates keyed by profiling category. Each template is a tuple
# of (optimization_type, title, description, expected_gain, risk_level,
# effort_level). The suggest_optimization AI pass draws from this table.
_OPTIMIZATION_TEMPLATES: Dict[str, List[Tuple[str, str, str, float, str, str]]] = {
    "cpu": [
        ("cache", "Cache repeated computations",
         "Memoize transform and physics queries that return identical results "
         "across consecutive frames so the hot loop avoids redundant work.",
         0.18, "low", "low"),
        ("parallel", "Parallelize independent systems",
         "Move independent update systems such as AI thinking and animation "
         "sampling onto worker threads to distribute CPU load.",
         0.30, "medium", "medium"),
        ("precompute", "Precompute static lookup tables",
         "Build lookup tables for trigonometric and AI utility functions at "
         "startup so the hot loop avoids repeated transcendental calls.",
         0.12, "low", "low"),
        ("reorder", "Reorder update phases",
         "Reschedule systems so cache-friendly contiguous work runs before "
         "scattered pointer-chasing work, improving cache locality.",
         0.08, "low", "low"),
    ],
    "gpu": [
        ("batch", "Batch draw calls by material",
         "Group render items sharing the same material and shader permutation "
         "into instanced draw calls to reduce GPU submission overhead.",
         0.25, "low", "medium"),
        ("lod", "Apply distance-based level of detail",
         "Swap high-poly meshes for lower-detail variants past a distance "
         "threshold to cut triangle throughput pressure.",
         0.22, "low", "low"),
        ("cull", "Tighten frustum and occlusion culling",
         "Add hierarchical z occlusion culling and conservative frustum tests "
         "so off-screen geometry is never submitted to the GPU.",
         0.20, "low", "low"),
        ("compress", "Use block-compressed textures",
         "Convert uncompressed textures to BCn or ASTC block formats to "
         "shrink GPU memory bandwidth and footprint.",
         0.15, "low", "low"),
    ],
    "render": [
        ("batch", "Batch draw calls by material",
         "Group render items sharing the same material into instanced draws "
         "to cut per-draw overhead on the render path.",
         0.25, "low", "medium"),
        ("cull", "Tighten frustum and occlusion culling",
         "Add occlusion culling so only visible geometry reaches the render "
         "queue, reducing overdraw and submission cost.",
         0.20, "low", "low"),
        ("lod", "Apply distance-based level of detail",
         "Reduce polygon count for distant objects to lower render time and "
         "triangle throughput.",
         0.18, "low", "low"),
        ("reorder", "Sort render queue front-to-back",
         "Submit opaque geometry front-to-back so the depth test rejects "
         "occluded fragments early and saves pixel shader work.",
         0.10, "low", "low"),
    ],
    "memory": [
        ("stream", "Stream large assets on demand",
         "Page large textures and meshes in and out based on camera proximity "
         "instead of keeping them resident at all times.",
         0.28, "medium", "high"),
        ("compress", "Compress in-memory assets",
         "Apply runtime decompression for audio and animation data to lower "
         "resident memory without sacrificing playback quality.",
         0.18, "low", "medium"),
        ("merge", "Pool and merge allocations",
         "Use object pools and arena allocators to reduce fragmentation and "
         "allocation churn across frames.",
         0.15, "low", "medium"),
    ],
    "network": [
        ("batch", "Batch network messages",
         "Coalesce frequent small packets into a single aggregated send per "
         "tick to cut per-packet overhead and syscall count.",
         0.20, "low", "low"),
        ("compress", "Compress network payloads",
         "Apply delta compression and bit-packing to replicated state "
         "snapshots to reduce bandwidth and serialization cost.",
         0.15, "low", "medium"),
        ("defer", "Defer non-critical replication",
         "Lower the send rate for distant or low-priority entities and "
         "interpolate their state on the client.",
         0.18, "low", "low"),
    ],
    "physics": [
        ("split", "Split the physics island",
         "Partition the simulation into independent islands so solver "
         "iterations run on smaller contact sets.",
         0.15, "medium", "medium"),
        ("defer", "Sleep inactive rigidbodies",
         "Tighten sleep thresholds so resting bodies skip integration until "
         "they are disturbed by a contact.",
         0.12, "low", "low"),
        ("parallel", "Parallelize collision broadphase",
         "Run broadphase pair generation across worker threads before the "
         "narrowphase solve to cut single-threaded physics cost.",
         0.18, "medium", "medium"),
    ],
    "audio": [
        ("stream", "Stream audio instead of preloading",
         "Stream long music and dialogue from disk rather than holding the "
         "full clip resident in memory.",
         0.20, "low", "low"),
        ("merge", "Pool audio voices",
         "Reuse a fixed pool of voice sources to avoid allocation spikes "
         "when many sounds trigger in the same frame.",
         0.10, "low", "low"),
        ("compress", "Compress audio assets",
         "Convert uncompressed clips to a streamed compressed format to "
         "reduce memory and IO pressure.",
         0.12, "low", "low"),
    ],
    "io": [
        ("stream", "Asynchronous asset streaming",
         "Move file IO off the main thread with a priority queue so loading "
         "never stalls the simulation frame.",
         0.25, "medium", "medium"),
        ("batch", "Batch IO requests",
         "Coalesce adjacent read requests into larger sequential transfers "
         "to maximize disk throughput.",
         0.15, "low", "low"),
        ("precompute", "Pack assets into bundles",
         "Merge loose files into packed archives with a locality-optimized "
         "layout to reduce seek overhead.",
         0.12, "low", "low"),
    ],
    "script": [
        ("cache", "Cache script bindings",
         "Avoid redundant cross-boundary calls by caching native handles in "
         "script state across frames.",
         0.15, "low", "low"),
        ("defer", "Defer expensive script calls",
         "Spread heavy script logic across multiple frames using a coroutine "
         "scheduler so no single frame bears the full cost.",
         0.18, "low", "medium"),
        ("batch", "Batch script callbacks",
         "Group per-entity script updates into a single native-to-script "
         "dispatch to cut marshalling overhead.",
         0.12, "low", "low"),
    ],
    "loading": [
        ("stream", "Background loading pipeline",
         "Load level chunks in the background while the player traverses the "
         "world so loading never blocks gameplay.",
         0.30, "medium", "high"),
        ("precompute", "Prebake loading manifests",
         "Generate dependency manifests at build time so the loader fetches "
         "a single curated list instead of probing the filesystem.",
         0.10, "low", "low"),
        ("compress", "Compress packaged data",
         "Compress packaged level data so disk reads transfer fewer bytes "
         "during loading.",
         0.08, "low", "low"),
    ],
    "input": [
        ("defer", "Decouple input sampling",
         "Sample input on a high-frequency thread decoupled from the render "
         "loop to reduce perceived input latency.",
         0.10, "low", "medium"),
    ],
    "ai": [
        ("cache", "Cache AI perception queries",
         "Reuse spatial query results across nearby AI agents and consecutive "
         "frames to cut repeated navmesh and sensor work.",
         0.18, "low", "low"),
        ("lod", "AI level of detail",
         "Reduce decision frequency and planner depth for distant agents so "
         "the update budget scales with player proximity.",
         0.22, "low", "low"),
        ("split", "Distribute AI work across frames",
         "Spread AI thinkers across frames so no single frame bears the full "
         "update cost of the whole agent population.",
         0.15, "low", "medium"),
    ],
}

# Maps a hotspot type to the profiling category it most often indicates.
_HOTSPOT_CATEGORY: Dict[str, str] = {
    "render_loop": "render",
    "update_loop": "cpu",
    "script_bind": "script",
    "asset_loading": "loading",
    "memory_allocation": "memory",
    "garbage_collection": "memory",
    "thread_sync": "cpu",
    "lock_contention": "cpu",
    "cache_miss": "cpu",
    "branch_mispredict": "cpu",
}


# ---------------------------------------------------------------------------
# Helper Functions
# ---------------------------------------------------------------------------


def _now() -> str:
    return datetime.utcnow().isoformat() + "Z"


def _new_id(prefix: str = "") -> str:
    base = uuid.uuid4().hex[:12]
    return f"{prefix}_{base}" if prefix else base


def _evict_fifo_dict(store: Dict[str, Any], max_size: int) -> None:
    cap = max(1, int(max_size))
    while len(store) > cap:
        oldest_key = next(iter(store), None)
        if oldest_key is None:
            break
        store.pop(oldest_key, None)


def _evict_fifo_list(store: List[Any], max_size: int) -> None:
    cap = max(1, int(max_size))
    while len(store) > cap:
        if not store:
            break
        store.pop(0)


def _coerce_enum(enum_cls: Any, value: Any, default: Any = None) -> Any:
    if value is None:
        return default
    if isinstance(value, enum_cls):
        return value
    try:
        return enum_cls(value)
    except (ValueError, KeyError):
        return default


def _to_jsonable(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, dict):
        return {str(k): _to_jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_to_jsonable(v) for v in value]
    if hasattr(value, "__dataclass_fields__"):
        return _dataclass_to_dict(value)
    if hasattr(value, "to_dict") and callable(value.to_dict):
        return value.to_dict()
    return value


def _dataclass_to_dict(instance: Any) -> Dict[str, Any]:
    if instance is None:
        return {}
    if not hasattr(instance, "__dataclass_fields__"):
        if isinstance(instance, dict):
            return {str(k): _to_jsonable(v) for k, v in instance.items()}
        if hasattr(instance, "to_dict") and callable(instance.to_dict):
            return instance.to_dict()
        return {}
    out: Dict[str, Any] = {}
    for name in getattr(instance, "__dataclass_fields__", {}).keys():
        try:
            raw = getattr(instance, name)
        except Exception:
            continue
        out[name] = _to_jsonable(raw)
    return out


def _clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    if value < low:
        return low
    if value > high:
        return high
    return value


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None:
            return default
        f = float(value)
        if math.isnan(f) or math.isinf(f):
            return default
        return f
    except (TypeError, ValueError):
        return default


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        if value is None:
            return default
        return int(value)
    except (TypeError, ValueError):
        return default


def _mean(values: List[float]) -> float:
    if not values:
        return 0.0
    return sum(values) / len(values)


def _classify_severity(value: float, threshold: float) -> str:
    """Escalate severity based on how far a value exceeds its threshold."""
    if threshold <= 0:
        return BottleneckSeverity.INFO.value
    ratio = value / threshold
    if ratio >= 5.0:
        return BottleneckSeverity.BLOCKING.value
    if ratio >= 3.0:
        return BottleneckSeverity.CRITICAL.value
    if ratio >= 2.0:
        return BottleneckSeverity.HIGH.value
    if ratio >= 1.5:
        return BottleneckSeverity.MEDIUM.value
    if ratio >= 1.0:
        return BottleneckSeverity.LOW.value
    return BottleneckSeverity.INFO.value


def _severity_rank(severity: str) -> int:
    """Numeric rank for a severity string; higher means more severe."""
    table = {
        BottleneckSeverity.INFO.value: 0,
        BottleneckSeverity.LOW.value: 1,
        BottleneckSeverity.MEDIUM.value: 2,
        BottleneckSeverity.HIGH.value: 3,
        BottleneckSeverity.CRITICAL.value: 4,
        BottleneckSeverity.BLOCKING.value: 5,
    }
    return table.get(severity, 0)


# ---------------------------------------------------------------------------
# Domain Enums
# ---------------------------------------------------------------------------


class ProfileCategory(str, Enum):
    """Subsystem category under profiling."""

    CPU = "cpu"
    GPU = "gpu"
    MEMORY = "memory"
    NETWORK = "network"
    RENDER = "render"
    PHYSICS = "physics"
    AUDIO = "audio"
    IO = "io"
    SCRIPT = "script"
    LOADING = "loading"
    INPUT = "input"
    AI = "ai"


class BottleneckSeverity(str, Enum):
    """Severity tier assigned to an identified bottleneck."""

    INFO = "info"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"
    BLOCKING = "blocking"


class OptimizationType(str, Enum):
    """Kind of optimization suggested or applied."""

    CACHE = "cache"
    BATCH = "batch"
    LOD = "lod"
    CULL = "cull"
    STREAM = "stream"
    DEFER = "defer"
    PARALLEL = "parallel"
    COMPRESS = "compress"
    MERGE = "merge"
    SPLIT = "split"
    REORDER = "reorder"
    PRECOMPUTE = "precompute"


class ProfileStatus(str, Enum):
    """Lifecycle state of a profiling session."""

    IDLE = "idle"
    PROFILING = "profiling"
    ANALYZING = "analyzing"
    OPTIMIZING = "optimizing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class MetricType(str, Enum):
    """Quantitative metric captured by the profiler."""

    FRAME_TIME = "frame_time"
    DRAW_CALLS = "draw_calls"
    TRIANGLES = "triangles"
    VERTICES = "vertices"
    MEMORY_USAGE = "memory_usage"
    GPU_TIME = "gpu_time"
    CPU_TIME = "cpu_time"
    NETWORK_LATENCY = "network_latency"
    IO_TIME = "io_time"
    SCRIPT_TIME = "script_time"
    PHYSICS_TIME = "physics_time"
    AUDIO_TIME = "audio_time"
    RENDER_TIME = "render_time"


class OptimizationStatus(str, Enum):
    """Lifecycle state of an optimization suggestion."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    APPLIED = "applied"
    REVERTED = "reverted"
    FAILED = "failed"
    SKIPPED = "skipped"


class ProfileSessionType(str, Enum):
    """Mode a profiling session runs in."""

    CONTINUOUS = "continuous"
    SNAPSHOT = "snapshot"
    BENCHMARK = "benchmark"
    STRESS_TEST = "stress_test"
    COMPARISON = "comparison"


class HotspotType(str, Enum):
    """Kind of code-level hot region detected inside a frame."""

    RENDER_LOOP = "render_loop"
    UPDATE_LOOP = "update_loop"
    SCRIPT_BIND = "script_bind"
    ASSET_LOADING = "asset_loading"
    MEMORY_ALLOCATION = "memory_allocation"
    GARBAGE_COLLECTION = "garbage_collection"
    THREAD_SYNC = "thread_sync"
    LOCK_CONTENTION = "lock_contention"
    CACHE_MISS = "cache_miss"
    BRANCH_MISPREDICT = "branch_mispredict"


# ---------------------------------------------------------------------------
# Data Classes
# ---------------------------------------------------------------------------


@dataclass
class ProfileSample:
    """A single metric measurement captured during a profiling session."""

    sample_id: str = field(default_factory=lambda: _new_id("smp"))
    session_id: str = ""
    category: str = ProfileCategory.CPU.value
    metric: str = MetricType.FRAME_TIME.value
    value: float = 0.0
    unit: str = "ms"
    threshold: float = 0.0
    timestamp: str = field(default_factory=_now)
    frame_number: int = 0
    context: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class Bottleneck:
    """A performance bottleneck identified from one or more samples."""

    bottleneck_id: str = field(default_factory=lambda: _new_id("btl"))
    session_id: str = ""
    category: str = ProfileCategory.CPU.value
    severity: str = BottleneckSeverity.MEDIUM.value
    metric: str = MetricType.FRAME_TIME.value
    observed_value: float = 0.0
    threshold_value: float = 0.0
    impact_score: float = 0.0
    title: str = ""
    description: str = ""
    location: str = ""
    sample_ids: List[str] = field(default_factory=list)
    identified_at: str = field(default_factory=_now)
    status: str = "open"
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class OptimizationSuggestion:
    """An AI-generated optimization plan tied to a bottleneck."""

    suggestion_id: str = field(default_factory=lambda: _new_id("opt"))
    bottleneck_id: str = ""
    category: str = ProfileCategory.CPU.value
    optimization_type: str = OptimizationType.CACHE.value
    title: str = ""
    description: str = ""
    expected_gain: float = 0.0
    risk_level: str = "low"
    effort_level: str = "low"
    confidence: float = 0.5
    prerequisites: List[str] = field(default_factory=list)
    side_effects: List[str] = field(default_factory=list)
    status: str = OptimizationStatus.PENDING.value
    created_at: str = field(default_factory=_now)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class ProfileSession:
    """A profiling session that aggregates samples and analysis."""

    session_id: str = field(default_factory=lambda: _new_id("sess"))
    name: str = ""
    session_type: str = ProfileSessionType.CONTINUOUS.value
    status: str = ProfileStatus.IDLE.value
    started_at: str = field(default_factory=_now)
    ended_at: str = ""
    duration_seconds: float = 0.0
    target: str = ""
    sample_count: int = 0
    bottleneck_count: int = 0
    optimization_count: int = 0
    notes: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class FrameMetrics:
    """Per-frame telemetry captured during continuous profiling."""

    frame_id: str = field(default_factory=lambda: _new_id("frm"))
    session_id: str = ""
    frame_number: int = 0
    frame_time: float = 0.0
    fps: float = 0.0
    gpu_time: float = 0.0
    cpu_time: float = 0.0
    render_time: float = 0.0
    draw_calls: int = 0
    triangles: int = 0
    vertices: int = 0
    memory_usage: float = 0.0
    network_latency: float = 0.0
    io_time: float = 0.0
    script_time: float = 0.0
    physics_time: float = 0.0
    audio_time: float = 0.0
    timestamp: str = field(default_factory=_now)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class Hotspot:
    """A code-level hot region that explains where frame time is spent."""

    hotspot_id: str = field(default_factory=lambda: _new_id("hot"))
    session_id: str = ""
    hotspot_type: str = HotspotType.UPDATE_LOOP.value
    name: str = ""
    location: str = ""
    self_time: float = 0.0
    total_time: float = 0.0
    call_count: int = 0
    percentage: float = 0.0
    category: str = ProfileCategory.CPU.value
    stack_hash: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class PerformanceBaseline:
    """A captured performance snapshot used as a comparison point."""

    baseline_id: str = field(default_factory=lambda: _new_id("base"))
    name: str = ""
    description: str = ""
    created_at: str = field(default_factory=_now)
    metrics: Dict[str, float] = field(default_factory=dict)
    target_fps: float = 60.0
    target_frame_time: float = 16.6
    max_memory: float = 2048.0
    max_draw_calls: int = 2000
    session_id: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class OptimizationResult:
    """Outcome of applying an optimization suggestion."""

    result_id: str = field(default_factory=lambda: _new_id("res"))
    suggestion_id: str = ""
    bottleneck_id: str = ""
    optimization_type: str = OptimizationType.CACHE.value
    status: str = OptimizationStatus.APPLIED.value
    applied_at: str = field(default_factory=_now)
    reverted_at: str = ""
    before_value: float = 0.0
    after_value: float = 0.0
    improvement_percent: float = 0.0
    actual_gain: float = 0.0
    metric: str = ""
    notes: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class ProfilerConfig:
    """Runtime configuration for the performance profiler."""

    max_sessions: int = 2000
    max_samples: int = 50000
    max_bottlenecks: int = 20000
    max_optimizations: int = 20000
    max_results: int = 20000
    max_hotspots: int = 10000
    max_baselines: int = 2000
    max_frame_metrics: int = 60000
    max_events: int = 20000
    auto_identify_bottlenecks: bool = True
    auto_suggest_optimizations: bool = True
    auto_apply_threshold: float = 0.6
    target_fps: float = 60.0
    sample_interval_ms: float = 16.6
    enabled_categories: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class ProfilerStats:
    """Aggregate counters for the performance profiler."""

    total_sessions: int = 0
    total_samples: int = 0
    total_bottlenecks: int = 0
    total_optimizations: int = 0
    total_applied: int = 0
    total_reverted: int = 0
    active_sessions: int = 0
    tick_count: int = 0
    avg_frame_time: float = 0.0
    avg_fps: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class ProfilerSnapshot:
    """A point-in-time capture of profiler state."""

    timestamp: str = field(default_factory=_now)
    sessions: List[Dict[str, Any]] = field(default_factory=list)
    samples: List[Dict[str, Any]] = field(default_factory=list)
    bottlenecks: List[Dict[str, Any]] = field(default_factory=list)
    optimizations: List[Dict[str, Any]] = field(default_factory=list)
    hotspots: List[Dict[str, Any]] = field(default_factory=list)
    baselines: List[Dict[str, Any]] = field(default_factory=list)
    frame_metrics: List[Dict[str, Any]] = field(default_factory=list)
    results: List[Dict[str, Any]] = field(default_factory=list)
    stats: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class ProfilerEvent:
    """An audit event emitted by the performance profiler."""

    event_id: str = field(default_factory=lambda: _new_id("evt"))
    event_type: str = ""
    timestamp: str = field(default_factory=_now)
    session_id: str = ""
    data: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


# ---------------------------------------------------------------------------
# AI Performance Profiler Singleton
# ---------------------------------------------------------------------------


class AIPerformanceProfiler:
    """Singleton agent that profiles, diagnoses, and optimizes game performance.

    The profiler maintains profiling sessions, metric samples, identified
    bottlenecks, optimization suggestions, applied optimization results,
    per-frame metrics, code-level hotspots, and performance baselines. It
    correlates samples into bottlenecks through threshold analysis, generates
    targeted optimization plans from a category-aware template table, applies
    optimizations while measuring their impact, and projects future
    performance via linear-regression trend analysis.

    All mutations are guarded by a reentrant lock so the profiler is safe to
    call from multiple threads. The AI capabilities center on three original
    algorithms:

      - auto_diagnose: holistic bottleneck ranking, root-cause inference from
        hotspot correlation, and health-score computation.
      - auto_optimize: greedy application of the highest-impact pending
        suggestions that clear the configured confidence threshold.
      - predict_performance: least-squares projection of frame time, FPS,
        memory, and draw calls over a future horizon.
    """

    _instance: Optional["AIPerformanceProfiler"] = None
    _init_lock = threading.RLock()

    # ------------------------------------------------------------------
    # Construction and Singleton
    # ------------------------------------------------------------------

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._initialized: bool = False
        # Storage containers; populated by _seed on first initialization.
        self._sessions: Dict[str, ProfileSession] = {}
        self._samples: Dict[str, ProfileSample] = {}
        self._bottlenecks: Dict[str, Bottleneck] = {}
        self._optimizations: Dict[str, OptimizationSuggestion] = {}
        self._results: Dict[str, OptimizationResult] = {}
        self._hotspots: Dict[str, Hotspot] = {}
        self._baselines: Dict[str, PerformanceBaseline] = {}
        self._frame_metrics: List[FrameMetrics] = []
        self._events: List[ProfilerEvent] = []
        self._config = ProfilerConfig()
        self._stats = ProfilerStats()
        self._tick_count: int = 0
        self.initialize()

    @classmethod
    def get_instance(cls) -> "AIPerformanceProfiler":
        if cls._instance is None:
            with cls._init_lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def _seed(self) -> None:
        # Populate the profiler with a canonical set of performance data.
        # self._initialized = True is set at the very end.
        self._seed_data()
        self._initialized = True

    def initialize(self) -> None:
        if self._initialized:
            return
        with self._lock:
            if self._initialized:
                return
            self._seed()

    # ------------------------------------------------------------------
    # Internal Helpers
    # ------------------------------------------------------------------

    def _emit(
        self,
        event_type: str,
        session_id: str = "",
        data: Optional[Dict[str, Any]] = None,
    ) -> None:
        event = ProfilerEvent(
            event_id=_new_id("evt"),
            event_type=event_type,
            timestamp=_now(),
            session_id=session_id,
            data=data or {},
        )
        self._events.append(event)
        _evict_fifo_list(self._events, self._config.max_events)

    def _refresh_stats(self) -> None:
        self._stats.total_sessions = len(self._sessions)
        self._stats.total_samples = len(self._samples)
        self._stats.total_bottlenecks = len(self._bottlenecks)
        self._stats.total_optimizations = len(self._optimizations)
        self._stats.total_applied = sum(
            1 for o in self._optimizations.values()
            if o.status == OptimizationStatus.APPLIED.value
        )
        self._stats.total_reverted = sum(
            1 for r in self._results.values()
            if r.status == OptimizationStatus.REVERTED.value
        )
        self._stats.active_sessions = sum(
            1 for s in self._sessions.values()
            if s.status in (ProfileStatus.PROFILING.value,
                            ProfileStatus.ANALYZING.value,
                            ProfileStatus.OPTIMIZING.value)
        )
        self._stats.tick_count = self._tick_count

        # Compute average frame time and FPS from captured frame metrics.
        if self._frame_metrics:
            frame_times = [f.frame_time for f in self._frame_metrics
                           if f.frame_time > 0]
            if frame_times:
                avg_ft = _mean(frame_times)
                self._stats.avg_frame_time = round(avg_ft, 4)
                self._stats.avg_fps = round(1000.0 / avg_ft, 2) if avg_ft > 0 else 0.0
            else:
                self._stats.avg_frame_time = 0.0
                self._stats.avg_fps = 0.0
        else:
            self._stats.avg_frame_time = 0.0
            self._stats.avg_fps = 0.0

    def _threshold_for(self, metric: str) -> Tuple[float, str, str]:
        """Return (threshold_value, operator, default_severity) for a metric."""
        entry = _METRIC_THRESHOLDS.get(metric)
        if entry is None:
            return (0.0, ">", BottleneckSeverity.LOW.value)
        return entry

    def _check_threshold(self, metric: str, value: float) -> Optional[str]:
        """Return a severity string if value crosses the metric threshold."""
        threshold, op, default_sev = self._threshold_for(metric)
        if threshold <= 0:
            return None
        crossed = False
        if op == ">":
            crossed = value > threshold
        elif op == "<":
            crossed = value < threshold
        elif op == ">=":
            crossed = value >= threshold
        elif op == "<=":
            crossed = value <= threshold
        if not crossed:
            return None
        return _classify_severity(value, threshold)

    def _impact_for(self, value: float, threshold: float, severity: str) -> float:
        """Compute a normalized impact score in [0, 1] for a bottleneck."""
        if threshold <= 0:
            base = 0.1
        else:
            ratio = value / threshold
            # Clamp the overshoot contribution; cap at 5x for scoring stability.
            base = _clamp((ratio - 1.0) / 4.0, 0.0, 1.0)
        severity_bonus = _SEVERITY_WEIGHTS.get(severity, 0.05)
        return _clamp(base * 0.7 + severity_bonus, _IMPACT_MIN, _IMPACT_MAX)

    def _generate_suggestions(
        self,
        bottleneck: Bottleneck,
    ) -> List[OptimizationSuggestion]:
        """Produce optimization suggestions for a bottleneck from templates."""
        templates = _OPTIMIZATION_TEMPLATES.get(bottleneck.category, [])
        suggestions: List[OptimizationSuggestion] = []
        for opt_type, title, desc, gain, risk, effort in templates:
            # Confidence blends the expected gain with the bottleneck impact so
            # high-impact issues produce higher-confidence suggestions.
            confidence = _clamp(
                0.4 * gain + 0.4 * bottleneck.impact_score + 0.2,
                _CONFIDENCE_MIN, _CONFIDENCE_MAX,
            )
            suggestions.append(OptimizationSuggestion(
                suggestion_id=_new_id("opt"),
                bottleneck_id=bottleneck.bottleneck_id,
                category=bottleneck.category,
                optimization_type=opt_type,
                title=title,
                description=desc,
                expected_gain=round(gain, 4),
                risk_level=risk,
                effort_level=effort,
                confidence=round(confidence, 4),
                prerequisites=[],
                side_effects=[],
                status=OptimizationStatus.PENDING.value,
                created_at=_now(),
                metadata={"seed": False, "metric": bottleneck.metric},
            ))
        return suggestions

    # ------------------------------------------------------------------
    # Session Lifecycle
    # ------------------------------------------------------------------

    def start_session(
        self,
        name: str = "",
        session_type: str = ProfileSessionType.CONTINUOUS.value,
        target: str = "",
        session_id: str = "",
        notes: str = "",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Tuple[bool, str, Optional[ProfileSession]]:
        """Start a new profiling session."""
        with self._lock:
            sid = session_id or _new_id("sess")
            if sid in self._sessions:
                return False, f"session_already_exists:{sid}", None
            st = _coerce_enum(ProfileSessionType, session_type,
                              ProfileSessionType.CONTINUOUS)
            session = ProfileSession(
                session_id=sid,
                name=name or f"session_{sid}",
                session_type=st.value if isinstance(st, Enum) else st,
                status=ProfileStatus.PROFILING.value,
                started_at=_now(),
                ended_at="",
                duration_seconds=0.0,
                target=target,
                sample_count=0,
                bottleneck_count=0,
                optimization_count=0,
                notes=notes,
                metadata=dict(metadata or {}),
            )
            self._sessions[sid] = session
            _evict_fifo_dict(self._sessions, self._config.max_sessions)
            self._emit("session_started", session_id=sid, data={
                "name": session.name,
                "session_type": session.session_type,
                "target": target,
            })
            return True, "success", session

    def stop_session(
        self,
        session_id: str,
        status: str = ProfileStatus.COMPLETED.value,
        notes: str = "",
    ) -> Tuple[bool, str, Optional[ProfileSession]]:
        """Stop a profiling session and finalize its aggregates."""
        with self._lock:
            session = self._sessions.get(session_id)
            if session is None:
                return False, f"session_not_found:{session_id}", None
            if session.status in (ProfileStatus.COMPLETED.value,
                                  ProfileStatus.FAILED.value,
                                  ProfileStatus.CANCELLED.value):
                return False, f"session_already_stopped:{session_id}", session
            stat = _coerce_enum(ProfileStatus, status, ProfileStatus.COMPLETED)
            session.status = stat.value if isinstance(stat, Enum) else stat
            session.ended_at = _now()
            if notes:
                session.notes = notes
            # Tally aggregates from stored samples and bottlenecks.
            session.sample_count = sum(
                1 for s in self._samples.values() if s.session_id == session_id
            )
            session.bottleneck_count = sum(
                1 for b in self._bottlenecks.values()
                if b.session_id == session_id
            )
            session.optimization_count = sum(
                1 for o in self._optimizations.values()
                if o.bottleneck_id in self._bottlenecks
                and self._bottlenecks[o.bottleneck_id].session_id == session_id
            )
            self._emit("session_stopped", session_id=session_id, data={
                "status": session.status,
                "sample_count": session.sample_count,
                "bottleneck_count": session.bottleneck_count,
            })
            return True, "success", session

    def get_session(self, session_id: str) -> Optional[ProfileSession]:
        with self._lock:
            return self._sessions.get(session_id)

    def list_sessions(
        self,
        status_filter: str = "",
        session_type_filter: str = "",
    ) -> List[ProfileSession]:
        with self._lock:
            stat = _coerce_enum(ProfileStatus, status_filter, None)
            stype = _coerce_enum(ProfileSessionType, session_type_filter, None)
            results: List[ProfileSession] = []
            for session in self._sessions.values():
                if stat is not None and session.status != stat.value:
                    continue
                if stype is not None and session.session_type != stype.value:
                    continue
                results.append(session)
            return results

    def remove_session(self, session_id: str) -> Tuple[bool, str]:
        """Remove a session and its associated samples and bottlenecks."""
        with self._lock:
            if session_id not in self._sessions:
                return False, f"session_not_found:{session_id}"
            del self._sessions[session_id]
            # Cascade-delete dependent records.
            for sid in [s for s, v in self._samples.items()
                        if v.session_id == session_id]:
                del self._samples[sid]
            for bid in [b for b, v in self._bottlenecks.items()
                        if v.session_id == session_id]:
                del self._bottlenecks[bid]
            self._frame_metrics = [
                f for f in self._frame_metrics if f.session_id != session_id
            ]
            self._emit("session_removed", session_id=session_id, data={})
            return True, "success"

    # ------------------------------------------------------------------
    # Sample Lifecycle
    # ------------------------------------------------------------------

    def record_sample(
        self,
        session_id: str = "",
        category: str = ProfileCategory.CPU.value,
        metric: str = "",
        value: float = 0.0,
        unit: str = "ms",
        threshold: float = 0.0,
        frame_number: int = 0,
        sample_id: str = "",
        context: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Tuple[bool, str, Optional[ProfileSample]]:
        """Record a single metric sample and optionally flag a bottleneck."""
        with self._lock:
            sid = sample_id or _new_id("smp")
            if sid in self._samples:
                return False, f"sample_already_exists:{sid}", None
            cat = _coerce_enum(ProfileCategory, category, ProfileCategory.CPU)
            metric_str = metric or _CATEGORY_DEFAULT_METRIC.get(
                cat.value if isinstance(cat, Enum) else cat,
                MetricType.FRAME_TIME.value,
            )
            met = _coerce_enum(MetricType, metric_str, MetricType.FRAME_TIME)
            # Resolve threshold: explicit override, else the metric budget.
            if threshold <= 0:
                resolved_threshold = self._threshold_for(
                    met.value if isinstance(met, Enum) else met)[0]
            else:
                resolved_threshold = _safe_float(threshold, 0.0)
            sample = ProfileSample(
                sample_id=sid,
                session_id=session_id,
                category=cat.value if isinstance(cat, Enum) else cat,
                metric=met.value if isinstance(met, Enum) else met,
                value=_safe_float(value, 0.0),
                unit=unit,
                threshold=resolved_threshold,
                timestamp=_now(),
                frame_number=_safe_int(frame_number, 0),
                context=dict(context or {}),
                metadata=dict(metadata or {}),
            )
            self._samples[sid] = sample
            _evict_fifo_dict(self._samples, self._config.max_samples)

            # Auto-identify bottlenecks when enabled and a threshold is set.
            identified: Optional[str] = None
            if self._config.auto_identify_bottlenecks and resolved_threshold > 0:
                sev = self._check_threshold(sample.metric, sample.value)
                if sev is not None:
                    ok, _, btl = self.identify_bottleneck(
                        session_id=session_id,
                        category=sample.category,
                        metric=sample.metric,
                        value=sample.value,
                        threshold=resolved_threshold,
                        sample_ids=[sid],
                        location=str(context.get("location", "")) if context else "",
                    )
                    if ok and btl is not None:
                        identified = btl.bottleneck_id

            self._emit("sample_recorded", session_id=session_id, data={
                "sample_id": sid,
                "metric": sample.metric,
                "value": sample.value,
                "identified_bottleneck": identified,
            })
            return True, "success", sample

    def get_sample(self, sample_id: str) -> Optional[ProfileSample]:
        with self._lock:
            return self._samples.get(sample_id)

    def list_samples(
        self,
        session_id: str = "",
        category_filter: str = "",
        metric_filter: str = "",
        limit: int = 200,
    ) -> List[ProfileSample]:
        with self._lock:
            cat = _coerce_enum(ProfileCategory, category_filter, None)
            met = _coerce_enum(MetricType, metric_filter, None)
            cap = max(1, _safe_int(limit, 200))
            results: List[ProfileSample] = []
            for sample in self._samples.values():
                if session_id and sample.session_id != session_id:
                    continue
                if cat is not None and sample.category != cat.value:
                    continue
                if met is not None and sample.metric != met.value:
                    continue
                results.append(sample)
                if len(results) >= cap:
                    break
            return results

    def remove_sample(self, sample_id: str) -> Tuple[bool, str]:
        with self._lock:
            if sample_id not in self._samples:
                return False, f"sample_not_found:{sample_id}"
            del self._samples[sample_id]
            self._emit("sample_removed", data={"sample_id": sample_id})
            return True, "success"

    # ------------------------------------------------------------------
    # Bottleneck Lifecycle
    # ------------------------------------------------------------------

    def identify_bottleneck(
        self,
        session_id: str = "",
        category: str = ProfileCategory.CPU.value,
        metric: str = "",
        value: float = 0.0,
        threshold: float = 0.0,
        severity: str = "",
        title: str = "",
        description: str = "",
        location: str = "",
        sample_ids: Optional[List[str]] = None,
        bottleneck_id: str = "",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Tuple[bool, str, Optional[Bottleneck]]:
        """Identify and register a performance bottleneck.

        When a severity is not supplied, it is derived from how far the
        observed value exceeds the threshold. When no threshold is supplied,
        the metric budget table supplies one.
        """
        with self._lock:
            bid = bottleneck_id or _new_id("btl")
            if bid in self._bottlenecks:
                return False, f"bottleneck_already_exists:{bid}", None
            cat = _coerce_enum(ProfileCategory, category, ProfileCategory.CPU)
            cat_str = cat.value if isinstance(cat, Enum) else cat
            metric_str = metric or _CATEGORY_DEFAULT_METRIC.get(
                cat_str, MetricType.FRAME_TIME.value)
            met = _coerce_enum(MetricType, metric_str, MetricType.FRAME_TIME)
            metric_val = met.value if isinstance(met, Enum) else met
            # Resolve threshold.
            if threshold <= 0:
                resolved_threshold = self._threshold_for(metric_val)[0]
            else:
                resolved_threshold = _safe_float(threshold, 0.0)
            val = _safe_float(value, 0.0)
            # Resolve severity.
            if severity:
                sev = _coerce_enum(BottleneckSeverity, severity,
                                   BottleneckSeverity.MEDIUM)
                sev_str = sev.value if isinstance(sev, Enum) else sev
            else:
                if resolved_threshold > 0:
                    sev_str = self._check_threshold(metric_val, val) or \
                        BottleneckSeverity.INFO.value
                else:
                    sev_str = BottleneckSeverity.INFO.value
            impact = self._impact_for(val, resolved_threshold, sev_str)
            if not title:
                title = f"{metric_val} exceeded budget on {cat_str}"
            if not description:
                if resolved_threshold > 0:
                    ratio = val / resolved_threshold if resolved_threshold > 0 else 0.0
                    description = (
                        f"Observed {metric_val}={val:.2f} against a budget of "
                        f"{resolved_threshold:.2f} ({ratio:.2f}x) in the "
                        f"{cat_str} subsystem. Severity: {sev_str}."
                    )
                else:
                    description = (
                        f"Observed {metric_val}={val:.2f} in the {cat_str} "
                        f"subsystem. Severity: {sev_str}."
                    )
            bottleneck = Bottleneck(
                bottleneck_id=bid,
                session_id=session_id,
                category=cat_str,
                severity=sev_str,
                metric=metric_val,
                observed_value=val,
                threshold_value=resolved_threshold,
                impact_score=round(impact, 4),
                title=title,
                description=description,
                location=location,
                sample_ids=list(sample_ids or []),
                identified_at=_now(),
                status="open",
                metadata=dict(metadata or {}),
            )
            self._bottlenecks[bid] = bottleneck
            _evict_fifo_dict(self._bottlenecks, self._config.max_bottlenecks)

            # Auto-suggest optimizations when enabled.
            suggested: List[str] = []
            if self._config.auto_suggest_optimizations:
                for s in self._generate_suggestions(bottleneck):
                    self._optimizations[s.suggestion_id] = s
                    suggested.append(s.suggestion_id)
                _evict_fifo_dict(self._optimizations,
                                 self._config.max_optimizations)

            self._emit("bottleneck_identified", session_id=session_id, data={
                "bottleneck_id": bid,
                "category": cat_str,
                "severity": sev_str,
                "impact_score": round(impact, 4),
                "suggestions": suggested,
            })
            return True, "success", bottleneck

    def get_bottleneck(self, bottleneck_id: str) -> Optional[Bottleneck]:
        with self._lock:
            return self._bottlenecks.get(bottleneck_id)

    def list_bottlenecks(
        self,
        session_id: str = "",
        category_filter: str = "",
        severity_filter: str = "",
        limit: int = 200,
    ) -> List[Bottleneck]:
        with self._lock:
            cat = _coerce_enum(ProfileCategory, category_filter, None)
            sev = _coerce_enum(BottleneckSeverity, severity_filter, None)
            cap = max(1, _safe_int(limit, 200))
            results: List[Bottleneck] = []
            for b in self._bottlenecks.values():
                if session_id and b.session_id != session_id:
                    continue
                if cat is not None and b.category != cat.value:
                    continue
                if sev is not None and b.severity != sev.value:
                    continue
                results.append(b)
            # Sort by impact descending so the most pressing issues come first.
            results.sort(key=lambda b: b.impact_score, reverse=True)
            return results[:cap]

    def remove_bottleneck(self, bottleneck_id: str) -> Tuple[bool, str]:
        with self._lock:
            if bottleneck_id not in self._bottlenecks:
                return False, f"bottleneck_not_found:{bottleneck_id}"
            del self._bottlenecks[bottleneck_id]
            # Cascade-delete suggestions tied to this bottleneck.
            for sid in [s for s, v in self._optimizations.items()
                        if v.bottleneck_id == bottleneck_id]:
                del self._optimizations[sid]
            self._emit("bottleneck_removed", data={
                "bottleneck_id": bottleneck_id,
            })
            return True, "success"

    # ------------------------------------------------------------------
    # Optimization Lifecycle
    # ------------------------------------------------------------------

    def suggest_optimization(
        self,
        bottleneck_id: str,
        optimization_type: str = "",
        title: str = "",
        description: str = "",
        expected_gain: float = 0.0,
        risk_level: str = "low",
        effort_level: str = "low",
        confidence: float = 0.5,
        prerequisites: Optional[List[str]] = None,
        side_effects: Optional[List[str]] = None,
        suggestion_id: str = "",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Tuple[bool, str, Optional[OptimizationSuggestion]]:
        """Create an optimization suggestion for a known bottleneck.

        If no optimization_type is supplied, the agent picks the highest-gain
        template available for the bottleneck's category.
        """
        with self._lock:
            bottleneck = self._bottlenecks.get(bottleneck_id)
            if bottleneck is None:
                return False, f"bottleneck_not_found:{bottleneck_id}", None
            sid = suggestion_id or _new_id("opt")
            if sid in self._optimizations:
                return False, f"suggestion_already_exists:{sid}", None

            if not optimization_type:
                # Pick the highest expected-gain template for the category.
                templates = _OPTIMIZATION_TEMPLATES.get(bottleneck.category, [])
                if templates:
                    best = max(templates, key=lambda t: t[3])
                    opt_type_str = best[0]
                    if not title:
                        title = best[1]
                    if not description:
                        description = best[2]
                    if expected_gain <= 0:
                        expected_gain = best[3]
                    if risk_level == "low":
                        risk_level = best[4]
                    if effort_level == "low" and not metadata:
                        effort_level = best[5]
                else:
                    opt_type_str = OptimizationType.CACHE.value
            else:
                ot = _coerce_enum(OptimizationType, optimization_type,
                                  OptimizationType.CACHE)
                opt_type_str = ot.value if isinstance(ot, Enum) else ot

            gain = _clamp(_safe_float(expected_gain, 0.0), 0.0, 1.0)
            conf = _clamp(_safe_float(confidence, 0.5), 0.0, 1.0)
            suggestion = OptimizationSuggestion(
                suggestion_id=sid,
                bottleneck_id=bottleneck_id,
                category=bottleneck.category,
                optimization_type=opt_type_str,
                title=title or f"Optimize {bottleneck.metric} via {opt_type_str}",
                description=description,
                expected_gain=round(gain, 4),
                risk_level=risk_level,
                effort_level=effort_level,
                confidence=round(conf, 4),
                prerequisites=list(prerequisites or []),
                side_effects=list(side_effects or []),
                status=OptimizationStatus.PENDING.value,
                created_at=_now(),
                metadata=dict(metadata or {}),
            )
            self._optimizations[sid] = suggestion
            _evict_fifo_dict(self._optimizations,
                             self._config.max_optimizations)
            self._emit("optimization_suggested", session_id=bottleneck.session_id,
                       data={
                           "suggestion_id": sid,
                           "bottleneck_id": bottleneck_id,
                           "optimization_type": opt_type_str,
                           "expected_gain": round(gain, 4),
                       })
            return True, "success", suggestion

    def get_optimization(
        self, suggestion_id: str,
    ) -> Optional[OptimizationSuggestion]:
        with self._lock:
            return self._optimizations.get(suggestion_id)

    def list_optimizations(
        self,
        bottleneck_id: str = "",
        status_filter: str = "",
        category_filter: str = "",
        limit: int = 200,
    ) -> List[OptimizationSuggestion]:
        with self._lock:
            stat = _coerce_enum(OptimizationStatus, status_filter, None)
            cat = _coerce_enum(ProfileCategory, category_filter, None)
            cap = max(1, _safe_int(limit, 200))
            results: List[OptimizationSuggestion] = []
            for o in self._optimizations.values():
                if bottleneck_id and o.bottleneck_id != bottleneck_id:
                    continue
                if stat is not None and o.status != stat.value:
                    continue
                if cat is not None and o.category != cat.value:
                    continue
                results.append(o)
            # Sort by expected_gain * confidence descending.
            results.sort(
                key=lambda o: o.expected_gain * o.confidence,
                reverse=True,
            )
            return results[:cap]

    def remove_optimization(self, suggestion_id: str) -> Tuple[bool, str]:
        with self._lock:
            if suggestion_id not in self._optimizations:
                return False, f"suggestion_not_found:{suggestion_id}"
            suggestion = self._optimizations[suggestion_id]
            if suggestion.status == OptimizationStatus.APPLIED.value:
                return False, (
                    "cannot remove applied optimization; revert it first",
                )
            del self._optimizations[suggestion_id]
            self._emit("optimization_removed", data={
                "suggestion_id": suggestion_id,
            })
            return True, "success"

    def apply_optimization(
        self,
        suggestion_id: str,
        before_value: float = 0.0,
        after_value: float = 0.0,
        notes: str = "",
    ) -> Tuple[bool, str, Optional[OptimizationResult]]:
        """Apply an optimization suggestion and record the measured outcome.

        When before/after values are not supplied, the agent simulates the
        improvement using the suggestion's expected gain and the linked
        bottleneck's observed value.
        """
        with self._lock:
            suggestion = self._optimizations.get(suggestion_id)
            if suggestion is None:
                return False, f"suggestion_not_found:{suggestion_id}", None
            if suggestion.status == OptimizationStatus.APPLIED.value:
                return False, "optimization_already_applied", None
            bottleneck = self._bottlenecks.get(suggestion.bottleneck_id)

            before = _safe_float(before_value, 0.0)
            after = _safe_float(after_value, 0.0)
            metric = ""
            if before <= 0 and bottleneck is not None:
                before = bottleneck.observed_value
                metric = bottleneck.metric
            # Simulate after-value from expected gain when not provided.
            if after <= 0:
                # Confidence-weighted gain; clamped so we never go negative.
                gain = suggestion.expected_gain * (0.5 + 0.5 * suggestion.confidence)
                after = before * max(0.0, 1.0 - gain)
            if not metric and bottleneck is not None:
                metric = bottleneck.metric
            improvement = 0.0
            if before > 0:
                improvement = round(
                    ((before - after) / before) * 100.0, 4)
            actual_gain = round(before - after, 4)

            result = OptimizationResult(
                result_id=_new_id("res"),
                suggestion_id=suggestion_id,
                bottleneck_id=suggestion.bottleneck_id,
                optimization_type=suggestion.optimization_type,
                status=OptimizationStatus.APPLIED.value,
                applied_at=_now(),
                reverted_at="",
                before_value=round(before, 4),
                after_value=round(after, 4),
                improvement_percent=improvement,
                actual_gain=actual_gain,
                metric=metric,
                notes=notes,
                metadata={"applied_by": "ai_performance_profiler"},
            )
            self._results[result.result_id] = result
            _evict_fifo_dict(self._results, self._config.max_results)
            suggestion.status = OptimizationStatus.APPLIED.value
            if bottleneck is not None:
                bottleneck.status = "optimized"

            self._emit("optimization_applied",
                       session_id=bottleneck.session_id if bottleneck else "",
                       data={
                           "suggestion_id": suggestion_id,
                           "result_id": result.result_id,
                           "before_value": round(before, 4),
                           "after_value": round(after, 4),
                           "improvement_percent": improvement,
                       })
            return True, "success", result

    def revert_optimization(
        self,
        result_id: str,
        notes: str = "",
    ) -> Tuple[bool, str, Optional[OptimizationResult]]:
        """Revert an applied optimization and record the rollback."""
        with self._lock:
            result = self._results.get(result_id)
            if result is None:
                return False, f"result_not_found:{result_id}", None
            if result.status == OptimizationStatus.REVERTED.value:
                return False, "optimization_already_reverted", result
            suggestion = self._optimizations.get(result.suggestion_id)
            result.status = OptimizationStatus.REVERTED.value
            result.reverted_at = _now()
            if notes:
                result.notes = notes
            if suggestion is not None:
                suggestion.status = OptimizationStatus.REVERTED.value
            bottleneck = self._bottlenecks.get(result.bottleneck_id)
            if bottleneck is not None:
                bottleneck.status = "open"
            self._emit("optimization_reverted",
                       session_id=bottleneck.session_id if bottleneck else "",
                       data={
                           "result_id": result_id,
                           "suggestion_id": result.suggestion_id,
                       })
            return True, "success", result

    # ------------------------------------------------------------------
    # Frame Metrics
    # ------------------------------------------------------------------

    def record_frame_metrics(
        self,
        session_id: str = "",
        frame_number: int = 0,
        frame_time: float = 0.0,
        gpu_time: float = 0.0,
        cpu_time: float = 0.0,
        render_time: float = 0.0,
        draw_calls: int = 0,
        triangles: int = 0,
        vertices: int = 0,
        memory_usage: float = 0.0,
        network_latency: float = 0.0,
        io_time: float = 0.0,
        script_time: float = 0.0,
        physics_time: float = 0.0,
        audio_time: float = 0.0,
        frame_id: str = "",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Tuple[bool, str, Optional[FrameMetrics]]:
        """Capture per-frame telemetry and run automatic bottleneck checks."""
        with self._lock:
            fid = frame_id or _new_id("frm")
            ft = _safe_float(frame_time, 0.0)
            fps = round(1000.0 / ft, 2) if ft > 0 else 0.0
            frame = FrameMetrics(
                frame_id=fid,
                session_id=session_id,
                frame_number=_safe_int(frame_number, 0),
                frame_time=ft,
                fps=fps,
                gpu_time=_safe_float(gpu_time, 0.0),
                cpu_time=_safe_float(cpu_time, 0.0),
                render_time=_safe_float(render_time, 0.0),
                draw_calls=_safe_int(draw_calls, 0),
                triangles=_safe_int(triangles, 0),
                vertices=_safe_int(vertices, 0),
                memory_usage=_safe_float(memory_usage, 0.0),
                network_latency=_safe_float(network_latency, 0.0),
                io_time=_safe_float(io_time, 0.0),
                script_time=_safe_float(script_time, 0.0),
                physics_time=_safe_float(physics_time, 0.0),
                audio_time=_safe_float(audio_time, 0.0),
                timestamp=_now(),
                metadata=dict(metadata or {}),
            )
            self._frame_metrics.append(frame)
            _evict_fifo_list(self._frame_metrics,
                             self._config.max_frame_metrics)

            # Auto-identify bottlenecks for the most diagnostic metrics.
            flagged: List[str] = []
            if self._config.auto_identify_bottlenecks:
                checks = [
                    (MetricType.FRAME_TIME, frame.frame_time),
                    (MetricType.GPU_TIME, frame.gpu_time),
                    (MetricType.CPU_TIME, frame.cpu_time),
                    (MetricType.RENDER_TIME, frame.render_time),
                    (MetricType.DRAW_CALLS, float(frame.draw_calls)),
                    (MetricType.MEMORY_USAGE, frame.memory_usage),
                    (MetricType.SCRIPT_TIME, frame.script_time),
                    (MetricType.PHYSICS_TIME, frame.physics_time),
                ]
                for metric_enum, val in checks:
                    sev = self._check_threshold(metric_enum.value, val)
                    if sev is None:
                        continue
                    category_str = ProfileCategory.CPU.value
                    if metric_enum in (MetricType.GPU_TIME, MetricType.RENDER_TIME,
                                       MetricType.DRAW_CALLS, MetricType.TRIANGLES,
                                       MetricType.VERTICES):
                        category_str = (ProfileCategory.GPU.value
                                        if metric_enum == MetricType.GPU_TIME
                                        else ProfileCategory.RENDER.value)
                    elif metric_enum == MetricType.MEMORY_USAGE:
                        category_str = ProfileCategory.MEMORY.value
                    elif metric_enum == MetricType.SCRIPT_TIME:
                        category_str = ProfileCategory.SCRIPT.value
                    elif metric_enum == MetricType.PHYSICS_TIME:
                        category_str = ProfileCategory.PHYSICS.value
                    ok, _, btl = self.identify_bottleneck(
                        session_id=session_id,
                        category=category_str,
                        metric=metric_enum.value,
                        value=val,
                        sample_ids=[fid],
                        location=f"frame:{frame.frame_number}",
                    )
                    if ok and btl is not None:
                        flagged.append(btl.bottleneck_id)

            self._emit("frame_recorded", session_id=session_id, data={
                "frame_id": fid,
                "frame_number": frame.frame_number,
                "frame_time": ft,
                "fps": fps,
                "flagged_bottlenecks": flagged,
            })
            return True, "success", frame

    def get_frame_metrics(
        self,
        session_id: str = "",
        limit: int = 200,
    ) -> List[FrameMetrics]:
        """Return frame metrics, optionally filtered by session."""
        with self._lock:
            cap = max(1, _safe_int(limit, 200))
            if session_id:
                results = [f for f in self._frame_metrics
                           if f.session_id == session_id]
            else:
                results = list(self._frame_metrics)
            return results[-cap:]

    # ------------------------------------------------------------------
    # Hotspots
    # ------------------------------------------------------------------

    def register_hotspot(
        self,
        session_id: str = "",
        hotspot_type: str = HotspotType.UPDATE_LOOP.value,
        name: str = "",
        location: str = "",
        self_time: float = 0.0,
        total_time: float = 0.0,
        call_count: int = 0,
        percentage: float = 0.0,
        category: str = "",
        stack_hash: str = "",
        hotspot_id: str = "",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Tuple[bool, str, Optional[Hotspot]]:
        """Register a code-level hot region detected inside a frame."""
        with self._lock:
            hid = hotspot_id or _new_id("hot")
            if hid in self._hotspots:
                return False, f"hotspot_already_exists:{hid}", None
            ht = _coerce_enum(HotspotType, hotspot_type,
                              HotspotType.UPDATE_LOOP)
            ht_str = ht.value if isinstance(ht, Enum) else ht
            if category:
                cat = _coerce_enum(ProfileCategory, category, ProfileCategory.CPU)
                cat_str = cat.value if isinstance(cat, Enum) else cat
            else:
                cat_str = _HOTSPOT_CATEGORY.get(ht_str, ProfileCategory.CPU.value)
            st = _safe_float(self_time, 0.0)
            tt = _safe_float(total_time, 0.0) or st
            pct = _safe_float(percentage, 0.0)
            if pct <= 0 and tt > 0:
                # Derive percentage from total_time when not provided. This
                # assumes total_time is expressed against a 16.6ms budget.
                pct = round((tt / 16.6) * 100.0, 4)
            hotspot = Hotspot(
                hotspot_id=hid,
                session_id=session_id,
                hotspot_type=ht_str,
                name=name or f"{ht_str}_{hid}",
                location=location,
                self_time=st,
                total_time=tt,
                call_count=_safe_int(call_count, 0),
                percentage=pct,
                category=cat_str,
                stack_hash=stack_hash,
                metadata=dict(metadata or {}),
            )
            self._hotspots[hid] = hotspot
            _evict_fifo_dict(self._hotspots, self._config.max_hotspots)
            self._emit("hotspot_registered", session_id=session_id, data={
                "hotspot_id": hid,
                "hotspot_type": ht_str,
                "percentage": pct,
            })
            return True, "success", hotspot

    def get_hotspot(self, hotspot_id: str) -> Optional[Hotspot]:
        with self._lock:
            return self._hotspots.get(hotspot_id)

    def list_hotspots(
        self,
        session_id: str = "",
        hotspot_type_filter: str = "",
        category_filter: str = "",
        limit: int = 100,
    ) -> List[Hotspot]:
        with self._lock:
            ht = _coerce_enum(HotspotType, hotspot_type_filter, None)
            cat = _coerce_enum(ProfileCategory, category_filter, None)
            cap = max(1, _safe_int(limit, 100))
            results: List[Hotspot] = []
            for h in self._hotspots.values():
                if session_id and h.session_id != session_id:
                    continue
                if ht is not None and h.hotspot_type != ht.value:
                    continue
                if cat is not None and h.category != cat.value:
                    continue
                results.append(h)
            results.sort(key=lambda h: h.percentage, reverse=True)
            return results[:cap]

    def remove_hotspot(self, hotspot_id: str) -> Tuple[bool, str]:
        with self._lock:
            if hotspot_id not in self._hotspots:
                return False, f"hotspot_not_found:{hotspot_id}"
            del self._hotspots[hotspot_id]
            self._emit("hotspot_removed", data={"hotspot_id": hotspot_id})
            return True, "success"

    # ------------------------------------------------------------------
    # Baselines
    # ------------------------------------------------------------------

    def create_baseline(
        self,
        name: str = "",
        description: str = "",
        target_fps: float = 60.0,
        target_frame_time: float = 16.6,
        max_memory: float = 2048.0,
        max_draw_calls: int = 2000,
        session_id: str = "",
        metrics: Optional[Dict[str, float]] = None,
        baseline_id: str = "",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Tuple[bool, str, Optional[PerformanceBaseline]]:
        """Create a performance baseline for comparison and regression checks."""
        with self._lock:
            bid = baseline_id or _new_id("base")
            if bid in self._baselines:
                return False, f"baseline_already_exists:{bid}", None
            resolved_metrics: Dict[str, float] = {}
            if metrics:
                resolved_metrics = {str(k): _safe_float(v, 0.0)
                                    for k, v in metrics.items()}
            elif session_id:
                # Derive metrics from the session's frame metrics.
                frames = [f for f in self._frame_metrics
                          if f.session_id == session_id]
                if frames:
                    resolved_metrics = {
                        "avg_frame_time": round(_mean(
                            [f.frame_time for f in frames if f.frame_time > 0]), 4),
                        "avg_gpu_time": round(_mean(
                            [f.gpu_time for f in frames]), 4),
                        "avg_cpu_time": round(_mean(
                            [f.cpu_time for f in frames]), 4),
                        "avg_render_time": round(_mean(
                            [f.render_time for f in frames]), 4),
                        "avg_memory": round(_mean(
                            [f.memory_usage for f in frames]), 4),
                        "avg_draw_calls": round(_mean(
                            [float(f.draw_calls) for f in frames]), 4),
                        "avg_fps": round(_mean(
                            [f.fps for f in frames if f.fps > 0]), 4),
                        "frame_count": float(len(frames)),
                    }
            baseline = PerformanceBaseline(
                baseline_id=bid,
                name=name or f"baseline_{bid}",
                description=description,
                created_at=_now(),
                metrics=resolved_metrics,
                target_fps=_safe_float(target_fps, 60.0),
                target_frame_time=_safe_float(target_frame_time, 16.6),
                max_memory=_safe_float(max_memory, 2048.0),
                max_draw_calls=_safe_int(max_draw_calls, 2000),
                session_id=session_id,
                metadata=dict(metadata or {}),
            )
            self._baselines[bid] = baseline
            _evict_fifo_dict(self._baselines, self._config.max_baselines)
            self._emit("baseline_created", session_id=session_id, data={
                "baseline_id": bid,
                "name": baseline.name,
                "metric_count": len(resolved_metrics),
            })
            return True, "success", baseline

    def get_baseline(self, baseline_id: str) -> Optional[PerformanceBaseline]:
        with self._lock:
            return self._baselines.get(baseline_id)

    def list_baselines(self, limit: int = 100) -> List[PerformanceBaseline]:
        with self._lock:
            cap = max(1, _safe_int(limit, 100))
            return list(self._baselines.values())[-cap:]

    def compare_baselines(
        self,
        baseline_id_a: str,
        baseline_id_b: str,
    ) -> Tuple[bool, str, Dict[str, Any]]:
        """Compare two baselines and return a metric-by-metric delta report."""
        with self._lock:
            a = self._baselines.get(baseline_id_a)
            b = self._baselines.get(baseline_id_b)
            if a is None:
                return False, f"baseline_not_found:{baseline_id_a}", {}
            if b is None:
                return False, f"baseline_not_found:{baseline_id_b}", {}
            metrics_a = a.metrics
            metrics_b = b.metrics
            all_keys = sorted(set(metrics_a.keys()) | set(metrics_b.keys()))
            deltas: List[Dict[str, Any]] = []
            regressions: List[str] = []
            improvements: List[str] = []
            for key in all_keys:
                va = _safe_float(metrics_a.get(key, 0.0), 0.0)
                vb = _safe_float(metrics_b.get(key, 0.0), 0.0)
                diff = round(vb - va, 4)
                pct = 0.0
                if va != 0:
                    pct = round((diff / abs(va)) * 100.0, 4)
                # For time-like metrics, an increase is a regression.
                is_time_metric = ("time" in key or "latency" in key
                                   or "memory" in key or "draw_calls" in key)
                direction = "stable"
                if diff > 0:
                    direction = "regression" if is_time_metric else "improvement"
                elif diff < 0:
                    direction = "improvement" if is_time_metric else "regression"
                if direction == "regression":
                    regressions.append(key)
                elif direction == "improvement":
                    improvements.append(key)
                deltas.append({
                    "metric": key,
                    "baseline_a": va,
                    "baseline_b": vb,
                    "delta": diff,
                    "delta_percent": pct,
                    "direction": direction,
                })
            report = {
                "baseline_a": baseline_id_a,
                "baseline_b": baseline_id_b,
                "name_a": a.name,
                "name_b": b.name,
                "deltas": deltas,
                "regressions": regressions,
                "improvements": improvements,
                "summary": (
                    f"{len(improvements)} improved, {len(regressions)} "
                    f"regressed, {len(all_keys)} total metrics"
                ),
            }
            self._emit("baselines_compared", data={
                "baseline_a": baseline_id_a,
                "baseline_b": baseline_id_b,
                "regressions": len(regressions),
                "improvements": len(improvements),
            })
            return True, "success", report

    # ------------------------------------------------------------------
    # AI Methods
    # ------------------------------------------------------------------

    def auto_diagnose(
        self,
        session_id: str = "",
    ) -> Dict[str, Any]:
        """Produce a comprehensive AI diagnosis report.

        The diagnosis ranks bottlenecks by impact, breaks them down by
        category and severity, infers root causes by correlating bottlenecks
        with the heaviest hotspots, and computes an overall health score.
        """
        with self._lock:
            self._refresh_stats()
            bottlenecks = list(self._bottlenecks.values())
            if session_id:
                bottlenecks = [b for b in bottlenecks
                               if b.session_id == session_id]

            # Category breakdown.
            category_counts: Dict[str, int] = {}
            category_impact: Dict[str, float] = {}
            severity_counts: Dict[str, int] = {}
            for b in bottlenecks:
                category_counts[b.category] = category_counts.get(
                    b.category, 0) + 1
                category_impact[b.category] = round(
                    category_impact.get(b.category, 0.0) + b.impact_score, 4)
                severity_counts[b.severity] = severity_counts.get(
                    b.severity, 0) + 1

            # Top bottlenecks by impact.
            ranked = sorted(bottlenecks,
                            key=lambda b: b.impact_score, reverse=True)
            top_bottlenecks = [
                {
                    "bottleneck_id": b.bottleneck_id,
                    "title": b.title,
                    "category": b.category,
                    "severity": b.severity,
                    "impact_score": round(b.impact_score, 4),
                    "metric": b.metric,
                    "observed_value": round(b.observed_value, 4),
                    "threshold_value": round(b.threshold_value, 4),
                }
                for b in ranked[:10]
            ]

            # Root-cause inference: pair each top bottleneck with the most
            # relevant hotspot by category overlap.
            hotspots = list(self._hotspots.values())
            if session_id:
                hotspots = [h for h in hotspots
                            if h.session_id == session_id or not h.session_id]
            root_causes: List[Dict[str, Any]] = []
            for b in ranked[:5]:
                related = [h for h in hotspots if h.category == b.category]
                related.sort(key=lambda h: h.percentage, reverse=True)
                top_hotspot = related[0] if related else None
                root_causes.append({
                    "bottleneck_id": b.bottleneck_id,
                    "title": b.title,
                    "category": b.category,
                    "inferred_hotspot": (
                        top_hotspot.name if top_hotspot else "unidentified"),
                    "hotspot_type": (
                        top_hotspot.hotspot_type if top_hotspot else ""),
                    "hotspot_percentage": (
                        round(top_hotspot.percentage, 4)
                        if top_hotspot else 0.0),
                    "explanation": (
                        f"The {b.category} bottleneck on {b.metric} aligns "
                        f"with the "
                        f"{top_hotspot.hotspot_type if top_hotspot else 'unknown'} "
                        f"hotspot consuming "
                        f"{round(top_hotspot.percentage, 2)}% of frame time."
                        if top_hotspot else
                        f"No matching hotspot found for the {b.category} "
                        f"bottleneck on {b.metric}."),
                })

            # Recommendations drawn from pending optimization suggestions.
            pending = [o for o in self._optimizations.values()
                       if o.status == OptimizationStatus.PENDING.value
                       and (not session_id
                            or self._bottlenecks.get(o.bottleneck_id) is None
                            or self._bottlenecks[o.bottleneck_id].session_id
                            == session_id)]
            pending.sort(key=lambda o: o.expected_gain * o.confidence,
                         reverse=True)
            recommendations = [
                {
                    "suggestion_id": o.suggestion_id,
                    "title": o.title,
                    "optimization_type": o.optimization_type,
                    "expected_gain": round(o.expected_gain, 4),
                    "confidence": round(o.confidence, 4),
                    "risk_level": o.risk_level,
                }
                for o in pending[:10]
            ]

            # Health score: start at 100 and subtract weighted severity penalties.
            penalty = 0.0
            for sev, count in severity_counts.items():
                penalty += _SEVERITY_WEIGHTS.get(sev, 0.05) * count
            health_score = round(
                _HEALTH_MAX - penalty * 10.0, 2)
            health_score = max(_HEALTH_MIN, min(_HEALTH_MAX, health_score))

            # Determine overall status label from the health score.
            if health_score >= 85:
                status_label = "healthy"
            elif health_score >= 65:
                status_label = "acceptable"
            elif health_score >= 40:
                status_label = "degraded"
            elif health_score >= 20:
                status_label = "critical"
            else:
                status_label = "blocking"

            summary = (
                f"Diagnosed {len(bottlenecks)} bottlenecks across "
                f"{len(category_counts)} subsystems. Health score "
                f"{health_score:.1f}/100 ({status_label}). "
                f"{len(pending)} pending optimizations available, "
                f"{len(recommendations)} recommended."
            )

            self._emit("auto_diagnose", session_id=session_id, data={
                "bottleneck_count": len(bottlenecks),
                "health_score": health_score,
                "status": status_label,
            })
            return {
                "session_id": session_id,
                "health_score": health_score,
                "status": status_label,
                "total_bottlenecks": len(bottlenecks),
                "category_breakdown": category_counts,
                "category_impact": category_impact,
                "severity_breakdown": severity_counts,
                "top_bottlenecks": top_bottlenecks,
                "root_causes": root_causes,
                "recommendations": recommendations,
                "pending_optimization_count": len(pending),
                "summary": summary,
                "timestamp": _now(),
            }

    def auto_optimize(
        self,
        session_id: str = "",
        max_applications: int = 10,
    ) -> Tuple[bool, str, List[str]]:
        """Automatically apply the highest-impact pending optimizations.

        Suggestions are ranked by expected_gain * confidence and applied in
        order as long as they clear the configured auto_apply_threshold.
        """
        with self._lock:
            threshold = _clamp(self._config.auto_apply_threshold, 0.0, 1.0)
            cap = max(1, _safe_int(max_applications, 10))
            candidates = [o for o in self._optimizations.values()
                          if o.status == OptimizationStatus.PENDING.value]
            if session_id:
                candidates = [
                    o for o in candidates
                    if (self._bottlenecks.get(o.bottleneck_id) is None
                        or self._bottlenecks[o.bottleneck_id].session_id
                        == session_id)
                ]
            candidates.sort(key=lambda o: o.expected_gain * o.confidence,
                            reverse=True)
            applied_ids: List[str] = []
            for suggestion in candidates:
                if len(applied_ids) >= cap:
                    break
                score = suggestion.expected_gain * suggestion.confidence
                if score < threshold:
                    continue
                ok, _, result = self.apply_optimization(suggestion.suggestion_id)
                if ok and result is not None:
                    applied_ids.append(result.result_id)
            self._emit("auto_optimize", session_id=session_id, data={
                "applied_count": len(applied_ids),
                "threshold": threshold,
                "result_ids": applied_ids,
            })
            if not applied_ids:
                return False, "no optimizations cleared the threshold", []
            return True, "success", applied_ids

    def predict_performance(
        self,
        session_id: str = "",
        horizon: int = 60,
    ) -> Dict[str, Any]:
        """Project future performance from frame-metric trends via regression.

        Uses a simple least-squares linear fit on the captured frame metrics
        to project frame_time, FPS, memory, and draw_calls over the supplied
        horizon (in frames). Confidence is the R-squared value of the fit.
        """
        with self._lock:
            frames = list(self._frame_metrics)
            if session_id:
                frames = [f for f in frames if f.session_id == session_id]
            # Sort by frame_number so the regression axis is monotonic.
            frames.sort(key=lambda f: f.frame_number)
            h = max(1, _safe_int(horizon, 60))

            if len(frames) < 2:
                return {
                    "session_id": session_id,
                    "horizon": h,
                    "sample_count": len(frames),
                    "predicted_frame_time": 0.0,
                    "predicted_fps": 0.0,
                    "predicted_memory": 0.0,
                    "predicted_draw_calls": 0,
                    "trend": "insufficient_data",
                    "confidence": 0.0,
                    "timestamp": _now(),
                }

            xs = [float(f.frame_number) for f in frames]
            # Project from the last sample's frame number.
            x_last = xs[-1]
            x_target = x_last + float(h)

            def _fit(ys: List[float]) -> Tuple[float, float, float, float]:
                """Return (slope, intercept, predicted_at_target, r_squared)."""
                n = len(xs)
                if n < 2:
                    return 0.0, ys[0] if ys else 0.0, ys[-1] if ys else 0.0, 0.0
                sum_x = sum(xs)
                sum_y = sum(ys)
                sum_xy = sum(x * y for x, y in zip(xs, ys))
                sum_xx = sum(x * x for x in xs)
                denom = n * sum_xx - sum_x * sum_x
                if denom == 0:
                    mean_y = sum_y / n
                    return 0.0, mean_y, mean_y, 0.0
                slope = (n * sum_xy - sum_x * sum_y) / denom
                intercept = (sum_y - slope * sum_x) / n
                predicted = slope * x_target + intercept
                # R-squared for goodness of fit.
                mean_y = sum_y / n
                ss_tot = sum((y - mean_y) ** 2 for y in ys)
                ss_res = sum(
                    (y - (slope * x + intercept)) ** 2
                    for x, y in zip(xs, ys))
                r2 = 1.0 - (ss_res / ss_tot) if ss_tot > 0 else 0.0
                return slope, intercept, predicted, r2

            frame_times = [f.frame_time for f in frames]
            memories = [f.memory_usage for f in frames]
            draw_calls = [float(f.draw_calls) for f in frames]

            ft_slope, _, ft_pred, ft_r2 = _fit(frame_times)
            mem_slope, _, mem_pred, mem_r2 = _fit(memories)
            dc_slope, _, dc_pred, dc_r2 = _fit(draw_calls)

            # Clamp predictions to non-negative values.
            ft_pred = max(0.0, ft_pred)
            mem_pred = max(0.0, mem_pred)
            dc_pred = max(0.0, dc_pred)
            fps_pred = (1000.0 / ft_pred) if ft_pred > 0 else 0.0

            # Overall trend label driven by frame-time slope.
            if ft_slope < -1e-6:
                trend = "improving"
            elif ft_slope > 1e-6:
                trend = "degrading"
            else:
                trend = "stable"

            # Confidence is the average R-squared across the fitted metrics,
            # clamped to [0, 1].
            r2_values = [ft_r2, mem_r2, dc_r2]
            confidence = _clamp(_mean(r2_values), 0.0, 1.0)

            self._emit("predict_performance", session_id=session_id, data={
                "horizon": h,
                "predicted_frame_time": round(ft_pred, 4),
                "predicted_fps": round(fps_pred, 2),
                "trend": trend,
                "confidence": round(confidence, 4),
            })
            return {
                "session_id": session_id,
                "horizon": h,
                "sample_count": len(frames),
                "predicted_frame_time": round(ft_pred, 4),
                "predicted_fps": round(fps_pred, 2),
                "predicted_memory": round(mem_pred, 4),
                "predicted_draw_calls": int(round(dc_pred)),
                "trend": trend,
                "confidence": round(confidence, 4),
                "frame_time_slope": round(ft_slope, 6),
                "memory_slope": round(mem_slope, 6),
                "draw_calls_slope": round(dc_slope, 6),
                "r_squared": {
                    "frame_time": round(ft_r2, 4),
                    "memory": round(mem_r2, 4),
                    "draw_calls": round(dc_r2, 4),
                },
                "timestamp": _now(),
            }

    # ------------------------------------------------------------------
    # Observability
    # ------------------------------------------------------------------

    def list_events(
        self,
        session_id: str = "",
        event_type: str = "",
        limit: int = 100,
    ) -> List[ProfilerEvent]:
        with self._lock:
            cap = max(1, _safe_int(limit, 100))
            results: List[ProfilerEvent] = []
            # Walk newest-first for a readable recent-activity feed.
            for e in reversed(self._events):
                if session_id and e.session_id != session_id:
                    continue
                if event_type and e.event_type != event_type:
                    continue
                results.append(e)
                if len(results) >= cap:
                    break
            return results

    def get_status(self) -> Dict[str, Any]:
        with self._lock:
            self._refresh_stats()
            return {
                "initialized": self._initialized,
                "sessions": len(self._sessions),
                "samples": len(self._samples),
                "bottlenecks": len(self._bottlenecks),
                "optimizations": len(self._optimizations),
                "results": len(self._results),
                "hotspots": len(self._hotspots),
                "baselines": len(self._baselines),
                "frame_metrics": len(self._frame_metrics),
                "events": len(self._events),
                "tick_count": self._tick_count,
                "config": self._config.to_dict(),
            }

    def get_stats(self) -> Dict[str, Any]:
        with self._lock:
            self._refresh_stats()
            return self._stats.to_dict()

    def get_snapshot(self) -> Dict[str, Any]:
        with self._lock:
            self._refresh_stats()
            snapshot = ProfilerSnapshot(
                timestamp=_now(),
                sessions=[s.to_dict() for s in list(self._sessions.values())[-50:]],
                samples=[s.to_dict() for s in list(self._samples.values())[-100:]],
                bottlenecks=[b.to_dict() for b in list(self._bottlenecks.values())[-100:]],
                optimizations=[o.to_dict() for o in list(self._optimizations.values())[-100:]],
                hotspots=[h.to_dict() for h in list(self._hotspots.values())[-50:]],
                baselines=[b.to_dict() for b in list(self._baselines.values())[-50:]],
                frame_metrics=[f.to_dict() for f in self._frame_metrics[-100:]],
                results=[r.to_dict() for r in list(self._results.values())[-50:]],
                stats=self._stats.to_dict(),
            )
            return snapshot.to_dict()

    def get_config(self) -> ProfilerConfig:
        with self._lock:
            return self._config

    def set_config(self, **kwargs: Any) -> Tuple[bool, str, ProfilerConfig]:
        """Update tunable configuration fields.

        Only known fields on ProfilerConfig are accepted. Numeric fields are
        coerced and clamped to safe ranges.
        """
        with self._lock:
            known = set(self._config.__dataclass_fields__.keys())
            applied: List[str] = []
            for key, value in kwargs.items():
                if key not in known or key == "metadata":
                    continue
                if key in ("max_sessions", "max_samples", "max_bottlenecks",
                           "max_optimizations", "max_results", "max_hotspots",
                           "max_baselines", "max_frame_metrics", "max_events"):
                    setattr(self._config, key,
                            max(1, _safe_int(value, getattr(self._config, key))))
                elif key == "auto_identify_bottlenecks":
                    self._config.auto_identify_bottlenecks = bool(value)
                elif key == "auto_suggest_optimizations":
                    self._config.auto_suggest_optimizations = bool(value)
                elif key == "auto_apply_threshold":
                    self._config.auto_apply_threshold = _clamp(
                        _safe_float(value, 0.6), 0.0, 1.0)
                elif key == "target_fps":
                    self._config.target_fps = max(1.0, _safe_float(value, 60.0))
                elif key == "sample_interval_ms":
                    self._config.sample_interval_ms = max(
                        0.1, _safe_float(value, 16.6))
                elif key == "enabled_categories":
                    if isinstance(value, (list, tuple, set)):
                        self._config.enabled_categories = [str(v) for v in value]
                    else:
                        continue
                else:
                    continue
                applied.append(key)

            if not applied:
                return False, "no valid config fields supplied", self._config

            self._emit("config_updated", data={"fields": applied})
            return True, "updated", self._config

    # ------------------------------------------------------------------
    # Tick and Lifecycle
    # ------------------------------------------------------------------

    def tick(self, dt: float = 1.0) -> Dict[str, Any]:
        """Advance the profiler by one tick.

        Increments the tick counter, refreshes statistics, and runs the
        automatic passes (bottleneck identification, optimization suggestion,
        and auto-application) for eligible sessions when enabled.
        """
        dt_seconds = max(0.0, _safe_float(dt, 1.0))
        with self._lock:
            self._tick_count += 1
            self._refresh_stats()

            # Accumulate duration on active continuous/benchmark sessions.
            advanced_sessions: List[str] = []
            for session in self._sessions.values():
                if session.status == ProfileStatus.PROFILING.value:
                    session.duration_seconds = round(
                        session.duration_seconds + dt_seconds, 4)
                    advanced_sessions.append(session.session_id)

            # Auto-apply eligible optimizations when the threshold is positive.
            auto_applied: List[str] = []
            if (self._config.auto_apply_threshold > 0.0
                    and self._config.auto_suggest_optimizations):
                ok, _, applied = self.auto_optimize(max_applications=5)
                if ok:
                    auto_applied = applied

            self._emit("tick", data={
                "tick": self._tick_count,
                "advanced_sessions": advanced_sessions,
                "auto_applied": auto_applied,
                "dt": dt_seconds,
            })
            return {
                "status": "ok",
                "tick": self._tick_count,
                "sessions": len(self._sessions),
                "samples": len(self._samples),
                "bottlenecks": len(self._bottlenecks),
                "optimizations": len(self._optimizations),
                "advanced_sessions": advanced_sessions,
                "auto_applied": auto_applied,
                "stats": self._stats.to_dict(),
            }

    def reset(self) -> None:
        """Clear all profiler state and re-seed the canonical dataset."""
        with self._lock:
            self._sessions.clear()
            self._samples.clear()
            self._bottlenecks.clear()
            self._optimizations.clear()
            self._results.clear()
            self._hotspots.clear()
            self._baselines.clear()
            self._frame_metrics.clear()
            self._events.clear()
            self._tick_count = 0
            self._stats = ProfilerStats()
            # Re-seed without re-entering the initialized guard.
            self._seed_data()
            self._emit("profiler_reset", data={
                "tick_count": self._tick_count,
            })

    # ------------------------------------------------------------------
    # Seed Data
    # ------------------------------------------------------------------

    def _seed_data(self) -> None:
        """Populate the profiler with a canonical set of performance data."""
        base_time = datetime.utcnow()

        # ----------------------------------------------------------
        # Profile Sessions (6)
        # ----------------------------------------------------------
        session_seeds = [
            ("sess_main_gameplay", "Main Gameplay Continuous Profile",
             ProfileSessionType.CONTINUOUS, ProfileStatus.PROFILING,
             "open_world_zone_3", 1280.0,
             "Continuous profiling of the open-world gameplay loop"),
            ("sess_menu_render", "Main Menu Render Snapshot",
             ProfileSessionType.SNAPSHOT, ProfileStatus.COMPLETED,
             "main_menu", 12.5,
             "Snapshot profile of the main menu render path"),
            ("sess_benchmark_std", "Standard Benchmark Run",
             ProfileSessionType.BENCHMARK, ProfileStatus.COMPLETED,
             "benchmark_scene_std", 300.0,
             "Standardized benchmark scene at 1080p high preset"),
            ("sess_stress_1000npc", "1000 NPC Stress Test",
             ProfileSessionType.STRESS_TEST, ProfileStatus.COMPLETED,
             "city_square_dense", 180.0,
             "Stress test with 1000 simultaneous AI agents"),
            ("sess_compare_pre_opt", "Pre-Optimization Comparison Baseline",
             ProfileSessionType.COMPARISON, ProfileStatus.COMPLETED,
             "raid_boss_01", 240.0,
             "Comparison baseline before render optimization pass"),
            ("sess_mp_match", "Multiplayer Match Profile",
             ProfileSessionType.CONTINUOUS, ProfileStatus.PROFILING,
             "pvp_arena_01", 940.0,
             "Continuous profiling of a live multiplayer arena match"),
        ]
        for idx, (sid, name, stype, status, target, dur, notes) in enumerate(
                session_seeds):
            started = (base_time - timedelta_for(idx)).isoformat() + "Z"
            ended = "" if status == ProfileStatus.PROFILING else \
                (base_time - timedelta_for(idx) + timedelta_seconds(60)).isoformat() + "Z"
            session = ProfileSession(
                session_id=sid,
                name=name,
                session_type=stype.value,
                status=status.value,
                started_at=started,
                ended_at=ended,
                duration_seconds=dur,
                target=target,
                sample_count=0,
                bottleneck_count=0,
                optimization_count=0,
                notes=notes,
                metadata={"seed": True},
            )
            self._sessions[sid] = session

        # ----------------------------------------------------------
        # Profile Samples (14)
        # ----------------------------------------------------------
        sample_seeds = [
            ("smp_frame_01", "sess_main_gameplay", ProfileCategory.CPU,
             MetricType.FRAME_TIME, 22.4, "ms", 16.6, 1024),
            ("smp_frame_02", "sess_main_gameplay", ProfileCategory.GPU,
             MetricType.GPU_TIME, 18.9, "ms", 16.6, 1024),
            ("smp_draw_01", "sess_main_gameplay", ProfileCategory.RENDER,
             MetricType.DRAW_CALLS, 2840.0, "count", 2000.0, 1024),
            ("smp_tri_01", "sess_main_gameplay", ProfileCategory.RENDER,
             MetricType.TRIANGLES, 4_200_000.0, "count", 3_000_000.0, 1024),
            ("smp_mem_01", "sess_main_gameplay", ProfileCategory.MEMORY,
             MetricType.MEMORY_USAGE, 2380.0, "MB", 2048.0, 1024),
            ("smp_net_01", "sess_mp_match", ProfileCategory.NETWORK,
             MetricType.NETWORK_LATENCY, 112.0, "ms", 80.0, 8700),
            ("smp_script_01", "sess_main_gameplay", ProfileCategory.SCRIPT,
             MetricType.SCRIPT_TIME, 7.8, "ms", 6.0, 1024),
            ("smp_phys_01", "sess_stress_1000npc", ProfileCategory.PHYSICS,
             MetricType.PHYSICS_TIME, 11.2, "ms", 5.0, 9200),
            ("smp_io_01", "sess_main_gameplay", ProfileCategory.IO,
             MetricType.IO_TIME, 9.6, "ms", 8.0, 1024),
            ("smp_audio_01", "sess_main_gameplay", ProfileCategory.AUDIO,
             MetricType.AUDIO_TIME, 2.1, "ms", 3.0, 1024),
            ("smp_ai_01", "sess_stress_1000npc", ProfileCategory.AI,
             MetricType.SCRIPT_TIME, 14.5, "ms", 6.0, 9200),
            ("smp_gpu_menu", "sess_menu_render", ProfileCategory.GPU,
             MetricType.GPU_TIME, 4.2, "ms", 16.6, 10),
            ("smp_bench_ft", "sess_benchmark_std", ProfileCategory.CPU,
             MetricType.FRAME_TIME, 14.8, "ms", 16.6, 18000),
            ("smp_bench_dc", "sess_benchmark_std", ProfileCategory.RENDER,
             MetricType.DRAW_CALLS, 1620.0, "count", 2000.0, 18000),
        ]
        for sid, sess, cat, met, val, unit, thr, frame in sample_seeds:
            ts = (base_time - timedelta_seconds(120)).isoformat() + "Z"
            sample = ProfileSample(
                sample_id=sid,
                session_id=sess,
                category=cat.value,
                metric=met.value,
                value=val,
                unit=unit,
                threshold=thr,
                timestamp=ts,
                frame_number=frame,
                context={"location": f"{cat.value}_subsystem"},
                metadata={"seed": True},
            )
            self._samples[sid] = sample

        # ----------------------------------------------------------
        # Bottlenecks (6) - registered directly to control IDs.
        # ----------------------------------------------------------
        bottleneck_seeds = [
            ("btl_frame_time", "sess_main_gameplay", ProfileCategory.CPU,
             BottleneckSeverity.MEDIUM, MetricType.FRAME_TIME, 22.4, 16.6,
             "Frame time exceeds 60 FPS budget",
             "Main gameplay frame time averaged 22.4ms against a 16.6ms "
             "budget, dropping effective FPS below 45.",
             "open_world_zone_3/update_loop", ["smp_frame_01"]),
            ("btl_draw_calls", "sess_main_gameplay", ProfileCategory.RENDER,
             BottleneckSeverity.HIGH, MetricType.DRAW_CALLS, 2840.0, 2000.0,
             "Draw call count over budget",
             "Render submission issued 2840 draw calls against a 2000 budget, "
             "indicating insufficient batching.",
             "render/forward_renderer", ["smp_draw_01"]),
            ("btl_memory", "sess_main_gameplay", ProfileCategory.MEMORY,
             BottleneckSeverity.HIGH, MetricType.MEMORY_USAGE, 2380.0, 2048.0,
             "Resident memory over budget",
             "Resident memory reached 2380MB against a 2048MB budget, "
             "risking low-memory device crashes.",
             "memory/asset_cache", ["smp_mem_01"]),
            ("btl_network", "sess_mp_match", ProfileCategory.NETWORK,
             BottleneckSeverity.MEDIUM, MetricType.NETWORK_LATENCY, 112.0, 80.0,
             "Network latency spike",
             "Network latency spiked to 112ms against an 80ms budget during "
             "the multiplayer arena match.",
             "net/replication_manager", ["smp_net_01"]),
            ("btl_physics", "sess_stress_1000npc", ProfileCategory.PHYSICS,
             BottleneckSeverity.CRITICAL, MetricType.PHYSICS_TIME, 11.2, 5.0,
             "Physics solve time critical",
             "Physics solve consumed 11.2ms against a 5ms budget under the "
             "1000 NPC stress test, more than 2x the budget.",
             "physics/broadphase_solver", ["smp_phys_01"]),
            ("btl_ai_script", "sess_stress_1000npc", ProfileCategory.AI,
             BottleneckSeverity.CRITICAL, MetricType.SCRIPT_TIME, 14.5, 6.0,
             "AI script time critical",
             "AI thinking script time reached 14.5ms against a 6ms budget "
             "with 1000 active agents.",
             "ai/agent_brain", ["smp_ai_01"]),
        ]
        for bid, sess, cat, sev, met, val, thr, title, desc, loc, sids in \
                bottleneck_seeds:
            impact = self._impact_for(val, thr, sev.value)
            bottleneck = Bottleneck(
                bottleneck_id=bid,
                session_id=sess,
                category=cat.value,
                severity=sev.value,
                metric=met.value,
                observed_value=val,
                threshold_value=thr,
                impact_score=round(impact, 4),
                title=title,
                description=desc,
                location=loc,
                sample_ids=sids,
                identified_at=(base_time - timedelta_seconds(100)).isoformat() + "Z",
                status="open",
                metadata={"seed": True},
            )
            self._bottlenecks[bid] = bottleneck

        # ----------------------------------------------------------
        # Optimization Suggestions (7) tied to the seeded bottlenecks.
        # ----------------------------------------------------------
        suggestion_seeds = [
            ("opt_batch_draws", "btl_draw_calls", ProfileCategory.RENDER,
             OptimizationType.BATCH, "Batch draw calls by material",
             "Group render items sharing the same material into instanced "
             "draw calls to cut submission overhead.",
             0.25, "low", "medium", 0.82),
            ("opt_lod_distance", "btl_draw_calls", ProfileCategory.RENDER,
             OptimizationType.LOD, "Apply distance-based level of detail",
             "Swap high-poly meshes for lower-detail variants past a distance "
             "threshold to reduce triangle throughput.",
             0.22, "low", "low", 0.78),
            ("opt_stream_assets", "btl_memory", ProfileCategory.MEMORY,
             OptimizationType.STREAM, "Stream large assets on demand",
             "Page large textures and meshes in and out based on camera "
             "proximity instead of keeping them resident.",
             0.28, "medium", "high", 0.74),
            ("opt_compress_textures", "btl_memory", ProfileCategory.MEMORY,
             OptimizationType.COMPRESS, "Use block-compressed textures",
             "Convert uncompressed textures to BCn or ASTC block formats to "
             "shrink memory footprint.",
             0.15, "low", "low", 0.85),
            ("opt_defer_replication", "btl_network", ProfileCategory.NETWORK,
             OptimizationType.DEFER, "Defer non-critical replication",
             "Lower the send rate for distant entities and interpolate their "
             "state on the client.",
             0.18, "low", "low", 0.70),
            ("opt_split_physics", "btl_physics", ProfileCategory.PHYSICS,
             OptimizationType.SPLIT, "Split the physics island",
             "Partition the simulation into independent islands so solver "
             "iterations run on smaller contact sets.",
             0.15, "medium", "medium", 0.68),
            ("opt_ai_lod", "btl_ai_script", ProfileCategory.AI,
             OptimizationType.LOD, "AI level of detail",
             "Reduce decision frequency and planner depth for distant agents "
             "to scale the update budget with proximity.",
             0.22, "low", "low", 0.80),
        ]
        for sid, bid, cat, ot, title, desc, gain, risk, effort, conf in \
                suggestion_seeds:
            suggestion = OptimizationSuggestion(
                suggestion_id=sid,
                bottleneck_id=bid,
                category=cat.value,
                optimization_type=ot.value,
                title=title,
                description=desc,
                expected_gain=gain,
                risk_level=risk,
                effort_level=effort,
                confidence=conf,
                prerequisites=[],
                side_effects=[],
                status=OptimizationStatus.PENDING.value,
                created_at=(base_time - timedelta_seconds(90)).isoformat() + "Z",
                metadata={"seed": True},
            )
            self._optimizations[sid] = suggestion

        # ----------------------------------------------------------
        # Frame Metrics (10) - a trending series for the main session.
        # ----------------------------------------------------------
        frame_time_series = [18.2, 19.6, 20.4, 21.1, 22.4, 21.8, 22.9, 23.5,
                             22.1, 21.4]
        for i, ft in enumerate(frame_time_series):
            fps = round(1000.0 / ft, 2) if ft > 0 else 0.0
            frame = FrameMetrics(
                frame_id=f"frm_seed_{i:02d}",
                session_id="sess_main_gameplay",
                frame_number=1024 + i,
                frame_time=ft,
                fps=fps,
                gpu_time=round(ft * 0.45, 4),
                cpu_time=round(ft * 0.40, 4),
                render_time=round(ft * 0.35, 4),
                draw_calls=2700 + i * 20,
                triangles=4_000_000 + i * 50000,
                vertices=4_200_000 + i * 60000,
                memory_usage=2300.0 + i * 8.0,
                network_latency=45.0 + i * 1.5,
                io_time=round(7.2 + i * 0.3, 4),
                script_time=round(6.8 + i * 0.2, 4),
                physics_time=round(4.2 + i * 0.15, 4),
                audio_time=2.1,
                timestamp=(base_time - timedelta_seconds(60 - i)).isoformat() + "Z",
                metadata={"seed": True},
            )
            self._frame_metrics.append(frame)

        # ----------------------------------------------------------
        # Hotspots (5)
        # ----------------------------------------------------------
        hotspot_seeds = [
            ("hot_render_loop", "sess_main_gameplay", HotspotType.RENDER_LOOP,
             "ForwardRenderer::submit", "render/forward_renderer.cpp:412",
             8.2, 9.1, 1, 36.5, ProfileCategory.RENDER, "0xab12cd"),
            ("hot_update_loop", "sess_main_gameplay", HotspotType.UPDATE_LOOP,
             "World::tick_systems", "world/world.cpp:188",
             6.4, 7.0, 1, 28.0, ProfileCategory.CPU, "0xef34ab"),
            ("hot_script_bind", "sess_main_gameplay", HotspotType.SCRIPT_BIND,
             "ScriptVM::call_native", "script/vm.cpp:901",
             3.8, 4.2, 1240, 16.8, ProfileCategory.SCRIPT, "0x12cd56"),
            ("hot_asset_load", "sess_main_gameplay", HotspotType.ASSET_LOADING,
             "AssetCache::load_sync", "assets/cache.cpp:240",
             2.9, 3.4, 12, 13.6, ProfileCategory.LOADING, "0x78ab90"),
            ("hot_gc", "sess_stress_1000npc", HotspotType.GARBAGE_COLLECTION,
             "GC::collect_minor", "memory/gc.cpp:512",
             4.6, 5.1, 3, 20.4, ProfileCategory.MEMORY, "0xcd56ef"),
        ]
        for hid, sess, ht, name, loc, st, tt, calls, pct, cat, sh in \
                hotspot_seeds:
            hotspot = Hotspot(
                hotspot_id=hid,
                session_id=sess,
                hotspot_type=ht.value,
                name=name,
                location=loc,
                self_time=st,
                total_time=tt,
                call_count=calls,
                percentage=pct,
                category=cat.value,
                stack_hash=sh,
                metadata={"seed": True},
            )
            self._hotspots[hid] = hotspot

        # ----------------------------------------------------------
        # Baselines (4)
        # ----------------------------------------------------------
        baseline_seeds = [
            ("base_v1_release", "v1.0 Release Baseline",
             "Performance baseline captured at the v1.0 release candidate.",
             60.0, 16.6, 2048.0, 2000, "sess_benchmark_std",
             {"avg_frame_time": 14.8, "avg_fps": 67.5, "avg_gpu_time": 6.2,
              "avg_cpu_time": 5.8, "avg_memory": 1820.0, "avg_draw_calls": 1620.0}),
            ("base_v11_release", "v1.1 Release Baseline",
             "Performance baseline captured at the v1.1 release candidate.",
             60.0, 16.6, 2048.0, 2000, "sess_benchmark_std",
             {"avg_frame_time": 13.9, "avg_fps": 71.9, "avg_gpu_time": 5.9,
              "avg_cpu_time": 5.4, "avg_memory": 1740.0, "avg_draw_calls": 1580.0}),
            ("base_optimized", "Optimized Build Baseline",
             "Baseline after the render optimization pass for comparison.",
             60.0, 16.6, 1800.0, 1600, "sess_compare_pre_opt",
             {"avg_frame_time": 12.4, "avg_fps": 80.6, "avg_gpu_time": 5.1,
              "avg_cpu_time": 5.0, "avg_memory": 1620.0, "avg_draw_calls": 1340.0}),
            ("base_target", "Target Performance Baseline",
             "The performance target the engine must meet on min-spec hardware.",
             60.0, 16.6, 1500.0, 1500, "",
             {"avg_frame_time": 16.6, "avg_fps": 60.0, "avg_gpu_time": 6.0,
              "avg_cpu_time": 6.0, "avg_memory": 1500.0, "avg_draw_calls": 1500.0}),
        ]
        for bid, name, desc, tfps, tft, mm, mdc, sess, metrics in \
                baseline_seeds:
            baseline = PerformanceBaseline(
                baseline_id=bid,
                name=name,
                description=desc,
                created_at=(base_time - timedelta_seconds(200)).isoformat() + "Z",
                metrics=metrics,
                target_fps=tfps,
                target_frame_time=tft,
                max_memory=mm,
                max_draw_calls=mdc,
                session_id=sess,
                metadata={"seed": True},
            )
            self._baselines[bid] = baseline

        # ----------------------------------------------------------
        # Optimization Results (4) - applied outcomes with before/after.
        # ----------------------------------------------------------
        result_seeds = [
            ("res_batch_applied", "opt_batch_draws", "btl_draw_calls",
             OptimizationType.BATCH, OptimizationStatus.APPLIED,
             2840.0, 2180.0, "draw_calls", "Batched 660 draw calls via instancing."),
            ("res_compress_applied", "opt_compress_textures", "btl_memory",
             OptimizationType.COMPRESS, OptimizationStatus.APPLIED,
             2380.0, 1980.0, "memory_usage", "Compressed 14 large textures to BC7."),
            ("res_lod_reverted", "opt_lod_distance", "btl_draw_calls",
             OptimizationType.LOD, OptimizationStatus.REVERTED,
             2180.0, 2150.0, "draw_calls",
             "LOD pop was too visible at close range; reverted pending tuning."),
            ("res_defer_applied", "opt_defer_replication", "btl_network",
             OptimizationType.DEFER, OptimizationStatus.APPLIED,
             112.0, 74.0, "network_latency",
             "Distant entity replication rate halved with client interpolation."),
        ]
        for rid, sid, bid, ot, status, before, after, metric, notes in \
                result_seeds:
            improvement = 0.0
            if before > 0:
                improvement = round(((before - after) / before) * 100.0, 4)
            result = OptimizationResult(
                result_id=rid,
                suggestion_id=sid,
                bottleneck_id=bid,
                optimization_type=ot.value,
                status=status.value,
                applied_at=(base_time - timedelta_seconds(80)).isoformat() + "Z",
                reverted_at=((base_time - timedelta_seconds(40)).isoformat() + "Z"
                             if status == OptimizationStatus.REVERTED else ""),
                before_value=before,
                after_value=after,
                improvement_percent=improvement,
                actual_gain=round(before - after, 4),
                metric=metric,
                notes=notes,
                metadata={"seed": True},
            )
            self._results[rid] = result
            # Sync the linked suggestion status with the result.
            suggestion = self._optimizations.get(sid)
            if suggestion is not None:
                suggestion.status = status.value

        # ----------------------------------------------------------
        # Events (6)
        # ----------------------------------------------------------
        self._emit("profiler_seeded", data={
            "sessions": len(self._sessions),
            "samples": len(self._samples),
            "bottlenecks": len(self._bottlenecks),
            "optimizations": len(self._optimizations),
            "hotspots": len(self._hotspots),
            "baselines": len(self._baselines),
            "frame_metrics": len(self._frame_metrics),
            "results": len(self._results),
        })
        self._emit("session_started", session_id="sess_main_gameplay", data={
            "name": "Main Gameplay Continuous Profile",
            "session_type": "continuous",
        })
        self._emit("bottleneck_identified", session_id="sess_main_gameplay",
                   data={"bottleneck_id": "btl_frame_time",
                         "severity": "medium"})
        self._emit("optimization_applied", session_id="sess_main_gameplay",
                   data={"suggestion_id": "opt_batch_draws",
                         "result_id": "res_batch_applied",
                         "improvement_percent": 23.24})
        self._emit("optimization_reverted", session_id="sess_main_gameplay",
                   data={"suggestion_id": "opt_lod_distance",
                         "result_id": "res_lod_reverted"})
        self._emit("baseline_created", data={
            "baseline_id": "base_v1_release",
            "name": "v1.0 Release Baseline",
        })

        self._refresh_stats()


# ---------------------------------------------------------------------------
# Local datetime helpers for seed timestamps
# ---------------------------------------------------------------------------

def timedelta_seconds(seconds: float):
    """Return a timedelta of the given seconds; isolated for readability."""
    from datetime import timedelta
    return timedelta(seconds=max(0.0, float(seconds)))


def timedelta_for(index: int):
    """Return a timedelta scaling with the seed index for staggered timestamps."""
    from datetime import timedelta
    return timedelta(hours=max(0, index + 1))


# ---------------------------------------------------------------------------
# Factory Function
# ---------------------------------------------------------------------------


def get_ai_performance_profiler() -> AIPerformanceProfiler:
    """Return the shared AIPerformanceProfiler singleton instance."""
    return AIPerformanceProfiler.get_instance()


# ---------------------------------------------------------------------------
# Exported Symbols
# ---------------------------------------------------------------------------

__all__ = [
    # Enums
    "ProfileCategory",
    "BottleneckSeverity",
    "OptimizationType",
    "ProfileStatus",
    "MetricType",
    "OptimizationStatus",
    "ProfileSessionType",
    "HotspotType",
    # Data classes
    "ProfileSample",
    "Bottleneck",
    "OptimizationSuggestion",
    "ProfileSession",
    "FrameMetrics",
    "Hotspot",
    "PerformanceBaseline",
    "OptimizationResult",
    "ProfilerConfig",
    "ProfilerStats",
    "ProfilerSnapshot",
    "ProfilerEvent",
    # Main system
    "AIPerformanceProfiler",
    "get_ai_performance_profiler",
]
