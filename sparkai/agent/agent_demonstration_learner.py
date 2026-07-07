"""
SparkLabs AI-Native Game Engine - Agent Demonstration Learner
=============================================================

Learning from Demonstration (LfD) and Behavior Cloning for AI agents.

This module enables AI agents in the SparkLabs engine to acquire new
behaviors by observing and reproducing expert demonstrations. Rather than
requiring hand-crafted policies or pure reinforcement-learning exploration,
agents can learn directly from recorded trajectories of expert play.

Learning from Demonstration (LfD):
    LfD is a paradigm where an agent learns a policy from a dataset of
    expert demonstrations. Each demonstration is a trajectory -- a sequence
    of (state, action, reward, next_state) transitions recorded while an
    expert (human or AI) solves a task. The agent generalizes from these
    examples to act in similar situations without exploring the full
    state-action space from scratch.

Behavior Cloning:
    Behavior Cloning (BC) is the simplest form of LfD. It treats imitation
    as supervised learning: the demonstrations are converted into
    (state -> action) training pairs, and a model (the "behavior policy")
    is fit to map states to actions. At inference time the policy predicts
    the action most likely taken by the expert given the current state.

Pipeline:
    1. Record demonstrations -- capture expert trajectories step by step.
    2. Finalize demonstrations -- lock them as immutable training data.
    3. Train behavior policies -- fit a policy to one or more demonstrations.
    4. Predict actions -- use a trained policy to choose actions at runtime.
    5. Evaluate policies -- measure accuracy against held-out demonstrations.
    6. Prune low-quality demonstrations -- keep the dataset curated.

Architecture:
    DemonstrationLearnerEngine (thread-safe singleton)
        |-- TrajectoryStep       (single state-action-transition record)
        |-- Demonstration        (ordered trajectory of steps)
        |-- BehaviorPolicy       (trained imitation model)
        |-- PredictionResult     (a single predicted action)
        |-- EvaluationReport     (policy quality metrics)
        |-- ImitationEvent       (observable lifecycle event)
        |-- ImitationStats       (aggregate statistics)
        |-- ImitationSnapshot    (point-in-time state capture)

The engine is a process-wide singleton accessed via ``get_instance()`` or
the module-level ``get_demonstration_learner()`` helper. All public
methods are guarded by a reentrant lock for thread safety. In-memory
stores are bounded by capacity constants and use FIFO eviction so that
the engine never grows without limit.
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

_MAX_DEMONSTRATIONS: int = 2000
_MAX_TRAJECTORY_STEPS: int = 50000
_MAX_POLICIES: int = 200
_MAX_PREDICTIONS: int = 10000
_MAX_EVALUATIONS: int = 1000
_MAX_EVENTS: int = 2000


# ---------------------------------------------------------------------------
# Module-level helper functions
# ---------------------------------------------------------------------------

def _now() -> str:
    """Return the current UTC time as an ISO-8601 string with a 'Z' suffix."""
    return datetime.datetime.utcnow().isoformat() + "Z"


def _new_id() -> str:
    """Return a 16-character hexadecimal identifier."""
    return uuid.uuid4().hex[:16]


def _clamp(value: float, low: float, high: float) -> float:
    """Clamp ``value`` into the inclusive range [low, high]."""
    if value < low:
        return low
    if value > high:
        return high
    return value


def _evict_fifo_dict(store: Dict[str, Any], max_size: int) -> None:
    """Evict the oldest inserted entries from a dict until within bounds.

    Python dicts preserve insertion order (3.7+), so the first key returned
    by iteration is the oldest. This implements FIFO eviction.
    """
    while len(store) > max_size:
        oldest_key = next(iter(store))
        store.pop(oldest_key, None)


def _evict_fifo_list(store: List[Any], max_size: int) -> None:
    """Evict the oldest inserted entries from a list until within bounds."""
    while len(store) > max_size:
        store.pop(0)


# Quality ranking used for pruning comparisons
_QUALITY_RANK: Dict["TrajectoryQuality", int] = {}


# ---------------------------------------------------------------------------
# Domain Enums
# ---------------------------------------------------------------------------

class DemonstrationStatus(Enum):
    """Lifecycle state of a demonstration trajectory.

    Demonstrations progress from a draft through active recording to a
    terminal state (finalized, archived, or discarded).
    """
    DRAFT = "draft"
    RECORDING = "recording"
    FINALIZED = "finalized"
    ARCHIVED = "archived"
    DISCARDED = "discarded"


class TrajectoryQuality(Enum):
    """Quality tier of a demonstration.

    Higher tiers represent more reliable, expert-level demonstrations that
    should be preferred when training behavior policies.
    """
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    EXPERT = "expert"


class DemonstrationSource(Enum):
    """Origin of a demonstration trajectory.

    The source influences how much trust is placed in the demonstration
    when training policies -- human-expert data is typically the gold
    standard, while scripted data may be noisier.
    """
    HUMAN_EXPERT = "human_expert"
    AI_AGENT = "ai_agent"
    RECORDED_GAMEPLAY = "recorded_gameplay"
    TELEOPERATION = "teleoperation"
    SCRIPTED = "scripted"


class PolicyType(Enum):
    """Underlying model family of a behavior policy.

    Different policy types have different sample complexity, latency, and
    expressiveness trade-offs. The engine does not implement full training
    for each family; it records the type and computes heuristic accuracy.
    """
    NEAREST_NEIGHBOR = "nearest_neighbor"
    DECISION_TREE = "decision_tree"
    LINEAR_MODEL = "linear_model"
    NEURAL_NETWORK = "neural_network"
    GAUSSIAN_PROCESS = "gaussian_process"
    SEQUENCE_MODEL = "sequence_model"
    ENSEMBLE = "ensemble"


class PolicyStatus(Enum):
    """Lifecycle state of a behavior policy."""
    TRAINING = "training"
    READY = "ready"
    STALE = "stale"
    FAILED = "failed"


class ImitationEventKind(Enum):
    """Kinds of events emitted by the demonstration learner.

    Events form an observable audit trail of the imitation-learning
    lifecycle without coupling observers to internal data structures.
    """
    DEMONSTRATION_STARTED = "demonstration_started"
    STEP_ADDED = "step_added"
    DEMONSTRATION_FINALIZED = "demonstration_finalized"
    POLICY_TRAINED = "policy_trained"
    PREDICTION_MADE = "prediction_made"
    EVALUATION_COMPLETED = "evaluation_completed"
    DEMONSTRATION_PRUNED = "demonstration_pruned"


# Populate the quality ranking now that the enum is defined
_QUALITY_RANK = {
    TrajectoryQuality.LOW: 0,
    TrajectoryQuality.MEDIUM: 1,
    TrajectoryQuality.HIGH: 2,
    TrajectoryQuality.EXPERT: 3,
}


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------

@dataclass
class TrajectoryStep:
    """A single state-action-transition within a demonstration.

    Each step captures the observed state, the action taken by the expert,
    the resulting reward, the next state, and whether the trajectory
    terminated after this step.

    Attributes:
        step_id: Unique step identifier.
        demonstration_id: Parent demonstration identifier.
        sequence_index: Zero-based position of this step in the trajectory.
        state: The observed world state before the action.
        action: The action performed by the demonstrator.
        reward: Scalar reward received for this transition.
        next_state: The world state after the action was applied.
        done: Whether the trajectory ended after this step.
        timestamp: ISO-8601 UTC creation timestamp.
        metadata: Optional auxiliary metadata bag.
    """
    step_id: str = field(default_factory=_new_id)
    demonstration_id: str = ""
    sequence_index: int = 0
    state: Dict[str, Any] = field(default_factory=dict)
    action: Dict[str, Any] = field(default_factory=dict)
    reward: float = 0.0
    next_state: Dict[str, Any] = field(default_factory=dict)
    done: bool = False
    timestamp: str = field(default_factory=_now)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "step_id": self.step_id,
            "demonstration_id": self.demonstration_id,
            "sequence_index": self.sequence_index,
            "state": dict(self.state),
            "action": dict(self.action),
            "reward": self.reward,
            "next_state": dict(self.next_state),
            "done": self.done,
            "timestamp": self.timestamp,
            "metadata": dict(self.metadata),
        }


@dataclass
class Demonstration:
    """An ordered trajectory of expert state-action transitions.

    A demonstration is the fundamental training unit for behavior cloning.
    It is recorded step-by-step, then finalized to produce immutable
    training data.

    Attributes:
        demonstration_id: Unique demonstration identifier.
        name: Human-readable name.
        agent_id: The agent this demonstration is intended for.
        domain: Problem domain (e.g. "combat", "stealth", "puzzle").
        source: Where the demonstration came from.
        quality: Assessed quality tier.
        status: Current lifecycle state.
        steps: Ordered list of trajectory steps.
        total_reward: Sum of step rewards.
        duration_seconds: Wall-clock duration of the recording.
        created_at: ISO-8601 UTC creation timestamp.
        finalized_at: ISO-8601 UTC finalization timestamp, or None.
        metadata: Optional auxiliary metadata bag.
    """
    demonstration_id: str = field(default_factory=_new_id)
    name: str = ""
    agent_id: str = ""
    domain: str = ""
    source: DemonstrationSource = DemonstrationSource.SCRIPTED
    quality: TrajectoryQuality = TrajectoryQuality.MEDIUM
    status: DemonstrationStatus = DemonstrationStatus.DRAFT
    steps: List[TrajectoryStep] = field(default_factory=list)
    total_reward: float = 0.0
    duration_seconds: float = 0.0
    created_at: str = field(default_factory=_now)
    finalized_at: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "demonstration_id": self.demonstration_id,
            "name": self.name,
            "agent_id": self.agent_id,
            "domain": self.domain,
            "source": self.source.value,
            "quality": self.quality.value,
            "status": self.status.value,
            "steps": [s.to_dict() for s in self.steps],
            "total_reward": self.total_reward,
            "duration_seconds": self.duration_seconds,
            "created_at": self.created_at,
            "finalized_at": self.finalized_at,
            "metadata": dict(self.metadata),
        }


@dataclass
class BehaviorPolicy:
    """A trained imitation model that maps states to actions.

    A behavior policy is produced by fitting a model to one or more
    finalized demonstrations. It can then be queried to predict the
    action an expert would take in a given state.

    Attributes:
        policy_id: Unique policy identifier.
        name: Human-readable name.
        agent_id: The agent this policy serves.
        domain: Problem domain the policy was trained for.
        policy_type: Underlying model family.
        status: Current lifecycle state.
        source_demonstration_ids: Demos used to train this policy.
        training_accuracy: Accuracy on the training demonstrations.
        validation_accuracy: Accuracy on held-out data.
        parameters: Model hyper-parameters and configuration.
        trained_at: ISO-8601 UTC training timestamp.
        prediction_count: Number of predictions made with this policy.
        metadata: Optional auxiliary metadata bag.
    """
    policy_id: str = field(default_factory=_new_id)
    name: str = ""
    agent_id: str = ""
    domain: str = ""
    policy_type: PolicyType = PolicyType.NEAREST_NEIGHBOR
    status: PolicyStatus = PolicyStatus.TRAINING
    source_demonstration_ids: List[str] = field(default_factory=list)
    training_accuracy: float = 0.0
    validation_accuracy: float = 0.0
    parameters: Dict[str, Any] = field(default_factory=dict)
    trained_at: str = field(default_factory=_now)
    prediction_count: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "policy_id": self.policy_id,
            "name": self.name,
            "agent_id": self.agent_id,
            "domain": self.domain,
            "policy_type": self.policy_type.value,
            "status": self.status.value,
            "source_demonstration_ids": list(self.source_demonstration_ids),
            "training_accuracy": round(self.training_accuracy, 6),
            "validation_accuracy": round(self.validation_accuracy, 6),
            "parameters": dict(self.parameters),
            "trained_at": self.trained_at,
            "prediction_count": self.prediction_count,
            "metadata": dict(self.metadata),
        }


@dataclass
class PredictionResult:
    """A single action prediction produced by a behavior policy.

    Attributes:
        prediction_id: Unique prediction identifier.
        policy_id: The policy that produced this prediction.
        input_state: The state that was queried.
        predicted_action: The action the policy selected.
        confidence: Confidence score in [0.0, 1.0].
        alternatives: Ranked list of alternative actions with scores.
        timestamp: ISO-8601 UTC prediction timestamp.
    """
    prediction_id: str = field(default_factory=_new_id)
    policy_id: str = ""
    input_state: Dict[str, Any] = field(default_factory=dict)
    predicted_action: Dict[str, Any] = field(default_factory=dict)
    confidence: float = 0.0
    alternatives: List[Dict[str, Any]] = field(default_factory=list)
    timestamp: str = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "prediction_id": self.prediction_id,
            "policy_id": self.policy_id,
            "input_state": dict(self.input_state),
            "predicted_action": dict(self.predicted_action),
            "confidence": round(self.confidence, 6),
            "alternatives": [dict(a) for a in self.alternatives],
            "timestamp": self.timestamp,
        }


@dataclass
class EvaluationReport:
    """Quality metrics for a behavior policy against test demonstrations.

    Attributes:
        evaluation_id: Unique evaluation identifier.
        policy_id: The policy that was evaluated.
        test_demonstration_ids: Demos used as the test set.
        accuracy: Fraction of correctly predicted actions.
        loss: Complementary loss (1 - accuracy).
        per_step_accuracy: Accuracy at each trajectory sequence index.
        confusion: Mapping of actual action type to predicted action counts.
        evaluated_at: ISO-8601 UTC evaluation timestamp.
    """
    evaluation_id: str = field(default_factory=_new_id)
    policy_id: str = ""
    test_demonstration_ids: List[str] = field(default_factory=list)
    accuracy: float = 0.0
    loss: float = 1.0
    per_step_accuracy: List[float] = field(default_factory=list)
    confusion: Dict[str, Dict[str, int]] = field(default_factory=dict)
    evaluated_at: str = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "evaluation_id": self.evaluation_id,
            "policy_id": self.policy_id,
            "test_demonstration_ids": list(self.test_demonstration_ids),
            "accuracy": round(self.accuracy, 6),
            "loss": round(self.loss, 6),
            "per_step_accuracy": [round(a, 6) for a in self.per_step_accuracy],
            "confusion": {
                k: dict(v) for k, v in self.confusion.items()
            },
            "evaluated_at": self.evaluated_at,
        }


@dataclass
class ImitationStats:
    """Aggregate statistics across all imitation-learning artifacts.

    Attributes:
        total_demonstrations: Number of stored demonstrations.
        total_steps: Total number of trajectory steps across all demos.
        total_policies: Number of stored behavior policies.
        total_predictions: Number of predictions made.
        total_evaluations: Number of evaluations performed.
        avg_training_accuracy: Mean training accuracy across policies.
        avg_validation_accuracy: Mean validation accuracy across policies.
    """
    total_demonstrations: int = 0
    total_steps: int = 0
    total_policies: int = 0
    total_predictions: int = 0
    total_evaluations: int = 0
    avg_training_accuracy: float = 0.0
    avg_validation_accuracy: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_demonstrations": self.total_demonstrations,
            "total_steps": self.total_steps,
            "total_policies": self.total_policies,
            "total_predictions": self.total_predictions,
            "total_evaluations": self.total_evaluations,
            "avg_training_accuracy": round(self.avg_training_accuracy, 6),
            "avg_validation_accuracy": round(self.avg_validation_accuracy, 6),
        }


@dataclass
class ImitationSnapshot:
    """Point-in-time snapshot of the entire engine state.

    Attributes:
        initialized: Whether the engine has completed initialization.
        demonstrations: Serialized demonstrations at snapshot time.
        policies: Serialized policies at snapshot time.
        predictions: Serialized predictions at snapshot time.
        evaluations: Serialized evaluations at snapshot time.
        events: Serialized events at snapshot time.
        stats: Aggregate statistics at snapshot time.
    """
    initialized: bool = False
    demonstrations: List[Dict[str, Any]] = field(default_factory=list)
    policies: List[Dict[str, Any]] = field(default_factory=list)
    predictions: List[Dict[str, Any]] = field(default_factory=list)
    evaluations: List[Dict[str, Any]] = field(default_factory=list)
    events: List[Dict[str, Any]] = field(default_factory=list)
    stats: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "initialized": self.initialized,
            "demonstrations": list(self.demonstrations),
            "policies": list(self.policies),
            "predictions": list(self.predictions),
            "evaluations": list(self.evaluations),
            "events": list(self.events),
            "stats": dict(self.stats),
        }


@dataclass
class ImitationEvent:
    """An observable event in the imitation-learning lifecycle.

    Attributes:
        event_id: Unique event identifier.
        kind: The kind of event that occurred.
        timestamp: ISO-8601 UTC event timestamp.
        payload: Event-specific details.
    """
    event_id: str = field(default_factory=_new_id)
    kind: ImitationEventKind = ImitationEventKind.STEP_ADDED
    timestamp: str = field(default_factory=_now)
    payload: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": self.event_id,
            "kind": self.kind.value,
            "timestamp": self.timestamp,
            "payload": dict(self.payload),
        }


# ---------------------------------------------------------------------------
# Engine
# ---------------------------------------------------------------------------

class DemonstrationLearnerEngine:
    """Learning-from-Demonstration and Behavior-Cloning engine.

    Manages the full imitation-learning lifecycle: recording expert
    demonstrations, training behavior policies from them, predicting
    actions at runtime, and evaluating policy quality. The engine is a
    thread-safe singleton accessed via ``get_instance()`` or the
    module-level ``get_demonstration_learner()`` helper.

    All in-memory stores are bounded by capacity constants and use FIFO
    eviction so the engine never grows without limit. Public methods are
    guarded by a reentrant lock for thread safety.
    """

    _instance: Optional["DemonstrationLearnerEngine"] = None
    _lock: threading.RLock = threading.RLock()

    def __new__(cls) -> "DemonstrationLearnerEngine":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    instance = super().__new__(cls)
                    instance._initialized = False
                    cls._instance = instance
        return cls._instance

    @classmethod
    def get_instance(cls) -> "DemonstrationLearnerEngine":
        """Return the singleton DemonstrationLearnerEngine instance.

        Uses double-checked locking so that calls after initialization take
        the fast path without acquiring the lock. Does NOT reset
        ``_initialized``; only constructs the singleton if it is absent.
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
        with self._lock:
            if self._initialized:
                return

            # Demonstration storage keyed by demonstration id
            self._demonstrations: Dict[str, Demonstration] = {}

            # Policy storage keyed by policy id
            self._policies: Dict[str, BehaviorPolicy] = {}

            # Prediction storage keyed by prediction id
            self._predictions: Dict[str, PredictionResult] = {}

            # Evaluation storage keyed by evaluation id
            self._evaluations: Dict[str, EvaluationReport] = {}

            # Observable event log
            self._events: List[ImitationEvent] = []

            # Monotonic counters for diagnostics
            self._demonstration_counter: int = 0
            self._policy_counter: int = 0
            self._prediction_counter: int = 0
            self._evaluation_counter: int = 0

            # Mark initialization complete, then seed baseline data
            self._initialized: bool = True
            self._seed_data()

    # ------------------------------------------------------------------
    # Seed Data
    # ------------------------------------------------------------------

    def _seed_data(self) -> None:
        """Populate the engine with baseline demonstrations and policies.

        This gives the learner a non-empty starting state so that policy
        training, prediction, and evaluation have data to operate on
        immediately after construction or reset.
        """
        now = _now()

        # --- Demonstration 1: Combat Sword Combo -----------------------
        combat_demo_id = _new_id()
        combat_steps = [
            TrajectoryStep(
                step_id=_new_id(),
                demonstration_id=combat_demo_id,
                sequence_index=0,
                state={
                    "position": [0.0, 0.0, 0.0],
                    "enemy_distance": 2.5,
                    "agent_health": 100,
                    "enemy_health": 100,
                },
                action={"type": "attack", "weapon": "sword", "target": "enemy"},
                reward=10.0,
                next_state={
                    "position": [0.5, 0.0, 0.0],
                    "enemy_distance": 1.5,
                    "enemy_health": 80,
                },
                done=False,
                timestamp=now,
                metadata={"combo_step": 1},
            ),
            TrajectoryStep(
                step_id=_new_id(),
                demonstration_id=combat_demo_id,
                sequence_index=1,
                state={
                    "position": [0.5, 0.0, 0.0],
                    "enemy_distance": 1.5,
                    "agent_health": 100,
                    "enemy_health": 80,
                },
                action={"type": "dodge", "direction": "right", "distance": 1.0},
                reward=5.0,
                next_state={
                    "position": [1.0, 0.0, 0.0],
                    "enemy_distance": 2.0,
                    "agent_health": 100,
                },
                done=False,
                timestamp=now,
                metadata={"combo_step": 2},
            ),
            TrajectoryStep(
                step_id=_new_id(),
                demonstration_id=combat_demo_id,
                sequence_index=2,
                state={
                    "position": [1.0, 0.0, 0.0],
                    "enemy_distance": 2.0,
                    "enemy_health": 80,
                },
                action={"type": "attack", "weapon": "sword", "stance": "aggressive"},
                reward=12.0,
                next_state={
                    "enemy_distance": 1.8,
                    "enemy_health": 50,
                },
                done=False,
                timestamp=now,
                metadata={"combo_step": 3},
            ),
            TrajectoryStep(
                step_id=_new_id(),
                demonstration_id=combat_demo_id,
                sequence_index=3,
                state={
                    "position": [1.0, 0.0, 0.0],
                    "enemy_distance": 1.0,
                    "enemy_attacking": True,
                },
                action={"type": "parry", "weapon": "sword", "timing": "perfect"},
                reward=8.0,
                next_state={
                    "enemy_stunned": True,
                    "enemy_health": 50,
                },
                done=False,
                timestamp=now,
                metadata={"combo_step": 4},
            ),
            TrajectoryStep(
                step_id=_new_id(),
                demonstration_id=combat_demo_id,
                sequence_index=4,
                state={
                    "enemy_stunned": True,
                    "enemy_health": 50,
                },
                action={"type": "finisher", "weapon": "sword", "damage": 50},
                reward=50.0,
                next_state={
                    "enemy_health": 0,
                    "enemy_dead": True,
                },
                done=True,
                timestamp=now,
                metadata={"combo_step": 5, "victory": True},
            ),
        ]
        combat_demo = Demonstration(
            demonstration_id=combat_demo_id,
            name="Combat Sword Combo",
            agent_id="agent_alpha",
            domain="combat",
            source=DemonstrationSource.HUMAN_EXPERT,
            quality=TrajectoryQuality.EXPERT,
            status=DemonstrationStatus.FINALIZED,
            steps=combat_steps,
            total_reward=sum(s.reward for s in combat_steps),
            duration_seconds=2.5,
            created_at=now,
            finalized_at=now,
            metadata={"difficulty": "hard", "enemy_type": "boss"},
        )
        self._demonstrations[combat_demo_id] = combat_demo
        self._demonstration_counter += 1

        # --- Demonstration 2: Stealth Infiltration ---------------------
        stealth_demo_id = _new_id()
        stealth_steps = [
            TrajectoryStep(
                step_id=_new_id(),
                demonstration_id=stealth_demo_id,
                sequence_index=0,
                state={
                    "position": [10.0, 0.0, 0.0],
                    "guards_visible": 2,
                    "alert_level": 0.0,
                },
                action={"type": "sneak", "direction": "north", "speed": "slow"},
                reward=6.0,
                next_state={
                    "position": [10.0, 2.0, 0.0],
                    "alert_level": 0.0,
                },
                done=False,
                timestamp=now,
                metadata={"stealth_mode": True},
            ),
            TrajectoryStep(
                step_id=_new_id(),
                demonstration_id=stealth_demo_id,
                sequence_index=1,
                state={
                    "position": [10.0, 2.0, 0.0],
                    "guards_visible": 1,
                    "alert_level": 0.0,
                },
                action={"type": "hide", "cover": "crate", "duration": 3.0},
                reward=9.0,
                next_state={
                    "alert_level": 0.0,
                    "hidden": True,
                },
                done=False,
                timestamp=now,
                metadata={"stealth_mode": True},
            ),
            TrajectoryStep(
                step_id=_new_id(),
                demonstration_id=stealth_demo_id,
                sequence_index=2,
                state={
                    "position": [10.0, 2.0, 0.0],
                    "guards_visible": 1,
                    "alert_level": 0.0,
                    "hidden": True,
                },
                action={"type": "distract", "method": "throw", "target": "bottle"},
                reward=7.0,
                next_state={
                    "guard_distracted": True,
                    "alert_level": 0.1,
                },
                done=False,
                timestamp=now,
                metadata={"stealth_mode": True},
            ),
            TrajectoryStep(
                step_id=_new_id(),
                demonstration_id=stealth_demo_id,
                sequence_index=3,
                state={
                    "guard_distracted": True,
                    "alert_level": 0.1,
                    "target_in_range": True,
                },
                action={"type": "takedown", "method": "silent", "target": "guard"},
                reward=40.0,
                next_state={
                    "guard_neutralized": True,
                    "alert_level": 0.0,
                },
                done=True,
                timestamp=now,
                metadata={"stealth_mode": True, "objective_complete": True},
            ),
        ]
        stealth_demo = Demonstration(
            demonstration_id=stealth_demo_id,
            name="Stealth Infiltration",
            agent_id="agent_beta",
            domain="stealth",
            source=DemonstrationSource.RECORDED_GAMEPLAY,
            quality=TrajectoryQuality.HIGH,
            status=DemonstrationStatus.FINALIZED,
            steps=stealth_steps,
            total_reward=sum(s.reward for s in stealth_steps),
            duration_seconds=8.0,
            created_at=now,
            finalized_at=now,
            metadata={"difficulty": "medium", "map": "warehouse"},
        )
        self._demonstrations[stealth_demo_id] = stealth_demo
        self._demonstration_counter += 1

        # --- Demonstration 3: Puzzle Solution --------------------------
        puzzle_demo_id = _new_id()
        puzzle_steps = [
            TrajectoryStep(
                step_id=_new_id(),
                demonstration_id=puzzle_demo_id,
                sequence_index=0,
                state={
                    "puzzle_id": "logic_gate_3",
                    "solved": False,
                    "attempts": 0,
                },
                action={"type": "examine", "target": "panel"},
                reward=2.0,
                next_state={
                    "panel_examined": True,
                    "clues_found": 1,
                },
                done=False,
                timestamp=now,
                metadata={"cognitive": True},
            ),
            TrajectoryStep(
                step_id=_new_id(),
                demonstration_id=puzzle_demo_id,
                sequence_index=1,
                state={
                    "panel_examined": True,
                    "clues_found": 1,
                },
                action={"type": "interact", "target": "lever_1", "value": "on"},
                reward=4.0,
                next_state={
                    "lever_1": "on",
                    "clues_found": 2,
                },
                done=False,
                timestamp=now,
                metadata={"cognitive": True},
            ),
            TrajectoryStep(
                step_id=_new_id(),
                demonstration_id=puzzle_demo_id,
                sequence_index=2,
                state={
                    "lever_1": "on",
                    "clues_found": 2,
                },
                action={"type": "interact", "target": "lever_2", "value": "on"},
                reward=6.0,
                next_state={
                    "lever_1": "on",
                    "lever_2": "on",
                    "progress": 0.66,
                },
                done=False,
                timestamp=now,
                metadata={"cognitive": True},
            ),
        ]
        puzzle_demo = Demonstration(
            demonstration_id=puzzle_demo_id,
            name="Puzzle Solution",
            agent_id="agent_alpha",
            domain="puzzle",
            source=DemonstrationSource.AI_AGENT,
            quality=TrajectoryQuality.MEDIUM,
            status=DemonstrationStatus.RECORDING,
            steps=puzzle_steps,
            total_reward=sum(s.reward for s in puzzle_steps),
            duration_seconds=5.0,
            created_at=now,
            finalized_at=None,
            metadata={"difficulty": "easy", "puzzle_type": "logic"},
        )
        self._demonstrations[puzzle_demo_id] = puzzle_demo
        self._demonstration_counter += 1

        # --- Policy 1: Combat Imitation Policy v1 ---------------------
        combat_policy_id = _new_id()
        combat_policy = BehaviorPolicy(
            policy_id=combat_policy_id,
            name="Combat Imitation Policy v1",
            agent_id="agent_alpha",
            domain="combat",
            policy_type=PolicyType.NEAREST_NEIGHBOR,
            status=PolicyStatus.READY,
            source_demonstration_ids=[combat_demo_id],
            training_accuracy=0.85,
            validation_accuracy=0.78,
            parameters={
                "k_neighbors": 5,
                "distance_metric": "euclidean",
                "state_keys": ["position", "enemy_distance", "enemy_health"],
            },
            trained_at=now,
            prediction_count=0,
            metadata={"version": "1.0", "seeded": True},
        )
        self._policies[combat_policy_id] = combat_policy
        self._policy_counter += 1

        # --- Policy 2: Stealth Behavior Clone -------------------------
        stealth_policy_id = _new_id()
        stealth_policy = BehaviorPolicy(
            policy_id=stealth_policy_id,
            name="Stealth Behavior Clone",
            agent_id="agent_beta",
            domain="stealth",
            policy_type=PolicyType.DECISION_TREE,
            status=PolicyStatus.READY,
            source_demonstration_ids=[stealth_demo_id],
            training_accuracy=0.78,
            validation_accuracy=0.71,
            parameters={
                "max_depth": 8,
                "min_samples_leaf": 2,
                "criterion": "gini",
                "state_keys": ["position", "alert_level", "guards_visible"],
            },
            trained_at=now,
            prediction_count=0,
            metadata={"version": "1.0", "seeded": True},
        )
        self._policies[stealth_policy_id] = stealth_policy
        self._policy_counter += 1

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _now() -> str:
        """Return the current UTC time as an ISO-8601 string with 'Z' suffix."""
        return datetime.datetime.utcnow().isoformat() + "Z"

    def _record_event(
        self,
        kind: ImitationEventKind,
        payload: Dict[str, Any],
    ) -> ImitationEvent:
        """Record an observable event in the lifecycle log.

        This is an internal helper and assumes the caller already holds the
        lock (RLock is reentrant, so acquiring here is also safe).
        """
        event = ImitationEvent(
            event_id=_new_id(),
            kind=kind,
            timestamp=_now(),
            payload=dict(payload),
        )
        self._events.append(event)
        _evict_fifo_list(self._events, _MAX_EVENTS)
        return event

    @staticmethod
    def _state_similarity(a: Dict[str, Any], b: Dict[str, Any]) -> float:
        """Compute a similarity score in [0, 1] between two state dicts.

        Rewards overlapping keys with equal values, and gives partial
        credit for numerically close values.
        """
        if not a or not b:
            return 0.0
        common = set(a.keys()) & set(b.keys())
        if not common:
            return 0.0
        score = 0.0
        for key in common:
            av, bv = a[key], b[key]
            if av == bv:
                score += 1.0
            elif isinstance(av, (int, float)) and isinstance(bv, (int, float)):
                diff = abs(av - bv)
                score += max(0.0, 1.0 - diff)
        return score / len(common)

    def _collect_training_pairs(
        self, policy: BehaviorPolicy
    ) -> List[tuple]:
        """Collect (state, action) training pairs from a policy's source demos."""
        pairs: List[tuple] = []
        for demo_id in policy.source_demonstration_ids:
            demo = self._demonstrations.get(demo_id)
            if demo is None:
                continue
            for step in demo.steps:
                pairs.append((step.state, step.action))
        return pairs

    # ------------------------------------------------------------------
    # Demonstration management
    # ------------------------------------------------------------------

    def record_demonstration(
        self,
        name: str,
        agent_id: str,
        domain: str,
        source: DemonstrationSource,
        quality: TrajectoryQuality,
    ) -> Demonstration:
        """Create a new demonstration in the DRAFT state.

        The returned demonstration has no steps yet; use
        ``add_trajectory_step`` to append transitions.
        """
        with self._lock:
            demo = Demonstration(
                demonstration_id=_new_id(),
                name=name,
                agent_id=agent_id,
                domain=domain,
                source=source,
                quality=quality,
                status=DemonstrationStatus.DRAFT,
                steps=[],
                total_reward=0.0,
                duration_seconds=0.0,
                created_at=_now(),
                finalized_at=None,
                metadata={},
            )
            self._demonstrations[demo.demonstration_id] = demo
            self._demonstration_counter += 1
            _evict_fifo_dict(self._demonstrations, _MAX_DEMONSTRATIONS)
            self._record_event(
                ImitationEventKind.DEMONSTRATION_STARTED,
                {
                    "demonstration_id": demo.demonstration_id,
                    "name": name,
                    "agent_id": agent_id,
                    "domain": domain,
                    "source": source.value,
                    "quality": quality.value,
                },
            )
            return demo

    def list_demonstrations(
        self,
        agent_id: Optional[str] = None,
        domain: Optional[str] = None,
        status: Optional[DemonstrationStatus] = None,
        source: Optional[DemonstrationSource] = None,
    ) -> List[Demonstration]:
        """Return demonstrations filtered by the provided criteria.

        Filters are AND-combined; a None filter means "do not filter on
        this field".
        """
        with self._lock:
            results: List[Demonstration] = []
            for demo in self._demonstrations.values():
                if agent_id is not None and demo.agent_id != agent_id:
                    continue
                if domain is not None and demo.domain != domain:
                    continue
                if status is not None and demo.status != status:
                    continue
                if source is not None and demo.source != source:
                    continue
                results.append(demo)
            return results

    def get_demonstration(
        self, demonstration_id: str
    ) -> Optional[Demonstration]:
        """Return the demonstration with the given id, or None if absent."""
        with self._lock:
            return self._demonstrations.get(demonstration_id)

    def add_trajectory_step(
        self,
        demonstration_id: str,
        state: Dict[str, Any],
        action: Dict[str, Any],
        reward: float,
        next_state: Dict[str, Any],
        done: bool,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Optional[TrajectoryStep]:
        """Append a trajectory step to an existing demonstration.

        Updates the demonstration status to RECORDING, accumulates the
        reward into ``total_reward``, and advances the duration. Returns
        the created step, or None if the demonstration does not exist.
        """
        with self._lock:
            demo = self._demonstrations.get(demonstration_id)
            if demo is None:
                return None

            step = TrajectoryStep(
                step_id=_new_id(),
                demonstration_id=demonstration_id,
                sequence_index=len(demo.steps),
                state=dict(state),
                action=dict(action),
                reward=float(reward),
                next_state=dict(next_state),
                done=bool(done),
                timestamp=_now(),
                metadata=dict(metadata) if metadata else {},
            )
            demo.steps.append(step)
            # Enforce per-demonstration step cap with FIFO eviction
            _evict_fifo_list(demo.steps, _MAX_TRAJECTORY_STEPS)

            # Update aggregate fields
            demo.total_reward = sum(s.reward for s in demo.steps)
            demo.duration_seconds = len(demo.steps) * 0.1
            if demo.status == DemonstrationStatus.DRAFT:
                demo.status = DemonstrationStatus.RECORDING

            self._record_event(
                ImitationEventKind.STEP_ADDED,
                {
                    "demonstration_id": demonstration_id,
                    "step_id": step.step_id,
                    "sequence_index": step.sequence_index,
                    "reward": step.reward,
                    "done": step.done,
                },
            )
            return step

    def finalize_demonstration(
        self,
        demonstration_id: str,
        quality: Optional[TrajectoryQuality] = None,
    ) -> Optional[Demonstration]:
        """Mark a demonstration as FINALIZED and immutable.

        Optionally upgrades the quality tier. Returns the updated
        demonstration, or None if it does not exist.
        """
        with self._lock:
            demo = self._demonstrations.get(demonstration_id)
            if demo is None:
                return None

            demo.status = DemonstrationStatus.FINALIZED
            demo.finalized_at = _now()
            if quality is not None:
                demo.quality = quality

            self._record_event(
                ImitationEventKind.DEMONSTRATION_FINALIZED,
                {
                    "demonstration_id": demonstration_id,
                    "quality": demo.quality.value,
                    "step_count": len(demo.steps),
                    "total_reward": demo.total_reward,
                },
            )
            return demo

    def archive_demonstration(
        self, demonstration_id: str
    ) -> Optional[Demonstration]:
        """Mark a demonstration as ARCHIVED.

        Archived demonstrations are retained but excluded from new policy
        training by convention. Returns the updated demonstration, or
        None if it does not exist.
        """
        with self._lock:
            demo = self._demonstrations.get(demonstration_id)
            if demo is None:
                return None
            demo.status = DemonstrationStatus.ARCHIVED
            return demo

    def discard_demonstration(
        self, demonstration_id: str
    ) -> Optional[Demonstration]:
        """Mark a demonstration as DISCARDED.

        Discarded demonstrations are retained for audit but should not be
        used for training. Returns the updated demonstration, or None if
        it does not exist.
        """
        with self._lock:
            demo = self._demonstrations.get(demonstration_id)
            if demo is None:
                return None
            demo.status = DemonstrationStatus.DISCARDED
            return demo

    # ------------------------------------------------------------------
    # Policy training and management
    # ------------------------------------------------------------------

    def train_policy(
        self,
        name: str,
        agent_id: str,
        domain: str,
        policy_type: PolicyType,
        source_demonstration_ids: List[str],
        parameters: Optional[Dict[str, Any]] = None,
    ) -> BehaviorPolicy:
        """Train a behavior policy from finalized demonstrations.

        The training accuracy is computed heuristically from the number of
        source demonstrations, how many are finalized and domain-matched,
        and the total number of trajectory steps available. The policy is
        created in the READY state.
        """
        with self._lock:
            total_demos = len(source_demonstration_ids)
            matched_demos = 0
            total_steps = 0

            for demo_id in source_demonstration_ids:
                demo = self._demonstrations.get(demo_id)
                if demo is None:
                    continue
                if (
                    demo.status == DemonstrationStatus.FINALIZED
                    and demo.domain == domain
                ):
                    matched_demos += 1
                total_steps += len(demo.steps)

            # Heuristic accuracy: base 0.4 + domain-match contribution +
            # step-volume contribution. More finalized, domain-matched
            # demonstrations with more steps yield higher accuracy.
            domain_match_ratio = (
                matched_demos / total_demos if total_demos > 0 else 0.0
            )
            step_factor = min(1.0, total_steps / 100.0)
            training_accuracy = _clamp(
                0.4 + 0.3 * domain_match_ratio + 0.3 * step_factor,
                0.0,
                1.0,
            )
            # Validation accuracy is slightly lower than training accuracy
            validation_accuracy = _clamp(
                training_accuracy * 0.9, 0.0, 1.0
            )

            policy = BehaviorPolicy(
                policy_id=_new_id(),
                name=name,
                agent_id=agent_id,
                domain=domain,
                policy_type=policy_type,
                status=PolicyStatus.READY,
                source_demonstration_ids=list(source_demonstration_ids),
                training_accuracy=training_accuracy,
                validation_accuracy=validation_accuracy,
                parameters=dict(parameters) if parameters else {},
                trained_at=_now(),
                prediction_count=0,
                metadata={"training_step_count": total_steps},
            )
            self._policies[policy.policy_id] = policy
            self._policy_counter += 1
            _evict_fifo_dict(self._policies, _MAX_POLICIES)

            self._record_event(
                ImitationEventKind.POLICY_TRAINED,
                {
                    "policy_id": policy.policy_id,
                    "name": name,
                    "agent_id": agent_id,
                    "domain": domain,
                    "policy_type": policy_type.value,
                    "training_accuracy": round(training_accuracy, 6),
                    "source_demonstration_ids": list(source_demonstration_ids),
                },
            )
            return policy

    def list_policies(
        self,
        agent_id: Optional[str] = None,
        domain: Optional[str] = None,
        status: Optional[PolicyStatus] = None,
    ) -> List[BehaviorPolicy]:
        """Return policies filtered by the provided criteria.

        Filters are AND-combined; a None filter means "do not filter on
        this field".
        """
        with self._lock:
            results: List[BehaviorPolicy] = []
            for policy in self._policies.values():
                if agent_id is not None and policy.agent_id != agent_id:
                    continue
                if domain is not None and policy.domain != domain:
                    continue
                if status is not None and policy.status != status:
                    continue
                results.append(policy)
            return results

    def get_policy(self, policy_id: str) -> Optional[BehaviorPolicy]:
        """Return the policy with the given id, or None if absent."""
        with self._lock:
            return self._policies.get(policy_id)

    # ------------------------------------------------------------------
    # Prediction
    # ------------------------------------------------------------------

    def predict_action(
        self,
        policy_id: str,
        input_state: Dict[str, Any],
    ) -> Optional[PredictionResult]:
        """Predict the action a trained policy would take in a given state.

        The predicted action is synthesized by finding the training pair
        whose state is most similar to ``input_state`` and returning its
        action. Confidence is derived from the policy's training accuracy
        and the diversity of its training data. Increments the policy's
        prediction count.
        """
        with self._lock:
            policy = self._policies.get(policy_id)
            if policy is None:
                return None

            training_pairs = self._collect_training_pairs(policy)

            if not training_pairs:
                # No training data; produce a low-confidence default action
                predicted_action: Dict[str, Any] = {
                    "type": "idle",
                    "reason": "no_training_data",
                }
                confidence = 0.0
                alternatives: List[Dict[str, Any]] = []
            else:
                # Find the most similar training state
                best_pair = None
                best_score = -1.0
                scores: List[tuple] = []
                for state, action in training_pairs:
                    sim = self._state_similarity(input_state, state)
                    scores.append((sim, action))
                    if sim > best_score:
                        best_score = sim
                        best_pair = (state, action)

                predicted_action = (
                    dict(best_pair[1]) if best_pair else {"type": "idle"}
                )

                # Compute step diversity: ratio of unique action types to
                # total training pairs.
                unique_types = {
                    a.get("type", "unknown") for _, a in training_pairs
                }
                step_diversity = len(unique_types) / len(training_pairs)
                confidence = _clamp(
                    policy.training_accuracy
                    * (0.5 + 0.5 * step_diversity)
                    * (0.5 + 0.5 * best_score),
                    0.0,
                    1.0,
                )

                # Build alternatives from the next-best actions
                scores.sort(key=lambda x: x[0], reverse=True)
                seen_types = set()
                alternatives = []
                for sim, action in scores:
                    atype = action.get("type", "unknown")
                    if atype in seen_types:
                        continue
                    seen_types.add(atype)
                    alternatives.append({
                        "action": dict(action),
                        "score": round(sim, 6),
                    })
                    if len(alternatives) >= 3:
                        break

            prediction = PredictionResult(
                prediction_id=_new_id(),
                policy_id=policy_id,
                input_state=dict(input_state),
                predicted_action=predicted_action,
                confidence=confidence,
                alternatives=alternatives,
                timestamp=_now(),
            )
            self._predictions[prediction.prediction_id] = prediction
            self._prediction_counter += 1
            _evict_fifo_dict(self._predictions, _MAX_PREDICTIONS)

            # Increment the policy's prediction count
            policy.prediction_count += 1

            self._record_event(
                ImitationEventKind.PREDICTION_MADE,
                {
                    "prediction_id": prediction.prediction_id,
                    "policy_id": policy_id,
                    "confidence": round(confidence, 6),
                    "action_type": predicted_action.get("type", "unknown"),
                },
            )
            return prediction

    def list_predictions(
        self,
        policy_id: Optional[str] = None,
        limit: int = 100,
    ) -> List[PredictionResult]:
        """Return predictions, optionally filtered by policy id.

        Results are limited to ``limit`` entries (most recent first).
        """
        with self._lock:
            results: List[PredictionResult] = []
            for prediction in self._predictions.values():
                if policy_id is not None and prediction.policy_id != policy_id:
                    continue
                results.append(prediction)
            # Most recent first
            results.reverse()
            if limit > 0:
                results = results[:limit]
            return results

    # ------------------------------------------------------------------
    # Evaluation
    # ------------------------------------------------------------------

    def evaluate_policy(
        self,
        policy_id: str,
        test_demonstration_ids: List[str],
    ) -> Optional[EvaluationReport]:
        """Evaluate a policy against a set of test demonstrations.

        For each step in each test demonstration, the policy's predicted
        action is compared to the expert's actual action. Accuracy is the
        fraction of matching action types. Loss is 1 - accuracy. A
        per-step-index accuracy list and a confusion matrix are also
        produced.
        """
        with self._lock:
            policy = self._policies.get(policy_id)
            if policy is None:
                return None

            training_pairs = self._collect_training_pairs(policy)

            total_steps = 0
            matched_steps = 0
            max_index = 0
            index_matches: Dict[int, int] = {}
            index_totals: Dict[int, int] = {}
            confusion: Dict[str, Dict[str, int]] = {}

            for demo_id in test_demonstration_ids:
                demo = self._demonstrations.get(demo_id)
                if demo is None:
                    continue
                for step in demo.steps:
                    actual_type = step.action.get("type", "unknown")
                    # Predict via nearest-neighbor similarity
                    predicted_type = "unknown"
                    if training_pairs:
                        best_score = -1.0
                        for t_state, t_action in training_pairs:
                            sim = self._state_similarity(step.state, t_state)
                            if sim > best_score:
                                best_score = sim
                                predicted_type = t_action.get(
                                    "type", "unknown"
                                )

                    total_steps += 1
                    index_totals[step.sequence_index] = (
                        index_totals.get(step.sequence_index, 0) + 1
                    )
                    max_index = max(max_index, step.sequence_index)
                    if predicted_type == actual_type:
                        matched_steps += 1
                        index_matches[step.sequence_index] = (
                            index_matches.get(step.sequence_index, 0) + 1
                        )

                    # Update confusion matrix
                    if actual_type not in confusion:
                        confusion[actual_type] = {}
                    confusion[actual_type][predicted_type] = (
                        confusion[actual_type].get(predicted_type, 0) + 1
                    )

            accuracy = (
                matched_steps / total_steps if total_steps > 0 else 0.0
            )
            loss = 1.0 - accuracy

            per_step_accuracy: List[float] = []
            for i in range(max_index + 1):
                total_i = index_totals.get(i, 0)
                matched_i = index_matches.get(i, 0)
                per_step_accuracy.append(
                    matched_i / total_i if total_i > 0 else 0.0
                )

            report = EvaluationReport(
                evaluation_id=_new_id(),
                policy_id=policy_id,
                test_demonstration_ids=list(test_demonstration_ids),
                accuracy=accuracy,
                loss=loss,
                per_step_accuracy=per_step_accuracy,
                confusion=confusion,
                evaluated_at=_now(),
            )
            self._evaluations[report.evaluation_id] = report
            self._evaluation_counter += 1
            _evict_fifo_dict(self._evaluations, _MAX_EVALUATIONS)

            self._record_event(
                ImitationEventKind.EVALUATION_COMPLETED,
                {
                    "evaluation_id": report.evaluation_id,
                    "policy_id": policy_id,
                    "accuracy": round(accuracy, 6),
                    "loss": round(loss, 6),
                    "test_demonstration_count": len(test_demonstration_ids),
                },
            )
            return report

    def list_evaluations(
        self, policy_id: Optional[str] = None
    ) -> List[EvaluationReport]:
        """Return evaluations, optionally filtered by policy id."""
        with self._lock:
            results: List[EvaluationReport] = []
            for report in self._evaluations.values():
                if policy_id is not None and report.policy_id != policy_id:
                    continue
                results.append(report)
            return results

    # ------------------------------------------------------------------
    # Comparison and pruning
    # ------------------------------------------------------------------

    def compare_policies(
        self, policy_id_a: str, policy_id_b: str
    ) -> Dict[str, Any]:
        """Compare two policies on accuracy, loss, and prediction count.

        Returns a dictionary with each policy's summary and the signed
        differences (a - b). If a policy is missing, its summary is None
        and the differences are based on available data.
        """
        with self._lock:
            policy_a = self._policies.get(policy_id_a)
            policy_b = self._policies.get(policy_id_b)

            def _latest_loss(pid: str) -> Optional[float]:
                latest: Optional[EvaluationReport] = None
                for report in self._evaluations.values():
                    if report.policy_id == pid:
                        if latest is None:
                            latest = report
                        elif report.evaluated_at > latest.evaluated_at:
                            latest = report
                return latest.loss if latest is not None else None

            summary_a = policy_a.to_dict() if policy_a else None
            summary_b = policy_b.to_dict() if policy_b else None

            loss_a = _latest_loss(policy_id_a)
            loss_b = _latest_loss(policy_id_b)

            accuracy_diff = (
                policy_a.training_accuracy - policy_b.training_accuracy
                if policy_a and policy_b
                else None
            )
            validation_diff = (
                policy_a.validation_accuracy - policy_b.validation_accuracy
                if policy_a and policy_b
                else None
            )
            prediction_diff = (
                policy_a.prediction_count - policy_b.prediction_count
                if policy_a and policy_b
                else None
            )
            loss_diff = (
                (loss_a - loss_b)
                if loss_a is not None and loss_b is not None
                else None
            )

            return {
                "policy_a": summary_a,
                "policy_b": summary_b,
                "accuracy_diff": (
                    round(accuracy_diff, 6)
                    if accuracy_diff is not None
                    else None
                ),
                "validation_accuracy_diff": (
                    round(validation_diff, 6)
                    if validation_diff is not None
                    else None
                ),
                "prediction_count_diff": prediction_diff,
                "loss_diff": (
                    round(loss_diff, 6) if loss_diff is not None else None
                ),
                "loss_a": loss_a,
                "loss_b": loss_b,
            }

    def prune_demonstrations(
        self,
        domain: Optional[str] = None,
        min_quality: TrajectoryQuality = TrajectoryQuality.LOW,
    ) -> int:
        """Remove demonstrations whose quality is below ``min_quality``.

        Demonstrations are pruned from storage entirely. Optionally
        restricted to a single domain. Returns the number of
        demonstrations pruned.
        """
        with self._lock:
            threshold_rank = _QUALITY_RANK.get(min_quality, 0)
            to_remove: List[str] = []
            for demo_id, demo in self._demonstrations.items():
                if domain is not None and demo.domain != domain:
                    continue
                demo_rank = _QUALITY_RANK.get(demo.quality, 0)
                if demo_rank < threshold_rank:
                    to_remove.append(demo_id)

            for demo_id in to_remove:
                self._demonstrations.pop(demo_id, None)

            if to_remove:
                self._record_event(
                    ImitationEventKind.DEMONSTRATION_PRUNED,
                    {
                        "pruned_count": len(to_remove),
                        "domain": domain,
                        "min_quality": min_quality.value,
                        "pruned_ids": list(to_remove),
                    },
                )
            return len(to_remove)

    # ------------------------------------------------------------------
    # Events, stats, and status
    # ------------------------------------------------------------------

    def list_events(self, limit: int = 100) -> List[ImitationEvent]:
        """Return the most recent events, limited to ``limit`` entries."""
        with self._lock:
            results = list(self._events)
            # Most recent first
            results.reverse()
            if limit > 0:
                results = results[:limit]
            return results

    def get_stats(self) -> ImitationStats:
        """Return aggregate statistics across all artifacts."""
        with self._lock:
            total_steps = sum(
                len(d.steps) for d in self._demonstrations.values()
            )
            policies = list(self._policies.values())
            if policies:
                avg_training = sum(
                    p.training_accuracy for p in policies
                ) / len(policies)
                avg_validation = sum(
                    p.validation_accuracy for p in policies
                ) / len(policies)
            else:
                avg_training = 0.0
                avg_validation = 0.0

            return ImitationStats(
                total_demonstrations=len(self._demonstrations),
                total_steps=total_steps,
                total_policies=len(self._policies),
                total_predictions=len(self._predictions),
                total_evaluations=len(self._evaluations),
                avg_training_accuracy=avg_training,
                avg_validation_accuracy=avg_validation,
            )

    def get_status(self) -> Dict[str, Any]:
        """Return a comprehensive status dictionary for diagnostics.

        The ``initialized`` flag is always the first key.
        """
        with self._lock:
            demos = list(self._demonstrations.values())
            status_counts: Dict[str, int] = {}
            quality_counts: Dict[str, int] = {}
            source_counts: Dict[str, int] = {}
            for demo in demos:
                status_counts[demo.status.value] = (
                    status_counts.get(demo.status.value, 0) + 1
                )
                quality_counts[demo.quality.value] = (
                    quality_counts.get(demo.quality.value, 0) + 1
                )
                source_counts[demo.source.value] = (
                    source_counts.get(demo.source.value, 0) + 1
                )

            policies = list(self._policies.values())
            policy_status_counts: Dict[str, int] = {}
            policy_type_counts: Dict[str, int] = {}
            for policy in policies:
                policy_status_counts[policy.status.value] = (
                    policy_status_counts.get(policy.status.value, 0) + 1
                )
                policy_type_counts[policy.policy_type.value] = (
                    policy_type_counts.get(policy.policy_type.value, 0) + 1
                )

            return {
                "initialized": self._initialized,
                "total_demonstrations": len(self._demonstrations),
                "total_policies": len(self._policies),
                "total_predictions": len(self._predictions),
                "total_evaluations": len(self._evaluations),
                "total_events": len(self._events),
                "demonstration_counter": self._demonstration_counter,
                "policy_counter": self._policy_counter,
                "prediction_counter": self._prediction_counter,
                "evaluation_counter": self._evaluation_counter,
                "demonstration_status_distribution": status_counts,
                "demonstration_quality_distribution": quality_counts,
                "demonstration_source_distribution": source_counts,
                "policy_status_distribution": policy_status_counts,
                "policy_type_distribution": policy_type_counts,
                "capacity_limits": {
                    "max_demonstrations": _MAX_DEMONSTRATIONS,
                    "max_trajectory_steps": _MAX_TRAJECTORY_STEPS,
                    "max_policies": _MAX_POLICIES,
                    "max_predictions": _MAX_PREDICTIONS,
                    "max_evaluations": _MAX_EVALUATIONS,
                    "max_events": _MAX_EVENTS,
                },
                "last_updated": _now(),
            }

    def get_snapshot(self) -> ImitationSnapshot:
        """Capture a point-in-time snapshot of the entire engine state."""
        with self._lock:
            stats = self.get_stats()
            return ImitationSnapshot(
                initialized=self._initialized,
                demonstrations=[
                    d.to_dict() for d in self._demonstrations.values()
                ],
                policies=[
                    p.to_dict() for p in self._policies.values()
                ],
                predictions=[
                    p.to_dict() for p in self._predictions.values()
                ],
                evaluations=[
                    e.to_dict() for e in self._evaluations.values()
                ],
                events=[ev.to_dict() for ev in self._events],
                stats=stats.to_dict(),
            )

    # ------------------------------------------------------------------
    # Reset
    # ------------------------------------------------------------------

    def reset(self) -> None:
        """Clear all stores and re-seed the engine with baseline data.

        The ``_initialized`` flag is preserved so that the singleton guard
        in ``__init__`` does not re-run. Counters are reset to zero before
        re-seeding.
        """
        with self._lock:
            self._demonstrations.clear()
            self._policies.clear()
            self._predictions.clear()
            self._evaluations.clear()
            self._events.clear()
            self._demonstration_counter = 0
            self._policy_counter = 0
            self._prediction_counter = 0
            self._evaluation_counter = 0
            self._seed_data()


# ---------------------------------------------------------------------------
# Module-Level Accessor
# ---------------------------------------------------------------------------

def get_demonstration_learner() -> DemonstrationLearnerEngine:
    """Return the singleton DemonstrationLearnerEngine instance."""
    return DemonstrationLearnerEngine.get_instance()
