"""
SparkLabs Agent - Theme Designer

AI-powered theme and style generation system for game interfaces.
Generates complete design token sets including colors, typography,
spacing, rounding, shadows, borders, transitions, and icons from
natural language descriptions and mood specifications.

Architecture:
  ThemeDesigner
    |-- Color Extractor (image description → color token generation)
    |-- Typography Composer (mood-aware font stack assembly)
    |-- Spacing Calculator (rhythmic scale generation)
    |-- Mood Interpreter (mood keyword → design parameter mapping)
    |-- Theme Blender (weighted interpolation between two themes)
    |-- CSS Exporter (design token → CSS custom properties)

Supports 10 distinct mood categories for diverse visual styles.
"""

from __future__ import annotations

import colorsys
import math
import threading
import time
import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class ThemeCategory(Enum):
    COLORS = "colors"
    TYPOGRAPHY = "typography"
    SPACING = "spacing"
    ROUNDING = "rounding"
    SHADOWS = "shadows"
    BORDERS = "borders"
    TRANSITIONS = "transitions"
    ICONS = "icons"


class StyleMood(Enum):
    DARK = "dark"
    LIGHT = "light"
    NEON = "neon"
    RETRO = "retro"
    MINIMAL = "minimal"
    BRUTALIST = "brutalist"
    ORGANIC = "organic"
    CORPORATE = "corporate"
    FANTASY = "fantasy"
    SCIFI = "scifi"


MOOD_COLOR_PALETTES: Dict[StyleMood, Dict[str, str]] = {
    StyleMood.DARK: {
        "primary": "#6C63FF", "secondary": "#3F3D56", "background": "#1E1E2E",
        "surface": "#2A2A3C", "text": "#E0E0E0", "accent": "#FF6584",
    },
    StyleMood.LIGHT: {
        "primary": "#4A90D9", "secondary": "#F5F5F5", "background": "#FFFFFF",
        "surface": "#F0F0F0", "text": "#333333", "accent": "#E8734A",
    },
    StyleMood.NEON: {
        "primary": "#FF00FF", "secondary": "#00FFFF", "background": "#0D0D0D",
        "surface": "#1A1A2E", "text": "#FFFFFF", "accent": "#FFFF00",
    },
    StyleMood.RETRO: {
        "primary": "#FF6B35", "secondary": "#004E89", "background": "#F7EDE2",
        "surface": "#F5CAC3", "text": "#2D2D2D", "accent": "#F6BD60",
    },
    StyleMood.MINIMAL: {
        "primary": "#000000", "secondary": "#F8F8F8", "background": "#FFFFFF",
        "surface": "#F5F5F5", "text": "#1A1A1A", "accent": "#666666",
    },
    StyleMood.BRUTALIST: {
        "primary": "#FF0000", "secondary": "#000000", "background": "#FFFFFF",
        "surface": "#EEEEEE", "text": "#000000", "accent": "#0000FF",
    },
    StyleMood.ORGANIC: {
        "primary": "#4A7C59", "secondary": "#8B5E3C", "background": "#F5F0E8",
        "surface": "#E8D5B7", "text": "#2C1810", "accent": "#C9A96E",
    },
    StyleMood.CORPORATE: {
        "primary": "#003366", "secondary": "#E5E5E5", "background": "#FFFFFF",
        "surface": "#F8F9FA", "text": "#212529", "accent": "#0066CC",
    },
    StyleMood.FANTASY: {
        "primary": "#7B2D8E", "secondary": "#D4A843", "background": "#1A0F2E",
        "surface": "#2D1B4E", "text": "#E8D5C4", "accent": "#4ECDC4",
    },
    StyleMood.SCIFI: {
        "primary": "#00D4FF", "secondary": "#1A1A2E", "background": "#0A0A1A",
        "surface": "#16213E", "text": "#A0D2DB", "accent": "#E94560",
    },
}


@dataclass
class ColorToken:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = ""
    hex_value: str = "#000000"
    opacity: float = 1.0
    usage_description: str = ""
    category: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "hex_value": self.hex_value,
            "opacity": round(self.opacity, 2),
            "usage_description": self.usage_description[:80],
            "category": self.category,
        }


@dataclass
class TypographyToken:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = ""
    font_family: str = "Inter, sans-serif"
    size: int = 16
    weight: int = 400
    line_height: float = 1.5
    letter_spacing: float = 0.0
    usage: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "font_family": self.font_family,
            "size": self.size,
            "weight": self.weight,
            "line_height": self.line_height,
            "letter_spacing": self.letter_spacing,
            "usage": self.usage,
        }

    def css_value(self) -> str:
        return (
            f"{self.weight} {self.size}px/{self.line_height} "
            f"'{self.font_family}', sans-serif; "
            f"letter-spacing: {self.letter_spacing}px"
        )


@dataclass
class ThemeDefinition:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = ""
    mood: StyleMood = StyleMood.DARK
    color_tokens: List[ColorToken] = field(default_factory=list)
    typography: List[TypographyToken] = field(default_factory=list)
    spacing_scale: List[float] = field(default_factory=lambda: [0, 4, 8, 12, 16, 24, 32, 48, 64, 96])
    border_radius_scale: List[int] = field(default_factory=lambda: [0, 4, 8, 12, 16, 24, 32])
    shadow_presets: List[dict] = field(default_factory=list)
    generated_from: str = ""
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "mood": self.mood.value,
            "color_tokens_count": len(self.color_tokens),
            "typography_count": len(self.typography),
            "spacing_scale": self.spacing_scale,
            "border_radius_scale": self.border_radius_scale,
            "shadow_presets_count": len(self.shadow_presets),
            "generated_from": self.generated_from[:100],
        }

    def to_full_dict(self) -> Dict[str, Any]:
        result = self.to_dict()
        result["color_tokens"] = [t.to_dict() for t in self.color_tokens]
        result["typography"] = [t.to_dict() for t in self.typography]
        result["shadow_presets"] = self.shadow_presets
        return result


class ThemeDesigner:
    """AI theme and style generation system for game interfaces."""

    _instance: Optional["ThemeDesigner"] = None
    _lock = threading.Lock()

    MAX_THEMES = 100

    MOOD_FONT_PAIRS: Dict[StyleMood, List[str]] = {
        StyleMood.DARK: ["Inter", "JetBrains Mono"],
        StyleMood.LIGHT: ["Inter", "Source Sans Pro"],
        StyleMood.NEON: ["Orbitron", "Rajdhani"],
        StyleMood.RETRO: ["Press Start 2P", "VT323"],
        StyleMood.MINIMAL: ["Inter", "Helvetica Neue"],
        StyleMood.BRUTALIST: ["Courier New", "Impact"],
        StyleMood.ORGANIC: ["Georgia", "Merriweather"],
        StyleMood.CORPORATE: ["Roboto", "Open Sans"],
        StyleMood.FANTASY: ["Cinzel", "Lora"],
        StyleMood.SCIFI: ["Orbitron", "Share Tech Mono"],
    }

    def __init__(self):
        self._themes: Dict[str, ThemeDefinition] = {}
        self._themes_generated: int = 0

    @classmethod
    def get_instance(cls) -> "ThemeDesigner":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def generate_theme(
        self, description: str, mood: StyleMood
    ) -> ThemeDefinition:
        palette = MOOD_COLOR_PALETTES.get(mood, MOOD_COLOR_PALETTES[StyleMood.DARK])
        fonts = self.MOOD_FONT_PAIRS.get(mood, ["Inter", "sans-serif"])

        color_tokens: List[ColorToken] = []
        for role, hex_val in palette.items():
            token = ColorToken(
                name=f"{mood.value}-{role}",
                hex_value=hex_val,
                opacity=1.0,
                usage_description=f"{role} color for {mood.value} theme",
                category=role,
            )
            color_tokens.append(token)

        desc_lower = description.lower()
        if any(w in desc_lower for w in ["gradient", "fade", "blend", "smooth"]):
            surface_color = palette.get("surface", "#F5F5F5")
            for i in range(3):
                lighter = self._adjust_hex_brightness(surface_color, 1.0 + i * 0.15)
                token = ColorToken(
                    name=f"{mood.value}-surface-{i}",
                    hex_value=lighter,
                    opacity=0.9,
                    usage_description=f"Surface variant {i}",
                    category="surface_variant",
                )
                color_tokens.append(token)

        typography_tokens: List[TypographyToken] = []
        type_scale = [
            ("heading-1", 48, 700, 1.1, -0.5, "Page title"),
            ("heading-2", 36, 600, 1.2, -0.3, "Section heading"),
            ("heading-3", 28, 600, 1.3, -0.1, "Subsection heading"),
            ("body-large", 20, 400, 1.6, 0.0, "Body text large"),
            ("body", 16, 400, 1.5, 0.0, "Default body text"),
            ("body-small", 14, 400, 1.4, 0.1, "Small body text"),
            ("caption", 12, 400, 1.3, 0.2, "Captions and labels"),
        ]
        for name, size, weight, lh, ls, usage in type_scale:
            typography_tokens.append(TypographyToken(
                name=name,
                font_family=fonts[0],
                size=size,
                weight=weight,
                line_height=lh,
                letter_spacing=ls,
                usage=usage,
            ))

        spacing_scale = [0.0, 4.0, 8.0, 12.0, 16.0, 24.0, 32.0, 48.0, 64.0, 96.0]
        if mood == StyleMood.BRUTALIST:
            spacing_scale = [0.0, 8.0, 16.0, 32.0, 64.0, 128.0]

        radius_scale = [0, 4, 8, 12, 16, 24, 32]
        if mood == StyleMood.BRUTALIST:
            radius_scale = [0, 0, 0, 2, 4]
        elif mood == StyleMood.ORGANIC:
            radius_scale = [0, 8, 16, 24, 32, 48, 64]

        shadow_presets = self._generate_shadows(mood)

        theme = ThemeDefinition(
            name=f"{mood.value}-{uuid.uuid4().hex[:6]}",
            mood=mood,
            color_tokens=color_tokens,
            typography=typography_tokens,
            spacing_scale=spacing_scale,
            border_radius_scale=radius_scale,
            shadow_presets=shadow_presets,
            generated_from=description[:200],
        )

        self._themes[theme.id] = theme
        self._themes_generated += 1

        if len(self._themes) > self.MAX_THEMES:
            oldest = min(self._themes.values(), key=lambda t: t.created_at)
            del self._themes[oldest.id]

        return theme

    def modify_theme(
        self, theme_id: str, modification_description: str
    ) -> Optional[ThemeDefinition]:
        theme = self._themes.get(theme_id)
        if theme is None:
            return None

        modified = ThemeDefinition(
            name=f"{theme.name}-mod",
            mood=theme.mood,
            color_tokens=[ColorToken(**t.__dict__) for t in theme.color_tokens],
            typography=[TypographyToken(**t.__dict__) for t in theme.typography],
            spacing_scale=list(theme.spacing_scale),
            border_radius_scale=list(theme.border_radius_scale),
            shadow_presets=list(theme.shadow_presets),
            generated_from=modification_description[:200],
        )

        desc_lower = modification_description.lower()
        if "larger" in desc_lower or "bigger" in desc_lower:
            modified.spacing_scale = [s * 1.25 for s in modified.spacing_scale]
        if "smaller" in desc_lower or "compact" in desc_lower:
            modified.spacing_scale = [s * 0.75 for s in modified.spacing_scale]

        self._themes[modified.id] = modified
        return modified

    def extract_colors_from_image(self, image_description: str) -> List[ColorToken]:
        tokens: List[ColorToken] = []
        desc_lower = image_description.lower()

        color_map = {
            "red": ("#E74C3C", "warm"),
            "blue": ("#3498DB", "cool"),
            "green": ("#2ECC71", "nature"),
            "yellow": ("#F1C40F", "warm"),
            "purple": ("#9B59B6", "luxury"),
            "orange": ("#E67E22", "warm"),
            "teal": ("#1ABC9C", "cool"),
            "pink": ("#E91E63", "warm"),
            "brown": ("#8B4513", "earth"),
            "gray": ("#95A5A6", "neutral"),
            "black": ("#1A1A1A", "neutral"),
            "white": ("#F5F5F5", "neutral"),
        }

        for color_name, (hex_val, category) in color_map.items():
            if color_name in desc_lower:
                tokens.append(ColorToken(
                    name=f"extracted-{color_name}",
                    hex_value=hex_val,
                    usage_description=f"Extracted from image: {color_name}",
                    category=category,
                ))

        return tokens

    def blend_themes(
        self, theme_a: ThemeDefinition, theme_b: ThemeDefinition, ratio: float
    ) -> ThemeDefinition:
        blended_ratio = max(0.0, min(1.0, ratio))
        tokens: List[ColorToken] = []

        min_colors = min(len(theme_a.color_tokens), len(theme_b.color_tokens))
        for i in range(min_colors):
            blended_hex = self._blend_hex(
                theme_a.color_tokens[i].hex_value,
                theme_b.color_tokens[i].hex_value,
                blended_ratio,
            )
            tokens.append(ColorToken(
                name=f"blended-{theme_a.color_tokens[i].name}",
                hex_value=blended_hex,
                usage_description=f"Blend of {theme_a.name} and {theme_b.name}",
                category=theme_a.color_tokens[i].category,
            ))

        blended_spacing = [
            a * (1 - blended_ratio) + b * blended_ratio
            for a, b in zip(theme_a.spacing_scale, theme_b.spacing_scale)
        ]

        blended_radius = [
            int(a * (1 - blended_ratio) + b * blended_ratio)
            for a, b in zip(theme_a.border_radius_scale, theme_b.border_radius_scale)
        ]

        blended = ThemeDefinition(
            name=f"blend-{theme_a.name}-{theme_b.name}",
            mood=theme_a.mood,
            color_tokens=tokens,
            typography=theme_a.typography if blended_ratio < 0.5 else theme_b.typography,
            spacing_scale=blended_spacing,
            border_radius_scale=blended_radius,
            shadow_presets=theme_a.shadow_presets,
            generated_from=f"Blend of {theme_a.id} ({1 - blended_ratio:.0%}) and {theme_b.id} ({blended_ratio:.0%})",
        )

        self._themes[blended.id] = blended
        return blended

    def export_css_variables(self, theme_id: str) -> str:
        theme = self._themes.get(theme_id)
        if theme is None:
            return ""

        lines: List[str] = [":root {"]
        lines.append(f"  /* {theme.name} — {theme.mood.value} */")
        lines.append("")

        for token in theme.color_tokens:
            lines.append(f"  --color-{token.name}: {token.hex_value};")
        lines.append("")

        for token in theme.typography:
            lines.append(f"  --font-{token.name}: {token.css_value()}")
        lines.append("")

        for i, sp in enumerate(theme.spacing_scale):
            lines.append(f"  --space-{i}: {sp}px;")
        lines.append("")

        for i, rad in enumerate(theme.border_radius_scale):
            lines.append(f"  --radius-{i}: {rad}px;")
        lines.append("")

        for i, shadow in enumerate(theme.shadow_presets):
            val = shadow.get("css", "none")
            lines.append(f"  --shadow-{shadow.get('name', i)}: {val};")

        lines.append("}")
        return "\n".join(lines)

    def _generate_shadows(self, mood: StyleMood) -> List[dict]:
        if mood in (StyleMood.DARK, StyleMood.NEON, StyleMood.SCIFI):
            return [
                {"name": "small", "css": "0 2px 4px rgba(0,0,0,0.3)"},
                {"name": "medium", "css": "0 4px 8px rgba(0,0,0,0.4)"},
                {"name": "large", "css": "0 8px 16px rgba(0,0,0,0.5)"},
            ]
        elif mood == StyleMood.BRUTALIST:
            return [
                {"name": "small", "css": "4px 4px 0 #000"},
                {"name": "medium", "css": "8px 8px 0 #000"},
                {"name": "large", "css": "12px 12px 0 #000"},
            ]
        else:
            return [
                {"name": "small", "css": "0 1px 3px rgba(0,0,0,0.12)"},
                {"name": "medium", "css": "0 4px 6px rgba(0,0,0,0.1)"},
                {"name": "large", "css": "0 10px 20px rgba(0,0,0,0.08)"},
            ]

    def _adjust_hex_brightness(self, hex_color: str, factor: float) -> str:
        hex_color = hex_color.lstrip("#")
        r = int(hex_color[0:2], 16)
        g = int(hex_color[2:4], 16)
        b = int(hex_color[4:6], 16)
        r = min(255, max(0, int(r * factor)))
        g = min(255, max(0, int(g * factor)))
        b = min(255, max(0, int(b * factor)))
        return f"#{r:02X}{g:02X}{b:02X}"

    def _blend_hex(self, hex_a: str, hex_b: str, ratio: float) -> str:
        hex_a = hex_a.lstrip("#")
        hex_b = hex_b.lstrip("#")
        r = int(int(hex_a[0:2], 16) * (1 - ratio) + int(hex_b[0:2], 16) * ratio)
        g = int(int(hex_a[2:4], 16) * (1 - ratio) + int(hex_b[2:4], 16) * ratio)
        b = int(int(hex_a[4:6], 16) * (1 - ratio) + int(hex_b[4:6], 16) * ratio)
        return f"#{r:02X}{g:02X}{b:02X}"

    def get_stats(self) -> dict:
        mood_counts: Dict[str, int] = defaultdict(int)
        total_colors = 0
        total_typography = 0
        for theme in self._themes.values():
            mood_counts[theme.mood.value] += 1
            total_colors += len(theme.color_tokens)
            total_typography += len(theme.typography)

        return {
            "total_themes": len(self._themes),
            "themes_generated_ever": self._themes_generated,
            "mood_distribution": dict(mood_counts),
            "total_color_tokens": total_colors,
            "total_typography_tokens": total_typography,
            "max_themes": self.MAX_THEMES,
        }


def get_theme_designer() -> ThemeDesigner:
    return ThemeDesigner.get_instance()