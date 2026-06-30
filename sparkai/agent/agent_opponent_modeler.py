"""
SparkLabs Agent - Opponent Modeler Engine

Opponent modeling system for competitive game AI. Builds behavioral
profiles of opponents from observed actions, predicts their strategies
and next moves, detects exploitable weaknesses, tracks strategy
adaptation, and generates counter-strategies.

Architecture:
  OpponentModelerEngine (Singleton)
    |-- OpponentAction (an observed action with phase and confidence)
    |-- StrategyProfile (archetype, strategies, metrics, weaknesses)
    |-- MovePrediction (forecasted move with probability and horizon)
    |-- WeaknessReport (exploitable pattern with severity)
    |-- CounterStrategy (suggested response to a weakness)
    |-- AdaptationEvent (recorded strategy change)

Core Capabilities:
  - Register opponents and record their observed actions
  - Classify opponents into player archetypes (aggressive, turtle, etc.)
  - Identify the active strategy of each opponent
  - Forecast the next moves using recency-weighted frequency analysis
  - Detect exploitable weaknesses in opponent behavior
  - Suggest counter-strategies tailored to each weakness
  - Track when opponents adapt and change strategy
  - Score prediction confidence from sample size and consistency
"""

from __future__ import annotations

import threading
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Enums (string-valued for JSON compatibility)
# ---------------------------------------------------------------------------

class PlayerArchetype(Enum):
    """Behavioral archetypes describing an opponent's overall play style."""
    AGGRESSIVE = "aggressive"
    DEFENSIVE = "defensive"
    BALANCED = "balanced"
    OPPORTUNIST = "opportunist"
    TURTLE = "turtle"
    RUSHER = "rusher"
    SNIPER = "sniper"
    UNPREDICTABLE = "unpredictable"
    UNKNOWN = "unknown"


class StrategyType(Enum):
    """High-level strategies an opponent may be executing."""
    RUSH = "rush"
    TURTLE = "turtle"
    BOOM = "boom"
    TIMING_ATTACK = "timing_attack"
    CHEESE = "cheese"
    MACRO = "macro"
    MICRO = "micro"
    ADAPTIVE = "adaptive"
    COUNTER = "counter"


class ObservationKind(Enum):
    """Categories of actions that can be observed from an opponent."""
    MOVE = "move"
    BUILD = "build"
    ATTACK = "attack"
    DEFEND = "defend"
    RESOURCE = "resource"
    RETREAT = "retreat"
    REPOSITION = "reposition"
    COMMUNICATE = "communicate"


class GamePhase(Enum):
    """Game phase tags used to weight predictions contextually."""
    EARLY_GAME = "early_game"
    MID_GAME = "mid_game"
    LATE_GAME = "late_game"


class WeaknessType(Enum):
    """Categories of exploitable patterns in opponent behavior."""
    PREDICTABLE_ROUTINE = "predictable_routine"
    WEAK_DEFENSE = "weak_defense"
    OVER_AGGRESSION = "over_aggression"
    NO_ADAPTATION = "no_adaptation"
    POOR_ECONOMY = "poor_economy"
    REPEATED_TIMING = "repeated_timing"
    LIMITED_UNIT_MIX = "limited_unit_mix"
    POOR_SCOUTING = "poor_scouting"
    OVERCOMMIT = "overcommit"


class Severity(Enum):
    """How damaging a detected weakness is to the opponent."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class OpponentEventKind(Enum):
    """Events emitted by the opponent modeler for external listeners."""
    OPPONENT_REGISTERED = "opponent_registered"
    ACTION_RECORDED = "action_recorded"
    PROFILE_UPDATED = "profile_updated"
    PREDICTION_MADE = "prediction_made"
    PREDICTION_RESOLVED = "prediction_resolved"
    WEAKNESS_DETECTED = "weakness_detected"
    COUNTER_GENERATED = "counter_generated"
    ADAPTATION_DETECTED = "adaptation_detected"
    ARCHETYPE_CHANGED = "archetype_changed"
    STRATEGY_CHANGED = "strategy_changed"


# ---------------------------------------------------------------------------
# Indicator tables (weights for archetype and strategy classification)
# ---------------------------------------------------------------------------

# Each archetype is scored against a set of normalized metrics derived from
# the opponent's action stream. Weights sum to 1.0 per archetype.
_ARCHETYPE_INDICATORS: Dict[PlayerArchetype, Dict[str, float]] = {
    PlayerArchetype.AGGRESSIVE: {
        "attack_ratio": 0.4,
        "aggression_rate": 0.35,
        "low_defense": 0.25,
    },
    PlayerArchetype.DEFENSIVE: {
        "defend_ratio": 0.45,
        "low_attack": 0.3,
        "build_ratio": 0.25,
    },
    PlayerArchetype.BALANCED: {
        "diversity": 0.5,
        "balance": 0.5,
    },
    PlayerArchetype.OPPORTUNIST: {
        "reposition_ratio": 0.35,
        "attack_ratio": 0.35,
        "diversity": 0.3,
    },
    PlayerArchetype.TURTLE: {
        "defend_ratio": 0.4,
        "resource_ratio": 0.35,
        "low_attack": 0.25,
    },
    PlayerArchetype.RUSHER: {
        "early_aggression": 0.45,
        "attack_ratio": 0.35,
        "low_resource": 0.2,
    },
    PlayerArchetype.SNIPER: {
        "attack_ratio": 0.4,
        "low_move": 0.3,
        "reposition_ratio": 0.3,
    },
    PlayerArchetype.UNPREDICTABLE: {
        "diversity": 0.6,
        "variance": 0.4,
    },
}

# Strategy scoring tables. Each strategy scores metrics the opponent exhibits.
_STRATEGY_INDICATORS: Dict[StrategyType, Dict[str, float]] = {
    StrategyType.RUSH: {
        "early_aggression": 0.45,
        "attack_ratio": 0.35,
        "low_resource": 0.2,
    },
    StrategyType.TURTLE: {
        "defend_ratio": 0.4,
        "resource_ratio": 0.35,
        "low_attack": 0.25,
    },
    StrategyType.BOOM: {
        "resource_ratio": 0.5,
        "build_ratio": 0.3,
        "low_attack": 0.2,
    },
    StrategyType.TIMING_ATTACK: {
        "mid_attack": 0.4,
        "resource_ratio": 0.3,
        "attack_ratio": 0.3,
    },
    StrategyType.CHEESE: {
        "early_aggression": 0.4,
        "low_resource": 0.35,
        "low_diversity": 0.25,
    },
    StrategyType.MACRO: {
        "build_ratio": 0.45,
        "resource_ratio": 0.35,
        "diversity": 0.2,
    },
    StrategyType.MICRO: {
        "move_ratio": 0.4,
        "reposition_ratio": 0.35,
        "attack_ratio": 0.25,
    },
    StrategyType.ADAPTIVE: {
        "adaptation_score": 0.6,
        "diversity": 0.4,
    },
    StrategyType.COUNTER: {
        "defend_ratio": 0.4,
        "reposition_ratio": 0.3,
        "diversity": 0.3,
    },
}

# Counter-strategy suggestions keyed by weakness type. Each entry lists a
# strategy name, a human-readable description, and concrete actions.
_COUNTER_PLAYBOOK: Dict[WeaknessType, Tuple[str, str, List[str]]] = {
    WeaknessType.PREDICTABLE_ROUTINE: (
        "Punish Routine",
        "The opponent repeats the same action sequence. Prepare an ambush "
        "at the predicted action point.",
        ["scout_predicted_position", "set_trap_at_routine_target", "strike_during_routine"],
    ),
    WeaknessType.WEAK_DEFENSE: (
        "Exploit Open Defense",
        "The opponent neglects defense. Apply direct pressure on weak points.",
        ["probe_defensive_gaps", "commit_to_frontal_push", "raid_economy"],
    ),
    WeaknessType.OVER_AGGRESSION: (
        "Bait and Counter",
        "The opponent over-commits to attacks. Bait them into bad engagements.",
        ["feign_weakness", "draw_into_chokepoint", "counter_attack_on_overextension"],
    ),
    WeaknessType.NO_ADAPTATION: (
        "Shift Tempo",
        "The opponent does not adapt. Change strategy to one they have not faced.",
        ["switch_strategy", "deny_information", "force_unfamiliar_situation"],
    ),
    WeaknessType.POOR_ECONOMY: (
        "Starve Economy",
        "The opponent under-invests in resources. Raid their economy lines.",
        ["raid_resource_lines", "deny_expansions", "contain_to_single_base"],
    ),
    WeaknessType.REPEATED_TIMING: (
        "Interrupt Timing",
        "The opponent attacks on a fixed schedule. Pre-position defenders.",
        ["pre_position_defenders", "scout_timing_window", "disrupt_before_attack"],
    ),
    WeaknessType.LIMITED_UNIT_MIX: (
        "Hard Counter Units",
        "The opponent uses a narrow unit set. Build units that hard-counter it.",
        ["identify_unit_type", "train_hard_counter", "deny_unit_production"],
    ),
    WeaknessType.POOR_SCOUTING: (
        "Deny Information",
        "The opponent does not scout. Execute a hidden strategy.",
        ["conceal_build_order", "take_hidden_expansion", "build_unscouted_army"],
    ),
    WeaknessType.OVERCOMMIT: (
        "Punish Overcommit",
        "The opponent commits too many resources to one objective.",
        ["exploit_opposite_front", "counter_at_commitment_point", "deny_recall_path"],
    ),
}


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class BehaviorMetric:
    """A single tracked behavioral metric for an opponent.

    Attributes:
        name: Identifier of the metric (e.g. "attack_ratio").
        value: Current normalized value in [0.0, 1.0].
        trend: Direction of change ("up", "down", "stable").
        samples: Number of observations contributing to this value.
        last_updated: Timestamp of the last update.
    """
    name: str = ""
    value: float = 0.0
    trend: str = "stable"
    samples: int = 0
    last_updated: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "value": round(self.value, 4),
            "trend": self.trend,
            "samples": self.samples,
            "last_updated": self.last_updated,
        }


@dataclass
class OpponentAction:
    """A single observed action performed by an opponent.

    Attributes:
        id: Unique observation identifier.
        opponent_id: The opponent that performed the action.
        kind: Category of the observation.
        action_type: Specific action name (e.g. "marine_push").
        parameters: Action parameters such as targets or coordinates.
        timestamp: When the observation was recorded.
        game_phase: Phase of the game when the action occurred.
        confidence: Reliability of this observation in [0.0, 1.0].
    """
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    opponent_id: str = ""
    kind: ObservationKind = ObservationKind.MOVE
    action_type: str = ""
    parameters: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)
    game_phase: str = GamePhase.EARLY_GAME.value
    confidence: float = 0.5

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "opponent_id": self.opponent_id,
            "kind": self.kind.value,
            "action_type": self.action_type,
            "parameters": dict(self.parameters),
            "timestamp": self.timestamp,
            "game_phase": self.game_phase,
            "confidence": round(self.confidence, 4),
        }


@dataclass
class StrategyProfile:
    """Behavioral profile of an opponent built from observed actions.

    Attributes:
        id: Unique profile identifier.
        opponent_id: The opponent this profile describes.
        archetype: Classified play style archetype.
        strategies: Ranked list of likely strategies.
        confidence: Confidence in the profile classification.
        action_counts: Per-action-type observation counts.
        metric_averages: Computed behavioral metric averages.
        last_seen: Timestamp of the most recent action.
        adaptation_score: How much the opponent changes strategy over time.
        weaknesses: Identifier list of detected weaknesses.
        metadata: Arbitrary additional data.
    """
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    opponent_id: str = ""
    archetype: PlayerArchetype = PlayerArchetype.UNKNOWN
    strategies: List[StrategyType] = field(default_factory=list)
    confidence: float = 0.0
    action_counts: Dict[str, int] = field(default_factory=dict)
    metric_averages: Dict[str, float] = field(default_factory=dict)
    last_seen: float = field(default_factory=time.time)
    adaptation_score: float = 0.0
    weaknesses: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "opponent_id": self.opponent_id,
            "archetype": self.archetype.value,
            "strategies": [s.value for s in self.strategies],
            "confidence": round(self.confidence, 4),
            "action_counts": dict(self.action_counts),
            "metric_averages": {k: round(v, 4) for k, v in self.metric_averages.items()},
            "last_seen": self.last_seen,
            "adaptation_score": round(self.adaptation_score, 4),
            "weaknesses": list(self.weaknesses),
            "metadata": dict(self.metadata),
        }


@dataclass
class MovePrediction:
    """A forecasted opponent move with alternatives and confidence.

    Attributes:
        id: Unique prediction identifier.
        opponent_id: The opponent this prediction concerns.
        predicted_action: The most likely next action.
        probability: Probability assigned to the predicted action.
        alternatives: Lower-ranked candidate actions.
        reasoning: Human-readable explanation of the prediction.
        horizon: How many steps ahead the prediction spans.
        confidence: Overall reliability of the prediction.
        created_at: When the prediction was generated.
        actual_action: Resolved actual action (filled on feedback).
        correct: Whether the prediction matched the actual action.
    """
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    opponent_id: str = ""
    predicted_action: str = ""
    probability: float = 0.0
    alternatives: List[Dict[str, Any]] = field(default_factory=list)
    reasoning: str = ""
    horizon: int = 1
    confidence: float = 0.0
    created_at: float = field(default_factory=time.time)
    actual_action: Optional[str] = None
    correct: Optional[bool] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "opponent_id": self.opponent_id,
            "predicted_action": self.predicted_action,
            "probability": round(self.probability, 4),
            "alternatives": list(self.alternatives),
            "reasoning": self.reasoning,
            "horizon": self.horizon,
            "confidence": round(self.confidence, 4),
            "created_at": self.created_at,
            "actual_action": self.actual_action,
            "correct": self.correct,
        }


@dataclass
class WeaknessReport:
    """A detected exploitable pattern in opponent behavior.

    Attributes:
        id: Unique report identifier.
        opponent_id: The opponent exhibiting the weakness.
        weakness_type: Category of the weakness.
        description: Human-readable explanation of the pattern.
        exploit_suggestion: Suggested way to exploit the weakness.
        confidence: Reliability of the detection.
        evidence: Supporting observations and metric values.
        severity: How damaging the weakness is.
    """
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    opponent_id: str = ""
    weakness_type: WeaknessType = WeaknessType.PREDICTABLE_ROUTINE
    description: str = ""
    exploit_suggestion: str = ""
    confidence: float = 0.0
    evidence: List[str] = field(default_factory=list)
    severity: Severity = Severity.MEDIUM

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "opponent_id": self.opponent_id,
            "weakness_type": self.weakness_type.value,
            "description": self.description,
            "exploit_suggestion": self.exploit_suggestion,
            "confidence": round(self.confidence, 4),
            "evidence": list(self.evidence),
            "severity": self.severity.value,
        }


@dataclass
class CounterStrategy:
    """A suggested response to a detected opponent weakness.

    Attributes:
        id: Unique counter-strategy identifier.
        opponent_id: The opponent to counter.
        strategy_name: Short name of the counter-strategy.
        description: Explanation of the counter-strategy.
        actions: Concrete actions to execute.
        expected_outcome: Anticipated result if executed correctly.
        confidence: Reliability of the counter-strategy.
        priority: Ordering priority (higher is more urgent).
    """
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    opponent_id: str = ""
    strategy_name: str = ""
    description: str = ""
    actions: List[str] = field(default_factory=list)
    expected_outcome: str = ""
    confidence: float = 0.0
    priority: float = 0.5

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "opponent_id": self.opponent_id,
            "strategy_name": self.strategy_name,
            "description": self.description,
            "actions": list(self.actions),
            "expected_outcome": self.expected_outcome,
            "confidence": round(self.confidence, 4),
            "priority": round(self.priority, 4),
        }


@dataclass
class AdaptationEvent:
    """A recorded strategy change by an opponent.

    Attributes:
        opponent_id: The opponent that adapted.
        old_strategy: Previous primary strategy.
        new_strategy: Newly detected primary strategy.
        detected_at: When the change was detected.
        confidence: Reliability of the detection.
        evidence: Supporting observations.
    """
    opponent_id: str = ""
    old_strategy: StrategyType = StrategyType.ADAPTIVE
    new_strategy: StrategyType = StrategyType.ADAPTIVE
    detected_at: float = field(default_factory=time.time)
    confidence: float = 0.0
    evidence: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "opponent_id": self.opponent_id,
            "old_strategy": self.old_strategy.value,
            "new_strategy": self.new_strategy.value,
            "detected_at": self.detected_at,
            "confidence": round(self.confidence, 4),
            "evidence": list(self.evidence),
        }


@dataclass
class OpponentStats:
    """Aggregate statistics across all modeled opponents."""
    total_opponents: int = 0
    total_profiles: int = 0
    total_predictions: int = 0
    total_correct: int = 0
    avg_confidence: float = 0.0
    total_weaknesses: int = 0
    total_counter_strategies: int = 0

    def to_dict(self) -> Dict[str, Any]:
        accuracy = (
            self.total_correct / self.total_predictions
            if self.total_predictions > 0
            else 0.0
        )
        return {
            "total_opponents": self.total_opponents,
            "total_profiles": self.total_profiles,
            "total_predictions": self.total_predictions,
            "total_correct": self.total_correct,
            "prediction_accuracy": round(accuracy, 4),
            "avg_confidence": round(self.avg_confidence, 4),
            "total_weaknesses": self.total_weaknesses,
            "total_counter_strategies": self.total_counter_strategies,
        }


@dataclass
class OpponentSnapshot:
    """Point-in-time snapshot of the modeler state."""
    profiles: List[Dict[str, Any]] = field(default_factory=list)
    predictions: List[Dict[str, Any]] = field(default_factory=list)
    weaknesses: List[Dict[str, Any]] = field(default_factory=list)
    counter_strategies: List[Dict[str, Any]] = field(default_factory=list)
    stats: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "profiles": list(self.profiles),
            "predictions": list(self.predictions),
            "weaknesses": list(self.weaknesses),
            "counter_strategies": list(self.counter_strategies),
            "stats": dict(self.stats),
        }


@dataclass
class OpponentEvent:
    """An internal event emitted by the modeler for listeners."""
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    kind: OpponentEventKind = OpponentEventKind.ACTION_RECORDED
    opponent_id: Optional[str] = None
    payload: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "kind": self.kind.value,
            "opponent_id": self.opponent_id,
            "payload": dict(self.payload),
            "timestamp": self.timestamp,
        }


# ---------------------------------------------------------------------------
# OpponentModelerEngine
# ---------------------------------------------------------------------------

class OpponentModelerEngine:
    """Thread-safe singleton engine for opponent modeling.

    Maintains opponent profiles, observed actions, predictions, weakness
    reports, counter-strategies, and adaptation history. All public
    operations are guarded by a re-entrant lock so the engine can be
    driven safely from multiple game threads.
    """

    _instance: Optional["OpponentModelerEngine"] = None
    _lock = threading.RLock()

    _MAX_ACTIONS: int = 50000
    _MAX_ACTIONS_PER_OPPONENT: int = 2000
    _MAX_PREDICTIONS: int = 10000
    _MAX_PREDICTIONS_PER_OPPONENT: int = 500
    _MAX_WEAKNESSES_PER_OPPONENT: int = 50
    _MAX_COUNTERS_PER_OPPONENT: int = 50
    _MAX_EVENTS: int = 10000
    _MAX_ADAPTATION_HISTORY: int = 100

    # Prediction tuning constants.
    _RECENCY_DECAY: float = 0.95
    _BASE_PREDICTION_CONFIDENCE: float = 0.7
    _FULL_CONFIDENCE_SAMPLES: int = 20
    _ADAPTATION_WINDOW: int = 20

    def __init__(self) -> None:
        if getattr(self, "_initialized", False):
            return

        self._profiles: Dict[str, StrategyProfile] = {}
        self._profiles_by_opponent: Dict[str, str] = {}
        self._actions: Dict[str, OpponentAction] = {}
        self._actions_by_opponent: Dict[str, List[str]] = {}
        self._predictions: Dict[str, MovePrediction] = {}
        self._predictions_by_opponent: Dict[str, List[str]] = {}
        self._weaknesses: Dict[str, WeaknessReport] = {}
        self._weaknesses_by_opponent: Dict[str, List[str]] = {}
        self._counters: Dict[str, CounterStrategy] = {}
        self._counters_by_opponent: Dict[str, List[str]] = {}
        self._adaptation_history: Dict[str, List[AdaptationEvent]] = {}
        self._last_strategy: Dict[str, StrategyType] = {}
        self._last_archetype: Dict[str, PlayerArchetype] = {}
        self._events: List[OpponentEvent] = []
        self._event_handlers: Dict[str, List[Tuple[str, Callable]]] = {}

        self._total_predictions: int = 0
        self._total_correct: int = 0
        self._total_weaknesses_detected: int = 0
        self._total_counters_generated: int = 0
        self._total_adaptations: int = 0

        self._initialized: bool = True

        self._seed_default_data()

    @classmethod
    def get_instance(cls) -> "OpponentModelerEngine":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    # ------------------------------------------------------------------
    # Internal helpers (lock assumed held)
    # ------------------------------------------------------------------

    def _emit_event(
        self,
        kind: OpponentEventKind,
        opponent_id: Optional[str] = None,
        payload: Optional[Dict[str, Any]] = None,
    ) -> OpponentEvent:
        """Create, store, and dispatch an event to registered handlers."""
        event = OpponentEvent(
            kind=kind,
            opponent_id=opponent_id,
            payload=payload if payload is not None else {},
        )
        self._events.append(event)
        if len(self._events) > self._MAX_EVENTS:
            self._events = self._events[-self._MAX_EVENTS:]

        for handler_id, handler in self._event_handlers.get(kind.value, []):
            try:
                handler(event)
            except Exception:
                # Handler errors must not disrupt engine operation.
                pass
        return event

    def _get_actions(self, opponent_id: str) -> List[OpponentAction]:
        ids = self._actions_by_opponent.get(opponent_id, [])
        return [self._actions[aid] for aid in ids if aid in self._actions]

    def _enforce_action_limits(self, opponent_id: str) -> None:
        ids = self._actions_by_opponent.get(opponent_id, [])
        if len(ids) <= self._MAX_ACTIONS_PER_OPPONENT:
            return
        overflow = len(ids) - self._MAX_ACTIONS_PER_OPPONENT
        for aid in ids[:overflow]:
            self._actions.pop(aid, None)
        self._actions_by_opponent[opponent_id] = ids[overflow:]

    def _enforce_prediction_limits(self, opponent_id: str) -> None:
        ids = self._predictions_by_opponent.get(opponent_id, [])
        if len(ids) <= self._MAX_PREDICTIONS_PER_OPPONENT:
            return
        overflow = len(ids) - self._MAX_PREDICTIONS_PER_OPPONENT
        for pid in ids[:overflow]:
            self._predictions.pop(pid, None)
        self._predictions_by_opponent[opponent_id] = ids[overflow:]

    # ------------------------------------------------------------------
    # Metric computation
    # ------------------------------------------------------------------

    def _compute_metrics(self, actions: List[OpponentAction]) -> Dict[str, float]:
        """Derive normalized behavioral metrics from an action list."""
        metrics: Dict[str, float] = {}
        total = len(actions)
        if total == 0:
            return metrics

        counts: Dict[str, int] = {}
        phase_counts: Dict[str, int] = {"early_game": 0, "mid_game": 0, "late_game": 0}
        # Per-phase action-kind counts so phase-specific ratios stay accurate.
        phase_kind_counts: Dict[str, Dict[str, int]] = {}
        action_types: Dict[str, int] = {}
        for act in actions:
            kv = act.kind.value
            counts[kv] = counts.get(kv, 0) + 1
            phase_counts[act.game_phase] = phase_counts.get(act.game_phase, 0) + 1
            phase_bucket = phase_kind_counts.setdefault(act.game_phase, {})
            phase_bucket[kv] = phase_bucket.get(kv, 0) + 1
            action_types[act.action_type] = action_types.get(act.action_type, 0) + 1

        attack = counts.get(ObservationKind.ATTACK.value, 0)
        defend = counts.get(ObservationKind.DEFEND.value, 0)
        build = counts.get(ObservationKind.BUILD.value, 0)
        resource = counts.get(ObservationKind.RESOURCE.value, 0)
        move = counts.get(ObservationKind.MOVE.value, 0)
        retreat = counts.get(ObservationKind.RETREAT.value, 0)
        reposition = counts.get(ObservationKind.REPOSITION.value, 0)

        early_total = phase_counts.get("early_game", 0)
        mid_total = phase_counts.get("mid_game", 0)
        early_attacks = (
            phase_kind_counts.get("early_game", {}).get(ObservationKind.ATTACK.value, 0)
        )
        mid_attacks = (
            phase_kind_counts.get("mid_game", {}).get(ObservationKind.ATTACK.value, 0)
        )

        metrics["attack_ratio"] = attack / total
        metrics["defend_ratio"] = defend / total
        metrics["build_ratio"] = build / total
        metrics["resource_ratio"] = resource / total
        metrics["move_ratio"] = move / total
        metrics["reposition_ratio"] = reposition / total
        metrics["retreat_ratio"] = retreat / total
        metrics["low_defense"] = 1.0 - (defend / total)
        metrics["low_attack"] = 1.0 - (attack / total)
        metrics["low_resource"] = 1.0 - (resource / total)
        metrics["low_move"] = 1.0 - (move / total)
        metrics["aggression_rate"] = (attack + reposition) / total
        metrics["early_aggression"] = (
            (early_attacks / early_total) if early_total > 0 else 0.0
        )
        metrics["mid_attack"] = (
            (mid_attacks / mid_total) if mid_total > 0 else 0.0
        )

        distinct_types = len(action_types)
        metrics["diversity"] = min(1.0, distinct_types / 8.0)
        metrics["low_diversity"] = 1.0 - metrics["diversity"]

        # Balance: how evenly distributed the action kinds are. Uses the max
        # deviation so a heavy concentration in one kind scores as imbalanced.
        even_share = 1.0 / max(1, len(counts)) if counts else 0.0
        deviations = [abs(c / total - even_share) for c in counts.values()]
        metrics["balance"] = 1.0 - max(deviations) if deviations else 1.0

        # Variance across action types (high variance => unpredictable).
        if action_types:
            avg_freq = sum(action_types.values()) / len(action_types)
            variance = sum((f - avg_freq) ** 2 for f in action_types.values())
            metrics["variance"] = min(1.0, variance / (total * total + 1.0))
        else:
            metrics["variance"] = 0.0

        avg_conf = sum(a.confidence for a in actions) / total
        metrics["avg_confidence"] = avg_conf

        metrics["adaptation_score"] = self._adaptation_score(actions)
        return metrics

    def _adaptation_score(self, actions: List[OpponentAction]) -> float:
        """Measure how much the action distribution shifts over time.

        Splits the action stream into two halves and compares their kind
        distributions. Larger divergence yields a higher score.
        """
        if len(actions) < 4:
            return 0.0
        midpoint = len(actions) // 2
        first_half = actions[:midpoint]
        second_half = actions[midpoint:]

        def distribution(segment: List[OpponentAction]) -> Dict[str, float]:
            counts: Dict[str, int] = {}
            for act in segment:
                counts[act.kind.value] = counts.get(act.kind.value, 0) + 1
            total = len(segment)
            return {k: v / total for k, v in counts.items()} if total > 0 else {}

        d1 = distribution(first_half)
        d2 = distribution(second_half)
        keys = set(d1.keys()) | set(d2.keys())
        divergence = sum(abs(d1.get(k, 0.0) - d2.get(k, 0.0)) for k in keys)
        return min(1.0, divergence / 2.0)

    # ------------------------------------------------------------------
    # Seed data
    # ------------------------------------------------------------------

    def _seed_default_data(self) -> None:
        """Populate two demo opponents so the system works out of the box."""
        self._seed_opponent_alpha()
        self._seed_opponent_beta()

    def _seed_opponent_alpha(self) -> None:
        opponent_id = "player-alpha"
        self.register_opponent(opponent_id, PlayerArchetype.AGGRESSIVE)

        # Aggressive rusher: many early attacks, low resource investment.
        seed_actions = [
            (ObservationKind.ATTACK, "marine_push", GamePhase.EARLY_GAME.value, 0.9),
            (ObservationKind.ATTACK, "marine_push", GamePhase.EARLY_GAME.value, 0.85),
            (ObservationKind.MOVE, "advance_front", GamePhase.EARLY_GAME.value, 0.8),
            (ObservationKind.ATTACK, "zealot_rush", GamePhase.EARLY_GAME.value, 0.88),
            (ObservationKind.ATTACK, "marine_push", GamePhase.MID_GAME.value, 0.82),
            (ObservationKind.REPOSITION, "reposition_army", GamePhase.MID_GAME.value, 0.75),
            (ObservationKind.ATTACK, "all_in_push", GamePhase.MID_GAME.value, 0.9),
            (ObservationKind.ATTACK, "marine_push", GamePhase.MID_GAME.value, 0.8),
            (ObservationKind.ATTACK, "all_in_push", GamePhase.LATE_GAME.value, 0.78),
            (ObservationKind.ATTACK, "marine_push", GamePhase.LATE_GAME.value, 0.7),
        ]
        for kind, action_type, phase, conf in seed_actions:
            self._record_action_internal(
                opponent_id, kind, action_type, {}, phase, conf
            )

        self.update_profile(opponent_id)

        # Seed one weakness report: over-aggression with no retreats.
        weakness = WeaknessReport(
            opponent_id=opponent_id,
            weakness_type=WeaknessType.OVER_AGGRESSION,
            description="Opponent commits to attacks without retreating, "
                        "leaving economy and defense exposed.",
            exploit_suggestion="Bait the over-extension into a chokepoint "
                               "and counter-attack the undefended base.",
            confidence=0.82,
            evidence=[
                "retreat_ratio is near zero",
                "attack_ratio above 0.6",
                "no defensive actions observed",
            ],
            severity=Severity.HIGH,
        )
        self._weaknesses[weakness.id] = weakness
        self._weaknesses_by_opponent.setdefault(opponent_id, []).append(weakness.id)
        self._total_weaknesses_detected += 1

        # Seed a prediction for the rusher.
        self._seed_prediction(opponent_id, "marine_push")

    def _seed_opponent_beta(self) -> None:
        opponent_id = "player-beta"
        self.register_opponent(opponent_id, PlayerArchetype.DEFENSIVE)

        # Defensive turtle: heavy defense with economy support, no attacks.
        # Distribution is defense-heavy so DEFENSIVE archetype dominates.
        seed_actions = [
            (ObservationKind.DEFEND, "wall_off", GamePhase.EARLY_GAME.value, 0.9),
            (ObservationKind.DEFEND, "wall_off", GamePhase.EARLY_GAME.value, 0.88),
            (ObservationKind.RESOURCE, "gather_minerals", GamePhase.EARLY_GAME.value, 0.85),
            (ObservationKind.DEFEND, "reinforce_wall", GamePhase.MID_GAME.value, 0.82),
            (ObservationKind.DEFEND, "wall_off", GamePhase.MID_GAME.value, 0.8),
            (ObservationKind.DEFEND, "wall_off", GamePhase.MID_GAME.value, 0.78),
            (ObservationKind.DEFEND, "reinforce_wall", GamePhase.LATE_GAME.value, 0.75),
            (ObservationKind.DEFEND, "wall_off", GamePhase.LATE_GAME.value, 0.72),
            (ObservationKind.DEFEND, "wall_off", GamePhase.LATE_GAME.value, 0.7),
            (ObservationKind.BUILD, "construct_bunker", GamePhase.LATE_GAME.value, 0.68),
        ]
        for kind, action_type, phase, conf in seed_actions:
            self._record_action_internal(
                opponent_id, kind, action_type, {}, phase, conf
            )

        self.update_profile(opponent_id)
        self._seed_prediction(opponent_id, "wall_off")

    def _seed_prediction(self, opponent_id: str, action: str) -> None:
        """Generate and store a seed prediction without re-triggering analysis."""
        actions = self._get_actions(opponent_id)
        if not actions:
            return
        prediction = MovePrediction(
            opponent_id=opponent_id,
            predicted_action=action,
            probability=0.45,
            alternatives=[],
            reasoning="Seed prediction based on observed action frequency.",
            horizon=1,
            confidence=0.55,
        )
        self._predictions[prediction.id] = prediction
        self._predictions_by_opponent.setdefault(opponent_id, []).append(prediction.id)
        self._total_predictions += 1

    def _record_action_internal(
        self,
        opponent_id: str,
        kind: ObservationKind,
        action_type: str,
        parameters: Dict[str, Any],
        game_phase: str,
        confidence: float,
    ) -> OpponentAction:
        """Internal action recorder that assumes the lock is already held."""
        action = OpponentAction(
            opponent_id=opponent_id,
            kind=kind,
            action_type=action_type,
            parameters=dict(parameters),
            game_phase=game_phase,
            confidence=max(0.0, min(1.0, confidence)),
        )
        self._actions[action.id] = action
        self._actions_by_opponent.setdefault(opponent_id, []).append(action.id)
        self._enforce_action_limits(opponent_id)
        return action

    # ------------------------------------------------------------------
    # Opponent registration
    # ------------------------------------------------------------------

    def register_opponent(
        self,
        opponent_id: str,
        initial_archetype: PlayerArchetype = PlayerArchetype.UNKNOWN,
    ) -> StrategyProfile:
        """Start tracking a new opponent.

        Returns the new or existing profile for the opponent. If the
        opponent is already registered, the existing profile is returned.
        """
        with self._lock:
            existing_id = self._profiles_by_opponent.get(opponent_id)
            if existing_id is not None and existing_id in self._profiles:
                return self._profiles[existing_id]

            profile = StrategyProfile(
                opponent_id=opponent_id,
                archetype=initial_archetype,
                confidence=0.0,
            )
            self._profiles[profile.id] = profile
            self._profiles_by_opponent[opponent_id] = profile.id
            self._last_strategy[opponent_id] = StrategyType.ADAPTIVE
            self._last_archetype[opponent_id] = initial_archetype
            self._emit_event(
                OpponentEventKind.OPPONENT_REGISTERED,
                opponent_id,
                {"archetype": initial_archetype.value, "profile_id": profile.id},
            )
            return profile

    # ------------------------------------------------------------------
    # Action recording
    # ------------------------------------------------------------------

    def record_action(
        self,
        opponent_id: str,
        kind: ObservationKind,
        action_type: str,
        parameters: Optional[Dict[str, Any]] = None,
        game_phase: str = GamePhase.EARLY_GAME.value,
        confidence: float = 0.5,
    ) -> OpponentAction:
        """Record an observed action performed by an opponent.

        Auto-registers the opponent if it has not been seen before.
        """
        with self._lock:
            if opponent_id not in self._profiles_by_opponent:
                self.register_opponent(opponent_id)

            action = self._record_action_internal(
                opponent_id,
                kind,
                action_type,
                parameters or {},
                game_phase,
                confidence,
            )

            profile = self._profiles.get(self._profiles_by_opponent[opponent_id])
            if profile is not None:
                profile.last_seen = action.timestamp

            self._emit_event(
                OpponentEventKind.ACTION_RECORDED,
                opponent_id,
                {"action_id": action.id, "kind": kind.value, "action_type": action_type},
            )
            return action

    # ------------------------------------------------------------------
    # Profile management
    # ------------------------------------------------------------------

    def get_profile(self, opponent_id: str) -> Optional[StrategyProfile]:
        """Return the profile for an opponent, or None if unknown."""
        with self._lock:
            pid = self._profiles_by_opponent.get(opponent_id)
            if pid is None:
                return None
            return self._profiles.get(pid)

    def list_profiles(
        self, archetype: Optional[PlayerArchetype] = None
    ) -> List[Dict[str, Any]]:
        """List all profiles, optionally filtered by archetype."""
        with self._lock:
            profiles = self._profiles.values()
            if archetype is not None:
                profiles = [p for p in profiles if p.archetype == archetype]
            return [p.to_dict() for p in profiles]

    def remove_profile(self, opponent_id: str) -> bool:
        """Remove an opponent and all associated data. Returns True if removed."""
        with self._lock:
            pid = self._profiles_by_opponent.pop(opponent_id, None)
            if pid is None:
                return False
            self._profiles.pop(pid, None)

            for aid in self._actions_by_opponent.pop(opponent_id, []):
                self._actions.pop(aid, None)
            for pred_id in self._predictions_by_opponent.pop(opponent_id, []):
                self._predictions.pop(pred_id, None)
            for wid in self._weaknesses_by_opponent.pop(opponent_id, []):
                self._weaknesses.pop(wid, None)
            for cid in self._counters_by_opponent.pop(opponent_id, []):
                self._counters.pop(cid, None)

            self._adaptation_history.pop(opponent_id, None)
            self._last_strategy.pop(opponent_id, None)
            self._last_archetype.pop(opponent_id, None)
            return True

    def update_profile(self, opponent_id: str) -> Optional[StrategyProfile]:
        """Recompute the profile from observed actions."""
        with self._lock:
            pid = self._profiles_by_opponent.get(opponent_id)
            if pid is None:
                return None
            profile = self._profiles[pid]
            actions = self._get_actions(opponent_id)

            if not actions:
                profile.confidence = 0.0
                self._emit_event(
                    OpponentEventKind.PROFILE_UPDATED,
                    opponent_id,
                    {"reason": "no_actions"},
                )
                return profile

            metrics = self._compute_metrics(actions)
            profile.metric_averages = metrics

            counts: Dict[str, int] = {}
            for act in actions:
                counts[act.action_type] = counts.get(act.action_type, 0) + 1
            profile.action_counts = counts
            profile.last_seen = actions[-1].timestamp
            profile.adaptation_score = metrics.get("adaptation_score", 0.0)

            archetype = self._classify_archetype(metrics)
            previous_archetype = profile.archetype
            profile.archetype = archetype

            strategies = self._rank_strategies(metrics)
            profile.strategies = strategies
            sample_factor = min(1.0, len(actions) / float(self._FULL_CONFIDENCE_SAMPLES))
            profile.confidence = round(sample_factor, 4)

            if (
                previous_archetype != PlayerArchetype.UNKNOWN
                and previous_archetype != archetype
            ):
                self._emit_event(
                    OpponentEventKind.ARCHETYPE_CHANGED,
                    opponent_id,
                    {
                        "old": previous_archetype.value,
                        "new": archetype.value,
                    },
                )

            last_arch = self._last_archetype.get(opponent_id)
            self._last_archetype[opponent_id] = archetype
            if last_arch is not None and last_arch != archetype:
                self._emit_event(
                    OpponentEventKind.STRATEGY_CHANGED,
                    opponent_id,
                    {"old_archetype": last_arch.value, "new_archetype": archetype.value},
                )

            self._emit_event(
                OpponentEventKind.PROFILE_UPDATED,
                opponent_id,
                {
                    "archetype": archetype.value,
                    "top_strategy": strategies[0].value if strategies else None,
                    "sample_count": len(actions),
                },
            )
            return profile

    # ------------------------------------------------------------------
    # Archetype and strategy detection
    # ------------------------------------------------------------------

    def _classify_archetype(self, metrics: Dict[str, float]) -> PlayerArchetype:
        """Score all archetypes against the metrics and return the best fit."""
        if not metrics:
            return PlayerArchetype.UNKNOWN

        scores: Dict[PlayerArchetype, float] = {}
        for archetype, indicators in _ARCHETYPE_INDICATORS.items():
            score = 0.0
            total_weight = 0.0
            for metric_name, weight in indicators.items():
                value = metrics.get(metric_name, 0.0)
                score += value * weight
                total_weight += weight
            scores[archetype] = score / total_weight if total_weight > 0 else 0.0

        best = max(scores, key=scores.get)
        best_score = scores[best]
        if best_score < 0.2:
            return PlayerArchetype.UNKNOWN
        return best

    def _rank_strategies(self, metrics: Dict[str, float]) -> List[StrategyType]:
        """Rank strategies by how well the metrics match each indicator set."""
        if not metrics:
            return [StrategyType.ADAPTIVE]

        scores: Dict[StrategyType, float] = {}
        for strategy, indicators in _STRATEGY_INDICATORS.items():
            score = 0.0
            total_weight = 0.0
            for metric_name, weight in indicators.items():
                value = metrics.get(metric_name, 0.0)
                score += value * weight
                total_weight += weight
            scores[strategy] = score / total_weight if total_weight > 0 else 0.0

        ranked = sorted(scores.items(), key=lambda item: item[1], reverse=True)
        return [s for s, _ in ranked if scores[s] > 0.05]

    def detect_archetype(self, opponent_id: str) -> Optional[Dict[str, Any]]:
        """Classify an opponent's play style and return the result."""
        with self._lock:
            actions = self._get_actions(opponent_id)
            if not actions:
                profile = self.get_profile(opponent_id)
                if profile is None:
                    return None
                return {
                    "opponent_id": opponent_id,
                    "archetype": profile.archetype.value,
                    "confidence": 0.0,
                }
            metrics = self._compute_metrics(actions)
            archetype = self._classify_archetype(metrics)
            scores = {}
            for arch, indicators in _ARCHETYPE_INDICATORS.items():
                score = 0.0
                total_weight = 0.0
                for metric_name, weight in indicators.items():
                    score += metrics.get(metric_name, 0.0) * weight
                    total_weight += weight
                scores[arch.value] = round(score / total_weight, 4) if total_weight else 0.0

            pid = self._profiles_by_opponent.get(opponent_id)
            if pid is not None:
                profile = self._profiles[pid]
                profile.archetype = archetype
                profile.metric_averages = metrics

            return {
                "opponent_id": opponent_id,
                "archetype": archetype.value,
                "confidence": round(scores.get(archetype.value, 0.0), 4),
                "all_scores": scores,
            }

    def detect_strategy(self, opponent_id: str) -> Optional[Dict[str, Any]]:
        """Identify the most likely active strategy of an opponent."""
        with self._lock:
            actions = self._get_actions(opponent_id)
            if not actions:
                profile = self.get_profile(opponent_id)
                if profile is None:
                    return None
                return {
                    "opponent_id": opponent_id,
                    "strategies": [s.value for s in profile.strategies],
                    "primary": profile.strategies[0].value if profile.strategies else None,
                    "confidence": 0.0,
                }
            metrics = self._compute_metrics(actions)
            strategies = self._rank_strategies(metrics)
            primary = strategies[0] if strategies else StrategyType.ADAPTIVE
            return {
                "opponent_id": opponent_id,
                "strategies": [s.value for s in strategies],
                "primary": primary.value,
                "confidence": round(metrics.get("adaptation_score", 0.0), 4),
            }

    # ------------------------------------------------------------------
    # Move prediction
    # ------------------------------------------------------------------

    def predict_move(
        self,
        opponent_id: str,
        horizon: int = 1,
        context: Optional[Dict[str, Any]] = None,
    ) -> Optional[MovePrediction]:
        """Forecast the next move(s) of an opponent.

        Uses recency-weighted action frequency analysis. Predictions are
        weighted by game phase when the context supplies one. Confidence
        combines a base value, a sample-size factor, and a consistency
        factor derived from how dominant the top action is.
        """
        with self._lock:
            actions = self._get_actions(opponent_id)
            if not actions:
                return None

            ctx = context or {}
            target_phase = ctx.get("game_phase")

            # Recency-weighted frequency of action types.
            weights: Dict[str, float] = {}
            total_weight = 0.0
            action_count = len(actions)
            for index, act in enumerate(actions):
                age = action_count - index - 1
                recency_weight = self._RECENCY_DECAY ** age
                phase_weight = 1.0
                if target_phase is not None and act.game_phase == target_phase:
                    phase_weight = 1.5
                combined = recency_weight * phase_weight * act.confidence
                weights[act.action_type] = weights.get(act.action_type, 0.0) + combined
                total_weight += combined

            if total_weight <= 0 or not weights:
                return None

            ranked = sorted(weights.items(), key=lambda item: item[1], reverse=True)
            top_action, top_weight = ranked[0]
            top_probability = top_weight / total_weight

            alternatives = [
                {"action": a, "probability": round(w / total_weight, 4)}
                for a, w in ranked[1:6]
            ]

            sample_factor = min(1.0, action_count / float(self._FULL_CONFIDENCE_SAMPLES))
            consistency_factor = top_probability
            confidence = (
                self._BASE_PREDICTION_CONFIDENCE
                * sample_factor
                * consistency_factor
            )

            phase_note = ""
            if target_phase is not None:
                phase_note = f" Weighted toward phase '{target_phase}'."

            reasoning = (
                f"Predicted based on recency-weighted action frequency "
                f"over {action_count} observations. "
                f"'{top_action}' appears most frequently.{phase_note}"
            )

            prediction = MovePrediction(
                opponent_id=opponent_id,
                predicted_action=top_action,
                probability=round(top_probability, 4),
                alternatives=alternatives,
                reasoning=reasoning,
                horizon=max(1, horizon),
                confidence=round(confidence, 4),
            )
            self._predictions[prediction.id] = prediction
            self._predictions_by_opponent.setdefault(opponent_id, []).append(prediction.id)
            self._enforce_prediction_limits(opponent_id)
            self._total_predictions += 1

            self._emit_event(
                OpponentEventKind.PREDICTION_MADE,
                opponent_id,
                {"prediction_id": prediction.id, "predicted_action": top_action},
            )
            return prediction

    # ------------------------------------------------------------------
    # Weakness detection
    # ------------------------------------------------------------------

    def detect_weaknesses(self, opponent_id: str) -> List[WeaknessReport]:
        """Identify exploitable patterns in opponent behavior."""
        with self._lock:
            actions = self._get_actions(opponent_id)
            if not actions:
                return []

            metrics = self._compute_metrics(actions)
            reports: List[WeaknessReport] = []

            # PREDICTABLE_ROUTINE: low diversity and a dominant action type.
            if metrics.get("diversity", 1.0) < 0.3:
                top_type = ""
                top_count = 0
                for act_type, count in self._action_type_counts(opponent_id).items():
                    if count > top_count:
                        top_count = count
                        top_type = act_type
                reports.append(self._make_weakness(
                    opponent_id, WeaknessType.PREDICTABLE_ROUTINE,
                    "Opponent relies on a narrow action set, dominated by "
                    f"'{top_type}'.",
                    "Predict and intercept the repeated action.",
                    confidence=0.8,
                    evidence=[f"diversity={metrics['diversity']:.2f}",
                             f"top_action={top_type} ({top_count} times)"],
                    severity=Severity.HIGH,
                ))

            # WEAK_DEFENSE: very low defend ratio.
            if metrics.get("defend_ratio", 0.0) < 0.1 and len(actions) >= 5:
                reports.append(self._make_weakness(
                    opponent_id, WeaknessType.WEAK_DEFENSE,
                    "Opponent neglects defensive actions, leaving positions "
                    "exposed to direct assault.",
                    "Apply sustained frontal pressure on undefended fronts.",
                    confidence=0.75,
                    evidence=[f"defend_ratio={metrics['defend_ratio']:.2f}"],
                    severity=Severity.HIGH,
                ))

            # OVER_AGGRESSION: high attack ratio and no retreats.
            if (metrics.get("attack_ratio", 0.0) > 0.5
                    and metrics.get("retreat_ratio", 0.0) < 0.05):
                reports.append(self._make_weakness(
                    opponent_id, WeaknessType.OVER_AGGRESSION,
                    "Opponent commits heavily to attacks without retreating, "
                    "leaving economy and defense exposed.",
                    "Bait the over-extension and counter-attack the base.",
                    confidence=0.82,
                    evidence=[f"attack_ratio={metrics['attack_ratio']:.2f}",
                             f"retreat_ratio={metrics['retreat_ratio']:.2f}"],
                    severity=Severity.HIGH,
                ))

            # NO_ADAPTATION: very low adaptation score over enough samples.
            if metrics.get("adaptation_score", 0.0) < 0.15 and len(actions) >= 8:
                reports.append(self._make_weakness(
                    opponent_id, WeaknessType.NO_ADAPTATION,
                    "Opponent's action distribution barely changes over time, "
                    "indicating a static strategy.",
                    "Shift to a strategy they have not yet faced.",
                    confidence=0.7,
                    evidence=[f"adaptation_score={metrics['adaptation_score']:.2f}"],
                    severity=Severity.MEDIUM,
                ))

            # POOR_ECONOMY: low resource ratio.
            if metrics.get("resource_ratio", 0.0) < 0.1 and len(actions) >= 5:
                reports.append(self._make_weakness(
                    opponent_id, WeaknessType.POOR_ECONOMY,
                    "Opponent under-invests in resource gathering, limiting "
                    "long-term production capacity.",
                    "Raid economy lines and deny expansions.",
                    confidence=0.68,
                    evidence=[f"resource_ratio={metrics['resource_ratio']:.2f}"],
                    severity=Severity.MEDIUM,
                ))

            # REPEATED_TIMING: attacks concentrated in a single phase.
            phase_attack_counts = self._phase_action_counts(opponent_id, ObservationKind.ATTACK)
            total_attacks = sum(phase_attack_counts.values())
            if total_attacks >= 4:
                for phase, count in phase_attack_counts.items():
                    if count / total_attacks >= 0.7:
                        reports.append(self._make_weakness(
                            opponent_id, WeaknessType.REPEATED_TIMING,
                            f"Opponent concentrates attacks in the {phase} "
                            f"({count}/{total_attacks}).",
                            "Pre-position defenders before the timing window.",
                            confidence=0.72,
                            evidence=[f"phase={phase}", f"attacks={count}/{total_attacks}"],
                            severity=Severity.MEDIUM,
                        ))
                        break

            # LIMITED_UNIT_MIX: low build diversity.
            build_types = {
                act.action_type for act in actions if act.kind == ObservationKind.BUILD
            }
            if 0 < len(build_types) <= 1 and len(actions) >= 5:
                reports.append(self._make_weakness(
                    opponent_id, WeaknessType.LIMITED_UNIT_MIX,
                    "Opponent builds a narrow set of structures or units.",
                    "Produce units that hard-counter the limited mix.",
                    confidence=0.65,
                    evidence=[f"distinct_build_types={len(build_types)}"],
                    severity=Severity.LOW,
                ))

            # POOR_SCOUTING: low move and reposition ratio.
            if (metrics.get("move_ratio", 0.0) < 0.1
                    and metrics.get("reposition_ratio", 0.0) < 0.1
                    and len(actions) >= 5):
                reports.append(self._make_weakness(
                    opponent_id, WeaknessType.POOR_SCOUTING,
                    "Opponent shows little movement or scouting activity.",
                    "Conceal build order and take hidden expansions.",
                    confidence=0.6,
                    evidence=[f"move_ratio={metrics['move_ratio']:.2f}",
                             f"reposition_ratio={metrics['reposition_ratio']:.2f}"],
                    severity=Severity.LOW,
                ))

            # OVERCOMMIT: high aggression with low diversity.
            if (metrics.get("aggression_rate", 0.0) > 0.6
                    and metrics.get("diversity", 1.0) < 0.4):
                reports.append(self._make_weakness(
                    opponent_id, WeaknessType.OVERCOMMIT,
                    "Opponent over-commits resources to a single objective "
                    "with little diversification.",
                    "Exploit the opposite front at the commitment point.",
                    confidence=0.7,
                    evidence=[f"aggression_rate={metrics['aggression_rate']:.2f}",
                             f"diversity={metrics['diversity']:.2f}"],
                    severity=Severity.MEDIUM,
                ))

            # Store reports and update the profile weakness list.
            weakness_ids: List[str] = []
            for report in reports:
                self._weaknesses[report.id] = report
                weakness_ids.append(report.id)
                self._total_weaknesses_detected += 1
                self._emit_event(
                    OpponentEventKind.WEAKNESS_DETECTED,
                    opponent_id,
                    {"weakness_id": report.id, "type": report.weakness_type.value},
                )

            existing = self._weaknesses_by_opponent.setdefault(opponent_id, [])
            if len(existing) > self._MAX_WEAKNESSES_PER_OPPONENT:
                overflow = len(existing) - self._MAX_WEAKNESSES_PER_OPPONENT
                for wid in existing[:overflow]:
                    self._weaknesses.pop(wid, None)
                self._weaknesses_by_opponent[opponent_id] = existing[overflow:]

            pid = self._profiles_by_opponent.get(opponent_id)
            if pid is not None:
                profile = self._profiles[pid]
                profile.weaknesses = [r.id for r in reports]

            return reports

    def _make_weakness(
        self,
        opponent_id: str,
        weakness_type: WeaknessType,
        description: str,
        exploit_suggestion: str,
        confidence: float,
        evidence: List[str],
        severity: Severity,
    ) -> WeaknessReport:
        return WeaknessReport(
            opponent_id=opponent_id,
            weakness_type=weakness_type,
            description=description,
            exploit_suggestion=exploit_suggestion,
            confidence=confidence,
            evidence=evidence,
            severity=severity,
        )

    def _action_type_counts(self, opponent_id: str) -> Dict[str, int]:
        counts: Dict[str, int] = {}
        for act in self._get_actions(opponent_id):
            counts[act.action_type] = counts.get(act.action_type, 0) + 1
        return counts

    def _phase_action_counts(
        self, opponent_id: str, kind: ObservationKind
    ) -> Dict[str, int]:
        counts: Dict[str, int] = {}
        for act in self._get_actions(opponent_id):
            if act.kind == kind:
                counts[act.game_phase] = counts.get(act.game_phase, 0) + 1
        return counts

    # ------------------------------------------------------------------
    # Counter-strategy generation
    # ------------------------------------------------------------------

    def generate_counter_strategy(
        self, opponent_id: str, weakness_id: str
    ) -> Optional[CounterStrategy]:
        """Suggest a counter-strategy for a detected weakness."""
        with self._lock:
            weakness = self._weaknesses.get(weakness_id)
            if weakness is None or weakness.opponent_id != opponent_id:
                return None

            playbook = _COUNTER_PLAYBOOK.get(weakness.weakness_type)
            if playbook is None:
                return None

            name, description, actions = playbook
            priority = self._severity_to_priority(weakness.severity)

            counter = CounterStrategy(
                opponent_id=opponent_id,
                strategy_name=name,
                description=description,
                actions=list(actions),
                expected_outcome=(
                    f"Exploits {weakness.weakness_type.value} to gain a "
                    "positional or economic advantage."
                ),
                confidence=weakness.confidence,
                priority=round(priority, 4),
            )
            self._counters[counter.id] = counter
            self._counters_by_opponent.setdefault(opponent_id, []).append(counter.id)
            self._enforce_counter_limits(opponent_id)
            self._total_counters_generated += 1

            self._emit_event(
                OpponentEventKind.COUNTER_GENERATED,
                opponent_id,
                {"counter_id": counter.id, "weakness_id": weakness_id},
            )
            return counter

    def _severity_to_priority(self, severity: Severity) -> float:
        return {
            Severity.LOW: 0.3,
            Severity.MEDIUM: 0.55,
            Severity.HIGH: 0.8,
            Severity.CRITICAL: 1.0,
        }.get(severity, 0.5)

    def _enforce_counter_limits(self, opponent_id: str) -> None:
        ids = self._counters_by_opponent.get(opponent_id, [])
        if len(ids) <= self._MAX_COUNTERS_PER_OPPONENT:
            return
        overflow = len(ids) - self._MAX_COUNTERS_PER_OPPONENT
        for cid in ids[:overflow]:
            self._counters.pop(cid, None)
        self._counters_by_opponent[opponent_id] = ids[overflow:]

    # ------------------------------------------------------------------
    # Adaptation tracking
    # ------------------------------------------------------------------

    def check_adaptation(self, opponent_id: str) -> Optional[AdaptationEvent]:
        """Detect whether an opponent changed strategy.

        Compares the strategy inferred from the most recent action window
        to the previously recorded strategy. Emits an AdaptationEvent when
        a meaningful change is detected.
        """
        with self._lock:
            actions = self._get_actions(opponent_id)
            if len(actions) < self._ADAPTATION_WINDOW:
                return None

            recent = actions[-self._ADAPTATION_WINDOW:]
            recent_metrics = self._compute_metrics(recent)
            recent_strategies = self._rank_strategies(recent_metrics)
            new_strategy = recent_strategies[0] if recent_strategies else StrategyType.ADAPTIVE

            old_strategy = self._last_strategy.get(opponent_id, StrategyType.ADAPTIVE)
            if old_strategy == new_strategy:
                return None

            event = AdaptationEvent(
                opponent_id=opponent_id,
                old_strategy=old_strategy,
                new_strategy=new_strategy,
                confidence=round(recent_metrics.get("adaptation_score", 0.0), 4),
                evidence=[
                    f"old_strategy={old_strategy.value}",
                    f"new_strategy={new_strategy.value}",
                    f"window={self._ADAPTATION_WINDOW} actions",
                ],
            )
            history = self._adaptation_history.setdefault(opponent_id, [])
            history.append(event)
            if len(history) > self._MAX_ADAPTATION_HISTORY:
                self._adaptation_history[opponent_id] = history[-self._MAX_ADAPTATION_HISTORY:]
            self._last_strategy[opponent_id] = new_strategy
            self._total_adaptations += 1

            self._emit_event(
                OpponentEventKind.ADAPTATION_DETECTED,
                opponent_id,
                {
                    "old_strategy": old_strategy.value,
                    "new_strategy": new_strategy.value,
                },
            )
            return event

    # ------------------------------------------------------------------
    # Prediction feedback and history
    # ------------------------------------------------------------------

    def get_prediction_history(
        self, opponent_id: str, limit: int = 20
    ) -> List[MovePrediction]:
        """Return past predictions for an opponent, most-recent last."""
        with self._lock:
            ids = self._predictions_by_opponent.get(opponent_id, [])
            return [
                self._predictions[pid]
                for pid in ids[-limit:]
                if pid in self._predictions
            ]

    def record_prediction_outcome(
        self, prediction_id: str, actual_action: str, correct: bool
    ) -> bool:
        """Record the actual outcome of a prediction for learning feedback."""
        with self._lock:
            prediction = self._predictions.get(prediction_id)
            if prediction is None:
                return False
            prediction.actual_action = actual_action
            prediction.correct = correct
            if correct:
                self._total_correct += 1
            self._emit_event(
                OpponentEventKind.PREDICTION_RESOLVED,
                prediction.opponent_id,
                {
                    "prediction_id": prediction_id,
                    "actual_action": actual_action,
                    "correct": correct,
                },
            )
            return True

    # ------------------------------------------------------------------
    # Event handling
    # ------------------------------------------------------------------

    def register_event_handler(
        self,
        event_kind: OpponentEventKind,
        handler: Callable[[OpponentEvent], None],
    ) -> str:
        """Register a handler for a specific event kind.

        Returns a handler id that uniquely identifies the registration.
        """
        with self._lock:
            handler_id = uuid.uuid4().hex
            key = event_kind.value
            self._event_handlers.setdefault(key, []).append((handler_id, handler))
            return handler_id

    def list_events(
        self,
        opponent_id: Optional[str] = None,
        limit: int = 100,
    ) -> List[OpponentEvent]:
        """Return recent events, optionally filtered by opponent."""
        with self._lock:
            events = list(self._events)
            if opponent_id is not None:
                events = [e for e in events if e.opponent_id == opponent_id]
            return events[-limit:]

    # ------------------------------------------------------------------
    # Import / export
    # ------------------------------------------------------------------

    def export_profile(self, opponent_id: str) -> Optional[Dict[str, Any]]:
        """Serialize an opponent profile (and its data) to a dict."""
        with self._lock:
            profile = self.get_profile(opponent_id)
            if profile is None:
                return None
            actions = [a.to_dict() for a in self._get_actions(opponent_id)]
            predictions = [
                self._predictions[pid].to_dict()
                for pid in self._predictions_by_opponent.get(opponent_id, [])
                if pid in self._predictions
            ]
            weaknesses = [
                self._weaknesses[wid].to_dict()
                for wid in self._weaknesses_by_opponent.get(opponent_id, [])
                if wid in self._weaknesses
            ]
            counters = [
                self._counters[cid].to_dict()
                for cid in self._counters_by_opponent.get(opponent_id, [])
                if cid in self._counters
            ]
            return {
                "profile": profile.to_dict(),
                "actions": actions,
                "predictions": predictions,
                "weaknesses": weaknesses,
                "counter_strategies": counters,
            }

    def import_profile(self, data: Dict[str, Any]) -> Optional[StrategyProfile]:
        """Import a previously exported opponent profile.

        Reconstructs the profile, actions, and (optionally) predictions.
        Returns the imported profile, or None if the data is invalid.
        """
        with self._lock:
            profile_data = data.get("profile", {})
            opponent_id = profile_data.get("opponent_id", "")
            if not opponent_id:
                return None

            try:
                archetype = PlayerArchetype(profile_data.get("archetype", "unknown"))
            except ValueError:
                archetype = PlayerArchetype.UNKNOWN

            self.register_opponent(opponent_id, archetype)
            profile = self.get_profile(opponent_id)
            if profile is None:
                return None

            for action_data in data.get("actions", []):
                try:
                    kind = ObservationKind(action_data.get("kind", "move"))
                except ValueError:
                    kind = ObservationKind.MOVE
                self._record_action_internal(
                    opponent_id,
                    kind,
                    action_data.get("action_type", ""),
                    action_data.get("parameters", {}),
                    action_data.get("game_phase", GamePhase.EARLY_GAME.value),
                    action_data.get("confidence", 0.5),
                )

            self.update_profile(opponent_id)
            return profile

    # ------------------------------------------------------------------
    # Status and snapshot
    # ------------------------------------------------------------------

    def get_status(self) -> Dict[str, Any]:
        """Return a dictionary with current engine statistics."""
        with self._lock:
            total_predictions = self._total_predictions
            total_correct = self._total_correct
            accuracy = (
                total_correct / total_predictions if total_predictions > 0 else 0.0
            )

            confidences = [p.confidence for p in self._predictions.values()]
            avg_confidence = (
                sum(confidences) / len(confidences) if confidences else 0.0
            )

            archetype_dist: Dict[str, int] = {}
            for profile in self._profiles.values():
                key = profile.archetype.value
                archetype_dist[key] = archetype_dist.get(key, 0) + 1

            return {
                "total_opponents": len(self._profiles_by_opponent),
                "total_profiles": len(self._profiles),
                "total_actions": len(self._actions),
                "total_predictions": total_predictions,
                "total_correct": total_correct,
                "prediction_accuracy": round(accuracy, 4),
                "avg_confidence": round(avg_confidence, 4),
                "total_weaknesses": len(self._weaknesses),
                "total_weaknesses_detected": self._total_weaknesses_detected,
                "total_counter_strategies": len(self._counters),
                "total_counters_generated": self._total_counters_generated,
                "total_adaptations": self._total_adaptations,
                "total_events": len(self._events),
                "archetype_distribution": archetype_dist,
            }

    def get_snapshot(self) -> OpponentSnapshot:
        """Return a point-in-time snapshot of the modeler state."""
        with self._lock:
            profiles = [p.to_dict() for p in self._profiles.values()]
            predictions = [
                p.to_dict()
                for p in list(self._predictions.values())[-50:]
            ]
            weaknesses = [w.to_dict() for w in self._weaknesses.values()]
            counters = [c.to_dict() for c in self._counters.values()]
            return OpponentSnapshot(
                profiles=profiles,
                predictions=predictions,
                weaknesses=weaknesses,
                counter_strategies=counters,
                stats=self.get_status(),
            )

    def reset(self) -> None:
        """Clear all modeled data and re-seed the default demo opponents."""
        with self._lock:
            self._profiles.clear()
            self._profiles_by_opponent.clear()
            self._actions.clear()
            self._actions_by_opponent.clear()
            self._predictions.clear()
            self._predictions_by_opponent.clear()
            self._weaknesses.clear()
            self._weaknesses_by_opponent.clear()
            self._counters.clear()
            self._counters_by_opponent.clear()
            self._adaptation_history.clear()
            self._last_strategy.clear()
            self._last_archetype.clear()
            self._events.clear()
            self._event_handlers.clear()
            self._total_predictions = 0
            self._total_correct = 0
            self._total_weaknesses_detected = 0
            self._total_counters_generated = 0
            self._total_adaptations = 0
            self._seed_default_data()


# ---------------------------------------------------------------------------
# Module-level accessor
# ---------------------------------------------------------------------------

def get_opponent_modeler() -> OpponentModelerEngine:
    """Return the singleton OpponentModelerEngine instance."""
    return OpponentModelerEngine.get_instance()
