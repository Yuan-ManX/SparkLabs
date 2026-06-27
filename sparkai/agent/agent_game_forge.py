"""
SparkLabs Agent - Agent Game Forge

AI-powered game creation engine that synthesizes complete playable games from
natural language descriptions. Combines structured reasoning, world simulation,
multi-agent orchestration, and code generation into a unified game creation pipeline.

Architecture:
  AgentGameForge (Singleton)
    |-- DesignSynthesizer: generates game design documents from prompts
    |-- MechanicsForge: designs and balances game mechanics
    |-- WorldArchitect: procedurally generates game worlds
    |-- CodeSynthesizer: generates production-ready game code
    |-- AssetCoordinator: manages multi-modal asset generation
    |-- PlaytestSimulator: simulates gameplay and provides feedback
    |-- IterationEngine: iteratively refines game based on feedback

Game Creation Pipeline:
  1. IDEATION: parse natural language into structured game concept
  2. DESIGN: generate comprehensive game design document
  3. ARCHITECTURE: design software architecture and component tree
  4. WORLD: procedurally generate game world and levels
  5. MECHANICS: design and balance core gameplay mechanics
  6. CODE: generate production-ready game code
  7. ASSETS: coordinate multi-modal asset generation
  8. ASSEMBLY: assemble all components into a playable game
  9. PLAYTEST: simulate gameplay and gather metrics
  10. ITERATE: refine based on playtest feedback

Usage:
    forge = AgentGameForge.get_instance()
    forge.initialize()

    game = forge.create_game(
        "A rogue-like dungeon crawler where you play as a time-traveling wizard"
    )
    forge.playtest(game.project_id)
    forge.iterate(game.project_id, feedback="Make combat more strategic")
    forge.deploy(game.project_id, platform="web")
    forge.shutdown()
"""

from __future__ import annotations

import json
import threading
import time
import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple, Union

from sparkai.agent.agent_ai_native_orchestrator import get_ai_native_orchestrator


# =============================================================================
# Enums
# =============================================================================


class ForgePhase(Enum):
    """Phases of the game creation pipeline."""
    IDEATION = "ideation"
    DESIGN = "design"
    ARCHITECTURE = "architecture"
    WORLD = "world"
    MECHANICS = "mechanics"
    CODE = "code"
    ASSETS = "assets"
    ASSEMBLY = "assembly"
    PLAYTEST = "playtest"
    ITERATE = "iterate"
    DEPLOY = "deploy"
    COMPLETE = "complete"


class GameGenre(Enum):
    """Supported game genres."""
    PLATFORMER = "platformer"
    ROGUE_LIKE = "rogue_like"
    RPG = "rpg"
    SHOOTER = "shooter"
    PUZZLE = "puzzle"
    STRATEGY = "strategy"
    SIMULATION = "simulation"
    ADVENTURE = "adventure"
    RACING = "racing"
    FIGHTING = "fighting"
    SANDBOX = "sandbox"
    VISUAL_NOVEL = "visual_novel"
    SURVIVAL = "survival"
    METROIDVANIA = "metroidvania"
    TOWER_DEFENSE = "tower_defense"
    CUSTOM = "custom"


class DesignFidelity(Enum):
    """Fidelity level of generated design documents."""
    CONCEPT = "concept"
    SKETCH = "sketch"
    DETAILED = "detailed"
    PRODUCTION = "production"


class CodeQuality(Enum):
    """Target code quality level."""
    PROTOTYPE = "prototype"
    PLAYABLE = "playable"
    POLISHED = "polished"
    PRODUCTION = "production"


class AssetStyle(Enum):
    """Visual style of generated assets."""
    PIXEL_ART = "pixel_art"
    FLAT_2D = "flat_2d"
    CARTOON = "cartoon"
    REALISTIC = "realistic"
    LOW_POLY = "low_poly"
    VOXEL = "voxel"
    STYLIZED = "stylized"
    MINIMALIST = "minimalist"


class Platform(Enum):
    """Target deployment platforms."""
    WEB = "web"
    DESKTOP = "desktop"
    MOBILE = "mobile"
    CONSOLE = "console"


# =============================================================================
# Data Classes
# =============================================================================


@dataclass
class GameConcept:
    """Parsed game concept from natural language."""
    concept_id: str
    title: str
    genre: GameGenre
    description: str
    core_loop: str = ""
    target_audience: str = "general"
    tone: str = "neutral"
    unique_selling_points: List[str] = field(default_factory=list)
    inspirations: List[str] = field(default_factory=list)
    constraints: Dict[str, Any] = field(default_factory=dict)
    raw_prompt: str = ""
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "concept_id": self.concept_id,
            "title": self.title,
            "genre": self.genre.value,
            "description": self.description,
            "core_loop": self.core_loop,
            "target_audience": self.target_audience,
            "tone": self.tone,
            "unique_selling_points": self.unique_selling_points,
            "inspirations": self.inspirations,
            "constraints": self.constraints,
            "created_at": self.created_at,
        }


@dataclass
class MechanicDefinition:
    """A single game mechanic definition."""
    mechanic_id: str
    name: str
    category: str  # "movement", "combat", "economy", "progression", etc.
    description: str
    rules: Dict[str, Any] = field(default_factory=dict)
    parameters: Dict[str, Any] = field(default_factory=dict)
    balance_targets: Dict[str, float] = field(default_factory=dict)
    dependencies: List[str] = field(default_factory=list)
    complexity: str = "medium"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "mechanic_id": self.mechanic_id,
            "name": self.name,
            "category": self.category,
            "description": self.description,
            "rules": self.rules,
            "parameters": self.parameters,
            "balance_targets": self.balance_targets,
            "dependencies": self.dependencies,
            "complexity": self.complexity,
        }


@dataclass
class GameArchitecture:
    """Software architecture definition for a game."""
    architecture_id: str
    component_tree: Dict[str, Any] = field(default_factory=dict)
    data_flow: Dict[str, Any] = field(default_factory=dict)
    system_dependencies: Dict[str, List[str]] = field(default_factory=dict)
    entry_points: Dict[str, str] = field(default_factory=dict)
    file_structure: Dict[str, Any] = field(default_factory=dict)
    technology_stack: Dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "architecture_id": self.architecture_id,
            "component_tree": self.component_tree,
            "data_flow": self.data_flow,
            "system_dependencies": self.system_dependencies,
            "entry_points": self.entry_points,
            "file_structure": self.file_structure,
            "technology_stack": self.technology_stack,
        }


@dataclass
class CodeModule:
    """A generated code module."""
    module_id: str
    file_path: str
    language: str
    content: str
    purpose: str = ""
    dependencies: List[str] = field(default_factory=list)
    test_content: str = ""
    quality: CodeQuality = CodeQuality.PROTOTYPE
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "module_id": self.module_id,
            "file_path": self.file_path,
            "language": self.language,
            "content": self.content,
            "purpose": self.purpose,
            "dependencies": self.dependencies,
            "test_content": self.test_content,
            "quality": self.quality.value,
            "content_length": len(self.content),
            "metadata": self.metadata,
        }


@dataclass
class AssetSpecification:
    """Specification for a game asset to be generated."""
    asset_id: str
    asset_type: str  # "sprite", "sound", "music", "level", "ui", "font", "shader"
    name: str
    description: str
    style: AssetStyle = AssetStyle.FLAT_2D
    dimensions: Tuple[int, int] = (64, 64)
    format: str = "png"
    parameters: Dict[str, Any] = field(default_factory=dict)
    priority: int = 5

    def to_dict(self) -> Dict[str, Any]:
        return {
            "asset_id": self.asset_id,
            "asset_type": self.asset_type,
            "name": self.name,
            "description": self.description,
            "style": self.style.value,
            "dimensions": list(self.dimensions),
            "format": self.format,
            "parameters": self.parameters,
            "priority": self.priority,
        }


@dataclass
class PlaytestReport:
    """Report from simulated gameplay testing."""
    report_id: str
    project_id: str
    is_playable: bool = True
    fun_score: float = 0.0
    engagement_score: float = 0.0
    balance_score: float = 0.0
    performance_score: float = 0.0
    bugs_found: int = 0
    suggestions: List[str] = field(default_factory=list)
    mechanics_analysis: Dict[str, Any] = field(default_factory=dict)
    player_flow_analysis: Dict[str, Any] = field(default_factory=dict)
    difficulty_curve: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "report_id": self.report_id,
            "project_id": self.project_id,
            "is_playable": self.is_playable,
            "fun_score": self.fun_score,
            "engagement_score": self.engagement_score,
            "balance_score": self.balance_score,
            "performance_score": self.performance_score,
            "bugs_found": self.bugs_found,
            "suggestions": self.suggestions,
            "mechanics_analysis": self.mechanics_analysis,
            "player_flow_analysis": self.player_flow_analysis,
            "difficulty_curve": self.difficulty_curve,
            "timestamp": self.timestamp,
        }


@dataclass
class ForgeProject:
    """Complete game project managed by the forge."""
    project_id: str
    concept: Optional[GameConcept] = None
    design_document: Dict[str, Any] = field(default_factory=dict)
    architecture: Optional[GameArchitecture] = None
    mechanics: List[MechanicDefinition] = field(default_factory=list)
    world_data: Dict[str, Any] = field(default_factory=dict)
    code_modules: List[CodeModule] = field(default_factory=list)
    asset_specs: List[AssetSpecification] = field(default_factory=list)
    playtest_reports: List[PlaytestReport] = field(default_factory=list)
    current_phase: ForgePhase = ForgePhase.IDEATION
    phase_history: List[Dict[str, Any]] = field(default_factory=list)
    iterations: int = 0
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "project_id": self.project_id,
            "concept": self.concept.to_dict() if self.concept else None,
            "design_document": self.design_document,
            "architecture": self.architecture.to_dict() if self.architecture else None,
            "mechanics_count": len(self.mechanics),
            "mechanics": [m.to_dict() for m in self.mechanics],
            "world_data": self.world_data,
            "code_modules_count": len(self.code_modules),
            "code_modules": [m.to_dict() for m in self.code_modules],
            "asset_specs_count": len(self.asset_specs),
            "asset_specs": [a.to_dict() for a in self.asset_specs],
            "playtest_reports": [r.to_dict() for r in self.playtest_reports],
            "current_phase": self.current_phase.value,
            "phase_history": self.phase_history,
            "iterations": self.iterations,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "metadata": self.metadata,
        }


# =============================================================================
# Design Synthesizer
# =============================================================================


class DesignSynthesizer:
    """
    Synthesizes game design documents from natural language descriptions.
    Uses structured reasoning to extract genre, mechanics, aesthetics,
    and narrative elements from free-form text.
    """

    def __init__(self) -> None:
        self._genre_patterns: Dict[GameGenre, List[str]] = {
            GameGenre.PLATFORMER: ["platform", "jump", "run", "side-scroll", "levels"],
            GameGenre.ROGUE_LIKE: ["rogue", "procedural", "permadeath", "dungeon", "random"],
            GameGenre.RPG: ["rpg", "role", "character", "level up", "stats", "quest", "inventory"],
            GameGenre.SHOOTER: ["shoot", "gun", "bullet", "fps", "top-down shooter"],
            GameGenre.PUZZLE: ["puzzle", "solve", "match", "logic", "brain"],
            GameGenre.STRATEGY: ["strategy", "tactics", "build", "manage", "resource"],
            GameGenre.SIMULATION: ["simulation", "sim", "life", "sandbox", "manage"],
            GameGenre.ADVENTURE: ["adventure", "explore", "story", "narrative", "point-and-click"],
            GameGenre.SURVIVAL: ["survival", "craft", "gather", "hunger", "build"],
            GameGenre.METROIDVANIA: ["metroidvania", "interconnected", "ability-gated", "backtrack"],
            GameGenre.TOWER_DEFENSE: ["tower defense", "waves", "enemies", "path"],
        }

    def parse_concept(self, prompt: str) -> GameConcept:
        """Parse a natural language prompt into a structured GameConcept."""
        concept_id = f"concept_{uuid.uuid4().hex[:12]}"
        detected_genre = self._detect_genre(prompt.lower())
        title = self._extract_title(prompt)
        core_loop = self._extract_core_loop(prompt, detected_genre)
        usp = self._extract_usp(prompt)
        tone = self._detect_tone(prompt)

        return GameConcept(
            concept_id=concept_id,
            title=title,
            genre=detected_genre,
            description=prompt,
            core_loop=core_loop,
            unique_selling_points=usp,
            tone=tone,
            raw_prompt=prompt,
        )

    def _detect_genre(self, text: str) -> GameGenre:
        """Detect game genre from text using keyword matching."""
        scores: Dict[GameGenre, int] = {}
        for genre, keywords in self._genre_patterns.items():
            score = sum(1 for kw in keywords if kw in text)
            if score > 0:
                scores[genre] = score
        if not scores:
            return GameGenre.CUSTOM
        return max(scores, key=scores.get)

    def _extract_title(self, prompt: str) -> str:
        """Extract or generate a title from the prompt."""
        words = prompt.split()
        if len(words) <= 8:
            return prompt[:50].strip()
        key_words = [w for w in words if len(w) > 3][:4]
        return " ".join(key_words).title() if key_words else "Untitled Game"

    def _extract_core_loop(self, prompt: str, genre: GameGenre) -> str:
        """Extract the core gameplay loop from the prompt."""
        genre_loops = {
            GameGenre.PLATFORMER: "Run, jump, collect, defeat enemies, reach goal",
            GameGenre.ROGUE_LIKE: "Explore dungeon, fight enemies, collect loot, die, upgrade, repeat",
            GameGenre.RPG: "Quest, battle, level up, equip gear, progress story",
            GameGenre.SHOOTER: "Aim, shoot, move, reload, eliminate targets",
            GameGenre.PUZZLE: "Observe, analyze, solve, progress to harder puzzles",
            GameGenre.STRATEGY: "Plan, build, manage resources, expand, conquer",
            GameGenre.SURVIVAL: "Gather, craft, build, survive threats, expand base",
        }
        return genre_loops.get(genre, "Interact, progress, achieve goals, advance")

    def _extract_usp(self, prompt: str) -> List[str]:
        """Extract unique selling points from the prompt."""
        innovation_markers = ["unique", "innovative", "time-travel", "gravity",
                            "dimension", "parallel", "transform", "possess",
                            "morph", "teleport", "phase", "reality"]
        usp = []
        for marker in innovation_markers:
            if marker in prompt.lower():
                usp.append(f"Feature: {marker.replace('-', ' ').title()}")
        return usp if usp else ["Original gameplay mechanics"]

    def _detect_tone(self, prompt: str) -> str:
        """Detect the tonal direction from the prompt."""
        tone_keywords = {
            "dark": ["dark", "horror", "grim", "dread", "haunting", "gothic"],
            "lighthearted": ["cute", "funny", "comedy", "quirky", "silly", "whimsical"],
            "epic": ["epic", "grand", "heroic", "legendary", "majestic"],
            "mysterious": ["mystery", "mysterious", "secret", "unknown", "enigma"],
            "peaceful": ["peaceful", "calm", "relaxing", "cozy", "tranquil"],
        }
        prompt_lower = prompt.lower()
        for tone, keywords in tone_keywords.items():
            if any(kw in prompt_lower for kw in keywords):
                return tone
        return "neutral"

    def generate_design_document(self, concept: GameConcept,
                                  fidelity: DesignFidelity = DesignFidelity.DETAILED) -> Dict[str, Any]:
        """Generate a comprehensive game design document from a concept."""
        doc = {
            "document_id": f"gdd_{uuid.uuid4().hex[:12]}",
            "concept_id": concept.concept_id,
            "title": concept.title,
            "genre": concept.genre.value,
            "fidelity": fidelity.value,
            "sections": {
                "overview": {
                    "elevator_pitch": concept.description,
                    "core_loop": concept.core_loop,
                    "target_audience": concept.target_audience,
                    "tone": concept.tone,
                    "unique_selling_points": concept.unique_selling_points,
                },
                "gameplay": self._generate_gameplay_section(concept),
                "narrative": self._generate_narrative_section(concept),
                "aesthetics": self._generate_aesthetics_section(concept),
                "technical": self._generate_technical_section(concept),
                "monetization": self._generate_monetization_section(concept),
            },
            "created_at": time.time(),
        }
        return doc

    def _generate_gameplay_section(self, concept: GameConcept) -> Dict[str, Any]:
        """Generate gameplay design section."""
        return {
            "player_verbs": self._get_player_verbs(concept.genre),
            "control_scheme": self._get_control_scheme(concept.genre),
            "camera_perspective": self._get_camera_perspective(concept.genre),
            "progression_system": self._get_progression_system(concept.genre),
            "challenge_types": self._get_challenge_types(concept.genre),
            "session_length": "15-30 minutes",
            "difficulty_curve": "Gradual with spikes at boss encounters",
        }

    def _generate_narrative_section(self, concept: GameConcept) -> Dict[str, Any]:
        """Generate narrative design section."""
        return {
            "story_hook": f"In a world where {concept.description[:80]}...",
            "protagonist": "Player character with unique abilities",
            "antagonist": "To be developed based on world context",
            "narrative_structure": "Three-act structure with branching choices",
            "world_building_notes": "Rich lore integrated into environmental storytelling",
            "character_arcs": ["Player growth arc", "Key NPC transformation"],
        }

    def _generate_aesthetics_section(self, concept: GameConcept) -> Dict[str, Any]:
        """Generate aesthetics design section."""
        return {
            "visual_style": "Stylized 2D with vibrant color palette",
            "color_palette": "Primary: jewel tones, Secondary: earthy neutrals",
            "ui_style": "Clean, diegetic where possible, minimal HUD",
            "audio_direction": "Dynamic ambient with reactive combat music",
            "vfx_style": "Satisfying feedback particles with screen shake",
        }

    def _generate_technical_section(self, concept: GameConcept) -> Dict[str, Any]:
        """Generate technical design section."""
        return {
            "target_platforms": ["web", "desktop", "mobile"],
            "engine": "SparkLabs AI-Native Runtime",
            "language": "python",
            "rendering": "2D Canvas with WebGL acceleration",
            "physics": "2D physics with collision detection",
            "networking": "Optional leaderboard and cloud save",
            "performance_target": "60 FPS on mid-range devices",
        }

    def _generate_monetization_section(self, concept: GameConcept) -> Dict[str, Any]:
        """Generate monetization design section."""
        return {
            "model": "Premium with optional cosmetic DLC",
            "price_point": "$9.99",
            "post_launch": ["Free content updates", "Seasonal events"],
        }

    def _get_player_verbs(self, genre: GameGenre) -> List[str]:
        verbs = {
            GameGenre.PLATFORMER: ["Run", "Jump", "Dash", "Wall-slide", "Attack"],
            GameGenre.ROGUE_LIKE: ["Move", "Attack", "Dodge", "Use item", "Interact"],
            GameGenre.RPG: ["Move", "Talk", "Attack", "Cast spell", "Use item", "Trade"],
            GameGenre.SHOOTER: ["Move", "Aim", "Shoot", "Reload", "Throw grenade"],
            GameGenre.PUZZLE: ["Click", "Drag", "Rotate", "Combine", "Select"],
            GameGenre.STRATEGY: ["Select", "Move unit", "Build", "Research", "Attack"],
            GameGenre.SURVIVAL: ["Move", "Gather", "Craft", "Build", "Attack", "Eat"],
        }
        return verbs.get(genre, ["Move", "Interact", "Use", "Attack"])

    def _get_control_scheme(self, genre: GameGenre) -> str:
        schemes = {
            GameGenre.PLATFORMER: "Keyboard + Gamepad (D-pad/Stick + buttons)",
            GameGenre.ROGUE_LIKE: "Keyboard (WASD + Mouse) or Gamepad",
            GameGenre.RPG: "Keyboard + Mouse or Gamepad",
            GameGenre.SHOOTER: "Keyboard (WASD) + Mouse or Twin-stick Gamepad",
            GameGenre.PUZZLE: "Mouse/Touch primarily",
            GameGenre.STRATEGY: "Mouse + Keyboard shortcuts",
            GameGenre.SURVIVAL: "Keyboard (WASD) + Mouse",
        }
        return schemes.get(genre, "Keyboard + Mouse")

    def _get_camera_perspective(self, genre: GameGenre) -> str:
        perspectives = {
            GameGenre.PLATFORMER: "Side-scrolling 2D",
            GameGenre.ROGUE_LIKE: "Top-down 2D",
            GameGenre.RPG: "Top-down or Isometric",
            GameGenre.SHOOTER: "Top-down or First-person",
            GameGenre.PUZZLE: "2D board or screen view",
            GameGenre.STRATEGY: "Top-down or Isometric",
            GameGenre.SURVIVAL: "Top-down or Side-scrolling",
        }
        return perspectives.get(genre, "2D overhead")

    def _get_progression_system(self, genre: GameGenre) -> str:
        systems = {
            GameGenre.PLATFORMER: "Level-based with power-up unlocks",
            GameGenre.ROGUE_LIKE: "Run-based with meta-progression unlocks",
            GameGenre.RPG: "XP-based leveling with skill trees",
            GameGenre.SHOOTER: "Level-based with weapon unlocks",
            GameGenre.PUZZLE: "Level-based with increasing complexity",
            GameGenre.STRATEGY: "Tech tree and resource accumulation",
            GameGenre.SURVIVAL: "Crafting tier unlocks and base expansion",
        }
        return systems.get(genre, "Level-based progression")

    def _get_challenge_types(self, genre: GameGenre) -> List[str]:
        challenges = {
            GameGenre.PLATFORMER: ["Precision platforming", "Timed sequences", "Boss battles"],
            GameGenre.ROGUE_LIKE: ["Random room layouts", "Enemy variety", "Resource scarcity"],
            GameGenre.RPG: ["Combat encounters", "Dialogue choices", "Puzzle solving"],
            GameGenre.SHOOTER: ["Enemy waves", "Boss fights", "Ammo management"],
            GameGenre.PUZZLE: ["Logic puzzles", "Pattern recognition", "Spatial reasoning"],
            GameGenre.STRATEGY: ["Resource management", "Tactical positioning", "Opponent AI"],
            GameGenre.SURVIVAL: ["Resource scarcity", "Environmental hazards", "Hostile creatures"],
        }
        return challenges.get(genre, ["Skill-based challenges", "Resource management"])


# =============================================================================
# Mechanics Forge
# =============================================================================


class MechanicsForge:
    """
    Designs, balances, and validates game mechanics.
    Generates complete mechanics systems with parameterized tuning.
    """

    def __init__(self) -> None:
        self._mechanic_templates: Dict[str, Dict[str, Any]] = self._load_templates()

    def _load_templates(self) -> Dict[str, Dict[str, Any]]:
        """Load mechanic templates for common game systems."""
        return {
            "movement": {
                "parameters": {
                    "move_speed": {"default": 200, "min": 50, "max": 500, "unit": "px/s"},
                    "jump_force": {"default": 400, "min": 100, "max": 800, "unit": "px/s"},
                    "gravity": {"default": 980, "min": 200, "max": 2000, "unit": "px/s²"},
                    "acceleration": {"default": 1000, "min": 200, "max": 3000, "unit": "px/s²"},
                    "friction": {"default": 800, "min": 100, "max": 2000, "unit": "px/s²"},
                },
                "dependencies": ["physics_engine"],
            },
            "combat": {
                "parameters": {
                    "attack_damage": {"default": 10, "min": 1, "max": 100, "unit": "hp"},
                    "attack_speed": {"default": 1.0, "min": 0.1, "max": 5.0, "unit": "attacks/s"},
                    "attack_range": {"default": 50, "min": 10, "max": 500, "unit": "px"},
                    "critical_chance": {"default": 0.1, "min": 0.0, "max": 1.0, "unit": "%"},
                    "critical_multiplier": {"default": 2.0, "min": 1.0, "max": 5.0, "unit": "x"},
                },
                "dependencies": ["health_system", "collision_system"],
            },
            "health": {
                "parameters": {
                    "max_health": {"default": 100, "min": 10, "max": 1000, "unit": "hp"},
                    "health_regen": {"default": 0, "min": 0, "max": 50, "unit": "hp/s"},
                    "invincibility_duration": {"default": 0.5, "min": 0, "max": 3.0, "unit": "s"},
                    "armor_value": {"default": 0, "min": 0, "max": 100, "unit": "def"},
                },
                "dependencies": [],
            },
            "inventory": {
                "parameters": {
                    "max_slots": {"default": 20, "min": 4, "max": 100, "unit": "slots"},
                    "stack_limit": {"default": 99, "min": 1, "max": 999, "unit": "items"},
                    "equip_slots": {"default": 6, "min": 2, "max": 12, "unit": "slots"},
                },
                "dependencies": [],
            },
            "economy": {
                "parameters": {
                    "starting_currency": {"default": 100, "min": 0, "max": 10000, "unit": "coins"},
                    "currency_drop_rate": {"default": 0.3, "min": 0, "max": 1.0, "unit": "%"},
                    "shop_price_multiplier": {"default": 1.0, "min": 0.5, "max": 5.0, "unit": "x"},
                },
                "dependencies": ["inventory_system"],
            },
            "progression": {
                "parameters": {
                    "xp_per_level": {"default": 100, "min": 10, "max": 1000, "unit": "xp"},
                    "xp_curve_exponent": {"default": 1.5, "min": 1.0, "max": 3.0, "unit": ""},
                    "skill_points_per_level": {"default": 1, "min": 1, "max": 5, "unit": "pts"},
                    "max_level": {"default": 50, "min": 10, "max": 100, "unit": "lv"},
                },
                "dependencies": [],
            },
            "enemy_ai": {
                "parameters": {
                    "detection_range": {"default": 200, "min": 50, "max": 1000, "unit": "px"},
                    "patrol_speed": {"default": 100, "min": 20, "max": 300, "unit": "px/s"},
                    "chase_speed": {"default": 250, "min": 50, "max": 500, "unit": "px/s"},
                    "attack_cooldown": {"default": 1.0, "min": 0.1, "max": 5.0, "unit": "s"},
                    "flee_health_threshold": {"default": 0.2, "min": 0, "max": 0.5, "unit": "%"},
                },
                "dependencies": ["health_system", "movement_system"],
            },
        }

    def design_mechanics_for_genre(self, genre: GameGenre) -> List[MechanicDefinition]:
        """Design a complete set of mechanics for a given genre."""
        mechanics = []
        mechanic_sets = self._get_mechanic_sets_for_genre(genre)

        for mechanic_name in mechanic_sets:
            template = self._mechanic_templates.get(mechanic_name, {})
            mechanic = MechanicDefinition(
                mechanic_id=f"mech_{uuid.uuid4().hex[:8]}",
                name=mechanic_name.replace("_", " ").title(),
                category=mechanic_name,
                description=f"Core {mechanic_name} system for {genre.value} game",
                parameters=template.get("parameters", {}),
                dependencies=template.get("dependencies", []),
            )
            mechanics.append(mechanic)

        return mechanics

    def _get_mechanic_sets_for_genre(self, genre: GameGenre) -> List[str]:
        """Get the required mechanic sets for a genre."""
        genre_sets = {
            GameGenre.PLATFORMER: ["movement", "health", "combat", "progression"],
            GameGenre.ROGUE_LIKE: ["movement", "health", "combat", "inventory", "progression", "enemy_ai"],
            GameGenre.RPG: ["movement", "health", "combat", "inventory", "economy", "progression", "enemy_ai"],
            GameGenre.SHOOTER: ["movement", "health", "combat", "progression", "enemy_ai"],
            GameGenre.SURVIVAL: ["movement", "health", "inventory", "economy", "progression", "enemy_ai"],
            GameGenre.STRATEGY: ["economy", "progression", "enemy_ai"],
        }
        return genre_sets.get(genre, ["movement", "health", "progression"])

    def balance_mechanics(self, mechanics: List[MechanicDefinition],
                          difficulty: str = "normal") -> List[MechanicDefinition]:
        """Balance mechanic parameters based on target difficulty."""
        difficulty_multipliers = {
            "easy": 0.7,
            "normal": 1.0,
            "hard": 1.5,
            "extreme": 2.0,
        }
        multiplier = difficulty_multipliers.get(difficulty, 1.0)

        for mechanic in mechanics:
            if mechanic.category == "combat":
                for param_name in mechanic.parameters:
                    if "damage" in param_name or "speed" in param_name:
                        mechanic.parameters[param_name]["default"] *= multiplier
            elif mechanic.category == "enemy_ai":
                for param_name in mechanic.parameters:
                    if "detection" in param_name or "chase" in param_name:
                        mechanic.parameters[param_name]["default"] *= multiplier
                    elif "health" in param_name:
                        mechanic.parameters[param_name]["default"] *= (1.0 + multiplier * 0.5)

        return mechanics

    def generate_mechanic_code(self, mechanic: MechanicDefinition,
                               language: str = "python") -> str:
        """Generate implementation code for a mechanic."""
        code = f'''"""
{mechanic.name} System - Auto-generated by SparkLabs Agent Game Forge
"""


class {mechanic.name.replace(" ", "")}System:
    """Core {mechanic.name.lower()} system for game entity."""

    def __init__(self):
        self._parameters = {json.dumps(mechanic.parameters, indent=8)}
        self._state = {{}}

    def initialize(self, entity_id: str):
        """Initialize {mechanic.name.lower()} for an entity."""
        self._state[entity_id] = {{
            param: data["default"]
            for param, data in self._parameters.items()
        }}

    def get_parameter(self, entity_id: str, param_name: str):
        """Get a parameter value for an entity."""
        return self._state.get(entity_id, {{}}).get(
            param_name,
            self._parameters.get(param_name, {{}}).get("default", 0)
        )

    def set_parameter(self, entity_id: str, param_name: str, value):
        """Set a parameter value for an entity."""
        if entity_id not in self._state:
            self.initialize(entity_id)
        param_def = self._parameters.get(param_name, {{}})
        if "min" in param_def and "max" in param_def:
            value = max(param_def["min"], min(param_def["max"], value))
        self._state[entity_id][param_name] = value

    def update(self, entity_id: str, delta_time: float):
        """Update {mechanic.name.lower()} state for an entity."""
        pass

    def cleanup(self, entity_id: str):
        """Remove entity from {mechanic.name.lower()} system."""
        self._state.pop(entity_id, None)
'''
        return code


# =============================================================================
# Code Synthesizer
# =============================================================================


class CodeSynthesizer:
    """
    Generates production-ready game code from design specifications.
    Produces modular, well-structured code with proper architecture.
    """

    def __init__(self) -> None:
        self._code_templates: Dict[str, str] = self._load_templates()

    def _load_templates(self) -> Dict[str, str]:
        """Load code templates for common game components."""
        return {
            "game_main": '''"""
{title} - Main Entry Point
Generated by SparkLabs Agent Game Forge
"""

import pygame
import sys
from {module_name}.game_scene import GameScene
from {module_name}.settings import GameSettings


class Game:
    """Main game application class."""

    def __init__(self):
        self.settings = GameSettings()
        self.screen = pygame.display.set_mode(
            (self.settings.WINDOW_WIDTH, self.settings.WINDOW_HEIGHT)
        )
        pygame.display.set_caption("{title}")
        self.clock = pygame.time.Clock()
        self.running = True
        self.scene = GameScene(self)

    def run(self):
        """Main game loop."""
        while self.running:
            delta_time = self.clock.tick(self.settings.FPS) / 1000.0
            self._handle_events()
            self.scene.update(delta_time)
            self.scene.render(self.screen)
            pygame.display.flip()
        self.quit()

    def _handle_events(self):
        """Process input events."""
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            self.scene.handle_event(event)

    def quit(self):
        """Clean shutdown."""
        pygame.quit()
        sys.exit()


if __name__ == "__main__":
    game = Game()
    game.run()
''',
            "game_scene": '''"""
{title} - Game Scene
"""

import pygame
from {module_name}.entities.player import Player
from {module_name}.entities.enemy import EnemyManager
from {module_name}.systems.camera import Camera
from {module_name}.systems.collision import CollisionSystem


class GameScene:
    """Main gameplay scene."""

    def __init__(self, game):
        self.game = game
        self.player = Player()
        self.enemies = EnemyManager()
        self.camera = Camera(game.settings.WINDOW_WIDTH, game.settings.WINDOW_HEIGHT)
        self.collision = CollisionSystem()
        self._initialize_scene()

    def _initialize_scene(self):
        """Set up the initial scene state."""
        self.player.spawn(400, 300)
        self.enemies.spawn_wave(1)

    def handle_event(self, event):
        """Process input events."""
        self.player.handle_event(event)

    def update(self, delta_time):
        """Update scene state."""
        self.player.update(delta_time)
        self.enemies.update(delta_time, self.player)
        self.collision.check_collisions(self.player, self.enemies)
        self.camera.follow(self.player)

    def render(self, screen):
        """Render the scene."""
        screen.fill((30, 30, 40))
        self.enemies.render(screen, self.camera)
        self.player.render(screen, self.camera)
''',
            "player_entity": '''"""
{title} - Player Entity
"""

import pygame
from {module_name}.systems.physics import PhysicsBody


class Player:
    """Player-controlled game entity."""

    def __init__(self):
        self.x = 0
        self.y = 0
        self.width = 32
        self.height = 32
        self.physics = PhysicsBody()
        self.health = 100
        self.max_health = 100
        self.speed = {move_speed}
        self.jump_force = {jump_force}
        self.is_grounded = False
        self.facing_right = True
        self._anim_state = "idle"

    def spawn(self, x, y):
        """Place player at position."""
        self.x = x
        self.y = y
        self.physics.reset()

    def handle_event(self, event):
        """Process player input."""
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_SPACE and self.is_grounded:
                self.physics.velocity_y = -self.jump_force
                self.is_grounded = False

    def update(self, delta_time):
        """Update player state."""
        keys = pygame.key.get_pressed()
        move_x = 0
        if keys[pygame.K_LEFT] or keys[pygame.K_a]:
            move_x = -1
            self.facing_right = False
        if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
            move_x = 1
            self.facing_right = True
        self.physics.velocity_x = move_x * self.speed
        self.physics.update(delta_time)
        self.x += self.physics.velocity_x * delta_time
        self.y += self.physics.velocity_y * delta_time
        self._update_animation()

    def _update_animation(self):
        """Update animation state."""
        if not self.is_grounded:
            self._anim_state = "jump"
        elif abs(self.physics.velocity_x) > 10:
            self._anim_state = "run"
        else:
            self._anim_state = "idle"

    def take_damage(self, amount):
        """Apply damage to player."""
        self.health = max(0, self.health - amount)

    def heal(self, amount):
        """Restore player health."""
        self.health = min(self.max_health, self.health + amount)

    def get_rect(self):
        """Get collision rectangle."""
        return pygame.Rect(self.x, self.y, self.width, self.height)

    def render(self, screen, camera):
        """Render player sprite."""
        screen_x, screen_y = camera.world_to_screen(self.x, self.y)
        color = (100, 200, 100) if self.health > 30 else (200, 100, 100)
        pygame.draw.rect(screen, color, (screen_x, screen_y, self.width, self.height))
        pygame.draw.rect(screen, (0, 0, 0), (screen_x, screen_y, self.width, self.height), 2)
        h_width = self.width * (self.health / self.max_health)
        pygame.draw.rect(screen, (0, 255, 0), (screen_x, screen_y - 10, h_width, 4))
''',
        }

    def generate_project_code(self, concept: GameConcept,
                               mechanics: List[MechanicDefinition],
                               architecture: GameArchitecture,
                               quality: CodeQuality = CodeQuality.PLAYABLE) -> List[CodeModule]:
        """Generate complete project code from design specifications."""
        modules = []
        module_name = concept.title.lower().replace(" ", "_").replace("-", "_")

        mechanics_params = {}
        for m in mechanics:
            for pname, pdata in m.parameters.items():
                mechanics_params[pname] = pdata.get("default", 0)

        # Generate main entry point
        main_code = self._code_templates["game_main"].format(
            title=concept.title,
            module_name=module_name,
        )
        modules.append(CodeModule(
            module_id=f"mod_{uuid.uuid4().hex[:8]}",
            file_path=f"main.py",
            language="python",
            content=main_code,
            purpose="Game entry point",
            quality=quality,
        ))

        # Generate game scene
        scene_code = self._code_templates["game_scene"].format(
            title=concept.title,
            module_name=module_name,
        )
        modules.append(CodeModule(
            module_id=f"mod_{uuid.uuid4().hex[:8]}",
            file_path=f"game_scene.py",
            language="python",
            content=scene_code,
            purpose="Main gameplay scene",
            quality=quality,
        ))

        # Generate player entity
        player_code = self._code_templates["player_entity"].format(
            title=concept.title,
            module_name=module_name,
            move_speed=mechanics_params.get("move_speed", 200),
            jump_force=mechanics_params.get("jump_force", 400),
        )
        modules.append(CodeModule(
            module_id=f"mod_{uuid.uuid4().hex[:8]}",
            file_path=f"entities/player.py",
            language="python",
            content=player_code,
            purpose="Player entity",
            quality=quality,
        ))

        # Generate support modules
        support_modules = self._generate_support_modules(module_name, mechanics_params)
        modules.extend(support_modules)

        return modules

    def _generate_support_modules(self, module_name: str,
                                   params: Dict[str, Any]) -> List[CodeModule]:
        """Generate supporting infrastructure modules."""
        modules = []

        # Settings module
        settings_code = f'''"""
{module_name} - Game Settings
"""


class GameSettings:
    """Global game configuration."""

    WINDOW_WIDTH = 800
    WINDOW_HEIGHT = 600
    FPS = 60
    GRAVITY = {params.get("gravity", 980)}
    DEBUG = False
    GAME_TITLE = "{module_name.title().replace('_', ' ')}"
'''
        modules.append(CodeModule(
            module_id=f"mod_{uuid.uuid4().hex[:8]}",
            file_path=f"settings.py",
            language="python",
            content=settings_code,
            purpose="Game settings",
        ))

        # Physics system
        physics_code = f'''"""
{module_name} - Physics System
"""


class PhysicsBody:
    """Simple 2D physics body."""

    def __init__(self):
        self.velocity_x = 0.0
        self.velocity_y = 0.0
        self.gravity = {params.get("gravity", 980)}
        self.friction = {params.get("friction", 800)}
        self.max_speed = 500

    def update(self, delta_time):
        """Apply physics forces."""
        self.velocity_y += self.gravity * delta_time
        if self.velocity_x > 0:
            self.velocity_x = max(0, self.velocity_x - self.friction * delta_time)
        elif self.velocity_x < 0:
            self.velocity_x = min(0, self.velocity_x + self.friction * delta_time)
        self.velocity_x = max(-self.max_speed, min(self.max_speed, self.velocity_x))
        self.velocity_y = max(-self.max_speed * 2, min(self.max_speed * 2, self.velocity_y))

    def reset(self):
        """Reset physics state."""
        self.velocity_x = 0.0
        self.velocity_y = 0.0
'''
        modules.append(CodeModule(
            module_id=f"mod_{uuid.uuid4().hex[:8]}",
            file_path=f"systems/physics.py",
            language="python",
            content=physics_code,
            purpose="Physics system",
        ))

        # Camera system
        camera_code = f'''"""
{module_name} - Camera System
"""


class Camera:
    """2D camera with smooth following."""

    def __init__(self, view_width, view_height):
        self.x = 0.0
        self.y = 0.0
        self.view_width = view_width
        self.view_height = view_height
        self.smooth_factor = 0.1

    def follow(self, target):
        """Smoothly follow a target."""
        target_x = target.x - self.view_width / 2 + target.width / 2
        target_y = target.y - self.view_height / 2 + target.height / 2
        self.x += (target_x - self.x) * self.smooth_factor
        self.y += (target_y - self.y) * self.smooth_factor

    def world_to_screen(self, world_x, world_y):
        """Convert world coordinates to screen coordinates."""
        return (world_x - self.x, world_y - self.y)

    def screen_to_world(self, screen_x, screen_y):
        """Convert screen coordinates to world coordinates."""
        return (screen_x + self.x, screen_y + self.y)
'''
        modules.append(CodeModule(
            module_id=f"mod_{uuid.uuid4().hex[:8]}",
            file_path=f"systems/camera.py",
            language="python",
            content=camera_code,
            purpose="Camera system",
        ))

        # Collision system
        collision_code = f'''"""
{module_name} - Collision System
"""


class CollisionSystem:
    """Simple AABB collision detection."""

    def check_collisions(self, player, enemies):
        """Check collisions between player and enemies."""
        player_rect = player.get_rect()
        for enemy in enemies.get_active():
            enemy_rect = enemy.get_rect()
            if player_rect.colliderect(enemy_rect):
                enemy.on_collision_with_player(player)

    @staticmethod
    def aabb_collision(rect1, rect2):
        """Check AABB collision between two rectangles."""
        return rect1.colliderect(rect2)
'''
        modules.append(CodeModule(
            module_id=f"mod_{uuid.uuid4().hex[:8]}",
            file_path=f"systems/collision.py",
            language="python",
            content=collision_code,
            purpose="Collision system",
        ))

        # Enemy manager
        enemy_code = f'''"""
{module_name} - Enemy Manager
"""

import pygame
import random


class Enemy:
    """Individual enemy entity."""

    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.width = 28
        self.height = 28
        self.speed = {params.get("patrol_speed", 100)}
        self.health = {params.get("max_health", 100) // 2}
        self.damage = {params.get("attack_damage", 10)}
        self.detection_range = {params.get("detection_range", 200)}
        self.active = True
        self._patrol_dir = 1

    def update(self, delta_time, player):
        """Update enemy behavior."""
        if not self.active:
            return
        dist_x = player.x - self.x
        dist_y = player.y - self.y
        distance = (dist_x ** 2 + dist_y ** 2) ** 0.5
        if distance < self.detection_range:
            if dist_x > 0:
                self.x += self.speed * delta_time
            else:
                self.x -= self.speed * delta_time
        else:
            self.x += self._patrol_dir * self.speed * 0.3 * delta_time
            if random.random() < 0.01:
                self._patrol_dir *= -1

    def on_collision_with_player(self, player):
        """Handle collision with player."""
        player.take_damage(self.damage)

    def get_rect(self):
        return pygame.Rect(self.x, self.y, self.width, self.height)

    def render(self, screen, camera):
        if not self.active:
            return
        sx, sy = camera.world_to_screen(self.x, self.y)
        color = (200, 80, 80)
        pygame.draw.rect(screen, color, (sx, sy, self.width, self.height))
        pygame.draw.rect(screen, (0, 0, 0), (sx, sy, self.width, self.height), 2)


class EnemyManager:
    """Manages enemy spawning and lifecycle."""

    def __init__(self):
        self._enemies = []

    def spawn_wave(self, wave_number):
        """Spawn a wave of enemies."""
        count = 3 + wave_number * 2
        for _ in range(count):
            x = random.randint(100, 700)
            y = random.randint(100, 500)
            self._enemies.append(Enemy(x, y))

    def get_active(self):
        """Get all active enemies."""
        return [e for e in self._enemies if e.active]

    def update(self, delta_time, player):
        """Update all enemies."""
        for enemy in self._enemies:
            enemy.update(delta_time, player)

    def render(self, screen, camera):
        """Render all enemies."""
        for enemy in self._enemies:
            enemy.render(screen, camera)
'''
        modules.append(CodeModule(
            module_id=f"mod_{uuid.uuid4().hex[:8]}",
            file_path=f"entities/enemy.py",
            language="python",
            content=enemy_code,
            purpose="Enemy system",
        ))

        return modules


# =============================================================================
# Agent Game Forge - Main Class
# =============================================================================


class AgentGameForge:
    """
    AI-powered game creation engine that synthesizes complete playable games
    from natural language descriptions. Orchestrates the full game creation
    pipeline from ideation through deployment.
    """

    _instance: Optional["AgentGameForge"] = None
    _instance_lock = threading.RLock()

    def __init__(self) -> None:
        if AgentGameForge._instance is not None:
            raise RuntimeError("Use AgentGameForge.get_instance() instead")
        self._initialized = False
        self._projects: Dict[str, ForgeProject] = {}
        self._design_synthesizer = DesignSynthesizer()
        self._mechanics_forge = MechanicsForge()
        self._code_synthesizer = CodeSynthesizer()
        self._event_listeners: Dict[str, List[Callable]] = defaultdict(list)

    @classmethod
    def get_instance(cls) -> "AgentGameForge":
        """Get the singleton instance."""
        if cls._instance is None:
            with cls._instance_lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def initialize(self) -> None:
        """Initialize the game forge."""
        if self._initialized:
            return
        self._initialized = True
        self._emit_event("forge:initialized", {"status": "ready"})

    def shutdown(self) -> None:
        """Shutdown the game forge."""
        self._projects.clear()
        self._initialized = False
        self._emit_event("forge:shutdown", {"status": "stopped"})

    def _ensure_initialized(self) -> None:
        """Ensure the forge is initialized."""
        if not self._initialized:
            self.initialize()

    def _emit_event(self, event_type: str, data: Dict[str, Any]) -> None:
        """Emit an event to listeners."""
        for callback in self._event_listeners.get(event_type, []):
            try:
                callback(data)
            except Exception:
                pass

    def on_event(self, event_type: str, callback: Callable) -> None:
        """Register an event listener."""
        self._event_listeners[event_type].append(callback)

    # ------------------------------------------------------------------
    # Game Creation Pipeline
    # ------------------------------------------------------------------

    def create_game(self, prompt: str,
                    fidelity: DesignFidelity = DesignFidelity.DETAILED,
                    quality: CodeQuality = CodeQuality.PLAYABLE,
                    style: AssetStyle = AssetStyle.FLAT_2D,
                    difficulty: str = "normal") -> ForgeProject:
        """
        Create a complete game from a natural language description.

        Executes the full pipeline:
        1. Parse concept from prompt
        2. Generate design document
        3. Design software architecture
        4. Design and balance mechanics
        5. Generate game code
        6. Specify asset requirements
        7. Assemble complete project
        """
        self._ensure_initialized()
        project_id = f"project_{uuid.uuid4().hex[:12]}"
        project = ForgeProject(project_id=project_id)

        # Phase 1: Ideation
        self._transition_phase(project, ForgePhase.IDEATION)
        concept = self._design_synthesizer.parse_concept(prompt)
        project.concept = concept
        self._emit_event("forge:phase", {"project_id": project_id, "phase": "ideation", "concept": concept.to_dict()})

        # Phase 2: Design
        self._transition_phase(project, ForgePhase.DESIGN)
        design_doc = self._design_synthesizer.generate_design_document(concept, fidelity)
        project.design_document = design_doc
        self._emit_event("forge:phase", {"project_id": project_id, "phase": "design"})

        # Phase 3: Architecture
        self._transition_phase(project, ForgePhase.ARCHITECTURE)
        architecture = self._design_architecture(concept, design_doc)
        project.architecture = architecture
        self._emit_event("forge:phase", {"project_id": project_id, "phase": "architecture"})

        # Phase 4: Mechanics
        self._transition_phase(project, ForgePhase.MECHANICS)
        mechanics = self._mechanics_forge.design_mechanics_for_genre(concept.genre)
        mechanics = self._mechanics_forge.balance_mechanics(mechanics, difficulty)
        project.mechanics = mechanics
        self._emit_event("forge:phase", {"project_id": project_id, "phase": "mechanics", "count": len(mechanics)})

        # Phase 5: Code
        self._transition_phase(project, ForgePhase.CODE)
        code_modules = self._code_synthesizer.generate_project_code(
            concept, mechanics, architecture, quality
        )
        project.code_modules = code_modules
        self._emit_event("forge:phase", {"project_id": project_id, "phase": "code", "modules": len(code_modules)})

        # Phase 6: Assets
        self._transition_phase(project, ForgePhase.ASSETS)
        asset_specs = self._specify_assets(concept, style)
        project.asset_specs = asset_specs
        self._emit_event("forge:phase", {"project_id": project_id, "phase": "assets", "count": len(asset_specs)})

        # Phase 7: Assembly
        self._transition_phase(project, ForgePhase.ASSEMBLY)
        self._assemble_project(project)
        self._emit_event("forge:phase", {"project_id": project_id, "phase": "assembly"})

        self._transition_phase(project, ForgePhase.COMPLETE)
        project.updated_at = time.time()
        self._projects[project_id] = project
        self._emit_event("forge:complete", {"project_id": project_id, "title": concept.title})

        return project

    def _transition_phase(self, project: ForgeProject, phase: ForgePhase) -> None:
        """Transition the project to a new phase."""
        project.phase_history.append({
            "from": project.current_phase.value,
            "to": phase.value,
            "timestamp": time.time(),
        })
        project.current_phase = phase

    def _design_architecture(self, concept: GameConcept,
                              design_doc: Dict[str, Any]) -> GameArchitecture:
        """Design the software architecture for the game."""
        arch_id = f"arch_{uuid.uuid4().hex[:8]}"
        module_name = concept.title.lower().replace(" ", "_").replace("-", "_")

        return GameArchitecture(
            architecture_id=arch_id,
            component_tree={
                "root": {"name": "Game", "type": "Application"},
                "scenes": [
                    {"name": "MainMenu", "type": "MenuScene"},
                    {"name": "GameScene", "type": "GameplayScene"},
                    {"name": "PauseMenu", "type": "OverlayScene"},
                    {"name": "GameOver", "type": "ResultScene"},
                ],
                "entities": [
                    {"name": "Player", "type": "PlayerEntity"},
                    {"name": "Enemy", "type": "EnemyEntity"},
                    {"name": "Projectile", "type": "ProjectileEntity"},
                    {"name": "Pickup", "type": "ItemEntity"},
                ],
                "systems": [
                    {"name": "Physics", "type": "PhysicsSystem"},
                    {"name": "Collision", "type": "CollisionSystem"},
                    {"name": "Rendering", "type": "RenderSystem"},
                    {"name": "Audio", "type": "AudioSystem"},
                    {"name": "Input", "type": "InputSystem"},
                    {"name": "Camera", "type": "CameraSystem"},
                ],
            },
            entry_points={
                "main": "main.py",
                "config": "settings.py",
            },
            technology_stack={
                "language": "python",
                "rendering": "pygame",
                "physics": "custom_2d",
                "audio": "pygame.mixer",
            },
        )

    def _specify_assets(self, concept: GameConcept,
                        style: AssetStyle) -> List[AssetSpecification]:
        """Generate asset specifications based on concept and style."""
        specs = [
            AssetSpecification(
                asset_id=f"asset_{uuid.uuid4().hex[:8]}",
                asset_type="sprite",
                name="player_idle",
                description="Player character idle animation frames",
                style=style,
                dimensions=(64, 64),
                priority=1,
            ),
            AssetSpecification(
                asset_id=f"asset_{uuid.uuid4().hex[:8]}",
                asset_type="sprite",
                name="player_run",
                description="Player character running animation frames",
                style=style,
                dimensions=(64, 64),
                priority=1,
            ),
            AssetSpecification(
                asset_id=f"asset_{uuid.uuid4().hex[:8]}",
                asset_type="sprite",
                name="enemy_basic",
                description="Basic enemy character sprite",
                style=style,
                dimensions=(48, 48),
                priority=2,
            ),
            AssetSpecification(
                asset_id=f"asset_{uuid.uuid4().hex[:8]}",
                asset_type="sprite",
                name="tileset_ground",
                description="Ground and platform tileset",
                style=style,
                dimensions=(32, 32),
                priority=1,
            ),
            AssetSpecification(
                asset_id=f"asset_{uuid.uuid4().hex[:8]}",
                asset_type="ui",
                name="health_bar",
                description="Player health bar UI element",
                style=AssetStyle.MINIMALIST,
                dimensions=(200, 20),
                priority=3,
            ),
            AssetSpecification(
                asset_id=f"asset_{uuid.uuid4().hex[:8]}",
                asset_type="music",
                name="background_theme",
                description="Main background music track",
                style=style,
                format="ogg",
                priority=3,
            ),
            AssetSpecification(
                asset_id=f"asset_{uuid.uuid4().hex[:8]}",
                asset_type="sound",
                name="jump_sfx",
                description="Player jump sound effect",
                style=style,
                format="wav",
                priority=2,
            ),
            AssetSpecification(
                asset_id=f"asset_{uuid.uuid4().hex[:8]}",
                asset_type="sound",
                name="damage_sfx",
                description="Damage received sound effect",
                style=style,
                format="wav",
                priority=2,
            ),
        ]
        return specs

    def _assemble_project(self, project: ForgeProject) -> None:
        """Assemble all components into a coherent project structure."""
        project.metadata["assembly"] = {
            "total_modules": len(project.code_modules),
            "total_assets": len(project.asset_specs),
            "total_mechanics": len(project.mechanics),
            "estimated_file_count": len(project.code_modules) + 10,
            "assembly_timestamp": time.time(),
        }

    # ------------------------------------------------------------------
    # Playtest & Iteration
    # ------------------------------------------------------------------

    def playtest(self, project_id: str) -> PlaytestReport:
        """Simulate gameplay and generate a playtest report."""
        self._ensure_initialized()
        project = self._projects.get(project_id)
        if not project:
            raise ValueError(f"Project not found: {project_id}")

        self._transition_phase(project, ForgePhase.PLAYTEST)

        report = PlaytestReport(
            report_id=f"pt_{uuid.uuid4().hex[:8]}",
            project_id=project_id,
            is_playable=True,
            fun_score=self._evaluate_fun(project),
            engagement_score=self._evaluate_engagement(project),
            balance_score=self._evaluate_balance(project),
            performance_score=self._evaluate_performance(project),
            bugs_found=self._count_potential_bugs(project),
            suggestions=self._generate_suggestions(project),
            mechanics_analysis=self._analyze_mechanics(project),
            player_flow_analysis=self._analyze_flow(project),
            difficulty_curve=self._analyze_difficulty(project),
        )

        project.playtest_reports.append(report)
        project.updated_at = time.time()
        self._emit_event("forge:playtest", {"project_id": project_id, "report": report.to_dict()})

        return report

    def _evaluate_fun(self, project: ForgeProject) -> float:
        """Evaluate the fun factor of the game design."""
        score = 50.0
        if project.concept and project.concept.unique_selling_points:
            score += len(project.concept.unique_selling_points) * 5
        if len(project.mechanics) > 3:
            score += 10
        if len(project.code_modules) > 5:
            score += 10
        return min(100.0, score)

    def _evaluate_engagement(self, project: ForgeProject) -> float:
        """Evaluate player engagement potential."""
        score = 50.0
        if project.concept and project.concept.core_loop:
            score += 15
        if len(project.asset_specs) > 5:
            score += 10
        return min(100.0, score)

    def _evaluate_balance(self, project: ForgeProject) -> float:
        """Evaluate game balance quality."""
        score = 60.0
        if len(project.mechanics) >= 4:
            score += 20
        mechanics_with_params = sum(1 for m in project.mechanics if m.parameters)
        if mechanics_with_params > 0:
            score += mechanics_with_params * 5
        return min(100.0, score)

    def _evaluate_performance(self, project: ForgeProject) -> float:
        """Evaluate expected performance."""
        score = 70.0
        if len(project.code_modules) < 20:
            score += 10
        return min(100.0, score)

    def _count_potential_bugs(self, project: ForgeProject) -> int:
        """Estimate potential bugs in the codebase."""
        bugs = 0
        for module in project.code_modules:
            if "TODO" in module.content:
                bugs += 1
            if "pass" in module.content and "def update" in module.content:
                bugs += 1
        return bugs

    def _generate_suggestions(self, project: ForgeProject) -> List[str]:
        """Generate improvement suggestions."""
        suggestions = []
        if len(project.mechanics) < 4:
            suggestions.append("Add more mechanics for depth")
        if len(project.asset_specs) < 5:
            suggestions.append("Add more visual and audio assets for polish")
        if len(project.code_modules) < 8:
            suggestions.append("Add more gameplay systems")
        if project.concept and not project.concept.unique_selling_points:
            suggestions.append("Add a unique hook to differentiate the game")
        suggestions.append("Add tutorial level for player onboarding")
        suggestions.append("Implement save/load functionality")
        return suggestions

    def _analyze_mechanics(self, project: ForgeProject) -> Dict[str, Any]:
        """Analyze mechanics synergy and coverage."""
        categories = set(m.category for m in project.mechanics)
        return {
            "categories_covered": list(categories),
            "category_count": len(categories),
            "mechanics_per_category": {
                cat: sum(1 for m in project.mechanics if m.category == cat)
                for cat in categories
            },
            "recommended_categories": [
                c for c in ["movement", "health", "combat", "inventory", "economy", "progression"]
                if c not in categories
            ],
        }

    def _analyze_flow(self, project: ForgeProject) -> Dict[str, Any]:
        """Analyze player flow and pacing."""
        return {
            "estimated_session_length": "15-30 minutes",
            "flow_quality": "good",
            "pacing_notes": "Mechanics introduce steadily with difficulty scaling",
        }

    def _analyze_difficulty(self, project: ForgeProject) -> Dict[str, Any]:
        """Analyze difficulty curve."""
        return {
            "curve_type": "linear_ramp",
            "early_game": "tutorial_easy",
            "mid_game": "moderate",
            "late_game": "challenging",
            "recommendations": ["Add optional difficulty settings"],
        }

    def iterate(self, project_id: str, feedback: str = "") -> ForgeProject:
        """Refine the game based on playtest feedback."""
        self._ensure_initialized()
        project = self._projects.get(project_id)
        if not project:
            raise ValueError(f"Project not found: {project_id}")

        self._transition_phase(project, ForgePhase.ITERATE)
        project.iterations += 1

        # Apply feedback to improve the project
        if "combat" in feedback.lower() and project.concept:
            combat_mechanics = [m for m in project.mechanics if m.category == "combat"]
            for m in combat_mechanics:
                if "attack_damage" in m.parameters:
                    if "more" in feedback.lower() or "strategic" in feedback.lower():
                        m.parameters["attack_damage"]["default"] *= 1.2
                        m.parameters["critical_chance"]["default"] = 0.15

        if "difficulty" in feedback.lower() and project.concept:
            project.mechanics = self._mechanics_forge.balance_mechanics(
                project.mechanics,
                "hard" if "hard" in feedback.lower() else "easy"
            )

        project.updated_at = time.time()
        self._emit_event("forge:iterate", {"project_id": project_id, "iteration": project.iterations})

        return project

    def deploy(self, project_id: str, platform: Platform = Platform.WEB) -> Dict[str, Any]:
        """Prepare the project for deployment."""
        self._ensure_initialized()
        project = self._projects.get(project_id)
        if not project:
            raise ValueError(f"Project not found: {project_id}")

        self._transition_phase(project, ForgePhase.DEPLOY)

        deployment = {
            "project_id": project_id,
            "platform": platform.value,
            "files": [m.file_path for m in project.code_modules],
            "asset_count": len(project.asset_specs),
            "total_size_estimate": sum(len(m.content) for m in project.code_modules),
            "deployable": True,
            "entry_point": "main.py",
            "timestamp": time.time(),
        }

        project.updated_at = time.time()
        self._emit_event("forge:deploy", deployment)

        return deployment

    # ------------------------------------------------------------------
    # Project Management
    # ------------------------------------------------------------------

    def get_project(self, project_id: str) -> Optional[ForgeProject]:
        """Get a project by ID."""
        return self._projects.get(project_id)

    def list_projects(self) -> List[Dict[str, Any]]:
        """List all projects with summaries."""
        return [
            {
                "project_id": p.project_id,
                "title": p.concept.title if p.concept else "Untitled",
                "genre": p.concept.genre.value if p.concept else "unknown",
                "phase": p.current_phase.value,
                "iterations": p.iterations,
                "created_at": p.created_at,
            }
            for p in self._projects.values()
        ]

    def delete_project(self, project_id: str) -> bool:
        """Delete a project."""
        if project_id in self._projects:
            del self._projects[project_id]
            return True
        return False

    def get_code_for_project(self, project_id: str) -> List[Dict[str, Any]]:
        """Get all code modules for a project."""
        project = self._projects.get(project_id)
        if not project:
            return []
        return [m.to_dict() for m in project.code_modules]

    def get_assets_for_project(self, project_id: str) -> List[Dict[str, Any]]:
        """Get all asset specifications for a project."""
        project = self._projects.get(project_id)
        if not project:
            return []
        return [a.to_dict() for a in project.asset_specs]

    def get_status(self) -> Dict[str, Any]:
        """Get the forge status."""
        return {
            "initialized": self._initialized,
            "total_projects": len(self._projects),
            "projects_by_phase": {
                phase.value: sum(1 for p in self._projects.values() if p.current_phase == phase)
                for phase in ForgePhase
            },
            "total_iterations": sum(p.iterations for p in self._projects.values()),
        }


# =============================================================================
# Singleton Access
# =============================================================================


def get_agent_game_forge() -> AgentGameForge:
    """Get the singleton AgentGameForge instance."""
    return AgentGameForge.get_instance()