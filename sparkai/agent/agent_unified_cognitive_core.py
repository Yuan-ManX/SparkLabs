"""
SparkLabs Agent - Unified Cognitive Core

A single coherent "mind" for game AI agents that orchestrates multiple
cognitive subsystems into one layered cognition model. The core unifies
BDI (Belief-Desire-Intention) reasoning, HTN (Hierarchical Task Network)
planning, curiosity-driven exploration, self-reflection, meta-reasoning,
emotional affect, and social cognition behind a thread-safe singleton
facade.

Layered cognition model implemented here:

  1. Perception Layer   - sensory input processing, attention filtering,
                          salience detection
  2. Belief Layer        - BDI beliefs about world state, other agents, self
  3. Desire Layer        - goals, motivations, needs, drives arranged on a
                          Maslow-inspired hierarchy
  4. Intention Layer     - committed goals, action plans, commitment mgmt
  5. Planning Layer      - HTN decomposition, means-ends reasoning, repair
  6. Reflection Layer    - self-model, performance evaluation, adaptation
  7. Meta-Reasoning Layer- thinking about thinking, resource allocation
  8. Emotion Layer       - affective state, appraisal, emotional influence
  9. Social Layer        - theory of mind, relationships, coalitions
 10. Action Layer        - action selection, execution monitoring, outcomes

Each registered agent owns an independent CognitiveState holding its
beliefs, desires, intentions, plans, emotional state, meta-cognition and
social relations. The core runs a cognitive cycle through tick() that
advances every registered agent one step along the pipeline.

Thread safety:
  - A class-level _init_lock guards singleton creation with double-checked
    locking.
  - An instance-level _lock (threading.RLock) guards every mutation so the
    core can be driven safely from multiple game threads.
  - A _seeded flag ensures seed data is populated exactly once.

The module exposes get_unified_cognitive_core() as the canonical factory.
"""

from __future__ import annotations

import datetime
import math
import threading
import time
import uuid
from collections import defaultdict, deque
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, Iterable, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class CognitivePhase(Enum):
    """Ordered phases of a single cognitive cycle for one agent."""
    PERCEPTION = "perception"
    BELIEF_UPDATE = "belief_update"
    DESIRE_ACTIVATION = "desire_activation"
    INTENTION_FORMATION = "intention_formation"
    PLANNING = "planning"
    EXECUTION = "execution"
    REFLECTION = "reflection"
    META_REASONING = "meta_reasoning"

    @classmethod
    def ordered(cls) -> List["CognitivePhase"]:
        return [
            cls.PERCEPTION,
            cls.BELIEF_UPDATE,
            cls.DESIRE_ACTIVATION,
            cls.INTENTION_FORMATION,
            cls.PLANNING,
            cls.EXECUTION,
            cls.REFLECTION,
            cls.META_REASONING,
        ]


class BeliefSource(Enum):
    """Origin of a belief held by an agent."""
    PERCEPTION = "perception"
    INFERENCE = "inference"
    COMMUNICATION = "communication"
    MEMORY = "memory"
    DEFAULT = "default"


class DesireCategory(Enum):
    """Maslow-inspired categories for agent desires."""
    SURVIVAL = "survival"
    SAFETY = "safety"
    SOCIAL = "social"
    ESTEEM = "esteem"
    SELF_ACTUALIZATION = "self_actualization"
    AESTHETIC = "aesthetic"
    COGNITIVE = "cognitive"


class IntentionStatus(Enum):
    """Lifecycle state of a committed intention."""
    PENDING = "pending"
    COMMITTED = "committed"
    ACTIVE = "active"
    SUSPENDED = "suspended"
    ABANDONED = "abandoned"
    COMPLETED = "completed"


class PlanStatus(Enum):
    """Lifecycle state of a plan."""
    DRAFT = "draft"
    VALIDATED = "validated"
    EXECUTING = "executing"
    PAUSED = "paused"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    ABORTED = "aborted"


class EmotionType(Enum):
    """Discrete emotion labels following an extended Plutchik set."""
    JOY = "joy"
    FEAR = "fear"
    ANGER = "anger"
    SADNESS = "sadness"
    SURPRISE = "surprise"
    DISGUST = "disgust"
    ANTICIPATION = "anticipation"
    TRUST = "trust"
    CURIOSITY = "curiosity"
    PRIDE = "pride"
    SHAME = "shame"
    ENVY = "envy"
    GRATITUDE = "gratitude"
    CONTEMPT = "contempt"


class MetaStrategy(Enum):
    """High-level strategy governing how deliberative an agent is."""
    REACTIVE = "reactive"
    DELIBERATIVE = "deliberative"
    REFLECTIVE = "reflective"
    LEARNING = "learning"
    CREATIVE = "creative"


class SocialRole(Enum):
    """Role an agent plays relative to another agent."""
    LEADER = "leader"
    FOLLOWER = "follower"
    PEER = "peer"
    RIVAL = "rival"
    MENTOR = "mentor"
    MENTEE = "mentee"
    ALLY = "ally"
    ENEMY = "enemy"
    STRANGER = "stranger"


class ActionType(Enum):
    """Action categories available to an agent."""
    MOVE = "move"
    INTERACT = "interact"
    COMMUNICATE = "communicate"
    OBSERVE = "observe"
    WAIT = "wait"
    CRAFT = "craft"
    ATTACK = "attack"
    DEFEND = "defend"
    FLEE = "flee"
    EXPLORE = "explore"


class CognitiveEventKind(Enum):
    """Kinds of events emitted by the cognitive core."""
    BELIEF_ADDED = "belief_added"
    BELIEF_UPDATED = "belief_updated"
    DESIRE_ACTIVATED = "desire_activated"
    INTENTION_COMMITTED = "intention_committed"
    PLAN_CREATED = "plan_created"
    PLAN_STEP_COMPLETED = "plan_step_completed"
    PLAN_FAILED = "plan_failed"
    EMOTION_CHANGED = "emotion_changed"
    REFLECTION_TRIGGERED = "reflection_triggered"
    META_STRATEGY_CHANGED = "meta_strategy_changed"
    SOCIAL_RELATION_UPDATED = "social_relation_updated"
    DECISION_MADE = "decision_made"
    SYSTEM_RESET = "system_reset"
    AI_PREDICTION = "ai_prediction"
    TICK = "tick"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_CATEGORY_WEIGHTS: Dict[DesireCategory, float] = {
    DesireCategory.SURVIVAL: 1.00,
    DesireCategory.SAFETY: 0.88,
    DesireCategory.SOCIAL: 0.66,
    DesireCategory.ESTEEM: 0.55,
    DesireCategory.SELF_ACTUALIZATION: 0.44,
    DesireCategory.COGNITIVE: 0.40,
    DesireCategory.AESTHETIC: 0.30,
}


def _category_weight(category: DesireCategory) -> float:
    """Return the base priority weight for a desire category."""
    return _CATEGORY_WEIGHTS.get(category, 0.5)


def _now_iso() -> str:
    """Return the current UTC time as an ISO 8601 string."""
    return datetime.datetime.utcnow().isoformat()


def _now_ts() -> float:
    """Return the current time as a POSIX timestamp."""
    return time.time()


def _clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    """Clamp a numeric value to the [low, high] interval."""
    if value < low:
        return low
    if value > high:
        return high
    return value


def _coerce_enum(enum_cls, value, default=None):
    """Coerce a string to an enum member, trying value-based then name-based lookup."""
    if isinstance(value, enum_cls):
        return value
    if isinstance(value, str):
        try:
            return enum_cls(value)
        except ValueError:
            try:
                return enum_cls[value.upper()]
            except KeyError:
                try:
                    return enum_cls[value]
                except KeyError:
                    return default
    return default if default is not None else value


def _round(value: float, digits: int = 4) -> float:
    """Round and avoid floating point noise for storage."""
    return round(float(value), digits)


def _uid(prefix: str = "id") -> str:
    """Generate a short unique identifier with a descriptive prefix."""
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


def _compare(actual: Any, operator: str, expected: Any) -> bool:
    """Compare two values using a string operator."""
    try:
        if operator == "eq":
            return actual == expected
        if operator == "ne":
            return actual != expected
        if operator == "lt":
            return actual < expected
        if operator == "le":
            return actual <= expected
        if operator == "gt":
            return actual > expected
        if operator == "ge":
            return actual >= expected
        if operator == "contains":
            return expected in actual
        return False
    except TypeError:
        return False


def _evaluate_criteria(
    criteria: Optional[Dict[str, Any]], context: Dict[str, Any]
) -> bool:
    """Evaluate a criteria dict against a context mapping.

    A criteria dict maps ``"<key>"`` to a spec dict holding an ``operator``
    and a ``value``. An empty or None criteria block is always satisfied.
    """
    if not criteria:
        return True
    for key, spec in criteria.items():
        if not isinstance(spec, dict):
            return False
        actual = context.get(key)
        operator = spec.get("operator", "eq")
        expected = spec.get("value")
        if not _compare(actual, operator, expected):
            return False
    return True


def _emotion_valence(emotion: EmotionType) -> float:
    """Return the typical valence for a discrete emotion in [-1.0, 1.0]."""
    table = {
        EmotionType.JOY: 0.90,
        EmotionType.TRUST: 0.60,
        EmotionType.ANTICIPATION: 0.30,
        EmotionType.CURIOSITY: 0.40,
        EmotionType.PRIDE: 0.55,
        EmotionType.GRATITUDE: 0.70,
        EmotionType.SURPRISE: 0.10,
        EmotionType.FEAR: -0.70,
        EmotionType.ANGER: -0.80,
        EmotionType.SADNESS: -0.75,
        EmotionType.DISGUST: -0.65,
        EmotionType.SHAME: -0.60,
        EmotionType.ENVY: -0.50,
        EmotionType.CONTEMPT: -0.55,
    }
    return table.get(emotion, 0.0)


def _emotion_arousal(emotion: EmotionType) -> float:
    """Return the typical arousal for a discrete emotion in [0.0, 1.0]."""
    table = {
        EmotionType.JOY: 0.70,
        EmotionType.TRUST: 0.25,
        EmotionType.ANTICIPATION: 0.65,
        EmotionType.CURIOSITY: 0.55,
        EmotionType.PRIDE: 0.55,
        EmotionType.GRATITUDE: 0.35,
        EmotionType.SURPRISE: 0.90,
        EmotionType.FEAR: 0.85,
        EmotionType.ANGER: 0.90,
        EmotionType.SADNESS: 0.20,
        EmotionType.DISGUST: 0.45,
        EmotionType.SHAME: 0.50,
        EmotionType.ENVY: 0.55,
        EmotionType.CONTEMPT: 0.35,
    }
    return table.get(emotion, 0.4)


def _emotion_dominance(emotion: EmotionType) -> float:
    """Return the typical dominance for a discrete emotion in [0.0, 1.0]."""
    table = {
        EmotionType.JOY: 0.65,
        EmotionType.TRUST: 0.55,
        EmotionType.ANTICIPATION: 0.55,
        EmotionType.CURIOSITY: 0.60,
        EmotionType.PRIDE: 0.80,
        EmotionType.GRATITUDE: 0.40,
        EmotionType.SURPRISE: 0.30,
        EmotionType.FEAR: 0.20,
        EmotionType.ANGER: 0.75,
        EmotionType.SADNESS: 0.25,
        EmotionType.DISGUST: 0.60,
        EmotionType.SHAME: 0.20,
        EmotionType.ENVY: 0.35,
        EmotionType.CONTEMPT: 0.70,
    }
    return table.get(emotion, 0.5)


def _meta_strategy_budget(strategy: MetaStrategy) -> float:
    """Return the default deliberation resource budget for a strategy."""
    return {
        MetaStrategy.REACTIVE: 0.25,
        MetaStrategy.DELIBERATIVE: 0.60,
        MetaStrategy.REFLECTIVE: 0.75,
        MetaStrategy.LEARNING: 0.65,
        MetaStrategy.CREATIVE: 0.80,
    }.get(strategy, 0.5)


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class Percept:
    """A single sensory observation registered by an agent."""
    percept_id: str = field(default_factory=lambda: _uid("percept"))
    agent_id: str = ""
    modality: str = "visual"
    content: Dict[str, Any] = field(default_factory=dict)
    salience: float = 0.5
    timestamp: float = field(default_factory=_now_ts)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "percept_id": self.percept_id,
            "agent_id": self.agent_id,
            "modality": self.modality,
            "content": dict(self.content),
            "salience": _round(self.salience),
            "timestamp": self.timestamp,
        }


@dataclass
class Belief:
    """A proposition an agent holds about the world with a confidence."""
    belief_id: str = field(default_factory=lambda: _uid("belief"))
    agent_id: str = ""
    proposition: str = ""
    value: Any = True
    confidence: float = 1.0
    source: BeliefSource = BeliefSource.PERCEPTION
    timestamp: float = field(default_factory=_now_ts)
    decay_rate: float = 0.01
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "belief_id": self.belief_id,
            "agent_id": self.agent_id,
            "proposition": self.proposition,
            "value": self.value,
            "confidence": _round(self.confidence),
            "source": self.source.value,
            "timestamp": self.timestamp,
            "decay_rate": _round(self.decay_rate),
            "metadata": dict(self.metadata),
        }


@dataclass
class Desire:
    """A goal an agent wants to achieve, classified by need category."""
    goal_id: str = field(default_factory=lambda: _uid("goal"))
    agent_id: str = ""
    description: str = ""
    priority: float = 0.5
    category: DesireCategory = DesireCategory.COGNITIVE
    deadline: Optional[float] = None
    satisfaction_criteria: Dict[str, Any] = field(default_factory=dict)
    status: str = "pending"
    created_at: float = field(default_factory=_now_ts)
    activated_at: Optional[float] = None
    satisfied_at: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "goal_id": self.goal_id,
            "agent_id": self.agent_id,
            "description": self.description,
            "priority": _round(self.priority),
            "category": self.category.value,
            "deadline": self.deadline,
            "satisfaction_criteria": dict(self.satisfaction_criteria),
            "status": self.status,
            "created_at": self.created_at,
            "activated_at": self.activated_at,
            "satisfied_at": self.satisfied_at,
            "metadata": dict(self.metadata),
        }


@dataclass
class Intention:
    """A commitment by an agent to pursue a goal through a plan."""
    intention_id: str = field(default_factory=lambda: _uid("intention"))
    agent_id: str = ""
    goal_id: str = ""
    plan_id: Optional[str] = None
    commitment_strength: float = 1.0
    status: IntentionStatus = IntentionStatus.PENDING
    created_at: float = field(default_factory=_now_ts)
    updated_at: float = field(default_factory=_now_ts)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "intention_id": self.intention_id,
            "agent_id": self.agent_id,
            "goal_id": self.goal_id,
            "plan_id": self.plan_id,
            "commitment_strength": _round(self.commitment_strength),
            "status": self.status.value,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "metadata": dict(self.metadata),
        }


@dataclass
class PlanStep:
    """A single step within a plan with preconditions and effects."""
    step_id: str = field(default_factory=lambda: _uid("step"))
    action: str = ""
    preconditions: Dict[str, Any] = field(default_factory=dict)
    effects: Dict[str, Any] = field(default_factory=dict)
    cost: float = 0.5
    duration: float = 1.0
    status: str = "pending"
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "step_id": self.step_id,
            "action": self.action,
            "preconditions": dict(self.preconditions),
            "effects": dict(self.effects),
            "cost": _round(self.cost),
            "duration": _round(self.duration),
            "status": self.status,
            "metadata": dict(self.metadata),
        }


@dataclass
class Plan:
    """A sequence of steps an agent intends to execute for a goal."""
    plan_id: str = field(default_factory=lambda: _uid("plan"))
    agent_id: str = ""
    goal_id: str = ""
    steps: List[PlanStep] = field(default_factory=list)
    current_step: int = 0
    status: PlanStatus = PlanStatus.DRAFT
    expected_outcome: Dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=_now_ts)
    updated_at: float = field(default_factory=_now_ts)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "plan_id": self.plan_id,
            "agent_id": self.agent_id,
            "goal_id": self.goal_id,
            "steps": [s.to_dict() for s in self.steps],
            "current_step": self.current_step,
            "status": self.status.value,
            "expected_outcome": dict(self.expected_outcome),
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "metadata": dict(self.metadata),
        }


@dataclass
class EmotionalState:
    """Affective state described with PAD dimensions and a label."""
    valence: float = 0.0
    arousal: float = 0.3
    dominance: float = 0.5
    primary_emotion: EmotionType = EmotionType.TRUST
    intensity: float = 0.4
    updated_at: float = field(default_factory=_now_ts)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "valence": _round(self.valence),
            "arousal": _round(self.arousal),
            "dominance": _round(self.dominance),
            "primary_emotion": self.primary_emotion.value,
            "intensity": _round(self.intensity),
            "updated_at": self.updated_at,
        }


@dataclass
class MetaCognition:
    """Self-assessment of an agent's deliberation state."""
    confidence_level: float = 0.5
    deliberation_depth: int = 1
    resource_budget: float = 0.5
    strategy: MetaStrategy = MetaStrategy.DELIBERATIVE
    biases_detected: List[str] = field(default_factory=list)
    self_corrections: List[str] = field(default_factory=list)
    updated_at: float = field(default_factory=_now_ts)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "confidence_level": _round(self.confidence_level),
            "deliberation_depth": self.deliberation_depth,
            "resource_budget": _round(self.resource_budget),
            "strategy": self.strategy.value,
            "biases_detected": list(self.biases_detected),
            "self_corrections": list(self.self_corrections),
            "updated_at": self.updated_at,
        }


@dataclass
class SocialRelation:
    """An agent's model of its relationship with another agent."""
    target_id: str = ""
    trust: float = 0.5
    affection: float = 0.5
    power_relation: SocialRole = SocialRole.STRANGER
    history: List[Dict[str, Any]] = field(default_factory=list)
    last_interaction: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "target_id": self.target_id,
            "trust": _round(self.trust),
            "affection": _round(self.affection),
            "power_relation": self.power_relation.value,
            "history": [dict(h) for h in self.history],
            "last_interaction": self.last_interaction,
            "metadata": dict(self.metadata),
        }


@dataclass
class ActionCandidate:
    """A candidate action proposed during action selection."""
    action_id: str = field(default_factory=lambda: _uid("action"))
    action_type: ActionType = ActionType.WAIT
    description: str = ""
    expected_utility: float = 0.5
    cost: float = 0.3
    risk: float = 0.2
    parameters: Dict[str, Any] = field(default_factory=dict)

    @property
    def net_utility(self) -> float:
        """Expected utility discounted by cost and risk."""
        return _clamp(self.expected_utility - 0.5 * self.cost - 0.5 * self.risk)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "action_id": self.action_id,
            "action_type": self.action_type.value,
            "description": self.description,
            "expected_utility": _round(self.expected_utility),
            "cost": _round(self.cost),
            "risk": _round(self.risk),
            "net_utility": _round(self.net_utility),
            "parameters": dict(self.parameters),
        }


@dataclass
class CognitiveState:
    """The full cognitive state for a single agent."""
    agent_id: str = ""
    beliefs: Dict[str, Belief] = field(default_factory=dict)
    desires: Dict[str, Desire] = field(default_factory=dict)
    intentions: Dict[str, Intention] = field(default_factory=dict)
    plans: Dict[str, Plan] = field(default_factory=dict)
    current_plan: Optional[str] = None
    percepts: deque = field(default_factory=lambda: deque(maxlen=200))
    emotional_state: EmotionalState = field(default_factory=EmotionalState)
    meta_state: MetaCognition = field(default_factory=MetaCognition)
    relations: Dict[str, SocialRelation] = field(default_factory=dict)
    self_model: Dict[str, Any] = field(default_factory=dict)
    phase: CognitivePhase = CognitivePhase.PERCEPTION
    last_tick: Optional[float] = None
    tick_count: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "agent_id": self.agent_id,
            "beliefs": {k: v.to_dict() for k, v in self.beliefs.items()},
            "desires": {k: v.to_dict() for k, v in self.desires.items()},
            "intentions": {k: v.to_dict() for k, v in self.intentions.items()},
            "plans": {k: v.to_dict() for k, v in self.plans.items()},
            "current_plan": self.current_plan,
            "percepts": [p.to_dict() for p in self.percepts],
            "emotional_state": self.emotional_state.to_dict(),
            "meta_state": self.meta_state.to_dict(),
            "relations": {k: v.to_dict() for k, v in self.relations.items()},
            "self_model": dict(self.self_model),
            "phase": self.phase.value,
            "last_tick": self.last_tick,
            "tick_count": self.tick_count,
            "metadata": dict(self.metadata),
        }


@dataclass
class CognitiveEvent:
    """An event emitted by the cognitive core for audit and tracing."""
    event_id: str = field(default_factory=lambda: _uid("event"))
    agent_id: str = ""
    kind: CognitiveEventKind = CognitiveEventKind.TICK
    payload: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=_now_ts)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": self.event_id,
            "agent_id": self.agent_id,
            "kind": self.kind.value,
            "payload": dict(self.payload),
            "timestamp": self.timestamp,
        }


@dataclass
class CognitiveStats:
    """Aggregate statistics over the cognitive core's lifetime."""
    decisions_made: int = 0
    plans_executed: int = 0
    reflections_done: int = 0
    goals_achieved: int = 0
    beliefs_added: int = 0
    beliefs_updated: int = 0
    desires_activated: int = 0
    intentions_committed: int = 0
    plans_created: int = 0
    plans_succeeded: int = 0
    plans_failed: int = 0
    emotions_changed: int = 0
    meta_strategy_changes: int = 0
    social_updates: int = 0
    ai_predictions: int = 0
    ticks_processed: int = 0
    last_reset: float = field(default_factory=_now_ts)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "decisions_made": self.decisions_made,
            "plans_executed": self.plans_executed,
            "reflections_done": self.reflections_done,
            "goals_achieved": self.goals_achieved,
            "beliefs_added": self.beliefs_added,
            "beliefs_updated": self.beliefs_updated,
            "desires_activated": self.desires_activated,
            "intentions_committed": self.intentions_committed,
            "plans_created": self.plans_created,
            "plans_succeeded": self.plans_succeeded,
            "plans_failed": self.plans_failed,
            "emotions_changed": self.emotions_changed,
            "meta_strategy_changes": self.meta_strategy_changes,
            "social_updates": self.social_updates,
            "ai_predictions": self.ai_predictions,
            "ticks_processed": self.ticks_processed,
            "last_reset": self.last_reset,
        }


@dataclass
class CognitiveSnapshot:
    """Full serialized snapshot of the cognitive core for persistence."""
    core_id: str = ""
    agent_count: int = 0
    agents: List[Dict[str, Any]] = field(default_factory=list)
    stats: Dict[str, Any] = field(default_factory=dict)
    config: Dict[str, Any] = field(default_factory=dict)
    status: str = "idle"
    timestamp: float = field(default_factory=_now_ts)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "core_id": self.core_id,
            "agent_count": self.agent_count,
            "agents": list(self.agents),
            "stats": dict(self.stats),
            "config": dict(self.config),
            "status": self.status,
            "timestamp": self.timestamp,
        }


# ---------------------------------------------------------------------------
# _UnifiedCognitiveCore - Singleton
# ---------------------------------------------------------------------------

class _UnifiedCognitiveCore:
    """Singleton orchestrator for the full layered cognitive architecture.

    The core maintains one CognitiveState per registered agent and exposes
    methods grouped by cognitive layer: perception, belief, desire,
    intention, planning, reflection, meta-reasoning, emotion, social
    cognition, action selection, system administration, and AI analysis.
    All mutating operations are guarded by an instance-level re-entrant
    lock. Singleton creation uses double-checked locking on a class-level
    lock so the first call from any thread produces exactly one instance.
    """

    _instance: Optional["_UnifiedCognitiveCore"] = None
    _init_lock: threading.RLock = threading.RLock()

    _MAX_EVENTS: int = 10000
    _MAX_EVENTS_PER_AGENT: int = 1000
    _MAX_OUTCOMES: int = 500
    _MAX_REFLECTIONS: int = 200

    def __new__(cls) -> "_UnifiedCognitiveCore":
        if cls._instance is None:
            with cls._init_lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    @classmethod
    def get_instance(cls) -> "_UnifiedCognitiveCore":
        """Get or create the singleton core instance with double-checked locking."""
        if cls._instance is None:
            with cls._init_lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def __init__(self) -> None:
        if getattr(self, "_initialized", False):
            return
        self._lock: threading.RLock = threading.RLock()
        self._core_id: str = _uid("cognitive_core")
        self._states: Dict[str, CognitiveState] = {}
        self._events: deque = deque(maxlen=self._MAX_EVENTS)
        self._events_by_agent: Dict[str, deque] = defaultdict(
            lambda: deque(maxlen=self._MAX_EVENTS_PER_AGENT)
        )
        self._handlers: Dict[
            Optional[CognitiveEventKind], Dict[str, Callable[[CognitiveEvent], None]]
        ] = {}
        self._outcomes: deque = deque(maxlen=self._MAX_OUTCOMES)
        self._reflections: deque = deque(maxlen=self._MAX_REFLECTIONS)
        self._stats: CognitiveStats = CognitiveStats()
        self._config: Dict[str, Any] = {
            "max_beliefs_per_agent": 200,
            "max_desires_per_agent": 50,
            "max_intentions_per_agent": 10,
            "max_plans_per_agent": 20,
            "default_decay_rate": 0.01,
            "salience_threshold": 0.3,
            "reflection_interval": 5,
            "auto_seed": True,
        }
        self._status: str = "idle"
        self._seeded: bool = False
        self._start_time: float = _now_ts()
        self._initialized: bool = True
        if self._config.get("auto_seed", True):
            self._seed_data()

    # ------------------------------------------------------------------
    # Internal helpers (assume lock is held unless noted)
    # ------------------------------------------------------------------

    def _require_state(self, agent_id: str) -> CognitiveState:
        """Return the state for an agent or raise ValueError."""
        state = self._states.get(agent_id)
        if state is None:
            raise ValueError(f"Agent '{agent_id}' is not registered")
        return state

    def _emit_event(
        self,
        agent_id: str,
        kind: CognitiveEventKind,
        payload: Optional[Dict[str, Any]] = None,
    ) -> CognitiveEvent:
        """Record an event and dispatch to registered handlers."""
        event = CognitiveEvent(agent_id=agent_id, kind=kind, payload=payload or {})
        self._events.append(event)
        self._events_by_agent[agent_id].append(event)
        exact = self._handlers.get(kind)
        if exact:
            for handler in list(exact.values()):
                try:
                    handler(event)
                except Exception:
                    pass
        wildcard = self._handlers.get(None)
        if wildcard:
            for handler in list(wildcard.values()):
                try:
                    handler(event)
                except Exception:
                    pass
        return event

    def _belief_context(self, state: CognitiveState) -> Dict[str, Any]:
        """Build a flat context dict from an agent's beliefs for criteria checks."""
        ctx: Dict[str, Any] = {}
        for belief in state.beliefs.values():
            ctx[belief.proposition] = belief.value
        return ctx

    def _active_intentions(self, state: CognitiveState) -> List[Intention]:
        """Return intentions that are not terminal."""
        return [
            i for i in state.intentions.values()
            if i.status in (
                IntentionStatus.PENDING,
                IntentionStatus.COMMITTED,
                IntentionStatus.ACTIVE,
                IntentionStatus.SUSPENDED,
            )
        ]

    def _desire_score(self, desire: Desire) -> float:
        """Compute a composite priority score for a desire."""
        base = desire.priority
        category_bonus = _category_weight(desire.category) * 0.4
        urgency = 0.0
        if desire.deadline is not None:
            remaining = desire.deadline - _now_ts()
            if remaining <= 0:
                urgency = 0.3
            else:
                urgency = _clamp(0.3 * (1.0 / (1.0 + remaining)))
        return _clamp(base + category_bonus + urgency)

    def _pick_primary_emotion(self, valence: float, arousal: float) -> EmotionType:
        """Pick the discrete emotion closest to a PAD triple."""
        best = EmotionType.TRUST
        best_dist = float("inf")
        for emotion in EmotionType:
            ev = _emotion_valence(emotion)
            ea = _emotion_arousal(emotion)
            dist = (ev - valence) ** 2 + (ea - arousal) ** 2
            if dist < best_dist:
                best_dist = dist
                best = emotion
        return best

    def _default_self_model(self, agent_id: str, traits: Dict[str, Any]) -> Dict[str, Any]:
        """Build a baseline self-model for a newly registered agent."""
        return {
            "agent_id": agent_id,
            "competence": traits.get("competence", 0.5),
            "boldness": traits.get("boldness", 0.5),
            "sociability": traits.get("sociability", 0.5),
            "integrity": traits.get("integrity", 0.5),
            "creativity": traits.get("creativity", 0.5),
            "strengths": traits.get("strengths", []),
            "weaknesses": traits.get("weaknesses", []),
            "success_rate": 0.5,
            "total_actions": 0,
            "successful_actions": 0,
        }

    # ------------------------------------------------------------------
    # Perception
    # ------------------------------------------------------------------

    def register_percept(
        self,
        agent_id: str,
        modality: str,
        content: Dict[str, Any],
        salience: float = 0.5,
    ) -> Percept:
        """Register a sensory percept for an agent."""
        with self._lock:
            state = self._require_state(agent_id)
            percept = Percept(
                agent_id=agent_id,
                modality=modality,
                content=dict(content),
                salience=_clamp(salience),
            )
            state.percepts.append(percept)
            return percept

    def get_percepts(
        self, agent_id: str, limit: Optional[int] = None
    ) -> List[Percept]:
        """Return recent percepts for an agent, newest first."""
        with self._lock:
            state = self._require_state(agent_id)
            percepts = list(state.percepts)
            percepts.reverse()
            if limit is not None:
                percepts = percepts[:limit]
            return percepts

    def filter_by_salience(
        self, agent_id: str, threshold: Optional[float] = None
    ) -> List[Percept]:
        """Return percepts whose salience meets the threshold."""
        if threshold is None:
            threshold = self._config.get("salience_threshold", 0.3)
        with self._lock:
            state = self._require_state(agent_id)
            return [p for p in state.percepts if p.salience >= threshold]

    def update_beliefs_from_percepts(
        self, agent_id: str, threshold: Optional[float] = None
    ) -> int:
        """Promote high-salience percepts into beliefs.

        Returns the number of beliefs added or updated.
        """
        if threshold is None:
            threshold = self._config.get("salience_threshold", 0.3)
        with self._lock:
            state = self._require_state(agent_id)
            count = 0
            for percept in state.percepts:
                if percept.salience < threshold:
                    continue
                proposition = f"percept.{percept.modality}.{percept.percept_id[:8]}"
                existing = next(
                    (b for b in state.beliefs.values()
                     if b.proposition == proposition),
                    None,
                )
                if existing is None:
                    belief = Belief(
                        agent_id=agent_id,
                        proposition=proposition,
                        value=percept.content,
                        confidence=_clamp(percept.salience),
                        source=BeliefSource.PERCEPTION,
                        decay_rate=self._config.get("default_decay_rate", 0.01),
                    )
                    state.beliefs[belief.belief_id] = belief
                    self._stats.beliefs_added += 1
                    self._emit_event(
                        agent_id,
                        CognitiveEventKind.BELIEF_ADDED,
                        {"belief_id": belief.belief_id, "proposition": proposition},
                    )
                    count += 1
                else:
                    existing.value = percept.content
                    existing.confidence = _clamp(
                        max(existing.confidence, percept.salience)
                    )
                    existing.timestamp = _now_ts()
                    self._stats.beliefs_updated += 1
                    self._emit_event(
                        agent_id,
                        CognitiveEventKind.BELIEF_UPDATED,
                        {"belief_id": existing.belief_id},
                    )
                    count += 1
            return count

    # ------------------------------------------------------------------
    # Belief management (BDI)
    # ------------------------------------------------------------------

    def add_belief(
        self,
        agent_id: str,
        proposition: str,
        value: Any = True,
        confidence: float = 1.0,
        source: BeliefSource = BeliefSource.PERCEPTION,
        decay_rate: Optional[float] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Belief:
        """Add a new belief to an agent's belief base."""
        source = _coerce_enum(BeliefSource, source, BeliefSource.PERCEPTION)
        with self._lock:
            state = self._require_state(agent_id)
            if decay_rate is None:
                decay_rate = self._config.get("default_decay_rate", 0.01)
            belief = Belief(
                agent_id=agent_id,
                proposition=proposition,
                value=value,
                confidence=_clamp(confidence),
                source=source,
                decay_rate=decay_rate,
                metadata=metadata or {},
            )
            state.beliefs[belief.belief_id] = belief
            self._stats.beliefs_added += 1
            self._emit_event(
                agent_id,
                CognitiveEventKind.BELIEF_ADDED,
                {"belief_id": belief.belief_id, "proposition": proposition},
            )
            return belief

    def get_belief(self, agent_id: str, belief_id: str) -> Optional[Belief]:
        """Return a belief by id, or None if it does not exist."""
        with self._lock:
            state = self._require_state(agent_id)
            return state.beliefs.get(belief_id)

    def list_beliefs(
        self,
        agent_id: str,
        source: Optional[BeliefSource] = None,
        min_confidence: float = 0.0,
    ) -> List[Belief]:
        """List beliefs for an agent, optionally filtered."""
        with self._lock:
            state = self._require_state(agent_id)
            beliefs = list(state.beliefs.values())
            if source is not None:
                beliefs = [b for b in beliefs if b.source == source]
            if min_confidence > 0.0:
                beliefs = [b for b in beliefs if b.confidence >= min_confidence]
            beliefs.sort(key=lambda b: b.confidence, reverse=True)
            return beliefs

    def update_belief(
        self,
        agent_id: str,
        belief_id: str,
        value: Optional[Any] = None,
        confidence: Optional[float] = None,
        source: Optional[BeliefSource] = None,
    ) -> Optional[Belief]:
        """Update fields of an existing belief."""
        with self._lock:
            state = self._require_state(agent_id)
            belief = state.beliefs.get(belief_id)
            if belief is None:
                return None
            if value is not None:
                belief.value = value
            if confidence is not None:
                belief.confidence = _clamp(confidence)
            if source is not None:
                belief.source = source
            belief.timestamp = _now_ts()
            self._stats.beliefs_updated += 1
            self._emit_event(
                agent_id,
                CognitiveEventKind.BELIEF_UPDATED,
                {"belief_id": belief_id},
            )
            return belief

    def remove_belief(self, agent_id: str, belief_id: str) -> bool:
        """Remove a belief from an agent's belief base."""
        with self._lock:
            state = self._require_state(agent_id)
            if belief_id in state.beliefs:
                del state.beliefs[belief_id]
                return True
            return False

    def query_beliefs(
        self,
        agent_id: str,
        predicate: Optional[str] = None,
        pattern: Optional[str] = None,
    ) -> List[Belief]:
        """Query beliefs by substring of proposition or value pattern.

        Args:
            agent_id: The agent to query.
            predicate: Substring matched against the proposition (case-insensitive).
            pattern: Substring matched against the stringified value.
        """
        with self._lock:
            state = self._require_state(agent_id)
            results: List[Belief] = []
            for belief in state.beliefs.values():
                if predicate is not None:
                    if predicate.lower() not in belief.proposition.lower():
                        continue
                if pattern is not None:
                    if pattern.lower() not in str(belief.value).lower():
                        continue
                results.append(belief)
            results.sort(key=lambda b: b.confidence, reverse=True)
            return results

    def reconcile_beliefs(self, agent_id: str) -> int:
        """Resolve conflicting beliefs by keeping the highest-confidence one.

        Two beliefs conflict when they share the same proposition but hold
        different values. Returns the number of beliefs removed.
        """
        with self._lock:
            state = self._require_state(agent_id)
            by_prop: Dict[str, List[Belief]] = defaultdict(list)
            for belief in state.beliefs.values():
                by_prop[belief.proposition].append(belief)
            removed = 0
            for prop, group in by_prop.items():
                if len(group) < 2:
                    continue
                values = {str(b.value) for b in group}
                if len(values) <= 1:
                    continue
                group.sort(key=lambda b: b.confidence, reverse=True)
                keeper = group[0]
                for b in group[1:]:
                    if b.belief_id == keeper.belief_id:
                        continue
                    del state.beliefs[b.belief_id]
                    removed += 1
            return removed

    def decay_beliefs(self, agent_id: str, elapsed: Optional[float] = None) -> int:
        """Reduce belief confidence by decay_rate * elapsed for each belief.

        Beliefs whose confidence drops to zero are removed. The elapsed
        argument is in seconds; if None, uses 1.0 tick unit. Returns the
        number of beliefs removed.
        """
        if elapsed is None:
            elapsed = 1.0
        with self._lock:
            state = self._require_state(agent_id)
            to_remove: List[str] = []
            for belief in state.beliefs.values():
                belief.confidence = _clamp(
                    belief.confidence - belief.decay_rate * elapsed, 0.0, 1.0
                )
                if belief.confidence <= 0.0:
                    to_remove.append(belief.belief_id)
            for bid in to_remove:
                del state.beliefs[bid]
            return len(to_remove)

    # ------------------------------------------------------------------
    # Desire management
    # ------------------------------------------------------------------

    def add_desire(
        self,
        agent_id: str,
        description: str,
        priority: float = 0.5,
        category: DesireCategory = DesireCategory.COGNITIVE,
        deadline: Optional[float] = None,
        satisfaction_criteria: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Desire:
        """Add a new desire to an agent's desire set."""
        category = _coerce_enum(DesireCategory, category, DesireCategory.COGNITIVE)
        with self._lock:
            state = self._require_state(agent_id)
            desire = Desire(
                agent_id=agent_id,
                description=description,
                priority=_clamp(priority),
                category=category,
                deadline=deadline,
                satisfaction_criteria=satisfaction_criteria or {},
                metadata=metadata or {},
            )
            state.desires[desire.goal_id] = desire
            return desire

    def get_desire(self, agent_id: str, goal_id: str) -> Optional[Desire]:
        """Return a desire by id, or None."""
        with self._lock:
            state = self._require_state(agent_id)
            return state.desires.get(goal_id)

    def list_desires(
        self,
        agent_id: str,
        category: Optional[DesireCategory] = None,
        status: Optional[str] = None,
    ) -> List[Desire]:
        """List desires for an agent, optionally filtered."""
        with self._lock:
            state = self._require_state(agent_id)
            desires = list(state.desires.values())
            if category is not None:
                desires = [d for d in desires if d.category == category]
            if status is not None:
                desires = [d for d in desires if d.status == status]
            desires.sort(key=self._desire_score, reverse=True)
            return desires

    def update_desire(
        self,
        agent_id: str,
        goal_id: str,
        priority: Optional[float] = None,
        status: Optional[str] = None,
        deadline: Optional[float] = None,
    ) -> Optional[Desire]:
        """Update fields of an existing desire."""
        with self._lock:
            state = self._require_state(agent_id)
            desire = state.desires.get(goal_id)
            if desire is None:
                return None
            if priority is not None:
                desire.priority = _clamp(priority)
            if status is not None:
                desire.status = status
                if status == "active" and desire.activated_at is None:
                    desire.activated_at = _now_ts()
                    self._stats.desires_activated += 1
                    self._emit_event(
                        agent_id,
                        CognitiveEventKind.DESIRE_ACTIVATED,
                        {"goal_id": goal_id},
                    )
                if status == "satisfied":
                    desire.satisfied_at = _now_ts()
                    self._stats.goals_achieved += 1
            if deadline is not None:
                desire.deadline = deadline
            return desire

    def remove_desire(self, agent_id: str, goal_id: str) -> bool:
        """Remove a desire from an agent's desire set."""
        with self._lock:
            state = self._require_state(agent_id)
            if goal_id in state.desires:
                del state.desires[goal_id]
                return True
            return False

    def activate_desires(self, agent_id: str) -> int:
        """Activate pending desires whose activation context is met.

        Satisfaction criteria are interpreted as activation gates here:
        if a desire has no criteria it activates immediately; otherwise
        its criteria are evaluated against the agent's belief context.
        Returns the number of desires activated.
        """
        with self._lock:
            state = self._require_state(agent_id)
            ctx = self._belief_context(state)
            activated = 0
            for desire in state.desires.values():
                if desire.status != "pending":
                    continue
                if _evaluate_criteria(desire.satisfaction_criteria, ctx):
                    desire.status = "active"
                    desire.activated_at = _now_ts()
                    activated += 1
                    self._stats.desires_activated += 1
                    self._emit_event(
                        agent_id,
                        CognitiveEventKind.DESIRE_ACTIVATED,
                        {"goal_id": desire.goal_id},
                    )
            return activated

    def prioritize_desires(self, agent_id: str) -> List[Desire]:
        """Rank active desires by composite urgency and importance."""
        with self._lock:
            state = self._require_state(agent_id)
            active = [d for d in state.desires.values() if d.status == "active"]
            active.sort(key=self._desire_score, reverse=True)
            return active

    def resolve_conflict(self, agent_id: str) -> Optional[Desire]:
        """Resolve conflicting active desires by selecting the top-ranked one.

        Desires conflict when they compete for the same resource key
        recorded in metadata['resource']. The highest-scoring desire is
        kept active and the others are suspended (status set to
        'suspended').
        """
        with self._lock:
            state = self._require_state(agent_id)
            active = [d for d in state.desires.values() if d.status == "active"]
            resources: Dict[str, List[Desire]] = defaultdict(list)
            for d in active:
                key = d.metadata.get("resource", "__default__")
                resources[key].append(d)
            winner: Optional[Desire] = None
            for group in resources.values():
                if len(group) < 2:
                    continue
                group.sort(key=self._desire_score, reverse=True)
                top = group[0]
                for d in group[1:]:
                    d.status = "suspended"
                if winner is None or self._desire_score(top) > self._desire_score(winner):
                    winner = top
            return winner

    # ------------------------------------------------------------------
    # Intention management
    # ------------------------------------------------------------------

    def commit_intention(
        self,
        agent_id: str,
        goal_id: str,
        plan_id: Optional[str] = None,
        commitment_strength: float = 1.0,
    ) -> Intention:
        """Commit an agent to pursuing a goal via an optional plan."""
        with self._lock:
            state = self._require_state(agent_id)
            desire = state.desires.get(goal_id)
            if desire is None:
                raise ValueError(f"Desire '{goal_id}' does not exist for agent '{agent_id}'")
            intention = Intention(
                agent_id=agent_id,
                goal_id=goal_id,
                plan_id=plan_id,
                commitment_strength=_clamp(commitment_strength),
                status=IntentionStatus.COMMITTED,
            )
            state.intentions[intention.intention_id] = intention
            desire.status = "active"
            if desire.activated_at is None:
                desire.activated_at = _now_ts()
            self._stats.intentions_committed += 1
            self._emit_event(
                agent_id,
                CognitiveEventKind.INTENTION_COMMITTED,
                {"intention_id": intention.intention_id, "goal_id": goal_id},
            )
            return intention

    def get_intention(self, agent_id: str, intention_id: str) -> Optional[Intention]:
        """Return an intention by id, or None."""
        with self._lock:
            state = self._require_state(agent_id)
            return state.intentions.get(intention_id)

    def list_intentions(
        self,
        agent_id: str,
        status: Optional[IntentionStatus] = None,
    ) -> List[Intention]:
        """List intentions for an agent, optionally filtered by status."""
        with self._lock:
            state = self._require_state(agent_id)
            intentions = list(state.intentions.values())
            if status is not None:
                intentions = [i for i in intentions if i.status == status]
            intentions.sort(key=lambda i: i.commitment_strength, reverse=True)
            return intentions

    def suspend_intention(self, agent_id: str, intention_id: str) -> Optional[Intention]:
        """Suspend an active or committed intention."""
        with self._lock:
            state = self._require_state(agent_id)
            intention = state.intentions.get(intention_id)
            if intention is None:
                return None
            if intention.status in (IntentionStatus.ACTIVE, IntentionStatus.COMMITTED):
                intention.status = IntentionStatus.SUSPENDED
                intention.updated_at = _now_ts()
            return intention

    def resume_intention(self, agent_id: str, intention_id: str) -> Optional[Intention]:
        """Resume a suspended intention."""
        with self._lock:
            state = self._require_state(agent_id)
            intention = state.intentions.get(intention_id)
            if intention is None:
                return None
            if intention.status == IntentionStatus.SUSPENDED:
                intention.status = IntentionStatus.ACTIVE
                intention.updated_at = _now_ts()
            return intention

    def abandon_intention(self, agent_id: str, intention_id: str) -> Optional[Intention]:
        """Abandon an intention, marking it as abandoned."""
        with self._lock:
            state = self._require_state(agent_id)
            intention = state.intentions.get(intention_id)
            if intention is None:
                return None
            intention.status = IntentionStatus.ABANDONED
            intention.updated_at = _now_ts()
            return intention

    def check_commitment(self, agent_id: str, intention_id: str) -> str:
        """Evaluate whether an intention should be maintained.

        Returns one of 'maintain', 'suspend', or 'abandon'. The decision is
        based on commitment strength, belief confidence in goal feasibility,
        and the emotional state of the agent.
        """
        with self._lock:
            state = self._require_state(agent_id)
            intention = state.intentions.get(intention_id)
            if intention is None:
                return "abandon"
            desire = state.desires.get(intention.goal_id)
            if desire is None:
                return "abandon"
            score = intention.commitment_strength
            score += 0.2 * state.emotional_state.dominance
            score -= 0.2 * state.emotional_state.intensity if state.emotional_state.valence < 0 else 0.0
            if desire.deadline is not None and desire.deadline < _now_ts():
                score -= 0.3
            if score < 0.2:
                return "abandon"
            if score < 0.5:
                return "suspend"
            return "maintain"

    # ------------------------------------------------------------------
    # Planning (HTN)
    # ------------------------------------------------------------------

    def create_plan(
        self,
        agent_id: str,
        goal_id: str,
        steps: Optional[List[Dict[str, Any]]] = None,
        expected_outcome: Optional[Dict[str, Any]] = None,
    ) -> Plan:
        """Create a new plan for a goal from a list of step dicts."""
        if not isinstance(expected_outcome, dict):
            expected_outcome = {}
        with self._lock:
            state = self._require_state(agent_id)
            plan = Plan(
                agent_id=agent_id,
                goal_id=goal_id,
                expected_outcome=expected_outcome or {},
            )
            for step_dict in steps or []:
                step = PlanStep(
                    action=step_dict.get("action", "wait"),
                    preconditions=dict(step_dict.get("preconditions", {})),
                    effects=dict(step_dict.get("effects", {})),
                    cost=float(step_dict.get("cost", 0.5)),
                    duration=float(step_dict.get("duration", 1.0)),
                    status=step_dict.get("status", "pending"),
                    metadata=dict(step_dict.get("metadata", {})),
                )
                plan.steps.append(step)
            state.plans[plan.plan_id] = plan
            self._stats.plans_created += 1
            self._emit_event(
                agent_id,
                CognitiveEventKind.PLAN_CREATED,
                {"plan_id": plan.plan_id, "goal_id": goal_id},
            )
            return plan

    def get_plan(self, agent_id: str, plan_id: str) -> Optional[Plan]:
        """Return a plan by id, or None."""
        with self._lock:
            state = self._require_state(agent_id)
            return state.plans.get(plan_id)

    def list_plans(
        self,
        agent_id: str,
        status: Optional[PlanStatus] = None,
    ) -> List[Plan]:
        """List plans for an agent, optionally filtered by status."""
        with self._lock:
            state = self._require_state(agent_id)
            plans = list(state.plans.values())
            if status is not None:
                plans = [p for p in plans if p.status == status]
            plans.sort(key=lambda p: p.created_at, reverse=True)
            return plans

    def update_plan(
        self,
        agent_id: str,
        plan_id: str,
        status: Optional[PlanStatus] = None,
        current_step: Optional[int] = None,
    ) -> Optional[Plan]:
        """Update fields of an existing plan."""
        if status is not None:
            status = _coerce_enum(PlanStatus, status, None)
        with self._lock:
            state = self._require_state(agent_id)
            plan = state.plans.get(plan_id)
            if plan is None:
                return None
            if status is not None:
                plan.status = status
            if current_step is not None:
                plan.current_step = max(0, min(current_step, len(plan.steps)))
            plan.updated_at = _now_ts()
            return plan

    def remove_plan(self, agent_id: str, plan_id: str) -> bool:
        """Remove a plan from an agent's plan set."""
        with self._lock:
            state = self._require_state(agent_id)
            if plan_id in state.plans:
                del state.plans[plan_id]
                if state.current_plan == plan_id:
                    state.current_plan = None
                return True
            return False

    def decompose_task(
        self,
        agent_id: str,
        task: str,
        depth: int = 2,
    ) -> List[PlanStep]:
        """Decompose a high-level task into subtasks (HTN decomposition).

        Uses a simple recursive decomposition table keyed by task name.
        Unknown tasks produce a generic observe-then-act sequence.
        """
        with self._lock:
            self._require_state(agent_id)
            return self._decompose_locked(agent_id, task, depth, set())

    def _decompose_locked(
        self,
        agent_id: str,
        task: str,
        depth: int,
        seen: set,
    ) -> List[PlanStep]:
        """Recursive helper for task decomposition (lock held)."""
        if depth <= 0 or task in seen:
            return [PlanStep(action=task, cost=0.5, duration=1.0)]
        seen = seen | {task}
        table: Dict[str, List[Any]] = {
            "defeat_enemy": [
                ("observe", {"target": "enemy"}, {"enemy_located": True}, 0.3, 1.0),
                ("attack", {"target": "enemy"}, {"enemy_defeated": True}, 0.7, 2.0),
                ("defend", {}, {"self_safe": True}, 0.4, 1.0),
            ],
            "gather_resources": [
                ("explore", {}, {"resource_located": True}, 0.4, 2.0),
                ("move", {"destination": "resource"}, {"at_resource": True}, 0.3, 1.0),
                ("craft", {"item": "tool"}, {"tool_acquired": True}, 0.5, 2.0),
            ],
            "befriend_npc": [
                ("observe", {"target": "npc"}, {"npc_located": True}, 0.3, 1.0),
                ("communicate", {"intent": "greet"}, {"rapport_started": True}, 0.4, 1.0),
                ("communicate", {"intent": "help"}, {"trust_gained": True}, 0.6, 2.0),
            ],
            "explore_region": [
                ("observe", {}, {"landmarks_mapped": True}, 0.4, 2.0),
                ("move", {"destination": "frontier"}, {"frontier_reached": True}, 0.5, 2.0),
                ("explore", {}, {"region_charted": True}, 0.6, 3.0),
            ],
            "escape_danger": [
                ("observe", {"target": "threat"}, {"threat_located": True}, 0.2, 0.5),
                ("flee", {"destination": "safe_zone"}, {"at_safe_zone": True}, 0.6, 1.0),
                ("defend", {}, {"self_safe": True}, 0.4, 1.0),
            ],
        }
        entry = table.get(task)
        if entry is None:
            return [PlanStep(action=task, cost=0.5, duration=1.0)]
        steps: List[PlanStep] = []
        for action, pre, eff, cost, duration in entry:
            sub = self._decompose_locked(agent_id, action, depth - 1, seen)
            if sub and sub[0].action == action:
                steps.append(PlanStep(
                    action=action,
                    preconditions=dict(pre),
                    effects=dict(eff),
                    cost=cost,
                    duration=duration,
                ))
            else:
                steps.extend(sub)
        return steps

    def validate_plan(self, agent_id: str, plan_id: str) -> Tuple[bool, str]:
        """Check preconditions and feasibility of a plan.

        Returns a (valid, reason) tuple.
        """
        with self._lock:
            state = self._require_state(agent_id)
            plan = state.plans.get(plan_id)
            if plan is None:
                return False, "plan not found"
            if not plan.steps:
                return False, "plan has no steps"
            ctx = self._belief_context(state)
            for index, step in enumerate(plan.steps):
                if not _evaluate_criteria(step.preconditions, ctx):
                    return False, f"step {index} '{step.action}' preconditions unmet"
                if step.cost < 0 or step.duration < 0:
                    return False, f"step {index} has negative cost or duration"
            return True, "valid"

    def execute_plan_step(self, agent_id: str, plan_id: str) -> Optional[PlanStep]:
        """Execute the next step of a plan and advance the pointer.

        Returns the executed step, or None if the plan is finished or invalid.
        """
        with self._lock:
            state = self._require_state(agent_id)
            plan = state.plans.get(plan_id)
            if plan is None:
                return None
            if plan.status not in (PlanStatus.VALIDATED, PlanStatus.EXECUTING):
                valid, _ = self.validate_plan(agent_id, plan_id)
                if not valid:
                    plan.status = PlanStatus.FAILED
                    self._stats.plans_failed += 1
                    self._emit_event(
                        agent_id,
                        CognitiveEventKind.PLAN_FAILED,
                        {"plan_id": plan_id},
                    )
                    return None
                plan.status = PlanStatus.EXECUTING
            if plan.current_step >= len(plan.steps):
                plan.status = PlanStatus.SUCCEEDED
                self._stats.plans_succeeded += 1
                self._stats.plans_executed += 1
                return None
            step = plan.steps[plan.current_step]
            step.status = "completed"
            plan.current_step += 1
            plan.updated_at = _now_ts()
            self._emit_event(
                agent_id,
                CognitiveEventKind.PLAN_STEP_COMPLETED,
                {"plan_id": plan_id, "step_id": step.step_id, "action": step.action},
            )
            if plan.current_step >= len(plan.steps):
                plan.status = PlanStatus.SUCCEEDED
                self._stats.plans_succeeded += 1
                self._stats.plans_executed += 1
                desire = state.desires.get(plan.goal_id)
                if desire is not None:
                    desire.status = "satisfied"
                    desire.satisfied_at = _now_ts()
                    self._stats.goals_achieved += 1
            return step

    def repair_plan(self, agent_id: str, plan_id: str) -> Optional[Plan]:
        """Repair a failed plan by re-decomposing remaining work.

        Replaces steps from the current pointer onward with a fresh
        decomposition of the goal's description. Returns the repaired plan
        or None if it cannot be repaired.
        """
        with self._lock:
            state = self._require_state(agent_id)
            plan = state.plans.get(plan_id)
            if plan is None:
                return None
            desire = state.desires.get(plan.goal_id)
            if desire is None:
                return None
            kept = plan.steps[:plan.current_step]
            replacement = self._decompose_locked(
                agent_id, desire.description.split()[0] if desire.description else "wait", 2, set()
            )
            plan.steps = kept + replacement
            plan.status = PlanStatus.VALIDATED
            plan.updated_at = _now_ts()
            return plan

    def estimate_plan_cost(
        self, agent_id: str, plan_id: str
    ) -> Tuple[float, float]:
        """Compute expected total cost and duration of a plan."""
        with self._lock:
            state = self._require_state(agent_id)
            plan = state.plans.get(plan_id)
            if plan is None:
                return 0.0, 0.0
            total_cost = sum(s.cost for s in plan.steps)
            total_duration = sum(s.duration for s in plan.steps)
            return _round(total_cost), _round(total_duration)

    # ------------------------------------------------------------------
    # Reflection
    # ------------------------------------------------------------------

    def trigger_reflection(
        self,
        agent_id: str,
        topic: str = "general",
    ) -> Dict[str, Any]:
        """Initiate a self-reflection cycle for an agent.

        Returns a reflection report dict containing observations about the
        agent's current beliefs, desires, intentions and emotional state.
        """
        with self._lock:
            state = self._require_state(agent_id)
            report: Dict[str, Any] = {
                "agent_id": agent_id,
                "topic": topic,
                "timestamp": _now_ts(),
                "belief_count": len(state.beliefs),
                "desire_count": len(state.desires),
                "intention_count": len(state.intentions),
                "plan_count": len(state.plans),
                "primary_emotion": state.emotional_state.primary_emotion.value,
                "confidence": state.meta_state.confidence_level,
                "observations": [],
                "corrections": [],
            }
            observations: List[str] = report["observations"]
            if len(state.beliefs) < 3:
                observations.append("Belief base is sparse; consider gathering more information.")
            low_conf = [b for b in state.beliefs.values() if b.confidence < 0.3]
            if low_conf:
                observations.append(
                    f"{len(low_conf)} beliefs have low confidence and may need verification."
                )
            if not state.intentions:
                observations.append("No active intentions; agent may be drifting without purpose.")
            active_desires = [d for d in state.desires.values() if d.status == "active"]
            if len(active_desires) > 5:
                observations.append("Many active desires competing for attention; consider prioritization.")
            if state.emotional_state.valence < -0.3:
                observations.append("Negative affect detected; coping strategies may be needed.")
            for plan in state.plans.values():
                if plan.status == PlanStatus.FAILED:
                    observations.append(f"Plan {plan.plan_id} failed and may need repair.")
            corrections: List[str] = report["corrections"]
            if state.meta_state.confidence_level < 0.3:
                corrections.append("Lower deliberation confidence; gather more evidence before committing.")
            if state.meta_state.strategy == MetaStrategy.REACTIVE and len(active_desires) > 3:
                corrections.append("Switch from reactive to deliberative strategy for complex goal set.")
            state.meta_state.self_corrections = list(corrections)
            self._stats.reflections_done += 1
            self._reflections.append(report)
            self._emit_event(
                agent_id,
                CognitiveEventKind.REFLECTION_TRIGGERED,
                {"topic": topic},
            )
            return report

    def evaluate_performance(self, agent_id: str) -> Dict[str, Any]:
        """Assess recent performance based on recorded outcomes.

        Returns a dict with success rate, action count, and trend.
        """
        with self._lock:
            state = self._require_state(agent_id)
            recent = [o for o in self._outcomes if o.get("agent_id") == agent_id][-50:]
            total = len(recent)
            successes = sum(1 for o in recent if o.get("success"))
            success_rate = successes / total if total else 0.0
            plan_total = len(state.plans)
            plan_successes = sum(
                1 for p in state.plans.values() if p.status == PlanStatus.SUCCEEDED
            )
            plan_rate = plan_successes / plan_total if plan_total else 0.0
            trend = "stable"
            if total >= 6:
                first_half = recent[: total // 2]
                second_half = recent[total // 2:]
                first_rate = sum(1 for o in first_half if o.get("success")) / len(first_half)
                second_rate = sum(1 for o in second_half if o.get("success")) / len(second_half)
                if second_rate > first_rate + 0.1:
                    trend = "improving"
                elif second_rate < first_rate - 0.1:
                    trend = "declining"
            return {
                "agent_id": agent_id,
                "total_actions": total,
                "successes": successes,
                "success_rate": _round(success_rate),
                "plan_total": plan_total,
                "plan_successes": plan_successes,
                "plan_success_rate": _round(plan_rate),
                "trend": trend,
                "timestamp": _now_ts(),
            }

    def update_self_model(
        self,
        agent_id: str,
        updates: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Revise the self-model based on provided updates and recent outcomes."""
        with self._lock:
            state = self._require_state(agent_id)
            model = state.self_model
            if updates:
                for key, value in updates.items():
                    model[key] = value
            perf = self.evaluate_performance(agent_id)
            model["success_rate"] = perf["success_rate"]
            model["total_actions"] = perf["total_actions"]
            model["successful_actions"] = perf["successes"]
            model["last_updated"] = _now_ts()
            return dict(model)

    def learn_from_outcome(
        self,
        agent_id: str,
        outcome: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Extract lessons from a success or failure outcome.

        Returns a lesson dict with inferred cause and recommended adjustment.
        """
        with self._lock:
            state = self._require_state(agent_id)
            success = bool(outcome.get("success", False))
            action = outcome.get("action", "unknown")
            lesson: Dict[str, Any] = {
                "agent_id": agent_id,
                "action": action,
                "success": success,
                "timestamp": _now_ts(),
                "cause": "",
                "adjustment": "",
            }
            if success:
                lesson["cause"] = "effective execution and accurate beliefs"
                lesson["adjustment"] = "reinforce similar action selection"
                state.meta_state.confidence_level = _clamp(
                    state.meta_state.confidence_level + 0.05
                )
            else:
                lesson["cause"] = outcome.get("reason", "unmet preconditions or low confidence")
                lesson["adjustment"] = "gather more evidence and repair plan before retry"
                state.meta_state.confidence_level = _clamp(
                    state.meta_state.confidence_level - 0.05
                )
                state.meta_state.self_corrections.append(lesson["adjustment"])
            return lesson

    def get_reflections(
        self, agent_id: str, limit: int = 20
    ) -> List[Dict[str, Any]]:
        """Return past reflection reports for an agent, newest first."""
        with self._lock:
            reports = [
                r for r in self._reflections
                if r.get("agent_id") == agent_id
            ]
            reports.reverse()
            return reports[:limit]

    def get_outcomes(
        self, agent_id: str, limit: int = 20
    ) -> List[Dict[str, Any]]:
        """Return past action outcome records for an agent, newest first."""
        with self._lock:
            records = [
                o for o in self._outcomes
                if o.get("agent_id") == agent_id
            ]
            records.reverse()
            return records[:limit]

    def get_self_model(self, agent_id: str) -> Dict[str, Any]:
        """Return the current self-model for an agent."""
        with self._lock:
            state = self._require_state(agent_id)
            return dict(state.self_model)

    # ------------------------------------------------------------------
    # Meta-reasoning
    # ------------------------------------------------------------------

    def set_meta_strategy(
        self,
        agent_id: str,
        strategy: MetaStrategy,
    ) -> MetaCognition:
        """Switch the meta-reasoning strategy for an agent."""
        strategy = _coerce_enum(MetaStrategy, strategy, MetaStrategy.DELIBERATIVE)
        with self._lock:
            state = self._require_state(agent_id)
            state.meta_state.strategy = strategy
            state.meta_state.resource_budget = _meta_strategy_budget(strategy)
            state.meta_state.deliberation_depth = {
                MetaStrategy.REACTIVE: 0,
                MetaStrategy.DELIBERATIVE: 2,
                MetaStrategy.REFLECTIVE: 3,
                MetaStrategy.LEARNING: 2,
                MetaStrategy.CREATIVE: 4,
            }.get(strategy, 1)
            state.meta_state.updated_at = _now_ts()
            self._stats.meta_strategy_changes += 1
            self._emit_event(
                agent_id,
                CognitiveEventKind.META_STRATEGY_CHANGED,
                {"strategy": strategy.value},
            )
            return state.meta_state

    def allocate_resources(
        self,
        agent_id: str,
        budget: Optional[float] = None,
    ) -> Dict[str, float]:
        """Distribute cognitive resource budget across cognitive phases.

        Returns a dict mapping phase name to allocated fraction.
        """
        with self._lock:
            state = self._require_state(agent_id)
            if budget is None:
                budget = state.meta_state.resource_budget
            else:
                state.meta_state.resource_budget = _clamp(budget)
            strategy = state.meta_state.strategy
            if strategy == MetaStrategy.REACTIVE:
                weights = {
                    "perception": 0.40,
                    "belief_update": 0.20,
                    "execution": 0.30,
                    "planning": 0.05,
                    "reflection": 0.05,
                }
            elif strategy == MetaStrategy.REFLECTIVE:
                weights = {
                    "perception": 0.15,
                    "belief_update": 0.15,
                    "planning": 0.20,
                    "reflection": 0.35,
                    "meta_reasoning": 0.15,
                }
            elif strategy == MetaStrategy.LEARNING:
                weights = {
                    "perception": 0.20,
                    "belief_update": 0.20,
                    "planning": 0.20,
                    "reflection": 0.25,
                    "execution": 0.15,
                }
            elif strategy == MetaStrategy.CREATIVE:
                weights = {
                    "perception": 0.15,
                    "belief_update": 0.15,
                    "planning": 0.25,
                    "reflection": 0.20,
                    "meta_reasoning": 0.25,
                }
            else:
                weights = {
                    "perception": 0.20,
                    "belief_update": 0.20,
                    "desire_activation": 0.10,
                    "planning": 0.25,
                    "execution": 0.20,
                    "reflection": 0.05,
                }
            allocation = {k: _round(v * budget) for k, v in weights.items()}
            return allocation

    def assess_confidence(self, agent_id: str) -> float:
        """Evaluate overall confidence in current beliefs and plans."""
        with self._lock:
            state = self._require_state(agent_id)
            if not state.beliefs:
                return 0.2
            avg_belief_conf = sum(b.confidence for b in state.beliefs.values()) / len(state.beliefs)
            plan_conf = 0.5
            active_plans = [p for p in state.plans.values() if p.status in (PlanStatus.EXECUTING, PlanStatus.VALIDATED)]
            if active_plans:
                valid_count = 0
                for plan in active_plans:
                    valid, _ = self.validate_plan(agent_id, plan.plan_id)
                    if valid:
                        valid_count += 1
                plan_conf = valid_count / len(active_plans)
            confidence = 0.6 * avg_belief_conf + 0.4 * plan_conf
            state.meta_state.confidence_level = _clamp(confidence)
            state.meta_state.updated_at = _now_ts()
            return _round(confidence)

    def decide_deliberation_depth(
        self,
        agent_id: str,
        problem_complexity: float = 0.5,
    ) -> int:
        """Decide how deeply to deliberate on a problem.

        Combines problem complexity with available resource budget to
        produce a depth count in [0, 5].
        """
        with self._lock:
            state = self._require_state(agent_id)
            budget = state.meta_state.resource_budget
            strategy = state.meta_state.strategy
            base = {
                MetaStrategy.REACTIVE: 0,
                MetaStrategy.DELIBERATIVE: 2,
                MetaStrategy.REFLECTIVE: 3,
                MetaStrategy.LEARNING: 2,
                MetaStrategy.CREATIVE: 4,
            }.get(strategy, 1)
            complexity_factor = int(_clamp(problem_complexity) * 2)
            depth = min(5, base + complexity_factor)
            depth = max(0, int(depth * budget * 2))
            state.meta_state.deliberation_depth = depth
            state.meta_state.updated_at = _now_ts()
            return depth

    # ------------------------------------------------------------------
    # Emotion
    # ------------------------------------------------------------------

    def set_emotional_state(
        self,
        agent_id: str,
        valence: float,
        arousal: float,
        dominance: float,
        primary_emotion: Optional[EmotionType] = None,
        intensity: Optional[float] = None,
    ) -> EmotionalState:
        """Set the emotional state of an agent directly."""
        if primary_emotion is not None:
            primary_emotion = _coerce_enum(EmotionType, primary_emotion, None)
        with self._lock:
            state = self._require_state(agent_id)
            valence = _clamp(valence, -1.0, 1.0)
            arousal = _clamp(arousal)
            dominance = _clamp(dominance)
            if primary_emotion is None:
                primary_emotion = self._pick_primary_emotion(valence, arousal)
            if intensity is None:
                intensity = _clamp(abs(arousal) + abs(valence) * 0.5)
            state.emotional_state = EmotionalState(
                valence=valence,
                arousal=arousal,
                dominance=dominance,
                primary_emotion=primary_emotion,
                intensity=intensity,
                updated_at=_now_ts(),
            )
            self._stats.emotions_changed += 1
            self._emit_event(
                agent_id,
                CognitiveEventKind.EMOTION_CHANGED,
                {"primary_emotion": primary_emotion.value, "valence": valence},
            )
            return state.emotional_state

    def get_emotional_state(self, agent_id: str) -> EmotionalState:
        """Return the current emotional state of an agent."""
        with self._lock:
            state = self._require_state(agent_id)
            return state.emotional_state

    def update_emotion(
        self,
        agent_id: str,
        valence_delta: float = 0.0,
        arousal_delta: float = 0.0,
        dominance_delta: float = 0.0,
    ) -> EmotionalState:
        """Adjust the emotional state by deltas and re-derive the label."""
        with self._lock:
            state = self._require_state(agent_id)
            current = state.emotional_state
            return self.set_emotional_state(
                agent_id,
                valence=current.valence + valence_delta,
                arousal=current.arousal + arousal_delta,
                dominance=current.dominance + dominance_delta,
            )

    def appraise_event(
        self,
        agent_id: str,
        event: Dict[str, Any],
    ) -> EmotionalState:
        """Perform an emotional appraisal of an event.

        The event dict may contain 'desirability' in [-1,1], 'urgency' in
        [0,1], 'control' in [0,1], and 'novelty' in [0,1]. These map onto
        valence, arousal, and dominance following appraisal theory.
        """
        with self._lock:
            state = self._require_state(agent_id)
            desirability = _clamp(float(event.get("desirability", 0.0)), -1.0, 1.0)
            urgency = _clamp(float(event.get("urgency", 0.3)))
            control = _clamp(float(event.get("control", 0.5)))
            novelty = _clamp(float(event.get("novelty", 0.2)))
            valence = desirability
            arousal = _clamp(0.5 * urgency + 0.3 * novelty + 0.2 * abs(desirability))
            dominance = control
            primary = self._pick_primary_emotion(valence, arousal)
            intensity = _clamp(arousal * 0.6 + abs(valence) * 0.4)
            return self.set_emotional_state(
                agent_id, valence, arousal, dominance, primary, intensity
            )

    def get_emotional_influence(self, agent_id: str) -> Dict[str, Any]:
        """Describe how the current emotion biases decision-making.

        Returns a dict with risk_tolerance, focus, speed, and creativity
        modifiers derived from the PAD state.
        """
        with self._lock:
            state = self._require_state(agent_id)
            emo = state.emotional_state
            risk_tolerance = _clamp(0.5 + emo.dominance * 0.3 - emo.intensity * 0.1)
            focus = _clamp(0.5 + emo.arousal * 0.3 - (1.0 - emo.dominance) * 0.1)
            speed = _clamp(0.5 + emo.arousal * 0.4)
            creativity = _clamp(0.4 + (1.0 - abs(emo.valence)) * 0.2 + emo.intensity * 0.1)
            if emo.primary_emotion == EmotionType.FEAR:
                risk_tolerance = _clamp(risk_tolerance - 0.2)
                speed = _clamp(speed + 0.1)
            elif emo.primary_emotion == EmotionType.ANGER:
                risk_tolerance = _clamp(risk_tolerance + 0.2)
                focus = _clamp(focus - 0.1)
            elif emo.primary_emotion == EmotionType.CURIOSITY:
                creativity = _clamp(creativity + 0.2)
            elif emo.primary_emotion == EmotionType.JOY:
                creativity = _clamp(creativity + 0.1)
                risk_tolerance = _clamp(risk_tolerance + 0.1)
            return {
                "agent_id": agent_id,
                "risk_tolerance": _round(risk_tolerance),
                "focus": _round(focus),
                "speed": _round(speed),
                "creativity": _round(creativity),
                "primary_emotion": emo.primary_emotion.value,
                "valence": _round(emo.valence),
                "arousal": _round(emo.arousal),
            }

    # ------------------------------------------------------------------
    # Social cognition
    # ------------------------------------------------------------------

    def register_relation(
        self,
        agent_id: str,
        target_id: str,
        trust: float = 0.5,
        affection: float = 0.5,
        power_relation: SocialRole = SocialRole.STRANGER,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> SocialRelation:
        """Register or replace a social relation toward a target agent."""
        power_relation = _coerce_enum(SocialRole, power_relation, SocialRole.STRANGER)
        with self._lock:
            state = self._require_state(agent_id)
            relation = SocialRelation(
                target_id=target_id,
                trust=_clamp(trust),
                affection=_clamp(affection),
                power_relation=power_relation,
                metadata=metadata or {},
            )
            state.relations[target_id] = relation
            self._stats.social_updates += 1
            self._emit_event(
                agent_id,
                CognitiveEventKind.SOCIAL_RELATION_UPDATED,
                {"target_id": target_id, "power_relation": power_relation.value},
            )
            return relation

    def get_relation(self, agent_id: str, target_id: str) -> Optional[SocialRelation]:
        """Return the relation an agent holds toward a target."""
        with self._lock:
            state = self._require_state(agent_id)
            return state.relations.get(target_id)

    def list_relations(
        self,
        agent_id: str,
        role: Optional[SocialRole] = None,
    ) -> List[SocialRelation]:
        """List relations an agent holds, optionally filtered by role."""
        with self._lock:
            state = self._require_state(agent_id)
            relations = list(state.relations.values())
            if role is not None:
                relations = [r for r in relations if r.power_relation == role]
            relations.sort(key=lambda r: r.trust, reverse=True)
            return relations

    def update_relation(
        self,
        agent_id: str,
        target_id: str,
        trust_delta: float = 0.0,
        affection_delta: float = 0.0,
        power_relation: Optional[SocialRole] = None,
        interaction_note: Optional[str] = None,
    ) -> Optional[SocialRelation]:
        """Adjust a social relation by deltas and optionally record an interaction."""
        if power_relation is not None:
            power_relation = _coerce_enum(SocialRole, power_relation, None)
        with self._lock:
            state = self._require_state(agent_id)
            relation = state.relations.get(target_id)
            if relation is None:
                relation = self.register_relation(agent_id, target_id)
            relation.trust = _clamp(relation.trust + trust_delta)
            relation.affection = _clamp(relation.affection + affection_delta)
            if power_relation is not None:
                relation.power_relation = power_relation
            relation.last_interaction = _now_ts()
            if interaction_note:
                relation.history.append({
                    "note": interaction_note,
                    "timestamp": _now_ts(),
                    "trust": _round(relation.trust),
                    "affection": _round(relation.affection),
                })
            self._stats.social_updates += 1
            self._emit_event(
                agent_id,
                CognitiveEventKind.SOCIAL_RELATION_UPDATED,
                {"target_id": target_id},
            )
            return relation

    def remove_relation(self, agent_id: str, target_id: str) -> bool:
        """Remove a social relation."""
        with self._lock:
            state = self._require_state(agent_id)
            if target_id in state.relations:
                del state.relations[target_id]
                return True
            return False

    def theory_of_mind(
        self,
        agent_id: str,
        target_id: str,
    ) -> Dict[str, Any]:
        """Infer the beliefs and desires of another agent.

        Produces a simulated model of the target's likely mental state
        based on the observing agent's relations and shared history.
        """
        with self._lock:
            state = self._require_state(agent_id)
            relation = state.relations.get(target_id)
            target_state = self._states.get(target_id)
            inferred: Dict[str, Any] = {
                "observer": agent_id,
                "target": target_id,
                "inferred_beliefs": [],
                "inferred_desires": [],
                "inferred_emotion": EmotionType.TRUST.value,
                "confidence": 0.3,
                "timestamp": _now_ts(),
            }
            if target_state is not None:
                inferred["confidence"] = 0.7
                for belief in list(target_state.beliefs.values())[:5]:
                    inferred["inferred_beliefs"].append({
                        "proposition": belief.proposition,
                        "confidence": _round(belief.confidence * 0.8),
                    })
                for desire in list(target_state.desires.values())[:5]:
                    inferred["inferred_desires"].append({
                        "description": desire.description,
                        "priority": _round(desire.priority * 0.8),
                    })
                inferred["inferred_emotion"] = target_state.emotional_state.primary_emotion.value
            elif relation is not None:
                inferred["confidence"] = _clamp(relation.trust * 0.5)
                inferred["inferred_emotion"] = (
                    EmotionType.TRUST.value if relation.affection > 0.5 else EmotionType.CONTEMPT.value
                )
            if relation is not None:
                if relation.power_relation == SocialRole.RIVAL:
                    inferred["inferred_desires"].append({
                        "description": "outperform the observer",
                        "priority": 0.8,
                    })
                elif relation.power_relation == SocialRole.ALLY:
                    inferred["inferred_desires"].append({
                        "description": "support the observer",
                        "priority": 0.7,
                    })
                elif relation.power_relation == SocialRole.MENTOR:
                    inferred["inferred_desires"].append({
                        "description": "guide the observer",
                        "priority": 0.6,
                    })
            return inferred

    def assess_trust(self, agent_id: str, target_id: str) -> float:
        """Evaluate the trust level an agent places in a target.

        Combines the recorded trust value with the recency of interactions.
        """
        with self._lock:
            state = self._require_state(agent_id)
            relation = state.relations.get(target_id)
            if relation is None:
                return 0.3
            trust = relation.trust
            if relation.last_interaction is not None:
                age = _now_ts() - relation.last_interaction
                decay = math.exp(-age / (3600.0 * 24.0 * 7.0))
                trust = trust * decay + 0.3 * (1.0 - decay)
            positive_history = sum(
                1 for h in relation.history if h.get("trust", 0.5) >= 0.5
            )
            total_history = max(1, len(relation.history))
            history_factor = positive_history / total_history
            return _round(0.7 * trust + 0.3 * history_factor)

    def reason_about_coalition(
        self,
        agent_id: str,
        candidates: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Reason about forming a coalition with other agents.

        Returns a dict with the proposed coalition members, aggregate trust,
        and a recommended goal focus.
        """
        with self._lock:
            state = self._require_state(agent_id)
            if candidates is None:
                candidates = [
                    tid for tid, r in state.relations.items()
                    if r.power_relation in (SocialRole.ALLY, SocialRole.PEER, SocialRole.MENTOR)
                ]
            members: List[str] = [agent_id]
            trust_scores: List[float] = []
            for cand in candidates:
                trust = self.assess_trust(agent_id, cand)
                if trust >= 0.5:
                    members.append(cand)
                    trust_scores.append(trust)
            aggregate = sum(trust_scores) / len(trust_scores) if trust_scores else 0.0
            active_desires = [d for d in state.desires.values() if d.status == "active"]
            if active_desires:
                top = max(active_desires, key=self._desire_score)
                goal_focus = top.description
            else:
                goal_focus = "mutual survival and exploration"
            return {
                "agent_id": agent_id,
                "members": members,
                "aggregate_trust": _round(aggregate),
                "goal_focus": goal_focus,
                "timestamp": _now_ts(),
            }

    # ------------------------------------------------------------------
    # Action selection
    # ------------------------------------------------------------------

    def propose_actions(
        self,
        agent_id: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> List[ActionCandidate]:
        """Generate candidate actions for an agent given current state.

        Proposals are derived from active intentions, emotional drives, and
        social context.
        """
        with self._lock:
            state = self._require_state(agent_id)
            context = context or {}
            candidates: List[ActionCandidate] = []
            influence = self.get_emotional_influence(agent_id)
            active = self._active_intentions(state)
            for intention in active:
                desire = state.desires.get(intention.goal_id)
                if desire is None:
                    continue
                plan = (
                    state.plans.get(intention.plan_id)
                    if intention.plan_id
                    else None
                )
                if plan is not None and plan.current_step < len(plan.steps):
                    step = plan.steps[plan.current_step]
                    action_type = self._action_type_from_name(step.action)
                    candidates.append(ActionCandidate(
                        action_type=action_type,
                        description=f"execute plan step: {step.action}",
                        expected_utility=_clamp(desire.priority * 0.8 + 0.1),
                        cost=step.cost,
                        risk=_clamp(0.2 + step.cost * 0.2 - influence["risk_tolerance"] * 0.2),
                        parameters={"plan_id": plan.plan_id, "step_id": step.step_id},
                    ))
                else:
                    candidates.append(ActionCandidate(
                        action_type=ActionType.OBSERVE,
                        description=f"pursue goal: {desire.description}",
                        expected_utility=_clamp(desire.priority * 0.6),
                        cost=0.4,
                        risk=0.3,
                        parameters={"goal_id": desire.goal_id},
                    ))
            emo = state.emotional_state
            if emo.primary_emotion == EmotionType.CURIOSITY:
                candidates.append(ActionCandidate(
                    action_type=ActionType.EXPLORE,
                    description="explore novel surroundings",
                    expected_utility=_clamp(0.4 + influence["creativity"] * 0.3),
                    cost=0.3,
                    risk=0.3,
                ))
            if emo.primary_emotion == EmotionType.FEAR:
                candidates.append(ActionCandidate(
                    action_type=ActionType.FLEE,
                    description="retreat to safety",
                    expected_utility=_clamp(0.6 + (1 - influence["risk_tolerance"]) * 0.2),
                    cost=0.2,
                    risk=0.1,
                ))
            if emo.primary_emotion == EmotionType.ANGER:
                candidates.append(ActionCandidate(
                    action_type=ActionType.ATTACK,
                    description="engage threat aggressively",
                    expected_utility=_clamp(0.5 + influence["risk_tolerance"] * 0.2),
                    cost=0.6,
                    risk=0.6,
                ))
            low_priority_allies = [
                r for r in state.relations.values()
                if r.power_relation == SocialRole.ALLY and r.affection > 0.6
            ]
            if low_priority_allies and emo.valence > 0:
                candidates.append(ActionCandidate(
                    action_type=ActionType.COMMUNICATE,
                    description="reinforce alliance with a friendly agent",
                    expected_utility=0.4,
                    cost=0.2,
                    risk=0.05,
                    parameters={"target_id": low_priority_allies[0].target_id},
                ))
            if not candidates:
                candidates.append(ActionCandidate(
                    action_type=ActionType.OBSERVE,
                    description="observe the environment",
                    expected_utility=0.3,
                    cost=0.1,
                    risk=0.05,
                ))
            return candidates

    def _action_type_from_name(self, name: str) -> ActionType:
        """Map an action name string to an ActionType enum value."""
        lower = name.lower()
        for at in ActionType:
            if at.value in lower:
                return at
        if "go" in lower or "travel" in lower:
            return ActionType.MOVE
        if "talk" in lower or "say" in lower:
            return ActionType.COMMUNICATE
        return ActionType.INTERACT

    def evaluate_action(
        self,
        agent_id: str,
        candidate: ActionCandidate,
    ) -> ActionCandidate:
        """Compute expected utility for a candidate action in context.

        Adjusts the candidate's expected utility using emotional influence
        and the agent's confidence level.
        """
        if isinstance(candidate, dict):
            candidate = ActionCandidate(
                action_id=candidate.get("action_id", _uid("action")),
                action_type=_coerce_enum(ActionType, candidate.get("action_type", "wait"), ActionType.WAIT),
                description=candidate.get("description", ""),
                expected_utility=float(candidate.get("expected_utility", 0.5)),
                cost=float(candidate.get("cost", 0.3)),
                risk=float(candidate.get("risk", 0.2)),
                parameters=candidate.get("parameters") or {},
            )
        with self._lock:
            state = self._require_state(agent_id)
            influence = self.get_emotional_influence(agent_id)
            confidence = state.meta_state.confidence_level
            utility = candidate.expected_utility
            utility *= (0.7 + 0.3 * confidence)
            if candidate.risk > influence["risk_tolerance"]:
                utility -= 0.15 * (candidate.risk - influence["risk_tolerance"])
            if candidate.action_type == ActionType.CRAFT and influence["creativity"] > 0.6:
                utility += 0.1
            if candidate.action_type == ActionType.FLEE and influence["speed"] < 0.4:
                utility -= 0.1
            candidate.expected_utility = _clamp(utility)
            return candidate

    def select_action(
        self,
        agent_id: str,
        candidates: Optional[List[ActionCandidate]] = None,
    ) -> Optional[ActionCandidate]:
        """Choose the best action from candidates by net utility."""
        with self._lock:
            state = self._require_state(agent_id)
            if candidates is None:
                candidates = self.propose_actions(agent_id)
            if not candidates:
                return None
            scored: List[ActionCandidate] = []
            for c in candidates:
                scored.append(self.evaluate_action(agent_id, c))
            scored.sort(key=lambda c: c.net_utility, reverse=True)
            choice = scored[0]
            self._stats.decisions_made += 1
            self._emit_event(
                agent_id,
                CognitiveEventKind.DECISION_MADE,
                {
                    "action_id": choice.action_id,
                    "action_type": choice.action_type.value,
                    "net_utility": _round(choice.net_utility),
                },
            )
            return choice

    def execute_action(
        self,
        agent_id: str,
        candidate: ActionCandidate,
    ) -> Dict[str, Any]:
        """Perform the selected action and return an execution record.

        Execution is simulated: the outcome is sampled from the action's
        net utility with noise from the emotional influence.
        """
        if isinstance(candidate, dict):
            candidate = ActionCandidate(
                action_id=candidate.get("action_id", _uid("action")),
                action_type=_coerce_enum(ActionType, candidate.get("action_type", "wait"), ActionType.WAIT),
                description=candidate.get("description", ""),
                expected_utility=float(candidate.get("expected_utility", 0.5)),
                cost=float(candidate.get("cost", 0.3)),
                risk=float(candidate.get("risk", 0.2)),
                parameters=candidate.get("parameters") or {},
            )
        with self._lock:
            state = self._require_state(agent_id)
            influence = self.get_emotional_influence(agent_id)
            base = candidate.net_utility
            speed_factor = 0.5 + influence["speed"] * 0.5
            success_threshold = 0.35
            success = base >= success_threshold
            if candidate.action_type == ActionType.ATTACK:
                success = base >= 0.45
            if candidate.action_type == ActionType.FLEE:
                success = base >= 0.30 and speed_factor > 0.5
            if candidate.action_type == ActionType.CRAFT:
                success = base >= 0.40 and influence["creativity"] > 0.4
            record: Dict[str, Any] = {
                "agent_id": agent_id,
                "action_id": candidate.action_id,
                "action_type": candidate.action_type.value,
                "description": candidate.description,
                "success": success,
                "net_utility": _round(base),
                "timestamp": _now_ts(),
            }
            self._outcomes.append(record)
            state.self_model["total_actions"] = state.self_model.get("total_actions", 0) + 1
            if success:
                state.self_model["successful_actions"] = (
                    state.self_model.get("successful_actions", 0) + 1
                )
            return record

    def record_outcome(
        self,
        agent_id: str,
        action_id: str,
        success: bool,
        reason: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Store an outcome record for later learning and reflection."""
        with self._lock:
            state = self._require_state(agent_id)
            record: Dict[str, Any] = {
                "agent_id": agent_id,
                "action_id": action_id,
                "success": success,
                "reason": reason or "",
                "timestamp": _now_ts(),
            }
            self._outcomes.append(record)
            state.self_model["total_actions"] = state.self_model.get("total_actions", 0) + 1
            if success:
                state.self_model["successful_actions"] = (
                    state.self_model.get("successful_actions", 0) + 1
                )
            return record

    # ------------------------------------------------------------------
    # System methods
    # ------------------------------------------------------------------

    def register_agent(
        self,
        agent_id: str,
        traits: Optional[Dict[str, Any]] = None,
    ) -> CognitiveState:
        """Register a new agent and initialize its cognitive state."""
        with self._lock:
            if agent_id in self._states:
                return self._states[agent_id]
            traits = traits or {}
            state = CognitiveState(agent_id=agent_id)
            state.self_model = self._default_self_model(agent_id, traits)
            state.emotional_state = EmotionalState(
                valence=float(traits.get("valence", 0.0)),
                arousal=float(traits.get("arousal", 0.3)),
                dominance=float(traits.get("dominance", 0.5)),
                primary_emotion=EmotionType.TRUST,
                intensity=0.4,
            )
            state.meta_state.strategy = MetaStrategy.DELIBERATIVE
            state.meta_state.resource_budget = _meta_strategy_budget(MetaStrategy.DELIBERATIVE)
            self._states[agent_id] = state
            return state

    def get_agent(self, agent_id: str) -> Optional[CognitiveState]:
        """Return the cognitive state for an agent, or None."""
        with self._lock:
            return self._states.get(agent_id)

    def list_agents(self) -> List[str]:
        """Return the ids of all registered agents."""
        with self._lock:
            return list(self._states.keys())

    def remove_agent(self, agent_id: str) -> bool:
        """Remove an agent and all its cognitive state."""
        with self._lock:
            if agent_id in self._states:
                del self._states[agent_id]
                if agent_id in self._events_by_agent:
                    del self._events_by_agent[agent_id]
                return True
            return False

    def tick(self, agent_id: Optional[str] = None) -> Dict[str, Any]:
        """Advance the cognitive cycle for one agent or all agents.

        Runs perception-to-belief promotion, desire activation, intention
        commitment checks, plan step execution, and periodic reflection.
        Returns a summary dict of the cycle.
        """
        with self._lock:
            targets = [agent_id] if agent_id is not None else list(self._states.keys())
            summary: Dict[str, Any] = {
                "tick": self._stats.ticks_processed + 1,
                "agents": {},
                "timestamp": _now_ts(),
            }
            for target in targets:
                state = self._states.get(target)
                if state is None:
                    summary["agents"][target] = {"error": "not registered"}
                    continue
                phase_results: Dict[str, Any] = {}
                state.phase = CognitivePhase.PERCEPTION
                phase_results["beliefs_updated"] = self.update_beliefs_from_percepts(target)
                state.phase = CognitivePhase.BELIEF_UPDATE
                self.decay_beliefs(target, elapsed=1.0)
                state.phase = CognitivePhase.DESIRE_ACTIVATION
                phase_results["desires_activated"] = self.activate_desires(target)
                state.phase = CognitivePhase.INTENTION_FORMATION
                maintained = 0
                for intention in list(state.intentions.values()):
                    verdict = self.check_commitment(target, intention.intention_id)
                    if verdict == "abandon":
                        self.abandon_intention(target, intention.intention_id)
                    elif verdict == "suspend":
                        self.suspend_intention(target, intention.intention_id)
                    else:
                        maintained += 1
                phase_results["intentions_maintained"] = maintained
                state.phase = CognitivePhase.PLANNING
                step_executed = None
                if state.current_plan is not None:
                    step_executed = self.execute_plan_step(target, state.current_plan)
                phase_results["step_executed"] = (
                    step_executed.action if step_executed is not None else None
                )
                state.phase = CognitivePhase.EXECUTION
                candidate = self.select_action(target)
                if candidate is not None:
                    self.execute_action(target, candidate)
                phase_results["action_selected"] = (
                    candidate.action_type.value if candidate is not None else None
                )
                state.phase = CognitivePhase.REFLECTION
                if state.tick_count % self._config.get("reflection_interval", 5) == 0:
                    self.trigger_reflection(target, topic="periodic")
                state.phase = CognitivePhase.META_REASONING
                self.assess_confidence(target)
                state.phase = CognitivePhase.PERCEPTION
                state.tick_count += 1
                state.last_tick = _now_ts()
                self._stats.ticks_processed += 1
                self._emit_event(
                    target,
                    CognitiveEventKind.TICK,
                    {"tick": state.tick_count},
                )
                summary["agents"][target] = phase_results
            self._status = "running"
            return summary

    def get_config(self, key: Optional[str] = None) -> Any:
        """Return a config value or the whole config dict."""
        with self._lock:
            if key is None:
                return dict(self._config)
            return self._config.get(key)

    def set_config(self, **kwargs: Any) -> Dict[str, Any]:
        """Update configuration values from keyword arguments."""
        with self._lock:
            for key, value in kwargs.items():
                self._config[key] = value
            return dict(self._config)

    def get_status(self) -> Dict[str, Any]:
        """Return a status snapshot of the core."""
        with self._lock:
            return {
                "core_id": self._core_id,
                "status": self._status,
                "agent_count": len(self._states),
                "event_count": len(self._events),
                "uptime": _round(_now_ts() - self._start_time),
                "tick_count": self._stats.ticks_processed,
                "timestamp": _now_ts(),
            }

    def get_stats(self) -> CognitiveStats:
        """Return aggregate statistics for the core."""
        with self._lock:
            return self._stats

    def get_snapshot(self) -> CognitiveSnapshot:
        """Return a full serializable snapshot of the core."""
        with self._lock:
            agents = [s.to_dict() for s in self._states.values()]
            return CognitiveSnapshot(
                core_id=self._core_id,
                agent_count=len(self._states),
                agents=agents,
                stats=self._stats.to_dict(),
                config=dict(self._config),
                status=self._status,
            )

    def list_events(
        self,
        agent_id: Optional[str] = None,
        kind: Optional[CognitiveEventKind] = None,
        limit: int = 100,
    ) -> List[CognitiveEvent]:
        """Return recent events, optionally filtered by agent or kind."""
        with self._lock:
            if agent_id is not None:
                events = list(self._events_by_agent.get(agent_id, deque()))
            else:
                events = list(self._events)
            if kind is not None:
                events = [e for e in events if e.kind == kind]
            events.reverse()
            return events[:limit]

    def get_visualization_data(self, agent_id: Optional[str] = None) -> Dict[str, Any]:
        """Return data formatted for visualization dashboards."""
        with self._lock:
            targets = [agent_id] if agent_id is not None else list(self._states.keys())
            nodes: List[Dict[str, Any]] = []
            edges: List[Dict[str, Any]] = []
            for target in targets:
                state = self._states.get(target)
                if state is None:
                    continue
                nodes.append({
                    "id": target,
                    "type": "agent",
                    "emotion": state.emotional_state.primary_emotion.value,
                    "valence": _round(state.emotional_state.valence),
                    "arousal": _round(state.emotional_state.arousal),
                    "confidence": _round(state.meta_state.confidence_level),
                    "strategy": state.meta_state.strategy.value,
                    "belief_count": len(state.beliefs),
                    "desire_count": len(state.desires),
                    "intention_count": len(state.intentions),
                    "plan_count": len(state.plans),
                })
                for rel in state.relations.values():
                    edges.append({
                        "source": target,
                        "target": rel.target_id,
                        "trust": _round(rel.trust),
                        "affection": _round(rel.affection),
                        "role": rel.power_relation.value,
                    })
            return {
                "nodes": nodes,
                "edges": edges,
                "stats": self._stats.to_dict(),
                "status": self._status,
                "timestamp": _now_ts(),
            }

    def reset(self) -> None:
        """Reset the core to its initial state and reseed default data."""
        with self._lock:
            self._states.clear()
            self._events.clear()
            self._events_by_agent.clear()
            self._outcomes.clear()
            self._reflections.clear()
            self._handlers.clear()
            self._stats = CognitiveStats()
            self._status = "idle"
            self._seeded = False
            self._start_time = _now_ts()
            self._emit_event("__core__", CognitiveEventKind.SYSTEM_RESET, {})
            self._seed_data()

    def initialize(
        self,
        config: Optional[Dict[str, Any]] = None,
        auto_seed: Optional[bool] = None,
    ) -> None:
        """Initialize or reconfigure the core with optional config."""
        with self._lock:
            if config is not None:
                self._config.update(config)
            if auto_seed is not None:
                self._config["auto_seed"] = auto_seed
            if not self._seeded and self._config.get("auto_seed", True):
                self._seed_data()
            self._status = "ready"

    def register_handler(
        self,
        handler_id: str,
        handler: Callable[[CognitiveEvent], None],
        kind: Optional[CognitiveEventKind] = None,
    ) -> None:
        """Register an event handler for a specific kind or all events."""
        with self._lock:
            bucket = self._handlers.setdefault(kind, {})
            bucket[handler_id] = handler

    def unregister_handler(
        self,
        handler_id: str,
        kind: Optional[CognitiveEventKind] = None,
    ) -> bool:
        """Remove a previously registered event handler."""
        with self._lock:
            bucket = self._handlers.get(kind)
            if bucket is None or handler_id not in bucket:
                return False
            del bucket[handler_id]
            return True

    # ------------------------------------------------------------------
    # AI methods
    # ------------------------------------------------------------------

    def ai_predict_behavior(
        self,
        agent_id: str,
        horizon: int = 5,
    ) -> Dict[str, Any]:
        """Predict likely future behavior of an agent from its cognitive state.

        The prediction projects the agent's active intentions and emotional
        trajectory forward by a number of ticks. Returns a dict with
        predicted actions, confidence, and emotional trend.
        """
        with self._lock:
            state = self._require_state(agent_id)
            self._stats.ai_predictions += 1
            predictions: List[Dict[str, Any]] = []
            active = self._active_intentions(state)
            influence = self.get_emotional_influence(agent_id)
            emo = state.emotional_state
            valence_trend = emo.valence
            arousal_trend = emo.arousal
            for step in range(horizon):
                entry: Dict[str, Any] = {"step": step + 1}
                if active:
                    top_intention = max(active, key=lambda i: i.commitment_strength)
                    desire = state.desires.get(top_intention.goal_id)
                    plan = (
                        state.plans.get(top_intention.plan_id)
                        if top_intention.plan_id
                        else None
                    )
                    if plan is not None and plan.current_step < len(plan.steps):
                        next_step = plan.steps[plan.current_step]
                        entry["predicted_action"] = next_step.action
                        entry["action_type"] = self._action_type_from_name(next_step.action).value
                    elif desire is not None:
                        entry["predicted_action"] = f"pursue:{desire.description}"
                        entry["action_type"] = ActionType.OBSERVE.value
                else:
                    if emo.primary_emotion == EmotionType.CURIOSITY:
                        entry["predicted_action"] = "explore"
                        entry["action_type"] = ActionType.EXPLORE.value
                    elif emo.primary_emotion == EmotionType.FEAR:
                        entry["predicted_action"] = "flee"
                        entry["action_type"] = ActionType.FLEE.value
                    else:
                        entry["predicted_action"] = "observe"
                        entry["action_type"] = ActionType.OBSERVE.value
                valence_trend = _clamp(valence_trend * 0.9, -1.0, 1.0)
                arousal_trend = _clamp(arousal_trend * 0.85)
                entry["valence"] = _round(valence_trend)
                entry["arousal"] = _round(arousal_trend)
                predictions.append(entry)
            confidence = _clamp(
                state.meta_state.confidence_level * 0.6
                + (1.0 - min(1.0, horizon / 10.0)) * 0.4
            )
            result = {
                "agent_id": agent_id,
                "horizon": horizon,
                "predictions": predictions,
                "confidence": _round(confidence),
                "current_emotion": emo.primary_emotion.value,
                "risk_tolerance": influence["risk_tolerance"],
                "timestamp": _now_ts(),
            }
            self._emit_event(
                agent_id,
                CognitiveEventKind.AI_PREDICTION,
                {"horizon": horizon, "confidence": _round(confidence)},
            )
            return result

    def ai_optimize_cognition(
        self,
        agent_id: str,
        objective: str = "balanced",
    ) -> Dict[str, Any]:
        """Optimize cognitive parameters for a target objective.

        Adjusts the meta-strategy, resource budget, and reflection cadence
        to improve performance toward the objective. Returns the applied
        parameter changes and projected improvement.
        """
        with self._lock:
            state = self._require_state(agent_id)
            self._stats.ai_predictions += 1
            perf = self.evaluate_performance(agent_id)
            current_strategy = state.meta_state.strategy
            changes: Dict[str, Any] = {}
            objective_lower = objective.lower()
            if objective_lower == "speed":
                new_strategy = MetaStrategy.REACTIVE
                changes["reflection_interval"] = 10
                changes["resource_budget"] = 0.3
            elif objective_lower == "accuracy":
                new_strategy = MetaStrategy.DELIBERATIVE
                changes["reflection_interval"] = 3
                changes["resource_budget"] = 0.7
            elif objective_lower == "learning":
                new_strategy = MetaStrategy.LEARNING
                changes["reflection_interval"] = 2
                changes["resource_budget"] = 0.65
            elif objective_lower == "creativity":
                new_strategy = MetaStrategy.CREATIVE
                changes["reflection_interval"] = 4
                changes["resource_budget"] = 0.8
            elif objective_lower == "reflection":
                new_strategy = MetaStrategy.REFLECTIVE
                changes["reflection_interval"] = 1
                changes["resource_budget"] = 0.75
            else:
                new_strategy = MetaStrategy.DELIBERATIVE
                changes["reflection_interval"] = 5
                changes["resource_budget"] = 0.6
            if new_strategy != current_strategy:
                self.set_meta_strategy(agent_id, new_strategy)
                changes["strategy"] = new_strategy.value
            else:
                state.meta_state.resource_budget = changes.get(
                    "resource_budget", state.meta_state.resource_budget
                )
            if "reflection_interval" in changes:
                self._config["reflection_interval"] = changes["reflection_interval"]
            projected = _clamp(
                perf["success_rate"] * 0.7
                + state.meta_state.resource_budget * 0.3
            )
            if objective_lower == "speed" and perf["trend"] == "stable":
                projected = _clamp(projected + 0.05)
            if objective_lower == "accuracy" and perf["trend"] == "improving":
                projected = _clamp(projected + 0.05)
            return {
                "agent_id": agent_id,
                "objective": objective,
                "changes": changes,
                "previous_strategy": current_strategy.value,
                "new_strategy": new_strategy.value,
                "projected_improvement": _round(projected),
                "current_performance": perf,
                "timestamp": _now_ts(),
            }

    def ai_assess_personality(
        self,
        agent_id: str,
    ) -> Dict[str, Any]:
        """Assess an agent's personality from its cognitive patterns.

        Derives a Big-Five-style profile from the distribution of desires,
        emotions, social relations, and action history.
        """
        with self._lock:
            state = self._require_state(agent_id)
            self._stats.ai_predictions += 1
            desires = list(state.desires.values())
            social_count = len(state.relations)
            ally_count = sum(
                1 for r in state.relations.values()
                if r.power_relation == SocialRole.ALLY
            )
            rival_count = sum(
                1 for r in state.relations.values()
                if r.power_relation == SocialRole.RIVAL
            )
            avg_trust = (
                sum(r.trust for r in state.relations.values()) / social_count
                if social_count
                else 0.5
            )
            avg_affection = (
                sum(r.affection for r in state.relations.values()) / social_count
                if social_count
                else 0.5
            )
            emo = state.emotional_state
            survival_count = sum(
                1 for d in desires if d.category == DesireCategory.SURVIVAL
            )
            cognitive_count = sum(
                1 for d in desires if d.category == DesireCategory.COGNITIVE
            )
            social_desire_count = sum(
                1 for d in desires if d.category == DesireCategory.SOCIAL
            )
            total_desires = max(1, len(desires))
            openness = _clamp(
                0.3
                + (cognitive_count / total_desires) * 0.5
                + emo.intensity * 0.2
            )
            conscientiousness = _clamp(
                state.meta_state.confidence_level * 0.5
                + state.meta_state.resource_budget * 0.5
            )
            extraversion = _clamp(
                0.3
                + (social_desire_count / total_desires) * 0.4
                + (social_count / 10.0) * 0.3
            )
            agreeableness = _clamp(
                avg_affection * 0.5
                + (ally_count / max(1, social_count)) * 0.4
                + (1.0 - rival_count / max(1, social_count)) * 0.1
            )
            neuroticism = _clamp(
                (1.0 - emo.dominance) * 0.4
                + emo.arousal * 0.3
                + max(0.0, -emo.valence) * 0.3
            )
            if emo.primary_emotion == EmotionType.ANGER:
                neuroticism = _clamp(neuroticism + 0.1)
            if emo.primary_emotion == EmotionType.JOY:
                extraversion = _clamp(extraversion + 0.1)
            dominant_trait = max(
                [
                    ("openness", openness),
                    ("conscientiousness", conscientiousness),
                    ("extraversion", extraversion),
                    ("agreeableness", agreeableness),
                    ("neuroticism", neuroticism),
                ],
                key=lambda t: t[1],
            )[0]
            archetype = "explorer"
            if extraversion > 0.6 and agreeableness > 0.6:
                archetype = "diplomat"
            elif conscientiousness > 0.7:
                archetype = "strategist"
            elif openness > 0.7:
                archetype = "innovator"
            elif neuroticism > 0.6:
                archetype = "survivor"
            elif agreeableness < 0.3:
                archetype = "lone wolf"
            risk_appetite = _clamp(
                0.5 + openness * 0.2 + (1.0 - agreeableness) * 0.1 - neuroticism * 0.2
            )
            return {
                "agent_id": agent_id,
                "traits": {
                    "openness": _round(openness),
                    "conscientiousness": _round(conscientiousness),
                    "extraversion": _round(extraversion),
                    "agreeableness": _round(agreeableness),
                    "neuroticism": _round(neuroticism),
                },
                "dominant_trait": dominant_trait,
                "archetype": archetype,
                "risk_appetite": _round(risk_appetite),
                "social_orientation": _round(avg_trust),
                "emotional_baseline": {
                    "valence": _round(emo.valence),
                    "arousal": _round(emo.arousal),
                    "dominance": _round(emo.dominance),
                    "primary_emotion": emo.primary_emotion.value,
                },
                "timestamp": _now_ts(),
            }

    # ------------------------------------------------------------------
    # Seed data
    # ------------------------------------------------------------------

    def _seed_data(self) -> None:
        """Populate the core with seed agents, beliefs, desires, intentions,
        plans, relations, and emotional states. Runs exactly once thanks to
        the _seeded flag.
        """
        if self._seeded:
            return
        agent_profiles = [
            ("Hero", {
                "valence": 0.4, "arousal": 0.6, "dominance": 0.7,
                "primary_emotion": EmotionType.CURIOSITY,
                "traits": {
                    "competence": 0.8, "boldness": 0.85, "sociability": 0.6,
                    "integrity": 0.9, "creativity": 0.5,
                    "strengths": ["courage", "leadership"],
                    "weaknesses": ["recklessness"],
                },
                "strategy": MetaStrategy.DELIBERATIVE,
            }),
            ("Villain", {
                "valence": -0.1, "arousal": 0.5, "dominance": 0.8,
                "primary_emotion": EmotionType.ANTICIPATION,
                "traits": {
                    "competence": 0.85, "boldness": 0.7, "sociability": 0.4,
                    "integrity": 0.2, "creativity": 0.7,
                    "strengths": ["cunning", "ambition"],
                    "weaknesses": ["hubris"],
                },
                "strategy": MetaStrategy.DELIBERATIVE,
            }),
            ("Mentor", {
                "valence": 0.5, "arousal": 0.2, "dominance": 0.65,
                "primary_emotion": EmotionType.TRUST,
                "traits": {
                    "competence": 0.9, "boldness": 0.4, "sociability": 0.7,
                    "integrity": 0.85, "creativity": 0.6,
                    "strengths": ["wisdom", "patience"],
                    "weaknesses": ["caution"],
                },
                "strategy": MetaStrategy.REFLECTIVE,
            }),
            ("Ally", {
                "valence": 0.6, "arousal": 0.4, "dominance": 0.55,
                "primary_emotion": EmotionType.JOY,
                "traits": {
                    "competence": 0.65, "boldness": 0.5, "sociability": 0.85,
                    "integrity": 0.8, "creativity": 0.45,
                    "strengths": ["loyalty", "supportiveness"],
                    "weaknesses": ["indecision"],
                },
                "strategy": MetaStrategy.LEARNING,
            }),
            ("Rival", {
                "valence": 0.1, "arousal": 0.65, "dominance": 0.7,
                "primary_emotion": EmotionType.PRIDE,
                "traits": {
                    "competence": 0.75, "boldness": 0.75, "sociability": 0.45,
                    "integrity": 0.5, "creativity": 0.55,
                    "strengths": ["drive", "skill"],
                    "weaknesses": ["vanity"],
                },
                "strategy": MetaStrategy.CREATIVE,
            }),
        ]
        for agent_id, profile in agent_profiles:
            self._seed_agent(agent_id, profile)
        self._seed_relations()
        self._seeded = True
        self._status = "seeded"

    def _seed_agent(self, agent_id: str, profile: Dict[str, Any]) -> None:
        """Seed a single agent with beliefs, desires, intentions, plans, and emotion."""
        traits = profile.get("traits", {})
        state = self.register_agent(agent_id, traits=traits)
        emo_profile = profile.get("primary_emotion", EmotionType.TRUST)
        self.set_emotional_state(
            agent_id,
            valence=profile.get("valence", 0.0),
            arousal=profile.get("arousal", 0.3),
            dominance=profile.get("dominance", 0.5),
            primary_emotion=emo_profile,
            intensity=0.6,
        )
        self.set_meta_strategy(agent_id, profile.get("strategy", MetaStrategy.DELIBERATIVE))
        self._seed_beliefs(agent_id)
        self._seed_desires(agent_id)
        self._seed_intentions_and_plans(agent_id)

    def _seed_beliefs(self, agent_id: str) -> None:
        """Seed ten beliefs per agent covering world, self, and others."""
        belief_sets = {
            "Hero": [
                ("world.safe_zone_location", {"x": 10, "y": 20}, 0.9, BeliefSource.MEMORY),
                ("world.enemy_patrol_active", True, 0.7, BeliefSource.PERCEPTION),
                ("self.combat_skill", 0.85, 0.95, BeliefSource.MEMORY),
                ("self.health_status", "healthy", 0.9, BeliefSource.PERCEPTION),
                ("self.current_objective", "defeat the warlord", 0.95, BeliefSource.INFERENCE),
                ("other.Villain.hostile", True, 0.85, BeliefSource.INFERENCE),
                ("other.Mentor.trustworthy", True, 0.9, BeliefSource.COMMUNICATION),
                ("other.Ally.reliable", True, 0.85, BeliefSource.COMMUNICATION),
                ("other.Rival.ambitious", True, 0.7, BeliefSource.INFERENCE),
                ("world.treasure_location", {"x": 45, "y": 12}, 0.6, BeliefSource.MEMORY),
            ],
            "Villain": [
                ("world.power_vacuum", True, 0.9, BeliefSource.INFERENCE),
                ("world.guard_routes", ["north", "east"], 0.8, BeliefSource.PERCEPTION),
                ("self.influence_level", 0.7, 0.9, BeliefSource.MEMORY),
                ("self.secret_alliance", True, 0.85, BeliefSource.INFERENCE),
                ("self.current_scheme", "usurp the throne", 0.95, BeliefSource.INFERENCE),
                ("other.Hero.threatening", True, 0.8, BeliefSource.INFERENCE),
                ("other.Mentor.observant", True, 0.7, BeliefSource.COMMUNICATION),
                ("other.Ally.gullible", True, 0.5, BeliefSource.INFERENCE),
                ("other.Rival.controllable", False, 0.6, BeliefSource.INFERENCE),
                ("world.artifact_location", {"x": 88, "y": 3}, 0.65, BeliefSource.MEMORY),
            ],
            "Mentor": [
                ("world.history_cycle", "repeating", 0.85, BeliefSource.MEMORY),
                ("world.political_tension", "high", 0.8, BeliefSource.PERCEPTION),
                ("self.wisdom_level", 0.9, 0.95, BeliefSource.MEMORY),
                ("self.energy_level", 0.6, 0.85, BeliefSource.PERCEPTION),
                ("self.current_purpose", "guide the next generation", 0.95, BeliefSource.INFERENCE),
                ("other.Hero.potential", 0.9, 0.85, BeliefSource.INFERENCE),
                ("other.Villain.dangerous", True, 0.85, BeliefSource.INFERENCE),
                ("other.Ally.devoted", True, 0.8, BeliefSource.COMMUNICATION),
                ("other.Rival.unsettled", True, 0.65, BeliefSource.INFERENCE),
                ("world.ancient_lore", True, 0.9, BeliefSource.MEMORY),
            ],
            "Ally": [
                ("world.team_headquarters", {"x": 5, "y": 5}, 0.95, BeliefSource.MEMORY),
                ("world.supply_levels", "adequate", 0.7, BeliefSource.PERCEPTION),
                ("self.support_skill", 0.75, 0.9, BeliefSource.MEMORY),
                ("self.morale", 0.8, 0.85, BeliefSource.PERCEPTION),
                ("self.current_role", "assist the Hero", 0.95, BeliefSource.INFERENCE),
                ("other.Hero.admirable", True, 0.9, BeliefSource.COMMUNICATION),
                ("other.Villain.untrustworthy", True, 0.75, BeliefSource.INFERENCE),
                ("other.Mentor.respected", True, 0.9, BeliefSource.COMMUNICATION),
                ("other.Rival.intimidating", True, 0.6, BeliefSource.INFERENCE),
                ("world.escape_routes", ["south", "west"], 0.8, BeliefSource.MEMORY),
            ],
            "Rival": [
                ("world.competition_active", True, 0.9, BeliefSource.PERCEPTION),
                ("world.reward_stakes", "high", 0.8, BeliefSource.INFERENCE),
                ("self.ranking", 2, 0.85, BeliefSource.MEMORY),
                ("self.prestige", 0.65, 0.9, BeliefSource.PERCEPTION),
                ("self.current_aim", "surpass the Hero", 0.95, BeliefSource.INFERENCE),
                ("other.Hero.rival", True, 0.9, BeliefSource.INFERENCE),
                ("other.Villain.deceptive", True, 0.7, BeliefSource.INFERENCE),
                ("other.Mentor.judging", True, 0.55, BeliefSource.COMMUNICATION),
                ("other.Ally.minor", True, 0.5, BeliefSource.INFERENCE),
                ("world.training_grounds", {"x": 30, "y": 40}, 0.85, BeliefSource.MEMORY),
            ],
        }
        for proposition, value, confidence, source in belief_sets.get(agent_id, []):
            self.add_belief(
                agent_id,
                proposition=proposition,
                value=value,
                confidence=confidence,
                source=source,
                decay_rate=0.005,
            )

    def _seed_desires(self, agent_id: str) -> None:
        """Seed five desires per agent across varied categories."""
        desire_sets = {
            "Hero": [
                ("Defeat the warlord and restore peace", 0.95, DesireCategory.SELF_ACTUALIZATION, None),
                ("Protect innocent villagers", 0.85, DesireCategory.SAFETY, None),
                ("Strengthen bonds with allies", 0.6, DesireCategory.SOCIAL, None),
                ("Earn recognition as a champion", 0.7, DesireCategory.ESTEEM, None),
                ("Discover hidden ancient lore", 0.55, DesireCategory.COGNITIVE, None),
            ],
            "Villain": [
                ("Seize control of the realm", 0.95, DesireCategory.SELF_ACTUALIZATION, None),
                ("Eliminate threats to power", 0.85, DesireCategory.SAFETY, None),
                ("Recruit useful pawns", 0.6, DesireCategory.SOCIAL, None),
                ("Be feared and respected", 0.75, DesireCategory.ESTEEM, None),
                ("Uncover the artifact's power", 0.65, DesireCategory.COGNITIVE, None),
            ],
            "Mentor": [
                ("Guide the Hero to fulfill destiny", 0.9, DesireCategory.SELF_ACTUALIZATION, None),
                ("Preserve ancient knowledge", 0.8, DesireCategory.COGNITIVE, None),
                ("Maintain stability in the region", 0.7, DesireCategory.SAFETY, None),
                ("Foster the next generation", 0.65, DesireCategory.SOCIAL, None),
                ("Reflect on lessons of the past", 0.5, DesireCategory.COGNITIVE, None),
            ],
            "Ally": [
                ("Support the Hero in every quest", 0.9, DesireCategory.SOCIAL, None),
                ("Keep the team safe", 0.8, DesireCategory.SAFETY, None),
                ("Improve personal combat skills", 0.65, DesireCategory.ESTEEM, None),
                ("Gather enough supplies", 0.7, DesireCategory.SURVIVAL, None),
                ("Find a place to belong", 0.55, DesireCategory.SOCIAL, None),
            ],
            "Rival": [
                ("Surpass the Hero in renown", 0.9, DesireCategory.ESTEEM, None),
                ("Win the grand tournament", 0.85, DesireCategory.SELF_ACTUALIZATION, None),
                ("Secure rare training resources", 0.7, DesireCategory.SURVIVAL, None),
                ("Build a reputation that lasts", 0.6, DesireCategory.ESTEEM, None),
                ("Explore uncharted frontier lands", 0.5, DesireCategory.COGNITIVE, None),
            ],
        }
        for description, priority, category, deadline in desire_sets.get(agent_id, []):
            desire = self.add_desire(
                agent_id,
                description=description,
                priority=priority,
                category=category,
                deadline=deadline,
                satisfaction_criteria={},
            )
            self.update_desire(agent_id, desire.goal_id, status="active")

    def _seed_intentions_and_plans(self, agent_id: str) -> None:
        """Seed three intentions and two multi-step plans per agent."""
        plan_sets = {
            "Hero": [
                ("Defeat the warlord and restore peace", [
                    {"action": "observe", "preconditions": {}, "effects": {"enemy_located": True}, "cost": 0.3, "duration": 1.0},
                    {"action": "attack", "preconditions": {}, "effects": {"enemy_engaged": True}, "cost": 0.7, "duration": 2.0},
                    {"action": "defend", "preconditions": {}, "effects": {"self_safe": True}, "cost": 0.4, "duration": 1.0},
                ]),
                ("Discover hidden ancient lore", [
                    {"action": "explore", "preconditions": {}, "effects": {"ruins_found": True}, "cost": 0.5, "duration": 2.0},
                    {"action": "observe", "preconditions": {}, "effects": {"lore_deciphered": True}, "cost": 0.3, "duration": 1.0},
                ]),
            ],
            "Villain": [
                ("Seize control of the realm", [
                    {"action": "observe", "preconditions": {}, "effects": {"weak_points_mapped": True}, "cost": 0.3, "duration": 1.0},
                    {"action": "communicate", "preconditions": {}, "effects": {"allies_recruited": True}, "cost": 0.4, "duration": 2.0},
                    {"action": "attack", "preconditions": {}, "effects": {"throne_seized": True}, "cost": 0.8, "duration": 3.0},
                ]),
                ("Uncover the artifact's power", [
                    {"action": "explore", "preconditions": {}, "effects": {"artifact_located": True}, "cost": 0.5, "duration": 2.0},
                    {"action": "craft", "preconditions": {}, "effects": {"ritual_prepared": True}, "cost": 0.6, "duration": 2.0},
                ]),
            ],
            "Mentor": [
                ("Guide the Hero to fulfill destiny", [
                    {"action": "observe", "preconditions": {}, "effects": {"hero_assessed": True}, "cost": 0.2, "duration": 1.0},
                    {"action": "communicate", "preconditions": {}, "effects": {"guidance_given": True}, "cost": 0.3, "duration": 1.0},
                    {"action": "communicate", "preconditions": {}, "effects": {"hero_empowered": True}, "cost": 0.4, "duration": 2.0},
                ]),
                ("Preserve ancient knowledge", [
                    {"action": "observe", "preconditions": {}, "effects": {"scrolls_found": True}, "cost": 0.3, "duration": 1.0},
                    {"action": "craft", "preconditions": {}, "effects": {"archive_built": True}, "cost": 0.6, "duration": 3.0},
                ]),
            ],
            "Ally": [
                ("Support the Hero in every quest", [
                    {"action": "observe", "preconditions": {}, "effects": {"hero_status_known": True}, "cost": 0.2, "duration": 1.0},
                    {"action": "move", "preconditions": {}, "effects": {"at_hero_side": True}, "cost": 0.3, "duration": 1.0},
                    {"action": "defend", "preconditions": {}, "effects": {"hero_protected": True}, "cost": 0.5, "duration": 2.0},
                ]),
                ("Gather enough supplies", [
                    {"action": "explore", "preconditions": {}, "effects": {"supplies_located": True}, "cost": 0.4, "duration": 2.0},
                    {"action": "move", "preconditions": {}, "effects": {"supplies_collected": True}, "cost": 0.3, "duration": 1.0},
                ]),
            ],
            "Rival": [
                ("Win the grand tournament", [
                    {"action": "observe", "preconditions": {}, "effects": {"opponents_known": True}, "cost": 0.3, "duration": 1.0},
                    {"action": "craft", "preconditions": {}, "effects": {"gear_improved": True}, "cost": 0.5, "duration": 2.0},
                    {"action": "attack", "preconditions": {}, "effects": {"matches_won": True}, "cost": 0.7, "duration": 3.0},
                ]),
                ("Explore uncharted frontier lands", [
                    {"action": "explore", "preconditions": {}, "effects": {"frontier_reached": True}, "cost": 0.5, "duration": 2.0},
                    {"action": "observe", "preconditions": {}, "effects": {"land_charted": True}, "cost": 0.4, "duration": 2.0},
                ]),
            ],
        }
        plans_for_agent = plan_sets.get(agent_id, [])
        if not plans_for_agent:
            return
        desires = list(self._states[agent_id].desires.values())
        desire_by_desc = {d.description: d for d in desires}
        committed = 0
        for plan_desc, step_dicts in plans_for_agent:
            desire = desire_by_desc.get(plan_desc)
            if desire is None and desires:
                desire = desires[0]
            if desire is None:
                continue
            plan = self.create_plan(
                agent_id,
                goal_id=desire.goal_id,
                steps=step_dicts,
                expected_outcome={"goal": plan_desc},
            )
            self.update_plan(agent_id, plan.plan_id, status=PlanStatus.VALIDATED)
            if committed < 2:
                self.commit_intention(
                    agent_id,
                    goal_id=desire.goal_id,
                    plan_id=plan.plan_id,
                    commitment_strength=0.9 - committed * 0.1,
                )
                committed += 1
        if committed < 3 and desires:
            remaining = [d for d in desires if d.description not in {p[0] for p in plans_for_agent}]
            if remaining:
                self.commit_intention(
                    agent_id,
                    goal_id=remaining[0].goal_id,
                    plan_id=None,
                    commitment_strength=0.5,
                )

    def _seed_relations(self) -> None:
        """Seed the social relations matrix between all agents."""
        relation_matrix = {
            ("Hero", "Villain"): (0.05, 0.0, SocialRole.ENEMY),
            ("Hero", "Mentor"): (0.95, 0.85, SocialRole.MENTEE),
            ("Hero", "Ally"): (0.9, 0.8, SocialRole.ALLY),
            ("Hero", "Rival"): (0.6, 0.45, SocialRole.RIVAL),
            ("Villain", "Hero"): (0.1, 0.05, SocialRole.ENEMY),
            ("Villain", "Mentor"): (0.3, 0.1, SocialRole.RIVAL),
            ("Villain", "Ally"): (0.4, 0.2, SocialRole.LEADER),
            ("Villain", "Rival"): (0.35, 0.15, SocialRole.PEER),
            ("Mentor", "Hero"): (0.9, 0.85, SocialRole.MENTOR),
            ("Mentor", "Villain"): (0.2, 0.1, SocialRole.RIVAL),
            ("Mentor", "Ally"): (0.85, 0.7, SocialRole.MENTOR),
            ("Mentor", "Rival"): (0.55, 0.4, SocialRole.PEER),
            ("Ally", "Hero"): (0.95, 0.9, SocialRole.FOLLOWER),
            ("Ally", "Villain"): (0.15, 0.05, SocialRole.ENEMY),
            ("Ally", "Mentor"): (0.9, 0.8, SocialRole.MENTEE),
            ("Ally", "Rival"): (0.4, 0.3, SocialRole.PEER),
            ("Rival", "Hero"): (0.55, 0.4, SocialRole.RIVAL),
            ("Rival", "Villain"): (0.3, 0.1, SocialRole.PEER),
            ("Rival", "Mentor"): (0.6, 0.45, SocialRole.MENTEE),
            ("Rival", "Ally"): (0.45, 0.35, SocialRole.PEER),
        }
        for (observer, target), (trust, affection, role) in relation_matrix.items():
            self.register_relation(
                observer,
                target,
                trust=trust,
                affection=affection,
                power_relation=role,
                metadata={"seeded": True},
            )


# ---------------------------------------------------------------------------
# Module-level accessor
# ---------------------------------------------------------------------------

def get_unified_cognitive_core() -> _UnifiedCognitiveCore:
    """Get or create the global _UnifiedCognitiveCore singleton instance."""
    return _UnifiedCognitiveCore.get_instance()
