"""
SparkLabs Engine - Save System

Save/Load system with versioning, migration, and data integrity.
Handles game state serialization to disk with automatic format
migration between versions. Supports incremental saves, auto-save
rotation, and save slot management. Critical for preserving player
progress and enabling AI agents to checkpoint game states.

Architecture:
  SaveSystem
    |-- SaveSlot (metadata, version, timestamp, thumbnail)
    |-- SaveFormatter (serialization to/from disk format)
    |-- VersionMigrator (schema upgrade between save versions)
    |-- AutoSaveManager (interval-based background saving)
    |-- IntegrityVerifier (checksum validation)

Save Format:
  - HEADER: magic bytes, version, timestamp, slot name
  - METADATA: game title, playtime, scene reference
  - STATE: full scene state with entities and components
  - CHECKSUM: SHA-256 hash for integrity verification
"""

from __future__ import annotations

import hashlib
import json
import os
import threading
import time
import zlib
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional


SAVE_MAGIC = b"SPARKSAVE"
CURRENT_VERSION = 1


class SaveStatus(Enum):
    EMPTY = "empty"
    SAVED = "saved"
    CORRUPT = "corrupt"
    MIGRATED = "migrated"
    LOCKED = "locked"


@dataclass
class SaveSlot:
    slot_id: int
    name: str
    status: SaveStatus = SaveStatus.EMPTY
    version: int = CURRENT_VERSION
    saved_at: float = 0.0
    playtime_seconds: float = 0.0
    scene_name: str = ""
    game_title: str = ""
    thumbnail_key: str = ""
    checksum: str = ""
    size_bytes: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "slot_id": self.slot_id,
            "name": self.name,
            "status": self.status.value,
            "version": self.version,
            "saved_at": self.saved_at,
            "playtime_seconds": self.playtime_seconds,
            "scene_name": self.scene_name,
            "game_title": self.game_title,
            "size_bytes": self.size_bytes,
        }

    def formatted_playtime(self) -> str:
        h = int(self.playtime_seconds // 3600)
        m = int((self.playtime_seconds % 3600) // 60)
        s = int(self.playtime_seconds % 60)
        return f"{h:02d}:{m:02d}:{s:02d}"


@dataclass
class AutoSaveConfig:
    enabled: bool = True
    interval_seconds: float = 300.0
    max_auto_slots: int = 3
    slot_offset: int = 100


class SaveSystem:
    """
    Save/Load system with versioning and integrity checking.

    Manages save slots, auto-save rotation, format migration,
    and data integrity verification. Provides the AI agent with
    reliable state persistence for game projects and runtime
    game state checkpointing.
    """

    _instance: Optional["SaveSystem"] = None
    MAX_SLOTS: int = 20

    def __init__(self):
        self._slots: Dict[int, SaveSlot] = {}
        self._save_dir: str = ""
        self._auto_config = AutoSaveConfig()
        self._serializers: Dict[str, Callable] = {}
        self._migrators: Dict[int, Callable] = {}
        self._lock = threading.Lock()
        self._last_auto_save: float = 0.0
        self._init_slots()

    @classmethod
    def get_instance(cls) -> "SaveSystem":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def set_save_directory(self, path: str) -> None:
        self._save_dir = path
        os.makedirs(path, exist_ok=True)

    def save(
        self,
        slot_id: int,
        game_state: Dict[str, Any],
        name: str = "",
        scene_name: str = "",
        playtime_seconds: float = 0.0,
    ) -> Optional[SaveSlot]:
        if slot_id < 0 or slot_id > self.MAX_SLOTS:
            return None

        with self._lock:
            slot = self._slots.get(slot_id, SaveSlot(slot_id=slot_id, name=name))
            if slot.status == SaveStatus.LOCKED:
                return None

            try:
                state_json = json.dumps(game_state, default=str)
                compressed = zlib.compress(state_json.encode("utf-8"))
                checksum = hashlib.sha256(compressed).hexdigest()

                header = {
                    "magic": SAVE_MAGIC.hex(),
                    "version": CURRENT_VERSION,
                    "timestamp": time.time(),
                    "name": name or slot.name or f"Save {slot_id}",
                    "scene_name": scene_name,
                    "playtime_seconds": playtime_seconds,
                    "checksum": checksum,
                }

                if self._save_dir:
                    save_path = os.path.join(self._save_dir, f"save_{slot_id:03d}.sav")
                    with open(save_path, "wb") as f:
                        header_bytes = json.dumps(header).encode("utf-8")
                        f.write(len(header_bytes).to_bytes(4, "big"))
                        f.write(header_bytes)
                        f.write(compressed)

                slot.name = header["name"]
                slot.status = SaveStatus.SAVED
                slot.version = CURRENT_VERSION
                slot.saved_at = header["timestamp"]
                slot.playtime_seconds = playtime_seconds
                slot.scene_name = scene_name
                slot.checksum = checksum
                slot.size_bytes = len(compressed)

                self._slots[slot_id] = slot
                return slot

            except Exception:
                slot.status = SaveStatus.CORRUPT
                return None

    def load(self, slot_id: int) -> Optional[Dict[str, Any]]:
        with self._lock:
            slot = self._slots.get(slot_id)
            if not slot or slot.status != SaveStatus.SAVED:
                return None

            try:
                if not self._save_dir:
                    return None

                save_path = os.path.join(self._save_dir, f"save_{slot_id:03d}.sav")
                if not os.path.exists(save_path):
                    return None

                with open(save_path, "rb") as f:
                    header_len = int.from_bytes(f.read(4), "big")
                    header = json.loads(f.read(header_len).decode("utf-8"))
                    compressed = f.read()

                if header.get("magic") != SAVE_MAGIC.hex():
                    slot.status = SaveStatus.CORRUPT
                    return None

                version = header.get("version", 0)
                if version < CURRENT_VERSION and version in self._migrators:
                    compressed = self._migrators[version](compressed)
                    slot.status = SaveStatus.MIGRATED

                actual_checksum = hashlib.sha256(compressed).hexdigest()
                if header.get("checksum") != actual_checksum:
                    slot.status = SaveStatus.CORRUPT
                    return None

                decompressed = zlib.decompress(compressed)
                return json.loads(decompressed.decode("utf-8"))

            except Exception:
                slot.status = SaveStatus.CORRUPT
                return None

    def delete(self, slot_id: int) -> bool:
        with self._lock:
            if slot_id in self._slots:
                slot = self._slots[slot_id]
                if slot.status == SaveStatus.LOCKED:
                    return False
                slot.status = SaveStatus.EMPTY
                slot.checksum = ""
                slot.size_bytes = 0
                if self._save_dir:
                    save_path = os.path.join(self._save_dir, f"save_{slot_id:03d}.sav")
                    if os.path.exists(save_path):
                        os.remove(save_path)
                return True
            return False

    def lock_slot(self, slot_id: int) -> bool:
        with self._lock:
            slot = self._slots.get(slot_id)
            if not slot:
                return False
            slot.status = SaveStatus.LOCKED
            return True

    def unlock_slot(self, slot_id: int) -> bool:
        with self._lock:
            slot = self._slots.get(slot_id)
            if slot and slot.status == SaveStatus.LOCKED:
                slot.status = SaveStatus.SAVED
                return True
            return False

    def get_slot(self, slot_id: int) -> Optional[SaveSlot]:
        return self._slots.get(slot_id)

    def list_slots(self) -> List[SaveSlot]:
        return sorted(self._slots.values(), key=lambda s: s.slot_id)

    def list_saved(self) -> List[SaveSlot]:
        return [s for s in self._slots.values() if s.status == SaveStatus.SAVED]

    def find_empty_slot(self) -> Optional[int]:
        for i in range(self.MAX_SLOTS):
            slot = self._slots.get(i)
            if not slot or slot.status == SaveStatus.EMPTY:
                return i
        return None

    def export_save(self, slot_id: int, output_path: str) -> bool:
        state = self.load(slot_id)
        if state is None:
            return False
        try:
            with open(output_path, "w") as f:
                json.dump(state, f, indent=2, default=str)
            return True
        except Exception:
            return False

    def import_save(self, slot_id: int, input_path: str) -> Optional[SaveSlot]:
        try:
            with open(input_path, "r") as f:
                state = json.load(f)
            return self.save(slot_id, state)
        except Exception:
            return None

    def try_auto_save(self, game_state: Dict[str, Any]) -> bool:
        if not self._auto_config.enabled:
            return False
        now = time.time()
        if now - self._last_auto_save < self._auto_config.interval_seconds:
            return False

        with self._lock:
            offset = self._auto_config.slot_offset
            max_slots = self._auto_config.max_auto_slots
            existing = [
                s for s in self._slots.values()
                if offset <= s.slot_id < offset + max_slots and s.status == SaveStatus.SAVED
            ]

            if len(existing) >= max_slots:
                oldest = min(existing, key=lambda s: s.saved_at)
                self.delete(oldest.slot_id)

            target_slot = offset
            for s in sorted(existing, key=lambda s: s.slot_id):
                if s.slot_id >= target_slot:
                    target_slot += 1

            result = self.save(target_slot, game_state, name=f"Auto {target_slot - offset + 1}")
            if result:
                self._last_auto_save = now
            return result is not None

    def configure_auto_save(
        self, enabled: bool = True, interval: float = 300.0, max_slots: int = 3
    ) -> None:
        self._auto_config = AutoSaveConfig(
            enabled=enabled,
            interval_seconds=max(10.0, interval),
            max_auto_slots=max(1, min(10, max_slots)),
        )

    def register_migrator(self, version: int, migrator: Callable) -> None:
        self._migrators[version] = migrator

    def verify_integrity(self, slot_id: int) -> bool:
        with self._lock:
            slot = self._slots.get(slot_id)
            if not slot or slot.status != SaveStatus.SAVED:
                return False
            if not self._save_dir:
                return False
            save_path = os.path.join(self._save_dir, f"save_{slot_id:03d}.sav")
            if not os.path.exists(save_path):
                return False
            try:
                with open(save_path, "rb") as f:
                    header_len = int.from_bytes(f.read(4), "big")
                    header = json.loads(f.read(header_len).decode("utf-8"))
                    compressed = f.read()
                actual = hashlib.sha256(compressed).hexdigest()
                return header.get("checksum") == actual
            except Exception:
                return False

    def _init_slots(self) -> None:
        for i in range(self.MAX_SLOTS):
            self._slots[i] = SaveSlot(slot_id=i, name=f"Save {i+1}")

    def scan_directory(self) -> int:
        if not self._save_dir or not os.path.isdir(self._save_dir):
            return 0

        count = 0
        for fname in os.listdir(self._save_dir):
            if not fname.startswith("save_") or not fname.endswith(".sav"):
                continue
            try:
                slot_id = int(fname.replace("save_", "").replace(".sav", ""))
                if slot_id > self.MAX_SLOTS:
                    continue
                save_path = os.path.join(self._save_dir, fname)
                with open(save_path, "rb") as f:
                    header_len = int.from_bytes(f.read(4), "big")
                    header = json.loads(f.read(header_len).decode("utf-8"))

                slot = self._slots.get(slot_id, SaveSlot(slot_id=slot_id, name=header.get("name", "")))
                slot.name = header.get("name", "")
                slot.status = SaveStatus.SAVED
                slot.version = header.get("version", 0)
                slot.saved_at = header.get("timestamp", 0)
                slot.playtime_seconds = header.get("playtime_seconds", 0)
                slot.scene_name = header.get("scene_name", "")
                slot.checksum = header.get("checksum", "")
                slot.size_bytes = os.path.getsize(save_path)
                self._slots[slot_id] = slot
                count += 1
            except Exception:
                pass

        return count

    def get_stats(self) -> dict:
        with self._lock:
            saved = self.list_saved()
            auto_saved = sum(
                1 for s in saved
                if self._auto_config.slot_offset <= s.slot_id < self._auto_config.slot_offset + self._auto_config.max_auto_slots
            )
            return {
                "total_slots": len(self._slots),
                "saved_slots": len(saved),
                "empty_slots": sum(1 for s in self._slots.values() if s.status == SaveStatus.EMPTY),
                "corrupt_slots": sum(1 for s in self._slots.values() if s.status == SaveStatus.CORRUPT),
                "auto_save_enabled": self._auto_config.enabled,
                "auto_save_interval": self._auto_config.interval_seconds,
                "auto_saved": auto_saved,
                "save_directory": self._save_dir,
            }

    def reset(self) -> None:
        with self._lock:
            self._slots.clear()
            self._init_slots()
            self._last_auto_save = 0.0


def get_save_system() -> SaveSystem:
    return SaveSystem.get_instance()
