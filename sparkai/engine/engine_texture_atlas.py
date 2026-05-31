"""
TextureAtlas - Dynamic texture atlas packing and sprite region management.

Packs multiple sprite textures into a single atlas texture to reduce draw
calls and GPU state changes. Supports multiple packing algorithms, atlas
resizing policies, and defragmentation for the SparkLabs game engine.
"""

import threading
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

_time_module = time


class PackingAlgorithm(Enum):
    """Algorithms for arranging sprite regions within an atlas.

    Each strategy optimizes for different use cases: BIN_PACK for general
    efficiency, GUILLOTINE for fast incremental placement, MAX_RECTS for
    maximum utilization, and SKYLINE for streaming texture updates.
    """

    BIN_PACK = "bin_pack"
    ROW_FIT = "row_fit"
    AREA_FIT = "area_fit"
    GUILLOTINE = "guillotine"
    MAX_RECTS = "max_rects"
    SKYLINE = "skyline"


class AtlasFormat(Enum):
    """Texture formats supported for atlas pages.

    Determines pixel layout, memory footprint, and color precision.
    COMPRESSED_DXT5 uses block compression for reduced GPU memory usage.
    """

    RGBA8888 = "rgba8888"
    RGB888 = "rgb888"
    RGBA4444 = "rgba4444"
    RGB565 = "rgb565"
    ALPHA8 = "alpha8"
    COMPRESSED_DXT5 = "compressed_dxt5"

    @property
    def bytes_per_pixel(self) -> float:
        """Returns the memory footprint in bytes per pixel for this format."""
        mapping = {
            AtlasFormat.RGBA8888: 4.0,
            AtlasFormat.RGB888: 3.0,
            AtlasFormat.RGBA4444: 2.0,
            AtlasFormat.RGB565: 2.0,
            AtlasFormat.ALPHA8: 1.0,
            AtlasFormat.COMPRESSED_DXT5: 1.0,
        }
        return mapping[self]

    @property
    def has_alpha(self) -> bool:
        """Whether this format includes an alpha channel."""
        return self in {
            AtlasFormat.RGBA8888,
            AtlasFormat.RGBA4444,
            AtlasFormat.ALPHA8,
            AtlasFormat.COMPRESSED_DXT5,
        }


class SpriteOrigin(Enum):
    """Coordinate origin conventions for sprite placement.

    Determines how offset_x and offset_y are interpreted relative to
    the sprite bounds. CUSTOM allows arbitrary origin positioning.
    """

    TOP_LEFT = "top_left"
    CENTER = "center"
    BOTTOM_CENTER = "bottom_center"
    CUSTOM = "custom"


class AtlasResizePolicy(Enum):
    """Policies governing atlas dimensions when space is exhausted.

    FIXED_SIZE never resizes and rejects sprites that do not fit.
    GROW_ONLY expands the atlas when needed but never shrinks it.
    DYNAMIC_RESIZE can both grow and shrink based on utilization.
    POWER_OF_TWO enforces power-of-two dimensions after each resize.
    """

    FIXED_SIZE = "fixed_size"
    GROW_ONLY = "grow_only"
    DYNAMIC_RESIZE = "dynamic_resize"
    POWER_OF_TWO = "power_of_two"


@dataclass
class SpriteRegion:
    """A rectangle within an atlas assigned to a single sprite.

    Tracks the sprite's position, size, and metadata including whether
    it was rotated or trimmed during packing. The original dimensions
    allow the engine to reconstruct untrimmed sprite bounds at runtime.
    """

    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    atlas_id: str = ""
    name: str = ""
    x: int = 0
    y: int = 0
    width: int = 0
    height: int = 0
    original_width: int = 0
    original_height: int = 0
    offset_x: int = 0
    offset_y: int = 0
    rotated: bool = False
    trimmed: bool = False

    def __post_init__(self) -> None:
        """Validates region dimensions after construction."""
        if self.width < 0:
            raise ValueError("width must be non-negative")
        if self.height < 0:
            raise ValueError("height must be non-negative")
        if self.original_width < 0:
            raise ValueError("original_width must be non-negative")
        if self.original_height < 0:
            raise ValueError("original_height must be non-negative")

    @property
    def area(self) -> int:
        """Total pixel area occupied by this region in the atlas."""
        return self.width * self.height

    @property
    def effective_width(self) -> int:
        """Width accounting for rotation (swapped if rotated)."""
        return self.height if self.rotated else self.width

    @property
    def effective_height(self) -> int:
        """Height accounting for rotation (swapped if rotated)."""
        return self.width if self.rotated else self.height

    def to_dict(self) -> dict:
        """Serializes the sprite region to a dictionary."""
        return {
            "id": self.id,
            "atlas_id": self.atlas_id,
            "name": self.name,
            "x": self.x,
            "y": self.y,
            "width": self.width,
            "height": self.height,
            "original_width": self.original_width,
            "original_height": self.original_height,
            "offset_x": self.offset_x,
            "offset_y": self.offset_y,
            "rotated": self.rotated,
            "trimmed": self.trimmed,
            "area": self.area,
        }

    def __repr__(self) -> str:
        return (
            f"SpriteRegion(id={self.id[:8]}..., name={self.name}, "
            f"pos=({self.x},{self.y}), size={self.width}x{self.height})"
        )


@dataclass
class AtlasPage:
    """A single texture atlas page containing packed sprite regions.

    Tracks dimensions, format, contained regions, and free space for
    incremental packing. Free space is represented as a list of
    non-overlapping rectangular areas available for new sprites.
    """

    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = ""
    width: int = 0
    height: int = 0
    format: AtlasFormat = AtlasFormat.RGBA8888
    regions: List[str] = field(default_factory=list)
    free_space: List[Dict[str, int]] = field(default_factory=list)
    utilization_pct: float = 0.0
    resize_policy: AtlasResizePolicy = AtlasResizePolicy.GROW_ONLY
    created_at: float = field(default_factory=_time_module.time)

    def __post_init__(self) -> None:
        """Validates atlas dimensions and initializes free space."""
        if self.width <= 0:
            raise ValueError("width must be positive")
        if self.height <= 0:
            raise ValueError("height must be positive")
        if not self.free_space:
            self.free_space = [
                {"x": 0, "y": 0, "w": self.width, "h": self.height}
            ]

    @property
    def total_area(self) -> int:
        """Total pixel area of this atlas page."""
        return self.width * self.height

    @property
    def used_area(self) -> int:
        """Total pixel area occupied by placed sprite regions.

        Computed from utilization_pct. May be approximate if regions
        have been modified externally.
        """
        return int(self.total_area * self.utilization_pct / 100.0)

    @property
    def free_area(self) -> int:
        """Total free pixel area available for new sprites.

        Summed from all free space rectangles.
        """
        return sum(rect["w"] * rect["h"] for rect in self.free_space)

    @property
    def free_rect_count(self) -> int:
        """Number of distinct free space rectangles."""
        return len(self.free_space)

    def to_dict(self) -> dict:
        """Serializes the atlas page to a dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "width": self.width,
            "height": self.height,
            "total_area": self.total_area,
            "format": self.format.value,
            "region_count": len(self.regions),
            "free_rect_count": self.free_rect_count,
            "free_area": self.free_area,
            "utilization_pct": self.utilization_pct,
            "bytes_per_pixel": self.format.bytes_per_pixel,
            "has_alpha": self.format.has_alpha,
            "memory_estimate_bytes": int(
                self.total_area * self.format.bytes_per_pixel
            ),
            "resize_policy": self.resize_policy.value,
            "created_at": self.created_at,
        }

    def __repr__(self) -> str:
        return (
            f"AtlasPage(id={self.id[:8]}..., name={self.name}, "
            f"size={self.width}x{self.height}, "
            f"regions={len(self.regions)}, "
            f"util={self.utilization_pct:.1f}%)"
        )


@dataclass
class PackResult:
    """Result of a pack operation on a texture atlas.

    Reports how many regions were successfully placed, how many were
    rejected due to insufficient space, the resulting atlas utilization,
    and the time taken to complete the packing computation.
    """

    atlas_id: str = ""
    atlas_name: str = ""
    regions_added: int = 0
    regions_rejected: int = 0
    new_utilization: float = 0.0
    packing_time_ms: float = 0.0
    algorithm: str = ""
    timestamp: float = field(default_factory=_time_module.time)

    @property
    def total_regions_processed(self) -> int:
        """Total number of regions considered during the pack."""
        return self.regions_added + self.regions_rejected

    @property
    def success_rate(self) -> float:
        """Ratio of successfully placed regions to total processed.

        Returns 0.0 if no regions were processed.
        """
        if self.total_regions_processed == 0:
            return 0.0
        return self.regions_added / self.total_regions_processed

    def to_dict(self) -> dict:
        """Serializes the pack result to a dictionary."""
        return {
            "atlas_id": self.atlas_id,
            "atlas_name": self.atlas_name,
            "regions_added": self.regions_added,
            "regions_rejected": self.regions_rejected,
            "total_regions_processed": self.total_regions_processed,
            "success_rate": round(self.success_rate, 4),
            "new_utilization": self.new_utilization,
            "packing_time_ms": self.packing_time_ms,
            "algorithm": self.algorithm,
            "timestamp": self.timestamp,
        }

    def __repr__(self) -> str:
        return (
            f"PackResult(atlas={self.atlas_name}, added={self.regions_added}, "
            f"rejected={self.regions_rejected}, util={self.new_utilization:.1f}%, "
            f"time={self.packing_time_ms:.2f}ms)"
        )


class TextureAtlas:
    """Singleton manager for texture atlas packing and sprite region tracking.

    Provides the central API for creating atlas textures, placing sprites
    using configurable packing algorithms, removing and querying regions,
    defragmenting atlases to consolidate free space, and resizing atlas
    pages according to configurable policies.

    Thread-safe via a reentrant lock. Use get_texture_atlas() or
    TextureAtlas.get_instance() to obtain the singleton instance.
    """

    _instance: Optional["TextureAtlas"] = None
    _lock: threading.RLock = threading.RLock()

    _DEFAULT_MAX_ATLAS_SIZE: Tuple[int, int] = (4096, 4096)
    _DEFAULT_PADDING: int = 1

    def __new__(cls) -> "TextureAtlas":
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
        self._atlases: Dict[str, AtlasPage] = {}
        self._regions: Dict[str, SpriteRegion] = {}
        self._pack_history: List[PackResult] = []
        self._max_atlas_size: Tuple[int, int] = self._DEFAULT_MAX_ATLAS_SIZE
        self._padding: int = self._DEFAULT_PADDING
        self._initialized = True

    @classmethod
    def get_instance(cls) -> "TextureAtlas":
        """Returns the singleton TextureAtlas instance."""
        return cls()

    # ------------------------------------------------------------------
    # Internal helpers: free space management
    # ------------------------------------------------------------------

    @staticmethod
    def _free_rect_fits(
        free_rect: Dict[str, int], width: int, height: int
    ) -> bool:
        """Checks whether a free rectangle can contain the given dimensions.

        Args:
            free_rect: Free rectangle dict with x, y, w, h keys.
            width: Required width.
            height: Required height.

        Returns:
            True if the free rectangle is large enough.
        """
        return free_rect["w"] >= width and free_rect["h"] >= height

    @staticmethod
    def _split_free_rect(
        free_rect: Dict[str, int],
        placed_x: int,
        placed_y: int,
        placed_w: int,
        placed_h: int,
    ) -> List[Dict[str, int]]:
        """Splits a free rectangle after placing a region inside it.

        Produces up to two new free rectangles: the area to the right
        of the placed region and the area below it. The split strategy
        uses a guillotine cut choosing the larger remainder.

        Args:
            free_rect: The original free rectangle being split.
            placed_x: X coordinate of the placed region.
            placed_y: Y coordinate of the placed region.
            placed_w: Width of the placed region.
            placed_h: Height of the placed region.

        Returns:
            A list of new free rectangles (0, 1, or 2 rectangles).
        """
        result: List[Dict[str, int]] = []

        right_w = free_rect["x"] + free_rect["w"] - (placed_x + placed_w)
        bottom_h = free_rect["y"] + free_rect["h"] - (placed_y + placed_h)

        if right_w > 0:
            result.append({
                "x": placed_x + placed_w,
                "y": placed_y,
                "w": right_w,
                "h": placed_h,
            })

        if bottom_h > 0:
            result.append({
                "x": free_rect["x"],
                "y": placed_y + placed_h,
                "w": free_rect["w"],
                "h": bottom_h,
            })

        if right_w > 0 and placed_h < free_rect["h"]:
            remaining_top_h = free_rect["y"] + free_rect["h"] - (placed_y + placed_h)
            if remaining_top_h > 0:
                result.append({
                    "x": placed_x + placed_w,
                    "y": placed_y + placed_h,
                    "w": right_w,
                    "h": remaining_top_h,
                })

        return result

    @staticmethod
    def _merge_free_space(free_space: List[Dict[str, int]]) -> List[Dict[str, int]]:
        """Merges adjacent or overlapping free rectangles where possible.

        Scans the free space list and combines rectangles that share
        edges, reducing fragmentation. This is a best-effort merge and
        may not produce the optimal set of maximal free rectangles.

        Args:
            free_space: List of free rectangle dicts.

        Returns:
            A (potentially shorter) list of merged free rectangles.
        """
        if len(free_space) <= 1:
            return list(free_space)

        merged = list(free_space)
        changed = True
        while changed:
            changed = False
            new_merged: List[Dict[str, int]] = []
            consumed: List[bool] = [False] * len(merged)

            for i, rect_a in enumerate(merged):
                if consumed[i]:
                    continue
                for j, rect_b in enumerate(merged):
                    if i >= j or consumed[j]:
                        continue

                    a_x2 = rect_a["x"] + rect_a["w"]
                    a_y2 = rect_a["y"] + rect_a["h"]
                    b_x2 = rect_b["x"] + rect_b["w"]
                    b_y2 = rect_b["y"] + rect_b["h"]

                    horizontal_merge = (
                        rect_a["y"] == rect_b["y"]
                        and rect_a["h"] == rect_b["h"]
                        and (a_x2 == rect_b["x"] or b_x2 == rect_a["x"])
                    )
                    vertical_merge = (
                        rect_a["x"] == rect_b["x"]
                        and rect_a["w"] == rect_b["w"]
                        and (a_y2 == rect_b["y"] or b_y2 == rect_a["y"])
                    )

                    if horizontal_merge or vertical_merge:
                        new_x = min(rect_a["x"], rect_b["x"])
                        new_y = min(rect_a["y"], rect_b["y"])
                        new_w = max(a_x2, b_x2) - new_x
                        new_h = max(a_y2, b_y2) - new_y
                        new_merged.append({
                            "x": new_x, "y": new_y,
                            "w": new_w, "h": new_h,
                        })
                        consumed[i] = True
                        consumed[j] = True
                        changed = True
                        break

                if not consumed[i]:
                    new_merged.append(dict(rect_a))

            merged = new_merged

        return merged

    @staticmethod
    def _sort_free_space_by_area(
        free_space: List[Dict[str, int]],
    ) -> List[Dict[str, int]]:
        """Sorts free rectangles by area in descending order.

        Larger free rectangles are prioritized during packing to avoid
        unnecessary fragmentation of smaller free areas.

        Args:
            free_space: List of free rectangle dicts.

        Returns:
            A new list sorted by area descending.
        """
        return sorted(
            free_space,
            key=lambda r: r["w"] * r["h"],
            reverse=True,
        )

    # ------------------------------------------------------------------
    # Internal helpers: packing algorithms
    # ------------------------------------------------------------------

    def _pack_bin_pack(
        self,
        atlas_width: int,
        atlas_height: int,
        region_specs: List[Tuple[str, int, int]],
    ) -> Tuple[Dict[str, Tuple[int, int]], List[str]]:
        """Shelf-based bin packing algorithm.

        Sorts regions by height descending, then places them into
        horizontal shelves (rows). Each shelf has a maximum height equal
        to the tallest region in that shelf. Regions are packed left to
        right within each shelf. A new shelf is started when the current
        shelf cannot accommodate the next region's width.

        Returns:
            A tuple of (placements dict, list of rejected region IDs).
        """
        sorted_specs = sorted(region_specs, key=lambda s: s[2], reverse=True)
        placements: Dict[str, Tuple[int, int]] = {}
        rejected: List[str] = []

        cursor_y = 0
        shelf_height = 0
        cursor_x = 0

        for region_id, rw, rh in sorted_specs:
            padded_w = rw + self._padding
            padded_h = rh + self._padding

            if padded_w > atlas_width or padded_h > atlas_height:
                rejected.append(region_id)
                continue

            if cursor_x + padded_w > atlas_width:
                cursor_y += shelf_height + self._padding
                cursor_x = 0
                shelf_height = 0

            if cursor_y + padded_h > atlas_height:
                rejected.append(region_id)
                continue

            if padded_h > shelf_height:
                shelf_height = padded_h

            placements[region_id] = (cursor_x, cursor_y)
            cursor_x += padded_w

        return placements, rejected

    def _pack_row_fit(
        self,
        atlas_width: int,
        atlas_height: int,
        region_specs: List[Tuple[str, int, int]],
    ) -> Tuple[Dict[str, Tuple[int, int]], List[str]]:
        """Row-based first-fit packing algorithm.

        Places regions left to right within rows, wrapping to the next
        row when the current row is exhausted. Each row's height is the
        maximum height of regions placed in that row.

        Returns:
            A tuple of (placements dict, list of rejected region IDs).
        """
        sorted_specs = sorted(region_specs, key=lambda s: s[2], reverse=True)
        placements: Dict[str, Tuple[int, int]] = {}
        rejected: List[str] = []

        rows: List[Dict[str, Any]] = [{"y": 0, "h": 0, "x": 0}]

        for region_id, rw, rh in sorted_specs:
            padded_w = rw + self._padding
            padded_h = rh + self._padding

            if padded_w > atlas_width or padded_h > atlas_height:
                rejected.append(region_id)
                continue

            placed = False
            for row in rows:
                if row["x"] + padded_w <= atlas_width and padded_h <= row["h"] if row["h"] > 0 else True:
                    if row["h"] == 0:
                        row["h"] = padded_h
                    if padded_h <= row["h"]:
                        placements[region_id] = (row["x"], row["y"])
                        row["x"] += padded_w
                        placed = True
                        break

            if not placed:
                prev_row = rows[-1]
                new_y = prev_row["y"] + prev_row["h"] + self._padding
                if new_y + padded_h > atlas_height:
                    rejected.append(region_id)
                    continue
                new_row = {"y": new_y, "h": padded_h, "x": 0}
                placements[region_id] = (0, new_y)
                new_row["x"] = padded_w
                rows.append(new_row)

        return placements, rejected

    def _pack_area_fit(
        self,
        atlas_width: int,
        atlas_height: int,
        region_specs: List[Tuple[str, int, int]],
    ) -> Tuple[Dict[str, Tuple[int, int]], List[str]]:
        """Area-descending first-fit packing algorithm.

        Sorts regions by area descending, then places each in the first
        free rectangle that fits. This greedy approach works well when
        regions have widely varying sizes.

        Returns:
            A tuple of (placements dict, list of rejected region IDs).
        """
        sorted_specs = sorted(
            region_specs, key=lambda s: s[1] * s[2], reverse=True
        )
        placements: Dict[str, Tuple[int, int]] = {}
        rejected: List[str] = []

        free_space: List[Dict[str, int]] = [
            {"x": 0, "y": 0, "w": atlas_width, "h": atlas_height}
        ]

        for region_id, rw, rh in sorted_specs:
            padded_w = rw + self._padding
            padded_h = rh + self._padding

            if padded_w > atlas_width or padded_h > atlas_height:
                rejected.append(region_id)
                continue

            placed = False
            for i, free_rect in enumerate(free_space):
                if self._free_rect_fits(free_rect, padded_w, padded_h):
                    px = free_rect["x"]
                    py = free_rect["y"]
                    placements[region_id] = (px, py)

                    new_free = self._split_free_rect(
                        free_rect, px, py, padded_w, padded_h
                    )
                    free_space.pop(i)
                    free_space.extend(new_free)
                    free_space = self._sort_free_space_by_area(free_space)
                    placed = True
                    break

            if not placed:
                rejected.append(region_id)

        return placements, rejected

    def _pack_guillotine(
        self,
        atlas_width: int,
        atlas_height: int,
        region_specs: List[Tuple[str, int, int]],
    ) -> Tuple[Dict[str, Tuple[int, int]], List[str]]:
        """Guillotine-cut packing algorithm.

        Places regions in the best-fit free rectangle, then splits the
        remaining space with a single cut (either horizontal or vertical)
        chosen to maximize the area of the larger remainder. This creates
        fewer but larger free rectangles compared to maxrects.

        Returns:
            A tuple of (placements dict, list of rejected region IDs).
        """
        sorted_specs = sorted(region_specs, key=lambda s: s[2], reverse=True)
        placements: Dict[str, Tuple[int, int]] = {}
        rejected: List[str] = []

        free_space: List[Dict[str, int]] = [
            {"x": 0, "y": 0, "w": atlas_width, "h": atlas_height}
        ]

        for region_id, rw, rh in sorted_specs:
            padded_w = rw + self._padding
            padded_h = rh + self._padding

            if padded_w > atlas_width or padded_h > atlas_height:
                rejected.append(region_id)
                continue

            best_idx = -1
            best_waste = float("inf")

            for i, free_rect in enumerate(free_space):
                if not self._free_rect_fits(free_rect, padded_w, padded_h):
                    continue
                waste = (
                    free_rect["w"] * free_rect["h"] - padded_w * padded_h
                )
                if waste < best_waste:
                    best_waste = waste
                    best_idx = i

            if best_idx < 0:
                rejected.append(region_id)
                continue

            free_rect = free_space.pop(best_idx)
            px = free_rect["x"]
            py = free_rect["y"]
            placements[region_id] = (px, py)

            right_w = free_rect["w"] - padded_w
            bottom_h = free_rect["h"] - padded_h

            if right_w > 0 and bottom_h > 0:
                if right_w * padded_h >= bottom_h * padded_w:
                    free_space.append({
                        "x": px + padded_w, "y": py,
                        "w": right_w, "h": padded_h,
                    })
                    free_space.append({
                        "x": px, "y": py + padded_h,
                        "w": free_rect["w"], "h": bottom_h,
                    })
                else:
                    free_space.append({
                        "x": px, "y": py + padded_h,
                        "w": padded_w, "h": bottom_h,
                    })
                    free_space.append({
                        "x": px + padded_w, "y": py,
                        "w": right_w, "h": free_rect["h"],
                    })
            elif right_w > 0:
                free_space.append({
                    "x": px + padded_w, "y": py,
                    "w": right_w, "h": free_rect["h"],
                })
            elif bottom_h > 0:
                free_space.append({
                    "x": px, "y": py + padded_h,
                    "w": free_rect["w"], "h": bottom_h,
                })

            free_space = self._sort_free_space_by_area(free_space)

        return placements, rejected

    def _pack_max_rects(
        self,
        atlas_width: int,
        atlas_height: int,
        region_specs: List[Tuple[str, int, int]],
    ) -> Tuple[Dict[str, Tuple[int, int]], List[str]]:
        """Maximal rectangles packing algorithm.

        Maintains a set of all maximal free rectangles and chooses the
        best-fit (smallest free rect that fits) for each region. After
        each placement, the free rectangle set is updated: the chosen
        rectangle is split, and any new rectangles fully contained
        within others are culled.

        Returns:
            A tuple of (placements dict, list of rejected region IDs).
        """
        sorted_specs = sorted(
            region_specs, key=lambda s: s[1] * s[2], reverse=True
        )
        placements: Dict[str, Tuple[int, int]] = {}
        rejected: List[str] = []

        free_space: List[Dict[str, int]] = [
            {"x": 0, "y": 0, "w": atlas_width, "h": atlas_height}
        ]

        for region_id, rw, rh in sorted_specs:
            padded_w = rw + self._padding
            padded_h = rh + self._padding

            if padded_w > atlas_width or padded_h > atlas_height:
                rejected.append(region_id)
                continue

            best_idx = -1
            best_area = float("inf")

            for i, free_rect in enumerate(free_space):
                if self._free_rect_fits(free_rect, padded_w, padded_h):
                    area = free_rect["w"] * free_rect["h"]
                    if area < best_area:
                        best_area = area
                        best_idx = i

            if best_idx < 0:
                rejected.append(region_id)
                continue

            free_rect = free_space.pop(best_idx)
            px = free_rect["x"]
            py = free_rect["y"]
            placements[region_id] = (px, py)

            new_rects = self._split_free_rect(
                free_rect, px, py, padded_w, padded_h
            )
            free_space.extend(new_rects)

            filtered: List[Dict[str, int]] = []
            for i, rect_a in enumerate(free_space):
                contained = False
                for j, rect_b in enumerate(free_space):
                    if i == j:
                        continue
                    if (
                        rect_b["x"] <= rect_a["x"]
                        and rect_b["y"] <= rect_a["y"]
                        and rect_b["x"] + rect_b["w"]
                        >= rect_a["x"] + rect_a["w"]
                        and rect_b["y"] + rect_b["h"]
                        >= rect_a["y"] + rect_a["h"]
                        and (
                            rect_b["w"] > rect_a["w"]
                            or rect_b["h"] > rect_a["h"]
                            or rect_b["x"] < rect_a["x"]
                            or rect_b["y"] < rect_a["y"]
                        )
                    ):
                        contained = True
                        break
                if not contained:
                    filtered.append(rect_a)
            free_space = filtered

        return placements, rejected

    def _pack_skyline(
        self,
        atlas_width: int,
        atlas_height: int,
        region_specs: List[Tuple[str, int, int]],
    ) -> Tuple[Dict[str, Tuple[int, int]], List[str]]:
        """Skyline (bottom-left) packing algorithm.

        Maintains a skyline profile representing the top edge of packed
        regions. Each new region is placed at the lowest available point
        on the skyline where it fits horizontally. This produces tightly
        packed, bottom-left-optimized layouts.

        Returns:
            A tuple of (placements dict, list of rejected region IDs).
        """
        sorted_specs = sorted(region_specs, key=lambda s: s[2], reverse=True)
        placements: Dict[str, Tuple[int, int]] = {}
        rejected: List[str] = []

        skyline: List[Dict[str, int]] = [
            {"x": 0, "y": 0, "w": atlas_width}
        ]

        for region_id, rw, rh in sorted_specs:
            padded_w = rw + self._padding
            padded_h = rh + self._padding

            if padded_w > atlas_width or padded_h > atlas_height:
                rejected.append(region_id)
                continue

            best_idx = -1
            best_y = float("inf")

            for i, node in enumerate(skyline):
                remaining = node["w"]
                j = i
                while j < len(skyline) and remaining < padded_w:
                    j += 1
                    if j < len(skyline):
                        remaining += skyline[j]["w"]

                if remaining >= padded_w:
                    max_y = max(
                        skyline[k]["y"] for k in range(i, min(j + 1, len(skyline)))
                    )
                    if max_y + padded_h <= atlas_height and max_y < best_y:
                        best_y = max_y
                        best_idx = i

            if best_idx < 0:
                rejected.append(region_id)
                continue

            px = skyline[best_idx]["x"]
            py = best_y
            placements[region_id] = (px, py)

            covered = 0
            new_skyline: List[Dict[str, int]] = []
            consumed_range = False

            for i, node in enumerate(skyline):
                if i < best_idx and not consumed_range:
                    new_skyline.append(node)
                    continue

                if not consumed_range:
                    if covered + node["w"] <= padded_w:
                        if node["y"] < py + padded_h:
                            pass
                        covered += node["w"]
                        if covered >= padded_w:
                            new_skyline.append({
                                "x": px,
                                "y": py + padded_h,
                                "w": padded_w,
                            })
                            if covered > padded_w:
                                new_skyline.append({
                                    "x": px + padded_w,
                                    "y": node["y"],
                                    "w": covered - padded_w,
                                })
                            consumed_range = True
                        continue
                    else:
                        partial = padded_w - covered
                        new_skyline.append({
                            "x": px,
                            "y": py + padded_h,
                            "w": padded_w,
                        })
                        new_skyline.append({
                            "x": px + padded_w,
                            "y": node["y"],
                            "w": node["w"] - partial,
                        })
                        consumed_range = True
                        continue

                new_skyline.append(node)

            if not consumed_range:
                new_skyline.append({
                    "x": px,
                    "y": py + padded_h,
                    "w": padded_w,
                })

            skyline = self._merge_skyline(new_skyline)

        return placements, rejected

    @staticmethod
    def _merge_skyline(
        skyline: List[Dict[str, int]],
    ) -> List[Dict[str, int]]:
        """Merges adjacent skyline segments at the same height.

        Args:
            skyline: Skyline node list.

        Returns:
            A new merged skyline list.
        """
        if not skyline:
            return []
        merged: List[Dict[str, int]] = []
        current = dict(skyline[0])
        for node in skyline[1:]:
            if node["y"] == current["y"]:
                current["w"] = (node["x"] + node["w"]) - current["x"]
            else:
                merged.append(current)
                current = dict(node)
        merged.append(current)
        return merged

    def _get_packing_function(self, algorithm: PackingAlgorithm):
        """Returns the packing function for the given algorithm.

        Args:
            algorithm: The PackingAlgorithm to resolve.

        Returns:
            A callable that performs the packing operation.
        """
        mapping = {
            PackingAlgorithm.BIN_PACK: self._pack_bin_pack,
            PackingAlgorithm.ROW_FIT: self._pack_row_fit,
            PackingAlgorithm.AREA_FIT: self._pack_area_fit,
            PackingAlgorithm.GUILLOTINE: self._pack_guillotine,
            PackingAlgorithm.MAX_RECTS: self._pack_max_rects,
            PackingAlgorithm.SKYLINE: self._pack_skyline,
        }
        return mapping[algorithm]

    # ------------------------------------------------------------------
    # Internal helpers: atlas utilities
    # ------------------------------------------------------------------

    def _get_atlas(self, atlas_id: str) -> AtlasPage:
        """Retrieves an atlas by name, raising if not found.

        Args:
            atlas_id: The name of the atlas to retrieve.

        Returns:
            The AtlasPage instance.

        Raises:
            KeyError: If no atlas exists with the given name.
        """
        if atlas_id not in self._atlases:
            raise KeyError(f"Atlas '{atlas_id}' not found")
        return self._atlases[atlas_id]

    def _compute_utilization(self, atlas: AtlasPage) -> float:
        """Recomputes the utilization percentage for an atlas.

        Sums the area of all registered sprite regions and divides by
        the total atlas area.

        Args:
            atlas: The AtlasPage to compute utilization for.

        Returns:
            Utilization as a percentage (0.0 to 100.0).
        """
        if atlas.total_area == 0:
            return 0.0
        used = 0
        for region_id in atlas.regions:
            region = self._regions.get(region_id)
            if region is not None:
                used += region.area
        return (used / atlas.total_area) * 100.0

    def _reconstruct_free_space(self, atlas: AtlasPage) -> List[Dict[str, int]]:
        """Reconstructs free space for an atlas from placed regions.

        Starts with the full atlas area and subtracts each placed region,
        producing a list of non-overlapping free rectangles.

        Args:
            atlas: The AtlasPage to reconstruct free space for.

        Returns:
            A list of free rectangle dicts.
        """
        free_space: List[Dict[str, int]] = [
            {"x": 0, "y": 0, "w": atlas.width, "h": atlas.height}
        ]

        for region_id in atlas.regions:
            region = self._regions.get(region_id)
            if region is None:
                continue

            new_free: List[Dict[str, int]] = []
            for free_rect in free_space:
                if (
                    region.x >= free_rect["x"] + free_rect["w"]
                    or region.x + region.width <= free_rect["x"]
                    or region.y >= free_rect["y"] + free_rect["h"]
                    or region.y + region.height <= free_rect["y"]
                ):
                    new_free.append(free_rect)
                    continue

                splits = self._split_free_rect(
                    free_rect,
                    region.x - self._padding,
                    region.y - self._padding,
                    region.width + 2 * self._padding,
                    region.height + 2 * self._padding,
                )
                new_free.extend(splits)

            free_space = new_free

        return self._merge_free_space(free_space)

    def _apply_packing_result(
        self,
        atlas: AtlasPage,
        placements: Dict[str, Tuple[int, int]],
        region_specs: List[Tuple[str, int, int]],
    ) -> None:
        """Applies packing placements to region objects and the atlas.

        Updates each placed region's x/y coordinates and links them
        to the atlas. Rejects are removed from the atlas regions list.

        Args:
            atlas: The AtlasPage to update.
            placements: Dict mapping region IDs to (x, y) tuples.
            region_specs: List of (region_id, width, height) tuples.
        """
        atlas.regions = []
        for region_id, rw, rh in region_specs:
            if region_id in placements:
                x, y = placements[region_id]
                region = self._regions.get(region_id)
                if region is not None:
                    region.x = x
                    region.y = y
                atlas.regions.append(region_id)

        atlas.free_space = self._reconstruct_free_space(atlas)
        atlas.utilization_pct = self._compute_utilization(atlas)

    def _should_resize_atlas(
        self,
        atlas: AtlasPage,
        reject_count: int,
        total_count: int,
    ) -> bool:
        """Determines whether an atlas should be resized after packing.

        Considers the atlas's resize policy and the ratio of rejected
        regions to total regions processed.

        Args:
            atlas: The AtlasPage to evaluate.
            reject_count: Number of regions rejected during packing.
            total_count: Total number of regions processed.

        Returns:
            True if the atlas should be resized.
        """
        if atlas.resize_policy == AtlasResizePolicy.FIXED_SIZE:
            return False
        if reject_count == 0:
            return False
        if total_count == 0:
            return False
        rejection_ratio = reject_count / total_count
        return rejection_ratio > 0.0

    def _grow_atlas(
        self,
        atlas: AtlasPage,
        additional_area: int,
    ) -> None:
        """Grows an atlas to accommodate the given additional area.

        Expands the atlas dimensions proportionally, respecting the
        maximum atlas size constraint. For POWER_OF_TWO policy, the
        new dimensions are rounded up to the next power of two.

        Args:
            atlas: The AtlasPage to resize.
            additional_area: Minimum additional area needed.
        """
        current_area = atlas.total_area
        target_area = current_area + additional_area

        area_ratio = target_area / current_area
        scale_factor = area_ratio ** 0.5

        new_width = int(atlas.width * scale_factor)
        new_height = int(atlas.height * scale_factor)

        if atlas.resize_policy == AtlasResizePolicy.POWER_OF_TWO:
            new_width = self._next_power_of_two(new_width)
            new_height = self._next_power_of_two(new_height)

        max_w, max_h = self._max_atlas_size
        new_width = min(new_width, max_w)
        new_height = min(new_height, max_h)

        if new_width <= atlas.width and new_height <= atlas.height:
            return

        self._resize_atlas_internal(atlas, new_width, new_height)

    @staticmethod
    def _next_power_of_two(value: int) -> int:
        """Returns the next power of two >= value, minimum 1."""
        if value <= 1:
            return 1
        power = 1
        while power < value:
            power <<= 1
        return power

    def _resize_atlas_internal(
        self,
        atlas: AtlasPage,
        new_width: int,
        new_height: int,
    ) -> None:
        """Updates atlas dimensions and rebuilds free space.

        Args:
            atlas: The AtlasPage to resize.
            new_width: New atlas width in pixels.
            new_height: New atlas height in pixels.
        """
        atlas.width = new_width
        atlas.height = new_height
        atlas.free_space = self._reconstruct_free_space(atlas)
        atlas.utilization_pct = self._compute_utilization(atlas)

    # ------------------------------------------------------------------
    # Public API: Atlas management
    # ------------------------------------------------------------------

    def create_atlas(
        self,
        name: str,
        width: int,
        height: int,
        format: AtlasFormat = AtlasFormat.RGBA8888,
        resize_policy: AtlasResizePolicy = AtlasResizePolicy.GROW_ONLY,
    ) -> AtlasPage:
        """Creates a new texture atlas page.

        The atlas is stored by name and can be referenced by that name
        in all subsequent operations. The initial free space covers the
        entire atlas area.

        Args:
            name: Unique name identifying this atlas.
            width: Atlas width in pixels. Must be positive.
            height: Atlas height in pixels. Must be positive.
            format: Pixel format for the atlas texture.
            resize_policy: Policy determining if/how the atlas resizes.

        Returns:
            The newly created AtlasPage instance.

        Raises:
            ValueError: If width or height is not positive.
            ValueError: If an atlas with the given name already exists.
        """
        with self._lock:
            if name in self._atlases:
                raise ValueError(f"Atlas '{name}' already exists")

            max_w, max_h = self._max_atlas_size
            if width > max_w or height > max_h:
                raise ValueError(
                    f"Atlas dimensions ({width}x{height}) exceed "
                    f"maximum ({max_w}x{max_h})"
                )

            atlas = AtlasPage(
                name=name,
                width=width,
                height=height,
                format=format,
                resize_policy=resize_policy,
            )
            self._atlases[name] = atlas
            return atlas

    def get_atlas(self, atlas_id: str) -> AtlasPage:
        """Retrieves an atlas page by name.

        Args:
            atlas_id: The name of the atlas to retrieve.

        Returns:
            The AtlasPage instance.

        Raises:
            KeyError: If no atlas is found with the given name.
        """
        with self._lock:
            return self._get_atlas(atlas_id)

    def remove_atlas(self, atlas_id: str) -> bool:
        """Removes an atlas and all its sprite regions.

        All SpriteRegion objects associated with this atlas are also
        removed from the region registry.

        Args:
            atlas_id: The name of the atlas to remove.

        Returns:
            True if the atlas was found and removed, False otherwise.
        """
        with self._lock:
            if atlas_id not in self._atlases:
                return False
            atlas = self._atlases.pop(atlas_id)
            for region_id in atlas.regions:
                self._regions.pop(region_id, None)
            return True

    # ------------------------------------------------------------------
    # Public API: Sprite management
    # ------------------------------------------------------------------

    def add_sprite(
        self,
        atlas_id: str,
        sprite_name: str,
        width: int,
        height: int,
        origin: SpriteOrigin = SpriteOrigin.TOP_LEFT,
        original_width: Optional[int] = None,
        original_height: Optional[int] = None,
    ) -> SpriteRegion:
        """Adds a sprite region to an atlas using incremental placement.

        Attempts to find a free space for the sprite within the atlas.
        If placement fails and the resize policy permits, the atlas is
        grown and placement is retried once.

        Args:
            atlas_id: The name of the target atlas.
            sprite_name: Human-readable name for the sprite.
            width: Width of the sprite in pixels. Must be positive.
            height: Height of the sprite in pixels. Must be positive.
            origin: The sprite's coordinate origin convention.
            original_width: Original (untrimmed) width. Defaults to width.
            original_height: Original (untrimmed) height. Defaults to height.

        Returns:
            The created SpriteRegion with assigned coordinates.

        Raises:
            KeyError: If the atlas does not exist.
            ValueError: If the sprite cannot be placed even after resizing.
        """
        if width <= 0 or height <= 0:
            raise ValueError("Sprite width and height must be positive")

        with self._lock:
            atlas = self._get_atlas(atlas_id)

            if original_width is None:
                original_width = width
            if original_height is None:
                original_height = height

            padded_w = width + self._padding
            padded_h = height + self._padding

            region = SpriteRegion(
                atlas_id=atlas.name,
                name=sprite_name,
                width=width,
                height=height,
                original_width=original_width,
                original_height=original_height,
                trimmed=(original_width != width or original_height != height),
            )

            self._compute_sprite_offsets(region, origin)

            placed = self._place_single_region(atlas, region.id, padded_w, padded_h)

            if not placed and atlas.resize_policy != AtlasResizePolicy.FIXED_SIZE:
                if self._should_resize_atlas(atlas, 1, 1):
                    needed_area = padded_w * padded_h
                    self._grow_atlas(atlas, needed_area)
                    placed = self._place_single_region(
                        atlas, region.id, padded_w, padded_h
                    )

            if not placed:
                raise ValueError(
                    f"Cannot place sprite '{sprite_name}' "
                    f"({padded_w}x{padded_h}) in atlas '{atlas_id}' "
                    f"({atlas.width}x{atlas.height})"
                )

            self._regions[region.id] = region
            atlas.regions.append(region.id)
            atlas.utilization_pct = self._compute_utilization(atlas)

            return region

    def _compute_sprite_offsets(
        self,
        region: SpriteRegion,
        origin: SpriteOrigin,
    ) -> None:
        """Computes offset_x and offset_y based on the sprite origin.

        Args:
            region: The SpriteRegion to compute offsets for.
            origin: The coordinate origin convention.
        """
        if origin == SpriteOrigin.CENTER:
            region.offset_x = -(region.original_width // 2)
            region.offset_y = -(region.original_height // 2)
        elif origin == SpriteOrigin.BOTTOM_CENTER:
            region.offset_x = -(region.original_width // 2)
            region.offset_y = -region.original_height
        elif origin == SpriteOrigin.TOP_LEFT:
            region.offset_x = 0
            region.offset_y = 0

    def _place_single_region(
        self,
        atlas: AtlasPage,
        region_id: str,
        padded_w: int,
        padded_h: int,
    ) -> bool:
        """Attempts to place a single region in the atlas free space.

        Uses first-fit strategy: finds the first free rectangle that
        can accommodate the region dimensions.

        Args:
            atlas: The AtlasPage to place into.
            region_id: The region's unique identifier.
            padded_w: Region width including padding.
            padded_h: Region height including padding.

        Returns:
            True if placement succeeded, False otherwise.
        """
        for i, free_rect in enumerate(atlas.free_space):
            if self._free_rect_fits(free_rect, padded_w, padded_h):
                px = free_rect["x"]
                py = free_rect["y"]
                region = self._regions.get(region_id)
                if region is not None:
                    region.x = px
                    region.y = py

                new_free = self._split_free_rect(
                    free_rect, px, py, padded_w, padded_h
                )
                atlas.free_space.pop(i)
                atlas.free_space.extend(new_free)
                atlas.free_space = self._merge_free_space(atlas.free_space)
                return True
        return False

    def remove_sprite(self, region_id: str) -> bool:
        """Removes a sprite region from its atlas.

        Frees the space occupied by the region so it can be reused by
        subsequent sprite placements or pack operations.

        Args:
            region_id: The unique ID of the SpriteRegion to remove.

        Returns:
            True if the region was found and removed, False otherwise.
        """
        with self._lock:
            if region_id not in self._regions:
                return False

            region = self._regions.pop(region_id)
            atlas = self._atlases.get(region.atlas_id)
            if atlas is not None and region_id in atlas.regions:
                atlas.regions.remove(region_id)
                atlas.free_space = self._reconstruct_free_space(atlas)
                atlas.utilization_pct = self._compute_utilization(atlas)

            return True

    def get_region(self, region_id: str) -> Optional[SpriteRegion]:
        """Retrieves a sprite region by its unique ID.

        Args:
            region_id: The unique ID of the SpriteRegion.

        Returns:
            The SpriteRegion if found, None otherwise.
        """
        with self._lock:
            return self._regions.get(region_id)

    def get_regions_in_atlas(self, atlas_id: str) -> List[SpriteRegion]:
        """Returns all sprite regions in a given atlas.

        Args:
            atlas_id: The name of the atlas to query.

        Returns:
            A list of SpriteRegion objects in the atlas.

        Raises:
            KeyError: If the atlas does not exist.
        """
        with self._lock:
            atlas = self._get_atlas(atlas_id)
            return [
                self._regions[rid]
                for rid in atlas.regions
                if rid in self._regions
            ]

    # ------------------------------------------------------------------
    # Public API: Packing
    # ------------------------------------------------------------------

    def pack_atlas(
        self,
        atlas_id: str,
        algorithm: PackingAlgorithm = PackingAlgorithm.MAX_RECTS,
    ) -> PackResult:
        """Re-packs all sprite regions in an atlas using the given algorithm.

        Clears all current placements and re-arranges every region from
        scratch. Regions that cannot be placed trigger an atlas resize
        if the policy allows, followed by a retry. Rejected regions are
        removed from the atlas.

        Args:
            atlas_id: The name of the atlas to pack.
            algorithm: The packing algorithm to use.

        Returns:
            A PackResult with statistics about the operation.

        Raises:
            KeyError: If the atlas does not exist.
        """
        with self._lock:
            atlas = self._get_atlas(atlas_id)
            pack_fn = self._get_packing_function(algorithm)

            region_specs: List[Tuple[str, int, int]] = []
            for region_id in atlas.regions:
                region = self._regions.get(region_id)
                if region is not None:
                    region_specs.append((region_id, region.width, region.height))

            start_time = _time_module.perf_counter()

            placements, rejected = pack_fn(
                atlas.width, atlas.height, region_specs
            )

            if rejected and atlas.resize_policy != AtlasResizePolicy.FIXED_SIZE:
                rejected_total_area = sum(
                    w * h
                    for rid, w, h in region_specs
                    if rid in rejected
                )
                if rejected_total_area > 0:
                    self._grow_atlas(atlas, rejected_total_area)
                    placements, rejected = pack_fn(
                        atlas.width, atlas.height, region_specs
                    )

            self._apply_packing_result(atlas, placements, region_specs)

            end_time = _time_module.perf_counter()
            packing_time_ms = (end_time - start_time) * 1000.0

            for rid in rejected:
                atlas.regions.remove(rid)

            result = PackResult(
                atlas_id=atlas.id,
                atlas_name=atlas.name,
                regions_added=len(placements),
                regions_rejected=len(rejected),
                new_utilization=atlas.utilization_pct,
                packing_time_ms=round(packing_time_ms, 3),
                algorithm=algorithm.value,
            )

            self._pack_history.append(result)
            return result

    def defragment_atlas(self, atlas_id: str) -> AtlasPage:
        """Defragments an atlas by re-packing all regions to consolidate free space.

        Uses MAX_RECTS for maximum space efficiency. After defragmentation,
        the free space is consolidated into fewer, larger contiguous blocks,
        improving the success rate of subsequent incremental placements.

        Args:
            atlas_id: The name of the atlas to defragment.

        Returns:
            The updated AtlasPage instance.

        Raises:
            KeyError: If the atlas does not exist.
        """
        with self._lock:
            atlas = self._get_atlas(atlas_id)
            self.pack_atlas(atlas_id, PackingAlgorithm.MAX_RECTS)

            atlas.free_space = self._merge_free_space(atlas.free_space)
            atlas.utilization_pct = self._compute_utilization(atlas)
            return atlas

    def resize_atlas(
        self,
        atlas_id: str,
        new_width: int,
        new_height: int,
    ) -> AtlasPage:
        """Resizes an atlas to new dimensions.

        If the new dimensions are smaller than the current ones, any
        regions that no longer fit are removed. The resize respects
        the atlas's configured resize policy.

        Args:
            atlas_id: The name of the atlas to resize.
            new_width: New atlas width in pixels. Must be positive.
            new_height: New atlas height in pixels. Must be positive.

        Returns:
            The updated AtlasPage instance.

        Raises:
            KeyError: If the atlas does not exist.
            ValueError: If dimensions are not positive or exceed max size.
        """
        if new_width <= 0 or new_height <= 0:
            raise ValueError("Atlas dimensions must be positive")

        with self._lock:
            atlas = self._get_atlas(atlas_id)

            max_w, max_h = self._max_atlas_size
            if new_width > max_w or new_height > max_h:
                raise ValueError(
                    f"Requested size ({new_width}x{new_height}) exceeds "
                    f"max ({max_w}x{max_h})"
                )

            if atlas.resize_policy == AtlasResizePolicy.FIXED_SIZE:
                raise ValueError(
                    f"Cannot resize atlas '{atlas_id}': "
                    f"policy is FIXED_SIZE"
                )

            removed: List[str] = []
            for region_id in list(atlas.regions):
                region = self._regions.get(region_id)
                if region is None:
                    continue
                if (
                    region.x + region.width > new_width
                    or region.y + region.height > new_height
                ):
                    removed.append(region_id)

            for region_id in removed:
                atlas.regions.remove(region_id)

            self._resize_atlas_internal(atlas, new_width, new_height)
            return atlas

    # ------------------------------------------------------------------
    # Public API: Configuration
    # ------------------------------------------------------------------

    def set_max_atlas_size(self, width: int, height: int) -> None:
        """Sets the maximum atlas dimensions for all atlases.

        Existing atlases larger than the new maximum are not resized.
        New atlases and automatic growth respect this constraint.

        Args:
            width: Maximum atlas width in pixels.
            height: Maximum atlas height in pixels.

        Raises:
            ValueError: If either dimension is not positive.
        """
        if width <= 0 or height <= 0:
            raise ValueError("Max atlas dimensions must be positive")
        with self._lock:
            self._max_atlas_size = (width, height)

    def set_padding(self, padding: int) -> None:
        """Sets the padding between adjacent sprites in the atlas.

        Padding prevents texture bleeding (edge pixels from adjacent
        sprites leaking into the rendered sprite when sampling near
        region boundaries).

        Args:
            padding: Padding in pixels. Must be non-negative.
        """
        if padding < 0:
            raise ValueError("Padding must be non-negative")
        with self._lock:
            self._padding = padding

    # ------------------------------------------------------------------
    # Public API: Statistics and queries
    # ------------------------------------------------------------------

    def get_stats(self) -> Dict[str, Any]:
        """Returns comprehensive statistics for all atlases and regions.

        Includes atlas counts, region totals, utilization metrics,
        packing history summary, free space tracking, and format
        memory estimates.

        Returns:
            A dictionary with string keys and varied value types.
        """
        with self._lock:
            atlas_count = len(self._atlases)
            region_count = len(self._regions)

            total_atlas_area = sum(a.total_area for a in self._atlases.values())
            total_used_area = sum(r.area for r in self._regions.values())
            total_free_area = sum(
                a.free_area for a in self._atlases.values()
            )

            overall_utilization = 0.0
            if total_atlas_area > 0:
                overall_utilization = (
                    total_used_area / total_atlas_area
                ) * 100.0

            atlas_details: List[Dict[str, Any]] = []
            for atlas in self._atlases.values():
                atlas_details.append({
                    "name": atlas.name,
                    "id": atlas.id,
                    "width": atlas.width,
                    "height": atlas.height,
                    "format": atlas.format.value,
                    "region_count": len(atlas.regions),
                    "free_rect_count": atlas.free_rect_count,
                    "utilization_pct": round(atlas.utilization_pct, 2),
                    "resize_policy": atlas.resize_policy.value,
                })

            total_packs = len(self._pack_history)
            avg_packing_time_ms = 0.0
            if total_packs > 0:
                avg_packing_time_ms = sum(
                    p.packing_time_ms for p in self._pack_history
                ) / total_packs

            total_regions_added = 0
            total_regions_rejected = 0
            total_packing_res = 0
            for p in self._pack_history:
                total_packing_res += 1
                total_regions_added += p.regions_added
                total_regions_rejected += p.regions_rejected

            packed_success_rate = 0.0
            total_processed = total_regions_added + total_regions_rejected
            if total_processed > 0:
                packed_success_rate = total_regions_added / total_processed

            algorithm_counts: Dict[str, int] = {}
            for p in self._pack_history:
                algo = p.algorithm
                algorithm_counts[algo] = algorithm_counts.get(algo, 0) + 1

            rotated_count = sum(1 for r in self._regions.values() if r.rotated)
            trimmed_count = sum(1 for r in self._regions.values() if r.trimmed)

            total_memory_estimate_bytes = sum(
                a.total_area * a.format.bytes_per_pixel
                for a in self._atlases.values()
            )

            return {
                "atlas_count": atlas_count,
                "region_count": region_count,
                "total_atlas_area": total_atlas_area,
                "total_used_area": total_used_area,
                "total_free_area": total_free_area,
                "overall_utilization_pct": round(overall_utilization, 2),
                "max_atlas_size": list(self._max_atlas_size),
                "padding": self._padding,
                "rotated_regions": rotated_count,
                "trimmed_regions": trimmed_count,
                "total_memory_estimate_bytes": int(total_memory_estimate_bytes),
                "atlas_details": atlas_details,
                "pack_history_count": total_packs,
                "avg_packing_time_ms": round(avg_packing_time_ms, 3),
                "packed_regions_added_total": total_regions_added,
                "packed_regions_rejected_total": total_regions_rejected,
                "packed_success_rate": round(packed_success_rate, 4),
                "algorithm_usage": algorithm_counts,
            }

    def get_pack_history(self) -> List[PackResult]:
        """Returns the complete packing history.

        Returns:
            A copy of the pack history list.
        """
        with self._lock:
            return list(self._pack_history)

    def clear_pack_history(self) -> None:
        """Clears all pack history records."""
        with self._lock:
            self._pack_history.clear()

    # ------------------------------------------------------------------
    # Public API: Lifecycle
    # ------------------------------------------------------------------

    def clear_all_atlases(self) -> None:
        """Removes all atlases, regions, and pack history.

        Resets the TextureAtlas to a clean state without affecting
        configuration parameters (max atlas size, padding).
        """
        with self._lock:
            self._atlases.clear()
            self._regions.clear()
            self._pack_history.clear()

    def reset(self) -> None:
        """Performs a complete reset of all atlas state.

        Clears all internal data and restores default configuration
        values for max atlas size and padding.
        """
        with self._lock:
            self._atlases.clear()
            self._regions.clear()
            self._pack_history.clear()
            self._max_atlas_size = self._DEFAULT_MAX_ATLAS_SIZE
            self._padding = self._DEFAULT_PADDING

    def __repr__(self) -> str:
        with self._lock:
            return (
                f"TextureAtlas(atlases={len(self._atlases)}, "
                f"regions={len(self._regions)}, "
                f"packs={len(self._pack_history)}, "
                f"max={self._max_atlas_size[0]}x{self._max_atlas_size[1]})"
            )


def get_texture_atlas() -> TextureAtlas:
    """Module-level accessor for the TextureAtlas singleton.

    Convenience function that returns the singleton instance without
    needing to reference TextureAtlas.get_instance() directly.

    Returns:
        The singleton TextureAtlas instance.
    """
    return TextureAtlas.get_instance()