"""
SparkAI Agent - Hierarchical Memory System

Supports three-factor retrieval (recency x relevance x importance)
with a reflection DAG that enables recursive reflection-on-reflection.
Memories are nodes in a provenance graph where reflection nodes point
back to the observations that inspired them.
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


class NodeType(Enum):
    """Memory node type for the reflection DAG."""
    OBSERVATION = "observation"
    REFLECTION = "reflection"


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
    # Reflection DAG fields
    node_type: NodeType = NodeType.OBSERVATION
    pointer_ids: List[str] = field(default_factory=list)
    last_retrieved: float = field(default_factory=time.time)
    # Emotional valence for game agent context (-1.0 to 1.0)
    emotional_valence: float = 0.0
    emotional_intensity: float = 0.0

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

    def recency_score(self, current_time: Optional[float] = None) -> float:
        """Exponential recency decay based on last retrieval time."""
        current_time = current_time or time.time()
        elapsed = current_time - self.last_retrieved
        return 0.99 ** (elapsed / 60.0)  # Decay per minute

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "content": self.content,
            "type": self.memory_type.value,
            "node_type": self.node_type.value,
            "importance": self.importance,
            "timestamp": self.timestamp,
            "last_retrieved": self.last_retrieved,
            "access_count": self.access_count,
            "pointer_ids": self.pointer_ids,
            "emotional_valence": self.emotional_valence,
            "emotional_intensity": self.emotional_intensity,
            "metadata": self.metadata,
        }


class AgentMemory:
    """
    Hierarchical memory system for AI agents.

    Supports five memory types with different retention characteristics:
    - Short-term: Rapid decay, current observations
    - Long-term: Slow decay, persistent knowledge
    - Episodic: Medium decay, event sequences
    - Semantic: Minimal decay, world facts
    - Working: Active processing buffer

    Three-factor retrieval scores each memory by:
    - Recency: exponential decay from last retrieval time
    - Relevance: keyword/bigram/semantic similarity to query
    - Importance: LLM-assigned or heuristic score (0.0-1.0)

    The reflection DAG allows reflections to be stored as memory nodes
    with provenance pointers to their source observations, enabling
    recursive reflection-on-reflection for deep agent reasoning.
    """

    def __init__(
        self,
        short_term_capacity: int = 10,
        long_term_capacity: int = 1000,
        episodic_capacity: int = 500,
        semantic_capacity: int = 2000,
        working_capacity: int = 20,
        # Three-factor retrieval weights (recency, relevance, importance)
        recency_weight: float = 0.3,
        relevance_weight: float = 0.4,
        importance_weight: float = 0.3,
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
        # Retrieval weights
        self._recency_w = recency_weight
        self._relevance_w = relevance_weight
        self._importance_w = importance_weight
        # Index for fast lookup by ID (reflection DAG traversal)
        self._id_index: Dict[str, MemoryEntry] = {}
        # Reflection cadence tracking
        self._tick_count: int = 0
        self._last_micro_reflection: float = 0.0
        self._last_full_reflection: float = 0.0

    def remember(
        self,
        content: str,
        memory_type: MemoryType = MemoryType.SHORT_TERM,
        importance: float = 0.5,
        metadata: Optional[Dict[str, Any]] = None,
        node_type: NodeType = NodeType.OBSERVATION,
        pointer_ids: Optional[List[str]] = None,
        emotional_valence: float = 0.0,
        emotional_intensity: float = 0.0,
    ) -> MemoryEntry:
        self._id_counter += 1
        entry = MemoryEntry(
            id=f"mem_{self._id_counter}",
            content=content,
            memory_type=memory_type,
            importance=importance,
            metadata=metadata or {},
            node_type=node_type,
            pointer_ids=pointer_ids or [],
            emotional_valence=emotional_valence,
            emotional_intensity=emotional_intensity,
        )
        self._memories[memory_type].append(entry)
        self._id_index[entry.id] = entry
        self._enforce_capacity(memory_type)
        return entry

    def recall(
        self,
        query: str,
        max_results: int = 5,
        memory_types: Optional[List[MemoryType]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Three-factor retrieval: recency x relevance x importance.

        Each factor is normalized to [0, 1] before weighted combination.
        Updates last_retrieved timestamp on accessed memories.
        """
        types = memory_types or list(MemoryType)
        candidates: List[MemoryEntry] = []
        for mt in types:
            candidates.extend(
                e for e in self._memories.get(mt, []) if not e.is_expired()
            )

        if not candidates:
            return []

        current_time = time.time()
        query_lower = query.lower()

        # Compute raw scores for all candidates
        raw_scores = []
        for entry in candidates:
            recency = entry.recency_score(current_time)
            relevance = self._compute_relevance(entry, query_lower)
            importance = max(0.0, min(1.0, entry.decay_importance(current_time)))
            raw_scores.append((recency, relevance, importance, entry))

        # Normalize each factor to [0, 1]
        max_recency = max(r[0] for r in raw_scores) or 1.0
        max_relevance = max(r[1] for r in raw_scores) or 1.0
        max_importance = max(r[2] for r in raw_scores) or 1.0

        scored = []
        for recency, relevance, importance, entry in raw_scores:
            n_recency = recency / max_recency if max_recency > 0 else 0.0
            n_relevance = relevance / max_relevance if max_relevance > 0 else 0.0
            n_importance = importance / max_importance if max_importance > 0 else 0.0

            master_score = (
                self._recency_w * n_recency
                + self._relevance_w * n_relevance
                + self._importance_w * n_importance
            )
            scored.append((master_score, entry))

        scored.sort(key=lambda x: x[0], reverse=True)

        results = []
        for score, entry in scored[:max_results]:
            entry.access_count += 1
            entry.last_retrieved = current_time
            results.append({
                "id": entry.id,
                "content": entry.content,
                "type": entry.memory_type.value,
                "node_type": entry.node_type.value,
                "importance": entry.importance,
                "score": round(score, 4),
                "timestamp": entry.timestamp,
                "pointer_ids": entry.pointer_ids,
                "metadata": entry.metadata,
            })
        return results

    def add_reflection(
        self,
        content: str,
        source_ids: List[str],
        importance: float = 0.8,
        memory_type: MemoryType = MemoryType.LONG_TERM,
        emotional_valence: float = 0.0,
        emotional_intensity: float = 0.0,
    ) -> MemoryEntry:
        """
        Add a reflection node to the memory DAG.

        Reflections are higher-abstraction memories that point back to
        the observation nodes that inspired them. This enables recursive
        reflection-on-reflection for deep agent reasoning.
        """
        entry = self.remember(
            content=content,
            memory_type=memory_type,
            importance=importance,
            node_type=NodeType.REFLECTION,
            pointer_ids=source_ids,
            emotional_valence=emotional_valence,
            emotional_intensity=emotional_intensity,
        )
        return entry

    def get_reflection_chain(self, reflection_id: str) -> List[Dict[str, Any]]:
        """Trace the provenance chain of a reflection back to source observations."""
        chain = []
        visited = set()
        stack = [reflection_id]
        while stack:
            node_id = stack.pop()
            if node_id in visited:
                continue
            visited.add(node_id)
            entry = self._id_index.get(node_id)
            if entry:
                chain.append(entry.to_dict())
                stack.extend(entry.pointer_ids)
        return chain

    def tick(self) -> None:
        """Advance the memory system's internal tick counter for cadence tracking."""
        self._tick_count += 1

    def should_micro_reflect(self, interval_ticks: int = 60) -> bool:
        """Check if a micro-reflection is due (lightweight, frequent)."""
        return self._tick_count - self._last_micro_reflection >= interval_ticks

    def should_full_reflect(self, interval_ticks: int = 3600) -> bool:
        """Check if a full reflection is due (heavyweight, infrequent)."""
        return self._tick_count - self._last_full_reflection >= interval_ticks

    def mark_micro_reflected(self) -> None:
        self._last_micro_reflection = self._tick_count

    def mark_full_reflected(self) -> None:
        self._last_full_reflection = self._tick_count

    def get_emotional_summary(self) -> Dict[str, float]:
        """Aggregate emotional state across recent memories."""
        recent = self._memories[MemoryType.SHORT_TERM][-20:]
        if not recent:
            return {"valence": 0.0, "intensity": 0.0}
        avg_valence = sum(e.emotional_valence for e in recent) / len(recent)
        avg_intensity = sum(e.emotional_intensity for e in recent) / len(recent)
        return {"valence": round(avg_valence, 3), "intensity": round(avg_intensity, 3)}

    def forget(self, entry_id: str) -> bool:
        for mt in MemoryType:
            memories = self._memories.get(mt, [])
            for i, entry in enumerate(memories):
                if entry.id == entry_id:
                    memories.pop(i)
                    self._id_index.pop(entry_id, None)
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
        query_lower = query.lower()

        keyword_score = 0.0
        query_words = [w for w in query_lower.split() if len(w) > 2]
        for word in query_words:
            if word in content_lower:
                keyword_score += 0.3

        bigram_score = 0.0
        if len(query_words) >= 2:
            query_bigrams = [f"{query_words[i]} {query_words[i+1]}" for i in range(len(query_words) - 1)]
            for bigram in query_bigrams:
                if bigram in content_lower:
                    bigram_score += 0.4

        tag_score = 0.0
        if entry.metadata and "tags" in entry.metadata:
            entry_tags = [str(t).lower() for t in entry.metadata["tags"]]
            for word in query_words:
                if word in entry_tags:
                    tag_score += 0.3

        type_weight = {
            MemoryType.WORKING: 1.2,
            MemoryType.SHORT_TERM: 1.0,
            MemoryType.EPISODIC: 0.8,
            MemoryType.LONG_TERM: 0.9,
            MemoryType.SEMANTIC: 1.1,
        }.get(entry.memory_type, 1.0)

        current_importance = entry.decay_importance()
        recency_score = max(0.0, 1.0 - (time.time() - entry.timestamp) / 86400.0)
        access_score = min(entry.access_count * 0.1, 0.3)

        return (keyword_score + bigram_score + tag_score + current_importance * 0.3 + recency_score * 0.2 + access_score) * type_weight

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
            evicted = memories.pop(lowest_idx)
            self._id_index.pop(evicted.id, None)
