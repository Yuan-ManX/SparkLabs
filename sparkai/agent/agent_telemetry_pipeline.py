"""
SparkLabs Agent - Telemetry Pipeline

Structured metrics streaming to analytics and sink destinations.
Provides a configurable pipeline for emitting agent-level metrics,
registering output sinks (stdout, file, http, websocket, kafka,
cloudwatch), setting aggregation policies, and flushing buffered
metrics on demand with throughput monitoring.

Architecture:
  AgentTelemetryPipeline
    |-- TelemetryMetric (individual data point with tags and value)
    |-- PipelineSink (destination configuration for metric delivery)
    |-- AggregationWindow (time-bounded aggregation policy per metric)
    |-- PipelineStats (cumulative pipeline throughput and health)
"""

from __future__ import annotations

import json
import math
import threading
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class SinkType(Enum):
    STDOUT = "stdout"
    FILE = "file"
    HTTP = "http"
    WEBSOCKET = "websocket"
    KAFKA = "kafka"
    CLOUDWATCH = "cloudwatch"


class MetricFormat(Enum):
    JSON = "json"
    AVRO = "avro"
    PROTOBUF = "protobuf"
    MSGPACK = "msgpack"
    PLAINTEXT = "plaintext"


class AggregationMode(Enum):
    RAW = "raw"
    AVERAGE = "average"
    SUM = "sum"
    MIN = "min"
    MAX = "max"
    PERCENTILE = "percentile"


@dataclass
class TelemetryMetric:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    agent_id: str = ""
    metric_name: str = ""
    value: float = 0.0
    tags: Dict[str, str] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "agent_id": self.agent_id,
            "metric_name": self.metric_name,
            "value": self.value,
            "tags": self.tags,
            "timestamp": self.timestamp,
        }


@dataclass
class PipelineSink:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = ""
    sink_type: SinkType = SinkType.STDOUT
    format: MetricFormat = MetricFormat.JSON
    config: Dict[str, Any] = field(default_factory=dict)
    enabled: bool = True
    buffered_count: int = 0
    total_flushed: int = 0
    last_flush_at: float = field(default_factory=time.time)
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "sink_type": self.sink_type.value,
            "format": self.format.value,
            "config": self.config,
            "enabled": self.enabled,
            "buffered_count": self.buffered_count,
            "total_flushed": self.total_flushed,
            "last_flush_at": self.last_flush_at,
            "created_at": self.created_at,
        }


@dataclass
class AggregationWindow:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    sink_id: str = ""
    metric_name: str = ""
    mode: AggregationMode = AggregationMode.AVERAGE
    window_seconds: float = 60.0
    values_buffer: List[float] = field(default_factory=list)
    last_aggregated: Dict[str, Any] = field(default_factory=dict)
    window_start: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "sink_id": self.sink_id,
            "metric_name": self.metric_name,
            "mode": self.mode.value,
            "window_seconds": self.window_seconds,
            "buffer_size": len(self.values_buffer),
            "last_aggregated": self.last_aggregated,
            "window_start": self.window_start,
        }


@dataclass
class PipelineStats:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    total_metrics_emitted: int = 0
    total_metrics_flushed: int = 0
    total_sinks: int = 0
    active_sinks: int = 0
    pending_metric_count: int = 0
    throughput_per_second: float = 0.0
    last_emit_at: float = field(default_factory=time.time)
    recorded_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "total_metrics_emitted": self.total_metrics_emitted,
            "total_metrics_flushed": self.total_metrics_flushed,
            "total_sinks": self.total_sinks,
            "active_sinks": self.active_sinks,
            "pending_metric_count": self.pending_metric_count,
            "throughput_per_second": self.throughput_per_second,
            "last_emit_at": self.last_emit_at,
            "recorded_at": self.recorded_at,
        }


class AgentTelemetryPipeline:
    """Structured metrics streaming to analytics and sink destinations."""

    _instance: Optional["AgentTelemetryPipeline"] = None
    _lock = threading.RLock()

    _DEFAULT_WINDOW_SECONDS: float = 60.0
    _MAX_BUFFER_SIZE: int = 10000
    _MAX_SINKS: int = 50
    _THROUGHPUT_WINDOW: float = 10.0

    def __init__(self) -> None:
        self._sinks: Dict[str, PipelineSink] = {}
        self._metrics: Dict[str, List[TelemetryMetric]] = {}
        self._aggregations: Dict[str, AggregationWindow] = {}
        self._emit_timestamps: List[float] = []

    @classmethod
    def get_instance(cls) -> "AgentTelemetryPipeline":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    # ---- Sink Registration ----

    def register_sink(self,
                      name: str,
                      sink_type: str = "stdout",
                      config: Optional[Dict[str, Any]] = None,
                      format_type: str = "json") -> PipelineSink:
        with self._lock:
            if len(self._sinks) >= self._MAX_SINKS:
                oldest_id = min(
                    self._sinks.keys(),
                    key=lambda sid: self._sinks[sid].created_at,
                )
                del self._sinks[oldest_id]

            sink = PipelineSink(
                name=name,
                sink_type=self._parse_sink_type(sink_type),
                format=self._parse_format(format_type),
                config=config or {},
            )
            self._sinks[sink.id] = sink
            self._metrics[sink.id] = []
            return sink

    def update_sink(self, sink_id: str, config: Dict[str, Any]) -> bool:
        sink = self._sinks.get(sink_id)
        if sink is None:
            return False
        sink.config.update(config)
        return True

    def enable_sink(self, sink_id: str) -> bool:
        sink = self._sinks.get(sink_id)
        if sink is None:
            return False
        sink.enabled = True
        return True

    def disable_sink(self, sink_id: str) -> bool:
        sink = self._sinks.get(sink_id)
        if sink is None:
            return False
        sink.enabled = False
        return True

    def remove_sink(self, sink_id: str) -> bool:
        if sink_id in self._sinks:
            del self._sinks[sink_id]
            self._metrics.pop(sink_id, None)
            self._aggregations = {
                aid: agg for aid, agg in self._aggregations.items()
                if agg.sink_id != sink_id
            }
            return True
        return False

    def get_sink(self, sink_id: str) -> Optional[PipelineSink]:
        return self._sinks.get(sink_id)

    def list_sinks(self, sink_type: str = "") -> List[PipelineSink]:
        sinks = list(self._sinks.values())
        if sink_type:
            try:
                type_enum = SinkType(sink_type)
                sinks = [s for s in sinks if s.sink_type == type_enum]
            except ValueError:
                pass
        return sinks

    # ---- Metric Emission ----

    def emit_metric(self,
                    agent_id: str,
                    metric_name: str,
                    value: float,
                    tags: Optional[Dict[str, str]] = None) -> Optional[TelemetryMetric]:
        active_sinks = [s for s in self._sinks.values() if s.enabled]
        if not active_sinks:
            return None

        metric = TelemetryMetric(
            agent_id=agent_id,
            metric_name=metric_name,
            value=value,
            tags=tags or {},
        )

        with self._lock:
            for sink in active_sinks:
                self._metrics[sink.id].append(metric)
                sink.buffered_count += 1
                if len(self._metrics[sink.id]) > self._MAX_BUFFER_SIZE:
                    overflow = len(self._metrics[sink.id]) - self._MAX_BUFFER_SIZE
                    self._metrics[sink.id] = self._metrics[sink.id][overflow:]
                    sink.buffered_count = len(self._metrics[sink.id])

            self._emit_timestamps.append(metric.timestamp)
            cutoff = metric.timestamp - self._THROUGHPUT_WINDOW
            self._emit_timestamps = [ts for ts in self._emit_timestamps if ts >= cutoff]

        return metric

    def emit_batch(self,
                   agent_id: str,
                   metrics: List[Dict[str, Any]]) -> List[TelemetryMetric]:
        results: List[TelemetryMetric] = []
        for entry in metrics:
            result = self.emit_metric(
                agent_id=agent_id,
                metric_name=entry.get("metric_name", ""),
                value=entry.get("value", 0.0),
                tags=entry.get("tags", {}),
            )
            if result:
                results.append(result)
        return results

    # ---- Aggregation ----

    def set_aggregation(self,
                        sink_id: str,
                        metric_name: str,
                        mode: str = "average",
                        window_seconds: float = 60.0) -> Optional[AggregationWindow]:
        sink = self._sinks.get(sink_id)
        if sink is None:
            return None

        mode_enum = self._parse_aggregation_mode(mode)
        window = AggregationWindow(
            sink_id=sink_id,
            metric_name=metric_name,
            mode=mode_enum,
            window_seconds=window_seconds,
        )
        with self._lock:
            self._aggregations[window.id] = window
        return window

    def remove_aggregation(self, aggregation_id: str) -> bool:
        if aggregation_id in self._aggregations:
            del self._aggregations[aggregation_id]
            return True
        return False

    def get_aggregation(self, aggregation_id: str) -> Optional[AggregationWindow]:
        return self._aggregations.get(aggregation_id)

    def list_aggregations(self, sink_id: str = "") -> List[AggregationWindow]:
        aggregations = list(self._aggregations.values())
        if sink_id:
            aggregations = [a for a in aggregations if a.sink_id == sink_id]
        return aggregations

    def _aggregate_values(self,
                          values: List[float],
                          mode: AggregationMode) -> float:
        if not values:
            return 0.0

        if mode == AggregationMode.RAW:
            return values[-1]
        if mode == AggregationMode.SUM:
            return sum(values)
        if mode == AggregationMode.AVERAGE:
            return sum(values) / len(values)
        if mode == AggregationMode.MIN:
            return min(values)
        if mode == AggregationMode.MAX:
            return max(values)
        if mode == AggregationMode.PERCENTILE:
            sorted_values = sorted(values)
            index = int(len(sorted_values) * 0.95)
            return sorted_values[min(index, len(sorted_values) - 1)]
        return values[-1]

    # ---- Flushing ----

    def flush_sink(self, sink_id: str) -> int:
        sink = self._sinks.get(sink_id)
        if sink is None:
            return 0

        with self._lock:
            metrics = self._metrics.get(sink_id, [])
            if not metrics:
                return 0

            flushed_metrics = self._apply_aggregations(sink_id, metrics)
            self._deliver_metrics(sink, flushed_metrics)

            count = len(metrics)
            self._metrics[sink_id] = []
            sink.buffered_count = 0
            sink.total_flushed += count
            sink.last_flush_at = time.time()
            return count

    def flush_all(self) -> Dict[str, int]:
        results: Dict[str, int] = {}
        for sink_id in list(self._sinks.keys()):
            results[sink_id] = self.flush_sink(sink_id)
        return results

    def _apply_aggregations(self,
                             sink_id: str,
                             metrics: List[TelemetryMetric]) -> List[TelemetryMetric]:
        relevant_aggregations = [
            a for a in self._aggregations.values()
            if a.sink_id == sink_id
        ]

        if not relevant_aggregations:
            return metrics

        now = time.time()
        result_metrics: List[TelemetryMetric] = []

        for agg in relevant_aggregations:
            if now - agg.window_start >= agg.window_seconds:
                matching = [
                    m for m in metrics
                    if m.metric_name == agg.metric_name
                ]
                agg.values_buffer.extend([m.value for m in matching])

                aggregated_value = self._aggregate_values(
                    agg.values_buffer, agg.mode
                )

                agg.last_aggregated = {
                    "value": aggregated_value,
                    "mode": agg.mode.value,
                    "window_seconds": agg.window_seconds,
                    "samples": len(agg.values_buffer),
                    "timestamp": now,
                }

                if matching:
                    representative = matching[0]
                    result_metrics.append(TelemetryMetric(
                        agent_id=representative.agent_id,
                        metric_name=f"{agg.metric_name}_agg",
                        value=aggregated_value,
                        tags={
                            **representative.tags,
                            "aggregation_mode": agg.mode.value,
                            "samples": str(len(agg.values_buffer)),
                        },
                    ))

                agg.values_buffer.clear()
                agg.window_start = now
            else:
                matching = [
                    m for m in metrics
                    if m.metric_name == agg.metric_name
                ]
                agg.values_buffer.extend([m.value for m in matching])

        non_aggregated = [
            m for m in metrics
            if not any(
                m.metric_name == a.metric_name
                for a in relevant_aggregations
            )
        ]
        result_metrics.extend(non_aggregated)

        return result_metrics

    def _deliver_metrics(self,
                          sink: PipelineSink,
                          metrics: List[TelemetryMetric]) -> None:
        if sink.sink_type == SinkType.STDOUT:
            for metric in metrics:
                if sink.format == MetricFormat.JSON:
                    print(json.dumps(metric.to_dict()))
                elif sink.format == MetricFormat.PLAINTEXT:
                    print(f"[{metric.timestamp}] {metric.agent_id} "
                          f"{metric.metric_name}={metric.value}")
                else:
                    print(json.dumps(metric.to_dict()))
            return

        filepath = sink.config.get("filepath", "")
        if sink.sink_type == SinkType.FILE and filepath:
            try:
                import os
                os.makedirs(os.path.dirname(filepath) or ".", exist_ok=True)
                with open(filepath, "a") as f:
                    for metric in metrics:
                        if sink.format == MetricFormat.PLAINTEXT:
                            f.write(
                                f"[{metric.timestamp}] {metric.agent_id} "
                                f"{metric.metric_name}={metric.value}\n"
                            )
                        else:
                            f.write(json.dumps(metric.to_dict()) + "\n")
            except (IOError, OSError):
                pass
            return

        if sink.sink_type == SinkType.HTTP:
            headers = sink.config.get("headers", {})
            sink.config["_pending_delivery"] = [m.to_dict() for m in metrics]
            return

        if sink.sink_type == SinkType.WEBSOCKET:
            sink.config["_pending_delivery"] = [m.to_dict() for m in metrics]
            return

        if sink.sink_type == SinkType.KAFKA:
            sink.config["_pending_delivery"] = [m.to_dict() for m in metrics]
            return

        if sink.sink_type == SinkType.CLOUDWATCH:
            sink.config["_pending_delivery"] = [m.to_dict() for m in metrics]
            return

    # ---- Pending Metrics ----

    def list_pending_metrics(self,
                              sink_id: str = "") -> List[TelemetryMetric]:
        if sink_id:
            return list(self._metrics.get(sink_id, []))

        all_metrics: List[TelemetryMetric] = []
        for metrics in self._metrics.values():
            all_metrics.extend(metrics)
        all_metrics.sort(key=lambda m: m.timestamp, reverse=True)
        return all_metrics

    def get_pending_count(self, sink_id: str = "") -> int:
        if sink_id:
            return len(self._metrics.get(sink_id, []))
        return sum(len(m) for m in self._metrics.values())

    # ---- Throughput ----

    def get_throughput(self) -> float:
        now = time.time()
        cutoff = now - self._THROUGHPUT_WINDOW
        recent = sum(1 for ts in self._emit_timestamps if ts >= cutoff)
        elapsed = max(now - cutoff, 0.001)
        return recent / elapsed

    # ---- Stats & Reset ----

    def get_stats(self) -> Dict[str, Any]:
        sink_type_counts: Dict[str, int] = {}
        for sink in self._sinks.values():
            key = sink.sink_type.value
            sink_type_counts[key] = sink_type_counts.get(key, 0) + 1

        format_counts: Dict[str, int] = {}
        for sink in self._sinks.values():
            key = sink.format.value
            format_counts[key] = format_counts.get(key, 0) + 1

        total_emitted = len(self._emit_timestamps)
        total_pending = self.get_pending_count()
        total_flushed = sum(s.total_flushed for s in self._sinks.values())
        active_count = sum(1 for s in self._sinks.values() if s.enabled)

        return {
            "total_sinks": len(self._sinks),
            "active_sinks": active_count,
            "sinks_by_type": sink_type_counts,
            "sinks_by_format": format_counts,
            "total_aggregations": len(self._aggregations),
            "total_metrics_emitted": total_emitted,
            "total_metrics_pending": total_pending,
            "total_metrics_flushed": total_flushed,
            "throughput_per_second": round(self.get_throughput(), 2),
        }

    def reset(self) -> None:
        with self._lock:
            self._sinks.clear()
            self._metrics.clear()
            self._aggregations.clear()
            self._emit_timestamps.clear()

    # ---- Helpers ----

    @staticmethod
    def _parse_sink_type(sink_type: str) -> SinkType:
        sink_lower = sink_type.lower().replace(" ", "_")
        for item in SinkType:
            if item.value == sink_lower:
                return item
        return SinkType.STDOUT

    @staticmethod
    def _parse_format(format_type: str) -> MetricFormat:
        format_lower = format_type.lower().replace(" ", "_")
        for item in MetricFormat:
            if item.value == format_lower:
                return item
        return MetricFormat.JSON

    @staticmethod
    def _parse_aggregation_mode(mode: str) -> AggregationMode:
        mode_lower = mode.lower().replace(" ", "_")
        for item in AggregationMode:
            if item.value == mode_lower:
                return item
        return AggregationMode.AVERAGE


def get_telemetry_pipeline() -> AgentTelemetryPipeline:
    return AgentTelemetryPipeline.get_instance()