"""
SparkLabs Engine - Procedural Dungeon Generator

Procedural dungeon and indoor level generation engine. Creates room
layouts, connects corridors, places decorations, distributes encounters
and treasures, and generates narrative-consistent dungeon themes using
algorithmic design principles.

Core capabilities:
  - Room layout generation with configurable size distributions
  - Corridor connection algorithms (BSP, cellular, digger-based)
  - Room decoration with thematic furniture and prop placement
  - Encounter distribution (combat, puzzle, treasure, trap, empty)
  - Dungeon theme management (cave, castle, tomb, lab, etc.)
  - Difficulty curve generation across dungeon levels
  - Key-lock progression (keys, doors, backtracking)
  - Secret room and hidden passage generation
  - Lighting and atmosphere zone placement

Architecture:
  EngineProceduralDungeon (Singleton)
    |-- DungeonRoom (dataclass)
    |-- DungeonCorridor (dataclass)
    |-- EncounterNode (dataclass)
    |-- TreasureNode (dataclass)
    |-- DungeonTheme (dataclass)
    |-- DungeonLayout (dataclass)
    |-- generate_dungeon_layout()
    |-- connect_rooms()
    |-- distribute_encounters()
    |-- place_treasures()
    |-- define_dungeon_theme()
    |-- compute_difficulty_curve()
"""

from __future__ import annotations

import math
import random
import threading
import time as _time_module
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


class RoomType(Enum):
    SPAWN = "spawn"
    COMBAT = "combat"
    TREASURE = "treasure"
    PUZZLE = "puzzle"
    BOSS = "boss"
    REST = "rest"
    SHOP = "shop"
    SECRET = "secret"
    CORRIDOR_NODE = "corridor_node"
    EXIT = "exit"


class EncounterType(Enum):
    COMBAT_EASY = "combat_easy"
    COMBAT_MEDIUM = "combat_medium"
    COMBAT_HARD = "combat_hard"
    COMBAT_BOSS = "combat_boss"
    PUZZLE = "puzzle"
    TRAP = "trap"
    SOCIAL = "social"
    AMBIENT = "ambient"
    NONE = "none"


class TreasureCategory(Enum):
    COMMON = "common"
    UNCOMMON = "uncommon"
    RARE = "rare"
    LEGENDARY = "legendary"
    KEY_ITEM = "key_item"
    LORE_ITEM = "lore_item"


class DungeonThemeCategory(Enum):
    CAVE = "cave"
    CASTLE = "castle"
    TOMB = "tomb"
    DUNGEON_PRISON = "dungeon_prison"
    TEMPLE = "temple"
    LABORATORY = "laboratory"
    RUIN = "ruin"
    SEWER = "sewer"
    MINES = "mines"
    FORTRESS = "fortress"
    NEST = "nest"
    CRYPT = "crypt"


class GenerationAlgorithm(Enum):
    BSP = "bsp"
    CELLULAR = "cellular"
    DIGGER = "digger"
    ROOM_PLACEMENT = "room_placement"
    HYBRID = "hybrid"


@dataclass
class DungeonRoom:
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    name: str = ""
    room_type: RoomType = RoomType.COMBAT
    x: int = 0
    y: int = 0
    width: int = 8
    height: int = 8
    difficulty_level: float = 0.5
    encounter: Optional[str] = None
    treasures: List[str] = field(default_factory=list)
    connections: List[str] = field(default_factory=list)
    door_directions: List[str] = field(default_factory=list)
    lighting: str = "torch"
    tags: List[str] = field(default_factory=list)
    created_at: float = field(default_factory=_time_module.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "room_type": self.room_type.value,
            "x": self.x,
            "y": self.y,
            "width": self.width,
            "height": self.height,
            "difficulty_level": self.difficulty_level,
            "encounter": self.encounter,
            "treasures": self.treasures,
            "connections": self.connections,
            "door_directions": self.door_directions,
            "lighting": self.lighting,
            "tags": self.tags,
            "created_at": self.created_at,
        }


@dataclass
class DungeonCorridor:
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    from_room_id: str = ""
    to_room_id: str = ""
    width: int = 2
    length: int = 0
    direction: str = "horizontal"
    corridor_type: str = "straight"
    locked: bool = False
    key_id: Optional[str] = None
    secret: bool = False
    created_at: float = field(default_factory=_time_module.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "from_room_id": self.from_room_id,
            "to_room_id": self.to_room_id,
            "width": self.width,
            "length": self.length,
            "direction": self.direction,
            "corridor_type": self.corridor_type,
            "locked": self.locked,
            "key_id": self.key_id,
            "secret": self.secret,
            "created_at": self.created_at,
        }


@dataclass
class EncounterNode:
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    room_id: str = ""
    encounter_type: EncounterType = EncounterType.COMBAT_MEDIUM
    name: str = ""
    description: str = ""
    difficulty: float = 0.5
    reward_pool: List[str] = field(default_factory=list)
    enemy_count: int = 0
    enemy_types: List[str] = field(default_factory=list)
    puzzle_type: Optional[str] = None
    trap_type: Optional[str] = None
    created_at: float = field(default_factory=_time_module.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "room_id": self.room_id,
            "encounter_type": self.encounter_type.value,
            "name": self.name,
            "description": self.description,
            "difficulty": self.difficulty,
            "reward_pool": self.reward_pool,
            "enemy_count": self.enemy_count,
            "enemy_types": self.enemy_types,
            "puzzle_type": self.puzzle_type,
            "trap_type": self.trap_type,
            "created_at": self.created_at,
        }


@dataclass
class TreasureNode:
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    room_id: str = ""
    category: TreasureCategory = TreasureCategory.COMMON
    name: str = ""
    description: str = ""
    value_score: float = 0.5
    is_key_item: bool = False
    unlocks_room_id: Optional[str] = None
    lore_text: Optional[str] = None
    created_at: float = field(default_factory=_time_module.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "room_id": self.room_id,
            "category": self.category.value,
            "name": self.name,
            "description": self.description,
            "value_score": self.value_score,
            "is_key_item": self.is_key_item,
            "unlocks_room_id": self.unlocks_room_id,
            "lore_text": self.lore_text,
            "created_at": self.created_at,
        }


@dataclass
class DungeonTheme:
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    name: str = ""
    category: DungeonThemeCategory = DungeonThemeCategory.CAVE
    primary_material: str = "stone"
    secondary_material: str = "wood"
    color_scheme: List[str] = field(default_factory=list)
    ambient_light_color: str = "#4a3728"
    ambient_sound: str = "dripping_water"
    enemy_families: List[str] = field(default_factory=list)
    prop_categories: List[str] = field(default_factory=list)
    trap_themes: List[str] = field(default_factory=list)
    treasure_themes: List[str] = field(default_factory=list)
    difficulty_multiplier: float = 1.0
    created_at: float = field(default_factory=_time_module.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "category": self.category.value,
            "primary_material": self.primary_material,
            "secondary_material": self.secondary_material,
            "color_scheme": self.color_scheme,
            "ambient_light_color": self.ambient_light_color,
            "ambient_sound": self.ambient_sound,
            "enemy_families": self.enemy_families,
            "prop_categories": self.prop_categories,
            "trap_themes": self.trap_themes,
            "treasure_themes": self.treasure_themes,
            "difficulty_multiplier": self.difficulty_multiplier,
            "created_at": self.created_at,
        }


@dataclass
class DungeonLayout:
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    name: str = ""
    seed: int = 0
    algorithm: GenerationAlgorithm = GenerationAlgorithm.BSP
    theme_id: str = ""
    rooms: List[str] = field(default_factory=list)
    corridors: List[str] = field(default_factory=list)
    total_area: int = 0
    room_count: int = 0
    max_depth: int = 0
    created_at: float = field(default_factory=_time_module.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "seed": self.seed,
            "algorithm": self.algorithm.value,
            "theme_id": self.theme_id,
            "rooms": self.rooms,
            "corridors": self.corridors,
            "total_area": self.total_area,
            "room_count": self.room_count,
            "max_depth": self.max_depth,
            "created_at": self.created_at,
        }


_THEME_TEMPLATES: Dict[str, Dict[str, Any]] = {
    "castle": {
        "category": DungeonThemeCategory.CASTLE,
        "primary_material": "hewn_stone",
        "secondary_material": "oak_wood",
        "color_scheme": ["#4a4a5a", "#8a7a6a", "#c4a882"],
        "ambient_light_color": "#daa520",
        "ambient_sound": "torch_crackle",
        "enemy_families": ["royal_guard", "knight", "court_mage", "hunting_hound"],
        "prop_categories": ["armor_stands", "tapestries", "candle_holders", "thrones"],
        "trap_themes": ["arrow_trap", "pit_trap", "swinging_blade"],
        "treasure_themes": ["royal_jewels", "ancient_crowns", "ceremonial_armor"],
    },
    "cave": {
        "category": DungeonThemeCategory.CAVE,
        "primary_material": "natural_stone",
        "secondary_material": "moss",
        "color_scheme": ["#2a2a2a", "#3a3a2a", "#1a3a1a"],
        "ambient_light_color": "#2a4a2a",
        "ambient_sound": "dripping_water",
        "enemy_families": ["cave_spider", "rock_golem", "bat_swarm", "slime"],
        "prop_categories": ["stalagmites", "mineral_deposits", "mushroom_clusters"],
        "trap_themes": ["rockfall", "poison_spores", "collapsing_floor"],
        "treasure_themes": ["rare_minerals", "fossils", "ancient_amber"],
    },
    "tomb": {
        "category": DungeonThemeCategory.TOMB,
        "primary_material": "sandstone",
        "secondary_material": "gold_trim",
        "color_scheme": ["#c4a43e", "#8a7a2a", "#4a3a1a"],
        "ambient_light_color": "#daa520",
        "ambient_sound": "distant_chants",
        "enemy_families": ["mummy", "scarab_swarm", "tomb_guardian", "cursed_priest"],
        "prop_categories": ["sarcophagi", "hieroglyph_walls", "offering_altars"],
        "trap_themes": ["curse_trap", "sand_pit", "dart_gallery"],
        "treasure_themes": ["pharaoh_artifacts", "golden_masks", "jeweled_amulets"],
    },
    "laboratory": {
        "category": DungeonThemeCategory.LABORATORY,
        "primary_material": "metal_plating",
        "secondary_material": "glass",
        "color_scheme": ["#3a3a4a", "#5a7a8a", "#1a3a5a"],
        "ambient_light_color": "#4a8afa",
        "ambient_sound": "machine_hum",
        "enemy_families": ["alchemical_horror", "security_bot", "escaped_experiment", "mad_scientist"],
        "prop_categories": ["alchemy_tables", "specimen_jars", "arcane_machinery"],
        "trap_themes": ["electric_field", "toxic_gas", "crushing_press"],
        "treasure_themes": ["research_blueprints", "experimental_elixirs", "power_cores"],
    },
    "temple": {
        "category": DungeonThemeCategory.TEMPLE,
        "primary_material": "white_marble",
        "secondary_material": "gold_trim",
        "color_scheme": ["#e8e0d0", "#c4b898", "#8a7a5a"],
        "ambient_light_color": "#fffaf0",
        "ambient_sound": "choir_echoes",
        "enemy_families": ["temple_guardian", "holy_knight", "fallen_priest", "celestial_being"],
        "prop_categories": ["altars", "stained_glass", "incense_burners", "holy_fontains"],
        "trap_themes": ["light_beam", "sacred_fire", "judgment_scale"],
        "treasure_themes": ["holy_relics", "blessed_weapons", "sacred_texts"],
    },
}

_ENEMY_POOLS: Dict[str, List[Tuple[str, float]]] = {
    "castle": [("guard_captain", 0.6), ("royal_mage", 0.7), ("elite_knight", 0.8), ("throne_champion", 0.9)],
    "cave": [("cave_troll", 0.6), ("giant_spider", 0.5), ("rock_elemental", 0.7), ("cave_dragon", 0.95)],
    "tomb": [("anubis_guardian", 0.6), ("cursed_pharaoh", 0.8), ("scarab_queen", 0.7), ("tomb_lord", 0.95)],
    "laboratory": [("security_mech", 0.5), ("rogue_ai", 0.7), ("chimera", 0.8), ("grand_alchemist", 0.9)],
    "temple": [("holy_paladin", 0.6), ("oracle_guardian", 0.7), ("fallen_seraph", 0.85), ("divine_arbiter", 0.95)],
}


class EngineProceduralDungeon:
    _instance: Optional["EngineProceduralDungeon"] = None
    _lock: threading.RLock = threading.RLock()

    def __new__(cls) -> "EngineProceduralDungeon":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    instance = super().__new__(cls)
                    instance._initialized = False
                    cls._instance = instance
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self._rooms: Dict[str, DungeonRoom] = {}
        self._corridors: Dict[str, DungeonCorridor] = {}
        self._encounters: Dict[str, EncounterNode] = {}
        self._treasures: Dict[str, TreasureNode] = {}
        self._themes: Dict[str, DungeonTheme] = {}
        self._layouts: Dict[str, DungeonLayout] = {}
        self._total_layouts_generated: int = 0
        self._total_rooms_created: int = 0
        self._total_encounters_placed: int = 0

    def generate_dungeon_layout(
        self,
        name: str = "",
        seed: int = 0,
        algorithm: Optional[str] = None,
        theme_name: Optional[str] = None,
        room_count: int = 12,
        map_width: int = 100,
        map_height: int = 100,
    ) -> DungeonLayout:
        if seed == 0:
            seed = random.randint(1, 999999)
        rng = random.Random(seed)
        algo = GenerationAlgorithm(algorithm) if algorithm else GenerationAlgorithm.BSP

        theme = self.define_dungeon_theme(theme_name or "castle")
        theme_id = theme.id

        rooms = self._generate_rooms_bsp(rng, room_count, map_width, map_height)
        corridors = self._connect_rooms_mspt(rng, rooms)
        self._assign_room_types(rng, rooms)

        room_ids = [r.id for r in rooms]
        corridor_ids = [c.id for c in corridors]

        total_area = sum(r.width * r.height for r in rooms)
        max_depth = self._compute_max_depth(rooms, corridors)

        layout = DungeonLayout(
            name=name or f"dungeon_{seed}",
            seed=seed,
            algorithm=algo,
            theme_id=theme_id,
            rooms=room_ids,
            corridors=corridor_ids,
            total_area=total_area,
            room_count=len(rooms),
            max_depth=max_depth,
        )

        self._layouts[layout.id] = layout
        self._total_layouts_generated += 1
        return layout

    def _generate_rooms_bsp(
        self, rng: random.Random, room_count: int, map_width: int, map_height: int
    ) -> List[DungeonRoom]:
        rooms = []

        padding = 3
        min_size = 5
        max_size = 14

        for i in range(room_count):
            max_attempts = 50
            placed = False

            for _ in range(max_attempts):
                w = rng.randint(min_size, max_size)
                h = rng.randint(min_size, max_size)
                x = rng.randint(padding, map_width - w - padding)
                y = rng.randint(padding, map_height - h - padding)

                overlap = False
                for existing in rooms:
                    if (
                        x < existing.x + existing.width + 2
                        and x + w + 2 > existing.x
                        and y < existing.y + existing.height + 2
                        and y + h + 2 > existing.y
                    ):
                        overlap = True
                        break

                if not overlap:
                    room = DungeonRoom(
                        name=f"Room_{i+1}",
                        room_type=RoomType.COMBAT,
                        x=x, y=y, width=w, height=h,
                        difficulty_level=round(0.2 + (i / max(room_count - 1, 1)) * 0.8, 2),
                    )
                    rooms.append(room)
                    self._rooms[room.id] = room
                    self._total_rooms_created += 1
                    placed = True
                    break

            if not placed:
                room = DungeonRoom(
                    name=f"Room_{i+1}",
                    room_type=RoomType.COMBAT,
                    x=rng.randint(padding, map_width - min_size - padding),
                    y=rng.randint(padding, map_height - min_size - padding),
                    width=min_size, height=min_size,
                    difficulty_level=round(0.2 + (i / max(room_count - 1, 1)) * 0.8, 2),
                )
                rooms.append(room)
                self._rooms[room.id] = room
                self._total_rooms_created += 1

        return rooms

    def _connect_rooms_mspt(
        self, rng: random.Random, rooms: List[DungeonRoom]
    ) -> List[DungeonCorridor]:
        corridors = []
        if len(rooms) < 2:
            return corridors

        connected = {rooms[0].id}
        unconnected = {r.id for r in rooms[1:]}

        while unconnected:
            best_dist = float("inf")
            best_from = None
            best_to = None

            for from_id in connected:
                from_room = self._rooms[from_id]
                for to_id in unconnected:
                    to_room = self._rooms[to_id]
                    dist = abs(from_room.x - to_room.x) + abs(from_room.y - to_room.y)
                    if dist < best_dist:
                        best_dist = dist
                        best_from = from_id
                        best_to = to_id

            if best_from and best_to:
                from_room = self._rooms[best_from]
                to_room = self._rooms[best_to]

                direction = "horizontal" if abs(from_room.x - to_room.x) > abs(from_room.y - to_room.y) else "vertical"
                corridor = DungeonCorridor(
                    from_room_id=best_from,
                    to_room_id=best_to,
                    direction=direction,
                    length=int(best_dist),
                )
                corridors.append(corridor)

                from_room.connections.append(best_to)
                from_room.door_directions.append(direction)
                to_room.connections.append(best_from)
                to_room.door_directions.append(direction)

                connected.add(best_to)
                unconnected.discard(best_to)

        for corridor in corridors:
            self._corridors[corridor.id] = corridor

        if len(rooms) >= 3:
            extra_connections = max(1, len(rooms) // 5)
            for _ in range(extra_connections):
                a_idx = rng.randint(0, len(rooms) - 1)
                b_idx = rng.randint(0, len(rooms) - 1)
                if a_idx != b_idx:
                    a = rooms[a_idx]
                    b = rooms[b_idx]
                    if b.id not in a.connections:
                        direction = "horizontal" if rng.random() < 0.5 else "vertical"
                        corridor = DungeonCorridor(
                            from_room_id=a.id,
                            to_room_id=b.id,
                            direction=direction,
                            length=abs(a.x - b.x) + abs(a.y - b.y),
                            secret=rng.random() < 0.3,
                        )
                        corridors.append(corridor)
                        self._corridors[corridor.id] = corridor
                        a.connections.append(b.id)
                        b.connections.append(a.id)

        return corridors

    def _assign_room_types(
        self, rng: random.Random, rooms: List[DungeonRoom]
    ) -> None:
        if not rooms:
            return

        rooms[0].room_type = RoomType.SPAWN
        rooms[0].name = "Entrance"

        if len(rooms) >= 2:
            rooms[-1].room_type = RoomType.BOSS
            rooms[-1].name = "Boss Chamber"
            rooms[-1].difficulty_level = 1.0

        special_rooms = [RoomType.TREASURE, RoomType.PUZZLE, RoomType.REST, RoomType.SHOP, RoomType.SECRET]
        available = [r for r in rooms if r.room_type == RoomType.COMBAT]

        shop_placed = False
        for room_type in special_rooms:
            candidates = [r for r in available if r.room_type == RoomType.COMBAT]
            if candidates:
                chosen = rng.choice(candidates)
                chosen.room_type = room_type
                chosen.name = f"{room_type.value.title()} Room"
                if room_type == RoomType.SHOP:
                    shop_placed = True
                available = [r for r in available if r.id != chosen.id]
            if not candidates:
                break

        if not shop_placed and len(available) > 0:
            chosen = rng.choice(available)
            chosen.room_type = RoomType.SHOP
            chosen.name = "Shop"

        if len(available) > 0:
            chosen = rng.choice(available)
            chosen.room_type = RoomType.EXIT
            chosen.name = "Exit"

        lighting_options = ["torch", "glow_mushroom", "magical_crystal", "dim_sconce", "brazier"]
        for room in rooms:
            room.lighting = rng.choice(lighting_options)

    def _compute_max_depth(
        self, rooms: List[DungeonRoom], corridors: List[DungeonCorridor]
    ) -> int:
        if not rooms:
            return 0

        graph: Dict[str, List[str]] = {r.id: list(r.connections) for r in rooms}
        visited: set = set()
        max_depth = 0

        def dfs(node_id: str, depth: int):
            nonlocal max_depth
            visited.add(node_id)
            max_depth = max(max_depth, depth)
            for neighbor in graph.get(node_id, []):
                if neighbor not in visited:
                    dfs(neighbor, depth + 1)

        if rooms:
            dfs(rooms[0].id, 0)

        return max_depth

    def define_dungeon_theme(self, theme_name: str) -> DungeonTheme:
        template = _THEME_TEMPLATES.get(theme_name.lower(), _THEME_TEMPLATES["castle"])

        theme = DungeonTheme(
            name=theme_name,
            category=template["category"],
            primary_material=template["primary_material"],
            secondary_material=template["secondary_material"],
            color_scheme=template["color_scheme"],
            ambient_light_color=template["ambient_light_color"],
            ambient_sound=template["ambient_sound"],
            enemy_families=template["enemy_families"],
            prop_categories=template["prop_categories"],
            trap_themes=template["trap_themes"],
            treasure_themes=template["treasure_themes"],
        )

        self._themes[theme.id] = theme
        return theme

    def distribute_encounters(
        self,
        layout_id: str,
        theme_name: str = "castle",
    ) -> List[EncounterNode]:
        layout = self._layouts.get(layout_id)
        if not layout:
            raise ValueError(f"Layout '{layout_id}' not found")

        rng = random.Random(layout.seed)
        encounters = []

        enemy_pool = _ENEMY_POOLS.get(theme_name, _ENEMY_POOLS["castle"])

        for room_id in layout.rooms:
            room = self._rooms.get(room_id)
            if not room:
                continue

            if room.room_type == RoomType.SPAWN:
                enc_type = EncounterType.AMBIENT
                difficulty = 0.1
            elif room.room_type == RoomType.BOSS:
                enc_type = EncounterType.COMBAT_BOSS
                difficulty = 0.95
            elif room.room_type == RoomType.COMBAT:
                roll = rng.random()
                if roll < 0.5:
                    enc_type = EncounterType.COMBAT_MEDIUM
                elif roll < 0.75:
                    enc_type = EncounterType.COMBAT_EASY
                else:
                    enc_type = EncounterType.COMBAT_HARD
                difficulty = room.difficulty_level
            elif room.room_type == RoomType.PUZZLE:
                enc_type = EncounterType.PUZZLE
                difficulty = room.difficulty_level
            elif room.room_type == RoomType.TREASURE:
                enc_type = EncounterType.AMBIENT
                difficulty = 0.2
            else:
                enc_type = EncounterType.AMBIENT
                difficulty = 0.1

            enemy_count = 0
            enemy_types = []
            if enc_type.value.startswith("combat"):
                enemy_count = max(1, int(difficulty * 5 + rng.randint(-1, 2)))
                for _ in range(min(3, enemy_count)):
                    enemy_pick = rng.choices(
                        [e[0] for e in enemy_pool],
                        weights=[e[1] for e in enemy_pool],
                        k=1,
                    )[0]
                    enemy_types.append(enemy_pick)

            encounter = EncounterNode(
                room_id=room_id,
                encounter_type=enc_type,
                name=f"{room.name}_encounter",
                description=f"A {enc_type.value} encounter in {room.name}",
                difficulty=round(difficulty, 2),
                enemy_count=enemy_count,
                enemy_types=list(set(enemy_types)),
                puzzle_type="symbol_match" if enc_type == EncounterType.PUZZLE else None,
                trap_type="arrow_trap" if rng.random() < 0.2 else None,
            )
            encounters.append(encounter)
            self._encounters[encounter.id] = encounter
            self._total_encounters_placed += 1

        return encounters

    def place_treasures(
        self,
        layout_id: str,
        theme_name: str = "castle",
    ) -> List[TreasureNode]:
        layout = self._layouts.get(layout_id)
        if not layout:
            raise ValueError(f"Layout '{layout_id}' not found")

        rng = random.Random(layout.seed + 1000)
        treasures = []

        treasure_distribution = [
            (TreasureCategory.COMMON, 0.5),
            (TreasureCategory.UNCOMMON, 0.25),
            (TreasureCategory.RARE, 0.15),
            (TreasureCategory.LEGENDARY, 0.05),
            (TreasureCategory.LORE_ITEM, 0.05),
        ]

        theme_treasures = _THEME_TEMPLATES.get(theme_name, _THEME_TEMPLATES["castle"]).get("treasure_themes", [])

        for room_id in layout.rooms:
            room = self._rooms.get(room_id)
            if not room:
                continue

            if room.room_type in (RoomType.TREASURE, RoomType.BOSS, RoomType.SECRET):
                treasure_count = rng.randint(1, 4) if room.room_type == RoomType.TREASURE else rng.randint(1, 3)
            elif room.room_type == RoomType.COMBAT:
                treasure_count = rng.randint(0, 2)
            else:
                treasure_count = rng.randint(0, 1)

            for _ in range(treasure_count):
                category_roll = rng.random()
                cumulative = 0.0
                chosen_category = TreasureCategory.COMMON
                for cat, prob in treasure_distribution:
                    cumulative += prob
                    if category_roll <= cumulative:
                        chosen_category = cat
                        break

                if room.room_type == RoomType.BOSS:
                    chosen_category = TreasureCategory.RARE if rng.random() < 0.7 else TreasureCategory.LEGENDARY

                treasure_name = f"{chosen_category.value}_{rng.choice(theme_treasures) if theme_treasures else 'generic_loot'}"

                treasure = TreasureNode(
                    room_id=room_id,
                    category=chosen_category,
                    name=treasure_name,
                    description=f"A {chosen_category.value} treasure found in {room.name}",
                    value_score=round(
                        {TreasureCategory.COMMON: 0.2, TreasureCategory.UNCOMMON: 0.4,
                         TreasureCategory.RARE: 0.65, TreasureCategory.LEGENDARY: 0.9,
                         TreasureCategory.LORE_ITEM: 0.5}[chosen_category] + rng.uniform(-0.1, 0.1), 2
                    ),
                )
                treasures.append(treasure)
                self._treasures[treasure.id] = treasure

        key_room = None
        for room_id in layout.rooms:
            room = self._rooms.get(room_id)
            if room and room.room_type == RoomType.EXIT:
                key_room = room
                break

        if key_room and len(layout.rooms) >= 5:
            mid_idx = len(layout.rooms) // 3
            key_holder_room_id = layout.rooms[mid_idx]
            key_treasure = TreasureNode(
                room_id=key_holder_room_id,
                category=TreasureCategory.KEY_ITEM,
                name="dungeon_key",
                description=f"A key that unlocks the exit door",
                value_score=0.8,
                is_key_item=True,
                unlocks_room_id=key_room.id,
            )
            treasures.append(key_treasure)
            self._treasures[key_treasure.id] = key_treasure

        return treasures

    def compute_difficulty_curve(
        self,
        layout_id: str,
    ) -> Dict[str, Any]:
        layout = self._layouts.get(layout_id)
        if not layout:
            raise ValueError(f"Layout '{layout_id}' not found")

        difficulties = []
        room_names = []

        for room_id in layout.rooms:
            room = self._rooms.get(room_id)
            if room:
                difficulties.append(room.difficulty_level)
                room_names.append(room.name)

        if not difficulties:
            return {"difficulty_curve": [], "recommended_player_level": 1}

        curve = []
        for i, diff in enumerate(difficulties):
            curve.append({
                "room_index": i,
                "room_name": room_names[i],
                "difficulty": diff,
                "cumulative_difficulty": round(sum(difficulties[:i+1]) / max(len(difficulties), 1), 2),
            })

        avg_difficulty = sum(difficulties) / max(len(difficulties), 1)
        recommended_level = max(1, int(avg_difficulty * 10))

        return {
            "difficulty_curve": curve,
            "average_difficulty": round(avg_difficulty, 2),
            "peak_difficulty": round(max(difficulties), 2) if difficulties else 0,
            "recommended_player_level": recommended_level,
            "room_count": len(curve),
        }

    def get_layout(self, layout_id: str) -> Optional[DungeonLayout]:
        return self._layouts.get(layout_id)

    def get_room(self, room_id: str) -> Optional[DungeonRoom]:
        return self._rooms.get(room_id)

    def list_rooms_for_layout(self, layout_id: str) -> List[Dict[str, Any]]:
        layout = self._layouts.get(layout_id)
        if not layout:
            return []
        return [self._rooms[rid].to_dict() for rid in layout.rooms if rid in self._rooms]

    def list_encounters_for_layout(self, layout_id: str) -> List[Dict[str, Any]]:
        layout = self._layouts.get(layout_id)
        if not layout:
            return []
        result = []
        for enc in self._encounters.values():
            if enc.room_id in layout.rooms:
                result.append(enc.to_dict())
        return result

    def list_treasures_for_layout(self, layout_id: str) -> List[Dict[str, Any]]:
        layout = self._layouts.get(layout_id)
        if not layout:
            return []
        result = []
        for treas in self._treasures.values():
            if treas.room_id in layout.rooms:
                result.append(treas.to_dict())
        return result

    def list_layouts(self) -> List[Dict[str, Any]]:
        return [lyt.to_dict() for lyt in self._layouts.values()]

    def get_stats(self) -> Dict[str, Any]:
        return {
            "total_layouts_generated": self._total_layouts_generated,
            "total_rooms_created": self._total_rooms_created,
            "total_encounters_placed": self._total_encounters_placed,
            "total_treasures_placed": len(self._treasures),
            "total_themes": len(self._themes),
            "total_corridors": len(self._corridors),
            "available_theme_templates": len(_THEME_TEMPLATES),
            "rooms_by_type": {
                rt.value: sum(1 for r in self._rooms.values() if r.room_type == rt)
                for rt in RoomType
            },
            "encounters_by_type": {
                et.value: sum(1 for e in self._encounters.values() if e.encounter_type == et)
                for et in EncounterType
            },
        }


def get_procedural_dungeon_generator() -> EngineProceduralDungeon:
    return EngineProceduralDungeon()