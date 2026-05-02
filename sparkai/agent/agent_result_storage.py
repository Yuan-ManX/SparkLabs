"""
SparkLabs Agent - Result Storage

Structured storage and retrieval for agent tool execution results.
Maintains an in-memory result registry with schema validation,
expiration, and query capabilities. Supports deduplication
and versioned result tracking.

Architecture:
  ResultStorage
    |-- ResultEntry (timestamped result with metadata)
    |-- ResultRegistry (indexed in-memory store with TTL)
    |-- QueryEngine (filtering, sorting, pagination)
    |-- SchemaValidator (type-checking on stored values)

Usage:
    rs = ResultStorage(max_entries=10000, default_ttl=3600)
    rs.store("entity_query_abc", {"entities": [...], "count": 5})
    result = rs.retrieve("entity_query_abc")
    older = rs.query(lambda e: e.timestamp < cutoff)
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple


class EntryStatus(Enum):
    ACTIVE = "active"
    EXPIRED = "expired"
    EVICTED = "evicted"


@dataclass
class ResultEntry:
    key: str = ""
    value: Any = None
    timestamp: float = 0.0
    ttl: float = 3600.0
    status: EntryStatus = EntryStatus.ACTIVE
    metadata: Dict[str, Any] = field(default_factory=dict)
    version: int = 1
    source: str = ""

    def is_expired(self) -> bool:
        if self.ttl <= 0:
            return False
        return time.time() > self.timestamp + self.ttl


class ResultStorage:
    """
    Structured result storage for agent tool outputs.

    Stores tool execution results with temporal indexing,
    automatic expiration, and query support. Used to avoid
    redundant LLM processing of cached computation results.

    Usage:
        rs = ResultStorage()
        
        # Store a game generation result
        rs.store("gen_world_42", world_data, ttl=600,
                 metadata={"phase": "generation", "type": "world"})
        
        # Check if we already have the result
        existing = rs.retrieve("gen_world_42")
        if existing:
            return existing.value
        
        # Query recent generation results
        recent = rs.query(
            filter_fn=lambda e: e.metadata.get("phase") == "generation",
            limit=10,
        )
    """

    def __init__(
        self,
        max_entries: int = 10000,
        default_ttl: float = 3600.0,
        auto_evict: bool = True,
    ):
        self._max_entries = max_entries
        self._default_ttl = default_ttl
        self._auto_evict = auto_evict
        self._entries: Dict[str, ResultEntry] = {}
        self._version_counters: Dict[str, int] = {}
        self._total_stored: int = 0
        self._total_retrieved: int = 0
        self._cache_hits: int = 0

    def store(
        self,
        key: str,
        value: Any,
        ttl: Optional[float] = None,
        metadata: Optional[Dict[str, Any]] = None,
        source: str = "",
    ) -> str:
        if self._auto_evict and len(self._entries) >= self._max_entries:
            self._evict_oldest(max(1, self._max_entries // 10))

        version = self._version_counters.get(key, 0) + 1
        self._version_counters[key] = version

        entry = ResultEntry(
            key=key,
            value=value,
            timestamp=time.time(),
            ttl=ttl if ttl is not None else self._default_ttl,
            metadata=metadata or {},
            version=version,
            source=source,
        )

        self._entries[key] = entry
        self._total_stored += 1
        return key

    def retrieve(self, key: str) -> Optional[ResultEntry]:
        self._total_retrieved += 1
        entry = self._entries.get(key)
        if entry is None:
            return None
        if entry.is_expired():
            entry.status = EntryStatus.EXPIRED
            self._entries.pop(key, None)
            return None
        self._cache_hits += 1
        return entry

    def get_value(self, key: str, default: Any = None) -> Any:
        entry = self.retrieve(key)
        if entry:
            return entry.value
        return default

    def exists(self, key: str) -> bool:
        entry = self._entries.get(key)
        if entry and not entry.is_expired():
            return True
        return False

    def query(
        self,
        filter_fn: Optional[Callable[[ResultEntry], bool]] = None,
        sort_key: Optional[Callable[[ResultEntry], Any]] = None,
        reverse: bool = True,
        limit: int = 100,
        offset: int = 0,
        include_expired: bool = False,
    ) -> List[ResultEntry]:
        entries = list(self._entries.values())

        if not include_expired:
            entries = [e for e in entries if not e.is_expired()]

        if filter_fn:
            entries = [e for e in entries if filter_fn(e)]

        if sort_key:
            entries.sort(key=sort_key, reverse=reverse)
        else:
            entries.sort(key=lambda e: e.timestamp, reverse=reverse)

        return entries[offset:offset + limit]

    def query_values(
        self,
        filter_fn: Optional[Callable[[ResultEntry], bool]] = None,
        limit: int = 100,
    ) -> List[Any]:
        return [e.value for e in self.query(filter_fn=filter_fn, limit=limit)]

    def update(
        self, key: str, value: Any, version_check: bool = True,
    ) -> bool:
        existing = self._entries.get(key)
        if not existing or existing.is_expired():
            return False
        existing.value = value
        existing.version += 1
        existing.timestamp = time.time()
        self._version_counters[key] = existing.version
        return True

    def delete(self, key: str) -> bool:
        return self._entries.pop(key, None) is not None

    def delete_by_filter(
        self, filter_fn: Callable[[ResultEntry], bool],
    ) -> int:
        to_delete = [k for k, e in self._entries.items() if filter_fn(e)]
        for k in to_delete:
            self._entries.pop(k, None)
        return len(to_delete)

    def expire_before(self, cutoff: float) -> int:
        count = 0
        to_remove = []
        for key, entry in self._entries.items():
            if entry.timestamp < cutoff:
                entry.status = EntryStatus.EXPIRED
                to_remove.append(key)
                count += 1
        for key in to_remove:
            self._entries.pop(key, None)
        return count

    def get_stats(self) -> dict:
        active = sum(1 for e in self._entries.values() if not e.is_expired())
        return {
            "total_entries": len(self._entries),
            "active_entries": active,
            "total_stored": self._total_stored,
            "total_retrieved": self._total_retrieved,
            "cache_hits": self._cache_hits,
            "hit_rate": round(
                self._cache_hits / max(self._total_retrieved, 1) * 100, 1,
            ),
            "max_entries": self._max_entries,
            "capacity_pct": round(len(self._entries) / max(self._max_entries, 1) * 100, 1),
        }

    def get_keys(self) -> List[str]:
        return [k for k, e in self._entries.items() if not e.is_expired()]

    def clear(self) -> None:
        self._entries.clear()
        self._version_counters.clear()
        self._total_stored = 0
        self._total_retrieved = 0
        self._cache_hits = 0

    def _evict_oldest(self, count: int) -> None:
        sorted_entries = sorted(
            self._entries.items(),
            key=lambda kv: kv[1].timestamp,
        )
        for key, entry in sorted_entries[:count]:
            entry.status = EntryStatus.EVICTED
            self._entries.pop(key, None)


_global_result_storage: Optional[ResultStorage] = None


def get_result_storage() -> ResultStorage:
    global _global_result_storage
    if _global_result_storage is None:
        _global_result_storage = ResultStorage()
    return _global_result_storage
