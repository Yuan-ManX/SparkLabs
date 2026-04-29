"""
SparkAI Agent - Memory System

Multi-layered agent memory with episodic, semantic, and procedural layers.

Memory Layers:
  - Episodic: Records of specific events and interactions
  - Semantic: General knowledge and facts about the game world
  - Procedural: Learned skills and action patterns

Memory enables agents to:
  - Recall past interactions and decisions
  - Build knowledge about the game project
  - Learn from experience and improve over time
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class MemoryLayer(Enum):
    EPISODIC = "episodic"
    SEMANTIC = "semantic"
    PROCEDURAL = "procedural"


@dataclass
class MemoryEntry:
    """
    A single memory entry in the agent's memory system.
    """
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    layer: str = MemoryLayer.EPISODIC.value
    content: str = ""
    tags: List[str] = field(default_factory=list)
    importance: float = 0.5
    timestamp: float = field(default_factory=time.time)
    access_count: int = 0
    last_accessed: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def access(self) -> str:
        self.access_count += 1
        self.last_accessed = time.time()
        return self.content

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "layer": self.layer,
            "content": self.content[:200],
            "tags": self.tags,
            "importance": self.importance,
            "timestamp": self.timestamp,
            "access_count": self.access_count,
        }


class MemoryLayerStore:
    """
    A single layer of agent memory.
    Supports storage, retrieval, search, and decay.
    """

    def __init__(self, layer: MemoryLayer, max_entries: int = 1000):
        self.layer = layer
        self.max_entries = max_entries
        self._entries: Dict[str, MemoryEntry] = {}

    def store(self, content: str, tags: Optional[List[str]] = None, importance: float = 0.5, metadata: Optional[Dict[str, Any]] = None) -> MemoryEntry:
        if len(self._entries) >= self.max_entries:
            self._evict()
        entry = MemoryEntry(
            layer=self.layer.value,
            content=content,
            tags=tags or [],
            importance=importance,
            metadata=metadata or {},
        )
        self._entries[entry.id] = entry
        return entry

    def get(self, entry_id: str) -> Optional[MemoryEntry]:
        entry = self._entries.get(entry_id)
        if entry:
            entry.access()
        return entry

    def search(self, query: str, limit: int = 10) -> List[MemoryEntry]:
        query_lower = query.lower()
        scored = []
        for entry in self._entries.values():
            score = 0.0
            if query_lower in entry.content.lower():
                score += 1.0
            for tag in entry.tags:
                if query_lower in tag.lower():
                    score += 0.5
            score += entry.importance * 0.3
            score += min(entry.access_count * 0.1, 1.0)
            if score > 0:
                scored.append((score, entry))
        scored.sort(key=lambda x: x[0], reverse=True)
        results = [entry for _, entry in scored[:limit]]
        for entry in results:
            entry.access()
        return results

    def search_by_tags(self, tags: List[str], limit: int = 10) -> List[MemoryEntry]:
        tag_set = set(t.lower() for t in tags)
        results = []
        for entry in self._entries.values():
            entry_tags = set(t.lower() for t in entry.tags)
            overlap = len(tag_set & entry_tags)
            if overlap > 0:
                results.append((overlap, entry))
        results.sort(key=lambda x: x[0], reverse=True)
        return [entry for _, entry in results[:limit]]

    def get_recent(self, count: int = 10) -> List[MemoryEntry]:
        entries = sorted(self._entries.values(), key=lambda e: e.timestamp, reverse=True)
        return entries[:count]

    def get_important(self, count: int = 10) -> List[MemoryEntry]:
        entries = sorted(self._entries.values(), key=lambda e: e.importance, reverse=True)
        return entries[:count]

    def count(self) -> int:
        return len(self._entries)

    def _evict(self) -> None:
        if not self._entries:
            return
        oldest = min(self._entries.values(), key=lambda e: e.last_accessed)
        del self._entries[oldest.id]

    def clear(self) -> None:
        self._entries.clear()


class AgentMemorySystem:
    """
    Multi-layered agent memory system.

    Combines episodic, semantic, and procedural memory layers
    to give agents comprehensive recall capabilities.
    """

    def __init__(
        self,
        episodic_limit: int = 500,
        semantic_limit: int = 1000,
        procedural_limit: int = 200,
    ):
        self.episodic = MemoryLayerStore(MemoryLayer.EPISODIC, episodic_limit)
        self.semantic = MemoryLayerStore(MemoryLayer.SEMANTIC, semantic_limit)
        self.procedural = MemoryLayerStore(MemoryLayer.PROCEDURAL, procedural_limit)

    def record_event(self, content: str, tags: Optional[List[str]] = None, importance: float = 0.5) -> MemoryEntry:
        return self.episodic.store(content, tags, importance)

    def store_knowledge(self, content: str, tags: Optional[List[str]] = None, importance: float = 0.7) -> MemoryEntry:
        return self.semantic.store(content, tags, importance)

    def store_procedure(self, content: str, tags: Optional[List[str]] = None, importance: float = 0.8) -> MemoryEntry:
        return self.procedural.store(content, tags, importance)

    def recall(self, query: str, limit: int = 10) -> List[MemoryEntry]:
        results = []
        results.extend(self.episodic.search(query, limit))
        results.extend(self.semantic.search(query, limit))
        results.extend(self.procedural.search(query, limit))
        results.sort(key=lambda e: e.importance, reverse=True)
        return results[:limit]

    def recall_by_tags(self, tags: List[str], limit: int = 10) -> List[MemoryEntry]:
        results = []
        results.extend(self.episodic.search_by_tags(tags, limit))
        results.extend(self.semantic.search_by_tags(tags, limit))
        results.extend(self.procedural.search_by_tags(tags, limit))
        results.sort(key=lambda e: e.importance, reverse=True)
        return results[:limit]

    def get_context(self, query: str, max_entries: int = 5) -> str:
        entries = self.recall(query, max_entries)
        if not entries:
            return ""
        parts = []
        for entry in entries:
            parts.append(f"[{entry.layer}] {entry.content[:150]}")
        return "\n".join(parts)

    def size(self) -> Dict[str, int]:
        return {
            "episodic": self.episodic.count(),
            "semantic": self.semantic.count(),
            "procedural": self.procedural.count(),
            "total": self.episodic.count() + self.semantic.count() + self.procedural.count(),
        }

    def get_stats(self) -> Dict[str, Any]:
        return {
            "size": self.size(),
            "layers": {
                "episodic": {"count": self.episodic.count(), "max": self.episodic.max_entries},
                "semantic": {"count": self.semantic.count(), "max": self.semantic.max_entries},
                "procedural": {"count": self.procedural.count(), "max": self.procedural.max_entries},
            },
        }

    def clear(self) -> None:
        self.episodic.clear()
        self.semantic.clear()
        self.procedural.clear()
