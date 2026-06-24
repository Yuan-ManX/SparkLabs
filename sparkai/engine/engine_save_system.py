"""
SparkLabs Engine - Save System Engine

Game save/load serialization with versioning, compression, cloud sync
support, and backwards compatibility. Provides save slot management,
checksum verification, and export/import functionality.

Architecture:
  SaveSystemEngine (Singleton)
    |-- SaveSlot         — named save slot with history and metadata
    |-- SaveData         — serialized game state with entity and variable data
    |-- SaveMetadata     — descriptive metadata for each save entry

Save Pipeline:
  1. Save     — serialize game state, compute checksum, store in slot
  2. Load     — verify integrity, deserialize, apply state
  3. Verify   — validate checksum and data structure
  4. Export   — serialize to portable format
  5. Import   — deserialize from portable format with version migration
"""

from __future__ import annotations

import hashlib
import json
import math
import threading
import time
import uuid
import zlib
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple, Set


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class SaveFormat(Enum):
    """Format type for save data serialization."""
    JSON = "json"
    BINARY = "binary"
    COMPRESSED = "compressed"
    CLOUD = "cloud"


class SaveSlotType(Enum):
    """Classification of a save slot by creation method."""
    AUTO = "auto"
    MANUAL = "manual"
    QUICK = "quick"
    CHECKPOINT = "checkpoint"


class SaveStatus(Enum):
    """Current status of a save operation or save data."""
    IDLE = "idle"
    SAVING = "saving"
    LOADING = "loading"
    VERIFYING = "verifying"
    CORRUPTED = "corrupted"


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------

@dataclass
class SaveMetadata:
    """Descriptive metadata for a save data entry."""

    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    slot_name: str = ""
    slot_type: SaveSlotType = SaveSlotType.MANUAL
    game_version: str = "1.0.0"
    timestamp: float = field(default_factory=time.time)
    playtime: float = 0.0
    level_name: str = ""
    thumbnail_ref: str = ""
    checksum: str = ""
    description: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "slot_name": self.slot_name,
            "slot_type": self.slot_type.value,
            "game_version": self.game_version,
            "timestamp": self.timestamp,
            "playtime": self.playtime,
            "level_name": self.level_name,
            "thumbnail_ref": self.thumbnail_ref,
            "checksum": self.checksum,
            "description": self.description,
            "metadata": dict(self.metadata),
        }


@dataclass
class SaveData:
    """Complete save data containing game state and entity information."""

    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    metadata: SaveMetadata = field(default_factory=SaveMetadata)
    game_state: Dict[str, Any] = field(default_factory=dict)
    entity_states: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    variables: Dict[str, Any] = field(default_factory=dict)
    flags: Dict[str, bool] = field(default_factory=dict)
    inventory: List[Dict[str, Any]] = field(default_factory=list)
    achievements: List[Dict[str, Any]] = field(default_factory=list)
    scene_id: str = ""
    format: SaveFormat = SaveFormat.JSON
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "metadata": self.metadata.to_dict(),
            "game_state": dict(self.game_state),
            "entity_states": {
                eid: dict(state) for eid, state in self.entity_states.items()
            },
            "variables": dict(self.variables),
            "flags": dict(self.flags),
            "inventory": list(self.inventory),
            "achievements": list(self.achievements),
            "scene_id": self.scene_id,
            "format": self.format.value,
            "metadata": dict(self.metadata),
        }


@dataclass
class SaveSlot:
    """A named save slot with history of save data entries."""

    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    slot_index: int = 0
    slot_type: SaveSlotType = SaveSlotType.MANUAL
    current_save: Optional[SaveData] = None
    save_history: List[SaveData] = field(default_factory=list)
    max_history: int = 10
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "slot_index": self.slot_index,
            "slot_type": self.slot_type.value,
            "has_current_save": self.current_save is not None,
            "history_count": len(self.save_history),
            "max_history": self.max_history,
            "metadata": dict(self.metadata),
        }


# ---------------------------------------------------------------------------
# Save System Engine
# ---------------------------------------------------------------------------

class SaveSystemEngine:
    """
    Game save/load system with serialization, versioning, and verification.

    Manages save slots, supports multiple save formats, automatic backups
    through history, and integrity verification via checksums. Provides
    export and import for save data portability.
    """

    _instance: Optional["SaveSystemEngine"] = None
    _lock = threading.RLock()

    _DEFAULT_MAX_HISTORY: int = 10
    _DEFAULT_GAME_VERSION: str = "1.0.0"

    def __new__(cls) -> "SaveSystemEngine":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    @classmethod
    def get_instance(cls) -> "SaveSystemEngine":
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

        self._slots: Dict[str, SaveSlot] = {}
        self._slot_index_map: Dict[int, str] = {}
        self._status: SaveStatus = SaveStatus.IDLE
        self._save_count: int = 0
        self._load_count: int = 0
        self._verify_count: int = 0
        self._corrupted_count: int = 0
        self._creation_time: float = time.time()
        self._version_migrations: Dict[str, Callable[[SaveData], SaveData]] = {}

    # ------------------------------------------------------------------
    # Slot Management
    # ------------------------------------------------------------------

    def create_slot(
        self,
        slot_index: int,
        slot_type: SaveSlotType = SaveSlotType.MANUAL,
        max_history: int = _DEFAULT_MAX_HISTORY,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> SaveSlot:
        """Create a new save slot.

        If a slot with the given index already exists, returns the existing slot.

        Args:
            slot_index: Numeric index for the slot (e.g., 0, 1, 2).
            slot_type: Type classification for the slot.
            max_history: Maximum number of historical saves to retain.
            metadata: Optional arbitrary metadata.

        Returns:
            The created or existing SaveSlot.
        """
        with self._lock:
            existing_id = self._slot_index_map.get(slot_index)
            if existing_id is not None and existing_id in self._slots:
                return self._slots[existing_id]

            slot = SaveSlot(
                slot_index=slot_index,
                slot_type=slot_type,
                max_history=max_history,
                metadata=metadata or {},
            )
            self._slots[slot.id] = slot
            self._slot_index_map[slot_index] = slot.id
            return slot

    def get_slot(self, slot_index: int) -> Optional[SaveSlot]:
        """Get a save slot by its index."""
        slot_id = self._slot_index_map.get(slot_index)
        if slot_id is None:
            return None
        return self._slots.get(slot_id)

    def list_slots(self) -> List[SaveSlot]:
        """List all save slots sorted by slot index."""
        with self._lock:
            return sorted(
                self._slots.values(), key=lambda s: s.slot_index
            )

    def delete_slot(self, slot_index: int) -> bool:
        """Delete a save slot and all its save data."""
        with self._lock:
            slot_id = self._slot_index_map.pop(slot_index, None)
            if slot_id is None:
                return False
            if slot_id in self._slots:
                del self._slots[slot_id]
                return True
            return False

    # ------------------------------------------------------------------
    # Save
    # ------------------------------------------------------------------

    def save(
        self,
        slot_index: int,
        game_state: Dict[str, Any],
        entity_states: Optional[Dict[str, Dict[str, Any]]] = None,
        variables: Optional[Dict[str, Any]] = None,
        flags: Optional[Dict[str, bool]] = None,
        inventory: Optional[List[Dict[str, Any]]] = None,
        achievements: Optional[List[Dict[str, Any]]] = None,
        scene_id: str = "",
        format: SaveFormat = SaveFormat.JSON,
        description: str = "",
        level_name: str = "",
        playtime: float = 0.0,
        game_version: str = _DEFAULT_GAME_VERSION,
    ) -> Optional[SaveData]:
        """Save game state to a slot.

        Creates a SaveData entry with metadata, computes a checksum for
        integrity verification, and stores it in the slot. The previous
        save is moved to the history, and old history entries are pruned.

        Returns:
            The newly created SaveData, or None if the slot doesn't exist.
        """
        with self._lock:
            self._status = SaveStatus.SAVING

            slot = self.get_slot(slot_index)
            if slot is None:
                self._status = SaveStatus.IDLE
                return None

            metadata = SaveMetadata(
                slot_name=f"slot_{slot_index}",
                slot_type=slot.slot_type,
                game_version=game_version,
                timestamp=time.time(),
                playtime=playtime,
                level_name=level_name,
                description=description,
            )

            save_data = SaveData(
                metadata=metadata,
                game_state=dict(game_state),
                entity_states=entity_states or {},
                variables=variables or {},
                flags=flags or {},
                inventory=inventory or [],
                achievements=achievements or [],
                scene_id=scene_id,
                format=format,
            )

            # Compute checksum
            save_data.metadata.checksum = self._compute_checksum(save_data)

            # Move current save to history
            if slot.current_save is not None:
                slot.save_history.append(slot.current_save)
                # Prune old history
                while len(slot.save_history) > slot.max_history:
                    slot.save_history.pop(0)

            slot.current_save = save_data
            self._save_count += 1
            self._status = SaveStatus.IDLE

            return save_data

    def quick_save(
        self,
        game_state: Dict[str, Any],
        slot_index: int = 0,
        **kwargs: Any,
    ) -> Optional[SaveData]:
        """Convenience method for a quick save to the default slot."""
        return self.save(
            slot_index=slot_index,
            game_state=game_state,
            **kwargs,
        )

    def auto_save(
        self,
        game_state: Dict[str, Any],
        slot_index: int = -1,
        **kwargs: Any,
    ) -> Optional[SaveData]:
        """Convenience method for an auto-save to a dedicated auto-save slot."""
        # Create the auto-save slot if it doesn't exist
        self.create_slot(slot_index, slot_type=SaveSlotType.AUTO)
        return self.save(
            slot_index=slot_index,
            game_state=game_state,
            **kwargs,
        )

    # ------------------------------------------------------------------
    # Load
    # ------------------------------------------------------------------

    def load(self, slot_index: int, verify: bool = True) -> Optional[SaveData]:
        """Load the current save data from a slot.

        If verify is True, checks the integrity of the save data before
        returning it. If verification fails, the save is marked as corrupted.

        Returns:
            The loaded SaveData, or None if the slot is empty or corrupted.
        """
        with self._lock:
            self._status = SaveStatus.LOADING

            slot = self.get_slot(slot_index)
            if slot is None or slot.current_save is None:
                self._status = SaveStatus.IDLE
                return None

            if verify:
                self._status = SaveStatus.VERIFYING
                self._verify_count += 1
                if not self._verify_data(slot.current_save):
                    slot.current_save.metadata.metadata["corrupted"] = True
                    self._corrupted_count += 1
                    self._status = SaveStatus.CORRUPTED
                    return None

            self._load_count += 1
            self._status = SaveStatus.IDLE
            return slot.current_save

    def load_from_history(
        self, slot_index: int, history_index: int, verify: bool = True
    ) -> Optional[SaveData]:
        """Load a historical save from a slot's history.

        Args:
            slot_index: The slot to load from.
            history_index: Index into the slot's save_history (0 is oldest).
            verify: Whether to verify integrity before returning.

        Returns:
            The historical SaveData, or None if not found or corrupted.
        """
        with self._lock:
            slot = self.get_slot(slot_index)
            if slot is None:
                return None
            if history_index < 0 or history_index >= len(slot.save_history):
                return None

            save_data = slot.save_history[history_index]

            if verify:
                self._verify_count += 1
                if not self._verify_data(save_data):
                    self._corrupted_count += 1
                    return None

            self._load_count += 1
            return save_data

    def get_latest_save(self, slot_type: Optional[SaveSlotType] = None) -> Optional[SaveData]:
        """Get the most recent save across all slots, optionally filtered by type.

        Returns:
            The SaveData with the most recent timestamp, or None if no saves exist.
        """
        with self._lock:
            latest: Optional[SaveData] = None
            latest_time = 0.0

            for slot in self._slots.values():
                if slot_type is not None and slot.slot_type != slot_type:
                    continue
                if slot.current_save is not None:
                    ts = slot.current_save.metadata.timestamp
                    if ts > latest_time:
                        latest_time = ts
                        latest = slot.current_save

            return latest

    # ------------------------------------------------------------------
    # Delete
    # ------------------------------------------------------------------

    def delete_save(self, slot_index: int) -> bool:
        """Delete the current save from a slot without removing the slot.

        The most recent historical save becomes the current save if available.
        """
        with self._lock:
            slot = self.get_slot(slot_index)
            if slot is None or slot.current_save is None:
                return False

            slot.current_save = None

            # Promote the most recent history entry
            if slot.save_history:
                slot.current_save = slot.save_history.pop()

            return True

    # ------------------------------------------------------------------
    # List Saves
    # ------------------------------------------------------------------

    def list_saves(self, slot_type: Optional[SaveSlotType] = None) -> List[Dict[str, Any]]:
        """List all current saves across slots, optionally filtered by type.

        Returns:
            A list of dictionaries with slot info and save metadata.
        """
        with self._lock:
            result: List[Dict[str, Any]] = []
            for slot in self._slots.values():
                if slot_type is not None and slot.slot_type != slot_type:
                    continue
                if slot.current_save is None:
                    continue
                result.append({
                    "slot_index": slot.slot_index,
                    "slot_type": slot.slot_type.value,
                    "save_id": slot.current_save.id,
                    "metadata": slot.current_save.metadata.to_dict(),
                    "history_count": len(slot.save_history),
                    "scene_id": slot.current_save.scene_id,
                })
            result.sort(key=lambda s: s["metadata"].get("timestamp", 0), reverse=True)
            return result

    # ------------------------------------------------------------------
    # Verify
    # ------------------------------------------------------------------

    def verify_save(self, slot_index: int) -> bool:
        """Verify the integrity of a slot's current save data."""
        with self._lock:
            slot = self.get_slot(slot_index)
            if slot is None or slot.current_save is None:
                return False

            self._status = SaveStatus.VERIFYING
            self._verify_count += 1
            valid = self._verify_data(slot.current_save)

            if not valid:
                self._corrupted_count += 1
                self._status = SaveStatus.CORRUPTED
            else:
                self._status = SaveStatus.IDLE

            return valid

    def _verify_data(self, save_data: SaveData) -> bool:
        """Verify the integrity of save data by recomputing the checksum."""
        if not save_data.metadata.checksum:
            return False

        computed = self._compute_checksum(save_data)
        return computed == save_data.metadata.checksum

    def _compute_checksum(self, save_data: SaveData) -> str:
        """Compute an SHA-256 checksum of the save data's content."""
        content = json.dumps({
            "game_state": save_data.game_state,
            "entity_states": save_data.entity_states,
            "variables": save_data.variables,
            "flags": save_data.flags,
            "inventory": save_data.inventory,
            "achievements": save_data.achievements,
            "scene_id": save_data.scene_id,
            "version": save_data.metadata.game_version,
        }, sort_keys=True, default=str)

        return hashlib.sha256(content.encode("utf-8")).hexdigest()

    # ------------------------------------------------------------------
    # Export / Import
    # ------------------------------------------------------------------

    def export_save(
        self,
        slot_index: int,
        format: SaveFormat = SaveFormat.JSON,
    ) -> Optional[bytes]:
        """Export a save to a portable byte representation.

        Supports JSON (human-readable), BINARY (compact), and COMPRESSED
        (zlib-compressed JSON) formats.

        Args:
            slot_index: The slot to export.
            format: The desired output format.

        Returns:
            Bytes of the serialized save data, or None if export fails.
        """
        with self._lock:
            slot = self.get_slot(slot_index)
            if slot is None or slot.current_save is None:
                return None

            save_data = slot.current_save
            save_dict = save_data.to_dict()

            if format == SaveFormat.JSON:
                return json.dumps(save_dict, indent=2, default=str).encode("utf-8")
            elif format == SaveFormat.BINARY:
                return json.dumps(save_dict, separators=(",", ":"), default=str).encode("utf-8")
            elif format == SaveFormat.COMPRESSED:
                json_bytes = json.dumps(save_dict, separators=(",", ":"), default=str).encode("utf-8")
                return zlib.compress(json_bytes)
            elif format == SaveFormat.CLOUD:
                # Cloud format wraps compressed data with a header
                compressed = zlib.compress(
                    json.dumps(save_dict, separators=(",", ":"), default=str).encode("utf-8")
                )
                header = json.dumps({
                    "version": save_data.metadata.game_version,
                    "timestamp": save_data.metadata.timestamp,
                    "checksum": save_data.metadata.checksum,
                    "size": len(compressed),
                }).encode("utf-8")
                header_len = len(header).to_bytes(4, "big")
                return header_len + header + compressed

            return None

    def import_save(
        self,
        slot_index: int,
        data: bytes,
        format: SaveFormat = SaveFormat.JSON,
    ) -> Optional[SaveData]:
        """Import save data from a byte representation into a slot.

        Supports the same formats as export_save. The imported save
        replaces the current save in the slot.

        Args:
            slot_index: The target slot for the imported save.
            data: The serialized save data bytes.
            format: The format of the input data.

        Returns:
            The imported SaveData, or None if import fails.
        """
        with self._lock:
            self._status = SaveStatus.LOADING

            try:
                if format == SaveFormat.JSON:
                    save_dict = json.loads(data.decode("utf-8"))
                elif format == SaveFormat.BINARY:
                    save_dict = json.loads(data.decode("utf-8"))
                elif format == SaveFormat.COMPRESSED:
                    decompressed = zlib.decompress(data)
                    save_dict = json.loads(decompressed.decode("utf-8"))
                elif format == SaveFormat.CLOUD:
                    header_len = int.from_bytes(data[:4], "big")
                    header = json.loads(data[4:4 + header_len].decode("utf-8"))
                    compressed = data[4 + header_len:]
                    decompressed = zlib.decompress(compressed)
                    save_dict = json.loads(decompressed.decode("utf-8"))
                else:
                    return None
            except (json.JSONDecodeError, zlib.error, UnicodeDecodeError, KeyError):
                self._status = SaveStatus.CORRUPTED
                self._corrupted_count += 1
                return None

            # Reconstruct SaveData from dict
            save_data = self._dict_to_save_data(save_dict)

            # Run version migrations if needed
            save_data = self._apply_migrations(save_data)

            # Ensure the slot exists
            slot = self.get_slot(slot_index)
            if slot is None:
                slot = self.create_slot(slot_index)

            # Move current save to history
            if slot.current_save is not None:
                slot.save_history.append(slot.current_save)
                while len(slot.save_history) > slot.max_history:
                    slot.save_history.pop(0)

            slot.current_save = save_data
            self._save_count += 1
            self._status = SaveStatus.IDLE
            return save_data

    def _dict_to_save_data(self, d: Dict[str, Any]) -> SaveData:
        """Reconstruct a SaveData object from a dictionary."""
        meta_dict = d.get("metadata", {})
        metadata = SaveMetadata(
            id=meta_dict.get("id", uuid.uuid4().hex[:12]),
            slot_name=meta_dict.get("slot_name", ""),
            slot_type=SaveSlotType(meta_dict.get("slot_type", "manual")),
            game_version=meta_dict.get("game_version", "1.0.0"),
            timestamp=meta_dict.get("timestamp", time.time()),
            playtime=meta_dict.get("playtime", 0.0),
            level_name=meta_dict.get("level_name", ""),
            thumbnail_ref=meta_dict.get("thumbnail_ref", ""),
            checksum=meta_dict.get("checksum", ""),
            description=meta_dict.get("description", ""),
            metadata=meta_dict.get("metadata", {}),
        )

        try:
            fmt = SaveFormat(d.get("format", "json"))
        except ValueError:
            fmt = SaveFormat.JSON

        return SaveData(
            id=d.get("id", uuid.uuid4().hex[:12]),
            metadata=metadata,
            game_state=d.get("game_state", {}),
            entity_states=d.get("entity_states", {}),
            variables=d.get("variables", {}),
            flags=d.get("flags", {}),
            inventory=d.get("inventory", []),
            achievements=d.get("achievements", []),
            scene_id=d.get("scene_id", ""),
            format=fmt,
        )

    # ------------------------------------------------------------------
    # Version Migration
    # ------------------------------------------------------------------

    def register_migration(
        self,
        from_version: str,
        to_version: str,
        migration_fn: Callable[[SaveData], SaveData],
    ) -> bool:
        """Register a migration function for upgrading save data versions.

        Args:
            from_version: The source game version.
            to_version: The target game version after migration.
            migration_fn: A function that takes a SaveData and returns a migrated SaveData.

        Returns:
            True if the migration was registered successfully.
        """
        with self._lock:
            key = f"{from_version}->{to_version}"
            if key in self._version_migrations:
                return False
            self._version_migrations[key] = migration_fn
            return True

    def _apply_migrations(self, save_data: SaveData) -> SaveData:
        """Apply all registered version migrations to a save data.

        Migrations are applied sequentially until the save version matches
        the current game version.
        """
        current_version = save_data.metadata.game_version

        # Build a chain of migrations
        applied = True
        while applied:
            applied = False
            for key, migration_fn in list(self._version_migrations.items()):
                from_ver, to_ver = key.split("->", 1)
                if from_ver == current_version:
                    save_data = migration_fn(save_data)
                    save_data.metadata.game_version = to_ver
                    current_version = to_ver
                    applied = True
                    break

        return save_data

    # ------------------------------------------------------------------
    # Statistics
    # ------------------------------------------------------------------

    def get_stats(self) -> Dict[str, Any]:
        """Get engine statistics including save counts and slot information."""
        with self._lock:
            total_saves = 0
            total_history = 0
            slot_details: List[Dict[str, Any]] = []

            for slot in self._slots.values():
                has_save = slot.current_save is not None
                if has_save:
                    total_saves += 1
                total_history += len(slot.save_history)
                slot_details.append({
                    "slot_index": slot.slot_index,
                    "slot_type": slot.slot_type.value,
                    "has_current_save": has_save,
                    "history_count": len(slot.save_history),
                    "max_history": slot.max_history,
                })

            slot_details.sort(key=lambda s: s["slot_index"])

            return {
                "slot_count": len(self._slots),
                "total_saves": total_saves,
                "total_history_entries": total_history,
                "save_count": self._save_count,
                "load_count": self._load_count,
                "verify_count": self._verify_count,
                "corrupted_count": self._corrupted_count,
                "status": self._status.value,
                "migration_count": len(self._version_migrations),
                "uptime_seconds": round(time.time() - self._creation_time, 1),
                "slots": slot_details,
            }

    # ------------------------------------------------------------------
    # Reset
    # ------------------------------------------------------------------

    def reset(self) -> None:
        """Reset the entire save system engine state."""
        with self._lock:
            self._slots.clear()
            self._slot_index_map.clear()
            self._status = SaveStatus.IDLE
            self._save_count = 0
            self._load_count = 0
            self._verify_count = 0
            self._corrupted_count = 0
            self._version_migrations.clear()
            self._creation_time = time.time()


# ---------------------------------------------------------------------------
# Factory Function
# ---------------------------------------------------------------------------


def get_save_system() -> SaveSystemEngine:
    """Get or create the singleton SaveSystemEngine instance."""
    return SaveSystemEngine.get_instance()