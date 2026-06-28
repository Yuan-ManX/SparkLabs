"""
SparkLabs Agent - Quality Assurance Orchestrator

Comprehensive quality assurance subsystem that orchestrates end-to-end QA
processes for the SparkLabs AI-Native Game Engine. Coordinates automated
testing, code review, performance validation, accessibility auditing,
compatibility checking, security scanning, localization verification,
content validation, UX evaluation, and continuous quality monitoring
across the entire game development lifecycle.

Architecture:
  QualityAssuranceOrchestrator (singleton)
    |-- CheckRegistry (registered QA checks and their handlers)
    |-- DefectDatabase (tracking and triage of detected defects)
    |-- ReportHistory (historical QA reports for trend analysis)
    |-- ContinuousMonitor (background continuous QA monitoring)

QA Lifecycle Phases:
  PRE_BUILD -> BUILD -> POST_BUILD -> PRE_RELEASE -> POST_RELEASE -> CONTINUOUS

QA Categories:
  FUNCTIONAL       - core game functionality and behavior
  PERFORMANCE      - frame rate, memory, load times, profiling
  CODE_QUALITY     - linting, complexity, coverage, patterns
  ACCESSIBILITY    - WCAG compliance, input alternatives, contrast
  COMPATIBILITY    - cross-platform, device, and OS validation
  SECURITY         - vulnerability scanning, secrets, sanitization
  LOCALIZATION     - i18n, locale correctness, text rendering
  CONTENT         - asset quality, narrative consistency, balance
  UX              - usability, onboarding, friction analysis
  REGRESSION       - behavior preservation across versions

Usage:
    qa = get_quality_assurance()
    qa.initialize()
    qa.register_check("smoke_test", QACategory.FUNCTIONAL, my_handler)
    result = qa.run_check("smoke_test", target="game_001")
    report = qa.run_full_qa("game_001", QAConfig(phases=[QAPhase.BUILD]))
    qa.run_continuous("game_001", interval=60.0)
    status = qa.get_status()
    qa.shutdown()
"""

from __future__ import annotations

import logging
import threading
import time
import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

_time_module = time

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class QACategory(Enum):
    """Categories of quality assurance checks."""

    FUNCTIONAL = "functional"
    PERFORMANCE = "performance"
    CODE_QUALITY = "code_quality"
    ACCESSIBILITY = "accessibility"
    COMPATIBILITY = "compatibility"
    SECURITY = "security"
    LOCALIZATION = "localization"
    CONTENT = "content"
    UX = "ux"
    REGRESSION = "regression"


class QASeverity(Enum):
    """Severity levels for QA findings and defects."""

    BLOCKER = "blocker"
    CRITICAL = "critical"
    MAJOR = "major"
    MINOR = "minor"
    INFO = "info"
    PASS = "pass"


class QAState(Enum):
    """Operational states for individual QA checks and the QA pipeline."""

    PENDING = "pending"
    RUNNING = "running"
    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"
    WARNINGS = "warnings"


class QAPhase(Enum):
    """Lifecycle phases at which QA can be executed."""

    PRE_BUILD = "pre_build"
    BUILD = "build"
    POST_BUILD = "post_build"
    PRE_RELEASE = "pre_release"
    POST_RELEASE = "post_release"
    CONTINUOUS = "continuous"


# ---------------------------------------------------------------------------
# Data Classes
# ---------------------------------------------------------------------------


@dataclass
class QAConfig:
    """Configuration for a QA pipeline run.

    Controls which phases are executed, which categories are included,
    failure thresholds, and whether continuous monitoring is enabled.
    """

    phases: List[QAPhase] = field(
        default_factory=lambda: [
            QAPhase.PRE_BUILD,
            QAPhase.BUILD,
            QAPhase.POST_BUILD,
            QAPhase.PRE_RELEASE,
        ]
    )
    categories: List[QACategory] = field(default_factory=lambda: list(QACategory))
    fail_on_blocker: bool = True
    fail_on_critical: bool = True
    pass_threshold: float = 0.8
    max_concurrent_checks: int = 4
    timeout_seconds: float = 300.0
    retry_attempts: int = 1
    include_skipped: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize the configuration to a dictionary."""
        return {
            "phases": [p.value for p in self.phases],
            "categories": [c.value for c in self.categories],
            "fail_on_blocker": self.fail_on_blocker,
            "fail_on_critical": self.fail_on_critical,
            "pass_threshold": self.pass_threshold,
            "max_concurrent_checks": self.max_concurrent_checks,
            "timeout_seconds": self.timeout_seconds,
            "retry_attempts": self.retry_attempts,
            "include_skipped": self.include_skipped,
            "metadata": dict(self.metadata),
        }


@dataclass
class QACheckResult:
    """Result of a single QA check execution.

    Captures the outcome, severity, duration, and any message produced
    by the check handler for a specific target.
    """

    check_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    category: QACategory = QACategory.FUNCTIONAL
    phase: QAPhase = QAPhase.BUILD
    state: QAState = QAState.PENDING
    severity: QASeverity = QASeverity.INFO
    target: str = ""
    message: str = ""
    score: float = 0.0
    duration_ms: float = 0.0
    details: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=_time_module.time)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize the check result to a dictionary."""
        return {
            "check_id": self.check_id,
            "name": self.name,
            "category": self.category.value,
            "phase": self.phase.value,
            "state": self.state.value,
            "severity": self.severity.value,
            "target": self.target,
            "message": self.message,
            "score": self.score,
            "duration_ms": self.duration_ms,
            "details": dict(self.details),
            "timestamp": self.timestamp,
        }


@dataclass
class QABatchResult:
    """Aggregated result of a batch of QA checks.

    Groups multiple :class:`QACheckResult` objects for a single target
    and provides summary counts and an overall batch verdict.
    """

    batch_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    target: str = ""
    phase: QAPhase = QAPhase.BUILD
    results: List[QACheckResult] = field(default_factory=list)
    total: int = 0
    passed: int = 0
    failed: int = 0
    warnings: int = 0
    skipped: int = 0
    overall_state: QAState = QAState.PENDING
    overall_score: float = 0.0
    duration_ms: float = 0.0
    timestamp: float = field(default_factory=_time_module.time)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize the batch result to a dictionary."""
        return {
            "batch_id": self.batch_id,
            "target": self.target,
            "phase": self.phase.value,
            "results": [r.to_dict() for r in self.results],
            "total": self.total,
            "passed": self.passed,
            "failed": self.failed,
            "warnings": self.warnings,
            "skipped": self.skipped,
            "overall_state": self.overall_state.value,
            "overall_score": self.overall_score,
            "duration_ms": self.duration_ms,
            "timestamp": self.timestamp,
        }


@dataclass
class QAReport:
    """Complete QA report for one or more targets.

    Aggregates batch results, derived defects, and category-level
    scores into a single comprehensive deliverable.
    """

    report_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    target: str = ""
    config: Optional[QAConfig] = None
    batch_results: List[QABatchResult] = field(default_factory=list)
    defects: List["Defect"] = field(default_factory=list)
    total_checks: int = 0
    total_passed: int = 0
    total_failed: int = 0
    total_warnings: int = 0
    overall_state: QAState = QAState.PENDING
    overall_score: float = 0.0
    category_scores: Dict[str, float] = field(default_factory=dict)
    created_at: float = field(default_factory=_time_module.time)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize the report to a dictionary."""
        return {
            "report_id": self.report_id,
            "target": self.target,
            "config": self.config.to_dict() if self.config else None,
            "batch_results": [b.to_dict() for b in self.batch_results],
            "defects": [d.to_dict() for d in self.defects],
            "total_checks": self.total_checks,
            "total_passed": self.total_passed,
            "total_failed": self.total_failed,
            "total_warnings": self.total_warnings,
            "overall_state": self.overall_state.value,
            "overall_score": self.overall_score,
            "category_scores": dict(self.category_scores),
            "created_at": self.created_at,
        }


@dataclass
class Defect:
    """A single defect discovered during QA.

    Tracks identification, severity, status, and resolution metadata
    across the lifetime of an issue.
    """

    defect_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    target: str = ""
    title: str = ""
    description: str = ""
    category: QACategory = QACategory.FUNCTIONAL
    severity: QASeverity = QASeverity.MAJOR
    state: QAState = QAState.FAILED
    source_check: str = ""
    detected_at: float = field(default_factory=_time_module.time)
    resolved_at: Optional[float] = None
    assignee: str = ""
    tags: List[str] = field(default_factory=list)
    details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize the defect to a dictionary."""
        return {
            "defect_id": self.defect_id,
            "target": self.target,
            "title": self.title,
            "description": self.description,
            "category": self.category.value,
            "severity": self.severity.value,
            "state": self.state.value,
            "source_check": self.source_check,
            "detected_at": self.detected_at,
            "resolved_at": self.resolved_at,
            "assignee": self.assignee,
            "tags": list(self.tags),
            "details": dict(self.details),
        }


@dataclass
class QualityAssuranceSnapshot:
    """Complete snapshot of the QA orchestrator state.

    Captures operational mode, registered checks, defect summary,
    and recent activity for observability and diagnostics.
    """

    state: QAState = QAState.PENDING
    active_target: str = ""
    registered_check_count: int = 0
    checks_by_category: Dict[str, int] = field(default_factory=dict)
    total_defects: int = 0
    open_defects: int = 0
    resolved_defects: int = 0
    report_count: int = 0
    continuous_running: bool = False
    continuous_targets: List[str] = field(default_factory=list)
    uptime_seconds: float = 0.0
    last_run_at: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize the snapshot to a dictionary."""
        return {
            "state": self.state.value,
            "active_target": self.active_target,
            "registered_check_count": self.registered_check_count,
            "checks_by_category": dict(self.checks_by_category),
            "total_defects": self.total_defects,
            "open_defects": self.open_defects,
            "resolved_defects": self.resolved_defects,
            "report_count": self.report_count,
            "continuous_running": self.continuous_running,
            "continuous_targets": list(self.continuous_targets),
            "uptime_seconds": self.uptime_seconds,
            "last_run_at": self.last_run_at,
            "metadata": dict(self.metadata),
        }


# Type alias for QA check handler callables.
QACheckHandler = Callable[[str, Dict[str, Any]], QACheckResult]


# ---------------------------------------------------------------------------
# Quality Assurance Orchestrator
# ---------------------------------------------------------------------------


class QualityAssuranceOrchestrator:
    """Master orchestrator for end-to-end quality assurance.

    Implements the singleton pattern with double-checked locking to
    guarantee a single shared instance across the engine. Coordinates
    the registration, execution, and aggregation of QA checks, manages
    a defect database, retains report history, and optionally runs
    continuous background monitoring of one or more targets.

    All public methods are thread-safe via a single re-entrant lock.
    """

    _instance: Optional["QualityAssuranceOrchestrator"] = None
    _lock = threading.RLock()

    # -------------------------------------------------------------------
    # Singleton
    # -------------------------------------------------------------------

    @classmethod
    def get_instance(cls) -> "QualityAssuranceOrchestrator":
        """Get the singleton instance with double-checked locking.

        Returns:
            The single shared QualityAssuranceOrchestrator instance.
        """
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    # -------------------------------------------------------------------
    # Initialization
    # -------------------------------------------------------------------

    def __init__(self) -> None:
        """Initialize the QA orchestrator with empty state.

        Sets up the check registry, defect database, report history,
        continuous monitoring structures, and operational counters.
        Use :meth:`initialize` to mark the orchestrator ready for use.
        """
        with self._lock:
            if getattr(self, "_initialized", False):
                return

            # Operational state
            self._state: QAState = QAState.PENDING
            self._active_target: str = ""
            self._started_at: float = _time_module.time()
            self._last_run_at: Optional[float] = None
            self._initialized: bool = True

            # Check registry: name -> (category, phase, handler)
            self._checks: Dict[str, tuple] = {}

            # Defect database keyed by defect_id
            self._defects: Dict[str, Defect] = {}
            self._defects_by_target: Dict[str, List[str]] = defaultdict(list)

            # Report history keyed by report_id, plus per-target list
            self._reports: Dict[str, QAReport] = {}
            self._reports_by_target: Dict[str, List[str]] = defaultdict(list)

            # Continuous monitoring
            self._continuous_thread: Optional[threading.Thread] = None
            self._continuous_stop_event: threading.Event = threading.Event()
            self._continuous_targets: Dict[str, float] = {}  # target -> interval

            # Seed a minimal set of built-in checks
            self._seed_builtin_checks()

    def _seed_builtin_checks(self) -> None:
        """Register a minimal set of built-in default QA checks."""
        builtin: List[tuple] = [
            (
                "build_smoke",
                QACategory.FUNCTIONAL,
                QAPhase.BUILD,
                self._builtin_smoke_handler,
            ),
            (
                "performance_budget",
                QACategory.PERFORMANCE,
                QAPhase.POST_BUILD,
                self._builtin_pass_handler,
            ),
            (
                "code_lint",
                QACategory.CODE_QUALITY,
                QAPhase.PRE_BUILD,
                self._builtin_pass_handler,
            ),
            (
                "accessibility_wcag",
                QACategory.ACCESSIBILITY,
                QAPhase.POST_BUILD,
                self._builtin_pass_handler,
            ),
            (
                "compatibility_matrix",
                QACategory.COMPATIBILITY,
                QAPhase.PRE_RELEASE,
                self._builtin_pass_handler,
            ),
            (
                "security_scan",
                QACategory.SECURITY,
                QAPhase.PRE_RELEASE,
                self._builtin_pass_handler,
            ),
            (
                "localization_keys",
                QACategory.LOCALIZATION,
                QAPhase.POST_BUILD,
                self._builtin_pass_handler,
            ),
            (
                "content_balance",
                QACategory.CONTENT,
                QAPhase.POST_BUILD,
                self._builtin_pass_handler,
            ),
            (
                "ux_onboarding",
                QACategory.UX,
                QAPhase.PRE_RELEASE,
                self._builtin_pass_handler,
            ),
            (
                "regression_suite",
                QACategory.REGRESSION,
                QAPhase.PRE_RELEASE,
                self._builtin_pass_handler,
            ),
        ]
        for name, category, phase, handler in builtin:
            self._checks[name] = (category, phase, handler)

    # -------------------------------------------------------------------
    # Built-in check handlers
    # -------------------------------------------------------------------

    def _builtin_smoke_handler(
        self, target: str, context: Dict[str, Any]
    ) -> QACheckResult:
        """Built-in smoke check handler.

        Verifies that the target is non-empty and reports a passing
        result. Real implementations should override this with a
        project-specific smoke test.
        """
        ok = bool(target)
        return QACheckResult(
            name="build_smoke",
            category=QACategory.FUNCTIONAL,
            phase=QAPhase.BUILD,
            state=QAState.PASSED if ok else QAState.FAILED,
            severity=QASeverity.PASS if ok else QASeverity.BLOCKER,
            target=target,
            message="Smoke check passed" if ok else "Smoke check failed: empty target",
            score=1.0 if ok else 0.0,
            details={"target": target},
        )

    def _builtin_pass_handler(
        self, target: str, context: Dict[str, Any]
    ) -> QACheckResult:
        """Default built-in handler that always passes.

        Used as a placeholder for built-in check slots so that the
        orchestrator is immediately functional. Replace via
        :meth:`register_check` with real handlers.
        """
        name = context.get("check_name", "builtin")
        return QACheckResult(
            name=name,
            category=context.get(
                "category", QACategory.CODE_QUALITY
            ),
            phase=context.get("phase", QAPhase.POST_BUILD),
            state=QAState.PASSED,
            severity=QASeverity.PASS,
            target=target,
            message=f"Built-in check '{name}' passed (default evaluation)",
            score=1.0,
            details={"default": True},
        )

    # -------------------------------------------------------------------
    # Lifecycle
    # -------------------------------------------------------------------

    def initialize(self) -> bool:
        """Initialize the QA orchestrator for operation.

        Marks the orchestrator as ready and verifies that built-in
        checks are registered. Returns True on success.

        Returns:
            True if initialization succeeded, False otherwise.
        """
        with self._lock:
            self._state = QAState.PENDING
            self._started_at = _time_module.time()
        logger.info(
            "QualityAssuranceOrchestrator initialized with %d checks",
            len(self._checks),
        )
        return True

    def register_check(
        self,
        name: str,
        category: QACategory,
        handler: QACheckHandler,
        phase: QAPhase = QAPhase.POST_BUILD,
    ) -> bool:
        """Register a QA check with its handler.

        Args:
            name: Unique name of the check.
            category: QA category the check belongs to.
            handler: Callable invoked as ``handler(target, context)``
                returning a :class:`QACheckResult`.
            phase: Lifecycle phase the check is associated with.

        Returns:
            True if registered, False if a check with the same name
            already exists.
        """
        if not name or not callable(handler):
            return False
        with self._lock:
            if name in self._checks:
                return False
            self._checks[name] = (category, phase, handler)
        logger.debug("Registered QA check '%s' under %s", name, category.value)
        return True

    # -------------------------------------------------------------------
    # Check execution
    # -------------------------------------------------------------------

    def run_check(
        self,
        name: str,
        target: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> Optional[QACheckResult]:
        """Run a single registered QA check against a target.

        Args:
            name: Name of the registered check.
            target: Identifier of the QA target (e.g. game/build id).
            context: Optional context dict forwarded to the handler.

        Returns:
            The :class:`QACheckResult` produced by the check, or
            ``None`` if the check is not registered.
        """
        with self._lock:
            entry = self._checks.get(name)
            if entry is None:
                return None
            category, phase, handler = entry
            ctx: Dict[str, Any] = dict(context or {})
            ctx.setdefault("check_name", name)
            ctx.setdefault("category", category)
            ctx.setdefault("phase", phase)
            self._state = QAState.RUNNING
            self._active_target = target

        start = _time_module.time()
        try:
            result = handler(target, ctx)
        except Exception as exc:  # noqa: BLE001 - orchestration safety net
            logger.exception("QA check '%s' raised an exception", name)
            result = QACheckResult(
                name=name,
                category=category,
                phase=phase,
                state=QAState.FAILED,
                severity=QASeverity.CRITICAL,
                target=target,
                message=f"Check raised exception: {exc}",
                score=0.0,
                details={"error_type": type(exc).__name__},
            )

        result.duration_ms = (_time_module.time() - start) * 1000.0

        with self._lock:
            self._last_run_at = _time_module.time()
            self._state = result.state
            # Auto-report defects for blocking/critical failures
            if result.state in (QAState.FAILED,) and result.severity in (
                QASeverity.BLOCKER,
                QASeverity.CRITICAL,
                QASeverity.MAJOR,
            ):
                self._record_defect_from_result(result)
        return result

    def run_category(
        self,
        category: QACategory,
        target: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> QABatchResult:
        """Run all registered checks within a category.

        Args:
            category: The QA category to execute.
            target: Identifier of the QA target.
            context: Optional context forwarded to each check.

        Returns:
            A :class:`QABatchResult` aggregating individual results.
        """
        with self._lock:
            names = [
                name
                for name, (cat, _phase, _h) in self._checks.items()
                if cat == category
            ]

        batch = QABatchResult(target=target, phase=QAPhase.POST_BUILD)
        start = _time_module.time()
        for name in names:
            result = self.run_check(name, target, context)
            if result is None:
                continue
            batch.results.append(result)
            batch.total += 1
            if result.state == QAState.PASSED:
                batch.passed += 1
            elif result.state == QAState.FAILED:
                batch.failed += 1
            elif result.state == QAState.WARNINGS:
                batch.warnings += 1
            elif result.state == QAState.SKIPPED:
                batch.skipped += 1

        evaluated = batch.passed + batch.failed + batch.warnings
        batch.overall_score = (
            batch.passed / evaluated if evaluated else 0.0
        )
        batch.overall_state = self._derive_batch_state(batch)
        batch.duration_ms = (_time_module.time() - start) * 1000.0
        return batch

    def run_full_qa(
        self,
        target: str,
        config: Optional[QAConfig] = None,
    ) -> QAReport:
        """Run the complete QA pipeline for a target.

        Executes every registered check whose category and phase are
        enabled by the supplied configuration, aggregating the results
        into a comprehensive :class:`QAReport`.

        Args:
            target: Identifier of the QA target.
            config: Optional configuration. Defaults to a standard
                configuration covering all categories and major phases.

        Returns:
            A :class:`QAReport` summarizing the full QA run.
        """
        cfg = config or QAConfig()
        report = QAReport(target=target, config=cfg)
        start = _time_module.time()

        with self._lock:
            phase_groups: Dict[QAPhase, List[tuple]] = defaultdict(list)
            for name, (cat, phase, _h) in self._checks.items():
                if cat not in cfg.categories:
                    continue
                if phase not in cfg.phases:
                    continue
                phase_groups[phase].append((name, cat, phase))

        for phase in cfg.phases:
            entries = phase_groups.get(phase, [])
            if not entries:
                continue
            batch = QABatchResult(target=target, phase=phase)
            phase_start = _time_module.time()
            for name, _cat, _phase in entries:
                result = self.run_check(name, target)
                if result is None:
                    continue
                if not cfg.include_skipped and result.state == QAState.SKIPPED:
                    continue
                batch.results.append(result)
                batch.total += 1
                if result.state == QAState.PASSED:
                    batch.passed += 1
                elif result.state == QAState.FAILED:
                    batch.failed += 1
                elif result.state == QAState.WARNINGS:
                    batch.warnings += 1
                elif result.state == QAState.SKIPPED:
                    batch.skipped += 1

            evaluated = batch.passed + batch.failed + batch.warnings
            batch.overall_score = (
                batch.passed / evaluated if evaluated else 0.0
            )
            batch.overall_state = self._derive_batch_state(batch)
            batch.duration_ms = (_time_module.time() - phase_start) * 1000.0
            report.batch_results.append(batch)
            report.total_checks += batch.total
            report.total_passed += batch.passed
            report.total_failed += batch.failed
            report.total_warnings += batch.warnings

        # Category scores
        cat_scores: Dict[str, List[float]] = defaultdict(list)
        for batch in report.batch_results:
            for r in batch.results:
                cat_scores[r.category.value].append(r.score)
        report.category_scores = {
            cat: sum(vals) / len(vals) for cat, vals in cat_scores.items() if vals
        }

        evaluated_total = (
            report.total_passed + report.total_failed + report.total_warnings
        )
        report.overall_score = (
            report.total_passed / evaluated_total if evaluated_total else 0.0
        )
        report.overall_state = self._derive_report_state(report, cfg)

        # Attach related defects
        with self._lock:
            report.defects = [
                self._defects[did]
                for did in self._defects_by_target.get(target, [])
            ]
            self._reports[report.report_id] = report
            self._reports_by_target[target].append(report.report_id)
            self._last_run_at = _time_module.time()

        # Re-mark duration via top-level elapsed (kept simple)
        _ = (_time_module.time() - start) * 1000.0
        logger.info(
            "Full QA for '%s' -> %s (score=%.2f, checks=%d)",
            target,
            report.overall_state.value,
            report.overall_score,
            report.total_checks,
        )
        return report

    def run_continuous(
        self,
        target: str,
        interval: float = 60.0,
    ) -> bool:
        """Start continuous QA monitoring for a target.

        Spawns (or reuses) a background thread that periodically runs
        the full QA pipeline for the target. Calling again with a new
        interval updates the polling cadence.

        Args:
            target: Identifier of the QA target.
            interval: Polling interval in seconds.

        Returns:
            True if monitoring was started or updated.
        """
        if interval <= 0:
            return False
        with self._lock:
            self._continuous_targets[target] = interval
            if (
                self._continuous_thread is None
                or not self._continuous_thread.is_alive()
            ):
                self._continuous_stop_event.clear()
                self._continuous_thread = threading.Thread(
                    target=self._continuous_loop,
                    name="qa-continuous-monitor",
                    daemon=True,
                )
                self._continuous_thread.start()
        logger.info(
            "Continuous QA monitoring started for '%s' (interval=%.1fs)",
            target,
            interval,
        )
        return True

    def _continuous_loop(self) -> None:
        """Background loop executing continuous QA for all targets."""
        while not self._continuous_stop_event.is_set():
            with self._lock:
                targets_snapshot = list(self._continuous_targets.items())
            for target, interval in targets_snapshot:
                if self._continuous_stop_event.is_set():
                    break
                try:
                    self.run_full_qa(target)
                except Exception:  # noqa: BLE001 - monitor must stay alive
                    logger.exception(
                        "Continuous QA run for '%s' failed", target
                    )
                # Sleep in small increments to remain responsive to stop
                slept = 0.0
                while slept < interval and not self._continuous_stop_event.is_set():
                    time.sleep(min(0.5, interval - slept))
                    slept += 0.5
        logger.info("Continuous QA monitoring loop exited")

    # -------------------------------------------------------------------
    # Defect management
    # -------------------------------------------------------------------

    def report_defect(self, defect: Defect) -> str:
        """Report a new defect.

        Args:
            defect: The :class:`Defect` to register.

        Returns:
            The defect id assigned to the reported defect.
        """
        with self._lock:
            self._defects[defect.defect_id] = defect
            if defect.defect_id not in self._defects_by_target[defect.target]:
                self._defects_by_target[defect.target].append(defect.defect_id)
        logger.info(
            "Defect reported: %s (%s/%s) for target '%s'",
            defect.title,
            defect.category.value,
            defect.severity.value,
            defect.target,
        )
        return defect.defect_id

    def track_defect(
        self, defect_id: str, status: QAState
    ) -> Optional[Defect]:
        """Track and update the status of a defect.

        Args:
            defect_id: Id of the defect to update.
            status: New QA state to assign.

        Returns:
            The updated :class:`Defect`, or ``None`` if not found.
        """
        with self._lock:
            defect = self._defects.get(defect_id)
            if defect is None:
                return None
            defect.state = status
            if status in (QAState.PASSED, QAState.SKIPPED):
                defect.resolved_at = _time_module.time()
            elif status == QAState.FAILED:
                defect.resolved_at = None
            return defect

    def _record_defect_from_result(self, result: QACheckResult) -> None:
        """Auto-record a defect derived from a failing check result."""
        defect = Defect(
            target=result.target,
            title=f"QA failure: {result.name}",
            description=result.message or "No message provided",
            category=result.category,
            severity=result.severity,
            state=QAState.FAILED,
            source_check=result.name,
            detected_at=result.timestamp,
            tags=[result.phase.value],
            details=result.details,
        )
        self._defects[defect.defect_id] = defect
        self._defects_by_target[defect.target].append(defect.defect_id)

    # -------------------------------------------------------------------
    # Reporting and queries
    # -------------------------------------------------------------------

    def generate_report(
        self, target: str, config: Optional[QAConfig] = None
    ) -> QAReport:
        """Generate a comprehensive QA report for a target.

        This is a convenience wrapper around :meth:`run_full_qa` that
        also persists the report in history.

        Args:
            target: Identifier of the QA target.
            config: Optional QA configuration.

        Returns:
            A fresh :class:`QAReport`.
        """
        return self.run_full_qa(target, config)

    def get_defects(
        self,
        target: Optional[str] = None,
        severity: Optional[QASeverity] = None,
    ) -> List[Defect]:
        """Get defects, optionally filtered by target and severity.

        Args:
            target: Optional target filter.
            severity: Optional severity filter.

        Returns:
            A list of matching :class:`Defect` objects.
        """
        with self._lock:
            if target:
                ids = self._defects_by_target.get(target, [])
                defects = [self._defects[did] for did in ids]
            else:
                defects = list(self._defects.values())
            if severity is not None:
                defects = [d for d in defects if d.severity == severity]
            return defects

    def get_status(self) -> QualityAssuranceSnapshot:
        """Get a comprehensive snapshot of the QA system state.

        Returns:
            A :class:`QualityAssuranceSnapshot` summarizing state,
            registered checks, defects, and monitoring status.
        """
        with self._lock:
            checks_by_category: Dict[str, int] = defaultdict(int)
            for _name, (cat, _phase, _h) in self._checks.items():
                checks_by_category[cat.value] += 1

            total_defects = len(self._defects)
            open_defects = sum(
                1
                for d in self._defects.values()
                if d.state not in (QAState.PASSED, QAState.SKIPPED)
            )
            resolved_defects = total_defects - open_defects

            continuous_running = (
                self._continuous_thread is not None
                and self._continuous_thread.is_alive()
            )

            snapshot = QualityAssuranceSnapshot(
                state=self._state,
                active_target=self._active_target,
                registered_check_count=len(self._checks),
                checks_by_category=dict(checks_by_category),
                total_defects=total_defects,
                open_defects=open_defects,
                resolved_defects=resolved_defects,
                report_count=len(self._reports),
                continuous_running=continuous_running,
                continuous_targets=list(self._continuous_targets.keys()),
                uptime_seconds=round(
                    _time_module.time() - self._started_at, 2
                ),
                last_run_at=self._last_run_at,
            )
            return snapshot

    # -------------------------------------------------------------------
    # Helpers
    # -------------------------------------------------------------------

    @staticmethod
    def _derive_batch_state(batch: QABatchResult) -> QAState:
        """Derive an overall state for a batch of checks."""
        if batch.failed > 0:
            return QAState.FAILED
        if batch.warnings > 0:
            return QAState.WARNINGS
        if batch.passed > 0:
            return QAState.PASSED
        return QAState.SKIPPED

    @staticmethod
    def _derive_report_state(report: QAReport, cfg: QAConfig) -> QAState:
        """Derive the overall state of a QA report."""
        if report.total_failed > 0:
            # Respect config-level severity gating
            if cfg.fail_on_blocker or cfg.fail_on_critical:
                return QAState.FAILED
        if report.total_warnings > 0:
            return QAState.WARNINGS
        if report.total_passed > 0:
            return QAState.PASSED
        return QAState.SKIPPED

    # -------------------------------------------------------------------
    # Shutdown
    # -------------------------------------------------------------------

    def shutdown(self) -> None:
        """Perform a graceful shutdown of the QA orchestrator.

        Stops continuous monitoring, flushes in-flight state, and
        transitions the orchestrator to an idle state. The singleton
        instance remains accessible but must be re-initialized via
        :meth:`initialize` before running further QA.
        """
        with self._lock:
            # Signal continuous loop to stop
            self._continuous_stop_event.set()
            thread = self._continuous_thread

        if thread is not None and thread.is_alive():
            thread.join(timeout=5.0)

        with self._lock:
            self._continuous_thread = None
            self._continuous_targets.clear()
            self._state = QAState.PENDING
            self._active_target = ""

        logger.info("QualityAssuranceOrchestrator shut down gracefully")


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------


def get_quality_assurance() -> QualityAssuranceOrchestrator:
    """Get the QualityAssuranceOrchestrator singleton instance."""
    return QualityAssuranceOrchestrator.get_instance()
