"""
SparkLabs Engine - Game Runtime

Transforms a synthesized GameDesignDocument into a complete, self-contained,
playable HTML5 game. The runtime acts as the bridge between the AI content
synthesis layer (GameContentSynthesizer) and the browser-based player.

Architecture:
  GameRuntime (Singleton)
    |-- ConceptCompiler   -> converts GDD concept into game config
    |-- WorldRenderer     -> paints biomes, structures, points of interest
    |-- EntityFactory     -> spawns player, NPCs, enemies, collectibles
    |-- MechanicBinder    -> wires core/secondary mechanics into game logic
    |-- NarrativeHost     -> injects quests, dialogue, branching points
    |-- LevelDirector     -> sequences levels with difficulty/pacing curves
    |-- HtmlAssembler     -> produces the final HTML/CSS/JS document

The produced HTML runs entirely in the browser (no external dependencies),
using a canvas-based game loop with physics, input, HUD, and win/lose states.
This design lets the game execute inside the GameRunner iframe without any
network round-trips, while still reflecting the AI-generated content.

Pattern integration (original SparkLabs design):
  - Scene tree architecture with hierarchical node composition
  - Fixed-timestep game loop with interpolation
  - Component-based entity composition (ECS roots)
  - Sprite batching and layer composition
  - Deterministic update pipeline for replayability
"""

from __future__ import annotations

import json
import logging
import math
import random
import threading
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from sparkai.engine.engine_game_extensions import FxInjector, ExtensionConfig

logger = logging.getLogger(__name__)


# =============================================================================
# Runtime Data Structures
# =============================================================================


@dataclass
class GameEntitySpec:
    """Specification for an in-game entity."""
    entity_id: str
    name: str
    entity_type: str  # player, npc, enemy, collectible, structure, terrain, trigger
    x: float
    y: float
    width: float = 32.0
    height: float = 32.0
    color: str = "#f97316"
    properties: Dict[str, Any] = field(default_factory=dict)


@dataclass
class GameLevelSpec:
    """Specification for a single game level."""
    level_id: str
    name: str
    index: int
    width: int
    height: int
    background: str
    entities: List[GameEntitySpec] = field(default_factory=list)
    objective: str = "reach_goal"
    time_limit: int = 0
    difficulty: float = 0.5


@dataclass
class GameConfig:
    """Compiled game configuration derived from a GameDesignDocument."""
    title: str
    genre: str
    theme: str
    visual_style: str
    player_role: str
    core_loop: str
    width: int
    height: int
    background: str
    accent_color: str
    player_color: str
    enemy_color: str
    collectible_color: str
    terrain_color: str
    structure_color: str
    npc_color: str
    gravity: float
    jump_strength: float
    move_speed: float
    enemy_speed: float
    collectible_count: int
    enemy_count: int
    npc_count: int
    lives: int
    narrative_intro: str = ""
    quest_summary: str = ""
    ending_text: str = ""
    levels: List[GameLevelSpec] = field(default_factory=list)
    mechanics: List[str] = field(default_factory=list)
    innovation_angles: List[str] = field(default_factory=list)


@dataclass
class RuntimeResult:
    """Result of a game runtime build."""
    success: bool
    html: str
    config: Optional[GameConfig]
    error: Optional[str]
    duration_s: float
    metadata: Dict[str, Any]


# =============================================================================
# Concept Compiler - GDD to GameConfig
# =============================================================================


class ConceptCompiler:
    """Converts a GameDesignDocument into a playable GameConfig."""

    # Genre-specific tuning parameters
    GENRE_TUNING: Dict[str, Dict[str, Any]] = {
        "platformer": {
            "gravity": 0.55, "jump_strength": 11.0, "move_speed": 4.2,
            "enemy_speed": 1.4, "background": "#1a1a2e", "accent": "#f97316",
            "player_color": "#f97316", "enemy_color": "#ef4444",
            "collectible_color": "#fbbf24", "terrain_color": "#4ade80",
            "structure_color": "#94a3b8", "npc_color": "#c084fc",
            "collectibles": 8, "enemies": 4, "npcs": 0, "lives": 3,
        },
        "top_down_adventure": {
            "gravity": 0.0, "jump_strength": 0.0, "move_speed": 3.2,
            "enemy_speed": 1.2, "background": "#0f1f1a", "accent": "#f97316",
            "player_color": "#f97316", "enemy_color": "#ef4444",
            "collectible_color": "#fbbf24", "terrain_color": "#22c55e",
            "structure_color": "#94a3b8", "npc_color": "#c084fc",
            "collectibles": 6, "enemies": 3, "npcs": 3, "lives": 4,
        },
        "puzzle": {
            "gravity": 0.0, "jump_strength": 0.0, "move_speed": 3.0,
            "enemy_speed": 0.0, "background": "#1a1a2e", "accent": "#a855f7",
            "player_color": "#a855f7", "enemy_color": "#ef4444",
            "collectible_color": "#a855f7", "terrain_color": "#2a2a4a",
            "structure_color": "#94a3b8", "npc_color": "#c084fc",
            "collectibles": 8, "enemies": 0, "npcs": 0, "lives": 5,
        },
        "shooter": {
            "gravity": 0.0, "jump_strength": 0.0, "move_speed": 3.8,
            "enemy_speed": 1.6, "background": "#0a0a1a", "accent": "#f97316",
            "player_color": "#f97316", "enemy_color": "#ef4444",
            "collectible_color": "#fbbf24", "terrain_color": "#2a2a4a",
            "structure_color": "#60a5fa", "npc_color": "#c084fc",
            "collectibles": 4, "enemies": 6, "npcs": 0, "lives": 3,
        },
        "rpg": {
            "gravity": 0.0, "jump_strength": 0.0, "move_speed": 3.0,
            "enemy_speed": 1.0, "background": "#1a1a2e", "accent": "#f97316",
            "player_color": "#f97316", "enemy_color": "#ef4444",
            "collectible_color": "#fbbf24", "terrain_color": "#22c55e",
            "structure_color": "#94a3b8", "npc_color": "#c084fc",
            "collectibles": 5, "enemies": 3, "npcs": 4, "lives": 5,
        },
        "dungeon_crawler": {
            "gravity": 0.0, "jump_strength": 0.0, "move_speed": 3.2,
            "enemy_speed": 1.3, "background": "#0f0f1a", "accent": "#f97316",
            "player_color": "#f97316", "enemy_color": "#ef4444",
            "collectible_color": "#fbbf24", "terrain_color": "#2a2a4a",
            "structure_color": "#94a3b8", "npc_color": "#c084fc",
            "collectibles": 6, "enemies": 5, "npcs": 1, "lives": 4,
        },
        "racing": {
            "gravity": 0.0, "jump_strength": 0.0, "move_speed": 5.5,
            "enemy_speed": 4.5, "background": "#1a1a2e", "accent": "#f97316",
            "player_color": "#f97316", "enemy_color": "#ef4444",
            "collectible_color": "#22c55e", "terrain_color": "#4ade80",
            "structure_color": "#94a3b8", "npc_color": "#c084fc",
            "collectibles": 8, "enemies": 2, "npcs": 0, "lives": 3,
        },
        "boss_battle": {
            "gravity": 0.5, "jump_strength": 10.0, "move_speed": 4.0,
            "enemy_speed": 2.0, "background": "#1a0a0a", "accent": "#f97316",
            "player_color": "#f97316", "enemy_color": "#ef4444",
            "collectible_color": "#22c55e", "terrain_color": "#4ade80",
            "structure_color": "#94a3b8", "npc_color": "#c084fc",
            "collectibles": 3, "enemies": 1, "npcs": 0, "lives": 5,
        },
        "narrative": {
            "gravity": 0.0, "jump_strength": 0.0, "move_speed": 2.8,
            "enemy_speed": 0.8, "background": "#1a1a2e", "accent": "#f97316",
            "player_color": "#f97316", "enemy_color": "#ef4444",
            "collectible_color": "#fbbf24", "terrain_color": "#22c55e",
            "structure_color": "#94a3b8", "npc_color": "#c084fc",
            "collectibles": 4, "enemies": 1, "npcs": 5, "lives": 5,
        },
        "music": {
            "gravity": 0.0, "jump_strength": 0.0, "move_speed": 3.0,
            "enemy_speed": 0.0, "background": "#1a0a2e", "accent": "#a855f7",
            "player_color": "#a855f7", "enemy_color": "#ef4444",
            "collectible_color": "#fbbf24", "terrain_color": "#2a2a4a",
            "structure_color": "#94a3b8", "npc_color": "#c084fc",
            "collectibles": 8, "enemies": 0, "npcs": 0, "lives": 5,
        },
        "survival": {
            "gravity": 0.5, "jump_strength": 9.0, "move_speed": 3.6,
            "enemy_speed": 1.5, "background": "#1a1a1a", "accent": "#f97316",
            "player_color": "#f97316", "enemy_color": "#ef4444",
            "collectible_color": "#22c55e", "terrain_color": "#4ade80",
            "structure_color": "#94a3b8", "npc_color": "#c084fc",
            "collectibles": 6, "enemies": 5, "npcs": 0, "lives": 3,
        },
        "strategy": {
            "gravity": 0.0, "jump_strength": 0.0, "move_speed": 2.5,
            "enemy_speed": 0.8, "background": "#1a1a2e", "accent": "#f97316",
            "player_color": "#f97316", "enemy_color": "#ef4444",
            "collectible_color": "#fbbf24", "terrain_color": "#22c55e",
            "structure_color": "#94a3b8", "npc_color": "#c084fc",
            "collectibles": 5, "enemies": 4, "npcs": 2, "lives": 5,
        },
        "sandbox": {
            "gravity": 0.4, "jump_strength": 9.5, "move_speed": 3.8,
            "enemy_speed": 1.0, "background": "#0f1a2e", "accent": "#f97316",
            "player_color": "#f97316", "enemy_color": "#ef4444",
            "collectible_color": "#fbbf24", "terrain_color": "#4ade80",
            "structure_color": "#94a3b8", "npc_color": "#c084fc",
            "collectibles": 10, "enemies": 2, "npcs": 2, "lives": 5,
        },
        "exploration": {
            "gravity": 0.3, "jump_strength": 8.5, "move_speed": 3.4,
            "enemy_speed": 1.0, "background": "#0f1a1a", "accent": "#f97316",
            "player_color": "#f97316", "enemy_color": "#ef4444",
            "collectible_color": "#fbbf24", "terrain_color": "#4ade80",
            "structure_color": "#94a3b8", "npc_color": "#c084fc",
            "collectibles": 8, "enemies": 2, "npcs": 2, "lives": 5,
        },
        "custom": {
            "gravity": 0.4, "jump_strength": 9.0, "move_speed": 3.6,
            "enemy_speed": 1.2, "background": "#1a1a2e", "accent": "#f97316",
            "player_color": "#f97316", "enemy_color": "#ef4444",
            "collectible_color": "#fbbf24", "terrain_color": "#4ade80",
            "structure_color": "#94a3b8", "npc_color": "#c084fc",
            "collectibles": 6, "enemies": 3, "npcs": 2, "lives": 4,
        },
    }

    def compile(self, gdd: Any) -> GameConfig:
        """Compile a GameDesignDocument into a GameConfig."""
        concept = gdd.concept
        genre_value = concept.genre.value if hasattr(concept.genre, "value") else str(concept.genre)
        tuning = self.GENRE_TUNING.get(genre_value, self.GENRE_TUNING["custom"])

        world_w = 1600
        world_h = 900
        if gdd.world is not None:
            world_w = max(800, getattr(gdd.world, "width", 1600))
            world_h = max(450, getattr(gdd.world, "height", 900))

        levels = self._compile_levels(gdd, tuning, world_w, world_h)
        narrative_intro = self._extract_narrative_intro(gdd)
        quest_summary = self._extract_quest_summary(gdd)
        ending_text = self._extract_ending(gdd)
        mechanics = self._extract_mechanics(gdd)
        innovations = list(getattr(concept, "innovation_angles", []) or [])

        return GameConfig(
            title=getattr(concept, "title", "SparkLabs Game"),
            genre=genre_value,
            theme=getattr(concept, "theme", "fantasy"),
            visual_style=getattr(concept, "visual_style", "flat-2d"),
            player_role=getattr(concept, "player_role", "hero"),
            core_loop=getattr(concept, "core_loop", "explore and overcome challenges"),
            width=world_w,
            height=world_h,
            background=tuning["background"],
            accent_color=tuning["accent"],
            player_color=tuning["player_color"],
            enemy_color=tuning["enemy_color"],
            collectible_color=tuning["collectible_color"],
            terrain_color=tuning["terrain_color"],
            structure_color=tuning["structure_color"],
            npc_color=tuning["npc_color"],
            gravity=tuning["gravity"],
            jump_strength=tuning["jump_strength"],
            move_speed=tuning["move_speed"],
            enemy_speed=tuning["enemy_speed"],
            collectible_count=tuning["collectibles"],
            enemy_count=tuning["enemies"],
            npc_count=tuning["npcs"],
            lives=tuning["lives"],
            levels=levels,
            narrative_intro=narrative_intro,
            quest_summary=quest_summary,
            ending_text=ending_text,
            mechanics=mechanics,
            innovation_angles=innovations,
        )

    def _compile_levels(self, gdd: Any, tuning: Dict[str, Any], world_w: int, world_h: int) -> List[GameLevelSpec]:
        """Build level specifications from the GDD level design."""
        levels: List[GameLevelSpec] = []
        gdd_levels = []
        if gdd.levels is not None:
            gdd_levels = getattr(gdd.levels, "levels", []) or []

        if not gdd_levels:
            # Produce a default level so the game is always playable
            gdd_levels = [{
                "name": "First Steps",
                "type": "tutorial",
                "difficulty": 0.3,
                "objective": "explore",
            }]

        for idx, lvl in enumerate(gdd_levels[:6]):
            name = lvl.get("name", f"Level {idx + 1}") if isinstance(lvl, dict) else getattr(lvl, "name", f"Level {idx + 1}")
            difficulty = lvl.get("difficulty", 0.3 + idx * 0.12) if isinstance(lvl, dict) else getattr(lvl, "difficulty", 0.3 + idx * 0.12)
            ltype = lvl.get("type", "standard") if isinstance(lvl, dict) else getattr(lvl, "type", "standard")
            objective = self._level_objective(ltype, gdd.concept.genre.value)
            entities = self._populate_level_entities(idx, difficulty, tuning, world_w, world_h, gdd)
            levels.append(GameLevelSpec(
                level_id=f"lvl_{idx}_{uuid.uuid4().hex[:6]}",
                name=str(name),
                index=idx,
                width=world_w,
                height=world_h,
                background=tuning["background"],
                entities=entities,
                objective=objective,
                time_limit=int(difficulty * 120) if ltype == "boss" else 0,
                difficulty=float(difficulty),
            ))
        return levels

    def _level_objective(self, level_type: str, genre: str) -> str:
        """Determine the objective for a level based on type and genre."""
        if level_type in ("boss", "final"):
            return "defeat_boss"
        if genre in ("puzzle", "music"):
            return "collect_all"
        if genre == "racing":
            return "reach_goal"
        if genre == "narrative":
            return "talk_npcs"
        return "reach_goal"

    def _populate_level_entities(
        self, level_idx: int, difficulty: float, tuning: Dict[str, Any],
        world_w: int, world_h: int, gdd: Any,
    ) -> List[GameEntitySpec]:
        """Populate a level with entities derived from the GDD."""
        entities: List[GameEntitySpec] = []
        rng = random.Random(level_idx * 1337 + 42)

        # Player spawn
        entities.append(GameEntitySpec(
            entity_id="player_spawn",
            name="Player",
            entity_type="player",
            x=80.0, y=float(world_h - 120),
            width=28.0, height=36.0,
            color=tuning["player_color"],
            properties={"spawn": True},
        ))

        # Terrain platforms (genre-aware)
        genre = gdd.concept.genre.value
        if tuning["gravity"] > 0:
            # Platformer-like: add platforms
            platform_count = 5 + level_idx
            for i in range(platform_count):
                px = 180 + i * ((world_w - 280) / max(1, platform_count))
                py = world_h - 80 - rng.randint(0, 180) - (i % 3) * 60
                entities.append(GameEntitySpec(
                    entity_id=f"plat_{i}",
                    name=f"Platform {i + 1}",
                    entity_type="terrain",
                    x=px, y=py,
                    width=120.0, height=18.0,
                    color=tuning["terrain_color"],
                ))
            # Ground
            entities.append(GameEntitySpec(
                entity_id="ground",
                name="Ground",
                entity_type="terrain",
                x=0.0, y=float(world_h - 40),
                width=float(world_w), height=40.0,
                color=tuning["terrain_color"],
                properties={"static": True},
            ))
        else:
            # Top-down: scatter terrain patches
            for i in range(8):
                entities.append(GameEntitySpec(
                    entity_id=f"terrain_{i}",
                    name=f"Terrain {i + 1}",
                    entity_type="terrain",
                    x=rng.uniform(60, world_w - 100),
                    y=rng.uniform(60, world_h - 100),
                    width=80.0, height=80.0,
                    color=tuning["terrain_color"],
                    properties={"static": True},
                ))

        # Structures
        structure_count = 3 + (level_idx % 3)
        for i in range(structure_count):
            entities.append(GameEntitySpec(
                entity_id=f"struct_{i}",
                name=f"Structure {i + 1}",
                entity_type="structure",
                x=rng.uniform(120, world_w - 160),
                y=rng.uniform(120, world_h - 160),
                width=60.0, height=60.0,
                color=tuning["structure_color"],
                properties={"static": True},
            ))

        # Collectibles
        coll_count = tuning["collectibles"]
        for i in range(coll_count):
            entities.append(GameEntitySpec(
                entity_id=f"coll_{i}",
                name=f"Collectible {i + 1}",
                entity_type="collectible",
                x=rng.uniform(100, world_w - 100),
                y=rng.uniform(80, world_h - 80),
                width=18.0, height=18.0,
                color=tuning["collectible_color"],
                properties={"value": 10},
            ))

        # Enemies
        enemy_count = tuning["enemies"] + level_idx
        if genre == "boss_battle":
            enemy_count = 1
        for i in range(enemy_count):
            is_boss = genre == "boss_battle" or (level_idx >= 4 and i == 0)
            entities.append(GameEntitySpec(
                entity_id=f"enemy_{i}",
                name="Boss" if is_boss else f"Enemy {i + 1}",
                entity_type="enemy",
                x=rng.uniform(200, world_w - 120),
                y=rng.uniform(100, world_h - 120),
                width=48.0 if is_boss else 28.0,
                height=48.0 if is_boss else 28.0,
                color=tuning["enemy_color"],
                properties={
                    "health": 3 if is_boss else 1,
                    "damage": 1,
                    "boss": is_boss,
                    "patrol_range": rng.uniform(60, 140),
                },
            ))

        # NPCs (from GDD personas)
        npc_count = tuning["npcs"]
        personas = getattr(gdd, "characters", []) or []
        for i in range(npc_count):
            persona = personas[i] if i < len(personas) else None
            name = getattr(persona, "name", f"NPC {i + 1}") if persona else f"NPC {i + 1}"
            role = getattr(persona, "role", "villager") if persona else "villager"
            entities.append(GameEntitySpec(
                entity_id=f"npc_{i}",
                name=name,
                entity_type="npc",
                x=rng.uniform(100, world_w - 100),
                y=rng.uniform(100, world_h - 100),
                width=28.0, height=32.0,
                color=tuning["npc_color"],
                properties={
                    "role": role,
                    "dialogue": self._npc_dialogue(persona, gdd),
                },
            ))

        # Goal/exit
        entities.append(GameEntitySpec(
            entity_id="goal",
            name="Goal",
            entity_type="trigger",
            x=float(world_w - 80), y=float(world_h - 120),
            width=32.0, height=48.0,
            color=tuning["accent"],
            properties={"goal": True},
        ))

        # Powerups (shield, speed, double-jump)
        powerup_kinds = ["shield", "speed", "doubleJump"]
        for i in range(min(2, level_idx + 1)):
            kind = powerup_kinds[i % len(powerup_kinds)]
            entities.append(GameEntitySpec(
                entity_id=f"powerup_{i}",
                name=f"Powerup {kind.capitalize()}",
                entity_type="powerup",
                x=rng.uniform(150, world_w - 150),
                y=rng.uniform(150, world_h - 150),
                width=24.0, height=24.0,
                color="#fbbf24",
                properties={"powerupKind": kind},
            ))

        # Checkpoints (1-2 per level)
        for i in range(min(2, level_idx + 1)):
            entities.append(GameEntitySpec(
                entity_id=f"checkpoint_{i}",
                name=f"Checkpoint {i + 1}",
                entity_type="checkpoint",
                x=rng.uniform(200, world_w - 200),
                y=float(world_h - 100),
                width=24.0, height=48.0,
                color="#555555",
                properties={"activated": False},
            ))

        # Hazards (spikes) — scaled by difficulty
        hazard_count = int(2 + level_idx * 1.5 + rng.random() * 2)
        for i in range(hazard_count):
            entities.append(GameEntitySpec(
                entity_id=f"hazard_{i}",
                name=f"Hazard {i + 1}",
                entity_type="hazard",
                x=rng.uniform(120, world_w - 120),
                y=float(world_h - 56),
                width=float(rng.randint(32, 64)),
                height=16.0,
                color="#ef4444",
                properties={},
            ))

        # Bounce pads
        for i in range(min(2, level_idx + 1)):
            entities.append(GameEntitySpec(
                entity_id=f"bouncepad_{i}",
                name=f"Bounce Pad {i + 1}",
                entity_type="bouncepad",
                x=rng.uniform(150, world_w - 150),
                y=float(world_h - 52),
                width=48.0, height=12.0,
                color="#06b6d4",
                properties={},
            ))

        # Moving platforms (when gravity is enabled)
        if tuning.get("gravity", 0) > 0:
            for i in range(min(2, level_idx + 1)):
                mx = rng.uniform(200, world_w - 300)
                my = rng.uniform(world_h * 0.3, world_h * 0.7)
                entities.append(GameEntitySpec(
                    entity_id=f"moving_platform_{i}",
                    name=f"Moving Platform {i + 1}",
                    entity_type="structure",
                    x=mx, y=my,
                    width=96.0, height=16.0,
                    color="#94a3b8",
                    properties={
                        "isMoving": True,
                        "moveAxis": "x" if i % 2 == 0 else "y",
                        "moveRange": float(rng.randint(80, 160)),
                        "originX": mx, "originY": my, "movePhase": 0,
                    },
                ))

        # Teleporter pair (from level index 1 onward)
        if level_idx >= 1:
            tx1 = rng.uniform(100, world_w * 0.4)
            tx2 = rng.uniform(world_w * 0.6, world_w - 100)
            ty = rng.uniform(world_h * 0.3, world_h * 0.6)
            pair_id = f"tp_{level_idx}"
            for j, tx in enumerate([tx1, tx2]):
                entities.append(GameEntitySpec(
                    entity_id=f"teleporter_{j}",
                    name=f"Teleporter {j + 1}",
                    entity_type="teleporter",
                    x=tx, y=ty,
                    width=32.0, height=32.0,
                    color="#a855f7",
                    properties={"pairId": pair_id},
                ))

        return entities

    def _npc_dialogue(self, persona: Any, gdd: Any) -> str:
        """Extract or generate dialogue for an NPC."""
        if persona is None:
            return "Be careful on your journey."
        style = getattr(persona, "dialogue_style", "neutral")
        name = getattr(persona, "name", "Stranger")
        goals = getattr(persona, "goals", []) or []
        fears = getattr(persona, "fears", []) or []
        goal_text = goals[0] if goals else "protecting this land"
        fear_text = fears[0] if fears else "the darkness ahead"
        templates = {
            "warm": f"Greetings, traveler. I am {name}. I dream of {goal_text}, though {fear_text} troubles me.",
            "gruff": f"Hmph. {name}'s the name. I seek {goal_text}. Watch out — {fear_text}.",
            "mysterious": f"...{name}. The winds whisper of {goal_text}. Yet {fear_text} lingers.",
            "cheerful": f"Hello there! I'm {name}! I'm working toward {goal_text}, but {fear_text} is scary!",
            "neutral": f"I am {name}. My purpose is {goal_text}. Beware {fear_text}.",
        }
        return templates.get(style, templates["neutral"])

    def _extract_narrative_intro(self, gdd: Any) -> str:
        """Extract the narrative introduction from the GDD."""
        if gdd.narrative is None:
            return f"Begin your journey in {getattr(gdd.concept, 'title', 'a new world')}."
        arcs = getattr(gdd.narrative, "story_arcs", []) or []
        if arcs and isinstance(arcs[0], dict):
            desc = arcs[0].get("description") or arcs[0].get("summary")
            if desc:
                return str(desc)
        main_quest = getattr(gdd.narrative, "main_quest_chain", []) or []
        if main_quest and isinstance(main_quest[0], dict):
            desc = main_quest[0].get("description") or main_quest[0].get("title")
            if desc:
                return str(desc)
        return f"A new adventure begins: {getattr(gdd.concept, 'core_loop', 'explore the world')}."

    def _extract_quest_summary(self, gdd: Any) -> str:
        """Extract a concise quest summary from the GDD narrative."""
        if gdd.narrative is None:
            return "Explore the world and reach the goal."
        main_quest = getattr(gdd.narrative, "main_quest_chain", []) or []
        titles = []
        for q in main_quest[:3]:
            if isinstance(q, dict):
                t = q.get("title") or q.get("name")
                if t:
                    titles.append(str(t))
        if titles:
            return " → ".join(titles)
        return "Complete the main quest and reach the goal."

    def _extract_ending(self, gdd: Any) -> str:
        """Extract the ending text from the GDD narrative."""
        if gdd.narrative is None:
            return "Victory! You have completed your quest."
        endings = getattr(gdd.narrative, "endings", []) or []
        if endings and isinstance(endings[0], dict):
            text = endings[0].get("description") or endings[0].get("text") or endings[0].get("title")
            if text:
                return str(text)
        return "Victory! Your journey is complete."

    def _extract_mechanics(self, gdd: Any) -> List[str]:
        """Extract mechanic names from the GDD."""
        if gdd.mechanics is None:
            return []
        result: List[str] = []
        for m in getattr(gdd.mechanics, "core_mechanics", []) or []:
            if isinstance(m, dict):
                name = m.get("name") or m.get("id")
                if name:
                    result.append(str(name))
        return result[:8]


# =============================================================================
# HTML Assembler - produces the final HTML document
# =============================================================================


class HtmlAssembler:
    """Assembles the final playable HTML document from a GameConfig."""

    def __init__(self) -> None:
        self._fx = FxInjector(ExtensionConfig())

    def assemble(self, config: GameConfig) -> str:
        """Produce a complete, self-contained HTML game document."""
        levels_json = self._serialize_levels(config)
        intro = self._escape(config.narrative_intro)
        quest = self._escape(config.quest_summary)
        fx_header = self._fx.build_header_js()
        fx_loop = self._fx.build_loop_patch_js()
        ending = self._escape(config.ending_text)

        return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8" />
<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no, viewport-fit=cover" />
<title>{self._escape(config.title)}</title>
<style>
  html, body {{
    margin: 0; padding: 0; width: 100%; height: 100%; overflow: hidden;
    background: {config.background}; color: #ccc;
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
    user-select: none; -webkit-user-select: none;
    -webkit-tap-highlight-color: transparent; touch-action: none;
  }}
  #gameCanvas {{ display: block; width: 100vw; height: 100vh; }}
  #hud {{
    position: absolute; top: 0; left: 0; right: 0;
    padding: 8px 12px; display: flex; justify-content: space-between;
    align-items: flex-start; pointer-events: none; z-index: 5; box-sizing: border-box;
  }}
  .hud-block {{
    background: rgba(10,10,10,0.78); border: 1px solid #1e1e1e; border-radius: 6px;
    padding: 4px 9px; font-size: 11px; font-weight: 700; letter-spacing: 0.6px; color: #999;
  }}
  .hud-block .label {{ color: #555; margin-right: 5px; font-weight: 600; }}
  #scoreVal {{ color: {config.accent_color}; }}
  #levelVal {{ color: #ccc; }}
  #modeVal {{ color: #888; font-size: 10px; }}
  .hearts {{ color: #ef4444; letter-spacing: 2px; }}
  .heart-empty {{ color: #2a2a2a; }}
  #overlay {{
    position: absolute; inset: 0; display: none; flex-direction: column;
    align-items: center; justify-content: center; background: rgba(0,0,0,0.88);
    z-index: 20; pointer-events: none; text-align: center; padding: 20px;
  }}
  #overlay.show {{ display: flex; }}
  #overlay-title {{
    font-size: 40px; font-weight: 800; letter-spacing: 3px;
    color: {config.accent_color}; text-shadow: 0 0 18px rgba(249,115,22,0.55);
    margin-bottom: 12px;
  }}
  #overlay-sub {{ font-size: 14px; color: #999; max-width: 480px; line-height: 1.6; }}
  #overlay-hint {{ font-size: 11px; color: #555; margin-top: 18px; letter-spacing: 1px; }}
  #dialogue {{
    position: absolute; bottom: 0; left: 0; right: 0;
    background: rgba(10,10,10,0.92); border-top: 1px solid #2a2a2a;
    padding: 14px 18px; display: none; z-index: 15;
  }}
  #dialogue.show {{ display: block; }}
  #dialogue-name {{ color: {config.accent_color}; font-weight: 700; font-size: 13px; margin-bottom: 4px; }}
  #dialogue-text {{ color: #ccc; font-size: 13px; line-height: 1.5; }}
  #mobile-controls {{
    position: absolute; bottom: 0; left: 0; right: 0; height: 120px;
    display: none; z-index: 10; pointer-events: none;
  }}
  @media (pointer: coarse) {{ #mobile-controls {{ display: flex; }} }}
  .touch-zone {{ flex: 1; pointer-events: auto; }}
</style>
</head>
<body>
<canvas id="gameCanvas"></canvas>
<div id="hud">
  <div class="hud-block">
    <span class="label">SCORE</span><span id="scoreVal">0</span>
  </div>
  <div class="hud-block">
    <span class="label">LEVEL</span><span id="levelVal">1</span>
    <span style="margin-left:10px"></span>
    <span class="label">LIVES</span><span id="livesVal" class="hearts">♥♥♥</span>
  </div>
  <div class="hud-block">
    <span class="label">MODE</span><span id="modeVal">{self._escape(config.genre.upper())}</span>
  </div>
</div>
<div id="dialogue">
  <div id="dialogue-name"></div>
  <div id="dialogue-text"></div>
</div>
<div id="mobile-controls">
  <div class="touch-zone" id="touchLeft"></div>
  <div class="touch-zone" id="touchRight"></div>
</div>
<div id="overlay">
  <div id="overlay-title"></div>
  <div id="overlay-sub"></div>
  <div id="overlay-hint">PRESS ANY KEY OR TAP TO CONTINUE</div>
</div>
<script>
// SparkLabs AI-Native Game Runtime
// Auto-generated from synthesized GameDesignDocument
(function() {{
  "use strict";

  var CONFIG = {json.dumps({
    "title": config.title, "genre": config.genre, "theme": config.theme,
    "width": config.width, "height": config.height,
    "gravity": config.gravity, "jumpStrength": config.jump_strength,
    "moveSpeed": config.move_speed, "enemySpeed": config.enemy_speed,
    "lives": config.lives, "accentColor": config.accent_color,
    "playerColor": config.player_color, "enemyColor": config.enemy_color,
    "collectibleColor": config.collectible_color, "terrainColor": config.terrain_color,
    "structureColor": config.structure_color, "npcColor": config.npc_color,
    "intro": intro, "quest": quest, "ending": ending,
    "mechanics": config.mechanics, "innovations": config.innovation_angles,
  })};
  var LEVELS = {levels_json};

  var canvas = document.getElementById('gameCanvas');
  var ctx = canvas.getContext('2d');
  var W = 0, H = 0, DPR = 1;
  function resize() {{
    DPR = window.devicePixelRatio || 1;
    W = window.innerWidth; H = window.innerHeight;
    canvas.width = W * DPR; canvas.height = H * DPR;
    canvas.style.width = W + 'px'; canvas.style.height = H + 'px';
    ctx.setTransform(DPR, 0, 0, DPR, 0, 0);
  }}
  window.addEventListener('resize', resize);
  resize();

  // Game state
  var state = 'intro'; // intro, playing, paused, won, lost, levelComplete
  var score = 0;
  var lives = CONFIG.lives;
  var levelIdx = 0;
  var currentLevel = null;
  var player = null;
  var entities = [];
  var particles = [];
  var keys = {{}};
  var touchLeft = false, touchRight = false, touchUp = false;
  var camera = {{ x: 0, y: 0 }};
  var dialogueActive = false;
{fx_header}
{fx_loop}

  // Input
  window.addEventListener('keydown', function(e) {{
    keys[e.key.toLowerCase()] = true;
    if (state === 'intro' || state === 'won' || state === 'lost') {{
      startGame();
    }} else if (e.key === 'Escape' && state === 'playing') {{
      state = 'paused';
      showOverlay('PAUSED', 'Press ESC to resume', '');
    }} else if (e.key === 'Escape' && state === 'paused') {{
      state = 'playing';
      hideOverlay();
    }}
  }});
  window.addEventListener('keyup', function(e) {{ keys[e.key.toLowerCase()] = false; }});

  // Touch controls
  var tl = document.getElementById('touchLeft');
  var tr = document.getElementById('touchRight');
  tl.addEventListener('touchstart', function(e) {{ e.preventDefault(); touchLeft = true; }});
  tl.addEventListener('touchend', function() {{ touchLeft = false; }});
  tl.addEventListener('touchstart', function(e) {{ e.preventDefault(); touchUp = true; }}, {{passive:false}});
  tr.addEventListener('touchstart', function(e) {{ e.preventDefault(); touchRight = true; if (CONFIG.jumpStrength > 0) touchUp = true; }}, {{passive:false}});
  tr.addEventListener('touchend', function() {{ touchRight = false; touchUp = false; }});

  canvas.addEventListener('pointerdown', function() {{
    if (state === 'intro' || state === 'won' || state === 'lost') startGame();
  }});

  function showOverlay(title, sub, hint) {{
    var o = document.getElementById('overlay');
    document.getElementById('overlay-title').textContent = title;
    document.getElementById('overlay-sub').textContent = sub;
    document.getElementById('overlay-hint').textContent = hint || 'PRESS ANY KEY OR TAP TO CONTINUE';
    o.classList.add('show');
  }}
  function hideOverlay() {{ document.getElementById('overlay').classList.remove('show'); }}

  function showDialogue(name, text) {{
    dialogueActive = true;
    var d = document.getElementById('dialogue');
    document.getElementById('dialogue-name').textContent = name;
    document.getElementById('dialogue-text').textContent = text;
    d.classList.add('show');
    setTimeout(function() {{
      d.classList.remove('show');
      dialogueActive = false;
    }}, 3200);
  }}

  function startGame() {{
    if (typeof initAudio === 'function') initAudio();
    if (typeof resumeAudio === 'function') resumeAudio();
    score = 0; lives = CONFIG.lives; levelIdx = 0;
    loadLevel(0);
    state = 'playing';
    hideOverlay();
  }}

  function loadLevel(idx) {{
    if (idx >= LEVELS.length) {{
      state = 'won';
      showOverlay('VICTORY', CONFIG.ending, '');
      return;
    }}
    levelIdx = idx;
    currentLevel = LEVELS[idx];
    entities = [];
    particles = [];
    camera = {{ x: 0, y: 0 }};
    for (var i = 0; i < currentLevel.entities.length; i++) {{
      var e = currentLevel.entities[i];
      var ent = {{
        id: e.id, name: e.name, type: e.type,
        x: e.x, y: e.y, w: e.w, h: e.h, color: e.color,
        vx: 0, vy: 0, onGround: false, alive: true,
        facing: 1,
        patrolOrigin: e.x, patrolRange: (e.props && e.props.patrolRange) || 0,
        patrolDir: 1, health: (e.props && e.props.health) || 1,
        isBoss: !!(e.props && e.props.boss), value: (e.props && e.props.value) || 0,
        dialogue: (e.props && e.props.dialogue) || '', role: (e.props && e.props.role) || '',
        isGoal: !!(e.props && e.props.goal), isStatic: !!(e.props && e.props.static),
        powerupKind: (e.props && e.props.powerupKind) || '',
        pairId: (e.props && e.props.pairId) || '',
        isMoving: !!(e.props && e.props.isMoving),
        moveAxis: (e.props && e.props.moveAxis) || 'x',
        moveRange: (e.props && e.props.moveRange) || 0,
        originX: e.x, originY: e.y, movePhase: 0,
        activated: false,
      }};
      if (e.type === 'player') {{
        player = ent;
      }}
      entities.push(ent);
    }}
    document.getElementById('levelVal').textContent = (idx + 1);
    if (idx === 0 && CONFIG.intro) {{
      showOverlay(currentLevel.name.toUpperCase(), CONFIG.intro, '');
      state = 'intro';
      setTimeout(function() {{ if (state === 'intro') {{ state = 'playing'; hideOverlay(); }} }}, 4000);
    }}
  }}

  function nextLevel() {{
    score += 100;
    loadLevel(levelIdx + 1);
    state = 'playing';
  }}

  function loseLife() {{
    if (typeof isInvulnerable === 'function' && isInvulnerable()) return;
    lives--;
    updateLives();
    if (typeof sfxDamage === 'function') sfxDamage();
    if (typeof spawnBurst === 'function') spawnBurst(player.x + player.w/2, player.y + player.h/2, '#ef4444', 12, 4);
    if (lives <= 0) {{
      state = 'lost';
      if (typeof sfxGameOver === 'function') sfxGameOver();
      showOverlay('GAME OVER', 'Score: ' + score, '');
    }} else {{
      if (typeof setInvulnerable === 'function') setInvulnerable(90);
      // Respawn at checkpoint if available, else level start
      if (typeof lastCheckpoint !== 'undefined' && lastCheckpoint) {{
        player.x = lastCheckpoint.x;
        player.y = lastCheckpoint.y - player.h;
        player.vx = 0; player.vy = 0;
      }} else {{
        loadLevel(levelIdx);
      }}
      state = 'playing';
    }}
  }}

  function updateLives() {{
    var el = document.getElementById('livesVal');
    var s = '';
    for (var i = 0; i < CONFIG.lives; i++) {{
      s += i < lives ? '♥' : '<span class="heart-empty">♥</span>';
    }}
    el.innerHTML = s;
  }}

  function spawnParticles(x, y, color, count) {{
    for (var i = 0; i < count; i++) {{
      var life = 30 + Math.random() * 20;
      particles.push({{
        x: x, y: y,
        vx: (Math.random() - 0.5) * 6,
        vy: (Math.random() - 0.5) * 6 - 2,
        life: life, maxLife: life,
        color: color,
        size: 2 + Math.random() * 3,
        type: 'dot'
      }});
    }}
  }}

  function update() {{
    if (state !== 'playing' || !player) return;
    if (dialogueActive) return;

    // Player input
    var left = keys['arrowleft'] || keys['a'] || touchLeft;
    var right = keys['arrowright'] || keys['d'] || touchRight;
    var up = keys['arrowup'] || keys['w'] || keys[' '] || touchUp;
    var shoot = keys['j'] || keys['k'] || keys['f'];

    if (left) {{ player.vx = -CONFIG.moveSpeed; player.facing = -1; }}
    else if (right) {{ player.vx = CONFIG.moveSpeed; player.facing = 1; }}
    else player.vx *= 0.75;

    // Speed powerup boosts movement
    if (typeof activePowerups !== 'undefined' && activePowerups.speed > 0) {{
      if (left) {{ player.vx = -CONFIG.moveSpeed * 1.6; player.facing = -1; }}
      else if (right) {{ player.vx = CONFIG.moveSpeed * 1.6; player.facing = 1; }}
    }}

    if (CONFIG.jumpStrength > 0 && up && player.onGround) {{
      player.vy = -CONFIG.jumpStrength;
      player.onGround = false;
      if (typeof sfxJump === 'function') sfxJump();
      if (typeof spawnTrail === 'function') spawnTrail(player.x + player.w/2, player.y + player.h, '#fff', 0, 2);
    }}
    // Double-jump powerup
    if (typeof activePowerups !== 'undefined' && activePowerups.doubleJump > 0 && up && !player.onGround && !player._djd) {{
      player.vy = -CONFIG.jumpStrength * 0.9;
      player._djd = true;
      if (typeof sfxJump === 'function') sfxJump();
      if (typeof spawnBurst === 'function') spawnBurst(player.x + player.w/2, player.y + player.h, '#fbbf24', 8, 3);
    }}
    if (player.onGround) player._djd = false;

    // Projectile firing
    if (shoot && typeof fireProjectile === 'function') fireProjectile();

    // Apply gravity
    if (CONFIG.gravity > 0) {{
      player.vy += CONFIG.gravity;
      if (player.vy > 16) player.vy = 16;
    }}

    // Move player X
    player.x += player.vx;
    if (player.x < 0) player.x = 0;
    if (player.x > currentLevel.width - player.w) player.x = currentLevel.width - player.w;

    // Move player Y and check platform collision
    player.y += player.vy;
    player.onGround = false;
    if (CONFIG.gravity > 0) {{
      for (var i = 0; i < entities.length; i++) {{
        var e = entities[i];
        if (!e.alive) continue;
        if (e.type !== 'terrain' && e.type !== 'structure') continue;
        if (rectOverlap(player, e)) {{
          if (player.vy > 0 && player.y < e.y) {{
            player.y = e.y - player.h;
            player.vy = 0;
            player.onGround = true;
          }} else if (player.vy < 0 && player.y > e.y) {{
            player.y = e.y + e.h;
            player.vy = 0;
          }}
        }}
      }}
      // Ground floor
      if (player.y > currentLevel.height - player.h - 40) {{
        player.y = currentLevel.height - player.h - 40;
        player.vy = 0;
        player.onGround = true;
      }}
    }}

    // Camera follows player
    camera.x = player.x - W / 2 + player.w / 2;
    camera.y = player.y - H / 2 + player.h / 2;
    if (camera.x < 0) camera.x = 0;
    if (camera.y < 0) camera.y = 0;
    if (camera.x > currentLevel.width - W) camera.x = currentLevel.width - W;
    if (camera.y > currentLevel.height - H) camera.y = currentLevel.height - H;

    // Update enemies (patrol behavior)
    for (var i = 0; i < entities.length; i++) {{
      var e = entities[i];
      if (!e.alive || e.type !== 'enemy') continue;
      if (e.patrolRange > 0) {{
        e.x += e.patrolDir * CONFIG.enemySpeed;
        if (e.x > e.patrolOrigin + e.patrolRange) e.patrolDir = -1;
        if (e.x < e.patrolOrigin - e.patrolRange) e.patrolDir = 1;
      }} else if (CONFIG.enemySpeed > 0) {{
        // Move toward player on X axis
        var dx = player.x - e.x;
        if (Math.abs(dx) > 5) e.x += Math.sign(dx) * CONFIG.enemySpeed * 0.6;
      }}
      // Enemy-player collision
      if (rectOverlap(player, e)) {{
        if (CONFIG.gravity > 0 && player.vy > 0 && player.y < e.y) {{
          // Stomp enemy
          e.alive = false;
          e.health--;
          if (e.health <= 0) {{
            if (typeof spawnBurst === 'function') spawnBurst(e.x + e.w/2, e.y + e.h/2, e.color, 14, 4);
            else spawnParticles(e.x + e.w/2, e.y + e.h/2, e.color, 12);
            score += e.isBoss ? 500 : 50;
            updateScore();
            player.vy = -CONFIG.jumpStrength * 0.7;
            if (typeof sfxStomp === 'function') sfxStomp();
          }} else {{
            e.alive = true;
          }}
        }} else if (typeof isInvulnerable === 'function' && isInvulnerable()) {{
          // Currently invulnerable — ignore damage
        }} else if (typeof activePowerups !== 'undefined' && activePowerups.shield > 0) {{
          // Shield absorbs one hit
          activePowerups.shield = 0;
          if (typeof setInvulnerable === 'function') setInvulnerable(60);
          if (typeof applyKnockback === 'function') applyKnockback(player.x < e.x ? -5 : 5, -4, 12);
          if (typeof sfxDamage === 'function') sfxDamage();
          if (typeof spawnBurst === 'function') spawnBurst(player.x + player.w/2, player.y + player.h/2, '#60a5fa', 10, 4);
        }} else {{
          // Player takes damage
          loseLife();
          return;
        }}
      }}
    }}

    // Collectibles
    for (var i = 0; i < entities.length; i++) {{
      var e = entities[i];
      if (!e.alive || e.type !== 'collectible') continue;
      if (rectOverlap(player, e)) {{
        e.alive = false;
        score += e.value || 10;
        updateScore();
        if (typeof spawnSparkles === 'function') spawnSparkles(e.x + e.w/2, e.y + e.h/2, e.color, 6);
        else spawnParticles(e.x + e.w/2, e.y + e.h/2, e.color, 8);
        if (typeof sfxCollect === 'function') sfxCollect();
      }}
    }}

    // NPC interaction
    for (var i = 0; i < entities.length; i++) {{
      var e = entities[i];
      if (!e.alive || e.type !== 'npc') continue;
      if (rectOverlap(player, e) && !dialogueActive) {{
        if (e.dialogue) {{
          showDialogue(e.name, e.dialogue);
          e.dialogue = ''; // Show once per level load
          score += 5;
          updateScore();
        }}
      }}
    }}

    // Goal trigger
    for (var i = 0; i < entities.length; i++) {{
      var e = entities[i];
      if (!e.alive || e.type !== 'trigger' || !e.isGoal) continue;
      if (rectOverlap(player, e)) {{
        e.alive = false;
        state = 'levelComplete';
        if (typeof spawnBurst === 'function') spawnBurst(e.x + e.w/2, e.y + e.h/2, e.color, 24, 6);
        else spawnParticles(e.x + e.w/2, e.y + e.h/2, e.color, 24);
        if (typeof sfxGoal === 'function') sfxGoal();
        var nextName = (levelIdx + 1 < LEVELS.length) ? LEVELS[levelIdx + 1].name : 'Victory';
        showOverlay('LEVEL CLEAR', 'Next: ' + nextName, '');
        setTimeout(function() {{ nextLevel(); }}, 1800);
        return;
      }}
    }}

    // Fall death
    if (player.y > currentLevel.height + 200) {{
      loseLife();
      return;
    }}

    // Update extension systems (particles, projectiles, powerups, etc.)
    if (typeof updateExtensions === 'function') updateExtensions();
  }}

  function rectOverlap(a, b) {{
    return a.x < b.x + b.w && a.x + a.w > b.x && a.y < b.y + b.h && a.y + a.h > b.y;
  }}

  function updateScore() {{
    document.getElementById('scoreVal').textContent = score;
  }}

  function render() {{
    ctx.fillStyle = currentLevel ? currentLevel.background : CONFIG.background || '#0a0a0a';
    ctx.fillRect(0, 0, W, H);

    if (!currentLevel || !player) return;

    ctx.save();
    ctx.translate(-camera.x, -camera.y);

    // Draw entities by type
    var terrainEnts = [], structEnts = [], collEnts = [], npcEnts = [], enemyEnts = [], triggerEnts = [];
    for (var i = 0; i < entities.length; i++) {{
      var e = entities[i];
      if (!e.alive) continue;
      if (e.type === 'terrain') terrainEnts.push(e);
      else if (e.type === 'structure') structEnts.push(e);
      else if (e.type === 'collectible') collEnts.push(e);
      else if (e.type === 'npc') npcEnts.push(e);
      else if (e.type === 'enemy') enemyEnts.push(e);
      else if (e.type === 'trigger') triggerEnts.push(e);
    }}

    // Terrain
    for (var i = 0; i < terrainEnts.length; i++) {{
      var e = terrainEnts[i];
      ctx.fillStyle = e.color;
      ctx.fillRect(e.x, e.y, e.w, e.h);
      ctx.fillStyle = 'rgba(255,255,255,0.06)';
      ctx.fillRect(e.x, e.y, e.w, 3);
    }}

    // Structures
    for (var i = 0; i < structEnts.length; i++) {{
      var e = structEnts[i];
      ctx.fillStyle = e.color;
      ctx.fillRect(e.x, e.y, e.w, e.h);
      ctx.strokeStyle = 'rgba(0,0,0,0.4)';
      ctx.lineWidth = 2;
      ctx.strokeRect(e.x, e.y, e.w, e.h);
      // Window detail
      ctx.fillStyle = 'rgba(249,115,22,0.3)';
      ctx.fillRect(e.x + e.w*0.3, e.y + e.h*0.2, e.w*0.4, e.h*0.25);
    }}

    // Collectibles (pulsing)
    var pulse = Math.sin(Date.now() / 200) * 0.3 + 0.7;
    for (var i = 0; i < collEnts.length; i++) {{
      var e = collEnts[i];
      ctx.fillStyle = e.color;
      ctx.globalAlpha = pulse;
      ctx.beginPath();
      ctx.arc(e.x + e.w/2, e.y + e.h/2, e.w/2, 0, Math.PI * 2);
      ctx.fill();
      ctx.globalAlpha = 1;
      ctx.strokeStyle = '#fff';
      ctx.lineWidth = 1;
      ctx.beginPath();
      ctx.arc(e.x + e.w/2, e.y + e.h/2, e.w/3, 0, Math.PI * 2);
      ctx.stroke();
    }}

    // NPCs
    for (var i = 0; i < npcEnts.length; i++) {{
      var e = npcEnts[i];
      ctx.fillStyle = e.color;
      ctx.fillRect(e.x, e.y, e.w, e.h);
      ctx.fillStyle = '#fff';
      ctx.font = '10px sans-serif';
      ctx.textAlign = 'center';
      ctx.fillText('!', e.x + e.w/2, e.y - 4);
    }}

    // Enemies
    for (var i = 0; i < enemyEnts.length; i++) {{
      var e = enemyEnts[i];
      ctx.fillStyle = e.color;
      ctx.fillRect(e.x, e.y, e.w, e.h);
      if (e.isBoss) {{
        ctx.strokeStyle = '#fff';
        ctx.lineWidth = 2;
        ctx.strokeRect(e.x - 2, e.y - 2, e.w + 4, e.h + 4);
        ctx.fillStyle = '#fff';
        ctx.font = 'bold 11px sans-serif';
        ctx.textAlign = 'center';
        ctx.fillText('BOSS', e.x + e.w/2, e.y - 6);
      }}
      // Eyes
      ctx.fillStyle = '#fff';
      ctx.fillRect(e.x + e.w*0.25, e.y + e.h*0.3, 3, 3);
      ctx.fillRect(e.x + e.w*0.65, e.y + e.h*0.3, 3, 3);
    }}

    // Goal trigger
    for (var i = 0; i < triggerEnts.length; i++) {{
      var e = triggerEnts[i];
      ctx.fillStyle = e.color;
      ctx.globalAlpha = 0.6 + Math.sin(Date.now() / 300) * 0.3;
      ctx.fillRect(e.x, e.y, e.w, e.h);
      ctx.globalAlpha = 1;
      ctx.fillStyle = '#fff';
      ctx.font = 'bold 10px sans-serif';
      ctx.textAlign = 'center';
      ctx.fillText('GOAL', e.x + e.w/2, e.y - 4);
    }}

    // Player
    if (player) {{
      var invFlash = (typeof isInvulnerable === 'function' && isInvulnerable()) ? (Math.floor(Date.now() / 80) % 2 === 0 ? 0.4 : 1) : 1;
      ctx.globalAlpha = invFlash;
      ctx.fillStyle = player.color;
      ctx.fillRect(player.x, player.y, player.w, player.h);
      ctx.fillStyle = '#fff';
      ctx.fillRect(player.x + player.w*0.2, player.y + player.h*0.2, 4, 4);
      ctx.fillRect(player.x + player.w*0.6, player.y + player.h*0.2, 4, 4);
      // Direction indicator
      ctx.fillStyle = typeof activePowerups !== 'undefined' && activePowerups.speed > 0 ? '#22c55e' : '#fff';
      var dirX = player.facing === -1 ? player.x : player.x + player.w - 3;
      ctx.fillRect(dirX, player.y + player.h*0.4, 3, 4);
      ctx.globalAlpha = 1;
    }}

    ctx.restore();

    // Extension rendering (particles, projectiles, powerups, etc.)
    // Rendered in screen space — extension functions subtract camera themselves.
    if (typeof renderExtensions === 'function') renderExtensions();

    // Quest text at bottom
    if (CONFIG.quest && state === 'playing') {{
      ctx.fillStyle = 'rgba(10,10,10,0.6)';
      ctx.fillRect(0, H - 24, W, 24);
      ctx.fillStyle = '#888';
      ctx.font = '11px sans-serif';
      ctx.textAlign = 'center';
      ctx.fillText(CONFIG.quest, W/2, H - 8);
    }}

    // Active powerup indicators
    if (typeof activePowerups !== 'undefined') {{
      var px = W - 10, py = 50;
      ctx.textAlign = 'right';
      ctx.font = 'bold 10px sans-serif';
      if (activePowerups.shield > 0) {{ ctx.fillStyle = '#60a5fa'; ctx.fillText('SHIELD ' + Math.ceil(activePowerups.shield / 60) + 's', px, py); py += 14; }}
      if (activePowerups.speed > 0) {{ ctx.fillStyle = '#22c55e'; ctx.fillText('SPEED ' + Math.ceil(activePowerups.speed / 60) + 's', px, py); py += 14; }}
      if (activePowerups.doubleJump > 0) {{ ctx.fillStyle = '#fbbf24'; ctx.fillText('2X JUMP ' + Math.ceil(activePowerups.doubleJump / 60) + 's', px, py); py += 14; }}
    }}
  }}

  // Main loop with fixed timestep
  var lastTime = 0;
  var accumulator = 0;
  var STEP = 1000 / 60;
  function loop(time) {{
    if (!lastTime) lastTime = time;
    var delta = time - lastTime;
    lastTime = time;
    accumulator += delta;
    while (accumulator >= STEP) {{
      update();
      accumulator -= STEP;
    }}
    render();
    requestAnimationFrame(loop);
  }}

  // Initial overlay
  updateLives();
  showOverlay(CONFIG.title.toUpperCase(), CONFIG.intro || CONFIG.quest, 'PRESS ANY KEY OR TAP TO START');
  requestAnimationFrame(loop);
}})();
</script>
</body>
</html>"""

    def _serialize_levels(self, config: GameConfig) -> str:
        """Serialize level specs into JSON for embedding."""
        levels_data = []
        for lvl in config.levels:
            levels_data.append({
                "name": lvl.name,
                "width": lvl.width,
                "height": lvl.height,
                "background": lvl.background,
                "objective": lvl.objective,
                "timeLimit": lvl.time_limit,
                "difficulty": lvl.difficulty,
                "entities": [
                    {
                        "id": e.entity_id,
                        "name": e.name,
                        "type": e.entity_type,
                        "x": round(e.x, 1),
                        "y": round(e.y, 1),
                        "w": e.width,
                        "h": e.height,
                        "color": e.color,
                        "props": e.properties,
                    }
                    for e in lvl.entities
                ],
            })
        return json.dumps(levels_data)

    def _escape(self, text: str) -> str:
        """Escape text for safe embedding in HTML/JS."""
        if not text:
            return ""
        return (
            str(text)
            .replace("\\", "\\\\")
            .replace('"', '\\"')
            .replace("\n", " ")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
        )


# =============================================================================
# Game Runtime - main entry point
# =============================================================================


class GameRuntime:
    """
    The main game runtime that transforms synthesized game content
    into playable HTML5 games.

    Acts as the production layer between content synthesis (GameContentSynthesizer)
    and the browser player (GameRunner iframe). Produces self-contained HTML
    documents that run entirely client-side.
    """

    _instance: Optional["GameRuntime"] = None
    _instance_lock = threading.RLock()

    def __init__(self) -> None:
        if GameRuntime._instance is not None:
            raise RuntimeError("Use GameRuntime.get_instance()")
        self._compiler = ConceptCompiler()
        self._assembler = HtmlAssembler()
        self._build_count: int = 0
        self._lock = threading.RLock()

    @classmethod
    def get_instance(cls) -> "GameRuntime":
        if cls._instance is None:
            with cls._instance_lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def build_from_gdd(self, gdd: Any) -> RuntimeResult:
        """
        Build a complete playable HTML game from a GameDesignDocument.

        Args:
            gdd: A GameDesignDocument from the GameContentSynthesizer

        Returns:
            RuntimeResult with the HTML and metadata
        """
        start = time.time()
        try:
            with self._lock:
                self._build_count += 1

            config = self._compiler.compile(gdd)
            html = self._assembler.assemble(config)
            duration = time.time() - start

            return RuntimeResult(
                success=True,
                html=html,
                config=config,
                error=None,
                duration_s=round(duration, 3),
                metadata={
                    "title": config.title,
                    "genre": config.genre,
                    "level_count": len(config.levels),
                    "entity_count": sum(len(lvl.entities) for lvl in config.levels),
                    "build_number": self._build_count,
                },
            )
        except Exception as exc:
            logger.exception("GameRuntime build failed: %s", exc)
            return RuntimeResult(
                success=False,
                html="",
                config=None,
                error=str(exc),
                duration_s=round(time.time() - start, 3),
                metadata={},
            )

    def build_from_prompt(self, prompt: str, genre_hint: Optional[str] = None) -> RuntimeResult:
        """
        Convenience: synthesize content from a prompt and build the game.

        Args:
            prompt: Natural-language game description
            genre_hint: Optional genre hint

        Returns:
            RuntimeResult with the HTML and metadata
        """
        try:
            from sparkai.agent.agent_game_content_synthesizer import get_content_synthesizer
            synthesizer = get_content_synthesizer()
            synth_result = synthesizer.synthesize(prompt, genre_hint=genre_hint)
            if not synth_result.success or synth_result.gdd is None:
                return RuntimeResult(
                    success=False,
                    html="",
                    config=None,
                    error=synth_result.error or "Content synthesis failed",
                    duration_s=0.0,
                    metadata={"synthesis_warnings": synth_result.warnings},
                )
            runtime_result = self.build_from_gdd(synth_result.gdd)
            runtime_result.metadata["synthesis_result_id"] = synth_result.result_id
            runtime_result.metadata["synthesis_warnings"] = synth_result.warnings
            runtime_result.metadata["quality_score"] = synth_result.gdd.quality_score
            return runtime_result
        except Exception as exc:
            logger.exception("GameRuntime build_from_prompt failed: %s", exc)
            return RuntimeResult(
                success=False,
                html="",
                config=None,
                error=str(exc),
                duration_s=0.0,
                metadata={},
            )

    def get_status(self) -> Dict[str, Any]:
        """Return runtime status information."""
        return {
            "status": "ready",
            "builds_completed": self._build_count,
            "supported_genres": list(ConceptCompiler.GENRE_TUNING.keys()),
        }


def get_game_runtime() -> GameRuntime:
    """Convenience function to access the singleton GameRuntime."""
    return GameRuntime.get_instance()
