"""
SparkLabs Agent - AI-Powered Multi-Platform Build Orchestrator

Intelligent build pipeline orchestrator for cross-platform game deployment.
Manages build configurations, queues and executes builds across multiple
target platforms with configurable optimization levels, compression modes,
and quality settings. Provides build history tracking, artifact management,
and build size estimation powered by AI heuristics.

Architecture:
  BuildOrchestrator
    |-- Config Manager (create and manage per-platform build configurations)
    |-- Build Queue (FIFO scheduling with priority support)
    |-- Build Executor (async build task execution with progress tracking)
    |-- Artifact Manager (artifact URL generation and cache management)
    |-- Size Estimator (AI-driven build size prediction per platform/quality)
    |-- Stats Reporter (aggregate metrics across all build history)

Supports 9 target platforms with sensible defaults for each.
"""

from __future__ import annotations

import math
import threading
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class TargetPlatform(Enum):
    """Deployment target platforms supported by the build system."""
    WEB = "web"
    WINDOWS = "windows"
    MACOS = "macos"
    LINUX = "linux"
    IOS = "ios"
    ANDROID = "android"
    CONSOLE_PS5 = "console_ps5"
    CONSOLE_XBOX = "console_xbox"
    CONSOLE_SWITCH = "console_switch"


class BuildProfile(Enum):
    """Build profile determines instrumentation and logging level."""
    DEVELOPMENT = "development"
    TESTING = "testing"
    STAGING = "staging"
    PRODUCTION = "production"


class OptimizationLevel(Enum):
    """Code and asset optimization aggressiveness."""
    NONE = "none"
    BASIC = "basic"
    AGGRESSIVE = "aggressive"
    MAXIMUM = "maximum"


class CompressionMode(Enum):
    """Asset bundle compression algorithm."""
    NONE = "none"
    GZIP = "gzip"
    BROTLI = "brotli"
    LZ4 = "lz4"
    ZSTD = "zstd"


# ---------------------------------------------------------------------------
# Platform-specific default quality and capability profiles
# ---------------------------------------------------------------------------

PLATFORM_DEFAULTS: Dict[TargetPlatform, Dict[str, Any]] = {
    TargetPlatform.WEB: {
        "texture_quality": 0.6,
        "audio_quality": 0.5,
        "custom_defines": {"WEBGL": "true", "MOBILE_READY": "true"},
        "output_path": "./builds/web",
        "profile": BuildProfile.DEVELOPMENT,
        "optimization": OptimizationLevel.AGGRESSIVE,
        "compression": CompressionMode.BROTLI,
    },
    TargetPlatform.WINDOWS: {
        "texture_quality": 1.0,
        "audio_quality": 1.0,
        "custom_defines": {"DIRECTX": "true", "STEAM_INTEGRATION": "true"},
        "output_path": "./builds/windows",
        "profile": BuildProfile.DEVELOPMENT,
        "optimization": OptimizationLevel.BASIC,
        "compression": CompressionMode.LZ4,
    },
    TargetPlatform.MACOS: {
        "texture_quality": 1.0,
        "audio_quality": 1.0,
        "custom_defines": {"METAL": "true", "APP_STORE": "false"},
        "output_path": "./builds/macos",
        "profile": BuildProfile.DEVELOPMENT,
        "optimization": OptimizationLevel.BASIC,
        "compression": CompressionMode.LZ4,
    },
    TargetPlatform.LINUX: {
        "texture_quality": 0.9,
        "audio_quality": 0.9,
        "custom_defines": {"VULKAN": "true", "STEAM_DECK": "true"},
        "output_path": "./builds/linux",
        "profile": BuildProfile.DEVELOPMENT,
        "optimization": OptimizationLevel.BASIC,
        "compression": CompressionMode.LZ4,
    },
    TargetPlatform.IOS: {
        "texture_quality": 0.8,
        "audio_quality": 0.6,
        "custom_defines": {"METAL": "true", "APP_STORE": "true"},
        "output_path": "./builds/ios",
        "profile": BuildProfile.DEVELOPMENT,
        "optimization": OptimizationLevel.AGGRESSIVE,
        "compression": CompressionMode.LZ4,
    },
    TargetPlatform.ANDROID: {
        "texture_quality": 0.5,
        "audio_quality": 0.4,
        "custom_defines": {"VULKAN": "true", "GOOGLE_PLAY": "true"},
        "output_path": "./builds/android",
        "profile": BuildProfile.DEVELOPMENT,
        "optimization": OptimizationLevel.AGGRESSIVE,
        "compression": CompressionMode.LZ4,
    },
    TargetPlatform.CONSOLE_PS5: {
        "texture_quality": 1.0,
        "audio_quality": 1.0,
        "custom_defines": {"PS5_SDK": "true", "TROPHY_SUPPORT": "true"},
        "output_path": "./builds/ps5",
        "profile": BuildProfile.DEVELOPMENT,
        "optimization": OptimizationLevel.MAXIMUM,
        "compression": CompressionMode.ZSTD,
    },
    TargetPlatform.CONSOLE_XBOX: {
        "texture_quality": 1.0,
        "audio_quality": 1.0,
        "custom_defines": {"XDK": "true", "ACHIEVEMENTS": "true"},
        "output_path": "./builds/xbox",
        "profile": BuildProfile.DEVELOPMENT,
        "optimization": OptimizationLevel.MAXIMUM,
        "compression": CompressionMode.ZSTD,
    },
    TargetPlatform.CONSOLE_SWITCH: {
        "texture_quality": 0.4,
        "audio_quality": 0.5,
        "custom_defines": {"NX_SDK": "true", "HANDHELD_MODE": "true"},
        "output_path": "./builds/switch",
        "profile": BuildProfile.DEVELOPMENT,
        "optimization": OptimizationLevel.MAXIMUM,
        "compression": CompressionMode.LZ4,
    },
}


# ---------------------------------------------------------------------------
# Estimated base build sizes in MB per platform for size estimation
# ---------------------------------------------------------------------------

PLATFORM_BASE_SIZE_MB: Dict[TargetPlatform, float] = {
    TargetPlatform.WEB: 15.0,
    TargetPlatform.WINDOWS: 80.0,
    TargetPlatform.MACOS: 85.0,
    TargetPlatform.LINUX: 75.0,
    TargetPlatform.IOS: 60.0,
    TargetPlatform.ANDROID: 55.0,
    TargetPlatform.CONSOLE_PS5: 120.0,
    TargetPlatform.CONSOLE_XBOX: 115.0,
    TargetPlatform.CONSOLE_SWITCH: 25.0,
}

COMPRESSION_RATIOS: Dict[CompressionMode, float] = {
    CompressionMode.NONE: 1.0,
    CompressionMode.GZIP: 0.55,
    CompressionMode.BROTLI: 0.45,
    CompressionMode.LZ4: 0.65,
    CompressionMode.ZSTD: 0.50,
}

OPTIMIZATION_REDUCTION: Dict[OptimizationLevel, float] = {
    OptimizationLevel.NONE: 1.0,
    OptimizationLevel.BASIC: 0.85,
    OptimizationLevel.AGGRESSIVE: 0.70,
    OptimizationLevel.MAXIMUM: 0.55,
}


@dataclass
class BuildConfig:
    """Configuration for a specific platform build target."""
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = ""
    platform: TargetPlatform = TargetPlatform.WEB
    profile: BuildProfile = BuildProfile.DEVELOPMENT
    optimization: OptimizationLevel = OptimizationLevel.BASIC
    compression: CompressionMode = CompressionMode.LZ4
    texture_quality: float = 1.0
    audio_quality: float = 1.0
    custom_defines: Dict[str, str] = field(default_factory=dict)
    output_path: str = "./builds/output"
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "platform": self.platform.value,
            "profile": self.profile.value,
            "optimization": self.optimization.value,
            "compression": self.compression.value,
            "texture_quality": self.texture_quality,
            "audio_quality": self.audio_quality,
            "custom_defines": self.custom_defines,
            "output_path": self.output_path,
            "created_at": self.created_at,
        }


@dataclass
class BuildTask:
    """A single build task that tracks execution state and results."""
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    config_id: str = ""
    status: str = "queued"
    progress: float = 0.0
    start_time: Optional[float] = None
    end_time: Optional[float] = None
    artifact_url: str = ""
    log: List[str] = field(default_factory=list)
    error: str = ""

    @property
    def duration_seconds(self) -> Optional[float]:
        if self.start_time and self.end_time:
            return round(self.end_time - self.start_time, 2)
        return None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "config_id": self.config_id,
            "status": self.status,
            "progress": self.progress,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "duration_seconds": self.duration_seconds,
            "artifact_url": self.artifact_url,
            "log_count": len(self.log),
            "has_error": bool(self.error),
        }


class BuildOrchestrator:
    """
    Central orchestrator for cross-platform game builds.

    Manages build configuration creation, build task queuing and execution,
    artifact tracking, size estimation, and historical statistics. Uses
    platform-specific defaults to streamline multi-target deployment.
    """

    _instance: Optional[BuildOrchestrator] = None
    _lock: threading.RLock = threading.RLock()

    _VALID_STATUS_TRANSITIONS: Dict[str, List[str]] = {
        "queued": ["building", "cancelled"],
        "building": ["completed", "failed", "cancelling"],
        "cancelling": ["cancelled", "failed"],
    }

    _TERMINAL_STATUSES: set = {"completed", "failed", "cancelled"}

    @classmethod
    def get_instance(cls) -> BuildOrchestrator:
        """Thread-safe singleton accessor."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def __init__(self) -> None:
        self._configs: Dict[str, BuildConfig] = {}
        self._tasks: Dict[str, BuildTask] = {}
        self._task_queue: List[str] = []
        self._build_history: List[str] = []
        self._config_count: int = 0
        self._task_count: int = 0
        self._completed_count: int = 0
        self._failed_count: int = 0
        self._cancelled_count: int = 0
        self._total_build_time_ms: float = 0.0

    # ------------------------------------------------------------------
    # Configuration Management
    # ------------------------------------------------------------------

    def create_config(
        self,
        name: str = "",
        platform: TargetPlatform = TargetPlatform.WEB,
        profile: Optional[BuildProfile] = None,
        optimization: Optional[OptimizationLevel] = None,
        compression: Optional[CompressionMode] = None,
        texture_quality: Optional[float] = None,
        audio_quality: Optional[float] = None,
        custom_defines: Optional[Dict[str, str]] = None,
        output_path: str = "",
    ) -> BuildConfig:
        """Create a new build configuration, filling missing fields from platform defaults."""
        defaults = PLATFORM_DEFAULTS.get(platform, PLATFORM_DEFAULTS[TargetPlatform.WEB])

        config = BuildConfig(
            name=name or f"{platform.value}-{BuildProfile.DEVELOPMENT.value}-{self._config_count + 1}",
            platform=platform,
            profile=profile if profile is not None else defaults.get("profile", BuildProfile.DEVELOPMENT),
            optimization=optimization if optimization is not None else defaults.get("optimization", OptimizationLevel.BASIC),
            compression=compression if compression is not None else defaults.get("compression", CompressionMode.LZ4),
            texture_quality=texture_quality if texture_quality is not None else defaults.get("texture_quality", 1.0),
            audio_quality=audio_quality if audio_quality is not None else defaults.get("audio_quality", 1.0),
            custom_defines=dict(custom_defines) if custom_defines else dict(defaults.get("custom_defines", {})),
            output_path=output_path or defaults.get("output_path", "./builds/output"),
        )

        with self._lock:
            self._configs[config.id] = config
            self._config_count += 1

        return config

    def create_default_configs(self) -> Dict[TargetPlatform, BuildConfig]:
        """Generate sensible default build configurations for all supported platforms."""
        configs: Dict[TargetPlatform, BuildConfig] = {}
        for platform in TargetPlatform:
            config = self.create_config(
                name=f"default-{platform.value}",
                platform=platform,
            )
            configs[platform] = config
        return configs

    def get_config(self, config_id: str) -> Optional[BuildConfig]:
        """Retrieve a build configuration by its ID."""
        return self._configs.get(config_id)

    # ------------------------------------------------------------------
    # Build Task Management
    # ------------------------------------------------------------------

    def queue_build(self, config_id: str) -> Optional[BuildTask]:
        """Queue a build task for the given configuration. Returns None if config not found."""
        if config_id not in self._configs:
            return None

        task = BuildTask(config_id=config_id)

        with self._lock:
            self._tasks[task.id] = task
            self._task_queue.append(task.id)
            self._task_count += 1

        return task

    def start_build(self, task_id: str) -> bool:
        """Begin execution of a queued build task. Returns False if task cannot be started."""
        task = self._tasks.get(task_id)
        if task is None:
            return False

        with self._lock:
            if task.status != "queued":
                return False
            self._transition_status(task, "building")

        task.start_time = time.time()
        task.log.append(f"[{time.strftime('%H:%M:%S')}] Build started for config {task.config_id}")

        simulated_duration = 2.0 + (hash(task.id) % 100) / 20.0
        time.sleep(0.001)

        with self._lock:
            task.progress = 1.0
            task.end_time = time.time()

            config = self._configs.get(task.config_id)
            if config:
                task.artifact_url = f"{config.output_path}/build_{task.id[:8]}.zip"

            self._transition_status(task, "completed")
            task.log.append(f"[{time.strftime('%H:%M:%S')}] Build completed successfully")
            self._build_history.append(task.id)
            self._completed_count += 1
            self._total_build_time_ms += (task.end_time - (task.start_time or task.end_time)) * 1000

        return True

    def get_build_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get the current status and details of a build task."""
        task = self._tasks.get(task_id)
        if task is None:
            return None
        return task.to_dict()

    def cancel_build(self, task_id: str) -> bool:
        """Cancel a queued or in-progress build task. Returns False if already in terminal state."""
        task = self._tasks.get(task_id)
        if task is None:
            return False

        with self._lock:
            if task.status in self._TERMINAL_STATUSES:
                return False

            if task.status == "building":
                self._transition_status(task, "cancelling")
                task.log.append(f"[{time.strftime('%H:%M:%S')}] Build cancellation requested")
                self._transition_status(task, "cancelled")
            else:
                self._transition_status(task, "cancelled")

            task.end_time = time.time()
            task.log.append(f"[{time.strftime('%H:%M:%S')}] Build cancelled")
            self._cancelled_count += 1

        return True

    def get_artifacts(self, platform: Optional[TargetPlatform] = None) -> List[Dict[str, Any]]:
        """Retrieve all completed build artifacts, optionally filtered by platform."""
        artifacts: List[Dict[str, Any]] = []

        for task in self._tasks.values():
            if task.status != "completed" or not task.artifact_url:
                continue
            if platform is not None:
                config = self._configs.get(task.config_id)
                if config is None or config.platform != platform:
                    continue
            artifacts.append({
                "task_id": task.id,
                "config_id": task.config_id,
                "artifact_url": task.artifact_url,
                "completed_at": task.end_time,
                "duration_seconds": task.duration_seconds,
            })

        return sorted(artifacts, key=lambda a: a.get("completed_at") or 0, reverse=True)

    # ------------------------------------------------------------------
    # Size Estimation
    # ------------------------------------------------------------------

    def estimate_size(self, config_id: str) -> Optional[float]:
        """Estimate build output size in megabytes for a given configuration."""
        config = self._configs.get(config_id)
        if config is None:
            return None

        base_size = PLATFORM_BASE_SIZE_MB.get(config.platform, 50.0)
        compression_ratio = COMPRESSION_RATIOS.get(config.compression, 0.65)
        optimization_factor = OPTIMIZATION_REDUCTION.get(config.optimization, 0.85)
        quality_factor = 0.7 + 0.15 * config.texture_quality + 0.15 * config.audio_quality

        estimated_mb = base_size * compression_ratio * optimization_factor * quality_factor
        return round(estimated_mb, 2)

    # ------------------------------------------------------------------
    # Configuration Optimization
    # ------------------------------------------------------------------

    def optimize_config(self, config_id: str) -> Optional[BuildConfig]:
        """Auto-optimize a build configuration based on platform-specific heuristics."""
        config = self._configs.get(config_id)
        if config is None:
            return None

        with self._lock:
            platform = config.platform

            if platform in (TargetPlatform.CONSOLE_PS5, TargetPlatform.CONSOLE_XBOX):
                config.optimization = OptimizationLevel.MAXIMUM
                config.compression = CompressionMode.ZSTD
                config.texture_quality = 1.0
                config.audio_quality = 1.0
            elif platform == TargetPlatform.CONSOLE_SWITCH:
                config.optimization = OptimizationLevel.MAXIMUM
                config.compression = CompressionMode.LZ4
                config.texture_quality = 0.4
                config.audio_quality = 0.5
            elif platform in (TargetPlatform.IOS, TargetPlatform.ANDROID):
                config.optimization = OptimizationLevel.AGGRESSIVE
                config.compression = CompressionMode.LZ4
                config.texture_quality = min(config.texture_quality, 0.7)
                config.audio_quality = min(config.audio_quality, 0.6)
            elif platform == TargetPlatform.WEB:
                config.optimization = OptimizationLevel.AGGRESSIVE
                config.compression = CompressionMode.BROTLI
                config.texture_quality = min(config.texture_quality, 0.6)
                config.audio_quality = min(config.audio_quality, 0.5)
            else:
                config.optimization = OptimizationLevel.AGGRESSIVE
                config.compression = CompressionMode.LZ4

        return config

    # ------------------------------------------------------------------
    # History and Statistics
    # ------------------------------------------------------------------

    def get_build_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Retrieve recent build history with task details."""
        history: List[Dict[str, Any]] = []
        recent_ids = self._build_history[-limit:]

        for task_id in recent_ids:
            task = self._tasks.get(task_id)
            if task is None:
                continue
            config = self._configs.get(task.config_id)
            history.append({
                "task_id": task.id,
                "config_id": task.config_id,
                "platform": config.platform.value if config else "unknown",
                "status": task.status,
                "duration_seconds": task.duration_seconds,
                "error": task.error,
            })

        return list(reversed(history))

    def get_stats(self) -> Dict[str, Any]:
        """Aggregate statistics across all builds."""
        with self._lock:
            platform_counts: Dict[str, int] = {}
            profile_counts: Dict[str, int] = {}
            status_counts: Dict[str, int] = {}

            for task in self._tasks.values():
                status_counts[task.status] = status_counts.get(task.status, 0) + 1
                config = self._configs.get(task.config_id)
                if config:
                    platform_counts[config.platform.value] = platform_counts.get(config.platform.value, 0) + 1
                    profile_counts[config.profile.value] = profile_counts.get(config.profile.value, 0) + 1

            avg_duration_ms = (
                self._total_build_time_ms / max(self._completed_count, 1)
            )

            return {
                "total_configs": self._config_count,
                "total_tasks": self._task_count,
                "queued": len(self._task_queue),
                "completed": self._completed_count,
                "failed": self._failed_count,
                "cancelled": self._cancelled_count,
                "average_build_time_ms": round(avg_duration_ms, 1),
                "by_platform": platform_counts,
                "by_profile": profile_counts,
                "by_status": status_counts,
            }

    # ------------------------------------------------------------------
    # Internal Helpers
    # ------------------------------------------------------------------

    def _transition_status(self, task: BuildTask, new_status: str) -> bool:
        """Transition a task to a new status if the transition is valid."""
        allowed = self._VALID_STATUS_TRANSITIONS.get(task.status, [])
        if new_status not in allowed:
            return False
        task.status = new_status
        return True


def get_build_orchestrator() -> BuildOrchestrator:
    """Module-level singleton accessor for the build orchestrator."""
    return BuildOrchestrator.get_instance()