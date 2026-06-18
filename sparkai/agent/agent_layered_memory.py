"""
SparkLabs Agent Layered Memory System

Provides a multi-layered memory architecture for AI game agents.
Each layer serves a distinct purpose: core memory for identity,
session memory for recent context, procedural memory for reusable
patterns, and episodic memory for significant experiences.

Core architecture:
  - Core Memory: Persistent identity, preferences, and critical knowledge
  - Session Memory: Short-term context with searchable history
  - Procedural Memory: Accumulated skills and behavioral patterns
  - Episodic Memory: Significant events and experiences
  - Memory Consolidation: Periodic promotion from session to core
"""

import threading
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class MemoryLayer(Enum):
    """Layers of the memory architecture."""
    CORE = "core"
    SESSION = "session"
    PROCEDURAL = "procedural"
    EPISODIC = "episodic"


class MemoryPriority(Enum):
    """Priority level for memory entries."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    TRANSIENT = "transient"


class MemoryCategory(Enum):
    """Categories for organizing memories."""
    IDENTITY = "identity"
    PREFERENCE = "preference"
    KNOWLEDGE = "knowledge"
    EXPERIENCE = "experience"
    RELATIONSHIP = "relationship"
    WORLD_STATE = "world_state"
    TASK = "task"
    CONVERSATION = "conversation"
    SKILL = "skill"
    EVENT = "event"


# ---------------------------------------------------------------------------
# Data Classes
# ---------------------------------------------------------------------------

@dataclass
class MemoryEntry:
    """A single memory entry in the layered memory system."""
    entry_id: str
    layer: MemoryLayer
    category: MemoryCategory
    priority: MemoryPriority
    content: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    source: Optional[str] = None
    access_count: int = 0
    last_accessed_at: float = field(default_factory=time.time)
    created_at: float = field(default_factory=time.time)
    expires_at: Optional[float] = None


@dataclass
class MemorySearchResult:
    """Result from a memory search query."""
    entry: MemoryEntry
    relevance_score: float
    matched_on: List[str] = field(default_factory=list)


@dataclass
class MemoryConsolidationResult:
    """Result of a memory consolidation operation."""
    entries_promoted: int = 0
    entries_archived: int = 0
    entries_expired: int = 0
    duration_ms: float = 0.0
    consolidated_at: float = field(default_factory=time.time)


# ---------------------------------------------------------------------------
# Layered Memory Engine
# ---------------------------------------------------------------------------

class LayeredMemoryEngine:
    """Multi-layered memory system for AI game agents.

    Implements a hierarchical memory architecture that separates
    persistent identity from transient context, enabling efficient
    retrieval and long-term knowledge accumulation.

    Usage:
        engine = get_layered_memory_engine()
        engine.store_core("My name is SparkLabs", category="identity")
        engine.store_session("User asked about game design", category="conversation")
        results = engine.search("game design", layers=[MemoryLayer.SESSION])
    """

    _instance: Optional["LayeredMemoryEngine"] = None
    _lock: threading.RLock = threading.RLock()

    MAX_CORE_ENTRIES: int = 200
    MAX_SESSION_ENTRIES: int = 2000
    MAX_PROCEDURAL_ENTRIES: int = 500
    MAX_EPISODIC_ENTRIES: int = 1000
    SESSION_TTL_MS: float = 3600000.0  # 1 hour
    CONSOLIDATION_INTERVAL_MS: float = 300000.0  # 5 minutes

    def __new__(cls) -> "LayeredMemoryEngine":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    @classmethod
    def get_instance(cls) -> "LayeredMemoryEngine":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def __init__(self) -> None:
        time.sleep(0.001)
        if not hasattr(self, "_initialized"):
            self._core: Dict[str, MemoryEntry] = {}
            self._session: Dict[str, MemoryEntry] = {}
            self._procedural: Dict[str, MemoryEntry] = {}
            self._episodic: Dict[str, MemoryEntry] = {}
            self._total_stored: int = 0
            self._total_retrieved: int = 0
            self._last_consolidation_at: float = 0.0
            self._initialized = True

    # ------------------------------------------------------------------
    # Storage by Layer
    # ------------------------------------------------------------------

    def store_core(
        self,
        content: str,
        category: str = "knowledge",
        priority: str = "high",
        metadata: Optional[Dict[str, Any]] = None,
        source: Optional[str] = None,
    ) -> MemoryEntry:
        """Store a persistent core memory entry.

        Core memory holds identity, preferences, and critical knowledge
        that should persist across sessions.
        """
        return self._store(
            MemoryLayer.CORE, self._core, self.MAX_CORE_ENTRIES,
            content, category, priority, metadata, source,
        )

    def store_session(
        self,
        content: str,
        category: str = "conversation",
        priority: str = "medium",
        metadata: Optional[Dict[str, Any]] = None,
        source: Optional[str] = None,
    ) -> MemoryEntry:
        """Store a session-scoped memory entry.

        Session memory holds recent context and is automatically
        cleaned up after the session TTL expires.
        """
        return self._store(
            MemoryLayer.SESSION, self._session, self.MAX_SESSION_ENTRIES,
            content, category, priority, metadata, source,
            ttl_ms=self.SESSION_TTL_MS,
        )

    def store_procedural(
        self,
        content: str,
        category: str = "skill",
        priority: str = "high",
        metadata: Optional[Dict[str, Any]] = None,
        source: Optional[str] = None,
    ) -> MemoryEntry:
        """Store a procedural memory entry.

        Procedural memory holds accumulated skills, patterns, and
        behavioral strategies for reuse.
        """
        return self._store(
            MemoryLayer.PROCEDURAL, self._procedural, self.MAX_PROCEDURAL_ENTRIES,
            content, category, priority, metadata, source,
        )

    def store_episodic(
        self,
        content: str,
        category: str = "event",
        priority: str = "medium",
        metadata: Optional[Dict[str, Any]] = None,
        source: Optional[str] = None,
    ) -> MemoryEntry:
        """Store an episodic memory entry.

        Episodic memory holds significant events and experiences
        that shape the agent's understanding over time.
        """
        return self._store(
            MemoryLayer.EPISODIC, self._episodic, self.MAX_EPISODIC_ENTRIES,
            content, category, priority, metadata, source,
        )

    def _store(
        self,
        layer: MemoryLayer,
        store: Dict[str, MemoryEntry],
        max_entries: int,
        content: str,
        category: str,
        priority: str,
        metadata: Optional[Dict[str, Any]],
        source: Optional[str],
        ttl_ms: Optional[float] = None,
    ) -> MemoryEntry:
        """Internal storage method."""
        time.sleep(0.001)
        with self._lock:
            entry = MemoryEntry(
                entry_id=uuid.uuid4().hex,
                layer=layer,
                category=MemoryCategory(category),
                priority=MemoryPriority(priority),
                content=content,
                metadata=metadata or {},
                source=source,
            )
            if ttl_ms:
                entry.expires_at = time.time() + ttl_ms / 1000.0

            store[entry.entry_id] = entry
            self._total_stored += 1

            # Prune if exceeding limit
            if len(store) > max_entries:
                self._prune_store(store, max_entries)

            return entry

    def _prune_store(self, store: Dict[str, MemoryEntry], max_entries: int) -> None:
        """Remove lowest-priority entries to stay within limits."""
        priority_order = {
            MemoryPriority.TRANSIENT: 0,
            MemoryPriority.LOW: 1,
            MemoryPriority.MEDIUM: 2,
            MemoryPriority.HIGH: 3,
            MemoryPriority.CRITICAL: 4,
        }
        entries = sorted(
            store.values(),
            key=lambda e: (priority_order.get(e.priority, 0), e.last_accessed_at),
        )
        to_remove = entries[:len(entries) - max_entries]
        for entry in to_remove:
            del store[entry.entry_id]

    # ------------------------------------------------------------------
    # Retrieval
    # ------------------------------------------------------------------

    def search(
        self,
        query: str,
        layers: Optional[List[str]] = None,
        categories: Optional[List[str]] = None,
        limit: int = 20,
        min_priority: str = "low",
    ) -> List[MemorySearchResult]:
        """Search across memory layers for relevant entries.

        Args:
            query: Search query string.
            layers: Optional list of layer names to search.
            categories: Optional list of category names to filter.
            limit: Maximum results.
            min_priority: Minimum priority level.

        Returns:
            List of MemorySearchResult sorted by relevance.
        """
        time.sleep(0.001)
        with self._lock:
            results: List[MemorySearchResult] = []

            layer_enums = [MemoryLayer(l) for l in layers] if layers else list(MemoryLayer)
            category_enums = [MemoryCategory(c) for c in categories] if categories else None
            min_prio = MemoryPriority(min_priority)

            layer_map = {
                MemoryLayer.CORE: self._core,
                MemoryLayer.SESSION: self._session,
                MemoryLayer.PROCEDURAL: self._procedural,
                MemoryLayer.EPISODIC: self._episodic,
            }

            query_lower = query.lower()

            for layer in layer_enums:
                store = layer_map.get(layer, {})
                for entry in list(store.values()):
                    # Skip expired entries
                    if entry.expires_at and entry.expires_at < time.time():
                        del store[entry.entry_id]
                        continue

                    # Filter by category
                    if category_enums and entry.category not in category_enums:
                        continue

                    # Filter by priority
                    priority_order = {
                        MemoryPriority.CRITICAL: 5,
                        MemoryPriority.HIGH: 4,
                        MemoryPriority.MEDIUM: 3,
                        MemoryPriority.LOW: 2,
                        MemoryPriority.TRANSIENT: 1,
                    }
                    if priority_order.get(entry.priority, 0) < priority_order.get(min_prio, 0):
                        continue

                    # Calculate relevance
                    relevance = self._calculate_relevance(query_lower, entry)
                    if relevance > 0:
                        matched = []
                        if query_lower in entry.content.lower():
                            matched.append("content")
                        if query_lower in entry.category.value.lower():
                            matched.append("category")
                        if any(query_lower in v.lower() for v in entry.metadata.values() if isinstance(v, str)):
                            matched.append("metadata")

                        results.append(MemorySearchResult(
                            entry=entry,
                            relevance_score=relevance,
                            matched_on=matched,
                        ))

                        entry.access_count += 1
                        entry.last_accessed_at = time.time()
                        self._total_retrieved += 1

            results.sort(key=lambda r: r.relevance_score, reverse=True)
            return results[:limit]

    def _calculate_relevance(self, query: str, entry: MemoryEntry) -> float:
        """Calculate relevance score for a memory entry."""
        score = 0.0

        # Content match
        if query in entry.content.lower():
            score += 0.6

        # Category match
        if query in entry.category.value.lower():
            score += 0.2

        # Metadata match
        for value in entry.metadata.values():
            if isinstance(value, str) and query in value.lower():
                score += 0.1
                break

        # Priority boost
        priority_boost = {
            MemoryPriority.CRITICAL: 0.3,
            MemoryPriority.HIGH: 0.2,
            MemoryPriority.MEDIUM: 0.1,
        }
        score += priority_boost.get(entry.priority, 0.0)

        # Recency boost
        age_hours = (time.time() - entry.created_at) / 3600.0
        if age_hours < 1:
            score += 0.1

        return min(score, 1.0)

    def get_by_id(self, entry_id: str) -> Optional[MemoryEntry]:
        """Get a specific memory entry by ID."""
        with self._lock:
            for store in [self._core, self._session, self._procedural, self._episodic]:
                if entry_id in store:
                    entry = store[entry_id]
                    entry.access_count += 1
                    entry.last_accessed_at = time.time()
                    return entry
            return None

    # ------------------------------------------------------------------
    # Consolidation
    # ------------------------------------------------------------------

    def consolidate(self) -> MemoryConsolidationResult:
        """Consolidate memories across layers.

        Promotes frequently accessed session memories to episodic,
        and significant episodic memories to core. Archives expired
        and low-priority entries.

        Returns:
            MemoryConsolidationResult with consolidation statistics.
        """
        time.sleep(0.001)
        with self._lock:
            now = time.time()
            if now - self._last_consolidation_at < self.CONSOLIDATION_INTERVAL_MS / 1000.0:
                return MemoryConsolidationResult()

            self._last_consolidation_at = now
            start = time.time()
            promoted = 0
            archived = 0
            expired = 0

            # Promote session → episodic (frequently accessed)
            for entry_id, entry in list(self._session.items()):
                if entry.expires_at and entry.expires_at < now:
                    del self._session[entry_id]
                    expired += 1
                elif entry.access_count >= 5 and entry.priority in (
                    MemoryPriority.HIGH, MemoryPriority.CRITICAL,
                ):
                    entry.layer = MemoryLayer.EPISODIC
                    self._episodic[entry_id] = entry
                    del self._session[entry_id]
                    promoted += 1

            # Promote episodic → core (highly significant)
            for entry_id, entry in list(self._episodic.items()):
                if entry.access_count >= 10 and entry.priority == MemoryPriority.CRITICAL:
                    entry.layer = MemoryLayer.CORE
                    self._core[entry_id] = entry
                    del self._episodic[entry_id]
                    promoted += 1

            # Archive low-priority session entries
            for entry_id, entry in list(self._session.items()):
                if entry.priority == MemoryPriority.TRANSIENT and entry.access_count == 0:
                    del self._session[entry_id]
                    archived += 1

            duration = (time.time() - start) * 1000

            return MemoryConsolidationResult(
                entries_promoted=promoted,
                entries_archived=archived,
                entries_expired=expired,
                duration_ms=duration,
            )

    # ------------------------------------------------------------------
    # Context Assembly
    # ------------------------------------------------------------------

    def assemble_context(
        self,
        max_tokens: int = 2000,
        recent_count: int = 10,
    ) -> str:
        """Assemble memory context for prompting the agent.

        Builds a structured context string from core identity,
        recent session entries, and relevant procedural knowledge.

        Args:
            max_tokens: Approximate token limit.
            recent_count: Number of recent session entries to include.

        Returns:
            Formatted context string.
        """
        with self._lock:
            parts = []

            # Core identity
            core_entries = [
                e for e in self._core.values()
                if e.category == MemoryCategory.IDENTITY
            ]
            if core_entries:
                parts.append("## Core Identity")
                for e in core_entries[:5]:
                    parts.append(f"- {e.content}")

            # Recent session
            session_entries = sorted(
                self._session.values(),
                key=lambda e: e.created_at,
                reverse=True,
            )[:recent_count]
            if session_entries:
                parts.append("## Recent Context")
                for e in session_entries:
                    parts.append(f"- [{e.category.value}] {e.content[:200]}")

            # Active procedural knowledge
            proc_entries = [
                e for e in self._procedural.values()
                if e.access_count > 0
            ]
            if proc_entries:
                parts.append("## Active Skills")
                for e in sorted(proc_entries, key=lambda x: x.access_count, reverse=True)[:5]:
                    parts.append(f"- {e.content[:150]}")

            context = "\n\n".join(parts)
            # Rough token estimation (4 chars ≈ 1 token)
            estimated_tokens = len(context) // 4
            if estimated_tokens > max_tokens:
                # Truncate to approximate token limit
                context = context[:max_tokens * 4]

            return context

    # ------------------------------------------------------------------
    # Query API
    # ------------------------------------------------------------------

    def get_memory_stats(self) -> Dict[str, Any]:
        """Get comprehensive memory statistics."""
        with self._lock:
            return {
                "total_stored": self._total_stored,
                "total_retrieved": self._total_retrieved,
                "core_entries": len(self._core),
                "session_entries": len(self._session),
                "procedural_entries": len(self._procedural),
                "episodic_entries": len(self._episodic),
                "last_consolidation_at": self._last_consolidation_at,
            }

    def clear_session(self) -> int:
        """Clear all session memory entries."""
        with self._lock:
            count = len(self._session)
            self._session.clear()
            return count

    def clear_all(self) -> Dict[str, int]:
        """Clear all memory layers."""
        with self._lock:
            counts = {
                "core": len(self._core),
                "session": len(self._session),
                "procedural": len(self._procedural),
                "episodic": len(self._episodic),
            }
            self._core.clear()
            self._session.clear()
            self._procedural.clear()
            self._episodic.clear()
            return counts


# ---------------------------------------------------------------------------
# Singleton Accessor
# ---------------------------------------------------------------------------

def get_layered_memory_engine() -> LayeredMemoryEngine:
    """Get the singleton LayeredMemoryEngine instance."""
    return LayeredMemoryEngine.get_instance()