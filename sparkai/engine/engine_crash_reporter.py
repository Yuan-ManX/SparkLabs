"""
SparkLabs Engine - Crash & Error Reporting System

An original, self-contained runtime crash and error reporting pipeline designed
from the ground up for the SparkLabs AI-native game engine. The system captures
crash and error reports as they occur during play sessions, fingerprints each
report so that recurrent defects roll up into actionable groups, and exposes
release-level health metrics that quantify the player-visible stability of a
build.

The design is intentionally engine-native: it owns no external dependencies,
serializes to plain JSON-friendly dictionaries so any route layer can project
the data over HTTP, and is fully thread-safe through a single reentrant lock.
Every mutation is recorded as an audit event so that triage decisions, group
merges, and resolution actions form a traceable history.

Architecture:
  CrashReporterSystem (singleton)
    |-- StackFrame, Breadcrumb, CrashReport, CrashGroup, SymbolicationResult,
    |   ReleaseHealth, CrashReporterStats, CrashReporterSnapshot,
    |   CrashReporterEvent
    |-- ErrorSeverity, ErrorCategory, Platform, ReportState, BreadcombType,
        StackFrameKind, CrashReporterEventKind

Core Capabilities:
  - submit_report: Capture a runtime crash or error, fingerprint it, and roll
    it up into a crash group (creating the group on first occurrence).
  - get_report / list_reports: Lookup and filtered queries over the report
    store by severity, category, state, platform, group, or player.
  - update_report_state / add_tag / remove_tag: Triage and annotate reports.
  - get_group / list_groups: Inspect aggregated crash groups and filter them
    by state, category, severity, or assignee.
  - assign_group / update_group_state / merge_groups: Route groups to owners,
    advance their lifecycle, and deduplicate groups that share a root cause.
  - compute_fingerprint: Deterministic signature over message, category, and
    the first user-authored stack frame.
  - add_breadcrumb / get_breadcrumbs: Per-session breadcrumb trail captured
    ahead of a crash so the moments leading up to a failure can be replayed.
  - symbolicate: Resolve native frames into symbolicated stack frames and
    report missing symbol files.
  - get_release_health: Per-build stability metrics computed live from the
    report store, including crash-free and error-free session rates.
  - list_events / get_stats / get_status / get_snapshot / reset: Observability
    and lifecycle management for the entire subsystem.
"""

from __future__ import annotations

import hashlib
import threading
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple


# ---------------------------------------------------------------------------
# Capacity Constants
# ---------------------------------------------------------------------------

# Bounded stores keep memory predictable under sustained crash traffic. FIFO
# eviction is applied after every insert so the most recent context is always
# retained while the oldest records are dropped first.
_MAX_REPORTS: int = 20000
_MAX_GROUPS: int = 5000
_MAX_BREADCRUMBS: int = 100          # per session breadcrumb buffer
_MAX_BREADCRUMB_SESSIONS: int = 1000  # distinct sessions tracked
_MAX_EVENTS: int = 10000
_MAX_RELEASE_HEALTH: int = 500
_FINGERPRINT_LENGTH: int = 16


# ---------------------------------------------------------------------------
# Helper Functions
# ---------------------------------------------------------------------------


def _now() -> str:
    """Return the current UTC time as an ISO-8601 string with a 'Z' suffix."""
    return datetime.utcnow().isoformat() + "Z"


def _new_id(prefix: str = "") -> str:
    """Generate a short unique identifier, optionally prefixed."""
    base = uuid.uuid4().hex[:12]
    return f"{prefix}_{base}" if prefix else base


def _evict_fifo_dict(store: Dict[str, Any], max_size: int) -> None:
    """Evict the oldest entries from a dict to keep ``len(store) <= max_size``.

    Dictionary insertion order is preserved in Python 3.7+, so the first
    inserted key is treated as the oldest entry and removed first.
    """
    cap = max(1, int(max_size))
    while len(store) > cap:
        oldest_key = next(iter(store), None)
        if oldest_key is None:
            break
        store.pop(oldest_key, None)


def _evict_fifo_list(store: List[Any], max_size: int) -> None:
    """Evict the oldest entries from a list to keep ``len(store) <= max_size``."""
    cap = max(1, int(max_size))
    while len(store) > cap:
        if not store:
            break
        store.pop(0)


def _to_jsonable(value: Any) -> Any:
    """Convert ``value`` into something safe to drop into a JSON payload.

    Handles ``None``, ``Enum`` (returns ``.value``), ``dict``, ``list``/``tuple``,
    ``set`` (sorted for determinism), and any object exposing ``to_dict`` (treated
    as a dataclass). Everything else passes through unchanged.
    """
    if value is None:
        return None
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, dict):
        return {str(k): _to_jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_to_jsonable(v) for v in value]
    if isinstance(value, set):
        try:
            return [_to_jsonable(v) for v in sorted(value, key=lambda x: str(x))]
        except TypeError:
            return [_to_jsonable(v) for v in value]
    if hasattr(value, "to_dict") and callable(value.to_dict):
        return _dataclass_to_dict(value)
    return value


def _dataclass_to_dict(instance: Any) -> Dict[str, Any]:
    """Convert a dataclass instance to a plain dictionary.

    Iterates ``__dataclass_fields__`` and routes each value through
    ``_to_jsonable`` so nested dataclasses, enums, sets, and collections are
    normalized consistently.
    """
    if instance is None:
        return {}
    if not hasattr(instance, "__dataclass_fields__"):
        return dict(instance) if isinstance(instance, dict) else {}
    out: Dict[str, Any] = {}
    for name in getattr(instance, "__dataclass_fields__", {}).keys():
        try:
            raw = getattr(instance, name)
        except Exception:
            continue
        out[name] = _to_jsonable(raw)
    return out


# ---------------------------------------------------------------------------
# Domain Enums
# ---------------------------------------------------------------------------


class ErrorSeverity(Enum):
    """Severity tier for a crash or error report."""
    FATAL = "fatal"
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"
    DEBUG = "debug"


class ErrorCategory(Enum):
    """Coarse-grained classification of the defect that produced a report."""
    CRASH = "crash"
    ASSERTION = "assertion"
    NULL_POINTER = "null_pointer"
    OUT_OF_MEMORY = "out_of_memory"
    NETWORK = "network"
    RENDERING = "rendering"
    AUDIO = "audio"
    INPUT = "input"
    SCRIPTING = "scripting"
    RESOURCE_LOADING = "resource_loading"
    LOGIC = "logic"
    UNKNOWN = "unknown"


class Platform(Enum):
    """Runtime platform that emitted the report."""
    WINDOWS = "windows"
    MACOS = "macos"
    LINUX = "linux"
    ANDROID = "android"
    IOS = "ios"
    WEB = "web"
    CONSOLE_PS5 = "console_ps5"
    CONSOLE_XBOX = "console_xbox"
    CONSOLE_SWITCH = "console_switch"


class ReportState(Enum):
    """Lifecycle state shared by individual reports and aggregated groups."""
    NEW = "new"
    TRIAGED = "triaged"
    IN_PROGRESS = "in_progress"
    RESOLVED = "resolved"
    IGNORED = "ignored"
    REOPENED = "reopened"


class BreadcombType(Enum):
    """Category of a breadcrumb left in a session's trail."""
    NAVIGATION = "navigation"
    ACTION = "action"
    LOG = "log"
    NETWORK = "network"
    USER_INPUT = "user_input"
    SYSTEM = "system"
    ERROR = "error"


class StackFrameKind(Enum):
    """Origin of a single stack frame, used to guide symbolication."""
    NATIVE = "native"
    MANAGED = "managed"
    SCRIPT = "script"
    INLINED = "inlined"
    UNKNOWN = "unknown"


class CrashReporterEventKind(Enum):
    """Audit event kinds emitted by the crash reporting system."""
    REPORT_RECEIVED = "report_received"
    REPORT_STATE_CHANGED = "report_state_changed"
    REPORT_TRIAGED = "report_triaged"
    REPORT_RESOLVED = "report_resolved"
    GROUP_CREATED = "group_created"
    GROUP_UPDATED = "group_updated"
    GROUP_MERGED = "group_merged"
    GROUP_ASSIGNED = "group_assigned"
    GROUP_STATE_CHANGED = "group_state_changed"
    TAG_ADDED = "tag_added"
    TAG_REMOVED = "tag_removed"
    BREADCRUMB_ADDED = "breadcrumb_added"
    SYMBOLICATED = "symbolicated"
    RELEASE_HEALTH_UPDATED = "release_health_updated"
    SYSTEM_RESET = "system_reset"
    SNAPSHOT_TAKEN = "snapshot_taken"


# ---------------------------------------------------------------------------
# Data Classes
# ---------------------------------------------------------------------------


@dataclass
class StackFrame:
    """A single frame in a crash stack trace.

    Frames are classified by ``frame_kind`` so the symbolicator can decide
    whether native symbol lookup is required. ``is_user_code`` marks frames
    that originate from the project's own scripts and are therefore the most
    actionable starting point for fingerprinting.
    """
    function_name: str
    file_path: str = ""
    line_number: int = 0
    column_number: int = 0
    module_name: str = ""
    frame_kind: StackFrameKind = StackFrameKind.UNKNOWN
    source_snippet: str = ""
    is_user_code: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class Breadcrumb:
    """A breadcrumb captured during a session before a crash occurs.

    Breadcrumbs reconstruct the moments leading up to a failure: navigation
    transitions, network calls, user input, and log lines. Each breadcrumb is
    timestamped and may carry an arbitrary ``data`` payload.
    """
    timestamp: str = field(default_factory=_now)
    type: BreadcombType = BreadcombType.LOG
    message: str = ""
    level: str = "info"
    category: str = ""
    data: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class CrashReport:
    """A single crash or error report submitted by a runtime session.

    Reports are fingerprinted on submission and attached to a ``CrashGroup``
    so that recurrent defects can be triaged as a unit. The ``occurrence_count``
    field is initialized to 1 for an individual report; the owning group's
    occurrence count is incremented separately to reflect aggregate frequency.
    """
    report_id: str
    session_id: str = ""
    player_id: str = ""
    build_version: str = ""
    platform: Platform = Platform.WINDOWS
    severity: ErrorSeverity = ErrorSeverity.ERROR
    category: ErrorCategory = ErrorCategory.UNKNOWN
    message: str = ""
    stack_trace: List[StackFrame] = field(default_factory=list)
    breadcrumbs: List[Breadcrumb] = field(default_factory=list)
    context: Dict[str, Any] = field(default_factory=dict)
    state: ReportState = ReportState.NEW
    group_id: str = ""
    created_at: str = field(default_factory=_now)
    fingerprint: str = ""
    occurrence_count: int = 1
    tags: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class CrashGroup:
    """An aggregated group of crash reports sharing a fingerprint.

    The group tracks the first and last time the defect was seen, the total
    number of occurrences, the set of affected players and platforms, and the
    lifecycle state used to drive triage workflows. Resolution metadata is
    captured when a group moves into the ``RESOLVED`` state.
    """
    group_id: str
    fingerprint: str = ""
    title: str = ""
    message: str = ""
    category: ErrorCategory = ErrorCategory.UNKNOWN
    severity: ErrorSeverity = ErrorSeverity.ERROR
    state: ReportState = ReportState.NEW
    first_seen: str = field(default_factory=_now)
    last_seen: str = field(default_factory=_now)
    occurrence_count: int = 0
    affected_players: Set[str] = field(default_factory=set)
    affected_platforms: Set[Platform] = field(default_factory=set)
    sample_report_id: str = ""
    resolved_at: str = ""
    resolved_by: str = ""
    assignee: str = ""
    fix_version: str = ""
    tags: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class SymbolicationResult:
    """Outcome of symbolication for a single report.

    ``status`` is a short string (``completed`` / ``partial`` / ``failed``).
    ``missing_symbols`` lists module or file identifiers for which no symbol
    file was available, and ``symbolicated_frames`` returns the resolved frame
    list in stack order.
    """
    report_id: str
    status: str = "completed"
    symbolicated_frames: List[StackFrame] = field(default_factory=list)
    missing_symbols: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class ReleaseHealth:
    """Stability metrics for a single build version.

    Computed live from the report store on demand. ``crash_rate`` and
    ``error_rate`` are expressed as fractions in the range ``[0.0, 1.0]``;
    a session is counted as crash-free when no fatal report references it and
    error-free when no fatal or error report references it.
    """
    build_version: str
    total_sessions: int = 0
    crash_free_sessions: int = 0
    error_free_sessions: int = 0
    crash_rate: float = 0.0
    error_rate: float = 0.0
    top_crashing_groups: List[str] = field(default_factory=list)
    last_updated: str = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class CrashReporterStats:
    """Aggregate statistics summarizing the crash reporting subsystem."""
    total_reports: int = 0
    new_reports: int = 0
    triaged_reports: int = 0
    resolved_reports: int = 0
    total_groups: int = 0
    active_groups: int = 0
    resolved_groups: int = 0
    total_sessions: int = 0
    crash_free_rate: float = 0.0
    total_events: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class CrashReporterSnapshot:
    """A point-in-time snapshot of the entire crash reporting subsystem."""
    reports: List[Dict[str, Any]] = field(default_factory=list)
    groups: List[Dict[str, Any]] = field(default_factory=list)
    stats: Dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class CrashReporterEvent:
    """An audit event emitted by the crash reporting subsystem."""
    event_id: str
    kind: CrashReporterEventKind = CrashReporterEventKind.REPORT_RECEIVED
    timestamp: str = field(default_factory=_now)
    data: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


# ---------------------------------------------------------------------------
# CrashReporterSystem - Thread-Safe Singleton
# ---------------------------------------------------------------------------


class CrashReporterSystem:
    """Engine-level crash and error reporting manager.

    Captures runtime crash and error reports, fingerprints them into
    deduplicated crash groups, maintains per-session breadcrumb trails,
    symbolicates stack traces, and computes per-build release health metrics.
    All public state mutations are recorded as audit events.

    Thread-safe via a reentrant lock. Use ``get_crash_reporter_system()`` to
    obtain the singleton instance.

    Usage:
        reporter = get_crash_reporter_system()
        report = reporter.submit_report(
            session_id="sess_1",
            player_id="player_1",
            build_version="1.0.1",
            platform=Platform.WINDOWS,
            severity=ErrorSeverity.FATAL,
            category=ErrorCategory.NULL_POINTER,
            message="NullPointerException in PlayerInventory",
            stack_trace=[StackFrame(function_name="get_items", is_user_code=True)],
        )
        group = reporter.get_group(report.group_id)
        health = reporter.get_release_health("1.0.1")
    """

    _instance: Optional["CrashReporterSystem"] = None
    _inner_lock = threading.RLock()
    _initialized: bool = False

    def __new__(cls) -> "CrashReporterSystem":
        if cls._instance is None:
            with cls._inner_lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self) -> None:
        with self._inner_lock:  # IMPORTANT: use _inner_lock, NOT self._lock (which doesn't exist yet)
            if self._initialized:
                return
            self._lock = threading.RLock()  # set instance attribute here
            # ----- initialize all stores here -----
            self._reports: Dict[str, CrashReport] = {}
            self._groups: Dict[str, CrashGroup] = {}
            self._fingerprint_index: Dict[str, str] = {}  # fingerprint -> group_id
            self._breadcrumbs: Dict[str, List[Breadcrumb]] = {}  # session_id -> breadcrumbs
            self._release_health: Dict[str, ReleaseHealth] = {}  # build_version -> health
            self._events: List[CrashReporterEvent] = []
            self._initialized = True
            self._seed_data()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _emit(self, kind: CrashReporterEventKind, data: Dict[str, Any]) -> None:
        """Append an audit event to the in-memory event log.

        Assumes the caller already holds ``self._lock``; it does not re-acquire
        the lock so it can be invoked freely from within locked public methods.
        """
        event = CrashReporterEvent(
            event_id=_new_id("evt"),
            kind=kind,
            timestamp=_now(),
            data=dict(data) if data else {},
        )
        self._events.append(event)
        _evict_fifo_list(self._events, _MAX_EVENTS)

    @staticmethod
    def _first_user_frame(stack_trace: List[StackFrame]) -> str:
        """Return a canonical string for the first user-authored frame.

        Falls back to the top-of-stack frame when no frame is flagged as user
        code, and to an empty string when the trace is empty.
        """
        if not stack_trace:
            return ""
        for frame in stack_trace:
            if frame.is_user_code:
                return f"{frame.function_name}:{frame.file_path}:{frame.line_number}"
        top = stack_trace[0]
        return f"{top.function_name}:{top.file_path}:{top.line_number}"

    # ------------------------------------------------------------------
    # Report submission
    # ------------------------------------------------------------------

    def submit_report(
        self,
        session_id: str,
        player_id: str,
        build_version: str,
        platform: Platform,
        severity: ErrorSeverity,
        category: ErrorCategory,
        message: str,
        stack_trace: Optional[List[StackFrame]] = None,
        breadcrumbs: Optional[List[Breadcrumb]] = None,
        context: Optional[Dict[str, Any]] = None,
        tags: Optional[List[str]] = None,
    ) -> Optional[CrashReport]:
        """Capture a new crash or error report.

        Computes a fingerprint from the message, category, and first user
        stack frame, then finds or creates the matching crash group. The
        group's ``last_seen``, ``occurrence_count``, ``affected_players`` and
        ``affected_platforms`` are updated to reflect the new occurrence.

        Returns the created ``CrashReport`` instance, or ``None`` when required
        arguments are missing or fail validation.
        """
        with self._lock:
            if not session_id or not player_id or not message:
                return None
            if not isinstance(platform, Platform):
                return None
            if not isinstance(severity, ErrorSeverity):
                return None
            if not isinstance(category, ErrorCategory):
                return None

            report_id = _new_id("rpt")
            now = _now()
            stack = list(stack_trace) if stack_trace else []
            crumbs = list(breadcrumbs) if breadcrumbs else []
            ctx = dict(context) if context else {}
            tag_list = list(tags) if tags else []
            fingerprint = self._compute_fingerprint_unlocked(message, category, stack)

            report = CrashReport(
                report_id=report_id,
                session_id=session_id,
                player_id=player_id,
                build_version=build_version,
                platform=platform,
                severity=severity,
                category=category,
                message=message,
                stack_trace=stack,
                breadcrumbs=crumbs,
                context=ctx,
                state=ReportState.NEW,
                group_id="",
                created_at=now,
                fingerprint=fingerprint,
                occurrence_count=1,
                tags=tag_list,
            )

            # Roll the report up into a crash group by fingerprint.
            existing_group_id = self._fingerprint_index.get(fingerprint)
            group = self._groups.get(existing_group_id) if existing_group_id else None
            if group is None:
                group = CrashGroup(
                    group_id=_new_id("grp"),
                    fingerprint=fingerprint,
                    title=(message or "").strip()[:160] or "Untitled crash",
                    message=message,
                    category=category,
                    severity=severity,
                    state=ReportState.NEW,
                    first_seen=now,
                    last_seen=now,
                    occurrence_count=1,
                    affected_players={player_id},
                    affected_platforms={platform},
                    sample_report_id=report_id,
                    resolved_at="",
                    resolved_by="",
                    assignee="",
                    fix_version="",
                    tags=list(tag_list),
                )
                self._groups[group.group_id] = group
                _evict_fifo_dict(self._groups, _MAX_GROUPS)
                self._fingerprint_index[fingerprint] = group.group_id
                self._emit(
                    CrashReporterEventKind.GROUP_CREATED,
                    {"group_id": group.group_id, "fingerprint": fingerprint, "category": category},
                )
            else:
                group.occurrence_count += 1
                group.last_seen = now
                group.affected_players.add(player_id)
                group.affected_platforms.add(platform)
                # Escalate group severity so the group always reflects the
                # worst observed outcome for the underlying defect.
                if _severity_rank(severity) > _severity_rank(group.severity):
                    group.severity = severity
                if not group.sample_report_id:
                    group.sample_report_id = report_id
                self._emit(
                    CrashReporterEventKind.GROUP_UPDATED,
                    {"group_id": group.group_id, "occurrence_count": group.occurrence_count},
                )

            report.group_id = group.group_id
            self._reports[report_id] = report
            _evict_fifo_dict(self._reports, _MAX_REPORTS)

            self._emit(
                CrashReporterEventKind.REPORT_RECEIVED,
                {
                    "report_id": report_id,
                    "group_id": group.group_id,
                    "severity": severity,
                    "category": category,
                    "platform": platform,
                },
            )
            return report

    # ------------------------------------------------------------------
    # Report queries
    # ------------------------------------------------------------------

    def get_report(self, report_id: str) -> Optional[CrashReport]:
        """Return the report with ``report_id``, or ``None`` if not found."""
        with self._lock:
            return self._reports.get(report_id)

    def list_reports(
        self,
        severity: Optional[ErrorSeverity] = None,
        category: Optional[ErrorCategory] = None,
        state: Optional[ReportState] = None,
        platform: Optional[Platform] = None,
        group_id: Optional[str] = None,
        player_id: Optional[str] = None,
        limit: int = 100,
    ) -> List[CrashReport]:
        """List reports, optionally filtered by several attributes.

        Filters are AND-combined. Results are returned newest-first and capped
        at ``limit`` entries.
        """
        with self._lock:
            results: List[CrashReport] = []
            cap = max(0, int(limit))
            # Iterate in reverse insertion order so the newest reports win.
            for report in reversed(list(self._reports.values())):
                if severity is not None and report.severity != severity:
                    continue
                if category is not None and report.category != category:
                    continue
                if state is not None and report.state != state:
                    continue
                if platform is not None and report.platform != platform:
                    continue
                if group_id is not None and report.group_id != group_id:
                    continue
                if player_id is not None and report.player_id != player_id:
                    continue
                results.append(report)
                if len(results) >= cap:
                    break
            return results

    # ------------------------------------------------------------------
    # Report triage and tagging
    # ------------------------------------------------------------------

    def update_report_state(
        self,
        report_id: str,
        new_state: ReportState,
        assignee: Optional[str] = None,
    ) -> Optional[CrashReport]:
        """Advance a report to ``new_state``.

        When ``assignee`` is provided and the report belongs to a group, the
        group's assignee is updated as well. Returns the updated report or
        ``None`` when the report is missing or the state is invalid.
        """
        with self._lock:
            report = self._reports.get(report_id)
            if report is None or not isinstance(new_state, ReportState):
                return None
            old_state = report.state
            report.state = new_state
            if assignee is not None and report.group_id:
                group = self._groups.get(report.group_id)
                if group is not None:
                    group.assignee = assignee
            if new_state == ReportState.TRIAGED:
                event_kind = CrashReporterEventKind.REPORT_TRIAGED
            elif new_state == ReportState.RESOLVED:
                event_kind = CrashReporterEventKind.REPORT_RESOLVED
            else:
                event_kind = CrashReporterEventKind.REPORT_STATE_CHANGED
            self._emit(
                event_kind,
                {"report_id": report_id, "old_state": old_state, "new_state": new_state},
            )
            return report

    def add_tag(self, report_id: str, tag: str) -> Optional[CrashReport]:
        """Add ``tag`` to a report's tag list. Returns the updated report."""
        with self._lock:
            report = self._reports.get(report_id)
            if report is None or not tag:
                return None
            if tag not in report.tags:
                report.tags.append(tag)
                self._emit(CrashReporterEventKind.TAG_ADDED, {"report_id": report_id, "tag": tag})
            return report

    def remove_tag(self, report_id: str, tag: str) -> Optional[CrashReport]:
        """Remove ``tag`` from a report's tag list. Returns the updated report."""
        with self._lock:
            report = self._reports.get(report_id)
            if report is None or not tag:
                return None
            if tag in report.tags:
                report.tags.remove(tag)
                self._emit(CrashReporterEventKind.TAG_REMOVED, {"report_id": report_id, "tag": tag})
            return report

    # ------------------------------------------------------------------
    # Crash group queries
    # ------------------------------------------------------------------

    def get_group(self, group_id: str) -> Optional[CrashGroup]:
        """Return the crash group with ``group_id``, or ``None`` if not found."""
        with self._lock:
            return self._groups.get(group_id)

    def list_groups(
        self,
        state: Optional[ReportState] = None,
        category: Optional[ErrorCategory] = None,
        severity: Optional[ErrorSeverity] = None,
        assignee: Optional[str] = None,
        limit: int = 100,
    ) -> List[CrashGroup]:
        """List crash groups, optionally filtered by several attributes.

        Results are ordered by ``last_seen`` descending so the most recently
        active groups surface first.
        """
        with self._lock:
            cap = max(0, int(limit))
            candidates: List[CrashGroup] = []
            for group in self._groups.values():
                if state is not None and group.state != state:
                    continue
                if category is not None and group.category != category:
                    continue
                if severity is not None and group.severity != severity:
                    continue
                if assignee is not None and group.assignee != assignee:
                    continue
                candidates.append(group)
            candidates.sort(key=lambda g: g.last_seen, reverse=True)
            return candidates[:cap]

    # ------------------------------------------------------------------
    # Crash group triage
    # ------------------------------------------------------------------

    def assign_group(self, group_id: str, assignee: str) -> Optional[CrashGroup]:
        """Assign ``assignee`` to a crash group. Returns the updated group."""
        with self._lock:
            group = self._groups.get(group_id)
            if group is None or not assignee:
                return None
            group.assignee = assignee
            self._emit(
                CrashReporterEventKind.GROUP_ASSIGNED,
                {"group_id": group_id, "assignee": assignee},
            )
            return group

    def update_group_state(
        self,
        group_id: str,
        new_state: ReportState,
        resolved_by: str = "",
        fix_version: str = "",
    ) -> Optional[CrashGroup]:
        """Advance a crash group to ``new_state``.

        When resolving, ``resolved_by`` and ``fix_version`` are recorded and
        ``resolved_at`` is timestamped. Reopening a group clears prior
        resolution metadata. Returns the updated group or ``None`` if missing.
        """
        with self._lock:
            group = self._groups.get(group_id)
            if group is None or not isinstance(new_state, ReportState):
                return None
            old_state = group.state
            group.state = new_state
            if new_state == ReportState.RESOLVED:
                group.resolved_at = _now()
                group.resolved_by = resolved_by
                group.fix_version = fix_version
            elif new_state == ReportState.REOPENED:
                group.resolved_at = ""
                group.resolved_by = ""
                group.fix_version = ""
            self._emit(
                CrashReporterEventKind.GROUP_STATE_CHANGED,
                {
                    "group_id": group_id,
                    "old_state": old_state,
                    "new_state": new_state,
                    "resolved_by": group.resolved_by,
                    "fix_version": group.fix_version,
                },
            )
            return group

    def merge_groups(
        self,
        source_group_id: str,
        target_group_id: str,
    ) -> Optional[CrashGroup]:
        """Merge ``source_group_id`` into ``target_group_id``.

        The target absorbs the source's occurrence count, affected players,
        and affected platforms. ``first_seen``/``last_seen`` are widened to
        span both groups. Every report previously attached to the source is
        re-pointed at the target, the source fingerprint is re-indexed to the
        target, and the source group is removed.

        Returns the merged target group, or ``None`` when either group is
        missing or the two ids are identical.
        """
        with self._lock:
            source = self._groups.get(source_group_id)
            target = self._groups.get(target_group_id)
            if source is None or target is None:
                return None
            if source_group_id == target_group_id:
                return None

            target.occurrence_count += source.occurrence_count
            target.affected_players |= source.affected_players
            target.affected_platforms |= source.affected_platforms
            if source.first_seen and (not target.first_seen or source.first_seen < target.first_seen):
                target.first_seen = source.first_seen
            if source.last_seen and (not target.last_seen or source.last_seen > target.last_seen):
                target.last_seen = source.last_seen
            if _severity_rank(source.severity) > _severity_rank(target.severity):
                target.severity = source.severity
            for tag in source.tags:
                if tag not in target.tags:
                    target.tags.append(tag)

            # Re-point reports and re-index the source fingerprint.
            for report in self._reports.values():
                if report.group_id == source_group_id:
                    report.group_id = target_group_id
            self._fingerprint_index[source.fingerprint] = target_group_id

            del self._groups[source_group_id]
            self._emit(
                CrashReporterEventKind.GROUP_MERGED,
                {
                    "source_group_id": source_group_id,
                    "target_group_id": target_group_id,
                    "occurrence_count": target.occurrence_count,
                },
            )
            return target

    # ------------------------------------------------------------------
    # Fingerprinting
    # ------------------------------------------------------------------

    def compute_fingerprint(
        self,
        message: str,
        category: ErrorCategory,
        stack_trace: List[StackFrame],
    ) -> str:
        """Compute a deterministic fingerprint for a report.

        The fingerprint is a truncated SHA-256 digest over the message, the
        category value, and the canonical first user-authored stack frame.
        Reports that share these three signals roll up into the same crash
        group even when their stacks differ in unrelated frames.
        """
        with self._lock:
            return self._compute_fingerprint_unlocked(message, category, stack_trace)

    def _compute_fingerprint_unlocked(
        self,
        message: str,
        category: ErrorCategory,
        stack_trace: List[StackFrame],
    ) -> str:
        """Fingerprint helper that assumes the lock is already held."""
        first_user = self._first_user_frame(stack_trace)
        category_value = category.value if isinstance(category, ErrorCategory) else str(category)
        raw = f"{(message or '').strip()}|{category_value}|{first_user}"
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:_FINGERPRINT_LENGTH]

    # ------------------------------------------------------------------
    # Breadcrumbs
    # ------------------------------------------------------------------

    def add_breadcrumb(
        self,
        session_id: str,
        type: BreadcombType,
        message: str,
        level: str = "info",
        category: str = "",
        data: Optional[Dict[str, Any]] = None,
    ) -> Optional[Breadcrumb]:
        """Append a breadcrumb to a session's trail.

        Each session keeps a bounded FIFO buffer of breadcrumbs so the most
        recent context leading up to a crash is preserved. The number of
        distinct tracked sessions is also bounded.

        Returns the created ``Breadcrumb``, or ``None`` when ``session_id`` is
        missing or ``type`` is not a ``BreadcombType``.
        """
        with self._lock:
            if not session_id or not isinstance(type, BreadcombType):
                return None
            crumb = Breadcrumb(
                timestamp=_now(),
                type=type,
                message=message,
                level=level,
                category=category,
                data=dict(data) if data else {},
            )
            self._breadcrumbs.setdefault(session_id, []).append(crumb)
            _evict_fifo_list(self._breadcrumbs[session_id], _MAX_BREADCRUMBS)
            _evict_fifo_dict(self._breadcrumbs, _MAX_BREADCRUMB_SESSIONS)
            self._emit(
                CrashReporterEventKind.BREADCRUMB_ADDED,
                {"session_id": session_id, "type": type, "message": message},
            )
            return crumb

    def get_breadcrumbs(self, session_id: str, limit: int = 100) -> List[Breadcrumb]:
        """Return the most recent breadcrumbs for ``session_id``."""
        with self._lock:
            crumbs = self._breadcrumbs.get(session_id, [])
            cap = max(0, int(limit))
            return list(crumbs[-cap:]) if cap else list(crumbs)

    # ------------------------------------------------------------------
    # Symbolication
    # ------------------------------------------------------------------

    def symbolicate(self, report_id: str) -> Optional[SymbolicationResult]:
        """Symbolicate the stack trace for a report.

        This is a placeholder implementation: it copies the report's frames
        into a ``SymbolicationResult`` and flags native frames that lack a
        function name as missing-symbol candidates. Returns ``None`` when the
        report does not exist.
        """
        with self._lock:
            report = self._reports.get(report_id)
            if report is None:
                return None
            symbolicated: List[StackFrame] = []
            missing: List[str] = []
            for frame in report.stack_trace:
                symbolicated.append(
                    StackFrame(
                        function_name=frame.function_name,
                        file_path=frame.file_path,
                        line_number=frame.line_number,
                        column_number=frame.column_number,
                        module_name=frame.module_name,
                        frame_kind=frame.frame_kind,
                        source_snippet=frame.source_snippet,
                        is_user_code=frame.is_user_code,
                    )
                )
                if frame.frame_kind == StackFrameKind.NATIVE and not frame.function_name:
                    identifier = frame.module_name or frame.file_path or "unknown_module"
                    if identifier not in missing:
                        missing.append(identifier)
            status = "completed" if not missing else "partial"
            result = SymbolicationResult(
                report_id=report_id,
                status=status,
                symbolicated_frames=symbolicated,
                missing_symbols=missing,
            )
            self._emit(
                CrashReporterEventKind.SYMBOLICATED,
                {"report_id": report_id, "status": status, "missing_count": len(missing)},
            )
            return result

    # ------------------------------------------------------------------
    # Release health
    # ------------------------------------------------------------------

    def get_release_health(self, build_version: str) -> ReleaseHealth:
        """Return release health metrics for ``build_version``.

        Creates the entry on first access and recomputes the metrics live from
        the current report store. A session is crash-free when no fatal report
        references it and error-free when no fatal or error report references
        it.
        """
        with self._lock:
            if not build_version:
                build_version = "unknown"
            health = self._release_health.get(build_version)
            if health is None:
                health = ReleaseHealth(build_version=build_version)
                self._release_health[build_version] = health
                _evict_fifo_dict(self._release_health, _MAX_RELEASE_HEALTH)

            version_reports = [r for r in self._reports.values() if r.build_version == build_version]
            sessions: Set[str] = {r.session_id for r in version_reports if r.session_id}
            crashed_sessions: Set[str] = {
                r.session_id for r in version_reports
                if r.severity == ErrorSeverity.FATAL and r.session_id
            }
            errored_sessions: Set[str] = {
                r.session_id for r in version_reports
                if r.severity in (ErrorSeverity.FATAL, ErrorSeverity.ERROR) and r.session_id
            }

            total = len(sessions)
            crash_count = len(crashed_sessions)
            error_count = len(errored_sessions)
            health.total_sessions = total
            health.crash_free_sessions = max(0, total - crash_count)
            health.error_free_sessions = max(0, total - error_count)
            health.crash_rate = (crash_count / total) if total else 0.0
            health.error_rate = (error_count / total) if total else 0.0

            # Top crashing groups by fatal occurrence for this build.
            group_counts: Dict[str, int] = {}
            for r in version_reports:
                if r.group_id and r.severity == ErrorSeverity.FATAL:
                    group_counts[r.group_id] = group_counts.get(r.group_id, 0) + 1
            ranked = sorted(group_counts.items(), key=lambda kv: kv[1], reverse=True)
            health.top_crashing_groups = [gid for gid, _ in ranked[:5]]
            health.last_updated = _now()

            self._emit(
                CrashReporterEventKind.RELEASE_HEALTH_UPDATED,
                {
                    "build_version": build_version,
                    "total_sessions": total,
                    "crash_rate": health.crash_rate,
                    "error_rate": health.error_rate,
                },
            )
            return health

    # ------------------------------------------------------------------
    # Observability and lifecycle
    # ------------------------------------------------------------------

    def list_events(
        self,
        limit: int = 100,
        kind: Optional[CrashReporterEventKind] = None,
    ) -> List[CrashReporterEvent]:
        """List recent audit events, optionally filtered by ``kind``."""
        with self._lock:
            cap = max(0, int(limit))
            events = self._events
            if kind is not None:
                events = [e for e in events if e.kind == kind]
            return list(events[-cap:]) if cap else list(events)

    def get_stats(self) -> CrashReporterStats:
        """Return aggregate statistics computed from the current stores."""
        with self._lock:
            new_reports = sum(1 for r in self._reports.values() if r.state == ReportState.NEW)
            triaged_reports = sum(
                1 for r in self._reports.values()
                if r.state in (ReportState.TRIAGED, ReportState.IN_PROGRESS)
            )
            resolved_reports = sum(1 for r in self._reports.values() if r.state == ReportState.RESOLVED)
            active_groups = sum(
                1 for g in self._groups.values()
                if g.state not in (ReportState.RESOLVED, ReportState.IGNORED)
            )
            resolved_groups = sum(1 for g in self._groups.values() if g.state == ReportState.RESOLVED)
            total_sessions = sum(h.total_sessions for h in self._release_health.values())

            crash_free_rate = 1.0
            if total_sessions:
                crash_sessions = 0
                counted_sessions = 0
                for h in self._release_health.values():
                    crash_sessions += max(0, h.total_sessions - h.crash_free_sessions)
                    counted_sessions += h.total_sessions
                if counted_sessions:
                    crash_free_rate = max(0.0, 1.0 - (crash_sessions / counted_sessions))

            return CrashReporterStats(
                total_reports=len(self._reports),
                new_reports=new_reports,
                triaged_reports=triaged_reports,
                resolved_reports=resolved_reports,
                total_groups=len(self._groups),
                active_groups=active_groups,
                resolved_groups=resolved_groups,
                total_sessions=total_sessions,
                crash_free_rate=crash_free_rate,
                total_events=len(self._events),
            )

    def get_status(self) -> Dict[str, Any]:
        """Return a status summary of the crash reporting subsystem.

        The ``initialized`` flag is always the first key so callers can cheaply
        verify the singleton has finished bootstrapping.
        """
        with self._lock:
            return {
                "initialized": self._initialized,
                "reports": len(self._reports),
                "groups": len(self._groups),
                "fingerprints": len(self._fingerprint_index),
                "breadcrumb_sessions": len(self._breadcrumbs),
                "release_health": len(self._release_health),
                "events": len(self._events),
                "capacities": {
                    "max_reports": _MAX_REPORTS,
                    "max_groups": _MAX_GROUPS,
                    "max_breadcrumbs": _MAX_BREADCRUMBS,
                    "max_breadcrumb_sessions": _MAX_BREADCRUMB_SESSIONS,
                    "max_events": _MAX_EVENTS,
                    "max_release_health": _MAX_RELEASE_HEALTH,
                },
            }

    def get_snapshot(self) -> CrashReporterSnapshot:
        """Capture a snapshot of the entire subsystem state."""
        with self._lock:
            snapshot = CrashReporterSnapshot(
                reports=[r.to_dict() for r in self._reports.values()],
                groups=[g.to_dict() for g in self._groups.values()],
                stats=self.get_stats().to_dict(),
                timestamp=_now(),
            )
            self._emit(CrashReporterEventKind.SNAPSHOT_TAKEN, {"reports": len(snapshot.reports)})
            return snapshot

    def reset(self) -> None:
        """Reset the subsystem to an empty state and emit a reset event."""
        with self._lock:
            self._reports.clear()
            self._groups.clear()
            self._fingerprint_index.clear()
            self._breadcrumbs.clear()
            self._release_health.clear()
            self._events.clear()
            self._emit(CrashReporterEventKind.SYSTEM_RESET, {})

    # ------------------------------------------------------------------
    # Seed data
    # ------------------------------------------------------------------

    def _seed_data(self) -> None:
        """Seed demo crash groups, reports, a breadcrumb, and release health.

        Seeds one crash group containing two reports (one fatal, one warning)
        that share a fingerprint, a breadcrumb for the first session, and a
        release health entry for build ``1.0.1``.
        """
        now = _now()
        build_version = "1.0.1"
        fingerprint = "fp_seed_npe_inv"  # stable seed fingerprint

        # --- Crash group ---
        group = CrashGroup(
            group_id="grp_seed_1",
            fingerprint=fingerprint,
            title="NullPointerException in PlayerInventory.get_items",
            message="NullPointerException: cannot access field 'items' on null PlayerInventory",
            category=ErrorCategory.NULL_POINTER,
            severity=ErrorSeverity.FATAL,
            state=ReportState.NEW,
            first_seen=now,
            last_seen=now,
            occurrence_count=2,
            affected_players={"player_seed_1", "player_seed_2"},
            affected_platforms={Platform.WINDOWS, Platform.MACOS},
            sample_report_id="rpt_seed_1",
            resolved_at="",
            resolved_by="",
            assignee="",
            fix_version="",
            tags=["seed", "inventory", "crash"],
        )
        self._groups[group.group_id] = group
        self._fingerprint_index[fingerprint] = group.group_id

        # --- Report 1: fatal crash (Windows) ---
        stack1 = [
            StackFrame(
                function_name="PlayerInventory.get_items",
                file_path="player/inventory.py",
                line_number=142,
                column_number=0,
                module_name="player.inventory",
                frame_kind=StackFrameKind.SCRIPT,
                source_snippet="return self.items",
                is_user_code=True,
            ),
            StackFrame(
                function_name="InventoryUI.render",
                file_path="ui/inventory_ui.py",
                line_number=88,
                column_number=0,
                module_name="ui.inventory_ui",
                frame_kind=StackFrameKind.SCRIPT,
                source_snippet="items = inventory.get_items()",
                is_user_code=True,
            ),
        ]
        report1 = CrashReport(
            report_id="rpt_seed_1",
            session_id="sess_seed_1",
            player_id="player_seed_1",
            build_version=build_version,
            platform=Platform.WINDOWS,
            severity=ErrorSeverity.FATAL,
            category=ErrorCategory.NULL_POINTER,
            message="NullPointerException: cannot access field 'items' on null PlayerInventory",
            stack_trace=stack1,
            breadcrumbs=[],
            context={"level": 3, "zone": "town", "frame": 12480},
            state=ReportState.NEW,
            group_id="grp_seed_1",
            created_at=now,
            fingerprint=fingerprint,
            occurrence_count=1,
            tags=["seed", "crash"],
        )
        self._reports[report1.report_id] = report1

        # --- Report 2: warning (macOS) - same fingerprint, joins the group ---
        stack2 = [
            StackFrame(
                function_name="PlayerInventory.get_items",
                file_path="player/inventory.py",
                line_number=142,
                column_number=0,
                module_name="player.inventory",
                frame_kind=StackFrameKind.SCRIPT,
                source_snippet="return self.items",
                is_user_code=True,
            ),
        ]
        report2 = CrashReport(
            report_id="rpt_seed_2",
            session_id="sess_seed_2",
            player_id="player_seed_2",
            build_version=build_version,
            platform=Platform.MACOS,
            severity=ErrorSeverity.WARNING,
            category=ErrorCategory.NULL_POINTER,
            message="NullPointerException: cannot access field 'items' on null PlayerInventory",
            stack_trace=stack2,
            breadcrumbs=[],
            context={"level": 7, "zone": "dungeon", "handled": True},
            state=ReportState.NEW,
            group_id="grp_seed_1",
            created_at=now,
            fingerprint=fingerprint,
            occurrence_count=1,
            tags=["seed", "warning"],
        )
        self._reports[report2.report_id] = report2

        # --- Breadcrumb for the first session ---
        crumb = Breadcrumb(
            timestamp=now,
            type=BreadcombType.NAVIGATION,
            message="Opened inventory screen",
            level="info",
            category="ui",
            data={"screen": "inventory", "player_id": "player_seed_1"},
        )
        self._breadcrumbs["sess_seed_1"] = [crumb]

        # --- Release health for build 1.0.1 ---
        # Stored under the build version key. The logical seed id
        # "rlz_seed_1_0_1" is referenced here for traceability; the dataclass
        # itself is keyed by build_version so get_release_health() can resolve
        # it directly.
        health = ReleaseHealth(
            build_version=build_version,
            total_sessions=0,
            crash_free_sessions=0,
            error_free_sessions=0,
            crash_rate=0.0,
            error_rate=0.0,
            top_crashing_groups=[],
            last_updated=now,
        )
        self._release_health[build_version] = health

        # Recompute release health from the seeded reports so metrics are live.
        version_reports = [r for r in self._reports.values() if r.build_version == build_version]
        sessions = {r.session_id for r in version_reports if r.session_id}
        crashed = {
            r.session_id for r in version_reports
            if r.severity == ErrorSeverity.FATAL and r.session_id
        }
        errored = {
            r.session_id for r in version_reports
            if r.severity in (ErrorSeverity.FATAL, ErrorSeverity.ERROR) and r.session_id
        }
        total = len(sessions)
        health.total_sessions = total
        health.crash_free_sessions = max(0, total - len(crashed))
        health.error_free_sessions = max(0, total - len(errored))
        health.crash_rate = (len(crashed) / total) if total else 0.0
        health.error_rate = (len(errored) / total) if total else 0.0
        health.top_crashing_groups = ["grp_seed_1"] if "grp_seed_1" in {
            r.group_id for r in version_reports if r.severity == ErrorSeverity.FATAL
        } else []


# ---------------------------------------------------------------------------
# Module-level helpers
# ---------------------------------------------------------------------------


_SEVERITY_RANK: Dict[ErrorSeverity, int] = {
    ErrorSeverity.DEBUG: 0,
    ErrorSeverity.INFO: 1,
    ErrorSeverity.WARNING: 2,
    ErrorSeverity.ERROR: 3,
    ErrorSeverity.FATAL: 4,
}


def _severity_rank(severity: ErrorSeverity) -> int:
    """Return a numeric rank for ``severity``; higher means more severe."""
    return _SEVERITY_RANK.get(severity, 0)


def get_crash_reporter_system() -> CrashReporterSystem:
    """Return the singleton ``CrashReporterSystem`` instance."""
    return CrashReporterSystem()
