"""
SparkLabs Agent - Insights Generator

Cross-session analytics engine that derives operational insights from
agent activity patterns across the SparkLabs game development platform.
Collects metrics, detects anomalies, analyzes trends, and produces
structured reports on agent behavior and productivity.

Architecture:
  InsightsGenerator
    |-- AgentInsight (single derived insight with confidence scoring)
    |-- InsightReport (multi-insight collection with formatting)
    |-- ActivityMetric (quantified activity measurement over time)
    |-- TrendLine (metric evolution across time windows)
    |-- AnomalyAlert (statistical deviation detection and alerting)

Insight Types:
  - PERFORMANCE: throughput, latency, resource efficiency
  - BEHAVIOR: interaction patterns, task preferences, response styles
  - USAGE: tool invocation frequency, model selection habits
  - TREND: directional shifts in activity over time
  - ANOMALY: statistical outliers and unexpected patterns
  - OPPORTUNITY: optimization suggestions and improvement areas

Usage:
    ig = get_insights_generator()
    ig.collect_metrics("agent_001", time_range_days=7)
    insights = ig.generate_insights("agent_001", types=[InsightType.PERFORMANCE])
    report = ig.create_report("agent_001", format=ReportFormat.MARKDOWN)
"""
from __future__ import annotations

import math
import statistics
import threading
import time
import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple


class InsightType(Enum):
    PERFORMANCE = "performance"
    BEHAVIOR = "behavior"
    USAGE = "usage"
    TREND = "trend"
    ANOMALY = "anomaly"
    OPPORTUNITY = "opportunity"


class TimeGranularity(Enum):
    HOURLY = "hourly"
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"


class ReportFormat(Enum):
    MARKDOWN = "markdown"
    JSON = "json"
    HTML = "html"


class AnomalySeverity(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class ActivityMetric:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    agent_id: str = ""
    metric_name: str = ""
    value: float = 0.0
    unit: str = ""
    timestamp: float = field(default_factory=time.time)
    session_id: str = ""
    labels: Dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "agent_id": self.agent_id,
            "metric_name": self.metric_name,
            "value": self.value,
            "unit": self.unit,
            "timestamp": self.timestamp,
            "session_id": self.session_id,
            "labels": self.labels,
        }


@dataclass
class TrendLine:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    agent_id: str = ""
    metric_name: str = ""
    granularity: TimeGranularity = TimeGranularity.DAILY
    data_points: List[Tuple[float, float]] = field(default_factory=list)
    slope: float = 0.0
    direction: str = "stable"
    r_squared: float = 0.0
    period_start: float = 0.0
    period_end: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "agent_id": self.agent_id,
            "metric_name": self.metric_name,
            "granularity": self.granularity.value,
            "data_points": [
                {"time": t, "value": v} for t, v in self.data_points
            ],
            "slope": round(self.slope, 4),
            "direction": self.direction,
            "r_squared": round(self.r_squared, 4),
            "period_start": self.period_start,
            "period_end": self.period_end,
        }


@dataclass
class AnomalyAlert:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    agent_id: str = ""
    metric_name: str = ""
    observed_value: float = 0.0
    expected_value: float = 0.0
    deviation: float = 0.0
    z_score: float = 0.0
    severity: AnomalySeverity = AnomalySeverity.LOW
    detected_at: float = field(default_factory=time.time)
    description: str = ""
    acknowledged: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "agent_id": self.agent_id,
            "metric_name": self.metric_name,
            "observed_value": self.observed_value,
            "expected_value": self.expected_value,
            "deviation": round(self.deviation, 4),
            "z_score": round(self.z_score, 4),
            "severity": self.severity.value,
            "detected_at": self.detected_at,
            "description": self.description,
            "acknowledged": self.acknowledged,
        }


@dataclass
class AgentInsight:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    agent_id: str = ""
    insight_type: InsightType = InsightType.PERFORMANCE
    title: str = ""
    summary: str = ""
    confidence: float = 0.0
    supporting_metrics: List[str] = field(default_factory=list)
    related_anomalies: List[str] = field(default_factory=list)
    recommendation: str = ""
    generated_at: float = field(default_factory=time.time)
    is_read: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "agent_id": self.agent_id,
            "insight_type": self.insight_type.value,
            "title": self.title,
            "summary": self.summary,
            "confidence": round(self.confidence, 3),
            "supporting_metrics": self.supporting_metrics,
            "related_anomalies": self.related_anomalies,
            "recommendation": self.recommendation,
            "generated_at": self.generated_at,
            "is_read": self.is_read,
        }


@dataclass
class InsightReport:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    agent_id: str = ""
    title: str = ""
    format: ReportFormat = ReportFormat.MARKDOWN
    insights: List[AgentInsight] = field(default_factory=list)
    trends: List[TrendLine] = field(default_factory=list)
    anomalies: List[AnomalyAlert] = field(default_factory=list)
    generated_at: float = field(default_factory=time.time)
    period_days: int = 7

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "agent_id": self.agent_id,
            "title": self.title,
            "format": self.format.value,
            "insights": [i.to_dict() for i in self.insights],
            "trends": [t.to_dict() for t in self.trends],
            "anomalies": [a.to_dict() for a in self.anomalies],
            "generated_at": self.generated_at,
            "period_days": self.period_days,
        }


GRANULARITY_SECONDS: Dict[TimeGranularity, float] = {
    TimeGranularity.HOURLY: 3600.0,
    TimeGranularity.DAILY: 86400.0,
    TimeGranularity.WEEKLY: 604800.0,
    TimeGranularity.MONTHLY: 2592000.0,
}


class InsightsGenerator:
    """
    Cross-session analytics engine for SparkLabs agents.

    Derives operational insights from agent activity data across
    multiple sessions. Performs trend analysis, anomaly detection,
    and structured report generation with multi-format output.

    Usage:
        ig = InsightsGenerator()
        ig.collect_metrics("agent_001", time_range_days=30)
        anomalies = ig.detect_anomalies("agent_001", lookback_days=14)
        report = ig.create_report("agent_001", format=ReportFormat.JSON)
    """

    _instance: Optional["InsightsGenerator"] = None
    _lock = threading.RLock()

    def __init__(self) -> None:
        self._metrics: Dict[str, List[ActivityMetric]] = defaultdict(list)
        self._insights: Dict[str, List[AgentInsight]] = defaultdict(list)
        self._alerts: Dict[str, List[AnomalyAlert]] = defaultdict(list)
        self._reports: Dict[str, InsightReport] = {}
        self._scheduled_reports: Dict[str, Dict[str, Any]] = {}
        self._metric_count: int = 0
        self._insight_count: int = 0
        self._alert_count: int = 0
        self._report_count: int = 0

    @classmethod
    def get_instance(cls) -> "InsightsGenerator":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def collect_metrics(
        self,
        agent_id: str,
        time_range_days: int = 7,
    ) -> List[ActivityMetric]:
        cutoff = time.time() - (time_range_days * 86400)
        all_metrics = self._metrics.get(agent_id, [])
        return [m for m in all_metrics if m.timestamp >= cutoff]

    def record_metric(
        self,
        agent_id: str,
        metric_name: str,
        value: float,
        unit: str = "",
        session_id: str = "",
        labels: Optional[Dict[str, str]] = None,
    ) -> ActivityMetric:
        metric = ActivityMetric(
            agent_id=agent_id,
            metric_name=metric_name,
            value=value,
            unit=unit,
            session_id=session_id,
            labels=labels or {},
        )
        self._metrics[agent_id].append(metric)
        self._metric_count += 1
        return metric

    def generate_insights(
        self,
        agent_id: str,
        types: Optional[List[InsightType]] = None,
        min_confidence: float = 0.3,
    ) -> List[AgentInsight]:
        if types is None:
            types = list(InsightType)

        metrics = self._metrics.get(agent_id, [])
        if not metrics:
            return []

        results: List[AgentInsight] = []
        metric_names = set(m.metric_name for m in metrics)
        metric_samples = {name: [m for m in metrics if m.metric_name == name] for name in metric_names}

        if InsightType.PERFORMANCE in types:
            for name, samples in metric_samples.items():
                if len(samples) < 3:
                    continue
                values = [s.value for s in samples]
                avg_val = statistics.mean(values)
                recent = [s.value for s in sorted(samples, key=lambda x: x.timestamp)[-5:]]
                recent_avg = statistics.mean(recent) if recent else avg_val

                if avg_val > 0 and abs(recent_avg - avg_val) / avg_val > 0.2:
                    direction = "improving" if recent_avg > avg_val else "declining"
                    conf = min(0.95, 0.5 + abs(recent_avg - avg_val) / avg_val)
                    if conf >= min_confidence:
                        insight = AgentInsight(
                            agent_id=agent_id,
                            insight_type=InsightType.PERFORMANCE,
                            title=f"Performance Shift: {name}",
                            summary=(
                                f"Metric '{name}' is {direction}: "
                                f"recent average {recent_avg:.2f} vs overall {avg_val:.2f}"
                            ),
                            confidence=conf,
                            supporting_metrics=[name],
                            recommendation=(
                                "Review recent sessions for changes in workflow."
                                if direction == "declining"
                                else "Consider solidifying recent process improvements."
                            ),
                        )
                        results.append(insight)

        if InsightType.USAGE in types:
            usage_by_session: Dict[str, int] = defaultdict(int)
            for m in metrics:
                if m.session_id:
                    usage_by_session[m.session_id] += 1

            if len(usage_by_session) >= 2:
                session_counts = list(usage_by_session.values())
                avg_session = statistics.mean(session_counts)
                stdev_session = statistics.stdev(session_counts) if len(session_counts) > 1 else 0

                insight = AgentInsight(
                    agent_id=agent_id,
                    insight_type=InsightType.USAGE,
                    title="Session Activity Profile",
                    summary=(
                        f"{len(usage_by_session)} sessions detected with "
                        f"avg {avg_session:.1f} metrics/session (stddev {stdev_session:.1f})"
                    ),
                    confidence=min(0.9, 0.4 + 0.1 * len(usage_by_session)),
                    recommendation="Review sessions with unusually high or low activity.",
                )
                results.append(insight)

        if InsightType.OPPORTUNITY in types:
            sparse_metrics = [
                name for name, samples in metric_samples.items()
                if len(samples) < 3
            ]
            if sparse_metrics and len(metric_samples) > 3:
                insight = AgentInsight(
                    agent_id=agent_id,
                    insight_type=InsightType.OPPORTUNITY,
                    title="Under-tracked Metrics",
                    summary=f"Sparse data in: {', '.join(sparse_metrics[:5])}",
                    confidence=0.6,
                    recommendation="Increase telemetry collection for these areas.",
                )
                results.append(insight)

        self._insights[agent_id].extend(results)
        self._insight_count += len(results)
        return results

    def detect_anomalies(
        self,
        agent_id: str,
        lookback_days: int = 14,
    ) -> List[AnomalyAlert]:
        cutoff = time.time() - (lookback_days * 86400)
        metrics = [m for m in self._metrics.get(agent_id, []) if m.timestamp >= cutoff]
        if len(metrics) < 5:
            return []

        alerts: List[AnomalyAlert] = []
        metric_names = set(m.metric_name for m in metrics)

        for name in metric_names:
            samples = sorted(
                [m for m in metrics if m.metric_name == name],
                key=lambda x: x.timestamp,
            )
            if len(samples) < 5:
                continue

            values = [s.value for s in samples]
            mean_val = statistics.mean(values)
            stdev = statistics.stdev(values) if len(values) > 1 else 1.0

            if stdev == 0:
                continue

            for sample in samples[-3:]:
                z = (sample.value - mean_val) / stdev
                if abs(z) < 1.5:
                    continue

                abs_z = abs(z)
                if abs_z >= 3.0:
                    severity = AnomalySeverity.CRITICAL
                    desc = f"Extreme outlier ({abs_z:.1f}σ) from mean {mean_val:.2f}"
                elif abs_z >= 2.5:
                    severity = AnomalySeverity.HIGH
                    desc = f"Significant outlier ({abs_z:.1f}σ) from mean {mean_val:.2f}"
                elif abs_z >= 2.0:
                    severity = AnomalySeverity.MEDIUM
                    desc = f"Notable outlier ({abs_z:.1f}σ) from mean {mean_val:.2f}"
                else:
                    severity = AnomalySeverity.LOW
                    desc = f"Mild deviation ({abs_z:.1f}σ) from mean {mean_val:.2f}"

                alert = AnomalyAlert(
                    agent_id=agent_id,
                    metric_name=name,
                    observed_value=sample.value,
                    expected_value=mean_val,
                    deviation=sample.value - mean_val,
                    z_score=z,
                    severity=severity,
                    description=desc,
                )
                alerts.append(alert)

        self._alerts[agent_id].extend(alerts)
        self._alert_count += len(alerts)
        return alerts

    def analyze_trends(
        self,
        agent_id: str,
        metric: str,
        granularity: TimeGranularity = TimeGranularity.DAILY,
    ) -> Optional[TrendLine]:
        all_samples = sorted(
            [m for m in self._metrics.get(agent_id, []) if m.metric_name == metric],
            key=lambda x: x.timestamp,
        )
        if len(all_samples) < 3:
            return None

        bucket_seconds = GRANULARITY_SECONDS.get(granularity, 86400.0)
        buckets: Dict[int, List[float]] = defaultdict(list)

        for sample in all_samples:
            bucket_key = int(sample.timestamp / bucket_seconds)
            buckets[bucket_key].append(sample.value)

        data_points: List[Tuple[float, float]] = []
        for bucket_key in sorted(buckets.keys()):
            bucket_values = buckets[bucket_key]
            avg = statistics.mean(bucket_values)
            ts = bucket_key * bucket_seconds + bucket_seconds / 2
            data_points.append((ts, avg))

        if len(data_points) < 2:
            return None

        n = len(data_points)
        times = [t for t, _ in data_points]
        vals = [v for _, v in data_points]

        mean_t = statistics.mean(times)
        mean_v = statistics.mean(vals)

        numerator = sum((t - mean_t) * (v - mean_v) for t, v in zip(times, vals))
        denominator = sum((t - mean_t) ** 2 for t in times)

        if denominator == 0:
            slope = 0.0
        else:
            slope = numerator / denominator

        if n > 2:
            ss_res = sum(
                (v - (mean_v + slope * (t - mean_t))) ** 2
                for t, v in zip(times, vals)
            )
            ss_tot = sum((v - mean_v) ** 2 for v in vals)
            r_squared = 1.0 - (ss_res / ss_tot) if ss_tot != 0 else 0.0
        else:
            r_squared = 1.0

        if slope > 0.01:
            direction = "rising" if slope > 0.05 else "slightly rising"
        elif slope < -0.01:
            direction = "falling" if slope < -0.05 else "slightly falling"
        else:
            direction = "stable"

        trend = TrendLine(
            agent_id=agent_id,
            metric_name=metric,
            granularity=granularity,
            data_points=data_points,
            slope=slope,
            direction=direction,
            r_squared=r_squared,
            period_start=times[0],
            period_end=times[-1],
        )
        return trend

    def create_report(
        self,
        agent_id: str,
        format: ReportFormat = ReportFormat.MARKDOWN,
        include_charts: bool = False,
    ) -> InsightReport:
        insights = self.generate_insights(agent_id)
        anomalies = self.detect_anomalies(agent_id)

        metric_names = set(
            m.metric_name for m in self._metrics.get(agent_id, [])
        )
        trends: List[TrendLine] = []
        for name in metric_names:
            trend = self.analyze_trends(agent_id, name)
            if trend is not None:
                trends.append(trend)

        report = InsightReport(
            agent_id=agent_id,
            title=f"Agent Insights Report — {agent_id}",
            format=format,
            insights=insights,
            trends=trends,
            anomalies=anomalies,
            period_days=7,
        )
        self._reports[report.id] = report
        self._report_count += 1
        return report

    def schedule_report(
        self,
        agent_id: str,
        frequency: str,
        format: ReportFormat = ReportFormat.MARKDOWN,
    ) -> Dict[str, Any]:
        schedule_entry = {
            "agent_id": agent_id,
            "frequency": frequency,
            "format": format.value,
            "created_at": time.time(),
            "next_run": time.time() + self._frequency_to_seconds(frequency),
        }
        schedule_id = uuid.uuid4().hex
        self._scheduled_reports[schedule_id] = schedule_entry
        return {"schedule_id": schedule_id, **schedule_entry}

    def compare_agents(
        self,
        agent_ids: List[str],
        metric: str,
    ) -> Dict[str, Any]:
        comparison: Dict[str, Dict[str, float]] = {}
        for aid in agent_ids:
            samples = [
                m.value for m in self._metrics.get(aid, [])
                if m.metric_name == metric
            ]
            if samples:
                comparison[aid] = {
                    "count": len(samples),
                    "mean": statistics.mean(samples),
                    "median": statistics.median(samples),
                    "min": min(samples),
                    "max": max(samples),
                }
                if len(samples) > 1:
                    comparison[aid]["stddev"] = statistics.stdev(samples)

        return {"metric": metric, "agents": comparison}

    def get_top_skills(self, agent_id: str, limit: int = 5) -> List[Dict[str, Any]]:
        metrics = self._metrics.get(agent_id, [])
        skill_metrics: Dict[str, float] = defaultdict(float)
        skill_counts: Dict[str, int] = defaultdict(int)

        for m in metrics:
            if m.labels.get("category") == "skill":
                skill_metrics[m.metric_name] += m.value
                skill_counts[m.metric_name] += 1

        ranked = sorted(
            [
                {
                    "skill": name,
                    "total_value": total,
                    "invocations": skill_counts[name],
                    "avg_per_invocation": total / max(skill_counts[name], 1),
                }
                for name, total in skill_metrics.items()
            ],
            key=lambda x: x["total_value"],
            reverse=True,
        )
        return ranked[:limit]

    def get_activity_summary(self, agent_id: str, days: int = 7) -> Dict[str, Any]:
        cutoff = time.time() - (days * 86400)
        recent = [
            m for m in self._metrics.get(agent_id, [])
            if m.timestamp >= cutoff
        ]
        if not recent:
            return {"agent_id": agent_id, "metrics": 0, "message": "No recent activity"}

        metric_names = set(m.metric_name for m in recent)
        sessions = set(m.session_id for m in recent if m.session_id)

        return {
            "agent_id": agent_id,
            "period_days": days,
            "total_metrics": len(recent),
            "unique_metrics": len(metric_names),
            "unique_sessions": len(sessions),
            "first_seen": min(m.timestamp for m in recent),
            "last_seen": max(m.timestamp for m in recent),
            "metric_names": sorted(metric_names),
        }

    def get_insight_history(self, agent_id: str) -> List[Dict[str, Any]]:
        return [i.to_dict() for i in self._insights.get(agent_id, [])]

    def get_alert_history(self, agent_id: str) -> List[Dict[str, Any]]:
        return [a.to_dict() for a in self._alerts.get(agent_id, [])]

    def acknowledge_alert(self, alert_id: str) -> bool:
        for alerts in self._alerts.values():
            for alert in alerts:
                if alert.id == alert_id:
                    alert.acknowledged = True
                    return True
        return False

    def mark_insight_read(self, insight_id: str) -> bool:
        for insights in self._insights.values():
            for insight in insights:
                if insight.id == insight_id:
                    insight.is_read = True
                    return True
        return False

    def get_report(self, report_id: str) -> Optional[Dict[str, Any]]:
        report = self._reports.get(report_id)
        if report is None:
            return None
        return report.to_dict()

    def format_report_text(self, report: InsightReport) -> str:
        if report.format == ReportFormat.JSON:
            import json
            return json.dumps(report.to_dict(), indent=2)

        if report.format == ReportFormat.HTML:
            parts = [f"<h1>{report.title}</h1>", f"<p>Generated: {report.generated_at}</p>"]
            if report.insights:
                parts.append("<h2>Insights</h2><ul>")
                for ins in report.insights:
                    parts.append(
                        f"<li><strong>{ins.title}</strong> "
                        f"[{ins.confidence:.0%}]: {ins.summary}</li>"
                    )
                parts.append("</ul>")
            return "\n".join(parts)

        lines = [
            f"# {report.title}",
            f"Generated: {time.strftime('%Y-%m-%d %H:%M', time.localtime(report.generated_at))}",
            f"Period: {report.period_days} days",
            "",
        ]

        if report.insights:
            lines.append("## Insights")
            for ins in report.insights:
                lines.append(f"- **{ins.title}** [{ins.confidence:.0%}]")
                lines.append(f"  {ins.summary}")
                if ins.recommendation:
                    lines.append(f"  → {ins.recommendation}")
            lines.append("")

        if report.trends:
            lines.append("## Trends")
            for trend in report.trends:
                lines.append(
                    f"- **{trend.metric_name}**: {trend.direction} "
                    f"(slope={trend.slope:.4f}, R²={trend.r_squared:.2f})"
                )
            lines.append("")

        if report.anomalies:
            lines.append("## Anomalies")
            for alert in report.anomalies:
                lines.append(
                    f"- [{alert.severity.value.upper()}] {alert.metric_name}: "
                    f"{alert.description}"
                )
            lines.append("")

        return "\n".join(lines)

    def get_stats(self) -> Dict[str, Any]:
        agents_with_data = len(self._metrics)
        return {
            "total_metrics": self._metric_count,
            "total_insights": self._insight_count,
            "total_alerts": self._alert_count,
            "total_reports": self._report_count,
            "agents_tracked": agents_with_data,
            "scheduled_reports": len(self._scheduled_reports),
            "active_alerts": sum(
                1 for alerts in self._alerts.values()
                for a in alerts if not a.acknowledged
            ),
            "unread_insights": sum(
                1 for insights in self._insights.values()
                for i in insights if not i.is_read
            ),
        }

    def clear(self) -> None:
        self._metrics.clear()
        self._insights.clear()
        self._alerts.clear()
        self._reports.clear()
        self._scheduled_reports.clear()
        self._metric_count = 0
        self._insight_count = 0
        self._alert_count = 0
        self._report_count = 0

    @staticmethod
    def _frequency_to_seconds(frequency: str) -> float:
        freq_map = {
            "hourly": 3600.0,
            "daily": 86400.0,
            "weekly": 604800.0,
            "monthly": 2592000.0,
        }
        return freq_map.get(frequency.lower(), 86400.0)


def get_insights_generator() -> InsightsGenerator:
    return InsightsGenerator.get_instance()