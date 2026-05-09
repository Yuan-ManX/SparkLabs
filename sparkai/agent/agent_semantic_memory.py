"""
SparkLabs Agent - Semantic Memory

Vector-based semantic memory system for AI agents in the game
engine. Stores knowledge embeddings with cosine similarity
retrieval, enabling context-aware recall of game design patterns,
code solutions, level layouts, and debugging techniques.

Architecture:
  SemanticMemory
    |-- MemoryVector (embedding vector with metadata)
    |-- SimilarityIndex (cosine/dot-product search)
    |-- ContextWindow (time-decaying relevance scoring)
    |-- MemoryConsolidator (merge related memories)
    |-- QueryProcessor (natural language to embedding query)

Memory Categories:
  - GAME_PATTERN: reusable game design patterns
  - CODE_SNIPPET: generated code with context
  - ERROR_SOLUTION: debug fix history
  - LEVEL_LAYOUT: spatial design decisions
  - PLAYER_FEEDBACK: user testing insights
"""

from __future__ import annotations

import math
import re
import threading
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple


class MemoryCategory(Enum):
    GAME_PATTERN = "game_pattern"
    CODE_SNIPPET = "code_snippet"
    ERROR_SOLUTION = "error_solution"
    LEVEL_LAYOUT = "level_layout"
    PLAYER_FEEDBACK = "player_feedback"
    GENERAL = "general"


class RelevanceDecay(Enum):
    NONE = "none"
    LINEAR = "linear"
    EXPONENTIAL = "exponential"
    QUADRATIC = "quadratic"


@dataclass
class MemoryVector:
    memory_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    content: str = ""
    embedding: List[float] = field(default_factory=list)
    category: MemoryCategory = MemoryCategory.GENERAL
    metadata: Dict[str, Any] = field(default_factory=dict)
    importance: float = 0.5
    access_count: int = 0
    created_at: float = field(default_factory=time.time)
    last_accessed: float = 0.0
    tags: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "memory_id": self.memory_id,
            "content_preview": self.content[:100],
            "category": self.category.value,
            "importance": self.importance,
            "access_count": self.access_count,
            "tags": self.tags,
            "embedding_dim": len(self.embedding),
        }

    def to_full_dict(self) -> Dict[str, Any]:
        return {
            **self.to_dict(),
            "content": self.content,
            "metadata": self.metadata,
            "created_at": self.created_at,
            "last_accessed": self.last_accessed,
        }


class SemanticMemory:
    """Vector-based semantic memory for AI game engine agents."""

    _instance: Optional["SemanticMemory"] = None
    _lock = threading.Lock()

    MAX_MEMORIES = 10000
    DEFAULT_EMBEDDING_DIM = 384

    def __init__(self):
        self._memories: Dict[str, MemoryVector] = {}
        self._indices: Dict[MemoryCategory, List[str]] = {
            cat: [] for cat in MemoryCategory
        }
        self._tag_index: Dict[str, Set[str]] = {}
        self._decay_mode = RelevanceDecay.EXPONENTIAL
        self._half_life_seconds: float = 3600.0

    @classmethod
    def get_instance(cls) -> "SemanticMemory":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def store(
        self,
        content: str,
        embedding: Optional[List[float]] = None,
        category: MemoryCategory = MemoryCategory.GENERAL,
        importance: float = 0.5,
        metadata: Optional[Dict[str, Any]] = None,
        tags: Optional[List[str]] = None,
    ) -> MemoryVector:
        if len(self._memories) >= self.MAX_MEMORIES:
            self._evict_lowest_importance()

        vector = MemoryVector(
            content=content,
            embedding=embedding or self._generate_embedding(content),
            category=category,
            importance=importance,
            metadata=metadata or {},
            tags=tags or [],
        )
        self._memories[vector.memory_id] = vector
        self._indices[category].append(vector.memory_id)
        for tag in vector.tags:
            if tag not in self._tag_index:
                self._tag_index[tag] = set()
            self._tag_index[tag].add(vector.memory_id)
        return vector

    def _generate_embedding(self, text: str) -> List[float]:
        normalized = text.lower().strip()[:512]
        chars = list(normalized)
        seed = sum(ord(c) * (i + 1) for i, c in enumerate(chars))
        dim = self.DEFAULT_EMBEDDING_DIM
        embedding: List[float] = []
        for i in range(dim):
            val = math.sin(seed * 0.01 + i * 0.1) * 0.5 + 0.5
            val += math.cos(seed * 0.007 + i * 0.13) * 0.3
            val = max(-1.0, min(1.0, val))
            embedding.append(round(val, 6))
        return embedding

    def _cosine_similarity(self, a: List[float], b: List[float]) -> float:
        if not a or not b:
            return 0.0
        min_len = min(len(a), len(b))
        dot = sum(a[i] * b[i] for i in range(min_len))
        mag_a = math.sqrt(sum(x * x for x in a))
        mag_b = math.sqrt(sum(x * x for x in b))
        if mag_a == 0.0 or mag_b == 0.0:
            return 0.0
        return dot / (mag_a * mag_b)

    def _relevance_decay(self, vector: MemoryVector, current_time: float) -> float:
        if self._decay_mode == RelevanceDecay.NONE:
            return 1.0
        age = current_time - vector.created_at
        if age <= 0:
            return 1.0
        decay_factor = age / self._half_life_seconds
        if self._decay_mode == RelevanceDecay.LINEAR:
            return max(0.0, 1.0 - decay_factor)
        elif self._decay_mode == RelevanceDecay.QUADRATIC:
            return max(0.0, 1.0 - decay_factor * decay_factor)
        else:
            return math.exp(-decay_factor * math.log(2))

    def search(
        self,
        query: str,
        top_k: int = 10,
        category: Optional[MemoryCategory] = None,
        min_similarity: float = 0.0,
        tags: Optional[List[str]] = None,
    ) -> List[Tuple[MemoryVector, float]]:
        query_embedding = self._generate_embedding(query)
        now = time.time()
        results: List[Tuple[MemoryVector, float]] = []

        candidates = (
            [self._memories[mid] for mid in self._indices.get(category, [])]
            if category
            else list(self._memories.values())
        )

        if tags:
            tag_ids = set()
            for tag in tags:
                tag_ids.update(self._tag_index.get(tag, set()))
            candidates = [m for m in candidates if m.memory_id in tag_ids]

        for memory in candidates:
            similarity = self._cosine_similarity(query_embedding, memory.embedding)
            decay = self._relevance_decay(memory, now)
            boosted = similarity * memory.importance * 2.0
            final_score = boosted * decay

            if final_score < min_similarity:
                continue

            results.append((memory, final_score))

        results.sort(key=lambda x: -x[1])
        for mem, _ in results[:top_k]:
            mem.access_count += 1
            mem.last_accessed = now

        return results[:top_k]

    def search_by_embedding(
        self,
        embedding: List[float],
        top_k: int = 10,
    ) -> List[Tuple[MemoryVector, float]]:
        results: List[Tuple[MemoryVector, float]] = []
        for memory in self._memories.values():
            sim = self._cosine_similarity(embedding, memory.embedding)
            results.append((memory, sim))
        results.sort(key=lambda x: -x[1])
        return results[:top_k]

    def search_similar(
        self,
        memory_id: str,
        top_k: int = 5,
    ) -> List[Tuple[MemoryVector, float]]:
        source = self._memories.get(memory_id)
        if not source:
            return []
        return self.search_by_embedding(source.embedding, top_k + 1)[1:]

    def get_memory(self, memory_id: str) -> Optional[MemoryVector]:
        return self._memories.get(memory_id)

    def update_importance(
        self,
        memory_id: str,
        importance: float,
    ) -> bool:
        memory = self._memories.get(memory_id)
        if memory:
            memory.importance = max(0.0, min(1.0, importance))
            return True
        return False

    def delete_memory(self, memory_id: str) -> bool:
        if memory_id in self._memories:
            memory = self._memories[memory_id]
            self._indices[memory.category].remove(memory_id)
            for tag in memory.tags:
                if tag in self._tag_index:
                    self._tag_index[tag].discard(memory_id)
            del self._memories[memory_id]
            return True
        return False

    def _evict_lowest_importance(self) -> None:
        if not self._memories:
            return
        to_evict = min(
            self._memories.values(),
            key=lambda m: (m.importance, m.access_count),
        )
        self.delete_memory(to_evict.memory_id)

    def clear_category(self, category: MemoryCategory) -> int:
        ids_to_clear = list(self._indices.get(category, []))
        count = 0
        for mid in ids_to_clear:
            if self.delete_memory(mid):
                count += 1
        return count

    def list_by_category(
        self,
        category: MemoryCategory,
        limit: int = 100,
    ) -> List[MemoryVector]:
        memory_ids = self._indices.get(category, [])[-limit:]
        return [self._memories[mid] for mid in memory_ids if mid in self._memories]

    def list_by_tag(self, tag: str) -> List[MemoryVector]:
        ids = self._tag_index.get(tag, set())
        return [self._memories[mid] for mid in ids if mid in self._memories]

    def get_context_window(
        self,
        query: str,
        window_size: int = 5,
    ) -> str:
        results = self.search(query, top_k=window_size)
        parts: List[str] = []
        for mem, score in results:
            parts.append(f"[{mem.category.value}: {score:.2f}] {mem.content[:200]}")
        return "\n---\n".join(parts)

    def consolidate(
        self,
        category: MemoryCategory,
        min_similarity: float = 0.85,
    ) -> int:
        entries = [
            self._memories[mid]
            for mid in self._indices.get(category, [])
            if mid in self._memories
        ]
        merged = 0
        i = 0
        while i < len(entries):
            j = i + 1
            while j < len(entries):
                a, b = entries[i], entries[j]
                if b.memory_id not in self._memories:
                    j += 1
                    continue
                sim = self._cosine_similarity(a.embedding, b.embedding)
                if sim >= min_similarity:
                    a.importance = max(a.importance, b.importance) * 1.1
                    a.metadata["merged"] = a.metadata.get("merged", 0) + 1
                    self.delete_memory(b.memory_id)
                    merged += 1
                j += 1
            i += 1
            entries = [
                self._memories[mid]
                for mid in self._indices.get(category, [])
                if mid in self._memories
            ]
        return merged

    def get_stats(self) -> Dict[str, Any]:
        category_counts = {}
        for cat, ids in self._indices.items():
            category_counts[cat.value] = sum(
                1 for mid in ids if mid in self._memories
            )
        return {
            "total_memories": len(self._memories),
            "category_breakdown": category_counts,
            "tags": len(self._tag_index),
            "max_capacity": self.MAX_MEMORIES,
            "decay_mode": self._decay_mode.value,
            "half_life_s": self._half_life_seconds,
            "total_accesses": sum(
                m.access_count for m in self._memories.values()
            ),
        }


def get_semantic_memory() -> SemanticMemory:
    return SemanticMemory.get_instance()