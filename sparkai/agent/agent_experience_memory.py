"""
SparkLabs Agent - Experience Memory Engine

Hermes-style experience memory system with trajectory compression for
AI-native game agents. Stores agent experiences, compresses them for
efficient retrieval, and provides context-aware memory recall. Supports
importance-based retention, memory consolidation, episodic/semantic
separation, time-decay weighting, and memory chain linking.

Architecture:
  ExperienceMemoryEngine
    |-- ExperienceStore (entry storage with metadata tagging)
    |-- TrajectoryCompressor (merge similar experiences within time windows)
    |-- ImportanceManager (retain important memories, forget trivial ones)
    |-- ContextRetriever (context-aware memory retrieval)
    |-- ConsolidationEngine (periodic episodic-to-semantic summarization)
    |-- MemoryLinker (chain related memories together)
    |-- TimeDecayCalculator (recency-weighted scoring)

Memory Flow:
  New experience -> tag & index -> evaluate importance ->
  store in appropriate type -> periodically compress trajectories ->
  consolidate episodic into semantic -> decay old/trivial memories
"""

from __future__ import annotations

import hashlib
import math
import threading
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple


class MemoryType(Enum):
    EPISODIC = "episodic"
    SEMANTIC = "semantic"
    PROCEDURAL = "procedural"
    EMOTIONAL = "emotional"


class ExperienceImportance(Enum):
    TRIVIAL = "trivial"
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"
    CRITICAL = "critical"


_IMPORTANCE_WEIGHTS: Dict[ExperienceImportance, float] = {
    ExperienceImportance.TRIVIAL: 0.1,
    ExperienceImportance.LOW: 0.3,
    ExperienceImportance.MODERATE: 0.5,
    ExperienceImportance.HIGH: 0.75,
    ExperienceImportance.CRITICAL: 1.0,
}

_IMPORTANCE_ORDER: Dict[ExperienceImportance, int] = {
    ExperienceImportance.TRIVIAL: 0,
    ExperienceImportance.LOW: 1,
    ExperienceImportance.MODERATE: 2,
    ExperienceImportance.HIGH: 3,
    ExperienceImportance.CRITICAL: 4,
}


@dataclass
class ExperienceEntry:
    entry_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    agent_id: str = ""
    memory_type: MemoryType = MemoryType.EPISODIC
    content: str = ""
    summary: str = ""
    importance: ExperienceImportance = ExperienceImportance.MODERATE
    timestamp: float = field(default_factory=time.time)
    context: Dict[str, Any] = field(default_factory=dict)
    tags: List[str] = field(default_factory=list)
    linked_entries: List[str] = field(default_factory=list)
    access_count: int = 0
    last_accessed: float = field(default_factory=time.time)
    decay_factor: float = 1.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "entry_id": self.entry_id,
            "agent_id": self.agent_id,
            "memory_type": self.memory_type.value,
            "content": self.content[:300],
            "summary": self.summary[:200],
            "importance": self.importance.value,
            "timestamp": self.timestamp,
            "context_keys": list(self.context.keys()) if self.context else [],
            "tags": self.tags,
            "linked_entries_count": len(self.linked_entries),
            "access_count": self.access_count,
            "last_accessed": self.last_accessed,
            "decay_factor": round(self.decay_factor, 4),
        }

    def to_full_dict(self) -> Dict[str, Any]:
        return {
            "entry_id": self.entry_id,
            "agent_id": self.agent_id,
            "memory_type": self.memory_type.value,
            "content": self.content,
            "summary": self.summary,
            "importance": self.importance.value,
            "timestamp": self.timestamp,
            "context": self.context,
            "tags": self.tags,
            "linked_entries": self.linked_entries,
            "access_count": self.access_count,
            "last_accessed": self.last_accessed,
            "decay_factor": self.decay_factor,
        }

    def get_importance_weight(self) -> float:
        return _IMPORTANCE_WEIGHTS.get(self.importance, 0.5)

    def compute_effective_score(self, now: Optional[float] = None) -> float:
        current = now or time.time()

        importance_score = self.get_importance_weight() * 0.4

        time_since_access = current - self.last_accessed
        recency_score = max(0.0, 1.0 - time_since_access / 86400.0) * 0.3

        access_score = min(self.access_count * 0.05, 0.2)

        decay_score = self.decay_factor * 0.1

        return importance_score + recency_score + access_score + decay_score


class ExperienceMemoryEngine:
    """
    Hermes-style experience memory system with trajectory compression.

    Stores agent experiences with metadata tagging, compresses similar
    experiences for efficient retrieval, and provides context-aware
    memory recall. Supports episodic/semantic separation, importance-based
    retention, time-decay weighting, and memory chain linking.
    """

    _instance: Optional["ExperienceMemoryEngine"] = None
    _lock = threading.RLock()

    _MAX_ENTRIES: int = 10000
    _MAX_ENTRIES_PER_AGENT: int = 2000
    _MAX_LINKED_ENTRIES: int = 20
    _MAX_TAGS_PER_ENTRY: int = 20
    _COMPRESSION_SIMILARITY_THRESHOLD: float = 0.6
    _CONSOLIDATION_MIN_ENTRIES: int = 5
    _DEFAULT_DECAY_INTERVAL: float = 3600.0

    def __init__(self) -> None:
        self._entries: Dict[str, ExperienceEntry] = {}
        self._agent_index: Dict[str, Set[str]] = {}
        self._tag_index: Dict[str, Set[str]] = {}
        self._type_index: Dict[str, Set[str]] = {}
        self._compressed_chains: Dict[str, List[str]] = {}
        self._total_recorded: int = 0
        self._total_compressed: int = 0
        self._total_consolidated: int = 0
        self._total_forgotten: int = 0

    @classmethod
    def get_instance(cls) -> "ExperienceMemoryEngine":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    # ------------------------------------------------------------------
    # Experience Recording
    # ------------------------------------------------------------------

    def record_experience(
        self,
        agent_id: str,
        content: str,
        memory_type: MemoryType = MemoryType.EPISODIC,
        importance: ExperienceImportance = ExperienceImportance.MODERATE,
        context: Optional[Dict[str, Any]] = None,
        tags: Optional[List[str]] = None,
    ) -> ExperienceEntry:
        with self._lock:
            self._enforce_max_entries()
            self._enforce_agent_limit(agent_id)

            entry = ExperienceEntry(
                agent_id=agent_id,
                memory_type=memory_type,
                content=content,
                summary=self._generate_summary(content),
                importance=importance,
                context=context or {},
                tags=tags or [],
            )

            self._entries[entry.entry_id] = entry
            self._total_recorded += 1

            self._add_to_index(self._agent_index, agent_id, entry.entry_id)
            for tag in entry.tags:
                self._add_to_index(self._tag_index, tag, entry.entry_id)
            self._add_to_index(self._type_index, memory_type.value, entry.entry_id)

            return entry

    # ------------------------------------------------------------------
    # Memory Retrieval
    # ------------------------------------------------------------------

    def retrieve_memories(
        self,
        agent_id: str,
        query: str = "",
        memory_type: Optional[MemoryType] = None,
        min_importance: Optional[ExperienceImportance] = None,
        tags: Optional[List[str]] = None,
        limit: int = 10,
        include_decayed: bool = True,
    ) -> List[ExperienceEntry]:
        candidate_ids = self._agent_index.get(agent_id, set()).copy()

        if memory_type is not None:
            type_ids = self._type_index.get(memory_type.value, set())
            candidate_ids = candidate_ids.intersection(type_ids)

        if tags:
            for tag in tags:
                tag_ids = self._tag_index.get(tag, set())
                candidate_ids = candidate_ids.intersection(tag_ids)

        if not candidate_ids:
            return []

        results: List[Tuple[ExperienceEntry, float]] = []
        now = time.time()
        query_lower = query.lower()
        query_tokens = set(query_lower.split()) if query_lower else set()

        for entry_id in candidate_ids:
            entry = self._entries.get(entry_id)
            if entry is None:
                continue

            if min_importance is not None:
                if _IMPORTANCE_ORDER[entry.importance] < _IMPORTANCE_ORDER[min_importance]:
                    continue

            if not include_decayed and entry.decay_factor < 0.1:
                continue

            score = self._compute_retrieval_score(entry, query_lower, query_tokens, now)

            entry.access_count += 1
            entry.last_accessed = now

            results.append((entry, score))

        results.sort(key=lambda r: r[1], reverse=True)
        return [entry for entry, _ in results[:limit]]

    def retrieve_context(
        self,
        agent_id: str,
        current_context: Dict[str, Any],
        max_tokens: int = 4096,
    ) -> str:
        relevant = self.retrieve_memories(
            agent_id=agent_id,
            min_importance=ExperienceImportance.LOW,
            limit=20,
            include_decayed=False,
        )

        if not relevant:
            return ""

        context_parts: List[str] = []
        estimated_tokens = 0

        context_parts.append("--- Relevant Past Experiences ---")
        estimated_tokens += 8

        for entry in relevant:
            snippet = f"[{entry.memory_type.value}] {entry.summary}"
            token_estimate = len(snippet) // 4
            if estimated_tokens + token_estimate > max_tokens:
                break
            context_parts.append(snippet)
            estimated_tokens += token_estimate

        context_keys = set()
        for entry in relevant:
            for key in entry.context:
                if key not in context_keys and key in current_context:
                    context_keys.add(key)
                    val = entry.context[key]
                    snippet = f"  {key}: {str(val)[:100]}"
                    token_estimate = len(snippet) // 4
                    if estimated_tokens + token_estimate > max_tokens:
                        break
                    context_parts.append(snippet)
                    estimated_tokens += token_estimate

        return "\n".join(context_parts)

    def get_entry(self, entry_id: str) -> Optional[ExperienceEntry]:
        entry = self._entries.get(entry_id)
        if entry is not None:
            entry.access_count += 1
            entry.last_accessed = time.time()
        return entry

    def search_by_similarity(
        self,
        agent_id: str,
        query_embedding: List[float],
        limit: int = 10,
    ) -> List[ExperienceEntry]:
        candidate_ids = self._agent_index.get(agent_id, set())
        if not candidate_ids or not query_embedding:
            return []

        results: List[Tuple[ExperienceEntry, float]] = []
        for entry_id in candidate_ids:
            entry = self._entries.get(entry_id)
            if entry is None:
                continue
            content_hash = hashlib.sha256(entry.content.encode("utf-8")).hexdigest()
            content_vec = self._text_to_embedding(content_hash, len(query_embedding))
            sim = self._cosine_similarity(query_embedding, content_vec)
            results.append((entry, sim))

        results.sort(key=lambda r: r[1], reverse=True)
        return [entry for entry, _ in results[:limit]]

    # ------------------------------------------------------------------
    # Trajectory Compression
    # ------------------------------------------------------------------

    def compress_trajectory(
        self,
        agent_id: str,
        time_window: float = 3600.0,
    ) -> List[ExperienceEntry]:
        with self._lock:
            agent_entries = [
                self._entries[eid]
                for eid in self._agent_index.get(agent_id, set())
                if eid in self._entries
            ]

            if len(agent_entries) < 2:
                return []

            agent_entries.sort(key=lambda e: e.timestamp)
            compressed: List[ExperienceEntry] = []
            now = time.time()

            i = 0
            while i < len(agent_entries):
                group = [agent_entries[i]]
                j = i + 1
                while j < len(agent_entries):
                    if agent_entries[j].timestamp - group[0].timestamp <= time_window:
                        if self._are_similar(group[0], agent_entries[j]):
                            group.append(agent_entries[j])
                        else:
                            break
                    else:
                        break
                    j += 1

                if len(group) >= 2:
                    compressed_entry = self._merge_group(agent_id, group)
                    if compressed_entry is not None:
                        compressed.append(compressed_entry)
                        self._total_compressed += 1

                        chain_id = compressed_entry.entry_id
                        self._compressed_chains[chain_id] = [
                            e.entry_id for e in group
                        ]

                        for old_entry in group:
                            self._remove_entry_silent(old_entry.entry_id)

                i = j

            return compressed

    # ------------------------------------------------------------------
    # Memory Consolidation
    # ------------------------------------------------------------------

    def consolidate_memories(
        self,
        agent_id: str,
        target_type: MemoryType = MemoryType.SEMANTIC,
    ) -> List[ExperienceEntry]:
        with self._lock:
            episodic_ids = [
                eid
                for eid in self._agent_index.get(agent_id, set())
                if eid in self._entries
                and self._entries[eid].memory_type == MemoryType.EPISODIC
            ]

            if len(episodic_ids) < self._CONSOLIDATION_MIN_ENTRIES:
                return []

            episodic_entries = [self._entries[eid] for eid in episodic_ids]
            episodic_entries.sort(key=lambda e: e.timestamp)

            consolidated: List[ExperienceEntry] = []
            batch_size = max(self._CONSOLIDATION_MIN_ENTRIES, len(episodic_entries) // 5)

            for batch_start in range(0, len(episodic_entries), batch_size):
                batch = episodic_entries[batch_start : batch_start + batch_size]
                if len(batch) < 2:
                    continue

                combined_content = "\n".join(
                    f"- {e.summary}" for e in batch
                )
                combined_tags: Set[str] = set()
                for e in batch:
                    combined_tags.update(e.tags)

                avg_importance = self._average_importance(batch)
                max_importance = max(batch, key=lambda e: _IMPORTANCE_ORDER[e.importance])

                consolidated_entry = ExperienceEntry(
                    agent_id=agent_id,
                    memory_type=target_type,
                    content=combined_content,
                    summary=self._generate_summary(combined_content),
                    importance=avg_importance,
                    context=max_importance.context.copy(),
                    tags=list(combined_tags)[:self._MAX_TAGS_PER_ENTRY],
                    linked_entries=[e.entry_id for e in batch],
                )

                self._entries[consolidated_entry.entry_id] = consolidated_entry
                self._add_to_index(self._agent_index, agent_id, consolidated_entry.entry_id)
                for tag in consolidated_entry.tags:
                    self._add_to_index(self._tag_index, tag, consolidated_entry.entry_id)
                self._add_to_index(
                    self._type_index, target_type.value, consolidated_entry.entry_id
                )

                consolidated.append(consolidated_entry)
                self._total_consolidated += 1

                for old_entry in batch:
                    self._remove_entry_silent(old_entry.entry_id)

            return consolidated

    # ------------------------------------------------------------------
    # Entry Management
    # ------------------------------------------------------------------

    def link_entries(self, entry_id_a: str, entry_id_b: str) -> bool:
        with self._lock:
            entry_a = self._entries.get(entry_id_a)
            entry_b = self._entries.get(entry_id_b)
            if entry_a is None or entry_b is None:
                return False
            if entry_id_a == entry_id_b:
                return False

            if entry_id_b not in entry_a.linked_entries and len(entry_a.linked_entries) < self._MAX_LINKED_ENTRIES:
                entry_a.linked_entries.append(entry_id_b)

            if entry_id_a not in entry_b.linked_entries and len(entry_b.linked_entries) < self._MAX_LINKED_ENTRIES:
                entry_b.linked_entries.append(entry_id_a)

            return True

    def update_importance(
        self, entry_id: str, new_importance: ExperienceImportance
    ) -> bool:
        entry = self._entries.get(entry_id)
        if entry is None:
            return False
        entry.importance = new_importance
        return True

    def forget_entry(self, entry_id: str) -> bool:
        with self._lock:
            entry = self._entries.get(entry_id)
            if entry is None:
                return False
            self._remove_entry_silent(entry_id)
            self._total_forgotten += 1
            return True

    # ------------------------------------------------------------------
    # Statistics
    # ------------------------------------------------------------------

    def get_agent_memory_stats(self, agent_id: str) -> Dict[str, Any]:
        agent_entries = [
            self._entries[eid]
            for eid in self._agent_index.get(agent_id, set())
            if eid in self._entries
        ]

        type_counts: Dict[str, int] = {}
        importance_counts: Dict[str, int] = {}
        total_accesses = 0
        total_decay = 0.0

        for entry in agent_entries:
            mt = entry.memory_type.value
            type_counts[mt] = type_counts.get(mt, 0) + 1
            imp = entry.importance.value
            importance_counts[imp] = importance_counts.get(imp, 0) + 1
            total_accesses += entry.access_count
            total_decay += entry.decay_factor

        n = len(agent_entries)
        return {
            "agent_id": agent_id,
            "total_entries": n,
            "by_type": type_counts,
            "by_importance": importance_counts,
            "total_accesses": total_accesses,
            "avg_accesses": round(total_accesses / n, 2) if n > 0 else 0.0,
            "avg_decay_factor": round(total_decay / n, 4) if n > 0 else 0.0,
            "compressed_chains": sum(
                1 for chain in self._compressed_chains.values()
                if any(
                    self._entries.get(eid) and self._entries[eid].agent_id == agent_id
                    for eid in chain
                )
            ),
        }

    def get_stats(self) -> Dict[str, Any]:
        with self._lock:
            type_counts: Dict[str, int] = {}
            importance_counts: Dict[str, int] = {}

            for entry in self._entries.values():
                mt = entry.memory_type.value
                type_counts[mt] = type_counts.get(mt, 0) + 1
                imp = entry.importance.value
                importance_counts[imp] = importance_counts.get(imp, 0) + 1

            return {
                "total_entries": len(self._entries),
                "total_recorded": self._total_recorded,
                "total_compressed": self._total_compressed,
                "total_consolidated": self._total_consolidated,
                "total_forgotten": self._total_forgotten,
                "unique_agents": len(self._agent_index),
                "unique_tags": len(self._tag_index),
                "compressed_chains": len(self._compressed_chains),
                "by_memory_type": type_counts,
                "by_importance": importance_counts,
                "max_entries_limit": self._MAX_ENTRIES,
                "max_entries_per_agent": self._MAX_ENTRIES_PER_AGENT,
            }

    def reset(self) -> None:
        with self._lock:
            self._entries.clear()
            self._agent_index.clear()
            self._tag_index.clear()
            self._type_index.clear()
            self._compressed_chains.clear()
            self._total_recorded = 0
            self._total_compressed = 0
            self._total_consolidated = 0
            self._total_forgotten = 0

    # ------------------------------------------------------------------
    # Internal Helpers
    # ------------------------------------------------------------------

    def _add_to_index(
        self, index: Dict[str, Set[str]], key: str, entry_id: str
    ) -> None:
        if key not in index:
            index[key] = set()
        index[key].add(entry_id)

    def _remove_from_index(
        self, index: Dict[str, Set[str]], key: str, entry_id: str
    ) -> None:
        if key in index:
            index[key].discard(entry_id)
            if not index[key]:
                del index[key]

    def _remove_entry_silent(self, entry_id: str) -> None:
        entry = self._entries.pop(entry_id, None)
        if entry is None:
            return

        self._remove_from_index(self._agent_index, entry.agent_id, entry_id)
        for tag in entry.tags:
            self._remove_from_index(self._tag_index, tag, entry_id)
        self._remove_from_index(self._type_index, entry.memory_type.value, entry_id)

        for other_id in entry.linked_entries:
            other = self._entries.get(other_id)
            if other is not None and entry_id in other.linked_entries:
                other.linked_entries.remove(entry_id)

    def _generate_summary(self, content: str) -> str:
        if not content:
            return ""
        lines = content.strip().split("\n")
        if lines:
            first_line = lines[0].strip()
            if len(first_line) > 200:
                return first_line[:197] + "..."
            return first_line
        return ""

    def _compute_retrieval_score(
        self,
        entry: ExperienceEntry,
        query_lower: str,
        query_tokens: Set[str],
        now: float,
    ) -> float:
        score = 0.0

        if query_lower:
            content_lower = entry.content.lower()
            if query_lower in content_lower:
                score += 0.5

            content_tokens = set(content_lower.split())
            matching = query_tokens.intersection(content_tokens)
            if matching:
                score += len(matching) / max(len(query_tokens), 1) * 0.3

            tag_lower = {t.lower() for t in entry.tags}
            tag_match = query_tokens.intersection(tag_lower)
            if tag_match:
                score += len(tag_match) / max(len(query_tokens), 1) * 0.2

            if query_lower in entry.summary.lower():
                score += 0.3
        else:
            score += 0.1

        importance_weight = entry.get_importance_weight()
        score += importance_weight * 0.2

        time_since_access = max(0.0, now - entry.last_accessed)
        recency = max(0.0, 1.0 - time_since_access / 86400.0)
        score += recency * 0.15

        access_bonus = min(entry.access_count * 0.02, 0.1)
        score += access_bonus

        score *= entry.decay_factor

        return min(1.0, score)

    def _are_similar(self, entry_a: ExperienceEntry, entry_b: ExperienceEntry) -> bool:
        if entry_a.memory_type != entry_b.memory_type:
            return False

        tokens_a = set(entry_a.content.lower().split())
        tokens_b = set(entry_b.content.lower().split())

        if not tokens_a or not tokens_b:
            return False

        intersection = tokens_a.intersection(tokens_b)
        union = tokens_a.union(tokens_b)
        jaccard = len(intersection) / len(union) if union else 0.0

        return jaccard >= self._COMPRESSION_SIMILARITY_THRESHOLD

    def _merge_group(
        self, agent_id: str, group: List[ExperienceEntry]
    ) -> Optional[ExperienceEntry]:
        if not group:
            return None

        combined_content = "\n---\n".join(
            f"[{e.timestamp}] {e.content}" for e in group
        )
        combined_summary = "\n".join(f"- {e.summary}" for e in group)

        all_tags: Set[str] = set()
        for e in group:
            all_tags.update(e.tags)

        avg_importance = self._average_importance(group)
        best_context = max(group, key=lambda e: len(e.context)).context.copy()

        compressed = ExperienceEntry(
            agent_id=agent_id,
            memory_type=group[0].memory_type,
            content=combined_content,
            summary=combined_summary,
            importance=avg_importance,
            timestamp=group[-1].timestamp,
            context=best_context,
            tags=list(all_tags)[:self._MAX_TAGS_PER_ENTRY],
        )

        self._entries[compressed.entry_id] = compressed
        self._add_to_index(self._agent_index, agent_id, compressed.entry_id)
        for tag in compressed.tags:
            self._add_to_index(self._tag_index, tag, compressed.entry_id)
        self._add_to_index(
            self._type_index, compressed.memory_type.value, compressed.entry_id
        )

        return compressed

    def _average_importance(
        self, entries: List[ExperienceEntry]
    ) -> ExperienceImportance:
        if not entries:
            return ExperienceImportance.MODERATE

        total = sum(_IMPORTANCE_ORDER[e.importance] for e in entries)
        avg = round(total / len(entries))

        for imp in ExperienceImportance:
            if _IMPORTANCE_ORDER[imp] == avg:
                return imp

        return ExperienceImportance.MODERATE

    def _cosine_similarity(
        self, vec_a: List[float], vec_b: List[float]
    ) -> float:
        if not vec_a or not vec_b or len(vec_a) != len(vec_b):
            return 0.0

        dot = sum(a * b for a, b in zip(vec_a, vec_b))
        mag_a = math.sqrt(sum(a * a for a in vec_a))
        mag_b = math.sqrt(sum(b * b for b in vec_b))

        if mag_a == 0.0 or mag_b == 0.0:
            return 0.0

        return dot / (mag_a * mag_b)

    def _text_to_embedding(self, text: str, dims: int) -> List[float]:
        if dims <= 0:
            return []

        hash_val = int(hashlib.sha256(text.encode("utf-8")).hexdigest(), 16)
        embedding: List[float] = []
        for i in range(dims):
            seed = (hash_val + i * 2654435761) & 0xFFFFFFFF
            val = ((seed * 1103515245 + 12345) & 0x7FFFFFFF) / 0x7FFFFFFF
            embedding.append(round(val * 2.0 - 1.0, 6))
        return embedding

    def _enforce_max_entries(self) -> None:
        if len(self._entries) < self._MAX_ENTRIES:
            return

        entries_by_score = sorted(
            self._entries.items(),
            key=lambda item: item[1].compute_effective_score(),
        )

        overflow = len(self._entries) - self._MAX_ENTRIES + 1
        for entry_id, _ in entries_by_score[:overflow]:
            self._remove_entry_silent(entry_id)

    def _enforce_agent_limit(self, agent_id: str) -> None:
        agent_entries = list(self._agent_index.get(agent_id, set()))
        if len(agent_entries) < self._MAX_ENTRIES_PER_AGENT:
            return

        scored = [
            (eid, self._entries[eid].compute_effective_score())
            for eid in agent_entries
            if eid in self._entries
        ]
        scored.sort(key=lambda x: x[1])

        overflow = len(scored) - self._MAX_ENTRIES_PER_AGENT + 1
        for entry_id, _ in scored[:overflow]:
            self._remove_entry_silent(entry_id)


def get_experience_memory() -> ExperienceMemoryEngine:
    return ExperienceMemoryEngine.get_instance()