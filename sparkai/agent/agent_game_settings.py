"""
SparkLabs Agent - Game Settings Engine

Intelligent configuration generation and optimization for AI-native
games. Analyzes game design parameters across graphics, audio,
controls, gameplay rules, and accessibility domains to produce
comprehensive settings profiles. Supports preset generation,
conflict detection between interdependent settings, platform-aware
optimization, and accessibility-first configuration suggestions.

Architecture:
  GameSettingsEngine
    |-- GraphicsConfigurator (resolution, quality, post-effects)
    |-- AudioConfigurator (volume, channels, 3D audio settings)
    |-- ControlBinder (input mapping, sensitivity, dead zones)
    |-- GameplayTuner (rule sets, timer settings, scoring configs)
    |-- AccessibilityAdvisor (colorblind modes, subtitles, remapping)
    |-- ConflictResolver (cross-domain dependency validation)

Settings Domains:
  - GRAPHICS: resolution, quality, vsync, anti-aliasing, shadows
  - AUDIO: master/music/sfx volume, surround mode, voice chat
  - CONTROLS: key bindings, sensitivity, invert axis, dead zone
  - GAMEPLAY: difficulty modifiers, timer settings, HUD options
  - ACCESSIBILITY: subtitles, colorblind mode, text scaling, TTS
  - NETWORK: region, max ping, cross-play, voice chat settings
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


class SettingsDomain(Enum):
    GRAPHICS = "graphics"
    AUDIO = "audio"
    CONTROLS = "controls"
    GAMEPLAY = "gameplay"
    ACCESSIBILITY = "accessibility"
    NETWORK = "network"


class QualityPreset(Enum):
    ULTRA = "ultra"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    MINIMUM = "minimum"


class ResolutionPreset(Enum):
    HD_720P = (1280, 720)
    FULL_HD = (1920, 1080)
    QHD = (2560, 1440)
    UHD_4K = (3840, 2160)

    def __new__(cls, width, height):
        obj = object.__new__(cls)
        obj._value_ = f"{width}x{height}"
        obj.width = width
        obj.height = height
        return obj


@dataclass
class SettingDefinition:
    setting_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    domain: SettingsDomain = SettingsDomain.GRAPHICS
    key: str = ""
    label: str = ""
    description: str = ""
    default_value: Any = None
    min_value: Any = None
    max_value: Any = None
    options: List[Any] = field(default_factory=list)
    value_type: str = "float"
    dependencies: List[str] = field(default_factory=list)
    conflicts: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "setting_id": self.setting_id,
            "domain": self.domain.value,
            "key": self.key,
            "label": self.label,
            "default": self.default_value,
            "type": self.value_type,
        }


@dataclass
class SettingsProfile:
    profile_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    name: str = ""
    description: str = ""
    is_default: bool = False
    settings: Dict[str, Any] = field(default_factory=dict)
    platform: str = "desktop"
    quality_preset: QualityPreset = QualityPreset.MEDIUM
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "profile_id": self.profile_id,
            "name": self.name,
            "is_default": self.is_default,
            "settings_count": len(self.settings),
            "quality": self.quality_preset.value,
        }


@dataclass
class SettingsConflict:
    conflict_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    setting_a: str = ""
    setting_b: str = ""
    reason: str = ""
    severity: str = "warning"
    resolution: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "conflict_id": self.conflict_id,
            "settings": [self.setting_a, self.setting_b],
            "reason": self.reason,
            "severity": self.severity,
        }


class GameSettingsEngine:
    _instance: Optional[GameSettingsEngine] = None

    GRAPHICS_DEFAULTS = {
        "resolution_width": 1920, "resolution_height": 1080, "fullscreen": True,
        "vsync": True, "anti_aliasing": 4, "texture_quality": 1.0,
        "shadow_quality": 1.0, "post_processing": True, "render_scale": 1.0,
        "max_fps": 60, "motion_blur": False, "bloom": True,
    }

    AUDIO_DEFAULTS = {
        "master_volume": 1.0, "music_volume": 0.8, "sfx_volume": 1.0,
        "voice_volume": 1.0, "ambient_volume": 0.6, "mute_when_unfocused": True,
        "audio_channels": "stereo", "voice_chat_enabled": False,
    }

    CONTROLS_DEFAULTS = {
        "mouse_sensitivity": 0.5, "invert_y_axis": False,
        "controller_dead_zone": 0.1, "aim_assist": True,
        "key_bindings": {"move_forward": "W", "move_back": "S",
                         "move_left": "A", "move_right": "D",
                         "jump": "Space", "interact": "E"},
    }

    GAMEPLAY_DEFAULTS = {
        "show_tutorials": True, "show_hud": True, "show_minimap": True,
        "show_damage_numbers": True, "auto_save_interval": 300,
        "difficulty": "normal", "language": "en",
    }

    ACCESSIBILITY_DEFAULTS = {
        "subtitles_enabled": True, "subtitle_size": 1.0,
        "colorblind_mode": "none", "text_scaling": 1.0,
        "screen_shake_reduction": 0.0, "high_contrast_mode": False,
        "tts_narration": False, "hold_buttons_instead_of_tap": False,
    }

    NETWORK_DEFAULTS = {
        "region": "auto", "max_ping_ms": 150, "cross_play": True,
        "show_connection_indicator": True, "voice_chat_push_to_talk": True,
    }

    @classmethod
    def get_instance(cls) -> GameSettingsEngine:
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self):
        self._definitions: Dict[str, SettingDefinition] = {}
        self._profiles: Dict[str, SettingsProfile] = {}
        self._conflicts: List[SettingsConflict] = []
        self._total_profiles: int = 0
        self._initialize_definitions()

    def _initialize_definitions(self):
        for domain, defaults in [
            (SettingsDomain.GRAPHICS, self.GRAPHICS_DEFAULTS),
            (SettingsDomain.AUDIO, self.AUDIO_DEFAULTS),
            (SettingsDomain.CONTROLS, self.CONTROLS_DEFAULTS),
            (SettingsDomain.GAMEPLAY, self.GAMEPLAY_DEFAULTS),
            (SettingsDomain.ACCESSIBILITY, self.ACCESSIBILITY_DEFAULTS),
            (SettingsDomain.NETWORK, self.NETWORK_DEFAULTS),
        ]:
            for key, default_val in defaults.items():
                self._register_definition(domain, key, key.replace("_", " ").title(), default_val)

    def _register_definition(self, domain: SettingsDomain, key: str, label: str,
                             default_val: Any, deps: List[str] = None, conflicts: List[str] = None):
        val_type = "bool" if isinstance(default_val, bool) else (
            "int" if isinstance(default_val, int) else (
                "float" if isinstance(default_val, float) else (
                    "string" if isinstance(default_val, str) else "json")))
        definition = SettingDefinition(
            domain=domain, key=key, label=label, description=f"{label} setting",
            default_value=default_val, value_type=val_type,
            dependencies=deps or [], conflicts=conflicts or [],
        )
        self._definitions[definition.setting_id] = definition

    def create_profile(self, name: str, quality: QualityPreset = QualityPreset.MEDIUM,
                       platform: str = "desktop", description: str = "") -> SettingsProfile:
        profile = SettingsProfile(
            name=name,
            description=description,
            quality_preset=quality,
            platform=platform,
        )
        profile.settings = self._generate_platform_defaults(platform, quality)
        self._profiles[profile.profile_id] = profile
        self._total_profiles += 1
        return profile

    def _generate_platform_defaults(self, platform: str, quality: QualityPreset) -> Dict[str, Any]:
        settings = {}
        quality_scale = {"ultra": 1.0, "high": 0.85, "medium": 0.65, "low": 0.4, "minimum": 0.2}.get(
            quality.value, 0.65)

        for domain_defaults in [self.GRAPHICS_DEFAULTS, self.AUDIO_DEFAULTS,
                                 self.CONTROLS_DEFAULTS, self.GAMEPLAY_DEFAULTS,
                                 self.ACCESSIBILITY_DEFAULTS, self.NETWORK_DEFAULTS]:
            for k, v in domain_defaults.items():
                settings[k] = v

        if platform in ("mobile_ios", "mobile_android"):
            settings["resolution_width"] = 1170
            settings["resolution_height"] = 2532
            settings["max_fps"] = 60
            settings["texture_quality"] = quality_scale
            settings["shadow_quality"] = quality_scale * 0.5
            settings["render_scale"] = quality_scale * 0.8
        elif platform == "web_browser":
            settings["max_fps"] = 60
            settings["texture_quality"] = quality_scale * 0.8

        return settings

    def validate_profile(self, profile_id: str) -> List[SettingsConflict]:
        profile = self._profiles.get(profile_id)
        if profile is None:
            return []

        self._conflicts.clear()
        settings = profile.settings

        if settings.get("fullscreen") and settings.get("resolution_width"):
            if settings.get("resolution_width", 1920) > 3840:
                self._conflicts.append(SettingsConflict(
                    setting_a="fullscreen", setting_b="resolution_width",
                    reason="Fullscreen with ultra-wide resolution may cause issues",
                    severity="warning"))

        if settings.get("anti_aliasing", 4) > 4 and settings.get("texture_quality", 1.0) < 0.5:
            self._conflicts.append(SettingsConflict(
                setting_a="anti_aliasing", setting_b="texture_quality",
                reason="High AA with low texture quality provides diminishing returns",
                severity="info"))

        if settings.get("voice_chat_enabled") and not settings.get("voice_chat_push_to_talk"):
            self._conflicts.append(SettingsConflict(
                setting_a="voice_chat_enabled", setting_b="voice_chat_push_to_talk",
                reason="Voice chat enabled without push-to-talk may cause audio issues",
                severity="warning"))

        return list(self._conflicts)

    def update_setting(self, profile_id: str, key: str, value: Any) -> bool:
        profile = self._profiles.get(profile_id)
        if profile is None:
            return False
        profile.settings[key] = value
        return True

    def get_profile(self, profile_id: str) -> Optional[SettingsProfile]:
        return self._profiles.get(profile_id)

    def list_profiles(self) -> List[Dict[str, Any]]:
        return [p.to_dict() for p in self._profiles.values()]

    def get_domain_settings(self, profile_id: str, domain: SettingsDomain) -> Dict[str, Any]:
        profile = self._profiles.get(profile_id)
        if profile is None:
            return {}
        defaults_map = {
            SettingsDomain.GRAPHICS: self.GRAPHICS_DEFAULTS,
            SettingsDomain.AUDIO: self.AUDIO_DEFAULTS,
            SettingsDomain.CONTROLS: self.CONTROLS_DEFAULTS,
            SettingsDomain.GAMEPLAY: self.GAMEPLAY_DEFAULTS,
            SettingsDomain.ACCESSIBILITY: self.ACCESSIBILITY_DEFAULTS,
            SettingsDomain.NETWORK: self.NETWORK_DEFAULTS,
        }
        domain_keys = set(defaults_map.get(domain, {}).keys())
        return {k: v for k, v in profile.settings.items() if k in domain_keys}

    def get_stats(self) -> Dict[str, Any]:
        return {
            "total_profiles": self._total_profiles,
            "active_profiles": len(self._profiles),
            "defined_settings": len(self._definitions),
            "domains": [d.value for d in SettingsDomain],
            "detected_conflicts": len(self._conflicts),
        }


def get_game_settings() -> GameSettingsEngine:
    return GameSettingsEngine.get_instance()