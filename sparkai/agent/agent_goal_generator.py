"""
SparkLabs Agent - Goal Generator

An autonomous goal generation and intrinsic motivation system for AI agents
in the SparkLabs game engine. Agents do not merely react to external stimuli -
they autonomously generate their own goals based on intrinsic motivation
drives (curiosity, mastery, social connection, autonomy, competence). The
engine evaluates an agent's current motivational state, identifies gaps
between desired and actual competence, and generates actionable goals with
priority, difficulty, and deadline.

The system marries two ideas:

  1. Intrinsic motivation - each agent carries a set of motivational drives
     (curiosity, mastery, social, autonomy, competence, relatedness), each
     with a ``level`` (how much the agent wants it, 0.0-1.0) and a
     ``satisfaction`` (how fulfilled it currently is, 0.0-1.0). The gap
     between level and satisfaction is the *deficit* that drives goal
     generation.

  2. Goal lifecycle - goals progress through a state machine (PROPOSED ->
     ACTIVE -> COMPLETED/ABANDONED/FAILED, with PAUSED as a side state).
     Goals can form hierarchical trees through parent/sub-goal links, carry
     priority and difficulty, and report fractional progress.

Architecture:
  GoalGeneratorEngine (Singleton)
    |-- MotivationDrive (intrinsic motivation drives)
    |-- GoalStatus (goal lifecycle state machine)
    |-- GoalCategory (domain classification of goals)
    |-- GoalPriority (priority tier for goal ordering)
    |-- GoalDifficulty (scaling tier for goal complexity)
    |-- GoalEventKind (observable system events)
    |-- MotivationState (per agent+drive motivational state)
    |-- Goal (individual goal with progress and lifecycle)
    |-- GoalTemplate (reusable goal archetype)
    |-- GoalStats (aggregate engine statistics)
    |-- GoalSnapshot (point-in-time state snapshot)
    |-- GoalEvent (observable event record)
    |-- Event Handlers (pluggable observers for goal lifecycle)

Core Capabilities:
  - Track per-agent motivational drives with level and satisfaction
  - Generate goals manually or autonomously from unsatisfied drives
  - Manage the full goal lifecycle (activate, pause, complete, abandon, fail)
  - Build hierarchical goal trees via parent/sub-goal relationships
  - Re-evaluate and reprioritize active goals from drive deficits
  - Emit observable events for the goal and motivation lifecycle
"""

from __future__ import annotations

import datetime
import threading
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Capacity constants - bounded in-memory stores with FIFO eviction
# ---------------------------------------------------------------------------

_MAX_GOALS: int = 5000
_MAX_TEMPLATES: int = 500
_MAX_MOTIVATIONS: int = 500
_MAX_EVENTS: int = 2000


# ---------------------------------------------------------------------------
# Domain Enums
# ---------------------------------------------------------------------------

class MotivationDrive(Enum):
    """Intrinsic motivation drives an agent may pursue.

    Each drive represents a distinct psychological need. The engine tracks a
    per-agent ``level`` (desired intensity) and ``satisfaction`` (current
    fulfillment) for each drive; the gap between them drives autonomous goal
    generation.
    """
    CURIOSITY = "curiosity"
    MASTERY = "mastery"
    SOCIAL = "social"
    AUTONOMY = "autonomy"
    COMPETENCE = "competence"
    RELATEDNESS = "relatedness"


class GoalStatus(Enum):
    """Lifecycle states for goal progression tracking.

    Goals are created in the PROPOSED state, activated into ACTIVE, and
    transition to a terminal state (COMPLETED, ABANDONED, FAILED). PAUSED
    is a temporary holding state for goals that are active but not currently
    being pursued.
    """
    PROPOSED = "proposed"
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    ABANDONED = "abandoned"
    FAILED = "failed"


class GoalCategory(Enum):
    """Domain classification of a goal.

    Categories pair with motivation drives to guide autonomous goal
    generation: a curiosity deficit tends to yield exploration goals, a
    mastery deficit tends to yield mastery goals, and so on.
    """
    EXPLORATION = "exploration"
    COMBAT = "combat"
    SOCIAL = "social"
    CREATIVE = "creative"
    SURVIVAL = "survival"
    ACHIEVEMENT = "achievement"
    MASTERY = "mastery"
    CUSTOM = "custom"


class GoalPriority(Enum):
    """Priority tier for goal ordering.

    Priorities are ordered from CRITICAL (most urgent) down to BACKGROUND
    (pursued only when nothing else demands attention).
    """
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    BACKGROUND = "background"


class GoalDifficulty(Enum):
    """Scaling tier that controls goal complexity and expected effort.

    Higher difficulty implies a larger expected investment of time and
    resources, and typically a greater satisfaction payoff on completion.
    """
    TRIVIAL = "trivial"
    EASY = "easy"
    MODERATE = "moderate"
    HARD = "hard"
    EXTREME = "extreme"


class GoalEventKind(Enum):
    """Kinds of events emitted by the goal generator.

    Handlers may be registered per kind to observe the goal and motivation
    lifecycle without coupling to internal data structures.
    """
    GOAL_GENERATED = "goal_generated"
    GOAL_ACTIVATED = "goal_activated"
    GOAL_COMPLETED = "goal_completed"
    GOAL_ABANDONED = "goal_abandoned"
    GOAL_FAILED = "goal_failed"
    MOTIVATION_UPDATED = "motivation_updated"
    DRIVE_SATISFIED = "drive_satisfied"


# ---------------------------------------------------------------------------
# Ranking tables for priority and difficulty ordering/scoring
# ---------------------------------------------------------------------------

_PRIORITY_RANKS: Dict[GoalPriority, int] = {
    GoalPriority.CRITICAL: 0,
    GoalPriority.HIGH: 1,
    GoalPriority.MEDIUM: 2,
    GoalPriority.LOW: 3,
    GoalPriority.BACKGROUND: 4,
}

_DIFFICULTY_SCORES: Dict[GoalDifficulty, float] = {
    GoalDifficulty.TRIVIAL: 0.0,
    GoalDifficulty.EASY: 0.25,
    GoalDifficulty.MODERATE: 0.5,
    GoalDifficulty.HARD: 0.75,
    GoalDifficulty.EXTREME: 1.0,
}

# Default mapping from a motivation drive to a goal category, used when
# auto-generating goals and no matching template is available.
_DRIVE_CATEGORY_DEFAULTS: Dict[MotivationDrive, GoalCategory] = {
    MotivationDrive.CURIOSITY: GoalCategory.EXPLORATION,
    MotivationDrive.MASTERY: GoalCategory.MASTERY,
    MotivationDrive.SOCIAL: GoalCategory.SOCIAL,
    MotivationDrive.AUTONOMY: GoalCategory.ACHIEVEMENT,
    MotivationDrive.COMPETENCE: GoalCategory.ACHIEVEMENT,
    MotivationDrive.RELATEDNESS: GoalCategory.SOCIAL,
}

# Threshold above which a drive deficit is considered worth auto-generating
# a goal, and threshold above which a drive is considered satisfied.
_DEFICIT_THRESHOLD: float = 0.1
_SATISFACTION_THRESHOLD: float = 0.9


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------

@dataclass
class MotivationState:
    """Per-agent motivational state for a single drive.

    Tracks the agent's desired intensity (``level``) and current fulfillment
    (``satisfaction``) for a motivation drive. Both values are clamped to the
    range [0.0, 1.0]. The gap ``level - satisfaction`` is the *deficit* that
    drives autonomous goal generation.

    Attributes:
        agent_id: The agent this motivation belongs to.
        drive: The motivation drive this state describes.
        level: Desired intensity of the drive (0.0-1.0).
        satisfaction: Current fulfillment of the drive (0.0-1.0).
        last_updated: ISO-8601 UTC timestamp of last update.
        metadata: Optional auxiliary metadata bag.
    """
    agent_id: str = ""
    drive: MotivationDrive = MotivationDrive.CURIOSITY
    level: float = 0.0
    satisfaction: float = 0.0
    last_updated: str = field(
        default_factory=lambda: datetime.datetime.utcnow().isoformat() + "Z"
    )
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def deficit(self) -> float:
        """The unmet portion of this drive: max(0, level - satisfaction)."""
        return max(0.0, self.level - self.satisfaction)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "agent_id": self.agent_id,
            "drive": self.drive.value,
            "level": round(self.level, 6),
            "satisfaction": round(self.satisfaction, 6),
            "deficit": round(self.deficit, 6),
            "last_updated": self.last_updated,
            "metadata": dict(self.metadata),
        }


@dataclass
class Goal:
    """A single goal with lifecycle, progress, and hierarchy tracking.

    Goals are created in the PROPOSED status and progress through the
    lifecycle as agents act on them. A goal may belong to a parent goal and
    own a list of sub-goal ids, forming a goal tree. Progress is a fractional
    value in [0.0, 1.0].

    Attributes:
        id: Unique goal identifier (uuid4 hex).
        agent_id: The agent that owns this goal.
        title: Human-readable goal title.
        description: Narrative description of the goal.
        category: Domain classification of the goal.
        priority: Priority tier for ordering among the agent's goals.
        difficulty: Scaling tier for complexity and expected effort.
        drive: The motivation drive this goal is intended to satisfy.
        status: Current lifecycle state of the goal.
        progress: Fractional completion (0.0-1.0).
        deadline: ISO-8601 UTC deadline timestamp, or empty if none.
        parent_goal_id: Id of the parent goal, or None if a root goal.
        sub_goal_ids: Ordered list of child goal ids.
        created_at: ISO-8601 UTC creation timestamp.
        updated_at: ISO-8601 UTC timestamp of last modification.
        metadata: Optional auxiliary metadata bag.
        outcome_notes: Notes recorded on terminal state transition.
    """
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    agent_id: str = ""
    title: str = ""
    description: str = ""
    category: GoalCategory = GoalCategory.CUSTOM
    priority: GoalPriority = GoalPriority.MEDIUM
    difficulty: GoalDifficulty = GoalDifficulty.MODERATE
    drive: MotivationDrive = MotivationDrive.CURIOSITY
    status: GoalStatus = GoalStatus.PROPOSED
    progress: float = 0.0
    deadline: str = ""
    parent_goal_id: Optional[str] = None
    sub_goal_ids: List[str] = field(default_factory=list)
    created_at: str = field(
        default_factory=lambda: datetime.datetime.utcnow().isoformat() + "Z"
    )
    updated_at: str = field(
        default_factory=lambda: datetime.datetime.utcnow().isoformat() + "Z"
    )
    metadata: Dict[str, Any] = field(default_factory=dict)
    outcome_notes: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "agent_id": self.agent_id,
            "title": self.title,
            "description": self.description,
            "category": self.category.value,
            "priority": self.priority.value,
            "difficulty": self.difficulty.value,
            "drive": self.drive.value,
            "status": self.status.value,
            "progress": round(self.progress, 6),
            "deadline": self.deadline,
            "parent_goal_id": self.parent_goal_id,
            "sub_goal_ids": list(self.sub_goal_ids),
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "metadata": dict(self.metadata),
            "outcome_notes": self.outcome_notes,
        }


@dataclass
class GoalTemplate:
    """A reusable goal archetype that can be instantiated into goals.

    Templates bind a name, category, drive, and difficulty together with a
    conditions dictionary that describes when the template applies. They are
    used by the autonomous generator to produce concrete goals for an agent's
    unsatisfied drives.

    Attributes:
        id: Unique template identifier (uuid4 hex).
        name: Display name of the template.
        category: Default goal category for goals produced from this template.
        drive: The motivation drive this template is meant to satisfy.
        difficulty: Default difficulty for goals produced from this template.
        conditions: Applicability conditions (e.g. min_level, region, skill).
        metadata: Optional auxiliary metadata bag.
    """
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = ""
    category: GoalCategory = GoalCategory.CUSTOM
    drive: MotivationDrive = MotivationDrive.CURIOSITY
    difficulty: GoalDifficulty = GoalDifficulty.MODERATE
    conditions: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "category": self.category.value,
            "drive": self.drive.value,
            "difficulty": self.difficulty.value,
            "conditions": dict(self.conditions),
            "metadata": dict(self.metadata),
        }


@dataclass
class GoalStats:
    """Summary statistics over the entire goal generator state.

    Attributes:
        total_goals: Count of all goals tracked by the engine.
        active_goals: Count of goals currently in the ACTIVE status.
        completed_goals: Count of goals that reached the COMPLETED status.
        abandoned_goals: Count of goals that reached the ABANDONED status.
        avg_completion_rate: Completed goals as a fraction of all goals.
        avg_difficulty: Mean difficulty score (0.0-1.0) across all goals.
        last_updated: ISO-8601 UTC timestamp of last computation.
    """
    total_goals: int = 0
    active_goals: int = 0
    completed_goals: int = 0
    abandoned_goals: int = 0
    avg_completion_rate: float = 0.0
    avg_difficulty: float = 0.0
    last_updated: str = field(
        default_factory=lambda: datetime.datetime.utcnow().isoformat() + "Z"
    )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_goals": self.total_goals,
            "active_goals": self.active_goals,
            "completed_goals": self.completed_goals,
            "abandoned_goals": self.abandoned_goals,
            "avg_completion_rate": round(self.avg_completion_rate, 6),
            "avg_difficulty": round(self.avg_difficulty, 6),
            "last_updated": self.last_updated,
        }


@dataclass
class GoalSnapshot:
    """Point-in-time snapshot of the goal generator state.

    Attributes:
        agent_count: Number of distinct agents with goals or motivations.
        total_goals: Total goals tracked at snapshot time.
        active_goals: Active goals at snapshot time.
        stats: Computed GoalStats at snapshot time (serialized to dict).
        timestamp: ISO-8601 UTC snapshot timestamp.
    """
    agent_count: int = 0
    total_goals: int = 0
    active_goals: int = 0
    stats: Dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(
        default_factory=lambda: datetime.datetime.utcnow().isoformat() + "Z"
    )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "agent_count": self.agent_count,
            "total_goals": self.total_goals,
            "active_goals": self.active_goals,
            "stats": dict(self.stats),
            "timestamp": self.timestamp,
        }


@dataclass
class GoalEvent:
    """An observable event emitted by the goal generator.

    Attributes:
        id: Unique event identifier (uuid4 hex).
        kind: The GoalEventKind discriminator (string value).
        agent_id: Agent the event pertains to (may be empty for global).
        payload: Event-specific data payload.
        timestamp: ISO-8601 UTC event timestamp.
    """
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    kind: str = GoalEventKind.GOAL_GENERATED.value
    agent_id: str = ""
    payload: Dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(
        default_factory=lambda: datetime.datetime.utcnow().isoformat() + "Z"
    )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "kind": self.kind,
            "agent_id": self.agent_id,
            "payload": dict(self.payload),
            "timestamp": self.timestamp,
        }


# ---------------------------------------------------------------------------
# Goal Generator Engine (Singleton)
# ---------------------------------------------------------------------------

class GoalGeneratorEngine:
    """Autonomous goal generation and intrinsic motivation engine.

    Tracks per-agent motivational drives, generates actionable goals from
    unsatisfied drives, manages the full goal lifecycle, and maintains
    hierarchical goal trees. The engine emits observable events for the goal
    and motivation lifecycle and supports pluggable event handlers.

    The engine is a thread-safe singleton accessed via ``get_instance()``
    or the module-level ``get_goal_generator()`` helper. It uses
    double-checked locking so the fast path after initialization does not
    acquire the lock.

    Usage:
        engine = GoalGeneratorEngine.get_instance()
        engine.set_motivation("agent_alpha", MotivationDrive.CURIOSITY, 0.8, 0.3)
        goals = engine.auto_generate("agent_alpha")
    """

    _instance: Optional["GoalGeneratorEngine"] = None
    _lock: threading.RLock = threading.RLock()

    def __new__(cls) -> "GoalGeneratorEngine":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    instance = super().__new__(cls)
                    instance._initialized = False
                    cls._instance = instance
        return cls._instance

    @classmethod
    def get_instance(cls) -> "GoalGeneratorEngine":
        """Return the singleton GoalGeneratorEngine instance.

        Uses double-checked locking so that the vast majority of calls
        after initialization take the fast path without acquiring the lock.
        """
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def __init__(self) -> None:
        # Guard against re-initialization of the singleton.
        if self._initialized:
            return
        self._initialized: bool = True

        # Motivation storage keyed by (agent_id, drive.value), plus agent index.
        self._motivations: Dict[Tuple[str, str], MotivationState] = {}
        self._agent_motivations: Dict[str, List[str]] = {}

        # Goal templates keyed by id, with category and drive indexes.
        self._templates: Dict[str, GoalTemplate] = {}

        # Goal storage keyed by id, plus agent index.
        self._goals: Dict[str, Goal] = {}
        self._agent_goals: Dict[str, List[str]] = {}

        # Event log and pluggable event handlers keyed by event kind.
        self._events: List[GoalEvent] = []
        self._event_handlers: Dict[
            str, List[Tuple[str, Callable[[GoalEvent], None]]]
        ] = {}

        # Seed the engine with baseline motivation and goal data.
        self._seed_baseline_data()

    # ------------------------------------------------------------------
    # Seed Data
    # ------------------------------------------------------------------

    def _seed_baseline_data(self) -> None:
        """Populate the engine with baseline motivations, templates, and goals.

        This gives the generator a non-empty starting state so that
        autonomous goal generation and priority evaluation have prior
        experience to draw upon immediately after construction.
        """
        now = datetime.datetime.utcnow().isoformat() + "Z"

        # --- Motivations for agent_alpha -------------------------------
        alpha_motivations = [
            MotivationState(
                agent_id="agent_alpha",
                drive=MotivationDrive.CURIOSITY,
                level=0.8,
                satisfaction=0.3,
                last_updated=now,
            ),
            MotivationState(
                agent_id="agent_alpha",
                drive=MotivationDrive.MASTERY,
                level=0.6,
                satisfaction=0.5,
                last_updated=now,
            ),
            MotivationState(
                agent_id="agent_alpha",
                drive=MotivationDrive.SOCIAL,
                level=0.4,
                satisfaction=0.7,
                last_updated=now,
            ),
            MotivationState(
                agent_id="agent_alpha",
                drive=MotivationDrive.AUTONOMY,
                level=0.7,
                satisfaction=0.4,
                last_updated=now,
            ),
            MotivationState(
                agent_id="agent_alpha",
                drive=MotivationDrive.COMPETENCE,
                level=0.5,
                satisfaction=0.6,
                last_updated=now,
            ),
        ]

        # --- Motivations for agent_beta --------------------------------
        beta_motivations = [
            MotivationState(
                agent_id="agent_beta",
                drive=MotivationDrive.CURIOSITY,
                level=0.9,
                satisfaction=0.2,
                last_updated=now,
            ),
            MotivationState(
                agent_id="agent_beta",
                drive=MotivationDrive.MASTERY,
                level=0.5,
                satisfaction=0.4,
                last_updated=now,
            ),
            MotivationState(
                agent_id="agent_beta",
                drive=MotivationDrive.SOCIAL,
                level=0.6,
                satisfaction=0.5,
                last_updated=now,
            ),
        ]

        for state in alpha_motivations + beta_motivations:
            self._motivations[(state.agent_id, state.drive.value)] = state
            self._agent_motivations.setdefault(state.agent_id, []).append(
                state.drive.value
            )

        # --- Goal templates --------------------------------------------
        templates = [
            GoalTemplate(
                id=uuid.uuid4().hex,
                name="Explore Uncharted Region",
                category=GoalCategory.EXPLORATION,
                drive=MotivationDrive.CURIOSITY,
                difficulty=GoalDifficulty.MODERATE,
                conditions={"min_deficit": 0.2, "region": "any"},
                metadata={"seed": True},
            ),
            GoalTemplate(
                id=uuid.uuid4().hex,
                name="Master Combat Technique",
                category=GoalCategory.MASTERY,
                drive=MotivationDrive.MASTERY,
                difficulty=GoalDifficulty.HARD,
                conditions={"min_deficit": 0.2, "skill": "combat"},
                metadata={"seed": True},
            ),
            GoalTemplate(
                id=uuid.uuid4().hex,
                name="Build Alliance",
                category=GoalCategory.SOCIAL,
                drive=MotivationDrive.SOCIAL,
                difficulty=GoalDifficulty.MODERATE,
                conditions={"min_deficit": 0.15, "faction": "any"},
                metadata={"seed": True},
            ),
        ]
        for template in templates:
            self._templates[template.id] = template

        # --- Goals for agent_alpha -------------------------------------
        alpha_goals = [
            Goal(
                id=uuid.uuid4().hex,
                agent_id="agent_alpha",
                title="Discover hidden cave system",
                description="Locate and map the hidden cave system beneath the northern ridge.",
                category=GoalCategory.EXPLORATION,
                priority=GoalPriority.HIGH,
                difficulty=GoalDifficulty.MODERATE,
                drive=MotivationDrive.CURIOSITY,
                status=GoalStatus.ACTIVE,
                progress=0.4,
                deadline="",
                parent_goal_id=None,
                created_at=now,
                updated_at=now,
                metadata={"seed": True},
            ),
            Goal(
                id=uuid.uuid4().hex,
                agent_id="agent_alpha",
                title="Improve swordsmanship",
                description="Train with the blade master to raise swordsmanship proficiency.",
                category=GoalCategory.MASTERY,
                priority=GoalPriority.MEDIUM,
                difficulty=GoalDifficulty.HARD,
                drive=MotivationDrive.MASTERY,
                status=GoalStatus.ACTIVE,
                progress=0.2,
                deadline="",
                parent_goal_id=None,
                created_at=now,
                updated_at=now,
                metadata={"seed": True},
            ),
            Goal(
                id=uuid.uuid4().hex,
                agent_id="agent_alpha",
                title="Befriend merchant guild",
                description="Establish a friendly relationship with the merchant guild.",
                category=GoalCategory.SOCIAL,
                priority=GoalPriority.LOW,
                difficulty=GoalDifficulty.EASY,
                drive=MotivationDrive.SOCIAL,
                status=GoalStatus.COMPLETED,
                progress=1.0,
                deadline="",
                parent_goal_id=None,
                created_at=now,
                updated_at=now,
                metadata={"seed": True},
                outcome_notes="Merchant guild relationship established; trade discount unlocked.",
            ),
            Goal(
                id=uuid.uuid4().hex,
                agent_id="agent_alpha",
                title="Map northern territory",
                description="Survey and chart the full northern territory for the cartographer.",
                category=GoalCategory.EXPLORATION,
                priority=GoalPriority.HIGH,
                difficulty=GoalDifficulty.MODERATE,
                drive=MotivationDrive.CURIOSITY,
                status=GoalStatus.PROPOSED,
                progress=0.0,
                deadline="",
                parent_goal_id=None,
                created_at=now,
                updated_at=now,
                metadata={"seed": True},
            ),
        ]

        # --- Goal for agent_beta ---------------------------------------
        beta_goals = [
            Goal(
                id=uuid.uuid4().hex,
                agent_id="agent_beta",
                title="Find rare herbs",
                description="Gather rare medicinal herbs from the shadowfen marsh.",
                category=GoalCategory.SURVIVAL,
                priority=GoalPriority.MEDIUM,
                difficulty=GoalDifficulty.EASY,
                drive=MotivationDrive.COMPETENCE,
                status=GoalStatus.ACTIVE,
                progress=0.6,
                deadline="",
                parent_goal_id=None,
                created_at=now,
                updated_at=now,
                metadata={"seed": True},
            ),
        ]

        for goal in alpha_goals + beta_goals:
            self._goals[goal.id] = goal
            self._agent_goals.setdefault(goal.agent_id, []).append(goal.id)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _now() -> str:
        """Return the current UTC time as an ISO-8601 string with 'Z' suffix."""
        return datetime.datetime.utcnow().isoformat() + "Z"

    @staticmethod
    def _clamp(value: float, lo: float = 0.0, hi: float = 1.0) -> float:
        """Clamp a numeric value to the inclusive [lo, hi] range."""
        if value < lo:
            return lo
        if value > hi:
            return hi
        return value

    @staticmethod
    def _priority_rank(priority: GoalPriority) -> int:
        """Return the ordinal rank of a priority (lower is more urgent)."""
        return _PRIORITY_RANKS.get(priority, _PRIORITY_RANKS[GoalPriority.MEDIUM])

    @staticmethod
    def _difficulty_score(difficulty: GoalDifficulty) -> float:
        """Return the numeric score (0.0-1.0) for a difficulty tier."""
        return _DIFFICULTY_SCORES.get(difficulty, _DIFFICULTY_SCORES[GoalDifficulty.MODERATE])

    def _emit_event(
        self,
        kind: GoalEventKind,
        agent_id: str,
        payload: Dict[str, Any],
    ) -> GoalEvent:
        """Record an event and dispatch it to any registered handlers.

        Handler exceptions are swallowed so that an observer failure can
        never disrupt the core goal-generation flow.
        """
        event = GoalEvent(
            id=uuid.uuid4().hex,
            kind=kind.value,
            agent_id=agent_id,
            payload=payload,
            timestamp=self._now(),
        )
        self._events.append(event)
        if len(self._events) > _MAX_EVENTS:
            # Drop the oldest events to stay within the bounded log.
            del self._events[: len(self._events) - _MAX_EVENTS]

        handlers = self._event_handlers.get(kind.value, [])
        for _, handler in handlers:
            try:
                handler(event)
            except Exception:
                # Observer failures must not affect the engine.
                pass
        return event

    def _evict_oldest_goal(self) -> None:
        """Remove the oldest goal to respect the goal capacity."""
        if not self._goals:
            return
        oldest_id = next(iter(self._goals))
        self._remove_goal_internal(oldest_id)

    def _evict_oldest_motivation(self) -> None:
        """Remove the oldest motivation state to respect the capacity."""
        if not self._motivations:
            return
        oldest_key = next(iter(self._motivations))
        oldest = self._motivations.pop(oldest_key, None)
        if oldest is None:
            return
        agent_list = self._agent_motivations.get(oldest.agent_id)
        if agent_list:
            try:
                agent_list.remove(oldest.drive.value)
            except ValueError:
                pass

    def _evict_oldest_template(self) -> None:
        """Remove the oldest template to respect the template capacity."""
        if not self._templates:
            return
        oldest_id = next(iter(self._templates))
        self._templates.pop(oldest_id, None)

    def _remove_goal_internal(self, goal_id: str) -> bool:
        """Internal: remove a goal from all indexes without acquiring the lock."""
        goal = self._goals.pop(goal_id, None)
        if goal is None:
            return False
        agent_list = self._agent_goals.get(goal.agent_id)
        if agent_list:
            try:
                agent_list.remove(goal_id)
            except ValueError:
                pass
        # Detach from parent's sub-goal list if present.
        if goal.parent_goal_id:
            parent = self._goals.get(goal.parent_goal_id)
            if parent and goal_id in parent.sub_goal_ids:
                parent.sub_goal_ids.remove(goal_id)
        # Orphaned children keep their parent_goal_id reference but are no
        # longer reachable through the tree; this is acceptable for capacity
        # eviction which is an exceptional path.
        return True

    # ------------------------------------------------------------------
    # Motivation Management
    # ------------------------------------------------------------------

    def set_motivation(
        self,
        agent_id: str,
        drive: MotivationDrive,
        level: float,
        satisfaction: float,
    ) -> MotivationState:
        """Set the motivational state for an agent and drive.

        Creates or replaces the (agent_id, drive) motivation entry. Both
        ``level`` and ``satisfaction`` are clamped to [0.0, 1.0]. A
        MOTIVATION_UPDATED event is emitted, plus a DRIVE_SATISFIED event
        if the satisfaction reaches the satisfaction threshold.

        Args:
            agent_id: Identifier of the agent.
            drive: The motivation drive to set.
            level: Desired intensity of the drive (0.0-1.0).
            satisfaction: Current fulfillment of the drive (0.0-1.0).

        Returns:
            The resulting MotivationState.
        """
        with self._lock:
            state = MotivationState(
                agent_id=agent_id,
                drive=drive,
                level=self._clamp(level),
                satisfaction=self._clamp(satisfaction),
                last_updated=self._now(),
            )
            key = (agent_id, drive.value)
            self._motivations[key] = state

            agent_list = self._agent_motivations.setdefault(agent_id, [])
            if drive.value not in agent_list:
                agent_list.append(drive.value)

            if len(self._motivations) > _MAX_MOTIVATIONS:
                self._evict_oldest_motivation()

            self._emit_event(
                GoalEventKind.MOTIVATION_UPDATED,
                agent_id,
                {
                    "drive": drive.value,
                    "level": state.level,
                    "satisfaction": state.satisfaction,
                    "deficit": state.deficit,
                },
            )
            if state.satisfaction >= _SATISFACTION_THRESHOLD:
                self._emit_event(
                    GoalEventKind.DRIVE_SATISFIED,
                    agent_id,
                    {
                        "drive": drive.value,
                        "satisfaction": state.satisfaction,
                    },
                )
            return state

    def get_motivation(
        self,
        agent_id: str,
        drive: MotivationDrive,
    ) -> Optional[MotivationState]:
        """Retrieve the motivational state for an agent and drive."""
        with self._lock:
            return self._motivations.get((agent_id, drive.value))

    def list_motivations(self, agent_id: str) -> List[MotivationState]:
        """List all motivational states recorded for an agent."""
        with self._lock:
            drives = self._agent_motivations.get(agent_id, [])
            results: List[MotivationState] = []
            for drive_value in drives:
                state = self._motivations.get((agent_id, drive_value))
                if state is not None:
                    results.append(state)
            return results

    def update_motivation(
        self,
        agent_id: str,
        drive: MotivationDrive,
        delta_level: float,
        delta_satisfaction: float,
    ) -> Optional[MotivationState]:
        """Apply relative deltas to an agent's motivational state.

        Adds ``delta_level`` and ``delta_satisfaction`` to the existing
        values, clamping the results to [0.0, 1.0]. If no prior state exists
        for the (agent_id, drive) pair, a fresh state is created from the
        deltas (treated as absolute starting values). Emits MOTIVATION_UPDATED
        and, when the satisfaction threshold is reached, DRIVE_SATISFIED.

        Args:
            agent_id: Identifier of the agent.
            drive: The motivation drive to update.
            delta_level: Change in desired intensity.
            delta_satisfaction: Change in current fulfillment.

        Returns:
            The updated MotivationState, or None if the drive could not be
            resolved (should not occur in normal usage).
        """
        with self._lock:
            key = (agent_id, drive.value)
            state = self._motivations.get(key)
            if state is None:
                state = MotivationState(
                    agent_id=agent_id,
                    drive=drive,
                    level=self._clamp(delta_level),
                    satisfaction=self._clamp(delta_satisfaction),
                    last_updated=self._now(),
                )
                self._motivations[key] = state
                agent_list = self._agent_motivations.setdefault(agent_id, [])
                if drive.value not in agent_list:
                    agent_list.append(drive.value)
                if len(self._motivations) > _MAX_MOTIVATIONS:
                    self._evict_oldest_motivation()
            else:
                state.level = self._clamp(state.level + delta_level)
                state.satisfaction = self._clamp(state.satisfaction + delta_satisfaction)
                state.last_updated = self._now()

            self._emit_event(
                GoalEventKind.MOTIVATION_UPDATED,
                agent_id,
                {
                    "drive": drive.value,
                    "level": state.level,
                    "satisfaction": state.satisfaction,
                    "deficit": state.deficit,
                    "delta_level": delta_level,
                    "delta_satisfaction": delta_satisfaction,
                },
            )
            if state.satisfaction >= _SATISFACTION_THRESHOLD:
                self._emit_event(
                    GoalEventKind.DRIVE_SATISFIED,
                    agent_id,
                    {
                        "drive": drive.value,
                        "satisfaction": state.satisfaction,
                    },
                )
            return state

    # ------------------------------------------------------------------
    # Goal Templates
    # ------------------------------------------------------------------

    def register_template(
        self,
        name: str,
        category: GoalCategory,
        drive: MotivationDrive,
        difficulty: GoalDifficulty,
        conditions: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> GoalTemplate:
        """Register a new reusable goal template.

        Args:
            name: Display name of the template.
            category: Default goal category for goals produced from this template.
            drive: The motivation drive this template is meant to satisfy.
            difficulty: Default difficulty for goals produced from this template.
            conditions: Optional applicability conditions.
            metadata: Optional auxiliary metadata.

        Returns:
            The newly created GoalTemplate.
        """
        with self._lock:
            template = GoalTemplate(
                id=uuid.uuid4().hex,
                name=name,
                category=category,
                drive=drive,
                difficulty=difficulty,
                conditions=dict(conditions) if conditions else {},
                metadata=dict(metadata) if metadata else {},
            )
            self._templates[template.id] = template
            if len(self._templates) > _MAX_TEMPLATES:
                self._evict_oldest_template()
            return template

    def get_template(self, template_id: str) -> Optional[GoalTemplate]:
        """Retrieve a goal template by its id."""
        with self._lock:
            return self._templates.get(template_id)

    def list_templates(
        self,
        category: Optional[GoalCategory] = None,
        drive: Optional[MotivationDrive] = None,
    ) -> List[GoalTemplate]:
        """List goal templates, optionally filtered by category and/or drive.

        Args:
            category: Filter by goal category. All categories if None.
            drive: Filter by motivation drive. All drives if None.

        Returns:
            A list of GoalTemplate instances matching the filters.
        """
        with self._lock:
            results = list(self._templates.values())
            if category is not None:
                results = [t for t in results if t.category == category]
            if drive is not None:
                results = [t for t in results if t.drive == drive]
            return results

    # ------------------------------------------------------------------
    # Goal Lifecycle
    # ------------------------------------------------------------------

    def generate_goal(
        self,
        agent_id: str,
        title: str,
        description: str = "",
        category: GoalCategory = GoalCategory.CUSTOM,
        drive: MotivationDrive = MotivationDrive.CURIOSITY,
        priority: GoalPriority = GoalPriority.MEDIUM,
        difficulty: GoalDifficulty = GoalDifficulty.MODERATE,
        deadline: str = "",
        parent_goal_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Goal:
        """Generate a new goal in the PROPOSED status.

        The goal is created with zero progress and current timestamps. If a
        ``parent_goal_id`` is supplied and resolves to an existing goal, the
        new goal is registered as a sub-goal of that parent. A GOAL_GENERATED
        event is emitted.

        Args:
            agent_id: Identifier of the owning agent.
            title: Human-readable goal title.
            description: Narrative description of the goal.
            category: Domain classification of the goal.
            drive: The motivation drive this goal is intended to satisfy.
            priority: Priority tier for ordering among the agent's goals.
            difficulty: Scaling tier for complexity and expected effort.
            deadline: ISO-8601 UTC deadline timestamp, or empty if none.
            parent_goal_id: Optional id of the parent goal.
            metadata: Optional auxiliary metadata.

        Returns:
            The newly created Goal.
        """
        with self._lock:
            now = self._now()
            goal = Goal(
                id=uuid.uuid4().hex,
                agent_id=agent_id,
                title=title,
                description=description,
                category=category,
                priority=priority,
                difficulty=difficulty,
                drive=drive,
                status=GoalStatus.PROPOSED,
                progress=0.0,
                deadline=deadline,
                parent_goal_id=parent_goal_id,
                created_at=now,
                updated_at=now,
                metadata=dict(metadata) if metadata else {},
            )
            self._goals[goal.id] = goal
            self._agent_goals.setdefault(agent_id, []).append(goal.id)

            if parent_goal_id is not None:
                parent = self._goals.get(parent_goal_id)
                if parent is not None and goal.id not in parent.sub_goal_ids:
                    parent.sub_goal_ids.append(goal.id)
                    parent.updated_at = now

            if len(self._goals) > _MAX_GOALS:
                self._evict_oldest_goal()

            self._emit_event(
                GoalEventKind.GOAL_GENERATED,
                agent_id,
                {
                    "goal_id": goal.id,
                    "title": goal.title,
                    "category": goal.category.value,
                    "drive": goal.drive.value,
                    "priority": goal.priority.value,
                    "difficulty": goal.difficulty.value,
                    "parent_goal_id": goal.parent_goal_id,
                },
            )
            return goal

    def get_goal(self, goal_id: str) -> Optional[Goal]:
        """Retrieve a goal by its id."""
        with self._lock:
            return self._goals.get(goal_id)

    def list_goals(
        self,
        agent_id: Optional[str] = None,
        status: Optional[GoalStatus] = None,
        category: Optional[GoalCategory] = None,
    ) -> List[Goal]:
        """List goals, optionally filtered by agent, status, and/or category.

        Args:
            agent_id: Filter by owning agent. All agents if None.
            status: Filter by lifecycle status. All statuses if None.
            category: Filter by goal category. All categories if None.

        Returns:
            A list of Goal instances matching the filters.
        """
        with self._lock:
            if agent_id is not None:
                ids = self._agent_goals.get(agent_id, [])
                goals = [self._goals[i] for i in ids if i in self._goals]
            else:
                goals = list(self._goals.values())

            if status is not None:
                goals = [g for g in goals if g.status == status]
            if category is not None:
                goals = [g for g in goals if g.category == category]
            return goals

    def remove_goal(self, goal_id: str) -> bool:
        """Remove a goal by its id.

        Detaches the goal from its parent's sub-goal list before removal.

        Returns:
            True if a goal was removed, False if not found.
        """
        with self._lock:
            return self._remove_goal_internal(goal_id)

    def activate_goal(self, goal_id: str) -> Optional[Goal]:
        """Transition a goal into the ACTIVE status.

        Emits a GOAL_ACTIVATED event. Returns None if the goal is not found.

        Args:
            goal_id: The goal to activate.

        Returns:
            The updated Goal, or None if not found.
        """
        with self._lock:
            goal = self._goals.get(goal_id)
            if goal is None:
                return None
            goal.status = GoalStatus.ACTIVE
            goal.updated_at = self._now()
            self._emit_event(
                GoalEventKind.GOAL_ACTIVATED,
                goal.agent_id,
                {
                    "goal_id": goal.id,
                    "title": goal.title,
                    "priority": goal.priority.value,
                },
            )
            return goal

    def pause_goal(self, goal_id: str) -> Optional[Goal]:
        """Transition a goal into the PAUSED status.

        Paused goals remain active in spirit but are not currently being
        pursued. Returns None if the goal is not found.

        Args:
            goal_id: The goal to pause.

        Returns:
            The updated Goal, or None if not found.
        """
        with self._lock:
            goal = self._goals.get(goal_id)
            if goal is None:
                return None
            goal.status = GoalStatus.PAUSED
            goal.updated_at = self._now()
            return goal

    def complete_goal(
        self,
        goal_id: str,
        outcome_notes: str = "",
    ) -> Optional[Goal]:
        """Mark a goal as COMPLETED.

        Sets progress to 1.0, records outcome notes, and emits a
        GOAL_COMPLETED event. Returns None if the goal is not found.

        Args:
            goal_id: The goal to complete.
            outcome_notes: Notes describing how the goal was achieved.

        Returns:
            The updated Goal, or None if not found.
        """
        with self._lock:
            goal = self._goals.get(goal_id)
            if goal is None:
                return None
            goal.status = GoalStatus.COMPLETED
            goal.progress = 1.0
            goal.outcome_notes = outcome_notes
            goal.updated_at = self._now()
            self._emit_event(
                GoalEventKind.GOAL_COMPLETED,
                goal.agent_id,
                {
                    "goal_id": goal.id,
                    "title": goal.title,
                    "drive": goal.drive.value,
                    "difficulty": goal.difficulty.value,
                    "outcome_notes": outcome_notes,
                },
            )
            return goal

    def abandon_goal(
        self,
        goal_id: str,
        reason: str = "",
    ) -> Optional[Goal]:
        """Mark a goal as ABANDONED.

        Records the abandonment reason as outcome notes and emits a
        GOAL_ABANDONED event. Returns None if the goal is not found.

        Args:
            goal_id: The goal to abandon.
            reason: The reason the goal was abandoned.

        Returns:
            The updated Goal, or None if not found.
        """
        with self._lock:
            goal = self._goals.get(goal_id)
            if goal is None:
                return None
            goal.status = GoalStatus.ABANDONED
            goal.outcome_notes = reason
            goal.updated_at = self._now()
            self._emit_event(
                GoalEventKind.GOAL_ABANDONED,
                goal.agent_id,
                {
                    "goal_id": goal.id,
                    "title": goal.title,
                    "reason": reason,
                },
            )
            return goal

    def fail_goal(
        self,
        goal_id: str,
        reason: str = "",
    ) -> Optional[Goal]:
        """Mark a goal as FAILED.

        Records the failure reason as outcome notes and emits a GOAL_FAILED
        event. Returns None if the goal is not found.

        Args:
            goal_id: The goal to fail.
            reason: The reason the goal failed.

        Returns:
            The updated Goal, or None if not found.
        """
        with self._lock:
            goal = self._goals.get(goal_id)
            if goal is None:
                return None
            goal.status = GoalStatus.FAILED
            goal.outcome_notes = reason
            goal.updated_at = self._now()
            self._emit_event(
                GoalEventKind.GOAL_FAILED,
                goal.agent_id,
                {
                    "goal_id": goal.id,
                    "title": goal.title,
                    "reason": reason,
                },
            )
            return goal

    def update_progress(
        self,
        goal_id: str,
        progress: float,
    ) -> Optional[Goal]:
        """Update the fractional progress of a goal.

        Progress is clamped to [0.0, 1.0]. If progress reaches 1.0 the goal
        is automatically transitioned to the COMPLETED status. Returns None
        if the goal is not found.

        Args:
            goal_id: The goal to update.
            progress: New fractional progress (0.0-1.0).

        Returns:
            The updated Goal, or None if not found.
        """
        with self._lock:
            goal = self._goals.get(goal_id)
            if goal is None:
                return None
            goal.progress = self._clamp(progress)
            goal.updated_at = self._now()
            if goal.progress >= 1.0 and goal.status != GoalStatus.COMPLETED:
                goal.status = GoalStatus.COMPLETED
                goal.outcome_notes = goal.outcome_notes or "Completed via progress update."
                self._emit_event(
                    GoalEventKind.GOAL_COMPLETED,
                    goal.agent_id,
                    {
                        "goal_id": goal.id,
                        "title": goal.title,
                        "drive": goal.drive.value,
                        "auto": True,
                    },
                )
            return goal

    def add_sub_goal(
        self,
        parent_goal_id: str,
        goal_id: str,
    ) -> bool:
        """Link an existing goal as a sub-goal of a parent goal.

        Sets the child's ``parent_goal_id`` and appends its id to the parent's
        ``sub_goal_ids`` list (deduplicated).

        Args:
            parent_goal_id: The id of the parent goal.
            goal_id: The id of the goal to attach as a sub-goal.

        Returns:
            True if the link was created, False if either goal is missing.
        """
        with self._lock:
            parent = self._goals.get(parent_goal_id)
            child = self._goals.get(goal_id)
            if parent is None or child is None:
                return False
            if goal_id not in parent.sub_goal_ids:
                parent.sub_goal_ids.append(goal_id)
            child.parent_goal_id = parent_goal_id
            now = self._now()
            parent.updated_at = now
            child.updated_at = now
            return True

    def get_goal_tree(self, goal_id: str) -> Dict[str, Any]:
        """Build a recursive tree structure rooted at the given goal.

        The returned dict has the shape::

            {
                "goal": <goal.to_dict()>,
                "sub_goals": [ <recursive tree>, ... ],
            }

        Cycles are guarded against by tracking visited goal ids. Returns an
        empty dict if the goal is not found.

        Args:
            goal_id: The id of the root goal of the tree.

        Returns:
            A nested dict describing the goal tree.
        """
        with self._lock:
            visited: set = set()

            def _build(current_id: str) -> Dict[str, Any]:
                goal = self._goals.get(current_id)
                if goal is None or current_id in visited:
                    return {}
                visited.add(current_id)
                node: Dict[str, Any] = {
                    "goal": goal.to_dict(),
                    "sub_goals": [],
                }
                for sub_id in goal.sub_goal_ids:
                    child = _build(sub_id)
                    if child:
                        node["sub_goals"].append(child)
                return node

            return _build(goal_id)

    # ------------------------------------------------------------------
    # Autonomous Goal Generation & Prioritization
    # ------------------------------------------------------------------

    def _compute_deficits(self, agent_id: str) -> Dict[str, float]:
        """Internal: compute the per-drive deficits for an agent.

        Returns a dict mapping drive value to ``max(0, level - satisfaction)``
        for every motivation recorded for the agent.
        """
        deficits: Dict[str, float] = {}
        for drive_value in self._agent_motivations.get(agent_id, []):
            state = self._motivations.get((agent_id, drive_value))
            if state is None:
                continue
            deficits[drive_value] = state.deficit
        return deficits

    def get_drive_deficit(self, agent_id: str) -> Dict[str, float]:
        """Return the per-drive deficits for an agent.

        Only drives whose deficit (level - satisfaction) exceeds the deficit
        threshold are included, so callers receive the set of drives that
        actually need attention.

        Args:
            agent_id: The agent to analyze.

        Returns:
            A dict mapping drive value to its deficit (positive floats only).
        """
        with self._lock:
            return {
                drive_value: round(deficit, 6)
                for drive_value, deficit in self._compute_deficits(agent_id).items()
                if deficit >= _DEFICIT_THRESHOLD
            }

    def auto_generate(self, agent_id: str) -> List[Goal]:
        """Auto-generate goals for an agent based on unsatisfied drives.

        For each drive whose deficit meets the deficit threshold, a goal is
        generated either from a matching template (by drive) or from a
        default category. The goal priority is derived from the deficit
        magnitude, and the difficulty is taken from the matching template or
        defaults to MODERATE.

        Args:
            agent_id: The agent to generate goals for.

        Returns:
            A list of newly generated Goal instances (one per deficient
            drive).
        """
        with self._lock:
            generated: List[Goal] = []
            deficits = self._compute_deficits(agent_id)

            for drive_value, deficit in deficits.items():
                if deficit < _DEFICIT_THRESHOLD:
                    continue
                try:
                    drive_enum = MotivationDrive(drive_value)
                except ValueError:
                    continue

                # Find a template whose drive matches this deficit.
                matching_templates = [
                    t for t in self._templates.values() if t.drive == drive_enum
                ]
                if matching_templates:
                    template = matching_templates[0]
                    category = template.category
                    difficulty = template.difficulty
                    title = template.name
                    description = (
                        f"Auto-generated from template '{template.name}' to "
                        f"address the {drive_enum.value} drive deficit."
                    )
                else:
                    category = _DRIVE_CATEGORY_DEFAULTS.get(
                        drive_enum, GoalCategory.CUSTOM
                    )
                    difficulty = GoalDifficulty.MODERATE
                    title = f"Pursue {drive_enum.value.replace('_', ' ').title()}"
                    description = (
                        f"Auto-generated goal to address the {drive_enum.value} "
                        f"drive deficit."
                    )

                # Priority scales with deficit magnitude.
                if deficit >= 0.4:
                    priority = GoalPriority.HIGH
                elif deficit >= 0.2:
                    priority = GoalPriority.MEDIUM
                else:
                    priority = GoalPriority.LOW

                goal = self.generate_goal(
                    agent_id=agent_id,
                    title=title,
                    description=description,
                    category=category,
                    drive=drive_enum,
                    priority=priority,
                    difficulty=difficulty,
                    deadline="",
                    parent_goal_id=None,
                    metadata={
                        "auto_generated": True,
                        "deficit": round(deficit, 6),
                        "drive": drive_enum.value,
                    },
                )
                generated.append(goal)
            return generated

    def evaluate_priorities(self, agent_id: str) -> List[Goal]:
        """Re-evaluate and reorder an agent's active goals by priority.

        For each active goal, a recommended priority is computed from the
        drive deficit (goals addressing a more deficient drive rank higher)
        and the inverse of progress (less-progressed goals rank higher).
        Each active goal's priority is updated to the recommended value and
        its ``updated_at`` timestamp is refreshed. The returned list is
        sorted by priority rank (most urgent first) and then by deadline.

        Args:
            agent_id: The agent whose active goals should be reprioritized.

        Returns:
            The sorted list of active Goal instances for the agent.
        """
        with self._lock:
            deficits = self._compute_deficits(agent_id)
            active_goals = [
                g for g in self._goals.values()
                if g.agent_id == agent_id and g.status == GoalStatus.ACTIVE
            ]

            now = self._now()
            for goal in active_goals:
                deficit = deficits.get(goal.drive.value, 0.0)
                # Urgency blends drive deficit with how little progress has
                # been made: an unsatisfied, barely-started goal is urgent.
                urgency = deficit * (1.0 - goal.progress)
                if urgency >= 0.5:
                    goal.priority = GoalPriority.CRITICAL
                elif urgency >= 0.3:
                    goal.priority = GoalPriority.HIGH
                elif urgency >= 0.15:
                    goal.priority = GoalPriority.MEDIUM
                else:
                    goal.priority = GoalPriority.LOW
                goal.updated_at = now

            # Sort by priority rank, then by deadline (earlier first; empty
            # deadlines sort last).
            active_goals.sort(
                key=lambda g: (
                    self._priority_rank(g.priority),
                    g.deadline if g.deadline else "\uffff",
                )
            )
            return active_goals

    # ------------------------------------------------------------------
    # Event Handlers
    # ------------------------------------------------------------------

    def register_event_handler(
        self,
        kind: GoalEventKind,
        handler: Callable[[GoalEvent], None],
    ) -> str:
        """Register an observer for events of a specific kind.

        Returns a handler id that can be used with
        :meth:`unregister_event_handler` to remove the handler later.
        """
        with self._lock:
            handler_id = uuid.uuid4().hex
            self._event_handlers.setdefault(kind.value, []).append(
                (handler_id, handler)
            )
            return handler_id

    def unregister_event_handler(self, handler_id: str) -> bool:
        """Remove a previously registered event handler by id."""
        with self._lock:
            for handlers in self._event_handlers.values():
                for i, (hid, _) in enumerate(handlers):
                    if hid == handler_id:
                        del handlers[i]
                        return True
            return False

    def list_events(
        self,
        event_kind: Optional[GoalEventKind] = None,
        limit: int = 100,
    ) -> List[GoalEvent]:
        """List recent events, optionally filtered by kind.

        Returns events in reverse chronological order (most recent first).
        """
        with self._lock:
            events = list(self._events)
            if event_kind is not None:
                events = [e for e in events if e.kind == event_kind.value]
            events.sort(key=lambda e: e.timestamp, reverse=True)
            return events[:limit]

    # ------------------------------------------------------------------
    # Aggregated Stats, Status, Snapshot
    # ------------------------------------------------------------------

    def get_stats(self) -> GoalStats:
        """Compute summary statistics over the current engine state."""
        with self._lock:
            goals = list(self._goals.values())
            total_goals = len(goals)
            active_goals = sum(
                1 for g in goals if g.status == GoalStatus.ACTIVE
            )
            completed_goals = sum(
                1 for g in goals if g.status == GoalStatus.COMPLETED
            )
            abandoned_goals = sum(
                1 for g in goals if g.status == GoalStatus.ABANDONED
            )
            avg_completion_rate = (
                completed_goals / total_goals if total_goals else 0.0
            )
            avg_difficulty = (
                sum(self._difficulty_score(g.difficulty) for g in goals)
                / total_goals
                if total_goals
                else 0.0
            )
            return GoalStats(
                total_goals=total_goals,
                active_goals=active_goals,
                completed_goals=completed_goals,
                abandoned_goals=abandoned_goals,
                avg_completion_rate=avg_completion_rate,
                avg_difficulty=avg_difficulty,
                last_updated=self._now(),
            )

    def get_status(self) -> Dict[str, Any]:
        """Return a comprehensive status dictionary for diagnostics."""
        with self._lock:
            goals = list(self._goals.values())
            status_distribution: Dict[str, int] = {}
            for goal in goals:
                status_distribution[goal.status.value] = (
                    status_distribution.get(goal.status.value, 0) + 1
                )
            priority_distribution: Dict[str, int] = {}
            for goal in goals:
                priority_distribution[goal.priority.value] = (
                    priority_distribution.get(goal.priority.value, 0) + 1
                )
            category_distribution: Dict[str, int] = {}
            for goal in goals:
                category_distribution[goal.category.value] = (
                    category_distribution.get(goal.category.value, 0) + 1
                )

            agents_with_goals = {g.agent_id for g in goals}
            agents_with_motivations = set(self._agent_motivations.keys())

            return {
                "initialized": self._initialized,
                "total_goals": len(self._goals),
                "total_templates": len(self._templates),
                "total_motivations": len(self._motivations),
                "total_events": len(self._events),
                "total_event_handlers": sum(
                    len(h) for h in self._event_handlers.values()
                ),
                "agent_count": len(agents_with_goals | agents_with_motivations),
                "status_distribution": status_distribution,
                "priority_distribution": priority_distribution,
                "category_distribution": category_distribution,
                "capacity_limits": {
                    "max_goals": _MAX_GOALS,
                    "max_templates": _MAX_TEMPLATES,
                    "max_motivations": _MAX_MOTIVATIONS,
                    "max_events": _MAX_EVENTS,
                },
                "last_updated": self._now(),
            }

    def get_snapshot(self) -> GoalSnapshot:
        """Capture a point-in-time snapshot of the engine state."""
        with self._lock:
            stats = self.get_stats()
            goals = list(self._goals.values())
            agents_with_goals = {g.agent_id for g in goals}
            agents_with_motivations = set(self._agent_motivations.keys())
            return GoalSnapshot(
                agent_count=len(agents_with_goals | agents_with_motivations),
                total_goals=len(self._goals),
                active_goals=sum(
                    1 for g in goals if g.status == GoalStatus.ACTIVE
                ),
                stats=stats.to_dict(),
                timestamp=self._now(),
            )

    # ------------------------------------------------------------------
    # Reset
    # ------------------------------------------------------------------

    def reset(self) -> None:
        """Clear all tracked state, returning the engine to empty.

        Note that this does NOT re-seed baseline data; callers wishing to
        restore seed data must construct a fresh singleton (which is not
        normally necessary within a single process).
        """
        with self._lock:
            self._motivations.clear()
            self._agent_motivations.clear()
            self._templates.clear()
            self._goals.clear()
            self._agent_goals.clear()
            self._events.clear()
            self._event_handlers.clear()


# ---------------------------------------------------------------------------
# Module-Level Accessor
# ---------------------------------------------------------------------------

def get_goal_generator() -> GoalGeneratorEngine:
    """Return the singleton GoalGeneratorEngine instance."""
    return GoalGeneratorEngine.get_instance()
