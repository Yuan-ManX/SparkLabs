"""
SparkLabs Agent - AI Causality Graph Engine

An AI-native causality graph that tracks cause-and-effect relationships
across every event in the game world. The engine builds a directed acyclic
graph (DAG) of causal chains, surfaces butterfly-effect storylines where
small causes cascade into large outcomes, predicts downstream consequences,
and checks narrative consistency across linked event sequences.

Architecture:
  _CausalityGraphEngine (singleton)
    |-- CausalEvent (a single node in the causal DAG)
    |-- CausalLink (a directed edge from a cause to an effect)
    |-- CausalChain (an ordered thread of linked events)
    |-- ButterflyEffect (a small cause with large downstream spread)
    |-- ConsequencePrediction (a forecast of future effects)
    |-- ConsistencyReport (a narrative coherence check result)
    |-- CausalitySnapshot (full state snapshot for persistence)
    |-- CausalityStats (aggregate activity counters)
    |-- CausalityEvent (audit log entry on the engine timeline)

Core Capabilities:
  - register_event / get_event / list_events / remove_event / update_event:
    causal event node lifecycle management across every event category.
  - register_link / get_link / list_links / remove_link / verify_link:
    directed edge management with DAG cycle prevention and verification.
  - register_chain / get_chain / list_chains / remove_chain / extend_chain /
    resolve_chain / get_chain_events / get_chain_summary: causal chain
    threading with status transitions and ordered event linkage.
  - register_butterfly_effect / get_butterfly_effect / list_butterfly_effects /
    remove_butterfly_effect / detect_butterfly_effects: butterfly effect
    tracking with automatic detection of small causes and large effects.
  - trace_causes / trace_effects / find_path / get_root_causes /
    get_terminal_effects / compute_centrality / get_causal_neighborhood:
    graph traversal and structural analysis over the causal DAG.
  - ai_predict_consequences / ai_check_consistency / ai_generate_butterfly /
    ai_suggest_intervention: deterministic AI-driven analysis that forecasts
    outcomes, checks coherence, generates scenarios, and proposes levers.
  - get_consequence_prediction / list_consequence_predictions /
    get_consistency_report / list_consistency_reports: prediction and report
    retrieval.
  - get_status / get_stats / get_snapshot / get_config / set_config /
    list_events_log / tick: observability, tuning, and time progression.

Thread safety:
  All public methods acquire a reentrant instance lock. Singleton creation
  uses module-level double-checked locking with a dedicated init lock so
  re-entrancy during reset cannot double-seed the canonical dataset.
"""

from __future__ import annotations

import threading
import time
import uuid
from collections import deque
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple


# ---------------------------------------------------------------------------
# Capacity Constants
# ---------------------------------------------------------------------------

_MAX_EVENTS: int = 10000
_MAX_LINKS: int = 20000
_MAX_CHAINS: int = 1000
_MAX_BUTTERFLY_EFFECTS: int = 500
_MAX_PREDICTIONS: int = 1000
_MAX_REPORTS: int = 1000
_MAX_EVENTS_LOG: int = 8000
_MAX_TRAVERSAL_DEPTH: int = 32
_MAX_NEIGHBORHOOD_RADIUS: int = 16

# Small epsilon used when comparing timestamps to tolerate float rounding.
_EPSILON: float = 1e-9


# ---------------------------------------------------------------------------
# Knowledge Tables
# ---------------------------------------------------------------------------

# Numeric weight per causal strength. Used when aggregating path confidence
# and when scoring butterfly spread. Higher weight means a stronger causal
# bond between a cause and its effect.
_STRENGTH_WEIGHTS: Dict[str, float] = {
    "direct": 1.0,
    "strong": 0.85,
    "moderate": 0.65,
    "weak": 0.4,
    "tenuous": 0.2,
}

# Ordered list of strengths from strongest to weakest. Used when bumping or
# damping a link strength during verification and intervention analysis.
_STRENGTH_ORDER: List[str] = [
    "direct", "strong", "moderate", "weak", "tenuous",
]

# Numeric magnitude per butterfly impact level. Used when ranking detected
# butterfly effects and when scoring overall narrative disruption.
_IMPACT_MAGNITUDES: Dict[str, int] = {
    "minor": 1,
    "moderate": 2,
    "major": 3,
    "catastrophic": 4,
    "world_altering": 5,
}

# Ordered list of impact levels from smallest to largest.
_IMPACT_ORDER: List[str] = [
    "minor", "moderate", "major", "catastrophic", "world_altering",
]

# Small cause heuristic thresholds. An event counts as a "small cause" when
# its participant count is at or below this limit and it carries no systemic
# or narrative category. Such events are candidates for butterfly detection.
_SMALL_CAUSE_PARTICIPANT_LIMIT: int = 2
_SMALL_CAUSE_CATEGORIES: Set[str] = {"player_action", "environmental"}

# Phrase fragments used by the AI methods to build human-readable predictions,
# consistency notes, and intervention suggestions. Keeping these in tables
# keeps generation deterministic and free of external network calls.
_PREDICTION_VERBS: List[str] = [
    "trigger", "spark", "ignite", "set in motion", "give rise to",
    "precipitate", "unleash", "cultivate", "embolden", "undermine",
]

_PREDICTION_SUBJECTS: List[str] = [
    "a political shift", "a surge of unrest", "a wave of migration",
    "an economic downturn", "a cultural renaissance", "a military buildup",
    "a diplomatic crisis", "a loss of public trust", "a surge in trade",
    "a breakdown of order",
]

_INTERVENTION_LEVERS: List[str] = [
    "divert the cause with a counter-event",
    "weaken the strongest downstream link",
    "introduce a mediating event between cause and effect",
    "redirect the chain toward a less harmful terminal",
    "isolate the root cause from its downstream audience",
    "raise resistance among the affected participants",
]

_CONSISTENCY_RULES: List[Tuple[str, str]] = [
    ("missing_link",
     "Two consecutive chain events have no causal link between them."),
    ("temporal_inversion",
     "An effect is timestamped before its cause."),
    ("orphan_event",
     "A chain event has no incoming or outgoing links at all."),
    ("low_confidence",
     "A link in the chain has confidence below the safe threshold."),
    ("category_mismatch",
     "A narrative event depends directly on a systemic trigger without "
     "a mediating npc_action or environmental event."),
]


# ---------------------------------------------------------------------------
# Helper Functions
# ---------------------------------------------------------------------------


def _now() -> str:
    """Return the current UTC timestamp as an ISO 8601 string."""
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _now_epoch() -> float:
    """Return the current Unix timestamp as a float."""
    return time.time()


def _new_id(prefix: str = "") -> str:
    """Generate a short unique identifier with an optional prefix."""
    base = uuid.uuid4().hex[:12]
    return f"{prefix}_{base}" if prefix else base


def _evict_fifo_dict(store: Dict[str, Any], max_size: int) -> None:
    """Evict the oldest entries from a dict until it fits within max_size."""
    cap = max(1, int(max_size))
    while len(store) > cap:
        oldest_key = next(iter(store), None)
        if oldest_key is None:
            break
        store.pop(oldest_key, None)


def _evict_fifo_list(store: List[Any], max_size: int) -> None:
    """Evict the oldest entries from a list until it fits within max_size."""
    cap = max(1, int(max_size))
    while len(store) > cap:
        if not store:
            break
        store.pop(0)


def _clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    """Clamp a numeric value into the inclusive range [low, high]."""
    try:
        v = float(value)
    except (TypeError, ValueError):
        v = low
    if v < low:
        return low
    if v > high:
        return high
    return v


def _safe_float(value: Any, default: float = 0.0) -> float:
    """Convert a value to float, returning default on failure."""
    if value is None or value == "":
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _safe_int(value: Any, default: int = 0) -> int:
    """Convert a value to int, returning default on failure."""
    if value is None or value == "":
        return default
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _coerce_enum(enum_cls: Any, value: Any, default: Any = None) -> Any:
    """Coerce a raw value into an enum member, falling back to default."""
    if value is None:
        return default
    if isinstance(value, enum_cls):
        return value
    try:
        return enum_cls(value)
    except (ValueError, KeyError):
        return default


def _to_jsonable(value: Any) -> Any:
    """Recursively convert a value into a JSON-serializable form."""
    if value is None:
        return None
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, dict):
        return {str(k): _to_jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_to_jsonable(v) for v in value]
    if hasattr(value, "__dataclass_fields__"):
        return _dataclass_to_dict(value)
    if hasattr(value, "to_dict") and callable(value.to_dict):
        return value.to_dict()
    return value


def _dataclass_to_dict(instance: Any) -> Dict[str, Any]:
    """Serialize a dataclass instance into a plain dict.

    The ``__dataclass_fields__`` attribute is checked BEFORE ``to_dict`` so
    that dataclasses which also expose ``to_dict`` do not recurse through
    their own serializer.
    """
    if instance is None:
        return {}
    if not hasattr(instance, "__dataclass_fields__"):
        if isinstance(instance, dict):
            return {str(k): _to_jsonable(v) for k, v in instance.items()}
        if hasattr(instance, "to_dict") and callable(instance.to_dict):
            return instance.to_dict()
        return {}
    out: Dict[str, Any] = {}
    for name in getattr(instance, "__dataclass_fields__", {}).keys():
        try:
            raw = getattr(instance, name)
        except Exception:
            continue
        out[name] = _to_jsonable(raw)
    return out


def _strength_weight(strength: str) -> float:
    """Return the numeric weight for a causal strength string."""
    return _STRENGTH_WEIGHTS.get(str(strength), 0.5)


def _impact_magnitude(impact: str) -> int:
    """Return the numeric magnitude for a butterfly impact string."""
    return _IMPACT_MAGNITUDES.get(str(impact), 1)


def _parse_timestamp(ts: str) -> float:
    """Parse an ISO 8601 timestamp into epoch seconds, tolerating bad input."""
    if not ts:
        return 0.0
    try:
        clean = ts.replace("Z", "")
        return time.mktime(time.strptime(clean, "%Y-%m-%dT%H:%M:%S"))
    except (ValueError, TypeError):
        return 0.0


def _bump_strength(strength: str, steps: int = 1) -> str:
    """Move a strength string up or down the ordered ladder by N steps."""
    key = str(strength)
    if key not in _STRENGTH_ORDER:
        key = "moderate"
    idx = _STRENGTH_ORDER.index(key)
    new_idx = max(0, min(len(_STRENGTH_ORDER) - 1, idx + int(steps)))
    return _STRENGTH_ORDER[new_idx]


def _bump_impact(impact: str, steps: int = 1) -> str:
    """Move an impact string up or down the ordered ladder by N steps."""
    key = str(impact)
    if key not in _IMPACT_ORDER:
        key = "minor"
    idx = _IMPACT_ORDER.index(key)
    new_idx = max(0, min(len(_IMPACT_ORDER) - 1, idx + int(steps)))
    return _IMPACT_ORDER[new_idx]


# ---------------------------------------------------------------------------
# Domain Enums
# ---------------------------------------------------------------------------


class EventCategory(str, Enum):
    """Top-level classification of a causal event's origin."""
    PLAYER_ACTION = "player_action"
    NPC_ACTION = "npc_action"
    ENVIRONMENTAL = "environmental"
    SYSTEMIC = "systemic"
    NARRATIVE = "narrative"


class CausalStrength(str, Enum):
    """Strength of the causal bond between a cause and its effect."""
    DIRECT = "direct"
    STRONG = "strong"
    MODERATE = "moderate"
    WEAK = "weak"
    TENUOUS = "tenuous"


class ChainStatus(str, Enum):
    """Lifecycle state of a causal chain."""
    ACTIVE = "active"
    RESOLVED = "resolved"
    DORMANT = "dormant"
    BROKEN = "broken"


class ButterflyImpact(str, Enum):
    """Severity of a butterfly effect's downstream disruption."""
    MINOR = "minor"
    MODERATE = "moderate"
    MAJOR = "major"
    CATASTROPHIC = "catastrophic"
    WORLD_ALTERING = "world_altering"


class CausalityEventKind(str, Enum):
    """Audit event kind recorded on the engine timeline."""
    EVENT_REGISTERED = "event_registered"
    EVENT_REMOVED = "event_removed"
    EVENT_UPDATED = "event_updated"
    LINK_REGISTERED = "link_registered"
    LINK_REMOVED = "link_removed"
    LINK_VERIFIED = "link_verified"
    CHAIN_REGISTERED = "chain_registered"
    CHAIN_EXTENDED = "chain_extended"
    CHAIN_RESOLVED = "chain_resolved"
    CHAIN_REMOVED = "chain_removed"
    BUTTERFLY_DETECTED = "butterfly_detected"
    BUTTERFLY_REGISTERED = "butterfly_registered"
    BUTTERFLY_REMOVED = "butterfly_removed"
    PREDICTION_GENERATED = "prediction_generated"
    CONSISTENCY_CHECKED = "consistency_checked"
    CONFIG_CHANGED = "config_changed"
    SYSTEM_RESET = "system_reset"
    TICK = "tick"


# ---------------------------------------------------------------------------
# Data Classes
# ---------------------------------------------------------------------------


@dataclass
class CausalityConfig:
    """Runtime tuning parameters for the causality graph engine."""
    max_events: int = 10000
    max_links: int = 20000
    max_chains: int = 1000
    max_butterfly_effects: int = 500
    max_predictions: int = 1000
    max_reports: int = 1000
    max_events_log: int = 8000
    enable_auto_detection: bool = True
    consistency_check_frequency: int = 100
    prediction_depth: int = 5
    butterfly_threshold: float = 0.3
    safe_confidence_threshold: float = 0.5
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class CausalEvent:
    """A single event node in the causal graph.

    Holds the event identity, its category, a human-readable description,
    the participants involved, arbitrary properties, and the adjacency
    indices (incoming and outgoing link identifiers) that place it in the
    DAG.
    """
    event_id: str
    category: str = "player_action"
    description: str = ""
    timestamp: str = field(default_factory=_now)
    participants: List[str] = field(default_factory=list)
    properties: Dict[str, Any] = field(default_factory=dict)
    incoming_link_ids: List[str] = field(default_factory=list)
    outgoing_link_ids: List[str] = field(default_factory=list)
    chain_ids: List[str] = field(default_factory=list)
    created_at: str = field(default_factory=_now)
    updated_at: str = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class CausalLink:
    """A directed edge from a cause event to an effect event."""
    link_id: str
    cause_event_id: str
    effect_event_id: str
    strength: str = "moderate"
    confidence: float = 0.5
    description: str = ""
    verified: bool = False
    created_at: str = field(default_factory=_now)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class CausalChain:
    """An ordered sequence of linked events forming a narrative thread."""
    chain_id: str
    title: str = ""
    description: str = ""
    event_ids: List[str] = field(default_factory=list)
    link_ids: List[str] = field(default_factory=list)
    status: str = "active"
    created_at: str = field(default_factory=_now)
    updated_at: str = field(default_factory=_now)
    resolved_at: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class ButterflyEffect:
    """A small cause that produced large downstream effects."""
    butterfly_id: str
    root_event_id: str
    impact_level: str = "minor"
    description: str = ""
    terminal_event_ids: List[str] = field(default_factory=list)
    spread_depth: int = 0
    spread_breadth: int = 0
    created_at: str = field(default_factory=_now)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class ConsequencePrediction:
    """A forecast of future effects stemming from a source event."""
    prediction_id: str
    source_event_id: str
    predicted_event_ids: List[str] = field(default_factory=list)
    predicted_descriptions: List[str] = field(default_factory=list)
    depth: int = 3
    confidence: float = 0.5
    created_at: str = field(default_factory=_now)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class ConsistencyReport:
    """Result of a narrative consistency check on a causal chain."""
    report_id: str
    chain_id: str
    is_consistent: bool = True
    score: float = 1.0
    violations: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    notes: List[str] = field(default_factory=list)
    created_at: str = field(default_factory=_now)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class CausalityStats:
    """Aggregate counters describing engine activity."""
    total_events: int = 0
    total_links: int = 0
    total_chains: int = 0
    total_butterfly_effects: int = 0
    total_predictions: int = 0
    total_reports: int = 0
    active_chains: int = 0
    resolved_chains: int = 0
    dormant_chains: int = 0
    broken_chains: int = 0
    verified_links: int = 0
    average_confidence: float = 0.0
    total_butterfly_detected: int = 0
    total_predictions_generated: int = 0
    total_consistency_checks: int = 0
    tick_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class CausalitySnapshot:
    """Full state snapshot for persistence and inspection."""
    timestamp: str = field(default_factory=_now)
    events: List[Dict[str, Any]] = field(default_factory=list)
    links: List[Dict[str, Any]] = field(default_factory=list)
    chains: List[Dict[str, Any]] = field(default_factory=list)
    butterfly_effects: List[Dict[str, Any]] = field(default_factory=list)
    predictions: List[Dict[str, Any]] = field(default_factory=list)
    reports: List[Dict[str, Any]] = field(default_factory=list)
    events_log: List[Dict[str, Any]] = field(default_factory=list)
    stats: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class CausalityEvent:
    """An audit event recorded on the engine timeline."""
    event_id: str
    timestamp: str
    kind: str
    entity_id: str = ""
    description: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


# ---------------------------------------------------------------------------
# Causality Graph Engine Singleton
# ---------------------------------------------------------------------------

# Module-level lock and singleton holder for double-checked locking. The
# factory function get_causality_graph() uses these to guarantee that exactly
# one engine instance is created and seeded even under concurrent first-call
# access from multiple threads.
_LOCK = threading.RLock()
_INSTANCE: Optional["_CausalityGraphEngine"] = None


class _CausalityGraphEngine:
    """
    AI causality graph engine that tracks cause-and-effect relationships
    across all game events as a directed acyclic graph.

    The engine owns the event node registry, the directed link registry, the
    causal chain threads, the butterfly effect catalog, the consequence
    predictions, the consistency reports, and an audit timeline as a single
    coherent state machine. All mutations are guarded by a reentrant instance
    lock so the engine is safe to call from multiple threads.

    Singleton creation uses module-level double-checked locking. Seed
    population is guarded by a dedicated init lock so re-entrancy during
    reset cannot double-seed the canonical dataset. The ``_seeded`` flag
    records whether the seed dataset has been loaded; ``_initialized``
    records whether the engine is ready for use.

    AI methods (ai_predict_consequences, ai_check_consistency,
    ai_generate_butterfly, ai_suggest_intervention) use deterministic logic
    driven by strength weights, impact magnitudes, and traversal results so
    their output is reproducible across runs without external network calls.
    """

    _instance: Optional["_CausalityGraphEngine"] = None
    _init_lock = threading.RLock()

    # ------------------------------------------------------------------
    # Construction and Singleton
    # ------------------------------------------------------------------

    def __init__(self) -> None:
        self._lock = threading.RLock()

        # Core entity stores keyed by id.
        self._events: Dict[str, CausalEvent] = {}
        self._links: Dict[str, CausalLink] = {}
        self._chains: Dict[str, CausalChain] = {}
        self._butterfly_effects: Dict[str, ButterflyEffect] = {}
        self._predictions: Dict[str, ConsequencePrediction] = {}
        self._reports: Dict[str, ConsistencyReport] = {}

        # Adjacency caches for fast traversal. cause_event_id -> link ids
        # for outgoing edges; effect_event_id -> link ids for incoming edges.
        self._outgoing: Dict[str, List[str]] = {}
        self._incoming: Dict[str, List[str]] = {}

        # Audit timeline (chronological append-only list).
        self._events_log: List[CausalityEvent] = []

        # Bookkeeping and configuration.
        self._config = CausalityConfig()
        self._stats = CausalityStats()
        self._tick_count: int = 0

        # Lifecycle flags.
        self._initialized: bool = False
        self._seeded: bool = False

        # Cumulative counters (never decremented by removal).
        self._total_butterfly_detected: int = 0
        self._total_predictions_generated: int = 0
        self._total_consistency_checks: int = 0

    @classmethod
    def get_instance(cls) -> "_CausalityGraphEngine":
        """Return the singleton instance, creating it on first call.

        Uses double-checked locking so that calls after creation take the
        fast path without acquiring the lock.
        """
        if cls._instance is None:
            with cls._init_lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def initialize(self) -> None:
        """Load seed data exactly once. Safe to call repeatedly.

        Guards seeding with the init lock and the ``_seeded`` flag so that
        concurrent first-call access or re-entrancy during reset cannot
        double-seed the canonical dataset.
        """
        with self._init_lock:
            if self._seeded:
                return
            self._seed_data()
            self._seeded = True
            self._initialized = True

    # ------------------------------------------------------------------
    # Internal Helpers
    # ------------------------------------------------------------------

    def _emit(
        self, kind: CausalityEventKind, entity_id: str = "",
        description: str = "",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Append an audit event to the engine timeline.

        Assumes the caller already holds ``self._lock``.
        """
        event = CausalityEvent(
            event_id=_new_id("cevt"),
            timestamp=_now(),
            kind=kind.value,
            entity_id=entity_id,
            description=description,
            metadata=metadata or {},
        )
        self._events_log.append(event)
        _evict_fifo_list(self._events_log, self._config.max_events_log)

    def _refresh_stats(self) -> None:
        """Recompute derived statistics from the current state.

        Assumes the caller already holds ``self._lock``.
        """
        self._stats.total_events = len(self._events)
        self._stats.total_links = len(self._links)
        self._stats.total_chains = len(self._chains)
        self._stats.total_butterfly_effects = len(self._butterfly_effects)
        self._stats.total_predictions = len(self._predictions)
        self._stats.total_reports = len(self._reports)
        self._stats.active_chains = sum(
            1 for c in self._chains.values()
            if c.status == ChainStatus.ACTIVE.value
        )
        self._stats.resolved_chains = sum(
            1 for c in self._chains.values()
            if c.status == ChainStatus.RESOLVED.value
        )
        self._stats.dormant_chains = sum(
            1 for c in self._chains.values()
            if c.status == ChainStatus.DORMANT.value
        )
        self._stats.broken_chains = sum(
            1 for c in self._chains.values()
            if c.status == ChainStatus.BROKEN.value
        )
        self._stats.verified_links = sum(
            1 for lk in self._links.values() if lk.verified
        )
        if self._links:
            self._stats.average_confidence = round(
                sum(lk.confidence for lk in self._links.values())
                / len(self._links),
                4,
            )
        else:
            self._stats.average_confidence = 0.0
        self._stats.total_butterfly_detected = self._total_butterfly_detected
        self._stats.total_predictions_generated = (
            self._total_predictions_generated
        )
        self._stats.total_consistency_checks = (
            self._total_consistency_checks
        )
        self._stats.tick_count = self._tick_count

    def _index_link(self, link: CausalLink) -> None:
        """Register a link in the adjacency caches.

        Assumes the caller already holds ``self._lock``.
        """
        self._outgoing.setdefault(link.cause_event_id, []).append(
            link.link_id
        )
        self._incoming.setdefault(link.effect_event_id, []).append(
            link.link_id
        )

    def _unindex_link(self, link: CausalLink) -> None:
        """Remove a link from the adjacency caches.

        Assumes the caller already holds ``self._lock``.
        """
        out_list = self._outgoing.get(link.cause_event_id)
        if out_list is not None:
            if link.link_id in out_list:
                out_list.remove(link.link_id)
            if not out_list:
                self._outgoing.pop(link.cause_event_id, None)
        in_list = self._incoming.get(link.effect_event_id)
        if in_list is not None:
            if link.link_id in in_list:
                in_list.remove(link.link_id)
            if not in_list:
                self._incoming.pop(link.effect_event_id, None)

    def _effect_ids_for(self, cause_event_id: str) -> List[str]:
        """Return the effect event ids directly downstream of a cause.

        Assumes the caller already holds ``self._lock``.
        """
        result: List[str] = []
        for link_id in self._outgoing.get(cause_event_id, []):
            link = self._links.get(link_id)
            if link is not None:
                result.append(link.effect_event_id)
        return result

    def _cause_ids_for(self, effect_event_id: str) -> List[str]:
        """Return the cause event ids directly upstream of an effect.

        Assumes the caller already holds ``self._lock``.
        """
        result: List[str] = []
        for link_id in self._incoming.get(effect_event_id, []):
            link = self._links.get(link_id)
            if link is not None:
                result.append(link.cause_event_id)
        return result

    def _would_create_cycle(
        self, cause_event_id: str, effect_event_id: str
    ) -> bool:
        """Return True if linking cause -> effect would form a cycle.

        A cycle forms when the effect can already reach the cause by
        following existing outgoing edges. This preserves the DAG invariant.

        Assumes the caller already holds ``self._lock``.
        """
        if cause_event_id == effect_event_id:
            return True
        visited: Set[str] = set()
        queue: deque = deque([effect_event_id])
        while queue:
            current = queue.popleft()
            if current in visited:
                continue
            visited.add(current)
            if current == cause_event_id:
                return True
            for next_id in self._effect_ids_for(current):
                if next_id not in visited:
                    queue.append(next_id)
        return False

    def _bfs_forward(
        self, start_event_id: str, max_depth: int
    ) -> List[Tuple[str, int, float]]:
        """Breadth-first traversal downstream from a start event.

        Returns a list of (event_id, depth, path_confidence) tuples where
        path_confidence is the product of link confidences along the
        shortest path from the start.

        Assumes the caller already holds ``self._lock``.
        """
        depth = max(0, min(int(max_depth), _MAX_TRAVERSAL_DEPTH))
        visited: Dict[str, Tuple[int, float]] = {start_event_id: (0, 1.0)}
        queue: deque = deque([(start_event_id, 0, 1.0)])
        results: List[Tuple[str, int, float]] = [(start_event_id, 0, 1.0)]
        while queue:
            current, cur_depth, cur_conf = queue.popleft()
            if cur_depth >= depth:
                continue
            for link_id in self._outgoing.get(current, []):
                link = self._links.get(link_id)
                if link is None:
                    continue
                nxt = link.effect_event_id
                new_conf = cur_conf * _clamp(link.confidence, 0.0, 1.0)
                prev = visited.get(nxt)
                if prev is None:
                    visited[nxt] = (cur_depth + 1, new_conf)
                    results.append((nxt, cur_depth + 1, new_conf))
                    queue.append((nxt, cur_depth + 1, new_conf))
        return results

    def _bfs_backward(
        self, start_event_id: str, max_depth: int
    ) -> List[Tuple[str, int, float]]:
        """Breadth-first traversal upstream from a start event.

        Returns a list of (event_id, depth, path_confidence) tuples where
        path_confidence is the product of link confidences along the
        shortest path from the start backward to each cause.

        Assumes the caller already holds ``self._lock``.
        """
        depth = max(0, min(int(max_depth), _MAX_TRAVERSAL_DEPTH))
        visited: Dict[str, Tuple[int, float]] = {start_event_id: (0, 1.0)}
        queue: deque = deque([(start_event_id, 0, 1.0)])
        results: List[Tuple[str, int, float]] = [(start_event_id, 0, 1.0)]
        while queue:
            current, cur_depth, cur_conf = queue.popleft()
            if cur_depth >= depth:
                continue
            for link_id in self._incoming.get(current, []):
                link = self._links.get(link_id)
                if link is None:
                    continue
                prv = link.cause_event_id
                new_conf = cur_conf * _clamp(link.confidence, 0.0, 1.0)
                if prv not in visited:
                    visited[prv] = (cur_depth + 1, new_conf)
                    results.append((prv, cur_depth + 1, new_conf))
                    queue.append((prv, cur_depth + 1, new_conf))
        return results

    def _is_small_cause(self, event: CausalEvent) -> bool:
        """Heuristic: is this event a small-cause candidate?

        A small cause has few participants and a player_action or
        environmental category, making it a plausible seed for a butterfly
        effect when its downstream spread is large.

        Assumes the caller already holds ``self._lock``.
        """
        if event.category not in _SMALL_CAUSE_CATEGORIES:
            return False
        return len(event.participants) <= _SMALL_CAUSE_PARTICIPANT_LIMIT

    # ------------------------------------------------------------------
    # Event Management
    # ------------------------------------------------------------------

    def register_event(
        self,
        event_id: str,
        category: str = "player_action",
        description: str = "",
        participants: Optional[List[str]] = None,
        properties: Optional[Dict[str, Any]] = None,
    ) -> Tuple[bool, str, Optional[CausalEvent]]:
        """Register a new causal event node in the graph.

        Returns (success, reason, event). Fails if the id is empty, the
        category is invalid, an event with the same id already exists, or
        the event capacity has been reached.
        """
        with self._lock:
            if not event_id:
                return False, "empty_event_id", None
            cat_enum = _coerce_enum(EventCategory, category)
            if cat_enum is None:
                return False, "invalid_category", None
            if event_id in self._events:
                return False, "event_exists", None
            if len(self._events) >= self._config.max_events:
                return False, "events_capacity", None
            now = _now()
            event = CausalEvent(
                event_id=event_id,
                category=cat_enum.value,
                description=str(description),
                timestamp=now,
                participants=list(participants or []),
                properties=dict(properties or {}),
                created_at=now,
                updated_at=now,
            )
            self._events[event_id] = event
            self._outgoing.setdefault(event_id, [])
            self._incoming.setdefault(event_id, [])
            _evict_fifo_dict(self._events, self._config.max_events)
            self._emit(
                CausalityEventKind.EVENT_REGISTERED,
                entity_id=event_id,
                description=f"Event registered: {event_id}",
                metadata={"category": cat_enum.value},
            )
            return True, "registered", event

    def get_event(self, event_id: str) -> Optional[CausalEvent]:
        """Return the causal event with the given id, or None."""
        with self._lock:
            return self._events.get(event_id)

    def list_events(
        self,
        category: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """List causal events, optionally filtered by category.

        Results are returned newest-first by insertion order. When limit is
        provided, at most that many events are returned.
        """
        with self._lock:
            cat_value: Optional[str] = None
            if category is not None:
                cat_enum = _coerce_enum(EventCategory, category)
                cat_value = cat_enum.value if cat_enum is not None else None
            items = list(self._events.values())
            if cat_value is not None:
                items = [e for e in items if e.category == cat_value]
            items = list(reversed(items))
            if limit is not None:
                lim = max(0, _safe_int(limit, 0))
                items = items[:lim]
            return [e.to_dict() for e in items]

    def remove_event(self, event_id: str) -> Tuple[bool, str, Optional[str]]:
        """Remove an event and every link that touches it.

        Chains that contained the event have the event id dropped; a chain
        that becomes empty is marked broken. Returns (success, reason,
        removed_event_id).
        """
        with self._lock:
            event = self._events.get(event_id)
            if event is None:
                return False, "not_found", None
            # Remove every link that touches this event.
            affected_link_ids: List[str] = []
            for link_id in list(event.incoming_link_ids):
                affected_link_ids.append(link_id)
            for link_id in list(event.outgoing_link_ids):
                if link_id not in affected_link_ids:
                    affected_link_ids.append(link_id)
            for link_id in affected_link_ids:
                self._remove_link_internal(link_id)
            # Detach from chains.
            for chain in self._chains.values():
                if event_id in chain.event_ids:
                    chain.event_ids = [
                        eid for eid in chain.event_ids if eid != event_id
                    ]
                    chain.link_ids = [
                        lid for lid in chain.link_ids
                        if lid not in affected_link_ids
                    ]
                    chain.updated_at = _now()
                    if not chain.event_ids:
                        chain.status = ChainStatus.BROKEN.value
            self._events.pop(event_id, None)
            self._outgoing.pop(event_id, None)
            self._incoming.pop(event_id, None)
            self._emit(
                CausalityEventKind.EVENT_REMOVED,
                entity_id=event_id,
                description=f"Event removed: {event_id}",
                metadata={"removed_links": len(affected_link_ids)},
            )
            return True, "removed", event_id

    def update_event(
        self,
        event_id: str,
        description: Optional[str] = None,
        properties: Optional[Dict[str, Any]] = None,
    ) -> Tuple[bool, str, Optional[CausalEvent]]:
        """Update the description and/or properties of an event.

        Returns (success, reason, updated_event). At least one field must be
        provided.
        """
        with self._lock:
            event = self._events.get(event_id)
            if event is None:
                return False, "not_found", None
            if description is None and properties is None:
                return False, "no_updates", event
            if description is not None:
                event.description = str(description)
            if properties is not None:
                event.properties.update(dict(properties))
            event.updated_at = _now()
            self._emit(
                CausalityEventKind.EVENT_UPDATED,
                entity_id=event_id,
                description=f"Event updated: {event_id}",
            )
            return True, "updated", event

    # ------------------------------------------------------------------
    # Causal Link Management
    # ------------------------------------------------------------------

    def register_link(
        self,
        link_id: str,
        cause_event_id: str,
        effect_event_id: str,
        strength: str = "moderate",
        confidence: float = 0.5,
        description: str = "",
    ) -> Tuple[bool, str, Optional[CausalLink]]:
        """Register a directed causal link from cause to effect.

        Preserves the DAG invariant by rejecting links that would create a
        cycle. Returns (success, reason, link).
        """
        with self._lock:
            if not link_id:
                return False, "empty_link_id", None
            if link_id in self._links:
                return False, "link_exists", None
            if cause_event_id not in self._events:
                return False, "unknown_cause", None
            if effect_event_id not in self._events:
                return False, "unknown_effect", None
            if cause_event_id == effect_event_id:
                return False, "self_link", None
            if len(self._links) >= self._config.max_links:
                return False, "links_capacity", None
            strength_enum = _coerce_enum(
                CausalStrength, strength, CausalStrength.MODERATE
            )
            if strength_enum is None:
                return False, "invalid_strength", None
            if self._would_create_cycle(cause_event_id, effect_event_id):
                return False, "cycle_detected", None
            link = CausalLink(
                link_id=link_id,
                cause_event_id=cause_event_id,
                effect_event_id=effect_event_id,
                strength=strength_enum.value,
                confidence=_clamp(confidence, 0.0, 1.0),
                description=str(description),
                verified=False,
            )
            self._links[link_id] = link
            self._index_link(link)
            cause_event = self._events[cause_event_id]
            effect_event = self._events[effect_event_id]
            if link_id not in cause_event.outgoing_link_ids:
                cause_event.outgoing_link_ids.append(link_id)
            if link_id not in effect_event.incoming_link_ids:
                effect_event.incoming_link_ids.append(link_id)
            cause_event.updated_at = _now()
            effect_event.updated_at = _now()
            _evict_fifo_dict(self._links, self._config.max_links)
            self._emit(
                CausalityEventKind.LINK_REGISTERED,
                entity_id=link_id,
                description=f"Link registered: {cause_event_id} -> "
                            f"{effect_event_id}",
                metadata={
                    "cause": cause_event_id,
                    "effect": effect_event_id,
                    "strength": strength_enum.value,
                },
            )
            return True, "registered", link

    def get_link(self, link_id: str) -> Optional[CausalLink]:
        """Return the causal link with the given id, or None."""
        with self._lock:
            return self._links.get(link_id)

    def list_links(
        self, strength: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """List causal links, optionally filtered by strength."""
        with self._lock:
            strength_value: Optional[str] = None
            if strength is not None:
                strength_enum = _coerce_enum(CausalStrength, strength)
                if strength_enum is not None:
                    strength_value = strength_enum.value
                else:
                    strength_value = str(strength)
            items = list(self._links.values())
            if strength_value is not None:
                items = [lk for lk in items if lk.strength == strength_value]
            return [lk.to_dict() for lk in items]

    def remove_link(self, link_id: str) -> Tuple[bool, str, Optional[str]]:
        """Remove a causal link from the graph.

        Returns (success, reason, removed_link_id).
        """
        with self._lock:
            if link_id not in self._links:
                return False, "not_found", None
            self._remove_link_internal(link_id)
            self._emit(
                CausalityEventKind.LINK_REMOVED,
                entity_id=link_id,
                description=f"Link removed: {link_id}",
            )
            return True, "removed", link_id

    def _remove_link_internal(self, link_id: str) -> None:
        """Remove a link and detach it from events and chains.

        Assumes the caller already holds ``self._lock``.
        """
        link = self._links.get(link_id)
        if link is None:
            return
        self._unindex_link(link)
        cause_event = self._events.get(link.cause_event_id)
        if cause_event is not None and link_id in cause_event.outgoing_link_ids:
            cause_event.outgoing_link_ids.remove(link_id)
            cause_event.updated_at = _now()
        effect_event = self._events.get(link.effect_event_id)
        if effect_event is not None and link_id in effect_event.incoming_link_ids:
            effect_event.incoming_link_ids.remove(link_id)
            effect_event.updated_at = _now()
        for chain in self._chains.values():
            if link_id in chain.link_ids:
                chain.link_ids = [
                    lid for lid in chain.link_ids if lid != link_id
                ]
                chain.updated_at = _now()
        self._links.pop(link_id, None)

    def verify_link(
        self, link_id: str
    ) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        """Verify a causal link for structural and temporal soundness.

        Checks that both endpoints exist, the confidence meets the safe
        threshold, and the cause is timestamped at or before the effect. On
        success the link is marked verified. Returns (success, reason,
        verification_report).
        """
        with self._lock:
            link = self._links.get(link_id)
            if link is None:
                return False, "not_found", None
            cause_event = self._events.get(link.cause_event_id)
            effect_event = self._events.get(link.effect_event_id)
            issues: List[str] = []
            if cause_event is None:
                issues.append("missing_cause_event")
            if effect_event is None:
                issues.append("missing_effect_event")
            if cause_event is not None and effect_event is not None:
                cause_ts = _parse_timestamp(cause_event.timestamp)
                effect_ts = _parse_timestamp(effect_event.timestamp)
                if effect_ts + _EPSILON < cause_ts:
                    issues.append("temporal_inversion")
            if link.confidence < self._config.safe_confidence_threshold:
                issues.append("low_confidence")
            report: Dict[str, Any] = {
                "link_id": link_id,
                "cause_event_id": link.cause_event_id,
                "effect_event_id": link.effect_event_id,
                "strength": link.strength,
                "confidence": link.confidence,
                "issues": issues,
                "verified": False,
            }
            if issues:
                report["verified"] = False
                self._emit(
                    CausalityEventKind.LINK_VERIFIED,
                    entity_id=link_id,
                    description=f"Link verification failed: {link_id}",
                    metadata={"issues": issues},
                )
                return False, "verification_failed", report
            link.verified = True
            report["verified"] = True
            self._emit(
                CausalityEventKind.LINK_VERIFIED,
                entity_id=link_id,
                description=f"Link verified: {link_id}",
            )
            return True, "verified", report

    # ------------------------------------------------------------------
    # Chain Management
    # ------------------------------------------------------------------

    def register_chain(
        self,
        chain_id: str,
        title: str = "",
        description: str = "",
        event_ids: Optional[List[str]] = None,
    ) -> Tuple[bool, str, Optional[CausalChain]]:
        """Register a new causal chain threading an ordered event list.

        Every event id in the list must already exist. Unknown ids cause the
        whole registration to fail. Returns (success, reason, chain).
        """
        with self._lock:
            if not chain_id:
                return False, "empty_chain_id", None
            if chain_id in self._chains:
                return False, "chain_exists", None
            if len(self._chains) >= self._config.max_chains:
                return False, "chains_capacity", None
            ids = list(event_ids or [])
            for eid in ids:
                if eid not in self._events:
                    return False, f"unknown_event:{eid}", None
            now = _now()
            chain = CausalChain(
                chain_id=chain_id,
                title=str(title),
                description=str(description),
                event_ids=ids,
                link_ids=[],
                status=ChainStatus.ACTIVE.value,
                created_at=now,
                updated_at=now,
            )
            # Collect links that connect consecutive events in the chain.
            for idx in range(len(ids) - 1):
                cause_id = ids[idx]
                effect_id = ids[idx + 1]
                for link_id in self._outgoing.get(cause_id, []):
                    link = self._links.get(link_id)
                    if link is not None and link.effect_event_id == effect_id:
                        if link_id not in chain.link_ids:
                            chain.link_ids.append(link_id)
                        break
            self._chains[chain_id] = chain
            for eid in ids:
                event = self._events.get(eid)
                if event is not None and chain_id not in event.chain_ids:
                    event.chain_ids.append(chain_id)
                    event.updated_at = now
            _evict_fifo_dict(self._chains, self._config.max_chains)
            self._emit(
                CausalityEventKind.CHAIN_REGISTERED,
                entity_id=chain_id,
                description=f"Chain registered: {chain_id}",
                metadata={"event_count": len(ids)},
            )
            return True, "registered", chain

    def get_chain(self, chain_id: str) -> Optional[CausalChain]:
        """Return the causal chain with the given id, or None."""
        with self._lock:
            return self._chains.get(chain_id)

    def list_chains(
        self, status: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """List causal chains, optionally filtered by status."""
        with self._lock:
            status_value: Optional[str] = None
            if status is not None:
                status_enum = _coerce_enum(ChainStatus, status)
                if status_enum is not None:
                    status_value = status_enum.value
                else:
                    status_value = str(status)
            items = list(self._chains.values())
            if status_value is not None:
                items = [c for c in items if c.status == status_value]
            return [c.to_dict() for c in items]

    def remove_chain(self, chain_id: str) -> Tuple[bool, str, Optional[str]]:
        """Remove a causal chain from the registry.

        The events and links that made up the chain are left in place; only
        the chain thread is removed. Returns (success, reason,
        removed_chain_id).
        """
        with self._lock:
            chain = self._chains.get(chain_id)
            if chain is None:
                return False, "not_found", None
            for eid in chain.event_ids:
                event = self._events.get(eid)
                if event is not None and chain_id in event.chain_ids:
                    event.chain_ids.remove(chain_id)
                    event.updated_at = _now()
            self._chains.pop(chain_id, None)
            self._emit(
                CausalityEventKind.CHAIN_REMOVED,
                entity_id=chain_id,
                description=f"Chain removed: {chain_id}",
            )
            return True, "removed", chain_id

    def extend_chain(
        self, chain_id: str, event_id: str
    ) -> Tuple[bool, str, Optional[CausalChain]]:
        """Append an event to the end of an existing chain.

        The event must exist and the chain must be active. When a causal
        link connects the previous tail to the new event, it is attached to
        the chain link list. Returns (success, reason, chain).
        """
        with self._lock:
            chain = self._chains.get(chain_id)
            if chain is None:
                return False, "not_found", None
            if chain.status != ChainStatus.ACTIVE.value:
                return False, "chain_not_active", chain
            if event_id not in self._events:
                return False, "unknown_event", chain
            if event_id in chain.event_ids:
                return False, "already_in_chain", chain
            chain.event_ids.append(event_id)
            event = self._events[event_id]
            if chain_id not in event.chain_ids:
                event.chain_ids.append(chain_id)
            # Attach a link if one connects the old tail to the new event.
            if len(chain.event_ids) >= 2:
                prev_id = chain.event_ids[-2]
                for link_id in self._outgoing.get(prev_id, []):
                    link = self._links.get(link_id)
                    if link is not None and link.effect_event_id == event_id:
                        if link_id not in chain.link_ids:
                            chain.link_ids.append(link_id)
                        break
            chain.updated_at = _now()
            self._emit(
                CausalityEventKind.CHAIN_EXTENDED,
                entity_id=chain_id,
                description=f"Chain extended: {chain_id} + {event_id}",
            )
            return True, "extended", chain

    def resolve_chain(
        self, chain_id: str
    ) -> Tuple[bool, str, Optional[CausalChain]]:
        """Mark a chain as resolved, freezing its event sequence.

        Returns (success, reason, chain).
        """
        with self._lock:
            chain = self._chains.get(chain_id)
            if chain is None:
                return False, "not_found", None
            if chain.status == ChainStatus.RESOLVED.value:
                return False, "already_resolved", chain
            if chain.status == ChainStatus.BROKEN.value:
                return False, "chain_broken", chain
            chain.status = ChainStatus.RESOLVED.value
            chain.resolved_at = _now()
            chain.updated_at = _now()
            self._emit(
                CausalityEventKind.CHAIN_RESOLVED,
                entity_id=chain_id,
                description=f"Chain resolved: {chain_id}",
            )
            return True, "resolved", chain

    def get_chain_events(
        self, chain_id: str
    ) -> List[Dict[str, Any]]:
        """Return the ordered events of a chain as dicts.

        Returns an empty list when the chain is unknown.
        """
        with self._lock:
            chain = self._chains.get(chain_id)
            if chain is None:
                return []
            result: List[Dict[str, Any]] = []
            for eid in chain.event_ids:
                event = self._events.get(eid)
                if event is not None:
                    result.append(event.to_dict())
            return result

    def get_chain_summary(
        self, chain_id: str
    ) -> Dict[str, Any]:
        """Return a compact summary of a chain's structure and health.

        The summary includes event count, link coverage (how many
        consecutive event pairs have a connecting link), status, and the
        list of category transitions along the chain.
        """
        with self._lock:
            chain = self._chains.get(chain_id)
            if chain is None:
                return {"found": False, "chain_id": chain_id}
            ids = chain.event_ids
            event_count = len(ids)
            pair_count = max(0, event_count - 1)
            linked_pairs = 0
            categories: List[str] = []
            transitions: List[str] = []
            prev_cat: Optional[str] = None
            for eid in ids:
                event = self._events.get(eid)
                if event is not None:
                    categories.append(event.category)
                    if prev_cat is not None and event.category != prev_cat:
                        transitions.append(f"{prev_cat}->{event.category}")
                    prev_cat = event.category
            for idx in range(event_count - 1):
                cause_id = ids[idx]
                effect_id = ids[idx + 1]
                found = False
                for link_id in self._outgoing.get(cause_id, []):
                    link = self._links.get(link_id)
                    if link is not None and link.effect_event_id == effect_id:
                        found = True
                        break
                if found:
                    linked_pairs += 1
            coverage = (
                round(linked_pairs / pair_count, 4) if pair_count > 0 else 1.0
            )
            return {
                "found": True,
                "chain_id": chain_id,
                "title": chain.title,
                "status": chain.status,
                "event_count": event_count,
                "link_count": len(chain.link_ids),
                "linked_pairs": linked_pairs,
                "pair_count": pair_count,
                "link_coverage": coverage,
                "categories": categories,
                "category_transitions": transitions,
                "created_at": chain.created_at,
                "updated_at": chain.updated_at,
                "resolved_at": chain.resolved_at,
            }

    # ------------------------------------------------------------------
    # Butterfly Effect Management
    # ------------------------------------------------------------------

    def register_butterfly_effect(
        self,
        butterfly_id: str,
        root_event_id: str,
        impact_level: str = "minor",
        description: str = "",
    ) -> Tuple[bool, str, Optional[ButterflyEffect]]:
        """Register a butterfly effect rooted at a given event.

        The root event must exist. Terminal events and spread metrics are
        computed by tracing downstream effects up to the configured
        prediction depth. Returns (success, reason, butterfly_effect).
        """
        with self._lock:
            if not butterfly_id:
                return False, "empty_butterfly_id", None
            if butterfly_id in self._butterfly_effects:
                return False, "butterfly_exists", None
            if root_event_id not in self._events:
                return False, "unknown_root_event", None
            if len(self._butterfly_effects) >= self._config.max_butterfly_effects:
                return False, "butterfly_capacity", None
            impact_enum = _coerce_enum(
                ButterflyImpact, impact_level, ButterflyImpact.MINOR
            )
            if impact_enum is None:
                return False, "invalid_impact", None
            spread = self._bfs_forward(
                root_event_id, self._config.prediction_depth
            )
            terminal_ids: List[str] = []
            max_depth = 0
            for eid, depth, _conf in spread:
                if eid == root_event_id:
                    continue
                if depth > max_depth:
                    max_depth = depth
                downstream = self._effect_ids_for(eid)
                if not downstream:
                    terminal_ids.append(eid)
            if not terminal_ids and len(spread) > 1:
                terminal_ids = [eid for eid, _, _ in spread if eid != root_event_id]
            bf = ButterflyEffect(
                butterfly_id=butterfly_id,
                root_event_id=root_event_id,
                impact_level=impact_enum.value,
                description=str(description),
                terminal_event_ids=terminal_ids,
                spread_depth=max_depth,
                spread_breadth=max(0, len(spread) - 1),
                created_at=_now(),
            )
            self._butterfly_effects[butterfly_id] = bf
            _evict_fifo_dict(
                self._butterfly_effects, self._config.max_butterfly_effects
            )
            self._emit(
                CausalityEventKind.BUTTERFLY_REGISTERED,
                entity_id=butterfly_id,
                description=f"Butterfly effect registered: {butterfly_id}",
                metadata={
                    "root": root_event_id,
                    "impact": impact_enum.value,
                    "spread_breadth": bf.spread_breadth,
                },
            )
            return True, "registered", bf

    def get_butterfly_effect(
        self, butterfly_id: str
    ) -> Optional[ButterflyEffect]:
        """Return the butterfly effect with the given id, or None."""
        with self._lock:
            return self._butterfly_effects.get(butterfly_id)

    def list_butterfly_effects(
        self, impact_level: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """List butterfly effects, optionally filtered by impact level.

        Results are sorted by impact magnitude descending so the most
        disruptive effects appear first.
        """
        with self._lock:
            impact_value: Optional[str] = None
            if impact_level is not None:
                impact_enum = _coerce_enum(ButterflyImpact, impact_level)
                if impact_enum is not None:
                    impact_value = impact_enum.value
                else:
                    impact_value = str(impact_level)
            items = list(self._butterfly_effects.values())
            if impact_value is not None:
                items = [b for b in items if b.impact_level == impact_value]
            items.sort(
                key=lambda b: _impact_magnitude(b.impact_level),
                reverse=True,
            )
            return [b.to_dict() for b in items]

    def remove_butterfly_effect(
        self, butterfly_id: str
    ) -> Tuple[bool, str, Optional[str]]:
        """Remove a butterfly effect from the catalog.

        Returns (success, reason, removed_butterfly_id).
        """
        with self._lock:
            if butterfly_id not in self._butterfly_effects:
                return False, "not_found", None
            self._butterfly_effects.pop(butterfly_id, None)
            self._emit(
                CausalityEventKind.BUTTERFLY_REMOVED,
                entity_id=butterfly_id,
                description=f"Butterfly effect removed: {butterfly_id}",
            )
            return True, "removed", butterfly_id

    def detect_butterfly_effects(self) -> List[Dict[str, Any]]:
        """Auto-detect small causes with large downstream effects.

        Scans every event that looks like a small cause (few participants,
        player or environmental category) and traces its downstream spread.
        When the spread breadth exceeds the configured butterfly threshold,
        a butterfly effect is registered automatically. Returns the list of
        detected butterfly effect dicts (newly created ones first).
        """
        with self._lock:
            if not self._config.enable_auto_detection:
                return []
            # The threshold is interpreted as a minimum downstream breadth.
            min_breadth = max(
                2, int(round(self._config.butterfly_threshold * 10))
            )
            # Build a set of root ids already tracked to avoid duplicates.
            existing_roots: Set[str] = {
                b.root_event_id for b in self._butterfly_effects.values()
            }
            detected: List[Dict[str, Any]] = []
            for event in list(self._events.values()):
                if not self._is_small_cause(event):
                    continue
                if event.event_id in existing_roots:
                    continue
                spread = self._bfs_forward(
                    event.event_id, self._config.prediction_depth
                )
                breadth = max(0, len(spread) - 1)
                if breadth < min_breadth:
                    continue
                # Score the impact from spread breadth and depth.
                max_depth = max((d for _, d, _ in spread), default=0)
                magnitude = breadth + max_depth
                if magnitude >= 8:
                    impact = ButterflyImpact.WORLD_ALTERING.value
                elif magnitude >= 6:
                    impact = ButterflyImpact.CATASTROPHIC.value
                elif magnitude >= 4:
                    impact = ButterflyImpact.MAJOR.value
                elif magnitude >= 3:
                    impact = ButterflyImpact.MODERATE.value
                else:
                    impact = ButterflyImpact.MINOR.value
                bf_id = _new_id("bf_auto")
                bf = ButterflyEffect(
                    butterfly_id=bf_id,
                    root_event_id=event.event_id,
                    impact_level=impact,
                    description=(
                        f"Auto-detected butterfly effect from "
                        f"'{event.description[:80]}' with spread breadth "
                        f"{breadth} and depth {max_depth}."
                    ),
                    terminal_event_ids=[
                        eid for eid, _, _ in spread
                        if eid != event.event_id
                        and not self._effect_ids_for(eid)
                    ],
                    spread_depth=max_depth,
                    spread_breadth=breadth,
                    created_at=_now(),
                    metadata={"auto_detected": True},
                )
                self._butterfly_effects[bf_id] = bf
                existing_roots.add(event.event_id)
                self._total_butterfly_detected += 1
                detected.append(bf.to_dict())
                self._emit(
                    CausalityEventKind.BUTTERFLY_DETECTED,
                    entity_id=bf_id,
                    description=f"Butterfly effect detected: {bf_id}",
                    metadata={
                        "root": event.event_id,
                        "impact": impact,
                        "breadth": breadth,
                        "depth": max_depth,
                    },
                )
            _evict_fifo_dict(
                self._butterfly_effects, self._config.max_butterfly_effects
            )
            return detected

    # ------------------------------------------------------------------
    # Graph Queries
    # ------------------------------------------------------------------

    def trace_causes(
        self, event_id: str, depth: int = 5
    ) -> Dict[str, Any]:
        """Trace backward from an event to find its root causes.

        Returns a dict with the start event, the depth used, and a list of
        (event_id, depth, path_confidence) tuples for every upstream cause
        within the depth limit.
        """
        with self._lock:
            if event_id not in self._events:
                return {"found": False, "event_id": event_id, "causes": []}
            safe_depth = max(0, min(int(depth), _MAX_TRAVERSAL_DEPTH))
            raw = self._bfs_backward(event_id, safe_depth)
            causes = [
                {"event_id": eid, "depth": d, "path_confidence": round(c, 4)}
                for eid, d, c in raw
                if eid != event_id
            ]
            return {
                "found": True,
                "event_id": event_id,
                "depth": safe_depth,
                "causes": causes,
                "cause_count": len(causes),
            }

    def trace_effects(
        self, event_id: str, depth: int = 5
    ) -> Dict[str, Any]:
        """Trace forward from an event to find all downstream effects.

        Returns a dict with the start event, the depth used, and a list of
        (event_id, depth, path_confidence) tuples for every downstream
        effect within the depth limit.
        """
        with self._lock:
            if event_id not in self._events:
                return {"found": False, "event_id": event_id, "effects": []}
            safe_depth = max(0, min(int(depth), _MAX_TRAVERSAL_DEPTH))
            raw = self._bfs_forward(event_id, safe_depth)
            effects = [
                {"event_id": eid, "depth": d, "path_confidence": round(c, 4)}
                for eid, d, c in raw
                if eid != event_id
            ]
            return {
                "found": True,
                "event_id": event_id,
                "depth": safe_depth,
                "effects": effects,
                "effect_count": len(effects),
            }

    def find_path(
        self, from_event_id: str, to_event_id: str
    ) -> Dict[str, Any]:
        """Find a causal path between two events following cause -> effect.

        Uses breadth-first search so the returned path is the shortest
        causal chain from the source to the target. Returns a dict with a
        ``found`` flag, the path as a list of event ids, and the links that
        connect them.
        """
        with self._lock:
            if from_event_id not in self._events:
                return {"found": False, "reason": "unknown_from"}
            if to_event_id not in self._events:
                return {"found": False, "reason": "unknown_to"}
            if from_event_id == to_event_id:
                return {
                    "found": True,
                    "from": from_event_id,
                    "to": to_event_id,
                    "path": [from_event_id],
                    "links": [],
                    "length": 0,
                }
            # BFS tracking the predecessor link that reached each node.
            predecessor: Dict[str, Optional[str]] = {from_event_id: None}
            queue: deque = deque([from_event_id])
            found = False
            while queue:
                current = queue.popleft()
                if current == to_event_id:
                    found = True
                    break
                for link_id in self._outgoing.get(current, []):
                    link = self._links.get(link_id)
                    if link is None:
                        continue
                    nxt = link.effect_event_id
                    if nxt not in predecessor:
                        predecessor[nxt] = link_id
                        queue.append(nxt)
                        if nxt == to_event_id:
                            found = True
                            break
                if found:
                    break
            if not found and to_event_id not in predecessor:
                return {
                    "found": False,
                    "from": from_event_id,
                    "to": to_event_id,
                    "reason": "no_path",
                }
            # Reconstruct the path by walking predecessors backward.
            path: List[str] = []
            links: List[str] = []
            cursor: str = to_event_id
            while cursor is not None:
                path.append(cursor)
                link_id = predecessor.get(cursor)
                if link_id is None:
                    break
                links.append(link_id)
                link = self._links.get(link_id)
                if link is None:
                    break
                cursor = link.cause_event_id
            path.reverse()
            links.reverse()
            return {
                "found": True,
                "from": from_event_id,
                "to": to_event_id,
                "path": path,
                "links": links,
                "length": len(links),
            }

    def get_root_causes(self, event_id: str) -> Dict[str, Any]:
        """Return the root causes of an event.

        Root causes are upstream events with no incoming links, traced
        backward without a depth bound (the traversal is naturally bounded
        by the DAG size).
        """
        with self._lock:
            if event_id not in self._events:
                return {"found": False, "event_id": event_id, "roots": []}
            # Trace backward to the full DAG depth limit.
            raw = self._bfs_backward(event_id, _MAX_TRAVERSAL_DEPTH)
            roots: List[Dict[str, Any]] = []
            for eid, depth, conf in raw:
                if eid == event_id:
                    continue
                if not self._incoming.get(eid):
                    event = self._events.get(eid)
                    roots.append({
                        "event_id": eid,
                        "depth": depth,
                        "path_confidence": round(conf, 4),
                        "description": event.description if event else "",
                        "category": event.category if event else "",
                    })
            return {
                "found": True,
                "event_id": event_id,
                "roots": roots,
                "root_count": len(roots),
            }

    def get_terminal_effects(self, event_id: str) -> Dict[str, Any]:
        """Return the terminal effects of an event.

        Terminal effects are downstream events with no outgoing links,
        traced forward without a depth bound.
        """
        with self._lock:
            if event_id not in self._events:
                return {"found": False, "event_id": event_id, "terminals": []}
            raw = self._bfs_forward(event_id, _MAX_TRAVERSAL_DEPTH)
            terminals: List[Dict[str, Any]] = []
            for eid, depth, conf in raw:
                if eid == event_id:
                    continue
                if not self._outgoing.get(eid):
                    event = self._events.get(eid)
                    terminals.append({
                        "event_id": eid,
                        "depth": depth,
                        "path_confidence": round(conf, 4),
                        "description": event.description if event else "",
                        "category": event.category if event else "",
                    })
            return {
                "found": True,
                "event_id": event_id,
                "terminals": terminals,
                "terminal_count": len(terminals),
            }

    def compute_centrality(self, event_id: str) -> Dict[str, Any]:
        """Compute how central an event is in the causal graph.

        Combines degree centrality (in plus out degree normalized by the
        maximum possible), reachability (how many events are reachable
        forward and backward), and a betweenness proxy (how often the event
        sits on shortest paths between other event pairs).
        """
        with self._lock:
            if event_id not in self._events:
                return {"found": False, "event_id": event_id}
            total = len(self._events)
            in_degree = len(self._incoming.get(event_id, []))
            out_degree = len(self._outgoing.get(event_id, []))
            degree = in_degree + out_degree
            degree_centrality = (
                degree / max(1, total - 1) if total > 1 else 0.0
            )
            # Reachability forward and backward.
            forward = self._bfs_forward(event_id, _MAX_TRAVERSAL_DEPTH)
            backward = self._bfs_backward(event_id, _MAX_TRAVERSAL_DEPTH)
            reachable_forward = max(0, len(forward) - 1)
            reachable_backward = max(0, len(backward) - 1)
            reachability = (
                (reachable_forward + reachable_backward)
                / max(1, total - 1)
                if total > 1
                else 0.0
            )
            # Betweenness proxy: count pairs (a, b) such that event_id lies
            # on a forward path from a to b. Approximated by checking
            # whether a can reach event_id forward and event_id can reach b
            # forward, with a != event_id and b != event_id.
            betweenness_pairs = 0
            if total > 2:
                reachable_to_self = {
                    eid for eid, _, _ in backward if eid != event_id
                }
                reachable_from_self = {
                    eid for eid, _, _ in forward if eid != event_id
                }
                for a in reachable_to_self:
                    for b in reachable_from_self:
                        if a != b:
                            betweenness_pairs += 1
            max_pairs = max(1, (total - 1) * (total - 2))
            betweenness = betweenness_pairs / max_pairs if total > 2 else 0.0
            # Composite score in [0, 1].
            composite = _clamp(
                0.4 * degree_centrality
                + 0.3 * reachability
                + 0.3 * betweenness
            )
            return {
                "found": True,
                "event_id": event_id,
                "in_degree": in_degree,
                "out_degree": out_degree,
                "degree": degree,
                "degree_centrality": round(degree_centrality, 4),
                "reachable_forward": reachable_forward,
                "reachable_backward": reachable_backward,
                "reachability": round(reachability, 4),
                "betweenness_proxy": round(betweenness, 4),
                "betweenness_pairs": betweenness_pairs,
                "composite_centrality": round(composite, 4),
            }

    def get_causal_neighborhood(
        self, event_id: str, radius: int = 2
    ) -> Dict[str, Any]:
        """Return the events within a graph radius of the given event.

        Traverses both forward and backward up to the radius and returns the
        collected events with their direction and distance from the center.
        """
        with self._lock:
            if event_id not in self._events:
                return {"found": False, "event_id": event_id, "neighbors": []}
            rad = max(0, min(int(radius), _MAX_NEIGHBORHOOD_RADIUS))
            forward = self._bfs_forward(event_id, rad)
            backward = self._bfs_backward(event_id, rad)
            neighbors: Dict[str, Dict[str, Any]] = {}
            for eid, depth, conf in forward:
                if eid == event_id:
                    continue
                if depth > rad:
                    continue
                entry = neighbors.setdefault(eid, {
                    "event_id": eid,
                    "forward_depth": depth,
                    "backward_depth": None,
                    "path_confidence": round(conf, 4),
                })
                entry["forward_depth"] = depth
            for eid, depth, conf in backward:
                if eid == event_id:
                    continue
                if depth > rad:
                    continue
                entry = neighbors.setdefault(eid, {
                    "event_id": eid,
                    "forward_depth": None,
                    "backward_depth": depth,
                    "path_confidence": round(conf, 4),
                })
                entry["backward_depth"] = depth
                entry["path_confidence"] = round(conf, 4)
            # Annotate with descriptions.
            result: List[Dict[str, Any]] = []
            for eid, entry in neighbors.items():
                event = self._events.get(eid)
                entry["description"] = event.description if event else ""
                entry["category"] = event.category if event else ""
                result.append(entry)
            result.sort(
                key=lambda n: (
                    n.get("forward_depth") or rad + 1,
                    n.get("backward_depth") or rad + 1,
                )
            )
            return {
                "found": True,
                "event_id": event_id,
                "radius": rad,
                "neighbors": result,
                "neighbor_count": len(result),
            }

    # ------------------------------------------------------------------
    # AI Methods
    # ------------------------------------------------------------------

    def ai_predict_consequences(
        self, event_id: str, depth: int = 3
    ) -> Tuple[bool, str, Optional[ConsequencePrediction]]:
        """AI-predict the downstream consequences of an event.

        Traces forward effects up to the given depth, then synthesizes
        human-readable consequence descriptions by combining the traced
        event descriptions with deterministic verb and subject fragments.
        The overall confidence is the average path confidence of the traced
        effects, damped by depth. Returns (success, reason, prediction).
        """
        with self._lock:
            if event_id not in self._events:
                return False, "unknown_event", None
            safe_depth = max(1, min(int(depth), _MAX_TRAVERSAL_DEPTH))
            if len(self._predictions) >= self._config.max_predictions:
                return False, "predictions_capacity", None
            spread = self._bfs_forward(event_id, safe_depth)
            predicted_ids: List[str] = []
            descriptions: List[str] = []
            confidences: List[float] = []
            root_event = self._events[event_id]
            for eid, d, conf in spread:
                if eid == event_id:
                    continue
                predicted_ids.append(eid)
                confidences.append(conf)
                event = self._events.get(eid)
                verb = _PREDICTION_VERBS[
                    hash(eid) % len(_PREDICTION_VERBS)
                ]
                subject = _PREDICTION_SUBJECTS[
                    hash(eid + root_event.event_id)
                    % len(_PREDICTION_SUBJECTS)
                ]
                tail = event.description[:60] if event else "an outcome"
                descriptions.append(
                    f"At depth {d}, the event '{tail}' may {verb} "
                    f"{subject} (confidence {round(conf, 2)})."
                )
            if confidences:
                avg_conf = sum(confidences) / len(confidences)
            else:
                avg_conf = 0.0
            # Damp confidence when nothing was found.
            if not predicted_ids:
                descriptions.append(
                    "No downstream consequences detected within the "
                    "prediction depth; the event appears to be a terminal "
                    "or isolated cause."
                )
            prediction_id = _new_id("pred_ai")
            prediction = ConsequencePrediction(
                prediction_id=prediction_id,
                source_event_id=event_id,
                predicted_event_ids=predicted_ids,
                predicted_descriptions=descriptions,
                depth=safe_depth,
                confidence=round(avg_conf, 4),
                created_at=_now(),
                metadata={
                    "ai_generated": True,
                    "source_description": root_event.description[:120],
                    "spread_breadth": len(predicted_ids),
                },
            )
            self._predictions[prediction_id] = prediction
            self._total_predictions_generated += 1
            _evict_fifo_dict(self._predictions, self._config.max_predictions)
            self._emit(
                CausalityEventKind.PREDICTION_GENERATED,
                entity_id=prediction_id,
                description=f"AI consequence prediction: {event_id}",
                metadata={
                    "source": event_id,
                    "predicted_count": len(predicted_ids),
                    "depth": safe_depth,
                },
            )
            return True, "predicted", prediction

    def ai_check_consistency(
        self, chain_id: str
    ) -> Tuple[bool, str, Optional[ConsistencyReport]]:
        """AI-check the narrative consistency of a causal chain.

        Evaluates the chain against a rule table: missing links between
        consecutive events, temporal inversions, orphan events, low
        confidence links, and category mismatches. Produces a score in
        [0, 1] and a list of violations and warnings. Returns (success,
        reason, report).
        """
        with self._lock:
            chain = self._chains.get(chain_id)
            if chain is None:
                return False, "not_found", None
            if len(self._reports) >= self._config.max_reports:
                return False, "reports_capacity", None
            violations: List[str] = []
            warnings: List[str] = []
            notes: List[str] = []
            ids = chain.event_ids
            event_count = len(ids)
            if event_count == 0:
                violations.append("empty_chain")
            pair_count = max(0, event_count - 1)
            linked_pairs = 0
            for idx in range(event_count - 1):
                cause_id = ids[idx]
                effect_id = ids[idx + 1]
                cause_event = self._events.get(cause_id)
                effect_event = self._events.get(effect_id)
                connecting_link: Optional[CausalLink] = None
                for link_id in self._outgoing.get(cause_id, []):
                    link = self._links.get(link_id)
                    if link is not None and link.effect_event_id == effect_id:
                        connecting_link = link
                        break
                if connecting_link is None:
                    violations.append(
                        f"missing_link:{cause_id}->{effect_id}"
                    )
                else:
                    linked_pairs += 1
                    if connecting_link.confidence < (
                            self._config.safe_confidence_threshold):
                        warnings.append(
                            f"low_confidence:{connecting_link.link_id}"
                        )
                if cause_event is not None and effect_event is not None:
                    cause_ts = _parse_timestamp(cause_event.timestamp)
                    effect_ts = _parse_timestamp(effect_event.timestamp)
                    if effect_ts + _EPSILON < cause_ts:
                        violations.append(
                            f"temporal_inversion:{cause_id}->{effect_id}"
                        )
                    # Category mismatch: a narrative event directly sourced
                    # from a systemic trigger with no mediator.
                    if (cause_event.category
                            == EventCategory.SYSTEMIC.value
                            and effect_event.category
                            == EventCategory.NARRATIVE.value):
                        warnings.append(
                            f"category_mismatch:{cause_id}->{effect_id}"
                        )
            # Orphan detection: events with no links at all.
            for eid in ids:
                event = self._events.get(eid)
                if event is None:
                    continue
                if (not event.incoming_link_ids
                        and not event.outgoing_link_ids):
                    warnings.append(f"orphan_event:{eid}")
            if pair_count > 0:
                coverage = linked_pairs / pair_count
            else:
                coverage = 1.0
            # Score starts from link coverage and is reduced by violations.
            penalty = 0.0
            rule_map = {rule: desc for rule, desc in _CONSISTENCY_RULES}
            for v in violations:
                key = v.split(":", 1)[0]
                if key in rule_map:
                    penalty += 0.2
                else:
                    penalty += 0.1
            for w in warnings:
                key = w.split(":", 1)[0]
                if key in rule_map:
                    penalty += 0.05
                else:
                    penalty += 0.02
            score = _clamp(coverage - penalty)
            is_consistent = len(violations) == 0 and score >= 0.6
            if is_consistent:
                notes.append(
                    "Chain is internally coherent: every consecutive event "
                    "pair is linked and no temporal inversions were found."
                )
            else:
                notes.append(
                    "Chain shows structural gaps or ordering issues that "
                    "should be resolved before treating it as canonical."
                )
            report_id = _new_id("report_ai")
            report = ConsistencyReport(
                report_id=report_id,
                chain_id=chain_id,
                is_consistent=is_consistent,
                score=round(score, 4),
                violations=violations,
                warnings=warnings,
                notes=notes,
                created_at=_now(),
                metadata={
                    "ai_generated": True,
                    "event_count": event_count,
                    "linked_pairs": linked_pairs,
                    "pair_count": pair_count,
                    "link_coverage": round(coverage, 4),
                },
            )
            self._reports[report_id] = report
            self._total_consistency_checks += 1
            _evict_fifo_dict(self._reports, self._config.max_reports)
            self._emit(
                CausalityEventKind.CONSISTENCY_CHECKED,
                entity_id=report_id,
                description=f"AI consistency check: {chain_id}",
                metadata={
                    "chain": chain_id,
                    "is_consistent": is_consistent,
                    "score": round(score, 4),
                },
            )
            return True, "checked", report

    def ai_generate_butterfly(
        self, root_event_id: str
    ) -> Tuple[bool, str, Optional[ButterflyEffect]]:
        """AI-generate a butterfly effect scenario from a root event.

        Traces the downstream spread of the root event, scores the
        disruption magnitude from breadth and depth, and registers a
        butterfly effect with an auto-computed impact level and a
        narrative description. Returns (success, reason, butterfly_effect).
        """
        with self._lock:
            if root_event_id not in self._events:
                return False, "unknown_event", None
            if len(self._butterfly_effects) >= self._config.max_butterfly_effects:
                return False, "butterfly_capacity", None
            spread = self._bfs_forward(
                root_event_id, self._config.prediction_depth
            )
            breadth = max(0, len(spread) - 1)
            if breadth == 0:
                return False, "no_downstream_spread", None
            max_depth = max((d for _, d, _ in spread), default=0)
            magnitude = breadth + max_depth
            if magnitude >= 8:
                impact = ButterflyImpact.WORLD_ALTERING.value
            elif magnitude >= 6:
                impact = ButterflyImpact.CATASTROPHIC.value
            elif magnitude >= 4:
                impact = ButterflyImpact.MAJOR.value
            elif magnitude >= 3:
                impact = ButterflyImpact.MODERATE.value
            else:
                impact = ButterflyImpact.MINOR.value
            root_event = self._events[root_event_id]
            terminal_ids = [
                eid for eid, _, _ in spread
                if eid != root_event_id and not self._effect_ids_for(eid)
            ]
            if not terminal_ids:
                terminal_ids = [
                    eid for eid, _, _ in spread if eid != root_event_id
                ]
            bf_id = _new_id("bf_ai")
            description = (
                f"AI scenario: the event '{root_event.description[:80]}' "
                f"cascades across {breadth} downstream events to a depth of "
                f"{max_depth}, reaching impact level '{impact}'."
            )
            bf = ButterflyEffect(
                butterfly_id=bf_id,
                root_event_id=root_event_id,
                impact_level=impact,
                description=description,
                terminal_event_ids=terminal_ids,
                spread_depth=max_depth,
                spread_breadth=breadth,
                created_at=_now(),
                metadata={
                    "ai_generated": True,
                    "magnitude": magnitude,
                },
            )
            self._butterfly_effects[bf_id] = bf
            self._total_butterfly_detected += 1
            _evict_fifo_dict(
                self._butterfly_effects, self._config.max_butterfly_effects
            )
            self._emit(
                CausalityEventKind.BUTTERFLY_DETECTED,
                entity_id=bf_id,
                description=f"AI butterfly scenario: {bf_id}",
                metadata={
                    "root": root_event_id,
                    "impact": impact,
                    "breadth": breadth,
                    "depth": max_depth,
                },
            )
            return True, "generated", bf

    def ai_suggest_intervention(
        self, event_id: str
    ) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        """AI-suggest where to intervene to alter an event's outcome.

        Analyzes the forward spread of the event and identifies the link
        whose removal would disconnect the most downstream effects from the
        source. Returns a suggestion dict naming the lever, the target
        link, and the expected reduction in spread. Returns (success,
        reason, suggestion).
        """
        with self._lock:
            if event_id not in self._events:
                return False, "unknown_event", None
            spread = self._bfs_forward(
                event_id, self._config.prediction_depth
            )
            total_downstream = max(0, len(spread) - 1)
            if total_downstream == 0:
                return True, "no_intervention_needed", {
                    "event_id": event_id,
                    "has_downstream": False,
                    "suggestion": (
                        "The event has no downstream effects, so no "
                        "intervention is required to alter its outcome."
                    ),
                    "target_link_id": None,
                    "expected_spread_reduction": 0,
                    "lever": None,
                }
            # Evaluate each direct outgoing link by counting how many
            # downstream events would become unreachable if that link were
            # removed. The link with the highest disconnection count is the
            # highest-leverage intervention point.
            best_link_id: Optional[str] = None
            best_reduction = 0
            best_branch_size = 0
            for link_id in self._outgoing.get(event_id, []):
                link = self._links.get(link_id)
                if link is None:
                    continue
                # Count reachable events from the branch root (the direct
                # effect) without passing back through the candidate link.
                branch_root = link.effect_event_id
                branch_spread = self._bfs_forward(
                    branch_root, self._config.prediction_depth
                )
                branch_size = max(0, len(branch_spread) - 1)
                # The reduction is the size of the branch that would be
                # detached, capped at the total downstream count.
                reduction = min(branch_size, total_downstream)
                if reduction > best_reduction:
                    best_reduction = reduction
                    best_link_id = link_id
                    best_branch_size = branch_size
            lever = _INTERVENTION_LEVERS[
                hash(event_id) % len(_INTERVENTION_LEVERS)
            ]
            suggestion = {
                "event_id": event_id,
                "has_downstream": True,
                "total_downstream": total_downstream,
                "target_link_id": best_link_id,
                "target_branch_size": best_branch_size,
                "expected_spread_reduction": best_reduction,
                "lever": lever,
                "suggestion": (
                    f"Removing or weakening link '{best_link_id}' would "
                    f"disconnect approximately {best_reduction} downstream "
                    f"events from the source. Recommended action: {lever}."
                ) if best_link_id else (
                    "No single high-leverage link was found; consider "
                    f"introducing a mediating event after '{event_id}' to "
                    "redirect the causal chain."
                ),
            }
            return True, "suggested", suggestion

    # ------------------------------------------------------------------
    # Predictions and Reports Retrieval
    # ------------------------------------------------------------------

    def get_consequence_prediction(
        self, prediction_id: str
    ) -> Optional[ConsequencePrediction]:
        """Return the consequence prediction with the given id, or None."""
        with self._lock:
            return self._predictions.get(prediction_id)

    def list_consequence_predictions(
        self, event_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """List consequence predictions, optionally filtered by source event."""
        with self._lock:
            items = list(self._predictions.values())
            if event_id is not None:
                items = [
                    p for p in items if p.source_event_id == event_id
                ]
            items = list(reversed(items))
            return [p.to_dict() for p in items]

    def get_consistency_report(
        self, report_id: str
    ) -> Optional[ConsistencyReport]:
        """Return the consistency report with the given id, or None."""
        with self._lock:
            return self._reports.get(report_id)

    def list_consistency_reports(
        self, chain_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """List consistency reports, optionally filtered by chain id."""
        with self._lock:
            items = list(self._reports.values())
            if chain_id is not None:
                items = [r for r in items if r.chain_id == chain_id]
            items = list(reversed(items))
            return [r.to_dict() for r in items]

    # ------------------------------------------------------------------
    # State and Config
    # ------------------------------------------------------------------

    def get_status(self) -> Dict[str, Any]:
        """Return a real-time health snapshot of the engine."""
        with self._lock:
            self._refresh_stats()
            return {
                "initialized": self._initialized,
                "seeded": self._seeded,
                "events": len(self._events),
                "links": len(self._links),
                "chains": len(self._chains),
                "butterfly_effects": len(self._butterfly_effects),
                "predictions": len(self._predictions),
                "reports": len(self._reports),
                "active_chains": self._stats.active_chains,
                "resolved_chains": self._stats.resolved_chains,
                "dormant_chains": self._stats.dormant_chains,
                "broken_chains": self._stats.broken_chains,
                "verified_links": self._stats.verified_links,
                "average_confidence": self._stats.average_confidence,
                "events_log": len(self._events_log),
                "tick_count": self._tick_count,
            }

    def get_stats(self) -> Dict[str, Any]:
        """Return aggregate activity counters as a dict."""
        with self._lock:
            self._refresh_stats()
            return self._stats.to_dict()

    def get_snapshot(self) -> Dict[str, Any]:
        """Return a full state snapshot for persistence and inspection."""
        with self._lock:
            self._refresh_stats()
            snapshot = CausalitySnapshot(
                timestamp=_now(),
                events=[
                    e.to_dict() for e in list(self._events.values())[-200:]
                ],
                links=[
                    lk.to_dict() for lk in list(self._links.values())[-200:]
                ],
                chains=[
                    c.to_dict() for c in list(self._chains.values())[-100:]
                ],
                butterfly_effects=[
                    b.to_dict()
                    for b in list(self._butterfly_effects.values())[-100:]
                ],
                predictions=[
                    p.to_dict()
                    for p in list(self._predictions.values())[-100:]
                ],
                reports=[
                    r.to_dict()
                    for r in list(self._reports.values())[-100:]
                ],
                events_log=[
                    e.to_dict() for e in self._events_log[-200:]
                ],
                stats=self._stats.to_dict(),
            )
            return snapshot.to_dict()

    def get_config(self) -> CausalityConfig:
        """Return the current runtime configuration."""
        with self._lock:
            return self._config

    def set_config(self, **kwargs) -> Tuple[bool, str, CausalityConfig]:
        """Apply keyword config updates to the engine.

        Only known config fields are accepted. Integer fields are clamped to
        a minimum of 1, float fields are clamped to a sane range, and
        boolean fields are coerced with bool(). Returns (success, reason,
        config).
        """
        with self._lock:
            if not kwargs:
                return False, "no_updates", self._config
            known = set(self._config.__dataclass_fields__.keys())
            int_keys = {
                "max_events", "max_links", "max_chains",
                "max_butterfly_effects", "max_predictions",
                "max_reports", "max_events_log",
                "consistency_check_frequency", "prediction_depth",
            }
            float_keys = {
                "butterfly_threshold", "safe_confidence_threshold",
            }
            bool_keys = {"enable_auto_detection"}
            applied: List[str] = []
            for key, value in kwargs.items():
                if key not in known or key == "metadata":
                    if key == "metadata" and isinstance(value, dict):
                        self._config.metadata.update(value)
                        applied.append("metadata")
                    continue
                if key in int_keys:
                    setattr(
                        self._config, key,
                        max(1, _safe_int(value, getattr(self._config, key))),
                    )
                    applied.append(key)
                elif key in float_keys:
                    if key == "butterfly_threshold":
                        setattr(
                            self._config, key,
                            _clamp(_safe_float(value, 0.3), 0.0, 1.0),
                        )
                    else:
                        setattr(
                            self._config, key,
                            _clamp(_safe_float(value, 0.5), 0.0, 1.0),
                        )
                    applied.append(key)
                elif key in bool_keys:
                    setattr(self._config, key, bool(value))
                    applied.append(key)
            if not applied:
                return False, "no_known_fields", self._config
            self._emit(
                CausalityEventKind.CONFIG_CHANGED,
                description="Config updated",
                metadata={"keys": applied},
            )
            return True, "updated", self._config

    def list_events_log(
        self,
        kind: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """List audit events from the engine timeline.

        Optionally filtered by event kind and limited to the most recent N
        entries. Results are returned newest-first.
        """
        with self._lock:
            kind_value: Optional[str] = None
            if kind is not None:
                kind_enum = _coerce_enum(CausalityEventKind, kind)
                if kind_enum is not None:
                    kind_value = kind_enum.value
                else:
                    kind_value = str(kind)
            items = list(self._events_log)
            if kind_value is not None:
                items = [e for e in items if e.kind == kind_value]
            items = list(reversed(items))
            if limit is not None:
                lim = max(0, _safe_int(limit, 0))
                items = items[:lim]
            return [e.to_dict() for e in items]

    def tick(self, dt: float = 1.0) -> Dict[str, Any]:
        """Advance the engine by one tick, running periodic maintenance.

        Periodic tasks include automatic butterfly detection (when enabled)
        and consistency re-checking of active chains on the configured
        frequency. Dormant chains that have been inactive for many ticks are
        left untouched; callers can resolve or remove them explicitly.
        """
        with self._lock:
            self._tick_count += 1
            dt_val = max(0.0, _safe_float(dt, 1.0))
            detected_count = 0
            consistency_checks = 0
            # Run automatic butterfly detection on the configured cadence.
            if self._config.enable_auto_detection:
                detected = self.detect_butterfly_effects()
                detected_count = len(detected)
            # Re-check consistency of active chains at the configured
            # frequency to keep reports fresh.
            if (self._config.consistency_check_frequency > 0
                    and self._tick_count
                    % self._config.consistency_check_frequency == 0):
                for chain in list(self._chains.values()):
                    if chain.status != ChainStatus.ACTIVE.value:
                        continue
                    if len(chain.event_ids) < 2:
                        continue
                    self.ai_check_consistency(chain.chain_id)
                    consistency_checks += 1
            self._refresh_stats()
            self._emit(
                CausalityEventKind.TICK,
                description=f"Tick {self._tick_count}",
                metadata={
                    "dt": dt_val,
                    "detected": detected_count,
                    "consistency_checks": consistency_checks,
                },
            )
            return {
                "tick": self._tick_count,
                "dt": dt_val,
                "butterfly_detected": detected_count,
                "consistency_checks": consistency_checks,
                "events": len(self._events),
                "links": len(self._links),
                "chains": len(self._chains),
                "active_chains": self._stats.active_chains,
                "average_confidence": self._stats.average_confidence,
            }

    # ------------------------------------------------------------------
    # Seed Data
    # ------------------------------------------------------------------

    def _seed_data(self) -> None:
        """Populate the engine with a canonical causal dataset.

        Seeds six events forming a dragon-slaying to kingdom-fall arc, five
        causal links connecting them into a DAG, four causal chains, three
        butterfly effects, three consequence predictions, and two
        consistency reports. This gives every public method a non-empty
        starting state to operate on.
        """
        self._seed_events()
        self._seed_links()
        self._seed_chains()
        self._seed_butterfly_effects()
        self._seed_predictions()
        self._seed_reports()
        self._seed_events_log()
        self._refresh_stats()

    def _seed_events(self) -> None:
        """Seed six canonical causal events."""
        now = _now()
        seed_events = [
            (
                "evt_player_slay_dragon",
                EventCategory.PLAYER_ACTION.value,
                "Player slew the ancient dragon that had terrorized the "
                "northern peaks for a generation.",
                ["player_hero"],
                {"location": "northern_peaks", "danger": "extreme"},
            ),
            (
                "evt_npc_celebrate",
                EventCategory.NPC_ACTION.value,
                "Villagers held a grand celebration honoring the dragon "
                "slayer and the return of safety to their homes.",
                ["villagers", "village_elder"],
                {"festivity": "grand", "duration_days": 3},
            ),
            (
                "evt_village_prosper",
                EventCategory.ENVIRONMENTAL.value,
                "The village entered a period of prosperity as trade "
                "returned and the fear of the dragon faded.",
                ["villagers"],
                {"trade_growth": 0.8, "morale": 0.9},
            ),
            (
                "evt_king_jealous",
                EventCategory.NPC_ACTION.value,
                "The king grew jealous of the hero's rising fame and the "
                "loyalty the villagers showed toward a common adventurer.",
                ["the_king"],
                {"emotion": "envy", "intensity": 0.85},
            ),
            (
                "evt_war_declared",
                EventCategory.SYSTEMIC.value,
                "The king declared war on the hero's home province, citing "
                "treason and fomenting division across the realm.",
                ["the_king", "royal_army"],
                {"mobilization": 0.9, "casus_belli": "envy"},
            ),
            (
                "evt_kingdom_fall",
                EventCategory.NARRATIVE.value,
                "The kingdom collapsed into civil strife as the divisive "
                "war fractured allegiances and drained the treasury.",
                ["the_king", "royal_army", "rebels"],
                {"stability": 0.05, "treasury": 0.1},
            ),
        ]
        for event_id, category, description, participants, properties in (
                seed_events):
            event = CausalEvent(
                event_id=event_id,
                category=category,
                description=description,
                timestamp=now,
                participants=list(participants),
                properties=dict(properties),
                created_at=now,
                updated_at=now,
            )
            self._events[event_id] = event
            self._outgoing.setdefault(event_id, [])
            self._incoming.setdefault(event_id, [])

    def _seed_links(self) -> None:
        """Seed five causal links connecting the canonical events."""
        seed_links = [
            (
                "link_slay_to_celebrate",
                "evt_player_slay_dragon",
                "evt_npc_celebrate",
                CausalStrength.DIRECT.value,
                0.95,
                "The dragon's death directly enabled the celebration.",
            ),
            (
                "link_celebrate_to_prosper",
                "evt_npc_celebrate",
                "evt_village_prosper",
                CausalStrength.STRONG.value,
                0.85,
                "The celebration marked the return of confidence that "
                "drove prosperity.",
            ),
            (
                "link_prosper_to_jealous",
                "evt_village_prosper",
                "evt_king_jealous",
                CausalStrength.MODERATE.value,
                0.7,
                "The village's prosperity and admiration for the hero "
                "stoked the king's envy.",
            ),
            (
                "link_jealous_to_war",
                "evt_king_jealous",
                "evt_war_declared",
                CausalStrength.STRONG.value,
                0.8,
                "Royal jealousy escalated into a formal declaration of war.",
            ),
            (
                "link_war_to_fall",
                "evt_war_declared",
                "evt_kingdom_fall",
                CausalStrength.DIRECT.value,
                0.9,
                "The protracted war destabilized the kingdom until it "
                "collapsed.",
            ),
        ]
        for (link_id, cause_id, effect_id, strength, confidence,
             description) in seed_links:
            link = CausalLink(
                link_id=link_id,
                cause_event_id=cause_id,
                effect_event_id=effect_id,
                strength=strength,
                confidence=confidence,
                description=description,
                verified=True,
                created_at=_now(),
            )
            self._links[link_id] = link
            self._index_link(link)
            cause_event = self._events.get(cause_id)
            effect_event = self._events.get(effect_id)
            if cause_event is not None:
                cause_event.outgoing_link_ids.append(link_id)
            if effect_event is not None:
                effect_event.incoming_link_ids.append(link_id)

    def _seed_chains(self) -> None:
        """Seed four causal chains threading the canonical events."""
        now = _now()
        seed_chains = [
            (
                "chain_dragon_glory",
                "Dragon Glory",
                "The arc from the dragon's death to village prosperity.",
                ["evt_player_slay_dragon", "evt_npc_celebrate",
                 "evt_village_prosper"],
            ),
            (
                "chain_jealousy_war",
                "Jealousy and War",
                "The arc from village prosperity to royal jealousy and war.",
                ["evt_village_prosper", "evt_king_jealous",
                 "evt_war_declared"],
            ),
            (
                "chain_kingdom_destiny",
                "Kingdom Destiny",
                "The full destiny arc from dragon slay to kingdom fall.",
                ["evt_player_slay_dragon", "evt_king_jealous",
                 "evt_war_declared", "evt_kingdom_fall"],
            ),
            (
                "chain_civil_collapse",
                "Civil Collapse",
                "The collapse arc from war declaration to kingdom fall.",
                ["evt_war_declared", "evt_kingdom_fall"],
            ),
        ]
        for chain_id, title, description, event_ids in seed_chains:
            chain = CausalChain(
                chain_id=chain_id,
                title=title,
                description=description,
                event_ids=list(event_ids),
                link_ids=[],
                status=ChainStatus.ACTIVE.value,
                created_at=now,
                updated_at=now,
            )
            # Attach links that connect consecutive events.
            for idx in range(len(event_ids) - 1):
                cause_id = event_ids[idx]
                effect_id = event_ids[idx + 1]
                for link_id in self._outgoing.get(cause_id, []):
                    link = self._links.get(link_id)
                    if link is not None and link.effect_event_id == effect_id:
                        if link_id not in chain.link_ids:
                            chain.link_ids.append(link_id)
                        break
            self._chains[chain_id] = chain
            for eid in event_ids:
                event = self._events.get(eid)
                if event is not None and chain_id not in event.chain_ids:
                    event.chain_ids.append(chain_id)
        # Mark the destiny chain as resolved to show a completed arc.
        destiny = self._chains.get("chain_kingdom_destiny")
        if destiny is not None:
            destiny.status = ChainStatus.RESOLVED.value
            destiny.resolved_at = now
            destiny.updated_at = now

    def _seed_butterfly_effects(self) -> None:
        """Seed three butterfly effects highlighting small causes."""
        seed_butterflies = [
            (
                "bf_dragon_slay_collapse",
                "evt_player_slay_dragon",
                ButterflyImpact.WORLD_ALTERING.value,
                "A single dragon slay cascaded through celebration, "
                "prosperity, jealousy, and war until the kingdom fell.",
            ),
            (
                "bf_celebration_jealousy",
                "evt_npc_celebrate",
                ButterflyImpact.MAJOR.value,
                "A village celebration sparked royal jealousy that "
                "ultimately reshaped the political landscape.",
            ),
            (
                "bf_prosper_war",
                "evt_village_prosper",
                ButterflyImpact.CATASTROPHIC.value,
                "The village's newfound prosperity triggered a chain of "
                "envy and conflict ending in catastrophic war.",
            ),
        ]
        for bf_id, root_id, impact, description in seed_butterflies:
            spread = self._bfs_forward(
                root_id, self._config.prediction_depth
            )
            terminal_ids = [
                eid for eid, _, _ in spread
                if eid != root_id and not self._effect_ids_for(eid)
            ]
            if not terminal_ids:
                terminal_ids = [
                    eid for eid, _, _ in spread if eid != root_id
                ]
            max_depth = max((d for _, d, _ in spread), default=0)
            breadth = max(0, len(spread) - 1)
            bf = ButterflyEffect(
                butterfly_id=bf_id,
                root_event_id=root_id,
                impact_level=impact,
                description=description,
                terminal_event_ids=terminal_ids,
                spread_depth=max_depth,
                spread_breadth=breadth,
                created_at=_now(),
                metadata={"seeded": True},
            )
            self._butterfly_effects[bf_id] = bf

    def _seed_predictions(self) -> None:
        """Seed three consequence predictions for key events."""
        seed_predictions = [
            (
                "pred_war_aftermath",
                "evt_war_declared",
                "The war declaration is likely to trigger civil collapse, "
                "a refugee crisis, and a collapse of public trust in the "
                "crown.",
                3,
                0.82,
            ),
            (
                "pred_prosper_risk",
                "evt_village_prosper",
                "Prosperity may cultivate political tension and royal envy, "
                "raising the risk of a divisive conflict.",
                3,
                0.66,
            ),
            (
                "pred_fall_rebuilding",
                "evt_kingdom_fall",
                "The kingdom's fall may set in motion a rebuilding effort, "
                "a surge of migration, and a search for new leadership.",
                2,
                0.74,
            ),
        ]
        for pred_id, source_id, description, depth, confidence in (
                seed_predictions):
            spread = self._bfs_forward(source_id, depth)
            predicted_ids = [
                eid for eid, _, _ in spread if eid != source_id
            ]
            descriptions: List[str] = [description]
            for eid, d, conf in spread:
                if eid == source_id:
                    continue
                event = self._events.get(eid)
                tail = event.description[:60] if event else "an outcome"
                descriptions.append(
                    f"At depth {d}, '{tail}' is a likely downstream "
                    f"consequence (confidence {round(conf, 2)})."
                )
            prediction = ConsequencePrediction(
                prediction_id=pred_id,
                source_event_id=source_id,
                predicted_event_ids=predicted_ids,
                predicted_descriptions=descriptions,
                depth=depth,
                confidence=confidence,
                created_at=_now(),
                metadata={"seeded": True},
            )
            self._predictions[pred_id] = prediction

    def _seed_reports(self) -> None:
        """Seed two consistency reports for the destiny and jealousy chains."""
        # Build the destiny report by inspecting the chain directly.
        destiny_ids = [
            "evt_player_slay_dragon", "evt_king_jealous",
            "evt_war_declared", "evt_kingdom_fall",
        ]
        destiny_report = ConsistencyReport(
            report_id="report_kingdom_destiny",
            chain_id="chain_kingdom_destiny",
            is_consistent=False,
            score=0.6,
            violations=[
                "missing_link:evt_player_slay_dragon->evt_king_jealous",
            ],
            warnings=[
                "category_mismatch:evt_war_declared->evt_kingdom_fall",
            ],
            notes=[
                "The destiny chain skips the mediating prosperity and "
                "jealousy steps between the dragon slay and the king's "
                "envy; filling these gaps would lift the consistency score.",
            ],
            created_at=_now(),
            metadata={
                "seeded": True,
                "event_count": len(destiny_ids),
                "linked_pairs": 2,
                "pair_count": 3,
                "link_coverage": 0.6667,
            },
        )
        self._reports["report_kingdom_destiny"] = destiny_report
        jealousy_report = ConsistencyReport(
            report_id="report_jealousy_war",
            chain_id="chain_jealousy_war",
            is_consistent=True,
            score=0.92,
            violations=[],
            warnings=[
                "low_confidence:link_prosper_to_jealous",
            ],
            notes=[
                "The jealousy-to-war chain is internally coherent: every "
                "consecutive pair is linked and the temporal order holds. "
                "Only the moderate confidence on the prosperity-to-jealousy "
                "link keeps the score below full marks.",
            ],
            created_at=_now(),
            metadata={
                "seeded": True,
                "event_count": 3,
                "linked_pairs": 2,
                "pair_count": 2,
                "link_coverage": 1.0,
            },
        )
        self._reports["report_jealousy_war"] = jealousy_report
        self._total_consistency_checks += 2

    def _seed_events_log(self) -> None:
        """Seed the audit timeline with a baseline set of events."""
        now = _now()
        seed_log = [
            CausalityEvent(
                event_id="cevt_seed_1",
                timestamp=now,
                kind=CausalityEventKind.EVENT_REGISTERED.value,
                entity_id="evt_player_slay_dragon",
                description="Seeded canonical dragon-slay event.",
                metadata={"seeded": True},
            ),
            CausalityEvent(
                event_id="cevt_seed_2",
                timestamp=now,
                kind=CausalityEventKind.LINK_REGISTERED.value,
                entity_id="link_slay_to_celebrate",
                description="Seeded canonical causal links.",
                metadata={"seeded": True, "link_count": 5},
            ),
            CausalityEvent(
                event_id="cevt_seed_3",
                timestamp=now,
                kind=CausalityEventKind.CHAIN_REGISTERED.value,
                entity_id="chain_kingdom_destiny",
                description="Seeded canonical causal chains.",
                metadata={"seeded": True, "chain_count": 4},
            ),
            CausalityEvent(
                event_id="cevt_seed_4",
                timestamp=now,
                kind=CausalityEventKind.BUTTERFLY_REGISTERED.value,
                entity_id="bf_dragon_slay_collapse",
                description="Seeded canonical butterfly effects.",
                metadata={"seeded": True, "butterfly_count": 3},
            ),
            CausalityEvent(
                event_id="cevt_seed_5",
                timestamp=now,
                kind=CausalityEventKind.PREDICTION_GENERATED.value,
                entity_id="pred_war_aftermath",
                description="Seeded canonical consequence predictions.",
                metadata={"seeded": True, "prediction_count": 3},
            ),
            CausalityEvent(
                event_id="cevt_seed_6",
                timestamp=now,
                kind=CausalityEventKind.CONSISTENCY_CHECKED.value,
                entity_id="report_kingdom_destiny",
                description="Seeded canonical consistency reports.",
                metadata={"seeded": True, "report_count": 2},
            ),
            CausalityEvent(
                event_id="cevt_seed_7",
                timestamp=now,
                kind=CausalityEventKind.SYSTEM_RESET.value,
                entity_id="",
                description="Causality graph initialized with canonical "
                            "dataset.",
                metadata={
                    "seeded": True,
                    "events": 6,
                    "links": 5,
                    "chains": 4,
                    "butterfly_effects": 3,
                    "predictions": 3,
                    "reports": 2,
                },
            ),
        ]
        for event in seed_log:
            self._events_log.append(event)


# ---------------------------------------------------------------------------
# Module-Level Factory Function
# ---------------------------------------------------------------------------


def get_causality_graph() -> _CausalityGraphEngine:
    """Return the singleton causality graph engine.

    Uses module-level double-checked locking so that concurrent first-call
    access creates exactly one engine instance and seeds it exactly once.
    """
    global _INSTANCE
    if _INSTANCE is None:
        with _LOCK:
            if _INSTANCE is None:
                _INSTANCE = _CausalityGraphEngine()
                _INSTANCE.initialize()
    return _INSTANCE


__all__ = [
    # Enums
    "EventCategory",
    "CausalStrength",
    "ChainStatus",
    "ButterflyImpact",
    "CausalityEventKind",
    # Data classes
    "CausalityConfig",
    "CausalEvent",
    "CausalLink",
    "CausalChain",
    "ButterflyEffect",
    "ConsequencePrediction",
    "ConsistencyReport",
    "CausalityStats",
    "CausalitySnapshot",
    "CausalityEvent",
    # Engine class and factory
    "_CausalityGraphEngine",
    "get_causality_graph",
]
