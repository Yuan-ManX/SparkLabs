"""
SparkLabs Agent - AI Persistence Architect

A runtime module that designs save-system layouts and orchestrates cloud
sync for the SparkLabs AI-native game engine. The architect manages save
slots across local, cloud, hybrid, and distributed storage tiers, drives
upload/download sync operations, detects and resolves version conflicts,
runs schema migrations with rollback checkpoints, tracks cloud endpoint
health, and produces point-in-time snapshots for backup and restore.

This module embodies the AI-native principle: persistence is not a static
file writer but an intelligent agent that reasons about storage placement,
sync state, conflict resolution strategy, and migration safety while
players are in-session.

Architecture:
  PersistenceArchitect (singleton)
    |-- SaveSlot, SaveSchema, SyncOperation, ConflictRecord,
        MigrationTask, CloudEndpoint, SnapshotManifest,
        PersistenceStats, PersistenceSnapshot, PersistenceEvent
    |-- SaveFormat, SyncState, ConflictResolution, StorageTier,
        MigrationStatus, DataCategory, PersistenceEventKind,
        SyncDirection

Core Capabilities:
  - create_save_slot / get_save_slot / list_save_slots / update_save_slot /
    delete_save_slot: full CRUD over save slot definitions.
  - register_schema / get_schema / list_schemas: versioned save schema
    management with migration lineage tracking.
  - start_sync / get_sync_operation / list_sync_operations / complete_sync:
    cloud sync orchestration with upload/download direction tracking.
  - detect_conflict / resolve_conflict / list_conflicts: version conflict
    detection and resolution across local and remote copies.
  - create_migration / get_migration / list_migrations / complete_migration:
    schema migration execution with rollback checkpoints.
  - register_endpoint / get_endpoint / list_endpoints / check_endpoint_health:
    cloud storage endpoint registration and health probing.
  - create_snapshot / get_snapshot_manifest / list_snapshot_manifests /
    restore_snapshot: point-in-time backup manifests and restoration.
  - list_events / get_stats / get_status / get_snapshot / reset:
    observability and state management.
"""

from __future__ import annotations

import threading
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------------
# Capacity Constants
# ---------------------------------------------------------------------------

_MAX_SLOTS: int = 2000
_MAX_SCHEMAS: int = 100
_MAX_SYNC_OPS: int = 5000
_MAX_CONFLICTS: int = 2000
_MAX_MIGRATIONS: int = 1000
_MAX_ENDPOINTS: int = 100
_MAX_SNAPSHOTS: int = 500
_MAX_EVENTS: int = 5000


# ---------------------------------------------------------------------------
# Helper Functions
# ---------------------------------------------------------------------------


def _now() -> str:
    return datetime.utcnow().isoformat() + "Z"


def _new_id(prefix: str = "") -> str:
    base = uuid.uuid4().hex[:12]
    return f"{prefix}_{base}" if prefix else base


def _parse_version(value: Any) -> int:
    """Parse a version value that may be an int or a string like 'v5'."""
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        digits = "".join(ch for ch in value if ch.isdigit())
        return int(digits) if digits else 0
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def _evict_fifo_dict(store: Dict[Any, Any], max_size: int) -> None:
    cap = max(1, int(max_size))
    while len(store) > cap:
        oldest_key = next(iter(store), None)
        if oldest_key is None:
            break
        store.pop(oldest_key, None)


def _evict_fifo_list(store: List[Any], max_size: int) -> None:
    cap = max(1, int(max_size))
    while len(store) > cap:
        if not store:
            break
        store.pop(0)


def _to_jsonable(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, dict):
        return {str(k): _to_jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_to_jsonable(v) for v in value]
    if hasattr(value, "to_dict") and callable(value.to_dict):
        return _dataclass_to_dict(value)
    return value


def _dataclass_to_dict(instance: Any) -> Dict[str, Any]:
    if instance is None:
        return {}
    if not hasattr(instance, "__dataclass_fields__"):
        return dict(instance) if isinstance(instance, dict) else {}
    out: Dict[str, Any] = {}
    for name in getattr(instance, "__dataclass_fields__", {}).keys():
        try:
            raw = getattr(instance, name)
        except Exception:
            continue
        out[name] = _to_jsonable(raw)
    return out


def _coerce_enum(enum_cls: Any, value: Any, default: Any = None) -> Any:
    """Coerce a raw value into an enum member, falling back to default."""
    if value is None:
        return default
    if isinstance(value, enum_cls):
        return value
    try:
        return enum_cls(value)
    except (ValueError, KeyError):
        return default


def _parse_iso(value: str) -> Optional[datetime]:
    """Parse an ISO-8601 timestamp string into a datetime object."""
    if not value:
        return None
    try:
        cleaned = value.replace("Z", "+00:00") if value.endswith("Z") else value
        return datetime.fromisoformat(cleaned)
    except (ValueError, TypeError):
        return None


# ---------------------------------------------------------------------------
# Domain Enums
# ---------------------------------------------------------------------------


class SaveFormat(Enum):
    JSON = "json"
    BINARY = "binary"
    MSGPACK = "msgpack"
    PROTOBUF = "protobuf"
    CUSTOM = "custom"


class SyncState(Enum):
    IDLE = "idle"
    SYNCING = "syncing"
    SYNCED = "synced"
    CONFLICT = "conflict"
    FAILED = "failed"
    OFFLINE = "offline"


class SyncDirection(Enum):
    UPLOAD = "upload"
    DOWNLOAD = "download"


class ConflictResolution(Enum):
    LATEST_WINS = "latest_wins"
    MERGE = "merge"
    MANUAL = "manual"
    BRANCH = "branch"
    SERVER_WINS = "server_wins"
    CLIENT_WINS = "client_wins"


class StorageTier(Enum):
    LOCAL = "local"
    CLOUD = "cloud"
    HYBRID = "hybrid"
    DISTRIBUTED = "distributed"


class MigrationStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"


class DataCategory(Enum):
    PLAYER_PROGRESS = "player_progress"
    WORLD_STATE = "world_state"
    SETTINGS = "settings"
    INVENTORY = "inventory"
    ACHIEVEMENTS = "achievements"
    CUSTOM_DATA = "custom_data"
    METADATA = "metadata"


class PersistenceEventKind(Enum):
    SAVE_CREATED = "save_created"
    SAVE_LOADED = "save_loaded"
    SAVE_DELETED = "save_deleted"
    SYNC_STARTED = "sync_started"
    SYNC_COMPLETED = "sync_completed"
    SYNC_FAILED = "sync_failed"
    CONFLICT_DETECTED = "conflict_detected"
    CONFLICT_RESOLVED = "conflict_resolved"
    MIGRATION_STARTED = "migration_started"
    MIGRATION_COMPLETED = "migration_completed"
    SCHEMA_UPDATED = "schema_updated"
    SNAPSHOT_CREATED = "snapshot_created"
    SNAPSHOT_RESTORED = "snapshot_restored"


# ---------------------------------------------------------------------------
# Data Classes
# ---------------------------------------------------------------------------


@dataclass
class SaveSlot:
    """A single save slot persisted across one or more storage tiers."""
    slot_id: str
    player_id: str
    game_id: str
    category: DataCategory
    format: SaveFormat
    size_bytes: int = 0
    version: int = 1
    checksum: str = ""
    created_at: str = field(default_factory=_now)
    updated_at: str = field(default_factory=_now)
    storage_tier: StorageTier = StorageTier.LOCAL
    sync_state: SyncState = SyncState.IDLE
    cloud_url: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class SaveSchema:
    """A versioned save schema describing fields, indices, and constraints."""
    schema_id: str
    version: int
    fields: List[Dict[str, Any]] = field(default_factory=list)
    indices: List[str] = field(default_factory=list)
    constraints: List[str] = field(default_factory=list)
    migration_from: int = 0
    migration_to: int = 0
    created_at: str = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class SyncOperation:
    """An upload or download sync operation for a save slot."""
    op_id: str
    slot_id: str
    direction: SyncDirection
    state: SyncState = SyncState.SYNCING
    started_at: str = field(default_factory=_now)
    completed_at: str = ""
    bytes_transferred: int = 0
    error_message: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class ConflictRecord:
    """A version conflict between local and remote save copies."""
    conflict_id: str
    slot_id: str
    local_version: int
    remote_version: int
    local_checksum: str = ""
    remote_checksum: str = ""
    resolution: ConflictResolution = ConflictResolution.MANUAL
    resolved_at: str = ""
    resolved_by: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class MigrationTask:
    """A schema migration task with rollback checkpoint support."""
    task_id: str
    from_version: int
    to_version: int
    status: MigrationStatus = MigrationStatus.PENDING
    started_at: str = field(default_factory=_now)
    completed_at: str = ""
    affected_slots: List[str] = field(default_factory=list)
    error_message: str = ""
    rollback_checkpoint: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class CloudEndpoint:
    """A cloud storage endpoint with health and latency tracking."""
    endpoint_id: str
    provider: str
    region: str
    bucket: str
    access_key_id: str
    endpoint_url: str = ""
    status: str = "active"
    latency_ms: int = 0
    last_health_check: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class SnapshotManifest:
    """A manifest describing a point-in-time snapshot of save slots."""
    manifest_id: str
    snapshot_id: str
    slot_ids: List[str] = field(default_factory=list)
    total_size: int = 0
    created_at: str = field(default_factory=_now)
    checksum: str = ""
    description: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class PersistenceStats:
    """Aggregate statistics for the persistence subsystem."""
    total_slots: int = 0
    total_synced: int = 0
    total_conflicts: int = 0
    total_migrations: int = 0
    total_snapshots: int = 0
    storage_used_bytes: int = 0
    sync_success_rate: float = 0.0
    avg_sync_time_ms: float = 0.0
    last_updated: str = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class PersistenceSnapshot:
    """A full snapshot of the architect's in-memory state."""
    slots: List[Dict[str, Any]] = field(default_factory=list)
    sync_ops: List[Dict[str, Any]] = field(default_factory=list)
    conflicts: List[Dict[str, Any]] = field(default_factory=list)
    migrations: List[Dict[str, Any]] = field(default_factory=list)
    endpoints: List[Dict[str, Any]] = field(default_factory=list)
    snapshots: List[Dict[str, Any]] = field(default_factory=list)
    stats: Dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class PersistenceEvent:
    """An internal audit-log entry recording a persistence state transition."""
    event_id: str
    kind: PersistenceEventKind
    slot_id: str
    timestamp: str
    payload: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


# ---------------------------------------------------------------------------
# Persistence Architect Singleton
# ---------------------------------------------------------------------------


class PersistenceArchitect:
    """AI-native save system designer and cloud sync orchestration agent."""

    _instance: Optional["PersistenceArchitect"] = None
    _inner_lock = threading.RLock()
    _initialized: bool = False

    def __new__(cls) -> "PersistenceArchitect":
        if cls._instance is None:
            with cls._inner_lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    @classmethod
    def get_instance(cls) -> "PersistenceArchitect":
        return cls()

    def __init__(self) -> None:
        if self._initialized:
            return
        with self._inner_lock:
            if self._initialized:
                return
            self._lock = threading.RLock()
            self._slots: Dict[str, SaveSlot] = {}
            self._schemas: Dict[int, SaveSchema] = {}
            self._sync_ops: Dict[str, SyncOperation] = {}
            self._conflicts: Dict[str, ConflictRecord] = {}
            self._migrations: Dict[str, MigrationTask] = {}
            self._endpoints: Dict[str, CloudEndpoint] = {}
            self._snapshots: Dict[str, SnapshotManifest] = {}
            self._events: List[PersistenceEvent] = []
            self._seed_data()
            self._initialized = True

    def _emit(
        self,
        kind: PersistenceEventKind,
        slot_id: str = "",
        payload: Dict[str, Any] = None,
    ) -> None:
        event = PersistenceEvent(
            event_id=_new_id("evt"),
            kind=kind,
            slot_id=slot_id,
            timestamp=_now(),
            payload=payload or {},
        )
        self._events.append(event)
        _evict_fifo_list(self._events, _MAX_EVENTS)

    # ------------------------------------------------------------------
    # Save Slot Management
    # ------------------------------------------------------------------

    def create_save_slot(
        self,
        player_id: str,
        game_id: str = "",
        category: Any = "",
        format: Any = "",
        storage_tier: Any = "",
        metadata: Dict[str, Any] = None,
        slot_id: str = "",
        name: str = "",
    ) -> SaveSlot:
        with self._lock:
            sid = slot_id if slot_id else _new_id("slot")
            meta = dict(metadata or {})
            if name:
                meta["name"] = name
            slot = SaveSlot(
                slot_id=sid,
                player_id=player_id,
                game_id=game_id,
                category=_coerce_enum(DataCategory, category, DataCategory.CUSTOM_DATA),
                format=_coerce_enum(SaveFormat, format, SaveFormat.JSON),
                storage_tier=_coerce_enum(StorageTier, storage_tier, StorageTier.LOCAL),
                size_bytes=int(meta.get("size_bytes", 0)),
                checksum="sha256:" + uuid.uuid4().hex[:16],
                metadata=meta,
            )
            self._slots[slot.slot_id] = slot
            _evict_fifo_dict(self._slots, _MAX_SLOTS)
            self._emit(
                PersistenceEventKind.SAVE_CREATED,
                slot.slot_id,
                {
                    "player_id": player_id,
                    "game_id": game_id,
                    "category": slot.category.value,
                    "format": slot.format.value,
                },
            )
            return slot

    def get_save_slot(self, slot_id: str) -> Optional[SaveSlot]:
        with self._lock:
            return self._slots.get(slot_id)

    def list_save_slots(
        self,
        player_id: str = None,
        game_id: str = None,
        category: DataCategory = None,
        sync_state: SyncState = None,
        limit: int = 100,
    ) -> List[SaveSlot]:
        with self._lock:
            items = list(self._slots.values())
            if player_id is not None:
                items = [s for s in items if s.player_id == player_id]
            if game_id is not None:
                items = [s for s in items if s.game_id == game_id]
            if category is not None:
                cat = _coerce_enum(DataCategory, category)
                items = [s for s in items if s.category == cat]
            if sync_state is not None:
                st = _coerce_enum(SyncState, sync_state)
                items = [s for s in items if s.sync_state == st]
            return items[-limit:]

    def update_save_slot(self, slot_id: str, **kwargs: Any) -> Optional[SaveSlot]:
        with self._lock:
            slot = self._slots.get(slot_id)
            if slot is None:
                return None
            for k, v in kwargs.items():
                if k in ("slot_id", "created_at"):
                    continue
                if k == "category":
                    v = _coerce_enum(DataCategory, v, slot.category)
                elif k == "format":
                    v = _coerce_enum(SaveFormat, v, slot.format)
                elif k == "storage_tier":
                    v = _coerce_enum(StorageTier, v, slot.storage_tier)
                elif k == "sync_state":
                    v = _coerce_enum(SyncState, v, slot.sync_state)
                if hasattr(slot, k):
                    setattr(slot, k, v)
            slot.updated_at = _now()
            self._emit(PersistenceEventKind.SAVE_LOADED, slot_id, {"updated": True})
            return slot

    def delete_save_slot(self, slot_id: str) -> bool:
        with self._lock:
            if slot_id not in self._slots:
                return False
            del self._slots[slot_id]
            self._emit(PersistenceEventKind.SAVE_DELETED, slot_id, {})
            return True

    # ------------------------------------------------------------------
    # Schema Management
    # ------------------------------------------------------------------

    def register_schema(
        self,
        version: Any,
        fields: Any = None,
        indices: Any = None,
        constraints: Any = None,
        migration_from: Any = 0,
    ) -> SaveSchema:
        with self._lock:
            ver = _parse_version(version)
            mig_from = _parse_version(migration_from) if migration_from else 0
            migration_to = ver if mig_from else 0
            schema = SaveSchema(
                schema_id=_new_id("sch"),
                version=ver,
                fields=list(fields or []),
                indices=list(indices or []),
                constraints=list(constraints or []),
                migration_from=mig_from,
                migration_to=migration_to,
            )
            self._schemas[schema.version] = schema
            _evict_fifo_dict(self._schemas, _MAX_SCHEMAS)
            self._emit(
                PersistenceEventKind.SCHEMA_UPDATED,
                "",
                {"version": schema.version, "migration_from": schema.migration_from},
            )
            return schema

    def get_schema(self, version: Any) -> Optional[SaveSchema]:
        with self._lock:
            return self._schemas.get(_parse_version(version))

    def list_schemas(self) -> List[SaveSchema]:
        with self._lock:
            return list(self._schemas.values())

    # ------------------------------------------------------------------
    # Sync Orchestration
    # ------------------------------------------------------------------

    def start_sync(self, slot_id: str, direction: Any = "upload", endpoint_id: str = "") -> SyncOperation:
        with self._lock:
            slot = self._slots.get(slot_id)
            if slot is None:
                return None  # type: ignore[return-value]
            direction = _coerce_enum(SyncDirection, direction, SyncDirection.UPLOAD)
            op = SyncOperation(
                op_id=_new_id("syn"),
                slot_id=slot_id,
                direction=direction,
                state=SyncState.SYNCING,
            )
            self._sync_ops[op.op_id] = op
            _evict_fifo_dict(self._sync_ops, _MAX_SYNC_OPS)
            slot.sync_state = SyncState.SYNCING
            slot.updated_at = _now()
            self._emit(
                PersistenceEventKind.SYNC_STARTED,
                slot_id,
                {"op_id": op.op_id, "direction": direction.value},
            )
            return op

    def get_sync_operation(self, op_id: str) -> Optional[SyncOperation]:
        with self._lock:
            return self._sync_ops.get(op_id)

    def list_sync_operations(
        self,
        slot_id: str = None,
        state: SyncState = None,
        limit: int = 100,
    ) -> List[SyncOperation]:
        with self._lock:
            items = list(self._sync_ops.values())
            if slot_id is not None:
                items = [o for o in items if o.slot_id == slot_id]
            if state is not None:
                st = _coerce_enum(SyncState, state)
                items = [o for o in items if o.state == st]
            return items[-limit:]

    def complete_sync(
        self,
        op_id: str,
        bytes_transferred: Any = 0,
        error_message: str = "",
    ) -> SyncOperation:
        with self._lock:
            op = self._sync_ops.get(op_id)
            if op is None:
                return None  # type: ignore[return-value]
            try:
                op.bytes_transferred = int(bytes_transferred) if bytes_transferred else 0
            except (TypeError, ValueError):
                op.bytes_transferred = 0
            op.error_message = error_message or ""
            op.completed_at = _now()
            if op.error_message:
                op.state = SyncState.FAILED
            else:
                op.state = SyncState.SYNCED
            slot = self._slots.get(op.slot_id)
            if slot is not None:
                slot.sync_state = op.state
                slot.updated_at = _now()
            if op.error_message:
                self._emit(
                    PersistenceEventKind.SYNC_FAILED,
                    op.slot_id,
                    {"op_id": op_id, "error": op.error_message},
                )
            else:
                self._emit(
                    PersistenceEventKind.SYNC_COMPLETED,
                    op.slot_id,
                    {"op_id": op_id, "bytes": op.bytes_transferred},
                )
            return op

    # ------------------------------------------------------------------
    # Conflict Detection and Resolution
    # ------------------------------------------------------------------

    def detect_conflict(
        self,
        slot_id: str,
        local_version: int,
        remote_version: int,
        local_checksum: str = "",
        remote_checksum: str = "",
    ) -> ConflictRecord:
        with self._lock:
            conflict = ConflictRecord(
                conflict_id=_new_id("cfl"),
                slot_id=slot_id,
                local_version=int(local_version),
                remote_version=int(remote_version),
                local_checksum=local_checksum,
                remote_checksum=remote_checksum,
                resolution=ConflictResolution.MANUAL,
            )
            self._conflicts[conflict.conflict_id] = conflict
            _evict_fifo_dict(self._conflicts, _MAX_CONFLICTS)
            slot = self._slots.get(slot_id)
            if slot is not None:
                slot.sync_state = SyncState.CONFLICT
                slot.updated_at = _now()
            self._emit(
                PersistenceEventKind.CONFLICT_DETECTED,
                slot_id,
                {
                    "conflict_id": conflict.conflict_id,
                    "local_version": conflict.local_version,
                    "remote_version": conflict.remote_version,
                },
            )
            return conflict

    def resolve_conflict(
        self,
        conflict_id: str,
        resolution: ConflictResolution,
        resolved_by: str = "",
    ) -> ConflictRecord:
        with self._lock:
            conflict = self._conflicts.get(conflict_id)
            if conflict is None:
                return None  # type: ignore[return-value]
            conflict.resolution = _coerce_enum(
                ConflictResolution, resolution, ConflictResolution.MANUAL
            )
            conflict.resolved_by = resolved_by
            conflict.resolved_at = _now()
            slot = self._slots.get(conflict.slot_id)
            if slot is not None:
                slot.sync_state = SyncState.SYNCED
                slot.updated_at = _now()
            self._emit(
                PersistenceEventKind.CONFLICT_RESOLVED,
                conflict.slot_id,
                {
                    "conflict_id": conflict_id,
                    "resolution": conflict.resolution.value,
                    "resolved_by": resolved_by,
                },
            )
            return conflict

    def list_conflicts(
        self,
        slot_id: str = None,
        limit: int = 100,
    ) -> List[ConflictRecord]:
        with self._lock:
            items = list(self._conflicts.values())
            if slot_id is not None:
                items = [c for c in items if c.slot_id == slot_id]
            return items[-limit:]

    # ------------------------------------------------------------------
    # Schema Migration
    # ------------------------------------------------------------------

    def create_migration(
        self,
        from_version: Any,
        to_version: Any,
        affected_slots: Any = None,
        description: str = "",
    ) -> MigrationTask:
        with self._lock:
            task = MigrationTask(
                task_id=_new_id("mig"),
                from_version=_parse_version(from_version),
                to_version=_parse_version(to_version),
                status=MigrationStatus.RUNNING,
                affected_slots=list(affected_slots or []),
                rollback_checkpoint="ckpt_" + uuid.uuid4().hex[:10],
            )
            self._migrations[task.task_id] = task
            _evict_fifo_dict(self._migrations, _MAX_MIGRATIONS)
            self._emit(
                PersistenceEventKind.MIGRATION_STARTED,
                "",
                {
                    "task_id": task.task_id,
                    "from_version": task.from_version,
                    "to_version": task.to_version,
                    "affected_slots": task.affected_slots,
                },
            )
            return task

    def get_migration(self, task_id: str) -> Optional[MigrationTask]:
        with self._lock:
            return self._migrations.get(task_id)

    def list_migrations(
        self,
        status: MigrationStatus = None,
        limit: int = 100,
    ) -> List[MigrationTask]:
        with self._lock:
            items = list(self._migrations.values())
            if status is not None:
                st = _coerce_enum(MigrationStatus, status)
                items = [m for m in items if m.status == st]
            return items[-limit:]

    def complete_migration(
        self,
        task_id: str,
        error_message: str = "",
        rollback_checkpoint: str = "",
    ) -> MigrationTask:
        with self._lock:
            task = self._migrations.get(task_id)
            if task is None:
                return None  # type: ignore[return-value]
            task.error_message = error_message or ""
            task.rollback_checkpoint = rollback_checkpoint or task.rollback_checkpoint
            task.completed_at = _now()
            if task.error_message:
                task.status = MigrationStatus.FAILED
            else:
                task.status = MigrationStatus.COMPLETED
                # Bump affected slots to the target schema version.
                for slot_id in task.affected_slots:
                    slot = self._slots.get(slot_id)
                    if slot is not None:
                        slot.version = task.to_version
                        slot.updated_at = _now()
            self._emit(
                PersistenceEventKind.MIGRATION_COMPLETED,
                "",
                {
                    "task_id": task_id,
                    "status": task.status.value,
                    "error": task.error_message,
                },
            )
            return task

    # ------------------------------------------------------------------
    # Cloud Endpoint Management
    # ------------------------------------------------------------------

    def register_endpoint(
        self,
        provider: str = "",
        region: str = "",
        bucket: str = "",
        access_key_id: str = "",
        endpoint_url: str = "",
        endpoint_id: str = "",
        name: str = "",
        url: str = "",
        tier: str = "",
    ) -> CloudEndpoint:
        with self._lock:
            eid = endpoint_id if endpoint_id else _new_id("ep")
            ep_url = url if url else endpoint_url
            ep_provider = name if name else provider
            endpoint = CloudEndpoint(
                endpoint_id=eid,
                provider=ep_provider,
                region=region,
                bucket=bucket,
                access_key_id=access_key_id,
                endpoint_url=ep_url,
                status=tier if tier else "active",
            )
            self._endpoints[endpoint.endpoint_id] = endpoint
            _evict_fifo_dict(self._endpoints, _MAX_ENDPOINTS)
            return endpoint

    def get_endpoint(self, endpoint_id: str) -> Optional[CloudEndpoint]:
        with self._lock:
            return self._endpoints.get(endpoint_id)

    def list_endpoints(
        self,
        status: str = None,
        limit: int = 100,
    ) -> List[CloudEndpoint]:
        with self._lock:
            items = list(self._endpoints.values())
            if status is not None:
                items = [e for e in items if e.status == status]
            return items[-limit:]

    def check_endpoint_health(self, endpoint_id: str) -> CloudEndpoint:
        with self._lock:
            endpoint = self._endpoints.get(endpoint_id)
            if endpoint is None:
                return None  # type: ignore[return-value]
            # Simulated latency probe derived from a stable ordinal sum so
            # results stay deterministic for a given endpoint id.
            ordinal_sum = sum(ord(c) for c in (endpoint_id or ""))
            latency = (ordinal_sum % 300) + 10
            endpoint.latency_ms = latency
            endpoint.last_health_check = _now()
            if latency < 100:
                endpoint.status = "active"
            elif latency < 250:
                endpoint.status = "degraded"
            else:
                endpoint.status = "offline"
            return endpoint

    # ------------------------------------------------------------------
    # Snapshot Management
    # ------------------------------------------------------------------

    def create_snapshot(
        self,
        slot_ids: List[str],
        description: str = "",
    ) -> SnapshotManifest:
        with self._lock:
            resolved_ids: List[str] = list(slot_ids or [])
            total_size = 0
            for slot_id in resolved_ids:
                slot = self._slots.get(slot_id)
                if slot is not None:
                    total_size += slot.size_bytes
            manifest = SnapshotManifest(
                manifest_id=_new_id("man"),
                snapshot_id=_new_id("snap"),
                slot_ids=resolved_ids,
                total_size=total_size,
                checksum="sha256:" + uuid.uuid4().hex[:16],
                description=description,
            )
            self._snapshots[manifest.manifest_id] = manifest
            _evict_fifo_dict(self._snapshots, _MAX_SNAPSHOTS)
            self._emit(
                PersistenceEventKind.SNAPSHOT_CREATED,
                "",
                {
                    "manifest_id": manifest.manifest_id,
                    "slot_count": len(resolved_ids),
                    "total_size": total_size,
                },
            )
            return manifest

    def get_snapshot_manifest(self, manifest_id: str) -> Optional[SnapshotManifest]:
        with self._lock:
            return self._snapshots.get(manifest_id)

    def list_snapshot_manifests(self, limit: int = 100) -> List[SnapshotManifest]:
        with self._lock:
            items = list(self._snapshots.values())
            return items[-limit:]

    def restore_snapshot(self, manifest_id: str) -> bool:
        with self._lock:
            manifest = self._snapshots.get(manifest_id)
            if manifest is None:
                return False
            # Mark referenced slots as synced and refreshed to reflect a
            # successful restore from the snapshot point.
            for slot_id in manifest.slot_ids:
                slot = self._slots.get(slot_id)
                if slot is not None:
                    slot.sync_state = SyncState.SYNCED
                    slot.updated_at = _now()
            self._emit(
                PersistenceEventKind.SNAPSHOT_RESTORED,
                "",
                {"manifest_id": manifest_id, "slot_count": len(manifest.slot_ids)},
            )
            return True

    # ------------------------------------------------------------------
    # Observability
    # ------------------------------------------------------------------

    def list_events(
        self,
        limit: int = 100,
        kind: PersistenceEventKind = None,
    ) -> List[PersistenceEvent]:
        with self._lock:
            items = list(self._events)
            if kind is not None:
                k = _coerce_enum(PersistenceEventKind, kind)
                items = [e for e in items if e.kind == k]
            return items[-limit:]

    def get_stats(self) -> PersistenceStats:
        with self._lock:
            total_slots = len(self._slots)
            total_synced = sum(
                1 for s in self._slots.values() if s.sync_state == SyncState.SYNCED
            )
            storage_used = sum(s.size_bytes for s in self._slots.values())

            successful = sum(
                1 for o in self._sync_ops.values() if o.state == SyncState.SYNCED
            )
            failed = sum(
                1 for o in self._sync_ops.values() if o.state == SyncState.FAILED
            )
            settled = successful + failed
            sync_success_rate = (successful / settled) if settled else 0.0

            durations: List[float] = []
            for o in self._sync_ops.values():
                if not o.completed_at:
                    continue
                start = _parse_iso(o.started_at)
                end = _parse_iso(o.completed_at)
                if start is None or end is None:
                    continue
                durations.append((end - start).total_seconds() * 1000.0)
            avg_sync_time_ms = (sum(durations) / len(durations)) if durations else 0.0

            return PersistenceStats(
                total_slots=total_slots,
                total_synced=total_synced,
                total_conflicts=len(self._conflicts),
                total_migrations=len(self._migrations),
                total_snapshots=len(self._snapshots),
                storage_used_bytes=storage_used,
                sync_success_rate=round(sync_success_rate, 4),
                avg_sync_time_ms=round(avg_sync_time_ms, 2),
                last_updated=_now(),
            )

    def get_status(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "initialized": self._initialized,
                "slots": len(self._slots),
                "schemas": len(self._schemas),
                "sync_operations": len(self._sync_ops),
                "conflicts": len(self._conflicts),
                "migrations": len(self._migrations),
                "endpoints": len(self._endpoints),
                "snapshots": len(self._snapshots),
                "events": len(self._events),
            }

    def get_snapshot(self) -> PersistenceSnapshot:
        with self._lock:
            return PersistenceSnapshot(
                slots=[s.to_dict() for s in list(self._slots.values())[:20]],
                sync_ops=[o.to_dict() for o in list(self._sync_ops.values())[:20]],
                conflicts=[c.to_dict() for c in list(self._conflicts.values())[:20]],
                migrations=[m.to_dict() for m in list(self._migrations.values())[:20]],
                endpoints=[e.to_dict() for e in list(self._endpoints.values())[:20]],
                snapshots=[m.to_dict() for m in list(self._snapshots.values())[:20]],
                stats=self.get_stats().to_dict(),
            )

    def reset(self) -> None:
        with self._lock:
            self._slots.clear()
            self._schemas.clear()
            self._sync_ops.clear()
            self._conflicts.clear()
            self._migrations.clear()
            self._endpoints.clear()
            self._snapshots.clear()
            self._events.clear()
            self._seed_data()

    # ------------------------------------------------------------------
    # Seed Data
    # ------------------------------------------------------------------

    def _seed_data(self) -> None:
        # Save slot 1: player progress, JSON, hybrid tier, already synced.
        slot_progress = SaveSlot(
            slot_id="slot_seed_progress",
            player_id="player_001",
            game_id="game_sparklabs",
            category=DataCategory.PLAYER_PROGRESS,
            format=SaveFormat.JSON,
            size_bytes=24576,
            version=2,
            checksum="sha256:a1b2c3d4e5f60718",
            storage_tier=StorageTier.HYBRID,
            sync_state=SyncState.SYNCED,
            cloud_url="s3://sparklabs-saves/player_001/progress.json",
            metadata={
                "level": 42,
                "playtime_hours": 87.5,
                "last_chapter": 7,
                "size_bytes": 24576,
            },
        )
        self._slots[slot_progress.slot_id] = slot_progress

        # Save slot 2: world state, binary, cloud tier, already synced.
        slot_world = SaveSlot(
            slot_id="slot_seed_world",
            player_id="player_001",
            game_id="game_sparklabs",
            category=DataCategory.WORLD_STATE,
            format=SaveFormat.BINARY,
            size_bytes=131072,
            version=1,
            checksum="sha256:d4e5f6a7b8c90102",
            storage_tier=StorageTier.CLOUD,
            sync_state=SyncState.SYNCED,
            cloud_url="s3://sparklabs-saves/player_001/world.bin",
            metadata={
                "seed": 987654,
                "chunks": 1024,
                "biome": "archipelago",
                "size_bytes": 131072,
            },
        )
        self._slots[slot_world.slot_id] = slot_world

        # Save slot 3: settings, JSON, local tier, idle sync state.
        slot_settings = SaveSlot(
            slot_id="slot_seed_settings",
            player_id="player_002",
            game_id="game_sparklabs",
            category=DataCategory.SETTINGS,
            format=SaveFormat.JSON,
            size_bytes=2048,
            version=1,
            checksum="sha256:g7h8i9j0k1l2m3n4",
            storage_tier=StorageTier.LOCAL,
            sync_state=SyncState.IDLE,
            cloud_url="",
            metadata={
                "graphics": "ultra",
                "volume": 0.8,
                "size_bytes": 2048,
            },
        )
        self._slots[slot_settings.slot_id] = slot_settings

        # Schema 1: initial v1 layout.
        schema_v1 = SaveSchema(
            schema_id="sch_seed_v1",
            version=1,
            fields=[
                {"name": "player_id", "type": "string"},
                {"name": "progress", "type": "object"},
                {"name": "timestamp", "type": "int64"},
            ],
            indices=["player_id"],
            constraints=["player_id NOT NULL"],
            migration_from=0,
            migration_to=0,
            created_at="2026-06-01T00:00:00Z",
        )
        self._schemas[schema_v1.version] = schema_v1

        # Schema 2: v2 layout migrated from v1 with an added inventory field.
        schema_v2 = SaveSchema(
            schema_id="sch_seed_v2",
            version=2,
            fields=[
                {"name": "player_id", "type": "string"},
                {"name": "progress", "type": "object"},
                {"name": "inventory", "type": "object"},
                {"name": "timestamp", "type": "int64"},
            ],
            indices=["player_id", "timestamp"],
            constraints=["player_id NOT NULL", "timestamp >= 0"],
            migration_from=1,
            migration_to=2,
            created_at="2026-06-20T00:00:00Z",
        )
        self._schemas[schema_v2.version] = schema_v2

        # Sync operation 1: completed upload of the progress slot.
        sync_op = SyncOperation(
            op_id="syn_seed_upload",
            slot_id="slot_seed_progress",
            direction=SyncDirection.UPLOAD,
            state=SyncState.SYNCED,
            started_at="2026-07-03T10:00:00Z",
            completed_at="2026-07-03T10:00:01Z",
            bytes_transferred=24576,
            error_message="",
        )
        self._sync_ops[sync_op.op_id] = sync_op

        # Conflict 1: already resolved in favor of the server copy.
        conflict = ConflictRecord(
            conflict_id="cfl_seed_001",
            slot_id="slot_seed_world",
            local_version=1,
            remote_version=2,
            local_checksum="sha256:localabc123",
            remote_checksum="sha256:remotexyz456",
            resolution=ConflictResolution.SERVER_WINS,
            resolved_at="2026-07-03T10:05:00Z",
            resolved_by="auto_resolver",
        )
        self._conflicts[conflict.conflict_id] = conflict

        # Migration 1: completed migration from v1 to v2.
        migration = MigrationTask(
            task_id="mig_seed_001",
            from_version=1,
            to_version=2,
            status=MigrationStatus.COMPLETED,
            started_at="2026-07-03T09:00:00Z",
            completed_at="2026-07-03T09:02:30Z",
            affected_slots=["slot_seed_progress", "slot_seed_world"],
            error_message="",
            rollback_checkpoint="ckpt_20260703_0900",
        )
        self._migrations[migration.task_id] = migration

        # Endpoint 1: AWS S3 in us-east-1.
        endpoint_aws = CloudEndpoint(
            endpoint_id="ep_seed_aws",
            provider="aws",
            region="us-east-1",
            bucket="sparklabs-saves",
            access_key_id="AKIAIOSFODNN7EXAMPLE",
            endpoint_url="https://s3.us-east-1.amazonaws.com",
            status="active",
            latency_ms=42,
            last_health_check="2026-07-03T10:30:00Z",
        )
        self._endpoints[endpoint_aws.endpoint_id] = endpoint_aws

        # Endpoint 2: GCP Storage in us-central1.
        endpoint_gcp = CloudEndpoint(
            endpoint_id="ep_seed_gcp",
            provider="gcp",
            region="us-central1",
            bucket="sparklabs-saves-gcp",
            access_key_id="GOOGEXAMPLEKEYID",
            endpoint_url="https://storage.googleapis.com",
            status="active",
            latency_ms=88,
            last_health_check="2026-07-03T10:30:00Z",
        )
        self._endpoints[endpoint_gcp.endpoint_id] = endpoint_gcp

        # Snapshot manifest 1: daily backup across all seed slots.
        manifest = SnapshotManifest(
            manifest_id="man_seed_001",
            snapshot_id="snap_20260703",
            slot_ids=[
                "slot_seed_progress",
                "slot_seed_world",
                "slot_seed_settings",
            ],
            total_size=24576 + 131072 + 2048,
            created_at="2026-07-03T11:00:00Z",
            checksum="sha256:manifestabc123456",
            description="Daily backup snapshot for all seed save slots",
        )
        self._snapshots[manifest.manifest_id] = manifest


def get_persistence_architect() -> PersistenceArchitect:
    """Factory function returning the singleton PersistenceArchitect instance."""
    return PersistenceArchitect.get_instance()
