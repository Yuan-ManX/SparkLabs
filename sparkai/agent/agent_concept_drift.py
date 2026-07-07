"""
SparkLabs Agent - Concept Drift Engine

This module implements a Concept Drift Engine for AI agents operating inside
the SparkLabs AI-native game engine. It tracks how each agent's concepts
(meanings, categories, and vocabulary) evolve over time as the agent
experiences new events, observes new data, and refines its understanding
of the world.

The Concept Drift Engine complements the Self-Model and Metacognition
subsystems by focusing specifically on the agent's internal vocabulary:
how concepts are first learned, how they are used, how they drift, how
they cluster, how they merge or split, and how they are eventually
retired.

Architecture:
  ConceptDriftEngine (Singleton, double-checked locking, threading.RLock)
    |-- Concept                -- a named concept/word the agent knows
    |-- ConceptOccurrence      -- a single use/observation of a concept
    |-- ConceptVersion         -- a historical version of a concept
    |-- ConceptCluster         -- a cluster of related concepts
    |-- DriftEvent             -- a recorded drift occurrence
    |-- AgentConceptState      -- per-agent aggregation of the above
    |-- ConceptDriftStats      -- aggregate engine statistics
    |-- ConceptDriftSnapshot   -- complete engine state snapshot
    |-- ConceptDriftEvent      -- observable engine lifecycle event

All public mutating methods are protected by a re-entrant lock so the
engine is safe to call from multiple agent threads. Bounded in-memory
stores use FIFO eviction when their capacity constants are exceeded.
"""

from __future__ import annotations

import datetime
import math
import threading
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Sequence, Tuple, Union


# ---------------------------------------------------------------------------
# Capacity constants - bounded in-memory stores with FIFO eviction
# ---------------------------------------------------------------------------

_MAX_AGENTS: int = 500
_MAX_CONCEPTS_PER_AGENT: int = 500
_MAX_OCCURRENCES_PER_CONCEPT: int = 200
_MAX_VERSIONS_PER_CONCEPT: int = 50
_MAX_CLUSTERS_PER_AGENT: int = 100
_MAX_DRIFT_EVENTS_PER_AGENT: int = 500
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
    return float(value)


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


def _to_jsonable(value: Any) -> Any:
    """Recursively convert a value to a JSON-friendly form.

    Enums become their string value, dataclasses become dicts (via this
    same function), lists and dicts are walked recursively, and anything
    else is returned as-is.
    """
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, dict):
        return {str(k): _to_jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_to_jsonable(v) for v in value]
    if hasattr(value, "__dataclass_fields__") and not isinstance(value, type):
        return _dataclass_to_dict(value)
    return value


def _dataclass_to_dict(instance: Any) -> Dict[str, Any]:
    """Convert a dataclass instance to a JSON-friendly dictionary.

    Enums are unwrapped to their string values, nested dataclasses and
    collections are walked recursively. ``float`` items in prototype
    vectors are coerced via ``float(...)`` for safety.
    """
    from dataclasses import fields, is_dataclass
    result: Dict[str, Any] = {}
    for field in fields(instance):
        value = getattr(instance, field.name)
        if field.name == "prototype" and isinstance(value, list):
            result[field.name] = [float(v) for v in value]
        elif is_dataclass(value) and not isinstance(value, type):
            result[field.name] = _dataclass_to_dict(value)
        else:
            result[field.name] = _to_jsonable(value)
    return result


def _prototype_distance(a: Sequence[float], b: Sequence[float]) -> float:
    """Euclidean distance between two prototype vectors.

    Vectors of different lengths are compared over their shared prefix
    (the trailing elements of the longer vector are ignored). A non-finite
    component is treated as zero so that the distance always remains finite.
    """
    if not a or not b:
        return 1.0
    n = min(len(a), len(b))
    if n == 0:
        return 1.0
    total = 0.0
    for i in range(n):
        diff = float(a[i]) - float(b[i])
        if not math.isfinite(diff):
            diff = 0.0
        total += diff * diff
    return math.sqrt(total)


def _prototype_centroid(prototypes: Sequence[Sequence[float]]) -> List[float]:
    """Compute the element-wise mean of a sequence of prototype vectors.

    The result has the length of the longest input vector. Components that
    are missing in every contributing vector are returned as 0.0.
    """
    if not prototypes:
        return []
    n = max((len(p) for p in prototypes), default=0)
    if n == 0:
        return []
    sums = [0.0] * n
    counts = [0] * n
    for proto in prototypes:
        for i, value in enumerate(proto):
            sums[i] += float(value)
            counts[i] += 1
    return [
        (sums[i] / counts[i]) if counts[i] > 0 else 0.0 for i in range(n)
    ]


def _prototype_magnitude(prototype: Sequence[float]) -> float:
    """Return the L2 magnitude of a prototype vector."""
    total = 0.0
    for value in prototype:
        total += float(value) * float(value)
    return math.sqrt(total)


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class ConceptType(Enum):
    """The semantic category of a concept in the agent's vocabulary."""
    ACTION = "action"
    OBJECT = "object"
    PROPERTY = "property"
    RELATION = "relation"
    EVENT = "event"
    EMOTION = "emotion"
    ABSTRACT = "abstract"


class DriftType(Enum):
    """The temporal pattern of how a concept's meaning changes over time."""
    GRADUAL = "gradual"
    SUDDEN = "sudden"
    INCREMENTAL = "incremental"
    RECURRING = "recurring"


class DriftDirection(Enum):
    """The semantic direction of a concept's drift in embedding space."""
    EXPANDING = "expanding"
    CONTRACTING = "contracting"
    SHIFTING = "shifting"
    STABLE = "stable"


class DetectionMethod(Enum):
    """The method used to detect that a concept has drifted."""
    DISTRIBUTION = "distribution"
    SEMANTIC = "semantic"
    USAGE = "usage"
    CONTEXTUAL = "contextual"


class ConceptDriftEventKind(Enum):
    """Observable lifecycle events emitted by the concept drift engine."""
    CONCEPT_REGISTERED = "concept_registered"
    CONCEPT_OCCURRED = "concept_occurred"
    CONCEPT_DRIFTED = "concept_drifted"
    CONCEPT_CLUSTERED = "concept_clustered"
    CONCEPT_MERGED = "concept_merged"
    CONCEPT_SPLIT = "concept_split"
    CONCEPT_DEPRECATED = "concept_deprecated"


# ---------------------------------------------------------------------------
# Data Classes
# ---------------------------------------------------------------------------


@dataclass
class Concept:
    """A named concept or word known by an agent, with a prototype vector."""
    concept_id: str
    agent_id: str
    name: str
    concept_type: ConceptType
    prototype: List[float]
    description: str
    occurrence_count: int
    version: int
    deprecated: bool
    drift_score: float
    last_drift: Optional[str]
    created_at: str
    updated_at: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    tags: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this concept to a JSON-friendly dictionary."""
        return _dataclass_to_dict(self)


@dataclass
class ConceptOccurrence:
    """A single observation or use of a concept by an agent."""
    occurrence_id: str
    agent_id: str
    concept_id: str
    context: str
    weight: float
    source: str
    sentiment: float
    timestamp: str
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this occurrence to a JSON-friendly dictionary."""
        return _dataclass_to_dict(self)


@dataclass
class ConceptVersion:
    """A historical version of a concept, captured during drift events."""
    version_id: str
    agent_id: str
    concept_id: str
    version_number: int
    prototype: List[float]
    description: str
    change_reason: str
    change_magnitude: float
    created_at: str
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this concept version to a JSON-friendly dictionary."""
        return _dataclass_to_dict(self)


@dataclass
class ConceptCluster:
    """A cluster of related concepts grouped by prototype similarity."""
    cluster_id: str
    agent_id: str
    name: str
    concept_ids: List[str]
    centroid: List[float]
    similarity: float
    size: int
    created_at: str
    updated_at: str
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this cluster to a JSON-friendly dictionary."""
        return _dataclass_to_dict(self)


@dataclass
class DriftEvent:
    """A recorded occurrence of concept drift with type and magnitude.

    Drift events describe how a concept changed between two versions, the
    method that detected the change, and a human-readable description.
    """
    event_id: str
    agent_id: str
    concept_id: str
    drift_type: DriftType
    direction: DriftDirection
    magnitude: float
    method: DetectionMethod
    old_version: int
    new_version: int
    description: str
    timestamp: str
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this drift event to a JSON-friendly dictionary."""
        return _dataclass_to_dict(self)


@dataclass
class AgentConceptState:
    """Per-agent aggregation of concepts, occurrences, clusters, and drift.

    Holds the full vocabulary state for a single agent. Snapshots and
    reports can be built by iterating over each agent's state.
    """
    agent_id: str
    concepts: Dict[str, Concept]
    occurrences: Dict[str, List[ConceptOccurrence]]
    versions: Dict[str, List[ConceptVersion]]
    clusters: List[ConceptCluster]
    drift_events: List[DriftEvent]
    created_at: str
    updated_at: str

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this agent concept state to a JSON-friendly dictionary."""
        return {
            "agent_id": self.agent_id,
            "concepts": {k: v.to_dict() for k, v in self.concepts.items()},
            "occurrences": {c: [o.to_dict() for o in v] for c, v in self.occurrences.items()},
            "versions": {c: [x.to_dict() for x in v] for c, v in self.versions.items()},
            "clusters": [c.to_dict() for c in self.clusters],
            "drift_events": [d.to_dict() for d in self.drift_events],
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


@dataclass
class ConceptDriftStats:
    """Aggregate statistics about the concept drift engine."""
    total_agents: int
    total_concepts: int
    total_occurrences: int
    total_versions: int
    total_drift_events: int
    total_clusters: int
    deprecated_concepts: int
    avg_drift_magnitude: float
    avg_concepts_per_agent: float

    def to_dict(self) -> Dict[str, Any]:
        """Serialize these statistics to a JSON-friendly dictionary."""
        return _dataclass_to_dict(self)


@dataclass
class ConceptDriftSnapshot:
    """A complete snapshot of the concept drift engine state."""
    initialized: bool
    agents: List[AgentConceptState]
    events: List[ConceptDriftEvent]
    stats: ConceptDriftStats

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this snapshot to a JSON-friendly dictionary."""
        return {
            "initialized": self.initialized,
            "agents": [a.to_dict() for a in self.agents],
            "events": [e.to_dict() for e in self.events],
            "stats": self.stats.to_dict(),
        }


@dataclass
class ConceptDriftEvent:
    """An observable lifecycle event emitted by the concept drift engine."""
    event_id: str
    kind: ConceptDriftEventKind
    timestamp: str
    payload: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this event to a JSON-friendly dictionary."""
        return _dataclass_to_dict(self)


# ---------------------------------------------------------------------------
# Concept Drift Engine (Singleton with double-checked locking)
# ---------------------------------------------------------------------------


class ConceptDriftEngine:
    """Concept drift engine for AI game agents.

    The engine maintains a per-agent vocabulary of concepts and tracks
    how each concept evolves as the agent gains experience. Concepts are
    organized into clusters, exposed to drift detection on demand, and
    merged, split, or deprecated as the agent's understanding refines.

    It is a thread-safe singleton accessed via :meth:`get_instance` or
    the module-level :func:`get_concept_drift` helper.
    """

    _instance: Optional["ConceptDriftEngine"] = None
    _lock: threading.RLock = threading.RLock()

    # -- Construction (double-checked locking) ---------------------------

    def __new__(cls) -> "ConceptDriftEngine":
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

            # Per-agent concept state keyed by agent_id.
            self._agents: Dict[str, AgentConceptState] = {}

            # Observable lifecycle events.
            self._events: List[ConceptDriftEvent] = []

            # Aggregate counters for diagnostics.
            self._agent_counter: int = 0
            self._concept_counter: int = 0
            self._occurrence_counter: int = 0
            self._version_counter: int = 0
            self._cluster_counter: int = 0
            self._drift_event_counter: int = 0

            self._initialized: bool = True

            # Seed baseline concept drift data.
            self._seed_data()

    @classmethod
    def get_instance(cls) -> "ConceptDriftEngine":
        """Return the singleton ConceptDriftEngine instance."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    # ------------------------------------------------------------------
    # Agent state helpers
    # ------------------------------------------------------------------

    def _ensure_agent(self, agent_id: str) -> AgentConceptState:
        """Return the concept state for an agent, creating one if missing.

        Assumes the caller already holds ``self._lock``.
        """
        agent = self._agents.get(agent_id)
        if agent is not None:
            return agent
        now = _now()
        agent = AgentConceptState(
            agent_id=agent_id,
            concepts={},
            occurrences={},
            versions={},
            clusters=[],
            drift_events=[],
            created_at=now,
            updated_at=now,
        )
        self._agents[agent_id] = agent
        self._agent_counter += 1
        _evict_fifo_dict(self._agents, _MAX_AGENTS)
        return agent

    def _touch_agent(self, agent: AgentConceptState) -> None:
        """Refresh the agent state's updated_at timestamp.

        Assumes the caller already holds ``self._lock``.
        """
        agent.updated_at = _now()

    def get_agent_state(self, agent_id: str) -> Optional[AgentConceptState]:
        """Return the concept state for an agent, or None if not present."""
        with self._lock:
            return self._agents.get(agent_id)

    def list_agents(self) -> List[AgentConceptState]:
        """Return all agent concept states currently tracked."""
        with self._lock:
            return list(self._agents.values())

    def delete_agent(self, agent_id: str) -> bool:
        """Remove the concept state for an agent. Returns True if removed."""
        with self._lock:
            removed = self._agents.pop(agent_id, None)
            return removed is not None

    # ------------------------------------------------------------------
    # Concept registration and lookup
    # ------------------------------------------------------------------

    def register_concept(
        self,
        agent_id: str,
        name: str,
        concept_type: Union[ConceptType, str],
        prototype: Optional[Sequence[float]] = None,
        description: str = "",
        tags: Optional[Sequence[str]] = None,
    ) -> Optional[Concept]:
        """Register a new concept for an agent.

        ``agent_id`` is the agent identifier, ``name`` is the human-readable
        concept name, ``concept_type`` is a :class:`ConceptType` (or its
        string value), ``prototype`` is the initial embedding vector, and
        ``tags`` is an optional list of free-form labels. Returns the
        newly created :class:`Concept`, or ``None`` if ``agent_id`` is empty.
        """
        with self._lock:
            if not agent_id:
                return None
            resolved_type: ConceptType
            if isinstance(concept_type, ConceptType):
                resolved_type = concept_type
            elif isinstance(concept_type, str):
                try:
                    resolved_type = ConceptType(concept_type)
                except ValueError:
                    resolved_type = ConceptType.ABSTRACT
            else:
                resolved_type = ConceptType.ABSTRACT
            agent = self._ensure_agent(agent_id)
            now = _now()
            proto = [float(v) for v in (prototype or [])]
            concept = Concept(
                concept_id=_new_id(), agent_id=agent_id, name=name,
                concept_type=resolved_type, prototype=proto,
                description=description or "", occurrence_count=0, version=1,
                deprecated=False, drift_score=0.0, last_drift=None,
                created_at=now, updated_at=now, metadata={},
                tags=list(tags) if tags else [],
            )
            agent.concepts[concept.concept_id] = concept
            agent.occurrences[concept.concept_id] = []
            initial_version = ConceptVersion(
                version_id=_new_id(), agent_id=agent_id,
                concept_id=concept.concept_id, version_number=1,
                prototype=list(concept.prototype),
                description=concept.description,
                change_reason="initial_registration", change_magnitude=0.0,
                created_at=now, metadata={},
            )
            agent.versions[concept.concept_id] = [initial_version]
            _evict_fifo_dict(agent.concepts, _MAX_CONCEPTS_PER_AGENT)
            self._concept_counter += 1
            self._version_counter += 1
            self._touch_agent(agent)
            self._record_event(
                ConceptDriftEventKind.CONCEPT_REGISTERED,
                {
                    "agent_id": agent_id, "concept_id": concept.concept_id,
                    "name": name, "concept_type": resolved_type.value,
                    "prototype_dim": len(concept.prototype),
                },
            )
            return concept

    def get_concept(
        self, agent_id: str, concept_id: str
    ) -> Optional[Concept]:
        """Return a single concept by id, or None if not found."""
        with self._lock:
            agent = self._agents.get(agent_id)
            if agent is None:
                return None
            return agent.concepts.get(concept_id)

    def list_concepts(
        self,
        agent_id: str,
        concept_type: Optional[Union[ConceptType, str]] = None,
        include_deprecated: bool = False,
    ) -> List[Concept]:
        """Return all concepts known for an agent, optionally filtered."""
        with self._lock:
            agent = self._agents.get(agent_id)
            if agent is None:
                return []
            resolved: Optional[ConceptType] = None
            if isinstance(concept_type, ConceptType):
                resolved = concept_type
            elif isinstance(concept_type, str):
                try:
                    resolved = ConceptType(concept_type)
                except ValueError:
                    resolved = None
            results: List[Concept] = []
            for concept in agent.concepts.values():
                if not include_deprecated and concept.deprecated:
                    continue
                if resolved is not None and concept.concept_type != resolved:
                    continue
                results.append(concept)
            return results

    # ------------------------------------------------------------------
    # Occurrence recording
    # ------------------------------------------------------------------

    def record_occurrence(
        self,
        agent_id: str,
        concept_id: str,
        context: str,
        weight: float = 1.0,
        source: str = "observation",
    ) -> Optional[ConceptOccurrence]:
        """Record a single use/observation of a concept by an agent.

        ``weight`` is clamped into [0.0, 10.0] and ``source`` is a free-form
        label such as ``"dialogue"``. Returns the new :class:`ConceptOccurrence`
        or ``None`` if the agent or concept is not registered.
        """
        with self._lock:
            agent = self._agents.get(agent_id)
            if agent is None:
                return None
            concept = agent.concepts.get(concept_id)
            if concept is None:
                return None
            sentiment = _infer_sentiment(context or "")
            occurrence = ConceptOccurrence(
                occurrence_id=_new_id(), agent_id=agent_id,
                concept_id=concept_id, context=context or "",
                weight=_clamp(float(weight), 0.0, 10.0),
                source=source or "observation", sentiment=sentiment,
                timestamp=_now(), metadata={},
            )
            occ_list = agent.occurrences.setdefault(concept_id, [])
            occ_list.append(occurrence)
            if len(occ_list) > _MAX_OCCURRENCES_PER_CONCEPT:
                agent.occurrences[concept_id] = occ_list[-_MAX_OCCURRENCES_PER_CONCEPT:]
            concept.occurrence_count += 1
            concept.updated_at = _now()
            self._occurrence_counter += 1
            self._touch_agent(agent)
            self._record_event(
                ConceptDriftEventKind.CONCEPT_OCCURRED,
                {
                    "agent_id": agent_id, "concept_id": concept_id,
                    "weight": occurrence.weight,
                    "source": occurrence.source,
                    "occurrence_count": concept.occurrence_count,
                },
            )
            return occurrence

    # ------------------------------------------------------------------
    # Drift detection
    # ------------------------------------------------------------------

    def detect_drift(
        self,
        agent_id: str,
        concept_id: str,
        method: Union[DetectionMethod, str] = DetectionMethod.DISTRIBUTION,
    ) -> Optional[DriftEvent]:
        """Detect whether a concept has drifted and record a :class:`DriftEvent`.

        The ``method`` controls how magnitude is estimated from the
        concept's recent occurrences: ``DISTRIBUTION`` (weight variance),
        ``SEMANTIC`` (prototype distance from origin), ``USAGE`` (log-scaled
        occurrence count), or ``CONTEXTUAL`` (mean absolute sentiment).
        Returns the new :class:`DriftEvent` or ``None`` if the agent or
        concept is not found.
        """
        with self._lock:
            agent = self._agents.get(agent_id)
            if agent is None:
                return None
            concept = agent.concepts.get(concept_id)
            if concept is None:
                return None
            resolved_method: DetectionMethod
            if isinstance(method, DetectionMethod):
                resolved_method = method
            elif isinstance(method, str):
                try:
                    resolved_method = DetectionMethod(method)
                except ValueError:
                    resolved_method = DetectionMethod.DISTRIBUTION
            else:
                resolved_method = DetectionMethod.DISTRIBUTION
            occurrences = agent.occurrences.get(concept_id, [])
            magnitude = _estimate_drift_magnitude(
                concept, occurrences, resolved_method
            )
            drift_type, direction = _classify_drift(magnitude)
            old_version = concept.version
            concept.drift_score = magnitude
            concept.last_drift = _now()
            concept.version += 1
            concept.updated_at = _now()
            version = ConceptVersion(
                version_id=_new_id(), agent_id=agent_id,
                concept_id=concept_id, version_number=concept.version,
                prototype=list(concept.prototype),
                description=concept.description,
                change_reason=f"drift_{resolved_method.value}",
                change_magnitude=round(magnitude, 4),
                created_at=_now(),
                metadata={
                    "drift_type": drift_type.value,
                    "direction": direction.value,
                },
            )
            version_list = agent.versions.setdefault(concept_id, [])
            version_list.append(version)
            if len(version_list) > _MAX_VERSIONS_PER_CONCEPT:
                agent.versions[concept_id] = version_list[
                    -_MAX_VERSIONS_PER_CONCEPT:
                ]
            event = DriftEvent(
                event_id=_new_id(),
                agent_id=agent_id,
                concept_id=concept_id,
                drift_type=drift_type,
                direction=direction,
                magnitude=round(magnitude, 4),
                method=resolved_method,
                old_version=old_version,
                new_version=concept.version,
                description=(
                    f"Detected {drift_type.value} drift via "
                    f"{resolved_method.value} with magnitude {magnitude:.4f}"
                ),
                timestamp=_now(),
                metadata={},
            )
            agent.drift_events.append(event)
            if len(agent.drift_events) > _MAX_DRIFT_EVENTS_PER_AGENT:
                agent.drift_events = agent.drift_events[
                    -_MAX_DRIFT_EVENTS_PER_AGENT:
                ]
            self._drift_event_counter += 1
            self._version_counter += 1
            self._touch_agent(agent)
            self._record_event(
                ConceptDriftEventKind.CONCEPT_DRIFTED,
                {
                    "agent_id": agent_id,
                    "concept_id": concept_id,
                    "drift_type": drift_type.value,
                    "direction": direction.value,
                    "magnitude": event.magnitude,
                    "method": resolved_method.value,
                },
            )
            return event

    def list_drift_events(
        self, agent_id: str, limit: int = 0
    ) -> List[DriftEvent]:
        """Return recorded drift events for an agent, newest first.

        When ``limit`` is > 0, return at most that many events; otherwise
        return every recorded event.
        """
        with self._lock:
            agent = self._agents.get(agent_id)
            if agent is None:
                return []
            n = max(0, int(limit))
            ordered = list(reversed(agent.drift_events))
            if n == 0:
                return ordered
            return ordered[:n]

    # ------------------------------------------------------------------
    # Versions
    # ------------------------------------------------------------------

    def get_versions(
        self, agent_id: str, concept_id: str
    ) -> List[ConceptVersion]:
        """Return all historical versions of a concept, oldest first."""
        with self._lock:
            agent = self._agents.get(agent_id)
            if agent is None:
                return []
            return list(agent.versions.get(concept_id, []))

    # ------------------------------------------------------------------
    # Clustering
    # ------------------------------------------------------------------

    def cluster_concepts(
        self, agent_id: str, similarity_threshold: float = 0.7
    ) -> List[ConceptCluster]:
        """Re-cluster an agent's non-deprecated concepts by prototype similarity.

        Single-linkage clustering groups concepts whose pairwise prototype
        distance is below ``1.0 - similarity_threshold``. Higher threshold
        values produce tighter, smaller clusters. Returns the new cluster
        list (also stored on the agent state).
        """
        with self._lock:
            agent = self._agents.get(agent_id)
            if agent is None:
                return []
            threshold = _clamp(float(similarity_threshold), 0.0, 1.0)
            distance_cutoff = 1.0 - threshold
            active = [c for c in agent.concepts.values() if not c.deprecated]
            if not active:
                agent.clusters = []
                self._touch_agent(agent)
                return []
            parent = list(range(len(active)))

            def find(x: int) -> int:
                while parent[x] != x:
                    parent[x] = parent[parent[x]]
                    x = parent[x]
                return x

            def union(x: int, y: int) -> None:
                rx, ry = find(x), find(y)
                if rx != ry:
                    parent[rx] = ry

            for i in range(len(active)):
                for j in range(i + 1, len(active)):
                    if _prototype_distance(active[i].prototype, active[j].prototype) <= distance_cutoff:
                        union(i, j)
            groups: Dict[int, List[int]] = {}
            for i in range(len(active)):
                groups.setdefault(find(i), []).append(i)
            now = _now()
            new_clusters: List[ConceptCluster] = []
            cluster_index = 0
            for grp in groups.values():
                if len(grp) < 2:
                    continue
                cluster_index += 1
                members = [active[i] for i in grp]
                centroid = _prototype_centroid([m.prototype for m in members])
                pair_sims: List[float] = []
                for i in range(len(members)):
                    for j in range(i + 1, len(members)):
                        d = _prototype_distance(members[i].prototype, members[j].prototype)
                        pair_sims.append(_clamp(1.0 - d, 0.0, 1.0))
                avg_sim = (
                    sum(pair_sims) / len(pair_sims) if pair_sims else 0.0
                )
                cluster = ConceptCluster(
                    cluster_id=_new_id(),
                    agent_id=agent_id,
                    name=f"cluster_{cluster_index:02d}",
                    concept_ids=[m.concept_id for m in members],
                    centroid=centroid,
                    similarity=round(avg_sim, 4),
                    size=len(members),
                    created_at=now,
                    updated_at=now,
                    metadata={},
                )
                new_clusters.append(cluster)
            agent.clusters = new_clusters
            _evict_fifo_list(agent.clusters, _MAX_CLUSTERS_PER_AGENT)
            self._cluster_counter += 1
            self._touch_agent(agent)
            self._record_event(
                ConceptDriftEventKind.CONCEPT_CLUSTERED,
                {
                    "agent_id": agent_id,
                    "cluster_count": len(new_clusters),
                    "similarity_threshold": threshold,
                    "distance_cutoff": round(distance_cutoff, 4),
                },
            )
            return list(new_clusters)

    def get_clusters(self, agent_id: str) -> List[ConceptCluster]:
        """Return the current clusters for an agent."""
        with self._lock:
            agent = self._agents.get(agent_id)
            if agent is None:
                return []
            return list(agent.clusters)

    # ------------------------------------------------------------------
    # Merge / split / deprecate
    # ------------------------------------------------------------------

    def merge_concepts(
        self,
        agent_id: str,
        source_id: str,
        target_id: str,
    ) -> Optional[Concept]:
        """Merge a source concept into a target concept.

        The source's occurrences are appended to the target, the target's
        prototype is averaged with the source's prototype, the source is
        marked deprecated, and a new :class:`ConceptVersion` is recorded
        for the target. Returns the updated target, or ``None`` if either
        concept is missing or the two ids are equal.
        """
        with self._lock:
            agent = self._agents.get(agent_id)
            if agent is None or source_id == target_id:
                return None
            source = agent.concepts.get(source_id)
            target = agent.concepts.get(target_id)
            if source is None or target is None:
                return None
            # Transfer occurrences
            target_occs = list(agent.occurrences.get(target_id, []))
            target_occs.extend(agent.occurrences.get(source_id, []))
            agent.occurrences[target_id] = target_occs[-_MAX_OCCURRENCES_PER_CONCEPT:]
            target.occurrence_count += source.occurrence_count
            # Average prototypes
            if source.prototype and target.prototype:
                n = min(len(source.prototype), len(target.prototype))
                target.prototype = [(source.prototype[i] + target.prototype[i]) / 2.0 for i in range(n)]
            elif source.prototype:
                target.prototype = list(source.prototype)
            target.tags = list(dict.fromkeys(list(target.tags) + list(source.tags)))
            target.version += 1
            target.updated_at = _now()
            version = ConceptVersion(
                version_id=_new_id(), agent_id=agent_id,
                concept_id=target_id, version_number=target.version,
                prototype=list(target.prototype),
                description=target.description,
                change_reason=f"merged_from_{source.name}",
                change_magnitude=0.5, created_at=_now(),
                metadata={"source_concept_id": source_id},
            )
            version_list = agent.versions.setdefault(target_id, [])
            version_list.append(version)
            if len(version_list) > _MAX_VERSIONS_PER_CONCEPT:
                agent.versions[target_id] = version_list[-_MAX_VERSIONS_PER_CONCEPT:]
            # Deprecate source
            source.deprecated = True
            source.updated_at = _now()
            source.metadata["merged_into"] = target_id
            # Clean up source occurrence slot
            agent.occurrences.pop(source_id, None)
            self._version_counter += 1
            self._touch_agent(agent)
            self._record_event(
                ConceptDriftEventKind.CONCEPT_MERGED,
                {
                    "agent_id": agent_id,
                    "source_id": source_id,
                    "target_id": target_id,
                    "source_name": source.name,
                    "target_name": target.name,
                },
            )
            return target

    def split_concept(
        self,
        agent_id: str,
        concept_id: str,
        sub_concepts: Sequence[Union[Dict[str, Any], Tuple[str, Sequence[float]]]],
    ) -> List[Concept]:
        """Split a parent concept into several sub-concepts.

        The parent is marked deprecated and its occurrences are
        round-robined across the new sub-concepts. ``sub_concepts`` may
        be a list of ``(name, prototype)`` tuples or dictionaries with
        ``"name"``, ``"prototype"``, and optional ``"concept_type"`` and
        ``"tags"`` keys. Returns the new sub-concepts (empty list if the
        parent is missing or ``sub_concepts`` is empty).
        """
        with self._lock:
            agent = self._agents.get(agent_id)
            if agent is None:
                return []
            parent = agent.concepts.get(concept_id)
            if parent is None or not sub_concepts:
                return []
            now = _now()
            new_concepts: List[Concept] = []
            for entry in sub_concepts:
                if isinstance(entry, dict):
                    name = str(entry.get("name", "sub_concept"))
                    proto = [float(v) for v in (entry.get("prototype", []) or [])]
                    ctype_raw = entry.get("concept_type", parent.concept_type)
                    if isinstance(ctype_raw, ConceptType):
                        ctype = ctype_raw
                    elif isinstance(ctype_raw, str):
                        try:
                            ctype = ConceptType(ctype_raw)
                        except ValueError:
                            ctype = parent.concept_type
                    else:
                        ctype = parent.concept_type
                    sub_tags = list(entry.get("tags", parent.tags) or [])
                elif isinstance(entry, (tuple, list)) and len(entry) >= 2:
                    name = str(entry[0])
                    proto = [float(v) for v in (entry[1] or [])]
                    ctype = parent.concept_type
                    sub_tags = list(parent.tags)
                else:
                    name = f"sub_concept_of_{parent.name}"
                    proto = list(parent.prototype)
                    ctype = parent.concept_type
                    sub_tags = list(parent.tags)
                concept = Concept(
                    concept_id=_new_id(), agent_id=agent_id, name=name,
                    concept_type=ctype, prototype=proto,
                    description=f"Split from {parent.name}",
                    occurrence_count=0, version=1, deprecated=False,
                    drift_score=0.0, last_drift=None,
                    created_at=now, updated_at=now,
                    metadata={"parent_concept_id": concept_id}, tags=sub_tags,
                )
                agent.concepts[concept.concept_id] = concept
                agent.occurrences[concept.concept_id] = []
                version = ConceptVersion(
                    version_id=_new_id(), agent_id=agent_id,
                    concept_id=concept.concept_id, version_number=1,
                    prototype=list(concept.prototype),
                    description=concept.description,
                    change_reason=f"split_from_{parent.name}",
                    change_magnitude=0.0, created_at=now,
                    metadata={"parent_concept_id": concept_id},
                )
                agent.versions[concept.concept_id] = [version]
                new_concepts.append(concept)
            _evict_fifo_dict(agent.concepts, _MAX_CONCEPTS_PER_AGENT)
            # Round-robin redistribute parent occurrences
            parent_occs = list(agent.occurrences.get(concept_id, []))
            for i, occ in enumerate(parent_occs):
                target = new_concepts[i % len(new_concepts)]
                target.occurrence_count += 1
                occ_list = agent.occurrences.setdefault(target.concept_id, [])
                occ_list.append(occ)
                if len(occ_list) > _MAX_OCCURRENCES_PER_CONCEPT:
                    agent.occurrences[target.concept_id] = occ_list[-_MAX_OCCURRENCES_PER_CONCEPT:]
            parent.deprecated = True
            parent.updated_at = now
            parent.metadata["split_into"] = [c.concept_id for c in new_concepts]
            agent.occurrences.pop(concept_id, None)
            self._concept_counter += len(new_concepts)
            self._version_counter += len(new_concepts)
            self._touch_agent(agent)
            self._record_event(
                ConceptDriftEventKind.CONCEPT_SPLIT,
                {
                    "agent_id": agent_id, "parent_id": concept_id,
                    "child_ids": [c.concept_id for c in new_concepts],
                    "child_count": len(new_concepts),
                },
            )
            return new_concepts

    def deprecate_concept(
        self,
        agent_id: str,
        concept_id: str,
        reason: str = "",
    ) -> Optional[Concept]:
        """Mark a concept as deprecated.

        Deprecated concepts remain in the engine (for historical
        queries) but are excluded from clustering and from
        :meth:`list_concepts` by default.

        Args:
            agent_id: Identifier of the agent.
            concept_id: Identifier of the concept to deprecate.
            reason: Free-form reason for the deprecation.

        Returns:
            The deprecated :class:`Concept`, or ``None`` if either the
            agent or the concept is not found.
        """
        with self._lock:
            agent = self._agents.get(agent_id)
            if agent is None:
                return None
            concept = agent.concepts.get(concept_id)
            if concept is None:
                return None
            concept.deprecated = True
            concept.updated_at = _now()
            concept.metadata["deprecated_reason"] = reason or ""
            self._touch_agent(agent)
            self._record_event(
                ConceptDriftEventKind.CONCEPT_DEPRECATED,
                {
                    "agent_id": agent_id,
                    "concept_id": concept_id,
                    "name": concept.name,
                    "reason": reason or "",
                },
            )
            return concept

    # ------------------------------------------------------------------
    # Events, Stats, Status, Snapshot
    # ------------------------------------------------------------------

    def _record_event(
        self,
        kind: ConceptDriftEventKind,
        payload: Dict[str, Any],
    ) -> None:
        """Record an observable concept drift event.

        Assumes the caller already holds ``self._lock``. The event log
        is bounded by ``_MAX_EVENTS`` with FIFO eviction.
        """
        event = ConceptDriftEvent(
            event_id=_new_id(),
            kind=kind,
            timestamp=_now(),
            payload=dict(payload) if payload else {},
        )
        self._events.append(event)
        _evict_fifo_list(self._events, _MAX_EVENTS)

    def list_events(self, limit: int = 100) -> List[ConceptDriftEvent]:
        """Return the most recent concept drift events, newest first."""
        with self._lock:
            n = max(0, int(limit))
            if n == 0:
                return []
            return list(reversed(self._events))[:n]

    def get_stats(self) -> ConceptDriftStats:
        """Return aggregate statistics about the concept drift engine."""
        with self._lock:
            total_concepts = 0
            total_occurrences = 0
            total_versions = 0
            total_drift_events = 0
            total_clusters = 0
            deprecated_count = 0
            drift_score_sum = 0.0
            for agent in self._agents.values():
                total_concepts += len(agent.concepts)
                total_clusters += len(agent.clusters)
                for concept in agent.concepts.values():
                    if concept.deprecated:
                        deprecated_count += 1
                    drift_score_sum += concept.drift_score
                for occs in agent.occurrences.values():
                    total_occurrences += len(occs)
                for versions in agent.versions.values():
                    total_versions += len(versions)
                total_drift_events += len(agent.drift_events)
            avg_magnitude = (
                drift_score_sum / total_concepts if total_concepts else 0.0
            )
            avg_concepts = (
                total_concepts / len(self._agents) if self._agents else 0.0
            )
            return ConceptDriftStats(
                total_agents=len(self._agents),
                total_concepts=total_concepts,
                total_occurrences=total_occurrences,
                total_versions=total_versions,
                total_drift_events=total_drift_events,
                total_clusters=total_clusters,
                deprecated_concepts=deprecated_count,
                avg_drift_magnitude=round(avg_magnitude, 4),
                avg_concepts_per_agent=round(avg_concepts, 4),
            )

    def get_status(self) -> Dict[str, Any]:
        """Return a comprehensive status dictionary for diagnostics.

        The first key is always ``"initialized"`` so callers can verify
        the singleton is alive.
        """
        with self._lock:
            stats = self.get_stats()
            return {
                "initialized": self._initialized,
                "total_agents": len(self._agents),
                "total_concepts": stats.total_concepts,
                "total_occurrences": stats.total_occurrences,
                "total_versions": stats.total_versions,
                "total_drift_events": stats.total_drift_events,
                "total_clusters": stats.total_clusters,
                "deprecated_concepts": stats.deprecated_concepts,
                "total_events": len(self._events),
                "agent_counter": self._agent_counter,
                "concept_counter": self._concept_counter,
                "occurrence_counter": self._occurrence_counter,
                "version_counter": self._version_counter,
                "cluster_counter": self._cluster_counter,
                "drift_event_counter": self._drift_event_counter,
                "avg_drift_magnitude": stats.avg_drift_magnitude,
                "avg_concepts_per_agent": stats.avg_concepts_per_agent,
                "capacities": {
                    "max_agents": _MAX_AGENTS,
                    "max_concepts_per_agent": _MAX_CONCEPTS_PER_AGENT,
                    "max_occurrences_per_concept": _MAX_OCCURRENCES_PER_CONCEPT,
                    "max_versions_per_concept": _MAX_VERSIONS_PER_CONCEPT,
                    "max_clusters_per_agent": _MAX_CLUSTERS_PER_AGENT,
                    "max_drift_events_per_agent": _MAX_DRIFT_EVENTS_PER_AGENT,
                    "max_events": _MAX_EVENTS,
                },
            }

    def get_snapshot(self) -> ConceptDriftSnapshot:
        """Return a complete snapshot of the concept drift engine state."""
        with self._lock:
            return ConceptDriftSnapshot(
                initialized=self._initialized,
                agents=list(self._agents.values()),
                events=list(self._events),
                stats=self.get_stats(),
            )

    # ------------------------------------------------------------------
    # Reset
    # ------------------------------------------------------------------

    def reset(self) -> None:
        """Clear all tracked state and re-seed baseline data.

        Unlike a one-shot clear, ``reset`` re-seeds the baseline concept
        drift data so the engine returns to a freshly initialised state.
        """
        with self._lock:
            self._agents.clear()
            self._events.clear()
            self._agent_counter = 0
            self._concept_counter = 0
            self._occurrence_counter = 0
            self._version_counter = 0
            self._cluster_counter = 0
            self._drift_event_counter = 0
            self._seed_data()

    # ------------------------------------------------------------------
    # Seed data
    # ------------------------------------------------------------------

    def _seed_data(self) -> None:
        """Populate the engine with baseline SparkLabs concept drift data.

        Seeds two agents (``agent_alpha`` -- a warrior,
        ``agent_beta`` -- a mage) with several concepts, occurrences,
        drift events, and clusters to provide a useful out-of-the-box
        demo.
        """
        # --- Agent Alpha: the warrior ---------------------------------
        alpha_specs = [
            ("sword", ConceptType.OBJECT, [0.10, 0.20, 0.30, 0.40], "A bladed melee weapon", ["weapon"]),
            ("slash", ConceptType.ACTION, [0.50, 0.40, 0.30, 0.20], "A sweeping cut", ["attack"]),
            ("parry", ConceptType.ACTION, [0.40, 0.50, 0.20, 0.10], "Deflecting a blow", ["defense"]),
            ("blade", ConceptType.OBJECT, [0.15, 0.25, 0.35, 0.45], "Sharpened edge", ["weapon"]),
            ("fear", ConceptType.EMOTION, [0.90, 0.10, 0.05, 0.05], "Dread in battle", ["feeling"]),
            ("courage", ConceptType.EMOTION, [0.85, 0.15, 0.05, 0.05], "Bravery under fire", ["feeling"]),
            ("victory", ConceptType.ABSTRACT, [0.70, 0.20, 0.10, 0.10], "Triumph over a foe", ["outcome"]),
        ]
        alpha = self._bulk_register("agent_alpha", alpha_specs)
        alpha_occs = [
            ("sword", "I drew my sword in the great hall", 1.0, "dialogue"),
            ("sword", "The sword gleamed in the morning light", 0.7, "observation"),
            ("slash", "He slashed at the dragon's neck", 0.9, "combat"),
            ("slash", "Another slash opened the wound wider", 1.0, "combat"),
            ("parry", "A graceful parry deflected the blow", 0.85, "combat"),
            ("fear", "Fear crept into his heart at the gate", 0.7, "dialogue"),
            ("courage", "Courage surged through him in the battle", 0.9, "dialogue"),
            ("victory", "Victory was finally within his grasp", 0.8, "dialogue"),
        ]
        self._bulk_occur("agent_alpha", alpha, alpha_occs)
        if alpha.get("sword") is not None:
            self.detect_drift("agent_alpha", alpha["sword"].concept_id, DetectionMethod.DISTRIBUTION)
        if alpha.get("fear") is not None:
            self.detect_drift("agent_alpha", alpha["fear"].concept_id, DetectionMethod.CONTEXTUAL)
        self.cluster_concepts("agent_alpha", similarity_threshold=0.7)

        # --- Agent Beta: the mage -------------------------------------
        beta_specs = [
            ("spell", ConceptType.ABSTRACT, [0.60, 0.60, 0.10, 0.10], "A magical incantation", ["magic"]),
            ("fireball", ConceptType.OBJECT, [0.80, 0.00, 0.00, 0.20], "A ball of conjured flame", ["magic"]),
            ("mana", ConceptType.PROPERTY, [0.10, 0.80, 0.10, 0.00], "Magical energy reserve", ["resource"]),
            ("incantation", ConceptType.EVENT, [0.50, 0.50, 0.00, 0.00], "Spoken spell words", ["magic"]),
            ("arcane", ConceptType.PROPERTY, [0.40, 0.70, 0.00, 0.00], "Hidden magical lore", ["magic"]),
            ("wisdom", ConceptType.ABSTRACT, [0.30, 0.60, 0.10, 0.00], "Deep magical understanding", ["trait"]),
            ("curse", ConceptType.ABSTRACT, [0.90, 0.10, 0.00, 0.00], "A malevolent affliction", ["magic"]),
        ]
        beta = self._bulk_register("agent_beta", beta_specs)
        beta_occs = [
            ("spell", "She cast a powerful spell of binding", 0.95, "combat"),
            ("fireball", "The fireball exploded in mid-air", 1.0, "combat"),
            ("mana", "Mana drained quickly from her staff", 0.85, "observation"),
            ("incantation", "An ancient incantation was spoken aloud", 0.9, "dialogue"),
            ("arcane", "Arcane symbols glowed on the page", 0.8, "observation"),
            ("wisdom", "Wisdom guided her every careful step", 0.7, "dialogue"),
            ("curse", "The curse was finally broken at dawn", 0.6, "narrative"),
        ]
        self._bulk_occur("agent_beta", beta, beta_occs)
        if beta.get("spell") is not None:
            self.detect_drift("agent_beta", beta["spell"].concept_id, DetectionMethod.SEMANTIC)
        if beta.get("mana") is not None:
            self.detect_drift("agent_beta", beta["mana"].concept_id, DetectionMethod.USAGE)
        self.cluster_concepts("agent_beta", similarity_threshold=0.6)

    def _bulk_register(
        self,
        agent_id: str,
        specs: Sequence[Tuple[str, ConceptType, Sequence[float], str, Sequence[str]]],
    ) -> Dict[str, Concept]:
        """Register many concepts for an agent in a single call.

        Assumes the caller already holds ``self._lock``. Returns a
        dictionary mapping concept name to :class:`Concept` instance.
        """
        result: Dict[str, Concept] = {}
        for name, ctype, proto, desc, tags in specs:
            concept = self.register_concept(
                agent_id, name, ctype, list(proto), description=desc, tags=list(tags)
            )
            if concept is not None:
                result[name] = concept
        return result

    def _bulk_occur(
        self,
        agent_id: str,
        concepts: Dict[str, Concept],
        entries: Sequence[Tuple[str, str, float, str]],
    ) -> None:
        """Record many occurrences for an agent in a single call.

        Assumes the caller already holds ``self._lock``.
        """
        for name, context, weight, source in entries:
            concept = concepts.get(name)
            if concept is None:
                continue
            self.record_occurrence(agent_id, concept.concept_id, context, weight=weight, source=source)


# ---------------------------------------------------------------------------
# Module-level helpers used by the engine
# ---------------------------------------------------------------------------


_POSITIVE_TOKENS = (
    "good", "great", "happy", "win", "joy", "triumph", "brave", "love",
    "hope", "success", "bright", "victor",
)
_NEGATIVE_TOKENS = (
    "bad", "sad", "loss", "fail", "fear", "dread", "hate", "dark",
    "doom", "weak", "curse", "wound", "broken",
)


def _infer_sentiment(context: str) -> float:
    """Heuristically derive a sentiment score in [-1.0, 1.0] from a context.

    The function counts occurrences of simple positive and negative
    tokens. The result is clamped to [-1.0, 1.0] and is intended only
    as a coarse prior for downstream drift detection.
    """
    if not context:
        return 0.0
    text = context.lower()
    pos = sum(1 for tok in _POSITIVE_TOKENS if tok in text)
    neg = sum(1 for tok in _NEGATIVE_TOKENS if tok in text)
    raw = float(pos - neg)
    if raw > 1.0:
        raw = 1.0
    elif raw < -1.0:
        raw = -1.0
    return raw


def _estimate_drift_magnitude(
    concept: Concept,
    occurrences: List[ConceptOccurrence],
    method: DetectionMethod,
) -> float:
    """Estimate the drift magnitude in [0.0, 1.0] for a concept.

    The estimate depends on the chosen :class:`DetectionMethod`. When
    there is no signal yet (no occurrences or no prototype), the
    function returns a small neutral value so the engine still records
    a drift event with a low magnitude.
    """
    if method == DetectionMethod.DISTRIBUTION:
        if not occurrences:
            return 0.05
        weights = [float(o.weight) for o in occurrences]
        avg = sum(weights) / len(weights)
        var = sum((w - avg) ** 2 for w in weights) / len(weights)
        return _clamp(math.sqrt(var) / 2.0, 0.0, 1.0)
    if method == DetectionMethod.SEMANTIC:
        if not concept.prototype:
            return 0.05
        origin = [0.0] * len(concept.prototype)
        dist = _prototype_distance(concept.prototype, origin)
        mag = _prototype_magnitude(concept.prototype)
        denom = max(1.0, mag)
        return _clamp((dist / denom) * 0.5, 0.0, 1.0)
    if method == DetectionMethod.USAGE:
        count = int(concept.occurrence_count)
        if count <= 0:
            return 0.05
        return _clamp(math.log10(1.0 + count) / 3.0, 0.0, 1.0)
    if method == DetectionMethod.CONTEXTUAL:
        if not occurrences:
            return 0.05
        sentiments = [float(o.sentiment) for o in occurrences]
        avg = sum(sentiments) / len(sentiments)
        return _clamp(abs(avg), 0.0, 1.0)
    return 0.1


def _classify_drift(
    magnitude: float,
) -> Tuple[DriftType, DriftDirection]:
    """Map a drift magnitude to a (drift_type, drift_direction) pair.

    The mapping is intentionally simple so callers can rely on stable
    labels without having to interpret the raw magnitude.
    """
    if magnitude < 0.10:
        return DriftType.GRADUAL, DriftDirection.STABLE
    if magnitude < 0.40:
        return DriftType.INCREMENTAL, DriftDirection.SHIFTING
    if magnitude < 0.70:
        return DriftType.GRADUAL, DriftDirection.EXPANDING
    return DriftType.SUDDEN, DriftDirection.SHIFTING


# ---------------------------------------------------------------------------
# Module-Level Accessor
# ---------------------------------------------------------------------------


def get_concept_drift() -> ConceptDriftEngine:
    """Return the singleton ConceptDriftEngine instance."""
    return ConceptDriftEngine.get_instance()
