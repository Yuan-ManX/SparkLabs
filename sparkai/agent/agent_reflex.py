"""
SparkAI Agent - Reflex Engine

A self-improving feedback loop system that monitors agent performance,
identifies bottlenecks, and automatically optimizes agent behavior.
Provides real-time metrics collection, anomaly detection, and
adaptive tuning for the AI-native game engine.

Architecture:
  ReflexEngine
    |-- MetricCollector (gather performance data from all subsystems)
    |-- AnomalyDetector (identify performance deviations)
    |-- OptimizationAdvisor (generate improvement suggestions)
    |-- AdaptiveTuner (auto-adjust system parameters)
    |-- ReflexReport (comprehensive performance analysis)
"""

from __future__ import annotations

import math
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


class MetricType(Enum):
    LATENCY = "latency"
    THROUGHPUT = "throughput"
    ERROR_RATE = "error_rate"
    MEMORY = "memory"
    CPU = "cpu"
    QUEUE_DEPTH = "queue_depth"
    SUCCESS_RATE = "success_rate"
    CACHE_HIT_RATE = "cache_hit_rate"
    AGENT_UTILIZATION = "agent_utilization"
    TASK_COMPLETION = "task_completion"


class SeverityLevel(Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class AnomalyType(Enum):
    SPIKE = "spike"
    DROP = "drop"
    TREND_UP = "trend_up"
    TREND_DOWN = "trend_down"
    OSCILLATION = "oscillation"
    STALL = "stall"


class TuningAction(Enum):
    SCALE_UP = "scale_up"
    SCALE_DOWN = "scale_down"
    RETRY = "retry"
    TIMEOUT_ADJUST = "timeout_adjust"
    CACHE_RESIZE = "cache_resize"
    QUEUE_REBALANCE = "queue_rebalance"
    ROUTE_CHANGE = "route_change"
    PARAMETER_ADJUST = "parameter_adjust"
    NO_ACTION = "no_action"


class ReportStatus(Enum):
    COLLECTING = "collecting"
    ANALYZING = "analyzing"
    READY = "ready"
    APPLIED = "applied"


@dataclass
class MetricSample:
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    metric_type: MetricType = MetricType.LATENCY
    subsystem: str = ""
    value: float = 0.0
    unit: str = ""
    tags: Dict[str, str] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "metric_type": self.metric_type.value,
            "subsystem": self.subsystem,
            "value": self.value,
            "unit": self.unit,
            "tags": self.tags,
            "timestamp": self.timestamp,
        }


@dataclass
class Anomaly:
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    anomaly_type: AnomalyType = AnomalyType.SPIKE
    metric_type: MetricType = MetricType.LATENCY
    subsystem: str = ""
    severity: SeverityLevel = SeverityLevel.WARNING
    description: str = ""
    detected_value: float = 0.0
    expected_range: Tuple[float, float] = (0.0, 0.0)
    confidence: float = 0.0
    detected_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "anomaly_type": self.anomaly_type.value,
            "metric_type": self.metric_type.value,
            "subsystem": self.subsystem,
            "severity": self.severity.value,
            "description": self.description,
            "detected_value": self.detected_value,
            "expected_range": list(self.expected_range),
            "confidence": self.confidence,
            "detected_at": self.detected_at,
        }


@dataclass
class OptimizationSuggestion:
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    target_subsystem: str = ""
    tuning_action: TuningAction = TuningAction.NO_ACTION
    description: str = ""
    expected_impact: str = ""
    confidence: float = 0.0
    priority: int = 2
    parameters: Dict[str, Any] = field(default_factory=dict)
    related_anomalies: List[str] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "target_subsystem": self.target_subsystem,
            "tuning_action": self.tuning_action.value,
            "description": self.description,
            "expected_impact": self.expected_impact,
            "confidence": self.confidence,
            "priority": self.priority,
            "parameters": self.parameters,
            "related_anomalies": self.related_anomalies,
            "created_at": self.created_at,
        }


@dataclass
class ReflexReport:
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    status: ReportStatus = ReportStatus.COLLECTING
    subsystem_metrics: Dict[str, Dict[str, float]] = field(default_factory=dict)
    anomalies: List[Anomaly] = field(default_factory=list)
    suggestions: List[OptimizationSuggestion] = field(default_factory=list)
    overall_health: float = 1.0
    summary: str = ""
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "status": self.status.value,
            "subsystem_metrics": self.subsystem_metrics,
            "anomaly_count": len(self.anomalies),
            "anomalies": [a.to_dict() for a in self.anomalies],
            "suggestion_count": len(self.suggestions),
            "suggestions": [s.to_dict() for s in self.suggestions],
            "overall_health": self.overall_health,
            "summary": self.summary,
            "created_at": self.created_at,
        }


class MetricCollector:
    """
    Gathers performance metrics from all engine subsystems.
    Maintains rolling windows for trend analysis.
    """

    def __init__(self, window_size: int = 100) -> None:
        self._window_size = window_size
        self._samples: Dict[str, List[MetricSample]] = {}
        self._total_collected: int = 0

    def record(
        self,
        metric_type: MetricType,
        subsystem: str,
        value: float,
        unit: str = "",
        tags: Optional[Dict[str, str]] = None,
    ) -> MetricSample:
        sample = MetricSample(
            metric_type=metric_type,
            subsystem=subsystem,
            value=value,
            unit=unit,
            tags=tags or {},
        )

        key = f"{subsystem}:{metric_type.value}"
        self._samples.setdefault(key, []).append(sample)
        self._total_collected += 1

        if len(self._samples[key]) > self._window_size:
            self._samples[key] = self._samples[key][-self._window_size:]

        return sample

    def get_stats(self, subsystem: str, metric_type: MetricType) -> Dict[str, float]:
        key = f"{subsystem}:{metric_type.value}"
        samples = self._samples.get(key, [])

        if not samples:
            return {"count": 0, "mean": 0.0, "std": 0.0, "min": 0.0, "max": 0.0, "latest": 0.0}

        values = [s.value for s in samples]
        n = len(values)
        mean = sum(values) / n
        variance = sum((v - mean) ** 2 for v in values) / n if n > 1 else 0.0
        std = math.sqrt(variance)

        return {
            "count": n,
            "mean": round(mean, 4),
            "std": round(std, 4),
            "min": round(min(values), 4),
            "max": round(max(values), 4),
            "latest": round(values[-1], 4),
        }

    def get_recent(self, subsystem: str, metric_type: MetricType, count: int = 20) -> List[Dict[str, Any]]:
        key = f"{subsystem}:{metric_type.value}"
        samples = self._samples.get(key, [])
        return [s.to_dict() for s in samples[-count:]]

    def get_all_subsystems(self) -> List[str]:
        subsystems: set = set()
        for key in self._samples:
            subsystem = key.split(":")[0]
            subsystems.add(subsystem)
        return sorted(subsystems)

    def get_total_collected(self) -> int:
        return self._total_collected


class AnomalyDetector:
    """
    Identifies performance deviations using statistical analysis.
    Detects spikes, drops, trends, and stalls.
    """

    def __init__(self, spike_threshold: float = 3.0, trend_window: int = 10) -> None:
        self._spike_threshold = spike_threshold
        self._trend_window = trend_window
        self._anomalies: List[Anomaly] = []
        self._detection_count: int = 0

    def detect(
        self,
        subsystem: str,
        metric_type: MetricType,
        samples: List[MetricSample],
    ) -> List[Anomaly]:
        anomalies: List[Anomaly] = []

        if len(samples) < 5:
            return anomalies

        values = [s.value for s in samples]
        n = len(values)
        mean = sum(values) / n
        variance = sum((v - mean) ** 2 for v in values) / n if n > 1 else 0.0
        std = math.sqrt(variance)

        if std == 0:
            return anomalies

        latest = values[-1]
        z_score = abs(latest - mean) / std

        if z_score > self._spike_threshold:
            severity = SeverityLevel.CRITICAL if z_score > 5.0 else SeverityLevel.WARNING
            anomaly_type = AnomalyType.SPIKE if latest > mean else AnomalyType.DROP
            anomaly = Anomaly(
                anomaly_type=anomaly_type,
                metric_type=metric_type,
                subsystem=subsystem,
                severity=severity,
                description=f"{anomaly_type.value} detected: z-score={z_score:.2f}, value={latest:.2f}, mean={mean:.2f}",
                detected_value=latest,
                expected_range=(mean - 2 * std, mean + 2 * std),
                confidence=min(z_score / 5.0, 1.0),
            )
            anomalies.append(anomaly)
            self._detection_count += 1

        if len(values) >= self._trend_window:
            recent = values[-self._trend_window:]
            first_half = recent[:len(recent) // 2]
            second_half = recent[len(recent) // 2:]

            if first_half and second_half:
                first_mean = sum(first_half) / len(first_half)
                second_mean = sum(second_half) / len(second_half)

                if mean > 0:
                    change_pct = (second_mean - first_mean) / abs(mean) * 100

                    if abs(change_pct) > 20:
                        trend_type = AnomalyType.TREND_UP if change_pct > 0 else AnomalyType.TREND_DOWN
                        anomaly = Anomaly(
                            anomaly_type=trend_type,
                            metric_type=metric_type,
                            subsystem=subsystem,
                            severity=SeverityLevel.INFO,
                            description=f"{trend_type.value}: {change_pct:+.1f}% change over {self._trend_window} samples",
                            detected_value=second_mean,
                            expected_range=(first_mean * 0.8, first_mean * 1.2),
                            confidence=min(abs(change_pct) / 50.0, 1.0),
                        )
                        anomalies.append(anomaly)
                        self._detection_count += 1

        if len(values) >= 5:
            recent_5 = values[-5:]
            if all(abs(v - recent_5[0]) < 0.001 for v in recent_5):
                anomaly = Anomaly(
                    anomaly_type=AnomalyType.STALL,
                    metric_type=metric_type,
                    subsystem=subsystem,
                    severity=SeverityLevel.WARNING,
                    description=f"Metric stalled at {latest:.4f} for 5+ samples",
                    detected_value=latest,
                    expected_range=(mean - std, mean + std),
                    confidence=0.8,
                )
                anomalies.append(anomaly)
                self._detection_count += 1

        self._anomalies.extend(anomalies)
        return anomalies

    def get_recent_anomalies(self, limit: int = 20) -> List[Dict[str, Any]]:
        return [a.to_dict() for a in self._anomalies[-limit:]]

    def get_stats(self) -> Dict[str, Any]:
        severity_counts: Dict[str, int] = {}
        type_counts: Dict[str, int] = {}
        for a in self._anomalies:
            severity_counts[a.severity.value] = severity_counts.get(a.severity.value, 0) + 1
            type_counts[a.anomaly_type.value] = type_counts.get(a.anomaly_type.value, 0) + 1

        return {
            "total_detections": self._detection_count,
            "by_severity": severity_counts,
            "by_type": type_counts,
        }


class OptimizationAdvisor:
    """
    Generates improvement suggestions based on detected anomalies
    and historical performance patterns.
    """

    def __init__(self) -> None:
        self._suggestions: List[OptimizationSuggestion] = []

    def analyze(
        self,
        anomalies: List[Anomaly],
        subsystem_metrics: Dict[str, Dict[str, float]],
    ) -> List[OptimizationSuggestion]:
        suggestions: List[OptimizationSuggestion] = []

        for anomaly in anomalies:
            if anomaly.anomaly_type == AnomalyType.SPIKE and anomaly.metric_type == MetricType.LATENCY:
                suggestion = OptimizationSuggestion(
                    target_subsystem=anomaly.subsystem,
                    tuning_action=TuningAction.SCALE_UP,
                    description=f"Latency spike in {anomaly.subsystem}: consider scaling up or adding caching",
                    expected_impact="Reduce latency by 30-50%",
                    confidence=0.7,
                    priority=1 if anomaly.severity == SeverityLevel.CRITICAL else 2,
                    parameters={"action": "scale_up", "target": anomaly.subsystem},
                    related_anomalies=[anomaly.id],
                )
                suggestions.append(suggestion)

            elif anomaly.anomaly_type == AnomalyType.DROP and anomaly.metric_type == MetricType.THROUGHPUT:
                suggestion = OptimizationSuggestion(
                    target_subsystem=anomaly.subsystem,
                    tuning_action=TuningAction.QUEUE_REBALANCE,
                    description=f"Throughput drop in {anomaly.subsystem}: rebalance task queues",
                    expected_impact="Restore throughput to normal levels",
                    confidence=0.6,
                    priority=2,
                    parameters={"action": "rebalance", "target": anomaly.subsystem},
                    related_anomalies=[anomaly.id],
                )
                suggestions.append(suggestion)

            elif anomaly.anomaly_type == AnomalyType.TREND_UP and anomaly.metric_type == MetricType.ERROR_RATE:
                suggestion = OptimizationSuggestion(
                    target_subsystem=anomaly.subsystem,
                    tuning_action=TuningAction.RETRY,
                    description=f"Rising error rate in {anomaly.subsystem}: add retry logic with backoff",
                    expected_impact="Reduce error rate by 40-60%",
                    confidence=0.65,
                    priority=1,
                    parameters={"action": "retry_with_backoff", "max_retries": 3, "target": anomaly.subsystem},
                    related_anomalies=[anomaly.id],
                )
                suggestions.append(suggestion)

            elif anomaly.anomaly_type == AnomalyType.STALL:
                suggestion = OptimizationSuggestion(
                    target_subsystem=anomaly.subsystem,
                    tuning_action=TuningAction.TIMEOUT_ADJUST,
                    description=f"Stalled metric in {anomaly.subsystem}: check for deadlocks or adjust timeouts",
                    expected_impact="Resume normal processing",
                    confidence=0.5,
                    priority=2,
                    parameters={"action": "timeout_adjust", "target": anomaly.subsystem},
                    related_anomalies=[anomaly.id],
                )
                suggestions.append(suggestion)

            elif anomaly.metric_type == MetricType.CACHE_HIT_RATE:
                low, high = anomaly.expected_range
                if anomaly.detected_value < low:
                    suggestion = OptimizationSuggestion(
                        target_subsystem=anomaly.subsystem,
                        tuning_action=TuningAction.CACHE_RESIZE,
                        description=f"Low cache hit rate in {anomaly.subsystem}: increase cache size",
                        expected_impact="Improve cache hit rate by 20-40%",
                        confidence=0.6,
                        priority=2,
                        parameters={"action": "cache_resize", "target": anomaly.subsystem},
                        related_anomalies=[anomaly.id],
                    )
                    suggestions.append(suggestion)

        self._suggestions.extend(suggestions)
        return suggestions

    def get_recent_suggestions(self, limit: int = 20) -> List[Dict[str, Any]]:
        return [s.to_dict() for s in self._suggestions[-limit:]]

    def get_stats(self) -> Dict[str, Any]:
        action_counts: Dict[str, int] = {}
        for s in self._suggestions:
            action_counts[s.tuning_action.value] = action_counts.get(s.tuning_action.value, 0) + 1

        return {
            "total_suggestions": len(self._suggestions),
            "by_action": action_counts,
        }


class AdaptiveTuner:
    """
    Auto-adjusts system parameters based on optimization suggestions.
    Applies safe, reversible changes with rollback support.
    """

    def __init__(self) -> None:
        self._adjustments: List[Dict[str, Any]] = []
        self._adjustment_count: int = 0

    def apply(
        self,
        suggestion: OptimizationSuggestion,
        current_params: Dict[str, Any],
    ) -> Dict[str, Any]:
        original = dict(current_params)
        new_params = dict(current_params)

        action = suggestion.tuning_action

        if action == TuningAction.SCALE_UP:
            current = new_params.get("max_concurrent", 5)
            new_params["max_concurrent"] = min(current + 2, 20)

        elif action == TuningAction.SCALE_DOWN:
            current = new_params.get("max_concurrent", 5)
            new_params["max_concurrent"] = max(current - 1, 1)

        elif action == TuningAction.TIMEOUT_ADJUST:
            current = new_params.get("timeout_ms", 30000)
            new_params["timeout_ms"] = int(current * 1.5)

        elif action == TuningAction.CACHE_RESIZE:
            current = new_params.get("cache_size", 100)
            new_params["cache_size"] = int(current * 1.5)

        elif action == TuningAction.RETRY:
            new_params["max_retries"] = new_params.get("max_retries", 1) + 1
            new_params["retry_backoff"] = "exponential"

        elif action == TuningAction.QUEUE_REBALANCE:
            new_params["queue_strategy"] = "round_robin"

        elif action == TuningAction.ROUTE_CHANGE:
            new_params["preferred_provider"] = suggestion.parameters.get("alternative", "")

        elif action == TuningAction.PARAMETER_ADJUST:
            for k, v in suggestion.parameters.items():
                if k != "action" and k != "target":
                    new_params[k] = v

        adjustment = {
            "id": str(uuid.uuid4())[:8],
            "suggestion_id": suggestion.id,
            "action": action.value,
            "subsystem": suggestion.target_subsystem,
            "original_params": original,
            "new_params": new_params,
            "applied_at": time.time(),
        }
        self._adjustments.append(adjustment)
        self._adjustment_count += 1

        return {
            "adjustment_id": adjustment["id"],
            "action": action.value,
            "subsystem": suggestion.target_subsystem,
            "changes": {
                k: {"from": original.get(k), "to": new_params.get(k)}
                for k in new_params
                if new_params.get(k) != original.get(k)
            },
        }

    def get_adjustments(self, limit: int = 20) -> List[Dict[str, Any]]:
        return self._adjustments[-limit:]

    def get_stats(self) -> Dict[str, Any]:
        action_counts: Dict[str, int] = {}
        for adj in self._adjustments:
            action_counts[adj["action"]] = action_counts.get(adj["action"], 0) + 1

        return {
            "total_adjustments": self._adjustment_count,
            "by_action": action_counts,
        }


class ReflexEngine:
    """
    Central self-improving feedback loop system for the SparkLabs AI-native game engine.

    Monitors agent performance, identifies bottlenecks, generates
    optimization suggestions, and auto-tunes system parameters.
    """

    def __init__(self) -> None:
        self._collector = MetricCollector()
        self._detector = AnomalyDetector()
        self._advisor = OptimizationAdvisor()
        self._tuner = AdaptiveTuner()
        self._reports: List[ReflexReport] = []
        self._report_count: int = 0
        self._seed_metrics()

    def _seed_metrics(self) -> None:
        seed_data = [
            (MetricType.LATENCY, "game_coder", 120.5, "ms"),
            (MetricType.LATENCY, "world_builder", 85.3, "ms"),
            (MetricType.LATENCY, "llm_router", 45.2, "ms"),
            (MetricType.THROUGHPUT, "game_coder", 12.5, "ops/s"),
            (MetricType.THROUGHPUT, "world_builder", 8.3, "ops/s"),
            (MetricType.ERROR_RATE, "game_coder", 0.02, "ratio"),
            (MetricType.ERROR_RATE, "world_builder", 0.01, "ratio"),
            (MetricType.SUCCESS_RATE, "game_coder", 0.95, "ratio"),
            (MetricType.SUCCESS_RATE, "world_builder", 0.92, "ratio"),
            (MetricType.CACHE_HIT_RATE, "llm_router", 0.78, "ratio"),
            (MetricType.AGENT_UTILIZATION, "studio_coordinator", 0.65, "ratio"),
            (MetricType.QUEUE_DEPTH, "game_pipeline", 3, "tasks"),
            (MetricType.MEMORY, "runtime", 256.0, "MB"),
            (MetricType.TASK_COMPLETION, "studio_coordinator", 0.88, "ratio"),
        ]

        for metric_type, subsystem, value, unit in seed_data:
            self._collector.record(metric_type, subsystem, value, unit)

    def record_metric(
        self,
        metric_type: str,
        subsystem: str,
        value: float,
        unit: str = "",
        tags: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        sample = self._collector.record(
            MetricType(metric_type),
            subsystem,
            value,
            unit,
            tags,
        )
        return sample.to_dict()

    def get_metric_stats(self, subsystem: str, metric_type: str) -> Dict[str, float]:
        return self._collector.get_stats(subsystem, MetricType(metric_type))

    def get_metric_history(self, subsystem: str, metric_type: str, count: int = 20) -> List[Dict[str, Any]]:
        return self._collector.get_recent(subsystem, MetricType(metric_type), count)

    def list_subsystems(self) -> List[str]:
        return self._collector.get_all_subsystems()

    def run_analysis(self, subsystem: Optional[str] = None) -> Dict[str, Any]:
        report = ReflexReport(status=ReportStatus.COLLECTING)

        subsystems = [subsystem] if subsystem else self._collector.get_all_subsystems()

        for sub in subsystems:
            sub_metrics: Dict[str, float] = {}
            for mt in MetricType:
                stats = self._collector.get_stats(sub, mt)
                if stats["count"] > 0:
                    sub_metrics[mt.value] = stats["latest"]
            if sub_metrics:
                report.subsystem_metrics[sub] = sub_metrics

        report.status = ReportStatus.ANALYZING

        all_anomalies: List[Anomaly] = []
        for sub in subsystems:
            for mt in MetricType:
                key = f"{sub}:{mt.value}"
                samples = self._collector._samples.get(key, [])
                if len(samples) >= 5:
                    anomalies = self._detector.detect(sub, mt, samples)
                    all_anomalies.extend(anomalies)

        report.anomalies = all_anomalies

        suggestions = self._advisor.analyze(all_anomalies, report.subsystem_metrics)
        report.suggestions = suggestions

        if all_anomalies:
            critical = sum(1 for a in all_anomalies if a.severity == SeverityLevel.CRITICAL)
            warning = sum(1 for a in all_anomalies if a.severity == SeverityLevel.WARNING)
            report.overall_health = max(0.0, 1.0 - (critical * 0.2 + warning * 0.05))
        else:
            report.overall_health = 1.0

        report.summary = (
            f"Analyzed {len(subsystems)} subsystems. "
            f"Found {len(all_anomalies)} anomalies, "
            f"generated {len(suggestions)} suggestions. "
            f"Overall health: {report.overall_health:.0%}"
        )

        report.status = ReportStatus.READY
        self._reports.append(report)
        self._report_count += 1

        return report.to_dict()

    def apply_suggestion(self, suggestion_id: str, current_params: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
        for report in reversed(self._reports):
            for suggestion in report.suggestions:
                if suggestion.id == suggestion_id:
                    result = self._tuner.apply(suggestion, current_params or {})
                    return result
        return None

    def get_reports(self, limit: int = 10) -> List[Dict[str, Any]]:
        return [r.to_dict() for r in self._reports[-limit:]]

    def get_anomalies(self, severity: Optional[SeverityLevel] = None, limit: int = 20) -> List[Dict[str, Any]]:
        anomalies = self._detector._anomalies
        if severity:
            anomalies = [a for a in anomalies if a.severity == severity]
        return [a.to_dict() for a in anomalies[-limit:]]

    def get_suggestions(self, limit: int = 20) -> List[Dict[str, Any]]:
        return self._advisor.get_recent_suggestions(limit)

    def get_adjustments(self, limit: int = 20) -> List[Dict[str, Any]]:
        return self._tuner.get_adjustments(limit)

    def get_stats(self) -> Dict[str, Any]:
        return {
            "total_reports": self._report_count,
            "total_metrics_collected": self._collector.get_total_collected(),
            "monitored_subsystems": len(self._collector.get_all_subsystems()),
            "detector_stats": self._detector.get_stats(),
            "advisor_stats": self._advisor.get_stats(),
            "tuner_stats": self._tuner.get_stats(),
        }


_global_reflex_engine: Optional[ReflexEngine] = None


def get_reflex_engine() -> ReflexEngine:
    global _global_reflex_engine
    if _global_reflex_engine is None:
        _global_reflex_engine = ReflexEngine()
    return _global_reflex_engine
