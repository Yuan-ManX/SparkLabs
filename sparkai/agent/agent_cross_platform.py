"""
SparkLabs Agent - Cross-Platform Adaptation Engine

Intelligent platform-specific game configuration and asset
adaptation for AI-native multi-platform deployment. Analyzes
target platform constraints (screen resolution, input method,
performance budget, storage limits) and generates optimized
configurations, control mappings, and UI layouts for seamless
cross-platform game delivery.

Architecture:
  CrossPlatformEngine
    |-- PlatformProfiler (capability assessment per platform)
    |-- InputAdapter (keyboard/mouse to touch/controller mapping)
    |-- ResolutionScaler (DPI-aware UI and asset scaling)
    |-- PerformanceBudgeter (platform-specific resource limits)
    |-- BuildConfigGenerator (per-platform build configurations)
    |-- PlatformValidator (minimum specs compliance checking)

Platforms:
  - DESKTOP: Windows, macOS, Linux (high perf, keyboard+mouse)
  - MOBILE: iOS, Android (limited perf, touchscreen)
  - WEB: browser-based (variable perf, keyboard+mouse+touch)
  - CONSOLE: PlayStation, Xbox, Switch (fixed perf, controller)
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


class TargetPlatform(Enum):
    DESKTOP_WINDOWS = "desktop_windows"
    DESKTOP_MACOS = "desktop_macos"
    DESKTOP_LINUX = "desktop_linux"
    MOBILE_IOS = "mobile_ios"
    MOBILE_ANDROID = "mobile_android"
    WEB_BROWSER = "web_browser"
    CONSOLE_PLAYSTATION = "console_playstation"
    CONSOLE_XBOX = "console_xbox"
    CONSOLE_SWITCH = "console_switch"


class InputMode(Enum):
    KEYBOARD_MOUSE = "keyboard_mouse"
    TOUCHSCREEN = "touchscreen"
    CONTROLLER = "controller"
    HYBRID = "hybrid"


class ScalingStrategy(Enum):
    FIXED_RESOLUTION = "fixed_resolution"
    PERCENTAGE_BASED = "percentage_based"
    DPI_AWARE = "dpi_aware"
    RESPONSIVE = "responsive"


class PlatformCapability(Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    VARIABLE = "variable"


@dataclass
class PlatformProfile:
    platform: TargetPlatform
    capability: PlatformCapability = PlatformCapability.MEDIUM
    input_mode: InputMode = InputMode.KEYBOARD_MOUSE
    max_resolution: Tuple[int, int] = (1920, 1080)
    target_fps: int = 60
    max_memory_mb: int = 2048
    max_storage_mb: int = 2048
    supports_3d: bool = True
    supports_shaders: bool = True
    supports_multitouch: bool = False
    supports_gamepad: bool = True
    scaling_strategy: ScalingStrategy = ScalingStrategy.DPI_AWARE
    icon_size: int = 64
    font_scale: float = 1.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "platform": self.platform.value,
            "capability": self.capability.value,
            "input": self.input_mode.value,
            "resolution": list(self.max_resolution),
            "target_fps": self.target_fps,
            "max_memory_mb": self.max_memory_mb,
        }


@dataclass
class PlatformBuildConfig:
    config_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    platform: TargetPlatform = TargetPlatform.DESKTOP_WINDOWS
    app_name: str = ""
    bundle_id: str = ""
    version: str = "1.0.0"
    resolution_override: Optional[Tuple[int, int]] = None
    fps_cap: int = 60
    texture_quality: float = 1.0
    audio_quality: float = 1.0
    shadow_enabled: bool = True
    particle_budget: int = 500
    ui_scale: float = 1.0
    features_enabled: Dict[str, bool] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "config_id": self.config_id,
            "platform": self.platform.value,
            "app_name": self.app_name,
            "resolution": list(self.resolution_override) if self.resolution_override else None,
            "fps_cap": self.fps_cap,
            "texture_quality": self.texture_quality,
            "particle_budget": self.particle_budget,
            "ui_scale": self.ui_scale,
        }


@dataclass
class InputMapping:
    mapping_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    platform: TargetPlatform = TargetPlatform.DESKTOP_WINDOWS
    input_mode: InputMode = InputMode.KEYBOARD_MOUSE
    key_bindings: Dict[str, str] = field(default_factory=dict)
    touch_zones: Dict[str, Tuple[float, float, float, float]] = field(default_factory=dict)
    controller_bindings: Dict[str, int] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "mapping_id": self.mapping_id,
            "platform": self.platform.value,
            "mode": self.input_mode.value,
            "key_count": len(self.key_bindings),
            "touch_zone_count": len(self.touch_zones),
            "controller_bindings": len(self.controller_bindings),
        }


DEFAULT_PLATFORM_PROFILES: Dict[TargetPlatform, PlatformProfile] = {
    TargetPlatform.DESKTOP_WINDOWS: PlatformProfile(
        platform=TargetPlatform.DESKTOP_WINDOWS, capability=PlatformCapability.HIGH,
        input_mode=InputMode.KEYBOARD_MOUSE, max_resolution=(3840, 2160), target_fps=144,
        max_memory_mb=8192, max_storage_mb=10240,
    ),
    TargetPlatform.DESKTOP_MACOS: PlatformProfile(
        platform=TargetPlatform.DESKTOP_MACOS, capability=PlatformCapability.HIGH,
        input_mode=InputMode.KEYBOARD_MOUSE, max_resolution=(3840, 2160), target_fps=120,
        max_memory_mb=8192, max_storage_mb=10240,
    ),
    TargetPlatform.MOBILE_IOS: PlatformProfile(
        platform=TargetPlatform.MOBILE_IOS, capability=PlatformCapability.MEDIUM,
        input_mode=InputMode.TOUCHSCREEN, max_resolution=(1170, 2532), target_fps=60,
        max_memory_mb=1024, max_storage_mb=2048, supports_multitouch=True,
        supports_gamepad=False, scaling_strategy=ScalingStrategy.RESPONSIVE,
    ),
    TargetPlatform.MOBILE_ANDROID: PlatformProfile(
        platform=TargetPlatform.MOBILE_ANDROID, capability=PlatformCapability.VARIABLE,
        input_mode=InputMode.TOUCHSCREEN, max_resolution=(1080, 2400), target_fps=60,
        max_memory_mb=512, max_storage_mb=1024, supports_multitouch=True,
        supports_gamepad=False, scaling_strategy=ScalingStrategy.RESPONSIVE,
    ),
    TargetPlatform.WEB_BROWSER: PlatformProfile(
        platform=TargetPlatform.WEB_BROWSER, capability=PlatformCapability.VARIABLE,
        input_mode=InputMode.HYBRID, max_resolution=(1920, 1080), target_fps=60,
        max_memory_mb=512, max_storage_mb=512, scaling_strategy=ScalingStrategy.RESPONSIVE,
    ),
    TargetPlatform.CONSOLE_SWITCH: PlatformProfile(
        platform=TargetPlatform.CONSOLE_SWITCH, capability=PlatformCapability.LOW,
        input_mode=InputMode.CONTROLLER, max_resolution=(1920, 1080), target_fps=30,
        max_memory_mb=3072, max_storage_mb=32768,
    ),
}


class CrossPlatformEngine:
    _instance: Optional[CrossPlatformEngine] = None

    @classmethod
    def get_instance(cls) -> CrossPlatformEngine:
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self):
        self._platform_profiles: Dict[TargetPlatform, PlatformProfile] = dict(DEFAULT_PLATFORM_PROFILES)
        self._build_configs: Dict[str, PlatformBuildConfig] = {}
        self._input_mappings: Dict[str, InputMapping] = {}
        self._total_configs_generated: int = 0

    def get_profile(self, platform: TargetPlatform) -> PlatformProfile:
        return self._platform_profiles.get(platform, DEFAULT_PLATFORM_PROFILES.get(
            TargetPlatform.DESKTOP_WINDOWS, PlatformProfile(platform=TargetPlatform.DESKTOP_WINDOWS)))

    def register_profile(self, profile: PlatformProfile):
        self._platform_profiles[profile.platform] = profile

    def generate_build_config(self, platform: TargetPlatform, app_name: str = "",
                              bundle_id: str = "", version: str = "1.0.0",
                              features: Optional[Dict[str, bool]] = None) -> PlatformBuildConfig:
        profile = self.get_profile(platform)
        config = PlatformBuildConfig(
            platform=platform,
            app_name=app_name,
            bundle_id=bundle_id,
            version=version,
            resolution_override=profile.max_resolution,
            fps_cap=profile.target_fps,
            texture_quality=0.5 if profile.capability == PlatformCapability.LOW else 1.0,
            audio_quality=0.6 if profile.capability == PlatformCapability.LOW else 1.0,
            shadow_enabled=profile.supports_shaders and profile.capability != PlatformCapability.LOW,
            particle_budget=100 if profile.capability == PlatformCapability.LOW else (
                300 if profile.capability == PlatformCapability.MEDIUM else 1000
            ),
            ui_scale=profile.font_scale,
            features_enabled=features or {},
        )
        self._build_configs[config.config_id] = config
        self._total_configs_generated += 1
        return config

    def create_input_mapping(self, platform: TargetPlatform,
                             actions: List[str]) -> InputMapping:
        profile = self.get_profile(platform)
        mapping = InputMapping(platform=platform, input_mode=profile.input_mode)

        if profile.input_mode in (InputMode.KEYBOARD_MOUSE, InputMode.HYBRID):
            default_keys = ["W", "A", "S", "D", "Space", "Shift", "E", "Q", "1", "2", "3", "4"]
            for i, action in enumerate(actions):
                if i < len(default_keys):
                    mapping.key_bindings[action] = default_keys[i]

        if profile.supports_multitouch:
            cols = 3
            for i, action in enumerate(actions[:9]):
                row, col = divmod(i, cols)
                x = col / cols + 0.5 / cols
                y = row / 3.0 + 0.5 / 3.0
                w, h = 0.3, 0.3
                mapping.touch_zones[action] = (x - w/2, y - h/2, w, h)

        if profile.supports_gamepad:
            controller_map = {0: 0, 1: 1, 2: 2, 3: 3, 4: 4, 5: 5, 6: 6, 7: 7}
            for i, action in enumerate(actions[:8]):
                mapping.controller_bindings[action] = i

        self._input_mappings[mapping.mapping_id] = mapping
        return mapping

    def check_compatibility(self, platform: TargetPlatform,
                            requirements: Dict[str, Any]) -> Tuple[bool, List[str]]:
        profile = self.get_profile(platform)
        issues = []

        if requirements.get("min_resolution"):
            req_w, req_h = requirements["min_resolution"]
            plat_w, plat_h = profile.max_resolution
            if plat_w < req_w or plat_h < req_h:
                issues.append(f"Resolution: platform max {plat_w}x{plat_h} < required {req_w}x{req_h}")

        if requirements.get("min_memory_mb", 0) > profile.max_memory_mb:
            issues.append(f"Memory: platform {profile.max_memory_mb}MB < required {requirements['min_memory_mb']}MB")

        if requirements.get("requires_3d") and not profile.supports_3d:
            issues.append("3D rendering not supported on target platform")

        if requirements.get("requires_gamepad") and not profile.supports_gamepad:
            issues.append("Gamepad not supported on target platform")

        return len(issues) == 0, issues

    def list_platforms(self) -> List[Dict[str, Any]]:
        return [pf.to_dict() for pf in self._platform_profiles.values()]

    def get_build_configs(self, platform: Optional[TargetPlatform] = None) -> List[Dict[str, Any]]:
        configs = list(self._build_configs.values())
        if platform:
            configs = [c for c in configs if c.platform == platform]
        return [c.to_dict() for c in configs]

    def get_supported_input_modes(self, platform: TargetPlatform) -> List[str]:
        profile = self.get_profile(platform)
        modes = [profile.input_mode.value]
        if profile.supports_multitouch:
            modes.append(InputMode.TOUCHSCREEN.value)
        if profile.supports_gamepad:
            modes.append(InputMode.CONTROLLER.value)
        return modes

    def get_stats(self) -> Dict[str, Any]:
        return {
            "total_platforms": len(self._platform_profiles),
            "total_configs": self._total_configs_generated,
            "active_configs": len(self._build_configs),
            "input_mappings": len(self._input_mappings),
            "platforms": [pf.value for pf in self._platform_profiles],
            "by_capability": {
                cap.value: sum(1 for p in self._platform_profiles.values() if p.capability == cap)
                for cap in PlatformCapability
            },
        }


def get_cross_platform_engine() -> CrossPlatformEngine:
    return CrossPlatformEngine.get_instance()