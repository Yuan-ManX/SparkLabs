"""
SparkLabs Agent - Memory Hierarchy

A singleton three-tier memory system for the SparkLabs AI game engine.
Manages short-term working memory, timestamped episodic records,
and long-term semantic knowledge with vector embeddings.

Architecture:
  MemoryHierarchy (singleton)
    |-- Working Memory  (short-term, limited capacity, current task context)
    |-- Episodic Memory (timestamped event records, past interactions)
    |-- Semantic Memory (long-term knowledge, vector embeddings)
    |-- MemoryEntry     (individual stored memory unit)
    |-- MemoryQuery     (retrieval request descriptor)
    |-- MemoryContext   (assembled retrieval result)
"""

from __future__ import annotations

import math
import random
import threading
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


_time_module = time


class MemoryTier(Enum):
    WORKING = "working"
    EPISODIC = "episodic"
    SEMANTIC = "semantic"


class RetrievalStrategy(Enum):
    RECENT = "recent"
    RELEVANT = "relevant"
    HYBRID = "hybrid"
    SEMANTIC = "semantic"


class MemoryPriority(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


# ------------------------------------------------------------------
# Dataclasses
# ------------------------------------------------------------------


@dataclass
class MemoryEntry:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    tier: MemoryTier = MemoryTier.WORKING
    content: str = ""
    embedding: List[float] = field(default_factory=list)
    priority: MemoryPriority = MemoryPriority.MEDIUM
    timestamp: float = field(default_factory=_time_module.time)
    access_count: int = 0
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "tier": self.tier.value,
            "content": self.content,
            "embedding": list(self.embedding),
            "priority": self.priority.value,
            "timestamp": self.timestamp,
            "access_count": self.access_count,
            "tags": list(self.tags),
            "metadata": dict(self.metadata),
        }


@dataclass
class MemoryQuery:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    query_text: str = ""
    strategy: RetrievalStrategy = RetrievalStrategy.HYBRID
    top_k: int = 5
    min_relevance: float = 0.3
    filters: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "query_text": self.query_text,
            "strategy": self.strategy.value,
            "top_k": self.top_k,
            "min_relevance": self.min_relevance,
            "filters": dict(self.filters),
        }


@dataclass
class MemoryContext:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    entries: List[str] = field(default_factory=list)
    total_tokens: int = 0
    summary: str = ""
    created_at: float = field(default_factory=_time_module.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "entries": list(self.entries),
            "total_tokens": self.total_tokens,
            "summary": self.summary,
            "created_at": self.created_at,
        }


# ------------------------------------------------------------------
# Singleton
# ------------------------------------------------------------------

WORKING_CAPACITY: int = 10
EPISODIC_RETENTION: int = 1000
EMBEDDING_DIM: int = 384
MAX_CONTEXT_TOKENS: int = 8192


class MemoryHierarchy:
    """Three-tier memory system for game AI agent persistence.

    Maintains working memory for active task context, episodic memory
    for timestamped event logs, and semantic memory for knowledge
    indexed by vector embeddings. Automatically consolidates important
    working memories into episodic storage and prunes excess entries.
    """

    _instance: Optional[MemoryHierarchy] = None
    _lock: threading.RLock = threading.RLock()

    def __new__(cls) -> MemoryHierarchy:
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    instance = super().__new__(cls)
                    instance._initialized = False
                    cls._instance = instance
        return cls._instance

    @classmethod
    def get_instance(cls) -> MemoryHierarchy:
        if cls._instance is None:
            cls()
        return cls._instance

    def __init__(self) -> None:
        if self._initialized:
            return
        self._initialized = True
        self._working: List[MemoryEntry] = []
        self._episodic: List[MemoryEntry] = []
        self._semantic: List[MemoryEntry] = []

    def _get_or_create_singleton(self) -> MemoryHierarchy:
        return self.get_instance()

    def get_stats(self) -> Dict[str, Any]:
        return {
            "working_count": len(self._working),
            "working_capacity": WORKING_CAPACITY,
            "episodic_count": len(self._episodic),
            "episodic_retention": EPISODIC_RETENTION,
            "semantic_count": len(self._semantic),
            "total_entries": len(self._working)
            + len(self._episodic)
            + len(self._semantic),
        }

    # --- Core Operations ---

    def store(
        self,
        tier: str,
        content: str,
        priority: str = "medium",
        embedding: Optional[List[float]] = None,
        tags: Optional[List[str]] = None,
    ) -> MemoryEntry:
        memory_tier = MemoryTier(tier)
        memory_priority = MemoryPriority(priority)

        entry = MemoryEntry(
            tier=memory_tier,
            content=content,
            embedding=embedding if embedding is not None else [],
            priority=memory_priority,
            tags=tags if tags is not None else [],
        )

        if memory_tier == MemoryTier.WORKING:
            self._working.append(entry)
            self._prune_working_memory()
        elif memory_tier == MemoryTier.EPISODIC:
            self._episodic.append(entry)
            self._prune_episodic_memory()
        elif memory_tier == MemoryTier.SEMANTIC:
            self._semantic.append(entry)

        return entry

    def retrieve(
        self,
        query_text: str,
        strategy: str = "hybrid",
        top_k: int = 5,
        min_relevance: float = 0.3,
        filters: Optional[Dict[str, Any]] = None,
    ) -> MemoryContext:
        retrieval_strategy = RetrievalStrategy(strategy)

        query = MemoryQuery(
            query_text=query_text,
            strategy=retrieval_strategy,
            top_k=top_k,
            min_relevance=min_relevance,
            filters=filters if filters is not None else {},
        )

        candidates: List[MemoryEntry] = []

        if retrieval_strategy == RetrievalStrategy.RECENT:
            candidates = self._episodic + self._semantic
            candidates.sort(key=lambda e: e.timestamp, reverse=True)
            candidates = candidates[:top_k]
        elif retrieval_strategy == RetrievalStrategy.RELEVANT:
            all_entries = self._working + self._episodic + self._semantic
            scored = [
                (entry, self._compute_relevance(entry, query_text))
                for entry in all_entries
            ]
            scored = [(e, s) for e, s in scored if s >= min_relevance]
            scored.sort(key=lambda pair: pair[1], reverse=True)
            candidates = [entry for entry, _ in scored[:top_k]]
        elif retrieval_strategy == RetrievalStrategy.HYBRID:
            all_entries = self._working + self._episodic + self._semantic
            scored = [
                (entry, self._compute_relevance(entry, query_text))
                for entry in all_entries
            ]
            scored.sort(
                key=lambda pair: (
                    pair[1],
                    pair[0].timestamp,
                ),
                reverse=True,
            )
            scored = [(e, s) for e, s in scored if s >= min_relevance]
            candidates = [entry for entry, _ in scored[:top_k]]
            candidates.sort(key=lambda e: e.timestamp, reverse=True)
        elif retrieval_strategy == RetrievalStrategy.SEMANTIC:
            all_semantic = self._semantic + self._episodic
            scored = [
                (entry, self._compute_relevance(entry, query_text))
                for entry in all_semantic
            ]
            scored = [(e, s) for e, s in scored if s >= min_relevance]
            scored.sort(key=lambda pair: pair[1], reverse=True)
            candidates = [entry for entry, _ in scored[:top_k]]

        if filters:
            tier_filter = filters.get("tier")
            if tier_filter:
                target_tier = MemoryTier(tier_filter)
                candidates = [e for e in candidates if e.tier == target_tier]
            priority_filter = filters.get("priority")
            if priority_filter:
                target_priority = MemoryPriority(priority_filter)
                candidates = [e for e in candidates if e.priority == target_priority]
            tag_filter = filters.get("tags")
            if tag_filter and isinstance(tag_filter, list):
                candidates = [
                    e for e in candidates if any(t in e.tags for t in tag_filter)
                ]

        for entry in candidates:
            entry.access_count += 1

        entry_ids = [e.id for e in candidates]
        total_tokens = sum(
            len(e.content.split()) for e in candidates
        )
        summary_text = " ".join(e.content[:120] for e in candidates)

        return MemoryContext(
            entries=entry_ids,
            total_tokens=min(total_tokens, MAX_CONTEXT_TOKENS),
            summary=summary_text[:500],
        )

    def forget(self, tier: str, older_than_seconds: float = 3600.0) -> int:
        memory_tier = MemoryTier(tier)
        cutoff = _time_module.time() - older_than_seconds
        removed = 0

        if memory_tier == MemoryTier.WORKING:
            before = len(self._working)
            self._working = [
                e for e in self._working if e.timestamp > cutoff
            ]
            removed = before - len(self._working)
        elif memory_tier == MemoryTier.EPISODIC:
            before = len(self._episodic)
            self._episodic = [
                e for e in self._episodic if e.timestamp > cutoff
            ]
            removed = before - len(self._episodic)
        elif memory_tier == MemoryTier.SEMANTIC:
            before = len(self._semantic)
            self._semantic = [
                e for e in self._semantic if e.timestamp > cutoff
            ]
            removed = before - len(self._semantic)

        return removed

    def consolidate(self) -> int:
        consolidated = 0
        important = [
            e
            for e in self._working
            if e.priority in (MemoryPriority.HIGH, MemoryPriority.CRITICAL)
        ]
        for entry in important:
            episodic_entry = MemoryEntry(
                tier=MemoryTier.EPISODIC,
                content=entry.content,
                embedding=list(entry.embedding),
                priority=entry.priority,
                tags=list(entry.tags),
                metadata=dict(entry.metadata),
            )
            self._episodic.append(episodic_entry)
            consolidated += 1

        self._working = [
            e
            for e in self._working
            if e.priority not in (MemoryPriority.HIGH, MemoryPriority.CRITICAL)
        ]
        self._prune_episodic_memory()
        return consolidated

    def get_tier_stats(self) -> Dict[str, Any]:
        return {
            "working": {
                "count": len(self._working),
                "capacity": WORKING_CAPACITY,
                "utilization": len(self._working) / WORKING_CAPACITY
                if WORKING_CAPACITY > 0
                else 0.0,
            },
            "episodic": {
                "count": len(self._episodic),
                "retention": EPISODIC_RETENTION,
                "utilization": len(self._episodic) / EPISODIC_RETENTION
                if EPISODIC_RETENTION > 0
                else 0.0,
            },
            "semantic": {
                "count": len(self._semantic),
            },
        }

    # --- Internal ---

    def _compute_relevance(self, entry: MemoryEntry, query_text: str) -> float:
        query_tokens = set(query_text.lower().split())
        content_tokens = set(entry.content.lower().split())

        if not query_tokens:
            return 0.0

        overlap = query_tokens & content_tokens
        jaccard = len(overlap) / len(query_tokens | content_tokens)

        if entry.embedding and len(entry.embedding) > 0:
            tag_boost = min(0.2, len(entry.tags) * 0.02)
            priority_weights = {
                MemoryPriority.LOW: 0.0,
                MemoryPriority.MEDIUM: 0.05,
                MemoryPriority.HIGH: 0.1,
                MemoryPriority.CRITICAL: 0.15,
            }
            priority_boost = priority_weights.get(entry.priority, 0.0)
            return min(1.0, jaccard + tag_boost + priority_boost)

        return jaccard

    def _prune_working_memory(self) -> None:
        while len(self._working) > WORKING_CAPACITY:
            self._working.sort(key=lambda e: (e.priority.value, e.timestamp))
            if self._working:
                self._working.pop(0)

    def _prune_episodic_memory(self) -> None:
        while len(self._episodic) > EPISODIC_RETENTION:
            self._episodic.sort(key=lambda e: (e.priority.value, e.timestamp))
            if self._episodic:
                self._episodic.pop(0)


def get_memory_hierarchy() -> MemoryHierarchy:
    return MemoryHierarchy.get_instance()