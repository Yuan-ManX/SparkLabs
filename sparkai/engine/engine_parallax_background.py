"""
SparkLabs Engine - Parallax Background System

Multi-layer parallax scrolling system with auto-tiling, camera tracking,
and smooth scene transitions. Each parallax layer scrolls at independent
rates relative to the camera, creating depth illusion in 2D scenes.
Supports auto-scrolling layers, tint/tint opacity, and configurable
tiling modes with seamless repetition.

Architecture:
  ParallaxBackgroundSystem
    |-- ParallaxLayer (texture-backed layer with scroll/tile params)
    |-- ParallaxScene (collection of ordered layers + camera binding)
    |-- ParallaxConfig (global parallax settings and smoothing)

Scroll Pipeline:
  1. Receive camera position from the active scene's camera entity
  2. For each enabled layer, compute parallax offset
  3. Apply auto-scroll delta if configured
  4. Generate tile UV offsets for the current viewport
  5. Perform cross-scene transition interpolation when active
"""

from __future__ import annotations

import math
import threading
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


class ScrollDirection(Enum):
    """Axis constraints for layer scrolling relative to camera movement."""
    HORIZONTAL = "horizontal"
    VERTICAL = "vertical"
    BOTH = "both"
    CUSTOM = "custom"


class RepeatMode(Enum):
    """Texture repetition strategy when the viewport exceeds the source image."""
    TILE = "tile"
    STRETCH = "stretch"
    CLAMP = "clamp"
    MIRROR_TILE = "mirror_tile"


class ParallaxMode(Enum):
    """Mathematical model for computing per-layer offset from camera position."""
    SCROLL_SPEED_MULTIPLIER = "scroll_speed_multiplier"
    FIXED_DISTANCE = "fixed_distance"
    DEPTH_BASED = "depth_based"
    CUSTOM_OFFSET = "custom_offset"


class LayerTransition(Enum):
    """Visual interpolation style when swapping between parallax scenes."""
    INSTANT = "instant"
    FADE = "fade"
    SLIDE = "slide"
    ZOOM = "zoom"
    CROSSFADE = "crossfade"


@dataclass
class ParallaxLayer:
    """A single scrollable background layer with texture and motion parameters.

    Each layer scrolls independently based on its parallax factor, which
    determines how much it moves relative to the camera. A factor of 0.0
    means the layer is fixed (distant background), while 1.0 means it
    moves in lockstep with the camera (foreground).
    """

    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = ""
    texture_ref: str = ""
    scroll_direction: ScrollDirection = ScrollDirection.HORIZONTAL
    parallax_factor: float = 0.5
    repeat_mode: RepeatMode = RepeatMode.TILE
    offset: Tuple[float, float] = (0.0, 0.0)
    z_index: int = 0
    tint_color: Tuple[float, float, float, float] = (1.0, 1.0, 1.0, 1.0)
    opacity: float = 1.0
    auto_scroll_speed: Tuple[float, float] = (0.0, 0.0)
    enabled: bool = True
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "texture_ref": self.texture_ref,
            "scroll_direction": self.scroll_direction.value,
            "parallax_factor": self.parallax_factor,
            "repeat_mode": self.repeat_mode.value,
            "offset": list(self.offset),
            "z_index": self.z_index,
            "tint_color": list(self.tint_color),
            "opacity": self.opacity,
            "auto_scroll_speed": list(self.auto_scroll_speed),
            "enabled": self.enabled,
            "created_at": self.created_at,
        }


@dataclass
class ParallaxScene:
    """A named collection of ordered parallax layers bound to a camera.

    Scenes group layers together and associate them with a camera entity.
    Only one scene is active at a time, but transition interpolation
    allows smooth crossfading between scenes.
    """

    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = ""
    layers: List[str] = field(default_factory=list)
    camera_entity_id: str = ""
    base_scroll_speed: float = 1.0
    width: float = 1920.0
    height: float = 1080.0
    transition: Optional[LayerTransition] = None
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "layer_count": len(self.layers),
            "camera_entity_id": self.camera_entity_id,
            "base_scroll_speed": self.base_scroll_speed,
            "dimensions": [self.width, self.height],
            "transition": self.transition.value if self.transition else None,
            "created_at": self.created_at,
        }


@dataclass
class ParallaxConfig:
    """Global parallax system settings shared across all scenes and layers."""

    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = ""
    scenes: List[str] = field(default_factory=list)
    global_scroll_speed: float = 1.0
    smoothing_enabled: bool = True
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "scene_count": len(self.scenes),
            "global_scroll_speed": self.global_scroll_speed,
            "smoothing_enabled": self.smoothing_enabled,
            "created_at": self.created_at,
        }


class ParallaxBackgroundSystem:
    """
    Multi-layer parallax scrolling with camera tracking and scene transitions.

    Manages layered background textures that scroll at independent rates
    to simulate depth in 2D scenes. Supports auto-tiling, mirror tiling,
    tinting/fading, and smooth scene-to-scene transitions.

    Usage:
        system = get_parallax_background()
        sky = system.create_layer("sky", "tex_sky_01", 0.1, "horizontal")
        mountains = system.create_layer("mountains", "tex_mt_01", 0.4, "horizontal")
        scene = system.create_scene("forest", "main_cam", 1920, 1080)
        system.add_layer_to_scene(scene.id, sky.id)
        system.add_layer_to_scene(scene.id, mountains.id)
        offsets = system.update_scroll((cam_x, cam_y), scene.id)
    """

    _instance: Optional["ParallaxBackgroundSystem"] = None
    _lock: threading.RLock = threading.RLock()

    MAX_LAYERS_PER_SCENE = 64
    MAX_SCENES = 32
    MAX_CONFIGS = 16
    DEFAULT_SMOOTHING_FACTOR = 0.15

    def __new__(cls) -> "ParallaxBackgroundSystem":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self) -> None:
        if self._initialized:
            return
        self._initialized = True

        self._layers: Dict[str, ParallaxLayer] = {}
        self._scenes: Dict[str, ParallaxScene] = {}
        self._configs: Dict[str, ParallaxConfig] = {}
        self._camera_positions: Dict[str, Tuple[float, float]] = {}
        self._smoothed_positions: Dict[str, Tuple[float, float]] = {}
        self._active_transitions: Dict[str, Dict[str, Any]] = {}
        self._tile_cache: Dict[str, List[Dict[str, Any]]] = {}

        self._total_layers_created: int = 0
        self._total_scenes_created: int = 0
        self._total_transitions: int = 0
        self._total_scroll_updates: int = 0

    @classmethod
    def get_instance(cls) -> "ParallaxBackgroundSystem":
        return cls()

    # ------------------------------------------------------------------
    # Layer Management
    # ------------------------------------------------------------------

    def create_layer(
        self,
        name: str,
        texture_ref: str,
        parallax_factor: float = 0.5,
        scroll_direction: str = "horizontal",
    ) -> ParallaxLayer:
        try:
            sd = ScrollDirection(scroll_direction.lower())
        except ValueError:
            sd = ScrollDirection.HORIZONTAL

        layer = ParallaxLayer(
            name=name,
            texture_ref=texture_ref,
            parallax_factor=max(0.0, min(2.0, parallax_factor)),
            scroll_direction=sd,
            z_index=len(self._layers),
        )
        self._layers[layer.id] = layer
        self._total_layers_created += 1
        return layer

    def get_layer(self, layer_id: str) -> Optional[ParallaxLayer]:
        return self._layers.get(layer_id)

    def find_layer_by_name(self, name: str) -> Optional[ParallaxLayer]:
        for layer in self._layers.values():
            if layer.name.lower() == name.lower():
                return layer
        return None

    def remove_layer(self, layer_id: str) -> bool:
        if layer_id not in self._layers:
            return False
        for scene in self._scenes.values():
            if layer_id in scene.layers:
                scene.layers.remove(layer_id)
        del self._layers[layer_id]
        self._tile_cache.pop(layer_id, None)
        return True

    def configure_layer(self, layer_id: str, **params: Any) -> Optional[ParallaxLayer]:
        layer = self._layers.get(layer_id)
        if layer is None:
            return None

        if "name" in params:
            layer.name = str(params["name"])
        if "texture_ref" in params:
            layer.texture_ref = str(params["texture_ref"])
        if "scroll_direction" in params:
            try:
                layer.scroll_direction = ScrollDirection(
                    str(params["scroll_direction"]).lower()
                )
            except ValueError:
                pass
        if "parallax_factor" in params:
            layer.parallax_factor = max(0.0, min(2.0, float(params["parallax_factor"])))
        if "repeat_mode" in params:
            try:
                layer.repeat_mode = RepeatMode(
                    str(params["repeat_mode"]).lower()
                )
            except ValueError:
                pass
        if "offset" in params:
            off = params["offset"]
            if isinstance(off, (list, tuple)) and len(off) >= 2:
                layer.offset = (float(off[0]), float(off[1]))
        if "z_index" in params:
            layer.z_index = int(params["z_index"])
        if "opacity" in params:
            layer.opacity = max(0.0, min(1.0, float(params["opacity"])))
        if "auto_scroll_speed" in params:
            spd = params["auto_scroll_speed"]
            if isinstance(spd, (list, tuple)) and len(spd) >= 2:
                layer.auto_scroll_speed = (float(spd[0]), float(spd[1]))
        if "enabled" in params:
            layer.enabled = bool(params["enabled"])

        return layer

    def set_auto_scroll(
        self,
        layer_id: str,
        speed_x: float = 0.0,
        speed_y: float = 0.0,
    ) -> Optional[ParallaxLayer]:
        layer = self._layers.get(layer_id)
        if layer is None:
            return None

        layer.auto_scroll_speed = (float(speed_x), float(speed_y))
        return layer

    def set_layer_tint(
        self,
        layer_id: str,
        color: Tuple[float, float, float, float],
        opacity: Optional[float] = None,
    ) -> Optional[ParallaxLayer]:
        layer = self._layers.get(layer_id)
        if layer is None:
            return None

        if len(color) >= 4:
            layer.tint_color = (
                max(0.0, min(1.0, color[0])),
                max(0.0, min(1.0, color[1])),
                max(0.0, min(1.0, color[2])),
                max(0.0, min(1.0, color[3])),
            )
        elif len(color) >= 3:
            layer.tint_color = (
                max(0.0, min(1.0, color[0])),
                max(0.0, min(1.0, color[1])),
                max(0.0, min(1.0, color[2])),
                layer.tint_color[3],
            )

        if opacity is not None:
            layer.opacity = max(0.0, min(1.0, opacity))

        return layer

    def export_layer_config(self, layer_id: str) -> Dict[str, Any]:
        layer = self._layers.get(layer_id)
        if layer is None:
            return {}
        return layer.to_dict()

    # ------------------------------------------------------------------
    # Scene Management
    # ------------------------------------------------------------------

    def create_scene(
        self,
        name: str,
        camera_entity_id: str,
        width: float = 1920.0,
        height: float = 1080.0,
    ) -> ParallaxScene:
        if len(self._scenes) >= self.MAX_SCENES:
            raise RuntimeError(
                f"Scene limit reached ({self.MAX_SCENES}). "
                "Remove unused scenes before creating new ones."
            )

        scene = ParallaxScene(
            name=name,
            camera_entity_id=camera_entity_id,
            width=max(1.0, width),
            height=max(1.0, height),
        )
        self._scenes[scene.id] = scene
        self._total_scenes_created += 1
        return scene

    def get_scene(self, scene_id: str) -> Optional[ParallaxScene]:
        return self._scenes.get(scene_id)

    def find_scene_by_name(self, name: str) -> Optional[ParallaxScene]:
        for scene in self._scenes.values():
            if scene.name.lower() == name.lower():
                return scene
        return None

    def remove_scene(self, scene_id: str) -> bool:
        if scene_id not in self._scenes:
            return False
        del self._scenes[scene_id]
        self._active_transitions.pop(scene_id, None)
        return True

    def add_layer_to_scene(self, scene_id: str, layer_id: str) -> bool:
        scene = self._scenes.get(scene_id)
        layer = self._layers.get(layer_id)
        if scene is None or layer is None:
            return False
        if len(scene.layers) >= self.MAX_LAYERS_PER_SCENE:
            return False
        if layer_id not in scene.layers:
            scene.layers.append(layer_id)
        return True

    def remove_layer_from_scene(self, scene_id: str, layer_id: str) -> bool:
        scene = self._scenes.get(scene_id)
        if scene is None:
            return False
        if layer_id in scene.layers:
            scene.layers.remove(layer_id)
            return True
        return False

    def reorder_layers(self, scene_id: str, layer_order: List[str]) -> bool:
        scene = self._scenes.get(scene_id)
        if scene is None:
            return False

        existing_set = set(scene.layers)
        requested_set = set(layer_order)

        if existing_set != requested_set:
            return False
        if len(layer_order) != len(scene.layers):
            return False

        scene.layers = list(layer_order)
        for idx, lid in enumerate(scene.layers):
            layer = self._layers.get(lid)
            if layer is not None:
                layer.z_index = idx

        return True

    def clone_scene(self, scene_id: str, new_name: str) -> Optional[ParallaxScene]:
        source = self._scenes.get(scene_id)
        if source is None:
            return None

        if len(self._scenes) >= self.MAX_SCENES:
            return None

        clone = ParallaxScene(
            name=new_name,
            layers=list(source.layers),
            camera_entity_id=source.camera_entity_id,
            base_scroll_speed=source.base_scroll_speed,
            width=source.width,
            height=source.height,
            transition=source.transition,
        )
        self._scenes[clone.id] = clone
        self._total_scenes_created += 1
        return clone

    # ------------------------------------------------------------------
    # Scroll and Offset Computation
    # ------------------------------------------------------------------

    def update_scroll(
        self,
        camera_position: Tuple[float, float],
        scene_id: str,
    ) -> Dict[str, Tuple[float, float]]:
        scene = self._scenes.get(scene_id)
        if scene is None:
            return {}

        cam_x, cam_y = camera_position
        now = time.time()

        smoothed = self._smoothed_positions.get(scene_id, (cam_x, cam_y))
        if self._get_global_smoothing():
            factor = self.DEFAULT_SMOOTHING_FACTOR
            sx = smoothed[0] + (cam_x - smoothed[0]) * factor
            sy = smoothed[1] + (cam_y - smoothed[1]) * factor
        else:
            sx, sy = cam_x, cam_y

        self._smoothed_positions[scene_id] = (sx, sy)
        self._camera_positions[scene.camera_entity_id] = (sx, sy)

        layer_offsets: Dict[str, Tuple[float, float]] = {}
        ordered_layers = sorted(
            scene.layers,
            key=lambda lid: self._layers[lid].z_index
            if lid in self._layers else 0,
        )

        for layer_id in ordered_layers:
            layer = self._layers.get(layer_id)
            if layer is None or not layer.enabled:
                continue

            offset = self._calculate_offset(layer, (sx, sy), now)
            layer_offsets[layer_id] = offset

        self._total_scroll_updates += 1

        active_transition = self._active_transitions.get(scene_id)
        if active_transition is not None:
            elapsed = now - active_transition["start_time"]
            total_duration = active_transition["duration"]
            if elapsed >= total_duration:
                self._active_transitions.pop(scene_id, None)
            else:
                progress = min(1.0, elapsed / max(total_duration, 0.001))
                interpolated = {}
                for lid, offset in layer_offsets.items():
                    start_off = active_transition["start_offsets"].get(
                        lid, (0.0, 0.0)
                    )
                    interp_x = self._interpolate_value(
                        start_off[0], offset[0], progress,
                        active_transition.get("easing", "linear"),
                    )
                    interp_y = self._interpolate_value(
                        start_off[1], offset[1], progress,
                        active_transition.get("easing", "linear"),
                    )
                    interpolated[lid] = (interp_x, interp_y)
                return interpolated

        return layer_offsets

    def _calculate_offset(
        self,
        layer: ParallaxLayer,
        camera_pos: Tuple[float, float],
        current_time: float,
    ) -> Tuple[float, float]:
        cam_x, cam_y = camera_pos
        factor = layer.parallax_factor

        base_ox = cam_x * factor + layer.offset[0]
        base_oy = cam_y * factor + layer.offset[1]

        auto_x, auto_y = layer.auto_scroll_speed
        if auto_x != 0.0 or auto_y != 0.0:
            base_ox += auto_x * current_time
            base_oy += auto_y * current_time

        sd = layer.scroll_direction
        if sd == ScrollDirection.HORIZONTAL:
            base_oy = layer.offset[1]
        elif sd == ScrollDirection.VERTICAL:
            base_ox = layer.offset[0]

        return (base_ox, base_oy)

    def _render_tiles(
        self,
        layer: ParallaxLayer,
        offset: Tuple[float, float],
        viewport: Tuple[float, float, float, float],
    ) -> List[Dict[str, Any]]:
        vx, vy, vw, vh = viewport
        ox, oy = offset

        tile_width = 256.0
        tile_height = 256.0

        if layer.repeat_mode == RepeatMode.STRETCH:
            return [{
                "x": vx + ox,
                "y": vy + oy,
                "width": vw,
                "height": vh,
                "uv_offset": (0.0, 0.0),
                "uv_scale": (1.0, 1.0),
            }]
        elif layer.repeat_mode == RepeatMode.CLAMP:
            return [{
                "x": vx + ox,
                "y": vy + oy,
                "width": tile_width,
                "height": tile_height,
                "uv_offset": (0.0, 0.0),
                "uv_scale": (1.0, 1.0),
            }]

        tiles: List[Dict[str, Any]] = []
        start_x = math.floor((vx + ox) / tile_width) * tile_width
        start_y = math.floor((vy + oy) / tile_height) * tile_height
        end_x = vx + ox + vw
        end_y = vy + oy + vh

        tx = start_x
        col = 0
        while tx < end_x:
            ty = start_y
            row = 0
            while ty < end_y:
                uv_offset = (0.0, 0.0)
                if layer.repeat_mode == RepeatMode.MIRROR_TILE:
                    uv_offset = (
                        1.0 if col % 2 == 1 else 0.0,
                        1.0 if row % 2 == 1 else 0.0,
                    )

                tiles.append({
                    "x": tx,
                    "y": ty,
                    "width": tile_width,
                    "height": tile_height,
                    "uv_offset": uv_offset,
                    "uv_scale": (1.0, 1.0),
                })
                ty += tile_height
                row += 1
            tx += tile_width
            col += 1

        return tiles

    def get_layer_tiles(
        self,
        layer_id: str,
        offset: Tuple[float, float],
        viewport: Tuple[float, float, float, float],
    ) -> List[Dict[str, Any]]:
        layer = self._layers.get(layer_id)
        if layer is None:
            return []
        return self._render_tiles(layer, offset, viewport)

    # ------------------------------------------------------------------
    # Scene Transitions
    # ------------------------------------------------------------------

    def transition_scene(
        self,
        current_scene_id: str,
        next_scene_id: str,
        transition_type: str = "fade",
        duration: float = 1.0,
    ) -> bool:
        current = self._scenes.get(current_scene_id)
        next_scene = self._scenes.get(next_scene_id)
        if current is None or next_scene is None:
            return False

        try:
            tt = LayerTransition(transition_type.lower())
        except ValueError:
            tt = LayerTransition.FADE

        current_layers = current.layers
        start_offsets: Dict[str, Tuple[float, float]] = {}
        for lid in current_layers:
            layer = self._layers.get(lid)
            if layer is not None:
                start_offsets[lid] = layer.offset

        current.transition = tt
        self._active_transitions[next_scene_id] = {
            "from_scene_id": current_scene_id,
            "transition_type": tt.value,
            "duration": max(0.01, duration),
            "start_time": time.time(),
            "start_offsets": start_offsets,
            "current_progress": 0.0,
            "easing": "ease_in_out",
        }
        self._total_transitions += 1
        return True

    def get_active_transition(
        self, scene_id: str
    ) -> Optional[Dict[str, Any]]:
        return self._active_transitions.get(scene_id)

    def cancel_transition(self, scene_id: str) -> bool:
        if scene_id in self._active_transitions:
            del self._active_transitions[scene_id]
            return True
        return False

    def _interpolate_value(
        self,
        start: float,
        end: float,
        progress: float,
        easing: str = "linear",
    ) -> float:
        t = max(0.0, min(1.0, progress))

        if easing == "ease_in":
            t = t * t
        elif easing == "ease_out":
            t = t * (2.0 - t)
        elif easing == "ease_in_out":
            if t < 0.5:
                t = 2.0 * t * t
            else:
                t = -1.0 + (4.0 - 2.0 * t) * t

        return start + (end - start) * t

    # ------------------------------------------------------------------
    # Config Management
    # ------------------------------------------------------------------

    def create_config(
        self,
        name: str,
        global_scroll_speed: float = 1.0,
        smoothing_enabled: bool = True,
    ) -> ParallaxConfig:
        if len(self._configs) >= self.MAX_CONFIGS:
            raise RuntimeError(
                f"Config limit reached ({self.MAX_CONFIGS})."
            )

        config = ParallaxConfig(
            name=name,
            global_scroll_speed=max(0.01, global_scroll_speed),
            smoothing_enabled=smoothing_enabled,
        )
        self._configs[config.id] = config
        return config

    def get_config(self, config_id: str) -> Optional[ParallaxConfig]:
        return self._configs.get(config_id)

    def add_scene_to_config(self, config_id: str, scene_id: str) -> bool:
        config = self._configs.get(config_id)
        scene = self._scenes.get(scene_id)
        if config is None or scene is None:
            return False
        if scene_id not in config.scenes:
            config.scenes.append(scene_id)
        return True

    def set_global_scroll_speed(self, config_id: str, speed: float) -> bool:
        config = self._configs.get(config_id)
        if config is None:
            return False
        config.global_scroll_speed = max(0.01, speed)
        return True

    def set_smoothing(self, config_id: str, enabled: bool) -> bool:
        config = self._configs.get(config_id)
        if config is None:
            return False
        config.smoothing_enabled = enabled
        return True

    def _get_global_smoothing(self) -> bool:
        for config in self._configs.values():
            if config.smoothing_enabled:
                return True
        return False

    def _get_global_scroll_speed(self) -> float:
        for config in self._configs.values():
            return config.global_scroll_speed
        return 1.0

    # ------------------------------------------------------------------
    # Camera Tracking
    # ------------------------------------------------------------------

    def set_camera_position(
        self, camera_entity_id: str, position: Tuple[float, float]
    ) -> None:
        self._camera_positions[camera_entity_id] = (
            float(position[0]), float(position[1])
        )

    def get_camera_position(
        self, camera_entity_id: str
    ) -> Optional[Tuple[float, float]]:
        return self._camera_positions.get(camera_entity_id)

    # ------------------------------------------------------------------
    # Utility Methods
    # ------------------------------------------------------------------

    def get_layer_count(self) -> int:
        return len(self._layers)

    def get_scene_count(self) -> int:
        return len(self._scenes)

    def list_layers(self) -> List[ParallaxLayer]:
        return list(self._layers.values())

    def list_scenes(self) -> List[ParallaxScene]:
        return list(self._scenes.values())

    def list_configs(self) -> List[ParallaxConfig]:
        return list(self._configs.values())

    # ------------------------------------------------------------------
    # Stats and Reset
    # ------------------------------------------------------------------

    def get_stats(self) -> Dict[str, Any]:
        total_layers = len(self._layers)
        enabled_layers = sum(1 for l in self._layers.values() if l.enabled)
        total_scenes = len(self._scenes)

        layer_per_scene: Dict[str, int] = {}
        for sid, scene in self._scenes.items():
            layer_per_scene[sid] = len(scene.layers)

        avg_layers_per_scene = 0.0
        if total_scenes > 0:
            avg_layers_per_scene = sum(
                layer_per_scene.values()
            ) / total_scenes

        direction_counts: Dict[str, int] = {}
        for layer in self._layers.values():
            sd = layer.scroll_direction.value
            direction_counts[sd] = direction_counts.get(sd, 0) + 1

        auto_scroll_count = sum(
            1 for l in self._layers.values()
            if l.auto_scroll_speed[0] != 0.0 or l.auto_scroll_speed[1] != 0.0
        )

        active_transition_count = len(self._active_transitions)

        return {
            "total_layers": total_layers,
            "enabled_layers": enabled_layers,
            "total_scenes": total_scenes,
            "max_scenes": self.MAX_SCENES,
            "max_layers_per_scene": self.MAX_LAYERS_PER_SCENE,
            "total_configs": len(self._configs),
            "max_configs": self.MAX_CONFIGS,
            "total_layers_created": self._total_layers_created,
            "total_scenes_created": self._total_scenes_created,
            "total_transitions": self._total_transitions,
            "total_scroll_updates": self._total_scroll_updates,
            "average_layers_per_scene": round(avg_layers_per_scene, 1),
            "scroll_direction_distribution": direction_counts,
            "auto_scroll_layers": auto_scroll_count,
            "active_transitions": active_transition_count,
            "tracked_cameras": len(self._camera_positions),
        }

    def reset(self) -> None:
        with self._lock:
            self._layers.clear()
            self._scenes.clear()
            self._configs.clear()
            self._camera_positions.clear()
            self._smoothed_positions.clear()
            self._active_transitions.clear()
            self._tile_cache.clear()
            self._total_layers_created = 0
            self._total_scenes_created = 0
            self._total_transitions = 0
            self._total_scroll_updates = 0


def get_parallax_background() -> ParallaxBackgroundSystem:
    """Return the global ParallaxBackgroundSystem singleton instance."""
    return ParallaxBackgroundSystem.get_instance()