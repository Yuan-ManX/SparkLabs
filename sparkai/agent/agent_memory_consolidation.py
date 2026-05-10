"""
SparkLabs Agent - Memory Consolidation Engine

Unified memory architecture bridging semantic, episodic, and working
memory domains for persistent agent reasoning across extended game
development sessions. Enables agents to maintain coherent context,
recall past decisions, and surface relevant historical knowledge
during AI-native game creation workflows.

Architecture:
  MemoryConsolidationEngine
    |-- SemanticStore (factual game design knowledge base)
    |-- EpisodicBuffer (session-level interaction records)
    |-- WorkingMemory (active context window management)
    |-- ConsolidationScheduler (importance-weighted memory transfer)
    |-- RetrievalRouter (multi-source memory query dispatch)
    |-- DecayManager (temporal relevance scoring)

Memory Domains:
  - SEMANTIC: domain facts, design patterns, engine capabilities
  - EPISODIC: user interactions, agent decisions, project events
  - WORKING: current task context, recent observations, pending actions
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


class MemoryDomain(Enum):
    SEMANTIC = "semantic"
    EPISODIC = "episodic"
    WORKING = "working"


class ConsolidationMode(Enum):
    IMMEDIATE = "immediate"
    SCHEDULED = "scheduled"
    IMPORTANCE_DRIVEN = "importance_driven"
    MANUAL = "manual"


class MemoryPriority(Enum):
    CRITICAL = 5
    HIGH = 4
    MEDIUM = 3
    LOW = 2
    TRANSIENT = 1


@dataclass
class MemoryEntry:
    entry_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    domain: MemoryDomain = MemoryDomain.WORKING
    content: Dict[str, Any] = field(default_factory=dict)
    priority: MemoryPriority = MemoryPriority.MEDIUM
    importance: float = 0.5
    tags: List[str] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    last_accessed: float = field(default_factory=time.time)
    access_count: int = 0
    decay_rate: float = 0.01
    source_agent: str = "system"

    def relevance_score(self, current_time: Optional[float] = None) -> float:
        t = current_time or time.time()
        age = max(0.0, t - self.created_at)
        recency = max(0.0, t - self.last_accessed)
        usage_bonus = min(0.3, self.access_count * 0.05)
        return self.importance * (1.0 / (1.0 + self.decay_rate * age)) * (1.0 / (1.0 + 0.1 * recency)) + usage_bonus

    def to_dict(self) -> Dict[str, Any]:
        return {
            "entry_id": self.entry_id,
            "domain": self.domain.value,
            "priority": self.priority.name,
            "importance": self.importance,
            "tags": self.tags,
            "relevance": self.relevance_score(),
            "source_agent": self.source_agent,
        }


@dataclass
class ConsolidationLog:
    log_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    source_domain: MemoryDomain = MemoryDomain.WORKING
    target_domain: MemoryDomain = MemoryDomain.EPISODIC
    entries_processed: int = 0
    entries_promoted: int = 0
    entries_discarded: int = 0
    duration_ms: float = 0.0
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "log_id": self.log_id,
            "source": self.source_domain.value,
            "target": self.target_domain.value,
            "processed": self.entries_processed,
            "promoted": self.entries_promoted,
            "discarded": self.entries_discarded,
            "duration_ms": self.duration_ms,
        }


class MemoryConsolidationEngine:
    _instance: Optional[MemoryConsolidationEngine] = None

    @classmethod
    def get_instance(cls) -> MemoryConsolidationEngine:
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self):
        self._semantic_store: Dict[str, MemoryEntry] = {}
        self._episodic_buffer: Dict[str, MemoryEntry] = {}
        self._working_memory: Dict[str, MemoryEntry] = {}
        self._consolidation_logs: List[ConsolidationLog] = []
        self._mode: ConsolidationMode = ConsolidationMode.IMPORTANCE_DRIVEN
        self._importance_threshold: float = 0.3
        self._max_working_size: int = 100
        self._total_consolidations: int = 0

    def store(self, content: Dict[str, Any], domain: MemoryDomain = MemoryDomain.WORKING,
              priority: MemoryPriority = MemoryPriority.MEDIUM, importance: float = 0.5,
              tags: Optional[List[str]] = None, source_agent: str = "system") -> str:
        entry = MemoryEntry(
            domain=domain,
            content=content,
            priority=priority,
            importance=importance,
            tags=tags or [],
            source_agent=source_agent,
        )
        if domain == MemoryDomain.SEMANTIC:
            self._semantic_store[entry.entry_id] = entry
        elif domain == MemoryDomain.EPISODIC:
            self._episodic_buffer[entry.entry_id] = entry
        else:
            self._working_memory[entry.entry_id] = entry
        self._enforce_working_limit()
        return entry.entry_id

    def recall(self, entry_id: str) -> Optional[MemoryEntry]:
        for store in [self._working_memory, self._episodic_buffer, self._semantic_store]:
            if entry_id in store:
                entry = store[entry_id]
                entry.last_accessed = time.time()
                entry.access_count += 1
                return entry
        return None

    def query(self, domain: Optional[MemoryDomain] = None, tags: Optional[List[str]] = None,
              min_importance: float = 0.0, limit: int = 20) -> List[MemoryEntry]:
        results = []
        stores = {
            MemoryDomain.WORKING: self._working_memory,
            MemoryDomain.EPISODIC: self._episodic_buffer,
            MemoryDomain.SEMANTIC: self._semantic_store,
        }
        target_stores = [stores[domain]] if domain else [self._working_memory, self._episodic_buffer, self._semantic_store]
        for store in target_stores:
            for entry in store.values():
                if entry.importance >= min_importance:
                    if tags is None or any(t in entry.tags for t in tags):
                        results.append(entry)
        results.sort(key=lambda e: e.relevance_score(), reverse=True)
        return results[:limit]

    def consolidate(self, source: MemoryDomain = MemoryDomain.WORKING,
                    target: MemoryDomain = MemoryDomain.EPISODIC) -> ConsolidationLog:
        start = time.time()
        source_store = {MemoryDomain.WORKING: self._working_memory,
                        MemoryDomain.EPISODIC: self._episodic_buffer,
                        MemoryDomain.SEMANTIC: self._semantic_store}.get(source, self._working_memory)
        target_store = {MemoryDomain.WORKING: self._working_memory,
                        MemoryDomain.EPISODIC: self._episodic_buffer,
                        MemoryDomain.SEMANTIC: self._semantic_store}.get(target, self._episodic_buffer)
        log = ConsolidationLog(source_domain=source, target_domain=target)
        promoted = []
        discarded = []
        for entry_id, entry in list(source_store.items()):
            if entry_id in target_store:
                continue
            if entry.importance >= self._importance_threshold:
                target_store[entry_id] = entry
                promoted.append(entry_id)
            else:
                discarded.append(entry_id)
        for eid in promoted:
            source_store.pop(eid, None)
        for eid in discarded:
            source_store.pop(eid, None)
        log.entries_processed = len(promoted) + len(discarded)
        log.entries_promoted = len(promoted)
        log.entries_discarded = len(discarded)
        log.duration_ms = (time.time() - start) * 1000
        self._consolidation_logs.append(log)
        self._total_consolidations += 1
        if len(self._consolidation_logs) > 50:
            self._consolidation_logs = self._consolidation_logs[-50:]
        return log

    def _enforce_working_limit(self):
        if len(self._working_memory) > self._max_working_size:
            sorted_entries = sorted(self._working_memory.values(), key=lambda e: e.relevance_score())
            excess = len(self._working_memory) - self._max_working_size
            for entry in sorted_entries[:excess]:
                if entry.importance >= self._importance_threshold:
                    self._episodic_buffer[entry.entry_id] = entry
                del self._working_memory[entry.entry_id]

    def get_domain_summary(self) -> Dict[str, Any]:
        return {
            "semantic": len(self._semantic_store),
            "episodic": len(self._episodic_buffer),
            "working": len(self._working_memory),
            "consolidations": self._total_consolidations,
            "mode": self._mode.value,
        }

    def get_stats(self) -> Dict[str, Any]:
        return {
            **self.get_domain_summary(),
            "total_entries": len(self._semantic_store) + len(self._episodic_buffer) + len(self._working_memory),
            "importance_threshold": self._importance_threshold,
            "max_working_size": self._max_working_size,
        }


def get_memory_consolidation() -> MemoryConsolidationEngine:
    return MemoryConsolidationEngine.get_instance()