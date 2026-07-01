"""
SparkLabs Agent - Meta-Learner Engine

A meta-learning system that enables AI agents to learn HOW to learn more
effectively. Rather than learning individual tasks, the MetaLearnerEngine
tracks which learning strategies work best for different categories of
tasks, adapts learning rates based on observed performance, and builds a
meta-knowledge base of learning effectiveness. This is "learning to learn."

The system observes learning episodes (one attempt at a task with a
particular strategy), aggregates them into strategy profiles (how well a
strategy works for a task category), maintains per-agent adaptive learning
rates with momentum, and stores reusable meta-knowledge that can transfer
across tasks. It also detects convergence plateaus and estimates transfer
potential between task categories.

Architecture:
  MetaLearnerEngine (Singleton)
    |-- LearningEpisode (single learning attempt record)
    |-- StrategyProfile (per strategy+category effectiveness aggregate)
    |-- MetaKnowledge (reusable cross-task learning insights)
    |-- AdaptiveRate (per agent+category learning rate with momentum)
    |-- MetaLearningEvent (observable system events)
    |-- Event Handlers (pluggable observers for learning lifecycle)

Core Capabilities:
  - Track and complete learning episodes with performance deltas
  - Aggregate episodes into strategy effectiveness profiles
  - Adapt learning rates using momentum and variance of past gains
  - Select the best strategy for a task category based on history
  - Store and retrieve reusable meta-knowledge entries
  - Detect convergence vs plateau vs regression over a window
  - Estimate transfer potential between task categories
  - Emit observable events for episode and strategy lifecycle
"""

from __future__ import annotations

import datetime
import math
import threading
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Capacity constants - bounded in-memory stores with FIFO eviction
# ---------------------------------------------------------------------------

_MAX_EPISODES: int = 5000
_MAX_PROFILES: int = 1000
_MAX_META_KNOWLEDGE: int = 2000
_MAX_RATES: int = 500
_MAX_EVENTS: int = 2000


# ---------------------------------------------------------------------------
# Domain Enums
# ---------------------------------------------------------------------------

class LearningStrategy(Enum):
    """Strategies an agent may use to acquire or refine a skill.

    The meta-learner compares these strategies against task categories to
    determine which approach yields the fastest, most reliable improvement.
    """
    GRADIENT_DESCENT = "gradient_descent"
    REINFORCEMENT = "reinforcement"
    IMITATION = "imitation"
    EXPLORATION = "exploration"
    ANALOGY = "analogy"
    DECOMPOSITION = "decomposition"
    REHEARSAL = "rehearsal"


class TaskCategory(Enum):
    """Classification of tasks used to pair with learning strategies.

    Different categories of tasks respond differently to each learning
    strategy; the meta-learner builds per-category effectiveness profiles.
    """
    MOTOR = "motor"
    COGNITIVE = "cognitive"
    SOCIAL = "social"
    SPATIAL = "spatial"
    TEMPORAL = "temporal"
    LINGUISTIC = "linguistic"
    STRATEGIC = "strategic"
    CUSTOM = "custom"


class LearningState(Enum):
    """Lifecycle state of a learning episode.

    Episodes progress from initialization through exploration/exploitation
    toward a terminal state (converged, plateaued, or regressed).
    """
    INITIALIZING = "initializing"
    EXPLORING = "exploring"
    EXPLOITING = "exploiting"
    CONVERGED = "converged"
    PLATEAUED = "plateaued"
    REGRESSED = "regressed"


class MetaLearningEventKind(Enum):
    """Kinds of events emitted by the meta-learner.

    Handlers may be registered per kind to observe the learning lifecycle
    without coupling to internal data structures.
    """
    EPISODE_STARTED = "episode_started"
    EPISODE_COMPLETED = "episode_completed"
    STRATEGY_UPDATED = "strategy_updated"
    RATE_ADAPTED = "rate_adapted"
    META_KNOWLEDGE_GAINED = "meta_knowledge_gained"
    CONVERGENCE_DETECTED = "convergence_detected"


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------

@dataclass
class LearningEpisode:
    """A single learning attempt by an agent on a task.

    Records the strategy used, the performance before and after learning,
    the computed improvement, the learning rate applied, the number of
    training steps, and the terminal learning state.

    Attributes:
        id: Unique episode identifier (uuid4 hex).
        agent_id: The agent that performed the learning.
        task_id: The specific task being learned.
        task_category: Category of the task for strategy matching.
        strategy: Learning strategy applied during this episode.
        initial_performance: Performance score before learning (0.0-1.0).
        final_performance: Performance score after learning (0.0-1.0).
        improvement: final - initial performance delta.
        learning_rate: Learning rate used during this episode.
        duration_steps: Number of training steps executed.
        state: Terminal learning state of the episode.
        timestamp: ISO-8601 UTC creation timestamp.
        metadata: Optional auxiliary metadata bag.
    """
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    agent_id: str = ""
    task_id: str = ""
    task_category: str = TaskCategory.CUSTOM.value
    strategy: str = LearningStrategy.EXPLORATION.value
    initial_performance: float = 0.0
    final_performance: float = 0.0
    improvement: float = 0.0
    learning_rate: float = 0.1
    duration_steps: int = 0
    state: str = LearningState.INITIALIZING.value
    timestamp: str = field(
        default_factory=lambda: datetime.datetime.utcnow().isoformat() + "Z"
    )
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "agent_id": self.agent_id,
            "task_id": self.task_id,
            "task_category": self.task_category,
            "strategy": self.strategy,
            "initial_performance": round(self.initial_performance, 6),
            "final_performance": round(self.final_performance, 6),
            "improvement": round(self.improvement, 6),
            "learning_rate": round(self.learning_rate, 6),
            "duration_steps": self.duration_steps,
            "state": self.state,
            "timestamp": self.timestamp,
            "metadata": dict(self.metadata),
        }


@dataclass
class StrategyProfile:
    """Aggregate effectiveness of a strategy for a task category.

    Built from the set of completed episodes sharing the same strategy
    and task category. Used to rank strategies and drive strategy
    selection for new tasks.

    Attributes:
        strategy: The learning strategy this profile describes.
        task_category: The task category this profile applies to.
        total_episodes: Number of episodes aggregated.
        avg_improvement: Mean improvement across episodes.
        success_rate: Fraction of episodes that reached a converged state.
        avg_steps_to_converge: Mean training steps among converged episodes.
        confidence: Belief in this profile's reliability (0.0-1.0).
        last_updated: ISO-8601 UTC timestamp of last update.
    """
    strategy: str = LearningStrategy.EXPLORATION.value
    task_category: str = TaskCategory.CUSTOM.value
    total_episodes: int = 0
    avg_improvement: float = 0.0
    success_rate: float = 0.0
    avg_steps_to_converge: float = 0.0
    confidence: float = 0.0
    last_updated: str = field(
        default_factory=lambda: datetime.datetime.utcnow().isoformat() + "Z"
    )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "strategy": self.strategy,
            "task_category": self.task_category,
            "total_episodes": self.total_episodes,
            "avg_improvement": round(self.avg_improvement, 6),
            "success_rate": round(self.success_rate, 6),
            "avg_steps_to_converge": round(self.avg_steps_to_converge, 6),
            "confidence": round(self.confidence, 6),
            "last_updated": self.last_updated,
        }


@dataclass
class MetaKnowledge:
    """A reusable insight derived from learning experience.

    Meta-knowledge captures generalizable facts about how to learn (e.g.,
    "motor tasks converge fastest with a 0.15 learning rate") that can
    transfer across tasks and agents.

    Attributes:
        id: Unique knowledge identifier (uuid4 hex).
        agent_id: Agent that produced or owns this knowledge.
        key: Human-readable knowledge key.
        value: The knowledge payload (any JSON-serializable value).
        category: Task category this knowledge pertains to.
        confidence: Belief in this knowledge (0.0-1.0).
        source_episodes: Episode IDs that contributed to this knowledge.
        timestamp: ISO-8601 UTC creation timestamp.
    """
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    agent_id: str = ""
    key: str = ""
    value: Any = None
    category: str = TaskCategory.CUSTOM.value
    confidence: float = 0.5
    source_episodes: List[str] = field(default_factory=list)
    timestamp: str = field(
        default_factory=lambda: datetime.datetime.utcnow().isoformat() + "Z"
    )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "agent_id": self.agent_id,
            "key": self.key,
            "value": self.value,
            "category": self.category,
            "confidence": round(self.confidence, 6),
            "source_episodes": list(self.source_episodes),
            "timestamp": self.timestamp,
        }


@dataclass
class AdaptiveRate:
    """Per-agent, per-category adaptive learning rate.

    Tracks the current learning rate along with momentum (exponential
    moving average of recent improvements) and variance of recent
    improvements. Variance is used to detect unstable learning and to
    dampen the rate accordingly.

    Attributes:
        agent_id: The agent this rate applies to.
        task_category: The task category this rate applies to.
        current_rate: Current adapted learning rate.
        momentum: EMA of recent improvements (trend signal).
        variance: Variance of recent improvements (stability signal).
        history: Recent improvement observations used to compute stats.
        last_updated: ISO-8601 UTC timestamp of last adaptation.
    """
    agent_id: str = ""
    task_category: str = TaskCategory.CUSTOM.value
    current_rate: float = 0.1
    momentum: float = 0.0
    variance: float = 0.0
    history: List[float] = field(default_factory=list)
    last_updated: str = field(
        default_factory=lambda: datetime.datetime.utcnow().isoformat() + "Z"
    )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "agent_id": self.agent_id,
            "task_category": self.task_category,
            "current_rate": round(self.current_rate, 6),
            "momentum": round(self.momentum, 6),
            "variance": round(self.variance, 6),
            "history": [round(h, 6) for h in self.history],
            "last_updated": self.last_updated,
        }


@dataclass
class MetaLearningStats:
    """Summary statistics over the entire meta-learner state.

    Attributes:
        total_episodes: Count of all recorded episodes.
        total_agents: Count of distinct agents with episodes.
        total_strategies: Count of distinct strategies observed.
        total_meta_knowledge: Count of meta-knowledge entries.
        avg_improvement: Mean improvement across all episodes.
        best_strategy: Strategy with the highest average improvement.
        last_updated: ISO-8601 UTC timestamp of last computation.
    """
    total_episodes: int = 0
    total_agents: int = 0
    total_strategies: int = 0
    total_meta_knowledge: int = 0
    avg_improvement: float = 0.0
    best_strategy: str = ""
    last_updated: str = field(
        default_factory=lambda: datetime.datetime.utcnow().isoformat() + "Z"
    )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_episodes": self.total_episodes,
            "total_agents": self.total_agents,
            "total_strategies": self.total_strategies,
            "total_meta_knowledge": self.total_meta_knowledge,
            "avg_improvement": round(self.avg_improvement, 6),
            "best_strategy": self.best_strategy,
            "last_updated": self.last_updated,
        }


@dataclass
class MetaLearningSnapshot:
    """Point-in-time snapshot of the meta-learner state.

    Attributes:
        agent_count: Number of distinct agents tracked.
        total_episodes: Total episodes recorded.
        total_strategies: Distinct strategies tracked in profiles.
        total_meta_knowledge: Total meta-knowledge entries stored.
        stats: Computed MetaLearningStats at snapshot time.
        timestamp: ISO-8601 UTC snapshot timestamp.
    """
    agent_count: int = 0
    total_episodes: int = 0
    total_strategies: int = 0
    total_meta_knowledge: int = 0
    stats: Dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(
        default_factory=lambda: datetime.datetime.utcnow().isoformat() + "Z"
    )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "agent_count": self.agent_count,
            "total_episodes": self.total_episodes,
            "total_strategies": self.total_strategies,
            "total_meta_knowledge": self.total_meta_knowledge,
            "stats": dict(self.stats),
            "timestamp": self.timestamp,
        }


@dataclass
class MetaLearningEvent:
    """An observable event emitted by the meta-learner.

    Attributes:
        id: Unique event identifier (uuid4 hex).
        kind: The MetaLearningEventKind discriminator.
        agent_id: Agent the event pertains to (may be empty for global).
        payload: Event-specific data payload.
        timestamp: ISO-8601 UTC event timestamp.
    """
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    kind: str = MetaLearningEventKind.EPISODE_STARTED.value
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
# Meta-Learner Engine (Singleton)
# ---------------------------------------------------------------------------

class MetaLearnerEngine:
    """
    Meta-learning engine that learns how agents learn best.

    Tracks learning episodes per (agent, strategy, task category), builds
    aggregate strategy profiles, maintains adaptive learning rates with
    momentum and variance, and stores reusable meta-knowledge. The engine
    emits observable events for the learning lifecycle and supports
    convergence detection and cross-category transfer estimation.

    The engine is a thread-safe singleton accessed via ``get_instance()``
    or the module-level ``get_meta_learner()`` helper.
    """

    _instance: Optional["MetaLearnerEngine"] = None
    _lock: threading.RLock = threading.RLock()

    # Adaptive rate tuning constants
    _BASE_LEARNING_RATE: float = 0.1
    _MIN_LEARNING_RATE: float = 0.001
    _MAX_LEARNING_RATE: float = 1.0
    _MOMENTUM_COEFFICIENT: float = 0.9
    _RATE_BOOST_FACTOR: float = 1.2
    _RATE_DAMP_FACTOR: float = 0.8
    _RATE_HISTORY_LIMIT: int = 50
    _DEFAULT_SUCCESS_THRESHOLD: float = 0.05
    _CONVERGENCE_VARIANCE_THRESHOLD: float = 0.01
    _TRANSFER_OVERLAP_WEIGHT: float = 0.5
    _TRANSFER_CONFIDENCE_WEIGHT: float = 0.5

    def __new__(cls) -> "MetaLearnerEngine":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    instance = super().__new__(cls)
                    instance._initialized = False
                    cls._instance = instance
        return cls._instance

    @classmethod
    def get_instance(cls) -> "MetaLearnerEngine":
        """Return the singleton MetaLearnerEngine instance.

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

        # Episode storage keyed by episode id, plus agent index
        self._episodes: Dict[str, LearningEpisode] = {}
        self._agent_episodes: Dict[str, List[str]] = {}

        # Strategy profiles keyed by (strategy, task_category) tuple
        self._profiles: Dict[Tuple[str, str], StrategyProfile] = {}

        # Meta-knowledge keyed by id, with per-agent and per-key indexes
        self._meta_knowledge: Dict[str, MetaKnowledge] = {}
        self._agent_meta_knowledge: Dict[str, List[str]] = {}
        self._agent_meta_keys: Dict[str, Dict[str, str]] = {}

        # Adaptive learning rates keyed by (agent_id, task_category)
        self._adaptive_rates: Dict[Tuple[str, str], AdaptiveRate] = {}

        # Event log and pluggable event handlers
        self._events: List[MetaLearningEvent] = []
        self._event_handlers: Dict[
            str, List[Tuple[str, Callable[[MetaLearningEvent], None]]]
        ] = {}

        # Seed the engine with baseline meta-learning data
        self._seed_baseline_data()

    # ------------------------------------------------------------------
    # Seed Data
    # ------------------------------------------------------------------

    def _seed_baseline_data(self) -> None:
        """Populate the engine with baseline episodes, profiles,
        meta-knowledge, and adaptive rates for the seed agents.

        This gives the meta-learner a non-empty starting state so that
        strategy selection and rate adaptation have prior experience to
        draw upon immediately after construction.
        """
        now = datetime.datetime.utcnow().isoformat() + "Z"

        # --- Episodes for agent_alpha -----------------------------------
        alpha_episodes = [
            LearningEpisode(
                id=uuid.uuid4().hex,
                agent_id="agent_alpha",
                task_id="task_motor_balance",
                task_category=TaskCategory.MOTOR.value,
                strategy=LearningStrategy.REINFORCEMENT.value,
                initial_performance=0.3,
                final_performance=0.8,
                improvement=0.5,
                learning_rate=0.15,
                duration_steps=420,
                state=LearningState.CONVERGED.value,
                timestamp=now,
            ),
            LearningEpisode(
                id=uuid.uuid4().hex,
                agent_id="agent_alpha",
                task_id="task_cognitive_puzzle",
                task_category=TaskCategory.COGNITIVE.value,
                strategy=LearningStrategy.DECOMPOSITION.value,
                initial_performance=0.4,
                final_performance=0.75,
                improvement=0.35,
                learning_rate=0.1,
                duration_steps=360,
                state=LearningState.CONVERGED.value,
                timestamp=now,
            ),
            LearningEpisode(
                id=uuid.uuid4().hex,
                agent_id="agent_alpha",
                task_id="task_social_dialogue",
                task_category=TaskCategory.SOCIAL.value,
                strategy=LearningStrategy.IMITATION.value,
                initial_performance=0.2,
                final_performance=0.65,
                improvement=0.45,
                learning_rate=0.08,
                duration_steps=510,
                state=LearningState.PLATEAUED.value,
                timestamp=now,
            ),
            LearningEpisode(
                id=uuid.uuid4().hex,
                agent_id="agent_alpha",
                task_id="task_spatial_navigation",
                task_category=TaskCategory.SPATIAL.value,
                strategy=LearningStrategy.EXPLORATION.value,
                initial_performance=0.5,
                final_performance=0.85,
                improvement=0.35,
                learning_rate=0.12,
                duration_steps=280,
                state=LearningState.CONVERGED.value,
                timestamp=now,
            ),
        ]

        # --- Episodes for agent_beta ------------------------------------
        beta_episodes = [
            LearningEpisode(
                id=uuid.uuid4().hex,
                agent_id="agent_beta",
                task_id="task_strategic_planning",
                task_category=TaskCategory.STRATEGIC.value,
                strategy=LearningStrategy.ANALOGY.value,
                initial_performance=0.35,
                final_performance=0.7,
                improvement=0.35,
                learning_rate=0.08,
                duration_steps=640,
                state=LearningState.EXPLORING.value,
                timestamp=now,
            ),
            LearningEpisode(
                id=uuid.uuid4().hex,
                agent_id="agent_beta",
                task_id="task_temporal_sequencing",
                task_category=TaskCategory.TEMPORAL.value,
                strategy=LearningStrategy.REHEARSAL.value,
                initial_performance=0.6,
                final_performance=0.9,
                improvement=0.3,
                learning_rate=0.1,
                duration_steps=220,
                state=LearningState.CONVERGED.value,
                timestamp=now,
            ),
        ]

        for episode in alpha_episodes + beta_episodes:
            self._episodes[episode.id] = episode
            self._agent_episodes.setdefault(episode.agent_id, []).append(episode.id)

        # --- Strategy profiles ------------------------------------------
        self._profiles[
            (LearningStrategy.REINFORCEMENT.value, TaskCategory.MOTOR.value)
        ] = StrategyProfile(
            strategy=LearningStrategy.REINFORCEMENT.value,
            task_category=TaskCategory.MOTOR.value,
            total_episodes=1,
            avg_improvement=0.5,
            success_rate=0.85,
            avg_steps_to_converge=420.0,
            confidence=0.85,
            last_updated=now,
        )
        self._profiles[
            (LearningStrategy.DECOMPOSITION.value, TaskCategory.COGNITIVE.value)
        ] = StrategyProfile(
            strategy=LearningStrategy.DECOMPOSITION.value,
            task_category=TaskCategory.COGNITIVE.value,
            total_episodes=1,
            avg_improvement=0.35,
            success_rate=0.75,
            avg_steps_to_converge=360.0,
            confidence=0.75,
            last_updated=now,
        )
        self._profiles[
            (LearningStrategy.IMITATION.value, TaskCategory.SOCIAL.value)
        ] = StrategyProfile(
            strategy=LearningStrategy.IMITATION.value,
            task_category=TaskCategory.SOCIAL.value,
            total_episodes=1,
            avg_improvement=0.45,
            success_rate=0.6,
            avg_steps_to_converge=510.0,
            confidence=0.6,
            last_updated=now,
        )

        # --- Meta-knowledge entries -------------------------------------
        motor_rate_knowledge = MetaKnowledge(
            id=uuid.uuid4().hex,
            agent_id="agent_alpha",
            key="motor_learning_optimal_rate",
            value=0.15,
            category=TaskCategory.MOTOR.value,
            confidence=0.85,
            source_episodes=[alpha_episodes[0].id],
            timestamp=now,
        )
        social_observation_knowledge = MetaKnowledge(
            id=uuid.uuid4().hex,
            agent_id="agent_alpha",
            key="social_learning_requires_observation",
            value=True,
            category=TaskCategory.SOCIAL.value,
            confidence=0.7,
            source_episodes=[alpha_episodes[2].id],
            timestamp=now,
        )
        for knowledge in (motor_rate_knowledge, social_observation_knowledge):
            self._meta_knowledge[knowledge.id] = knowledge
            self._agent_meta_knowledge.setdefault(knowledge.agent_id, []).append(
                knowledge.id
            )
            self._agent_meta_keys.setdefault(knowledge.agent_id, {})[
                knowledge.key
            ] = knowledge.id

        # --- Adaptive rates ---------------------------------------------
        self._adaptive_rates[("agent_alpha", TaskCategory.MOTOR.value)] = AdaptiveRate(
            agent_id="agent_alpha",
            task_category=TaskCategory.MOTOR.value,
            current_rate=0.15,
            momentum=0.5,
            variance=0.02,
            history=[0.5],
            last_updated=now,
        )
        self._adaptive_rates[("agent_beta", TaskCategory.STRATEGIC.value)] = AdaptiveRate(
            agent_id="agent_beta",
            task_category=TaskCategory.STRATEGIC.value,
            current_rate=0.08,
            momentum=0.35,
            variance=0.04,
            history=[0.35],
            last_updated=now,
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _now() -> str:
        """Return the current UTC time as an ISO-8601 string with 'Z' suffix."""
        return datetime.datetime.utcnow().isoformat() + "Z"

    def _emit_event(
        self,
        kind: MetaLearningEventKind,
        agent_id: str,
        payload: Dict[str, Any],
    ) -> MetaLearningEvent:
        """Record an event and dispatch it to any registered handlers.

        Handler exceptions are swallowed so that an observer failure can
        never disrupt the core learning flow.
        """
        event = MetaLearningEvent(
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

    def _index_episode(self, episode: LearningEpisode) -> None:
        """Register an episode in the agent index."""
        self._episodes[episode.id] = episode
        agent_list = self._agent_episodes.setdefault(episode.agent_id, [])
        if episode.id not in agent_list:
            agent_list.append(episode.id)
        if len(self._episodes) > _MAX_EPISODES:
            self._evict_oldest_episode()

    def _evict_oldest_episode(self) -> None:
        """Remove the oldest episode to respect the episode capacity."""
        if not self._episodes:
            return
        oldest_id = next(iter(self._episodes))
        oldest = self._episodes.pop(oldest_id, None)
        if oldest is None:
            return
        agent_list = self._agent_episodes.get(oldest.agent_id)
        if agent_list:
            try:
                agent_list.remove(oldest_id)
            except ValueError:
                pass

    def _recompute_profile(
        self, strategy: str, task_category: str
    ) -> Optional[StrategyProfile]:
        """Recompute the aggregate strategy profile from its episodes."""
        matching = [
            ep
            for ep in self._episodes.values()
            if ep.strategy == strategy and ep.task_category == task_category
        ]
        if not matching:
            # If the profile exists but has no episodes, leave it as-is
            # so callers can still see the last known aggregate.
            return self._profiles.get((strategy, task_category))

        total = len(matching)
        avg_improvement = sum(ep.improvement for ep in matching) / total
        converged = [
            ep
            for ep in matching
            if ep.state == LearningState.CONVERGED.value
        ]
        success_rate = len(converged) / total if total else 0.0
        avg_steps = (
            sum(ep.duration_steps for ep in converged) / len(converged)
            if converged
            else 0.0
        )
        # Confidence grows with sample count, capped at 1.0.
        confidence = min(1.0, total / 20.0)

        profile = self._profiles.get((strategy, task_category))
        if profile is None:
            profile = StrategyProfile(
                strategy=strategy,
                task_category=task_category,
            )
        profile.total_episodes = total
        profile.avg_improvement = avg_improvement
        profile.success_rate = success_rate
        profile.avg_steps_to_converge = avg_steps
        profile.confidence = confidence
        profile.last_updated = self._now()
        self._profiles[(strategy, task_category)] = profile
        return profile

    # ------------------------------------------------------------------
    # Episode Management
    # ------------------------------------------------------------------

    def start_episode(
        self,
        agent_id: str,
        task_id: str,
        task_category: TaskCategory,
        strategy: LearningStrategy,
        initial_performance: float,
        learning_rate: float,
    ) -> LearningEpisode:
        """Begin tracking a new learning episode.

        The episode is created in the INITIALIZING state and recorded in
        the engine. An EPISODE_STARTED event is emitted.

        Args:
            agent_id: Identifier of the learning agent.
            task_id: Identifier of the task being learned.
            task_category: Category of the task.
            strategy: Learning strategy to apply.
            initial_performance: Starting performance score (0.0-1.0).
            learning_rate: Learning rate to use for this episode.

        Returns:
            The newly created LearningEpisode.
        """
        with self._lock:
            episode = LearningEpisode(
                id=uuid.uuid4().hex,
                agent_id=agent_id,
                task_id=task_id,
                task_category=task_category.value,
                strategy=strategy.value,
                initial_performance=initial_performance,
                final_performance=initial_performance,
                improvement=0.0,
                learning_rate=learning_rate,
                duration_steps=0,
                state=LearningState.INITIALIZING.value,
                timestamp=self._now(),
            )
            self._index_episode(episode)
            self._emit_event(
                MetaLearningEventKind.EPISODE_STARTED,
                agent_id,
                {
                    "episode_id": episode.id,
                    "task_id": task_id,
                    "task_category": task_category.value,
                    "strategy": strategy.value,
                    "initial_performance": initial_performance,
                },
            )
            return episode

    def complete_episode(
        self,
        episode_id: str,
        final_performance: float,
        duration_steps: int,
        state: LearningState,
    ) -> Optional[LearningEpisode]:
        """Finalize a learning episode with the observed outcome.

        Computes the improvement delta, updates the relevant strategy
        profile, and feeds the improvement into the adaptive rate. An
        EPISODE_COMPLETED event is emitted, plus a STRATEGY_UPDATED event
        if the profile changed and a CONVERGENCE_DETECTED event if the
        episode reached convergence.

        Args:
            episode_id: The episode to finalize.
            final_performance: Performance after learning (0.0-1.0).
            duration_steps: Number of training steps executed.
            state: Terminal learning state.

        Returns:
            The updated LearningEpisode, or None if not found.
        """
        with self._lock:
            episode = self._episodes.get(episode_id)
            if episode is None:
                return None

            episode.final_performance = final_performance
            episode.improvement = final_performance - episode.initial_performance
            episode.duration_steps = duration_steps
            episode.state = state.value
            episode.timestamp = self._now()

            # Refresh the strategy profile from the episode set.
            try:
                strategy_enum = LearningStrategy(episode.strategy)
                category_enum = TaskCategory(episode.task_category)
            except ValueError:
                strategy_enum = None
                category_enum = None

            profile = self._recompute_profile(
                episode.strategy, episode.task_category
            )

            self._emit_event(
                MetaLearningEventKind.EPISODE_COMPLETED,
                episode.agent_id,
                {
                    "episode_id": episode.id,
                    "final_performance": final_performance,
                    "improvement": episode.improvement,
                    "duration_steps": duration_steps,
                    "state": state.value,
                },
            )

            if profile is not None:
                self._emit_event(
                    MetaLearningEventKind.STRATEGY_UPDATED,
                    episode.agent_id,
                    {
                        "strategy": profile.strategy,
                        "task_category": profile.task_category,
                        "avg_improvement": profile.avg_improvement,
                        "success_rate": profile.success_rate,
                        "confidence": profile.confidence,
                    },
                )

            # Feed the improvement into the adaptive rate.
            if strategy_enum is not None and category_enum is not None:
                self._update_adaptive_rate(
                    episode.agent_id, category_enum, episode.improvement
                )

            if state == LearningState.CONVERGED:
                self._emit_event(
                    MetaLearningEventKind.CONVERGENCE_DETECTED,
                    episode.agent_id,
                    {
                        "episode_id": episode.id,
                        "task_category": episode.task_category,
                        "strategy": episode.strategy,
                        "final_performance": final_performance,
                    },
                )

            return episode

    def get_episode(self, episode_id: str) -> Optional[LearningEpisode]:
        """Retrieve an episode by id."""
        with self._lock:
            return self._episodes.get(episode_id)

    def list_episodes(
        self,
        agent_id: Optional[str] = None,
        task_category: Optional[TaskCategory] = None,
        strategy: Optional[LearningStrategy] = None,
        limit: int = 100,
    ) -> List[LearningEpisode]:
        """List episodes optionally filtered by agent, category, and strategy.

        Results are returned in reverse chronological order (most recent
        first) up to ``limit`` entries.
        """
        with self._lock:
            if agent_id is not None:
                ids = self._agent_episodes.get(agent_id, [])
                episodes = [self._episodes[i] for i in ids if i in self._episodes]
            else:
                episodes = list(self._episodes.values())

            if task_category is not None:
                episodes = [
                    ep for ep in episodes if ep.task_category == task_category.value
                ]
            if strategy is not None:
                episodes = [
                    ep for ep in episodes if ep.strategy == strategy.value
                ]

            episodes.sort(key=lambda e: e.timestamp, reverse=True)
            return episodes[:limit]

    # ------------------------------------------------------------------
    # Strategy Profiles
    # ------------------------------------------------------------------

    def get_strategy_profile(
        self,
        strategy: LearningStrategy,
        task_category: TaskCategory,
    ) -> Optional[StrategyProfile]:
        """Get the aggregate profile for a strategy + task category."""
        with self._lock:
            return self._profiles.get((strategy.value, task_category.value))

    def list_strategy_profiles(
        self, agent_id: Optional[str] = None
    ) -> List[StrategyProfile]:
        """List strategy profiles.

        If ``agent_id`` is provided, only profiles for which the agent has
        recorded episodes are returned. Otherwise all profiles are listed.
        """
        with self._lock:
            if agent_id is None:
                return list(self._profiles.values())

            agent_episode_ids = self._agent_episodes.get(agent_id, [])
            agent_episodes = [
                self._episodes[i] for i in agent_episode_ids if i in self._episodes
            ]
            relevant_keys = {
                (ep.strategy, ep.task_category) for ep in agent_episodes
            }
            return [
                self._profiles[k]
                for k in relevant_keys
                if k in self._profiles
            ]

    def select_best_strategy(
        self,
        agent_id: str,
        task_category: TaskCategory,
    ) -> Optional[LearningStrategy]:
        """Select the best learning strategy for a task category.

        Ranks all strategies that have a profile for the given category by
        a composite score blending average improvement, success rate, and
        confidence. Returns the top-ranked strategy, or None if no profile
        exists for the category.
        """
        with self._lock:
            candidates: List[Tuple[float, StrategyProfile]] = []
            for (strategy, category), profile in self._profiles.items():
                if category != task_category.value:
                    continue
                # Composite score: weighted blend of the three signals.
                score = (
                    0.45 * profile.avg_improvement
                    + 0.35 * profile.success_rate
                    + 0.20 * profile.confidence
                )
                candidates.append((score, profile))

            if not candidates:
                return None

            candidates.sort(key=lambda item: item[0], reverse=True)
            best = candidates[0][1]
            try:
                return LearningStrategy(best.strategy)
            except ValueError:
                return None

    # ------------------------------------------------------------------
    # Adaptive Learning Rates
    # ------------------------------------------------------------------

    def _apply_momentum_and_adjust(self, rate: AdaptiveRate) -> None:
        """Recompute momentum, variance, and adjust the current rate.

        Momentum is an EMA of the improvement history; variance measures
        stability. The rate is boosted when momentum is positive and
        variance is low, damped when momentum is negative or variance is
        high, and left steady otherwise.
        """
        if not rate.history:
            return
        momentum = rate.history[0]
        for value in rate.history[1:]:
            momentum = self._MOMENTUM_COEFFICIENT * momentum + (
                1.0 - self._MOMENTUM_COEFFICIENT
            ) * value
        rate.momentum = momentum
        mean = sum(rate.history) / len(rate.history)
        rate.variance = sum((v - mean) ** 2 for v in rate.history) / len(rate.history)

        if rate.momentum > 0 and rate.variance < self._CONVERGENCE_VARIANCE_THRESHOLD:
            # Stable positive progress - boost the rate.
            rate.current_rate = min(
                self._MAX_LEARNING_RATE,
                rate.current_rate * self._RATE_BOOST_FACTOR,
            )
        elif rate.momentum < 0 or rate.variance >= 0.05:
            # Negative progress or instability - damp the rate.
            rate.current_rate = max(
                self._MIN_LEARNING_RATE,
                rate.current_rate * self._RATE_DAMP_FACTOR,
            )
        # else: keep the rate steady when momentum is mildly positive.
        rate.last_updated = self._now()

    def _emit_rate_adapted(self, agent_id: str, rate: AdaptiveRate) -> None:
        """Emit a RATE_ADAPTED event for the given adaptive rate."""
        self._emit_event(
            MetaLearningEventKind.RATE_ADAPTED,
            agent_id,
            {
                "task_category": rate.task_category,
                "current_rate": rate.current_rate,
                "momentum": rate.momentum,
                "variance": rate.variance,
            },
        )

    def _get_or_create_rate(
        self, agent_id: str, task_category: TaskCategory
    ) -> AdaptiveRate:
        """Get the adaptive rate for an agent+category, creating a default if absent."""
        key = (agent_id, task_category.value)
        rate = self._adaptive_rates.get(key)
        if rate is None:
            rate = AdaptiveRate(
                agent_id=agent_id,
                task_category=task_category.value,
                current_rate=self._BASE_LEARNING_RATE,
            )
            self._adaptive_rates[key] = rate
        return rate

    def _update_adaptive_rate(
        self,
        agent_id: str,
        task_category: TaskCategory,
        improvement: float,
    ) -> AdaptiveRate:
        """Internal: feed an improvement observation into the adaptive rate."""
        rate = self._get_or_create_rate(agent_id, task_category)
        rate.history.append(improvement)
        if len(rate.history) > self._RATE_HISTORY_LIMIT:
            rate.history = rate.history[-self._RATE_HISTORY_LIMIT:]
        self._apply_momentum_and_adjust(rate)
        self._emit_rate_adapted(agent_id, rate)
        return rate

    def adapt_learning_rate(
        self,
        agent_id: str,
        task_category: TaskCategory,
    ) -> AdaptiveRate:
        """Adapt and return the learning rate for an agent + task category.

        Triggers adaptation from recent episode history for the given
        agent and category, then returns the updated AdaptiveRate. If no
        prior rate exists, a default-rate AdaptiveRate is created.
        """
        with self._lock:
            key = (agent_id, task_category.value)
            rate = self._get_or_create_rate(agent_id, task_category)

            # Pull recent improvements for this agent+category from episodes.
            agent_episode_ids = self._agent_episodes.get(agent_id, [])
            improvements: List[float] = []
            for eid in agent_episode_ids:
                ep = self._episodes.get(eid)
                if (
                    ep is not None
                    and ep.task_category == task_category.value
                    and ep.state != LearningState.INITIALIZING.value
                ):
                    improvements.append(ep.improvement)

            if improvements:
                rate.history = list(improvements)
                if len(rate.history) > self._RATE_HISTORY_LIMIT:
                    rate.history = rate.history[-self._RATE_HISTORY_LIMIT:]
                self._apply_momentum_and_adjust(rate)
                self._emit_rate_adapted(agent_id, rate)

            if len(self._adaptive_rates) > _MAX_RATES:
                # Evict a single oldest rate entry to stay within capacity.
                oldest_key = next(iter(self._adaptive_rates))
                if oldest_key != key:
                    self._adaptive_rates.pop(oldest_key, None)

            return rate

    def get_adaptive_rate(
        self,
        agent_id: str,
        task_category: TaskCategory,
    ) -> AdaptiveRate:
        """Get the adaptive rate for an agent + task category.

        Returns the existing AdaptiveRate, or a fresh default-rate one if
        none exists yet (without persisting it).
        """
        with self._lock:
            key = (agent_id, task_category.value)
            rate = self._adaptive_rates.get(key)
            if rate is not None:
                return rate
            return AdaptiveRate(
                agent_id=agent_id,
                task_category=task_category.value,
                current_rate=self._BASE_LEARNING_RATE,
            )

    # ------------------------------------------------------------------
    # Meta-Knowledge
    # ------------------------------------------------------------------

    def register_meta_knowledge(
        self,
        agent_id: str,
        key: str,
        value: Any,
        category: str = TaskCategory.CUSTOM.value,
        confidence: float = 0.5,
        source_episodes: Optional[List[str]] = None,
    ) -> MetaKnowledge:
        """Register or update a meta-knowledge entry.

        If an entry with the same (agent_id, key) already exists, it is
        updated in place; otherwise a new entry is created. A
        META_KNOWLEDGE_GAINED event is emitted.
        """
        with self._lock:
            source = list(source_episodes) if source_episodes else []
            existing_id = self._agent_meta_keys.get(agent_id, {}).get(key)

            if existing_id and existing_id in self._meta_knowledge:
                knowledge = self._meta_knowledge[existing_id]
                knowledge.value = value
                knowledge.category = category
                knowledge.confidence = confidence
                # Merge source episodes without duplicates.
                merged = list(knowledge.source_episodes)
                for sid in source:
                    if sid not in merged:
                        merged.append(sid)
                knowledge.source_episodes = merged
                knowledge.timestamp = self._now()
            else:
                knowledge = MetaKnowledge(
                    id=uuid.uuid4().hex,
                    agent_id=agent_id,
                    key=key,
                    value=value,
                    category=category,
                    confidence=confidence,
                    source_episodes=source,
                    timestamp=self._now(),
                )
                self._meta_knowledge[knowledge.id] = knowledge
                self._agent_meta_knowledge.setdefault(agent_id, []).append(
                    knowledge.id
                )
                self._agent_meta_keys.setdefault(agent_id, {})[key] = knowledge.id

                if len(self._meta_knowledge) > _MAX_META_KNOWLEDGE:
                    self._evict_oldest_meta_knowledge()

            self._emit_event(
                MetaLearningEventKind.META_KNOWLEDGE_GAINED,
                agent_id,
                {
                    "knowledge_id": knowledge.id,
                    "key": key,
                    "category": category,
                    "confidence": confidence,
                },
            )
            return knowledge

    def _evict_oldest_meta_knowledge(self) -> None:
        """Remove the oldest meta-knowledge entry to respect capacity."""
        if not self._meta_knowledge:
            return
        oldest_id = next(iter(self._meta_knowledge))
        oldest = self._meta_knowledge.pop(oldest_id, None)
        if oldest is None:
            return
        agent_list = self._agent_meta_knowledge.get(oldest.agent_id)
        if agent_list:
            try:
                agent_list.remove(oldest_id)
            except ValueError:
                pass
        key_map = self._agent_meta_keys.get(oldest.agent_id)
        if key_map and key_map.get(oldest.key) == oldest_id:
            del key_map[oldest.key]

    def get_meta_knowledge(
        self,
        agent_id: str,
        key: str,
    ) -> Optional[MetaKnowledge]:
        """Get a specific meta-knowledge entry by agent and key."""
        with self._lock:
            knowledge_id = self._agent_meta_keys.get(agent_id, {}).get(key)
            if knowledge_id is None:
                return None
            return self._meta_knowledge.get(knowledge_id)

    def list_meta_knowledge(
        self,
        agent_id: str,
        category: Optional[str] = None,
    ) -> List[MetaKnowledge]:
        """List meta-knowledge for an agent, optionally filtered by category."""
        with self._lock:
            ids = self._agent_meta_knowledge.get(agent_id, [])
            results = [
                self._meta_knowledge[i]
                for i in ids
                if i in self._meta_knowledge
            ]
            if category is not None:
                results = [k for k in results if k.category == category]
            return results

    def remove_meta_knowledge(self, knowledge_id: str) -> bool:
        """Remove a meta-knowledge entry by id.

        Returns True if an entry was removed, False if not found.
        """
        with self._lock:
            knowledge = self._meta_knowledge.pop(knowledge_id, None)
            if knowledge is None:
                return False
            agent_list = self._agent_meta_knowledge.get(knowledge.agent_id)
            if agent_list:
                try:
                    agent_list.remove(knowledge_id)
                except ValueError:
                    pass
            key_map = self._agent_meta_keys.get(knowledge.agent_id)
            if key_map and key_map.get(knowledge.key) == knowledge_id:
                del key_map[knowledge.key]
            return True

    # ------------------------------------------------------------------
    # Convergence Detection & Transfer Potential
    # ------------------------------------------------------------------

    def detect_convergence(
        self,
        agent_id: str,
        task_category: TaskCategory,
        window: int = 10,
    ) -> Dict[str, Any]:
        """Detect whether an agent has converged on a task category.

        Analyzes the most recent ``window`` completed episodes for the
        given agent and category. Convergence is declared when the average
        improvement is small (below the success threshold) and the
        variance of improvements is below the convergence threshold,
        indicating stable, diminishing returns.

        Args:
            agent_id: The agent to analyze.
            task_category: The task category to analyze.
            window: Number of recent episodes to consider.

        Returns:
            Dict with ``converged`` (bool), ``avg_improvement`` (float),
            and ``variance`` (float). Returns zeroed values when no
            episodes are available.
        """
        with self._lock:
            agent_episode_ids = self._agent_episodes.get(agent_id, [])
            episodes = [
                self._episodes[i]
                for i in agent_episode_ids
                if i in self._episodes
            ]
            episodes = [
                ep
                for ep in episodes
                if ep.task_category == task_category.value
                and ep.state != LearningState.INITIALIZING.value
            ]
            episodes.sort(key=lambda e: e.timestamp, reverse=True)
            recent = episodes[: max(0, window)]

            if not recent:
                return {
                    "converged": False,
                    "avg_improvement": 0.0,
                    "variance": 0.0,
                    "samples": 0,
                }

            improvements = [ep.improvement for ep in recent]
            avg_improvement = sum(improvements) / len(improvements)
            mean = avg_improvement
            variance = sum((v - mean) ** 2 for v in improvements) / len(improvements)

            converged = (
                abs(avg_improvement) < self._DEFAULT_SUCCESS_THRESHOLD
                and variance < self._CONVERGENCE_VARIANCE_THRESHOLD
            )

            return {
                "converged": converged,
                "avg_improvement": round(avg_improvement, 6),
                "variance": round(variance, 6),
                "samples": len(recent),
            }

    def get_transfer_potential(
        self,
        agent_id: str,
        source_category: TaskCategory,
        target_category: TaskCategory,
    ) -> Dict[str, Any]:
        """Estimate how well learning in one category transfers to another.

        Computes a transfer potential score (0.0-1.0) based on the
        confidence and success rate of the source category profile and the
        overlap of strategies used across both categories. A higher score
        suggests knowledge from the source category is likely to benefit
        learning in the target category.

        Args:
            agent_id: The agent to estimate transfer for.
            source_category: The category with prior learning.
            target_category: The category to transfer into.

        Returns:
            Dict with ``potential`` (float 0-1), ``rationale`` (str),
            ``source_confidence``, and ``strategy_overlap``.
        """
        with self._lock:
            source_profiles = [
                p
                for (strategy, category), p in self._profiles.items()
                if category == source_category.value
            ]
            target_profiles = [
                p
                for (strategy, category), p in self._profiles.items()
                if category == target_category.value
            ]

            if not source_profiles:
                return {
                    "potential": 0.0,
                    "rationale": (
                        "No source-category learning experience available "
                        "to estimate transfer potential."
                    ),
                    "source_confidence": 0.0,
                    "strategy_overlap": 0.0,
                }

            # Best source profile by confidence.
            best_source = max(source_profiles, key=lambda p: p.confidence)
            source_confidence = best_source.confidence
            source_success = best_source.success_rate

            # Strategy overlap between source and target categories.
            source_strategies = {
                p.strategy for p in source_profiles
            }
            target_strategies = {
                p.strategy for p in target_profiles
            }
            if source_strategies and target_strategies:
                overlap = len(source_strategies & target_strategies) / max(
                    len(source_strategies | target_strategies), 1
                )
            else:
                overlap = 0.0

            # Potential blends confidence/success with strategy overlap.
            confidence_signal = (
                0.5 * source_confidence + 0.5 * source_success
            )
            potential = (
                self._TRANSFER_CONFIDENCE_WEIGHT * confidence_signal
                + self._TRANSFER_OVERLAP_WEIGHT * overlap
            )
            potential = max(0.0, min(1.0, potential))

            if potential >= 0.7:
                rationale = (
                    "High transfer potential: strong source confidence and "
                    "shared strategies between categories."
                )
            elif potential >= 0.4:
                rationale = (
                    "Moderate transfer potential: partial overlap in "
                    "strategies or moderate source confidence."
                )
            else:
                rationale = (
                    "Low transfer potential: limited shared strategies or "
                    "insufficient source confidence."
                )

            return {
                "potential": round(potential, 6),
                "rationale": rationale,
                "source_confidence": round(source_confidence, 6),
                "strategy_overlap": round(overlap, 6),
            }

    # ------------------------------------------------------------------
    # Event Handlers
    # ------------------------------------------------------------------

    def register_event_handler(
        self,
        kind: MetaLearningEventKind,
        handler: Callable[[MetaLearningEvent], None],
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
            for kind, handlers in self._event_handlers.items():
                for i, (hid, _) in enumerate(handlers):
                    if hid == handler_id:
                        del handlers[i]
                        return True
            return False

    def list_events(
        self,
        event_kind: Optional[MetaLearningEventKind] = None,
        limit: int = 100,
    ) -> List[MetaLearningEvent]:
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

    def get_stats(self) -> MetaLearningStats:
        """Compute summary statistics over the current engine state."""
        with self._lock:
            episodes = list(self._episodes.values())
            total_episodes = len(episodes)

            agents = {ep.agent_id for ep in episodes}
            strategies = {ep.strategy for ep in episodes}

            if episodes:
                avg_improvement = sum(
                    ep.improvement for ep in episodes
                ) / total_episodes
            else:
                avg_improvement = 0.0

            # Best strategy by average improvement across its episodes.
            strategy_improvements: Dict[str, List[float]] = {}
            for ep in episodes:
                strategy_improvements.setdefault(ep.strategy, []).append(
                    ep.improvement
                )
            best_strategy = ""
            best_score = -float("inf")
            for strategy, improvements in strategy_improvements.items():
                score = sum(improvements) / len(improvements)
                if score > best_score:
                    best_score = score
                    best_strategy = strategy

            return MetaLearningStats(
                total_episodes=total_episodes,
                total_agents=len(agents),
                total_strategies=len(strategies),
                total_meta_knowledge=len(self._meta_knowledge),
                avg_improvement=avg_improvement,
                best_strategy=best_strategy,
                last_updated=self._now(),
            )

    def get_status(self) -> Dict[str, Any]:
        """Return a comprehensive status dictionary for diagnostics."""
        with self._lock:
            episodes = list(self._episodes.values())
            converged = sum(
                1 for ep in episodes if ep.state == LearningState.CONVERGED.value
            )
            plateaued = sum(
                1 for ep in episodes if ep.state == LearningState.PLATEAUED.value
            )
            exploring = sum(
                1 for ep in episodes if ep.state == LearningState.EXPLORING.value
            )

            state_distribution: Dict[str, int] = {}
            for ep in episodes:
                state_distribution[ep.state] = (
                    state_distribution.get(ep.state, 0) + 1
                )

            return {
                "initialized": self._initialized,
                "total_episodes": len(episodes),
                "total_profiles": len(self._profiles),
                "total_meta_knowledge": len(self._meta_knowledge),
                "total_adaptive_rates": len(self._adaptive_rates),
                "total_events": len(self._events),
                "converged_episodes": converged,
                "plateaued_episodes": plateaued,
                "exploring_episodes": exploring,
                "state_distribution": state_distribution,
                "capacity_limits": {
                    "max_episodes": _MAX_EPISODES,
                    "max_profiles": _MAX_PROFILES,
                    "max_meta_knowledge": _MAX_META_KNOWLEDGE,
                    "max_rates": _MAX_RATES,
                    "max_events": _MAX_EVENTS,
                },
                "last_updated": self._now(),
            }

    def get_snapshot(self) -> MetaLearningSnapshot:
        """Capture a point-in-time snapshot of the engine state."""
        with self._lock:
            stats = self.get_stats()
            agents = {ep.agent_id for ep in self._episodes.values()}
            strategies = {p.strategy for p in self._profiles.values()}
            return MetaLearningSnapshot(
                agent_count=len(agents),
                total_episodes=len(self._episodes),
                total_strategies=len(strategies),
                total_meta_knowledge=len(self._meta_knowledge),
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
            self._episodes.clear()
            self._agent_episodes.clear()
            self._profiles.clear()
            self._meta_knowledge.clear()
            self._agent_meta_knowledge.clear()
            self._agent_meta_keys.clear()
            self._adaptive_rates.clear()
            self._events.clear()
            self._event_handlers.clear()


# ---------------------------------------------------------------------------
# Module-Level Accessor
# ---------------------------------------------------------------------------

def get_meta_learner() -> MetaLearnerEngine:
    """Return the singleton MetaLearnerEngine instance."""
    return MetaLearnerEngine.get_instance()
