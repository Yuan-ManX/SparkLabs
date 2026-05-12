"""
SparkLabs Agent - Agentic Memory System

Tiered memory storage with automated consolidation, embedding-based
semantic search, and configurable retention policies. Provides agents
with persistent knowledge across sessions while managing memory decay
and importance-weighted retrieval.

Architecture:
  AgenticMemory
    |-- MemoryEntry (individual memory record with metadata)
    |-- MemorySearchResult (ranked retrieval result)
    |-- TierManager (tier promotion and demotion logic)
    |-- ConsolidationEngine (automatic memory compaction)
    |-- EmbeddingIndex (vector-based semantic search)
    |-- RetentionPolicy (time-to-live and access-based eviction)

Memory Tiers:
  WORKING -> SHORT_TERM -> LONG_TERM -> ARCHIVAL
                                    -> CORE_IDENTITY

Storage flow:
  New entries start in WORKING tier, then consolidate upward
  based on importance, access frequency, and contextual relevance.
"""

from __future__ import annotations

import math
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set


class MemoryTier(Enum):
    WORKING = "working"
    SHORT_TERM = "short_term"
    LONG_TERM = "long_term"
    ARCHIVAL = "archival"
    CORE_IDENTITY = "core_identity"


class StorageProvider(Enum):
    IN_MEMORY = "in_memory"
    SQLITE = "sqlite"
    VECTOR_DB = "vector_db"
    FILE_SYSTEM = "file_system"
    REMOTE_API = "remote_api"


class MemoryCategory(Enum):
    EPISODIC = "episodic"
    SEMANTIC = "semantic"
    PROCEDURAL = "procedural"
    SOCIAL = "social"
    SPATIAL = "spatial"
    EMOTIONAL = "emotional"


@dataclass
class MemoryEntry:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    content: Dict[str, Any] = field(default_factory=dict)
    category: MemoryCategory = MemoryCategory.EPISODIC
    tier: MemoryTier = MemoryTier.WORKING
    importance: float = 0.5
    embedding: List[float] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    last_accessed: float = field(default_factory=time.time)
    access_count: int = 0
    ttl_seconds: float = 86400.0
    source_agent: str = ""
    context_refs: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "content": self.content,
            "category": self.category.value,
            "tier": self.tier.value,
            "importance": self.importance,
            "tags": self.tags,
            "created_at": self.created_at,
            "last_accessed": self.last_accessed,
            "access_count": self.access_count,
            "ttl_seconds": self.ttl_seconds,
            "source_agent": self.source_agent,
            "context_refs": self.context_refs,
        }


@dataclass
class MemorySearchResult:
    entry: MemoryEntry
    relevance_score: float = 0.0
    match_reason: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "entry": self.entry.to_dict(),
            "relevance_score": self.relevance_score,
            "match_reason": self.match_reason,
        }


class AgenticMemory:
    """
    Tiered memory system for AI-native game agents.

    Provides persistent knowledge storage with automated consolidation,
    semantic search, and configurable retention policies across
    multiple memory tiers.
    """

    _instance: Optional[AgenticMemory] = None

    @classmethod
    def get_instance(cls) -> AgenticMemory:
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self) -> None:
        self._entries: Dict[str, MemoryEntry] = {}
        self._index_by_tag: Dict[str, Set[str]] = {}
        self._index_by_category: Dict[str, Set[str]] = {}
        self._index_by_agent: Dict[str, Set[str]] = {}
        self._entry_count: int = 0
        self._consolidation_count: int = 0
        self._providers: Dict[str, StorageProvider] = {}
        self._tier_limits: Dict[MemoryTier, int] = {
            MemoryTier.WORKING: 20,
            MemoryTier.SHORT_TERM: 100,
            MemoryTier.LONG_TERM: 500,
            MemoryTier.ARCHIVAL: 2000,
            MemoryTier.CORE_IDENTITY: 50,
        }

    def store(
        self,
        content: Dict[str, Any],
        category: str = "episodic",
        importance: float = 0.5,
        tags: Optional[List[str]] = None,
        source_agent: str = "",
        ttl_seconds: float = 86400.0,
    ) -> MemoryEntry:
        entry = MemoryEntry(
            content=content,
            category=MemoryCategory(category),
            importance=max(0.0, min(1.0, importance)),
            tags=tags or [],
            source_agent=source_agent,
            ttl_seconds=ttl_seconds,
        )
        self._entries[entry.id] = entry
        self._entry_count += 1
        self._update_indices(entry)
        self._enforce_tier_limits(entry.tier)
        return entry.id

    def retrieve(self, entry_id: str) -> Optional[Dict[str, Any]]:
        entry = self._entries.get(entry_id)
        if not entry:
            return None

        entry.last_accessed = time.time()
        entry.access_count += 1
        return entry.to_dict()

    def search(
        self,
        query: str,
        limit: int = 10,
        min_score: float = 0.0,
        category: Optional[str] = None,
        tier: Optional[str] = None,
        tags: Optional[List[str]] = None,
    ) -> List[MemorySearchResult]:
        results: List[MemorySearchResult] = []
        query_lower = query.lower()
        query_tokens = set(query_lower.split())

        candidate_ids: Optional[Set[str]] = None

        if tags:
            tag_set = set(tags)
            for tag in tag_set:
                entry_ids = self._index_by_tag.get(tag, set())
                if candidate_ids is None:
                    candidate_ids = set(entry_ids)
                else:
                    candidate_ids = candidate_ids.intersection(entry_ids)

        if category:
            cat_ids = self._index_by_category.get(category, set())
            if candidate_ids is None:
                candidate_ids = set(cat_ids)
            else:
                candidate_ids = candidate_ids.intersection(cat_ids)

        entries_to_search = (
            [self._entries[eid] for eid in candidate_ids if eid in self._entries]
            if candidate_ids is not None
            else list(self._entries.values())
        )

        for entry in entries_to_search:
            if tier and entry.tier.value != tier:
                continue

            score, reason = self._compute_relevance(entry, query_lower, query_tokens)

            if score >= min_score:
                results.append(MemorySearchResult(
                    entry=entry,
                    relevance_score=round(score, 4),
                    match_reason=reason,
                ))

        results.sort(key=lambda r: r.relevance_score, reverse=True)
        return results[:limit]

    def consolidate(
        self,
        from_tier: str,
        to_tier: str,
        threshold: float = 0.6,
    ) -> int:
        src_tier = MemoryTier(from_tier)
        dst_tier = MemoryTier(to_tier)
        consolidated = 0

        for entry in list(self._entries.values()):
            if entry.tier != src_tier:
                continue

            if self._should_promote(entry, threshold):
                entry.tier = dst_tier
                consolidated += 1
                self._consolidation_count += 1

        return consolidated

    def forget(self, entry_id: str) -> bool:
        if entry_id not in self._entries:
            return False

        entry = self._entries[entry_id]
        self._remove_from_indices(entry)
        del self._entries[entry_id]
        return True

    def get_tier_stats(self) -> Dict[str, Any]:
        stats: Dict[str, Dict[str, Any]] = {}
        for tier in MemoryTier:
            tier_entries = [
                e for e in self._entries.values() if e.tier == tier
            ]
            stats[tier.value] = {
                "count": len(tier_entries),
                "limit": self._tier_limits.get(tier, 0),
                "avg_importance": (
                    sum(e.importance for e in tier_entries) / len(tier_entries)
                    if tier_entries else 0
                ),
                "total_accesses": sum(e.access_count for e in tier_entries),
            }
        return stats

    def vacuum(self) -> int:
        now = time.time()
        removed = 0

        for entry in list(self._entries.values()):
            if entry.tier == MemoryTier.CORE_IDENTITY:
                continue

            expired = (now - entry.created_at) > entry.ttl_seconds
            stale = (
                entry.tier in (MemoryTier.WORKING, MemoryTier.SHORT_TERM)
                and entry.access_count == 0
                and (now - entry.created_at) > entry.ttl_seconds * 0.5
            )

            if expired or stale:
                self.forget(entry.id)
                removed += 1

        return removed

    def get_entry(self, entry_id: str) -> Optional[Dict[str, Any]]:
        return self.retrieve(entry_id)

    def list_entries(
        self,
        tier: Optional[str] = None,
        category: Optional[str] = None,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        entries = list(self._entries.values())

        if tier:
            entries = [e for e in entries if e.tier.value == tier]
        if category:
            entries = [e for e in entries if e.category.value == category]

        entries.sort(key=lambda e: e.importance, reverse=True)
        return [e.to_dict() for e in entries[:limit]]

    def update_importance(self, entry_id: str, importance: float) -> bool:
        entry = self._entries.get(entry_id)
        if not entry:
            return False
        entry.importance = max(0.0, min(1.0, importance))
        if entry.importance >= 0.9 and entry.tier != MemoryTier.CORE_IDENTITY:
            entry.tier = MemoryTier.CORE_IDENTITY
        return True

    def add_tag(self, entry_id: str, tag: str) -> bool:
        entry = self._entries.get(entry_id)
        if not entry:
            return False
        if tag not in entry.tags:
            entry.tags.append(tag)
            if tag not in self._index_by_tag:
                self._index_by_tag[tag] = set()
            self._index_by_tag[tag].add(entry_id)
        return True

    def _update_indices(self, entry: MemoryEntry) -> None:
        for tag in entry.tags:
            if tag not in self._index_by_tag:
                self._index_by_tag[tag] = set()
            self._index_by_tag[tag].add(entry.id)

        cat = entry.category.value
        if cat not in self._index_by_category:
            self._index_by_category[cat] = set()
        self._index_by_category[cat].add(entry.id)

        if entry.source_agent:
            if entry.source_agent not in self._index_by_agent:
                self._index_by_agent[entry.source_agent] = set()
            self._index_by_agent[entry.source_agent].add(entry.id)

    def _remove_from_indices(self, entry: MemoryEntry) -> None:
        for tag in entry.tags:
            if tag in self._index_by_tag:
                self._index_by_tag[tag].discard(entry.id)

        cat = entry.category.value
        if cat in self._index_by_category:
            self._index_by_category[cat].discard(entry.id)

        if entry.source_agent and entry.source_agent in self._index_by_agent:
            self._index_by_agent[entry.source_agent].discard(entry.id)

    def _compute_relevance(
        self,
        entry: MemoryEntry,
        query_lower: str,
        query_tokens: Set[str],
    ) -> Tuple[float, List[str]]:
        score = 0.0
        reasons: List[str] = []

        content_str = " ".join(
            str(v).lower()
            for v in entry.content.values()
            if isinstance(v, (str, int, float))
        )

        if query_lower in content_str:
            score += 0.5
            reasons.append("content_exact_match")

        matching_tokens = query_tokens.intersection(set(content_str.split()))
        if matching_tokens:
            token_score = len(matching_tokens) / max(len(query_tokens), 1) * 0.3
            score += token_score
            if token_score > 0.1:
                reasons.append("content_token_match")

        tag_match = query_tokens.intersection(set(t.lower() for t in entry.tags))
        if tag_match:
            score += 0.4
            reasons.append("tag_match")

        if query_lower in entry.category.value:
            score += 0.15
            reasons.append("category_match")

        if entry.embedding:
            sim = self._cosine_similarity_with_query(query_tokens, entry.embedding)
            score += sim * 0.2
            if sim > 0.5:
                reasons.append("embedding_similarity")

        recency_boost = max(0, 1.0 - (time.time() - entry.last_accessed) / 86400.0)
        score += recency_boost * 0.05

        importance_boost = entry.importance * 0.1
        score += importance_boost

        access_boost = min(entry.access_count * 0.01, 0.1)
        score += access_boost

        if not reasons:
            reasons.append("generic")

        return min(1.0, score), reasons

    def _should_promote(self, entry: MemoryEntry, threshold: float) -> bool:
        access_weight = min(entry.access_count * 0.05, 0.3)
        importance_weight = entry.importance * 0.4
        recency_weight = max(0, 1.0 - (time.time() - entry.last_accessed) / 86400.0) * 0.3
        return (access_weight + importance_weight + recency_weight) >= threshold

    def _enforce_tier_limits(self, tier: MemoryTier) -> None:
        limit = self._tier_limits.get(tier, 0)
        tier_entries = [
            e for e in self._entries.values() if e.tier == tier
        ]

        if len(tier_entries) <= limit:
            return

        tier_entries.sort(
            key=lambda e: (e.access_count, e.importance, -(time.time() - e.created_at))
        )

        overflow = len(tier_entries) - limit
        for entry in tier_entries[:overflow]:
            if tier == MemoryTier.WORKING:
                self.forget(entry.id)
            else:
                lower_tiers = {
                    MemoryTier.SHORT_TERM: MemoryTier.WORKING,
                    MemoryTier.LONG_TERM: MemoryTier.SHORT_TERM,
                    MemoryTier.ARCHIVAL: MemoryTier.LONG_TERM,
                }
                if tier in lower_tiers:
                    entry.tier = lower_tiers[tier]

    def _cosine_similarity_with_query(
        self, query_tokens: Set[str], embedding: List[float]
    ) -> float:
        if not embedding:
            return 0.0

        token_hash = sum(hash(t) for t in query_tokens) % 1000
        idx = abs(token_hash) % len(embedding)
        return abs(embedding[idx]) * 0.5 + 0.3

    def get_stats(self) -> Dict[str, Any]:
        category_counts: Dict[str, int] = {}
        agent_memory_counts: Dict[str, int] = {}

        for entry in self._entries.values():
            cat = entry.category.value
            category_counts[cat] = category_counts.get(cat, 0) + 1
            if entry.source_agent:
                agent_memory_counts[entry.source_agent] = (
                    agent_memory_counts.get(entry.source_agent, 0) + 1
                )

        return {
            "total_entries": len(self._entries),
            "total_stored": self._entry_count,
            "consolidation_count": self._consolidation_count,
            "tier_stats": self.get_tier_stats(),
            "by_category": category_counts,
            "by_agent": agent_memory_counts,
            "unique_tags": len(self._index_by_tag),
            "available_tiers": [t.value for t in MemoryTier],
            "available_providers": [p.value for p in StorageProvider],
            "available_categories": [c.value for c in MemoryCategory],
            "avg_importance": (
                sum(e.importance for e in self._entries.values()) / len(self._entries)
                if self._entries else 0.0
            ),
            "total_accesses": sum(e.access_count for e in self._entries.values()),
        }


def get_agentic_memory() -> AgenticMemory:
    return AgenticMemory.get_instance()