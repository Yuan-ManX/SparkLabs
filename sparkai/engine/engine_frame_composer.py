"""
FrameComposer - Frame-based render scheduling with priority-based draw call batching.

Manages draw commands across render passes, sorts by priority, batches similar
draw calls using configurable strategies, and tracks frame budgets for the
SparkLabs game engine rendering pipeline.
"""

import threading
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional

_time_module = time


class RenderPass(Enum):
    """Render pass types defining the draw order within a frame."""

    SHADOW_MAP = 1
    OPAQUE = 2
    TRANSPARENT = 3
    OVERLAY = 4
    UI = 5
    POST_PROCESS = 6
    CUSTOM = 7

    @property
    def sort_order(self) -> int:
        """Returns the natural rendering order for this pass type.

        Lower values are drawn first: shadows before geometry, opaque before
        transparent, world-space before screen-space, and post-processing last.
        """
        return {
            RenderPass.SHADOW_MAP: 0,
            RenderPass.OPAQUE: 1,
            RenderPass.TRANSPARENT: 2,
            RenderPass.OVERLAY: 3,
            RenderPass.UI: 4,
            RenderPass.POST_PROCESS: 5,
            RenderPass.CUSTOM: 6,
        }[self]


class DrawPriority(Enum):
    """Priority levels for draw commands within a render pass.

    Commands with higher priority are drawn first within their pass.
    """

    CRITICAL = 1
    HIGH = 2
    NORMAL = 3
    LOW = 4
    BACKGROUND = 5

    @property
    def sort_order(self) -> int:
        """Returns the numeric ordering for this priority.

        Lower values indicate higher priority (drawn first).
        """
        return {
            DrawPriority.CRITICAL: 0,
            DrawPriority.HIGH: 1,
            DrawPriority.NORMAL: 2,
            DrawPriority.LOW: 3,
            DrawPriority.BACKGROUND: 4,
        }[self]


class BatchStrategy(Enum):
    """Strategies for grouping draw commands into render batches.

    Each strategy groups commands by a different property to minimize
    GPU state changes. NONE disables batching entirely.
    """

    BY_MATERIAL = 1
    BY_TEXTURE = 2
    BY_MESH = 3
    BY_SHADER = 4
    NONE = 5

    def group_key(self, command: "DrawCommand") -> str:
        """Extracts the grouping key from a draw command based on this strategy."""
        if self == BatchStrategy.BY_MATERIAL:
            return command.material_id
        elif self == BatchStrategy.BY_TEXTURE:
            return command.texture_id
        elif self == BatchStrategy.BY_MESH:
            return command.mesh_id
        elif self == BatchStrategy.BY_SHADER:
            return command.shader_id
        elif self == BatchStrategy.NONE:
            return command.id
        return command.material_id


class FrameBudgetMode(Enum):
    """Frame budget modes controlling how the renderer manages frame time.

    FIXED_FPS targets a specific frame rate. ADAPTIVE adjusts quality
    dynamically based on actual frame time. UNLIMITED imposes no restrictions.
    """

    FIXED_FPS = 1
    ADAPTIVE = 2
    UNLIMITED = 3


@dataclass
class DrawCommand:
    """A single draw command submitted to the rendering pipeline.

    Represents one draw call before batching. Carries all state needed for
    rendering: material, texture, mesh, shader bindings, geometry counts,
    and a 4x4 transform matrix.
    """

    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    pass_type: RenderPass = RenderPass.OPAQUE
    priority: DrawPriority = DrawPriority.NORMAL
    material_id: str = ""
    texture_id: str = ""
    mesh_id: str = ""
    shader_id: str = ""
    vertex_count: int = 0
    triangle_count: int = 0
    transform_matrix: List[float] = field(default_factory=lambda: [0.0] * 16)
    sort_key: int = 0
    is_batched: bool = False
    batch_group_id: Optional[str] = None
    created_at: float = field(default_factory=_time_module.time)

    def __post_init__(self) -> None:
        """Validates and initializes command state after construction."""
        if len(self.transform_matrix) != 16:
            raise ValueError(
                f"transform_matrix must have exactly 16 elements, "
                f"got {len(self.transform_matrix)}"
            )
        if self.vertex_count < 0:
            raise ValueError("vertex_count must be non-negative")
        if self.triangle_count < 0:
            raise ValueError("triangle_count must be non-negative")
        if not self.sort_key:
            self.sort_key = self._compute_sort_key()

    def _compute_sort_key(self) -> int:
        """Computes a sort key encoding pass type and priority ordering.

        The key encodes pass type in the high bits and priority in the low
        bits, enabling a single integer sort that respects the render pass
        sequence first, then priority within each pass.
        """
        pass_order = self.pass_type.sort_order
        priority_order = self.priority.sort_order
        return pass_order * 100 + priority_order

    def to_dict(self) -> dict:
        """Serializes the draw command to a dictionary."""
        return {
            "id": self.id,
            "pass_type": self.pass_type.name,
            "priority": self.priority.name,
            "material_id": self.material_id,
            "texture_id": self.texture_id,
            "mesh_id": self.mesh_id,
            "shader_id": self.shader_id,
            "vertex_count": self.vertex_count,
            "triangle_count": self.triangle_count,
            "transform_matrix": list(self.transform_matrix),
            "sort_key": self.sort_key,
            "is_batched": self.is_batched,
            "batch_group_id": self.batch_group_id,
            "created_at": self.created_at,
        }

    def __repr__(self) -> str:
        return (
            f"DrawCommand(id={self.id[:8]}..., pass={self.pass_type.name}, "
            f"pri={self.priority.name}, verts={self.vertex_count})"
        )


@dataclass
class RenderBatch:
    """A batch of draw commands grouped for efficient GPU submission.

    Batching combines multiple draw commands with shared rendering state
    into a single submission, reducing API call overhead and GPU state
    changes. Tracks aggregate geometry counts and references all grouped
    command IDs for debugging and profiling.
    """

    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    command_ids: List[str] = field(default_factory=list)
    material_id: str = ""
    texture_id: str = ""
    shader_id: str = ""
    total_vertices: int = 0
    total_triangles: int = 0
    created_at: float = field(default_factory=_time_module.time)

    @property
    def command_count(self) -> int:
        """Number of draw commands grouped in this batch."""
        return len(self.command_ids)

    @property
    def is_empty(self) -> bool:
        """Whether this batch contains no commands."""
        return len(self.command_ids) == 0

    def add_command(self, command: DrawCommand) -> None:
        """Adds a draw command to this batch, accumulating geometry counts."""
        self.command_ids.append(command.id)
        self.total_vertices += command.vertex_count
        self.total_triangles += command.triangle_count
        command.is_batched = True
        command.batch_group_id = self.id

    def to_dict(self) -> dict:
        """Serializes the render batch to a dictionary."""
        return {
            "id": self.id,
            "command_ids": list(self.command_ids),
            "command_count": self.command_count,
            "material_id": self.material_id,
            "texture_id": self.texture_id,
            "shader_id": self.shader_id,
            "total_vertices": self.total_vertices,
            "total_triangles": self.total_triangles,
            "created_at": self.created_at,
        }

    def __repr__(self) -> str:
        return (
            f"RenderBatch(id={self.id[:8]}..., cmds={self.command_count}, "
            f"verts={self.total_vertices}, tris={self.total_triangles})"
        )


@dataclass
class FrameProfile:
    """Performance profile for a single composed frame.

    Captures timing data, command statistics, and batch counts for a frame.
    Profiles are stored for historical analysis and can be used to drive
    adaptive quality or budget-aware rendering decisions.
    """

    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    frame_number: int = 0
    draw_commands_total: int = 0
    batches_created: int = 0
    draw_calls_issued: int = 0
    frame_time_ms: float = 0.0
    gpu_time_ms: float = 0.0
    cpu_time_ms: float = 0.0
    budget_mode: FrameBudgetMode = FrameBudgetMode.ADAPTIVE
    created_at: float = field(default_factory=_time_module.time)

    @property
    def batch_efficiency(self) -> float:
        """Ratio of commands to draw calls, measuring batching effectiveness.

        A value near 1.0 means strong batching (few draw calls per many commands).
        A value near 0.0 means poor batching (nearly one draw call per command).
        Returns 0.0 if no commands were submitted or no draw calls were issued.
        """
        if self.draw_commands_total == 0:
            return 0.0
        if self.draw_calls_issued == 0:
            return 0.0
        efficiency = 1.0 - (self.draw_calls_issued / self.draw_commands_total)
        return max(0.0, min(1.0, efficiency))

    @property
    def total_time_ms(self) -> float:
        """Total estimated frame time including CPU and GPU contributions."""
        return self.cpu_time_ms + self.gpu_time_ms

    def to_dict(self) -> dict:
        """Serializes the frame profile to a dictionary."""
        return {
            "id": self.id,
            "frame_number": self.frame_number,
            "draw_commands_total": self.draw_commands_total,
            "batches_created": self.batches_created,
            "draw_calls_issued": self.draw_calls_issued,
            "frame_time_ms": self.frame_time_ms,
            "gpu_time_ms": self.gpu_time_ms,
            "cpu_time_ms": self.cpu_time_ms,
            "budget_mode": self.budget_mode.name,
            "batch_efficiency": self.batch_efficiency,
            "total_time_ms": self.total_time_ms,
            "created_at": self.created_at,
        }

    def __repr__(self) -> str:
        return (
            f"FrameProfile(frame={self.frame_number}, "
            f"cmds={self.draw_commands_total}, "
            f"batches={self.batches_created}, "
            f"time={self.frame_time_ms:.2f}ms)"
        )


class FrameComposer:
    """Singleton manager for frame-based render scheduling.

    Coordinates the entire per-frame rendering pipeline: accepts draw commands
    from game systems, sorts them by render pass and priority, batches similar
    commands to reduce GPU overhead, and produces frame profiles for performance
    monitoring.

    Thread-safe via a reentrant lock. Use get_frame_composer() or
    FrameComposer.get_instance() to obtain the singleton instance.
    """

    _instance: Optional["FrameComposer"] = None
    _lock: threading.RLock = threading.RLock()

    # Estimated GPU cost constants in microseconds.
    _GPU_COST_PER_VERTEX_US: float = 0.002
    _GPU_COST_PER_TRIANGLE_US: float = 0.001
    _GPU_COST_PER_BATCH_US: float = 5.0
    _GPU_COST_PER_STATE_CHANGE_US: float = 12.0

    def __new__(cls) -> "FrameComposer":
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
        self._commands: Dict[str, DrawCommand] = {}
        self._batches: List[RenderBatch] = []
        self._profiles: Dict[int, FrameProfile] = {}
        self._budget_mode: FrameBudgetMode = FrameBudgetMode.ADAPTIVE
        self._total_frames_composed: int = 0
        self._last_frame_time_ms: float = 0.0
        self._initialized = True

    @classmethod
    def get_instance(cls) -> "FrameComposer":
        """Returns the singleton FrameComposer instance."""
        return cls()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _validate_transform_matrix(self, matrix: List[float]) -> None:
        """Validates that a transform matrix has exactly 16 float elements.

        Raises:
            ValueError: If the matrix does not contain exactly 16 values.
        """
        if len(matrix) != 16:
            raise ValueError(
                f"Transform matrix must have exactly 16 elements, "
                f"got {len(matrix)}"
            )

    def _sort_commands_for_composition(self) -> List[DrawCommand]:
        """Sorts all pending commands by render pass then priority.

        Commands are ordered first by their pass type's natural rendering
        sequence, then by priority within each pass. This ensures correct
        visual layering before batching occurs.

        Returns:
            A new list of DrawCommand objects in composition order.
        """
        commands = list(self._commands.values())
        commands.sort(key=lambda cmd: cmd.sort_key)
        return commands

    def _group_commands_by_strategy(
        self,
        commands: List[DrawCommand],
        strategy: BatchStrategy,
    ) -> Dict[str, List[DrawCommand]]:
        """Groups draw commands by the given batch strategy.

        Each command is assigned to a group based on the strategy's grouping
        key. Commands with the same key are batched together.

        Returns:
            A dict mapping group keys to lists of draw commands.
        """
        groups: Dict[str, List[DrawCommand]] = {}
        for command in commands:
            key = strategy.group_key(command)
            if key not in groups:
                groups[key] = []
            groups[key].append(command)
        return groups

    def _create_batch_from_group(
        self,
        group_commands: List[DrawCommand],
    ) -> RenderBatch:
        """Creates a single RenderBatch from a group of draw commands.

        The batch inherits material, texture, and shader IDs from the first
        command in the group. All commands in the group are marked as batched
        and linked to the new batch.

        Returns:
            A new RenderBatch containing all commands in the group.
        """
        if not group_commands:
            return RenderBatch()

        representative = group_commands[0]
        batch = RenderBatch(
            material_id=representative.material_id,
            texture_id=representative.texture_id,
            shader_id=representative.shader_id,
        )

        for command in group_commands:
            batch.add_command(command)

        return batch

    def _estimate_gpu_time_ms(self, batches: List[RenderBatch]) -> float:
        """Estimates GPU execution time based on batch geometry complexity.

        Uses per-vertex, per-triangle, per-batch, and per-state-change cost
        constants to produce a rough GPU time estimate in milliseconds.

        Returns:
            Estimated GPU time in milliseconds.
        """
        total_vertices = sum(b.total_vertices for b in batches)
        total_triangles = sum(b.total_triangles for b in batches)
        batch_count = len(batches)

        vertex_cost_us = total_vertices * self._GPU_COST_PER_VERTEX_US
        triangle_cost_us = total_triangles * self._GPU_COST_PER_TRIANGLE_US
        batch_overhead_us = batch_count * self._GPU_COST_PER_BATCH_US
        state_change_cost_us = max(0, batch_count - 1) * self._GPU_COST_PER_STATE_CHANGE_US

        total_us = vertex_cost_us + triangle_cost_us + batch_overhead_us + state_change_cost_us
        return total_us / 1000.0

    def _resolve_batch_strategy(
        self,
        strategy: Optional[BatchStrategy],
    ) -> BatchStrategy:
        """Resolves the batch strategy, falling back to BY_MATERIAL if None."""
        if strategy is not None:
            return strategy
        return BatchStrategy.BY_MATERIAL

    # ------------------------------------------------------------------
    # Public API: Command management
    # ------------------------------------------------------------------

    def submit_command(
        self,
        pass_type: RenderPass,
        priority: DrawPriority,
        material_id: str,
        texture_id: str,
        mesh_id: str,
        shader_id: str,
        vertex_count: int,
        triangle_count: int,
        transform_matrix: List[float],
    ) -> DrawCommand:
        """Submits a new draw command to the frame composer.

        Creates a DrawCommand with the provided rendering parameters, validates
        input, and registers it for inclusion in the next frame composition.

        Args:
            pass_type: The render pass this command belongs to.
            priority: Draw ordering priority within the pass.
            material_id: Material resource identifier.
            texture_id: Texture resource identifier.
            mesh_id: Mesh resource identifier.
            shader_id: Shader resource identifier.
            vertex_count: Number of vertices in the geometry.
            triangle_count: Number of triangles in the geometry.
            transform_matrix: 4x4 column-major transform as 16 floats.

        Returns:
            The created DrawCommand instance.

        Raises:
            ValueError: If transform_matrix has wrong length or counts are negative.
        """
        with self._lock:
            self._validate_transform_matrix(transform_matrix)

            if vertex_count < 0:
                raise ValueError("vertex_count must be non-negative")
            if triangle_count < 0:
                raise ValueError("triangle_count must be non-negative")

            command = DrawCommand(
                pass_type=pass_type,
                priority=priority,
                material_id=material_id,
                texture_id=texture_id,
                mesh_id=mesh_id,
                shader_id=shader_id,
                vertex_count=vertex_count,
                triangle_count=triangle_count,
                transform_matrix=list(transform_matrix),
            )

            self._commands[command.id] = command
            return command

    def remove_command(self, command_id: str) -> bool:
        """Removes a previously submitted draw command by its ID.

        Args:
            command_id: The unique ID of the command to remove.

        Returns:
            True if the command was found and removed, False otherwise.
        """
        with self._lock:
            if command_id in self._commands:
                del self._commands[command_id]
                return True
            return False

    def get_commands_in_pass(self, pass_type: RenderPass) -> List[DrawCommand]:
        """Returns all draw commands for a given render pass.

        Args:
            pass_type: The render pass to query.

        Returns:
            A list of DrawCommand objects in submission order.
        """
        with self._lock:
            return [
                cmd
                for cmd in self._commands.values()
                if cmd.pass_type == pass_type
            ]

    # ------------------------------------------------------------------
    # Public API: Batch management
    # ------------------------------------------------------------------

    def build_batches(
        self,
        strategy: Optional[BatchStrategy] = None,
    ) -> List[RenderBatch]:
        """Builds render batches from pending draw commands.

        Groups commands by the specified strategy and creates one RenderBatch
        per group. Commands are sorted by pass type and priority before
        grouping. Batches are stored internally for subsequent frame composition.

        Args:
            strategy: The batching strategy. Defaults to BY_MATERIAL.

        Returns:
            A list of created RenderBatch objects.
        """
        resolved_strategy = self._resolve_batch_strategy(strategy)

        with self._lock:
            sorted_commands = self._sort_commands_for_composition()
            groups = self._group_commands_by_strategy(
                sorted_commands, resolved_strategy
            )

            self._batches = []
            for _group_key, group_commands in groups.items():
                batch = self._create_batch_from_group(group_commands)
                if not batch.is_empty:
                    self._batches.append(batch)

            return list(self._batches)

    def get_batches(self) -> List[RenderBatch]:
        """Returns the current list of render batches.

        Returns:
            A copy of the internal batch list.
        """
        with self._lock:
            return list(self._batches)

    # ------------------------------------------------------------------
    # Public API: Frame composition
    # ------------------------------------------------------------------

    def compose_frame(
        self,
        frame_number: int,
        budget_mode: Optional[FrameBudgetMode] = None,
    ) -> FrameProfile:
        """Composes a complete frame from pending draw commands.

        This is the core per-frame entry point. It sorts all pending commands
        by render pass and priority, builds render batches, tracks CPU and
        estimated GPU timing, and produces a FrameProfile with detailed
        statistics for the composed frame.

        After composition, the command list is cleared so the next frame
        starts fresh. Batches remain available for inspection via get_batches().

        Args:
            frame_number: Monotonic frame sequence number.
            budget_mode: Optional budget mode override. Uses the composer's
                current mode if not provided.

        Returns:
            A FrameProfile with timing and statistics for this frame.
        """
        if budget_mode is not None:
            self.set_budget_mode(budget_mode)

        cpu_start = _time_module.perf_counter()

        with self._lock:
            command_count = len(self._commands)

            sorted_commands = self._sort_commands_for_composition()
            groups = self._group_commands_by_strategy(
                sorted_commands, self._budget_mode_to_strategy()
            )

            self._batches = []
            for _group_key, group_commands in groups.items():
                batch = self._create_batch_from_group(group_commands)
                if not batch.is_empty:
                    self._batches.append(batch)

            batch_count = len(self._batches)
            draw_calls = batch_count if batch_count > 0 else command_count

            gpu_time = self._estimate_gpu_time_ms(self._batches)

        cpu_end = _time_module.perf_counter()
        cpu_time_ms = (cpu_end - cpu_start) * 1000.0

        with self._lock:
            self._commands.clear()

        profile = FrameProfile(
            frame_number=frame_number,
            draw_commands_total=command_count,
            batches_created=batch_count,
            draw_calls_issued=draw_calls,
            frame_time_ms=cpu_time_ms,
            gpu_time_ms=gpu_time,
            cpu_time_ms=cpu_time_ms,
            budget_mode=self._budget_mode,
        )

        with self._lock:
            self._profiles[frame_number] = profile
            self._total_frames_composed += 1
            self._last_frame_time_ms = cpu_time_ms

        return profile

    # ------------------------------------------------------------------
    # Public API: Profiling and queries
    # ------------------------------------------------------------------

    def get_frame_profile(self, frame_number: int) -> Optional[FrameProfile]:
        """Retrieves a frame profile by its frame number.

        Args:
            frame_number: The frame number to look up.

        Returns:
            The FrameProfile if found, None otherwise.
        """
        with self._lock:
            return self._profiles.get(frame_number)

    def get_latest_profile(self) -> Optional[FrameProfile]:
        """Returns the most recently composed frame profile.

        Returns:
            The latest FrameProfile, or None if no frames have been composed.
        """
        with self._lock:
            if not self._profiles:
                return None
            latest_frame = max(self._profiles.keys())
            return self._profiles[latest_frame]

    # ------------------------------------------------------------------
    # Public API: Budget management
    # ------------------------------------------------------------------

    def set_budget_mode(self, mode: FrameBudgetMode) -> None:
        """Sets the frame budget mode for future frame compositions.

        Args:
            mode: The FrameBudgetMode to activate.
        """
        with self._lock:
            self._budget_mode = mode

    def _budget_mode_to_strategy(self) -> BatchStrategy:
        """Maps the current budget mode to the most appropriate batch strategy.

        All budget modes currently use BY_MATERIAL as the default batching
        strategy. Different strategies could be assigned per mode for more
        aggressive or conservative batching based on budget constraints.

        Returns:
            The BatchStrategy appropriate for the current budget mode.
        """
        return BatchStrategy.BY_MATERIAL

    # ------------------------------------------------------------------
    # Public API: Frame lifecycle
    # ------------------------------------------------------------------

    def clear_frame(self) -> None:
        """Clears all pending commands and batches for a fresh frame.

        Resets internal state without affecting stored profiles or budget
        settings. Call this between frames to start clean.
        """
        with self._lock:
            self._commands.clear()
            self._batches.clear()

    def reset(self) -> None:
        """Performs a complete reset of all composer state.

        Clears commands, batches, profiles, and resets counters. Budget mode
        is preserved.
        """
        with self._lock:
            self._commands.clear()
            self._batches.clear()
            self._profiles.clear()
            self._total_frames_composed = 0
            self._last_frame_time_ms = 0.0

    # ------------------------------------------------------------------
    # Public API: Statistics
    # ------------------------------------------------------------------

    def get_stats(self) -> Dict:
        """Returns a comprehensive statistics dictionary for monitoring.

        Includes command and batch counts, profile information, budget
        settings, active pass/priority breakdowns, and GPU cost constants.

        Returns:
            A dictionary with string keys and numeric/collection values.
        """
        with self._lock:
            command_count = len(self._commands)
            batch_count = len(self._batches)
            profile_count = len(self._profiles)

            total_vertices_pending = sum(
                cmd.vertex_count for cmd in self._commands.values()
            )
            total_triangles_pending = sum(
                cmd.triangle_count for cmd in self._commands.values()
            )

            batched_command_count = sum(
                1 for cmd in self._commands.values() if cmd.is_batched
            )
            unbatched_command_count = command_count - batched_command_count

            avg_frame_time_ms = 0.0
            if profile_count > 0:
                avg_frame_time_ms = sum(
                    p.frame_time_ms for p in self._profiles.values()
                ) / profile_count

            avg_batch_efficiency = 0.0
            if profile_count > 0:
                avg_batch_efficiency = sum(
                    p.batch_efficiency for p in self._profiles.values()
                ) / profile_count

            best_frame_time_ms = 0.0
            worst_frame_time_ms = 0.0
            if profile_count > 0:
                profile_times = [p.frame_time_ms for p in self._profiles.values()]
                best_frame_time_ms = min(profile_times)
                worst_frame_time_ms = max(profile_times)

            passes_active: Dict[str, int] = {}
            for cmd in self._commands.values():
                pass_name = cmd.pass_type.name
                passes_active[pass_name] = passes_active.get(pass_name, 0) + 1

            priorities_active: Dict[str, int] = {}
            for cmd in self._commands.values():
                pri_name = cmd.priority.name
                priorities_active[pri_name] = (
                    priorities_active.get(pri_name, 0) + 1
                )

            return {
                "command_count": command_count,
                "batched_commands": batched_command_count,
                "unbatched_commands": unbatched_command_count,
                "batch_count": batch_count,
                "profile_count": profile_count,
                "total_frames_composed": self._total_frames_composed,
                "last_frame_time_ms": self._last_frame_time_ms,
                "avg_frame_time_ms": round(avg_frame_time_ms, 3),
                "best_frame_time_ms": round(best_frame_time_ms, 3),
                "worst_frame_time_ms": round(worst_frame_time_ms, 3),
                "avg_batch_efficiency": round(avg_batch_efficiency, 4),
                "budget_mode": self._budget_mode.name,
                "total_vertices_pending": total_vertices_pending,
                "total_triangles_pending": total_triangles_pending,
                "passes_active": passes_active,
                "priorities_active": priorities_active,
                "gpu_cost_per_vertex_us": self._GPU_COST_PER_VERTEX_US,
                "gpu_cost_per_triangle_us": self._GPU_COST_PER_TRIANGLE_US,
                "gpu_cost_per_batch_us": self._GPU_COST_PER_BATCH_US,
                "gpu_cost_per_state_change_us": self._GPU_COST_PER_STATE_CHANGE_US,
            }

    def __repr__(self) -> str:
        with self._lock:
            return (
                f"FrameComposer(cmds={len(self._commands)}, "
                f"batches={len(self._batches)}, "
                f"profiles={len(self._profiles)}, "
                f"mode={self._budget_mode.name})"
            )


def get_frame_composer() -> FrameComposer:
    """Module-level accessor for the FrameComposer singleton.

    Convenience function that returns the singleton instance without
    needing to reference FrameComposer.get_instance() directly.

    Returns:
        The singleton FrameComposer instance.
    """
    return FrameComposer.get_instance()