"""
SparkLabs Engine - Render Pipeline

Unified rendering pipeline for the SparkLabs AI-native game engine.
Orchestrates render passes, post-processing effects, frame composition,
and render state management for both 2D and 3D rendering.

Architecture:
  EngineRenderPipeline (Singleton)
    |-- Render Pass Manager (ordered render pass execution)
    |-- Frame Composer (composite final frame from passes)
    |-- Post-Process Stack (bloom, blur, color grading, etc.)
    |-- Render State Cache (optimize state changes)
    |-- Draw Call Batcher (batch similar draw calls)
    |-- Resolution Scaler (dynamic resolution adjustment)
    |-- Debug Overlay (render debug visualization)
"""

from __future__ import annotations

import threading
import time as _time_module
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


class RenderPassType(Enum):
    SHADOW_MAP = "shadow_map"
    DEPTH_PREPASS = "depth_prepass"
    GEOMETRY = "geometry"
    TRANSPARENT = "transparent"
    UI = "ui"
    POST_PROCESS = "post_process"
    DEBUG = "debug"
    CUSTOM = "custom"


class PostProcessEffect(Enum):
    BLOOM = "bloom"
    BLUR = "blur"
    COLOR_GRADING = "color_grading"
    VIGNETTE = "vignette"
    CHROMATIC_ABERRATION = "chromatic_aberration"
    MOTION_BLUR = "motion_blur"
    DEPTH_OF_FIELD = "depth_of_field"
    AMBIENT_OCCLUSION = "ambient_occlusion"
    FXAA = "fxaa"
    TONE_MAPPING = "tone_mapping"
    FILM_GRAIN = "film_grain"
    LENS_FLARE = "lens_flare"


class BlendMode(Enum):
    NONE = "none"
    ALPHA = "alpha"
    ADDITIVE = "additive"
    MULTIPLY = "multiply"
    SCREEN = "screen"
    OVERLAY = "overlay"


class RenderQuality(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    ULTRA = "ultra"
    CUSTOM = "custom"


class CullingMode(Enum):
    NONE = "none"
    FRUSTUM = "frustum"
    OCCLUSION = "occlusion"
    DISTANCE = "distance"


@dataclass
class RenderPass:
    """A single render pass in the pipeline."""
    pass_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    pass_type: RenderPassType = RenderPassType.GEOMETRY
    name: str = ""
    order: int = 0
    enabled: bool = True
    clear_color: Tuple[float, float, float, float] = (0.0, 0.0, 0.0, 1.0)
    clear_depth: bool = True
    blend_mode: BlendMode = BlendMode.NONE
    culling_mode: CullingMode = CullingMode.FRUSTUM
    render_target_width: int = 1920
    render_target_height: int = 1080
    shader_program: str = ""
    draw_calls: int = 0
    triangles: int = 0
    execution_time_ms: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "pass_id": self.pass_id,
            "pass_type": self.pass_type.value,
            "name": self.name,
            "order": self.order,
            "enabled": self.enabled,
            "clear_color": list(self.clear_color),
            "blend_mode": self.blend_mode.value,
            "culling_mode": self.culling_mode.value,
            "resolution": f"{self.render_target_width}x{self.render_target_height}",
            "draw_calls": self.draw_calls,
            "triangles": self.triangles,
            "execution_time_ms": self.execution_time_ms,
        }


@dataclass
class PostProcessConfig:
    """Configuration for a post-processing effect."""
    effect: PostProcessEffect
    enabled: bool = True
    intensity: float = 1.0
    properties: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "effect": self.effect.value,
            "enabled": self.enabled,
            "intensity": self.intensity,
            "properties": self.properties,
        }


@dataclass
class RenderStats:
    """Per-frame rendering statistics."""
    frame_id: int = 0
    timestamp: float = field(default_factory=_time_module.time)
    total_draw_calls: int = 0
    total_triangles: int = 0
    total_pass_execution_ms: float = 0.0
    frame_time_ms: float = 0.0
    fps: float = 0.0
    gpu_memory_mb: float = 0.0
    resolution_scale: float = 1.0
    visible_objects: int = 0
    culled_objects: int = 0
    batch_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "frame_id": self.frame_id,
            "timestamp": self.timestamp,
            "total_draw_calls": self.total_draw_calls,
            "total_triangles": self.total_triangles,
            "total_pass_execution_ms": self.total_pass_execution_ms,
            "frame_time_ms": self.frame_time_ms,
            "fps": self.fps,
            "gpu_memory_mb": self.gpu_memory_mb,
            "resolution_scale": self.resolution_scale,
            "visible_objects": self.visible_objects,
            "culled_objects": self.culled_objects,
            "batch_count": self.batch_count,
        }


class EngineRenderPipeline:
    """
    Unified rendering pipeline engine.

    Manages the complete rendering pipeline from render passes through
    post-processing to final frame output. Supports dynamic quality
    scaling, render state optimization, and comprehensive profiling.
    """

    _instance = None
    _lock = threading.RLock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if hasattr(self, "_initialized") and self._initialized:
            return
        self._initialized = True
        self._passes: Dict[str, RenderPass] = {}
        self._post_processes: List[PostProcessConfig] = []
        self._render_stats: List[RenderStats] = []
        self._frame_count: int = 0
        self._quality: RenderQuality = RenderQuality.HIGH
        self._resolution_scale: float = 1.0
        self._target_fps: int = 60
        self._current_fps: float = 60.0
        self._is_rendering: bool = False
        self._clear_color: Tuple[float, float, float, float] = (0.1, 0.1, 0.15, 1.0)

        # Initialize default render passes
        self._init_default_passes()

        # Initialize default post-process effects
        self._init_default_post_processes()

    @classmethod
    def get_instance(cls) -> "EngineRenderPipeline":
        return cls()

    def _init_default_passes(self):
        """Initialize the standard render pass pipeline."""
        default_passes = [
            (RenderPassType.SHADOW_MAP, "Shadow Map", 0),
            (RenderPassType.DEPTH_PREPASS, "Depth Prepass", 10),
            (RenderPassType.GEOMETRY, "Geometry", 20, BlendMode.ALPHA),
            (RenderPassType.TRANSPARENT, "Transparent", 30, BlendMode.ALPHA),
            (RenderPassType.UI, "UI", 40, BlendMode.ALPHA),
            (RenderPassType.POST_PROCESS, "Post Process", 50),
            (RenderPassType.DEBUG, "Debug Overlay", 60),
        ]

        for pass_type, name, order, *args in default_passes:
            blend = args[0] if args else BlendMode.NONE
            rp = RenderPass(
                pass_type=pass_type,
                name=name,
                order=order,
                blend_mode=blend,
            )
            self._passes[rp.pass_id] = rp

    def _init_default_post_processes(self):
        """Initialize default post-processing effects."""
        defaults = [
            (PostProcessEffect.TONE_MAPPING, True, 1.0),
            (PostProcessEffect.BLOOM, True, 0.5, {"threshold": 0.8, "radius": 1.0}),
            (PostProcessEffect.COLOR_GRADING, True, 0.8, {"contrast": 1.1, "saturation": 1.05}),
            (PostProcessEffect.FXAA, True, 1.0),
            (PostProcessEffect.VIGNETTE, True, 0.3, {"radius": 0.8, "softness": 0.5}),
            (PostProcessEffect.DEPTH_OF_FIELD, False, 0.0, {"focus_distance": 10.0, "aperture": 2.8}),
            (PostProcessEffect.MOTION_BLUR, False, 0.0, {"samples": 8}),
            (PostProcessEffect.CHROMATIC_ABERRATION, False, 0.0, {"offset": 1.0}),
            (PostProcessEffect.AMBIENT_OCCLUSION, False, 0.0, {"radius": 0.5, "intensity": 1.0}),
            (PostProcessEffect.FILM_GRAIN, False, 0.0, {"strength": 0.1}),
            (PostProcessEffect.LENS_FLARE, False, 0.0),
        ]

        for effect, enabled, intensity, *args in defaults:
            props = args[0] if args else {}
            self._post_processes.append(PostProcessConfig(
                effect=effect,
                enabled=enabled,
                intensity=intensity,
                properties=props,
            ))

    # ---- Render Pass Management ----

    def add_pass(
        self,
        pass_type: RenderPassType,
        name: str,
        order: int = -1,
        blend_mode: BlendMode = BlendMode.NONE,
        culling_mode: CullingMode = CullingMode.FRUSTUM,
    ) -> RenderPass:
        """Add a custom render pass."""
        with self._lock:
            if order < 0:
                order = len(self._passes) * 10

            rp = RenderPass(
                pass_type=pass_type,
                name=name,
                order=order,
                blend_mode=blend_mode,
                culling_mode=culling_mode,
            )
            self._passes[rp.pass_id] = rp
            return rp

    def remove_pass(self, pass_id: str) -> bool:
        """Remove a render pass."""
        with self._lock:
            if pass_id in self._passes:
                del self._passes[pass_id]
                return True
            return False

    def set_pass_enabled(self, pass_id: str, enabled: bool) -> bool:
        """Enable or disable a render pass."""
        with self._lock:
            rp = self._passes.get(pass_id)
            if rp:
                rp.enabled = enabled
                return True
            return False

    def get_passes(self) -> List[Dict[str, Any]]:
        """Get sorted list of render passes."""
        with self._lock:
            sorted_passes = sorted(
                self._passes.values(), key=lambda p: p.order,
            )
            return [p.to_dict() for p in sorted_passes]

    # ---- Post-Process Management ----

    def set_post_process(
        self,
        effect: PostProcessEffect,
        enabled: bool,
        intensity: Optional[float] = None,
        properties: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Configure a post-processing effect."""
        with self._lock:
            for pp in self._post_processes:
                if pp.effect == effect:
                    pp.enabled = enabled
                    if intensity is not None:
                        pp.intensity = max(0.0, min(1.0, intensity))
                    if properties is not None:
                        pp.properties.update(properties)
                    return

            # Add new effect
            self._post_processes.append(PostProcessConfig(
                effect=effect,
                enabled=enabled,
                intensity=intensity or 1.0,
                properties=properties or {},
            ))

    def get_post_processes(self) -> List[Dict[str, Any]]:
        """Get all post-process configurations."""
        return [pp.to_dict() for pp in self._post_processes]

    def get_enabled_post_processes(self) -> List[PostProcessEffect]:
        """Get list of enabled post-process effects."""
        return [
            pp.effect for pp in self._post_processes
            if pp.enabled and pp.intensity > 0.0
        ]

    # ---- Quality Management ----

    def set_quality(self, quality: RenderQuality) -> None:
        """Set global render quality preset."""
        with self._lock:
            self._quality = quality

            quality_configs = {
                RenderQuality.LOW: {
                    "resolution_scale": 0.5,
                    "shadow_resolution": 512,
                    "max_draw_distance": 500,
                    "post_process_count": 2,
                },
                RenderQuality.MEDIUM: {
                    "resolution_scale": 0.75,
                    "shadow_resolution": 1024,
                    "max_draw_distance": 1000,
                    "post_process_count": 4,
                },
                RenderQuality.HIGH: {
                    "resolution_scale": 1.0,
                    "shadow_resolution": 2048,
                    "max_draw_distance": 2000,
                    "post_process_count": 6,
                },
                RenderQuality.ULTRA: {
                    "resolution_scale": 1.0,
                    "shadow_resolution": 4096,
                    "max_draw_distance": 5000,
                    "post_process_count": 10,
                },
            }

            config = quality_configs.get(quality, quality_configs[RenderQuality.HIGH])
            self._resolution_scale = config["resolution_scale"]

            # Disable expensive post-processes for lower quality
            pp_limit = config["post_process_count"]
            enabled_count = 0
            for pp in self._post_processes:
                if pp.effect in (
                    PostProcessEffect.BLOOM,
                    PostProcessEffect.COLOR_GRADING,
                    PostProcessEffect.TONE_MAPPING,
                    PostProcessEffect.FXAA,
                ):
                    if enabled_count < pp_limit:
                        pp.enabled = True
                        enabled_count += 1
                    else:
                        pp.enabled = False

    def get_quality(self) -> str:
        return self._quality.value

    # ---- Frame Rendering ----

    def render_frame(self) -> RenderStats:
        """
        Simulate rendering a frame.

        Executes enabled render passes in order, applies post-processing,
        and collects rendering statistics.
        """
        frame_start = _time_module.time()

        total_draw_calls = 0
        total_triangles = 0
        total_pass_time = 0.0

        sorted_passes = sorted(
            [p for p in self._passes.values() if p.enabled],
            key=lambda p: p.order,
        )

        for rp in sorted_passes:
            pass_start = _time_module.time()

            # Simulate draw calls per pass type
            dc, tri = self._simulate_pass_draw_calls(rp.pass_type)
            rp.draw_calls = dc
            rp.triangles = tri
            total_draw_calls += dc
            total_triangles += tri

            rp.execution_time_ms = (_time_module.time() - pass_start) * 1000
            total_pass_time += rp.execution_time_ms

        frame_time = (_time_module.time() - frame_start) * 1000
        self._frame_count += 1

        # Calculate FPS
        if frame_time > 0:
            self._current_fps = 1000.0 / frame_time

        # Dynamic resolution scaling
        if self._quality != RenderQuality.ULTRA:
            self._adjust_resolution_scale()

        stats = RenderStats(
            frame_id=self._frame_count,
            total_draw_calls=total_draw_calls,
            total_triangles=total_triangles,
            total_pass_execution_ms=total_pass_time,
            frame_time_ms=frame_time,
            fps=self._current_fps,
            resolution_scale=self._resolution_scale,
            visible_objects=total_draw_calls,
            culled_objects=max(0, total_draw_calls * 2),
            batch_count=total_draw_calls // 3,
        )
        self._render_stats.append(stats)

        if len(self._render_stats) > 600:
            self._render_stats = self._render_stats[-300:]

        return stats

    def _simulate_pass_draw_calls(self, pass_type: RenderPassType) -> Tuple[int, int]:
        """Simulate draw calls for a render pass type."""
        base = {
            RenderPassType.SHADOW_MAP: (50, 5000),
            RenderPassType.DEPTH_PREPASS: (100, 10000),
            RenderPassType.GEOMETRY: (200, 50000),
            RenderPassType.TRANSPARENT: (30, 3000),
            RenderPassType.UI: (20, 1000),
            RenderPassType.POST_PROCESS: (1, 6),
            RenderPassType.DEBUG: (10, 500),
            RenderPassType.CUSTOM: (25, 2500),
        }
        scale = int(self._resolution_scale * 100)
        dc, tri = base.get(pass_type, (10, 1000))
        return (dc * scale // 100, tri * scale // 100)

    def _adjust_resolution_scale(self):
        """Dynamically adjust resolution scale to maintain target FPS."""
        if self._current_fps < self._target_fps * 0.8:
            self._resolution_scale = max(0.5, self._resolution_scale - 0.05)
        elif self._current_fps > self._target_fps * 1.2:
            self._resolution_scale = min(1.0, self._resolution_scale + 0.02)

    # ---- Stats and Profiling ----

    def get_latest_stats(self) -> Optional[Dict[str, Any]]:
        """Get the most recent frame statistics."""
        if self._render_stats:
            return self._render_stats[-1].to_dict()
        return None

    def get_stats_history(self, limit: int = 60) -> List[Dict[str, Any]]:
        """Get recent frame statistics history."""
        return [s.to_dict() for s in self._render_stats[-limit:]]

    def get_average_stats(self) -> Dict[str, Any]:
        """Get average rendering statistics."""
        if not self._render_stats:
            return {}

        count = len(self._render_stats)
        avg_fps = sum(s.fps for s in self._render_stats) / count
        avg_frame_time = sum(s.frame_time_ms for s in self._render_stats) / count
        avg_draw_calls = sum(s.total_draw_calls for s in self._render_stats) / count
        avg_triangles = sum(s.total_triangles for s in self._render_stats) / count

        return {
            "average_fps": round(avg_fps, 1),
            "average_frame_time_ms": round(avg_frame_time, 2),
            "average_draw_calls": int(avg_draw_calls),
            "average_triangles": int(avg_triangles),
            "frame_count": count,
            "resolution_scale": self._resolution_scale,
            "quality": self._quality.value,
        }

    def get_stats(self) -> Dict[str, Any]:
        """Get comprehensive pipeline statistics."""
        with self._lock:
            return {
                "frame_count": self._frame_count,
                "current_fps": round(self._current_fps, 1),
                "target_fps": self._target_fps,
                "quality": self._quality.value,
                "resolution_scale": self._resolution_scale,
                "render_passes": len(self._passes),
                "enabled_passes": sum(1 for p in self._passes.values() if p.enabled),
                "post_processes": len(self._post_processes),
                "enabled_post_processes": len(self.get_enabled_post_processes()),
                "is_rendering": self._is_rendering,
                "average_stats": self.get_average_stats(),
            }

    def start_rendering(self) -> None:
        self._is_rendering = True

    def stop_rendering(self) -> None:
        self._is_rendering = False

    def set_target_fps(self, fps: int) -> None:
        self._target_fps = max(30, min(240, fps))


# Module-level accessor
_render_pipeline: Optional[EngineRenderPipeline] = None


def get_render_pipeline() -> EngineRenderPipeline:
    global _render_pipeline
    if _render_pipeline is None:
        _render_pipeline = EngineRenderPipeline()
    return _render_pipeline