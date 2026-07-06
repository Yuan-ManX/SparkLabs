"""
SparkLabs Engine - Tutorial & Guidance System

Designs, sequences and runtime-tracks guided learning experiences for
players. A ``TutorialCampaign`` is a collection of ``Lesson`` objects,
each of which is an ordered list of ``GuidanceStep`` entries. Steps are
atomic guidance actions: highlighting a UI element, displaying a
tooltip, playing a voice-over line, waiting for the player to perform a
specific input, gating progress until a condition is met, or branching
to a different lesson based on player behavior.

The engine also maintains per-player ``TutorialProgress`` records that
track which campaigns and lessons have been started, completed or
skipped, along with an adaptive ``HintQueue`` that surfaces contextual
hints when the player appears stuck. Every state transition is recorded
as a ``GuidanceEvent`` for analytics and replay debugging.

Architecture:
  TutorialGuidanceEngine (singleton)
    |-- TutorialCampaign, Lesson, GuidanceStep, BranchRule
    |-- TutorialProgress, LessonProgress, HintEntry, GuidanceContext
    |-- GuidanceStats, GuidanceSnapshot, GuidanceEvent
    |-- StepType, StepStatus, CampaignStatus, HintPriority,
        TriggerKind, AudienceTag

Core Capabilities:
  - create_campaign / update_campaign / delete_campaign: lifecycle
    management for tutorial campaigns with audience targeting.
  - add_lesson / remove_lesson / reorder_lessons: lesson composition
    within a campaign.
  - add_step / remove_step / update_step: atomic guidance step
    composition within a lesson, including branch rules.
  - start_campaign / start_lesson / advance_step / complete_step /
    skip_step / skip_campaign: runtime progression tracking.
  - evaluate_branch: dynamic branching based on player context.
  - enqueue_hint / dequeue_hint / dismiss_hint: contextual hint queue
    with priority ordering and time-to-live.
  - get_progress / get_campaign_progress / get_lesson_progress:
    per-player progress inspection.
  - list_events / get_stats / get_status / get_snapshot:
    observability and serialization.
  - reset: clear all stores and re-seed with default data.

The class implements the singleton pattern with double-checked locking
using ``threading.RLock``; consumers should obtain the instance through
:meth:`TutorialGuidanceEngine.get_instance` or the module-level
:func:`get_tutorial_guidance` factory. All public methods are guarded by
the re-entrant lock.
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

_MAX_CAMPAIGNS: int = 200
_MAX_LESSONS_PER_CAMPAIGN: int = 100
_MAX_STEPS_PER_LESSON: int = 100
_MAX_PROGRESS_RECORDS: int = 1000
_MAX_HINTS_PER_PLAYER: int = 50
_MAX_EVENTS: int = 3000


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
    """Evict the oldest entries from a dict to keep it bounded."""
    cap = max(1, int(max_size))
    while len(store) > cap:
        oldest_key = next(iter(store), None)
        if oldest_key is None:
            break
        store.pop(oldest_key, None)


def _evict_fifo_list(store: List[Any], max_size: int) -> None:
    """Evict the oldest entries from a list to keep it bounded."""
    cap = max(1, int(max_size))
    while len(store) > cap:
        if not store:
            break
        store.pop(0)


def _to_jsonable(value: Any) -> Any:
    """Convert a value into a JSON-safe representation."""
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
    """Convert a dataclass instance to a plain dictionary."""
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


class StepType(Enum):
    """The kind of action a guidance step performs.

    - ``HIGHLIGHT``: draw attention to a UI element or world object.
    - ``TOOLTIP``: display a short text bubble near a target.
    - ``VOICE_OVER``: play a narration line.
    - ``WAIT_INPUT``: wait for the player to perform a specific input.
    - ``WAIT_CONDITION``: wait until a game state condition is satisfied.
    - ``GATE``: block progression until a condition is met.
    - ``BRANCH``: evaluate branch rules to jump to another lesson.
    - ``ACTION``: trigger a game action (open menu, spawn entity, etc).
    - ``CHECKPOINT``: mark a save point the player can resume from.
    - ``CELEBRATION``: play a positive feedback animation or sound.
    """

    HIGHLIGHT = "highlight"
    TOOLTIP = "tooltip"
    VOICE_OVER = "voice_over"
    WAIT_INPUT = "wait_input"
    WAIT_CONDITION = "wait_condition"
    GATE = "gate"
    BRANCH = "branch"
    ACTION = "action"
    CHECKPOINT = "checkpoint"
    CELEBRATION = "celebration"


class StepStatus(Enum):
    """Runtime status of a guidance step for a specific player.

    - ``PENDING``: the step has not been reached yet.
    - ``ACTIVE``: the step is currently being presented.
    - ``COMPLETED``: the step was finished successfully.
    - ``SKIPPED``: the player or system skipped the step.
    - ``FAILED``: the step could not be completed (e.g. input timeout).
    """

    PENDING = "pending"
    ACTIVE = "active"
    COMPLETED = "completed"
    SKIPPED = "skipped"
    FAILED = "failed"


class CampaignStatus(Enum):
    """Runtime status of a campaign for a specific player.

    - ``NOT_STARTED``: the player has not begun the campaign.
    - ``IN_PROGRESS``: the player is actively going through lessons.
    - ``COMPLETED``: the player finished all required lessons.
    - ``SKIPPED``: the player or system skipped the campaign.
    - ``ABANDONED``: the player left the campaign incomplete.
    """

    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    SKIPPED = "skipped"
    ABANDONED = "abandoned"


class HintPriority(Enum):
    """Priority level for contextual hints.

    - ``LOW``: informational, can be safely ignored.
    - ``NORMAL``: helpful for current context.
    - ``HIGH``: important for progression.
    - ``CRITICAL``: blocking, player cannot proceed without addressing.
    """

    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    CRITICAL = "critical"


class TriggerKind(Enum):
    """What triggers a hint to surface.

    - ``MANUAL``: explicitly enqueued by the game or AI.
    - ``IDLE``: player has been idle for a duration.
    - ``REPEAT_FAIL``: player failed the same action multiple times.
    - ``PROXIMITY``: player entered a region or approached an object.
    - ``PROGRESS``: player reached a progress milestone.
    - ``CONTEXT``: game context changed (new area, new mechanic).
    """

    MANUAL = "manual"
    IDLE = "idle"
    REPEAT_FAIL = "repeat_fail"
    PROXIMITY = "proximity"
    PROGRESS = "progress"
    CONTEXT = "context"


class AudienceTag(Enum):
    """Target audience segment for a campaign.

    - ``NEW_PLAYER``: first-time players who need full onboarding.
    - ``RETURNING_PLAYER``: players returning after absence.
    - ``EXPERIENCED``: players familiar with the genre.
    - ``CHURN_RISK``: players showing signs of leaving.
    - ``ALL``: applies to every player.
    """

    NEW_PLAYER = "new_player"
    RETURNING_PLAYER = "returning_player"
    EXPERIENCED = "experienced"
    CHURN_RISK = "churn_risk"
    ALL = "all"


class GuidanceEventKind(Enum):
    """Audit event types emitted by the engine.

    - ``CAMPAIGN_CREATED``: a new campaign was defined.
    - ``CAMPAIGN_UPDATED``: campaign metadata changed.
    - ``CAMPAIGN_DELETED``: a campaign was removed.
    - ``LESSON_ADDED``: a lesson was added to a campaign.
    - ``LESSON_REMOVED``: a lesson was removed.
    - ``STEP_ADDED``: a step was added to a lesson.
    - ``STEP_REMOVED``: a step was removed.
    - ``CAMPAIGN_STARTED``: a player started a campaign.
    - ``LESSON_STARTED``: a player started a lesson.
    - ``STEP_ADVANCED``: a player advanced to a step.
    - ``STEP_COMPLETED``: a step was completed.
    - ``STEP_SKIPPED``: a step was skipped.
    - ``LESSON_COMPLETED``: a lesson was completed.
    - ``LESSON_SKIPPED``: a lesson was skipped.
    - ``CAMPAIGN_COMPLETED``: a campaign was completed.
    - ``CAMPAIGN_SKIPPED``: a campaign was skipped.
    - ``BRANCH_EVALUATED``: a branch rule fired.
    - ``HINT_ENQUEUED``: a hint was added to the queue.
    - ``HINT_SURFACED``: a hint was shown to the player.
    - ``HINT_DISMISSED``: a hint was dismissed.
    - ``CAMPAIGN_ABANDONED``: a campaign was abandoned.
    """

    CAMPAIGN_CREATED = "campaign_created"
    CAMPAIGN_UPDATED = "campaign_updated"
    CAMPAIGN_DELETED = "campaign_deleted"
    LESSON_ADDED = "lesson_added"
    LESSON_REMOVED = "lesson_removed"
    STEP_ADDED = "step_added"
    STEP_REMOVED = "step_removed"
    CAMPAIGN_STARTED = "campaign_started"
    LESSON_STARTED = "lesson_started"
    STEP_ADVANCED = "step_advanced"
    STEP_COMPLETED = "step_completed"
    STEP_SKIPPED = "step_skipped"
    LESSON_COMPLETED = "lesson_completed"
    LESSON_SKIPPED = "lesson_skipped"
    CAMPAIGN_COMPLETED = "campaign_completed"
    CAMPAIGN_SKIPPED = "campaign_skipped"
    BRANCH_EVALUATED = "branch_evaluated"
    HINT_ENQUEUED = "hint_enqueued"
    HINT_SURFACED = "hint_surfaced"
    HINT_DISMISSED = "hint_dismissed"
    CAMPAIGN_ABANDONED = "campaign_abandoned"


# ---------------------------------------------------------------------------
# Data Classes
# ---------------------------------------------------------------------------


@dataclass
class BranchRule:
    """A conditional jump rule evaluated during a BRANCH step.

    When the condition expression evaluates truthy in the player's
    context, the engine jumps to ``target_lesson_id``. Otherwise the
    next rule is checked; if no rule matches, the lesson continues to
    the next step.
    """

    rule_id: str
    condition: str
    target_lesson_id: str
    priority: int = 0
    description: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class GuidanceStep:
    """An atomic guidance action within a lesson.

    Steps are executed in order. Some step types (WAIT_INPUT,
    WAIT_CONDITION, GATE) block progression until a condition is
    satisfied. BRANCH steps evaluate ``branch_rules`` to jump to a
    different lesson.
    """

    step_id: str
    step_type: StepType
    title: str = ""
    description: str = ""
    target_element: str = ""
    tooltip_text: str = ""
    voice_line: str = ""
    expected_input: str = ""
    condition_expression: str = ""
    action_command: str = ""
    action_payload: Dict[str, Any] = field(default_factory=dict)
    branch_rules: List[BranchRule] = field(default_factory=list)
    required: bool = True
    timeout_seconds: float = 0.0
    sort_order: int = 0
    created_at: str = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class Lesson:
    """A sequence of guidance steps teaching a specific mechanic.

    Lessons are the primary unit of tutorial progression. Each lesson
    belongs to exactly one campaign and has an ordered list of steps.
    """

    lesson_id: str
    campaign_id: str
    name: str
    description: str = ""
    mechanic: str = ""
    estimated_minutes: float = 2.0
    required: bool = True
    sort_order: int = 0
    steps: List[GuidanceStep] = field(default_factory=list)
    created_at: str = field(default_factory=_now)
    updated_at: str = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class TutorialCampaign:
    """A top-level tutorial container targeting a player audience.

    Campaigns group related lessons and carry audience targeting
    metadata so the AI can select the right onboarding flow for each
    player segment.
    """

    campaign_id: str
    name: str
    description: str = ""
    audience: AudienceTag = AudienceTag.ALL
    locale: str = "en"
    active: bool = True
    priority: int = 0
    tags: List[str] = field(default_factory=list)
    lessons: List[Lesson] = field(default_factory=list)
    created_at: str = field(default_factory=_now)
    updated_at: str = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class StepProgress:
    """Per-player runtime status of a single guidance step."""

    step_id: str
    status: StepStatus = StepStatus.PENDING
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    attempt_count: int = 0
    time_spent_seconds: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class LessonProgress:
    """Per-player runtime status of a single lesson."""

    lesson_id: str
    status: CampaignStatus = CampaignStatus.NOT_STARTED
    current_step_index: int = 0
    steps: List[StepProgress] = field(default_factory=list)
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    time_spent_seconds: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class TutorialProgress:
    """Per-player runtime status of a full campaign."""

    progress_id: str
    player_id: str
    campaign_id: str
    status: CampaignStatus = CampaignStatus.NOT_STARTED
    current_lesson_index: int = 0
    lessons: List[LessonProgress] = field(default_factory=list)
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    last_active_at: Optional[str] = None
    total_time_seconds: float = 0.0
    completion_percentage: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class HintEntry:
    """A contextual hint in a player's hint queue.

    Hints are prioritized and may expire after ``ttl_seconds``. The
    engine surfaces the highest-priority non-expired hint when the
    game polls for hints.
    """

    hint_id: str
    player_id: str
    text: str
    priority: HintPriority = HintPriority.NORMAL
    trigger: TriggerKind = TriggerKind.MANUAL
    target_element: str = ""
    context_key: str = ""
    ttl_seconds: float = 30.0
    enqueued_at: str = field(default_factory=_now)
    surfaced: bool = False
    surfaced_at: Optional[str] = None
    dismissed: bool = False
    dismissed_at: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class GuidanceContext:
    """Snapshot of player context used for branch evaluation.

    The context is a free-form dictionary of key-value pairs that
    branch condition expressions can reference. Typical keys include
    ``skill_level``, ``fail_count``, ``time_in_area``, ``locale`` and
    ``device_type``.
    """

    player_id: str
    campaign_id: str
    lesson_id: str
    step_id: str
    context: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class GuidanceStats:
    """Aggregate statistics for the guidance engine."""

    total_campaigns: int = 0
    total_lessons: int = 0
    total_steps: int = 0
    active_campaigns: int = 0
    total_progress_records: int = 0
    campaigns_started: int = 0
    campaigns_completed: int = 0
    campaigns_skipped: int = 0
    campaigns_abandoned: int = 0
    lessons_completed: int = 0
    steps_completed: int = 0
    steps_skipped: int = 0
    hints_enqueued: int = 0
    hints_surfaced: int = 0
    hints_dismissed: int = 0
    branches_evaluated: int = 0
    event_counter: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class GuidanceSnapshot:
    """Full state snapshot for persistence or debugging."""

    campaigns: List[Dict[str, Any]] = field(default_factory=list)
    progress: List[Dict[str, Any]] = field(default_factory=list)
    hints: List[Dict[str, Any]] = field(default_factory=list)
    events: List[Dict[str, Any]] = field(default_factory=list)
    stats: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class GuidanceEvent:
    """Audit event emitted on every state transition."""

    event_id: str
    kind: GuidanceEventKind
    timestamp: str
    player_id: str = ""
    campaign_id: str = ""
    lesson_id: str = ""
    step_id: str = ""
    payload: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


# ---------------------------------------------------------------------------
# Engine
# ---------------------------------------------------------------------------


class TutorialGuidanceEngine:
    """Singleton engine for designing and runtime-tracking guided tutorials.

    The engine stores campaign definitions, per-player progress records,
    hint queues and an audit event log. All public methods are guarded by
    a re-entrant lock for thread safety.
    """

    _instance: Optional["TutorialGuidanceEngine"] = None
    _lock: threading.RLock = threading.RLock()

    @classmethod
    def get_instance(cls) -> "TutorialGuidanceEngine":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def __new__(cls) -> "TutorialGuidanceEngine":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    inst = super().__new__(cls)
                    inst._initialized = False
                    cls._instance = inst
        return cls._instance

    def __init__(self) -> None:
        if getattr(self, "_initialized", False):
            return
        with self._lock:
            if getattr(self, "_initialized", False):
                return
            self._initialized: bool = False
            self._campaigns: Dict[str, TutorialCampaign] = {}
            self._progress: Dict[str, TutorialProgress] = {}
            self._hints: Dict[str, List[HintEntry]] = {}
            self._events: List[GuidanceEvent] = []
            self._campaign_counter: int = 0
            self._lesson_counter: int = 0
            self._step_counter: int = 0
            self._progress_counter: int = 0
            self._hint_counter: int = 0
            self._campaigns_started: int = 0
            self._campaigns_completed: int = 0
            self._campaigns_skipped: int = 0
            self._campaigns_abandoned: int = 0
            self._lessons_completed: int = 0
            self._steps_completed: int = 0
            self._steps_skipped: int = 0
            self._hints_enqueued: int = 0
            self._hints_surfaced: int = 0
            self._hints_dismissed: int = 0
            self._branches_evaluated: int = 0
            self._event_counter: int = 0
            self._seed_data()
            self._initialized = True

    # ------------------------------------------------------------------
    # Campaign Management
    # ------------------------------------------------------------------

    def create_campaign(
        self,
        name: str,
        description: str = "",
        audience: AudienceTag = AudienceTag.ALL,
        locale: str = "en",
        active: bool = True,
        priority: int = 0,
        tags: Optional[List[str]] = None,
    ) -> TutorialCampaign:
        """Create and register a new tutorial campaign."""
        with self._lock:
            campaign_id = _new_id("camp")
            campaign = TutorialCampaign(
                campaign_id=campaign_id,
                name=name,
                description=description,
                audience=audience,
                locale=locale,
                active=active,
                priority=priority,
                tags=tags or [],
            )
            self._campaigns[campaign_id] = campaign
            self._campaign_counter += 1
            self._record_event(
                GuidanceEventKind.CAMPAIGN_CREATED,
                campaign_id=campaign_id,
                payload={"name": name, "audience": audience.value},
            )
            _evict_fifo_dict(self._campaigns, _MAX_CAMPAIGNS)
            return campaign

    def update_campaign(
        self,
        campaign_id: str,
        updates: Dict[str, Any],
    ) -> Optional[TutorialCampaign]:
        """Update mutable fields of a campaign."""
        with self._lock:
            campaign = self._campaigns.get(campaign_id)
            if campaign is None:
                return None
            if "name" in updates:
                campaign.name = str(updates["name"])
            if "description" in updates:
                campaign.description = str(updates["description"])
            if "audience" in updates:
                campaign.audience = AudienceTag(updates["audience"])
            if "locale" in updates:
                campaign.locale = str(updates["locale"])
            if "active" in updates:
                campaign.active = bool(updates["active"])
            if "priority" in updates:
                campaign.priority = int(updates["priority"])
            if "tags" in updates:
                campaign.tags = list(updates["tags"])
            campaign.updated_at = _now()
            self._record_event(
                GuidanceEventKind.CAMPAIGN_UPDATED,
                campaign_id=campaign_id,
                payload=updates,
            )
            return campaign

    def delete_campaign(self, campaign_id: str) -> bool:
        """Remove a campaign and all its lessons and steps."""
        with self._lock:
            existed = self._campaigns.pop(campaign_id, None) is not None
            if existed:
                self._record_event(
                    GuidanceEventKind.CAMPAIGN_DELETED,
                    campaign_id=campaign_id,
                )
            return existed

    def get_campaign(self, campaign_id: str) -> Optional[TutorialCampaign]:
        with self._lock:
            return self._campaigns.get(campaign_id)

    def list_campaigns(
        self,
        audience: Optional[AudienceTag] = None,
        active_only: bool = False,
    ) -> List[TutorialCampaign]:
        with self._lock:
            out: List[TutorialCampaign] = []
            for c in self._campaigns.values():
                if active_only and not c.active:
                    continue
                if audience is not None and c.audience != audience and c.audience != AudienceTag.ALL:
                    continue
                out.append(c)
            out.sort(key=lambda x: (-x.priority, x.created_at))
            return out

    # ------------------------------------------------------------------
    # Lesson Management
    # ------------------------------------------------------------------

    def add_lesson(
        self,
        campaign_id: str,
        name: str,
        description: str = "",
        mechanic: str = "",
        estimated_minutes: float = 2.0,
        required: bool = True,
        sort_order: Optional[int] = None,
    ) -> Optional[Lesson]:
        """Add a lesson to a campaign."""
        with self._lock:
            campaign = self._campaigns.get(campaign_id)
            if campaign is None:
                return None
            lesson_id = _new_id("less")
            order = len(campaign.lessons) if sort_order is None else int(sort_order)
            lesson = Lesson(
                lesson_id=lesson_id,
                campaign_id=campaign_id,
                name=name,
                description=description,
                mechanic=mechanic,
                estimated_minutes=float(estimated_minutes),
                required=bool(required),
                sort_order=order,
            )
            campaign.lessons.append(lesson)
            self._lesson_counter += 1
            campaign.updated_at = _now()
            self._record_event(
                GuidanceEventKind.LESSON_ADDED,
                campaign_id=campaign_id,
                lesson_id=lesson_id,
                payload={"name": name, "mechanic": mechanic},
            )
            _evict_fifo_list(campaign.lessons, _MAX_LESSONS_PER_CAMPAIGN)
            return lesson

    def remove_lesson(self, campaign_id: str, lesson_id: str) -> bool:
        with self._lock:
            campaign = self._campaigns.get(campaign_id)
            if campaign is None:
                return False
            before = len(campaign.lessons)
            campaign.lessons = [l for l in campaign.lessons if l.lesson_id != lesson_id]
            removed = len(campaign.lessons) < before
            if removed:
                campaign.updated_at = _now()
                self._record_event(
                    GuidanceEventKind.LESSON_REMOVED,
                    campaign_id=campaign_id,
                    lesson_id=lesson_id,
                )
            return removed

    def reorder_lessons(self, campaign_id: str, lesson_ids: List[str]) -> bool:
        """Reorder lessons within a campaign to match the given ID list."""
        with self._lock:
            campaign = self._campaigns.get(campaign_id)
            if campaign is None:
                return False
            lookup = {l.lesson_id: l for l in campaign.lessons}
            new_order: List[Lesson] = []
            for idx, lid in enumerate(lesson_ids):
                lesson = lookup.get(lid)
                if lesson is None:
                    return False
                lesson.sort_order = idx
                new_order.append(lesson)
            campaign.lessons = new_order
            campaign.updated_at = _now()
            return True

    def get_lesson(self, campaign_id: str, lesson_id: str) -> Optional[Lesson]:
        with self._lock:
            campaign = self._campaigns.get(campaign_id)
            if campaign is None:
                return None
            for l in campaign.lessons:
                if l.lesson_id == lesson_id:
                    return l
            return None

    # ------------------------------------------------------------------
    # Step Management
    # ------------------------------------------------------------------

    def add_step(
        self,
        campaign_id: str,
        lesson_id: str,
        step_type: StepType,
        title: str = "",
        description: str = "",
        target_element: str = "",
        tooltip_text: str = "",
        voice_line: str = "",
        expected_input: str = "",
        condition_expression: str = "",
        action_command: str = "",
        action_payload: Optional[Dict[str, Any]] = None,
        branch_rules: Optional[List[Dict[str, Any]]] = None,
        required: bool = True,
        timeout_seconds: float = 0.0,
        sort_order: Optional[int] = None,
    ) -> Optional[GuidanceStep]:
        """Add a guidance step to a lesson."""
        with self._lock:
            lesson = self.get_lesson(campaign_id, lesson_id)
            if lesson is None:
                return None
            step_id = _new_id("step")
            order = len(lesson.steps) if sort_order is None else int(sort_order)
            rules: List[BranchRule] = []
            if branch_rules:
                for r in branch_rules:
                    rules.append(
                        BranchRule(
                            rule_id=_new_id("rule"),
                            condition=str(r.get("condition", "")),
                            target_lesson_id=str(r.get("target_lesson_id", "")),
                            priority=int(r.get("priority", 0)),
                            description=str(r.get("description", "")),
                        )
                    )
            step = GuidanceStep(
                step_id=step_id,
                step_type=step_type,
                title=title,
                description=description,
                target_element=target_element,
                tooltip_text=tooltip_text,
                voice_line=voice_line,
                expected_input=expected_input,
                condition_expression=condition_expression,
                action_command=action_command,
                action_payload=action_payload or {},
                branch_rules=rules,
                required=required,
                timeout_seconds=float(timeout_seconds),
                sort_order=order,
            )
            lesson.steps.append(step)
            lesson.updated_at = _now()
            self._step_counter += 1
            self._record_event(
                GuidanceEventKind.STEP_ADDED,
                campaign_id=campaign_id,
                lesson_id=lesson_id,
                step_id=step_id,
                payload={"step_type": step_type.value, "title": title},
            )
            _evict_fifo_list(lesson.steps, _MAX_STEPS_PER_LESSON)
            return step

    def remove_step(self, campaign_id: str, lesson_id: str, step_id: str) -> bool:
        with self._lock:
            lesson = self.get_lesson(campaign_id, lesson_id)
            if lesson is None:
                return False
            before = len(lesson.steps)
            lesson.steps = [s for s in lesson.steps if s.step_id != step_id]
            removed = len(lesson.steps) < before
            if removed:
                lesson.updated_at = _now()
                self._record_event(
                    GuidanceEventKind.STEP_REMOVED,
                    campaign_id=campaign_id,
                    lesson_id=lesson_id,
                    step_id=step_id,
                )
            return removed

    def update_step(
        self,
        campaign_id: str,
        lesson_id: str,
        step_id: str,
        updates: Dict[str, Any],
    ) -> Optional[GuidanceStep]:
        """Update mutable fields of a guidance step."""
        with self._lock:
            lesson = self.get_lesson(campaign_id, lesson_id)
            if lesson is None:
                return None
            for s in lesson.steps:
                if s.step_id == step_id:
                    if "title" in updates:
                        s.title = str(updates["title"])
                    if "description" in updates:
                        s.description = str(updates["description"])
                    if "target_element" in updates:
                        s.target_element = str(updates["target_element"])
                    if "tooltip_text" in updates:
                        s.tooltip_text = str(updates["tooltip_text"])
                    if "voice_line" in updates:
                        s.voice_line = str(updates["voice_line"])
                    if "expected_input" in updates:
                        s.expected_input = str(updates["expected_input"])
                    if "condition_expression" in updates:
                        s.condition_expression = str(updates["condition_expression"])
                    if "action_command" in updates:
                        s.action_command = str(updates["action_command"])
                    if "required" in updates:
                        s.required = bool(updates["required"])
                    if "timeout_seconds" in updates:
                        s.timeout_seconds = float(updates["timeout_seconds"])
                    lesson.updated_at = _now()
                    return s
            return None

    # ------------------------------------------------------------------
    # Runtime Progression
    # ------------------------------------------------------------------

    def start_campaign(self, player_id: str, campaign_id: str) -> Optional[TutorialProgress]:
        """Begin a campaign for a player, initializing lesson progress."""
        with self._lock:
            campaign = self._campaigns.get(campaign_id)
            if campaign is None:
                return None
            progress_id = _new_id("prog")
            lesson_progress_list: List[LessonProgress] = []
            for lesson in campaign.lessons:
                lp = LessonProgress(lesson_id=lesson.lesson_id)
                for step in lesson.steps:
                    lp.steps.append(StepProgress(step_id=step.step_id))
                lesson_progress_list.append(lp)
            progress = TutorialProgress(
                progress_id=progress_id,
                player_id=player_id,
                campaign_id=campaign_id,
                status=CampaignStatus.IN_PROGRESS,
                current_lesson_index=0,
                lessons=lesson_progress_list,
                started_at=_now(),
                last_active_at=_now(),
            )
            self._progress[progress_id] = progress
            self._progress_counter += 1
            self._campaigns_started += 1
            self._record_event(
                GuidanceEventKind.CAMPAIGN_STARTED,
                player_id=player_id,
                campaign_id=campaign_id,
                payload={"progress_id": progress_id},
            )
            _evict_fifo_dict(self._progress, _MAX_PROGRESS_RECORDS)
            return progress

    def start_lesson(self, progress_id: str, lesson_index: int) -> Optional[TutorialProgress]:
        """Mark a lesson as started and set the current lesson index."""
        with self._lock:
            progress = self._progress.get(progress_id)
            if progress is None:
                return None
            if lesson_index < 0 or lesson_index >= len(progress.lessons):
                return None
            lp = progress.lessons[lesson_index]
            if lp.status == CampaignStatus.NOT_STARTED:
                lp.status = CampaignStatus.IN_PROGRESS
                lp.started_at = _now()
                if lp.steps:
                    lp.steps[0].status = StepStatus.ACTIVE
                    lp.steps[0].started_at = _now()
                progress.current_lesson_index = lesson_index
                progress.last_active_at = _now()
                self._record_event(
                    GuidanceEventKind.LESSON_STARTED,
                    player_id=progress.player_id,
                    campaign_id=progress.campaign_id,
                    lesson_id=lp.lesson_id,
                    payload={"lesson_index": lesson_index},
                )
            return progress

    def advance_step(self, progress_id: str) -> Optional[TutorialProgress]:
        """Advance to the next step in the current lesson.

        Completes the current step, marks the next step as active, and
        auto-completes the lesson if there are no more steps.
        """
        with self._lock:
            progress = self._progress.get(progress_id)
            if progress is None:
                return None
            idx = progress.current_lesson_index
            if idx < 0 or idx >= len(progress.lessons):
                return None
            lp = progress.lessons[idx]
            step_idx = lp.current_step_index
            if step_idx < 0 or step_idx >= len(lp.steps):
                return None
            current = lp.steps[step_idx]
            current.status = StepStatus.COMPLETED
            current.completed_at = _now()
            self._steps_completed += 1
            self._record_event(
                GuidanceEventKind.STEP_COMPLETED,
                player_id=progress.player_id,
                campaign_id=progress.campaign_id,
                lesson_id=lp.lesson_id,
                step_id=current.step_id,
            )
            next_idx = step_idx + 1
            if next_idx >= len(lp.steps):
                lp.status = CampaignStatus.COMPLETED
                lp.completed_at = _now()
                self._lessons_completed += 1
                self._record_event(
                    GuidanceEventKind.LESSON_COMPLETED,
                    player_id=progress.player_id,
                    campaign_id=progress.campaign_id,
                    lesson_id=lp.lesson_id,
                )
                self._update_completion_percentage(progress)
                next_lesson_idx = idx + 1
                if next_lesson_idx >= len(progress.lessons):
                    progress.status = CampaignStatus.COMPLETED
                    progress.completed_at = _now()
                    self._campaigns_completed += 1
                    self._record_event(
                        GuidanceEventKind.CAMPAIGN_COMPLETED,
                        player_id=progress.player_id,
                        campaign_id=progress.campaign_id,
                    )
                else:
                    progress.current_lesson_index = next_lesson_idx
            else:
                lp.current_step_index = next_idx
                lp.steps[next_idx].status = StepStatus.ACTIVE
                lp.steps[next_idx].started_at = _now()
                self._record_event(
                    GuidanceEventKind.STEP_ADVANCED,
                    player_id=progress.player_id,
                    campaign_id=progress.campaign_id,
                    lesson_id=lp.lesson_id,
                    step_id=lp.steps[next_idx].step_id,
                )
            progress.last_active_at = _now()
            return progress

    def complete_step(self, progress_id: str) -> Optional[TutorialProgress]:
        """Explicitly complete the current step (alias for advance_step)."""
        return self.advance_step(progress_id)

    def skip_step(self, progress_id: str) -> Optional[TutorialProgress]:
        """Skip the current step and advance to the next one."""
        with self._lock:
            progress = self._progress.get(progress_id)
            if progress is None:
                return None
            idx = progress.current_lesson_index
            if idx < 0 or idx >= len(progress.lessons):
                return None
            lp = progress.lessons[idx]
            step_idx = lp.current_step_index
            if step_idx < 0 or step_idx >= len(lp.steps):
                return None
            current = lp.steps[step_idx]
            current.status = StepStatus.SKIPPED
            current.completed_at = _now()
            self._steps_skipped += 1
            self._record_event(
                GuidanceEventKind.STEP_SKIPPED,
                player_id=progress.player_id,
                campaign_id=progress.campaign_id,
                lesson_id=lp.lesson_id,
                step_id=current.step_id,
            )
            return self.advance_step(progress_id)

    def skip_lesson(self, progress_id: str, lesson_index: Optional[int] = None) -> Optional[TutorialProgress]:
        """Skip an entire lesson, marking all remaining steps as skipped."""
        with self._lock:
            progress = self._progress.get(progress_id)
            if progress is None:
                return None
            idx = lesson_index if lesson_index is not None else progress.current_lesson_index
            if idx < 0 or idx >= len(progress.lessons):
                return None
            lp = progress.lessons[idx]
            lp.status = CampaignStatus.SKIPPED
            lp.completed_at = _now()
            for sp in lp.steps:
                if sp.status not in (StepStatus.COMPLETED, StepStatus.SKIPPED):
                    sp.status = StepStatus.SKIPPED
                    sp.completed_at = _now()
                    self._steps_skipped += 1
            self._record_event(
                GuidanceEventKind.LESSON_SKIPPED,
                player_id=progress.player_id,
                campaign_id=progress.campaign_id,
                lesson_id=lp.lesson_id,
            )
            self._update_completion_percentage(progress)
            next_idx = idx + 1
            if next_idx >= len(progress.lessons):
                progress.status = CampaignStatus.COMPLETED
                progress.completed_at = _now()
                self._campaigns_completed += 1
                self._record_event(
                    GuidanceEventKind.CAMPAIGN_COMPLETED,
                    player_id=progress.player_id,
                    campaign_id=progress.campaign_id,
                )
            else:
                progress.current_lesson_index = next_idx
            progress.last_active_at = _now()
            return progress

    def skip_campaign(self, progress_id: str) -> Optional[TutorialProgress]:
        """Skip the entire campaign for this player."""
        with self._lock:
            progress = self._progress.get(progress_id)
            if progress is None:
                return None
            progress.status = CampaignStatus.SKIPPED
            progress.completed_at = _now()
            self._campaigns_skipped += 1
            for lp in progress.lessons:
                if lp.status not in (CampaignStatus.COMPLETED, CampaignStatus.SKIPPED):
                    lp.status = CampaignStatus.SKIPPED
                    lp.completed_at = _now()
                    for sp in lp.steps:
                        if sp.status not in (StepStatus.COMPLETED, StepStatus.SKIPPED):
                            sp.status = StepStatus.SKIPPED
                            sp.completed_at = _now()
                            self._steps_skipped += 1
            self._record_event(
                GuidanceEventKind.CAMPAIGN_SKIPPED,
                player_id=progress.player_id,
                campaign_id=progress.campaign_id,
            )
            progress.last_active_at = _now()
            return progress

    def abandon_campaign(self, progress_id: str) -> Optional[TutorialProgress]:
        """Mark a campaign as abandoned (player left without completing)."""
        with self._lock:
            progress = self._progress.get(progress_id)
            if progress is None:
                return None
            progress.status = CampaignStatus.ABANDONED
            progress.last_active_at = _now()
            self._campaigns_abandoned += 1
            self._record_event(
                GuidanceEventKind.CAMPAIGN_ABANDONED,
                player_id=progress.player_id,
                campaign_id=progress.campaign_id,
            )
            return progress

    # ------------------------------------------------------------------
    # Branch Evaluation
    # ------------------------------------------------------------------

    def evaluate_branch(
        self,
        progress_id: str,
        context: Dict[str, Any],
    ) -> Optional[str]:
        """Evaluate branch rules for the current BRANCH step.

        Returns the ``target_lesson_id`` if a rule matches, or ``None``
        if no rule fires (in which case the lesson continues normally).
        """
        with self._lock:
            progress = self._progress.get(progress_id)
            if progress is None:
                return None
            campaign = self._campaigns.get(progress.campaign_id)
            if campaign is None:
                return None
            idx = progress.current_lesson_index
            if idx < 0 or idx >= len(progress.lessons):
                return None
            lp = progress.lessons[idx]
            step_idx = lp.current_step_index
            if step_idx < 0 or step_idx >= len(lp.steps):
                return None
            current_step_id = lp.steps[step_idx].step_id
            lesson = None
            for l in campaign.lessons:
                if l.lesson_id == lp.lesson_id:
                    lesson = l
                    break
            if lesson is None:
                return None
            step = None
            for s in lesson.steps:
                if s.step_id == current_step_id:
                    step = s
                    break
            if step is None or step.step_type != StepType.BRANCH:
                return None
            self._branches_evaluated += 1
            sorted_rules = sorted(step.branch_rules, key=lambda r: -r.priority)
            target = None
            for rule in sorted_rules:
                if self._eval_condition(rule.condition, context):
                    target = rule.target_lesson_id
                    self._record_event(
                        GuidanceEventKind.BRANCH_EVALUATED,
                        player_id=progress.player_id,
                        campaign_id=progress.campaign_id,
                        lesson_id=lp.lesson_id,
                        step_id=current_step_id,
                        payload={
                            "rule_id": rule.rule_id,
                            "target_lesson_id": target,
                            "condition": rule.condition,
                        },
                    )
                    break
            return target

    def _eval_condition(self, expression: str, context: Dict[str, Any]) -> bool:
        """Safely evaluate a condition expression against a context dict.

        Supports ``key==value``, ``key!=value``, ``key>=value``,
        ``key<=value``, ``key>value`` and ``key<value`` comparisons
        and the literals ``true`` / ``false``. Unsupported expressions
        default to ``False``.
        """
        expr = expression.strip()
        if not expr:
            return False
        if expr.lower() == "true":
            return True
        if expr.lower() == "false":
            return False
        for op in (">=", "<=", "==", "!=", ">", "<"):
            if op in expr:
                left, right = expr.split(op, 1)
                left = left.strip()
                right = right.strip()
                left_val = context.get(left, left)
                try:
                    left_num = float(left_val)
                    right_num = float(right)
                    if op == "==":
                        return left_num == right_num
                    if op == "!=":
                        return left_num != right_num
                    if op == ">=":
                        return left_num >= right_num
                    if op == "<=":
                        return left_num <= right_num
                    if op == ">":
                        return left_num > right_num
                    return left_num < right_num
                except (ValueError, TypeError):
                    if right.lower() == "true":
                        right_val = True
                    elif right.lower() == "false":
                        right_val = False
                    else:
                        right_val = right
                    if op == "==":
                        return str(left_val) == str(right_val)
                    if op == "!=":
                        return str(left_val) != str(right_val)
                    return False
        return bool(context.get(expr, False))

    def _update_completion_percentage(self, progress: TutorialProgress) -> None:
        """Recompute the completion percentage for a progress record."""
        total_lessons = len(progress.lessons)
        if total_lessons == 0:
            progress.completion_percentage = 100.0
            return
        done = sum(
            1 for lp in progress.lessons
            if lp.status in (CampaignStatus.COMPLETED, CampaignStatus.SKIPPED)
        )
        progress.completion_percentage = round((done / total_lessons) * 100.0, 2)

    # ------------------------------------------------------------------
    # Hint Queue
    # ------------------------------------------------------------------

    def enqueue_hint(
        self,
        player_id: str,
        text: str,
        priority: HintPriority = HintPriority.NORMAL,
        trigger: TriggerKind = TriggerKind.MANUAL,
        target_element: str = "",
        context_key: str = "",
        ttl_seconds: float = 30.0,
    ) -> HintEntry:
        """Add a contextual hint to a player's hint queue."""
        with self._lock:
            hint_id = _new_id("hint")
            hint = HintEntry(
                hint_id=hint_id,
                player_id=player_id,
                text=text,
                priority=priority,
                trigger=trigger,
                target_element=target_element,
                context_key=context_key,
                ttl_seconds=float(ttl_seconds),
            )
            queue = self._hints.setdefault(player_id, [])
            queue.append(hint)
            self._hint_counter += 1
            self._hints_enqueued += 1
            self._record_event(
                GuidanceEventKind.HINT_ENQUEUED,
                player_id=player_id,
                payload={
                    "hint_id": hint_id,
                    "priority": priority.value,
                    "trigger": trigger.value,
                },
            )
            _evict_fifo_list(queue, _MAX_HINTS_PER_PLAYER)
            return hint

    def dequeue_hint(self, player_id: str) -> Optional[HintEntry]:
        """Surface the highest-priority non-expired, non-dismissed hint."""
        with self._lock:
            queue = self._hints.get(player_id, [])
            now = datetime.utcnow()
            best: Optional[HintEntry] = None
            best_idx = -1
            priority_order = {
                HintPriority.CRITICAL: 4,
                HintPriority.HIGH: 3,
                HintPriority.NORMAL: 2,
                HintPriority.LOW: 1,
            }
            for i, h in enumerate(queue):
                if h.dismissed or h.surfaced:
                    continue
                enq_time = datetime.strptime(h.enqueued_at[:19], "%Y-%m-%dT%H:%M:%S")
                elapsed = (now - enq_time).total_seconds()
                if h.ttl_seconds > 0 and elapsed > h.ttl_seconds:
                    h.dismissed = True
                    h.dismissed_at = _now()
                    continue
                if best is None or priority_order.get(h.priority, 0) > priority_order.get(best.priority, 0):
                    best = h
                    best_idx = i
            if best is not None:
                best.surfaced = True
                best.surfaced_at = _now()
                self._hints_surfaced += 1
                self._record_event(
                    GuidanceEventKind.HINT_SURFACED,
                    player_id=player_id,
                    payload={"hint_id": best.hint_id},
                )
            return best

    def dismiss_hint(self, player_id: str, hint_id: str) -> bool:
        """Mark a specific hint as dismissed."""
        with self._lock:
            queue = self._hints.get(player_id, [])
            for h in queue:
                if h.hint_id == hint_id:
                    h.dismissed = True
                    h.dismissed_at = _now()
                    self._hints_dismissed += 1
                    self._record_event(
                        GuidanceEventKind.HINT_DISMISSED,
                        player_id=player_id,
                        payload={"hint_id": hint_id},
                    )
                    return True
            return False

    def list_hints(self, player_id: str, include_dismissed: bool = False) -> List[HintEntry]:
        with self._lock:
            queue = self._hints.get(player_id, [])
            if include_dismissed:
                return list(queue)
            return [h for h in queue if not h.dismissed]

    # ------------------------------------------------------------------
    # Progress Inspection
    # ------------------------------------------------------------------

    def get_progress(self, progress_id: str) -> Optional[TutorialProgress]:
        with self._lock:
            return self._progress.get(progress_id)

    def get_campaign_progress(
        self,
        player_id: str,
        campaign_id: str,
    ) -> Optional[TutorialProgress]:
        """Find a player's progress record for a specific campaign."""
        with self._lock:
            for p in self._progress.values():
                if p.player_id == player_id and p.campaign_id == campaign_id:
                    return p
            return None

    def list_progress(
        self,
        player_id: Optional[str] = None,
        campaign_id: Optional[str] = None,
    ) -> List[TutorialProgress]:
        with self._lock:
            out: List[TutorialProgress] = []
            for p in self._progress.values():
                if player_id is not None and p.player_id != player_id:
                    continue
                if campaign_id is not None and p.campaign_id != campaign_id:
                    continue
                out.append(p)
            return out

    # ------------------------------------------------------------------
    # Observability
    # ------------------------------------------------------------------

    def list_events(
        self,
        kind: Optional[GuidanceEventKind] = None,
        player_id: Optional[str] = None,
        campaign_id: Optional[str] = None,
        limit: int = 100,
    ) -> List[GuidanceEvent]:
        with self._lock:
            out: List[GuidanceEvent] = []
            for e in reversed(self._events):
                if kind is not None and e.kind != kind:
                    continue
                if player_id is not None and e.player_id != player_id:
                    continue
                if campaign_id is not None and e.campaign_id != campaign_id:
                    continue
                out.append(e)
                if len(out) >= int(limit):
                    break
            return out

    def get_stats(self) -> GuidanceStats:
        with self._lock:
            active_campaigns = sum(1 for c in self._campaigns.values() if c.active)
            total_lessons = sum(len(c.lessons) for c in self._campaigns.values())
            total_steps = sum(
                len(l.steps) for c in self._campaigns.values() for l in c.lessons
            )
            return GuidanceStats(
                total_campaigns=len(self._campaigns),
                total_lessons=total_lessons,
                total_steps=total_steps,
                active_campaigns=active_campaigns,
                total_progress_records=len(self._progress),
                campaigns_started=self._campaigns_started,
                campaigns_completed=self._campaigns_completed,
                campaigns_skipped=self._campaigns_skipped,
                campaigns_abandoned=self._campaigns_abandoned,
                lessons_completed=self._lessons_completed,
                steps_completed=self._steps_completed,
                steps_skipped=self._steps_skipped,
                hints_enqueued=self._hints_enqueued,
                hints_surfaced=self._hints_surfaced,
                hints_dismissed=self._hints_dismissed,
                branches_evaluated=self._branches_evaluated,
                event_counter=self._event_counter,
            )

    def get_status(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "initialized": self._initialized,
                "total_campaigns": len(self._campaigns),
                "total_progress": len(self._progress),
                "total_hint_queues": len(self._hints),
                "total_events": len(self._events),
                "campaign_counter": self._campaign_counter,
                "lesson_counter": self._lesson_counter,
                "step_counter": self._step_counter,
                "progress_counter": self._progress_counter,
                "hint_counter": self._hint_counter,
                "campaigns_started": self._campaigns_started,
                "campaigns_completed": self._campaigns_completed,
                "campaigns_skipped": self._campaigns_skipped,
                "campaigns_abandoned": self._campaigns_abandoned,
                "lessons_completed": self._lessons_completed,
                "steps_completed": self._steps_completed,
                "steps_skipped": self._steps_skipped,
                "hints_enqueued": self._hints_enqueued,
                "hints_surfaced": self._hints_surfaced,
                "hints_dismissed": self._hints_dismissed,
                "branches_evaluated": self._branches_evaluated,
                "event_counter": self._event_counter,
                "capacities": {
                    "max_campaigns": _MAX_CAMPAIGNS,
                    "max_lessons_per_campaign": _MAX_LESSONS_PER_CAMPAIGN,
                    "max_steps_per_lesson": _MAX_STEPS_PER_LESSON,
                    "max_progress_records": _MAX_PROGRESS_RECORDS,
                    "max_hints_per_player": _MAX_HINTS_PER_PLAYER,
                    "max_events": _MAX_EVENTS,
                },
            }

    def get_snapshot(self) -> GuidanceSnapshot:
        with self._lock:
            return GuidanceSnapshot(
                campaigns=[c.to_dict() for c in self._campaigns.values()],
                progress=[p.to_dict() for p in self._progress.values()],
                hints={
                    pid: [h.to_dict() for h in hlist]
                    for pid, hlist in self._hints.items()
                },
                events=[e.to_dict() for e in self._events[-200:]],
                stats=self.get_stats().to_dict(),
            )

    # ------------------------------------------------------------------
    # Internal Helpers
    # ------------------------------------------------------------------

    def _record_event(
        self,
        kind: GuidanceEventKind,
        player_id: str = "",
        campaign_id: str = "",
        lesson_id: str = "",
        step_id: str = "",
        payload: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Record an audit event. Caller must hold the lock."""
        event = GuidanceEvent(
            event_id=_new_id("evt"),
            kind=kind,
            timestamp=_now(),
            player_id=player_id,
            campaign_id=campaign_id,
            lesson_id=lesson_id,
            step_id=step_id,
            payload=payload or {},
        )
        self._events.append(event)
        self._event_counter += 1
        _evict_fifo_list(self._events, _MAX_EVENTS)

    # ------------------------------------------------------------------
    # Reset
    # ------------------------------------------------------------------

    def reset(self) -> None:
        """Reset the engine to its seeded state."""
        with self._lock:
            self._campaigns.clear()
            self._progress.clear()
            self._hints.clear()
            self._events.clear()
            self._campaign_counter = 0
            self._lesson_counter = 0
            self._step_counter = 0
            self._progress_counter = 0
            self._hint_counter = 0
            self._campaigns_started = 0
            self._campaigns_completed = 0
            self._campaigns_skipped = 0
            self._campaigns_abandoned = 0
            self._lessons_completed = 0
            self._steps_completed = 0
            self._steps_skipped = 0
            self._hints_enqueued = 0
            self._hints_surfaced = 0
            self._hints_dismissed = 0
            self._branches_evaluated = 0
            self._event_counter = 0
            self._seed_data()

    # ------------------------------------------------------------------
    # Seed Data
    # ------------------------------------------------------------------

    def _seed_data(self) -> None:
        """Populate the engine with sample campaigns and lessons."""
        # Campaign 1: Basic Movement Tutorial for new players
        c1 = self.create_campaign(
            name="Movement Basics",
            description="Teaches the player how to move, jump and look around.",
            audience=AudienceTag.NEW_PLAYER,
            priority=10,
            tags=["core", "movement"],
        )
        l1 = self.add_lesson(
            campaign_id=c1.campaign_id,
            name="Walking",
            description="Learn to walk using the left stick or WASD.",
            mechanic="locomotion",
            estimated_minutes=1.5,
        )
        if l1:
            self.add_step(
                campaign_id=c1.campaign_id,
                lesson_id=l1.lesson_id,
                step_type=StepType.VOICE_OVER,
                title="Welcome",
                voice_line="Welcome! Use the left stick or WASD to move around.",
                sort_order=0,
            )
            self.add_step(
                campaign_id=c1.campaign_id,
                lesson_id=l1.lesson_id,
                step_type=StepType.HIGHLIGHT,
                title="Highlight Movement Controls",
                target_element="ui_movement_hud",
                tooltip_text="These are your movement controls.",
                sort_order=1,
            )
            self.add_step(
                campaign_id=c1.campaign_id,
                lesson_id=l1.lesson_id,
                step_type=StepType.WAIT_INPUT,
                title="Try Walking",
                expected_input="move_forward",
                description="Walk forward to continue.",
                timeout_seconds=30.0,
                sort_order=2,
            )
            self.add_step(
                campaign_id=c1.campaign_id,
                lesson_id=l1.lesson_id,
                step_type=StepType.CELEBRATION,
                title="Great Job!",
                description="Celebrate the player's first movement.",
                sort_order=3,
            )
        l2 = self.add_lesson(
            campaign_id=c1.campaign_id,
            name="Jumping",
            description="Learn to jump over obstacles.",
            mechanic="jump",
            estimated_minutes=1.0,
        )
        if l2:
            self.add_step(
                campaign_id=c1.campaign_id,
                lesson_id=l2.lesson_id,
                step_type=StepType.TOOLTIP,
                title="Jump Button",
                target_element="ui_jump_button",
                tooltip_text="Press A or Space to jump.",
                sort_order=0,
            )
            self.add_step(
                campaign_id=c1.campaign_id,
                lesson_id=l2.lesson_id,
                step_type=StepType.WAIT_INPUT,
                title="Try Jumping",
                expected_input="jump",
                timeout_seconds=20.0,
                sort_order=1,
            )
            self.add_step(
                campaign_id=c1.campaign_id,
                lesson_id=l2.lesson_id,
                step_type=StepType.CHECKPOINT,
                title="Checkpoint Reached",
                description="Progress saved.",
                sort_order=2,
            )

        # Campaign 2: Combat Tutorial with branching
        c2 = self.create_campaign(
            name="Combat Essentials",
            description="Teaches basic combat mechanics with difficulty branching.",
            audience=AudienceTag.NEW_PLAYER,
            priority=8,
            tags=["core", "combat"],
        )
        l3 = self.add_lesson(
            campaign_id=c2.campaign_id,
            name="First Encounter",
            description="Engage your first enemy.",
            mechanic="melee_combat",
            estimated_minutes=3.0,
        )
        if l3:
            self.add_step(
                campaign_id=c2.campaign_id,
                lesson_id=l3.lesson_id,
                step_type=StepType.HIGHLIGHT,
                title="Enemy Ahead",
                target_element="entity_enemy_01",
                tooltip_text="An enemy! Approach to engage.",
                sort_order=0,
            )
            self.add_step(
                campaign_id=c2.campaign_id,
                lesson_id=l3.lesson_id,
                step_type=StepType.WAIT_CONDITION,
                title="Engage Enemy",
                condition_expression="enemy_engaged==true",
                timeout_seconds=60.0,
                sort_order=1,
            )
            self.add_step(
                campaign_id=c2.campaign_id,
                lesson_id=l3.lesson_id,
                step_type=StepType.BRANCH,
                title="Assess Difficulty",
                description="Branch based on player performance.",
                branch_rules=[
                    {
                        "condition": "fail_count>=3",
                        "target_lesson_id": "less_easy_mode",
                        "priority": 10,
                        "description": "Struggling players get easy mode.",
                    },
                    {
                        "condition": "fail_count==0",
                        "target_lesson_id": "less_advanced_combo",
                        "priority": 5,
                        "description": "Skilled players unlock advanced combo.",
                    },
                ],
                sort_order=2,
            )


# ---------------------------------------------------------------------------
# Module-level Factory
# ---------------------------------------------------------------------------


def get_tutorial_guidance() -> TutorialGuidanceEngine:
    """Return the singleton TutorialGuidanceEngine instance."""
    return TutorialGuidanceEngine.get_instance()
