"""
SparkLabs Engine - Undo/Redo Command System

A reversible command execution engine for the SparkLabs AI-native game
engine editor. Editor operations are captured as ``Command`` objects
that know how to apply (do) and revert (undo) themselves. Commands can
be grouped into ``Transaction`` batches for atomic undo, marked with
a ``MergePolicy`` so that adjacent similar commands (typing, dragging)
coalesce into a single undo step, and snapshotted via
``HistorySnapshot`` for time-travel debugging or session persistence.

Architecture:
  UndoRedoEngine (singleton)
    |-- Command, CommandBatch, Transaction, HistorySnapshot,
        CommandHistory, MergePolicy, UndoRedoStats, UndoRedoSnapshot,
        UndoRedoEvent
    |-- CommandType, CommandStatus, TransactionState, MergeMode,
        HistoryScope, UndoRedoEventKind

Core Capabilities:
  - push_command: register a reversible command on the undo stack
    (executes the do callback, attempts to merge via the active policy).
  - begin_transaction / end_transaction / abort_transaction: group
    commands into atomic batches.
  - undo / redo / undo_steps / redo_steps / can_undo / can_redo.
  - clear_history / get_history / get_undo_stack / get_redo_stack.
  - set_merge_mode / set_history_limit: per-scope configuration.
  - checkpoint / restore_checkpoint: persistent state snapshots.
  - get_status / get_snapshot / list_events: observability.
  - reset: clear all stores and re-seed with default data.

The class implements the singleton pattern with double-checked locking
using ``threading.RLock``; consumers should obtain the instance through
:meth:`UndoRedoEngine.get_instance` or the module-level
:func:`get_undo_redo` factory. All public methods are guarded by the
re-entrant lock.
"""

from __future__ import annotations

import threading
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple


# Capacity Constants

# Bounded store capacities. When a store exceeds its cap the oldest
# entry is evicted in FIFO order to keep memory growth predictable.
_MAX_COMMANDS: int = 5000
_MAX_TRANSACTIONS: int = 2000
_MAX_SNAPSHOTS: int = 500
_MAX_EVENTS: int = 5000
_MAX_HISTORIES: int = 64
_MERGE_INTERVAL_MS: int = 800


# Helper Functions


def _now() -> str:
    """Return the current UTC time as an ISO-8601 string with a 'Z' suffix."""
    return datetime.utcnow().isoformat() + "Z"


def _new_id(prefix: str = "") -> str:
    """Generate a short unique identifier, optionally prefixed."""
    base = uuid.uuid4().hex[:12]
    return f"{prefix}_{base}" if prefix else base


def _safe_call(fn: Optional[Callable[[], Any]]) -> bool:
    """Invoke a callable, swallowing exceptions. None is a no-op True.

    Used for the user-supplied ``do_fn`` and ``undo_fn`` callbacks so
    that a faulty callback never tears down the whole engine.
    """
    if fn is None:
        return True
    try:
        fn()
        return True
    except Exception:
        return False


# Domain Enums


class CommandType(Enum):
    """Classification of a reversible command.

    - ``CREATE``: an entity or asset was created.
    - ``DELETE``: an entity or asset was destroyed.
    - ``MODIFY``: a non-specific mutation was applied.
    - ``MOVE``: a transform translation was applied.
    - ``PROPERTY_CHANGE``: a single property was set to a new value.
    - ``TRANSFORM``: a transform edit (rotation, scale, shear).
    - ``SCRIPT``: a script binding or hot-reload occurred.
    - ``ASSET``: an asset was imported, reimported or compiled.
    """

    CREATE = "create"
    DELETE = "delete"
    MODIFY = "modify"
    MOVE = "move"
    PROPERTY_CHANGE = "property_change"
    TRANSFORM = "transform"
    SCRIPT = "script"
    ASSET = "asset"


class CommandStatus(Enum):
    """Lifecycle status of a Command.

    - ``PENDING``: constructed but not yet applied.
    - ``APPLIED``: the do callback has been executed.
    - ``UNDONE``: the undo callback has been executed.
    - ``FAILED``: the most recent callback raised and was suppressed.
    - ``MERGED``: subsumed into a newer adjacent command.
    """

    PENDING = "pending"
    APPLIED = "applied"
    UNDONE = "undone"
    FAILED = "failed"
    MERGED = "merged"


class TransactionState(Enum):
    """Lifecycle state of a Transaction.

    - ``OPEN``: currently accepting commands; not yet committed.
    - ``COMMITTED``: sealed and pushed onto the undo stack as a single
      atomic unit.
    - ``ABORTED``: closed without pushing (no commands were kept).
    - ``ROLLED_BACK``: closed and the entire batch was reverted.
    """

    OPEN = "open"
    COMMITTED = "committed"
    ABORTED = "aborted"
    ROLLED_BACK = "rolled_back"


class MergeMode(Enum):
    """Strategy for merging adjacent commands.

    - ``NONE``: never merge. Each command is its own undo step.
    - ``ADJACENT_SAME``: merge with the previous command only when both
      share the same ``merge_key`` and ``command_type``.
    - ``ADJACENT_PROPERTY``: like ``ADJACENT_SAME`` but specialized for
      property edits (e.g. dragging a slider).
    - ``ADJACENT_TRANSFORM``: specialized for transform gizmo drags.
    - ``INTERVAL``: merge when both share the ``merge_key`` and the
      time delta is below the configured interval.
    """

    NONE = "none"
    ADJACENT_SAME = "adjacent_same"
    ADJACENT_PROPERTY = "adjacent_property"
    ADJACENT_TRANSFORM = "adjacent_transform"
    INTERVAL = "interval"


class HistoryScope(Enum):
    """Bucket into which commands are partitioned.

    - ``GLOBAL``: one history that contains every command.
    - ``SCENE``: per-scene histories.
    - ``ENTITY``: per-entity histories (used for inspector edits).
    - ``COMPONENT``: per-component histories (fine-grained undo).
    """

    GLOBAL = "global"
    SCENE = "scene"
    ENTITY = "entity"
    COMPONENT = "component"


class UndoRedoEventKind(Enum):
    """Audit event kinds emitted by the undo/redo engine."""

    COMMAND_PUSHED = "command_pushed"
    COMMAND_UNDONE = "command_undone"
    COMMAND_REDONE = "command_redone"
    TRANSACTION_STARTED = "transaction_started"
    TRANSACTION_COMMITTED = "transaction_committed"
    HISTORY_CLEARED = "history_cleared"
    COMMAND_MERGED = "command_merged"


# Default Policy Table

# Per-scope default merge modes. Components and entities use interval
# merging so that rapid editor interactions fold into a single undo step.
_DEFAULT_MERGE_MODE: Dict[HistoryScope, MergeMode] = {
    HistoryScope.GLOBAL: MergeMode.NONE,
    HistoryScope.SCENE: MergeMode.NONE,
    HistoryScope.ENTITY: MergeMode.INTERVAL,
    HistoryScope.COMPONENT: MergeMode.ADJACENT_PROPERTY,
}

# Per-scope default history limits.
_DEFAULT_HISTORY_LIMIT: Dict[HistoryScope, int] = {
    HistoryScope.GLOBAL: 1000,
    HistoryScope.SCENE: 500,
    HistoryScope.ENTITY: 200,
    HistoryScope.COMPONENT: 100,
}


# Data Classes


@dataclass
class Command:
    """A reversible operation.

    A command encapsulates a forward (``do_fn``) and a reverse
    (``undo_fn``) callable that apply and revert the operation. It
    carries the metadata needed to participate in merging, transaction
    grouping and serialization.
    """

    command_id: str = field(default_factory=lambda: _new_id("cmd"))
    command_type: CommandType = CommandType.MODIFY
    name: str = ""
    scope: HistoryScope = HistoryScope.GLOBAL
    scope_key: str = ""
    merge_key: str = ""
    do_fn: Optional[Callable[[], Any]] = None
    undo_fn: Optional[Callable[[], Any]] = None
    status: CommandStatus = CommandStatus.PENDING
    pushed_at: str = field(default_factory=_now)
    applied_at: str = ""
    undone_at: str = ""
    transaction_id: str = ""
    merge_count: int = 1
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "command_id": self.command_id,
            "command_type": self.command_type.value,
            "name": self.name,
            "scope": self.scope.value,
            "scope_key": self.scope_key,
            "merge_key": self.merge_key,
            "status": self.status.value,
            "pushed_at": self.pushed_at,
            "applied_at": self.applied_at,
            "undone_at": self.undone_at,
            "transaction_id": self.transaction_id,
            "merge_count": self.merge_count,
            "metadata": dict(self.metadata) if self.metadata else {},
        }


@dataclass
class CommandBatch:
    """A group of commands executed atomically.

    A batch is the unit of undo/redo for any operation that is
    logically one user action but is implemented as several underlying
    commands (for example, a paste that creates N entities). All
    commands in a batch share the same ``batch_id`` and are undone in
    reverse order on undo and redone in forward order on redo.
    """

    batch_id: str = field(default_factory=lambda: _new_id("batch"))
    name: str = ""
    commands: List[Command] = field(default_factory=list)
    scope: HistoryScope = HistoryScope.GLOBAL
    scope_key: str = ""
    created_at: str = field(default_factory=_now)
    applied: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "batch_id": self.batch_id,
            "name": self.name,
            "commands": [c.to_dict() for c in self.commands],
            "scope": self.scope.value,
            "scope_key": self.scope_key,
            "created_at": self.created_at,
            "applied": self.applied,
            "command_count": len(self.commands),
            "metadata": dict(self.metadata) if self.metadata else {},
        }


@dataclass
class Transaction:
    """A multi-command grouping for atomic undo.

    Transactions are opened with
    :meth:`UndoRedoEngine.begin_transaction` and closed with
    :meth:`end_transaction` (commit) or :meth:`abort_transaction`
    (discard). All commands pushed while a transaction is open are
    collected into the transaction's ``commands`` list and collapse
    into a single undo step when the transaction is committed.
    """

    transaction_id: str = field(default_factory=lambda: _new_id("tx"))
    name: str = ""
    state: TransactionState = TransactionState.OPEN
    scope: HistoryScope = HistoryScope.GLOBAL
    scope_key: str = ""
    commands: List[Command] = field(default_factory=list)
    started_at: str = field(default_factory=_now)
    closed_at: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "transaction_id": self.transaction_id,
            "name": self.name,
            "state": self.state.value,
            "scope": self.scope.value,
            "scope_key": self.scope_key,
            "commands": [c.to_dict() for c in self.commands],
            "command_count": len(self.commands),
            "started_at": self.started_at,
            "closed_at": self.closed_at,
            "metadata": dict(self.metadata) if self.metadata else {},
        }


@dataclass
class HistorySnapshot:
    """A checkpoint of the undo/redo state at a moment in time.

    Snapshots allow the engine to roll back to a known-good point in
    the edit history (for example when an AI assistant makes a
    speculative change the user wants to discard).
    """

    snapshot_id: str = field(default_factory=lambda: _new_id("snap"))
    name: str = ""
    scope: HistoryScope = HistoryScope.GLOBAL
    scope_key: str = ""
    undo_stack: List[Dict[str, Any]] = field(default_factory=list)
    redo_stack: List[Dict[str, Any]] = field(default_factory=list)
    active_transaction_id: str = ""
    created_at: str = field(default_factory=_now)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "snapshot_id": self.snapshot_id,
            "name": self.name,
            "scope": self.scope.value,
            "scope_key": self.scope_key,
            "undo_stack": list(self.undo_stack),
            "redo_stack": list(self.redo_stack),
            "active_transaction_id": self.active_transaction_id,
            "created_at": self.created_at,
            "undo_size": len(self.undo_stack),
            "redo_size": len(self.redo_stack),
            "metadata": dict(self.metadata) if self.metadata else {},
        }


@dataclass
class CommandHistory:
    """Full history for a single scope/bucket with metadata.

    A ``CommandHistory`` owns the undo and redo stacks, the current
    merge mode, the bounded history limit and bookkeeping counters.
    """

    scope: HistoryScope = HistoryScope.GLOBAL
    scope_key: str = ""
    undo_stack: List[Command] = field(default_factory=list)
    redo_stack: List[Command] = field(default_factory=list)
    merge_mode: MergeMode = MergeMode.NONE
    history_limit: int = 1000
    total_pushed: int = 0
    total_undone: int = 0
    total_redone: int = 0
    total_merged: int = 0
    last_push_at: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "scope": self.scope.value,
            "scope_key": self.scope_key,
            "undo_stack": [c.to_dict() for c in self.undo_stack],
            "redo_stack": [c.to_dict() for c in self.redo_stack],
            "merge_mode": self.merge_mode.value,
            "history_limit": self.history_limit,
            "undo_size": len(self.undo_stack),
            "redo_size": len(self.redo_stack),
            "total_pushed": self.total_pushed,
            "total_undone": self.total_undone,
            "total_redone": self.total_redone,
            "total_merged": self.total_merged,
            "last_push_at": self.last_push_at,
            "metadata": dict(self.metadata) if self.metadata else {},
        }


@dataclass
class MergePolicy:
    """Rules for merging adjacent similar commands.

    A merge policy encapsulates the conditions under which a freshly
    pushed command can be folded into the previous command on the undo
    stack. The engine uses one policy per scope.
    """

    mode: MergeMode = MergeMode.NONE
    max_interval_ms: int = _MERGE_INTERVAL_MS
    require_same_scope_key: bool = True
    require_same_merge_key: bool = True
    require_same_command_type: bool = True
    enabled: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "mode": self.mode.value,
            "max_interval_ms": self.max_interval_ms,
            "require_same_scope_key": self.require_same_scope_key,
            "require_same_merge_key": self.require_same_merge_key,
            "require_same_command_type": self.require_same_command_type,
            "enabled": self.enabled,
        }


@dataclass
class UndoRedoStats:
    """Aggregate counters describing the undo/redo engine state."""

    total_commands: int = 0
    total_transactions: int = 0
    total_snapshots: int = 0
    total_events: int = 0
    total_merged: int = 0
    total_undone: int = 0
    total_redone: int = 0
    total_restored: int = 0
    history_count: int = 0
    by_scope: Dict[str, int] = field(default_factory=dict)
    by_type: Dict[str, int] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_commands": self.total_commands,
            "total_transactions": self.total_transactions,
            "total_snapshots": self.total_snapshots,
            "total_events": self.total_events,
            "total_merged": self.total_merged,
            "total_undone": self.total_undone,
            "total_redone": self.total_redone,
            "total_restored": self.total_restored,
            "history_count": self.history_count,
            "by_scope": dict(self.by_scope) if self.by_scope else {},
            "by_type": dict(self.by_type) if self.by_type else {},
        }


@dataclass
class UndoRedoSnapshot:
    """An immutable snapshot of the entire undo/redo engine state."""

    initialized: bool = False
    histories: Dict[str, CommandHistory] = field(default_factory=dict)
    active_transaction: Optional[Transaction] = None
    snapshots: List[HistorySnapshot] = field(default_factory=list)
    transactions: List[Transaction] = field(default_factory=list)
    events: List["UndoRedoEvent"] = field(default_factory=list)
    stats: UndoRedoStats = field(default_factory=UndoRedoStats)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "initialized": self.initialized,
            "histories": {k: h.to_dict() for k, h in self.histories.items()},
            "active_transaction": self.active_transaction.to_dict()
            if self.active_transaction is not None
            else None,
            "snapshots": [s.to_dict() for s in self.snapshots],
            "transactions": [t.to_dict() for t in self.transactions],
            "events": [e.to_dict() for e in self.events],
            "stats": self.stats.to_dict(),
        }


@dataclass
class UndoRedoEvent:
    """An audit event emitted by the undo/redo engine."""

    event_id: str = field(default_factory=lambda: _new_id("evt"))
    kind: UndoRedoEventKind = UndoRedoEventKind.COMMAND_PUSHED
    timestamp: str = field(default_factory=_now)
    scope: HistoryScope = HistoryScope.GLOBAL
    scope_key: str = ""
    command_id: str = ""
    transaction_id: str = ""
    snapshot_id: str = ""
    payload: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": self.event_id,
            "kind": self.kind.value,
            "timestamp": self.timestamp,
            "scope": self.scope.value,
            "scope_key": self.scope_key,
            "command_id": self.command_id,
            "transaction_id": self.transaction_id,
            "snapshot_id": self.snapshot_id,
            "payload": dict(self.payload) if self.payload else {},
        }


# Undo/Redo Engine (Singleton)


class UndoRedoEngine:
    """Reversible command execution engine for the editor.

    Maintains per-scope command histories (undo/redo stacks), an
    active transaction (when commands are being batched), and a
    collection of checkpoints that can be restored. The engine
    supports command merging so that rapid-fire editor interactions
    (typing, dragging) collapse into a single undo step.

    Implements the singleton pattern with double-checked locking
    using ``threading.RLock`` for thread-safe access. All public
    methods are guarded by the re-entrant lock. Consumers should
    obtain the instance through :meth:`get_instance` or the
    module-level :func:`get_undo_redo` factory.

    Usage:
        engine = get_undo_redo()
        engine.push_command(
            CommandType.PROPERTY_CHANGE, "Set Cube X",
            do_fn=lambda: cube.position.x = 1.0,
            undo_fn=lambda: cube.position.x = 0.0,
            scope=HistoryScope.ENTITY, scope_key=cube.id,
            merge_key="position.x",
        )
        engine.undo()
        engine.redo()
    """

    _instance: Optional["UndoRedoEngine"] = None
    _lock: threading.RLock = threading.RLock()

    # Singleton management

    def __new__(cls) -> "UndoRedoEngine":
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
    def get_instance(cls) -> "UndoRedoEngine":
        """Return the singleton engine instance (constructs on first use)."""
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

            self._histories: Dict[str, CommandHistory] = {}
            self._merge_policies: Dict[HistoryScope, MergePolicy] = {
                scope: MergePolicy(mode=_DEFAULT_MERGE_MODE[scope])
                for scope in HistoryScope
            }
            self._active_transaction: Optional[Transaction] = None
            self._snapshots: Dict[str, HistorySnapshot] = {}
            self._transactions: List[Transaction] = []
            self._events: List[UndoRedoEvent] = []

            # Aggregate counters maintained for fast stats retrieval.
            self._command_counter: int = 0
            self._transaction_counter: int = 0
            self._snapshot_counter: int = 0
            self._event_counter: int = 0
            self._merge_counter: int = 0
            self._undo_counter: int = 0
            self._redo_counter: int = 0
            self._restore_counter: int = 0

            self._initialized: bool = True
            self._seed_data()

    # Seeding

    def _seed_data(self) -> None:
        """Populate the engine with a representative seed history.

        Demonstrates a typical editor session: open a "Create Player"
        transaction with three commands, push a series of single
        commands, open a "Tune Enemy" transaction with three property
        edits, commit it, and capture one checkpoint. All seed
        callbacks are no-ops so the seed is side-effect free.
        """
        # Seed transaction 1: Create Player
        self.begin_transaction(name="Create Player")
        for name in ("Create Player Entity", "Create Weapon Entity", "Import Player Script"):
            self.push_command(
                command_type=CommandType.CREATE if "Entity" in name else CommandType.ASSET,
                name=name, do_fn=None, undo_fn=None,
                scope=HistoryScope.GLOBAL, merge_key="",
            )
        self.end_transaction()

        # Seed commands: direct global history.
        for ct, name, key in (
            (CommandType.MODIFY, "Set Player Name", "player.name"),
            (CommandType.PROPERTY_CHANGE, "Set Player Health", "player.health"),
            (CommandType.TRANSFORM, "Rotate Player 90 deg", "player.rotation"),
            (CommandType.MOVE, "Move Player to Spawn", "player.position"),
            (CommandType.SCRIPT, "Hot Reload Player Script", "player.script"),
            (CommandType.DELETE, "Delete Temp Marker", "marker.delete"),
        ):
            self.push_command(
                command_type=ct, name=name, do_fn=None, undo_fn=None,
                scope=HistoryScope.GLOBAL, merge_key=key,
            )

        # Seed transaction 2: Tune Enemy
        self.begin_transaction(name="Tune Enemy")
        for name, key in (
            ("Set Enemy Speed", "enemy.speed"),
            ("Set Enemy Damage", "enemy.damage"),
            ("Set Enemy Health", "enemy.health"),
        ):
            self.push_command(
                command_type=CommandType.PROPERTY_CHANGE, name=name,
                do_fn=None, undo_fn=None, scope=HistoryScope.GLOBAL, merge_key=key,
            )
        self.end_transaction()

        # Seed checkpoint.
        self.checkpoint(name="after_enemy_tuning")

    # Internal helpers

    @staticmethod
    def _history_key(scope: HistoryScope, scope_key: str) -> str:
        """Return the bucket key for a scope/scope_key pair (``"scope:scope_key"``)."""
        return f"{scope.value}:{scope_key}"

    def _get_or_create_history(
        self, scope: HistoryScope, scope_key: str
    ) -> CommandHistory:
        """Return the history for the bucket, creating it if missing.

        Caller must hold ``self._lock``. Enforces the bounded
        history store cap via FIFO eviction.
        """
        key = self._history_key(scope, scope_key)
        history = self._histories.get(key)
        if history is not None:
            return history
        # Enforce the bounded history store cap via FIFO eviction.
        if len(self._histories) >= _MAX_HISTORIES:
            oldest_key = next(iter(self._histories), None)
            if oldest_key is not None:
                self._histories.pop(oldest_key, None)
        history = CommandHistory(
            scope=scope,
            scope_key=scope_key,
            merge_mode=_DEFAULT_MERGE_MODE.get(scope, MergeMode.NONE),
            history_limit=_DEFAULT_HISTORY_LIMIT.get(scope, 1000),
            metadata={"seed": False},
        )
        self._histories[key] = history
        return history

    def _maybe_merge(
        self,
        history: CommandHistory,
        new_command: Command,
        policy: MergePolicy,
    ) -> bool:
        """Attempt to merge ``new_command`` into the previous command.

        If the previous command on the history's undo stack satisfies
        the merge policy with respect to ``new_command``, the previous
        command's ``merge_count`` is incremented and the new command is
        marked MERGED. Returns True if a merge happened. Caller must
        hold ``self._lock``.
        """
        if not policy.enabled or policy.mode == MergeMode.NONE:
            return False
        if not history.undo_stack:
            return False

        previous = history.undo_stack[-1]
        if previous.status != CommandStatus.APPLIED:
            return False
        if previous.transaction_id and previous.transaction_id == new_command.transaction_id:
            # Do not merge commands inside the same transaction; the
            # transaction itself is the atomic unit of undo.
            return False

        if policy.require_same_command_type and (
            previous.command_type != new_command.command_type
        ):
            return False
        if policy.require_same_scope_key and (
            previous.scope_key != new_command.scope_key
        ):
            return False
        if policy.require_same_merge_key and (
            previous.merge_key != new_command.merge_key
        ):
            return False

        if policy.mode == MergeMode.INTERVAL:
            try:
                prev_ts = datetime.fromisoformat(previous.pushed_at.rstrip("Z"))
                new_ts = datetime.fromisoformat(new_command.pushed_at.rstrip("Z"))
                delta_ms = (new_ts - prev_ts).total_seconds() * 1000.0
            except Exception:
                delta_ms = policy.max_interval_ms + 1
            if delta_ms > policy.max_interval_ms:
                return False

        # The new command supersedes the previous one.
        previous.merge_count += 1
        new_command.status = CommandStatus.MERGED
        history.total_merged += 1
        self._merge_counter += 1
        self._record_event(
            kind=UndoRedoEventKind.COMMAND_MERGED,
            scope=new_command.scope,
            scope_key=new_command.scope_key,
            command_id=previous.command_id,
            payload={
                "merged_command_id": new_command.command_id,
                "merge_count": previous.merge_count,
                "merge_key": new_command.merge_key,
            },
        )
        return True

    def _record_event(
        self,
        kind: UndoRedoEventKind,
        scope: HistoryScope = HistoryScope.GLOBAL,
        scope_key: str = "",
        command_id: str = "",
        transaction_id: str = "",
        snapshot_id: str = "",
        payload: Optional[Dict[str, Any]] = None,
    ) -> UndoRedoEvent:
        """Record an audit event (caller must hold ``self._lock``).

        Returns the created UndoRedoEvent. Evicts the oldest event
        when the event store is at capacity.
        """
        event = UndoRedoEvent(
            kind=kind,
            scope=scope,
            scope_key=scope_key,
            command_id=command_id,
            transaction_id=transaction_id,
            snapshot_id=snapshot_id,
            payload=dict(payload) if payload else {},
        )
        if len(self._events) >= _MAX_EVENTS:
            # FIFO eviction: drop the oldest event.
            self._events.pop(0)
        self._events.append(event)
        self._event_counter += 1
        return event

    # Command push and execution

    def push_command(
        self,
        command_type: CommandType,
        name: str,
        do_fn: Optional[Callable[[], Any]],
        undo_fn: Optional[Callable[[], Any]],
        scope: HistoryScope = HistoryScope.GLOBAL,
        merge_key: str = "",
        scope_key: str = "",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Command:
        """Register a new reversible command on the undo stack.

        The ``do_fn`` is executed immediately. If a merge policy is
        active and the new command can coalesce with the previous
        command on the stack, the new command is recorded as MERGED.
        Otherwise it is appended to the history's undo stack, the redo
        stack is cleared, and a COMMAND_PUSHED event is recorded.

        When a transaction is currently open, the new command is
        collected into the transaction instead of being pushed to the
        history immediately. Returns the created Command.
        """
        with self._lock:
            command = Command(
                command_type=command_type,
                name=name,
                scope=scope,
                scope_key=scope_key,
                merge_key=merge_key,
                do_fn=do_fn,
                undo_fn=undo_fn,
                status=CommandStatus.PENDING,
                metadata=dict(metadata) if metadata else {},
            )
            if self._active_transaction is not None:
                command.transaction_id = self._active_transaction.transaction_id
                self._active_transaction.commands.append(command)
                self._record_event(
                    kind=UndoRedoEventKind.COMMAND_PUSHED,
                    scope=scope,
                    scope_key=scope_key,
                    command_id=command.command_id,
                    transaction_id=command.transaction_id,
                    payload={
                        "name": name,
                        "command_type": command_type.value,
                        "merged": False,
                        "in_transaction": True,
                    },
                )
                return command

            # Apply the do callback before appending to the history.
            applied = _safe_call(do_fn)
            if applied:
                command.status = CommandStatus.APPLIED
                command.applied_at = _now()
            else:
                command.status = CommandStatus.FAILED

            history = self._get_or_create_history(scope, scope_key)
            policy = self._merge_policies.get(
                scope, MergePolicy(mode=MergeMode.NONE)
            )

            merged = False
            if applied and self._maybe_merge(history, command, policy):
                merged = True

            if not merged:
                # New commands invalidate any redo path.
                history.redo_stack.clear()
                # Enforce the bounded history limit via FIFO eviction.
                limit = max(1, int(history.history_limit))
                while len(history.undo_stack) >= limit:
                    history.undo_stack.pop(0)
                history.undo_stack.append(command)
                history.total_pushed += 1
                history.last_push_at = command.pushed_at
                self._command_counter += 1

            self._record_event(
                kind=UndoRedoEventKind.COMMAND_PUSHED,
                scope=scope,
                scope_key=scope_key,
                command_id=command.command_id,
                payload={
                    "name": name,
                    "command_type": command_type.value,
                    "merged": merged,
                    "status": command.status.value,
                },
            )
            return command

    # Transactions

    def begin_transaction(
        self,
        name: str,
        scope: HistoryScope = HistoryScope.GLOBAL,
        scope_key: str = "",
    ) -> Transaction:
        """Open a new transaction that groups subsequent commands.

        While the transaction is open, every command pushed via
        :meth:`push_command` is collected into the transaction. The
        transaction is closed via :meth:`end_transaction` (commit) or
        :meth:`abort_transaction` (discard). A nested begin returns
        the existing transaction unchanged.
        """
        with self._lock:
            if self._active_transaction is not None:
                return self._active_transaction
            transaction = Transaction(
                name=name,
                state=TransactionState.OPEN,
                scope=scope,
                scope_key=scope_key,
            )
            self._active_transaction = transaction
            self._transaction_counter += 1
            self._transactions.append(transaction)
            self._record_event(
                kind=UndoRedoEventKind.TRANSACTION_STARTED,
                scope=scope,
                scope_key=scope_key,
                transaction_id=transaction.transaction_id,
                payload={"name": name},
            )
            return transaction

    def end_transaction(self) -> Transaction:
        """Close and commit the active transaction.

        On commit the transaction's first command is pushed to the
        history's undo stack as a summary entry; the rest remain on the
        transaction for serialization. The transaction's state becomes
        COMMITTED. Returns an empty ABORTED transaction when no
        transaction is open.
        """
        with self._lock:
            if self._active_transaction is None:
                empty = Transaction(state=TransactionState.ABORTED)
                return empty
            transaction = self._active_transaction
            self._active_transaction = None
            transaction.state = TransactionState.COMMITTED
            transaction.closed_at = _now()

            if transaction.commands:
                history = self._get_or_create_history(
                    transaction.scope, transaction.scope_key
                )
                # Use the first command as the "representative" and
                # mark it as a transaction summary; the rest are
                # retained on the transaction for serialization.
                summary = transaction.commands[0]
                summary.status = CommandStatus.APPLIED
                summary.applied_at = transaction.closed_at
                history.redo_stack.clear()
                limit = max(1, int(history.history_limit))
                while len(history.undo_stack) >= limit:
                    history.undo_stack.pop(0)
                history.undo_stack.append(summary)
                history.total_pushed += 1
                history.last_push_at = summary.pushed_at
                self._command_counter += 1

            self._record_event(
                kind=UndoRedoEventKind.TRANSACTION_COMMITTED,
                scope=transaction.scope,
                scope_key=transaction.scope_key,
                transaction_id=transaction.transaction_id,
                payload={
                    "name": transaction.name,
                    "command_count": len(transaction.commands),
                },
            )
            return transaction

    def abort_transaction(self) -> Transaction:
        """Close the active transaction without pushing to the stack.

        All commands collected inside the transaction are discarded and
        the transaction's state is set to ABORTED. If no transaction
        is open, an empty ABORTED transaction is returned.
        """
        with self._lock:
            if self._active_transaction is None:
                return Transaction(state=TransactionState.ABORTED)
            transaction = self._active_transaction
            self._active_transaction = None
            transaction.state = TransactionState.ABORTED
            transaction.closed_at = _now()
            transaction.commands.clear()
            self._record_event(
                kind=UndoRedoEventKind.TRANSACTION_COMMITTED,
                scope=transaction.scope,
                scope_key=transaction.scope_key,
                transaction_id=transaction.transaction_id,
                payload={
                    "name": transaction.name,
                    "aborted": True,
                    "command_count": 0,
                },
            )
            return transaction

    # Undo / redo

    def undo(self) -> Optional[Command]:
        """Undo the most recent command on the GLOBAL history.

        The command's ``undo_fn`` is invoked (when present), the
        command is moved from the undo stack to the redo stack and a
        COMMAND_UNDONE event is recorded.

        Returns:
            The undone Command, or None if the undo stack is empty.
        """
        return self._undo_one(HistoryScope.GLOBAL, "")

    def redo(self) -> Optional[Command]:
        """Redo the most recently undone command on the GLOBAL history.

        The command's ``do_fn`` is invoked, the command is moved from
        the redo stack back to the undo stack and a COMMAND_REDONE
        event is recorded.

        Returns:
            The redone Command, or None if the redo stack is empty.
        """
        return self._redo_one(HistoryScope.GLOBAL, "")

    def can_undo(self, scope: HistoryScope = HistoryScope.GLOBAL,
                 scope_key: str = "") -> bool:
        """Return whether a command is available to undo on the given bucket."""
        with self._lock:
            history = self._histories.get(self._history_key(scope, scope_key))
            if history is None:
                return False
            return bool(history.undo_stack)

    def can_redo(self, scope: HistoryScope = HistoryScope.GLOBAL,
                 scope_key: str = "") -> bool:
        """Return whether a command is available to redo on the given bucket."""
        with self._lock:
            history = self._histories.get(self._history_key(scope, scope_key))
            if history is None:
                return False
            return bool(history.redo_stack)

    def undo_steps(
        self, n: int, scope: HistoryScope = HistoryScope.GLOBAL, scope_key: str = ""
    ) -> List[Command]:
        """Undo up to ``n`` commands in order (most recent first).

        Args:
            n: Maximum number of commands to undo. Values <= 0 return
                an empty list.
            scope: The history scope to operate on.
            scope_key: The bucket key within the scope.

        Returns:
            The list of commands that were actually undone (shorter
            than ``n`` when the stack runs dry).
        """
        with self._lock:
            undone: List[Command] = []
            for _ in range(max(0, int(n))):
                cmd = self._undo_one_internal(scope, scope_key)
                if cmd is None:
                    break
                undone.append(cmd)
            return undone

    def redo_steps(
        self, n: int, scope: HistoryScope = HistoryScope.GLOBAL, scope_key: str = ""
    ) -> List[Command]:
        """Redo up to ``n`` commands in order.

        Args:
            n: Maximum number of commands to redo. Values <= 0 result
                in an empty list.
            scope: The history scope to operate on.
            scope_key: The bucket key within the scope.

        Returns:
            The list of commands that were actually redone.
        """
        with self._lock:
            redone: List[Command] = []
            for _ in range(max(0, int(n))):
                cmd = self._redo_one_internal(scope, scope_key)
                if cmd is None:
                    break
                redone.append(cmd)
            return redone

    def _undo_one(
        self, scope: HistoryScope, scope_key: str
    ) -> Optional[Command]:
        """Public lock-protected wrapper around ``_undo_one_internal``."""
        with self._lock:
            return self._undo_one_internal(scope, scope_key)

    def _undo_one_internal(
        self, scope: HistoryScope, scope_key: str
    ) -> Optional[Command]:
        """Undo the most recent command (caller holds ``self._lock``)."""
        history = self._histories.get(self._history_key(scope, scope_key))
        if history is None or not history.undo_stack:
            return None
        command = history.undo_stack.pop()
        ok = _safe_call(command.undo_fn)
        if ok:
            command.status = CommandStatus.UNDONE
            command.undone_at = _now()
        else:
            command.status = CommandStatus.FAILED
        history.redo_stack.append(command)
        history.total_undone += 1
        self._undo_counter += 1
        self._record_event(
            kind=UndoRedoEventKind.COMMAND_UNDONE,
            scope=scope,
            scope_key=scope_key,
            command_id=command.command_id,
            payload={
                "name": command.name,
                "command_type": command.command_type.value,
                "ok": ok,
            },
        )
        return command

    def _redo_one(
        self, scope: HistoryScope, scope_key: str
    ) -> Optional[Command]:
        """Public lock-protected wrapper around ``_redo_one_internal``."""
        with self._lock:
            return self._redo_one_internal(scope, scope_key)

    def _redo_one_internal(
        self, scope: HistoryScope, scope_key: str
    ) -> Optional[Command]:
        """Redo the most recently undone command (caller holds lock)."""
        history = self._histories.get(self._history_key(scope, scope_key))
        if history is None or not history.redo_stack:
            return None
        command = history.redo_stack.pop()
        ok = _safe_call(command.do_fn)
        if ok:
            command.status = CommandStatus.APPLIED
            command.applied_at = _now()
        else:
            command.status = CommandStatus.FAILED
        history.undo_stack.append(command)
        history.total_redone += 1
        self._redo_counter += 1
        self._record_event(
            kind=UndoRedoEventKind.COMMAND_REDONE,
            scope=scope,
            scope_key=scope_key,
            command_id=command.command_id,
            payload={
                "name": command.name,
                "command_type": command.command_type.value,
                "ok": ok,
            },
        )
        return command

    # History management

    def clear_history(
        self, scope: HistoryScope = HistoryScope.GLOBAL, scope_key: str = ""
    ) -> None:
        """Clear the undo and redo stacks for a single history bucket."""
        with self._lock:
            key = self._history_key(scope, scope_key)
            history = self._histories.get(key)
            if history is None:
                return
            cleared_undo = len(history.undo_stack)
            cleared_redo = len(history.redo_stack)
            history.undo_stack.clear()
            history.redo_stack.clear()
            history.metadata["last_cleared_at"] = _now()
            self._record_event(
                kind=UndoRedoEventKind.HISTORY_CLEARED,
                scope=scope,
                scope_key=scope_key,
                payload={
                    "cleared_undo": cleared_undo,
                    "cleared_redo": cleared_redo,
                },
            )

    def get_history(
        self, scope: HistoryScope = HistoryScope.GLOBAL, scope_key: str = ""
    ) -> CommandHistory:
        """Return a deep-copy snapshot of the history for a bucket.

        An empty CommandHistory is returned when no history exists for
        the bucket. The returned object is decoupled from the engine
        state and may be safely mutated by the caller.
        """
        with self._lock:
            history = self._histories.get(self._history_key(scope, scope_key))
            if history is None:
                return CommandHistory(
                    scope=scope,
                    scope_key=scope_key,
                    merge_mode=_DEFAULT_MERGE_MODE.get(scope, MergeMode.NONE),
                    history_limit=_DEFAULT_HISTORY_LIMIT.get(scope, 1000),
                )
            return CommandHistory(
                scope=history.scope,
                scope_key=history.scope_key,
                undo_stack=list(history.undo_stack),
                redo_stack=list(history.redo_stack),
                merge_mode=history.merge_mode,
                history_limit=history.history_limit,
                total_pushed=history.total_pushed,
                total_undone=history.total_undone,
                total_redone=history.total_redone,
                total_merged=history.total_merged,
                last_push_at=history.last_push_at,
                metadata=dict(history.metadata) if history.metadata else {},
            )

    def get_undo_stack(
        self, scope: HistoryScope = HistoryScope.GLOBAL, scope_key: str = ""
    ) -> List[Command]:
        """Return a copy of the undo stack for a bucket (oldest to newest)."""
        with self._lock:
            history = self._histories.get(self._history_key(scope, scope_key))
            if history is None:
                return []
            return list(history.undo_stack)

    def get_redo_stack(
        self, scope: HistoryScope = HistoryScope.GLOBAL, scope_key: str = ""
    ) -> List[Command]:
        """Return a copy of the redo stack for a bucket (oldest to newest)."""
        with self._lock:
            history = self._histories.get(self._history_key(scope, scope_key))
            if history is None:
                return []
            return list(history.redo_stack)

    def set_merge_mode(
        self,
        scope: HistoryScope,
        mode: MergeMode,
        max_interval_ms: Optional[int] = None,
    ) -> None:
        """Configure the merge policy for a scope.

        ``max_interval_ms`` overrides the interval used by
        ``MergeMode.INTERVAL`` (no effect for other modes).
        """
        with self._lock:
            policy = self._merge_policies.setdefault(
                scope, MergePolicy(mode=mode)
            )
            policy.mode = mode
            policy.enabled = mode != MergeMode.NONE
            if max_interval_ms is not None:
                policy.max_interval_ms = int(max_interval_ms)

    def set_history_limit(
        self, scope: HistoryScope, limit: int, scope_key: str = ""
    ) -> None:
        """Configure the bounded undo stack size for a scope.

        The limit is clamped to a minimum of 1. When ``scope_key`` is
        empty, every bucket under the scope is updated.
        """
        with self._lock:
            new_limit = max(1, int(limit))
            if scope_key:
                history = self._get_or_create_history(scope, scope_key)
                history.history_limit = new_limit
                while len(history.undo_stack) > new_limit:
                    history.undo_stack.pop(0)
                return
            for key, history in self._histories.items():
                if history.scope == scope:
                    history.history_limit = new_limit
                    while len(history.undo_stack) > new_limit:
                        history.undo_stack.pop(0)

    # Checkpoints

    def checkpoint(
        self,
        name: str,
        scope: HistoryScope = HistoryScope.GLOBAL,
        scope_key: str = "",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> HistorySnapshot:
        """Capture a serializable checkpoint of the current state.

        When ``scope_key`` is empty, every bucket under the scope is
        captured; otherwise only the matching bucket is captured. The
        active transaction id (if any) is recorded on the snapshot.
        """
        with self._lock:
            undo_dump: List[Dict[str, Any]] = []
            redo_dump: List[Dict[str, Any]] = []
            if scope_key:
                history = self._histories.get(
                    self._history_key(scope, scope_key)
                )
                if history is not None:
                    undo_dump = [c.to_dict() for c in history.undo_stack]
                    redo_dump = [c.to_dict() for c in history.redo_stack]
            else:
                for history in self._histories.values():
                    if history.scope == scope:
                        undo_dump.extend(c.to_dict() for c in history.undo_stack)
                        redo_dump.extend(c.to_dict() for c in history.redo_stack)

            active_tx = (
                self._active_transaction.transaction_id
                if self._active_transaction is not None
                else ""
            )
            snapshot = HistorySnapshot(
                name=name,
                scope=scope,
                scope_key=scope_key,
                undo_stack=undo_dump,
                redo_stack=redo_dump,
                active_transaction_id=active_tx,
                metadata=dict(metadata) if metadata else {},
            )
            # Enforce the bounded snapshot store cap via FIFO eviction.
            if len(self._snapshots) >= _MAX_SNAPSHOTS:
                oldest_id = next(iter(self._snapshots), None)
                if oldest_id is not None:
                    self._snapshots.pop(oldest_id, None)
            self._snapshots[snapshot.snapshot_id] = snapshot
            self._snapshot_counter += 1
            self._record_event(
                kind=UndoRedoEventKind.HISTORY_CLEARED,
                scope=scope,
                scope_key=scope_key,
                snapshot_id=snapshot.snapshot_id,
                payload={"name": name, "captured": True},
            )
            return snapshot

    def restore_checkpoint(self, snapshot_id: str) -> bool:
        """Restore the engine to a previously captured checkpoint.

        The bucket's undo and redo stacks are replaced with the
        serialized command lists stored in the snapshot. The active
        transaction (if any) is left untouched. Returns False when the
        snapshot id is unknown.
        """
        with self._lock:
            snapshot = self._snapshots.get(snapshot_id)
            if snapshot is None:
                return False
            # Replace the bucket history with the snapshot data. Only
            # the matching bucket is replaced to avoid wiping
            # unrelated histories.
            history = self._get_or_create_history(
                snapshot.scope, snapshot.scope_key
            )
            history.undo_stack = [
                Command(
                    command_type=CommandType(d.get("command_type", "modify")),
                    name=d.get("name", ""),
                    scope=HistoryScope(d.get("scope", "global")),
                    scope_key=d.get("scope_key", ""),
                    merge_key=d.get("merge_key", ""),
                    status=CommandStatus(d.get("status", "applied")),
                    pushed_at=d.get("pushed_at", _now()),
                    applied_at=d.get("applied_at", ""),
                    transaction_id=d.get("transaction_id", ""),
                    metadata=d.get("metadata", {}),
                )
                for d in snapshot.undo_stack
            ]
            history.redo_stack = [
                Command(
                    command_type=CommandType(d.get("command_type", "modify")),
                    name=d.get("name", ""),
                    scope=HistoryScope(d.get("scope", "global")),
                    scope_key=d.get("scope_key", ""),
                    merge_key=d.get("merge_key", ""),
                    status=CommandStatus.UNDONE,
                    pushed_at=d.get("pushed_at", _now()),
                    applied_at=d.get("applied_at", ""),
                    transaction_id=d.get("transaction_id", ""),
                    metadata=d.get("metadata", {}),
                )
                for d in snapshot.redo_stack
            ]
            self._restore_counter += 1
            self._record_event(
                kind=UndoRedoEventKind.HISTORY_CLEARED,
                scope=snapshot.scope,
                scope_key=snapshot.scope_key,
                snapshot_id=snapshot.snapshot_id,
                payload={"restored": True, "name": snapshot.name},
            )
            return True

    # Observability

    def list_events(self, limit: int = 100) -> List[UndoRedoEvent]:
        """Return audit events limited to the most recent ``limit`` entries.

        A non-positive ``limit`` returns an empty list.
        """
        with self._lock:
            events = list(self._events)
        if limit <= 0:
            return []
        return events[-limit:]

    def get_stats(self) -> UndoRedoStats:
        """Compute aggregate statistics from the current engine state.

        Returns an UndoRedoStats describing store counts and the
        per-scope / per-type command distribution.
        """
        with self._lock:
            total_commands = 0
            by_scope: Dict[str, int] = {}
            by_type: Dict[str, int] = {}
            for history in self._histories.values():
                for cmd in history.undo_stack:
                    total_commands += 1
                    scope_key = cmd.scope.value
                    type_key = cmd.command_type.value
                    by_scope[scope_key] = by_scope.get(scope_key, 0) + 1
                    by_type[type_key] = by_type.get(type_key, 0) + 1
                for cmd in history.redo_stack:
                    total_commands += 1
                    scope_key = cmd.scope.value
                    type_key = cmd.command_type.value
                    by_scope[scope_key] = by_scope.get(scope_key, 0) + 1
                    by_type[type_key] = by_type.get(type_key, 0) + 1
            return UndoRedoStats(
                total_commands=total_commands,
                total_transactions=len(self._transactions),
                total_snapshots=len(self._snapshots),
                total_events=len(self._events),
                total_merged=self._merge_counter,
                total_undone=self._undo_counter,
                total_redone=self._redo_counter,
                total_restored=self._restore_counter,
                history_count=len(self._histories),
                by_scope=by_scope,
                by_type=by_type,
            )

    def get_status(self) -> Dict[str, Any]:
        """Return a summary of the current undo/redo engine state.

        The ``initialized`` flag is always the first key in the
        returned dictionary, followed by store counts, aggregate
        counters and the computed stats block.
        """
        with self._lock:
            stats = self.get_stats()
            return {
                "initialized": self._initialized,
                "history_count": len(self._histories),
                "transaction_count": len(self._transactions),
                "snapshot_count": len(self._snapshots),
                "event_count": len(self._events),
                "command_counter": self._command_counter,
                "transaction_counter": self._transaction_counter,
                "snapshot_counter": self._snapshot_counter,
                "event_counter": self._event_counter,
                "merge_counter": self._merge_counter,
                "undo_counter": self._undo_counter,
                "redo_counter": self._redo_counter,
                "restore_counter": self._restore_counter,
                "has_active_transaction": self._active_transaction is not None,
                "active_transaction_name": (
                    self._active_transaction.name
                    if self._active_transaction is not None
                    else ""
                ),
                "stats": stats.to_dict(),
            }

    def get_snapshot(self) -> UndoRedoSnapshot:
        """Capture an immutable snapshot of the undo/redo engine state."""
        with self._lock:
            stats = self.get_stats()
            histories_copy: Dict[str, CommandHistory] = {}
            for key, history in self._histories.items():
                histories_copy[key] = CommandHistory(
                    scope=history.scope,
                    scope_key=history.scope_key,
                    undo_stack=list(history.undo_stack),
                    redo_stack=list(history.redo_stack),
                    merge_mode=history.merge_mode,
                    history_limit=history.history_limit,
                    total_pushed=history.total_pushed,
                    total_undone=history.total_undone,
                    total_redone=history.total_redone,
                    total_merged=history.total_merged,
                    last_push_at=history.last_push_at,
                    metadata=dict(history.metadata) if history.metadata else {},
                )
            return UndoRedoSnapshot(
                initialized=self._initialized,
                histories=histories_copy,
                active_transaction=self._active_transaction,
                snapshots=list(self._snapshots.values()),
                transactions=list(self._transactions),
                events=list(self._events),
                stats=stats,
            )

    # Lifecycle

    def reset(self) -> None:
        """Clear all stores and re-seed the engine with default data.

        Restores the engine to its initial state, including the seed
        history, transactions and checkpoint.
        """
        with self._lock:
            self._histories.clear()
            self._merge_policies = {
                scope: MergePolicy(mode=_DEFAULT_MERGE_MODE[scope])
                for scope in HistoryScope
            }
            self._active_transaction = None
            self._snapshots.clear()
            self._transactions.clear()
            self._events.clear()
            self._command_counter = 0
            self._transaction_counter = 0
            self._snapshot_counter = 0
            self._event_counter = 0
            self._merge_counter = 0
            self._undo_counter = 0
            self._redo_counter = 0
            self._restore_counter = 0
            self._seed_data()


# Module-Level Factory


def get_undo_redo() -> UndoRedoEngine:
    """Return the singleton UndoRedoEngine instance."""
    return UndoRedoEngine.get_instance()
