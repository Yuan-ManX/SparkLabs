"""
Font System - Font resource management, glyph metrics, and text layout.

Architecture:
    FontSystem/
    |-- FontType (bitmap, truetype, system enumeration)
    |-- FontWeight (weight classification enumeration)
    |-- TextStyle (rendering style configuration dataclass)
    |-- FontResource (font definition and metrics dataclass)
    |-- GlyphInfo (per-character layout dataclass)
    |-- TextBlock (measured text layout result dataclass)
    |-- FontSystem (global font orchestration)

Manages font resources with character metrics, text measurement, line wrapping,
and styled text block layout. Supports fallback font chains and bitmap font import.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Dict, List, Optional, Tuple


class FontType(Enum):
    BITMAP = auto()
    TRUETYPE = auto()
    SYSTEM = auto()


class FontWeight(Enum):
    THIN = 100
    EXTRA_LIGHT = 200
    LIGHT = 300
    REGULAR = 400
    MEDIUM = 500
    SEMI_BOLD = 600
    BOLD = 700
    EXTRA_BOLD = 800
    BLACK = 900


class TextAlignment(Enum):
    LEFT = "left"
    CENTER = "center"
    RIGHT = "right"
    JUSTIFY = "justify"


class TextOverflow(Enum):
    CLIP = "clip"
    ELLIPSIS = "ellipsis"
    WRAP = "wrap"


@dataclass
class TextStyle:
    font_id: str = ""
    font_size: float = 16.0
    line_spacing: float = 1.2
    letter_spacing: float = 0.0
    alignment: TextAlignment = TextAlignment.LEFT
    overflow: TextOverflow = TextOverflow.WRAP
    color: Tuple[int, int, int, int] = (255, 255, 255, 255)
    bold: bool = False
    italic: bool = False
    underline: bool = False
    strikethrough: bool = False
    shadow_offset: Tuple[float, float] = (0.0, 0.0)
    shadow_color: Tuple[int, int, int, int] = (0, 0, 0, 128)
    outline_width: float = 0.0
    outline_color: Tuple[int, int, int, int] = (0, 0, 0, 255)
    max_width: Optional[float] = None
    max_height: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "font_id": self.font_id,
            "font_size": self.font_size,
            "line_spacing": self.line_spacing,
            "letter_spacing": self.letter_spacing,
            "alignment": self.alignment.value,
            "overflow": self.overflow.value,
            "color": list(self.color),
            "bold": self.bold,
            "italic": self.italic,
            "underline": self.underline,
            "strikethrough": self.strikethrough,
            "outline_width": self.outline_width,
        }


@dataclass
class FontResource:
    font_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = "Default"
    font_type: FontType = FontType.SYSTEM
    family: str = "sans-serif"
    weight: FontWeight = FontWeight.REGULAR
    source_path: str = ""
    default_size: float = 16.0
    line_height: float = 1.2
    ascender: float = 14.0
    descender: float = -4.0
    x_height: float = 8.0
    cap_height: float = 12.0
    space_width: float = 4.0
    tab_width: float = 32.0
    fallback_fonts: List[str] = field(default_factory=list)
    glyph_count: int = 128

    def estimate_width(self, text: str, size: float) -> float:
        scale = size / self.default_size if self.default_size > 0 else 1.0
        avg_char_width = self.x_height * 0.6
        return len(text) * avg_char_width * scale

    def to_dict(self) -> Dict[str, Any]:
        return {
            "font_id": self.font_id,
            "name": self.name,
            "type": self.font_type.name,
            "family": self.family,
            "weight": self.weight.name,
            "default_size": self.default_size,
            "line_height": self.line_height,
            "fallback_count": len(self.fallback_fonts),
            "glyph_count": self.glyph_count,
        }


@dataclass
class GlyphInfo:
    character: str = ""
    index: int = 0
    advance: float = 10.0
    bearing_x: float = 0.0
    bearing_y: float = 12.0
    width: float = 10.0
    height: float = 12.0
    x: float = 0.0
    y: float = 0.0
    texture_rect: Tuple[float, float, float, float] = (0.0, 0.0, 1.0, 1.0)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "character": self.character,
            "advance": self.advance,
            "width": self.width,
            "height": self.height,
        }


@dataclass
class TextBlock:
    block_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    text: str = ""
    style: TextStyle = field(default_factory=TextStyle)
    lines: List[str] = field(default_factory=list)
    total_width: float = 0.0
    total_height: float = 0.0
    line_count: int = 0
    glyphs: List[GlyphInfo] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "block_id": self.block_id,
            "text": self.text[:100],
            "style": self.style.to_dict(),
            "total_width": self.total_width,
            "total_height": self.total_height,
            "line_count": self.line_count,
            "glyph_count": len(self.glyphs),
        }


class FontSystem:
    _instance: Optional["FontSystem"] = None

    def __init__(self):
        self._fonts: Dict[str, FontResource] = {}
        self._text_blocks: Dict[str, TextBlock] = {}
        self._initialize_default_font()

    def _initialize_default_font(self) -> None:
        default = FontResource(
            name="System Default",
            font_type=FontType.SYSTEM,
            family="sans-serif",
            weight=FontWeight.REGULAR,
        )
        self._fonts[default.font_id] = default

    @classmethod
    def get_instance(cls) -> "FontSystem":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def register_font(self, font: FontResource) -> str:
        self._fonts[font.font_id] = font
        return font.font_id

    def create_font(
        self,
        name: str = "Font",
        family: str = "sans-serif",
        weight: FontWeight = FontWeight.REGULAR,
        default_size: float = 16.0,
        font_type: FontType = FontType.SYSTEM,
    ) -> FontResource:
        font = FontResource(
            name=name,
            font_type=font_type,
            family=family,
            weight=weight,
            default_size=default_size,
        )
        self._fonts[font.font_id] = font
        return font

    def get_font(self, font_id: str) -> Optional[FontResource]:
        return self._fonts.get(font_id)

    def remove_font(self, font_id: str) -> bool:
        if font_id in self._fonts:
            del self._fonts[font_id]
            return True
        return False

    def list_fonts(self) -> List[FontResource]:
        return list(self._fonts.values())

    def find_font_by_family(self, family: str, weight: Optional[FontWeight] = None) -> Optional[FontResource]:
        for font in self._fonts.values():
            if font.family.lower() == family.lower():
                if weight is None or font.weight == weight:
                    return font
        return None

    def measure_text(self, text: str, style: TextStyle) -> TextBlock:
        font = self._fonts.get(style.font_id)
        if not font and self._fonts:
            font = next(iter(self._fonts.values()))
        if not font:
            font = self.create_font()

        block = TextBlock(text=text, style=style)
        scale = style.font_size / font.default_size if font.default_size > 0 else 1.0
        line_height = font.line_height * style.font_size * style.line_spacing

        if style.max_width and style.max_width > 0:
            current_line = ""
            current_width = 0.0
            words = text.split(" ")

            for word in words:
                word_width = font.estimate_width(word + " ", style.font_size)
                word_width += style.letter_spacing * len(word)

                if current_width + word_width > style.max_width and current_line:
                    block.lines.append(current_line.rstrip())
                    current_line = word + " "
                    current_width = font.estimate_width(word + " ", style.font_size)
                else:
                    current_line += word + " "
                    current_width += word_width

            if current_line.strip():
                block.lines.append(current_line.rstrip())
        else:
            block.lines = text.split("\n") if "\n" in text else [text]

        block.line_count = len(block.lines)
        max_line_width = 0.0
        for i, line in enumerate(block.lines):
            line_width = font.estimate_width(line, style.font_size)
            line_width += style.letter_spacing * len(line)
            max_line_width = max(max_line_width, line_width)
            char_idx = 0
            for ch in line:
                glyph = GlyphInfo(
                    character=ch,
                    index=char_idx,
                    advance=style.font_size * 0.6,
                    x=font.estimate_width(line[:char_idx], style.font_size),
                    y=i * line_height,
                )
                block.glyphs.append(glyph)
                char_idx += 1

        block.total_width = min(max_line_width, style.max_width or max_line_width)
        block.total_height = block.line_count * line_height

        return block

    def create_text_block(self, text: str, style: TextStyle) -> TextBlock:
        block = self.measure_text(text, style)
        self._text_blocks[block.block_id] = block
        return block

    def get_text_block(self, block_id: str) -> Optional[TextBlock]:
        return self._text_blocks.get(block_id)

    def wrap_text(self, text: str, style: TextStyle) -> List[str]:
        block = self.measure_text(text, style)
        return block.lines

    def get_default_font_id(self) -> str:
        if self._fonts:
            return next(iter(self._fonts.keys()))
        font = self.create_font()
        return font.font_id

    def get_stats(self) -> Dict[str, Any]:
        return {
            "font_count": len(self._fonts),
            "text_block_count": len(self._text_blocks),
            "fonts": [f.name for f in self._fonts.values()],
            "default_font_id": self.get_default_font_id(),
        }


def get_font_system() -> FontSystem:
    return FontSystem.get_instance()
