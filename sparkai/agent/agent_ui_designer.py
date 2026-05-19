"""
SparkLabs Agent - UI Designer

AI-driven UI/UX layout generation system for game interfaces.
Provides automated generation of complete UI layouts including
element placement, theming, responsive variants, and validation
for in-game HUDs, menus, dialogs, and interactive panels.

Architecture:
  UIDesigner
    |-- Session Manager (design workflow lifecycle tracking)
    |-- Layout Generator (intelligent element placement per layout type)
    |-- Theme Engine (theme variant application and recalculation)
    |-- Auto-Layout Solver (responsive repositioning for any resolution)
    |-- Responsive Variant Generator (mobile/tablet/desktop scaling)
    |-- Layout Validator (overlap, bounds, and accessibility checks)

Supports 12 layout types, 13 widget types, 7 theme variants,
and 10 alignment modes for complete UI composition.
"""

from __future__ import annotations

import math
import threading
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

MAX_LAYOUTS = 200
MAX_ELEMENTS = 5000
MAX_SESSIONS = 50

# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class LayoutType(Enum):
    HUD = "hud"
    MAIN_MENU = "main_menu"
    PAUSE_MENU = "pause_menu"
    SETTINGS = "settings"
    INVENTORY = "inventory"
    DIALOG_BOX = "dialog_box"
    SCOREBOARD = "scoreboard"
    SHOP = "shop"
    QUEST_LOG = "quest_log"
    MINIMAP = "minimap"
    HEALTH_BAR = "health_bar"
    CONTROLLER_OVERLAY = "controller_overlay"


class WidgetType(Enum):
    BUTTON = "button"
    LABEL = "label"
    IMAGE = "image"
    SLIDER = "slider"
    DROPDOWN = "dropdown"
    TOGGLE = "toggle"
    INPUT_FIELD = "input_field"
    PROGRESS_BAR = "progress_bar"
    PANEL = "panel"
    GRID = "grid"
    SCROLL_VIEW = "scroll_view"
    TAB_BAR = "tab_bar"
    ICON_BUTTON = "icon_button"


class Alignment(Enum):
    TOP_LEFT = "top_left"
    TOP_CENTER = "top_center"
    TOP_RIGHT = "top_right"
    MIDDLE_LEFT = "middle_left"
    CENTER = "center"
    MIDDLE_RIGHT = "middle_right"
    BOTTOM_LEFT = "bottom_left"
    BOTTOM_CENTER = "bottom_center"
    BOTTOM_RIGHT = "bottom_right"
    STRETCH = "stretch"


class ThemeVariant(Enum):
    DARK = "dark"
    LIGHT = "light"
    HIGH_CONTRAST = "high_contrast"
    RETRO = "retro"
    MINIMAL = "minimal"
    FANTASY = "fantasy"
    SCI_FI = "sci_fi"


# ---------------------------------------------------------------------------
# Theme Presets
# ---------------------------------------------------------------------------

THEME_PRESETS: Dict[ThemeVariant, Dict[str, Any]] = {
    ThemeVariant.DARK: {
        "primary": "#6C63FF",
        "secondary": "#3F3D56",
        "background": "#1E1E2E",
        "surface": "#2A2A3C",
        "text_primary": "#EAEAEA",
        "text_secondary": "#A0A0B0",
        "accent": "#FF6584",
        "border": "#3E3E52",
        "disabled": "#555566",
    },
    ThemeVariant.LIGHT: {
        "primary": "#6C63FF",
        "secondary": "#E8E8F0",
        "background": "#F5F5FA",
        "surface": "#FFFFFF",
        "text_primary": "#1A1A2E",
        "text_secondary": "#6E6E82",
        "accent": "#FF6584",
        "border": "#D0D0DA",
        "disabled": "#BBBBCC",
    },
    ThemeVariant.HIGH_CONTRAST: {
        "primary": "#FFFF00",
        "secondary": "#00FFFF",
        "background": "#000000",
        "surface": "#1A1A1A",
        "text_primary": "#FFFFFF",
        "text_secondary": "#CCCCCC",
        "accent": "#FF0000",
        "border": "#FFFFFF",
        "disabled": "#666666",
    },
    ThemeVariant.RETRO: {
        "primary": "#FFD700",
        "secondary": "#8B4513",
        "background": "#2B1B0E",
        "surface": "#3D2B1F",
        "text_primary": "#FFE4B5",
        "text_secondary": "#CD853F",
        "accent": "#FF6347",
        "border": "#8B6914",
        "disabled": "#555544",
    },
    ThemeVariant.MINIMAL: {
        "primary": "#333333",
        "secondary": "#F0F0F0",
        "background": "#FFFFFF",
        "surface": "#FAFAFA",
        "text_primary": "#111111",
        "text_secondary": "#888888",
        "accent": "#0066CC",
        "border": "#E0E0E0",
        "disabled": "#CCCCCC",
    },
    ThemeVariant.FANTASY: {
        "primary": "#9B59B6",
        "secondary": "#2ECC71",
        "background": "#1C0C2E",
        "surface": "#2D1B4E",
        "text_primary": "#F1C40F",
        "text_secondary": "#C39BD3",
        "accent": "#E74C3C",
        "border": "#7D3C98",
        "disabled": "#4A235A",
    },
    ThemeVariant.SCI_FI: {
        "primary": "#00E5FF",
        "secondary": "#1B1B2F",
        "background": "#0A0A1A",
        "surface": "#12122A",
        "text_primary": "#00FFCC",
        "text_secondary": "#0088AA",
        "accent": "#FF0088",
        "border": "#00E5FF",
        "disabled": "#003344",
    },
}

# ---------------------------------------------------------------------------
# Layout Templates
# ---------------------------------------------------------------------------

LAYOUT_TEMPLATES: Dict[LayoutType, List[Dict[str, Any]]] = {
    LayoutType.HUD: [
        {
            "element_type": WidgetType.PANEL,
            "name": "health_bar_container",
            "x": 20,
            "y": 20,
            "width": 260,
            "height": 40,
            "alignment": Alignment.TOP_LEFT,
            "style": {"opacity": 0.85, "corner_radius": 6},
        },
        {
            "element_type": WidgetType.PROGRESS_BAR,
            "name": "health_bar",
            "x": 26,
            "y": 26,
            "width": 248,
            "height": 28,
            "alignment": Alignment.TOP_LEFT,
            "style": {"color": "#FF4444", "bg_color": "#331111", "corner_radius": 4},
        },
        {
            "element_type": WidgetType.LABEL,
            "name": "health_label",
            "x": 30,
            "y": 22,
            "width": 100,
            "height": 20,
            "alignment": Alignment.TOP_LEFT,
            "text": "HP",
            "style": {"font_size": 14, "color": "#FFFFFF"},
        },
        {
            "element_type": WidgetType.PANEL,
            "name": "minimap_container",
            "x": -20,
            "y": 20,
            "width": 160,
            "height": 160,
            "alignment": Alignment.TOP_RIGHT,
            "style": {"opacity": 0.8, "corner_radius": 80},
        },
        {
            "element_type": WidgetType.IMAGE,
            "name": "minimap",
            "x": -14,
            "y": 26,
            "width": 148,
            "height": 148,
            "alignment": Alignment.TOP_RIGHT,
            "style": {"opacity": 0.9},
        },
        {
            "element_type": WidgetType.PANEL,
            "name": "ammo_container",
            "x": -20,
            "y": -20,
            "width": 160,
            "height": 50,
            "alignment": Alignment.BOTTOM_RIGHT,
            "style": {"opacity": 0.85, "corner_radius": 6},
        },
        {
            "element_type": WidgetType.LABEL,
            "name": "ammo_counter",
            "x": -14,
            "y": -14,
            "width": 148,
            "height": 36,
            "alignment": Alignment.BOTTOM_RIGHT,
            "text": "30 / 30",
            "style": {"font_size": 24, "color": "#FFFFFF"},
        },
    ],
    LayoutType.MAIN_MENU: [
        {
            "element_type": WidgetType.PANEL,
            "name": "menu_background",
            "x": 0,
            "y": 0,
            "width": 1920,
            "height": 1080,
            "alignment": Alignment.STRETCH,
            "style": {"bg_color": "#0A0A1A", "opacity": 1.0},
        },
        {
            "element_type": WidgetType.LABEL,
            "name": "game_title",
            "x": 0,
            "y": -200,
            "width": 800,
            "height": 80,
            "alignment": Alignment.TOP_CENTER,
            "text": "GAME TITLE",
            "style": {"font_size": 48, "color": "#FFFFFF"},
        },
        {
            "element_type": WidgetType.BUTTON,
            "name": "btn_play",
            "x": 0,
            "y": -20,
            "width": 280,
            "height": 60,
            "alignment": Alignment.CENTER,
            "text": "Play",
            "style": {"font_size": 22, "color": "#00FFCC", "bg_color": "#1B1B3A"},
        },
        {
            "element_type": WidgetType.BUTTON,
            "name": "btn_options",
            "x": 0,
            "y": 60,
            "width": 280,
            "height": 60,
            "alignment": Alignment.CENTER,
            "text": "Options",
            "style": {"font_size": 22, "color": "#00FFCC", "bg_color": "#1B1B3A"},
        },
        {
            "element_type": WidgetType.BUTTON,
            "name": "btn_quit",
            "x": 0,
            "y": 140,
            "width": 280,
            "height": 60,
            "alignment": Alignment.CENTER,
            "text": "Quit",
            "style": {"font_size": 22, "color": "#FF4444", "bg_color": "#1B1B3A"},
        },
    ],
    LayoutType.SETTINGS: [
        {
            "element_type": WidgetType.PANEL,
            "name": "settings_panel",
            "x": 0,
            "y": 0,
            "width": 720,
            "height": 600,
            "alignment": Alignment.CENTER,
            "style": {"bg_color": "#2A2A3C", "corner_radius": 12, "opacity": 0.95},
        },
        {
            "element_type": WidgetType.LABEL,
            "name": "settings_title",
            "x": 0,
            "y": -260,
            "width": 400,
            "height": 40,
            "alignment": Alignment.TOP_CENTER,
            "text": "Settings",
            "style": {"font_size": 28, "color": "#FFFFFF"},
        },
        {
            "element_type": WidgetType.LABEL,
            "name": "lbl_volume",
            "x": -280,
            "y": -180,
            "width": 150,
            "height": 30,
            "alignment": Alignment.MIDDLE_LEFT,
            "text": "Master Volume",
            "style": {"font_size": 18, "color": "#CCCCCC"},
        },
        {
            "element_type": WidgetType.SLIDER,
            "name": "slider_volume",
            "x": 40,
            "y": -180,
            "width": 280,
            "height": 30,
            "alignment": Alignment.MIDDLE_LEFT,
            "style": {"color": "#6C63FF", "bg_color": "#3E3E52", "corner_radius": 4},
        },
        {
            "element_type": WidgetType.LABEL,
            "name": "lbl_resolution",
            "x": -280,
            "y": -110,
            "width": 150,
            "height": 30,
            "alignment": Alignment.MIDDLE_LEFT,
            "text": "Resolution",
            "style": {"font_size": 18, "color": "#CCCCCC"},
        },
        {
            "element_type": WidgetType.DROPDOWN,
            "name": "dropdown_resolution",
            "x": 40,
            "y": -110,
            "width": 280,
            "height": 36,
            "alignment": Alignment.MIDDLE_LEFT,
            "style": {"color": "#FFFFFF", "bg_color": "#3E3E52", "corner_radius": 4},
        },
        {
            "element_type": WidgetType.LABEL,
            "name": "lbl_fullscreen",
            "x": -280,
            "y": -40,
            "width": 200,
            "height": 30,
            "alignment": Alignment.MIDDLE_LEFT,
            "text": "Fullscreen",
            "style": {"font_size": 18, "color": "#CCCCCC"},
        },
        {
            "element_type": WidgetType.TOGGLE,
            "name": "toggle_fullscreen",
            "x": 280,
            "y": -40,
            "width": 50,
            "height": 30,
            "alignment": Alignment.MIDDLE_RIGHT,
            "style": {"color": "#6C63FF", "bg_color": "#3E3E52"},
        },
    ],
    LayoutType.INVENTORY: [
        {
            "element_type": WidgetType.PANEL,
            "name": "inventory_panel",
            "x": 0,
            "y": 0,
            "width": 800,
            "height": 560,
            "alignment": Alignment.CENTER,
            "style": {"bg_color": "#2A2A3C", "corner_radius": 12, "opacity": 0.95},
        },
        {
            "element_type": WidgetType.LABEL,
            "name": "inventory_title",
            "x": 0,
            "y": -250,
            "width": 400,
            "height": 40,
            "alignment": Alignment.TOP_CENTER,
            "text": "Inventory",
            "style": {"font_size": 26, "color": "#FFFFFF"},
        },
        {
            "element_type": WidgetType.TAB_BAR,
            "name": "inventory_tabs",
            "x": 0,
            "y": -190,
            "width": 720,
            "height": 40,
            "alignment": Alignment.TOP_CENTER,
            "style": {"bg_color": "#1E1E2E", "corner_radius": 6},
        },
        {
            "element_type": WidgetType.GRID,
            "name": "item_grid",
            "x": 0,
            "y": -30,
            "width": 720,
            "height": 400,
            "alignment": Alignment.CENTER,
            "style": {"bg_color": "#1E1E2E", "corner_radius": 8},
        },
        {
            "element_type": WidgetType.SCROLL_VIEW,
            "name": "item_scroll",
            "x": 0,
            "y": -30,
            "width": 710,
            "height": 390,
            "alignment": Alignment.CENTER,
            "style": {"bg_color": "#1E1E2E"},
        },
    ],
    LayoutType.DIALOG_BOX: [
        {
            "element_type": WidgetType.PANEL,
            "name": "dialog_panel",
            "x": 0,
            "y": 200,
            "width": 900,
            "height": 280,
            "alignment": Alignment.BOTTOM_CENTER,
            "style": {"bg_color": "#1E1E2E", "corner_radius": 16, "opacity": 0.92},
        },
        {
            "element_type": WidgetType.PANEL,
            "name": "portrait_frame",
            "x": 30,
            "y": 30,
            "width": 120,
            "height": 120,
            "alignment": Alignment.TOP_LEFT,
            "style": {"bg_color": "#3E3E52", "corner_radius": 60},
        },
        {
            "element_type": WidgetType.IMAGE,
            "name": "portrait",
            "x": 36,
            "y": 36,
            "width": 108,
            "height": 108,
            "alignment": Alignment.TOP_LEFT,
            "style": {"opacity": 1.0},
        },
        {
            "element_type": WidgetType.LABEL,
            "name": "speaker_name",
            "x": 170,
            "y": 30,
            "width": 300,
            "height": 28,
            "alignment": Alignment.TOP_LEFT,
            "text": "Character Name",
            "style": {"font_size": 20, "color": "#FFD700"},
        },
        {
            "element_type": WidgetType.LABEL,
            "name": "dialog_text",
            "x": 170,
            "y": 70,
            "width": 680,
            "height": 120,
            "alignment": Alignment.TOP_LEFT,
            "text": "Dialog text appears here...",
            "style": {"font_size": 16, "color": "#EAEAEA"},
        },
        {
            "element_type": WidgetType.PANEL,
            "name": "choices_panel",
            "x": 0,
            "y": 170,
            "width": 860,
            "height": 90,
            "alignment": Alignment.TOP_CENTER,
            "style": {"bg_color": "#252538", "corner_radius": 8},
        },
        {
            "element_type": WidgetType.BUTTON,
            "name": "choice_1",
            "x": -280,
            "y": 185,
            "width": 260,
            "height": 44,
            "alignment": Alignment.TOP_LEFT,
            "text": "Choice 1",
            "style": {"font_size": 15, "color": "#00FFCC", "bg_color": "#1B1B3A"},
        },
        {
            "element_type": WidgetType.BUTTON,
            "name": "choice_2",
            "x": 0,
            "y": 185,
            "width": 260,
            "height": 44,
            "alignment": Alignment.TOP_CENTER,
            "text": "Choice 2",
            "style": {"font_size": 15, "color": "#00FFCC", "bg_color": "#1B1B3A"},
        },
        {
            "element_type": WidgetType.BUTTON,
            "name": "choice_3",
            "x": 280,
            "y": 185,
            "width": 260,
            "height": 44,
            "alignment": Alignment.TOP_RIGHT,
            "text": "Choice 3",
            "style": {"font_size": 15, "color": "#00FFCC", "bg_color": "#1B1B3A"},
        },
    ],
    LayoutType.PAUSE_MENU: [
        {
            "element_type": WidgetType.PANEL,
            "name": "pause_overlay",
            "x": 0,
            "y": 0,
            "width": 1920,
            "height": 1080,
            "alignment": Alignment.STRETCH,
            "style": {"bg_color": "#000000", "opacity": 0.7},
        },
        {
            "element_type": WidgetType.LABEL,
            "name": "pause_title",
            "x": 0,
            "y": -100,
            "width": 400,
            "height": 50,
            "alignment": Alignment.CENTER,
            "text": "PAUSED",
            "style": {"font_size": 36, "color": "#FFFFFF"},
        },
        {
            "element_type": WidgetType.BUTTON,
            "name": "btn_resume",
            "x": 0,
            "y": -20,
            "width": 240,
            "height": 52,
            "alignment": Alignment.CENTER,
            "text": "Resume",
            "style": {"font_size": 20, "color": "#FFFFFF", "bg_color": "#2A2A3C"},
        },
        {
            "element_type": WidgetType.BUTTON,
            "name": "btn_save",
            "x": 0,
            "y": 50,
            "width": 240,
            "height": 52,
            "alignment": Alignment.CENTER,
            "text": "Save Game",
            "style": {"font_size": 20, "color": "#FFFFFF", "bg_color": "#2A2A3C"},
        },
        {
            "element_type": WidgetType.BUTTON,
            "name": "btn_quit_menu",
            "x": 0,
            "y": 120,
            "width": 240,
            "height": 52,
            "alignment": Alignment.CENTER,
            "text": "Quit to Menu",
            "style": {"font_size": 20, "color": "#FF4444", "bg_color": "#2A2A3C"},
        },
    ],
    LayoutType.SCOREBOARD: [
        {
            "element_type": WidgetType.PANEL,
            "name": "scoreboard_bg",
            "x": 0,
            "y": 0,
            "width": 700,
            "height": 500,
            "alignment": Alignment.CENTER,
            "style": {"bg_color": "#1E1E2E", "corner_radius": 12, "opacity": 0.95},
        },
        {
            "element_type": WidgetType.LABEL,
            "name": "scoreboard_title",
            "x": 0,
            "y": -220,
            "width": 400,
            "height": 40,
            "alignment": Alignment.TOP_CENTER,
            "text": "Scoreboard",
            "style": {"font_size": 24, "color": "#FFD700"},
        },
        {
            "element_type": WidgetType.SCROLL_VIEW,
            "name": "score_list",
            "x": 0,
            "y": -30,
            "width": 640,
            "height": 340,
            "alignment": Alignment.CENTER,
            "style": {"bg_color": "#16162A"},
        },
    ],
    LayoutType.SHOP: [
        {
            "element_type": WidgetType.PANEL,
            "name": "shop_panel",
            "x": 0,
            "y": 0,
            "width": 860,
            "height": 620,
            "alignment": Alignment.CENTER,
            "style": {"bg_color": "#2A2A3C", "corner_radius": 12, "opacity": 0.95},
        },
        {
            "element_type": WidgetType.LABEL,
            "name": "shop_title",
            "x": 0,
            "y": -280,
            "width": 400,
            "height": 40,
            "alignment": Alignment.TOP_CENTER,
            "text": "Shop",
            "style": {"font_size": 26, "color": "#FFD700"},
        },
        {
            "element_type": WidgetType.TAB_BAR,
            "name": "shop_category_tabs",
            "x": 0,
            "y": -220,
            "width": 780,
            "height": 38,
            "alignment": Alignment.TOP_CENTER,
            "style": {"bg_color": "#1E1E2E", "corner_radius": 6},
        },
        {
            "element_type": WidgetType.GRID,
            "name": "shop_item_grid",
            "x": 0,
            "y": -40,
            "width": 780,
            "height": 360,
            "alignment": Alignment.CENTER,
            "style": {"bg_color": "#1E1E2E", "corner_radius": 8},
        },
        {
            "element_type": WidgetType.LABEL,
            "name": "currency_display",
            "x": 340,
            "y": -280,
            "width": 180,
            "height": 32,
            "alignment": Alignment.TOP_RIGHT,
            "text": "Gold: 1000",
            "style": {"font_size": 18, "color": "#FFD700"},
        },
    ],
    LayoutType.QUEST_LOG: [
        {
            "element_type": WidgetType.PANEL,
            "name": "quest_panel",
            "x": 0,
            "y": 0,
            "width": 660,
            "height": 520,
            "alignment": Alignment.CENTER,
            "style": {"bg_color": "#2A2A3C", "corner_radius": 12, "opacity": 0.95},
        },
        {
            "element_type": WidgetType.LABEL,
            "name": "quest_title",
            "x": 0,
            "y": -230,
            "width": 400,
            "height": 40,
            "alignment": Alignment.TOP_CENTER,
            "text": "Quest Log",
            "style": {"font_size": 24, "color": "#FFFFFF"},
        },
        {
            "element_type": WidgetType.SCROLL_VIEW,
            "name": "quest_list",
            "x": 0,
            "y": -40,
            "width": 600,
            "height": 370,
            "alignment": Alignment.CENTER,
            "style": {"bg_color": "#1E1E2E"},
        },
    ],
    LayoutType.MINIMAP: [
        {
            "element_type": WidgetType.PANEL,
            "name": "minimap_frame",
            "x": -20,
            "y": 20,
            "width": 180,
            "height": 180,
            "alignment": Alignment.TOP_RIGHT,
            "style": {"bg_color": "#1E1E2E", "corner_radius": 90, "opacity": 0.85},
        },
        {
            "element_type": WidgetType.IMAGE,
            "name": "minimap_content",
            "x": -14,
            "y": 26,
            "width": 168,
            "height": 168,
            "alignment": Alignment.TOP_RIGHT,
            "style": {"opacity": 0.9},
        },
    ],
    LayoutType.HEALTH_BAR: [
        {
            "element_type": WidgetType.PANEL,
            "name": "health_bg",
            "x": 20,
            "y": -20,
            "width": 300,
            "height": 28,
            "alignment": Alignment.BOTTOM_LEFT,
            "style": {"bg_color": "#331111", "corner_radius": 6, "opacity": 0.8},
        },
        {
            "element_type": WidgetType.PROGRESS_BAR,
            "name": "health_fill",
            "x": 24,
            "y": -17,
            "width": 292,
            "height": 22,
            "alignment": Alignment.BOTTOM_LEFT,
            "style": {"color": "#FF4444", "bg_color": "#331111", "corner_radius": 4},
        },
        {
            "element_type": WidgetType.LABEL,
            "name": "health_value",
            "x": 0,
            "y": -16,
            "width": 100,
            "height": 20,
            "alignment": Alignment.BOTTOM_CENTER,
            "text": "100 / 100",
            "style": {"font_size": 14, "color": "#FFFFFF"},
        },
    ],
    LayoutType.CONTROLLER_OVERLAY: [
        {
            "element_type": WidgetType.PANEL,
            "name": "dpad_panel",
            "x": 60,
            "y": -20,
            "width": 140,
            "height": 140,
            "alignment": Alignment.BOTTOM_LEFT,
            "style": {"bg_color": "#333344", "corner_radius": 16, "opacity": 0.5},
        },
        {
            "element_type": WidgetType.ICON_BUTTON,
            "name": "btn_up",
            "x": 0,
            "y": -60,
            "width": 48,
            "height": 48,
            "alignment": Alignment.BOTTOM_CENTER,
            "style": {"bg_color": "#444466", "corner_radius": 8, "opacity": 0.6},
        },
        {
            "element_type": WidgetType.ICON_BUTTON,
            "name": "btn_action_a",
            "x": -60,
            "y": -20,
            "width": 52,
            "height": 52,
            "alignment": Alignment.BOTTOM_RIGHT,
            "text": "A",
            "style": {"bg_color": "#33AA33", "corner_radius": 26, "font_size": 18},
        },
        {
            "element_type": WidgetType.ICON_BUTTON,
            "name": "btn_action_b",
            "x": -120,
            "y": -20,
            "width": 52,
            "height": 52,
            "alignment": Alignment.BOTTOM_RIGHT,
            "text": "B",
            "style": {"bg_color": "#CC3333", "corner_radius": 26, "font_size": 18},
        },
        {
            "element_type": WidgetType.PANEL,
            "name": "left_stick_zone",
            "x": 130,
            "y": -50,
            "width": 100,
            "height": 100,
            "alignment": Alignment.BOTTOM_LEFT,
            "style": {"bg_color": "#333344", "corner_radius": 50, "opacity": 0.4},
        },
    ],
}

# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------


@dataclass
class UIElement:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    element_type: WidgetType = WidgetType.LABEL
    name: str = ""
    x: float = 0.0
    y: float = 0.0
    width: float = 100.0
    height: float = 40.0
    alignment: Alignment = Alignment.CENTER
    anchor: Optional[str] = None
    text: str = ""
    style: Dict[str, Any] = field(default_factory=dict)
    children: List[str] = field(default_factory=list)
    visible: bool = True
    enabled: bool = True
    tooltip: str = ""
    z_order: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "element_type": self.element_type.value,
            "name": self.name,
            "x": self.x,
            "y": self.y,
            "width": self.width,
            "height": self.height,
            "alignment": self.alignment.value,
            "anchor": self.anchor,
            "text": self.text,
            "style": self.style,
            "children": self.children,
            "visible": self.visible,
            "enabled": self.enabled,
            "tooltip": self.tooltip,
            "z_order": self.z_order,
        }


@dataclass
class UILayout:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = ""
    layout_type: LayoutType = LayoutType.HUD
    resolution_width: int = 1920
    resolution_height: int = 1080
    elements: Dict[str, UIElement] = field(default_factory=dict)
    root_element_id: Optional[str] = None
    theme: ThemeVariant = ThemeVariant.DARK
    safe_area: Dict[str, int] = field(default_factory=lambda: {
        "top": 0,
        "bottom": 0,
        "left": 0,
        "right": 0,
    })
    created_at: float = field(default_factory=time.time)
    complexity_score: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "layout_type": self.layout_type.value,
            "resolution": {
                "width": self.resolution_width,
                "height": self.resolution_height,
            },
            "element_count": len(self.elements),
            "elements": {eid: el.to_dict() for eid, el in self.elements.items()},
            "root_element_id": self.root_element_id,
            "theme": self.theme.value,
            "safe_area": self.safe_area,
            "created_at": self.created_at,
            "complexity_score": self.complexity_score,
        }


@dataclass
class DesignSession:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    layout_name: str = ""
    layout_type: LayoutType = LayoutType.HUD
    target_resolution: Tuple[int, int] = (1920, 1080)
    requirements: List[str] = field(default_factory=list)
    started_at: float = field(default_factory=time.time)
    completed: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "layout_name": self.layout_name,
            "layout_type": self.layout_type.value,
            "target_resolution": {
                "width": self.target_resolution[0],
                "height": self.target_resolution[1],
            },
            "requirements": self.requirements,
            "started_at": self.started_at,
            "completed": self.completed,
        }


# ---------------------------------------------------------------------------
# UIDesigner (Singleton)
# ---------------------------------------------------------------------------


class UIDesigner:
    _instance: Optional["UIDesigner"] = None
    _lock: threading.RLock = threading.RLock()

    def __init__(self) -> None:
        self._layouts: Dict[str, UILayout] = {}
        self._sessions: Dict[str, DesignSession] = {}
        self._layout_count: int = 0
        self._session_count: int = 0
        self._total_elements_created: int = 0
        self._widget_usage: Dict[str, int] = {}
        self._theme_usage: Dict[str, int] = {}
        self._layouts_by_type: Dict[str, int] = {}

    @classmethod
    def get_instance(cls) -> "UIDesigner":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    # ------------------------------------------------------------------
    # Session Management
    # ------------------------------------------------------------------

    def start_session(
        self,
        layout_name: str,
        layout_type: LayoutType,
        resolution_w: int = 1920,
        resolution_h: int = 1080,
        requirements: Optional[List[str]] = None,
    ) -> Optional[DesignSession]:
        if len(self._sessions) >= MAX_SESSIONS:
            return None
        session = DesignSession(
            layout_name=layout_name,
            layout_type=layout_type,
            target_resolution=(resolution_w, resolution_h),
            requirements=requirements or [],
        )
        self._sessions[session.id] = session
        self._session_count += 1
        return session

    # ------------------------------------------------------------------
    # Layout Generation
    # ------------------------------------------------------------------

    def generate_layout(
        self,
        session_id: str,
        theme: ThemeVariant = ThemeVariant.DARK,
    ) -> Optional[UILayout]:
        session = self._sessions.get(session_id)
        if session is None:
            return None
        if len(self._layouts) >= MAX_LAYOUTS:
            return None

        layout = UILayout(
            name=session.layout_name,
            layout_type=session.layout_type,
            resolution_width=session.target_resolution[0],
            resolution_height=session.target_resolution[1],
            theme=theme,
        )

        template_key = session.layout_type
        if template_key not in LAYOUT_TEMPLATES:
            template_key = LayoutType.HUD

        templates = LAYOUT_TEMPLATES.get(template_key, [])

        for tpl in templates:
            if self._total_elements_created >= MAX_ELEMENTS:
                break
            element = UIElement(
                element_type=tpl.get("element_type", WidgetType.LABEL),
                name=tpl.get("name", ""),
                x=tpl.get("x", 0.0),
                y=tpl.get("y", 0.0),
                width=tpl.get("width", 100.0),
                height=tpl.get("height", 40.0),
                alignment=tpl.get("alignment", Alignment.CENTER),
                text=tpl.get("text", ""),
                style=tpl.get("style", {}),
            )
            layout.elements[element.id] = element
            self._total_elements_created += 1
            widget_key = element.element_type.value
            self._widget_usage[widget_key] = self._widget_usage.get(widget_key, 0) + 1

        if layout.elements:
            first_id = next(iter(layout.elements))
            layout.root_element_id = first_id

        layout.complexity_score = self._compute_complexity(layout)

        self._layouts[layout.id] = layout
        self._layout_count += 1

        type_key = layout.layout_type.value
        self._layouts_by_type[type_key] = self._layouts_by_type.get(type_key, 0) + 1

        theme_key = theme.value
        self._theme_usage[theme_key] = self._theme_usage.get(theme_key, 0) + 1

        session.completed = True

        return layout

    # ------------------------------------------------------------------
    # Element Management
    # ------------------------------------------------------------------

    def add_element(
        self,
        layout_id: str,
        parent_id: Optional[str],
        element_type: WidgetType,
        name: str,
        x: float,
        y: float,
        w: float,
        h: float,
        style: Optional[Dict[str, Any]] = None,
    ) -> Optional[UIElement]:
        layout = self._layouts.get(layout_id)
        if layout is None:
            return None
        if self._total_elements_created >= MAX_ELEMENTS:
            return None

        element = UIElement(
            element_type=element_type,
            name=name,
            x=x,
            y=y,
            width=w,
            height=h,
            style=style or {},
        )

        if parent_id and parent_id in layout.elements:
            layout.elements[parent_id].children.append(element.id)

        layout.elements[element.id] = element
        self._total_elements_created += 1
        widget_key = element.element_type.value
        self._widget_usage[widget_key] = self._widget_usage.get(widget_key, 0) + 1

        layout.complexity_score = self._compute_complexity(layout)

        return element

    def remove_element(self, layout_id: str, element_id: str) -> bool:
        layout = self._layouts.get(layout_id)
        if layout is None or element_id not in layout.elements:
            return False

        element = layout.elements[element_id]

        if layout.root_element_id == element_id:
            layout.root_element_id = None

        for parent in layout.elements.values():
            if element_id in parent.children:
                parent.children.remove(element_id)

        for child_id in list(element.children):
            if child_id in layout.elements:
                del layout.elements[child_id]

        del layout.elements[element_id]

        layout.complexity_score = self._compute_complexity(layout)

        return True

    def update_element(
        self, layout_id: str, element_id: str, updates: Dict[str, Any]
    ) -> Optional[UIElement]:
        layout = self._layouts.get(layout_id)
        if layout is None or element_id not in layout.elements:
            return None

        element = layout.elements[element_id]

        updatable_fields = {
            "name", "text", "visible", "enabled", "tooltip",
            "z_order", "alignment", "anchor", "style",
        }

        for key, value in updates.items():
            if key in updatable_fields:
                if key == "style" and isinstance(value, dict):
                    element.style.update(value)
                else:
                    setattr(element, key, value)

        layout.complexity_score = self._compute_complexity(layout)

        return element

    def reposition_element(
        self, layout_id: str, element_id: str,
        x: float, y: float, w: float, h: float,
    ) -> Optional[UIElement]:
        layout = self._layouts.get(layout_id)
        if layout is None or element_id not in layout.elements:
            return None

        element = layout.elements[element_id]
        element.x = x
        element.y = y
        element.width = w
        element.height = h

        layout.complexity_score = self._compute_complexity(layout)

        return element

    # ------------------------------------------------------------------
    # Theme Management
    # ------------------------------------------------------------------

    def change_theme(self, layout_id: str, theme: ThemeVariant) -> Optional[UILayout]:
        layout = self._layouts.get(layout_id)
        if layout is None:
            return None

        old_theme = layout.theme.value
        self._theme_usage[old_theme] = max(0, self._theme_usage.get(old_theme, 1) - 1)

        layout.theme = theme
        theme_key = theme.value
        self._theme_usage[theme_key] = self._theme_usage.get(theme_key, 0) + 1

        return layout

    # ------------------------------------------------------------------
    # Layout Operations
    # ------------------------------------------------------------------

    def auto_layout(self, layout_id: str) -> Optional[UILayout]:
        layout = self._layouts.get(layout_id)
        if layout is None:
            return None

        for element in layout.elements.values():
            aligned_x, aligned_y = self._compute_aligned_position(
                element, layout.resolution_width, layout.resolution_height
            )
            element.x = aligned_x
            element.y = aligned_y

        layout.complexity_score = self._compute_complexity(layout)

        return layout

    def generate_responsive_variants(self, layout_id: str) -> List[UILayout]:
        layout = self._layouts.get(layout_id)
        if layout is None:
            return []

        variants: List[UILayout] = []
        resolutions = [
            (375, 812),    # Mobile
            (768, 1024),   # Tablet
            (1920, 1080),  # Desktop
        ]

        for res_w, res_h in resolutions:
            if len(self._layouts) >= MAX_LAYOUTS:
                break
            variant = UILayout(
                name=f"{layout.name} ({res_w}x{res_h})",
                layout_type=layout.layout_type,
                resolution_width=res_w,
                resolution_height=res_h,
                theme=layout.theme,
                safe_area=dict(layout.safe_area),
            )

            scale_x = res_w / max(layout.resolution_width, 1)
            scale_y = res_h / max(layout.resolution_height, 1)

            for orig_element in layout.elements.values():
                if self._total_elements_created >= MAX_ELEMENTS:
                    break
                scaled_element = UIElement(
                    element_type=orig_element.element_type,
                    name=orig_element.name,
                    x=round(orig_element.x * scale_x, 1),
                    y=round(orig_element.y * scale_y, 1),
                    width=max(20, round(orig_element.width * scale_x, 1)),
                    height=max(20, round(orig_element.height * scale_y, 1)),
                    alignment=orig_element.alignment,
                    anchor=orig_element.anchor,
                    text=orig_element.text,
                    style=dict(orig_element.style),
                    visible=orig_element.visible,
                    enabled=orig_element.enabled,
                    tooltip=orig_element.tooltip,
                    z_order=orig_element.z_order,
                )
                variant.elements[scaled_element.id] = scaled_element
                self._total_elements_created += 1
                widget_key = scaled_element.element_type.value
                self._widget_usage[widget_key] = self._widget_usage.get(widget_key, 0) + 1

            if variant.elements:
                variant.root_element_id = next(iter(variant.elements))

            variant.complexity_score = self._compute_complexity(variant)
            self._layouts[variant.id] = variant
            self._layout_count += 1
            type_key = variant.layout_type.value
            self._layouts_by_type[type_key] = self._layouts_by_type.get(type_key, 0) + 1

            theme_key = variant.theme.value
            self._theme_usage[theme_key] = self._theme_usage.get(theme_key, 0) + 1

            variants.append(variant)

        return variants

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    def validate_layout(self, layout_id: str) -> List[str]:
        layout = self._layouts.get(layout_id)
        if layout is None:
            return ["Layout not found"]

        issues: List[str] = []
        elements = list(layout.elements.values())

        for element in elements:
            if element.width <= 0 or element.height <= 0:
                issues.append(
                    f"Element '{element.name}' ({element.id}) has invalid dimensions "
                    f"({element.width}x{element.height})"
                )
            right = element.x + element.width
            bottom = element.y + element.height
            if element.x < 0:
                issues.append(
                    f"Element '{element.name}' ({element.id}) extends beyond left boundary "
                    f"(x={element.x})"
                )
            if element.y < 0:
                issues.append(
                    f"Element '{element.name}' ({element.id}) extends beyond top boundary "
                    f"(y={element.y})"
                )
            if right > layout.resolution_width:
                issues.append(
                    f"Element '{element.name}' ({element.id}) extends beyond right boundary "
                    f"(right={right}, max={layout.resolution_width})"
                )
            if bottom > layout.resolution_height:
                issues.append(
                    f"Element '{element.name}' ({element.id}) extends beyond bottom boundary "
                    f"(bottom={bottom}, max={layout.resolution_height})"
                )

        for i in range(len(elements)):
            for j in range(i + 1, len(elements)):
                a = elements[i]
                b = elements[j]
                a_right = a.x + a.width
                a_bottom = a.y + a.height
                b_right = b.x + b.width
                b_bottom = b.y + b.height

                if (
                    a.x < b_right
                    and a_right > b.x
                    and a.y < b_bottom
                    and a_bottom > b.y
                    and a.visible
                    and b.visible
                ):
                    ax1, ay1 = a.x, a.y
                    ax2, ay2 = a_right, a_bottom
                    bx1, by1 = b.x, b.y
                    bx2, by2 = b_right, b_bottom
                    overlap_x = max(0.0, min(ax2, bx2) - max(ax1, bx1))
                    overlap_y = max(0.0, min(ay2, by2) - max(ay1, by1))
                    overlap_area = overlap_x * overlap_y
                    if overlap_area > 0:
                        issues.append(
                            f"Overlap detected: '{a.name}' and '{b.name}' "
                            f"(area={overlap_area:.0f}px)"
                        )

        for element in elements:
            if element.element_type in (WidgetType.LABEL, WidgetType.BUTTON):
                font_size = element.style.get("font_size", 14)
                if isinstance(font_size, (int, float)) and font_size < 10:
                    issues.append(
                        f"Accessibility: '{element.name}' has small font size ({font_size}px)"
                    )
            if element.element_type == WidgetType.ICON_BUTTON:
                if element.width < 40 or element.height < 40:
                    issues.append(
                        f"Accessibility: '{element.name}' icon button is too small "
                        f"({element.width}x{element.height}), minimum 40x40"
                    )
            if element.style.get("opacity", 1.0) < 0.3 and element.visible:
                issues.append(
                    f"Accessibility: '{element.name}' has very low opacity "
                    f"({element.style['opacity']})"
                )

        if not layout.root_element_id or layout.root_element_id not in layout.elements:
            issues.append("Layout has no valid root element")

        return issues

    # ------------------------------------------------------------------
    # Export
    # ------------------------------------------------------------------

    def export_layout(self, layout_id: str) -> Optional[Dict[str, Any]]:
        layout = self._layouts.get(layout_id)
        if layout is None:
            return None
        return {
            "format": "sparkai_ui_layout_v1",
            "layout": layout.to_dict(),
            "theme_preset": THEME_PRESETS.get(layout.theme, {}),
            "validated": len(self.validate_layout(layout_id)) == 0,
        }

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------

    def get_layout(self, layout_id: str) -> Optional[UILayout]:
        return self._layouts.get(layout_id)

    def get_session(self, session_id: str) -> Optional[DesignSession]:
        return self._sessions.get(session_id)

    def list_layouts(self) -> List[UILayout]:
        return list(self._layouts.values())

    # ------------------------------------------------------------------
    # Stats
    # ------------------------------------------------------------------

    def get_stats(self) -> Dict[str, Any]:
        total_elements = sum(
            len(layout.elements) for layout in self._layouts.values()
        )
        element_count = total_elements
        layout_count = len(self._layouts)
        return {
            "total_layouts": layout_count,
            "total_sessions": len(self._sessions),
            "total_elements": element_count,
            "elements_per_layout": round(
                element_count / max(layout_count, 1), 2
            ),
            "layouts_by_type": dict(self._layouts_by_type),
            "most_used_widgets": sorted(
                self._widget_usage.items(), key=lambda x: x[1], reverse=True
            )[:5],
            "themes_used": dict(self._theme_usage),
        }

    # ------------------------------------------------------------------
    # Internal Helpers
    # ------------------------------------------------------------------

    def _compute_complexity(self, layout: UILayout) -> float:
        element_count = len(layout.elements)
        depth = self._compute_max_depth(layout)
        base = element_count * 0.5 + depth * 1.2
        unique_types = len({e.element_type for e in layout.elements.values()})
        return round(base + unique_types * 0.8, 2)

    def _compute_max_depth(self, layout: UILayout) -> int:
        if not layout.root_element_id:
            return 0
        children_map: Dict[str, List[str]] = {}
        for eid, element in layout.elements.items():
            children_map[eid] = list(element.children)

        def dfs(node_id: str) -> int:
            if node_id not in children_map or not children_map[node_id]:
                return 1
            return 1 + max(dfs(child) for child in children_map[node_id])

        if layout.root_element_id in layout.elements:
            return dfs(layout.root_element_id)
        return 0

    def _compute_aligned_position(
        self, element: UIElement, canvas_w: int, canvas_h: int
    ) -> Tuple[float, float]:
        alignment = element.alignment
        if alignment == Alignment.TOP_LEFT:
            return (element.x, element.y)
        elif alignment == Alignment.TOP_CENTER:
            return (canvas_w / 2 - element.width / 2 + element.x, element.y)
        elif alignment == Alignment.TOP_RIGHT:
            return (canvas_w - element.width + element.x, element.y)
        elif alignment == Alignment.MIDDLE_LEFT:
            return (element.x, canvas_h / 2 - element.height / 2 + element.y)
        elif alignment == Alignment.CENTER:
            return (
                canvas_w / 2 - element.width / 2 + element.x,
                canvas_h / 2 - element.height / 2 + element.y,
            )
        elif alignment == Alignment.MIDDLE_RIGHT:
            return (
                canvas_w - element.width + element.x,
                canvas_h / 2 - element.height / 2 + element.y,
            )
        elif alignment == Alignment.BOTTOM_LEFT:
            return (element.x, canvas_h - element.height + element.y)
        elif alignment == Alignment.BOTTOM_CENTER:
            return (
                canvas_w / 2 - element.width / 2 + element.x,
                canvas_h - element.height + element.y,
            )
        elif alignment == Alignment.BOTTOM_RIGHT:
            return (
                canvas_w - element.width + element.x,
                canvas_h - element.height + element.y,
            )
        elif alignment == Alignment.STRETCH:
            return (0.0, 0.0)
        return (element.x, element.y)


def get_ui_designer() -> UIDesigner:
    return UIDesigner.get_instance()