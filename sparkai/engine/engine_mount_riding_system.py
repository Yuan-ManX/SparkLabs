"""
SparkLabs Engine - Mount & Riding System

Manages rideable mounts that provide movement speed bonuses, flying,
aquatic traversal, and combat capabilities. Players collect, train,
customize, and summon mounts for faster world traversal and specialized
terrain navigation.

Architecture:
  MountRidingSystem (singleton)
    |-- MountType, MountTerrain, MountStatus, MountEventKind
    |-- MountDefinition, PlayerMount, MountSkin, MountEquipment,
       MountTrainingRecord, MountConfig, MountStats, MountSnapshot,
       MountEvent
    |-- get_mount_riding_system

Core Capabilities:
  - register_mount / remove_mount / get_mount / list_mounts
  - register_skin / get_skin / list_skins
  - acquire_mount / get_player_mount / list_player_mounts
  - summon_mount / dismiss_mount / get_active_mount
  - train_mount / get_training_record
  - equip_mount_item / unequip_mount_item
  - apply_skin / get_mount_skins
  - calculate_speed / get_speed_bonus
  - tick / set_config / get_config
  - list_events / get_stats / get_status / get_snapshot / reset

The class implements the singleton pattern with double-checked locking
using ``threading.RLock``; consumers should obtain the instance through
:meth:`MountRidingSystem.get_instance` or the module-level
:func:`get_mount_riding_system` factory.
"""

from __future__ import annotations

import threading
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Capacity Constants
# ---------------------------------------------------------------------------

_MAX_MOUNTS: int = 500
_MAX_SKINS: int = 2000
_MAX_PLAYER_MOUNTS: int = 100000
_MAX_TRAINING_RECORDS: int = 100000
_MAX_EVENTS: int = 10000


# ---------------------------------------------------------------------------
# Helper Functions
# ---------------------------------------------------------------------------

_LOCK = threading.RLock()


def _now() -> float:
    return time.time()


def _new_id(prefix: str = "") -> str:
    base = uuid.uuid4().hex[:12]
    return f"{prefix}_{base}" if prefix else base


def _safe_float(value: Any, default: float = 0.0) -> float:
    if value is None or value == "":
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _safe_int(value: Any, default: int = 0) -> int:
    if value is None or value == "":
        return default
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _clamp(value: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, value))


def _evict_fifo_list(store: List[Any], max_size: int) -> None:
    cap = max(1, int(max_size))
    while len(store) > cap:
        if not store:
            break
        store.pop(0)


def _dataclass_to_dict(obj: Any) -> Any:
    if hasattr(obj, "__dataclass_fields__"):
        result: Dict[str, Any] = {}
        for k in obj.__dataclass_fields__:
            v = getattr(obj, k)
            if hasattr(v, "__dataclass_fields__"):
                result[k] = _dataclass_to_dict(v)
            elif hasattr(v, "to_dict") and callable(v.to_dict):
                result[k] = v.to_dict()
            elif isinstance(v, list):
                result[k] = [_dataclass_to_dict(i) for i in v]
            elif isinstance(v, dict):
                result[k] = {kk: _dataclass_to_dict(vv) for kk, vv in v.items()}
            elif isinstance(v, tuple):
                result[k] = list(v)
            else:
                result[k] = v
        return result
    return obj


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class MountType(str, Enum):
    """Type of mount based on creature form."""
    GROUND = "ground"
    FLYING = "flying"
    AQUATIC = "aquatic"
    AMPHIBIOUS = "amphibious"
    ALL_TERRAIN = "all_terrain"


class MountTerrain(str, Enum):
    """Terrain types mounts can traverse."""
    LAND = "land"
    WATER = "water"
    AIR = "air"
    UNDERGROUND = "underground"
    LAVA = "lava"
    ICE = "ice"


class MountStatus(str, Enum):
    """Status of a player's mount."""
    STORED = "stored"
    SUMMONED = "summoned"
    COOLDOWN = "cooldown"
    TRAINING = "training"
    LOCKED = "locked"


class MountRarity(str, Enum):
    """Rarity tier for mounts."""
    COMMON = "common"
    UNCOMMON = "uncommon"
    RARE = "rare"
    EPIC = "epic"
    LEGENDARY = "legendary"
    MYTHIC = "mythic"


class TrainingType(str, Enum):
    """Types of mount training."""
    SPEED = "speed"
    STAMINA = "stamina"
    COMBAT = "combat"
    AGILITY = "agility"
    LOYALTY = "loyalty"


class MountEventKind(str, Enum):
    """Audit event types emitted by the mount riding system."""
    MOUNT_REGISTERED = "mount_registered"
    MOUNT_REMOVED = "mount_removed"
    SKIN_REGISTERED = "skin_registered"
    MOUNT_ACQUIRED = "mount_acquired"
    MOUNT_SUMMONED = "mount_summoned"
    MOUNT_DISMISSED = "mount_dismissed"
    MOUNT_TRAINED = "mount_trained"
    EQUIPMENT_EQUIPPED = "equipment_equipped"
    EQUIPMENT_UNEQUIPPED = "equipment_unequipped"
    SKIN_APPLIED = "skin_applied"
    CONFIG_UPDATED = "config_updated"
    RESET = "reset"
    TICK = "tick"


# ---------------------------------------------------------------------------
# Data Classes
# ---------------------------------------------------------------------------

@dataclass
class MountDefinition:
    """Definition of a mount species."""
    mount_id: str
    name: str
    description: str = ""
    mount_type: str = MountType.GROUND.value
    rarity: str = MountRarity.COMMON.value
    base_speed: float = 60.0
    max_speed: float = 100.0
    base_stamina: float = 100.0
    max_stamina: float = 100.0
    stamina_regen: float = 5.0
    allowed_terrains: List[str] = field(default_factory=lambda: [MountTerrain.LAND.value])
    combat_capable: bool = False
    combat_power: float = 0.0
    passenger_capacity: int = 1
    required_level: int = 1
    acquisition_method: str = "purchase"
    acquisition_cost: float = 100.0
    acquisition_currency: str = "gold"
    icon: str = ""
    model_id: str = ""
    color: str = "#FFFFFF"
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class MountSkin:
    """A cosmetic skin that can be applied to a mount."""
    skin_id: str
    name: str
    description: str = ""
    mount_id: str = ""
    rarity: str = MountRarity.UNCOMMON.value
    model_override: str = ""
    color_override: str = ""
    effect_id: str = ""
    acquisition_method: str = "shop"
    acquisition_cost: float = 0.0
    icon: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class MountEquipment:
    """Equipment slot data for a mount."""
    slot: str
    item_id: str = ""
    item_name: str = ""
    stat_bonuses: Dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class PlayerMount:
    """A player's owned mount instance."""
    pm_id: str
    player_id: str
    mount_id: str
    status: str = MountStatus.STORED.value
    level: int = 1
    experience: int = 0
    current_speed: float = 60.0
    current_stamina: float = 100.0
    max_stamina: float = 100.0
    loyalty: float = 50.0
    trained_stats: Dict[str, float] = field(default_factory=dict)
    equipped_slots: Dict[str, MountEquipment] = field(default_factory=dict)
    applied_skin_id: str = ""
    acquired_at: float = field(default_factory=_now)
    total_distance: float = 0.0
    total_playtime: float = 0.0
    summon_count: int = 0
    last_summoned: float = 0.0
    cooldown_until: float = 0.0
    custom_name: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def effective_speed(self) -> float:
        base = self.current_speed
        for eq in self.equipped_slots.values():
            base += eq.stat_bonuses.get("speed", 0.0)
        return min(base, 200.0)

    def to_dict(self) -> Dict[str, Any]:
        d = _dataclass_to_dict(self)
        d["effective_speed"] = self.effective_speed
        return d


@dataclass
class MountTrainingRecord:
    """Record of a training session for a mount."""
    record_id: str
    pm_id: str
    player_id: str
    training_type: str = TrainingType.SPEED.value
    xp_gained: int = 10
    stat_before: float = 0.0
    stat_after: float = 0.0
    cost: float = 10.0
    currency: str = "gold"
    trained_at: float = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class MountConfig:
    """Global tuning parameters."""
    max_mounts: int = 500
    max_skins: int = 2000
    max_player_mounts: int = 100000
    max_equipped_slots: int = 4
    base_summon_cooldown: float = 5.0
    max_mount_level: int = 60
    xp_per_level: int = 1000
    speed_cap: float = 200.0
    stamina_drain_rate: float = 1.0
    stamina_regen_rate: float = 5.0
    loyalty_gain_per_ride: float = 0.5
    loyalty_max: float = 100.0
    tick_rate_hz: float = 1.0

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class MountStats:
    """Aggregate statistics."""
    total_mounts: int = 0
    total_skins: int = 0
    total_player_mounts: int = 0
    total_summoned: int = 0
    total_training_records: int = 0
    total_distance: float = 0.0
    total_playtime: float = 0.0
    tick_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class MountSnapshot:
    """Full state snapshot."""
    mounts: List[Dict[str, Any]] = field(default_factory=list)
    stats: Dict[str, Any] = field(default_factory=dict)
    config: Dict[str, Any] = field(default_factory=dict)
    tick_count: int = 0
    timestamp: float = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class MountEvent:
    """An audit event."""
    event_id: str
    kind: str
    timestamp: float
    mount_id: str = ""
    player_id: str = ""
    pm_id: str = ""
    skin_id: str = ""
    description: str = ""
    details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


# ---------------------------------------------------------------------------
# Mount & Riding System
# ---------------------------------------------------------------------------

class MountRidingSystem:
    """Manages mount definitions, player ownership, summoning, and training."""

    _instance: Optional["MountRidingSystem"] = None
    _lock = threading.RLock()

    def __init__(self) -> None:
        self._mounts: Dict[str, MountDefinition] = {}
        self._skins: Dict[str, MountSkin] = {}
        self._player_mounts: Dict[str, PlayerMount] = {}
        self._training_records: Dict[str, MountTrainingRecord] = {}
        self._active_mounts: Dict[str, str] = {}
        self._events: List[MountEvent] = []
        self._stats = MountStats()
        self._config = MountConfig()
        self._tick_count: int = 0
        self._event_counter: int = 0
        self._initialized: bool = False
        self._init_lock = threading.RLock()
        self._seed()

    @classmethod
    def get_instance(cls) -> "MountRidingSystem":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    # ------------------------------------------------------------------
    # Initialization
    # ------------------------------------------------------------------

    def _seed(self) -> None:
        with self._init_lock:
            if self._initialized:
                return

            mounts_data = [
                ("mount_warhorse", "Iron Warhorse", "A sturdy warhorse bred for battle.",
                 MountType.GROUND.value, MountRarity.UNCOMMON.value,
                 70.0, 110.0, 120.0, 120.0, 6.0,
                 [MountTerrain.LAND.value], True, 150.0, 1, "purchase", 500.0, "gold",
                 "icon_warhorse", "model_warhorse", "#8B4513"),
                ("mount_griffon", "Storm Griffon", "A majestic griffon that soars through the skies.",
                 MountType.FLYING.value, MountRarity.EPIC.value,
                 90.0, 150.0, 100.0, 100.0, 4.0,
                 [MountTerrain.LAND.value, MountTerrain.AIR.value], True, 200.0, 2, "quest", 5000.0, "gold",
                 "icon_griffon", "model_griffon", "#4169E1"),
                ("mount_seahorse", "Tidal Seahorse", "An aquatic mount that glides through water.",
                 MountType.AQUATIC.value, MountRarity.RARE.value,
                 50.0, 80.0, 90.0, 90.0, 5.0,
                 [MountTerrain.WATER.value], False, 0.0, 1, "purchase", 1000.0, "gold",
                 "icon_seahorse", "model_seahorse", "#00CED1"),
                ("mount_drake", "Crimson Drake", "A fearsome drake capable of land and air travel.",
                 MountType.AMPHIBIOUS.value, MountRarity.LEGENDARY.value,
                 100.0, 180.0, 150.0, 150.0, 8.0,
                 [MountTerrain.LAND.value, MountTerrain.AIR.value], True, 300.0, 2, "achievement", 0.0, "gold",
                 "icon_drake", "model_drake", "#DC143C"),
                ("mount_ram", "Mountain Ram", "A sure-footed ram for mountainous terrain.",
                 MountType.GROUND.value, MountRarity.COMMON.value,
                 55.0, 80.0, 110.0, 110.0, 5.0,
                 [MountTerrain.LAND.value, MountTerrain.ICE.value], False, 0.0, 1, "purchase", 100.0, "gold",
                 "icon_ram", "model_ram", "#696969"),
            ]
            for (mid, name, desc, mtype, rarity, bspeed, mspeed, bstam, mstam, sregen,
                 terrains, combat, cpower, passengers, method, cost, currency,
                 icon, model, color) in mounts_data:
                m = MountDefinition(
                    mount_id=mid, name=name, description=desc,
                    mount_type=mtype, rarity=rarity,
                    base_speed=bspeed, max_speed=mspeed,
                    base_stamina=bstam, max_stamina=mstam, stamina_regen=sregen,
                    allowed_terrains=terrains,
                    combat_capable=combat, combat_power=cpower,
                    passenger_capacity=passengers,
                    acquisition_method=method, acquisition_cost=cost,
                    acquisition_currency=currency,
                    icon=icon, model_id=model, color=color,
                )
                self._mounts[mid] = m

            # Skins
            skins_data = [
                ("skin_warhorse_armored", "Armored Warhorse", "Heavy plate armor for the warhorse.",
                 "mount_warhorse", MountRarity.RARE.value, "model_warhorse_armored", "#A0522D", "effect_armor",
                 "shop", 500.0, "icon_skin_armored"),
                ("skin_griffon_golden", "Golden Griffon", "Golden plumage for the storm griffon.",
                 "mount_griffon", MountRarity.EPIC.value, "model_griffon_golden", "#FFD700", "effect_golden",
                 "achievement", 0.0, "icon_skin_golden"),
                ("skin_drake_shadow", "Shadow Drake", "Shadowy flames for the crimson drake.",
                 "mount_drake", MountRarity.LEGENDARY.value, "model_drake_shadow", "#2F0035", "effect_shadow",
                 "raid", 0.0, "icon_skin_shadow"),
            ]
            for sid, name, desc, mount_id, rarity, model, color, effect, method, cost, icon in skins_data:
                skin = MountSkin(
                    skin_id=sid, name=name, description=desc,
                    mount_id=mount_id, rarity=rarity,
                    model_override=model, color_override=color,
                    effect_id=effect, acquisition_method=method,
                    acquisition_cost=cost, icon=icon,
                )
                self._skins[sid] = skin

            # Player mounts
            pm1 = PlayerMount(
                pm_id="pm_starter_warhorse",
                player_id="player_starter",
                mount_id="mount_warhorse",
                status=MountStatus.STORED.value,
                level=5,
                experience=500,
                current_speed=75.0,
                current_stamina=120.0,
                max_stamina=120.0,
                loyalty=70.0,
                trained_stats={"speed": 5.0, "stamina": 10.0},
                summon_count=15,
                last_summoned=_now() - 3600,
                custom_name="Thunder",
            )
            self._player_mounts[pm1.pm_id] = pm1

            pm2 = PlayerMount(
                pm_id="pm_veteran_drake",
                player_id="player_veteran",
                mount_id="mount_drake",
                status=MountStatus.SUMMONED.value,
                level=30,
                experience=15000,
                current_speed=160.0,
                current_stamina=150.0,
                max_stamina=150.0,
                loyalty=95.0,
                trained_stats={"speed": 20.0, "stamina": 30.0, "combat": 15.0},
                applied_skin_id="skin_drake_shadow",
                summon_count=200,
                last_summoned=_now() - 300,
                custom_name="Inferno",
            )
            self._player_mounts[pm2.pm_id] = pm2
            self._active_mounts["player_veteran"] = pm2.pm_id

            pm3 = PlayerMount(
                pm_id="pm_starter_ram",
                player_id="player_starter",
                mount_id="mount_ram",
                status=MountStatus.STORED.value,
                level=1,
                experience=0,
                current_speed=55.0,
                current_stamina=110.0,
                max_stamina=110.0,
                loyalty=30.0,
                summon_count=3,
                last_summoned=_now() - 86400,
                custom_name="Boulder",
            )
            self._player_mounts[pm3.pm_id] = pm3

            # Training records
            tr1 = MountTrainingRecord(
                record_id="train_starter_warhorse_01",
                pm_id="pm_starter_warhorse",
                player_id="player_starter",
                training_type=TrainingType.SPEED.value,
                xp_gained=100,
                stat_before=70.0,
                stat_after=75.0,
                cost=50.0,
                currency="gold",
            )
            self._training_records[tr1.record_id] = tr1

            tr2 = MountTrainingRecord(
                record_id="train_veteran_drake_01",
                pm_id="pm_veteran_drake",
                player_id="player_veteran",
                training_type=TrainingType.COMBAT.value,
                xp_gained=500,
                stat_before=285.0,
                stat_after=300.0,
                cost=200.0,
                currency="gold",
            )
            self._training_records[tr2.record_id] = tr2

            self._update_stats()
            self._initialized = True

    def _update_stats(self) -> None:
        self._stats.total_mounts = len(self._mounts)
        self._stats.total_skins = len(self._skins)
        self._stats.total_player_mounts = len(self._player_mounts)
        self._stats.total_summoned = sum(
            1 for pm in self._player_mounts.values()
            if pm.status == MountStatus.SUMMONED.value
        )
        self._stats.total_training_records = len(self._training_records)
        self._stats.total_distance = sum(pm.total_distance for pm in self._player_mounts.values())
        self._stats.total_playtime = sum(pm.total_playtime for pm in self._player_mounts.values())

    def _log_event(self, kind: str, details: Dict[str, Any],
                   mount_id: str = "", player_id: str = "",
                   pm_id: str = "", skin_id: str = "",
                   description: str = "") -> None:
        event = MountEvent(
            event_id=f"evt_{self._event_counter:08d}",
            kind=kind, timestamp=_now(),
            mount_id=mount_id, player_id=player_id,
            pm_id=pm_id, skin_id=skin_id,
            description=description, details=details,
        )
        self._event_counter += 1
        self._events.append(event)
        _evict_fifo_list(self._events, _MAX_EVENTS)

    # ------------------------------------------------------------------
    # Mount Definition Management
    # ------------------------------------------------------------------

    def register_mount(self, mount_id: str, name: str, description: str = "",
                       mount_type: str = MountType.GROUND.value,
                       rarity: str = MountRarity.COMMON.value,
                       base_speed: float = 60.0, max_speed: float = 100.0,
                       base_stamina: float = 100.0, max_stamina: float = 100.0,
                       stamina_regen: float = 5.0,
                       allowed_terrains: Optional[List[str]] = None,
                       combat_capable: bool = False, combat_power: float = 0.0,
                       passenger_capacity: int = 1, required_level: int = 1,
                       acquisition_method: str = "purchase",
                       acquisition_cost: float = 100.0,
                       acquisition_currency: str = "gold",
                       icon: str = "", model_id: str = "",
                       color: str = "#FFFFFF"
                       ) -> Tuple[bool, str, Optional[MountDefinition]]:
        with _LOCK:
            if mount_id in self._mounts:
                return False, "mount_exists", None
            if len(self._mounts) >= _MAX_MOUNTS:
                return False, "max_mounts", None
            mount = MountDefinition(
                mount_id=mount_id, name=name, description=description,
                mount_type=mount_type, rarity=rarity,
                base_speed=base_speed, max_speed=max_speed,
                base_stamina=base_stamina, max_stamina=max_stamina,
                stamina_regen=stamina_regen,
                allowed_terrains=allowed_terrains or [MountTerrain.LAND.value],
                combat_capable=combat_capable, combat_power=combat_power,
                passenger_capacity=passenger_capacity,
                required_level=required_level,
                acquisition_method=acquisition_method,
                acquisition_cost=acquisition_cost,
                acquisition_currency=acquisition_currency,
                icon=icon, model_id=model_id, color=color,
            )
            self._mounts[mount_id] = mount
            self._log_event(MountEventKind.MOUNT_REGISTERED.value,
                            {"name": name}, mount_id=mount_id)
            self._update_stats()
            return True, "registered", mount

    def remove_mount(self, mount_id: str) -> Tuple[bool, str]:
        with _LOCK:
            if mount_id not in self._mounts:
                return False, "mount_not_found"
            # Check if any player owns this mount
            for pm in self._player_mounts.values():
                if pm.mount_id == mount_id:
                    return False, "mount_in_use"
            del self._mounts[mount_id]
            # Remove skins for this mount
            skin_ids = [sid for sid, s in self._skins.items() if s.mount_id == mount_id]
            for sid in skin_ids:
                del self._skins[sid]
            self._log_event(MountEventKind.MOUNT_REMOVED.value,
                            {"mount_id": mount_id})
            self._update_stats()
            return True, "removed"

    def get_mount(self, mount_id: str) -> Optional[MountDefinition]:
        with _LOCK:
            return self._mounts.get(mount_id)

    def list_mounts(self, mount_type: str = "", rarity: str = "") -> List[MountDefinition]:
        with _LOCK:
            results = list(self._mounts.values())
            if mount_type:
                results = [m for m in results if m.mount_type == mount_type]
            if rarity:
                results = [m for m in results if m.rarity == rarity]
            return results

    # ------------------------------------------------------------------
    # Skin Management
    # ------------------------------------------------------------------

    def register_skin(self, skin_id: str, name: str, description: str = "",
                      mount_id: str = "", rarity: str = MountRarity.UNCOMMON.value,
                      model_override: str = "", color_override: str = "",
                      effect_id: str = "", acquisition_method: str = "shop",
                      acquisition_cost: float = 0.0, icon: str = ""
                      ) -> Tuple[bool, str, Optional[MountSkin]]:
        with _LOCK:
            if skin_id in self._skins:
                return False, "skin_exists", None
            if len(self._skins) >= _MAX_SKINS:
                return False, "max_skins", None
            skin = MountSkin(
                skin_id=skin_id, name=name, description=description,
                mount_id=mount_id, rarity=rarity,
                model_override=model_override, color_override=color_override,
                effect_id=effect_id, acquisition_method=acquisition_method,
                acquisition_cost=acquisition_cost, icon=icon,
            )
            self._skins[skin_id] = skin
            self._log_event(MountEventKind.SKIN_REGISTERED.value,
                            {"name": name}, skin_id=skin_id)
            self._update_stats()
            return True, "registered", skin

    def get_skin(self, skin_id: str) -> Optional[MountSkin]:
        with _LOCK:
            return self._skins.get(skin_id)

    def list_skins(self, mount_id: str = "") -> List[MountSkin]:
        with _LOCK:
            results = list(self._skins.values())
            if mount_id:
                results = [s for s in results if s.mount_id == mount_id]
            return results

    # ------------------------------------------------------------------
    # Player Mount Management
    # ------------------------------------------------------------------

    def acquire_mount(self, player_id: str, mount_id: str,
                      custom_name: str = "") -> Tuple[bool, str, Optional[PlayerMount]]:
        with _LOCK:
            mount = self._mounts.get(mount_id)
            if mount is None:
                return False, "mount_not_found", None
            # Check max player mounts
            player_count = sum(1 for pm in self._player_mounts.values() if pm.player_id == player_id)
            if player_count >= self._config.max_player_mounts:
                return False, "max_player_mounts", None
            pm_id = _new_id("pm")
            pm = PlayerMount(
                pm_id=pm_id, player_id=player_id, mount_id=mount_id,
                status=MountStatus.STORED.value,
                current_speed=mount.base_speed,
                current_stamina=mount.base_stamina,
                max_stamina=mount.max_stamina,
                custom_name=custom_name or mount.name,
            )
            self._player_mounts[pm_id] = pm
            self._log_event(MountEventKind.MOUNT_ACQUIRED.value,
                            {"mount_id": mount_id},
                            mount_id=mount_id, player_id=player_id, pm_id=pm_id)
            self._update_stats()
            return True, "acquired", pm

    def get_player_mount(self, pm_id: str) -> Optional[PlayerMount]:
        with _LOCK:
            return self._player_mounts.get(pm_id)

    def list_player_mounts(self, player_id: str) -> List[PlayerMount]:
        with _LOCK:
            return [pm for pm in self._player_mounts.values() if pm.player_id == player_id]

    def summon_mount(self, pm_id: str) -> Tuple[bool, str, Optional[PlayerMount]]:
        with _LOCK:
            pm = self._player_mounts.get(pm_id)
            if pm is None:
                return False, "pm_not_found", None
            if pm.status == MountStatus.SUMMONED.value:
                return False, "already_summoned", pm
            if pm.status == MountStatus.COOLDOWN.value:
                if _now() < pm.cooldown_until:
                    return False, "on_cooldown", pm
            if pm.status == MountStatus.LOCKED.value:
                return False, "locked", pm
            # Dismiss any currently active mount for this player
            current_active = self._active_mounts.get(pm.player_id)
            if current_active and current_active != pm_id:
                old_pm = self._player_mounts.get(current_active)
                if old_pm:
                    old_pm.status = MountStatus.STORED.value
                    self._log_event(MountEventKind.MOUNT_DISMISSED.value,
                                    {"pm_id": current_active},
                                    player_id=pm.player_id, pm_id=current_active)
            pm.status = MountStatus.SUMMONED.value
            pm.last_summoned = _now()
            pm.summon_count += 1
            pm.loyalty = min(pm.loyalty + self._config.loyalty_gain_per_ride,
                             self._config.loyalty_max)
            self._active_mounts[pm.player_id] = pm_id
            self._log_event(MountEventKind.MOUNT_SUMMONED.value,
                            {"mount_id": pm.mount_id},
                            mount_id=pm.mount_id, player_id=pm.player_id, pm_id=pm_id)
            self._update_stats()
            return True, "summoned", pm

    def dismiss_mount(self, pm_id: str) -> Tuple[bool, str, Optional[PlayerMount]]:
        with _LOCK:
            pm = self._player_mounts.get(pm_id)
            if pm is None:
                return False, "pm_not_found", None
            if pm.status != MountStatus.SUMMONED.value:
                return False, "not_summoned", pm
            pm.status = MountStatus.STORED.value
            pm.cooldown_until = _now() + self._config.base_summon_cooldown
            if pm.player_id in self._active_mounts:
                del self._active_mounts[pm.player_id]
            self._log_event(MountEventKind.MOUNT_DISMISSED.value,
                            {"pm_id": pm_id},
                            player_id=pm.player_id, pm_id=pm_id)
            self._update_stats()
            return True, "dismissed", pm

    def get_active_mount(self, player_id: str) -> Optional[PlayerMount]:
        with _LOCK:
            pm_id = self._active_mounts.get(player_id)
            if pm_id:
                return self._player_mounts.get(pm_id)
            return None

    # ------------------------------------------------------------------
    # Training
    # ------------------------------------------------------------------

    def train_mount(self, pm_id: str, training_type: str = TrainingType.SPEED.value,
                    cost: float = 10.0, currency: str = "gold"
                    ) -> Tuple[bool, str, Optional[MountTrainingRecord]]:
        with _LOCK:
            pm = self._player_mounts.get(pm_id)
            if pm is None:
                return False, "pm_not_found", None
            mount = self._mounts.get(pm.mount_id)
            if mount is None:
                return False, "mount_not_found", None
            # Calculate stat before
            stat_key = training_type
            stat_before = pm.trained_stats.get(stat_key, 0.0)
            stat_gain = 1.0 + (pm.level * 0.1)
            stat_after = stat_before + stat_gain
            # Apply training
            pm.trained_stats[stat_key] = stat_after
            if training_type == TrainingType.SPEED.value:
                pm.current_speed = min(mount.max_speed, pm.current_speed + stat_gain)
            elif training_type == TrainingType.STAMINA.value:
                pm.max_stamina = min(mount.max_stamina, pm.max_stamina + stat_gain * 10)
                pm.current_stamina = pm.max_stamina
            elif training_type == TrainingType.LOYALTY.value:
                pm.loyalty = min(self._config.loyalty_max, pm.loyalty + stat_gain * 2)
            # Award XP
            xp_gained = int(cost * 10)
            pm.experience += xp_gained
            # Check level up
            while pm.experience >= pm.level * self._config.xp_per_level:
                pm.experience -= pm.level * self._config.xp_per_level
                pm.level += 1
                if pm.level >= self._config.max_mount_level:
                    pm.level = self._config.max_mount_level
                    pm.experience = 0
                    break
            record = MountTrainingRecord(
                record_id=_new_id("train"),
                pm_id=pm_id, player_id=pm.player_id,
                training_type=training_type,
                xp_gained=xp_gained,
                stat_before=stat_before, stat_after=stat_after,
                cost=cost, currency=currency,
            )
            self._training_records[record.record_id] = record
            self._log_event(MountEventKind.MOUNT_TRAINED.value,
                            {"training_type": training_type, "xp": xp_gained},
                            player_id=pm.player_id, pm_id=pm_id)
            self._update_stats()
            return True, "trained", record

    def get_training_record(self, record_id: str) -> Optional[MountTrainingRecord]:
        with _LOCK:
            return self._training_records.get(record_id)

    def list_training_records(self, pm_id: str = "",
                              player_id: str = "") -> List[MountTrainingRecord]:
        with _LOCK:
            results = list(self._training_records.values())
            if pm_id:
                results = [r for r in results if r.pm_id == pm_id]
            if player_id:
                results = [r for r in results if r.player_id == player_id]
            return results

    # ------------------------------------------------------------------
    # Equipment & Skins
    # ------------------------------------------------------------------

    def equip_mount_item(self, pm_id: str, slot: str, item_id: str,
                         item_name: str = "",
                         stat_bonuses: Optional[Dict[str, float]] = None
                         ) -> Tuple[bool, str, Optional[PlayerMount]]:
        with _LOCK:
            pm = self._player_mounts.get(pm_id)
            if pm is None:
                return False, "pm_not_found", None
            if len(pm.equipped_slots) >= self._config.max_equipped_slots and slot not in pm.equipped_slots:
                return False, "max_slots", pm
            eq = MountEquipment(
                slot=slot, item_id=item_id, item_name=item_name,
                stat_bonuses=stat_bonuses or {},
            )
            pm.equipped_slots[slot] = eq
            self._log_event(MountEventKind.EQUIPMENT_EQUIPPED.value,
                            {"slot": slot, "item_id": item_id},
                            player_id=pm.player_id, pm_id=pm_id)
            return True, "equipped", pm

    def unequip_mount_item(self, pm_id: str, slot: str
                           ) -> Tuple[bool, str, Optional[PlayerMount]]:
        with _LOCK:
            pm = self._player_mounts.get(pm_id)
            if pm is None:
                return False, "pm_not_found", None
            if slot not in pm.equipped_slots:
                return False, "slot_empty", pm
            del pm.equipped_slots[slot]
            self._log_event(MountEventKind.EQUIPMENT_UNEQUIPPED.value,
                            {"slot": slot},
                            player_id=pm.player_id, pm_id=pm_id)
            return True, "unequipped", pm

    def apply_skin(self, pm_id: str, skin_id: str
                   ) -> Tuple[bool, str, Optional[PlayerMount]]:
        with _LOCK:
            pm = self._player_mounts.get(pm_id)
            if pm is None:
                return False, "pm_not_found", None
            skin = self._skins.get(skin_id)
            if skin is None:
                return False, "skin_not_found", None
            if skin.mount_id and skin.mount_id != pm.mount_id:
                return False, "skin_mismatch", pm
            pm.applied_skin_id = skin_id
            self._log_event(MountEventKind.SKIN_APPLIED.value,
                            {"skin_id": skin_id},
                            player_id=pm.player_id, pm_id=pm_id, skin_id=skin_id)
            return True, "applied", pm

    def get_mount_skins(self, mount_id: str) -> List[MountSkin]:
        with _LOCK:
            return [s for s in self._skins.values() if s.mount_id == mount_id]

    # ------------------------------------------------------------------
    # Calculations
    # ------------------------------------------------------------------

    def calculate_speed(self, pm_id: str, terrain: str = MountTerrain.LAND.value
                        ) -> Tuple[bool, str, float]:
        with _LOCK:
            pm = self._player_mounts.get(pm_id)
            if pm is None:
                return False, "pm_not_found", 0.0
            mount = self._mounts.get(pm.mount_id)
            if mount is None:
                return False, "mount_not_found", 0.0
            if terrain not in mount.allowed_terrains:
                return False, "terrain_blocked", 0.0
            speed = pm.effective_speed
            # Stamina factor
            if pm.current_stamina < pm.max_stamina * 0.2:
                speed *= 0.7
            return True, "calculated", speed

    def get_speed_bonus(self, pm_id: str) -> float:
        with _LOCK:
            pm = self._player_mounts.get(pm_id)
            if pm is None:
                return 0.0
            mount = self._mounts.get(pm.mount_id)
            if mount is None:
                return 0.0
            return pm.effective_speed - mount.base_speed

    # ------------------------------------------------------------------
    # System Operations
    # ------------------------------------------------------------------

    def tick(self) -> Dict[str, Any]:
        with _LOCK:
            self._tick_count += 1
            # Regenerate stamina for summoned mounts
            for pm in self._player_mounts.values():
                if pm.status == MountStatus.SUMMONED.value:
                    pm.current_stamina = min(
                        pm.max_stamina,
                        pm.current_stamina + self._config.stamina_regen_rate
                    )
                    pm.total_playtime += 1.0
            self._log_event(MountEventKind.TICK.value,
                            {"tick": self._tick_count})
            return {"tick_count": self._tick_count}

    def set_config(self, config: Dict[str, Any]) -> Tuple[bool, str, MountConfig]:
        with _LOCK:
            if "max_mounts" in config:
                self._config.max_mounts = _safe_int(config["max_mounts"], self._config.max_mounts)
            if "max_player_mounts" in config:
                self._config.max_player_mounts = _safe_int(config["max_player_mounts"], self._config.max_player_mounts)
            if "base_summon_cooldown" in config:
                self._config.base_summon_cooldown = _safe_float(config["base_summon_cooldown"], self._config.base_summon_cooldown)
            if "speed_cap" in config:
                self._config.speed_cap = _safe_float(config["speed_cap"], self._config.speed_cap)
            if "xp_per_level" in config:
                self._config.xp_per_level = _safe_int(config["xp_per_level"], self._config.xp_per_level)
            self._log_event(MountEventKind.CONFIG_UPDATED.value, dict(config))
            return True, "updated", self._config

    def get_config(self) -> MountConfig:
        with _LOCK:
            return self._config

    def list_events(self, limit: int = 100, kind: str = "") -> List[MountEvent]:
        with _LOCK:
            results = list(self._events)
            if kind:
                results = [e for e in results if e.kind == kind]
            if limit > 0:
                results = results[-limit:]
            return results

    def get_stats(self) -> MountStats:
        with _LOCK:
            self._update_stats()
            self._stats.tick_count = self._tick_count
            return self._stats

    def get_status(self) -> Dict[str, Any]:
        with _LOCK:
            self._update_stats()
            return {
                "initialized": self._initialized,
                "total_mounts": len(self._mounts),
                "total_skins": len(self._skins),
                "total_player_mounts": len(self._player_mounts),
                "total_summoned": self._stats.total_summoned,
                "total_training_records": len(self._training_records),
                "tick_count": self._tick_count,
            }

    def get_snapshot(self) -> MountSnapshot:
        with _LOCK:
            self._update_stats()
            return MountSnapshot(
                mounts=[m.to_dict() for m in self._mounts.values()],
                stats=self._stats.to_dict(),
                config=self._config.to_dict(),
                tick_count=self._tick_count,
            )

    def reset(self) -> Dict[str, Any]:
        with _LOCK:
            self._mounts.clear()
            self._skins.clear()
            self._player_mounts.clear()
            self._training_records.clear()
            self._active_mounts.clear()
            self._events.clear()
            self._tick_count = 0
            self._event_counter = 0
            self._initialized = False
            self._seed()
            self._log_event(MountEventKind.RESET.value, {})
            return self.get_status()


# ---------------------------------------------------------------------------
# Module-level Factory
# ---------------------------------------------------------------------------

def get_mount_riding_system() -> MountRidingSystem:
    return MountRidingSystem.get_instance()
