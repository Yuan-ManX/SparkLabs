"""
AssetSynthesizer - AI-powered procedural asset generation system.

Given text descriptions, generates complete asset packs including sprite
definitions, material configurations, sound descriptors, and animation data
for the AI-native game engine. Uses a singleton pattern with thread-safe
double-check locking.
"""

import threading
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Any

_time_module = time


# ---------------------------------------------------------------------------
# Domain Enumerations
# ---------------------------------------------------------------------------


class AssetCategory(Enum):
    """Categories of game assets produced by the synthesizer."""

    SPRITE = "sprite"
    TILESET = "tileset"
    UI_ELEMENT = "ui_element"
    SOUND_EFFECT = "sound_effect"
    BACKGROUND = "background"
    CHARACTER = "character"
    PROP = "prop"
    EFFECT = "effect"


class GenerationStyle(Enum):
    """Visual styles available for asset generation."""

    PIXEL_ART = "pixel_art"
    VECTOR = "vector"
    SKETCH = "sketch"
    REALISTIC = "realistic"
    CARTOON = "cartoon"
    MINIMALIST = "minimalist"
    FANTASY = "fantasy"
    SCI_FI = "sci_fi"


class SynthesisMode(Enum):
    """Modes for asset synthesis operations."""

    SINGLE_ASSET = "single_asset"
    ASSET_PACK = "asset_pack"
    THEME_COLLECTION = "theme_collection"
    VARIATION_SET = "variation_set"


class OutputFormat(Enum):
    """Output formats for synthesized assets."""

    PNG_SHEET = "png_sheet"
    SVG = "svg"
    JSON_DESCRIPTOR = "json_descriptor"
    AUDIO_WAV = "audio_wav"
    SPRITE_ATLAS = "sprite_atlas"


# ---------------------------------------------------------------------------
# Theme Palette Presets
# ---------------------------------------------------------------------------

_THEME_PALETTES: Dict[str, List[str]] = {
    "forest": ["#2d5a27", "#4a8c3f", "#8fbc6b", "#c4d4a0", "#1a3314", "#6b4226"],
    "ocean": ["#1a3a5c", "#2e6b8a", "#4fa4c4", "#7ec8e3", "#0d2137", "#c2e0f0"],
    "desert": ["#c4a35a", "#e8c97a", "#8b6914", "#d4a843", "#f5deb3", "#6b4226"],
    "snow": ["#e8f0f8", "#c8d8e8", "#a0b8d0", "#7890a8", "#f0f4f8", "#506880"],
    "lava": ["#1a0a00", "#4a1800", "#cc3300", "#ff6600", "#ff9933", "#ffcc00"],
    "neon": ["#0a0a2e", "#ff00ff", "#00ffff", "#ff0066", "#00ff66", "#ffff00"],
    "pastel": ["#f8e8e8", "#e8f0e8", "#e8e8f0", "#f0e8f0", "#f8f0e8", "#f0f0e8"],
    "medieval": ["#4a3728", "#6b5040", "#8b7355", "#a08060", "#2a1a0a", "#c4a060"],
    "space": ["#0a0a1a", "#1a1a3a", "#2a2a5a", "#4a4a8a", "#6a6aaa", "#aaaaee"],
    "cyberpunk": ["#0d0221", "#1a0553", "#3a0ca3", "#7209b7", "#f72585", "#4cc9f0"],
    "sunset": ["#2d1b69", "#e05a47", "#f48847", "#f5ce47", "#4a2080", "#c06bae"],
    "underwater": ["#001a33", "#003366", "#006699", "#0099cc", "#003355", "#66ccff"],
    "toxic": ["#1a2a0a", "#3a5a1a", "#6aaa2a", "#8aca3a", "#0a1a00", "#aaea4a"],
    "magical": ["#1a0a2e", "#4a1a6a", "#7a3aaa", "#aa5aea", "#0a0a1a", "#dac0ff"],
    "industrial": ["#2a2a2a", "#4a4a4a", "#6a6a6a", "#8a8a8a", "#1a1a1a", "#aaaaaa"],
    "candy": ["#ff6b9d", "#c44dff", "#4ecdc4", "#ffe66d", "#ff8a80", "#b388ff"],
    "horror": ["#0a0a0a", "#1a0a0a", "#2a0000", "#4a0000", "#0a0000", "#6a0a0a"],
    "retro": ["#000000", "#ffffff", "#ff0000", "#00ff00", "#0000ff", "#ffff00"],
    "monochrome": ["#000000", "#333333", "#666666", "#999999", "#cccccc", "#ffffff"],
    "autumn": ["#4a2a0a", "#8b4513", "#cd853f", "#deb887", "#2a1a0a", "#f4a460"],
}


def _generate_palette_id() -> str:
    return uuid.uuid4().hex[:12]


def _simulate_generation_time_ms(
    category: AssetCategory, style: GenerationStyle
) -> float:
    base_times: Dict[str, float] = {
        "sprite": 120.0,
        "tileset": 250.0,
        "ui_element": 80.0,
        "sound_effect": 200.0,
        "background": 300.0,
        "character": 350.0,
        "prop": 150.0,
        "effect": 180.0,
    }
    style_multipliers: Dict[str, float] = {
        "pixel_art": 1.0,
        "vector": 0.8,
        "sketch": 0.6,
        "realistic": 1.5,
        "cartoon": 0.9,
        "minimalist": 0.5,
        "fantasy": 1.2,
        "sci_fi": 1.3,
    }
    base = base_times.get(category.value, 150.0)
    multiplier = style_multipliers.get(style.value, 1.0)
    variation = 0.85 + (_time_module.time() % 0.3)
    return round(base * multiplier * variation, 2)


def _estimate_asset_size_bytes(
    category: AssetCategory, format: OutputFormat
) -> int:
    size_table: Dict[str, Dict[str, int]] = {
        "sprite": {"png_sheet": 4096, "svg": 2048, "json_descriptor": 1024,
                     "audio_wav": 0, "sprite_atlas": 8192},
        "tileset": {"png_sheet": 16384, "svg": 8192, "json_descriptor": 2048,
                     "audio_wav": 0, "sprite_atlas": 32768},
        "ui_element": {"png_sheet": 2048, "svg": 1024, "json_descriptor": 512,
                        "audio_wav": 0, "sprite_atlas": 4096},
        "sound_effect": {"png_sheet": 0, "svg": 0, "json_descriptor": 512,
                          "audio_wav": 32768, "sprite_atlas": 0},
        "background": {"png_sheet": 65536, "svg": 16384, "json_descriptor": 2048,
                        "audio_wav": 0, "sprite_atlas": 0},
        "character": {"png_sheet": 32768, "svg": 8192, "json_descriptor": 4096,
                       "audio_wav": 0, "sprite_atlas": 65536},
        "prop": {"png_sheet": 8192, "svg": 4096, "json_descriptor": 1024,
                  "audio_wav": 0, "sprite_atlas": 16384},
        "effect": {"png_sheet": 16384, "svg": 4096, "json_descriptor": 1024,
                    "audio_wav": 65536, "sprite_atlas": 32768},
    }
    return size_table.get(category.value, {}).get(format.value, 1024)


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------


@dataclass
class AssetSpec:
    """Specification describing an asset to be generated."""

    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = ""
    category: AssetCategory = AssetCategory.SPRITE
    description: str = ""
    dimensions: Dict[str, int] = field(default_factory=lambda: {
        "width": 64,
        "height": 64,
    })
    color_palette: List[str] = field(default_factory=list)
    style: GenerationStyle = GenerationStyle.PIXEL_ART
    tags: List[str] = field(default_factory=list)
    created_at: float = field(default_factory=_time_module.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "category": self.category.value,
            "description": self.description,
            "dimensions": dict(self.dimensions),
            "color_palette": list(self.color_palette),
            "style": self.style.value,
            "tags": list(self.tags),
            "created_at": self.created_at,
        }


@dataclass
class SynthesisResult:
    """Result of an asset synthesis operation."""

    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    spec_id: str = ""
    generated_assets: List[str] = field(default_factory=list)
    preview_url: str = ""
    format: OutputFormat = OutputFormat.PNG_SHEET
    generation_time_ms: float = 0.0
    created_at: float = field(default_factory=_time_module.time)
    mode: SynthesisMode = SynthesisMode.SINGLE_ASSET

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "spec_id": self.spec_id,
            "generated_assets": list(self.generated_assets),
            "preview_url": self.preview_url,
            "format": self.format.value,
            "generation_time_ms": self.generation_time_ms,
            "created_at": self.created_at,
            "mode": self.mode.value,
        }


@dataclass
class AssetPack:
    """A themed collection of synthesized assets."""

    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = ""
    theme: str = ""
    assets: List[AssetSpec] = field(default_factory=list)
    style_consistency_score: float = 0.0
    total_size_bytes: int = 0
    created_at: float = field(default_factory=_time_module.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "theme": self.theme,
            "asset_count": len(self.assets),
            "assets": [a.to_dict() for a in self.assets],
            "style_consistency_score": self.style_consistency_score,
            "total_size_bytes": self.total_size_bytes,
            "created_at": self.created_at,
        }


# ---------------------------------------------------------------------------
# Asset Synthesizer (Singleton)
# ---------------------------------------------------------------------------


class AssetSynthesizer:
    """Singleton system for AI-powered procedural asset generation.

    Given text descriptions, generates complete asset packs including sprite
    definitions, material configurations, sound descriptors, and animation data
    for the AI-native game engine. Thread-safe via a reentrant lock.
    """

    _instance: Optional["AssetSynthesizer"] = None
    _lock: threading.RLock = threading.RLock()

    def __new__(cls) -> "AssetSynthesizer":
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
        self._asset_templates: Dict[str, AssetSpec] = {}
        self._generated_assets: Dict[str, SynthesisResult] = {}
        self._style_presets: Dict[str, Dict[str, Any]] = {}
        self._stats: Dict[str, Any] = {
            "total_synthesis_calls": 0,
            "total_packs_generated": 0,
            "total_variations_created": 0,
            "total_style_transfers": 0,
            "total_generation_time_ms": 0.0,
            "by_category": {c.value: 0 for c in AssetCategory},
            "by_style": {s.value: 0 for s in GenerationStyle},
            "by_format": {f.value: 0 for f in OutputFormat},
        }
        self._register_default_templates()
        self._register_default_presets()
        self._initialized = True

    # ------------------------------------------------------------------
    # Singleton Accessor
    # ------------------------------------------------------------------

    @classmethod
    def get_instance(cls) -> "AssetSynthesizer":
        """Return the singleton AssetSynthesizer instance."""
        return cls()

    # ------------------------------------------------------------------
    # Default Registration
    # ------------------------------------------------------------------

    def _register_default_templates(self) -> None:
        defaults: List[Dict[str, Any]] = [
            {
                "name": "player_character",
                "category": AssetCategory.CHARACTER,
                "description": "Default player character sprite",
                "dimensions": {"width": 64, "height": 64},
                "color_palette": ["#ff0000", "#0000ff", "#ffffff", "#000000"],
                "style": GenerationStyle.PIXEL_ART,
                "tags": ["player", "default", "character"],
            },
            {
                "name": "grass_tile",
                "category": AssetCategory.TILESET,
                "description": "Green grass terrain tile",
                "dimensions": {"width": 32, "height": 32},
                "color_palette": ["#2d5a27", "#4a8c3f", "#8fbc6b"],
                "style": GenerationStyle.PIXEL_ART,
                "tags": ["terrain", "tile", "grass"],
            },
            {
                "name": "start_button",
                "category": AssetCategory.UI_ELEMENT,
                "description": "Start button for main menu",
                "dimensions": {"width": 200, "height": 60},
                "color_palette": ["#4a90d9", "#ffffff", "#2a6099"],
                "style": GenerationStyle.MINIMALIST,
                "tags": ["ui", "button", "menu"],
            },
            {
                "name": "jump_sound",
                "category": AssetCategory.SOUND_EFFECT,
                "description": "Cartoon jump sound effect",
                "dimensions": {},
                "color_palette": [],
                "style": GenerationStyle.CARTOON,
                "tags": ["sfx", "jump", "movement"],
            },
            {
                "name": "sky_background",
                "category": AssetCategory.BACKGROUND,
                "description": "Blue sky with clouds parallax background",
                "dimensions": {"width": 1920, "height": 1080},
                "color_palette": ["#87ceeb", "#ffffff", "#b0c4de"],
                "style": GenerationStyle.VECTOR,
                "tags": ["background", "sky", "parallax"],
            },
            {
                "name": "coin_prop",
                "category": AssetCategory.PROP,
                "description": "Spinning gold coin collectible",
                "dimensions": {"width": 16, "height": 16},
                "color_palette": ["#ffd700", "#daa520", "#b8860b"],
                "style": GenerationStyle.PIXEL_ART,
                "tags": ["prop", "collectible", "coin"],
            },
            {
                "name": "explosion_effect",
                "category": AssetCategory.EFFECT,
                "description": "Particle explosion effect with fire and smoke",
                "dimensions": {"width": 128, "height": 128},
                "color_palette": ["#ff4500", "#ff8c00", "#ffd700", "#808080"],
                "style": GenerationStyle.CARTOON,
                "tags": ["effect", "explosion", "particle"],
            },
            {
                "name": "enemy_slime",
                "category": AssetCategory.CHARACTER,
                "description": "Green slime enemy with bouncing animation",
                "dimensions": {"width": 32, "height": 28},
                "color_palette": ["#32cd32", "#228b22", "#006400"],
                "style": GenerationStyle.PIXEL_ART,
                "tags": ["enemy", "character", "slime"],
            },
        ]
        for template in defaults:
            spec = AssetSpec(
                name=template["name"],
                category=template["category"],
                description=template["description"],
                dimensions=template["dimensions"],
                color_palette=template["color_palette"],
                style=template["style"],
                tags=template["tags"],
            )
            self._asset_templates[spec.id] = spec

    def _register_default_presets(self) -> None:
        default_presets: Dict[str, Dict[str, Any]] = {
            "pixel_perfect": {
                "antialiasing": False,
                "interpolation": "nearest",
                "palette_size": 32,
                "dithering": "none",
                "scale_mode": "integer",
            },
            "hd_ready": {
                "antialiasing": True,
                "interpolation": "bilinear",
                "palette_size": 256,
                "dithering": "floyd_steinberg",
                "scale_mode": "smooth",
            },
            "mobile_optimized": {
                "antialiasing": False,
                "interpolation": "nearest",
                "palette_size": 16,
                "dithering": "ordered",
                "scale_mode": "power_of_two",
            },
            "vector_clean": {
                "antialiasing": True,
                "interpolation": "bicubic",
                "palette_size": 0,
                "dithering": "none",
                "scale_mode": "any",
            },
        }
        for name, params in default_presets.items():
            preset_id = _generate_palette_id()
            self._style_presets[preset_id] = {
                "name": name,
                "parameters": params,
                "created_at": _time_module.time(),
            }

    # ------------------------------------------------------------------
    # Primary Synthesis API
    # ------------------------------------------------------------------

    def synthesize_asset(
        self,
        description: str,
        category: AssetCategory = AssetCategory.SPRITE,
        style: GenerationStyle = GenerationStyle.PIXEL_ART,
        dimensions: Optional[Dict[str, int]] = None,
        palette: Optional[List[str]] = None,
        output_format: OutputFormat = OutputFormat.PNG_SHEET,
    ) -> SynthesisResult:
        """Generate a single asset from a text description.

        Args:
            description: Natural language description of the desired asset.
            category: The category of asset to generate.
            style: The visual style to apply.
            dimensions: Optional width/height dict. Defaults to 64x64.
            palette: Optional color palette. Auto-suggested if None.
            output_format: Desired output format.

        Returns:
            A SynthesisResult containing the generated asset metadata.
        """
        with self._lock:
            spec = AssetSpec(
                name=description[:64].strip() or "unnamed_asset",
                category=category,
                description=description,
                dimensions=dimensions or {"width": 64, "height": 64},
                color_palette=palette or self.suggest_palette(description),
                style=style,
                tags=self._extract_tags(description, category),
            )

            gen_time = _simulate_generation_time_ms(category, style)
            result = SynthesisResult(
                spec_id=spec.id,
                generated_assets=[
                    f"asset_{spec.id[:8]}_{output_format.value}.{self._format_extension(output_format)}"
                ],
                preview_url=f"/previews/{spec.id[:12]}_{category.value}.png",
                format=output_format,
                generation_time_ms=gen_time,
                mode=SynthesisMode.SINGLE_ASSET,
            )

            self._generated_assets[result.id] = result
            self._update_stats(category, style, output_format, gen_time)

            return result

    def generate_asset_pack(
        self,
        theme: str,
        categories: Optional[List[AssetCategory]] = None,
        style: GenerationStyle = GenerationStyle.PIXEL_ART,
        output_format: OutputFormat = OutputFormat.PNG_SHEET,
    ) -> AssetPack:
        """Generate a themed collection of assets as a complete pack.

        Args:
            theme: The unifying theme for all assets in the pack.
            categories: List of asset categories to include. Uses all if None.
            style: The visual style applied to all assets in the pack.
            output_format: Desired output format for generated assets.

        Returns:
            An AssetPack containing all synthesized assets for the theme.
        """
        with self._lock:
            target_categories = categories or list(AssetCategory)
            pack_assets: List[AssetSpec] = []
            total_size = 0
            palette = self.suggest_palette(theme)
            generation_index = 0

            for cat in target_categories:
                generation_index += 1
                desc = self._theme_description(theme, cat, generation_index)
                spec = AssetSpec(
                    name=f"{theme}_{cat.value}_{generation_index:02d}",
                    category=cat,
                    description=desc,
                    dimensions=self._default_dimensions(cat),
                    color_palette=palette,
                    style=style,
                    tags=self._extract_tags(desc, cat),
                )
                pack_assets.append(spec)

                gen_time = _simulate_generation_time_ms(cat, style)
                result = SynthesisResult(
                    spec_id=spec.id,
                    generated_assets=[
                        f"pack_{theme}_{cat.value}_{spec.id[:8]}.{self._format_extension(output_format)}"
                    ],
                    preview_url=f"/previews/pack_{theme}_{cat.value}.png",
                    format=output_format,
                    generation_time_ms=gen_time,
                    mode=SynthesisMode.ASSET_PACK,
                )
                self._generated_assets[result.id] = result
                self._update_stats(cat, style, output_format, gen_time)

                est_size = _estimate_asset_size_bytes(cat, output_format)
                total_size += est_size

            consistency_score = self._compute_consistency_score(
                pack_assets, palette, style
            )

            pack = AssetPack(
                name=f"{theme.title()} Asset Pack",
                theme=theme,
                assets=pack_assets,
                style_consistency_score=consistency_score,
                total_size_bytes=total_size,
            )
            self._stats["total_packs_generated"] += 1

            return pack

    def create_variations(
        self,
        base_spec: AssetSpec,
        count: int = 3,
        variation_strength: float = 0.3,
    ) -> List[SynthesisResult]:
        """Create multiple variations of a base asset specification.

        Args:
            base_spec: The source asset specification to vary.
            count: Number of variations to generate.
            variation_strength: How much each variation differs (0.0 to 1.0).

        Returns:
            List of SynthesisResult objects, one per variation.
        """
        with self._lock:
            variations: List[SynthesisResult] = []
            clamped_count = max(1, min(count, 20))
            clamped_strength = max(0.05, min(variation_strength, 1.0))

            for i in range(clamped_count):
                variant_seed = (
                    _time_module.time() + sum(ord(c) for c in base_spec.id) + i
                )
                hue_shift = int((variant_seed * 137) % 360)
                sat_shift = (variant_seed * 73) % 100 / 100.0

                shifted_palette = self._shift_palette(
                    base_spec.color_palette,
                    hue_shift,
                    sat_shift,
                    clamped_strength,
                )

                dim_variation = int(clamped_strength * 16 * (i + 1))
                variant_dims = {
                    "width": max(8, base_spec.dimensions.get("width", 64) + dim_variation * ((i % 3) - 1)),
                    "height": max(8, base_spec.dimensions.get("height", 64) + dim_variation * ((i % 2) - 1)),
                }

                variant_spec = AssetSpec(
                    name=f"{base_spec.name}_variant_{i + 1:02d}",
                    category=base_spec.category,
                    description=f"Variation {i + 1} of: {base_spec.description}",
                    dimensions=variant_dims,
                    color_palette=shifted_palette,
                    style=base_spec.style,
                    tags=base_spec.tags + [f"variant_{i + 1}"],
                )

                gen_time = _simulate_generation_time_ms(
                    variant_spec.category, variant_spec.style
                ) * 0.6

                format = OutputFormat.PNG_SHEET
                result = SynthesisResult(
                    spec_id=variant_spec.id,
                    generated_assets=[
                        f"variant_{base_spec.id[:8]}_{i + 1:02d}.{self._format_extension(format)}"
                    ],
                    preview_url=f"/previews/variant_{base_spec.id[:12]}_{i + 1:02d}.png",
                    format=format,
                    generation_time_ms=gen_time,
                    mode=SynthesisMode.VARIATION_SET,
                )

                self._generated_assets[result.id] = result
                self._update_stats(
                    variant_spec.category, variant_spec.style, format, gen_time
                )
                variations.append(result)

            self._stats["total_variations_created"] += clamped_count
            return variations

    def define_style_preset(
        self,
        name: str,
        parameters: Dict[str, Any],
    ) -> str:
        """Register a named style preset with generation parameters.

        Args:
            name: Unique name for this preset.
            parameters: Key-value pairs defining rendering parameters.

        Returns:
            The preset_id string for the registered preset.
        """
        with self._lock:
            for preset in self._style_presets.values():
                if preset["name"] == name:
                    return ""

            preset_id = _generate_palette_id()
            self._style_presets[preset_id] = {
                "name": name,
                "parameters": dict(parameters),
                "created_at": _time_module.time(),
            }
            return preset_id

    def apply_style_transfer(
        self,
        source_spec: AssetSpec,
        target_style: GenerationStyle,
    ) -> SynthesisResult:
        """Transfer the visual style of an existing asset to a different style.

        Args:
            source_spec: The source asset to restyle.
            target_style: The destination visual style.

        Returns:
            A SynthesisResult for the style-transferred asset.
        """
        with self._lock:
            transferred_spec = AssetSpec(
                name=f"{source_spec.name}_{target_style.value}",
                category=source_spec.category,
                description=f"{source_spec.description} (style transfer to {target_style.value})",
                dimensions=dict(source_spec.dimensions),
                color_palette=list(source_spec.color_palette),
                style=target_style,
                tags=source_spec.tags + [f"style:{target_style.value}"],
            )

            gen_time = _simulate_generation_time_ms(
                source_spec.category, target_style
            ) * 0.7

            format = OutputFormat.PNG_SHEET
            result = SynthesisResult(
                spec_id=transferred_spec.id,
                generated_assets=[
                    f"transfer_{source_spec.id[:8]}_to_{target_style.value}.{self._format_extension(format)}"
                ],
                preview_url=f"/previews/transfer_{source_spec.id[:12]}_{target_style.value}.png",
                format=format,
                generation_time_ms=gen_time,
                mode=SynthesisMode.SINGLE_ASSET,
            )

            self._generated_assets[result.id] = result
            self._stats["total_style_transfers"] += 1
            self._update_stats(
                source_spec.category, target_style, format, gen_time
            )

            return result

    def suggest_palette(self, theme: str) -> List[str]:
        """Suggest a color palette based on a theme description.

        Args:
            theme: Theme string or description to base colors on.

        Returns:
            A list of hex color strings forming the suggested palette.
        """
        theme_lower = theme.lower()
        for key, palette in _THEME_PALETTES.items():
            if key in theme_lower:
                return list(palette)

        topic_matches: Dict[str, List[str]] = {
            "forest": ["forest", "wood", "tree", "jungle", "nature", "green", "leaf"],
            "ocean": ["ocean", "sea", "water", "marine", "blue", "wave", "beach"],
            "desert": ["desert", "sand", "arid", "dry", "cactus", "dune"],
            "snow": ["snow", "ice", "frozen", "cold", "winter", "frost", "arctic"],
            "lava": ["lava", "fire", "flame", "volcano", "magma", "inferno", "heat"],
            "neon": ["neon", "glow", "light", "bright", "vivid", "flash", "laser"],
            "space": ["space", "star", "galaxy", "cosmic", "planet", "moon", "orbit"],
            "medieval": ["medieval", "castle", "knight", "stone", "old", "ancient", "relic"],
            "cyberpunk": ["cyber", "tech", "digital", "future", "hack", "circuit", "grid"],
            "horror": ["horror", "dark", "shadow", "gloom", "spooky", "creepy", "ghost"],
        }

        for palette_key, keywords in topic_matches.items():
            for kw in keywords:
                if kw in theme_lower:
                    return list(_THEME_PALETTES[palette_key])

        return list(_THEME_PALETTES["pastel"])

    def get_stats(self) -> Dict[str, Any]:
        """Return synthesis statistics and operational metrics.

        Returns:
            A dictionary of accumulated statistics.
        """
        with self._lock:
            return {
                "total_synthesis_calls": self._stats["total_synthesis_calls"],
                "total_packs_generated": self._stats["total_packs_generated"],
                "total_variations_created": self._stats["total_variations_created"],
                "total_style_transfers": self._stats["total_style_transfers"],
                "total_generation_time_ms": self._stats["total_generation_time_ms"],
                "by_category": dict(self._stats["by_category"]),
                "by_style": dict(self._stats["by_style"]),
                "by_format": dict(self._stats["by_format"]),
                "generated_asset_count": len(self._generated_assets),
                "template_count": len(self._asset_templates),
                "preset_count": len(self._style_presets),
            }

    # ------------------------------------------------------------------
    # Query Methods
    # ------------------------------------------------------------------

    def get_result(self, result_id: str) -> Optional[SynthesisResult]:
        with self._lock:
            return self._generated_assets.get(result_id)

    def get_template(self, template_id: str) -> Optional[AssetSpec]:
        with self._lock:
            return self._asset_templates.get(template_id)

    def list_templates(
        self,
        category: Optional[AssetCategory] = None,
    ) -> List[Dict[str, Any]]:
        with self._lock:
            templates = list(self._asset_templates.values())
            if category:
                templates = [t for t in templates if t.category == category]
            templates.sort(key=lambda t: t.created_at, reverse=True)
            return [t.to_dict() for t in templates]

    def list_results(
        self,
        mode: Optional[SynthesisMode] = None,
    ) -> List[Dict[str, Any]]:
        with self._lock:
            results = list(self._generated_assets.values())
            if mode:
                results = [r for r in results if r.mode == mode]
            results.sort(key=lambda r: r.created_at, reverse=True)
            return [r.to_dict() for r in results]

    def list_style_presets(self) -> List[Dict[str, Any]]:
        with self._lock:
            return [
                {
                    "preset_id": pid,
                    "name": preset["name"],
                    "parameters": dict(preset["parameters"]),
                    "created_at": preset["created_at"],
                }
                for pid, preset in self._style_presets.items()
            ]

    # ------------------------------------------------------------------
    # Internal Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _format_extension(format: OutputFormat) -> str:
        extensions: Dict[OutputFormat, str] = {
            OutputFormat.PNG_SHEET: "png",
            OutputFormat.SVG: "svg",
            OutputFormat.JSON_DESCRIPTOR: "json",
            OutputFormat.AUDIO_WAV: "wav",
            OutputFormat.SPRITE_ATLAS: "atlas.json",
        }
        return extensions.get(format, "png")

    @staticmethod
    def _default_dimensions(category: AssetCategory) -> Dict[str, int]:
        defaults: Dict[AssetCategory, Dict[str, int]] = {
            AssetCategory.SPRITE: {"width": 64, "height": 64},
            AssetCategory.TILESET: {"width": 32, "height": 32},
            AssetCategory.UI_ELEMENT: {"width": 200, "height": 60},
            AssetCategory.SOUND_EFFECT: {},
            AssetCategory.BACKGROUND: {"width": 1920, "height": 1080},
            AssetCategory.CHARACTER: {"width": 64, "height": 64},
            AssetCategory.PROP: {"width": 32, "height": 32},
            AssetCategory.EFFECT: {"width": 128, "height": 128},
        }
        return dict(defaults.get(category, {"width": 64, "height": 64}))

    @staticmethod
    def _extract_tags(
        description: str, category: AssetCategory
    ) -> List[str]:
        tags = [category.value]
        words = description.lower().split()
        common_tags: Dict[str, List[str]] = {
            "player": ["player", "hero", "protagonist", "character"],
            "enemy": ["enemy", "foe", "boss", "villain", "monster"],
            "terrain": ["terrain", "ground", "floor", "platform", "tile"],
            "ui": ["ui", "menu", "button", "panel", "hud", "interface"],
            "collectible": ["coin", "gem", "item", "pickup", "collectible"],
            "particle": ["particle", "spark", "dust", "smoke", "trail"],
            "weapon": ["weapon", "sword", "gun", "bow", "staff", "axe"],
            "magic": ["magic", "spell", "mana", "arcane", "elemental"],
            "nature": ["tree", "plant", "flower", "bush", "grass", "rock"],
            "building": ["building", "house", "wall", "door", "window"],
        }
        for tag_name, keywords in common_tags.items():
            if any(kw in words for kw in keywords):
                tags.append(tag_name)
        return tags

    @staticmethod
    def _theme_description(
        theme: str, category: AssetCategory, index: int
    ) -> str:
        templates: Dict[AssetCategory, str] = {
            AssetCategory.CHARACTER: "{theme} character asset {index}",
            AssetCategory.SPRITE: "{theme} sprite asset {index}",
            AssetCategory.TILESET: "{theme} tileset element {index}",
            AssetCategory.UI_ELEMENT: "{theme} UI element {index}",
            AssetCategory.SOUND_EFFECT: "{theme} sound effect {index}",
            AssetCategory.BACKGROUND: "{theme} background scene {index}",
            AssetCategory.PROP: "{theme} prop object {index}",
            AssetCategory.EFFECT: "{theme} special effect {index}",
        }
        template = templates.get(category, "{theme} asset {index}")
        return template.format(theme=theme, index=index)

    @staticmethod
    def _shift_palette(
        palette: List[str],
        hue_shift: int,
        sat_shift: float,
        strength: float,
    ) -> List[str]:
        if not palette:
            return palette
        shifted: List[str] = []
        for color in palette:
            shifted.append(_shift_hex_color(color, hue_shift, sat_shift, strength))
        return shifted

    @staticmethod
    def _compute_consistency_score(
        assets: List[AssetSpec],
        palette: List[str],
        style: GenerationStyle,
    ) -> float:
        if not assets:
            return 0.0
        same_style_count = sum(
            1 for a in assets if a.style == style
        )
        style_score = same_style_count / len(assets)
        palette_score = 0.0
        for a in assets:
            if a.color_palette:
                common = len(set(a.color_palette) & set(palette))
                total = len(set(a.color_palette) | set(palette))
                if total > 0:
                    palette_score += common / total
        palette_score = palette_score / len(assets) if assets else 0.0
        return round(0.6 * style_score + 0.4 * palette_score, 4)

    def _update_stats(
        self,
        category: AssetCategory,
        style: GenerationStyle,
        format: OutputFormat,
        gen_time_ms: float,
    ) -> None:
        self._stats["total_synthesis_calls"] += 1
        self._stats["total_generation_time_ms"] += gen_time_ms
        self._stats["by_category"][category.value] += 1
        self._stats["by_style"][style.value] += 1
        self._stats["by_format"][format.value] += 1


# ---------------------------------------------------------------------------
# Color Utility
# ---------------------------------------------------------------------------


def _shift_hex_color(
    hex_color: str,
    hue_shift: int,
    sat_shift: float,
    strength: float,
) -> str:
    clean = hex_color.lstrip("#")
    if len(clean) != 6:
        return hex_color
    try:
        r = int(clean[0:2], 16)
        g = int(clean[2:4], 16)
        b = int(clean[4:6], 16)
    except ValueError:
        return hex_color

    h, s, v = _rgb_to_hsv(r, g, b)
    h = (h + hue_shift * strength) % 360
    s = max(0.0, min(1.0, s + (sat_shift - 0.5) * strength * 2.0))
    nr, ng, nb = _hsv_to_rgb(h, s, v)
    return f"#{int(nr):02x}{int(ng):02x}{int(nb):02x}"


def _rgb_to_hsv(r: int, g: int, b: int) -> tuple:
    rf, gf, bf = r / 255.0, g / 255.0, b / 255.0
    cmax = max(rf, gf, bf)
    cmin = min(rf, gf, bf)
    delta = cmax - cmin

    if delta == 0:
        h = 0.0
    elif cmax == rf:
        h = 60.0 * (((gf - bf) / delta) % 6)
    elif cmax == gf:
        h = 60.0 * (((bf - rf) / delta) + 2)
    else:
        h = 60.0 * (((rf - gf) / delta) + 4)

    s = 0.0 if cmax == 0 else delta / cmax
    v = cmax
    return (h, s, v)


def _hsv_to_rgb(h: float, s: float, v: float) -> tuple:
    c = v * s
    x = c * (1 - abs((h / 60.0) % 2 - 1))
    m = v - c

    if h < 60:
        rf, gf, bf = c, x, 0.0
    elif h < 120:
        rf, gf, bf = x, c, 0.0
    elif h < 180:
        rf, gf, bf = 0.0, c, x
    elif h < 240:
        rf, gf, bf = 0.0, x, c
    elif h < 300:
        rf, gf, bf = x, 0.0, c
    else:
        rf, gf, bf = c, 0.0, x

    return ((rf + m) * 255.0, (gf + m) * 255.0, (bf + m) * 255.0)


# ---------------------------------------------------------------------------
# Module-Level Accessor
# ---------------------------------------------------------------------------


def get_asset_synthesizer() -> AssetSynthesizer:
    """Module-level accessor for the AssetSynthesizer singleton.

    Convenience function that returns the singleton instance without
    needing to reference AssetSynthesizer.get_instance() directly.

    Returns:
        The singleton AssetSynthesizer instance.
    """
    return AssetSynthesizer.get_instance()