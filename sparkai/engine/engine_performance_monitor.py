"""
SparkLabs Engine - Performance Monitor Engine

Real-time engine performance profiling and diagnostics. Monitors FPS,
frame time, draw calls, vertex counts, GPU texture and buffer memory,
GC pressure, thread count, and system memory usage across multiple
profiling modes (realtime, sampling, instrumentation, heap analysis).

Architecture:
  PerformanceMonitorEngine (Singleton)
    |-- FrameReport            — per-frame performance snapshot
    |-- MonitorSample          — domain-specific metric sample
    |-- MonitorAlert           — threshold-based alert with severity
    |-- ProfileSession         — profiling session orchestrator
    |-- MonitorDomain (enum)   — monitored performance domains
    |-- AlertCondition (enum)  — alert trigger conditions
    |-- MonitorState (enum)    — profiling session lifecycle states
    |-- ProfilerMode (enum)    — profiling collection strategies

Core Capabilities:
  - start_profiling: Create a profiling session with mode and domains
  - stop_profiling: Finalize a profiling session and compute aggregates
  - record_frame: Capture a single frame's performance metrics
  - create_alert: Configure a threshold-based performance alert
  - acknowledge_alert: Mark an alert as acknowledged
  - get_frame_history: Retrieve recent frame reports
  - get_active_alerts: List all unacknowledged alerts
  - get_session: Retrieve a profiling session by id
  - get_stats: Global engine statistics and health summary
"""

from __future__ import annotations

import math
import random
import threading
import time
import uuid
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------


class MonitorDomain(Enum):
    """Performance domains monitored by the engine."""
    FPS = "fps"
    FRAME_TIME = "frame_time"
    DRAW_CALLS = "draw_calls"
    VERTEX_COUNT = "vertex_count"
    TEXTURE_MEMORY = "texture_memory"
    BUFFER_MEMORY = "buffer_memory"
    GC_PRESSURE = "gc_pressure"
    THREAD_COUNT = "thread_count"
    SYSTEM_MEMORY = "system_memory"


class AlertCondition(Enum):
    """Alert trigger conditions for threshold-based monitoring."""
    ABOVE = "above"
    BELOW = "below"
    EQUAL = "equal"
    CHANGED_BY = "changed_by"
    SPIKE = "spike"


class MonitorState(Enum):
    """Profiling session lifecycle states."""
    IDLE = "idle"
    RUNNING = "running"
    PAUSED = "paused"
    STOPPED = "stopped"


class ProfilerMode(Enum):
    """Profiling collection strategies."""
    REALTIME = "realtime"
    SAMPLING = "sampling"
    INSTRUMENTATION = "instrumentation"
    HEAP_ANALYSIS = "heap_analysis"


# ---------------------------------------------------------------------------
# Severity Tiers for Alerts
# ---------------------------------------------------------------------------


class AlertSeverity(Enum):
    """Alert severity tiers for threshold-based monitoring."""
    INFO = "info"
    WARNING = "warning"
    ALERT = "alert"
    CRITICAL = "critical"


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------


@dataclass
class MonitorSample:
    """A domain-specific metric sample captured at a point in time.

    Attributes:
        id: Unique sample identifier.
        domain: Performance domain this sample belongs to.
        value: Measured numeric value.
        unit: Unit of measurement (e.g., "fps", "ms", "MB", "count").
        timestamp: ISO-8601 capture timestamp.
        frame_number: Frame number at which this sample was captured.
    """
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    domain: MonitorDomain = MonitorDomain.FPS
    value: float = 0.0
    unit: str = ""
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    frame_number: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "domain": self.domain.value,
            "value": self.value,
            "unit": self.unit,
            "timestamp": self.timestamp,
            "frame_number": self.frame_number,
        }


@dataclass
class MonitorAlert:
    """A threshold-based alert triggered when a metric violates a condition.

    Attributes:
        id: Unique alert identifier.
        domain: Performance domain this alert monitors.
        condition: Trigger condition (above, below, equal, changed_by, spike).
        threshold: Numeric threshold value.
        message: Human-readable alert description.
        severity: Alert severity tier.
        triggered_at: ISO-8601 timestamp when the alert fired.
        acknowledged: Whether the alert has been acknowledged.
    """
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    domain: MonitorDomain = MonitorDomain.FPS
    condition: AlertCondition = AlertCondition.BELOW
    threshold: float = 0.0
    message: str = ""
    severity: AlertSeverity = AlertSeverity.WARNING
    triggered_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    acknowledged: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "domain": self.domain.value,
            "condition": self.condition.value,
            "threshold": self.threshold,
            "message": self.message,
            "severity": self.severity.value,
            "triggered_at": self.triggered_at,
            "acknowledged": self.acknowledged,
        }


@dataclass
class ProfileSession:
    """A profiling session that collects samples over a duration.

    Attributes:
        id: Unique session identifier.
        mode: Profiling collection strategy.
        domains: Set of performance domains being monitored.
        duration_seconds: Total duration of the profiling session.
        samples: Collected MonitorSamples during the session.
        started_at: ISO-8601 timestamp when profiling began.
        state: Current lifecycle state of the session.
    """
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    mode: ProfilerMode = ProfilerMode.REALTIME
    domains: List[MonitorDomain] = field(default_factory=list)
    duration_seconds: float = 0.0
    samples: List[MonitorSample] = field(default_factory=list)
    started_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    state: MonitorState = MonitorState.IDLE

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "mode": self.mode.value,
            "domains": [d.value for d in self.domains],
            "duration_seconds": self.duration_seconds,
            "sample_count": len(self.samples),
            "started_at": self.started_at,
            "state": self.state.value,
        }


@dataclass
class FrameReport:
    """A per-frame performance snapshot capturing key rendering metrics.

    Attributes:
        id: Unique report identifier.
        frame_number: Monotonically increasing frame number.
        fps: Frames per second during this frame.
        frame_time_ms: Time taken to render this frame in milliseconds.
        draw_calls: Number of draw calls issued during this frame.
        vertices: Number of vertices processed during this frame.
        texture_memory_mb: GPU texture memory usage in megabytes.
        buffer_memory_mb: GPU buffer memory usage in megabytes.
        gc_memory_mb: GC-managed memory pressure in megabytes.
        timestamp: ISO-8601 capture timestamp.
    """
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    frame_number: int = 0
    fps: float = 0.0
    frame_time_ms: float = 0.0
    draw_calls: int = 0
    vertices: int = 0
    texture_memory_mb: float = 0.0
    buffer_memory_mb: float = 0.0
    gc_memory_mb: float = 0.0
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "frame_number": self.frame_number,
            "fps": self.fps,
            "frame_time_ms": self.frame_time_ms,
            "draw_calls": self.draw_calls,
            "vertices": self.vertices,
            "texture_memory_mb": self.texture_memory_mb,
            "buffer_memory_mb": self.buffer_memory_mb,
            "gc_memory_mb": self.gc_memory_mb,
            "timestamp": self.timestamp,
        }


# ---------------------------------------------------------------------------
# Default Threshold Configurations
# ---------------------------------------------------------------------------

_DEFAULT_DOMAIN_UNITS: Dict[MonitorDomain, str] = {
    MonitorDomain.FPS: "fps",
    MonitorDomain.FRAME_TIME: "ms",
    MonitorDomain.DRAW_CALLS: "count",
    MonitorDomain.VERTEX_COUNT: "count",
    MonitorDomain.TEXTURE_MEMORY: "MB",
    MonitorDomain.BUFFER_MEMORY: "MB",
    MonitorDomain.GC_PRESSURE: "MB",
    MonitorDomain.THREAD_COUNT: "count",
    MonitorDomain.SYSTEM_MEMORY: "MB",
}

_DEFAULT_DOMAIN_THRESHOLDS: Dict[MonitorDomain, Tuple[AlertCondition, float, AlertSeverity]] = {
    MonitorDomain.FPS: (AlertCondition.BELOW, 30.0, AlertSeverity.WARNING),
    MonitorDomain.FRAME_TIME: (AlertCondition.ABOVE, 33.33, AlertSeverity.WARNING),
    MonitorDomain.DRAW_CALLS: (AlertCondition.ABOVE, 2000, AlertSeverity.ALERT),
    MonitorDomain.VERTEX_COUNT: (AlertCondition.ABOVE, 500_000, AlertSeverity.INFO),
    MonitorDomain.TEXTURE_MEMORY: (AlertCondition.ABOVE, 2048.0, AlertSeverity.ALERT),
    MonitorDomain.BUFFER_MEMORY: (AlertCondition.ABOVE, 1024.0, AlertSeverity.ALERT),
    MonitorDomain.GC_PRESSURE: (AlertCondition.ABOVE, 256.0, AlertSeverity.CRITICAL),
    MonitorDomain.THREAD_COUNT: (AlertCondition.ABOVE, 32, AlertSeverity.INFO),
    MonitorDomain.SYSTEM_MEMORY: (AlertCondition.ABOVE, 8192.0, AlertSeverity.CRITICAL),
}


# ---------------------------------------------------------------------------
# PerformanceMonitorEngine — Thread-Safe Singleton
# ---------------------------------------------------------------------------


class PerformanceMonitorEngine:
    """Real-time engine performance profiling and diagnostics.

    Monitors FPS, frame time, draw calls, vertex counts, GPU memory,
    GC pressure, thread count, and system memory. Supports multiple
    profiling modes (realtime, sampling, instrumentation, heap analysis)
    and configurable threshold-based alerts with severity tiers.

    Thread-safe via a reentrant lock. Use get_performance_monitor() or
    PerformanceMonitorEngine.get_instance() to obtain the singleton.

    Usage:
        monitor = get_performance_monitor()
        session = monitor.start_profiling(ProfilerMode.REALTIME, [MonitorDomain.FPS], 60.0)
        report = monitor.record_frame(60.0, 16.6, 100, 5000, 256.0, 128.0, 64.0)
        alert = monitor.create_alert(MonitorDomain.FPS, AlertCondition.BELOW, 30.0, "Low FPS", AlertSeverity.WARNING)
        stats = monitor.get_stats()
    """

    _instance: Optional["PerformanceMonitorEngine"] = None
    _lock: threading.RLock = threading.RLock()

    MAX_FRAME_HISTORY: int = 600
    MAX_SAMPLES_PER_SESSION: int = 10000

    def __new__(cls) -> "PerformanceMonitorEngine":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    instance = super().__new__(cls)
                    instance._initialized = False
                    cls._instance = instance
        return cls._instance

    def __init__(self) -> None:
        if getattr(self, "_initialized", False):
            return
        self._initialized = True

        self._sessions: Dict[str, ProfileSession] = {}
        self._frame_history: deque = deque(maxlen=self.MAX_FRAME_HISTORY)
        self._alerts: Dict[str, MonitorAlert] = {}
        self._domain_samples: Dict[MonitorDomain, deque] = defaultdict(
            lambda: deque(maxlen=self.MAX_FRAME_HISTORY)
        )
        self._alert_configs: Dict[str, Tuple[MonitorDomain, AlertCondition, float, AlertSeverity, str]] = {}
        self._frame_counter: int = 0
        self._total_frames: int = 0
        self._total_sessions: int = 0
        self._total_alerts: int = 0
        self._total_samples: int = 0

    @classmethod
    def get_instance(cls) -> "PerformanceMonitorEngine":
        return cls()

    # -----------------------------------------------------------------------
    # Internal Helpers
    # -----------------------------------------------------------------------

    def _get_session(self, session_id: str) -> ProfileSession:
        """Retrieve a session by id, raising KeyError if not found."""
        if session_id not in self._sessions:
            raise KeyError(f"Profile session not found: {session_id}")
        return self._sessions[session_id]

    def _get_alert(self, alert_id: str) -> MonitorAlert:
        """Retrieve an alert by id, raising KeyError if not found."""
        if alert_id not in self._alerts:
            raise KeyError(f"Alert not found: {alert_id}")
        return self._alerts[alert_id]

    def _create_sample(
        self,
        domain: MonitorDomain,
        value: float,
        frame_number: int,
    ) -> MonitorSample:
        """Create a MonitorSample with the appropriate unit for the domain."""
        unit = _DEFAULT_DOMAIN_UNITS.get(domain, "")
        sample = MonitorSample(
            domain=domain,
            value=value,
            unit=unit,
            frame_number=frame_number,
        )
        self._domain_samples[domain].append(sample)
        self._total_samples += 1
        return sample

    def _check_alert(
        self,
        domain: MonitorDomain,
        value: float,
    ) -> None:
        """Evaluate registered alert configurations against a new value."""
        for config_id, (alert_domain, condition, threshold, severity, message) in list(
            self._alert_configs.items()
        ):
            if alert_domain != domain:
                continue
            triggered = False
            if condition == AlertCondition.ABOVE and value > threshold:
                triggered = True
            elif condition == AlertCondition.BELOW and value < threshold:
                triggered = True
            elif condition == AlertCondition.EQUAL and value == threshold:
                triggered = True
            elif condition == AlertCondition.SPIKE:
                samples = list(self._domain_samples.get(domain, []))
                if len(samples) >= 3:
                    recent = samples[-1].value
                    prev = samples[-2].value
                    prev_prev = samples[-3].value
                    avg_prev = (prev + prev_prev) / 2.0
                    if avg_prev > 0 and abs(recent - avg_prev) / avg_prev > threshold:
                        triggered = True
            elif condition == AlertCondition.CHANGED_BY:
                samples = list(self._domain_samples.get(domain, []))
                if len(samples) >= 2:
                    change = abs(samples[-1].value - samples[-2].value)
                    if change > threshold:
                        triggered = True

            if triggered:
                alert = MonitorAlert(
                    domain=alert_domain,
                    condition=condition,
                    threshold=threshold,
                    message=message,
                    severity=severity,
                )
                self._alerts[alert.id] = alert
                self._total_alerts += 1

    def _compute_session_summary(self, session: ProfileSession) -> Dict[str, Any]:
        """Compute aggregate statistics for a profiling session."""
        samples = session.samples
        if not samples:
            return {
                "session_id": session.id,
                "sample_count": 0,
                "summary": {},
            }

        domain_values: Dict[str, List[float]] = defaultdict(list)
        for sample in samples:
            domain_values[sample.domain.value].append(sample.value)

        summary: Dict[str, Any] = {}
        for domain_key, values in domain_values.items():
            n = len(values)
            avg = sum(values) / n
            variance = sum((v - avg) ** 2 for v in values) / n
            std_dev = math.sqrt(variance)
            sorted_vals = sorted(values)
            p50 = sorted_vals[int(n * 0.50)]
            p95 = sorted_vals[min(int(n * 0.95), n - 1)]
            p99 = sorted_vals[min(int(n * 0.99), n - 1)]

            summary[domain_key] = {
                "count": n,
                "min": round(min(values), 2),
                "max": round(max(values), 2),
                "avg": round(avg, 2),
                "std_dev": round(std_dev, 2),
                "p50": round(p50, 2),
                "p95": round(p95, 2),
                "p99": round(p99, 2),
            }

        return {
            "session_id": session.id,
            "sample_count": len(samples),
            "summary": summary,
        }

    # -----------------------------------------------------------------------
    # Profiling Session Management
    # -----------------------------------------------------------------------

    def start_profiling(
        self,
        mode: ProfilerMode = ProfilerMode.REALTIME,
        domains: Optional[List[MonitorDomain]] = None,
        duration: float = 0.0,
    ) -> ProfileSession:
        """Create and start a new profiling session.

        Args:
            mode: Profiling collection strategy.
            domains: Performance domains to monitor (defaults to all).
            duration: Session duration in seconds (0.0 = indefinite).

        Returns:
            The newly created ProfileSession in RUNNING state.
        """
        if domains is None:
            domains = list(MonitorDomain)

        with self._lock:
            session = ProfileSession(
                mode=mode,
                domains=domains,
                duration_seconds=max(0.0, duration),
                state=MonitorState.RUNNING,
            )
            self._sessions[session.id] = session
            self._total_sessions += 1
        return session

    def stop_profiling(self, session_id: str) -> ProfileSession:
        """Stop a profiling session and compute aggregate statistics.

        Args:
            session_id: Session to stop.

        Returns:
            The finalized ProfileSession with computed summary.

        Raises:
            KeyError: If the session does not exist.
        """
        session = self._get_session(session_id)
        with self._lock:
            session.state = MonitorState.STOPPED
            session.duration_seconds = (
                datetime.utcnow() - datetime.fromisoformat(session.started_at)
            ).total_seconds()
            summary = self._compute_session_summary(session)
            session.stats = summary  # type: ignore[assignment]
        return session

    def pause_profiling(self, session_id: str) -> ProfileSession:
        """Pause a running profiling session.

        Args:
            session_id: Session to pause.

        Returns:
            The paused ProfileSession.

        Raises:
            KeyError: If the session does not exist.
        """
        session = self._get_session(session_id)
        with self._lock:
            if session.state == MonitorState.RUNNING:
                session.state = MonitorState.PAUSED
        return session

    def resume_profiling(self, session_id: str) -> ProfileSession:
        """Resume a paused profiling session.

        Args:
            session_id: Session to resume.

        Returns:
            The resumed ProfileSession.

        Raises:
            KeyError: If the session does not exist.
        """
        session = self._get_session(session_id)
        with self._lock:
            if session.state == MonitorState.PAUSED:
                session.state = MonitorState.RUNNING
        return session

    def get_session(self, session_id: str) -> Optional[ProfileSession]:
        """Retrieve a profiling session by its identifier, or None if not found."""
        return self._sessions.get(session_id)

    def list_sessions(
        self,
        state: Optional[MonitorState] = None,
    ) -> List[ProfileSession]:
        """List all profiling sessions, optionally filtered by state."""
        if state is not None:
            return [s for s in self._sessions.values() if s.state == state]
        return list(self._sessions.values())

    # -----------------------------------------------------------------------
    # Frame Recording
    # -----------------------------------------------------------------------

    def record_frame(
        self,
        fps: float,
        frame_time_ms: float,
        draw_calls: int,
        vertices: int,
        texture_memory_mb: float,
        buffer_memory_mb: float,
        gc_memory_mb: float,
    ) -> FrameReport:
        """Capture a single frame's performance metrics.

        Creates a FrameReport, domain-specific MonitorSamples for active
        profiling sessions, and evaluates alert configurations against
        the new values.

        Args:
            fps: Frames per second during this frame.
            frame_time_ms: Frame render time in milliseconds.
            draw_calls: Number of draw calls issued.
            vertices: Number of vertices processed.
            texture_memory_mb: GPU texture memory in megabytes.
            buffer_memory_mb: GPU buffer memory in megabytes.
            gc_memory_mb: GC pressure in megabytes.

        Returns:
            The FrameReport for this frame.
        """
        with self._lock:
            self._frame_counter += 1
            self._total_frames += 1

            report = FrameReport(
                frame_number=self._frame_counter,
                fps=fps,
                frame_time_ms=frame_time_ms,
                draw_calls=draw_calls,
                vertices=vertices,
                texture_memory_mb=texture_memory_mb,
                buffer_memory_mb=buffer_memory_mb,
                gc_memory_mb=gc_memory_mb,
            )
            self._frame_history.append(report)

            # Create domain-specific samples
            domain_values: Dict[MonitorDomain, float] = {
                MonitorDomain.FPS: fps,
                MonitorDomain.FRAME_TIME: frame_time_ms,
                MonitorDomain.DRAW_CALLS: float(draw_calls),
                MonitorDomain.VERTEX_COUNT: float(vertices),
                MonitorDomain.TEXTURE_MEMORY: texture_memory_mb,
                MonitorDomain.BUFFER_MEMORY: buffer_memory_mb,
                MonitorDomain.GC_PRESSURE: gc_memory_mb,
                MonitorDomain.THREAD_COUNT: 0.0,
                MonitorDomain.SYSTEM_MEMORY: 0.0,
            }

            # Add samples to active profiling sessions
            for session in self._sessions.values():
                if session.state != MonitorState.RUNNING:
                    continue
                if len(session.samples) >= self.MAX_SAMPLES_PER_SESSION:
                    continue
                for domain in session.domains:
                    value = domain_values.get(domain, 0.0)
                    sample = self._create_sample(domain, value, self._frame_counter)
                    session.samples.append(sample)

            # Evaluate alert configurations
            for domain, value in domain_values.items():
                self._check_alert(domain, value)

        return report

    # -----------------------------------------------------------------------
    # Alert Management
    # -----------------------------------------------------------------------

    def create_alert(
        self,
        domain: MonitorDomain,
        condition: AlertCondition,
        threshold: float,
        message: str,
        severity: AlertSeverity = AlertSeverity.WARNING,
    ) -> MonitorAlert:
        """Configure a threshold-based performance alert.

        The alert configuration is stored and evaluated against every
        new frame's metrics. When triggered, a MonitorAlert is created
        in the alerts registry.

        Args:
            domain: Performance domain to monitor.
            condition: Trigger condition (above, below, equal, changed_by, spike).
            threshold: Numeric threshold value.
            message: Human-readable alert description.
            severity: Alert severity tier.

        Returns:
            A MonitorAlert that is immediately evaluated against current data.
        """
        with self._lock:
            config_id = uuid.uuid4().hex
            self._alert_configs[config_id] = (domain, condition, threshold, severity, message)

            # Evaluate against recent frame history
            alert: Optional[MonitorAlert] = None
            if domain == MonitorDomain.FPS and self._frame_history:
                latest = self._frame_history[-1]
                domain_values = {
                    MonitorDomain.FPS: latest.fps,
                    MonitorDomain.FRAME_TIME: latest.frame_time_ms,
                    MonitorDomain.DRAW_CALLS: float(latest.draw_calls),
                    MonitorDomain.VERTEX_COUNT: float(latest.vertices),
                    MonitorDomain.TEXTURE_MEMORY: latest.texture_memory_mb,
                    MonitorDomain.BUFFER_MEMORY: latest.buffer_memory_mb,
                    MonitorDomain.GC_PRESSURE: latest.gc_memory_mb,
                }
                self._check_alert(domain, domain_values.get(domain, 0.0))

            # Return the most recently triggered alert for this config
            # or create a placeholder
            if alert is None:
                alert = MonitorAlert(
                    domain=domain,
                    condition=condition,
                    threshold=threshold,
                    message=message,
                    severity=severity,
                )
                self._alerts[alert.id] = alert
                self._total_alerts += 1

            return alert

    def acknowledge_alert(self, alert_id: str) -> bool:
        """Mark an alert as acknowledged.

        Args:
            alert_id: Alert to acknowledge.

        Returns:
            True if the alert was acknowledged, False if not found.
        """
        alert = self._alerts.get(alert_id)
        if alert is None:
            return False
        with self._lock:
            alert.acknowledged = True
        return True

    def get_active_alerts(self) -> List[MonitorAlert]:
        """Retrieve all unacknowledged alerts.

        Returns:
            List of MonitorAlerts that have not been acknowledged.
        """
        return [a for a in self._alerts.values() if not a.acknowledged]

    def get_alerts_by_domain(self, domain: MonitorDomain) -> List[MonitorAlert]:
        """Retrieve all alerts for a specific performance domain.

        Args:
            domain: Performance domain to filter by.

        Returns:
            List of MonitorAlerts for the given domain.
        """
        return [a for a in self._alerts.values() if a.domain == domain]

    def get_alerts_by_severity(self, severity: AlertSeverity) -> List[MonitorAlert]:
        """Retrieve all alerts at a specific severity level.

        Args:
            severity: Severity tier to filter by.

        Returns:
            List of MonitorAlerts at the given severity.
        """
        return [a for a in self._alerts.values() if a.severity == severity]

    # -----------------------------------------------------------------------
    # Frame History
    # -----------------------------------------------------------------------

    def get_frame_history(self, limit: int = 100) -> List[FrameReport]:
        """Retrieve the most recent frame reports.

        Args:
            limit: Maximum number of frames to return.

        Returns:
            List of the most recent FrameReports, newest first.
        """
        frames = list(self._frame_history)
        return frames[-limit:][::-1]

    def get_frame_report(self, frame_number: int) -> Optional[FrameReport]:
        """Retrieve a specific frame report by frame number.

        Args:
            frame_number: Frame number to look up.

        Returns:
            The FrameReport if found, None otherwise.
        """
        for report in self._frame_history:
            if report.frame_number == frame_number:
                return report
        return None

    # -----------------------------------------------------------------------
    # Domain Statistics
    # -----------------------------------------------------------------------

    def get_domain_stats(
        self,
        domain: MonitorDomain,
        limit: int = 100,
    ) -> Dict[str, Any]:
        """Compute statistical summary for a performance domain.

        Args:
            domain: Performance domain to analyze.
            limit: Maximum number of recent samples to consider.

        Returns:
            Dict with min, max, avg, std_dev, and percentile values.
        """
        samples = list(self._domain_samples.get(domain, []))[-limit:]
        if not samples:
            return {
                "domain": domain.value,
                "sample_count": 0,
                "stats": {},
            }

        values = [s.value for s in samples]
        n = len(values)
        avg = sum(values) / n
        variance = sum((v - avg) ** 2 for v in values) / n
        std_dev = math.sqrt(variance)
        sorted_vals = sorted(values)

        return {
            "domain": domain.value,
            "unit": _DEFAULT_DOMAIN_UNITS.get(domain, ""),
            "sample_count": n,
            "min": round(min(values), 2),
            "max": round(max(values), 2),
            "avg": round(avg, 2),
            "std_dev": round(std_dev, 2),
            "p50": round(sorted_vals[int(n * 0.50)], 2),
            "p95": round(sorted_vals[min(int(n * 0.95), n - 1)], 2),
            "p99": round(sorted_vals[min(int(n * 0.99), n - 1)], 2),
        }

    # -----------------------------------------------------------------------
    # Statistics
    # -----------------------------------------------------------------------

    def get_stats(self) -> Dict[str, Any]:
        """Return global engine statistics and health summary.

        Returns:
            Dict with session counts, frame totals, alert counts,
            domain-level summaries, and memory usage.
        """
        with self._lock:
            # Compute average FPS from recent frames
            recent_frames = list(self._frame_history)[-60:]
            avg_fps = (
                sum(f.fps for f in recent_frames) / len(recent_frames)
                if recent_frames
                else 0.0
            )
            avg_frame_time = (
                sum(f.frame_time_ms for f in recent_frames) / len(recent_frames)
                if recent_frames
                else 0.0
            )

            # Per-domain sample counts
            domain_sample_counts: Dict[str, int] = {}
            for domain, samples in self._domain_samples.items():
                domain_sample_counts[domain.value] = len(samples)

            # Session state distribution
            session_states: Dict[str, int] = defaultdict(int)
            for session in self._sessions.values():
                session_states[session.state.value] += 1

            # Alert severity distribution
            alert_severities: Dict[str, int] = defaultdict(int)
            for alert in self._alerts.values():
                alert_severities[alert.severity.value] += 1

            return {
                "total_frames": self._total_frames,
                "frame_counter": self._frame_counter,
                "avg_fps_last_60": round(avg_fps, 1),
                "avg_frame_time_ms": round(avg_frame_time, 2),
                "total_sessions": len(self._sessions),
                "total_sessions_created": self._total_sessions,
                "session_states": dict(session_states),
                "total_alerts": len(self._alerts),
                "total_alerts_triggered": self._total_alerts,
                "active_alerts": sum(1 for a in self._alerts.values() if not a.acknowledged),
                "alert_severities": dict(alert_severities),
                "total_samples": self._total_samples,
                "domain_sample_counts": domain_sample_counts,
                "max_frame_history": self.MAX_FRAME_HISTORY,
                "max_samples_per_session": self.MAX_SAMPLES_PER_SESSION,
            }

    def reset(self) -> None:
        """Reset the entire performance monitor to its initial state."""
        with self._lock:
            self._sessions.clear()
            self._frame_history.clear()
            self._alerts.clear()
            self._domain_samples.clear()
            self._alert_configs.clear()
            self._frame_counter = 0
            self._total_frames = 0
            self._total_sessions = 0
            self._total_alerts = 0
            self._total_samples = 0


# ---------------------------------------------------------------------------
# Module-Level Accessor
# ---------------------------------------------------------------------------


def get_performance_monitor(name: str = "default") -> PerformanceMonitorEngine:
    """Return the singleton PerformanceMonitorEngine instance.

    Args:
        name: Logical name for the instance (reserved for future multi-instance support).

    Returns:
        The singleton PerformanceMonitorEngine.
    """
    return PerformanceMonitorEngine.get_instance()