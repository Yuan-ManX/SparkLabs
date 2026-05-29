"""
RenderPass - Multi-pass rendering pipeline orchestration system.

Manages render passes for depth prepass, shadow maps, deferred shading,
post-processing, and final composition. Provides pass configuration,
priority-ordered execution, pipeline profiling, and bottleneck analysis
for the SparkLabs game engine rendering pipeline.
"""

import threading
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

_time_module = time


class PassType(Enum):
    """Types of render passes defining their role in the pipeline.

    Each pass type represents a distinct rendering stage. The natural
    ordering follows the standard real-time rendering sequence: depth
    and shadow passes first, then geometry, post-processing, and UI.
    """

    DEPTH_PREPASS = "depth_prepass"
    SHADOW_MAP = "shadow_map"
    OPAQUE_GEOMETRY = "opaque_geometry"
    TRANSPARENT = "transparent"
    POST_PROCESS = "post_process"
    UI_OVERLAY = "ui_overlay"
    CUSTOM = "custom"

    @property
    def sort_order(self) -> int:
        """Returns the natural pipeline ordering for this pass type.

        Lower values execute first: depth prepass before shadows,
        opaque before transparent, scene before post-process, and
        UI overlay last.
        """
        return {
            PassType.DEPTH_PREPASS: 0,
            PassType.SHADOW_MAP: 1,
            PassType.OPAQUE_GEOMETRY: 2,
            PassType.TRANSPARENT: 3,
            PassType.POST_PROCESS: 4,
            PassType.UI_OVERLAY: 5,
            PassType.CUSTOM: 6,
        }[self]


class RenderTarget(Enum):
    """Render target types specifying where pass output is drawn.

    Determines the destination framebuffer for a render pass. SCREEN
    writes directly to the backbuffer. RENDER_TEXTURE writes to an
    off-screen texture for subsequent passes. CUBEMAP targets a cube
    map face. DEPTH_ONLY and STENCIL_BUFFER target specialized buffers.
    """

    SCREEN = "screen"
    RENDER_TEXTURE = "render_texture"
    CUBEMAP = "cubemap"
    DEPTH_ONLY = "depth_only"
    STENCIL_BUFFER = "stencil_buffer"


class BlendFunction(Enum):
    """Blend functions controlling how pass output composites with the target.

    Determines the blending equation used when writing a pass result to
    its render target. NONE disables blending entirely. ALPHA_BLEND uses
    standard source-over-alpha. ADDITIVE, MULTIPLY, SCREEN, and
    PREMULTIPLIED provide common artistic blend modes.
    """

    NONE = "none"
    ALPHA_BLEND = "alpha_blend"
    ADDITIVE = "additive"
    MULTIPLY = "multiply"
    SCREEN = "screen"
    PREMULTIPLIED = "premultiplied"


class PassPriority(Enum):
    """Execution priority levels for render passes within the same sort order.

    Within passes of the same PassType, higher priority passes execute first.
    This allows fine-grained control over intra-pass ordering when multiple
    passes share a pass type.
    """

    FIRST = "first"
    EARLY = "early"
    NORMAL = "normal"
    LATE = "late"
    LAST = "last"

    @property
    def sort_order(self) -> int:
        """Returns the numeric ordering for this priority.

        Lower values indicate higher priority (executed first).
        """
        return {
            PassPriority.FIRST: 0,
            PassPriority.EARLY: 1,
            PassPriority.NORMAL: 2,
            PassPriority.LATE: 3,
            PassPriority.LAST: 4,
        }[self]


@dataclass
class RenderPassConfig:
    """Configuration for a single render pass in the pipeline.

    Defines all settings for one rendering stage: its type, output target,
    blend function, execution priority, clear color, and enabled state.
    Each config receives a unique hex ID for referencing throughout the
    pipeline lifecycle.
    """

    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = ""
    pass_type: PassType = PassType.OPAQUE_GEOMETRY
    target: RenderTarget = RenderTarget.SCREEN
    blend_function: BlendFunction = BlendFunction.NONE
    priority: PassPriority = PassPriority.NORMAL
    clear_color: List[float] = field(default_factory=lambda: [0.0, 0.0, 0.0, 1.0])
    enabled: bool = True
    created_at: float = field(default_factory=_time_module.time)

    def __post_init__(self) -> None:
        """Validates configuration state after construction."""
        if len(self.clear_color) != 4:
            raise ValueError(
                f"clear_color must have exactly 4 elements (RGBA), "
                f"got {len(self.clear_color)}"
            )
        for i, channel in enumerate(self.clear_color):
            if channel < 0.0 or channel > 1.0:
                raise ValueError(
                    f"clear_color channel {i} must be in range [0.0, 1.0], "
                    f"got {channel}"
                )

    @property
    def sort_key(self) -> int:
        """Computes a sort key encoding pass type and priority ordering.

        The key encodes pass type in the high bits and priority in the
        low bits, enabling a single integer sort that respects the
        pipeline sequence first, then priority within each stage.
        """
        pass_order = self.pass_type.sort_order
        priority_order = self.priority.sort_order
        return pass_order * 100 + priority_order

    def to_dict(self) -> dict:
        """Serializes the render pass configuration to a dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "pass_type": self.pass_type.name,
            "target": self.target.name,
            "blend_function": self.blend_function.name,
            "priority": self.priority.name,
            "clear_color": list(self.clear_color),
            "enabled": self.enabled,
            "sort_key": self.sort_key,
            "created_at": self.created_at,
        }

    def __repr__(self) -> str:
        return (
            f"RenderPassConfig(id={self.id[:8]}..., name={self.name}, "
            f"type={self.pass_type.name}, enabled={self.enabled})"
        )


@dataclass
class PassExecutionResult:
    """Result of executing a single render pass.

    Captures performance metrics and output state after a pass completes:
    draw call count, triangle throughput, execution time, output texture
    binding, and success status. Results are stored in the execution
    history for profiling and debugging.
    """

    pass_id: str = ""
    draw_calls: int = 0
    triangles: int = 0
    time_ms: float = 0.0
    output_texture: str = ""
    success: bool = True
    recorded_at: float = field(default_factory=_time_module.time)

    def __post_init__(self) -> None:
        """Validates result state after construction."""
        if self.draw_calls < 0:
            raise ValueError("draw_calls must be non-negative")
        if self.triangles < 0:
            raise ValueError("triangles must be non-negative")
        if self.time_ms < 0.0:
            raise ValueError("time_ms must be non-negative")

    def to_dict(self) -> dict:
        """Serializes the pass execution result to a dictionary."""
        return {
            "pass_id": self.pass_id,
            "draw_calls": self.draw_calls,
            "triangles": self.triangles,
            "time_ms": self.time_ms,
            "output_texture": self.output_texture,
            "success": self.success,
            "recorded_at": self.recorded_at,
        }

    def __repr__(self) -> str:
        return (
            f"PassExecutionResult(pass={self.pass_id[:8]}..., "
            f"draws={self.draw_calls}, tris={self.triangles}, "
            f"time={self.time_ms:.3f}ms, ok={self.success})"
        )


@dataclass
class PipelineProfile:
    """Performance profile for a complete pipeline execution.

    Captures the full execution history across all passes, total frame
    time, bottleneck identification, and optimization hints. Profiles
    drive adaptive pipeline tuning and inform developers about rendering
    performance characteristics.
    """

    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    passes: List[PassExecutionResult] = field(default_factory=list)
    total_time_ms: float = 0.0
    bottleneck_pass: str = ""
    optimization_hints: List[str] = field(default_factory=list)
    created_at: float = field(default_factory=_time_module.time)

    @property
    def pass_count(self) -> int:
        """Number of passes executed in this pipeline profile."""
        return len(self.passes)

    @property
    def successful_passes(self) -> int:
        """Number of passes that completed successfully."""
        return sum(1 for p in self.passes if p.success)

    @property
    def failed_passes(self) -> int:
        """Number of passes that failed during execution."""
        return sum(1 for p in self.passes if not p.success)

    @property
    def total_draw_calls(self) -> int:
        """Total draw calls across all passes in this profile."""
        return sum(p.draw_calls for p in self.passes)

    @property
    def total_triangles(self) -> int:
        """Total triangles rendered across all passes in this profile."""
        return sum(p.triangles for p in self.passes)

    @property
    def slowest_pass(self) -> Optional[PassExecutionResult]:
        """The pass with the highest execution time, or None if empty."""
        if not self.passes:
            return None
        return max(self.passes, key=lambda p: p.time_ms)

    @property
    def fastest_pass(self) -> Optional[PassExecutionResult]:
        """The pass with the lowest execution time, or None if empty."""
        if not self.passes:
            return None
        return min(self.passes, key=lambda p: p.time_ms)

    def to_dict(self) -> dict:
        """Serializes the pipeline profile to a dictionary."""
        return {
            "id": self.id,
            "passes": [p.to_dict() for p in self.passes],
            "pass_count": self.pass_count,
            "successful_passes": self.successful_passes,
            "failed_passes": self.failed_passes,
            "total_draw_calls": self.total_draw_calls,
            "total_triangles": self.total_triangles,
            "total_time_ms": self.total_time_ms,
            "bottleneck_pass": self.bottleneck_pass,
            "optimization_hints": list(self.optimization_hints),
            "created_at": self.created_at,
        }

    def __repr__(self) -> str:
        return (
            f"PipelineProfile(id={self.id[:8]}..., "
            f"passes={self.pass_count}, "
            f"time={self.total_time_ms:.3f}ms, "
            f"bottleneck={self.bottleneck_pass[:8] if self.bottleneck_pass else 'none'}...)"
        )


class RenderPass:
    """Singleton manager for multi-pass rendering pipelines.

    Orchestrates the complete render pipeline lifecycle: creates and
    configures render passes, executes them in priority order with
    timing and performance capture, profiles pipelines to identify
    bottlenecks, and generates optimization hints.

    Thread-safe via a reentrant lock. Use get_render_pass() or
    RenderPass.get_instance() to obtain the singleton instance.
    """

    _instance: Optional["RenderPass"] = None
    _lock: threading.RLock = threading.RLock()

    def __new__(cls) -> "RenderPass":
        """Thread-safe singleton construction with double-check locking."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    instance = super().__new__(cls)
                    instance._initialized = False
                    cls._instance = instance
        return cls._instance

    def __init__(self) -> None:
        """Initializes internal state on first construction only."""
        if getattr(self, "_initialized", False):
            return
        self._pass_configs: Dict[str, RenderPassConfig] = {}
        self._execution_history: List[PassExecutionResult] = []
        self._pipeline_profiles: Dict[str, PipelineProfile] = {}
        self._stats: Dict[str, Any] = {}
        self._initialized = True

    @classmethod
    def get_instance(cls) -> "RenderPass":
        """Returns the singleton RenderPass instance."""
        return cls()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _resolve_default_name(
        self,
        pass_type: PassType,
        priority: PassPriority,
    ) -> str:
        """Generates a default human-readable name for a pass.

        Combines the pass type and priority into a descriptive string
        useful for debugging and profiling displays.

        Returns:
            A string in the format 'type_priority'.
        """
        return f"{pass_type.value}_{priority.value}"

    def _get_sorted_configs(self) -> List[RenderPassConfig]:
        """Returns all pass configs sorted by pass type then priority.

        Configs are ordered first by their PassType natural rendering
        sequence, then by PassPriority within each type. Disabled
        passes are excluded from the result.

        Returns:
            A new list of RenderPassConfig in pipeline execution order.
        """
        configs = [
            cfg
            for cfg in self._pass_configs.values()
            if cfg.enabled
        ]
        configs.sort(key=lambda cfg: cfg.sort_key)
        return configs

    def _analyze_bottleneck(
        self,
        results: List[PassExecutionResult],
        total_time_ms: float,
    ) -> str:
        """Identifies the bottleneck pass from a set of execution results.

        The bottleneck is the pass that consumes the largest portion of
        total pipeline time. If total time is zero or no results exist,
        returns an empty string.

        Returns:
            The pass ID of the bottleneck pass, or empty string.
        """
        if not results or total_time_ms <= 0.0:
            return ""
        bottleneck = max(results, key=lambda r: r.time_ms)
        return bottleneck.pass_id

    def _generate_optimization_hints(
        self,
        results: List[PassExecutionResult],
        total_time_ms: float,
    ) -> List[str]:
        """Generates optimization hints based on pipeline performance data.

        Analyzes execution results to produce actionable suggestions for
        improving pipeline performance. Hints cover draw call reduction,
        pass reordering, and failure remediation.

        Returns:
            A list of human-readable optimization hint strings.
        """
        hints: List[str] = []

        if not results:
            return hints

        for result in results:
            if not result.success:
                config = self._pass_configs.get(result.pass_id)
                name = config.name if config else result.pass_id[:8]
                hints.append(
                    f"Pass '{name}' failed execution - check render target "
                    f"and shader bindings."
                )

        if total_time_ms > 0.0:
            bottleneck_result = max(results, key=lambda r: r.time_ms)
            bottleneck_config = self._pass_configs.get(bottleneck_result.pass_id)
            if bottleneck_config:
                hints.append(
                    f"Bottleneck in pass '{bottleneck_config.name}' "
                    f"({bottleneck_result.time_ms:.2f}ms, "
                    f"{bottleneck_result.draw_calls} draw calls) - "
                    f"consider reducing draw calls or simplifying shaders."
                )

        high_draw_passes = [
            r for r in results if r.draw_calls > 500
        ]
        if high_draw_passes:
            pass_names = []
            for r in high_draw_passes:
                cfg = self._pass_configs.get(r.pass_id)
                pass_names.append(cfg.name if cfg else r.pass_id[:8])
            hints.append(
                f"Passes with high draw calls ({', '.join(pass_names)}) - "
                f"consider batching or instancing."
            )

        if len(results) > 5:
            hints.append(
                "Pipeline has many passes - consider merging compatible "
                "passes to reduce state changes."
            )

        return hints

    def _simulate_pass_execution(
        self,
        config: RenderPassConfig,
        _scene_data: Optional[Dict[str, Any]] = None,
    ) -> PassExecutionResult:
        """Simulates the execution of a single render pass.

        Produces a PassExecutionResult with estimated metrics. In a
        production environment this would interface with the GPU command
        buffer and issue actual draw calls. The current implementation
        generates representative data for pipeline testing and profiling.

        Returns:
            A PassExecutionResult with simulated performance metrics.
        """
        import random

        base_draw_calls = random.randint(10, 200)
        base_triangles = random.randint(500, 50000)

        if config.pass_type == PassType.SHADOW_MAP:
            base_draw_calls = random.randint(20, 400)
            base_triangles = random.randint(1000, 100000)
        elif config.pass_type == PassType.OPAQUE_GEOMETRY:
            base_draw_calls = random.randint(50, 500)
            base_triangles = random.randint(5000, 200000)
        elif config.pass_type == PassType.TRANSPARENT:
            base_draw_calls = random.randint(10, 100)
            base_triangles = random.randint(500, 20000)
        elif config.pass_type == PassType.POST_PROCESS:
            base_draw_calls = random.randint(1, 10)
            base_triangles = random.randint(2, 100)
        elif config.pass_type == PassType.UI_OVERLAY:
            base_draw_calls = random.randint(5, 50)
            base_triangles = random.randint(10, 5000)

        time_ms = (base_draw_calls * 0.05) + (base_triangles * 0.0002)

        output_texture = ""
        if config.target == RenderTarget.RENDER_TEXTURE:
            output_texture = f"rt_{config.id[:8]}"
        elif config.target == RenderTarget.CUBEMAP:
            output_texture = f"cm_{config.id[:8]}"
        elif config.target == RenderTarget.DEPTH_ONLY:
            output_texture = f"depth_{config.id[:8]}"

        return PassExecutionResult(
            pass_id=config.id,
            draw_calls=base_draw_calls,
            triangles=base_triangles,
            time_ms=round(time_ms, 4),
            output_texture=output_texture,
            success=True,
        )

    # ------------------------------------------------------------------
    # Public API: Pass creation and configuration
    # ------------------------------------------------------------------

    def create_pass(
        self,
        name: str = "",
        pass_type: PassType = PassType.OPAQUE_GEOMETRY,
        target: RenderTarget = RenderTarget.SCREEN,
        priority: PassPriority = PassPriority.NORMAL,
    ) -> RenderPassConfig:
        """Creates and registers a new render pass configuration.

        Constructs a RenderPassConfig with the specified parameters and
        adds it to the internal pass registry. If no name is provided,
        a default name is generated from the pass type and priority.

        Args:
            name: Human-readable name for the pass. Auto-generated if empty.
            pass_type: The type of render pass to create.
            target: The render target this pass writes to.
            priority: Execution priority within the pass type.

        Returns:
            The created RenderPassConfig instance.
        """
        with self._lock:
            if not name:
                name = self._resolve_default_name(pass_type, priority)

            config = RenderPassConfig(
                name=name,
                pass_type=pass_type,
                target=target,
                priority=priority,
            )

            self._pass_configs[config.id] = config
            return config

    def configure_pass(
        self,
        pass_id: str,
        **settings: Any,
    ) -> RenderPassConfig:
        """Updates configuration settings for an existing render pass.

        Applies the provided keyword arguments to the pass config
        identified by pass_id. Only recognized attributes are updated;
        unknown keys are silently ignored.

        Args:
            pass_id: The unique ID of the pass to configure.
            **settings: Keyword arguments mapping to RenderPassConfig fields.

        Returns:
            The updated RenderPassConfig instance.

        Raises:
            KeyError: If no pass exists with the given pass_id.
        """
        with self._lock:
            if pass_id not in self._pass_configs:
                raise KeyError(f"No render pass found with id '{pass_id}'")

            config = self._pass_configs[pass_id]

            if "name" in settings:
                config.name = str(settings["name"])
            if "pass_type" in settings:
                config.pass_type = settings["pass_type"]
            if "target" in settings:
                config.target = settings["target"]
            if "blend_function" in settings:
                config.blend_function = settings["blend_function"]
            if "priority" in settings:
                config.priority = settings["priority"]
            if "clear_color" in settings:
                color = settings["clear_color"]
                if len(color) != 4:
                    raise ValueError(
                        f"clear_color must have exactly 4 elements (RGBA), "
                        f"got {len(color)}"
                    )
                config.clear_color = list(color)
            if "enabled" in settings:
                config.enabled = bool(settings["enabled"])

            return config

    def get_pass_config(self, pass_id: str) -> Optional[RenderPassConfig]:
        """Retrieves a render pass configuration by its ID.

        Args:
            pass_id: The unique ID of the pass to look up.

        Returns:
            The RenderPassConfig if found, None otherwise.
        """
        with self._lock:
            return self._pass_configs.get(pass_id)

    def remove_pass(self, pass_id: str) -> bool:
        """Removes a render pass configuration from the pipeline.

        Args:
            pass_id: The unique ID of the pass to remove.

        Returns:
            True if the pass was found and removed, False otherwise.
        """
        with self._lock:
            if pass_id in self._pass_configs:
                del self._pass_configs[pass_id]
                return True
            return False

    def get_all_passes(self) -> List[RenderPassConfig]:
        """Returns all registered render pass configurations.

        Returns:
            A list of all RenderPassConfig objects, unsorted.
        """
        with self._lock:
            return list(self._pass_configs.values())

    def get_enabled_passes(self) -> List[RenderPassConfig]:
        """Returns all enabled render pass configurations.

        Returns:
            A list of RenderPassConfig objects where enabled is True.
        """
        with self._lock:
            return [cfg for cfg in self._pass_configs.values() if cfg.enabled]

    # ------------------------------------------------------------------
    # Public API: Pass execution
    # ------------------------------------------------------------------

    def execute_pass(
        self,
        pass_id: str,
        scene_data: Optional[Dict[str, Any]] = None,
    ) -> PassExecutionResult:
        """Executes a single render pass by its ID.

        Runs the specified pass with optional scene data, captures
        performance metrics, and records the result in the execution
        history.

        Args:
            pass_id: The unique ID of the pass to execute.
            scene_data: Optional scene data consumed by the pass.

        Returns:
            A PassExecutionResult with timing and draw call metrics.

        Raises:
            KeyError: If no pass exists with the given pass_id.
        """
        with self._lock:
            if pass_id not in self._pass_configs:
                raise KeyError(f"No render pass found with id '{pass_id}'")

            config = self._pass_configs[pass_id]

        if not config.enabled:
            return PassExecutionResult(
                pass_id=pass_id,
                draw_calls=0,
                triangles=0,
                time_ms=0.0,
                success=True,
            )

        start_time = _time_module.perf_counter()
        result = self._simulate_pass_execution(config, scene_data)
        end_time = _time_module.perf_counter()

        actual_time_ms = (end_time - start_time) * 1000.0
        result.time_ms = round(actual_time_ms, 4)
        result.success = True

        with self._lock:
            self._execution_history.append(result)

        return result

    def execute_pipeline(
        self,
        scene_data: Optional[Dict[str, Any]] = None,
    ) -> PipelineProfile:
        """Executes all enabled render passes in priority order.

        This is the core pipeline entry point. It sorts all enabled passes
        by pass type and priority, executes each sequentially, collects
        results, performs bottleneck analysis, and produces a complete
        PipelineProfile with optimization hints.

        Args:
            scene_data: Optional scene data passed to each pass.

        Returns:
            A PipelineProfile with execution results and analysis.
        """
        pipeline_start = _time_module.perf_counter()

        with self._lock:
            sorted_configs = self._get_sorted_configs()

        results: List[PassExecutionResult] = []
        for config in sorted_configs:
            result = self.execute_pass(config.id, scene_data)
            results.append(result)

        pipeline_end = _time_module.perf_counter()
        total_time_ms = (pipeline_end - pipeline_start) * 1000.0

        bottleneck = self._analyze_bottleneck(results, total_time_ms)
        hints = self._generate_optimization_hints(results, total_time_ms)

        profile = PipelineProfile(
            passes=results,
            total_time_ms=round(total_time_ms, 4),
            bottleneck_pass=bottleneck,
            optimization_hints=hints,
        )

        with self._lock:
            self._pipeline_profiles[profile.id] = profile

        return profile

    # ------------------------------------------------------------------
    # Public API: Pass ordering
    # ------------------------------------------------------------------

    def reorder_passes(self, pass_ids: List[str]) -> None:
        """Reorders render passes to a custom execution sequence.

        Updates each pass's pass_type and priority to reflect the
        desired ordering. The first pass in the list receives the
        highest priority and earliest pass type in the pipeline.

        Passes not included in the list retain their current ordering.

        Args:
            pass_ids: Ordered list of pass IDs defining the new sequence.

        Raises:
            KeyError: If any pass_id does not exist in the registry.
        """
        with self._lock:
            for pid in pass_ids:
                if pid not in self._pass_configs:
                    raise KeyError(f"No render pass found with id '{pid}'")

            pass_types = list(PassType)
            for index, pass_id in enumerate(pass_ids):
                config = self._pass_configs[pass_id]
                if index < len(pass_types):
                    config.pass_type = pass_types[index]

            priorities = list(PassPriority)
            for index, pass_id in enumerate(pass_ids):
                config = self._pass_configs[pass_id]
                if index < len(priorities):
                    config.priority = priorities[index]

    # ------------------------------------------------------------------
    # Public API: Pipeline profiling
    # ------------------------------------------------------------------

    def profile_pipeline(
        self,
        scene_data: Optional[Dict[str, Any]] = None,
    ) -> PipelineProfile:
        """Profiles the full pipeline with bottleneck analysis.

        Executes the complete pipeline and performs detailed bottleneck
        analysis. Identifies the slowest pass, generates optimization
        hints, and produces a PipelineProfile suitable for performance
        monitoring and adaptive pipeline tuning.

        This is equivalent to execute_pipeline but semantically indicates
        a profiling intent for the caller.

        Args:
            scene_data: Optional scene data passed to each pass.

        Returns:
            A PipelineProfile with detailed performance analysis.
        """
        return self.execute_pipeline(scene_data)

    def get_pipeline_profile(
        self,
        profile_id: str,
    ) -> Optional[PipelineProfile]:
        """Retrieves a pipeline profile by its ID.

        Args:
            profile_id: The unique ID of the profile to look up.

        Returns:
            The PipelineProfile if found, None otherwise.
        """
        with self._lock:
            return self._pipeline_profiles.get(profile_id)

    def get_latest_profile(self) -> Optional[PipelineProfile]:
        """Returns the most recently recorded pipeline profile.

        Returns:
            The latest PipelineProfile, or None if no profiles exist.
        """
        with self._lock:
            if not self._pipeline_profiles:
                return None
            latest_key = max(
                self._pipeline_profiles.keys(),
                key=lambda k: self._pipeline_profiles[k].created_at,
            )
            return self._pipeline_profiles[latest_key]

    def get_execution_history(self) -> List[PassExecutionResult]:
        """Returns the full execution history for all passes.

        Returns:
            A copy of the execution history list.
        """
        with self._lock:
            return list(self._execution_history)

    def get_pass_execution_history(
        self,
        pass_id: str,
    ) -> List[PassExecutionResult]:
        """Returns execution history filtered to a single pass.

        Args:
            pass_id: The unique ID of the pass to query.

        Returns:
            A list of PassExecutionResult for the specified pass.
        """
        with self._lock:
            return [
                r for r in self._execution_history if r.pass_id == pass_id
            ]

    # ------------------------------------------------------------------
    # Public API: Lifecycle management
    # ------------------------------------------------------------------

    def clear_history(self) -> None:
        """Clears all execution history without affecting pass configs.

        Resets the execution history list while preserving all pass
        configurations and pipeline profiles.
        """
        with self._lock:
            self._execution_history.clear()

    def reset(self) -> None:
        """Performs a complete reset of all pipeline state.

        Clears pass configurations, execution history, pipeline profiles,
        and statistics. The singleton instance remains active for reuse.
        """
        with self._lock:
            self._pass_configs.clear()
            self._execution_history.clear()
            self._pipeline_profiles.clear()
            self._stats.clear()

    # ------------------------------------------------------------------
    # Public API: Statistics
    # ------------------------------------------------------------------

    def get_stats(self) -> Dict[str, Any]:
        """Returns a comprehensive statistics dictionary for monitoring.

        Includes pass counts by type and status, execution metrics,
        profile information, and bottleneck summaries.

        Returns:
            A dictionary with string keys and numeric/collection values.
        """
        with self._lock:
            total_passes = len(self._pass_configs)
            enabled_passes = sum(
                1 for cfg in self._pass_configs.values() if cfg.enabled
            )
            disabled_passes = total_passes - enabled_passes

            passes_by_type: Dict[str, int] = {}
            for cfg in self._pass_configs.values():
                type_name = cfg.pass_type.name
                passes_by_type[type_name] = passes_by_type.get(type_name, 0) + 1

            passes_by_target: Dict[str, int] = {}
            for cfg in self._pass_configs.values():
                target_name = cfg.target.name
                passes_by_target[target_name] = (
                    passes_by_target.get(target_name, 0) + 1
                )

            total_executions = len(self._execution_history)
            total_profile_count = len(self._pipeline_profiles)

            total_draw_calls_all = sum(
                r.draw_calls for r in self._execution_history
            )
            total_triangles_all = sum(
                r.triangles for r in self._execution_history
            )

            avg_pass_time_ms = 0.0
            if total_executions > 0:
                avg_pass_time_ms = sum(
                    r.time_ms for r in self._execution_history
                ) / total_executions

            failed_executions = sum(
                1 for r in self._execution_history if not r.success
            )

            avg_pipeline_time_ms = 0.0
            if total_profile_count > 0:
                avg_pipeline_time_ms = sum(
                    p.total_time_ms for p in self._pipeline_profiles.values()
                ) / total_profile_count

            bottleneck_summary: Dict[str, int] = {}
            for profile in self._pipeline_profiles.values():
                if profile.bottleneck_pass:
                    cfg = self._pass_configs.get(profile.bottleneck_pass)
                    name = cfg.name if cfg else profile.bottleneck_pass[:8]
                    bottleneck_summary[name] = (
                        bottleneck_summary.get(name, 0) + 1
                    )

            return {
                "total_passes": total_passes,
                "enabled_passes": enabled_passes,
                "disabled_passes": disabled_passes,
                "passes_by_type": passes_by_type,
                "passes_by_target": passes_by_target,
                "total_executions": total_executions,
                "failed_executions": failed_executions,
                "total_draw_calls": total_draw_calls_all,
                "total_triangles": total_triangles_all,
                "avg_pass_time_ms": round(avg_pass_time_ms, 4),
                "total_profiles": total_profile_count,
                "avg_pipeline_time_ms": round(avg_pipeline_time_ms, 4),
                "bottleneck_summary": bottleneck_summary,
            }

    def __repr__(self) -> str:
        with self._lock:
            enabled = sum(
                1 for cfg in self._pass_configs.values() if cfg.enabled
            )
            return (
                f"RenderPass(passes={len(self._pass_configs)}, "
                f"enabled={enabled}, "
                f"profiles={len(self._pipeline_profiles)})"
            )


def get_render_pass() -> RenderPass:
    """Module-level accessor for the RenderPass singleton.

    Convenience function that returns the singleton instance without
    needing to reference RenderPass.get_instance() directly.

    Returns:
        The singleton RenderPass instance.
    """
    return RenderPass.get_instance()