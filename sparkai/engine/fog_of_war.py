"""
SparkLabs Engine - Fog of War System

Grid-based visibility and exploration system for strategy and RPG games.
Manages per-layer fog cells with multiple reveal methods, persistent
exploration memory, and observer-driven visibility updates.

Architecture:
  FogOfWarSystem
    |-- FogLayer (named visibility grid with configurable appearance)
    |-- FogCell (individual grid cell with state and reveal tracking)
    |-- Observer Manager (position-based visibility calculation)
    |-- Reveal Processor (circular, LOS, sector, proximity, global modes)

Cell States:
  - HIDDEN: never seen — fully obscured
  - EXPLORED: previously seen but not currently visible — dimmed
  - VISIBLE: currently within an observer's range — fully lit
  - PERMANENTLY_VISIBLE: always visible regardless of observers
"""

from __future__ import annotations

import math
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple


class FogRevealMethod(Enum):
    CIRCULAR = "circular"
    LINE_OF_SIGHT = "line_of_sight"
    SECTOR = "sector"
    PROXIMITY = "proximity"
    GLOBAL = "global"


class FogCellState(Enum):
    HIDDEN = 0
    EXPLORED = 1
    VISIBLE = 2
    PERMANENTLY_VISIBLE = 3


class TileVisibility(Enum):
    """Tile-based visibility states for strategy grid maps."""
    UNDISCOVERED = "undiscovered"
    EXPLORED = "explored"
    CURRENTLY_VISIBLE = "currently_visible"
    TEAM_VISIBLE = "team_visible"
    GLOBAL_VISIBLE = "global_visible"


class FogShape(Enum):
    """Shape presets for fog area application."""
    CIRCLE = "circle"
    SQUARE = "square"
    CONE = "cone"
    DIAMOND = "diamond"
    CROSS = "cross"
    LINE = "line"
    CUSTOM = "custom"


@dataclass
class FogCell:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    grid_x: int = 0
    grid_y: int = 0
    state: FogCellState = FogCellState.HIDDEN
    last_updated: float = field(default_factory=time.time)
    revealed_by: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "grid_x": self.grid_x,
            "grid_y": self.grid_y,
            "state": self.state.value,
            "last_updated": self.last_updated,
            "revealed_by_count": len(self.revealed_by),
        }


@dataclass
class FogLayer:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = ""
    grid_width: int = 64
    grid_height: int = 64
    cell_size: float = 32.0
    cells: List[FogCell] = field(default_factory=list)
    alpha_hidden: float = 1.0
    alpha_explored: float = 0.5

    def get_cell(self, x: int, y: int) -> Optional[FogCell]:
        for cell in self.cells:
            if cell.grid_x == x and cell.grid_y == y:
                return cell
        return None

    def cell_count_by_state(self, state: FogCellState) -> int:
        return sum(1 for c in self.cells if c.state == state)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "grid_width": self.grid_width,
            "grid_height": self.grid_height,
            "cell_size": self.cell_size,
            "total_cells": len(self.cells),
            "hidden_cells": self.cell_count_by_state(FogCellState.HIDDEN),
            "explored_cells": self.cell_count_by_state(FogCellState.EXPLORED),
            "visible_cells": self.cell_count_by_state(FogCellState.VISIBLE),
            "permanent_cells": self.cell_count_by_state(FogCellState.PERMANENTLY_VISIBLE),
            "alpha_hidden": self.alpha_hidden,
            "alpha_explored": self.alpha_explored,
        }


class FogOfWarSystem:
    """
    Grid-based fog of war with layered visibility management.

    Supports multiple fog layers with different opacity settings,
    various reveal methods (circular, LOS, sector, proximity, global),
    and observer-driven visibility updates.

    Usage:
        fog = get_fog_of_war()
        layer = fog.create_layer("main", 128, 128, 32.0)
        fog.reveal_area(layer.id, 64, 64, 10, "player_unit_1")
        fog.update_visibility([("player_unit_1", 64.0, 64.0, 12.0)])
        state = fog.get_cell_state(layer.id, 32, 50)
    """

    _instance: Optional["FogOfWarSystem"] = None

    def __init__(self):
        self._layers: Dict[str, FogLayer] = {}
        self._observers: Dict[str, Tuple[float, float, float, str]] = {}
        self._update_count: int = 0
        self._total_cells_revealed: int = 0

    @classmethod
    def get_instance(cls) -> "FogOfWarSystem":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def create_layer(
        self,
        name: str,
        width: int,
        height: int,
        cell_size: float = 32.0,
    ) -> FogLayer:
        layer = FogLayer(
            name=name,
            grid_width=max(1, width),
            grid_height=max(1, height),
            cell_size=max(1.0, cell_size),
        )

        layer.cells = []
        for y in range(layer.grid_height):
            for x in range(layer.grid_width):
                cell = FogCell(grid_x=x, grid_y=y)
                layer.cells.append(cell)

        self._layers[layer.id] = layer
        return layer

    def remove_layer(self, layer_id: str) -> bool:
        if layer_id in self._layers:
            del self._layers[layer_id]
            return True
        return False

    def get_layer(self, layer_id: str) -> Optional[FogLayer]:
        return self._layers.get(layer_id)

    def list_layers(self) -> List[FogLayer]:
        return list(self._layers.values())

    def reveal_area(
        self,
        layer_id: str,
        center_x: float,
        center_y: float,
        radius: float,
        revealer_id: str,
        method: FogRevealMethod = FogRevealMethod.CIRCULAR,
    ) -> int:
        layer = self._layers.get(layer_id)
        if layer is None:
            return 0

        now = time.time()
        revealed_count = 0

        if method == FogRevealMethod.GLOBAL:
            for cell in layer.cells:
                if cell.state != FogCellState.PERMANENTLY_VISIBLE:
                    cell.state = FogCellState.VISIBLE
                cell.last_updated = now
                if revealer_id not in cell.revealed_by:
                    cell.revealed_by.append(revealer_id)
                revealed_count += 1
            self._total_cells_revealed += revealed_count
            return revealed_count

        radius_cells = int(math.ceil(radius / layer.cell_size))

        for cell in layer.cells:
            dx = (cell.grid_x * layer.cell_size + layer.cell_size / 2) - center_x
            dy = (cell.grid_y * layer.cell_size + layer.cell_size / 2) - center_y

            if method == FogRevealMethod.CIRCULAR:
                if math.sqrt(dx * dx + dy * dy) <= radius:
                    if cell.state != FogCellState.PERMANENTLY_VISIBLE:
                        cell.state = FogCellState.VISIBLE
                    cell.last_updated = now
                    if revealer_id not in cell.revealed_by:
                        cell.revealed_by.append(revealer_id)
                    revealed_count += 1

            elif method == FogRevealMethod.SECTOR:
                if math.sqrt(dx * dx + dy * dy) <= radius:
                    angle = math.atan2(dy, dx)
                    if -math.pi / 4 <= angle <= math.pi / 4:
                        if cell.state != FogCellState.PERMANENTLY_VISIBLE:
                            cell.state = FogCellState.VISIBLE
                        cell.last_updated = now
                        if revealer_id not in cell.revealed_by:
                            cell.revealed_by.append(revealer_id)
                        revealed_count += 1

            elif method == FogRevealMethod.PROXIMITY:
                dist = math.sqrt(dx * dx + dy * dy)
                effective_radius = radius * (1.0 - min(dist / (radius * 2), 0.9))
                if dist <= effective_radius:
                    if cell.state != FogCellState.PERMANENTLY_VISIBLE:
                        cell.state = FogCellState.VISIBLE
                    cell.last_updated = now
                    if revealer_id not in cell.revealed_by:
                        cell.revealed_by.append(revealer_id)
                    revealed_count += 1

            elif method == FogRevealMethod.LINE_OF_SIGHT:
                if math.sqrt(dx * dx + dy * dy) <= radius:
                    ray_steps = max(1, int(math.sqrt(dx * dx + dy * dy) / layer.cell_size))
                    blocked = False
                    for step in range(1, ray_steps + 1):
                        t = step / ray_steps
                        sx = center_x + dx * t
                        sy = center_y + dy * t
                        check_x = int(sx / layer.cell_size)
                        check_y = int(sy / layer.cell_size)
                        blocker = layer.get_cell(check_x, check_y)
                        if blocker and blocker.state == FogCellState.PERMANENTLY_VISIBLE:
                            continue
                    if not blocked:
                        if cell.state != FogCellState.PERMANENTLY_VISIBLE:
                            cell.state = FogCellState.VISIBLE
                        cell.last_updated = now
                        if revealer_id not in cell.revealed_by:
                            cell.revealed_by.append(revealer_id)
                        revealed_count += 1

        self._total_cells_revealed += revealed_count
        return revealed_count

    def conceal_area(
        self,
        layer_id: str,
        center_x: float,
        center_y: float,
        radius: float,
    ) -> int:
        layer = self._layers.get(layer_id)
        if layer is None:
            return 0

        concealed_count = 0
        for cell in layer.cells:
            if cell.state == FogCellState.PERMANENTLY_VISIBLE:
                continue
            dx = (cell.grid_x * layer.cell_size + layer.cell_size / 2) - center_x
            dy = (cell.grid_y * layer.cell_size + layer.cell_size / 2) - center_y
            if math.sqrt(dx * dx + dy * dy) <= radius:
                cell.state = FogCellState.HIDDEN
                cell.revealed_by.clear()
                cell.last_updated = time.time()
                concealed_count += 1

        return concealed_count

    def update_visibility(
        self,
        observer_positions: List[Tuple[str, float, float, float]],
    ) -> None:
        self._update_count += 1
        now = time.time()

        for observer_id, ox, oy, radius in observer_positions:
            self._observers[observer_id] = (ox, oy, radius, "circular")

        for layer in self._layers.values():
            for cell in layer.cells:
                if cell.state == FogCellState.VISIBLE:
                    cell.state = FogCellState.EXPLORED
                elif cell.state == FogCellState.PERMANENTLY_VISIBLE:
                    continue

            for observer_id, (ox, oy, radius, method) in self._observers.items():
                for cell in layer.cells:
                    if cell.state == FogCellState.PERMANENTLY_VISIBLE:
                        continue
                    cx = cell.grid_x * layer.cell_size + layer.cell_size / 2
                    cy = cell.grid_y * layer.cell_size + layer.cell_size / 2
                    dist = math.sqrt((cx - ox) ** 2 + (cy - oy) ** 2)
                    if dist <= radius:
                        cell.state = FogCellState.VISIBLE
                        cell.last_updated = now
                        if observer_id not in cell.revealed_by:
                            cell.revealed_by.append(observer_id)

    def add_observer(
        self,
        observer_id: str,
        x: float,
        y: float,
        radius: float,
        method: str = "circular",
    ) -> None:
        self._observers[observer_id] = (x, y, radius, method)

    def move_observer(self, observer_id: str, x: float, y: float) -> bool:
        if observer_id in self._observers:
            _, _, radius, method = self._observers[observer_id]
            self._observers[observer_id] = (x, y, radius, method)
            return True
        return False

    def remove_observer(self, observer_id: str) -> bool:
        if observer_id in self._observers:
            del self._observers[observer_id]
            return True
        return False

    def get_cell_state(self, layer_id: str, x: int, y: int) -> FogCellState:
        layer = self._layers.get(layer_id)
        if layer is None:
            return FogCellState.HIDDEN
        cell = layer.get_cell(x, y)
        if cell is None:
            return FogCellState.HIDDEN
        return cell.state

    def set_cell_permanent(self, layer_id: str, x: int, y: int) -> bool:
        layer = self._layers.get(layer_id)
        if layer is None:
            return False
        cell = layer.get_cell(x, y)
        if cell is None:
            return False
        cell.state = FogCellState.PERMANENTLY_VISIBLE
        cell.last_updated = time.time()
        return True

    def get_grid_state(self, layer_id: str) -> List[List[int]]:
        layer = self._layers.get(layer_id)
        if layer is None:
            return []
        grid = [[0] * layer.grid_width for _ in range(layer.grid_height)]
        for cell in layer.cells:
            grid[cell.grid_y][cell.grid_x] = cell.state.value
        return grid

    def get_exploration_percentage(self, layer_id: str) -> float:
        layer = self._layers.get(layer_id)
        if layer is None or len(layer.cells) == 0:
            return 0.0
        explored = sum(1 for c in layer.cells if c.state != FogCellState.HIDDEN)
        return explored / len(layer.cells)

    def reset_layer(self, layer_id: str) -> None:
        layer = self._layers.get(layer_id)
        if layer is None:
            return
        for cell in layer.cells:
            if cell.state != FogCellState.PERMANENTLY_VISIBLE:
                cell.state = FogCellState.HIDDEN
            cell.revealed_by.clear()
            cell.last_updated = time.time()

    def reset_all(self) -> None:
        for layer in self._layers.values():
            self.reset_layer(layer.id)

    def get_stats(self) -> Dict[str, Any]:
        layers_stats = [layer.to_dict() for layer in self._layers.values()]
        return {
            "layer_count": len(self._layers),
            "observer_count": len(self._observers),
            "update_count": self._update_count,
            "total_cells_revealed": self._total_cells_revealed,
            "layers": layers_stats,
        }


def get_fog_of_war() -> FogOfWarSystem:
    return FogOfWarSystem.get_instance()