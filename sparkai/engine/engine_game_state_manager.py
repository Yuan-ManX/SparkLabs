"""
SparkLabs Engine - Game State Manager

Unified game state management for the SparkLabs AI-native game engine.
Provides a single source of truth for save data, scene stacks, runtime
state snapshots, checkpoint systems, and state diffing for network
synchronization.

Architecture:
  GameStateManager (Singleton, double-checked locking)
    |-- StateConfig          -- configuration for state management
    |-- GameState            -- complete game state snapshot
    |-- SceneStackEntry      -- entry in the scene navigation stack
    |-- Checkpoint           -- named checkpoint with embedded state
    |-- StateDiff            -- field-level difference between two states
    |-- StateManagerSnapshot -- complete state manager snapshot

Subsystems:
  1. Save Slots    -- persistent storage of GameState per SaveSlot
  2. Checkpoints   -- named rollback points with metadata
  3. Scene Stack   -- hierarchical scene navigation (push/pop/replace/swap)
  4. State Diffing -- added/removed/modified field diff for net sync
"""

from __future__ import annotations

import copy
import hashlib
import json
import threading
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class StateType(Enum):
    """Classification of a game state by the scope of data it captures."""
    GLOBAL = "global"
    SCENE = "scene"
    ENTITY = "entity"
    COMPONENT = "component"
    SESSION = "session"
    PERSISTENT = "persistent"
    TRANSIENT = "transient"


class SnapshotType(Enum):
    """Strategy used to capture a state snapshot."""
    FULL = "full"
    INCREMENTAL = "incremental"
    DIFF = "diff"
    CHECKPOINT = "checkpoint"
    AUTOSAVE = "autosave"


class SaveSlot(Enum):
    """Logical save slot identifier covering manual, quick, auto, and cloud."""
    SLOT_1 = "slot_1"
    SLOT_2 = "slot_2"
    SLOT_3 = "slot_3"
    SLOT_4 = "slot_4"
    QUICK_SAVE = "quick_save"
    AUTO_SAVE = "auto_save"
    CLOUD_SAVE = "cloud_save"


class StackOperation(Enum):
    """Operation performed on the scene navigation stack."""
    PUSH = "push"
    POP = "pop"
    REPLACE = "replace"
    SWAP = "swap"
    CLEAR = "clear"


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------

@dataclass
class StateConfig:
    """Configuration for the GameStateManager."""

    max_save_slots: int = 7
    max_checkpoints: int = 20
    max_scene_stack: int = 32
    autosave_enabled: bool = True
    autosave_interval_s: float = 300.0
    diff_enabled: bool = True
    compression_enabled: bool = False
    verify_on_load: bool = True
    created_at: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "max_save_slots": self.max_save_slots,
            "max_checkpoints": self.max_checkpoints,
            "max_scene_stack": self.max_scene_stack,
            "autosave_enabled": self.autosave_enabled,
            "autosave_interval_s": self.autosave_interval_s,
            "diff_enabled": self.diff_enabled,
            "compression_enabled": self.compression_enabled,
            "verify_on_load": self.verify_on_load,
            "created_at": self.created_at,
            "metadata": dict(self.metadata),
        }


@dataclass
class GameState:
    """A complete game state snapshot captured at a point in time."""

    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    state_type: StateType = StateType.GLOBAL
    snapshot_type: SnapshotType = SnapshotType.FULL
    timestamp: float = field(default_factory=time.time)
    scene_id: str = ""
    global_data: Dict[str, Any] = field(default_factory=dict)
    entity_data: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    component_data: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    session_data: Dict[str, Any] = field(default_factory=dict)
    persistent_data: Dict[str, Any] = field(default_factory=dict)
    transient_data: Dict[str, Any] = field(default_factory=dict)
    hash: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "state_type": self.state_type.value,
            "snapshot_type": self.snapshot_type.value,
            "timestamp": self.timestamp,
            "scene_id": self.scene_id,
            "global_data": dict(self.global_data),
            "entity_data": {eid: dict(s) for eid, s in self.entity_data.items()},
            "component_data": {cid: dict(s) for cid, s in self.component_data.items()},
            "session_data": dict(self.session_data),
            "persistent_data": dict(self.persistent_data),
            "transient_data": dict(self.transient_data),
            "hash": self.hash,
            "metadata": dict(self.metadata),
        }


@dataclass
class SceneStackEntry:
    """An entry in the scene navigation stack."""

    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    scene_id: str = ""
    layer: str = "base"
    data: Dict[str, Any] = field(default_factory=dict)
    pushed_at: float = field(default_factory=time.time)
    is_active: bool = True
    is_paused: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "scene_id": self.scene_id,
            "layer": self.layer,
            "data": dict(self.data),
            "pushed_at": self.pushed_at,
            "is_active": self.is_active,
            "is_paused": self.is_paused,
            "metadata": dict(self.metadata),
        }


@dataclass
class Checkpoint:
    """A named checkpoint with metadata and embedded game state."""

    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    name: str = ""
    timestamp: float = field(default_factory=time.time)
    state: Optional[GameState] = None
    description: str = ""
    is_auto: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "timestamp": self.timestamp,
            "state": self.state.to_dict() if self.state is not None else None,
            "description": self.description,
            "is_auto": self.is_auto,
            "metadata": dict(self.metadata),
        }


@dataclass
class StateDiff:
    """Field-level difference between two GameState snapshots."""

    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    from_id: str = ""
    to_id: str = ""
    timestamp: float = field(default_factory=time.time)
    added: Dict[str, Any] = field(default_factory=dict)
    removed: List[str] = field(default_factory=list)
    modified: Dict[str, Any] = field(default_factory=dict)
    unchanged_count: int = 0
    hash: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "from_id": self.from_id,
            "to_id": self.to_id,
            "timestamp": self.timestamp,
            "added": dict(self.added),
            "removed": list(self.removed),
            "modified": dict(self.modified),
            "unchanged_count": self.unchanged_count,
            "hash": self.hash,
            "metadata": dict(self.metadata),
        }


@dataclass
class StateManagerSnapshot:
    """Complete snapshot of the GameStateManager's runtime status."""

    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    timestamp: float = field(default_factory=time.time)
    save_slots: List[Dict[str, Any]] = field(default_factory=list)
    checkpoint_count: int = 0
    scene_stack_depth: int = 0
    active_scene_id: str = ""
    stats: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "timestamp": self.timestamp,
            "save_slots": list(self.save_slots),
            "checkpoint_count": self.checkpoint_count,
            "scene_stack_depth": self.scene_stack_depth,
            "active_scene_id": self.active_scene_id,
            "stats": dict(self.stats),
            "metadata": dict(self.metadata),
        }


# ---------------------------------------------------------------------------
# Game State Manager
# ---------------------------------------------------------------------------

class GameStateManager:
    """
    Unified game state manager for the SparkLabs engine.

    Coordinates save slots, named checkpoints, a scene navigation stack,
    and state diffing for network synchronization. Thread-safe via RLock.
    """

    _instance: Optional["GameStateManager"] = None
    _lock = threading.RLock()

    _DEFAULT_MAX_CHECKPOINTS: int = 20
    _DEFAULT_MAX_SCENE_STACK: int = 32

    def __new__(cls) -> "GameStateManager":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    @classmethod
    def get_instance(cls) -> "GameStateManager":
        """Get the singleton GameStateManager instance with double-checked locking."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self) -> None:
        if self._initialized:
            return
        self._initialized = True

        # State stores
        self._config: StateConfig = StateConfig()
        self._states: Dict[str, GameState] = {}
        self._save_slots: Dict[SaveSlot, GameState] = {}
        self._checkpoints: Dict[str, Checkpoint] = {}
        self._checkpoint_order: List[str] = []
        self._scene_stack: List[SceneStackEntry] = []
        self._diffs: Dict[str, StateDiff] = {}

        # Bookkeeping
        self._is_initialized: bool = False
        self._is_running: bool = False
        self._save_count: int = 0
        self._load_count: int = 0
        self._checkpoint_count: int = 0
        self._diff_count: int = 0
        self._scene_ops_count: int = 0
        self._creation_time: float = time.time()
        self._last_save_time: float = 0.0
        self._last_load_time: float = 0.0

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def initialize(self, config: Optional[StateConfig] = None) -> bool:
        """Initialize the state manager with an optional configuration.

        Args:
            config: Optional StateConfig. Defaults to a new StateConfig.

        Returns:
            True if initialization succeeded (or was already initialized).
        """
        with self._lock:
            if self._is_initialized:
                return True
            self._config = config or StateConfig()
            self._is_initialized = True
            self._is_running = True
            return True

    def shutdown(self) -> None:
        """Gracefully shut down the state manager, releasing all stored state."""
        with self._lock:
            self._is_running = False
            self._states.clear()
            self._save_slots.clear()
            self._checkpoints.clear()
            self._checkpoint_order.clear()
            self._scene_stack.clear()
            self._diffs.clear()

    # ------------------------------------------------------------------
    # Save / Load
    # ------------------------------------------------------------------

    def save_state(self, slot: SaveSlot, state: GameState) -> Optional[GameState]:
        """Save a game state to the given save slot.

        Computes a content hash for integrity verification and stores a deep
        copy of the state so later mutations do not affect the saved snapshot.

        Args:
            slot: The SaveSlot to write to.
            state: The GameState to persist.

        Returns:
            The stored GameState copy, or None if the manager is not running.
        """
        with self._lock:
            if not self._is_running:
                return None

            snapshot = copy.deepcopy(state)
            snapshot.snapshot_type = SnapshotType.FULL
            snapshot.timestamp = time.time()
            snapshot.hash = self._compute_state_hash(snapshot)

            self._save_slots[slot] = snapshot
            self._states[snapshot.id] = snapshot
            self._save_count += 1
            self._last_save_time = snapshot.timestamp
            return snapshot

    def load_state(self, slot: SaveSlot) -> Optional[GameState]:
        """Load the game state stored in the given save slot.

        When verify_on_load is enabled, the stored hash is recomputed and
        compared against the state content. A mismatch returns None.

        Returns:
            The loaded GameState, or None if the slot is empty, corrupted,
            or the manager is not running.
        """
        with self._lock:
            if not self._is_running:
                return None

            state = self._save_slots.get(slot)
            if state is None:
                return None

            if self._config.verify_on_load and state.hash:
                recomputed = self._compute_state_hash(state)
                if recomputed != state.hash:
                    state.metadata["corrupted"] = True
                    return None

            self._load_count += 1
            self._last_load_time = time.time()
            return copy.deepcopy(state)

    # ------------------------------------------------------------------
    # Checkpoints
    # ------------------------------------------------------------------

    def create_checkpoint(
        self,
        name: str,
        state: GameState,
        description: str = "",
        is_auto: bool = False,
    ) -> Optional[Checkpoint]:
        """Create a named checkpoint embedding a copy of the given state.

        Args:
            name: Unique checkpoint name. If it already exists, the existing
                checkpoint is replaced.
            state: The GameState to embed.
            description: Optional human-readable description.
            is_auto: Whether this checkpoint was created automatically.

        Returns:
            The created Checkpoint, or None if the manager is not running.
        """
        with self._lock:
            if not self._is_running:
                return None

            snapshot = copy.deepcopy(state)
            snapshot.hash = self._compute_state_hash(snapshot)

            checkpoint = Checkpoint(
                name=name,
                state=snapshot,
                description=description,
                is_auto=is_auto,
                timestamp=time.time(),
            )

            # Replace existing checkpoint with the same name
            existing = self._checkpoints.get(name)
            if existing is not None:
                self._checkpoint_order.remove(name)

            self._checkpoints[name] = checkpoint
            self._checkpoint_order.append(name)
            self._checkpoint_count += 1

            self._prune_checkpoints()
            return checkpoint

    def restore_checkpoint(self, name: str) -> Optional[GameState]:
        """Restore a previously created checkpoint by name.

        Returns a deep copy so the caller cannot mutate the stored checkpoint.

        Returns:
            A copy of the checkpoint's GameState, or None if not found.
        """
        with self._lock:
            checkpoint = self._checkpoints.get(name)
            if checkpoint is None or checkpoint.state is None:
                return None
            return copy.deepcopy(checkpoint.state)

    def _prune_checkpoints(self) -> None:
        """Enforce the max_checkpoints limit, evicting the oldest entries."""
        max_c = self._config.max_checkpoints
        while len(self._checkpoint_order) > max_c:
            oldest = self._checkpoint_order.pop(0)
            self._checkpoints.pop(oldest, None)

    # ------------------------------------------------------------------
    # Scene Stack
    # ------------------------------------------------------------------

    def push_scene(
        self,
        scene_id: str,
        data: Optional[Dict[str, Any]] = None,
        layer: str = "base",
    ) -> Optional[SceneStackEntry]:
        """Push a new scene onto the navigation stack.

        The previously active scene (if any) is marked as paused and inactive.
        The new entry becomes the active scene.

        Returns:
            The created SceneStackEntry, or None if the stack is full or the
            manager is not running.
        """
        with self._lock:
            if not self._is_running:
                return None
            if len(self._scene_stack) >= self._config.max_scene_stack:
                return None

            # Pause the currently active scene
            if self._scene_stack:
                current = self._scene_stack[-1]
                current.is_active = False
                current.is_paused = True

            entry = SceneStackEntry(
                scene_id=scene_id,
                layer=layer,
                data=dict(data) if data else {},
                is_active=True,
                is_paused=False,
                pushed_at=time.time(),
            )
            self._scene_stack.append(entry)
            self._scene_ops_count += 1
            return entry

    def pop_scene(self) -> Optional[SceneStackEntry]:
        """Pop the top scene from the navigation stack.

        The new top scene (if any) is resumed and marked active.

        Returns:
            The removed SceneStackEntry, or None if the stack is empty.
        """
        with self._lock:
            if not self._scene_stack:
                return None

            entry = self._scene_stack.pop()
            self._scene_ops_count += 1

            # Resume the new top scene
            if self._scene_stack:
                top = self._scene_stack[-1]
                top.is_active = True
                top.is_paused = False

            return entry

    def get_active_scene(self) -> Optional[SceneStackEntry]:
        """Get the currently active scene (top of the stack)."""
        with self._lock:
            if not self._scene_stack:
                return None
            return self._scene_stack[-1]

    def get_scene_stack(self) -> List[SceneStackEntry]:
        """Get a copy of the full scene stack from bottom to top."""
        with self._lock:
            return list(self._scene_stack)

    # ------------------------------------------------------------------
    # State Diffing
    # ------------------------------------------------------------------

    def compute_diff(
        self,
        state_a: GameState,
        state_b: GameState,
    ) -> StateDiff:
        """Compute a field-level diff between two GameState snapshots.

        The diff is computed over the merged set of keys across all data
        buckets (global_data, session_data, persistent_data, transient_data).
        Per-field values from state_b are used as the source of truth.

        Args:
            state_a: The baseline state.
            state_b: The target state.

        Returns:
            A StateDiff describing added, removed, and modified fields.
        """
        with self._lock:
            diff = StateDiff(
                from_id=state_a.id,
                to_id=state_b.id,
                timestamp=time.time(),
            )

            merged_keys: set = set()
            per_bucket: Dict[str, Tuple[Dict[str, Any], Dict[str, Any]]] = {
                "global": (state_a.global_data, state_b.global_data),
                "session": (state_a.session_data, state_b.session_data),
                "persistent": (state_a.persistent_data, state_b.persistent_data),
                "transient": (state_a.transient_data, state_b.transient_data),
            }

            for bucket, (data_a, data_b) in per_bucket.items():
                keys_a = set(data_a.keys())
                keys_b = set(data_b.keys())
                merged_keys |= keys_a | keys_b

                for key in keys_b - keys_a:
                    diff.added[f"{bucket}.{key}"] = copy.deepcopy(data_b[key])

                for key in keys_a - keys_b:
                    diff.removed.append(f"{bucket}.{key}")

                for key in keys_a & keys_b:
                    if data_a[key] != data_b[key]:
                        diff.modified[f"{bucket}.{key}"] = copy.deepcopy(data_b[key])
                    else:
                        diff.unchanged_count += 1

            diff.hash = self._compute_diff_hash(diff)
            self._diffs[diff.id] = diff
            self._diff_count += 1
            return diff

    def apply_diff(self, base_state: GameState, diff: StateDiff) -> GameState:
        """Apply a StateDiff to a base GameState, returning a new state.

        The base state is deep-copied so the original is not mutated. Added
        and modified fields are written; removed fields are deleted.

        Args:
            base_state: The starting GameState.
            diff: The StateDiff to apply.

        Returns:
            A new GameState reflecting the applied diff.
        """
        with self._lock:
            result = copy.deepcopy(base_state)
            result.id = uuid.uuid4().hex[:12]
            result.timestamp = time.time()
            result.snapshot_type = SnapshotType.DIFF

            bucket_map = {
                "global": result.global_data,
                "session": result.session_data,
                "persistent": result.persistent_data,
                "transient": result.transient_data,
            }

            for path, value in diff.added.items():
                bucket, key = self._split_path(path)
                if bucket in bucket_map:
                    bucket_map[bucket][key] = copy.deepcopy(value)

            for path, value in diff.modified.items():
                bucket, key = self._split_path(path)
                if bucket in bucket_map:
                    bucket_map[bucket][key] = copy.deepcopy(value)

            for path in diff.removed:
                bucket, key = self._split_path(path)
                if bucket in bucket_map and key in bucket_map[bucket]:
                    del bucket_map[bucket][key]

            result.hash = self._compute_state_hash(result)
            return result

    @staticmethod
    def _split_path(path: str) -> Tuple[str, str]:
        """Split a 'bucket.key' path into (bucket, key)."""
        if "." in path:
            bucket, key = path.split(".", 1)
            return bucket, key
        return "global", path

    # ------------------------------------------------------------------
    # Hashing
    # ------------------------------------------------------------------

    def _compute_state_hash(self, state: GameState) -> str:
        """Compute an SHA-256 hash of a state's data buckets."""
        content = json.dumps(
            {
                "global_data": state.global_data,
                "entity_data": state.entity_data,
                "component_data": state.component_data,
                "session_data": state.session_data,
                "persistent_data": state.persistent_data,
                "transient_data": state.transient_data,
                "scene_id": state.scene_id,
            },
            sort_keys=True,
            default=str,
        )
        return hashlib.sha256(content.encode("utf-8")).hexdigest()

    def _compute_diff_hash(self, diff: StateDiff) -> str:
        """Compute an SHA-256 hash of a diff's contents."""
        content = json.dumps(
            {
                "from_id": diff.from_id,
                "to_id": diff.to_id,
                "added": diff.added,
                "removed": diff.removed,
                "modified": diff.modified,
            },
            sort_keys=True,
            default=str,
        )
        return hashlib.sha256(content.encode("utf-8")).hexdigest()

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------

    def get_save_slots(self) -> List[Dict[str, Any]]:
        """Get info for all save slots, including empty ones.

        Returns a list sorted by the SaveSlot declaration order, each entry
        describing whether the slot is occupied and basic state metadata.
        """
        with self._lock:
            result: List[Dict[str, Any]] = []
            for slot in SaveSlot:
                state = self._save_slots.get(slot)
                result.append(
                    {
                        "slot": slot.value,
                        "occupied": state is not None,
                        "state_id": state.id if state else None,
                        "timestamp": state.timestamp if state else 0.0,
                        "scene_id": state.scene_id if state else "",
                        "hash": state.hash if state else "",
                    }
                )
            return result

    def get_status(self) -> Dict[str, Any]:
        """Get the runtime status of the state manager.

        Includes initialization/running flags, counts, and the active scene.
        """
        with self._lock:
            active = self.get_active_scene()
            return {
                "is_initialized": self._is_initialized,
                "is_running": self._is_running,
                "config": self._config.to_dict(),
                "save_count": self._save_count,
                "load_count": self._load_count,
                "checkpoint_count_total": self._checkpoint_count,
                "checkpoints_stored": len(self._checkpoints),
                "diff_count_total": self._diff_count,
                "diffs_stored": len(self._diffs),
                "scene_ops_count": self._scene_ops_count,
                "scene_stack_depth": len(self._scene_stack),
                "active_scene_id": active.scene_id if active else "",
                "states_stored": len(self._states),
                "save_slots_occupied": len(self._save_slots),
                "last_save_time": self._last_save_time,
                "last_load_time": self._last_load_time,
                "uptime_seconds": round(time.time() - self._creation_time, 1),
            }

    def snapshot(self) -> StateManagerSnapshot:
        """Capture a complete snapshot of the state manager's current state."""
        with self._lock:
            active = self.get_active_scene()
            return StateManagerSnapshot(
                save_slots=self.get_save_slots(),
                checkpoint_count=len(self._checkpoints),
                scene_stack_depth=len(self._scene_stack),
                active_scene_id=active.scene_id if active else "",
                stats=self.get_status(),
            )

    def reset(self) -> None:
        """Reset all runtime state while preserving configuration.

        Re-initializes the manager so it can be reused after shutdown.
        """
        with self._lock:
            self._states.clear()
            self._save_slots.clear()
            self._checkpoints.clear()
            self._checkpoint_order.clear()
            self._scene_stack.clear()
            self._diffs.clear()
            self._save_count = 0
            self._load_count = 0
            self._checkpoint_count = 0
            self._diff_count = 0
            self._scene_ops_count = 0
            self._last_save_time = 0.0
            self._last_load_time = 0.0
            self._is_running = True


# ---------------------------------------------------------------------------
# Factory Function
# ---------------------------------------------------------------------------

def get_game_state_manager() -> GameStateManager:
    """Get the GameStateManager singleton instance."""
    return GameStateManager.get_instance()
