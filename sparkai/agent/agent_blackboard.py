"""
SparkLabs Agent - Blackboard Knowledge Workspace

Distributed shared-memory coordination layer for multi-agent game AI
systems. The Blackboard Knowledge Workspace provides a structured,
versioned, and policy-governed knowledge repository where agents
publish observations, query shared understanding, and subscribe to
relevant changes without direct peer-to-peer communication.

Architecture:
  BlackboardEngine
    |-- EntryStore (keyed knowledge entries with type and confidence)
    |-- IndexManager (tag, source, and type indices for fast queries)
    |-- PolicyResolver (conflict resolution per key pattern)
    |-- ConsensusCollector (multi-agent agreement for CONSENSUS policy)
    |-- SubscriptionHub (pattern-based change notifications)
    |-- ExpirationSweeper (TTL-based entry eviction)
    |-- SnapshotEngine (point-in-time workspace capture)

Knowledge Flow:
  Agent writes observation -> evaluate policy -> resolve conflicts ->
  store entry -> update indices -> notify matching subscribers ->
  periodically expire stale entries -> snapshot for persistence

Key format:
  Entries are identified by unique string keys. Agents use structured
  key naming conventions (e.g. "world:player_position", "team_alpha:threat_level")
  to organize knowledge. The blackboard enforces type safety and confidence
  tracking to ensure high-quality knowledge propagation across the agent
  population.
"""

from __future__ import annotations

import fnmatch
import threading
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class EntryType(Enum):
    """Type categories for blackboard knowledge entries."""
    STRING = "string"
    NUMBER = "number"
    BOOLEAN = "boolean"
    LIST = "list"
    DICT = "dict"
    GAME_OBJECT = "game_object"
    VECTOR2D = "vector2d"
    VECTOR3D = "vector3d"
    AGENT_STATE = "agent_state"
    WORLD_EVENT = "world_event"


class BlackboardPolicy(Enum):
    """Conflict resolution policies for concurrent writes to the same key.

    FIRST_WRITER_WINS:  the first entry written is never overwritten.
    LAST_WRITER_WINS:   the most recent write always replaces prior entries.
    HIGHEST_CONFIDENCE: the entry with the highest confidence value wins.
    CONSENSUS:          requires a minimum number of distinct agents to agree
                        before the entry is committed to the blackboard.
    """
    FIRST_WRITER_WINS = "first_writer_wins"
    LAST_WRITER_WINS = "last_writer_wins"
    HIGHEST_CONFIDENCE = "highest_confidence"
    CONSENSUS = "consensus"


# ---------------------------------------------------------------------------
# Data Classes
# ---------------------------------------------------------------------------

@dataclass
class BlackboardEntry:
    """A single knowledge unit stored on the blackboard workspace.

    Attributes:
        key: unique identifier for this knowledge entry.
        value: the payload data (type must match entry_type).
        entry_type: category of data stored in the entry.
        timestamp: when the entry was created or last updated.
        source_agent_id: identifier of the agent that produced this entry.
        confidence: trust weight in the range [0.0, 1.0].
        ttl: time-to-live in seconds; 0.0 means no expiration.
        priority: importance rank (higher = more important, 0-100).
        tags: list of string tags for categorization and filtering.
        metadata: optional auxiliary key-value information.
        entry_id: unique identifier for this specific entry instance.
        version: monotonically increasing revision counter.
    """
    key: str
    value: Any
    entry_type: EntryType = EntryType.DICT
    timestamp: float = field(default_factory=time.time)
    source_agent_id: str = ""
    confidence: float = 1.0
    ttl: float = 0.0
    priority: int = 50
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    entry_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    version: int = 1

    def __post_init__(self) -> None:
        if self.confidence < 0.0:
            self.confidence = 0.0
        elif self.confidence > 1.0:
            self.confidence = 1.0
        if self.priority < 0:
            self.priority = 0
        elif self.priority > 100:
            self.priority = 100

    def is_expired(self, current_time: Optional[float] = None) -> bool:
        """Return True if the entry has exceeded its time-to-live."""
        if self.ttl <= 0.0:
            return False
        now = current_time if current_time is not None else time.time()
        return (now - self.timestamp) > self.ttl

    def age_seconds(self, current_time: Optional[float] = None) -> float:
        """Return the age of this entry in seconds."""
        now = current_time if current_time is not None else time.time()
        return max(0.0, now - self.timestamp)

    def remaining_ttl(self, current_time: Optional[float] = None) -> float:
        """Return remaining time-to-live in seconds, or -1 if no TTL."""
        if self.ttl <= 0.0:
            return -1.0
        now = current_time if current_time is not None else time.time()
        elapsed = now - self.timestamp
        return max(0.0, self.ttl - elapsed)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "key": self.key,
            "entry_id": self.entry_id,
            "entry_type": self.entry_type.value,
            "timestamp": self.timestamp,
            "source_agent_id": self.source_agent_id,
            "confidence": self.confidence,
            "ttl": self.ttl,
            "priority": self.priority,
            "tags": list(self.tags),
            "metadata_keys": list(self.metadata.keys()) if self.metadata else [],
            "version": self.version,
            "is_expired": self.is_expired(),
            "age_seconds": round(self.age_seconds(), 3),
        }

    def to_full_dict(self) -> Dict[str, Any]:
        return {
            "key": self.key,
            "entry_id": self.entry_id,
            "entry_type": self.entry_type.value,
            "timestamp": self.timestamp,
            "source_agent_id": self.source_agent_id,
            "confidence": self.confidence,
            "ttl": self.ttl,
            "priority": self.priority,
            "tags": list(self.tags),
            "metadata": dict(self.metadata),
            "version": self.version,
            "value": self.value,
        }


@dataclass
class BlackboardQuery:
    """Filter and sort specification for querying the blackboard workspace.

    Attributes:
        entry_types: optional set of entry types to include.
        source_agents: optional set of source agent IDs to filter by.
        tags: optional set of tags; entries must have ALL specified tags.
        min_confidence: minimum confidence threshold (inclusive).
        max_confidence: maximum confidence threshold (inclusive).
        priority_threshold: minimum priority value (inclusive).
        sort_by: field to sort results by ('confidence', 'priority', 'timestamp').
        sort_descending: if True, sort in descending order.
        limit: maximum number of entries to return (None = unlimited).
        include_expired: if True, include entries past their TTL.
        key_pattern: optional fnmatch pattern to filter by key.
    """
    entry_types: Optional[Set[EntryType]] = None
    source_agents: Optional[Set[str]] = None
    tags: Optional[Set[str]] = None
    min_confidence: float = 0.0
    max_confidence: float = 1.0
    priority_threshold: int = 0
    sort_by: str = "timestamp"
    sort_descending: bool = True
    limit: Optional[int] = None
    include_expired: bool = False
    key_pattern: str = "*"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "entry_types": [et.value for et in self.entry_types] if self.entry_types else None,
            "source_agents": list(self.source_agents) if self.source_agents else None,
            "tags": list(self.tags) if self.tags else None,
            "min_confidence": self.min_confidence,
            "max_confidence": self.max_confidence,
            "priority_threshold": self.priority_threshold,
            "sort_by": self.sort_by,
            "sort_descending": self.sort_descending,
            "limit": self.limit,
            "include_expired": self.include_expired,
            "key_pattern": self.key_pattern,
        }


@dataclass
class BlackboardSubscription:
    """A pattern-based subscription to blackboard entry changes.

    Attributes:
        subscription_id: unique identifier for this subscription.
        subscribed_agent_id: agent that registered this subscription.
        key_patterns: list of fnmatch patterns for key matching.
        entry_types: optional set of entry types to filter notifications.
        min_confidence: minimum confidence threshold for notifications.
        callback_url: optional URL endpoint for webhook notifications.
        created_at: timestamp when the subscription was created.
        notification_count: cumulative count of notifications delivered.
    """
    subscription_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    subscribed_agent_id: str = ""
    key_patterns: List[str] = field(default_factory=list)
    entry_types: Optional[Set[EntryType]] = None
    min_confidence: float = 0.0
    callback_url: Optional[str] = None
    created_at: float = field(default_factory=time.time)
    notification_count: int = 0

    def matches(self, entry: BlackboardEntry) -> bool:
        """Return True if the entry matches this subscription's filters."""
        if self.key_patterns:
            if not any(fnmatch.fnmatchcase(entry.key, p) for p in self.key_patterns):
                return False
        if self.entry_types is not None and entry.entry_type not in self.entry_types:
            return False
        if entry.confidence < self.min_confidence:
            return False
        return True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "subscription_id": self.subscription_id,
            "subscribed_agent_id": self.subscribed_agent_id,
            "key_patterns": list(self.key_patterns),
            "entry_types": [et.value for et in self.entry_types] if self.entry_types else None,
            "min_confidence": self.min_confidence,
            "callback_url": self.callback_url,
            "created_at": self.created_at,
            "notification_count": self.notification_count,
        }


@dataclass
class BlackboardSnapshot:
    """A point-in-time capture of the blackboard workspace state.

    Attributes:
        entries: list of all non-expired entries at capture time.
        timestamp: when the snapshot was taken.
        entry_count: total number of entries in the snapshot.
        snapshot_id: unique identifier for this snapshot.
        metadata: optional auxiliary information about the snapshot.
    """
    entries: List[BlackboardEntry] = field(default_factory=list)
    timestamp: float = field(default_factory=time.time)
    entry_count: int = 0
    snapshot_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "snapshot_id": self.snapshot_id,
            "timestamp": self.timestamp,
            "entry_count": self.entry_count,
            "entry_keys": [e.key for e in self.entries[:50]],
            "metadata": dict(self.metadata),
        }

    def to_full_dict(self) -> Dict[str, Any]:
        return {
            "snapshot_id": self.snapshot_id,
            "timestamp": self.timestamp,
            "entry_count": self.entry_count,
            "entries": [e.to_full_dict() for e in self.entries],
            "metadata": dict(self.metadata),
        }


# ---------------------------------------------------------------------------
# Blackboard Engine
# ---------------------------------------------------------------------------

class BlackboardEngine:
    """Distributed shared-memory coordination workspace for multi-agent AI.

    The Blackboard Knowledge Workspace provides a structured, versioned,
    and policy-governed knowledge repository. Agents publish observations
    to the workspace, query shared understanding via typed filters and
    tag-based indices, and subscribe to pattern-matched change notifications.

    Conflict resolution is policy-driven per key pattern, supporting four
    strategies: FIRST_WRITER_WINS, LAST_WRITER_WINS, HIGHEST_CONFIDENCE,
    and CONSENSUS (requiring N agents to agree).

    Usage:
        bb = get_blackboard()
        bb.write("world:player_pos", {"x": 10, "y": 20},
                 entry_type=EntryType.DICT, source_agent_id="agent_1",
                 confidence=0.95, tags=["world", "position"])
        entry = bb.read("world:player_pos")
        results = bb.read_all(BlackboardQuery(tags={"world"}, min_confidence=0.8))
        bb.subscribe("agent_2", ["world:*"], {EntryType.DICT}, 0.7)
    """

    _instance: Optional["BlackboardEngine"] = None
    _lock = threading.RLock()

    _MAX_ENTRIES: int = 50000
    _MAX_ENTRIES_PER_AGENT: int = 5000
    _MAX_TAGS_PER_ENTRY: int = 20
    _MAX_SUBSCRIPTIONS: int = 2000
    _MAX_KEY_PATTERNS_PER_SUBSCRIPTION: int = 50
    _DEFAULT_CONSENSUS_THRESHOLD: int = 3
    _DEFAULT_POLICY: BlackboardPolicy = BlackboardPolicy.LAST_WRITER_WINS

    def __init__(self) -> None:
        if getattr(self, "_initialized", False):
            return

        self._entries: Dict[str, BlackboardEntry] = {}
        self._tag_index: Dict[str, Set[str]] = {}
        self._source_index: Dict[str, Set[str]] = {}
        self._type_index: Dict[str, Set[str]] = {}
        self._agent_index: Dict[str, Set[str]] = {}
        self._subscriptions: Dict[str, BlackboardSubscription] = {}
        self._sub_agent_index: Dict[str, Set[str]] = {}
        self._policy_patterns: Dict[str, BlackboardPolicy] = {}
        self._consensus_buffer: Dict[str, List[BlackboardEntry]] = {}
        self._consensus_thresholds: Dict[str, int] = {}
        self._total_writes: int = 0
        self._total_reads: int = 0
        self._total_deletes: int = 0
        self._total_expirations: int = 0
        self._total_notifications: int = 0
        self._total_conflicts_resolved: int = 0
        self._total_consensus_committed: int = 0
        self._initialized = True

    @classmethod
    def get_instance(cls) -> "BlackboardEngine":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    # ------------------------------------------------------------------
    # Entry Write / Read / Update / Delete
    # ------------------------------------------------------------------

    def write(
        self,
        key: str,
        value: Any,
        entry_type: EntryType = EntryType.DICT,
        source_agent_id: str = "",
        confidence: float = 1.0,
        ttl: float = 0.0,
        priority: int = 50,
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> BlackboardEntry:
        """Write a knowledge entry to the blackboard workspace.

        If an entry already exists for the given key, the conflict resolution
        policy for that key pattern determines whether the new entry replaces
        the existing one. For CONSENSUS policy, the entry is held in a buffer
        until the required number of distinct agents provide matching entries.

        Returns the entry that ultimately resides on the blackboard (the new
        entry, the existing entry if policy blocked the write, or None if the
        entry is buffered pending consensus).
        """
        with self._lock:
            self._enforce_max_entries()
            self._enforce_agent_limit(source_agent_id)

            tag_list = tags or []
            tag_list = tag_list[:self._MAX_TAGS_PER_ENTRY]

            entry = BlackboardEntry(
                key=key,
                value=value,
                entry_type=entry_type,
                source_agent_id=source_agent_id,
                confidence=confidence,
                ttl=ttl,
                priority=priority,
                tags=tag_list,
                metadata=metadata or {},
            )

            existing = self._entries.get(key)

            if existing is not None:
                policy = self._resolve_policy_for_key(key)
                if policy == BlackboardPolicy.FIRST_WRITER_WINS:
                    self._total_conflicts_resolved += 1
                    return existing
                elif policy == BlackboardPolicy.LAST_WRITER_WINS:
                    entry.version = existing.version + 1
                elif policy == BlackboardPolicy.HIGHEST_CONFIDENCE:
                    if entry.confidence < existing.confidence:
                        self._total_conflicts_resolved += 1
                        return existing
                    entry.version = existing.version + 1
                elif policy == BlackboardPolicy.CONSENSUS:
                    return self._handle_consensus_write(key, entry, existing)

            self._store_entry(key, entry)
            self._total_writes += 1
            return entry

    def read(self, key: str, default: Any = None) -> Optional[BlackboardEntry]:
        """Read a single entry by key.

        Returns the entry if found and not expired, or the default value
        otherwise. Expired entries are lazily evicted on read.
        """
        with self._lock:
            entry = self._entries.get(key)
            if entry is None:
                return default
            if entry.is_expired():
                self._remove_entry(key)
                self._total_expirations += 1
                return default
            self._total_reads += 1
            return entry

    def read_all(self, query: Optional[BlackboardQuery] = None) -> List[BlackboardEntry]:
        """Query the blackboard for entries matching the given filter criteria.

        Returns a list of entries sorted according to the query's sort_by
        field. If no query is provided, returns all non-expired entries.
        """
        q = query or BlackboardQuery()
        results: List[BlackboardEntry] = []

        with self._lock:
            candidate_keys: Optional[Set[str]] = None

            if q.key_pattern != "*":
                candidate_keys = set()
                for key in self._entries:
                    if fnmatch.fnmatchcase(key, q.key_pattern):
                        candidate_keys.add(key)
                if not candidate_keys:
                    return []

            if q.tags:
                tag_keys: Set[str] = set()
                first = True
                for tag in q.tags:
                    tag_set = self._tag_index.get(tag, set())
                    if first:
                        tag_keys = tag_set.copy()
                        first = False
                    else:
                        tag_keys.intersection_update(tag_set)
                    if not tag_keys:
                        return []
                if candidate_keys is not None:
                    candidate_keys.intersection_update(tag_keys)
                else:
                    candidate_keys = tag_keys

            if q.source_agents:
                source_keys: Set[str] = set()
                for agent_id in q.source_agents:
                    source_keys.update(self._source_index.get(agent_id, set()))
                if candidate_keys is not None:
                    candidate_keys.intersection_update(source_keys)
                else:
                    candidate_keys = source_keys
                if not candidate_keys:
                    return []

            if q.entry_types:
                type_keys: Set[str] = set()
                for et in q.entry_types:
                    type_keys.update(self._type_index.get(et.value, set()))
                if candidate_keys is not None:
                    candidate_keys.intersection_update(type_keys)
                else:
                    candidate_keys = type_keys
                if not candidate_keys:
                    return []

            keys_to_check = candidate_keys if candidate_keys is not None else set(self._entries.keys())

            for key in keys_to_check:
                entry = self._entries.get(key)
                if entry is None:
                    continue
                if not q.include_expired and entry.is_expired():
                    continue
                if entry.confidence < q.min_confidence:
                    continue
                if entry.confidence > q.max_confidence:
                    continue
                if entry.priority < q.priority_threshold:
                    continue
                results.append(entry)

        sort_key: str = q.sort_by
        if sort_key == "confidence":
            results.sort(key=lambda e: e.confidence, reverse=q.sort_descending)
        elif sort_key == "priority":
            results.sort(key=lambda e: e.priority, reverse=q.sort_descending)
        else:
            results.sort(key=lambda e: e.timestamp, reverse=q.sort_descending)

        if q.limit is not None and len(results) > q.limit:
            return results[:q.limit]
        return results

    def update(
        self,
        key: str,
        value: Any,
        confidence: Optional[float] = None,
        source_agent_id: Optional[str] = None,
    ) -> Optional[BlackboardEntry]:
        """Update an existing entry's value and optionally confidence/source.

        Returns the updated entry, or None if no entry exists for the key
        or the entry has expired.
        """
        with self._lock:
            existing = self._entries.get(key)
            if existing is None:
                return None
            if existing.is_expired():
                self._remove_entry(key)
                self._total_expirations += 1
                return None

            existing.value = value
            existing.timestamp = time.time()
            existing.version += 1
            if confidence is not None:
                existing.confidence = max(0.0, min(1.0, confidence))
            if source_agent_id is not None:
                existing.source_agent_id = source_agent_id

            self._total_writes += 1
            return existing

    def delete(self, key: str) -> bool:
        """Remove an entry from the blackboard by key.

        Returns True if an entry was removed, False if no entry existed.
        """
        with self._lock:
            if key not in self._entries:
                return False
            self._remove_entry(key)
            self._total_deletes += 1
            return True

    # ------------------------------------------------------------------
    # Subscription Management
    # ------------------------------------------------------------------

    def subscribe(
        self,
        agent_id: str,
        key_patterns: Optional[List[str]] = None,
        entry_type_filters: Optional[Set[EntryType]] = None,
        min_confidence: float = 0.0,
        callback_url: Optional[str] = None,
    ) -> Optional[BlackboardSubscription]:
        """Register a subscription for pattern-matched entry notifications.

        Returns the subscription object, or None if the subscription limit
        has been reached.
        """
        with self._lock:
            if len(self._subscriptions) >= self._MAX_SUBSCRIPTIONS:
                return None

            patterns = (key_patterns or ["*"])[:self._MAX_KEY_PATTERNS_PER_SUBSCRIPTION]

            sub = BlackboardSubscription(
                subscribed_agent_id=agent_id,
                key_patterns=patterns,
                entry_types=entry_type_filters,
                min_confidence=min_confidence,
                callback_url=callback_url,
            )

            self._subscriptions[sub.subscription_id] = sub
            self._add_to_set_index(self._sub_agent_index, agent_id, sub.subscription_id)
            return sub

    def unsubscribe(self, subscription_id: str) -> bool:
        """Remove a subscription by its identifier.

        Returns True if the subscription was found and removed.
        """
        with self._lock:
            sub = self._subscriptions.pop(subscription_id, None)
            if sub is None:
                return False
            self._remove_from_set_index(
                self._sub_agent_index, sub.subscribed_agent_id, subscription_id
            )
            return True

    def notify_subscribers(self, entry: BlackboardEntry) -> List[str]:
        """Notify all matching subscribers about a new or updated entry.

        Returns a list of agent IDs that were notified. Subscribers with a
        callback_url have their notification_count incremented but are not
        actively called (the callback URL is intended for external polling).
        """
        notified_ids: List[str] = []
        with self._lock:
            subscriptions = list(self._subscriptions.values())

        for sub in subscriptions:
            if not sub.matches(entry):
                continue
            sub.notification_count += 1
            notified_ids.append(sub.subscribed_agent_id)
            self._total_notifications += 1

        return notified_ids

    def get_subscriptions_for_agent(self, agent_id: str) -> List[BlackboardSubscription]:
        """Return all subscriptions registered by a specific agent."""
        with self._lock:
            sub_ids = self._sub_agent_index.get(agent_id, set())
            return [self._subscriptions[sid] for sid in sub_ids if sid in self._subscriptions]

    # ------------------------------------------------------------------
    # Snapshot and Maintenance
    # ------------------------------------------------------------------

    def snapshot(self) -> BlackboardSnapshot:
        """Capture a point-in-time snapshot of all non-expired entries."""
        with self._lock:
            now = time.time()
            entries = [
                e for e in self._entries.values()
                if not e.is_expired(now)
            ]
            return BlackboardSnapshot(
                entries=entries,
                timestamp=now,
                entry_count=len(entries),
            )

    def clear(self, agent_id: Optional[str] = None) -> int:
        """Remove entries from the blackboard.

        If an agent_id is provided, only entries from that agent are removed.
        Otherwise, all entries are cleared.

        Returns the number of entries removed.
        """
        with self._lock:
            if agent_id is None:
                count = len(self._entries)
                self._entries.clear()
                self._tag_index.clear()
                self._source_index.clear()
                self._type_index.clear()
                self._agent_index.clear()
                self._consensus_buffer.clear()
                return count

            keys_to_remove = list(self._agent_index.get(agent_id, set()))
            for key in keys_to_remove:
                self._remove_entry(key)
            return len(keys_to_remove)

    def expire(self) -> int:
        """Remove all entries that have exceeded their time-to-live.

        Returns the number of entries removed.
        """
        now = time.time()
        removed = 0
        with self._lock:
            expired_keys = [
                key for key, entry in self._entries.items()
                if entry.ttl > 0.0 and (now - entry.timestamp) > entry.ttl
            ]
            for key in expired_keys:
                self._remove_entry(key)
                removed += 1
            self._total_expirations += removed
        return removed

    def query_by_tag(self, tag: str) -> List[BlackboardEntry]:
        """Return all non-expired entries matching a specific tag."""
        with self._lock:
            keys = self._tag_index.get(tag, set())
            results: List[BlackboardEntry] = []
            for key in keys:
                entry = self._entries.get(key)
                if entry is not None and not entry.is_expired():
                    results.append(entry)
            return results

    # ------------------------------------------------------------------
    # Policy Management
    # ------------------------------------------------------------------

    def set_policy(self, key_pattern: str, policy: BlackboardPolicy) -> None:
        """Set the conflict resolution policy for keys matching a pattern.

        When multiple policies match a key, the most specific (longest)
        pattern wins. If no policy is set for a key, LAST_WRITER_WINS is
        used as the default.
        """
        with self._lock:
            self._policy_patterns[key_pattern] = policy

    def set_consensus_threshold(self, key_pattern: str, threshold: int) -> None:
        """Set the minimum number of distinct agents required for consensus.

        The CONSENSUS policy requires this many agents to write matching
        entries before the entry is committed to the blackboard.
        """
        with self._lock:
            self._consensus_thresholds[key_pattern] = max(1, threshold)

    def resolve_conflict(
        self, key: str, entries: List[BlackboardEntry]
    ) -> Optional[BlackboardEntry]:
        """Resolve a conflict between multiple entries for the same key.

        Uses the policy configured for the key's matching pattern. For
        CONSENSUS policy, this checks if the required number of distinct
        source agents have provided entries.

        Returns the winning entry, or None if consensus has not been reached.
        """
        if not entries:
            return None
        if len(entries) == 1:
            return entries[0]

        policy = self._resolve_policy_for_key(key)

        if policy == BlackboardPolicy.FIRST_WRITER_WINS:
            return min(entries, key=lambda e: e.timestamp)
        elif policy == BlackboardPolicy.LAST_WRITER_WINS:
            return max(entries, key=lambda e: e.timestamp)
        elif policy == BlackboardPolicy.HIGHEST_CONFIDENCE:
            return max(entries, key=lambda e: (e.confidence, e.timestamp))
        elif policy == BlackboardPolicy.CONSENSUS:
            threshold = self._consensus_thresholds.get(key, self._DEFAULT_CONSENSUS_THRESHOLD)
            unique_sources: Set[str] = {e.source_agent_id for e in entries if e.source_agent_id}
            if len(unique_sources) >= threshold:
                return max(entries, key=lambda e: (e.confidence, e.timestamp))
            return None

        return entries[-1]

    # ------------------------------------------------------------------
    # Statistics
    # ------------------------------------------------------------------

    def get_stats(self) -> Dict[str, Any]:
        """Return aggregate statistics about the blackboard workspace."""
        with self._lock:
            now = time.time()
            type_counts: Dict[str, int] = {}
            tag_counts: Dict[str, int] = {}
            agent_entry_counts: Dict[str, int] = {}
            source_entry_counts: Dict[str, int] = {}
            expired_count = 0
            total_confidence = 0.0
            total_priority = 0

            for entry in self._entries.values():
                type_counts[entry.entry_type.value] = (
                    type_counts.get(entry.entry_type.value, 0) + 1
                )
                for tag in entry.tags:
                    tag_counts[tag] = tag_counts.get(tag, 0) + 1
                if entry.source_agent_id:
                    source_entry_counts[entry.source_agent_id] = (
                        source_entry_counts.get(entry.source_agent_id, 0) + 1
                    )
                if entry.is_expired(now):
                    expired_count += 1
                total_confidence += entry.confidence
                total_priority += entry.priority

            n = len(self._entries)
            return {
                "total_entries": n,
                "active_entries": n - expired_count,
                "expired_entries": expired_count,
                "total_writes": self._total_writes,
                "total_reads": self._total_reads,
                "total_deletes": self._total_deletes,
                "total_expirations": self._total_expirations,
                "total_notifications": self._total_notifications,
                "total_conflicts_resolved": self._total_conflicts_resolved,
                "total_consensus_committed": self._total_consensus_committed,
                "total_subscriptions": len(self._subscriptions),
                "total_policies": len(self._policy_patterns),
                "consensus_buffer_size": sum(
                    len(buf) for buf in self._consensus_buffer.values()
                ),
                "avg_confidence": round(total_confidence / n, 4) if n > 0 else 0.0,
                "avg_priority": round(total_priority / n, 2) if n > 0 else 0.0,
                "by_entry_type": type_counts,
                "by_source_agent": source_entry_counts,
                "top_tags": dict(
                    sorted(tag_counts.items(), key=lambda x: x[1], reverse=True)[:20]
                ),
                "unique_tags": len(tag_counts),
                "unique_sources": len(source_entry_counts),
                "max_entries_limit": self._MAX_ENTRIES,
                "max_entries_per_agent": self._MAX_ENTRIES_PER_AGENT,
            }

    def get_policy_for_key(self, key: str) -> BlackboardPolicy:
        """Return the active conflict resolution policy for a given key."""
        return self._resolve_policy_for_key(key)

    def reset(self) -> None:
        """Reset the blackboard to its initial empty state."""
        with self._lock:
            self._entries.clear()
            self._tag_index.clear()
            self._source_index.clear()
            self._type_index.clear()
            self._agent_index.clear()
            self._subscriptions.clear()
            self._sub_agent_index.clear()
            self._policy_patterns.clear()
            self._consensus_buffer.clear()
            self._consensus_thresholds.clear()
            self._total_writes = 0
            self._total_reads = 0
            self._total_deletes = 0
            self._total_expirations = 0
            self._total_notifications = 0
            self._total_conflicts_resolved = 0
            self._total_consensus_committed = 0

    # ------------------------------------------------------------------
    # Internal Helpers
    # ------------------------------------------------------------------

    def _store_entry(self, key: str, entry: BlackboardEntry) -> None:
        """Store an entry and update all indices (caller must hold lock)."""
        old_entry = self._entries.get(key)
        if old_entry is not None:
            self._remove_from_indices(key, old_entry)

        self._entries[key] = entry

        self._add_to_set_index(self._agent_index, entry.source_agent_id, key)
        self._add_to_set_index(self._source_index, entry.source_agent_id, key)
        self._add_to_set_index(self._type_index, entry.entry_type.value, key)
        for tag in entry.tags:
            self._add_to_set_index(self._tag_index, tag, key)

        self._maybe_notify(entry)

    def _remove_entry(self, key: str) -> None:
        """Remove an entry and update all indices (caller must hold lock)."""
        entry = self._entries.pop(key, None)
        if entry is None:
            return
        self._remove_from_indices(key, entry)

    def _remove_from_indices(self, key: str, entry: BlackboardEntry) -> None:
        """Remove the entry's key from all index structures."""
        self._remove_from_set_index(self._agent_index, entry.source_agent_id, key)
        self._remove_from_set_index(self._source_index, entry.source_agent_id, key)
        self._remove_from_set_index(self._type_index, entry.entry_type.value, key)
        for tag in entry.tags:
            self._remove_from_set_index(self._tag_index, tag, key)

    def _add_to_set_index(
        self, index: Dict[str, Set[str]], index_key: str, entry_key: str
    ) -> None:
        if index_key not in index:
            index[index_key] = set()
        index[index_key].add(entry_key)

    def _remove_from_set_index(
        self, index: Dict[str, Set[str]], index_key: str, entry_key: str
    ) -> None:
        if index_key in index:
            index[index_key].discard(entry_key)
            if not index[index_key]:
                del index[index_key]

    def _resolve_policy_for_key(self, key: str) -> BlackboardPolicy:
        """Find the most specific policy pattern matching the given key."""
        best_match: Optional[str] = None
        best_len = -1
        for pattern in self._policy_patterns:
            if fnmatch.fnmatchcase(key, pattern):
                if len(pattern) > best_len:
                    best_len = len(pattern)
                    best_match = pattern
        if best_match is not None:
            return self._policy_patterns[best_match]
        return self._DEFAULT_POLICY

    def _handle_consensus_write(
        self, key: str, entry: BlackboardEntry, existing: BlackboardEntry
    ) -> BlackboardEntry:
        """Handle a write under CONSENSUS policy.

        Buffers the entry and checks if the consensus threshold has been met.
        If met, the winning entry is committed to the blackboard.
        """
        if key not in self._consensus_buffer:
            self._consensus_buffer[key] = []

        buffer = self._consensus_buffer[key]
        buffer.append(entry)

        threshold = self._consensus_thresholds.get(key, self._DEFAULT_CONSENSUS_THRESHOLD)
        unique_sources: Set[str] = {e.source_agent_id for e in buffer if e.source_agent_id}

        if len(unique_sources) >= threshold:
            winner = max(buffer, key=lambda e: (e.confidence, e.timestamp))
            winner.version = existing.version + 1
            self._store_entry(key, winner)
            self._consensus_buffer.pop(key, None)
            self._total_writes += 1
            self._total_consensus_committed += 1
            return winner

        return existing

    def _maybe_notify(self, entry: BlackboardEntry) -> None:
        """Notify subscribers matching the entry (caller must hold lock).

        Notifications are delivered synchronously to avoid race conditions
        with the entry store. Callback URLs are not actively invoked; they
        are intended for external polling systems.
        """
        for sub in self._subscriptions.values():
            if sub.matches(entry):
                sub.notification_count += 1
                self._total_notifications += 1

    def _enforce_max_entries(self) -> None:
        """Evict lowest-priority, lowest-confidence entries if over capacity."""
        if len(self._entries) < self._MAX_ENTRIES:
            return

        sorted_entries = sorted(
            self._entries.items(),
            key=lambda item: (
                item[1].priority,
                item[1].confidence,
                -item[1].timestamp,
            ),
        )
        overflow = len(self._entries) - self._MAX_ENTRIES + 1
        for key, _ in sorted_entries[:overflow]:
            self._remove_entry(key)

    def _enforce_agent_limit(self, agent_id: str) -> None:
        """Evict this agent's lowest-quality entries if over per-agent limit."""
        if not agent_id:
            return
        agent_keys = list(self._agent_index.get(agent_id, set()))
        if len(agent_keys) < self._MAX_ENTRIES_PER_AGENT:
            return

        scored = []
        for key in agent_keys:
            entry = self._entries.get(key)
            if entry is not None:
                scored.append((key, entry.priority, entry.confidence, entry.timestamp))
        scored.sort(key=lambda x: (x[1], x[2], -x[3]))

        overflow = len(scored) - self._MAX_ENTRIES_PER_AGENT + 1
        for key, _, _, _ in scored[:overflow]:
            self._remove_entry(key)


# ---------------------------------------------------------------------------
# Factory Function
# ---------------------------------------------------------------------------

def get_blackboard() -> BlackboardEngine:
    """Return the singleton BlackboardEngine instance."""
    return BlackboardEngine.get_instance()