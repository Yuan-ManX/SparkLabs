"""
SparkLabs Engine Post-Processing Effects Pipeline

A full suite of screen-space post-processing effects for the AI-native
game engine. Provides composable effect chains with quality profiles,
blend mode control, and stage-based ordering for bloom, blur, color
grading, vignette, chromatic aberration, motion blur, depth of field,
ambient occlusion, film grain, lens flare, tone mapping, anti-aliasing,
sharpen, and pixelate effects.

Architecture:
  PostProcessingEngine (Singleton-per-name)
    |-- PostProcessEffect   — individual effect with typed parameters
    |-- EffectParameter     — parameter metadata with min/max/description
    |-- PipelineConfig      — named collection of ordered effects
    |-- EffectResult        — execution outcome with timing diagnostics

Pipeline Stages:
  1. PRE_PROCESS   — effects applied before the main render pass
  2. MAIN_PROCESS  — effects composited during the main render pass
  3. POST_PROCESS  — effects applied after the main render pass
  4. OVERLAY       — screen-space overlay effects rendered last
"""

from __future__ import annotations

import threading
import uuid
from collections import OrderedDict
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class EffectType(Enum):
    """Screen-space post-processing effect identifiers."""
    BLOOM = "bloom"
    BLUR = "blur"
    COLOR_GRADING = "color_grading"
    VIGNETTE = "vignette"
    CHROMATIC_ABERRATION = "chromatic_aberration"
    MOTION_BLUR = "motion_blur"
    DEPTH_OF_FIELD = "depth_of_field"
    AMBIENT_OCCLUSION = "ambient_occlusion"
    FILM_GRAIN = "film_grain"
    LENS_FLARE = "lens_flare"
    TONE_MAPPING = "tone_mapping"
    ANTIALIASING = "antialiasing"
    SHARPEN = "sharpen"
    PIXELATE = "pixelate"


class BlendMode(Enum):
    """Compositing blend mode for combining effect output with the framebuffer."""
    NORMAL = "normal"
    ADDITIVE = "additive"
    MULTIPLY = "multiply"
    SCREEN = "screen"
    OVERLAY = "overlay"
    SOFT_LIGHT = "soft_light"


class QualityLevel(Enum):
    """Quality presets that control sample counts and internal precision."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    ULTRA = "ultra"


class PipelineStage(Enum):
    """Ordered stages within the post-processing pipeline."""
    PRE_PROCESS = "pre_process"
    MAIN_PROCESS = "main_process"
    POST_PROCESS = "post_process"
    OVERLAY = "overlay"


# ---------------------------------------------------------------------------
# Default Effect Parameters
# ---------------------------------------------------------------------------

DEFAULT_EFFECT_PARAMETERS: Dict[EffectType, Dict[str, Any]] = {
    EffectType.BLOOM: {
        "intensity": 0.5,
        "threshold": 0.8,
        "radius": 1.5,
        "scatter": 0.7,
        "tint_r": 1.0,
        "tint_g": 1.0,
        "tint_b": 1.0,
    },
    EffectType.BLUR: {
        "radius": 4.0,
        "iterations": 2,
        "sigma": 1.0,
        "direction": "both",
    },
    EffectType.COLOR_GRADING: {
        "intensity": 1.0,
        "lookup_texture": "",
        "contrast": 1.0,
        "saturation": 1.0,
        "brightness": 0.0,
        "temperature": 6500.0,
        "tint": 0.0,
    },
    EffectType.VIGNETTE: {
        "intensity": 0.4,
        "radius": 0.9,
        "softness": 0.3,
        "center_x": 0.5,
        "center_y": 0.5,
        "color_r": 0.0,
        "color_g": 0.0,
        "color_b": 0.0,
    },
    EffectType.CHROMATIC_ABERRATION: {
        "intensity": 0.3,
        "radial_amount": 0.5,
        "tangential_amount": 0.1,
        "center_x": 0.5,
        "center_y": 0.5,
        "max_samples": 3,
    },
    EffectType.MOTION_BLUR: {
        "intensity": 0.6,
        "sample_count": 8,
        "shutter_speed": 0.02,
        "max_velocity": 10.0,
        "tile_size": 16,
    },
    EffectType.DEPTH_OF_FIELD: {
        "focus_distance": 10.0,
        "aperture": 1.4,
        "focal_length": 50.0,
        "max_blur": 4.0,
        "near_transition": 0.2,
        "far_transition": 0.8,
    },
    EffectType.AMBIENT_OCCLUSION: {
        "radius": 1.0,
        "intensity": 0.8,
        "bias": 0.025,
        "sample_count": 16,
        "occlusion_power": 2.0,
        "blur_radius": 2.0,
    },
    EffectType.FILM_GRAIN: {
        "intensity": 0.15,
        "grain_size": 1.6,
        "luminance_contribution": 0.5,
        "color_shift": 0.1,
        "animate": True,
        "seed": 0,
    },
    EffectType.LENS_FLARE: {
        "intensity": 0.6,
        "ghost_count": 4,
        "halo_width": 0.5,
        "distortion": 0.3,
        "threshold": 0.9,
        "chromatic_spread": 0.02,
    },
    EffectType.TONE_MAPPING: {
        "exposure": 1.0,
        "method": "aces",
        "white_point": 4.0,
        "gamma": 2.2,
    },
    EffectType.ANTIALIASING: {
        "method": "taa",
        "sample_count": 4,
        "jitter_scale": 1.0,
        "feedback_min": 0.88,
        "feedback_max": 0.97,
    },
    EffectType.SHARPEN: {
        "intensity": 0.5,
        "radius": 1.0,
        "threshold": 0.05,
        "clamp": 0.2,
    },
    EffectType.PIXELATE: {
        "pixel_size": 4,
        "resolution_x": 320,
        "resolution_y": 180,
        "maintain_aspect": True,
        "filter": "nearest",
    },
}

# ---------------------------------------------------------------------------
# Quality sample multipliers
# ---------------------------------------------------------------------------

_QUALITY_SAMPLE_MULTIPLIERS: Dict[QualityLevel, float] = {
    QualityLevel.LOW: 0.25,
    QualityLevel.MEDIUM: 0.5,
    QualityLevel.HIGH: 1.0,
    QualityLevel.ULTRA: 2.0,
}

# ---------------------------------------------------------------------------
# Stage ordering priority
# ---------------------------------------------------------------------------

_STAGE_PRIORITY: Dict[PipelineStage, int] = {
    PipelineStage.PRE_PROCESS: 0,
    PipelineStage.MAIN_PROCESS: 1,
    PipelineStage.POST_PROCESS: 2,
    PipelineStage.OVERLAY: 3,
}


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------

@dataclass
class EffectParameter:
    """Metadata describing a configurable parameter for an effect type."""

    name: str = ""
    value: Any = None
    min_val: Any = None
    max_val: Any = None
    default_val: Any = None
    description: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "value": self.value,
            "min_val": self.min_val,
            "max_val": self.max_val,
            "default_val": self.default_val,
            "description": self.description,
        }


@dataclass
class PostProcessEffect:
    """A single post-processing effect with typed configuration and
    stage-based ordering."""

    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    effect_type: EffectType = EffectType.BLOOM
    enabled: bool = True
    parameters: Dict[str, Any] = field(default_factory=dict)
    blend_mode: BlendMode = BlendMode.NORMAL
    quality: QualityLevel = QualityLevel.MEDIUM
    priority: int = 0
    stage: PipelineStage = PipelineStage.POST_PROCESS
    created_at: str = field(
        default_factory=lambda: datetime.utcnow().isoformat()
    )
    updated_at: str = field(
        default_factory=lambda: datetime.utcnow().isoformat()
    )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "effect_type": self.effect_type.value,
            "enabled": self.enabled,
            "parameters": dict(self.parameters),
            "blend_mode": self.blend_mode.value,
            "quality": self.quality.value,
            "priority": self.priority,
            "stage": self.stage.value,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


@dataclass
class PipelineConfig:
    """A named, ordered collection of post-processing effects that form a
    complete pipeline configuration."""

    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    effects: List[str] = field(default_factory=list)
    resolution_scale: float = 1.0
    quality: QualityLevel = QualityLevel.MEDIUM
    enabled: bool = True
    name: str = ""
    created_at: str = field(
        default_factory=lambda: datetime.utcnow().isoformat()
    )
    updated_at: str = field(
        default_factory=lambda: datetime.utcnow().isoformat()
    )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "effects": list(self.effects),
            "resolution_scale": self.resolution_scale,
            "quality": self.quality.value,
            "enabled": self.enabled,
            "name": self.name,
            "effect_count": len(self.effects),
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


@dataclass
class EffectResult:
    """The outcome of applying a single effect within a pipeline."""

    effect_id: str = ""
    effect_type: EffectType = EffectType.BLOOM
    execution_time_ms: float = 0.0
    success: bool = False
    error: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "effect_id": self.effect_id,
            "effect_type": self.effect_type.value,
            "execution_time_ms": self.execution_time_ms,
            "success": self.success,
            "error": self.error,
        }


# ---------------------------------------------------------------------------
# Post-Processing Engine
# ---------------------------------------------------------------------------

class PostProcessingEngine:
    """
    Post-processing effects pipeline for screen-space visual effects.

    Manages composable effect chains with quality profiles, blend mode
    control, and stage-based ordering. Each named instance maintains its
    own effect registry, pipeline configurations, and execution statistics.
    """

    _instances: Dict[str, "PostProcessingEngine"] = {}
    _lock = threading.RLock()

    def __new__(cls, name: str = "default") -> "PostProcessingEngine":
        if name not in cls._instances:
            with cls._lock:
                if name not in cls._instances:
                    instance = super().__new__(cls)
                    instance._initialized = False
                    cls._instances[name] = instance
        return cls._instances[name]

    @classmethod
    def get_instance(cls, name: str = "default") -> "PostProcessingEngine":
        """Get or create a named PostProcessingEngine instance."""
        if name not in cls._instances:
            with cls._lock:
                if name not in cls._instances:
                    instance = cls(name)
                    instance._initialized = False
                    cls._instances[name] = instance
        return cls._instances[name]

    def __init__(self, name: str = "default") -> None:
        if getattr(self, "_initialized", False):
            return
        self._initialized = True

        self._name: str = name
        self._effects: Dict[str, PostProcessEffect] = OrderedDict()
        self._pipelines: Dict[str, PipelineConfig] = OrderedDict()
        self._max_effects: int = 128
        self._effect_count: int = 0
        self._pipeline_count: int = 0
        self._stats: Dict[str, Any] = {
            "total_effects_added": 0,
            "total_effects_removed": 0,
            "total_pipelines_created": 0,
            "total_pipelines_applied": 0,
            "total_frames_processed": 0,
            "total_execution_time_ms": 0.0,
            "last_error": "",
        }

    # ------------------------------------------------------------------
    # Effect Management
    # ------------------------------------------------------------------

    def add_effect(
        self,
        effect_type: EffectType,
        parameters: Optional[Dict[str, Any]] = None,
        blend_mode: BlendMode = BlendMode.NORMAL,
        quality: QualityLevel = QualityLevel.MEDIUM,
        priority: int = 0,
        stage: PipelineStage = PipelineStage.POST_PROCESS,
    ) -> PostProcessEffect:
        """Add a new post-processing effect to the engine.

        Merges the supplied parameters with the default parameter set for
        the effect type, then applies quality-based sample count scaling.
        """
        with self._lock:
            if self._effect_count >= self._max_effects:
                raise RuntimeError(
                    f"Maximum effect limit reached ({self._max_effects})"
                )

            defaults = dict(DEFAULT_EFFECT_PARAMETERS.get(effect_type, {}))
            merged_params = dict(defaults)
            if parameters:
                merged_params.update(parameters)

            # Apply quality-based sample count scaling
            sample_key = "sample_count"
            if sample_key in defaults:
                multiplier = _QUALITY_SAMPLE_MULTIPLIERS.get(quality, 0.5)
                base = defaults[sample_key]
                merged_params[sample_key] = max(1, int(base * multiplier))

            now = datetime.utcnow().isoformat()
            effect = PostProcessEffect(
                effect_type=effect_type,
                enabled=True,
                parameters=merged_params,
                blend_mode=blend_mode,
                quality=quality,
                priority=priority,
                stage=stage,
                created_at=now,
                updated_at=now,
            )
            self._effects[effect.id] = effect
            self._effect_count += 1
            self._stats["total_effects_added"] += 1
            return effect

    def remove_effect(self, effect_id: str) -> bool:
        """Remove an effect by its ID. Returns True if the effect was found
        and removed."""
        with self._lock:
            if effect_id not in self._effects:
                return False

            # Remove references from all pipelines
            for pipeline in self._pipelines.values():
                if effect_id in pipeline.effects:
                    pipeline.effects.remove(effect_id)
                    pipeline.updated_at = datetime.utcnow().isoformat()

            del self._effects[effect_id]
            self._effect_count = max(0, self._effect_count - 1)
            self._stats["total_effects_removed"] += 1
            return True

    def update_effect(
        self,
        effect_id: str,
        parameters: Optional[Dict[str, Any]] = None,
    ) -> Optional[PostProcessEffect]:
        """Update the parameters of an existing effect. Returns the updated
        effect or None if not found."""
        with self._lock:
            effect = self._effects.get(effect_id)
            if effect is None:
                return None

            if parameters:
                effect.parameters.update(parameters)

            effect.updated_at = datetime.utcnow().isoformat()
            return effect

    def enable_effect(self, effect_id: str) -> bool:
        """Enable an effect. Returns True if the effect was found and
        successfully enabled."""
        with self._lock:
            effect = self._effects.get(effect_id)
            if effect is None:
                return False
            effect.enabled = True
            effect.updated_at = datetime.utcnow().isoformat()
            return True

    def disable_effect(self, effect_id: str) -> bool:
        """Disable an effect. Returns True if the effect was found and
        successfully disabled."""
        with self._lock:
            effect = self._effects.get(effect_id)
            if effect is None:
                return False
            effect.enabled = False
            effect.updated_at = datetime.utcnow().isoformat()
            return True

    def reorder_effects(self, effect_ids: List[str]) -> bool:
        """Reorder effects in the registry according to the provided list of
        effect IDs. Effects not in the list retain their relative order at
        the end. Returns True if the reorder succeeded."""
        with self._lock:
            if not effect_ids:
                return False

            # Build a new ordered dict from the specified order
            new_order: Dict[str, PostProcessEffect] = OrderedDict()
            seen: set = set()

            for eid in effect_ids:
                effect = self._effects.get(eid)
                if effect is not None and eid not in seen:
                    new_order[eid] = effect
                    seen.add(eid)

            # Append any remaining effects not in the reorder list
            for eid, effect in self._effects.items():
                if eid not in seen:
                    new_order[eid] = effect

            self._effects = new_order
            return True

    # ------------------------------------------------------------------
    # Pipeline Management
    # ------------------------------------------------------------------

    def create_pipeline(
        self,
        name: str,
        effect_ids: Optional[List[str]] = None,
        quality: QualityLevel = QualityLevel.MEDIUM,
    ) -> PipelineConfig:
        """Create a named pipeline configuration from a list of effect IDs.

        Only effects that exist in the registry are included. Effects are
        ordered by stage priority, then by their individual priority value.
        """
        with self._lock:
            valid_effects: List[str] = []
            if effect_ids:
                for eid in effect_ids:
                    if eid in self._effects:
                        valid_effects.append(eid)

            # Sort effects by stage priority, then by individual priority
            valid_effects.sort(
                key=lambda eid: (
                    _STAGE_PRIORITY.get(
                        self._effects[eid].stage,
                        2,
                    ),
                    -self._effects[eid].priority,
                )
            )

            now = datetime.utcnow().isoformat()
            pipeline = PipelineConfig(
                effects=valid_effects,
                quality=quality,
                name=name,
                created_at=now,
                updated_at=now,
            )
            self._pipelines[pipeline.id] = pipeline
            self._pipeline_count += 1
            self._stats["total_pipelines_created"] += 1
            return pipeline

    def apply_pipeline(self, pipeline_id: str) -> List[EffectResult]:
        """Apply a pipeline by executing all enabled effects in order.

        Returns a list of EffectResult objects describing the outcome of
        each effect execution.
        """
        with self._lock:
            pipeline = self._pipelines.get(pipeline_id)
            if pipeline is None or not pipeline.enabled:
                return []

            results: List[EffectResult] = []
            for effect_id in pipeline.effects:
                effect = self._effects.get(effect_id)
                if effect is None or not effect.enabled:
                    continue

                # Simulate effect execution with timing
                t_start = datetime.utcnow()
                success = True
                error = ""
                try:
                    # Placeholder for actual GPU/compute shader dispatch
                    self._execute_effect(effect, pipeline)
                except Exception as exc:
                    success = False
                    error = str(exc)
                    self._stats["last_error"] = error

                t_end = datetime.utcnow()
                execution_time_ms = (
                    t_end - t_start
                ).total_seconds() * 1000.0

                result = EffectResult(
                    effect_id=effect.id,
                    effect_type=effect.effect_type,
                    execution_time_ms=round(execution_time_ms, 4),
                    success=success,
                    error=error,
                )
                results.append(result)

            self._stats["total_pipelines_applied"] += 1
            self._stats["total_frames_processed"] += 1
            self._stats["total_execution_time_ms"] += sum(
                r.execution_time_ms for r in results
            )
            return results

    def _execute_effect(
        self,
        effect: PostProcessEffect,
        pipeline: PipelineConfig,
    ) -> None:
        """Internal dispatch for effect execution. This is a placeholder
        that would be replaced with actual GPU shader invocation."""
        _ = effect.parameters
        _ = pipeline.resolution_scale
        _ = pipeline.quality

    # ------------------------------------------------------------------
    # Query
    # ------------------------------------------------------------------

    def get_effect(self, effect_id: str) -> Optional[PostProcessEffect]:
        """Get an effect by its ID."""
        return self._effects.get(effect_id)

    def list_effects(
        self,
        stage: Optional[PipelineStage] = None,
    ) -> List[PostProcessEffect]:
        """List all effects, optionally filtered by pipeline stage."""
        with self._lock:
            if stage is None:
                return list(self._effects.values())
            return [
                e for e in self._effects.values()
                if e.stage == stage
            ]

    def get_available_parameters(
        self,
        effect_type: EffectType,
    ) -> List[EffectParameter]:
        """Get the list of available parameters for a given effect type,
        including metadata such as min/max values and descriptions."""
        defaults = DEFAULT_EFFECT_PARAMETERS.get(effect_type, {})
        param_infos = _EFFECT_PARAMETER_METADATA.get(effect_type, {})

        result: List[EffectParameter] = []
        for param_name, default_val in defaults.items():
            info = param_infos.get(param_name, {})
            result.append(
                EffectParameter(
                    name=param_name,
                    value=default_val,
                    min_val=info.get("min"),
                    max_val=info.get("max"),
                    default_val=default_val,
                    description=info.get("description", ""),
                )
            )
        return result

    def get_pipeline(self, pipeline_id: str) -> Optional[PipelineConfig]:
        """Get a pipeline configuration by its ID."""
        return self._pipelines.get(pipeline_id)

    def list_pipelines(self) -> List[PipelineConfig]:
        """List all pipeline configurations."""
        with self._lock:
            return list(self._pipelines.values())

    def remove_pipeline(self, pipeline_id: str) -> bool:
        """Remove a pipeline configuration by its ID."""
        with self._lock:
            if pipeline_id not in self._pipelines:
                return False
            del self._pipelines[pipeline_id]
            self._pipeline_count = max(0, self._pipeline_count - 1)
            return True

    def set_max_effects(self, limit: int) -> None:
        """Set the maximum number of effects allowed."""
        with self._lock:
            self._max_effects = max(1, limit)

    # ------------------------------------------------------------------
    # Statistics
    # ------------------------------------------------------------------

    def get_stats(self) -> Dict[str, Any]:
        """Get comprehensive engine statistics."""
        with self._lock:
            enabled_count = sum(
                1 for e in self._effects.values() if e.enabled
            )
            disabled_count = self._effect_count - enabled_count

            stage_distribution: Dict[str, int] = {}
            for e in self._effects.values():
                key = e.stage.value
                stage_distribution[key] = stage_distribution.get(key, 0) + 1

            type_distribution: Dict[str, int] = {}
            for e in self._effects.values():
                key = e.effect_type.value
                type_distribution[key] = type_distribution.get(key, 0) + 1

            quality_distribution: Dict[str, int] = {}
            for e in self._effects.values():
                key = e.quality.value
                quality_distribution[key] = quality_distribution.get(key, 0) + 1

            return {
                "instance_name": self._name,
                "effect_count": self._effect_count,
                "enabled_effects": enabled_count,
                "disabled_effects": disabled_count,
                "max_effects": self._max_effects,
                "pipeline_count": self._pipeline_count,
                "stage_distribution": stage_distribution,
                "effect_type_distribution": type_distribution,
                "quality_distribution": quality_distribution,
                "total_effects_added": self._stats["total_effects_added"],
                "total_effects_removed": self._stats["total_effects_removed"],
                "total_pipelines_created": self._stats["total_pipelines_created"],
                "total_pipelines_applied": self._stats["total_pipelines_applied"],
                "total_frames_processed": self._stats["total_frames_processed"],
                "total_execution_time_ms": round(
                    self._stats["total_execution_time_ms"], 4
                ),
                "last_error": self._stats["last_error"],
            }

    # ------------------------------------------------------------------
    # Reset
    # ------------------------------------------------------------------

    def reset(self) -> None:
        """Reset the entire post-processing engine state."""
        with self._lock:
            self._effects = OrderedDict()
            self._pipelines = OrderedDict()
            self._effect_count = 0
            self._pipeline_count = 0
            self._stats = {
                "total_effects_added": 0,
                "total_effects_removed": 0,
                "total_pipelines_created": 0,
                "total_pipelines_applied": 0,
                "total_frames_processed": 0,
                "total_execution_time_ms": 0.0,
                "last_error": "",
            }


# ---------------------------------------------------------------------------
# Effect Parameter Metadata
# ---------------------------------------------------------------------------

_EFFECT_PARAMETER_METADATA: Dict[EffectType, Dict[str, Dict[str, Any]]] = {
    EffectType.BLOOM: {
        "intensity": {"min": 0.0, "max": 2.0, "description": "Overall bloom intensity multiplier"},
        "threshold": {"min": 0.0, "max": 1.0, "description": "Luminance threshold for bloom contribution"},
        "radius": {"min": 0.1, "max": 10.0, "description": "Blur radius for bloom spread"},
        "scatter": {"min": 0.0, "max": 1.0, "description": "Light scatter diffusion amount"},
        "tint_r": {"min": 0.0, "max": 1.0, "description": "Red channel tint for bloom"},
        "tint_g": {"min": 0.0, "max": 1.0, "description": "Green channel tint for bloom"},
        "tint_b": {"min": 0.0, "max": 1.0, "description": "Blue channel tint for bloom"},
    },
    EffectType.BLUR: {
        "radius": {"min": 0.0, "max": 32.0, "description": "Blur kernel radius in pixels"},
        "iterations": {"min": 1, "max": 8, "description": "Number of blur passes"},
        "sigma": {"min": 0.1, "max": 10.0, "description": "Gaussian sigma value"},
        "direction": {"min": None, "max": None, "description": "Blur direction: horizontal, vertical, or both"},
    },
    EffectType.COLOR_GRADING: {
        "intensity": {"min": 0.0, "max": 2.0, "description": "Color grading influence strength"},
        "lookup_texture": {"min": None, "max": None, "description": "Path to LUT texture asset"},
        "contrast": {"min": 0.0, "max": 3.0, "description": "Contrast adjustment multiplier"},
        "saturation": {"min": 0.0, "max": 3.0, "description": "Saturation adjustment multiplier"},
        "brightness": {"min": -1.0, "max": 1.0, "description": "Brightness offset"},
        "temperature": {"min": 1000.0, "max": 40000.0, "description": "White balance temperature in Kelvin"},
        "tint": {"min": -1.0, "max": 1.0, "description": "Green/magenta tint adjustment"},
    },
    EffectType.VIGNETTE: {
        "intensity": {"min": 0.0, "max": 1.0, "description": "Vignette darkening strength"},
        "radius": {"min": 0.1, "max": 1.0, "description": "Radius of the vignette circle"},
        "softness": {"min": 0.0, "max": 1.0, "description": "Edge softness transition"},
        "center_x": {"min": 0.0, "max": 1.0, "description": "Horizontal center of vignette"},
        "center_y": {"min": 0.0, "max": 1.0, "description": "Vertical center of vignette"},
        "color_r": {"min": 0.0, "max": 1.0, "description": "Red channel of vignette color"},
        "color_g": {"min": 0.0, "max": 1.0, "description": "Green channel of vignette color"},
        "color_b": {"min": 0.0, "max": 1.0, "description": "Blue channel of vignette color"},
    },
    EffectType.CHROMATIC_ABERRATION: {
        "intensity": {"min": 0.0, "max": 1.0, "description": "Overall chromatic aberration strength"},
        "radial_amount": {"min": 0.0, "max": 1.0, "description": "Radial distortion component"},
        "tangential_amount": {"min": 0.0, "max": 1.0, "description": "Tangential distortion component"},
        "center_x": {"min": 0.0, "max": 1.0, "description": "Horizontal distortion center"},
        "center_y": {"min": 0.0, "max": 1.0, "description": "Vertical distortion center"},
        "max_samples": {"min": 1, "max": 16, "description": "Maximum sample count for color separation"},
    },
    EffectType.MOTION_BLUR: {
        "intensity": {"min": 0.0, "max": 1.0, "description": "Motion blur strength"},
        "sample_count": {"min": 2, "max": 32, "description": "Number of velocity samples per pixel"},
        "shutter_speed": {"min": 0.0, "max": 0.5, "description": "Virtual shutter speed in seconds"},
        "max_velocity": {"min": 1.0, "max": 100.0, "description": "Maximum velocity clamp"},
        "tile_size": {"min": 8, "max": 64, "description": "Tile size for velocity buffer"},
    },
    EffectType.DEPTH_OF_FIELD: {
        "focus_distance": {"min": 0.1, "max": 1000.0, "description": "Distance to the focal plane"},
        "aperture": {"min": 0.1, "max": 32.0, "description": "Aperture f-stop value"},
        "focal_length": {"min": 1.0, "max": 300.0, "description": "Focal length in millimeters"},
        "max_blur": {"min": 0.0, "max": 16.0, "description": "Maximum blur radius in pixels"},
        "near_transition": {"min": 0.0, "max": 1.0, "description": "Near-field focus transition zone"},
        "far_transition": {"min": 0.0, "max": 1.0, "description": "Far-field focus transition zone"},
    },
    EffectType.AMBIENT_OCCLUSION: {
        "radius": {"min": 0.1, "max": 10.0, "description": "AO sampling radius in world units"},
        "intensity": {"min": 0.0, "max": 2.0, "description": "AO darkening intensity"},
        "bias": {"min": 0.0, "max": 0.1, "description": "Depth bias to prevent self-occlusion"},
        "sample_count": {"min": 4, "max": 64, "description": "Number of AO samples per pixel"},
        "occlusion_power": {"min": 0.5, "max": 5.0, "description": "Exponent applied to occlusion value"},
        "blur_radius": {"min": 0.0, "max": 8.0, "description": "Bilateral blur radius for AO"},
    },
    EffectType.FILM_GRAIN: {
        "intensity": {"min": 0.0, "max": 1.0, "description": "Film grain intensity"},
        "grain_size": {"min": 0.1, "max": 5.0, "description": "Grain particle size"},
        "luminance_contribution": {"min": 0.0, "max": 1.0, "description": "How much grain affects luminance"},
        "color_shift": {"min": 0.0, "max": 1.0, "description": "Chromatic variation in grain"},
        "animate": {"min": None, "max": None, "description": "Whether grain pattern animates each frame"},
        "seed": {"min": 0, "max": 65535, "description": "Random seed for grain pattern"},
    },
    EffectType.LENS_FLARE: {
        "intensity": {"min": 0.0, "max": 2.0, "description": "Overall lens flare intensity"},
        "ghost_count": {"min": 1, "max": 16, "description": "Number of ghost reflections"},
        "halo_width": {"min": 0.0, "max": 1.0, "description": "Width of the central halo"},
        "distortion": {"min": 0.0, "max": 1.0, "description": "Anamorphic distortion amount"},
        "threshold": {"min": 0.0, "max": 1.0, "description": "Brightness threshold for flare generation"},
        "chromatic_spread": {"min": 0.0, "max": 0.1, "description": "Color separation in flare elements"},
    },
    EffectType.TONE_MAPPING: {
        "exposure": {"min": 0.0, "max": 10.0, "description": "Exposure multiplier"},
        "method": {"min": None, "max": None, "description": "Tone mapping method: aces, filmic, reinhard, uncharted2"},
        "white_point": {"min": 0.0, "max": 20.0, "description": "White point luminance"},
        "gamma": {"min": 1.0, "max": 3.0, "description": "Gamma correction value"},
    },
    EffectType.ANTIALIASING: {
        "method": {"min": None, "max": None, "description": "AA method: taa, fxaa, smaa, msaa"},
        "sample_count": {"min": 2, "max": 16, "description": "Number of samples per pixel"},
        "jitter_scale": {"min": 0.0, "max": 2.0, "description": "TAA jitter pattern scale"},
        "feedback_min": {"min": 0.0, "max": 1.0, "description": "Minimum temporal feedback blend"},
        "feedback_max": {"min": 0.0, "max": 1.0, "description": "Maximum temporal feedback blend"},
    },
    EffectType.SHARPEN: {
        "intensity": {"min": 0.0, "max": 2.0, "description": "Sharpening intensity"},
        "radius": {"min": 0.0, "max": 8.0, "description": "Sharpening kernel radius"},
        "threshold": {"min": 0.0, "max": 1.0, "description": "Edge detection threshold for selective sharpening"},
        "clamp": {"min": 0.0, "max": 1.0, "description": "Maximum sharpening delta clamp"},
    },
    EffectType.PIXELATE: {
        "pixel_size": {"min": 1, "max": 64, "description": "Size of each pixel block"},
        "resolution_x": {"min": 1, "max": 1920, "description": "Target horizontal resolution"},
        "resolution_y": {"min": 1, "max": 1080, "description": "Target vertical resolution"},
        "maintain_aspect": {"min": None, "max": None, "description": "Whether to preserve aspect ratio"},
        "filter": {"min": None, "max": None, "description": "Downsample filter: nearest, bilinear"},
    },
}


# ---------------------------------------------------------------------------
# Module-Level Accessor
# ---------------------------------------------------------------------------


def get_post_processing(name: str = "default") -> PostProcessingEngine:
    """Get or create a named PostProcessingEngine instance.

    Args:
        name: A unique name for the engine instance. Defaults to 'default'.

    Returns:
        The PostProcessingEngine singleton instance for the given name.
    """
    return PostProcessingEngine.get_instance(name)