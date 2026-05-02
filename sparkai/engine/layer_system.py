"""
SparkLabs Engine - Layer System

Structured rendering layer management for depth ordering,
parallax scrolling, visibility groups, and composite blend
modes. Provides the z-ordering infrastructure for complex
AI-generated 2D scenes with multiple overlapping visual planes.

Architecture:
  LayerSystem
    |-- RenderLayer (name, z-order, blend mode, parallax factor)
    |-- LayerGroup (collection of layers with shared properties)
    |-- LayerStack (ordered list of layers for composition)

Layer Blend Modes:
  - NORMAL: standard alpha blending
  - ADDITIVE: light/screen blending for glow effects
  - MULTIPLY: darken blending for shadows
  - MASK: layer acts as a stencil mask

Parallax Modes:
  - FIXED: stays at screen position (HUD)
  - SCROLL: moves with camera at parallax_factor (background)
  - RATIO: moves proportionally (midground)

Usage:
    ls = LayerSystem()
    ls.add_layer("bg_far", z=0, parallax=0.1, blend="normal")
    ls.add_layer("bg_near", z=1, parallax=0.4, blend="normal")
    ls.add_layer("gameplay", z=10, parallax=1.0, blend="normal")
    ls.add_layer("foreground", z=50, parallax=1.5, blend="additive")
    ls.add_layer("hud", z=100, parallax=0.0, blend="normal")
    ls.hide_layer("hud")
    render_list = ls.get_sorted_layers()
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Dict, List, Optional, Set, Tuple


class LayerBlendMode(Enum):
    NORMAL = auto()
    ADDITIVE = auto()
    MULTIPLY = auto()
    SCREEN = auto()
    OVERLAY = auto()
    MASK = auto()
    DARKEN = auto()
    LIGHTEN = auto()


class LayerParallaxMode(Enum):
    FIXED = auto()
    SCROLL = auto()
    RATIO = auto()


@dataclass
class RenderLayer:
    name: str = ""
    layer_id: str = ""
    z_index: int = 0
    parallax_factor: float = 1.0
    blend_mode: LayerBlendMode = LayerBlendMode.NORMAL
    visible: bool = True
    opacity: float = 1.0
    tint_color: Tuple[float, float, float, float] = (1.0, 1.0, 1.0, 1.0)
    camera_relative: bool = True
    scroll_speed_x: float = 1.0
    scroll_speed_y: float = 1.0
    repeat_horizontal: bool = False
    repeat_vertical: bool = False
    entity_count: int = 0
    properties: Dict[str, Any] = field(default_factory=dict)


@dataclass
class LayerGroup:
    name: str = ""
    group_id: str = ""
    layers: List[str] = field(default_factory=list)
    visible: bool = True
    locked: bool = False
    expanded: bool = True
    color_tag: str = ""


@dataclass
class LayerStats:
    layer_count: int = 0
    visible_layer_count: int = 0
    group_count: int = 0
    total_entities: int = 0
    layer_names: List[str] = field(default_factory=list)
    sorted_layer_order: List[str] = field(default_factory=list)


class LayerSystem:
    _instance: Optional["LayerSystem"] = None

    def __init__(self):
        self._layers: Dict[str, RenderLayer] = {}
        self._groups: Dict[str, LayerGroup] = {}
        self._default_layer_id: Optional[str] = None
        self._setup_default_layers()

    @classmethod
    def get_instance(cls) -> "LayerSystem":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def _setup_default_layers(self) -> None:
        defaults = [
            ("background", 0, 0.1, LayerBlendMode.NORMAL),
            ("platforms", 5, 1.0, LayerBlendMode.NORMAL),
            ("gameplay", 10, 1.0, LayerBlendMode.NORMAL),
            ("foreground", 20, 1.2, LayerBlendMode.NORMAL),
            ("overlay", 30, 0.0, LayerBlendMode.ADDITIVE),
            ("ui", 100, 0.0, LayerBlendMode.NORMAL),
        ]
        for name, z, parallax, blend in defaults:
            self.add_layer(name, z_index=z, parallax_factor=parallax, blend_mode=blend)
        self._default_layer_id = next(iter(self._layers.values())).layer_id

    @property
    def default_layer_id(self) -> Optional[str]:
        return self._default_layer_id

    def add_layer(
        self,
        name: str,
        z_index: Optional[int] = None,
        parallax_factor: float = 1.0,
        blend_mode: LayerBlendMode = LayerBlendMode.NORMAL,
        **properties,
    ) -> RenderLayer:
        if z_index is None:
            existing_zs = [l.z_index for l in self._layers.values()]
            z_index = max(existing_zs, default=-1) + 1

        existing = self.find_layer_by_name(name)
        if existing:
            return existing

        layer_id = str(uuid.uuid4())
        layer = RenderLayer(
            name=name,
            layer_id=layer_id,
            z_index=z_index,
            parallax_factor=parallax_factor,
            blend_mode=blend_mode,
            properties=properties,
        )
        self._layers[layer_id] = layer
        if self._default_layer_id is None:
            self._default_layer_id = layer_id
        return layer

    def remove_layer(self, layer_id: str) -> bool:
        if layer_id not in self._layers:
            return False
        del self._layers[layer_id]
        if self._default_layer_id == layer_id:
            self._default_layer_id = next(iter(self._layers.values())).layer_id if self._layers else None
        for group in self._groups.values():
            if layer_id in group.layers:
                group.layers.remove(layer_id)
        return True

    def get_layer(self, layer_id: str) -> Optional[RenderLayer]:
        return self._layers.get(layer_id)

    def find_layer_by_name(self, name: str) -> Optional[RenderLayer]:
        for layer in self._layers.values():
            if layer.name == name:
                return layer
        return None

    def set_layer_visibility(self, layer_id: str, visible: bool) -> bool:
        layer = self._layers.get(layer_id)
        if not layer:
            return False
        layer.visible = visible
        return True

    def hide_layer(self, identifier: str) -> bool:
        return self._set_layer_visibility(identifier, False)

    def show_layer(self, identifier: str) -> bool:
        return self._set_layer_visibility(identifier, True)

    def toggle_layer(self, identifier: str) -> Optional[bool]:
        layer = self._resolve_layer(identifier)
        if not layer:
            return None
        layer.visible = not layer.visible
        return layer.visible

    def set_layer_opacity(self, identifier: str, opacity: float) -> bool:
        layer = self._resolve_layer(identifier)
        if not layer:
            return False
        layer.opacity = max(0.0, min(1.0, opacity))
        return True

    def set_layer_z_index(self, identifier: str, z_index: int) -> bool:
        layer = self._resolve_layer(identifier)
        if not layer:
            return False
        layer.z_index = z_index
        return True

    def set_layer_parallax(self, identifier: str, factor: float) -> bool:
        layer = self._resolve_layer(identifier)
        if not layer:
            return False
        layer.parallax_factor = factor
        return True

    def set_layer_blend_mode(self, identifier: str, blend_mode: LayerBlendMode) -> bool:
        layer = self._resolve_layer(identifier)
        if not layer:
            return False
        layer.blend_mode = blend_mode
        return True

    def set_layer_repeat(self, identifier: str, horizontal: bool, vertical: bool) -> bool:
        layer = self._resolve_layer(identifier)
        if not layer:
            return False
        layer.repeat_horizontal = horizontal
        layer.repeat_vertical = vertical
        return True

    def set_layer_scroll_speed(self, identifier: str, speed_x: float, speed_y: float) -> bool:
        layer = self._resolve_layer(identifier)
        if not layer:
            return False
        layer.scroll_speed_x = speed_x
        layer.scroll_speed_y = speed_y
        return True

    def get_sorted_layers(self, visible_only: bool = False) -> List[RenderLayer]:
        layers = list(self._layers.values())
        if visible_only:
            layers = [l for l in layers if l.visible]
        layers.sort(key=lambda l: l.z_index)
        return layers

    def get_layer_order(self) -> List[str]:
        return [l.layer_id for l in self.get_sorted_layers()]

    def move_layer_up(self, identifier: str) -> bool:
        return self._shift_layer_z(identifier, +1)

    def move_layer_down(self, identifier: str) -> bool:
        return self._shift_layer_z(identifier, -1)

    def move_layer_to_top(self, identifier: str) -> bool:
        layer = self._resolve_layer(identifier)
        if not layer:
            return False
        max_z = max((l.z_index for l in self._layers.values()), default=0)
        layer.z_index = max_z + 1
        return True

    def move_layer_to_bottom(self, identifier: str) -> bool:
        layer = self._resolve_layer(identifier)
        if not layer:
            return False
        min_z = min((l.z_index for l in self._layers.values()), default=0)
        layer.z_index = min_z - 1
        return True

    def create_group(self, name: str, layer_ids: List[str] | None = None) -> LayerGroup:
        group_id = str(uuid.uuid4())
        group = LayerGroup(name=name, group_id=group_id, layers=layer_ids or [])
        self._groups[group_id] = group
        return group

    def get_group(self, group_id: str) -> Optional[LayerGroup]:
        return self._groups.get(group_id)

    def add_layer_to_group(self, group_id: str, layer_id: str) -> bool:
        group = self._groups.get(group_id)
        if not group or layer_id not in self._layers:
            return False
        if layer_id not in group.layers:
            group.layers.append(layer_id)
        return True

    def remove_layer_from_group(self, group_id: str, layer_id: str) -> bool:
        group = self._groups.get(group_id)
        if not group:
            return False
        if layer_id in group.layers:
            group.layers.remove(layer_id)
        return True

    def delete_group(self, group_id: str) -> bool:
        if group_id not in self._groups:
            return False
        del self._groups[group_id]
        return True

    def set_group_visibility(self, group_id: str, visible: bool) -> bool:
        group = self._groups.get(group_id)
        if not group:
            return False
        group.visible = visible
        for lid in group.layers:
            self.set_layer_visibility(lid, visible)
        return True

    def increment_entity_count(self, layer_id: str) -> None:
        layer = self._layers.get(layer_id)
        if layer:
            layer.entity_count += 1

    def decrement_entity_count(self, layer_id: str) -> None:
        layer = self._layers.get(layer_id)
        if layer:
            layer.entity_count = max(0, layer.entity_count - 1)

    def get_layers_for_rendering(self) -> List[Dict[str, Any]]:
        result = []
        for layer in self.get_sorted_layers():
            if not layer.visible:
                continue
            result.append({
                "layer_id": layer.layer_id,
                "name": layer.name,
                "z_index": layer.z_index,
                "parallax_factor": layer.parallax_factor,
                "blend_mode": layer.blend_mode.name.lower(),
                "opacity": layer.opacity,
                "tint_color": layer.tint_color,
                "camera_relative": layer.camera_relative,
                "scroll_speed": (layer.scroll_speed_x, layer.scroll_speed_y),
                "repeat": (layer.repeat_horizontal, layer.repeat_vertical),
                "entity_count": layer.entity_count,
            })
        return result

    def get_computed_parallax_offset(
        self, layer_id: str, camera_x: float, camera_y: float
    ) -> Tuple[float, float]:
        layer = self._layers.get(layer_id)
        if not layer:
            return (0.0, 0.0)
        offset_x = camera_x * (1.0 - layer.parallax_factor) * layer.scroll_speed_x
        offset_y = camera_y * (1.0 - layer.parallax_factor) * layer.scroll_speed_y
        return (offset_x, offset_y)

    def get_all_layers(self) -> List[Dict[str, Any]]:
        result = []
        for layer in self.get_sorted_layers():
            result.append({
                "layer_id": layer.layer_id,
                "name": layer.name,
                "z_index": layer.z_index,
                "visible": layer.visible,
                "opacity": layer.opacity,
                "parallax_factor": layer.parallax_factor,
                "blend_mode": layer.blend_mode.name.lower(),
                "entity_count": layer.entity_count,
                "properties": layer.properties,
            })
        return result

    def get_all_groups(self) -> List[Dict[str, Any]]:
        result = []
        for group in self._groups.values():
            result.append({
                "group_id": group.group_id,
                "name": group.name,
                "visible": group.visible,
                "locked": group.locked,
                "color_tag": group.color_tag,
                "layer_ids": group.layers,
            })
        return result

    def get_stats(self) -> LayerStats:
        layers = self._layers.values()
        visible = [l for l in layers if l.visible]
        sorted_layers = self.get_sorted_layers()
        total_entities = sum(l.entity_count for l in layers)
        return LayerStats(
            layer_count=len(layers),
            visible_layer_count=len(visible),
            group_count=len(self._groups),
            total_entities=total_entities,
            layer_names=[l.name for l in sorted_layers],
            sorted_layer_order=[l.layer_id for l in sorted_layers],
        )

    def _set_layer_visibility(self, identifier: str, visible: bool) -> bool:
        layer = self._resolve_layer(identifier)
        if not layer:
            return False
        layer.visible = visible
        return True

    def _resolve_layer(self, identifier: str) -> Optional[RenderLayer]:
        if identifier in self._layers:
            return self._layers[identifier]
        return self.find_layer_by_name(identifier)

    def _shift_layer_z(self, identifier: str, delta: int) -> bool:
        layer = self._resolve_layer(identifier)
        if not layer:
            return False
        layer.z_index += delta
        return True


def get_layer_system() -> LayerSystem:
    return LayerSystem.get_instance()
