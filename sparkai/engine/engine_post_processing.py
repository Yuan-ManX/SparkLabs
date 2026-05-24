"""
SparkLabs Engine - Post Processing System

Screen-space post-processing effects pipeline for cinematic rendering
and gameplay-driven visual feedback. Manages composable effect chains
with quality profiles, pass ordering, and parameter-driven effect
configuration for bloom, depth of field, motion blur, SSAO, vignette,
chromatic aberration, color grading, film grain, tone mapping,
and anti-aliasing.

Architecture:
  PostProcessingSystem
    |-- PostEffect (individual effect with typed parameters)
    |-- EffectChain (ordered sequence of effects per render pass)
    |-- RenderPass (target binding with pass-order semantics)
    |-- PipelineProfile (named collection of chains for scene presets)
"""

from __future__ import annotations

import threading
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class EffectType(Enum):
    BLOOM = "bloom"
    DOF = "dof"
    MOTION_BLUR = "motion_blur"
    SSAO = "ssao"
    VIGNETTE = "vignette"
    CHROMATIC_ABERRATION = "chromatic_aberration"
    COLOR_GRADING = "color_grading"
    FILM_GRAIN = "film_grain"
    TONE_MAPPING = "tone_mapping"
    ANTI_ALIASING = "anti_aliasing"


class EffectQuality(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    ULTRA = "ultra"
    BESPOKE = "bespoke"


class PassOrder(Enum):
    PRE_FX = "pre_fx"
    MAIN = "main"
    POST_FX = "post_fx"
    OVERLAY = "overlay"
    UI = "ui"


DEFAULT_EFFECT_PARAMETERS: Dict[EffectType, Dict[str, Any]] = {
    EffectType.BLOOM: {
        "intensity": 0.5, "threshold": 0.8, "radius": 1.5,
        "scatter": 0.7, "tint_r": 1.0, "tint_g": 1.0, "tint_b": 1.0,
    },
    EffectType.DOF: {
        "focus_distance": 10.0, "aperture": 1.4, "focal_length": 50.0,
        "max_blur": 4.0, "near_transition": 0.2, "far_transition": 0.8,
    },
    EffectType.MOTION_BLUR: {
        "intensity": 0.6, "sample_count": 8, "shutter_speed": 0.02,
        "max_velocity": 10.0, "tile_size": 16,
    },
    EffectType.SSAO: {
        "radius": 1.0, "intensity": 0.8, "bias": 0.025,
        "sample_count": 16, "occlusion_power": 2.0, "blur_radius": 2.0,
    },
    EffectType.VIGNETTE: {
        "intensity": 0.4, "radius": 0.9, "softness": 0.3,
        "center_x": 0.5, "center_y": 0.5, "color_r": 0.0, "color_g": 0.0, "color_b": 0.0,
    },
    EffectType.CHROMATIC_ABERRATION: {
        "intensity": 0.3, "radial_amount": 0.5, "tangential_amount": 0.1,
        "center_x": 0.5, "center_y": 0.5, "max_samples": 3,
    },
    EffectType.COLOR_GRADING: {
        "intensity": 1.0, "lookup_texture": "",
        "contrast": 1.0, "saturation": 1.0, "brightness": 0.0,
        "temperature": 6500.0, "tint": 0.0,
    },
    EffectType.FILM_GRAIN: {
        "intensity": 0.15, "grain_size": 1.6, "luminance_contribution": 0.5,
        "color_shift": 0.1, "animate": True, "seed": 0,
    },
    EffectType.TONE_MAPPING: {
        "exposure": 1.0, "method": "aces",
        "white_point": 4.0, "gamma": 2.2,
    },
    EffectType.ANTI_ALIASING: {
        "method": "taa", "sample_count": 4, "jitter_scale": 1.0,
        "feedback_min": 0.88, "feedback_max": 0.97,
    },
}


# ---------------------------------------------------------------------------
# Data Classes
# ---------------------------------------------------------------------------


@dataclass
class PostEffect:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    effect_type: str = "bloom"
    quality: str = "medium"
    enabled: bool = True
    parameters: Dict[str, Any] = field(default_factory=dict)
    pass_order: str = "post_fx"
    blend_weight: float = 1.0
    render_scale: float = 1.0
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "effect_type": self.effect_type,
            "quality": self.quality,
            "enabled": self.enabled,
            "parameters": dict(self.parameters),
            "pass_order": self.pass_order,
            "blend_weight": round(self.blend_weight, 3),
            "render_scale": round(self.render_scale, 3),
            "created_at": self.created_at,
        }


@dataclass
class EffectChain:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = ""
    pass_order: str = "post_fx"
    effect_ids: List[str] = field(default_factory=list)
    render_scale: float = 1.0
    target_width: int = 1920
    target_height: int = 1080
    is_active: bool = True
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "pass_order": self.pass_order,
            "effect_count": len(self.effect_ids),
            "effect_ids": list(self.effect_ids),
            "render_scale": round(self.render_scale, 3),
            "target_width": self.target_width,
            "target_height": self.target_height,
            "is_active": self.is_active,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


@dataclass
class RenderPass:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = ""
    pass_order: str = "post_fx"
    chain_ids: List[str] = field(default_factory=list)
    source_texture: str = "_main_color"
    target_texture: str = "_post_color"
    clear_buffer: bool = True
    render_scale: float = 1.0
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "pass_order": self.pass_order,
            "chain_count": len(self.chain_ids),
            "chain_ids": list(self.chain_ids),
            "source_texture": self.source_texture,
            "target_texture": self.target_texture,
            "clear_buffer": self.clear_buffer,
            "render_scale": round(self.render_scale, 3),
            "created_at": self.created_at,
        }


@dataclass
class PipelineProfile:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = ""
    chain_ids: List[str] = field(default_factory=list)
    render_pass_id: str = ""
    description: str = ""
    default_quality: str = "medium"
    is_active: bool = False
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "chain_count": len(self.chain_ids),
            "chain_ids": list(self.chain_ids),
            "render_pass_id": self.render_pass_id,
            "description": self.description,
            "default_quality": self.default_quality,
            "is_active": self.is_active,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


# ---------------------------------------------------------------------------
# Parameter Helpers
# ---------------------------------------------------------------------------


_QUALITY_SAMPLE_MULTIPLIERS: Dict[str, float] = {
    "low": 0.25,
    "medium": 0.5,
    "high": 1.0,
    "ultra": 2.0,
    "bespoke": 1.0,
}


def _merge_parameters(
    defaults: Dict[str, Any],
    overrides: Dict[str, Any],
) -> Dict[str, Any]:
    merged = dict(defaults)
    for key, value in overrides.items():
        merged[key] = value
    return merged


def _resolve_effect_type(effect_type: str) -> Optional[EffectType]:
    try:
        return EffectType(effect_type.lower())
    except ValueError:
        pass
    return None


def _resolve_quality(quality: str) -> str:
    try:
        EffectQuality(quality.lower())
        return quality.lower()
    except ValueError:
        return "medium"


def _resolve_pass_order(pass_order: str) -> str:
    try:
        PassOrder(pass_order.lower())
        return pass_order.lower()
    except ValueError:
        return "post_fx"


# ---------------------------------------------------------------------------
# Post Processing System (Singleton)
# ---------------------------------------------------------------------------


class PostProcessingSystem:
    _instance: Optional["PostProcessingSystem"] = None
    _lock: threading.RLock = threading.RLock()

    def __init__(self) -> None:
        self._effects: Dict[str, PostEffect] = {}
        self._chains: Dict[str, EffectChain] = {}
        self._render_passes: Dict[str, RenderPass] = {}
        self._profiles: Dict[str, PipelineProfile] = {}
        self._active_profile_id: str = ""
        self._effect_count: int = 0
        self._chain_count: int = 0
        self._profile_count: int = 0
        self._frames_processed: int = 0

    @classmethod
    def get_instance(cls) -> "PostProcessingSystem":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    # ------------------------------------------------------------------
    # Effect Management
    # ------------------------------------------------------------------

    def add_effect(
        self,
        effect_type: str = "bloom",
        parameters: Optional[Dict[str, Any]] = None,
        quality: str = "medium",
    ) -> Optional[PostEffect]:
        with self._lock:
            resolved_type = _resolve_effect_type(effect_type)
            if resolved_type is None:
                return None

            resolved_quality = _resolve_quality(quality)
            defaults = dict(DEFAULT_EFFECT_PARAMETERS.get(resolved_type, {}))
            merged_params = _merge_parameters(defaults, parameters or {})

            sample_count = merged_params.get("sample_count", 4)
            multiplier = _QUALITY_SAMPLE_MULTIPLIERS.get(resolved_quality, 0.5)
            if "sample_count" in defaults and quality != "bespoke":
                merged_params["sample_count"] = max(1, int(sample_count * multiplier))

            effect = PostEffect(
                effect_type=resolved_type.value,
                quality=resolved_quality,
                parameters=merged_params,
            )
            self._effects[effect.id] = effect
            self._effect_count += 1
            return effect

    def get_effect(self, effect_id: str) -> Optional[PostEffect]:
        return self._effects.get(effect_id)

    def remove_effect(self, effect_id: str) -> bool:
        with self._lock:
            if effect_id not in self._effects:
                return False

            for chain in self._chains.values():
                if effect_id in chain.effect_ids:
                    chain.effect_ids.remove(effect_id)
                    chain.updated_at = time.time()

            del self._effects[effect_id]
            self._effect_count = max(0, self._effect_count - 1)
            return True

    def toggle_effect(self, effect_id: str, enabled: bool) -> bool:
        with self._lock:
            effect = self._effects.get(effect_id)
            if effect is None:
                return False
            effect.enabled = enabled
            return True

    def update_effect_parameter(
        self,
        effect_id: str,
        param_name: str,
        value: Any,
    ) -> bool:
        with self._lock:
            effect = self._effects.get(effect_id)
            if effect is None:
                return False
            effect.parameters[param_name] = value
            return True

    def set_effect_quality(self, effect_id: str, quality: str) -> bool:
        with self._lock:
            effect = self._effects.get(effect_id)
            if effect is None:
                return False

            resolved_quality = _resolve_quality(quality)
            effect.quality = resolved_quality

            sample_key = "sample_count"
            if sample_key in effect.parameters and quality != "bespoke":
                base_defaults = DEFAULT_EFFECT_PARAMETERS.get(
                    EffectType(effect.effect_type), {}
                )
                base_samples = base_defaults.get(sample_key, 4)
                multiplier = _QUALITY_SAMPLE_MULTIPLIERS.get(resolved_quality, 0.5)
                effect.parameters[sample_key] = max(1, int(base_samples * multiplier))

            return True

    # ------------------------------------------------------------------
    # Chain Management
    # ------------------------------------------------------------------

    def create_chain(
        self,
        name: str,
        pass_order: str = "post_fx",
    ) -> Optional[EffectChain]:
        with self._lock:
            resolved_order = _resolve_pass_order(pass_order)
            chain = EffectChain(
                name=name,
                pass_order=resolved_order,
            )
            self._chains[chain.id] = chain
            self._chain_count += 1
            return chain

    def get_chain(self, chain_id: str) -> Optional[EffectChain]:
        return self._chains.get(chain_id)

    def remove_chain(self, chain_id: str) -> bool:
        with self._lock:
            if chain_id not in self._chains:
                return False

            for render_pass in self._render_passes.values():
                if chain_id in render_pass.chain_ids:
                    render_pass.chain_ids.remove(chain_id)

            for profile in self._profiles.values():
                if chain_id in profile.chain_ids:
                    profile.chain_ids.remove(chain_id)
                    profile.updated_at = time.time()

            del self._chains[chain_id]
            self._chain_count = max(0, self._chain_count - 1)
            return True

    def add_effect_to_chain(
        self,
        chain_id: str,
        effect_id: str,
        index: int = -1,
    ) -> bool:
        with self._lock:
            chain = self._chains.get(chain_id)
            if chain is None:
                return False

            effect = self._effects.get(effect_id)
            if effect is None:
                return False

            if effect_id in chain.effect_ids:
                return False

            if index < 0 or index >= len(chain.effect_ids):
                chain.effect_ids.append(effect_id)
            else:
                chain.effect_ids.insert(index, effect_id)

            chain.updated_at = time.time()
            return True

    def remove_effect_from_chain(
        self,
        chain_id: str,
        effect_id: str,
    ) -> bool:
        with self._lock:
            chain = self._chains.get(chain_id)
            if chain is None:
                return False

            if effect_id not in chain.effect_ids:
                return False

            chain.effect_ids.remove(effect_id)
            chain.updated_at = time.time()
            return True

    def reorder_chain(
        self,
        chain_id: str,
        effect_ids: Optional[List[str]] = None,
    ) -> bool:
        with self._lock:
            chain = self._chains.get(chain_id)
            if chain is None:
                return False

            if effect_ids is None:
                return False

            valid_ids: List[str] = []
            seen: set = set()
            for eid in effect_ids:
                if eid not in seen and eid in self._effects:
                    valid_ids.append(eid)
                    seen.add(eid)

            chain.effect_ids = valid_ids
            chain.updated_at = time.time()
            return True

    # ------------------------------------------------------------------
    # Render Pass Management
    # ------------------------------------------------------------------

    def create_render_pass(
        self,
        name: str,
        pass_order: str = "post_fx",
        source_texture: str = "_main_color",
        target_texture: str = "_post_color",
    ) -> RenderPass:
        with self._lock:
            resolved_order = _resolve_pass_order(pass_order)
            render_pass = RenderPass(
                name=name,
                pass_order=resolved_order,
                source_texture=source_texture,
                target_texture=target_texture,
            )
            self._render_passes[render_pass.id] = render_pass
            return render_pass

    def add_chain_to_render_pass(
        self,
        pass_id: str,
        chain_id: str,
    ) -> bool:
        with self._lock:
            render_pass = self._render_passes.get(pass_id)
            if render_pass is None:
                return False

            if chain_id not in self._chains:
                return False

            if chain_id in render_pass.chain_ids:
                return False

            render_pass.chain_ids.append(chain_id)
            return True

    # ------------------------------------------------------------------
    # Profile Management
    # ------------------------------------------------------------------

    def create_profile(
        self,
        name: str,
        chain_ids: Optional[List[str]] = None,
    ) -> Optional[PipelineProfile]:
        with self._lock:
            valid_chains: List[str] = []
            if chain_ids:
                for cid in chain_ids:
                    if cid in self._chains:
                        valid_chains.append(cid)

            profile = PipelineProfile(
                name=name,
                chain_ids=valid_chains,
            )
            self._profiles[profile.id] = profile
            self._profile_count += 1
            return profile

    def get_profile(self, profile_id: str) -> Optional[PipelineProfile]:
        return self._profiles.get(profile_id)

    def remove_profile(self, profile_id: str) -> bool:
        with self._lock:
            if profile_id not in self._profiles:
                return False

            if self._active_profile_id == profile_id:
                self._active_profile_id = ""

            del self._profiles[profile_id]
            self._profile_count = max(0, self._profile_count - 1)
            return True

    def apply_profile(self, profile_id: str) -> bool:
        with self._lock:
            profile = self._profiles.get(profile_id)
            if profile is None:
                return False

            for pid, p in self._profiles.items():
                if pid != profile_id:
                    p.is_active = False

            profile.is_active = True
            self._active_profile_id = profile_id
            return True

    def update_profile(
        self,
        profile_id: str,
        chain_ids: Optional[List[str]] = None,
        description: Optional[str] = None,
    ) -> bool:
        with self._lock:
            profile = self._profiles.get(profile_id)
            if profile is None:
                return False

            if chain_ids is not None:
                valid_chains: List[str] = []
                for cid in chain_ids:
                    if cid in self._chains:
                        valid_chains.append(cid)
                profile.chain_ids = valid_chains

            if description is not None:
                profile.description = description

            profile.updated_at = time.time()
            return True

    # ------------------------------------------------------------------
    # Preview
    # ------------------------------------------------------------------

    def preview_effect(
        self,
        effect_type: str,
        source_texture: str = "",
    ) -> Dict[str, Any]:
        resolved_type = _resolve_effect_type(effect_type)
        if resolved_type is None:
            return {"error": f"unknown effect type: {effect_type}"}

        defaults = DEFAULT_EFFECT_PARAMETERS.get(resolved_type, {})
        return {
            "effect_type": resolved_type.value,
            "source_texture": source_texture or "_main_color",
            "default_parameters": dict(defaults),
            "parameter_count": len(defaults),
            "supported_qualities": [q.value for q in EffectQuality],
            "compatible_pass_orders": self._get_compatible_passes(resolved_type),
        }

    def _get_compatible_passes(self, effect_type: EffectType) -> List[str]:
        overlay_effects = {
            EffectType.VIGNETTE,
            EffectType.CHROMATIC_ABERRATION,
            EffectType.FILM_GRAIN,
        }
        ui_effects = {
            EffectType.TONE_MAPPING,
        }
        if effect_type in overlay_effects:
            return [PassOrder.OVERLAY.value, PassOrder.POST_FX.value]
        if effect_type in ui_effects:
            return [PassOrder.UI.value, PassOrder.POST_FX.value]
        return [PassOrder.POST_FX.value, PassOrder.MAIN.value]

    # ------------------------------------------------------------------
    # Process Frame
    # ------------------------------------------------------------------

    def process_frame(self) -> Dict[str, Any]:
        with self._lock:
            self._frames_processed += 1

            active_profile = self._profiles.get(self._active_profile_id)
            applied_effects: List[str] = []
            chain_order: List[str] = []

            if active_profile is not None:
                for chain_id in active_profile.chain_ids:
                    chain = self._chains.get(chain_id)
                    if chain is None or not chain.is_active:
                        continue
                    chain_order.append(chain.name)
                    for effect_id in chain.effect_ids:
                        effect = self._effects.get(effect_id)
                        if effect is not None and effect.enabled:
                            applied_effects.append(effect.effect_type)
            else:
                sorted_chains = sorted(
                    self._chains.values(),
                    key=lambda c: _pass_order_priority(c.pass_order),
                )
                for chain in sorted_chains:
                    if not chain.is_active:
                        continue
                    chain_order.append(chain.name)
                    for effect_id in chain.effect_ids:
                        effect = self._effects.get(effect_id)
                        if effect is not None and effect.enabled:
                            applied_effects.append(effect.effect_type)

            return {
                "frame": self._frames_processed,
                "active_profile": self._active_profile_id,
                "chain_order": chain_order,
                "applied_effects": applied_effects,
                "total_applied": len(applied_effects),
            }

    # ------------------------------------------------------------------
    # Stats
    # ------------------------------------------------------------------

    def get_stats(self) -> Dict[str, Any]:
        total_chain_effects = sum(
            len(c.effect_ids) for c in self._chains.values()
        )
        enabled_effects = sum(
            1 for e in self._effects.values() if e.enabled
        )
        active_chains = sum(
            1 for c in self._chains.values() if c.is_active
        )
        active_profile_name = ""
        active = self._profiles.get(self._active_profile_id)
        if active is not None:
            active_profile_name = active.name

        return {
            "effect_count": self._effect_count,
            "chain_count": self._chain_count,
            "profile_count": self._profile_count,
            "render_pass_count": len(self._render_passes),
            "stored_effects": len(self._effects),
            "stored_chains": len(self._chains),
            "stored_profiles": len(self._profiles),
            "total_chain_effects": total_chain_effects,
            "enabled_effects": enabled_effects,
            "active_chains": active_chains,
            "active_profile_id": self._active_profile_id,
            "active_profile_name": active_profile_name,
            "frames_processed": self._frames_processed,
        }

    # ------------------------------------------------------------------
    # Reset
    # ------------------------------------------------------------------

    def reset(self) -> None:
        with self._lock:
            self._effects.clear()
            self._chains.clear()
            self._render_passes.clear()
            self._profiles.clear()
            self._active_profile_id = ""
            self._effect_count = 0
            self._chain_count = 0
            self._profile_count = 0
            self._frames_processed = 0

    # ------------------------------------------------------------------
    # Query Helpers
    # ------------------------------------------------------------------

    def get_effects_by_type(self, effect_type: str) -> List[PostEffect]:
        resolved = _resolve_effect_type(effect_type)
        if resolved is None:
            return []
        return [
            e for e in self._effects.values()
            if e.effect_type == resolved.value
        ]

    def get_chains_by_pass_order(self, pass_order: str) -> List[EffectChain]:
        resolved = _resolve_pass_order(pass_order)
        return [
            c for c in self._chains.values()
            if c.pass_order == resolved
        ]

    def get_all_effects(self) -> Dict[str, Dict[str, Any]]:
        return {eid: e.to_dict() for eid, e in self._effects.items()}

    def get_all_chains(self) -> Dict[str, Dict[str, Any]]:
        return {cid: c.to_dict() for cid, c in self._chains.items()}

    def get_all_profiles(self) -> Dict[str, Dict[str, Any]]:
        return {pid: p.to_dict() for pid, p in self._profiles.items()}


def _pass_order_priority(pass_order: str) -> int:
    order_map = {
        PassOrder.PRE_FX.value: 0,
        PassOrder.MAIN.value: 1,
        PassOrder.POST_FX.value: 2,
        PassOrder.OVERLAY.value: 3,
        PassOrder.UI.value: 4,
    }
    return order_map.get(pass_order, 2)


# ---------------------------------------------------------------------------
# Module-Level Accessor
# ---------------------------------------------------------------------------


def get_post_processing() -> PostProcessingSystem:
    return PostProcessingSystem.get_instance()