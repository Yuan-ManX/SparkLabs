"""
SparkAI Engine - Platform Abstraction Layer

Cross-platform abstraction providing unified interfaces for
hardware-accelerated rendering, input handling, audio output,
filesystem access, and display management across desktop,
mobile, and web targets.

Supports automatic backend detection and runtime switching with
consistent API surface regardless of underlying platform.
"""

from __future__ import annotations

import threading
import time as _time_module
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class TargetPlatform(str, Enum):
    WINDOWS = "windows"
    MACOS = "macos"
    LINUX = "linux"
    IOS = "ios"
    ANDROID = "android"
    WEB = "web"
    CONSOLE = "console"


class RenderBackend(str, Enum):
    WEBGL = "webgl"
    WEBGPU = "webgpu"
    METAL = "metal"
    VULKAN = "vulkan"
    DIRECTX = "directx"
    OPENGL = "opengl"
    SOFTWARE = "software"


class InputDevice(str, Enum):
    KEYBOARD = "keyboard"
    MOUSE = "mouse"
    TOUCH = "touch"
    GAMEPAD = "gamepad"
    PEN = "pen"
    MOTION = "motion"
    VOICE = "voice"


class DisplayMode(str, Enum):
    WINDOWED = "windowed"
    FULLSCREEN = "fullscreen"
    BORDERLESS = "borderless"
    EXCLUSIVE_FULLSCREEN = "exclusive_fullscreen"


class AudioBackend(str, Enum):
    WEBAUDIO = "webaudio"
    OPENAL = "openal"
    WASAPI = "wasapi"
    COREAUDIO = "coreaudio"
    PULSEAUDIO = "pulseaudio"
    AAUDIO = "aaudio"


# ---------------------------------------------------------------------------
# Data Classes
# ---------------------------------------------------------------------------

@dataclass
class DisplayConfig:
    """Display configuration for a platform target."""
    config_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    width: int = 1920
    height: int = 1080
    mode: DisplayMode = DisplayMode.WINDOWED
    target_fps: int = 60
    vsync_enabled: bool = True
    render_backend: RenderBackend = RenderBackend.WEBGL
    antialias_level: int = 4
    pixel_ratio: float = 1.0
    clear_color: Tuple[float, float, float, float] = (0.0, 0.0, 0.0, 1.0)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "config_id": self.config_id,
            "width": self.width,
            "height": self.height,
            "mode": self.mode.value,
            "target_fps": self.target_fps,
            "vsync_enabled": self.vsync_enabled,
            "render_backend": self.render_backend.value,
            "antialias_level": self.antialias_level,
            "pixel_ratio": self.pixel_ratio,
            "clear_color": list(self.clear_color),
        }


@dataclass
class PlatformCapabilities:
    """Detected platform capabilities."""
    cap_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    platform: TargetPlatform = TargetPlatform.WEB
    available_render_backends: List[RenderBackend] = field(default_factory=list)
    available_audio_backends: List[AudioBackend] = field(default_factory=list)
    max_texture_size: int = 4096
    max_fps: int = 240
    supports_webgl2: bool = False
    supports_webgpu: bool = False
    supports_multitouch: bool = False
    supports_gamepad: bool = False
    supports_workers: bool = True
    max_vram_mb: int = 2048
    cpu_cores: int = 4
    gpu_vendor: str = ""
    os_version: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "cap_id": self.cap_id,
            "platform": self.platform.value,
            "render_backends": [b.value for b in self.available_render_backends],
            "audio_backends": [b.value for b in self.available_audio_backends],
            "max_texture_size": self.max_texture_size,
            "max_fps": self.max_fps,
            "supports_webgl2": self.supports_webgl2,
            "supports_webgpu": self.supports_webgpu,
            "supports_multitouch": self.supports_multitouch,
            "supports_gamepad": self.supports_gamepad,
            "max_vram_mb": self.max_vram_mb,
            "cpu_cores": self.cpu_cores,
            "gpu_vendor": self.gpu_vendor,
        }


@dataclass
class InputProfile:
    """Input device profile."""
    profile_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    device_type: InputDevice = InputDevice.KEYBOARD
    device_name: str = ""
    is_connected: bool = False
    axis_count: int = 0
    button_count: int = 0
    has_vibration: bool = False
    mapping_id: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "profile_id": self.profile_id,
            "device_type": self.device_type.value,
            "device_name": self.device_name,
            "is_connected": self.is_connected,
            "axis_count": self.axis_count,
            "button_count": self.button_count,
            "has_vibration": self.has_vibration,
        }


# ---------------------------------------------------------------------------
# Platform Layer
# ---------------------------------------------------------------------------

class EnginePlatformLayer:
    """
    Cross-platform abstraction layer.

    Provides unified interfaces for rendering backends, input devices,
    audio systems, filesystem access, and display configuration across
    all target platforms with automatic detection and runtime switching.
    """

    _instance: Optional["EnginePlatformLayer"] = None
    _lock = threading.RLock()

    def __new__(cls) -> "EnginePlatformLayer":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    @classmethod
    def get_instance(cls) -> "EnginePlatformLayer":
        if cls._instance is None:
            cls._instance = cls()
            cls._instance._initialize()
        return cls._instance

    def _initialize(self) -> None:
        if self._initialized:
            return
        self._initialized = True
        self._target_platform: TargetPlatform = TargetPlatform.WEB
        self._display_configs: Dict[str, DisplayConfig] = {}
        self._capabilities: Optional[PlatformCapabilities] = None
        self._input_profiles: Dict[str, InputProfile] = {}
        self._active_render_backend: RenderBackend = RenderBackend.WEBGL
        self._active_audio_backend: AudioBackend = AudioBackend.WEBAUDIO
        self._feature_flags: Dict[str, bool] = {}
        self._total_draw_calls: int = 0
        self._total_triangles: int = 0

    # ------------------------------------------------------------------
    # Platform Detection
    # ------------------------------------------------------------------

    def detect_platform(self) -> TargetPlatform:
        """Detect the current runtime platform."""
        with self._lock:
            import platform
            system = platform.system().lower()
            if system == "darwin":
                self._target_platform = TargetPlatform.MACOS
            elif system == "windows":
                self._target_platform = TargetPlatform.WINDOWS
            elif system == "linux":
                self._target_platform = TargetPlatform.LINUX
            else:
                self._target_platform = TargetPlatform.WEB
            return self._target_platform

    def set_target_platform(self, platform_type: TargetPlatform) -> None:
        """Explicitly set the target platform."""
        with self._lock:
            self._target_platform = platform_type

    def get_capabilities(self) -> PlatformCapabilities:
        """Get detected platform capabilities."""
        with self._lock:
            if self._capabilities is None:
                self._capabilities = self._detect_capabilities()
            return self._capabilities

    def _detect_capabilities(self) -> PlatformCapabilities:
        """Detect the current platform's capabilities."""
        caps = PlatformCapabilities(platform=self._target_platform)

        if self._target_platform == TargetPlatform.WEB:
            caps.available_render_backends = [RenderBackend.WEBGL, RenderBackend.WEBGPU]
            caps.available_audio_backends = [AudioBackend.WEBAUDIO]
            caps.supports_webgl2 = True
            caps.supports_webgpu = True
            caps.supports_multitouch = True
            caps.max_texture_size = 8192
            caps.max_vram_mb = 1024
        elif self._target_platform == TargetPlatform.MACOS:
            caps.available_render_backends = [RenderBackend.METAL, RenderBackend.OPENGL]
            caps.available_audio_backends = [AudioBackend.COREAUDIO]
            caps.supports_gamepad = True
            caps.max_texture_size = 16384
            caps.max_vram_mb = 8192
        elif self._target_platform == TargetPlatform.WINDOWS:
            caps.available_render_backends = [RenderBackend.DIRECTX, RenderBackend.VULKAN, RenderBackend.OPENGL]
            caps.available_audio_backends = [AudioBackend.WASAPI, AudioBackend.OPENAL]
            caps.supports_gamepad = True
            caps.max_texture_size = 16384
        elif self._target_platform == TargetPlatform.LINUX:
            caps.available_render_backends = [RenderBackend.VULKAN, RenderBackend.OPENGL]
            caps.available_audio_backends = [AudioBackend.PULSEAUDIO, AudioBackend.OPENAL]
            caps.supports_gamepad = True
        elif self._target_platform == TargetPlatform.ANDROID:
            caps.available_render_backends = [RenderBackend.VULKAN, RenderBackend.OPENGL]
            caps.available_audio_backends = [AudioBackend.AAUDIO, AudioBackend.OPENAL]
            caps.supports_multitouch = True
            caps.max_texture_size = 4096

        caps.cpu_cores = 4  # Default estimate
        return caps

    # ------------------------------------------------------------------
    # Display Configuration
    # ------------------------------------------------------------------

    def create_display_config(
        self, width: int = 1920, height: int = 1080,
        mode: DisplayMode = DisplayMode.WINDOWED,
        target_fps: int = 60, vsync: bool = True,
        render_backend: Optional[RenderBackend] = None,
        antialias: int = 4,
    ) -> DisplayConfig:
        """Create a display configuration."""
        with self._lock:
            backend = render_backend or self._active_render_backend
            config = DisplayConfig(
                width=width, height=height,
                mode=mode, target_fps=target_fps,
                vsync_enabled=vsync,
                render_backend=backend,
                antialias_level=antialias,
            )
            self._display_configs[config.config_id] = config
            return config

    def set_active_render_backend(self, backend: RenderBackend) -> bool:
        """Set the active rendering backend."""
        with self._lock:
            caps = self.get_capabilities()
            if backend in caps.available_render_backends:
                self._active_render_backend = backend
                return True
            return False

    def set_active_audio_backend(self, backend: AudioBackend) -> bool:
        """Set the active audio backend."""
        with self._lock:
            caps = self.get_capabilities()
            if backend in caps.available_audio_backends:
                self._active_audio_backend = backend
                return True
            return False

    # ------------------------------------------------------------------
    # Input Management
    # ------------------------------------------------------------------

    def register_input_device(
        self, device_type: InputDevice, device_name: str = "",
        axis_count: int = 0, button_count: int = 0,
        has_vibration: bool = False,
    ) -> InputProfile:
        """Register a connected input device."""
        with self._lock:
            profile = InputProfile(
                device_type=device_type,
                device_name=device_name,
                is_connected=True,
                axis_count=axis_count,
                button_count=button_count,
                has_vibration=has_vibration,
            )
            self._input_profiles[profile.profile_id] = profile
            return profile

    def get_input_devices(
        self, device_type: Optional[InputDevice] = None,
    ) -> List[InputProfile]:
        """Get connected input devices, optionally filtered by type."""
        with self._lock:
            if device_type:
                return [
                    p for p in self._input_profiles.values()
                    if p.device_type == device_type and p.is_connected
                ]
            return [
                p for p in self._input_profiles.values()
                if p.is_connected
            ]

    # ------------------------------------------------------------------
    # Feature Flags
    # ------------------------------------------------------------------

    def set_feature_flag(self, flag: str, enabled: bool) -> None:
        """Set a feature flag."""
        with self._lock:
            self._feature_flags[flag] = enabled

    def is_feature_enabled(self, flag: str) -> bool:
        """Check if a feature flag is enabled."""
        with self._lock:
            return self._feature_flags.get(flag, False)

    # ------------------------------------------------------------------
    # Statistics
    # ------------------------------------------------------------------

    def record_draw_calls(self, calls: int, triangles: int) -> None:
        """Record rendering statistics."""
        with self._lock:
            self._total_draw_calls += calls
            self._total_triangles += triangles

    def get_platform_stats(self) -> Dict[str, Any]:
        """Get comprehensive platform statistics."""
        with self._lock:
            caps = self.get_capabilities()
            return {
                "target_platform": self._target_platform.value,
                "active_render_backend": self._active_render_backend.value,
                "active_audio_backend": self._active_audio_backend.value,
                "capabilities": caps.to_dict(),
                "display_configs": len(self._display_configs),
                "input_devices": len([i for i in self._input_profiles.values() if i.is_connected]),
                "feature_flags": dict(self._feature_flags),
                "total_draw_calls": self._total_draw_calls,
                "total_triangles": self._total_triangles,
            }

    def reset_counters(self) -> None:
        """Reset rendering counters."""
        with self._lock:
            self._total_draw_calls = 0
            self._total_triangles = 0

    def get_backend_compatibility(self) -> Dict[str, Any]:
        """Get render backend compatibility matrix."""
        with self._lock:
            result: Dict[str, Any] = {}
            for platform_type in TargetPlatform:
                caps = PlatformCapabilities(platform=platform_type)
                caps = self._detect_capabilities_for(platform_type)
                result[platform_type.value] = {
                    "render": [b.value for b in caps.available_render_backends],
                    "audio": [b.value for b in caps.available_audio_backends],
                    "max_texture": caps.max_texture_size,
                    "supports_webgpu": caps.supports_webgpu,
                }
            return result

    def _detect_capabilities_for(self, platform_type: TargetPlatform) -> PlatformCapabilities:
        """Detect capabilities for a specific platform."""
        caps = PlatformCapabilities(platform=platform_type)
        if platform_type == TargetPlatform.WEB:
            caps.available_render_backends = [RenderBackend.WEBGL, RenderBackend.WEBGPU]
            caps.available_audio_backends = [AudioBackend.WEBAUDIO]
            caps.supports_webgl2 = True
            caps.supports_webgpu = True
            caps.max_texture_size = 8192
        elif platform_type == TargetPlatform.MACOS:
            caps.available_render_backends = [RenderBackend.METAL, RenderBackend.OPENGL]
            caps.available_audio_backends = [AudioBackend.COREAUDIO]
            caps.max_texture_size = 16384
        elif platform_type == TargetPlatform.WINDOWS:
            caps.available_render_backends = [RenderBackend.DIRECTX, RenderBackend.VULKAN, RenderBackend.OPENGL]
            caps.available_audio_backends = [AudioBackend.WASAPI, AudioBackend.OPENAL]
            caps.max_texture_size = 16384
        elif platform_type == TargetPlatform.LINUX:
            caps.available_render_backends = [RenderBackend.VULKAN, RenderBackend.OPENGL]
            caps.available_audio_backends = [AudioBackend.PULSEAUDIO, AudioBackend.OPENAL]
        elif platform_type == TargetPlatform.ANDROID:
            caps.available_render_backends = [RenderBackend.VULKAN, RenderBackend.OPENGL]
            caps.available_audio_backends = [AudioBackend.AAUDIO, AudioBackend.OPENAL]
            caps.max_texture_size = 4096
        elif platform_type == TargetPlatform.IOS:
            caps.available_render_backends = [RenderBackend.METAL, RenderBackend.OPENGL]
            caps.available_audio_backends = [AudioBackend.COREAUDIO]
        return caps


# ---------------------------------------------------------------------------
# Module-level accessor
# ---------------------------------------------------------------------------

def get_platform_layer() -> EnginePlatformLayer:
    return EnginePlatformLayer.get_instance()