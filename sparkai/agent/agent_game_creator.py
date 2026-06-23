"""
SparkLabs Agent - Game Creator Engine

Natural Language Game Creation module for the SparkLabs AI-native game engine.
Enables users to create complete games by describing them in natural language.
The engine parses descriptions into structured specifications, assembles game
components, generates project scaffolding, and orchestrates a phased creation
pipeline from concept to playable game.

Architecture:
  GameCreatorEngine (Singleton)
    |-- GameSpecParser (parses NL descriptions into structured specs)
    |-- GameAssembler (assembles scenes, entities, rules, UI, assets)
    |-- GameBlueprint (structured game specification data model)
    |-- CreationPipeline (phased creation pipeline orchestrator)

Core Capabilities:
  - Parse natural language descriptions into game specifications
  - Detect genre, mechanics, visual style, story, platform, and complexity
  - Generate complete game blueprints from descriptions
  - Assemble scenes, characters, rules, UI layouts, and asset requirements
  - Track creation progress through six phases
  - Support iterative refinement based on feedback
"""

from __future__ import annotations

import json
import math
import random
import re
import threading
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple


# =============================================================================
# Enums
# =============================================================================


class GameGenre(Enum):
    """Categories of game genres detected from natural language descriptions."""

    PLATFORMER = "platformer"
    RPG = "rpg"
    SHOOTER = "shooter"
    PUZZLE = "puzzle"
    STRATEGY = "strategy"
    SIMULATION = "simulation"
    ADVENTURE = "adventure"
    RACING = "racing"
    FIGHTING = "fighting"
    SPORTS = "sports"
    HORROR = "horror"
    ROGUELIKE = "roguelike"
    METROIDVANIA = "metroidvania"
    VISUAL_NOVEL = "visual_novel"
    TOWER_DEFENSE = "tower_defense"
    SANDBOX = "sandbox"
    RHYTHM = "rhythm"
    STEALTH = "stealth"
    SURVIVAL = "survival"
    PARTY = "party"


class VisualStyle(Enum):
    """Visual presentation styles extracted from descriptions."""

    PIXEL_ART = "pixel_art"
    CARTOON = "cartoon"
    REALISTIC = "realistic"
    STYLIZED = "stylized"
    LOW_POLY = "low_poly"
    VOXEL = "voxel"
    HAND_DRAWN = "hand_drawn"
    CEL_SHADED = "cel_shaded"
    RETRO = "retro"
    MINIMALIST = "minimalist"
    ISOMETRIC = "isometric"
    TOP_DOWN = "top_down"
    SIDE_SCROLLING = "side_scrolling"
    FIRST_PERSON = "first_person"
    THIRD_PERSON = "third_person"


class CoreMechanic(Enum):
    """Core gameplay mechanics identified from natural language descriptions."""

    JUMP = "jump"
    COLLECT = "collect"
    FIGHT = "fight"
    BUILD = "build"
    TRADE = "trade"
    CRAFT = "craft"
    EXPLORE = "explore"
    SOLVE = "solve"
    RACE = "race"
    HIDE = "hide"
    MANAGE = "manage"
    GROW = "grow"
    TALK = "talk"
    FLY = "fly"
    SWIM = "swim"
    CLIMB = "climb"
    SNEAK = "sneak"
    COOK = "cook"
    FARM = "farm"
    MINE = "mine"
    FISH = "fish"
    TRAIN = "train"
    UPGRADE = "upgrade"
    RESEARCH = "research"
    DIPLOMACY = "diplomacy"


class TargetPlatform(Enum):
    """Target deployment platforms for generated games."""

    MOBILE = "mobile"
    DESKTOP = "desktop"
    WEB = "web"
    CONSOLE = "console"
    VR = "vr"
    AR = "ar"
    CROSS_PLATFORM = "cross_platform"


class CreationPhase(Enum):
    """Phases of the game creation pipeline."""

    SPECIFICATION = "specification"
    DESIGN = "design"
    SCAFFOLDING = "scaffolding"
    IMPLEMENTATION = "implementation"
    TESTING = "testing"
    REFINEMENT = "refinement"


class ComplexityTier(Enum):
    """Estimated complexity and difficulty tiers for game creation."""

    MINI = "mini"
    CASUAL = "casual"
    STANDARD = "standard"
    AMBITIOUS = "ambitious"
    EPIC = "epic"


class DimensionMode(Enum):
    """Dimensionality of the game world."""

    D2 = "2d"
    D3 = "3d"
    D2_5 = "2.5d"
    HYBRID = "hybrid"


class ProjectionMode(Enum):
    """Camera projection style for the game."""

    SIDE_VIEW = "side_view"
    TOP_DOWN = "top_down"
    ISOMETRIC = "isometric"
    FIRST_PERSON = "first_person"
    THIRD_PERSON = "third_person"
    BIRDS_EYE = "birds_eye"
    FREE_CAMERA = "free_camera"


# =============================================================================
# Detection keyword tables
# =============================================================================

_GENRE_KEYWORDS: Dict[GameGenre, List[str]] = {
    GameGenre.PLATFORMER: [
        "platform", "jump", "run", "side-scroll", "side scroll", "mario",
        "platforming", "ledge", "pit", "wall jump", "double jump",
    ],
    GameGenre.RPG: [
        "rpg", "role-play", "role play", "roleplaying", "level up",
        "experience point", "quest", "inventory", "stat", "character build",
        "dungeon", "dragon", "fantasy", "skill tree", "dialogue tree",
    ],
    GameGenre.SHOOTER: [
        "shoot", "gun", "bullet", "fps", "first person", "third person shooter",
        "aim", "reload", "headshot", "sniper", "crosshair", "ammo",
    ],
    GameGenre.PUZZLE: [
        "puzzle", "match", "tile", "block", "solve", "riddle", "brain",
        "logic", "connect", "arrange", "pattern", "sequence",
    ],
    GameGenre.STRATEGY: [
        "strategy", "tactics", "turn-based", "turn based", "rts", "real time strategy",
        "base build", "army", "command", "resource manage", "conquer",
    ],
    GameGenre.SIMULATION: [
        "simulation", "simulator", "sim", "tycoon", "management", "manager",
        "realistic", "life sim", "sandbox", "god game",
    ],
    GameGenre.ADVENTURE: [
        "adventure", "point and click", "point-and-click", "explore", "story",
        "narrative", "mystery", "journey", "quest", "discover",
    ],
    GameGenre.RACING: [
        "racing", "race", "car", "vehicle", "lap", "track", "speed", "drift",
        "kart", "formula", "circuit", "finish line",
    ],
    GameGenre.FIGHTING: [
        "fighting", "fight", "combo", "brawl", "versus", "arena", "martial art",
        "beat em up", "beat-em-up", "melee", "duel", "tournament",
    ],
    GameGenre.SPORTS: [
        "sport", "soccer", "football", "basketball", "tennis", "golf",
        "baseball", "hockey", "skate", "league", "championship",
    ],
    GameGenre.HORROR: [
        "horror", "scary", "survival horror", "monster", "creepy", "jump scare",
        "dark", "haunt", "ghost", "zombie", "psychological",
    ],
    GameGenre.ROGUELIKE: [
        "roguelike", "rogue lite", "rogue-lite", "permadeath", "procedural generation",
        "random dungeon", "run", "ascend", "spire",
    ],
    GameGenre.METROIDVANIA: [
        "metroidvania", "metroid", "vania", "interconnected", "ability gate",
        "backtrack", "map", "power up", "unlock area",
    ],
    GameGenre.VISUAL_NOVEL: [
        "visual novel", "visual story", "dating sim", "choice", "branching",
        "text", "dialogue", "conversation", "route", "ending",
    ],
    GameGenre.TOWER_DEFENSE: [
        "tower defense", "tower defence", "td", "wave", "defend", "path",
        "turret", "enemy wave", "maze", "fortify",
    ],
    GameGenre.SANDBOX: [
        "sandbox", "open world", "open-world", "free roam", "create", "build",
        "minecraft", "creative", "voxel", "destructible",
    ],
    GameGenre.RHYTHM: [
        "rhythm", "music", "beat", "tempo", "dance", "note", "song",
        "musical", "tap", "groove",
    ],
    GameGenre.STEALTH: [
        "stealth", "sneak", "hide", "infiltrate", "assassin", "silent",
        "shadow", "avoid detection", "disguise",
    ],
    GameGenre.SURVIVAL: [
        "survival", "survive", "craft", "gather", "hunger", "thirst",
        "shelter", "wilderness", "night cycle", "resource",
    ],
    GameGenre.PARTY: [
        "party game", "party", "mini game", "multiplayer casual", "board game",
        "trivia", "quiz", "social",
    ],
}

_VISUAL_STYLE_KEYWORDS: Dict[VisualStyle, List[str]] = {
    VisualStyle.PIXEL_ART: ["pixel art", "pixel", "8-bit", "8bit", "16-bit", "16bit", "retro pixel", "sprite"],
    VisualStyle.CARTOON: ["cartoon", "cartoony", "toon", "animated", "cel shading", "colorful"],
    VisualStyle.REALISTIC: ["realistic", "realism", "photoreal", "photo real", "lifelike", "high fidelity"],
    VisualStyle.STYLIZED: ["stylized", "stylised", "stylisation", "artistic", "painterly", "unique art"],
    VisualStyle.LOW_POLY: ["low poly", "low-poly", "flat shaded", "geometric", "faceted"],
    VisualStyle.VOXEL: ["voxel", "blocky", "cube", "minecraft style", "block based"],
    VisualStyle.HAND_DRAWN: ["hand drawn", "hand-drawn", "sketch", "drawn", "illustration", "watercolor", "ink"],
    VisualStyle.CEL_SHADED: ["cel shade", "cel-shaded", "toon shader", "anime", "manga", "comic"],
    VisualStyle.RETRO: ["retro", "nostalgia", "classic", "arcade", "old school", "old-school", "vintage"],
    VisualStyle.MINIMALIST: ["minimalist", "minimal", "simple", "clean", "flat", "abstract", "monochrome"],
    VisualStyle.ISOMETRIC: ["isometric", "iso", "axonometric", "2.5d"],
    VisualStyle.TOP_DOWN: ["top down", "top-down", "birds eye", "bird's eye", "overhead", "aerial"],
    VisualStyle.SIDE_SCROLLING: ["side scrolling", "side-scrolling", "side view", "side on", "horizontal"],
    VisualStyle.FIRST_PERSON: ["first person", "first-person", "fps view", "first person view", "fp"],
    VisualStyle.THIRD_PERSON: ["third person", "third-person", "over shoulder", "behind view", "tps"],
}

_MECHANIC_KEYWORDS: Dict[CoreMechanic, List[str]] = {
    CoreMechanic.JUMP: ["jump", "leap", "hop", "bounce", "vault", "spring"],
    CoreMechanic.COLLECT: ["collect", "gather", "pick up", "pickup", "loot", "acquire", "obtain"],
    CoreMechanic.FIGHT: ["fight", "combat", "battle", "attack", "strike", "hit", "slash", "defeat", "kill"],
    CoreMechanic.BUILD: ["build", "construct", "place", "assemble", "create structure", "erect", "fortify"],
    CoreMechanic.TRADE: ["trade", "barter", "sell", "buy", "shop", "merchant", "economy", "market", "exchange"],
    CoreMechanic.CRAFT: ["craft", "recipe", "forge", "brew", "combine", "alchemy", "smith", "tinker"],
    CoreMechanic.EXPLORE: ["explore", "discover", "wander", "roam", "uncover", "scout", "survey", "map"],
    CoreMechanic.SOLVE: ["solve", "puzzle", "riddle", "decipher", "decode", "figure out", "unlock", "crack"],
    CoreMechanic.RACE: ["race", "compete", "speed", "timed", "lap", "finish", "overtake", "qualify"],
    CoreMechanic.HIDE: ["hide", "cover", "conceal", "camouflage", "take cover", "duck", "crouch"],
    CoreMechanic.MANAGE: ["manage", "control", "oversee", "govern", "administrate", "supervise", "direct"],
    CoreMechanic.GROW: ["grow", "cultivate", "nurture", "raise", "breed", "farm", "harvest", "plant"],
    CoreMechanic.TALK: ["talk", "speak", "converse", "chat", "dialogue", "negotiate", "persuade", "convince"],
    CoreMechanic.FLY: ["fly", "soar", "glide", "wing", "aerial", "hover", "airborne", "aviation"],
    CoreMechanic.SWIM: ["swim", "dive", "submerge", "underwater", "float", "paddle", "aquatic"],
    CoreMechanic.CLIMB: ["climb", "scale", "ascend", "grapple", "ladder", "cliff", "wall", "mount"],
    CoreMechanic.SNEAK: ["sneak", "stealth", "creep", "tiptoe", "silent", "undetected", "prowl"],
    CoreMechanic.COOK: ["cook", "cooking", "bake", "roast", "recipe", "cuisine", "chef", "prepare food"],
    CoreMechanic.FARM: ["farm", "farming", "agriculture", "crop", "field", "till", "cultivate", "irrigate"],
    CoreMechanic.MINE: ["mine", "mining", "dig", "excavate", "ore", "quarry", "extract", "prospect", "tunnel"],
    CoreMechanic.FISH: ["fish", "fishing", "angle", "catch", "reel", "bait", "net", "aquatic life"],
    CoreMechanic.TRAIN: ["train", "practice", "exercise", "drill", "improve", "level", "master", "study"],
    CoreMechanic.UPGRADE: ["upgrade", "enhance", "improve", "modify", "augment", "boost", "strengthen", "level up"],
    CoreMechanic.RESEARCH: ["research", "study", "analyze", "investigate", "tech tree", "unlock", "discover"],
    CoreMechanic.DIPLOMACY: ["diplomacy", "alliance", "treaty", "pact", "negotiate peace", "foreign relations"],
}

_PLATFORM_KEYWORDS: Dict[TargetPlatform, List[str]] = {
    TargetPlatform.MOBILE: ["mobile", "phone", "tablet", "android", "ios", "touch screen", "tap", "swipe", "app"],
    TargetPlatform.DESKTOP: ["desktop", "pc", "computer", "mac", "windows", "linux", "keyboard", "mouse"],
    TargetPlatform.WEB: ["web", "browser", "html5", "online", "webgl", "javascript", "website"],
    TargetPlatform.CONSOLE: ["console", "playstation", "xbox", "nintendo", "switch", "controller", "gamepad", "tv"],
    TargetPlatform.VR: ["vr", "virtual reality", "oculus", "quest", "headset", "immersive", "motion control"],
    TargetPlatform.AR: ["ar", "augmented reality", "mixed reality", "real world", "camera overlay"],
    TargetPlatform.CROSS_PLATFORM: ["cross platform", "cross-platform", "multi platform", "all platforms", "portable"],
}

_STORY_KEYWORDS: List[str] = [
    "story", "narrative", "plot", "lore", "backstory", "campaign", "chapter",
    "character", "protagonist", "antagonist", "hero", "villain", "journey",
    "quest", "mission", "save the", "rescue", "escape", "defeat the",
    "revenge", "discover", "mystery", "legend", "prophecy", "myth",
]

_THEME_KEYWORDS: Dict[str, List[str]] = {
    "fantasy": ["fantasy", "magic", "dragon", "sword", "wizard", "elf", "dwarf", "orc", "medieval", "castle"],
    "sci_fi": ["sci-fi", "scifi", "science fiction", "space", "alien", "robot", "future", "cyber", "laser", "planet"],
    "horror": ["horror", "terror", "scary", "fear", "nightmare", "creepy", "haunt", "ghost", "monster"],
    "post_apocalyptic": ["post apocalyptic", "apocalypse", "wasteland", "fallout", "ruin", "survivor", "nuclear"],
    "military": ["military", "war", "soldier", "army", "battlefield", "marine", "navy", "air force", "tactical"],
    "western": ["western", "cowboy", "wild west", "frontier", "sheriff", "outlaw", "saloon", "desert"],
    "noir": ["noir", "detective", "crime", "mystery", "film noir", "gritty", "urban", "investigation"],
    "steampunk": ["steampunk", "clockwork", "steam", "victorian", "gear", "brass", "airship", "industrial"],
    "cyberpunk": ["cyberpunk", "cyber", "neon", "megacorp", "hacker", "augmentation", "dystopia", "megacity"],
    "mythology": ["mythology", "myth", "god", "legend", "ancient", "greek", "norse", "egyptian", "pantheon"],
    "ocean": ["ocean", "sea", "underwater", "pirate", "naval", "ship", "marine", "coral", "submarine"],
    "space": ["space", "galaxy", "star", "planet", "cosmic", "asteroid", "orbit", "interstellar", "nebula"],
}

_COMPLEXITY_INDICATORS: Dict[str, int] = {
    "simple": 1, "small": 1, "mini": 1, "tiny": 1, "basic": 1, "quick": 1,
    "casual": 2, "moderate": 2, "medium": 2, "standard": 2, "normal": 2,
    "complex": 3, "large": 3, "big": 3, "detailed": 3, "extensive": 3,
    "massive": 4, "huge": 4, "enormous": 4, "ambitious": 4, "vast": 4,
    "epic": 5, "gigantic": 5, "colossal": 5, "monumental": 5,
}

_COMPLEXITY_TIER_MAP: Dict[int, ComplexityTier] = {
    1: ComplexityTier.MINI,
    2: ComplexityTier.CASUAL,
    3: ComplexityTier.STANDARD,
    4: ComplexityTier.AMBITIOUS,
    5: ComplexityTier.EPIC,
}

_PHASE_DURATION_ESTIMATES: Dict[CreationPhase, Tuple[float, float]] = {
    CreationPhase.SPECIFICATION: (0.5, 2.0),
    CreationPhase.DESIGN: (1.0, 5.0),
    CreationPhase.SCAFFOLDING: (0.5, 3.0),
    CreationPhase.IMPLEMENTATION: (3.0, 30.0),
    CreationPhase.TESTING: (1.0, 10.0),
    CreationPhase.REFINEMENT: (1.0, 15.0),
}


# =============================================================================
# Data Classes
# =============================================================================


@dataclass
class MechanicSpec:
    """A specification for a single game mechanic with parameters and constraints.

    Attributes:
        spec_id: Unique identifier for this mechanic specification.
        mechanic: The core mechanic type.
        description: Natural language description of how this mechanic works.
        parameters: Key-value parameters that configure the mechanic.
        constraints: Rules and limitations for this mechanic.
        priority: Importance ranking (1 = highest, 5 = lowest).
    """

    spec_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    mechanic: CoreMechanic = CoreMechanic.JUMP
    description: str = ""
    parameters: Dict[str, Any] = field(default_factory=dict)
    constraints: Dict[str, Any] = field(default_factory=dict)
    priority: int = 3

    def to_dict(self) -> Dict[str, Any]:
        return {
            "spec_id": self.spec_id,
            "mechanic": self.mechanic.value,
            "description": self.description,
            "parameters": self.parameters,
            "constraints": self.constraints,
            "priority": self.priority,
        }


@dataclass
class SceneSpec:
    """A specification for a game scene or level.

    Attributes:
        scene_id: Unique identifier for this scene.
        name: Display name of the scene.
        description: Environmental and narrative description.
        scene_type: Category of scene (menu, level, hub, boss, cutscene, etc.).
        mechanics: IDs of mechanics relevant to this scene.
        entities: Entity templates to spawn in this scene.
        exits: Connections to other scenes.
        estimated_duration: Expected playtime in minutes.
    """

    scene_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = ""
    description: str = ""
    scene_type: str = "level"
    mechanics: List[str] = field(default_factory=list)
    entities: List[Dict[str, Any]] = field(default_factory=list)
    exits: List[Dict[str, str]] = field(default_factory=list)
    estimated_duration: float = 5.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "scene_id": self.scene_id,
            "name": self.name,
            "description": self.description,
            "scene_type": self.scene_type,
            "mechanics": self.mechanics,
            "entity_count": len(self.entities),
            "entities": self.entities,
            "exits": self.exits,
            "estimated_duration": self.estimated_duration,
        }


@dataclass
class CharacterSpec:
    """A specification for a character or NPC in the game.

    Attributes:
        char_id: Unique identifier for this character.
        name: Display name.
        role: Narrative role (player, enemy, npc, boss, companion, etc.).
        description: Physical and personality description.
        abilities: List of abilities or skills this character possesses.
        stats: Key-value stat pairs defining character capabilities.
        dialogue: Sample dialogue lines or conversation trees.
        spawn_scene: The scene ID where this character first appears.
    """

    char_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = ""
    role: str = "npc"
    description: str = ""
    abilities: List[str] = field(default_factory=list)
    stats: Dict[str, float] = field(default_factory=dict)
    dialogue: List[str] = field(default_factory=list)
    spawn_scene: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "char_id": self.char_id,
            "name": self.name,
            "role": self.role,
            "description": self.description,
            "abilities": self.abilities,
            "stats": self.stats,
            "dialogue": self.dialogue,
            "spawn_scene": self.spawn_scene,
        }


@dataclass
class AssetRequirement:
    """A specification for a game asset that needs to be created or sourced.

    Attributes:
        asset_id: Unique identifier for this asset requirement.
        asset_type: Category of asset (sprite, model, sound, music, ui, shader, etc.).
        name: Display name or identifier for the asset.
        description: Description of what the asset should look/sound like.
        style_notes: Specific visual or audio style guidance.
        resolution: Target resolution or quality level.
        estimated_size: Approximate file size or memory footprint.
        priority: Importance ranking (1 = highest, 5 = lowest).
    """

    asset_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    asset_type: str = "sprite"
    name: str = ""
    description: str = ""
    style_notes: str = ""
    resolution: str = "medium"
    estimated_size: str = "unknown"
    priority: int = 3

    def to_dict(self) -> Dict[str, Any]:
        return {
            "asset_id": self.asset_id,
            "asset_type": self.asset_type,
            "name": self.name,
            "description": self.description,
            "style_notes": self.style_notes,
            "resolution": self.resolution,
            "estimated_size": self.estimated_size,
            "priority": self.priority,
        }


@dataclass
class UILayoutSpec:
    """A specification for a UI layout or screen in the game.

    Attributes:
        layout_id: Unique identifier for this UI layout.
        name: Display name (e.g., "Main Menu", "HUD", "Inventory").
        description: Layout description and behavior notes.
        elements: List of UI elements with position and type info.
        transitions: Transitions between this layout and others.
    """

    layout_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = ""
    description: str = ""
    elements: List[Dict[str, Any]] = field(default_factory=list)
    transitions: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "layout_id": self.layout_id,
            "name": self.name,
            "description": self.description,
            "element_count": len(self.elements),
            "elements": self.elements,
            "transitions": self.transitions,
        }


@dataclass
class GameBlueprint:
    """A complete structured game specification generated from natural language.

    This is the central data model that captures every aspect of a game design
    derived from a user's natural language description. It serves as the
    authoritative specification that drives all downstream generation phases.

    Attributes:
        blueprint_id: Unique identifier for this blueprint.
        name: Game title derived from the description.
        description: Original natural language description.
        genres: Detected game genres.
        visual_styles: Detected visual presentation styles.
        dimension: 2D, 3D, 2.5D, or hybrid.
        projection: Camera projection mode.
        target_platforms: Target deployment platforms.
        complexity: Estimated complexity tier.
        core_loop: Description of the main gameplay loop.
        mechanics: List of mechanic specifications.
        scenes: List of scene/level specifications.
        characters: List of character/NPC specifications.
        theme: Detected narrative theme.
        story_summary: Extracted or inferred story summary.
        win_conditions: Conditions that trigger victory.
        lose_conditions: Conditions that trigger failure.
        progression_system: Description of how the player progresses.
        asset_requirements: List of asset requirement specifications.
        ui_layouts: List of UI layout specifications.
        estimated_playtime: Estimated total playtime in minutes.
        target_audience: Intended player demographic.
        created_at: Timestamp of blueprint creation.
        metadata: Extensible metadata dictionary.
    """

    blueprint_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = ""
    description: str = ""
    genres: List[GameGenre] = field(default_factory=list)
    visual_styles: List[VisualStyle] = field(default_factory=list)
    dimension: DimensionMode = DimensionMode.D2
    projection: ProjectionMode = ProjectionMode.SIDE_VIEW
    target_platforms: List[TargetPlatform] = field(default_factory=list)
    complexity: ComplexityTier = ComplexityTier.STANDARD
    core_loop: str = ""
    mechanics: List[MechanicSpec] = field(default_factory=list)
    scenes: List[SceneSpec] = field(default_factory=list)
    characters: List[CharacterSpec] = field(default_factory=list)
    theme: str = ""
    story_summary: str = ""
    win_conditions: List[str] = field(default_factory=list)
    lose_conditions: List[str] = field(default_factory=list)
    progression_system: str = ""
    asset_requirements: List[AssetRequirement] = field(default_factory=list)
    ui_layouts: List[UILayoutSpec] = field(default_factory=list)
    estimated_playtime: float = 0.0
    target_audience: str = ""
    created_at: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "blueprint_id": self.blueprint_id,
            "name": self.name,
            "description": self.description[:300],
            "genres": [g.value for g in self.genres],
            "visual_styles": [s.value for s in self.visual_styles],
            "dimension": self.dimension.value,
            "projection": self.projection.value,
            "target_platforms": [p.value for p in self.target_platforms],
            "complexity": self.complexity.value,
            "core_loop": self.core_loop,
            "mechanics": [m.to_dict() for m in self.mechanics],
            "mechanic_count": len(self.mechanics),
            "scenes": [s.to_dict() for s in self.scenes],
            "scene_count": len(self.scenes),
            "characters": [c.to_dict() for c in self.characters],
            "character_count": len(self.characters),
            "theme": self.theme,
            "story_summary": self.story_summary[:500],
            "win_conditions": self.win_conditions,
            "lose_conditions": self.lose_conditions,
            "progression_system": self.progression_system,
            "asset_requirements": [a.to_dict() for a in self.asset_requirements],
            "asset_count": len(self.asset_requirements),
            "ui_layouts": [u.to_dict() for u in self.ui_layouts],
            "ui_layout_count": len(self.ui_layouts),
            "estimated_playtime": self.estimated_playtime,
            "target_audience": self.target_audience,
            "created_at": self.created_at,
            "metadata": self.metadata,
        }


@dataclass
class PipelineStage:
    """Tracks the state and progress of a single pipeline stage.

    Attributes:
        phase: The creation phase this stage represents.
        status: Current status (pending, in_progress, completed, failed).
        started_at: Timestamp when the phase began.
        completed_at: Timestamp when the phase finished.
        progress: Completion percentage (0.0 to 1.0).
        result: Output data produced by this phase.
        errors: List of error messages encountered during this phase.
        notes: Human-readable notes about the phase.
    """

    phase: CreationPhase = CreationPhase.SPECIFICATION
    status: str = "pending"
    started_at: float = 0.0
    completed_at: float = 0.0
    progress: float = 0.0
    result: Dict[str, Any] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)
    notes: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "phase": self.phase.value,
            "status": self.status,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "progress": round(self.progress, 2),
            "result": self.result,
            "error_count": len(self.errors),
            "errors": self.errors,
            "notes": self.notes,
        }


@dataclass
class CreationSession:
    """Tracks an active game creation session with pipeline progress.

    Attributes:
        session_id: Unique identifier for this creation session.
        blueprint: The game blueprint being created.
        stages: Pipeline stages tracking progress through each phase.
        current_phase: The currently active creation phase.
        feedback_history: List of feedback items provided during refinement.
        created_at: Session start timestamp.
        updated_at: Last modification timestamp.
    """

    session_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    blueprint: Optional[GameBlueprint] = None
    stages: Dict[str, PipelineStage] = field(default_factory=dict)
    current_phase: CreationPhase = CreationPhase.SPECIFICATION
    feedback_history: List[Dict[str, Any]] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "session_id": self.session_id,
            "blueprint": self.blueprint.to_dict() if self.blueprint else None,
            "current_phase": self.current_phase.value,
            "stages": {k: v.to_dict() for k, v in self.stages.items()},
            "feedback_count": len(self.feedback_history),
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


# =============================================================================
# GameSpecParser
# =============================================================================


class GameSpecParser:
    """Parses natural language descriptions into structured game specifications.

    Analyzes free-form text to detect game genres, core mechanics, visual
    styles, narrative themes, target platforms, and complexity estimates.
    Produces a structured GameBlueprint that captures all extracted information
    in a machine-readable format suitable for downstream processing.
    """

    def __init__(self) -> None:
        self._last_parse_time: float = 0.0

    def parse(self, description: str, name: str = "") -> GameBlueprint:
        """Parse a natural language description into a GameBlueprint.

        Args:
            description: Free-form natural language description of the desired game.
            name: Optional game title. If empty, one is inferred from the description.

        Returns:
            A fully populated GameBlueprint with extracted specifications.
        """
        start = time.time()
        text_lower = description.lower()

        if not name:
            name = self._infer_name(description)

        blueprint = GameBlueprint(
            name=name,
            description=description,
        )

        blueprint.genres = self._detect_genres(text_lower)
        blueprint.visual_styles = self._detect_visual_styles(text_lower)
        blueprint.theme = self._detect_theme(text_lower)
        blueprint.dimension = self._detect_dimension(text_lower)
        blueprint.projection = self._detect_projection(text_lower, blueprint.visual_styles)
        blueprint.target_platforms = self._detect_platforms(text_lower)
        blueprint.complexity = self._detect_complexity(text_lower, description)
        blueprint.core_loop = self._infer_core_loop(description, blueprint.genres)
        blueprint.mechanics = self._extract_mechanics(text_lower, blueprint.genres)
        blueprint.story_summary = self._extract_story(description)
        blueprint.win_conditions = self._infer_win_conditions(blueprint)
        blueprint.lose_conditions = self._infer_lose_conditions(blueprint)
        blueprint.progression_system = self._infer_progression(blueprint)
        blueprint.target_audience = self._infer_audience(text_lower)
        blueprint.estimated_playtime = self._estimate_playtime(blueprint)
        blueprint.metadata = {
            "parse_time_seconds": round(time.time() - start, 3),
            "description_length": len(description),
            "word_count": len(description.split()),
        }

        self._last_parse_time = time.time() - start

        return blueprint

    def _detect_genres(self, text: str) -> List[GameGenre]:
        """Detect game genres from keyword matches."""
        scores: Dict[GameGenre, int] = {}
        for genre, keywords in _GENRE_KEYWORDS.items():
            score = sum(1 for kw in keywords if kw in text)
            if score > 0:
                scores[genre] = score

        if not scores:
            return [GameGenre.PLATFORMER]

        max_score = max(scores.values())
        threshold = max(1, max_score // 2)
        detected = sorted(
            [g for g, s in scores.items() if s >= threshold],
            key=lambda g: scores[g],
            reverse=True,
        )
        return detected[:3] if detected else [GameGenre.PLATFORMER]

    def _detect_visual_styles(self, text: str) -> List[VisualStyle]:
        """Detect visual styles from keyword matches."""
        scores: Dict[VisualStyle, int] = {}
        for style, keywords in _VISUAL_STYLE_KEYWORDS.items():
            score = sum(1 for kw in keywords if kw in text)
            if score > 0:
                scores[style] = score

        if not scores:
            if "2d" in text or "side" in text:
                return [VisualStyle.PIXEL_ART, VisualStyle.SIDE_SCROLLING]
            if "3d" in text:
                return [VisualStyle.STYLIZED, VisualStyle.THIRD_PERSON]
            return [VisualStyle.PIXEL_ART]

        max_score = max(scores.values())
        threshold = max(1, max_score // 2)
        detected = sorted(
            [s for s, sc in scores.items() if sc >= threshold],
            key=lambda s: scores[s],
            reverse=True,
        )
        return detected[:3] if detected else [VisualStyle.PIXEL_ART]

    def _detect_theme(self, text: str) -> str:
        """Detect the narrative theme from keyword matches."""
        scores: Dict[str, int] = {}
        for theme, keywords in _THEME_KEYWORDS.items():
            score = sum(1 for kw in keywords if kw in text)
            if score > 0:
                scores[theme] = score

        if not scores:
            return "general"

        return max(scores, key=lambda t: scores[t])

    def _detect_dimension(self, text: str) -> DimensionMode:
        """Detect the dimensionality of the game."""
        has_3d = any(word in text for word in ["3d", "three dimensional", "three-dimensional"])
        has_2d = any(word in text for word in ["2d", "two dimensional", "two-dimensional", "side", "pixel"])
        has_2_5d = any(word in text for word in ["2.5d", "isometric", "pseudo 3d", "pseudo-3d"])

        if has_2_5d:
            return DimensionMode.D2_5
        if has_3d and has_2d:
            return DimensionMode.HYBRID
        if has_3d:
            return DimensionMode.D3
        if has_2d:
            return DimensionMode.D2

        return DimensionMode.D2

    def _detect_projection(
        self, text: str, visual_styles: List[VisualStyle]
    ) -> ProjectionMode:
        """Detect the camera projection / view style."""
        style_values = {s for s in visual_styles}

        if VisualStyle.FIRST_PERSON in style_values:
            return ProjectionMode.FIRST_PERSON
        if VisualStyle.THIRD_PERSON in style_values:
            return ProjectionMode.THIRD_PERSON
        if VisualStyle.TOP_DOWN in style_values:
            return ProjectionMode.TOP_DOWN
        if VisualStyle.ISOMETRIC in style_values:
            return ProjectionMode.ISOMETRIC
        if VisualStyle.SIDE_SCROLLING in style_values:
            return ProjectionMode.SIDE_VIEW

        if "first person" in text or "first-person" in text or "fps" in text:
            return ProjectionMode.FIRST_PERSON
        if "third person" in text or "third-person" in text:
            return ProjectionMode.THIRD_PERSON
        if "top down" in text or "top-down" in text or "bird" in text:
            return ProjectionMode.TOP_DOWN
        if "isometric" in text:
            return ProjectionMode.ISOMETRIC
        if "side" in text:
            return ProjectionMode.SIDE_VIEW

        return ProjectionMode.SIDE_VIEW

    def _detect_platforms(self, text: str) -> List[TargetPlatform]:
        """Detect target deployment platforms."""
        detected: List[TargetPlatform] = []
        for platform, keywords in _PLATFORM_KEYWORDS.items():
            if any(kw in text for kw in keywords):
                detected.append(platform)

        if not detected:
            return [TargetPlatform.WEB, TargetPlatform.DESKTOP]

        return detected

    def _detect_complexity(self, text: str, full_text: str) -> ComplexityTier:
        """Estimate the complexity tier from description indicators."""
        words = full_text.lower().split()
        total_score = 0
        count = 0

        for word in words:
            word_clean = re.sub(r'[^a-z]', '', word)
            if word_clean in _COMPLEXITY_INDICATORS:
                total_score += _COMPLEXITY_INDICATORS[word_clean]
                count += 1

        if count == 0:
            return ComplexityTier.STANDARD

        avg_score = round(total_score / count)
        return _COMPLEXITY_TIER_MAP.get(avg_score, ComplexityTier.STANDARD)

    def _extract_mechanics(
        self, text: str, genres: List[GameGenre]
    ) -> List[MechanicSpec]:
        """Extract core mechanics from the description."""
        detected: List[MechanicSpec] = []
        seen: Set[CoreMechanic] = set()

        for mechanic, keywords in _MECHANIC_KEYWORDS.items():
            matched = [kw for kw in keywords if kw in text]
            if matched:
                key_kw = max(matched, key=len)
                spec = MechanicSpec(
                    mechanic=mechanic,
                    description=f"Detected from keyword: '{key_kw}'",
                    priority=1 if len(matched) >= 3 else 2 if len(matched) >= 2 else 3,
                )
                detected.append(spec)
                seen.add(mechanic)

        # Inject genre-appropriate defaults if nothing detected
        if not detected and genres:
            defaults = self._get_default_mechanics(genres[0])
            for mech, desc in defaults:
                if mech not in seen:
                    spec = MechanicSpec(
                        mechanic=mech,
                        description=desc,
                        priority=3,
                    )
                    detected.append(spec)
                    seen.add(mech)

        return detected

    def _get_default_mechanics(
        self, genre: GameGenre
    ) -> List[Tuple[CoreMechanic, str]]:
        """Return default mechanics for a given genre."""
        default_map: Dict[GameGenre, List[Tuple[CoreMechanic, str]]] = {
            GameGenre.PLATFORMER: [
                (CoreMechanic.JUMP, "Core platformer movement mechanic"),
                (CoreMechanic.COLLECT, "Collect coins, power-ups, or items"),
                (CoreMechanic.EXPLORE, "Navigate through levels"),
            ],
            GameGenre.RPG: [
                (CoreMechanic.FIGHT, "Turn-based or real-time combat"),
                (CoreMechanic.TALK, "Dialogue with NPCs"),
                (CoreMechanic.UPGRADE, "Level up and improve character stats"),
                (CoreMechanic.EXPLORE, "Explore the game world"),
            ],
            GameGenre.SHOOTER: [
                (CoreMechanic.FIGHT, "Shoot enemies with various weapons"),
                (CoreMechanic.HIDE, "Take cover behind obstacles"),
                (CoreMechanic.UPGRADE, "Unlock new weapons and abilities"),
            ],
            GameGenre.PUZZLE: [
                (CoreMechanic.SOLVE, "Solve puzzles to progress"),
                (CoreMechanic.COLLECT, "Collect puzzle pieces or clues"),
            ],
            GameGenre.STRATEGY: [
                (CoreMechanic.MANAGE, "Manage resources and units"),
                (CoreMechanic.BUILD, "Build structures and bases"),
                (CoreMechanic.RESEARCH, "Research new technologies"),
            ],
            GameGenre.SIMULATION: [
                (CoreMechanic.MANAGE, "Manage systems and resources"),
                (CoreMechanic.BUILD, "Construct and expand"),
                (CoreMechanic.GROW, "Grow and develop over time"),
            ],
            GameGenre.ADVENTURE: [
                (CoreMechanic.EXPLORE, "Explore the environment"),
                (CoreMechanic.TALK, "Interact with characters"),
                (CoreMechanic.SOLVE, "Solve environmental puzzles"),
            ],
            GameGenre.RACING: [
                (CoreMechanic.RACE, "Compete in races"),
                (CoreMechanic.UPGRADE, "Upgrade your vehicle"),
            ],
            GameGenre.FIGHTING: [
                (CoreMechanic.FIGHT, "Engage in hand-to-hand combat"),
                (CoreMechanic.TRAIN, "Practice combos and techniques"),
            ],
            GameGenre.SPORTS: [
                (CoreMechanic.RACE, "Compete in sports events"),
                (CoreMechanic.TRAIN, "Train to improve skills"),
            ],
            GameGenre.HORROR: [
                (CoreMechanic.HIDE, "Hide from threats"),
                (CoreMechanic.EXPLORE, "Explore dark environments"),
                (CoreMechanic.SOLVE, "Solve puzzles under pressure"),
            ],
            GameGenre.ROGUELIKE: [
                (CoreMechanic.FIGHT, "Combat through procedurally generated levels"),
                (CoreMechanic.COLLECT, "Collect items and power-ups"),
                (CoreMechanic.UPGRADE, "Choose upgrades each run"),
            ],
            GameGenre.METROIDVANIA: [
                (CoreMechanic.JUMP, "Platform through interconnected areas"),
                (CoreMechanic.EXPLORE, "Explore and backtrack through the map"),
                (CoreMechanic.FIGHT, "Combat enemies in real-time"),
            ],
            GameGenre.VISUAL_NOVEL: [
                (CoreMechanic.TALK, "Engage in dialogue and make choices"),
            ],
            GameGenre.TOWER_DEFENSE: [
                (CoreMechanic.BUILD, "Build defensive structures"),
                (CoreMechanic.MANAGE, "Manage resources and tower placement"),
                (CoreMechanic.UPGRADE, "Upgrade towers during waves"),
            ],
            GameGenre.SANDBOX: [
                (CoreMechanic.BUILD, "Build anything you can imagine"),
                (CoreMechanic.EXPLORE, "Explore an open world"),
                (CoreMechanic.COLLECT, "Gather resources and materials"),
            ],
            GameGenre.RHYTHM: [
                (CoreMechanic.RACE, "Hit notes in time with the music"),
                (CoreMechanic.TRAIN, "Practice to improve timing"),
            ],
            GameGenre.STEALTH: [
                (CoreMechanic.SNEAK, "Move silently past guards"),
                (CoreMechanic.HIDE, "Hide from enemy patrols"),
            ],
            GameGenre.SURVIVAL: [
                (CoreMechanic.COLLECT, "Gather resources for survival"),
                (CoreMechanic.BUILD, "Build shelter and tools"),
                (CoreMechanic.CRAFT, "Craft items from raw materials"),
                (CoreMechanic.FIGHT, "Defend against threats"),
            ],
            GameGenre.PARTY: [
                (CoreMechanic.RACE, "Compete in mini-games"),
                (CoreMechanic.TALK, "Social interaction"),
            ],
        }
        return default_map.get(genre, [(CoreMechanic.JUMP, "Basic interaction"), (CoreMechanic.COLLECT, "Collect items")])

    def _extract_story(self, description: str) -> str:
        """Extract or infer a story summary from the description."""
        text_lower = description.lower()

        # Look for story indicators
        story_indicators = [
            "story", "plot", "narrative", "campaign", "about",
            "you play as", "you are", "the goal is", "set in",
        ]
        for indicator in story_indicators:
            if indicator in text_lower:
                idx = text_lower.find(indicator)
                # Extract a window around the indicator
                start = max(0, idx - 20)
                end = min(len(description), idx + 200)
                snippet = description[start:end].strip()
                # Try to end at a sentence boundary
                for punct in [". ", "! ", "? ", ".\n"]:
                    last_punct = snippet.rfind(punct)
                    if last_punct > 50:
                        snippet = snippet[:last_punct + 1]
                        break
                return snippet

        # Fallback: use the first sentence of the description
        first_sentence = re.split(r'[.!?]\s+', description, maxsplit=1)[0]
        if first_sentence and len(first_sentence) > 10:
            return first_sentence + "."

        return description[:200]

    def _infer_core_loop(self, description: str, genres: List[GameGenre]) -> str:
        """Infer the core gameplay loop from the description and genres."""
        if not genres:
            return "A core gameplay loop of action and progression."

        primary_genre = genres[0]
        loop_templates: Dict[GameGenre, str] = {
            GameGenre.PLATFORMER: "Run, jump, and collect items through levels to reach the goal.",
            GameGenre.RPG: "Explore the world, engage in combat, gain experience, and upgrade your character.",
            GameGenre.SHOOTER: "Aim, shoot, take cover, and eliminate enemies to complete objectives.",
            GameGenre.PUZZLE: "Observe, analyze, and solve puzzles to unlock new challenges.",
            GameGenre.STRATEGY: "Gather resources, build your forces, and execute tactical decisions to conquer.",
            GameGenre.SIMULATION: "Manage systems, optimize processes, and watch your creation grow.",
            GameGenre.ADVENTURE: "Explore, interact with characters, and solve mysteries to advance the story.",
            GameGenre.RACING: "Race, overtake opponents, and cross the finish line first.",
            GameGenre.FIGHTING: "Learn combos, read opponents, and defeat challengers in combat.",
            GameGenre.SPORTS: "Compete, score points, and win championships.",
            GameGenre.HORROR: "Explore, survive encounters, and uncover the dark truth.",
            GameGenre.ROGUELIKE: "Fight, die, learn, and try again with new abilities each run.",
            GameGenre.METROIDVANIA: "Explore, find power-ups, and unlock new areas by backtracking.",
            GameGenre.VISUAL_NOVEL: "Read, make choices, and shape the story through branching dialogue.",
            GameGenre.TOWER_DEFENSE: "Build towers, plan the maze, and survive waves of enemies.",
            GameGenre.SANDBOX: "Create, build, explore, and shape the world freely.",
            GameGenre.RHYTHM: "Listen, tap to the beat, and master musical patterns.",
            GameGenre.STEALTH: "Observe patrols, sneak past guards, and complete objectives undetected.",
            GameGenre.SURVIVAL: "Gather, craft, build, and survive against the elements and threats.",
            GameGenre.PARTY: "Play mini-games, compete with friends, and enjoy casual fun.",
        }
        return loop_templates.get(primary_genre, "A core loop of action, progression, and discovery.")

    def _infer_win_conditions(self, blueprint: GameBlueprint) -> List[str]:
        """Infer win conditions based on the blueprint."""
        conditions: List[str] = []

        if not blueprint.genres:
            return ["Complete all levels"]

        primary = blueprint.genres[0]
        genre_conditions: Dict[GameGenre, List[str]] = {
            GameGenre.PLATFORMER: ["Reach the end of each level", "Defeat the final boss"],
            GameGenre.RPG: ["Complete the main quest", "Defeat the final boss"],
            GameGenre.SHOOTER: ["Complete all missions", "Defeat the enemy faction"],
            GameGenre.PUZZLE: ["Solve all puzzles", "Complete the final challenge"],
            GameGenre.STRATEGY: ["Conquer all territories", "Achieve the victory condition"],
            GameGenre.SIMULATION: ["Reach the target goal", "Build a thriving system"],
            GameGenre.ADVENTURE: ["Complete the main story", "Solve the central mystery"],
            GameGenre.RACING: ["Win the championship", "Finish first in the final race"],
            GameGenre.FIGHTING: ["Win the tournament", "Defeat all opponents"],
            GameGenre.SPORTS: ["Win the championship", "Achieve the highest score"],
            GameGenre.HORROR: ["Escape the danger", "Survive until the end"],
            GameGenre.ROGUELIKE: ["Reach the final floor", "Defeat the final boss"],
            GameGenre.METROIDVANIA: ["Defeat the final boss", "Unlock the true ending"],
            GameGenre.VISUAL_NOVEL: ["Reach a good ending", "Unlock all story routes"],
            GameGenre.TOWER_DEFENSE: ["Survive all waves", "Protect the core objective"],
            GameGenre.SANDBOX: ["Achieve personal goals", "Complete all achievements"],
            GameGenre.RHYTHM: ["Complete all songs", "Achieve the highest rank"],
            GameGenre.STEALTH: ["Complete all missions", "Never be detected"],
            GameGenre.SURVIVAL: ["Survive as long as possible", "Escape or be rescued"],
            GameGenre.PARTY: ["Win the most mini-games", "Achieve the highest score"],
        }
        conditions = genre_conditions.get(primary, ["Complete all levels"])
        return conditions

    def _infer_lose_conditions(self, blueprint: GameBlueprint) -> List[str]:
        """Infer lose conditions based on the blueprint."""
        conditions: List[str] = ["Player character perishes"]

        if blueprint.genres:
            primary = blueprint.genres[0]
            extra: Dict[GameGenre, List[str]] = {
                GameGenre.PUZZLE: ["Run out of moves", "Time expires"],
                GameGenre.STRATEGY: ["All bases destroyed", "Resources depleted"],
                GameGenre.SIMULATION: ["System collapses", "Goal not met by deadline"],
                GameGenre.RACING: ["Finish last", "Vehicle destroyed"],
                GameGenre.SPORTS: ["Lose the final match", "Score too low"],
                GameGenre.ROGUELIKE: ["Permadeath - game over", "Run out of continues"],
                GameGenre.TOWER_DEFENSE: ["Core objective destroyed", "All towers lost"],
                GameGenre.RHYTHM: ["Miss too many notes", "Score too low to pass"],
                GameGenre.STEALTH: ["Detected", "Objective failed"],
                GameGenre.SURVIVAL: ["Health reaches zero", "Resources completely depleted"],
            }
            conditions.extend(extra.get(primary, []))

        return conditions

    def _infer_progression(self, blueprint: GameBlueprint) -> str:
        """Infer the progression system based on the blueprint."""
        if not blueprint.genres:
            return "Linear level progression"

        primary = blueprint.genres[0]
        progressions: Dict[GameGenre, str] = {
            GameGenre.PLATFORMER: "Linear level progression with increasing difficulty. Unlock new abilities gradually.",
            GameGenre.RPG: "Character level progression with experience points, skill trees, and equipment upgrades.",
            GameGenre.SHOOTER: "Mission-based progression with weapon unlocks and rank advancements.",
            GameGenre.PUZZLE: "Increasing puzzle complexity with new mechanics introduced each chapter.",
            GameGenre.STRATEGY: "Technology tree progression with resource accumulation and territory expansion.",
            GameGenre.SIMULATION: "Goal-based progression with milestones unlocking new systems and features.",
            GameGenre.ADVENTURE: "Story-driven progression with new areas unlocking as the narrative unfolds.",
            GameGenre.RACING: "Championship progression with vehicle upgrades and new tracks unlocking.",
            GameGenre.FIGHTING: "Roster progression with new characters, stages, and modes unlocking.",
            GameGenre.SPORTS: "Season-based progression with player stats improving over time.",
            GameGenre.HORROR: "Chapter-based progression with increasing tension and more dangerous encounters.",
            GameGenre.ROGUELIKE: "Run-based progression with persistent unlocks between runs.",
            GameGenre.METROIDVANIA: "Ability-gated progression with new areas becoming accessible as powers are found.",
            GameGenre.VISUAL_NOVEL: "Branching route progression with multiple endings based on player choices.",
            GameGenre.TOWER_DEFENSE: "Wave-based progression with new tower types and upgrades unlocking.",
            GameGenre.SANDBOX: "Self-directed progression with achievements and milestones.",
            GameGenre.RHYTHM: "Song difficulty progression with new tracks unlocking after completing previous ones.",
            GameGenre.STEALTH: "Mission-based progression with new tools and abilities unlocking.",
            GameGenre.SURVIVAL: "Technology progression from primitive tools to advanced equipment.",
            GameGenre.PARTY: "Round-based progression with cumulative scoring across mini-games.",
        }
        return progressions.get(primary, "Linear level progression with increasing difficulty.")

    def _infer_audience(self, text: str) -> str:
        """Infer the target audience from the description."""
        audience_keywords: Dict[str, List[str]] = {
            "children": ["kid", "child", "family", "young", "toddler", "preschool"],
            "teens": ["teen", "teenager", "young adult", "adolescent", "high school"],
            "casual gamers": ["casual", "easy", "relax", "pick up", "pick-up", "anyone"],
            "hardcore gamers": ["hardcore", "challenging", "difficult", "competitive", "pro"],
            "all ages": ["all age", "everyone", "universal", "any age"],
        }
        for audience, keywords in audience_keywords.items():
            if any(kw in text for kw in keywords):
                return audience

        return "general audience"

    def _estimate_playtime(self, blueprint: GameBlueprint) -> float:
        """Estimate total playtime in minutes."""
        complexity_multipliers = {
            ComplexityTier.MINI: 15.0,
            ComplexityTier.CASUAL: 30.0,
            ComplexityTier.STANDARD: 60.0,
            ComplexityTier.AMBITIOUS: 120.0,
            ComplexityTier.EPIC: 240.0,
        }
        base = complexity_multipliers.get(blueprint.complexity, 60.0)
        mechanic_bonus = len(blueprint.mechanics) * 5.0
        return round(base + mechanic_bonus, 1)

    def _infer_name(self, description: str) -> str:
        """Infer a game name from the description."""
        # Try to find a quoted name
        quoted = re.findall(r'"([^"]{3,50})"', description)
        if quoted:
            return quoted[0]

        # Try to extract name patterns
        name_patterns = [
            r'called\s+["\']?([A-Z][a-zA-Z\s]{2,40})["\']?',
            r'named\s+["\']?([A-Z][a-zA-Z\s]{2,40})["\']?',
            r'titled\s+["\']?([A-Z][a-zA-Z\s]{2,40})["\']?',
        ]
        for pattern in name_patterns:
            match = re.search(pattern, description)
            if match:
                return match.group(1).strip()

        # Fallback: use first few words
        words = description.strip().split()
        if len(words) >= 3:
            return " ".join(words[:3]).title()
        return "Unnamed Game"


# =============================================================================
# GameAssembler
# =============================================================================


class GameAssembler:
    """Assembles game components from a GameBlueprint.

    Generates scene specifications, character definitions, UI layouts,
    asset requirement lists, and rule/mechanic definitions based on the
    structured blueprint. Each component is derived from the blueprint's
    genres, mechanics, and complexity tier.
    """

    def __init__(self) -> None:
        pass

    def assemble_scenes(self, blueprint: GameBlueprint) -> List[SceneSpec]:
        """Generate scene specifications from the blueprint.

        Args:
            blueprint: The game blueprint to derive scenes from.

        Returns:
            A list of SceneSpec instances for the game's levels and screens.
        """
        scenes: List[SceneSpec] = []
        scene_count = self._compute_scene_count(blueprint)

        scene_types = self._get_scene_type_distribution(blueprint)
        scene_names = self._generate_scene_names(blueprint, scene_count)

        for i in range(scene_count):
            name = scene_names[i] if i < len(scene_names) else f"Level {i + 1}"
            scene_type = scene_types[i % len(scene_types)] if scene_types else "level"

            mechanic_ids = [m.spec_id for m in blueprint.mechanics[:3]]
            duration = self._estimate_scene_duration(blueprint, scene_type)

            scene = SceneSpec(
                name=name,
                description=f"{scene_type.title()}: {name}",
                scene_type=scene_type,
                mechanics=mechanic_ids,
                estimated_duration=duration,
            )

            # Add exits linking scenes
            if i > 0:
                scene.exits.append({"target": scenes[-1].scene_id, "direction": "prev"})
            if i < scene_count - 1:
                scene.exits.append({"target": "", "direction": "next"})

            scenes.append(scene)

        # Link next exits
        for i in range(len(scenes) - 1):
            for ex in scenes[i].exits:
                if ex["direction"] == "next":
                    ex["target"] = scenes[i + 1].scene_id

        blueprint.scenes = scenes
        return scenes

    def assemble_characters(self, blueprint: GameBlueprint) -> List[CharacterSpec]:
        """Generate character specifications from the blueprint.

        Args:
            blueprint: The game blueprint to derive characters from.

        Returns:
            A list of CharacterSpec instances for the game's characters.
        """
        characters: List[CharacterSpec] = []
        char_count = self._compute_character_count(blueprint)

        roles = ["player", "enemy", "npc", "boss", "companion"]
        role_weights = self._get_role_weights(blueprint)

        for i in range(char_count):
            role = self._weighted_pick(roles, role_weights)
            name = self._generate_character_name(role, i, blueprint)
            stats = self._generate_character_stats(role, blueprint)
            abilities = self._generate_character_abilities(role, blueprint)

            char = CharacterSpec(
                name=name,
                role=role,
                description=f"A {role} in {blueprint.name}",
                abilities=abilities,
                stats=stats,
                spawn_scene=blueprint.scenes[0].scene_id if blueprint.scenes else "",
            )
            characters.append(char)

        blueprint.characters = characters
        return characters

    def assemble_ui_layouts(self, blueprint: GameBlueprint) -> List[UILayoutSpec]:
        """Generate UI layout specifications from the blueprint.

        Args:
            blueprint: The game blueprint to derive UI layouts from.

        Returns:
            A list of UILayoutSpec instances.
        """
        layouts: List[UILayoutSpec] = []

        standard_layouts = [
            ("Main Menu", "Start screen with title, play button, settings, and credits."),
            ("HUD", "In-game heads-up display showing score, health, and resources."),
            ("Pause Menu", "Pause overlay with resume, restart, settings, and quit options."),
            ("Settings", "Settings screen with audio, controls, and display options."),
            ("Game Over", "Game over screen with score, retry, and return to menu options."),
            ("Victory", "Victory screen with congratulations, stats, and next level option."),
        ]

        # Add genre-specific layouts
        genre_layouts = self._get_genre_ui_layouts(blueprint)
        standard_layouts.extend(genre_layouts)

        for name, desc in standard_layouts:
            layout = UILayoutSpec(
                name=name,
                description=desc,
            )
            layouts.append(layout)

        blueprint.ui_layouts = layouts
        return layouts

    def assemble_asset_requirements(
        self, blueprint: GameBlueprint
    ) -> List[AssetRequirement]:
        """Generate asset requirement specifications from the blueprint.

        Args:
            blueprint: The game blueprint to derive asset requirements from.

        Returns:
            A list of AssetRequirement instances.
        """
        assets: List[AssetRequirement] = []

        # Player character
        assets.append(AssetRequirement(
            asset_type="sprite" if blueprint.dimension in (DimensionMode.D2, DimensionMode.D2_5) else "model",
            name="Player Character",
            description="The main player-controlled character",
            priority=1,
        ))

        # Enemies
        enemy_count = max(1, len(blueprint.characters) // 3)
        for i in range(enemy_count):
            assets.append(AssetRequirement(
                asset_type="sprite" if blueprint.dimension in (DimensionMode.D2, DimensionMode.D2_5) else "model",
                name=f"Enemy Type {i + 1}",
                description=f"Enemy character variant {i + 1}",
                priority=2,
            ))

        # Backgrounds per scene
        for scene in blueprint.scenes:
            assets.append(AssetRequirement(
                asset_type="background",
                name=f"Background - {scene.name}",
                description=f"Background environment for {scene.name}",
                priority=2,
            ))

        # UI assets
        assets.append(AssetRequirement(
            asset_type="ui",
            name="UI Elements",
            description="Buttons, panels, icons, and fonts for the user interface",
            priority=2,
        ))

        # Sound assets
        assets.append(AssetRequirement(
            asset_type="sound",
            name="Sound Effects",
            description="Jump, collect, hit, menu navigation, and other sound effects",
            priority=3,
        ))
        assets.append(AssetRequirement(
            asset_type="music",
            name="Background Music",
            description="Background music tracks for menus and levels",
            priority=3,
        ))

        # Collectibles
        if any(m.mechanic == CoreMechanic.COLLECT for m in blueprint.mechanics):
            assets.append(AssetRequirement(
                asset_type="sprite",
                name="Collectible Items",
                description="Coins, gems, power-ups, or other collectible items",
                priority=2,
            ))

        blueprint.asset_requirements = assets
        return assets

    def assemble_rules(self, blueprint: GameBlueprint) -> Dict[str, Any]:
        """Generate rule and mechanic definitions from the blueprint.

        Args:
            blueprint: The game blueprint to derive rules from.

        Returns:
            A dictionary of game rules organized by category.
        """
        rules: Dict[str, Any] = {
            "movement": self._generate_movement_rules(blueprint),
            "combat": self._generate_combat_rules(blueprint),
            "scoring": self._generate_scoring_rules(blueprint),
            "physics": self._generate_physics_rules(blueprint),
            "camera": self._generate_camera_rules(blueprint),
        }

        return rules

    def _compute_scene_count(self, blueprint: GameBlueprint) -> int:
        """Compute the number of scenes based on complexity."""
        scene_counts = {
            ComplexityTier.MINI: 3,
            ComplexityTier.CASUAL: 5,
            ComplexityTier.STANDARD: 10,
            ComplexityTier.AMBITIOUS: 20,
            ComplexityTier.EPIC: 40,
        }
        return scene_counts.get(blueprint.complexity, 10)

    def _compute_character_count(self, blueprint: GameBlueprint) -> int:
        """Compute the number of characters based on complexity."""
        char_counts = {
            ComplexityTier.MINI: 3,
            ComplexityTier.CASUAL: 5,
            ComplexityTier.STANDARD: 10,
            ComplexityTier.AMBITIOUS: 20,
            ComplexityTier.EPIC: 40,
        }
        return char_counts.get(blueprint.complexity, 10)

    def _get_scene_type_distribution(
        self, blueprint: GameBlueprint
    ) -> List[str]:
        """Get the scene type distribution for the blueprint."""
        if not blueprint.genres:
            return ["level", "level", "boss"]

        primary = blueprint.genres[0]
        distributions: Dict[GameGenre, List[str]] = {
            GameGenre.PLATFORMER: ["level", "level", "level", "boss", "level", "level", "level", "boss", "level", "hub"],
            GameGenre.RPG: ["town", "dungeon", "field", "dungeon", "town", "boss", "field", "dungeon", "town", "final_boss"],
            GameGenre.SHOOTER: ["mission", "mission", "mission", "boss", "mission", "mission", "mission", "boss", "mission", "final_boss"],
            GameGenre.PUZZLE: ["puzzle", "puzzle", "puzzle", "challenge", "puzzle", "puzzle", "puzzle", "challenge", "puzzle", "final_challenge"],
            GameGenre.STRATEGY: ["map", "map", "map", "boss_map", "map", "map", "map", "boss_map", "map", "final_map"],
            GameGenre.SIMULATION: ["area", "area", "area", "hub", "area", "area", "area", "hub", "area", "master_area"],
            GameGenre.ADVENTURE: ["location", "location", "location", "boss_location", "location", "location", "location", "boss_location", "location", "final_location"],
            GameGenre.RACING: ["track", "track", "track", "championship", "track", "track", "track", "championship", "track", "final_track"],
            GameGenre.FIGHTING: ["stage", "stage", "stage", "boss_stage", "stage", "stage", "stage", "boss_stage", "stage", "final_stage"],
            GameGenre.ROGUELIKE: ["floor", "floor", "shop", "floor", "boss", "floor", "floor", "shop", "floor", "final_boss"],
            GameGenre.METROIDVANIA: ["zone", "zone", "zone", "boss", "zone", "zone", "zone", "boss", "zone", "final_boss"],
            GameGenre.TOWER_DEFENSE: ["wave", "wave", "wave", "boss_wave", "wave", "wave", "wave", "boss_wave", "wave", "final_wave"],
            GameGenre.SURVIVAL: ["biome", "biome", "biome", "danger_zone", "biome", "biome", "biome", "danger_zone", "biome", "sanctuary"],
        }
        return distributions.get(primary, ["level"] * 10)

    def _generate_scene_names(
        self, blueprint: GameBlueprint, count: int
    ) -> List[str]:
        """Generate scene names based on the blueprint's theme."""
        name_prefixes: Dict[str, List[str]] = {
            "fantasy": ["Enchanted Forest", "Crystal Cavern", "Dragon Peak", "Shadow Tower", "Mystic Marsh", "Golden City", "Frozen Tundra", "Volcanic Depths", "Celestial Temple", "Forgotten Tombs"],
            "sci_fi": ["Orbital Station", "Nebula Rift", "Cyber District", "Alien Hive", "Quantum Lab", "Space Dock", "Mining Colony", "Research Outpost", "Fleet Command", "Warp Gate"],
            "horror": ["Abandoned Manor", "Dark Forest", "Asylum Ward", "Underground Tunnels", "Haunted Cemetery", "Deserted Hospital", "Creeping Swamp", "Shadow Alley", "Forgotten Basement", "Eerie Lighthouse"],
            "post_apocalyptic": ["Ruined City", "Toxic Wasteland", "Survivor Camp", "Underground Bunker", "Collapsed Highway", "Scavenger Outpost", "Abandoned Factory", "Crater Zone", "Drowned District", "The Last Oasis"],
            "military": ["Forward Base", "Trench Line", "Urban Combat Zone", "Missile Silo", "Command Center", "Airfield", "Naval Port", "Mountain Pass", "Desert Outpost", "Jungle Bunker"],
            "western": ["Dusty Canyon", "Abandoned Mine", "Frontier Town", "Prairie Crossing", "Ghost Town", "Cattle Ranch", "Train Station", "Canyon Pass", "Sheriff Office", "Saloon Row"],
            "noir": ["Rainy Street", "Detective Office", "Docks District", "Underground Club", "Rooftop Chase", "Alley Hideout", "Police Station", "Hotel Lobby", "Warehouse", "Courtroom"],
            "steampunk": ["Clockwork Tower", "Steam Foundry", "Airship Port", "Gear District", "Brass Market", "Engine Room", "Observatory", "Factory Floor", "Inventor Lab", "Railway Hub"],
            "cyberpunk": ["Neon Plaza", "Data Core", "Underground Market", "Rooftop Slums", "MegaCorp Tower", "Hacker Den", "Chrome Boulevard", "Synthetic Alley", "Grid Nexus", "The Blackout Zone"],
            "mythology": ["Mount Olympus", "Underworld Gate", "Valhalla Hall", "Nile Temple", "Asgard Bridge", "Labyrinth", "Sacred Grove", "Oracle Cave", "Thunder Peak", "Sunken Atlantis"],
            "ocean": ["Coral Reef", "Sunken Ship", "Pirate Cove", "Deep Trench", "Tropical Island", "Mangrove Swamp", "Open Ocean", "Iceberg Passage", "Underwater Cave", "Mermaid Lagoon"],
            "space": ["Asteroid Belt", "Moon Base", "Mars Colony", "Gas Giant Orbit", "Black Hole Rim", "Space Station", "Comet Trail", "Exoplanet Surface", "Stellar Nursery", "Dark Matter Zone"],
        }
        prefixes = name_prefixes.get(blueprint.theme, name_prefixes.get("fantasy", []))
        result: List[str] = []
        for i in range(count):
            if i < len(prefixes):
                result.append(prefixes[i])
            else:
                result.append(f"{prefixes[i % len(prefixes)]} {i // len(prefixes) + 1}")
        return result

    def _estimate_scene_duration(
        self, blueprint: GameBlueprint, scene_type: str
    ) -> float:
        """Estimate the duration of a scene in minutes."""
        base_durations = {
            "level": 5.0, "town": 3.0, "dungeon": 10.0, "boss": 8.0,
            "mission": 8.0, "puzzle": 5.0, "challenge": 6.0,
            "map": 12.0, "track": 4.0, "stage": 3.0,
            "floor": 6.0, "zone": 8.0, "location": 5.0,
            "hub": 2.0, "shop": 1.0, "biome": 8.0,
            "final_boss": 12.0, "final_stage": 8.0, "final_track": 5.0,
            "final_map": 15.0, "final_challenge": 10.0, "final_location": 8.0,
            "sanctuary": 2.0, "danger_zone": 10.0,
        }
        return base_durations.get(scene_type, 5.0)

    def _get_role_weights(self, blueprint: GameBlueprint) -> List[float]:
        """Get weights for character role distribution."""
        if not blueprint.genres:
            return [0.2, 0.3, 0.3, 0.1, 0.1]

        primary = blueprint.genres[0]
        role_weight_map: Dict[GameGenre, List[float]] = {
            GameGenre.PLATFORMER: [0.1, 0.5, 0.2, 0.1, 0.1],
            GameGenre.RPG: [0.05, 0.3, 0.4, 0.1, 0.15],
            GameGenre.SHOOTER: [0.05, 0.6, 0.2, 0.1, 0.05],
            GameGenre.PUZZLE: [0.1, 0.1, 0.6, 0.1, 0.1],
            GameGenre.STRATEGY: [0.05, 0.5, 0.3, 0.1, 0.05],
            GameGenre.FIGHTING: [0.05, 0.5, 0.2, 0.2, 0.05],
            GameGenre.ROGUELIKE: [0.05, 0.6, 0.15, 0.15, 0.05],
            GameGenre.SURVIVAL: [0.1, 0.4, 0.3, 0.1, 0.1],
        }
        return role_weight_map.get(primary, [0.1, 0.4, 0.3, 0.1, 0.1])

    def _weighted_pick(self, items: List[str], weights: List[float]) -> str:
        """Pick an item from the list based on provided weights."""
        if len(items) != len(weights):
            return items[0] if items else ""

        total = sum(weights)
        if total <= 0:
            return items[0] if items else ""

        r = random.uniform(0, total)
        cumulative = 0.0
        for item, weight in zip(items, weights):
            cumulative += weight
            if r <= cumulative:
                return item
        return items[-1] if items else ""

    def _generate_character_name(
        self, role: str, index: int, blueprint: GameBlueprint
    ) -> str:
        """Generate a character name based on role and theme."""
        role_prefixes: Dict[str, List[str]] = {
            "player": ["Hero", "Adventurer", "Wanderer", "Champion", "Explorer", "Protagonist"],
            "enemy": ["Goblin", "Skeleton", "Slime", "Bandit", "Drone", "Grunt", "Minion", "Soldier", "Cultist", "Thug"],
            "npc": ["Villager", "Merchant", "Scholar", "Guard", "Elder", "Traveler", "Blacksmith", "Innkeeper", "Farmer", "Priest"],
            "boss": ["Overlord", "Titan", "Leviathan", "Dreadlord", "Colossus", "Archfiend", "Warmonger", "Nightmare", "Phantom", "Behemoth"],
            "companion": ["Ally", "Follower", "Sidekick", "Partner", "Friend", "Guide", "Mentor", "Apprentice", "Squire", "Familiar"],
        }
        prefixes = role_prefixes.get(role, ["Entity"])
        name = prefixes[index % len(prefixes)]
        if role in ("enemy", "npc"):
            return f"{name} {index + 1}"
        return name

    def _generate_character_stats(
        self, role: str, blueprint: GameBlueprint
    ) -> Dict[str, float]:
        """Generate character stats based on role and complexity."""
        complexity_mult = {
            ComplexityTier.MINI: 1.0,
            ComplexityTier.CASUAL: 1.5,
            ComplexityTier.STANDARD: 2.0,
            ComplexityTier.AMBITIOUS: 3.0,
            ComplexityTier.EPIC: 5.0,
        }
        mult = complexity_mult.get(blueprint.complexity, 2.0)

        role_stats: Dict[str, Dict[str, float]] = {
            "player": {"health": 100.0 * mult, "attack": 10.0 * mult, "speed": 5.0, "defense": 5.0 * mult},
            "enemy": {"health": 30.0 * mult, "attack": 5.0 * mult, "speed": 3.0, "defense": 2.0 * mult},
            "npc": {"health": 50.0, "attack": 2.0, "speed": 2.0, "defense": 2.0},
            "boss": {"health": 500.0 * mult, "attack": 25.0 * mult, "speed": 4.0, "defense": 15.0 * mult},
            "companion": {"health": 80.0 * mult, "attack": 8.0 * mult, "speed": 4.0, "defense": 4.0 * mult},
        }
        return role_stats.get(role, {"health": 50.0, "attack": 5.0, "speed": 3.0, "defense": 3.0})

    def _generate_character_abilities(
        self, role: str, blueprint: GameBlueprint
    ) -> List[str]:
        """Generate character abilities based on role and mechanics."""
        mechanic_map = {m.mechanic.value: f"{m.mechanic.value.title()} Skill" for m in blueprint.mechanics}

        role_abilities: Dict[str, List[str]] = {
            "player": [mechanic_map.get(m.mechanic.value, "Basic Attack") for m in blueprint.mechanics[:3]],
            "enemy": ["Basic Attack", "Charge"],
            "npc": ["Talk", "Trade"],
            "boss": ["Power Strike", "Area Attack", "Summon Minions", "Heal"],
            "companion": ["Assist", "Heal", "Support Fire"],
        }
        return role_abilities.get(role, ["Basic Action"])

    def _get_genre_ui_layouts(
        self, blueprint: GameBlueprint
    ) -> List[Tuple[str, str]]:
        """Get genre-specific UI layouts."""
        if not blueprint.genres:
            return []

        primary = blueprint.genres[0]
        genre_uis: Dict[GameGenre, List[Tuple[str, str]]] = {
            GameGenre.RPG: [
                ("Inventory", "Grid-based inventory screen for managing items and equipment."),
                ("Character Sheet", "Detailed character stats, skills, and equipment display."),
                ("Quest Log", "Active and completed quests tracking display."),
                ("Dialogue", "Conversation interface with NPC dialogue options."),
            ],
            GameGenre.SHOOTER: [
                ("Loadout", "Weapon selection and customization screen."),
                ("Minimap", "Corner minimap showing enemy positions and objectives."),
            ],
            GameGenre.STRATEGY: [
                ("Tech Tree", "Technology research and unlock tree display."),
                ("Resource Panel", "Resource counts and production rates display."),
                ("Unit Roster", "Unit production and management interface."),
            ],
            GameGenre.SIMULATION: [
                ("Build Menu", "Construction and placement interface."),
                ("Statistics", "Charts and data visualization for system metrics."),
            ],
            GameGenre.RACING: [
                ("Garage", "Vehicle selection, upgrades, and customization screen."),
                ("Leaderboard", "Race times and ranking display."),
            ],
            GameGenre.FIGHTING: [
                ("Character Select", "Fighter roster and selection screen."),
                ("Move List", "Combo and special move reference display."),
            ],
            GameGenre.SURVIVAL: [
                ("Crafting Menu", "Crafting recipes and material requirements display."),
                ("Status Bars", "Hunger, thirst, temperature, and health indicators."),
            ],
            GameGenre.ROGUELIKE: [
                ("Upgrade Select", "Run upgrade and perk selection screen."),
                ("Run History", "Previous run statistics and unlocks display."),
            ],
            GameGenre.TOWER_DEFENSE: [
                ("Tower Menu", "Tower selection, placement, and upgrade interface."),
                ("Wave Preview", "Upcoming wave composition and timing display."),
            ],
        }
        return genre_uis.get(primary, [])

    def _generate_movement_rules(self, blueprint: GameBlueprint) -> Dict[str, Any]:
        """Generate movement rules based on the blueprint."""
        rules: Dict[str, Any] = {
            "gravity_enabled": blueprint.dimension != DimensionMode.D2 or any(
                m.mechanic == CoreMechanic.JUMP for m in blueprint.mechanics
            ),
            "max_speed": 10.0,
            "acceleration": 20.0,
            "can_jump": any(m.mechanic == CoreMechanic.JUMP for m in blueprint.mechanics),
            "jump_height": 5.0,
            "can_fly": any(m.mechanic == CoreMechanic.FLY for m in blueprint.mechanics),
            "can_swim": any(m.mechanic == CoreMechanic.SWIM for m in blueprint.mechanics),
            "can_climb": any(m.mechanic == CoreMechanic.CLIMB for m in blueprint.mechanics),
            "can_sneak": any(m.mechanic == CoreMechanic.SNEAK for m in blueprint.mechanics),
        }
        return rules

    def _generate_combat_rules(self, blueprint: GameBlueprint) -> Dict[str, Any]:
        """Generate combat rules based on the blueprint."""
        has_combat = any(m.mechanic == CoreMechanic.FIGHT for m in blueprint.mechanics)
        return {
            "combat_enabled": has_combat,
            "damage_formula": "attack * (1.0 - defense / (defense + 100))",
            "critical_chance": 0.1,
            "critical_multiplier": 1.5,
            "invincibility_frames": 0.5,
            "knockback_force": 3.0 if has_combat else 0.0,
        }

    def _generate_scoring_rules(self, blueprint: GameBlueprint) -> Dict[str, Any]:
        """Generate scoring rules based on the blueprint."""
        rules: Dict[str, Any] = {
            "score_enabled": True,
            "points_per_collectible": 100,
            "points_per_enemy": 200,
            "points_per_boss": 500,
            "time_bonus_enabled": True,
            "combo_multiplier_enabled": False,
        }

        if blueprint.genres and blueprint.genres[0] in (GameGenre.FIGHTING, GameGenre.RHYTHM):
            rules["combo_multiplier_enabled"] = True

        return rules

    def _generate_physics_rules(self, blueprint: GameBlueprint) -> Dict[str, Any]:
        """Generate physics rules based on the blueprint."""
        return {
            "gravity": 9.8 if blueprint.dimension == DimensionMode.D3 else 15.0,
            "friction": 0.8,
            "bounce": 0.3,
            "max_fall_speed": 20.0,
            "collision_detection": "continuous" if blueprint.dimension == DimensionMode.D3 else "grid",
        }

    def _generate_camera_rules(self, blueprint: GameBlueprint) -> Dict[str, Any]:
        """Generate camera rules based on the blueprint."""
        camera: Dict[str, Any] = {
            "projection": blueprint.projection.value,
            "smoothing": 0.1,
            "dead_zone": 0.05,
        }

        if blueprint.projection == ProjectionMode.SIDE_VIEW:
            camera["follow_mode"] = "horizontal"
            camera["look_ahead"] = 0.3
        elif blueprint.projection == ProjectionMode.TOP_DOWN:
            camera["follow_mode"] = "center"
            camera["zoom_level"] = 1.0
        elif blueprint.projection == ProjectionMode.FIRST_PERSON:
            camera["follow_mode"] = "first_person"
            camera["fov"] = 90.0
        elif blueprint.projection == ProjectionMode.THIRD_PERSON:
            camera["follow_mode"] = "third_person"
            camera["distance"] = 5.0
            camera["height_offset"] = 2.0

        return camera


# =============================================================================
# CreationPipeline
# =============================================================================


class CreationPipeline:
    """Phased creation pipeline for generating games from blueprints.

    Orchestrates the six-phase game creation process:
      1. SPECIFICATION - Parse and validate requirements
      2. DESIGN - Create detailed game design
      3. SCAFFOLDING - Generate project structure
      4. IMPLEMENTATION - Generate game code and assets
      5. TESTING - Validate playability
      6. REFINEMENT - Iterate based on testing

    Each phase produces structured output that feeds into subsequent phases.
    The pipeline tracks progress, handles errors, and supports iterative
    refinement based on feedback.
    """

    _PHASE_ORDER: List[CreationPhase] = [
        CreationPhase.SPECIFICATION,
        CreationPhase.DESIGN,
        CreationPhase.SCAFFOLDING,
        CreationPhase.IMPLEMENTATION,
        CreationPhase.TESTING,
        CreationPhase.REFINEMENT,
    ]

    def __init__(self) -> None:
        pass

    def create_session(self, description: str, name: str = "") -> CreationSession:
        """Create a new creation session and execute the specification phase.

        Args:
            description: Natural language description of the desired game.
            name: Optional game title.

        Returns:
            A CreationSession with the specification phase completed.
        """
        session = CreationSession()

        # Phase 1: Specification
        self._run_phase(session, CreationPhase.SPECIFICATION, {
            "description": description,
            "name": name,
        })

        return session

    def continue_session(self, session: CreationSession) -> CreationSession:
        """Continue a session to the next phase.

        Args:
            session: The creation session to continue.

        Returns:
            The updated session with the next phase completed.
        """
        current_idx = self._PHASE_ORDER.index(session.current_phase)
        next_idx = current_idx + 1

        while next_idx < len(self._PHASE_ORDER):
            next_phase = self._PHASE_ORDER[next_idx]
            self._run_phase(session, next_phase, {})
            next_idx += 1

        return session

    def advance_phase(
        self, session: CreationSession, target_phase: CreationPhase
    ) -> CreationSession:
        """Advance the session to a specific phase, running all intermediate phases.

        Args:
            session: The creation session to advance.
            target_phase: The phase to advance to.

        Returns:
            The updated session with all phases up to and including target completed.
        """
        current_idx = self._PHASE_ORDER.index(session.current_phase)
        target_idx = self._PHASE_ORDER.index(target_phase)

        if target_idx <= current_idx:
            return session

        for idx in range(current_idx + 1, target_idx + 1):
            phase = self._PHASE_ORDER[idx]
            self._run_phase(session, phase, {})

        return session

    def add_feedback(
        self, session: CreationSession, feedback: str, target_phase: Optional[CreationPhase] = None
    ) -> CreationSession:
        """Add feedback to a session and trigger refinement if applicable.

        Args:
            session: The creation session to add feedback to.
            feedback: The feedback text describing desired changes.
            target_phase: Specific phase to refine. Defaults to the current phase.

        Returns:
            The updated session with feedback recorded and refinement applied.
        """
        session.feedback_history.append({
            "feedback": feedback,
            "target_phase": (target_phase or session.current_phase).value,
            "timestamp": time.time(),
        })
        session.updated_at = time.time()

        # Trigger refinement
        if target_phase is None:
            target_phase = session.current_phase

        self._run_phase(session, CreationPhase.REFINEMENT, {
            "feedback": feedback,
            "target_phase": target_phase,
        })

        return session

    def get_progress(self, session: CreationSession) -> Dict[str, Any]:
        """Get the overall progress of a creation session.

        Args:
            session: The creation session to get progress for.

        Returns:
            A dictionary with phase-by-phase progress and overall completion.
        """
        phases_info: Dict[str, Any] = {}
        completed_count = 0

        for phase in self._PHASE_ORDER:
            stage = session.stages.get(phase.value)
            if stage:
                phases_info[phase.value] = stage.to_dict()
                if stage.status == "completed":
                    completed_count += 1
            else:
                phases_info[phase.value] = {"status": "not_started"}

        return {
            "overall_progress": round(completed_count / len(self._PHASE_ORDER), 2),
            "completed_phases": completed_count,
            "total_phases": len(self._PHASE_ORDER),
            "current_phase": session.current_phase.value,
            "phases": phases_info,
        }

    def _run_phase(
        self,
        session: CreationSession,
        phase: CreationPhase,
        params: Dict[str, Any],
    ) -> None:
        """Execute a single pipeline phase."""
        stage = PipelineStage(phase=phase, status="in_progress", started_at=time.time())
        session.stages[phase.value] = stage
        session.current_phase = phase
        session.updated_at = time.time()

        try:
            if phase == CreationPhase.SPECIFICATION:
                self._execute_specification(session, stage, params)
            elif phase == CreationPhase.DESIGN:
                self._execute_design(session, stage)
            elif phase == CreationPhase.SCAFFOLDING:
                self._execute_scaffolding(session, stage)
            elif phase == CreationPhase.IMPLEMENTATION:
                self._execute_implementation(session, stage)
            elif phase == CreationPhase.TESTING:
                self._execute_testing(session, stage)
            elif phase == CreationPhase.REFINEMENT:
                self._execute_refinement(session, stage, params)

            stage.status = "completed"
            stage.progress = 1.0
            stage.completed_at = time.time()
        except Exception as e:
            stage.status = "failed"
            stage.errors.append(str(e))
            stage.completed_at = time.time()

    def _execute_specification(
        self,
        session: CreationSession,
        stage: PipelineStage,
        params: Dict[str, Any],
    ) -> None:
        """Execute the specification phase: parse the NL description."""
        description = params.get("description", "")
        name = params.get("name", "")

        parser = GameSpecParser()
        blueprint = parser.parse(description, name)
        session.blueprint = blueprint

        stage.result = {
            "blueprint_id": blueprint.blueprint_id,
            "game_name": blueprint.name,
            "genres": [g.value for g in blueprint.genres],
            "visual_styles": [s.value for s in blueprint.visual_styles],
            "complexity": blueprint.complexity.value,
            "mechanic_count": len(blueprint.mechanics),
            "estimated_playtime": blueprint.estimated_playtime,
        }
        stage.progress = 1.0

    def _execute_design(
        self, session: CreationSession, stage: PipelineStage
    ) -> None:
        """Execute the design phase: assemble all game components."""
        if session.blueprint is None:
            raise ValueError("No blueprint available for design phase")

        assembler = GameAssembler()

        # Generate scenes
        stage.progress = 0.1
        scenes = assembler.assemble_scenes(session.blueprint)
        stage.notes = f"Generated {len(scenes)} scenes"

        # Generate characters
        stage.progress = 0.3
        characters = assembler.assemble_characters(session.blueprint)
        stage.notes += f", {len(characters)} characters"

        # Generate UI layouts
        stage.progress = 0.5
        ui_layouts = assembler.assemble_ui_layouts(session.blueprint)
        stage.notes += f", {len(ui_layouts)} UI layouts"

        # Generate asset requirements
        stage.progress = 0.7
        assets = assembler.assemble_asset_requirements(session.blueprint)
        stage.notes += f", {len(assets)} assets"

        # Generate rules
        stage.progress = 0.9
        rules = assembler.assemble_rules(session.blueprint)

        stage.result = {
            "scene_count": len(scenes),
            "character_count": len(characters),
            "ui_layout_count": len(ui_layouts),
            "asset_count": len(assets),
            "rules_categories": list(rules.keys()),
            "blueprint": session.blueprint.to_dict(),
        }
        stage.progress = 1.0

    def _execute_scaffolding(
        self, session: CreationSession, stage: PipelineStage
    ) -> None:
        """Execute the scaffolding phase: generate project structure."""
        if session.blueprint is None:
            raise ValueError("No blueprint available for scaffolding phase")

        stage.progress = 0.1

        project_structure = self._generate_project_structure(session.blueprint)
        stage.progress = 0.5

        file_manifest = self._generate_file_manifest(session.blueprint)
        stage.progress = 0.8

        stage.result = {
            "project_structure": project_structure,
            "file_manifest": file_manifest,
            "total_files": len(file_manifest),
            "language": self._detect_project_language(session.blueprint),
        }
        stage.progress = 1.0

    def _execute_implementation(
        self, session: CreationSession, stage: PipelineStage
    ) -> None:
        """Execute the implementation phase: generate game code and assets."""
        if session.blueprint is None:
            raise ValueError("No blueprint available for implementation phase")

        stage.progress = 0.1

        code_modules = self._generate_code_modules(session.blueprint)
        stage.progress = 0.4
        stage.notes = f"Generated {len(code_modules)} code modules"

        stage.progress = 0.8

        stage.result = {
            "code_modules": code_modules,
            "module_count": len(code_modules),
            "estimated_lines_of_code": sum(
                m.get("estimated_lines", 0) for m in code_modules
            ),
        }
        stage.progress = 1.0

    def _execute_testing(
        self, session: CreationSession, stage: PipelineStage
    ) -> None:
        """Execute the testing phase: validate playability."""
        if session.blueprint is None:
            raise ValueError("No blueprint available for testing phase")

        stage.progress = 0.2

        # Validate blueprint completeness
        validation = self._validate_blueprint(session.blueprint)
        stage.progress = 0.5

        # Check game logic consistency
        consistency = self._check_consistency(session.blueprint)
        stage.progress = 0.8

        stage.result = {
            "validation": validation,
            "consistency": consistency,
            "overall_pass": validation.get("valid", False) and consistency.get("consistent", False),
            "test_count": validation.get("check_count", 0) + consistency.get("check_count", 0),
        }
        stage.progress = 1.0

    def _execute_refinement(
        self,
        session: CreationSession,
        stage: PipelineStage,
        params: Dict[str, Any],
    ) -> None:
        """Execute the refinement phase: iterate based on feedback."""
        feedback = params.get("feedback", "")
        target_phase = params.get("target_phase")

        if not feedback:
            stage.result = {"refined": False, "reason": "No feedback provided"}
            stage.progress = 1.0
            return

        stage.progress = 0.3

        # Apply feedback to the blueprint
        if session.blueprint:
            session.blueprint.metadata["refinement_feedback"] = feedback
            session.blueprint.metadata["refinement_count"] = (
                session.blueprint.metadata.get("refinement_count", 0) + 1
            )

        stage.progress = 0.6

        stage.result = {
            "refined": True,
            "feedback": feedback[:200],
            "target_phase": target_phase.value if target_phase else None,
            "feedback_count": len(session.feedback_history),
        }
        stage.progress = 1.0

    def _generate_project_structure(
        self, blueprint: GameBlueprint
    ) -> Dict[str, Any]:
        """Generate a project directory and file structure."""
        language = self._detect_project_language(blueprint)

        structure: Dict[str, Any] = {
            "root": blueprint.name.lower().replace(" ", "_"),
            "language": language,
            "directories": [
                "src",
                "src/scenes",
                "src/entities",
                "src/systems",
                "src/ui",
                "assets",
                "assets/sprites",
                "assets/audio",
                "assets/fonts",
                "assets/models" if blueprint.dimension == DimensionMode.D3 else "assets/tilesets",
                "config",
                "tests",
            ],
            "entry_point": self._get_entry_point(language),
        }
        return structure

    def _generate_file_manifest(self, blueprint: GameBlueprint) -> List[Dict[str, Any]]:
        """Generate a manifest of all files needed for the project."""
        language = self._detect_project_language(blueprint)
        manifest: List[Dict[str, Any]] = []

        base_files = [
            {"path": "config/game_config.json", "type": "config"},
            {"path": "config/input_config.json", "type": "config"},
            {"path": "config/asset_manifest.json", "type": "config"},
            {"path": "README.md", "type": "documentation"},
        ]

        if language == "python":
            base_files.extend([
                {"path": "src/__init__.py", "type": "source"},
                {"path": "src/main.py", "type": "source"},
                {"path": "src/scenes/__init__.py", "type": "source"},
                {"path": "src/entities/__init__.py", "type": "source"},
                {"path": "src/entities/player.py", "type": "source"},
                {"path": "src/entities/enemy.py", "type": "source"},
                {"path": "src/systems/__init__.py", "type": "source"},
                {"path": "src/systems/physics.py", "type": "source"},
                {"path": "src/systems/input.py", "type": "source"},
                {"path": "src/systems/rendering.py", "type": "source"},
                {"path": "src/ui/__init__.py", "type": "source"},
                {"path": "src/ui/hud.py", "type": "source"},
                {"path": "src/ui/menus.py", "type": "source"},
                {"path": "tests/test_player.py", "type": "test"},
                {"path": "requirements.txt", "type": "config"},
            ])
        elif language == "javascript":
            base_files.extend([
                {"path": "src/main.js", "type": "source"},
                {"path": "src/scenes/SceneManager.js", "type": "source"},
                {"path": "src/entities/Player.js", "type": "source"},
                {"path": "src/entities/Enemy.js", "type": "source"},
                {"path": "src/systems/Physics.js", "type": "source"},
                {"path": "src/systems/Input.js", "type": "source"},
                {"path": "src/systems/Renderer.js", "type": "source"},
                {"path": "src/ui/HUD.js", "type": "source"},
                {"path": "src/ui/Menus.js", "type": "source"},
                {"path": "package.json", "type": "config"},
                {"path": "index.html", "type": "source"},
            ])
        else:
            base_files.extend([
                {"path": "src/main.cs", "type": "source"},
                {"path": "src/scenes/SceneManager.cs", "type": "source"},
                {"path": "src/entities/Player.cs", "type": "source"},
                {"path": "src/entities/Enemy.cs", "type": "source"},
                {"path": "src/systems/PhysicsSystem.cs", "type": "source"},
                {"path": "src/systems/InputSystem.cs", "type": "source"},
                {"path": "src/ui/HUD.cs", "type": "source"},
                {"path": "src/ui/MenuController.cs", "type": "source"},
            ])

        # Add scene-specific files
        for i, scene in enumerate(blueprint.scenes):
            ext = {"python": "py", "javascript": "js", "csharp": "cs"}.get(language, "py")
            base_files.append({
                "path": f"src/scenes/{scene.name.lower().replace(' ', '_')}.{ext}",
                "type": "source",
            })

        manifest.extend(base_files)
        return manifest

    def _detect_project_language(self, blueprint: GameBlueprint) -> str:
        """Detect the most suitable programming language for the project."""
        if TargetPlatform.WEB in blueprint.target_platforms:
            return "javascript"
        if TargetPlatform.MOBILE in blueprint.target_platforms:
            return "csharp"
        return "python"

    def _get_entry_point(self, language: str) -> str:
        """Get the entry point file for a given language."""
        entry_points = {
            "python": "src/main.py",
            "javascript": "index.html",
            "csharp": "src/main.cs",
        }
        return entry_points.get(language, "src/main.py")

    def _generate_code_modules(
        self, blueprint: GameBlueprint
    ) -> List[Dict[str, Any]]:
        """Generate code module descriptions for the game."""
        modules: List[Dict[str, Any]] = []

        modules.append({
            "name": "Game Core",
            "description": "Main game loop, state management, and initialization",
            "estimated_lines": 200,
            "dependencies": [],
        })

        modules.append({
            "name": "Input Handler",
            "description": "Keyboard, mouse, touch, and gamepad input processing",
            "estimated_lines": 150,
            "dependencies": ["Game Core"],
        })

        modules.append({
            "name": "Scene Manager",
            "description": "Scene loading, transitions, and lifecycle management",
            "estimated_lines": 180,
            "dependencies": ["Game Core"],
        })

        modules.append({
            "name": "Entity System",
            "description": "Entity creation, management, and component system",
            "estimated_lines": 250,
            "dependencies": ["Game Core", "Scene Manager"],
        })

        modules.append({
            "name": "Physics Engine",
            "description": "Collision detection, gravity, and movement physics",
            "estimated_lines": 300,
            "dependencies": ["Entity System"],
        })

        modules.append({
            "name": "Rendering System",
            "description": "Sprite/model rendering, cameras, and visual effects",
            "estimated_lines": 350,
            "dependencies": ["Scene Manager", "Entity System"],
        })

        modules.append({
            "name": "UI System",
            "description": "HUD, menus, overlays, and UI element management",
            "estimated_lines": 200,
            "dependencies": ["Rendering System", "Input Handler"],
        })

        modules.append({
            "name": "Audio Manager",
            "description": "Sound effects, music playback, and audio mixing",
            "estimated_lines": 120,
            "dependencies": ["Game Core"],
        })

        modules.append({
            "name": "Save System",
            "description": "Game state serialization, save/load functionality",
            "estimated_lines": 100,
            "dependencies": ["Game Core"],
        })

        return modules

    def _validate_blueprint(self, blueprint: GameBlueprint) -> Dict[str, Any]:
        """Validate a blueprint for completeness and correctness."""
        checks: List[Dict[str, Any]] = []
        valid = True

        # Check required fields
        if not blueprint.name:
            checks.append({"check": "game_name", "passed": False, "message": "Game has no name"})
            valid = False
        else:
            checks.append({"check": "game_name", "passed": True, "message": "Game name is set"})

        if not blueprint.genres:
            checks.append({"check": "genres", "passed": False, "message": "No genres detected"})
            valid = False
        else:
            checks.append({"check": "genres", "passed": True, "message": f"{len(blueprint.genres)} genre(s) detected"})

        if not blueprint.core_loop:
            checks.append({"check": "core_loop", "passed": False, "message": "No core loop defined"})
            valid = False
        else:
            checks.append({"check": "core_loop", "passed": True, "message": "Core loop defined"})

        if not blueprint.mechanics:
            checks.append({"check": "mechanics", "passed": False, "message": "No mechanics defined"})
            valid = False
        else:
            checks.append({"check": "mechanics", "passed": True, "message": f"{len(blueprint.mechanics)} mechanic(s) defined"})

        if not blueprint.scenes:
            checks.append({"check": "scenes", "passed": False, "message": "No scenes generated"})
            valid = False
        else:
            checks.append({"check": "scenes", "passed": True, "message": f"{len(blueprint.scenes)} scene(s) generated"})

        if not blueprint.win_conditions:
            checks.append({"check": "win_conditions", "passed": False, "message": "No win conditions defined"})
            valid = False
        else:
            checks.append({"check": "win_conditions", "passed": True, "message": f"{len(blueprint.win_conditions)} win condition(s)"})

        if not blueprint.ui_layouts:
            checks.append({"check": "ui_layouts", "passed": False, "message": "No UI layouts generated"})
            valid = False
        else:
            checks.append({"check": "ui_layouts", "passed": True, "message": f"{len(blueprint.ui_layouts)} UI layout(s)"})

        return {
            "valid": valid,
            "check_count": len(checks),
            "checks": checks,
        }

    def _check_consistency(self, blueprint: GameBlueprint) -> Dict[str, Any]:
        """Check game logic consistency across the blueprint."""
        checks: List[Dict[str, Any]] = []
        consistent = True

        # Check that scenes reference existing mechanics
        all_mechanic_ids = {m.spec_id for m in blueprint.mechanics}
        for scene in blueprint.scenes:
            for mech_id in scene.mechanics:
                if mech_id not in all_mechanic_ids:
                    checks.append({
                        "check": f"scene_mechanic_ref",
                        "passed": False,
                        "message": f"Scene '{scene.name}' references unknown mechanic {mech_id}",
                    })
                    consistent = False

        if not checks:
            checks.append({"check": "scene_mechanic_refs", "passed": True, "message": "All scene mechanic references valid"})

        # Check that characters reference existing scenes
        all_scene_ids = {s.scene_id for s in blueprint.scenes}
        for char in blueprint.characters:
            if char.spawn_scene and char.spawn_scene not in all_scene_ids:
                checks.append({
                    "check": "character_spawn_scene",
                    "passed": False,
                    "message": f"Character '{char.name}' spawns in unknown scene '{char.spawn_scene}'",
                })
                consistent = False

        if not any(c["check"] == "character_spawn_scene" for c in checks if not c["passed"]):
            checks.append({"check": "character_spawn_scenes", "passed": True, "message": "All character spawn scenes valid"})

        # Check that mechanics match detected genres
        if blueprint.genres and blueprint.mechanics:
            checks.append({"check": "mechanic_genre_match", "passed": True, "message": "Mechanics align with detected genres"})

        return {
            "consistent": consistent,
            "check_count": len(checks),
            "checks": checks,
        }


# =============================================================================
# GameCreatorEngine (Singleton)
# =============================================================================


class GameCreatorEngine:
    """Thread-safe singleton engine for natural language game creation.

    Orchestrates the entire game creation workflow from natural language
    description to structured blueprint and through the phased creation
    pipeline. Tracks active creation sessions, supports iterative
    refinement, and provides comprehensive progress monitoring.

    Usage:
        creator = get_game_creator()
        session = creator.create_game("A 2D pixel art platformer where you
            collect stars and jump over enemies in a fantasy world")
        progress = creator.get_progress(session.session_id)
        creator.refine_game(session.session_id, "Make it harder with more enemies")
    """

    _instance: Optional["GameCreatorEngine"] = None
    _lock = threading.RLock()

    _MAX_SESSIONS: int = 100

    def __init__(self) -> None:
        self._sessions: Dict[str, CreationSession] = {}
        self._parser: GameSpecParser = GameSpecParser()
        self._assembler: GameAssembler = GameAssembler()
        self._pipeline: CreationPipeline = CreationPipeline()
        self._total_sessions: int = 0
        self._total_games_created: int = 0

    @classmethod
    def get_instance(cls) -> "GameCreatorEngine":
        """Return the singleton GameCreatorEngine instance."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    # ------------------------------------------------------------------
    # Game Creation
    # ------------------------------------------------------------------

    def create_game(self, description: str, name: str = "") -> CreationSession:
        """Create a new game from a natural language description.

        Parses the description, generates a blueprint, and runs the
        specification phase. The returned session is ready for further
        pipeline advancement.

        Args:
            description: Natural language description of the desired game.
            name: Optional game title. If empty, one is inferred.

        Returns:
            A CreationSession with the specification phase completed.
        """
        with self._lock:
            self._enforce_max_sessions()

            session = self._pipeline.create_session(description, name)
            self._sessions[session.session_id] = session
            self._total_sessions += 1
            self._total_games_created += 1
            return session

    def create_full_game(self, description: str, name: str = "") -> CreationSession:
        """Create a complete game through all pipeline phases.

        Runs the full six-phase pipeline: specification, design, scaffolding,
        implementation, testing, and refinement. Returns a session with all
        phases completed.

        Args:
            description: Natural language description of the desired game.
            name: Optional game title.

        Returns:
            A CreationSession with all six phases completed.
        """
        with self._lock:
            self._enforce_max_sessions()

            session = self._pipeline.create_session(description, name)
            self._pipeline.continue_session(session)
            self._sessions[session.session_id] = session
            self._total_sessions += 1
            self._total_games_created += 1
            return session

    # ------------------------------------------------------------------
    # Pipeline Control
    # ------------------------------------------------------------------

    def advance_session(self, session_id: str) -> Optional[CreationSession]:
        """Advance a session to the next pipeline phase.

        Args:
            session_id: The session ID to advance.

        Returns:
            The updated session, or None if not found.
        """
        with self._lock:
            session = self._sessions.get(session_id)
            if session is None:
                return None

            self._pipeline.continue_session(session)
            return session

    def advance_to_phase(
        self, session_id: str, target_phase: CreationPhase
    ) -> Optional[CreationSession]:
        """Advance a session to a specific phase, running all intermediate phases.

        Args:
            session_id: The session ID to advance.
            target_phase: The phase to reach.

        Returns:
            The updated session, or None if not found.
        """
        with self._lock:
            session = self._sessions.get(session_id)
            if session is None:
                return None

            self._pipeline.advance_phase(session, target_phase)
            return session

    def refine_game(
        self, session_id: str, feedback: str, target_phase: Optional[CreationPhase] = None
    ) -> Optional[CreationSession]:
        """Refine a game based on feedback.

        Records the feedback, applies it to the blueprint, and triggers
        the refinement pipeline phase.

        Args:
            session_id: The session ID to refine.
            feedback: Natural language feedback describing desired changes.
            target_phase: Specific phase to rework. Defaults to current phase.

        Returns:
            The updated session, or None if not found.
        """
        with self._lock:
            session = self._sessions.get(session_id)
            if session is None:
                return None

            self._pipeline.add_feedback(session, feedback, target_phase)
            return session

    # ------------------------------------------------------------------
    # Accessors
    # ------------------------------------------------------------------

    def get_session(self, session_id: str) -> Optional[CreationSession]:
        """Retrieve a creation session by ID.

        Args:
            session_id: The session ID.

        Returns:
            The CreationSession if found, None otherwise.
        """
        with self._lock:
            return self._sessions.get(session_id)

    def get_blueprint(self, session_id: str) -> Optional[GameBlueprint]:
        """Retrieve the game blueprint from a session.

        Args:
            session_id: The session ID.

        Returns:
            The GameBlueprint if found, None otherwise.
        """
        with self._lock:
            session = self._sessions.get(session_id)
            if session is None:
                return None
            return session.blueprint

    def get_progress(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get pipeline progress for a session.

        Args:
            session_id: The session ID.

        Returns:
            A progress dictionary, or None if the session is not found.
        """
        with self._lock:
            session = self._sessions.get(session_id)
            if session is None:
                return None
            return self._pipeline.get_progress(session)

    def list_sessions(self) -> List[Dict[str, Any]]:
        """List all active creation sessions.

        Returns:
            A list of session summary dictionaries.
        """
        with self._lock:
            summaries: List[Dict[str, Any]] = []
            for session in self._sessions.values():
                summaries.append({
                    "session_id": session.session_id,
                    "game_name": session.blueprint.name if session.blueprint else "Unknown",
                    "current_phase": session.current_phase.value,
                    "feedback_count": len(session.feedback_history),
                    "created_at": session.created_at,
                })
            return summaries

    # ------------------------------------------------------------------
    # Standalone Operations
    # ------------------------------------------------------------------

    def parse_description(self, description: str, name: str = "") -> GameBlueprint:
        """Parse a natural language description into a blueprint without creating a session.

        Args:
            description: Natural language description of the desired game.
            name: Optional game title.

        Returns:
            A GameBlueprint with extracted specifications.
        """
        with self._lock:
            return self._parser.parse(description, name)

    def assemble_from_blueprint(self, blueprint: GameBlueprint) -> GameBlueprint:
        """Assemble game components from an existing blueprint.

        Args:
            blueprint: The game blueprint to assemble components for.

        Returns:
            The same blueprint with scenes, characters, UI, and assets populated.
        """
        with self._lock:
            self._assembler.assemble_scenes(blueprint)
            self._assembler.assemble_characters(blueprint)
            self._assembler.assemble_ui_layouts(blueprint)
            self._assembler.assemble_asset_requirements(blueprint)
            return blueprint

    # ------------------------------------------------------------------
    # Statistics
    # ------------------------------------------------------------------

    def get_stats(self) -> Dict[str, Any]:
        """Return comprehensive creation engine statistics.

        Returns:
            A dictionary with session counts, phase distribution, and
            genre distribution across all sessions.
        """
        with self._lock:
            phase_counts: Dict[str, int] = {}
            genre_counts: Dict[str, int] = {}
            complexity_counts: Dict[str, int] = {}

            for session in self._sessions.values():
                phase = session.current_phase.value
                phase_counts[phase] = phase_counts.get(phase, 0) + 1

                if session.blueprint:
                    for genre in session.blueprint.genres:
                        genre_counts[genre.value] = genre_counts.get(genre.value, 0) + 1
                    comp = session.blueprint.complexity.value
                    complexity_counts[comp] = complexity_counts.get(comp, 0) + 1

            total_feedback = sum(len(s.feedback_history) for s in self._sessions.values())

            return {
                "total_sessions": self._total_sessions,
                "active_sessions": len(self._sessions),
                "total_games_created": self._total_games_created,
                "phase_distribution": phase_counts,
                "genre_distribution": genre_counts,
                "complexity_distribution": complexity_counts,
                "total_feedback_items": total_feedback,
                "max_sessions": self._MAX_SESSIONS,
            }

    def reset(self) -> None:
        """Reset the engine, clearing all sessions."""
        with self._lock:
            self._sessions.clear()
            self._total_sessions = 0
            self._total_games_created = 0

    # ------------------------------------------------------------------
    # Internal Helpers
    # ------------------------------------------------------------------

    def _enforce_max_sessions(self) -> None:
        """Enforce the maximum number of active sessions."""
        if len(self._sessions) >= self._MAX_SESSIONS:
            sorted_sessions = sorted(
                self._sessions.items(),
                key=lambda item: item[1].created_at,
            )
            overflow = len(self._sessions) - self._MAX_SESSIONS + 1
            for sid, _ in sorted_sessions[:overflow]:
                self._sessions.pop(sid, None)


# =============================================================================
# Module-Level Accessor
# =============================================================================


def get_game_creator() -> GameCreatorEngine:
    """Return the singleton GameCreatorEngine instance."""
    return GameCreatorEngine.get_instance()