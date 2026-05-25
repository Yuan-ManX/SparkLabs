"""
SparkLabs Engine - Render Layer System

Z-order layer management with per-layer render effects, sorting strategies,
and layer groups for organizing entity rendering pipelines.

Architecture:
    RenderLayerSystem
      |-- RenderLayer (z-ordered renderable container with effects and visibility)
      |-- LayerGroup (named collection of layers with collapse/lock state)
      |-- RenderSortRule (property-based sorting configuration per layer)
      |-- LayerConfig (scene-wide layer configuration with defaults)

Layer Features:
    - BY_Z_ORDER: sort entities by their assigned z-index value
    - BY_Y_POSITION: sort by world-space Y-coordinate for isometric/perspective
    - BY_DEPTH: sort by depth buffer or distance from camera
    - CUSTOM_COMPARATOR: user-defined comparison function
    - Per-layer post-processing effects (tint, blur, pixelate, outline, etc.)
    - Group-based layer organization with collapse and lock toggles
"""

from __future__ import annotations

import threading
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple


class SortStrategy(Enum):
    """Sorting method for ordering entities within a render layer."""
    BY_Z_ORDER = "by_z_order"
    BY_Y_POSITION = "by_y_position"
    BY_DEPTH = "by_depth"
    CUSTOM_COMPARATOR = "custom_comparator"
    NONE = "none"


class LayerEffect(Enum):
    """Per-layer post-processing effect applied during rendering."""
    NONE = "none"
    COLOR_TINT = "color_tint"
    BLUR = "blur"
    PIXELATE = "pixelate"
    OUTLINE = "outline"
    GRAYSCALE = "grayscale"
    SEPIA = "sepia"
    INVERT = "invert"
    CHROMATIC_SHIFT = "chromatic_shift"
    CUSTOM_SHADER = "custom_shader"


class LayerVisibility(Enum):
    """Visibility state determining whether and how a layer is rendered."""
    VISIBLE = "visible"
    HIDDEN = "hidden"
    FADE_IN = "fade_in"
    FADE_OUT = "fade_out"
    DISTANCE_CULLED = "distance_culled"


class RenderTarget(Enum):
    """Destination surface for a render layer's output."""
    SCREEN = "screen"
    RENDER_TEXTURE = "render_texture"
    POST_PROCESS_BUFFER = "post_process_buffer"


@dataclass
class RenderLayer:
    """A z-ordered container holding entities with per-layer effects and sorting."""
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = ""
    z_index: int = 0
    sort_strategy: SortStrategy = SortStrategy.BY_Z_ORDER
    visibility: LayerVisibility = LayerVisibility.VISIBLE
    effect: LayerEffect = LayerEffect.NONE
    effect_params: Dict[str, Any] = field(default_factory=dict)
    render_target: RenderTarget = RenderTarget.SCREEN
    entities: List[str] = field(default_factory=list)
    enabled: bool = True
    parent_layer_id: str = ""
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "z_index": self.z_index,
            "sort_strategy": self.sort_strategy.value,
            "visibility": self.visibility.value,
            "effect": self.effect.value,
            "effect_params": self.effect_params,
            "render_target": self.render_target.value,
            "entity_count": len(self.entities),
            "entities": list(self.entities),
            "enabled": self.enabled,
            "parent_layer_id": self.parent_layer_id,
            "created_at": self.created_at,
        }


@dataclass
class LayerGroup:
    """Named collection of render layers with collapse and lock state management."""
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = ""
    layers: List[str] = field(default_factory=list)
    collapsed: bool = False
    locked: bool = False
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "layer_count": len(self.layers),
            "layers": list(self.layers),
            "collapsed": self.collapsed,
            "locked": self.locked,
            "created_at": self.created_at,
        }


@dataclass
class RenderSortRule:
    """Property-based sorting rule applied to entities within a render layer."""
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    layer_id: str = ""
    property_name: str = "z_index"
    ascending: bool = True
    priority: int = 0
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "layer_id": self.layer_id,
            "property_name": self.property_name,
            "ascending": self.ascending,
            "priority": self.priority,
            "created_at": self.created_at,
        }


@dataclass
class LayerConfig:
    """Scene-wide configuration for render layers including defaults and limits."""
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    scene_id: str = ""
    groups: List[str] = field(default_factory=list)
    default_sort: SortStrategy = SortStrategy.BY_Z_ORDER
    max_layers: int = 256
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "scene_id": self.scene_id,
            "group_count": len(self.groups),
            "groups": list(self.groups),
            "default_sort": self.default_sort.value,
            "max_layers": self.max_layers,
            "created_at": self.created_at,
        }


class RenderLayerSystem:
    """Z-order layer management with per-layer render effects and sorting strategies."""

    _instance: Optional["RenderLayerSystem"] = None
    _lock = threading.RLock()

    MAX_LAYERS = 4096
    MAX_GROUPS = 256
    MAX_ENTITIES_PER_LAYER = 65536
    MAX_SORT_RULES = 128

    def __init__(self) -> None:
        self._layers: Dict[str, RenderLayer] = {}
        self._groups: Dict[str, LayerGroup] = {}
        self._sort_rules: Dict[str, RenderSortRule] = {}
        self._configs: Dict[str, LayerConfig] = {}
        self._entity_to_layer: Dict[str, str] = {}
        self._custom_comparators: Dict[str, Callable[[str, str], int]] = {}
        self._total_layers_created: int = 0
        self._total_groups_created: int = 0
        self._total_entities_assigned: int = 0
        self._total_sorts_performed: int = 0

    @classmethod
    def get_instance(cls) -> "RenderLayerSystem":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    # ---- Layer Management ----

    def create_layer(self,
                     name: str,
                     z_index: int = 0,
                     sort_strategy: str = "by_z_order") -> RenderLayer:
        try:
            strategy = SortStrategy(sort_strategy.lower())
        except ValueError:
            strategy = SortStrategy.BY_Z_ORDER

        if len(self._layers) >= self.MAX_LAYERS:
            raise RuntimeError(
                f"Layer limit reached ({self.MAX_LAYERS})"
            )

        layer = RenderLayer(
            name=name,
            z_index=z_index,
            sort_strategy=strategy,
        )
        self._layers[layer.id] = layer
        self._total_layers_created += 1
        return layer

    def get_layer(self, layer_id: str) -> Optional[RenderLayer]:
        return self._layers.get(layer_id)

    def list_layers(self) -> List[RenderLayer]:
        return sorted(self._layers.values(), key=lambda l: l.z_index)

    def remove_layer(self, layer_id: str) -> bool:
        layer = self._layers.pop(layer_id, None)
        if layer is None:
            return False

        for entity_id in layer.entities:
            self._entity_to_layer.pop(entity_id, None)

        sort_rule_ids = [
            rid for rid, rule in self._sort_rules.items()
            if rule.layer_id == layer_id
        ]
        for rid in sort_rule_ids:
            del self._sort_rules[rid]

        for group in self._groups.values():
            if layer_id in group.layers:
                group.layers.remove(layer_id)

        return True

    def set_layer_z_index(self, layer_id: str, z_index: int) -> bool:
        layer = self._layers.get(layer_id)
        if layer is None:
            return False
        layer.z_index = z_index
        return True

    def set_layer_enabled(self, layer_id: str, enabled: bool) -> bool:
        layer = self._layers.get(layer_id)
        if layer is None:
            return False
        layer.enabled = enabled
        return True

    # ---- Group Management ----

    def create_group(self, name: str) -> LayerGroup:
        if len(self._groups) >= self.MAX_GROUPS:
            raise RuntimeError(
                f"Group limit reached ({self.MAX_GROUPS})"
            )

        group = LayerGroup(name=name)
        self._groups[group.id] = group
        self._total_groups_created += 1
        return group

    def get_group(self, group_id: str) -> Optional[LayerGroup]:
        return self._groups.get(group_id)

    def list_groups(self) -> List[LayerGroup]:
        return sorted(self._groups.values(), key=lambda g: g.created_at)

    def remove_group(self, group_id: str) -> bool:
        if group_id not in self._groups:
            return False
        del self._groups[group_id]
        return True

    def add_layer_to_group(self, group_id: str, layer_id: str) -> bool:
        group = self._groups.get(group_id)
        layer = self._layers.get(layer_id)
        if group is None or layer is None:
            return False
        if group.locked:
            return False
        if layer_id not in group.layers:
            group.layers.append(layer_id)
        return True

    def remove_layer_from_group(self, group_id: str, layer_id: str) -> bool:
        group = self._groups.get(group_id)
        if group is None:
            return False
        if group.locked:
            return False
        if layer_id in group.layers:
            group.layers.remove(layer_id)
            return True
        return False

    # ---- Entity Assignment ----

    def assign_entity_to_layer(self, entity_id: str, layer_id: str) -> bool:
        layer = self._layers.get(layer_id)
        if layer is None:
            return False

        previous_layer_id = self._entity_to_layer.get(entity_id)
        if previous_layer_id:
            prev_layer = self._layers.get(previous_layer_id)
            if prev_layer and entity_id in prev_layer.entities:
                prev_layer.entities.remove(entity_id)

        if entity_id not in layer.entities:
            if len(layer.entities) >= self.MAX_ENTITIES_PER_LAYER:
                raise RuntimeError(
                    f"Entity limit per layer reached ({self.MAX_ENTITIES_PER_LAYER})"
                )
            layer.entities.append(entity_id)

        self._entity_to_layer[entity_id] = layer_id
        self._total_entities_assigned += 1
        return True

    def get_entity_layer(self, entity_id: str) -> Optional[str]:
        return self._entity_to_layer.get(entity_id)

    def remove_entity_from_layer(self, entity_id: str, layer_id: str) -> bool:
        layer = self._layers.get(layer_id)
        if layer is None:
            return False
        if entity_id in layer.entities:
            layer.entities.remove(entity_id)
            self._entity_to_layer.pop(entity_id, None)
            return True
        return False

    def get_entities_in_layer(self, layer_id: str) -> List[str]:
        layer = self._layers.get(layer_id)
        if layer is None:
            return []
        return list(layer.entities)

    # ---- Effect Management ----

    def set_layer_effect(self,
                         layer_id: str,
                         effect: str = "none",
                         params: Optional[Dict[str, Any]] = None) -> Optional[RenderLayer]:
        layer = self._layers.get(layer_id)
        if layer is None:
            return None

        try:
            resolved = LayerEffect(effect.lower())
        except ValueError:
            resolved = LayerEffect.NONE

        layer.effect = resolved
        layer.effect_params = params or {}
        return layer

    def set_layer_render_target(self,
                                layer_id: str,
                                render_target: str = "screen") -> bool:
        layer = self._layers.get(layer_id)
        if layer is None:
            return False

        try:
            target = RenderTarget(render_target.lower())
        except ValueError:
            target = RenderTarget.SCREEN

        layer.render_target = target
        return True

    # ---- Visibility Management ----

    def set_layer_visibility(self,
                             layer_id: str,
                             visibility: str = "visible") -> Optional[RenderLayer]:
        layer = self._layers.get(layer_id)
        if layer is None:
            return None

        try:
            resolved = LayerVisibility(visibility.lower())
        except ValueError:
            resolved = LayerVisibility.VISIBLE

        layer.visibility = resolved
        return layer

    def show_layer(self, layer_id: str) -> bool:
        layer = self._layers.get(layer_id)
        if layer is None:
            return False
        layer.visibility = LayerVisibility.VISIBLE
        return True

    def hide_layer(self, layer_id: str) -> bool:
        layer = self._layers.get(layer_id)
        if layer is None:
            return False
        layer.visibility = LayerVisibility.HIDDEN
        return True

    def get_visible_layers(self) -> List[RenderLayer]:
        return [
            l for l in self._layers.values()
            if l.enabled and l.visibility != LayerVisibility.HIDDEN
        ]

    # ---- Z-Order Reordering ----

    def reorder_layers(self, group_id: str, layer_order: List[str]) -> bool:
        group = self._groups.get(group_id)
        if group is None:
            return False
        if group.locked:
            return False

        existing_set = set(group.layers)
        requested_set = set(layer_order)

        if existing_set != requested_set:
            return False

        group.layers = list(layer_order)
        return True

    def move_layer_up(self, group_id: str, layer_id: str) -> bool:
        group = self._groups.get(group_id)
        if group is None or layer_id not in group.layers:
            return False
        if group.locked:
            return False

        idx = group.layers.index(layer_id)
        if idx < len(group.layers) - 1:
            group.layers[idx], group.layers[idx + 1] = (
                group.layers[idx + 1], group.layers[idx]
            )
            return True
        return False

    def move_layer_down(self, group_id: str, layer_id: str) -> bool:
        group = self._groups.get(group_id)
        if group is None or layer_id not in group.layers:
            return False
        if group.locked:
            return False

        idx = group.layers.index(layer_id)
        if idx > 0:
            group.layers[idx], group.layers[idx - 1] = (
                group.layers[idx - 1], group.layers[idx]
            )
            return True
        return False

    # ---- Sorting ----

    def sort_layer_entities(self, layer_id: str) -> List[str]:
        layer = self._layers.get(layer_id)
        if layer is None:
            return []

        sorted_entities = self._apply_sort_strategy(
            layer.entities, layer.sort_strategy
        )

        layer_rules = sorted(
            [r for r in self._sort_rules.values() if r.layer_id == layer_id],
            key=lambda r: r.priority,
        )

        for rule in layer_rules:
            sorted_entities = sorted(
                sorted_entities,
                key=lambda eid: self._compute_sort_key(eid, rule),
                reverse=not rule.ascending,
            )

        layer.entities = sorted_entities
        self._total_sorts_performed += 1
        return list(sorted_entities)

    def set_layer_sort_strategy(self, layer_id: str, sort_strategy: str = "by_z_order") -> bool:
        layer = self._layers.get(layer_id)
        if layer is None:
            return False

        try:
            strategy = SortStrategy(sort_strategy.lower())
        except ValueError:
            return False

        layer.sort_strategy = strategy
        return True

    def add_sort_rule(self,
                      layer_id: str,
                      property_name: str = "z_index",
                      ascending: bool = True,
                      priority: int = 0) -> Optional[RenderSortRule]:
        layer = self._layers.get(layer_id)
        if layer is None:
            return None

        if len(self._sort_rules) >= self.MAX_SORT_RULES:
            raise RuntimeError(
                f"Sort rule limit reached ({self.MAX_SORT_RULES})"
            )

        rule = RenderSortRule(
            layer_id=layer_id,
            property_name=property_name,
            ascending=ascending,
            priority=priority,
        )
        self._sort_rules[rule.id] = rule
        return rule

    def get_sort_rules(self, layer_id: str) -> List[RenderSortRule]:
        return sorted(
            [r for r in self._sort_rules.values() if r.layer_id == layer_id],
            key=lambda r: r.priority,
        )

    def remove_sort_rule(self, rule_id: str) -> bool:
        if rule_id not in self._sort_rules:
            return False
        del self._sort_rules[rule_id]
        return True

    def set_custom_comparator(self,
                               layer_id: str,
                               comparator: Callable[[str, str], int]) -> bool:
        layer = self._layers.get(layer_id)
        if layer is None:
            return False
        self._custom_comparators[layer_id] = comparator
        return True

    # ---- Render Order ----

    def get_render_order(self, scene_id: str) -> List[Tuple[str, List[str]]]:
        config = self._configs.get(scene_id)
        ordered: List[Tuple[str, List[str]]] = []

        if config is None:
            visible = sorted(
                self.get_visible_layers(),
                key=lambda l: l.z_index,
            )
            for layer in visible:
                ordered.append((layer.id, list(layer.entities)))
            return ordered

        for group_id in config.groups:
            group = self._groups.get(group_id)
            if group is None or group.collapsed:
                continue
            for layer_id in group.layers:
                layer = self._layers.get(layer_id)
                if layer is None or not layer.enabled:
                    continue
                if layer.visibility == LayerVisibility.HIDDEN:
                    continue
                ordered.append((layer.id, list(layer.entities)))

        ungrouped = [
            l for l in self._layers.values()
            if l.enabled
            and l.visibility != LayerVisibility.HIDDEN
            and not any(l.id in self._groups.get(gid, LayerGroup("")).layers
                        for gid in config.groups)
        ]
        ungrouped.sort(key=lambda l: l.z_index)
        for layer in ungrouped:
            ordered.append((layer.id, list(layer.entities)))

        return ordered

    # ---- Layer Merging and Cloning ----

    def merge_layers(self, source_layer_id: str, target_layer_id: str) -> bool:
        source = self._layers.get(source_layer_id)
        target = self._layers.get(target_layer_id)
        if source is None or target is None:
            return False
        if source_layer_id == target_layer_id:
            return False

        for entity_id in source.entities:
            if entity_id not in target.entities:
                if len(target.entities) >= self.MAX_ENTITIES_PER_LAYER:
                    return False
                target.entities.append(entity_id)
                self._entity_to_layer[entity_id] = target_layer_id

        self.remove_layer(source_layer_id)
        return True

    def clone_layer(self, layer_id: str, new_name: str) -> Optional[RenderLayer]:
        source = self._layers.get(layer_id)
        if source is None:
            return None

        if len(self._layers) >= self.MAX_LAYERS:
            raise RuntimeError(
                f"Layer limit reached ({self.MAX_LAYERS})"
            )

        cloned = RenderLayer(
            name=new_name,
            z_index=source.z_index,
            sort_strategy=source.sort_strategy,
            visibility=source.visibility,
            effect=source.effect,
            effect_params=dict(source.effect_params),
            render_target=source.render_target,
            entities=list(source.entities),
            enabled=source.enabled,
            parent_layer_id=source.parent_layer_id,
        )
        self._layers[cloned.id] = cloned
        self._total_layers_created += 1

        for entity_id in cloned.entities:
            self._entity_to_layer[entity_id] = cloned.id

        return cloned

    # ---- Group Lock and Collapse ----

    def lock_group(self, group_id: str) -> bool:
        group = self._groups.get(group_id)
        if group is None:
            return False
        group.locked = True
        return True

    def unlock_group(self, group_id: str) -> bool:
        group = self._groups.get(group_id)
        if group is None:
            return False
        group.locked = False
        return True

    def collapse_group(self, group_id: str) -> bool:
        group = self._groups.get(group_id)
        if group is None:
            return False
        group.collapsed = True
        return True

    def expand_group(self, group_id: str) -> bool:
        group = self._groups.get(group_id)
        if group is None:
            return False
        group.collapsed = False
        return True

    def is_group_locked(self, group_id: str) -> bool:
        group = self._groups.get(group_id)
        if group is None:
            return False
        return group.locked

    def is_group_collapsed(self, group_id: str) -> bool:
        group = self._groups.get(group_id)
        if group is None:
            return False
        return group.collapsed

    # ---- Config Management ----

    def configure_scene_layers(self,
                               scene_id: str,
                               max_layers: int = 256) -> LayerConfig:
        config = LayerConfig(
            scene_id=scene_id,
            max_layers=max(1, max_layers),
        )
        self._configs[scene_id] = config
        return config

    def get_scene_config(self, scene_id: str) -> Optional[LayerConfig]:
        return self._configs.get(scene_id)

    def add_group_to_config(self, scene_id: str, group_id: str) -> bool:
        config = self._configs.get(scene_id)
        group = self._groups.get(group_id)
        if config is None or group is None:
            return False
        if group_id not in config.groups:
            config.groups.append(group_id)
        return True

    def remove_group_from_config(self, scene_id: str, group_id: str) -> bool:
        config = self._configs.get(scene_id)
        if config is None:
            return False
        if group_id in config.groups:
            config.groups.remove(group_id)
            return True
        return False

    # ---- Parent-Child Relationships ----

    def set_parent_layer(self, layer_id: str, parent_id: str) -> bool:
        layer = self._layers.get(layer_id)
        parent = self._layers.get(parent_id)
        if layer is None or parent is None:
            return False
        if layer_id == parent_id:
            return False

        chain = self._resolve_layer_hierarchy(parent_id)
        if layer_id in chain:
            return False

        layer.parent_layer_id = parent_id
        return True

    def clear_parent_layer(self, layer_id: str) -> bool:
        layer = self._layers.get(layer_id)
        if layer is None:
            return False
        layer.parent_layer_id = ""
        return True

    # ---- Stats ----

    def get_stats(self) -> Dict[str, Any]:
        effect_counts: Dict[str, int] = {}
        visibility_counts: Dict[str, int] = {}
        strategy_counts: Dict[str, int] = {}
        total_entities = 0
        enabled_count = 0

        for layer in self._layers.values():
            if layer.enabled:
                enabled_count += 1
            total_entities += len(layer.entities)

            eff = layer.effect.value
            effect_counts[eff] = effect_counts.get(eff, 0) + 1

            vis = layer.visibility.value
            visibility_counts[vis] = visibility_counts.get(vis, 0) + 1

            strat = layer.sort_strategy.value
            strategy_counts[strat] = strategy_counts.get(strat, 0) + 1

        return {
            "total_layers": len(self._layers),
            "enabled_layers": enabled_count,
            "disabled_layers": len(self._layers) - enabled_count,
            "total_groups": len(self._groups),
            "total_entities_across_layers": total_entities,
            "total_layers_created": self._total_layers_created,
            "total_groups_created": self._total_groups_created,
            "total_entities_assigned": self._total_entities_assigned,
            "total_sorts_performed": self._total_sorts_performed,
            "total_sort_rules": len(self._sort_rules),
            "total_configs": len(self._configs),
            "effect_distribution": effect_counts,
            "visibility_distribution": visibility_counts,
            "sort_strategy_distribution": strategy_counts,
            "max_layers": self.MAX_LAYERS,
            "max_groups": self.MAX_GROUPS,
            "max_entities_per_layer": self.MAX_ENTITIES_PER_LAYER,
            "max_sort_rules": self.MAX_SORT_RULES,
        }

    # ---- Reset ----

    def reset(self) -> None:
        with self._lock:
            self._layers.clear()
            self._groups.clear()
            self._sort_rules.clear()
            self._configs.clear()
            self._entity_to_layer.clear()
            self._custom_comparators.clear()
            self._total_layers_created = 0
            self._total_groups_created = 0
            self._total_entities_assigned = 0
            self._total_sorts_performed = 0

    # ---- Internal Methods ----

    def _apply_sort_strategy(self,
                              entities: List[str],
                              strategy: SortStrategy) -> List[str]:
        if strategy == SortStrategy.NONE:
            return list(entities)

        if strategy == SortStrategy.CUSTOM_COMPARATOR:
            return list(entities)

        sorted_list = list(entities)
        if strategy == SortStrategy.BY_Z_ORDER:
            sorted_list.sort(
                key=lambda eid: self._compute_sort_key(
                    eid,
                    RenderSortRule(property_name="z_index", ascending=True, priority=0),
                )
            )
        elif strategy == SortStrategy.BY_Y_POSITION:
            sorted_list.sort(
                key=lambda eid: self._compute_sort_key(
                    eid,
                    RenderSortRule(property_name="y_position", ascending=True, priority=0),
                )
            )
        elif strategy == SortStrategy.BY_DEPTH:
            sorted_list.sort(
                key=lambda eid: self._compute_sort_key(
                    eid,
                    RenderSortRule(property_name="depth", ascending=True, priority=0),
                )
            )

        return sorted_list

    def _compute_sort_key(self, entity_id: str, sort_rule: RenderSortRule) -> Any:
        prop = sort_rule.property_name

        if prop == "z_index":
            layer_id = self._entity_to_layer.get(entity_id)
            if layer_id:
                layer = self._layers.get(layer_id)
                if layer:
                    return layer.z_index
            return 0

        if prop == "y_position":
            return entity_id

        if prop == "depth":
            return entity_id

        return 0

    def _apply_effect_to_entities(self, layer: RenderLayer) -> List[str]:
        if layer.effect == LayerEffect.NONE:
            return list(layer.entities)

        return list(layer.entities)

    def _resolve_layer_hierarchy(self, layer_id: str) -> List[str]:
        chain: List[str] = [layer_id]
        current_id = layer_id
        visited: Set[str] = set()

        while current_id:
            if current_id in visited:
                break
            visited.add(current_id)
            layer = self._layers.get(current_id)
            if layer is None or not layer.parent_layer_id:
                break
            chain.append(layer.parent_layer_id)
            current_id = layer.parent_layer_id

        return chain


def get_render_layer() -> RenderLayerSystem:
    return RenderLayerSystem.get_instance()