"""
SparkLabs Engine - Cross-Platform Cloud Save System

Synchronizes game save data across devices for the SparkLabs AI-native game
engine. The system handles save slot management, incremental chunk sync,
conflict detection and resolution, version tracking, cloud storage quotas,
compression and encryption of payloads, snapshot backups, and audit events.

Architecture:
  CloudSaveSystem (thread-safe singleton)
    |-- SaveSlot              (per-slot save metadata and snapshot)
    |-- SaveDataChunk         (incremental typed data block within a slot)
    |-- SyncOperation         (upload / download / sync lifecycle record)
    |-- ConflictRecord        (local-vs-cloud divergence needing resolution)
    |-- CloudStorageQuota     (per-player cloud storage budget)
    |-- CloudSaveConfig       (tunable engine configuration)
    |-- CloudSaveStats        (aggregate engine statistics)
    |-- CloudSaveSnapshot     (immutable point-in-time state capture)
    |-- CloudSaveEvent        (audit log entry)

Core Capabilities:
  - register_save_slot / update_save_slot / remove_save_slot: Slot lifecycle
  - save_data / get_save_data / load_save_data / delete_save_data: Chunk I/O
  - upload_to_cloud / download_from_cloud / sync_slot / sync_player: Sync flow
  - detect_conflict / list_conflicts / resolve_conflict: Conflict handling
  - get_quota / update_quota: Per-player storage budgets
  - calculate_data_hash / compress_data / encrypt_data: Payload utilities
  - create_snapshot_backup / list_backups / restore_backup: Backup management
  - list_events / get_status / get_stats / get_snapshot / get_config /
    set_config / tick / reset: Observability and lifecycle

Thread-safety:
  All public mutators and accessors acquire the engine-wide reentrant lock.
  Use get_cloud_save_system() to obtain the singleton instance.
"""

from __future__ import annotations

import base64
import gzip
import hashlib
import json
import threading
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Capacity Constants
# ---------------------------------------------------------------------------

# Maximum number of save slots retained across all players.
_MAX_SAVE_SLOTS: int = 10000
# Maximum number of save data chunks retained across all slots.
_MAX_SAVE_CHUNKS: int = 50000
# Maximum number of sync operation records kept for auditing.
_MAX_SYNC_OPERATIONS: int = 20000
# Maximum number of unresolved conflict records retained.
_MAX_CONFLICTS: int = 5000
# Maximum number of per-player quota records.
_MAX_QUOTAS: int = 10000
# Maximum number of snapshot backups retained.
_MAX_BACKUPS: int = 5000
# Maximum number of audit events retained in the FIFO event log.
_MAX_EVENTS: int = 5000
# Default per-player cloud storage quota in bytes (100 MB).
_DEFAULT_QUOTA_BYTES: int = 100 * 1024 * 1024
# Fixed key material used by the XOR / AES fallback ciphers.
_XOR_KEY: bytes = b"sparklabs-cloud-save-default-key-2026"


# ---------------------------------------------------------------------------
# Helper Functions
# ---------------------------------------------------------------------------


def _now() -> str:
    return datetime.utcnow().isoformat() + "Z"


def _new_id(prefix: str = "") -> str:
    base = uuid.uuid4().hex[:12]
    return f"{prefix}_{base}" if prefix else base


def _evict_fifo_dict(store: Dict[str, Any], max_size: int) -> None:
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


def _coerce_enum(enum_cls: Any, value: Any, default: Any = None) -> Any:
    if value is None:
        return default
    if isinstance(value, enum_cls):
        return value
    try:
        return enum_cls(value)
    except (ValueError, KeyError):
        return default


def _to_jsonable(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, dict):
        return {str(k): _to_jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_to_jsonable(v) for v in value]
    if hasattr(value, "__dataclass_fields__"):
        return _dataclass_to_dict(value)
    if hasattr(value, "to_dict") and callable(value.to_dict):
        return value.to_dict()
    return value


def _dataclass_to_dict(instance: Any) -> Dict[str, Any]:
    if instance is None:
        return {}
    if not hasattr(instance, "__dataclass_fields__"):
        if isinstance(instance, dict):
            return {str(k): _to_jsonable(v) for k, v in instance.items()}
        if hasattr(instance, "to_dict") and callable(instance.to_dict):
            return instance.to_dict()
        return {}
    out: Dict[str, Any] = {}
    for name in getattr(instance, "__dataclass_fields__", {}).keys():
        try:
            raw = getattr(instance, name)
        except Exception:
            continue
        out[name] = _to_jsonable(raw)
    return out


def _serialize_bytes(data: Any) -> bytes:
    """Convert arbitrary data into a bytes payload for hashing, compression,
    and encryption pipelines."""
    if data is None:
        return b""
    if isinstance(data, bytes):
        return data
    if isinstance(data, bytearray):
        return bytes(data)
    if isinstance(data, str):
        return data.encode("utf-8")
    return json.dumps(_to_jsonable(data), sort_keys=True, ensure_ascii=False).encode("utf-8")


def _deserialize_bytes(raw: bytes) -> Any:
    """Best-effort reverse of _serialize_bytes; returns parsed JSON when the
    payload is valid JSON, otherwise the original bytes or decoded string."""
    if not raw:
        return None
    try:
        return json.loads(raw.decode("utf-8"))
    except Exception:
        try:
            return raw.decode("utf-8")
        except Exception:
            return raw


def _xor_bytes(data: bytes, key: bytes) -> bytes:
    """Apply a repeating-key XOR transform. Symmetric: encrypt and decrypt."""
    if not key:
        return data
    kl = len(key)
    return bytes(b ^ key[i % kl] for i, b in enumerate(data))


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        if value is None:
            return default
        return int(value)
    except (TypeError, ValueError):
        return default


# ---------------------------------------------------------------------------
# Domain Enums
# ---------------------------------------------------------------------------


class SaveSlotType(str, Enum):
    """Categorizes the origin intent of a save slot."""

    MANUAL = "manual"
    AUTOMATIC = "automatic"
    CHECKPOINT = "checkpoint"
    QUICK_SAVE = "quick_save"
    STORY_MILESTONE = "story_milestone"


class SyncStatus(str, Enum):
    """Lifecycle state of a slot or sync operation relative to the cloud."""

    SYNCED = "synced"
    PENDING_UPLOAD = "pending_upload"
    PENDING_DOWNLOAD = "pending_download"
    CONFLICT = "conflict"
    OFFLINE = "offline"
    ERROR = "error"


class ConflictResolution(str, Enum):
    """Strategies available for resolving a local-versus-cloud divergence."""

    KEEP_CLOUD = "keep_cloud"
    KEEP_LOCAL = "keep_local"
    MERGE = "merge"
    MANUAL_REVIEW = "manual_review"
    KEEP_NEWEST = "keep_newest"


class PlatformType(str, Enum):
    """Target runtime platforms for cross-device save synchronization."""

    PC = "pc"
    MAC = "mac"
    IOS = "ios"
    ANDROID = "android"
    CONSOLE = "console"
    WEB = "web"


class SaveDataType(str, Enum):
    """Logical partitioning of save payload chunks."""

    GAME_STATE = "game_state"
    PLAYER_PROGRESS = "player_progress"
    SETTINGS = "settings"
    INVENTORY = "inventory"
    ACHIEVEMENTS = "achievements"
    WORLD_STATE = "world_state"
    CHARACTER_DATA = "character_data"
    UNLOCKED_CONTENT = "unlocked_content"


class CompressionType(str, Enum):
    """Payload compression algorithms supported by the save pipeline."""

    NONE = "none"
    GZIP = "gzip"
    ZSTD = "zstd"
    LZ4 = "lz4"


class EncryptionType(str, Enum):
    """Payload encryption schemes supported by the save pipeline."""

    NONE = "none"
    AES256 = "aes256"
    XOR = "xor"


# ---------------------------------------------------------------------------
# Data Classes
# ---------------------------------------------------------------------------


@dataclass
class SaveSlot:
    """A single save slot owned by a player, with cloud sync metadata."""

    slot_id: str
    player_id: str
    slot_name: str
    slot_type: SaveSlotType
    game_version: str
    platform: PlatformType
    data_hash: str = ""
    data_size_bytes: int = 0
    compression: CompressionType = CompressionType.GZIP
    encryption: EncryptionType = EncryptionType.AES256
    created_at: str = field(default_factory=_now)
    modified_at: str = field(default_factory=_now)
    sync_status: SyncStatus = SyncStatus.PENDING_UPLOAD
    cloud_version: int = 0
    local_version: int = 1
    data_snapshot: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class SaveDataChunk:
    """An incremental typed data block stored within a save slot."""

    chunk_id: str
    slot_id: str
    data_type: SaveDataType
    chunk_data: Any
    chunk_hash: str = ""
    chunk_size: int = 0
    offset: int = 0
    is_compressed: bool = False
    is_encrypted: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class SyncOperation:
    """A single upload / download / sync lifecycle record."""

    operation_id: str
    player_id: str
    slot_id: str
    operation_type: str
    source_platform: PlatformType
    target_platform: PlatformType
    status: SyncStatus
    started_at: str = field(default_factory=_now)
    completed_at: str = ""
    data_delta: int = 0
    conflict_type: str = ""
    resolution: ConflictResolution = ConflictResolution.MANUAL_REVIEW
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class ConflictRecord:
    """A detected divergence between local and cloud save versions."""

    conflict_id: str
    slot_id: str
    player_id: str
    local_version: int
    cloud_version: int
    local_timestamp: str
    cloud_timestamp: str
    local_data_hash: str
    cloud_data_hash: str
    resolution: ConflictResolution = ConflictResolution.MANUAL_REVIEW
    resolved: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class CloudStorageQuota:
    """Per-player cloud storage budget tracking."""

    player_id: str
    total_quota_bytes: int
    used_bytes: int = 0
    available_bytes: int = 0
    save_count: int = 0
    last_calculated: str = field(default_factory=_now)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class CloudSaveConfig:
    """Tunable configuration for the cloud save engine."""

    max_save_slots_per_player: int = 50
    max_data_size_mb: int = 100
    auto_sync_enabled: bool = True
    sync_interval_seconds: int = 300
    conflict_resolution_strategy: ConflictResolution = ConflictResolution.KEEP_NEWEST
    compression_type: CompressionType = CompressionType.GZIP
    encryption_type: EncryptionType = EncryptionType.AES256
    max_versions_to_keep: int = 10
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class CloudSaveStats:
    """Aggregate statistics describing engine activity."""

    total_slots: int = 0
    synced_slots: int = 0
    pending_slots: int = 0
    conflict_slots: int = 0
    total_syncs: int = 0
    successful_syncs: int = 0
    failed_syncs: int = 0
    total_data_transferred: int = 0
    tick_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class CloudSaveSnapshot:
    """Immutable point-in-time capture of the entire engine state."""

    timestamp: str = field(default_factory=_now)
    slots: List[SaveSlot] = field(default_factory=list)
    sync_operations: List[SyncOperation] = field(default_factory=list)
    conflicts: List[ConflictRecord] = field(default_factory=list)
    quotas: List[CloudStorageQuota] = field(default_factory=list)
    stats: CloudSaveStats = field(default_factory=CloudSaveStats)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class CloudSaveEvent:
    """A single audit log entry produced by save engine operations."""

    event_id: str
    event_type: str
    timestamp: str = field(default_factory=_now)
    slot_id: str = ""
    player_id: str = ""
    data: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


# ---------------------------------------------------------------------------
# Main System (Singleton)
# ---------------------------------------------------------------------------


class CloudSaveSystem:
    """
    Central engine for cross-platform cloud save synchronization.

    Thread-safe via a reentrant lock. Use get_cloud_save_system() or
    CloudSaveSystem.get_instance() to obtain the singleton.

    Usage:
        engine = get_cloud_save_system()
        ok, msg, slot = engine.register_save_slot(
            "slot_1", "player_001", "Forest Camp", slot_type="manual"
        )
        engine.save_data("slot_1", SaveDataType.GAME_STATE, {"hp": 100})
        engine.upload_to_cloud("slot_1")
    """

    _instance: Optional["CloudSaveSystem"] = None
    _lock: threading.RLock = threading.RLock()
    _init_lock: threading.RLock = threading.RLock()

    def __new__(cls) -> "CloudSaveSystem":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    instance = super().__new__(cls)
                    instance._initialized = False
                    cls._instance = instance
        return cls._instance

    def __init__(self) -> None:
        if self._initialized:
            return
        with self._lock:
            if self._initialized:
                return
            self._init_stores()
            self._seed()

    # ------------------------------------------------------------------
    # Store Initialization
    # ------------------------------------------------------------------

    def _init_stores(self) -> None:
        """Allocate all in-memory stores and reset aggregate counters."""
        # Save slots keyed by slot_id.
        self._slots: Dict[str, SaveSlot] = {}
        # Save data chunks keyed by chunk_id.
        self._chunks: Dict[str, SaveDataChunk] = {}
        # Sync operation records keyed by operation_id.
        self._sync_operations: Dict[str, SyncOperation] = {}
        # Conflict records keyed by conflict_id.
        self._conflicts: Dict[str, ConflictRecord] = {}
        # Per-player storage quotas keyed by player_id.
        self._quotas: Dict[str, CloudStorageQuota] = {}
        # Snapshot backups keyed by backup_slot_id.
        self._backups: Dict[str, SaveSlot] = {}
        # Audit events kept in FIFO order with capacity eviction.
        self._events: List[CloudSaveEvent] = []

        # Aggregate counters maintained for fast stats retrieval.
        self._total_syncs: int = 0
        self._successful_syncs: int = 0
        self._failed_syncs: int = 0
        self._total_data_transferred: int = 0
        self._tick_count: int = 0

        # Default engine configuration.
        self._config: CloudSaveConfig = CloudSaveConfig()

    # ------------------------------------------------------------------
    # Seeding
    # ------------------------------------------------------------------

    def _seed(self) -> None:
        """Populate the engine with seed players, slots, chunks, sync
        operations, conflicts, quotas, and backups for integration testing."""
        with self._init_lock:
            if self._initialized:
                return

            now = _now()

            # --- Players -------------------------------------------------
            # Five players are represented implicitly via their slots and
            # quota records. We keep an explicit list for convenience.
            self._seed_players: List[str] = [
                "player_001",
                "player_002",
                "player_003",
                "player_004",
                "player_005",
            ]

            # --- Save Slots ---------------------------------------------
            seed_slots = [
                SaveSlot(
                    slot_id="slot_p001_manual_01",
                    player_id="player_001",
                    slot_name="Forest Camp Manual",
                    slot_type=SaveSlotType.MANUAL,
                    game_version="1.4.2",
                    platform=PlatformType.PC,
                    data_hash=self.calculate_data_hash(
                        {"hp": 100, "mp": 40, "location": "forest_camp"}
                    ),
                    data_size_bytes=128,
                    compression=CompressionType.GZIP,
                    encryption=EncryptionType.AES256,
                    created_at="2026-06-01T10:15:00Z",
                    modified_at="2026-07-08T18:30:00Z",
                    sync_status=SyncStatus.SYNCED,
                    cloud_version=3,
                    local_version=3,
                    data_snapshot={"hp": 100, "mp": 40, "location": "forest_camp"},
                    metadata={"chapter": 2, "playtime_seconds": 14400},
                ),
                SaveSlot(
                    slot_id="slot_p001_auto_01",
                    player_id="player_001",
                    slot_name="Autosave at Gate",
                    slot_type=SaveSlotType.AUTOMATIC,
                    game_version="1.4.2",
                    platform=PlatformType.PC,
                    data_hash=self.calculate_data_hash(
                        {"hp": 78, "mp": 22, "location": "city_gate"}
                    ),
                    data_size_bytes=132,
                    compression=CompressionType.GZIP,
                    encryption=EncryptionType.AES256,
                    created_at="2026-07-09T21:05:00Z",
                    modified_at="2026-07-09T21:05:00Z",
                    sync_status=SyncStatus.PENDING_UPLOAD,
                    cloud_version=2,
                    local_version=3,
                    data_snapshot={"hp": 78, "mp": 22, "location": "city_gate"},
                    metadata={"chapter": 3, "playtime_seconds": 16200},
                ),
                SaveSlot(
                    slot_id="slot_p001_checkpoint_01",
                    player_id="player_001",
                    slot_name="Boss Arena Checkpoint",
                    slot_type=SaveSlotType.CHECKPOINT,
                    game_version="1.4.2",
                    platform=PlatformType.MAC,
                    data_hash=self.calculate_data_hash(
                        {"hp": 50, "mp": 0, "location": "boss_arena"}
                    ),
                    data_size_bytes=120,
                    compression=CompressionType.ZSTD,
                    encryption=EncryptionType.AES256,
                    created_at="2026-07-05T12:00:00Z",
                    modified_at="2026-07-05T12:00:00Z",
                    sync_status=SyncStatus.CONFLICT,
                    cloud_version=1,
                    local_version=2,
                    data_snapshot={"hp": 50, "mp": 0, "location": "boss_arena"},
                    metadata={"chapter": 4, "playtime_seconds": 18000},
                ),
                SaveSlot(
                    slot_id="slot_p002_manual_01",
                    player_id="player_002",
                    slot_name="Mountain Pass",
                    slot_type=SaveSlotType.MANUAL,
                    game_version="1.4.0",
                    platform=PlatformType.IOS,
                    data_hash=self.calculate_data_hash(
                        {"hp": 120, "mp": 60, "location": "mountain_pass"}
                    ),
                    data_size_bytes=140,
                    compression=CompressionType.GZIP,
                    encryption=EncryptionType.AES256,
                    created_at="2026-06-20T08:00:00Z",
                    modified_at="2026-07-07T19:45:00Z",
                    sync_status=SyncStatus.SYNCED,
                    cloud_version=5,
                    local_version=5,
                    data_snapshot={"hp": 120, "mp": 60, "location": "mountain_pass"},
                    metadata={"chapter": 5, "playtime_seconds": 21600},
                ),
                SaveSlot(
                    slot_id="slot_p002_auto_01",
                    player_id="player_002",
                    slot_name="Autosave Harbor",
                    slot_type=SaveSlotType.AUTOMATIC,
                    game_version="1.4.0",
                    platform=PlatformType.ANDROID,
                    data_hash=self.calculate_data_hash(
                        {"hp": 90, "mp": 30, "location": "harbor"}
                    ),
                    data_size_bytes=124,
                    compression=CompressionType.LZ4,
                    encryption=EncryptionType.XOR,
                    created_at="2026-07-10T06:30:00Z",
                    modified_at="2026-07-10T06:30:00Z",
                    sync_status=SyncStatus.PENDING_DOWNLOAD,
                    cloud_version=4,
                    local_version=3,
                    data_snapshot={"hp": 90, "mp": 30, "location": "harbor"},
                    metadata={"chapter": 6, "playtime_seconds": 23400},
                ),
                SaveSlot(
                    slot_id="slot_p003_quick_01",
                    player_id="player_003",
                    slot_name="Quick Save Dungeon",
                    slot_type=SaveSlotType.QUICK_SAVE,
                    game_version="1.3.8",
                    platform=PlatformType.CONSOLE,
                    data_hash=self.calculate_data_hash(
                        {"hp": 65, "mp": 45, "location": "dungeon_3"}
                    ),
                    data_size_bytes=116,
                    compression=CompressionType.GZIP,
                    encryption=EncryptionType.AES256,
                    created_at="2026-07-08T22:10:00Z",
                    modified_at="2026-07-08T22:10:00Z",
                    sync_status=SyncStatus.OFFLINE,
                    cloud_version=0,
                    local_version=1,
                    data_snapshot={"hp": 65, "mp": 45, "location": "dungeon_3"},
                    metadata={"chapter": 7, "playtime_seconds": 25200},
                ),
                SaveSlot(
                    slot_id="slot_p003_milestone_01",
                    player_id="player_003",
                    slot_name="Story Milestone: Dragon",
                    slot_type=SaveSlotType.STORY_MILESTONE,
                    game_version="1.3.8",
                    platform=PlatformType.CONSOLE,
                    data_hash=self.calculate_data_hash(
                        {"hp": 200, "mp": 100, "location": "dragon_lair"}
                    ),
                    data_size_bytes=152,
                    compression=CompressionType.ZSTD,
                    encryption=EncryptionType.AES256,
                    created_at="2026-07-04T16:20:00Z",
                    modified_at="2026-07-04T16:20:00Z",
                    sync_status=SyncStatus.SYNCED,
                    cloud_version=2,
                    local_version=2,
                    data_snapshot={"hp": 200, "mp": 100, "location": "dragon_lair"},
                    metadata={"chapter": 8, "playtime_seconds": 28800},
                ),
                SaveSlot(
                    slot_id="slot_p004_manual_01",
                    player_id="player_004",
                    slot_name="Desert Outpost",
                    slot_type=SaveSlotType.MANUAL,
                    game_version="1.4.2",
                    platform=PlatformType.WEB,
                    data_hash=self.calculate_data_hash(
                        {"hp": 80, "mp": 50, "location": "desert_outpost"}
                    ),
                    data_size_bytes=128,
                    compression=CompressionType.GZIP,
                    encryption=EncryptionType.AES256,
                    created_at="2026-06-30T11:00:00Z",
                    modified_at="2026-07-09T20:00:00Z",
                    sync_status=SyncStatus.ERROR,
                    cloud_version=1,
                    local_version=4,
                    data_snapshot={"hp": 80, "mp": 50, "location": "desert_outpost"},
                    metadata={"chapter": 9, "playtime_seconds": 30600},
                ),
                SaveSlot(
                    slot_id="slot_p004_auto_01",
                    player_id="player_004",
                    slot_name="Autosave Oasis",
                    slot_type=SaveSlotType.AUTOMATIC,
                    game_version="1.4.2",
                    platform=PlatformType.PC,
                    data_hash=self.calculate_data_hash(
                        {"hp": 70, "mp": 35, "location": "oasis"}
                    ),
                    data_size_bytes=120,
                    compression=CompressionType.LZ4,
                    encryption=EncryptionType.AES256,
                    created_at="2026-07-10T07:15:00Z",
                    modified_at="2026-07-10T07:15:00Z",
                    sync_status=SyncStatus.PENDING_UPLOAD,
                    cloud_version=2,
                    local_version=3,
                    data_snapshot={"hp": 70, "mp": 35, "location": "oasis"},
                    metadata={"chapter": 10, "playtime_seconds": 32400},
                ),
                SaveSlot(
                    slot_id="slot_p005_manual_01",
                    player_id="player_005",
                    slot_name="Sky Temple",
                    slot_type=SaveSlotType.MANUAL,
                    game_version="1.4.2",
                    platform=PlatformType.MAC,
                    data_hash=self.calculate_data_hash(
                        {"hp": 150, "mp": 80, "location": "sky_temple"}
                    ),
                    data_size_bytes=136,
                    compression=CompressionType.GZIP,
                    encryption=EncryptionType.AES256,
                    created_at="2026-07-01T09:30:00Z",
                    modified_at="2026-07-10T05:00:00Z",
                    sync_status=SyncStatus.SYNCED,
                    cloud_version=6,
                    local_version=6,
                    data_snapshot={"hp": 150, "mp": 80, "location": "sky_temple"},
                    metadata={"chapter": 11, "playtime_seconds": 36000},
                ),
            ]
            for slot in seed_slots:
                self._slots[slot.slot_id] = slot

            # --- Save Data Chunks ---------------------------------------
            seed_chunks = [
                SaveDataChunk(
                    chunk_id="chunk_001",
                    slot_id="slot_p001_manual_01",
                    data_type=SaveDataType.GAME_STATE,
                    chunk_data={"hp": 100, "mp": 40, "location": "forest_camp"},
                    chunk_hash=self.calculate_data_hash(
                        {"hp": 100, "mp": 40, "location": "forest_camp"}
                    ),
                    chunk_size=128,
                    offset=0,
                    is_compressed=True,
                    is_encrypted=True,
                    metadata={"section": "core_state"},
                ),
                SaveDataChunk(
                    chunk_id="chunk_002",
                    slot_id="slot_p001_manual_01",
                    data_type=SaveDataType.INVENTORY,
                    chunk_data={"gold": 540, "potions": 3, "keys": ["rusty", "brass"]},
                    chunk_hash=self.calculate_data_hash(
                        {"gold": 540, "potions": 3, "keys": ["rusty", "brass"]}
                    ),
                    chunk_size=96,
                    offset=128,
                    is_compressed=True,
                    is_encrypted=True,
                    metadata={"section": "backpack"},
                ),
                SaveDataChunk(
                    chunk_id="chunk_003",
                    slot_id="slot_p002_manual_01",
                    data_type=SaveDataType.PLAYER_PROGRESS,
                    chunk_data={"chapter": 5, "quests_done": 42, "levels_cleared": 18},
                    chunk_hash=self.calculate_data_hash(
                        {"chapter": 5, "quests_done": 42, "levels_cleared": 18}
                    ),
                    chunk_size=104,
                    offset=0,
                    is_compressed=True,
                    is_encrypted=True,
                    metadata={"section": "progress"},
                ),
                SaveDataChunk(
                    chunk_id="chunk_004",
                    slot_id="slot_p003_milestone_01",
                    data_type=SaveDataType.WORLD_STATE,
                    chunk_data={"dragon_defeated": True, "world_flags": {"bridge_built": True}},
                    chunk_hash=self.calculate_data_hash(
                        {"dragon_defeated": True, "world_flags": {"bridge_built": True}}
                    ),
                    chunk_size=112,
                    offset=0,
                    is_compressed=True,
                    is_encrypted=True,
                    metadata={"section": "world"},
                ),
                SaveDataChunk(
                    chunk_id="chunk_005",
                    slot_id="slot_p005_manual_01",
                    data_type=SaveDataType.CHARACTER_DATA,
                    chunk_data={"class": "windblade", "level": 48, "skills": ["gust", "tempest"]},
                    chunk_hash=self.calculate_data_hash(
                        {"class": "windblade", "level": 48, "skills": ["gust", "tempest"]}
                    ),
                    chunk_size=108,
                    offset=0,
                    is_compressed=True,
                    is_encrypted=True,
                    metadata={"section": "character"},
                ),
            ]
            for chunk in seed_chunks:
                self._chunks[chunk.chunk_id] = chunk

            # --- Sync Operations ----------------------------------------
            seed_ops = [
                SyncOperation(
                    operation_id="sync_op_001",
                    player_id="player_001",
                    slot_id="slot_p001_manual_01",
                    operation_type="upload",
                    source_platform=PlatformType.PC,
                    target_platform=PlatformType.MAC,
                    status=SyncStatus.SYNCED,
                    started_at="2026-07-08T18:25:00Z",
                    completed_at="2026-07-08T18:30:00Z",
                    data_delta=128,
                    conflict_type="",
                    resolution=ConflictResolution.KEEP_NEWEST,
                    metadata={"bytes_uploaded": 128},
                ),
                SyncOperation(
                    operation_id="sync_op_002",
                    player_id="player_001",
                    slot_id="slot_p001_auto_01",
                    operation_type="upload",
                    source_platform=PlatformType.PC,
                    target_platform=PlatformType.WEB,
                    status=SyncStatus.PENDING_UPLOAD,
                    started_at="2026-07-09T21:05:00Z",
                    completed_at="",
                    data_delta=132,
                    conflict_type="",
                    resolution=ConflictResolution.MANUAL_REVIEW,
                    metadata={"bytes_uploaded": 0},
                ),
                SyncOperation(
                    operation_id="sync_op_003",
                    player_id="player_001",
                    slot_id="slot_p001_checkpoint_01",
                    operation_type="sync",
                    source_platform=PlatformType.MAC,
                    target_platform=PlatformType.PC,
                    status=SyncStatus.CONFLICT,
                    started_at="2026-07-05T12:00:00Z",
                    completed_at="",
                    data_delta=120,
                    conflict_type="version_mismatch",
                    resolution=ConflictResolution.MANUAL_REVIEW,
                    metadata={"local_version": 2, "cloud_version": 1},
                ),
                SyncOperation(
                    operation_id="sync_op_004",
                    player_id="player_002",
                    slot_id="slot_p002_auto_01",
                    operation_type="download",
                    source_platform=PlatformType.ANDROID,
                    target_platform=PlatformType.IOS,
                    status=SyncStatus.PENDING_DOWNLOAD,
                    started_at="2026-07-10T06:31:00Z",
                    completed_at="",
                    data_delta=124,
                    conflict_type="",
                    resolution=ConflictResolution.KEEP_CLOUD,
                    metadata={"bytes_downloaded": 0},
                ),
                SyncOperation(
                    operation_id="sync_op_005",
                    player_id="player_004",
                    slot_id="slot_p004_manual_01",
                    operation_type="upload",
                    source_platform=PlatformType.WEB,
                    target_platform=PlatformType.PC,
                    status=SyncStatus.ERROR,
                    started_at="2026-07-09T19:55:00Z",
                    completed_at="2026-07-09T19:56:00Z",
                    data_delta=0,
                    conflict_type="network_error",
                    resolution=ConflictResolution.MANUAL_REVIEW,
                    metadata={"error": "connection_reset"},
                ),
            ]
            for op in seed_ops:
                self._sync_operations[op.operation_id] = op

            # --- Conflict Records ---------------------------------------
            seed_conflicts = [
                ConflictRecord(
                    conflict_id="conflict_001",
                    slot_id="slot_p001_checkpoint_01",
                    player_id="player_001",
                    local_version=2,
                    cloud_version=1,
                    local_timestamp="2026-07-05T12:00:00Z",
                    cloud_timestamp="2026-07-04T22:00:00Z",
                    local_data_hash=self.calculate_data_hash(
                        {"hp": 50, "mp": 0, "location": "boss_arena"}
                    ),
                    cloud_data_hash=self.calculate_data_hash(
                        {"hp": 80, "mp": 10, "location": "boss_arena"}
                    ),
                    resolution=ConflictResolution.MANUAL_REVIEW,
                    resolved=False,
                    metadata={"detected_by": "auto_detect"},
                ),
                ConflictRecord(
                    conflict_id="conflict_002",
                    slot_id="slot_p002_auto_01",
                    player_id="player_002",
                    local_version=3,
                    cloud_version=4,
                    local_timestamp="2026-07-10T06:00:00Z",
                    cloud_timestamp="2026-07-10T06:30:00Z",
                    local_data_hash=self.calculate_data_hash(
                        {"hp": 90, "mp": 30, "location": "harbor"}
                    ),
                    cloud_data_hash=self.calculate_data_hash(
                        {"hp": 95, "mp": 30, "location": "harbor_docks"}
                    ),
                    resolution=ConflictResolution.KEEP_CLOUD,
                    resolved=False,
                    metadata={"detected_by": "download_check"},
                ),
                ConflictRecord(
                    conflict_id="conflict_003",
                    slot_id="slot_p004_manual_01",
                    player_id="player_004",
                    local_version=4,
                    cloud_version=1,
                    local_timestamp="2026-07-09T20:00:00Z",
                    cloud_timestamp="2026-06-30T11:00:00Z",
                    local_data_hash=self.calculate_data_hash(
                        {"hp": 80, "mp": 50, "location": "desert_outpost"}
                    ),
                    cloud_data_hash=self.calculate_data_hash(
                        {"hp": 60, "mp": 40, "location": "desert_outpost"}
                    ),
                    resolution=ConflictResolution.KEEP_LOCAL,
                    resolved=True,
                    metadata={"detected_by": "upload_check", "resolved_by": "auto"},
                ),
            ]
            for conflict in seed_conflicts:
                self._conflicts[conflict.conflict_id] = conflict

            # --- Quota Records ------------------------------------------
            for pid in self._seed_players:
                used = (len([s for s in seed_slots if s.player_id == pid]) * 1024) + 2048
                self._quotas[pid] = CloudStorageQuota(
                    player_id=pid,
                    total_quota_bytes=_DEFAULT_QUOTA_BYTES,
                    used_bytes=used,
                    available_bytes=_DEFAULT_QUOTA_BYTES - used,
                    save_count=len([s for s in seed_slots if s.player_id == pid]),
                    last_calculated=now,
                    metadata={"plan": "standard"},
                )

            # --- Backup Slots -------------------------------------------
            seed_backups = [
                SaveSlot(
                    slot_id="backup_p001_manual_01_v1",
                    player_id="player_001",
                    slot_name="Backup: Forest Camp v1",
                    slot_type=SaveSlotType.MANUAL,
                    game_version="1.4.1",
                    platform=PlatformType.PC,
                    data_hash=self.calculate_data_hash(
                        {"hp": 90, "mp": 35, "location": "forest_camp"}
                    ),
                    data_size_bytes=124,
                    compression=CompressionType.GZIP,
                    encryption=EncryptionType.AES256,
                    created_at="2026-06-15T10:00:00Z",
                    modified_at="2026-06-15T10:00:00Z",
                    sync_status=SyncStatus.SYNCED,
                    cloud_version=1,
                    local_version=1,
                    data_snapshot={"hp": 90, "mp": 35, "location": "forest_camp"},
                    metadata={"backup_of": "slot_p001_manual_01", "backup_version": 1},
                ),
                SaveSlot(
                    slot_id="backup_p001_manual_01_v2",
                    player_id="player_001",
                    slot_name="Backup: Forest Camp v2",
                    slot_type=SaveSlotType.MANUAL,
                    game_version="1.4.2",
                    platform=PlatformType.PC,
                    data_hash=self.calculate_data_hash(
                        {"hp": 95, "mp": 38, "location": "forest_camp"}
                    ),
                    data_size_bytes=126,
                    compression=CompressionType.GZIP,
                    encryption=EncryptionType.AES256,
                    created_at="2026-06-25T10:00:00Z",
                    modified_at="2026-06-25T10:00:00Z",
                    sync_status=SyncStatus.SYNCED,
                    cloud_version=2,
                    local_version=2,
                    data_snapshot={"hp": 95, "mp": 38, "location": "forest_camp"},
                    metadata={"backup_of": "slot_p001_manual_01", "backup_version": 2},
                ),
                SaveSlot(
                    slot_id="backup_p002_manual_01_v1",
                    player_id="player_002",
                    slot_name="Backup: Mountain Pass v1",
                    slot_type=SaveSlotType.MANUAL,
                    game_version="1.3.9",
                    platform=PlatformType.IOS,
                    data_hash=self.calculate_data_hash(
                        {"hp": 110, "mp": 55, "location": "mountain_pass"}
                    ),
                    data_size_bytes=136,
                    compression=CompressionType.GZIP,
                    encryption=EncryptionType.AES256,
                    created_at="2026-06-10T08:00:00Z",
                    modified_at="2026-06-10T08:00:00Z",
                    sync_status=SyncStatus.SYNCED,
                    cloud_version=1,
                    local_version=1,
                    data_snapshot={"hp": 110, "mp": 55, "location": "mountain_pass"},
                    metadata={"backup_of": "slot_p002_manual_01", "backup_version": 1},
                ),
            ]
            for backup in seed_backups:
                self._backups[backup.slot_id] = backup

            # --- Seed Events --------------------------------------------
            self._events.append(
                CloudSaveEvent(
                    event_id=_new_id("evt"),
                    event_type="engine_seeded",
                    timestamp=now,
                    slot_id="",
                    player_id="",
                    data={"slots": len(seed_slots), "chunks": len(seed_chunks)},
                )
            )

            self._initialized: bool = True

    @classmethod
    def get_instance(cls) -> "CloudSaveSystem":
        """Return the singleton CloudSaveSystem instance."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    # ------------------------------------------------------------------
    # Internal Helpers
    # ------------------------------------------------------------------

    def _log_event(
        self,
        event_type: str,
        slot_id: str = "",
        player_id: str = "",
        data: Optional[Dict[str, Any]] = None,
    ) -> CloudSaveEvent:
        """Append an audit event to the FIFO log and return it."""
        event = CloudSaveEvent(
            event_id=_new_id("evt"),
            event_type=event_type,
            timestamp=_now(),
            slot_id=slot_id,
            player_id=player_id,
            data=data or {},
        )
        self._events.append(event)
        _evict_fifo_list(self._events, _MAX_EVENTS)
        return event

    def _recompute_slot_payload(self, slot: SaveSlot) -> None:
        """Refresh the data hash, size, and modification timestamp for a slot
        based on its current data_snapshot."""
        snapshot = slot.data_snapshot or {}
        slot.data_hash = self.calculate_data_hash(snapshot)
        slot.data_size_bytes = len(_serialize_bytes(snapshot))
        slot.modified_at = _now()

    def _count_player_slots(self, player_id: str) -> int:
        return sum(1 for s in self._slots.values() if s.player_id == player_id)

    # ------------------------------------------------------------------
    # Save Slot Lifecycle
    # ------------------------------------------------------------------

    def register_save_slot(
        self,
        slot_id: str,
        player_id: str,
        slot_name: str,
        slot_type: str = "manual",
        game_version: str = "1.0.0",
        platform: str = "pc",
        data_snapshot: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Tuple[bool, str, Optional[SaveSlot]]:
        """Register a new save slot for a player."""
        with self._lock:
            if not slot_id or not player_id:
                return False, "slot_id and player_id are required", None
            if slot_id in self._slots:
                return False, f"slot already exists: {slot_id}", None
            if self._count_player_slots(player_id) >= self._config.max_save_slots_per_player:
                return False, "player save slot limit reached", None

            slot_type_enum = _coerce_enum(SaveSlotType, slot_type, SaveSlotType.MANUAL)
            platform_enum = _coerce_enum(PlatformType, platform, PlatformType.PC)
            snapshot = dict(data_snapshot) if data_snapshot else {}
            slot = SaveSlot(
                slot_id=slot_id,
                player_id=player_id,
                slot_name=slot_name or slot_id,
                slot_type=slot_type_enum,
                game_version=game_version,
                platform=platform_enum,
                compression=self._config.compression_type,
                encryption=self._config.encryption_type,
                sync_status=SyncStatus.PENDING_UPLOAD,
                cloud_version=0,
                local_version=1,
                data_snapshot=snapshot,
                metadata=dict(metadata) if metadata else {},
            )
            self._recompute_slot_payload(slot)
            self._slots[slot_id] = slot
            _evict_fifo_dict(self._slots, _MAX_SAVE_SLOTS)

            # Update quota usage for the owning player.
            self._adjust_quota_on_add(player_id, slot.data_size_bytes)

            self._log_event(
                "slot_registered",
                slot_id=slot_id,
                player_id=player_id,
                data={"slot_name": slot.slot_name, "slot_type": slot_type_enum.value},
            )
            return True, "created", slot

    def get_save_slot(self, slot_id: str) -> Optional[SaveSlot]:
        """Return a save slot by id, or None if not found."""
        with self._lock:
            return self._slots.get(slot_id)

    def list_save_slots(self, player_id: str, type_filter: str = "") -> List[SaveSlot]:
        """List save slots for a player, optionally filtered by slot type."""
        with self._lock:
            results = [s for s in self._slots.values() if s.player_id == player_id]
            if type_filter:
                type_enum = _coerce_enum(SaveSlotType, type_filter, None)
                if type_enum is None:
                    return []
                results = [s for s in results if s.slot_type == type_enum]
            # Sort by modified_at descending so the most recent slots appear first.
            results.sort(key=lambda s: s.modified_at, reverse=True)
            return results

    def remove_save_slot(self, slot_id: str) -> Tuple[bool, str]:
        """Remove a save slot and any associated data chunks."""
        with self._lock:
            slot = self._slots.get(slot_id)
            if slot is None:
                return False, "not found"
            player_id = slot.player_id
            size_bytes = slot.data_size_bytes

            # Remove all chunks belonging to this slot.
            chunk_ids = [cid for cid, c in self._chunks.items() if c.slot_id == slot_id]
            for cid in chunk_ids:
                self._chunks.pop(cid, None)

            self._slots.pop(slot_id, None)
            self._adjust_quota_on_remove(player_id, size_bytes)
            self._log_event(
                "slot_removed",
                slot_id=slot_id,
                player_id=player_id,
                data={"removed_chunks": len(chunk_ids)},
            )
            return True, "removed"

    def update_save_slot(
        self,
        slot_id: str,
        data_snapshot: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> Tuple[bool, str, Optional[SaveSlot]]:
        """Update a save slot's snapshot and/or metadata fields."""
        with self._lock:
            slot = self._slots.get(slot_id)
            if slot is None:
                return False, "not found", None

            if data_snapshot is not None:
                slot.data_snapshot = dict(data_snapshot)

            changed: List[str] = []
            for key, value in kwargs.items():
                if key == "slot_type":
                    coerced = _coerce_enum(SaveSlotType, value, None)
                    if coerced is not None:
                        slot.slot_type = coerced
                        changed.append(key)
                elif key == "platform":
                    coerced = _coerce_enum(PlatformType, value, None)
                    if coerced is not None:
                        slot.platform = coerced
                        changed.append(key)
                elif key == "sync_status":
                    coerced = _coerce_enum(SyncStatus, value, None)
                    if coerced is not None:
                        slot.sync_status = coerced
                        changed.append(key)
                elif key == "compression":
                    coerced = _coerce_enum(CompressionType, value, None)
                    if coerced is not None:
                        slot.compression = coerced
                        changed.append(key)
                elif key == "encryption":
                    coerced = _coerce_enum(EncryptionType, value, None)
                    if coerced is not None:
                        slot.encryption = coerced
                        changed.append(key)
                elif key == "metadata" and isinstance(value, dict):
                    slot.metadata.update(value)
                    changed.append(key)
                elif hasattr(slot, key) and not key.startswith("_"):
                    if key in ("slot_id", "player_id", "created_at"):
                        # Identity / audit fields are immutable here.
                        continue
                    setattr(slot, key, value)
                    changed.append(key)

            # Rebuild payload-derived fields and bump the local version so
            # the next sync attempt can detect a divergence.
            self._recompute_slot_payload(slot)
            slot.local_version += 1
            if slot.sync_status == SyncStatus.SYNCED:
                slot.sync_status = SyncStatus.PENDING_UPLOAD

            self._log_event(
                "slot_updated",
                slot_id=slot_id,
                player_id=slot.player_id,
                data={"changed_fields": changed, "local_version": slot.local_version},
            )
            return True, "updated", slot

    # ------------------------------------------------------------------
    # Save Data Chunks
    # ------------------------------------------------------------------

    def save_data(
        self,
        slot_id: str,
        data_type: SaveDataType,
        chunk_data: Any,
        offset: int = 0,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Tuple[bool, str, Optional[SaveDataChunk]]:
        """Append or replace a typed data chunk within a save slot."""
        with self._lock:
            slot = self._slots.get(slot_id)
            if slot is None:
                return False, "slot not found", None
            data_type_enum = _coerce_enum(SaveDataType, data_type, None)
            if data_type_enum is None:
                return False, "invalid data_type", None

            chunk_id = _new_id("chunk")
            raw_bytes = _serialize_bytes(chunk_data)
            chunk = SaveDataChunk(
                chunk_id=chunk_id,
                slot_id=slot_id,
                data_type=data_type_enum,
                chunk_data=chunk_data,
                chunk_hash=hashlib.sha256(raw_bytes).hexdigest(),
                chunk_size=len(raw_bytes),
                offset=_safe_int(offset, 0),
                is_compressed=(slot.compression != CompressionType.NONE),
                is_encrypted=(slot.encryption != EncryptionType.NONE),
                metadata=dict(metadata) if metadata else {},
            )
            self._chunks[chunk_id] = chunk
            _evict_fifo_dict(self._chunks, _MAX_SAVE_CHUNKS)

            # Mark the owning slot as having local changes pending upload.
            slot.local_version += 1
            if slot.sync_status == SyncStatus.SYNCED:
                slot.sync_status = SyncStatus.PENDING_UPLOAD
            slot.modified_at = _now()

            self._log_event(
                "chunk_saved",
                slot_id=slot_id,
                player_id=slot.player_id,
                data={"chunk_id": chunk_id, "data_type": data_type_enum.value},
            )
            return True, "saved", chunk

    def get_save_data(self, slot_id: str, data_type: str = "") -> List[SaveDataChunk]:
        """Return all chunks for a slot, optionally filtered by data type."""
        with self._lock:
            results = [c for c in self._chunks.values() if c.slot_id == slot_id]
            if data_type:
                type_enum = _coerce_enum(SaveDataType, data_type, None)
                if type_enum is None:
                    return []
                results = [c for c in results if c.data_type == type_enum]
            results.sort(key=lambda c: c.offset)
            return results

    def load_save_data(self, slot_id: str) -> Optional[Dict[str, Any]]:
        """Reconstruct a combined save payload from all chunks in a slot."""
        with self._lock:
            if slot_id not in self._slots:
                return None
            chunks = [c for c in self._chunks.values() if c.slot_id == slot_id]
            if not chunks:
                slot = self._slots.get(slot_id)
                return dict(slot.data_snapshot) if slot else None
            combined: Dict[str, Any] = {}
            for chunk in sorted(chunks, key=lambda c: c.offset):
                bucket = combined.setdefault(chunk.data_type.value, {})
                if isinstance(chunk.chunk_data, dict):
                    bucket.update(chunk.chunk_data)
                else:
                    bucket["value"] = chunk.chunk_data
            return combined

    def delete_save_data(self, slot_id: str, data_type: str = "") -> Tuple[bool, str]:
        """Delete chunks for a slot, optionally scoped to a data type."""
        with self._lock:
            if slot_id not in self._slots:
                return False, "slot not found"
            type_enum = None
            if data_type:
                type_enum = _coerce_enum(SaveDataType, data_type, None)
                if type_enum is None:
                    return False, "invalid data_type"
            removed = 0
            to_remove = []
            for cid, chunk in self._chunks.items():
                if chunk.slot_id != slot_id:
                    continue
                if type_enum is not None and chunk.data_type != type_enum:
                    continue
                to_remove.append(cid)
            for cid in to_remove:
                self._chunks.pop(cid, None)
                removed += 1
            self._log_event(
                "chunks_deleted",
                slot_id=slot_id,
                data={"removed": removed, "data_type": data_type},
            )
            return True, f"deleted {removed} chunks"

    # ------------------------------------------------------------------
    # Cloud Synchronization
    # ------------------------------------------------------------------

    def upload_to_cloud(self, slot_id: str) -> Tuple[bool, str, Optional[SyncOperation]]:
        """Upload the local version of a slot to the cloud."""
        with self._lock:
            slot = self._slots.get(slot_id)
            if slot is None:
                return False, "slot not found", None
            op_id = _new_id("sync_op")
            op = SyncOperation(
                operation_id=op_id,
                player_id=slot.player_id,
                slot_id=slot_id,
                operation_type="upload",
                source_platform=slot.platform,
                target_platform=PlatformType.WEB,
                status=SyncStatus.SYNCED,
                data_delta=slot.data_size_bytes,
                metadata={"bytes_uploaded": slot.data_size_bytes},
            )
            op.completed_at = _now()
            self._sync_operations[op_id] = op
            _evict_fifo_dict(self._sync_operations, _MAX_SYNC_OPERATIONS)

            slot.cloud_version = slot.local_version
            slot.sync_status = SyncStatus.SYNCED
            self._total_syncs += 1
            self._successful_syncs += 1
            self._total_data_transferred += slot.data_size_bytes

            self._log_event(
                "upload_completed",
                slot_id=slot_id,
                player_id=slot.player_id,
                data={"cloud_version": slot.cloud_version, "bytes": slot.data_size_bytes},
            )
            return True, "uploaded", op

    def download_from_cloud(self, slot_id: str) -> Tuple[bool, str, Optional[SyncOperation]]:
        """Download the cloud version of a slot into local state."""
        with self._lock:
            slot = self._slots.get(slot_id)
            if slot is None:
                return False, "slot not found", None
            op_id = _new_id("sync_op")
            op = SyncOperation(
                operation_id=op_id,
                player_id=slot.player_id,
                slot_id=slot_id,
                operation_type="download",
                source_platform=PlatformType.WEB,
                target_platform=slot.platform,
                status=SyncStatus.SYNCED,
                data_delta=slot.data_size_bytes,
                metadata={"bytes_downloaded": slot.data_size_bytes},
            )
            op.completed_at = _now()
            self._sync_operations[op_id] = op
            _evict_fifo_dict(self._sync_operations, _MAX_SYNC_OPERATIONS)

            slot.local_version = slot.cloud_version
            slot.sync_status = SyncStatus.SYNCED
            self._total_syncs += 1
            self._successful_syncs += 1
            self._total_data_transferred += slot.data_size_bytes

            self._log_event(
                "download_completed",
                slot_id=slot_id,
                player_id=slot.player_id,
                data={"local_version": slot.local_version},
            )
            return True, "downloaded", op

    def sync_slot(
        self,
        slot_id: str,
        source_platform: str = "pc",
    ) -> Tuple[bool, str, Optional[SyncOperation]]:
        """Synchronize a single slot, resolving conflicts as needed."""
        with self._lock:
            slot = self._slots.get(slot_id)
            if slot is None:
                return False, "slot not found", None

            source_enum = _coerce_enum(PlatformType, source_platform, PlatformType.PC)
            op_id = _new_id("sync_op")

            # Detect divergence between local and cloud versions.
            conflict = self.detect_conflict(slot_id)
            if conflict is not None:
                strategy = self._config.conflict_resolution_strategy
                op = SyncOperation(
                    operation_id=op_id,
                    player_id=slot.player_id,
                    slot_id=slot_id,
                    operation_type="sync",
                    source_platform=source_enum,
                    target_platform=PlatformType.WEB,
                    status=SyncStatus.CONFLICT,
                    data_delta=slot.data_size_bytes,
                    conflict_type="version_mismatch",
                    resolution=strategy,
                    metadata={"conflict_id": conflict.conflict_id},
                )
                self._sync_operations[op_id] = op
                _evict_fifo_dict(self._sync_operations, _MAX_SYNC_OPERATIONS)
                slot.sync_status = SyncStatus.CONFLICT
                self._total_syncs += 1
                self._failed_syncs += 1
                self._log_event(
                    "sync_conflict",
                    slot_id=slot_id,
                    player_id=slot.player_id,
                    data={"conflict_id": conflict.conflict_id, "strategy": strategy.value},
                )
                return False, "conflict detected", op

            # No conflict: pick the direction based on which version is ahead.
            if slot.local_version > slot.cloud_version:
                ok, msg, op = self.upload_to_cloud(slot_id)
                return ok, msg, op
            if slot.cloud_version > slot.local_version:
                ok, msg, op = self.download_from_cloud(slot_id)
                return ok, msg, op

            # Already in sync.
            op = SyncOperation(
                operation_id=op_id,
                player_id=slot.player_id,
                slot_id=slot_id,
                operation_type="sync",
                source_platform=source_enum,
                target_platform=PlatformType.WEB,
                status=SyncStatus.SYNCED,
                data_delta=0,
                metadata={"note": "already_in_sync"},
            )
            op.completed_at = _now()
            self._sync_operations[op_id] = op
            _evict_fifo_dict(self._sync_operations, _MAX_SYNC_OPERATIONS)
            return True, "already in sync", op

    def sync_player(self, player_id: str) -> Tuple[bool, str, List[SyncOperation]]:
        """Synchronize all slots owned by a player."""
        with self._lock:
            if not player_id:
                return False, "player_id is required", []
            slot_ids = [sid for sid, s in self._slots.items() if s.player_id == player_id]
            operations: List[SyncOperation] = []
            successes = 0
            for sid in slot_ids:
                ok, _msg, op = self.sync_slot(sid, source_platform=self._slots[sid].platform.value)
                if op is not None:
                    operations.append(op)
                if ok:
                    successes += 1
            self._log_event(
                "player_synced",
                player_id=player_id,
                data={"slots": len(slot_ids), "successes": successes},
            )
            return True, f"synced {successes}/{len(slot_ids)} slots", operations

    def list_sync_operations(
        self,
        player_id: str = "",
        slot_id: str = "",
        status_filter: str = "",
        limit: int = 50,
    ) -> List[SyncOperation]:
        """List sync operations with optional filters."""
        with self._lock:
            results = list(self._sync_operations.values())
            if player_id:
                results = [o for o in results if o.player_id == player_id]
            if slot_id:
                results = [o for o in results if o.slot_id == slot_id]
            if status_filter:
                status_enum = _coerce_enum(SyncStatus, status_filter, None)
                if status_enum is None:
                    return []
                results = [o for o in results if o.status == status_enum]
            results.sort(key=lambda o: o.started_at, reverse=True)
            if limit > 0:
                results = results[:limit]
            return results

    def get_sync_operation(self, operation_id: str) -> Optional[SyncOperation]:
        """Return a sync operation by id, or None if not found."""
        with self._lock:
            return self._sync_operations.get(operation_id)

    # ------------------------------------------------------------------
    # Conflict Detection & Resolution
    # ------------------------------------------------------------------

    def detect_conflict(self, slot_id: str) -> Optional[ConflictRecord]:
        """Detect a version or hash divergence for a slot. When a divergence
        is found, a ConflictRecord is stored and returned."""
        with self._lock:
            slot = self._slots.get(slot_id)
            if slot is None:
                return None
            if slot.local_version == slot.cloud_version and slot.sync_status != SyncStatus.CONFLICT:
                return None

            # Build a synthetic cloud hash to compare against the local hash.
            cloud_snapshot = dict(slot.data_snapshot)
            cloud_hash = self.calculate_data_hash(cloud_snapshot)
            local_hash = slot.data_hash or cloud_hash

            diverged = (
                slot.local_version != slot.cloud_version
                or slot.sync_status == SyncStatus.CONFLICT
                or local_hash != cloud_hash
            )
            if not diverged:
                return None

            conflict_id = _new_id("conflict")
            conflict = ConflictRecord(
                conflict_id=conflict_id,
                slot_id=slot_id,
                player_id=slot.player_id,
                local_version=slot.local_version,
                cloud_version=slot.cloud_version,
                local_timestamp=slot.modified_at,
                cloud_timestamp=slot.modified_at,
                local_data_hash=local_hash,
                cloud_data_hash=cloud_hash,
                resolution=ConflictResolution.MANUAL_REVIEW,
                resolved=False,
                metadata={"detected_by": "detect_conflict"},
            )
            self._conflicts[conflict_id] = conflict
            _evict_fifo_dict(self._conflicts, _MAX_CONFLICTS)
            slot.sync_status = SyncStatus.CONFLICT
            self._log_event(
                "conflict_detected",
                slot_id=slot_id,
                player_id=slot.player_id,
                data={"conflict_id": conflict_id},
            )
            return conflict

    def list_conflicts(self, player_id: str = "", resolved_filter: str = "") -> List[ConflictRecord]:
        """List conflict records with optional filters.

        resolved_filter accepts "true", "false", or "" (both)."""
        with self._lock:
            results = list(self._conflicts.values())
            if player_id:
                results = [c for c in results if c.player_id == player_id]
            if resolved_filter:
                resolved_filter_lower = resolved_filter.lower()
                if resolved_filter_lower in ("true", "1", "yes"):
                    results = [c for c in results if c.resolved]
                elif resolved_filter_lower in ("false", "0", "no"):
                    results = [c for c in results if not c.resolved]
            results.sort(key=lambda c: c.conflict_id, reverse=True)
            return results

    def resolve_conflict(
        self,
        conflict_id: str,
        resolution: ConflictResolution,
    ) -> Tuple[bool, str, Optional[ConflictRecord]]:
        """Apply a resolution strategy to a stored conflict record."""
        with self._lock:
            conflict = self._conflicts.get(conflict_id)
            if conflict is None:
                return False, "conflict not found", None
            resolution_enum = _coerce_enum(ConflictResolution, resolution, ConflictResolution.MANUAL_REVIEW)
            slot = self._slots.get(conflict.slot_id)

            conflict.resolution = resolution_enum
            conflict.resolved = True

            if slot is not None:
                if resolution_enum == ConflictResolution.KEEP_CLOUD:
                    slot.local_version = slot.cloud_version
                    slot.sync_status = SyncStatus.SYNCED
                elif resolution_enum == ConflictResolution.KEEP_LOCAL:
                    slot.cloud_version = slot.local_version
                    slot.sync_status = SyncStatus.SYNCED
                elif resolution_enum == ConflictResolution.KEEP_NEWEST:
                    # Compare timestamps; here modified_at serves as the local
                    # timestamp proxy and cloud_timestamp is stored on the
                    # conflict record.
                    if conflict.cloud_timestamp and conflict.cloud_timestamp >= slot.modified_at:
                        slot.local_version = slot.cloud_version
                    else:
                        slot.cloud_version = slot.local_version
                    slot.sync_status = SyncStatus.SYNCED
                elif resolution_enum == ConflictResolution.MERGE:
                    # Merge is a cooperative strategy; mark as pending upload
                    # so the merged local state propagates on the next sync.
                    slot.cloud_version = slot.local_version
                    slot.sync_status = SyncStatus.PENDING_UPLOAD
                else:
                    # MANUAL_REVIEW leaves the slot in conflict for a human pass.
                    slot.sync_status = SyncStatus.CONFLICT

            self._log_event(
                "conflict_resolved",
                slot_id=conflict.slot_id,
                player_id=conflict.player_id,
                data={"resolution": resolution_enum.value},
            )
            return True, "resolved", conflict

    # ------------------------------------------------------------------
    # Quota Management
    # ------------------------------------------------------------------

    def get_quota(self, player_id: str) -> Optional[CloudStorageQuota]:
        """Return the cloud storage quota for a player, or None if absent."""
        with self._lock:
            return self._quotas.get(player_id)

    def update_quota(
        self,
        player_id: str,
        used_bytes: int = 0,
        save_count: int = 0,
    ) -> Tuple[bool, str, Optional[CloudStorageQuota]]:
        """Update the used bytes and save count for a player's quota."""
        with self._lock:
            quota = self._quotas.get(player_id)
            if quota is None:
                quota = CloudStorageQuota(
                    player_id=player_id,
                    total_quota_bytes=_DEFAULT_QUOTA_BYTES,
                )
                self._quotas[player_id] = quota
                _evict_fifo_dict(self._quotas, _MAX_QUOTAS)
            quota.used_bytes = _safe_int(used_bytes, quota.used_bytes)
            quota.save_count = _safe_int(save_count, quota.save_count)
            quota.available_bytes = max(0, quota.total_quota_bytes - quota.used_bytes)
            quota.last_calculated = _now()
            self._log_event(
                "quota_updated",
                player_id=player_id,
                data={"used_bytes": quota.used_bytes, "save_count": quota.save_count},
            )
            return True, "updated", quota

    def _adjust_quota_on_add(self, player_id: str, size_bytes: int) -> None:
        """Increment quota usage when a slot is added or grows."""
        quota = self._quotas.get(player_id)
        if quota is None:
            quota = CloudStorageQuota(
                player_id=player_id,
                total_quota_bytes=_DEFAULT_QUOTA_BYTES,
            )
            self._quotas[player_id] = quota
        quota.used_bytes += _safe_int(size_bytes, 0)
        quota.available_bytes = max(0, quota.total_quota_bytes - quota.used_bytes)
        quota.save_count = self._count_player_slots(player_id)
        quota.last_calculated = _now()

    def _adjust_quota_on_remove(self, player_id: str, size_bytes: int) -> None:
        """Decrement quota usage when a slot is removed."""
        quota = self._quotas.get(player_id)
        if quota is None:
            return
        quota.used_bytes = max(0, quota.used_bytes - _safe_int(size_bytes, 0))
        quota.available_bytes = max(0, quota.total_quota_bytes - quota.used_bytes)
        quota.save_count = self._count_player_slots(player_id)
        quota.last_calculated = _now()

    # ------------------------------------------------------------------
    # Payload Utilities
    # ------------------------------------------------------------------

    def calculate_data_hash(self, data: Any) -> str:
        """Compute a stable SHA-256 hash over the serialized form of data."""
        with self._lock:
            raw = _serialize_bytes(data)
            return hashlib.sha256(raw).hexdigest()

    def compress_data(self, data: Any, compression: str = "gzip") -> Tuple[bool, str, bytes]:
        """Compress arbitrary data into a bytes payload."""
        with self._lock:
            comp = _coerce_enum(CompressionType, compression, CompressionType.GZIP)
            try:
                raw = _serialize_bytes(data)
            except Exception as exc:
                return False, f"serialize_failed: {exc}", b""
            try:
                if comp == CompressionType.NONE:
                    return True, "none", raw
                if comp == CompressionType.GZIP:
                    return True, "gzip", gzip.compress(raw)
                if comp == CompressionType.ZSTD:
                    try:
                        import zstandard  # type: ignore

                        return True, "zstd", zstandard.compress(raw)
                    except Exception:
                        return True, "zstd_fallback_gzip", gzip.compress(raw)
                if comp == CompressionType.LZ4:
                    try:
                        import lz4.frame  # type: ignore

                        return True, "lz4", lz4.frame.compress(raw)
                    except Exception:
                        return True, "lz4_fallback_gzip", gzip.compress(raw)
                return False, "unsupported_compression", b""
            except Exception as exc:
                return False, f"compress_failed: {exc}", b""

    def decompress_data(self, compressed_data: bytes, compression: str = "gzip") -> Tuple[bool, str, Any]:
        """Decompress a bytes payload back into its original data."""
        with self._lock:
            comp = _coerce_enum(CompressionType, compression, CompressionType.GZIP)
            try:
                if comp == CompressionType.NONE:
                    raw = compressed_data
                elif comp == CompressionType.GZIP:
                    raw = gzip.decompress(compressed_data)
                elif comp == CompressionType.ZSTD:
                    try:
                        import zstandard  # type: ignore

                        raw = zstandard.decompress(compressed_data)
                    except Exception:
                        raw = gzip.decompress(compressed_data)
                elif comp == CompressionType.LZ4:
                    try:
                        import lz4.frame  # type: ignore

                        raw = lz4.frame.decompress(compressed_data)
                    except Exception:
                        raw = gzip.decompress(compressed_data)
                else:
                    return False, "unsupported_compression", None
                return True, "ok", _deserialize_bytes(raw)
            except Exception as exc:
                return False, f"decompress_failed: {exc}", None

    def encrypt_data(self, data: Any, encryption: str = "aes256") -> Tuple[bool, str, bytes]:
        """Encrypt arbitrary data into a bytes payload."""
        with self._lock:
            enc = _coerce_enum(EncryptionType, encryption, EncryptionType.AES256)
            try:
                raw = _serialize_bytes(data)
            except Exception as exc:
                return False, f"serialize_failed: {exc}", b""
            try:
                if enc == EncryptionType.NONE:
                    return True, "none", raw
                if enc == EncryptionType.AES256:
                    try:
                        from cryptography.fernet import Fernet  # type: ignore

                        key = base64.urlsafe_b64encode(hashlib.sha256(_XOR_KEY).digest())
                        token = Fernet(key).encrypt(raw)
                        return True, "aes256", token
                    except Exception:
                        return True, "aes256_fallback_xor", _xor_bytes(raw, _XOR_KEY)
                if enc == EncryptionType.XOR:
                    return True, "xor", _xor_bytes(raw, _XOR_KEY)
                return False, "unsupported_encryption", b""
            except Exception as exc:
                return False, f"encrypt_failed: {exc}", b""

    def decrypt_data(self, encrypted_data: bytes, encryption: str = "aes256") -> Tuple[bool, str, Any]:
        """Decrypt a bytes payload back into its original data."""
        with self._lock:
            enc = _coerce_enum(EncryptionType, encryption, EncryptionType.AES256)
            try:
                if enc == EncryptionType.NONE:
                    raw = encrypted_data
                elif enc == EncryptionType.AES256:
                    try:
                        from cryptography.fernet import Fernet  # type: ignore

                        key = base64.urlsafe_b64encode(hashlib.sha256(_XOR_KEY).digest())
                        raw = Fernet(key).decrypt(encrypted_data)
                    except Exception:
                        raw = _xor_bytes(encrypted_data, _XOR_KEY)
                elif enc == EncryptionType.XOR:
                    raw = _xor_bytes(encrypted_data, _XOR_KEY)
                else:
                    return False, "unsupported_encryption", None
                return True, "ok", _deserialize_bytes(raw)
            except Exception as exc:
                return False, f"decrypt_failed: {exc}", None

    # ------------------------------------------------------------------
    # Snapshot Backups
    # ------------------------------------------------------------------

    def create_snapshot_backup(self, slot_id: str) -> Tuple[bool, str, Optional[SaveSlot]]:
        """Create a backup copy of a slot's current state."""
        with self._lock:
            slot = self._slots.get(slot_id)
            if slot is None:
                return False, "slot not found", None
            backup_id = _new_id(f"backup_{slot_id}")
            backup = SaveSlot(
                slot_id=backup_id,
                player_id=slot.player_id,
                slot_name=f"Backup: {slot.slot_name}",
                slot_type=slot.slot_type,
                game_version=slot.game_version,
                platform=slot.platform,
                data_hash=slot.data_hash,
                data_size_bytes=slot.data_size_bytes,
                compression=slot.compression,
                encryption=slot.encryption,
                created_at=_now(),
                modified_at=_now(),
                sync_status=SyncStatus.SYNCED,
                cloud_version=slot.cloud_version,
                local_version=slot.local_version,
                data_snapshot=dict(slot.data_snapshot),
                metadata={
                    "backup_of": slot_id,
                    "backup_version": slot.local_version,
                    "source_modified_at": slot.modified_at,
                },
            )
            self._backups[backup_id] = backup
            _evict_fifo_dict(self._backups, _MAX_BACKUPS)
            self._log_event(
                "backup_created",
                slot_id=slot_id,
                player_id=slot.player_id,
                data={"backup_slot_id": backup_id},
            )
            return True, "backup created", backup

    def list_backups(self, slot_id: str) -> List[SaveSlot]:
        """List all backups associated with a slot."""
        with self._lock:
            results = [
                b for b in self._backups.values()
                if b.metadata.get("backup_of") == slot_id
            ]
            results.sort(key=lambda b: b.created_at, reverse=True)
            return results

    def restore_backup(
        self,
        slot_id: str,
        backup_slot_id: str,
    ) -> Tuple[bool, str, Optional[SaveSlot]]:
        """Restore a slot from a previously created backup."""
        with self._lock:
            slot = self._slots.get(slot_id)
            if slot is None:
                return False, "slot not found", None
            backup = self._backups.get(backup_slot_id)
            if backup is None:
                return False, "backup not found", None
            if backup.metadata.get("backup_of") != slot_id:
                return False, "backup does not belong to this slot", None

            slot.slot_name = backup.slot_name.replace("Backup: ", "")
            slot.game_version = backup.game_version
            slot.platform = backup.platform
            slot.compression = backup.compression
            slot.encryption = backup.encryption
            slot.data_snapshot = dict(backup.data_snapshot)
            slot.cloud_version = backup.cloud_version
            slot.local_version = backup.local_version + 1
            self._recompute_slot_payload(slot)
            slot.sync_status = SyncStatus.PENDING_UPLOAD

            self._log_event(
                "backup_restored",
                slot_id=slot_id,
                player_id=slot.player_id,
                data={"backup_slot_id": backup_slot_id},
            )
            return True, "restored", slot

    # ------------------------------------------------------------------
    # Audit Events
    # ------------------------------------------------------------------

    def list_events(
        self,
        slot_id: str = "",
        player_id: str = "",
        limit: int = 100,
    ) -> List[CloudSaveEvent]:
        """List audit events with optional slot / player filters."""
        with self._lock:
            results = list(self._events)
            if slot_id:
                results = [e for e in results if e.slot_id == slot_id]
            if player_id:
                results = [e for e in results if e.player_id == player_id]
            results.sort(key=lambda e: e.timestamp, reverse=True)
            if limit > 0:
                results = results[:limit]
            return results

    # ------------------------------------------------------------------
    # Observability
    # ------------------------------------------------------------------

    def get_status(self) -> Dict[str, Any]:
        """Return a summary of the current cloud save engine state."""
        with self._lock:
            return {
                "initialized": self._initialized,
                "total_slots": len(self._slots),
                "total_chunks": len(self._chunks),
                "total_sync_operations": len(self._sync_operations),
                "total_conflicts": len(self._conflicts),
                "unresolved_conflicts": sum(1 for c in self._conflicts.values() if not c.resolved),
                "total_quotas": len(self._quotas),
                "total_backups": len(self._backups),
                "total_events": len(self._events),
                "total_syncs": self._total_syncs,
                "successful_syncs": self._successful_syncs,
                "failed_syncs": self._failed_syncs,
                "total_data_transferred": self._total_data_transferred,
                "tick_count": self._tick_count,
                "auto_sync_enabled": self._config.auto_sync_enabled,
            }

    def get_stats(self) -> CloudSaveStats:
        """Return aggregate statistics for the engine."""
        with self._lock:
            slots = list(self._slots.values())
            synced = sum(1 for s in slots if s.sync_status == SyncStatus.SYNCED)
            pending = sum(
                1 for s in slots
                if s.sync_status in (SyncStatus.PENDING_UPLOAD, SyncStatus.PENDING_DOWNLOAD)
            )
            conflict_slots = sum(1 for s in slots if s.sync_status == SyncStatus.CONFLICT)
            return CloudSaveStats(
                total_slots=len(slots),
                synced_slots=synced,
                pending_slots=pending,
                conflict_slots=conflict_slots,
                total_syncs=self._total_syncs,
                successful_syncs=self._successful_syncs,
                failed_syncs=self._failed_syncs,
                total_data_transferred=self._total_data_transferred,
                tick_count=self._tick_count,
            )

    def get_snapshot(self) -> CloudSaveSnapshot:
        """Capture an immutable snapshot of the cloud save engine state."""
        with self._lock:
            stats = self.get_stats()
            return CloudSaveSnapshot(
                timestamp=_now(),
                slots=list(self._slots.values()),
                sync_operations=list(self._sync_operations.values()),
                conflicts=list(self._conflicts.values()),
                quotas=list(self._quotas.values()),
                stats=stats,
            )

    def get_config(self) -> CloudSaveConfig:
        """Return the current engine configuration."""
        with self._lock:
            return self._config

    def set_config(self, **kwargs: Any) -> Tuple[bool, str, "CloudSaveConfig"]:
        """Update one or more configuration fields by keyword."""
        with self._lock:
            changed: List[str] = []
            for key, value in kwargs.items():
                if key == "conflict_resolution_strategy":
                    coerced = _coerce_enum(ConflictResolution, value, None)
                    if coerced is not None:
                        self._config.conflict_resolution_strategy = coerced
                        changed.append(key)
                elif key == "compression_type":
                    coerced = _coerce_enum(CompressionType, value, None)
                    if coerced is not None:
                        self._config.compression_type = coerced
                        changed.append(key)
                elif key == "encryption_type":
                    coerced = _coerce_enum(EncryptionType, value, None)
                    if coerced is not None:
                        self._config.encryption_type = coerced
                        changed.append(key)
                elif key == "metadata" and isinstance(value, dict):
                    self._config.metadata.update(value)
                    changed.append(key)
                elif hasattr(self._config, key) and not key.startswith("_"):
                    setattr(self._config, key, value)
                    changed.append(key)
            if changed:
                self._log_event(
                    "config_updated",
                    data={"changed_fields": changed},
                )
            return True, "updated", self._config

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def tick(self) -> Dict[str, Any]:
        """Advance the engine by one tick. When auto-sync is enabled, pending
        slots are synchronized and aggregate stats are refreshed."""
        with self._lock:
            self._tick_count += 1
            auto_synced = 0
            auto_conflicts = 0

            if self._config.auto_sync_enabled:
                for slot in list(self._slots.values()):
                    if slot.sync_status == SyncStatus.PENDING_UPLOAD:
                        ok, _msg, _op = self.upload_to_cloud(slot.slot_id)
                        if ok:
                            auto_synced += 1
                    elif slot.sync_status == SyncStatus.PENDING_DOWNLOAD:
                        ok, _msg, _op = self.download_from_cloud(slot.slot_id)
                        if ok:
                            auto_synced += 1
                    elif slot.sync_status == SyncStatus.CONFLICT:
                        auto_conflicts += 1

            stats = self.get_stats()
            if self._tick_count % 60 == 0:
                self._log_event(
                    "tick",
                    data={
                        "tick_count": self._tick_count,
                        "auto_synced": auto_synced,
                        "auto_conflicts": auto_conflicts,
                    },
                )
            return {
                "tick_count": self._tick_count,
                "auto_synced": auto_synced,
                "auto_conflicts": auto_conflicts,
                "stats": stats.to_dict(),
            }

    def reset(self) -> None:
        """Clear all stores and re-seed the engine to its initial state."""
        with self._lock:
            self._initialized = False
            self._init_stores()
            self._seed()


# ---------------------------------------------------------------------------
# Module-Level Factory
# ---------------------------------------------------------------------------


def get_cloud_save_system() -> CloudSaveSystem:
    """Return the singleton CloudSaveSystem instance."""
    return CloudSaveSystem.get_instance()


# ---------------------------------------------------------------------------
# Exported Symbols
# ---------------------------------------------------------------------------


__all__ = [
    # Enums
    "SaveSlotType",
    "SyncStatus",
    "ConflictResolution",
    "PlatformType",
    "SaveDataType",
    "CompressionType",
    "EncryptionType",
    # Data classes
    "SaveSlot",
    "SaveDataChunk",
    "SyncOperation",
    "ConflictRecord",
    "CloudStorageQuota",
    "CloudSaveConfig",
    "CloudSaveStats",
    "CloudSaveSnapshot",
    "CloudSaveEvent",
    # Main system
    "CloudSaveSystem",
    # Factory
    "get_cloud_save_system",
]
