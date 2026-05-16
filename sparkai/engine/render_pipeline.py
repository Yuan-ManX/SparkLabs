"""
SparkLabs Engine - Render Pipeline

Configurable rendering pipeline for the AI-native game engine.
Orchestrates the complete frame rendering lifecycle from draw
submission through render pass execution to final presentation.
Supports forward, deferred, forward-plus, and custom pipeline
architectures with configurable render targets and GBuffer layout.

Architecture:
  RenderPipeline
    |-- PipelineConfig (pipeline type, MSAA, HDR, resolution)
    |-- RenderTarget (color/depth/stencil buffer descriptors)
    |-- RenderPass (ordered execution stages with target binding)
    |-- GBufferEntry (deferred shading surface descriptors)
    |-- DrawBatch (sorted draw command grouping by pass/material)

Pipeline Types:
  - FORWARD: single-pass forward rendering
  - DEFERRED: multi-pass deferred shading with GBuffer
  - FORWARD_PLUS: tiled forward rendering with light culling
  - CUSTOM: user-defined rendering architecture

Render Passes:
  - GEOMETRY, LIGHTING, SHADOW, POST_PROCESS, TRANSPARENCY,
    UI_OVERLAY, SKYBOX, DEBUG

Usage:
    rp = RenderPipeline()
    cfg = PipelineConfig(pipeline_type=PipelineType.DEFERRED, msaa_samples=4)
    rp.create_pipeline(cfg)
    rp.add_render_pass(RenderPass.GEOMETRY)
    rp.begin_frame()
    rp.submit_draw({"mesh_id": "cube_01", "material_id": "mat_pbr"})
    rp.execute_pass("geometry")
    rp.end_frame()
    stats = rp.get_frame_stats()
"""
from __future__ import annotations

import threading
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


class PipelineType(Enum):
    FORWARD = "forward"
    DEFERRED = "deferred"
    FORWARD_PLUS = "forward_plus"
    CUSTOM = "custom"


class RenderPass(Enum):
    GEOMETRY = "geometry"
    LIGHTING = "lighting"
    SHADOW = "shadow"
    POST_PROCESS = "post_process"
    TRANSPARENCY = "transparency"
    UI_OVERLAY = "ui_overlay"
    SKYBOX = "skybox"
    DEBUG = "debug"


class BufferFormat(Enum):
    RGBA8 = "rgba8"
    RGBA16F = "rgba16f"
    RGBA32F = "rgba32f"
    DEPTH24_STENCIL8 = "depth24_stencil8"
    DEPTH32F = "depth32f"
    R8 = "r8"
    R16F = "r16f"


class CullingMode(Enum):
    NONE = "none"
    FRONT = "front"
    BACK = "back"


@dataclass
class PipelineConfig:
    pipeline_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    pipeline_type: PipelineType = PipelineType.FORWARD
    render_passes: List[RenderPass] = field(default_factory=list)
    msaa_samples: int = 1
    use_hdr: bool = False
    shadow_map_resolution: int = 2048
    render_scale: float = 1.0
    max_draw_calls: int = 10000
    enable_vsync: bool = True
    max_batches: int = 2048
    frame_width: int = 1920
    frame_height: int = 1080

    def to_dict(self) -> Dict[str, Any]:
        return {
            "pipeline_id": self.pipeline_id,
            "pipeline_type": self.pipeline_type.value,
            "render_passes": [p.value for p in self.render_passes],
            "msaa_samples": self.msaa_samples,
            "use_hdr": self.use_hdr,
            "shadow_map_resolution": self.shadow_map_resolution,
            "render_scale": self.render_scale,
            "max_draw_calls": self.max_draw_calls,
            "enable_vsync": self.enable_vsync,
            "max_batches": self.max_batches,
            "frame_width": self.frame_width,
            "frame_height": self.frame_height,
        }


@dataclass
class RenderTarget:
    target_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    width: int = 1920
    height: int = 1080
    format: BufferFormat = BufferFormat.RGBA8
    name: str = "main_target"
    clear_color: Tuple[float, float, float, float] = (0.0, 0.0, 0.0, 1.0)
    msaa_samples: int = 1
    mip_levels: int = 1
    enabled: bool = True

    def resize(self, width: int, height: int) -> None:
        self.width = width
        self.height = height

    def to_dict(self) -> Dict[str, Any]:
        return {
            "target_id": self.target_id,
            "width": self.width,
            "height": self.height,
            "format": self.format.value,
            "name": self.name,
            "clear_color": self.clear_color,
            "msaa_samples": self.msaa_samples,
            "mip_levels": self.mip_levels,
            "enabled": self.enabled,
        }


@dataclass
class GBufferEntry:
    entry_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    albedo: Tuple[float, float, float] = (0.5, 0.5, 0.5)
    normal: Tuple[float, float, float] = (0.0, 0.0, 1.0)
    metallic: float = 0.0
    roughness: float = 0.5
    emission: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    depth: float = 0.0
    ao: float = 1.0
    specular: float = 0.5

    def to_dict(self) -> Dict[str, Any]:
        return {
            "entry_id": self.entry_id,
            "albedo": self.albedo,
            "normal": self.normal,
            "metallic": self.metallic,
            "roughness": self.roughness,
            "emission": self.emission,
            "depth": self.depth,
            "ao": self.ao,
            "specular": self.specular,
        }


@dataclass
class DrawBatch:
    batch_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    pass_id: str = ""
    draw_commands: List[Dict[str, Any]] = field(default_factory=list)
    material_id: str = ""
    sort_key: int = 0
    instance_count: int = 1
    triangle_count: int = 0
    submitted: bool = False

    def add_command(self, command: Dict[str, Any]) -> None:
        self.draw_commands.append(command)

    def clear(self) -> None:
        self.draw_commands.clear()
        self.triangle_count = 0
        self.submitted = False


class RenderPipeline:
    """
    Configurable rendering pipeline orchestrator.

    Manages the full frame rendering lifecycle: pipeline configuration,
    render target setup, draw command submission, render pass execution,
    and frame finalization. Supports multiple pipeline architectures
    with deferred shading GBuffer integration and batch management.
    """

    _instance: Optional["RenderPipeline"] = None

    def __init__(self):
        self._config: Optional[PipelineConfig] = None
        self._render_targets: Dict[str, RenderTarget] = {}
        self._g_buffer: List[GBufferEntry] = []
        self._batches: Dict[str, DrawBatch] = {}
        self._pass_queue: List[RenderPass] = []
        self._draw_commands_pending: List[Dict[str, Any]] = []
        self._frame_active: bool = False
        self._draw_call_count: int = 0
        self._triangle_count: int = 0
        self._batch_count: int = 0
        self._pass_timings: Dict[str, float] = {}
        self._frame_count: int = 0
        self._frame_start_time: float = 0.0
        self._lock = threading.RLock()
        self._enabled: bool = True
        self._culling_mode: CullingMode = CullingMode.BACK

    @classmethod
    def get_instance(cls) -> "RenderPipeline":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def create_pipeline(self, config: PipelineConfig) -> bool:
        with self._lock:
            self._config = config
            self._pass_queue = list(config.render_passes)
            self._batches.clear()
            self._g_buffer.clear()
            self._render_targets.clear()
            self._draw_command_count = 0
            self._triangle_count = 0
            self._batch_count = 0
            self._pass_timings.clear()

            if not self._pass_queue:
                default_passes: List[RenderPass]
                if config.pipeline_type == PipelineType.DEFERRED:
                    default_passes = [
                        RenderPass.GEOMETRY,
                        RenderPass.LIGHTING,
                        RenderPass.SHADOW,
                        RenderPass.TRANSPARENCY,
                        RenderPass.SKYBOX,
                        RenderPass.POST_PROCESS,
                        RenderPass.UI_OVERLAY,
                    ]
                elif config.pipeline_type == PipelineType.FORWARD_PLUS:
                    default_passes = [
                        RenderPass.GEOMETRY,
                        RenderPass.LIGHTING,
                        RenderPass.SHADOW,
                        RenderPass.POST_PROCESS,
                        RenderPass.TRANSPARENCY,
                        RenderPass.UI_OVERLAY,
                    ]
                elif config.pipeline_type == PipelineType.CUSTOM:
                    default_passes = []
                else:
                    default_passes = [
                        RenderPass.GEOMETRY,
                        RenderPass.SHADOW,
                        RenderPass.LIGHTING,
                        RenderPass.TRANSPARENCY,
                        RenderPass.SKYBOX,
                        RenderPass.POST_PROCESS,
                        RenderPass.UI_OVERLAY,
                    ]
                self._pass_queue = default_passes

            return True

    def add_render_pass(self, pass_def: RenderPass) -> str:
        with self._lock:
            self._pass_queue.append(pass_def)
            return pass_def.value

    def remove_render_pass(self, pass_def: RenderPass) -> bool:
        with self._lock:
            if pass_def in self._pass_queue:
                self._pass_queue.remove(pass_def)
                return True
            return False

    def get_render_passes(self) -> List[str]:
        with self._lock:
            return [p.value for p in self._pass_queue]

    def set_render_target(self, target: RenderTarget) -> str:
        with self._lock:
            self._render_targets[target.target_id] = target
            return target.target_id

    def remove_render_target(self, target_id: str) -> bool:
        with self._lock:
            if target_id in self._render_targets:
                del self._render_targets[target_id]
                return True
            return False

    def get_render_target(self, target_id: str) -> Optional[RenderTarget]:
        with self._lock:
            return self._render_targets.get(target_id)

    def set_culling_mode(self, mode: CullingMode) -> None:
        with self._lock:
            self._culling_mode = mode

    def begin_frame(self) -> None:
        with self._lock:
            self._frame_active = True
            self._frame_start_time = time.monotonic()
            self._draw_commands_pending.clear()
            self._batches.clear()
            self._g_buffer.clear()
            self._draw_call_count = 0
            self._triangle_count = 0
            self._batch_count = 0
            self._pass_timings.clear()

    def submit_draw(self, draw_command: Dict[str, Any]) -> bool:
        if not self._enabled:
            return False

        with self._lock:
            if not self._frame_active:
                return False

            if self._config and self._draw_call_count >= self._config.max_draw_calls:
                return False

            self._draw_commands_pending.append(draw_command)
            self._draw_call_count += 1

            tri_count = draw_command.get("triangle_count", 0)
            self._triangle_count += tri_count

            pass_id = draw_command.get("pass_id", RenderPass.GEOMETRY.value)
            material_id = draw_command.get("material_id", "default")
            sort_key = draw_command.get("sort_key", 0)

            batch_key = f"{pass_id}:{material_id}:{sort_key}"
            if batch_key not in self._batches:
                self._batches[batch_key] = DrawBatch(
                    pass_id=pass_id,
                    material_id=material_id,
                    sort_key=sort_key,
                )
                self._batch_count += 1

            batch = self._batches[batch_key]
            batch.add_command(draw_command)
            batch.triangle_count += tri_count
            batch.instance_count = max(1, draw_command.get("instance_count", 1))

            return True

    def submit_g_buffer_entry(self, entry: GBufferEntry) -> None:
        with self._lock:
            self._g_buffer.append(entry)

    def clear_g_buffer(self) -> None:
        with self._lock:
            self._g_buffer.clear()

    def execute_pass(self, pass_id: str) -> Dict[str, Any]:
        with self._lock:
            if not self._frame_active:
                return {"success": False, "error": "Frame not active"}

            pass_start = time.monotonic()

            pass_batches = sorted(
                [b for b in self._batches.values() if b.pass_id == pass_id],
                key=lambda b: b.sort_key,
            )

            commands_executed = 0
            triangles_processed = 0
            for batch in pass_batches:
                if batch.submitted:
                    continue
                commands_executed += len(batch.draw_commands)
                triangles_processed += batch.triangle_count
                batch.submitted = True

            pass_time_ms = (time.monotonic() - pass_start) * 1000.0
            self._pass_timings[pass_id] = pass_time_ms

            return {
                "success": True,
                "pass_id": pass_id,
                "batches_processed": len(pass_batches),
                "commands_executed": commands_executed,
                "triangles_processed": triangles_processed,
                "pass_time_ms": pass_time_ms,
            }

    def end_frame(self) -> Dict[str, Any]:
        with self._lock:
            if not self._frame_active:
                return {"success": False, "error": "No active frame"}

            frame_time_ms = (time.monotonic() - self._frame_start_time) * 1000.0

            pass_results: Dict[str, Dict[str, Any]] = {}
            for render_pass in self._pass_queue:
                pass_result = self.execute_pass(render_pass.value)
                pass_results[render_pass.value] = pass_result

            self._frame_active = False
            self._frame_count += 1

            return {
                "success": True,
                "frame": self._frame_count,
                "frame_time_ms": frame_time_ms,
                "draw_calls": self._draw_call_count,
                "triangles": self._triangle_count,
                "batches": self._batch_count,
                "pass_results": pass_results,
            }

    def get_frame_stats(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "draw_calls": self._draw_call_count,
                "triangles": self._triangle_count,
                "batches": self._batch_count,
                "pass_timings": dict(self._pass_timings),
                "frame_active": self._frame_active,
                "render_targets": len(self._render_targets),
                "g_buffer_entries": len(self._g_buffer),
            }

    def get_stats(self) -> Dict[str, Any]:
        with self._lock:
            pipeline_type_value = (
                self._config.pipeline_type.value
                if self._config
                else "unconfigured"
            )
            return {
                "pipeline_type": pipeline_type_value,
                "total_frames": self._frame_count,
                "render_passes": [p.value for p in self._pass_queue],
                "render_targets": {
                    tid: t.to_dict() for tid, t in self._render_targets.items()
                },
                "draw_calls_current": self._draw_call_count,
                "total_triangles_current": self._triangle_count,
                "total_batches_current": self._batch_count,
                "g_buffer_entries": len(self._g_buffer),
                "culling_mode": self._culling_mode.value,
                "enabled": self._enabled,
                "frame_active": self._frame_active,
                "config": self._config.to_dict() if self._config else None,
            }

    def set_enabled(self, enabled: bool) -> None:
        with self._lock:
            self._enabled = enabled

    def reset_stats(self) -> None:
        with self._lock:
            self._draw_call_count = 0
            self._triangle_count = 0
            self._batch_count = 0
            self._pass_timings.clear()
            self._frame_count = 0
            self._g_buffer.clear()


def get_render_pipeline() -> RenderPipeline:
    return RenderPipeline.get_instance()