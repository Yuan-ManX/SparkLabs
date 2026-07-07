"""
SparkLabs Agent - AI Knowledge Synthesis and Cross-Domain Concept Fusion

A knowledge synthesis agent for the SparkLabs AI-native game engine. It
maintains a graph of game-development concepts spanning many domains,
fuses concepts across domain boundaries, draws inferences over concept
premises, explores domains, discovers patterns, and answers
natural-language questions over the concept graph.

Architecture:
  KnowledgeSynthesis (singleton)
    |-- KnowledgeConcept, ConceptRelation, SynthesisResult,
       InferenceChain, DomainMap, InsightRecord, KnowledgeQuery,
       KnowledgeStats, KnowledgeSnapshot, KnowledgeEvent
    |-- KnowledgeDomain, ConceptTier, SynthesisMethod, InferenceType,
       RelationKind, ConfidenceLevel, KnowledgeEventKind

Core Capabilities:
  - create_concept / get_concept / list_concepts / update_concept /
    merge_concepts: concept lifecycle and merging.
  - add_relation / get_relation / list_relations: concept graph edges.
  - synthesize / get_synthesis / list_syntheses: cross-domain concept
    fusion with multiple synthesis methods.
  - draw_inference / get_inference / list_inferences: inference chains
    built from concept premises.
  - explore_domain / get_domain_map / list_domain_maps: domain-scoped
    exploration and mapping.
  - discover_pattern / get_insight / list_insights: pattern discovery
    and insight records.
  - query / get_query / list_queries: natural-language question
    answering over the concept graph.
  - list_events / get_stats / get_status / get_snapshot / reset:
    observability and state management.

The class implements the singleton pattern with double-checked locking
using ``threading.RLock``; consumers should obtain the instance through
:meth:`KnowledgeSynthesis.get_instance` or the module-level
:func:`get_knowledge_synthesis` factory.
"""

from __future__ import annotations

import threading
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Set


# ---------------------------------------------------------------------------
# Capacity Constants
# ---------------------------------------------------------------------------

_MAX_CONCEPTS: int = 5000
_MAX_RELATIONS: int = 5000
_MAX_SYNTHESES: int = 2000
_MAX_INFERENCES: int = 2000
_MAX_DOMAIN_MAPS: int = 100
_MAX_INSIGHTS: int = 2000
_MAX_QUERIES: int = 5000
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


# ---------------------------------------------------------------------------
# Domain Enums
# ---------------------------------------------------------------------------


class KnowledgeDomain(Enum):
    GAME_DESIGN = "game_design"
    NARRATIVE = "narrative"
    MECHANICS = "mechanics"
    ART_STYLE = "art_style"
    AUDIO = "audio"
    PROGRAMMING = "programming"
    LEVEL_DESIGN = "level_design"
    CHARACTER = "character"
    ECONOMY = "economy"
    MULTIPLAYER = "multiplayer"
    UI_UX = "ui_ux"
    MONETIZATION = "monetization"
    ACCESSIBILITY = "accessibility"
    PERFORMANCE = "performance"
    TESTING = "testing"


class ConceptTier(Enum):
    PRIMITIVE = "primitive"
    COMPOSITE = "composite"
    PATTERN = "pattern"
    PRINCIPLE = "principle"
    META_CONCEPT = "meta_concept"


class SynthesisMethod(Enum):
    INTERSECTION = "intersection"
    UNION = "union"
    ABSTRACTION = "abstraction"
    ANALOGY = "analogy"
    MUTATION = "mutation"
    CROSS_POLLINATION = "cross_pollination"
    DISTILLATION = "distillation"
    COMPOSITION = "composition"


class InferenceType(Enum):
    DEDUCTIVE = "deductive"
    INDUCTIVE = "inductive"
    ABDUCTIVE = "abductive"
    ANALOGICAL = "analogical"
    CAUSAL = "causal"


class RelationKind(Enum):
    DEPENDS_ON = "depends_on"
    EXTENDS = "extends"
    CONTRADICTS = "contradicts"
    COMPLEMENTS = "complements"
    SPECIALIZES = "specializes"
    GENERALIZES = "generalizes"
    COMPOSED_OF = "composed_of"
    INSPIRED_BY = "inspired_by"


class ConfidenceLevel(Enum):
    VERY_LOW = "very_low"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    VERY_HIGH = "very_high"


class KnowledgeEventKind(Enum):
    CONCEPT_CREATED = "concept_created"
    CONCEPT_UPDATED = "concept_updated"
    CONCEPT_MERGED = "concept_merged"
    RELATION_ADDED = "relation_added"
    SYNTHESIS_COMPLETED = "synthesis_completed"
    INFERENCE_DRAWN = "inference_drawn"
    DOMAIN_EXPLORED = "domain_explored"
    PATTERN_DISCOVERED = "pattern_discovered"
    QUERY_ANSWERED = "query_answered"
    INSIGHT_GENERATED = "insight_generated"


# ---------------------------------------------------------------------------
# Data Classes
# ---------------------------------------------------------------------------


@dataclass
class KnowledgeConcept:
    """A unit of game-development knowledge belonging to a single domain."""
    concept_id: str
    name: str
    domain: KnowledgeDomain
    tier: ConceptTier
    description: str = ""
    tags: List[str] = field(default_factory=list)
    attributes: Dict[str, Any] = field(default_factory=dict)
    source_domain: str = ""
    confidence: ConfidenceLevel = ConfidenceLevel.MEDIUM
    created_at: str = field(default_factory=_now)
    updated_at: str = field(default_factory=_now)
    usage_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class ConceptRelation:
    """A directed edge linking two KnowledgeConcept nodes."""
    relation_id: str
    source_concept_id: str
    target_concept_id: str
    kind: RelationKind
    strength: float = 0.5
    description: str = ""
    created_at: str = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class SynthesisResult:
    """The outcome of fusing one or more concepts into a new concept."""
    synthesis_id: str
    method: SynthesisMethod
    source_concept_ids: List[str] = field(default_factory=list)
    result_concept_id: str = ""
    description: str = ""
    confidence: ConfidenceLevel = ConfidenceLevel.MEDIUM
    created_at: str = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class InferenceChain:
    """A chain of reasoning from premises to a conclusion concept."""
    chain_id: str
    premise_ids: List[str] = field(default_factory=list)
    conclusion_id: str = ""
    inference_type: InferenceType = InferenceType.DEDUCTIVE
    steps: List[str] = field(default_factory=list)
    confidence: ConfidenceLevel = ConfidenceLevel.MEDIUM
    created_at: str = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class DomainMap:
    """A snapshot of concepts and relations within a single domain."""
    map_id: str
    domain: KnowledgeDomain
    concept_count: int = 0
    relation_count: int = 0
    key_concepts: List[str] = field(default_factory=list)
    coverage_score: float = 0.0
    last_explored: str = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class InsightRecord:
    """A discovered pattern or insight supported by concepts."""
    insight_id: str
    domain: KnowledgeDomain
    description: str = ""
    supporting_concept_ids: List[str] = field(default_factory=list)
    confidence: ConfidenceLevel = ConfidenceLevel.MEDIUM
    impact_score: float = 0.0
    novelty_score: float = 0.0
    created_at: str = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class KnowledgeQuery:
    """A natural-language question and the answer produced over the graph."""
    query_id: str
    question: str
    domain: KnowledgeDomain
    matched_concept_ids: List[str] = field(default_factory=list)
    answer: str = ""
    confidence: ConfidenceLevel = ConfidenceLevel.MEDIUM
    created_at: str = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class KnowledgeStats:
    """Aggregate statistics describing the knowledge graph."""
    total_concepts: int = 0
    total_relations: int = 0
    total_syntheses: int = 0
    total_inferences: int = 0
    total_insights: int = 0
    total_queries: int = 0
    domain_distribution: Dict[str, int] = field(default_factory=dict)
    avg_confidence: float = 0.0
    last_updated: str = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class KnowledgeSnapshot:
    """A point-in-time snapshot of the synthesis engine state."""
    concepts: List[Dict[str, Any]] = field(default_factory=list)
    relations: List[Dict[str, Any]] = field(default_factory=list)
    syntheses: List[Dict[str, Any]] = field(default_factory=list)
    inferences: List[Dict[str, Any]] = field(default_factory=list)
    domain_maps: List[Dict[str, Any]] = field(default_factory=list)
    insights: List[Dict[str, Any]] = field(default_factory=list)
    queries: List[Dict[str, Any]] = field(default_factory=list)
    stats: Dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class KnowledgeEvent:
    """An audit event emitted by the knowledge synthesis engine."""
    event_id: str
    kind: KnowledgeEventKind
    concept_id: str = ""
    timestamp: str = field(default_factory=_now)
    payload: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


# ---------------------------------------------------------------------------
# Knowledge Synthesis Singleton
# ---------------------------------------------------------------------------


class KnowledgeSynthesis:
    """AI knowledge synthesis and cross-domain concept fusion engine.

    Maintains a concept graph, fuses concepts across domains, draws
    inferences, explores domains, discovers patterns, and answers
    natural-language questions. All public methods are guarded by a
    reentrant lock so the engine is safe to call from multiple threads.
    """

    _instance: Optional["KnowledgeSynthesis"] = None
    _inner_lock = threading.RLock()
    _initialized: bool = False

    def __new__(cls) -> "KnowledgeSynthesis":
        if cls._instance is None:
            with cls._inner_lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    @classmethod
    def get_instance(cls) -> "KnowledgeSynthesis":
        return cls()

    def __init__(self) -> None:
        if self._initialized:
            return
        with self._inner_lock:
            if self._initialized:
                return
            self._lock = threading.RLock()
            self._concepts: Dict[str, KnowledgeConcept] = {}
            self._relations: Dict[str, ConceptRelation] = {}
            self._syntheses: Dict[str, SynthesisResult] = {}
            self._inferences: Dict[str, InferenceChain] = {}
            self._domain_maps: Dict[str, DomainMap] = {}
            self._insights: Dict[str, InsightRecord] = {}
            self._queries: Dict[str, KnowledgeQuery] = {}
            self._events: List[KnowledgeEvent] = []
            self._seed_data()
            self._initialized = True

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _emit(
        self,
        kind: KnowledgeEventKind,
        concept_id: str = "",
        payload: Optional[Dict[str, Any]] = None,
    ) -> None:
        event = KnowledgeEvent(
            event_id=_new_id("evt"),
            kind=kind,
            concept_id=concept_id,
            timestamp=_now(),
            payload=payload or {},
        )
        self._events.append(event)
        _evict_fifo_list(self._events, _MAX_EVENTS)

    @staticmethod
    def _coerce_domain(value: Any) -> KnowledgeDomain:
        if isinstance(value, KnowledgeDomain):
            return value
        if isinstance(value, str):
            for d in KnowledgeDomain:
                if d.value == value:
                    return d
        return KnowledgeDomain.GAME_DESIGN

    @staticmethod
    def _coerce_tier(value: Any) -> ConceptTier:
        if isinstance(value, ConceptTier):
            return value
        if isinstance(value, str):
            for t in ConceptTier:
                if t.value == value:
                    return t
        return ConceptTier.PRIMITIVE

    @staticmethod
    def _coerce_confidence(value: Any) -> ConfidenceLevel:
        if isinstance(value, ConfidenceLevel):
            return value
        if isinstance(value, str):
            for c in ConfidenceLevel:
                if c.value == value:
                    return c
        return ConfidenceLevel.MEDIUM

    @staticmethod
    def _coerce_method(value: Any) -> SynthesisMethod:
        if isinstance(value, SynthesisMethod):
            return value
        if isinstance(value, str):
            for m in SynthesisMethod:
                if m.value == value:
                    return m
        return SynthesisMethod.COMPOSITION

    @staticmethod
    def _coerce_inference_type(value: Any) -> InferenceType:
        if isinstance(value, InferenceType):
            return value
        if isinstance(value, str):
            for i in InferenceType:
                if i.value == value:
                    return i
        return InferenceType.DEDUCTIVE

    @staticmethod
    def _coerce_relation_kind(value: Any) -> RelationKind:
        if isinstance(value, RelationKind):
            return value
        if isinstance(value, str):
            for k in RelationKind:
                if k.value == value:
                    return k
        return RelationKind.COMPLEMENTS

    @staticmethod
    def _coerce_event_kind(value: Any) -> Optional[KnowledgeEventKind]:
        if isinstance(value, KnowledgeEventKind):
            return value
        if isinstance(value, str):
            for e in KnowledgeEventKind:
                if e.value == value:
                    return e
        return None

    @staticmethod
    def _conf_rank(confidence: Any) -> int:
        conf = KnowledgeSynthesis._coerce_confidence(confidence)
        return {"very_low": 1, "low": 2, "medium": 3, "high": 4, "very_high": 5}.get(
            conf.value, 3
        )

    @staticmethod
    def _tokenize(text: str) -> Set[str]:
        cleaned = "".join(
            ch.lower() if ch.isalnum() or ch.isspace() else " " for ch in (text or "")
        )
        return {tok for tok in cleaned.split() if len(tok) >= 3}

    @staticmethod
    def _match_score(concept: KnowledgeConcept, question: str, terms: Set[str]) -> float:
        if not terms:
            return 0.0
        name_tokens = KnowledgeSynthesis._tokenize(concept.name)
        desc_tokens = KnowledgeSynthesis._tokenize(concept.description)
        tag_tokens = {t.lower() for t in concept.tags}
        name_overlap = len(terms & name_tokens) / max(1, len(terms))
        desc_overlap = len(terms & desc_tokens) / max(1, len(terms))
        tag_overlap = len(terms & tag_tokens) / max(1, len(terms))
        exact = 0.15 if question.lower() in concept.name.lower() else 0.0
        conf_boost = KnowledgeSynthesis._conf_rank(concept.confidence) * 0.02
        score = (
            name_overlap * 0.45
            + desc_overlap * 0.25
            + tag_overlap * 0.20
            + exact
            + conf_boost
        )
        return round(min(1.0, score), 4)

    def _build_domain_map(self, dom: KnowledgeDomain) -> DomainMap:
        dom_concepts = [c for c in self._concepts.values() if c.domain == dom]
        dom_concept_ids = {c.concept_id for c in dom_concepts}
        dom_relations = [
            r
            for r in self._relations.values()
            if r.source_concept_id in dom_concept_ids
            or r.target_concept_id in dom_concept_ids
        ]
        key = sorted(dom_concepts, key=lambda c: c.usage_count, reverse=True)[:5]
        coverage = round(min(1.0, len(dom_concepts) / 10.0), 4) if dom_concepts else 0.0
        return DomainMap(
            map_id=_new_id("dm"),
            domain=dom,
            concept_count=len(dom_concepts),
            relation_count=len(dom_relations),
            key_concepts=[c.concept_id for c in key],
            coverage_score=coverage,
            last_explored=_now(),
        )

    # ------------------------------------------------------------------
    # Concept Lifecycle
    # ------------------------------------------------------------------

    def create_concept(
        self,
        name: str,
        domain: KnowledgeDomain,
        tier: ConceptTier,
        description: str = "",
        tags: Optional[List[str]] = None,
        attributes: Optional[Dict[str, Any]] = None,
        source_domain: str = "",
        confidence: ConfidenceLevel = ConfidenceLevel.MEDIUM,
    ) -> KnowledgeConcept:
        with self._lock:
            dom = self._coerce_domain(domain)
            tier_val = self._coerce_tier(tier)
            conf = self._coerce_confidence(confidence)
            concept = KnowledgeConcept(
                concept_id=_new_id("c"),
                name=name,
                domain=dom,
                tier=tier_val,
                description=description,
                tags=list(tags) if tags else [],
                attributes=dict(attributes) if attributes else {},
                source_domain=source_domain,
                confidence=conf,
            )
            self._concepts[concept.concept_id] = concept
            _evict_fifo_dict(self._concepts, _MAX_CONCEPTS)
            self._emit(
                KnowledgeEventKind.CONCEPT_CREATED,
                concept_id=concept.concept_id,
                payload={
                    "name": name,
                    "domain": dom.value,
                    "tier": tier_val.value,
                    "confidence": conf.value,
                },
            )
            return concept

    def get_concept(self, concept_id: str) -> Optional[KnowledgeConcept]:
        with self._lock:
            return self._concepts.get(concept_id)

    def list_concepts(
        self,
        domain: Optional[KnowledgeDomain] = None,
        tier: Optional[ConceptTier] = None,
        limit: int = 100,
    ) -> List[KnowledgeConcept]:
        with self._lock:
            items = list(self._concepts.values())
            if domain is not None:
                dom = self._coerce_domain(domain)
                items = [c for c in items if c.domain == dom]
            if tier is not None:
                tier_val = self._coerce_tier(tier)
                items = [c for c in items if c.tier == tier_val]
            return items[-limit:]

    def update_concept(self, concept_id: str, **kwargs: Any) -> Optional[KnowledgeConcept]:
        with self._lock:
            concept = self._concepts.get(concept_id)
            if concept is None:
                return None
            if "name" in kwargs:
                concept.name = str(kwargs["name"])
            if "description" in kwargs:
                concept.description = str(kwargs["description"])
            if "tags" in kwargs:
                concept.tags = list(kwargs["tags"])
            if "attributes" in kwargs:
                concept.attributes = dict(kwargs["attributes"])
            if "source_domain" in kwargs:
                concept.source_domain = str(kwargs["source_domain"])
            if "usage_count" in kwargs:
                concept.usage_count = int(kwargs["usage_count"])
            if "domain" in kwargs:
                concept.domain = self._coerce_domain(kwargs["domain"])
            if "tier" in kwargs:
                concept.tier = self._coerce_tier(kwargs["tier"])
            if "confidence" in kwargs:
                concept.confidence = self._coerce_confidence(kwargs["confidence"])
            concept.updated_at = _now()
            self._emit(
                KnowledgeEventKind.CONCEPT_UPDATED,
                concept_id=concept_id,
                payload={"fields": list(kwargs.keys())},
            )
            return concept

    def merge_concepts(
        self,
        concept_ids: List[str],
        new_name: str,
        new_domain: KnowledgeDomain,
        new_description: str = "",
    ) -> KnowledgeConcept:
        with self._lock:
            dom = self._coerce_domain(new_domain)
            sources = [
                self._concepts[cid]
                for cid in concept_ids
                if cid in self._concepts
            ]
            merged_tags = sorted({t for s in sources for t in s.tags})
            merged_attrs: Dict[str, Any] = {}
            for s in sources:
                merged_attrs.update(s.attributes)
            if sources:
                best_conf = max(
                    (s.confidence for s in sources),
                    key=lambda c: self._conf_rank(c),
                )
            else:
                best_conf = ConfidenceLevel.MEDIUM
            concept = KnowledgeConcept(
                concept_id=_new_id("c"),
                name=new_name,
                domain=dom,
                tier=ConceptTier.COMPOSITE,
                description=new_description,
                tags=merged_tags,
                attributes=merged_attrs,
                source_domain=sources[0].source_domain if sources else "",
                confidence=best_conf,
            )
            self._concepts[concept.concept_id] = concept
            _evict_fifo_dict(self._concepts, _MAX_CONCEPTS)
            # Bump usage of source concepts that fed the merge.
            for s in sources:
                s.usage_count += 1
                s.updated_at = _now()
            self._emit(
                KnowledgeEventKind.CONCEPT_MERGED,
                concept_id=concept.concept_id,
                payload={
                    "source_concept_ids": list(concept_ids),
                    "name": new_name,
                    "domain": dom.value,
                },
            )
            return concept

    # ------------------------------------------------------------------
    # Relations
    # ------------------------------------------------------------------

    def add_relation(
        self,
        source_concept_id: str = "",
        target_concept_id: str = "",
        kind: Any = None,
        strength: Any = 0.5,
        description: str = "",
        source_id: str = "",
        target_id: str = "",
        relation_kind: Any = None,
        confidence: Any = None,
    ) -> ConceptRelation:
        with self._lock:
            src = source_id if source_id else source_concept_id
            tgt = target_id if target_id else target_concept_id
            kind_val_raw = relation_kind if relation_kind is not None else kind
            kind_val = self._coerce_relation_kind(kind_val_raw)
            if confidence is not None and isinstance(confidence, str):
                conf_map = {"high": 0.9, "medium": 0.6, "low": 0.3}
                strength_val = conf_map.get(confidence.lower(), 0.5)
            else:
                try:
                    strength_val = float(strength) if strength else 0.5
                except (TypeError, ValueError):
                    strength_val = 0.5
            rel = ConceptRelation(
                relation_id=_new_id("rel"),
                source_concept_id=src,
                target_concept_id=tgt,
                kind=kind_val,
                strength=strength_val,
                description=description,
            )
            self._relations[rel.relation_id] = rel
            _evict_fifo_dict(self._relations, _MAX_RELATIONS)
            self._emit(
                KnowledgeEventKind.RELATION_ADDED,
                concept_id=source_concept_id,
                payload={
                    "relation_id": rel.relation_id,
                    "target_concept_id": target_concept_id,
                    "kind": kind_val.value,
                    "strength": rel.strength,
                },
            )
            return rel

    def get_relation(self, relation_id: str) -> Optional[ConceptRelation]:
        with self._lock:
            return self._relations.get(relation_id)

    def list_relations(
        self,
        source_concept_id: Optional[str] = None,
        target_concept_id: Optional[str] = None,
        kind: Optional[RelationKind] = None,
        limit: int = 100,
    ) -> List[ConceptRelation]:
        with self._lock:
            items = list(self._relations.values())
            if source_concept_id is not None:
                items = [r for r in items if r.source_concept_id == source_concept_id]
            if target_concept_id is not None:
                items = [r for r in items if r.target_concept_id == target_concept_id]
            if kind is not None:
                kind_val = self._coerce_relation_kind(kind)
                items = [r for r in items if r.kind == kind_val]
            return items[-limit:]

    # ------------------------------------------------------------------
    # Synthesis
    # ------------------------------------------------------------------

    def synthesize(
        self,
        source_concept_ids: List[str],
        method: SynthesisMethod,
        description: str = "",
        confidence: ConfidenceLevel = ConfidenceLevel.MEDIUM,
    ) -> SynthesisResult:
        with self._lock:
            method_val = self._coerce_method(method)
            conf = self._coerce_confidence(confidence)
            sources = [
                self._concepts[cid]
                for cid in source_concept_ids
                if cid in self._concepts
            ]
            if sources:
                dom_counts: Dict[KnowledgeDomain, int] = {}
                for s in sources:
                    dom_counts[s.domain] = dom_counts.get(s.domain, 0) + 1
                result_domain = max(dom_counts, key=lambda k: dom_counts[k])
            else:
                result_domain = KnowledgeDomain.GAME_DESIGN
            merged_tags = sorted({t for s in sources for t in s.tags})
            merged_attrs: Dict[str, Any] = {}
            for s in sources:
                merged_attrs.update(s.attributes)
            result_concept = KnowledgeConcept(
                concept_id=_new_id("c"),
                name=f"Synthesis of {len(sources)} concepts",
                domain=result_domain,
                tier=ConceptTier.COMPOSITE,
                description=description,
                tags=merged_tags,
                attributes=merged_attrs,
                source_domain=sources[0].source_domain if sources else "",
                confidence=conf,
            )
            self._concepts[result_concept.concept_id] = result_concept
            _evict_fifo_dict(self._concepts, _MAX_CONCEPTS)
            for s in sources:
                s.usage_count += 1
                s.updated_at = _now()
            synthesis = SynthesisResult(
                synthesis_id=_new_id("syn"),
                method=method_val,
                source_concept_ids=list(source_concept_ids),
                result_concept_id=result_concept.concept_id,
                description=description,
                confidence=conf,
            )
            self._syntheses[synthesis.synthesis_id] = synthesis
            _evict_fifo_dict(self._syntheses, _MAX_SYNTHESES)
            self._emit(
                KnowledgeEventKind.SYNTHESIS_COMPLETED,
                concept_id=result_concept.concept_id,
                payload={
                    "synthesis_id": synthesis.synthesis_id,
                    "method": method_val.value,
                    "source_count": len(sources),
                },
            )
            return synthesis

    def get_synthesis(self, synthesis_id: str) -> Optional[SynthesisResult]:
        with self._lock:
            return self._syntheses.get(synthesis_id)

    def list_syntheses(
        self,
        method: Optional[SynthesisMethod] = None,
        limit: int = 100,
    ) -> List[SynthesisResult]:
        with self._lock:
            items = list(self._syntheses.values())
            if method is not None:
                method_val = self._coerce_method(method)
                items = [s for s in items if s.method == method_val]
            return items[-limit:]

    # ------------------------------------------------------------------
    # Inference
    # ------------------------------------------------------------------

    def draw_inference(
        self,
        premise_ids: List[str],
        conclusion_id: str,
        inference_type: InferenceType,
        steps: List[str],
        confidence: ConfidenceLevel = ConfidenceLevel.MEDIUM,
    ) -> InferenceChain:
        with self._lock:
            it = self._coerce_inference_type(inference_type)
            conf = self._coerce_confidence(confidence)
            chain = InferenceChain(
                chain_id=_new_id("inf"),
                premise_ids=list(premise_ids),
                conclusion_id=conclusion_id,
                inference_type=it,
                steps=list(steps),
                confidence=conf,
            )
            self._inferences[chain.chain_id] = chain
            _evict_fifo_dict(self._inferences, _MAX_INFERENCES)
            self._emit(
                KnowledgeEventKind.INFERENCE_DRAWN,
                concept_id=conclusion_id,
                payload={
                    "chain_id": chain.chain_id,
                    "inference_type": it.value,
                    "premise_count": len(premise_ids),
                },
            )
            return chain

    def get_inference(self, chain_id: str) -> Optional[InferenceChain]:
        with self._lock:
            return self._inferences.get(chain_id)

    def list_inferences(
        self,
        inference_type: Optional[InferenceType] = None,
        limit: int = 100,
    ) -> List[InferenceChain]:
        with self._lock:
            items = list(self._inferences.values())
            if inference_type is not None:
                it = self._coerce_inference_type(inference_type)
                items = [i for i in items if i.inference_type == it]
            return items[-limit:]

    # ------------------------------------------------------------------
    # Domain Exploration
    # ------------------------------------------------------------------

    def explore_domain(self, domain: KnowledgeDomain) -> DomainMap:
        with self._lock:
            dom = self._coerce_domain(domain)
            domain_map = self._build_domain_map(dom)
            self._domain_maps[dom.value] = domain_map
            _evict_fifo_dict(self._domain_maps, _MAX_DOMAIN_MAPS)
            self._emit(
                KnowledgeEventKind.DOMAIN_EXPLORED,
                payload={
                    "domain": dom.value,
                    "concept_count": domain_map.concept_count,
                    "relation_count": domain_map.relation_count,
                },
            )
            return domain_map

    def get_domain_map(self, domain: KnowledgeDomain) -> Optional[DomainMap]:
        with self._lock:
            dom = self._coerce_domain(domain)
            return self._domain_maps.get(dom.value)

    def list_domain_maps(self) -> List[DomainMap]:
        with self._lock:
            return list(self._domain_maps.values())

    # ------------------------------------------------------------------
    # Pattern Discovery and Insights
    # ------------------------------------------------------------------

    def discover_pattern(
        self,
        domain: Any = None,
        description: str = "",
        supporting_concept_ids: Any = None,
        confidence: Any = None,
        impact_score: float = 0.5,
        novelty_score: float = 0.5,
        concept_ids: Any = None,
        pattern_type: str = "",
    ) -> InsightRecord:
        with self._lock:
            dom = self._coerce_domain(domain) if domain else KnowledgeDomain.GAME_DESIGN
            conf = self._coerce_confidence(confidence) if confidence else ConfidenceLevel.MEDIUM
            sup_ids = list(concept_ids if concept_ids is not None else (supporting_concept_ids or []))
            desc = pattern_type if pattern_type else description
            if not desc:
                desc = f"Pattern discovered from {len(sup_ids)} concepts"
            insight = InsightRecord(
                insight_id=_new_id("ins"),
                domain=dom,
                description=desc,
                supporting_concept_ids=list(sup_ids),
                confidence=conf,
                impact_score=float(impact_score),
                novelty_score=float(novelty_score),
            )
            self._insights[insight.insight_id] = insight
            _evict_fifo_dict(self._insights, _MAX_INSIGHTS)
            self._emit(
                KnowledgeEventKind.PATTERN_DISCOVERED,
                payload={
                    "insight_id": insight.insight_id,
                    "domain": dom.value,
                    "supporting_count": len(sup_ids),
                    "impact_score": insight.impact_score,
                    "novelty_score": insight.novelty_score,
                },
            )
            self._emit(
                KnowledgeEventKind.INSIGHT_GENERATED,
                payload={
                    "insight_id": insight.insight_id,
                    "domain": dom.value,
                    "confidence": conf.value,
                },
            )
            return insight

    def get_insight(self, insight_id: str) -> Optional[InsightRecord]:
        with self._lock:
            return self._insights.get(insight_id)

    def list_insights(
        self,
        domain: Optional[KnowledgeDomain] = None,
        limit: int = 100,
    ) -> List[InsightRecord]:
        with self._lock:
            items = list(self._insights.values())
            if domain is not None:
                dom = self._coerce_domain(domain)
                items = [i for i in items if i.domain == dom]
            return items[-limit:]

    # ------------------------------------------------------------------
    # Query and Answering
    # ------------------------------------------------------------------

    def query(self, question: str = "", domain: Any = None,
              query_text: str = "") -> KnowledgeQuery:
        with self._lock:
            qtext = query_text if query_text else question
            dom = self._coerce_domain(domain) if domain else KnowledgeDomain.GAME_DESIGN
            terms = self._tokenize(qtext)
            candidates = [c for c in self._concepts.values() if c.domain == dom]
            scored: List[tuple] = []
            for c in candidates:
                score = self._match_score(c, qtext, terms)
                if score > 0.0:
                    scored.append((c, score))
            scored.sort(key=lambda x: -x[1])
            matched = [c.concept_id for c, _ in scored[:10]]
            if matched:
                top = [self._concepts[mid] for mid in matched[:3]]
                answer = " | ".join(
                    f"{c.name}: {c.description}" for c in top if c.description
                )
                if not answer:
                    answer = "Matched concepts: " + ", ".join(c.name for c in top)
                conf = (
                    ConfidenceLevel.HIGH
                    if scored[0][1] > 0.5
                    else ConfidenceLevel.MEDIUM
                )
            else:
                answer = "No matching concepts found in this domain."
                conf = ConfidenceLevel.LOW
            knowledge_query = KnowledgeQuery(
                query_id=_new_id("q"),
                question=qtext,
                domain=dom,
                matched_concept_ids=matched,
                answer=answer,
                confidence=conf,
            )
            self._queries[knowledge_query.query_id] = knowledge_query
            _evict_fifo_dict(self._queries, _MAX_QUERIES)
            self._emit(
                KnowledgeEventKind.QUERY_ANSWERED,
                payload={
                    "query_id": knowledge_query.query_id,
                    "domain": dom.value,
                    "matched_count": len(matched),
                    "confidence": conf.value,
                },
            )
            return knowledge_query

    def get_query(self, query_id: str) -> Optional[KnowledgeQuery]:
        with self._lock:
            return self._queries.get(query_id)

    def list_queries(
        self,
        domain: Optional[KnowledgeDomain] = None,
        limit: int = 100,
    ) -> List[KnowledgeQuery]:
        with self._lock:
            items = list(self._queries.values())
            if domain is not None:
                dom = self._coerce_domain(domain)
                items = [q for q in items if q.domain == dom]
            return items[-limit:]

    # ------------------------------------------------------------------
    # Observability and State
    # ------------------------------------------------------------------

    def list_events(
        self,
        limit: int = 100,
        kind: Optional[KnowledgeEventKind] = None,
    ) -> List[KnowledgeEvent]:
        with self._lock:
            items = list(self._events)
            if kind is not None:
                kind_val = self._coerce_event_kind(kind)
                if kind_val is not None:
                    items = [e for e in items if e.kind == kind_val]
            return items[-limit:]

    def get_stats(self) -> KnowledgeStats:
        with self._lock:
            concepts = list(self._concepts.values())
            domain_dist: Dict[str, int] = {}
            conf_sum = 0
            for c in concepts:
                dom_key = c.domain.value if isinstance(c.domain, KnowledgeDomain) else str(c.domain)
                domain_dist[dom_key] = domain_dist.get(dom_key, 0) + 1
                conf_sum += self._conf_rank(c.confidence)
            avg_conf = round(conf_sum / max(1, len(concepts)) / 5.0, 4)
            return KnowledgeStats(
                total_concepts=len(self._concepts),
                total_relations=len(self._relations),
                total_syntheses=len(self._syntheses),
                total_inferences=len(self._inferences),
                total_insights=len(self._insights),
                total_queries=len(self._queries),
                domain_distribution=domain_dist,
                avg_confidence=avg_conf,
                last_updated=_now(),
            )

    def get_status(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "initialized": self._initialized,
                "concepts": len(self._concepts),
                "relations": len(self._relations),
                "syntheses": len(self._syntheses),
                "inferences": len(self._inferences),
                "domain_maps": len(self._domain_maps),
                "insights": len(self._insights),
                "queries": len(self._queries),
                "events": len(self._events),
            }

    def get_snapshot(self) -> KnowledgeSnapshot:
        with self._lock:
            return KnowledgeSnapshot(
                concepts=[c.to_dict() for c in list(self._concepts.values())[:20]],
                relations=[r.to_dict() for r in list(self._relations.values())[:20]],
                syntheses=[s.to_dict() for s in list(self._syntheses.values())[:20]],
                inferences=[i.to_dict() for i in list(self._inferences.values())[:20]],
                domain_maps=[d.to_dict() for d in list(self._domain_maps.values())[:20]],
                insights=[i.to_dict() for i in list(self._insights.values())[:20]],
                queries=[q.to_dict() for q in list(self._queries.values())[:20]],
                stats=self.get_stats().to_dict(),
            )

    def reset(self) -> None:
        with self._lock:
            self._concepts.clear()
            self._relations.clear()
            self._syntheses.clear()
            self._inferences.clear()
            self._domain_maps.clear()
            self._insights.clear()
            self._queries.clear()
            self._events.clear()
            self._seed_data()

    # ------------------------------------------------------------------
    # Seed Data
    # ------------------------------------------------------------------

    def _seed_data(self) -> None:
        # Eight concepts spanning game_design, narrative, and mechanics.
        concepts = [
            KnowledgeConcept(
                concept_id="c_core_loop",
                name="Core Loop",
                domain=KnowledgeDomain.GAME_DESIGN,
                tier=ConceptTier.PRINCIPLE,
                description="The repeating cycle of actions a player performs each session.",
                tags=["loop", "engagement", "core"],
                attributes={"cycle_time_sec": 90},
                source_domain="game_design",
                confidence=ConfidenceLevel.HIGH,
                usage_count=5,
            ),
            KnowledgeConcept(
                concept_id="c_risk_reward",
                name="Risk-Reward Tradeoff",
                domain=KnowledgeDomain.GAME_DESIGN,
                tier=ConceptTier.PRINCIPLE,
                description="Tension between player risk and corresponding payoff.",
                tags=["risk", "reward", "balance"],
                attributes={"asymmetry": 0.6},
                source_domain="game_design",
                confidence=ConfidenceLevel.HIGH,
                usage_count=3,
            ),
            KnowledgeConcept(
                concept_id="c_emergent_narrative",
                name="Emergent Narrative",
                domain=KnowledgeDomain.NARRATIVE,
                tier=ConceptTier.PATTERN,
                description="Stories that arise from player actions rather than scripted beats.",
                tags=["narrative", "emergence", "story"],
                attributes={"scripted_ratio": 0.2},
                source_domain="narrative",
                confidence=ConfidenceLevel.MEDIUM,
                usage_count=4,
            ),
            KnowledgeConcept(
                concept_id="c_character_arc",
                name="Character Arc",
                domain=KnowledgeDomain.NARRATIVE,
                tier=ConceptTier.COMPOSITE,
                description="The transformation a character undergoes across the story.",
                tags=["character", "arc", "story"],
                attributes={"beats": 7},
                source_domain="narrative",
                confidence=ConfidenceLevel.HIGH,
                usage_count=3,
            ),
            KnowledgeConcept(
                concept_id="c_skill_tree",
                name="Skill Tree",
                domain=KnowledgeDomain.MECHANICS,
                tier=ConceptTier.COMPOSITE,
                description="Branching progression structure gating player abilities.",
                tags=["progression", "skills", "branching"],
                attributes={"depth": 5},
                source_domain="mechanics",
                confidence=ConfidenceLevel.HIGH,
                usage_count=2,
            ),
            KnowledgeConcept(
                concept_id="c_resource_economy",
                name="Resource Economy",
                domain=KnowledgeDomain.MECHANICS,
                tier=ConceptTier.PATTERN,
                description="Flow of resources between sources, sinks, and storage.",
                tags=["economy", "resources", "balance"],
                attributes={"sink_count": 4},
                source_domain="mechanics",
                confidence=ConfidenceLevel.MEDIUM,
                usage_count=3,
            ),
            KnowledgeConcept(
                concept_id="c_engagement_principle",
                name="Engagement Principle",
                domain=KnowledgeDomain.GAME_DESIGN,
                tier=ConceptTier.META_CONCEPT,
                description="A fused principle linking core loops with risk-reward tension.",
                tags=["engagement", "synthesis", "meta"],
                attributes={"fusion_method": "abstraction"},
                source_domain="game_design",
                confidence=ConfidenceLevel.HIGH,
                usage_count=2,
            ),
            KnowledgeConcept(
                concept_id="c_narrative_emergence",
                name="Narrative Emergence Pattern",
                domain=KnowledgeDomain.NARRATIVE,
                tier=ConceptTier.PATTERN,
                description="A fused pattern where character arcs channel emergent narrative.",
                tags=["narrative", "emergence", "synthesis"],
                attributes={"fusion_method": "composition"},
                source_domain="narrative",
                confidence=ConfidenceLevel.MEDIUM,
                usage_count=1,
            ),
        ]
        for concept in concepts:
            self._concepts[concept.concept_id] = concept

        # Five relations linking concepts across and within domains.
        relations = [
            ConceptRelation(
                relation_id="rel_loop_economy",
                source_concept_id="c_core_loop",
                target_concept_id="c_resource_economy",
                kind=RelationKind.DEPENDS_ON,
                strength=0.8,
                description="The core loop depends on a balanced resource economy.",
            ),
            ConceptRelation(
                relation_id="rel_skill_economy",
                source_concept_id="c_skill_tree",
                target_concept_id="c_resource_economy",
                kind=RelationKind.COMPLEMENTS,
                strength=0.6,
                description="Skill progression complements resource spending.",
            ),
            ConceptRelation(
                relation_id="rel_narrative_arc",
                source_concept_id="c_narrative_emergence",
                target_concept_id="c_character_arc",
                kind=RelationKind.COMPOSED_OF,
                strength=0.7,
                description="Narrative emergence is composed of structured character arcs.",
            ),
            ConceptRelation(
                relation_id="rel_risk_loop",
                source_concept_id="c_risk_reward",
                target_concept_id="c_core_loop",
                kind=RelationKind.EXTENDS,
                strength=0.75,
                description="Risk-reward tension extends the core loop.",
            ),
            ConceptRelation(
                relation_id="rel_engagement_loop",
                source_concept_id="c_engagement_principle",
                target_concept_id="c_core_loop",
                kind=RelationKind.GENERALIZES,
                strength=0.7,
                description="The engagement principle generalizes the core loop idea.",
            ),
        ]
        for rel in relations:
            self._relations[rel.relation_id] = rel

        # Two syntheses recording how fused concepts were produced.
        syntheses = [
            SynthesisResult(
                synthesis_id="syn_engagement",
                method=SynthesisMethod.ABSTRACTION,
                source_concept_ids=["c_core_loop", "c_risk_reward"],
                result_concept_id="c_engagement_principle",
                description="Abstract the shared engagement driver from core loop and risk-reward.",
                confidence=ConfidenceLevel.HIGH,
            ),
            SynthesisResult(
                synthesis_id="syn_narrative",
                method=SynthesisMethod.COMPOSITION,
                source_concept_ids=["c_emergent_narrative", "c_character_arc"],
                result_concept_id="c_narrative_emergence",
                description="Compose emergent narrative with character arcs into a guiding pattern.",
                confidence=ConfidenceLevel.MEDIUM,
            ),
        ]
        for synthesis in syntheses:
            self._syntheses[synthesis.synthesis_id] = synthesis

        # Two inference chains over concept premises.
        inferences = [
            InferenceChain(
                chain_id="inf_engagement",
                premise_ids=["c_core_loop", "c_resource_economy"],
                conclusion_id="c_engagement_principle",
                inference_type=InferenceType.INDUCTIVE,
                steps=[
                    "The core loop drives repeated engagement.",
                    "The resource economy sustains the loop over time.",
                    "Therefore engagement depends on a balanced resource economy.",
                ],
                confidence=ConfidenceLevel.MEDIUM,
            ),
            InferenceChain(
                chain_id="inf_narrative",
                premise_ids=["c_character_arc", "c_emergent_narrative"],
                conclusion_id="c_narrative_emergence",
                inference_type=InferenceType.ABDUCTIVE,
                steps=[
                    "Character arcs provide story structure.",
                    "Emergent narrative arises from player choice.",
                    "Best explanation: structured arcs channel emergent story.",
                ],
                confidence=ConfidenceLevel.MEDIUM,
            ),
        ]
        for chain in inferences:
            self._inferences[chain.chain_id] = chain

        # Three domain maps for game_design, narrative, and mechanics.
        for dom in (
            KnowledgeDomain.GAME_DESIGN,
            KnowledgeDomain.NARRATIVE,
            KnowledgeDomain.MECHANICS,
        ):
            domain_map = self._build_domain_map(dom)
            self._domain_maps[dom.value] = domain_map

        # Two insight records capturing discovered patterns.
        insights = [
            InsightRecord(
                insight_id="ins_engagement",
                domain=KnowledgeDomain.GAME_DESIGN,
                description="Balancing risk and reward within the core loop maximizes engagement.",
                supporting_concept_ids=[
                    "c_core_loop",
                    "c_risk_reward",
                    "c_engagement_principle",
                ],
                confidence=ConfidenceLevel.HIGH,
                impact_score=0.82,
                novelty_score=0.6,
            ),
            InsightRecord(
                insight_id="ins_narrative",
                domain=KnowledgeDomain.NARRATIVE,
                description="Structured character arcs channel emergent narrative into coherent stories.",
                supporting_concept_ids=[
                    "c_character_arc",
                    "c_emergent_narrative",
                    "c_narrative_emergence",
                ],
                confidence=ConfidenceLevel.MEDIUM,
                impact_score=0.7,
                novelty_score=0.75,
            ),
        ]
        for insight in insights:
            self._insights[insight.insight_id] = insight

        # Two pre-seeded queries and their answers.
        queries = [
            KnowledgeQuery(
                query_id="q_engagement",
                question="What drives player engagement?",
                domain=KnowledgeDomain.GAME_DESIGN,
                matched_concept_ids=["c_core_loop", "c_engagement_principle"],
                answer="Engagement is driven by a well-tuned core loop combining risk-reward tradeoffs.",
                confidence=ConfidenceLevel.HIGH,
            ),
            KnowledgeQuery(
                query_id="q_narrative",
                question="How do character arcs relate to emergent narrative?",
                domain=KnowledgeDomain.NARRATIVE,
                matched_concept_ids=[
                    "c_character_arc",
                    "c_emergent_narrative",
                    "c_narrative_emergence",
                ],
                answer="Character arcs provide structure that channels emergent narrative into coherent storylines.",
                confidence=ConfidenceLevel.MEDIUM,
            ),
        ]
        for knowledge_query in queries:
            self._queries[knowledge_query.query_id] = knowledge_query


# Backwards-compatible alias for the previous class name. Existing callers
# that import KnowledgeSynthesisEngine continue to resolve to the singleton.
KnowledgeSynthesisEngine = KnowledgeSynthesis


def get_knowledge_synthesis() -> KnowledgeSynthesis:
    """Factory function returning the singleton KnowledgeSynthesis instance."""
    return KnowledgeSynthesis.get_instance()
