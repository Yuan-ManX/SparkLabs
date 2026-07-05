"""
SparkLabs Engine - Anti-Cheat and Game Integrity Verification System

A self-contained integrity layer for the SparkLabs AI-native game engine. It
scans player memory and behavior, detects speed hacks, memory edits, packet
manipulation, aim bots, item duplication, and client tampering, then issues
flags, bans, alerts, and audit reports. All state is held in bounded in-memory
stores with FIFO eviction so the system stays predictable under load.

Architecture:
  IntegrityGuardSystem (singleton)
    |-- IntegrityRule        -- a detection rule bound to a violation type
    |-- ScanResult           -- one scan lifecycle for a player
    |-- Violation            -- a confirmed integrity violation
    |-- PlayerIntegrity      -- per-player integrity standing and risk score
    |-- IntegrityAlert       -- a manual or auto alert for review
    |-- IntegrityReport      -- a rolled-up report over a time window
    |-- IntegrityStats       -- aggregate counters
    |-- IntegritySnapshot    -- immutable full-state snapshot
    |-- IntegrityLogEvent    -- audit log entry
    |-- ViolationType, DetectionMethod, SeverityLevel, ActionTaken,
        PlayerStatus, IntegrityEventKind

Core Capabilities:
  - add_rule / get_rule / list_rules / update_rule / remove_rule: rule registry.
  - start_scan / get_scan / list_scans / complete_scan: scan lifecycle.
  - record_violation / get_violation / list_violations / resolve_violation:
    violation capture and resolution workflow.
  - register_player / get_player / list_players / flag_player / ban_player /
    clear_player: player standing management with risk scoring.
  - issue_alert / get_alert / list_alerts / acknowledge_alert: alert workflow.
  - generate_report / get_report / list_reports: rolled-up integrity reports.
  - list_events / get_stats / get_status / get_snapshot / reset: observability
    and state management.

The module is written from scratch for SparkLabs. It depends only on the Python
standard library and follows the engine-wide singleton + reentrant-lock
conventions used across the SparkLabs engine modules.
"""

from __future__ import annotations

import threading
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------------
# Capacity Constants
# ---------------------------------------------------------------------------

_MAX_RULES: int = 500
_MAX_SCANS: int = 20000
_MAX_VIOLATIONS: int = 50000
_MAX_PLAYERS: int = 50000
_MAX_ALERTS: int = 10000
_MAX_REPORTS: int = 5000
_MAX_EVENTS: int = 10000

# Risk weight added to a player's risk score when a violation of a given
# severity is recorded. Resolving a violation refunds the same weight.
_SEVERITY_WEIGHTS: Dict["SeverityLevel", float] = {}  # populated after the enum is defined


# ---------------------------------------------------------------------------
# Helper Functions
# ---------------------------------------------------------------------------


def _now() -> str:
    """Return the current UTC time as an ISO-8601 string with a ``Z`` suffix."""
    return datetime.utcnow().isoformat() + "Z"


def _new_id(prefix: str = "") -> str:
    """Generate a short unique identifier, optionally prefixed.

    Args:
        prefix: Optional prefix joined to the generated identifier with an
            underscore. When empty, the raw hexadecimal identifier is returned.

    Returns:
        A short hexadecimal identifier, optionally prefixed.
    """
    base = uuid.uuid4().hex[:12]
    return f"{prefix}_{base}" if prefix else base


def _evict_fifo_dict(store: Dict[str, Any], max_size: int) -> None:
    """Evict the oldest entries from a dict until it fits within ``max_size``.

    Eviction is FIFO based on dict insertion order. The capacity is floored at
    one so that a store can always retain its most recent entry.
    """
    cap = max(1, int(max_size))
    while len(store) > cap:
        oldest_key = next(iter(store), None)
        if oldest_key is None:
            break
        store.pop(oldest_key, None)


def _evict_fifo_list(store: List[Any], max_size: int) -> None:
    """Evict the oldest entries from a list until it fits within ``max_size``.

    Eviction is FIFO by popping from the front of the list.
    """
    cap = max(1, int(max_size))
    while len(store) > cap:
        if not store:
            break
        store.pop(0)


def _to_jsonable(value: Any) -> Any:
    """Recursively convert a value into a JSON-friendly representation.

    Handles ``None``, ``Enum`` values (returns ``.value``), dicts, lists and
    tuples, sets, and any object exposing a ``to_dict()`` method (such as the
    dataclasses defined in this module). All other values are returned
    unchanged.
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
        return [_to_jsonable(v) for v in value]
    if hasattr(value, "to_dict") and callable(value.to_dict):
        return _dataclass_to_dict(value)
    return value


def _dataclass_to_dict(instance: Any) -> Dict[str, Any]:
    """Serialize a dataclass instance into a dict via ``_to_jsonable``.

    Iterates over ``__dataclass_fields__`` so that field order is preserved and
    every value is normalized through ``_to_jsonable``. Non-dataclass inputs
    degrade gracefully to an empty dict (or a copy when a plain dict is given).
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


def _iso_from_now(hours: float) -> str:
    """Return an ISO-8601 ``Z`` timestamp that is ``hours`` from now."""
    ts = datetime.utcnow().timestamp() + max(0.0, float(hours)) * 3600.0
    return datetime.utcfromtimestamp(ts).isoformat() + "Z"


def _in_period(ts: str, start: str, end: str) -> bool:
    """Return whether ``ts`` falls inside the inclusive [start, end] window.

    Empty ``start`` or ``end`` bounds are treated as unbounded on that side.
    Uses ISO-8601 lexicographic comparison, which is correct for timestamps
    produced by ``_now``.
    """
    if not ts:
        return False
    if start and ts < start:
        return False
    if end and ts > end:
        return False
    return True


# ---------------------------------------------------------------------------
# Domain Enums
# ---------------------------------------------------------------------------


class ViolationType(Enum):
    """Classifications of integrity violations tracked by the system."""

    SPEED_HACK = "speed_hack"
    MEMORY_EDIT = "memory_edit"
    PACKET_MANIPULATION = "packet_manipulation"
    AIM_BOT = "aim_bot"
    WALL_HACK = "wall_hack"
    DUP_ITEM = "dup_item"
    GOLD_HACK = "gold_hack"
    XP_HACK = "xp_hack"
    MACRO_USE = "macro_use"
    ACCOUNT_SHARING = "account_sharing"
    CLIENT_MODIFICATION = "client_modification"
    TRAINER_DETECTED = "trainer_detected"
    UNKNOWN = "unknown"


class DetectionMethod(Enum):
    """Methods used to detect a violation."""

    HEURISTIC = "heuristic"
    SIGNATURE = "signature"
    STATISTICAL = "statistical"
    BEHAVIORAL = "behavioral"
    MEMORY_SCAN = "memory_scan"
    NETWORK_ANALYSIS = "network_analysis"
    SERVER_VALIDATION = "server_validation"
    MACHINE_LEARNING = "machine_learning"


class SeverityLevel(Enum):
    """Severity classifications that drive risk scoring and actions."""

    INFO = "info"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ActionTaken(Enum):
    """Actions the system can take in response to a violation."""

    NONE = "none"
    WARN = "warn"
    FLAG = "flag"
    KICK = "kick"
    TEMP_BAN = "temp_ban"
    PERMA_BAN = "perma_ban"
    SHADOW_BAN = "shadow_ban"
    ROLLBACK = "rollback"
    FREEZE_ACCOUNT = "freeze_account"


class PlayerStatus(Enum):
    """Lifecycle states for a player's integrity standing."""

    CLEAN = "clean"
    FLAGGED = "flagged"
    SUSPICIOUS = "suspicious"
    BANNED = "banned"
    UNDER_REVIEW = "under_review"
    CLEARED = "cleared"


class IntegrityEventKind(Enum):
    """Audit event kinds emitted by the integrity system."""

    SCAN_STARTED = "scan_started"
    SCAN_COMPLETED = "scan_completed"
    VIOLATION_DETECTED = "violation_detected"
    VIOLATION_RESOLVED = "violation_resolved"
    PLAYER_FLAGGED = "player_flagged"
    PLAYER_BANNED = "player_banned"
    PLAYER_CLEARED = "player_cleared"
    THRESHOLD_UPDATED = "threshold_updated"
    RULE_ADDED = "rule_added"
    RULE_REMOVED = "rule_removed"
    REPORT_GENERATED = "report_generated"
    ALERT_ISSUED = "alert_issued"


# Severity risk weights, wired up after the enum is defined.
_SEVERITY_WEIGHTS = {
    SeverityLevel.INFO: 5.0,
    SeverityLevel.LOW: 15.0,
    SeverityLevel.MEDIUM: 30.0,
    SeverityLevel.HIGH: 50.0,
    SeverityLevel.CRITICAL: 75.0,
}


# ---------------------------------------------------------------------------
# Data Classes
# ---------------------------------------------------------------------------


@dataclass
class IntegrityRule:
    """A detection rule bound to a violation type and detection method.

    Attributes:
        rule_id: Unique identifier for the rule.
        name: Human-readable name of the rule.
        violation_type: The ViolationType this rule targets.
        detection_method: The DetectionMethod used to evaluate the rule.
        threshold: Numeric threshold above which the rule triggers.
        sensitivity: Sensitivity tuning value in the range [0.0, 1.0].
        enabled: Whether the rule is active during scans.
        description: Free-form description of what the rule detects.
        created_at: ISO-8601 timestamp the rule was created.
        updated_at: ISO-8601 timestamp the rule was last updated.
        trigger_count: Number of times the rule has triggered a violation.
    """

    rule_id: str = field(default_factory=lambda: _new_id("rule"))
    name: str = ""
    violation_type: ViolationType = ViolationType.UNKNOWN
    detection_method: DetectionMethod = DetectionMethod.HEURISTIC
    threshold: float = 1.0
    sensitivity: float = 0.5
    enabled: bool = True
    description: str = ""
    created_at: str = field(default_factory=_now)
    updated_at: str = field(default_factory=_now)
    trigger_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class ScanResult:
    """One scan lifecycle for a player.

    Attributes:
        scan_id: Unique identifier for the scan.
        player_id: The player scanned.
        started_at: ISO-8601 timestamp the scan started.
        completed_at: ISO-8601 timestamp the scan completed (empty while running).
        rules_evaluated: Number of rules evaluated during the scan.
        violations_found: Number of violations produced by the scan.
        status: Lifecycle state: ``running``, ``completed``, or ``failed``.
        details: Free-form summary of the scan outcome.
    """

    scan_id: str = field(default_factory=lambda: _new_id("scan"))
    player_id: str = ""
    started_at: str = field(default_factory=_now)
    completed_at: str = ""
    rules_evaluated: int = 0
    violations_found: int = 0
    status: str = "running"
    details: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class Violation:
    """A confirmed integrity violation recorded against a player.

    Attributes:
        violation_id: Unique identifier for the violation.
        scan_id: The scan that produced the violation.
        player_id: The player who committed the violation.
        violation_type: The ViolationType classification.
        detection_method: The DetectionMethod that caught it.
        severity: The SeverityLevel assigned to the violation.
        confidence: Confidence score in the range [0.0, 1.0].
        description: Free-form description of the detected behavior.
        detected_at: ISO-8601 timestamp the violation was detected.
        evidence: Free-form evidence bag captured by the detector.
        action_taken: The ActionTaken in response to the violation.
        resolved: Whether the violation has been resolved.
        resolved_at: ISO-8601 timestamp the violation was resolved.
    """

    violation_id: str = field(default_factory=lambda: _new_id("viol"))
    scan_id: str = ""
    player_id: str = ""
    violation_type: ViolationType = ViolationType.UNKNOWN
    detection_method: DetectionMethod = DetectionMethod.HEURISTIC
    severity: SeverityLevel = SeverityLevel.INFO
    confidence: float = 0.0
    description: str = ""
    detected_at: str = field(default_factory=_now)
    evidence: Dict[str, Any] = field(default_factory=dict)
    action_taken: ActionTaken = ActionTaken.NONE
    resolved: bool = False
    resolved_at: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class PlayerIntegrity:
    """Per-player integrity standing and risk score.

    Attributes:
        player_id: Unique identifier for the player.
        status: The current PlayerStatus.
        violation_count: Total violations recorded against the player.
        last_scan_at: ISO-8601 timestamp of the player's last scan.
        last_violation_at: ISO-8601 timestamp of the player's last violation.
        risk_score: Aggregate risk score in the range [0.0, 100.0].
        banned_until: ISO-8601 timestamp the ban expires (empty if permanent).
        ban_reason: Reason recorded when the player was banned.
        flagged_at: ISO-8601 timestamp the player was flagged.
        cleared_at: ISO-8601 timestamp the player was cleared.
        history: Chronological log of standing changes for the player.
    """

    player_id: str = ""
    status: PlayerStatus = PlayerStatus.CLEAN
    violation_count: int = 0
    last_scan_at: str = ""
    last_violation_at: str = ""
    risk_score: float = 0.0
    banned_until: str = ""
    ban_reason: str = ""
    flagged_at: str = ""
    cleared_at: str = ""
    history: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class IntegrityAlert:
    """A manual or automatic alert raised for review.

    Attributes:
        alert_id: Unique identifier for the alert.
        player_id: The player the alert concerns.
        violation_type: The ViolationType associated with the alert.
        severity: The SeverityLevel of the alert.
        message: Human-readable alert message.
        created_at: ISO-8601 timestamp the alert was created.
        acknowledged: Whether the alert has been acknowledged.
        acknowledged_by: Identifier of the user who acknowledged the alert.
        acknowledged_at: ISO-8601 timestamp the alert was acknowledged.
    """

    alert_id: str = field(default_factory=lambda: _new_id("alert"))
    player_id: str = ""
    violation_type: ViolationType = ViolationType.UNKNOWN
    severity: SeverityLevel = SeverityLevel.INFO
    message: str = ""
    created_at: str = field(default_factory=_now)
    acknowledged: bool = False
    acknowledged_by: str = ""
    acknowledged_at: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class IntegrityReport:
    """A rolled-up integrity report over a time window for a player.

    Attributes:
        report_id: Unique identifier for the report.
        player_id: The player the report covers.
        period_start: ISO-8601 start of the reporting window (empty = unbounded).
        period_end: ISO-8601 end of the reporting window (empty = unbounded).
        total_scans: Number of scans in the window.
        total_violations: Number of violations in the window.
        violations_by_type: Violation counts keyed by ViolationType value.
        risk_assessment: Textual risk assessment (low/moderate/high/critical).
        recommendations: List of recommended follow-up actions.
        generated_at: ISO-8601 timestamp the report was generated.
    """

    report_id: str = field(default_factory=lambda: _new_id("report"))
    player_id: str = ""
    period_start: str = ""
    period_end: str = ""
    total_scans: int = 0
    total_violations: int = 0
    violations_by_type: Dict[str, int] = field(default_factory=dict)
    risk_assessment: str = ""
    recommendations: List[str] = field(default_factory=list)
    generated_at: str = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class IntegrityStats:
    """Aggregate counters describing the whole integrity system.

    Attributes:
        total_players: Number of registered players.
        total_scans: Number of scans recorded.
        total_violations: Number of violations recorded.
        total_bans: Number of players currently banned.
        total_flags: Number of players currently flagged.
        active_alerts: Number of unacknowledged alerts.
        avg_risk_score: Mean player risk score.
        violation_distribution: Violation counts keyed by ViolationType value.
        last_updated: ISO-8601 timestamp the stats were computed.
    """

    total_players: int = 0
    total_scans: int = 0
    total_violations: int = 0
    total_bans: int = 0
    total_flags: int = 0
    active_alerts: int = 0
    avg_risk_score: float = 0.0
    violation_distribution: Dict[str, int] = field(default_factory=dict)
    last_updated: str = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class IntegritySnapshot:
    """An immutable snapshot of the entire integrity system state.

    Each collection field holds a list of serialized dicts (capped at 100
    entries) so the snapshot is cheap to serialize and inspect.

    Attributes:
        rules: Serialized IntegrityRule entries.
        scans: Serialized ScanResult entries.
        violations: Serialized Violation entries.
        players: Serialized PlayerIntegrity entries.
        alerts: Serialized IntegrityAlert entries.
        reports: Serialized IntegrityReport entries.
        stats: Serialized IntegrityStats.
        timestamp: ISO-8601 timestamp the snapshot was taken.
    """

    rules: List[Dict[str, Any]] = field(default_factory=list)
    scans: List[Dict[str, Any]] = field(default_factory=list)
    violations: List[Dict[str, Any]] = field(default_factory=list)
    players: List[Dict[str, Any]] = field(default_factory=list)
    alerts: List[Dict[str, Any]] = field(default_factory=list)
    reports: List[Dict[str, Any]] = field(default_factory=list)
    stats: Dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class IntegrityLogEvent:
    """An audit log entry emitted by the integrity system.

    Attributes:
        event_id: Unique identifier for the event.
        kind: The IntegrityEventKind classification.
        player_id: The player the event concerns (empty when not applicable).
        timestamp: ISO-8601 timestamp the event was emitted.
        payload: Free-form event payload.
    """

    event_id: str = field(default_factory=lambda: _new_id("evt"))
    kind: IntegrityEventKind = IntegrityEventKind.SCAN_STARTED
    player_id: str = ""
    timestamp: str = field(default_factory=_now)
    payload: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


# ---------------------------------------------------------------------------
# Integrity Guard System
# ---------------------------------------------------------------------------


class IntegrityGuardSystem:
    """Anti-cheat and game integrity verification system (singleton).

    Holds rules, scans, violations, players, alerts, reports, and an audit
    event log in bounded in-memory stores guarded by a reentrant lock. All
    public methods acquire ``self._lock`` so the system is safe to call from
    multiple threads.
    """

    _instance: Optional["IntegrityGuardSystem"] = None
    _inner_lock = threading.RLock()
    _initialized: bool = False

    def __new__(cls) -> "IntegrityGuardSystem":
        if cls._instance is None:
            with cls._inner_lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self) -> None:
        with self._inner_lock:  # use _inner_lock; self._lock does not exist yet
            if self._initialized:
                return
            self._lock = threading.RLock()  # instance attribute set here
            # Primary stores keyed by their respective identifiers.
            self._rules: Dict[str, IntegrityRule] = {}
            self._scans: Dict[str, ScanResult] = {}
            self._violations: Dict[str, Violation] = {}
            self._players: Dict[str, PlayerIntegrity] = {}
            self._alerts: Dict[str, IntegrityAlert] = {}
            self._reports: Dict[str, IntegrityReport] = {}
            # Audit log stored as a chronological list (oldest first).
            self._events: List[IntegrityLogEvent] = []

            self._initialized = True
            self._seed_data()

    # ------------------------------------------------------------------
    # Event Helpers
    # ------------------------------------------------------------------

    def _emit(
        self,
        kind: IntegrityEventKind,
        player_id: str = "",
        payload: Optional[Dict[str, Any]] = None,
    ) -> IntegrityLogEvent:
        """Append an audit event to the in-memory event log."""
        event = IntegrityLogEvent(
            event_id=_new_id("evt"),
            kind=kind,
            player_id=player_id,
            timestamp=_now(),
            payload=payload or {},
        )
        self._events.append(event)
        _evict_fifo_list(self._events, _MAX_EVENTS)
        return event

    # ------------------------------------------------------------------
    # Internal Helpers
    # ------------------------------------------------------------------

    def _ensure_player(self, player_id: str) -> PlayerIntegrity:
        """Return the integrity record for ``player_id``, creating it if missing."""
        player = self._players.get(player_id)
        if player is not None:
            return player
        player = PlayerIntegrity(player_id=player_id)
        self._players[player_id] = player
        _evict_fifo_dict(self._players, _MAX_PLAYERS)
        return player

    def _find_rule_for(
        self, violation_type: ViolationType, detection_method: DetectionMethod
    ) -> Optional[IntegrityRule]:
        """Find the best-matching rule for a violation type and method.

        Prefers an exact match on both violation type and detection method,
        falling back to the first rule sharing the violation type.
        """
        partial: Optional[IntegrityRule] = None
        for rule in self._rules.values():
            if rule.violation_type != violation_type:
                continue
            if rule.detection_method == detection_method:
                return rule
            if partial is None:
                partial = rule
        return partial

    def _recommendations_for(
        self, player: PlayerIntegrity, assessment: str
    ) -> List[str]:
        """Build a list of recommended follow-up actions for a player."""
        recs: List[str] = []
        if player.status == PlayerStatus.BANNED:
            recs.append("Keep the account banned until a manual review completes.")
            recs.append("Roll back any ill-gotten gains tied to the violation.")
        elif player.status == PlayerStatus.FLAGGED:
            recs.append("Raise scan frequency for this account.")
            recs.append("Monitor network traffic for repeat offenses.")
        elif assessment in ("high", "critical"):
            recs.append("Apply soft restrictions pending a deeper review.")
            recs.append("Track the account across the next several sessions.")
        else:
            recs.append("No action needed. Continue routine scanning.")
        return recs

    # ------------------------------------------------------------------
    # Seeding
    # ------------------------------------------------------------------

    def _seed_data(self) -> None:
        """Populate the engine with seed rules, scans, violations, players, alerts, and a report."""
        # --- Rules: 5 ---
        rule1 = IntegrityRule(
            rule_id="rule_seed_1",
            name="Speed Hack Detector",
            violation_type=ViolationType.SPEED_HACK,
            detection_method=DetectionMethod.STATISTICAL,
            threshold=1.5,
            sensitivity=0.8,
            enabled=True,
            description="Flags movement speed exceeding the legitimate maximum.",
            created_at=_now(),
            updated_at=_now(),
            trigger_count=3,
        )
        rule2 = IntegrityRule(
            rule_id="rule_seed_2",
            name="Memory Edit Sentinel",
            violation_type=ViolationType.MEMORY_EDIT,
            detection_method=DetectionMethod.MEMORY_SCAN,
            threshold=0.9,
            sensitivity=0.9,
            enabled=True,
            description="Detects tampered process memory regions.",
            created_at=_now(),
            updated_at=_now(),
            trigger_count=2,
        )
        rule3 = IntegrityRule(
            rule_id="rule_seed_3",
            name="Aim Bot Behavior",
            violation_type=ViolationType.AIM_BOT,
            detection_method=DetectionMethod.BEHAVIORAL,
            threshold=0.85,
            sensitivity=0.85,
            enabled=True,
            description="Spots unnatural aiming patterns and snap-to-target clicks.",
            created_at=_now(),
            updated_at=_now(),
            trigger_count=1,
        )
        rule4 = IntegrityRule(
            rule_id="rule_seed_4",
            name="Item Duplication Guard",
            violation_type=ViolationType.DUP_ITEM,
            detection_method=DetectionMethod.SERVER_VALIDATION,
            threshold=0.95,
            sensitivity=0.9,
            enabled=True,
            description="Validates inventory state against the server ledger.",
            created_at=_now(),
            updated_at=_now(),
            trigger_count=1,
        )
        rule5 = IntegrityRule(
            rule_id="rule_seed_5",
            name="Client Modification Check",
            violation_type=ViolationType.CLIENT_MODIFICATION,
            detection_method=DetectionMethod.SIGNATURE,
            threshold=0.9,
            sensitivity=0.95,
            enabled=True,
            description="Matches known modified-client file signatures.",
            created_at=_now(),
            updated_at=_now(),
            trigger_count=0,
        )
        for rule in (rule1, rule2, rule3, rule4, rule5):
            self._rules[rule.rule_id] = rule

        # --- Players: 3 (1 clean, 1 flagged, 1 banned) ---
        player1 = PlayerIntegrity(
            player_id="player_seed_1",
            status=PlayerStatus.CLEAN,
            violation_count=2,
            last_scan_at=_now(),
            last_violation_at=_now(),
            risk_score=15.0,
            banned_until="",
            ban_reason="",
            flagged_at="",
            cleared_at=_now(),
            history=[
                {"event": "violation_recorded", "violation_type": "speed_hack", "severity": "medium", "timestamp": _now()},
                {"event": "violation_resolved", "violation_type": "speed_hack", "timestamp": _now()},
                {"event": "cleared", "timestamp": _now()},
            ],
        )
        player2 = PlayerIntegrity(
            player_id="player_seed_2",
            status=PlayerStatus.FLAGGED,
            violation_count=1,
            last_scan_at=_now(),
            last_violation_at=_now(),
            risk_score=65.0,
            banned_until="",
            ban_reason="",
            flagged_at=_now(),
            cleared_at="",
            history=[
                {"event": "violation_recorded", "violation_type": "aim_bot", "severity": "high", "timestamp": _now()},
                {"event": "flagged", "reason": "Aim bot suspicion", "timestamp": _now()},
            ],
        )
        player3 = PlayerIntegrity(
            player_id="player_seed_3",
            status=PlayerStatus.BANNED,
            violation_count=1,
            last_scan_at=_now(),
            last_violation_at=_now(),
            risk_score=95.0,
            banned_until="",  # empty means permanent
            ban_reason="Duplicate item exploitation",
            flagged_at=_now(),
            cleared_at="",
            history=[
                {"event": "violation_recorded", "violation_type": "dup_item", "severity": "critical", "timestamp": _now()},
                {"event": "banned", "reason": "Duplicate item exploitation", "duration_hours": 0, "timestamp": _now()},
            ],
        )
        self._players[player1.player_id] = player1
        self._players[player2.player_id] = player2
        self._players[player3.player_id] = player3

        # --- Scans: 3 (all completed) ---
        scan1 = ScanResult(
            scan_id="scan_seed_1",
            player_id="player_seed_1",
            started_at=_now(),
            completed_at=_now(),
            rules_evaluated=5,
            violations_found=2,
            status="completed",
            details="Routine scan completed; two historical violations reviewed.",
        )
        scan2 = ScanResult(
            scan_id="scan_seed_2",
            player_id="player_seed_2",
            started_at=_now(),
            completed_at=_now(),
            rules_evaluated=5,
            violations_found=1,
            status="completed",
            details="Behavioral scan surfaced an aim bot pattern.",
        )
        scan3 = ScanResult(
            scan_id="scan_seed_3",
            player_id="player_seed_3",
            started_at=_now(),
            completed_at=_now(),
            rules_evaluated=5,
            violations_found=1,
            status="completed",
            details="Server validation detected duplicated inventory items.",
        )
        self._scans[scan1.scan_id] = scan1
        self._scans[scan2.scan_id] = scan2
        self._scans[scan3.scan_id] = scan3

        # --- Violations: 4 (2 resolved, 2 active) ---
        viol1 = Violation(
            violation_id="viol_seed_1",
            scan_id="scan_seed_1",
            player_id="player_seed_1",
            violation_type=ViolationType.SPEED_HACK,
            detection_method=DetectionMethod.STATISTICAL,
            severity=SeverityLevel.MEDIUM,
            confidence=0.82,
            description="Movement speed exceeded the cap by 45%.",
            detected_at=_now(),
            evidence={"max_speed": 1.45, "cap": 1.0, "samples": 12},
            action_taken=ActionTaken.WARN,
            resolved=True,
            resolved_at=_now(),
        )
        viol2 = Violation(
            violation_id="viol_seed_2",
            scan_id="scan_seed_1",
            player_id="player_seed_1",
            violation_type=ViolationType.MEMORY_EDIT,
            detection_method=DetectionMethod.MEMORY_SCAN,
            severity=SeverityLevel.LOW,
            confidence=0.71,
            description="A single tampered memory region was found and reverted.",
            detected_at=_now(),
            evidence={"region": "0x004A1F20", "bytes_changed": 4},
            action_taken=ActionTaken.WARN,
            resolved=True,
            resolved_at=_now(),
        )
        viol3 = Violation(
            violation_id="viol_seed_3",
            scan_id="scan_seed_2",
            player_id="player_seed_2",
            violation_type=ViolationType.AIM_BOT,
            detection_method=DetectionMethod.BEHAVIORAL,
            severity=SeverityLevel.HIGH,
            confidence=0.91,
            description="Snap-to-target aim pattern detected across 30 seconds of play.",
            detected_at=_now(),
            evidence={"snap_events": 18, "window_seconds": 30},
            action_taken=ActionTaken.FLAG,
            resolved=False,
            resolved_at="",
        )
        viol4 = Violation(
            violation_id="viol_seed_4",
            scan_id="scan_seed_3",
            player_id="player_seed_3",
            violation_type=ViolationType.DUP_ITEM,
            detection_method=DetectionMethod.SERVER_VALIDATION,
            severity=SeverityLevel.CRITICAL,
            confidence=0.97,
            description="Inventory contained duplicated items absent from the server ledger.",
            detected_at=_now(),
            evidence={"item_id": "item_orb_001", "expected": 1, "found": 5},
            action_taken=ActionTaken.PERMA_BAN,
            resolved=False,
            resolved_at="",
        )
        self._violations[viol1.violation_id] = viol1
        self._violations[viol2.violation_id] = viol2
        self._violations[viol3.violation_id] = viol3
        self._violations[viol4.violation_id] = viol4

        # --- Alerts: 2 (1 acknowledged, 1 not) ---
        alert1 = IntegrityAlert(
            alert_id="alert_seed_1",
            player_id="player_seed_2",
            violation_type=ViolationType.AIM_BOT,
            severity=SeverityLevel.HIGH,
            message="Aim bot pattern flagged for review.",
            created_at=_now(),
            acknowledged=True,
            acknowledged_by="admin_1",
            acknowledged_at=_now(),
        )
        alert2 = IntegrityAlert(
            alert_id="alert_seed_2",
            player_id="player_seed_3",
            violation_type=ViolationType.DUP_ITEM,
            severity=SeverityLevel.CRITICAL,
            message="Item duplication confirmed; account frozen.",
            created_at=_now(),
            acknowledged=False,
            acknowledged_by="",
            acknowledged_at="",
        )
        self._alerts[alert1.alert_id] = alert1
        self._alerts[alert2.alert_id] = alert2

        # --- Report: 1 ---
        report1 = IntegrityReport(
            report_id="report_seed_1",
            player_id="player_seed_2",
            period_start="",
            period_end="",
            total_scans=1,
            total_violations=1,
            violations_by_type={ViolationType.AIM_BOT.value: 1},
            risk_assessment="high",
            recommendations=[
                "Raise scan frequency for this account.",
                "Monitor network traffic for repeat offenses.",
            ],
            generated_at=_now(),
        )
        self._reports[report1.report_id] = report1

    # ------------------------------------------------------------------
    # Rule Management
    # ------------------------------------------------------------------

    def add_rule(
        self,
        name: str,
        violation_type: ViolationType,
        detection_method: DetectionMethod,
        threshold: float = 1.0,
        sensitivity: float = 0.5,
        description: str = "",
    ) -> IntegrityRule:
        """Create and register a new integrity rule."""
        with self._lock:
            rule = IntegrityRule(
                rule_id=_new_id("rule"),
                name=name,
                violation_type=violation_type,
                detection_method=detection_method,
                threshold=float(threshold),
                sensitivity=float(sensitivity),
                enabled=True,
                description=description,
                created_at=_now(),
                updated_at=_now(),
                trigger_count=0,
            )
            self._rules[rule.rule_id] = rule
            _evict_fifo_dict(self._rules, _MAX_RULES)
            self._emit(
                IntegrityEventKind.RULE_ADDED,
                payload={
                    "rule_id": rule.rule_id,
                    "name": name,
                    "violation_type": violation_type.value,
                    "detection_method": detection_method.value,
                },
            )
            return rule

    def get_rule(self, rule_id: str) -> Optional[IntegrityRule]:
        """Return the rule with the given id, or ``None`` if not found."""
        with self._lock:
            return self._rules.get(rule_id)

    def list_rules(
        self,
        violation_type: Optional[ViolationType] = None,
        enabled: Optional[bool] = None,
        limit: int = 100,
    ) -> List[IntegrityRule]:
        """List rules filtered by violation type and/or enabled state."""
        with self._lock:
            cap = max(1, min(int(limit), _MAX_RULES))
            results: List[IntegrityRule] = []
            for rule in self._rules.values():
                if violation_type is not None and rule.violation_type != violation_type:
                    continue
                if enabled is not None and rule.enabled != enabled:
                    continue
                results.append(rule)
                if len(results) >= cap:
                    break
            return results

    def update_rule(self, rule_id: str, **kwargs: Any) -> Optional[IntegrityRule]:
        """Update mutable fields on a rule.

        Only ``name``, ``violation_type``, ``detection_method``, ``threshold``,
        ``sensitivity``, ``enabled``, and ``description`` may be updated. Unknown
        keys are ignored. Returns the updated rule, or ``None`` if not found.
        """
        with self._lock:
            rule = self._rules.get(rule_id)
            if rule is None:
                return None
            allowed = {
                "name",
                "violation_type",
                "detection_method",
                "threshold",
                "sensitivity",
                "enabled",
                "description",
            }
            threshold_changed = False
            for key, value in kwargs.items():
                if key not in allowed:
                    continue
                setattr(rule, key, value)
                if key == "threshold":
                    threshold_changed = True
            rule.updated_at = _now()
            if threshold_changed:
                self._emit(
                    IntegrityEventKind.THRESHOLD_UPDATED,
                    payload={"rule_id": rule_id, "threshold": rule.threshold},
                )
            return rule

    def remove_rule(self, rule_id: str) -> bool:
        """Remove a rule. Returns ``True`` if removed, ``False`` if not found."""
        with self._lock:
            if rule_id not in self._rules:
                return False
            self._rules.pop(rule_id, None)
            self._emit(
                IntegrityEventKind.RULE_REMOVED,
                payload={"rule_id": rule_id},
            )
            return True

    # ------------------------------------------------------------------
    # Scan Management
    # ------------------------------------------------------------------

    def start_scan(self, player_id: str) -> ScanResult:
        """Start a new scan for ``player_id``, registering the player if needed."""
        with self._lock:
            self._ensure_player(player_id)
            scan = ScanResult(
                scan_id=_new_id("scan"),
                player_id=player_id,
                started_at=_now(),
                completed_at="",
                rules_evaluated=len(self._rules),
                violations_found=0,
                status="running",
                details="",
            )
            self._scans[scan.scan_id] = scan
            _evict_fifo_dict(self._scans, _MAX_SCANS)
            self._emit(
                IntegrityEventKind.SCAN_STARTED,
                player_id=player_id,
                payload={
                    "scan_id": scan.scan_id,
                    "rules_evaluated": scan.rules_evaluated,
                },
            )
            return scan

    def get_scan(self, scan_id: str) -> Optional[ScanResult]:
        """Return the scan with the given id, or ``None`` if not found."""
        with self._lock:
            return self._scans.get(scan_id)

    def list_scans(
        self,
        player_id: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 100,
    ) -> List[ScanResult]:
        """List scans filtered by player and/or status."""
        with self._lock:
            cap = max(1, min(int(limit), _MAX_SCANS))
            results: List[ScanResult] = []
            for scan in self._scans.values():
                if player_id is not None and scan.player_id != player_id:
                    continue
                if status is not None and scan.status != status:
                    continue
                results.append(scan)
                if len(results) >= cap:
                    break
            return results

    def complete_scan(
        self,
        scan_id: str,
        violations_found: int = 0,
        details: str = "",
    ) -> ScanResult:
        """Mark a scan as completed with the given violation count and details.

        Raises ``ValueError`` if the scan is not found.
        """
        with self._lock:
            scan = self._scans.get(scan_id)
            if scan is None:
                raise ValueError(f"Scan not found: {scan_id}")
            scan.completed_at = _now()
            scan.violations_found = int(violations_found)
            scan.status = "completed"
            scan.details = details
            player = self._players.get(scan.player_id)
            if player is not None:
                player.last_scan_at = scan.completed_at
            self._emit(
                IntegrityEventKind.SCAN_COMPLETED,
                player_id=scan.player_id,
                payload={
                    "scan_id": scan_id,
                    "violations_found": int(violations_found),
                },
            )
            return scan

    # ------------------------------------------------------------------
    # Violation Management
    # ------------------------------------------------------------------

    def record_violation(
        self,
        scan_id: str,
        player_id: str,
        violation_type: ViolationType,
        detection_method: DetectionMethod,
        severity: SeverityLevel,
        confidence: float = 0.5,
        description: str = "",
        evidence: Optional[Dict[str, Any]] = None,
        action_taken: ActionTaken = ActionTaken.NONE,
    ) -> Violation:
        """Record a new violation and update the player's standing.

        Increases the player's violation count, refreshes their last-violation
        timestamp, adds the severity weight to their risk score (capped at 100),
        marks them suspicious if currently clean, and bumps the matching rule's
        trigger count when one exists.
        """
        with self._lock:
            player = self._ensure_player(player_id)
            violation = Violation(
                violation_id=_new_id("viol"),
                scan_id=scan_id,
                player_id=player_id,
                violation_type=violation_type,
                detection_method=detection_method,
                severity=severity,
                confidence=float(confidence),
                description=description,
                detected_at=_now(),
                evidence=evidence or {},
                action_taken=action_taken,
                resolved=False,
                resolved_at="",
            )
            self._violations[violation.violation_id] = violation
            _evict_fifo_dict(self._violations, _MAX_VIOLATIONS)

            # Update player aggregates and risk score.
            player.violation_count += 1
            player.last_violation_at = violation.detected_at
            weight = _SEVERITY_WEIGHTS.get(severity, 0.0)
            player.risk_score = round(min(100.0, player.risk_score + weight), 2)
            if player.status == PlayerStatus.CLEAN:
                player.status = PlayerStatus.SUSPICIOUS
            player.history.append(
                {
                    "event": "violation_recorded",
                    "violation_id": violation.violation_id,
                    "violation_type": violation_type.value,
                    "severity": severity.value,
                    "timestamp": violation.detected_at,
                }
            )

            # Bump the matching rule's trigger count.
            matched_rule = self._find_rule_for(violation_type, detection_method)
            if matched_rule is not None:
                matched_rule.trigger_count += 1
                matched_rule.updated_at = _now()

            self._emit(
                IntegrityEventKind.VIOLATION_DETECTED,
                player_id=player_id,
                payload={
                    "violation_id": violation.violation_id,
                    "scan_id": scan_id,
                    "violation_type": violation_type.value,
                    "severity": severity.value,
                    "confidence": violation.confidence,
                },
            )
            return violation

    def get_violation(self, violation_id: str) -> Optional[Violation]:
        """Return the violation with the given id, or ``None`` if not found."""
        with self._lock:
            return self._violations.get(violation_id)

    def list_violations(
        self,
        player_id: Optional[str] = None,
        violation_type: Optional[ViolationType] = None,
        severity: Optional[SeverityLevel] = None,
        resolved: Optional[bool] = None,
        limit: int = 100,
    ) -> List[Violation]:
        """List violations filtered by player, type, severity, and/or state."""
        with self._lock:
            cap = max(1, min(int(limit), _MAX_VIOLATIONS))
            results: List[Violation] = []
            for violation in self._violations.values():
                if player_id is not None and violation.player_id != player_id:
                    continue
                if violation_type is not None and violation.violation_type != violation_type:
                    continue
                if severity is not None and violation.severity != severity:
                    continue
                if resolved is not None and violation.resolved != resolved:
                    continue
                results.append(violation)
                if len(results) >= cap:
                    break
            return results

    def resolve_violation(self, violation_id: str) -> Violation:
        """Mark a violation as resolved and refund its risk weight to the player.

        Raises ``ValueError`` if the violation is not found.
        """
        with self._lock:
            violation = self._violations.get(violation_id)
            if violation is None:
                raise ValueError(f"Violation not found: {violation_id}")
            violation.resolved = True
            violation.resolved_at = _now()
            player = self._players.get(violation.player_id)
            if player is not None:
                weight = _SEVERITY_WEIGHTS.get(violation.severity, 0.0)
                player.risk_score = round(max(0.0, player.risk_score - weight), 2)
                player.history.append(
                    {
                        "event": "violation_resolved",
                        "violation_id": violation_id,
                        "timestamp": violation.resolved_at,
                    }
                )
            self._emit(
                IntegrityEventKind.VIOLATION_RESOLVED,
                player_id=violation.player_id,
                payload={"violation_id": violation_id},
            )
            return violation

    # ------------------------------------------------------------------
    # Player Management
    # ------------------------------------------------------------------

    def register_player(self, player_id: str) -> PlayerIntegrity:
        """Register a player if missing and return their integrity record."""
        with self._lock:
            return self._ensure_player(player_id)

    def get_player(self, player_id: str) -> Optional[PlayerIntegrity]:
        """Return the integrity record for ``player_id``, or ``None`` if not found."""
        with self._lock:
            return self._players.get(player_id)

    def list_players(
        self,
        status: Optional[PlayerStatus] = None,
        limit: int = 100,
    ) -> List[PlayerIntegrity]:
        """List players filtered by status."""
        with self._lock:
            cap = max(1, min(int(limit), _MAX_PLAYERS))
            results: List[PlayerIntegrity] = []
            for player in self._players.values():
                if status is not None and player.status != status:
                    continue
                results.append(player)
                if len(results) >= cap:
                    break
            return results

    def flag_player(self, player_id: str, reason: str = "") -> PlayerIntegrity:
        """Flag a player for review, registering them if needed."""
        with self._lock:
            player = self._ensure_player(player_id)
            player.status = PlayerStatus.FLAGGED
            player.flagged_at = _now()
            player.history.append(
                {
                    "event": "flagged",
                    "reason": reason,
                    "timestamp": player.flagged_at,
                }
            )
            self._emit(
                IntegrityEventKind.PLAYER_FLAGGED,
                player_id=player_id,
                payload={"reason": reason},
            )
            return player

    def ban_player(self, player_id: str, duration_hours: int = 0, reason: str = "") -> PlayerIntegrity:
        """Ban a player. ``duration_hours=0`` means a permanent ban.

        Registers the player if needed. For a timed ban, ``banned_until`` is set
        to an ISO-8601 expiry timestamp; for a permanent ban it is left empty.
        """
        with self._lock:
            player = self._ensure_player(player_id)
            player.status = PlayerStatus.BANNED
            player.ban_reason = reason
            if duration_hours and duration_hours > 0:
                player.banned_until = _iso_from_now(float(duration_hours))
            else:
                player.banned_until = ""  # permanent
            player.history.append(
                {
                    "event": "banned",
                    "reason": reason,
                    "duration_hours": int(duration_hours),
                    "banned_until": player.banned_until,
                    "timestamp": _now(),
                }
            )
            self._emit(
                IntegrityEventKind.PLAYER_BANNED,
                player_id=player_id,
                payload={
                    "reason": reason,
                    "duration_hours": int(duration_hours),
                    "permanent": duration_hours == 0,
                },
            )
            return player

    def clear_player(self, player_id: str) -> PlayerIntegrity:
        """Clear a player, marking their standing as cleared."""
        with self._lock:
            player = self._ensure_player(player_id)
            player.status = PlayerStatus.CLEARED
            player.cleared_at = _now()
            player.banned_until = ""
            player.ban_reason = ""
            player.history.append(
                {
                    "event": "cleared",
                    "timestamp": player.cleared_at,
                }
            )
            self._emit(
                IntegrityEventKind.PLAYER_CLEARED,
                player_id=player_id,
                payload={},
            )
            return player

    # ------------------------------------------------------------------
    # Alert Management
    # ------------------------------------------------------------------

    def issue_alert(
        self,
        player_id: str,
        violation_type: ViolationType,
        severity: SeverityLevel,
        message: str = "",
    ) -> IntegrityAlert:
        """Issue a new alert for a player, registering them if needed."""
        with self._lock:
            self._ensure_player(player_id)
            alert = IntegrityAlert(
                alert_id=_new_id("alert"),
                player_id=player_id,
                violation_type=violation_type,
                severity=severity,
                message=message,
                created_at=_now(),
                acknowledged=False,
                acknowledged_by="",
                acknowledged_at="",
            )
            self._alerts[alert.alert_id] = alert
            _evict_fifo_dict(self._alerts, _MAX_ALERTS)
            self._emit(
                IntegrityEventKind.ALERT_ISSUED,
                player_id=player_id,
                payload={
                    "alert_id": alert.alert_id,
                    "violation_type": violation_type.value,
                    "severity": severity.value,
                },
            )
            return alert

    def get_alert(self, alert_id: str) -> Optional[IntegrityAlert]:
        """Return the alert with the given id, or ``None`` if not found."""
        with self._lock:
            return self._alerts.get(alert_id)

    def list_alerts(
        self,
        player_id: Optional[str] = None,
        acknowledged: Optional[bool] = None,
        limit: int = 100,
    ) -> List[IntegrityAlert]:
        """List alerts filtered by player and/or acknowledged state."""
        with self._lock:
            cap = max(1, min(int(limit), _MAX_ALERTS))
            results: List[IntegrityAlert] = []
            for alert in self._alerts.values():
                if player_id is not None and alert.player_id != player_id:
                    continue
                if acknowledged is not None and alert.acknowledged != acknowledged:
                    continue
                results.append(alert)
                if len(results) >= cap:
                    break
            return results

    def acknowledge_alert(self, alert_id: str, acknowledged_by: str) -> IntegrityAlert:
        """Mark an alert as acknowledged by ``acknowledged_by``.

        Raises ``ValueError`` if the alert is not found.
        """
        with self._lock:
            alert = self._alerts.get(alert_id)
            if alert is None:
                raise ValueError(f"Alert not found: {alert_id}")
            alert.acknowledged = True
            alert.acknowledged_by = acknowledged_by
            alert.acknowledged_at = _now()
            return alert

    # ------------------------------------------------------------------
    # Reporting
    # ------------------------------------------------------------------

    def generate_report(
        self,
        player_id: str,
        period_start: str = "",
        period_end: str = "",
    ) -> IntegrityReport:
        """Generate a rolled-up integrity report for a player over a window.

        Empty ``period_start`` or ``period_end`` bounds are treated as unbounded
        on that side. Registers the player if needed.
        """
        with self._lock:
            player = self._ensure_player(player_id)

            scans_count = 0
            for scan in self._scans.values():
                if scan.player_id != player_id:
                    continue
                if _in_period(scan.started_at, period_start, period_end):
                    scans_count += 1

            violations_count = 0
            by_type: Dict[str, int] = {}
            for violation in self._violations.values():
                if violation.player_id != player_id:
                    continue
                if _in_period(violation.detected_at, period_start, period_end):
                    violations_count += 1
                    key = violation.violation_type.value
                    by_type[key] = by_type.get(key, 0) + 1

            risk = player.risk_score
            if risk < 25.0:
                assessment = "low"
            elif risk < 50.0:
                assessment = "moderate"
            elif risk < 75.0:
                assessment = "high"
            else:
                assessment = "critical"

            recommendations = self._recommendations_for(player, assessment)

            report = IntegrityReport(
                report_id=_new_id("report"),
                player_id=player_id,
                period_start=period_start,
                period_end=period_end,
                total_scans=scans_count,
                total_violations=violations_count,
                violations_by_type=by_type,
                risk_assessment=assessment,
                recommendations=recommendations,
                generated_at=_now(),
            )
            self._reports[report.report_id] = report
            _evict_fifo_dict(self._reports, _MAX_REPORTS)
            self._emit(
                IntegrityEventKind.REPORT_GENERATED,
                player_id=player_id,
                payload={
                    "report_id": report.report_id,
                    "total_scans": scans_count,
                    "total_violations": violations_count,
                    "risk_assessment": assessment,
                },
            )
            return report

    def get_report(self, report_id: str) -> Optional[IntegrityReport]:
        """Return the report with the given id, or ``None`` if not found."""
        with self._lock:
            return self._reports.get(report_id)

    def list_reports(
        self,
        player_id: Optional[str] = None,
        limit: int = 100,
    ) -> List[IntegrityReport]:
        """List reports filtered by player."""
        with self._lock:
            cap = max(1, min(int(limit), _MAX_REPORTS))
            results: List[IntegrityReport] = []
            for report in self._reports.values():
                if player_id is not None and report.player_id != player_id:
                    continue
                results.append(report)
                if len(results) >= cap:
                    break
            return results

    # ------------------------------------------------------------------
    # Observability and State
    # ------------------------------------------------------------------

    def list_events(
        self,
        limit: int = 100,
        kind: Optional[IntegrityEventKind] = None,
    ) -> List[IntegrityLogEvent]:
        """List audit events filtered by event kind."""
        with self._lock:
            cap = max(1, min(int(limit), _MAX_EVENTS))
            results: List[IntegrityLogEvent] = []
            for event in self._events:
                if kind is not None and event.kind != kind:
                    continue
                results.append(event)
                if len(results) >= cap:
                    break
            return results

    def get_stats(self) -> IntegrityStats:
        """Compute and return aggregate statistics for the integrity system."""
        with self._lock:
            total_players = len(self._players)
            total_bans = sum(
                1 for p in self._players.values() if p.status == PlayerStatus.BANNED
            )
            total_flags = sum(
                1 for p in self._players.values() if p.status == PlayerStatus.FLAGGED
            )
            active_alerts = sum(
                1 for a in self._alerts.values() if not a.acknowledged
            )
            avg_risk = 0.0
            if total_players > 0:
                avg_risk = round(
                    sum(p.risk_score for p in self._players.values()) / total_players,
                    2,
                )
            distribution: Dict[str, int] = {}
            for violation in self._violations.values():
                key = violation.violation_type.value
                distribution[key] = distribution.get(key, 0) + 1
            return IntegrityStats(
                total_players=total_players,
                total_scans=len(self._scans),
                total_violations=len(self._violations),
                total_bans=total_bans,
                total_flags=total_flags,
                active_alerts=active_alerts,
                avg_risk_score=avg_risk,
                violation_distribution=distribution,
                last_updated=_now(),
            )

    def get_status(self) -> Dict[str, Any]:
        """Return a status dictionary describing the current system state."""
        with self._lock:
            return {
                "initialized": self._initialized,
                "rules": len(self._rules),
                "scans": len(self._scans),
                "violations": len(self._violations),
                "players": len(self._players),
                "alerts": len(self._alerts),
                "reports": len(self._reports),
                "events": len(self._events),
                "capacities": {
                    "max_rules": _MAX_RULES,
                    "max_scans": _MAX_SCANS,
                    "max_violations": _MAX_VIOLATIONS,
                    "max_players": _MAX_PLAYERS,
                    "max_alerts": _MAX_ALERTS,
                    "max_reports": _MAX_REPORTS,
                    "max_events": _MAX_EVENTS,
                },
            }

    def get_snapshot(self) -> IntegritySnapshot:
        """Return an immutable snapshot of the entire system state."""
        with self._lock:
            stats = self.get_stats()
            return IntegritySnapshot(
                rules=[r.to_dict() for r in list(self._rules.values())[:100]],
                scans=[s.to_dict() for s in list(self._scans.values())[:100]],
                violations=[v.to_dict() for v in list(self._violations.values())[:100]],
                players=[p.to_dict() for p in list(self._players.values())[:100]],
                alerts=[a.to_dict() for a in list(self._alerts.values())[:100]],
                reports=[rep.to_dict() for rep in list(self._reports.values())[:100]],
                stats=stats.to_dict(),
                timestamp=_now(),
            )

    def reset(self) -> None:
        """Clear all stores and re-seed the engine with default data."""
        with self._lock:
            self._rules.clear()
            self._scans.clear()
            self._violations.clear()
            self._players.clear()
            self._alerts.clear()
            self._reports.clear()
            self._events.clear()
            self._seed_data()


# ---------------------------------------------------------------------------
# Factory Function
# ---------------------------------------------------------------------------


def get_integrity_guard() -> IntegrityGuardSystem:
    """Factory function returning the singleton IntegrityGuardSystem instance."""
    return IntegrityGuardSystem()
