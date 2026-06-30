"""
SparkLabs Agent - Plan Recognition

Infers the goals and plans of other agents or players based on observed
actions. Maintains a library of known goals with associated action
sequences, and matches observed action streams against these patterns to
generate ranked goal hypotheses.

As more actions are observed, confidence in hypotheses is updated: actions
that align with a hypothesis increase its confidence, while actions that
contradict it decrease confidence. The system can also detect anomalies
where observed actions do not fit any known goal pattern.

The module is the inverse of planning: rather than choosing actions to
achieve a goal, it determines the goal from the actions. This enables
responsive AI that anticipates player intentions, opponents that adapt
to observed strategies, and cooperative agents that support teammates.

Architecture:
  PlanRecognitionEngine (Singleton)
    |-- GoalPattern (known goal with action sequence)
    |-- ActionStep (single step within a goal pattern)
    |-- ObservedAction (recorded action from an entity)
    |-- GoalHypothesis (ranked guess about an entity's goal)
    |-- ObservationStream (per-entity observation history)
    |-- RecognitionEvent (audit trail of recognition operations)
    |-- PlanRecognitionSnapshot (engine status summary)
"""

from __future__ import annotations

import datetime
import threading
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class HypothesisStatus(Enum):
    """Lifecycle state of a goal hypothesis."""

    ACTIVE = "active"
    CONFIRMED = "confirmed"
    REJECTED = "rejected"
    SUPERSEDED = "superseded"


class ActionMatchType(Enum):
    """Degree to which an observed action matches a planned step."""

    EXACT = "exact"
    PARTIAL = "partial"
    ORDERED = "ordered"
    UNORDERED = "unordered"
    NONE = "none"


class ObservationSource(Enum):
    """How an observation was obtained."""

    DIRECT = "direct"
    INFERRED = "inferred"
    REPORTED = "reported"


class RecognitionEventKind(Enum):
    """Kind of events emitted by the recognition engine."""

    OBSERVATION_RECORDED = "observation_recorded"
    HYPOTHESIS_CREATED = "hypothesis_created"
    HYPOTHESIS_UPDATED = "hypothesis_updated"
    HYPOTHESIS_CONFIRMED = "hypothesis_confirmed"
    HYPOTHESIS_REJECTED = "hypothesis_rejected"
    ANOMALY_DETECTED = "anomaly_detected"
    GOAL_LIBRARY_UPDATED = "goal_library_updated"


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------


def _now() -> datetime.datetime:
    """Return the current UTC timestamp."""
    return datetime.datetime.utcnow()


def _timestamp_iso(ts: Optional[datetime.datetime]) -> Optional[str]:
    """Convert a datetime to an ISO 8601 string (or None)."""
    if ts is None:
        return None
    return ts.isoformat()


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------


@dataclass
class ActionStep:
    """A single step within a goal pattern's action sequence.

    Attributes:
        action_type: The type of action expected at this step.
        parameters: Expected parameters and their values. An empty dict
            means any parameters are acceptable.
        optional: When True, a missing step does not disqualify the
            hypothesis. The step may be skipped without penalty.
        description: Human-readable description of this step.
    """

    action_type: str = ""
    parameters: Dict[str, Any] = field(default_factory=dict)
    optional: bool = False
    description: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "action_type": self.action_type,
            "parameters": dict(self.parameters),
            "optional": self.optional,
            "description": self.description,
        }


@dataclass
class GoalPattern:
    """A known goal and the action sequences that achieve it.

    Attributes:
        id: Unique identifier for this pattern.
        name: Short human-readable name.
        description: Longer description of the goal.
        action_sequence: Ordered steps that achieve this goal.
        alternative_sequences: Additional sequences that also achieve the
            goal, providing flexibility in matching.
        tags: Categorization labels for filtering.
        metadata: Arbitrary additional data.
    """

    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = ""
    description: str = ""
    action_sequence: List[ActionStep] = field(default_factory=list)
    alternative_sequences: List[List[ActionStep]] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "action_sequence": [s.to_dict() for s in self.action_sequence],
            "alternative_sequences": [
                [s.to_dict() for s in seq] for seq in self.alternative_sequences
            ],
            "tags": list(self.tags),
            "metadata": dict(self.metadata),
        }

    def all_sequences(self) -> List[List[ActionStep]]:
        """Return the primary sequence followed by all alternatives."""
        sequences: List[List[ActionStep]] = [self.action_sequence]
        sequences.extend(self.alternative_sequences)
        return sequences

    @property
    def total_steps(self) -> int:
        """Number of steps in the primary action sequence."""
        return len(self.action_sequence)


@dataclass
class ObservedAction:
    """An action observed from an entity.

    Attributes:
        id: Unique observation identifier.
        observed_entity_id: The entity that performed the action.
        action_type: The type of action performed.
        parameters: The parameters of the action.
        timestamp: When the observation was recorded.
        source: How the observation was obtained.
        confidence: Reliability of this observation in [0.0, 1.0].
    """

    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    observed_entity_id: str = ""
    action_type: str = ""
    parameters: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime.datetime = field(default_factory=_now)
    source: ObservationSource = ObservationSource.DIRECT
    confidence: float = 1.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "observed_entity_id": self.observed_entity_id,
            "action_type": self.action_type,
            "parameters": dict(self.parameters),
            "timestamp": _timestamp_iso(self.timestamp),
            "source": self.source.value,
            "confidence": self.confidence,
        }


@dataclass
class GoalHypothesis:
    """A ranked guess about what an entity is trying to achieve.

    Attributes:
        id: Unique hypothesis identifier.
        observed_entity_id: The entity being analyzed.
        goal_pattern_id: The goal pattern this hypothesis tracks.
        confidence: Current confidence in [0.0, 1.0].
        matched_steps: Indices of pattern steps matched so far.
        unmatched_steps: Indices of pattern steps not yet matched.
        current_step_index: Next expected step in the sequence.
        status: Lifecycle state of this hypothesis.
        created_at: When the hypothesis was created.
        updated_at: When the hypothesis was last updated.
        evidence: IDs of observations that support this hypothesis.
    """

    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    observed_entity_id: str = ""
    goal_pattern_id: str = ""
    confidence: float = 0.0
    matched_steps: List[int] = field(default_factory=list)
    unmatched_steps: List[int] = field(default_factory=list)
    current_step_index: int = 0
    status: HypothesisStatus = HypothesisStatus.ACTIVE
    created_at: datetime.datetime = field(default_factory=_now)
    updated_at: datetime.datetime = field(default_factory=_now)
    evidence: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "observed_entity_id": self.observed_entity_id,
            "goal_pattern_id": self.goal_pattern_id,
            "confidence": self.confidence,
            "matched_steps": list(self.matched_steps),
            "unmatched_steps": list(self.unmatched_steps),
            "current_step_index": self.current_step_index,
            "status": self.status.value,
            "created_at": _timestamp_iso(self.created_at),
            "updated_at": _timestamp_iso(self.updated_at),
            "evidence": list(self.evidence),
        }


@dataclass
class ObservationStream:
    """Per-entity observation history and associated hypotheses.

    Attributes:
        observed_entity_id: The entity being observed.
        actions: Chronologically ordered observations.
        hypotheses: Current hypotheses for this entity.
        created_at: When the stream was created.
        last_updated: When the stream was last modified.
    """

    observed_entity_id: str = ""
    actions: List[ObservedAction] = field(default_factory=list)
    hypotheses: List[GoalHypothesis] = field(default_factory=list)
    created_at: datetime.datetime = field(default_factory=_now)
    last_updated: datetime.datetime = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "observed_entity_id": self.observed_entity_id,
            "actions": [a.to_dict() for a in self.actions],
            "hypotheses": [h.to_dict() for h in self.hypotheses],
            "created_at": _timestamp_iso(self.created_at),
            "last_updated": _timestamp_iso(self.last_updated),
            "action_count": len(self.actions),
            "hypothesis_count": len(self.hypotheses),
        }


@dataclass
class RecognitionEvent:
    """An event emitted by the recognition engine.

    Attributes:
        id: Unique event identifier.
        kind: The type of event.
        observed_entity_id: Related entity, if any.
        hypothesis_id: Related hypothesis, if any.
        goal_pattern_id: Related goal pattern, if any.
        payload: Arbitrary event-specific data.
        timestamp: When the event was emitted.
    """

    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    kind: RecognitionEventKind = RecognitionEventKind.OBSERVATION_RECORDED
    observed_entity_id: Optional[str] = None
    hypothesis_id: Optional[str] = None
    goal_pattern_id: Optional[str] = None
    payload: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime.datetime = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "kind": self.kind.value,
            "observed_entity_id": self.observed_entity_id,
            "hypothesis_id": self.hypothesis_id,
            "goal_pattern_id": self.goal_pattern_id,
            "payload": dict(self.payload),
            "timestamp": _timestamp_iso(self.timestamp),
        }


@dataclass
class PlanRecognitionSnapshot:
    """A point-in-time summary of the recognition engine state.

    Attributes:
        goal_count: Number of registered goal patterns.
        observation_stream_count: Number of observation streams.
        total_observations: Total observations across all streams.
        total_hypotheses: Total hypotheses across all streams.
        stats: Aggregate statistics dictionary.
        timestamp: When the snapshot was taken.
    """

    goal_count: int = 0
    observation_stream_count: int = 0
    total_observations: int = 0
    total_hypotheses: int = 0
    stats: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime.datetime = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "goal_count": self.goal_count,
            "observation_stream_count": self.observation_stream_count,
            "total_observations": self.total_observations,
            "total_hypotheses": self.total_hypotheses,
            "stats": dict(self.stats),
            "timestamp": _timestamp_iso(self.timestamp),
        }


# ---------------------------------------------------------------------------
# Engine
# ---------------------------------------------------------------------------


class PlanRecognitionEngine:
    """Singleton engine that infers goals from observed actions.

    Maintains a library of goal patterns, records observations of entity
    behavior, generates ranked hypotheses about what each entity is
    trying to achieve, and updates confidence as new observations arrive.

    All public methods are thread-safe, protected by a re-entrant lock.
    """

    _instance: Optional["PlanRecognitionEngine"] = None
    _lock: threading.RLock = threading.RLock()

    def __init__(self) -> None:
        if getattr(self, "_initialized", False):
            return

        # Goal library: pattern_id -> GoalPattern
        self._goal_patterns: Dict[str, GoalPattern] = {}

        # Per-entity observation streams
        self._observation_streams: Dict[str, ObservationStream] = {}

        # Hypothesis index for quick lookup by id
        self._hypotheses: Dict[str, GoalHypothesis] = {}

        # Event log and handler registry
        self._events: List[RecognitionEvent] = []
        self._event_handlers: Dict[str, List[Tuple[str, Callable]]] = {}

        # Aggregate statistics
        self._stats: Dict[str, Any] = {
            "total_goal_patterns": 0,
            "total_observation_streams": 0,
            "total_observations": 0,
            "total_hypotheses_created": 0,
            "total_hypotheses_confirmed": 0,
            "total_hypotheses_rejected": 0,
            "total_anomalies_detected": 0,
            "last_observation_at": None,
        }

        self._initialized: bool = True
        self._seed_default_goals()

    @classmethod
    def get_instance(cls) -> "PlanRecognitionEngine":
        """Return the singleton engine instance, creating it on first use."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _seed_default_goals(self) -> None:
        """Populate the goal library with default patterns."""
        # collect_treasure: move to treasure, pick it up, return to base
        collect_treasure = GoalPattern(
            id="collect_treasure",
            name="collect_treasure",
            description="Collect a treasure by moving to it, picking it up, "
                        "and returning to base.",
            action_sequence=[
                ActionStep(
                    action_type="move_to",
                    parameters={"target": "treasure_location"},
                    description="Move to the treasure location.",
                ),
                ActionStep(
                    action_type="pickup",
                    parameters={"item": "treasure"},
                    description="Pick up the treasure.",
                ),
                ActionStep(
                    action_type="return_to",
                    parameters={"target": "base"},
                    description="Return to base with the treasure.",
                ),
            ],
            tags=["collection", "movement"],
            metadata={"difficulty": "easy"},
        )

        # attack_player: approach, attack, retreat
        attack_player = GoalPattern(
            id="attack_player",
            name="attack_player",
            description="Attack a player by approaching, attacking, "
                        "then retreating to safety.",
            action_sequence=[
                ActionStep(
                    action_type="approach",
                    parameters={"target": "player"},
                    description="Approach the target player.",
                ),
                ActionStep(
                    action_type="attack",
                    parameters={"target": "player"},
                    description="Attack the target player.",
                ),
                ActionStep(
                    action_type="retreat",
                    parameters={},
                    description="Retreat to a safe distance.",
                ),
            ],
            tags=["combat", "aggressive"],
            metadata={"difficulty": "medium"},
        )

        # explore_area: move and look around across regions
        explore_area = GoalPattern(
            id="explore_area",
            name="explore_area",
            description="Explore an area by moving to unexplored regions "
                        "and looking around.",
            action_sequence=[
                ActionStep(
                    action_type="move_to",
                    parameters={"region": "unexplored_region"},
                    description="Move to an unexplored region.",
                ),
                ActionStep(
                    action_type="look_around",
                    parameters={},
                    description="Look around the current region.",
                ),
                ActionStep(
                    action_type="move_to",
                    parameters={"region": "next_region"},
                    description="Move to the next region.",
                ),
                ActionStep(
                    action_type="look_around",
                    parameters={},
                    description="Look around the next region.",
                ),
            ],
            tags=["exploration", "movement"],
            metadata={"difficulty": "easy"},
        )

        for pattern in (collect_treasure, attack_player, explore_area):
            self._goal_patterns[pattern.id] = pattern

        self._stats["total_goal_patterns"] = len(self._goal_patterns)

    def _emit_event(
        self,
        kind: RecognitionEventKind,
        observed_entity_id: Optional[str] = None,
        hypothesis_id: Optional[str] = None,
        goal_pattern_id: Optional[str] = None,
        payload: Optional[Dict[str, Any]] = None,
    ) -> RecognitionEvent:
        """Create, store, and dispatch a recognition event."""
        event = RecognitionEvent(
            kind=kind,
            observed_entity_id=observed_entity_id,
            hypothesis_id=hypothesis_id,
            goal_pattern_id=goal_pattern_id,
            payload=payload if payload is not None else {},
        )
        self._events.append(event)

        # Dispatch to registered handlers for this kind
        key = kind.value
        for handler_id, handler in self._event_handlers.get(key, []):
            try:
                handler(event)
            except Exception:
                # Handler errors must not disrupt engine operation
                pass

        return event

    def _get_or_create_stream(self, observed_entity_id: str) -> ObservationStream:
        """Return the stream for an entity, creating one if absent."""
        stream = self._observation_streams.get(observed_entity_id)
        if stream is None:
            stream = ObservationStream(observed_entity_id=observed_entity_id)
            self._observation_streams[observed_entity_id] = stream
            self._stats["total_observation_streams"] = len(self._observation_streams)
        return stream

    def _match_parameters(
        self, observed: Dict[str, Any], expected: Dict[str, Any]
    ) -> ActionMatchType:
        """Compare observed parameters against expected step parameters."""
        if not expected:
            # No expected parameters: any observation is an exact match
            return ActionMatchType.EXACT

        matched = 0
        for key, value in expected.items():
            if key in observed and observed[key] == value:
                matched += 1

        if matched == len(expected):
            return ActionMatchType.EXACT
        if matched > 0:
            return ActionMatchType.PARTIAL
        # Action type matched but no parameters aligned
        return ActionMatchType.PARTIAL

    def _match_sequence(
        self,
        observations: List[ObservedAction],
        sequence: List[ActionStep],
    ) -> Tuple[List[int], List[int], int, List[str]]:
        """Match observations against a single action sequence.

        Returns a tuple of (matched_step_indices, unmatched_step_indices,
        next_step_index, evidence_observation_ids).
        """
        matched: List[int] = []
        evidence: List[str] = []
        step_idx = 0

        for obs in observations:
            if step_idx < len(sequence):
                step = sequence[step_idx]
                if obs.action_type == step.action_type:
                    match = self._match_parameters(obs.parameters, step.parameters)
                    if match != ActionMatchType.NONE:
                        matched.append(step_idx)
                        evidence.append(obs.id)
                        step_idx += 1
                        continue
            # Observation did not advance the sequence
            # Try to find a match in upcoming non-optional steps (unordered)
            found = False
            for future_idx in range(step_idx + 1, len(sequence)):
                step = sequence[future_idx]
                if obs.action_type == step.action_type:
                    match = self._match_parameters(obs.parameters, step.parameters)
                    if match != ActionMatchType.NONE and future_idx not in matched:
                        matched.append(future_idx)
                        evidence.append(obs.id)
                        found = True
                        break
            # If not found, the observation is unmatched for this sequence

        unmatched = [
            i for i in range(len(sequence)) if i not in matched
        ]
        return matched, unmatched, step_idx, evidence

    # ------------------------------------------------------------------
    # Goal library management
    # ------------------------------------------------------------------

    def register_goal_pattern(
        self,
        name: str,
        description: str,
        action_sequence: List[ActionStep],
        alternative_sequences: Optional[List[List[ActionStep]]] = None,
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> GoalPattern:
        """Register a new goal pattern in the library.

        Args:
            name: Short human-readable name for the goal.
            description: Longer description of what the goal achieves.
            action_sequence: Ordered steps that achieve this goal.
            alternative_sequences: Additional sequences that also achieve
                the goal, providing matching flexibility.
            tags: Categorization labels for filtering.
            metadata: Arbitrary additional data.

        Returns:
            The newly created GoalPattern.
        """
        with self._lock:
            pattern = GoalPattern(
                id=uuid.uuid4().hex,
                name=name,
                description=description,
                action_sequence=list(action_sequence),
                alternative_sequences=list(alternative_sequences or []),
                tags=list(tags or []),
                metadata=dict(metadata or {}),
            )
            self._goal_patterns[pattern.id] = pattern
            self._stats["total_goal_patterns"] = len(self._goal_patterns)

            self._emit_event(
                RecognitionEventKind.GOAL_LIBRARY_UPDATED,
                goal_pattern_id=pattern.id,
                payload={"action": "register", "name": name},
            )
            return pattern

    def get_goal_pattern(self, pattern_id: str) -> Optional[GoalPattern]:
        """Return the goal pattern with the given id, or None."""
        with self._lock:
            return self._goal_patterns.get(pattern_id)

    def list_goal_patterns(self, tag: Optional[str] = None) -> List[GoalPattern]:
        """List goal patterns, optionally filtered by tag."""
        with self._lock:
            patterns = list(self._goal_patterns.values())
            if tag is not None:
                patterns = [p for p in patterns if tag in p.tags]
            return patterns

    def remove_goal_pattern(self, pattern_id: str) -> bool:
        """Remove a goal pattern from the library.

        Returns True if the pattern was found and removed.
        """
        with self._lock:
            if pattern_id not in self._goal_patterns:
                return False
            del self._goal_patterns[pattern_id]
            self._stats["total_goal_patterns"] = len(self._goal_patterns)

            self._emit_event(
                RecognitionEventKind.GOAL_LIBRARY_UPDATED,
                goal_pattern_id=pattern_id,
                payload={"action": "remove"},
            )
            return True

    # ------------------------------------------------------------------
    # Observation management
    # ------------------------------------------------------------------

    def record_observation(
        self,
        observed_entity_id: str,
        action_type: str,
        parameters: Optional[Dict[str, Any]] = None,
        source: ObservationSource = ObservationSource.DIRECT,
        confidence: float = 1.0,
    ) -> ObservedAction:
        """Record an observed action and update hypotheses.

        This is the primary entry point for feeding observations into the
        engine. The action is appended to the entity's observation stream,
        existing hypotheses are updated, and new hypotheses are generated
        when the action matches the start of a goal pattern.

        Args:
            observed_entity_id: The entity that performed the action.
            action_type: The type of action performed.
            parameters: The parameters of the action.
            source: How the observation was obtained.
            confidence: Reliability of this observation in [0.0, 1.0].

        Returns:
            The created ObservedAction.
        """
        with self._lock:
            action = ObservedAction(
                observed_entity_id=observed_entity_id,
                action_type=action_type,
                parameters=dict(parameters or {}),
                source=source,
                confidence=max(0.0, min(1.0, confidence)),
            )

            stream = self._get_or_create_stream(observed_entity_id)
            stream.actions.append(action)
            stream.last_updated = _now()

            self._stats["total_observations"] += 1
            self._stats["last_observation_at"] = _timestamp_iso(action.timestamp)

            self._emit_event(
                RecognitionEventKind.OBSERVATION_RECORDED,
                observed_entity_id=observed_entity_id,
                payload={
                    "action_id": action.id,
                    "action_type": action_type,
                    "parameters": dict(action.parameters),
                },
            )

            # Update existing hypotheses with the new observation
            self.update_hypotheses(observed_entity_id, action)

            # Generate new hypotheses for patterns not yet tracked
            self.generate_hypotheses(observed_entity_id)

            # Detect anomalies for the latest observation
            anomalies = self.detect_anomalies(observed_entity_id)
            if anomalies and anomalies[-1].id == action.id:
                self._stats["total_anomalies_detected"] += 1
                self._emit_event(
                    RecognitionEventKind.ANOMALY_DETECTED,
                    observed_entity_id=observed_entity_id,
                    payload={
                        "action_id": action.id,
                        "action_type": action_type,
                    },
                )

            return action

    def get_observation_stream(
        self, observed_entity_id: str
    ) -> Optional[ObservationStream]:
        """Return the observation stream for an entity, or None."""
        with self._lock:
            return self._observation_streams.get(observed_entity_id)

    def list_observations(
        self, observed_entity_id: str, limit: int = 50
    ) -> List[ObservedAction]:
        """Return the most recent observations for an entity.

        Args:
            observed_entity_id: The entity whose observations to list.
            limit: Maximum number of observations to return.

        Returns:
            A list of observations ordered most-recent-last.
        """
        with self._lock:
            stream = self._observation_streams.get(observed_entity_id)
            if stream is None:
                return []
            return list(stream.actions[-limit:])

    def clear_observations(self, observed_entity_id: str) -> bool:
        """Remove all observations and hypotheses for an entity.

        Returns True if the entity had a stream that was cleared.
        """
        with self._lock:
            stream = self._observation_streams.get(observed_entity_id)
            if stream is None:
                return False

            # Remove hypotheses from the global index
            for hyp in stream.hypotheses:
                self._hypotheses.pop(hyp.id, None)

            stream.actions.clear()
            stream.hypotheses.clear()
            stream.last_updated = _now()

            # Recompute aggregate totals
            self._stats["total_observations"] = sum(
                len(s.actions) for s in self._observation_streams.values()
            )
            return True

    # ------------------------------------------------------------------
    # Hypothesis management
    # ------------------------------------------------------------------

    def get_hypotheses(
        self,
        observed_entity_id: str,
        status: Optional[HypothesisStatus] = None,
    ) -> List[GoalHypothesis]:
        """Return hypotheses for an entity, optionally filtered by status.

        Results are sorted by confidence in descending order.
        """
        with self._lock:
            stream = self._observation_streams.get(observed_entity_id)
            if stream is None:
                return []
            hypotheses = list(stream.hypotheses)
            if status is not None:
                hypotheses = [h for h in hypotheses if h.status == status]
            hypotheses.sort(key=lambda h: h.confidence, reverse=True)
            return hypotheses

    def get_top_hypothesis(
        self, observed_entity_id: str
    ) -> Optional[GoalHypothesis]:
        """Return the highest-confidence non-rejected hypothesis.

        Considers ACTIVE and CONFIRMED hypotheses. Returns None if no
        suitable hypothesis exists.
        """
        with self._lock:
            stream = self._observation_streams.get(observed_entity_id)
            if stream is None:
                return None
            candidates = [
                h
                for h in stream.hypotheses
                if h.status in (HypothesisStatus.ACTIVE, HypothesisStatus.CONFIRMED)
            ]
            if not candidates:
                return None
            candidates.sort(key=lambda h: h.confidence, reverse=True)
            return candidates[0]

    def confirm_hypothesis(self, hypothesis_id: str) -> GoalHypothesis:
        """Mark a hypothesis as CONFIRMED.

        Raises KeyError if the hypothesis does not exist.
        """
        with self._lock:
            hyp = self._hypotheses.get(hypothesis_id)
            if hyp is None:
                raise KeyError(f"Hypothesis not found: {hypothesis_id}")
            hyp.status = HypothesisStatus.CONFIRMED
            hyp.updated_at = _now()
            self._stats["total_hypotheses_confirmed"] += 1

            self._emit_event(
                RecognitionEventKind.HYPOTHESIS_CONFIRMED,
                observed_entity_id=hyp.observed_entity_id,
                hypothesis_id=hyp.id,
                goal_pattern_id=hyp.goal_pattern_id,
                payload={"confidence": hyp.confidence},
            )
            return hyp

    def reject_hypothesis(self, hypothesis_id: str) -> GoalHypothesis:
        """Mark a hypothesis as REJECTED.

        Raises KeyError if the hypothesis does not exist.
        """
        with self._lock:
            hyp = self._hypotheses.get(hypothesis_id)
            if hyp is None:
                raise KeyError(f"Hypothesis not found: {hypothesis_id}")
            hyp.status = HypothesisStatus.REJECTED
            hyp.updated_at = _now()
            self._stats["total_hypotheses_rejected"] += 1

            self._emit_event(
                RecognitionEventKind.HYPOTHESIS_REJECTED,
                observed_entity_id=hyp.observed_entity_id,
                hypothesis_id=hyp.id,
                goal_pattern_id=hyp.goal_pattern_id,
                payload={"confidence": hyp.confidence},
            )
            return hyp

    def clear_hypotheses(self, observed_entity_id: str) -> bool:
        """Remove all hypotheses for an entity.

        Returns True if the entity had hypotheses that were removed.
        """
        with self._lock:
            stream = self._observation_streams.get(observed_entity_id)
            if stream is None or not stream.hypotheses:
                return False
            for hyp in stream.hypotheses:
                self._hypotheses.pop(hyp.id, None)
            stream.hypotheses.clear()
            stream.last_updated = _now()
            return True

    # ------------------------------------------------------------------
    # Recognition logic
    # ------------------------------------------------------------------

    def generate_hypotheses(
        self, observed_entity_id: str
    ) -> List[GoalHypothesis]:
        """Generate new hypotheses based on all observed actions.

        For each goal pattern that does not already have an active or
        confirmed hypothesis for this entity, the observation stream is
        matched against the pattern's sequences. If at least one step
        matches, a new hypothesis is created.

        Returns the list of newly created hypotheses.
        """
        with self._lock:
            stream = self._observation_streams.get(observed_entity_id)
            if stream is None or not stream.actions:
                return []

            observations = list(stream.actions)

            # Track which goal patterns already have active/confirmed hypotheses
            existing_patterns = {
                h.goal_pattern_id
                for h in stream.hypotheses
                if h.status in (HypothesisStatus.ACTIVE, HypothesisStatus.CONFIRMED)
            }

            created: List[GoalHypothesis] = []

            for pattern in self._goal_patterns.values():
                if pattern.id in existing_patterns:
                    continue

                # Try the primary sequence and all alternatives
                best_matched: List[int] = []
                best_unmatched: List[int] = []
                best_step_idx = 0
                best_evidence: List[str] = []

                for sequence in pattern.all_sequences():
                    if not sequence:
                        continue
                    matched, unmatched, step_idx, evidence = self._match_sequence(
                        observations, sequence
                    )
                    if len(matched) > len(best_matched):
                        best_matched = matched
                        best_unmatched = unmatched
                        best_step_idx = step_idx
                        best_evidence = evidence

                if not best_matched:
                    continue

                hypothesis = GoalHypothesis(
                    observed_entity_id=observed_entity_id,
                    goal_pattern_id=pattern.id,
                    confidence=0.0,
                    matched_steps=list(best_matched),
                    unmatched_steps=list(best_unmatched),
                    current_step_index=best_step_idx,
                    status=HypothesisStatus.ACTIVE,
                    evidence=list(best_evidence),
                )

                hypothesis.confidence = self.compute_confidence(
                    hypothesis, observations
                )

                # Apply lifecycle rules based on initial confidence
                if (
                    hypothesis.confidence >= 1.0
                    and len(hypothesis.matched_steps) >= pattern.total_steps
                ):
                    hypothesis.status = HypothesisStatus.CONFIRMED
                    self._stats["total_hypotheses_confirmed"] += 1
                elif hypothesis.confidence < 0.1:
                    hypothesis.status = HypothesisStatus.REJECTED
                    self._stats["total_hypotheses_rejected"] += 1

                stream.hypotheses.append(hypothesis)
                self._hypotheses[hypothesis.id] = hypothesis
                self._stats["total_hypotheses_created"] += 1
                created.append(hypothesis)

                self._emit_event(
                    RecognitionEventKind.HYPOTHESIS_CREATED,
                    observed_entity_id=observed_entity_id,
                    hypothesis_id=hypothesis.id,
                    goal_pattern_id=pattern.id,
                    payload={
                        "confidence": hypothesis.confidence,
                        "matched_steps": list(hypothesis.matched_steps),
                        "status": hypothesis.status.value,
                    },
                )

            stream.last_updated = _now()
            return created

    def update_hypotheses(
        self,
        observed_entity_id: str,
        new_observation: ObservedAction,
    ) -> List[GoalHypothesis]:
        """Update existing hypotheses based on a new observation.

        For each active hypothesis, the new observation is checked against
        the next expected step. If it matches, the step is recorded and the
        hypothesis advances. Confidence is then recomputed and lifecycle
        transitions (confirmation or rejection) are applied.

        Returns the list of hypotheses that were updated.
        """
        with self._lock:
            stream = self._observation_streams.get(observed_entity_id)
            if stream is None:
                return []

            observations = list(stream.actions)
            updated: List[GoalHypothesis] = []

            for hyp in stream.hypotheses:
                if hyp.status not in (
                    HypothesisStatus.ACTIVE,
                    HypothesisStatus.CONFIRMED,
                ):
                    continue

                pattern = self._goal_patterns.get(hyp.goal_pattern_id)
                if pattern is None:
                    continue

                sequence = pattern.action_sequence
                advanced = False

                # Check if the new observation matches the next expected step
                if hyp.current_step_index < len(sequence):
                    step = sequence[hyp.current_step_index]
                    if new_observation.action_type == step.action_type:
                        match = self._match_parameters(
                            new_observation.parameters, step.parameters
                        )
                        if match != ActionMatchType.NONE:
                            hyp.matched_steps.append(hyp.current_step_index)
                            hyp.evidence.append(new_observation.id)
                            hyp.current_step_index += 1
                            advanced = True

                # If not advanced, try matching against future steps
                if not advanced:
                    for future_idx in range(
                        hyp.current_step_index + 1, len(sequence)
                    ):
                        if future_idx in hyp.matched_steps:
                            continue
                        step = sequence[future_idx]
                        if new_observation.action_type == step.action_type:
                            match = self._match_parameters(
                                new_observation.parameters, step.parameters
                            )
                            if match != ActionMatchType.NONE:
                                hyp.matched_steps.append(future_idx)
                                hyp.evidence.append(new_observation.id)
                                advanced = True
                                break

                # Recompute unmatched steps
                hyp.unmatched_steps = [
                    i for i in range(len(sequence)) if i not in hyp.matched_steps
                ]

                # Recompute confidence
                hyp.confidence = self.compute_confidence(hyp, observations)
                hyp.updated_at = _now()

                # Apply lifecycle rules
                if (
                    hyp.confidence >= 1.0
                    and len(hyp.matched_steps) >= len(sequence)
                    and hyp.status != HypothesisStatus.CONFIRMED
                ):
                    hyp.status = HypothesisStatus.CONFIRMED
                    self._stats["total_hypotheses_confirmed"] += 1
                    self._emit_event(
                        RecognitionEventKind.HYPOTHESIS_CONFIRMED,
                        observed_entity_id=observed_entity_id,
                        hypothesis_id=hyp.id,
                        goal_pattern_id=hyp.goal_pattern_id,
                        payload={"confidence": hyp.confidence},
                    )
                elif hyp.confidence < 0.1 and hyp.status != HypothesisStatus.REJECTED:
                    hyp.status = HypothesisStatus.REJECTED
                    self._stats["total_hypotheses_rejected"] += 1
                    self._emit_event(
                        RecognitionEventKind.HYPOTHESIS_REJECTED,
                        observed_entity_id=observed_entity_id,
                        hypothesis_id=hyp.id,
                        goal_pattern_id=hyp.goal_pattern_id,
                        payload={"confidence": hyp.confidence},
                    )

                updated.append(hyp)

                self._emit_event(
                    RecognitionEventKind.HYPOTHESIS_UPDATED,
                    observed_entity_id=observed_entity_id,
                    hypothesis_id=hyp.id,
                    goal_pattern_id=hyp.goal_pattern_id,
                    payload={
                        "confidence": hyp.confidence,
                        "matched_steps": list(hyp.matched_steps),
                        "current_step_index": hyp.current_step_index,
                        "status": hyp.status.value,
                        "advanced": advanced,
                    },
                )

            stream.last_updated = _now()
            return updated

    def match_action_to_step(
        self, action: ObservedAction, step: ActionStep
    ) -> ActionMatchType:
        """Determine how well an observed action matches a planned step.

        Returns EXACT when the action type and all parameters match,
        PARTIAL when the action type matches but parameters are incomplete,
        or NONE when the action type does not match.
        """
        with self._lock:
            if action.action_type != step.action_type:
                return ActionMatchType.NONE
            return self._match_parameters(action.parameters, step.parameters)

    def compute_confidence(
        self, hypothesis: GoalHypothesis, observations: List[ObservedAction]
    ) -> float:
        """Compute confidence for a hypothesis given observations.

        The confidence is calculated as:
          base = matched_steps / total_steps
          bonus = +0.1 per step matched in sequential order
          penalty = -0.05 per observation that did not match any step

        The result is clamped to [0.0, 1.0].
        """
        with self._lock:
            pattern = self._goal_patterns.get(hypothesis.goal_pattern_id)
            if pattern is None or pattern.total_steps == 0:
                return 0.0

            total_steps = pattern.total_steps
            matched_count = len(hypothesis.matched_steps)

            # Base confidence from matched steps
            base = matched_count / total_steps

            # Bonus for ordered matching: count sequential matches from 0
            ordered = 0
            for i in range(total_steps):
                if i in hypothesis.matched_steps:
                    ordered += 1
                else:
                    break
            bonus = 0.1 * ordered

            # Penalty for observations that did not match any step
            evidence_set = set(hypothesis.evidence)
            unmatched_obs = len(observations) - len(evidence_set)
            penalty = 0.05 * max(0, unmatched_obs)

            confidence = base + bonus - penalty
            return max(0.0, min(1.0, confidence))

    def detect_anomalies(
        self, observed_entity_id: str
    ) -> List[ObservedAction]:
        """Find observations that do not fit any known goal pattern.

        An observation is anomalous when its action type does not match any
        step of any goal pattern in the library.
        """
        with self._lock:
            stream = self._observation_streams.get(observed_entity_id)
            if stream is None:
                return []

            # Collect all action types known across all patterns
            known_action_types: set = set()
            for pattern in self._goal_patterns.values():
                for sequence in pattern.all_sequences():
                    for step in sequence:
                        known_action_types.add(step.action_type)

            anomalies: List[ObservedAction] = []
            for obs in stream.actions:
                if obs.action_type not in known_action_types:
                    anomalies.append(obs)
            return anomalies

    # ------------------------------------------------------------------
    # Event handling
    # ------------------------------------------------------------------

    def register_event_handler(
        self,
        kind: RecognitionEventKind,
        handler: Callable[[RecognitionEvent], None],
    ) -> str:
        """Register a handler for a specific event kind.

        Args:
            kind: The event kind to listen for.
            handler: A callable that receives a RecognitionEvent.

        Returns:
            A handler id that can be used for future de-registration.
        """
        with self._lock:
            handler_id = uuid.uuid4().hex
            key = kind.value
            if key not in self._event_handlers:
                self._event_handlers[key] = []
            self._event_handlers[key].append((handler_id, handler))
            return handler_id

    def list_events(
        self,
        observed_entity_id: Optional[str] = None,
        limit: int = 100,
    ) -> List[RecognitionEvent]:
        """Return recent events, optionally filtered by entity.

        Args:
            observed_entity_id: If provided, only events for this entity.
            limit: Maximum number of events to return.

        Returns:
            A list of events ordered most-recent-last.
        """
        with self._lock:
            events = list(self._events)
            if observed_entity_id is not None:
                events = [
                    e
                    for e in events
                    if e.observed_entity_id == observed_entity_id
                ]
            return events[-limit:]

    # ------------------------------------------------------------------
    # Status and snapshot
    # ------------------------------------------------------------------

    def get_status(self) -> Dict[str, Any]:
        """Return a dictionary with current engine statistics."""
        with self._lock:
            total_obs = sum(
                len(s.actions) for s in self._observation_streams.values()
            )
            total_hyp = sum(
                len(s.hypotheses) for s in self._observation_streams.values()
            )
            return {
                "total_goal_patterns": len(self._goal_patterns),
                "total_observation_streams": len(self._observation_streams),
                "total_observations": total_obs,
                "total_hypotheses": total_hyp,
                "total_hypotheses_created": self._stats["total_hypotheses_created"],
                "total_hypotheses_confirmed": self._stats["total_hypotheses_confirmed"],
                "total_hypotheses_rejected": self._stats["total_hypotheses_rejected"],
                "total_anomalies_detected": self._stats["total_anomalies_detected"],
                "last_observation_at": self._stats["last_observation_at"],
            }

    def get_snapshot(self) -> PlanRecognitionSnapshot:
        """Return a point-in-time snapshot of the engine state."""
        with self._lock:
            total_obs = sum(
                len(s.actions) for s in self._observation_streams.values()
            )
            total_hyp = sum(
                len(s.hypotheses) for s in self._observation_streams.values()
            )
            return PlanRecognitionSnapshot(
                goal_count=len(self._goal_patterns),
                observation_stream_count=len(self._observation_streams),
                total_observations=total_obs,
                total_hypotheses=total_hyp,
                stats=self.get_status(),
                timestamp=_now(),
            )

    def reset(self) -> None:
        """Clear all state except the default goal patterns.

        Removes all observation streams, hypotheses, events, and resets
        statistics. The default goal library is re-seeded.
        """
        with self._lock:
            self._observation_streams.clear()
            self._hypotheses.clear()
            self._events.clear()
            self._event_handlers.clear()
            self._goal_patterns.clear()
            self._stats = {
                "total_goal_patterns": 0,
                "total_observation_streams": 0,
                "total_observations": 0,
                "total_hypotheses_created": 0,
                "total_hypotheses_confirmed": 0,
                "total_hypotheses_rejected": 0,
                "total_anomalies_detected": 0,
                "last_observation_at": None,
            }
            self._seed_default_goals()


def get_plan_recognition_engine() -> PlanRecognitionEngine:
    """Return the singleton PlanRecognitionEngine instance."""
    return PlanRecognitionEngine.get_instance()
