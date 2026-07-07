"""
SparkLabs Agent - World Anchoring Engine

This module implements a world anchoring engine for AI agents operating
inside the SparkLabs AI-native game engine. World anchoring is the process
of binding abstract symbols, language tokens, and high-level concepts to
concrete world entities (objects, places, agents) and their properties.
This symbol grounding capability is critical for agents that must
communicate with humans and other agents about specific things in the
world.

The world anchoring engine is distinct from (and complementary to) other
SparkLabs agent subsystems:

  * Self-Model tracks what an agent knows about itself.
  * World Model tracks objective world state.
  * Perception Engine ingests low-level sensor data.
  * World Anchoring (this module) bridges language and perception by
    binding symbols to entities, recording references, and resolving
    ambiguities across reference frames.

Core concepts:

  1. Anchors
       An anchor is a binding from a symbol (a word, phrase, or concept)
       to a concrete world entity. Each anchor carries a grounding
       strength that reflects how reliable the binding is.

  2. References
       A reference is a specific occurrence of an entity in a frame or
       scene. The engine stores the per-anchor reference history so the
       agent can later recall when and where an entity was last seen.

  3. Bindings
       A binding is a connection between a symbol and a world reference
       under a particular reference frame (absolute, agent-centric,
       object-centric, or world). The same symbol can have multiple
       bindings across different frames.

  4. History
       Each anchor has a history of strength updates, rebindings, and
       disambiguations so the agent can audit its grounding decisions.

  5. Context
       Context describes the spatial, temporal, and social conditions
       under which a reference or binding applies. The engine uses
       context to disambiguate references when symbols are reused.

  6. Grounding Chains
       A grounding chain links a high-level concept (such as "the
       dragon") through intermediate symbols down to low-level percepts
       (such as raw visual features). Chains are how the agent explains
       its symbol grounding in a layered way.

  7. Disambiguation
       When the same symbol has multiple candidate referents, the
       engine records a disambiguation describing the chosen referent,
       the candidates considered, the strategy used, and the result.

Architecture:
  WorldAnchoringEngine (Singleton, double-checked locking with
  threading.RLock)
    |-- Anchor                 -- a symbol-to-entity binding
    |-- AnchorReference        -- a scene/frame occurrence of an entity
    |-- AnchorBinding          -- a connection between a symbol and a
    |                              world reference under a frame
    |-- AnchorHistory          -- a historical record of an anchor
    |-- AnchorContext          -- spatial/temporal/social context
    |-- GroundingChain         -- a layered chain linking concept to
    |                              percept
    |-- AnchorDisambiguation   -- a resolution record for ambiguous
    |                              symbols
    |-- WorldAnchoring         -- the per-agent world anchoring state
    |-- WorldAnchoringStats    -- aggregate engine statistics
    |-- WorldAnchoringSnapshot -- complete engine state snapshot
    |-- WorldAnchoringEvent    -- observable engine lifecycle event

All public mutating methods are protected by a re-entrant lock so the
engine is safe to call from multiple agent threads. Bounded in-memory
stores use FIFO eviction when their capacity constants are exceeded.
"""

from __future__ import annotations

import datetime
import threading
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Union


# ---------------------------------------------------------------------------
# Capacity constants - bounded in-memory stores with FIFO eviction
# ---------------------------------------------------------------------------

_MAX_AGENTS: int = 500
_MAX_ANCHORS_PER_AGENT: int = 500
_MAX_BINDINGS_PER_ANCHOR: int = 50
_MAX_REFERENCES_PER_ANCHOR: int = 200
_MAX_HISTORY_PER_ANCHOR: int = 200
_MAX_CHAINS_PER_AGENT: int = 100
_MAX_DISAMBIGUATIONS_PER_AGENT: int = 200
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


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class SymbolType(Enum):
    """The category of a linguistic symbol being anchored."""
    WORD = "word"
    PHRASE = "phrase"
    PRONOUN = "pronoun"
    PROPER_NOUN = "proper_noun"
    IDIOM = "idiom"
    METAPHOR = "metaphor"


class EntityType(Enum):
    """The category of a world entity a symbol can refer to."""
    AGENT = "agent"
    OBJECT = "object"
    LOCATION = "location"
    EVENT = "event"
    PROPERTY = "property"
    ABSTRACT = "abstract"


class ReferenceFrame(Enum):
    """The coordinate frame a binding is expressed in."""
    ABSOLUTE = "absolute"
    AGENT_CENTRIC = "agent_centric"
    OBJECT_CENTRIC = "object_centric"
    WORLD = "world"


class GroundingStrength(Enum):
    """How strongly a symbol is bound to its referent."""
    STRONG = "strong"
    MODERATE = "moderate"
    WEAK = "weak"
    AMBIGUOUS = "ambiguous"


class DisambiguationStrategy(Enum):
    """Strategy used to resolve an ambiguous symbol to a referent."""
    CONTEXT = "context"
    RECENCY = "recency"
    SALIENCE = "salience"
    FREQUENCY = "frequency"
    USER = "user"


class WorldAnchoringEventKind(Enum):
    """Observable lifecycle events emitted by the anchoring engine."""
    ANCHOR_REGISTERED = "anchor_registered"
    BINDING_ADDED = "binding_added"
    ANCHOR_RESOLVED = "anchor_resolved"
    ANCHOR_DISAMBIGUATED = "anchor_disambiguated"
    CHAIN_BUILT = "chain_built"
    ANCHOR_UPDATED = "anchor_updated"


# ---------------------------------------------------------------------------
# Data Classes
# ---------------------------------------------------------------------------


@dataclass
class Anchor:
    """A binding from a symbol to a concrete world entity."""
    anchor_id: str
    agent_id: str
    symbol: str
    symbol_type: SymbolType
    entity_id: str
    entity_type: EntityType
    strength: GroundingStrength
    confidence: float
    usage_count: int
    created_at: str
    updated_at: str
    description: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this anchor to a JSON-friendly dictionary."""
        return {
            "anchor_id": self.anchor_id,
            "agent_id": self.agent_id,
            "symbol": self.symbol,
            "symbol_type": self.symbol_type.value,
            "entity_id": self.entity_id,
            "entity_type": self.entity_type.value,
            "strength": self.strength.value,
            "confidence": self.confidence,
            "usage_count": self.usage_count,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "description": self.description,
            "metadata": dict(self.metadata) if self.metadata else {},
        }


@dataclass
class AnchorReference:
    """A reference to an entity in a particular scene or frame."""
    reference_id: str
    anchor_id: str
    agent_id: str
    entity_id: str
    scene_id: str
    position: Dict[str, float]
    frame: ReferenceFrame
    timestamp: str
    context: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this reference to a JSON-friendly dictionary."""
        return {
            "reference_id": self.reference_id,
            "anchor_id": self.anchor_id,
            "agent_id": self.agent_id,
            "entity_id": self.entity_id,
            "scene_id": self.scene_id,
            "position": dict(self.position) if self.position else {},
            "frame": self.frame.value,
            "timestamp": self.timestamp,
            "context": dict(self.context) if self.context else {},
        }


@dataclass
class AnchorBinding:
    """A connection between a symbol and a world reference under a frame."""
    binding_id: str
    anchor_id: str
    agent_id: str
    entity_id: str
    entity_type: EntityType
    frame: ReferenceFrame
    confidence: float
    evidence: List[str]
    created_at: str
    active: bool
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this binding to a JSON-friendly dictionary."""
        return {
            "binding_id": self.binding_id,
            "anchor_id": self.anchor_id,
            "agent_id": self.agent_id,
            "entity_id": self.entity_id,
            "entity_type": self.entity_type.value,
            "frame": self.frame.value,
            "confidence": self.confidence,
            "evidence": list(self.evidence) if self.evidence else [],
            "created_at": self.created_at,
            "active": self.active,
            "metadata": dict(self.metadata) if self.metadata else {},
        }


@dataclass
class AnchorHistory:
    """A historical record describing a change to an anchor."""
    history_id: str
    anchor_id: str
    agent_id: str
    action: str
    description: str
    timestamp: str
    previous_state: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this history record to a JSON-friendly dictionary."""
        return {
            "history_id": self.history_id,
            "anchor_id": self.anchor_id,
            "agent_id": self.agent_id,
            "action": self.action,
            "description": self.description,
            "timestamp": self.timestamp,
            "previous_state": dict(self.previous_state) if self.previous_state else {},
        }


@dataclass
class AnchorContext:
    """Contextual information describing a reference or binding."""
    context_id: str
    agent_id: str
    spatial: Dict[str, Any]
    temporal: Dict[str, Any]
    social: Dict[str, Any]
    notes: str
    timestamp: str

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this context to a JSON-friendly dictionary."""
        return {
            "context_id": self.context_id,
            "agent_id": self.agent_id,
            "spatial": dict(self.spatial) if self.spatial else {},
            "temporal": dict(self.temporal) if self.temporal else {},
            "social": dict(self.social) if self.social else {},
            "notes": self.notes,
            "timestamp": self.timestamp,
        }


@dataclass
class GroundingChain:
    """A chain linking a high-level concept to a low-level percept."""
    chain_id: str
    agent_id: str
    concept: str
    depth: int
    links: List[Dict[str, Any]]
    leaf_anchor_id: Optional[str]
    confidence: float
    created_at: str
    description: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this grounding chain to a JSON-friendly dictionary."""
        return {
            "chain_id": self.chain_id,
            "agent_id": self.agent_id,
            "concept": self.concept,
            "depth": self.depth,
            "links": [dict(link) if isinstance(link, dict) else link for link in self.links],
            "leaf_anchor_id": self.leaf_anchor_id,
            "confidence": self.confidence,
            "created_at": self.created_at,
            "description": self.description,
        }


@dataclass
class AnchorDisambiguation:
    """A resolution record describing how an ambiguous symbol was resolved."""
    disambiguation_id: str
    agent_id: str
    symbol: str
    candidates: List[str]
    chosen_entity_id: Optional[str]
    strategy: DisambiguationStrategy
    resolved: bool
    confidence: float
    reason: str
    timestamp: str

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this disambiguation to a JSON-friendly dictionary."""
        return {
            "disambiguation_id": self.disambiguation_id,
            "agent_id": self.agent_id,
            "symbol": self.symbol,
            "candidates": list(self.candidates) if self.candidates else [],
            "chosen_entity_id": self.chosen_entity_id,
            "strategy": self.strategy.value,
            "resolved": self.resolved,
            "confidence": self.confidence,
            "reason": self.reason,
            "timestamp": self.timestamp,
        }


@dataclass
class WorldAnchoring:
    """The per-agent world anchoring state.

    Aggregates anchors, references, bindings, histories, grounding
    chains, and disambiguations for a single agent together with
    quality scores that summarise how stable the agent's grounding is.
    """
    agent_id: str
    anchors: Dict[str, Anchor]
    references: Dict[str, List[AnchorReference]]
    bindings: Dict[str, List[AnchorBinding]]
    histories: Dict[str, List[AnchorHistory]]
    contexts: List[AnchorContext]
    chains: List[GroundingChain]
    disambiguations: List[AnchorDisambiguation]
    stability: float
    coverage: float
    created_at: str
    updated_at: str

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this world anchoring state to a JSON-friendly dictionary."""
        return {
            "agent_id": self.agent_id,
            "anchors": {k: v.to_dict() for k, v in self.anchors.items()},
            "references": {
                k: [r.to_dict() for r in v]
                for k, v in self.references.items()
            },
            "bindings": {
                k: [b.to_dict() for b in v]
                for k, v in self.bindings.items()
            },
            "histories": {
                k: [h.to_dict() for h in v]
                for k, v in self.histories.items()
            },
            "contexts": [c.to_dict() for c in self.contexts],
            "chains": [c.to_dict() for c in self.chains],
            "disambiguations": [d.to_dict() for d in self.disambiguations],
            "stability": self.stability,
            "coverage": self.coverage,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


@dataclass
class WorldAnchoringStats:
    """Aggregate statistics about the world anchoring engine."""
    total_agents: int
    total_anchors: int
    total_bindings: int
    total_references: int
    total_chains: int
    total_disambiguations: int
    avg_confidence: float
    avg_stability: float
    avg_coverage: float

    def to_dict(self) -> Dict[str, Any]:
        """Serialize these statistics to a JSON-friendly dictionary."""
        return {
            "total_agents": self.total_agents,
            "total_anchors": self.total_anchors,
            "total_bindings": self.total_bindings,
            "total_references": self.total_references,
            "total_chains": self.total_chains,
            "total_disambiguations": self.total_disambiguations,
            "avg_confidence": self.avg_confidence,
            "avg_stability": self.avg_stability,
            "avg_coverage": self.avg_coverage,
        }


@dataclass
class WorldAnchoringSnapshot:
    """A complete snapshot of the world anchoring engine state."""
    initialized: bool
    anchorings: List[WorldAnchoring]
    events: List[WorldAnchoringEvent]
    stats: WorldAnchoringStats

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this snapshot to a JSON-friendly dictionary."""
        return {
            "initialized": self.initialized,
            "anchorings": [a.to_dict() for a in self.anchorings],
            "events": [e.to_dict() for e in self.events],
            "stats": self.stats.to_dict(),
        }


@dataclass
class WorldAnchoringEvent:
    """An observable lifecycle event emitted by the anchoring engine."""
    event_id: str
    kind: WorldAnchoringEventKind
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


# ---------------------------------------------------------------------------
# World Anchoring Engine (Singleton with double-checked locking)
# ---------------------------------------------------------------------------


class WorldAnchoringEngine:
    """World anchoring engine for AI game agents.

    The engine maintains per-agent symbol-to-entity bindings, references,
    bindings, grounding chains, and disambiguations. Other subsystems
    (dialogue, planner, narrative) can read these structures via the
    provided accessors to ground their behaviour in specific things in
    the world.

    It is a thread-safe singleton accessed via :meth:`get_instance` or
    the module-level :func:`get_world_anchoring` helper.

    Usage:
        engine = get_world_anchoring()
        anchor = engine.register_symbol("agent_alpha", "sword",
            SymbolType.WORD)
        engine.bind_to_entity("agent_alpha", anchor.anchor_id,
            "sword_of_dawn", EntityType.OBJECT, ReferenceFrame.WORLD)
        engine.resolve_symbol("agent_alpha", "it", context={...})
    """

    _instance: Optional["WorldAnchoringEngine"] = None
    _lock: threading.RLock = threading.RLock()

    # -- Construction (double-checked locking) ---------------------------

    def __new__(cls) -> "WorldAnchoringEngine":
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

            # Per-agent anchoring state keyed by agent_id.
            self._anchorings: Dict[str, WorldAnchoring] = {}

            # Observable lifecycle events.
            self._events: List[WorldAnchoringEvent] = []

            # Aggregate counters for diagnostics.
            self._anchor_counter: int = 0
            self._binding_counter: int = 0
            self._reference_counter: int = 0
            self._history_counter: int = 0
            self._chain_counter: int = 0
            self._disambiguation_counter: int = 0
            self._context_counter: int = 0
            self._agent_counter: int = 0

            self._initialized: bool = True

            # Seed baseline world anchoring data.
            self._seed_data()

    @classmethod
    def get_instance(cls) -> "WorldAnchoringEngine":
        """Return the singleton WorldAnchoringEngine instance."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    # ------------------------------------------------------------------
    # Internal helpers (must be called with self._lock held)
    # ------------------------------------------------------------------

    def _ensure_anchoring(self, agent_id: str) -> WorldAnchoring:
        """Return the anchoring state for an agent, creating one if missing.

        Assumes the caller already holds ``self._lock``.
        """
        existing = self._anchorings.get(agent_id)
        if existing is not None:
            return existing
        now = _now()
        state = WorldAnchoring(
            agent_id=agent_id,
            anchors={},
            references={},
            bindings={},
            histories={},
            contexts=[],
            chains=[],
            disambiguations=[],
            stability=0.0,
            coverage=0.0,
            created_at=now,
            updated_at=now,
        )
        self._anchorings[agent_id] = state
        self._agent_counter += 1
        _evict_fifo_dict(self._anchorings, _MAX_AGENTS)
        return state

    def _touch(self, state: WorldAnchoring) -> None:
        """Refresh the state's updated_at timestamp.

        Assumes the caller already holds ``self._lock``.
        """
        state.updated_at = _now()

    def _record_event(
        self,
        kind: WorldAnchoringEventKind,
        payload: Dict[str, Any],
    ) -> None:
        """Record an observable world anchoring event.

        Assumes the caller already holds ``self._lock``. The event log is
        bounded by ``_MAX_EVENTS`` with FIFO eviction.
        """
        event = WorldAnchoringEvent(
            event_id=_new_id(),
            kind=kind,
            timestamp=_now(),
            payload=dict(payload) if payload else {},
        )
        self._events.append(event)
        _evict_fifo_list(self._events, _MAX_EVENTS)

    def _append_history(
        self,
        state: WorldAnchoring,
        anchor: Anchor,
        action: str,
        description: str,
        previous_state: Optional[Dict[str, Any]] = None,
    ) -> AnchorHistory:
        """Append a history record to an anchor.

        Assumes the caller already holds ``self._lock``.
        """
        record = AnchorHistory(
            history_id=_new_id(),
            anchor_id=anchor.anchor_id,
            agent_id=anchor.agent_id,
            action=action,
            description=description,
            timestamp=_now(),
            previous_state=dict(previous_state) if previous_state else {},
        )
        bucket = state.histories.setdefault(anchor.anchor_id, [])
        bucket.append(record)
        # Keep history depth bounded per anchor.
        if len(bucket) > _MAX_HISTORY_PER_ANCHOR:
            del bucket[:-_MAX_HISTORY_PER_ANCHOR]
        self._history_counter += 1
        return record

    # ------------------------------------------------------------------
    # Symbol registration
    # ------------------------------------------------------------------

    def register_symbol(
        self,
        agent_id: str,
        symbol: str,
        symbol_type: Union[SymbolType, str] = SymbolType.WORD,
        entity_id: str = "",
        entity_type: Union[EntityType, str] = EntityType.OBJECT,
        strength: Union[GroundingStrength, str] = GroundingStrength.MODERATE,
        confidence: float = 0.5,
        description: str = "",
    ) -> Anchor:
        """Register a new anchor binding a symbol to a world entity.

        Args:
            agent_id: Identifier of the agent registering the anchor.
            symbol: The linguistic symbol being anchored (a word,
                phrase, or proper noun).
            symbol_type: A :class:`SymbolType` enum or its string value.
            entity_id: Identifier of the world entity the symbol refers
                to. May be empty for purely provisional anchors.
            entity_type: A :class:`EntityType` enum or its string value.
            strength: A :class:`GroundingStrength` enum or its string
                value indicating the initial binding strength.
            confidence: Initial confidence in the binding in [0.0, 1.0]
                (clamped).
            description: Optional human-readable description.

        Returns:
            The newly created :class:`Anchor`. If an anchor for the same
            symbol already exists for the agent, the existing anchor is
            updated and returned.
        """
        with self._lock:
            state = self._ensure_anchoring(agent_id)
            resolved_symbol_type = self._coerce_symbol_type(symbol_type)
            resolved_entity_type = self._coerce_entity_type(entity_type)
            resolved_strength = self._coerce_strength(strength)

            # Reuse an existing anchor for the same symbol when present.
            existing = None
            for anchor in state.anchors.values():
                if anchor.symbol == symbol:
                    existing = anchor
                    break
            if existing is not None:
                existing.entity_id = entity_id or existing.entity_id
                existing.entity_type = resolved_entity_type
                existing.strength = resolved_strength
                existing.confidence = _clamp(float(confidence))
                existing.usage_count += 1
                existing.updated_at = _now()
                existing.description = description or existing.description
                self._append_history(
                    state,
                    existing,
                    action="updated",
                    description="Anchor re-registered for existing symbol",
                    previous_state={},
                )
                self._touch(state)
                self._record_event(
                    WorldAnchoringEventKind.ANCHOR_UPDATED,
                    {
                        "agent_id": agent_id,
                        "anchor_id": existing.anchor_id,
                        "symbol": symbol,
                    },
                )
                return existing

            now = _now()
            anchor = Anchor(
                anchor_id=_new_id(),
                agent_id=agent_id,
                symbol=symbol,
                symbol_type=resolved_symbol_type,
                entity_id=entity_id,
                entity_type=resolved_entity_type,
                strength=resolved_strength,
                confidence=_clamp(float(confidence)),
                usage_count=1,
                created_at=now,
                updated_at=now,
                description=description or "",
                metadata={},
            )
            state.anchors[anchor.anchor_id] = anchor
            self._anchor_counter += 1
            _evict_fifo_dict(state.anchors, _MAX_ANCHORS_PER_AGENT)
            state.histories.setdefault(anchor.anchor_id, [])
            state.references.setdefault(anchor.anchor_id, [])
            state.bindings.setdefault(anchor.anchor_id, [])
            self._append_history(
                state,
                anchor,
                action="registered",
                description="Initial anchor registration",
                previous_state={},
            )
            self._touch(state)
            self._record_event(
                WorldAnchoringEventKind.ANCHOR_REGISTERED,
                {
                    "agent_id": agent_id,
                    "anchor_id": anchor.anchor_id,
                    "symbol": symbol,
                    "symbol_type": resolved_symbol_type.value,
                    "entity_id": entity_id,
                    "entity_type": resolved_entity_type.value,
                },
            )
            return anchor

    def _coerce_symbol_type(
        self, value: Union[SymbolType, str]
    ) -> SymbolType:
        """Coerce a value to :class:`SymbolType`, falling back to WORD."""
        if isinstance(value, SymbolType):
            return value
        if isinstance(value, str):
            try:
                return SymbolType(value)
            except ValueError:
                return SymbolType.WORD
        return SymbolType.WORD

    def _coerce_entity_type(
        self, value: Union[EntityType, str]
    ) -> EntityType:
        """Coerce a value to :class:`EntityType`, falling back to OBJECT."""
        if isinstance(value, EntityType):
            return value
        if isinstance(value, str):
            try:
                return EntityType(value)
            except ValueError:
                return EntityType.OBJECT
        return EntityType.OBJECT

    def _coerce_strength(
        self, value: Union[GroundingStrength, str]
    ) -> GroundingStrength:
        """Coerce a value to :class:`GroundingStrength`."""
        if isinstance(value, GroundingStrength):
            return value
        if isinstance(value, str):
            try:
                return GroundingStrength(value)
            except ValueError:
                return GroundingStrength.MODERATE
        return GroundingStrength.MODERATE

    def _coerce_frame(
        self, value: Union[ReferenceFrame, str]
    ) -> ReferenceFrame:
        """Coerce a value to :class:`ReferenceFrame`."""
        if isinstance(value, ReferenceFrame):
            return value
        if isinstance(value, str):
            try:
                return ReferenceFrame(value)
            except ValueError:
                return ReferenceFrame.WORLD
        return ReferenceFrame.WORLD

    def _coerce_strategy(
        self, value: Union[DisambiguationStrategy, str]
    ) -> DisambiguationStrategy:
        """Coerce a value to :class:`DisambiguationStrategy`."""
        if isinstance(value, DisambiguationStrategy):
            return value
        if isinstance(value, str):
            try:
                return DisambiguationStrategy(value)
            except ValueError:
                return DisambiguationStrategy.CONTEXT
        return DisambiguationStrategy.CONTEXT

    # ------------------------------------------------------------------
    # Binding management
    # ------------------------------------------------------------------

    def bind_to_entity(
        self,
        agent_id: str,
        anchor_id: str,
        entity_id: str,
        entity_type: Union[EntityType, str] = EntityType.OBJECT,
        frame: Union[ReferenceFrame, str] = ReferenceFrame.WORLD,
        confidence: float = 0.5,
        evidence: Optional[List[str]] = None,
    ) -> Optional[AnchorBinding]:
        """Bind an anchor to a world entity under a specific reference frame.

        Args:
            agent_id: Identifier of the agent performing the binding.
            anchor_id: Identifier of the anchor to bind.
            entity_id: Identifier of the world entity to bind the anchor
                to.
            entity_type: A :class:`EntityType` enum or its string value
                describing the entity.
            frame: A :class:`ReferenceFrame` enum or its string value
                describing the reference frame of the binding.
            confidence: Binding confidence in [0.0, 1.0] (clamped).
            evidence: Optional list of evidence strings justifying the
                binding.

        Returns:
            The newly created :class:`AnchorBinding`, or ``None`` if the
            agent or anchor is not found.
        """
        with self._lock:
            state = self._anchorings.get(agent_id)
            if state is None:
                return None
            anchor = state.anchors.get(anchor_id)
            if anchor is None:
                return None
            resolved_entity_type = self._coerce_entity_type(entity_type)
            resolved_frame = self._coerce_frame(frame)
            binding = AnchorBinding(
                binding_id=_new_id(),
                anchor_id=anchor_id,
                agent_id=agent_id,
                entity_id=entity_id,
                entity_type=resolved_entity_type,
                frame=resolved_frame,
                confidence=_clamp(float(confidence)),
                evidence=list(evidence) if evidence else [],
                created_at=_now(),
                active=True,
                metadata={},
            )
            bucket = state.bindings.setdefault(anchor_id, [])
            bucket.append(binding)
            if len(bucket) > _MAX_BINDINGS_PER_ANCHOR:
                del bucket[:-_MAX_BINDINGS_PER_ANCHOR]
            # Update the anchor to reflect the binding.
            anchor.entity_id = entity_id
            anchor.entity_type = resolved_entity_type
            anchor.updated_at = _now()
            anchor.usage_count += 1
            self._binding_counter += 1
            self._append_history(
                state,
                anchor,
                action="bound",
                description=(
                    f"Bound to entity {entity_id} in {resolved_frame.value} frame"
                ),
                previous_state={
                    "entity_id": anchor.entity_id,
                    "entity_type": anchor.entity_type.value,
                },
            )
            self._touch(state)
            self._record_event(
                WorldAnchoringEventKind.BINDING_ADDED,
                {
                    "agent_id": agent_id,
                    "anchor_id": anchor_id,
                    "entity_id": entity_id,
                    "entity_type": resolved_entity_type.value,
                    "frame": resolved_frame.value,
                    "confidence": binding.confidence,
                },
            )
            return binding

    def get_bindings(
        self, agent_id: str, anchor_id: str
    ) -> List[AnchorBinding]:
        """Return all bindings for a specific anchor.

        Returns an empty list if the agent or anchor is not found.
        """
        with self._lock:
            state = self._anchorings.get(agent_id)
            if state is None:
                return []
            return list(state.bindings.get(anchor_id, []))

    # ------------------------------------------------------------------
    # Symbol resolution
    # ------------------------------------------------------------------

    def resolve_symbol(
        self,
        agent_id: str,
        symbol: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> AnchorDisambiguation:
        """Resolve a symbol to one of its candidate referents.

        The resolver first looks for an exact anchor matching ``symbol``.
        If exactly one anchor exists, it is returned as the resolved
        referent. If multiple anchors exist, the most recent anchor is
        chosen and a disambiguation record is created describing the
        resolution.

        Args:
            agent_id: Identifier of the agent performing the resolution.
            symbol: The symbol to resolve.
            context: Optional context dictionary used to influence the
                resolution (currently used as a hint for the disambigua-
                tion reason).

        Returns:
            An :class:`AnchorDisambiguation` describing the result. When
            the symbol cannot be resolved the returned record has
            ``resolved=False`` and ``chosen_entity_id=None``.
        """
        with self._lock:
            state = self._anchorings.get(agent_id)
            now = _now()
            if state is None:
                return AnchorDisambiguation(
                    disambiguation_id=_new_id(),
                    agent_id=agent_id,
                    symbol=symbol,
                    candidates=[],
                    chosen_entity_id=None,
                    strategy=DisambiguationStrategy.CONTEXT,
                    resolved=False,
                    confidence=0.0,
                    reason="agent_not_registered",
                    timestamp=now,
                )
            candidates: List[Anchor] = [
                a for a in state.anchors.values() if a.symbol == symbol
            ]
            if not candidates:
                return AnchorDisambiguation(
                    disambiguation_id=_new_id(),
                    agent_id=agent_id,
                    symbol=symbol,
                    candidates=[],
                    chosen_entity_id=None,
                    strategy=DisambiguationStrategy.CONTEXT,
                    resolved=False,
                    confidence=0.0,
                    reason="symbol_unknown",
                    timestamp=now,
                )
            if len(candidates) == 1:
                chosen = candidates[0]
                chosen.usage_count += 1
                chosen.updated_at = now
                self._append_history(
                    state,
                    chosen,
                    action="resolved",
                    description="Symbol resolved unambiguously",
                    previous_state={},
                )
                self._touch(state)
                disambiguation = AnchorDisambiguation(
                    disambiguation_id=_new_id(),
                    agent_id=agent_id,
                    symbol=symbol,
                    candidates=[c.anchor_id for c in candidates],
                    chosen_entity_id=chosen.entity_id,
                    strategy=DisambiguationStrategy.CONTEXT,
                    resolved=True,
                    confidence=chosen.confidence,
                    reason="single_candidate",
                    timestamp=now,
                )
                state.disambiguations.append(disambiguation)
                if (
                    len(state.disambiguations)
                    > _MAX_DISAMBIGUATIONS_PER_AGENT
                ):
                    del state.disambiguations[-_MAX_DISAMBIGUATIONS_PER_AGENT:]
                self._disambiguation_counter += 1
                self._record_event(
                    WorldAnchoringEventKind.ANCHOR_RESOLVED,
                    {
                        "agent_id": agent_id,
                        "symbol": symbol,
                        "entity_id": chosen.entity_id,
                        "anchor_id": chosen.anchor_id,
                    },
                )
                return disambiguation
            # Multiple candidates: pick the most recently updated anchor.
            chosen = max(candidates, key=lambda a: a.updated_at)
            chosen.usage_count += 1
            chosen.updated_at = now
            self._append_history(
                state,
                chosen,
                action="resolved",
                description="Symbol resolved via recency over multiple candidates",
                previous_state={},
            )
            disambiguation = AnchorDisambiguation(
                disambiguation_id=_new_id(),
                agent_id=agent_id,
                symbol=symbol,
                candidates=[c.anchor_id for c in candidates],
                chosen_entity_id=chosen.entity_id,
                strategy=DisambiguationStrategy.RECENCY,
                resolved=True,
                confidence=_clamp(chosen.confidence * 0.8),
                reason="multiple_candidates",
                timestamp=now,
            )
            state.disambiguations.append(disambiguation)
            if (
                len(state.disambiguations)
                > _MAX_DISAMBIGUATIONS_PER_AGENT
            ):
                del state.disambiguations[-_MAX_DISAMBIGUATIONS_PER_AGENT:]
            self._disambiguation_counter += 1
            self._touch(state)
            self._record_event(
                WorldAnchoringEventKind.ANCHOR_DISAMBIGUATED,
                {
                    "agent_id": agent_id,
                    "symbol": symbol,
                    "entity_id": chosen.entity_id,
                    "anchor_id": chosen.anchor_id,
                    "candidate_count": len(candidates),
                    "strategy": DisambiguationStrategy.RECENCY.value,
                },
            )
            return disambiguation

    def disambiguate(
        self,
        agent_id: str,
        symbol: str,
        candidates: List[str],
        strategy: Union[DisambiguationStrategy, str] = DisambiguationStrategy.CONTEXT,
    ) -> AnchorDisambiguation:
        """Explicitly disambiguate a symbol using the given strategy.

        Unlike :meth:`resolve_symbol`, this method requires the caller
        to provide the candidate entity ids directly. The selected
        candidate is the first one whose entity id is in the agent's
        anchor store; if none match, ``chosen_entity_id`` is ``None`` and
        ``resolved`` is ``False``.

        Args:
            agent_id: Identifier of the agent performing the
                disambiguation.
            symbol: The symbol being disambiguated.
            candidates: List of candidate entity ids to consider.
            strategy: A :class:`DisambiguationStrategy` enum or its
                string value.

        Returns:
            An :class:`AnchorDisambiguation` describing the resolution.
        """
        with self._lock:
            state = self._anchorings.get(agent_id)
            now = _now()
            resolved_strategy = self._coerce_strategy(strategy)
            if state is None:
                return AnchorDisambiguation(
                    disambiguation_id=_new_id(),
                    agent_id=agent_id,
                    symbol=symbol,
                    candidates=list(candidates) if candidates else [],
                    chosen_entity_id=None,
                    strategy=resolved_strategy,
                    resolved=False,
                    confidence=0.0,
                    reason="agent_not_registered",
                    timestamp=now,
                )
            chosen_entity_id: Optional[str] = None
            for entity_id in candidates or []:
                for anchor in state.anchors.values():
                    if anchor.entity_id == entity_id:
                        chosen_entity_id = entity_id
                        break
                if chosen_entity_id is not None:
                    break
            resolved = chosen_entity_id is not None
            confidence = 0.7 if resolved else 0.0
            disambiguation = AnchorDisambiguation(
                disambiguation_id=_new_id(),
                agent_id=agent_id,
                symbol=symbol,
                candidates=list(candidates) if candidates else [],
                chosen_entity_id=chosen_entity_id,
                strategy=resolved_strategy,
                resolved=resolved,
                confidence=confidence,
                reason=(
                    "explicit_disambiguation"
                    if resolved
                    else "no_matching_candidate"
                ),
                timestamp=now,
            )
            state.disambiguations.append(disambiguation)
            if (
                len(state.disambiguations)
                > _MAX_DISAMBIGUATIONS_PER_AGENT
            ):
                del state.disambiguations[-_MAX_DISAMBIGUATIONS_PER_AGENT:]
            self._disambiguation_counter += 1
            self._touch(state)
            self._record_event(
                WorldAnchoringEventKind.ANCHOR_DISAMBIGUATED,
                {
                    "agent_id": agent_id,
                    "symbol": symbol,
                    "chosen_entity_id": chosen_entity_id,
                    "candidate_count": len(candidates or []),
                    "strategy": resolved_strategy.value,
                },
            )
            return disambiguation

    # ------------------------------------------------------------------
    # Anchor lookups
    # ------------------------------------------------------------------

    def get_anchor(
        self, agent_id: str, anchor_id: str
    ) -> Optional[Anchor]:
        """Return a single anchor by id, or None if not found."""
        with self._lock:
            state = self._anchorings.get(agent_id)
            if state is None:
                return None
            return state.anchors.get(anchor_id)

    def list_anchors(
        self,
        agent_id: str,
        symbol_type: Optional[Union[SymbolType, str]] = None,
    ) -> List[Anchor]:
        """Return anchors for an agent, optionally filtered by symbol type."""
        with self._lock:
            state = self._anchorings.get(agent_id)
            if state is None:
                return []
            if symbol_type is None:
                return list(state.anchors.values())
            resolved = self._coerce_symbol_type(symbol_type)
            return [
                a for a in state.anchors.values()
                if a.symbol_type == resolved
            ]

    def get_history(
        self, agent_id: str, anchor_id: str
    ) -> List[AnchorHistory]:
        """Return the history records for a specific anchor.

        Returns an empty list if the agent or anchor is not found.
        """
        with self._lock:
            state = self._anchorings.get(agent_id)
            if state is None:
                return []
            return list(state.histories.get(anchor_id, []))

    # ------------------------------------------------------------------
    # Grounding chains
    # ------------------------------------------------------------------

    def build_grounding_chain(
        self,
        agent_id: str,
        concept: str,
        depth: int = 3,
    ) -> GroundingChain:
        """Build a grounding chain linking a concept to leaf anchors.

        The chain is constructed by walking the agent's anchor store
        looking for symbols whose text matches intermediate concept
        levels separated by underscores. For a concept like
        ``"dragon.fire"`` at depth 3, the engine searches for anchors
        whose symbol matches the concept, ``"dragon"``, and
        ``"fire"``.

        Args:
            agent_id: Identifier of the agent building the chain.
            concept: The high-level concept to ground.
            depth: Maximum number of levels (must be >= 1). Values
                greater than 6 are clamped to 6.

        Returns:
            A :class:`GroundingChain` describing the constructed chain.
            The chain's ``leaf_anchor_id`` is the id of the deepest
            matching anchor, or ``None`` when no anchors were found.
        """
        with self._lock:
            state = self._anchorings.get(agent_id)
            now = _now()
            effective_depth = max(1, min(int(depth), 6))
            if state is None or not state.anchors:
                chain = GroundingChain(
                    chain_id=_new_id(),
                    agent_id=agent_id,
                    concept=concept,
                    depth=effective_depth,
                    links=[],
                    leaf_anchor_id=None,
                    confidence=0.0,
                    created_at=now,
                    description="No anchors available for grounding",
                )
                return chain
            levels: List[str] = []
            if effective_depth >= 1:
                levels.append(concept)
            parts = concept.replace(".", "_").split("_")
            for i in range(1, min(effective_depth, len(parts) + 1)):
                levels.append("_".join(parts[:i]))
            links: List[Dict[str, Any]] = []
            leaf_anchor_id: Optional[str] = None
            for level in levels:
                match: Optional[Anchor] = None
                for anchor in state.anchors.values():
                    if anchor.symbol == level:
                        match = anchor
                        break
                if match is not None:
                    links.append(
                        {
                            "level": level,
                            "anchor_id": match.anchor_id,
                            "entity_id": match.entity_id,
                            "confidence": match.confidence,
                        }
                    )
                    leaf_anchor_id = match.anchor_id
            confidence = 0.0
            if links:
                confidence = sum(
                    float(link.get("confidence", 0.0)) for link in links
                ) / len(links)
            chain = GroundingChain(
                chain_id=_new_id(),
                agent_id=agent_id,
                concept=concept,
                depth=effective_depth,
                links=links,
                leaf_anchor_id=leaf_anchor_id,
                confidence=_clamp(round(confidence, 4)),
                created_at=now,
                description=(
                    f"Grounding chain for concept '{concept}' "
                    f"with {len(links)} link(s)"
                ),
            )
            state.chains.append(chain)
            if len(state.chains) > _MAX_CHAINS_PER_AGENT:
                del state.chains[-_MAX_CHAINS_PER_AGENT:]
            self._chain_counter += 1
            self._touch(state)
            self._record_event(
                WorldAnchoringEventKind.CHAIN_BUILT,
                {
                    "agent_id": agent_id,
                    "chain_id": chain.chain_id,
                    "concept": concept,
                    "depth": effective_depth,
                    "link_count": len(links),
                },
            )
            return chain

    # ------------------------------------------------------------------
    # Anchor updates
    # ------------------------------------------------------------------

    def update_anchor_strength(
        self,
        agent_id: str,
        anchor_id: str,
        strength: Union[GroundingStrength, str] = GroundingStrength.MODERATE,
        evidence: str = "",
    ) -> Optional[Anchor]:
        """Update the grounding strength of an anchor.

        Args:
            agent_id: Identifier of the agent whose anchor is updated.
            anchor_id: Identifier of the anchor to update.
            strength: A :class:`GroundingStrength` enum or its string
                value.
            evidence: A short description of the evidence that prompted
                the update.

        Returns:
            The updated :class:`Anchor`, or ``None`` if the agent or
            anchor is not found.
        """
        with self._lock:
            state = self._anchorings.get(agent_id)
            if state is None:
                return None
            anchor = state.anchors.get(anchor_id)
            if anchor is None:
                return None
            previous = {
                "strength": anchor.strength.value,
                "confidence": anchor.confidence,
            }
            resolved = self._coerce_strength(strength)
            anchor.strength = resolved
            # Adjust confidence to align with the new strength.
            target_confidence = {
                GroundingStrength.STRONG: 0.95,
                GroundingStrength.MODERATE: 0.7,
                GroundingStrength.WEAK: 0.4,
                GroundingStrength.AMBIGUOUS: 0.2,
            }.get(resolved, anchor.confidence)
            anchor.confidence = _clamp(target_confidence)
            anchor.updated_at = _now()
            self._append_history(
                state,
                anchor,
                action="strength_updated",
                description=evidence or f"Strength set to {resolved.value}",
                previous_state=previous,
            )
            self._touch(state)
            self._record_event(
                WorldAnchoringEventKind.ANCHOR_UPDATED,
                {
                    "agent_id": agent_id,
                    "anchor_id": anchor_id,
                    "strength": resolved.value,
                    "confidence": anchor.confidence,
                    "evidence": evidence,
                },
            )
            return anchor

    def record_reference(
        self,
        agent_id: str,
        anchor_id: str,
        scene_id: str,
        position: Optional[Dict[str, float]] = None,
        frame: Union[ReferenceFrame, str] = ReferenceFrame.WORLD,
        context: Optional[Dict[str, Any]] = None,
    ) -> Optional[AnchorReference]:
        """Record a scene/frame reference to the entity bound by an anchor.

        Args:
            agent_id: Identifier of the agent recording the reference.
            anchor_id: Identifier of the anchor being referenced.
            scene_id: Identifier of the scene in which the entity was
                observed.
            position: Optional position dictionary (e.g. with ``x``,
                ``y``, ``z`` keys).
            frame: A :class:`ReferenceFrame` enum or its string value
                describing the frame the reference is expressed in.
            context: Optional context dictionary.

        Returns:
            The newly created :class:`AnchorReference`, or ``None`` if
            the agent or anchor is not found.
        """
        with self._lock:
            state = self._anchorings.get(agent_id)
            if state is None:
                return None
            anchor = state.anchors.get(anchor_id)
            if anchor is None:
                return None
            resolved_frame = self._coerce_frame(frame)
            reference = AnchorReference(
                reference_id=_new_id(),
                anchor_id=anchor_id,
                agent_id=agent_id,
                entity_id=anchor.entity_id,
                scene_id=scene_id,
                position=dict(position) if position else {},
                frame=resolved_frame,
                timestamp=_now(),
                context=dict(context) if context else {},
            )
            bucket = state.references.setdefault(anchor_id, [])
            bucket.append(reference)
            if len(bucket) > _MAX_REFERENCES_PER_ANCHOR:
                del bucket[:-_MAX_REFERENCES_PER_ANCHOR]
            anchor.usage_count += 1
            anchor.updated_at = _now()
            self._reference_counter += 1
            self._append_history(
                state,
                anchor,
                action="referenced",
                description=(
                    f"Entity observed in scene {scene_id} "
                    f"({resolved_frame.value} frame)"
                ),
                previous_state={},
            )
            self._touch(state)
            self._record_event(
                WorldAnchoringEventKind.ANCHOR_UPDATED,
                {
                    "agent_id": agent_id,
                    "anchor_id": anchor_id,
                    "scene_id": scene_id,
                    "frame": resolved_frame.value,
                    "reference_id": reference.reference_id,
                },
            )
            return reference

    # ------------------------------------------------------------------
    # Context management
    # ------------------------------------------------------------------

    def add_context(
        self,
        agent_id: str,
        spatial: Optional[Dict[str, Any]] = None,
        temporal: Optional[Dict[str, Any]] = None,
        social: Optional[Dict[str, Any]] = None,
        notes: str = "",
    ) -> Optional[AnchorContext]:
        """Record a context snapshot for an agent.

        Args:
            agent_id: Identifier of the agent.
            spatial: Optional spatial context dictionary.
            temporal: Optional temporal context dictionary.
            social: Optional social context dictionary.
            notes: Optional human-readable notes.

        Returns:
            The newly created :class:`AnchorContext`, or ``None`` if the
            agent is not registered.
        """
        with self._lock:
            state = self._anchorings.get(agent_id)
            if state is None:
                return None
            context = AnchorContext(
                context_id=_new_id(),
                agent_id=agent_id,
                spatial=dict(spatial) if spatial else {},
                temporal=dict(temporal) if temporal else {},
                social=dict(social) if social else {},
                notes=notes or "",
                timestamp=_now(),
            )
            state.contexts.append(context)
            self._context_counter += 1
            self._touch(state)
            return context

    # ------------------------------------------------------------------
    # Events, Stats, Status, Snapshot
    # ------------------------------------------------------------------

    def list_events(self, limit: int = 100) -> List[WorldAnchoringEvent]:
        """Return the most recent world anchoring events, newest first."""
        with self._lock:
            n = max(0, int(limit))
            if n == 0:
                return []
            return list(reversed(self._events))[:n]

    def get_stats(self) -> WorldAnchoringStats:
        """Return aggregate statistics about the world anchoring engine."""
        with self._lock:
            total_anchors = 0
            total_bindings = 0
            total_references = 0
            total_chains = 0
            total_disambiguations = 0
            confidence_sum = 0.0
            confidence_count = 0
            stability_sum = 0.0
            coverage_sum = 0.0
            for state in self._anchorings.values():
                total_anchors += len(state.anchors)
                for bindings in state.bindings.values():
                    total_bindings += len(bindings)
                for references in state.references.values():
                    total_references += len(references)
                total_chains += len(state.chains)
                total_disambiguations += len(state.disambiguations)
                for anchor in state.anchors.values():
                    confidence_sum += anchor.confidence
                    confidence_count += 1
                stability_sum += state.stability
                coverage_sum += state.coverage
            agent_count = len(self._anchorings)
            avg_confidence = (
                confidence_sum / confidence_count if confidence_count else 0.0
            )
            avg_stability = (
                stability_sum / agent_count if agent_count else 0.0
            )
            avg_coverage = (
                coverage_sum / agent_count if agent_count else 0.0
            )
            return WorldAnchoringStats(
                total_agents=agent_count,
                total_anchors=total_anchors,
                total_bindings=total_bindings,
                total_references=total_references,
                total_chains=total_chains,
                total_disambiguations=total_disambiguations,
                avg_confidence=round(avg_confidence, 4),
                avg_stability=round(avg_stability, 4),
                avg_coverage=round(avg_coverage, 4),
            )

    def get_status(self) -> Dict[str, Any]:
        """Return a comprehensive status dictionary for diagnostics.

        The first key in the returned dictionary is always
        ``"initialized"`` mapped to ``self._initialized`` so callers can
        check engine readiness at a glance.
        """
        with self._lock:
            stats = self.get_stats()
            status: Dict[str, Any] = {
                "initialized": self._initialized,
                "total_agents": len(self._anchorings),
                "total_anchors": stats.total_anchors,
                "total_bindings": stats.total_bindings,
                "total_references": stats.total_references,
                "total_chains": stats.total_chains,
                "total_disambiguations": stats.total_disambiguations,
                "total_events": len(self._events),
                "agent_counter": self._agent_counter,
                "anchor_counter": self._anchor_counter,
                "binding_counter": self._binding_counter,
                "reference_counter": self._reference_counter,
                "history_counter": self._history_counter,
                "chain_counter": self._chain_counter,
                "disambiguation_counter": self._disambiguation_counter,
                "context_counter": self._context_counter,
                "avg_confidence": stats.avg_confidence,
                "avg_stability": stats.avg_stability,
                "avg_coverage": stats.avg_coverage,
                "capacities": {
                    "max_agents": _MAX_AGENTS,
                    "max_anchors_per_agent": _MAX_ANCHORS_PER_AGENT,
                    "max_bindings_per_anchor": _MAX_BINDINGS_PER_ANCHOR,
                    "max_references_per_anchor": _MAX_REFERENCES_PER_ANCHOR,
                    "max_history_per_anchor": _MAX_HISTORY_PER_ANCHOR,
                    "max_chains_per_agent": _MAX_CHAINS_PER_AGENT,
                    "max_disambiguations_per_agent": _MAX_DISAMBIGUATIONS_PER_AGENT,
                    "max_events": _MAX_EVENTS,
                },
            }
            return status

    def get_snapshot(self) -> WorldAnchoringSnapshot:
        """Return a complete snapshot of the world anchoring engine state."""
        with self._lock:
            return WorldAnchoringSnapshot(
                initialized=self._initialized,
                anchorings=list(self._anchorings.values()),
                events=list(self._events),
                stats=self.get_stats(),
            )

    # ------------------------------------------------------------------
    # Reset
    # ------------------------------------------------------------------

    def reset(self) -> None:
        """Clear all tracked state and re-seed baseline data.

        Unlike a one-shot clear, ``reset`` re-seeds the baseline
        world anchoring data so the engine returns to a freshly
        initialised state.
        """
        with self._lock:
            self._anchorings.clear()
            self._events.clear()
            self._anchor_counter = 0
            self._binding_counter = 0
            self._reference_counter = 0
            self._history_counter = 0
            self._chain_counter = 0
            self._disambiguation_counter = 0
            self._context_counter = 0
            self._agent_counter = 0
            self._seed_data()

    # ------------------------------------------------------------------
    # Seed data
    # ------------------------------------------------------------------

    def _seed_data(self) -> None:
        """Populate the engine with baseline SparkLabs anchoring data.

        Seeds two agents (``agent_alpha`` -- a warrior tracking physical
        world referents, and ``agent_beta`` -- a mage tracking magical
        and abstract referents) with anchors, bindings, references,
        grounding chains, and disambiguations, providing a useful
        out-of-the-box demo.
        """
        # --- Agent Alpha: the warrior ---------------------------------
        self._ensure_anchoring("agent_alpha")
        sword = self.register_symbol(
            "agent_alpha",
            "sword",
            symbol_type=SymbolType.WORD,
            entity_id="sword_of_dawn",
            entity_type=EntityType.OBJECT,
            strength=GroundingStrength.STRONG,
            confidence=0.9,
            description="The blade carried by the warrior",
        )
        dragon = self.register_symbol(
            "agent_alpha",
            "dragon",
            symbol_type=SymbolType.WORD,
            entity_id="elder_dragon",
            entity_type=EntityType.AGENT,
            strength=GroundingStrength.MODERATE,
            confidence=0.7,
            description="The dragon threatening the kingdom",
        )
        castle = self.register_symbol(
            "agent_alpha",
            "castle",
            symbol_type=SymbolType.WORD,
            entity_id="ironhold_keep",
            entity_type=EntityType.LOCATION,
            strength=GroundingStrength.STRONG,
            confidence=0.85,
            description="The fortified castle on the northern hill",
        )
        battle = self.register_symbol(
            "agent_alpha",
            "the battle",
            symbol_type=SymbolType.PHRASE,
            entity_id="battle_of_dawn",
            entity_type=EntityType.EVENT,
            strength=GroundingStrength.MODERATE,
            confidence=0.65,
            description="The climactic battle at sunrise",
        )
        it_pronoun = self.register_symbol(
            "agent_alpha",
            "it",
            symbol_type=SymbolType.PRONOUN,
            entity_id="sword_of_dawn",
            entity_type=EntityType.OBJECT,
            strength=GroundingStrength.WEAK,
            confidence=0.4,
            description="Pronoun referring to a salient nearby object",
        )

        # Bindings for alpha.
        if sword is not None:
            self.bind_to_entity(
                "agent_alpha",
                sword.anchor_id,
                "sword_of_dawn",
                EntityType.OBJECT,
                ReferenceFrame.OBJECT_CENTRIC,
                confidence=0.95,
                evidence=["visible", "held_by_agent"],
            )
            self.bind_to_entity(
                "agent_alpha",
                sword.anchor_id,
                "sword_of_dawn",
                EntityType.OBJECT,
                ReferenceFrame.WORLD,
                confidence=0.9,
                evidence=["world_position_known"],
            )
        if dragon is not None:
            self.bind_to_entity(
                "agent_alpha",
                dragon.anchor_id,
                "elder_dragon",
                EntityType.AGENT,
                ReferenceFrame.WORLD,
                confidence=0.7,
                evidence=["sighted", "name_known"],
            )
        if castle is not None:
            self.bind_to_entity(
                "agent_alpha",
                castle.anchor_id,
                "ironhold_keep",
                EntityType.LOCATION,
                ReferenceFrame.ABSOLUTE,
                confidence=0.85,
                evidence=["map_marker"],
            )
        if battle is not None:
            self.bind_to_entity(
                "agent_alpha",
                battle.anchor_id,
                "battle_of_dawn",
                EntityType.EVENT,
                ReferenceFrame.WORLD,
                confidence=0.65,
                evidence=["narrative_beat"],
            )

        # References for alpha.
        if sword is not None:
            self.record_reference(
                "agent_alpha",
                sword.anchor_id,
                scene_id="courtyard_dawn",
                position={"x": 12.5, "y": 0.0, "z": 3.2},
                frame=ReferenceFrame.WORLD,
                context={"lighting": "low", "audience": "none"},
            )
        if dragon is not None:
            self.record_reference(
                "agent_alpha",
                dragon.anchor_id,
                scene_id="mountain_pass",
                position={"x": 200.0, "y": 50.0, "z": 0.0},
                frame=ReferenceFrame.WORLD,
                context={"weather": "stormy", "audience": "allies"},
            )
            self.record_reference(
                "agent_alpha",
                dragon.anchor_id,
                scene_id="mountain_pass",
                position={"x": 210.0, "y": 55.0, "z": 0.0},
                frame=ReferenceFrame.AGENT_CENTRIC,
                context={"weather": "stormy", "facing": "north"},
            )
        if castle is not None:
            self.record_reference(
                "agent_alpha",
                castle.anchor_id,
                scene_id="kingdom_overlook",
                position={"x": 0.0, "y": 120.0, "z": 0.0},
                frame=ReferenceFrame.ABSOLUTE,
                context={"view": "distant"},
            )

        # A context snapshot for alpha.
        self.add_context(
            "agent_alpha",
            spatial={"region": "northern_realm", "altitude": "high"},
            temporal={"epoch": "third_age", "phase": "morning"},
            social={"present": ["ally_01", "ally_02"]},
            notes="Alpha is on the march toward the dragon's lair",
        )

        # Build a grounding chain for alpha.
        self.build_grounding_chain("agent_alpha", "dragon", depth=3)
        self.build_grounding_chain("agent_alpha", "sword", depth=2)

        # --- Agent Beta: the mage -------------------------------------
        self._ensure_anchoring("agent_beta")
        spell = self.register_symbol(
            "agent_beta",
            "spell",
            symbol_type=SymbolType.WORD,
            entity_id="arcane_bolt",
            entity_type=EntityType.ABSTRACT,
            strength=GroundingStrength.STRONG,
            confidence=0.9,
            description="A basic offensive spell",
        )
        tome = self.register_symbol(
            "agent_beta",
            "tome",
            symbol_type=SymbolType.WORD,
            entity_id="tome_of_echoes",
            entity_type=EntityType.OBJECT,
            strength=GroundingStrength.MODERATE,
            confidence=0.75,
            description="A magical book of recorded spells",
        )
        tower = self.register_symbol(
            "agent_beta",
            "tower",
            symbol_type=SymbolType.WORD,
            entity_id="ivory_tower",
            entity_type=EntityType.LOCATION,
            strength=GroundingStrength.STRONG,
            confidence=0.85,
            description="The mage's home tower",
        )
        mana = self.register_symbol(
            "agent_beta",
            "mana",
            symbol_type=SymbolType.WORD,
            entity_id="magical_energy",
            entity_type=EntityType.PROPERTY,
            strength=GroundingStrength.MODERATE,
            confidence=0.7,
            description="The magical energy used to cast spells",
        )
        she = self.register_symbol(
            "agent_beta",
            "she",
            symbol_type=SymbolType.PRONOUN,
            entity_id="archmage_lyra",
            entity_type=EntityType.AGENT,
            strength=GroundingStrength.WEAK,
            confidence=0.45,
            description="Pronoun referring to a salient female agent",
        )

        # Bindings for beta.
        if spell is not None:
            self.bind_to_entity(
                "agent_beta",
                spell.anchor_id,
                "arcane_bolt",
                EntityType.ABSTRACT,
                ReferenceFrame.AGENT_CENTRIC,
                confidence=0.9,
                evidence=["frequently_cast"],
            )
        if tome is not None:
            self.bind_to_entity(
                "agent_beta",
                tome.anchor_id,
                "tome_of_echoes",
                EntityType.OBJECT,
                ReferenceFrame.OBJECT_CENTRIC,
                confidence=0.8,
                evidence=["held_by_agent"],
            )
            self.bind_to_entity(
                "agent_beta",
                tome.anchor_id,
                "tome_of_echoes",
                EntityType.OBJECT,
                ReferenceFrame.WORLD,
                confidence=0.75,
                evidence=["on_pedestal"],
            )
        if tower is not None:
            self.bind_to_entity(
                "agent_beta",
                tower.anchor_id,
                "ivory_tower",
                EntityType.LOCATION,
                ReferenceFrame.ABSOLUTE,
                confidence=0.85,
                evidence=["map_marker"],
            )
        if mana is not None:
            self.bind_to_entity(
                "agent_beta",
                mana.anchor_id,
                "magical_energy",
                EntityType.PROPERTY,
                ReferenceFrame.WORLD,
                confidence=0.7,
                evidence=["measurable"],
            )

        # A reference for beta.
        if spell is not None:
            self.record_reference(
                "agent_beta",
                spell.anchor_id,
                scene_id="tower_summit",
                position={"x": 0.0, "y": 5.0, "z": 0.0},
                frame=ReferenceFrame.AGENT_CENTRIC,
                context={"casting": True, "audience": "none"},
            )

        # Build grounding chains for beta.
        self.build_grounding_chain("agent_beta", "spell", depth=3)
        self.build_grounding_chain("agent_beta", "tome", depth=2)

        # A disambiguation for beta to demonstrate the field.
        self.disambiguate(
            "agent_beta",
            symbol="she",
            candidates=["archmage_lyra", "sister_merlin"],
            strategy=DisambiguationStrategy.CONTEXT,
        )

        # --- Quality scores for both agents ---------------------------
        alpha_state = self._anchorings.get("agent_alpha")
        if alpha_state is not None:
            alpha_state.stability = 0.85
            alpha_state.coverage = 0.7
        beta_state = self._anchorings.get("agent_beta")
        if beta_state is not None:
            beta_state.stability = 0.8
            beta_state.coverage = 0.75


# ---------------------------------------------------------------------------
# Module-Level Accessor
# ---------------------------------------------------------------------------


def get_world_anchoring() -> WorldAnchoringEngine:
    """Return the singleton WorldAnchoringEngine instance."""
    return WorldAnchoringEngine.get_instance()
