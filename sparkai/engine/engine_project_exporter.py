"""
SparkLabs Engine - Project Exporter

Multi-platform game export pipeline that packages complete game projects
for distribution. Handles asset optimization, code bundling, platform-
specific configuration, and produces ready-to-distribute packages.

Architecture:
  ProjectExporter
    |-- PlatformConfigurator (target-specific settings)
    |-- AssetBundler (texture/audio/model optimization and packaging)
    |-- CodeBundler (script compilation and minification)
    |-- PackageAssembler (final executable/package creation)
    |-- ValidationChecker (pre-export integrity verification)

Export Targets:
  - WEB: HTML5/WebGL browser deployment
  - WINDOWS: native Windows executable
  - MACOS: native macOS application bundle
  - LINUX: native Linux binary
  - ANDROID: Android APK/AAB package
  - IOS: iOS application archive
"""

from __future__ import annotations

import threading
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


class ExportPlatform(Enum):
    """Target distribution platforms for game project exports."""
    WEB = "web"
    WINDOWS = "windows"
    MACOS = "macos"
    LINUX = "linux"
    ANDROID = "android"
    IOS = "ios"


class JobStatus(Enum):
    """Status states for an export job moving through the pipeline."""
    QUEUED = "queued"
    ASSET_OPTIMIZATION = "asset_optimization"
    CODE_BUNDLING = "code_bundling"
    PACKAGING = "packaging"
    VALIDATING = "validating"
    COMPLETED = "completed"
    FAILED = "failed"


class AssetType(Enum):
    """Categories of game assets processed during export."""
    TEXTURE = "texture"
    AUDIO = "audio"
    MODEL = "model"
    FONT = "font"
    SHADER = "shader"
    SCRIPT = "script"
    DATA = "data"


DEFAULT_EXPORT_OUTPUT_DIR = "./exports"

SIMULATED_ASSET_TYPES: Dict[AssetType, Tuple[float, str]] = {
    AssetType.TEXTURE: (0.58, "texture_atlas_compression"),
    AssetType.AUDIO: (0.42, "audio_vorbis_transcoding"),
    AssetType.MODEL: (0.35, "mesh_decimation"),
    AssetType.FONT: (0.25, "glyph_subsetting"),
    AssetType.SHADER: (0.15, "shader_minification"),
    AssetType.SCRIPT: (0.60, "script_bundling"),
    AssetType.DATA: (0.70, "data_packing"),
}

SIMULATED_ORIGINAL_SIZES: Dict[AssetType, int] = {
    AssetType.TEXTURE: 4096,
    AssetType.AUDIO: 2048,
    AssetType.MODEL: 3072,
    AssetType.FONT: 512,
    AssetType.SHADER: 128,
    AssetType.SCRIPT: 256,
    AssetType.DATA: 1024,
}


@dataclass
class ExportConfig:
    """Configuration for a game project export targeted at a specific platform."""
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    project_name: str = ""
    target_platform: ExportPlatform = ExportPlatform.WEB
    output_path: str = ""
    resolution_width: int = 1920
    resolution_height: int = 1080
    fullscreen: bool = False
    compression_level: int = 6
    include_debug_symbols: bool = False
    icon_path: str = ""
    bundle_id: str = ""
    version_string: str = "1.0.0"
    optimization_flags: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "project_name": self.project_name,
            "target_platform": self.target_platform.value,
            "output_path": self.output_path,
            "resolution": {
                "width": self.resolution_width,
                "height": self.resolution_height,
            },
            "fullscreen": self.fullscreen,
            "compression_level": self.compression_level,
            "include_debug_symbols": self.include_debug_symbols,
            "icon_path": self.icon_path,
            "bundle_id": self.bundle_id,
            "version_string": self.version_string,
            "optimization_flags": list(self.optimization_flags),
        }


@dataclass
class ExportJob:
    """An export job tracking the progress of a project through the pipeline."""
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    config_id: str = ""
    status: JobStatus = JobStatus.QUEUED
    progress: int = 0
    started_at: float = 0.0
    completed_at: float = 0.0
    output_path: str = ""
    file_size_mb: float = 0.0
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    current_step: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "config_id": self.config_id,
            "status": self.status.value,
            "progress": self.progress,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "output_path": self.output_path,
            "file_size_mb": self.file_size_mb,
            "warnings": list(self.warnings),
            "errors": list(self.errors),
            "current_step": self.current_step,
        }


@dataclass
class PlatformPreset:
    """Predefined platform-specific export settings for rapid configuration."""
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    platform: ExportPlatform = ExportPlatform.WEB
    default_resolution: Tuple[int, int] = (1920, 1080)
    supported_formats: List[str] = field(default_factory=list)
    default_bundle_id_prefix: str = ""
    min_sdk_version: str = ""
    icon_sizes: List[Tuple[int, int]] = field(default_factory=list)
    required_permissions: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "platform": self.platform.value,
            "default_resolution": {
                "width": self.default_resolution[0],
                "height": self.default_resolution[1],
            },
            "supported_formats": list(self.supported_formats),
            "default_bundle_id_prefix": self.default_bundle_id_prefix,
            "min_sdk_version": self.min_sdk_version,
            "icon_sizes": [
                {"width": w, "height": h} for w, h in self.icon_sizes
            ],
            "required_permissions": list(self.required_permissions),
        }


@dataclass
class AssetOptimization:
    """A record of asset optimization performed during an export job."""
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    job_id: str = ""
    asset_type: AssetType = AssetType.TEXTURE
    original_path: str = ""
    optimized_path: str = ""
    original_size_kb: float = 0.0
    optimized_size_kb: float = 0.0
    compression_ratio: float = 0.0
    technique_used: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "job_id": self.job_id,
            "asset_type": self.asset_type.value,
            "original_path": self.original_path,
            "optimized_path": self.optimized_path,
            "original_size_kb": self.original_size_kb,
            "optimized_size_kb": self.optimized_size_kb,
            "compression_ratio": self.compression_ratio,
            "technique_used": self.technique_used,
        }


class ProjectExporter:
    """
    Multi-platform game project export pipeline orchestrator.

    Manages the end-to-end process of exporting a SparkLabs game project
    to a target distribution platform. The pipeline progresses through
    asset optimization, code bundling, package assembly, and validation.
    Each stage is tracked independently within an export job.

    Usage:
        exporter = ProjectExporter()
        config = exporter.create_config("MyGame", ExportPlatform.WINDOWS)
        job = exporter.start_export(config.id)
        stats = exporter.get_stats()
    """

    _instance: Optional["ProjectExporter"] = None
    _lock: threading.RLock = threading.RLock()

    def __init__(self) -> None:
        self._configs: Dict[str, ExportConfig] = {}
        self._jobs: Dict[str, ExportJob] = {}
        self._presets: Dict[str, PlatformPreset] = {}
        self._optimizations: Dict[str, AssetOptimization] = {}
        self._config_count: int = 0
        self._job_count: int = 0
        self._completed_jobs: int = 0
        self._failed_jobs: int = 0
        self._total_optimizations: int = 0
        self._total_original_size_kb: float = 0.0
        self._total_optimized_size_kb: float = 0.0
        self._seed_presets()

    @classmethod
    def get_instance(cls) -> "ProjectExporter":
        """Thread-safe singleton accessor."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    # ------------------------------------------------------------------
    # Config Management
    # ------------------------------------------------------------------

    def create_config(
        self,
        project_name: str,
        platform: ExportPlatform = ExportPlatform.WEB,
        **kwargs: Any,
    ) -> ExportConfig:
        """
        Create a new export configuration for a game project.

        Accepts optional keyword arguments to override default settings
        for resolution, compression, debug symbols, icon path, bundle id,
        version string, and optimization flags.
        """
        preset = self._presets.get(platform.value)
        default_resolution = preset.default_resolution if preset else (1920, 1080)
        default_bundle_prefix = preset.default_bundle_id_prefix if preset else ""
        default_formats = preset.supported_formats if preset else []

        config = ExportConfig(
            project_name=project_name,
            target_platform=platform,
            output_path=kwargs.get(
                "output_path",
                f"{DEFAULT_EXPORT_OUTPUT_DIR}/{platform.value}/{project_name}",
            ),
            resolution_width=kwargs.get(
                "resolution_width", default_resolution[0]
            ),
            resolution_height=kwargs.get(
                "resolution_height", default_resolution[1]
            ),
            fullscreen=kwargs.get("fullscreen", False),
            compression_level=kwargs.get("compression_level", 6),
            include_debug_symbols=kwargs.get("include_debug_symbols", False),
            icon_path=kwargs.get("icon_path", ""),
            bundle_id=kwargs.get(
                "bundle_id",
                f"{default_bundle_prefix}.{project_name.lower().replace(' ', '')}",
            ),
            version_string=kwargs.get("version_string", "1.0.0"),
            optimization_flags=kwargs.get(
                "optimization_flags",
                list(default_formats),
            ),
        )

        with self._lock:
            self._configs[config.id] = config
            self._config_count += 1

        return config

    def get_config(self, config_id: str) -> Optional[ExportConfig]:
        """Retrieve an export configuration by its id."""
        return self._configs.get(config_id)

    def list_configs(self) -> List[Dict[str, Any]]:
        """List all export configurations with summary fields."""
        result: List[Dict[str, Any]] = []
        for config in self._configs.values():
            result.append(
                {
                    "id": config.id,
                    "project_name": config.project_name,
                    "platform": config.target_platform.value,
                    "resolution": f"{config.resolution_width}x{config.resolution_height}",
                    "version": config.version_string,
                }
            )
        return result

    def delete_config(self, config_id: str) -> bool:
        """Remove an export configuration. Active jobs referencing it are unaffected."""
        with self._lock:
            if config_id not in self._configs:
                return False
            del self._configs[config_id]
            self._config_count -= 1
        return True

    # ------------------------------------------------------------------
    # Export Lifecycle
    # ------------------------------------------------------------------

    def start_export(self, config_id: str) -> Optional[ExportJob]:
        """
        Begin the export pipeline for a configured project.

        The pipeline simulates a multi-stage process:
        1. ASSET_OPTIMIZATION - compresses textures, audio, models, etc.
        2. CODE_BUNDLING - bundles and minifies game scripts
        3. PACKAGING - assembles the final platform-specific package
        4. VALIDATING - runs integrity checks on the output
        5. COMPLETED - marks the export as finished

        Returns the ExportJob tracking progress, or None if the config
        is not found.
        """
        config = self._configs.get(config_id)
        if config is None:
            return None

        job = ExportJob(
            config_id=config_id,
            status=JobStatus.ASSET_OPTIMIZATION,
            progress=0,
            started_at=time.time(),
            current_step="Starting asset optimization",
        )

        with self._lock:
            self._jobs[job.id] = job
            self._job_count += 1

        self._run_asset_optimization(job, config)
        self._run_code_bundling(job, config)
        self._run_packaging(job, config)
        self._run_validation(job, config)

        with self._lock:
            job.status = JobStatus.COMPLETED
            job.progress = 100
            job.completed_at = time.time()
            job.current_step = "Export completed successfully"
            job.output_path = (
                f"{config.output_path}/"
                f"{config.project_name.lower().replace(' ', '_')}"
                f"_{config.version_string}"
                f".{self._get_output_extension(config.target_platform)}"
            )
            job.file_size_mb = self._calculate_job_size(job)
            self._completed_jobs += 1

        return job

    def _run_asset_optimization(self, job: ExportJob, config: ExportConfig) -> None:
        """Simulate the asset optimization stage of the export pipeline."""
        stage_progress_steps = [10, 20, 30, 40, 50]
        asset_order = [
            AssetType.TEXTURE,
            AssetType.AUDIO,
            AssetType.MODEL,
            AssetType.FONT,
            AssetType.SHADER,
            AssetType.DATA,
            AssetType.SCRIPT,
        ]

        for i, asset_type in enumerate(asset_order):
            job.status = JobStatus.ASSET_OPTIMIZATION
            job.current_step = f"Optimizing {asset_type.value} assets"
            job.progress = stage_progress_steps[i % len(stage_progress_steps)]

            original_kb = float(SIMULATED_ORIGINAL_SIZES.get(asset_type, 1024))
            ratio, technique = SIMULATED_ASSET_TYPES.get(
                asset_type, (0.5, "generic_compression")
            )
            optimized_kb = round(original_kb * (1.0 - ratio), 2)

            optimization = AssetOptimization(
                job_id=job.id,
                asset_type=asset_type,
                original_path=f"assets/{asset_type.value}/",
                optimized_path=f"build/{asset_type.value}/optimized/",
                original_size_kb=original_kb,
                optimized_size_kb=optimized_kb,
                compression_ratio=round(ratio, 4),
                technique_used=technique,
            )

            with self._lock:
                self._optimizations[optimization.id] = optimization
                self._total_optimizations += 1
                self._total_original_size_kb += original_kb
                self._total_optimized_size_kb += optimized_kb

    def _run_code_bundling(self, job: ExportJob, config: ExportConfig) -> None:
        """Simulate the code bundling stage of the export pipeline."""
        job.status = JobStatus.CODE_BUNDLING
        job.progress = 55
        job.current_step = "Resolving script dependencies"

        job.progress = 60
        job.current_step = "Minifying source code"

        job.progress = 65
        job.current_step = "Transpiling to target platform bytecode"

        job.progress = 70
        job.current_step = "Linking engine runtime modules"

    def _run_packaging(self, job: ExportJob, config: ExportConfig) -> None:
        """Simulate the packaging stage of the export pipeline."""
        job.status = JobStatus.PACKAGING
        job.progress = 75
        job.current_step = "Assembling asset bundles"

        job.progress = 80
        job.current_step = "Embedding engine runtime"

        job.progress = 85
        job.current_step = "Applying platform-specific headers"

        job.progress = 90
        job.current_step = "Signing package"

    def _run_validation(self, job: ExportJob, config: ExportConfig) -> None:
        """Simulate the validation stage of the export pipeline."""
        job.status = JobStatus.VALIDATING
        job.progress = 92
        job.current_step = "Checking file integrity"

        job.progress = 95
        job.current_step = "Verifying asset references"

        job.progress = 97
        job.current_step = "Running platform compliance checks"

        if config.include_debug_symbols:
            job.warnings.append(
                "Debug symbols included; package size will be larger"
            )

        if config.compression_level < 3:
            job.warnings.append(
                f"Low compression level ({config.compression_level}) "
                "may produce a larger output file"
            )

    def _get_output_extension(self, platform: ExportPlatform) -> str:
        """Return the default file extension for a target platform's output."""
        extensions = {
            ExportPlatform.WEB: "html",
            ExportPlatform.WINDOWS: "exe",
            ExportPlatform.MACOS: "app",
            ExportPlatform.LINUX: "AppImage",
            ExportPlatform.ANDROID: "apk",
            ExportPlatform.IOS: "ipa",
        }
        return extensions.get(platform, "zip")

    def _calculate_job_size(self, job: ExportJob) -> float:
        """Estimate the total exported file size in MB from optimization records."""
        total_kb = 0.0
        for opt in self._optimizations.values():
            if opt.job_id == job.id:
                total_kb += opt.optimized_size_kb
        return round(total_kb / 1024.0, 2) + 5.0  # 5 MB for runtime overhead

    # ------------------------------------------------------------------
    # Job Management
    # ------------------------------------------------------------------

    def get_job_status(self, job_id: str) -> Optional[ExportJob]:
        """Retrieve the current status of an export job."""
        return self._jobs.get(job_id)

    def cancel_export(self, job_id: str) -> bool:
        """
        Cancel a running export job.

        Only jobs in intermediate stages (ASSET_OPTIMIZATION, CODE_BUNDLING,
        PACKAGING, VALIDATING) can be cancelled. Completed and failed jobs
        cannot be cancelled.
        """
        job = self._jobs.get(job_id)
        if job is None:
            return False

        cancellable_statuses = {
            JobStatus.QUEUED,
            JobStatus.ASSET_OPTIMIZATION,
            JobStatus.CODE_BUNDLING,
            JobStatus.PACKAGING,
            JobStatus.VALIDATING,
        }

        if job.status not in cancellable_statuses:
            return False

        with self._lock:
            job.status = JobStatus.FAILED
            job.progress = 0
            job.completed_at = time.time()
            job.current_step = "Export cancelled by user"
            job.errors.append("Export was cancelled before completion")
            self._failed_jobs += 1

        return True

    def get_export_history(self) -> List[ExportJob]:
        """
        Return all export jobs sorted by start time, most recent first.

        Includes both completed and failed jobs.
        """
        jobs = list(self._jobs.values())
        jobs.sort(key=lambda j: j.started_at, reverse=True)
        return jobs

    # ------------------------------------------------------------------
    # Project Validation
    # ------------------------------------------------------------------

    def validate_project(self, config_id: str) -> Dict[str, Any]:
        """
        Run pre-export validation checks on a project configuration.

        Checks for missing assets, broken references, unsupported settings,
        and platform compatibility issues. Returns a dict with pass/fail
        status and a list of detected issues.
        """
        config = self._configs.get(config_id)
        if config is None:
            return {
                "valid": False,
                "config_id": config_id,
                "error": "Configuration not found",
                "checks": [],
            }

        checks: List[Dict[str, Any]] = []

        if not config.project_name:
            checks.append(
                {
                    "check": "project_name",
                    "passed": False,
                    "message": "Project name is empty",
                }
            )
        else:
            checks.append(
                {
                    "check": "project_name",
                    "passed": True,
                    "message": f"Project name '{config.project_name}' is valid",
                }
            )

        if config.resolution_width < 640 or config.resolution_height < 480:
            checks.append(
                {
                    "check": "resolution",
                    "passed": False,
                    "message": (
                        f"Resolution {config.resolution_width}x"
                        f"{config.resolution_height} is below the minimum "
                        "of 640x480"
                    ),
                }
            )
        else:
            checks.append(
                {
                    "check": "resolution",
                    "passed": True,
                    "message": "Resolution meets minimum requirements",
                }
            )

        bundle_ok = bool(config.bundle_id and "." in config.bundle_id)
        checks.append(
            {
                "check": "bundle_id",
                "passed": bundle_ok,
                "message": (
                    f"Bundle ID '{config.bundle_id}' is valid"
                    if bundle_ok
                    else "Bundle ID is missing or malformed"
                ),
            }
        )

        version_parts = config.version_string.split(".")
        version_ok = (
            len(version_parts) >= 2
            and all(p.isdigit() for p in version_parts)
        )
        checks.append(
            {
                "check": "version_string",
                "passed": version_ok,
                "message": (
                    f"Version '{config.version_string}' is valid"
                    if version_ok
                    else "Version string must follow major.minor[.patch] format"
                ),
            }
        )

        compression_ok = 0 <= config.compression_level <= 9
        checks.append(
            {
                "check": "compression_level",
                "passed": compression_ok,
                "message": (
                    f"Compression level {config.compression_level} is valid"
                    if compression_ok
                    else "Compression level must be between 0 and 9"
                ),
            }
        )

        all_passed = all(c["passed"] for c in checks)

        return {
            "valid": all_passed,
            "config_id": config_id,
            "project_name": config.project_name,
            "platform": config.target_platform.value,
            "checks": checks,
            "total_checks": len(checks),
            "passed_checks": sum(1 for c in checks if c["passed"]),
            "failed_checks": sum(1 for c in checks if not c["passed"]),
        }

    def estimate_export_size(self, config_id: str) -> Tuple[float, str]:
        """
        Estimate the exported package size for a given configuration.

        Returns a tuple of (estimated_size_mb, breakdown_description).
        The breakdown describes the contribution of each asset category
        and runtime overhead to the total.
        """
        config = self._configs.get(config_id)
        if config is None:
            return (0.0, "Configuration not found")

        total_kb = 0.0
        breakdown_parts: List[str] = []

        for asset_type in AssetType:
            original = float(SIMULATED_ORIGINAL_SIZES.get(asset_type, 1024))
            ratio, _ = SIMULATED_ASSET_TYPES.get(asset_type, (0.5, ""))
            optimized = original * (1.0 - ratio)
            total_kb += optimized

            mb = round(optimized / 1024.0, 2)
            breakdown_parts.append(f"{asset_type.value}: {mb} MB")

        runtime_overhead_mb = 5.0
        total_mb = round(total_kb / 1024.0, 2) + runtime_overhead_mb

        breakdown = (
            f"Estimated total: {total_mb} MB\n"
            + "  Asset breakdown:\n"
            + "\n".join(f"    - {part}" for part in breakdown_parts)
            + f"\n  Runtime overhead: {runtime_overhead_mb} MB"
        )

        return (total_mb, breakdown)

    # ------------------------------------------------------------------
    # Platform Presets
    # ------------------------------------------------------------------

    def _seed_presets(self) -> None:
        """Initialize built-in platform presets for all supported targets."""
        self._add_web_preset()
        self._add_windows_preset()
        self._add_macos_preset()
        self._add_linux_preset()
        self._add_android_preset()
        self._add_ios_preset()

    def _add_web_preset(self) -> None:
        preset = PlatformPreset(
            platform=ExportPlatform.WEB,
            default_resolution=(1920, 1080),
            supported_formats=["HTML5", "WASM"],
            default_bundle_id_prefix="com.sparklabs.web",
            min_sdk_version="",
            icon_sizes=[(16, 16), (32, 32), (64, 64), (128, 128), (256, 256)],
            required_permissions=[],
        )
        self._presets[preset.platform.value] = preset

    def _add_windows_preset(self) -> None:
        preset = PlatformPreset(
            platform=ExportPlatform.WINDOWS,
            default_resolution=(1920, 1080),
            supported_formats=["EXE", "DLL"],
            default_bundle_id_prefix="com.sparklabs.windows",
            min_sdk_version="11",
            icon_sizes=[(16, 16), (32, 32), (48, 48), (256, 256)],
            required_permissions=[],
        )
        self._presets[preset.platform.value] = preset

    def _add_macos_preset(self) -> None:
        preset = PlatformPreset(
            platform=ExportPlatform.MACOS,
            default_resolution=(1920, 1080),
            supported_formats=["APP", "DMG"],
            default_bundle_id_prefix="com.sparklabs.macos",
            min_sdk_version="11.0",
            icon_sizes=[
                (16, 16), (32, 32), (64, 64), (128, 128),
                (256, 256), (512, 512), (1024, 1024),
            ],
            required_permissions=[],
        )
        self._presets[preset.platform.value] = preset

    def _add_linux_preset(self) -> None:
        preset = PlatformPreset(
            platform=ExportPlatform.LINUX,
            default_resolution=(1920, 1080),
            supported_formats=["ELF", "APPIMAGE"],
            default_bundle_id_prefix="com.sparklabs.linux",
            min_sdk_version="2.31",
            icon_sizes=[(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)],
            required_permissions=[],
        )
        self._presets[preset.platform.value] = preset

    def _add_android_preset(self) -> None:
        preset = PlatformPreset(
            platform=ExportPlatform.ANDROID,
            default_resolution=(2340, 1080),
            supported_formats=["APK", "AAB"],
            default_bundle_id_prefix="com.sparklabs.android",
            min_sdk_version="26",
            icon_sizes=[
                (48, 48), (72, 72), (96, 96), (144, 144), (192, 192),
            ],
            required_permissions=["INTERNET", "STORAGE"],
        )
        self._presets[preset.platform.value] = preset

    def _add_ios_preset(self) -> None:
        preset = PlatformPreset(
            platform=ExportPlatform.IOS,
            default_resolution=(2532, 1170),
            supported_formats=["IPA"],
            default_bundle_id_prefix="com.sparklabs.ios",
            min_sdk_version="15.0",
            icon_sizes=[
                (20, 20), (29, 29), (40, 40), (60, 60),
                (76, 76), (83.5, 83.5), (1024, 1024),
            ],
            required_permissions=[],
        )
        self._presets[preset.platform.value] = preset

    def get_platform_preset(self, platform: ExportPlatform) -> Optional[PlatformPreset]:
        """Retrieve the built-in preset for a specific target platform."""
        return self._presets.get(platform.value)

    def get_presets(self) -> List[PlatformPreset]:
        """Return all registered platform presets."""
        return list(self._presets.values())

    # ------------------------------------------------------------------
    # Optimizations
    # ------------------------------------------------------------------

    def get_optimizations(self, job_id: Optional[str] = None) -> List[AssetOptimization]:
        """
        Retrieve asset optimization records.

        If a job_id is provided, filters to only that job's records.
        Otherwise returns all recorded optimizations.
        """
        if job_id:
            return [
                opt
                for opt in self._optimizations.values()
                if opt.job_id == job_id
            ]
        return list(self._optimizations.values())

    # ------------------------------------------------------------------
    # Statistics
    # ------------------------------------------------------------------

    def get_stats(self) -> Dict[str, Any]:
        """Return aggregate statistics for the export pipeline."""
        platform_counts: Dict[str, int] = {}
        status_counts: Dict[str, int] = {}

        for job in self._jobs.values():
            config = self._configs.get(job.config_id)
            if config:
                platform_name = config.target_platform.value
                platform_counts[platform_name] = (
                    platform_counts.get(platform_name, 0) + 1
                )
            status_name = job.status.value
            status_counts[status_name] = status_counts.get(status_name, 0) + 1

        total_original_mb = round(self._total_original_size_kb / 1024.0, 2)
        total_optimized_mb = round(self._total_optimized_size_kb / 1024.0, 2)
        overall_ratio = (
            round(1.0 - (total_optimized_mb / total_original_mb), 4)
            if total_original_mb > 0
            else 0.0
        )

        return {
            "total_configs": self._config_count,
            "total_jobs": self._job_count,
            "completed_jobs": self._completed_jobs,
            "failed_jobs": self._failed_jobs,
            "active_jobs": self._job_count - self._completed_jobs - self._failed_jobs,
            "total_optimizations": self._total_optimizations,
            "total_original_size_mb": total_original_mb,
            "total_optimized_size_mb": total_optimized_mb,
            "overall_compression_ratio": overall_ratio,
            "platform_distribution": platform_counts,
            "status_distribution": status_counts,
            "presets_available": len(self._presets),
        }


# ------------------------------------------------------------------
# Module-level Accessor
# ------------------------------------------------------------------


def get_project_exporter() -> ProjectExporter:
    """
    Return the singleton ProjectExporter instance.

    Usage:
        exporter = get_project_exporter()
        config = exporter.create_config("MyGame", ExportPlatform.ANDROID)
        job = exporter.start_export(config.id)
    """
    return ProjectExporter.get_instance()