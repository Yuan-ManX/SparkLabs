"""
SparkLabs Engine - GPU Compute Pipeline

A generalized GPU compute shader management and execution pipeline that
enables parallel computation on the GPU for non-rendering tasks. Powers
particle physics, procedural generation, AI inference, audio processing,
and other data-parallel workloads via the engine's compute shader abstraction.

Architecture:
  EngineGPUCompute (Singleton)
    |-- ComputeKernel (individual compute shader program)
    |-- ComputeDispatch (kernel execution configuration)
    |-- ComputeBuffer (GPU memory buffer management)
    |-- ComputePipeline (ordered kernel execution chain)
    |-- BarrierManager (synchronization point management)
    |-- ResourceTracker (GPU memory accounting)

Core Capabilities:
  - Compute shader compilation and caching
  - Multi-dimensional dispatch configuration (1D/2D/3D)
  - GPU buffer allocation with readback synchronization
  - Ordered kernel execution with pipeline barriers
  - Workgroup size optimization and occupancy analysis
  - GPU memory budget tracking and resource management
"""

from __future__ import annotations

import math
import random
import threading
import time as _time_module
import uuid
from collections import defaultdict, deque
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple


# ---------------------------------------------------------------------------
# Domain Enums
# ---------------------------------------------------------------------------

class ComputeDimension(Enum):
    """Dimensionality of a compute dispatch."""
    ONE_D = "1d"
    TWO_D = "2d"
    THREE_D = "3d"


class BufferType(Enum):
    """Types of GPU compute buffers."""
    STRUCTURED = "structured"
    RAW = "raw"
    CONSTANT = "constant"
    READBACK = "readback"
    RW_STRUCTURED = "rw_structured"
    INDIRECT_ARGS = "indirect_args"


class BufferAccess(Enum):
    """Buffer access patterns for synchronization."""
    READ_ONLY = "read_only"
    WRITE_ONLY = "write_only"
    READ_WRITE = "read_write"


class PipelineBarrier(Enum):
    """Types of pipeline barriers for synchronization."""
    UAV_BARRIER = "uav_barrier"
    TRANSITION = "transition"
    EXECUTION = "execution"
    MEMORY = "memory"


class KernelStatus(Enum):
    """Compilation and execution status of a compute kernel."""
    UNCOMPILED = "uncompiled"
    COMPILING = "compiling"
    COMPILED = "compiled"
    EXECUTING = "executing"
    COMPLETED = "completed"
    ERROR = "error"


class OccupancyLevel(Enum):
    """GPU occupancy quality classification."""
    OPTIMAL = "optimal"
    GOOD = "good"
    ACCEPTABLE = "acceptable"
    LOW = "low"
    CRITICAL = "critical"


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------

@dataclass
class WorkgroupConfig:
    """Configuration for compute shader workgroup sizes.

    Attributes:
        x: Workgroup size in X dimension.
        y: Workgroup size in Y dimension (1 for 1D).
        z: Workgroup size in Z dimension (1 for 1D/2D).
        total_threads: Total threads per workgroup.
        optimal_for_hardware: Whether this config is optimal for target GPU.
    """
    x: int = 64
    y: int = 1
    z: int = 1
    total_threads: int = 64
    optimal_for_hardware: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "x": self.x,
            "y": self.y,
            "z": self.z,
            "total_threads": self.total_threads,
            "optimal_for_hardware": self.optimal_for_hardware,
        }


@dataclass
class ComputeBuffer:
    """A GPU memory buffer for compute shader data.

    Attributes:
        id: Unique buffer identifier.
        name: Human-readable buffer name.
        buffer_type: Type of compute buffer.
        element_size: Size of each element in bytes.
        element_count: Number of elements in the buffer.
        total_size_bytes: Total allocation size.
        access: Current access pattern for synchronization.
        gpu_address: Simulated GPU memory address.
        is_mapped: Whether the buffer is CPU-mapped for readback.
        bound_kernels: Kernels currently bound to this buffer.
        last_used_frame: Frame number when last accessed.
    """
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = ""
    buffer_type: str = BufferType.STRUCTURED.value
    element_size: int = 4
    element_count: int = 1024
    total_size_bytes: int = 4096
    access: str = BufferAccess.READ_WRITE.value
    gpu_address: int = 0
    is_mapped: bool = False
    bound_kernels: List[str] = field(default_factory=list)
    last_used_frame: int = 0

    @property
    def size_kb(self) -> float:
        return self.total_size_bytes / 1024.0

    @property
    def size_mb(self) -> float:
        return self.total_size_bytes / (1024.0 * 1024.0)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "buffer_type": self.buffer_type,
            "element_size": self.element_size,
            "element_count": self.element_count,
            "total_size_bytes": self.total_size_bytes,
            "size_kb": round(self.size_kb, 2),
            "access": self.access,
            "is_mapped": self.is_mapped,
            "bound_kernels": len(self.bound_kernels),
            "last_used_frame": self.last_used_frame,
        }


@dataclass
class ComputeKernel:
    """A compiled compute shader kernel ready for dispatch.

    Attributes:
        id: Unique kernel identifier.
        name: Kernel function name.
        shader_source: GLSL/HLSL source code (for caching/debugging).
        compiled_bytecode: Simulated compiled bytecode hash.
        workgroup_config: Optimal workgroup configuration.
        status: Current compilation/execution status.
        required_buffers: Buffer slots required by this kernel.
        dispatch_count: Number of times this kernel has been dispatched.
        total_execution_time_us: Cumulative execution time.
        avg_execution_time_us: Average execution time per dispatch.
        last_dispatch_frame: Frame number of last dispatch.
        compilation_time_ms: Time spent compiling this kernel.
    """
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = ""
    shader_source: str = ""
    compiled_bytecode: str = ""
    workgroup_config: WorkgroupConfig = field(default_factory=WorkgroupConfig)
    status: str = KernelStatus.UNCOMPILED.value
    required_buffers: List[str] = field(default_factory=list)
    dispatch_count: int = 0
    total_execution_time_us: float = 0.0
    avg_execution_time_us: float = 0.0
    last_dispatch_frame: int = 0
    compilation_time_ms: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "status": self.status,
            "workgroup_config": self.workgroup_config.to_dict(),
            "required_buffers": len(self.required_buffers),
            "dispatch_count": self.dispatch_count,
            "avg_execution_time_us": round(self.avg_execution_time_us, 2),
            "compilation_time_ms": round(self.compilation_time_ms, 2),
            "last_dispatch_frame": self.last_dispatch_frame,
        }


@dataclass
class ComputeDispatch:
    """A single compute shader dispatch configuration.

    Attributes:
        id: Unique dispatch identifier.
        kernel_id: The kernel to dispatch.
        dimension: Dispatch dimensionality (1D/2D/3D).
        thread_groups_x: Number of workgroups in X.
        thread_groups_y: Number of workgroups in Y.
        thread_groups_z: Number of workgroups in Z.
        total_threads: Total thread count for this dispatch.
        buffers: Buffer bindings for this dispatch.
        execution_time_us: Actual execution time.
        frame_number: Which frame this dispatch occurred in.
        occupancy: Achieved GPU occupancy level.
    """
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    kernel_id: str = ""
    dimension: str = ComputeDimension.ONE_D.value
    thread_groups_x: int = 1
    thread_groups_y: int = 1
    thread_groups_z: int = 1
    total_threads: int = 64
    buffers: Dict[str, str] = field(default_factory=dict)
    execution_time_us: float = 0.0
    frame_number: int = 0
    occupancy: str = OccupancyLevel.GOOD.value

    @property
    def total_thread_groups(self) -> int:
        return self.thread_groups_x * self.thread_groups_y * self.thread_groups_z

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "kernel_id": self.kernel_id,
            "dimension": self.dimension,
            "thread_groups": {
                "x": self.thread_groups_x,
                "y": self.thread_groups_y,
                "z": self.thread_groups_z,
                "total": self.total_thread_groups,
            },
            "total_threads": self.total_threads,
            "buffer_count": len(self.buffers),
            "execution_time_us": round(self.execution_time_us, 2),
            "frame_number": self.frame_number,
            "occupancy": self.occupancy,
        }


@dataclass
class ComputePipeline:
    """An ordered chain of compute kernel dispatches with barriers.

    Attributes:
        id: Unique pipeline identifier.
        name: Human-readable pipeline name.
        kernels: Ordered list of kernel IDs to execute.
        barriers: Barriers between kernel dispatches.
        dispatch_count: Total dispatches in this pipeline.
        total_execution_time_us: Cumulative pipeline execution time.
        last_execution_frame: Frame number of last execution.
        enabled: Whether this pipeline is active.
    """
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = ""
    kernels: List[str] = field(default_factory=list)
    barriers: List[Dict[str, str]] = field(default_factory=list)
    dispatch_count: int = 0
    total_execution_time_us: float = 0.0
    last_execution_frame: int = 0
    enabled: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "kernel_count": len(self.kernels),
            "barrier_count": len(self.barriers),
            "dispatch_count": self.dispatch_count,
            "total_execution_time_us": round(self.total_execution_time_us, 2),
            "enabled": self.enabled,
        }


# ---------------------------------------------------------------------------
# Engine GPU Compute (Singleton)
# ---------------------------------------------------------------------------

class EngineGPUCompute:
    """
    GPU compute shader management and execution pipeline for SparkLabs.

    Provides a generalized abstraction for dispatching data-parallel
    computation to the GPU. Powers particle physics simulation, procedural
    terrain generation, AI neural inference, audio DSP processing, and
    other compute-intensive workloads.

    Features compile-time kernel optimization, automatic workgroup sizing,
    GPU memory budget tracking, barrier-based synchronization, and pipeline
    chaining for complex multi-pass compute operations.
    """

    _instance: Optional["EngineGPUCompute"] = None
    _lock: threading.RLock = threading.RLock()

    def __new__(cls) -> "EngineGPUCompute":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    instance = super().__new__(cls)
                    instance._initialized = False
                    cls._instance = instance
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True

        # Kernel management
        self._kernels: Dict[str, ComputeKernel] = {}
        self._kernel_cache: Dict[str, str] = {}  # source_hash -> kernel_id

        # Buffer management
        self._buffers: Dict[str, ComputeBuffer] = {}
        self._buffer_allocations: int = 0
        self._gpu_memory_used_bytes: int = 0
        self._gpu_memory_budget_bytes: int = 512 * 1024 * 1024  # 512 MB default

        # Dispatch tracking
        self._dispatches: List[ComputeDispatch] = []
        self._dispatch_history: deque[ComputeDispatch] = deque(maxlen=1000)

        # Pipeline management
        self._pipelines: Dict[str, ComputePipeline] = {}

        # Performance tracking
        self._frame_number: int = 0
        self._total_dispatches: int = 0
        self._total_execution_time_us: float = 0.0
        self._occupancy_samples: deque[float] = deque(maxlen=300)

        # Hardware capability simulation
        self._max_workgroup_size: int = 1024
        self._max_workgroup_count: Tuple[int, int, int] = (65535, 65535, 65535)
        self._warp_size: int = 32
        self._max_shared_memory_bytes: int = 48 * 1024

        # Standard workgroup configurations
        self._standard_workgroups: Dict[str, WorkgroupConfig] = {
            "1d_64": WorkgroupConfig(x=64, y=1, z=1, total_threads=64),
            "1d_128": WorkgroupConfig(x=128, y=1, z=1, total_threads=128),
            "1d_256": WorkgroupConfig(x=256, y=1, z=1, total_threads=256),
            "2d_8x8": WorkgroupConfig(x=8, y=8, z=1, total_threads=64),
            "2d_16x16": WorkgroupConfig(x=16, y=16, z=1, total_threads=256),
            "3d_4x4x4": WorkgroupConfig(x=4, y=4, z=4, total_threads=64),
            "3d_8x8x8": WorkgroupConfig(x=8, y=8, z=8, total_threads=512),
        }

    # ------------------------------------------------------------------
    # Kernel Management
    # ------------------------------------------------------------------

    def compile_kernel(
        self,
        name: str,
        shader_source: str,
        workgroup_config: Optional[WorkgroupConfig] = None,
    ) -> ComputeKernel:
        """
        Compile a compute shader into an executable kernel.

        In production, this would invoke the platform's shader compiler
        (glslangValidator, DXC, FXC, etc.). Here it simulates compilation
        with workgroup optimization.

        Args:
            name: Kernel function name.
            shader_source: GLSL/HLSL compute shader source code.
            workgroup_config: Optional explicit workgroup configuration.

        Returns:
            Compiled ComputeKernel ready for dispatch.
        """
        with self._lock:
            # Check cache first
            source_hash = hashlib.md5(shader_source.encode()).hexdigest()
            cached_kernel_id = self._kernel_cache.get(source_hash)
            if cached_kernel_id and cached_kernel_id in self._kernels:
                return self._kernels[cached_kernel_id]

            compile_start = _time_module.time()

            kernel = ComputeKernel(
                name=name,
                shader_source=shader_source,
                compiled_bytecode=source_hash[:16],
                status=KernelStatus.COMPILING.value,
            )

            # Determine optimal workgroup configuration
            if workgroup_config:
                kernel.workgroup_config = workgroup_config
            else:
                kernel.workgroup_config = self._determine_optimal_workgroup(
                    shader_source
                )

            # Simulate compilation
            compile_time = (len(shader_source) / 10000.0) * 5.0 + random.uniform(0.5, 2.0)
            kernel.compilation_time_ms = round(
                (_time_module.time() - compile_start) * 1000, 2
            )
            # Override with realistic compilation time
            kernel.compilation_time_ms = round(compile_time, 2)
            kernel.status = KernelStatus.COMPILED.value

            self._kernels[kernel.id] = kernel
            self._kernel_cache[source_hash] = kernel.id

            return kernel

    def _determine_optimal_workgroup(self, shader_source: str) -> WorkgroupConfig:
        """Heuristically determine optimal workgroup configuration from shader source."""
        # In production, this would analyze shader resource usage
        # and query hardware capabilities for occupancy optimization

        source_lower = shader_source.lower()

        if "image2d" in source_lower or "texture2d" in source_lower:
            return WorkgroupConfig(**self._standard_workgroups["2d_16x16"].__dict__)
        if "image3d" in source_lower or "volume" in source_lower:
            return WorkgroupConfig(**self._standard_workgroups["3d_8x8x8"].__dict__)
        if "particle" in source_lower and "num_particles" in source_lower:
            return WorkgroupConfig(**self._standard_workgroups["1d_256"].__dict__)

        # Default: 1D with 256 threads
        return WorkgroupConfig(**self._standard_workgroups["1d_256"].__dict__)

    def get_kernel(self, kernel_id: str) -> Optional[ComputeKernel]:
        """Retrieve a compiled kernel by ID."""
        return self._kernels.get(kernel_id)

    def list_kernels(self) -> List[Dict[str, Any]]:
        """List all compiled kernels."""
        return [k.to_dict() for k in self._kernels.values()]

    # ------------------------------------------------------------------
    # Buffer Management
    # ------------------------------------------------------------------

    def create_buffer(
        self,
        name: str,
        buffer_type: BufferType = BufferType.STRUCTURED,
        element_size: int = 4,
        element_count: int = 1024,
        access: BufferAccess = BufferAccess.READ_WRITE,
    ) -> ComputeBuffer:
        """
        Allocate a GPU compute buffer.

        Args:
            name: Human-readable buffer name.
            buffer_type: Type of compute buffer.
            element_size: Size of each element in bytes.
            element_count: Number of elements.
            access: Buffer access pattern.

        Returns:
            Created ComputeBuffer with GPU memory allocation.
        """
        with self._lock:
            total_size = element_size * element_count

            # Check memory budget
            if self._gpu_memory_used_bytes + total_size > self._gpu_memory_budget_bytes:
                raise RuntimeError(
                    f"GPU memory budget exceeded: {self._gpu_memory_used_bytes + total_size} > {self._gpu_memory_budget_bytes}"
                )

            buffer = ComputeBuffer(
                name=name,
                buffer_type=buffer_type.value,
                element_size=element_size,
                element_count=element_count,
                total_size_bytes=total_size,
                access=access.value,
                gpu_address=self._gpu_memory_used_bytes,  # Simulated address
            )

            self._buffers[buffer.id] = buffer
            self._buffer_allocations += 1
            self._gpu_memory_used_bytes += total_size

            return buffer

    def get_buffer(self, buffer_id: str) -> Optional[ComputeBuffer]:
        """Retrieve a GPU buffer by ID."""
        return self._buffers.get(buffer_id)

    def release_buffer(self, buffer_id: str) -> bool:
        """Release a GPU buffer and reclaim memory."""
        buffer = self._buffers.pop(buffer_id, None)
        if not buffer:
            return False
        self._gpu_memory_used_bytes -= buffer.total_size_bytes
        self._gpu_memory_used_bytes = max(0, self._gpu_memory_used_bytes)
        return True

    def list_buffers(self) -> List[Dict[str, Any]]:
        """List all allocated buffers."""
        return [b.to_dict() for b in self._buffers.values()]

    # ------------------------------------------------------------------
    # Dispatch Execution
    # ------------------------------------------------------------------

    def dispatch(
        self,
        kernel_id: str,
        dimension: ComputeDimension = ComputeDimension.ONE_D,
        thread_groups: Optional[Tuple[int, int, int]] = None,
        buffers: Optional[Dict[str, str]] = None,
        indirect_args_buffer: Optional[str] = None,
    ) -> ComputeDispatch:
        """
        Dispatch a compute kernel for GPU execution.

        Args:
            kernel_id: The compiled kernel to execute.
            dimension: Dispatch dimensionality.
            thread_groups: Explicit (x, y, z) thread group counts.
            buffers: Buffer slot-to-buffer-id bindings.
            indirect_args_buffer: Optional indirect dispatch arguments buffer.

        Returns:
            ComputeDispatch record with execution metrics.
        """
        with self._lock:
            kernel = self._kernels.get(kernel_id)
            if not kernel:
                raise ValueError(f"Kernel not found: {kernel_id}")

            if kernel.status != KernelStatus.COMPILED.value:
                raise RuntimeError(f"Kernel not compiled: {kernel.status}")

            wg = kernel.workgroup_config

            # Compute thread group counts
            if thread_groups:
                tg_x, tg_y, tg_z = thread_groups
            else:
                # Auto-compute from total data size
                tg_x = 1
                tg_y = 1
                tg_z = 1

                if dimension == ComputeDimension.ONE_D:
                    # Assume 1D dispatch over a reasonable data size
                    data_size = 4096
                    if buffers:
                        for buf_id in buffers.values():
                            buf = self._buffers.get(buf_id)
                            if buf:
                                data_size = max(data_size, buf.element_count)
                    tg_x = max(1, math.ceil(data_size / wg.x))
                elif dimension == ComputeDimension.TWO_D:
                    # 2D dispatch for image/texture processing
                    dim = 256
                    tg_x = max(1, math.ceil(dim / wg.x))
                    tg_y = max(1, math.ceil(dim / wg.y))
                elif dimension == ComputeDimension.THREE_D:
                    dim = 64
                    tg_x = max(1, math.ceil(dim / wg.x))
                    tg_y = max(1, math.ceil(dim / wg.y))
                    tg_z = max(1, math.ceil(dim / wg.z))

            # Clamp to hardware limits
            tg_x = min(tg_x, self._max_workgroup_count[0])
            tg_y = min(tg_y, self._max_workgroup_count[1])
            tg_z = min(tg_z, self._max_workgroup_count[2])

            total_threads = tg_x * tg_y * tg_z * wg.total_threads

            # Compute occupancy
            occupancy = self._compute_occupancy(wg, tg_x, tg_y, tg_z)

            # Simulate execution time
            execution_us = self._simulate_execution_time(
                total_threads, len(buffers or {}), occupancy
            )

            # Build dispatch record
            dispatch = ComputeDispatch(
                kernel_id=kernel_id,
                dimension=dimension.value,
                thread_groups_x=tg_x,
                thread_groups_y=tg_y,
                thread_groups_z=tg_z,
                total_threads=total_threads,
                buffers=buffers or {},
                execution_time_us=execution_us,
                frame_number=self._frame_number,
                occupancy=occupancy,
            )

            # Update kernel stats
            kernel.dispatch_count += 1
            kernel.total_execution_time_us += execution_us
            kernel.avg_execution_time_us = (
                kernel.total_execution_time_us / kernel.dispatch_count
            )
            kernel.last_dispatch_frame = self._frame_number
            kernel.status = KernelStatus.COMPLETED.value

            # Update buffer access tracking
            if buffers:
                for buf_id in buffers.values():
                    buf = self._buffers.get(buf_id)
                    if buf:
                        buf.last_used_frame = self._frame_number
                        buf.bound_kernels.append(kernel_id)

            # Track dispatch
            self._dispatches.append(dispatch)
            self._dispatch_history.append(dispatch)
            self._total_dispatches += 1
            self._total_execution_time_us += execution_us
            self._occupancy_samples.append(self._get_occupancy_ratio(occupancy))

            return dispatch

    def _compute_occupancy(
        self, wg: WorkgroupConfig, tg_x: int, tg_y: int, tg_z: int
    ) -> str:
        """Compute GPU occupancy level for a dispatch configuration."""
        # Compute threads per multiprocessor (simplified model)
        threads_per_block = wg.total_threads
        blocks_per_sm = min(
            32,
            self._max_workgroup_size // threads_per_block,
            self._max_shared_memory_bytes // (1024),  # Assume 1KB shared mem per block
        )

        if blocks_per_sm >= 16:
            return OccupancyLevel.OPTIMAL.value
        if blocks_per_sm >= 8:
            return OccupancyLevel.GOOD.value
        if blocks_per_sm >= 4:
            return OccupancyLevel.ACCEPTABLE.value
        if blocks_per_sm >= 2:
            return OccupancyLevel.LOW.value
        return OccupancyLevel.CRITICAL.value

    def _get_occupancy_ratio(self, occupancy: str) -> float:
        """Convert occupancy level to a numeric ratio."""
        return {
            OccupancyLevel.OPTIMAL.value: 1.0,
            OccupancyLevel.GOOD.value: 0.75,
            OccupancyLevel.ACCEPTABLE.value: 0.5,
            OccupancyLevel.LOW.value: 0.25,
            OccupancyLevel.CRITICAL.value: 0.1,
        }.get(occupancy, 0.5)

    def _simulate_execution_time(
        self, total_threads: int, buffer_count: int, occupancy: str
    ) -> float:
        """Simulate kernel execution time based on workload characteristics."""
        base_time = total_threads / 1_000_000.0  # Base: 1M threads per microsecond
        buffer_cost = buffer_count * 0.1  # Buffer binding overhead
        occupancy_factor = {
            OccupancyLevel.OPTIMAL.value: 1.0,
            OccupancyLevel.GOOD.value: 1.3,
            OccupancyLevel.ACCEPTABLE.value: 1.8,
            OccupancyLevel.LOW.value: 2.5,
            OccupancyLevel.CRITICAL.value: 4.0,
        }.get(occupancy, 1.0)

        return (base_time + buffer_cost) * occupancy_factor * 1000  # Convert to microseconds

    # ------------------------------------------------------------------
    # Pipeline Execution
    # ------------------------------------------------------------------

    def create_pipeline(
        self,
        name: str,
        kernel_ids: List[str],
        barriers: Optional[List[Dict[str, str]]] = None,
    ) -> ComputePipeline:
        """
        Create an ordered compute pipeline for multi-pass execution.

        Args:
            name: Human-readable pipeline name.
            kernel_ids: Ordered list of kernel IDs to execute.
            barriers: Optional barriers between kernel dispatches.

        Returns:
            Created ComputePipeline.
        """
        pipeline = ComputePipeline(
            name=name,
            kernels=list(kernel_ids),
            barriers=barriers or [],
        )
        self._pipelines[pipeline.id] = pipeline
        return pipeline

    def execute_pipeline(self, pipeline_id: str) -> List[ComputeDispatch]:
        """
        Execute all kernels in a compute pipeline with proper barriers.

        Args:
            pipeline_id: The pipeline to execute.

        Returns:
            List of dispatch records for each kernel execution.
        """
        pipeline = self._pipelines.get(pipeline_id)
        if not pipeline:
            raise ValueError(f"Pipeline not found: {pipeline_id}")

        if not pipeline.enabled:
            return []

        dispatches = []
        exec_start = _time_module.time()

        for i, kernel_id in enumerate(pipeline.kernels):
            # Insert barrier if specified (not the first kernel)
            if i > 0 and i - 1 < len(pipeline.barriers):
                barrier = pipeline.barriers[i - 1]
                # Barrier is implicitly handled by sequential dispatch

            # Dispatch kernel
            dispatch = self.dispatch(kernel_id)
            dispatches.append(dispatch)

        pipeline.dispatch_count += 1
        pipeline.total_execution_time_us += (_time_module.time() - exec_start) * 1_000_000
        pipeline.last_execution_frame = self._frame_number

        return dispatches

    # ------------------------------------------------------------------
    # Frame Management
    # ------------------------------------------------------------------

    def begin_frame(self) -> None:
        """Begin a new frame, resetting per-frame dispatch tracking."""
        self._frame_number += 1
        self._dispatches.clear()

    def end_frame(self) -> List[ComputeDispatch]:
        """End the current frame and return all dispatches."""
        return list(self._dispatches)

    # ------------------------------------------------------------------
    # Status & Reporting
    # ------------------------------------------------------------------

    def get_status(self) -> Dict[str, Any]:
        """Get comprehensive GPU compute pipeline status."""
        avg_occupancy = (
            sum(self._occupancy_samples) / len(self._occupancy_samples)
            if self._occupancy_samples else 0.0
        )
        avg_exec_time = (
            self._total_execution_time_us / max(1, self._total_dispatches)
        )

        return {
            "frame_number": self._frame_number,
            "kernels_compiled": len(self._kernels),
            "buffers_allocated": len(self._buffers),
            "gpu_memory_used_mb": round(self._gpu_memory_used_bytes / (1024.0 * 1024.0), 2),
            "gpu_memory_budget_mb": round(self._gpu_memory_budget_bytes / (1024.0 * 1024.0), 2),
            "gpu_memory_usage_percent": round(
                self._gpu_memory_used_bytes / max(1, self._gpu_memory_budget_bytes) * 100, 1
            ),
            "total_dispatches": self._total_dispatches,
            "avg_execution_time_us": round(avg_exec_time, 2),
            "avg_occupancy": round(avg_occupancy, 4),
            "pipelines": len(self._pipelines),
            "active_pipelines": sum(1 for p in self._pipelines.values() if p.enabled),
            "hardware_limits": {
                "max_workgroup_size": self._max_workgroup_size,
                "max_workgroup_count": list(self._max_workgroup_count),
                "warp_size": self._warp_size,
                "max_shared_memory_kb": self._max_shared_memory_bytes // 1024,
            },
        }

    def get_memory_report(self) -> Dict[str, Any]:
        """Get detailed GPU memory usage report."""
        buffers_by_type: Dict[str, int] = defaultdict(int)
        buffers_by_type_size: Dict[str, int] = defaultdict(int)

        for buf in self._buffers.values():
            buffers_by_type[buf.buffer_type] += 1
            buffers_by_type_size[buf.buffer_type] += buf.total_size_bytes

        return {
            "total_buffers": len(self._buffers),
            "total_memory_bytes": self._gpu_memory_used_bytes,
            "total_memory_mb": round(self._gpu_memory_used_bytes / (1024.0 * 1024.0), 2),
            "by_type": {
                bt: {
                    "count": count,
                    "size_mb": round(buffers_by_type_size[bt] / (1024.0 * 1024.0), 2),
                }
                for bt, count in buffers_by_type.items()
            },
            "budget_remaining_mb": round(
                (self._gpu_memory_budget_bytes - self._gpu_memory_used_bytes) / (1024.0 * 1024.0), 2
            ),
        }

    @classmethod
    def get_instance(cls) -> "EngineGPUCompute":
        """Return the singleton instance."""
        return cls()

    def reset(self) -> None:
        """Reset all GPU compute state."""
        with self._lock:
            self._kernels.clear()
            self._kernel_cache.clear()
            self._buffers.clear()
            self._buffer_allocations = 0
            self._gpu_memory_used_bytes = 0
            self._dispatches.clear()
            self._dispatch_history.clear()
            self._pipelines.clear()
            self._frame_number = 0
            self._total_dispatches = 0
            self._total_execution_time_us = 0.0
            self._occupancy_samples.clear()


# Need hashlib at module level for kernel cache
import hashlib


# ---------------------------------------------------------------------------
# Module-Level Accessor
# ---------------------------------------------------------------------------

def get_gpu_compute() -> EngineGPUCompute:
    """Return the singleton EngineGPUCompute instance."""
    return EngineGPUCompute()