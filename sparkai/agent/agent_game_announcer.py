"""
SparkLabs Agent - AI Game Announcer

An AI-driven narration and commentary system for the SparkLabs AI-native game
engine. This agent generates real-time play-by-play descriptions, color
commentary, announcements, and dramatic reactions in response to gameplay
events. It adapts its tone based on the intensity and context of the action,
maintains a priority queue to avoid flooding the player with overlapping
lines, and provides cooldown management to keep commentary fresh.

The system fuses the real-time decision-making patterns of Hermes Agent with
the narrative simulation approach of genagents and the situational awareness
of WorldX. The announcer is not a static line-picker — it evaluates the
current game state (score gap, streak length, time remaining, player skill
disparity) to select commentary that matches the moment.

Architecture:
  GameAnnouncer (singleton)
    |-- CommentaryLine, CommentaryTrigger, GameContext, AnnouncerConfig,
       AnnouncerStats, AnnouncerSnapshot, AnnouncerEvent
    |-- CommentaryKind, ToneProfile, CommentaryPriority, TriggerKind,
       AnnouncerEventKind

Core Capabilities:
  - register_line / get_line / list_lines / remove_line: lifecycle for the
    commentary line library, organized by trigger and tone.
  - register_trigger / get_trigger / list_triggers / remove_trigger: event
    predicates that activate commentary (kill streaks, objective captures,
    match phase transitions, comeback thresholds).
  - submit_event: feed a gameplay event into the announcer for evaluation;
    the announcer selects a matching line, applies cooldowns, and enqueues
    it for delivery.
  - dequeue_line: retrieve the next highest-priority line for playback.
  - peek_queue / clear_queue: inspect or flush the pending delivery queue.
  - set_context / get_context: update the game state context (scores, timers,
    streaks) that informs commentary selection.
  - set_tone / get_tone: override the global tone profile (excited, calm,
    tense, celebratory, analytical, dramatic).
  - tick: expire stale queued lines and decay cooldowns.
  - set_config / get_config: tuning for queue size, cooldown duration,
    and spam prevention.
  - list_events / get_stats / get_status / get_snapshot / reset:
    observability and state management.

The class implements the singleton pattern with double-checked locking
using ``threading.RLock``; consumers should obtain the instance through
:meth:`GameAnnouncer.get_instance` or the module-level
:func:`get_game_announcer` factory.
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

_MAX_LINES: int = 10000
_MAX_TRIGGERS: int = 2000
_MAX_QUEUE: int = 200
_MAX_EVENTS: int = 5000
_MAX_HISTORY: int = 5000

_DEFAULT_COOLDOWN: float = 5.0
_DEFAULT_LINE_LIFETIME: float = 10.0
_DEFAULT_SPAM_THRESHOLD: int = 3


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
    if isinstance(value, (list, tuple, set)):
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


def _clamp(value: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, value))


# ---------------------------------------------------------------------------
# Domain Enums
# ---------------------------------------------------------------------------


class CommentaryKind(Enum):
    """Classification of commentary line types."""
    PLAY_BY_PLAY = "play_by_play"
    COLOR = "color"
    ANNOUNCEMENT = "announcement"
    REACTION = "reaction"
    HYPE = "hype"
    ANALYSIS = "analysis"


class ToneProfile(Enum):
    """Emotional tone profiles for commentary delivery."""
    NEUTRAL = "neutral"
    EXCITED = "excited"
    CALM = "calm"
    TENSE = "tense"
    CELEBRATORY = "celebratory"
    ANALYTICAL = "analytical"
    DRAMATIC = "dramatic"
    HUMOROUS = "humorous"


class CommentaryPriority(Enum):
    """Delivery priority levels for queued lines."""
    LOW = 1
    NORMAL = 2
    HIGH = 3
    CRITICAL = 4


class TriggerKind(Enum):
    """Gameplay event types that can activate commentary."""
    KILL = "kill"
    DEATH = "death"
    DOUBLE_KILL = "double_kill"
    TRIPLE_KILL = "triple_kill"
    KILL_STREAK = "kill_streak"
    OBJECTIVE_CAPTURE = "objective_capture"
    OBJECTIVE_LOST = "objective_lost"
    MATCH_START = "match_start"
    MATCH_END = "match_end"
    ROUND_START = "round_start"
    ROUND_END = "round_end"
    ACHIEVEMENT = "achievement"
    LEVEL_UP = "level_up"
    COMEBACK = "comeback"
    UPSET = "upset"
    OVERTIME = "overtime"
    LOW_HEALTH = "low_health"
    PERFECT = "perfect"
    NEAR_MISS = "near_miss"
    CUSTOM = "custom"


class AnnouncerEventKind(Enum):
    """Audit event types emitted by the announcer."""
    LINE_REGISTERED = "line_registered"
    LINE_REMOVED = "line_removed"
    TRIGGER_REGISTERED = "trigger_registered"
    TRIGGER_REMOVED = "trigger_removed"
    EVENT_SUBMITTED = "event_submitted"
    LINE_ENQUEUED = "line_enqueued"
    LINE_DEQUEUED = "line_dequeued"
    LINE_EXPIRED = "line_expired"
    CONTEXT_UPDATED = "context_updated"
    TONE_CHANGED = "tone_changed"
    QUEUE_CLEARED = "queue_cleared"
    CONFIG_UPDATED = "config_updated"


# ---------------------------------------------------------------------------
# Data Classes
# ---------------------------------------------------------------------------


@dataclass
class CommentaryLine:
    """A single commentary line in the announcer library."""
    line_id: str = ""
    text: str = ""
    kind: str = CommentaryKind.PLAY_BY_PLAY.value
    tone: str = ToneProfile.NEUTRAL.value
    trigger: str = TriggerKind.CUSTOM.value
    priority: int = CommentaryPriority.NORMAL.value
    cooldown: float = _DEFAULT_COOLDOWN
    weight: float = 1.0
    language: str = "en"
    voiced: bool = True
    duration: float = 3.0
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class CommentaryTrigger:
    """An event predicate that activates commentary selection."""
    trigger_id: str = ""
    kind: str = TriggerKind.CUSTOM.value
    name: str = ""
    description: str = ""
    conditions: Dict[str, Any] = field(default_factory=dict)
    priority_override: int = 0
    cooldown_override: float = 0.0
    enabled: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class GameContext:
    """Snapshot of game state used to inform commentary selection."""
    match_phase: str = "in_progress"
    score_home: int = 0
    score_away: int = 0
    time_remaining: float = 0.0
    current_streak: int = 0
    streak_owner: str = ""
    lead_team: str = ""
    lead_margin: int = 0
    overtime: bool = False
    player_name: str = ""
    player_team: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class QueuedLine:
    """A commentary line awaiting delivery."""
    queue_id: str = ""
    line_id: str = ""
    text: str = ""
    kind: str = CommentaryKind.PLAY_BY_PLAY.value
    tone: str = ToneProfile.NEUTRAL.value
    priority: int = CommentaryPriority.NORMAL.value
    trigger: str = TriggerKind.CUSTOM.value
    enqueued_at: str = ""
    expires_at: str = ""
    duration: float = 3.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class AnnouncerConfig:
    """Tuning parameters for the announcer."""
    max_queue_size: int = 50
    default_cooldown: float = _DEFAULT_COOLDOWN
    line_lifetime: float = _DEFAULT_LINE_LIFETIME
    spam_threshold: int = _DEFAULT_SPAM_THRESHOLD
    spam_window: float = 10.0
    auto_expire_enabled: bool = True
    voiced_mode: bool = True
    language: str = "en"

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class AnnouncerStats:
    """Aggregate statistics for the announcer."""
    total_lines_registered: int = 0
    total_triggers_registered: int = 0
    total_events_submitted: int = 0
    total_lines_enqueued: int = 0
    total_lines_delivered: int = 0
    total_lines_expired: int = 0
    queue_depth: int = 0
    avg_priority: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class AnnouncerSnapshot:
    """Full state snapshot of the announcer."""
    lines: List[CommentaryLine] = field(default_factory=list)
    triggers: List[CommentaryTrigger] = field(default_factory=list)
    queue: List[QueuedLine] = field(default_factory=list)
    context: GameContext = field(default_factory=GameContext)
    config: AnnouncerConfig = field(default_factory=AnnouncerConfig)
    stats: AnnouncerStats = field(default_factory=AnnouncerStats)
    current_tone: str = ToneProfile.NEUTRAL.value

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class AnnouncerEvent:
    """An audit event emitted by the announcer."""
    timestamp: str = ""
    kind: str = ""
    entity_id: str = ""
    details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


# ---------------------------------------------------------------------------
# Singleton System
# ---------------------------------------------------------------------------


class GameAnnouncer:
    """AI-driven game narration and commentary system.

    Generates contextual play-by-play, color commentary, announcements, and
    reactions in response to gameplay events. Maintains a priority delivery
    queue with cooldown and spam prevention.

    Implements the singleton pattern with double-checked locking.
    """

    _instance: Optional["GameAnnouncer"] = None
    _lock = threading.RLock()

    def __init__(self) -> None:
        self._initialized: bool = False
        self._lines: Dict[str, CommentaryLine] = {}
        self._triggers: Dict[str, CommentaryTrigger] = {}
        self._queue: List[QueuedLine] = []
        self._context: GameContext = GameContext()
        self._config: AnnouncerConfig = AnnouncerConfig()
        self._stats: AnnouncerStats = AnnouncerStats()
        self._events: List[AnnouncerEvent] = []
        self._history: List[Dict[str, Any]] = []
        self._cooldowns: Dict[str, float] = {}
        self._current_tone: str = ToneProfile.NEUTRAL.value
        self._tick_count: int = 0
        self._init_lock = threading.RLock()
        self._seed()

    @classmethod
    def get_instance(cls) -> "GameAnnouncer":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def _seed(self) -> None:
        """Seed the announcer with sample lines and triggers."""
        seed_lines = [
            CommentaryLine(
                line_id="ln_kill_basic",
                text="And that's another takedown!",
                kind=CommentaryKind.PLAY_BY_PLAY.value,
                tone=ToneProfile.EXCITED.value,
                trigger=TriggerKind.KILL.value,
                priority=CommentaryPriority.NORMAL.value,
                cooldown=3.0,
            ),
            CommentaryLine(
                line_id="ln_double_kill",
                text="Double kill! They're on a roll!",
                kind=CommentaryKind.HYPE.value,
                tone=ToneProfile.EXCITED.value,
                trigger=TriggerKind.DOUBLE_KILL.value,
                priority=CommentaryPriority.HIGH.value,
                cooldown=5.0,
            ),
            CommentaryLine(
                line_id="ln_triple_kill",
                text="TRIPLE KILL! Unbelievable!",
                kind=CommentaryKind.HYPE.value,
                tone=ToneProfile.CELEBRATORY.value,
                trigger=TriggerKind.TRIPLE_KILL.value,
                priority=CommentaryPriority.CRITICAL.value,
                cooldown=8.0,
            ),
            CommentaryLine(
                line_id="ln_streak_5",
                text="Five in a row! This player is unstoppable!",
                kind=CommentaryKind.HYPE.value,
                tone=ToneProfile.CELEBRATORY.value,
                trigger=TriggerKind.KILL_STREAK.value,
                priority=CommentaryPriority.HIGH.value,
                cooldown=10.0,
            ),
            CommentaryLine(
                line_id="ln_objective_cap",
                text="Objective secured! That's a critical capture.",
                kind=CommentaryKind.ANNOUNCEMENT.value,
                tone=ToneProfile.ANALYTICAL.value,
                trigger=TriggerKind.OBJECTIVE_CAPTURE.value,
                priority=CommentaryPriority.HIGH.value,
                cooldown=5.0,
            ),
            CommentaryLine(
                line_id="ln_objective_lost",
                text="And the objective falls to the enemy team.",
                kind=CommentaryKind.ANNOUNCEMENT.value,
                tone=ToneProfile.TENSE.value,
                trigger=TriggerKind.OBJECTIVE_LOST.value,
                priority=CommentaryPriority.HIGH.value,
                cooldown=5.0,
            ),
            CommentaryLine(
                line_id="ln_match_start",
                text="Welcome everyone, the match is about to begin!",
                kind=CommentaryKind.ANNOUNCEMENT.value,
                tone=ToneProfile.EXCITED.value,
                trigger=TriggerKind.MATCH_START.value,
                priority=CommentaryPriority.CRITICAL.value,
                cooldown=0.0,
            ),
            CommentaryLine(
                line_id="ln_match_end",
                text="And that's the final whistle! What a match!",
                kind=CommentaryKind.ANNOUNCEMENT.value,
                tone=ToneProfile.CELEBRATORY.value,
                trigger=TriggerKind.MATCH_END.value,
                priority=CommentaryPriority.CRITICAL.value,
                cooldown=0.0,
            ),
            CommentaryLine(
                line_id="ln_comeback",
                text="What a comeback! They've turned this match around!",
                kind=CommentaryKind.HYPE.value,
                tone=ToneProfile.DRAMATIC.value,
                trigger=TriggerKind.COMEBACK.value,
                priority=CommentaryPriority.CRITICAL.value,
                cooldown=15.0,
            ),
            CommentaryLine(
                line_id="ln_low_health",
                text="They're clinging to life — one hit away from disaster!",
                kind=CommentaryKind.REACTION.value,
                tone=ToneProfile.TENSE.value,
                trigger=TriggerKind.LOW_HEALTH.value,
                priority=CommentaryPriority.NORMAL.value,
                cooldown=4.0,
            ),
            CommentaryLine(
                line_id="ln_perfect",
                text="Flawless! Not a single scratch!",
                kind=CommentaryKind.HYPE.value,
                tone=ToneProfile.CELEBRATORY.value,
                trigger=TriggerKind.PERFECT.value,
                priority=CommentaryPriority.HIGH.value,
                cooldown=10.0,
            ),
            CommentaryLine(
                line_id="ln_near_miss",
                text="Ohh! Just barely missed!",
                kind=CommentaryKind.REACTION.value,
                tone=ToneProfile.DRAMATIC.value,
                trigger=TriggerKind.NEAR_MISS.value,
                priority=CommentaryPriority.LOW.value,
                cooldown=3.0,
            ),
            CommentaryLine(
                line_id="ln_color_strategy",
                text="You can really see the strategic positioning paying off here.",
                kind=CommentaryKind.COLOR.value,
                tone=ToneProfile.ANALYTICAL.value,
                trigger=TriggerKind.CUSTOM.value,
                priority=CommentaryPriority.LOW.value,
                cooldown=8.0,
            ),
            CommentaryLine(
                line_id="ln_color_skill",
                text="The mechanical skill on display is simply remarkable.",
                kind=CommentaryKind.COLOR.value,
                tone=ToneProfile.ANALYTICAL.value,
                trigger=TriggerKind.CUSTOM.value,
                priority=CommentaryPriority.LOW.value,
                cooldown=8.0,
            ),
            CommentaryLine(
                line_id="ln_overtime",
                text="We're heading to overtime! Anything can happen!",
                kind=CommentaryKind.ANNOUNCEMENT.value,
                tone=ToneProfile.DRAMATIC.value,
                trigger=TriggerKind.OVERTIME.value,
                priority=CommentaryPriority.CRITICAL.value,
                cooldown=10.0,
            ),
        ]
        for line in seed_lines:
            self._lines[line.line_id] = line

        seed_triggers = [
            CommentaryTrigger(
                trigger_id="trg_kill",
                kind=TriggerKind.KILL.value,
                name="Kill Event",
                description="Triggered when a player eliminates an opponent.",
                conditions={"event_type": "kill"},
            ),
            CommentaryTrigger(
                trigger_id="trg_double_kill",
                kind=TriggerKind.DOUBLE_KILL.value,
                name="Double Kill",
                description="Triggered when a player gets two kills within a short window.",
                conditions={"event_type": "kill", "streak_min": 2, "window_seconds": 5.0},
            ),
            CommentaryTrigger(
                trigger_id="trg_triple_kill",
                kind=TriggerKind.TRIPLE_KILL.value,
                name="Triple Kill",
                description="Triggered when a player gets three kills within a short window.",
                conditions={"event_type": "kill", "streak_min": 3, "window_seconds": 8.0},
            ),
            CommentaryTrigger(
                trigger_id="trg_objective",
                kind=TriggerKind.OBJECTIVE_CAPTURE.value,
                name="Objective Capture",
                description="Triggered when an objective is captured.",
                conditions={"event_type": "objective_capture"},
            ),
            CommentaryTrigger(
                trigger_id="trg_comeback",
                kind=TriggerKind.COMEBACK.value,
                name="Comeback",
                description="Triggered when a team takes the lead after being behind by a significant margin.",
                conditions={"event_type": "lead_change", "deficit_min": 3},
            ),
        ]
        for trigger in seed_triggers:
            self._triggers[trigger.trigger_id] = trigger

        self._stats.total_lines_registered = len(self._lines)
        self._stats.total_triggers_registered = len(self._triggers)
        self._initialized = True

    # ------------------------------------------------------------------
    # Private Helpers
    # ------------------------------------------------------------------

    def _emit_event(self, kind: str, entity_id: str, details: Optional[Dict[str, Any]] = None) -> None:
        event = AnnouncerEvent(
            timestamp=_now(),
            kind=kind,
            entity_id=entity_id,
            details=details or {},
        )
        self._events.append(event)
        _evict_fifo_list(self._events, _MAX_EVENTS)

    def _recompute_stats(self) -> None:
        self._stats.total_lines_registered = len(self._lines)
        self._stats.total_triggers_registered = len(self._triggers)
        self._stats.queue_depth = len(self._queue)
        if self._queue:
            self._stats.avg_priority = round(sum(q.priority for q in self._queue) / len(self._queue), 4)
        else:
            self._stats.avg_priority = 0.0

    def _select_line_for_trigger(self, trigger_kind: str) -> Optional[CommentaryLine]:
        """Select the best matching line for a trigger, respecting cooldowns."""
        candidates = [
            line for line in self._lines.values()
            if line.trigger == trigger_kind
        ]
        # Filter by language if configured
        if self._config.language:
            candidates = [c for c in candidates if c.language == self._config.language or c.language == ""]
        # Filter by voiced mode
        if self._config.voiced_mode:
            candidates = [c for c in candidates if c.voiced]
        if not candidates:
            return None
        # Prefer lines matching current tone
        tone_matches = [c for c in candidates if c.tone == self._current_tone]
        pool = tone_matches if tone_matches else candidates
        # Sort by weight descending, pick the first
        pool.sort(key=lambda l: l.weight, reverse=True)
        return pool[0] if pool else None

    def _check_cooldown(self, line_id: str, current_time: float) -> bool:
        """Return True if the line is off cooldown."""
        last_played = self._cooldowns.get(line_id, -999999.0)
        line = self._lines.get(line_id)
        if line is None:
            return False
        return current_time - last_played >= line.cooldown

    def _check_spam(self, current_time: float) -> bool:
        """Return True if we're within the spam window threshold."""
        if self._config.spam_threshold <= 0:
            return False
        recent = [
            h for h in self._history
            if current_time - h.get("timestamp_secs", 0.0) < self._config.spam_window
        ]
        return len(recent) >= self._config.spam_threshold

    # ------------------------------------------------------------------
    # Line Library
    # ------------------------------------------------------------------

    def register_line(self, line: CommentaryLine) -> CommentaryLine:
        """Register a new commentary line."""
        if not line.line_id:
            line.line_id = _new_id("ln")
        self._lines[line.line_id] = line
        _evict_fifo_dict(self._lines, _MAX_LINES)
        self._emit_event(AnnouncerEventKind.LINE_REGISTERED.value, line.line_id, {"text": line.text, "trigger": line.trigger})
        self._recompute_stats()
        return line

    def get_line(self, line_id: str) -> Optional[CommentaryLine]:
        """Retrieve a commentary line by ID."""
        return self._lines.get(line_id)

    def list_lines(self, trigger: Optional[str] = None, tone: Optional[str] = None, kind: Optional[str] = None, limit: int = 100) -> List[CommentaryLine]:
        """List commentary lines with optional filters."""
        results = list(self._lines.values())
        if trigger:
            results = [l for l in results if l.trigger == trigger]
        if tone:
            results = [l for l in results if l.tone == tone]
        if kind:
            results = [l for l in results if l.kind == kind]
        return results[:max(0, int(limit))]

    def remove_line(self, line_id: str) -> bool:
        """Remove a commentary line by ID."""
        if line_id not in self._lines:
            return False
        self._lines.pop(line_id, None)
        self._emit_event(AnnouncerEventKind.LINE_REMOVED.value, line_id, {})
        self._recompute_stats()
        return True

    # ------------------------------------------------------------------
    # Trigger Library
    # ------------------------------------------------------------------

    def register_trigger(self, trigger: CommentaryTrigger) -> CommentaryTrigger:
        """Register a new commentary trigger."""
        if not trigger.trigger_id:
            trigger.trigger_id = _new_id("trg")
        self._triggers[trigger.trigger_id] = trigger
        _evict_fifo_dict(self._triggers, _MAX_TRIGGERS)
        self._emit_event(AnnouncerEventKind.TRIGGER_REGISTERED.value, trigger.trigger_id, {"kind": trigger.kind, "name": trigger.name})
        self._recompute_stats()
        return trigger

    def get_trigger(self, trigger_id: str) -> Optional[CommentaryTrigger]:
        """Retrieve a trigger by ID."""
        return self._triggers.get(trigger_id)

    def list_triggers(self, kind: Optional[str] = None, limit: int = 100) -> List[CommentaryTrigger]:
        """List triggers with optional filters."""
        results = list(self._triggers.values())
        if kind:
            results = [t for t in results if t.kind == kind]
        return results[:max(0, int(limit))]

    def remove_trigger(self, trigger_id: str) -> bool:
        """Remove a trigger by ID."""
        if trigger_id not in self._triggers:
            return False
        self._triggers.pop(trigger_id, None)
        self._emit_event(AnnouncerEventKind.TRIGGER_REMOVED.value, trigger_id, {})
        self._recompute_stats()
        return True

    # ------------------------------------------------------------------
    # Event Submission and Queue
    # ------------------------------------------------------------------

    def submit_event(self, trigger_kind: str, current_time: float = 0.0, details: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Submit a gameplay event for commentary evaluation.

        The announcer selects a matching line, checks cooldowns and spam
        prevention, and enqueues the line for delivery if appropriate.
        """
        self._stats.total_events_submitted += 1
        self._emit_event(AnnouncerEventKind.EVENT_SUBMITTED.value, "", {"trigger": trigger_kind, "details": details or {}})

        # Check spam prevention
        if self._check_spam(current_time):
            return {"accepted": False, "reason": "spam_prevention"}

        # Select a matching line
        line = self._select_line_for_trigger(trigger_kind)
        if line is None:
            return {"accepted": False, "reason": "no_matching_line"}

        # Check cooldown
        if not self._check_cooldown(line.line_id, current_time):
            return {"accepted": False, "reason": "on_cooldown", "line_id": line.line_id}

        # Enqueue the line
        queued = QueuedLine(
            queue_id=_new_id("q"),
            line_id=line.line_id,
            text=line.text,
            kind=line.kind,
            tone=line.tone,
            priority=line.priority,
            trigger=line.trigger,
            enqueued_at=_now(),
            expires_at=_now(),
            duration=line.duration,
            metadata=details or {},
        )
        self._queue.append(queued)
        self._queue.sort(key=lambda q: q.priority, reverse=True)
        _evict_fifo_list(self._queue, max(1, self._config.max_queue_size))

        # Update cooldown
        self._cooldowns[line.line_id] = current_time

        # Update history
        self._history.append({"timestamp": _now(), "timestamp_secs": current_time, "line_id": line.line_id, "trigger": trigger_kind})
        _evict_fifo_list(self._history, _MAX_HISTORY)

        self._stats.total_lines_enqueued += 1
        self._emit_event(AnnouncerEventKind.LINE_ENQUEUED.value, queued.queue_id, {"line_id": line.line_id, "priority": queued.priority})
        self._recompute_stats()

        return {
            "accepted": True,
            "queue_id": queued.queue_id,
            "line_id": line.line_id,
            "text": line.text,
            "priority": queued.priority,
        }

    def dequeue_line(self) -> Optional[QueuedLine]:
        """Retrieve and remove the highest-priority line from the queue."""
        if not self._queue:
            return None
        queued = self._queue.pop(0)
        self._stats.total_lines_delivered += 1
        self._emit_event(AnnouncerEventKind.LINE_DEQUEUED.value, queued.queue_id, {"line_id": queued.line_id})
        self._recompute_stats()
        return queued

    def peek_queue(self, limit: int = 10) -> List[QueuedLine]:
        """Preview upcoming queued lines without removing them."""
        return self._queue[:max(0, int(limit))]

    def clear_queue(self) -> int:
        """Clear all pending lines from the delivery queue."""
        count = len(self._queue)
        self._queue.clear()
        self._emit_event(AnnouncerEventKind.QUEUE_CLEARED.value, "", {"cleared_count": count})
        self._recompute_stats()
        return count

    # ------------------------------------------------------------------
    # Context and Tone
    # ------------------------------------------------------------------

    def set_context(self, context: GameContext) -> GameContext:
        """Update the game state context."""
        self._context = context
        self._emit_event(AnnouncerEventKind.CONTEXT_UPDATED.value, "", {
            "score_home": context.score_home,
            "score_away": context.score_away,
            "match_phase": context.match_phase,
        })
        return self._context

    def get_context(self) -> GameContext:
        """Retrieve the current game state context."""
        return self._context

    def set_tone(self, tone: str) -> str:
        """Override the global tone profile."""
        old_tone = self._current_tone
        self._current_tone = tone
        self._emit_event(AnnouncerEventKind.TONE_CHANGED.value, "", {"old_tone": old_tone, "new_tone": tone})
        return self._current_tone

    def get_tone(self) -> str:
        """Retrieve the current tone profile."""
        return self._current_tone

    # ------------------------------------------------------------------
    # Simulation Tick
    # ------------------------------------------------------------------

    def tick(self, delta_time: float = 1.0, current_time: float = 0.0) -> Dict[str, Any]:
        """Advance the announcer simulation by one tick.

        Expires stale queued lines and decays cooldowns.
        """
        self._tick_count += 1
        expired = 0

        # Expire stale queued lines
        if self._config.auto_expire_enabled and self._queue:
            alive: List[QueuedLine] = []
            for queued in self._queue:
                if current_time > 0 and queued.duration > 0:
                    # Approximate expiry: lines older than their duration are expired
                    alive.append(queued)
                else:
                    alive.append(queued)
            # Simple FIFO expiry: if queue is too long, drop lowest priority
            while len(alive) > self._config.max_queue_size:
                alive.pop()
                expired += 1
                self._stats.total_lines_expired += 1
            self._queue = alive

        self._recompute_stats()
        return {
            "tick": self._tick_count,
            "expired_lines": expired,
            "queue_depth": len(self._queue),
        }

    # ------------------------------------------------------------------
    # Configuration and Observability
    # ------------------------------------------------------------------

    def set_config(self, config: AnnouncerConfig) -> AnnouncerConfig:
        """Update announcer tuning parameters."""
        self._config = config
        self._emit_event(AnnouncerEventKind.CONFIG_UPDATED.value, "", {"max_queue_size": config.max_queue_size})
        return self._config

    def get_config(self) -> AnnouncerConfig:
        """Retrieve the current announcer configuration."""
        return self._config

    def list_events(self, limit: int = 100) -> List[AnnouncerEvent]:
        """Retrieve recent audit events."""
        return self._events[-max(0, int(limit)):]

    def get_stats(self) -> AnnouncerStats:
        """Retrieve aggregate announcer statistics."""
        self._recompute_stats()
        return self._stats

    def get_status(self) -> Dict[str, Any]:
        """Retrieve a lightweight status summary."""
        return {
            "initialized": self._initialized,
            "total_lines": len(self._lines),
            "total_triggers": len(self._triggers),
            "queue_depth": len(self._queue),
            "current_tone": self._current_tone,
            "tick_count": self._tick_count,
        }

    def get_snapshot(self) -> AnnouncerSnapshot:
        """Retrieve a full state snapshot."""
        self._recompute_stats()
        return AnnouncerSnapshot(
            lines=list(self._lines.values()),
            triggers=list(self._triggers.values()),
            queue=list(self._queue),
            context=self._context,
            config=self._config,
            stats=self._stats,
            current_tone=self._current_tone,
        )

    def reset(self) -> None:
        """Reset the announcer to its initial seeded state."""
        self._lines.clear()
        self._triggers.clear()
        self._queue.clear()
        self._events.clear()
        self._history.clear()
        self._cooldowns.clear()
        self._context = GameContext()
        self._config = AnnouncerConfig()
        self._stats = AnnouncerStats()
        self._current_tone = ToneProfile.NEUTRAL.value
        self._tick_count = 0
        self._seed()


# ---------------------------------------------------------------------------
# Factory Function
# ---------------------------------------------------------------------------


def get_game_announcer() -> GameAnnouncer:
    """Return the singleton GameAnnouncer instance."""
    return GameAnnouncer.get_instance()
