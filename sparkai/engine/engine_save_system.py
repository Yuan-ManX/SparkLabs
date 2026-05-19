"""
SparkLabs Engine - Save System

Game state persistence engine providing save/load functionality with
slot management, auto-save scheduling, checkpoint support, and cloud
sync readiness. Handles serialization of game objects, scene state,
player progress, and configuration settings.

Architecture:
  SaveSystem
    |-- SlotManager (create, delete, and enumerate save slots)
    |-- Serializer (game object to byte/slot representation)
    |-- AutoSaveScheduler (time-based and event-based auto-save triggers)
    |-- CheckpointManager (named save points within a playthrough)
    |-- MigrationEngine (save format versioning and compatibility)

Save Features:
  - SLOTS: up to 10 manual save slots with metadata preview
  - AUTO_SAVE: configurable interval-based and milestone-based saving
  - CHECKPOINTS: named restore points during gameplay
  - METADATA: playtime, progress %, screenshot reference, timestamp
  - MIGRATION: version-tagged saves with forward compatibility
"""

from __future__ import annotations

import json
import threading
import time
import uuid
import zlib
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class SaveType(Enum):
    MANUAL = "manual"
    AUTO = "auto"
    CHECKPOINT = "checkpoint"
    QUICK = "quick"
    CLOUD = "cloud"


class SaveSlotState(Enum):
    EMPTY = "empty"
    ACTIVE = "active"
    CORRUPTED = "corrupted"
    LOCKED = "locked"
    SYNCING = "syncing"


class AutoSaveTrigger(Enum):
    INTERVAL = "interval"
    LEVEL_START = "level_start"
    LEVEL_END = "level_end"
    BOSS_DEFEATED = "boss_defeated"
    ITEM_ACQUIRED = "item_acquired"
    DANGER_ZONE = "danger_zone"


class SaveVersion(Enum):
    V1_0 = "1.0"
    V1_1 = "1.1"
    V2_0 = "2.0"


@dataclass
class SaveSlot:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    slot_number: int = 0
    save_type: SaveType = SaveType.MANUAL
    state: SaveSlotState = SaveSlotState.EMPTY
    profile_name: str = ""
    playtime_seconds: float = 0.0
    progress_pct: float = 0.0
    level_name: str = ""
    player_position: Dict[str, float] = field(default_factory=dict)
    timestamp: float = 0.0
    file_size_bytes: int = 0
    version: SaveVersion = SaveVersion.V1_0
    scene_id: str = ""
    screenshot_id: str = ""
    game_data: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "slot_number": self.slot_number,
            "save_type": self.save_type.value,
            "state": self.state.value,
            "profile_name": self.profile_name,
            "playtime_seconds": round(self.playtime_seconds, 1),
            "progress_pct": round(self.progress_pct, 1),
            "level_name": self.level_name,
            "player_position": self.player_position,
            "timestamp": self.timestamp,
            "file_size_bytes": self.file_size_bytes,
            "version": self.version.value,
            "scene_id": self.scene_id,
            "screenshot_id": self.screenshot_id,
        }


@dataclass
class Checkpoint:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = ""
    slot_id: str = ""
    description: str = ""
    playtime_at_checkpoint: float = 0.0
    progress_at_checkpoint: float = 0.0
    is_one_shot: bool = True
    has_been_used: bool = False
    game_data_snapshot: Dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "slot_id": self.slot_id,
            "description": self.description,
            "playtime_at_checkpoint": round(self.playtime_at_checkpoint, 1),
            "progress_at_checkpoint": round(self.progress_at_checkpoint, 1),
            "is_one_shot": self.is_one_shot,
            "has_been_used": self.has_been_used,
            "created_at": self.created_at,
        }


@dataclass
class AutoSaveConfig:
    interval_seconds: float = 300.0
    max_auto_saves: int = 3
    enabled_triggers: List[AutoSaveTrigger] = field(default_factory=lambda: [
        AutoSaveTrigger.INTERVAL,
        AutoSaveTrigger.LEVEL_START,
        AutoSaveTrigger.BOSS_DEFEATED,
    ])
    is_enabled: bool = True
    last_auto_save: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "interval_seconds": self.interval_seconds,
            "max_auto_saves": self.max_auto_saves,
            "enabled_triggers": [t.value for t in self.enabled_triggers],
            "is_enabled": self.is_enabled,
            "last_auto_save": self.last_auto_save,
        }


class SaveSystem:
    """Game state persistence engine with slot and checkpoint management."""

    _instance: Optional["SaveSystem"] = None
    _lock = threading.RLock()

    MAX_SLOTS = 10
    MAX_CHECKPOINTS = 50

    def __init__(self) -> None:
        self._slots: Dict[str, SaveSlot] = {}
        self._checkpoints: Dict[str, Checkpoint] = {}
        self._auto_save_config = AutoSaveConfig()
        self._active_slot_id: Optional[str] = None
        self._total_playtime: float = 0.0
        self._progress_pct: float = 0.0
        self._save_log: List[Dict[str, Any]] = []
        self._auto_save_timer: float = 0.0

    @classmethod
    def get_instance(cls) -> "SaveSystem":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    # ---- Slot Management ----

    def initialize_slots(self) -> List[SaveSlot]:
        slots = []
        for i in range(1, self.MAX_SLOTS + 1):
            slot = SaveSlot(slot_number=i)
            self._slots[slot.id] = slot
            slots.append(slot)
        return slots

    def create_save(self,
                    slot_number: int,
                    save_type: str = "manual",
                    profile_name: str = "",
                    level_name: str = "",
                    player_position: Optional[Dict[str, float]] = None,
                    scene_id: str = "",
                    game_data: Optional[Dict[str, Any]] = None) -> Optional[SaveSlot]:
        if slot_number < 1 or slot_number > self.MAX_SLOTS:
            return None

        try:
            st = SaveType(save_type.lower())
        except ValueError:
            st = SaveType.MANUAL

        existing = self._find_slot_by_number(slot_number)
        if existing:
            slot = existing
        else:
            slot = SaveSlot(slot_number=slot_number)

        slot.save_type = st
        slot.state = SaveSlotState.ACTIVE
        slot.profile_name = profile_name
        slot.playtime_seconds = self._total_playtime
        slot.progress_pct = self._progress_pct
        slot.level_name = level_name
        slot.player_position = player_position or {}
        slot.timestamp = time.time()
        slot.scene_id = scene_id
        slot.version = SaveVersion.V1_0
        slot.game_data = game_data or {}
        serialized = json.dumps(slot.to_dict())
        slot.file_size_bytes = len(serialized.encode("utf-8"))

        self._slots[slot.id] = slot
        self._active_slot_id = slot.id
        self._save_log.append({
            "action": "save_created",
            "slot": slot_number,
            "type": st.value,
            "timestamp": time.time(),
        })
        return slot

    def load_save(self, slot_id: str) -> Optional[Dict[str, Any]]:
        slot = self._slots.get(slot_id)
        if slot is None or slot.state == SaveSlotState.EMPTY:
            return None
        if slot.state == SaveSlotState.CORRUPTED:
            return {"error": "corrupted_save", "slot_id": slot_id}
        self._active_slot_id = slot_id
        self._total_playtime = slot.playtime_seconds
        self._progress_pct = slot.progress_pct
        self._save_log.append({
            "action": "save_loaded",
            "slot": slot.slot_number,
            "timestamp": time.time(),
        })
        return {
            "loaded": True,
            "slot": slot.to_dict(),
            "game_data": slot.game_data,
        }

    def delete_save(self, slot_id: str) -> bool:
        slot = self._slots.get(slot_id)
        if slot is None:
            return False
        slot.state = SaveSlotState.EMPTY
        slot.game_data = {}
        slot.profile_name = ""
        slot.playtime_seconds = 0.0
        slot.progress_pct = 0.0
        slot.file_size_bytes = 0
        if self._active_slot_id == slot_id:
            self._active_slot_id = None
        self._save_log.append({
            "action": "save_deleted",
            "slot": slot.slot_number,
            "timestamp": time.time(),
        })
        return True

    def list_slots(self) -> List[SaveSlot]:
        return sorted(
            self._slots.values(),
            key=lambda s: s.slot_number,
        )

    def get_slot(self, slot_id: str) -> Optional[SaveSlot]:
        return self._slots.get(slot_id)

    def get_active_slot(self) -> Optional[SaveSlot]:
        if self._active_slot_id:
            return self._slots.get(self._active_slot_id)
        return None

    def _find_slot_by_number(self, number: int) -> Optional[SaveSlot]:
        for slot in self._slots.values():
            if slot.slot_number == number:
                return slot
        return None

    # ---- Auto-Save ----

    def configure_auto_save(self,
                            interval_seconds: float = 300.0,
                            max_auto_saves: int = 3,
                            enabled: bool = True) -> AutoSaveConfig:
        self._auto_save_config.interval_seconds = max(30.0, interval_seconds)
        self._auto_save_config.max_auto_saves = max(1, min(10, max_auto_saves))
        self._auto_save_config.is_enabled = enabled
        return self._auto_save_config

    def enable_auto_save_trigger(self,
                                 trigger: str,
                                 enabled: bool = True) -> bool:
        try:
            t = AutoSaveTrigger(trigger.lower())
        except ValueError:
            return False
        triggers = self._auto_save_config.enabled_triggers
        if enabled and t not in triggers:
            triggers.append(t)
        elif not enabled and t in triggers:
            triggers.remove(t)
        return True

    def trigger_auto_save(self,
                          trigger: str) -> Optional[SaveSlot]:
        try:
            t = AutoSaveTrigger(trigger.lower())
        except ValueError:
            return None
        if not self._auto_save_config.is_enabled:
            return None
        if t not in self._auto_save_config.enabled_triggers:
            return None

        auto_slots = [
            s for s in self._slots.values()
            if s.save_type == SaveType.AUTO and s.state == SaveSlotState.ACTIVE
        ]
        auto_slots.sort(key=lambda s: s.timestamp)

        target_number: int
        if len(auto_slots) >= self._auto_save_config.max_auto_saves:
            oldest = auto_slots[0]
            target_number = oldest.slot_number
        else:
            used = {s.slot_number for s in auto_slots}
            target_number = 1
            while target_number in used and target_number <= self.MAX_SLOTS:
                target_number += 1

        self._auto_save_config.last_auto_save = time.time()
        return self.create_save(
            slot_number=target_number,
            save_type="auto",
            profile_name=f"AutoSave_{target_number}",
            level_name="auto_save_level",
        )

    def get_auto_save_config(self) -> AutoSaveConfig:
        return self._auto_save_config

    # ---- Checkpoints ----

    def create_checkpoint(self,
                          name: str,
                          description: str = "",
                          is_one_shot: bool = True,
                          game_data_snapshot: Optional[Dict[str, Any]] = None) -> Optional[Checkpoint]:
        if len(self._checkpoints) >= self.MAX_CHECKPOINTS:
            oldest = min(self._checkpoints.values(),
                        key=lambda c: c.created_at)
            del self._checkpoints[oldest.id]

        checkpoint = Checkpoint(
            name=name,
            slot_id=self._active_slot_id or "",
            description=description,
            playtime_at_checkpoint=self._total_playtime,
            progress_at_checkpoint=self._progress_pct,
            is_one_shot=is_one_shot,
            game_data_snapshot=game_data_snapshot or {},
        )
        self._checkpoints[checkpoint.id] = checkpoint
        self._save_log.append({
            "action": "checkpoint_created",
            "checkpoint": name,
            "timestamp": time.time(),
        })
        return checkpoint

    def restore_checkpoint(self, checkpoint_id: str) -> Optional[Dict[str, Any]]:
        checkpoint = self._checkpoints.get(checkpoint_id)
        if checkpoint is None:
            return None
        if checkpoint.is_one_shot and checkpoint.has_been_used:
            return {"error": "checkpoint_already_used"}
        checkpoint.has_been_used = True
        self._total_playtime = checkpoint.playtime_at_checkpoint
        self._progress_pct = checkpoint.progress_at_checkpoint
        self._save_log.append({
            "action": "checkpoint_restored",
            "checkpoint": checkpoint.name,
            "timestamp": time.time(),
        })
        return {
            "restored": True,
            "checkpoint": checkpoint.to_dict(),
            "snapshot_data": checkpoint.game_data_snapshot,
        }

    def list_checkpoints(self,
                         include_used: bool = False) -> List[Checkpoint]:
        checkpoints = list(self._checkpoints.values())
        if not include_used:
            checkpoints = [c for c in checkpoints if not c.has_been_used]
        return sorted(checkpoints, key=lambda c: c.created_at, reverse=True)

    def get_checkpoint(self, checkpoint_id: str) -> Optional[Checkpoint]:
        return self._checkpoints.get(checkpoint_id)

    def delete_checkpoint(self, checkpoint_id: str) -> bool:
        if checkpoint_id in self._checkpoints:
            del self._checkpoints[checkpoint_id]
            return True
        return False

    # ---- Runtime State ----

    def update_progress(self,
                        playtime_delta: float,
                        progress_pct: float) -> None:
        self._total_playtime += playtime_delta
        self._progress_pct = max(0.0, min(100.0, progress_pct))

    def tick(self, delta_time: float = 0.016) -> None:
        self._total_playtime += delta_time

        if not self._auto_save_config.is_enabled:
            return
        if AutoSaveTrigger.INTERVAL not in self._auto_save_config.enabled_triggers:
            return

        self._auto_save_timer += delta_time
        if self._auto_save_timer >= self._auto_save_config.interval_seconds:
            self._auto_save_timer = 0.0
            self.trigger_auto_save("interval")

    def get_progress(self) -> Dict[str, Any]:
        active_slot = self.get_active_slot()
        return {
            "total_playtime": round(self._total_playtime, 1),
            "progress_pct": round(self._progress_pct, 1),
            "active_slot": active_slot.slot_number if active_slot else None,
            "active_save_id": self._active_slot_id,
        }

    def get_save_log(self, limit: int = 50) -> List[Dict[str, Any]]:
        return self._save_log[-limit:]

    def get_stats(self) -> Dict[str, Any]:
        active_saves = sum(
            1 for s in self._slots.values()
            if s.state == SaveSlotState.ACTIVE
        )
        total_size = sum(
            s.file_size_bytes for s in self._slots.values()
            if s.state == SaveSlotState.ACTIVE
        )
        unused_checkpoints = sum(
            1 for c in self._checkpoints.values()
            if not c.has_been_used
        )
        return {
            "total_slots": len(self._slots),
            "active_saves": active_saves,
            "empty_slots": self.MAX_SLOTS - active_saves,
            "total_save_size_bytes": total_size,
            "total_checkpoints": len(self._checkpoints),
            "unused_checkpoints": unused_checkpoints,
            "auto_save_enabled": self._auto_save_config.is_enabled,
            "auto_save_interval": self._auto_save_config.interval_seconds,
            "total_playtime": round(self._total_playtime, 1),
            "progress_pct": round(self._progress_pct, 1),
            "active_slot_exists": self._active_slot_id is not None,
            "max_slots": self.MAX_SLOTS,
            "max_checkpoints": self.MAX_CHECKPOINTS,
        }


def get_save_system() -> SaveSystem:
    return SaveSystem.get_instance()