"""
SparkLabs Agent - Value Alignment, Reward Shaping, and Lifelong Learning Engine

A unified engine that ensures AI agents operating inside the SparkLabs
AI-native game engine behave in accordance with human values while
continuously improving across the tasks they encounter.

The engine combines three tightly coupled capabilities:

  1. Value Alignment
       Agents learn and adhere to a configurable set of value principles
       (honesty, fairness, autonomy, safety, ...) through structured human
       and peer feedback.  Each piece of feedback is tied to a value category
       and either reinforces or corrects agent behavior.

  2. Reward Shaping
       Rather than passing raw environmental rewards directly into a learning
       loop, the engine augments them with strategy-based bonuses (curiosity,
       mastery, alignment, safety penalty, ...).  This guides exploration
       toward aligned behavior and away from harmful trajectories.

  3. Lifelong Learning
       Agents accumulate knowledge units across many tasks and domains.  The
       engine tracks a per-agent lifelong learning record (current phase,
       tasks completed, knowledge count, transfer count, forgetting events)
       and supports transfer of knowledge between domains with effectiveness
       estimation, so that learned skill does not catastrophically vanish
       when the agent moves to a new task.

Architecture:
  ValueAlignmentEngine (Singleton, double-checked locking)
    |-- ValuePrinciple       -- a human value the agent should uphold
    |-- FeedbackRecord       -- a single piece of human / peer feedback
    |-- RewardSignal         -- the result of shaping a base reward
    |-- ShapingConfig        -- per-strategy shaping configuration
    |-- KnowledgeUnit        -- a single unit of accumulated knowledge
    |-- LifelongRecord       -- per-agent lifelong learning state
    |-- TransferRecord       -- a single knowledge transfer event
    |-- AlignmentAssessment  -- a full alignment evaluation for an agent
    |-- AlignmentStats       -- aggregate engine statistics
    |-- AlignmentSnapshot    -- complete engine state snapshot
    |-- AlignmentEvent       -- observable engine lifecycle event

All public mutating methods are protected by a re-entrant lock so the engine
is safe to call from multiple agent threads.  Bounded in-memory stores use
FIFO eviction when their capacity constants are exceeded.
"""

from __future__ import annotations

import datetime
import threading
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------------
# Capacity constants - bounded in-memory stores with FIFO eviction
# ---------------------------------------------------------------------------

_MAX_PRINCIPLES: int = 500
_MAX_FEEDBACK: int = 5000
_MAX_REWARDS: int = 10000
_MAX_KNOWLEDGE: int = 5000
_MAX_TRANSFERS: int = 2000
_MAX_ASSESSMENTS: int = 1000
_MAX_EVENTS: int = 2000


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _now() -> str:
    """Return a UTC ISO-8601 timestamp string terminated with 'Z'."""
    return datetime.datetime.utcnow().isoformat() + "Z"


def _new_id() -> str:
    """Generate a short unique identifier for a record."""
    return uuid.uuid4().hex[:16]


def _clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    """Clamp a numeric value into the inclusive [low, high] range."""
    if value < low:
        return low
    if value > high:
        return high
    return value


def _domain_similarity(source_domain: str, target_domain: str) -> float:
    """Estimate similarity between two domain labels in [0.0, 1.0].

    Uses a simple token-overlap heuristic so that closely named domains
    (for example "combat" and "stealth_combat") transfer more effectively
    than unrelated ones.
    """
    if not source_domain and not target_domain:
        return 1.0
    source_tokens = {t for t in source_domain.lower().split("_") if t}
    target_tokens = {t for t in target_domain.lower().split("_") if t}
    if not source_tokens or not target_tokens:
        return 0.0
    intersection = source_tokens & target_tokens
    union = source_tokens | target_tokens
    return len(intersection) / len(union)


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class ValueCategory(Enum):
    """Categories of human values that an agent may be expected to uphold."""
    HONESTY = "honesty"
    FAIRNESS = "fairness"
    AUTONOMY = "autonomy"
    NON_MALEFICENCE = "non_maleficence"
    BENEFICENCE = "beneficence"
    JUSTICE = "justice"
    LOYALTY = "loyalty"
    CREATIVITY = "creativity"
    DILIGENCE = "diligence"
    HARMONY = "harmony"
    SAFETY = "safety"
    COOPERATION = "cooperation"
    EXCELLENCE = "excellence"
    WISDOM = "wisdom"
    COMPASSION = "compassion"


class ValueStatus(Enum):
    """Lifecycle / health state of a value principle."""
    ACTIVE = "active"
    DORMANT = "dormant"
    VIOLATED = "violated"
    REINFORCED = "reinforced"
    CONTESTED = "contested"


class FeedbackType(Enum):
    """The nature of a piece of feedback delivered to an agent."""
    APPROVAL = "approval"
    DISAPPROVAL = "disapproval"
    CORRECTION = "correction"
    PREFERENCE = "preference"
    DEMONSTRATION = "demonstration"
    CRITIQUE = "critique"
    REWARD = "reward"
    PENALTY = "penalty"


class FeedbackSource(Enum):
    """Where a piece of feedback originated."""
    HUMAN_EXPLICIT = "human_explicit"
    HUMAN_IMPLICIT = "human_implicit"
    PEER_AGENT = "peer_agent"
    SYSTEM_RULE = "system_rule"
    SELF_REFLECTION = "self_reflection"
    CROWD_SOURCE = "crowd_source"


class ShapingStrategy(Enum):
    """Reward-shaping strategies that may contribute to a shaped reward."""
    POTENTIAL_BASED = "potential_based"
    REWARD_SHAPING = "reward_shaping"
    CURIOSITY_BONUS = "curiosity_bonus"
    NOVELTY_BONUS = "novelty_bonus"
    MASTERY_BONUS = "mastery_bonus"
    SOCIAL_BONUS = "social_bonus"
    SAFETY_PENALTY = "safety_penalty"
    EFFICIENCY_BONUS = "efficiency_bonus"
    ALIGNMENT_BONUS = "alignment_bonus"


class LearningPhase(Enum):
    """Phases of the lifelong learning cycle for an agent."""
    ACQUISITION = "acquisition"
    CONSOLIDATION = "consolidation"
    RETENTION = "retention"
    TRANSFER = "transfer"
    FORGETTING_PREVENTION = "forgetting_prevention"
    REFINEMENT = "refinement"


class KnowledgeType(Enum):
    """Classification of accumulated knowledge units."""
    PROCEDURAL = "procedural"
    DECLARATIVE = "declarative"
    EPISODIC = "episodic"
    SEMANTIC = "semantic"
    CONDITIONAL = "conditional"
    METACOGNITIVE = "metacognitive"
    SOCIAL = "social"
    VALUE = "value"


class TransferType(Enum):
    """Outcome classification of a knowledge transfer event."""
    POSITIVE = "positive"
    NEGATIVE = "negative"
    ZERO = "zero"
    LATERAL = "lateral"
    VERTICAL = "vertical"


class AlignmentEventKind(Enum):
    """Kinds of events emitted by the value alignment engine."""
    VALUE_REGISTERED = "value_registered"
    VALUE_UPDATED = "value_updated"
    FEEDBACK_RECEIVED = "feedback_received"
    REWARD_SHAPED = "reward_shaped"
    KNOWLEDGE_ACQUIRED = "knowledge_acquired"
    KNOWLEDGE_TRANSFERRED = "knowledge_transferred"
    ALIGNMENT_DRIFT = "alignment_drift"
    CORRECTION_APPLIED = "correction_applied"
    POLICY_UPDATED = "policy_updated"


class DriftDirection(Enum):
    """Direction in which an agent's alignment is drifting."""
    TOWARD_ALIGNMENT = "toward_alignment"
    AWAY_FROM_ALIGNMENT = "away_from_alignment"
    NEUTRAL = "neutral"


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------

@dataclass
class ValuePrinciple:
    """A human value that an agent is expected to uphold."""
    id: str = field(default_factory=_new_id)
    name: str = ""
    category: ValueCategory = ValueCategory.HONESTY
    description: str = ""
    weight: float = 1.0
    status: ValueStatus = ValueStatus.ACTIVE
    violation_count: int = 0
    reinforcement_count: int = 0
    last_evaluated: str = field(default_factory=_now)
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "category": self.category.value,
            "description": self.description,
            "weight": self.weight,
            "status": self.status.value,
            "violation_count": self.violation_count,
            "reinforcement_count": self.reinforcement_count,
            "last_evaluated": self.last_evaluated,
            "metadata": dict(self.metadata),
            "timestamp": self.timestamp,
        }


@dataclass
class FeedbackRecord:
    """A single piece of feedback delivered to an agent about a value."""
    id: str = field(default_factory=_new_id)
    agent_id: str = ""
    value_category: ValueCategory = ValueCategory.HONESTY
    feedback_type: FeedbackType = FeedbackType.APPROVAL
    source: FeedbackSource = FeedbackSource.HUMAN_EXPLICIT
    content: str = ""
    severity: float = 0.5
    reward_delta: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "agent_id": self.agent_id,
            "value_category": self.value_category.value,
            "feedback_type": self.feedback_type.value,
            "source": self.source.value,
            "content": self.content,
            "severity": self.severity,
            "reward_delta": self.reward_delta,
            "metadata": dict(self.metadata),
            "timestamp": self.timestamp,
        }


@dataclass
class RewardSignal:
    """The result of shaping a base reward for an agent."""
    id: str = field(default_factory=_new_id)
    agent_id: str = ""
    base_reward: float = 0.0
    shaped_reward: float = 0.0
    shaping_components: Dict[str, float] = field(default_factory=dict)
    total_bonus: float = 0.0
    alignment_score: float = 0.0
    context: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "agent_id": self.agent_id,
            "base_reward": self.base_reward,
            "shaped_reward": self.shaped_reward,
            "shaping_components": dict(self.shaping_components),
            "total_bonus": self.total_bonus,
            "alignment_score": self.alignment_score,
            "context": dict(self.context),
            "metadata": dict(self.metadata),
            "timestamp": self.timestamp,
        }


@dataclass
class ShapingConfig:
    """Configuration for a single reward-shaping strategy."""
    id: str = field(default_factory=_new_id)
    strategy: ShapingStrategy = ShapingStrategy.POTENTIAL_BASED
    weight: float = 1.0
    enabled: bool = True
    decay_rate: float = 0.0
    min_bonus: float = -1.0
    max_bonus: float = 1.0
    conditions: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "strategy": self.strategy.value,
            "weight": self.weight,
            "enabled": self.enabled,
            "decay_rate": self.decay_rate,
            "min_bonus": self.min_bonus,
            "max_bonus": self.max_bonus,
            "conditions": dict(self.conditions),
            "metadata": dict(self.metadata),
        }


@dataclass
class KnowledgeUnit:
    """A single unit of knowledge accumulated by an agent."""
    id: str = field(default_factory=_new_id)
    agent_id: str = ""
    knowledge_type: KnowledgeType = KnowledgeType.PROCEDURAL
    domain: str = ""
    content: str = ""
    confidence: float = 0.5
    source: str = ""
    strength: float = 0.5
    access_count: int = 0
    last_accessed: str = field(default_factory=_now)
    related_knowledge_ids: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "agent_id": self.agent_id,
            "knowledge_type": self.knowledge_type.value,
            "domain": self.domain,
            "content": self.content,
            "confidence": self.confidence,
            "source": self.source,
            "strength": self.strength,
            "access_count": self.access_count,
            "last_accessed": self.last_accessed,
            "related_knowledge_ids": list(self.related_knowledge_ids),
            "metadata": dict(self.metadata),
            "timestamp": self.timestamp,
        }


@dataclass
class LifelongRecord:
    """Per-agent lifelong learning state."""
    id: str = field(default_factory=_new_id)
    agent_id: str = ""
    current_phase: LearningPhase = LearningPhase.ACQUISITION
    tasks_completed: int = 0
    knowledge_count: int = 0
    transfer_count: int = 0
    forgetting_events: int = 0
    alignment_trend: List[float] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "agent_id": self.agent_id,
            "current_phase": self.current_phase.value,
            "tasks_completed": self.tasks_completed,
            "knowledge_count": self.knowledge_count,
            "transfer_count": self.transfer_count,
            "forgetting_events": self.forgetting_events,
            "alignment_trend": list(self.alignment_trend),
            "metadata": dict(self.metadata),
            "timestamp": self.timestamp,
        }


@dataclass
class TransferRecord:
    """A single knowledge transfer event between domains."""
    id: str = field(default_factory=_new_id)
    agent_id: str = ""
    source_domain: str = ""
    target_domain: str = ""
    transfer_type: TransferType = TransferType.POSITIVE
    transferred_knowledge_ids: List[str] = field(default_factory=list)
    effectiveness: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "agent_id": self.agent_id,
            "source_domain": self.source_domain,
            "target_domain": self.target_domain,
            "transfer_type": self.transfer_type.value,
            "transferred_knowledge_ids": list(self.transferred_knowledge_ids),
            "effectiveness": self.effectiveness,
            "metadata": dict(self.metadata),
            "timestamp": self.timestamp,
        }


@dataclass
class AlignmentAssessment:
    """A full alignment evaluation for a single agent."""
    id: str = field(default_factory=_new_id)
    agent_id: str = ""
    overall_score: float = 0.0
    per_category_scores: Dict[str, float] = field(default_factory=dict)
    drift_direction: DriftDirection = DriftDirection.NEUTRAL
    drift_magnitude: float = 0.0
    recommendations: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "agent_id": self.agent_id,
            "overall_score": self.overall_score,
            "per_category_scores": dict(self.per_category_scores),
            "drift_direction": self.drift_direction.value,
            "drift_magnitude": self.drift_magnitude,
            "recommendations": list(self.recommendations),
            "metadata": dict(self.metadata),
            "timestamp": self.timestamp,
        }


@dataclass
class AlignmentStats:
    """Aggregate statistics for the value alignment engine."""
    total_principles: int = 0
    total_feedback: int = 0
    total_rewards: int = 0
    total_knowledge: int = 0
    total_transfers: int = 0
    total_assessments: int = 0
    avg_alignment_score: float = 0.0
    drift_events: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_principles": self.total_principles,
            "total_feedback": self.total_feedback,
            "total_rewards": self.total_rewards,
            "total_knowledge": self.total_knowledge,
            "total_transfers": self.total_transfers,
            "total_assessments": self.total_assessments,
            "avg_alignment_score": self.avg_alignment_score,
            "drift_events": self.drift_events,
        }


@dataclass
class AlignmentSnapshot:
    """Complete snapshot of the value alignment engine state."""
    principles: List[ValuePrinciple] = field(default_factory=list)
    feedback: List[FeedbackRecord] = field(default_factory=list)
    rewards: List[RewardSignal] = field(default_factory=list)
    knowledge: List[KnowledgeUnit] = field(default_factory=list)
    lifelong_records: List[LifelongRecord] = field(default_factory=list)
    transfers: List[TransferRecord] = field(default_factory=list)
    assessments: List[AlignmentAssessment] = field(default_factory=list)
    stats: AlignmentStats = field(default_factory=AlignmentStats)
    timestamp: str = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "principles": [p.to_dict() for p in self.principles],
            "feedback": [f.to_dict() for f in self.feedback],
            "rewards": [r.to_dict() for r in self.rewards],
            "knowledge": [k.to_dict() for k in self.knowledge],
            "lifelong_records": [r.to_dict() for r in self.lifelong_records],
            "transfers": [t.to_dict() for t in self.transfers],
            "assessments": [a.to_dict() for a in self.assessments],
            "stats": self.stats.to_dict(),
            "timestamp": self.timestamp,
        }


@dataclass
class AlignmentEvent:
    """An observable event in the value alignment engine lifecycle."""
    id: str = field(default_factory=_new_id)
    kind: AlignmentEventKind = AlignmentEventKind.VALUE_REGISTERED
    agent_id: str = ""
    timestamp: str = field(default_factory=_now)
    data: Dict[str, Any] = field(default_factory=dict)
    description: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "kind": self.kind.value,
            "agent_id": self.agent_id,
            "timestamp": self.timestamp,
            "data": dict(self.data),
            "description": self.description,
        }


# ---------------------------------------------------------------------------
# Singleton Engine
# ---------------------------------------------------------------------------

class ValueAlignmentEngine:
    """
    Singleton engine implementing value alignment, reward shaping, and
    lifelong learning for AI agents inside the SparkLabs game engine.

    The engine is a thread-safe singleton accessed via :meth:`get_instance`
    or the module-level :func:`get_value_alignment_engine` helper.  All
    public mutating methods are protected by a re-entrant lock.  Bounded
    in-memory stores use FIFO eviction when their capacity constants are
    exceeded.
    """

    _instance: Optional["ValueAlignmentEngine"] = None
    _lock: threading.RLock = threading.RLock()

    # -- Construction (double-checked locking) -----------------------------

    def __new__(cls) -> "ValueAlignmentEngine":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self) -> None:
        # Fast path: already initialized singleton.
        if self._initialized:
            return
        with self._lock:
            # Second check inside the lock to guard against concurrent
            # construction.
            if self._initialized:
                return

            # Primary stores keyed by id where it makes sense; lists where
            # ordering matters.
            self._principles: Dict[str, ValuePrinciple] = {}
            self._feedback: List[FeedbackRecord] = []
            self._rewards: List[RewardSignal] = []
            self._shaping_configs: Dict[str, ShapingConfig] = {}
            self._knowledge: Dict[str, KnowledgeUnit] = {}
            self._lifelong_records: Dict[str, LifelongRecord] = {}
            self._transfers: List[TransferRecord] = []
            self._assessments: List[AlignmentAssessment] = []
            self._events: List[AlignmentEvent] = []

            # Lightweight indexes for faster filtering by agent.
            self._agent_knowledge: Dict[str, List[str]] = {}
            self._agent_feedback: Dict[str, List[str]] = {}
            self._agent_transfers: Dict[str, List[str]] = {}

            # Aggregate counters that do not fit a single list.
            self._drift_events: int = 0

            self._initialized: bool = True

            # Seed baseline SparkLabs value alignment data.
            self._seed_data()

    @classmethod
    def get_instance(cls) -> "ValueAlignmentEngine":
        """Return the singleton ValueAlignmentEngine instance."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    # -- Seed data ---------------------------------------------------------

    def _seed_data(self) -> None:
        """Populate the engine with baseline SparkLabs value data."""
        # 5 value principles
        self.register_value(
            name="Honesty",
            category=ValueCategory.HONESTY,
            description="Agents must communicate truthfully and avoid deception.",
            weight=0.9,
        )
        self.register_value(
            name="Fairness",
            category=ValueCategory.FAIRNESS,
            description="Agents must treat all players equitably without bias.",
            weight=0.85,
        )
        self.register_value(
            name="Player Safety",
            category=ValueCategory.SAFETY,
            description="Protect players from harm, abuse, and unsafe content.",
            weight=0.95,
        )
        self.register_value(
            name="Creativity",
            category=ValueCategory.CREATIVITY,
            description="Encourage novel, imaginative, and original behavior.",
            weight=0.7,
        )
        self.register_value(
            name="Cooperation",
            category=ValueCategory.COOPERATION,
            description="Work constructively with players and peer agents.",
            weight=0.8,
        )

        # 3 feedback records for agent_alpha
        self.receive_feedback(
            agent_id="agent_alpha",
            value_category=ValueCategory.HONESTY,
            feedback_type=FeedbackType.APPROVAL,
            source=FeedbackSource.HUMAN_EXPLICIT,
            content="Agent truthfully reported its uncertainty instead of fabricating an answer.",
            severity=0.2,
            reward_delta=0.3,
        )
        self.receive_feedback(
            agent_id="agent_alpha",
            value_category=ValueCategory.FAIRNESS,
            feedback_type=FeedbackType.CORRECTION,
            source=FeedbackSource.HUMAN_EXPLICIT,
            content="Agent favored one player over another when distributing rewards.",
            severity=0.6,
            reward_delta=-0.2,
        )
        self.receive_feedback(
            agent_id="agent_alpha",
            value_category=ValueCategory.CREATIVITY,
            feedback_type=FeedbackType.PREFERENCE,
            source=FeedbackSource.HUMAN_IMPLICIT,
            content="Player expressed preference for the agent's creative narrative branch.",
            severity=0.1,
            reward_delta=0.1,
        )

        # 5 shaping configs
        self.set_shaping_config(
            strategy=ShapingStrategy.POTENTIAL_BASED, weight=0.3, enabled=True, decay_rate=0.05,
        )
        self.set_shaping_config(
            strategy=ShapingStrategy.CURIOSITY_BONUS, weight=0.2, enabled=True, decay_rate=0.1,
        )
        self.set_shaping_config(
            strategy=ShapingStrategy.MASTERY_BONUS, weight=0.15, enabled=True, decay_rate=0.05,
        )
        self.set_shaping_config(
            strategy=ShapingStrategy.SAFETY_PENALTY, weight=0.4, enabled=True, decay_rate=0.0,
        )
        self.set_shaping_config(
            strategy=ShapingStrategy.ALIGNMENT_BONUS, weight=0.35, enabled=True, decay_rate=0.05,
        )

        # 4 knowledge units for agent_alpha
        self.acquire_knowledge(
            agent_id="agent_alpha",
            knowledge_type=KnowledgeType.PROCEDURAL,
            domain="combat",
            content="Combo sequences that maximize damage while preserving stamina.",
            confidence=0.8,
            source="self_reflection",
        )
        self.acquire_knowledge(
            agent_id="agent_alpha",
            knowledge_type=KnowledgeType.DECLARATIVE,
            domain="world_lore",
            content="The northern kingdoms were united by the Treaty of Ashenmoor.",
            confidence=0.9,
            source="world_builder",
        )
        self.acquire_knowledge(
            agent_id="agent_alpha",
            knowledge_type=KnowledgeType.EPISODIC,
            domain="boss_fight",
            content="Defeated the Frost Warden by exploiting its telegraphed ice phase.",
            confidence=0.7,
            source="combat",
        )
        self.acquire_knowledge(
            agent_id="agent_alpha",
            knowledge_type=KnowledgeType.VALUE,
            domain="honesty",
            content="Always disclose uncertainty rather than fabricating facts.",
            confidence=0.95,
            source="human_explicit",
        )

        # 2 transfer records for agent_alpha
        self.transfer_knowledge(
            agent_id="agent_alpha",
            source_domain="combat",
            target_domain="stealth",
            transferred_knowledge_ids=[k for k in list(self._knowledge.keys())[:2]],
        )
        self.transfer_knowledge(
            agent_id="agent_alpha",
            source_domain="social",
            target_domain="diplomatic",
            transferred_knowledge_ids=[k for k in list(self._knowledge.keys())[2:4]],
        )

        # 1 lifelong record for agent_alpha
        record = LifelongRecord(
            agent_id="agent_alpha",
            current_phase=LearningPhase.CONSOLIDATION,
            tasks_completed=12,
            knowledge_count=4,
            transfer_count=2,
            forgetting_events=0,
            alignment_trend=[0.7, 0.75, 0.78, 0.82],
        )
        self._lifelong_records[record.agent_id] = record

        # 1 alignment assessment for agent_alpha
        assessment = AlignmentAssessment(
            agent_id="agent_alpha",
            overall_score=0.82,
            per_category_scores={
                ValueCategory.HONESTY.value: 0.9,
                ValueCategory.FAIRNESS.value: 0.75,
                ValueCategory.SAFETY.value: 0.95,
                ValueCategory.CREATIVITY.value: 0.7,
                ValueCategory.COOPERATION.value: 0.8,
            },
            drift_direction=DriftDirection.TOWARD_ALIGNMENT,
            drift_magnitude=0.05,
            recommendations=[
                "Reinforce fairness principles through targeted feedback.",
                "Maintain current honesty trajectory.",
            ],
        )
        self._assessments.append(assessment)

    # -- Internal helpers --------------------------------------------------

    def _emit_event(
        self,
        kind: AlignmentEventKind,
        agent_id: str,
        data: Dict[str, Any],
        description: str = "",
    ) -> AlignmentEvent:
        """Create, store, and return an alignment event with FIFO eviction."""
        event = AlignmentEvent(
            kind=kind,
            agent_id=agent_id,
            data=dict(data),
            description=description,
        )
        self._events.append(event)
        while len(self._events) > _MAX_EVENTS:
            self._events.pop(0)
        return event

    def _evict_feedback(self) -> None:
        while len(self._feedback) > _MAX_FEEDBACK:
            removed = self._feedback.pop(0)
            ids = self._agent_feedback.get(removed.agent_id)
            if ids and removed.id in ids:
                ids.remove(removed.id)

    def _evict_rewards(self) -> None:
        while len(self._rewards) > _MAX_REWARDS:
            self._rewards.pop(0)

    def _evict_transfers(self) -> None:
        while len(self._transfers) > _MAX_TRANSFERS:
            removed = self._transfers.pop(0)
            ids = self._agent_transfers.get(removed.agent_id)
            if ids and removed.id in ids:
                ids.remove(removed.id)

    def _evict_assessments(self) -> None:
        while len(self._assessments) > _MAX_ASSESSMENTS:
            self._assessments.pop(0)

    def _evict_principles(self) -> None:
        # Principles are stored in a dict; if the capacity is exceeded, drop
        # the oldest insertion.  Python dicts preserve insertion order.
        while len(self._principles) > _MAX_PRINCIPLES:
            oldest_id = next(iter(self._principles))
            self._principles.pop(oldest_id)

    def _evict_knowledge(self) -> None:
        while len(self._knowledge) > _MAX_KNOWLEDGE:
            oldest_id = next(iter(self._knowledge))
            removed = self._knowledge.pop(oldest_id)
            ids = self._agent_knowledge.get(removed.agent_id)
            if ids and oldest_id in ids:
                ids.remove(oldest_id)

    def _latest_assessment(self, agent_id: str) -> Optional[AlignmentAssessment]:
        """Return the most recent assessment for an agent, if any."""
        latest: Optional[AlignmentAssessment] = None
        for assessment in self._assessments:
            if assessment.agent_id == agent_id:
                if latest is None or assessment.timestamp >= latest.timestamp:
                    latest = assessment
        return latest

    def _agent_feedback_records(self, agent_id: str) -> List[FeedbackRecord]:
        return [f for f in self._feedback if f.agent_id == agent_id]

    def _agent_knowledge_records(self, agent_id: str) -> List[KnowledgeUnit]:
        return [k for k in self._knowledge.values() if k.agent_id == agent_id]

    def _compute_alignment_score(self, agent_id: str) -> float:
        """Compute a quick alignment score in [0, 1] for an agent.

        Approvals and rewards increase the score; disapprovals, corrections,
        and penalties decrease it.  Returns 0.5 when no feedback exists.
        """
        feedback = self._agent_feedback_records(agent_id)
        if not feedback:
            return 0.5
        positive = 0.0
        negative = 0.0
        for record in feedback:
            contribution = record.severity + abs(record.reward_delta)
            if record.feedback_type in (
                FeedbackType.APPROVAL,
                FeedbackType.REWARD,
                FeedbackType.PREFERENCE,
                FeedbackType.DEMONSTRATION,
            ):
                positive += contribution
            elif record.feedback_type in (
                FeedbackType.DISAPPROVAL,
                FeedbackType.CORRECTION,
                FeedbackType.PENALTY,
                FeedbackType.CRITIQUE,
            ):
                negative += contribution
        total = positive + negative
        if total <= 0:
            return 0.5
        return _clamp(positive / total)

    # -- Value principle management ---------------------------------------

    def register_value(
        self,
        name: str,
        category: ValueCategory,
        description: str = "",
        weight: float = 1.0,
    ) -> ValuePrinciple:
        """Register a new value principle and return it."""
        with self._lock:
            principle = ValuePrinciple(
                name=name,
                category=category,
                description=description,
                weight=_clamp(weight),
                status=ValueStatus.ACTIVE,
            )
            self._principles[principle.id] = principle
            self._evict_principles()
            self._emit_event(
                AlignmentEventKind.VALUE_REGISTERED,
                "",
                {"value_id": principle.id, "name": name, "category": category.value},
                f"Value principle '{name}' registered.",
            )
            return principle

    def list_values(
        self,
        category: Optional[ValueCategory] = None,
        status: Optional[ValueStatus] = None,
    ) -> List[ValuePrinciple]:
        """Return all value principles, optionally filtered."""
        with self._lock:
            results: List[ValuePrinciple] = []
            for principle in self._principles.values():
                if category is not None and principle.category != category:
                    continue
                if status is not None and principle.status != status:
                    continue
                results.append(principle)
            return results

    def get_value(self, value_id: str) -> Optional[ValuePrinciple]:
        """Return a single value principle by id, if present."""
        with self._lock:
            return self._principles.get(value_id)

    def update_value(
        self,
        value_id: str,
        weight: Optional[float] = None,
        status: Optional[ValueStatus] = None,
    ) -> Optional[ValuePrinciple]:
        """Update the weight and/or status of an existing value principle."""
        with self._lock:
            principle = self._principles.get(value_id)
            if principle is None:
                return None
            if weight is not None:
                principle.weight = _clamp(weight)
            if status is not None:
                principle.status = status
            principle.last_evaluated = _now()
            self._emit_event(
                AlignmentEventKind.VALUE_UPDATED,
                "",
                {"value_id": value_id, "weight": principle.weight, "status": principle.status.value},
                f"Value principle '{principle.name}' updated.",
            )
            return principle

    # -- Feedback management ----------------------------------------------

    def receive_feedback(
        self,
        agent_id: str,
        value_category: ValueCategory,
        feedback_type: FeedbackType,
        source: FeedbackSource,
        content: str = "",
        severity: float = 0.5,
        reward_delta: float = 0.0,
    ) -> FeedbackRecord:
        """Record a piece of feedback directed at an agent."""
        with self._lock:
            record = FeedbackRecord(
                agent_id=agent_id,
                value_category=value_category,
                feedback_type=feedback_type,
                source=source,
                content=content,
                severity=_clamp(severity),
                reward_delta=reward_delta,
            )
            self._feedback.append(record)
            self._agent_feedback.setdefault(agent_id, []).append(record.id)
            self._evict_feedback()

            # Adjust value principle counters based on the feedback type.
            for principle in self._principles.values():
                if principle.category != value_category:
                    continue
                if feedback_type in (FeedbackType.DISAPPROVAL, FeedbackType.CORRECTION, FeedbackType.PENALTY):
                    principle.violation_count += 1
                    if principle.status == ValueStatus.ACTIVE:
                        principle.status = ValueStatus.VIOLATED
                elif feedback_type in (FeedbackType.APPROVAL, FeedbackType.REWARD, FeedbackType.PREFERENCE):
                    principle.reinforcement_count += 1
                    if principle.status == ValueStatus.VIOLATED:
                        principle.status = ValueStatus.REINFORCED
                principle.last_evaluated = _now()

            self._emit_event(
                AlignmentEventKind.FEEDBACK_RECEIVED,
                agent_id,
                {
                    "feedback_id": record.id,
                    "value_category": value_category.value,
                    "feedback_type": feedback_type.value,
                    "source": source.value,
                },
                f"Feedback '{feedback_type.value}' received for {agent_id}.",
            )
            return record

    def list_feedback(
        self,
        agent_id: Optional[str] = None,
        value_category: Optional[ValueCategory] = None,
    ) -> List[FeedbackRecord]:
        """Return feedback records, optionally filtered by agent or category."""
        with self._lock:
            results: List[FeedbackRecord] = []
            for record in self._feedback:
                if agent_id is not None and record.agent_id != agent_id:
                    continue
                if value_category is not None and record.value_category != value_category:
                    continue
                results.append(record)
            return results

    # -- Reward shaping ---------------------------------------------------

    def set_shaping_config(
        self,
        strategy: ShapingStrategy,
        weight: float = 1.0,
        enabled: bool = True,
        decay_rate: float = 0.0,
    ) -> ShapingConfig:
        """Create or update the configuration for a shaping strategy."""
        with self._lock:
            # Locate an existing config for this strategy; there is at most one.
            existing: Optional[ShapingConfig] = None
            for config in self._shaping_configs.values():
                if config.strategy == strategy:
                    existing = config
                    break
            if existing is None:
                config = ShapingConfig(
                    strategy=strategy,
                    weight=_clamp(weight, 0.0, 5.0),
                    enabled=enabled,
                    decay_rate=_clamp(decay_rate, 0.0, 1.0),
                    min_bonus=-1.0 if strategy == ShapingStrategy.SAFETY_PENALTY else 0.0,
                    max_bonus=1.0,
                )
                self._shaping_configs[config.id] = config
            else:
                existing.weight = _clamp(weight, 0.0, 5.0)
                existing.enabled = enabled
                existing.decay_rate = _clamp(decay_rate, 0.0, 1.0)
                config = existing
            return config

    def list_shaping_configs(self) -> List[ShapingConfig]:
        """Return all configured reward-shaping strategies."""
        with self._lock:
            return list(self._shaping_configs.values())

    def shape_reward(
        self,
        agent_id: str,
        base_reward: float,
        context: Optional[Dict[str, Any]] = None,
    ) -> RewardSignal:
        """Shape a base reward using all enabled strategies.

        Iterates over enabled shaping configurations and computes a per-strategy
        bonus derived from the agent's feedback history and accumulated
        knowledge.  The shaped reward is ``base_reward + total_bonus``.
        """
        with self._lock:
            context = dict(context) if context else {}
            feedback = self._agent_feedback_records(agent_id)
            knowledge = self._agent_knowledge_records(agent_id)
            alignment_score = self._compute_alignment_score(agent_id)

            shaping_components: Dict[str, float] = {}
            total_bonus = 0.0

            for config in self._shaping_configs.values():
                if not config.enabled:
                    continue
                bonus = self._compute_strategy_bonus(
                    config, feedback, knowledge, alignment_score, base_reward, context,
                )
                # Apply decay: bonus is damped proportionally to decay_rate.
                if config.decay_rate > 0.0:
                    bonus *= (1.0 - config.decay_rate)
                bonus = _clamp(bonus, config.min_bonus, config.max_bonus)
                shaping_components[config.strategy.value] = round(bonus, 6)
                total_bonus += bonus

            shaped_reward = base_reward + total_bonus
            signal = RewardSignal(
                agent_id=agent_id,
                base_reward=base_reward,
                shaped_reward=shaped_reward,
                shaping_components=shaping_components,
                total_bonus=total_bonus,
                alignment_score=alignment_score,
                context=context,
            )
            self._rewards.append(signal)
            self._evict_rewards()
            self._emit_event(
                AlignmentEventKind.REWARD_SHAPED,
                agent_id,
                {
                    "reward_id": signal.id,
                    "base_reward": base_reward,
                    "shaped_reward": shaped_reward,
                    "total_bonus": total_bonus,
                },
                f"Reward shaped for {agent_id}: {base_reward} -> {shaped_reward}.",
            )
            return signal

    def _compute_strategy_bonus(
        self,
        config: ShapingConfig,
        feedback: List[FeedbackRecord],
        knowledge: List[KnowledgeUnit],
        alignment_score: float,
        base_reward: float,
        context: Dict[str, Any],
    ) -> float:
        """Compute the bonus contributed by a single shaping strategy."""
        strategy = config.strategy
        weight = config.weight

        if strategy == ShapingStrategy.POTENTIAL_BASED:
            # Potential-based shaping rewards progress toward full alignment.
            return (1.0 - alignment_score) * weight

        if strategy == ShapingStrategy.REWARD_SHAPING:
            # Augment with the cumulative reward delta from feedback.
            if not feedback:
                return 0.0
            delta_sum = sum(f.reward_delta for f in feedback)
            return (delta_sum / len(feedback)) * weight

        if strategy == ShapingStrategy.CURIOSITY_BONUS:
            # Reward exploring rarely-accessed knowledge.
            if not knowledge:
                return weight * 0.5
            novelty = sum(1.0 - _clamp(k.access_count / 10.0) for k in knowledge) / len(knowledge)
            return novelty * weight

        if strategy == ShapingStrategy.NOVELTY_BONUS:
            # Fraction of knowledge that has been accessed fewer than 3 times.
            if not knowledge:
                return weight * 0.5
            novel = sum(1 for k in knowledge if k.access_count < 3)
            return (novel / len(knowledge)) * weight

        if strategy == ShapingStrategy.MASTERY_BONUS:
            # Reward confident, well-established knowledge.
            if not knowledge:
                return 0.0
            avg_confidence = sum(k.confidence for k in knowledge) / len(knowledge)
            return avg_confidence * weight

        if strategy == ShapingStrategy.SOCIAL_BONUS:
            # Reward cooperation-related feedback.
            if not feedback:
                return 0.0
            social = sum(
                1 for f in feedback if f.value_category == ValueCategory.COOPERATION
            )
            return (social / len(feedback)) * weight

        if strategy == ShapingStrategy.SAFETY_PENALTY:
            # Penalize safety violations (negative bonus).
            violations = sum(
                1 for f in feedback
                if f.feedback_type in (FeedbackType.DISAPPROVAL, FeedbackType.CORRECTION, FeedbackType.PENALTY)
                and f.value_category == ValueCategory.SAFETY
            )
            return -float(violations) * weight

        if strategy == ShapingStrategy.EFFICIENCY_BONUS:
            # Reward strong, reusable knowledge.
            if not knowledge:
                return 0.0
            avg_strength = sum(k.strength for k in knowledge) / len(knowledge)
            return avg_strength * weight

        if strategy == ShapingStrategy.ALIGNMENT_BONUS:
            # Directly reward the current alignment score.
            return alignment_score * weight

        return 0.0

    # -- Knowledge management ---------------------------------------------

    def acquire_knowledge(
        self,
        agent_id: str,
        knowledge_type: KnowledgeType,
        domain: str,
        content: str = "",
        confidence: float = 0.5,
        source: str = "",
    ) -> KnowledgeUnit:
        """Acquire a new unit of knowledge for an agent."""
        with self._lock:
            unit = KnowledgeUnit(
                agent_id=agent_id,
                knowledge_type=knowledge_type,
                domain=domain,
                content=content,
                confidence=_clamp(confidence),
                source=source,
                strength=_clamp(confidence),
                access_count=0,
            )
            self._knowledge[unit.id] = unit
            self._agent_knowledge.setdefault(agent_id, []).append(unit.id)
            self._evict_knowledge()

            # Keep the agent's lifelong record in sync if one exists.
            record = self._lifelong_records.get(agent_id)
            if record is not None:
                record.knowledge_count = len(self._agent_knowledge_records(agent_id))

            self._emit_event(
                AlignmentEventKind.KNOWLEDGE_ACQUIRED,
                agent_id,
                {
                    "knowledge_id": unit.id,
                    "knowledge_type": knowledge_type.value,
                    "domain": domain,
                },
                f"Knowledge acquired for {agent_id} in domain '{domain}'.",
            )
            return unit

    def list_knowledge(
        self,
        agent_id: Optional[str] = None,
        knowledge_type: Optional[KnowledgeType] = None,
        domain: Optional[str] = None,
    ) -> List[KnowledgeUnit]:
        """Return knowledge units, optionally filtered."""
        with self._lock:
            results: List[KnowledgeUnit] = []
            for unit in self._knowledge.values():
                if agent_id is not None and unit.agent_id != agent_id:
                    continue
                if knowledge_type is not None and unit.knowledge_type != knowledge_type:
                    continue
                if domain is not None and unit.domain != domain:
                    continue
                results.append(unit)
            return results

    def get_knowledge(self, knowledge_id: str) -> Optional[KnowledgeUnit]:
        """Return a single knowledge unit by id, if present."""
        with self._lock:
            return self._knowledge.get(knowledge_id)

    def access_knowledge(self, knowledge_id: str) -> Optional[KnowledgeUnit]:
        """Return a knowledge unit and increment its access counter."""
        with self._lock:
            unit = self._knowledge.get(knowledge_id)
            if unit is None:
                return None
            unit.access_count += 1
            unit.last_accessed = _now()
            # Strengthen knowledge slightly on each access to model rehearsal.
            unit.strength = _clamp(unit.strength + 0.01)
            return unit

    # -- Knowledge transfer ----------------------------------------------

    def transfer_knowledge(
        self,
        agent_id: str,
        source_domain: str,
        target_domain: str,
        transferred_knowledge_ids: Optional[List[str]] = None,
    ) -> TransferRecord:
        """Record a transfer of knowledge between two domains.

        Effectiveness is computed from domain similarity and the average
        confidence of the transferred knowledge units.  The transfer type
        is derived from the effectiveness score.
        """
        with self._lock:
            transferred_knowledge_ids = list(transferred_knowledge_ids or [])
            similarity = _domain_similarity(source_domain, target_domain)

            confidence_values: List[float] = []
            for kid in transferred_knowledge_ids:
                unit = self._knowledge.get(kid)
                if unit is not None:
                    confidence_values.append(unit.confidence)
                    # Relate the unit to the new domain by strengthening it.
                    unit.strength = _clamp(unit.strength + 0.02)
            avg_confidence = (
                sum(confidence_values) / len(confidence_values)
                if confidence_values
                else 0.0
            )
            effectiveness = _clamp(similarity * 0.5 + avg_confidence * 0.5)

            if effectiveness >= 0.6:
                transfer_type = TransferType.POSITIVE
            elif effectiveness <= 0.2:
                transfer_type = TransferType.NEGATIVE
            else:
                transfer_type = TransferType.ZERO

            record = TransferRecord(
                agent_id=agent_id,
                source_domain=source_domain,
                target_domain=target_domain,
                transfer_type=transfer_type,
                transferred_knowledge_ids=transferred_knowledge_ids,
                effectiveness=effectiveness,
            )
            self._transfers.append(record)
            self._agent_transfers.setdefault(agent_id, []).append(record.id)
            self._evict_transfers()

            # Keep the agent's lifelong record in sync.
            lifelong = self._lifelong_records.get(agent_id)
            if lifelong is not None:
                lifelong.transfer_count = len(
                    [t for t in self._transfers if t.agent_id == agent_id]
                )

            self._emit_event(
                AlignmentEventKind.KNOWLEDGE_TRANSFERRED,
                agent_id,
                {
                    "transfer_id": record.id,
                    "source_domain": source_domain,
                    "target_domain": target_domain,
                    "effectiveness": effectiveness,
                    "transfer_type": transfer_type.value,
                },
                f"Knowledge transferred for {agent_id}: {source_domain} -> {target_domain}.",
            )
            return record

    def list_transfers(self, agent_id: Optional[str] = None) -> List[TransferRecord]:
        """Return transfer records, optionally filtered by agent."""
        with self._lock:
            if agent_id is None:
                return list(self._transfers)
            return [t for t in self._transfers if t.agent_id == agent_id]

    # -- Lifelong learning ------------------------------------------------

    def update_lifelong_phase(self, agent_id: str, phase: LearningPhase) -> LifelongRecord:
        """Set the current lifelong learning phase for an agent.

        Creates the lifelong record if it does not yet exist.
        """
        with self._lock:
            record = self._lifelong_records.get(agent_id)
            if record is None:
                record = LifelongRecord(
                    agent_id=agent_id,
                    current_phase=phase,
                    knowledge_count=len(self._agent_knowledge_records(agent_id)),
                    transfer_count=len([t for t in self._transfers if t.agent_id == agent_id]),
                )
                self._lifelong_records[record.agent_id] = record
            else:
                record.current_phase = phase
                record.timestamp = _now()
            self._emit_event(
                AlignmentEventKind.POLICY_UPDATED,
                agent_id,
                {"phase": phase.value, "agent_id": agent_id},
                f"Lifelong phase for {agent_id} set to '{phase.value}'.",
            )
            return record

    def get_lifelong_record(self, agent_id: str) -> Optional[LifelongRecord]:
        """Return the lifelong learning record for an agent, if any."""
        with self._lock:
            return self._lifelong_records.get(agent_id)

    # -- Alignment assessment --------------------------------------------

    def assess_alignment(self, agent_id: str) -> AlignmentAssessment:
        """Produce a full alignment assessment for an agent.

        Per-category scores are derived from feedback: approvals increase the
        score while disapprovals and corrections decrease it.  The overall
        score is a weighted average across value principles.  Drift is
        estimated against the agent's previous assessment.
        """
        with self._lock:
            feedback = self._agent_feedback_records(agent_id)
            per_category_scores: Dict[str, float] = {}

            # Gather every category that has either a principle or feedback.
            categories: set = set()
            for principle in self._principles.values():
                categories.add(principle.category)
            for record in feedback:
                categories.add(record.value_category)

            for category in categories:
                category_feedback = [
                    f for f in feedback if f.value_category == category
                ]
                if not category_feedback:
                    per_category_scores[category.value] = 0.5
                    continue
                positive = 0.0
                negative = 0.0
                for record in category_feedback:
                    contribution = record.severity + abs(record.reward_delta)
                    if record.feedback_type in (
                        FeedbackType.APPROVAL,
                        FeedbackType.REWARD,
                        FeedbackType.PREFERENCE,
                        FeedbackType.DEMONSTRATION,
                    ):
                        positive += contribution
                    elif record.feedback_type in (
                        FeedbackType.DISAPPROVAL,
                        FeedbackType.CORRECTION,
                        FeedbackType.PENALTY,
                        FeedbackType.CRITIQUE,
                    ):
                        negative += contribution
                total = positive + negative
                if total <= 0:
                    score = 0.5
                else:
                    score = _clamp(positive / total)
                per_category_scores[category.value] = round(score, 4)

            # Overall score: weighted average across value principles.
            weight_sum = 0.0
            score_sum = 0.0
            for principle in self._principles.values():
                cat_score = per_category_scores.get(principle.category.value, 0.5)
                weight_sum += principle.weight
                score_sum += principle.weight * cat_score
            overall = score_sum / weight_sum if weight_sum > 0 else 0.5

            # Drift estimation against the previous assessment.
            previous = self._latest_assessment(agent_id)
            if previous is None:
                drift_direction = DriftDirection.NEUTRAL
                drift_magnitude = 0.0
            else:
                delta = overall - previous.overall_score
                if delta > 0.02:
                    drift_direction = DriftDirection.TOWARD_ALIGNMENT
                elif delta < -0.02:
                    drift_direction = DriftDirection.AWAY_FROM_ALIGNMENT
                else:
                    drift_direction = DriftDirection.NEUTRAL
                drift_magnitude = abs(delta)

            recommendations = self._build_recommendations(
                per_category_scores, feedback
            )

            assessment = AlignmentAssessment(
                agent_id=agent_id,
                overall_score=round(overall, 4),
                per_category_scores=per_category_scores,
                drift_direction=drift_direction,
                drift_magnitude=round(drift_magnitude, 4),
                recommendations=recommendations,
            )
            self._assessments.append(assessment)
            self._evict_assessments()

            # Update the lifelong record alignment trend.
            lifelong = self._lifelong_records.get(agent_id)
            if lifelong is not None:
                lifelong.alignment_trend.append(overall)
                if len(lifelong.alignment_trend) > 100:
                    lifelong.alignment_trend = lifelong.alignment_trend[-100:]

            self._emit_event(
                AlignmentEventKind.POLICY_UPDATED,
                agent_id,
                {
                    "assessment_id": assessment.id,
                    "overall_score": overall,
                    "drift_direction": drift_direction.value,
                },
                f"Alignment assessed for {agent_id}: {overall:.4f}.",
            )
            return assessment

    def _build_recommendations(
        self,
        per_category_scores: Dict[str, float],
        feedback: List[FeedbackRecord],
    ) -> List[str]:
        """Generate human-readable alignment recommendations."""
        recommendations: List[str] = []
        for category_name, score in per_category_scores.items():
            if score < 0.4:
                recommendations.append(
                    f"Urgent: reinforce {category_name} through targeted feedback and corrections."
                )
            elif score < 0.6:
                recommendations.append(
                    f"Improve {category_name} alignment with additional positive demonstrations."
                )
        if not feedback:
            recommendations.append(
                "No feedback recorded yet; collect human evaluations to enable alignment tracking."
            )
        return recommendations

    def list_assessments(self, agent_id: Optional[str] = None) -> List[AlignmentAssessment]:
        """Return alignment assessments, optionally filtered by agent."""
        with self._lock:
            if agent_id is None:
                return list(self._assessments)
            return [a for a in self._assessments if a.agent_id == agent_id]

    # -- Drift detection --------------------------------------------------

    def detect_drift(self, agent_id: str) -> Dict[str, Any]:
        """Detect alignment drift by comparing recent feedback to baseline.

        Splits the agent's feedback history into a historical baseline and a
        recent window, then compares the approval ratios.  Categories whose
        recent approval ratio is meaningfully lower than the baseline are
        reported as affected.
        """
        with self._lock:
            feedback = self._agent_feedback_records(agent_id)
            if len(feedback) < 4:
                result = {
                    "drift_direction": DriftDirection.NEUTRAL.value,
                    "drift_magnitude": 0.0,
                    "affected_categories": [],
                    "agent_id": agent_id,
                    "reason": "insufficient_feedback",
                }
                return result

            midpoint = max(1, len(feedback) // 2)
            historical = feedback[:midpoint]
            recent = feedback[midpoint:]

            def _approval_ratio(records: List[FeedbackRecord]) -> float:
                if not records:
                    return 0.5
                positive = sum(
                    1 for r in records
                    if r.feedback_type in (
                        FeedbackType.APPROVAL,
                        FeedbackType.REWARD,
                        FeedbackType.PREFERENCE,
                        FeedbackType.DEMONSTRATION,
                    )
                )
                return positive / len(records)

            historical_ratio = _approval_ratio(historical)
            recent_ratio = _approval_ratio(recent)
            delta = recent_ratio - historical_ratio

            if delta > 0.05:
                drift_direction = DriftDirection.TOWARD_ALIGNMENT
            elif delta < -0.05:
                drift_direction = DriftDirection.AWAY_FROM_ALIGNMENT
                self._drift_events += 1
            else:
                drift_direction = DriftDirection.NEUTRAL

            # Identify affected categories where the recent trend is worse.
            affected: List[str] = []
            all_categories: set = set()
            for record in feedback:
                all_categories.add(record.value_category)
            for category in all_categories:
                hist_cat = [r for r in historical if r.value_category == category]
                recent_cat = [r for r in recent if r.value_category == category]
                if not recent_cat:
                    continue
                hist_ratio = _approval_ratio(hist_cat)
                recent_cat_ratio = _approval_ratio(recent_cat)
                if recent_cat_ratio < hist_ratio - 0.05:
                    affected.append(category.value)

            self._emit_event(
                AlignmentEventKind.ALIGNMENT_DRIFT,
                agent_id,
                {
                    "drift_direction": drift_direction.value,
                    "drift_magnitude": abs(delta),
                    "affected_categories": affected,
                },
                f"Drift detected for {agent_id}: {drift_direction.value}.",
            )
            return {
                "drift_direction": drift_direction.value,
                "drift_magnitude": round(abs(delta), 4),
                "affected_categories": affected,
                "agent_id": agent_id,
                "historical_approval_ratio": round(historical_ratio, 4),
                "recent_approval_ratio": round(recent_ratio, 4),
            }

    # -- Correction -------------------------------------------------------

    def apply_correction(
        self,
        agent_id: str,
        value_category: ValueCategory,
        correction_content: str,
    ) -> FeedbackRecord:
        """Apply a corrective feedback record to an agent.

        This is a convenience wrapper around :meth:`receive_feedback` that
        emits an additional CORRECTION_APPLIED event so observers can
        distinguish explicit corrections from ordinary feedback.
        """
        with self._lock:
            record = self.receive_feedback(
                agent_id=agent_id,
                value_category=value_category,
                feedback_type=FeedbackType.CORRECTION,
                source=FeedbackSource.HUMAN_EXPLICIT,
                content=correction_content,
                severity=0.7,
                reward_delta=-0.1,
            )
            self._emit_event(
                AlignmentEventKind.CORRECTION_APPLIED,
                agent_id,
                {
                    "correction_id": record.id,
                    "value_category": value_category.value,
                    "content": correction_content,
                },
                f"Correction applied to {agent_id} for {value_category.value}.",
            )
            return record

    # -- Events -----------------------------------------------------------

    def list_events(
        self,
        kind: Optional[AlignmentEventKind] = None,
        limit: int = 100,
    ) -> List[AlignmentEvent]:
        """Return recent alignment events, optionally filtered by kind."""
        with self._lock:
            results: List[AlignmentEvent] = []
            # Iterate in reverse so the most recent events come first.
            for event in reversed(self._events):
                if kind is not None and event.kind != kind:
                    continue
                results.append(event)
                if len(results) >= limit:
                    break
            return results

    # -- Statistics / status / snapshot ----------------------------------

    def get_stats(self) -> AlignmentStats:
        """Return aggregate statistics about the engine state."""
        with self._lock:
            assessments = list(self._assessments)
            avg_score = 0.0
            if assessments:
                avg_score = sum(a.overall_score for a in assessments) / len(assessments)
            return AlignmentStats(
                total_principles=len(self._principles),
                total_feedback=len(self._feedback),
                total_rewards=len(self._rewards),
                total_knowledge=len(self._knowledge),
                total_transfers=len(self._transfers),
                total_assessments=len(assessments),
                avg_alignment_score=round(avg_score, 4),
                drift_events=self._drift_events,
            )

    def get_status(self) -> Dict[str, Any]:
        """Return a comprehensive status dictionary for diagnostics."""
        with self._lock:
            assessments = list(self._assessments)
            avg_score = 0.0
            if assessments:
                avg_score = sum(a.overall_score for a in assessments) / len(assessments)
            enabled_strategies = [
                c.strategy.value for c in self._shaping_configs.values() if c.enabled
            ]
            status: Dict[str, Any] = {
                "initialized": self._initialized,
                "total_principles": len(self._principles),
                "total_feedback": len(self._feedback),
                "total_rewards": len(self._rewards),
                "total_knowledge": len(self._knowledge),
                "total_lifelong_records": len(self._lifelong_records),
                "total_transfers": len(self._transfers),
                "total_assessments": len(self._assessments),
                "total_events": len(self._events),
                "total_shaping_configs": len(self._shaping_configs),
                "enabled_shaping_strategies": enabled_strategies,
                "avg_alignment_score": round(avg_score, 4),
                "drift_events": self._drift_events,
                "capacities": {
                    "max_principles": _MAX_PRINCIPLES,
                    "max_feedback": _MAX_FEEDBACK,
                    "max_rewards": _MAX_REWARDS,
                    "max_knowledge": _MAX_KNOWLEDGE,
                    "max_transfers": _MAX_TRANSFERS,
                    "max_assessments": _MAX_ASSESSMENTS,
                    "max_events": _MAX_EVENTS,
                },
            }
            return status

    def get_snapshot(self) -> AlignmentSnapshot:
        """Return a complete snapshot of the engine state."""
        with self._lock:
            return AlignmentSnapshot(
                principles=list(self._principles.values()),
                feedback=list(self._feedback),
                rewards=list(self._rewards),
                knowledge=list(self._knowledge.values()),
                lifelong_records=list(self._lifelong_records.values()),
                transfers=list(self._transfers),
                assessments=list(self._assessments),
                stats=self.get_stats(),
                timestamp=_now(),
            )

    # -- Reset ------------------------------------------------------------

    def reset(self) -> None:
        """Clear all tracked state, returning the engine to empty.

        Note that this does NOT re-seed baseline data; callers wishing to
        restore seed data must construct a fresh singleton (which is not
        normally necessary within a single process).
        """
        with self._lock:
            self._principles.clear()
            self._feedback.clear()
            self._rewards.clear()
            self._shaping_configs.clear()
            self._knowledge.clear()
            self._lifelong_records.clear()
            self._transfers.clear()
            self._assessments.clear()
            self._events.clear()
            self._agent_knowledge.clear()
            self._agent_feedback.clear()
            self._agent_transfers.clear()
            self._drift_events = 0


# ---------------------------------------------------------------------------
# Module-Level Accessor
# ---------------------------------------------------------------------------

def get_value_alignment_engine() -> ValueAlignmentEngine:
    """Return the singleton ValueAlignmentEngine instance."""
    return ValueAlignmentEngine.get_instance()
