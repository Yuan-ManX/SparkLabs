"""
SparkLabs Engine - Tactical Grid Combat System

A grid-based tactical combat engine for the SparkLabs AI-native game
engine. Provides turn-based tactical combat on square, hex, offset, and
isometric grids in the style of classic strategy RPGs. Manages grid
terrain, unit deployment, movement with pathfinding-aware ranges,
attack resolution with terrain and elevation modifiers, fog of war,
faction turn order, and battle lifecycle from setup through victory or
defeat.

The system supports multiple concurrent battles, each bound to a grid
and a set of factions. Units belong to factions, occupy grid cells,
and act during their faction's turn. Combat resolution accounts for
terrain type, elevation advantage, cover, flanking, counter attacks,
and unit class statistics. A configurable ruleset controls whether
friendly fire, fog of war, terrain bonuses, elevation bonuses, and
flanking bonuses are active.

Architecture:
  TacticalGridSystem (singleton)
    |-- GridType, TerrainType, UnitClass, MoveType, AttackType,
       FacingDirection, UnitStatus, CombatPhase, TacticalGridEventKind
    |-- GridCell, TacticalUnit, TacticalGrid, BattleState, Faction,
       TerrainModifier, TacticalGridConfig, TacticalGridStats,
       TacticalGridSnapshot, TacticalGridEvent
    |-- get_tactical_grid_system

Core Capabilities:
  - register_grid / get_grid / list_grids / remove_grid
  - set_terrain / get_cell / get_cells_in_range
  - register_unit / get_unit / list_units / remove_unit
  - deploy_unit / move_unit / attack_unit
  - calculate_damage / calculate_move_range / calculate_attack_range
  - register_faction / get_faction / list_factions
  - create_battle / get_battle / list_battles
  - end_turn / set_fog_of_war / reveal_area
  - tick / set_config / get_config
  - list_events / get_stats / get_status / get_snapshot / reset

The class implements the singleton pattern with double-checked locking
using ``threading.RLock``; consumers should obtain the instance through
:meth:`TacticalGridSystem.get_instance` or the module-level
:func:`get_tactical_grid_system` factory.
"""

from __future__ import annotations

import math
import threading
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Capacity Constants
# ---------------------------------------------------------------------------

_MAX_GRIDS: int = 500
_MAX_BATTLES: int = 200
_MAX_UNITS: int = 5000
_MAX_FACTIONS: int = 100
_MAX_EVENTS: int = 10000
_MAX_CELLS_PER_GRID: int = 10000


# ---------------------------------------------------------------------------
# Helper Functions
# ---------------------------------------------------------------------------

_lock = threading.RLock()
_instance = None


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
    # Check __dataclass_fields__ BEFORE to_dict to avoid recursion.
    if hasattr(obj, "__dataclass_fields__"):
        result: Dict[str, Any] = {}
        for k in obj.__dataclass_fields__:
            result[k] = _dataclass_to_dict(getattr(obj, k))
        return result
    if isinstance(obj, Enum):
        return obj.value
    if isinstance(obj, list):
        return [_dataclass_to_dict(i) for i in obj]
    if isinstance(obj, dict):
        return {kk: _dataclass_to_dict(vv) for kk, vv in obj.items()}
    if isinstance(obj, tuple):
        return [_dataclass_to_dict(i) for i in obj]
    if hasattr(obj, "to_dict") and callable(obj.to_dict):
        return obj.to_dict()
    return obj


def _cell_key(x: int, y: int) -> str:
    return f"{x},{y}"


def _hex_distance(x1: int, y1: int, x2: int, y2: int) -> int:
    # Axial coordinate distance for hex grids.
    dx = x2 - x1
    dy = y2 - y1
    return (abs(dx) + abs(dy) + abs(dx + dy)) // 2


def _chebyshev_distance(x1: int, y1: int, x2: int, y2: int) -> int:
    return max(abs(x2 - x1), abs(y2 - y1))


def _manhattan_distance(x1: int, y1: int, x2: int, y2: int) -> int:
    return abs(x2 - x1) + abs(y2 - y1)


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class GridType(str, Enum):
    """Supported grid topologies for tactical combat."""
    SQUARE = "square"
    HEX = "hex"
    OFFSET_SQUARE = "offset_square"
    ISOMETRIC = "isometric"


class TerrainType(str, Enum):
    """Terrain categories that affect movement and combat."""
    PLAIN = "plain"
    FOREST = "forest"
    MOUNTAIN = "mountain"
    WATER = "water"
    DESERT = "desert"
    SNOW = "snow"
    SWAMP = "swamp"
    LAVA = "lava"
    VOID = "void"
    WALL = "wall"
    ROAD = "road"
    BRIDGE = "bridge"


class UnitClass(str, Enum):
    """Unit archetypes with distinct combat profiles."""
    WARRIOR = "warrior"
    KNIGHT = "knight"
    ARCHER = "archer"
    MAGE = "mage"
    HEALER = "healer"
    ROGUE = "rogue"
    CAVALRY = "cavalry"
    FLYER = "flyer"
    ARMOR = "armor"
    SUPPORT = "support"


class MoveType(str, Enum):
    """Movement modes determining which terrain is passable."""
    WALK = "walk"
    FLY = "fly"
    SWIM = "swim"
    TELEPORT = "teleport"
    MOUNT = "mount"
    NONE = "none"


class AttackType(str, Enum):
    """Attack categories determining range and damage flavor."""
    MELEE = "melee"
    RANGED = "ranged"
    MAGIC = "magic"
    AREA = "area"
    PIERCE = "pierce"
    THROW = "throw"


class FacingDirection(str, Enum):
    """Eight-way facing for flanking and directional mechanics."""
    NORTH = "north"
    SOUTH = "south"
    EAST = "east"
    WEST = "west"
    NORTHEAST = "northeast"
    NORTHWEST = "northwest"
    SOUTHEAST = "southeast"
    SOUTHWEST = "southwest"


class UnitStatus(str, Enum):
    """Runtime status of a unit on the grid."""
    ACTIVE = "active"
    EXHAUSTED = "exhausted"
    STUNNED = "stunned"
    POISONED = "poisoned"
    BURNING = "burning"
    FROZEN = "frozen"
    BLESSED = "blessed"
    HIDDEN = "hidden"
    DEAD = "dead"


class CombatPhase(str, Enum):
    """Lifecycle phases of a tactical battle."""
    SETUP = "setup"
    DEPLOY = "deploy"
    PLAYER_TURN = "player_turn"
    ENEMY_TURN = "enemy_turn"
    RESOLUTION = "resolution"
    VICTORY = "victory"
    DEFEAT = "defeat"


class TacticalGridEventKind(str, Enum):
    """Audit event types emitted by the tactical grid system."""
    UNIT_DEPLOYED = "unit_deployed"
    UNIT_MOVED = "unit_moved"
    UNIT_ATTACKED = "unit_attacked"
    UNIT_DAMAGED = "unit_damaged"
    UNIT_HEALED = "unit_healed"
    TERRAIN_CHANGED = "terrain_changed"
    TURN_STARTED = "turn_started"
    TURN_ENDED = "turn_ended"
    BATTLE_STARTED = "battle_started"
    BATTLE_ENDED = "battle_ended"


# ---------------------------------------------------------------------------
# Data Classes
# ---------------------------------------------------------------------------

@dataclass
class GridCell:
    """A single tile on a tactical grid."""
    cell_id: str
    x: int
    y: int
    terrain_type: str
    z: int = 0
    elevation: int = 0
    movement_cost: int = 1
    is_occupied: bool = False
    occupant_id: str = ""
    is_passable: bool = True
    is_visible: bool = True
    cover_value: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class TacticalUnit:
    """A combat unit deployed on a tactical grid."""
    unit_id: str
    name: str
    unit_class: str
    move_type: str
    attack_type: str
    max_hp: int
    current_hp: int
    attack_power: int
    defense: int
    move_range: int
    attack_range: int
    speed: int = 5
    facing: str = FacingDirection.SOUTH.value
    status: str = UnitStatus.ACTIVE.value
    position_x: int = -1
    position_y: int = -1
    abilities: List[str] = field(default_factory=list)
    equipped_items: List[str] = field(default_factory=list)
    level: int = 1
    experience: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class TacticalGrid:
    """A tactical battle grid composed of cells."""
    grid_id: str
    name: str
    grid_type: str
    width: int
    height: int
    cells: Dict[str, GridCell] = field(default_factory=dict)
    origin_x: int = 0
    origin_y: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class BattleState:
    """State of an active or completed tactical battle."""
    battle_id: str
    grid_id: str
    phase: str = CombatPhase.SETUP.value
    turn_number: int = 1
    current_faction: str = ""
    factions: List[str] = field(default_factory=list)
    units: Dict[str, str] = field(default_factory=dict)
    active_unit: str = ""
    winner: str = ""
    started_at: float = field(default_factory=_now)
    ended_at: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class Faction:
    """A group of units under player or AI control."""
    faction_id: str
    name: str
    color: str = "#FFFFFF"
    unit_ids: List[str] = field(default_factory=list)
    is_player_controlled: bool = True
    ai_strategy: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class TerrainModifier:
    """A stat modifier applied when a unit stands on a terrain type."""
    modifier_id: str
    terrain_type: str
    stat_affected: str
    modifier_value: float = 0.0
    is_percentage: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class TacticalGridConfig:
    """Global tuning parameters for the tactical grid system."""
    default_grid_type: str = GridType.SQUARE.value
    max_units_per_faction: int = 20
    turn_time_limit: int = 60
    fog_of_war_enabled: bool = True
    friendly_fire: bool = False
    counter_attack: bool = True
    terrain_bonuses: bool = True
    elevation_bonus: bool = True
    flanking_bonus: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class TacticalGridStats:
    """Aggregate statistics for the tactical grid system."""
    total_grids: int = 0
    total_battles: int = 0
    active_battles: int = 0
    units_deployed: int = 0
    attacks_made: int = 0
    units_lost: int = 0
    avg_battle_length: float = 0.0
    total_events: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class TacticalGridSnapshot:
    """Full state snapshot of the tactical grid system."""
    timestamp: float = field(default_factory=_now)
    grids_count: int = 0
    battles_count: int = 0
    active_battles: int = 0
    units_count: int = 0
    config: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class TacticalGridEvent:
    """An audit event emitted by the tactical grid system."""
    event_id: str
    kind: str
    timestamp: float
    battle_id: str = ""
    unit_id: str = ""
    cell_id: str = ""
    data: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


# ---------------------------------------------------------------------------
# Tactical Grid System
# ---------------------------------------------------------------------------

class TacticalGridSystem:
    """Manages tactical grid combat: grids, units, factions, and battles.

    Provides turn-based tactical combat on square, hex, offset, and
    isometric grids. Each battle is bound to a grid and a set of
    factions. Units deploy onto cells, move within their movement range,
    and attack targets within their attack range. Damage is resolved
    using attacker power, defender defense, terrain modifiers,
    elevation advantage, cover, and flanking. Fog of war controls cell
    visibility per faction.
    """

    _init_lock = threading.RLock()

    def __init__(self) -> None:
        self._grids: Dict[str, TacticalGrid] = {}
        self._battles: Dict[str, BattleState] = {}
        self._units: Dict[str, TacticalUnit] = {}
        self._factions: Dict[str, Faction] = {}
        self._terrain_modifiers: Dict[str, TerrainModifier] = {}
        self._events: List[TacticalGridEvent] = []
        self._config = TacticalGridConfig()
        self._stats = TacticalGridStats()
        self._tick_count: int = 0
        self._event_counter: int = 0
        self._initialized: bool = False
        self._seed()

    @classmethod
    def get_instance(cls) -> "TacticalGridSystem":
        global _instance
        if _instance is None:
            with _lock:
                if _instance is None:
                    _instance = cls()
        return _instance

    # ------------------------------------------------------------------
    # Initialization
    # ------------------------------------------------------------------

    def _seed(self) -> None:
        """Seed sample grids, units, factions, battles, and modifiers."""
        with self._init_lock:
            if self._initialized:
                return

            # Terrain modifiers for various terrain types.
            modifiers = [
                ("mod_forest_def", TerrainType.FOREST.value, "defense", 2.0, False),
                ("mod_forest_cover", TerrainType.FOREST.value, "cover", 2, False),
                ("mod_mountain_def", TerrainType.MOUNTAIN.value, "defense", 3.0, False),
                ("mod_mountain_elev", TerrainType.MOUNTAIN.value, "elevation", 2, False),
                ("mod_water_move", TerrainType.WATER.value, "movement_cost", 3, False),
                ("mod_swamp_move", TerrainType.SWAMP.value, "movement_cost", 2, False),
                ("mod_road_move", TerrainType.ROAD.value, "movement_cost", 0, False),
                ("mod_wall_def", TerrainType.WALL.value, "defense", 5.0, False),
                ("mod_bridge_move", TerrainType.BRIDGE.value, "movement_cost", 1, False),
                ("mod_lava_dmg", TerrainType.LAVA.value, "damage_per_turn", 5, False),
                ("mod_desert_spd", TerrainType.DESERT.value, "speed", -0.2, True),
                ("mod_snow_spd", TerrainType.SNOW.value, "speed", -0.3, True),
            ]
            for mod_id, terrain, stat, value, is_pct in modifiers:
                self._terrain_modifiers[mod_id] = TerrainModifier(
                    modifier_id=mod_id, terrain_type=terrain,
                    stat_affected=stat, modifier_value=value,
                    is_percentage=is_pct)

            # Grids: plains battlefield, forest ambush, castle siege.
            self._build_seed_grid(
                "grid_plains_battlefield", "Plains Battlefield",
                GridType.SQUARE.value, 10, 10,
            )
            self._build_seed_grid(
                "grid_forest_ambush", "Forest Ambush",
                GridType.HEX.value, 8, 8,
            )
            self._build_seed_grid(
                "grid_castle_siege", "Castle Siege",
                GridType.SQUARE.value, 12, 12,
            )

            # Apply varied terrain to the plains grid.
            self._apply_seed_terrain("grid_plains_battlefield")
            self._apply_seed_terrain("grid_forest_ambush")
            self._apply_seed_terrain("grid_castle_siege")

            # Factions: player alliance, enemy horde, neutral mercenaries.
            self._factions["faction_player_alliance"] = Faction(
                faction_id="faction_player_alliance", name="Player Alliance",
                color="#3B82F6", is_player_controlled=True)
            self._factions["faction_enemy_horde"] = Faction(
                faction_id="faction_enemy_horde", name="Enemy Horde",
                color="#EF4444", is_player_controlled=False,
                ai_strategy="aggressive")
            self._factions["faction_neutral_mercenaries"] = Faction(
                faction_id="faction_neutral_mercenaries", name="Neutral Mercenaries",
                color="#22C55E", is_player_controlled=False,
                ai_strategy="defensive")

            # Units: player roster and enemy bandits.
            # Tuple: (id, name, class, move, attack, hp, atk, def, mrange, arange, spd, abilities)
            seed_units = [
                ("unit_knight_01", "Sir Galahad", "knight", "walk", "melee", 30, 12, 8, 3, 1, 4, ["shield_bash", "taunt"]),
                ("unit_archer_01", "Lyra Swift", "archer", "walk", "ranged", 20, 10, 4, 4, 3, 6, ["piercing_shot", "volley"]),
                ("unit_mage_01", "Aldric Frost", "mage", "walk", "magic", 18, 15, 3, 3, 4, 5, ["fireball", "frost_nova"]),
                ("unit_healer_01", "Elara Dawn", "healer", "walk", "magic", 22, 5, 5, 3, 1, 5, ["heal", "sanctuary"]),
                ("unit_rogue_01", "Vex Shadow", "rogue", "walk", "melee", 24, 12, 4, 5, 1, 7, ["backstab", "stealth"]),
                ("unit_warrior_01", "Bjorn Ironaxe", "warrior", "walk", "melee", 28, 14, 6, 3, 1, 4, ["whirlwind", "warcry"]),
                ("unit_cavalry_01", "Dane Stormrider", "cavalry", "mount", "melee", 32, 11, 7, 5, 1, 6, ["charge", "trample"]),
                ("unit_flyer_01", "Sora Skywing", "flyer", "fly", "ranged", 20, 13, 3, 6, 2, 8, ["dive_bomb", "aerial_dodge"]),
                ("unit_armor_01", "Grim Bulwark", "armor", "walk", "melee", 40, 10, 12, 2, 1, 2, ["fortify", "shield_wall"]),
                ("unit_enemy_bandit_01", "Brug the Cruel", "warrior", "walk", "melee", 26, 12, 5, 3, 1, 4, ["reckless_swing"]),
                ("unit_enemy_bandit_02", "Snek Knifehand", "rogue", "walk", "pierce", 22, 11, 4, 5, 1, 6, ["poison_blade"]),
                ("unit_enemy_bandit_03", "Mara Axe Raider", "warrior", "walk", "throw", 28, 13, 5, 3, 2, 3, ["axe_throw"]),
            ]
            for (uid, uname, uclass, mtype, atype, mhp, atk, df,
                 mr, ar, spd, abilities) in seed_units:
                faction_id = ("faction_enemy_horde" if uid.startswith("unit_enemy_")
                              else "faction_player_alliance")
                self._units[uid] = TacticalUnit(
                    unit_id=uid, name=uname, unit_class=uclass,
                    move_type=mtype, attack_type=atype, max_hp=mhp,
                    current_hp=mhp, attack_power=atk, defense=df,
                    move_range=mr, attack_range=ar, speed=spd,
                    abilities=abilities)
                self._factions[faction_id].unit_ids.append(uid)

            # Battles: plains skirmish and forest ambush.
            self._battles["battle_plains_skirmish"] = BattleState(
                battle_id="battle_plains_skirmish",
                grid_id="grid_plains_battlefield",
                phase=CombatPhase.PLAYER_TURN.value, turn_number=3,
                current_faction="faction_player_alliance",
                factions=["faction_player_alliance", "faction_enemy_horde"],
                started_at=_now() - 300,
                metadata={"difficulty": "normal", "map": "plains"})
            self._battles["battle_forest_ambush"] = BattleState(
                battle_id="battle_forest_ambush",
                grid_id="grid_forest_ambush",
                phase=CombatPhase.ENEMY_TURN.value, turn_number=2,
                current_faction="faction_enemy_horde",
                factions=["faction_player_alliance", "faction_enemy_horde",
                          "faction_neutral_mercenaries"],
                started_at=_now() - 120,
                metadata={"difficulty": "hard", "map": "forest"})

            # Deploy units onto the battles for a live state.
            deployments = [
                ("battle_plains_skirmish", "unit_knight_01", 1, 1, "faction_player_alliance"),
                ("battle_plains_skirmish", "unit_archer_01", 2, 1, "faction_player_alliance"),
                ("battle_plains_skirmish", "unit_mage_01", 1, 2, "faction_player_alliance"),
                ("battle_plains_skirmish", "unit_enemy_bandit_01", 8, 8, "faction_enemy_horde"),
                ("battle_plains_skirmish", "unit_enemy_bandit_02", 7, 8, "faction_enemy_horde"),
                ("battle_forest_ambush", "unit_rogue_01", 0, 0, "faction_player_alliance"),
                ("battle_forest_ambush", "unit_healer_01", 1, 0, "faction_player_alliance"),
                ("battle_forest_ambush", "unit_enemy_bandit_03", 6, 6, "faction_enemy_horde"),
            ]
            for bid, uid, dx, dy, fid in deployments:
                self._deploy_seed_unit(bid, uid, dx, dy, fid)

            self._update_stats()
            self._initialized = True

    def _build_seed_grid(self, grid_id: str, name: str, grid_type: str,
                         width: int, height: int) -> None:
        """Create a grid and populate it with default plain cells."""
        grid = TacticalGrid(grid_id=grid_id, name=name, grid_type=grid_type,
                            width=width, height=height)
        for y in range(height):
            for x in range(width):
                grid.cells[_cell_key(x, y)] = GridCell(
                    cell_id=f"{grid_id}_{x}_{y}", x=x, y=y,
                    terrain_type=TerrainType.PLAIN.value)
        self._grids[grid_id] = grid

    def _apply_seed_terrain(self, grid_id: str) -> None:
        """Apply varied terrain patterns to a seeded grid."""
        grid = self._grids.get(grid_id)
        if not grid:
            return
        terrain_patches = {
            TerrainType.FOREST.value: 0.12,
            TerrainType.MOUNTAIN.value: 0.06,
            TerrainType.WATER.value: 0.05,
            TerrainType.ROAD.value: 0.08,
            TerrainType.WALL.value: 0.03,
        }
        cell_count = len(grid.cells)
        for terrain, ratio in terrain_patches.items():
            target = max(1, int(cell_count * ratio))
            placed = 0
            for cell in grid.cells.values():
                if placed >= target:
                    break
                # Deterministic placement based on cell coordinates.
                h = (cell.x * 31 + cell.y * 17 + len(terrain)) % 100
                if h < int(ratio * 100) and cell.terrain_type == TerrainType.PLAIN.value:
                    cell.terrain_type = terrain
                    if terrain == TerrainType.MOUNTAIN.value:
                        cell.elevation, cell.movement_cost = 2, 3
                    elif terrain == TerrainType.FOREST.value:
                        cell.elevation, cell.movement_cost, cell.cover_value = 1, 2, 2
                    elif terrain == TerrainType.WATER.value:
                        cell.movement_cost, cell.is_passable = 3, False
                    elif terrain == TerrainType.WALL.value:
                        cell.movement_cost, cell.is_passable, cell.cover_value = 99, False, 3
                    elif terrain == TerrainType.ROAD.value:
                        cell.movement_cost = 0
                    placed += 1

    def _deploy_seed_unit(self, battle_id: str, unit_id: str, x: int, y: int,
                          faction_id: str) -> None:
        """Deploy a unit during seeding without emitting events."""
        battle = self._battles.get(battle_id)
        grid = self._grids.get(battle.grid_id) if battle else None
        unit = self._units.get(unit_id)
        if not battle or not grid or not unit:
            return
        cell = grid.cells.get(_cell_key(x, y))
        if not cell:
            return
        cell.is_occupied = True
        cell.occupant_id = unit_id
        unit.position_x = x
        unit.position_y = y
        battle.units[unit_id] = faction_id

    # ------------------------------------------------------------------
    # Internal Helpers
    # ------------------------------------------------------------------

    def _emit_event(self, kind: str, battle_id: str = "",
                    unit_id: str = "", cell_id: str = "",
                    data: Optional[Dict[str, Any]] = None) -> None:
        """Record an audit event and evict old entries."""
        event = TacticalGridEvent(
            event_id=f"evt_{self._event_counter}", kind=kind,
            timestamp=_now(), battle_id=battle_id, unit_id=unit_id,
            cell_id=cell_id, data=data or {})
        self._event_counter += 1
        self._events.append(event)
        _evict_fifo_list(self._events, _MAX_EVENTS)

    def _update_stats(self) -> None:
        """Refresh aggregate statistics from current state."""
        self._stats.total_grids = len(self._grids)
        self._stats.total_battles = len(self._battles)
        self._stats.active_battles = sum(
            1 for b in self._battles.values()
            if b.phase not in (CombatPhase.VICTORY.value,
                               CombatPhase.DEFEAT.value))
        self._stats.units_deployed = sum(
            1 for u in self._units.values() if u.position_x >= 0)
        self._stats.total_events = len(self._events)
        completed = [b for b in self._battles.values() if b.ended_at > 0]
        if completed:
            total_time = sum(b.ended_at - b.started_at for b in completed)
            self._stats.avg_battle_length = total_time / len(completed)

    def _resolve_grid_type(self, grid_type: str) -> str:
        """Resolve a grid type string to a valid GridType value."""
        for gt in GridType:
            if gt.value == grid_type:
                return gt.value
        return self._config.default_grid_type

    def _resolve_terrain(self, terrain_type: str) -> str:
        """Resolve a terrain string to a valid TerrainType value."""
        for tt in TerrainType:
            if tt.value == terrain_type:
                return tt.value
        return TerrainType.PLAIN.value

    def _is_terrain_passable(self, terrain_type: str, move_type: str) -> bool:
        """Determine if a unit with a move type can enter a terrain."""
        if move_type == MoveType.FLY.value:
            return terrain_type not in (TerrainType.VOID.value, TerrainType.WALL.value)
        if move_type == MoveType.SWIM.value:
            return terrain_type in (TerrainType.WATER.value,
                                    TerrainType.SWAMP.value,
                                    TerrainType.BRIDGE.value)
        if move_type == MoveType.TELEPORT.value:
            return True
        return terrain_type not in (TerrainType.WATER.value, TerrainType.LAVA.value,
                                    TerrainType.VOID.value, TerrainType.WALL.value)

    def _grid_distance(self, grid: TacticalGrid, x1: int, y1: int,
                       x2: int, y2: int) -> int:
        """Compute the grid-appropriate distance between two cells."""
        if grid.grid_type == GridType.HEX.value:
            return _hex_distance(x1, y1, x2, y2)
        if grid.grid_type in (GridType.OFFSET_SQUARE.value, GridType.ISOMETRIC.value):
            return _chebyshev_distance(x1, y1, x2, y2)
        return _manhattan_distance(x1, y1, x2, y2)

    def _get_terrain_modifier(self, terrain_type: str, stat: str) -> float:
        """Sum all modifiers for a terrain type and stat."""
        return sum(m.modifier_value for m in self._terrain_modifiers.values()
                   if m.terrain_type == terrain_type and m.stat_affected == stat)

    def _unit_is_enemy(self, battle: BattleState, unit_id: str,
                       other_id: str) -> bool:
        """Check whether two units belong to opposing factions."""
        f1 = battle.units.get(unit_id, "")
        f2 = battle.units.get(other_id, "")
        return f1 != f2 and f1 != "" and f2 != ""

    def _check_battle_victory(self, battle: BattleState) -> None:
        """Determine if a battle has a winner and update its phase."""
        if battle.phase in (CombatPhase.VICTORY.value,
                            CombatPhase.DEFEAT.value):
            return
        faction_units: Dict[str, List[str]] = {}
        for uid, fid in battle.units.items():
            unit = self._units.get(uid)
            if unit and unit.status != UnitStatus.DEAD.value:
                faction_units.setdefault(fid, []).append(uid)
        alive_factions = [f for f in battle.factions if f in faction_units]
        if len(alive_factions) <= 1:
            battle.winner = alive_factions[0] if alive_factions else ""
            battle.ended_at = _now()
            if battle.winner == "faction_player_alliance":
                battle.phase = CombatPhase.VICTORY.value
            elif battle.winner:
                battle.phase = CombatPhase.DEFEAT.value
            else:
                battle.phase = CombatPhase.RESOLUTION.value
            self._emit_event(TacticalGridEventKind.BATTLE_ENDED.value,
                             battle_id=battle.battle_id,
                             data={"winner": battle.winner,
                                   "phase": battle.phase})

    # ------------------------------------------------------------------
    # Grid Management
    # ------------------------------------------------------------------

    def register_grid(self, grid_id: str, name: str, grid_type: str,
                      width: int, height: int, origin_x: int = 0,
                      origin_y: int = 0,
                      metadata: Optional[Dict[str, Any]] = None
                      ) -> Tuple[bool, str, Optional[TacticalGrid]]:
        """Register a new tactical grid with generated cells."""
        with _lock:
            if grid_id in self._grids:
                return False, "grid_exists", None
            if len(self._grids) >= _MAX_GRIDS:
                return False, "max_grids", None
            if width <= 0 or height <= 0:
                return False, "invalid_dimensions", None
            if width * height > _MAX_CELLS_PER_GRID:
                return False, "grid_too_large", None
            resolved_type = self._resolve_grid_type(grid_type)
            grid = TacticalGrid(
                grid_id=grid_id, name=name, grid_type=resolved_type,
                width=width, height=height, origin_x=origin_x,
                origin_y=origin_y, metadata=metadata or {})
            for y in range(height):
                for x in range(width):
                    key = _cell_key(x, y)
                    grid.cells[key] = GridCell(
                        cell_id=f"{grid_id}_{x}_{y}", x=x, y=y,
                        terrain_type=TerrainType.PLAIN.value)
            self._grids[grid_id] = grid
            self._emit_event(
                TacticalGridEventKind.TERRAIN_CHANGED.value,
                cell_id=grid_id,
                data={"action": "grid_registered", "width": width,
                      "height": height, "grid_type": resolved_type})
            return True, "registered", grid

    def get_grid(self, grid_id: str) -> Optional[TacticalGrid]:
        """Retrieve a grid by its identifier."""
        with _lock:
            return self._grids.get(grid_id)

    def list_grids(self, grid_type: str = "") -> List[TacticalGrid]:
        """List all grids, optionally filtered by grid type."""
        with _lock:
            if grid_type:
                return [g for g in self._grids.values()
                        if g.grid_type == grid_type]
            return list(self._grids.values())

    def remove_grid(self, grid_id: str) -> Tuple[bool, str]:
        """Remove a grid. Grids tied to active battles cannot be removed."""
        with _lock:
            if grid_id not in self._grids:
                return False, "not_found"
            for battle in self._battles.values():
                if battle.grid_id == grid_id and battle.ended_at == 0:
                    return False, "grid_in_active_battle"
            del self._grids[grid_id]
            return True, "removed"

    # ------------------------------------------------------------------
    # Cell and Terrain Management
    # ------------------------------------------------------------------

    def set_terrain(self, grid_id: str, x: int, y: int,
                    terrain_type: str, elevation: int = 0,
                    movement_cost: int = 1
                    ) -> Tuple[bool, str, Optional[GridCell]]:
        """Set the terrain of a specific cell on a grid."""
        with _lock:
            grid = self._grids.get(grid_id)
            if not grid:
                return False, "grid_not_found", None
            if x < 0 or x >= grid.width or y < 0 or y >= grid.height:
                return False, "out_of_bounds", None
            key = _cell_key(x, y)
            cell = grid.cells.get(key)
            if not cell:
                return False, "cell_not_found", None
            resolved_terrain = self._resolve_terrain(terrain_type)
            cell.terrain_type = resolved_terrain
            cell.elevation = elevation
            cell.movement_cost = movement_cost
            impassable = (TerrainType.WALL.value, TerrainType.WATER.value,
                          TerrainType.LAVA.value, TerrainType.VOID.value)
            cell.is_passable = resolved_terrain not in impassable
            if resolved_terrain == TerrainType.FOREST.value:
                cell.cover_value = 2
            elif resolved_terrain == TerrainType.WALL.value:
                cell.cover_value = 3
            else:
                cell.cover_value = 0
            self._emit_event(
                TacticalGridEventKind.TERRAIN_CHANGED.value,
                cell_id=cell.cell_id,
                data={"terrain": resolved_terrain, "elevation": elevation,
                      "movement_cost": movement_cost})
            return True, "updated", cell

    def get_cell(self, grid_id: str, x: int, y: int) -> Optional[GridCell]:
        """Retrieve a cell at the given coordinates."""
        with _lock:
            grid = self._grids.get(grid_id)
            if not grid:
                return None
            return grid.cells.get(_cell_key(x, y))

    def get_cells_in_range(self, grid_id: str, x: int, y: int,
                           radius: int) -> List[GridCell]:
        """Return all cells within a radius of the given coordinates."""
        with _lock:
            grid = self._grids.get(grid_id)
            if not grid:
                return []
            result: List[GridCell] = []
            for cell in grid.cells.values():
                dist = self._grid_distance(grid, x, y, cell.x, cell.y)
                if dist <= radius:
                    result.append(cell)
            return result

    # ------------------------------------------------------------------
    # Unit Management
    # ------------------------------------------------------------------

    def register_unit(self, unit_id: str, name: str, unit_class: str,
                      move_type: str, attack_type: str, max_hp: int,
                      attack_power: int, defense: int, move_range: int,
                      attack_range: int, speed: int = 5,
                      facing: str = "south",
                      metadata: Optional[Dict[str, Any]] = None
                      ) -> Tuple[bool, str, Optional[TacticalUnit]]:
        """Register a new tactical unit."""
        with _lock:
            if unit_id in self._units:
                return False, "unit_exists", None
            if len(self._units) >= _MAX_UNITS:
                return False, "max_units", None
            resolved_facing = facing
            for fd in FacingDirection:
                if fd.value == facing:
                    resolved_facing = fd.value
                    break
            else:
                resolved_facing = FacingDirection.SOUTH.value
            unit = TacticalUnit(
                unit_id=unit_id, name=name, unit_class=unit_class,
                move_type=move_type, attack_type=attack_type, max_hp=max_hp,
                current_hp=max_hp, attack_power=attack_power, defense=defense,
                move_range=move_range, attack_range=attack_range, speed=speed,
                facing=resolved_facing, metadata=metadata or {})
            self._units[unit_id] = unit
            return True, "registered", unit

    def get_unit(self, unit_id: str) -> Optional[TacticalUnit]:
        """Retrieve a unit by its identifier."""
        with _lock:
            return self._units.get(unit_id)

    def list_units(self, battle_id: str = "",
                   faction_id: str = "") -> List[TacticalUnit]:
        """List units, optionally filtered by battle or faction."""
        with _lock:
            result: List[TacticalUnit] = []
            for unit in self._units.values():
                if faction_id:
                    in_battle = any(
                        b.units.get(unit.unit_id) == faction_id
                        for b in self._battles.values())
                    fac = self._factions.get(faction_id)
                    in_roster = fac and unit.unit_id in fac.unit_ids
                    if not in_battle and not in_roster:
                        continue
                if battle_id:
                    battle = self._battles.get(battle_id)
                    if not battle or unit.unit_id not in battle.units:
                        continue
                result.append(unit)
            return result

    def remove_unit(self, unit_id: str) -> Tuple[bool, str]:
        """Remove a unit. Units in active battles cannot be removed."""
        with _lock:
            if unit_id not in self._units:
                return False, "not_found"
            for battle in self._battles.values():
                if unit_id in battle.units and battle.ended_at == 0:
                    return False, "unit_in_active_battle"
            # Remove from faction rosters.
            for fac in self._factions.values():
                if unit_id in fac.unit_ids:
                    fac.unit_ids.remove(unit_id)
            del self._units[unit_id]
            return True, "removed"

    # ------------------------------------------------------------------
    # Faction Management
    # ------------------------------------------------------------------

    def register_faction(self, faction_id: str, name: str, color: str,
                         is_player_controlled: bool = True,
                         ai_strategy: str = "",
                         metadata: Optional[Dict[str, Any]] = None
                         ) -> Tuple[bool, str, Optional[Faction]]:
        """Register a new faction."""
        with _lock:
            if faction_id in self._factions:
                return False, "faction_exists", None
            if len(self._factions) >= _MAX_FACTIONS:
                return False, "max_factions", None
            faction = Faction(
                faction_id=faction_id, name=name, color=color,
                is_player_controlled=is_player_controlled,
                ai_strategy=ai_strategy, metadata=metadata or {})
            self._factions[faction_id] = faction
            return True, "registered", faction

    def get_faction(self, faction_id: str) -> Optional[Faction]:
        """Retrieve a faction by its identifier."""
        with _lock:
            return self._factions.get(faction_id)

    def list_factions(self, battle_id: str = "") -> List[Faction]:
        """List factions, optionally filtered by battle participation."""
        with _lock:
            if battle_id:
                battle = self._battles.get(battle_id)
                if not battle:
                    return []
                return [self._factions[fid] for fid in battle.factions
                        if fid in self._factions]
            return list(self._factions.values())

    # ------------------------------------------------------------------
    # Battle Management
    # ------------------------------------------------------------------

    def create_battle(self, grid_id: str, faction_ids: List[str],
                      metadata: Optional[Dict[str, Any]] = None
                      ) -> Tuple[bool, str, Optional[BattleState]]:
        """Create a new battle on a grid with the given factions."""
        with _lock:
            if grid_id not in self._grids:
                return False, "grid_not_found", None
            if len(self._battles) >= _MAX_BATTLES:
                return False, "max_battles", None
            if not faction_ids or len(faction_ids) < 2:
                return False, "need_two_factions", None
            for fid in faction_ids:
                if fid not in self._factions:
                    return False, f"faction_not_found:{fid}", None
            battle_id = _new_id("battle")
            battle = BattleState(
                battle_id=battle_id, grid_id=grid_id,
                phase=CombatPhase.SETUP.value, turn_number=1,
                current_faction=faction_ids[0], factions=list(faction_ids),
                started_at=_now(), metadata=metadata or {})
            self._battles[battle_id] = battle
            self._emit_event(
                TacticalGridEventKind.BATTLE_STARTED.value,
                battle_id=battle_id,
                data={"grid_id": grid_id, "factions": list(faction_ids)})
            return True, "created", battle

    def get_battle(self, battle_id: str) -> Optional[BattleState]:
        """Retrieve a battle by its identifier."""
        with _lock:
            return self._battles.get(battle_id)

    def list_battles(self, status: str = "") -> List[BattleState]:
        """List battles, optionally filtered by phase status."""
        with _lock:
            if status:
                return [b for b in self._battles.values()
                        if b.phase == status]
            return list(self._battles.values())

    def end_turn(self, battle_id: str,
                 faction_id: str) -> Tuple[bool, str, Optional[BattleState]]:
        """End the current faction's turn and advance to the next faction."""
        with _lock:
            battle = self._battles.get(battle_id)
            if not battle:
                return False, "battle_not_found", None
            if battle.phase in (CombatPhase.VICTORY.value,
                                CombatPhase.DEFEAT.value):
                return False, "battle_ended", None
            if battle.current_faction != faction_id:
                return False, "not_your_turn", None
            self._emit_event(
                TacticalGridEventKind.TURN_ENDED.value, battle_id=battle_id,
                data={"faction_id": faction_id, "turn_number": battle.turn_number})
            # Advance to the next faction in order.
            idx = battle.factions.index(faction_id)
            next_idx = (idx + 1) % len(battle.factions)
            if next_idx == 0:
                battle.turn_number += 1
            battle.current_faction = battle.factions[next_idx]
            battle.phase = (CombatPhase.PLAYER_TURN.value
                            if battle.current_faction == battle.factions[0]
                            else CombatPhase.ENEMY_TURN.value)
            # Reset exhausted units of the next faction to active.
            for uid, fid in battle.units.items():
                if fid == battle.current_faction:
                    unit = self._units.get(uid)
                    if unit and unit.status == UnitStatus.EXHAUSTED.value:
                        unit.status = UnitStatus.ACTIVE.value
            self._emit_event(
                TacticalGridEventKind.TURN_STARTED.value, battle_id=battle_id,
                data={"faction_id": battle.current_faction,
                      "turn_number": battle.turn_number})
            self._check_battle_victory(battle)
            return True, "turn_ended", battle

    # ------------------------------------------------------------------
    # Combat Actions
    # ------------------------------------------------------------------

    def deploy_unit(self, battle_id: str, unit_id: str, x: int, y: int,
                    faction_id: str
                    ) -> Tuple[bool, str, Optional[BattleState]]:
        """Deploy a unit onto a cell in a battle for a faction."""
        with _lock:
            battle = self._battles.get(battle_id)
            if not battle:
                return False, "battle_not_found", None
            if battle.phase not in (CombatPhase.SETUP.value,
                                    CombatPhase.DEPLOY.value,
                                    CombatPhase.PLAYER_TURN.value,
                                    CombatPhase.ENEMY_TURN.value):
                return False, "battle_not_deployable", None
            grid = self._grids.get(battle.grid_id)
            if not grid:
                return False, "grid_not_found", None
            if x < 0 or x >= grid.width or y < 0 or y >= grid.height:
                return False, "out_of_bounds", None
            unit = self._units.get(unit_id)
            if not unit:
                return False, "unit_not_found", None
            if faction_id not in battle.factions:
                return False, "faction_not_in_battle", None
            faction_count = sum(1 for f in battle.units.values() if f == faction_id)
            if faction_count >= self._config.max_units_per_faction:
                return False, "max_units_per_faction", None
            cell = grid.cells.get(_cell_key(x, y))
            if not cell:
                return False, "cell_not_found", None
            if cell.is_occupied:
                return False, "cell_occupied", None
            if not self._is_terrain_passable(cell.terrain_type, unit.move_type):
                return False, "terrain_impassable", None
            cell.is_occupied = True
            cell.occupant_id = unit_id
            unit.position_x = x
            unit.position_y = y
            unit.status = UnitStatus.ACTIVE.value
            battle.units[unit_id] = faction_id
            if unit_id not in self._factions[faction_id].unit_ids:
                self._factions[faction_id].unit_ids.append(unit_id)
            self._emit_event(
                TacticalGridEventKind.UNIT_DEPLOYED.value,
                battle_id=battle_id, unit_id=unit_id, cell_id=cell.cell_id,
                data={"x": x, "y": y, "faction_id": faction_id})
            return True, "deployed", battle

    def move_unit(self, battle_id: str, unit_id: str, x: int, y: int
                  ) -> Tuple[bool, str, Optional[BattleState]]:
        """Move a unit to a new cell within its movement range."""
        with _lock:
            battle = self._battles.get(battle_id)
            if not battle:
                return False, "battle_not_found", None
            if battle.phase in (CombatPhase.VICTORY.value,
                                CombatPhase.DEFEAT.value):
                return False, "battle_ended", None
            unit = self._units.get(unit_id)
            if not unit:
                return False, "unit_not_found", None
            if unit.status in (UnitStatus.DEAD.value, UnitStatus.STUNNED.value,
                               UnitStatus.FROZEN.value):
                return False, f"unit_{unit.status}", None
            faction_id = battle.units.get(unit_id)
            if not faction_id:
                return False, "unit_not_in_battle", None
            if battle.current_faction != faction_id:
                return False, "not_your_turn", None
            grid = self._grids.get(battle.grid_id)
            if not grid:
                return False, "grid_not_found", None
            if x < 0 or x >= grid.width or y < 0 or y >= grid.height:
                return False, "out_of_bounds", None
            if (x, y) not in self._compute_reachable(grid, unit):
                return False, "out_of_move_range", None
            dest_cell = grid.cells.get(_cell_key(x, y))
            if not dest_cell:
                return False, "cell_not_found", None
            if dest_cell.is_occupied:
                return False, "cell_occupied", None
            # Free the old cell and occupy the destination.
            old_cell = grid.cells.get(_cell_key(unit.position_x, unit.position_y))
            if old_cell:
                old_cell.is_occupied = False
                old_cell.occupant_id = ""
            dest_cell.is_occupied = True
            dest_cell.occupant_id = unit_id
            unit.position_x = x
            unit.position_y = y
            # Update facing based on movement direction.
            dx = x - (old_cell.x if old_cell else x)
            dy = y - (old_cell.y if old_cell else y)
            unit.facing = self._facing_from_delta(dx, dy, unit.facing)
            unit.status = UnitStatus.EXHAUSTED.value
            self._emit_event(
                TacticalGridEventKind.UNIT_MOVED.value,
                battle_id=battle_id, unit_id=unit_id, cell_id=dest_cell.cell_id,
                data={"x": x, "y": y, "facing": unit.facing})
            return True, "moved", battle

    def _kill_unit(self, grid: Optional[TacticalGrid],
                   unit: TacticalUnit) -> None:
        """Mark a unit as dead, clear its position, and free its cell."""
        unit.status = UnitStatus.DEAD.value
        unit.position_x = -1
        unit.position_y = -1
        self._stats.units_lost += 1
        if grid:
            for cell in grid.cells.values():
                if cell.occupant_id == unit.unit_id:
                    cell.is_occupied = False
                    cell.occupant_id = ""
                    break

    def attack_unit(self, battle_id: str, attacker_id: str,
                    target_id: str
                    ) -> Tuple[bool, str, Optional[BattleState]]:
        """Resolve an attack from one unit against another."""
        with _lock:
            battle = self._battles.get(battle_id)
            if not battle:
                return False, "battle_not_found", None
            if battle.phase in (CombatPhase.VICTORY.value,
                                CombatPhase.DEFEAT.value):
                return False, "battle_ended", None
            attacker = self._units.get(attacker_id)
            target = self._units.get(target_id)
            if not attacker:
                return False, "attacker_not_found", None
            if not target:
                return False, "target_not_found", None
            if attacker.status in (UnitStatus.DEAD.value, UnitStatus.STUNNED.value,
                                   UnitStatus.FROZEN.value):
                return False, f"attacker_{attacker.status}", None
            if target.status == UnitStatus.DEAD.value:
                return False, "target_dead", None
            attacker_faction = battle.units.get(attacker_id)
            if not attacker_faction:
                return False, "attacker_not_in_battle", None
            if battle.current_faction != attacker_faction:
                return False, "not_your_turn", None
            if (not self._unit_is_enemy(battle, attacker_id, target_id)
                    and not self._config.friendly_fire):
                return False, "friendly_fire_disabled", None
            # Check attack range.
            in_range = self._compute_attack_targets(battle, attacker)
            if target_id not in in_range:
                return False, "target_out_of_range", None
            grid = self._grids.get(battle.grid_id)
            damage = self._compute_damage(grid, attacker, target)
            if damage > 0:
                target.current_hp = max(0, target.current_hp - damage)
                self._stats.attacks_made += 1
                self._emit_event(
                    TacticalGridEventKind.UNIT_ATTACKED.value,
                    battle_id=battle_id, unit_id=attacker_id,
                    data={"target_id": target_id, "damage": damage,
                          "attack_type": attacker.attack_type})
                self._emit_event(
                    TacticalGridEventKind.UNIT_DAMAGED.value,
                    battle_id=battle_id, unit_id=target_id,
                    data={"damage": damage, "remaining_hp": target.current_hp,
                          "attacker_id": attacker_id})
                if target.current_hp <= 0:
                    self._kill_unit(grid, target)
            attacker.status = UnitStatus.EXHAUSTED.value
            # Counter attack if enabled, target survived, and in range.
            if (self._config.counter_attack
                    and target.status != UnitStatus.DEAD.value
                    and target.attack_range > 0):
                counter_in_range = self._compute_attack_targets(battle, target)
                if attacker_id in counter_in_range:
                    counter_dmg = self._compute_damage(grid, target, attacker)
                    if counter_dmg > 0:
                        attacker.current_hp = max(
                            0, attacker.current_hp - counter_dmg)
                        self._emit_event(
                            TacticalGridEventKind.UNIT_DAMAGED.value,
                            battle_id=battle_id, unit_id=attacker_id,
                            data={"damage": counter_dmg,
                                  "remaining_hp": attacker.current_hp,
                                  "counter": True,
                                  "attacker_id": target_id})
                        if attacker.current_hp <= 0:
                            self._kill_unit(grid, attacker)
            self._check_battle_victory(battle)
            return True, "attacked", battle

    def calculate_damage(self, battle_id: str, attacker_id: str,
                         target_id: str) -> Optional[int]:
        """Calculate the damage an attacker would deal to a target."""
        with _lock:
            battle = self._battles.get(battle_id)
            if not battle:
                return None
            attacker = self._units.get(attacker_id)
            target = self._units.get(target_id)
            if not attacker or not target:
                return None
            grid = self._grids.get(battle.grid_id)
            return self._compute_damage(grid, attacker, target)

    def calculate_move_range(self, battle_id: str,
                             unit_id: str) -> List[Tuple[int, int]]:
        """Return the list of reachable coordinates for a unit."""
        with _lock:
            battle = self._battles.get(battle_id)
            unit = self._units.get(unit_id)
            grid = self._grids.get(battle.grid_id) if battle else None
            if not battle or not unit or not grid:
                return []
            return list(self._compute_reachable(grid, unit))

    def calculate_attack_range(self, battle_id: str,
                               unit_id: str) -> List[Tuple[int, int]]:
        """Return the list of coordinates within a unit's attack range."""
        with _lock:
            battle = self._battles.get(battle_id)
            unit = self._units.get(unit_id)
            grid = self._grids.get(battle.grid_id) if battle else None
            if not battle or not unit or not grid:
                return []
            return self._compute_attack_cells(grid, unit)

    # ------------------------------------------------------------------
    # Combat Calculation Helpers
    # ------------------------------------------------------------------

    def _facing_from_delta(self, dx: int, dy: int, default: str) -> str:
        """Determine facing direction from a movement delta."""
        if dx == 0 and dy == 0:
            return default
        if dx > 0 and dy > 0:
            return FacingDirection.SOUTHEAST.value
        if dx > 0 and dy < 0:
            return FacingDirection.NORTHEAST.value
        if dx < 0 and dy > 0:
            return FacingDirection.SOUTHWEST.value
        if dx < 0 and dy < 0:
            return FacingDirection.NORTHWEST.value
        if dx > 0:
            return FacingDirection.EAST.value
        if dx < 0:
            return FacingDirection.WEST.value
        return (FacingDirection.SOUTH.value if dy > 0
                else FacingDirection.NORTH.value)

    def _compute_reachable(self, grid: TacticalGrid,
                           unit: TacticalUnit) -> List[Tuple[int, int]]:
        """Compute reachable cells using a bounded flood fill."""
        if unit.position_x < 0 or unit.position_y < 0:
            return []
        max_range = unit.move_range
        start = (unit.position_x, unit.position_y)
        visited: Dict[Tuple[int, int], int] = {start: 0}
        frontier: List[Tuple[int, int]] = [start]
        result: List[Tuple[int, int]] = []
        while frontier:
            current = frontier.pop(0)
            cx, cy = current
            cost = visited[current]
            if cost > 0:
                result.append(current)
            if cost >= max_range:
                continue
            for nx, ny in self._get_neighbors(grid, cx, cy):
                if not (0 <= nx < grid.width and 0 <= ny < grid.height):
                    continue
                ncell = grid.cells.get(_cell_key(nx, ny))
                if not ncell:
                    continue
                if ncell.is_occupied and ncell.occupant_id != unit.unit_id:
                    continue
                if not self._is_terrain_passable(ncell.terrain_type, unit.move_type):
                    continue
                new_cost = cost + max(1, ncell.movement_cost)
                if new_cost > max_range:
                    continue
                if (nx, ny) not in visited or visited[(nx, ny)] > new_cost:
                    visited[(nx, ny)] = new_cost
                    frontier.append((nx, ny))
        return result

    def _get_neighbors(self, grid: TacticalGrid, x: int,
                       y: int) -> List[Tuple[int, int]]:
        """Return neighbor coordinates based on grid topology."""
        if grid.grid_type == GridType.HEX.value:
            # Axial hex neighbors (pointy-top offset coordinates).
            return [(x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1),
                    (x + 1, y - 1), (x - 1, y + 1)]
        # Square, offset, and isometric grids use 8-way neighbors.
        return [(x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1),
                (x + 1, y + 1), (x - 1, y - 1),
                (x + 1, y - 1), (x - 1, y + 1)]

    def _compute_attack_cells(self, grid: TacticalGrid,
                              unit: TacticalUnit) -> List[Tuple[int, int]]:
        """Return all cells within a unit's attack range."""
        if unit.position_x < 0 or unit.position_y < 0:
            return []
        result: List[Tuple[int, int]] = []
        for cell in grid.cells.values():
            if cell.x == unit.position_x and cell.y == unit.position_y:
                continue
            if self._grid_distance(grid, unit.position_x,
                                   unit.position_y, cell.x, cell.y) <= unit.attack_range:
                result.append((cell.x, cell.y))
        return result

    def _compute_attack_targets(self, battle: BattleState,
                                unit: TacticalUnit) -> List[str]:
        """Return unit IDs of enemy targets within attack range."""
        grid = self._grids.get(battle.grid_id)
        if not grid:
            return []
        targets: List[str] = []
        for cx, cy in self._compute_attack_cells(grid, unit):
            cell = grid.cells.get(_cell_key(cx, cy))
            if (cell and cell.is_occupied and cell.occupant_id
                    and self._unit_is_enemy(battle, unit.unit_id,
                                            cell.occupant_id)):
                target_unit = self._units.get(cell.occupant_id)
                if target_unit and target_unit.status != UnitStatus.DEAD.value:
                    targets.append(cell.occupant_id)
        return targets

    def _compute_damage(self, grid: Optional[TacticalGrid],
                        attacker: TacticalUnit,
                        target: TacticalUnit) -> int:
        """Compute damage with terrain, elevation, and flanking modifiers."""
        damage = float(max(1, attacker.attack_power - target.defense // 2))
        if self._config.terrain_bonuses and grid:
            tcell = grid.cells.get(_cell_key(target.position_x,
                                             target.position_y))
            if tcell:
                damage = max(1.0, damage - self._get_terrain_modifier(
                    tcell.terrain_type, "defense"))
                # Cover reduces ranged and throw damage.
                if (tcell.cover_value > 0 and attacker.attack_type in (
                        AttackType.RANGED.value, AttackType.THROW.value)):
                    damage = max(1.0, damage - tcell.cover_value)
        # Elevation advantage for the attacker.
        if self._config.elevation_bonus and grid:
            acell = grid.cells.get(_cell_key(attacker.position_x,
                                             attacker.position_y))
            tcell = grid.cells.get(_cell_key(target.position_x,
                                             target.position_y))
            if acell and tcell and acell.elevation > tcell.elevation:
                damage += float(acell.elevation - tcell.elevation) * 2.0
        # Flanking bonus when attacking from behind the target's facing.
        if self._config.flanking_bonus and grid:
            if self._is_flanking(grid, attacker, target):
                damage *= 1.5
        # Magic attacks partially bypass defense.
        if attacker.attack_type == AttackType.MAGIC.value:
            damage += float(target.defense) * 0.25
        return max(1, int(round(damage)))

    def _is_flanking(self, grid: TacticalGrid, attacker: TacticalUnit,
                     target: TacticalUnit) -> bool:
        """Check if the attacker strikes the target from a flanking angle."""
        dx = attacker.position_x - target.position_x
        dy = attacker.position_y - target.position_y
        if dx == 0 and dy == 0:
            return False
        front_dirs = {
            "north": (0, -1), "south": (0, 1), "east": (1, 0), "west": (-1, 0),
            "northeast": (1, -1), "northwest": (-1, -1),
            "southeast": (1, 1), "southwest": (-1, 1)}
        fx, fy = front_dirs.get(target.facing, (0, 1))
        # A negative dot product means the attacker is behind the facing.
        return (dx * fx + dy * fy) < 0

    # ------------------------------------------------------------------
    # Fog of War
    # ------------------------------------------------------------------

    def set_fog_of_war(self, battle_id: str,
                       enabled: bool) -> Tuple[bool, str]:
        """Enable or disable fog of war for a battle."""
        with _lock:
            battle = self._battles.get(battle_id)
            if not battle:
                return False, "battle_not_found"
            battle.metadata["fog_of_war"] = enabled
            if not enabled:
                grid = self._grids.get(battle.grid_id)
                if grid:
                    for cell in grid.cells.values():
                        cell.is_visible = True
            return True, "updated"

    def reveal_area(self, battle_id: str, x: int, y: int,
                    radius: int) -> Tuple[bool, str, int]:
        """Reveal cells within a radius for a battle. Returns count revealed."""
        with _lock:
            battle = self._battles.get(battle_id)
            if not battle:
                return False, "battle_not_found", 0
            grid = self._grids.get(battle.grid_id)
            if not grid:
                return False, "grid_not_found", 0
            revealed = 0
            for cell in grid.cells.values():
                if (self._grid_distance(grid, x, y, cell.x, cell.y) <= radius
                        and not cell.is_visible):
                    cell.is_visible = True
                    revealed += 1
            return True, "revealed", revealed

    # ------------------------------------------------------------------
    # Simulation and Observability
    # ------------------------------------------------------------------

    def tick(self, dt: float = 1.0) -> Dict[str, Any]:
        """Advance the simulation by a time step."""
        with _lock:
            self._tick_count += 1
            now = _now()
            expired_turns = 0
            status_effects_processed = 0
            for battle in self._battles.values():
                if battle.phase in (CombatPhase.VICTORY.value,
                                    CombatPhase.DEFEAT.value):
                    continue
                # Check turn time limit and auto-end expired turns.
                turn_start = battle.metadata.get("turn_started_at", 0)
                if (turn_start and self._config.turn_time_limit > 0
                        and now - turn_start > self._config.turn_time_limit):
                    if battle.current_faction:
                        idx = battle.factions.index(battle.current_faction)
                        next_idx = (idx + 1) % len(battle.factions)
                        if next_idx == 0:
                            battle.turn_number += 1
                        battle.current_faction = battle.factions[next_idx]
                        battle.metadata["turn_started_at"] = now
                        expired_turns += 1
                # Process status effects on units in this battle.
                grid = self._grids.get(battle.grid_id)
                for uid in battle.units:
                    unit = self._units.get(uid)
                    if not unit or unit.status == UnitStatus.DEAD.value:
                        continue
                    dot_damage = 0
                    if unit.status == UnitStatus.POISONED.value:
                        dot_damage = 2
                    elif unit.status == UnitStatus.BURNING.value:
                        dot_damage = 3
                    if dot_damage > 0:
                        unit.current_hp = max(0, unit.current_hp - dot_damage)
                        status_effects_processed += 1
                        if unit.current_hp <= 0:
                            self._kill_unit(grid, unit)
                self._check_battle_victory(battle)
            self._emit_event(
                TacticalGridEventKind.TURN_ENDED.value,
                data={"action": "tick", "dt": dt,
                      "expired_turns": expired_turns,
                      "status_effects_processed": status_effects_processed})
            return {
                "success": True,
                "tick_count": self._tick_count,
                "expired_turns": expired_turns,
                "status_effects_processed": status_effects_processed,
            }

    def get_status(self) -> Dict[str, Any]:
        """Return a summary of the current system state."""
        with _lock:
            self._update_stats()
            phase_dist: Dict[str, int] = {}
            for battle in self._battles.values():
                phase_dist[battle.phase] = phase_dist.get(battle.phase, 0) + 1
            terrain_dist: Dict[str, int] = {}
            for grid in self._grids.values():
                for cell in grid.cells.values():
                    terrain_dist[cell.terrain_type] = (
                        terrain_dist.get(cell.terrain_type, 0) + 1)
            return {
                "initialized": self._initialized,
                "total_grids": len(self._grids),
                "total_battles": len(self._battles),
                "active_battles": self._stats.active_battles,
                "total_units": len(self._units),
                "total_factions": len(self._factions),
                "total_terrain_modifiers": len(self._terrain_modifiers),
                "total_events": len(self._events),
                "tick_count": self._tick_count,
                "phase_distribution": phase_dist,
                "terrain_distribution": terrain_dist,
            }

    def reset(self) -> Tuple[bool, str]:
        """Clear all state and re-seed initial data."""
        with _lock:
            self._grids.clear()
            self._battles.clear()
            self._units.clear()
            self._factions.clear()
            self._terrain_modifiers.clear()
            self._events.clear()
            self._stats = TacticalGridStats()
            self._config = TacticalGridConfig()
            self._tick_count = 0
            self._event_counter = 0
            self._initialized = False
            self._seed()
            self._emit_event(TacticalGridEventKind.BATTLE_ENDED.value,
                             data={"action": "reset"})
            return True, "reset"

    def get_snapshot(self) -> TacticalGridSnapshot:
        """Capture a full state snapshot of the system."""
        with _lock:
            self._update_stats()
            return TacticalGridSnapshot(
                timestamp=_now(), grids_count=len(self._grids),
                battles_count=len(self._battles),
                active_battles=self._stats.active_battles,
                units_count=len(self._units),
                config=self._config.to_dict())

    def get_stats(self) -> TacticalGridStats:
        """Return aggregate statistics for the system."""
        with _lock:
            self._update_stats()
            return self._stats

    def set_config(self, updates: Dict[str, Any]
                   ) -> Tuple[bool, str, TacticalGridConfig]:
        """Update configuration fields from a dictionary of changes."""
        with _lock:
            changed = []
            for k, v in updates.items():
                if hasattr(self._config, k):
                    old_val = getattr(self._config, k)
                    setattr(self._config, k, v)
                    changed.append(f"{k}: {old_val}->{v}")
            if changed:
                self._emit_event(
                    TacticalGridEventKind.TERRAIN_CHANGED.value,
                    data={"action": "config_updated", "changes": changed})
            return True, "updated", self._config

    def get_config(self) -> TacticalGridConfig:
        """Return the current configuration."""
        with _lock:
            return self._config

    def list_events(self, limit: int = 100, battle_id: str = "",
                    event_type: str = "") -> List[TacticalGridEvent]:
        """List audit events with optional filtering."""
        with _lock:
            results = list(self._events)
            if battle_id:
                results = [e for e in results if e.battle_id == battle_id]
            if event_type:
                results = [e for e in results if e.kind == event_type]
            if limit > 0:
                results = results[-limit:]
            return results


def get_tactical_grid_system() -> TacticalGridSystem:
    """Factory that returns the singleton TacticalGridSystem instance."""
    return TacticalGridSystem.get_instance()
