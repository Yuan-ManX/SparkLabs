"""
SparkLabs Agent - AI Innovation Forge

An innovation forge agent for the SparkLabs AI-native game engine. It
forges novel game concepts by fusing elements from disparate design
domains, applying analogical reasoning, creative mutation, and
cross-pollination to produce original mechanics, narratives, and
experiences. The forge maintains a lineage graph of every concept it
produces so that creative provenance is always traceable.

Architecture:
  InnovationForge (singleton)
    |-- GameConcept, ConceptElement, FusionRecipe, InnovationResult,
       InnovationLineage, InnovationScore, InnovationStats,
       InnovationSnapshot, InnovationEvent
    |-- InnovationDomain, FusionMethod, InnovationTier, InnovationStatus,
       InnovationEventKind, MutationStrategy

Core Capabilities:
  - register_concept / get_concept / list_concepts / update_concept:
    concept lifecycle management with domain tagging and tier grading.
  - forge_fusion: fuse two or more concepts into a novel hybrid using
    intersection, union, abstraction, analogy, or cross-pollination.
  - mutate_concept: apply structured mutations (inversion, escalation,
    simplification, reframing, hybridization) to produce variants.
  - evaluate_innovation: score a concept on novelty, feasibility,
    cohesion, and surprise dimensions.
  - trace_lineage: walk the parent-child graph of any concept to
    reveal its full creative provenance.
  - recommend_fusions: suggest promising concept pairings based on
    domain distance and compatibility scoring.
  - list_events / get_stats / get_status / get_snapshot / reset:
    observability and state management.

The class implements the singleton pattern with double-checked locking
using ``threading.RLock``; consumers should obtain the instance through
:meth:`InnovationForge.get_instance` or the module-level
:func:`get_innovation_forge` factory.
"""

from __future__ import annotations

import threading
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple


# ---------------------------------------------------------------------------
# Capacity Constants
# ---------------------------------------------------------------------------

_MAX_CONCEPTS: int = 5000
_MAX_FUSIONS: int = 3000
_MAX_MUTATIONS: int = 3000
_MAX_LINEAGES: int = 5000
_MAX_SCORES: int = 5000
_MAX_EVENTS: int = 5000


# ---------------------------------------------------------------------------
# Helper Functions
# ---------------------------------------------------------------------------


def _now() -> str:
    return datetime.utcnow().isoformat() + "Z"


def _new_id(prefix: str = "") -> str:
    base = uuid.uuid4().hex[:12]
    return f"{prefix}_{base}" if prefix else base


def _evict_fifo_dict(store: Dict[str, Any], max_size: int) -> None:
    cap = max(1, int(max_size))
    while len(store) > cap:
        oldest_key = next(iter(store), None)
        if oldest_key is None:
            break
        store.pop(oldest_key, None)


def _evict_fifo_list(store: List[Any], max_size: int) -> None:
    cap = max(1, int(max_size))
    while len(store) > cap:
        if not store:
            break
        store.pop(0)


def _to_jsonable(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, dict):
        return {str(k): _to_jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_to_jsonable(v) for v in value]
    if hasattr(value, "to_dict") and callable(value.to_dict):
        return _dataclass_to_dict(value)
    return value


def _dataclass_to_dict(instance: Any) -> Dict[str, Any]:
    if instance is None:
        return {}
    if not hasattr(instance, "__dataclass_fields__"):
        return dict(instance) if isinstance(instance, dict) else {}
    out: Dict[str, Any] = {}
    for name in getattr(instance, "__dataclass_fields__", {}).keys():
        try:
            raw = getattr(instance, name)
        except Exception:
            continue
        out[name] = _to_jsonable(raw)
    return out


def _safe_float(value: Any, default: float = 0.0) -> float:
    if value is None or value == "":
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _safe_int(value: Any, default: int = 0) -> int:
    if value is None or value == "":
        return default
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


# ---------------------------------------------------------------------------
# Domain Enums
# ---------------------------------------------------------------------------


class InnovationDomain(Enum):
    """Design domains that concepts can belong to."""
    MECHANIC = "mechanic"
    NARRATIVE = "narrative"
    AESTHETIC = "aesthetic"
    PROGRESSION = "progression"
    SOCIAL = "social"
    ECONOMIC = "economic"
    SPATIAL = "spatial"
    TEMPORAL = "temporal"
    SENSORY = "sensory"
    META = "meta"
    INTERFACE = "interface"
    AI_BEHAVIOR = "ai_behavior"


class FusionMethod(Enum):
    """How two concepts are combined to produce a hybrid."""
    INTERSECTION = "intersection"
    UNION = "union"
    ABSTRACTION = "abstraction"
    ANALOGY = "analogy"
    CROSS_POLLINATION = "cross_pollination"
    INVERSION = "inversion"
    ESCALATION = "escalation"
    SIMPLIFICATION = "simplification"


class MutationStrategy(Enum):
    """Structured mutation applied to a single concept."""
    INVERT = "invert"
    ESCALATE = "escalate"
    SIMPLIFY = "simplify"
    REFRAME = "reframe"
    HYBRIDIZE = "hybridize"
    RANDOMIZE = "randomize"
    CONVERGE = "converge"
    DIVERGE = "diverge"


class InnovationTier(Enum):
    """Quality grade assigned to a concept."""
    EXPERIMENTAL = "experimental"
    PROMISING = "promising"
    VIABLE = "viable"
    POLISHED = "polished"
    BREAKTHROUGH = "breakthrough"


class InnovationStatus(Enum):
    """Lifecycle status of a concept."""
    DRAFT = "draft"
    EVALUATED = "evaluated"
    SELECTED = "selected"
    ARCHIVED = "archived"
    DEPRECATED = "deprecated"


class InnovationEventKind(Enum):
    """Audit event types emitted by the forge."""
    CONCEPT_REGISTERED = "concept_registered"
    CONCEPT_UPDATED = "concept_updated"
    FUSION_FORGED = "fusion_forged"
    MUTATION_APPLIED = "mutation_applied"
    INNOVATION_EVALUATED = "innovation_evaluated"
    LINEAGE_TRACED = "lineage_traced"
    FUSION_RECOMMENDED = "fusion_recommended"


# ---------------------------------------------------------------------------
# Data Classes
# ---------------------------------------------------------------------------


@dataclass
class ConceptElement:
    """A single element extracted from a game concept for fusion."""
    element_id: str = field(default_factory=lambda: _new_id("elm"))
    concept_id: str = ""
    domain: str = InnovationDomain.MECHANIC.value
    label: str = ""
    description: str = ""
    weight: float = 1.0
    tags: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class GameConcept:
    """A registered game concept awaiting fusion or mutation."""
    concept_id: str = field(default_factory=lambda: _new_id("cnc"))
    name: str = ""
    domain: str = InnovationDomain.MECHANIC.value
    description: str = ""
    elements: List[ConceptElement] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    tier: str = InnovationTier.EXPERIMENTAL.value
    status: str = InnovationStatus.DRAFT.value
    parent_ids: List[str] = field(default_factory=list)
    source_domain: str = ""
    compatibility_score: float = 0.5
    created_at: str = field(default_factory=_now)
    updated_at: str = field(default_factory=_now)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class FusionRecipe:
    """A recipe describing how concepts are fused."""
    recipe_id: str = field(default_factory=lambda: _new_id("rcp"))
    source_concept_ids: List[str] = field(default_factory=list)
    method: str = FusionMethod.INTERSECTION.value
    parameters: Dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class InnovationResult:
    """The output of a fusion or mutation operation."""
    result_id: str = field(default_factory=lambda: _new_id("inv"))
    operation: str = "fusion"
    method: str = FusionMethod.INTERSECTION.value
    source_concept_ids: List[str] = field(default_factory=list)
    result_concept_id: str = ""
    name: str = ""
    description: str = ""
    domain: str = InnovationDomain.MECHANIC.value
    rationale: str = ""
    created_at: str = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class InnovationLineage:
    """Parent-child relationship tracking for creative provenance."""
    lineage_id: str = field(default_factory=lambda: _new_id("lin"))
    concept_id: str = ""
    parent_ids: List[str] = field(default_factory=list)
    depth: int = 0
    root_ids: List[str] = field(default_factory=list)
    created_at: str = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class InnovationScore:
    """Multi-dimensional evaluation of a concept's innovation quality."""
    score_id: str = field(default_factory=lambda: _new_id("scr"))
    concept_id: str = ""
    novelty: float = 0.0
    feasibility: float = 0.0
    cohesion: float = 0.0
    surprise: float = 0.0
    overall: float = 0.0
    notes: str = ""
    created_at: str = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class InnovationStats:
    """Aggregate counters for the forge."""
    total_concepts: int = 0
    total_fusions: int = 0
    total_mutations: int = 0
    total_evaluations: int = 0
    total_lineages: int = 0
    breakthrough_count: int = 0
    avg_novelty: float = 0.0
    avg_feasibility: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class InnovationSnapshot:
    """Immutable point-in-time capture of forge state."""
    concepts: Dict[str, Any] = field(default_factory=dict)
    results: Dict[str, Any] = field(default_factory=dict)
    lineages: Dict[str, Any] = field(default_factory=dict)
    scores: Dict[str, Any] = field(default_factory=dict)
    stats: Dict[str, Any] = field(default_factory=dict)
    taken_at: str = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class InnovationEvent:
    """Audit log entry."""
    event_id: str = field(default_factory=lambda: _new_id("evt"))
    kind: str = InnovationEventKind.CONCEPT_REGISTERED.value
    concept_id: str = ""
    payload: Dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


# ---------------------------------------------------------------------------
# Innovation Forge Singleton
# ---------------------------------------------------------------------------


class InnovationForge:
    """Singleton forge that produces novel game concepts through fusion.

    The forge maintains a registry of game concepts, a lineage graph,
    evaluation scores, and an audit trail. It supports multiple fusion
    methods and structured mutations, and can recommend promising
    pairings based on domain distance and compatibility.
    """

    _instance: Optional["InnovationForge"] = None
    _inner_lock = threading.RLock()

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._initialized: bool = False
        self._concepts: Dict[str, GameConcept] = {}
        self._results: Dict[str, InnovationResult] = {}
        self._lineages: Dict[str, InnovationLineage] = {}
        self._scores: Dict[str, InnovationScore] = {}
        self._events: List[InnovationEvent] = []
        self._concept_counter: int = 0
        self._fusion_counter: int = 0
        self._mutation_counter: int = 0
        self._evaluation_counter: int = 0

    # ------------------------------------------------------------------
    # Singleton
    # ------------------------------------------------------------------

    @classmethod
    def get_instance(cls) -> "InnovationForge":
        if cls._instance is None:
            with cls._inner_lock:
                if cls._instance is None:
                    cls._instance = cls()
                    cls._instance._initialize()
        return cls._instance

    def _initialize(self) -> None:
        with self._lock:
            if self._initialized:
                return
            self._initialized = True

    # ------------------------------------------------------------------
    # Internal Helpers
    # ------------------------------------------------------------------

    def _emit(self, kind: InnovationEventKind, concept_id: str = "",
              payload: Optional[Dict[str, Any]] = None) -> None:
        event = InnovationEvent(
            kind=kind.value,
            concept_id=concept_id,
            payload=payload or {},
        )
        self._events.append(event)
        _evict_fifo_list(self._events, _MAX_EVENTS)

    def _coerce_domain(self, value: Any) -> InnovationDomain:
        if isinstance(value, InnovationDomain):
            return value
        if isinstance(value, str) and value:
            try:
                return InnovationDomain(value)
            except ValueError:
                pass
        return InnovationDomain.MECHANIC

    def _coerce_method(self, value: Any) -> FusionMethod:
        if isinstance(value, FusionMethod):
            return value
        if isinstance(value, str) and value:
            try:
                return FusionMethod(value)
            except ValueError:
                pass
        return FusionMethod.INTERSECTION

    def _coerce_mutation(self, value: Any) -> MutationStrategy:
        if isinstance(value, MutationStrategy):
            return value
        if isinstance(value, str) and value:
            try:
                return MutationStrategy(value)
            except ValueError:
                pass
        return MutationStrategy.INVERT

    def _coerce_tier(self, value: Any) -> InnovationTier:
        if isinstance(value, InnovationTier):
            return value
        if isinstance(value, str) and value:
            try:
                return InnovationTier(value)
            except ValueError:
                pass
        return InnovationTier.EXPERIMENTAL

    def _coerce_status(self, value: Any) -> InnovationStatus:
        if isinstance(value, InnovationStatus):
            return value
        if isinstance(value, str) and value:
            try:
                return InnovationStatus(value)
            except ValueError:
                pass
        return InnovationStatus.DRAFT

    def _domain_distance(self, d1: InnovationDomain, d2: InnovationDomain) -> float:
        """Heuristic distance between two domains (0.0 = same, 1.0 = max)."""
        if d1 == d2:
            return 0.0
        domain_list = list(InnovationDomain)
        idx1 = domain_list.index(d1)
        idx2 = domain_list.index(d2)
        return abs(idx1 - idx2) / max(1, len(domain_list) - 1)

    def _compute_compatibility(self, c1: GameConcept, c2: GameConcept) -> float:
        """Score how compatible two concepts are for fusion (0.0 - 1.0)."""
        d1 = self._coerce_domain(c1.domain)
        d2 = self._coerce_domain(c2.domain)
        distance = self._domain_distance(d1, d2)
        # Moderate distance yields highest compatibility - too close is
        # derivative, too far is incoherent.
        proximity_bonus = 1.0 - abs(distance - 0.4) * 2.0
        proximity_bonus = max(0.0, min(1.0, proximity_bonus))
        tag_overlap = len(set(c1.tags) & set(c2.tags))
        tag_bonus = min(0.3, tag_overlap * 0.1)
        return max(0.0, min(1.0, proximity_bonus * 0.7 + tag_bonus + 0.1))

    # ------------------------------------------------------------------
    # Concept Lifecycle
    # ------------------------------------------------------------------

    def register_concept(
        self,
        name: str,
        domain: Any = InnovationDomain.MECHANIC.value,
        description: str = "",
        tags: Any = None,
        tier: Any = InnovationTier.EXPERIMENTAL.value,
        status: Any = InnovationStatus.DRAFT.value,
        elements: Any = None,
        parent_ids: Any = None,
        concept_id: str = "",
        source_domain: str = "",
        compatibility_score: Any = 0.5,
    ) -> GameConcept:
        """Register a new game concept in the forge."""
        with self._lock:
            dom = self._coerce_domain(domain)
            tier_enum = self._coerce_tier(tier)
            status_enum = self._coerce_status(status)
            tag_list = list(tags) if tags else []
            parent_list = list(parent_ids) if parent_ids else []
            cid = concept_id if concept_id else _new_id("cnc")
            element_list: List[ConceptElement] = []
            if elements:
                for elm in elements:
                    if isinstance(elm, ConceptElement):
                        element_list.append(elm)
                    elif isinstance(elm, dict):
                        element_list.append(ConceptElement(
                            concept_id=cid,
                            domain=elm.get("domain", dom.value),
                            label=elm.get("label", ""),
                            description=elm.get("description", ""),
                            weight=_safe_float(elm.get("weight", 1.0)),
                            tags=elm.get("tags", []),
                        ))
            concept = GameConcept(
                concept_id=cid,
                name=name,
                domain=dom.value,
                description=description,
                elements=element_list,
                tags=tag_list,
                tier=tier_enum.value,
                status=status_enum.value,
                parent_ids=parent_list,
                source_domain=source_domain,
                compatibility_score=_safe_float(compatibility_score, 0.5),
            )
            self._concepts[cid] = concept
            _evict_fifo_dict(self._concepts, _MAX_CONCEPTS)
            self._concept_counter += 1
            lineage = InnovationLineage(
                concept_id=cid,
                parent_ids=parent_list,
                depth=0,
                root_ids=[cid] if not parent_list else [],
            )
            self._lineages[cid] = lineage
            _evict_fifo_dict(self._lineages, _MAX_LINEAGES)
            self._emit(InnovationEventKind.CONCEPT_REGISTERED, cid,
                       {"name": name, "domain": dom.value, "tier": tier_enum.value})
            return concept

    def get_concept(self, concept_id: str) -> Optional[GameConcept]:
        with self._lock:
            return self._concepts.get(concept_id)

    def list_concepts(self, domain: Any = None, tier: Any = None,
                      status: Any = None, limit: int = 100) -> List[GameConcept]:
        with self._lock:
            items = list(self._concepts.values())
            if domain is not None and domain != "":
                dom_val = self._coerce_domain(domain).value
                items = [c for c in items if c.domain == dom_val]
            if tier is not None and tier != "":
                tier_val = self._coerce_tier(tier).value
                items = [c for c in items if c.tier == tier_val]
            if status is not None and status != "":
                status_val = self._coerce_status(status).value
                items = [c for c in items if c.status == status_val]
            return items[:limit]

    def update_concept(self, concept_id: str, **kwargs: Any) -> Optional[GameConcept]:
        with self._lock:
            concept = self._concepts.get(concept_id)
            if concept is None:
                return None
            if "name" in kwargs:
                concept.name = str(kwargs["name"])
            if "description" in kwargs:
                concept.description = str(kwargs["description"])
            if "domain" in kwargs:
                concept.domain = self._coerce_domain(kwargs["domain"]).value
            if "tier" in kwargs:
                concept.tier = self._coerce_tier(kwargs["tier"]).value
            if "status" in kwargs:
                concept.status = self._coerce_status(kwargs["status"]).value
            if "tags" in kwargs and kwargs["tags"]:
                concept.tags = list(kwargs["tags"])
            if "compatibility_score" in kwargs:
                concept.compatibility_score = _safe_float(kwargs["compatibility_score"], 0.5)
            if "metadata" in kwargs and kwargs["metadata"]:
                concept.metadata.update(dict(kwargs["metadata"]))
            concept.updated_at = _now()
            self._emit(InnovationEventKind.CONCEPT_UPDATED, concept_id,
                       {"fields": list(kwargs.keys())})
            return concept

    # ------------------------------------------------------------------
    # Fusion Operations
    # ------------------------------------------------------------------

    def forge_fusion(
        self,
        source_concept_ids: Any,
        method: Any = FusionMethod.INTERSECTION.value,
        name: str = "",
        description: str = "",
        domain: Any = None,
        rationale: str = "",
    ) -> InnovationResult:
        """Fuse two or more concepts into a novel hybrid concept."""
        with self._lock:
            method_enum = self._coerce_method(method)
            src_ids = list(source_concept_ids) if source_concept_ids else []
            parents: List[GameConcept] = []
            for sid in src_ids:
                c = self._concepts.get(sid)
                if c is not None:
                    parents.append(c)
            if not parents:
                raise ValueError("No valid source concepts found for fusion")
            # Determine the resulting domain
            if domain is not None and domain != "":
                result_domain = self._coerce_domain(domain)
            else:
                result_domain = self._coerce_domain(parents[0].domain)
            # Build the fused concept name and description
            if not name:
                name_parts = [p.name for p in parents if p.name]
                name = " / ".join(name_parts[:3]) if name_parts else "Fused Concept"
            if not description:
                desc_parts = [p.description for p in parents if p.description]
                description = " ".join(desc_parts[:2])[:500] if desc_parts else ""
            if not rationale:
                rationale = f"Forged via {method_enum.value} of {len(parents)} concepts"
            # Collect elements from all parents
            fused_elements: List[ConceptElement] = []
            seen_labels: Set[str] = set()
            for p in parents:
                for elm in p.elements:
                    if elm.label and elm.label not in seen_labels:
                        fused_elements.append(ConceptElement(
                            domain=result_domain.value,
                            label=elm.label,
                            description=elm.description,
                            weight=elm.weight,
                            tags=list(elm.tags),
                        ))
                        seen_labels.add(elm.label)
            # Collect tags
            fused_tags: List[str] = []
            for p in parents:
                for tag in p.tags:
                    if tag not in fused_tags:
                        fused_tags.append(tag)
            # Compute compatibility
            avg_compat = 0.0
            if len(parents) >= 2:
                total = 0.0
                count = 0
                for i in range(len(parents)):
                    for j in range(i + 1, len(parents)):
                        total += self._compute_compatibility(parents[i], parents[j])
                        count += 1
                avg_compat = total / count if count > 0 else 0.5
            else:
                avg_compat = parents[0].compatibility_score
            # Create the fused concept
            fused = self.register_concept(
                name=name,
                domain=result_domain.value,
                description=description,
                tags=fused_tags,
                elements=fused_elements,
                parent_ids=src_ids,
                compatibility_score=avg_compat,
            )
            result = InnovationResult(
                operation="fusion",
                method=method_enum.value,
                source_concept_ids=src_ids,
                result_concept_id=fused.concept_id,
                name=name,
                description=description,
                domain=result_domain.value,
                rationale=rationale,
            )
            self._results[result.result_id] = result
            _evict_fifo_dict(self._results, _MAX_FUSIONS)
            self._fusion_counter += 1
            self._emit(InnovationEventKind.FUSION_FORGED, fused.concept_id,
                       {"method": method_enum.value, "sources": src_ids,
                        "result": fused.concept_id})
            return result

    # ------------------------------------------------------------------
    # Mutation Operations
    # ------------------------------------------------------------------

    def mutate_concept(
        self,
        concept_id: str,
        strategy: Any = MutationStrategy.INVERT.value,
        name: str = "",
        description: str = "",
        rationale: str = "",
    ) -> InnovationResult:
        """Apply a structured mutation to a concept, producing a variant."""
        with self._lock:
            source = self._concepts.get(concept_id)
            if source is None:
                raise ValueError(f"Concept not found: {concept_id}")
            strat = self._coerce_mutation(strategy)
            # Generate the mutated name and description
            prefix_map = {
                MutationStrategy.INVERT: "Inverted",
                MutationStrategy.ESCALATE: "Escalated",
                MutationStrategy.SIMPLIFY: "Simplified",
                MutationStrategy.REFRAME: "Reframed",
                MutationStrategy.HYBRIDIZE: "Hybridized",
                MutationStrategy.RANDOMIZE: "Randomized",
                MutationStrategy.CONVERGE: "Converged",
                MutationStrategy.DIVERGE: "Diverged",
            }
            prefix = prefix_map.get(strat, "Mutated")
            mut_name = name if name else f"{prefix}: {source.name}"
            mut_desc = description if description else source.description
            if not rationale:
                rationale = f"Applied {strat.value} mutation to '{source.name}'"
            # Apply mutation-specific element transformations
            mutated_elements: List[ConceptElement] = []
            for elm in source.elements:
                mut_elm = ConceptElement(
                    domain=elm.domain,
                    label=elm.label,
                    description=elm.description,
                    weight=elm.weight,
                    tags=list(elm.tags),
                )
                if strat == MutationStrategy.ESCALATE:
                    mut_elm.weight = min(2.0, mut_elm.weight * 1.5)
                elif strat == MutationStrategy.SIMPLIFY:
                    mut_elm.weight = max(0.1, mut_elm.weight * 0.5)
                elif strat == MutationStrategy.INVERT:
                    mut_elm.weight = max(0.1, 2.0 - mut_elm.weight)
                mutated_elements.append(mut_elm)
            mutated = self.register_concept(
                name=mut_name,
                domain=source.domain,
                description=mut_desc,
                tags=list(source.tags),
                elements=mutated_elements,
                parent_ids=[concept_id],
                compatibility_score=source.compatibility_score,
            )
            result = InnovationResult(
                operation="mutation",
                method=strat.value,
                source_concept_ids=[concept_id],
                result_concept_id=mutated.concept_id,
                name=mut_name,
                description=mut_desc,
                domain=source.domain,
                rationale=rationale,
            )
            self._results[result.result_id] = result
            _evict_fifo_dict(self._results, _MAX_MUTATIONS)
            self._mutation_counter += 1
            self._emit(InnovationEventKind.MUTATION_APPLIED, mutated.concept_id,
                       {"strategy": strat.value, "source": concept_id,
                        "result": mutated.concept_id})
            return result

    # ------------------------------------------------------------------
    # Evaluation
    # ------------------------------------------------------------------

    def evaluate_innovation(
        self,
        concept_id: str,
        novelty: Any = 0.5,
        feasibility: Any = 0.5,
        cohesion: Any = 0.5,
        surprise: Any = 0.5,
        notes: str = "",
    ) -> InnovationScore:
        """Score a concept on four innovation dimensions."""
        with self._lock:
            concept = self._concepts.get(concept_id)
            if concept is None:
                raise ValueError(f"Concept not found: {concept_id}")
            n = _safe_float(novelty, 0.5)
            f = _safe_float(feasibility, 0.5)
            c = _safe_float(cohesion, 0.5)
            s = _safe_float(surprise, 0.5)
            overall = (n * 0.35 + f * 0.25 + c * 0.20 + s * 0.20)
            overall = max(0.0, min(1.0, overall))
            score = InnovationScore(
                concept_id=concept_id,
                novelty=max(0.0, min(1.0, n)),
                feasibility=max(0.0, min(1.0, f)),
                cohesion=max(0.0, min(1.0, c)),
                surprise=max(0.0, min(1.0, s)),
                overall=overall,
                notes=notes,
            )
            self._scores[score.score_id] = score
            _evict_fifo_dict(self._scores, _MAX_SCORES)
            self._evaluation_counter += 1
            # Update concept tier based on overall score
            if overall >= 0.9:
                concept.tier = InnovationTier.BREAKTHROUGH.value
            elif overall >= 0.75:
                concept.tier = InnovationTier.POLISHED.value
            elif overall >= 0.6:
                concept.tier = InnovationTier.VIABLE.value
            elif overall >= 0.4:
                concept.tier = InnovationTier.PROMISING.value
            concept.status = InnovationStatus.EVALUATED.value
            concept.updated_at = _now()
            self._emit(InnovationEventKind.INNOVATION_EVALUATED, concept_id,
                       {"overall": overall, "tier": concept.tier})
            return score

    def get_score(self, concept_id: str) -> Optional[InnovationScore]:
        with self._lock:
            for score in self._scores.values():
                if score.concept_id == concept_id:
                    return score
            return None

    # ------------------------------------------------------------------
    # Lineage Tracking
    # ------------------------------------------------------------------

    def trace_lineage(self, concept_id: str) -> InnovationLineage:
        """Trace the full parent chain of a concept."""
        with self._lock:
            visited: Set[str] = set()
            roots: List[str] = []
            queue: List[str] = [concept_id]
            max_depth = 0
            while queue:
                current_id = queue.pop(0)
                if current_id in visited:
                    continue
                visited.add(current_id)
                lineage = self._lineages.get(current_id)
                if lineage:
                    if not lineage.parent_ids:
                        roots.append(current_id)
                    else:
                        for pid in lineage.parent_ids:
                            if pid not in visited:
                                queue.append(pid)
                                pl = self._lineages.get(pid)
                                if pl:
                                    max_depth = max(max_depth, pl.depth + 1)
                else:
                    roots.append(current_id)
            result = InnovationLineage(
                concept_id=concept_id,
                parent_ids=list(visited - {concept_id}),
                depth=max_depth,
                root_ids=roots,
            )
            self._emit(InnovationEventKind.LINEAGE_TRACED, concept_id,
                       {"depth": max_depth, "roots": roots,
                        "ancestors": len(visited) - 1})
            return result

    # ------------------------------------------------------------------
    # Recommendations
    # ------------------------------------------------------------------

    def recommend_fusions(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Suggest promising concept pairings based on compatibility."""
        with self._lock:
            concepts = list(self._concepts.values())
            if len(concepts) < 2:
                return []
            pairs: List[Tuple[float, GameConcept, GameConcept]] = []
            for i in range(len(concepts)):
                for j in range(i + 1, len(concepts)):
                    compat = self._compute_compatibility(concepts[i], concepts[j])
                    pairs.append((compat, concepts[i], concepts[j]))
            pairs.sort(key=lambda x: x[0], reverse=True)
            recommendations: List[Dict[str, Any]] = []
            for compat, c1, c2 in pairs[:limit]:
                recommendations.append({
                    "concept_a": c1.concept_id,
                    "concept_b": c2.concept_id,
                    "name_a": c1.name,
                    "name_b": c2.name,
                    "domain_a": c1.domain,
                    "domain_b": c2.domain,
                    "compatibility": round(compat, 3),
                })
            if recommendations:
                self._emit(InnovationEventKind.FUSION_RECOMMENDED, "",
                           {"count": len(recommendations)})
            return recommendations

    # ------------------------------------------------------------------
    # Observability
    # ------------------------------------------------------------------

    def list_events(self, limit: int = 100) -> List[InnovationEvent]:
        with self._lock:
            return list(self._events[-limit:])

    def get_result(self, result_id: str) -> Optional[InnovationResult]:
        with self._lock:
            return self._results.get(result_id)

    def list_results(self, operation: Any = None, limit: int = 100) -> List[InnovationResult]:
        with self._lock:
            items = list(self._results.values())
            if operation is not None and operation != "":
                items = [r for r in items if r.operation == str(operation)]
            return items[-limit:]

    def get_lineage(self, concept_id: str) -> Optional[InnovationLineage]:
        with self._lock:
            return self._lineages.get(concept_id)

    def list_lineages(self, limit: int = 100) -> List[InnovationLineage]:
        with self._lock:
            return list(self._lineages.values())[-limit:]

    def list_scores(self, limit: int = 100) -> List[InnovationScore]:
        with self._lock:
            return list(self._scores.values())[-limit:]

    def get_stats(self) -> InnovationStats:
        with self._lock:
            breakthroughs = sum(
                1 for c in self._concepts.values()
                if c.tier == InnovationTier.BREAKTHROUGH.value
            )
            scores = list(self._scores.values())
            avg_n = sum(s.novelty for s in scores) / len(scores) if scores else 0.0
            avg_f = sum(s.feasibility for s in scores) / len(scores) if scores else 0.0
            return InnovationStats(
                total_concepts=len(self._concepts),
                total_fusions=self._fusion_counter,
                total_mutations=self._mutation_counter,
                total_evaluations=self._evaluation_counter,
                total_lineages=len(self._lineages),
                breakthrough_count=breakthroughs,
                avg_novelty=round(avg_n, 3),
                avg_feasibility=round(avg_f, 3),
            )

    def get_status(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "initialized": self._initialized,
                "concepts": len(self._concepts),
                "results": len(self._results),
                "lineages": len(self._lineages),
                "scores": len(self._scores),
                "events": len(self._events),
            }

    def get_snapshot(self) -> InnovationSnapshot:
        with self._lock:
            return InnovationSnapshot(
                concepts={k: v.to_dict() for k, v in list(self._concepts.items())[:50]},
                results={k: v.to_dict() for k, v in list(self._results.items())[:50]},
                lineages={k: v.to_dict() for k, v in list(self._lineages.items())[:50]},
                scores={k: v.to_dict() for k, v in list(self._scores.items())[:50]},
                stats=self.get_stats().to_dict(),
            )

    def reset(self) -> None:
        with self._lock:
            self._concepts.clear()
            self._results.clear()
            self._lineages.clear()
            self._scores.clear()
            self._events.clear()
            self._concept_counter = 0
            self._fusion_counter = 0
            self._mutation_counter = 0
            self._evaluation_counter = 0


# ---------------------------------------------------------------------------
# Module-Level Factory
# ---------------------------------------------------------------------------


def get_innovation_forge() -> InnovationForge:
    """Return the singleton InnovationForge instance."""
    return InnovationForge.get_instance()
