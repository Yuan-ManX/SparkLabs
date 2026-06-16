"""
SparkLabs Engine - Deployment Orchestrator

An AI-driven deployment orchestration system that handles cross-platform game
building, packaging, optimization, and distribution for the AI-native game
engine. Coordinates the full lifecycle from build configuration through
compilation, asset optimization, packaging, signing, and deployment to
distribution platforms.

Architecture:
  DeploymentOrchestrator (Singleton)
    |-- BuildConfiguration (per-platform build settings)
    |-- BuildJob (individual build pipeline execution)
    |-- DeploymentTarget (distribution store/platform endpoint)
    |-- TargetPlatform / BuildStatus / OptimizationLevel (enums)

Capabilities:
  - CREATE: define build configurations per target platform
  - QUEUE: submit build jobs for individual or batch execution
  - EXECUTE: simulate the full build pipeline (prepare, compile, package,
    optimize, sign, complete)
  - OPTIMIZE: simulate asset optimization (texture/audio compression,
    code minification, deduplication, sprite atlas generation)
  - PACKAGE: bundle game into platform-specific output formats
  - DEPLOY: simulate deployment to distribution targets (Steam, Epic, etc.)
  - ESTIMATE: predict build size and build time for a configuration
  - MONITOR: track build status, progress, and aggregate statistics
"""

from __future__ import annotations

import json
import os
import threading
import time
import uuid
from collections import deque
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Domain Enums
# ---------------------------------------------------------------------------


class TargetPlatform(Enum):
    """Supported target platforms for game builds and deployment."""
    WEB = "web"
    WINDOWS = "windows"
    MACOS = "macos"
    LINUX = "linux"
    IOS = "ios"
    ANDROID = "android"
    HTML5 = "html5"
    PWA = "pwa"
    STEAM = "steam"
    EPIC = "epic"
    ITCH = "itch"


class BuildStatus(Enum):
    """Ordered lifecycle states for a build job."""
    QUEUED = "queued"
    PREPARING = "preparing"
    COMPILING = "compiling"
    PACKAGING = "packaging"
    OPTIMIZING = "optimizing"
    SIGNING = "signing"
    UPLOADING = "uploading"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class OptimizationLevel(Enum):
    """Granularity of asset and code optimization applied during builds."""
    NONE = "none"
    BASIC = "basic"
    STANDARD = "standard"
    AGGRESSIVE = "aggressive"
    MAXIMUM = "maximum"


# Ordered sequence for pipeline progression
BUILD_PIPELINE_SEQUENCE: Tuple[BuildStatus, ...] = (
    BuildStatus.QUEUED,
    BuildStatus.PREPARING,
    BuildStatus.COMPILING,
    BuildStatus.PACKAGING,
    BuildStatus.OPTIMIZING,
    BuildStatus.SIGNING,
    BuildStatus.COMPLETED,
)

# Platform-specific output format mappings
PLATFORM_OUTPUT_FORMATS: Dict[TargetPlatform, str] = {
    TargetPlatform.WEB: "html",
    TargetPlatform.WINDOWS: "exe",
    TargetPlatform.MACOS: "app",
    TargetPlatform.LINUX: "tar.gz",
    TargetPlatform.IOS: "ipa",
    TargetPlatform.ANDROID: "apk",
    TargetPlatform.HTML5: "html",
    TargetPlatform.PWA: "pwa",
    TargetPlatform.STEAM: "exe",
    TargetPlatform.EPIC: "exe",
    TargetPlatform.ITCH: "zip",
}

# Platform-specific output directory naming
PLATFORM_OUTPUT_DIRS: Dict[TargetPlatform, str] = {
    TargetPlatform.WEB: "web_build",
    TargetPlatform.WINDOWS: "windows_build",
    TargetPlatform.MACOS: "macos_build",
    TargetPlatform.LINUX: "linux_build",
    TargetPlatform.IOS: "ios_build",
    TargetPlatform.ANDROID: "android_build",
    TargetPlatform.HTML5: "html5_build",
    TargetPlatform.PWA: "pwa_build",
    TargetPlatform.STEAM: "steam_build",
    TargetPlatform.EPIC: "epic_build",
    TargetPlatform.ITCH: "itch_build",
}

# Estimated base sizes in megabytes per platform for a default project
PLATFORM_BASE_SIZES_MB: Dict[TargetPlatform, float] = {
    TargetPlatform.WEB: 12.0,
    TargetPlatform.WINDOWS: 45.0,
    TargetPlatform.MACOS: 52.0,
    TargetPlatform.LINUX: 38.0,
    TargetPlatform.IOS: 35.0,
    TargetPlatform.ANDROID: 28.0,
    TargetPlatform.HTML5: 10.0,
    TargetPlatform.PWA: 8.0,
    TargetPlatform.STEAM: 55.0,
    TargetPlatform.EPIC: 55.0,
    TargetPlatform.ITCH: 25.0,
}

# Optimization level multipliers for build time and size
OPTIMIZATION_MULTIPLIERS: Dict[OptimizationLevel, Dict[str, float]] = {
    OptimizationLevel.NONE: {"time": 1.0, "size_reduction": 0.0},
    OptimizationLevel.BASIC: {"time": 1.15, "size_reduction": 0.10},
    OptimizationLevel.STANDARD: {"time": 1.35, "size_reduction": 0.22},
    OptimizationLevel.AGGRESSIVE: {"time": 1.70, "size_reduction": 0.35},
    OptimizationLevel.MAXIMUM: {"time": 2.20, "size_reduction": 0.48},
}

# Store types for deployment targets
STORE_TYPES = ("steamworks", "epic_games_store", "itch_io", "app_store", "google_play",
               "custom_cdn", "direct_download")


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------


@dataclass
class BuildConfiguration:
    """Immutable snapshot of a build configuration for a specific target platform."""
    config_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = ""
    platform: TargetPlatform = TargetPlatform.WEB
    optimization_level: OptimizationLevel = OptimizationLevel.STANDARD
    target_resolution: Tuple[int, int] = (1920, 1080)
    compression: int = 6
    include_assets: List[str] = field(default_factory=list)
    exclude_patterns: List[str] = field(default_factory=list)
    custom_flags: Dict[str, str] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "config_id": self.config_id,
            "name": self.name,
            "platform": self.platform.value,
            "optimization_level": self.optimization_level.value,
            "target_resolution": {
                "width": self.target_resolution[0],
                "height": self.target_resolution[1],
            },
            "compression": self.compression,
            "include_assets": list(self.include_assets),
            "exclude_patterns": list(self.exclude_patterns),
            "custom_flags": dict(self.custom_flags),
            "created_at": self.created_at,
        }


@dataclass
class BuildJob:
    """Tracks a build job through each stage of the deployment pipeline."""
    job_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    config_id: str = ""
    platform: TargetPlatform = TargetPlatform.WEB
    status: BuildStatus = BuildStatus.QUEUED
    progress: float = 0.0
    started_at: float = 0.0
    completed_at: float = 0.0
    output_path: str = ""
    file_size: float = 0.0
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    duration_seconds: float = 0.0
    current_step: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "job_id": self.job_id,
            "config_id": self.config_id,
            "platform": self.platform.value,
            "status": self.status.value,
            "progress": self.progress,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "output_path": self.output_path,
            "file_size": self.file_size,
            "errors": list(self.errors),
            "warnings": list(self.warnings),
            "duration_seconds": self.duration_seconds,
            "current_step": self.current_step,
        }


@dataclass
class DeploymentTarget:
    """Represents a distribution endpoint where builds can be deployed."""
    target_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = ""
    platform: TargetPlatform = TargetPlatform.WEB
    store_type: str = ""
    credentials_ref: str = ""
    status: str = "configured"
    last_deployed: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "target_id": self.target_id,
            "name": self.name,
            "platform": self.platform.value,
            "store_type": self.store_type,
            "credentials_ref": self.credentials_ref,
            "status": self.status,
            "last_deployed": self.last_deployed,
            "metadata": dict(self.metadata),
        }


# ---------------------------------------------------------------------------
# Deployment Orchestrator
# ---------------------------------------------------------------------------


class DeploymentOrchestrator:
    """
    AI-driven cross-platform game deployment orchestration system.

    Manages the complete lifecycle of building, optimizing, packaging, and
    deploying game projects across multiple target platforms and distribution
    stores. Each build progresses through a simulated pipeline (prepare,
    compile, package, optimize, sign, complete) with full status tracking
    and aggregate statistics.

    Usage:
        orch = get_deployment_orchestrator()
        config = orch.create_build_config("MyGame", TargetPlatform.WINDOWS)
        job = orch.queue_build(config.config_id)
        result = orch.execute_build(job.job_id)
        stats = orch.get_stats()
    """

    _instance: Optional["DeploymentOrchestrator"] = None
    _lock: threading.RLock = threading.RLock()

    def __init__(self) -> None:
        self._configs: Dict[str, BuildConfiguration] = {}
        self._jobs: Dict[str, BuildJob] = {}
        self._targets: Dict[str, DeploymentTarget] = {}
        self._job_history: deque = deque(maxlen=100)
        self._config_count: int = 0
        self._job_count: int = 0
        self._completed_jobs: int = 0
        self._failed_jobs: int = 0
        self._cancelled_jobs: int = 0
        self._total_build_time: float = 0.0
        self._total_size_saved_mb: float = 0.0
        self._active_jobs: int = 0
        self._seed_pipeline_timings()

    # ------------------------------------------------------------------
    # Internal Helpers
    # ------------------------------------------------------------------

    def _seed_pipeline_timings(self) -> None:
        """Seed simulated timing values (in seconds) for each pipeline stage."""
        self._stage_timings: Dict[BuildStatus, Dict[str, Tuple[float, float]]] = {
            BuildStatus.PREPARING: {"base": (0.3, 1.0), "description": "Validating configuration"},
            BuildStatus.COMPILING: {"base": (1.5, 4.0), "description": "Compiling game scripts"},
            BuildStatus.PACKAGING: {"base": (1.0, 3.0), "description": "Bundling platform package"},
            BuildStatus.OPTIMIZING: {"base": (0.8, 2.5), "description": "Optimizing assets"},
            BuildStatus.SIGNING: {"base": (0.2, 0.8), "description": "Applying signatures"},
        }

    def _validate_config(self, config_id: str) -> BuildConfiguration:
        """Look up and validate a build configuration by id."""
        config = self._configs.get(config_id)
        if config is None:
            raise ValueError(f"Build configuration '{config_id}' not found")
        return config

    def _validate_job(self, job_id: str) -> BuildJob:
        """Look up and validate a build job by id."""
        job = self._jobs.get(job_id)
        if job is None:
            raise ValueError(f"Build job '{job_id}' not found")
        return job

    def _compute_output_path(self, config: BuildConfiguration, output_format: str = "") -> str:
        """Generate a platform-appropriate output directory and filename."""
        platform_dir = PLATFORM_OUTPUT_DIRS.get(config.platform, "build")
        ext = output_format or PLATFORM_OUTPUT_FORMATS.get(config.platform, "bin")
        safe_name = config.name.replace(" ", "_").lower()
        return f"./builds/{platform_dir}/{safe_name}.{ext}"

    @classmethod
    def get_instance(cls) -> "DeploymentOrchestrator":
        """Thread-safe singleton accessor."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    # ------------------------------------------------------------------
    # Build Configuration
    # ------------------------------------------------------------------

    def create_build_config(
        self,
        name: str,
        platform: TargetPlatform = TargetPlatform.WEB,
        optimization_level: OptimizationLevel = OptimizationLevel.STANDARD,
        target_resolution: Tuple[int, int] = (1920, 1080),
        compression: int = 6,
        include_assets: List[str] = None,
        exclude_patterns: List[str] = None,
        custom_flags: Dict[str, str] = None,
    ) -> BuildConfiguration:
        """
        Create a new build configuration for a target platform.

        Args:
            name: Human-readable name for this build configuration.
            platform: Target platform to build for.
            optimization_level: How aggressively to optimize assets and code.
            target_resolution: Output resolution as (width, height).
            compression: Compression level 0-9 for asset packaging.
            include_assets: Specific asset paths to include.
            exclude_patterns: Glob patterns for assets to exclude.
            custom_flags: Platform-specific build flags.

        Returns:
            The newly created BuildConfiguration.
        """
        config = BuildConfiguration(
            name=name,
            platform=platform,
            optimization_level=optimization_level,
            target_resolution=target_resolution,
            compression=compression,
            include_assets=include_assets or [],
            exclude_patterns=exclude_patterns or [],
            custom_flags=custom_flags or {},
        )
        with self._lock:
            self._configs[config.config_id] = config
            self._config_count += 1
        return config

    # ------------------------------------------------------------------
    # Build Queuing & Execution
    # ------------------------------------------------------------------

    def queue_build(self, config_id: str) -> BuildJob:
        """
        Queue a new build job from an existing configuration.

        Args:
            config_id: The id of the BuildConfiguration to use.

        Returns:
            The newly created BuildJob in QUEUED status.
        """
        config = self._validate_config(config_id)
        job = BuildJob(
            config_id=config_id,
            platform=config.platform,
            status=BuildStatus.QUEUED,
        )
        with self._lock:
            self._jobs[job.job_id] = job
            self._job_count += 1
            self._job_history.append(job.job_id)
        return job

    def execute_build(self, job_id: str) -> BuildJob:
        """
        Execute the full simulated build pipeline for a queued job.

        Progresses through PREPARING, COMPILING, PACKAGING, OPTIMIZING,
        SIGNING, and COMPLETED stages. Each stage updates progress,
        appends any warnings, and records timing.

        Args:
            job_id: The id of the BuildJob to execute.

        Returns:
            The completed or failed BuildJob.
        """
        job = self._validate_job(job_id)
        config = self._validate_config(job.config_id)

        if job.status not in (BuildStatus.QUEUED, BuildStatus.FAILED):
            raise RuntimeError(
                f"Cannot execute build in status '{job.status.value}'. "
                f"Expected QUEUED or FAILED."
            )

        with self._lock:
            job.started_at = time.time()
            job.status = BuildStatus.PREPARING
            job.current_step = "Initializing build environment"
            self._active_jobs += 1

        pipeline_stages = [
            (BuildStatus.PREPARING, "Validating build configuration and dependencies"),
            (BuildStatus.COMPILING, "Compiling game scripts, shaders, and processing assets"),
            (BuildStatus.PACKAGING, "Bundling assets into platform-specific package"),
            (BuildStatus.OPTIMIZING, "Compressing textures, stripping symbols, minifying code"),
            (BuildStatus.SIGNING, "Applying platform digital signatures"),
        ]

        progression_points = [5.0, 20.0, 45.0, 70.0, 90.0]

        try:
            for idx, (stage, description) in enumerate(pipeline_stages):
                with self._lock:
                    job.status = stage
                    job.progress = progression_points[idx]
                    job.current_step = description

                timing = self._stage_timings[stage]
                opt_mult = OPTIMIZATION_MULTIPLIERS[config.optimization_level]["time"]
                base_min, base_max = timing["base"]
                duration = (base_min + (base_min * 0.3)) * opt_mult
                time.sleep(0.01)  # Tiny real delay to prevent zero duration

                # Simulate occasional warnings
                if idx == 2 and config.compression > 7:
                    with self._lock:
                        job.warnings.append(
                            "High compression level may increase load times on low-end devices"
                        )
                if idx == 3 and config.optimization_level == OptimizationLevel.MAXIMUM:
                    with self._lock:
                        job.warnings.append(
                            "Maximum optimization may cause minor visual degradation on some assets"
                        )

            # Compute output
            output_format = PLATFORM_OUTPUT_FORMATS.get(config.platform, "bin")
            output_path = self._compute_output_path(config, output_format)

            # Simulate file size
            base_size = PLATFORM_BASE_SIZES_MB.get(config.platform, 40.0)
            size_reduction = OPTIMIZATION_MULTIPLIERS[config.optimization_level]["size_reduction"]
            final_size = round(base_size * (1.0 - size_reduction), 2)

            with self._lock:
                job.status = BuildStatus.COMPLETED
                job.progress = 100.0
                job.completed_at = time.time()
                job.output_path = output_path
                job.file_size = final_size
                job.duration_seconds = round(job.completed_at - job.started_at, 3)
                job.current_step = "Build completed successfully"
                self._completed_jobs += 1
                self._total_build_time += job.duration_seconds
                self._total_size_saved_mb += base_size - final_size
                self._active_jobs -= 1

        except Exception as exc:
            with self._lock:
                job.status = BuildStatus.FAILED
                job.errors.append(str(exc))
                job.current_step = f"Build failed: {exc}"
                job.completed_at = time.time()
                if job.started_at > 0:
                    job.duration_seconds = round(job.completed_at - job.started_at, 3)
                self._failed_jobs += 1
                self._active_jobs -= 1

        return job

    def batch_build(self, config_ids: List[str]) -> List[BuildJob]:
        """
        Queue and execute builds for multiple configurations sequentially.

        Args:
            config_ids: List of build configuration ids to process.

        Returns:
            List of resulting BuildJob instances in execution order.
        """
        results: List[BuildJob] = []
        for cid in config_ids:
            try:
                job = self.queue_build(cid)
                executed = self.execute_build(job.job_id)
                results.append(executed)
            except (ValueError, RuntimeError) as exc:
                # Create a synthetic failed job record for tracking
                synthetic = BuildJob(
                    config_id=cid,
                    status=BuildStatus.FAILED,
                    errors=[str(exc)],
                )
                results.append(synthetic)
                with self._lock:
                    self._jobs[synthetic.job_id] = synthetic
                    self._failed_jobs += 1
        return results

    # ------------------------------------------------------------------
    # Asset Optimization
    # ------------------------------------------------------------------

    def optimize_assets(self, job_id: str) -> Dict[str, Any]:
        """
        Simulate asset optimization for a completed build job.

        Performs the following simulated optimizations:
          - Texture compression with size reduction calculation
          - Audio compression with bitrate adjustment
          - Code minification with byte savings
          - Asset deduplication with duplicate count
          - Sprite atlas generation with atlas dimensions

        Args:
            job_id: The id of the build job whose assets to optimize.

        Returns:
            Dictionary with per-category optimization results and totals.
        """
        job = self._validate_job(job_id)
        config = self._validate_config(job.config_id)

        opt_level = config.optimization_level
        multiplier = OPTIMIZATION_MULTIPLIERS[opt_level]["time"]

        # -- Simulated texture compression --
        texture_original_count = 48
        texture_original_size_kb = 4096.0 * texture_original_count
        texture_reduction_pct = 0.25 + (0.06 * list(OptimizationLevel).index(opt_level))
        texture_saved_kb = round(texture_original_size_kb * texture_reduction_pct, 1)
        texture_final_kb = round(texture_original_size_kb - texture_saved_kb, 1)

        # -- Simulated audio compression --
        audio_original_count = 64
        audio_original_bitrate = 320
        audio_target_bitrate = 128 if opt_level.value in ("aggressive", "maximum") else 192
        audio_bitrate_reduction = audio_original_bitrate - audio_target_bitrate
        audio_original_size_kb = 3072.0 * audio_original_count
        audio_reduction_pct = audio_bitrate_reduction / audio_original_bitrate
        audio_saved_kb = round(audio_original_size_kb * audio_reduction_pct, 1)
        audio_final_kb = round(audio_original_size_kb - audio_saved_kb, 1)

        # -- Simulated code minification --
        code_original_size_kb = 512.0
        code_reduction_pct = 0.15 + (0.04 * list(OptimizationLevel).index(opt_level))
        code_saved_bytes = int(code_original_size_kb * code_reduction_pct * 1024)
        code_final_kb = round(code_original_size_kb * (1.0 - code_reduction_pct), 1)

        # -- Simulated asset deduplication --
        duplicate_count = 12 if opt_level.value in ("aggressive", "maximum") else 5
        dedup_saved_kb = round(duplicate_count * 128.0, 1)

        # -- Simulated sprite atlas generation --
        atlas_sheets = 3 if opt_level.value in ("aggressive", "maximum") else 1
        atlas_dimensions = "2048x2048" if opt_level.value == "maximum" else "1024x1024"
        atlas_draw_call_reduction = round(48 * 0.6)
        atlas_saved_kb = round(atlas_sheets * 256.0, 1)

        total_textures = texture_original_count - duplicate_count
        total_audio = audio_original_count
        total_saved_kb = round(
            texture_saved_kb + audio_saved_kb + (code_original_size_kb - code_final_kb)
            + dedup_saved_kb + atlas_saved_kb, 1
        )
        total_original_kb = round(
            texture_original_size_kb + audio_original_size_kb + code_original_size_kb, 1
        )
        overall_reduction_pct = round((total_saved_kb / total_original_kb) * 100, 1)

        result = {
            "job_id": job_id,
            "optimization_level": opt_level.value,
            "textures": {
                "original_count": texture_original_count,
                "original_size_kb": texture_original_size_kb,
                "reduction_percent": round(texture_reduction_pct * 100, 1),
                "saved_kb": texture_saved_kb,
                "final_size_kb": texture_final_kb,
                "technique": "astc_compression",
            },
            "audio": {
                "original_count": audio_original_count,
                "original_size_kb": audio_original_size_kb,
                "original_bitrate": audio_original_bitrate,
                "target_bitrate": audio_target_bitrate,
                "reduction_percent": round(audio_reduction_pct * 100, 1),
                "saved_kb": audio_saved_kb,
                "final_size_kb": audio_final_kb,
                "technique": "vorbis_transcoding",
            },
            "code": {
                "original_size_kb": code_original_size_kb,
                "reduction_percent": round(code_reduction_pct * 100, 1),
                "saved_bytes": code_saved_bytes,
                "final_size_kb": code_final_kb,
                "technique": "terser_minification",
            },
            "deduplication": {
                "duplicate_assets_found": duplicate_count,
                "saved_kb": dedup_saved_kb,
                "technique": "content_hash_matching",
            },
            "sprite_atlas": {
                "sheets_generated": atlas_sheets,
                "atlas_dimensions": atlas_dimensions,
                "draw_call_reduction": atlas_draw_call_reduction,
                "saved_kb": atlas_saved_kb,
                "technique": "maxrects_packing",
            },
            "totals": {
                "total_textures_final": total_textures,
                "total_audio_clips": total_audio,
                "total_original_kb": total_original_kb,
                "total_saved_kb": total_saved_kb,
                "overall_reduction_percent": overall_reduction_pct,
            },
        }
        return result

    # ------------------------------------------------------------------
    # Game Packaging
    # ------------------------------------------------------------------

    def package_game(self, job_id: str, output_format: str = "") -> Dict[str, Any]:
        """
        Simulate packaging a completed build into a distributable format.

        Args:
            job_id: The id of the build job to package.
            output_format: Desired output format override (e.g. "zip", "exe").

        Returns:
            Dictionary with packaging details, file counts, and paths.
        """
        job = self._validate_job(job_id)
        config = self._validate_config(job.config_id)

        if job.status != BuildStatus.COMPLETED:
            raise RuntimeError(
                f"Cannot package build in status '{job.status.value}'. "
                f"Expected COMPLETED."
            )

        fmt = output_format or PLATFORM_OUTPUT_FORMATS.get(config.platform, "bin")
        output_path = self._compute_output_path(config, fmt)

        total_files = 120 + len(config.include_assets) * 15 - len(config.exclude_patterns) * 3
        executable_name = f"{config.name.replace(' ', '_').lower()}.{fmt}"
        bundle_size_mb = round(job.file_size * (1.0 + config.compression * 0.02), 2)

        result = {
            "job_id": job_id,
            "config_name": config.name,
            "platform": config.platform.value,
            "output_format": fmt,
            "output_path": output_path,
            "executable_name": executable_name,
            "bundle_size_mb": bundle_size_mb,
            "total_files": total_files,
            "compression_level": config.compression,
            "resolution": {
                "width": config.target_resolution[0],
                "height": config.target_resolution[1],
            },
            "package_structure": {
                "binaries": 1,
                "assets": total_files - 10,
                "libraries": config.platform == TargetPlatform.WINDOWS and 3 or 2,
                "config_files": 4,
                "metadata_files": 3,
            },
        }
        return result

    # ------------------------------------------------------------------
    # Deployment
    # ------------------------------------------------------------------

    def deploy_to_target(self, job_id: str, target_id: str) -> Dict[str, Any]:
        """
        Simulate deploying a completed build to a distribution target.

        Validates the build is completed, the target exists, and that the
        build platform matches the deployment target platform. Simulates the
        upload process with timing and status updates.

        Args:
            job_id: The id of the build job to deploy.
            target_id: The id of the DeploymentTarget to deploy to.

        Returns:
            Dictionary with deployment results and metadata.
        """
        job = self._validate_job(job_id)
        target = self._targets.get(target_id)
        if target is None:
            raise ValueError(f"Deployment target '{target_id}' not found")

        if job.status != BuildStatus.COMPLETED:
            raise RuntimeError(
                f"Cannot deploy build in status '{job.status.value}'. "
                f"Expected COMPLETED."
            )

        if job.platform != target.platform:
            raise ValueError(
                f"Build platform '{job.platform.value}' does not match "
                f"target platform '{target.platform.value}'"
            )

        with self._lock:
            job.status = BuildStatus.UPLOADING
            job.current_step = f"Uploading to {target.name} ({target.store_type})"

        time.sleep(0.01)

        deploy_start = time.time()
        simulated_upload_mbps = 25.0
        upload_duration = job.file_size / simulated_upload_mbps

        with self._lock:
            target.last_deployed = time.time()
            target.status = "active"
            job.status = BuildStatus.COMPLETED
            job.current_step = f"Deployed successfully to {target.name}"

        result = {
            "job_id": job_id,
            "target_id": target_id,
            "target_name": target.name,
            "store_type": target.store_type,
            "upload_size_mb": job.file_size,
            "upload_speed_mbps": simulated_upload_mbps,
            "upload_duration_seconds": round(upload_duration, 2),
            "deployed_at": target.last_deployed,
            "build_output": job.output_path,
            "deployment_url": f"https://{target.store_type}.example.com/builds/{job.job_id}",
            "checksum": uuid.uuid4().hex[:16],
            "status": "deployed",
        }
        return result

    # ------------------------------------------------------------------
    # Estimation
    # ------------------------------------------------------------------

    def estimate_build_size(self, config_id: str) -> Dict[str, Any]:
        """
        Estimate the expected output size of a build configuration.

        Factors in platform base size, optimization level reduction,
        and compression settings to produce a projected file size.

        Args:
            config_id: The id of the BuildConfiguration to estimate.

        Returns:
            Dictionary with size breakdown and projected total.
        """
        config = self._validate_config(config_id)
        base_size = PLATFORM_BASE_SIZES_MB.get(config.platform, 40.0)
        size_reduction = OPTIMIZATION_MULTIPLIERS[config.optimization_level]["size_reduction"]
        optimized_size = round(base_size * (1.0 - size_reduction), 2)
        compressed_size = round(optimized_size * (1.0 - config.compression * 0.015), 2)

        asset_count = len(config.include_assets)
        excluded_count = len(config.exclude_patterns)
        asset_overhead = round(asset_count * 0.5, 2)
        exclusion_savings = round(excluded_count * 0.2, 2)

        projected = round(compressed_size + asset_overhead - exclusion_savings, 2)

        return {
            "config_id": config_id,
            "config_name": config.name,
            "platform": config.platform.value,
            "optimization_level": config.optimization_level.value,
            "base_size_mb": base_size,
            "optimized_size_mb": optimized_size,
            "compressed_size_mb": compressed_size,
            "asset_overhead_mb": asset_overhead,
            "exclusion_savings_mb": exclusion_savings,
            "projected_total_mb": projected,
            "projected_total_kb": round(projected * 1024, 1),
        }

    def estimate_build_time(self, config_id: str) -> Dict[str, Any]:
        """
        Estimate the expected build duration for a configuration.

        Aggregates per-stage timing estimates scaled by the optimization
        level multiplier and platform complexity factor.

        Args:
            config_id: The id of the BuildConfiguration to estimate.

        Returns:
            Dictionary with per-stage and total time estimates.
        """
        config = self._validate_config(config_id)
        opt_mult = OPTIMIZATION_MULTIPLIERS[config.optimization_level]["time"]

        platform_complexity = {
            TargetPlatform.WEB: 0.8,
            TargetPlatform.HTML5: 0.8,
            TargetPlatform.PWA: 0.8,
            TargetPlatform.WINDOWS: 1.0,
            TargetPlatform.MACOS: 1.1,
            TargetPlatform.LINUX: 1.0,
            TargetPlatform.IOS: 1.3,
            TargetPlatform.ANDROID: 1.2,
            TargetPlatform.STEAM: 1.1,
            TargetPlatform.EPIC: 1.1,
            TargetPlatform.ITCH: 0.9,
        }
        complexity = platform_complexity.get(config.platform, 1.0)

        stage_estimates = {}
        total = 0.0
        for stage, timing in self._stage_timings.items():
            base_min, base_max = timing["base"]
            avg = ((base_min + base_max) / 2.0) * opt_mult * complexity
            stage_estimates[stage.value] = {
                "description": timing["description"],
                "estimated_seconds": round(avg, 2),
                "min_seconds": round(base_min * opt_mult * complexity, 2),
                "max_seconds": round(base_max * opt_mult * complexity, 2),
            }
            total += avg

        return {
            "config_id": config_id,
            "config_name": config.name,
            "platform": config.platform.value,
            "optimization_level": config.optimization_level.value,
            "complexity_factor": complexity,
            "optimization_multiplier": opt_mult,
            "stages": stage_estimates,
            "total_estimated_seconds": round(total, 2),
            "total_estimated_minutes": round(total / 60.0, 2),
            "confidence": "medium" if complexity > 1.0 else "high",
        }

    # ------------------------------------------------------------------
    # Status & Querying
    # ------------------------------------------------------------------

    def get_build_status(self, job_id: str) -> BuildJob:
        """
        Retrieve the current status of a build job.

        Args:
            job_id: The id of the BuildJob to query.

        Returns:
            The BuildJob with current status information.
        """
        return self._validate_job(job_id)

    def list_builds(
        self,
        platform: TargetPlatform = None,
        status: BuildStatus = None,
    ) -> List[BuildJob]:
        """
        List all build jobs, optionally filtered by platform or status.

        Args:
            platform: If set, only return builds for this platform.
            status: If set, only return builds with this status.

        Returns:
            List of matching BuildJob instances.
        """
        with self._lock:
            jobs = list(self._jobs.values())
        if platform is not None:
            jobs = [j for j in jobs if j.platform == platform]
        if status is not None:
            jobs = [j for j in jobs if j.status == status]
        return jobs

    def get_stats(self) -> Dict[str, Any]:
        """
        Return aggregate statistics about the deployment orchestrator.

        Provides counts for configurations, jobs, deployments, success/failure
        rates, average build times, and size savings across all builds.

        Returns:
            Dictionary of orchestrator-wide statistics.
        """
        with self._lock:
            total_jobs = self._job_count
            avg_build_time = (
                round(self._total_build_time / max(1, self._completed_jobs), 3)
                if self._completed_jobs > 0
                else 0.0
            )
            success_rate = (
                round(self._completed_jobs / max(1, total_jobs) * 100, 1)
                if total_jobs > 0
                else 0.0
            )

            platform_counts: Dict[str, int] = {}
            status_counts: Dict[str, int] = {}
            total_file_size = 0.0
            for job in self._jobs.values():
                platform_key = job.platform.value
                platform_counts[platform_key] = platform_counts.get(platform_key, 0) + 1
                status_key = job.status.value
                status_counts[status_key] = status_counts.get(status_key, 0) + 1
                if job.status == BuildStatus.COMPLETED:
                    total_file_size += job.file_size

            return {
                "configurations": {
                    "total": self._config_count,
                },
                "jobs": {
                    "total": total_jobs,
                    "active": self._active_jobs,
                    "completed": self._completed_jobs,
                    "failed": self._failed_jobs,
                    "cancelled": self._cancelled_jobs,
                },
                "deployments": {
                    "targets_configured": len(self._targets),
                    "active_targets": sum(
                        1 for t in self._targets.values() if t.status == "active"
                    ),
                },
                "performance": {
                    "success_rate_percent": success_rate,
                    "average_build_time_seconds": avg_build_time,
                    "total_build_time_seconds": round(self._total_build_time, 3),
                    "total_size_saved_mb": round(self._total_size_saved_mb, 2),
                    "total_output_size_mb": round(total_file_size, 2),
                },
                "platform_distribution": platform_counts,
                "status_distribution": status_counts,
            }

    # ------------------------------------------------------------------
    # Target Management
    # ------------------------------------------------------------------

    def register_deployment_target(
        self,
        name: str,
        platform: TargetPlatform,
        store_type: str = "",
        credentials_ref: str = "",
        metadata: Dict[str, Any] = None,
    ) -> DeploymentTarget:
        """
        Register a new deployment target for distributing builds.

        Args:
            name: Human-readable name for this target.
            platform: Platform this target accepts.
            store_type: Type of store (e.g. 'steamworks', 'app_store').
            credentials_ref: Reference to stored credentials.
            metadata: Arbitrary key-value metadata.

        Returns:
            The newly registered DeploymentTarget.
        """
        if store_type and store_type not in STORE_TYPES:
            raise ValueError(
                f"Unknown store type '{store_type}'. "
                f"Valid types: {STORE_TYPES}"
            )
        target = DeploymentTarget(
            name=name,
            platform=platform,
            store_type=store_type or "custom_cdn",
            credentials_ref=credentials_ref,
            metadata=metadata or {},
        )
        with self._lock:
            self._targets[target.target_id] = target
        return target

    def get_deployment_target(self, target_id: str) -> Optional[DeploymentTarget]:
        """Retrieve a deployment target by id."""
        return self._targets.get(target_id)

    def list_deployment_targets(self) -> List[Dict[str, Any]]:
        """List all registered deployment targets as dictionaries."""
        with self._lock:
            return [t.to_dict() for t in self._targets.values()]

    def cancel_build(self, job_id: str) -> BuildJob:
        """
        Cancel a build job that is still in progress.

        Args:
            job_id: The id of the BuildJob to cancel.

        Returns:
            The cancelled BuildJob.

        Raises:
            RuntimeError: If the build is already completed or failed.
        """
        job = self._validate_job(job_id)
        terminal_states = (BuildStatus.COMPLETED, BuildStatus.FAILED, BuildStatus.CANCELLED)
        if job.status in terminal_states:
            raise RuntimeError(
                f"Cannot cancel build in terminal status '{job.status.value}'"
            )
        with self._lock:
            job.status = BuildStatus.CANCELLED
            job.current_step = "Build cancelled by user"
            if job.started_at > 0:
                job.completed_at = time.time()
                job.duration_seconds = round(job.completed_at - job.started_at, 3)
            self._cancelled_jobs += 1
            if self._active_jobs > 0:
                self._active_jobs -= 1
        return job

    # ------------------------------------------------------------------
    # Export / Serialization
    # ------------------------------------------------------------------

    def export_config(self, config_id: str, filepath: str) -> None:
        """
        Export a build configuration to a JSON file.

        Args:
            config_id: The id of the configuration to export.
            filepath: Destination path for the JSON file.
        """
        config = self._validate_config(config_id)
        with open(filepath, "w") as f:
            json.dump(config.to_dict(), f, indent=2)

    def import_config(self, filepath: str) -> BuildConfiguration:
        """
        Import a build configuration from a JSON file.

        Args:
            filepath: Path to the JSON configuration file.

        Returns:
            The imported BuildConfiguration.
        """
        with open(filepath, "r") as f:
            data = json.load(f)

        platform_str = data.get("platform", "web")
        platform = TargetPlatform(platform_str)

        opt_str = data.get("optimization_level", "standard")
        optimization = OptimizationLevel(opt_str)

        res = data.get("target_resolution", {})
        resolution = (res.get("width", 1920), res.get("height", 1080))

        config = BuildConfiguration(
            name=data.get("name", "Imported Config"),
            platform=platform,
            optimization_level=optimization,
            target_resolution=resolution,
            compression=data.get("compression", 6),
            include_assets=data.get("include_assets", []),
            exclude_patterns=data.get("exclude_patterns", []),
            custom_flags=data.get("custom_flags", {}),
        )
        with self._lock:
            self._configs[config.config_id] = config
            self._config_count += 1
        return config

    def export_job_report(self, job_id: str, filepath: str) -> None:
        """
        Export a detailed build job report to a JSON file.

        Args:
            job_id: The id of the build job.
            filepath: Destination path for the JSON report.
        """
        job = self._validate_job(job_id)
        config = self._configs.get(job.config_id)
        report = {
            "job": job.to_dict(),
            "configuration": config.to_dict() if config else None,
        }
        with open(filepath, "w") as f:
            json.dump(report, f, indent=2)


# ---------------------------------------------------------------------------
# Singleton Accessor
# ---------------------------------------------------------------------------

_deployment_orchestrator: Optional[DeploymentOrchestrator] = None
_orchestrator_lock = threading.RLock()


def get_deployment_orchestrator() -> DeploymentOrchestrator:
    """
    Retrieve the singleton DeploymentOrchestrator instance.

    Creates the instance on first call in a thread-safe manner.
    """
    global _deployment_orchestrator
    with _orchestrator_lock:
        if _deployment_orchestrator is None:
            _deployment_orchestrator = DeploymentOrchestrator()
        return _deployment_orchestrator