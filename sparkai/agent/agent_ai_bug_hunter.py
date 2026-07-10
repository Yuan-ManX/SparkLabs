"""
SparkLabs Agent - AI Bug Hunter

An autonomous bug detection, reproduction, and classification agent for the
SparkLabs AI-native game engine. The agent ingests gameplay telemetry,
player reports, and static code analysis results, then correlates them
into structured bug reports. It runs reproduction scripts to confirm
issues, applies AI-driven severity and category classification, surfaces
duplicate reports, and emits fix suggestions.

The module embodies the AI-native principle: bugs are not passively
logged, they are actively hunted. Telemetry patterns trigger automatic
bug creation, reproduction scripts validate hypotheses, and classification
heuristics triage issues without human intervention.

Architecture:
  AIBugHunter (singleton)
    |-- BugReport, ReproductionScript, TelemetryPattern, CodeAnalysisResult,
        PlayerReport, BugHunterConfig, BugHunterStats, BugHunterSnapshot,
        BugHunterEvent
    |-- BugSeverity, BugStatus, BugCategory, DetectionSource,
        Reproducibility, FixConfidence

Core Capabilities:
  - register_bug / get_bug / list_bugs / remove_bug /
    update_bug_status / update_bug_severity / assign_bug: full bug
    lifecycle management with severity, status, and assignment tracking.
  - register_reproduction_script / get_reproduction_script /
    list_reproduction_scripts / remove_reproduction_script /
    run_reproduction: reproduction script library and simulated execution
    that updates success rates.
  - register_telemetry_pattern / get_telemetry_pattern /
    list_telemetry_patterns / remove_telemetry_pattern / scan_telemetry:
    telemetry anomaly detection that auto-creates bug reports when
    metrics cross configured thresholds.
  - register_player_report / get_player_report / list_player_reports /
    remove_player_report / link_player_report_to_bug: player-facing
    report intake and correlation to known bugs.
  - register_code_analysis / get_code_analysis / list_code_analyses /
    remove_code_analysis: static analysis result storage tied to bugs.
  - auto_classify_bug / suggest_fix / find_duplicates / get_bug_summary:
    AI-driven triage, fix recommendation, duplicate detection, and
    per-bug summarization.
  - list_events / get_stats / get_status / get_snapshot / get_config /
    set_config / tick / reset: observability, tuning, and lifecycle
    management.

The class implements the singleton pattern with double-checked locking
using ``threading.RLock``; consumers should obtain the instance through
:meth:`AIBugHunter.get_instance` or the module-level
:func:`get_ai_bug_hunter` factory.
"""

from __future__ import annotations

import random
import threading
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Module-Level Singleton Lock and Instance
# ---------------------------------------------------------------------------

_lock = threading.RLock()
_instance: Optional["AIBugHunter"] = None


# ---------------------------------------------------------------------------
# Capacity Constants
# ---------------------------------------------------------------------------

_MAX_BUGS: int = 5000
_MAX_REPRODUCTION_SCRIPTS: int = 2000
_MAX_TELEMETRY_PATTERNS: int = 1000
_MAX_PLAYER_REPORTS: int = 5000
_MAX_CODE_ANALYSES: int = 3000
_MAX_EVENTS: int = 8000


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


def _safe_int(value: Any, default: int = 0) -> int:
    if value is None or value == "":
        return default
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _safe_float(value: Any, default: float = 0.0) -> float:
    if value is None or value == "":
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    if value < low:
        return low
    if value > high:
        return high
    return value


def _tokenize(text: str) -> List[str]:
    """Split free text into lowercase word tokens for similarity scoring."""
    if not text:
        return []
    tokens: List[str] = []
    current = []
    for ch in text.lower():
        if ch.isalnum():
            current.append(ch)
        else:
            if current:
                tokens.append("".join(current))
                current = []
    if current:
        tokens.append("".join(current))
    return tokens


# ---------------------------------------------------------------------------
# Domain Enums
# ---------------------------------------------------------------------------


class BugSeverity(str, Enum):
    """Severity tier assigned to a bug report."""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    TRIVIAL = "trivial"
    INFO = "info"


class BugStatus(str, Enum):
    """Lifecycle state of a bug report."""

    DETECTED = "detected"
    INVESTIGATING = "investigating"
    REPRODUCED = "reproduced"
    CONFIRMED = "confirmed"
    FIXING = "fixing"
    FIXED = "fixed"
    WONT_FIX = "wont_fix"
    DUPLICATE = "duplicate"


class BugCategory(str, Enum):
    """Functional area a bug belongs to."""

    CRASH = "crash"
    GRAPHICS = "graphics"
    GAMEPLAY = "gameplay"
    NETWORK = "network"
    PERFORMANCE = "performance"
    AUDIO = "audio"
    UI = "ui"
    LOGIC = "logic"
    MEMORY = "memory"
    SECURITY = "security"
    INPUT = "input"
    AI_BEHAVIOR = "ai_behavior"
    PHYSICS = "physics"
    SAVE_SYSTEM = "save_system"
    PROGRESSION = "progression"


class DetectionSource(str, Enum):
    """Origin of a bug detection event."""

    TELEMETRY = "telemetry"
    PLAYER_REPORT = "player_report"
    AUTOMATED_TEST = "automated_test"
    CODE_ANALYSIS = "code_analysis"
    AI_INFERENCE = "ai_inference"
    REGRESSION_CHECK = "regression_check"


class Reproducibility(str, Enum):
    """How reliably a bug can be reproduced."""

    ALWAYS = "always"
    SOMETIMES = "sometimes"
    RARE = "rare"
    UNABLE_TO_REPRODUCE = "unable_to_reproduce"


class FixConfidence(str, Enum):
    """Confidence level of a suggested fix."""

    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    NONE = "none"


# ---------------------------------------------------------------------------
# Data Classes
# ---------------------------------------------------------------------------


@dataclass
class BugReport:
    """A structured bug report tracked by the hunter."""

    bug_id: str = field(default_factory=lambda: _new_id("bug"))
    title: str = ""
    description: str = ""
    severity: str = BugSeverity.MEDIUM.value
    status: str = BugStatus.DETECTED.value
    category: str = BugCategory.GAMEPLAY.value
    detection_source: str = DetectionSource.TELEMETRY.value
    reproducibility: str = Reproducibility.SOMETIMES.value
    first_seen: str = field(default_factory=_now)
    last_seen: str = field(default_factory=_now)
    occurrence_count: int = 1
    affected_versions: List[str] = field(default_factory=list)
    affected_platforms: List[str] = field(default_factory=list)
    stack_trace: str = ""
    reproduction_steps: List[str] = field(default_factory=list)
    expected_behavior: str = ""
    actual_behavior: str = ""
    suggested_fix: str = ""
    fix_confidence: str = FixConfidence.NONE.value
    reporter_id: str = ""
    assignee_id: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class ReproductionScript:
    """A scripted sequence that attempts to reproduce a known bug."""

    script_id: str = field(default_factory=lambda: _new_id("repro"))
    bug_id: str = ""
    steps: List[str] = field(default_factory=list)
    preconditions: str = ""
    input_sequence: str = ""
    expected_result: str = ""
    actual_result: str = ""
    success_rate: float = 0.0
    last_run: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class TelemetryPattern:
    """A metric anomaly pattern that auto-creates bug reports."""

    pattern_id: str = field(default_factory=lambda: _new_id("pat"))
    name: str = ""
    description: str = ""
    metric_name: str = ""
    condition: str = ">"
    threshold: float = 0.0
    window_size: int = 60
    bug_category: str = BugCategory.GAMEPLAY.value
    confidence_score: float = 0.5
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class CodeAnalysisResult:
    """A static code analysis finding linked to a bug."""

    analysis_id: str = field(default_factory=lambda: _new_id("ca"))
    bug_id: str = ""
    file_path: str = ""
    line_start: int = 0
    line_end: int = 0
    issue_type: str = ""
    issue_description: str = ""
    code_snippet: str = ""
    suggested_fix: str = ""
    confidence: str = FixConfidence.MEDIUM.value
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class PlayerReport:
    """A bug report submitted by a player."""

    report_id: str = field(default_factory=lambda: _new_id("rpt"))
    player_id: str = ""
    bug_id: str = ""
    title: str = ""
    description: str = ""
    timestamp: str = field(default_factory=_now)
    game_version: str = ""
    platform: str = ""
    session_id: str = ""
    reproduction_steps: List[str] = field(default_factory=list)
    severity_assessment: str = BugSeverity.MEDIUM.value
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class BugHunterConfig:
    """Runtime configuration for the bug hunter."""

    max_bugs: int = 5000
    max_reproduction_scripts: int = 2000
    max_telemetry_patterns: int = 1000
    max_player_reports: int = 5000
    auto_classify_enabled: bool = True
    auto_reproduce_enabled: bool = False
    telemetry_scan_interval: int = 60
    confidence_threshold: float = 0.6
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class BugHunterStats:
    """Aggregate counters for the bug hunter."""

    total_bugs: int = 0
    critical_bugs: int = 0
    high_bugs: int = 0
    medium_bugs: int = 0
    low_bugs: int = 0
    fixed_bugs: int = 0
    total_reproductions: int = 0
    total_player_reports: int = 0
    total_telemetry_patterns: int = 0
    tick_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class BugHunterSnapshot:
    """A point-in-time capture of bug hunter state."""

    timestamp: str = field(default_factory=_now)
    bugs: List[Dict[str, Any]] = field(default_factory=list)
    reproduction_scripts: List[Dict[str, Any]] = field(default_factory=list)
    telemetry_patterns: List[Dict[str, Any]] = field(default_factory=list)
    player_reports: List[Dict[str, Any]] = field(default_factory=list)
    code_analyses: List[Dict[str, Any]] = field(default_factory=list)
    stats: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class BugHunterEvent:
    """An audit event emitted by the bug hunter."""

    event_id: str = field(default_factory=lambda: _new_id("evt"))
    event_type: str = ""
    timestamp: str = field(default_factory=_now)
    bug_id: str = ""
    data: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


# ---------------------------------------------------------------------------
# Static Classification Heuristics
# ---------------------------------------------------------------------------

# Maps keyword fragments to (category, severity). The first matching
# keyword set wins, so order matters: the most specific patterns come first.
_CLASSIFICATION_RULES: List[Tuple[List[str], str, str]] = [
    (["crash", "segfault", "seg fault", "null pointer", "nullptr",
      "null ref", "sigsegv", "access violation", "fatal"],
     BugCategory.CRASH.value, BugSeverity.CRITICAL.value),
    (["memory leak", "out of memory", "oom", "heap exhausted",
      "allocation failed", "bad_alloc"],
     BugCategory.MEMORY.value, BugSeverity.CRITICAL.value),
    (["save corrupt", "save file", "corrupt save", "save lost",
      "load fail"],
     BugCategory.SAVE_SYSTEM.value, BugSeverity.CRITICAL.value),
    (["desync", "desynchronize", "network timeout", "connection reset",
      "latency spike", "packet loss", "disconnect"],
     BugCategory.NETWORK.value, BugSeverity.HIGH.value),
    (["fps drop", "frame rate", "stutter", "lag spike", "low fps",
      "performance drop", "frame time", "hitch"],
     BugCategory.PERFORMANCE.value, BugSeverity.HIGH.value),
    (["ai stuck", "pathfinding", "navmesh", "npc stuck", "ai loop",
      "behavior tree", "decision loop", "npc frozen"],
     BugCategory.AI_BEHAVIOR.value, BugSeverity.HIGH.value),
    (["texture flicker", "texture", "flicker", "shader", "render",
      "z-fighting", "artifact", "gpu error", "vulkan", "opengl"],
     BugCategory.GRAPHICS.value, BugSeverity.MEDIUM.value),
    (["input lag", "input delay", "input latency", "controller",
      "keypress", "button unresponsive"],
     BugCategory.INPUT.value, BugSeverity.MEDIUM.value),
    (["physics", "collision", "rigidbody", "clipping", "tunneling"],
     BugCategory.PHYSICS.value, BugSeverity.MEDIUM.value),
    (["audio", "sound", "audio glitch", "audio drop", "volume"],
     BugCategory.AUDIO.value, BugSeverity.LOW.value),
    (["ui overlap", "ui", "menu", "button", "hud", "tooltip",
      "interface", "panel"],
     BugCategory.UI.value, BugSeverity.LOW.value),
    (["progression", "quest blocked", "achievement", "xp", "level up",
      "skill point"],
     BugCategory.PROGRESSION.value, BugSeverity.MEDIUM.value),
    (["security", "exploit", "cheat", "injection", "overflow"],
     BugCategory.SECURITY.value, BugSeverity.CRITICAL.value),
    (["logic", "wrong value", "incorrect", "calculation"],
     BugCategory.LOGIC.value, BugSeverity.MEDIUM.value),
    (["gameplay", "mechanic", "rule", "balance"],
     BugCategory.GAMEPLAY.value, BugSeverity.MEDIUM.value),
    (["typo", "spelling", "grammar", "label"],
     BugCategory.UI.value, BugSeverity.TRIVIAL.value),
]

# Suggested fix text keyed by bug category.
_FIX_SUGGESTIONS: Dict[str, str] = {
    BugCategory.CRASH.value: (
        "Inspect the stack trace for the failing frame. Add null guards "
        "around the accessed pointer, validate object lifetime before "
        "access, and add a regression test that reproduces the call path."
    ),
    BugCategory.MEMORY.value: (
        "Run the build under an address sanitizer or leak detector. Audit "
        "resource acquisition and release pairs, ensure every allocation "
        "has a matching free, and add a teardown test that asserts stable "
        "heap usage across repeated sessions."
    ),
    BugCategory.SAVE_SYSTEM.value: (
        "Introduce atomic save writes with a temporary file and rename "
        "operation. Validate the save schema on load, keep a backup of the "
        "previous save, and add a migration path for version upgrades."
    ),
    BugCategory.NETWORK.value: (
        "Add client-side prediction and server reconciliation. Increase "
        "snapshot interpolation buffering, validate sequence numbers, and "
        "log desync deltas to isolate the divergent state."
    ),
    BugCategory.PERFORMANCE.value: (
        "Profile the affected frame with a CPU and GPU tracer. Batch draw "
        "calls, cache expensive computations, reduce overdraw, and consider "
        "level-of-life streaming for dense scenes."
    ),
    BugCategory.AI_BEHAVIOR.value: (
        "Add a fallback pathfinding query when the primary navmesh request "
        "fails or stalls. Cap decision-tree iteration depth, log stuck "
        "agents, and inject a recovery behavior after a timeout."
    ),
    BugCategory.GRAPHICS.value: (
        "Verify texture streaming priorities and mip availability. Clamp "
        "depth bias to avoid z-fighting, validate shader permutations, and "
        "reproduce under the lowest supported graphics preset."
    ),
    BugCategory.INPUT.value: (
        "Measure input-to-frame latency with a hardware tracer. Decouple "
        "input sampling from the render loop, buffer input events, and "
        "ensure the input thread is not starved by heavy effects."
    ),
    BugCategory.PHYSICS.value: (
        "Tighten the fixed timestep, enable continuous collision detection "
        "for fast-moving bodies, and validate rigidbody sleeping thresholds "
        "to prevent tunneling."
    ),
    BugCategory.AUDIO.value: (
        "Check audio source pooling and voice stealing logic. Validate "
        "volume curves, ensure 3D positional sources update each frame, and "
        "log dropped audio frames."
    ),
    BugCategory.UI.value: (
        "Add a layout pass that clamps panels to the safe area. Validate "
        "anchor settings at low resolutions, and add a regression test "
        "across a matrix of aspect ratios."
    ),
    BugCategory.LOGIC.value: (
        "Add unit tests covering the calculation branch. Validate inputs "
        "against expected ranges, log the computed values, and assert the "
        "corrected formula in isolation."
    ),
    BugCategory.SECURITY.value: (
        "Sanitize all untrusted input. Add bounds checks, use parameterized "
        "queries, and audit the call path for injection vectors. Add a "
        "fuzz test that exercises the entry point."
    ),
    BugCategory.PROGRESSION.value: (
        "Validate quest state transitions against the progression graph. "
        "Add guards that prevent skipping prerequisites, and log the "
        "reward grant path for audit."
    ),
    BugCategory.GAMEPLAY.value: (
        "Reproduce the mechanic in isolation. Tune the balance constants, "
        "add telemetry for the affected interaction, and validate against "
        "the design specification."
    ),
}

# Comparison operators supported by telemetry pattern conditions.
_CONDITION_OPS: Dict[str, Any] = {
    ">": lambda a, b: a > b,
    "<": lambda a, b: a < b,
    ">=": lambda a, b: a >= b,
    "<=": lambda a, b: a <= b,
    "==": lambda a, b: a == b,
    "!=": lambda a, b: a != b,
}


# ---------------------------------------------------------------------------
# AI Bug Hunter Singleton
# ---------------------------------------------------------------------------


class AIBugHunter:
    """Singleton agent that hunts, reproduces, and classifies bugs.

    The hunter maintains bug reports, reproduction scripts, telemetry
    patterns, player reports, and code analysis results. It correlates
    telemetry anomalies into new bug reports, runs reproduction scripts
    to validate hypotheses, applies heuristic classification, detects
    duplicates, and emits fix suggestions.

    All mutations are guarded by a reentrant lock so the hunter is safe
    to call from multiple threads.
    """

    _init_lock = threading.RLock()

    # ------------------------------------------------------------------
    # Construction and Singleton
    # ------------------------------------------------------------------

    def __init__(self) -> None:
        self._bugs: Dict[str, BugReport] = {}
        self._reproduction_scripts: Dict[str, ReproductionScript] = {}
        self._telemetry_patterns: Dict[str, TelemetryPattern] = {}
        self._player_reports: Dict[str, PlayerReport] = {}
        self._code_analyses: Dict[str, CodeAnalysisResult] = {}
        self._events: List[BugHunterEvent] = []
        self._config = BugHunterConfig()
        self._stats = BugHunterStats()
        self._tick_count: int = 0
        self._reproduction_runs: int = 0
        self._telemetry_scans: int = 0
        self._initialized: bool = False
        self._seed()

    @classmethod
    def get_instance(cls) -> "AIBugHunter":
        global _instance
        if _instance is None:
            with _lock:
                if _instance is None:
                    _instance = cls()
        return _instance

    # ------------------------------------------------------------------
    # Internal Helpers
    # ------------------------------------------------------------------

    def _emit(self, event_type: str, bug_id: str = "",
              data: Optional[Dict[str, Any]] = None) -> None:
        event = BugHunterEvent(
            event_id=_new_id("evt"),
            event_type=event_type,
            timestamp=_now(),
            bug_id=bug_id,
            data=data or {},
        )
        self._events.append(event)
        _evict_fifo_list(self._events, _MAX_EVENTS)

    def _refresh_stats(self) -> None:
        self._stats.total_bugs = len(self._bugs)
        self._stats.critical_bugs = sum(
            1 for b in self._bugs.values()
            if b.severity == BugSeverity.CRITICAL.value
        )
        self._stats.high_bugs = sum(
            1 for b in self._bugs.values()
            if b.severity == BugSeverity.HIGH.value
        )
        self._stats.medium_bugs = sum(
            1 for b in self._bugs.values()
            if b.severity == BugSeverity.MEDIUM.value
        )
        self._stats.low_bugs = sum(
            1 for b in self._bugs.values()
            if b.severity in (BugSeverity.LOW.value,
                              BugSeverity.TRIVIAL.value,
                              BugSeverity.INFO.value)
        )
        self._stats.fixed_bugs = sum(
            1 for b in self._bugs.values()
            if b.status == BugStatus.FIXED.value
        )
        self._stats.total_reproductions = self._reproduction_runs
        self._stats.total_player_reports = len(self._player_reports)
        self._stats.total_telemetry_patterns = len(self._telemetry_patterns)
        self._stats.tick_count = self._tick_count

    def _classify_text(self, text: str) -> Tuple[str, str]:
        """Return (category, severity) inferred from free text."""
        lowered = (text or "").lower()
        for keywords, category, severity in _CLASSIFICATION_RULES:
            for kw in keywords:
                if kw in lowered:
                    return category, severity
        return BugCategory.GAMEPLAY.value, BugSeverity.MEDIUM.value

    # ------------------------------------------------------------------
    # Bug Lifecycle
    # ------------------------------------------------------------------

    def register_bug(
        self,
        bug_id: str = "",
        title: str = "",
        description: str = "",
        severity: str = BugSeverity.MEDIUM.value,
        category: str = BugCategory.GAMEPLAY.value,
        detection_source: str = DetectionSource.TELEMETRY.value,
        reproducibility: str = Reproducibility.SOMETIMES.value,
        affected_versions: Optional[List[str]] = None,
        affected_platforms: Optional[List[str]] = None,
        stack_trace: str = "",
        reproduction_steps: Optional[List[str]] = None,
        expected_behavior: str = "",
        actual_behavior: str = "",
        suggested_fix: str = "",
        fix_confidence: str = FixConfidence.NONE.value,
        reporter_id: str = "",
        assignee_id: str = "",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Tuple[bool, str, Optional[BugReport]]:
        """Register a new bug report."""
        with _lock:
            bid = bug_id or _new_id("bug")
            if bid in self._bugs:
                return False, f"bug_already_exists:{bid}", None
            sev = _coerce_enum(BugSeverity, severity, BugSeverity.MEDIUM)
            cat = _coerce_enum(BugCategory, category, BugCategory.GAMEPLAY)
            src = _coerce_enum(DetectionSource, detection_source,
                               DetectionSource.TELEMETRY)
            repro = _coerce_enum(Reproducibility, reproducibility,
                                 Reproducibility.SOMETIMES)
            conf = _coerce_enum(FixConfidence, fix_confidence,
                                FixConfidence.NONE)
            now = _now()
            bug = BugReport(
                bug_id=bid,
                title=title,
                description=description,
                severity=sev.value if isinstance(sev, Enum) else sev,
                status=BugStatus.DETECTED.value,
                category=cat.value if isinstance(cat, Enum) else cat,
                detection_source=src.value if isinstance(src, Enum) else src,
                reproducibility=(repro.value if isinstance(repro, Enum)
                                 else repro),
                first_seen=now,
                last_seen=now,
                occurrence_count=1,
                affected_versions=list(affected_versions or []),
                affected_platforms=list(affected_platforms or []),
                stack_trace=stack_trace,
                reproduction_steps=list(reproduction_steps or []),
                expected_behavior=expected_behavior,
                actual_behavior=actual_behavior,
                suggested_fix=suggested_fix,
                fix_confidence=(conf.value if isinstance(conf, Enum)
                                else conf),
                reporter_id=reporter_id,
                assignee_id=assignee_id,
                metadata=dict(metadata or {}),
            )
            self._bugs[bid] = bug
            _evict_fifo_dict(self._bugs, self._config.max_bugs)
            self._emit("bug_registered", bug_id=bid, data={
                "title": title,
                "severity": bug.severity,
                "category": bug.category,
            })
            return True, "success", bug

    def get_bug(self, bug_id: str) -> Optional[BugReport]:
        with _lock:
            return self._bugs.get(bug_id)

    def list_bugs(
        self,
        severity_filter: str = "",
        status_filter: str = "",
        category_filter: str = "",
    ) -> List[BugReport]:
        with _lock:
            sev = _coerce_enum(BugSeverity, severity_filter, None)
            stat = _coerce_enum(BugStatus, status_filter, None)
            cat = _coerce_enum(BugCategory, category_filter, None)
            results: List[BugReport] = []
            for bug in self._bugs.values():
                if sev is not None and bug.severity != sev.value:
                    continue
                if stat is not None and bug.status != stat.value:
                    continue
                if cat is not None and bug.category != cat.value:
                    continue
                results.append(bug)
            results.sort(key=lambda b: b.last_seen, reverse=True)
            return results

    def remove_bug(self, bug_id: str) -> Tuple[bool, str]:
        with _lock:
            existed = self._bugs.pop(bug_id, None) is not None
            if existed:
                self._emit("bug_removed", bug_id=bug_id)
                return True, "removed"
            return False, "not_found"

    def update_bug_status(
        self, bug_id: str, status: str,
    ) -> Tuple[bool, str, Optional[BugReport]]:
        with _lock:
            bug = self._bugs.get(bug_id)
            if bug is None:
                return False, "not_found", None
            stat = _coerce_enum(BugStatus, status, None)
            if stat is None:
                return False, f"invalid_status:{status}", None
            bug.status = stat.value
            bug.last_seen = _now()
            self._emit("bug_status_updated", bug_id=bug_id, data={
                "status": bug.status,
            })
            return True, "updated", bug

    def update_bug_severity(
        self, bug_id: str, severity: str,
    ) -> Tuple[bool, str, Optional[BugReport]]:
        with _lock:
            bug = self._bugs.get(bug_id)
            if bug is None:
                return False, "not_found", None
            sev = _coerce_enum(BugSeverity, severity, None)
            if sev is None:
                return False, f"invalid_severity:{severity}", None
            bug.severity = sev.value
            bug.last_seen = _now()
            self._emit("bug_severity_updated", bug_id=bug_id, data={
                "severity": bug.severity,
            })
            return True, "updated", bug

    def assign_bug(
        self, bug_id: str, assignee_id: str,
    ) -> Tuple[bool, str, Optional[BugReport]]:
        with _lock:
            bug = self._bugs.get(bug_id)
            if bug is None:
                return False, "not_found", None
            bug.assignee_id = assignee_id
            bug.last_seen = _now()
            self._emit("bug_assigned", bug_id=bug_id, data={
                "assignee_id": assignee_id,
            })
            return True, "assigned", bug

    # ------------------------------------------------------------------
    # Reproduction Scripts
    # ------------------------------------------------------------------

    def register_reproduction_script(
        self,
        script_id: str = "",
        bug_id: str = "",
        steps: Optional[List[str]] = None,
        preconditions: str = "",
        input_sequence: str = "",
        expected_result: str = "",
        actual_result: str = "",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Tuple[bool, str, Optional[ReproductionScript]]:
        with _lock:
            sid = script_id or _new_id("repro")
            if sid in self._reproduction_scripts:
                return False, f"script_already_exists:{sid}", None
            script = ReproductionScript(
                script_id=sid,
                bug_id=bug_id,
                steps=list(steps or []),
                preconditions=preconditions,
                input_sequence=input_sequence,
                expected_result=expected_result,
                actual_result=actual_result,
                success_rate=0.0,
                last_run="",
                metadata=dict(metadata or {}),
            )
            self._reproduction_scripts[sid] = script
            _evict_fifo_dict(self._reproduction_scripts,
                             self._config.max_reproduction_scripts)
            self._emit("reproduction_script_registered", bug_id=bug_id, data={
                "script_id": sid,
            })
            return True, "success", script

    def get_reproduction_script(
        self, script_id: str,
    ) -> Optional[ReproductionScript]:
        with _lock:
            return self._reproduction_scripts.get(script_id)

    def list_reproduction_scripts(self, bug_id: str) -> List[ReproductionScript]:
        with _lock:
            if not bug_id:
                return list(self._reproduction_scripts.values())
            return [
                s for s in self._reproduction_scripts.values()
                if s.bug_id == bug_id
            ]

    def remove_reproduction_script(self, script_id: str) -> Tuple[bool, str]:
        with _lock:
            existed = self._reproduction_scripts.pop(script_id, None) is not None
            if existed:
                self._emit("reproduction_script_removed", data={
                    "script_id": script_id,
                })
                return True, "removed"
            return False, "not_found"

    def run_reproduction(
        self, script_id: str,
    ) -> Tuple[bool, str, Optional[ReproductionScript]]:
        """Simulate running a reproduction script and update its success rate."""
        with _lock:
            script = self._reproduction_scripts.get(script_id)
            if script is None:
                return False, "not_found", None
            self._reproduction_runs += 1
            # Simulate reproduction outcome. Scripts tied to a reproduced
            # or confirmed bug succeed more often than unverified ones.
            base_success = 0.4
            bug = self._bugs.get(script.bug_id)
            if bug is not None:
                if bug.status in (BugStatus.REPRODUCED.value,
                                  BugStatus.CONFIRMED.value):
                    base_success = 0.85
                elif bug.status == BugStatus.DETECTED.value:
                    base_success = 0.35
                elif bug.status == BugStatus.FIXED.value:
                    base_success = 0.1
            succeeded = random.random() < base_success
            # Exponential moving average of the success rate.
            alpha = 0.3
            outcome = 1.0 if succeeded else 0.0
            script.success_rate = round(
                (alpha * outcome) + ((1.0 - alpha) * script.success_rate), 4,
            )
            script.last_run = _now()
            if succeeded:
                script.actual_result = script.expected_result or "reproduced"
                message = "reproduced"
            else:
                script.actual_result = "unable_to_reproduce_on_this_run"
                message = "not_reproduced"
            self._emit("reproduction_run", bug_id=script.bug_id, data={
                "script_id": script_id,
                "succeeded": succeeded,
                "success_rate": script.success_rate,
            })
            # If the reproduction succeeds and the bug is still only
            # detected, promote it to investigating for triage.
            if succeeded and bug is not None:
                if bug.status == BugStatus.DETECTED.value:
                    bug.status = BugStatus.INVESTIGATING.value
                    bug.last_seen = _now()
                    self._emit("bug_status_updated", bug_id=bug.bug_id, data={
                        "status": bug.status,
                        "reason": "reproduction_succeeded",
                    })
            return True, message, script

    # ------------------------------------------------------------------
    # Telemetry Patterns
    # ------------------------------------------------------------------

    def register_telemetry_pattern(
        self,
        pattern_id: str = "",
        name: str = "",
        description: str = "",
        metric_name: str = "",
        condition: str = ">",
        threshold: float = 0.0,
        window_size: int = 60,
        bug_category: str = BugCategory.GAMEPLAY.value,
        confidence_score: float = 0.5,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Tuple[bool, str, Optional[TelemetryPattern]]:
        with _lock:
            pid = pattern_id or _new_id("pat")
            if pid in self._telemetry_patterns:
                return False, f"pattern_already_exists:{pid}", None
            if condition not in _CONDITION_OPS:
                return False, f"invalid_condition:{condition}", None
            cat = _coerce_enum(BugCategory, bug_category, BugCategory.GAMEPLAY)
            pattern = TelemetryPattern(
                pattern_id=pid,
                name=name,
                description=description,
                metric_name=metric_name,
                condition=condition,
                threshold=_safe_float(threshold, 0.0),
                window_size=max(1, _safe_int(window_size, 60)),
                bug_category=cat.value if isinstance(cat, Enum) else cat,
                confidence_score=_clamp(_safe_float(confidence_score, 0.5),
                                        0.0, 1.0),
                metadata=dict(metadata or {}),
            )
            self._telemetry_patterns[pid] = pattern
            _evict_fifo_dict(self._telemetry_patterns,
                             self._config.max_telemetry_patterns)
            self._emit("telemetry_pattern_registered", data={
                "pattern_id": pid,
                "metric_name": metric_name,
            })
            return True, "success", pattern

    def get_telemetry_pattern(
        self, pattern_id: str,
    ) -> Optional[TelemetryPattern]:
        with _lock:
            return self._telemetry_patterns.get(pattern_id)

    def list_telemetry_patterns(self) -> List[TelemetryPattern]:
        with _lock:
            return list(self._telemetry_patterns.values())

    def remove_telemetry_pattern(self, pattern_id: str) -> Tuple[bool, str]:
        with _lock:
            existed = self._telemetry_patterns.pop(pattern_id, None) is not None
            if existed:
                self._emit("telemetry_pattern_removed", data={
                    "pattern_id": pattern_id,
                })
                return True, "removed"
            return False, "not_found"

    def scan_telemetry(
        self, metrics_data: Dict[str, Any],
    ) -> Tuple[bool, str, List[BugReport]]:
        """Analyze telemetry metrics against registered patterns.

        For each pattern whose metric breaches its threshold, a new bug
        report is created (unless an open bug already exists for the same
        pattern). Returns the list of newly created bug reports.
        """
        with _lock:
            if not isinstance(metrics_data, dict):
                return False, "invalid_metrics_data", []
            self._telemetry_scans += 1
            created: List[BugReport] = []
            for pattern in list(self._telemetry_patterns.values()):
                metric_value = metrics_data.get(pattern.metric_name)
                if metric_value is None:
                    continue
                try:
                    value = float(metric_value)
                except (TypeError, ValueError):
                    continue
                op = _CONDITION_OPS.get(pattern.condition)
                if op is None:
                    continue
                if not op(value, pattern.threshold):
                    continue
                # Skip if an open bug already tracks this pattern.
                already_tracked = False
                for bug in self._bugs.values():
                    if bug.metadata.get("pattern_id") == pattern.pattern_id \
                            and bug.status not in (BugStatus.FIXED.value,
                                                   BugStatus.WONT_FIX.value):
                        already_tracked = True
                        # Bump occurrence count and last_seen for the
                        # existing bug so recurrence is visible.
                        bug.occurrence_count += 1
                        bug.last_seen = _now()
                        break
                if already_tracked:
                    continue
                severity = BugSeverity.HIGH.value
                if pattern.confidence_score >= self._config.confidence_threshold:
                    severity = BugSeverity.CRITICAL.value
                elif pattern.confidence_score < 0.3:
                    severity = BugSeverity.MEDIUM.value
                bid = _new_id("bug")
                bug = BugReport(
                    bug_id=bid,
                    title=f"Telemetry anomaly: {pattern.name}",
                    description=(
                        f"Metric '{pattern.metric_name}' value {value} "
                        f"{pattern.condition} threshold {pattern.threshold} "
                        f"over a {pattern.window_size}s window. "
                        f"{pattern.description}"
                    ),
                    severity=severity,
                    status=BugStatus.DETECTED.value,
                    category=pattern.bug_category,
                    detection_source=DetectionSource.TELEMETRY.value,
                    reproducibility=Reproducibility.SOMETIMES.value,
                    occurrence_count=1,
                    metadata={
                        "pattern_id": pattern.pattern_id,
                        "metric_value": value,
                        "threshold": pattern.threshold,
                        "confidence_score": pattern.confidence_score,
                    },
                )
                self._bugs[bid] = bug
                _evict_fifo_dict(self._bugs, self._config.max_bugs)
                self._emit("bug_registered", bug_id=bid, data={
                    "title": bug.title,
                    "source": "telemetry_scan",
                    "pattern_id": pattern.pattern_id,
                })
                created.append(bug)
            self._emit("telemetry_scan_completed", data={
                "patterns_evaluated": len(self._telemetry_patterns),
                "bugs_created": len(created),
            })
            return True, "scanned", created

    # ------------------------------------------------------------------
    # Player Reports
    # ------------------------------------------------------------------

    def register_player_report(
        self,
        report_id: str = "",
        player_id: str = "",
        title: str = "",
        description: str = "",
        game_version: str = "",
        platform: str = "",
        session_id: str = "",
        reproduction_steps: Optional[List[str]] = None,
        severity_assessment: str = BugSeverity.MEDIUM.value,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Tuple[bool, str, Optional[PlayerReport]]:
        with _lock:
            rid = report_id or _new_id("rpt")
            if rid in self._player_reports:
                return False, f"report_already_exists:{rid}", None
            sev = _coerce_enum(BugSeverity, severity_assessment,
                               BugSeverity.MEDIUM)
            report = PlayerReport(
                report_id=rid,
                player_id=player_id,
                bug_id="",
                title=title,
                description=description,
                timestamp=_now(),
                game_version=game_version,
                platform=platform,
                session_id=session_id,
                reproduction_steps=list(reproduction_steps or []),
                severity_assessment=(sev.value if isinstance(sev, Enum)
                                     else sev),
                metadata=dict(metadata or {}),
            )
            self._player_reports[rid] = report
            _evict_fifo_dict(self._player_reports,
                             self._config.max_player_reports)
            self._emit("player_report_registered", data={
                "report_id": rid,
                "player_id": player_id,
            })
            return True, "success", report

    def get_player_report(self, report_id: str) -> Optional[PlayerReport]:
        with _lock:
            return self._player_reports.get(report_id)

    def list_player_reports(self, bug_id: str = "") -> List[PlayerReport]:
        with _lock:
            if not bug_id:
                return list(self._player_reports.values())
            return [
                r for r in self._player_reports.values()
                if r.bug_id == bug_id
            ]

    def remove_player_report(self, report_id: str) -> Tuple[bool, str]:
        with _lock:
            existed = self._player_reports.pop(report_id, None) is not None
            if existed:
                self._emit("player_report_removed", data={
                    "report_id": report_id,
                })
                return True, "removed"
            return False, "not_found"

    def link_player_report_to_bug(
        self, report_id: str, bug_id: str,
    ) -> Tuple[bool, str, Optional[PlayerReport]]:
        with _lock:
            report = self._player_reports.get(report_id)
            if report is None:
                return False, "report_not_found", None
            if bug_id not in self._bugs:
                return False, "bug_not_found", None
            report.bug_id = bug_id
            self._emit("player_report_linked", bug_id=bug_id, data={
                "report_id": report_id,
            })
            return True, "linked", report

    # ------------------------------------------------------------------
    # Code Analysis
    # ------------------------------------------------------------------

    def register_code_analysis(
        self,
        analysis_id: str = "",
        bug_id: str = "",
        file_path: str = "",
        line_start: int = 0,
        line_end: int = 0,
        issue_type: str = "",
        issue_description: str = "",
        code_snippet: str = "",
        suggested_fix: str = "",
        confidence: str = FixConfidence.MEDIUM.value,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Tuple[bool, str, Optional[CodeAnalysisResult]]:
        with _lock:
            aid = analysis_id or _new_id("ca")
            if aid in self._code_analyses:
                return False, f"analysis_already_exists:{aid}", None
            conf = _coerce_enum(FixConfidence, confidence,
                                FixConfidence.MEDIUM)
            ls = max(0, _safe_int(line_start, 0))
            le = max(ls, _safe_int(line_end, ls))
            analysis = CodeAnalysisResult(
                analysis_id=aid,
                bug_id=bug_id,
                file_path=file_path,
                line_start=ls,
                line_end=le,
                issue_type=issue_type,
                issue_description=issue_description,
                code_snippet=code_snippet,
                suggested_fix=suggested_fix,
                confidence=conf.value if isinstance(conf, Enum) else conf,
                metadata=dict(metadata or {}),
            )
            self._code_analyses[aid] = analysis
            _evict_fifo_dict(self._code_analyses, _MAX_CODE_ANALYSES)
            self._emit("code_analysis_registered", bug_id=bug_id, data={
                "analysis_id": aid,
                "file_path": file_path,
            })
            # Attach the suggested fix to the linked bug if it has none.
            bug = self._bugs.get(bug_id)
            if bug is not None and suggested_fix and not bug.suggested_fix:
                bug.suggested_fix = suggested_fix
                bug.fix_confidence = analysis.confidence
            return True, "success", analysis

    def get_code_analysis(
        self, analysis_id: str,
    ) -> Optional[CodeAnalysisResult]:
        with _lock:
            return self._code_analyses.get(analysis_id)

    def list_code_analyses(self, bug_id: str) -> List[CodeAnalysisResult]:
        with _lock:
            if not bug_id:
                return list(self._code_analyses.values())
            return [
                a for a in self._code_analyses.values()
                if a.bug_id == bug_id
            ]

    def remove_code_analysis(self, analysis_id: str) -> Tuple[bool, str]:
        with _lock:
            existed = self._code_analyses.pop(analysis_id, None) is not None
            if existed:
                self._emit("code_analysis_removed", data={
                    "analysis_id": analysis_id,
                })
                return True, "removed"
            return False, "not_found"

    # ------------------------------------------------------------------
    # AI-Driven Triage
    # ------------------------------------------------------------------

    def auto_classify_bug(
        self, bug_id: str,
    ) -> Tuple[bool, str, Optional[BugReport]]:
        """Apply heuristic classification to a bug's severity and category."""
        with _lock:
            bug = self._bugs.get(bug_id)
            if bug is None:
                return False, "not_found", None
            combined = " ".join([
                bug.title,
                bug.description,
                bug.stack_trace,
                bug.actual_behavior,
                " ".join(bug.reproduction_steps),
            ])
            category, severity = self._classify_text(combined)
            bug.category = category
            bug.severity = severity
            bug.last_seen = _now()
            # Mark that classification came from inference.
            bug.metadata["auto_classified"] = True
            bug.metadata["classification_source"] = \
                DetectionSource.AI_INFERENCE.value
            self._emit("bug_auto_classified", bug_id=bug_id, data={
                "category": category,
                "severity": severity,
            })
            return True, "classified", bug

    def suggest_fix(self, bug_id: str) -> Tuple[bool, str, str]:
        """Return a suggested fix string for the given bug."""
        with _lock:
            bug = self._bugs.get(bug_id)
            if bug is None:
                return False, "not_found", ""
            # Prefer an existing code analysis suggestion when present.
            for analysis in self._code_analyses.values():
                if analysis.bug_id == bug_id and analysis.suggested_fix:
                    bug.suggested_fix = analysis.suggested_fix
                    bug.fix_confidence = analysis.confidence
                    self._emit("fix_suggested", bug_id=bug_id, data={
                        "source": "code_analysis",
                        "analysis_id": analysis.analysis_id,
                    })
                    return True, "success", analysis.suggested_fix
            suggestion = _FIX_SUGGESTIONS.get(
                bug.category,
                "Reproduce the issue in isolation, capture telemetry around "
                "the failure window, and add a regression test that locks the "
                "expected behavior.",
            )
            bug.suggested_fix = suggestion
            bug.fix_confidence = FixConfidence.MEDIUM.value
            self._emit("fix_suggested", bug_id=bug_id, data={
                "source": "heuristic",
                "category": bug.category,
            })
            return True, "success", suggestion

    def find_duplicates(self, bug_id: str) -> List[BugReport]:
        """Return bugs that are likely duplicates of the given bug.

        Duplicate scoring blends a title-weighted Jaccard similarity with a
        full-text Jaccard similarity. Titles carry the strongest duplicate
        signal, so they are weighted more heavily. Bugs in a different
        category are skipped entirely.
        """
        with _lock:
            bug = self._bugs.get(bug_id)
            if bug is None:
                return []

            def _sig_tokens(text: str) -> set:
                return {t for t in _tokenize(text) if len(t) > 3}

            query_title = _sig_tokens(bug.title)
            query_full = _sig_tokens(bug.title + " " + bug.description)
            if not query_full:
                return []

            def _jaccard(a: set, b: set) -> float:
                if not a or not b:
                    return 0.0
                union = len(a | b)
                if union == 0:
                    return 0.0
                return len(a & b) / union

            duplicates: List[Tuple[float, BugReport]] = []
            for other in self._bugs.values():
                if other.bug_id == bug_id:
                    continue
                if other.category != bug.category:
                    continue
                other_title = _sig_tokens(other.title)
                other_full = _sig_tokens(other.title + " " + other.description)
                if not other_full:
                    continue
                title_sim = _jaccard(query_title, other_title)
                full_sim = _jaccard(query_full, other_full)
                # Title similarity dominates; full text breaks ties and
                # catches cases where the title differs but the body matches.
                score = max(title_sim, 0.6 * title_sim + 0.4 * full_sim)
                if score >= 0.3:
                    duplicates.append((score, other))
            duplicates.sort(key=lambda pair: pair[0], reverse=True)
            return [d[1] for d in duplicates]

    def get_bug_summary(self, bug_id: str) -> Dict[str, Any]:
        """Return a consolidated summary of a bug and its supporting data."""
        with _lock:
            bug = self._bugs.get(bug_id)
            if bug is None:
                return {}
            scripts = [
                s.to_dict() for s in self._reproduction_scripts.values()
                if s.bug_id == bug_id
            ]
            reports = [
                r.to_dict() for r in self._player_reports.values()
                if r.bug_id == bug_id
            ]
            analyses = [
                a.to_dict() for a in self._code_analyses.values()
                if a.bug_id == bug_id
            ]
            events = [
                e.to_dict() for e in self._events
                if e.bug_id == bug_id
            ]
            return {
                "bug": bug.to_dict(),
                "reproduction_scripts": scripts,
                "player_reports": reports,
                "code_analyses": analyses,
                "recent_events": events[-20:],
                "reproduction_count": len(scripts),
                "player_report_count": len(reports),
                "code_analysis_count": len(analyses),
            }

    # ------------------------------------------------------------------
    # Observability
    # ------------------------------------------------------------------

    def list_events(
        self, bug_id: str = "", limit: int = 100,
    ) -> List[BugHunterEvent]:
        with _lock:
            items = list(reversed(self._events))
            if bug_id:
                items = [e for e in items if e.bug_id == bug_id]
            if limit and limit > 0:
                items = items[:limit]
            return items

    def get_status(self) -> Dict[str, Any]:
        with _lock:
            self._refresh_stats()
            return {
                "initialized": self._initialized,
                "bugs": len(self._bugs),
                "critical_bugs": self._stats.critical_bugs,
                "high_bugs": self._stats.high_bugs,
                "reproduction_scripts": len(self._reproduction_scripts),
                "telemetry_patterns": len(self._telemetry_patterns),
                "player_reports": len(self._player_reports),
                "code_analyses": len(self._code_analyses),
                "reproduction_runs": self._reproduction_runs,
                "telemetry_scans": self._telemetry_scans,
                "events": len(self._events),
                "tick_count": self._tick_count,
                "auto_classify_enabled": self._config.auto_classify_enabled,
                "auto_reproduce_enabled": self._config.auto_reproduce_enabled,
            }

    def get_stats(self) -> BugHunterStats:
        with _lock:
            self._refresh_stats()
            return self._stats

    def get_snapshot(self) -> BugHunterSnapshot:
        with _lock:
            self._refresh_stats()
            return BugHunterSnapshot(
                timestamp=_now(),
                bugs=[b.to_dict() for b in list(self._bugs.values())[:100]],
                reproduction_scripts=[
                    s.to_dict()
                    for s in list(self._reproduction_scripts.values())[:100]
                ],
                telemetry_patterns=[
                    p.to_dict()
                    for p in list(self._telemetry_patterns.values())[:100]
                ],
                player_reports=[
                    r.to_dict()
                    for r in list(self._player_reports.values())[:100]
                ],
                code_analyses=[
                    a.to_dict()
                    for a in list(self._code_analyses.values())[:100]
                ],
                stats=self._stats.to_dict(),
            )

    def get_config(self) -> BugHunterConfig:
        with _lock:
            return self._config

    def set_config(self, **kwargs: Any) -> Tuple[bool, str, BugHunterConfig]:
        """Apply configuration updates passed as keyword arguments."""
        with _lock:
            if not kwargs:
                return False, "no_updates", self._config
            for key, value in kwargs.items():
                if key == "metadata" and isinstance(value, dict):
                    self._config.metadata.update(value)
                elif hasattr(self._config, key):
                    if key in ("max_bugs", "max_reproduction_scripts",
                               "max_telemetry_patterns", "max_player_reports",
                               "telemetry_scan_interval"):
                        setattr(self._config, key,
                                max(1, _safe_int(value,
                                                 getattr(self._config, key))))
                    elif key == "confidence_threshold":
                        setattr(self._config, key,
                                _clamp(_safe_float(value, 0.6), 0.0, 1.0))
                    elif key in ("auto_classify_enabled",
                                 "auto_reproduce_enabled"):
                        setattr(self._config, key, bool(value))
                    else:
                        setattr(self._config, key, value)
            self._emit("config_updated", data={"keys": list(kwargs.keys())})
            return True, "updated", self._config

    def tick(self, dt: float = 1.0) -> Dict[str, Any]:
        """Advance the hunter by one tick, running automated workflows."""
        with _lock:
            self._tick_count += 1
            classified = 0
            reproduced = 0
            fixed_promoted = 0
            # Auto-classify bugs that are still only detected.
            if self._config.auto_classify_enabled:
                for bug in list(self._bugs.values()):
                    if bug.status == BugStatus.DETECTED.value \
                            and not bug.metadata.get("auto_classified"):
                        category, severity = self._classify_text(
                            bug.title + " " + bug.description
                            + " " + bug.stack_trace
                        )
                        bug.category = category
                        bug.severity = severity
                        bug.metadata["auto_classified"] = True
                        bug.metadata["classification_source"] = \
                            DetectionSource.AI_INFERENCE.value
                        bug.last_seen = _now()
                        classified += 1
                        self._emit("bug_auto_classified", bug_id=bug.bug_id,
                                   data={
                                       "category": category,
                                       "severity": severity,
                                   })
            # Auto-run reproduction scripts for investigating bugs.
            if self._config.auto_reproduce_enabled:
                for script in list(self._reproduction_scripts.values()):
                    bug = self._bugs.get(script.bug_id)
                    if bug is None:
                        continue
                    if bug.status not in (BugStatus.DETECTED.value,
                                          BugStatus.INVESTIGATING.value):
                        continue
                    self._reproduction_runs += 1
                    succeeded = random.random() < 0.6
                    alpha = 0.3
                    outcome = 1.0 if succeeded else 0.0
                    script.success_rate = round(
                        (alpha * outcome)
                        + ((1.0 - alpha) * script.success_rate), 4,
                    )
                    script.last_run = _now()
                    reproduced += 1
                    if succeeded:
                        script.actual_result = (
                            script.expected_result or "reproduced"
                        )
                        if bug.status == BugStatus.DETECTED.value:
                            bug.status = BugStatus.INVESTIGATING.value
                            fixed_promoted += 1
                    else:
                        script.actual_result = (
                            "unable_to_reproduce_on_this_run"
                        )
            self._refresh_stats()
            self._emit("tick", data={
                "tick_count": self._tick_count,
                "classified": classified,
                "reproduced": reproduced,
            })
            return {
                "tick": self._tick_count,
                "dt": dt,
                "auto_classified": classified,
                "auto_reproduced": reproduced,
                "promoted_to_investigating": fixed_promoted,
                "total_bugs": self._stats.total_bugs,
                "critical_bugs": self._stats.critical_bugs,
                "fixed_bugs": self._stats.fixed_bugs,
                "events": len(self._events),
            }

    def reset(self) -> None:
        """Clear all hunter state and re-seed the canonical dataset."""
        with _lock:
            self._bugs.clear()
            self._reproduction_scripts.clear()
            self._telemetry_patterns.clear()
            self._player_reports.clear()
            self._code_analyses.clear()
            self._events.clear()
            self._config = BugHunterConfig()
            self._stats = BugHunterStats()
            self._tick_count = 0
            self._reproduction_runs = 0
            self._telemetry_scans = 0
            self._initialized = False
            self._seed()

    # ------------------------------------------------------------------
    # Seed Data
    # ------------------------------------------------------------------

    def _seed(self) -> None:
        """Populate the hunter with a canonical set of bug hunting data."""
        with self._init_lock:
            if self._initialized:
                return

            # ----------------------------------------------------------
            # Bug Reports (10)
            # ----------------------------------------------------------
            self._seed_bugs()

            # ----------------------------------------------------------
            # Reproduction Scripts (5)
            # ----------------------------------------------------------
            self._seed_reproduction_scripts()

            # ----------------------------------------------------------
            # Telemetry Patterns (5)
            # ----------------------------------------------------------
            self._seed_telemetry_patterns()

            # ----------------------------------------------------------
            # Player Reports (5)
            # ----------------------------------------------------------
            self._seed_player_reports()

            # ----------------------------------------------------------
            # Code Analysis Results (5)
            # ----------------------------------------------------------
            self._seed_code_analyses()

            self._emit("hunter_seeded", data={
                "bugs": len(self._bugs),
                "reproduction_scripts": len(self._reproduction_scripts),
                "telemetry_patterns": len(self._telemetry_patterns),
                "player_reports": len(self._player_reports),
                "code_analyses": len(self._code_analyses),
            })
            self._initialized = True

    def _seed_bugs(self) -> None:
        bug_specs = [
            (
                "bug_crash_001",
                "Engine crash during scene transition",
                "The engine hard crashes when transitioning from the "
                "overworld to the dungeon scene while a streaming asset "
                "is still being decompressed. A null pointer is "
                "accessed inside the scene loader.",
                BugSeverity.CRITICAL, BugStatus.CONFIRMED, BugCategory.CRASH,
                DetectionSource.TELEMETRY, Reproducibility.ALWAYS,
                ["1.4.0", "1.4.1"], ["windows", "linux", "macos"],
                "SIGSEGV at SceneLoader::finalize (scene_loader.cpp:412)\n"
                "  #0 SceneLoader::finalize\n"
                "  #1 TransitionManager::commit\n"
                "  #2 GameLoop::onFrame",
                [
                    "Load into the overworld scene",
                    "Trigger the dungeon entrance transition",
                    "Observe the crash during asset decompression",
                ],
                "Scene transition completes without crashing",
                "Engine crashes with SIGSEGV in SceneLoader::finalize",
                "Guard the asset readiness check before finalizing the "
                "scene loader and defer the transition until streaming "
                "completes.",
                FixConfidence.HIGH,
            ),
            (
                "bug_perf_drop_001",
                "Frame rate drops in dense forest biome",
                "Average frame rate drops from 60 to 22 fps when the "
                "camera enters the dense forest biome. Profiling shows "
                "excessive draw calls from unbatched foliage.",
                BugSeverity.HIGH, BugStatus.INVESTIGATING,
                BugCategory.PERFORMANCE,
                DetectionSource.TELEMETRY, Reproducibility.SOMETIMES,
                ["1.4.0"], ["windows", "macos"],
                "",
                [
                    "Travel to the Whispering Woods region",
                    "Move the camera across the dense foliage cluster",
                    "Observe the frame rate collapse",
                ],
                "Stable 60 fps across all biomes",
                "Frame rate collapses to 22 fps in dense foliage",
                "Instanced foliage rendering and GPU-driven batching for "
                "the forest biome draw calls.",
                FixConfidence.MEDIUM,
            ),
            (
                "bug_texture_flicker_001",
                "Texture flickering on water surfaces",
                "Water surface textures flicker when the camera moves at "
                "shallow angles near sunset. The flicker is caused by "
                "z-fighting between the water plane and the reflection "
                "buffer.",
                BugSeverity.MEDIUM, BugStatus.REPRODUCED,
                BugCategory.GRAPHICS,
                DetectionSource.PLAYER_REPORT, Reproducibility.ALWAYS,
                ["1.3.5", "1.4.0"], ["windows", "linux"],
                "",
                [
                    "Stand near the lake at golden hour",
                    "Rotate the camera to a shallow angle",
                    "Observe the water texture flicker",
                ],
                "Stable water rendering at all camera angles",
                "Water surface flickers due to z-fighting",
                "Apply a depth bias to the water material and tighten "
                "the reflection buffer near plane.",
                FixConfidence.MEDIUM,
            ),
            (
                "bug_typo_001",
                "Typographical error in quest dialog",
                "The quest giver dialog for 'The Lost Caravan' contains "
                "a spelling mistake: 'caravan' is written as 'caravann' "
                "in the third response line.",
                BugSeverity.TRIVIAL, BugStatus.FIXED, BugCategory.UI,
                DetectionSource.PLAYER_REPORT, Reproducibility.ALWAYS,
                ["1.4.0"], ["all"],
                "",
                [
                    "Speak with the quest giver in Millhaven",
                    "Progress to the third dialog response",
                    "Observe the spelling mistake",
                ],
                "Correct spelling of 'caravan'",
                "Misspelled as 'caravann'",
                "Correct the localized string in the quest dialog table.",
                FixConfidence.HIGH,
            ),
            (
                "bug_ai_stuck_001",
                "NPC pathfinding stuck behind obstacles",
                "Escort NPCs become stuck behind small environmental "
                "obstacles and stop following the player. The navmesh "
                "agent fails to find an alternate route around thin "
                "collision boxes.",
                BugSeverity.HIGH, BugStatus.DETECTED,
                BugCategory.AI_BEHAVIOR,
                DetectionSource.TELEMETRY, Reproducibility.SOMETIMES,
                ["1.4.0", "1.4.1"], ["windows", "macos", "linux"],
                "",
                [
                    "Start the escort quest in the Iron Pass",
                    "Walk around a thin fence obstacle",
                    "Observe the NPC freeze behind the fence",
                ],
                "NPC navigates around obstacles to follow the player",
                "NPC pathfinding stalls behind thin collision boxes",
                "Add a fallback pathfinding query with a wider corridor "
                "and a stuck-agent recovery behavior.",
                FixConfidence.LOW,
            ),
            (
                "bug_memory_leak_001",
                "Memory leak during long play sessions",
                "Process memory grows continuously during long play "
                "sessions, exceeding 4 GB after roughly two hours. "
                "Disconnected particle systems are not released by the "
                "effect pool.",
                BugSeverity.CRITICAL, BugStatus.CONFIRMED,
                BugCategory.MEMORY,
                DetectionSource.TELEMETRY, Reproducibility.ALWAYS,
                ["1.4.0", "1.4.1"], ["windows", "macos"],
                "MemoryError: allocation failed at ParticlePool::acquire",
                [
                    "Enter a combat-heavy area",
                    "Trigger many particle effects over two hours",
                    "Observe steady memory growth in the profiler",
                ],
                "Stable memory footprint across long sessions",
                "Memory grows without bound until allocation fails",
                "Release disconnected particle systems back to the pool "
                "and add a periodic pool compaction pass.",
                FixConfidence.HIGH,
            ),
            (
                "bug_desync_001",
                "Client-server desynchronization during combat",
                "Players observe rubber-banding and hit registration "
                "desync during high-intensity combat. The client and "
                "server diverge on entity positions by several meters.",
                BugSeverity.HIGH, BugStatus.REPRODUCED,
                BugCategory.NETWORK,
                DetectionSource.PLAYER_REPORT, Reproducibility.SOMETIMES,
                ["1.4.0"], ["windows", "macos", "linux"],
                "",
                [
                    "Join a high-population combat encounter",
                    "Engage multiple enemies with fast abilities",
                    "Observe position and hit registration desync",
                ],
                "Client and server remain synchronized during combat",
                "Positions diverge and hits fail to register",
                "Increase snapshot interpolation buffering and add "
                "server-side reconciliation for fast abilities.",
                FixConfidence.MEDIUM,
            ),
            (
                "bug_ui_overlap_001",
                "Inventory panel overlaps minimap at low resolutions",
                "At 1280x720 the inventory panel overlaps the minimap, "
                "hiding the compass and quest tracker.",
                BugSeverity.LOW, BugStatus.DETECTED, BugCategory.UI,
                DetectionSource.PLAYER_REPORT, Reproducibility.ALWAYS,
                ["1.4.0"], ["windows"],
                "",
                [
                    "Set the display resolution to 1280x720",
                    "Open the inventory panel",
                    "Observe the overlap with the minimap",
                ],
                "Inventory panel respects the minimap safe area",
                "Inventory panel overlaps the minimap at low resolution",
                "Anchor the inventory panel to the safe area and clamp "
                "its width at low aspect ratios.",
                FixConfidence.MEDIUM,
            ),
            (
                "bug_save_corrupt_001",
                "Save file corruption on version upgrade",
                "Save files become corrupt when upgrading from 1.3.x to "
                "1.4.0. The migration path fails to remap legacy quest "
                "state fields, leaving the save unreadable.",
                BugSeverity.CRITICAL, BugStatus.FIXING,
                BugCategory.SAVE_SYSTEM,
                DetectionSource.AUTOMATED_TEST, Reproducibility.ALWAYS,
                ["1.3.5", "1.4.0"], ["all"],
                "",
                [
                    "Create a save on version 1.3.5",
                    "Upgrade the game to version 1.4.0",
                    "Attempt to load the legacy save",
                ],
                "Legacy saves migrate cleanly to 1.4.0",
                "Save file is corrupt and cannot be loaded",
                "Add a schema migration step that remaps legacy quest "
                "state fields and keeps a backup of the original save.",
                FixConfidence.HIGH,
            ),
            (
                "bug_input_lag_001",
                "Input latency spike during heavy effects",
                "Input latency spikes to 180 ms during heavy particle "
                "and post-processing effects. The input thread appears "
                "to be starved by the render thread.",
                BugSeverity.MEDIUM, BugStatus.CONFIRMED,
                BugCategory.INPUT,
                DetectionSource.TELEMETRY, Reproducibility.SOMETIMES,
                ["1.4.0"], ["windows", "macos"],
                "",
                [
                    "Enter an area with heavy post-processing",
                    "Trigger a large particle burst",
                    "Measure input-to-frame latency",
                ],
                "Input latency stays below 50 ms",
                "Input latency spikes to 180 ms during heavy effects",
                "Decouple input sampling from the render loop and "
                "guarantee an input poll each frame.",
                FixConfidence.MEDIUM,
            ),
        ]
        for (bid, title, desc, sev, stat, cat, src, repro,
             versions, platforms, trace, steps, expected,
             actual, fix, conf) in bug_specs:
            bug = BugReport(
                bug_id=bid,
                title=title,
                description=desc,
                severity=sev.value,
                status=stat.value,
                category=cat.value,
                detection_source=src.value,
                reproducibility=repro.value,
                first_seen=_now(),
                last_seen=_now(),
                occurrence_count=random.randint(1, 48),
                affected_versions=list(versions),
                affected_platforms=list(platforms),
                stack_trace=trace,
                reproduction_steps=list(steps),
                expected_behavior=expected,
                actual_behavior=actual,
                suggested_fix=fix,
                fix_confidence=conf.value,
                reporter_id="system" if src == DetectionSource.TELEMETRY
                else "qa_team",
                assignee_id="eng_" + cat.value,
                metadata={"seeded": True},
            )
            self._bugs[bid] = bug

    def _seed_reproduction_scripts(self) -> None:
        script_specs = [
            (
                "repro_crash_001", "bug_crash_001",
                [
                    "Boot the game in debug mode",
                    "Load the overworld scene",
                    "Issue the dungeon transition command",
                    "Capture the crash dump from SceneLoader::finalize",
                ],
                "Debug build with asset streaming enabled",
                "transition(dungeon_entrance_01)",
                "Scene transition completes cleanly",
                "Engine crashes with SIGSEGV",
                0.92,
            ),
            (
                "repro_perf_drop_001", "bug_perf_drop_001",
                [
                    "Load into the Whispering Woods region",
                    "Set the camera to free-fly mode",
                    "Sweep the camera across the dense foliage cluster",
                    "Capture a GPU profile of the frame",
                ],
                "Profiling overlay enabled",
                "camera.sweep(foliage_cluster_a)",
                "Frame rate stays at or above 60 fps",
                "Frame rate collapses to 22 fps",
                0.78,
            ),
            (
                "repro_desync_001", "bug_desync_001",
                [
                    "Join a high-population combat instance",
                    "Engage five enemies with fast abilities",
                    "Record client and server position logs",
                    "Compare the divergent entity positions",
                ],
                "Network debug logging enabled",
                "combat.engage(enemy_pack_05)",
                "Client and server positions stay within tolerance",
                "Positions diverge by several meters",
                0.65,
            ),
            (
                "repro_texture_flicker_001", "bug_texture_flicker_001",
                [
                    "Teleport to the lake at golden hour",
                    "Lower the camera to a shallow angle",
                    "Rotate the camera slowly",
                    "Capture a frame sequence of the flicker",
                ],
                "Graphics preset set to high",
                "camera.rotate(shallow_angle, 360)",
                "Stable water rendering",
                "Water texture flickers from z-fighting",
                0.88,
            ),
            (
                "repro_ai_stuck_001", "bug_ai_stuck_001",
                [
                    "Start the escort quest in the Iron Pass",
                    "Walk the escort NPC toward a thin fence",
                    "Observe the pathfinding stall",
                    "Capture the navmesh debug overlay",
                ],
                "Navmesh debug overlay enabled",
                "escort.move_to(fence_obstacle_03)",
                "NPC routes around the fence",
                "NPC freezes behind the thin collision box",
                0.55,
            ),
        ]
        for (sid, bid, steps, pre, inputs, expected, actual,
             success_rate) in script_specs:
            script = ReproductionScript(
                script_id=sid,
                bug_id=bid,
                steps=list(steps),
                preconditions=pre,
                input_sequence=inputs,
                expected_result=expected,
                actual_result=actual,
                success_rate=success_rate,
                last_run=_now(),
                metadata={"seeded": True},
            )
            self._reproduction_scripts[sid] = script

    def _seed_telemetry_patterns(self) -> None:
        pattern_specs = [
            (
                "pattern_crash_spike",
                "Crash Rate Spike",
                "Detects when the per-session crash rate exceeds the "
                "safe threshold, indicating a stability regression.",
                "crash_rate", ">", 0.05, 60,
                BugCategory.CRASH, 0.92,
            ),
            (
                "pattern_fps_drop",
                "Frame Rate Floor Breach",
                "Detects when the average frame rate drops below the "
                "playable floor for a sustained window.",
                "avg_fps", "<", 30.0, 120,
                BugCategory.PERFORMANCE, 0.8,
            ),
            (
                "pattern_memory_growth",
                "Memory Usage Ceiling Breach",
                "Detects when resident memory exceeds the safe ceiling, "
                "indicating a likely leak under sustained play.",
                "memory_usage_mb", ">", 2048.0, 300,
                BugCategory.MEMORY, 0.85,
            ),
            (
                "pattern_network_latency",
                "Network Latency Spike",
                "Detects when the round-trip network latency exceeds "
                "the tolerance for responsive combat.",
                "network_latency_ms", ">", 200.0, 60,
                BugCategory.NETWORK, 0.75,
            ),
            (
                "pattern_ai_loop",
                "AI Tick Duration Spike",
                "Detects when the AI decision loop consumes more than "
                "the allotted frame budget, indicating a stuck or "
                "divergent behavior tree.",
                "ai_tick_duration_ms", ">", 50.0, 30,
                BugCategory.AI_BEHAVIOR, 0.7,
            ),
        ]
        for (pid, name, desc, metric, cond, threshold,
             window, cat, confidence) in pattern_specs:
            pattern = TelemetryPattern(
                pattern_id=pid,
                name=name,
                description=desc,
                metric_name=metric,
                condition=cond,
                threshold=threshold,
                window_size=window,
                bug_category=cat.value,
                confidence_score=confidence,
                metadata={"seeded": True},
            )
            self._telemetry_patterns[pid] = pattern

    def _seed_player_reports(self) -> None:
        report_specs = [
            (
                "rpt_001", "player_8421", "bug_crash_001",
                "Game crashed going into the dungeon",
                "I was walking up to the dungeon entrance and the game "
                "just crashed to desktop. It happened twice in a row.",
                "1.4.0", "windows", "sess_8421_a",
                [
                    "Walked to the dungeon entrance",
                    "Pressed the interact key",
                    "Game crashed to desktop",
                ],
                BugSeverity.CRITICAL,
            ),
            (
                "rpt_002", "player_3092", "bug_perf_drop_001",
                "Massive fps drop in the forest",
                "The game runs fine until I enter the Whispering Woods, "
                "then my fps tanks to the low twenties.",
                "1.4.0", "macos", "sess_3092_b",
                [
                    "Entered the Whispering Woods",
                    "Fps dropped from 60 to 22",
                ],
                BugSeverity.HIGH,
            ),
            (
                "rpt_003", "player_5510", "bug_desync_001",
                "Rubber-banding in combat",
                "During the big fight in the arena my character kept "
                "rubber-banding and my hits were not registering.",
                "1.4.0", "linux", "sess_5510_c",
                [
                    "Joined the arena combat encounter",
                    "Used fast abilities repeatedly",
                    "Observed rubber-banding and missed hits",
                ],
                BugSeverity.HIGH,
            ),
            (
                "rpt_004", "player_7733", "bug_texture_flicker_001",
                "Water flickers at sunset",
                "The lake near the mill flickers badly when I look "
                "across it at sunset. Looks like a z-fighting issue.",
                "1.3.5", "windows", "sess_7733_d",
                [
                    "Stood near the lake at sunset",
                    "Looked across the water at a shallow angle",
                    "Observed the flicker",
                ],
                BugSeverity.MEDIUM,
            ),
            (
                "rpt_005", "player_2218", "bug_save_corrupt_001",
                "My save broke after the update",
                "After updating to 1.4.0 my save from 1.3.5 will not "
                "load anymore. It says the save is corrupt.",
                "1.4.0", "windows", "sess_2218_e",
                [
                    "Updated the game to 1.4.0",
                    "Tried to load my 1.3.5 save",
                    "Got a corrupt save error",
                ],
                BugSeverity.CRITICAL,
            ),
        ]
        for (rid, player, bid, title, desc, version, platform,
             session, steps, sev) in report_specs:
            report = PlayerReport(
                report_id=rid,
                player_id=player,
                bug_id=bid,
                title=title,
                description=desc,
                timestamp=_now(),
                game_version=version,
                platform=platform,
                session_id=session,
                reproduction_steps=list(steps),
                severity_assessment=sev.value,
                metadata={"seeded": True},
            )
            self._player_reports[rid] = report

    def _seed_code_analyses(self) -> None:
        analysis_specs = [
            (
                "ca_crash_001", "bug_crash_001",
                "engine/scene/scene_loader.cpp", 405, 420,
                "null_pointer_access",
                "The finalize method accesses the active stream "
                "handle without checking that streaming has completed.",
                "auto& stream = active_streams[handle];\n"
                "stream->finalize();  // stream may be null",
                "Guard the access with a readiness check and defer "
                "the transition until streaming completes.",
                FixConfidence.HIGH,
            ),
            (
                "ca_memory_leak_001", "bug_memory_leak_001",
                "engine/effects/particle_pool.cpp", 88, 104,
                "resource_leak",
                "Disconnected particle systems are removed from the "
                "active list but never returned to the free pool.",
                "active_particles.remove(ps);\n"
                "// missing: free_pool.release(ps);",
                "Release disconnected particle systems back to the free "
                "pool and add a periodic compaction pass.",
                FixConfidence.HIGH,
            ),
            (
                "ca_desync_001", "bug_desync_001",
                "game/net/combat_sync.cpp", 142, 165,
                "missing_reconciliation",
                "Fast abilities bypass the server reconciliation pass, "
                "allowing client and server positions to diverge.",
                "if (ability.is_fast) {\n"
                "    apply_locally(ability);\n"
                "    // missing: queue_reconciliation(ability);\n"
                "}",
                "Queue a server reconciliation step for fast abilities "
                "and clamp the client prediction error.",
                FixConfidence.MEDIUM,
            ),
            (
                "ca_ai_stuck_001", "bug_ai_stuck_001",
                "game/ai/navmesh_agent.cpp", 57, 78,
                "missing_fallback",
                "The pathfinding query has no fallback when the primary "
                "corridor is blocked by a thin collision box.",
                "if (!primary_path.valid) {\n"
                "    stop();\n"
                "    // missing: request_fallback_path();\n"
                "}",
                "Request a fallback path with a wider corridor and add "
                "a stuck-agent recovery behavior after a timeout.",
                FixConfidence.LOW,
            ),
            (
                "ca_input_lag_001", "bug_input_lag_001",
                "engine/input/input_system.cpp", 31, 49,
                "thread_starvation",
                "The input poll is issued from the render thread, which "
                "starves input during heavy post-processing.",
                "// render thread\n"
                "render_frame();\n"
                "poll_input();  // starved under load",
                "Decouple input sampling into its own thread and "
                "guarantee an input poll each frame.",
                FixConfidence.MEDIUM,
            ),
        ]
        for (aid, bid, path, ls, le, issue_type, issue_desc,
             snippet, fix, conf) in analysis_specs:
            analysis = CodeAnalysisResult(
                analysis_id=aid,
                bug_id=bid,
                file_path=path,
                line_start=ls,
                line_end=le,
                issue_type=issue_type,
                issue_description=issue_desc,
                code_snippet=snippet,
                suggested_fix=fix,
                confidence=conf.value,
                metadata={"seeded": True},
            )
            self._code_analyses[aid] = analysis


# ---------------------------------------------------------------------------
# Module-Level Factory
# ---------------------------------------------------------------------------


def get_ai_bug_hunter() -> AIBugHunter:
    """Return the singleton AIBugHunter instance."""
    return AIBugHunter.get_instance()


# ---------------------------------------------------------------------------
# Exported Symbols
# ---------------------------------------------------------------------------

__all__ = [
    # Enums
    "BugSeverity",
    "BugStatus",
    "BugCategory",
    "DetectionSource",
    "Reproducibility",
    "FixConfidence",
    # Data classes
    "BugReport",
    "ReproductionScript",
    "TelemetryPattern",
    "CodeAnalysisResult",
    "PlayerReport",
    "BugHunterConfig",
    "BugHunterStats",
    "BugHunterSnapshot",
    "BugHunterEvent",
    # Main system class
    "AIBugHunter",
    # Factory
    "get_ai_bug_hunter",
]
