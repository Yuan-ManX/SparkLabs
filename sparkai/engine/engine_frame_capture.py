"""
SparkLabs Engine - Frame Capture

Render frame capture subsystem that acquires rendered frames as pixel data
and exposes them through structured queries for AI agent perception. The
subsystem maintains a ring buffer of recent frames for temporal analysis,
supports region and point sampling for targeted inspection, and provides
downsampling to lower resolutions for efficient AI consumption.

Frame sources are pluggable: a synthetic generator is provided for testing,
and external renderers can register a frame supplier callback to feed real
pixel data into the capture pipeline. The captured frames are stored as
RGBA byte arrays with associated metadata (timestamp, dimensions, source).
"""

from __future__ import annotations

import datetime
import random
import threading
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple


# =============================================================================
# Enums
# =============================================================================


class PixelFormat(Enum):
    """Pixel formats supported by the frame capture pipeline.

    Each format defines an in-memory byte layout for a single pixel. All
    formats are 8 bits per channel.
    """

    RGBA8 = "rgba8"
    RGB8 = "rgb8"
    BGRA8 = "bgra8"
    GRAY8 = "gray8"


class CaptureMode(Enum):
    """Capture modes controlling when frames are acquired from a source."""

    CONTINUOUS = "continuous"
    ON_DEMAND = "on_demand"
    TRIGGERED = "triggered"


class FrameSourceKind(Enum):
    """Origin of a frame source."""

    SYNTHETIC = "synthetic"
    RENDERER = "renderer"
    REPLAY = "replay"
    CUSTOM = "custom"


class SyntheticPattern(Enum):
    """Patterns available from the synthetic frame generator."""

    SOLID_COLOR = "solid_color"
    HORIZONTAL_GRADIENT = "horizontal_gradient"
    VERTICAL_GRADIENT = "vertical_gradient"
    CHECKERBOARD = "checkerboard"
    RANDOM_NOISE = "random_noise"
    DIAGONAL_STRIPES = "diagonal_stripes"


class SampleFormat(Enum):
    """Output formats for frame sampling queries."""

    RAW_BYTES = "raw_bytes"
    DOWNSAMPLED = "downsampled"
    REGION_AVERAGE = "region_average"
    POINT_SAMPLE = "point_sample"
    HISTOGRAM = "histogram"


class CaptureStatus(Enum):
    """Status of an individual capture request."""

    PENDING = "pending"
    CAPTURING = "capturing"
    SUCCESS = "success"
    FAILED = "failed"
    NOT_AVAILABLE = "not_available"


# =============================================================================
# Pixel helpers
# =============================================================================


def _bytes_per_pixel(fmt: PixelFormat) -> int:
    """Return the number of bytes per pixel for a pixel format."""
    return {
        PixelFormat.RGBA8: 4,
        PixelFormat.RGB8: 3,
        PixelFormat.BGRA8: 4,
        PixelFormat.GRAY8: 1,
    }[fmt]


def _lerp_color(
    c1: Tuple[int, int, int, int],
    c2: Tuple[int, int, int, int],
    t: float,
) -> Tuple[int, int, int, int]:
    """Linearly interpolate two RGBA colors by factor ``t`` in ``[0, 1]``."""
    return (
        max(0, min(255, round(c1[0] + (c2[0] - c1[0]) * t))),
        max(0, min(255, round(c1[1] + (c2[1] - c1[1]) * t))),
        max(0, min(255, round(c1[2] + (c2[2] - c1[2]) * t))),
        max(0, min(255, round(c1[3] + (c2[3] - c1[3]) * t))),
    )


def _color_bytes(color: Tuple[int, int, int, int], fmt: PixelFormat) -> bytes:
    """Serialize a single RGBA color into the byte layout of ``fmt``."""
    r, g, b, a = color
    if fmt == PixelFormat.RGBA8:
        return bytes((r, g, b, a))
    if fmt == PixelFormat.BGRA8:
        return bytes((b, g, r, a))
    if fmt == PixelFormat.RGB8:
        return bytes((r, g, b))
    if fmt == PixelFormat.GRAY8:
        lum = (r * 299 + g * 587 + b * 114) // 1000
        return bytes((lum,))
    return bytes((r, g, b, a))


def _read_pixel(data: bytes, offset: int, fmt: PixelFormat) -> Tuple[int, int, int, int]:
    """Read a single pixel at ``offset`` and return it as an RGBA tuple."""
    if fmt == PixelFormat.RGBA8:
        return (data[offset], data[offset + 1], data[offset + 2], data[offset + 3])
    if fmt == PixelFormat.BGRA8:
        return (data[offset + 2], data[offset + 1], data[offset], data[offset + 3])
    if fmt == PixelFormat.RGB8:
        return (data[offset], data[offset + 1], data[offset + 2], 255)
    if fmt == PixelFormat.GRAY8:
        lum = data[offset]
        return (lum, lum, lum, 255)
    return (data[offset], data[offset + 1], data[offset + 2], data[offset + 3])


# =============================================================================
# Data Classes
# =============================================================================


@dataclass
class FrameDimensions:
    """Width, height, pixel format and memory layout of a frame buffer.

    Attributes:
        width: Frame width in pixels.
        height: Frame height in pixels.
        format: Pixel format describing the byte layout of one pixel.
        bytes_per_pixel: Number of bytes per pixel. Computed from ``format``
            when not provided.
        stride: Number of bytes per row. Defaults to a tightly packed layout
            (``width * bytes_per_pixel``) when not provided.
    """

    width: int
    height: int
    format: PixelFormat = PixelFormat.RGBA8
    bytes_per_pixel: int = 0
    stride: int = 0

    def __post_init__(self) -> None:
        if self.width < 1:
            raise ValueError("width must be >= 1")
        if self.height < 1:
            raise ValueError("height must be >= 1")
        if self.bytes_per_pixel <= 0:
            self.bytes_per_pixel = _bytes_per_pixel(self.format)
        if self.stride <= 0:
            self.stride = self.width * self.bytes_per_pixel

    @property
    def total_bytes(self) -> int:
        """Total number of bytes of tightly packed pixel data."""
        return self.width * self.height * self.bytes_per_pixel

    def to_dict(self) -> Dict[str, Any]:
        return {
            "width": self.width,
            "height": self.height,
            "format": self.format.value,
            "bytes_per_pixel": self.bytes_per_pixel,
            "stride": self.stride,
            "total_bytes": self.total_bytes,
        }


@dataclass
class CapturedFrame:
    """A captured frame buffer and its metadata.

    Attributes:
        id: Unique identifier of the frame.
        source_kind: Kind of source that produced the frame.
        dimensions: Dimensions and pixel format of the buffer.
        data: Raw pixel data.
        timestamp: ISO timestamp at which the frame was captured.
        frame_index: Monotonically increasing ordering index.
        metadata: Free-form metadata associated with the frame.
    """

    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    source_kind: FrameSourceKind = FrameSourceKind.SYNTHETIC
    dimensions: FrameDimensions = field(default_factory=lambda: FrameDimensions(1, 1))
    data: bytes = b""
    timestamp: str = field(default_factory=lambda: datetime.datetime.utcnow().isoformat())
    frame_index: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def data_size(self) -> int:
        """Number of bytes of pixel data."""
        return len(self.data)

    def to_dict(self) -> Dict[str, Any]:
        # Raw pixel bytes are intentionally omitted: they are too large for
        # typical serialization consumers. ``data_size`` is included instead.
        return {
            "id": self.id,
            "source_kind": self.source_kind.value,
            "dimensions": self.dimensions.to_dict(),
            "data_size": self.data_size,
            "timestamp": self.timestamp,
            "frame_index": self.frame_index,
            "metadata": dict(self.metadata),
        }


@dataclass
class FrameCaptureRequest:
    """A single capture request and its outcome.

    Attributes:
        id: Unique identifier of the request.
        source_kind: Kind of source used to satisfy the request.
        dimensions: Requested frame dimensions.
        mode: Capture mode.
        region: Optional region of interest as ``(x, y, width, height)``.
        downsample_to: Optional target resolution as ``(width, height)``.
        requested_at: ISO timestamp of the request.
        status: Current status of the request.
        result: The captured frame on success, otherwise ``None``.
        error: Error message when ``status`` is ``FAILED``.
    """

    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    source_kind: FrameSourceKind = FrameSourceKind.SYNTHETIC
    dimensions: FrameDimensions = field(default_factory=lambda: FrameDimensions(1, 1))
    mode: CaptureMode = CaptureMode.ON_DEMAND
    region: Optional[Tuple[int, int, int, int]] = None
    downsample_to: Optional[Tuple[int, int]] = None
    requested_at: str = field(default_factory=lambda: datetime.datetime.utcnow().isoformat())
    status: CaptureStatus = CaptureStatus.PENDING
    result: Optional[CapturedFrame] = None
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "source_kind": self.source_kind.value,
            "dimensions": self.dimensions.to_dict(),
            "mode": self.mode.value,
            "region": list(self.region) if self.region else None,
            "downsample_to": list(self.downsample_to) if self.downsample_to else None,
            "requested_at": self.requested_at,
            "status": self.status.value,
            "result": self.result.to_dict() if self.result is not None else None,
            "error": self.error,
        }


@dataclass
class RegionSample:
    """Aggregate color statistics for a rectangular region of a frame.

    Attributes:
        x: Region origin X in pixels.
        y: Region origin Y in pixels.
        width: Region width in pixels.
        height: Region height in pixels.
        average_color: Average RGBA color over the region.
        min_color: Element-wise minimum RGBA color over the region.
        max_color: Element-wise maximum RGBA color over the region.
        pixel_count: Number of pixels sampled.
    """

    x: int
    y: int
    width: int
    height: int
    average_color: Tuple[int, int, int, int] = (0, 0, 0, 0)
    min_color: Tuple[int, int, int, int] = (0, 0, 0, 0)
    max_color: Tuple[int, int, int, int] = (0, 0, 0, 0)
    pixel_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "x": self.x,
            "y": self.y,
            "width": self.width,
            "height": self.height,
            "average_color": list(self.average_color),
            "min_color": list(self.min_color),
            "max_color": list(self.max_color),
            "pixel_count": self.pixel_count,
        }


@dataclass
class PointSample:
    """A single sampled pixel.

    Attributes:
        x: Pixel X coordinate.
        y: Pixel Y coordinate.
        color: RGBA color at the pixel.
    """

    x: int
    y: int
    color: Tuple[int, int, int, int] = (0, 0, 0, 0)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "x": self.x,
            "y": self.y,
            "color": list(self.color),
        }


@dataclass
class FrameHistogram:
    """Per-channel intensity histogram with 256 bins for R, G and B.

    Attributes:
        bins: Mapping from channel name to a list of 256 integer counts.
        total_pixels: Number of pixels contributing to the histogram.
    """

    bins: Dict[str, List[int]] = field(
        default_factory=lambda: {"r": [0] * 256, "g": [0] * 256, "b": [0] * 256}
    )
    total_pixels: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "bins": {k: list(v) for k, v in self.bins.items()},
            "total_pixels": self.total_pixels,
        }


@dataclass
class FrameHistorySnapshot:
    """Snapshot of the ring buffer state.

    Attributes:
        capacity: Maximum number of frames the buffer can hold.
        current_count: Number of frames currently in the buffer.
        oldest_frame_index: Frame index of the oldest frame in the buffer.
        newest_frame_index: Frame index of the newest frame in the buffer.
        total_captures: Total number of frames successfully captured.
        dropped_frames: Number of frames evicted from the buffer.
    """

    capacity: int = 0
    current_count: int = 0
    oldest_frame_index: int = 0
    newest_frame_index: int = 0
    total_captures: int = 0
    dropped_frames: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "capacity": self.capacity,
            "current_count": self.current_count,
            "oldest_frame_index": self.oldest_frame_index,
            "newest_frame_index": self.newest_frame_index,
            "total_captures": self.total_captures,
            "dropped_frames": self.dropped_frames,
        }


@dataclass
class FrameSourceDescriptor:
    """Public description of a registered frame source.

    Attributes:
        name: Unique name of the source.
        kind: Kind of source.
        description: Human-readable description.
        is_active: Whether this is the active source.
        capture_count: Number of frames captured from this source.
        last_capture_at: ISO timestamp of the last capture, or ``None``.
    """

    name: str
    kind: FrameSourceKind
    description: str = ""
    is_active: bool = False
    capture_count: int = 0
    last_capture_at: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "kind": self.kind.value,
            "description": self.description,
            "is_active": self.is_active,
            "capture_count": self.capture_count,
            "last_capture_at": self.last_capture_at,
        }


@dataclass
class FrameCaptureSnapshot:
    """Snapshot of the frame capture engine state.

    Attributes:
        source_count: Number of registered sources.
        request_count: Total number of capture requests issued.
        history_capacity: Capacity of the ring buffer.
        history_count: Number of frames currently in the ring buffer.
        stats: Aggregated statistics dictionary.
        timestamp: ISO timestamp of the snapshot.
    """

    source_count: int = 0
    request_count: int = 0
    history_capacity: int = 0
    history_count: int = 0
    stats: Dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.datetime.utcnow().isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "source_count": self.source_count,
            "request_count": self.request_count,
            "history_capacity": self.history_capacity,
            "history_count": self.history_count,
            "stats": dict(self.stats),
            "timestamp": self.timestamp,
        }


@dataclass
class _SourceEntry:
    """Internal record binding a source descriptor to its supplier callback."""

    descriptor: FrameSourceDescriptor
    supplier: Callable[[FrameDimensions, Optional[Dict[str, Any]]], bytes]


# =============================================================================
# Frame Capture Engine (Singleton)
# =============================================================================


class FrameCaptureEngine:
    """Singleton render frame capture subsystem.

    Maintains a ring buffer of captured frames, a registry of pluggable frame
    sources, and a set of structured query operations (region sampling, point
    sampling, histogram, downsampling) for AI agent perception. All public
    methods are thread-safe.

    Typical usage::

        engine = get_frame_capture()
        request = engine.capture_frame()
        if request.result is not None:
            sample = engine.sample_region(request.result.id, 0, 0, 64, 64)
    """

    _instance: Optional["FrameCaptureEngine"] = None
    _lock = threading.RLock()

    def __init__(self) -> None:
        # Guard against re-initialization of the singleton.
        if getattr(self, "_initialized", False):
            return
        self._sources: Dict[str, _SourceEntry] = {}
        self._active_source_name: Optional[str] = None
        self._history: List[CapturedFrame] = []
        self._frames_by_id: Dict[str, CapturedFrame] = {}
        self._history_capacity: int = 30
        self._max_history_capacity: int = 1000
        self._frame_index_counter: int = 0
        self._dropped_frames: int = 0
        self._default_dimensions: FrameDimensions = FrameDimensions(
            640, 480, PixelFormat.RGBA8
        )
        self._request_count: int = 0
        self._stats: Dict[str, Any] = {
            "total_captures": 0,
            "captures_succeeded": 0,
            "captures_failed": 0,
            "total_samples": 0,
            "total_histograms": 0,
            "total_downsamples": 0,
            "dropped_frames": 0,
            "last_capture_at": None,
            "last_error": None,
        }
        # Seed the default synthetic source and make it active.
        self.register_synthetic_source(
            "synthetic-default",
            SyntheticPattern.HORIZONTAL_GRADIENT,
            color1=(20, 30, 80, 255),
            color2=(180, 200, 255, 255),
        )
        self.set_active_source("synthetic-default")
        self._initialized: bool = True

    @classmethod
    def get_instance(cls) -> "FrameCaptureEngine":
        """Return the singleton FrameCaptureEngine instance (thread-safe)."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    # ------------------------------------------------------------------
    # Source registration
    # ------------------------------------------------------------------

    def register_source(
        self,
        name: str,
        kind: FrameSourceKind,
        supplier_callback: Callable[[FrameDimensions, Optional[Dict[str, Any]]], bytes],
        description: str = "",
    ) -> FrameSourceDescriptor:
        """Register an external frame source.

        Args:
            name: Unique name of the source.
            kind: Kind of source.
            supplier_callback: Callable invoked with
                ``(dimensions, metadata)`` that returns raw pixel data bytes.
            description: Human-readable description.

        Returns:
            The descriptor identifying the registered source.
        """
        with self._lock:
            if not name:
                raise ValueError("source name must be non-empty")
            descriptor = FrameSourceDescriptor(
                name=name,
                kind=kind,
                description=description,
                is_active=False,
                capture_count=0,
                last_capture_at=None,
            )
            self._sources[name] = _SourceEntry(
                descriptor=descriptor, supplier=supplier_callback
            )
            return self._descriptor_view(self._sources[name])

    def remove_source(self, name: str) -> bool:
        """Remove a registered source by name.

        Returns:
            ``True`` if the source was removed, ``False`` if not found.
        """
        with self._lock:
            if name not in self._sources:
                return False
            del self._sources[name]
            if self._active_source_name == name:
                self._active_source_name = None
            return True

    def list_sources(self) -> List[FrameSourceDescriptor]:
        """List descriptors of all registered sources."""
        with self._lock:
            return [self._descriptor_view(entry) for entry in self._sources.values()]

    def get_active_source(self) -> Optional[FrameSourceDescriptor]:
        """Return the descriptor of the active source, or ``None``."""
        with self._lock:
            if self._active_source_name is None:
                return None
            entry = self._sources.get(self._active_source_name)
            if entry is None:
                return None
            return self._descriptor_view(entry)

    def set_active_source(self, name: str) -> bool:
        """Set the active source by name.

        Returns:
            ``True`` if the source was set, ``False`` if not found.
        """
        with self._lock:
            if name not in self._sources:
                return False
            self._active_source_name = name
            return True

    def register_synthetic_source(
        self,
        name: str,
        pattern: SyntheticPattern,
        color1: Tuple[int, int, int, int] = (0, 0, 0, 255),
        color2: Tuple[int, int, int, int] = (255, 255, 255, 255),
    ) -> FrameSourceDescriptor:
        """Register a synthetic frame source that generates ``pattern`` frames.

        Args:
            name: Unique name of the source.
            pattern: Synthetic pattern to generate.
            color1: First color used by the pattern (RGBA).
            color2: Second color used by the pattern (RGBA).

        Returns:
            The descriptor identifying the registered source.
        """
        with self._lock:
            captured_pattern = pattern
            captured_color1 = color1
            captured_color2 = color2

            def supplier(
                dimensions: FrameDimensions,
                metadata: Optional[Dict[str, Any]],
            ) -> bytes:
                return self.generate_synthetic_frame(
                    captured_pattern, dimensions, captured_color1, captured_color2
                )

            return self.register_source(
                name=name,
                kind=FrameSourceKind.SYNTHETIC,
                supplier_callback=supplier,
                description=f"synthetic {pattern.value} generator",
            )

    # ------------------------------------------------------------------
    # Capture
    # ------------------------------------------------------------------

    def capture_frame(
        self,
        source_name: Optional[str] = None,
        dimensions: Optional[FrameDimensions] = None,
        region: Optional[Tuple[int, int, int, int]] = None,
        downsample_to: Optional[Tuple[int, int]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> FrameCaptureRequest:
        """Capture a single frame from a source.

        Args:
            source_name: Source to capture from. When ``None`` the active
                source is used.
            dimensions: Frame dimensions to capture. When ``None`` the
                default dimensions (640x480 RGBA8) are used.
            region: Optional region of interest recorded on the request.
            downsample_to: Optional target resolution recorded on the request.
            metadata: Optional metadata forwarded to the supplier.

        Returns:
            The capture request with ``result`` set on success.
        """
        with self._lock:
            self._request_count += 1
            self._stats["total_captures"] += 1
            dims = (
                dimensions if dimensions is not None else self._default_dimensions
            )
            effective_source = (
                source_name if source_name is not None else self._active_source_name
            )
            entry = (
                self._sources.get(effective_source) if effective_source is not None else None
            )
            source_kind = (
                entry.descriptor.kind if entry is not None else FrameSourceKind.CUSTOM
            )
            request = FrameCaptureRequest(
                source_kind=source_kind,
                dimensions=dims,
                mode=CaptureMode.ON_DEMAND,
                region=region,
                downsample_to=downsample_to,
                status=CaptureStatus.PENDING,
            )
            if entry is None:
                request.status = CaptureStatus.FAILED
                request.error = f"no frame source available: {effective_source!r}"
                self._stats["captures_failed"] += 1
                self._stats["last_error"] = request.error
                return request

            request.status = CaptureStatus.CAPTURING
            try:
                data = entry.supplier(dims, metadata)
            except Exception as exc:  # noqa: BLE001 - record any supplier failure
                request.status = CaptureStatus.FAILED
                request.error = f"supplier error: {exc}"
                self._stats["captures_failed"] += 1
                self._stats["last_error"] = request.error
                return request

            expected = dims.total_bytes
            if len(data) != expected:
                request.status = CaptureStatus.FAILED
                request.error = (
                    f"data size mismatch: got {len(data)}, expected {expected}"
                )
                self._stats["captures_failed"] += 1
                self._stats["last_error"] = request.error
                return request

            self._frame_index_counter += 1
            now = datetime.datetime.utcnow().isoformat()
            frame = CapturedFrame(
                source_kind=entry.descriptor.kind,
                dimensions=dims,
                data=data,
                timestamp=now,
                frame_index=self._frame_index_counter,
                metadata=dict(metadata) if metadata else {},
            )
            self._add_to_history(frame)
            entry.descriptor.capture_count += 1
            entry.descriptor.last_capture_at = now
            request.status = CaptureStatus.SUCCESS
            request.result = frame
            self._stats["captures_succeeded"] += 1
            self._stats["last_capture_at"] = now
            return request

    def get_frame(self, frame_id: str) -> Optional[CapturedFrame]:
        """Return a captured frame by id, or ``None`` if not available."""
        with self._lock:
            return self._frames_by_id.get(frame_id)

    def get_latest_frame(self) -> Optional[CapturedFrame]:
        """Return the most recently captured frame, or ``None``."""
        with self._lock:
            if not self._history:
                return None
            return self._history[-1]

    def list_frames(self, limit: int = 10) -> List[CapturedFrame]:
        """Return up to ``limit`` most recent frames in capture order."""
        with self._lock:
            if limit <= 0:
                return []
            return list(self._history[-limit:])

    # ------------------------------------------------------------------
    # Sampling
    # ------------------------------------------------------------------

    def sample_region(
        self,
        frame_id: str,
        x: int,
        y: int,
        width: int,
        height: int,
    ) -> Optional[RegionSample]:
        """Compute aggregate color statistics for a rectangular region.

        Returns ``None`` if the frame is not found or the region is invalid
        or out of bounds.
        """
        with self._lock:
            frame = self._frames_by_id.get(frame_id)
            if frame is None:
                return None
            dims = frame.dimensions
            if width <= 0 or height <= 0:
                return None
            if x < 0 or y < 0 or x + width > dims.width or y + height > dims.height:
                return None
            data = frame.data
            fmt = dims.format
            bpp = dims.bytes_per_pixel
            src_w = dims.width
            sum_r = 0
            sum_g = 0
            sum_b = 0
            sum_a = 0
            count = 0
            min_c = [255, 255, 255, 255]
            max_c = [0, 0, 0, 0]
            for ry in range(y, y + height):
                row_base = ry * src_w * bpp
                for rx in range(x, x + width):
                    off = row_base + rx * bpp
                    r, g, b, a = _read_pixel(data, off, fmt)
                    sum_r += r
                    sum_g += g
                    sum_b += b
                    sum_a += a
                    if r < min_c[0]:
                        min_c[0] = r
                    if g < min_c[1]:
                        min_c[1] = g
                    if b < min_c[2]:
                        min_c[2] = b
                    if a < min_c[3]:
                        min_c[3] = a
                    if r > max_c[0]:
                        max_c[0] = r
                    if g > max_c[1]:
                        max_c[1] = g
                    if b > max_c[2]:
                        max_c[2] = b
                    if a > max_c[3]:
                        max_c[3] = a
                    count += 1
            if count == 0:
                return None
            average = (sum_r // count, sum_g // count, sum_b // count, sum_a // count)
            self._stats["total_samples"] += 1
            return RegionSample(
                x=x,
                y=y,
                width=width,
                height=height,
                average_color=average,
                min_color=(min_c[0], min_c[1], min_c[2], min_c[3]),
                max_color=(max_c[0], max_c[1], max_c[2], max_c[3]),
                pixel_count=count,
            )

    def sample_point(self, frame_id: str, x: int, y: int) -> Optional[PointSample]:
        """Sample a single pixel from a frame.

        Returns ``None`` if the frame is not found or the coordinate is out
        of bounds.
        """
        with self._lock:
            frame = self._frames_by_id.get(frame_id)
            if frame is None:
                return None
            dims = frame.dimensions
            if x < 0 or y < 0 or x >= dims.width or y >= dims.height:
                return None
            off = (y * dims.width + x) * dims.bytes_per_pixel
            r, g, b, a = _read_pixel(frame.data, off, dims.format)
            self._stats["total_samples"] += 1
            return PointSample(x=x, y=y, color=(r, g, b, a))

    def compute_histogram(
        self,
        frame_id: str,
        channels: Tuple[str, ...] = ("r", "g", "b"),
    ) -> Optional[FrameHistogram]:
        """Compute a per-channel intensity histogram for a frame.

        Args:
            frame_id: Identifier of the frame.
            channels: Channels to include in the returned bins.

        Returns:
            The histogram, or ``None`` if the frame is not found.
        """
        with self._lock:
            frame = self._frames_by_id.get(frame_id)
            if frame is None:
                return None
            dims = frame.dimensions
            data = frame.data
            fmt = dims.format
            bpp = dims.bytes_per_pixel
            total = dims.width * dims.height
            r_bins = [0] * 256
            g_bins = [0] * 256
            b_bins = [0] * 256
            for i in range(total):
                off = i * bpp
                r, g, b, _ = _read_pixel(data, off, fmt)
                r_bins[r] += 1
                g_bins[g] += 1
                b_bins[b] += 1
            bins: Dict[str, List[int]] = {}
            if "r" in channels:
                bins["r"] = r_bins
            if "g" in channels:
                bins["g"] = g_bins
            if "b" in channels:
                bins["b"] = b_bins
            self._stats["total_histograms"] += 1
            return FrameHistogram(bins=bins, total_pixels=total)

    def downsample(
        self,
        frame_id: str,
        target_width: int,
        target_height: int,
    ) -> Optional[CapturedFrame]:
        """Downsample a frame to a lower resolution using box averaging.

        Returns ``None`` if the frame is not found, the target resolution is
        non-positive, or the target exceeds the source resolution.
        """
        with self._lock:
            frame = self._frames_by_id.get(frame_id)
            if frame is None:
                return None
            return self._downsample_frame(frame, target_width, target_height)

    # ------------------------------------------------------------------
    # Synthetic generation
    # ------------------------------------------------------------------

    def generate_synthetic_frame(
        self,
        pattern: SyntheticPattern,
        dimensions: FrameDimensions,
        color1: Tuple[int, int, int, int] = (0, 0, 0, 255),
        color2: Tuple[int, int, int, int] = (255, 255, 255, 255),
    ) -> bytes:
        """Generate raw pixel data for ``pattern`` at ``dimensions``.

        Pure helper with no side effects on engine state. Uses only the
        standard library so that no third-party dependency is required.
        """
        with self._lock:
            width = dimensions.width
            height = dimensions.height
            fmt = dimensions.format

            if pattern == SyntheticPattern.SOLID_COLOR:
                pixel = _color_bytes(color1, fmt)
                return pixel * (width * height)

            if pattern == SyntheticPattern.HORIZONTAL_GRADIENT:
                buf = bytearray()
                denom = max(height - 1, 1)
                for r in range(height):
                    t = r / denom
                    row_pixel = _color_bytes(_lerp_color(color1, color2, t), fmt)
                    buf.extend(row_pixel * width)
                return bytes(buf)

            if pattern == SyntheticPattern.VERTICAL_GRADIENT:
                row = bytearray()
                denom = max(width - 1, 1)
                for c in range(width):
                    t = c / denom
                    row.extend(_color_bytes(_lerp_color(color1, color2, t), fmt))
                row_bytes = bytes(row)
                buf = bytearray()
                for _ in range(height):
                    buf.extend(row_bytes)
                return bytes(buf)

            if pattern == SyntheticPattern.CHECKERBOARD:
                buf = bytearray()
                block_rows = (height + 31) // 32
                for rb in range(block_rows):
                    row = bytearray()
                    for c in range(width):
                        cb = c // 32
                        color = color1 if (rb + cb) % 2 == 0 else color2
                        row.extend(_color_bytes(color, fmt))
                    row_bytes = bytes(row)
                    r_start = rb * 32
                    r_end = min(r_start + 32, height)
                    for _ in range(r_start, r_end):
                        buf.extend(row_bytes)
                return bytes(buf)

            if pattern == SyntheticPattern.RANDOM_NOISE:
                seed = ((width * 73856093) ^ (height * 19349663)) & 0xFFFFFFFF
                rng = random.Random(seed)
                return rng.randbytes(width * height * dimensions.bytes_per_pixel)

            if pattern == SyntheticPattern.DIAGONAL_STRIPES:
                buf = bytearray()
                for r in range(height):
                    row = bytearray()
                    for c in range(width):
                        color = color1 if ((r + c) // 16) % 2 == 0 else color2
                        row.extend(_color_bytes(color, fmt))
                    buf.extend(row)
                return bytes(buf)

            # Fallback: solid color.
            pixel = _color_bytes(color1, fmt)
            return pixel * (width * height)

    # ------------------------------------------------------------------
    # History configuration
    # ------------------------------------------------------------------

    def set_history_capacity(self, capacity: int) -> None:
        """Set the ring buffer capacity (clamped to ``[1, 1000]``).

        Evicts the oldest frames when shrinking below the current count.
        """
        with self._lock:
            capacity = max(1, min(capacity, self._max_history_capacity))
            self._history_capacity = capacity
            while len(self._history) > capacity:
                dropped = self._history.pop(0)
                self._frames_by_id.pop(dropped.id, None)
                self._dropped_frames += 1
            self._stats["dropped_frames"] = self._dropped_frames

    def get_history_snapshot(self) -> FrameHistorySnapshot:
        """Return a snapshot of the ring buffer state."""
        with self._lock:
            return FrameHistorySnapshot(
                capacity=self._history_capacity,
                current_count=len(self._history),
                oldest_frame_index=self._history[0].frame_index if self._history else 0,
                newest_frame_index=self._history[-1].frame_index if self._history else 0,
                total_captures=self._stats["captures_succeeded"],
                dropped_frames=self._dropped_frames,
            )

    def set_default_dimensions(self, dimensions: FrameDimensions) -> None:
        """Set the default dimensions used when no dimensions are provided."""
        with self._lock:
            self._default_dimensions = dimensions

    def get_default_dimensions(self) -> FrameDimensions:
        """Return the default capture dimensions."""
        with self._lock:
            return self._default_dimensions

    # ------------------------------------------------------------------
    # Status and lifecycle
    # ------------------------------------------------------------------

    def get_status(self) -> Dict[str, Any]:
        """Return a status dictionary describing engine state and stats."""
        with self._lock:
            status = dict(self._stats)
            status["source_count"] = len(self._sources)
            status["active_source"] = self._active_source_name
            status["history_capacity"] = self._history_capacity
            status["history_count"] = len(self._history)
            status["request_count"] = self._request_count
            status["default_dimensions"] = self._default_dimensions.to_dict()
            return status

    def get_snapshot(self) -> FrameCaptureSnapshot:
        """Return a structured snapshot of the engine state."""
        with self._lock:
            return FrameCaptureSnapshot(
                source_count=len(self._sources),
                request_count=self._request_count,
                history_capacity=self._history_capacity,
                history_count=len(self._history),
                stats=dict(self._stats),
            )

    def reset(self) -> None:
        """Reset all engine state and re-seed the default synthetic source."""
        with self._lock:
            self._sources.clear()
            self._active_source_name = None
            self._history.clear()
            self._frames_by_id.clear()
            self._frame_index_counter = 0
            self._dropped_frames = 0
            self._request_count = 0
            self._stats = {
                "total_captures": 0,
                "captures_succeeded": 0,
                "captures_failed": 0,
                "total_samples": 0,
                "total_histograms": 0,
                "total_downsamples": 0,
                "dropped_frames": 0,
                "last_capture_at": None,
                "last_error": None,
            }
            self.register_synthetic_source(
                "synthetic-default",
                SyntheticPattern.HORIZONTAL_GRADIENT,
                color1=(20, 30, 80, 255),
                color2=(180, 200, 255, 255),
            )
            self.set_active_source("synthetic-default")

    # ------------------------------------------------------------------
    # Internal helpers (caller holds lock)
    # ------------------------------------------------------------------

    def _descriptor_view(self, entry: _SourceEntry) -> FrameSourceDescriptor:
        """Build a fresh descriptor reflecting current active-source state."""
        return FrameSourceDescriptor(
            name=entry.descriptor.name,
            kind=entry.descriptor.kind,
            description=entry.descriptor.description,
            is_active=(entry.descriptor.name == self._active_source_name),
            capture_count=entry.descriptor.capture_count,
            last_capture_at=entry.descriptor.last_capture_at,
        )

    def _add_to_history(self, frame: CapturedFrame) -> None:
        """Append a frame to the ring buffer, evicting the oldest if full."""
        self._history.append(frame)
        self._frames_by_id[frame.id] = frame
        while len(self._history) > self._history_capacity:
            dropped = self._history.pop(0)
            self._frames_by_id.pop(dropped.id, None)
            self._dropped_frames += 1
        self._stats["dropped_frames"] = self._dropped_frames

    def _downsample_frame(
        self,
        frame: CapturedFrame,
        target_width: int,
        target_height: int,
    ) -> Optional[CapturedFrame]:
        """Box-filter downsample. Caller must hold the lock."""
        dims = frame.dimensions
        src_w = dims.width
        src_h = dims.height
        bpp = dims.bytes_per_pixel
        fmt = dims.format
        if target_width <= 0 or target_height <= 0:
            return None
        if target_width > src_w or target_height > src_h:
            return None
        out = bytearray(target_width * target_height * bpp)
        data = frame.data
        for oy in range(target_height):
            y0 = oy * src_h // target_height
            y1 = (oy + 1) * src_h // target_height
            if y1 <= y0:
                y1 = y0 + 1
            y1 = min(y1, src_h)
            for ox in range(target_width):
                x0 = ox * src_w // target_width
                x1 = (ox + 1) * src_w // target_width
                if x1 <= x0:
                    x1 = x0 + 1
                x1 = min(x1, src_w)
                sum_r = 0
                sum_g = 0
                sum_b = 0
                sum_a = 0
                count = 0
                for sy in range(y0, y1):
                    base = (sy * src_w + x0) * bpp
                    for _sx in range(x0, x1):
                        r, g, b, a = _read_pixel(data, base, fmt)
                        sum_r += r
                        sum_g += g
                        sum_b += b
                        sum_a += a
                        count += 1
                        base += bpp
                if count == 0:
                    continue
                avg = (sum_r // count, sum_g // count, sum_b // count, sum_a // count)
                off = (oy * target_width + ox) * bpp
                out[off : off + bpp] = _color_bytes(avg, fmt)
        self._stats["total_downsamples"] += 1
        new_dims = FrameDimensions(
            width=target_width,
            height=target_height,
            format=fmt,
            bytes_per_pixel=bpp,
            stride=target_width * bpp,
        )
        return CapturedFrame(
            source_kind=frame.source_kind,
            dimensions=new_dims,
            data=bytes(out),
            timestamp=datetime.datetime.utcnow().isoformat(),
            frame_index=frame.frame_index,
            metadata={
                "downsampled_from": frame.id,
                "source_frame_index": frame.frame_index,
            },
        )


def get_frame_capture() -> FrameCaptureEngine:
    """Return the singleton FrameCaptureEngine instance."""
    return FrameCaptureEngine.get_instance()
