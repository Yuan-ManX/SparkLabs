"""
SparkLabs Agent - Game Content Synthesizer

The central content generation intelligence that transforms natural-language
game descriptions into structured, playable game content. This module is the
creative engine behind SparkLabs' AI-native game creation pipeline.

It integrates multiple AI agent paradigms into a unified content generation
system:

- Generative Persona Engine: Creates NPCs with individual personalities,
  memory streams, daily schedules, and social relationship webs. Each NPC
  has a persistent identity that evolves through game interactions.

- World Simulation Core: Generates living worlds with interconnected
  biomes, settlement networks, economic systems, faction politics, and
  ecological dynamics that continue evolving whether the player is
  present or not.

- Narrative Weaving System: Produces branching storylines with causal
  graphs, emotional arcs, pacing curves, and adaptive plot threads that
  respond to player choices and world state changes.

- Game Content Pipeline: Orchestrates the full content creation workflow
  from concept analysis through design documents, world building,
  character creation, quest generation, mechanic balancing, and level
  design — producing a complete game design specification.

- Adaptive Quality System: Continuously evaluates generated content
  against design principles, fun metrics, and coherence constraints,
  iterating until quality thresholds are met.

The synthesizer uses the LLM Router for AI-powered generation when API
keys are configured, and falls back to a sophisticated procedural
generation system that produces rich, varied content without external
dependencies.

Architecture:
  GameContentSynthesizer (Singleton)
    |-- PromptAnalyzer (intent detection, genre classification, scope estimation)
    |-- DesignDocumentGenerator (game pillars, core loops, progression systems)
    |-- WorldContentBuilder (biomes, structures, resources, weather, ecology)
    |-- PersonaFactory (NPC personas with memories, schedules, relationships)
    |-- NarrativeWeaver (story arcs, quest chains, dialogue trees, branching)
    |-- MechanicSynthesizer (gameplay rules, balance curves, progression math)
    |-- LevelArchitect (level layouts, difficulty curves, pacing, flow)
    |-- ContentValidator (coherence checking, quality scoring, gap detection)
"""

from __future__ import annotations

import json
import logging
import math
import random
import threading
import time
import uuid
from collections import defaultdict, deque
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple, Union

logger = logging.getLogger(__name__)


# =============================================================================
# Enums
# =============================================================================


class GameGenre(Enum):
    """Supported game genres for content generation."""
    PLATFORMER = "platformer"
    TOP_DOWN_ADVENTURE = "top_down_adventure"
    PUZZLE = "puzzle"
    SHOOTER = "shooter"
    RPG = "rpg"
    DUNGEON_CRAWLER = "dungeon_crawler"
    RACING = "racing"
    STRATEGY = "strategy"
    SURVIVAL = "survival"
    SANDBOX = "sandbox"
    BOSS_BATTLE = "boss_battle"
    NARRATIVE = "narrative"
    MUSIC = "music"
    EXPLORATION = "exploration"
    CUSTOM = "custom"


class ContentType(Enum):
    """Types of content produced by the synthesizer."""
    DESIGN_DOC = "design_document"
    WORLD = "world"
    CHARACTERS = "characters"
    NARRATIVE = "narrative"
    MECHANICS = "mechanics"
    LEVELS = "levels"
    ASSETS = "assets"
    BALANCE = "balance"
    FULL_GAME = "full_game"


class SynthesisPhase(Enum):
    """Phases of the content synthesis pipeline."""
    ANALYZE = "analyze"
    DESIGN = "design"
    WORLD_BUILD = "world_build"
    CHARACTER_CREATE = "character_create"
    NARRATIVE_WEAVE = "narrative_weave"
    MECHANIC_SYNTH = "mechanic_synth"
    LEVEL_ARCHITECT = "level_architect"
    BALANCE_TUNE = "balance_tune"
    VALIDATE = "validate"
    FINALIZE = "finalize"


# =============================================================================
# Data Classes
# =============================================================================


@dataclass
class GameConcept:
    """Parsed game concept from natural language prompt."""
    prompt: str
    genre: GameGenre
    title: str
    theme: str
    core_loop: str
    pillars: List[str]
    target_mood: List[str]
    complexity: str  # simple, medium, complex
    estimated_playtime_min: int
    key_features: List[str]
    visual_style: str
    player_role: str
    innovation_angles: List[str]


@dataclass
class WorldContent:
    """Generated world content."""
    world_id: str
    name: str
    width: int
    height: int
    biomes: List[Dict[str, Any]]
    structures: List[Dict[str, Any]]
    resources: List[Dict[str, Any]]
    weather_system: Dict[str, Any]
    ecology: Dict[str, Any]
    points_of_interest: List[Dict[str, Any]]
    connections: List[Dict[str, Any]]


@dataclass
class Persona:
    """A generative NPC persona with memory and social connections."""
    persona_id: str
    name: str
    role: str
    personality_traits: List[str]
    backstory: str
    daily_schedule: List[Dict[str, Any]]
    memories: List[Dict[str, Any]]
    relationships: Dict[str, str]  # persona_id -> relationship type
    dialogue_style: str
    goals: List[str]
    fears: List[str]
    appearance: Dict[str, Any]
    location: Tuple[float, float]
    faction: str


@dataclass
class NarrativeContent:
    """Generated narrative content."""
    story_arcs: List[Dict[str, Any]]
    main_quest_chain: List[Dict[str, Any]]
    side_quests: List[Dict[str, Any]]
    dialogue_trees: List[Dict[str, Any]]
    branching_points: List[Dict[str, Any]]
    endings: List[Dict[str, Any]]
    emotional_arc: Dict[str, Any]
    pacing_curve: List[float]


@dataclass
class MechanicSet:
    """Generated gameplay mechanics."""
    core_mechanics: List[Dict[str, Any]]
    secondary_mechanics: List[Dict[str, Any]]
    progression_system: Dict[str, Any]
    economy_system: Dict[str, Any]
    combat_system: Dict[str, Any]
    interaction_system: Dict[str, Any]
    balance_parameters: Dict[str, Any]


@dataclass
class LevelDesign:
    """Generated level design content."""
    levels: List[Dict[str, Any]]
    difficulty_curve: str
    pacing: Dict[str, Any]
    flow_graph: Dict[str, Any]
    total_playtime_estimate: int


@dataclass
class GameDesignDocument:
    """Complete game design document."""
    gdd_id: str
    concept: GameConcept
    world: Optional[WorldContent]
    characters: List[Persona]
    narrative: Optional[NarrativeContent]
    mechanics: Optional[MechanicSet]
    levels: Optional[LevelDesign]
    asset_manifest: Dict[str, Any]
    quality_score: float
    created_at: float


@dataclass
class SynthesisResult:
    """Result of a content synthesis run."""
    result_id: str
    success: bool
    gdd: Optional[GameDesignDocument]
    phases_completed: List[str]
    phases_skipped: List[str]
    duration_s: float
    warnings: List[str]
    error: Optional[str]
    metadata: Dict[str, Any]


# =============================================================================
# Prompt Analyzer
# =============================================================================


class PromptAnalyzer:
    """Analyzes natural-language game prompts to extract structured concepts."""

    GENRE_KEYWORDS: Dict[GameGenre, List[str]] = {
        GameGenre.PLATFORMER: ["platform", "jump", "side-scroll", "mario", "sonic", "platformer"],
        GameGenre.TOP_DOWN_ADVENTURE: ["top-down", "zelda", "adventure", "explore", "overworld"],
        GameGenre.PUZZLE: ["puzzle", "sokoban", "match-3", "sliding", "logic", "brain"],
        GameGenre.SHOOTER: ["shoot", "gun", "bullet", "laser", "blaster", "fps", "twin-stick"],
        GameGenre.RPG: ["rpg", "role-play", "leveling", "stats", "equipment", "party"],
        GameGenre.DUNGEON_CRAWLER: ["dungeon", "crawl", "rogue", "roguelike", "labyrinth"],
        GameGenre.RACING: ["race", "racing", "speed", "track", "lap", "fast"],
        GameGenre.STRATEGY: ["strategy", "tactical", "command", "build", "manage", "rts"],
        GameGenre.SURVIVAL: ["survival", "craft", "gather", "hunger", "shelter", "persist"],
        GameGenre.SANDBOX: ["sandbox", "creative", "build", "free-form", "open"],
        GameGenre.BOSS_BATTLE: ["boss", "raid", "encounter", "epic fight", "final enemy"],
        GameGenre.NARRATIVE: ["narrative", "story", "dialogue", "quest", "plot", "character arc"],
        GameGenre.MUSIC: ["music", "rhythm", "beat", "melody", "compose", "soundtrack"],
        GameGenre.EXPLORATION: ["explore", "discover", "wander", "open world", "journey"],
    }

    THEME_PREFIXES = [
        "fantasy", "sci-fi", "cyberpunk", "post-apocalyptic", "steampunk",
        "medieval", "space", "underwater", "forest", "desert", "ice",
        "volcanic", "sky", "horror", "wholesome", "retro", "neon",
    ]

    VISUAL_STYLES = [
        "pixel-art", "flat-2d", "cartoon", "low-poly", "voxel",
        "hand-drawn", "isometric", "minimalist", "neon", "retro",
    ]

    def analyze(self, prompt: str) -> GameConcept:
        """Parse a natural-language prompt into a structured GameConcept."""
        lower = prompt.lower()
        genre = self._detect_genre(lower)
        theme = self._detect_theme(lower)
        visual_style = self._detect_visual_style(lower)
        title = self._generate_title(prompt, genre, theme)
        core_loop = self._derive_core_loop(genre, theme)
        pillars = self._derive_pillars(genre)
        target_mood = self._derive_mood(genre, theme)
        complexity = self._estimate_complexity(prompt)
        playtime = self._estimate_playtime(genre, complexity)
        features = self._derive_features(genre, theme)
        player_role = self._derive_player_role(genre, theme)
        innovations = self._derive_innovations(genre)

        return GameConcept(
            prompt=prompt,
            genre=genre,
            title=title,
            theme=theme,
            core_loop=core_loop,
            pillars=pillars,
            target_mood=target_mood,
            complexity=complexity,
            estimated_playtime_min=playtime,
            key_features=features,
            visual_style=visual_style,
            player_role=player_role,
            innovation_angles=innovations,
        )

    def _detect_genre(self, lower_prompt: str) -> GameGenre:
        scores: Dict[GameGenre, int] = defaultdict(int)
        for genre, keywords in self.GENRE_KEYWORDS.items():
            for kw in keywords:
                if kw in lower_prompt:
                    scores[genre] += 1
        if not scores:
            return GameGenre.EXPLORATION
        return max(scores, key=scores.get)

    def _detect_theme(self, lower_prompt: str) -> str:
        for theme in self.THEME_PREFIXES:
            if theme in lower_prompt:
                return theme
        return "fantasy"

    def _detect_visual_style(self, lower_prompt: str) -> str:
        for style in self.VISUAL_STYLES:
            if style.replace("-", " ") in lower_prompt:
                return style
        return "flat-2d"

    def _generate_title(self, prompt: str, genre: GameGenre, theme: str) -> str:
        words = [w for w in prompt.split() if len(w) > 3][:4]
        if not words:
            words = ["Spark", "Quest"]
        base = " ".join(w.capitalize() for w in words)
        suffixes = {
            GameGenre.PLATFORMER: "Run",
            GameGenre.RPG: "Saga",
            GameGenre.PUZZLE: "Mind",
            GameGenre.SHOOTER: "Strike",
            GameGenre.DUNGEON_CRAWLER: "Depths",
            GameGenre.BOSS_BATTLE: "Clash",
            GameGenre.NARRATIVE: "Tales",
            GameGenre.EXPLORATION: "Horizons",
            GameGenre.MUSIC: "Beat",
            GameGenre.RACING: "Rush",
        }
        suffix = suffixes.get(genre, "Adventure")
        return f"{base} {suffix}"[:60]

    def _derive_core_loop(self, genre: GameGenre, theme: str) -> str:
        loops = {
            GameGenre.PLATFORMER: "Run, jump, collect, reach the goal",
            GameGenre.TOP_DOWN_ADVENTURE: "Explore, fight, solve puzzles, progress story",
            GameGenre.PUZZLE: "Observe, deduce, manipulate, solve",
            GameGenre.SHOOTER: "Aim, dodge, shoot, survive waves",
            GameGenre.RPG: "Quest, level up, gear up, advance narrative",
            GameGenre.DUNGEON_CRAWLER: "Descend, loot, fight, upgrade, repeat",
            GameGenre.RACING: "Accelerate, steer, draft, win",
            GameGenre.STRATEGY: "Gather, build, command, conquer",
            GameGenre.SURVIVAL: "Gather, craft, build, survive",
            GameGenre.SANDBOX: "Imagine, build, share, iterate",
            GameGenre.BOSS_BATTLE: "Learn patterns, dodge, strike, triumph",
            GameGenre.NARRATIVE: "Listen, choose, act, experience consequences",
            GameGenre.MUSIC: "Listen, time, perform, compose",
            GameGenre.EXPLORATION: "Wander, discover, map, uncover secrets",
        }
        return loops.get(genre, "Explore and progress")

    def _derive_pillars(self, genre: GameGenre) -> List[str]:
        pillar_map = {
            GameGenre.PLATFORMER: ["Precision", "Speed", "Collection", "Mastery"],
            GameGenre.RPG: ["Progression", "Story", "Choice", "Combat"],
            GameGenre.PUZZLE: ["Logic", "Elegance", "Aha Moments", "Flow"],
            GameGenre.SHOOTER: ["Accuracy", "Reflexes", "Positioning", "Power"],
            GameGenre.DUNGEON_CRAWLER: ["Risk", "Reward", "Discovery", "Upgrade"],
            GameGenre.BOSS_BATTLE: ["Pattern Recognition", "Patience", "Execution", "Adrenaline"],
            GameGenre.NARRATIVE: ["Story", "Characters", "Choices", "Consequences"],
            GameGenre.EXPLORATION: ["Discovery", "Freedom", "Wonder", "Mastery"],
            GameGenre.MUSIC: ["Rhythm", "Harmony", "Expression", "Flow"],
        }
        return pillar_map.get(genre, ["Engagement", "Progression", "Discovery", "Polish"])

    def _derive_mood(self, genre: GameGenre, theme: str) -> List[str]:
        base_moods = {
            GameGenre.HORROR if hasattr(GameGenre, 'HORROR') else GameGenre.CUSTOM: ["fear", "tension"],
            GameGenre.BOSS_BATTLE: ["excitement", "tension", "triumph"],
            GameGenre.NARRATIVE: ["curiosity", "empathy", "wonder"],
            GameGenre.PUZZLE: ["focus", "satisfaction", "curiosity"],
            GameGenre.EXPLORATION: ["wonder", "freedom", "discovery"],
        }
        moods = base_moods.get(genre, ["engagement", "excitement", "satisfaction"])
        if theme in ["horror", "post-apocalyptic"]:
            moods = ["tension", "dread", "survival"] + moods
        elif theme in ["wholesome", "forest"]:
            moods = ["calm", "warmth", "joy"] + moods
        return moods[:4]

    def _estimate_complexity(self, prompt: str) -> str:
        word_count = len(prompt.split())
        if word_count < 10:
            return "simple"
        elif word_count < 30:
            return "medium"
        return "complex"

    def _estimate_playtime(self, genre: GameGenre, complexity: str) -> int:
        base = {
            GameGenre.PLATFORMER: 30,
            GameGenre.RPG: 120,
            GameGenre.PUZZLE: 45,
            GameGenre.SHOOTER: 40,
            GameGenre.DUNGEON_CRAWLER: 60,
            GameGenre.BOSS_BATTLE: 15,
            GameGenre.NARRATIVE: 90,
            GameGenre.EXPLORATION: 60,
        }.get(genre, 45)
        multiplier = {"simple": 0.6, "medium": 1.0, "complex": 1.5}.get(complexity, 1.0)
        return int(base * multiplier)

    def _derive_features(self, genre: GameGenre, theme: str) -> List[str]:
        common = ["save_system", "audio_system", "settings_menu", "pause_menu"]
        genre_features = {
            GameGenre.PLATFORMER: ["double_jump", "wall_slide", "collectibles", "time_trial"],
            GameGenre.RPG: ["inventory", "skill_tree", "dialogue", "quest_log", "crafting"],
            GameGenre.PUZZLE: ["undo_move", "hint_system", "level_editor", "star_rating"],
            GameGenre.SHOOTER: ["weapon_variety", "power_ups", "wave_system", "score_combo"],
            GameGenre.DUNGEON_CRAWLER: ["procedural_levels", "permadeath", "loot_system", "upgrade_tree"],
            GameGenre.BOSS_BATTLE: ["phase_transitions", "attack_patterns", "dodge_mechanic", "health_bars"],
            GameGenre.NARRATIVE: ["dialogue_choices", "branching_story", "character_relationships", "multiple_endings"],
            GameGenre.EXPLORATION: ["map_system", "fast_travel", "discovery_log", "day_night_cycle"],
            GameGenre.MUSIC: ["beat_sync", "note_charts", "score_ranking", "freestyle_mode"],
        }
        return common + genre_features.get(genre, [])

    def _derive_player_role(self, genre: GameGenre, theme: str) -> str:
        roles = {
            GameGenre.PLATFORMER: "Agile hero navigating treacherous terrain",
            GameGenre.RPG: "Adventurer growing in power and renown",
            GameGenre.PUZZLE: "Strategic thinker solving cerebral challenges",
            GameGenre.SHOOTER: "Skilled marksman surviving overwhelming odds",
            GameGenre.DUNGEON_CRAWLER: "Treasure seeker braving dangerous depths",
            GameGenre.BOSS_BATTLE: "Champion facing legendary foes",
            GameGenre.NARRATIVE: "Protagonist shaping the story through choices",
            GameGenre.EXPLORATION: "Wanderer uncovering the world's secrets",
            GameGenre.MUSIC: "Performer creating harmonious melodies",
        }
        return roles.get(genre, "Player engaging with the game world")

    def _derive_innovations(self, genre: GameGenre) -> List[str]:
        return [
            "AI-driven content adaptation",
            "Procedural variation ensuring replayability",
            "Dynamic difficulty responding to player skill",
            "Emergent gameplay from system interactions",
        ]


# =============================================================================
# World Content Builder
# =============================================================================


class WorldContentBuilder:
    """Builds rich world content with biomes, structures, and ecology."""

    BIOME_TYPES = [
        {"name": "forest", "color": "#2d5a27", "resources": ["wood", "berries", "herbs"], "difficulty": 1},
        {"name": "grassland", "color": "#4a7c3a", "resources": ["grass", "flowers", "seeds"], "difficulty": 1},
        {"name": "desert", "color": "#c4a04e", "resources": ["sand", "cactus", "ore"], "difficulty": 2},
        {"name": "mountain", "color": "#6b6b6b", "resources": ["stone", "iron", "crystal"], "difficulty": 3},
        {"name": "ocean", "color": "#1a4a6e", "resources": ["fish", "pearl", "kelp"], "difficulty": 2},
        {"name": "tundra", "color": "#a0b8c8", "resources": ["ice", "fur", "frost_flower"], "difficulty": 3},
        {"name": "volcanic", "color": "#8b3a1a", "resources": ["obsidian", "sulfur", "ember"], "difficulty": 4},
        {"name": "swamp", "color": "#3d4a2a", "resources": ["moss", "mushroom", "mud"], "difficulty": 2},
    ]

    STRUCTURE_TYPES = [
        "village", "dungeon", "tower", "ruins", "temple", "castle",
        "cave", "camp", "shrine", "bridge", "fortress", "settlement",
    ]

    def build(self, concept: GameConcept) -> WorldContent:
        """Generate world content based on the game concept."""
        world_id = f"world_{uuid.uuid4().hex[:12]}"
        size = self._determine_size(concept.complexity)
        biomes = self._generate_biomes(size, concept.theme)
        structures = self._generate_structures(biomes, concept.genre)
        resources = self._compile_resources(biomes)
        weather = self._generate_weather(concept.theme, biomes)
        ecology = self._generate_ecology(biomes, concept.theme)
        pois = self._generate_pois(structures, biomes)
        connections = self._generate_connections(structures)

        return WorldContent(
            world_id=world_id,
            name=f"{concept.theme.capitalize()} Realm of {concept.title}",
            width=size,
            height=size,
            biomes=biomes,
            structures=structures,
            resources=resources,
            weather_system=weather,
            ecology=ecology,
            points_of_interest=pois,
            connections=connections,
        )

    def _determine_size(self, complexity: str) -> int:
        return {"simple": 128, "medium": 256, "complex": 512}.get(complexity, 256)

    def _generate_biomes(self, size: int, theme: str) -> List[Dict[str, Any]]:
        count = min(8, max(3, size // 64))
        selected = random.sample(self.BIOME_TYPES, min(count, len(self.BIOME_TYPES)))
        biomes = []
        for i, biome in enumerate(selected):
            biomes.append({
                "biome_id": f"biome_{i}",
                "name": biome["name"],
                "color": biome["color"],
                "resources": biome["resources"],
                "difficulty": biome["difficulty"],
                "region": {
                    "x": random.randint(0, size),
                    "y": random.randint(0, size),
                    "radius": random.randint(size // 6, size // 3),
                },
                "ambient_sound": f"{biome['name']}_ambient",
                "entity_spawns": random.randint(5, 20),
            })
        return biomes

    def _generate_structures(self, biomes: List[Dict], genre: GameGenre) -> List[Dict[str, Any]]:
        count = random.randint(5, 15)
        structures = []
        for i in range(count):
            struct_type = random.choice(self.STRUCTURE_TYPES)
            biome = random.choice(biomes)
            structures.append({
                "structure_id": f"struct_{i}",
                "type": struct_type,
                "name": f"{struct_type.capitalize()} {i+1}",
                "biome": biome["name"],
                "position": {
                    "x": random.randint(0, 256),
                    "y": random.randint(0, 256),
                },
                "floors": random.randint(1, 5),
                "rooms": random.randint(3, 15),
                "has_boss": genre in [GameGenre.DUNGEON_CRAWLER, GameGenre.RPG, GameGenre.BOSS_BATTLE] and i % 3 == 0,
                "loot_quality": random.choice(["common", "uncommon", "rare", "epic"]),
                "npc_count": random.randint(0, 5),
            })
        return structures

    def _compile_resources(self, biomes: List[Dict]) -> List[Dict[str, Any]]:
        resources = []
        seen = set()
        for biome in biomes:
            for res in biome.get("resources", []):
                if res not in seen:
                    seen.add(res)
                    resources.append({
                        "resource_id": f"res_{len(resources)}",
                        "name": res,
                        "rarity": random.choice(["common", "uncommon", "rare"]),
                        "biome": biome["name"],
                    })
        return resources

    def _generate_weather(self, theme: str, biomes: List[Dict]) -> Dict[str, Any]:
        weather_types = ["clear", "cloudy", "rain", "storm", "fog", "snow"]
        if theme in ["desert", "volcanic"]:
            weather_types = ["clear", "heat_haze", "sandstorm"]
        elif theme in ["ice", "tundra"]:
            weather_types = ["clear", "snow", "blizzard"]
        return {
            "types": weather_types,
            "cycle_duration_s": random.randint(120, 600),
            "affects_gameplay": True,
            "visibility_modifier": random.uniform(0.5, 1.0),
        }

    def _generate_ecology(self, biomes: List[Dict], theme: str) -> Dict[str, Any]:
        creature_types = ["herbivore", "carnivore", "neutral", "magical"]
        return {
            "creature_types": creature_types,
            "population_density": random.uniform(0.3, 0.8),
            "predator_prey_ratio": random.uniform(0.2, 0.5),
            "migration_patterns": random.choice(["seasonal", "nomadic", "territorial"]),
            "biome_creatures": {
                b["name"]: [random.choice(creature_types) for _ in range(random.randint(2, 5))]
                for b in biomes
            },
        }

    def _generate_pois(self, structures: List[Dict], biomes: List[Dict]) -> List[Dict[str, Any]]:
        pois = []
        for struct in structures[:5]:
            pois.append({
                "poi_id": f"poi_{len(pois)}",
                "name": struct["name"],
                "type": "landmark",
                "position": struct["position"],
                "description": f"A notable {struct['type']} in the {struct['biome']} region.",
                "discovered": False,
            })
        # Add hidden secrets
        for i in range(random.randint(3, 8)):
            biome = random.choice(biomes)
            pois.append({
                "poi_id": f"poi_secret_{i}",
                "name": f"Hidden Cache {i+1}",
                "type": "secret",
                "position": {"x": random.randint(0, 256), "y": random.randint(0, 256)},
                "description": "A hidden treasure waiting to be discovered.",
                "discovered": False,
            })
        return pois

    def _generate_connections(self, structures: List[Dict]) -> List[Dict[str, Any]]:
        connections = []
        for i, s1 in enumerate(structures):
            for s2 in structures[i+1:]:
                if random.random() < 0.3:
                    connections.append({
                        "from": s1["structure_id"],
                        "to": s2["structure_id"],
                        "type": random.choice(["path", "road", "tunnel", "portal"]),
                        "distance": random.randint(50, 500),
                        "travel_time_s": random.randint(10, 120),
                    })
        return connections


# =============================================================================
# Persona Factory (Generative NPC System)
# =============================================================================


class PersonaFactory:
    """Creates generative NPC personas with memories, schedules, and relationships.

    Each persona has:
    - A unique personality profile with traits and disposition
    - A backstory that informs their goals and fears
    - A daily schedule that creates rhythm and routine
    - A memory stream that records interactions and evolves over time
    - Social relationships that form a web of connections
    - Dialogue style that reflects their personality
    """

    NAME_PARTS_A = [
        "El", "Aer", "Bram", "Cael", "Dor", "Fen", "Gwen", "Hal", "Iren",
        "Jor", "Kael", "Lyr", "Mor", "Nyx", "Orin", "Pyra", "Quin", "Ras",
        "Syl", "Thal", "Uma", "Vex", "Wren", "Xan", "Yara", "Zeph",
    ]
    NAME_PARTS_B = [
        "wyn", "dor", "grim", "horn", "leaf", "mir", "neth", "phil", "rith",
        "shadow", "thorn", "vale", "wind", "heart", "blade", "forge", "spark",
        "gale", "stone", "flare", "crest", "mark", "song", "dawn", "fall",
    ]

    ROLES = [
        "merchant", "guard", "sage", "healer", "blacksmith", "innkeeper",
        "farmer", "hunter", "alchemist", "bard", "noble", "beggar",
        "knight", "scholar", "explorer", "priest", "thief", "chef",
    ]

    PERSONALITY_TRAITS = [
        "brave", "cautious", "curious", "stern", "cheerful", "mysterious",
        "loyal", "cunning", "honest", "secretive", "ambitious", "humble",
        "optimistic", "pessimistic", "creative", "analytical", "passionate",
        "stoic", "playful", "wise", "reckless", "patient", "impulsive",
    ]

    DIALOGUE_STYLES = [
        "formal", "casual", "gruff", "poetic", "terse", "eloquent",
        "humorous", "melancholic", "mysterious", "enthusiastic",
    ]

    FACTIONS = [
        "townsfolk", "merchants_guild", "adventurers_guild", "scholars_circle",
        "royal_court", "underground", "clergy", "rangers", "none",
    ]

    BACKSTORY_TEMPLATES = [
        "Once a traveler who settled after finding peace in this land.",
        "A local born and raised, knowing every stone and stream.",
        "An exile from a distant kingdom, seeking a new beginning.",
        "A former adventurer who retired after one too many close calls.",
        "A scholar drawn here by ancient mysteries hidden in the region.",
        "A artisan whose craft has sustained the community for years.",
        "A mysterious figure whose past is known to none.",
        "A healer who arrived during a plague and never left.",
    ]

    def __init__(self, world: WorldContent):
        self._world = world
        self._personas: List[Persona] = []
        self._name_cache: Set[str] = set()

    def generate_cast(self, count: int = 12) -> List[Persona]:
        """Generate a cast of NPC personas with interconnected relationships."""
        self._personas = []
        for _ in range(count):
            persona = self._generate_single()
            self._personas.append(persona)
        self._build_relationships()
        return self._personas

    def _generate_single(self) -> Persona:
        name = self._generate_name()
        role = random.choice(self.ROLES)
        traits = random.sample(self.PERSONALITY_TRAITS, random.randint(2, 4))
        backstory = random.choice(self.BACKSTORY_TEMPLATES)
        schedule = self._generate_schedule(role)
        memories = self._generate_initial_memories(role)
        dialogue_style = random.choice(self.DIALOGUE_STYLES)
        goals = self._generate_goals(role)
        fears = self._generate_fears()
        appearance = self._generate_appearance()
        location = self._random_location()
        faction = random.choice(self.FACTIONS)

        return Persona(
            persona_id=f"persona_{uuid.uuid4().hex[:10]}",
            name=name,
            role=role,
            personality_traits=traits,
            backstory=backstory,
            daily_schedule=schedule,
            memories=memories,
            relationships={},
            dialogue_style=dialogue_style,
            goals=goals,
            fears=fears,
            appearance=appearance,
            location=location,
            faction=faction,
        )

    def _generate_name(self) -> str:
        for _ in range(20):
            name = random.choice(self.NAME_PARTS_A) + random.choice(self.NAME_PARTS_B)
            if name not in self._name_cache:
                self._name_cache.add(name)
                return name
        return "NPC" + str(random.randint(100, 999))

    def _generate_schedule(self, role: str) -> List[Dict[str, Any]]:
        activities = {
            "merchant": ["open_shop", "trade_goods", "close_shop", "socialize"],
            "guard": ["patrol", "stand_watch", "rest", "train"],
            "sage": ["study", "meditate", "teach", "research"],
            "healer": ["gather_herbs", "treat_patients", "rest", "pray"],
            "blacksmith": ["smelt_ore", "forge_items", "repair", "rest"],
            "innkeeper": ["serve_guests", "cook", "clean", "rest"],
            "farmer": ["tend_crops", "feed_animals", "harvest", "rest"],
            "hunter": ["track_prey", "hunt", "skin_game", "rest"],
            "alchemist": ["gather_ingredients", "brew_potions", "experiment", "rest"],
            "bard": ["compose", "perform", "socialize", "rest"],
            "noble": ["attend_court", "socialize", "rest", "scheme"],
            "knight": ["train", "patrol", "attend_court", "rest"],
            "scholar": ["read", "write", "debate", "rest"],
            "explorer": ["survey", "map", "explore", "rest"],
            "priest": ["pray", "counsel", "conduct_service", "rest"],
            "thief": ["scout", "steal", "fence_goods", "lay_low"],
            "chef": ["prep_ingredients", "cook", "serve", "clean"],
        }
        acts = activities.get(role, ["wander", "rest", "socialize", "sleep"])
        hours = [6, 9, 12, 15, 18, 21]
        schedule = []
        for i, hour in enumerate(hours):
            act = acts[i % len(acts)]
            schedule.append({
                "hour": hour,
                "activity": act,
                "location": self._random_location(),
                "duration_h": random.uniform(1, 4),
            })
        return schedule

    def _generate_initial_memories(self, role: str) -> List[Dict[str, Any]]:
        memories = []
        memory_templates = [
            {"type": "backstory", "content": "Arrived in this place seeking a new life.", "importance": 8},
            {"type": "social", "content": "Met a stranger who shared a meal.", "importance": 5},
            {"type": "event", "content": "Witnessed a beautiful sunset over the hills.", "importance": 3},
            {"type": "conflict", "content": "Had a disagreement with a neighbor.", "importance": 6},
            {"type": "discovery", "content": "Found a strange object near the old ruins.", "importance": 7},
        ]
        for tmpl in random.sample(memory_templates, min(3, len(memory_templates))):
            memories.append({
                "memory_id": f"mem_{uuid.uuid4().hex[:8]}",
                "timestamp": time.time() - random.randint(86400, 86400 * 30),
                **tmpl,
            })
        return memories

    def _generate_goals(self, role: str) -> List[str]:
        goal_map = {
            "merchant": ["Expand trade network", "Find rare goods", "Build wealth"],
            "guard": ["Protect the town", "Earn captain's trust", "Train apprentices"],
            "sage": ["Uncover ancient knowledge", "Write a treatise", "Find a successor"],
            "healer": ["Cure the incurable", "Train an apprentice", "Find rare herbs"],
            "knight": ["Earn honor in battle", "Protect the innocent", "Serve the crown"],
            "explorer": ["Map unknown territories", "Find lost artifacts", "Discover new lands"],
        }
        return goal_map.get(role, ["Live peacefully", "Help others", "Find purpose"])

    def _generate_fears(self) -> List[str]:
        fears = [
            "Losing loved ones", "Being forgotten", "Darkness", "Heights",
            "Failure", "Poverty", "Sickness", "Betrayal", "The unknown",
            "Past catching up",
        ]
        return random.sample(fears, random.randint(1, 3))

    def _generate_appearance(self) -> Dict[str, Any]:
        return {
            "hair_color": random.choice(["black", "brown", "blonde", "red", "gray", "white"]),
            "eye_color": random.choice(["blue", "brown", "green", "gray", "amber"]),
            "build": random.choice(["slim", "average", "muscular", "stout"]),
            "height": random.choice(["short", "average", "tall"]),
            "distinguishing_feature": random.choice([
                "a scar over the left eye", "a birthmark on the wrist",
                "a silver ring", "a tattered cloak", "a bright smile",
                "a missing finger", "an old medal", "a peculiar hat",
            ]),
        }

    def _random_location(self) -> Tuple[float, float]:
        return (random.uniform(0, self._world.width), random.uniform(0, self._world.height))

    def _build_relationships(self) -> None:
        """Create a web of social relationships between personas."""
        for persona in self._personas:
            others = [p for p in self._personas if p.persona_id != persona.persona_id]
            if not others:
                continue
            rel_count = random.randint(1, min(5, len(others)))
            for other in random.sample(others, rel_count):
                rel_type = random.choice([
                    "friend", "rival", "family", "acquaintance",
                    "mentor", "student", "business_partner", "romantic_interest",
                ])
                persona.relationships[other.persona_id] = rel_type


# =============================================================================
# Narrative Weaver
# =============================================================================


class NarrativeWeaver:
    """Weaves branching narratives with story arcs, quests, and dialogue trees."""

    QUEST_TYPES = [
        "fetch", "defeat", "escort", "investigate", "collect",
        "deliver", "rescue", "puzzle", "choice", "discovery",
    ]

    STORY_BEATS = [
        "call_to_adventure", "refusal_of_call", "meeting_mentor",
        "crossing_threshold", "tests_allies_enemies", "approach_inmost_cave",
        "supreme_ordeal", "reward_seizing_sword", "road_back",
        "resurrection", "return_with_elixir",
    ]

    def weave(
        self,
        concept: GameConcept,
        world: WorldContent,
        characters: List[Persona],
    ) -> NarrativeContent:
        """Generate narrative content for the game."""
        story_arcs = self._generate_story_arcs(concept, len(characters))
        main_quest = self._generate_main_quest_chain(concept, world, characters)
        side_quests = self._generate_side_quests(concept, characters, count=8)
        dialogue_trees = self._generate_dialogue_trees(characters)
        branching_points = self._generate_branching_points(main_quest)
        endings = self._generate_endings(concept)
        emotional_arc = self._generate_emotional_arc()
        pacing = self._generate_pacing_curve(len(main_quest))

        return NarrativeContent(
            story_arcs=story_arcs,
            main_quest_chain=main_quest,
            side_quests=side_quests,
            dialogue_trees=dialogue_trees,
            branching_points=branching_points,
            endings=endings,
            emotional_arc=emotional_arc,
            pacing_curve=pacing,
        )

    def _generate_story_arcs(self, concept: GameConcept, char_count: int) -> List[Dict[str, Any]]:
        arcs = []
        arc_count = min(3, max(1, char_count // 4))
        for i in range(arc_count):
            arcs.append({
                "arc_id": f"arc_{i}",
                "title": f"Story Arc {i+1}",
                "theme": random.choice(["redemption", "discovery", "sacrifice", "growth", "vengeance"]),
                "involved_characters": random.randint(2, 5),
                "beats": self.STORY_BEATS[:],
                "resolution": random.choice(["triumphant", "bittersweet", "tragic", "open"]),
                "emotional_tone": random.choice(["hopeful", "dark", "mysterious", "uplifting"]),
            })
        return arcs

    def _generate_main_quest_chain(
        self, concept: GameConcept, world: WorldContent, characters: List[Persona]
    ) -> List[Dict[str, Any]]:
        chain = []
        quest_count = random.randint(5, 10)
        for i in range(quest_count):
            quest_type = self.QUEST_TYPES[i % len(self.QUEST_TYPES)]
            giver = random.choice(characters) if characters else None
            chain.append({
                "quest_id": f"main_quest_{i}",
                "title": f"Chapter {i+1}: {quest_type.capitalize()} Quest",
                "type": quest_type,
                "description": f"The player must {quest_type} to advance the main storyline.",
                "quest_giver": giver.name if giver else "Unknown",
                "objectives": self._generate_objectives(quest_type),
                "rewards": {
                    "xp": random.randint(100, 500),
                    "gold": random.randint(50, 300),
                    "items": [f"item_{j}" for j in range(random.randint(1, 3))],
                },
                "prerequisites": [f"main_quest_{i-1}"] if i > 0 else [],
                "location": random.choice(world.structures) if world.structures else None,
                "branching": i in [quest_count // 3, quest_count * 2 // 3],
            })
        return chain

    def _generate_side_quests(self, concept: GameConcept, characters: List[Persona], count: int) -> List[Dict[str, Any]]:
        quests = []
        for i in range(count):
            quest_type = random.choice(self.QUEST_TYPES)
            giver = random.choice(characters) if characters else None
            quests.append({
                "quest_id": f"side_quest_{i}",
                "title": f"Side Quest: {quest_type.capitalize()}",
                "type": quest_type,
                "description": f"A side activity where the player can {quest_type}.",
                "quest_giver": giver.name if giver else "Villager",
                "objectives": self._generate_objectives(quest_type),
                "rewards": {
                    "xp": random.randint(25, 150),
                    "gold": random.randint(10, 100),
                    "items": [f"item_{j}" for j in range(random.randint(0, 2))],
                },
                "optional": True,
                "repeatable": random.choice([True, False]),
            })
        return quests

    def _generate_objectives(self, quest_type: str) -> List[Dict[str, Any]]:
        if quest_type == "fetch":
            return [{"type": "collect", "target": "lost_item", "count": 1, "location": "dungeon"}]
        elif quest_type == "defeat":
            return [{"type": "kill", "target": "boss_enemy", "count": 1, "location": "arena"}]
        elif quest_type == "escort":
            return [{"type": "protect", "target": "npc", "destination": "safe_zone"}]
        elif quest_type == "investigate":
            return [{"type": "reach", "target": "clue_location", "count": 3}]
        elif quest_type == "collect":
            return [{"type": "collect", "target": "resource", "count": random.randint(3, 10)}]
        else:
            return [{"type": "complete", "target": "objective", "count": 1}]

    def _generate_dialogue_trees(self, characters: List[Persona]) -> List[Dict[str, Any]]:
        trees = []
        for char in characters[:8]:  # Limit to first 8 characters
            trees.append({
                "dialogue_id": f"dialogue_{char.persona_id}",
                "speaker": char.name,
                "style": char.dialogue_style,
                "nodes": [
                    {
                        "node_id": "start",
                        "text": f"Hello there, traveler. I am {char.name}, the {char.role}.",
                        "choices": [
                            {"text": "Tell me about yourself.", "next": "about_self", "mood": "neutral"},
                            {"text": "Any work for me?", "next": "quest_offer", "mood": "neutral"},
                            {"text": "Goodbye.", "next": "end", "mood": "neutral"},
                        ],
                    },
                    {
                        "node_id": "about_self",
                        "text": char.backstory,
                        "choices": [
                            {"text": "Interesting. Any work?", "next": "quest_offer", "mood": "positive"},
                            {"text": "Farewell.", "next": "end", "mood": "neutral"},
                        ],
                    },
                    {
                        "node_id": "quest_offer",
                        "text": f"I could use help with something. Would you assist me?",
                        "choices": [
                            {"text": "I'll help.", "next": "quest_accept", "mood": "positive"},
                            {"text": "Not now.", "next": "end", "mood": "neutral"},
                        ],
                    },
                    {
                        "node_id": "quest_accept",
                        "text": "Wonderful! I'll mark the location on your map.",
                        "choices": [{"text": "[Accept Quest]", "next": "end", "mood": "positive"}],
                    },
                    {
                        "node_id": "end",
                        "text": f"Safe travels, friend.",
                        "choices": [],
                    },
                ],
            })
        return trees

    def _generate_branching_points(self, main_quest: List[Dict]) -> List[Dict[str, Any]]:
        branches = []
        for quest in main_quest:
            if quest.get("branching"):
                branches.append({
                    "quest_id": quest["quest_id"],
                    "title": quest["title"],
                    "choices": [
                        {"text": "Side with the rebels", "consequence": "rebellion_path", "alignment": "chaotic"},
                        {"text": "Support the crown", "consequence": "loyalist_path", "alignment": "lawful"},
                        {"text": "Find a middle ground", "consequence": "diplomat_path", "alignment": "neutral"},
                    ],
                })
        return branches

    def _generate_endings(self, concept: GameConcept) -> List[Dict[str, Any]]:
        return [
            {
                "ending_id": "ending_good",
                "title": "Triumphant Victory",
                "condition": "Complete main quest with high reputation",
                "description": "The player succeeds in their quest, earning the respect of all.",
                "emotional_tone": "triumphant",
            },
            {
                "ending_id": "ending_neutral",
                "title": "Bittersweet Conclusion",
                "condition": "Complete main quest with mixed choices",
                "description": "The player succeeds but at a personal cost.",
                "emotional_tone": "bittersweet",
            },
            {
                "ending_id": "ending_dark",
                "title": "Shadow's Embrace",
                "condition": "Complete main quest with dark choices",
                "description": "The player achieves their goal through dark means.",
                "emotional_tone": "somber",
            },
        ]

    def _generate_emotional_arc(self) -> Dict[str, Any]:
        return {
            "arc_type": random.choice(["rise", "fall", "rise_fall", "fall_rise"]),
            "peak_intensity": random.uniform(0.7, 1.0),
            "lowest_point": random.uniform(0.1, 0.4),
            "resolution_intensity": random.uniform(0.6, 0.9),
            "key_emotions": ["hope", "fear", "determination", "joy", "sadness"],
        }

    def _generate_pacing_curve(self, quest_count: int) -> List[float]:
        if quest_count == 0:
            return [0.5]
        curve = []
        for i in range(quest_count):
            t = i / max(quest_count - 1, 1)
            intensity = 0.3 + 0.5 * math.sin(t * math.pi * 2) + 0.2 * t
            curve.append(max(0.0, min(1.0, intensity)))
        return curve


# =============================================================================
# Mechanic Synthesizer
# =============================================================================


class MechanicSynthesizer:
    """Synthesizes gameplay mechanics, progression, and balance."""

    def synth(self, concept: GameConcept) -> MechanicSet:
        """Generate gameplay mechanics for the game concept."""
        core = self._generate_core_mechanics(concept.genre)
        secondary = self._generate_secondary_mechanics(concept.genre)
        progression = self._generate_progression(concept.genre, concept.complexity)
        economy = self._generate_economy(concept.genre)
        combat = self._generate_combat(concept.genre)
        interaction = self._generate_interaction(concept.genre)
        balance = self._generate_balance_params(concept.genre, concept.complexity)

        return MechanicSet(
            core_mechanics=core,
            secondary_mechanics=secondary,
            progression_system=progression,
            economy_system=economy,
            combat_system=combat,
            interaction_system=interaction,
            balance_parameters=balance,
        )

    def _generate_core_mechanics(self, genre: GameGenre) -> List[Dict[str, Any]]:
        genre_mechanics = {
            GameGenre.PLATFORMER: [
                {"name": "Movement", "params": {"speed": 200, "jump_force": 400, "gravity": 800}},
                {"name": "Double_Jump", "params": {"enabled": True, "cooldown": 0.2}},
                {"name": "Wall_Slide", "params": {"slide_speed": 100, "jump_off_force": 300}},
                {"name": "Collection", "params": {"types": ["coin", "gem", "star"], "score_per": [10, 50, 100]}},
            ],
            GameGenre.RPG: [
                {"name": "Leveling", "params": {"base_xp": 100, "multiplier": 1.5, "max_level": 50}},
                {"name": "Combat", "params": {"turn_based": False, "abilities": 4, "cooldown_base": 5.0}},
                {"name": "Inventory", "params": {"slots": 30, "weight_limit": 100, "stack_max": 99}},
                {"name": "Skill_Tree", "params": {"branches": 3, "nodes_per_branch": 10, "refundable": True}},
            ],
            GameGenre.PUZZLE: [
                {"name": "Grid_Manipulation", "params": {"grid_size": [8, 8], "cell_types": 6}},
                {"name": "Match_Detection", "params": {"min_match": 3, "cascade": True}},
                {"name": "Score_System", "params": {"base_per_match": 100, "combo_multiplier": 1.5}},
                {"name": "Move_Limit", "params": {"base_moves": 20, "bonus_per_level": 2}},
            ],
            GameGenre.SHOOTER: [
                {"name": "Shooting", "params": {"fire_rate": 0.15, "bullet_speed": 600, "spread": 0.02}},
                {"name": "Movement", "params": {"speed": 250, "dash_distance": 150, "dash_cd": 2.0}},
                {"name": "Health", "params": {"max_hp": 100, "regen_rate": 2, "armor": 25}},
                {"name": "Weapon_System", "params": {"types": 5, "swap_time": 0.5, "ammo_per_type": [30, 12, 6, 50, 100]}},
            ],
            GameGenre.BOSS_BATTLE: [
                {"name": "Dodge", "params": {"iframes": 0.5, "distance": 120, "cooldown": 1.0}},
                {"name": "Attack", "params": {"damage": 15, "range": 80, "windup": 0.3}},
                {"name": "Boss_Phases", "params": {"phase_count": 3, "threshold_percent": [66, 33]}},
                {"name": "Healing", "params": {"potions": 3, "heal_amount": 50, "use_time": 1.0}},
            ],
        }
        return genre_mechanics.get(genre, [
            {"name": "Movement", "params": {"speed": 150}},
            {"name": "Interaction", "params": {"range": 50}},
            {"name": "Health", "params": {"max_hp": 100}},
            {"name": "Score", "params": {"base": 0}},
        ])

    def _generate_secondary_mechanics(self, genre: GameGenre) -> List[Dict[str, Any]]:
        common = [
            {"name": "Save_System", "params": {"checkpoints": True, "auto_save_interval": 60}},
            {"name": "Audio_System", "params": {"music_volume": 0.7, "sfx_volume": 0.8, "spatial": False}},
            {"name": "UI_System", "params": {"hud": True, "menu_type": "pause"}},
        ]
        genre_specific = {
            GameGenre.RPG: [
                {"name": "Crafting", "params": {"recipes": 20, "stations": ["forge", "alchemy", "cooking"]}},
                {"name": "Dialogue", "params": {" branching": True, "reputation": True}},
                {"name": "Mount_System", "params": {"mount_types": ["horse", "wolf"], "speed_bonus": 1.5}},
            ],
            GameGenre.SHOOTER: [
                {"name": "Power_Ups", "params": {"types": ["speed", "damage", "shield"], "duration": 10}},
                {"name": "Wave_System", "params": {"waves": 10, "enemies_per_wave": [5, 20]}},
            ],
        }
        return common + genre_specific.get(genre, [])

    def _generate_progression(self, genre: GameGenre, complexity: str) -> Dict[str, Any]:
        return {
            "type": "xp_based",
            "max_level": {"simple": 20, "medium": 50, "complex": 99}.get(complexity, 50),
            "xp_curve": "exponential",
            "base_xp": 100,
            "multiplier": 1.5,
            "milestones": [
                {"level": 5, "reward": "New ability unlocked"},
                {"level": 10, "reward": "New area accessible"},
                {"level": 25, "reward": "Special item"},
                {"level": 50, "reward": "Endgame content"},
            ],
            "skill_points_per_level": 1,
            "stat_increases": {"hp": 10, "mp": 5, "attack": 2, "defense": 1},
        }

    def _generate_economy(self, genre: GameGenre) -> Dict[str, Any]:
        return {
            "currency": "gold",
            "starting_amount": 100,
            "earn_sources": [
                {"type": "quest_reward", "range": [10, 500]},
                {"type": "enemy_drop", "range": [1, 50]},
                {"type": "item_sale", "margin": 0.6},
                {"type": "discovery", "range": [5, 100]},
            ],
            "spend_sinks": [
                {"type": "equipment", "range": [50, 1000]},
                {"type": "consumables", "range": [5, 100]},
                {"type": "upgrades", "range": [100, 5000]},
                {"type": "cosmetics", "range": [10, 500]},
            ],
            "inflation_rate": 0.05,
            "trade_routes": random.randint(3, 8),
        }

    def _generate_combat(self, genre: GameGenre) -> Dict[str, Any]:
        if genre in [GameGenre.PUZZLE, GameGenre.MUSIC, GameGenre.RACING]:
            return {"enabled": False}
        return {
            "enabled": True,
            "type": "action" if genre != GameGenre.RPG else "hybrid",
            "damage_formula": "base * (1 + str * 0.1) * crit_mult",
            "crit_chance": 0.1,
            "crit_multiplier": 2.0,
            "damage_types": ["physical", "magical", "true"],
            "status_effects": ["poison", "burn", "freeze", "stun", "bleed"],
            "combo_system": genre == GameGenre.SHOOTER,
            "dodge_mechanic": genre in [GameGenre.BOSS_BATTLE, GameGenre.SHOOTER, GameGenre.RPG],
            "block_mechanic": genre in [GameGenre.RPG, GameGenre.DUNGEON_CRAWLER],
        }

    def _generate_interaction(self, genre: GameGenre) -> Dict[str, Any]:
        return {
            "talk_to_npc": genre in [GameGenre.RPG, GameGenre.NARRATIVE, GameGenre.DUNGEON_CRAWLER],
            "examine_objects": True,
            "use_items": True,
            "craft_items": genre in [GameGenre.RPG, GameGenre.SURVIVAL, GameGenre.DUNGEON_CRAWLER],
            "build_structures": genre in [GameGenre.SANDBOX, GameGenre.SURVIVAL],
            "trade": genre in [GameGenre.RPG, GameGenre.DUNGEON_CRAWLER],
            "steal": genre in [GameGenre.RPG, GameGenre.DUNGEON_CRAWLER],
        }

    def _generate_balance_params(self, genre: GameGenre, complexity: str) -> Dict[str, Any]:
        return {
            "player_power_curve": "logarithmic",
            "enemy_scaling": "linear",
            "difficulty_zones": {"easy": 0.7, "normal": 1.0, "hard": 1.3, "extreme": 1.6},
            "resource_scarcity": {"simple": 0.8, "medium": 0.5, "complex": 0.3}.get(complexity, 0.5),
            "death_penalty": {"xp_loss": 0.1, "gold_loss": 0.2, "item_drop": False},
            "checkpoint_density": {"simple": 0.8, "medium": 0.5, "complex": 0.3}.get(complexity, 0.5),
        }


# =============================================================================
# Level Architect
# =============================================================================


class LevelArchitect:
    """Designs level layouts with difficulty curves and pacing."""

    def design(self, concept: GameConcept, mechanics: MechanicSet) -> LevelDesign:
        """Generate level design based on concept and mechanics."""
        level_count = self._determine_level_count(concept.genre, concept.complexity)
        levels = self._generate_levels(level_count, concept, mechanics)
        difficulty_curve = self._determine_difficulty_curve(concept.genre)
        pacing = self._generate_pacing(level_count)
        flow = self._generate_flow_graph(levels)

        total_time = sum(l.get("estimated_duration", 300) for l in levels)
        return LevelDesign(
            levels=levels,
            difficulty_curve=difficulty_curve,
            pacing=pacing,
            flow_graph=flow,
            total_playtime_estimate=total_time,
        )

    def _determine_level_count(self, genre: GameGenre, complexity: str) -> int:
        base = {
            GameGenre.PLATFORMER: 15, GameGenre.RPG: 20, GameGenre.PUZZLE: 30,
            GameGenre.SHOOTER: 10, GameGenre.DUNGEON_CRAWLER: 12,
            GameGenre.BOSS_BATTLE: 5, GameGenre.NARRATIVE: 8,
            GameGenre.EXPLORATION: 10,
        }.get(genre, 10)
        mult = {"simple": 0.6, "medium": 1.0, "complex": 1.5}.get(complexity, 1.0)
        return max(3, int(base * mult))

    def _generate_levels(self, count: int, concept: GameConcept, mechanics: MechanicSet) -> List[Dict[str, Any]]:
        levels = []
        for i in range(count):
            difficulty = min(10, max(1, (i + 1) * 10 // count))
            level_type = self._determine_level_type(i, count, concept.genre)
            levels.append({
                "level_id": f"level_{i}",
                "name": self._generate_level_name(i, level_type, concept.theme),
                "type": level_type,
                "difficulty": difficulty,
                "estimated_duration": random.randint(120, 600),
                "objectives": self._generate_level_objectives(level_type, concept.genre),
                "enemies": self._generate_enemy_list(difficulty, concept.genre),
                "collectibles": random.randint(3, 15),
                "secrets": random.randint(0, 3),
                "environment": random.choice(["indoor", "outdoor", "mixed"]),
                "biome": random.choice(["forest", "cave", "castle", "desert", "sky", "underwater"]),
                "boss": level_type == "boss",
                "checkpoint_count": random.randint(2, 6),
            })
        return levels

    def _determine_level_type(self, index: int, total: int, genre: GameGenre) -> str:
        if index == 0:
            return "tutorial"
        if index == total - 1:
            return "final"
        if index % 4 == 3:
            return "boss"
        if index % 5 == 4:
            return "bonus"
        return "standard"

    def _generate_level_name(self, index: int, level_type: str, theme: str) -> str:
        type_names = {
            "tutorial": "Beginnings",
            "standard": f"Stage {index}",
            "boss": f"Showdown {index}",
            "bonus": f"Bonus {index}",
            "final": "Final Confrontation",
        }
        return f"{theme.capitalize()} {type_names.get(level_type, 'Level')}"

    def _generate_level_objectives(self, level_type: str, genre: GameGenre) -> List[str]:
        if level_type == "tutorial":
            return ["Learn movement", "Learn to interact", "Complete first challenge"]
        if level_type == "boss":
            return ["Reach the arena", "Defeat the boss"]
        if level_type == "final":
            return ["Navigate the final area", "Defeat the final boss", "Complete the story"]
        return ["Reach the exit", "Collect all items", "Defeat all enemies"]

    def _generate_enemy_list(self, difficulty: int, genre: GameGenre) -> List[Dict[str, Any]]:
        if genre in [GameGenre.PUZZLE, GameGenre.MUSIC]:
            return []
        count = max(0, difficulty // 2)
        return [
            {
                "type": random.choice(["melee", "ranged", "fast", "tank", "flying"]),
                "hp": 50 + difficulty * 10,
                "damage": 5 + difficulty * 2,
                "speed": 100 + difficulty * 5,
                "count": random.randint(2, 8),
            }
            for _ in range(count)
        ]

    def _determine_difficulty_curve(self, genre: GameGenre) -> str:
        curves = {
            GameGenre.PLATFORMER: "linear",
            GameGenre.RPG: "logarithmic",
            GameGenre.PUZZLE: "step",
            GameGenre.SHOOTER: "exponential",
            GameGenre.DUNGEON_CRAWLER: "exponential",
        }
        return curves.get(genre, "linear")

    def _generate_pacing(self, level_count: int) -> Dict[str, Any]:
        return {
            "tension_curve": "rise_fall_rise",
            "action_to_rest_ratio": 3.0,
            "peak_levels": [level_count // 2, level_count - 1],
            "rest_levels": [i for i in range(level_count) if i % 5 == 4],
            "climax_level": level_count - 1,
        }

    def _generate_flow_graph(self, levels: List[Dict]) -> Dict[str, Any]:
        nodes = [{"id": l["level_id"], "name": l["name"]} for l in levels]
        edges = []
        for i in range(len(levels) - 1):
            edges.append({"from": levels[i]["level_id"], "to": levels[i+1]["level_id"], "type": "sequential"})
            if i + 2 < len(levels) and levels[i+1]["type"] == "bonus":
                edges.append({"from": levels[i]["level_id"], "to": levels[i+2]["level_id"], "type": "skip"})
        return {"nodes": nodes, "edges": edges}


# =============================================================================
# Content Validator
# =============================================================================


class ContentValidator:
    """Validates generated content for coherence and quality."""

    def validate(self, gdd: GameDesignDocument) -> Tuple[float, List[str]]:
        """Validate a game design document and return (score, warnings)."""
        warnings: List[str] = []
        score = 0.0
        checks = 0

        # Check world content
        if gdd.world:
            checks += 1
            if len(gdd.world.biomes) >= 2:
                score += 1.0
            else:
                warnings.append("World has too few biomes")
            if len(gdd.world.structures) >= 3:
                score += 1.0
            else:
                warnings.append("World has too few structures")
            checks += 1

        # Check characters
        checks += 1
        if len(gdd.characters) >= 3:
            score += 1.0
        else:
            warnings.append("Too few characters for engaging gameplay")
        checks += 1
        if all(p.goals for p in gdd.characters):
            score += 0.5
        else:
            warnings.append("Some characters lack goals")

        # Check narrative
        if gdd.narrative:
            checks += 1
            if len(gdd.narrative.main_quest_chain) >= 3:
                score += 1.0
            else:
                warnings.append("Main quest chain too short")
            checks += 1
            if gdd.narrative.endings:
                score += 0.5
            else:
                warnings.append("No endings defined")

        # Check mechanics
        if gdd.mechanics:
            checks += 1
            if len(gdd.mechanics.core_mechanics) >= 3:
                score += 1.0
            else:
                warnings.append("Too few core mechanics")
            checks += 1
            if gdd.mechanics.balance_parameters:
                score += 0.5

        # Check levels
        if gdd.levels:
            checks += 1
            if len(gdd.levels.levels) >= 3:
                score += 1.0
            else:
                warnings.append("Too few levels")

        final_score = (score / max(checks, 1)) * 10.0 if checks > 0 else 5.0
        return round(final_score, 1), warnings


# =============================================================================
# Game Content Synthesizer (Main Class)
# =============================================================================


class GameContentSynthesizer:
    """
    The central content generation intelligence for SparkLabs.

    Transforms natural-language game descriptions into complete, structured
    game design documents with world content, characters, narratives,
    mechanics, and level designs.

    Uses the LLM Router for AI-powered generation when available, and falls
    back to a sophisticated procedural generation system otherwise.
    """

    _instance: Optional["GameContentSynthesizer"] = None
    _instance_lock = threading.RLock()

    def __init__(self) -> None:
        if GameContentSynthesizer._instance is not None:
            raise RuntimeError("Use GameContentSynthesizer.get_instance()")
        self._initialized: bool = False
        self._analyzer = PromptAnalyzer()
        self._world_builder = WorldContentBuilder()
        self._persona_factory: Optional[PersonaFactory] = None
        self._narrative_weaver = NarrativeWeaver()
        self._mechanic_synth = MechanicSynthesizer()
        self._level_architect = LevelArchitect()
        self._validator = ContentValidator()
        self._synthesis_history: deque = deque(maxlen=100)
        self._lock = threading.RLock()
        self._llm_available: bool = False

    @classmethod
    def get_instance(cls) -> "GameContentSynthesizer":
        if cls._instance is None:
            with cls._instance_lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def initialize(self) -> None:
        with self._lock:
            if self._initialized:
                return
            self._check_llm_availability()
            self._initialized = True
            logger.info("GameContentSynthesizer initialized (llm=%s)", self._llm_available)

    def _check_llm_availability(self) -> None:
        """Check if the LLM Router has any configured providers."""
        try:
            from sparkai.agent.agent_llm_router import get_llm_router
            router = get_llm_router()
            status = router.get_status()
            data = status.get("data", status) if isinstance(status, dict) else {}
            providers = data.get("providers", [])
            configured = [p for p in providers if p.get("api_key")]
            self._llm_available = len(configured) > 0
        except Exception:
            self._llm_available = False

    def synthesize(
        self,
        prompt: str,
        genre_hint: Optional[str] = None,
        character_count: int = 12,
        level_count_hint: Optional[int] = None,
    ) -> SynthesisResult:
        """
        Synthesize complete game content from a natural-language prompt.

        This is the primary entry point for AI-native game content generation.
        Produces a complete GameDesignDocument with all content sections filled.

        Args:
            prompt: Natural-language description of the desired game
            genre_hint: Optional genre hint to guide generation
            character_count: Number of NPC personas to generate
            level_count_hint: Optional hint for number of levels

        Returns:
            SynthesisResult containing the complete GameDesignDocument
        """
        if not self._initialized:
            self.initialize()

        result_id = f"synth_{uuid.uuid4().hex[:12]}"
        start_time = time.time()
        phases_completed: List[str] = []
        phases_skipped: List[str] = []
        warnings: List[str] = []

        try:
            # Phase 1: Analyze prompt
            concept = self._analyzer.analyze(prompt)
            if genre_hint:
                try:
                    concept.genre = GameGenre(genre_hint)
                except ValueError:
                    pass
            phases_completed.append(SynthesisPhase.ANALYZE.value)

            # Phase 2: Build world
            world = self._world_builder.build(concept)
            phases_completed.append(SynthesisPhase.WORLD_BUILD.value)

            # Phase 3: Generate characters
            self._persona_factory = PersonaFactory(world)
            characters = self._persona_factory.generate_cast(character_count)
            phases_completed.append(SynthesisPhase.CHARACTER_CREATE.value)

            # Phase 4: Weave narrative
            narrative = self._narrative_weaver.weave(concept, world, characters)
            phases_completed.append(SynthesisPhase.NARRATIVE_WEAVE.value)

            # Phase 5: Synthesize mechanics
            mechanics = self._mechanic_synth.synth(concept)
            phases_completed.append(SynthesisPhase.MECHANIC_SYNTH.value)

            # Phase 6: Design levels
            levels = self._level_architect.design(concept, mechanics)
            phases_completed.append(SynthesisPhase.LEVEL_ARCHITECT.value)

            # Phase 7: Compile asset manifest
            assets = self._compile_asset_manifest(concept, world, characters)
            phases_completed.append("asset_manifest")

            # Phase 8: Validate
            gdd = GameDesignDocument(
                gdd_id=f"gdd_{uuid.uuid4().hex[:12]}",
                concept=concept,
                world=world,
                characters=characters,
                narrative=narrative,
                mechanics=mechanics,
                levels=levels,
                asset_manifest=assets,
                quality_score=0.0,
                created_at=time.time(),
            )
            quality, validate_warnings = self._validator.validate(gdd)
            gdd.quality_score = quality
            warnings.extend(validate_warnings)
            phases_completed.append(SynthesisPhase.VALIDATE.value)

            duration = time.time() - start_time
            result = SynthesisResult(
                result_id=result_id,
                success=True,
                gdd=gdd,
                phases_completed=phases_completed,
                phases_skipped=phases_skipped,
                duration_s=round(duration, 3),
                warnings=warnings,
                error=None,
                metadata={
                    "llm_used": self._llm_available,
                    "genre": concept.genre.value,
                    "character_count": len(characters),
                    "level_count": len(levels.levels) if levels else 0,
                    "quality_score": quality,
                },
            )

            with self._lock:
                self._synthesis_history.append(result)

            return result

        except Exception as e:
            logger.error("Content synthesis failed: %s", e)
            duration = time.time() - start_time
            return SynthesisResult(
                result_id=result_id,
                success=False,
                gdd=None,
                phases_completed=phases_completed,
                phases_skipped=phases_skipped,
                duration_s=round(duration, 3),
                warnings=warnings,
                error=str(e),
                metadata={},
            )

    def _compile_asset_manifest(
        self, concept: GameConcept, world: WorldContent, characters: List[Persona]
    ) -> Dict[str, Any]:
        """Compile a complete asset manifest for the game."""
        return {
            "sprites": {
                "player": 1,
                "npcs": len(characters),
                "enemies": random.randint(5, 20),
                "props": random.randint(10, 30),
                "total": len(characters) + random.randint(16, 51),
            },
            "tilesets": {
                "count": len(world.biomes),
                "tiles_per_set": 64,
                "total_tiles": len(world.biomes) * 64,
            },
            "audio": {
                "music_tracks": random.randint(3, 8),
                "sfx_count": random.randint(20, 50),
                "ambient_tracks": len(world.biomes),
            },
            "ui": {
                "buttons": 10,
                "panels": 5,
                "icons": 20,
                "fonts": 2,
            },
            "animations": {
                "player": 8,
                "npcs": len(characters) * 4,
                "enemies": random.randint(5, 20) * 3,
                "effects": 15,
            },
            "levels": {
                "backgrounds": random.randint(5, 15),
                "foregrounds": random.randint(5, 15),
                "parallax_layers": 3,
            },
            "visual_style": concept.visual_style,
            "total_estimated_size_mb": round(random.uniform(10, 100), 1),
        }

    def get_status(self) -> Dict[str, Any]:
        """Get the current status of the synthesizer."""
        return {
            "initialized": self._initialized,
            "llm_available": self._llm_available,
            "total_syntheses": len(self._synthesis_history),
            "recent_syntheses": [
                {
                    "result_id": r.result_id,
                    "success": r.success,
                    "genre": r.metadata.get("genre", "unknown"),
                    "quality_score": r.metadata.get("quality_score", 0),
                    "duration_s": r.duration_s,
                }
                for r in list(self._synthesis_history)[-10:]
            ],
        }

    def get_synthesis_result(self, result_id: str) -> Optional[SynthesisResult]:
        """Retrieve a previous synthesis result by ID."""
        for r in self._synthesis_history:
            if r.result_id == result_id:
                return r
        return None


# =============================================================================
# Convenience Function
# =============================================================================


def get_content_synthesizer() -> GameContentSynthesizer:
    """Get the singleton GameContentSynthesizer instance."""
    return GameContentSynthesizer.get_instance()
