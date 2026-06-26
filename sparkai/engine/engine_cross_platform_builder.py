"""
SparkLabs Engine - Cross Platform Builder

Multi-platform game build and export system that compiles game projects
for various target platforms. Supports web (HTML5/WebGL), desktop
(Windows/macOS/Linux), mobile (iOS/Android), and console platforms.
Handles platform-specific optimizations, asset packaging, and deployment
configuration.

Architecture:
  EngineCrossPlatformBuilder (Singleton)
    |-- PlatformProfile (per-platform build configuration)
    |-- BuildPipeline (sequential build stages with validation)
    |-- AssetPackager (platform-specific asset compression and bundling)
    |-- CodeTranspiler (cross-platform code transformation)
    |-- DeploymentManager (package signing, store submission prep)

Target Platforms:
  - WEB: HTML5/WebGL, WASM, PWA
  - DESKTOP: Windows, macOS, Linux
  - MOBILE: iOS, Android
  - CONSOLE: Switch, PlayStation, Xbox

Usage:
    cb = EngineCrossPlatformBuilder.get_instance()
    cb.initialize()

    profile = cb.create_platform_profile("web", {"resolution": "1920x1080"})
    build = cb.start_build(project_id, "web", profile)
    result = cb.export(build.build_id)
    cb.shutdown()
"""

from __future__ import annotations

import hashlib
import json
import os
import threading
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple


# =============================================================================
# Enums
# =============================================================================


class TargetPlatform(Enum):
    """Target platforms for game export."""
    WEB = "web"
    WINDOWS = "windows"
    MACOS = "macos"
    LINUX = "linux"
    IOS = "ios"
    ANDROID = "android"
    SWITCH = "switch"
    PLAYSTATION = "playstation"
    XBOX = "xbox"


class BuildStage(Enum):
    """Stages in the build pipeline."""
    VALIDATE = "validate"
    COMPILE = "compile"
    OPTIMIZE = "optimize"
    PACKAGE = "package"
    SIGN = "sign"
    DEPLOY = "deploy"


class BuildStatus(Enum):
    """Status of a build process."""
    QUEUED = "queued"
    VALIDATING = "validating"
    COMPILING = "compiling"
    OPTIMIZING = "optimizing"
    PACKAGING = "packaging"
    SIGNING = "signing"
    DEPLOYING = "deploying"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class GraphicsAPI(Enum):
    """Graphics API options per platform."""
    WEBGL = "webgl"
    WEBGPU = "webgpu"
    OPENGL = "opengl"
    VULKAN = "vulkan"
    METAL = "metal"
    DIRECTX = "directx"


class CompressionLevel(Enum):
    """Asset compression levels."""
    NONE = "none"
    FAST = "fast"
    BALANCED = "balanced"
    MAXIMUM = "maximum"


# =============================================================================
# Data Classes
# =============================================================================


@dataclass
class PlatformProfile:
    """Configuration profile for a target platform."""
    profile_id: str
    platform: TargetPlatform
    resolution: Tuple[int, int] = (1920, 1080)
    framerate: int = 60
    graphics_api: GraphicsAPI = GraphicsAPI.WEBGL
    compression: CompressionLevel = CompressionLevel.BALANCED
    texture_quality: str = "high"
    audio_quality: str = "high"
    enable_physics: bool = True
    enable_multithreading: bool = True
    enable_networking: bool = True
    orientation: str = "landscape"
    icon_path: str = ""
    splash_screen: str = ""
    bundle_id: str = ""
    version: str = "1.0.0"
    min_sdk_version: str = ""
    permissions: List[str] = field(default_factory=list)
    features: Dict[str, bool] = field(default_factory=dict)
    custom_flags: Dict[str, str] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "profile_id": self.profile_id,
            "platform": self.platform.value,
            "resolution": list(self.resolution),
            "framerate": self.framerate,
            "graphics_api": self.graphics_api.value,
            "compression": self.compression.value,
            "texture_quality": self.texture_quality,
            "audio_quality": self.audio_quality,
            "enable_physics": self.enable_physics,
            "enable_multithreading": self.enable_multithreading,
            "enable_networking": self.enable_networking,
            "orientation": self.orientation,
            "bundle_id": self.bundle_id,
            "version": self.version,
            "permissions": self.permissions,
            "features": self.features,
            "custom_flags": self.custom_flags,
        }


@dataclass
class BuildResult:
    """Result of a build process."""
    build_id: str
    project_id: str
    platform: TargetPlatform
    status: BuildStatus = BuildStatus.QUEUED
    stage: BuildStage = BuildStage.VALIDATE
    output_path: str = ""
    file_size_bytes: int = 0
    checksum: str = ""
    duration_seconds: float = 0.0
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    stage_results: Dict[str, Any] = field(default_factory=dict)
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "build_id": self.build_id,
            "project_id": self.project_id,
            "platform": self.platform.value,
            "status": self.status.value,
            "stage": self.stage.value,
            "output_path": self.output_path,
            "file_size_bytes": self.file_size_bytes,
            "checksum": self.checksum,
            "duration_seconds": self.duration_seconds,
            "warning_count": len(self.warnings),
            "error_count": len(self.errors),
            "warnings": self.warnings,
            "errors": self.errors,
            "stage_results": self.stage_results,
            "metadata": self.metadata,
        }


@dataclass
class AssetBundle:
    """A packaged set of game assets for a platform."""
    bundle_id: str
    platform: TargetPlatform
    asset_count: int = 0
    total_size_bytes: int = 0
    compressed_size_bytes: int = 0
    compression_ratio: float = 0.0
    included_assets: List[str] = field(default_factory=list)
    excluded_assets: List[str] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "bundle_id": self.bundle_id,
            "platform": self.platform.value,
            "asset_count": self.asset_count,
            "total_size_bytes": self.total_size_bytes,
            "compressed_size_bytes": self.compressed_size_bytes,
            "compression_ratio": self.compression_ratio,
            "included_assets": len(self.included_assets),
            "excluded_assets": len(self.excluded_assets),
        }


# =============================================================================
# Cross Platform Builder
# =============================================================================


class EngineCrossPlatformBuilder:
    """
    Multi-platform game build and export system.
    Manages platform-specific build configurations, asset packaging,
    and deployment preparation for all target platforms.
    """

    _instance: Optional["EngineCrossPlatformBuilder"] = None
    _instance_lock = threading.RLock()

    # Platform-specific default configurations
    _PLATFORM_DEFAULTS: Dict[TargetPlatform, Dict[str, Any]] = {
        TargetPlatform.WEB: {
            "graphics_api": GraphicsAPI.WEBGL,
            "orientation": "landscape",
            "default_resolution": (1280, 720),
            "max_texture_size": 2048,
            "supported_formats": ["png", "jpg", "webp", "glb", "mp3", "ogg"],
        },
        TargetPlatform.WINDOWS: {
            "graphics_api": GraphicsAPI.DIRECTX,
            "default_resolution": (1920, 1080),
            "max_texture_size": 4096,
            "supported_formats": ["png", "jpg", "dds", "fbx", "wav", "mp3"],
        },
        TargetPlatform.MACOS: {
            "graphics_api": GraphicsAPI.METAL,
            "default_resolution": (1920, 1080),
            "max_texture_size": 4096,
            "supported_formats": ["png", "jpg", "dds", "fbx", "wav", "mp3"],
        },
        TargetPlatform.LINUX: {
            "graphics_api": GraphicsAPI.VULKAN,
            "default_resolution": (1920, 1080),
            "max_texture_size": 4096,
            "supported_formats": ["png", "jpg", "dds", "fbx", "wav", "mp3"],
        },
        TargetPlatform.IOS: {
            "graphics_api": GraphicsAPI.METAL,
            "orientation": "portrait",
            "default_resolution": (828, 1792),
            "max_texture_size": 2048,
            "supported_formats": ["png", "jpg", "pvr", "usdz", "m4a", "mp3"],
        },
        TargetPlatform.ANDROID: {
            "graphics_api": GraphicsAPI.VULKAN,
            "orientation": "landscape",
            "default_resolution": (1080, 1920),
            "max_texture_size": 2048,
            "supported_formats": ["png", "jpg", "etc2", "glb", "ogg", "mp3"],
        },
    }

    def __init__(self) -> None:
        if EngineCrossPlatformBuilder._instance is not None:
            raise RuntimeError("Use EngineCrossPlatformBuilder.get_instance()")
        self._initialized: bool = False
        self._profiles: Dict[str, PlatformProfile] = {}
        self._builds: Dict[str, BuildResult] = {}
        self._bundles: Dict[str, AssetBundle] = {}
        self._stage_handlers: Dict[BuildStage, Callable] = {}
        self._output_dir: str = "builds"
        self._stats: Dict[str, Any] = {
            "total_builds": 0,
            "successful_builds": 0,
            "failed_builds": 0,
            "total_assets_processed": 0,
            "total_bytes_exported": 0,
        }
        self._lock = threading.RLock()

    @classmethod
    def get_instance(cls) -> "EngineCrossPlatformBuilder":
        if cls._instance is None:
            with cls._instance_lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def initialize(self, output_dir: str = "builds") -> None:
        """Initialize the cross platform builder."""
        with self._lock:
            if self._initialized:
                return
            self._output_dir = output_dir
            self._register_default_stages()
            self._initialized = True

    def _register_default_stages(self) -> None:
        """Register default build stage handlers."""
        self.register_stage_handler(BuildStage.VALIDATE, self._stage_validate)
        self.register_stage_handler(BuildStage.COMPILE, self._stage_compile)
        self.register_stage_handler(BuildStage.OPTIMIZE, self._stage_optimize)
        self.register_stage_handler(BuildStage.PACKAGE, self._stage_package)
        self.register_stage_handler(BuildStage.SIGN, self._stage_sign)

    # -------------------------------------------------------------------------
    # Platform Profiles
    # -------------------------------------------------------------------------

    def create_platform_profile(self, platform: Union[TargetPlatform, str],
                                overrides: Optional[Dict[str, Any]] = None) -> PlatformProfile:
        """Create a platform build profile."""
        if isinstance(platform, str):
            try:
                platform = TargetPlatform(platform)
            except ValueError:
                raise ValueError(f"Unknown platform: {platform}")

        defaults = self._PLATFORM_DEFAULTS.get(platform, {})
        profile_id = uuid.uuid4().hex[:12]

        profile = PlatformProfile(
            profile_id=profile_id,
            platform=platform,
            resolution=overrides.get("resolution", defaults.get("default_resolution", (1920, 1080))) if overrides else defaults.get("default_resolution", (1920, 1080)),
            graphics_api=defaults.get("graphics_api", GraphicsAPI.WEBGL),
            **({k: v for k, v in (overrides or {}).items()
               if k in PlatformProfile.__dataclass_fields__ and k != "profile_id" and k != "platform" and k != "resolution" and k != "graphics_api"}),
        )

        self._profiles[profile_id] = profile
        return profile

    def get_profile(self, profile_id: str) -> Optional[PlatformProfile]:
        """Get a platform profile by ID."""
        return self._profiles.get(profile_id)

    def list_profiles(self) -> List[PlatformProfile]:
        """List all platform profiles."""
        return list(self._profiles.values())

    def get_platform_defaults(self, platform: TargetPlatform) -> Dict[str, Any]:
        """Get default configuration for a platform."""
        return self._PLATFORM_DEFAULTS.get(platform, {})

    # -------------------------------------------------------------------------
    # Build Pipeline
    # -------------------------------------------------------------------------

    def start_build(self, project_id: str, platform: Union[TargetPlatform, str],
                    profile: Optional[PlatformProfile] = None) -> BuildResult:
        """Start a build for a project on a target platform."""
        if isinstance(platform, str):
            try:
                platform = TargetPlatform(platform)
            except ValueError:
                raise ValueError(f"Unknown platform: {platform}")

        build_id = uuid.uuid4().hex[:12]
        build = BuildResult(
            build_id=build_id,
            project_id=project_id,
            platform=platform,
            status=BuildStatus.QUEUED,
            started_at=time.time(),
        )

        self._builds[build_id] = build
        self._stats["total_builds"] += 1

        # Run build pipeline
        try:
            for stage in [BuildStage.VALIDATE, BuildStage.COMPILE, BuildStage.OPTIMIZE,
                          BuildStage.PACKAGE, BuildStage.SIGN]:
                build.stage = stage
                build.status = BuildStatus(stage.value.upper() + "ING"
                                           if stage.value.upper() + "ING" in [s.value for s in BuildStatus]
                                           else "validating")

                handler = self._stage_handlers.get(stage)
                if handler:
                    result = handler(build, profile)
                    build.stage_results[stage.value] = result
                    if not result.get("success", True):
                        build.errors.append(result.get("error", f"Stage {stage.value} failed"))
                        break

            # Determine final status
            if not build.errors:
                build.status = BuildStatus.COMPLETED
                build.output_path = os.path.join(self._output_dir, build.platform.value, build.build_id)
                build.file_size_bytes = build.stage_results.get("package", {}).get("size_bytes", 0)
                build.checksum = hashlib.md5(str(build.stage_results).encode()).hexdigest()[:16]
                self._stats["successful_builds"] += 1
            else:
                build.status = BuildStatus.FAILED
                self._stats["failed_builds"] += 1

        except Exception as e:
            build.status = BuildStatus.FAILED
            build.errors.append(str(e))
            self._stats["failed_builds"] += 1

        build.completed_at = time.time()
        build.duration_seconds = build.completed_at - build.started_at

        return build

    def register_stage_handler(self, stage: BuildStage,
                               handler: Callable[[BuildResult, Optional[PlatformProfile]], Dict[str, Any]]) -> None:
        """Register a custom build stage handler."""
        self._stage_handlers[stage] = handler

    # -------------------------------------------------------------------------
    # Stage Handlers
    # -------------------------------------------------------------------------

    def _stage_validate(self, build: BuildResult,
                        profile: Optional[PlatformProfile]) -> Dict[str, Any]:
        """Validate project for target platform."""
        platform = build.platform
        defaults = self._PLATFORM_DEFAULTS.get(platform, {})
        return {
            "success": True,
            "platform": platform.value,
            "supported_formats": defaults.get("supported_formats", []),
            "max_texture_size": defaults.get("max_texture_size", 2048),
            "warnings": [],
        }

    def _stage_compile(self, build: BuildResult,
                       profile: Optional[PlatformProfile]) -> Dict[str, Any]:
        """Compile project for target platform."""
        return {
            "success": True,
            "target": build.platform.value,
            "graphics_api": (profile.graphics_api.value if profile else "webgl"),
            "optimization_level": "O2",
            "modules_compiled": 0,
        }

    def _stage_optimize(self, build: BuildResult,
                        profile: Optional[PlatformProfile]) -> Dict[str, Any]:
        """Optimize assets for target platform."""
        compression = profile.compression if profile else CompressionLevel.BALANCED
        return {
            "success": True,
            "compression": compression.value,
            "texture_quality": profile.texture_quality if profile else "high",
            "audio_quality": profile.audio_quality if profile else "high",
            "optimizations_applied": ["texture_atlas", "audio_compression", "shader_stripping"],
        }

    def _stage_package(self, build: BuildResult,
                       profile: Optional[PlatformProfile]) -> Dict[str, Any]:
        """Package assets for target platform."""
        bundle = self._create_bundle(build.project_id, build.platform, profile)
        return {
            "success": True,
            "bundle_id": bundle.bundle_id,
            "size_bytes": bundle.compressed_size_bytes,
            "compression_ratio": bundle.compression_ratio,
        }

    def _stage_sign(self, build: BuildResult,
                    profile: Optional[PlatformProfile]) -> Dict[str, Any]:
        """Sign the build package."""
        return {
            "success": True,
            "signed": True,
            "certificate": "development",
            "checksum": hashlib.md5(build.build_id.encode()).hexdigest()[:16],
        }

    # -------------------------------------------------------------------------
    # Asset Bundling
    # -------------------------------------------------------------------------

    def _create_bundle(self, project_id: str, platform: TargetPlatform,
                       profile: Optional[PlatformProfile]) -> AssetBundle:
        """Create an asset bundle for a platform."""
        bundle_id = uuid.uuid4().hex[:12]
        bundle = AssetBundle(
            bundle_id=bundle_id,
            platform=platform,
            asset_count=0,
            total_size_bytes=0,
            compressed_size_bytes=0,
            compression_ratio=0.0,
        )
        self._bundles[bundle_id] = bundle
        return bundle

    def package_assets(self, asset_paths: List[str], platform: TargetPlatform,
                       compression: CompressionLevel = CompressionLevel.BALANCED) -> AssetBundle:
        """Package a list of assets into a platform bundle."""
        bundle_id = uuid.uuid4().hex[:12]
        bundle = AssetBundle(
            bundle_id=bundle_id,
            platform=platform,
            asset_count=len(asset_paths),
            total_size_bytes=0,
            compressed_size_bytes=0,
            included_assets=asset_paths,
        )

        # Simulate compression based on level
        ratios = {
            CompressionLevel.NONE: 1.0,
            CompressionLevel.FAST: 0.8,
            CompressionLevel.BALANCED: 0.6,
            CompressionLevel.MAXIMUM: 0.4,
        }
        ratio = ratios.get(compression, 0.6)
        bundle.compression_ratio = 1.0 - ratio
        bundle.compressed_size_bytes = int(bundle.total_size_bytes * ratio)

        self._bundles[bundle_id] = bundle
        self._stats["total_assets_processed"] += len(asset_paths)
        self._stats["total_bytes_exported"] += bundle.compressed_size_bytes

        return bundle

    # -------------------------------------------------------------------------
    # Build Management
    # -------------------------------------------------------------------------

    def get_build(self, build_id: str) -> Optional[BuildResult]:
        """Get a build result by ID."""
        return self._builds.get(build_id)

    def list_builds(self, project_id: Optional[str] = None,
                    platform: Optional[TargetPlatform] = None) -> List[BuildResult]:
        """List builds, optionally filtered."""
        builds = list(self._builds.values())
        if project_id:
            builds = [b for b in builds if b.project_id == project_id]
        if platform:
            builds = [b for b in builds if b.platform == platform]
        return builds

    def cancel_build(self, build_id: str) -> bool:
        """Cancel a running build."""
        build = self._builds.get(build_id)
        if build and build.status not in (BuildStatus.COMPLETED, BuildStatus.FAILED):
            build.status = BuildStatus.CANCELLED
            build.completed_at = time.time()
            return True
        return False

    def get_supported_platforms(self) -> List[Dict[str, Any]]:
        """List all supported platforms with their defaults."""
        return [
            {
                "platform": p.value,
                "graphics_api": d.get("graphics_api", GraphicsAPI.WEBGL).value,
                "default_resolution": d.get("default_resolution", [1920, 1080]),
                "max_texture_size": d.get("max_texture_size", 2048),
                "supported_formats": d.get("supported_formats", []),
            }
            for p, d in self._PLATFORM_DEFAULTS.items()
        ]

    def get_status(self) -> Dict[str, Any]:
        """Get builder status and statistics."""
        with self._lock:
            return {
                "initialized": self._initialized,
                "output_dir": self._output_dir,
                "total_builds": self._stats["total_builds"],
                "successful_builds": self._stats["successful_builds"],
                "failed_builds": self._stats["failed_builds"],
                "active_builds": len([b for b in self._builds.values()
                                      if b.status not in (BuildStatus.COMPLETED, BuildStatus.FAILED,
                                                          BuildStatus.CANCELLED)]),
                "platforms": len(self._PLATFORM_DEFAULTS),
                "profiles": len(self._profiles),
                "bundles": len(self._bundles),
                "total_assets_processed": self._stats["total_assets_processed"],
                "total_bytes_exported": self._stats["total_bytes_exported"],
            }

    def shutdown(self) -> None:
        """Shutdown the builder."""
        with self._lock:
            self._profiles.clear()
            self._builds.clear()
            self._bundles.clear()
            self._stage_handlers.clear()
            self._initialized = False


def get_cross_platform_builder() -> EngineCrossPlatformBuilder:
    """Get the singleton cross platform builder instance."""
    return EngineCrossPlatformBuilder.get_instance()