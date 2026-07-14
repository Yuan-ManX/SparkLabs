"""
SparkLabs Agent - AI Knowledge Retrieval System

A RAG-based knowledge manager for the SparkLabs AI-native game engine.
Ingests game design documents, lore, code, and assets; chunks them into
retrievable units; performs semantic search via simulated TF-IDF scoring;
maintains a concept knowledge graph; assembles context windows for model
consumption; and tracks provenance, freshness, and search analytics.

Thread safety: all mutating operations are guarded by a single
``threading.Lock``. Returned objects are snapshots; live mutation must
go through the public API.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
import threading
import time
import uuid
from collections import Counter, deque
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Deque, Dict, List, Optional, Set, Tuple

_MAX_DOCUMENTS = 10000
_MAX_CHUNKS_PER_DOC = 256
_MAX_CHUNKS_TOTAL = 100000
_MAX_CONCEPTS = 5000
_MAX_EDGES = 10000
_MAX_SEARCH_HISTORY = 1000
_MAX_POPULAR_QUERIES = 200
_EMBEDDING_DIM = 64
_DEFAULT_CHUNK_SIZE = 200
_DEFAULT_CHUNK_OVERLAP = 30
_STALE_DAYS = 90

def _now_ts() -> float:
    return time.time()

def _clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return max(low, min(high, value))

def _uid(prefix: str = "id") -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"

def _round(value: float, digits: int = 4) -> float:
    return round(float(value), digits)

_WORD_RE = re.compile(r"[a-zA-Z][a-zA-Z0-9_']*")

def _tokenize(text: str) -> List[str]:
    return [w.lower() for w in _WORD_RE.findall(text or "")]

_STOPWORDS: Set[str] = {
    "the", "a", "an", "and", "or", "but", "of", "to", "in", "on", "for",
    "is", "are", "was", "were", "be", "been", "being", "this", "that",
    "these", "those", "it", "its", "as", "at", "by", "with", "from", "into",
    "if", "then", "else", "when", "while", "not", "no", "yes", "so", "such",
    "can", "could", "should", "would", "may", "might", "must", "shall",
    "will", "do", "does", "did", "has", "have", "had", "about", "above",
}

def _content_tokens(text: str) -> List[str]:
    return [t for t in _tokenize(text) if t not in _STOPWORDS and len(t) > 1]

def _days_since(ts: float, now: Optional[float] = None) -> float:
    return max(0.0, ((now or _now_ts()) - ts) / 86400.0)

class DocumentCategory(Enum):
    GAME_DESIGN = "game_design"
    LORE = "lore"
    CHARACTER = "character"
    MECHANICS = "mechanics"
    CODE = "code"
    ASSET = "asset"
    TUTORIAL = "tutorial"
    BUG_REPORT = "bug_report"
    REVIEW = "review"
    UNKNOWN = "unknown"

class ContentFormat(Enum):
    TEXT = "text"
    MARKDOWN = "markdown"
    JSON = "json"

class ContextStrategy(Enum):
    TOP_K = "top_k"
    DIVERSITY_WEIGHTED = "diversity_weighted"
    TEMPORAL_DECAY = "temporal_decay"
    GRAPH_EXPANDED = "graph_expanded"

class ConceptRelation(Enum):
    RELATES_TO = "relates_to"
    PART_OF = "part_of"
    DEPENDS_ON = "depends_on"
    CONTRADICTS = "contradicts"

_CATEGORY_KEYWORDS: Dict[DocumentCategory, Set[str]] = {
    DocumentCategory.GAME_DESIGN: {"combat", "system", "design", "balance", "loop", "mechanic", "playtest", "feature"},
    DocumentCategory.LORE: {"realm", "world", "history", "myth", "lore", "faction", "legend", "ancient", "kingdom", "god"},
    DocumentCategory.CHARACTER: {"character", "archetype", "npc", "protagonist", "villain", "hero", "class", "trait"},
    DocumentCategory.MECHANICS: {"damage", "health", "mana", "cooldown", "input", "physics", "collision", "movement", "stat"},
    DocumentCategory.CODE: {"class", "function", "module", "import", "return", "api", "interface", "component"},
    DocumentCategory.ASSET: {"sprite", "mesh", "texture", "audio", "animation", "model", "shader", "material"},
    DocumentCategory.TUTORIAL: {"tutorial", "guide", "step", "learn", "beginner", "onboarding", "example"},
    DocumentCategory.BUG_REPORT: {"bug", "crash", "error", "reproduce", "stack", "trace", "issue", "fail"},
    DocumentCategory.REVIEW: {"review", "feedback", "rating", "score", "opinion", "critique", "sentiment"},
}

_SYNONYMS: Dict[str, Set[str]] = {
    "combat": {"battle", "fight", "conflict", "duel"},
    "weapon": {"armament", "blade", "firearm", "tool"},
    "character": {"hero", "protagonist", "npc", "person"},
    "quest": {"mission", "task", "objective", "errand"},
    "world": {"realm", "domain", "land", "setting"},
    "enemy": {"foe", "opponent", "adversary", "monster"},
    "magic": {"spell", "arcane", "sorcery", "enchantment"},
    "level": {"stage", "area", "zone", "map"},
    "item": {"object", "artifact", "loot", "gear"},
    "skill": {"ability", "talent", "technique", "power"},
}

@dataclass
class DocumentChunk:
    """A retrievable slice of a parent document."""
    chunk_id: str
    doc_id: str
    text: str
    embedding: List[float] = field(default_factory=list)
    position: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=_now_ts)

    def to_dict(self) -> Dict[str, Any]:
        return {"chunk_id": self.chunk_id, "doc_id": self.doc_id, "text": self.text, "embedding": self.embedding,
                "position": self.position, "metadata": dict(self.metadata), "created_at": self.created_at}

@dataclass
class KnowledgeDocument:
    """A full document stored in the knowledge base."""
    doc_id: str
    title: str
    content: str
    source: str = "internal"
    category: DocumentCategory = DocumentCategory.UNKNOWN
    tags: List[str] = field(default_factory=list)
    format: ContentFormat = ContentFormat.TEXT
    metadata: Dict[str, Any] = field(default_factory=dict)
    chunk_ids: List[str] = field(default_factory=list)
    created_at: float = field(default_factory=_now_ts)
    updated_at: float = field(default_factory=_now_ts)
    access_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {"doc_id": self.doc_id, "title": self.title, "content": self.content, "source": self.source,
                "category": self.category.value, "tags": list(self.tags), "format": self.format.value,
                "metadata": dict(self.metadata), "chunk_ids": list(self.chunk_ids),
                "created_at": self.created_at, "updated_at": self.updated_at, "access_count": self.access_count}

    def touch(self) -> None:
        self.access_count += 1
        self.updated_at = _now_ts()

@dataclass
class SearchResult:
    """A single ranked retrieval result with provenance."""
    chunk: DocumentChunk
    document: KnowledgeDocument
    score: float
    rank: int = 0
    matched_terms: List[str] = field(default_factory=list)
    explanation: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {"chunk": self.chunk.to_dict(), "document": self.document.to_dict(), "score": _round(self.score),
                "rank": self.rank, "matched_terms": list(self.matched_terms), "explanation": self.explanation}

@dataclass
class KnowledgeGraphNode:
    """A concept node in the knowledge graph."""
    concept_id: str
    name: str
    category: DocumentCategory = DocumentCategory.UNKNOWN
    description: str = ""
    weight: float = 1.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    mentions: int = 0
    created_at: float = field(default_factory=_now_ts)

    def to_dict(self) -> Dict[str, Any]:
        return {"concept_id": self.concept_id, "name": self.name, "category": self.category.value,
                "description": self.description, "weight": _round(self.weight), "metadata": dict(self.metadata),
                "mentions": self.mentions, "created_at": self.created_at}

@dataclass
class KnowledgeGraphEdge:
    """A typed relationship between two concept nodes."""
    edge_id: str
    source_id: str
    target_id: str
    relation: ConceptRelation = ConceptRelation.RELATES_TO
    weight: float = 1.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=_now_ts)

    def to_dict(self) -> Dict[str, Any]:
        return {"edge_id": self.edge_id, "source_id": self.source_id, "target_id": self.target_id,
                "relation": self.relation.value, "weight": _round(self.weight),
                "metadata": dict(self.metadata), "created_at": self.created_at}

@dataclass
class KnowledgeGraph:
    """Container holding all concept nodes and edges."""
    nodes: Dict[str, KnowledgeGraphNode] = field(default_factory=dict)
    edges: Dict[str, KnowledgeGraphEdge] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {"nodes": {n: v.to_dict() for n, v in self.nodes.items()},
                "edges": {e: v.to_dict() for e, v in self.edges.items()}}

@dataclass
class ContextWindow:
    """An assembled context window ready for model consumption."""
    query: str
    strategy: ContextStrategy
    chunks: List[DocumentChunk]
    citations: List[Dict[str, Any]] = field(default_factory=list)
    token_estimate: int = 0
    assembled_text: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {"query": self.query, "strategy": self.strategy.value, "chunks": [c.to_dict() for c in self.chunks],
                "citations": list(self.citations), "token_estimate": self.token_estimate, "assembled_text": self.assembled_text}

@dataclass
class QueryExpansion:
    """The result of expanding a query with synonyms and graph concepts."""
    original: str
    expanded_terms: List[str]
    synonyms: List[str]
    related_concepts: List[str]
    reformulated: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {"original": self.original, "expanded_terms": list(self.expanded_terms), "synonyms": list(self.synonyms),
                "related_concepts": list(self.related_concepts), "reformulated": self.reformulated}

@dataclass
class RetrievalConfig:
    """Tunable parameters for retrieval and chunking."""
    chunk_size: int = _DEFAULT_CHUNK_SIZE
    chunk_overlap: int = _DEFAULT_CHUNK_OVERLAP
    top_k: int = 5
    context_top_k: int = 6
    min_score: float = 0.05
    diversity_lambda: float = 0.5
    temporal_decay: float = 0.02
    graph_expansion_depth: int = 1
    max_context_tokens: int = 2048
    auto_categorize: bool = True
    auto_extract_concepts: bool = True
    stale_days: int = _STALE_DAYS

    def to_dict(self) -> Dict[str, Any]:
        return {"chunk_size": self.chunk_size, "chunk_overlap": self.chunk_overlap, "top_k": self.top_k,
                "context_top_k": self.context_top_k, "min_score": self.min_score,
                "diversity_lambda": self.diversity_lambda, "temporal_decay": self.temporal_decay,
                "graph_expansion_depth": self.graph_expansion_depth, "max_context_tokens": self.max_context_tokens,
                "auto_categorize": self.auto_categorize, "auto_extract_concepts": self.auto_extract_concepts,
                "stale_days": self.stale_days}

@dataclass
class RetrievalStats:
    """Aggregate statistics about the knowledge base and its usage."""
    document_count: int = 0
    chunk_count: int = 0
    concept_count: int = 0
    edge_count: int = 0
    average_chunk_size: float = 0.0
    category_distribution: Dict[str, int] = field(default_factory=dict)
    search_count: int = 0
    last_search_at: Optional[float] = None
    popular_queries: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {"document_count": self.document_count, "chunk_count": self.chunk_count,
                "concept_count": self.concept_count, "edge_count": self.edge_count,
                "average_chunk_size": _round(self.average_chunk_size), "category_distribution": dict(self.category_distribution),
                "search_count": self.search_count, "last_search_at": self.last_search_at,
                "popular_queries": list(self.popular_queries)}

_SEED_DOCUMENTS: List[Dict[str, Any]] = [
    {"title": "Combat System Design", "source": "design_doc", "category": DocumentCategory.GAME_DESIGN,
     "tags": ["combat", "balance", "mechanics"], "format": ContentFormat.MARKDOWN,
     "content": "# Combat System Design\n\nThe combat system uses a real-time action loop with a stamina economy. "
         "Each attack costs stamina that regenerates over time. Heavy attacks deal more damage but consume more "
         "stamina and have longer recovery frames.\n\nDamage is calculated from weapon base damage, character "
         "strength, and a critical multiplier. Defensive stats reduce incoming damage with diminishing returns. "
         "Block timing opens a parry window that staggers enemies. Enemy AI scales aggression and health with player level."},
    {"title": "World Lore: The Shattered Realm", "source": "lore_bible", "category": DocumentCategory.LORE,
     "tags": ["lore", "world", "history", "shattered"], "format": ContentFormat.MARKDOWN,
     "content": "# The Shattered Realm\n\nLong ago a single kingdom spanned the world. A great cataclysm shattered "
         "the realm into floating islands above an endless void. The survivors rebuilt scattered civilizations on "
         "these fragments.\n\nAncient gods slumber beneath the void. Their dreams leak into the world as magic. "
         "Factions vie for control of the largest fragments and the relics left by the old kingdom. "
         "Legend says a chosen hero can reforge the realm."},
    {"title": "Character Archetypes", "source": "design_doc", "category": DocumentCategory.CHARACTER,
     "tags": ["character", "archetype", "class"], "format": ContentFormat.MARKDOWN,
     "content": "# Character Archetypes\n\nPlayer characters pick one of four archetypes. Each defines a starting stat "
         "distribution, a unique skill tree, and a signature ability unlocked at level ten.\n\nThe Warrior favors "
         "strength and vitality with melee skills. The Mage channels mana into spells and elemental damage. "
         "The Rogue relies on agility and stealth for critical strikes. The Cleric heals allies and wields protective enchantments."},
    {"title": "Quest Design Patterns", "source": "design_doc", "category": DocumentCategory.GAME_DESIGN,
     "tags": ["quest", "design", "pattern"], "format": ContentFormat.MARKDOWN,
     "content": "# Quest Design Patterns\n\nQuests follow established patterns to give players clear goals while leaving "
         "room for narrative surprise. The fetch pattern tasks players with retrieving an item. The escort pattern "
         "protects an NPC through hostile territory.\n\nThe mystery pattern unfolds through clues the player pieces "
         "together. The branching pattern offers choices that change the outcome. Every quest declares an objective, "
         "a reward, and a failure state."},
]

def _coerce_enum(cls, value: Any, default: Any) -> Any:
    if isinstance(value, cls):
        return value
    if isinstance(value, str):
        try:
            return cls(value)
        except ValueError:
            try:
                return cls[value.upper()]
            except KeyError:
                return default
    return default

class KnowledgeRetrievalSystem:
    """RAG knowledge manager with semantic search and a concept graph."""

    _instance: Optional["KnowledgeRetrievalSystem"] = None
    _instance_lock = threading.Lock()

    def __init__(self, config: Optional[RetrievalConfig] = None) -> None:
        self._lock = threading.RLock()
        self._config = config or RetrievalConfig()
        self._documents: Dict[str, KnowledgeDocument] = {}
        self._chunks: Dict[str, DocumentChunk] = {}
        self._graph = KnowledgeGraph()
        self._concept_index: Dict[str, str] = {}  # name -> concept id
        self._inverted_index: Dict[str, Set[str]] = {}  # term -> chunk ids
        self._df: Dict[str, int] = {}  # term -> document frequency
        self._search_history: Deque[Dict[str, Any]] = deque(maxlen=_MAX_SEARCH_HISTORY)
        self._query_counts: Counter = Counter()
        self._initialized = False

    @classmethod
    def get_instance(cls) -> "KnowledgeRetrievalSystem":
        if cls._instance is None:
            with cls._instance_lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def initialize(self) -> None:
        with self._lock:
            if self._initialized:
                return
            for spec in _SEED_DOCUMENTS:
                self._ingest_locked(spec, doc_id=_uid("doc"))
            self._initialized = True

    def reset(self) -> None:
        with self._lock:
            self._documents.clear()
            self._chunks.clear()
            self._graph = KnowledgeGraph()
            self._concept_index.clear()
            self._inverted_index.clear()
            self._df.clear()
            self._search_history.clear()
            self._query_counts.clear()
            self._initialized = False

    def get_config(self) -> RetrievalConfig:
        with self._lock:
            return self._snapshot_config()

    def set_config(self, config: Any) -> None:
        if isinstance(config, dict):
            config = RetrievalConfig(
                chunk_size=int(config.get("chunk_size", _DEFAULT_CHUNK_SIZE)),
                chunk_overlap=int(config.get("chunk_overlap", _DEFAULT_CHUNK_OVERLAP)),
                top_k=int(config.get("top_k", 5)),
                context_top_k=int(config.get("context_top_k", 6)),
                min_score=float(config.get("min_score", 0.05)),
                diversity_lambda=float(config.get("diversity_lambda", 0.5)),
                temporal_decay=float(config.get("temporal_decay", 0.02)),
                graph_expansion_depth=int(config.get("graph_expansion_depth", 1)),
                max_context_tokens=int(config.get("max_context_tokens", 2048)),
                auto_categorize=bool(config.get("auto_categorize", True)),
                auto_extract_concepts=bool(config.get("auto_extract_concepts", True)),
                stale_days=int(config.get("stale_days", _STALE_DAYS)),
            )
        if not isinstance(config, RetrievalConfig):
            raise TypeError("config must be a RetrievalConfig instance or dict")
        with self._lock:
            self._config = config

    def get_status(self) -> Dict[str, Any]:
        with self._lock:
            return {"initialized": self._initialized,
                    "document_count": len(self._documents),
                    "chunk_count": len(self._chunks),
                    "concept_count": len(self._graph.nodes),
                    "edge_count": len(self._graph.edges),
                    "search_count": sum(self._query_counts.values()),
                    "last_search_at": (self._search_history[-1]["at"]
                                        if self._search_history else None)}

    def get_snapshot(self) -> Dict[str, Any]:
        with self._lock:
            return {"config": self._snapshot_config().to_dict(),
                    "status": {"initialized": self._initialized,
                               "document_count": len(self._documents),
                               "chunk_count": len(self._chunks),
                               "concept_count": len(self._graph.nodes),
                               "edge_count": len(self._graph.edges)},
                    "statistics": self._stats_locked().to_dict()}

    def to_dict(self) -> Dict[str, Any]:
        with self._lock:
            return {"documents": {d: v.to_dict() for d, v in self._documents.items()},
                    "chunks": {c: v.to_dict() for c, v in self._chunks.items()},
                    "graph": self._graph.to_dict(),
                    "config": self._snapshot_config().to_dict(),
                    "statistics": self._stats_locked().to_dict(),
                    "search_history": list(self._search_history)}

    def add_document(self, title: str, content: str, source: str = "internal",
                     category: Optional[DocumentCategory] = None,
                     tags: Optional[List[str]] = None,
                     content_format: ContentFormat = ContentFormat.TEXT,
                     metadata: Optional[Dict[str, Any]] = None,
                     doc_id: Optional[str] = None) -> str:
        """Ingest a document, auto-chunk it, and index its chunks."""
        if not title or not content:
            raise ValueError("title and content are required")
        spec = {"title": title, "content": content, "source": source,
                "category": category, "tags": list(tags or []),
                "format": content_format, "metadata": dict(metadata or {})}
        with self._lock:
            if len(self._documents) >= _MAX_DOCUMENTS:
                raise RuntimeError("document capacity reached")
            return self._ingest_locked(spec, doc_id=doc_id or _uid("doc"))

    def get_document(self, doc_id: str) -> Optional[KnowledgeDocument]:
        with self._lock:
            doc = self._documents.get(doc_id)
            if doc is None:
                return None
            doc.touch()
            return self._clone_document(doc)

    def update_document(self, doc_id: str, **fields: Any) -> Optional[KnowledgeDocument]:
        with self._lock:
            doc = self._documents.get(doc_id)
            if doc is None:
                return None
            if "title" in fields:
                doc.title = str(fields["title"])
            if "content" in fields:
                doc.content = str(fields["content"])
            if "source" in fields:
                doc.source = str(fields["source"])
            if "tags" in fields and fields["tags"] is not None:
                doc.tags = list(fields["tags"])
            if "format" in fields and fields["format"] is not None:
                doc.format = self._coerce_format(fields["format"])
            if "category" in fields and fields["category"] is not None:
                doc.category = self._coerce_category(fields["category"])
            if "metadata" in fields and fields["metadata"] is not None:
                doc.metadata = dict(fields["metadata"])
            self._remove_chunks_locked(doc)
            self._chunk_and_index_locked(doc)
            doc.updated_at = _now_ts()
            return self._clone_document(doc)

    def remove_document(self, doc_id: str) -> bool:
        with self._lock:
            doc = self._documents.get(doc_id)
            if doc is None:
                return False
            self._remove_chunks_locked(doc)
            del self._documents[doc_id]
            return True

    def list_documents(self, category: Optional[DocumentCategory] = None,
                       tag: Optional[str] = None, source: Optional[str] = None,
                       limit: Optional[int] = None) -> List[KnowledgeDocument]:
        """List documents, optionally filtered by category, tag, or source."""
        with self._lock:
            results: List[KnowledgeDocument] = []
            for doc in self._documents.values():
                if category is not None and doc.category != category:
                    continue
                if tag is not None and tag not in doc.tags:
                    continue
                if source is not None and doc.source != source:
                    continue
                results.append(self._clone_document(doc))
            results.sort(key=lambda d: d.updated_at, reverse=True)
            if limit is not None:
                results = results[:max(0, int(limit))]
            return results

    def list_by_category(self, category: DocumentCategory) -> List[KnowledgeDocument]:
        return self.list_documents(category=category)

    def search_documents(self, query: str, top_k: Optional[int] = None,
                         category: Optional[DocumentCategory] = None,
                         tags: Optional[List[str]] = None,
                         source: Optional[str] = None) -> List[SearchResult]:
        """Run a keyword-overlap search with optional filters."""
        return self.semantic_search(
            query=query, top_k=top_k,
            filters={"category": category, "tags": tags, "source": source},
            strategy=ContextStrategy.TOP_K)

    def semantic_search(self, query: str, top_k: Optional[int] = None,
                        filters: Optional[Dict[str, Any]] = None,
                        strategy: ContextStrategy = ContextStrategy.TOP_K) -> List[SearchResult]:
        """Rank chunks by TF-IDF style similarity and return the best ones."""
        if isinstance(strategy, str):
            try:
                strategy = ContextStrategy(strategy)
            except ValueError:
                strategy = ContextStrategy.TOP_K
        if not query or not query.strip():
            return []
        query_tokens = _content_tokens(query)
        if not query_tokens:
            return []
        k = max(1, int(top_k or self._config.top_k))
        filters = filters or {}
        raw_cat = filters.get("category")
        cat = self._coerce_category(raw_cat) if raw_cat is not None else None
        tag_filter = filters.get("tags")
        src_filter = filters.get("source")
        now = _now_ts()
        with self._lock:
            scored: List[Tuple[float, DocumentChunk, List[str]]] = []
            for chunk in self._chunks.values():
                doc = self._documents.get(chunk.doc_id)
                if doc is None:
                    continue
                if cat is not None and doc.category != cat:
                    continue
                if tag_filter and not all(t in doc.tags for t in tag_filter):
                    continue
                if src_filter is not None and doc.source != src_filter:
                    continue
                score, matched = self._score_chunk_locked(chunk, query_tokens)
                if strategy == ContextStrategy.TEMPORAL_DECAY:
                    age = _days_since(chunk.created_at, now)
                    score *= math.exp(-self._config.temporal_decay * age)
                if score >= self._config.min_score:
                    scored.append((score, chunk, matched))
            scored.sort(key=lambda item: item[0], reverse=True)
            top = scored[:k * 3]  # pool for diversity selection
            if strategy == ContextStrategy.DIVERSITY_WEIGHTED:
                top = self._mmr_select_locked(top, k)
            else:
                top = top[:k]
            results: List[SearchResult] = []
            for rank, (score, chunk, matched) in enumerate(top, start=1):
                doc = self._documents[chunk.doc_id]
                doc.touch()
                results.append(SearchResult(
                    chunk=self._clone_chunk(chunk),
                    document=self._clone_document(doc),
                    score=score, rank=rank, matched_terms=sorted(set(matched)),
                    explanation=(f"matched {len(set(matched))} term(s) "
                                 f"with tf-idf weight {_round(score)}")))
            self._record_search_locked(query, results)
            return results

    def get_context(self, query: str, strategy: ContextStrategy = ContextStrategy.TOP_K,
                    top_k: Optional[int] = None,
                    max_tokens: Optional[int] = None) -> ContextWindow:
        """Retrieve chunks for a query and pack them into a context window."""
        if isinstance(strategy, str):
            try:
                strategy = ContextStrategy(strategy)
            except ValueError:
                strategy = ContextStrategy.TOP_K
        results = self.semantic_search(query=query, top_k=top_k, strategy=strategy)
        with self._lock:
            max_t = int(max_tokens or self._config.max_context_tokens)
            chosen: List[DocumentChunk] = []
            tokens_used = 0
            citations: List[Dict[str, Any]] = []
            if strategy == ContextStrategy.GRAPH_EXPANDED:
                results = self._graph_expand_locked(query, results)
            for res in results:
                est = max(1, int(len(res.chunk.text) / 4))
                if tokens_used + est > max_t and chosen:
                    break
                chosen.append(res.chunk)
                tokens_used += est
                doc = self._documents.get(res.chunk.doc_id)
                citations.append({"rank": res.rank, "doc_id": res.chunk.doc_id,
                                   "chunk_id": res.chunk.chunk_id,
                                   "title": doc.title if doc else "",
                                   "source": doc.source if doc else "",
                                   "score": _round(res.score),
                                   "position": res.chunk.position})
            text = self._render_context_locked(query, chosen)
            return ContextWindow(query=query, strategy=strategy,
                                 chunks=[self._clone_chunk(c) for c in chosen],
                                 citations=citations, token_estimate=tokens_used,
                                 assembled_text=text)

    def assemble_context(self, query: str, strategy: ContextStrategy = ContextStrategy.TOP_K,
                         top_k: Optional[int] = None,
                         max_tokens: Optional[int] = None) -> str:
        """Return a formatted context string ready for model consumption."""
        if isinstance(strategy, str):
            try:
                strategy = ContextStrategy(strategy)
            except ValueError:
                strategy = ContextStrategy.TOP_K
        return self.get_context(query=query, strategy=strategy, top_k=top_k,
                                max_tokens=max_tokens).assembled_text

    def add_concept(self, name: str, category: DocumentCategory = DocumentCategory.UNKNOWN,
                    description: str = "",
                    metadata: Optional[Dict[str, Any]] = None) -> str:
        """Create a concept node, returning the existing id if present."""
        key = name.strip().lower()
        if not key:
            raise ValueError("concept name is required")
        with self._lock:
            existing = self._concept_index.get(key)
            if existing is not None:
                node = self._graph.nodes[existing]
                node.mentions += 1
                node.weight = _clamp(node.weight + 0.1, 0.0, 10.0)
                return existing
            if len(self._graph.nodes) >= _MAX_CONCEPTS:
                raise RuntimeError("concept capacity reached")
            cid = _uid("cpt")
            self._graph.nodes[cid] = KnowledgeGraphNode(
                concept_id=cid, name=name.strip(), category=category,
                description=description, metadata=dict(metadata or {}), mentions=1)
            self._concept_index[key] = cid
            return cid

    def get_concept(self, concept_id: str) -> Optional[KnowledgeGraphNode]:
        with self._lock:
            node = self._graph.nodes.get(concept_id)
            return self._clone_node(node) if node else None

    def link_concepts(self, source_id: str, target_id: str,
                      relation: ConceptRelation = ConceptRelation.RELATES_TO,
                      weight: float = 1.0,
                      metadata: Optional[Dict[str, Any]] = None) -> Optional[str]:
        """Create a typed edge between two concept nodes."""
        with self._lock:
            if source_id not in self._graph.nodes or target_id not in self._graph.nodes:
                return None
            if len(self._graph.edges) >= _MAX_EDGES:
                raise RuntimeError("edge capacity reached")
            # De-duplicate: update weight if an identical edge exists
            for edge in self._graph.edges.values():
                if (edge.source_id == source_id and edge.target_id == target_id
                        and edge.relation == relation):
                    edge.weight = _clamp(weight, 0.0, 10.0)
                    edge.metadata.update(metadata or {})
                    return edge.edge_id
            eid = _uid("edge")
            self._graph.edges[eid] = KnowledgeGraphEdge(
                edge_id=eid, source_id=source_id, target_id=target_id,
                relation=relation, weight=_clamp(weight, 0.0, 10.0),
                metadata=dict(metadata or {}))
            return eid

    def get_concept_neighbors(self, concept_id: str, depth: int = 1) -> List[Dict[str, Any]]:
        with self._lock:
            if concept_id not in self._graph.nodes:
                return []
            adj = self._build_adjacency_locked()
            visited: Set[str] = {concept_id}
            frontier: List[str] = [concept_id]
            output: List[Dict[str, Any]] = []
            for level in range(1, max(1, int(depth)) + 1):
                next_frontier: List[str] = []
                for nid in frontier:
                    for nbr_id, rels in adj.get(nid, []):
                        if nbr_id in visited:
                            continue
                        visited.add(nbr_id)
                        next_frontier.append(nbr_id)
                        node = self._graph.nodes[nbr_id]
                        output.append({"concept_id": nbr_id, "name": node.name,
                                       "category": node.category.value, "depth": level,
                                       "relations": list(rels)})
                frontier = next_frontier
                if not frontier:
                    break
            return output

    def find_concept_path(self, start_id: str, end_id: str) -> List[str]:
        with self._lock:
            if start_id not in self._graph.nodes or end_id not in self._graph.nodes:
                return []
            if start_id == end_id:
                return [start_id]
            adj = self._build_adjacency_locked()
            visited: Set[str] = {start_id}
            queue: Deque[Tuple[str, List[str]]] = deque([(start_id, [start_id])])
            while queue:
                current, path = queue.popleft()
                for nbr_id, _rels in adj.get(current, []):
                    if nbr_id in visited:
                        continue
                    new_path = path + [nbr_id]
                    if nbr_id == end_id:
                        return new_path
                    visited.add(nbr_id)
                    queue.append((nbr_id, new_path))
            return []

    def expand_query(self, query: str) -> QueryExpansion:
        tokens = _content_tokens(query)
        synonyms: Set[str] = set()
        expanded: Set[str] = set(tokens)
        for tok in tokens:
            for syn in _SYNONYMS.get(tok, set()):
                synonyms.add(syn)
                expanded.add(syn)
        related: List[str] = []
        with self._lock:
            for tok in tokens:
                cid = self._concept_index.get(tok)
                if not cid:
                    continue
                for nbr in self._neighbors_of_locked(cid):
                    node = self._graph.nodes.get(nbr)
                    if not node:
                        continue
                    name = node.name.lower()
                    if name not in expanded:
                        related.append(node.name)
                        expanded.add(name)
        return QueryExpansion(original=query, expanded_terms=sorted(expanded),
                              synonyms=sorted(synonyms), related_concepts=related,
                              reformulated=self._reformulate_locked(query, sorted(expanded)))

    def reformulate_query(self, query: str) -> str:
        return self.expand_query(query).reformulated

    def categorize_document(self, doc_id: str) -> Optional[DocumentCategory]:
        with self._lock:
            doc = self._documents.get(doc_id)
            if doc is None:
                return None
            category = self._classify_text_locked(f"{doc.title} {doc.content}")
            doc.category = category
            doc.updated_at = _now_ts()
            return category

    def merge_documents(self, doc_id_a: str, doc_id_b: str) -> Optional[str]:
        with self._lock:
            a = self._documents.get(doc_id_a)
            b = self._documents.get(doc_id_b)
            if a is None or b is None:
                return None
            a.content = f"{a.content}\n\n# Merged: {b.title}\n\n{b.content}"
            a.tags = sorted(set(a.tags) | set(b.tags))
            a.metadata.update(b.metadata)
            a.updated_at = _now_ts()
            self._remove_chunks_locked(a)
            self._chunk_and_index_locked(a)
            self._remove_chunks_locked(b)
            del self._documents[doc_id_b]
            return doc_id_a

    def detect_stale(self, max_age_days: Optional[int] = None) -> List[Dict[str, Any]]:
        threshold = int(max_age_days if max_age_days is not None else self._config.stale_days)
        now = _now_ts()
        output: List[Dict[str, Any]] = []
        with self._lock:
            for doc in self._documents.values():
                age_days = _days_since(doc.updated_at, now)
                if age_days >= threshold:
                    staleness = 1.0 if threshold <= 0 else _clamp(age_days / (threshold * 2.0))
                    output.append({"doc_id": doc.doc_id, "title": doc.title,
                                   "age_days": _round(age_days),
                                   "staleness": _round(staleness),
                                   "updated_at": doc.updated_at})
        output.sort(key=lambda d: d["staleness"], reverse=True)
        return output

    def get_statistics(self) -> RetrievalStats:
        with self._lock:
            return self._stats_locked()

    def get_search_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        with self._lock:
            history = list(self._search_history)
        history.reverse()
        return history[:max(0, int(limit))]

    def get_popular_queries(self, limit: int = 10) -> List[Dict[str, Any]]:
        with self._lock:
            ranked = self._query_counts.most_common(max(1, int(limit)))
            return [{"query": q, "count": c} for q, c in ranked]

    def export_knowledge_base(self) -> str:
        with self._lock:
            payload = self.to_dict()
        return json.dumps(payload, indent=2, sort_keys=True)

    def export_search_report(self, query: str,
                             results: Optional[List[SearchResult]] = None) -> str:
        """Render a human-readable report for a search and its results."""
        if results is None:
            results = self.semantic_search(query)
        lines: List[str] = ["=" * 72, "KNOWLEDGE RETRIEVAL REPORT", "=" * 72,
                            f"Query: {query}", f"Result count: {len(results)}",
                            "-" * 72]
        for res in results:
            lines.append(f"[{res.rank}] score={_round(res.score)} doc={res.document.title}")
            lines.append(f"    source={res.document.source} category={res.document.category.value}")
            lines.append(f"    matched={', '.join(res.matched_terms) or '(none)'}")
            excerpt = res.chunk.text.strip().replace("\n", " ")
            if len(excerpt) > 140:
                excerpt = excerpt[:137] + "..."
            lines.append(f"    excerpt: {excerpt}")
            lines.append("")
        lines.append("=" * 72)
        return "\n".join(lines)

    def ai_generate_knowledge(self, description: str,
                              category: DocumentCategory = DocumentCategory.GAME_DESIGN,
                              tags: Optional[List[str]] = None) -> str:
        """Produce a starter knowledge document from a short description."""
        if not description or not description.strip():
            raise ValueError("description is required")
        title = description.strip().split("\n")[0][:80]
        if len(title) < 3:
            title = "Generated Knowledge"
        body = "\n".join([f"# {title}", "", "## Overview", description.strip(), "",
                          "## Design Goals",
                          "- Provide clear player-facing feedback.",
                          "- Keep the implementation testable in isolation.",
                          "- Align with the overall game feel and pacing.", "",
                          "## Open Questions",
                          "- What are the failure states?",
                          "- How does this interact with progression?",
                          "- Which assets are required at runtime?", "",
                          "## Acceptance Criteria",
                          "- Behavior is deterministic under fixed input.",
                          "- Edge cases are documented and covered by tests.",
                          "- Performance stays within the allocated budget."])
        return self.add_document(title=title, content=body, source="ai_generated",
                                 category=category, tags=list(tags or []),
                                 content_format=ContentFormat.MARKDOWN,
                                 metadata={"generator": "ai_generate_knowledge"})

    def ai_validate_knowledge(self, doc_id: str) -> Dict[str, Any]:
        with self._lock:
            doc = self._documents.get(doc_id)
            if doc is None:
                return {"valid": False, "errors": ["document not found"]}
            contradictions: List[Dict[str, Any]] = []
            gaps: List[str] = []
            mentioned_ids: List[str] = []
            for name in self._extract_concepts_locked(doc.content):
                cid = self._concept_index.get(name.lower())
                if cid:
                    mentioned_ids.append(cid)
            # Find contradiction edges among mentioned concepts
            for edge in self._graph.edges.values():
                if edge.relation != ConceptRelation.CONTRADICTS:
                    continue
                if (edge.source_id in mentioned_ids and edge.target_id in mentioned_ids):
                    contradictions.append({
                        "concept_a": self._graph.nodes[edge.source_id].name,
                        "concept_b": self._graph.nodes[edge.target_id].name,
                        "edge_id": edge.edge_id})
            # Detect gaps: concepts with no neighbors
            for cid in mentioned_ids:
                if not self._neighbors_of_locked(cid):
                    gaps.append(f"concept '{self._graph.nodes[cid].name}' has no graph relations")
            lower = doc.content.lower()
            if "acceptance" not in lower and "criteria" not in lower:
                gaps.append("document lacks explicit acceptance criteria")
            if not doc.tags:
                gaps.append("document has no tags for retrieval filtering")
            return {"valid": len(contradictions) == 0, "doc_id": doc_id,
                    "title": doc.title, "contradictions": contradictions,
                    "gaps": gaps, "concept_count": len(mentioned_ids)}

    def _ingest_locked(self, spec: Dict[str, Any], doc_id: str) -> str:
        category = spec.get("category")
        if category is None and self._config.auto_categorize:
            category = self._classify_text_locked(f"{spec['title']} {spec['content']}")
        if category is None:
            category = DocumentCategory.UNKNOWN
        doc = KnowledgeDocument(doc_id=doc_id, title=str(spec["title"]),
                                content=str(spec["content"]),
                                source=str(spec.get("source", "internal")),
                                category=self._coerce_category(category),
                                tags=list(spec.get("tags") or []),
                                format=self._coerce_format(spec.get("format")),
                                metadata=dict(spec.get("metadata") or {}))
        self._documents[doc_id] = doc
        self._chunk_and_index_locked(doc)
        if self._config.auto_extract_concepts:
            self._extract_and_link_concepts_locked(doc)
        return doc_id

    def _chunk_and_index_locked(self, doc: KnowledgeDocument) -> None:
        chunks = self._split_into_chunks_locked(doc)[:_MAX_CHUNKS_PER_DOC]
        doc.chunk_ids = [c.chunk_id for c in chunks]
        for chunk in chunks:
            if len(self._chunks) >= _MAX_CHUNKS_TOTAL:
                raise RuntimeError("chunk capacity reached")
            self._chunks[chunk.chunk_id] = chunk
            chunk.embedding = self._simulate_embedding_locked(chunk.text)
            self._index_chunk_locked(chunk)

    def _split_into_chunks_locked(self, doc: KnowledgeDocument) -> List[DocumentChunk]:
        size = max(20, int(self._config.chunk_size))
        overlap = max(0, min(int(self._config.chunk_overlap), size - 1))
        words = _tokenize(doc.content) or [doc.title]
        meta = {"title": doc.title, "category": doc.category.value,
                "source": doc.source, "format": doc.format.value}
        chunks: List[DocumentChunk] = []
        pos, step = 0, max(1, size - overlap)
        while pos < len(words):
            text = " ".join(words[pos:pos + size])
            if text.strip():
                chunks.append(DocumentChunk(chunk_id=_uid("chk"), doc_id=doc.doc_id,
                                            text=text, position=pos, metadata=dict(meta)))
            if pos + size >= len(words):
                break
            pos += step
        if not chunks:
            chunks.append(DocumentChunk(chunk_id=_uid("chk"), doc_id=doc.doc_id,
                                        text=doc.content, position=0, metadata=dict(meta)))
        return chunks

    def _index_chunk_locked(self, chunk: DocumentChunk) -> None:
        for term in set(_content_tokens(chunk.text)):
            self._inverted_index.setdefault(term, set()).add(chunk.chunk_id)
            self._df[term] = self._df.get(term, 0) + 1

    def _remove_chunks_locked(self, doc: KnowledgeDocument) -> None:
        for cid in list(doc.chunk_ids):
            chunk = self._chunks.pop(cid, None)
            if chunk is None:
                continue
            for term in set(_content_tokens(chunk.text)):
                ids = self._inverted_index.get(term)
                if ids is None:
                    continue
                ids.discard(cid)
                if not ids:
                    self._inverted_index.pop(term, None)
                    self._df.pop(term, None)
                else:
                    self._df[term] = len(ids)
        doc.chunk_ids = []

    def _score_chunk_locked(self, chunk: DocumentChunk,
                            query_tokens: List[str]) -> Tuple[float, List[str]]:
        """Compute a TF-IDF style overlap score for a chunk."""
        chunk_tokens = _content_tokens(chunk.text)
        if not chunk_tokens or not query_tokens:
            return 0.0, []
        chunk_tf = Counter(chunk_tokens)
        query_tf = Counter(query_tokens)
        total_chunks = max(1, len(self._chunks))
        score, matched = 0.0, []
        for term, qf in query_tf.items():
            cf = chunk_tf.get(term, 0)
            if cf <= 0:
                continue
            df = self._df.get(term, 1)
            idf = math.log((total_chunks + 1) / (df + 1)) + 1.0
            score += (cf * qf) * idf
            matched.append(term)
        chunk_norm = math.sqrt(sum(c * c for c in chunk_tf.values())) or 1.0
        query_norm = math.sqrt(sum(q * q for q in query_tf.values())) or 1.0
        return _clamp(score / (chunk_norm * query_norm)), matched

    def _simulate_embedding_locked(self, text: str) -> List[float]:
        tokens = _content_tokens(text)
        vec = [0.0] * _EMBEDDING_DIM
        if not tokens:
            return vec
        for token in tokens:
            h = int(hashlib.md5(token.encode("utf-8")).hexdigest(), 16)
            vec[h % _EMBEDDING_DIM] += 1.0 if (h >> 8) % 2 == 0 else -1.0
        norm = math.sqrt(sum(v * v for v in vec)) or 1.0
        return [_round(v / norm) for v in vec]

    def _mmr_select_locked(self, scored: List[Tuple[float, DocumentChunk, List[str]]],
                           k: int) -> List[Tuple[float, DocumentChunk, List[str]]]:
        """Pick results that balance relevance against redundancy (MMR)."""
        if not scored:
            return []
        lam = _clamp(self._config.diversity_lambda, 0.0, 1.0)
        selected: List[Tuple[float, DocumentChunk, List[str]]] = []
        pool = list(scored)
        while pool and len(selected) < k:
            best_idx, best_score = 0, -1.0
            for i, (rel, chunk, matched) in enumerate(pool):
                redundancy = max((self._chunk_similarity_locked(chunk, sc)
                                  for _, sc, _ in selected), default=0.0)
                mmr = lam * rel - (1.0 - lam) * redundancy
                if mmr > best_score:
                    best_score, best_idx = mmr, i
            selected.append(pool.pop(best_idx))
        return selected

    def _chunk_similarity_locked(self, a: DocumentChunk, b: DocumentChunk) -> float:
        ta = Counter(_content_tokens(a.text))
        tb = Counter(_content_tokens(b.text))
        if not ta or not tb:
            return 0.0
        shared = sum(ta[t] * tb[t] for t in ta.keys() & tb.keys())
        na = math.sqrt(sum(v * v for v in ta.values())) or 1.0
        nb = math.sqrt(sum(v * v for v in tb.values())) or 1.0
        return _clamp(shared / (na * nb))

    def _graph_expand_locked(self, query: str,
                             results: List[SearchResult]) -> List[SearchResult]:
        """Add chunks tied to concepts that appear in the query."""
        if not results:
            return results
        query_terms = _content_tokens(query)
        extra_ids: Set[str] = set()
        for tok in query_terms:
            cid = self._concept_index.get(tok)
            if not cid:
                continue
            for nbr in self._neighbors_of_locked(cid):
                node = self._graph.nodes.get(nbr)
                if node:
                    extra_ids.update(self._inverted_index.get(node.name.lower(), set()))
        if not extra_ids:
            return results
        output = list(results)
        existing_ids = {r.chunk.chunk_id for r in results}
        for cid in extra_ids:
            if cid in existing_ids:
                continue
            chunk = self._chunks.get(cid)
            doc = self._documents.get(chunk.doc_id) if chunk else None
            if chunk is None or doc is None:
                continue
            score, _ = self._score_chunk_locked(chunk, query_terms)
            output.append(SearchResult(chunk=chunk, document=doc,
                                       score=max(score, self._config.min_score),
                                       rank=0, matched_terms=[],
                                       explanation="graph expansion addition"))
        output.sort(key=lambda r: r.score, reverse=True)
        for rank, res in enumerate(output, start=1):
            res.rank = rank
        return output

    def _extract_and_link_concepts_locked(self, doc: KnowledgeDocument) -> None:
        created_ids: List[str] = []
        for name in self._extract_concepts_locked(doc.content):
            try:
                cid = self.add_concept(name=name, category=doc.category,
                                       description=f"Mentioned in {doc.title}",
                                       metadata={"doc_id": doc.doc_id})
            except RuntimeError:
                break  # capacity reached; stop adding concepts
            created_ids.append(cid)
        # Link concepts that co-occur in the same document
        for i in range(len(created_ids)):
            for j in range(i + 1, len(created_ids)):
                self.link_concepts(created_ids[i], created_ids[j],
                                   relation=ConceptRelation.RELATES_TO, weight=0.5)

    def _extract_concepts_locked(self, text: str) -> List[str]:
        names: List[str] = []
        seen: Set[str] = set()
        # Capitalized words are good signals for concept names
        for match in re.finditer(r"\b([A-Z][a-z]{2,})\b", text or ""):
            name = match.group(1)
            key = name.lower()
            if key not in _STOPWORDS and key not in seen:
                seen.add(key)
                names.append(name)
        # Prominent nouns from keyword signals
        for tok in _content_tokens(text):
            for kws in _CATEGORY_KEYWORDS.values():
                if tok in kws and tok not in seen:
                    seen.add(tok)
                    names.append(tok.capitalize())
                    break
        return names[:32]

    def _build_adjacency_locked(self) -> Dict[str, List[Tuple[str, List[str]]]]:
        adj: Dict[str, List[Tuple[str, List[str]]]] = {}
        for edge in self._graph.edges.values():
            rels = adj.setdefault(edge.source_id, [])
            entry = next((e for e in rels if e[0] == edge.target_id), None)
            if entry is None:
                rels.append((edge.target_id, [edge.relation.value]))
            else:
                entry[1].append(edge.relation.value)
            rels_rev = adj.setdefault(edge.target_id, [])
            entry_rev = next((e for e in rels_rev if e[0] == edge.source_id), None)
            if entry_rev is None:
                rels_rev.append((edge.source_id, [edge.relation.value]))
            else:
                entry_rev[1].append(edge.relation.value)
        return adj

    def _neighbors_of_locked(self, concept_id: str) -> List[str]:
        return [nbr for nbr, _rels in self._build_adjacency_locked().get(concept_id, [])]

    def _classify_text_locked(self, text: str) -> DocumentCategory:
        tokens = set(_content_tokens(text))
        if not tokens:
            return DocumentCategory.UNKNOWN
        best_cat, best_score = DocumentCategory.UNKNOWN, 0
        for cat, kws in _CATEGORY_KEYWORDS.items():
            score = len(tokens & kws)
            if score > best_score:
                best_score, best_cat = score, cat
        return best_cat

    def _render_context_locked(self, query: str, chunks: List[DocumentChunk]) -> str:
        if not chunks:
            return f"[Context for query: {query}]\n(no relevant knowledge found)\n"
        lines: List[str] = [f"[Context for query: {query}]", ""]
        for idx, chunk in enumerate(chunks, start=1):
            doc = self._documents.get(chunk.doc_id)
            title = doc.title if doc else "Unknown"
            source = doc.source if doc else "unknown"
            lines.append(f"--- Excerpt {idx} | {title} ({source}) ---")
            lines.append(chunk.text.strip())
            lines.append("")
        return "\n".join(lines)

    def _reformulate_locked(self, query: str, expanded_terms: List[str]) -> str:
        if not expanded_terms:
            return query
        query_tokens = set(_content_tokens(query))
        extra = [t for t in expanded_terms if t.lower() not in query_tokens][:4]
        return f"{query} (related: {', '.join(extra)})" if extra else query

    def _record_search_locked(self, query: str, results: List[SearchResult]) -> None:
        self._search_history.append({
            "at": _now_ts(), "query": query, "result_count": len(results),
            "top_score": _round(results[0].score) if results else 0.0,
            "top_doc_id": results[0].chunk.doc_id if results else None})
        self._query_counts[query] += 1

    def _stats_locked(self) -> RetrievalStats:
        chunk_sizes = [len(c.text) for c in self._chunks.values()]
        avg = (sum(chunk_sizes) / len(chunk_sizes)) if chunk_sizes else 0.0
        dist: Dict[str, int] = {}
        for doc in self._documents.values():
            dist[doc.category.value] = dist.get(doc.category.value, 0) + 1
        popular = [{"query": q, "count": c}
                    for q, c in self._query_counts.most_common(_MAX_POPULAR_QUERIES)]
        return RetrievalStats(document_count=len(self._documents),
                              chunk_count=len(self._chunks),
                              concept_count=len(self._graph.nodes),
                              edge_count=len(self._graph.edges),
                              average_chunk_size=avg, category_distribution=dist,
                              search_count=sum(self._query_counts.values()),
                              last_search_at=(self._search_history[-1]["at"]
                                              if self._search_history else None),
                              popular_queries=popular)

    def _snapshot_config(self) -> RetrievalConfig:
        return RetrievalConfig(**self._config.to_dict())

    @staticmethod
    def _coerce_category(value: Any) -> DocumentCategory:
        return _coerce_enum(DocumentCategory, value, DocumentCategory.UNKNOWN)

    @staticmethod
    def _coerce_format(value: Any) -> ContentFormat:
        return _coerce_enum(ContentFormat, value, ContentFormat.TEXT)

    @staticmethod
    def _clone_chunk(chunk: DocumentChunk) -> DocumentChunk:
        return DocumentChunk(chunk_id=chunk.chunk_id, doc_id=chunk.doc_id, text=chunk.text,
                             embedding=list(chunk.embedding), position=chunk.position,
                             metadata=dict(chunk.metadata), created_at=chunk.created_at)

    @staticmethod
    def _clone_document(doc: KnowledgeDocument) -> KnowledgeDocument:
        return KnowledgeDocument(doc_id=doc.doc_id, title=doc.title, content=doc.content,
                                 source=doc.source, category=doc.category, tags=list(doc.tags),
                                 format=doc.format, metadata=dict(doc.metadata),
                                 chunk_ids=list(doc.chunk_ids), created_at=doc.created_at,
                                 updated_at=doc.updated_at, access_count=doc.access_count)

    @staticmethod
    def _clone_node(node: KnowledgeGraphNode) -> KnowledgeGraphNode:
        return KnowledgeGraphNode(concept_id=node.concept_id, name=node.name,
                                  category=node.category, description=node.description,
                                  weight=node.weight, metadata=dict(node.metadata),
                                  mentions=node.mentions, created_at=node.created_at)

def get_knowledge_retrieval() -> KnowledgeRetrievalSystem:
    """Return the shared :class:`KnowledgeRetrievalSystem` instance."""
    return KnowledgeRetrievalSystem.get_instance()

__all__ = [
    "ConceptRelation", "ContentFormat", "ContextStrategy", "ContextWindow",
    "DocumentCategory", "DocumentChunk", "KnowledgeDocument", "KnowledgeGraph",
    "KnowledgeGraphEdge", "KnowledgeGraphNode", "KnowledgeRetrievalSystem",
    "QueryExpansion", "RetrievalConfig", "RetrievalStats", "SearchResult",
    "get_knowledge_retrieval",
]
