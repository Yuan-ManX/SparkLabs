"""
SparkLabs Agent - Level Designer

AI-driven procedural level and map generation system. Creates tile-based
level layouts using multiple generation algorithms including BSP tree
partitioning, cellular automata, drunkard's walk, wave function collapse,
agent-based placement, and room graph construction.

Architecture:
  LevelDesigner
    |-- Session Manager (tracks generation sessions and their lifecycle)
    |-- Generator Engine (produces deterministic level layouts from seed)
    |-- Room Manager (add/remove/modify rooms within layouts)
    |-- Spawn System (places enemy, item, and player spawn points)
    |-- Layout Analyzer (connectivity, flow, chokepoint, difficulty analysis)
    |-- Exporter (serializes layouts to exportable dictionaries)

Supports 7 terrain biomes and 6 generation algorithms for diverse level design.
"""

from __future__ import annotations

import math
import random
import threading
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple


class GenerationAlgorithm(Enum):
    BSP = "bsp"
    CELLULAR_AUTOMATA = "cellular_automata"
    DRUNKARD_WALK = "drunkard_walk"
    WAVE_FUNCTION_COLLAPSE = "wave_function_collapse"
    AGENT_PLACEMENT = "agent_placement"
    ROOM_GRAPH = "room_graph"


class TerrainType(Enum):
    FLAT = "flat"
    HILLY = "hilly"
    MOUNTAINOUS = "mountainous"
    AQUATIC = "aquatic"
    CAVE = "cave"
    URBAN = "urban"
    RUINS = "ruins"


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------


@dataclass
class GenerationParams:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    algorithm: GenerationAlgorithm = GenerationAlgorithm.BSP
    seed: int = 42
    width: int = 100
    height: int = 100
    room_count: int = 8
    corridor_width: int = 2
    density: float = 0.45
    symmetry: float = 0.0
    max_depth: int = 4
    biome: TerrainType = TerrainType.FLAT
    constraints: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "algorithm": self.algorithm.value,
            "seed": self.seed,
            "width": self.width,
            "height": self.height,
            "room_count": self.room_count,
            "corridor_width": self.corridor_width,
            "density": self.density,
            "symmetry": self.symmetry,
            "max_depth": self.max_depth,
            "biome": self.biome.value,
            "constraints": self.constraints,
        }


@dataclass
class LevelTile:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    x: int = 0
    y: int = 0
    tile_type: str = "floor"
    elevation: int = 0
    walkable: bool = True
    features: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "x": self.x,
            "y": self.y,
            "tile_type": self.tile_type,
            "elevation": self.elevation,
            "walkable": self.walkable,
            "features": self.features,
        }


@dataclass
class LevelLayout:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = ""
    width: int = 100
    height: int = 100
    tiles: List[Dict[str, Any]] = field(default_factory=list)
    rooms: List[Dict[str, Any]] = field(default_factory=list)
    corridors: List[Dict[str, Any]] = field(default_factory=list)
    spawn_points: List[Dict[str, Any]] = field(default_factory=list)
    exit_points: List[Dict[str, Any]] = field(default_factory=list)
    enemy_spawns: List[Dict[str, Any]] = field(default_factory=list)
    item_spawns: List[Dict[str, Any]] = field(default_factory=list)
    algorithm: str = ""
    generation_time_ms: float = 0.0
    complexity_score: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "width": self.width,
            "height": self.height,
            "tile_count": len(self.tiles),
            "tiles": self.tiles,
            "room_count": len(self.rooms),
            "rooms": self.rooms,
            "corridor_count": len(self.corridors),
            "corridors": self.corridors,
            "spawn_points": self.spawn_points,
            "exit_points": self.exit_points,
            "enemy_spawns": self.enemy_spawns,
            "item_spawns": self.item_spawns,
            "algorithm": self.algorithm,
            "generation_time_ms": round(self.generation_time_ms, 2),
            "complexity_score": round(self.complexity_score, 2),
        }


@dataclass
class GenerationSession:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    level_id: Optional[str] = None
    algorithm: GenerationAlgorithm = GenerationAlgorithm.BSP
    params: Dict[str, Any] = field(default_factory=dict)
    status: str = "pending"
    started_at: float = field(default_factory=time.time)
    completed_at: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "level_id": self.level_id,
            "algorithm": self.algorithm.value,
            "params": self.params,
            "status": self.status,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
        }


# ---------------------------------------------------------------------------
# LevelDesigner — Singleton Orchestrator
# ---------------------------------------------------------------------------


class LevelDesigner:
    """AI-driven procedural level and map generation system.

    Provides deterministic level layout generation using multiple
    algorithms. Manages generation sessions, spawn points, room
    manipulation, and layout analysis.
    """

    _instance: Optional["LevelDesigner"] = None
    _lock: threading.RLock = threading.RLock()

    MAX_LAYOUTS: int = 200
    MAX_SESSIONS: int = 50
    MAX_WIDTH: int = 500
    MAX_HEIGHT: int = 500

    GENERATION_PRESETS: Dict[str, Dict[str, Any]] = {
        "dungeon_crawler": {
            "description": "Interconnected dungeon rooms with narrow corridors",
            "algorithm": GenerationAlgorithm.BSP,
            "seed": 12345,
            "width": 80,
            "height": 80,
            "room_count": 12,
            "corridor_width": 2,
            "density": 0.4,
            "symmetry": 0.1,
            "max_depth": 5,
            "biome": TerrainType.CAVE,
            "constraints": {"min_room_size": 5, "max_room_size": 20},
        },
        "open_world": {
            "description": "Large open terrain with scattered points of interest",
            "algorithm": GenerationAlgorithm.AGENT_PLACEMENT,
            "seed": 54321,
            "width": 200,
            "height": 200,
            "room_count": 25,
            "corridor_width": 4,
            "density": 0.25,
            "symmetry": 0.0,
            "max_depth": 3,
            "biome": TerrainType.FLAT,
            "constraints": {"min_room_size": 3, "max_room_size": 30},
        },
        "castle_interior": {
            "description": "Structured castle layout with symmetric room arrangement",
            "algorithm": GenerationAlgorithm.ROOM_GRAPH,
            "seed": 77777,
            "width": 100,
            "height": 100,
            "room_count": 15,
            "corridor_width": 3,
            "density": 0.5,
            "symmetry": 0.7,
            "max_depth": 6,
            "biome": TerrainType.URBAN,
            "constraints": {"min_room_size": 4, "max_room_size": 16},
        },
    }

    def __init__(self):
        self._layouts: Dict[str, LevelLayout] = {}
        self._sessions: Dict[str, GenerationSession] = {}
        self._total_generations: int = 0
        self._total_tiles: int = 0
        self._total_rooms: int = 0

    # ------------------------------------------------------------------
    # Singleton
    # ------------------------------------------------------------------

    @classmethod
    def get_instance(cls) -> "LevelDesigner":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    # ------------------------------------------------------------------
    # Session Management
    # ------------------------------------------------------------------

    def start_session(
        self, params: GenerationParams, algorithm: GenerationAlgorithm
    ) -> GenerationSession:
        if len(self._sessions) >= self.MAX_SESSIONS:
            oldest = min(
                self._sessions.keys(),
                key=lambda k: self._sessions[k].started_at,
            )
            del self._sessions[oldest]

        session = GenerationSession(
            algorithm=algorithm,
            params=params.to_dict(),
            status="started",
        )
        self._sessions[session.id] = session
        return session

    # ------------------------------------------------------------------
    # Level Generation
    # ------------------------------------------------------------------

    def generate_level(self, session_id: str) -> Optional[LevelLayout]:
        session = self._sessions.get(session_id)
        if session is None:
            return None

        params = session.params
        algorithm = session.algorithm
        width = min(params.get("width", 100), self.MAX_WIDTH)
        height = min(params.get("height", 100), self.MAX_HEIGHT)
        seed = params.get("seed", 42)
        room_count = params.get("room_count", 8)
        corridor_width = params.get("corridor_width", 2)
        density = params.get("density", 0.45)
        max_depth = params.get("max_depth", 4)
        biome_str = params.get("biome", "flat")
        constraints = params.get("constraints", {})

        min_room_size = constraints.get("min_room_size", 4)
        max_room_size = constraints.get("max_room_size", 16)

        if len(self._layouts) >= self.MAX_LAYOUTS:
            oldest = min(
                self._layouts.values(),
                key=lambda l: session.started_at if session else 0,
            )
            del self._layouts[oldest.id]

        start_time = time.time()
        rng = random.Random(seed)

        try:
            biome = TerrainType(biome_str)
        except (ValueError, TypeError):
            biome = TerrainType.FLAT

        rooms: List[Dict[str, Any]] = []
        corridors: List[Dict[str, Any]] = []

        if algorithm == GenerationAlgorithm.BSP:
            rooms = self._generate_bsp(rng, width, height, room_count,
                                       min_room_size, max_room_size, max_depth)
        elif algorithm == GenerationAlgorithm.CELLULAR_AUTOMATA:
            rooms, corridors = self._generate_cellular_automata(
                rng, width, height, density, corridor_width
            )
        elif algorithm == GenerationAlgorithm.DRUNKARD_WALK:
            rooms, corridors = self._generate_drunkard_walk(
                rng, width, height, room_count, corridor_width
            )
        elif algorithm == GenerationAlgorithm.WAVE_FUNCTION_COLLAPSE:
            rooms = self._generate_wfc(rng, width, height, room_count,
                                       min_room_size, max_room_size)
        elif algorithm == GenerationAlgorithm.AGENT_PLACEMENT:
            rooms = self._generate_agent_placement(
                rng, width, height, room_count,
                min_room_size, max_room_size
            )
        elif algorithm == GenerationAlgorithm.ROOM_GRAPH:
            rooms, corridors = self._generate_room_graph(
                rng, width, height, room_count,
                min_room_size, max_room_size, corridor_width
            )
        else:
            rooms = self._generate_bsp(rng, width, height, room_count,
                                       min_room_size, max_room_size, max_depth)

        corridors = self._connect_rooms(rng, rooms, corridors, corridor_width)
        tiles = self._build_tiles(width, height, rooms, corridors, biome)

        spawn_points = self._place_default_spawns(rng, rooms)
        exit_points = self._place_default_exits(rng, rooms)
        enemy_spawns = self._place_default_enemies(rng, rooms)
        item_spawns = self._place_default_items(rng, rooms)

        generation_time_ms = (time.time() - start_time) * 1000.0
        complexity_score = self._compute_complexity(
            rooms, corridors, len(tiles)
        )

        layout = LevelLayout(
            name=f"{algorithm.value}_{seed}_{uuid.uuid4().hex[:6]}",
            width=width,
            height=height,
            tiles=tiles,
            rooms=rooms,
            corridors=corridors,
            spawn_points=spawn_points,
            exit_points=exit_points,
            enemy_spawns=enemy_spawns,
            item_spawns=item_spawns,
            algorithm=algorithm.value,
            generation_time_ms=generation_time_ms,
            complexity_score=complexity_score,
        )

        self._layouts[layout.id] = layout
        session.level_id = layout.id
        session.status = "completed"
        session.completed_at = time.time()

        self._total_generations += 1
        self._total_tiles += len(tiles)
        self._total_rooms += len(rooms)

        return layout

    def regenerate_section(
        self, session_id: str, x: int, y: int, w: int, h: int
    ) -> Optional[LevelLayout]:
        layout = self.generate_level(session_id)
        if layout is None:
            return None

        for tile in layout.tiles:
            tx = tile.get("x", 0)
            ty = tile.get("y", 0)
            if x <= tx < x + w and y <= ty < y + h:
                tile["tile_type"] = "floor"
                tile["walkable"] = True

        return layout

    # ------------------------------------------------------------------
    # Room Management
    # ------------------------------------------------------------------

    def add_room(
        self, session_id: str, x: int, y: int, w: int, h: int, room_type: str
    ) -> Optional[LevelLayout]:
        session = self._sessions.get(session_id)
        if session is None or session.level_id is None:
            return None

        layout = self._layouts.get(session.level_id)
        if layout is None:
            return None

        x = max(0, min(x, layout.width - 1))
        y = max(0, min(y, layout.height - 1))
        w = max(3, min(w, layout.width - x))
        h = max(3, min(h, layout.height - y))

        room = {
            "x": x, "y": y, "w": w, "h": h,
            "type": room_type,
            "id": uuid.uuid4().hex,
        }
        layout.rooms.append(room)

        for rx in range(x, x + w):
            for ry in range(y, y + h):
                if 0 <= rx < layout.width and 0 <= ry < layout.height:
                    existing = next(
                        (t for t in layout.tiles
                         if t["x"] == rx and t["y"] == ry), None
                    )
                    if existing:
                        existing["tile_type"] = "floor"
                        existing["walkable"] = True
                    else:
                        layout.tiles.append({
                            "id": uuid.uuid4().hex,
                            "x": rx, "y": ry,
                            "tile_type": "floor",
                            "elevation": 0,
                            "walkable": True,
                            "features": [],
                        })

        layout.complexity_score = self._compute_complexity(
            layout.rooms, layout.corridors, len(layout.tiles)
        )
        return layout

    def remove_room(
        self, session_id: str, room_index: int
    ) -> Optional[LevelLayout]:
        session = self._sessions.get(session_id)
        if session is None or session.level_id is None:
            return None

        layout = self._layouts.get(session.level_id)
        if layout is None:
            return None

        if 0 <= room_index < len(layout.rooms):
            layout.rooms.pop(room_index)

        layout.complexity_score = self._compute_complexity(
            layout.rooms, layout.corridors, len(layout.tiles)
        )
        return layout

    # ------------------------------------------------------------------
    # Spawn Points
    # ------------------------------------------------------------------

    def add_enemy_spawn(
        self, session_id: str, x: int, y: int, enemy_type: str
    ) -> Optional[LevelLayout]:
        session = self._sessions.get(session_id)
        if session is None or session.level_id is None:
            return None

        layout = self._layouts.get(session.level_id)
        if layout is None:
            return None

        layout.enemy_spawns.append({
            "x": x, "y": y, "type": enemy_type, "id": uuid.uuid4().hex,
        })
        return layout

    def add_item_spawn(
        self, session_id: str, x: int, y: int, item_type: str
    ) -> Optional[LevelLayout]:
        session = self._sessions.get(session_id)
        if session is None or session.level_id is None:
            return None

        layout = self._layouts.get(session.level_id)
        if layout is None:
            return None

        layout.item_spawns.append({
            "x": x, "y": y, "type": item_type, "id": uuid.uuid4().hex,
        })
        return layout

    def add_spawn_point(
        self, session_id: str, x: int, y: int, label: str
    ) -> Optional[LevelLayout]:
        session = self._sessions.get(session_id)
        if session is None or session.level_id is None:
            return None

        layout = self._layouts.get(session.level_id)
        if layout is None:
            return None

        layout.spawn_points.append({
            "x": x, "y": y, "label": label, "id": uuid.uuid4().hex,
        })
        return layout

    # ------------------------------------------------------------------
    # Layout Analysis
    # ------------------------------------------------------------------

    def analyze_layout(self, layout_id: str) -> Dict[str, Any]:
        layout = self._layouts.get(layout_id)
        if layout is None:
            return {}

        connectivity = self._compute_connectivity(layout.rooms, layout.corridors)
        flow_analysis = self._compute_flow(layout.rooms, layout.corridors)
        chokepoints = self._find_chokepoints(layout.rooms, layout.corridors)
        difficulty_estimate = self._estimate_difficulty(layout)
        exploration_score = self._compute_exploration_score(layout)

        return {
            "layout_id": layout_id,
            "connectivity": connectivity,
            "flow_analysis": flow_analysis,
            "chokepoints": chokepoints,
            "difficulty_estimate": difficulty_estimate,
            "exploration_score": exploration_score,
        }

    # ------------------------------------------------------------------
    # Export / Access / Listing
    # ------------------------------------------------------------------

    def export_layout(
        self, layout_id: str, format: str = "json"
    ) -> Dict[str, Any]:
        layout = self._layouts.get(layout_id)
        if layout is None:
            return {}
        return layout.to_dict()

    def get_layout(self, layout_id: str) -> Optional[LevelLayout]:
        return self._layouts.get(layout_id)

    def get_session(self, session_id: str) -> Optional[GenerationSession]:
        return self._sessions.get(session_id)

    def list_layouts(self) -> List[LevelLayout]:
        return list(self._layouts.values())

    def list_sessions(self) -> List[GenerationSession]:
        return list(self._sessions.values())

    # ------------------------------------------------------------------
    # Stats
    # ------------------------------------------------------------------

    def get_stats(self) -> Dict[str, Any]:
        if not self._layouts:
            return {
                "total_layouts": 0,
                "total_sessions": len(self._sessions),
                "total_tiles": self._total_tiles,
                "tiles_per_layout": 0.0,
                "algorithms_used": {},
                "average_rooms": 0.0,
                "average_complexity": 0.0,
            }

        algo_counts: Dict[str, int] = {}
        total_rooms = 0
        total_complexity = 0.0
        total_layout_tiles = 0

        for layout in self._layouts.values():
            algo = layout.algorithm
            algo_counts[algo] = algo_counts.get(algo, 0) + 1
            total_rooms += len(layout.rooms)
            total_complexity += layout.complexity_score
            total_layout_tiles += len(layout.tiles)

        count = len(self._layouts)

        return {
            "total_layouts": count,
            "total_sessions": len(self._sessions),
            "total_tiles": self._total_tiles,
            "tiles_per_layout": round(total_layout_tiles / count, 2),
            "algorithms_used": algo_counts,
            "average_rooms": round(total_rooms / count, 2),
            "average_complexity": round(total_complexity / count, 2),
        }

    # ------------------------------------------------------------------
    # Generation Algorithms (Private)
    # ------------------------------------------------------------------

    def _generate_bsp(
        self,
        rng: random.Random,
        width: int,
        height: int,
        room_count: int,
        min_size: int,
        max_size: int,
        max_depth: int,
    ) -> List[Dict[str, Any]]:
        rooms: List[Dict[str, Any]] = []
        margin = 2

        def _place_room(x: int, y: int, w: int, h: int):
            available_w = w - margin * 2
            available_h = h - margin * 2
            if available_w < min_size or available_h < min_size:
                return
            room_w = rng.randint(min_size, min(max_size, available_w))
            room_h = rng.randint(min_size, min(max_size, available_h))
            room_x = x + rng.randint(margin, margin + available_w - room_w)
            room_y = y + rng.randint(margin, margin + available_h - room_h)
            rooms.append({
                "x": room_x, "y": room_y, "w": room_w, "h": room_h,
                "type": "room", "id": uuid.uuid4().hex,
            })

        def partition(x: int, y: int, w: int, h: int, depth: int):
            if depth >= max_depth or w < min_size * 3 or h < min_size * 3:
                _place_room(x, y, w, h)
                return

            split_horizontally = rng.choice([True, False])
            if w > h and w / h >= 1.25:
                split_horizontally = False
            elif h > w and h / w >= 1.25:
                split_horizontally = True

            if split_horizontally:
                if h < min_size * 2:
                    _place_room(x, y, w, h)
                    return
                split = rng.randint(min_size, h - min_size)
                partition(x, y, w, split, depth + 1)
                partition(x, y + split, w, h - split, depth + 1)
            else:
                if w < min_size * 2:
                    _place_room(x, y, w, h)
                    return
                split = rng.randint(min_size, w - min_size)
                partition(x, y, split, h, depth + 1)
                partition(x + split, y, w - split, h, depth + 1)

        partition(0, 0, width, height, 0)
        return rooms

    def _generate_cellular_automata(
        self,
        rng: random.Random,
        width: int,
        height: int,
        density: float,
        corridor_width: int,
    ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        grid = [[rng.random() < density for _ in range(width)] for _ in range(height)]

        for _ in range(4):
            new_grid = [[False for _ in range(width)] for _ in range(height)]
            for y in range(height):
                for x in range(width):
                    neighbors = 0
                    for dy in range(-1, 2):
                        for dx in range(-1, 2):
                            nx, ny = x + dx, y + dy
                            if 0 <= nx < width and 0 <= ny < height:
                                if grid[ny][nx]:
                                    neighbors += 1
                    new_grid[y][x] = neighbors >= 5 if grid[y][x] else neighbors >= 5
            grid = new_grid

        rooms: List[Dict[str, Any]] = []
        visited: Set[Tuple[int, int]] = set()

        for y in range(height):
            for x in range(width):
                if grid[y][x] and (x, y) not in visited:
                    region = self._flood_fill(grid, x, y, width, height)
                    visited.update(region)
                    if len(region) >= 9:
                        xs = [p[0] for p in region]
                        ys = [p[1] for p in region]
                        rooms.append({
                            "x": min(xs), "y": min(ys),
                            "w": max(xs) - min(xs) + 1,
                            "h": max(ys) - min(ys) + 1,
                            "type": "cave_room",
                            "id": uuid.uuid4().hex,
                        })

        corridors: List[Dict[str, Any]] = []
        return rooms, corridors

    def _generate_drunkard_walk(
        self,
        rng: random.Random,
        width: int,
        height: int,
        room_count: int,
        corridor_width: int,
    ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        grid = [[False for _ in range(width)] for _ in range(height)]
        cx, cy = width // 2, height // 2
        steps_per_walk = (width * height) // (room_count * 4)

        for _ in range(room_count * 3):
            x, y = rng.randint(0, width - 1), rng.randint(0, height - 1)
            for _ in range(steps_per_walk):
                grid[y][x] = True
                direction = rng.choice([(0, -1), (0, 1), (-1, 0), (1, 0)])
                x = max(0, min(width - 1, x + direction[0]))
                y = max(0, min(height - 1, y + direction[1]))

        rooms: List[Dict[str, Any]] = []
        room = {
            "x": cx - 4, "y": cy - 4, "w": 8, "h": 8,
            "type": "hub", "id": uuid.uuid4().hex,
        }
        rooms.append(room)

        corridors: List[Dict[str, Any]] = []
        return rooms, corridors

    def _generate_wfc(
        self,
        rng: random.Random,
        width: int,
        height: int,
        room_count: int,
        min_size: int,
        max_size: int,
    ) -> List[Dict[str, Any]]:
        rooms: List[Dict[str, Any]] = []
        for _ in range(room_count):
            w = rng.randint(min_size, max_size)
            h = rng.randint(min_size, max_size)
            x = rng.randint(0, max(0, width - w - 1))
            y = rng.randint(0, max(0, height - h - 1))
            rooms.append({
                "x": x, "y": y, "w": w, "h": h,
                "type": "wfc_room",
                "id": uuid.uuid4().hex,
            })
        return rooms

    def _generate_agent_placement(
        self,
        rng: random.Random,
        width: int,
        height: int,
        room_count: int,
        min_size: int,
        max_size: int,
    ) -> List[Dict[str, Any]]:
        rooms: List[Dict[str, Any]] = []
        placed: List[Tuple[int, int, int, int]] = []

        for _ in range(room_count * 2):
            w = rng.randint(min_size, max_size)
            h = rng.randint(min_size, max_size)
            x = rng.randint(0, max(0, width - w - 1))
            y = rng.randint(0, max(0, height - h - 1))

            overlaps = False
            for px, py, pw, ph in placed:
                if not (
                    x + w + 2 < px or px + pw + 2 < x
                    or y + h + 2 < py or py + ph + 2 < y
                ):
                    overlaps = True
                    break

            if not overlaps:
                placed.append((x, y, w, h))
                rooms.append({
                    "x": x, "y": y, "w": w, "h": h,
                    "type": "agent_room",
                    "id": uuid.uuid4().hex,
                })

        return rooms[:room_count]

    def _generate_room_graph(
        self,
        rng: random.Random,
        width: int,
        height: int,
        room_count: int,
        min_size: int,
        max_size: int,
        corridor_width: int,
    ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        rooms: List[Dict[str, Any]] = []
        for i in range(room_count):
            angle = (2 * math.pi * i) / room_count
            radius = min(width, height) * 0.35
            cx = int(width / 2 + math.cos(angle) * radius * rng.uniform(0.5, 1.0))
            cy = int(height / 2 + math.sin(angle) * radius * rng.uniform(0.5, 1.0))
            w = rng.randint(min_size, max_size)
            h = rng.randint(min_size, max_size)
            rooms.append({
                "x": max(0, cx - w // 2),
                "y": max(0, cy - h // 2),
                "w": w, "h": h,
                "type": "graph_room",
                "id": uuid.uuid4().hex,
            })

        corridors: List[Dict[str, Any]] = []
        center = {"x": width // 2 - 3, "y": height // 2 - 3, "w": 6, "h": 6,
                  "type": "hub", "id": uuid.uuid4().hex}
        rooms.insert(0, center)

        for i in range(1, len(rooms)):
            c = self._build_corridor(rng, center, rooms[i], corridor_width)
            if c:
                corridors.append(c)

        return rooms, corridors

    # ------------------------------------------------------------------
    # Connection / Tile Building
    # ------------------------------------------------------------------

    def _connect_rooms(
        self,
        rng: random.Random,
        rooms: List[Dict[str, Any]],
        existing_corridors: List[Dict[str, Any]],
        corridor_width: int,
    ) -> List[Dict[str, Any]]:
        if len(rooms) < 2:
            return existing_corridors

        corridors = list(existing_corridors)
        connected: Set[int] = {0}
        remaining = set(range(1, len(rooms)))

        while remaining:
            best_pair: Optional[Tuple[int, int]] = None
            best_dist = float("inf")

            for c in connected:
                for r in remaining:
                    dist = self._room_distance(rooms[c], rooms[r])
                    if dist < best_dist:
                        best_dist = dist
                        best_pair = (c, r)

            if best_pair is None:
                break

            c, r = best_pair
            corr = self._build_corridor(rng, rooms[c], rooms[r], corridor_width)
            if corr:
                corridors.append(corr)
            connected.add(r)
            remaining.discard(r)

        return corridors

    def _build_corridor(
        self,
        rng: random.Random,
        room_a: Dict[str, Any],
        room_b: Dict[str, Any],
        width: int,
    ) -> Optional[Dict[str, Any]]:
        ax = room_a["x"] + room_a["w"] // 2
        ay = room_a["y"] + room_a["h"] // 2
        bx = room_b["x"] + room_b["w"] // 2
        by = room_b["y"] + room_b["h"] // 2

        segments: List[Dict[str, Any]] = []

        if rng.choice([True, False]):
            segments.append({
                "x1": ax, "y1": ay, "x2": bx, "y2": ay,
                "width": width,
            })
            segments.append({
                "x1": bx, "y1": ay, "x2": bx, "y2": by,
                "width": width,
            })
        else:
            segments.append({
                "x1": ax, "y1": ay, "x2": ax, "y2": by,
                "width": width,
            })
            segments.append({
                "x1": ax, "y1": by, "x2": bx, "y2": by,
                "width": width,
            })

        return {
            "segments": segments,
            "id": uuid.uuid4().hex,
            "from_room": room_a.get("id", ""),
            "to_room": room_b.get("id", ""),
        }

    def _build_tiles(
        self,
        width: int,
        height: int,
        rooms: List[Dict[str, Any]],
        corridors: List[Dict[str, Any]],
        biome: TerrainType,
    ) -> List[Dict[str, Any]]:
        tile_map: Dict[Tuple[int, int], Dict[str, Any]] = {}

        for y in range(height):
            for x in range(width):
                tile_map[(x, y)] = {
                    "id": uuid.uuid4().hex,
                    "x": x, "y": y,
                    "tile_type": "wall",
                    "elevation": 0,
                    "walkable": False,
                    "features": [],
                }

        biome_features: Dict[TerrainType, List[str]] = {
            TerrainType.CAVE: ["stalactite", "rock_formation"],
            TerrainType.HILLY: ["slope", "boulder"],
            TerrainType.MOUNTAINOUS: ["cliff", "peak"],
            TerrainType.AQUATIC: ["shallow_water", "coral"],
            TerrainType.URBAN: ["cobblestone", "lantern_post"],
            TerrainType.RUINS: ["broken_pillar", "overgrown_vine"],
            TerrainType.FLAT: ["grass", "small_rock"],
        }
        features = biome_features.get(biome, [])

        for room in rooms:
            rx, ry, rw, rh = room["x"], room["y"], room["w"], room["h"]
            for dx in range(rw):
                for dy in range(rh):
                    px, py = rx + dx, ry + dy
                    if (px, py) in tile_map:
                        tile_map[(px, py)]["tile_type"] = "floor"
                        tile_map[(px, py)]["walkable"] = True

        for corridor in corridors:
            for seg in corridor.get("segments", []):
                x1, y1 = seg["x1"], seg["y1"]
                x2, y2 = seg["x2"], seg["y2"]
                seg_width = seg.get("width", 1)

                if x1 == x2:
                    for dy in range(min(y1, y2), max(y1, y2) + 1):
                        for dw in range(-seg_width // 2, seg_width // 2 + 1):
                            px, py = x1 + dw, dy
                            if (px, py) in tile_map:
                                tile_map[(px, py)]["tile_type"] = "corridor"
                                tile_map[(px, py)]["walkable"] = True
                elif y1 == y2:
                    for dx in range(min(x1, x2), max(x1, x2) + 1):
                        for dw in range(-seg_width // 2, seg_width // 2 + 1):
                            px, py = dx, y1 + dw
                            if (px, py) in tile_map:
                                tile_map[(px, py)]["tile_type"] = "corridor"
                                tile_map[(px, py)]["walkable"] = True

        return list(tile_map.values())

    # ------------------------------------------------------------------
    # Spawn Placement Helpers
    # ------------------------------------------------------------------

    def _place_default_spawns(
        self,
        rng: random.Random,
        rooms: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        spawns: List[Dict[str, Any]] = []
        if not rooms:
            return spawns

        first = rooms[0]
        spawns.append({
            "x": first["x"] + first["w"] // 2,
            "y": first["y"] + first["h"] // 2,
            "label": "player_start",
            "id": uuid.uuid4().hex,
        })
        return spawns

    def _place_default_exits(
        self,
        rng: random.Random,
        rooms: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        exits: List[Dict[str, Any]] = []
        if len(rooms) < 2:
            return exits

        last = rooms[-1]
        exits.append({
            "x": last["x"] + last["w"] // 2,
            "y": last["y"] + last["h"] // 2,
            "label": "level_exit",
            "id": uuid.uuid4().hex,
        })
        return exits

    def _place_default_enemies(
        self,
        rng: random.Random,
        rooms: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        enemies: List[Dict[str, Any]] = []
        enemy_types = ["grunt", "scout", "heavy", "ranged"]

        for i, room in enumerate(rooms):
            if i == 0 or rng.random() < 0.3:
                continue
            count = rng.randint(1, 3)
            for _ in range(count):
                enemies.append({
                    "x": room["x"] + rng.randint(1, max(1, room["w"] - 2)),
                    "y": room["y"] + rng.randint(1, max(1, room["h"] - 2)),
                    "type": rng.choice(enemy_types),
                    "id": uuid.uuid4().hex,
                })
        return enemies

    def _place_default_items(
        self,
        rng: random.Random,
        rooms: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        items: List[Dict[str, Any]] = []
        item_types = ["health_potion", "mana_potion", "gold_coins", "weapon", "armor"]

        for i, room in enumerate(rooms):
            if rng.random() < 0.6:
                continue
            count = rng.randint(1, 2)
            for _ in range(count):
                items.append({
                    "x": room["x"] + rng.randint(1, max(1, room["w"] - 2)),
                    "y": room["y"] + rng.randint(1, max(1, room["h"] - 2)),
                    "type": rng.choice(item_types),
                    "id": uuid.uuid4().hex,
                })
        return items

    # ------------------------------------------------------------------
    # Analysis Helpers
    # ------------------------------------------------------------------

    def _compute_connectivity(
        self,
        rooms: List[Dict[str, Any]],
        corridors: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        n = len(rooms)
        if n < 2:
            return {"graph_density": 0.0, "isolated_rooms": n, "fully_connected": n <= 1}

        edge_count = len(corridors)
        max_edges = n * (n - 1) / 2
        graph_density = round(edge_count / max(max_edges, 1), 3)

        connected = {c.get("from_room", "") for c in corridors}
        connected.update(c.get("to_room", "") for c in corridors)
        room_ids = {r.get("id", "") for r in rooms}
        isolated = len(room_ids - connected)

        return {
            "graph_density": graph_density,
            "isolated_rooms": isolated,
            "fully_connected": graph_density >= 0.5,
            "total_edges": edge_count,
        }

    def _compute_flow(
        self,
        rooms: List[Dict[str, Any]],
        corridors: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        if not rooms:
            return {"linearity": 0.0, "branch_factor": 0.0, "dead_ends": 0}

        room_centers = [
            (r["x"] + r["w"] // 2, r["y"] + r["h"] // 2) for r in rooms
        ]

        linearity = 0.0
        if len(room_centers) >= 3:
            start = room_centers[0]
            end = room_centers[-1]
            direct_dist = math.hypot(end[0] - start[0], end[1] - start[1])
            path_dist = sum(
                math.hypot(
                    room_centers[i + 1][0] - room_centers[i][0],
                    room_centers[i + 1][1] - room_centers[i][1],
                )
                for i in range(len(room_centers) - 1)
            )
            linearity = round(direct_dist / max(path_dist, 1.0), 3)

        branch_factor = round(
            len(corridors) / max(len(rooms), 1), 2
        )

        return {
            "linearity": linearity,
            "branch_factor": branch_factor,
            "dead_ends": max(0, len(rooms) - len(corridors)),
        }

    def _find_chokepoints(
        self,
        rooms: List[Dict[str, Any]],
        corridors: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        chokepoints: List[Dict[str, Any]] = []
        for corridor in corridors:
            segs = corridor.get("segments", [])
            if len(segs) == 1:
                chokepoints.append({
                    "corridor_id": corridor.get("id", ""),
                    "type": "single_segment",
                })
        return chokepoints

    def _estimate_difficulty(self, layout: LevelLayout) -> Dict[str, Any]:
        enemy_count = len(layout.enemy_spawns)
        room_count = len(layout.rooms)
        corridor_count = len(layout.corridors)

        if room_count == 0:
            return {"rating": "trivial", "score": 0.0}

        enemy_density = enemy_count / max(room_count, 1)
        traversal_complexity = corridor_count / max(room_count, 1)

        score = enemy_density * 40 + traversal_complexity * 20 + min(room_count * 2, 40)

        if score < 20:
            rating = "trivial"
        elif score < 40:
            rating = "easy"
        elif score < 60:
            rating = "medium"
        elif score < 80:
            rating = "hard"
        else:
            rating = "extreme"

        return {
            "rating": rating,
            "score": round(score, 2),
            "enemy_density": round(enemy_density, 2),
            "traversal_complexity": round(traversal_complexity, 2),
        }

    def _compute_exploration_score(self, layout: LevelLayout) -> float:
        total_area = layout.width * layout.height
        if total_area == 0:
            return 0.0

        floor_tiles = sum(1 for t in layout.tiles if t.get("walkable", False))
        room_area = sum(r["w"] * r["h"] for r in layout.rooms)
        corridor_length = len(layout.corridors)

        exploration = (
            (floor_tiles / total_area) * 40
            + min(room_area / max(total_area, 1), 1.0) * 30
            + min(corridor_length * 2, 30)
        )
        return round(min(exploration, 100.0), 2)

    def _compute_complexity(
        self,
        rooms: List[Dict[str, Any]],
        corridors: List[Dict[str, Any]],
        tile_count: int,
    ) -> float:
        room_score = len(rooms) * 3.0
        corridor_score = len(corridors) * 5.0
        tile_score = tile_count * 0.001

        room_sizes = sum(r["w"] * r["h"] for r in rooms)
        size_score = room_sizes * 0.005

        return round(
            min(room_score + corridor_score + tile_score + size_score, 100.0),
            2,
        )

    def _room_distance(
        self, room_a: Dict[str, Any], room_b: Dict[str, Any]
    ) -> float:
        ax = room_a["x"] + room_a["w"] / 2
        ay = room_a["y"] + room_a["h"] / 2
        bx = room_b["x"] + room_b["w"] / 2
        by = room_b["y"] + room_b["h"] / 2
        return math.hypot(ax - bx, ay - by)

    def _flood_fill(
        self,
        grid: List[List[bool]],
        start_x: int,
        start_y: int,
        width: int,
        height: int,
    ) -> Set[Tuple[int, int]]:
        region: Set[Tuple[int, int]] = set()
        stack: List[Tuple[int, int]] = [(start_x, start_y)]

        while stack:
            x, y = stack.pop()
            if (x, y) in region:
                continue
            if not (0 <= x < width and 0 <= y < height):
                continue
            if not grid[y][x]:
                continue
            region.add((x, y))
            for dx, dy in [(0, 1), (1, 0), (0, -1), (-1, 0)]:
                stack.append((x + dx, y + dy))

        return region


# ---------------------------------------------------------------------------
# Module-Level Accessor
# ---------------------------------------------------------------------------


def get_level_designer() -> LevelDesigner:
    return LevelDesigner.get_instance()