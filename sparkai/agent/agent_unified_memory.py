"""
SparkLabs Agent - Unified Memory System

A cognitive-architecture-inspired unified memory system that provides
four distinct memory stores with automatic consolidation across layers.
The system models human-like memory processes: working memory for active
reasoning, episodic memory for experiential records, semantic memory for
factual knowledge, and procedural memory for learned skills.

Architecture:
  UnifiedMemorySystem (Singleton)
    |-- WorkingMemory (highly active, capacity-limited scratchpad)
    |-- EpisodicMemory (time-indexed experience records)
    |-- SemanticMemory (structured knowledge graph)
    |-- ProceduralMemory (skill and procedure storage)
    |-- MemoryConsolidationEngine (cross-layer consolidation)
    |-- MemoryRetrievalEngine (similarity-based multi-store retrieval)
"""

from __future__ import annotations

import math
import threading
import time as _time_module
import uuid
from collections import OrderedDict
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple


class MemoryLayerType(Enum):
    """Designates the cognitive layer of a memory fragment."""
    WORKING = "working"
    EPISODIC = "episodic"
    SEMANTIC = "semantic"
    PROCEDURAL = "procedural"


class MemoryActivation(Enum):
    """Activation level of a memory entry."""
    DORMANT = "dormant"
    PRIMED = "primed"
    ACTIVE = "active"
    RETRIEVED = "retrieved"


class ConsolidationPhase(Enum):
    """Phase of the memory consolidation pipeline."""
    IDLE = "idle"
    ENCODING = "encoding"
    STABILIZING = "stabilizing"
    GENERALIZING = "generalizing"
    ABSTRACTING = "abstracting"
    COMPLETE = "complete"


@dataclass
class MemoryChunk:
    """A single unit of memory that can reside in any memory layer."""
    chunk_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    content: str = ""
    layer: MemoryLayerType = MemoryLayerType.WORKING
    activation: MemoryActivation = MemoryActivation.ACTIVE
    importance: float = 0.5
    relevance: float = 0.5
    access_count: int = 0
    created_at: float = field(default_factory=_time_module.time)
    last_accessed: float = field(default_factory=_time_module.time)
    tags: List[str] = field(default_factory=list)
    associations: List[str] = field(default_factory=list)
    source_layer: Optional[MemoryLayerType] = None
    decay_rate: float = 0.01
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "chunk_id": self.chunk_id,
            "content": self.content,
            "layer": self.layer.value,
            "activation": self.activation.value,
            "importance": self.importance,
            "relevance": self.relevance,
            "access_count": self.access_count,
            "created_at": self.created_at,
            "last_accessed": self.last_accessed,
            "tags": self.tags,
            "associations": self.associations,
            "source_layer": self.source_layer.value if self.source_layer else None,
            "decay_rate": self.decay_rate,
            "metadata": self.metadata,
        }

    def activation_value(self, current_time: Optional[float] = None) -> float:
        """Compute the current activation value accounting for decay."""
        t = current_time or _time_module.time()
        elapsed = t - self.last_accessed
        decay = math.exp(-self.decay_rate * elapsed)
        base = self.importance * 0.4 + self.relevance * 0.3 + min(self.access_count * 0.05, 0.3)
        return base * decay


class WorkingMemory:
    """
    Capacity-limited memory store for active reasoning.
    Maintains a small set of highly accessible chunks that represent
    the agent's current cognitive context.
    """

    def __init__(self, capacity: int = 7) -> None:
        self._capacity = capacity
        self._chunks: OrderedDict[str, MemoryChunk] = OrderedDict()
        self._lock = threading.RLock()

    @property
    def capacity(self) -> int:
        return self._capacity

    @property
    def size(self) -> int:
        return len(self._chunks)

    def add(self, content: str, importance: float = 0.5, tags: Optional[List[str]] = None) -> MemoryChunk:
        """Add a chunk to working memory, evicting the least active if full."""
        with self._lock:
            chunk = MemoryChunk(
                content=content,
                layer=MemoryLayerType.WORKING,
                importance=importance,
                tags=tags or [],
            )
            if len(self._chunks) >= self._capacity:
                self._evict_least_active()
            self._chunks[chunk.chunk_id] = chunk
            return chunk

    def get(self, chunk_id: str) -> Optional[MemoryChunk]:
        """Retrieve a chunk by ID and update its access metadata."""
        with self._lock:
            chunk = self._chunks.get(chunk_id)
            if chunk:
                chunk.access_count += 1
                chunk.last_accessed = _time_module.time()
                chunk.activation = MemoryActivation.RETRIEVED
            return chunk

    def query(self, tags: Optional[List[str]] = None, min_importance: float = 0.0) -> List[MemoryChunk]:
        """Query working memory by tags and importance threshold."""
        with self._lock:
            results = list(self._chunks.values())
            if tags:
                results = [c for c in results if any(t in c.tags for t in tags)]
            results = [c for c in results if c.importance >= min_importance]
            for c in results:
                c.access_count += 1
                c.last_accessed = _time_module.time()
            return results

    def remove(self, chunk_id: str) -> bool:
        with self._lock:
            if chunk_id in self._chunks:
                del self._chunks[chunk_id]
                return True
            return False

    def clear(self) -> None:
        with self._lock:
            self._chunks.clear()

    def to_dict(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "capacity": self._capacity,
                "size": len(self._chunks),
                "chunks": [c.to_dict() for c in self._chunks.values()],
            }

    def _evict_least_active(self) -> None:
        """Evict the chunk with the lowest activation value."""
        if not self._chunks:
            return
        t = _time_module.time()
        weakest_id = min(self._chunks.keys(), key=lambda cid: self._chunks[cid].activation_value(t))
        del self._chunks[weakest_id]


class EpisodicMemory:
    """
    Time-indexed store for experiential records.
    Stores sequences of events with temporal context, forming the
    agent's autobiographical memory.
    """

    def __init__(self, max_episodes: int = 10000) -> None:
        self._max_episodes = max_episodes
        self._chunks: Dict[str, MemoryChunk] = {}
        self._episode_index: Dict[str, List[str]] = {}
        self._time_index: List[Tuple[float, str]] = []
        self._lock = threading.RLock()

    def store(self, content: str, episode_id: str = "", importance: float = 0.5,
              tags: Optional[List[str]] = None, associations: Optional[List[str]] = None) -> MemoryChunk:
        """Store an episodic memory chunk."""
        with self._lock:
            chunk = MemoryChunk(
                content=content,
                layer=MemoryLayerType.EPISODIC,
                importance=importance,
                activation=MemoryActivation.PRIMED,
                tags=tags or [],
                associations=associations or [],
            )
            if len(self._chunks) >= self._max_episodes:
                self._evict_oldest()
            self._chunks[chunk.chunk_id] = chunk
            if episode_id:
                if episode_id not in self._episode_index:
                    self._episode_index[episode_id] = []
                self._episode_index[episode_id].append(chunk.chunk_id)
            self._time_index.append((chunk.created_at, chunk.chunk_id))
            return chunk

    def retrieve(self, chunk_id: str) -> Optional[MemoryChunk]:
        with self._lock:
            chunk = self._chunks.get(chunk_id)
            if chunk:
                chunk.access_count += 1
                chunk.last_accessed = _time_module.time()
            return chunk

    def retrieve_by_episode(self, episode_id: str) -> List[MemoryChunk]:
        with self._lock:
            ids = self._episode_index.get(episode_id, [])
            chunks = [self._chunks[cid] for cid in ids if cid in self._chunks]
            for c in chunks:
                c.access_count += 1
                c.last_accessed = _time_module.time()
            return chunks

    def retrieve_recent(self, limit: int = 20) -> List[MemoryChunk]:
        with self._lock:
            sorted_ids = sorted(self._time_index, key=lambda x: x[0], reverse=True)[:limit]
            chunks = [self._chunks[cid] for _, cid in sorted_ids if cid in self._chunks]
            return chunks

    def query_by_tags(self, tags: List[str], limit: int = 50) -> List[MemoryChunk]:
        with self._lock:
            results = [c for c in self._chunks.values() if any(t in c.tags for t in tags)]
            results.sort(key=lambda c: c.created_at, reverse=True)
            return results[:limit]

    def to_dict(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "total_episodes": len(self._chunks),
                "episode_count": len(self._episode_index),
                "max_episodes": self._max_episodes,
            }

    def _evict_oldest(self) -> None:
        if self._time_index:
            self._time_index.sort(key=lambda x: x[0])
            oldest_time, oldest_id = self._time_index.pop(0)
            if oldest_id in self._chunks:
                del self._chunks[oldest_id]


class SemanticMemory:
    """
    Structured knowledge store for facts, concepts, and relationships.
    Organizes knowledge into domains with cross-referencing.
    """

    def __init__(self) -> None:
        self._chunks: Dict[str, MemoryChunk] = {}
        self._domain_index: Dict[str, List[str]] = {}
        self._relation_graph: Dict[str, Set[str]] = {}
        self._lock = threading.RLock()

    def store(self, content: str, domain: str = "", importance: float = 0.5,
              tags: Optional[List[str]] = None, associations: Optional[List[str]] = None) -> MemoryChunk:
        """Store a semantic knowledge chunk."""
        with self._lock:
            chunk = MemoryChunk(
                content=content,
                layer=MemoryLayerType.SEMANTIC,
                importance=importance,
                activation=MemoryActivation.DORMANT,
                tags=tags or [],
                associations=associations or [],
            )
            self._chunks[chunk.chunk_id] = chunk
            if domain:
                if domain not in self._domain_index:
                    self._domain_index[domain] = []
                self._domain_index[domain].append(chunk.chunk_id)
            for assoc in chunk.associations:
                if assoc in self._chunks:
                    if chunk.chunk_id not in self._relation_graph:
                        self._relation_graph[chunk.chunk_id] = set()
                    self._relation_graph[chunk.chunk_id].add(assoc)
            return chunk

    def retrieve(self, chunk_id: str) -> Optional[MemoryChunk]:
        with self._lock:
            chunk = self._chunks.get(chunk_id)
            if chunk:
                chunk.access_count += 1
                chunk.last_accessed = _time_module.time()
            return chunk

    def retrieve_by_domain(self, domain: str) -> List[MemoryChunk]:
        with self._lock:
            ids = self._domain_index.get(domain, [])
            return [self._chunks[cid] for cid in ids if cid in self._chunks]

    def retrieve_related(self, chunk_id: str) -> List[MemoryChunk]:
        with self._lock:
            related_ids = self._relation_graph.get(chunk_id, set())
            return [self._chunks[cid] for cid in related_ids if cid in self._chunks]

    def list_domains(self) -> List[str]:
        with self._lock:
            return list(self._domain_index.keys())

    def to_dict(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "total_chunks": len(self._chunks),
                "domains": list(self._domain_index.keys()),
                "domain_count": len(self._domain_index),
                "relation_count": sum(len(v) for v in self._relation_graph.values()),
            }


class ProceduralMemory:
    """
    Skill and procedure memory store.
    Holds sequences of actions, learned procedures, and motor patterns
    that can be executed automatically.
    """

    def __init__(self) -> None:
        self._chunks: Dict[str, MemoryChunk] = {}
        self._procedure_index: Dict[str, List[str]] = {}
        self._lock = threading.RLock()

    def store(self, content: str, procedure_name: str = "", importance: float = 0.5,
              tags: Optional[List[str]] = None) -> MemoryChunk:
        """Store a procedural memory chunk."""
        with self._lock:
            chunk = MemoryChunk(
                content=content,
                layer=MemoryLayerType.PROCEDURAL,
                importance=importance,
                activation=MemoryActivation.DORMANT,
                tags=tags or [],
                decay_rate=0.001,
            )
            self._chunks[chunk.chunk_id] = chunk
            if procedure_name:
                if procedure_name not in self._procedure_index:
                    self._procedure_index[procedure_name] = []
                self._procedure_index[procedure_name].append(chunk.chunk_id)
            return chunk

    def retrieve(self, chunk_id: str) -> Optional[MemoryChunk]:
        with self._lock:
            chunk = self._chunks.get(chunk_id)
            if chunk:
                chunk.access_count += 1
                chunk.last_accessed = _time_module.time()
            return chunk

    def retrieve_by_procedure(self, procedure_name: str) -> List[MemoryChunk]:
        with self._lock:
            ids = self._procedure_index.get(procedure_name, [])
            return [self._chunks[cid] for cid in ids if cid in self._chunks]

    def list_procedures(self) -> List[str]:
        with self._lock:
            return list(self._procedure_index.keys())

    def to_dict(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "total_chunks": len(self._chunks),
                "procedures": list(self._procedure_index.keys()),
                "procedure_count": len(self._procedure_index),
            }


class MemoryConsolidationEngine:
    """
    Consolidates memories across layers following cognitive consolidation
    theory: working memory chunks stabilize into episodic records, which
    generalize into semantic knowledge, which abstract into procedural skills.
    """

    def __init__(self) -> None:
        self._consolidation_log: List[Dict[str, Any]] = []
        self._lock = threading.RLock()

    def consolidate_working_to_episodic(
        self,
        working: WorkingMemory,
        episodic: EpisodicMemory,
        episode_id: str = "",
        importance_threshold: float = 0.3,
    ) -> List[MemoryChunk]:
        """Consolidate active working memory chunks into episodic memory."""
        with self._lock:
            consolidated: List[MemoryChunk] = []
            for chunk in working.query(min_importance=importance_threshold):
                if chunk.importance >= importance_threshold:
                    ep_chunk = episodic.store(
                        content=chunk.content,
                        episode_id=episode_id,
                        importance=chunk.importance * 0.8,
                        tags=chunk.tags,
                        associations=chunk.associations,
                    )
                    ep_chunk.source_layer = MemoryLayerType.WORKING
                    consolidated.append(ep_chunk)
            if consolidated:
                self._consolidation_log.append({
                    "phase": "working_to_episodic",
                    "count": len(consolidated),
                    "timestamp": _time_module.time(),
                })
            return consolidated

    def consolidate_episodic_to_semantic(
        self,
        episodic: EpisodicMemory,
        semantic: SemanticMemory,
        min_episodes: int = 3,
        similarity_threshold: float = 0.6,
    ) -> List[MemoryChunk]:
        """Consolidate recurring episodic patterns into semantic knowledge."""
        with self._lock:
            consolidated: List[MemoryChunk] = []
            recent = episodic.retrieve_recent(limit=100)
            if len(recent) < min_episodes:
                return consolidated

            groups: Dict[str, List[MemoryChunk]] = {}
            for chunk in recent:
                key = _extract_pattern_key(chunk.content)
                if key not in groups:
                    groups[key] = []
                groups[key].append(chunk)

            for key, group in groups.items():
                if len(group) >= min_episodes:
                    avg_importance = sum(c.importance for c in group) / len(group)
                    all_tags = list(set(t for c in group for t in c.tags))
                    sem_chunk = semantic.store(
                        content=f"Pattern: {key} (from {len(group)} episodes)",
                        domain=all_tags[0] if all_tags else "general",
                        importance=avg_importance,
                        tags=all_tags,
                        associations=[c.chunk_id for c in group],
                    )
                    sem_chunk.source_layer = MemoryLayerType.EPISODIC
                    consolidated.append(sem_chunk)

            if consolidated:
                self._consolidation_log.append({
                    "phase": "episodic_to_semantic",
                    "count": len(consolidated),
                    "timestamp": _time_module.time(),
                })
            return consolidated

    def consolidate_semantic_to_procedural(
        self,
        semantic: SemanticMemory,
        procedural: ProceduralMemory,
        min_chunks: int = 5,
    ) -> List[MemoryChunk]:
        """Consolidate semantic knowledge clusters into procedural skills."""
        with self._lock:
            consolidated: List[MemoryChunk] = []
            for domain in semantic.list_domains():
                domain_chunks = semantic.retrieve_by_domain(domain)
                if len(domain_chunks) >= min_chunks:
                    avg_importance = sum(c.importance for c in domain_chunks) / len(domain_chunks)
                    all_tags = list(set(t for c in domain_chunks for t in c.tags))
                    proc_chunk = procedural.store(
                        content=f"Domain procedure: {domain} (from {len(domain_chunks)} knowledge chunks)",
                        procedure_name=domain,
                        importance=avg_importance * 0.9,
                        tags=all_tags,
                    )
                    proc_chunk.source_layer = MemoryLayerType.SEMANTIC
                    consolidated.append(proc_chunk)

            if consolidated:
                self._consolidation_log.append({
                    "phase": "semantic_to_procedural",
                    "count": len(consolidated),
                    "timestamp": _time_module.time(),
                })
            return consolidated

    def run_full_consolidation(
        self,
        working: WorkingMemory,
        episodic: EpisodicMemory,
        semantic: SemanticMemory,
        procedural: ProceduralMemory,
        episode_id: str = "",
    ) -> Dict[str, int]:
        """Run the complete consolidation pipeline across all layers."""
        results: Dict[str, int] = {}
        w2e = self.consolidate_working_to_episodic(working, episodic, episode_id)
        results["working_to_episodic"] = len(w2e)
        e2s = self.consolidate_episodic_to_semantic(episodic, semantic)
        results["episodic_to_semantic"] = len(e2s)
        s2p = self.consolidate_semantic_to_procedural(semantic, procedural)
        results["semantic_to_procedural"] = len(s2p)
        return results

    def to_dict(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "total_consolidations": len(self._consolidation_log),
                "recent_consolidations": self._consolidation_log[-10:],
            }


class MemoryRetrievalEngine:
    """
    Retrieves memories across all stores using similarity-based search.
    Combines results from multiple memory layers with weighted relevance.
    """

    def __init__(self) -> None:
        self._lock = threading.RLock()

    def retrieve(
        self,
        query: str,
        working: WorkingMemory,
        episodic: EpisodicMemory,
        semantic: SemanticMemory,
        procedural: ProceduralMemory,
        max_results: int = 10,
    ) -> List[Dict[str, Any]]:
        """Retrieve memories from all layers matching the query."""
        with self._lock:
            results: List[Tuple[float, MemoryChunk]] = []

            for chunk in working.query():
                sim = _compute_similarity(query, chunk.content)
                results.append((sim * 1.2, chunk))

            for chunk in episodic.retrieve_recent(limit=50):
                sim = _compute_similarity(query, chunk.content)
                results.append((sim * 0.8, chunk))

            for domain in semantic.list_domains()[:5]:
                for chunk in semantic.retrieve_by_domain(domain):
                    sim = _compute_similarity(query, chunk.content)
                    results.append((sim * 0.6, chunk))

            for proc_name in procedural.list_procedures()[:5]:
                for chunk in procedural.retrieve_by_procedure(proc_name):
                    sim = _compute_similarity(query, chunk.content)
                    results.append((sim * 0.5, chunk))

            results.sort(key=lambda x: x[0], reverse=True)
            top = results[:max_results]

            return [
                {
                    "chunk": chunk.to_dict(),
                    "score": round(score, 4),
                    "layer": chunk.layer.value,
                }
                for score, chunk in top
            ]

    def retrieve_by_layer(
        self,
        layer: MemoryLayerType,
        working: WorkingMemory,
        episodic: EpisodicMemory,
        semantic: SemanticMemory,
        procedural: ProceduralMemory,
        query: str = "",
        limit: int = 20,
    ) -> List[MemoryChunk]:
        """Retrieve memories from a specific layer."""
        with self._lock:
            if layer == MemoryLayerType.WORKING:
                chunks = working.query()
            elif layer == MemoryLayerType.EPISODIC:
                chunks = episodic.retrieve_recent(limit=limit)
            elif layer == MemoryLayerType.SEMANTIC:
                chunks = []
                for domain in semantic.list_domains():
                    chunks.extend(semantic.retrieve_by_domain(domain))
            elif layer == MemoryLayerType.PROCEDURAL:
                chunks = []
                for proc in procedural.list_procedures():
                    chunks.extend(procedural.retrieve_by_procedure(proc))
            else:
                return []

            if query:
                chunks.sort(key=lambda c: _compute_similarity(query, c.content), reverse=True)
            return chunks[:limit]


def _extract_pattern_key(content: str, max_length: int = 80) -> str:
    """Extract a simplified pattern key from content for grouping."""
    words = content.lower().split()
    if not words:
        return "empty"
    significant = [w for w in words if len(w) > 3][:5]
    if not significant:
        significant = words[:3]
    return " ".join(significant)[:max_length]


def _compute_similarity(query: str, content: str) -> float:
    """Compute a simple token-overlap similarity score."""
    if not query or not content:
        return 0.0
    query_tokens = set(query.lower().split())
    content_tokens = set(content.lower().split())
    if not query_tokens:
        return 0.0
    intersection = query_tokens & content_tokens
    return len(intersection) / len(query_tokens)


class UnifiedMemorySystem:
    """
    Cognitive-architecture-inspired unified memory system.

    Provides four distinct memory stores with automatic consolidation
    across layers, modeling human-like memory processes for AI agents.
    """

    _instance = None
    _lock = threading.RLock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if hasattr(self, "_initialized") and self._initialized:
            return
        self._initialized = True
        self._working = WorkingMemory(capacity=7)
        self._episodic = EpisodicMemory(max_episodes=10000)
        self._semantic = SemanticMemory()
        self._procedural = ProceduralMemory()
        self._consolidation_engine = MemoryConsolidationEngine()
        self._retrieval_engine = MemoryRetrievalEngine()
        self._current_episode_id: str = ""
        self._consolidation_interval: float = 300.0
        self._last_consolidation: float = _time_module.time()

    @classmethod
    def get_instance(cls) -> "UnifiedMemorySystem":
        return cls()

    @property
    def working(self) -> WorkingMemory:
        return self._working

    @property
    def episodic(self) -> EpisodicMemory:
        return self._episodic

    @property
    def semantic(self) -> SemanticMemory:
        return self._semantic

    @property
    def procedural(self) -> ProceduralMemory:
        return self._procedural

    @property
    def consolidation(self) -> MemoryConsolidationEngine:
        return self._consolidation_engine

    @property
    def retrieval(self) -> MemoryRetrievalEngine:
        return self._retrieval_engine

    def start_episode(self, episode_id: str = "") -> str:
        """Begin a new episodic memory episode."""
        with self._lock:
            self._current_episode_id = episode_id or str(uuid.uuid4().hex)
            return self._current_episode_id

    def remember(self, content: str, importance: float = 0.5,
                 tags: Optional[List[str]] = None) -> MemoryChunk:
        """Store content in working memory and trigger consolidation if needed."""
        with self._lock:
            chunk = self._working.add(content, importance=importance, tags=tags)
            self._maybe_consolidate()
            return chunk

    def recall(self, query: str, max_results: int = 10) -> List[Dict[str, Any]]:
        """Retrieve memories across all layers matching the query."""
        return self._retrieval_engine.retrieve(
            query=query,
            working=self._working,
            episodic=self._episodic,
            semantic=self._semantic,
            procedural=self._procedural,
            max_results=max_results,
        )

    def store_episode(self, content: str, importance: float = 0.5,
                      tags: Optional[List[str]] = None) -> MemoryChunk:
        """Directly store an episodic memory."""
        return self._episodic.store(
            content=content,
            episode_id=self._current_episode_id,
            importance=importance,
            tags=tags,
        )

    def store_knowledge(self, content: str, domain: str = "",
                        importance: float = 0.5,
                        tags: Optional[List[str]] = None) -> MemoryChunk:
        """Directly store semantic knowledge."""
        return self._semantic.store(
            content=content,
            domain=domain,
            importance=importance,
            tags=tags,
        )

    def store_procedure(self, content: str, procedure_name: str = "",
                        importance: float = 0.5,
                        tags: Optional[List[str]] = None) -> MemoryChunk:
        """Directly store a procedural memory."""
        return self._procedural.store(
            content=content,
            procedure_name=procedure_name,
            importance=importance,
            tags=tags,
        )

    def consolidate(self) -> Dict[str, int]:
        """Run the full consolidation pipeline."""
        with self._lock:
            results = self._consolidation_engine.run_full_consolidation(
                working=self._working,
                episodic=self._episodic,
                semantic=self._semantic,
                procedural=self._procedural,
                episode_id=self._current_episode_id,
            )
            self._last_consolidation = _time_module.time()
            return results

    def get_stats(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "working": self._working.to_dict(),
                "episodic": self._episodic.to_dict(),
                "semantic": self._semantic.to_dict(),
                "procedural": self._procedural.to_dict(),
                "consolidation": self._consolidation_engine.to_dict(),
                "current_episode_id": self._current_episode_id,
                "last_consolidation": self._last_consolidation,
            }

    def _maybe_consolidate(self) -> None:
        """Trigger consolidation if the interval has elapsed."""
        t = _time_module.time()
        if t - self._last_consolidation >= self._consolidation_interval:
            self.consolidate()


_global_unified_memory: Optional[UnifiedMemorySystem] = None


def get_unified_memory() -> UnifiedMemorySystem:
    global _global_unified_memory
    if _global_unified_memory is None:
        _global_unified_memory = UnifiedMemorySystem()
    return _global_unified_memory