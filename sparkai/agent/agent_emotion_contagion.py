"""
SparkLabs AI-Native Game Engine - Agent Emotion Contagion System
================================================================

Genagents-style emotion contagion engine for AI agents in the SparkLabs
AI-native game engine.

This module models how emotions and moods spread through a population of
agents connected in a social network. When an agent experiences an
emotion, that emotion can propagate to nearby agents based on connection
strength, agent susceptibility, and the emotion's intensity. The engine
tracks contagion chains, detects emotion outbreaks, and supports decay of
active emotional signals over time.

Core Concepts
-------------

1. **Emotion Signals** -- ``emit_emotion`` records an :class:`EmotionSignal`
   emitted by an agent. The engine then propagates the signal through the
   social network to connected agents, attenuating intensity at each hop.

2. **Agent Susceptibility** -- Each agent has a ``base_susceptibility`` in
   [0, 1] that modulates how strongly incoming emotions affect them.
   Agents can be made immune to specific emotions (``grant_immunity``) or
   amplify certain emotions (``add_amplifier``). A ``social_resistance``
   threshold gates whether a signal is strong enough to shift the
   agent's mood at all.

3. **Contagion Links** -- Directed social connections between agents
   (``connect_agents``). Each :class:`ContagionLink` carries a
   ``connection_strength`` in [0, 1] that scales how much of an emotion's
   intensity survives the transmission.

4. **Propagation** -- ``propagate_signal`` walks the source agent's
   outgoing links via breadth-first expansion. For each target agent:
   - Immune agents are skipped.
   - ``received_intensity = signal.intensity * connection_strength *
     target.base_susceptibility * amplifier``
   - If ``received_intensity > target.social_resistance`` a
     :class:`ContagionRecord` is created and the target's mood shifts by
     the received intensity.

5. **Contagion Chains** -- When an emotion reaches 3+ agents, the engine
   records a :class:`ContagionChain` tracking the propagation path and
   the total intensity decay from origin to the furthest recipient.

6. **Outbreaks** -- When 3+ agents are affected by the same emotion
   within a time window, an :class:`EmotionOutbreak` is detected.
   Outbreaks can be contained (``contain_outbreak``) and eventually
   expire.

7. **Decay** -- ``apply_decay`` attenuates all active emotion signal
   intensities, modeling the natural fade of emotional impact over time.

The engine is a process-wide singleton accessed via ``get_instance()`` or
the module-level ``get_emotion_contagion()`` helper. All public methods
are guarded by a reentrant lock for thread safety. In-memory stores are
bounded by capacity constants and use FIFO eviction so the engine never
grows without limit.
"""

from __future__ import annotations

import datetime
import threading
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple


# ---------------------------------------------------------------------------
# Capacity constants - bounded in-memory stores with FIFO eviction
# ---------------------------------------------------------------------------

_MAX_CONTAGION_EVENTS: int = 5000
_MAX_SIGNALS: int = 10000
_MAX_RECORDS: int = 20000
_MAX_AGENTS: int = 1000
_MAX_LINKS: int = 5000
_MAX_CHAINS: int = 2000
_MAX_OUTBREAKS: int = 500


# ---------------------------------------------------------------------------
# Propagation / outbreak tuning constants
# ---------------------------------------------------------------------------

# BFS depth limit for transitive propagation. Prevents unbounded walks in
# densely connected networks.
_MAX_PROPAGATION_DEPTH: int = 6

# Window (in seconds) within which 3+ affected agents trigger an outbreak.
_OUTBREAK_WINDOW_SECONDS: float = 3600.0

# Active outbreaks expire after this many seconds.
_OUTBREAK_TTL_SECONDS: float = 86400.0

# Signals whose intensity falls below this threshold are pruned by decay.
_DECAY_EPSILON: float = 0.01


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


def _seconds_between(start_ts: str, end_ts: str) -> float:
    """Return the number of seconds between two ISO-8601 timestamps.

    Returns ``float('inf')`` if either timestamp cannot be parsed.
    """
    start_dt = _parse_timestamp(start_ts)
    end_dt = _parse_timestamp(end_ts)
    if start_dt is None or end_dt is None:
        return float("inf")
    return (end_dt - start_dt).total_seconds()


def _evict_fifo_dict(store: Dict[str, Any], max_size: int) -> None:
    """Evict the oldest inserted entries from a dict until within bounds.

    Python dicts preserve insertion order (3.7+), so the first key
    returned by iteration is the oldest. This implements FIFO eviction.
    """
    while len(store) > max_size:
        oldest_key = next(iter(store))
        store.pop(oldest_key, None)


def _evict_fifo_list(store: List[Any], max_size: int) -> None:
    """Evict the oldest inserted entries from a list until within bounds."""
    while len(store) > max_size:
        store.pop(0)


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class ContagionMode(Enum):
    """Directionality of an emotion contagion channel."""
    PROPAGATION_SOURCE = "propagation_source"
    RECEIVING_AGENT = "receiving_agent"
    BIDIRECTIONAL = "bidirectional"


class EmotionValence(Enum):
    """Affective valence of an emotion signal."""
    POSITIVE = "positive"
    NEGATIVE = "negative"
    NEUTRAL = "neutral"


class ContagionPath(Enum):
    """How an emotion reached a target agent."""
    DIRECT = "direct"
    TRANSITIVE = "transitive"
    NETWORK_CHAIN = "network_chain"


class OutbreakStatus(Enum):
    """Lifecycle state of an emotion outbreak."""
    ACTIVE = "active"
    CONTAINED = "contained"
    EXPIRED = "expired"


class ContagionEventKind(Enum):
    """Observable event kind emitted by the emotion contagion engine."""
    EMOTION_EMITTED = "emotion_emitted"
    EMOTION_RECEIVED = "emotion_received"
    MOOD_SHIFTED = "mood_shifted"
    CONTAGION_CHAIN = "contagion_chain"
    SUSCEPTIBILITY_CHANGED = "susceptibility_changed"
    IMMUNITY_GRANTED = "immunity_granted"
    OUTBREAK_DETECTED = "outbreak_detected"
    DECAY_APPLIED = "decay_applied"


# ---------------------------------------------------------------------------
# Data Classes
# ---------------------------------------------------------------------------

@dataclass
class EmotionSignal:
    """An emotion emitted by an agent into the contagion network.

    The signal carries the emotion's valence and intensity in [0, 1]. The
    engine propagates the signal to agents connected to the source,
    attenuating intensity at each hop.
    """
    signal_id: str = field(default_factory=_new_id)
    emotion_name: str = ""
    valence: EmotionValence = EmotionValence.NEUTRAL
    intensity: float = 0.0
    source_agent_id: str = ""
    timestamp: str = field(default_factory=_now)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this signal to a JSON-friendly dictionary."""
        return {
            "signal_id": self.signal_id,
            "emotion_name": self.emotion_name,
            "valence": self.valence.value,
            "intensity": self.intensity,
            "source_agent_id": self.source_agent_id,
            "timestamp": self.timestamp,
            "metadata": dict(self.metadata) if self.metadata else {},
        }


@dataclass
class AgentSusceptibility:
    """Per-agent contagion parameters.

    ``base_susceptibility`` scales how strongly incoming emotions affect
    the agent. ``emotion_immunities`` is the set of emotions the agent is
    immune to. ``emotion_amplifiers`` maps emotion names to multipliers
    applied on top of susceptibility. ``social_resistance`` is the
    minimum received intensity required to shift the agent's mood.
    """
    agent_id: str = ""
    base_susceptibility: float = 0.5
    emotion_immunities: Set[str] = field(default_factory=set)
    emotion_amplifiers: Dict[str, float] = field(default_factory=dict)
    social_resistance: float = 0.0
    created_at: str = field(default_factory=_now)
    updated_at: str = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this susceptibility profile to a JSON-friendly dict."""
        return {
            "agent_id": self.agent_id,
            "base_susceptibility": self.base_susceptibility,
            "emotion_immunities": sorted(self.emotion_immunities),
            "emotion_amplifiers": dict(self.emotion_amplifiers),
            "social_resistance": self.social_resistance,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


@dataclass
class ContagionLink:
    """A directed social connection between two agents.

    Emotions flow from ``source_agent_id`` to ``target_agent_id``. The
    ``connection_strength`` in [0, 1] scales how much of an emotion's
    intensity survives the transmission.
    """
    source_agent_id: str = ""
    target_agent_id: str = ""
    connection_strength: float = 0.5
    last_transmission_at: Optional[str] = None
    transmission_count: int = 0
    created_at: str = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this link to a JSON-friendly dictionary."""
        return {
            "source_agent_id": self.source_agent_id,
            "target_agent_id": self.target_agent_id,
            "connection_strength": self.connection_strength,
            "last_transmission_at": self.last_transmission_at,
            "transmission_count": self.transmission_count,
            "created_at": self.created_at,
        }


@dataclass
class ContagionRecord:
    """A record of an emotion signal reaching a target agent.

    Captures the received intensity (after attenuation), the applied mood
    shift, and the path classification (direct / transitive / chain).
    """
    record_id: str = field(default_factory=_new_id)
    signal: EmotionSignal = field(default_factory=EmotionSignal)
    target_agent_id: str = ""
    received_intensity: float = 0.0
    applied_shift: float = 0.0
    path: ContagionPath = ContagionPath.DIRECT
    timestamp: str = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this record to a JSON-friendly dictionary."""
        return {
            "record_id": self.record_id,
            "signal": self.signal.to_dict(),
            "target_agent_id": self.target_agent_id,
            "received_intensity": self.received_intensity,
            "applied_shift": self.applied_shift,
            "path": self.path.value,
            "timestamp": self.timestamp,
        }


@dataclass
class ContagionChain:
    """A multi-hop propagation path traced from an origin agent.

    A chain is recorded when an emotion reaches 3+ agents. ``path`` is the
    ordered list of agent ids from origin to the furthest recipient.
    ``total_decay`` is the loss in intensity from the origin signal to the
    furthest recipient. ``length`` is the number of agents in the path.
    """
    chain_id: str = field(default_factory=_new_id)
    origin_agent_id: str = ""
    emotion_name: str = ""
    path: List[str] = field(default_factory=list)
    total_decay: float = 0.0
    length: int = 0
    timestamp: str = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this chain to a JSON-friendly dictionary."""
        return {
            "chain_id": self.chain_id,
            "origin_agent_id": self.origin_agent_id,
            "emotion_name": self.emotion_name,
            "path": list(self.path),
            "total_decay": self.total_decay,
            "length": self.length,
            "timestamp": self.timestamp,
        }


@dataclass
class EmotionOutbreak:
    """A detected outbreak of an emotion across multiple agents.

    An outbreak is recorded when 3+ agents are affected by the same
    emotion within ``_OUTBREAK_WINDOW_SECONDS``. Outbreaks move through a
    lifecycle: ACTIVE -> CONTAINED (via ``contain_outbreak``) or
    ACTIVE -> EXPIRED (after ``_OUTBREAK_TTL_SECONDS``).
    """
    outbreak_id: str = field(default_factory=_new_id)
    emotion_name: str = ""
    origin_agent_id: str = ""
    affected_agents: List[str] = field(default_factory=list)
    spread_radius: int = 0
    peak_intensity: float = 0.0
    status: OutbreakStatus = OutbreakStatus.ACTIVE
    started_at: str = field(default_factory=_now)
    ended_at: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this outbreak to a JSON-friendly dictionary."""
        return {
            "outbreak_id": self.outbreak_id,
            "emotion_name": self.emotion_name,
            "origin_agent_id": self.origin_agent_id,
            "affected_agents": list(self.affected_agents),
            "spread_radius": self.spread_radius,
            "peak_intensity": self.peak_intensity,
            "status": self.status.value,
            "started_at": self.started_at,
            "ended_at": self.ended_at,
        }


@dataclass
class ContagionStats:
    """Aggregate statistics about the emotion contagion engine."""
    total_signals: int = 0
    total_transmissions: int = 0
    total_chains: int = 0
    total_outbreaks: int = 0
    avg_reach: float = 0.0
    avg_intensity_loss: float = 0.0
    most_contagious_emotion: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Serialize these statistics to a JSON-friendly dictionary."""
        return {
            "total_signals": self.total_signals,
            "total_transmissions": self.total_transmissions,
            "total_chains": self.total_chains,
            "total_outbreaks": self.total_outbreaks,
            "avg_reach": self.avg_reach,
            "avg_intensity_loss": self.avg_intensity_loss,
            "most_contagious_emotion": self.most_contagious_emotion,
        }


@dataclass
class ContagionEvent:
    """An observable event emitted by the emotion contagion engine."""
    event_id: str = field(default_factory=_new_id)
    kind: ContagionEventKind = ContagionEventKind.EMOTION_EMITTED
    timestamp: str = field(default_factory=_now)
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
class ContagionSnapshot:
    """A point-in-time snapshot of the entire contagion engine state."""
    initialized: bool = False
    agents: List[AgentSusceptibility] = field(default_factory=list)
    links: List[ContagionLink] = field(default_factory=list)
    chains: List[ContagionChain] = field(default_factory=list)
    outbreaks: List[EmotionOutbreak] = field(default_factory=list)
    events: List[ContagionEvent] = field(default_factory=list)
    stats: ContagionStats = field(default_factory=ContagionStats)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this snapshot to a JSON-friendly dictionary."""
        return {
            "initialized": self.initialized,
            "agents": [a.to_dict() for a in self.agents],
            "links": [l.to_dict() for l in self.links],
            "chains": [c.to_dict() for c in self.chains],
            "outbreaks": [o.to_dict() for o in self.outbreaks],
            "events": [e.to_dict() for e in self.events],
            "stats": self.stats.to_dict(),
        }


# ---------------------------------------------------------------------------
# Emotion Contagion Engine (Singleton with double-checked locking)
# ---------------------------------------------------------------------------

class EmotionContagionEngine:
    """Singleton engine that models emotion contagion across agents.

    The engine maintains a population of agents, each with a
    susceptibility profile, connected by directed contagion links. When an
    agent emits an emotion, the engine propagates the resulting signal
    through the network, attenuating intensity at each hop based on
    connection strength, agent susceptibility, and per-emotion
    amplifiers. Multi-hop propagation is tracked as contagion chains, and
    widespread spread is surfaced as emotion outbreaks.

    All public methods are thread-safe, guarded by a reentrant lock.
    In-memory stores are bounded by capacity constants and use FIFO
    eviction.
    """

    _instance: Optional["EmotionContagionEngine"] = None
    _lock: threading.RLock = threading.RLock()

    # ------------------------------------------------------------------
    # Singleton construction (double-checked locking)
    # ------------------------------------------------------------------

    def __new__(cls) -> "EmotionContagionEngine":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    instance = super().__new__(cls)
                    instance._initialized = False
                    cls._instance = instance
        return cls._instance

    @classmethod
    def get_instance(cls) -> "EmotionContagionEngine":
        """Return the singleton EmotionContagionEngine instance.

        Uses double-checked locking so that calls after initialization
        take the fast path without acquiring the lock. Does NOT reset
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

            # Core entity stores keyed by id.
            self._agents: Dict[str, AgentSusceptibility] = {}
            self._links: Dict[str, ContagionLink] = {}
            self._signals: Dict[str, EmotionSignal] = {}
            self._records: Dict[str, ContagionRecord] = {}
            self._chains: Dict[str, ContagionChain] = {}
            self._outbreaks: Dict[str, EmotionOutbreak] = {}

            # Per-agent lookup of received records (target_agent_id -> records).
            self._agent_records: Dict[str, List[ContagionRecord]] = {}

            # Per-agent mood state: agent_id -> {emotion_name: intensity}.
            self._agent_moods: Dict[str, Dict[str, float]] = {}

            # Adjacency cache: source_agent_id -> list of link keys.
            self._outgoing: Dict[str, List[str]] = {}

            # Observable event log (chronological append-only list).
            self._events: List[ContagionEvent] = []

            # Monotonic counters for diagnostics.
            self._signal_counter: int = 0
            self._record_counter: int = 0
            self._chain_counter: int = 0
            self._outbreak_counter: int = 0
            self._event_counter: int = 0
            self._transmission_counter: int = 0

            # Mark initialization complete, then seed baseline data.
            # _seed_data is called at the END of init as required.
            self._initialized: bool = True
            self._seed_data()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _link_key(source_id: str, target_id: str) -> str:
        """Return the composite dict key for a directed link."""
        return f"{source_id}->{target_id}"

    def _ensure_agent(
        self, agent_id: str, base_susceptibility: float = 0.5,
        social_resistance: float = 0.0,
    ) -> AgentSusceptibility:
        """Return the susceptibility profile for an agent, creating if missing.

        Assumes the caller already holds ``self._lock``.
        """
        agent = self._agents.get(agent_id)
        if agent is not None:
            return agent
        now = _now()
        agent = AgentSusceptibility(
            agent_id=agent_id,
            base_susceptibility=_clamp(base_susceptibility, 0.0, 1.0),
            social_resistance=_clamp(social_resistance, 0.0, 1.0),
            created_at=now,
            updated_at=now,
        )
        self._agents[agent_id] = agent
        self._agent_records.setdefault(agent_id, [])
        self._agent_moods.setdefault(agent_id, {})
        self._outgoing.setdefault(agent_id, [])
        _evict_fifo_dict(self._agents, _MAX_AGENTS)
        return agent

    def _is_immune(
        self, agent: AgentSusceptibility, emotion_name: str
    ) -> bool:
        """Return True if the agent is immune to the given emotion."""
        return emotion_name in agent.emotion_immunities

    def _amplifier_for(
        self, agent: AgentSusceptibility, emotion_name: str
    ) -> float:
        """Return the per-emotion amplifier multiplier (default 1.0)."""
        return agent.emotion_amplifiers.get(emotion_name, 1.0)

    def _compute_received_intensity(
        self,
        signal: EmotionSignal,
        link: ContagionLink,
        target: AgentSusceptibility,
    ) -> float:
        """Compute the intensity a target agent receives for a signal.

        ``received = signal.intensity * connection_strength *
        target.base_susceptibility * amplifier``
        """
        amplifier = self._amplifier_for(target, signal.emotion_name)
        received = (
            signal.intensity
            * link.connection_strength
            * target.base_susceptibility
            * amplifier
        )
        return _clamp(received, 0.0, 1.0)

    def _path_classification(self, depth: int) -> ContagionPath:
        """Map a BFS depth to a ContagionPath classification."""
        if depth <= 1:
            return ContagionPath.DIRECT
        if depth == 2:
            return ContagionPath.TRANSITIVE
        return ContagionPath.NETWORK_CHAIN

    def _shift_mood(
        self, agent_id: str, emotion_name: str, shift: float
    ) -> float:
        """Apply a mood shift to an agent and return the new mood intensity.

        Assumes the caller already holds ``self._lock``.
        """
        moods = self._agent_moods.setdefault(agent_id, {})
        current = moods.get(emotion_name, 0.0)
        # Positive-shift emotions accumulate; we cap at 1.0 to keep the
        # mood model bounded.
        new_value = _clamp(current + shift, 0.0, 1.0)
        moods[emotion_name] = new_value
        return new_value

    def _record_event(
        self, kind: ContagionEventKind, payload: Dict[str, Any]
    ) -> None:
        """Record an observable contagion event.

        Assumes the caller already holds ``self._lock``. The event log is
        bounded by ``_MAX_CONTAGION_EVENTS`` with FIFO eviction.
        """
        event = ContagionEvent(
            kind=kind,
            payload=dict(payload) if payload else {},
        )
        self._events.append(event)
        self._event_counter += 1
        _evict_fifo_list(self._events, _MAX_CONTAGION_EVENTS)

    def _ingest_signal(self, signal: EmotionSignal) -> EmotionSignal:
        """Store a constructed signal and emit an EMOTION_EMITTED event.

        Assumes the caller already holds ``self._lock``.
        """
        self._signals[signal.signal_id] = signal
        self._signal_counter += 1
        _evict_fifo_dict(self._signals, _MAX_SIGNALS)
        # The source agent's own mood is set to the emitted intensity so
        # the origin is consistently reflected in mood state.
        self._shift_mood(
            signal.source_agent_id, signal.emotion_name, signal.intensity
        )
        self._record_event(
            ContagionEventKind.EMOTION_EMITTED,
            {
                "signal_id": signal.signal_id,
                "agent_id": signal.source_agent_id,
                "emotion_name": signal.emotion_name,
                "valence": signal.valence.value,
                "intensity": signal.intensity,
            },
        )
        return signal

    def _ingest_record(self, record: ContagionRecord) -> ContagionRecord:
        """Store a contagion record and update derived link/mood state.

        Assumes the caller already holds ``self._lock``.
        """
        self._records[record.record_id] = record
        self._record_counter += 1
        self._transmission_counter += 1
        _evict_fifo_dict(self._records, _MAX_RECORDS)

        # Update the target's per-agent record index.
        bucket = self._agent_records.setdefault(record.target_agent_id, [])
        bucket.append(record)
        _evict_fifo_list(bucket, _MAX_RECORDS)

        # Apply the mood shift and emit the appropriate events.
        new_mood = self._shift_mood(
            record.target_agent_id,
            record.signal.emotion_name,
            record.applied_shift,
        )
        self._record_event(
            ContagionEventKind.EMOTION_RECEIVED,
            {
                "record_id": record.record_id,
                "signal_id": record.signal.signal_id,
                "target_agent_id": record.target_agent_id,
                "received_intensity": record.received_intensity,
                "path": record.path.value,
            },
        )
        self._record_event(
            ContagionEventKind.MOOD_SHIFTED,
            {
                "agent_id": record.target_agent_id,
                "emotion_name": record.signal.emotion_name,
                "applied_shift": record.applied_shift,
                "new_mood": new_mood,
            },
        )
        return record

    def _touch_link(self, source_id: str, target_id: str) -> None:
        """Mark a link as having transmitted an emotion.

        Assumes the caller already holds ``self._lock``.
        """
        key = self._link_key(source_id, target_id)
        link = self._links.get(key)
        if link is not None:
            link.last_transmission_at = _now()
            link.transmission_count += 1

    # ------------------------------------------------------------------
    # Agent susceptibility management
    # ------------------------------------------------------------------

    def register_agent(
        self,
        agent_id: str,
        base_susceptibility: float = 0.5,
        social_resistance: float = 0.0,
    ) -> AgentSusceptibility:
        """Register an agent with a susceptibility profile.

        If the agent is already registered, the existing profile is
        returned unchanged. New agents start with no immunities and no
        amplifiers.

        Args:
            agent_id: Unique identifier of the agent to register.
            base_susceptibility: Susceptibility in [0, 1] (default 0.5).
            social_resistance: Mood-shift threshold in [0, 1] (default 0.0).

        Returns:
            The :class:`AgentSusceptibility` for the agent.
        """
        with self._lock:
            existing = self._agents.get(agent_id)
            if existing is not None:
                return existing
            agent = self._ensure_agent(
                agent_id, base_susceptibility, social_resistance
            )
            self._record_event(
                ContagionEventKind.SUSCEPTIBILITY_CHANGED,
                {
                    "agent_id": agent_id,
                    "base_susceptibility": agent.base_susceptibility,
                    "social_resistance": agent.social_resistance,
                    "registered": True,
                },
            )
            return agent

    def get_agent(self, agent_id: str) -> Optional[AgentSusceptibility]:
        """Return the susceptibility profile for an agent, or None."""
        with self._lock:
            return self._agents.get(agent_id)

    def list_agents(self) -> List[AgentSusceptibility]:
        """Return all registered agent susceptibility profiles."""
        with self._lock:
            return list(self._agents.values())

    def update_susceptibility(
        self, agent_id: str, **kwargs: Any
    ) -> Optional[AgentSusceptibility]:
        """Update one or more fields of an agent's susceptibility profile.

        Recognised keyword arguments:
          - ``base_susceptibility`` (float, clamped to [0, 1])
          - ``social_resistance`` (float, clamped to [0, 1])
          - ``emotion_immunities`` (iterable of emotion names)
          - ``emotion_amplifiers`` (dict emotion -> multiplier)

        Unknown keys are ignored. Returns the updated profile, or ``None``
        if the agent is not registered.
        """
        with self._lock:
            agent = self._agents.get(agent_id)
            if agent is None:
                return None

            if "base_susceptibility" in kwargs:
                agent.base_susceptibility = _clamp(
                    float(kwargs["base_susceptibility"]), 0.0, 1.0
                )
            if "social_resistance" in kwargs:
                agent.social_resistance = _clamp(
                    float(kwargs["social_resistance"]), 0.0, 1.0
                )
            if "emotion_immunities" in kwargs:
                value = kwargs["emotion_immunities"]
                agent.emotion_immunities = set(value) if value else set()
            if "emotion_amplifiers" in kwargs:
                value = kwargs["emotion_amplifiers"]
                agent.emotion_amplifiers = dict(value) if value else {}
            agent.updated_at = _now()

            self._record_event(
                ContagionEventKind.SUSCEPTIBILITY_CHANGED,
                {
                    "agent_id": agent_id,
                    "base_susceptibility": agent.base_susceptibility,
                    "social_resistance": agent.social_resistance,
                    "fields_updated": [
                        k for k in kwargs.keys()
                        if k in {
                            "base_susceptibility", "social_resistance",
                            "emotion_immunities", "emotion_amplifiers",
                        }
                    ],
                },
            )
            return agent

    def grant_immunity(
        self, agent_id: str, emotion_name: str
    ) -> AgentSusceptibility:
        """Make an agent immune to an emotion.

        Immune agents never receive signals of that emotion. The agent is
        registered if it does not already exist.
        """
        with self._lock:
            agent = self._ensure_agent(agent_id)
            agent.emotion_immunities.add(emotion_name)
            agent.updated_at = _now()
            self._record_event(
                ContagionEventKind.IMMUNITY_GRANTED,
                {
                    "agent_id": agent_id,
                    "emotion_name": emotion_name,
                },
            )
            return agent

    def add_amplifier(
        self, agent_id: str, emotion_name: str, multiplier: float
    ) -> AgentSusceptibility:
        """Register an amplifier so an agent magnifies certain emotions.

        The multiplier scales the received intensity for that emotion on
        top of the agent's base susceptibility. The agent is registered
        if it does not already exist.
        """
        with self._lock:
            agent = self._ensure_agent(agent_id)
            agent.emotion_amplifiers[emotion_name] = float(multiplier)
            agent.updated_at = _now()
            self._record_event(
                ContagionEventKind.SUSCEPTIBILITY_CHANGED,
                {
                    "agent_id": agent_id,
                    "emotion_name": emotion_name,
                    "multiplier": float(multiplier),
                    "amplifier_added": True,
                },
            )
            return agent

    # ------------------------------------------------------------------
    # Connection management
    # ------------------------------------------------------------------

    def connect_agents(
        self,
        source_id: str,
        target_id: str,
        connection_strength: float = 0.5,
    ) -> ContagionLink:
        """Create or update a directed contagion link between two agents.

        Both agents are registered if they do not already exist. If a
        link from ``source_id`` to ``target_id`` already exists, its
        connection strength is updated and the existing link is returned.

        Args:
            source_id: The emitting agent.
            target_id: The receiving agent.
            connection_strength: Strength in [0, 1] (default 0.5).

        Returns:
            The :class:`ContagionLink` for the connection.
        """
        with self._lock:
            self._ensure_agent(source_id)
            self._ensure_agent(target_id)
            key = self._link_key(source_id, target_id)
            link = self._links.get(key)
            if link is None:
                link = ContagionLink(
                    source_agent_id=source_id,
                    target_agent_id=target_id,
                    connection_strength=_clamp(connection_strength, 0.0, 1.0),
                )
                self._links[key] = link
                self._outgoing.setdefault(source_id, []).append(key)
                _evict_fifo_dict(self._links, _MAX_LINKS)
            else:
                link.connection_strength = _clamp(
                    connection_strength, 0.0, 1.0
                )
            return link

    def disconnect_agents(
        self, source_id: str, target_id: str
    ) -> bool:
        """Remove the directed link from ``source_id`` to ``target_id``.

        Returns ``True`` if a link was removed, ``False`` otherwise.
        """
        with self._lock:
            key = self._link_key(source_id, target_id)
            link = self._links.pop(key, None)
            if link is None:
                return False
            bucket = self._outgoing.get(source_id, [])
            if key in bucket:
                bucket.remove(key)
            return True

    def list_connections(
        self, agent_id: Optional[str] = None
    ) -> List[ContagionLink]:
        """Return contagion links, optionally filtered by participant.

        When ``agent_id`` is provided, links where the agent is either the
        source or the target are returned. When omitted, all links are
        returned.
        """
        with self._lock:
            if agent_id is None:
                return list(self._links.values())
            results: List[ContagionLink] = []
            for link in self._links.values():
                if (
                    link.source_agent_id == agent_id
                    or link.target_agent_id == agent_id
                ):
                    results.append(link)
            return results

    # ------------------------------------------------------------------
    # Emotion emission and propagation
    # ------------------------------------------------------------------

    def emit_emotion(
        self,
        agent_id: str,
        emotion_name: str,
        valence: EmotionValence,
        intensity: float,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> EmotionSignal:
        """An agent emits an emotion; the engine propagates it.

        Creates an :class:`EmotionSignal`, records it, and propagates it
        through the network via :meth:`propagate_signal`. The source
        agent's mood is set to the emitted intensity.

        Args:
            agent_id: The emitting agent.
            emotion_name: Name of the emotion (e.g. "joy", "anger").
            valence: The :class:`EmotionValence` of the emotion.
            intensity: Emission intensity in [0, 1] (clamped).
            metadata: Optional arbitrary metadata to attach to the signal.

        Returns:
            The newly created :class:`EmotionSignal`.
        """
        with self._lock:
            self._ensure_agent(agent_id)
            signal = EmotionSignal(
                emotion_name=emotion_name,
                valence=valence,
                intensity=_clamp(float(intensity), 0.0, 1.0),
                source_agent_id=agent_id,
                timestamp=_now(),
                metadata=dict(metadata) if metadata else {},
            )
            self._ingest_signal(signal)
            # Propagate the signal through the network.
            self.propagate_signal(signal)
            return signal

    def propagate_signal(
        self, signal: EmotionSignal
    ) -> List[ContagionRecord]:
        """Propagate a signal through the network.

        Performs a breadth-first expansion from the signal's source agent
        over outgoing :class:`ContagionLink` entries. At each hop the
        signal intensity is attenuated by the connection strength, the
        target's susceptibility, and any per-emotion amplifier. Targets
        that are immune or whose received intensity does not exceed their
        ``social_resistance`` are skipped.

        When the emotion reaches 3+ agents, a :class:`ContagionChain` is
        recorded tracing the propagation path. When 3+ agents are
        affected within ``_OUTBREAK_WINDOW_SECONDS``, an
        :class:`EmotionOutbreak` is detected.

        Args:
            signal: The :class:`EmotionSignal` to propagate.

        Returns:
            A list of :class:`ContagionRecord` entries for agents that
            received the signal, in discovery order.
        """
        with self._lock:
            # Ensure the source agent exists so mood state is consistent.
            self._ensure_agent(signal.source_agent_id)

            records: List[ContagionRecord] = []
            # Track the received intensity at each agent to support
            # transitive propagation. The origin starts with the full
            # signal intensity.
            visited: Set[str] = {signal.source_agent_id}
            # BFS frontier of (agent_id, incoming_intensity, depth).
            frontier: List[Tuple[str, float, int]] = [
                (signal.source_agent_id, signal.intensity, 0)
            ]
            # Ordered discovery list for chain construction.
            discovery_path: List[str] = [signal.source_agent_id]
            furthest_intensity = signal.intensity

            while frontier:
                next_frontier: List[Tuple[str, float, int]] = []
                for current_id, incoming, depth in frontier:
                    if depth >= _MAX_PROPAGATION_DEPTH:
                        continue
                    link_keys = self._outgoing.get(current_id, [])
                    for key in link_keys:
                        link = self._links.get(key)
                        if link is None:
                            continue
                        target_id = link.target_agent_id
                        if target_id in visited:
                            continue
                        target = self._agents.get(target_id)
                        if target is None:
                            continue
                        if self._is_immune(target, signal.emotion_name):
                            # Immune agents are skipped entirely; they do
                            # not propagate the emotion further either.
                            visited.add(target_id)
                            continue

                        # Compute the intensity arriving at this target.
                        amplifier = self._amplifier_for(
                            target, signal.emotion_name
                        )
                        received = _clamp(
                            incoming
                            * link.connection_strength
                            * target.base_susceptibility
                            * amplifier,
                            0.0,
                            1.0,
                        )

                        if received <= target.social_resistance:
                            # Signal too weak to shift mood; do not
                            # propagate further from this target.
                            visited.add(target_id)
                            continue

                        record = ContagionRecord(
                            signal=signal,
                            target_agent_id=target_id,
                            received_intensity=received,
                            applied_shift=received,
                            path=self._path_classification(depth + 1),
                            timestamp=_now(),
                        )
                        self._ingest_record(record)
                        self._touch_link(current_id, target_id)
                        records.append(record)
                        visited.add(target_id)
                        discovery_path.append(target_id)
                        furthest_intensity = received
                        next_frontier.append(
                            (target_id, received, depth + 1)
                        )
                frontier = next_frontier

            # Step 4: if the emotion reached 3+ agents, record a chain.
            if len(records) >= 3:
                total_decay = _clamp(
                    signal.intensity - furthest_intensity, 0.0, 1.0
                )
                chain = ContagionChain(
                    origin_agent_id=signal.source_agent_id,
                    emotion_name=signal.emotion_name,
                    path=list(discovery_path),
                    total_decay=round(total_decay, 6),
                    length=len(discovery_path),
                    timestamp=_now(),
                )
                self._chains[chain.chain_id] = chain
                self._chain_counter += 1
                _evict_fifo_dict(self._chains, _MAX_CHAINS)
                self._record_event(
                    ContagionEventKind.CONTAGION_CHAIN,
                    {
                        "chain_id": chain.chain_id,
                        "origin_agent_id": chain.origin_agent_id,
                        "emotion_name": chain.emotion_name,
                        "length": chain.length,
                        "total_decay": chain.total_decay,
                        "path": list(chain.path),
                    },
                )

            # Step 5: if 3+ agents are affected within the time window,
            # detect an outbreak. We check this emission's records plus
            # any recent records for the same emotion.
            if len(records) >= 3:
                self._maybe_detect_outbreak(
                    signal.emotion_name, signal.source_agent_id
                )

            return records

    def get_agent_signals(
        self, agent_id: str, limit: int = 20
    ) -> List[ContagionRecord]:
        """Return emotions this agent received, most recent first.

        Args:
            agent_id: The receiving agent.
            limit: Maximum number of records to return. ``0`` returns an
                empty list.

        Returns:
            A list of :class:`ContagionRecord` entries targeting the
            agent, newest first.
        """
        with self._lock:
            n = max(0, int(limit))
            bucket = self._agent_records.get(agent_id, [])
            if n == 0:
                return []
            return list(reversed(bucket))[:n]

    # ------------------------------------------------------------------
    # Outbreak detection and management
    # ------------------------------------------------------------------

    def _expire_stale_outbreaks(self) -> None:
        """Mark ACTIVE outbreaks older than the TTL as EXPIRED.

        Assumes the caller already holds ``self._lock``.
        """
        now = _now()
        for outbreak in self._outbreaks.values():
            if outbreak.status != OutbreakStatus.ACTIVE:
                continue
            age = _seconds_between(outbreak.started_at, now)
            if age > _OUTBREAK_TTL_SECONDS:
                outbreak.status = OutbreakStatus.EXPIRED
                outbreak.ended_at = now

    def _maybe_detect_outbreak(
        self, emotion_name: str, origin_agent_id: str
    ) -> Optional[EmotionOutbreak]:
        """Detect an outbreak for an emotion based on recent records.

        Considers records created within ``_OUTBREAK_WINDOW_SECONDS``. If
        3+ distinct agents were affected, an :class:`EmotionOutbreak` is
        created (unless one is already ACTIVE for the same emotion).

        Assumes the caller already holds ``self._lock``.
        """
        self._expire_stale_outbreaks()

        # Skip if there is already an active outbreak for this emotion.
        for outbreak in self._outbreaks.values():
            if (
                outbreak.emotion_name == emotion_name
                and outbreak.status == OutbreakStatus.ACTIVE
            ):
                return outbreak

        now = _now()
        affected: Set[str] = set()
        peak = 0.0
        origin = origin_agent_id
        for record in self._records.values():
            if record.signal.emotion_name != emotion_name:
                continue
            if _seconds_between(record.timestamp, now) > _OUTBREAK_WINDOW_SECONDS:
                continue
            affected.add(record.target_agent_id)
            if record.received_intensity > peak:
                peak = record.received_intensity
            if origin == "" or record.signal.source_agent_id:
                origin = record.signal.source_agent_id or origin

        if len(affected) < 3:
            return None

        # Spread radius is the longest chain length for this emotion, or
        # the number of affected agents as a fallback.
        radius = len(affected)
        for chain in self._chains.values():
            if (
                chain.emotion_name == emotion_name
                and chain.length > radius
            ):
                radius = chain.length

        outbreak = EmotionOutbreak(
            emotion_name=emotion_name,
            origin_agent_id=origin,
            affected_agents=sorted(affected),
            spread_radius=radius,
            peak_intensity=round(peak, 6),
            status=OutbreakStatus.ACTIVE,
            started_at=now,
            ended_at=None,
        )
        self._outbreaks[outbreak.outbreak_id] = outbreak
        self._outbreak_counter += 1
        _evict_fifo_dict(self._outbreaks, _MAX_OUTBREAKS)
        self._record_event(
            ContagionEventKind.OUTBREAK_DETECTED,
            {
                "outbreak_id": outbreak.outbreak_id,
                "emotion_name": emotion_name,
                "origin_agent_id": origin,
                "affected_count": len(affected),
                "peak_intensity": outbreak.peak_intensity,
                "spread_radius": outbreak.spread_radius,
            },
        )
        return outbreak

    def detect_outbreak(
        self,
        emotion_name: Optional[str] = None,
        min_affected: int = 3,
    ) -> Optional[EmotionOutbreak]:
        """Detect whether an emotion is spreading to many agents.

        Scans records within ``_OUTBREAK_WINDOW_SECONDS``. If an emotion
        (or any emotion, when ``emotion_name`` is None) has affected at
        least ``min_affected`` agents, an :class:`EmotionOutbreak` is
        recorded and returned.

        Args:
            emotion_name: Restrict detection to this emotion. When
                ``None``, the emotion with the widest recent reach is
                evaluated.
            min_affected: Minimum number of affected agents required to
                declare an outbreak (default 3).

        Returns:
            The detected :class:`EmotionOutbreak`, or ``None`` if no
            outbreak was found.
        """
        with self._lock:
            self._expire_stale_outbreaks()
            now = _now()

            # Build a reach map: emotion -> (set of affected agents,
            # peak intensity, origin).
            reach: Dict[str, Tuple[Set[str], float, str]] = {}
            for record in self._records.values():
                if _seconds_between(record.timestamp, now) > _OUTBREAK_WINDOW_SECONDS:
                    continue
                em = record.signal.emotion_name
                affected_set, peak, origin = reach.get(
                    em, (set(), 0.0, "")
                )
                affected_set.add(record.target_agent_id)
                if record.received_intensity > peak:
                    peak = record.received_intensity
                if not origin and record.signal.source_agent_id:
                    origin = record.signal.source_agent_id
                reach[em] = (affected_set, peak, origin)

            target_emotion = emotion_name
            if target_emotion is None:
                # Pick the emotion with the widest reach.
                best_emotion: Optional[str] = None
                best_count = 0
                for em, (affected_set, _, _) in reach.items():
                    if len(affected_set) > best_count:
                        best_count = len(affected_set)
                        best_emotion = em
                target_emotion = best_emotion

            if target_emotion is None:
                return None

            affected_set, peak, origin = reach.get(
                target_emotion, (set(), 0.0, "")
            )
            if len(affected_set) < min_affected:
                return None

            return self._maybe_detect_outbreak(target_emotion, origin)

    def list_outbreaks(
        self, status: Optional[OutbreakStatus] = None
    ) -> List[EmotionOutbreak]:
        """Return outbreaks, optionally filtered by status."""
        with self._lock:
            results: List[EmotionOutbreak] = []
            for outbreak in self._outbreaks.values():
                if status is not None and outbreak.status != status:
                    continue
                results.append(outbreak)
            return results

    def contain_outbreak(
        self, outbreak_id: str
    ) -> Optional[EmotionOutbreak]:
        """Mark an outbreak as CONTAINED and record its end time.

        Returns the updated outbreak, or ``None`` if not found.
        """
        with self._lock:
            outbreak = self._outbreaks.get(outbreak_id)
            if outbreak is None:
                return None
            outbreak.status = OutbreakStatus.CONTAINED
            outbreak.ended_at = _now()
            self._record_event(
                ContagionEventKind.OUTBREAK_DETECTED,
                {
                    "outbreak_id": outbreak_id,
                    "emotion_name": outbreak.emotion_name,
                    "contained": True,
                },
            )
            return outbreak

    # ------------------------------------------------------------------
    # Decay and reach
    # ------------------------------------------------------------------

    def apply_decay(self, decay_rate: float = 0.05) -> int:
        """Decay all active emotion signal intensities.

        Each signal's intensity is multiplicatively attenuated by
        ``(1 - decay_rate)``. Signals whose intensity falls below
        ``_DECAY_EPSILON`` are pruned. Returns the number of signals that
        were decayed (i.e. had their intensity reduced).

        Args:
            decay_rate: Fraction of intensity to remove in [0, 1]
                (default 0.05).

        Returns:
            The number of signals that received decay.
        """
        with self._lock:
            rate = _clamp(float(decay_rate), 0.0, 1.0)
            decayed = 0
            stale: List[str] = []
            for signal in self._signals.values():
                if signal.intensity <= 0.0:
                    continue
                signal.intensity = _clamp(
                    signal.intensity * (1.0 - rate), 0.0, 1.0
                )
                decayed += 1
                if signal.intensity < _DECAY_EPSILON:
                    stale.append(signal.signal_id)
            for sid in stale:
                self._signals.pop(sid, None)
            self._record_event(
                ContagionEventKind.DECAY_APPLIED,
                {
                    "decay_rate": rate,
                    "decayed_count": decayed,
                    "pruned_count": len(stale),
                },
            )
            return decayed

    def compute_reach(
        self,
        agent_id: str,
        emotion_name: Optional[str] = None,
    ) -> int:
        """Compute how many agents an emotion from this agent would affect.

        Simulates propagation of a unit-intensity signal from the agent
        through the network. Agents that are immune (when ``emotion_name``
        is provided) or whose received intensity would not exceed their
        ``social_resistance`` are not counted.

        Args:
            agent_id: The originating agent.
            emotion_name: When provided, immunities and amplifiers for
                this emotion are considered. When ``None``, a generic
                emotion with no immunities is assumed.

        Returns:
            The number of agents that would be affected.
        """
        with self._lock:
            if agent_id not in self._agents:
                return 0
            visited: Set[str] = {agent_id}
            frontier: List[Tuple[str, float, int]] = [(agent_id, 1.0, 0)]
            affected = 0
            while frontier:
                next_frontier: List[Tuple[str, float, int]] = []
                for current_id, incoming, depth in frontier:
                    if depth >= _MAX_PROPAGATION_DEPTH:
                        continue
                    for key in self._outgoing.get(current_id, []):
                        link = self._links.get(key)
                        if link is None:
                            continue
                        target_id = link.target_agent_id
                        if target_id in visited:
                            continue
                        target = self._agents.get(target_id)
                        if target is None:
                            continue
                        if (
                            emotion_name is not None
                            and self._is_immune(target, emotion_name)
                        ):
                            visited.add(target_id)
                            continue
                        amplifier = (
                            self._amplifier_for(target, emotion_name)
                            if emotion_name is not None
                            else 1.0
                        )
                        received = _clamp(
                            incoming
                            * link.connection_strength
                            * target.base_susceptibility
                            * amplifier,
                            0.0,
                            1.0,
                        )
                        if received <= target.social_resistance:
                            visited.add(target_id)
                            continue
                        affected += 1
                        visited.add(target_id)
                        next_frontier.append(
                            (target_id, received, depth + 1)
                        )
                frontier = next_frontier
            return affected

    # ------------------------------------------------------------------
    # Events, Stats, Status, Snapshot
    # ------------------------------------------------------------------

    def list_events(self, limit: int = 100) -> List[ContagionEvent]:
        """Return the most recent contagion events, newest first."""
        with self._lock:
            n = max(0, int(limit))
            if n == 0:
                return []
            return list(reversed(self._events))[:n]

    def get_stats(self) -> ContagionStats:
        """Compute aggregate statistics over the contagion engine."""
        with self._lock:
            total_signals = len(self._signals)
            total_transmissions = self._transmission_counter
            total_chains = len(self._chains)
            total_outbreaks = len(self._outbreaks)

            # Average reach: mean number of records per signal.
            if self._signal_counter > 0:
                avg_reach = total_transmissions / self._signal_counter
            else:
                avg_reach = 0.0

            # Average intensity loss across chains.
            if total_chains > 0:
                avg_loss = sum(
                    c.total_decay for c in self._chains.values()
                ) / total_chains
            else:
                avg_loss = 0.0

            # Most contagious emotion: the emotion with the most records.
            emotion_counts: Dict[str, int] = {}
            for record in self._records.values():
                em = record.signal.emotion_name
                emotion_counts[em] = emotion_counts.get(em, 0) + 1
            most_contagious = ""
            best_count = 0
            for em, count in emotion_counts.items():
                if count > best_count:
                    best_count = count
                    most_contagious = em

            return ContagionStats(
                total_signals=total_signals,
                total_transmissions=total_transmissions,
                total_chains=total_chains,
                total_outbreaks=total_outbreaks,
                avg_reach=round(avg_reach, 4),
                avg_intensity_loss=round(avg_loss, 4),
                most_contagious_emotion=most_contagious,
            )

    def get_status(self) -> Dict[str, Any]:
        """Return the current operational status of the engine.

        The ``initialized`` flag is always the first key so callers can
        cheaply verify the engine is ready before inspecting counts.
        """
        with self._lock:
            return {
                "initialized": self._initialized,
                "engine_id": id(self),
                "total_agents": len(self._agents),
                "total_links": len(self._links),
                "total_signals": len(self._signals),
                "total_records": len(self._records),
                "total_chains": len(self._chains),
                "total_outbreaks": len(self._outbreaks),
                "total_events": len(self._events),
                "signal_counter": self._signal_counter,
                "record_counter": self._record_counter,
                "chain_counter": self._chain_counter,
                "outbreak_counter": self._outbreak_counter,
                "event_counter": self._event_counter,
                "transmission_counter": self._transmission_counter,
                "capacities": {
                    "max_agents": _MAX_AGENTS,
                    "max_links": _MAX_LINKS,
                    "max_signals": _MAX_SIGNALS,
                    "max_records": _MAX_RECORDS,
                    "max_chains": _MAX_CHAINS,
                    "max_outbreaks": _MAX_OUTBREAKS,
                    "max_events": _MAX_CONTAGION_EVENTS,
                },
                "propagation": {
                    "max_depth": _MAX_PROPAGATION_DEPTH,
                    "outbreak_window_seconds": _OUTBREAK_WINDOW_SECONDS,
                    "outbreak_ttl_seconds": _OUTBREAK_TTL_SECONDS,
                    "decay_epsilon": _DECAY_EPSILON,
                },
            }

    def get_snapshot(self) -> ContagionSnapshot:
        """Capture a point-in-time snapshot of the engine state."""
        with self._lock:
            return ContagionSnapshot(
                initialized=self._initialized,
                agents=list(self._agents.values()),
                links=list(self._links.values()),
                chains=list(self._chains.values()),
                outbreaks=list(self._outbreaks.values()),
                events=list(self._events),
                stats=self.get_stats(),
            )

    # ------------------------------------------------------------------
    # Reset
    # ------------------------------------------------------------------

    def reset(self) -> None:
        """Reset the engine to its initial seeded state."""
        with self._lock:
            self._agents.clear()
            self._links.clear()
            self._signals.clear()
            self._records.clear()
            self._chains.clear()
            self._outbreaks.clear()
            self._agent_records.clear()
            self._agent_moods.clear()
            self._outgoing.clear()
            self._events.clear()
            self._signal_counter = 0
            self._record_counter = 0
            self._chain_counter = 0
            self._outbreak_counter = 0
            self._event_counter = 0
            self._transmission_counter = 0
            self._seed_data()

    # ------------------------------------------------------------------
    # Seed Data
    # ------------------------------------------------------------------

    def _seed_data(self) -> None:
        """Populate the engine with baseline contagion content.

        Seeds four agents (``agent_alpha``, ``agent_beta``, ``agent_gamma``,
        ``agent_delta``) with distinct susceptibilities, grants
        ``agent_beta`` immunity to ``anger``, gives ``agent_gamma`` a 1.5x
        amplifier for ``joy``, connects them with five directed links, and
        emits one initial ``joy`` signal from ``agent_alpha`` whose
        propagation yields one contagion chain.
        """
        now = _now()

        # --- Agents ---------------------------------------------------
        alpha = self._ensure_agent("agent_alpha", 0.7, 0.0)
        beta = self._ensure_agent("agent_beta", 0.4, 0.0)
        gamma = self._ensure_agent("agent_gamma", 0.6, 0.0)
        delta = self._ensure_agent("agent_delta", 0.3, 0.0)

        # agent_beta is immune to "anger".
        beta.emotion_immunities.add("anger")
        beta.updated_at = now
        self._record_event(
            ContagionEventKind.IMMUNITY_GRANTED,
            {"agent_id": "agent_beta", "emotion_name": "anger"},
        )

        # agent_gamma amplifies "joy" by 1.5x.
        gamma.emotion_amplifiers["joy"] = 1.5
        gamma.updated_at = now
        self._record_event(
            ContagionEventKind.SUSCEPTIBILITY_CHANGED,
            {
                "agent_id": "agent_gamma",
                "emotion_name": "joy",
                "multiplier": 1.5,
                "amplifier_added": True,
            },
        )

        # --- Connections ---------------------------------------------
        # alpha -> beta (0.8), alpha -> gamma (0.6), beta -> delta (0.5),
        # gamma -> delta (0.4), delta -> alpha (0.3).
        link_specs = [
            ("agent_alpha", "agent_beta", 0.8),
            ("agent_alpha", "agent_gamma", 0.6),
            ("agent_beta", "agent_delta", 0.5),
            ("agent_gamma", "agent_delta", 0.4),
            ("agent_delta", "agent_alpha", 0.3),
        ]
        for source_id, target_id, strength in link_specs:
            key = self._link_key(source_id, target_id)
            link = ContagionLink(
                source_agent_id=source_id,
                target_agent_id=target_id,
                connection_strength=strength,
                created_at=now,
            )
            self._links[key] = link
            self._outgoing.setdefault(source_id, []).append(key)
        _evict_fifo_dict(self._links, _MAX_LINKS)

        # --- Initial emotion signal: alpha emits "joy" ---------------
        # Build the signal directly so the seed state is deterministic.
        joy_signal = EmotionSignal(
            signal_id="sig_seed_joy_alpha",
            emotion_name="joy",
            valence=EmotionValence.POSITIVE,
            intensity=0.8,
            source_agent_id="agent_alpha",
            timestamp=now,
            metadata={"seed": True},
        )
        self._ingest_signal(joy_signal)

        # Propagate the seed signal manually so the resulting records and
        # chain are deterministic and match the seed specification.
        # Hop 1: alpha -> beta (0.8 * 0.8 * 0.4 = 0.256)
        beta_received = _clamp(
            joy_signal.intensity
            * 0.8  # alpha -> beta connection strength
            * beta.base_susceptibility,
            0.0,
            1.0,
        )
        beta_record = ContagionRecord(
            signal=joy_signal,
            target_agent_id="agent_beta",
            received_intensity=beta_received,
            applied_shift=beta_received,
            path=ContagionPath.DIRECT,
            timestamp=now,
        )
        self._ingest_record(beta_record)
        self._touch_link("agent_alpha", "agent_beta")

        # Hop 1: alpha -> gamma (0.8 * 0.6 * 0.6 * 1.5 = 0.432)
        gamma_received = _clamp(
            joy_signal.intensity
            * 0.6  # alpha -> gamma connection strength
            * gamma.base_susceptibility
            * 1.5,  # joy amplifier
            0.0,
            1.0,
        )
        gamma_record = ContagionRecord(
            signal=joy_signal,
            target_agent_id="agent_gamma",
            received_intensity=gamma_received,
            applied_shift=gamma_received,
            path=ContagionPath.DIRECT,
            timestamp=now,
        )
        self._ingest_record(gamma_record)
        self._touch_link("agent_alpha", "agent_gamma")

        # Hop 2: beta -> delta (0.256 * 0.5 * 0.3 = 0.0384)
        delta_received = _clamp(
            beta_received
            * 0.5  # beta -> delta connection strength
            * delta.base_susceptibility,
            0.0,
            1.0,
        )
        delta_record = ContagionRecord(
            signal=joy_signal,
            target_agent_id="agent_delta",
            received_intensity=delta_received,
            applied_shift=delta_received,
            path=ContagionPath.TRANSITIVE,
            timestamp=now,
        )
        self._ingest_record(delta_record)
        self._touch_link("agent_beta", "agent_delta")

        # --- Contagion chain from the joy signal ---------------------
        # Path: alpha -> beta -> gamma -> delta (3 affected agents).
        total_decay = _clamp(
            joy_signal.intensity - delta_received, 0.0, 1.0
        )
        chain = ContagionChain(
            chain_id="chain_seed_joy_alpha",
            origin_agent_id="agent_alpha",
            emotion_name="joy",
            path=["agent_alpha", "agent_beta", "agent_gamma", "agent_delta"],
            total_decay=round(total_decay, 6),
            length=4,
            timestamp=now,
        )
        self._chains[chain.chain_id] = chain
        self._chain_counter += 1
        _evict_fifo_dict(self._chains, _MAX_CHAINS)
        self._record_event(
            ContagionEventKind.CONTAGION_CHAIN,
            {
                "chain_id": chain.chain_id,
                "origin_agent_id": chain.origin_agent_id,
                "emotion_name": chain.emotion_name,
                "length": chain.length,
                "total_decay": chain.total_decay,
                "path": list(chain.path),
                "seed": True,
            },
        )

        # Enforce capacity bounds after seeding.
        _evict_fifo_dict(self._agents, _MAX_AGENTS)
        _evict_fifo_dict(self._links, _MAX_LINKS)
        _evict_fifo_dict(self._signals, _MAX_SIGNALS)
        _evict_fifo_dict(self._records, _MAX_RECORDS)
        _evict_fifo_dict(self._chains, _MAX_CHAINS)
        _evict_fifo_dict(self._outbreaks, _MAX_OUTBREAKS)
        _evict_fifo_list(self._events, _MAX_CONTAGION_EVENTS)


# ---------------------------------------------------------------------------
# Module-Level Accessor
# ---------------------------------------------------------------------------

def get_emotion_contagion() -> EmotionContagionEngine:
    """Return the singleton EmotionContagionEngine instance."""
    return EmotionContagionEngine.get_instance()
