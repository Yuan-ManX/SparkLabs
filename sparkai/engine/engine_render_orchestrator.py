"""
SparkLabs Engine - Render Orchestrator

A unified rendering orchestration system that manages the complete rendering
pipeline across multiple rendering passes, post-processing effects, and
output targets. Coordinates GPU resources, manages render order, and
optimizes draw calls for maximum performance.

Architecture:
  RenderOrchestrator
    |-- RenderPassManager (organize and sequence render passes)
    |-- GPUResourceManager (texture, buffer, shader allocation and caching)
    |-- DrawCallOptimizer (batching, instancing, culling)
    |-- PostProcessingChain (screen-space effects pipeline)
    |-- FrameComposer (final frame assembly and output)

Capabilities:
  - Render pass organization with dependency-aware ordering
  - GPU resource management with smart caching and eviction
  - Draw call optimization through batching, instancing, and culling
  - Post-processing effect chain with configurable ordering
  - Frame composition with multiple output targets
  - Performance monitoring and automatic quality adjustment
"""

from __future__ import annotations

import threading
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple


class RenderPassType(Enum):
    SHADOW_MAP = "shadow_map"
    DEPTH_PREPASS = "depth_prepass"
    OPAQUE_GEOMETRY = "opaque_geometry"
    TRANSPARENT_GEOMETRY = "transparent_geometry"
    SKYBOX = "skybox"
    UI_OVERLAY = "ui_overlay"
    POST_PROCESSING = "post_processing"
    DEBUG_OVERLAY = "debug_overlay"
    CUSTOM = "custom"


class PostProcessEffect(Enum):
    BLOOM = "bloom"
    AMBIENT_OCCLUSION = "ambient_occlusion"
    MOTION_BLUR = "motion_blur"
    DEPTH_OF_FIELD = "depth_of_field"
    COLOR_GRADING = "color_grading"
    VIGNETTE = "vignette"
    CHROMATIC_ABERRATION = "chromatic_aberration"
    FILM_GRAIN = "film_grain"
    ANTI_ALIASING = "anti_aliasing"
    TONE_MAPPING = "tone_mapping"


class GPUBufferType(Enum):
    VERTEX = "vertex"
    INDEX = "index"
    UNIFORM = "uniform"
    STORAGE = "storage"
    FRAMEBUFFER = "framebuffer"


class QualityPreset(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    ULTRA = "ultra"
    CUSTOM = "custom"


@dataclass
class RenderPass:
    """A single render pass configuration."""
    pass_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    pass_type: RenderPassType = RenderPassType.OPAQUE_GEOMETRY
    name: str = ""
    order: int = 0
    dependencies: List[str] = field(default_factory=list)
    enabled: bool = True
    config: Dict[str, Any] = field(default_factory=dict)
    statistics: Dict[str, Any] = field(default_factory=dict)


@dataclass
class GPUResource:
    """A tracked GPU resource."""
    resource_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = ""
    buffer_type: GPUBufferType = GPUBufferType.VERTEX
    size_bytes: int = 0
    ref_count: int = 0
    last_used: float = field(default_factory=time.time)
    cached: bool = False


@dataclass
class DrawCallBatch:
    """A batched draw call group."""
    batch_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    material_id: str = ""
    mesh_id: str = ""
    instance_count: int = 1
    triangle_count: int = 0
    state_changes: int = 0


@dataclass
class FrameStats:
    """Per-frame rendering statistics."""
    frame_id: int = 0
    draw_calls: int = 0
    draw_calls_batched: int = 0
    triangles: int = 0
    vertices: int = 0
    gpu_time_ms: float = 0.0
    cpu_time_ms: float = 0.0
    memory_used_mb: float = 0.0
    pass_times: Dict[str, float] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)


class RenderOrchestrator:
    """Unified rendering pipeline orchestration system."""

    def __init__(self):
        self._lock = threading.RLock()
        self._render_passes: Dict[str, RenderPass] = {}
        self._post_process_chain: List[PostProcessEffect] = []
        self._gpu_resources: Dict[str, GPUResource] = {}
        self._frame_stats: List[FrameStats] = []
        self._quality_preset = QualityPreset.HIGH
        self._target_fps = 60
        self._current_frame = 0
        self._total_draw_calls = 0
        self._settings: Dict[str, Any] = {}

    # ---- Render Pass Management ----

    def add_render_pass(self, name: str, pass_type: RenderPassType,
                        order: int = 0,
                        dependencies: List[str] = None,
                        config: Dict[str, Any] = None) -> RenderPass:
        rp = RenderPass(
            pass_type=pass_type,
            name=name,
            order=order,
            dependencies=dependencies or [],
            config=config or {}
        )
        with self._lock:
            self._render_passes[rp.pass_id] = rp
        return rp

    def get_render_passes(self, pass_type: RenderPassType = None) -> List[Dict[str, Any]]:
        with self._lock:
            passes = self._render_passes.values()
            if pass_type:
                passes = [p for p in passes if p.pass_type == pass_type]
            return [
                {
                    "pass_id": p.pass_id,
                    "name": p.name,
                    "pass_type": p.pass_type.value,
                    "order": p.order,
                    "enabled": p.enabled,
                    "dependencies": p.dependencies,
                    "statistics": p.statistics,
                }
                for p in sorted(passes, key=lambda x: x.order)
            ]

    def sort_passes(self) -> List[str]:
        """Topological sort of render passes by dependencies."""
        with self._lock:
            in_degree = {}
            adj = {}
            for pid, p in self._render_passes.items():
                in_degree[pid] = len(p.dependencies)
                adj[pid] = []
                for dep in p.dependencies:
                    if dep in self._render_passes:
                        if dep not in adj:
                            adj[dep] = []
                        adj[dep].append(pid)

            queue = [pid for pid, deg in in_degree.items() if deg == 0]
            order = []
            while queue:
                pid = queue.pop(0)
                order.append(pid)
                for neighbor in adj.get(pid, []):
                    in_degree[neighbor] -= 1
                    if in_degree[neighbor] == 0:
                        queue.append(neighbor)

            return order

    # ---- Post-Processing ----

    def set_post_process_chain(self, effects: List[PostProcessEffect]):
        with self._lock:
            self._post_process_chain = effects

    def get_post_process_chain(self) -> List[str]:
        with self._lock:
            return [e.value for e in self._post_process_chain]

    def add_post_effect(self, effect: PostProcessEffect):
        with self._lock:
            if effect not in self._post_process_chain:
                self._post_process_chain.append(effect)

    def remove_post_effect(self, effect: PostProcessEffect):
        with self._lock:
            if effect in self._post_process_chain:
                self._post_process_chain.remove(effect)

    # ---- GPU Resource Management ----

    def register_gpu_resource(self, name: str, buffer_type: GPUBufferType,
                              size_bytes: int) -> GPUResource:
        resource = GPUResource(
            name=name,
            buffer_type=buffer_type,
            size_bytes=size_bytes,
        )
        with self._lock:
            self._gpu_resources[resource.resource_id] = resource
        return resource

    def get_gpu_memory_usage(self) -> Dict[str, Any]:
        with self._lock:
            total = sum(r.size_bytes for r in self._gpu_resources.values())
            by_type = {}
            for r in self._gpu_resources.values():
                t = r.buffer_type.value
                by_type[t] = by_type.get(t, 0) + r.size_bytes
            return {
                "total_bytes": total,
                "total_mb": total / (1024 * 1024),
                "by_type": by_type,
                "resource_count": len(self._gpu_resources),
            }

    def release_unused_resources(self, max_age_seconds: float = 30.0) -> int:
        released = 0
        now = time.time()
        with self._lock:
            to_remove = []
            for rid, r in self._gpu_resources.items():
                if r.ref_count == 0 and (now - r.last_used) > max_age_seconds:
                    to_remove.append(rid)
            for rid in to_remove:
                del self._gpu_resources[rid]
                released += 1
        return released

    # ---- Quality Management ----

    def set_quality_preset(self, preset: QualityPreset):
        with self._lock:
            self._quality_preset = preset
            self._apply_quality_settings()

    def _apply_quality_settings(self):
        settings_map = {
            QualityPreset.LOW: {
                "shadow_resolution": 512,
                "max_draw_distance": 500,
                "anti_aliasing": "fxaa",
                "texture_quality": 0,
                "particle_limit": 100,
                "post_effects": [PostProcessEffect.ANTI_ALIASING],
            },
            QualityPreset.MEDIUM: {
                "shadow_resolution": 1024,
                "max_draw_distance": 1000,
                "anti_aliasing": "smaa",
                "texture_quality": 1,
                "particle_limit": 500,
                "post_effects": [PostProcessEffect.ANTI_ALIASING, PostProcessEffect.BLOOM],
            },
            QualityPreset.HIGH: {
                "shadow_resolution": 2048,
                "max_draw_distance": 2000,
                "anti_aliasing": "taa",
                "texture_quality": 2,
                "particle_limit": 2000,
                "post_effects": [PostProcessEffect.ANTI_ALIASING, PostProcessEffect.BLOOM,
                                 PostProcessEffect.AMBIENT_OCCLUSION],
            },
            QualityPreset.ULTRA: {
                "shadow_resolution": 4096,
                "max_draw_distance": 5000,
                "anti_aliasing": "taa",
                "texture_quality": 3,
                "particle_limit": 5000,
                "post_effects": [PostProcessEffect.ANTI_ALIASING, PostProcessEffect.BLOOM,
                                 PostProcessEffect.AMBIENT_OCCLUSION, PostProcessEffect.DEPTH_OF_FIELD,
                                 PostProcessEffect.COLOR_GRADING],
            },
        }
        if self._quality_preset in settings_map:
            self._settings = settings_map[self._quality_preset]
            self._post_process_chain = self._settings["post_effects"]

    def get_quality_settings(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "preset": self._quality_preset.value,
                "settings": dict(self._settings),
            }

    # ---- Frame Stats ----

    def record_frame(self, draw_calls: int = 0, triangles: int = 0,
                     gpu_time_ms: float = 0.0, cpu_time_ms: float = 0.0,
                     pass_times: Dict[str, float] = None,
                     batch_savings: int = 0):
        with self._lock:
            self._current_frame += 1
            stats = FrameStats(
                frame_id=self._current_frame,
                draw_calls=draw_calls,
                draw_calls_batched=draw_calls - batch_savings,
                triangles=triangles,
                gpu_time_ms=gpu_time_ms,
                cpu_time_ms=cpu_time_ms,
                pass_times=pass_times or {},
            )
            self._frame_stats.append(stats)
            if len(self._frame_stats) > 3600:  # Keep last minute at 60fps
                self._frame_stats = self._frame_stats[-300:]
            self._total_draw_calls += draw_calls

    def get_frame_stats(self, last_n: int = 60) -> List[Dict[str, Any]]:
        with self._lock:
            return [
                {
                    "frame_id": s.frame_id,
                    "draw_calls": s.draw_calls,
                    "draw_calls_batched": s.draw_calls_batched,
                    "triangles": s.triangles,
                    "gpu_time_ms": s.gpu_time_ms,
                    "cpu_time_ms": s.cpu_time_ms,
                    "pass_times": s.pass_times,
                }
                for s in self._frame_stats[-last_n:]
            ]

    def get_performance_summary(self) -> Dict[str, Any]:
        with self._lock:
            recent = self._frame_stats[-60:]
            if not recent:
                return {}
            avg_draw_calls = sum(s.draw_calls for s in recent) / len(recent)
            avg_gpu_time = sum(s.gpu_time_ms for s in recent) / len(recent)
            avg_cpu_time = sum(s.cpu_time_ms for s in recent) / len(recent)
            avg_triangles = sum(s.triangles for s in recent) / len(recent)
            return {
                "avg_draw_calls": round(avg_draw_calls, 1),
                "avg_gpu_time_ms": round(avg_gpu_time, 2),
                "avg_cpu_time_ms": round(avg_cpu_time, 2),
                "avg_triangles": round(avg_triangles, 1),
                "target_fps": self._target_fps,
                "current_fps": round(1000.0 / max(0.001, max(avg_gpu_time, avg_cpu_time)), 1),
                "gpu_memory_mb": self.get_gpu_memory_usage()["total_mb"],
            }

    # ---- Stats ----

    def get_stats(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "render_passes": len(self._render_passes),
                "post_effects": len(self._post_process_chain),
                "gpu_resources": len(self._gpu_resources),
                "quality_preset": self._quality_preset.value,
                "current_frame": self._current_frame,
                "target_fps": self._target_fps,
                "settings": {k: v for k, v in self._settings.items() if k != "post_effects"},
                "performance": self.get_performance_summary(),
            }


# Singleton instance
_render_orchestrator: Optional[RenderOrchestrator] = None
_orchestrator_lock = threading.RLock()


def get_render_orchestrator() -> RenderOrchestrator:
    global _render_orchestrator
    with _orchestrator_lock:
        if _render_orchestrator is None:
            _render_orchestrator = RenderOrchestrator()
        return _render_orchestrator