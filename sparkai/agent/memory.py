"""
SparkAI Agent - Hierarchical Memory System
"""

from __future__ import annotations

import time
import math
from enum import Enum
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


class MemoryType(Enum):
    SHORT_TERM = "short_term"
    LONG_TERM = "long_term"
    EPISODIC = "episodic"
    SEMANTIC = "semantic"
    WORKING = "working"


@dataclass
class MemoryEntry:
    id: str = ""
    content: str = ""
    memory_type: MemoryType = MemoryType.SHORT_TERM
    importance: float = 0.5
    timestamp: float = field(default_factory=time.time)
    expires_at: Optional[float] = None
    embedding: List[float] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    access_count: int = 0

    def is_expired(self) -> bool:
        if self.expires_at is None:
            return False
        return time.time() > self.expires_at

    def decay_importance(self, current_time: Optional[float] = None) -> float:
        current_time = current_time or time.time()
        elapsed = current_time - self.timestamp
        decay_rates = {
            MemoryType.SHORT_TERM: 10.0,
            MemoryType.EPISODIC: 1.0,
            MemoryType.LONG_TERM: 0.1,
            MemoryType.SEMANTIC: 0.01,
            MemoryType.WORKING: 5.0,
        }
        rate = decay_rates.get(self.memory_type, 1.0)
        return self.importance * math.exp(-rate * elapsed / 3600.0)


class AgentMemory:
    """
    Hierarchical memory system for AI agents.

    Supports five memory types with different retention characteristics:
    - Short-term: Rapid decay, current observations
    - Long-term: Slow decay, persistent knowledge
    - Episodic: Medium decay, event sequences
    - Semantic: Minimal decay, world facts
    - Working: Active processing buffer
    """

    def __init__(
        self,
        short_term_capacity: int = 10,
        long_term_capacity: int = 1000,
        episodic_capacity: int = 500,
        semantic_capacity: int = 2000,
        working_capacity: int = 20,
    ):
        self._memories: Dict[MemoryType, List[MemoryEntry]] = {
            MemoryType.SHORT_TERM: [],
            MemoryType.LONG_TERM: [],
            MemoryType.EPISODIC: [],
            MemoryType.SEMANTIC: [],
            MemoryType.WORKING: [],
        }
        self._capacities = {
            MemoryType.SHORT_TERM: short_term_capacity,
            MemoryType.LONG_TERM: long_term_capacity,
            MemoryType.EPISODIC: episodic_capacity,
            MemoryType.SEMANTIC: semantic_capacity,
            MemoryType.WORKING: working_capacity,
        }
        self._id_counter = 0

    def remember(
        self,
        content: str,
        memory_type: MemoryType = MemoryType.SHORT_TERM,
        importance: float = 0.5,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> MemoryEntry:
        self._id_counter += 1
        entry = MemoryEntry(
            id=f"mem_{self._id_counter}",
            content=content,
            memory_type=memory_type,
            importance=importance,
            metadata=metadata or {},
        )
        self._memories[memory_type].append(entry)
        self._enforce_capacity(memory_type)
        return entry

    def recall(
        self,
        query: str,
        max_results: int = 5,
        memory_types: Optional[List[MemoryType]] = None,
    ) -> List[Dict[str, Any]]:
        types = memory_types or list(MemoryType)
        candidates: List[MemoryEntry] = []
        for mt in types:
            candidates.extend(
                e for e in self._memories.get(mt, []) if not e.is_expired()
            )

        scored = []
        query_lower = query.lower()
        for entry in candidates:
            score = self._compute_relevance(entry, query_lower)
            scored.append((score, entry))

        scored.sort(key=lambda x: x[0], reverse=True)
        results = []
        for score, entry in scored[:max_results]:
            entry.access_count += 1
            results.append({
                "id": entry.id,
                "content": entry.content,
                "type": entry.memory_type.value,
                "importance": entry.importance,
                "relevance": score,
                "timestamp": entry.timestamp,
                "metadata": entry.metadata,
            })
        return results

    def forget(self, entry_id: str) -> bool:
        for mt in MemoryType:
            memories = self._memories.get(mt, [])
            for i, entry in enumerate(memories):
                if entry.id == entry_id:
                    memories.pop(i)
                    return True
        return False

    def consolidate(self) -> int:
        """
        Promote important short-term memories to long-term.
        Returns the number of consolidated entries.
        """
        short_term = self._memories[MemoryType.SHORT_TERM]
        if not short_term:
            return 0

        threshold = 0.7
        consolidated = 0
        to_remove = []

        for i, entry in enumerate(short_term):
            if entry.importance >= threshold or entry.access_count >= 3:
                new_entry = MemoryEntry(
                    id=entry.id,
                    content=entry.content,
                    memory_type=MemoryType.LONG_TERM,
                    importance=min(entry.importance * 1.2, 1.0),
                    timestamp=entry.timestamp,
                    metadata=entry.metadata,
                    access_count=entry.access_count,
                )
                self._memories[MemoryType.LONG_TERM].append(new_entry)
                to_remove.append(i)
                consolidated += 1

        for i in reversed(to_remove):
            short_term.pop(i)

        self._enforce_capacity(MemoryType.LONG_TERM)
        return consolidated

    def clear(self, memory_type: Optional[MemoryType] = None) -> None:
        if memory_type:
            self._memories[memory_type] = []
        else:
            for mt in MemoryType:
                self._memories[mt] = []

    def size(self, memory_type: Optional[MemoryType] = None) -> int:
        if memory_type:
            return len(self._memories.get(memory_type, []))
        return sum(len(v) for v in self._memories.values())

    def get_all(self, memory_type: Optional[MemoryType] = None) -> List[Dict[str, Any]]:
        if memory_type:
            entries = self._memories.get(memory_type, [])
        else:
            entries = []
            for mt in MemoryType:
                entries.extend(self._memories.get(mt, []))

        return [
            {
                "id": e.id,
                "content": e.content,
                "type": e.memory_type.value,
                "importance": e.importance,
                "timestamp": e.timestamp,
                "metadata": e.metadata,
            }
            for e in entries
            if not e.is_expired()
        ]

    def _compute_relevance(self, entry: MemoryEntry, query: str) -> float:
        content_lower = entry.content.lower()
        keyword_score = 0.0
        query_words = query.split()
        for word in query_words:
            if word in content_lower:
                keyword_score += 0.3

        current_importance = entry.decay_importance()
        recency_score = max(0.0, 1.0 - (time.time() - entry.timestamp) / 86400.0)
        access_score = min(entry.access_count * 0.1, 0.3)

        return keyword_score + current_importance * 0.3 + recency_score * 0.2 + access_score

    def _enforce_capacity(self, memory_type: MemoryType) -> None:
        memories = self._memories.get(memory_type, [])
        capacity = self._capacities.get(memory_type, 1000)
        while len(memories) > capacity:
            lowest_idx = 0
            lowest_importance = float("inf")
            for i, entry in enumerate(memories):
                imp = entry.decay_importance()
                if imp < lowest_importance:
                    lowest_importance = imp
                    lowest_idx = i
            memories.pop(lowest_idx)
