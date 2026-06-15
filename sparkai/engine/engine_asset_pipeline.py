"""
SparkLabs Engine - AI Asset Pipeline

A unified AI-driven game asset generation pipeline that produces consistent,
stylistically coherent assets across multiple asset types (sprites, audio,
levels, UI, particles, prefabs). All assets generated under a shared
StyleProfile maintain visual and thematic consistency through palette
enforcement, mood-appropriate randomization, and resolution-aware sizing.

Architecture:
  AssetPipelineEngine (Singleton)
    |-- StyleProfile — unified style guide for asset generation
    |-- AssetRequest — queued generation task with status tracking
    |-- GeneratedAsset — completed asset with type-specific metadata
    |-- AssetType — supported asset categories
    |-- AssetStatus — lifecycle states for generation requests

Usage:
    engine = get_asset_pipeline_engine()
    profile = engine.create_style_profile(
        name="pixel_retro",
        color_palette=["#2b2b2b", "#6b6b6b", "#f0d9b5", "#b58863", "#769656"],
        theme="dungeon_crawler",
        mood="dark_atmospheric",
        art_style="pixel_art_16bit",
        resolution=(320, 240),
        pixel_scale=4,
    )
    request = engine.request_asset(
        asset_type=AssetType.SPRITE,
        name="player_idle",
        style_profile_id=profile.profile_id,
        parameters={"variant": "warrior", "size": (32, 32)},
    )
    asset = engine.generate_asset(request.request_id)
"""

from __future__ import annotations

import json
import math
import random
import threading
import time as _time_module
import uuid
from collections import deque
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple

_time = _time_module.time


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

DEFAULT_COLOR_PALETTE: List[str] = [
    "#1a1c2c", "#5d275d", "#b13e53", "#ef7d57", "#ffcd75",
    "#a7f070", "#38b764", "#257179", "#29366f", "#3b5dc9",
    "#41a6f6", "#73eff7", "#f4f4f4", "#94b0c2", "#566c86",
]

DEFAULT_RESOLUTION: Tuple[int, int] = (640, 480)
DEFAULT_PIXEL_SCALE: int = 2
MAX_PALETTE_COLORS: int = 32
MAX_GENERATION_HISTORY: int = 100
MAX_BATCH_SIZE: int = 64


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class AssetType(str, Enum):
    """Categories of generatable game assets supported by the pipeline.

    Each type has a distinct generation strategy that produces
    type-appropriate metadata and preview data.
    """

    SPRITE = "sprite"
    SPRITE_SHEET = "sprite_sheet"
    TILEMAP = "tilemap"
    AUDIO_SFX = "audio_sfx"
    AUDIO_MUSIC = "audio_music"
    UI_ELEMENT = "ui_element"
    FONT = "font"
    PARTICLE = "particle"
    SHADER = "shader"
    LEVEL = "level"
    ANIMATION = "animation"
    PREFAB = "prefab"


class AssetStatus(str, Enum):
    """Lifecycle states for an asset generation request."""

    QUEUED = "queued"
    GENERATING = "generating"
    COMPLETED = "completed"
    FAILED = "failed"
    MODIFIED = "modified"


# ---------------------------------------------------------------------------
# Data Classes
# ---------------------------------------------------------------------------


@dataclass
class StyleProfile:
    """Unified style guide that governs all assets generated under it.

    Assets sharing the same profile_id receive consistent palette
    application, mood-aligned random variation, and resolution-aware
    sizing. This is the central consistency mechanism of the pipeline.

    Attributes:
        profile_id: Unique identifier for the style profile.
        name: Human-readable label for the profile.
        color_palette: Ordered list of hex color strings defining the
            restricted palette for sprite/UI/tilemap generation.
        theme: Broad thematic category (e.g. "dungeon_crawler", "space_opera").
        mood: Emotional tone affecting generation randomness (e.g.
            "dark_atmospheric", "cheerful_bright", "somber_muted").
        art_style: Rendering approach (e.g. "pixel_art_8bit",
            "pixel_art_16bit", "vector_flat", "hand_drawn").
        resolution: Base canvas resolution as (width, height) in pixels.
        pixel_scale: Integer scale factor for pixel-art styles.
        created_at: Unix timestamp of profile creation.
    """

    profile_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = ""
    color_palette: List[str] = field(default_factory=lambda: list(DEFAULT_COLOR_PALETTE))
    theme: str = "generic"
    mood: str = "neutral"
    art_style: str = "pixel_art_16bit"
    resolution: Tuple[int, int] = DEFAULT_RESOLUTION
    pixel_scale: int = DEFAULT_PIXEL_SCALE
    created_at: float = field(default_factory=_time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "profile_id": self.profile_id,
            "name": self.name,
            "color_palette": list(self.color_palette),
            "theme": self.theme,
            "mood": self.mood,
            "art_style": self.art_style,
            "resolution": list(self.resolution),
            "pixel_scale": self.pixel_scale,
            "created_at": self.created_at,
        }

    def _resolve_color(self, index: int) -> str:
        """Return a palette color, wrapping with index if out of range."""
        if not self.color_palette:
            return "#000000"
        return self.color_palette[index % len(self.color_palette)]

    def _seed_for_asset(self, asset_name: str) -> int:
        """Derive a deterministic seed from profile + asset name for
        reproducible randomness within a style context."""
        raw = f"{self.profile_id}_{asset_name}"
        return sum(ord(c) for c in raw) % (2 ** 31)


@dataclass
class AssetRequest:
    """A queued request for asset generation.

    Tracks the lifecycle of a single generation task from submission
    through completion or failure.

    Attributes:
        request_id: Unique identifier for this request.
        asset_type: The category of asset being generated.
        name: Human-readable asset name used for seeding consistency.
        style_profile_id: References the StyleProfile governing generation.
        parameters: Type-specific generation parameters (dimensions,
            waveform, emitter shape, etc.).
        status: Current lifecycle state.
        result: The generated asset (populated on completion).
        created_at: Unix timestamp when the request was submitted.
        completed_at: Unix timestamp when generation finished.
    """

    request_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    asset_type: AssetType = AssetType.SPRITE
    name: str = ""
    style_profile_id: str = ""
    parameters: Dict[str, Any] = field(default_factory=dict)
    status: AssetStatus = AssetStatus.QUEUED
    result: Optional[GeneratedAsset] = None
    created_at: float = field(default_factory=_time)
    completed_at: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "request_id": self.request_id,
            "asset_type": self.asset_type.value,
            "name": self.name,
            "style_profile_id": self.style_profile_id,
            "parameters": dict(self.parameters),
            "status": self.status.value,
            "result": self.result.to_dict() if self.result else None,
            "created_at": self.created_at,
            "completed_at": self.completed_at,
        }


@dataclass
class GeneratedAsset:
    """A completed asset produced by the generation pipeline.

    Holds type-specific metadata describing the generated content
    along with lightweight preview data for editor tooling.

    Attributes:
        asset_id: Unique identifier for the generated asset.
        request_id: Links back to the originating AssetRequest.
        asset_type: Category of the generated asset.
        name: Human-readable name inherited from the request.
        style_profile_id: StyleProfile that governed generation.
        metadata: Type-specific structured data (dimensions for sprites,
            tile layouts for levels, waveform descriptors for audio, etc.).
        preview_data: Lightweight representation for editor previews
            (ascii art, color swatch, waveform sketch).
        created_at: Unix timestamp of asset completion.
    """

    asset_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    request_id: str = ""
    asset_type: AssetType = AssetType.SPRITE
    name: str = ""
    style_profile_id: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    preview_data: Dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=_time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "asset_id": self.asset_id,
            "request_id": self.request_id,
            "asset_type": self.asset_type.value,
            "name": self.name,
            "style_profile_id": self.style_profile_id,
            "metadata": dict(self.metadata),
            "preview_data": dict(self.preview_data),
            "created_at": self.created_at,
        }


# ---------------------------------------------------------------------------
# Asset Pipeline Engine (Singleton)
# ---------------------------------------------------------------------------


class AssetPipelineEngine:
    """AI-driven asset generation pipeline with style-grounded consistency.

    Manages style profiles, queues generation requests, produces assets
    with type-specific metadata, validates output quality, and tracks
    pipeline statistics. All generation respects StyleProfile constraints
    for palette, mood, resolution, and pixel scale.
    """

    _instance: Optional["AssetPipelineEngine"] = None
    _lock = threading.RLock()

    def __init__(self) -> None:
        if getattr(self, "_initialized", False):
            return
        self._initialized: bool = True

        self._style_profiles: Dict[str, StyleProfile] = {}
        self._requests: Dict[str, AssetRequest] = {}
        self._assets: Dict[str, GeneratedAsset] = {}
        self._generation_history: deque = deque(maxlen=MAX_GENERATION_HISTORY)
        self._request_count: int = 0
        self._generation_count: int = 0
        self._failure_count: int = 0
        self._total_generation_time_ms: float = 0.0

        self._rng = random.Random()

        self._type_generators: Dict[
            AssetType, Callable[
                [AssetRequest, StyleProfile, AssetPipelineEngine],
                GeneratedAsset,
            ]
        ] = {
            AssetType.SPRITE: self._generate_sprite,
            AssetType.SPRITE_SHEET: self._generate_sprite_sheet,
            AssetType.TILEMAP: self._generate_tilemap,
            AssetType.AUDIO_SFX: self._generate_audio_sfx,
            AssetType.AUDIO_MUSIC: self._generate_audio_music,
            AssetType.UI_ELEMENT: self._generate_ui_element,
            AssetType.FONT: self._generate_font,
            AssetType.PARTICLE: self._generate_particle,
            AssetType.SHADER: self._generate_shader,
            AssetType.LEVEL: self._generate_level,
            AssetType.ANIMATION: self._generate_animation,
            AssetType.PREFAB: self._generate_prefab,
        }

    @classmethod
    def get_instance(cls) -> "AssetPipelineEngine":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    # ------------------------------------------------------------------
    # Style Profile Management
    # ------------------------------------------------------------------

    def create_style_profile(
        self,
        name: str,
        color_palette: Optional[List[str]] = None,
        theme: str = "generic",
        mood: str = "neutral",
        art_style: str = "pixel_art_16bit",
        resolution: Optional[Tuple[int, int]] = None,
        pixel_scale: int = DEFAULT_PIXEL_SCALE,
    ) -> StyleProfile:
        """Register a new style profile for consistent asset generation.

        Args:
            name: Human-readable label for the profile.
            color_palette: List of hex color strings. Defaults to a
                built-in 15-color palette if not provided.
            theme: Broad thematic category.
            mood: Emotional tone ("dark_atmospheric", "cheerful_bright",
                "somber_muted", "neutral").
            art_style: Rendering approach identifier.
            resolution: Base canvas resolution as (width, height).
            pixel_scale: Integer scale factor for pixel-art styles.

        Returns:
            The newly created StyleProfile.
        """
        with self._lock:
            palette = (
                list(color_palette)
                if color_palette
                else list(DEFAULT_COLOR_PALETTE)
            )
            if len(palette) > MAX_PALETTE_COLORS:
                palette = palette[:MAX_PALETTE_COLORS]

            resolved_res = resolution if resolution else DEFAULT_RESOLUTION

            profile = StyleProfile(
                name=name,
                color_palette=palette,
                theme=theme,
                mood=mood,
                art_style=art_style,
                resolution=resolved_res,
                pixel_scale=max(1, pixel_scale),
            )
            self._style_profiles[profile.profile_id] = profile
            return profile

    def get_style_profile(self, profile_id: str) -> Optional[StyleProfile]:
        """Retrieve a style profile by its identifier.

        Args:
            profile_id: The profile's unique identifier.

        Returns:
            The StyleProfile if found, otherwise None.
        """
        return self._style_profiles.get(profile_id)

    def list_style_profiles(self) -> List[StyleProfile]:
        """Return all registered style profiles."""
        return list(self._style_profiles.values())

    def delete_style_profile(self, profile_id: str) -> bool:
        """Remove a style profile and its associated assets.

        Args:
            profile_id: The profile's unique identifier.

        Returns:
            True if the profile was found and removed, False otherwise.
        """
        with self._lock:
            if profile_id not in self._style_profiles:
                return False
            del self._style_profiles[profile_id]

            orphan_assets = [
                aid for aid, a in self._assets.items()
                if a.style_profile_id == profile_id
            ]
            for aid in orphan_assets:
                del self._assets[aid]

            orphan_requests = [
                rid for rid, r in self._requests.items()
                if r.style_profile_id == profile_id
            ]
            for rid in orphan_requests:
                del self._requests[rid]

            return True

    # ------------------------------------------------------------------
    # Asset Request Management
    # ------------------------------------------------------------------

    def request_asset(
        self,
        asset_type: AssetType,
        name: str,
        style_profile_id: str,
        parameters: Optional[Dict[str, Any]] = None,
    ) -> AssetRequest:
        """Submit a generation request to the pipeline.

        The request is created in QUEUED status. Call generate_asset
        to execute the actual generation.

        Args:
            asset_type: The category of asset to generate.
            name: Human-readable asset name used for seeding.
            style_profile_id: StyleProfile governing visual consistency.
            parameters: Type-specific parameters (dimensions, waveform,
                emitter shape, tile count, etc.).

        Returns:
            The newly created AssetRequest in QUEUED status.

        Raises:
            ValueError: If the style_profile_id does not reference a
                registered StyleProfile.
        """
        if style_profile_id not in self._style_profiles:
            raise ValueError(
                f"StyleProfile '{style_profile_id}' not found. "
                f"Create it first with create_style_profile()."
            )

        with self._lock:
            request = AssetRequest(
                asset_type=asset_type,
                name=name,
                style_profile_id=style_profile_id,
                parameters=dict(parameters) if parameters else {},
            )
            self._requests[request.request_id] = request
            self._request_count += 1
            return request

    def get_request(self, request_id: str) -> Optional[AssetRequest]:
        """Retrieve a generation request by its identifier."""
        return self._requests.get(request_id)

    def cancel_request(self, request_id: str) -> bool:
        """Cancel a queued request before generation begins.

        Args:
            request_id: The request's unique identifier.

        Returns:
            True if the request was found and was queued, False otherwise.
        """
        with self._lock:
            req = self._requests.get(request_id)
            if req is None or req.status != AssetStatus.QUEUED:
                return False
            req.status = AssetStatus.FAILED
            req.completed_at = _time()
            return True

    # ------------------------------------------------------------------
    # Asset Generation
    # ------------------------------------------------------------------

    def generate_asset(self, request_id: str) -> Optional[GeneratedAsset]:
        """Execute generation for a queued asset request.

        Dispatches to the type-specific generator based on the request's
        asset_type. The generator uses the associated StyleProfile for
        palette, mood, resolution, and pixel_scale constraints.

        Args:
            request_id: The request's unique identifier.

        Returns:
            The GeneratedAsset on success, or None if the request was
            not found or is not in QUEUED status.

        Side Effects:
            Updates the AssetRequest status to GENERATING then COMPLETED
            (or FAILED). Records the result in the request and in the
            internal asset registry.
        """
        with self._lock:
            req = self._requests.get(request_id)
            if req is None:
                return None
            if req.status != AssetStatus.QUEUED:
                return req.result if req.status == AssetStatus.COMPLETED else None

            req.status = AssetStatus.GENERATING

        profile = self._style_profiles.get(req.style_profile_id)
        if profile is None:
            with self._lock:
                req.status = AssetStatus.FAILED
                req.completed_at = _time()
                self._failure_count += 1
            return None

        generator = self._type_generators.get(req.asset_type)
        if generator is None:
            with self._lock:
                req.status = AssetStatus.FAILED
                req.completed_at = _time()
                self._failure_count += 1
            return None

        start = _time()
        try:
            asset = generator(req, profile, self)
            elapsed = (_time() - start) * 1000.0
        except Exception:
            with self._lock:
                req.status = AssetStatus.FAILED
                req.completed_at = _time()
                self._failure_count += 1
            return None

        with self._lock:
            asset.request_id = request_id
            asset.name = req.name
            asset.style_profile_id = req.style_profile_id
            asset.created_at = _time()

            req.status = AssetStatus.COMPLETED
            req.result = asset
            req.completed_at = _time()

            self._assets[asset.asset_id] = asset
            self._generation_count += 1
            self._total_generation_time_ms += elapsed
            self._generation_history.append({
                "request_id": request_id,
                "asset_type": req.asset_type.value,
                "name": req.name,
                "elapsed_ms": round(elapsed, 2),
                "completed_at": _time(),
            })

        return asset

    def batch_generate(
        self,
        requests: List[AssetRequest],
    ) -> List[GeneratedAsset]:
        """Generate assets for multiple requests.

        Processes up to MAX_BATCH_SIZE requests. Each request is generated
        independently; a failure in one does not abort the batch.

        Args:
            requests: List of AssetRequest objects to process.

        Returns:
            List of successfully generated GeneratedAsset objects.
            Failed requests are silently skipped.
        """
        results: List[GeneratedAsset] = []
        batch = requests[:MAX_BATCH_SIZE]

        for req in batch:
            asset = self.generate_asset(req.request_id)
            if asset is not None:
                results.append(asset)

        return results

    def estimate_generation_time(
        self,
        asset_type: AssetType,
        parameters: Optional[Dict[str, Any]] = None,
    ) -> float:
        """Estimate generation time in milliseconds for a given asset type.

        The estimate is based on the asset type category and optional
        parameters that affect complexity (e.g., tilemap dimensions).

        Args:
            asset_type: The category of asset.
            parameters: Optional parameters affecting complexity.

        Returns:
            Estimated milliseconds for generation.
        """
        params = parameters or {}

        base_estimates: Dict[AssetType, float] = {
            AssetType.SPRITE:       15.0,
            AssetType.SPRITE_SHEET: 45.0,
            AssetType.TILEMAP:      35.0,
            AssetType.AUDIO_SFX:    25.0,
            AssetType.AUDIO_MUSIC:  80.0,
            AssetType.UI_ELEMENT:   20.0,
            AssetType.FONT:         60.0,
            AssetType.PARTICLE:     30.0,
            AssetType.SHADER:       40.0,
            AssetType.LEVEL:       120.0,
            AssetType.ANIMATION:    50.0,
            AssetType.PREFAB:       25.0,
        }

        base = base_estimates.get(asset_type, 20.0)

        width = params.get("width", params.get("tile_width", 32))
        height = params.get("height", params.get("tile_height", 32))
        area_factor = math.sqrt((width * height) / (32 * 32))
        area_factor = max(0.5, min(area_factor, 10.0))

        frame_count = params.get("frame_count", params.get("animation_frames", 1))
        frame_factor = math.sqrt(max(1, frame_count))

        return round(base * area_factor * frame_factor, 1)

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    def validate_asset(self, asset_id: str) -> Dict[str, Any]:
        """Validate a generated asset against quality heuristics.

        Produces scores for consistency, style matching, and technical
        quality. These are heuristics based on the asset's metadata and
        are not a substitute for manual review.

        Args:
            asset_id: The generated asset's unique identifier.

        Returns:
            A dict with keys:
                consistency_score (0.0-1.0): How well the asset's
                    internal metadata fields cohere with each other.
                style_match (0.0-1.0): How well the asset adheres to
                    its declared StyleProfile constraints.
                technical_quality (0.0-1.0): Whether technical fields
                    (dimensions, counts, ranges) fall within valid bounds.
                valid (bool): True if all scores are above minimum threshold.
                warnings (List[str]): Diagnostic messages for scores
                    below threshold.
        """
        asset = self._assets.get(asset_id)
        if asset is None:
            return {
                "consistency_score": 0.0,
                "style_match": 0.0,
                "technical_quality": 0.0,
                "valid": False,
                "warnings": [f"Asset '{asset_id}' not found."],
            }

        profile = self._style_profiles.get(asset.style_profile_id)

        consistency_score = self._compute_consistency_score(asset)
        style_match = self._compute_style_match(asset, profile)
        technical_quality = self._compute_technical_quality(asset)

        warnings: List[str] = []
        threshold = 0.4
        if consistency_score < threshold:
            warnings.append(
                f"Low consistency score ({consistency_score:.2f}): "
                f"metadata fields may conflict."
            )
        if style_match < threshold:
            warnings.append(
                f"Low style match ({style_match:.2f}): asset may not "
                f"adhere to style profile '{asset.style_profile_id}'."
            )
        if technical_quality < threshold:
            warnings.append(
                f"Low technical quality ({technical_quality:.2f}): "
                f"dimensions or counts may be out of valid range."
            )

        valid = (
            consistency_score >= threshold
            and style_match >= threshold
            and technical_quality >= threshold
        )

        return {
            "consistency_score": round(consistency_score, 3),
            "style_match": round(style_match, 3),
            "technical_quality": round(technical_quality, 3),
            "valid": valid,
            "warnings": warnings,
        }

    def _compute_consistency_score(self, asset: GeneratedAsset) -> float:
        """Score how internally coherent the asset's metadata fields are."""
        meta = asset.metadata
        score = 1.0

        if asset.asset_type in (AssetType.SPRITE, AssetType.SPRITE_SHEET):
            dims = meta.get("dimensions", (0, 0))
            frames = meta.get("animation_frames", 0)
            if frames > 0 and (dims[0] % frames != 0 and dims[1] % frames != 0):
                score -= 0.3

        elif asset.asset_type in (AssetType.AUDIO_SFX, AssetType.AUDIO_MUSIC):
            duration = meta.get("duration_seconds", 0.0)
            sample_rate = meta.get("sample_rate", 44100)
            if duration > 0 and sample_rate > 0:
                channels = meta.get("channels", 1)
                estimated_samples = duration * sample_rate * channels
                if estimated_samples > 10_000_000:
                    score -= 0.2

        elif asset.asset_type == AssetType.LEVEL:
            tile_width = meta.get("tilemap_width", 0)
            tile_height = meta.get("tilemap_height", 0)
            enemy_count = meta.get("enemy_count", 0)
            if tile_width > 0 and tile_height > 0:
                density = enemy_count / (tile_width * tile_height)
                if density > 0.5:
                    score -= 0.4

        elif asset.asset_type == AssetType.PARTICLE:
            count = meta.get("particle_count", 0)
            lifetime = meta.get("lifetime", 0.0)
            if count > 5000 and lifetime < 0.1:
                score -= 0.3

        return max(0.0, score)

    def _compute_style_match(
        self,
        asset: GeneratedAsset,
        profile: Optional[StyleProfile],
    ) -> float:
        """Score how well the asset matches its StyleProfile."""
        if profile is None:
            return 0.5
        score = 1.0

        resolution = asset.metadata.get("resolution", asset.metadata.get("dimensions"))
        if resolution and isinstance(resolution, (list, tuple)) and len(resolution) >= 2:
            w, h = resolution[0], resolution[1]
            pw, ph = profile.resolution
            if pw > 0 and ph > 0:
                w_ratio = abs(w / pw - 1.0) if w > 0 else 1.0
                h_ratio = abs(h / ph - 1.0) if h > 0 else 1.0
                resolution_deviation = (w_ratio + h_ratio) / 2.0
                score -= min(resolution_deviation, 0.5)

        palette_match = asset.metadata.get("palette_used", [])
        if palette_match and profile.color_palette:
            profile_set = {c.lower() for c in profile.color_palette}
            match_count = sum(
                1 for c in palette_match if c.lower() in profile_set
            )
            if match_count > 0:
                palette_ratio = match_count / len(palette_match)
                score -= (1.0 - palette_ratio) * 0.3

        pixel_scale = asset.metadata.get("pixel_scale", profile.pixel_scale)
        if pixel_scale != profile.pixel_scale:
            score -= 0.15

        return max(0.0, score)

    def _compute_technical_quality(self, asset: GeneratedAsset) -> float:
        """Score whether technical metadata falls within valid bounds."""
        meta = asset.metadata
        score = 1.0

        dims = meta.get("dimensions", meta.get("tile_dimensions"))
        if dims and isinstance(dims, (list, tuple)) and len(dims) >= 2:
            w, h = dims[0], dims[1]
            if w <= 0 or h <= 0 or w > 8192 or h > 8192:
                score -= 0.5

        sample_rate = meta.get("sample_rate")
        if sample_rate is not None and sample_rate not in (
            8000, 11025, 22050, 44100, 48000, 96000,
        ):
            score -= 0.2

        duration = meta.get("duration_seconds")
        if duration is not None and (duration < 0.1 or duration > 600):
            score -= 0.3

        return max(0.0, score)

    # ------------------------------------------------------------------
    # Query Methods
    # ------------------------------------------------------------------

    def list_assets(
        self,
        asset_type: Optional[AssetType] = None,
        style_profile_id: Optional[str] = None,
    ) -> List[GeneratedAsset]:
        """List generated assets with optional filtering.

        Args:
            asset_type: If provided, filter to this asset type.
            style_profile_id: If provided, filter to this style profile.

        Returns:
            List of matching GeneratedAsset objects.
        """
        results: List[GeneratedAsset] = []
        for asset in self._assets.values():
            if asset_type is not None and asset.asset_type != asset_type:
                continue
            if style_profile_id is not None and asset.style_profile_id != style_profile_id:
                continue
            results.append(asset)
        return results

    def get_asset(self, asset_id: str) -> Optional[GeneratedAsset]:
        """Retrieve a generated asset by its identifier."""
        return self._assets.get(asset_id)

    # ------------------------------------------------------------------
    # Statistics
    # ------------------------------------------------------------------

    def get_stats(self) -> Dict[str, Any]:
        """Return pipeline statistics.

        Includes request/generation counts, failure rate, average
        generation time, asset distribution by type, and style profile
        usage.
        """
        type_distribution: Dict[str, int] = {}
        for asset in self._assets.values():
            k = asset.asset_type.value
            type_distribution[k] = type_distribution.get(k, 0) + 1

        status_counts: Dict[str, int] = {}
        for req in self._requests.values():
            k = req.status.value
            status_counts[k] = status_counts.get(k, 0) + 1

        profile_usage: Dict[str, int] = {}
        for asset in self._assets.values():
            pid = asset.style_profile_id
            profile_usage[pid] = profile_usage.get(pid, 0) + 1

        avg_time = (
            self._total_generation_time_ms / self._generation_count
            if self._generation_count > 0
            else 0.0
        )

        failure_rate = (
            self._failure_count / self._request_count
            if self._request_count > 0
            else 0.0
        )

        return {
            "style_profiles": len(self._style_profiles),
            "total_requests": self._request_count,
            "total_generated": self._generation_count,
            "total_failures": self._failure_count,
            "failure_rate": round(failure_rate, 4),
            "queued_requests": status_counts.get("queued", 0),
            "generating_requests": status_counts.get("generating", 0),
            "completed_requests": status_counts.get("completed", 0),
            "failed_requests": status_counts.get("failed", 0),
            "modified_requests": status_counts.get("modified", 0),
            "average_generation_time_ms": round(avg_time, 2),
            "type_distribution": type_distribution,
            "profile_usage": profile_usage,
            "generation_history_size": len(self._generation_history),
        }

    def get_generation_history(self) -> List[Dict[str, Any]]:
        """Return the most recent generation entries."""
        return list(self._generation_history)

    def clear_history(self) -> None:
        """Clear the generation history buffer."""
        with self._lock:
            self._generation_history.clear()

    # ------------------------------------------------------------------
    # Type-Specific Generators
    # ------------------------------------------------------------------

    def _derive_seed(self, profile: StyleProfile, asset_name: str) -> int:
        """Derive a deterministic seed from profile + asset name."""
        return profile._seed_for_asset(asset_name)

    def _sample_palette(
        self,
        profile: StyleProfile,
        count: int,
        seed: int,
    ) -> List[str]:
        """Sample a subset of colors from the profile palette."""
        rng = random.Random(seed)
        palette = profile.color_palette
        if count >= len(palette):
            return list(palette)
        indices = rng.sample(range(len(palette)), count)
        return [palette[i] for i in indices]

    def _interpolate_color(
        self,
        c1: str,
        c2: str,
        t: float,
    ) -> str:
        """Linearly interpolate between two hex colors."""
        r1 = int(c1[1:3], 16)
        g1 = int(c1[3:5], 16)
        b1 = int(c1[5:7], 16)
        r2 = int(c2[1:3], 16)
        g2 = int(c2[3:5], 16)
        b2 = int(c2[5:7], 16)
        r = int(r1 + (r2 - r1) * t)
        g = int(g1 + (g2 - g1) * t)
        b = int(b1 + (b2 - b1) * t)
        return f"#{r:02x}{g:02x}{b:02x}"

    def _mood_multiplier(self, mood: str) -> float:
        """Return a randomness damping factor based on mood.

        Dark/muted moods reduce variation; bright moods increase it.
        """
        mood_factors = {
            "dark_atmospheric": 0.6,
            "somber_muted": 0.7,
            "neutral": 1.0,
            "cheerful_bright": 1.3,
            "chaotic": 1.6,
        }
        return mood_factors.get(mood, 1.0)

    def _make_preview_sprite(
        self,
        width: int,
        height: int,
        palette: List[str],
        seed: int,
    ) -> Dict[str, Any]:
        """Generate a lightweight ascii-style preview for sprites."""
        rng = random.Random(seed)
        chars = " .:-=+*#%@"
        rows: List[str] = []
        for y in range(min(height, 16)):
            row_chars: List[str] = []
            for x in range(min(width, 32)):
                idx = rng.randint(0, len(chars) - 1)
                row_chars.append(chars[idx])
            rows.append("".join(row_chars))
        return {
            "ascii_preview": rows,
            "dominant_colors": palette[:5],
        }

    def _make_preview_audio(self, duration: float, channels: int) -> Dict[str, Any]:
        """Generate a lightweight waveform sketch for audio previews."""
        points = 40
        wave: List[float] = []
        for i in range(points):
            t = i / points
            amplitude = math.sin(t * math.pi * 4) * (1.0 - t) * 0.8
            if channels > 1:
                amplitude *= 1.2
            wave.append(round(amplitude, 3))
        return {
            "waveform_sketch": wave,
            "duration_seconds": round(duration, 2),
            "channels": channels,
        }

    # -- Sprite Generation --

    def _generate_sprite(
        self,
        req: AssetRequest,
        profile: StyleProfile,
        engine: AssetPipelineEngine,
    ) -> GeneratedAsset:
        params = req.parameters
        seed = self._derive_seed(profile, req.name)
        rng = random.Random(seed)
        mood_factor = self._mood_multiplier(profile.mood)

        base_w = params.get("width", params.get("size", (32, 32))[0] if isinstance(params.get("size"), (list, tuple)) else 32)
        base_h = params.get("height", params.get("size", (32, 32))[1] if isinstance(params.get("size"), (list, tuple)) else 32)

        w_variation = int(base_w * 0.1 * mood_factor)
        h_variation = int(base_h * 0.1 * mood_factor)
        width = max(8, base_w + rng.randint(-w_variation, w_variation))
        height = max(8, base_h + rng.randint(-h_variation, h_variation))

        frames = params.get("animation_frames", 1)
        frame_width = width // frames if frames > 1 else width

        palette_count = rng.randint(3, min(8, len(profile.color_palette)))
        used_palette = self._sample_palette(profile, palette_count, seed + 1)

        collision_type = params.get("collision", "box")
        collision_bounds: Dict[str, Any]
        if collision_type == "circle":
            radius = min(width, height) // 2 - 1
            collision_bounds = {"type": "circle", "radius": max(1, radius)}
        elif collision_type == "capsule":
            collision_bounds = {
                "type": "capsule",
                "width": max(2, width - 4),
                "height": max(2, height // 2),
            }
        else:
            collision_bounds = {
                "type": "box",
                "x": rng.randint(0, max(0, width // 4)),
                "y": rng.randint(0, max(0, height // 4)),
                "width": max(4, width - rng.randint(0, width // 4)),
                "height": max(4, height - rng.randint(0, height // 4)),
            }

        metadata: Dict[str, Any] = {
            "dimensions": (width, height),
            "frame_width": frame_width,
            "animation_frames": frames,
            "palette_used": used_palette,
            "collision_bounds": collision_bounds,
            "pixel_scale": profile.pixel_scale,
            "resolution": profile.resolution,
            "estimated_memory_bytes": width * height * 4,
            "mood": profile.mood,
            "theme": profile.theme,
            "art_style": profile.art_style,
        }

        preview = self._make_preview_sprite(width, height, used_palette, seed + 2)

        return GeneratedAsset(
            asset_type=AssetType.SPRITE,
            metadata=metadata,
            preview_data=preview,
        )

    # -- Sprite Sheet Generation --

    def _generate_sprite_sheet(
        self,
        req: AssetRequest,
        profile: StyleProfile,
        engine: AssetPipelineEngine,
    ) -> GeneratedAsset:
        params = req.parameters
        seed = self._derive_seed(profile, req.name)
        rng = random.Random(seed)

        columns = params.get("columns", 4)
        rows = params.get("rows", 4)
        cell_w = params.get("cell_width", 32)
        cell_h = params.get("cell_height", 32)

        total_w = columns * cell_w
        total_h = rows * cell_h

        palette_count = rng.randint(4, min(12, len(profile.color_palette)))
        used_palette = self._sample_palette(profile, palette_count, seed + 1)

        cell_offsets: List[Dict[str, int]] = []
        for r in range(rows):
            for c in range(columns):
                cell_offsets.append({
                    "x": c * cell_w,
                    "y": r * cell_h,
                    "width": cell_w,
                    "height": cell_h,
                    "frame_index": r * columns + c,
                })

        metadata: Dict[str, Any] = {
            "dimensions": (total_w, total_h),
            "columns": columns,
            "rows": rows,
            "cell_width": cell_w,
            "cell_height": cell_h,
            "total_cells": columns * rows,
            "cell_offsets": cell_offsets,
            "palette_used": used_palette,
            "pixel_scale": profile.pixel_scale,
            "resolution": profile.resolution,
            "estimated_memory_bytes": total_w * total_h * 4,
        }

        preview = self._make_preview_sprite(
            min(total_w, 64), min(total_h, 64), used_palette, seed + 2,
        )

        return GeneratedAsset(
            asset_type=AssetType.SPRITE_SHEET,
            metadata=metadata,
            preview_data=preview,
        )

    # -- Tilemap Generation --

    def _generate_tilemap(
        self,
        req: AssetRequest,
        profile: StyleProfile,
        engine: AssetPipelineEngine,
    ) -> GeneratedAsset:
        params = req.parameters
        seed = self._derive_seed(profile, req.name)
        rng = random.Random(seed)

        tile_w = params.get("tile_width", 16)
        tile_h = params.get("tile_height", 16)
        map_w = params.get("map_width", 20)
        map_h = params.get("map_height", 15)

        layer_count = params.get("layers", 3)

        palette_count = rng.randint(4, min(10, len(profile.color_palette)))
        used_palette = self._sample_palette(profile, palette_count, seed + 1)

        tile_types_used: List[str] = ["ground", "wall", "water", "decoration"]
        rng.shuffle(tile_types_used)
        tile_types_used = tile_types_used[:rng.randint(2, len(tile_types_used))]

        layers_metadata: List[Dict[str, Any]] = []
        for layer_idx in range(layer_count):
            layer_seed = seed + layer_idx * 1000
            layer_rng = random.Random(layer_seed)
            tile_data: List[List[int]] = []
            for y in range(map_h):
                row: List[int] = []
                for x in range(map_w):
                    tile_id = layer_rng.randint(0, len(tile_types_used) - 1)
                    row.append(tile_id)
                tile_data.append(row)
            layers_metadata.append({
                "layer_index": layer_idx,
                "name": f"layer_{layer_idx}",
                "visible": layer_idx == 0 or layer_rng.choice([True, True, False]),
                "opacity": 1.0 if layer_idx == 0 else round(layer_rng.uniform(0.5, 1.0), 2),
                "tile_data": tile_data,
            })

        metadata: Dict[str, Any] = {
            "tile_dimensions": (tile_w, tile_h),
            "map_dimensions": (map_w, map_h),
            "total_tiles": map_w * map_h,
            "layers": layers_metadata,
            "layer_count": layer_count,
            "tile_types_used": tile_types_used,
            "palette_used": used_palette,
            "pixel_scale": profile.pixel_scale,
            "resolution": profile.resolution,
        }

        preview_colors = used_palette[:4] if len(used_palette) >= 4 else used_palette
        preview = self._make_preview_sprite(map_w, map_h, preview_colors, seed + 2)

        return GeneratedAsset(
            asset_type=AssetType.TILEMAP,
            metadata=metadata,
            preview_data=preview,
        )

    # -- Audio SFX Generation --

    def _generate_audio_sfx(
        self,
        req: AssetRequest,
        profile: StyleProfile,
        engine: AssetPipelineEngine,
    ) -> GeneratedAsset:
        params = req.parameters
        seed = self._derive_seed(profile, req.name)
        rng = random.Random(seed)
        mood_factor = self._mood_multiplier(profile.mood)

        waveforms = ["sine", "square", "sawtooth", "triangle", "noise"]
        waveform = params.get("waveform", rng.choice(waveforms))

        duration = params.get("duration_seconds", round(rng.uniform(0.1, 2.0), 2))
        duration = max(0.05, min(duration, 10.0))

        sample_rate = params.get("sample_rate", rng.choice([22050, 44100, 48000]))
        channels = params.get("channels", rng.choice([1, 2]))

        frequency_base = params.get("frequency_hz", rng.uniform(80, 2000))
        frequency_base *= (0.8 + 0.4 * mood_factor)

        envelope = {
            "attack_seconds": round(rng.uniform(0.001, 0.05), 4),
            "decay_seconds": round(rng.uniform(0.01, duration * 0.3), 4),
            "sustain_level": round(rng.uniform(0.3, 0.9), 2),
            "release_seconds": round(rng.uniform(0.01, duration * 0.4), 4),
        }

        metadata: Dict[str, Any] = {
            "duration_seconds": duration,
            "sample_rate": sample_rate,
            "channels": channels,
            "waveform_type": waveform,
            "frequency_hz": round(frequency_base, 1),
            "envelope": envelope,
            "estimated_file_size_bytes": int(duration * sample_rate * channels * 2),
            "loopable": params.get("loopable", False),
            "mood": profile.mood,
            "theme": profile.theme,
        }

        preview = self._make_preview_audio(duration, channels)

        return GeneratedAsset(
            asset_type=AssetType.AUDIO_SFX,
            metadata=metadata,
            preview_data=preview,
        )

    # -- Audio Music Generation --

    def _generate_audio_music(
        self,
        req: AssetRequest,
        profile: StyleProfile,
        engine: AssetPipelineEngine,
    ) -> GeneratedAsset:
        params = req.parameters
        seed = self._derive_seed(profile, req.name)
        rng = random.Random(seed)
        mood_factor = self._mood_multiplier(profile.mood)

        duration = params.get("duration_seconds", round(rng.uniform(30, 180), 0))
        duration = max(5.0, min(duration, 600.0))

        sample_rate = params.get("sample_rate", 44100)
        channels = params.get("channels", 2)

        bpm = params.get("bpm", rng.randint(60, 180))
        bpm = int(bpm * (0.8 + 0.4 * mood_factor))
        bpm = max(40, min(bpm, 240))

        time_signature = params.get("time_signature", rng.choice(["4/4", "3/4", "6/8", "2/4"]))

        music_scales = ["major", "minor", "pentatonic", "chromatic", "blues"]
        scale = params.get("scale", rng.choice(music_scales))

        key_root = params.get("key", rng.choice([
            "C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B",
        ]))

        track_count = rng.randint(2, 6)
        tracks: List[Dict[str, Any]] = []
        for i in range(track_count):
            tracks.append({
                "track_index": i,
                "instrument": rng.choice([
                    "piano", "synth_lead", "bass", "drums", "strings",
                    "pad", "pluck", "organ",
                ]),
                "midi_channel": i,
                "polyphony": rng.randint(1, 8),
                "volume": round(rng.uniform(0.3, 1.0), 2),
                "pan": round(rng.uniform(-1.0, 1.0), 2),
            })

        section_count = rng.randint(2, 5)
        sections: List[Dict[str, Any]] = []
        for i in range(section_count):
            sections.append({
                "section_index": i,
                "name": rng.choice(["intro", "verse", "chorus", "bridge", "outro", "loop"]),
                "start_beat": i * (bpm // 2),
                "length_beats": rng.randint(bpm // 2, bpm * 2),
                "active_tracks": rng.sample(
                    range(track_count),
                    rng.randint(1, track_count),
                ),
            })

        metadata: Dict[str, Any] = {
            "duration_seconds": duration,
            "sample_rate": sample_rate,
            "channels": channels,
            "bpm": bpm,
            "time_signature": time_signature,
            "key": key_root,
            "scale": scale,
            "tracks": tracks,
            "track_count": track_count,
            "sections": sections,
            "section_count": section_count,
            "estimated_file_size_bytes": int(duration * sample_rate * channels * 2),
            "loopable": params.get("loopable", True),
            "mood": profile.mood,
            "theme": profile.theme,
        }

        preview = self._make_preview_audio(duration, channels)

        return GeneratedAsset(
            asset_type=AssetType.AUDIO_MUSIC,
            metadata=metadata,
            preview_data=preview,
        )

    # -- UI Element Generation --

    def _generate_ui_element(
        self,
        req: AssetRequest,
        profile: StyleProfile,
        engine: AssetPipelineEngine,
    ) -> GeneratedAsset:
        params = req.parameters
        seed = self._derive_seed(profile, req.name)
        rng = random.Random(seed)

        element_type = params.get("element_type", rng.choice([
            "button", "panel", "slider", "toggle", "dropdown",
            "text_input", "scrollbar", "progress_bar", "tooltip",
        ]))

        width = params.get("width", rng.randint(64, 400))
        height = params.get("height", rng.randint(24, 200))

        palette_count = rng.randint(3, min(6, len(profile.color_palette)))
        used_palette = self._sample_palette(profile, palette_count, seed + 1)

        interaction_states: Dict[str, Dict[str, Any]] = {}
        state_names = ["default", "hover", "pressed", "disabled", "focused"]
        for state in state_names:
            state_rng = random.Random(seed + hash(state) % 10000)
            interaction_states[state] = {
                "background_color": used_palette[state_rng.randint(0, len(used_palette) - 1)],
                "text_color": profile._resolve_color(state_rng.randint(0, len(profile.color_palette) - 1)),
                "border_color": used_palette[state_rng.randint(0, len(used_palette) - 1)],
                "border_width": state_rng.randint(0, 3),
                "corner_radius": rng.randint(0, 12) if element_type in ("button", "panel") else 0,
                "scale": 1.0 if state == "default" else round(state_rng.uniform(0.95, 1.05), 3),
                "opacity": round(state_rng.uniform(0.4, 1.0), 2) if state == "disabled" else 1.0,
            }

        style_properties: Dict[str, Any] = {
            "font_size": rng.randint(10, 32),
            "font_weight": rng.choice(["normal", "bold", "light"]),
            "text_align": rng.choice(["left", "center", "right"]),
            "padding": [rng.randint(2, 16) for _ in range(4)],
            "margin": [rng.randint(0, 8) for _ in range(4)],
            "shadow_enabled": rng.choice([True, False]),
            "shadow_offset": (rng.randint(0, 4), rng.randint(0, 4)),
            "shadow_color": used_palette[0],
        }

        accessibility: Dict[str, Any] = {
            "aria_label": f"{element_type}_{req.name}",
            "focusable": element_type not in ("tooltip",),
            "min_contrast_ratio": round(rng.uniform(4.5, 7.0), 1),
            "scalable": True,
            "screen_reader_text": f"{element_type} element: {req.name}",
        }

        metadata: Dict[str, Any] = {
            "dimensions": (width, height),
            "element_type": element_type,
            "interaction_states": interaction_states,
            "style_properties": style_properties,
            "accessibility": accessibility,
            "palette_used": used_palette,
            "pixel_scale": profile.pixel_scale,
            "resolution": profile.resolution,
        }

        preview = self._make_preview_sprite(
            min(width, 64), min(height, 32), used_palette, seed + 2,
        )

        return GeneratedAsset(
            asset_type=AssetType.UI_ELEMENT,
            metadata=metadata,
            preview_data=preview,
        )

    # -- Font Generation --

    def _generate_font(
        self,
        req: AssetRequest,
        profile: StyleProfile,
        engine: AssetPipelineEngine,
    ) -> GeneratedAsset:
        params = req.parameters
        seed = self._derive_seed(profile, req.name)
        rng = random.Random(seed)

        font_size = params.get("font_size", rng.randint(8, 72))
        font_weight = params.get("font_weight", rng.choice(["normal", "bold"]))
        font_style = params.get("font_style", rng.choice(["serif", "sans_serif", "monospace", "pixel"]))

        glyph_count = params.get("glyph_count", rng.randint(64, 256))
        charset = params.get("charset", "ascii")

        metadata: Dict[str, Any] = {
            "font_size": font_size,
            "font_weight": font_weight,
            "font_style": font_style,
            "glyph_count": glyph_count,
            "charset": charset,
            "line_height": int(font_size * 1.4),
            "ascent": int(font_size * 0.8),
            "descent": int(font_size * 0.2),
            "kerning_pairs": rng.randint(0, 200),
            "estimated_memory_bytes": glyph_count * font_size * font_size // 2,
            "pixel_scale": profile.pixel_scale,
            "resolution": profile.resolution,
        }

        preview_colors: List[str] = []
        for i in range(min(3, len(profile.color_palette))):
            preview_colors.append(profile._resolve_color(i))

        preview: Dict[str, Any] = {
            "sample_text": "The quick brown fox jumps over the lazy dog. 0123456789",
            "text_colors": preview_colors,
            "font_size": font_size,
        }

        return GeneratedAsset(
            asset_type=AssetType.FONT,
            metadata=metadata,
            preview_data=preview,
        )

    # -- Particle Generation --

    def _generate_particle(
        self,
        req: AssetRequest,
        profile: StyleProfile,
        engine: AssetPipelineEngine,
    ) -> GeneratedAsset:
        params = req.parameters
        seed = self._derive_seed(profile, req.name)
        rng = random.Random(seed)
        mood_factor = self._mood_multiplier(profile.mood)

        emitter_shapes = ["point", "circle", "cone", "box", "sphere", "line", "ring"]
        emitter_shape = params.get("emitter_shape", rng.choice(emitter_shapes))

        emitter_params: Dict[str, Any] = {}
        if emitter_shape == "circle":
            emitter_params["radius"] = rng.uniform(5, 50) * mood_factor
        elif emitter_shape == "cone":
            emitter_params["angle_degrees"] = rng.uniform(10, 90)
            emitter_params["length"] = rng.uniform(10, 100) * mood_factor
        elif emitter_shape == "box":
            emitter_params["width"] = rng.uniform(10, 80) * mood_factor
            emitter_params["height"] = rng.uniform(10, 80) * mood_factor
        elif emitter_shape == "sphere":
            emitter_params["radius"] = rng.uniform(5, 40) * mood_factor
        elif emitter_shape == "line":
            emitter_params["length"] = rng.uniform(10, 120) * mood_factor
        elif emitter_shape == "ring":
            emitter_params["inner_radius"] = rng.uniform(5, 30)
            emitter_params["outer_radius"] = rng.uniform(10, 60) * mood_factor

        particle_count = params.get("particle_count", rng.randint(10, 200))
        particle_count = int(particle_count * mood_factor)
        particle_count = max(5, min(particle_count, 1000))

        lifetime = params.get("lifetime", round(rng.uniform(0.2, 5.0), 2))
        lifetime = max(0.05, lifetime)

        palette_count = rng.randint(3, min(6, len(profile.color_palette)))
        used_palette = self._sample_palette(profile, palette_count, seed + 1)

        gradient_stops: List[Dict[str, Any]] = []
        for i in range(rng.randint(2, 5)):
            t = i / max(1, rng.randint(2, 5) - 1)
            gradient_stops.append({
                "position": round(t, 2),
                "color": used_palette[i % len(used_palette)],
                "alpha": round(rng.uniform(0.3, 1.0), 2),
            })

        velocity_range: Dict[str, Any] = {
            "min_speed": round(rng.uniform(10, 50) * mood_factor, 1),
            "max_speed": round(rng.uniform(50, 200) * mood_factor, 1),
            "direction_spread_degrees": rng.randint(0, 360),
            "gravity": round(rng.uniform(-200, 200), 1),
        }

        size_range: Dict[str, Any] = {
            "min_size": round(rng.uniform(1, 8), 1),
            "max_size": round(rng.uniform(4, 32), 1),
            "size_over_lifetime": rng.choice(["constant", "grow", "shrink", "pulse"]),
        }

        metadata: Dict[str, Any] = {
            "emitter_shape": emitter_shape,
            "emitter_parameters": emitter_params,
            "particle_count": particle_count,
            "lifetime": lifetime,
            "color_gradient": gradient_stops,
            "velocity_range": velocity_range,
            "size_range": size_range,
            "blend_mode": rng.choice(["additive", "alpha", "multiply"]),
            "palette_used": used_palette,
            "mood": profile.mood,
            "theme": profile.theme,
        }

        preview = {
            "particle_count": particle_count,
            "dominant_colors": used_palette[:3],
            "emitter_shape": emitter_shape,
            "estimated_max_particles": particle_count,
        }

        return GeneratedAsset(
            asset_type=AssetType.PARTICLE,
            metadata=metadata,
            preview_data=preview,
        )

    # -- Shader Generation --

    def _generate_shader(
        self,
        req: AssetRequest,
        profile: StyleProfile,
        engine: AssetPipelineEngine,
    ) -> GeneratedAsset:
        params = req.parameters
        seed = self._derive_seed(profile, req.name)
        rng = random.Random(seed)

        shader_type = params.get("shader_type", rng.choice([
            "vertex", "fragment", "compute", "geometry",
        ]))

        uniforms: List[Dict[str, Any]] = []
        uniform_names = ["u_time", "u_resolution", "u_mouse", "u_color"]
        for i, name in enumerate(uniform_names[:rng.randint(2, len(uniform_names))]):
            uniforms.append({
                "name": name,
                "type": rng.choice(["float", "vec2", "vec3", "vec4", "sampler2D"]),
                "default": None,
            })

        metadata: Dict[str, Any] = {
            "shader_type": shader_type,
            "uniforms": uniforms,
            "uniform_count": len(uniforms),
            "version": params.get("glsl_version", "330 core"),
            "estimated_instruction_count": rng.randint(20, 200),
            "texture_slots": rng.randint(0, 4),
            "mood": profile.mood,
            "theme": profile.theme,
        }

        preview: Dict[str, Any] = {
            "shader_type": shader_type,
            "uniform_names": [u["name"] for u in uniforms],
        }

        return GeneratedAsset(
            asset_type=AssetType.SHADER,
            metadata=metadata,
            preview_data=preview,
        )

    # -- Level Generation --

    def _generate_level(
        self,
        req: AssetRequest,
        profile: StyleProfile,
        engine: AssetPipelineEngine,
    ) -> GeneratedAsset:
        params = req.parameters
        seed = self._derive_seed(profile, req.name)
        rng = random.Random(seed)
        mood_factor = self._mood_multiplier(profile.mood)

        tile_w = params.get("tilemap_width", 40)
        tile_h = params.get("tilemap_height", 30)
        difficulty = params.get("difficulty", rng.randint(1, 10))

        player_spawn: Dict[str, Any] = {
            "x": rng.randint(1, tile_w - 2),
            "y": rng.randint(1, tile_h - 2),
        }

        enemy_count = max(1, int(rng.randint(3, 15) * (difficulty / 5.0) * mood_factor))
        enemies: List[Dict[str, Any]] = []
        enemy_types = ["patrol", "chaser", "shooter", "stationary", "boss"]
        for i in range(enemy_count):
            enemy_type = enemy_types[i % len(enemy_types)] if i < len(enemy_types) else rng.choice(enemy_types)
            enemies.append({
                "enemy_id": i,
                "type": enemy_type,
                "x": rng.randint(1, tile_w - 2),
                "y": rng.randint(1, tile_h - 2),
                "difficulty_rating": round(
                    rng.uniform(0.5, 1.5) * (difficulty / 5.0), 2
                ),
                "patrol_points": (
                    [(rng.randint(1, tile_w - 2), rng.randint(1, tile_h - 2))
                     for _ in range(rng.randint(0, 4))]
                    if enemy_type == "patrol" else []
                ),
            })

        item_count = rng.randint(3, 20)
        items: List[Dict[str, Any]] = []
        item_types = ["health_potion", "mana_potion", "coin", "weapon", "armor", "key", "ammo"]
        for i in range(item_count):
            items.append({
                "item_id": i,
                "type": rng.choice(item_types),
                "x": rng.randint(1, tile_w - 2),
                "y": rng.randint(1, tile_h - 2),
                "quantity": rng.randint(1, 5),
                "rarity": rng.choice(["common", "uncommon", "rare"]),
            })

        difficulty_curve: List[Dict[str, Any]] = []
        segments = rng.randint(3, 6)
        for i in range(segments):
            progress = i / (segments - 1) if segments > 1 else 0.0
            difficulty_curve.append({
                "progress": round(progress, 2),
                "enemy_spawn_rate": round(0.2 + progress * 0.8 * mood_factor, 2),
                "item_drop_rate": round(0.5 - progress * 0.3, 2),
                "environmental_hazards": rng.randint(0, int(progress * 5)),
            })

        palette_count = rng.randint(4, min(8, len(profile.color_palette)))
        used_palette = self._sample_palette(profile, palette_count, seed + 1)

        tilemap_layout: List[List[int]] = []
        floor_tile = 0
        wall_tile = 1
        for y in range(min(tile_h, 30)):
            row: List[int] = []
            for x in range(min(tile_w, 40)):
                if x == 0 or y == 0 or x == tile_w - 1 or y == tile_h - 1:
                    row.append(wall_tile)
                elif rng.random() < 0.02:
                    row.append(wall_tile)
                else:
                    row.append(floor_tile)
            tilemap_layout.append(row)

        metadata: Dict[str, Any] = {
            "tilemap_layout": tilemap_layout,
            "tilemap_width": tile_w,
            "tilemap_height": tile_h,
            "enemy_placement": enemies,
            "enemy_count": enemy_count,
            "item_distribution": items,
            "item_count": item_count,
            "difficulty_curve": difficulty_curve,
            "difficulty": difficulty,
            "player_spawn": player_spawn,
            "palette_used": used_palette,
            "mood": profile.mood,
            "theme": profile.theme,
        }

        preview: Dict[str, Any] = {
            "level_width": tile_w,
            "level_height": tile_h,
            "enemy_count": enemy_count,
            "item_count": item_count,
            "difficulty": difficulty,
            "simple_layout": tilemap_layout[:8] if len(tilemap_layout) >= 8 else tilemap_layout,
        }

        return GeneratedAsset(
            asset_type=AssetType.LEVEL,
            metadata=metadata,
            preview_data=preview,
        )

    # -- Animation Generation --

    def _generate_animation(
        self,
        req: AssetRequest,
        profile: StyleProfile,
        engine: AssetPipelineEngine,
    ) -> GeneratedAsset:
        params = req.parameters
        seed = self._derive_seed(profile, req.name)
        rng = random.Random(seed)

        frame_count = params.get("frame_count", rng.randint(4, 32))
        frame_rate = params.get("fps", rng.choice([6, 8, 12, 15, 24, 30]))
        loop = params.get("loop", True)
        ping_pong = params.get("ping_pong", False)

        sprite_width = params.get("sprite_width", rng.randint(16, 128))
        sprite_height = params.get("sprite_height", rng.randint(16, 128))

        keyframes: List[Dict[str, Any]] = []
        key_count = rng.randint(2, min(6, frame_count))
        for i in range(key_count):
            keyframes.append({
                "frame_index": int(i * frame_count / max(1, key_count - 1)),
                "label": f"key_{i}",
                "duration_frames": rng.randint(2, 6),
            })

        palette_count = rng.randint(3, min(8, len(profile.color_palette)))
        used_palette = self._sample_palette(profile, palette_count, seed + 1)

        animation_events: List[Dict[str, Any]] = []
        if rng.choice([True, False, False]):
            animation_events.append({
                "frame": rng.randint(0, frame_count - 1),
                "event_name": rng.choice(["footstep", "attack", "jump", "land", "effect"]),
            })

        metadata: Dict[str, Any] = {
            "frame_count": frame_count,
            "fps": frame_rate,
            "loop": loop,
            "ping_pong": ping_pong,
            "sprite_dimensions": (sprite_width, sprite_height),
            "keyframes": keyframes,
            "keyframe_count": key_count,
            "animation_events": animation_events,
            "palette_used": used_palette,
            "duration_seconds": round(frame_count / frame_rate, 3),
            "pixel_scale": profile.pixel_scale,
        }

        preview = self._make_preview_sprite(
            sprite_width, sprite_height, used_palette, seed + 2,
        )
        preview["frame_count"] = frame_count
        preview["fps"] = frame_rate

        return GeneratedAsset(
            asset_type=AssetType.ANIMATION,
            metadata=metadata,
            preview_data=preview,
        )

    # -- Prefab Generation --

    def _generate_prefab(
        self,
        req: AssetRequest,
        profile: StyleProfile,
        engine: AssetPipelineEngine,
    ) -> GeneratedAsset:
        params = req.parameters
        seed = self._derive_seed(profile, req.name)
        rng = random.Random(seed)

        component_types = [
            "Transform", "SpriteRenderer", "Collider", "RigidBody",
            "Animator", "AudioSource", "ParticleEmitter", "Script",
            "Light2D", "UI_Canvas",
        ]
        component_count = rng.randint(2, min(6, len(component_types)))
        selected_components = rng.sample(component_types, component_count)

        component_list: List[Dict[str, Any]] = []
        for comp_name in selected_components:
            comp_defaults: Dict[str, Any] = {"enabled": rng.choice([True, True, False])}
            if comp_name == "Transform":
                comp_defaults.update({
                    "position": [round(rng.uniform(-100, 100), 1) for _ in range(3)],
                    "scale": [round(rng.uniform(0.5, 2.0), 2) for _ in range(3)],
                    "rotation": [round(rng.uniform(0, 360), 1)],
                })
            elif comp_name == "SpriteRenderer":
                comp_defaults.update({
                    "sprite": "",
                    "color": profile._resolve_color(rng.randint(0, len(profile.color_palette) - 1)),
                    "sorting_layer": rng.randint(0, 10),
                    "flip_x": rng.choice([True, False]),
                    "flip_y": rng.choice([True, False]),
                })
            elif comp_name == "Collider":
                comp_defaults.update({
                    "shape": rng.choice(["box", "circle", "capsule"]),
                    "trigger": rng.choice([True, False, False]),
                    "offset": [0.0, 0.0],
                })
            elif comp_name == "Light2D":
                comp_defaults.update({
                    "intensity": round(rng.uniform(0.3, 1.5), 2),
                    "range": round(rng.uniform(5, 50), 1),
                    "color": profile._resolve_color(rng.randint(0, len(profile.color_palette) - 1)),
                })
            component_list.append({
                "name": comp_name,
                "property_defaults": comp_defaults,
            })

        variant_count = rng.randint(1, 4)
        variants: List[Dict[str, Any]] = []
        for i in range(variant_count):
            variants.append({
                "variant_id": uuid.uuid4().hex[:12],
                "variant_name": f"variant_{i + 1}",
                "weight": round(rng.uniform(0.5, 2.0), 2),
                "overrides": {
                    "scale": [round(rng.uniform(0.8, 1.5), 2) for _ in range(3)]
                } if i > 0 else {},
            })

        palette_count = rng.randint(2, min(5, len(profile.color_palette)))
        used_palette = self._sample_palette(profile, palette_count, seed + 1)

        metadata: Dict[str, Any] = {
            "component_list": component_list,
            "component_count": component_count,
            "property_defaults": {
                comp["name"]: comp["property_defaults"] for comp in component_list
            },
            "variant_data": variants,
            "variant_count": variant_count,
            "palette_used": used_palette,
            "pixel_scale": profile.pixel_scale,
            "resolution": profile.resolution,
            "mood": profile.mood,
            "theme": profile.theme,
        }

        preview: Dict[str, Any] = {
            "component_names": selected_components,
            "variant_names": [v["variant_name"] for v in variants],
            "dominant_colors": used_palette[:3],
        }

        return GeneratedAsset(
            asset_type=AssetType.PREFAB,
            metadata=metadata,
            preview_data=preview,
        )


# ---------------------------------------------------------------------------
# Module Accessor
# ---------------------------------------------------------------------------


def get_asset_pipeline_engine() -> AssetPipelineEngine:
    """Return the singleton AssetPipelineEngine instance."""
    return AssetPipelineEngine.get_instance()