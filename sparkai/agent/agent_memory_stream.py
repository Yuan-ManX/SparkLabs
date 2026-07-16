"""
SparkLabs Agent - Memory Stream and Reflection System

This module implements a generative memory stream
for AI agents operating inside the SparkLabs AI-native game engine. The design
follows the influential Park et al. memory stream model, adapted for game
agents that must remember observations, reflect on experience, and retrieve
relevant memories to inform in-the-moment behaviour.

Core concepts:

  1. Observations with Importance Scoring
       Every recorded memory carries an importance score (1-10) and a derived
       importance level (TRIVIAL .. CRUCIAL). Higher-importance memories are
       more likely to be retrieved and less likely to be forgotten.

  2. Recency Decay
       Each memory's retrieval score is weighted by an exponential recency
       term, ``exp(-hours_since_creation / _RECENCY_DECAY_HOURS)``, so that
       fresh experiences dominate retrieval unless outweighed by importance
       or relevance.

  3. Relevance-based Retrieval
       Query-to-memory relevance is estimated with a Jaccard token-overlap
       similarity in [0, 1]. Combined with importance and recency, this yields
       a ranked retrieval result set.

  4. Reflection Synthesis
       Periodically a set of source memories is synthesised into a higher-level
       reflective insight (a \"reflection\") with a confidence score. Reflections
       are themselves retrievable and provide compressed, generalised knowledge
       that grows the agent's understanding over time.

Architecture:
  MemoryStreamEngine (Singleton, double-checked locking with threading.RLock)
    |-- MemoryObservation       -- a single recorded memory entry
    |-- ReflectionInsight       -- a synthesised reflective insight
    |-- RetrievalResult         -- a scored retrieval hit
    |-- AgentMemoryProfile      -- per-agent memory statistics
    |-- MemoryStreamStats       -- aggregate engine statistics
    |-- MemoryStreamSnapshot    -- complete engine state snapshot
    |-- MemoryStreamEvent       -- observable engine lifecycle event

All public mutating methods are protected by a re-entrant lock so the engine
is safe to call from multiple agent threads. Bounded in-memory stores use FIFO
eviction when their capacity constants are exceeded.
"""

from __future__ import annotations

import datetime
import math
import re
import threading
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set


# ---------------------------------------------------------------------------
# Capacity constants - bounded in-memory stores with FIFO eviction
# ---------------------------------------------------------------------------

_MAX_MEMORIES: int = 10000
_MAX_REFLECTIONS: int = 2000
_MAX_RETRIEVALS: int = 5000
_MAX_AGENTS: int = 500
_MAX_EVENTS: int = 2000


# ---------------------------------------------------------------------------
# Scoring constants
# ---------------------------------------------------------------------------

_IMPORTANCE_WEIGHT: float = 1.0
_RECENCY_WEIGHT: float = 1.0
_RELEVANCE_WEIGHT: float = 1.0
_RECENCY_DECAY_HOURS: float = 24.0  # exponential decay half-life scale


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

_TOKEN_PATTERN = re.compile(r"[a-z0-9]+")


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


def _hours_ago_timestamp(hours: float) -> str:
    """Return an ISO-8601 timestamp for the given number of hours in the past."""
    dt = datetime.datetime.utcnow() - datetime.timedelta(hours=hours)
    return dt.isoformat() + "Z"


def _parse_timestamp(value: str) -> Optional[datetime.datetime]:
    """Parse an ISO-8601 timestamp string into a datetime object.

    Returns ``None`` if the value cannot be parsed.
    """
    if not value:
        return None
    try:
        cleaned = value.replace("Z", "")
        return datetime.datetime.fromisoformat(cleaned)
    except (ValueError, TypeError, AttributeError):
        return None


def _split_tokens(text: str) -> List[str]:
    """Split text into an ordered list of lowercase alphanumeric tokens."""
    if not text:
        return []
    return _TOKEN_PATTERN.findall(text.lower())


def _tokenize(text: str) -> Set[str]:
    """Tokenize text into a set of lowercase alphanumeric tokens."""
    return set(_split_tokens(text))


def _similarity(text_a: str, text_b: str) -> float:
    """Estimate textual similarity in [0.0, 1.0] using Jaccard token overlap.

    Returns 0.0 when either side has no usable tokens.
    """
    tokens_a = _tokenize(text_a)
    tokens_b = _tokenize(text_b)
    if not tokens_a or not tokens_b:
        return 0.0
    union = tokens_a | tokens_b
    if not union:
        return 0.0
    intersection = tokens_a & tokens_b
    return len(intersection) / len(union)


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


# A small English stop-word set used for keyword extraction. Keeping this
# minimal avoids stripping meaningful game vocabulary.
_STOP_WORDS: Set[str] = {
    "the", "a", "an", "and", "or", "but", "of", "to", "in", "on", "at",
    "by", "for", "with", "about", "as", "is", "are", "was", "were", "be",
    "been", "being", "have", "has", "had", "do", "does", "did", "will",
    "would", "could", "should", "may", "might", "must", "shall", "can",
    "this", "that", "these", "those", "i", "you", "he", "she", "it", "we",
    "they", "them", "his", "her", "its", "our", "their", "my", "your",
    "from", "into", "over", "under", "than", "then", "so", "if", "when",
    "where", "what", "who", "how", "why", "not", "no", "nor", "too", "very",
    "just", "also", "only", "up", "down", "out", "off", "all", "any", "some",
}


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class MemoryType(Enum):
    """The kind of content a memory observation captures."""
    OBSERVATION = "observation"
    ACTION = "action"
    CONVERSATION = "conversation"
    THOUGHT = "thought"
    REFLECTION = "reflection"
    PLAN = "plan"
    EMOTION = "emotion"
    EVENT = "event"
    ACHIEVEMENT = "achievement"
    FAILURE = "failure"


class MemoryImportance(Enum):
    """Discrete importance levels derived from a 1-10 importance score."""
    TRIVIAL = "trivial"
    MINOR = "minor"
    MODERATE = "moderate"
    NOTABLE = "notable"
    SIGNIFICANT = "significant"
    CRUCIAL = "crucial"


class ReflectionType(Enum):
    """The category of a synthesised reflective insight."""
    GOAL_REVIEW = "goal_review"
    SKILL_ASSESSMENT = "skill_assessment"
    RELATIONSHIP_ANALYSIS = "relationship_analysis"
    PATTERN_DISCOVERY = "pattern_discovery"
    LESSON_LEARNED = "lesson_learned"
    STRATEGY_REVISION = "strategy_revision"
    SELF_EVALUATION = "self_evaluation"


class RetrievalStrategy(Enum):
    """Weighting strategy for memory retrieval."""
    BALANCED = "balanced"
    IMPORTANCE_FOCUSED = "importance_focused"
    RECENCY_FOCUSED = "recency_focused"
    RELEVANCE_FOCUSED = "relevance_focused"
    REFLECTION_INCLUSIVE = "reflection_inclusive"


class MemoryStreamEventKind(Enum):
    """Observable lifecycle events emitted by the memory stream engine."""
    MEMORY_RECORDED = "memory_recorded"
    MEMORY_RETRIEVED = "memory_retrieved"
    REFLECTION_GENERATED = "reflection_generated"
    REFLECTION_RETRIEVED = "reflection_retrieved"
    MEMORY_FORGOTTEN = "memory_forgotten"
    AGENT_REGISTERED = "agent_registered"


# ---------------------------------------------------------------------------
# Data Classes
# ---------------------------------------------------------------------------

@dataclass
class MemoryObservation:
    """A single recorded memory observation for an agent."""
    memory_id: str
    agent_id: str
    memory_type: MemoryType
    content: str
    importance_score: float
    importance_level: MemoryImportance
    created_at: str
    last_accessed_at: str
    access_count: int
    embedding_keywords: List[str] = field(default_factory=list)
    associated_agent_ids: List[str] = field(default_factory=list)
    location: str = ""
    timestamp: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this observation to a JSON-friendly dictionary."""
        return {
            "memory_id": self.memory_id,
            "agent_id": self.agent_id,
            "memory_type": self.memory_type.value,
            "content": self.content,
            "importance_score": self.importance_score,
            "importance_level": self.importance_level.value,
            "created_at": self.created_at,
            "last_accessed_at": self.last_accessed_at,
            "access_count": self.access_count,
            "embedding_keywords": list(self.embedding_keywords),
            "associated_agent_ids": list(self.associated_agent_ids),
            "location": self.location,
            "timestamp": self.timestamp,
            "metadata": dict(self.metadata) if self.metadata else {},
        }


@dataclass
class ReflectionInsight:
    """A synthesised reflective insight derived from source memories."""
    reflection_id: str
    agent_id: str
    reflection_type: ReflectionType
    source_memory_ids: List[str]
    insight_text: str
    confidence: float
    generated_at: str
    keywords: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this reflection insight to a JSON-friendly dictionary."""
        return {
            "reflection_id": self.reflection_id,
            "agent_id": self.agent_id,
            "reflection_type": self.reflection_type.value,
            "source_memory_ids": list(self.source_memory_ids),
            "insight_text": self.insight_text,
            "confidence": self.confidence,
            "generated_at": self.generated_at,
            "keywords": list(self.keywords),
            "metadata": dict(self.metadata) if self.metadata else {},
        }


@dataclass
class RetrievalResult:
    """A single scored retrieval hit for a memory query."""
    memory_id: str
    content: str
    importance_score: float
    recency_score: float
    relevance_score: float
    combined_score: float
    memory_type: MemoryType
    created_at: str

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this retrieval result to a JSON-friendly dictionary."""
        return {
            "memory_id": self.memory_id,
            "content": self.content,
            "importance_score": self.importance_score,
            "recency_score": self.recency_score,
            "relevance_score": self.relevance_score,
            "combined_score": self.combined_score,
            "memory_type": self.memory_type.value,
            "created_at": self.created_at,
        }


@dataclass
class AgentMemoryProfile:
    """Per-agent memory statistics maintained by the engine."""
    agent_id: str
    total_memories: int
    total_reflections: int
    avg_importance: float
    last_reflection_at: Optional[str]
    first_memory_at: Optional[str]
    created_at: str
    updated_at: str

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this agent profile to a JSON-friendly dictionary."""
        return {
            "agent_id": self.agent_id,
            "total_memories": self.total_memories,
            "total_reflections": self.total_reflections,
            "avg_importance": self.avg_importance,
            "last_reflection_at": self.last_reflection_at,
            "first_memory_at": self.first_memory_at,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


@dataclass
class MemoryStreamStats:
    """Aggregate statistics about the memory stream engine."""
    total_memories: int
    total_reflections: int
    total_retrievals: int
    total_agents: int
    memories_by_type: Dict[str, int]
    memories_by_importance: Dict[str, int]
    avg_importance: float

    def to_dict(self) -> Dict[str, Any]:
        """Serialize these statistics to a JSON-friendly dictionary."""
        return {
            "total_memories": self.total_memories,
            "total_reflections": self.total_reflections,
            "total_retrievals": self.total_retrievals,
            "total_agents": self.total_agents,
            "memories_by_type": dict(self.memories_by_type),
            "memories_by_importance": dict(self.memories_by_importance),
            "avg_importance": self.avg_importance,
        }


@dataclass
class MemoryStreamEvent:
    """An observable lifecycle event emitted by the memory stream engine."""
    event_id: str
    kind: MemoryStreamEventKind
    timestamp: str
    payload: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this event to a JSON-friendly dictionary."""
        return {
            "event_id": self.event_id,
            "kind": self.kind.value,
            "timestamp": self.timestamp,
            "payload": dict(self.payload) if self.payload else {},
        }


@dataclass
class MemoryStreamSnapshot:
    """A complete snapshot of the memory stream engine state."""
    initialized: bool
    memories: List[MemoryObservation]
    reflections: List[ReflectionInsight]
    agents: List[AgentMemoryProfile]
    events: List[MemoryStreamEvent]
    stats: MemoryStreamStats

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this snapshot to a JSON-friendly dictionary."""
        return {
            "initialized": self.initialized,
            "memories": [m.to_dict() for m in self.memories],
            "reflections": [r.to_dict() for r in self.reflections],
            "agents": [a.to_dict() for a in self.agents],
            "events": [e.to_dict() for e in self.events],
            "stats": self.stats.to_dict(),
        }


# ---------------------------------------------------------------------------
# Memory Stream Engine (Singleton with double-checked locking)
# ---------------------------------------------------------------------------

class MemoryStreamEngine:
    """Memory stream and reflection engine for AI game agents.

    The engine records observations with importance scores, retrieves memories
    using a combined importance / recency / relevance scoring formula, and
    synthesises higher-level reflective insights from groups of source
    memories. It is a thread-safe singleton accessed via :meth:`get_instance`
    or the module-level :func:`get_memory_stream` helper.

    Usage:
        engine = get_memory_stream()
        engine.register_agent("agent_alpha")
        engine.record_memory("agent_alpha", MemoryType.OBSERVATION,
                             "Found a hidden passage", importance_score=7)
        results = engine.retrieve_memories("agent_alpha", "hidden passage")
    """

    _instance: Optional["MemoryStreamEngine"] = None
    _lock: threading.RLock = threading.RLock()

    # -- Construction (double-checked locking) -----------------------------

    def __new__(cls) -> "MemoryStreamEngine":
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
            self._memories: Dict[str, MemoryObservation] = {}
            self._reflections: Dict[str, ReflectionInsight] = {}
            self._agents: Dict[str, AgentMemoryProfile] = {}
            self._events: List[MemoryStreamEvent] = []

            # Aggregate counters.
            self._total_retrievals: int = 0
            self._memory_counter: int = 0
            self._reflection_counter: int = 0
            self._agent_counter: int = 0

            self._initialized: bool = True

            # Seed baseline memory stream data.
            self._seed_data()

    @classmethod
    def get_instance(cls) -> "MemoryStreamEngine":
        """Return the singleton MemoryStreamEngine instance."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    # ------------------------------------------------------------------
    # Agent profile management
    # ------------------------------------------------------------------

    def register_agent(self, agent_id: str) -> AgentMemoryProfile:
        """Create (or return an existing) memory profile for an agent.

        Args:
            agent_id: Unique identifier of the agent to register.

        Returns:
            The :class:`AgentMemoryProfile` for the agent. If the agent was
            already registered, the existing profile is returned unchanged.
        """
        with self._lock:
            if agent_id in self._agents:
                return self._agents[agent_id]
            now = _now()
            profile = AgentMemoryProfile(
                agent_id=agent_id,
                total_memories=0,
                total_reflections=0,
                avg_importance=0.0,
                last_reflection_at=None,
                first_memory_at=None,
                created_at=now,
                updated_at=now,
            )
            self._agents[agent_id] = profile
            self._agent_counter += 1
            _evict_fifo_dict(self._agents, _MAX_AGENTS)
            self._record_event(
                MemoryStreamEventKind.AGENT_REGISTERED,
                {"agent_id": agent_id},
            )
            return profile

    def list_agents(self) -> List[AgentMemoryProfile]:
        """Return all registered agent memory profiles."""
        with self._lock:
            return list(self._agents.values())

    def get_agent(self, agent_id: str) -> Optional[AgentMemoryProfile]:
        """Return the memory profile for an agent, or None if not registered."""
        with self._lock:
            return self._agents.get(agent_id)

    def _ensure_agent(self, agent_id: str) -> AgentMemoryProfile:
        """Return the profile for an agent, creating one if missing.

        Assumes the caller already holds ``self._lock``.
        """
        profile = self._agents.get(agent_id)
        if profile is not None:
            return profile
        now = _now()
        profile = AgentMemoryProfile(
            agent_id=agent_id,
            total_memories=0,
            total_reflections=0,
            avg_importance=0.0,
            last_reflection_at=None,
            first_memory_at=None,
            created_at=now,
            updated_at=now,
        )
        self._agents[agent_id] = profile
        self._agent_counter += 1
        _evict_fifo_dict(self._agents, _MAX_AGENTS)
        self._record_event(
            MemoryStreamEventKind.AGENT_REGISTERED,
            {"agent_id": agent_id},
        )
        return profile

    def _update_agent_for_memory(self, agent_id: str, importance: float) -> None:
        """Refresh per-agent aggregate statistics after a memory is added.

        Assumes the caller already holds ``self._lock``.
        """
        profile = self._ensure_agent(agent_id)
        # Recompute aggregates from the full set of agent memories to keep
        # the profile consistent even after forget operations.
        scores: List[float] = []
        first_at: Optional[str] = None
        for mem in self._memories.values():
            if mem.agent_id != agent_id:
                continue
            scores.append(mem.importance_score)
            if first_at is None or mem.created_at < first_at:
                first_at = mem.created_at
        profile.total_memories = len(scores)
        profile.avg_importance = (
            sum(scores) / len(scores) if scores else 0.0
        )
        profile.first_memory_at = first_at
        profile.updated_at = _now()

    def _update_agent_for_reflection(self, agent_id: str) -> None:
        """Refresh per-agent reflection statistics after a reflection is added.

        Assumes the caller already holds ``self._lock``.
        """
        profile = self._ensure_agent(agent_id)
        count = 0
        last_at: Optional[str] = None
        for ref in self._reflections.values():
            if ref.agent_id != agent_id:
                continue
            count += 1
            if last_at is None or ref.generated_at > last_at:
                last_at = ref.generated_at
        profile.total_reflections = count
        profile.last_reflection_at = last_at
        profile.updated_at = _now()

    # ------------------------------------------------------------------
    # Memory recording and lookup
    # ------------------------------------------------------------------

    def record_memory(
        self,
        agent_id: str,
        memory_type: MemoryType,
        content: str,
        importance_score: float,
        location: str = "",
        associated_agent_ids: Optional[List[str]] = None,
        timestamp: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> MemoryObservation:
        """Record a memory observation for an agent.

        The importance level is auto-derived from ``importance_score`` and
        keywords are extracted from ``content`` via tokenization. The agent's
        memory profile is updated to reflect the new observation. If the agent
        has not been registered yet, a profile is created automatically.

        Args:
            agent_id: Identifier of the agent that owns the memory.
            memory_type: The :class:`MemoryType` categorisation of the content.
            content: Free-form textual content of the memory observation.
            importance_score: Salience in the range 1-10 (clamped). Higher
                values increase retrieval probability and resistance to
                forgetting.
            location: Optional location tag where the observation occurred.
            associated_agent_ids: Other agents referenced by this memory.
            timestamp: Optional narrative/game-world timestamp string. When
                omitted, the wall-clock creation time is used.
            metadata: Optional arbitrary metadata to attach to the memory.

        Returns:
            The newly created :class:`MemoryObservation`.
        """
        with self._lock:
            clamped_score = _clamp(float(importance_score), low=1.0, high=10.0)
            now = _now()
            observation = MemoryObservation(
                memory_id=_new_id(),
                agent_id=agent_id,
                memory_type=memory_type,
                content=content,
                importance_score=clamped_score,
                importance_level=self._compute_importance_level(clamped_score),
                created_at=now,
                last_accessed_at=now,
                access_count=0,
                embedding_keywords=self._extract_keywords(content),
                associated_agent_ids=list(associated_agent_ids) if associated_agent_ids else [],
                location=location or "",
                timestamp=timestamp or now,
                metadata=dict(metadata) if metadata else {},
            )
            return self._ingest_memory(observation)

    def _ingest_memory(
        self, observation: MemoryObservation
    ) -> MemoryObservation:
        """Store a constructed observation and update derived state.

        Assumes the caller already holds ``self._lock``.
        """
        self._memories[observation.memory_id] = observation
        self._memory_counter += 1
        _evict_fifo_dict(self._memories, _MAX_MEMORIES)
        self._update_agent_for_memory(observation.agent_id, observation.importance_score)
        self._record_event(
            MemoryStreamEventKind.MEMORY_RECORDED,
            {
                "memory_id": observation.memory_id,
                "agent_id": observation.agent_id,
                "memory_type": observation.memory_type.value,
                "importance_score": observation.importance_score,
            },
        )
        return observation

    def list_memories(
        self,
        agent_id: Optional[str] = None,
        memory_type: Optional[MemoryType] = None,
        importance_level: Optional[MemoryImportance] = None,
        limit: int = 100,
    ) -> List[MemoryObservation]:
        """List memories, optionally filtered by agent, type, and importance.

        Args:
            agent_id: When provided, only memories owned by this agent are
                returned.
            memory_type: When provided, only memories of this type are
                returned.
            importance_level: When provided, only memories at this importance
                level are returned.
            limit: Maximum number of memories to return. ``0`` returns an
                empty list.

        Returns:
            A list of matching :class:`MemoryObservation` objects in insertion
            order, truncated to ``limit``.
        """
        with self._lock:
            n = max(0, int(limit))
            results: List[MemoryObservation] = []
            for mem in self._memories.values():
                if agent_id is not None and mem.agent_id != agent_id:
                    continue
                if memory_type is not None and mem.memory_type != memory_type:
                    continue
                if importance_level is not None and mem.importance_level != importance_level:
                    continue
                results.append(mem)
                if n > 0 and len(results) >= n:
                    break
            return results

    def get_memory(self, memory_id: str) -> Optional[MemoryObservation]:
        """Return a single memory by id, or None if not found."""
        with self._lock:
            return self._memories.get(memory_id)

    # ------------------------------------------------------------------
    # Memory retrieval
    # ------------------------------------------------------------------

    def retrieve_memories(
        self,
        agent_id: str,
        query: str,
        limit: int = 10,
        strategy: RetrievalStrategy = RetrievalStrategy.BALANCED,
    ) -> List[RetrievalResult]:
        """Retrieve memories for an agent using combined scoring.

        The combined score is::

            w_i * (importance_score / 10)
          + w_r * exp(-hours_since_creation / _RECENCY_DECAY_HOURS)
          + w_v * similarity(query, memory.content)

        where (w_i, w_r, w_v) depend on the chosen ``strategy``. Retrieved
        memories have their access metadata updated. Results are sorted by
        combined score, descending.

        Args:
            agent_id: Identifier of the agent whose memories are searched.
            query: Natural-language retrieval query.
            limit: Maximum number of results to return. ``0`` returns an empty
                list.
            strategy: Weighting strategy. ``IMPORTANCE_FOCUSED`` weights
                salience 3x, ``RECENCY_FOCUSED`` weights freshness 3x,
                ``RELEVANCE_FOCUSED`` weights query overlap 3x,
                ``REFLECTION_INCLUSIVE`` uses balanced weights and also folds
                the agent's reflections into the ranked result set.

        Returns:
            A list of :class:`RetrievalResult` sorted by ``combined_score``
            descending.
        """
        with self._lock:
            w_importance, w_recency, w_relevance = self._strategy_weights(strategy)
            n = max(0, int(limit))
            results: List[RetrievalResult] = []

            for mem in self._memories.values():
                if mem.agent_id != agent_id:
                    continue
                importance = mem.importance_score / 10.0
                recency = self._compute_recency(mem.created_at)
                relevance = self._compute_relevance(query, mem.content)
                combined = (
                    w_importance * importance
                    + w_recency * recency
                    + w_relevance * relevance
                )
                results.append(
                    RetrievalResult(
                        memory_id=mem.memory_id,
                        content=mem.content,
                        importance_score=mem.importance_score,
                        recency_score=recency,
                        relevance_score=relevance,
                        combined_score=combined,
                        memory_type=mem.memory_type,
                        created_at=mem.created_at,
                    )
                )

            # When the strategy is reflection-inclusive, also fold matching
            # reflections into the result set so callers get a single ranked
            # view of both raw memories and synthesised insights.
            if strategy == RetrievalStrategy.REFLECTION_INCLUSIVE:
                results.extend(self._reflection_retrieval_results(agent_id, query))

            results.sort(key=lambda r: r.combined_score, reverse=True)
            if n > 0:
                results = results[:n]

            # Update access metadata for the returned memories.
            now = _now()
            for result in results:
                mem = self._memories.get(result.memory_id)
                if mem is not None:
                    mem.last_accessed_at = now
                    mem.access_count += 1

            self._total_retrievals += 1
            _evict_fifo_list(self._events, _MAX_EVENTS)  # keep events bounded
            self._record_event(
                MemoryStreamEventKind.MEMORY_RETRIEVED,
                {
                    "agent_id": agent_id,
                    "query": query,
                    "strategy": strategy.value,
                    "returned": len(results),
                },
            )
            return results

    def _strategy_weights(
        self, strategy: RetrievalStrategy
    ) -> tuple:
        """Return (importance_weight, recency_weight, relevance_weight)."""
        if strategy == RetrievalStrategy.IMPORTANCE_FOCUSED:
            return (3.0, 1.0, 1.0)
        if strategy == RetrievalStrategy.RECENCY_FOCUSED:
            return (1.0, 3.0, 1.0)
        if strategy == RetrievalStrategy.RELEVANCE_FOCUSED:
            return (1.0, 1.0, 3.0)
        # BALANCED and REFLECTION_INCLUSIVE both use equal weights.
        return (1.0, 1.0, 1.0)

    def _reflection_retrieval_results(
        self, agent_id: str, query: str
    ) -> List[RetrievalResult]:
        """Convert an agent's reflections into retrieval-result entries.

        Assumes the caller already holds ``self._lock``.
        """
        results: List[RetrievalResult] = []
        for ref in self._reflections.values():
            if ref.agent_id != agent_id:
                continue
            relevance = self._compute_relevance(query, ref.insight_text)
            recency = self._compute_recency(ref.generated_at)
            importance = _clamp(ref.confidence, 0.0, 1.0)
            combined = (
                _IMPORTANCE_WEIGHT * importance
                + _RECENCY_WEIGHT * recency
                + _RELEVANCE_WEIGHT * relevance
            )
            results.append(
                RetrievalResult(
                    memory_id=ref.reflection_id,
                    content=ref.insight_text,
                    importance_score=round(importance * 10.0, 4),
                    recency_score=recency,
                    relevance_score=relevance,
                    combined_score=combined,
                    memory_type=MemoryType.REFLECTION,
                    created_at=ref.generated_at,
                )
            )
        return results

    # ------------------------------------------------------------------
    # Reflection synthesis and retrieval
    # ------------------------------------------------------------------

    def generate_reflection(
        self,
        agent_id: str,
        reflection_type: ReflectionType,
        source_memory_ids: List[str],
        insight_text: str,
        confidence: float,
        keywords: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> ReflectionInsight:
        """Synthesise a reflective insight from a set of source memories.

        Reflections compress groups of memories into higher-level, generalised
        knowledge. The agent's profile is updated with the new reflection's
        timestamp and reflection count.

        Args:
            agent_id: Identifier of the agent that owns the reflection.
            reflection_type: The :class:`ReflectionType` categorisation.
            source_memory_ids: Identifiers of the memories this insight
                synthesises. Stored as references for provenance.
            insight_text: The synthesised insight as free-form text.
            confidence: Confidence in the insight, clamped to [0.0, 1.0].
            keywords: Optional explicit keyword list. When omitted, keywords
                are extracted from ``insight_text``.
            metadata: Optional arbitrary metadata to attach.

        Returns:
            The newly created :class:`ReflectionInsight`.
        """
        with self._lock:
            clamped_confidence = _clamp(float(confidence), 0.0, 1.0)
            now = _now()
            insight = ReflectionInsight(
                reflection_id=_new_id(),
                agent_id=agent_id,
                reflection_type=reflection_type,
                source_memory_ids=list(source_memory_ids) if source_memory_ids else [],
                insight_text=insight_text,
                confidence=clamped_confidence,
                generated_at=now,
                keywords=list(keywords) if keywords else self._extract_keywords(insight_text),
                metadata=dict(metadata) if metadata else {},
            )
            return self._ingest_reflection(insight)

    def _ingest_reflection(
        self, insight: ReflectionInsight
    ) -> ReflectionInsight:
        """Store a constructed reflection and update derived state.

        Assumes the caller already holds ``self._lock``.
        """
        self._reflections[insight.reflection_id] = insight
        self._reflection_counter += 1
        _evict_fifo_dict(self._reflections, _MAX_REFLECTIONS)
        self._update_agent_for_reflection(insight.agent_id)
        self._record_event(
            MemoryStreamEventKind.REFLECTION_GENERATED,
            {
                "reflection_id": insight.reflection_id,
                "agent_id": insight.agent_id,
                "reflection_type": insight.reflection_type.value,
                "confidence": insight.confidence,
            },
        )
        return insight

    def list_reflections(
        self,
        agent_id: Optional[str] = None,
        reflection_type: Optional[ReflectionType] = None,
        limit: int = 100,
    ) -> List[ReflectionInsight]:
        """List reflections, optionally filtered by agent and type."""
        with self._lock:
            n = max(0, int(limit))
            results: List[ReflectionInsight] = []
            for ref in self._reflections.values():
                if agent_id is not None and ref.agent_id != agent_id:
                    continue
                if reflection_type is not None and ref.reflection_type != reflection_type:
                    continue
                results.append(ref)
                if n > 0 and len(results) >= n:
                    break
            return results

    def get_reflection(self, reflection_id: str) -> Optional[ReflectionInsight]:
        """Return a single reflection by id, or None if not found."""
        with self._lock:
            return self._reflections.get(reflection_id)

    def retrieve_reflections(
        self,
        agent_id: str,
        query: str,
        limit: int = 5,
    ) -> List[ReflectionInsight]:
        """Retrieve an agent's reflections by keyword/text match with the query.

        Reflections are ranked by a combined similarity of the query against
        the insight text (weight 0.7) and the reflection's keyword set
        (weight 0.3).

        Args:
            agent_id: Identifier of the agent whose reflections are searched.
            query: Natural-language retrieval query.
            limit: Maximum number of reflections to return. ``0`` returns an
                empty list.

        Returns:
            A list of :class:`ReflectionInsight` objects ranked by combined
            similarity, descending.
        """
        with self._lock:
            n = max(0, int(limit))
            scored: List[tuple] = []
            query_tokens = _tokenize(query)
            for ref in self._reflections.values():
                if ref.agent_id != agent_id:
                    continue
                text_sim = _similarity(query, ref.insight_text)
                keyword_tokens = set(k.lower() for k in ref.keywords)
                if query_tokens and keyword_tokens:
                    keyword_sim = len(query_tokens & keyword_tokens) / len(query_tokens | keyword_tokens)
                else:
                    keyword_sim = 0.0
                score = 0.7 * text_sim + 0.3 * keyword_sim
                scored.append((score, ref))
            scored.sort(key=lambda pair: pair[0], reverse=True)
            results = [ref for _, ref in scored[:n]] if n > 0 else []
            self._total_retrievals += 1
            self._record_event(
                MemoryStreamEventKind.REFLECTION_RETRIEVED,
                {
                    "agent_id": agent_id,
                    "query": query,
                    "returned": len(results),
                },
            )
            return results

    # ------------------------------------------------------------------
    # Forgetting
    # ------------------------------------------------------------------

    def forget_memory(self, memory_id: str) -> bool:
        """Remove a single memory by id (forgetting). Returns True if removed.

        Args:
            memory_id: Identifier of the memory to forget.

        Returns:
            ``True`` if the memory existed and was removed, ``False`` otherwise.
        """
        with self._lock:
            mem = self._memories.pop(memory_id, None)
            if mem is None:
                return False
            self._record_event(
                MemoryStreamEventKind.MEMORY_FORGOTTEN,
                {
                    "memory_id": memory_id,
                    "agent_id": mem.agent_id,
                    "importance_score": mem.importance_score,
                },
            )
            # Refresh the affected agent's aggregates.
            self._update_agent_for_memory(mem.agent_id, mem.importance_score)
            return True

    def forget_old_memories(
        self,
        agent_id: str,
        max_age_hours: float,
        min_importance: float = 0,
    ) -> int:
        """Forget memories older than ``max_age_hours`` with importance below
        ``min_importance``. Returns the number of memories forgotten.

        A memory is forgotten when BOTH conditions hold:
          - its age in hours exceeds ``max_age_hours``, AND
          - its importance score is strictly below ``min_importance``.

        Setting ``min_importance`` above 10 forgets all old memories for the
        agent regardless of importance.
        """
        with self._lock:
            now_dt = datetime.datetime.utcnow()
            threshold = float(min_importance)
            forgotten: List[str] = []
            for mem in list(self._memories.values()):
                if mem.agent_id != agent_id:
                    continue
                if mem.importance_score >= threshold:
                    continue
                created_dt = _parse_timestamp(mem.created_at)
                if created_dt is None:
                    continue
                age_hours = (now_dt - created_dt).total_seconds() / 3600.0
                if age_hours > max_age_hours:
                    forgotten.append(mem.memory_id)
            for mid in forgotten:
                self.forget_memory(mid)
            return len(forgotten)

    # ------------------------------------------------------------------
    # Internal scoring helpers
    # ------------------------------------------------------------------

    def _compute_importance_level(self, score: float) -> MemoryImportance:
        """Map a 1-10 importance score to a discrete MemoryImportance level."""
        if score < 2:
            return MemoryImportance.TRIVIAL
        if score < 4:
            return MemoryImportance.MINOR
        if score < 6:
            return MemoryImportance.MODERATE
        if score < 7:
            return MemoryImportance.NOTABLE
        if score < 9:
            return MemoryImportance.SIGNIFICANT
        return MemoryImportance.CRUCIAL

    def _compute_recency(
        self,
        created_at: str,
        current_time: Optional[str] = None,
    ) -> float:
        """Compute exponential recency decay in [0.0, 1.0].

        ``recency = exp(-hours_since_creation / _RECENCY_DECAY_HOURS)``
        """
        created_dt = _parse_timestamp(created_at)
        if created_dt is None:
            return 0.0
        if current_time is None:
            current_dt = datetime.datetime.utcnow()
        else:
            current_dt = _parse_timestamp(current_time)
            if current_dt is None:
                current_dt = datetime.datetime.utcnow()
        hours = (current_dt - created_dt).total_seconds() / 3600.0
        if hours < 0:
            hours = 0.0
        return math.exp(-hours / _RECENCY_DECAY_HOURS)

    def _compute_relevance(self, query: str, content: str) -> float:
        """Compute query-to-content relevance as Jaccard token overlap."""
        return _similarity(query, content)

    def _extract_keywords(self, text: str) -> List[str]:
        """Extract up to five keywords from text.

        Tokens are lowercased, stop words are removed, and the remaining
        tokens are ranked by frequency (ties broken alphabetically). The
        top five are returned.
        """
        tokens = [t for t in _split_tokens(text) if t not in _STOP_WORDS]
        if not tokens:
            return []
        counts: Dict[str, int] = {}
        for token in tokens:
            counts[token] = counts.get(token, 0) + 1
        ranked = sorted(counts.keys(), key=lambda k: (-counts[k], k))
        return ranked[:5]

    # ------------------------------------------------------------------
    # Events, Stats, Status, Snapshot
    # ------------------------------------------------------------------

    def _record_event(
        self,
        kind: MemoryStreamEventKind,
        payload: Dict[str, Any],
    ) -> None:
        """Record an observable memory stream event.

        Assumes the caller already holds ``self._lock``. The event log is
        bounded by ``_MAX_EVENTS`` with FIFO eviction.
        """
        event = MemoryStreamEvent(
            event_id=_new_id(),
            kind=kind,
            timestamp=_now(),
            payload=dict(payload) if payload else {},
        )
        self._events.append(event)
        _evict_fifo_list(self._events, _MAX_EVENTS)

    def list_events(self, limit: int = 100) -> List[MemoryStreamEvent]:
        """Return the most recent memory stream events, newest first."""
        with self._lock:
            n = max(0, int(limit))
            if n == 0:
                return []
            return list(reversed(self._events))[:n]

    def get_stats(self) -> MemoryStreamStats:
        """Return aggregate statistics about the memory stream engine."""
        with self._lock:
            memories = list(self._memories.values())
            by_type: Dict[str, int] = {}
            by_importance: Dict[str, int] = {}
            total_importance = 0.0
            for mem in memories:
                by_type[mem.memory_type.value] = by_type.get(mem.memory_type.value, 0) + 1
                by_importance[mem.importance_level.value] = by_importance.get(mem.importance_level.value, 0) + 1
                total_importance += mem.importance_score
            avg_importance = (
                total_importance / len(memories) if memories else 0.0
            )
            return MemoryStreamStats(
                total_memories=len(memories),
                total_reflections=len(self._reflections),
                total_retrievals=self._total_retrievals,
                total_agents=len(self._agents),
                memories_by_type=by_type,
                memories_by_importance=by_importance,
                avg_importance=round(avg_importance, 4),
            )

    def get_status(self) -> Dict[str, Any]:
        """Return a comprehensive status dictionary for diagnostics."""
        with self._lock:
            stats = self.get_stats()
            status: Dict[str, Any] = {
                "initialized": self._initialized,
                "total_memories": len(self._memories),
                "total_reflections": len(self._reflections),
                "total_agents": len(self._agents),
                "total_events": len(self._events),
                "total_retrievals": self._total_retrievals,
                "memory_counter": self._memory_counter,
                "reflection_counter": self._reflection_counter,
                "agent_counter": self._agent_counter,
                "avg_importance": stats.avg_importance,
                "memories_by_type": dict(stats.memories_by_type),
                "memories_by_importance": dict(stats.memories_by_importance),
                "capacities": {
                    "max_memories": _MAX_MEMORIES,
                    "max_reflections": _MAX_REFLECTIONS,
                    "max_retrievals": _MAX_RETRIEVALS,
                    "max_agents": _MAX_AGENTS,
                    "max_events": _MAX_EVENTS,
                },
                "scoring": {
                    "importance_weight": _IMPORTANCE_WEIGHT,
                    "recency_weight": _RECENCY_WEIGHT,
                    "relevance_weight": _RELEVANCE_WEIGHT,
                    "recency_decay_hours": _RECENCY_DECAY_HOURS,
                },
            }
            return status

    def get_snapshot(self) -> MemoryStreamSnapshot:
        """Return a complete snapshot of the memory stream engine state."""
        with self._lock:
            return MemoryStreamSnapshot(
                initialized=self._initialized,
                memories=list(self._memories.values()),
                reflections=list(self._reflections.values()),
                agents=list(self._agents.values()),
                events=list(self._events),
                stats=self.get_stats(),
            )

    # ------------------------------------------------------------------
    # Reset
    # ------------------------------------------------------------------

    def reset(self) -> None:
        """Clear all tracked state and re-seed baseline data.

        Unlike some sibling engines, this method re-seeds the baseline memory
        stream data after clearing, restoring the engine to a freshly
        initialized state.
        """
        with self._lock:
            self._memories.clear()
            self._reflections.clear()
            self._agents.clear()
            self._events.clear()
            self._total_retrievals = 0
            self._memory_counter = 0
            self._reflection_counter = 0
            self._agent_counter = 0
            self._seed_data()

    # ------------------------------------------------------------------
    # Seed data
    # ------------------------------------------------------------------

    def _seed_data(self) -> None:
        """Populate the engine with baseline SparkLabs memory stream data.

        Seeds two agents (``agent_alpha`` and ``agent_beta``), six memories
        for ``agent_alpha`` spanning multiple memory types and importance
        levels, three memories for ``agent_beta``, and two reflective
        insights for ``agent_alpha`` derived from those memories.
        """
        # --- Agents ----------------------------------------------------
        self._ensure_agent("agent_alpha")
        self._ensure_agent("agent_beta")

        # --- Memories for agent_alpha ----------------------------------
        # Spaced over the past several hours so recency scores differ.
        alpha_memory_specs = [
            (
                MemoryType.OBSERVATION,
                "Found a hidden passage behind the waterfall",
                7.0,
                "forest",
                [],
                _hours_ago_timestamp(72.0),
                ["hidden", "passage", "waterfall"],
            ),
            (
                MemoryType.ACTION,
                "Defeated the goblin chieftain in single combat",
                8.0,
                "",
                [],
                _hours_ago_timestamp(60.0),
                ["defeated", "goblin", "chieftain", "combat"],
            ),
            (
                MemoryType.CONVERSATION,
                "The merchant shared rumors about a dragon's lair",
                6.0,
                "",
                ["merchant_1"],
                _hours_ago_timestamp(48.0),
                ["merchant", "rumors", "dragon", "lair"],
            ),
            (
                MemoryType.THOUGHT,
                "I should prepare fire resistance gear before facing the dragon",
                7.0,
                "",
                [],
                _hours_ago_timestamp(36.0),
                ["prepare", "fire", "resistance", "dragon"],
            ),
            (
                MemoryType.ACHIEVEMENT,
                "Reached level 10 and unlocked the Paladin class",
                9.0,
                "",
                [],
                _hours_ago_timestamp(12.0),
                ["level", "10", "paladin", "class"],
            ),
            (
                MemoryType.EMOTION,
                "Felt a sense of dread when entering the cursed temple",
                5.0,
                "temple",
                [],
                _hours_ago_timestamp(4.0),
                ["dread", "cursed", "temple"],
            ),
        ]
        alpha_memory_ids: List[str] = []
        for (
            mem_type,
            content,
            importance,
            location,
            associated,
            created,
            keywords,
        ) in alpha_memory_specs:
            observation = MemoryObservation(
                memory_id=_new_id(),
                agent_id="agent_alpha",
                memory_type=mem_type,
                content=content,
                importance_score=importance,
                importance_level=self._compute_importance_level(importance),
                created_at=created,
                last_accessed_at=created,
                access_count=0,
                embedding_keywords=list(keywords),
                associated_agent_ids=list(associated),
                location=location,
                timestamp=created,
                metadata={"seed": True},
            )
            self._ingest_memory(observation)
            alpha_memory_ids.append(observation.memory_id)

        # --- Memories for agent_beta -----------------------------------
        beta_memory_specs = [
            (
                MemoryType.OBSERVATION,
                "Discovered a rare herb garden in the mountain pass",
                6.0,
                "mountain",
                [],
                _hours_ago_timestamp(40.0),
                ["rare", "herb", "garden", "mountain"],
            ),
            (
                MemoryType.CONVERSATION,
                "Agent alpha mentioned needing fire resistance gear",
                5.0,
                "",
                ["agent_alpha"],
                _hours_ago_timestamp(30.0),
                ["alpha", "fire", "resistance", "gear"],
            ),
            (
                MemoryType.PLAN,
                "Will brew fire resistance potions for the dragon encounter",
                7.0,
                "",
                [],
                _hours_ago_timestamp(18.0),
                ["brew", "fire", "resistance", "potions", "dragon"],
            ),
        ]
        for (
            mem_type,
            content,
            importance,
            location,
            associated,
            created,
            keywords,
        ) in beta_memory_specs:
            observation = MemoryObservation(
                memory_id=_new_id(),
                agent_id="agent_beta",
                memory_type=mem_type,
                content=content,
                importance_score=importance,
                importance_level=self._compute_importance_level(importance),
                created_at=created,
                last_accessed_at=created,
                access_count=0,
                embedding_keywords=list(keywords),
                associated_agent_ids=list(associated),
                location=location,
                timestamp=created,
                metadata={"seed": True},
            )
            self._ingest_memory(observation)

        # --- Reflections for agent_alpha -------------------------------
        # Source memory ids reference the seeded memories above.
        reflection_specs = [
            (
                ReflectionType.PATTERN_DISCOVERY,
                [alpha_memory_ids[0], alpha_memory_ids[2]],
                "Water sources often hide secrets in this world - "
                "I should investigate all waterfalls and rivers",
                0.75,
                ["water", "secrets", "investigate"],
            ),
            (
                ReflectionType.STRATEGY_REVISION,
                [alpha_memory_ids[1], alpha_memory_ids[3], alpha_memory_ids[4]],
                "My combat skills have grown significantly - I can now face "
                "stronger foes, but I need better preparation for elemental threats",
                0.82,
                ["combat", "growth", "preparation", "elemental"],
            ),
        ]
        for ref_type, source_ids, insight_text, confidence, keywords in reflection_specs:
            insight = ReflectionInsight(
                reflection_id=_new_id(),
                agent_id="agent_alpha",
                reflection_type=ref_type,
                source_memory_ids=list(source_ids),
                insight_text=insight_text,
                confidence=confidence,
                generated_at=_hours_ago_timestamp(2.0),
                keywords=list(keywords),
                metadata={"seed": True},
            )
            self._ingest_reflection(insight)


# ---------------------------------------------------------------------------
# Module-Level Accessor
# ---------------------------------------------------------------------------

def get_memory_stream() -> MemoryStreamEngine:
    """Return the singleton MemoryStreamEngine instance."""
    return MemoryStreamEngine.get_instance()
