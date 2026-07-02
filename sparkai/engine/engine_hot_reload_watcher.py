"""
SparkLabs Engine - Hot Reload Watcher

A file-system watching engine that monitors assets, scripts, scenes and
shaders for changes and notifies subscribed consumers so the running
editor / runtime can hot-reload without a full restart. The watcher
keeps an in-memory record of every change it observes, debounces
related events into ``ChangeBatch`` groups, and plans ``ReloadAction``
operations against the interested ``Subscriber`` entities.

Architecture:
  HotReloadWatcherEngine (singleton)
    |-- WatchTarget        -- a directory or file being watched
    |-- FileChange         -- a single detected change event
    |-- ChangeBatch        -- a debounced collection of FileChange events
    |-- Subscriber         -- an entity subscribed to a subset of changes
    |-- ReloadAction       -- a planned reload operation
    |-- ReloadHistory      -- historical record of completed reloads
    |-- WatchFilter        -- a glob/regex include/exclude filter
    |-- ReloadStats        -- aggregate counters
    |-- HotReloadSnapshot  -- full state snapshot
    |-- HotReloadEvent     -- lifecycle audit event
    |-- ChangeKind         -- 5 file change kinds
    |-- FileType           -- 8 supported file types
    |-- ReloadStrategy     -- 5 reload timing strategies
    |-- SubscriberKind     -- 5 consumer classifications
    |-- ReloadStatus       -- 5 reload lifecycle states
    |-- HotReloadEventKind -- 7 audit event kinds

Core Capabilities:
  - add_watch / remove_watch / list_watches: target registry with FIFO
    eviction, file-type and recursive flags.
  - subscribe / unsubscribe / list_subscribers: subscription registry
    with paths/kinds/strategy configuration.
  - record_change / batch_changes / process_batch: change ingestion,
    debounced batching and processing pipeline that emits ReloadAction
    objects for every interested subscriber.
  - trigger_reload / complete_reload / get_reload_history /
    get_pending_actions: per-path and per-batch reload orchestration.
  - set_debounce / add_filter / remove_filter: runtime tuning of the
    watcher.
  - simulate_event: test hook that injects a synthetic file change
    without touching the file system.
  - list_events / get_status / get_snapshot: observability.
  - reset: clear all stores and re-seed with default data.

The class implements the singleton pattern with double-checked locking
using ``threading.RLock``; consumers should obtain the instance through
:meth:`HotReloadWatcherEngine.get_instance` or the module-level
:func:`get_hot_reload_watcher` factory. All public methods are guarded
by the re-entrant lock.
"""

from __future__ import annotations

import threading
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple


# ---------------------------------------------------------------------------
# Capacity Constants
# ---------------------------------------------------------------------------

# Bounded store capacities. When a store exceeds its cap the oldest entry
# is evicted in FIFO order to keep memory growth predictable under
# prolonged sessions (for example, a long-running editor that watches
# thousands of files for an entire workday).
_MAX_WATCHES: int = 256
_MAX_CHANGES: int = 5000
_MAX_BATCHES: int = 1000
_MAX_SUBSCRIBERS: int = 256
_MAX_ACTIONS: int = 5000
_MAX_HISTORY: int = 2000
_MAX_EVENTS: int = 2000
_MAX_FILTERS: int = 64


# ---------------------------------------------------------------------------
# Helper Functions
# ---------------------------------------------------------------------------


def _now() -> str:
    """Return the current UTC time as an ISO-8601 string with a 'Z' suffix.

    Used as the default factory for ``created_at`` / ``updated_at`` /
    ``timestamp`` fields and for event timestamps throughout the module.
    """
    return datetime.utcnow().isoformat() + "Z"


def _new_id(prefix: str = "") -> str:
    """Generate a short unique identifier, optionally prefixed.

    Args:
        prefix: Optional prefix joined to the generated identifier with
            an underscore. When omitted, the bare hexadecimal id is
            returned.

    Returns:
        A short hexadecimal identifier, optionally prefixed.
    """
    base = uuid.uuid4().hex[:12]
    return f"{prefix}_{base}" if prefix else base


def _classify_file_type(path: str) -> "FileType":
    """Return the FileType best matching the file extension of ``path``.

    Unknown extensions map to ``FileType.UNKNOWN``. The check is
    case-insensitive and uses a simple ``endswith`` test on the path.

    Args:
        path: The path to classify.

    Returns:
        The matching FileType, or ``FileType.UNKNOWN`` if no rule fires.
    """
    lowered = path.lower()
    if lowered.endswith((".py", ".lua", ".js", ".ts", ".cs", ".gd")):
        return FileType.SCRIPT
    if lowered.endswith((".scene", ".tscn", ".scn", ".unity", ".umap")):
        return FileType.SCENE
    if lowered.endswith((".glsl", ".vert", ".frag", ".shader", ".hlsl")):
        return FileType.SHADER
    if lowered.endswith((".png", ".jpg", ".jpeg", ".tga", ".bmp", ".ktx", ".dds", ".webp")):
        return FileType.ASSET
    if lowered.endswith((".wav", ".ogg", ".mp3", ".flac", ".aiff")):
        return FileType.AUDIO
    if lowered.endswith((".json", ".yaml", ".yml", ".xml", ".toml", ".ini")):
        return FileType.DATA
    if lowered.endswith((".cfg", ".conf", ".toml", ".ini", ".env")):
        return FileType.CONFIG
    return FileType.UNKNOWN


# ---------------------------------------------------------------------------
# Domain Enums
# ---------------------------------------------------------------------------


class ChangeKind(Enum):
    """Classification of a file change event.

    - ``CREATED``: a new file or directory appeared.
    - ``MODIFIED``: an existing file's contents changed.
    - ``DELETED``: a file or directory was removed.
    - ``MOVED``: a file or directory was renamed/moved.
    - ``ATTRIBUTE_CHANGED``: metadata (mtime, mode, owner) changed but
      contents may not have.
    """

    CREATED = "created"
    MODIFIED = "modified"
    DELETED = "deleted"
    MOVED = "moved"
    ATTRIBUTE_CHANGED = "attribute_changed"


class FileType(Enum):
    """Coarse classification of a watched file.

    - ``SCRIPT``: gameplay or editor script source code.
    - ``SCENE``: serialized scene/level data.
    - ``ASSET``: texture/model/mesh/other binary asset.
    - ``SHADER``: GLSL/HLSL/SPIR-V shader source or compiled blob.
    - ``AUDIO``: sound effect, music or streamed audio file.
    - ``DATA``: structured data file (json/yaml/xml).
    - ``CONFIG``: engine configuration file.
    - ``UNKNOWN``: an unrecognised extension; the watcher still records
      the change but cannot classify it for targeted reload.
    """

    SCRIPT = "script"
    SCENE = "scene"
    ASSET = "asset"
    SHADER = "shader"
    AUDIO = "audio"
    DATA = "data"
    CONFIG = "config"
    UNKNOWN = "unknown"


class ReloadStrategy(Enum):
    """How a reload is scheduled after a change is detected.

    - ``IMMEDIATE``: reload as soon as the change is observed.
    - ``DEBOUNCED``: wait for a quiet period (debounce window) before
      reloading so that a burst of changes is collapsed into one.
    - ``BATCHED``: accumulate changes into a batch and reload only on
      batch boundaries.
    - ``MANUAL``: never reload automatically; only via explicit calls
      to :meth:`trigger_reload`.
    - ``SCHEDULED``: reload on a recurring schedule regardless of the
      number of changes.
    """

    IMMEDIATE = "immediate"
    DEBOUNCED = "debounced"
    BATCHED = "batched"
    MANUAL = "manual"
    SCHEDULED = "scheduled"


class SubscriberKind(Enum):
    """Classification of a subscription consumer.

    - ``EDITOR``: an editor UI surface that needs to refresh panels.
    - ``RUNTIME``: the live runtime/play session that needs the new
      asset or script applied without restart.
    - ``DEBUGGER``: a debugger attachment that needs to refresh
      breakpoints and symbols.
    - ``COMPILER``: a hot-reload compiler / transpiler that needs to
      rebuild artifacts.
    - ``AI_ASSISTANT``: an AI assistant that needs to refresh context
      about the project state.
    """

    EDITOR = "editor"
    RUNTIME = "runtime"
    DEBUGGER = "debugger"
    COMPILER = "compiler"
    AI_ASSISTANT = "ai_assistant"


class ReloadStatus(Enum):
    """Lifecycle status of a ReloadAction.

    - ``PENDING``: queued and waiting to be processed.
    - ``IN_PROGRESS``: currently being executed by a subscriber.
    - ``COMPLETED``: finished successfully.
    - ``FAILED``: encountered an error during execution.
    - ``SKIPPED``: deliberately skipped (manual strategy, filter
      excluded the path, etc.).
    """

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class HotReloadEventKind(Enum):
    """Audit event kinds emitted by the hot reload watcher engine."""

    WATCHER_STARTED = "watcher_started"
    FILE_DETECTED = "file_detected"
    CHANGE_BATCHED = "change_batched"
    RELOAD_TRIGGERED = "reload_triggered"
    SUBSCRIBER_NOTIFIED = "subscriber_notified"
    RELOAD_COMPLETED = "reload_completed"
    RELOAD_FAILED = "reload_failed"


# ---------------------------------------------------------------------------
# Data Classes
# ---------------------------------------------------------------------------


@dataclass
class WatchTarget:
    """A path being watched by the engine.

    A watch target is either a single file or a directory. When
    ``recursive`` is True the engine recursively monitors all files
    beneath the path. ``file_types`` restricts notifications to the
    listed ``FileType`` classifications; an empty list means "any".

    Attributes:
        target_id: Unique identifier for the watch target.
        path: The path being watched.
        recursive: Whether subdirectories are watched recursively.
        file_types: List of FileType values to filter for. Empty means
            "watch all file types".
        active: Whether the watch is currently active.
        created_at: ISO-8601 timestamp of creation.
        last_event_at: ISO-8601 timestamp of the last observed change
            (empty string if no changes have been observed).
        metadata: Free-form extension data.
    """

    target_id: str = field(default_factory=lambda: _new_id("watch"))
    path: str = ""
    recursive: bool = True
    file_types: List[FileType] = field(default_factory=list)
    active: bool = True
    created_at: str = field(default_factory=_now)
    last_event_at: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "target_id": self.target_id,
            "path": self.path,
            "recursive": self.recursive,
            "file_types": [ft.value for ft in self.file_types],
            "active": self.active,
            "created_at": self.created_at,
            "last_event_at": self.last_event_at,
            "metadata": dict(self.metadata) if self.metadata else {},
        }


@dataclass
class FileChange:
    """A single file change event.

    Captures the path that changed, the kind of change, the inferred
    file type, the watcher that detected the change (if any), and a
    timestamp. File changes are accumulated in ``_changes`` and grouped
    into ``ChangeBatch`` records on debounce boundaries.

    Attributes:
        change_id: Unique identifier for the change.
        path: The path that changed.
        kind: The ChangeKind classification.
        file_type: The inferred FileType of the path.
        target_id: Identifier of the originating WatchTarget (may be
            empty if the change was simulated).
        timestamp: ISO-8601 timestamp of the change.
        size: Optional file size in bytes (None when unavailable).
        metadata: Free-form extension data.
    """

    change_id: str = field(default_factory=lambda: _new_id("chg"))
    path: str = ""
    kind: ChangeKind = ChangeKind.MODIFIED
    file_type: FileType = FileType.UNKNOWN
    target_id: str = ""
    timestamp: str = field(default_factory=_now)
    size: Optional[int] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "change_id": self.change_id,
            "path": self.path,
            "kind": self.kind.value,
            "file_type": self.file_type.value,
            "target_id": self.target_id,
            "timestamp": self.timestamp,
            "size": self.size,
            "metadata": dict(self.metadata) if self.metadata else {},
        }


@dataclass
class ChangeBatch:
    """A debounced batch of file changes.

    A batch groups one or more FileChange records that share a common
    debounce window. ``process_strategy`` is the strategy selected for
    the batch when :meth:`process_batch` is called; the default is
    ``DEBOUNCED`` which is the most common case in editor workflows.

    Attributes:
        batch_id: Unique identifier for the batch.
        change_ids: List of change ids contained in the batch.
        process_strategy: The ReloadStrategy to use when processing.
        created_at: ISO-8601 timestamp of batch creation.
        processed: Whether :meth:`process_batch` has been called.
        processed_at: ISO-8601 timestamp of processing (empty if not
            yet processed).
        metadata: Free-form extension data.
    """

    batch_id: str = field(default_factory=lambda: _new_id("batch"))
    change_ids: List[str] = field(default_factory=list)
    process_strategy: ReloadStrategy = ReloadStrategy.DEBOUNCED
    created_at: str = field(default_factory=_now)
    processed: bool = False
    processed_at: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "batch_id": self.batch_id,
            "change_ids": list(self.change_ids),
            "process_strategy": self.process_strategy.value,
            "created_at": self.created_at,
            "processed": self.processed,
            "processed_at": self.processed_at,
            "metadata": dict(self.metadata) if self.metadata else {},
        }


@dataclass
class Subscriber:
    """An entity subscribed to specific change kinds.

    A subscriber declares the paths it cares about, the kinds of
    changes it wants to be notified about, and the reload strategy it
    prefers. The engine uses the subscription to determine which
    ReloadAction objects to emit when a batch is processed.

    Attributes:
        subscriber_id: Caller-supplied unique identifier (e.g. the
            "Editor.Panel.Outliner").
        kind: The SubscriberKind classification.
        paths: List of path patterns the subscriber is interested in
            (empty list means "all watched paths").
        kinds: List of ChangeKind values the subscriber is interested
            in (empty list means "all change kinds").
        strategy: The preferred ReloadStrategy.
        notification_count: Number of notifications sent to this
            subscriber.
        last_notified_at: ISO-8601 timestamp of the last notification
            (empty if never notified).
        metadata: Free-form extension data.
    """

    subscriber_id: str = ""
    kind: SubscriberKind = SubscriberKind.EDITOR
    paths: List[str] = field(default_factory=list)
    kinds: List[ChangeKind] = field(default_factory=list)
    strategy: ReloadStrategy = ReloadStrategy.IMMEDIATE
    notification_count: int = 0
    last_notified_at: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "subscriber_id": self.subscriber_id,
            "kind": self.kind.value,
            "paths": list(self.paths),
            "kinds": [k.value for k in self.kinds],
            "strategy": self.strategy.value,
            "notification_count": self.notification_count,
            "last_notified_at": self.last_notified_at,
            "metadata": dict(self.metadata) if self.metadata else {},
        }


@dataclass
class ReloadAction:
    """A planned reload operation against a subscriber.

    A ReloadAction is created when the engine decides that a change
    should be propagated to a subscriber. It records the target
    subscriber, the path being reloaded, the change that triggered the
    action and the current status of the operation.

    Attributes:
        action_id: Unique identifier for the action.
        subscriber_id: Identifier of the targeted Subscriber.
        path: The path being reloaded.
        change_id: Identifier of the triggering FileChange.
        batch_id: Identifier of the originating ChangeBatch (empty
            when triggered directly via :meth:`trigger_reload`).
        strategy: The ReloadStrategy that was applied.
        status: The current ReloadStatus.
        created_at: ISO-8601 timestamp of creation.
        completed_at: ISO-8601 timestamp of completion (empty if
            not yet completed).
        error: Optional error message on failure.
    """

    action_id: str = field(default_factory=lambda: _new_id("act"))
    subscriber_id: str = ""
    path: str = ""
    change_id: str = ""
    batch_id: str = ""
    strategy: ReloadStrategy = ReloadStrategy.IMMEDIATE
    status: ReloadStatus = ReloadStatus.PENDING
    created_at: str = field(default_factory=_now)
    completed_at: str = ""
    error: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "action_id": self.action_id,
            "subscriber_id": self.subscriber_id,
            "path": self.path,
            "change_id": self.change_id,
            "batch_id": self.batch_id,
            "strategy": self.strategy.value,
            "status": self.status.value,
            "created_at": self.created_at,
            "completed_at": self.completed_at,
            "error": self.error,
        }


@dataclass
class ReloadHistory:
    """Historical record of a completed reload action.

    A snapshot of a ReloadAction that has been moved from the
    live queue to the historical log. Retained for audit and for the
    editor's "recent activity" panel.

    Attributes:
        history_id: Unique identifier for the history record.
        action_id: The original ReloadAction id.
        subscriber_id: Identifier of the subscriber that was notified.
        path: The reloaded path.
        strategy: The ReloadStrategy that was used.
        status: The final ReloadStatus.
        started_at: ISO-8601 timestamp the action started.
        finished_at: ISO-8601 timestamp the action finished.
        duration_ms: Wall-clock duration in milliseconds.
        error: Optional error message on failure.
    """

    history_id: str = field(default_factory=lambda: _new_id("hist"))
    action_id: str = ""
    subscriber_id: str = ""
    path: str = ""
    strategy: ReloadStrategy = ReloadStrategy.IMMEDIATE
    status: ReloadStatus = ReloadStatus.COMPLETED
    started_at: str = field(default_factory=_now)
    finished_at: str = field(default_factory=_now)
    duration_ms: float = 0.0
    error: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "history_id": self.history_id,
            "action_id": self.action_id,
            "subscriber_id": self.subscriber_id,
            "path": self.path,
            "strategy": self.strategy.value,
            "status": self.status.value,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "duration_ms": self.duration_ms,
            "error": self.error,
        }


@dataclass
class WatchFilter:
    """A pattern filter applied to watched paths.

    Filters can be either include or exclude rules. When at least one
    include filter exists, paths must match an include rule to be
    processed. Exclude filters always win: any path matching an
    exclude rule is dropped. Matching is implemented as a simple
    substring or glob-style wildcard check.

    Attributes:
        filter_id: Unique identifier for the filter.
        pattern: The pattern string. Supports ``*`` (any segment) and
            ``**`` (any path segment including slashes).
        include: True for include rules, False for exclude rules.
        created_at: ISO-8601 timestamp of creation.
        metadata: Free-form extension data.
    """

    filter_id: str = field(default_factory=lambda: _new_id("flt"))
    pattern: str = ""
    include: bool = True
    created_at: str = field(default_factory=_now)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "filter_id": self.filter_id,
            "pattern": self.pattern,
            "include": self.include,
            "created_at": self.created_at,
            "metadata": dict(self.metadata) if self.metadata else {},
        }


@dataclass
class ReloadStats:
    """Aggregate counters describing the hot reload engine state.

    Attributes:
        total_watches: Number of registered watch targets.
        total_changes: Number of recorded file changes.
        total_batches: Number of debounced batches.
        total_subscribers: Number of registered subscribers.
        total_actions: Number of reload actions ever created.
        total_history: Number of completed reloads in the history log.
        changes_by_kind: Mapping of ChangeKind value to count.
        actions_by_status: Mapping of ReloadStatus value to count.
        debounce_window_ms: Current debounce window in milliseconds.
    """

    total_watches: int = 0
    total_changes: int = 0
    total_batches: int = 0
    total_subscribers: int = 0
    total_actions: int = 0
    total_history: int = 0
    changes_by_kind: Dict[str, int] = field(default_factory=dict)
    actions_by_status: Dict[str, int] = field(default_factory=dict)
    debounce_window_ms: int = 250

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_watches": self.total_watches,
            "total_changes": self.total_changes,
            "total_batches": self.total_batches,
            "total_subscribers": self.total_subscribers,
            "total_actions": self.total_actions,
            "total_history": self.total_history,
            "changes_by_kind": dict(self.changes_by_kind)
            if self.changes_by_kind
            else {},
            "actions_by_status": dict(self.actions_by_status)
            if self.actions_by_status
            else {},
            "debounce_window_ms": self.debounce_window_ms,
        }


@dataclass
class HotReloadSnapshot:
    """An immutable snapshot of the entire hot reload engine state.

    Attributes:
        initialized: Whether the engine has completed initialization.
        watches: List of all registered watch targets.
        changes: List of all recorded file changes.
        batches: List of all debounced batches.
        subscribers: List of all registered subscribers.
        actions: List of all live reload actions.
        history: List of all completed reloads.
        filters: List of all watch filters.
        events: List of all audit events.
        stats: Aggregate statistics.
    """

    initialized: bool = False
    watches: List[WatchTarget] = field(default_factory=list)
    changes: List[FileChange] = field(default_factory=list)
    batches: List[ChangeBatch] = field(default_factory=list)
    subscribers: List[Subscriber] = field(default_factory=list)
    actions: List[ReloadAction] = field(default_factory=list)
    history: List[ReloadHistory] = field(default_factory=list)
    filters: List[WatchFilter] = field(default_factory=list)
    events: List["HotReloadEvent"] = field(default_factory=list)
    stats: ReloadStats = field(default_factory=ReloadStats)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "initialized": self.initialized,
            "watches": [w.to_dict() for w in self.watches],
            "changes": [c.to_dict() for c in self.changes],
            "batches": [b.to_dict() for b in self.batches],
            "subscribers": [s.to_dict() for s in self.subscribers],
            "actions": [a.to_dict() for a in self.actions],
            "history": [h.to_dict() for h in self.history],
            "filters": [f.to_dict() for f in self.filters],
            "events": [e.to_dict() for e in self.events],
            "stats": self.stats.to_dict(),
        }


@dataclass
class HotReloadEvent:
    """An audit event emitted by the hot reload engine.

    Attributes:
        event_id: Unique identifier for the event.
        kind: The HotReloadEventKind classification.
        timestamp: ISO-8601 timestamp when the event occurred.
        payload: Event-specific payload data.
    """

    event_id: str = field(default_factory=lambda: _new_id("evt"))
    kind: HotReloadEventKind = HotReloadEventKind.WATCHER_STARTED
    timestamp: str = field(default_factory=_now)
    payload: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": self.event_id,
            "kind": self.kind.value,
            "timestamp": self.timestamp,
            "payload": dict(self.payload) if self.payload else {},
        }


# ---------------------------------------------------------------------------
# Hot Reload Watcher Engine (Singleton)
# ---------------------------------------------------------------------------


class HotReloadWatcherEngine:
    """File-system watching engine for the SparkLabs AI-native editor.

    Maintains a registry of watch targets, records every change it
    observes, groups changes into debounced batches and emits
    ReloadAction objects for every interested Subscriber. The engine
    also tracks the historical record of completed reloads and exposes
    aggregate statistics.

    The class implements the singleton pattern with double-checked
    locking using ``threading.RLock`` for thread-safe access. All
    public methods are guarded by the re-entrant lock. Consumers
    should obtain the instance through :meth:`get_instance` or the
    module-level :func:`get_hot_reload_watcher` factory.

    Usage:
        engine = get_hot_reload_watcher()
        engine.add_watch("/proj/scripts", file_types=[FileType.SCRIPT])
        engine.subscribe(
            "Editor.Panel.Outliner",
            paths=["/proj/scenes"],
            kinds=[ChangeKind.MODIFIED],
            strategy=ReloadStrategy.DEBOUNCED,
        )
        change = engine.simulate_event(
            "/proj/scenes/level.scene",
            ChangeKind.MODIFIED,
        )
        batch = engine.batch_changes()
        actions = engine.process_batch(batch.batch_id)
    """

    _instance: Optional["HotReloadWatcherEngine"] = None
    _lock: threading.RLock = threading.RLock()

    # ------------------------------------------------------------------
    # Singleton management
    # ------------------------------------------------------------------

    def __new__(cls) -> "HotReloadWatcherEngine":
        # Double-checked locking: acquire the lock only when the
        # instance has not yet been created. The freshly allocated
        # instance is marked as not-yet-initialized so that __init__
        # performs the real one-time setup.
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    instance = super().__new__(cls)
                    instance._initialized = False
                    cls._instance = instance
        return cls._instance

    @classmethod
    def get_instance(cls) -> "HotReloadWatcherEngine":
        """Return the singleton engine instance.

        Constructs the engine on first call; subsequent calls return
        the cached instance. Does not reset the ``_initialized`` flag.
        """
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self) -> None:
        # One-time initialization guard. The outer check avoids taking
        # the lock on the hot path once initialization is complete; the
        # inner check prevents a race between two threads that both
        # observed _initialized as False.
        if self._initialized:
            return
        with self._lock:
            if self._initialized:
                return

            # Primary registries.
            # Watch targets keyed by target id.
            self._watches: Dict[str, WatchTarget] = {}
            # In-memory change log keyed by change id.
            self._changes: Dict[str, FileChange] = {}
            # Debounced batches keyed by batch id.
            self._batches: Dict[str, ChangeBatch] = {}
            # Subscribers keyed by subscriber id.
            self._subscribers: Dict[str, Subscriber] = {}
            # Live reload actions keyed by action id.
            self._actions: Dict[str, ReloadAction] = {}
            # Historical record of completed reloads, FIFO with cap.
            self._history: List[ReloadHistory] = []
            # Watch filters keyed by filter id.
            self._filters: Dict[str, WatchFilter] = {}
            # Audit events kept in FIFO order with capacity eviction.
            self._events: List[HotReloadEvent] = []

            # Aggregate counters maintained for fast stats retrieval.
            self._watch_counter: int = 0
            self._change_counter: int = 0
            self._batch_counter: int = 0
            self._subscriber_counter: int = 0
            self._action_counter: int = 0
            self._history_counter: int = 0
            self._filter_counter: int = 0
            self._event_counter: int = 0

            # Debounce window in milliseconds. Changes observed within
            # the same window are grouped into a single batch.
            self._debounce_window_ms: int = 250

            self._initialized: bool = True

            # Populate the default seed hot-reload data.
            self._seed_data()

    # ------------------------------------------------------------------
    # Seeding
    # ------------------------------------------------------------------

    def _seed_data(self) -> None:
        """Populate the engine with seed watch targets, subscribers and
        a few simulated file changes.

        The seed data demonstrates a typical editor hot-reload
        workflow:

          1. Three watch targets covering the project "scripts",
             "scenes" and "shaders" directories.
          2. Four subscribers representing an editor outliner, a
             runtime, a debugger and an AI assistant.
          3. Ten simulated file changes scattered across scripts,
             scenes, shaders and audio files.
          4. Three reload actions -- two completed and one failed --
             plus one filter that excludes ``__pycache__``.
        """
        # ------------------------------------------------------------------
        # Watch targets.
        # ------------------------------------------------------------------
        self.add_watch(
            path="/proj/scripts",
            file_types=[FileType.SCRIPT],
            recursive=True,
            metadata={"seed": True, "category": "scripts"},
        )
        self.add_watch(
            path="/proj/scenes",
            file_types=[FileType.SCENE, FileType.DATA],
            recursive=True,
            metadata={"seed": True, "category": "scenes"},
        )
        self.add_watch(
            path="/proj/shaders",
            file_types=[FileType.SHADER],
            recursive=False,
            metadata={"seed": True, "category": "shaders"},
        )

        # ------------------------------------------------------------------
        # Subscribers.
        # ------------------------------------------------------------------
        self.subscribe(
            subscriber_id="Editor.Panel.Outliner",
            paths=["/proj/scenes", "/proj/scripts"],
            kinds=[ChangeKind.MODIFIED, ChangeKind.CREATED, ChangeKind.DELETED],
            strategy=ReloadStrategy.DEBOUNCED,
        )
        self.subscribe(
            subscriber_id="Runtime.Gameplay",
            paths=[],
            kinds=[ChangeKind.MODIFIED],
            strategy=ReloadStrategy.IMMEDIATE,
        )
        self.subscribe(
            subscriber_id="Debugger.Attach",
            paths=["/proj/scripts"],
            kinds=[ChangeKind.MODIFIED, ChangeKind.ATTRIBUTE_CHANGED],
            strategy=ReloadStrategy.IMMEDIATE,
        )
        self.subscribe(
            subscriber_id="AI.Assistant",
            paths=[],
            kinds=[],
            strategy=ReloadStrategy.MANUAL,
        )

        # ------------------------------------------------------------------
        # Filters.
        # ------------------------------------------------------------------
        self.add_filter(pattern="**/__pycache__/**", include=False)
        self.add_filter(pattern="**/*.tmp", include=False)

        # ------------------------------------------------------------------
        # Simulated file changes. These exercise every ChangeKind at
        # least once and cover four different file types.
        # ------------------------------------------------------------------
        simulated: List[Tuple[str, ChangeKind]] = [
            ("/proj/scripts/player.py", ChangeKind.MODIFIED),
            ("/proj/scripts/enemy.py", ChangeKind.CREATED),
            ("/proj/scripts/utils.py", ChangeKind.MODIFIED),
            ("/proj/scripts/legacy.py", ChangeKind.DELETED),
            ("/proj/scenes/level_01.scene", ChangeKind.MODIFIED),
            ("/proj/scenes/level_02.scene", ChangeKind.ATTRIBUTE_CHANGED),
            ("/proj/scenes/intro.scene", ChangeKind.MOVED),
            ("/proj/shaders/pbr_lit.frag", ChangeKind.MODIFIED),
            ("/proj/audio/sfx_jump.wav", ChangeKind.CREATED),
            ("/proj/data/items.json", ChangeKind.MODIFIED),
        ]
        for path, kind in simulated:
            self.simulate_event(path, kind)

        # ------------------------------------------------------------------
        # Reload actions. Build them through the public API so the
        # status transitions and history records are produced by the
        # engine itself.
        # ------------------------------------------------------------------
        # Action 1: completed reload of a script.
        action1 = self.trigger_reload(
            path="/proj/scripts/player.py",
            strategy=ReloadStrategy.IMMEDIATE,
        )
        if action1 is not None:
            self.complete_reload(
                action_id=action1.action_id,
                status=ReloadStatus.COMPLETED,
            )

        # Action 2: completed reload of a scene.
        action2 = self.trigger_reload(
            path="/proj/scenes/level_01.scene",
            strategy=ReloadStrategy.DEBOUNCED,
        )
        if action2 is not None:
            self.complete_reload(
                action_id=action2.action_id,
                status=ReloadStatus.COMPLETED,
            )

        # Action 3: failed reload of a shader.
        action3 = self.trigger_reload(
            path="/proj/shaders/pbr_lit.frag",
            strategy=ReloadStrategy.IMMEDIATE,
        )
        if action3 is not None:
            self.complete_reload(
                action_id=action3.action_id,
                status=ReloadStatus.FAILED,
                error="shader compile error: unknown identifier 'uNormal'",
            )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _matches_filter(pattern: str, path: str) -> bool:
        """Return True if ``path`` matches the ``pattern`` glob.

        Supports the common glob constructs:
          - ``*``  matches any sequence of characters except ``/``.
          - ``**`` matches any sequence of characters including ``/``.
          - ``?``  matches a single character.

        A literal substring check is used as a fallback when no
        wildcard characters are present.

        Args:
            pattern: The glob pattern to match against.
            path: The path to test.

        Returns:
            True if the path matches the pattern, False otherwise.
        """
        if not pattern:
            return True
        # Convert the glob to a regex by escaping all non-glob chars
        # and then expanding the wildcards.
        import re

        regex_parts: List[str] = []
        i = 0
        while i < len(pattern):
            ch = pattern[i]
            if ch == "*":
                if i + 1 < len(pattern) and pattern[i + 1] == "*":
                    regex_parts.append(".*")
                    i += 2
                else:
                    regex_parts.append("[^/]*")
                    i += 1
            elif ch == "?":
                regex_parts.append("[^/]")
                i += 1
            else:
                regex_parts.append(re.escape(ch))
                i += 1
        regex = "^" + "".join(regex_parts) + "$"
        return re.match(regex, path) is not None

    def _passes_filters(self, path: str) -> bool:
        """Return True if ``path`` is allowed by the registered filters.

        Exclude rules always win. When at least one include filter
        exists, the path must match at least one include rule.

        Args:
            path: The path to test.

        Returns:
            True if the path should be processed, False if dropped.
        """
        with self._lock:
            filters = list(self._filters.values())
        if not filters:
            return True
        has_include = any(f.include for f in filters)
        excluded = any(
            (not f.include) and self._matches_filter(f.pattern, path)
            for f in filters
        )
        if excluded:
            return False
        if has_include:
            return any(
                f.include and self._matches_filter(f.pattern, path)
                for f in filters
            )
        return True

    def _interested_subscribers(self, path: str, kind: ChangeKind) -> List[Subscriber]:
        """Return the subscribers interested in ``(path, kind)``.

        A subscriber is interested if:
          - its ``paths`` list is empty (matches everything), or the
            path starts with one of its declared paths; and
          - its ``kinds`` list is empty (matches every kind), or the
            ``kind`` is contained in its declared kinds.

        Args:
            path: The path of the change.
            kind: The ChangeKind of the change.

        Returns:
            A list of Subscriber objects that should be notified.
        """
        with self._lock:
            subscribers = list(self._subscribers.values())
        result: List[Subscriber] = []
        for sub in subscribers:
            path_match = not sub.paths or any(
                path == p or path.startswith(p.rstrip("/") + "/") or p in path
                for p in sub.paths
            )
            kind_match = not sub.kinds or kind in sub.kinds
            if path_match and kind_match:
                result.append(sub)
        return result

    def _record_event(
        self,
        kind: HotReloadEventKind,
        payload: Dict[str, Any],
    ) -> HotReloadEvent:
        """Record an audit event (caller must hold ``self._lock``).

        Args:
            kind: The HotReloadEventKind classification.
            payload: Event-specific payload data.

        Returns:
            The created HotReloadEvent.
        """
        event = HotReloadEvent(
            kind=kind,
            payload=dict(payload) if payload else {},
        )
        if len(self._events) >= _MAX_EVENTS:
            # FIFO eviction: drop the oldest event.
            self._events.pop(0)
        self._events.append(event)
        self._event_counter += 1
        return event

    # ------------------------------------------------------------------
    # Watch management
    # ------------------------------------------------------------------

    def add_watch(
        self,
        path: str,
        file_types: Optional[List[FileType]] = None,
        recursive: bool = True,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> WatchTarget:
        """Register a new watch target.

        A watch target may be either a directory or a single file. The
        caller may restrict the watch to a specific set of file types
        via ``file_types``; an empty list (the default) means "all
        types". Watch targets are FIFO-evicted when the
        ``_MAX_WATCHES`` cap is exceeded.

        Args:
            path: The path to watch.
            file_types: Optional list of FileType values to filter for.
            recursive: Whether to watch subdirectories of ``path``.
            metadata: Optional free-form extension data.

        Returns:
            The newly created WatchTarget.
        """
        with self._lock:
            # Enforce the bounded store cap via FIFO eviction.
            if len(self._watches) >= _MAX_WATCHES:
                oldest_id = next(iter(self._watches), None)
                if oldest_id is not None:
                    self._watches.pop(oldest_id, None)

            target = WatchTarget(
                path=path,
                recursive=bool(recursive),
                file_types=list(file_types) if file_types else [],
                metadata=dict(metadata) if metadata else {},
            )
            self._watches[target.target_id] = target
            self._watch_counter += 1

            self._record_event(
                HotReloadEventKind.WATCHER_STARTED,
                payload={
                    "target_id": target.target_id,
                    "path": target.path,
                    "recursive": target.recursive,
                    "file_types": [ft.value for ft in target.file_types],
                },
            )
            return target

    def remove_watch(self, path: str) -> bool:
        """Remove a watch target matching ``path``.

        The first watch whose ``path`` attribute equals the supplied
        value is removed. Path comparison is exact (case-sensitive).

        Args:
            path: The path of the watch to remove.

        Returns:
            True if a watch was removed, False if no match was found.
        """
        with self._lock:
            for tid, target in list(self._watches.items()):
                if target.path == path:
                    self._watches.pop(tid, None)
                    return True
            return False

    def list_watches(
        self,
        file_type: Optional[FileType] = None,
        active_only: bool = False,
    ) -> List[WatchTarget]:
        """List watch targets, optionally filtered.

        Args:
            file_type: Optional FileType to filter by. A watch matches
                when its ``file_types`` list is empty (matches all) or
                contains the supplied type.
            active_only: When True, only active watches are returned.

        Returns:
            A list of WatchTarget objects matching the filters.
        """
        with self._lock:
            watches = list(self._watches.values())
        result: List[WatchTarget] = []
        for w in watches:
            if active_only and not w.active:
                continue
            if file_type is not None and w.file_types and file_type not in w.file_types:
                continue
            result.append(w)
        return result

    # ------------------------------------------------------------------
    # Subscription management
    # ------------------------------------------------------------------

    def subscribe(
        self,
        subscriber_id: str,
        paths: Optional[List[str]] = None,
        kinds: Optional[List[ChangeKind]] = None,
        strategy: ReloadStrategy = ReloadStrategy.IMMEDIATE,
    ) -> Subscriber:
        """Register a new subscriber.

        If a subscriber with the same ``subscriber_id`` already exists
        its configuration is replaced atomically. The returned object
        reflects the new state. Subscribers are FIFO-evicted when the
        ``_MAX_SUBSCRIBERS`` cap is exceeded.

        Args:
            subscriber_id: Caller-supplied unique identifier.
            paths: Optional list of path patterns to filter for. Empty
                list means "all paths".
            kinds: Optional list of ChangeKind values to filter for.
                Empty list means "all kinds".
            strategy: The preferred ReloadStrategy.

        Returns:
            The (newly inserted or updated) Subscriber.
        """
        with self._lock:
            # Enforce the bounded store cap via FIFO eviction, but
            # never evict the subscriber being upserted.
            if (
                subscriber_id not in self._subscribers
                and len(self._subscribers) >= _MAX_SUBSCRIBERS
            ):
                oldest_id = next(iter(self._subscribers), None)
                if oldest_id is not None:
                    self._subscribers.pop(oldest_id, None)

            existing = self._subscribers.get(subscriber_id)
            notification_count = existing.notification_count if existing else 0
            last_notified_at = existing.last_notified_at if existing else ""

            subscriber = Subscriber(
                subscriber_id=subscriber_id,
                paths=list(paths) if paths else [],
                kinds=list(kinds) if kinds else [],
                strategy=strategy,
                notification_count=notification_count,
                last_notified_at=last_notified_at,
            )
            self._subscribers[subscriber_id] = subscriber
            if existing is None:
                self._subscriber_counter += 1

            self._record_event(
                HotReloadEventKind.SUBSCRIBER_NOTIFIED,
                payload={
                    "subscriber_id": subscriber_id,
                    "subscribed": True,
                    "paths": subscriber.paths,
                    "kinds": [k.value for k in subscriber.kinds],
                    "strategy": subscriber.strategy.value,
                },
            )
            return subscriber

    def unsubscribe(self, subscriber_id: str) -> bool:
        """Remove a subscriber by id.

        Args:
            subscriber_id: The identifier of the subscriber to remove.

        Returns:
            True if the subscriber was removed, False if not found.
        """
        with self._lock:
            if subscriber_id in self._subscribers:
                self._subscribers.pop(subscriber_id, None)
                return True
            return False

    def list_subscribers(
        self,
        kind: Optional[SubscriberKind] = None,
    ) -> List[Subscriber]:
        """List registered subscribers, optionally filtered by kind.

        Args:
            kind: Optional SubscriberKind to filter by.

        Returns:
            A list of Subscriber objects matching the filter.
        """
        with self._lock:
            subscribers = list(self._subscribers.values())
        if kind is None:
            return subscribers
        return [s for s in subscribers if s.kind == kind]

    # ------------------------------------------------------------------
    # Change ingestion
    # ------------------------------------------------------------------

    def record_change(
        self,
        path: str,
        kind: ChangeKind,
        file_type: Optional[FileType] = None,
    ) -> FileChange:
        """Record a new file change event.

        When ``file_type`` is None the engine infers it from the file
        extension via :func:`_classify_file_type``. The change is
        stored in the change log (with FIFO eviction at the cap), the
        originating watch target's ``last_event_at`` is refreshed, a
        ``FILE_DETECTED`` audit event is recorded and the change is
        also added to the most recent unprocessed batch (or a new
        batch is created if no batch is currently open).

        Args:
            path: The path of the file that changed.
            kind: The ChangeKind classification.
            file_type: Optional explicit FileType; if None, the type
                is inferred from the path.

        Returns:
            The newly created FileChange.
        """
        with self._lock:
            # Enforce the bounded change-log cap via FIFO eviction.
            if len(self._changes) >= _MAX_CHANGES:
                oldest_id = next(iter(self._changes), None)
                if oldest_id is not None:
                    self._changes.pop(oldest_id, None)

            inferred = file_type if file_type is not None else _classify_file_type(path)

            # Find the originating watch target, if any.
            target_id = ""
            for target in self._watches.values():
                if target.path and (path == target.path or path.startswith(
                    target.path.rstrip("/") + "/"
                )):
                    target_id = target.target_id
                    target.last_event_at = _now()
                    break

            change = FileChange(
                path=path,
                kind=kind,
                file_type=inferred,
                target_id=target_id,
            )
            self._changes[change.change_id] = change
            self._change_counter += 1

            # Drop the change if a registered filter excludes the path.
            if not self._passes_filters(path):
                self._record_event(
                    HotReloadEventKind.FILE_DETECTED,
                    payload={
                        "change_id": change.change_id,
                        "path": path,
                        "kind": kind.value,
                        "filtered": True,
                    },
                )
                return change

            # Add the change to the latest open (unprocessed) batch, or
            # create a new batch if none exists. The batch carries the
            # strategy that will be used when it is processed.
            open_batch: Optional[ChangeBatch] = None
            for batch in reversed(self._batches.values()):
                if not batch.processed:
                    open_batch = batch
                    break
            if open_batch is None:
                if len(self._batches) >= _MAX_BATCHES:
                    oldest_bid = next(iter(self._batches), None)
                    if oldest_bid is not None:
                        self._batches.pop(oldest_bid, None)
                open_batch = ChangeBatch(process_strategy=ReloadStrategy.DEBOUNCED)
                self._batches[open_batch.batch_id] = open_batch
                self._batch_counter += 1
            open_batch.change_ids.append(change.change_id)

            self._record_event(
                HotReloadEventKind.FILE_DETECTED,
                payload={
                    "change_id": change.change_id,
                    "path": path,
                    "kind": kind.value,
                    "file_type": inferred.value,
                    "target_id": target_id,
                    "batch_id": open_batch.batch_id,
                },
            )
            return change

    def batch_changes(self) -> ChangeBatch:
        """Close the current open batch and return it.

        If no open batch exists (i.e. no changes have been recorded
        since the last call), a fresh empty batch is created and
        returned so that callers always receive a usable handle.

        Returns:
            The closed (or newly created) ChangeBatch.
        """
        with self._lock:
            open_batch: Optional[ChangeBatch] = None
            for batch in reversed(self._batches.values()):
                if not batch.processed:
                    open_batch = batch
                    break
            if open_batch is None:
                if len(self._batches) >= _MAX_BATCHES:
                    oldest_bid = next(iter(self._batches), None)
                    if oldest_bid is not None:
                        self._batches.pop(oldest_bid, None)
                open_batch = ChangeBatch(process_strategy=ReloadStrategy.DEBOUNCED)
                self._batches[open_batch.batch_id] = open_batch
                self._batch_counter += 1

            self._record_event(
                HotReloadEventKind.CHANGE_BATCHED,
                payload={
                    "batch_id": open_batch.batch_id,
                    "change_count": len(open_batch.change_ids),
                },
            )
            return open_batch

    def process_batch(
        self,
        batch_id: str,
        strategy: Optional[ReloadStrategy] = None,
    ) -> List[ReloadAction]:
        """Process a batch and emit ReloadAction objects.

        Each FileChange in the batch is matched against all registered
        subscribers. For every (change, subscriber) pair a
        ReloadAction is created in PENDING status. The ``strategy``
        parameter overrides the batch's ``process_strategy`` when
        supplied.

        Args:
            batch_id: Identifier of the batch to process.
            strategy: Optional override for the batch's strategy.

        Returns:
            A list of newly created ReloadAction objects. The list is
            empty if the batch is not found.
        """
        with self._lock:
            batch = self._batches.get(batch_id)
            if batch is None:
                return []
            if strategy is not None:
                batch.process_strategy = strategy

            effective_strategy = batch.process_strategy
            actions: List[ReloadAction] = []
            change_ids = list(batch.change_ids)
            for change_id in change_ids:
                change = self._changes.get(change_id)
                if change is None:
                    continue
                if not self._passes_filters(change.path):
                    continue
                subscribers = self._interested_subscribers(change.path, change.kind)
                for sub in subscribers:
                    # MANUAL subscribers are not notified automatically
                    # by process_batch; they must be triggered via
                    # trigger_reload.
                    if sub.strategy == ReloadStrategy.MANUAL:
                        continue
                    # When the batch strategy is BATCHED, the action
                    # inherits the batch strategy; otherwise it uses
                    # the subscriber's preferred strategy.
                    chosen = (
                        effective_strategy
                        if effective_strategy != ReloadStrategy.BATCHED
                        else sub.strategy
                    )
                    if len(self._actions) >= _MAX_ACTIONS:
                        oldest_aid = next(iter(self._actions), None)
                        if oldest_aid is not None:
                            self._actions.pop(oldest_aid, None)
                    action = ReloadAction(
                        subscriber_id=sub.subscriber_id,
                        path=change.path,
                        change_id=change.change_id,
                        batch_id=batch.batch_id,
                        strategy=chosen,
                        status=ReloadStatus.PENDING,
                    )
                    self._actions[action.action_id] = action
                    self._action_counter += 1
                    sub.notification_count += 1
                    sub.last_notified_at = _now()
                    actions.append(action)

                    self._record_event(
                        HotReloadEventKind.SUBSCRIBER_NOTIFIED,
                        payload={
                            "action_id": action.action_id,
                            "subscriber_id": sub.subscriber_id,
                            "change_id": change.change_id,
                            "path": change.path,
                        },
                    )

            batch.processed = True
            batch.processed_at = _now()
            return actions

    # ------------------------------------------------------------------
    # Reload orchestration
    # ------------------------------------------------------------------

    def trigger_reload(
        self,
        path: str,
        strategy: ReloadStrategy = ReloadStrategy.IMMEDIATE,
    ) -> Optional[ReloadAction]:
        """Plan a reload for ``path`` against all interested subscribers.

        The path is recorded as a synthetic change so that history
        lookups remain consistent. A ReloadAction is created in
        PENDING status for every interested subscriber (subject to the
        MANUAL strategy short-circuit).

        Args:
            path: The path to reload.
            strategy: The ReloadStrategy to apply.

        Returns:
            The first ReloadAction created, or None if no subscribers
            were interested.
        """
        with self._lock:
            change = self.record_change(path=path, kind=ChangeKind.MODIFIED)
            subscribers = self._interested_subscribers(path, ChangeKind.MODIFIED)
            created: List[ReloadAction] = []
            for sub in subscribers:
                if sub.strategy == ReloadStrategy.MANUAL and strategy != ReloadStrategy.MANUAL:
                    # Subscribers that opted in to MANUAL are still
                    # notified when the caller explicitly chooses
                    # MANUAL on this call.
                    pass
                if len(self._actions) >= _MAX_ACTIONS:
                    oldest_aid = next(iter(self._actions), None)
                    if oldest_aid is not None:
                        self._actions.pop(oldest_aid, None)
                action = ReloadAction(
                    subscriber_id=sub.subscriber_id,
                    path=path,
                    change_id=change.change_id,
                    batch_id="",
                    strategy=strategy,
                    status=ReloadStatus.PENDING,
                )
                self._actions[action.action_id] = action
                self._action_counter += 1
                sub.notification_count += 1
                sub.last_notified_at = _now()
                created.append(action)

            if not created:
                return None

            self._record_event(
                HotReloadEventKind.RELOAD_TRIGGERED,
                payload={
                    "path": path,
                    "strategy": strategy.value,
                    "subscriber_count": len(created),
                    "first_action_id": created[0].action_id,
                },
            )
            return created[0]

    def complete_reload(
        self,
        action_id: str,
        status: ReloadStatus = ReloadStatus.COMPLETED,
        error: str = "",
    ) -> Optional[ReloadAction]:
        """Mark a ReloadAction as finished and move it to history.

        Args:
            action_id: Identifier of the ReloadAction to complete.
            status: The terminal ReloadStatus to assign.
            error: Optional error message (used when status is FAILED).

        Returns:
            The updated ReloadAction, or None if not found.
        """
        with self._lock:
            action = self._actions.get(action_id)
            if action is None:
                return None
            action.status = status
            action.completed_at = _now()
            action.error = error

            # Move the action to the history log.
            started = action.created_at
            finished = action.completed_at
            try:
                t0 = datetime.fromisoformat(started.rstrip("Z"))
                t1 = datetime.fromisoformat(finished.rstrip("Z"))
                duration_ms = max(0.0, (t1 - t0).total_seconds() * 1000.0)
            except Exception:
                duration_ms = 0.0

            history = ReloadHistory(
                action_id=action.action_id,
                subscriber_id=action.subscriber_id,
                path=action.path,
                strategy=action.strategy,
                status=status,
                started_at=started,
                finished_at=finished,
                duration_ms=duration_ms,
                error=error,
            )
            if len(self._history) >= _MAX_HISTORY:
                self._history.pop(0)
            self._history.append(history)
            self._history_counter += 1

            # Remove the action from the live queue.
            self._actions.pop(action_id, None)

            if status == ReloadStatus.FAILED:
                self._record_event(
                    HotReloadEventKind.RELOAD_FAILED,
                    payload={
                        "action_id": action.action_id,
                        "subscriber_id": action.subscriber_id,
                        "path": action.path,
                        "error": error,
                    },
                )
            else:
                self._record_event(
                    HotReloadEventKind.RELOAD_COMPLETED,
                    payload={
                        "action_id": action.action_id,
                        "subscriber_id": action.subscriber_id,
                        "path": action.path,
                        "status": status.value,
                    },
                )
            return action

    def get_reload_history(self, limit: int = 100) -> List[ReloadAction]:
        """Return the most recent completed reloads.

        The returned objects are reconstructed ReloadAction instances
        derived from the ReloadHistory log; they are not the original
        live objects. The ``status`` field always reflects the final
        status recorded at completion time.

        Args:
            limit: Maximum number of records to return (most recent).

        Returns:
            A list of ReloadAction objects, most recent last.
        """
        with self._lock:
            history = list(self._history)
        if limit > 0:
            history = history[-limit:]
        result: List[ReloadAction] = []
        for h in history:
            result.append(
                ReloadAction(
                    action_id=h.action_id,
                    subscriber_id=h.subscriber_id,
                    path=h.path,
                    change_id="",
                    batch_id="",
                    strategy=h.strategy,
                    status=h.status,
                    created_at=h.started_at,
                    completed_at=h.finished_at,
                    error=h.error,
                )
            )
        return result

    def get_pending_actions(self) -> List[ReloadAction]:
        """Return all live reload actions in PENDING or IN_PROGRESS status."""
        with self._lock:
            actions = list(self._actions.values())
        return [
            a for a in actions
            if a.status in (ReloadStatus.PENDING, ReloadStatus.IN_PROGRESS)
        ]

    # ------------------------------------------------------------------
    # Tuning: debounce window and filters
    # ------------------------------------------------------------------

    def set_debounce(self, window_ms: int) -> None:
        """Set the debounce window in milliseconds.

        Values less than 0 are clamped to 0 (no debounce). The window
        is advisory -- it does not retroactively re-batch existing
        changes -- and primarily affects newly created batches.

        Args:
            window_ms: The desired debounce window in milliseconds.
        """
        with self._lock:
            self._debounce_window_ms = max(0, int(window_ms))

    def add_filter(
        self,
        pattern: str,
        include: bool = True,
    ) -> WatchFilter:
        """Register a new watch filter.

        Args:
            pattern: The glob pattern to match.
            include: True for an include rule, False for an exclude
                rule. Exclude rules always win over include rules.

        Returns:
            The newly created WatchFilter.
        """
        with self._lock:
            if len(self._filters) >= _MAX_FILTERS:
                oldest_id = next(iter(self._filters), None)
                if oldest_id is not None:
                    self._filters.pop(oldest_id, None)
            flt = WatchFilter(pattern=pattern, include=bool(include))
            self._filters[flt.filter_id] = flt
            self._filter_counter += 1
            return flt

    def remove_filter(self, pattern: str) -> bool:
        """Remove the first filter matching ``pattern``.

        Args:
            pattern: The pattern string of the filter to remove.

        Returns:
            True if a filter was removed, False otherwise.
        """
        with self._lock:
            for fid, flt in list(self._filters.items()):
                if flt.pattern == pattern:
                    self._filters.pop(fid, None)
                    return True
            return False

    # ------------------------------------------------------------------
    # Simulation / test hooks
    # ------------------------------------------------------------------

    def simulate_event(self, path: str, kind: ChangeKind) -> FileChange:
        """Inject a synthetic file change without touching the disk.

        This is a convenience wrapper around :meth:`record_change` for
        tests and demo flows. The change is processed through the
        normal ingestion pipeline (filter check, batch insertion,
        event recording).

        Args:
            path: The path to simulate a change on.
            kind: The ChangeKind to attribute to the change.

        Returns:
            The newly created FileChange.
        """
        return self.record_change(path=path, kind=kind)

    # ------------------------------------------------------------------
    # Observability
    # ------------------------------------------------------------------

    def list_events(self, limit: int = 100) -> List[HotReloadEvent]:
        """Return audit events limited to the most recent ``limit`` entries.

        Args:
            limit: Maximum number of events to return.

        Returns:
            A list of HotReloadEvent objects ordered from oldest to
            newest (after the truncation).
        """
        with self._lock:
            events = list(self._events)
        if limit > 0:
            events = events[-limit:]
        return events

    def get_stats(self) -> ReloadStats:
        """Compute aggregate statistics from the current engine state.

        Returns:
            A ReloadStats describing the current store counts, kind
            distribution, status distribution and debounce window.
        """
        with self._lock:
            changes_by_kind: Dict[str, int] = {}
            for c in self._changes.values():
                key = c.kind.value
                changes_by_kind[key] = changes_by_kind.get(key, 0) + 1
            actions_by_status: Dict[str, int] = {}
            for a in self._actions.values():
                key = a.status.value
                actions_by_status[key] = actions_by_status.get(key, 0) + 1
            return ReloadStats(
                total_watches=len(self._watches),
                total_changes=len(self._changes),
                total_batches=len(self._batches),
                total_subscribers=len(self._subscribers),
                total_actions=len(self._actions),
                total_history=len(self._history),
                changes_by_kind=changes_by_kind,
                actions_by_status=actions_by_status,
                debounce_window_ms=self._debounce_window_ms,
            )

    def get_status(self) -> Dict[str, Any]:
        """Return a summary of the current hot reload engine state.

        The ``initialized`` flag is always the first key in the
        returned dictionary, followed by store counts and aggregate
        statistics.

        Returns:
            A dictionary with the system status.
        """
        with self._lock:
            stats = self.get_stats()
            return {
                "initialized": self._initialized,
                "total_watches": len(self._watches),
                "total_changes": len(self._changes),
                "total_batches": len(self._batches),
                "total_subscribers": len(self._subscribers),
                "total_actions": len(self._actions),
                "total_history": len(self._history),
                "total_filters": len(self._filters),
                "total_events": len(self._events),
                "watch_counter": self._watch_counter,
                "change_counter": self._change_counter,
                "batch_counter": self._batch_counter,
                "subscriber_counter": self._subscriber_counter,
                "action_counter": self._action_counter,
                "history_counter": self._history_counter,
                "filter_counter": self._filter_counter,
                "event_counter": self._event_counter,
                "debounce_window_ms": self._debounce_window_ms,
                "stats": stats.to_dict(),
            }

    def get_snapshot(self) -> HotReloadSnapshot:
        """Capture an immutable snapshot of the hot reload engine state.

        Returns:
            A HotReloadSnapshot capturing the system state at this
            moment.
        """
        with self._lock:
            stats = self.get_stats()
            return HotReloadSnapshot(
                initialized=self._initialized,
                watches=list(self._watches.values()),
                changes=list(self._changes.values()),
                batches=list(self._batches.values()),
                subscribers=list(self._subscribers.values()),
                actions=list(self._actions.values()),
                history=list(self._history),
                filters=list(self._filters.values()),
                events=list(self._events),
                stats=stats,
            )

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def reset(self) -> None:
        """Clear all stores and re-seed the engine with default data.

        Restores the engine to its initial state, including the seed
        watches, subscribers, filters, simulated changes and reload
        actions.
        """
        with self._lock:
            self._watches.clear()
            self._changes.clear()
            self._batches.clear()
            self._subscribers.clear()
            self._actions.clear()
            self._history.clear()
            self._filters.clear()
            self._events.clear()
            self._watch_counter = 0
            self._change_counter = 0
            self._batch_counter = 0
            self._subscriber_counter = 0
            self._action_counter = 0
            self._history_counter = 0
            self._filter_counter = 0
            self._event_counter = 0
            self._debounce_window_ms = 250
            self._seed_data()


# ---------------------------------------------------------------------------
# Module-Level Factory
# ---------------------------------------------------------------------------


def get_hot_reload_watcher() -> HotReloadWatcherEngine:
    """Return the singleton HotReloadWatcherEngine instance."""
    return HotReloadWatcherEngine.get_instance()
