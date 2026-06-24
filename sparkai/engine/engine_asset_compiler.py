"""
SparkLabs Engine - Asset Compiler Engine

A comprehensive asset compilation, optimization, and bundling pipeline for
the SparkLabs game engine. Handles importing various asset formats, compiling
them into optimized runtime formats, and creating asset bundles for
distribution. Supports incremental builds via a compilation cache, multi-stage
compilation pipelines, and multiple bundling strategies.

Architecture:
  AssetCompilerEngine (Singleton)
    |-- AssetImporter — imports assets from source files into the project
    |-- FormatCompiler — compiles assets from source format to runtime format
    |-- AssetOptimizer — applies optimization passes to compiled assets
    |-- BundleBuilder — creates asset bundles for distribution
    |-- CacheManager — manages compilation cache for incremental builds
    |-- AssetSource — metadata for a source asset file
    |-- CompileConfig — configuration for a specific asset type compilation
    |-- CompileResult — result of a single compilation operation
    |-- AssetBundle — packaged collection of compiled assets
    |-- CompilePipeline — ordered multi-stage compilation pipeline
    |-- CompilerStats — aggregate compilation statistics

Usage:
    engine = get_asset_compiler()
    source = engine.import_asset("assets/textures/player.png")
    engine.configure_compilation(AssetType.TEXTURE, config)
    result = engine.compile_asset(source.source_id)
    bundle = engine.build_bundle("level_1", [source.source_id])
"""

from __future__ import annotations

import hashlib
import io
import json
import math
import random
import threading
import time as _time_module
import uuid
from collections import OrderedDict, deque
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

_time = _time_module.time


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

DEFAULT_CACHE_MAX_ENTRIES: int = 2048
DEFAULT_CACHE_MAX_SIZE_MB: int = 512
DEFAULT_MAX_CONCURRENT_COMPILES: int = 4
MAX_BUNDLE_SIZE_BYTES: int = 512 * 1024 * 1024  # 512 MB
DEFAULT_PIPELINE_TIMEOUT: float = 300.0  # 5 minutes
SIMULATED_COMPILE_DELAY_MS: float = 2.0

# Typical compression ratios by format category (synthetic values)
_FORMAT_COMPRESSION_RATIOS: Dict[str, float] = {
    "png": 0.85, "jpeg": 0.92, "webp": 0.78, "svg": 0.65,
    "mp3": 0.88, "wav": 0.45, "ogg": 0.82,
    "ttf": 0.70, "otf": 0.72,
    "json": 0.55, "yaml": 0.50, "xml": 0.48,
    "glsl": 0.30, "hlsl": 0.30,
    "bin": 0.95,
}

# Format-to-AssetType mapping
_FORMAT_TYPE_MAP: Dict[str, AssetType] = {}
# AssetType-to-supported-formats mapping
_TYPE_FORMAT_MAP: Dict[AssetType, List[AssetFormat]] = {}

# Default platform targets
_PLATFORM_TARGETS: List[str] = [
    "windows", "macos", "linux", "android", "ios", "webgl", "ps5", "xbox_series",
]


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class AssetType(str, Enum):
    """Categories of assets supported by the compilation pipeline.

    Each type has a distinct compilation strategy and may produce
    different runtime output formats depending on the target platform.
    """

    TEXTURE = "texture"
    SPRITE = "sprite"
    SPRITE_SHEET = "sprite_sheet"
    AUDIO = "audio"
    FONT = "font"
    TILEMAP = "tilemap"
    ANIMATION = "animation"
    SHADER = "shader"
    MATERIAL = "material"
    PREFAB = "prefab"
    SCENE = "scene"
    SCRIPT = "script"
    CONFIG = "config"
    DATA = "data"
    UNKNOWN = "unknown"


class AssetFormat(str, Enum):
    """Source and target file formats recognized by the compiler.

    Enumerates the formats that can be imported, compiled to/from,
    and used as intermediate or final output formats.
    """

    PNG = "png"
    JPEG = "jpeg"
    WEBP = "webp"
    SVG = "svg"
    MP3 = "mp3"
    WAV = "wav"
    OGG = "ogg"
    TTF = "ttf"
    OTF = "otf"
    JSON = "json"
    YAML = "yaml"
    XML = "xml"
    GLSL = "glsl"
    HLSL = "hlsl"
    BIN = "bin"
    CUSTOM = "custom"


class CompressionLevel(str, Enum):
    """Compression aggressiveness levels for the compilation pipeline.

    NONE: No compression applied (passthrough).
    FAST: Light compression optimized for speed.
    BALANCED: Good trade-off between size and time.
    MAXIMUM: Best compression ratio, slower.
    LOSSLESS: Lossless compression where applicable.
    """

    NONE = "none"
    FAST = "fast"
    BALANCED = "balanced"
    MAXIMUM = "maximum"
    LOSSLESS = "lossless"


class CompileStatus(str, Enum):
    """Lifecycle states for a compilation operation.

    PENDING: Source imported but not yet queued for compilation.
    QUEUED: In the compilation queue awaiting a worker slot.
    COMPILING: Actively being compiled by a worker.
    COMPLETED: Compilation finished successfully.
    FAILED: Compilation encountered an error.
    CACHED: Result was retrieved from the compilation cache.
    SKIPPED: Compilation was skipped (e.g. no changes detected).
    """

    PENDING = "pending"
    QUEUED = "queued"
    COMPILING = "compiling"
    COMPLETED = "completed"
    FAILED = "failed"
    CACHED = "cached"
    SKIPPED = "skipped"


class BundleStrategy(str, Enum):
    """Strategies for packaging compiled assets into bundles.

    SINGLE_FILE: All assets in one monolithic bundle.
    SPLIT_BY_TYPE: Separate bundles per asset type.
    SPLIT_BY_SCENE: Separate bundles per scene reference.
    LAZY_LOAD: Assets split into initial-load and deferred bundles.
    STREAMING: Assets streamed progressively at runtime.
    CUSTOM: User-defined splitting logic.
    """

    SINGLE_FILE = "single_file"
    SPLIT_BY_TYPE = "split_by_type"
    SPLIT_BY_SCENE = "split_by_scene"
    LAZY_LOAD = "lazy_load"
    STREAMING = "streaming"
    CUSTOM = "custom"


# ---------------------------------------------------------------------------
# Format Mapping Initialization
# ---------------------------------------------------------------------------

def _init_format_maps() -> None:
    """Populate the format-to-type and type-to-format lookup tables."""
    _FORMAT_TYPE_MAP.update({
        "png": AssetType.TEXTURE, "jpeg": AssetType.TEXTURE,
        "webp": AssetType.TEXTURE, "svg": AssetType.TEXTURE,
        "mp3": AssetType.AUDIO, "wav": AssetType.AUDIO, "ogg": AssetType.AUDIO,
        "ttf": AssetType.FONT, "otf": AssetType.FONT,
        "json": AssetType.DATA, "yaml": AssetType.CONFIG, "xml": AssetType.DATA,
        "glsl": AssetType.SHADER, "hlsl": AssetType.SHADER,
        "bin": AssetType.DATA,
    })

    _TYPE_FORMAT_MAP.update({
        AssetType.TEXTURE: [AssetFormat.PNG, AssetFormat.JPEG, AssetFormat.WEBP, AssetFormat.SVG],
        AssetType.SPRITE: [AssetFormat.PNG, AssetFormat.JPEG, AssetFormat.WEBP],
        AssetType.SPRITE_SHEET: [AssetFormat.PNG, AssetFormat.WEBP],
        AssetType.AUDIO: [AssetFormat.MP3, AssetFormat.WAV, AssetFormat.OGG],
        AssetType.FONT: [AssetFormat.TTF, AssetFormat.OTF],
        AssetType.TILEMAP: [AssetFormat.JSON, AssetFormat.XML, AssetFormat.BIN],
        AssetType.ANIMATION: [AssetFormat.JSON, AssetFormat.BIN],
        AssetType.SHADER: [AssetFormat.GLSL, AssetFormat.HLSL],
        AssetType.MATERIAL: [AssetFormat.JSON, AssetFormat.YAML],
        AssetType.PREFAB: [AssetFormat.JSON, AssetFormat.BIN],
        AssetType.SCENE: [AssetFormat.JSON, AssetFormat.BIN],
        AssetType.SCRIPT: [AssetFormat.JSON, AssetFormat.CUSTOM],
        AssetType.CONFIG: [AssetFormat.JSON, AssetFormat.YAML, AssetFormat.XML],
        AssetType.DATA: [AssetFormat.JSON, AssetFormat.XML, AssetFormat.BIN, AssetFormat.CUSTOM],
        AssetType.UNKNOWN: [AssetFormat.CUSTOM],
    })


_init_format_maps()


# ---------------------------------------------------------------------------
# Data Classes
# ---------------------------------------------------------------------------


@dataclass
class AssetSource:
    """Metadata for a source asset file imported into the project.

    Tracks the file's identity, type, format, size, modification time,
    integrity checksum, and arbitrary key/value metadata.

    Attributes:
        source_id: Unique identifier for this source asset.
        path: File-system path to the source file.
        asset_type: Category of the asset.
        format: File format of the source.
        file_size: Size of the source file in bytes.
        last_modified: Unix timestamp of last file modification.
        checksum: SHA-256 integrity hash of the source file content.
        metadata: Arbitrary key/value metadata.
    """

    source_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    path: str = ""
    asset_type: AssetType = AssetType.UNKNOWN
    format: AssetFormat = AssetFormat.CUSTOM
    file_size: int = 0
    last_modified: float = field(default_factory=_time)
    checksum: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "source_id": self.source_id,
            "path": self.path,
            "asset_type": self.asset_type.value,
            "format": self.format.value,
            "file_size": self.file_size,
            "last_modified": self.last_modified,
            "checksum": self.checksum,
            "metadata": dict(self.metadata),
        }


@dataclass
class CompileConfig:
    """Configuration for compiling assets of a specific type.

    Defines how assets of a given type should be compiled: target format,
    compression level, resolution scaling, mipmap generation, platform
    target, and optimization flags.

    Attributes:
        config_id: Unique identifier for this configuration.
        asset_type: The asset type this configuration applies to.
        target_format: Desired output format after compilation.
        compression_level: Compression aggressiveness.
        resolution_scale: Scale factor for texture resolution (1.0 = original).
        mipmap_levels: Number of mipmap levels to generate (0 = none).
        platform_target: Target platform for platform-specific optimization.
        optimization_flags: Set of optimization flags to apply.
    """

    config_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    asset_type: AssetType = AssetType.UNKNOWN
    target_format: AssetFormat = AssetFormat.BIN
    compression_level: CompressionLevel = CompressionLevel.BALANCED
    resolution_scale: float = 1.0
    mipmap_levels: int = 0
    platform_target: str = "windows"
    optimization_flags: Set[str] = field(default_factory=set)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "config_id": self.config_id,
            "asset_type": self.asset_type.value,
            "target_format": self.target_format.value,
            "compression_level": self.compression_level.value,
            "resolution_scale": self.resolution_scale,
            "mipmap_levels": self.mipmap_levels,
            "platform_target": self.platform_target,
            "optimization_flags": sorted(self.optimization_flags),
        }


@dataclass
class CompileResult:
    """Result of a single asset compilation operation.

    Records the compiled size, original size, compression ratio, timing,
    any warnings or errors, the output path, and a cache key for
    incremental build support.

    Attributes:
        result_id: Unique identifier for this compilation result.
        source: The source asset that was compiled.
        compiled_size: Size of the compiled output in bytes.
        original_size: Size of the original source in bytes.
        compression_ratio: Ratio of compiled_size to original_size.
        compile_time_ms: Time spent compiling in milliseconds.
        warnings: List of warning messages generated during compilation.
        errors: List of error messages (empty if successful).
        output_path: File-system path to the compiled output.
        cache_key: Key used for caching this compilation result.
        status: Final status of the compilation.
    """

    result_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    source: Optional[AssetSource] = None
    compiled_size: int = 0
    original_size: int = 0
    compression_ratio: float = 1.0
    compile_time_ms: float = 0.0
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    output_path: str = ""
    cache_key: str = ""
    status: CompileStatus = CompileStatus.PENDING

    @property
    def is_success(self) -> bool:
        return self.status == CompileStatus.COMPLETED and len(self.errors) == 0

    @property
    def bytes_saved(self) -> int:
        return max(0, self.original_size - self.compiled_size)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "result_id": self.result_id,
            "source_id": self.source.source_id if self.source else "",
            "compiled_size": self.compiled_size,
            "original_size": self.original_size,
            "compression_ratio": round(self.compression_ratio, 4),
            "compile_time_ms": round(self.compile_time_ms, 2),
            "warnings": list(self.warnings),
            "errors": list(self.errors),
            "output_path": self.output_path,
            "cache_key": self.cache_key,
            "status": self.status.value,
            "is_success": self.is_success,
            "bytes_saved": self.bytes_saved,
        }


@dataclass
class AssetBundle:
    """Packaged collection of compiled assets for distribution.

    Bundles are the primary distribution unit for game content.
    They track included assets, total size, strategy, dependencies,
    load priority, compression, and versioning information.

    Attributes:
        bundle_id: Unique identifier for this bundle.
        name: Human-readable bundle name.
        assets: List of source asset IDs included in the bundle.
        total_size: Total uncompressed size of all assets in bytes.
        strategy: The bundling strategy used to create this bundle.
        dependencies: List of other bundle IDs this bundle depends on.
        load_priority: Priority for loading this bundle at runtime.
        compression_used: Compression level applied to the bundle.
        created_at: Unix timestamp of bundle creation.
        version: Version string for the bundle.
    """

    bundle_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = ""
    assets: List[str] = field(default_factory=list)
    total_size: int = 0
    strategy: BundleStrategy = BundleStrategy.SPLIT_BY_TYPE
    dependencies: List[str] = field(default_factory=list)
    load_priority: int = 0
    compression_used: CompressionLevel = CompressionLevel.BALANCED
    created_at: float = field(default_factory=_time)
    version: str = "1.0.0"

    @property
    def asset_count(self) -> int:
        return len(self.assets)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "bundle_id": self.bundle_id,
            "name": self.name,
            "asset_count": self.asset_count,
            "assets": list(self.assets),
            "total_size": self.total_size,
            "strategy": self.strategy.value,
            "dependencies": list(self.dependencies),
            "load_priority": self.load_priority,
            "compression_used": self.compression_used.value,
            "created_at": self.created_at,
            "version": self.version,
        }


@dataclass
class CompilePipeline:
    """Ordered multi-stage compilation pipeline.

    A pipeline defines a sequence of compilation stages (each with its
    own configuration) that are applied in order. Tracks overall progress,
    status, timing, and estimated completion.

    Attributes:
        pipeline_id: Unique identifier for this pipeline.
        stages: Ordered list of stage names.
        configs: List of CompileConfig instances, one per stage.
        progress: Overall progress as a float from 0.0 to 1.0.
        status: Current pipeline status.
        start_time: Unix timestamp when the pipeline started.
        estimated_time: Estimated total time in seconds.
        name: Human-readable pipeline name.
    """

    pipeline_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    stages: List[str] = field(default_factory=list)
    configs: List[CompileConfig] = field(default_factory=list)
    progress: float = 0.0
    status: CompileStatus = CompileStatus.PENDING
    start_time: float = 0.0
    estimated_time: float = 0.0
    name: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "pipeline_id": self.pipeline_id,
            "name": self.name,
            "stages": list(self.stages),
            "config_count": len(self.configs),
            "progress": round(self.progress, 4),
            "status": self.status.value,
            "start_time": self.start_time,
            "estimated_time": round(self.estimated_time, 2),
        }


@dataclass
class CompilerStats:
    """Aggregate compilation statistics for the compiler engine.

    Tracks total compiled and failed counts, cache performance,
    total bytes saved, and average compile time across all operations.

    Attributes:
        stats_id: Unique identifier for this stats snapshot.
        total_compiled: Total number of successful compilations.
        total_failed: Total number of failed compilations.
        cache_hits: Number of cache hits during compilation.
        cache_misses: Number of cache misses during compilation.
        total_bytes_saved: Total bytes saved through compression.
        avg_compile_time: Average compilation time in milliseconds.
        pipeline_count: Number of pipelines created.
        bundle_count: Number of bundles created.
    """

    stats_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    total_compiled: int = 0
    total_failed: int = 0
    cache_hits: int = 0
    cache_misses: int = 0
    total_bytes_saved: int = 0
    avg_compile_time: float = 0.0
    pipeline_count: int = 0
    bundle_count: int = 0

    @property
    def cache_hit_ratio(self) -> float:
        total = self.cache_hits + self.cache_misses
        if total == 0:
            return 0.0
        return self.cache_hits / total

    @property
    def success_rate(self) -> float:
        total = self.total_compiled + self.total_failed
        if total == 0:
            return 1.0
        return self.total_compiled / total

    def to_dict(self) -> Dict[str, Any]:
        return {
            "stats_id": self.stats_id,
            "total_compiled": self.total_compiled,
            "total_failed": self.total_failed,
            "cache_hits": self.cache_hits,
            "cache_misses": self.cache_misses,
            "cache_hit_ratio": round(self.cache_hit_ratio, 4),
            "success_rate": round(self.success_rate, 4),
            "total_bytes_saved": self.total_bytes_saved,
            "total_bytes_saved_mb": round(self.total_bytes_saved / (1024 * 1024), 2),
            "avg_compile_time_ms": round(self.avg_compile_time, 2),
            "pipeline_count": self.pipeline_count,
            "bundle_count": self.bundle_count,
        }


# ---------------------------------------------------------------------------
# Subsystem Classes
# ---------------------------------------------------------------------------


class AssetImporter:
    """Imports assets from source files into the project.

    Resolves file paths, detects asset types from file extensions,
    computes integrity checksums, and creates AssetSource metadata
    entries for each imported file.
    """

    def __init__(self) -> None:
        self._imported_count: int = 0
        self._failed_imports: int = 0

    def import_asset(
        self, source_path: str, asset_type: Optional[AssetType] = None
    ) -> AssetSource:
        """Import a single asset from a file path.

        Detects the asset type from the file extension if not explicitly
        provided. Computes a simulated checksum and file size.

        Args:
            source_path: File-system path to the source asset.
            asset_type: Explicit asset type (auto-detected if None).

        Returns:
            An AssetSource instance representing the imported asset.
        """
        path = Path(source_path)
        suffix = path.suffix.lstrip(".").lower()

        # Auto-detect format
        try:
            detected_format = AssetFormat(suffix)
        except ValueError:
            detected_format = AssetFormat.CUSTOM

        # Auto-detect asset type from format
        if asset_type is None:
            asset_type = _FORMAT_TYPE_MAP.get(suffix, AssetType.UNKNOWN)

        # Simulated file size (varies by type for realism)
        base_size = random.randint(1024, 10 * 1024 * 1024)
        type_multipliers: Dict[AssetType, float] = {
            AssetType.TEXTURE: 8.0,
            AssetType.AUDIO: 12.0,
            AssetType.FONT: 2.0,
            AssetType.SHADER: 0.01,
            AssetType.SCENE: 0.5,
            AssetType.CONFIG: 0.01,
            AssetType.DATA: 1.0,
        }
        file_size = int(base_size * type_multipliers.get(asset_type, 1.0))

        # Simulated checksum
        raw = f"{source_path}:{file_size}:{_time()}"
        checksum = hashlib.sha256(raw.encode()).hexdigest()

        source = AssetSource(
            path=source_path,
            asset_type=asset_type,
            format=detected_format,
            file_size=file_size,
            checksum=checksum,
            metadata={
                "extension": suffix,
                "imported_at": _time(),
                "original_path": source_path,
            },
        )

        self._imported_count += 1
        return source

    def import_batch(
        self, source_paths: List[str], asset_types: Optional[List[Optional[AssetType]]] = None
    ) -> List[AssetSource]:
        """Import multiple assets in a batch.

        Args:
            source_paths: List of file paths to import.
            asset_types: Optional list of explicit asset types per path.

        Returns:
            List of AssetSource instances.
        """
        results: List[AssetSource] = []
        types = asset_types if asset_types else [None] * len(source_paths)
        for path, atype in zip(source_paths, types):
            try:
                source = self.import_asset(path, atype)
                results.append(source)
            except Exception:
                self._failed_imports += 1
        return results

    @property
    def stats(self) -> Dict[str, int]:
        return {
            "imported_count": self._imported_count,
            "failed_imports": self._failed_imports,
        }


class FormatCompiler:
    """Compiles assets from source format to optimized runtime format.

    Simulates format conversion with realistic compression ratios based
    on the source and target formats. Supports platform-specific
    compilation and multi-pass optimization.
    """

    def __init__(self) -> None:
        self._compile_count: int = 0

    def compile(
        self,
        source: AssetSource,
        config: CompileConfig,
        output_dir: str = "",
    ) -> CompileResult:
        """Compile a single asset source to the target format.

        Simulates the compilation process with format-specific timing
        and compression ratio calculations.

        Args:
            source: The source asset to compile.
            config: Compilation configuration.
            output_dir: Directory for the compiled output.

        Returns:
            A CompileResult with compilation details.
        """
        start_time = _time()

        # Determine compression ratio based on format conversion
        source_ext = source.format.value
        target_ext = config.target_format.value
        source_ratio = _FORMAT_COMPRESSION_RATIOS.get(source_ext, 0.90)
        target_ratio = _FORMAT_COMPRESSION_RATIOS.get(target_ext, 0.85)

        # Base ratio blended between source and target characteristics
        base_ratio = (source_ratio * 0.3 + target_ratio * 0.7)

        # Adjust by compression level
        level_modifiers: Dict[CompressionLevel, float] = {
            CompressionLevel.NONE: 1.0,
            CompressionLevel.FAST: 0.88,
            CompressionLevel.BALANCED: 0.75,
            CompressionLevel.MAXIMUM: 0.60,
            CompressionLevel.LOSSLESS: 0.95,
        }
        level_mod = level_modifiers.get(config.compression_level, 0.80)

        # Resolution scale affects texture/image assets
        resolution_mod = 1.0
        if source.asset_type in (AssetType.TEXTURE, AssetType.SPRITE, AssetType.SPRITE_SHEET):
            resolution_mod = config.resolution_scale ** 2

        # Final compression ratio with some randomness
        random_factor = 1.0 + random.uniform(-0.08, 0.08)
        compression_ratio = base_ratio * level_mod * resolution_mod * random_factor
        compression_ratio = max(0.01, min(1.0, compression_ratio))

        compiled_size = max(1, int(source.file_size * compression_ratio))

        # Simulated compile time based on size
        size_factor = math.log2(max(source.file_size, 1024)) / 20.0
        level_time = {
            CompressionLevel.NONE: 0.3,
            CompressionLevel.FAST: 0.7,
            CompressionLevel.BALANCED: 1.0,
            CompressionLevel.MAXIMUM: 2.5,
            CompressionLevel.LOSSLESS: 1.2,
        }.get(config.compression_level, 1.0)
        compile_time_ms = (source.file_size / (1024 * 1024)) * level_time * 50.0 * size_factor
        compile_time_ms = max(0.1, min(compile_time_ms, 60000.0))

        # Simulate occasional warnings
        warnings: List[str] = []
        if source.file_size > 50 * 1024 * 1024:
            warnings.append("Large asset may cause runtime performance impact")
        if config.resolution_scale < 0.5:
            warnings.append(f"Significant resolution reduction (scale={config.resolution_scale})")

        # Build cache key
        cache_key_data = f"{source.checksum}:{config.config_id}:{config.target_format.value}:{config.compression_level.value}"
        cache_key = hashlib.md5(cache_key_data.encode()).hexdigest()

        # Output path
        if output_dir:
            base_name = Path(source.path).stem
            output_path = str(Path(output_dir) / f"{base_name}.{config.target_format.value}")
        else:
            output_path = source.path + f".compiled.{config.target_format.value}"

        self._compile_count += 1

        return CompileResult(
            source=source,
            compiled_size=compiled_size,
            original_size=source.file_size,
            compression_ratio=compression_ratio,
            compile_time_ms=compile_time_ms,
            warnings=warnings,
            errors=[],
            output_path=output_path,
            cache_key=cache_key,
            status=CompileStatus.COMPLETED,
        )

    @property
    def compile_count(self) -> int:
        return self._compile_count


class AssetOptimizer:
    """Applies optimization passes to compiled assets.

    Supports multiple optimization techniques including dead code
    elimination, texture channel packing, audio frequency analysis,
    and mipmap generation.
    """

    _OPTIMIZATION_PASSES: Dict[str, str] = {
        "strip_metadata": "Remove non-essential metadata from the asset",
        "deduplicate": "Merge duplicate data blocks",
        "channel_packing": "Pack texture channels efficiently",
        "mipmap_generate": "Generate mipmap pyramid",
        "audio_normalize": "Normalize audio levels",
        "shader_minify": "Minify shader source code",
        "json_minify": "Remove whitespace from JSON data",
        "reorder_vertices": "Optimize vertex cache locality",
        "atlas_repack": "Repack atlas textures for tighter packing",
        "streamline_prefab": "Flatten unnecessary prefab nesting",
    }

    def __init__(self) -> None:
        self._optimization_count: int = 0
        self._total_bytes_saved_extra: int = 0

    def optimize(self, result: CompileResult, passes: Optional[List[str]] = None) -> CompileResult:
        """Apply optimization passes to a compiled asset.

        Each pass reduces the compiled size by a small additional
        percentage. The result is updated in-place with the new
        size and compression ratio.

        Args:
            result: The CompileResult to optimize.
            passes: List of optimization pass names to apply.
                    If None, applies default passes for the asset type.

        Returns:
            The updated CompileResult with optimization applied.
        """
        if result.status != CompileStatus.COMPLETED:
            return result

        if passes is None:
            passes = self._default_passes(result.source.asset_type if result.source else AssetType.UNKNOWN)

        current_size = result.compiled_size
        for pass_name in passes:
            if pass_name in self._OPTIMIZATION_PASSES:
                # Each pass reduces size by 1-5%
                reduction = 1.0 - random.uniform(0.01, 0.05)
                current_size = max(1, int(current_size * reduction))

        bytes_saved = result.compiled_size - current_size
        result.compiled_size = current_size
        if result.original_size > 0:
            result.compression_ratio = current_size / result.original_size

        self._optimization_count += 1
        self._total_bytes_saved_extra += bytes_saved

        return result

    def _default_passes(self, asset_type: AssetType) -> List[str]:
        """Return the default optimization passes for a given asset type."""
        mapping: Dict[AssetType, List[str]] = {
            AssetType.TEXTURE: ["strip_metadata", "channel_packing", "mipmap_generate"],
            AssetType.SPRITE: ["strip_metadata", "channel_packing"],
            AssetType.SPRITE_SHEET: ["strip_metadata", "atlas_repack", "channel_packing"],
            AssetType.AUDIO: ["strip_metadata", "audio_normalize"],
            AssetType.FONT: ["strip_metadata", "deduplicate"],
            AssetType.SHADER: ["shader_minify", "strip_metadata"],
            AssetType.PREFAB: ["streamline_prefab", "strip_metadata"],
            AssetType.CONFIG: ["json_minify", "strip_metadata"],
            AssetType.DATA: ["strip_metadata", "deduplicate"],
        }
        return mapping.get(asset_type, ["strip_metadata"])

    @property
    def optimization_count(self) -> int:
        return self._optimization_count

    @property
    def total_bytes_saved_extra(self) -> int:
        return self._total_bytes_saved_extra


class BundleBuilder:
    """Creates asset bundles for distribution.

    Groups compiled assets into bundles according to a specified
    strategy, tracks dependencies between bundles, and applies
    bundle-level compression.
    """

    def __init__(self) -> None:
        self._bundle_count: int = 0

    def build(
        self,
        name: str,
        results: List[CompileResult],
        strategy: BundleStrategy = BundleStrategy.SPLIT_BY_TYPE,
        load_priority: int = 0,
        version: str = "1.0.0",
    ) -> List[AssetBundle]:
        """Build bundles from a list of compilation results.

        Depending on the strategy, results are grouped into one or
        more bundles. Each bundle tracks its total size, dependencies,
        and compression level.

        Args:
            name: Base name for the bundle(s).
            results: List of CompileResult instances to bundle.
            strategy: The bundling strategy to use.
            load_priority: Priority for runtime loading.
            version: Version string for the bundle(s).

        Returns:
            List of AssetBundle instances created.
        """
        if strategy == BundleStrategy.SINGLE_FILE:
            return [self._build_single(name, results, load_priority, version)]
        elif strategy == BundleStrategy.SPLIT_BY_TYPE:
            return self._build_split_by_type(name, results, load_priority, version)
        elif strategy == BundleStrategy.SPLIT_BY_SCENE:
            return self._build_split_by_scene(name, results, load_priority, version)
        elif strategy == BundleStrategy.LAZY_LOAD:
            return self._build_lazy_load(name, results, load_priority, version)
        elif strategy == BundleStrategy.STREAMING:
            return self._build_streaming(name, results, load_priority, version)
        else:
            return [self._build_single(name, results, load_priority, version)]

    def _build_single(
        self, name: str, results: List[CompileResult], priority: int, version: str
    ) -> AssetBundle:
        """Create a single monolithic bundle."""
        asset_ids = [r.result_id for r in results]
        total_size = sum(r.compiled_size for r in results)
        bundle = AssetBundle(
            name=name,
            assets=asset_ids,
            total_size=total_size,
            strategy=BundleStrategy.SINGLE_FILE,
            load_priority=priority,
            compression_used=CompressionLevel.BALANCED,
            version=version,
        )
        self._bundle_count += 1
        return bundle

    def _build_split_by_type(
        self, name: str, results: List[CompileResult], priority: int, version: str
    ) -> List[AssetBundle]:
        """Create separate bundles per asset type."""
        grouped: Dict[AssetType, List[CompileResult]] = {}
        for r in results:
            atype = r.source.asset_type if r.source else AssetType.UNKNOWN
            grouped.setdefault(atype, []).append(r)

        bundles: List[AssetBundle] = []
        for atype, group in grouped.items():
            asset_ids = [r.result_id for r in group]
            total_size = sum(r.compiled_size for r in group)
            bundle = AssetBundle(
                name=f"{name}_{atype.value}",
                assets=asset_ids,
                total_size=total_size,
                strategy=BundleStrategy.SPLIT_BY_TYPE,
                load_priority=priority,
                version=version,
            )
            bundles.append(bundle)
            self._bundle_count += 1

        return bundles

    def _build_split_by_scene(
        self, name: str, results: List[CompileResult], priority: int, version: str
    ) -> List[AssetBundle]:
        """Create separate bundles per scene (simulated)."""
        # Simulated: group by scene tag in metadata
        scene_grouped: Dict[str, List[CompileResult]] = {}
        unassigned: List[CompileResult] = []
        for r in results:
            scene = r.source.metadata.get("scene", "") if r.source else ""
            if scene:
                scene_grouped.setdefault(scene, []).append(r)
            else:
                unassigned.append(r)

        bundles: List[AssetBundle] = []
        for scene, group in scene_grouped.items():
            asset_ids = [r.result_id for r in group]
            total_size = sum(r.compiled_size for r in group)
            bundle = AssetBundle(
                name=f"{name}_{scene}",
                assets=asset_ids,
                total_size=total_size,
                strategy=BundleStrategy.SPLIT_BY_SCENE,
                load_priority=priority,
                version=version,
            )
            bundles.append(bundle)
            self._bundle_count += 1

        if unassigned:
            asset_ids = [r.result_id for r in unassigned]
            total_size = sum(r.compiled_size for r in unassigned)
            bundle = AssetBundle(
                name=f"{name}_shared",
                assets=asset_ids,
                total_size=total_size,
                strategy=BundleStrategy.SPLIT_BY_SCENE,
                load_priority=priority,
                version=version,
            )
            bundles.append(bundle)
            self._bundle_count += 1

        return bundles

    def _build_lazy_load(
        self, name: str, results: List[CompileResult], priority: int, version: str
    ) -> List[AssetBundle]:
        """Create initial-load and deferred bundles."""
        # Split into initial (high priority) and deferred
        initial: List[CompileResult] = []
        deferred: List[CompileResult] = []
        for r in results:
            if r.source and r.source.asset_type in (
                AssetType.TEXTURE, AssetType.SHADER, AssetType.CONFIG
            ):
                initial.append(r)
            else:
                deferred.append(r)

        bundles: List[AssetBundle] = []
        for label, group, pri in [("initial", initial, 0), ("deferred", deferred, 10)]:
            if not group:
                continue
            asset_ids = [r.result_id for r in group]
            total_size = sum(r.compiled_size for r in group)
            bundle = AssetBundle(
                name=f"{name}_{label}",
                assets=asset_ids,
                total_size=total_size,
                strategy=BundleStrategy.LAZY_LOAD,
                load_priority=pri,
                version=version,
            )
            bundles.append(bundle)
            self._bundle_count += 1

        return bundles

    def _build_streaming(
        self, name: str, results: List[CompileResult], priority: int, version: str
    ) -> List[AssetBundle]:
        """Create streaming-ready bundles chunked by size."""
        # Split into chunks of ~MAX_BUNDLE_SIZE_BYTES
        chunks: List[List[CompileResult]] = []
        current_chunk: List[CompileResult] = []
        current_size = 0
        for r in sorted(results, key=lambda x: x.compiled_size, reverse=True):
            if current_size + r.compiled_size > MAX_BUNDLE_SIZE_BYTES and current_chunk:
                chunks.append(current_chunk)
                current_chunk = []
                current_size = 0
            current_chunk.append(r)
            current_size += r.compiled_size
        if current_chunk:
            chunks.append(current_chunk)

        bundles: List[AssetBundle] = []
        for i, chunk in enumerate(chunks):
            asset_ids = [r.result_id for r in chunk]
            total_size = sum(r.compiled_size for r in chunk)
            bundle = AssetBundle(
                name=f"{name}_stream_{i:03d}",
                assets=asset_ids,
                total_size=total_size,
                strategy=BundleStrategy.STREAMING,
                load_priority=priority + i,
                version=version,
            )
            bundles.append(bundle)
            self._bundle_count += 1

        return bundles

    @property
    def bundle_count(self) -> int:
        return self._bundle_count


class CacheManager:
    """Manages the compilation cache for incremental builds.

    Stores CompileResult entries keyed by a content-based cache key.
    Supports LRU eviction, hit/miss tracking, and cache invalidation.
    """

    def __init__(self, max_entries: int = DEFAULT_CACHE_MAX_ENTRIES) -> None:
        self._cache: OrderedDict[str, CompileResult] = OrderedDict()
        self._max_entries: int = max_entries
        self._hits: int = 0
        self._misses: int = 0
        self._lock = threading.RLock()

    def get(self, cache_key: str) -> Optional[CompileResult]:
        """Retrieve a cached compilation result.

        Moves the entry to the end (most-recently-used) on hit.

        Args:
            cache_key: The cache key to look up.

        Returns:
            The cached CompileResult if found, None otherwise.
        """
        with self._lock:
            if cache_key in self._cache:
                self._cache.move_to_end(cache_key)
                self._hits += 1
                return self._cache[cache_key]
            self._misses += 1
            return None

    def put(self, cache_key: str, result: CompileResult) -> None:
        """Store a compilation result in the cache.

        If the cache is full, evicts the least-recently-used entry.

        Args:
            cache_key: The cache key for the result.
            result: The CompileResult to cache.
        """
        with self._lock:
            if cache_key in self._cache:
                self._cache.move_to_end(cache_key)
            else:
                while len(self._cache) >= self._max_entries:
                    self._cache.popitem(last=False)
                self._cache[cache_key] = result

    def invalidate(self, cache_key: str) -> bool:
        """Remove a specific entry from the cache.

        Args:
            cache_key: The cache key to invalidate.

        Returns:
            True if the entry was removed, False if not found.
        """
        with self._lock:
            if cache_key in self._cache:
                del self._cache[cache_key]
                return True
            return False

    def clear(self) -> int:
        """Clear all entries from the cache.

        Returns:
            Number of entries removed.
        """
        with self._lock:
            count = len(self._cache)
            self._cache.clear()
            return count

    @property
    def hits(self) -> int:
        return self._hits

    @property
    def misses(self) -> int:
        return self._misses

    @property
    def entry_count(self) -> int:
        return len(self._cache)

    @property
    def size_mb(self) -> float:
        total = sum(r.compiled_size for r in self._cache.values())
        return total / (1024 * 1024)


# ---------------------------------------------------------------------------
# Asset Compiler Engine (Singleton)
# ---------------------------------------------------------------------------


class AssetCompilerEngine:
    """Orchestrates the full asset compilation pipeline.

    Coordinates importing, configuration, compilation, optimization,
    bundling, and caching. Manages compilation pipelines, tracks
    per-asset status, and provides aggregate statistics.

    Usage:
        engine = get_asset_compiler()
        source = engine.import_asset("assets/player.png")
        engine.configure_compilation(AssetType.TEXTURE, config)
        result = engine.compile_asset(source.source_id)
        bundle = engine.build_bundle("level_1", [source.source_id])
    """

    _instance: Optional["AssetCompilerEngine"] = None
    _lock: threading.RLock = threading.RLock()
    _initialized: bool = False

    def __new__(cls) -> "AssetCompilerEngine":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self) -> None:
        if self._initialized:
            return
        self._initialize()

    @classmethod
    def get_instance(cls) -> "AssetCompilerEngine":
        """Return the singleton AssetCompilerEngine instance."""
        return cls()

    def _initialize(self) -> None:
        """One-time initialization of all internal subsystems and data."""
        if self._initialized:
            return

        # Subsystems
        self._importer = AssetImporter()
        self._compiler = FormatCompiler()
        self._optimizer = AssetOptimizer()
        self._bundle_builder = BundleBuilder()
        self._cache = CacheManager()

        # Source registry
        self._sources: Dict[str, AssetSource] = {}

        # Compilation results
        self._results: Dict[str, CompileResult] = {}

        # Compilation configurations per asset type
        self._configs: Dict[AssetType, CompileConfig] = {}

        # Compilation status tracking
        self._statuses: Dict[str, CompileStatus] = {}

        # Bundles
        self._bundles: Dict[str, AssetBundle] = {}

        # Pipelines
        self._pipelines: Dict[str, CompilePipeline] = {}

        # Statistics
        self._stats = CompilerStats()

        # Compile queue
        self._compile_queue: deque = deque()

        # Output directory
        self._output_dir: str = "build/compiled"

        self._initialized = True

    # ------------------------------------------------------------------
    # Import
    # ------------------------------------------------------------------

    def import_asset(
        self, source_path: str, asset_type: Optional[AssetType] = None
    ) -> AssetSource:
        """Import an asset source file into the project.

        Detects the asset type from the file extension if not explicitly
        provided. Registers the source in the engine's registry.

        Args:
            source_path: File-system path to the source asset.
            asset_type: Explicit asset type (auto-detected if None).

        Returns:
            The imported AssetSource instance.
        """
        with self._lock:
            source = self._importer.import_asset(source_path, asset_type)
            self._sources[source.source_id] = source
            self._statuses[source.source_id] = CompileStatus.PENDING
            return source

    # ------------------------------------------------------------------
    # Configuration
    # ------------------------------------------------------------------

    def configure_compilation(self, asset_type: AssetType, config: CompileConfig) -> None:
        """Set the compilation configuration for a specific asset type.

        Overwrites any existing configuration for that type.

        Args:
            asset_type: The asset type to configure.
            config: The CompileConfig to apply.
        """
        with self._lock:
            config.asset_type = asset_type
            self._configs[asset_type] = config

    def get_config(self, asset_type: AssetType) -> Optional[CompileConfig]:
        """Retrieve the compilation configuration for a given asset type.

        Args:
            asset_type: The asset type to look up.

        Returns:
            The CompileConfig if set, None otherwise.
        """
        return self._configs.get(asset_type)

    # ------------------------------------------------------------------
    # Compilation
    # ------------------------------------------------------------------

    def compile_asset(self, source_id: str) -> CompileResult:
        """Compile a single asset from its source to the runtime format.

        Checks the cache first. If a cache hit occurs, returns the
        cached result with status CACHED. Otherwise, performs the
        compilation, applies optimization, and caches the result.

        Args:
            source_id: The source asset's unique identifier.

        Returns:
            A CompileResult with the compilation outcome.
        """
        source = self._sources.get(source_id)
        if source is None:
            result = CompileResult(
                status=CompileStatus.FAILED,
                errors=[f"Source not found: {source_id}"],
            )
            self._results[result.result_id] = result
            self._stats.total_failed += 1
            return result

        config = self._configs.get(source.asset_type)
        if config is None:
            config = CompileConfig(
                asset_type=source.asset_type,
                target_format=AssetFormat.BIN,
                compression_level=CompressionLevel.BALANCED,
            )

        with self._lock:
            self._statuses[source_id] = CompileStatus.COMPILING

        # Check cache
        cache_key_data = f"{source.checksum}:{config.config_id}:{config.target_format.value}:{config.compression_level.value}"
        cache_key = hashlib.md5(cache_key_data.encode()).hexdigest()

        cached = self._cache.get(cache_key)
        if cached is not None:
            with self._lock:
                self._statuses[source_id] = CompileStatus.CACHED
                self._stats.cache_hits += 1
            cached.status = CompileStatus.CACHED
            return cached

        self._stats.cache_misses += 1

        # Compile
        result = self._compiler.compile(source, config, self._output_dir)

        if result.is_success:
            # Optimize
            result = self._optimizer.optimize(result)
            self._cache.put(cache_key, result)
            with self._lock:
                self._statuses[source_id] = CompileStatus.COMPLETED
                self._stats.total_compiled += 1
                self._stats.total_bytes_saved += result.bytes_saved
                self._stats.avg_compile_time = (
                    (self._stats.avg_compile_time * (self._stats.total_compiled - 1) + result.compile_time_ms)
                    / max(self._stats.total_compiled, 1)
                )
        else:
            with self._lock:
                self._statuses[source_id] = CompileStatus.FAILED
                self._stats.total_failed += 1

        with self._lock:
            self._results[result.result_id] = result

        return result

    def compile_batch(self, source_ids: List[str]) -> List[CompileResult]:
        """Compile multiple assets in a batch.

        Processes each source sequentially, collecting results.

        Args:
            source_ids: List of source asset IDs to compile.

        Returns:
            List of CompileResult instances, one per source.
        """
        results: List[CompileResult] = []
        total = len(source_ids)
        for i, sid in enumerate(source_ids):
            with self._lock:
                self._statuses[sid] = CompileStatus.QUEUED
            result = self.compile_asset(sid)
            results.append(result)
        return results

    # ------------------------------------------------------------------
    # Optimization
    # ------------------------------------------------------------------

    def optimize_asset(self, result_id: str) -> CompileResult:
        """Apply additional optimization passes to an already compiled asset.

        Args:
            result_id: The CompileResult's unique identifier.

        Returns:
            The updated CompileResult with optimization applied.
        """
        result = self._results.get(result_id)
        if result is None:
            new_result = CompileResult(
                status=CompileStatus.FAILED,
                errors=[f"Result not found: {result_id}"],
            )
            return new_result

        if result.status != CompileStatus.COMPLETED:
            return result

        optimized = self._optimizer.optimize(result)
        with self._lock:
            self._results[result_id] = optimized
        return optimized

    # ------------------------------------------------------------------
    # Bundling
    # ------------------------------------------------------------------

    def build_bundle(
        self,
        name: str,
        asset_ids: List[str],
        strategy: BundleStrategy = BundleStrategy.SPLIT_BY_TYPE,
    ) -> AssetBundle:
        """Build an asset bundle from compiled results.

        Collects the CompileResult for each source_id, then uses the
        bundle builder to create bundles according to the strategy.

        Args:
            name: Base name for the bundle(s).
            asset_ids: List of source asset IDs to include.
            strategy: The bundling strategy to use.

        Returns:
            The primary AssetBundle created. If the strategy produces
            multiple bundles, returns the first one.
        """
        results: List[CompileResult] = []
        for aid in asset_ids:
            # Find the result for this source
            found = None
            for rid, result in self._results.items():
                if result.source and result.source.source_id == aid:
                    found = result
                    break
            if found is None:
                # Compile it first
                found = self.compile_asset(aid)
            results.append(found)

        bundles = self._bundle_builder.build(name, results, strategy)

        with self._lock:
            for bundle in bundles:
                self._bundles[bundle.bundle_id] = bundle
                self._stats.bundle_count += 1

        return bundles[0] if bundles else AssetBundle(name=name)

    def get_bundle(self, bundle_id: str) -> Optional[AssetBundle]:
        """Retrieve a bundle by its unique identifier.

        Args:
            bundle_id: The bundle's unique identifier.

        Returns:
            The AssetBundle if found, None otherwise.
        """
        return self._bundles.get(bundle_id)

    def list_bundles(self) -> List[AssetBundle]:
        """List all created asset bundles.

        Returns:
            List of all AssetBundle instances.
        """
        return list(self._bundles.values())

    # ------------------------------------------------------------------
    # Status & Statistics
    # ------------------------------------------------------------------

    def get_compile_status(self, source_id: str) -> CompileStatus:
        """Get the current compilation status for a source asset.

        Args:
            source_id: The source asset's unique identifier.

        Returns:
            The current CompileStatus. Returns FAILED if the source
            is not found.
        """
        return self._statuses.get(source_id, CompileStatus.FAILED)

    def get_compiler_stats(self) -> CompilerStats:
        """Get a snapshot of the compiler's aggregate statistics.

        Returns:
            A CompilerStats instance with current counts.
        """
        with self._lock:
            return CompilerStats(
                stats_id=uuid.uuid4().hex,
                total_compiled=self._stats.total_compiled,
                total_failed=self._stats.total_failed,
                cache_hits=self._stats.cache_hits,
                cache_misses=self._stats.cache_misses,
                total_bytes_saved=self._stats.total_bytes_saved,
                avg_compile_time=self._stats.avg_compile_time,
                pipeline_count=self._stats.pipeline_count,
                bundle_count=self._stats.bundle_count,
            )

    def get_result(self, result_id: str) -> Optional[CompileResult]:
        """Retrieve a compilation result by its unique identifier.

        Args:
            result_id: The result's unique identifier.

        Returns:
            The CompileResult if found, None otherwise.
        """
        return self._results.get(result_id)

    def get_source(self, source_id: str) -> Optional[AssetSource]:
        """Retrieve a source asset by its unique identifier.

        Args:
            source_id: The source's unique identifier.

        Returns:
            The AssetSource if found, None otherwise.
        """
        return self._sources.get(source_id)

    def list_sources(
        self, asset_type: Optional[AssetType] = None
    ) -> List[AssetSource]:
        """List all imported source assets, optionally filtered by type.

        Args:
            asset_type: Filter by asset type (None = all).

        Returns:
            List of matching AssetSource instances.
        """
        if asset_type is None:
            return list(self._sources.values())
        return [s for s in self._sources.values() if s.asset_type == asset_type]

    # ------------------------------------------------------------------
    # Cache
    # ------------------------------------------------------------------

    def clear_cache(self) -> None:
        """Clear the entire compilation cache.

        Future compilations will need to recompile from source.
        """
        count = self._cache.clear()
        with self._lock:
            self._stats.cache_hits = 0
            self._stats.cache_misses = 0

    def get_cache_stats(self) -> Dict[str, Any]:
        """Get statistics about the compilation cache.

        Returns:
            Dict with entry count, hit/miss counts, hit ratio, and size.
        """
        return {
            "entry_count": self._cache.entry_count,
            "hits": self._cache.hits,
            "misses": self._cache.misses,
            "hit_ratio": round(
                self._cache.hits / max(self._cache.hits + self._cache.misses, 1), 4
            ),
            "estimated_size_mb": round(self._cache.size_mb, 2),
            "max_entries": DEFAULT_CACHE_MAX_ENTRIES,
        }

    # ------------------------------------------------------------------
    # Supported Formats
    # ------------------------------------------------------------------

    def get_supported_formats(self) -> Dict[str, Any]:
        """Get the mapping of supported asset types to their formats.

        Returns:
            Dict with asset types as keys and lists of supported
            formats and compression ratios as values.
        """
        result: Dict[str, Any] = {}
        for atype, formats in _TYPE_FORMAT_MAP.items():
            result[atype.value] = {
                "formats": [f.value for f in formats],
                "can_import": True,
                "can_compile": True,
                "default_target": formats[0].value if formats else "bin",
            }
        return result

    # ------------------------------------------------------------------
    # Pipeline
    # ------------------------------------------------------------------

    def create_pipeline(
        self, name: str, configs: List[CompileConfig]
    ) -> CompilePipeline:
        """Create a multi-stage compilation pipeline.

        Each config in the list represents a stage in the pipeline.
        Stages are applied in order.

        Args:
            name: Human-readable pipeline name.
            configs: Ordered list of CompileConfig instances.

        Returns:
            The created CompilePipeline instance.
        """
        stages = [f"stage_{i}_{c.asset_type.value}" for i, c in enumerate(configs)]
        estimated = sum(
            SIMULATED_COMPILE_DELAY_MS * 50  # rough estimate per stage
            for _ in configs
        )

        pipeline = CompilePipeline(
            name=name,
            stages=stages,
            configs=configs,
            estimated_time=estimated,
        )

        with self._lock:
            self._pipelines[pipeline.pipeline_id] = pipeline
            self._stats.pipeline_count += 1

        return pipeline

    def run_pipeline(self, pipeline_id: str) -> List[CompileResult]:
        """Execute a compilation pipeline on all matching sources.

        Each stage's configuration is applied to sources matching
        its asset type. Sources are compiled through each stage
        sequentially.

        Args:
            pipeline_id: The pipeline's unique identifier.

        Returns:
            List of CompileResult instances from all stages.
        """
        pipeline = self._pipelines.get(pipeline_id)
        if pipeline is None:
            return []

        with self._lock:
            pipeline.status = CompileStatus.COMPILING
            pipeline.start_time = _time()

        all_results: List[CompileResult] = []
        total_stages = len(pipeline.configs)

        for stage_idx, config in enumerate(pipeline.configs):
            # Find sources matching this stage's asset type
            matching = self.list_sources(config.asset_type)
            if not matching:
                pipeline.progress = (stage_idx + 1) / max(total_stages, 1)
                continue

            # Configure and compile
            self.configure_compilation(config.asset_type, config)
            source_ids = [s.source_id for s in matching]
            stage_results = self.compile_batch(source_ids)
            all_results.extend(stage_results)

            pipeline.progress = (stage_idx + 1) / max(total_stages, 1)

        with self._lock:
            pipeline.status = CompileStatus.COMPLETED

        return all_results

    def get_pipeline(self, pipeline_id: str) -> Optional[CompilePipeline]:
        """Retrieve a pipeline by its unique identifier.

        Args:
            pipeline_id: The pipeline's unique identifier.

        Returns:
            The CompilePipeline if found, None otherwise.
        """
        return self._pipelines.get(pipeline_id)

    def list_pipelines(self) -> List[CompilePipeline]:
        """List all created compilation pipelines.

        Returns:
            List of all CompilePipeline instances.
        """
        return list(self._pipelines.values())

    # ------------------------------------------------------------------
    # Export / Status
    # ------------------------------------------------------------------

    def get_status(self) -> Dict[str, Any]:
        """Get a comprehensive status snapshot of the compiler engine.

        Returns:
            Dict with source count, result count, bundle count,
            pipeline count, cache stats, and compiler stats.
        """
        status_counts: Dict[str, int] = {}
        for s in self._statuses.values():
            key = s.value
            status_counts[key] = status_counts.get(key, 0) + 1

        return {
            "source_count": len(self._sources),
            "result_count": len(self._results),
            "bundle_count": len(self._bundles),
            "pipeline_count": len(self._pipelines),
            "status_breakdown": status_counts,
            "cache": self.get_cache_stats(),
            "compiler_stats": self.get_compiler_stats().to_dict(),
            "importer_stats": self._importer.stats,
            "output_dir": self._output_dir,
        }

    def set_output_dir(self, output_dir: str) -> None:
        """Set the output directory for compiled assets.

        Args:
            output_dir: The directory path for compiled output.
        """
        self._output_dir = output_dir

    def reset(self) -> None:
        """Reset the compiler engine to its initial empty state.

        Clears all sources, results, bundles, pipelines, cache,
        and statistics. The singleton instance remains valid for reuse.
        """
        with self._lock:
            self._sources.clear()
            self._results.clear()
            self._configs.clear()
            self._statuses.clear()
            self._bundles.clear()
            self._pipelines.clear()
            self._compile_queue.clear()
            self._cache.clear()
            self._stats = CompilerStats()
            self._importer = AssetImporter()
            self._compiler = FormatCompiler()
            self._optimizer = AssetOptimizer()
            self._bundle_builder = BundleBuilder()


# ---------------------------------------------------------------------------
# Module-level accessor
# ---------------------------------------------------------------------------


def get_asset_compiler() -> AssetCompilerEngine:
    """Return the global AssetCompilerEngine singleton instance."""
    return AssetCompilerEngine.get_instance()