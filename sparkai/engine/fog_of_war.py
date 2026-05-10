"""
SparkLabs Engine - Fog of War System

Grid-based visibility system for strategy and RPG game maps.
Manages exploration state, unit-based vision reveal, persistent
fog memory, and multi-team visibility layers.

Architecture:
  FogOfWarSystem
    |-- VisibilityGrid (per-team explored/visible state)
    |-- VisionSource (unit-based radius reveal calculation)
    |-- FogMemory (persistent fog for previously explored areas)
    |-- FogRenderer (tile-based fog mesh generation)
    |-- VisibilityQueries (LOS and range checks)

Grid States per Tile:
  - HIDDEN: never seen — fully obscured
  - EXPLORED: previously seen but not currently visible — dimmed
  - VISIBLE: currently within a vision source radius — fully lit
"""

from __future__ import annotations

import math
import time
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Dict, List, Optional, Set, Tuple


class TileVisibility(Enum):
    HIDDEN = 0
    EXPLORED = 1
    VISIBLE = 2


class FogShape(Enum):
    CIRCLE = "circle"
    CONE = "cone"
    SQUARE = "square"


@dataclass
class VisionSource:
    id: str = ""
    team: int = 0
    x: float = 0.0
    y: float = 0.0
    radius: float = 8.0
    shape: FogShape = FogShape.CIRCLE
    cone_angle: float = 90.0
    cone_direction: float = 0.0
    enabled: bool = True
    priority: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "team": self.team,
            "x": round(self.x, 2),
            "y": round(self.y, 2),
            "radius": round(self.radius, 2),
            "shape": self.shape.value,
            "enabled": self.enabled,
            "priority": self.priority,
        }


@dataclass
class FogCell:
    visibility: TileVisibility = TileVisibility.HIDDEN
    revealed_by: Optional[str] = None
    last_seen: float = 0.0


class FogOfWarSystem:
    """
    Grid-based fog of war and visibility system.

    Maintains per-team visibility grids with vision sources
    that reveal tiles. Supports persistent fog memory so
    previously explored tiles remain dimly visible.

    Usage:
        fog = FogOfWarSystem(width=64, height=64, tile_size=32)
        fog.set_team(0)
        src = fog.add_vision_source("player", 0, 320.0, 240.0, 8.0)
        fog.update()
        visible = fog.is_visible(10, 8)
        all_tiles = fog.get_grid_state()
    """

    _instance: Optional["FogOfWarSystem"] = None

    def __init__(
        self,
        width: int = 64,
        height: int = 64,
        tile_size: float = 32.0,
        max_teams: int = 4,
    ):
        self._width = max(1, width)
        self._height = max(1, height)
        self._tile_size = max(1.0, tile_size)
        self._max_teams = max(1, max_teams)

        self._grids: Dict[int, List[List[FogCell]]] = {}
        for team in range(self._max_teams):
            self._grids[team] = [
                [FogCell() for _ in range(self._width)]
                for _ in range(self._height)
            ]

        self._sources: List[VisionSource] = []
        self._active_team: int = 0
        self._update_count: int = 0
        self._global_reveal: bool = False
        self._dirty: bool = True

    @classmethod
    def get_instance(
        cls,
        width: int = 64,
        height: int = 64,
        tile_size: float = 32.0,
        max_teams: int = 4,
    ) -> "FogOfWarSystem":
        if cls._instance is None:
            cls._instance = cls(
                width=width,
                height=height,
                tile_size=tile_size,
                max_teams=max_teams,
            )
        return cls._instance

    def resize(self, width: int, height: int) -> None:
        self._width = max(1, width)
        self._height = max(1, height)
        for team in range(self._max_teams):
            new_grid = [
                [FogCell() for _ in range(self._width)]
                for _ in range(self._height)
            ]
            old_grid = self._grids.get(team, [])
            for y in range(min(height, len(old_grid))):
                for x in range(min(width, len(old_grid[y]) if y < len(old_grid) else 0)):
                    new_grid[y][x] = old_grid[y][x]
            self._grids[team] = new_grid
        self._dirty = True

    def set_team(self, team: int) -> None:
        self._active_team = max(0, min(self._max_teams - 1, team))

    def get_team(self) -> int:
        return self._active_team

    def set_global_reveal(self, reveal: bool) -> None:
        self._global_reveal = reveal
        if reveal:
            for team in range(self._max_teams):
                grid = self._grids[team]
                for y in range(self._height):
                    for x in range(self._width):
                        grid[y][x].visibility = TileVisibility.VISIBLE
                        grid[y][x].last_seen = time.time()

    def add_vision_source(
        self,
        source_id: str,
        team: int,
        x: float,
        y: float,
        radius: float = 8.0,
        shape: FogShape = FogShape.CIRCLE,
        cone_angle: float = 90.0,
        cone_direction: float = 0.0,
    ) -> VisionSource:
        source = VisionSource(
            id=source_id,
            team=max(0, min(self._max_teams - 1, team)),
            x=x, y=y,
            radius=radius,
            shape=shape,
            cone_angle=cone_angle,
            cone_direction=cone_direction,
        )
        self._sources.append(source)
        self._dirty = True
        return source

    def remove_vision_source(self, source_id: str) -> bool:
        for i, src in enumerate(self._sources):
            if src.id == source_id:
                self._sources.pop(i)
                self._dirty = True
                return True
        return False

    def update_vision_source(self, source_id: str, x: float, y: float) -> bool:
        for src in self._sources:
            if src.id == source_id:
                src.x = x
                src.y = y
                self._dirty = True
                return True
        return False

    def set_source_enabled(self, source_id: str, enabled: bool) -> bool:
        for src in self._sources:
            if src.id == source_id:
                src.enabled = enabled
                self._dirty = True
                return True
        return False

    def update(self) -> None:
        self._update_count += 1
        if self._global_reveal:
            return

        now = time.time()

        for team in range(self._max_teams):
            grid = self._grids[team]

            for y in range(self._height):
                for x in range(self._width):
                    cell = grid[y][x]
                    if cell.visibility == TileVisibility.VISIBLE:
                        cell.visibility = TileVisibility.EXPLORED

            team_sources = sorted(
                [s for s in self._sources if s.team == team and s.enabled],
                key=lambda s: -s.priority,
            )

            for source in team_sources:
                center_tile_x = source.x / self._tile_size
                center_tile_y = source.y / self._tile_size

                radius_tiles = int(math.ceil(source.radius))

                for dy in range(-radius_tiles, radius_tiles + 1):
                    for dx in range(-radius_tiles, radius_tiles + 1):
                        tx = int(center_tile_x + dx)
                        ty = int(center_tile_y + dy)

                        if tx < 0 or tx >= self._width or ty < 0 or ty >= self._height:
                            continue

                        dist = math.sqrt(dx * dx + dy * dy)
                        if dist > source.radius:
                            continue

                        if source.shape == FogShape.CONE:
                            if dist < 0.5:
                                pass
                            else:
                                angle_to = math.atan2(-dy, dx)
                                angle_diff = abs(
                                    (angle_to - math.radians(source.cone_direction) + math.pi) % (2 * math.pi) - math.pi
                                )
                                if angle_diff > math.radians(source.cone_angle / 2):
                                    continue

                        cell = grid[ty][tx]
                        cell.visibility = TileVisibility.VISIBLE
                        cell.revealed_by = source.id
                        cell.last_seen = now

        self._dirty = False

    def is_visible(self, tile_x: int, tile_y: int, team: Optional[int] = None) -> bool:
        if self._global_reveal:
            return True
        t = team if team is not None else self._active_team
        grid = self._grids.get(t)
        if grid and 0 <= tile_x < self._width and 0 <= tile_y < self._height:
            return grid[tile_y][tile_x].visibility == TileVisibility.VISIBLE
        return False

    def is_explored(self, tile_x: int, tile_y: int, team: Optional[int] = None) -> bool:
        t = team if team is not None else self._active_team
        grid = self._grids.get(t)
        if grid and 0 <= tile_x < self._width and 0 <= tile_y < self._height:
            return grid[tile_y][tile_x].visibility in (
                TileVisibility.EXPLORED,
                TileVisibility.VISIBLE,
            )
        return False

    def get_tile_state(self, tile_x: int, tile_y: int, team: Optional[int] = None) -> TileVisibility:
        t = team if team is not None else self._active_team
        grid = self._grids.get(t)
        if grid and 0 <= tile_x < self._width and 0 <= tile_y < self._height:
            return grid[tile_y][tile_x].visibility
        return TileVisibility.HIDDEN

    def get_grid_state(
        self,
        team: Optional[int] = None,
        as_values: bool = False,
    ) -> List[List[int]]:
        t = team if team is not None else self._active_team
        grid = self._grids.get(t, [])
        if as_values:
            return [[cell.visibility.value for cell in row] for row in grid]
        return [[cell.visibility.value for cell in row] for row in grid]

    def get_exploration_percentage(self, team: Optional[int] = None) -> float:
        t = team if team is not None else self._active_team
        grid = self._grids.get(t)
        if not grid:
            return 0.0

        total = self._width * self._height
        if total == 0:
            return 0.0

        explored = 0
        for row in grid:
            for cell in row:
                if cell.visibility != TileVisibility.HIDDEN:
                    explored += 1
        return explored / total

    def get_visible_count(self, team: Optional[int] = None) -> int:
        t = team if team is not None else self._active_team
        grid = self._grids.get(t)
        if not grid:
            return 0

        count = 0
        for row in grid:
            for cell in row:
                if cell.visibility == TileVisibility.VISIBLE:
                    count += 1
        return count

    def list_vision_sources(self, team: Optional[int] = None) -> List[Dict[str, Any]]:
        sources = self._sources
        if team is not None:
            sources = [s for s in sources if s.team == team]
        return [s.to_dict() for s in sources]

    def reset(self, team: Optional[int] = None) -> None:
        teams = range(self._max_teams) if team is None else [team]
        for t in teams:
            grid = self._grids.get(t, [])
            for row in grid:
                for cell in row:
                    cell.visibility = TileVisibility.HIDDEN
                    cell.revealed_by = None
                    cell.last_seen = 0.0
        self._dirty = True

    def get_stats(self) -> Dict[str, Any]:
        return {
            "width": self._width,
            "height": self._height,
            "tile_size": self._tile_size,
            "max_teams": self._max_teams,
            "active_team": self._active_team,
            "vision_sources": len(self._sources),
            "update_count": self._update_count,
            "global_reveal": self._global_reveal,
            "exploration_percent": round(self.get_exploration_percentage() * 100, 1),
            "visible_tiles": self.get_visible_count(),
        }


def get_fog_of_war(
    width: int = 64,
    height: int = 64,
    tile_size: float = 32.0,
    max_teams: int = 4,
) -> FogOfWarSystem:
    return FogOfWarSystem.get_instance(
        width=width,
        height=height,
        tile_size=tile_size,
        max_teams=max_teams,
    )