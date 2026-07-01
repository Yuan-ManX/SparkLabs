"""
SparkLabs Engine - Accessibility System Engine

A runtime accessibility system for the SparkLabs AI-native game engine.
It manages per-player accessibility profiles with colorblind modes, subtitle
configuration, input remapping, text scaling, contrast modes, motion
reduction, and audio descriptions. The engine is designed to run alongside
the game loop, allowing settings to be mutated at runtime and validated
against a set of heuristics that catch common misconfigurations.

Architecture:
  AccessibilitySystemEngine (thread-safe singleton)
    |-- AccessibilityProfile     (per-player accessibility configuration)
    |-- AccessibilityPreset      (reusable bundle of accessibility settings)
    |-- SubtitleConfig           (subtitle rendering configuration)
    |-- InputRemap               (single input action remapping record)
    |-- TextScalingConfig        (per-surface text scaling configuration)
    |-- AudioDescription         (audio narration configuration)
    |-- ValidationResult         (output of profile validation)
    |-- ValidationIssue          (single validation finding)
    |-- AccessibilityStats       (aggregate engine statistics)
    |-- AccessibilitySnapshot    (immutable point-in-time state capture)
    |-- AccessibilityEvent       (audit log entry)

Core Capabilities:
  - create_profile: Register a new per-player accessibility profile
  - set_colorblind_mode / set_contrast_mode / set_motion_reduction:
        Toggle visual accessibility modes on a profile
  - set_subtitle_config / set_text_scaling / set_audio_description:
        Fine-tune per-surface accessibility configuration
  - remap_input / remove_input_remap / list_input_remaps:
        Manage input action remappings per profile
  - create_preset / apply_preset: Build and apply reusable setting bundles
  - validate_profile: Run heuristics that detect conflicting settings
  - list_events / get_stats / get_status / get_snapshot: Observability

Thread-safety:
  All public mutators and accessors acquire the engine-wide reentrant lock.
  Use get_accessibility_system() to obtain the singleton instance.
"""

from __future__ import annotations

import threading
import time
import uuid
from collections import deque
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

import datetime as _datetime


# ---------------------------------------------------------------------------
# Capacity Constants
# ---------------------------------------------------------------------------

# Maximum number of accessibility profiles retained by the engine.
_MAX_PROFILES = 10000
# Maximum number of input remaps retained across all profiles.
_MAX_INPUT_REMAPS = 50000
# Maximum number of reusable accessibility presets.
_MAX_PRESETS = 200
# Maximum number of validation results kept for auditing.
_MAX_VALIDATIONS = 5000
# Maximum number of audit events retained in the FIFO event log.
_MAX_EVENTS = 2000


# ---------------------------------------------------------------------------
# Helper Functions
# ---------------------------------------------------------------------------


def _now() -> str:
    """Return the current UTC time as an ISO-8601 string with a 'Z' suffix."""
    return _datetime.datetime.utcnow().isoformat() + "Z"


def _now_epoch() -> float:
    """Return the current time as a Unix epoch float."""
    return time.time()


def _new_id(prefix: str = "") -> str:
    """Generate a short unique identifier, optionally prefixed."""
    base = uuid.uuid4().hex[:12]
    return f"{prefix}_{base}" if prefix else base


def _clamp(value: float, low: float, high: float) -> float:
    """Clamp a numeric value to the inclusive [low, high] range."""
    if value < low:
        return low
    if value > high:
        return high
    return value


# ---------------------------------------------------------------------------
# Domain Enums
# ---------------------------------------------------------------------------


class ColorblindMode(Enum):
    """Color vision deficiency simulation / correction modes."""

    NONE = "none"
    PROTANOPIA = "protanopia"
    DEUTERANOPIA = "deuteranopia"
    TRITANOPIA = "tritanopia"
    ACHROMATOPSIA = "achromatopsia"
    BLUE_CONE_MONOCHROMACY = "blue_cone_monochromacy"


class ContrastMode(Enum):
    """UI contrast presets applied to menus, HUD, and subtitles."""

    NORMAL = "normal"
    HIGH = "high"
    MAXIMUM = "maximum"


class MotionReduction(Enum):
    """Degree to which motion and animation effects are dampened."""

    NONE = "none"
    REDUCED = "reduced"
    MINIMAL = "minimal"


class SubtitleBackground(Enum):
    """Background treatment for rendered subtitle text."""

    SOLID = "solid"
    OUTLINE = "outline"
    TRANSLUCENT = "translucent"
    NONE = "none"


class InputDevice(Enum):
    """Physical or logical input device categories for remapping."""

    KEYBOARD = "keyboard"
    MOUSE = "mouse"
    GAMEPAD = "gamepad"
    TOUCH = "touch"
    MOTION = "motion"


class AccessibilityEventKind(Enum):
    """Audit event kinds emitted by the accessibility engine."""

    PROFILE_CREATED = "profile_created"
    COLORBLIND_SET = "colorblind_set"
    SUBTITLE_CONFIGURED = "subtitle_configured"
    INPUT_REMAPPED = "input_remapped"
    TEXT_SCALED = "text_scaled"
    CONTRAST_SET = "contrast_set"
    MOTION_SET = "motion_set"
    AUDIO_DESC_SET = "audio_desc_set"
    PRESET_APPLIED = "preset_applied"
    VALIDATION_RUN = "validation_run"


class ValidationLevel(Enum):
    """Severity of a single validation finding."""

    OK = "ok"
    WARNING = "warning"
    ERROR = "error"


# ---------------------------------------------------------------------------
# Default Configuration Factories
# ---------------------------------------------------------------------------


def _default_text_scaling() -> "TextScalingConfig":
    """Return a TextScalingConfig with neutral 1.0 scales."""
    return TextScalingConfig(
        ui_scale=1.0,
        subtitle_scale=1.0,
        hud_scale=1.0,
        tooltip_scale=1.0,
        min_scale=0.5,
        max_scale=3.0,
    )


def _default_subtitle_config() -> "SubtitleConfig":
    """Return a SubtitleConfig with sensible defaults (enabled, solid bg)."""
    return SubtitleConfig(
        enabled=True,
        font_size=18.0,
        background=SubtitleBackground.SOLID,
        text_color="#ffffff",
        background_color="#000000",
        position_y=0.15,
        duration_multiplier=1.0,
        speaker_label=True,
        sound_cue_labels=False,
    )


def _default_audio_description() -> "AudioDescription":
    """Return an AudioDescription with narration disabled by default."""
    return AudioDescription(
        enabled=False,
        volume=0.8,
        narration_speed=1.0,
        describe_environment=False,
        describe_actions=False,
        describe_menu=False,
    )


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------


@dataclass
class SubtitleConfig:
    """Configuration for subtitle rendering and presentation."""

    enabled: bool = True
    font_size: float = 18.0
    background: SubtitleBackground = SubtitleBackground.SOLID
    text_color: str = "#ffffff"
    background_color: str = "#000000"
    position_y: float = 0.15
    duration_multiplier: float = 1.0
    speaker_label: bool = True
    sound_cue_labels: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "enabled": self.enabled,
            "font_size": self.font_size,
            "background": self.background.value,
            "text_color": self.text_color,
            "background_color": self.background_color,
            "position_y": self.position_y,
            "duration_multiplier": self.duration_multiplier,
            "speaker_label": self.speaker_label,
            "sound_cue_labels": self.sound_cue_labels,
        }


@dataclass
class InputRemap:
    """A single input remapping entry mapping one action/key to another."""

    remap_id: str = field(default_factory=lambda: _new_id("remap"))
    profile_id: str = ""
    device: InputDevice = InputDevice.KEYBOARD
    source_action: str = ""
    target_action: str = ""
    source_key: str = ""
    target_key: str = ""
    created_at: float = field(default_factory=_now_epoch)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "remap_id": self.remap_id,
            "profile_id": self.profile_id,
            "device": self.device.value,
            "source_action": self.source_action,
            "target_action": self.target_action,
            "source_key": self.source_key,
            "target_key": self.target_key,
            "created_at": self.created_at,
        }


@dataclass
class TextScalingConfig:
    """Per-surface text scaling configuration with min/max bounds."""

    ui_scale: float = 1.0
    subtitle_scale: float = 1.0
    hud_scale: float = 1.0
    tooltip_scale: float = 1.0
    min_scale: float = 0.5
    max_scale: float = 3.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "ui_scale": self.ui_scale,
            "subtitle_scale": self.subtitle_scale,
            "hud_scale": self.hud_scale,
            "tooltip_scale": self.tooltip_scale,
            "min_scale": self.min_scale,
            "max_scale": self.max_scale,
        }


@dataclass
class AudioDescription:
    """Configuration for narrated audio descriptions of on-screen content."""

    enabled: bool = False
    volume: float = 0.8
    narration_speed: float = 1.0
    describe_environment: bool = False
    describe_actions: bool = False
    describe_menu: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "enabled": self.enabled,
            "volume": self.volume,
            "narration_speed": self.narration_speed,
            "describe_environment": self.describe_environment,
            "describe_actions": self.describe_actions,
            "describe_menu": self.describe_menu,
        }


@dataclass
class AccessibilityPreset:
    """A reusable bundle of accessibility settings that can be applied to profiles."""

    preset_id: str = field(default_factory=lambda: _new_id("preset"))
    name: str = ""
    description: str = ""
    colorblind_mode: ColorblindMode = ColorblindMode.NONE
    contrast_mode: ContrastMode = ContrastMode.NORMAL
    motion_reduction: MotionReduction = MotionReduction.NONE
    text_scaling: TextScalingConfig = field(default_factory=_default_text_scaling)
    subtitle_config: SubtitleConfig = field(default_factory=_default_subtitle_config)
    audio_description: AudioDescription = field(default_factory=_default_audio_description)
    created_at: float = field(default_factory=_now_epoch)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "preset_id": self.preset_id,
            "name": self.name,
            "description": self.description,
            "colorblind_mode": self.colorblind_mode.value,
            "contrast_mode": self.contrast_mode.value,
            "motion_reduction": self.motion_reduction.value,
            "text_scaling": self.text_scaling.to_dict(),
            "subtitle_config": self.subtitle_config.to_dict(),
            "audio_description": self.audio_description.to_dict(),
            "created_at": self.created_at,
        }


@dataclass
class AccessibilityProfile:
    """A per-player accessibility configuration record."""

    profile_id: str = field(default_factory=lambda: _new_id("profile"))
    player_id: str = ""
    player_name: str = ""
    colorblind_mode: ColorblindMode = ColorblindMode.NONE
    contrast_mode: ContrastMode = ContrastMode.NORMAL
    motion_reduction: MotionReduction = MotionReduction.NONE
    text_scaling: TextScalingConfig = field(default_factory=_default_text_scaling)
    subtitle_config: SubtitleConfig = field(default_factory=_default_subtitle_config)
    audio_description: AudioDescription = field(default_factory=_default_audio_description)
    input_remaps: List[InputRemap] = field(default_factory=list)
    created_at: float = field(default_factory=_now_epoch)
    updated_at: float = field(default_factory=_now_epoch)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "profile_id": self.profile_id,
            "player_id": self.player_id,
            "player_name": self.player_name,
            "colorblind_mode": self.colorblind_mode.value,
            "contrast_mode": self.contrast_mode.value,
            "motion_reduction": self.motion_reduction.value,
            "text_scaling": self.text_scaling.to_dict(),
            "subtitle_config": self.subtitle_config.to_dict(),
            "audio_description": self.audio_description.to_dict(),
            "input_remaps": [r.to_dict() for r in self.input_remaps],
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "metadata": dict(self.metadata),
        }


@dataclass
class ValidationIssue:
    """A single finding produced by profile validation."""

    level: ValidationLevel = ValidationLevel.OK
    category: str = ""
    message: str = ""
    suggestion: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "level": self.level.value,
            "category": self.category,
            "message": self.message,
            "suggestion": self.suggestion,
        }


@dataclass
class ValidationResult:
    """The result of validating a single accessibility profile."""

    validation_id: str = field(default_factory=lambda: _new_id("val"))
    profile_id: str = ""
    issues: List[ValidationIssue] = field(default_factory=list)
    valid: bool = True
    validated_at: float = field(default_factory=_now_epoch)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "validation_id": self.validation_id,
            "profile_id": self.profile_id,
            "issues": [i.to_dict() for i in self.issues],
            "valid": self.valid,
            "validated_at": self.validated_at,
        }


@dataclass
class AccessibilityStats:
    """Aggregate counters describing accessibility system usage."""

    total_profiles: int = 0
    total_input_remaps: int = 0
    total_presets: int = 0
    total_validations: int = 0
    avg_text_scale: float = 1.0
    colorblind_usage_pct: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_profiles": self.total_profiles,
            "total_input_remaps": self.total_input_remaps,
            "total_presets": self.total_presets,
            "total_validations": self.total_validations,
            "avg_text_scale": self.avg_text_scale,
            "colorblind_usage_pct": self.colorblind_usage_pct,
        }


@dataclass
class AccessibilityEvent:
    """An audit log entry emitted by the accessibility engine."""

    event_id: str = field(default_factory=lambda: _new_id("evt"))
    kind: AccessibilityEventKind = AccessibilityEventKind.PROFILE_CREATED
    timestamp: str = field(default_factory=_now)
    payload: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": self.event_id,
            "kind": self.kind.value,
            "timestamp": self.timestamp,
            "payload": dict(self.payload),
        }


@dataclass
class AccessibilitySnapshot:
    """An immutable snapshot of the accessibility engine's state."""

    initialized: bool = False
    profiles: List[AccessibilityProfile] = field(default_factory=list)
    presets: List[AccessibilityPreset] = field(default_factory=list)
    validations: List[ValidationResult] = field(default_factory=list)
    events: List[AccessibilityEvent] = field(default_factory=list)
    stats: AccessibilityStats = field(default_factory=AccessibilityStats)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "initialized": self.initialized,
            "profiles": [p.to_dict() for p in self.profiles],
            "presets": [p.to_dict() for p in self.presets],
            "validations": [v.to_dict() for v in self.validations],
            "events": [e.to_dict() for e in self.events],
            "stats": self.stats.to_dict(),
        }


# ---------------------------------------------------------------------------
# AccessibilitySystemEngine — Thread-Safe Singleton
# ---------------------------------------------------------------------------


class AccessibilitySystemEngine:
    """
    Central engine for managing per-player accessibility profiles, presets,
    input remaps, and validation within the SparkLabs AI-native game engine.

    Thread-safe via a reentrant lock. Use get_accessibility_system() or
    AccessibilitySystemEngine.get_instance() to obtain the singleton.

    Usage:
        engine = get_accessibility_system()
        profile = engine.create_profile("player_1", "Alice")
        engine.set_colorblind_mode(profile.profile_id, ColorblindMode.DEUTERANOPIA)
        result = engine.validate_profile(profile.profile_id)
    """

    _instance: Optional["AccessibilitySystemEngine"] = None
    _lock: threading.RLock = threading.RLock()

    def __new__(cls) -> "AccessibilitySystemEngine":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    instance = super().__new__(cls)
                    instance._initialized = False
                    cls._instance = instance
        return cls._instance

    def __init__(self) -> None:
        if self._initialized:
            return
        with self._lock:
            if self._initialized:
                return

            # Profiles keyed by profile_id.
            self._profiles: Dict[str, AccessibilityProfile] = {}
            # Input remaps keyed by remap_id (global store for fast lookup).
            self._input_remaps: Dict[str, InputRemap] = {}
            # Presets keyed by preset_id.
            self._presets: Dict[str, AccessibilityPreset] = {}
            # Validation results keyed by validation_id.
            self._validations: Dict[str, ValidationResult] = {}
            # Audit events kept in FIFO order with capacity eviction.
            self._events: deque = deque(maxlen=_MAX_EVENTS)

            # Aggregate counters maintained for fast stats retrieval.
            self._total_profiles_created: int = 0
            self._total_input_remaps_created: int = 0
            self._total_presets_created: int = 0
            self._total_validations_run: int = 0

            self._initialized: bool = True
            self._seed_data()

    @classmethod
    def get_instance(cls) -> "AccessibilitySystemEngine":
        """Return the singleton AccessibilitySystemEngine instance."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    # ------------------------------------------------------------------
    # Seeding
    # ------------------------------------------------------------------

    def _seed_data(self) -> None:
        """Populate the engine with seed presets and demo player profiles."""
        # Preset 1: Default accessibility baseline.
        default_preset = AccessibilityPreset(
            name="Default",
            description="Baseline accessibility settings with no modifications.",
            colorblind_mode=ColorblindMode.NONE,
            contrast_mode=ContrastMode.NORMAL,
            motion_reduction=MotionReduction.NONE,
            text_scaling=TextScalingConfig(
                ui_scale=1.0,
                subtitle_scale=1.0,
                hud_scale=1.0,
                tooltip_scale=1.0,
                min_scale=0.5,
                max_scale=3.0,
            ),
            subtitle_config=SubtitleConfig(
                enabled=True,
                font_size=18.0,
                background=SubtitleBackground.SOLID,
                text_color="#ffffff",
                background_color="#000000",
                position_y=0.15,
                duration_multiplier=1.0,
                speaker_label=True,
                sound_cue_labels=False,
            ),
            audio_description=_default_audio_description(),
        )
        self._presets[default_preset.preset_id] = default_preset
        self._total_presets_created += 1

        # Preset 2: Colorblind friendly with higher contrast.
        colorblind_preset = AccessibilityPreset(
            name="Colorblind Friendly",
            description="Deuteranopia correction with high contrast and outlined subtitles.",
            colorblind_mode=ColorblindMode.DEUTERANOPIA,
            contrast_mode=ContrastMode.HIGH,
            motion_reduction=MotionReduction.NONE,
            text_scaling=TextScalingConfig(
                ui_scale=1.1,
                subtitle_scale=1.1,
                hud_scale=1.1,
                tooltip_scale=1.1,
                min_scale=0.5,
                max_scale=3.0,
            ),
            subtitle_config=SubtitleConfig(
                enabled=True,
                font_size=20.0,
                background=SubtitleBackground.OUTLINE,
                text_color="#ffffff",
                background_color="#000000",
                position_y=0.15,
                duration_multiplier=1.1,
                speaker_label=True,
                sound_cue_labels=True,
            ),
            audio_description=_default_audio_description(),
        )
        self._presets[colorblind_preset.preset_id] = colorblind_preset
        self._total_presets_created += 1

        # Preset 3: Low motion with audio descriptions enabled.
        low_motion_preset = AccessibilityPreset(
            name="Low Motion",
            description="Minimal motion with subtitles and audio descriptions enabled.",
            colorblind_mode=ColorblindMode.NONE,
            contrast_mode=ContrastMode.NORMAL,
            motion_reduction=MotionReduction.MINIMAL,
            text_scaling=TextScalingConfig(
                ui_scale=1.15,
                subtitle_scale=1.15,
                hud_scale=1.15,
                tooltip_scale=1.15,
                min_scale=0.5,
                max_scale=3.0,
            ),
            subtitle_config=SubtitleConfig(
                enabled=True,
                font_size=18.0,
                background=SubtitleBackground.SOLID,
                text_color="#ffffff",
                background_color="#000000",
                position_y=0.15,
                duration_multiplier=1.0,
                speaker_label=True,
                sound_cue_labels=True,
            ),
            audio_description=AudioDescription(
                enabled=True,
                volume=0.9,
                narration_speed=1.0,
                describe_environment=True,
                describe_actions=True,
                describe_menu=True,
            ),
        )
        self._presets[low_motion_preset.preset_id] = low_motion_preset
        self._total_presets_created += 1

        # Profile 1: player_alpha with default settings and two input remaps.
        alpha = AccessibilityProfile(
            player_id="player_alpha",
            player_name="Alpha",
            colorblind_mode=ColorblindMode.NONE,
            contrast_mode=ContrastMode.NORMAL,
            motion_reduction=MotionReduction.NONE,
            text_scaling=_default_text_scaling(),
            subtitle_config=_default_subtitle_config(),
            audio_description=_default_audio_description(),
        )
        self._profiles[alpha.profile_id] = alpha
        self._total_profiles_created += 1

        alpha_remap_1 = InputRemap(
            profile_id=alpha.profile_id,
            device=InputDevice.KEYBOARD,
            source_action="jump",
            target_action="dash",
            source_key="space",
            target_key="shift",
        )
        alpha.input_remaps.append(alpha_remap_1)
        self._input_remaps[alpha_remap_1.remap_id] = alpha_remap_1
        self._total_input_remaps_created += 1

        alpha_remap_2 = InputRemap(
            profile_id=alpha.profile_id,
            device=InputDevice.GAMEPAD,
            source_action="fire",
            target_action="aim",
            source_key="RT",
            target_key="LT",
        )
        alpha.input_remaps.append(alpha_remap_2)
        self._input_remaps[alpha_remap_2.remap_id] = alpha_remap_2
        self._total_input_remaps_created += 1

        self._record_event(
            AccessibilityEventKind.PROFILE_CREATED,
            {
                "profile_id": alpha.profile_id,
                "player_id": alpha.player_id,
                "player_name": alpha.player_name,
            },
        )
        self._record_event(
            AccessibilityEventKind.INPUT_REMAPPED,
            {
                "profile_id": alpha.profile_id,
                "remap_id": alpha_remap_1.remap_id,
                "device": alpha_remap_1.device.value,
            },
        )
        self._record_event(
            AccessibilityEventKind.INPUT_REMAPPED,
            {
                "profile_id": alpha.profile_id,
                "remap_id": alpha_remap_2.remap_id,
                "device": alpha_remap_2.device.value,
            },
        )

        # Profile 2: player_beta with deuteranopia, high contrast, larger text.
        beta = AccessibilityProfile(
            player_id="player_beta",
            player_name="Beta",
            colorblind_mode=ColorblindMode.DEUTERANOPIA,
            contrast_mode=ContrastMode.HIGH,
            motion_reduction=MotionReduction.NONE,
            text_scaling=TextScalingConfig(
                ui_scale=1.2,
                subtitle_scale=1.2,
                hud_scale=1.2,
                tooltip_scale=1.2,
                min_scale=0.5,
                max_scale=3.0,
            ),
            subtitle_config=SubtitleConfig(
                enabled=True,
                font_size=20.0,
                background=SubtitleBackground.OUTLINE,
                text_color="#ffffff",
                background_color="#000000",
                position_y=0.15,
                duration_multiplier=1.1,
                speaker_label=True,
                sound_cue_labels=True,
            ),
            audio_description=_default_audio_description(),
        )
        self._profiles[beta.profile_id] = beta
        self._total_profiles_created += 1

        self._record_event(
            AccessibilityEventKind.PROFILE_CREATED,
            {
                "profile_id": beta.profile_id,
                "player_id": beta.player_id,
                "player_name": beta.player_name,
            },
        )
        self._record_event(
            AccessibilityEventKind.COLORBLIND_SET,
            {
                "profile_id": beta.profile_id,
                "mode": beta.colorblind_mode.value,
            },
        )

    # ------------------------------------------------------------------
    # Internal Helpers
    # ------------------------------------------------------------------

    def _evict_oldest_profile(self) -> None:
        """Evict the oldest profile when the profile store is full (caller holds lock)."""
        if len(self._profiles) < _MAX_PROFILES:
            return
        oldest_id = next(iter(self._profiles), None)
        if oldest_id is None:
            return
        profile = self._profiles.pop(oldest_id)
        # Remove any remaps that belong to the evicted profile.
        for remap in profile.input_remaps:
            self._input_remaps.pop(remap.remap_id, None)

    def _evict_oldest_input_remap(self) -> None:
        """Evict the oldest input remap when the remap store is full (caller holds lock)."""
        if len(self._input_remaps) < _MAX_INPUT_REMAPS:
            return
        oldest_id = next(iter(self._input_remaps), None)
        if oldest_id is None:
            return
        remap = self._input_remaps.pop(oldest_id)
        # Detach the remap from its owning profile.
        profile = self._profiles.get(remap.profile_id)
        if profile is not None:
            profile.input_remaps = [
                r for r in profile.input_remaps if r.remap_id != oldest_id
            ]

    def _evict_oldest_preset(self) -> None:
        """Evict the oldest preset when the preset store is full (caller holds lock)."""
        if len(self._presets) < _MAX_PRESETS:
            return
        oldest_id = next(iter(self._presets), None)
        if oldest_id is None:
            return
        self._presets.pop(oldest_id, None)

    def _evict_oldest_validation(self) -> None:
        """Evict the oldest validation result when the store is full (caller holds lock)."""
        if len(self._validations) < _MAX_VALIDATIONS:
            return
        oldest_id = next(iter(self._validations), None)
        if oldest_id is None:
            return
        self._validations.pop(oldest_id, None)

    def _touch(self, profile: AccessibilityProfile) -> None:
        """Update the updated_at timestamp on a profile (caller holds lock)."""
        profile.updated_at = _now_epoch()

    def _record_event(
        self,
        kind: AccessibilityEventKind,
        payload: Dict[str, Any],
    ) -> AccessibilityEvent:
        """Record an audit event (caller must hold self._lock)."""
        event = AccessibilityEvent(
            kind=kind,
            payload=dict(payload) if payload else {},
        )
        self._events.append(event)
        return event

    # ------------------------------------------------------------------
    # Profile Management
    # ------------------------------------------------------------------

    def create_profile(
        self,
        player_id: str,
        player_name: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> AccessibilityProfile:
        """Create and register a new accessibility profile with default settings."""
        with self._lock:
            self._evict_oldest_profile()
            profile = AccessibilityProfile(
                player_id=player_id,
                player_name=player_name,
                colorblind_mode=ColorblindMode.NONE,
                contrast_mode=ContrastMode.NORMAL,
                motion_reduction=MotionReduction.NONE,
                text_scaling=_default_text_scaling(),
                subtitle_config=_default_subtitle_config(),
                audio_description=_default_audio_description(),
                metadata=dict(metadata) if metadata else {},
            )
            self._profiles[profile.profile_id] = profile
            self._total_profiles_created += 1
            self._record_event(
                AccessibilityEventKind.PROFILE_CREATED,
                {
                    "profile_id": profile.profile_id,
                    "player_id": profile.player_id,
                    "player_name": profile.player_name,
                },
            )
            return profile

    def get_profile(self, profile_id: str) -> Optional[AccessibilityProfile]:
        """Retrieve an accessibility profile by its id."""
        with self._lock:
            return self._profiles.get(profile_id)

    def get_profile_by_player(self, player_id: str) -> Optional[AccessibilityProfile]:
        """Retrieve the first accessibility profile matching a player id."""
        with self._lock:
            for profile in self._profiles.values():
                if profile.player_id == player_id:
                    return profile
            return None

    def list_profiles(self) -> List[AccessibilityProfile]:
        """Return all registered accessibility profiles."""
        with self._lock:
            return list(self._profiles.values())

    # ------------------------------------------------------------------
    # Visual Accessibility Modes
    # ------------------------------------------------------------------

    def set_colorblind_mode(
        self,
        profile_id: str,
        mode: ColorblindMode,
    ) -> Optional[AccessibilityProfile]:
        """Set the colorblind mode on a profile and emit a COLORBLIND_SET event."""
        with self._lock:
            profile = self._profiles.get(profile_id)
            if profile is None:
                return None
            profile.colorblind_mode = mode
            self._touch(profile)
            self._record_event(
                AccessibilityEventKind.COLORBLIND_SET,
                {
                    "profile_id": profile.profile_id,
                    "mode": mode.value,
                },
            )
            return profile

    def set_contrast_mode(
        self,
        profile_id: str,
        mode: ContrastMode,
    ) -> Optional[AccessibilityProfile]:
        """Set the contrast mode on a profile and emit a CONTRAST_SET event."""
        with self._lock:
            profile = self._profiles.get(profile_id)
            if profile is None:
                return None
            profile.contrast_mode = mode
            self._touch(profile)
            self._record_event(
                AccessibilityEventKind.CONTRAST_SET,
                {
                    "profile_id": profile.profile_id,
                    "mode": mode.value,
                },
            )
            return profile

    def set_motion_reduction(
        self,
        profile_id: str,
        reduction: MotionReduction,
    ) -> Optional[AccessibilityProfile]:
        """Set the motion reduction level on a profile and emit a MOTION_SET event."""
        with self._lock:
            profile = self._profiles.get(profile_id)
            if profile is None:
                return None
            profile.motion_reduction = reduction
            self._touch(profile)
            self._record_event(
                AccessibilityEventKind.MOTION_SET,
                {
                    "profile_id": profile.profile_id,
                    "reduction": reduction.value,
                },
            )
            return profile

    # ------------------------------------------------------------------
    # Subtitle Configuration
    # ------------------------------------------------------------------

    def set_subtitle_config(
        self,
        profile_id: str,
        **kwargs: Any,
    ) -> Optional[AccessibilityProfile]:
        """Update subtitle config fields on a profile via keyword arguments.

        Accepts any subset of SubtitleConfig field names (e.g. enabled,
        font_size, background, text_color, background_color, position_y,
        duration_multiplier, speaker_label, sound_cue_labels).
        """
        with self._lock:
            profile = self._profiles.get(profile_id)
            if profile is None:
                return None
            config = profile.subtitle_config
            for key, value in kwargs.items():
                if hasattr(config, key):
                    setattr(config, key, value)
            self._touch(profile)
            self._record_event(
                AccessibilityEventKind.SUBTITLE_CONFIGURED,
                {
                    "profile_id": profile.profile_id,
                    "fields": list(kwargs.keys()),
                },
            )
            return profile

    # ------------------------------------------------------------------
    # Text Scaling
    # ------------------------------------------------------------------

    def set_text_scaling(
        self,
        profile_id: str,
        **kwargs: Any,
    ) -> Optional[AccessibilityProfile]:
        """Update text scaling fields on a profile, clamping scales to [min, max].

        Accepts any subset of TextScalingConfig field names (e.g. ui_scale,
        subtitle_scale, hud_scale, tooltip_scale, min_scale, max_scale).
        Scale values are clamped to the resulting [min_scale, max_scale] range.
        """
        with self._lock:
            profile = self._profiles.get(profile_id)
            if profile is None:
                return None
            config = profile.text_scaling
            for key, value in kwargs.items():
                if hasattr(config, key):
                    setattr(config, key, value)
            # Re-clamp the per-surface scales to the resulting bounds.
            low = config.min_scale
            high = config.max_scale
            config.ui_scale = _clamp(config.ui_scale, low, high)
            config.subtitle_scale = _clamp(config.subtitle_scale, low, high)
            config.hud_scale = _clamp(config.hud_scale, low, high)
            config.tooltip_scale = _clamp(config.tooltip_scale, low, high)
            self._touch(profile)
            self._record_event(
                AccessibilityEventKind.TEXT_SCALED,
                {
                    "profile_id": profile.profile_id,
                    "ui_scale": config.ui_scale,
                    "subtitle_scale": config.subtitle_scale,
                    "hud_scale": config.hud_scale,
                    "tooltip_scale": config.tooltip_scale,
                },
            )
            return profile

    # ------------------------------------------------------------------
    # Audio Description
    # ------------------------------------------------------------------

    def set_audio_description(
        self,
        profile_id: str,
        **kwargs: Any,
    ) -> Optional[AccessibilityProfile]:
        """Update audio description fields on a profile via keyword arguments.

        Accepts any subset of AudioDescription field names (e.g. enabled,
        volume, narration_speed, describe_environment, describe_actions,
        describe_menu).
        """
        with self._lock:
            profile = self._profiles.get(profile_id)
            if profile is None:
                return None
            config = profile.audio_description
            for key, value in kwargs.items():
                if hasattr(config, key):
                    setattr(config, key, value)
            self._touch(profile)
            self._record_event(
                AccessibilityEventKind.AUDIO_DESC_SET,
                {
                    "profile_id": profile.profile_id,
                    "enabled": config.enabled,
                },
            )
            return profile

    # ------------------------------------------------------------------
    # Input Remapping
    # ------------------------------------------------------------------

    def remap_input(
        self,
        profile_id: str,
        device: InputDevice,
        source_action: str,
        target_action: str,
        source_key: str,
        target_key: str,
    ) -> InputRemap:
        """Create an input remap and attach it to a profile.

        Raises KeyError if the profile does not exist.
        """
        with self._lock:
            profile = self._profiles.get(profile_id)
            if profile is None:
                raise KeyError(f"Profile not found: {profile_id}")
            self._evict_oldest_input_remap()
            remap = InputRemap(
                profile_id=profile_id,
                device=device,
                source_action=source_action,
                target_action=target_action,
                source_key=source_key,
                target_key=target_key,
            )
            profile.input_remaps.append(remap)
            self._input_remaps[remap.remap_id] = remap
            self._total_input_remaps_created += 1
            self._touch(profile)
            self._record_event(
                AccessibilityEventKind.INPUT_REMAPPED,
                {
                    "profile_id": profile_id,
                    "remap_id": remap.remap_id,
                    "device": device.value,
                    "source_action": source_action,
                    "target_action": target_action,
                },
            )
            return remap

    def list_input_remaps(self, profile_id: str) -> List[InputRemap]:
        """Return all input remaps attached to a profile."""
        with self._lock:
            profile = self._profiles.get(profile_id)
            if profile is None:
                return []
            return list(profile.input_remaps)

    def remove_input_remap(self, profile_id: str, remap_id: str) -> bool:
        """Remove an input remap from a profile. Returns True if removed."""
        with self._lock:
            profile = self._profiles.get(profile_id)
            if profile is None:
                return False
            for index, remap in enumerate(profile.input_remaps):
                if remap.remap_id == remap_id:
                    profile.input_remaps.pop(index)
                    self._input_remaps.pop(remap_id, None)
                    self._touch(profile)
                    return True
            return False

    # ------------------------------------------------------------------
    # Presets
    # ------------------------------------------------------------------

    def create_preset(
        self,
        name: str,
        description: str,
        colorblind_mode: ColorblindMode,
        contrast_mode: ContrastMode,
        motion_reduction: MotionReduction,
        text_scaling: TextScalingConfig,
        subtitle_config: SubtitleConfig,
        audio_description: AudioDescription,
    ) -> AccessibilityPreset:
        """Create and register a new reusable accessibility preset."""
        with self._lock:
            self._evict_oldest_preset()
            preset = AccessibilityPreset(
                name=name,
                description=description,
                colorblind_mode=colorblind_mode,
                contrast_mode=contrast_mode,
                motion_reduction=motion_reduction,
                text_scaling=text_scaling,
                subtitle_config=subtitle_config,
                audio_description=audio_description,
            )
            self._presets[preset.preset_id] = preset
            self._total_presets_created += 1
            return preset

    def list_presets(self) -> List[AccessibilityPreset]:
        """Return all registered accessibility presets."""
        with self._lock:
            return list(self._presets.values())

    def get_preset(self, preset_id: str) -> Optional[AccessibilityPreset]:
        """Retrieve a preset by its id."""
        with self._lock:
            return self._presets.get(preset_id)

    def apply_preset(
        self,
        profile_id: str,
        preset_id: str,
    ) -> Optional[AccessibilityProfile]:
        """Copy preset settings into a profile and emit a PRESET_APPLIED event."""
        with self._lock:
            profile = self._profiles.get(profile_id)
            preset = self._presets.get(preset_id)
            if profile is None or preset is None:
                return None
            profile.colorblind_mode = preset.colorblind_mode
            profile.contrast_mode = preset.contrast_mode
            profile.motion_reduction = preset.motion_reduction
            # Deep-copy nested configs so the profile owns independent copies.
            profile.text_scaling = TextScalingConfig(
                ui_scale=preset.text_scaling.ui_scale,
                subtitle_scale=preset.text_scaling.subtitle_scale,
                hud_scale=preset.text_scaling.hud_scale,
                tooltip_scale=preset.text_scaling.tooltip_scale,
                min_scale=preset.text_scaling.min_scale,
                max_scale=preset.text_scaling.max_scale,
            )
            profile.subtitle_config = SubtitleConfig(
                enabled=preset.subtitle_config.enabled,
                font_size=preset.subtitle_config.font_size,
                background=preset.subtitle_config.background,
                text_color=preset.subtitle_config.text_color,
                background_color=preset.subtitle_config.background_color,
                position_y=preset.subtitle_config.position_y,
                duration_multiplier=preset.subtitle_config.duration_multiplier,
                speaker_label=preset.subtitle_config.speaker_label,
                sound_cue_labels=preset.subtitle_config.sound_cue_labels,
            )
            profile.audio_description = AudioDescription(
                enabled=preset.audio_description.enabled,
                volume=preset.audio_description.volume,
                narration_speed=preset.audio_description.narration_speed,
                describe_environment=preset.audio_description.describe_environment,
                describe_actions=preset.audio_description.describe_actions,
                describe_menu=preset.audio_description.describe_menu,
            )
            self._touch(profile)
            self._record_event(
                AccessibilityEventKind.PRESET_APPLIED,
                {
                    "profile_id": profile_id,
                    "preset_id": preset_id,
                    "preset_name": preset.name,
                },
            )
            return profile

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    def validate_profile(self, profile_id: str) -> ValidationResult:
        """Run validation heuristics against a profile and store the result.

        Checks performed:
          - Text scale combined with high/maximum contrast (potential overflow).
          - Input remap collisions (duplicate source or target keys per device).
          - Subtitle text color matching the background color (invisible text).
          - Subtitle background disabled while subtitles are enabled.
          - Audio description volume out of range.
          - Text scale bounds (min_scale greater than max_scale).
        """
        with self._lock:
            profile = self._profiles.get(profile_id)
            issues: List[ValidationIssue] = []

            if profile is None:
                result = ValidationResult(
                    profile_id=profile_id,
                    issues=[
                        ValidationIssue(
                            level=ValidationLevel.ERROR,
                            category="profile",
                            message=f"Profile not found: {profile_id}",
                            suggestion="Create the profile before validating.",
                        )
                    ],
                    valid=False,
                )
                self._evict_oldest_validation()
                self._validations[result.validation_id] = result
                self._total_validations_run += 1
                self._record_event(
                    AccessibilityEventKind.VALIDATION_RUN,
                    {
                        "profile_id": profile_id,
                        "valid": False,
                        "issue_count": 1,
                    },
                )
                return result

            ts = profile.text_scaling
            sub = profile.subtitle_config
            audio = profile.audio_description

            # Check 1: text scale combined with high contrast.
            max_scale = max(ts.ui_scale, ts.subtitle_scale, ts.hud_scale, ts.tooltip_scale)
            if max_scale > 1.5 and profile.contrast_mode in (
                ContrastMode.HIGH,
                ContrastMode.MAXIMUM,
            ):
                issues.append(
                    ValidationIssue(
                        level=ValidationLevel.WARNING,
                        category="text_scaling",
                        message=(
                            f"Text scale {max_scale:.2f} combined with "
                            f"{profile.contrast_mode.value} contrast may cause "
                            "UI overflow or clipping."
                        ),
                        suggestion="Reduce text scale or lower the contrast mode.",
                    )
                )

            # Check 2: text scale bounds inverted.
            if ts.min_scale > ts.max_scale:
                issues.append(
                    ValidationIssue(
                        level=ValidationLevel.ERROR,
                        category="text_scaling",
                        message=(
                            f"min_scale {ts.min_scale} is greater than "
                            f"max_scale {ts.max_scale}."
                        ),
                        suggestion="Ensure min_scale does not exceed max_scale.",
                    )
                )

            # Check 3: input remap collisions (same device + duplicate keys).
            seen_sources: Dict[str, str] = {}
            seen_targets: Dict[str, str] = {}
            for remap in profile.input_remaps:
                source_key = f"{remap.device.value}:{remap.source_key}"
                target_key = f"{remap.device.value}:{remap.target_key}"
                if source_key in seen_sources:
                    issues.append(
                        ValidationIssue(
                            level=ValidationLevel.ERROR,
                            category="input_remap",
                            message=(
                                f"Duplicate source key '{remap.source_key}' on "
                                f"{remap.device.value} (also used by "
                                f"remap {seen_sources[source_key]})."
                            ),
                            suggestion="Assign a unique source key per device.",
                        )
                    )
                else:
                    seen_sources[source_key] = remap.remap_id
                if target_key in seen_targets:
                    issues.append(
                        ValidationIssue(
                            level=ValidationLevel.WARNING,
                            category="input_remap",
                            message=(
                                f"Target key '{remap.target_key}' on "
                                f"{remap.device.value} is shared with remap "
                                f"{seen_targets[target_key]}."
                            ),
                            suggestion="Avoid binding multiple actions to one key.",
                        )
                    )
                else:
                    seen_targets[target_key] = remap.remap_id

            # Check 4: subtitle text color matches background color.
            if sub.enabled and sub.text_color.lower() == sub.background_color.lower():
                issues.append(
                    ValidationIssue(
                        level=ValidationLevel.ERROR,
                        category="subtitle",
                        message=(
                            f"Subtitle text color '{sub.text_color}' is identical "
                            f"to background color '{sub.background_color}'."
                        ),
                        suggestion="Choose contrasting text and background colors.",
                    )
                )

            # Check 5: subtitles enabled with no background.
            if sub.enabled and sub.background == SubtitleBackground.NONE:
                issues.append(
                    ValidationIssue(
                        level=ValidationLevel.WARNING,
                        category="subtitle",
                        message="Subtitles are enabled but background is set to NONE.",
                        suggestion="Use a background or outline for readability.",
                    )
                )

            # Check 6: audio description volume out of range.
            if audio.enabled and (audio.volume < 0.0 or audio.volume > 1.0):
                issues.append(
                    ValidationIssue(
                        level=ValidationLevel.ERROR,
                        category="audio_description",
                        message=f"Audio description volume {audio.volume} is out of [0, 1].",
                        suggestion="Set volume to a value between 0.0 and 1.0.",
                    )
                )

            # Check 7: audio description narration speed out of range.
            if audio.enabled and (audio.narration_speed <= 0.0 or audio.narration_speed > 3.0):
                issues.append(
                    ValidationIssue(
                        level=ValidationLevel.WARNING,
                        category="audio_description",
                        message=(
                            f"Narration speed {audio.narration_speed} is outside "
                            "the recommended (0, 3] range."
                        ),
                        suggestion="Keep narration speed between 0.5 and 2.0.",
                    )
                )

            has_error = any(i.level == ValidationLevel.ERROR for i in issues)
            result = ValidationResult(
                profile_id=profile_id,
                issues=issues,
                valid=not has_error,
            )
            self._evict_oldest_validation()
            self._validations[result.validation_id] = result
            self._total_validations_run += 1
            self._record_event(
                AccessibilityEventKind.VALIDATION_RUN,
                {
                    "profile_id": profile_id,
                    "valid": result.valid,
                    "issue_count": len(issues),
                },
            )
            return result

    def list_validations(
        self,
        profile_id: Optional[str] = None,
    ) -> List[ValidationResult]:
        """Return validation results, optionally filtered by profile id."""
        with self._lock:
            results = list(self._validations.values())
        if profile_id is not None:
            results = [r for r in results if r.profile_id == profile_id]
        return results

    # ------------------------------------------------------------------
    # Events
    # ------------------------------------------------------------------

    def list_events(self, limit: int = 100) -> List[AccessibilityEvent]:
        """Return audit events limited to the most recent `limit` entries."""
        with self._lock:
            events = list(self._events)
        if limit > 0:
            events = events[-limit:]
        return events

    # ------------------------------------------------------------------
    # Stats / Status / Snapshot
    # ------------------------------------------------------------------

    def get_stats(self) -> AccessibilityStats:
        """Compute and return aggregate accessibility system stats."""
        with self._lock:
            total_profiles = len(self._profiles)
            total_input_remaps = len(self._input_remaps)
            total_presets = len(self._presets)
            total_validations = len(self._validations)

            scale_sum = 0.0
            scale_count = 0
            for profile in self._profiles.values():
                ts = profile.text_scaling
                scale_sum += ts.ui_scale + ts.subtitle_scale + ts.hud_scale + ts.tooltip_scale
                scale_count += 4
            avg_text_scale = (scale_sum / scale_count) if scale_count > 0 else 1.0

            colorblind_count = sum(
                1 for p in self._profiles.values()
                if p.colorblind_mode != ColorblindMode.NONE
            )
            colorblind_usage_pct = (
                (colorblind_count / total_profiles * 100.0)
                if total_profiles > 0
                else 0.0
            )

            return AccessibilityStats(
                total_profiles=total_profiles,
                total_input_remaps=total_input_remaps,
                total_presets=total_presets,
                total_validations=total_validations,
                avg_text_scale=avg_text_scale,
                colorblind_usage_pct=colorblind_usage_pct,
            )

    def get_status(self) -> Dict[str, Any]:
        """Return a summary of the current accessibility engine state."""
        with self._lock:
            return {
                "initialized": self._initialized,
                "total_profiles": len(self._profiles),
                "total_input_remaps": len(self._input_remaps),
                "total_presets": len(self._presets),
                "total_validations": len(self._validations),
                "total_events": len(self._events),
                "total_profiles_created": self._total_profiles_created,
                "total_input_remaps_created": self._total_input_remaps_created,
                "total_presets_created": self._total_presets_created,
                "total_validations_run": self._total_validations_run,
            }

    def get_snapshot(self) -> AccessibilitySnapshot:
        """Capture an immutable snapshot of the accessibility engine state."""
        with self._lock:
            stats = self.get_stats()
            return AccessibilitySnapshot(
                initialized=self._initialized,
                profiles=list(self._profiles.values()),
                presets=list(self._presets.values()),
                validations=list(self._validations.values()),
                events=list(self._events),
                stats=stats,
            )

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def reset(self) -> None:
        """Clear all stores and re-seed the engine to its initial state."""
        with self._lock:
            self._profiles.clear()
            self._input_remaps.clear()
            self._presets.clear()
            self._validations.clear()
            self._events.clear()
            self._total_profiles_created = 0
            self._total_input_remaps_created = 0
            self._total_presets_created = 0
            self._total_validations_run = 0
            self._seed_data()


# ---------------------------------------------------------------------------
# Module-Level Factory
# ---------------------------------------------------------------------------


def get_accessibility_system() -> AccessibilitySystemEngine:
    """Return the singleton AccessibilitySystemEngine instance."""
    return AccessibilitySystemEngine.get_instance()
