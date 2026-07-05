"""
SparkLabs Agent - AI Emergent Gameplay Detector

An agent for the SparkLabs AI-native game engine that monitors live
gameplay sessions to detect emergent patterns - unexpected player
strategies, creative solutions, exploit attempts, and novel interactions.
The detector analyzes player action sequences, identifies statistical
anomalies, categorizes emergent behaviors, and feeds insights back to
the design loop so the engine can adapt and evolve.

Architecture:
  EmergentGameplayDetector (singleton)
    |-- GameplaySession, PlayerAction, EmergentPattern, DetectionRule,
       EmergenceInsight, DetectorStats, DetectorSnapshot, DetectorEvent
    |-- ActionType, PatternCategory, PatternSeverity, DetectionMethod,
       PatternStatus, DetectorEventKind

Core Capabilities:
  - start_session / end_session / get_session / list_sessions: gameplay
    session lifecycle management.
  - record_action / get_action / list_actions: player action stream
    ingestion with context and outcome tracking.
  - register_rule / get_rule / list_rules / remove_rule: custom
    detection rules with conditions and thresholds.
  - detect_patterns / get_pattern / list_patterns: emergent pattern
    detection and classification.
  - classify_pattern / resolve_pattern: pattern categorization and
    lifecycle management.
  - generate_insight / get_insight / list_insights: design insights
    derived from detected patterns.
  - list_events / get_stats / get_status / get_snapshot / reset:
    observability and state management.

The class implements the singleton pattern with double-checked locking
using ``threading.RLock``; consumers should obtain the instance through
:meth:`EmergentGameplayDetector.get_instance` or the module-level
:func:`get_emergent_gameplay_detector` factory.
"""

from __future__ import annotations

import threading
import uuid
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple


# ---------------------------------------------------------------------------
# Capacity Constants
# ---------------------------------------------------------------------------

_MAX_SESSIONS: int = 500
_MAX_ACTIONS: int = 10000
_MAX_PATTERNS: int = 3000
_MAX_RULES: int = 500
_MAX_INSIGHTS: int = 1000
_MAX_EVENTS: int = 5000


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


def _to_jsonable(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, dict):
        return {str(k): _to_jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_to_jsonable(v) for v in value]
    if hasattr(value, "to_dict") and callable(value.to_dict):
        return _dataclass_to_dict(value)
    return value


def _dataclass_to_dict(instance: Any) -> Dict[str, Any]:
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


def _safe_float(value: Any, default: float = 0.0) -> float:
    if value is None or value == "":
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _safe_int(value: Any, default: int = 0) -> int:
    if value is None or value == "":
        return default
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


# ---------------------------------------------------------------------------
# Domain Enums
# ---------------------------------------------------------------------------


class ActionType(Enum):
    """Categories of player actions."""
    MOVEMENT = "movement"
    COMBAT = "combat"
    INTERACT = "interact"
    CRAFT = "craft"
    TRADE = "trade"
    EXPLORE = "explore"
    SOCIAL = "social"
    UI = "ui"
    EXPLOIT = "exploit"
    CREATIVE = "creative"
    CUSTOM = "custom"


class PatternCategory(Enum):
    """Classification of detected emergent patterns."""
    UNEXPECTED_STRATEGY = "unexpected_strategy"
    CREATIVE_SOLUTION = "creative_solution"
    EXPLOIT = "exploit"
    SPEEDRUN = "speedrun"
    SEQUENCE_BREAK = "sequence_break"
    EMERGENT_INTERACTION = "emergent_interaction"
    STATISTICAL_ANOMALY = "statistical_anomaly"
    BEHAVIORAL_DRIFT = "behavioral_drift"
    NOVEL_COMBINATION = "novel_combination"


class PatternSeverity(Enum):
    """Impact severity of a detected pattern."""
    INFO = "info"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class DetectionMethod(Enum):
    """Methods used to detect a pattern."""
    FREQUENCY = "frequency"
    SEQUENCE = "sequence"
    ANOMALY = "anomaly"
    THRESHOLD = "threshold"
    COMPOSITE = "composite"
    HEURISTIC = "heuristic"


class PatternStatus(Enum):
    """Lifecycle status of a detected pattern."""
    DETECTED = "detected"
    CONFIRMED = "confirmed"
    FALSE_POSITIVE = "false_positive"
    RESOLVED = "resolved"
    MONITORING = "monitoring"


class DetectorEventKind(Enum):
    """Audit event types emitted by the detector."""
    SESSION_STARTED = "session_started"
    SESSION_ENDED = "session_ended"
    ACTION_RECORDED = "action_recorded"
    RULE_REGISTERED = "rule_registered"
    RULE_REMOVED = "rule_removed"
    PATTERN_DETECTED = "pattern_detected"
    PATTERN_CLASSIFIED = "pattern_classified"
    PATTERN_RESOLVED = "pattern_resolved"
    INSIGHT_GENERATED = "insight_generated"


# ---------------------------------------------------------------------------
# Data Classes
# ---------------------------------------------------------------------------


@dataclass
class PlayerAction:
    """A single player action within a gameplay session."""
    action_id: str = field(default_factory=lambda: _new_id("act"))
    session_id: str = ""
    player_id: str = ""
    action_type: str = ActionType.MOVEMENT.value
    target: str = ""
    position: Dict[str, float] = field(default_factory=dict)
    context: Dict[str, Any] = field(default_factory=dict)
    outcome: str = ""
    timestamp: str = field(default_factory=_now)
    sequence_index: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class GameplaySession:
    """A tracked gameplay session with an action stream."""
    session_id: str = field(default_factory=lambda: _new_id("ses"))
    player_id: str = ""
    game_mode: str = ""
    started_at: str = field(default_factory=_now)
    ended_at: str = ""
    action_count: int = 0
    patterns_detected: int = 0
    status: str = "active"
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class DetectionRule:
    """A custom rule for detecting emergent patterns."""
    rule_id: str = field(default_factory=lambda: _new_id("rul"))
    name: str = ""
    description: str = ""
    method: str = DetectionMethod.HEURISTIC.value
    category: str = PatternCategory.UNEXPECTED_STRATEGY.value
    severity: str = PatternSeverity.LOW.value
    conditions: Dict[str, Any] = field(default_factory=dict)
    threshold: float = 0.5
    enabled: bool = True
    created_at: str = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class EmergentPattern:
    """A detected emergent gameplay pattern."""
    pattern_id: str = field(default_factory=lambda: _new_id("pat"))
    session_id: str = ""
    player_id: str = ""
    category: str = PatternCategory.UNEXPECTED_STRATEGY.value
    severity: str = PatternSeverity.LOW.value
    method: str = DetectionMethod.HEURISTIC.value
    description: str = ""
    action_ids: List[str] = field(default_factory=list)
    confidence: float = 0.5
    frequency: int = 1
    first_seen: str = field(default_factory=_now)
    last_seen: str = field(default_factory=_now)
    status: str = PatternStatus.DETECTED.value
    rule_id: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class EmergenceInsight:
    """A design insight derived from detected patterns."""
    insight_id: str = field(default_factory=lambda: _new_id("ins"))
    title: str = ""
    description: str = ""
    pattern_ids: List[str] = field(default_factory=list)
    category: str = PatternCategory.UNEXPECTED_STRATEGY.value
    recommendation: str = ""
    impact_score: float = 0.5
    actionability: float = 0.5
    created_at: str = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class DetectorStats:
    """Aggregate counters for the detector."""
    total_sessions: int = 0
    active_sessions: int = 0
    total_actions: int = 0
    total_patterns: int = 0
    total_rules: int = 0
    total_insights: int = 0
    patterns_by_category: Dict[str, int] = field(default_factory=dict)
    patterns_by_severity: Dict[str, int] = field(default_factory=dict)
    avg_confidence: float = 0.0
    last_updated: str = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class DetectorSnapshot:
    """Immutable point-in-time capture of detector state."""
    sessions: Dict[str, Any] = field(default_factory=dict)
    actions: List[Dict[str, Any]] = field(default_factory=list)
    patterns: List[Dict[str, Any]] = field(default_factory=list)
    rules: Dict[str, Any] = field(default_factory=dict)
    insights: List[Dict[str, Any]] = field(default_factory=list)
    stats: Dict[str, Any] = field(default_factory=dict)
    taken_at: str = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class DetectorEvent:
    """Audit log entry."""
    event_id: str = field(default_factory=lambda: _new_id("dev"))
    kind: str = DetectorEventKind.SESSION_STARTED.value
    payload: Dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


# ---------------------------------------------------------------------------
# Emergent Gameplay Detector Singleton
# ---------------------------------------------------------------------------


class EmergentGameplayDetector:
    """Singleton agent that detects emergent gameplay patterns.

    The detector ingests player actions from live gameplay sessions,
    analyzes them using built-in heuristics and custom rules, and
    identifies emergent patterns such as unexpected strategies, creative
    solutions, exploits, and statistical anomalies. Detected patterns
    are classified, tracked, and can generate design insights that feed
    back into the game's evolution.
    """

    _instance: Optional["EmergentGameplayDetector"] = None
    _inner_lock = threading.RLock()

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._initialized: bool = False
        self._sessions: Dict[str, GameplaySession] = {}
        self._actions: Dict[str, PlayerAction] = {}
        self._actions_by_session: Dict[str, List[str]] = {}
        self._patterns: Dict[str, EmergentPattern] = {}
        self._rules: Dict[str, DetectionRule] = {}
        self._insights: Dict[str, EmergenceInsight] = {}
        self._events: List[DetectorEvent] = []
        self._action_counter: int = 0
        self._pattern_counter: int = 0

    # ------------------------------------------------------------------
    # Singleton
    # ------------------------------------------------------------------

    @classmethod
    def get_instance(cls) -> "EmergentGameplayDetector":
        if cls._instance is None:
            with cls._inner_lock:
                if cls._instance is None:
                    cls._instance = cls()
                    cls._instance._initialize()
        return cls._instance

    def _initialize(self) -> None:
        with self._lock:
            if self._initialized:
                return
            self._seed_default_rules()
            self._initialized = True

    def _seed_default_rules(self) -> None:
        """Seed a small set of default detection rules."""
        defaults = [
            ("High Frequency Action", "Detects actions repeated at unusual frequency",
             DetectionMethod.FREQUENCY, PatternCategory.STATISTICAL_ANOMALY,
             PatternSeverity.MEDIUM, 0.7),
            ("Sequence Break", "Detects out-of-order action sequences",
             DetectionMethod.SEQUENCE, PatternCategory.SEQUENCE_BREAK,
             PatternSeverity.HIGH, 0.6),
            ("Exploit Pattern", "Detects potential exploit combinations",
             DetectionMethod.COMPOSITE, PatternCategory.EXPLOIT,
             PatternSeverity.CRITICAL, 0.8),
            ("Creative Solution", "Detects novel action combinations",
             DetectionMethod.HEURISTIC, PatternCategory.CREATIVE_SOLUTION,
             PatternSeverity.INFO, 0.4),
            ("Speedrun Behavior", "Detects speedrun-style optimization",
             DetectionMethod.THRESHOLD, PatternCategory.SPEEDRUN,
             PatternSeverity.LOW, 0.5),
        ]
        for name, desc, method, cat, sev, threshold in defaults:
            rule = DetectionRule(
                rule_id=_new_id("rul"),
                name=name,
                description=desc,
                method=method.value,
                category=cat.value,
                severity=sev.value,
                threshold=threshold,
            )
            self._rules[rule.rule_id] = rule

    def _emit_event(self, kind: DetectorEventKind, payload: Dict[str, Any]) -> None:
        evt = DetectorEvent(kind=kind.value, payload=payload)
        self._events.append(evt)
        _evict_fifo_list(self._events, _MAX_EVENTS)

    def _index_append(self, index: Dict[str, List[str]], key: str, value: str) -> None:
        if key not in index:
            index[key] = []
        if value not in index[key]:
            index[key].append(value)

    # ------------------------------------------------------------------
    # Session Management
    # ------------------------------------------------------------------

    def start_session(self, player_id: str = "", game_mode: str = "",
                      session_id: str = "",
                      metadata: Optional[Dict[str, Any]] = None) -> GameplaySession:
        with self._lock:
            sid = session_id or _new_id("ses")
            session = GameplaySession(
                session_id=sid,
                player_id=player_id,
                game_mode=game_mode,
                status="active",
                metadata=metadata or {},
            )
            self._sessions[sid] = session
            self._actions_by_session[sid] = []
            _evict_fifo_dict(self._sessions, _MAX_SESSIONS)
            self._emit_event(DetectorEventKind.SESSION_STARTED, {"session_id": sid})
            return session

    def end_session(self, session_id: str) -> Optional[GameplaySession]:
        with self._lock:
            session = self._sessions.get(session_id)
            if session is None:
                return None
            session.status = "ended"
            session.ended_at = _now()
            self._emit_event(DetectorEventKind.SESSION_ENDED, {"session_id": session_id})
            return session

    def get_session(self, session_id: str) -> Optional[GameplaySession]:
        with self._lock:
            return self._sessions.get(session_id)

    def list_sessions(self, player_id: str = "", active_only: bool = False,
                      limit: int = 100) -> List[GameplaySession]:
        with self._lock:
            items = list(self._sessions.values())
            if player_id:
                items = [s for s in items if s.player_id == player_id]
            if active_only:
                items = [s for s in items if s.status == "active"]
            return items[-limit:]

    # ------------------------------------------------------------------
    # Action Recording
    # ------------------------------------------------------------------

    def record_action(self, session_id: str = "", player_id: str = "",
                      action_type: Any = "", target: str = "",
                      position: Optional[Dict[str, float]] = None,
                      context: Optional[Dict[str, Any]] = None,
                      outcome: str = "",
                      action_id: str = "") -> PlayerAction:
        with self._lock:
            at_val = self._coerce_action_type(action_type).value
            aid = action_id or _new_id("act")
            seq_idx = self._action_counter
            action = PlayerAction(
                action_id=aid,
                session_id=session_id,
                player_id=player_id,
                action_type=at_val,
                target=target,
                position=dict(position) if position else {},
                context=dict(context) if context else {},
                outcome=outcome,
                sequence_index=seq_idx,
            )
            self._actions[aid] = action
            self._action_counter += 1
            if session_id:
                self._index_append(self._actions_by_session, session_id, aid)
                session = self._sessions.get(session_id)
                if session:
                    session.action_count += 1
            _evict_fifo_dict(self._actions, _MAX_ACTIONS)
            self._emit_event(DetectorEventKind.ACTION_RECORDED, {
                "action_id": aid, "session_id": session_id, "type": at_val,
            })
            return action

    def get_action(self, action_id: str) -> Optional[PlayerAction]:
        with self._lock:
            return self._actions.get(action_id)

    def list_actions(self, session_id: str = "", action_type: Any = None,
                     limit: int = 100) -> List[PlayerAction]:
        with self._lock:
            if session_id:
                ids = self._actions_by_session.get(session_id, [])
                items = [self._actions[aid] for aid in ids if aid in self._actions]
            else:
                items = list(self._actions.values())
            if action_type is not None and action_type != "":
                at_val = self._coerce_action_type(action_type).value
                items = [a for a in items if a.action_type == at_val]
            return items[-limit:]

    # ------------------------------------------------------------------
    # Rule Management
    # ------------------------------------------------------------------

    def register_rule(self, name: str = "", description: str = "",
                      method: Any = "heuristic", category: Any = "unexpected_strategy",
                      severity: Any = "low", conditions: Optional[Dict[str, Any]] = None,
                      threshold: float = 0.5, enabled: bool = True,
                      rule_id: str = "") -> DetectionRule:
        with self._lock:
            rid = rule_id or _new_id("rul")
            rule = DetectionRule(
                rule_id=rid,
                name=name,
                description=description,
                method=self._coerce_method(method).value,
                category=self._coerce_category(category).value,
                severity=self._coerce_severity(severity).value,
                conditions=dict(conditions) if conditions else {},
                threshold=_safe_float(threshold, 0.5),
                enabled=enabled,
            )
            self._rules[rid] = rule
            _evict_fifo_dict(self._rules, _MAX_RULES)
            self._emit_event(DetectorEventKind.RULE_REGISTERED, {"rule_id": rid})
            return rule

    def get_rule(self, rule_id: str) -> Optional[DetectionRule]:
        with self._lock:
            return self._rules.get(rule_id)

    def list_rules(self, category: Any = None, enabled_only: bool = False,
                   limit: int = 100) -> List[DetectionRule]:
        with self._lock:
            items = list(self._rules.values())
            if category is not None and category != "":
                cat_val = self._coerce_category(category).value
                items = [r for r in items if r.category == cat_val]
            if enabled_only:
                items = [r for r in items if r.enabled]
            return items[-limit:]

    def remove_rule(self, rule_id: str) -> bool:
        with self._lock:
            if rule_id not in self._rules:
                return False
            self._rules.pop(rule_id)
            self._emit_event(DetectorEventKind.RULE_REMOVED, {"rule_id": rule_id})
            return True

    # ------------------------------------------------------------------
    # Pattern Detection
    # ------------------------------------------------------------------

    def detect_patterns(self, session_id: str = "",
                        limit: int = 50) -> List[EmergentPattern]:
        """Run detection heuristics over a session's action stream."""
        with self._lock:
            if session_id:
                action_ids = self._actions_by_session.get(session_id, [])
                actions = [self._actions[aid] for aid in action_ids if aid in self._actions]
            else:
                actions = list(self._actions.values())

            detected: List[EmergentPattern] = []

            if len(actions) < 2:
                return detected

            # Frequency analysis: detect unusually repeated actions
            type_counter: Counter = Counter(a.action_type for a in actions)
            for atype, count in type_counter.items():
                if count >= 5:
                    ratio = count / max(1, len(actions))
                    if ratio > 0.4:
                        pattern = self._create_pattern(
                            session_id=session_id,
                            actions=[a.action_id for a in actions if a.action_type == atype][:10],
                            category=PatternCategory.STATISTICAL_ANOMALY,
                            severity=PatternSeverity.MEDIUM if ratio > 0.6 else PatternSeverity.LOW,
                            method=DetectionMethod.FREQUENCY,
                            description=f"High frequency of '{atype}' actions ({count}/{len(actions)}, {ratio:.0%})",
                            confidence=min(1.0, ratio),
                            frequency=count,
                        )
                        detected.append(pattern)

            # Sequence analysis: detect repeated action sequences
            seq_patterns = self._detect_sequences(actions, session_id)
            detected.extend(seq_patterns)

            # Exploit detection: look for suspicious action combinations
            exploit_patterns = self._detect_exploits(actions, session_id)
            detected.extend(exploit_patterns)

            # Creative solution detection: novel action combinations
            creative_patterns = self._detect_creative_combos(actions, session_id)
            detected.extend(creative_patterns)

            # Apply custom rules
            for rule in self._rules.values():
                if not rule.enabled:
                    continue
                rule_patterns = self._apply_rule(rule, actions, session_id)
                detected.extend(rule_patterns)

            # Update session pattern count
            if session_id and detected:
                session = self._sessions.get(session_id)
                if session:
                    session.patterns_detected += len(detected)

            return detected[:limit]

    def _detect_sequences(self, actions: List[PlayerAction],
                          session_id: str) -> List[EmergentPattern]:
        """Detect repeated action sequences of length 2-4."""
        patterns: List[EmergentPattern] = []
        if len(actions) < 4:
            return patterns
        seq_counter: Counter = Counter()
        seq_actions: Dict[str, List[str]] = {}
        for i in range(len(actions) - 2):
            seq = tuple(a.action_type for a in actions[i:i + 3])
            seq_key = "->".join(seq)
            seq_counter[seq_key] += 1
            if seq_key not in seq_actions:
                seq_actions[seq_key] = [actions[i + j].action_id for j in range(3)]

        for seq_key, count in seq_counter.items():
            if count >= 3:
                pattern = self._create_pattern(
                    session_id=session_id,
                    actions=seq_actions[seq_key],
                    category=PatternCategory.NOVEL_COMBINATION,
                    severity=PatternSeverity.LOW,
                    method=DetectionMethod.SEQUENCE,
                    description=f"Repeated action sequence: {seq_key} ({count} times)",
                    confidence=min(1.0, count / 10.0),
                    frequency=count,
                )
                patterns.append(pattern)
        return patterns

    def _detect_exploits(self, actions: List[PlayerAction],
                         session_id: str) -> List[EmergentPattern]:
        """Detect potential exploit patterns."""
        patterns: List[EmergentPattern] = []
        exploit_types = {ActionType.EXPLOIT.value, ActionType.TRADE.value, ActionType.CRAFT.value}
        exploit_actions = [a for a in actions if a.action_type in exploit_types]
        if len(exploit_actions) >= 3:
            # Check for rapid repetition of exploit-prone actions
            time_gaps: List[float] = []
            for i in range(1, len(exploit_actions)):
                try:
                    t1 = datetime.fromisoformat(exploit_actions[i - 1].timestamp.replace("Z", "+00:00"))
                    t2 = datetime.fromisoformat(exploit_actions[i].timestamp.replace("Z", "+00:00"))
                    gap = (t2 - t1).total_seconds()
                    time_gaps.append(gap)
                except (ValueError, TypeError):
                    continue
            if time_gaps and all(g < 1.0 for g in time_gaps) and len(time_gaps) >= 2:
                pattern = self._create_pattern(
                    session_id=session_id,
                    actions=[a.action_id for a in exploit_actions[:5]],
                    category=PatternCategory.EXPLOIT,
                    severity=PatternSeverity.HIGH,
                    method=DetectionMethod.COMPOSITE,
                    description="Rapid exploit-prone action sequence detected",
                    confidence=0.75,
                    frequency=len(exploit_actions),
                )
                patterns.append(pattern)
        return patterns

    def _detect_creative_combos(self, actions: List[PlayerAction],
                                session_id: str) -> List[EmergentPattern]:
        """Detect creative action combinations."""
        patterns: List[EmergentPattern] = []
        if len(actions) < 3:
            return patterns
        # Look for diverse action types in a short window
        window_size = min(10, len(actions))
        window = actions[-window_size:]
        unique_types = set(a.action_type for a in window)
        if len(unique_types) >= 4:
            pattern = self._create_pattern(
                session_id=session_id,
                actions=[a.action_id for a in window],
                category=PatternCategory.CREATIVE_SOLUTION,
                severity=PatternSeverity.INFO,
                method=DetectionMethod.HEURISTIC,
                description=f"Diverse action combination ({len(unique_types)} unique types in {window_size} actions)",
                confidence=0.6,
                frequency=1,
            )
            patterns.append(pattern)
        return patterns

    def _apply_rule(self, rule: DetectionRule, actions: List[PlayerAction],
                    session_id: str) -> List[EmergentPattern]:
        """Apply a custom detection rule to the action stream."""
        patterns: List[EmergentPattern] = []
        conditions = rule.conditions or {}
        target_type = conditions.get("action_type", "")
        min_count = int(conditions.get("min_count", 3))
        if target_type:
            matching = [a for a in actions if a.action_type == target_type]
            if len(matching) >= min_count:
                confidence = min(1.0, len(matching) / (min_count * 2.0))
                if confidence >= rule.threshold:
                    pattern = self._create_pattern(
                        session_id=session_id,
                        actions=[a.action_id for a in matching[:5]],
                        category=self._coerce_category(rule.category),
                        severity=self._coerce_severity(rule.severity),
                        method=self._coerce_method(rule.method),
                        description=f"Rule '{rule.name}' triggered: {len(matching)} '{target_type}' actions",
                        confidence=confidence,
                        frequency=len(matching),
                        rule_id=rule.rule_id,
                    )
                    patterns.append(pattern)
        return patterns

    def _create_pattern(self, session_id: str, actions: List[str],
                        category: PatternCategory, severity: PatternSeverity,
                        method: DetectionMethod, description: str,
                        confidence: float = 0.5, frequency: int = 1,
                        rule_id: str = "") -> EmergentPattern:
        pid = _new_id("pat")
        pattern = EmergentPattern(
            pattern_id=pid,
            session_id=session_id,
            category=category.value,
            severity=severity.value,
            method=method.value,
            description=description,
            action_ids=list(actions),
            confidence=round(confidence, 4),
            frequency=frequency,
            rule_id=rule_id,
        )
        self._patterns[pid] = pattern
        self._pattern_counter += 1
        _evict_fifo_dict(self._patterns, _MAX_PATTERNS)
        self._emit_event(DetectorEventKind.PATTERN_DETECTED, {
            "pattern_id": pid, "category": category.value, "confidence": pattern.confidence,
        })
        return pattern

    def get_pattern(self, pattern_id: str) -> Optional[EmergentPattern]:
        with self._lock:
            return self._patterns.get(pattern_id)

    def list_patterns(self, session_id: str = "", category: Any = None,
                      severity: Any = None, status: Any = None,
                      limit: int = 100) -> List[EmergentPattern]:
        with self._lock:
            items = list(self._patterns.values())
            if session_id:
                items = [p for p in items if p.session_id == session_id]
            if category is not None and category != "":
                cat_val = self._coerce_category(category).value
                items = [p for p in items if p.category == cat_val]
            if severity is not None and severity != "":
                sev_val = self._coerce_severity(severity).value
                items = [p for p in items if p.severity == sev_val]
            if status is not None and status != "":
                st_val = self._coerce_status(status).value
                items = [p for p in items if p.status == st_val]
            return items[-limit:]

    def classify_pattern(self, pattern_id: str, category: Any = "",
                         severity: Any = "") -> Optional[EmergentPattern]:
        with self._lock:
            pattern = self._patterns.get(pattern_id)
            if pattern is None:
                return None
            if category:
                pattern.category = self._coerce_category(category).value
            if severity:
                pattern.severity = self._coerce_severity(severity).value
            pattern.status = PatternStatus.CONFIRMED.value
            self._emit_event(DetectorEventKind.PATTERN_CLASSIFIED, {"pattern_id": pattern_id})
            return pattern

    def resolve_pattern(self, pattern_id: str,
                        resolution: str = "resolved") -> Optional[EmergentPattern]:
        with self._lock:
            pattern = self._patterns.get(pattern_id)
            if pattern is None:
                return None
            if resolution == "false_positive":
                pattern.status = PatternStatus.FALSE_POSITIVE.value
            else:
                pattern.status = PatternStatus.RESOLVED.value
            self._emit_event(DetectorEventKind.PATTERN_RESOLVED, {"pattern_id": pattern_id})
            return pattern

    # ------------------------------------------------------------------
    # Insight Generation
    # ------------------------------------------------------------------

    def generate_insight(self, title: str = "", description: str = "",
                         pattern_ids: Optional[List[str]] = None,
                         category: Any = "", recommendation: str = "",
                         impact_score: float = 0.5,
                         actionability: float = 0.5,
                         insight_id: str = "") -> EmergenceInsight:
        with self._lock:
            iid = insight_id or _new_id("ins")
            insight = EmergenceInsight(
                insight_id=iid,
                title=title,
                description=description,
                pattern_ids=list(pattern_ids) if pattern_ids else [],
                category=self._coerce_category(category).value,
                recommendation=recommendation,
                impact_score=_safe_float(impact_score, 0.5),
                actionability=_safe_float(actionability, 0.5),
            )
            self._insights[iid] = insight
            _evict_fifo_dict(self._insights, _MAX_INSIGHTS)
            self._emit_event(DetectorEventKind.INSIGHT_GENERATED, {"insight_id": iid})
            return insight

    def get_insight(self, insight_id: str) -> Optional[EmergenceInsight]:
        with self._lock:
            return self._insights.get(insight_id)

    def list_insights(self, category: Any = None, limit: int = 100) -> List[EmergenceInsight]:
        with self._lock:
            items = list(self._insights.values())
            if category is not None and category != "":
                cat_val = self._coerce_category(category).value
                items = [i for i in items if i.category == cat_val]
            return items[-limit:]

    # ------------------------------------------------------------------
    # Enum Coercion Helpers
    # ------------------------------------------------------------------

    def _coerce_action_type(self, value: Any) -> ActionType:
        if isinstance(value, ActionType):
            return value
        if isinstance(value, str) and value:
            try:
                return ActionType(value)
            except ValueError:
                pass
        return ActionType.MOVEMENT

    def _coerce_category(self, value: Any) -> PatternCategory:
        if isinstance(value, PatternCategory):
            return value
        if isinstance(value, str) and value:
            try:
                return PatternCategory(value)
            except ValueError:
                pass
        return PatternCategory.UNEXPECTED_STRATEGY

    def _coerce_severity(self, value: Any) -> PatternSeverity:
        if isinstance(value, PatternSeverity):
            return value
        if isinstance(value, str) and value:
            try:
                return PatternSeverity(value)
            except ValueError:
                pass
        return PatternSeverity.LOW

    def _coerce_method(self, value: Any) -> DetectionMethod:
        if isinstance(value, DetectionMethod):
            return value
        if isinstance(value, str) and value:
            try:
                return DetectionMethod(value)
            except ValueError:
                pass
        return DetectionMethod.HEURISTIC

    def _coerce_status(self, value: Any) -> PatternStatus:
        if isinstance(value, PatternStatus):
            return value
        if isinstance(value, str) and value:
            try:
                return PatternStatus(value)
            except ValueError:
                pass
        return PatternStatus.DETECTED

    # ------------------------------------------------------------------
    # Observability
    # ------------------------------------------------------------------

    def list_events(self, limit: int = 100) -> List[DetectorEvent]:
        with self._lock:
            return list(self._events[-limit:])

    def get_stats(self) -> DetectorStats:
        with self._lock:
            cat_counts: Dict[str, int] = {}
            sev_counts: Dict[str, int] = {}
            total_conf = 0.0
            for p in self._patterns.values():
                cat_counts[p.category] = cat_counts.get(p.category, 0) + 1
                sev_counts[p.severity] = sev_counts.get(p.severity, 0) + 1
                total_conf += p.confidence
            avg_conf = round(total_conf / len(self._patterns), 4) if self._patterns else 0.0
            active = sum(1 for s in self._sessions.values() if s.status == "active")
            return DetectorStats(
                total_sessions=len(self._sessions),
                active_sessions=active,
                total_actions=len(self._actions),
                total_patterns=len(self._patterns),
                total_rules=len(self._rules),
                total_insights=len(self._insights),
                patterns_by_category=cat_counts,
                patterns_by_severity=sev_counts,
                avg_confidence=avg_conf,
            )

    def get_status(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "initialized": self._initialized,
                "sessions": len(self._sessions),
                "actions": len(self._actions),
                "patterns": len(self._patterns),
                "rules": len(self._rules),
                "insights": len(self._insights),
                "events": len(self._events),
            }

    def get_snapshot(self) -> DetectorSnapshot:
        with self._lock:
            return DetectorSnapshot(
                sessions={sid: s.to_dict() for sid, s in list(self._sessions.items())[:50]},
                actions=[a.to_dict() for a in list(self._actions.values())[-50:]],
                patterns=[p.to_dict() for p in list(self._patterns.values())[-50:]],
                rules={rid: r.to_dict() for rid, r in list(self._rules.items())[:50]},
                insights=[i.to_dict() for i in list(self._insights.values())[-50:]],
                stats=self.get_stats().to_dict(),
            )

    def reset(self) -> None:
        with self._lock:
            self._sessions.clear()
            self._actions.clear()
            self._actions_by_session.clear()
            self._patterns.clear()
            self._rules.clear()
            self._insights.clear()
            self._events.clear()
            self._action_counter = 0
            self._pattern_counter = 0
            self._seed_default_rules()


def get_emergent_gameplay_detector() -> EmergentGameplayDetector:
    """Factory function to obtain the singleton EmergentGameplayDetector."""
    return EmergentGameplayDetector.get_instance()
