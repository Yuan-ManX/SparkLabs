"""
Observability System - Distributed tracing, metrics, and logging for agent operations.

Architecture:
    ObservabilitySystem/
    |-- SpanKind (operation type enumeration)
    |-- MetricType (counter, gauge, histogram enumeration)
    |-- TraceSpan (timed operation span dataclass)
    |-- MetricSnapshot (metric data point dataclass)
    |-- LogEntry (structured log dataclass)
    |-- MetricRegistry (named metric collection)
    |-- ObservabilitySystem (global observability orchestration)

Provides end-to-end visibility into agent behavior for the AI-native game engine.
Tracks LLM calls, tool invocations, game engine operations, and editor interactions
with support for span hierarchies, metric aggregation, and structured logging.
"""

from __future__ import annotations

import time
import uuid
import threading
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Callable, Dict, List, Optional


class SpanKind(Enum):
    LLM_CALL = auto()
    TOOL_CALL = auto()
    AGENT_STEP = auto()
    ENGINE_OP = auto()
    EDITOR_ACTION = auto()
    HTTP_REQUEST = auto()


class MetricType(Enum):
    COUNTER = auto()
    GAUGE = auto()
    HISTOGRAM = auto()
    TIMER = auto()


class LogLevel(Enum):
    DEBUG = 10
    INFO = 20
    WARNING = 30
    ERROR = 40


@dataclass
class TraceSpan:
    span_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    parent_id: Optional[str] = None
    trace_id: str = ""
    kind: SpanKind = SpanKind.AGENT_STEP
    name: str = ""
    started_at: float = 0.0
    ended_at: float = 0.0
    duration_ms: float = 0.0
    status: str = "ok"
    attributes: Dict[str, Any] = field(default_factory=dict)
    events: List[Dict[str, Any]] = field(default_factory=list)
    children: List["TraceSpan"] = field(default_factory=list)

    def add_event(self, name: str, attributes: Optional[Dict[str, Any]] = None) -> None:
        self.events.append({
            "name": name,
            "timestamp": time.time(),
            "attributes": attributes or {},
        })

    def set_attribute(self, key: str, value: Any) -> None:
        self.attributes[key] = value

    def finish(self, status: str = "ok") -> None:
        self.ended_at = time.time()
        self.duration_ms = (self.ended_at - self.started_at) * 1000
        self.status = status

    def to_dict(self) -> Dict[str, Any]:
        return {
            "span_id": self.span_id,
            "parent_id": self.parent_id,
            "trace_id": self.trace_id,
            "kind": self.kind.name,
            "name": self.name,
            "duration_ms": round(self.duration_ms, 3),
            "status": self.status,
            "attributes": self.attributes,
            "event_count": len(self.events),
            "child_count": len(self.children),
        }


@dataclass
class MetricSnapshot:
    metric_name: str = ""
    metric_type: MetricType = MetricType.COUNTER
    value: float = 0.0
    timestamp: float = 0.0
    labels: Dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.metric_name,
            "type": self.metric_type.name,
            "value": self.value,
            "labels": self.labels,
        }


@dataclass
class LogEntry:
    entry_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    level: LogLevel = LogLevel.INFO
    message: str = ""
    timestamp: float = 0.0
    component: str = ""
    trace_id: str = ""
    extra: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "entry_id": self.entry_id,
            "level": self.level.name,
            "message": self.message,
            "component": self.component,
            "trace_id": self.trace_id,
        }


class MetricRegistry:
    def __init__(self):
        self._counters: Dict[str, float] = {}
        self._gauges: Dict[str, float] = {}
        self._histograms: Dict[str, List[float]] = {}
        self._lock = threading.Lock()

    def increment(self, name: str, value: float = 1.0, labels: Optional[Dict[str, str]] = None) -> None:
        key = self._build_key(name, labels)
        with self._lock:
            self._counters[key] = self._counters.get(key, 0) + value

    def set_gauge(self, name: str, value: float, labels: Optional[Dict[str, str]] = None) -> None:
        key = self._build_key(name, labels)
        with self._lock:
            self._gauges[key] = value

    def record_histogram(self, name: str, value: float, labels: Optional[Dict[str, str]] = None) -> None:
        key = self._build_key(name, labels)
        with self._lock:
            if key not in self._histograms:
                self._histograms[key] = []
            self._histograms[key].append(value)

    def get_counter(self, name: str, labels: Optional[Dict[str, str]] = None) -> float:
        key = self._build_key(name, labels)
        return self._counters.get(key, 0)

    def get_gauge(self, name: str, labels: Optional[Dict[str, str]] = None) -> float:
        key = self._build_key(name, labels)
        return self._gauges.get(key, 0)

    def get_snapshot(self) -> Dict[str, Any]:
        with self._lock:
            histogram_stats = {}
            for name, values in self._histograms.items():
                if values:
                    sorted_vals = sorted(values)
                    histogram_stats[name] = {
                        "count": len(values),
                        "min": min(values),
                        "max": max(values),
                        "avg": sum(values) / len(values),
                        "p50": sorted_vals[len(sorted_vals) // 2],
                        "p95": sorted_vals[int(len(sorted_vals) * 0.95)],
                        "p99": sorted_vals[int(len(sorted_vals) * 0.99)],
                    }
            return {
                "counters": dict(self._counters),
                "gauges": dict(self._gauges),
                "histograms": histogram_stats,
            }

    def _build_key(self, name: str, labels: Optional[Dict[str, str]] = None) -> str:
        if not labels:
            return name
        label_str = ",".join(f"{k}={v}" for k, v in sorted(labels.items()))
        return f"{name}{{{label_str}}}"


class ObservabilitySystem:
    _instance: Optional["ObservabilitySystem"] = None
    _MAX_TRACES = 1000
    _MAX_LOGS = 2000

    def __init__(self):
        self._traces: Dict[str, TraceSpan] = {}
        self._spans: Dict[str, TraceSpan] = {}
        self._active_spans: Dict[str, str] = {}
        self._metrics = MetricRegistry()
        self._logs: List[LogEntry] = []
        self._lock = threading.Lock()
        self._enabled: bool = True

    @classmethod
    def get_instance(cls) -> "ObservabilitySystem":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def start_trace(self, name: str, kind: SpanKind = SpanKind.AGENT_STEP,
                    parent_id: Optional[str] = None, attributes: Optional[Dict[str, Any]] = None) -> TraceSpan:
        if not self._enabled:
            return TraceSpan(name=name)

        trace_id = str(uuid.uuid4())
        span = TraceSpan(
            trace_id=trace_id,
            parent_id=parent_id,
            kind=kind,
            name=name,
            started_at=time.time(),
            attributes=attributes or {},
        )
        with self._lock:
            self._traces[trace_id] = span
            self._spans[span.span_id] = span
            self._trim_traces()
        return span

    def start_child_span(self, name: str, kind: SpanKind = SpanKind.TOOL_CALL,
                         parent: Optional[TraceSpan] = None,
                         attributes: Optional[Dict[str, Any]] = None) -> TraceSpan:
        if not self._enabled:
            return TraceSpan(name=name)

        span = TraceSpan(
            trace_id=parent.trace_id if parent else str(uuid.uuid4()),
            parent_id=parent.span_id if parent else None,
            kind=kind,
            name=name,
            started_at=time.time(),
            attributes=attributes or {},
        )
        with self._lock:
            self._spans[span.span_id] = span
            if parent:
                parent.children.append(span)
        return span

    def finish_span(self, span: TraceSpan, status: str = "ok") -> None:
        span.finish(status)
        self._metrics.record_histogram("span.duration_ms", span.duration_ms,
                                        {"kind": span.kind.name, "name": span.name})
        self._metrics.increment("span.completed", labels={"status": status})

    def counter(self, name: str, value: float = 1.0, labels: Optional[Dict[str, str]] = None) -> None:
        self._metrics.increment(name, value, labels)

    def gauge(self, name: str, value: float, labels: Optional[Dict[str, str]] = None) -> None:
        self._metrics.set_gauge(name, value, labels)

    def histogram(self, name: str, value: float, labels: Optional[Dict[str, str]] = None) -> None:
        self._metrics.record_histogram(name, value, labels)

    def log(self, level: LogLevel, message: str, component: str = "",
            trace_id: str = "", extra: Optional[Dict[str, Any]] = None) -> None:
        if not self._enabled:
            return
        entry = LogEntry(
            level=level,
            message=message,
            timestamp=time.time(),
            component=component,
            trace_id=trace_id,
            extra=extra or {},
        )
        with self._lock:
            self._logs.append(entry)
            self._trim_logs()
        self._metrics.increment("log.entries", labels={"level": level.name})

    def get_recent_logs(self, limit: int = 100, level: Optional[LogLevel] = None) -> List[LogEntry]:
        with self._lock:
            logs = list(self._logs)
        if level:
            logs = [l for l in logs if l.level == level]
        return logs[-limit:]

    def get_recent_traces(self, limit: int = 50) -> List[Dict[str, Any]]:
        with self._lock:
            traces = list(self._traces.values())
        traces.sort(key=lambda t: t.started_at, reverse=True)
        return [t.to_dict() for t in traces[:limit]]

    def get_metric_snapshot(self) -> Dict[str, Any]:
        return self._metrics.get_snapshot()

    def get_stats(self) -> Dict[str, Any]:
        with self._lock:
            span_count = len(self._spans)
            trace_count = len(self._traces)
            log_count = len(self._logs)
        return {
            "enabled": self._enabled,
            "span_count": span_count,
            "trace_count": trace_count,
            "log_count": log_count,
            "metrics": self._metrics.get_snapshot(),
        }

    def set_enabled(self, enabled: bool) -> None:
        self._enabled = enabled

    def reset(self) -> None:
        with self._lock:
            self._traces.clear()
            self._spans.clear()
            self._logs.clear()
            self._metrics = MetricRegistry()

    def _trim_traces(self) -> None:
        if len(self._traces) > self._MAX_TRACES:
            keys = sorted(self._traces.keys(), key=lambda k: self._traces[k].started_at)
            for key in keys[:len(keys) - self._MAX_TRACES]:
                del self._traces[key]

    def _trim_logs(self) -> None:
        if len(self._logs) > self._MAX_LOGS:
            self._logs = self._logs[-self._MAX_LOGS:]


def get_observability() -> ObservabilitySystem:
    return ObservabilitySystem.get_instance()
