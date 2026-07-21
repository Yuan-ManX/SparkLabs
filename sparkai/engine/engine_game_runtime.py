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
from sparkai.engine.engine_game_features import FeatureInjector, FeatureConfig
from sparkai.engine.engine_game_polish import PolishInjector, PolishConfig
from sparkai.engine.engine_game_assets import GenreAssetProfile, get_dom_overlay_html
from sparkai.engine.engine_game_bridge_client import BridgeClientBuilder

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
        "parkour": {
            "gravity": 0.65, "jump_strength": 12.5, "move_speed": 6.0,
            "enemy_speed": 0.0, "background": "#0a0e1a", "accent": "#00e5ff",
            "player_color": "#00e5ff", "enemy_color": "#ef4444",
            "collectible_color": "#ff00ff", "terrain_color": "#1e3a5f",
            "structure_color": "#00e5ff", "npc_color": "#c084fc",
            "collectibles": 6, "enemies": 0, "npcs": 0, "lives": 3,
        },
        "tank_battle": {
            "gravity": 0.0, "jump_strength": 0.0, "move_speed": 2.5,
            "enemy_speed": 1.2, "background": "#000000", "accent": "#fbbf24",
            "player_color": "#fbbf24", "enemy_color": "#94a3b8",
            "collectible_color": "#22c55e", "terrain_color": "#8b4513",
            "structure_color": "#64748b", "npc_color": "#c084fc",
            "collectibles": 0, "enemies": 4, "npcs": 0, "lives": 3,
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
            # Vertical walls for wall-slide/wall-jump (parkour & platformer)
            # Tall thin terrain lets the player slide along the side and kick off.
            # Walls sit on the ground and are short enough to reach by jumping.
            if genre in ("parkour", "platformer"):
                wall_count = 3 + level_idx
                wall_h = 150.0  # reachable: jump peak ~120px above ground
                for i in range(wall_count):
                    # Space walls between platforms, offset from platform centers
                    wx = 240 + i * ((world_w - 400) / max(1, wall_count)) + rng.randint(-30, 30)
                    wy = float(world_h - 40 - wall_h)  # bottom rests on ground
                    entities.append(GameEntitySpec(
                        entity_id=f"wall_{i}",
                        name=f"Wall {i + 1}",
                        entity_type="terrain",
                        x=float(wx), y=wy,
                        width=28.0, height=wall_h,
                        color=tuning["terrain_color"],
                        properties={"static": True, "wall": True},
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

    # Genre to visual rendering style mapping. Each style controls how the
    # player, enemies, and collectibles are drawn on the canvas, giving each
    # game type a distinct visual identity.
    GENRE_STYLE_MAP: Dict[str, str] = {
        "platformer": "humanoid",
        "boss_battle": "humanoid",
        "survival": "humanoid",
        "sandbox": "humanoid",
        "exploration": "humanoid",
        "shooter": "ship",
        "parkour": "ship",
        "racing": "ship",
        "puzzle": "orb",
        "music": "orb",
        "rpg": "humanoid",
        "dungeon_crawler": "humanoid",
        "top_down_adventure": "isometric",
        "narrative": "humanoid",
        "strategy": "isometric",
        "tank_battle": "tank",
        "custom": "humanoid",
    }

    def __init__(self) -> None:
        self._fx = FxInjector(ExtensionConfig())
        self._features = FeatureInjector(FeatureConfig())
        self._polish = PolishInjector(PolishConfig())

    def _get_genre_style(self, genre: str) -> str:
        """Return the visual rendering style for a given genre."""
        return self.GENRE_STYLE_MAP.get(genre, "humanoid")

    def assemble(self, config: GameConfig) -> str:
        """Produce a complete, self-contained HTML game document."""
        levels_json = self._serialize_levels(config)
        intro = self._escape(config.narrative_intro)
        quest = self._escape(config.quest_summary)
        fx_header = self._fx.build_header_js()
        fx_loop = self._fx.build_loop_patch_js()
        feature_header = self._features.build_header_js()
        feature_loop = self._features.build_loop_patch_js()
        feature_init = self._features.build_init_call_js()
        polish_header = self._polish.build_header_js()
        polish_loop = self._polish.build_loop_patch_js()
        polish_init = self._polish.build_init_call_js()
        ending = self._escape(config.ending_text)

        # Per-genre asset profile (audio + visual + effects overrides)
        asset_profile = GenreAssetProfile(config.genre, config)
        genre_css = asset_profile.build_css()
        genre_audio_js = asset_profile.build_audio_overrides()
        genre_effects_js = asset_profile.build_effect_overrides()
        genre_post_process_js = asset_profile.build_post_process_js()
        genre_dom_overlay = get_dom_overlay_html(config.genre)

        # AI-Native Game Bridge client script for live cognitive adaptation
        bridge_script = BridgeClientBuilder.build_script(
            bridge_url="http://localhost:8000/api/agent/game-bridge",
            telemetry_interval=30,
            directive_interval=60,
        )

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
{genre_css}
</style>
</head>
<body>
<canvas id="gameCanvas"></canvas>
{genre_dom_overlay}
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
    "genreStyle": self._get_genre_style(config.genre),
    "width": config.width, "height": config.height,
    "gravity": config.gravity, "jumpStrength": config.jump_strength,
    "moveSpeed": config.move_speed, "enemySpeed": config.enemy_speed,
    "lives": config.lives, "accentColor": config.accent_color,
    "playerColor": config.player_color, "enemyColor": config.enemy_color,
    "collectibleColor": config.collectible_color, "terrainColor": config.terrain_color,
    "structureColor": config.structure_color, "npcColor": config.npc_color,
    "intro": intro, "quest": quest, "ending": ending,
    "mechanics": config.mechanics, "innovations": config.innovation_angles,
    "canDoubleJump": config.genre in ("platformer", "boss_battle", "sandbox", "survival"),
    "canWallJump": config.genre in ("parkour", "platformer"),
    "bossPhases": config.genre in ("boss_battle", "shooter"),
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
  var keysJustPressed = {{}}; // edge-detected: true for one frame after keydown
  var touchLeft = false, touchRight = false, touchUp = false, touchUpJustPressed = false;
  var camera = {{ x: 0, y: 0 }};
  var dialogueActive = false;
  var lastCheckpoint = null; // Respawn position set by checkpoint triggers
  // Game-feel timers (frames @ 60 FPS)
  var coyoteTimer = 0;      // grace period after leaving ledge to still jump
  var jumpBufferTimer = 0;  // jump pressed shortly before landing executes on land
  var hitStopTimer = 0;     // freeze update logic for heavy impacts
  var COYOTE_FRAMES = 6;
  var JUMP_BUFFER_FRAMES = 6;
  // Genre-specific mechanic state
  var jumpsRemaining = 0;   // double-jump counter (reset on landing)
  var maxJumps = CONFIG.canDoubleJump ? 2 : 1;
  var isWallSliding = false; // true when touching wall while falling
  var wallJumpLock = 0;     // frames to lock horizontal input after wall-jump

  // Expose game state for AI Event Sheet runtime evaluation
  window.gameState = {{ score: 0, lives: CONFIG.lives, level: 1, state: 'intro', health: CONFIG.lives, enemies: 0, combo: 0, multiplier: 1 }};
{fx_header}
{fx_loop}
{feature_header}
{feature_loop}
{polish_header}
{polish_loop}

  // ===== Per-Genre Asset Profile Overrides =====
  // Audio overrides: redefine sfx* functions with genre-specific sound palettes.
  // Runs AFTER base AudioSynth definitions so reassignment cleanly replaces defaults.
{genre_audio_js}
  // Effect overrides: redefine particle spawn functions per genre identity.
{genre_effects_js}
  // Post-process: per-frame canvas filter applied after scene render.
{genre_post_process_js}

  // Enemy projectile system (used by boss phase attacks)
  var enemyProjectiles = [];
  function fireEnemyProjectile(sx, sy, tx, ty) {{
    var dx = tx - sx, dy = ty - sy;
    var dist = Math.sqrt(dx*dx + dy*dy) || 1;
    var speed = 4.5;
    enemyProjectiles.push({{ x: sx, y: sy, vx: dx/dist * speed, vy: dy/dist * speed, life: 120, w: 8, h: 8, color: '#ff4444' }});
  }}
  function updateEnemyProjectiles() {{
    for (var i = enemyProjectiles.length - 1; i >= 0; i--) {{
      var p = enemyProjectiles[i];
      p.x += p.vx; p.y += p.vy; p.life--;
      if (p.life <= 0) {{ enemyProjectiles.splice(i, 1); continue; }}
      // Hit player
      if (typeof player !== 'undefined' && player && p.x < player.x + player.w && p.x + p.w > player.x && p.y < player.y + player.h && p.y + p.h > player.y) {{
        enemyProjectiles.splice(i, 1);
        if (typeof damagePlayer === 'function') damagePlayer();
      }}
    }}
  }}
  function renderEnemyProjectiles() {{
    for (var i = 0; i < enemyProjectiles.length; i++) {{
      var p = enemyProjectiles[i];
      ctx.fillStyle = p.color;
      ctx.beginPath();
      ctx.arc(p.x, p.y, p.w/2, 0, Math.PI * 2);
      ctx.fill();
      ctx.fillStyle = 'rgba(255,80,80,0.4)';
      ctx.beginPath();
      ctx.arc(p.x, p.y, p.w, 0, Math.PI * 2);
      ctx.fill();
    }}
  }}

  // Tank battle: 4-directional shooting and destructible walls
  if (CONFIG.genre === 'tank_battle') {{
    // Override projectile firing to shoot in tankDir (4 directions)
    var _origFireProjectile = (typeof fireProjectile === 'function') ? fireProjectile : null;
    fireProjectile = function() {{
      if (projectileCooldown > 0) return;
      var dx = 0, dy = 0;
      var dir = player.tankDir || 'up';
      if (dir === 'up') {{ dy = -1; }}
      else if (dir === 'down') {{ dy = 1; }}
      else if (dir === 'left') {{ dx = -1; }}
      else {{ dx = 1; }}
      projectiles.push({{
        x: player.x + player.w/2, y: player.y + player.h/2,
        vx: dx * 8, vy: dy * 8,
        w: 6, h: 6, life: 80, color: CONFIG.playerColor
      }});
      projectileCooldown = 20;
      if (typeof sfxShoot === 'function') sfxShoot();
      // Cannon smoke puff at muzzle (genre-specific effect)
      if (typeof spawnCannonSmoke === 'function') {{
        spawnCannonSmoke(player.x + player.w/2 + dx * 12, player.y + player.h/2 + dy * 12, dir);
      }}
    }};
    // Check projectile hits on destructible walls (brick terrain)
    function checkProjectileWallHits() {{
      for (var i = projectiles.length - 1; i >= 0; i--) {{
        var p = projectiles[i];
        for (var j = 0; j < entities.length; j++) {{
          var w = entities[j];
          if (!w.alive || w.type !== 'terrain') continue;
          if (p.x < w.x + w.w && p.x + p.w > w.x && p.y < w.y + w.h && p.y + p.h > w.y) {{
            // Hit destructible wall
            w.wallHp = (w.wallHp !== undefined) ? w.wallHp - 1 : 0;
            if (w.wallHp <= 0) {{
              w.alive = false;
              if (typeof spawnBurst === 'function') spawnBurst(w.x + w.w/2, w.y + w.h/2, w.color, 8, 3);
              else spawnParticles(w.x + w.w/2, w.y + w.h/2, w.color, 6);
            }}
            projectiles.splice(i, 1);
            break;
          }}
        }}
      }}
    }}
  }}

  // Input - edge detection tracks justPressed for one frame
  var JUMP_KEYS = ['arrowup', 'w', ' '];
  function isJumpKey(k) {{ return JUMP_KEYS.indexOf(k) >= 0; }}
  window.addEventListener('keydown', function(e) {{
    var k = e.key.toLowerCase();
    if (!keys[k]) keysJustPressed[k] = true; // only flag on fresh press (not auto-repeat)
    keys[k] = true;
    // Feed jump buffer when jump key is freshly pressed during play
    if (state === 'playing' && isJumpKey(k)) {{
      jumpBufferTimer = JUMP_BUFFER_FRAMES;
    }}
    if (state === 'intro' || state === 'won' || state === 'lost') {{
      startGame();
    }} else if (e.key === 'Escape' && state === 'playing') {{
      state = 'paused';
      showOverlay('PAUSED', 'Press ESC to resume', '');
    }} else if (e.key === 'Escape' && state === 'paused') {{
      state = 'playing';
      hideOverlay();
    }} else if (k === 'm' && typeof toggleAudio === 'function') {{
      toggleAudio();
    }} else if (k === 'r' && state === 'paused' && typeof restartGame === 'function') {{
      restartGame();
    }} else if (e.key === 'Tab' && state === 'playing' && typeof toggleSettings === 'function') {{
      e.preventDefault();
      toggleSettings();
    }} else if (e.key === 'Tab' && state === 'paused' && typeof toggleSettings === 'function') {{
      e.preventDefault();
      toggleSettings();
    }}
  }});
  window.addEventListener('keyup', function(e) {{ keys[e.key.toLowerCase()] = false; }});

  // Touch controls - feed jump buffer on fresh tap
  var tl = document.getElementById('touchLeft');
  var tr = document.getElementById('touchRight');
  tl.addEventListener('touchstart', function(e) {{ e.preventDefault(); touchLeft = true; }});
  tl.addEventListener('touchend', function() {{ touchLeft = false; }});
  tl.addEventListener('touchstart', function(e) {{ e.preventDefault(); touchUp = true; touchUpJustPressed = true; if (state === 'playing') jumpBufferTimer = JUMP_BUFFER_FRAMES; }}, {{passive:false}});
  tr.addEventListener('touchstart', function(e) {{ e.preventDefault(); touchRight = true; if (CONFIG.jumpStrength > 0) {{ touchUp = true; touchUpJustPressed = true; if (state === 'playing') jumpBufferTimer = JUMP_BUFFER_FRAMES; }} }}, {{passive:false}});
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
    {feature_init}
    {polish_init}
    state = 'playing';
    hideOverlay();
    // Initialize AI-Native Game Bridge connection for live cognitive adaptation
    if (typeof window.initBridge === 'function') {{
      window.initBridge('http://localhost:8000/api/agent/game-bridge', CONFIG.title, CONFIG.genre);
    }}
  }}

  // Action helpers for AI Event Sheet runtime
  function spawnEntity(typeName) {{
    if (!player || !currentLevel) return;
    var sx = player.x + (Math.random() - 0.5) * 200;
    var sy = player.y - 80;
    var ent = {{ x: sx, y: sy, w: 24, h: 24, vx: 0, vy: 0, type: 'enemy', color: CONFIG.enemyColor, facing: -1, onGround: false, hp: 1, points: 100, animPhase: Math.random() * 6.28 }};
    if (typeName && typeName.indexOf('collect') >= 0) {{
      ent.type = 'collectible'; ent.color = CONFIG.collectibleColor; ent.points = 50;
    }} else if (typeName && typeName.indexOf('potion') >= 0) {{
      ent.type = 'collectible'; ent.color = '#22c55e'; ent.points = 0; ent.heals = true;
    }}
    entities.push(ent);
  }}

  function playSound(name) {{
    try {{
      var ctx = window._slAudioCtx || (window._slAudioCtx = new (window.AudioContext || window.webkitAudioContext)());
      var osc = ctx.createOscillator();
      var gain = ctx.createGain();
      osc.connect(gain); gain.connect(ctx.destination);
      osc.frequency.value = (name && name.indexOf('warn') >= 0) ? 220 : 440;
      osc.type = 'square';
      gain.gain.setValueAtTime(0.15, ctx.currentTime);
      gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 0.3);
      osc.start(ctx.currentTime);
      osc.stop(ctx.currentTime + 0.3);
    }} catch(e) {{}}
  }}

  function moveEntity(target, destination) {{
    if (!player || !target) return;
    if (target === 'player' || target.indexOf('player') >= 0) {{
      if (destination === 'start') {{ player.x = 50; player.y = 100; }}
    }}
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
    lastCheckpoint = null; // Reset checkpoint on level load
    if (typeof generateTilemapForLevel === 'function') generateTilemapForLevel(idx);
    if (typeof levelStartTime !== 'undefined') levelStartTime = Date.now();
    if (typeof deathlessLevel !== 'undefined') deathlessLevel = true;
    for (var i = 0; i < currentLevel.entities.length; i++) {{
      var e = currentLevel.entities[i];
      var ent = {{
        id: e.id, name: e.name, type: e.type,
        x: e.x, y: e.y, w: e.w, h: e.h, color: e.color,
        vx: 0, vy: 0, onGround: false, alive: true,
        facing: 1, tankDir: 'up',
        patrolOrigin: e.x, patrolRange: (e.props && e.props.patrolRange) || 0,
        patrolDir: 1, health: (e.props && e.props.health) || 1,
        isBoss: !!(e.props && e.props.boss), value: (e.props && e.props.value) || 0,
        dialogue: (e.props && e.props.dialogue) || '', role: (e.props && e.props.role) || '',
        isGoal: !!(e.props && e.props.goal),
        isCheckpoint: !!(e.props && e.props.checkpoint),
        isStatic: !!(e.props && e.props.static),
        powerupKind: (e.props && e.props.powerupKind) || '',
        pairId: (e.props && e.props.pairId) || '',
        isMoving: !!(e.props && e.props.isMoving),
        moveAxis: (e.props && e.props.moveAxis) || 'x',
        moveRange: (e.props && e.props.moveRange) || 0,
        originX: e.x, originY: e.y, movePhase: 0,
        activated: false,
        wallHp: (e.type === 'terrain') ? 2 : 0, // Destructible brick walls (2 hits)
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
    var nextIdx = levelIdx + 1;
    if (typeof showTransition === 'function' && nextIdx < LEVELS.length) {{
      var lvlName = (LEVELS[nextIdx] && LEVELS[nextIdx].name) ? LEVELS[nextIdx].name : ('LEVEL ' + (nextIdx + 1));
      showTransition(lvlName);
    }}
    loadLevel(nextIdx);
    state = 'playing';
  }}

  function loseLife() {{
    if (typeof isInvulnerable === 'function' && isInvulnerable()) return;
    lives--;
    if (typeof window.trackBridgeEvent === 'function') window.trackBridgeEvent('death');
    updateLives();
    if (typeof sfxDamage === 'function') sfxDamage();
    if (typeof triggerShake === 'function') triggerShake(8);
    // Hit-stop on player damage for impact emphasis
    hitStopTimer = 6;
    if (typeof deathlessLevel !== 'undefined') deathlessLevel = false;
    if (typeof deathlessRun !== 'undefined') deathlessRun = false;
    if (typeof resetCombo === 'function') resetCombo();
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

  function spawnParticles(x, y, color, count, particleType) {{
    // particleType: 'dot' (default), 'spark', 'star', 'ring'
    var ptype = particleType || 'dot';
    for (var i = 0; i < count; i++) {{
      var life = 30 + Math.random() * 20;
      var angle = Math.random() * Math.PI * 2;
      var speed = 2 + Math.random() * 4;
      particles.push({{
        x: x, y: y,
        vx: ptype === 'spark' ? Math.cos(angle) * speed * 1.5 : (Math.random() - 0.5) * 6,
        vy: ptype === 'spark' ? Math.sin(angle) * speed * 1.5 - 1 : (Math.random() - 0.5) * 6 - 2,
        life: life, maxLife: life,
        color: color,
        size: ptype === 'star' ? 3 + Math.random() * 4 : 2 + Math.random() * 3,
        type: ptype,
        rotation: Math.random() * Math.PI * 2,
        rotSpeed: (Math.random() - 0.5) * 0.3,
        gravity: ptype === 'spark' ? 0.15 : 0.08,
      }});
    }}
  }}

  function updateParticles() {{
    for (var i = particles.length - 1; i >= 0; i--) {{
      var p = particles[i];
      p.x += p.vx;
      p.y += p.vy;
      p.vy += p.gravity;
      p.vx *= 0.97;
      p.rotation += p.rotSpeed;
      p.life--;
      if (p.life <= 0) particles.splice(i, 1);
    }}
  }}

  function renderParticles() {{
    // Rendered in world space (inside camera translate)
    for (var i = 0; i < particles.length; i++) {{
      var p = particles[i];
      var alpha = p.life / p.maxLife;
      ctx.globalAlpha = alpha;
      ctx.fillStyle = p.color;
      if (p.type === 'star') {{
        ctx.save();
        ctx.translate(p.x, p.y);
        ctx.rotate(p.rotation);
        ctx.beginPath();
        for (var s = 0; s < 5; s++) {{
          var a = (s / 5) * Math.PI * 2 - Math.PI / 2;
          var r = s % 2 === 0 ? p.size : p.size * 0.4;
          if (s === 0) ctx.moveTo(Math.cos(a) * r, Math.sin(a) * r);
          else ctx.lineTo(Math.cos(a) * r, Math.sin(a) * r);
        }}
        ctx.closePath();
        ctx.fill();
        ctx.restore();
      }} else if (p.type === 'ring') {{
        ctx.strokeStyle = p.color;
        ctx.lineWidth = 2;
        ctx.beginPath();
        ctx.arc(p.x, p.y, p.size * (1 + (1 - alpha) * 2), 0, Math.PI * 2);
        ctx.stroke();
      }} else if (p.type === 'spark') {{
        ctx.save();
        ctx.translate(p.x, p.y);
        ctx.rotate(Math.atan2(p.vy, p.vx));
        ctx.fillRect(-p.size, -1, p.size * 2, 2);
        ctx.restore();
      }} else {{
        // dot
        ctx.beginPath();
        ctx.arc(p.x, p.y, p.size * alpha, 0, Math.PI * 2);
        ctx.fill();
      }}
    }}
    ctx.globalAlpha = 1;
  }}

  function update() {{
    if (state !== 'playing' || !player) return;
    if (dialogueActive) return;
    // Hit-stop: freeze gameplay logic briefly on heavy impacts for game feel
    if (hitStopTimer > 0) {{
      hitStopTimer--;
      return;
    }}

    // Sync game state for AI Event Sheet runtime
    window.gameState.score = score;
    window.gameState.lives = lives;
    window.gameState.level = levelIdx + 1;
    window.gameState.state = state;
    window.gameState.health = lives;
    window.gameState.enemies = entities.filter(function(e) {{ return e.type === 'enemy'; }}).length;
    if (typeof combo !== 'undefined') window.gameState.combo = combo;
    if (typeof multiplier !== 'undefined') window.gameState.multiplier = multiplier;

    // Player input
    var left = keys['arrowleft'] || keys['a'] || touchLeft;
    var right = keys['arrowright'] || keys['d'] || touchRight;
    var up = keys['arrowup'] || keys['w'] || keys[' '] || touchUp;
    var shoot = keys['j'] || keys['k'] || keys['f'];

    // Wall-jump input lock: preserve horizontal velocity during lock so the
    // wall-jump push is not immediately overridden by held direction input.
    if (wallJumpLock > 0) {{
      wallJumpLock--;
      // Skip horizontal input override; keep wall-jump's outbound velocity.
    }} else {{
      if (left) {{ player.vx = -CONFIG.moveSpeed; player.facing = -1; }}
      else if (right) {{ player.vx = CONFIG.moveSpeed; player.facing = 1; }}
      else player.vx *= 0.75;
    }}

    // Tank battle: 4-directional movement with directional facing
    if (CONFIG.genre === 'tank_battle') {{
      var downKey = keys['arrowdown'] || keys['s'];
      if (left) {{ player.vx = -CONFIG.moveSpeed; player.facing = -1; player.tankDir = 'left'; player.vy = 0; }}
      else if (right) {{ player.vx = CONFIG.moveSpeed; player.facing = 1; player.tankDir = 'right'; player.vy = 0; }}
      else if (up) {{ player.vy = -CONFIG.moveSpeed; player.tankDir = 'up'; player.vx = 0; }}
      else if (downKey) {{ player.vy = CONFIG.moveSpeed; player.tankDir = 'down'; player.vx = 0; }}
      else {{ player.vx *= 0.5; player.vy *= 0.5; }}
    }}

    // Speed powerup boosts movement
    if (typeof activePowerups !== 'undefined' && activePowerups.speed > 0) {{
      if (left) {{ player.vx = -CONFIG.moveSpeed * 1.6; player.facing = -1; }}
      else if (right) {{ player.vx = CONFIG.moveSpeed * 1.6; player.facing = 1; }}
    }}

    if (CONFIG.jumpStrength > 0) {{
      // Coyote time: refresh timer while grounded, decay once airborne
      if (player.onGround) {{
        coyoteTimer = COYOTE_FRAMES;
        jumpsRemaining = maxJumps; // Reset double-jump on landing
      }} else if (coyoteTimer > 0) {{
        coyoteTimer--;
      }}
      // Jump buffer: consume on landing or use with coyote time
      if (jumpBufferTimer > 0 && coyoteTimer > 0) {{
        player.vy = -CONFIG.jumpStrength;
        player.onGround = false;
        coyoteTimer = 0;
        jumpBufferTimer = 0;
        jumpsRemaining = maxJumps - 1;
        if (typeof sfxJump === 'function') sfxJump();
        if (typeof window.trackBridgeEvent === 'function') window.trackBridgeEvent('jump');
        if (typeof spawnTrail === 'function') spawnTrail(player.x + player.w/2, player.y + player.h, '#fff', 0, 2);
      }}
    }}
    // Airborne jump: wall-jump takes priority over double-jump when wall-sliding,
    // so the two never fire in the same frame (avoids wasted double-jump charges
    // and conflicting horizontal velocities).
    var jumpPressedNow = jumpBufferTimer > 0 || touchUpJustPressed;
    if (jumpPressedNow && !player.onGround) {{
      if (CONFIG.canWallJump && isWallSliding) {{
        // Wall-jump: kick off wall for parkour/platformer genres
        player.vy = -CONFIG.jumpStrength * 0.9;
        player.vx = player.facing * -CONFIG.moveSpeed * 1.4; // Push away from wall
        wallJumpLock = 10;
        jumpBufferTimer = 0;
        jumpsRemaining = maxJumps - 1;
        if (typeof window.trackBridgeEvent === 'function') window.trackBridgeEvent('wall_jump');
        isWallSliding = false;
        if (typeof sfxJump === 'function') sfxJump();
        if (typeof spawnBurst === 'function') spawnBurst(player.x + player.w/2, player.y + player.h/2, '#00e5ff', 10, 4);
      }} else if (CONFIG.canDoubleJump && jumpsRemaining > 0) {{
        // Double-jump: core mechanic for platformer/boss/sandbox genres
        player.vy = -CONFIG.jumpStrength * 0.85;
        jumpsRemaining--;
        jumpBufferTimer = 0;
        if (typeof sfxJump === 'function') sfxJump();
        if (typeof spawnBurst === 'function') spawnBurst(player.x + player.w/2, player.y + player.h, CONFIG.accentColor, 8, 3);
      }}
    }}
    touchUpJustPressed = false;

    // Projectile firing
    if (shoot && typeof fireProjectile === 'function') fireProjectile();

    // Apply gravity (wall-slide reduces fall speed for parkour/platformer)
    if (CONFIG.gravity > 0) {{
      if (CONFIG.canWallJump && isWallSliding && player.vy > 2) {{
        player.vy += CONFIG.gravity * 0.3; // Slow descent while wall-sliding
      }} else {{
        player.vy += CONFIG.gravity;
      }}
      if (player.vy > 16) player.vy = 16;
    }}

    // Move player X with wall collision detection
    isWallSliding = false;
    player.x += player.vx;
    if (player.x < 0) player.x = 0;
    if (player.x > currentLevel.width - player.w) player.x = currentLevel.width - player.w;
    // X-axis wall collision for ALL gravity>0 games (push player out of walls).
    // Wall-slide detection is layered on top for canWallJump games when airborne.
    if (CONFIG.gravity > 0) {{
      for (var wi = 0; wi < entities.length; wi++) {{
        var we = entities[wi];
        if (!we.alive) continue;
        if (we.type !== 'terrain' && we.type !== 'structure') continue;
        if (rectOverlap(player, we)) {{
          if (player.vx > 0) {{
            player.x = we.x - player.w;
            if (CONFIG.canWallJump && !player.onGround) isWallSliding = true;
          }} else if (player.vx < 0) {{
            player.x = we.x + we.w;
            if (CONFIG.canWallJump && !player.onGround) isWallSliding = true;
          }}
        }}
      }}
    }}

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
    // Tank battle: Y-axis wall collision (top-down view, no gravity)
    if (CONFIG.genre === 'tank_battle') {{
      for (var ti = 0; ti < entities.length; ti++) {{
        var te = entities[ti];
        if (!te.alive) continue;
        if (te.type !== 'terrain' && te.type !== 'structure') continue;
        if (rectOverlap(player, te)) {{
          if (player.vy > 0) {{ player.y = te.y - player.h; player.vy = 0; }}
          else if (player.vy < 0) {{ player.y = te.y + te.h; player.vy = 0; }}
        }}
      }}
      // Clamp to level bounds
      if (player.y < 0) {{ player.y = 0; player.vy = 0; }}
      if (player.y > currentLevel.height - player.h) {{ player.y = currentLevel.height - player.h; player.vy = 0; }}
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
      // Boss phases: escalate aggression as HP drops
      if (e.isBoss && CONFIG.bossPhases) {{
        var bossMaxHp = 3;
        var hpRatio = e.health / bossMaxHp;
        var newPhase = hpRatio < 0.34 ? 3 : (hpRatio < 0.67 ? 2 : 1);
        if (newPhase === 3) {{
          // Phase 3: enraged - fast, red glow, lunges at player
          e.color = '#dc2626';
          e.patrolDir = (player.x < e.x) ? -1 : 1;
          e.x += e.patrolDir * CONFIG.enemySpeed * 1.8;
        }} else if (newPhase === 2) {{
          // Phase 2: aggressive - faster, orange tint
          e.color = '#f97316';
          e.x += Math.sign(player.x - e.x) * CONFIG.enemySpeed * 1.3;
        }} else {{
          // Phase 1: cautious - normal patrol
          e.color = CONFIG.enemyColor;
        }}
        // Trigger phase-change shockwave once on transition (epic effect)
        if (typeof e.lastBossPhase === 'undefined') e.lastBossPhase = newPhase;
        if (e.lastBossPhase !== newPhase) {{
          if (typeof spawnPhaseChange === 'function') {{
            spawnPhaseChange(e.x + e.w/2, e.y + e.h/2);
          }} else if (typeof spawnBurst === 'function') {{
            spawnBurst(e.x + e.w/2, e.y + e.h/2, e.color, 12, 5);
          }}
          e.lastBossPhase = newPhase;
        }}
        // Boss fires projectiles in later phases
        if (hpRatio < 0.67 && typeof fireEnemyProjectile === 'function' && Math.random() < 0.02) {{
          fireEnemyProjectile(e.x + e.w/2, e.y + e.h/2, player.x + player.w/2, player.y + player.h/2);
        }}
      }} else if (CONFIG.genre === 'tank_battle') {{
        // Tank enemies: chase player on both axes and shoot
        var tdx = player.x - e.x, tdy = player.y - e.y;
        if (Math.abs(tdx) > Math.abs(tdy)) {{
          e.x += Math.sign(tdx) * CONFIG.enemySpeed;
        }} else {{
          e.y += Math.sign(tdy) * CONFIG.enemySpeed;
        }}
        // Enemy tank shoots at player
        if (typeof fireEnemyProjectile === 'function' && Math.random() < 0.008) {{
          fireEnemyProjectile(e.x + e.w/2, e.y + e.h/2, player.x + player.w/2, player.y + player.h/2);
        }}
        // Clamp enemy to level bounds
        if (e.x < 0) e.x = 0;
        if (e.x > currentLevel.width - e.w) e.x = currentLevel.width - e.w;
        if (e.y < 0) e.y = 0;
        if (e.y > currentLevel.height - e.h) e.y = currentLevel.height - e.h;
      }} else if (e.patrolRange > 0) {{
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
            var enemyPoints = e.isBoss ? 500 : 50;
            if (typeof addCombo === 'function') {{
              addCombo();
              enemyPoints = applyScore(enemyPoints);
              if (typeof spawnScorePopup === 'function') spawnScorePopup(e.x + e.w/2, e.y, '+' + enemyPoints, '#f97316');
            }} else {{
              score += enemyPoints;
            }}
            if (typeof window.trackBridgeEvent === 'function') window.trackBridgeEvent('enemy_kill');
            updateScore();
            player.vy = -CONFIG.jumpStrength * 0.7;
            if (typeof sfxStomp === 'function') sfxStomp();
            if (typeof triggerShake === 'function') triggerShake(5);
            // Hit-stop: brief freeze on heavy impacts (longer for bosses)
            hitStopTimer = e.isBoss ? 8 : 3;
            if (typeof totalEnemiesDefeated !== 'undefined') totalEnemiesDefeated++;
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
        var collectPoints = e.value || 10;
        if (typeof addCombo === 'function') {{
          addCombo();
          collectPoints = applyScore(collectPoints);
          if (typeof spawnScorePopup === 'function') spawnScorePopup(e.x + e.w/2, e.y, '+' + collectPoints, '#fbbf24');
          if (typeof spawnBurst === 'function') spawnBurst(e.x + e.w/2, e.y + e.h/2, e.color, 8, 3);
        }} else {{
          score += collectPoints;
        }}
        if (typeof window.trackBridgeEvent === 'function') window.trackBridgeEvent('collect');
        updateScore();
        if (typeof spawnSparkles === 'function') spawnSparkles(e.x + e.w/2, e.y + e.h/2, e.color, 6);
        else spawnParticles(e.x + e.w/2, e.y + e.h/2, e.color, 8);
        if (typeof sfxCollect === 'function') sfxCollect();
        if (typeof totalCollectiblesGathered !== 'undefined') totalCollectiblesGathered++;
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

    // Checkpoint triggers (set respawn position)
    for (var i = 0; i < entities.length; i++) {{
      var e = entities[i];
      if (!e.alive || e.type !== 'trigger') continue;
      if (!e.isCheckpoint || e.activated) continue;
      if (rectOverlap(player, e)) {{
        e.activated = true;
        lastCheckpoint = {{ x: e.x, y: e.y }};
        if (typeof sfxCollect === 'function') sfxCollect();
        spawnParticles(e.x + e.w/2, e.y + e.h/2, '#22c55e', 12, 'ring');
        if (typeof spawnScorePopup === 'function') spawnScorePopup(e.x + e.w/2, e.y, 'CHECKPOINT', '#22c55e');
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
        if (typeof triggerShake === 'function') triggerShake(10);
        if (typeof saveProgress === 'function') saveProgress();
        if (typeof deathlessLevel !== 'undefined' && deathlessLevel) {{
          if (typeof unlockAchievement === 'function') unlockAchievement('survivor');
        }}
        if (typeof levelStartTime !== 'undefined' && (Date.now() - levelStartTime) < 30000) {{
          if (typeof unlockAchievement === 'function') unlockAchievement('speed_runner');
        }}
        if (levelIdx + 1 >= LEVELS.length) {{
          if (typeof unlockAchievement === 'function') unlockAchievement('champion');
          if (typeof deathlessRun !== 'undefined' && deathlessRun) {{
            if (typeof unlockAchievement === 'function') unlockAchievement('untouchable');
          }}
        }}
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
    updateEnemyProjectiles();
    if (typeof checkProjectileWallHits === 'function') checkProjectileWallHits();
    // Update feature systems (save, achievements, shake, camera)
    if (typeof updateFeatureSystems === 'function') updateFeatureSystems();
    // Update polish systems (combo, particles, tutorial, transitions)
    if (typeof updatePolishSystems === 'function') updatePolishSystems();
    // Per-genre ambient effect ticks (engine trails, afterimages, tread marks)
    if (state === 'playing' && player) {{
      if (CONFIG.genre === 'shooter' && typeof spawnEngineTrail === 'function') {{
        if (Math.abs(player.vx) + Math.abs(player.vy) > 0.5) {{
          spawnEngineTrail(player.x + player.w/2, player.y + player.h, CONFIG.playerColor);
        }}
      }} else if (CONFIG.genre === 'parkour' && typeof spawnAfterimage === 'function') {{
        var pSpd = Math.abs(player.vx);
        if (pSpd > 4 && Math.random() < 0.5) {{
          spawnAfterimage(player.x, player.y, player.w, player.h, CONFIG.playerColor);
        }}
      }} else if (CONFIG.genre === 'tank_battle' && typeof spawnTreadMark === 'function') {{
        if ((Math.abs(player.vx) + Math.abs(player.vy)) > 0.5 && Math.random() < 0.3) {{
          spawnTreadMark(player.x + player.w/2, player.y + player.h - 2,
            (player.tankDir === 'up' || player.tankDir === 'down') ? 'v' : 'h');
        }}
      }}
    }}
    // Update core particle system (dot/sparkle/trail/ring/shard/afterimage/treadmark)
    updateParticles();

    // Decrement jump buffer (consumed on landing, else expires)
    if (jumpBufferTimer > 0) jumpBufferTimer--;
    // Clear edge-detected input state at end of frame
    keysJustPressed = {{}};
    touchUpJustPressed = false;
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

    // Parallax background layers (screen-space, scroll slower than camera)
    var bgBase = currentLevel.background || CONFIG.background || '#0a0a0a';
    // Far layer: gradient band with slow-scrolling silhouettes
    var farOffset = -camera.x * 0.15;
    var grad = ctx.createLinearGradient(0, 0, 0, H);
    grad.addColorStop(0, bgBase);
    grad.addColorStop(0.55, bgBase);
    grad.addColorStop(1, 'rgba(0,0,0,0.5)');
    ctx.fillStyle = grad;
    ctx.fillRect(0, 0, W, H);
    ctx.fillStyle = 'rgba(255,255,255,0.025)';
    for (var i = 0; i < 6; i++) {{
      var bx = ((farOffset + i * 280) % (W + 280) + (W + 280)) % (W + 280) - 140;
      var by = H * 0.35 + Math.sin(i * 1.7) * 30;
      var bw = 180 + (i % 3) * 40;
      ctx.beginPath();
      ctx.moveTo(bx, by + 60);
      ctx.lineTo(bx + bw / 2, by);
      ctx.lineTo(bx + bw, by + 60);
      ctx.closePath();
      ctx.fill();
    }}
    // Near layer: faster parallax dots / particles
    var nearOffset = -camera.x * 0.4;
    ctx.fillStyle = 'rgba(255,255,255,0.05)';
    for (var i = 0; i < 18; i++) {{
      var nx = ((nearOffset + i * 90) % (W + 90) + (W + 90)) % (W + 90) - 45;
      var ny = (i * 53) % H;
      ctx.fillRect(nx, ny, 3, 3);
    }}

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

    // Collectibles (pulsing with glow halo)
    var pulse = Math.sin(Date.now() / 200) * 0.3 + 0.7;
    for (var i = 0; i < collEnts.length; i++) {{
      var e = collEnts[i];
      var cx = e.x + e.w/2, cy = e.y + e.h/2;
      // Outer glow halo
      ctx.globalAlpha = pulse * 0.35;
      ctx.fillStyle = e.color;
      ctx.beginPath();
      ctx.arc(cx, cy, e.w * 0.9, 0, Math.PI * 2);
      ctx.fill();
      // Core orb
      ctx.globalAlpha = pulse;
      ctx.fillStyle = e.color;
      ctx.beginPath();
      ctx.arc(cx, cy, e.w/2, 0, Math.PI * 2);
      ctx.fill();
      // Inner highlight
      ctx.globalAlpha = 1;
      ctx.fillStyle = '#fff';
      ctx.beginPath();
      ctx.arc(cx - e.w*0.12, cy - e.h*0.12, e.w/6, 0, Math.PI * 2);
      ctx.fill();
      // Ring outline
      ctx.strokeStyle = 'rgba(255,255,255,0.6)';
      ctx.lineWidth = 1;
      ctx.beginPath();
      ctx.arc(cx, cy, e.w/3, 0, Math.PI * 2);
      ctx.stroke();
    }}
    ctx.globalAlpha = 1;

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

    // Enemies (genre-styled rendering)
    for (var i = 0; i < enemyEnts.length; i++) {{
      var e = enemyEnts[i];
      var ecx = e.x + e.w/2, ecy = e.y + e.h/2;
      var eStyle = CONFIG.genreStyle || 'humanoid';
      ctx.fillStyle = e.color;
      if (eStyle === 'ship') {{
        // Enemy ship: inverted triangle pointing toward player
        var dir = (player && player.x < e.x) ? -1 : 1;
        ctx.beginPath();
        if (dir === -1) {{
          ctx.moveTo(e.x, ecy);
          ctx.lineTo(e.x + e.w, e.y);
          ctx.lineTo(e.x + e.w, e.y + e.h);
        }} else {{
          ctx.moveTo(e.x + e.w, ecy);
          ctx.lineTo(e.x, e.y);
          ctx.lineTo(e.x, e.y + e.h);
        }}
        ctx.closePath();
        ctx.fill();
        // Red eye/sensor
        ctx.fillStyle = '#ff0000';
        ctx.beginPath();
        ctx.arc(ecx, ecy, 2, 0, Math.PI * 2);
        ctx.fill();
      }} else if (eStyle === 'orb') {{
        // Enemy orb: spiky circle
        ctx.beginPath();
        var spikes = 8;
        for (var s = 0; s < spikes * 2; s++) {{
          var r = s % 2 === 0 ? e.w/2 : e.w/3;
          var a = (s / (spikes * 2)) * Math.PI * 2;
          if (s === 0) ctx.moveTo(ecx + Math.cos(a) * r, ecy + Math.sin(a) * r);
          else ctx.lineTo(ecx + Math.cos(a) * r, ecy + Math.sin(a) * r);
        }}
        ctx.closePath();
        ctx.fill();
        // Core
        ctx.fillStyle = '#fff';
        ctx.beginPath();
        ctx.arc(ecx, ecy, 3, 0, Math.PI * 2);
        ctx.fill();
      }} else if (eStyle === 'isometric') {{
        // Enemy isometric: hostile 3D cube with red glow
        var eIsoW = e.w, eIsoH = e.h, eIsoD = e.w * 0.5;
        var ebx = e.x, eby = e.y;
        // Top face
        ctx.fillStyle = e.color;
        ctx.beginPath();
        ctx.moveTo(ebx, eby + eIsoD);
        ctx.lineTo(ebx + eIsoW/2, eby);
        ctx.lineTo(ebx + eIsoW, eby + eIsoD);
        ctx.lineTo(ebx + eIsoW/2, eby + eIsoD * 2);
        ctx.closePath();
        ctx.fill();
        // Left face
        ctx.globalAlpha = 0.7;
        ctx.beginPath();
        ctx.moveTo(ebx, eby + eIsoD);
        ctx.lineTo(ebx + eIsoW/2, eby + eIsoD * 2);
        ctx.lineTo(ebx + eIsoW/2, eby + eIsoH + eIsoD);
        ctx.lineTo(ebx, eby + eIsoH);
        ctx.closePath();
        ctx.fill();
        // Right face
        ctx.globalAlpha = 0.45;
        ctx.beginPath();
        ctx.moveTo(ebx + eIsoW, eby + eIsoD);
        ctx.lineTo(ebx + eIsoW/2, eby + eIsoD * 2);
        ctx.lineTo(ebx + eIsoW/2, eby + eIsoH + eIsoD);
        ctx.lineTo(ebx + eIsoW, eby + eIsoH);
        ctx.closePath();
        ctx.fill();
        ctx.globalAlpha = 1;
        // Red eye on top
        ctx.fillStyle = '#ff0000';
        ctx.beginPath();
        ctx.arc(ecx, eby + eIsoD, 2.5, 0, Math.PI * 2);
        ctx.fill();
      }} else if (eStyle === 'tank') {{
        // Enemy tank: body + treads + barrel facing player
        var etbx = e.x, etby = e.y, etbw = e.w, etbh = e.h;
        // Determine facing direction toward player
        var edir = 'up';
        if (typeof player !== 'undefined' && player) {{
          var edx = player.x - e.x, edy = player.y - e.y;
          if (Math.abs(edx) > Math.abs(edy)) edir = edx > 0 ? 'right' : 'left';
          else edir = edy > 0 ? 'down' : 'up';
        }}
        // Treads
        ctx.fillStyle = '#2a2a2a';
        ctx.fillRect(etbx - 2, etby + 2, 3, etbh - 4);
        ctx.fillRect(etbx + etbw - 1, etby + 2, 3, etbh - 4);
        // Body
        ctx.fillStyle = e.color;
        ctx.fillRect(etbx + 2, etby + 2, etbw - 4, etbh - 4);
        // Barrel
        ctx.fillStyle = '#111';
        var ebcx = etbx + etbw/2, ebcy = etby + etbh/2;
        var ebLen = etbw * 0.55;
        if (edir === 'up') ctx.fillRect(ebcx - 2, etby - ebLen + 4, 4, ebLen);
        else if (edir === 'down') ctx.fillRect(ebcx - 2, etby + etbh - 4, 4, ebLen);
        else if (edir === 'left') ctx.fillRect(etbx - ebLen + 4, ebcy - 2, ebLen, 4);
        else ctx.fillRect(etbx + etbw - 4, ebcy - 2, ebLen, 4);
        // Red sensor dot
        ctx.fillStyle = '#ff0000';
        ctx.beginPath();
        ctx.arc(ebcx, ebcy, 3, 0, Math.PI * 2);
        ctx.fill();
      }} else {{
        // Humanoid enemy: rectangle with eyes
        ctx.fillRect(e.x, e.y, e.w, e.h);
        // Eyes
        ctx.fillStyle = '#fff';
        ctx.fillRect(e.x + e.w*0.25, e.y + e.h*0.3, 3, 3);
        ctx.fillRect(e.x + e.w*0.65, e.y + e.h*0.3, 3, 3);
      }}
      if (e.isBoss) {{
        ctx.strokeStyle = '#fff';
        ctx.lineWidth = 2;
        ctx.strokeRect(e.x - 2, e.y - 2, e.w + 4, e.h + 4);
        ctx.fillStyle = '#fff';
        ctx.font = 'bold 11px sans-serif';
        ctx.textAlign = 'center';
        ctx.fillText('BOSS', e.x + e.w/2, e.y - 6);
        // Boss HP bar with phase color coding
        var bossMaxHp = 3;
        var hpRatio = Math.max(0, e.health / bossMaxHp);
        var barW = e.w + 8, barH = 4;
        var barX = e.x - 4, barY = e.y - 18;
        ctx.fillStyle = 'rgba(0,0,0,0.6)';
        ctx.fillRect(barX, barY, barW, barH);
        ctx.fillStyle = hpRatio > 0.67 ? '#22c55e' : (hpRatio > 0.34 ? '#f97316' : '#dc2626');
        ctx.fillRect(barX, barY, barW * hpRatio, barH);
        ctx.strokeStyle = '#333';
        ctx.lineWidth = 1;
        ctx.strokeRect(barX, barY, barW, barH);
      }}
    }}

    // Goal and checkpoint triggers
    for (var i = 0; i < triggerEnts.length; i++) {{
      var e = triggerEnts[i];
      var isCheckpoint = e.isCheckpoint;
      var pulseT = Math.sin(Date.now() / 300) * 0.3 + 0.7;
      if (isCheckpoint) {{
        // Checkpoint: flag-style marker, brighter when activated
        ctx.globalAlpha = e.activated ? 0.9 : 0.5 + pulseT * 0.3;
        ctx.fillStyle = e.activated ? '#22c55e' : '#666';
        ctx.fillRect(e.x, e.y, e.w, e.h);
        // Flag pole
        ctx.fillStyle = '#888';
        ctx.fillRect(e.x + e.w/2 - 1, e.y - 8, 2, e.h + 8);
        // Flag
        ctx.fillStyle = e.activated ? '#22c55e' : '#555';
        ctx.beginPath();
        ctx.moveTo(e.x + e.w/2 + 1, e.y - 8);
        ctx.lineTo(e.x + e.w/2 + 10, e.y - 4);
        ctx.lineTo(e.x + e.w/2 + 1, e.y);
        ctx.closePath();
        ctx.fill();
        ctx.globalAlpha = 1;
        ctx.fillStyle = e.activated ? '#22c55e' : '#888';
        ctx.font = 'bold 9px sans-serif';
        ctx.textAlign = 'center';
        ctx.fillText(e.activated ? 'SAVED' : 'CHECKPOINT', e.x + e.w/2, e.y - 12);
      }} else {{
        // Goal trigger
        ctx.fillStyle = e.color;
        ctx.globalAlpha = 0.6 + pulseT * 0.3;
        ctx.fillRect(e.x, e.y, e.w, e.h);
        ctx.globalAlpha = 1;
        ctx.fillStyle = '#fff';
        ctx.font = 'bold 10px sans-serif';
        ctx.textAlign = 'center';
        ctx.fillText('GOAL', e.x + e.w/2, e.y - 4);
      }}
    }}
    ctx.globalAlpha = 1;

    // Player (genre-styled rendering with animation)
    if (player) {{
      var invFlash = (typeof isInvulnerable === 'function' && isInvulnerable()) ? (Math.floor(Date.now() / 80) % 2 === 0 ? 0.4 : 1) : 1;
      ctx.globalAlpha = invFlash;
      var pcx = player.x + player.w/2, pcy = player.y + player.h/2;
      var pStyle = CONFIG.genreStyle || 'humanoid';

      // Wall-slide visual: sparks on contact side
      if (isWallSliding && Math.random() < 0.5) {{
        var sparkX = player.facing === -1 ? player.x + player.w : player.x;
        ctx.fillStyle = '#00e5ff';
        ctx.globalAlpha = invFlash * 0.7;
        ctx.fillRect(sparkX - 1, player.y + Math.random() * player.h, 2, 2);
        ctx.globalAlpha = invFlash;
      }}

      // Double-jump trail: fading aura when airborne with jumps used
      if (CONFIG.canDoubleJump && !player.onGround && jumpsRemaining < maxJumps - 1) {{
        ctx.globalAlpha = invFlash * 0.25;
        ctx.fillStyle = CONFIG.accentColor;
        ctx.beginPath();
        ctx.arc(pcx, pcy, player.w * 0.7, 0, Math.PI * 2);
        ctx.fill();
        ctx.globalAlpha = invFlash;
      }}

      if (pStyle === 'ship') {{
        // Spaceship: triangle pointing in facing direction with thrust trail
        ctx.fillStyle = player.color;
        ctx.beginPath();
        if (player.facing === -1) {{
          ctx.moveTo(player.x, pcy);
          ctx.lineTo(player.x + player.w, player.y);
          ctx.lineTo(player.x + player.w, player.y + player.h);
        }} else {{
          ctx.moveTo(player.x + player.w, pcy);
          ctx.lineTo(player.x, player.y);
          ctx.lineTo(player.x, player.y + player.h);
        }}
        ctx.closePath();
        ctx.fill();
        // Cockpit
        ctx.fillStyle = '#fff';
        ctx.globalAlpha = invFlash * 0.8;
        ctx.beginPath();
        ctx.arc(pcx, pcy, 3, 0, Math.PI * 2);
        ctx.fill();
        ctx.globalAlpha = invFlash;
        // Thrust trail
        var thrustLen = Math.abs(player.vx) > 0.5 ? 8 + Math.random() * 6 : 4;
        var trailX = player.facing === -1 ? player.x + player.w : player.x;
        ctx.fillStyle = '#fbbf24';
        ctx.globalAlpha = invFlash * 0.6;
        ctx.beginPath();
        ctx.moveTo(trailX, pcy - 3);
        ctx.lineTo(trailX + (player.facing === -1 ? thrustLen : -thrustLen), pcy);
        ctx.lineTo(trailX, pcy + 3);
        ctx.closePath();
        ctx.fill();
        ctx.globalAlpha = invFlash;
      }} else if (pStyle === 'orb') {{
        // Orb: circular entity with pulsing aura
        var orbPulse = Math.sin(Date.now() / 200) * 0.15 + 0.85;
        // Outer aura
        ctx.globalAlpha = invFlash * 0.3;
        ctx.fillStyle = player.color;
        ctx.beginPath();
        ctx.arc(pcx, pcy, player.w * 0.7 * orbPulse, 0, Math.PI * 2);
        ctx.fill();
        // Core
        ctx.globalAlpha = invFlash;
        ctx.fillStyle = player.color;
        ctx.beginPath();
        ctx.arc(pcx, pcy, player.w / 2.2, 0, Math.PI * 2);
        ctx.fill();
        // Inner highlight
        ctx.fillStyle = '#fff';
        ctx.beginPath();
        ctx.arc(pcx - 2, pcy - 2, 3, 0, Math.PI * 2);
        ctx.fill();
        // Direction indicator
        ctx.fillStyle = '#fff';
        ctx.globalAlpha = invFlash * 0.6;
        ctx.beginPath();
        ctx.arc(pcx + player.facing * (player.w/2.5), pcy, 2, 0, Math.PI * 2);
        ctx.fill();
        ctx.globalAlpha = invFlash;
      }} else if (pStyle === 'isometric') {{
        // Isometric: pseudo-3D cube with three visible faces
        var isoW = player.w, isoH = player.h, isoD = player.w * 0.5;
        var bx = player.x, by = player.y;
        // Top face (lighter)
        ctx.fillStyle = player.color;
        ctx.globalAlpha = invFlash * 1.0;
        ctx.beginPath();
        ctx.moveTo(bx, by + isoD);
        ctx.lineTo(bx + isoW/2, by);
        ctx.lineTo(bx + isoW, by + isoD);
        ctx.lineTo(bx + isoW/2, by + isoD * 2);
        ctx.closePath();
        ctx.fill();
        // Left face (medium)
        ctx.globalAlpha = invFlash * 0.75;
        ctx.beginPath();
        ctx.moveTo(bx, by + isoD);
        ctx.lineTo(bx + isoW/2, by + isoD * 2);
        ctx.lineTo(bx + isoW/2, by + isoH + isoD);
        ctx.lineTo(bx, by + isoH);
        ctx.closePath();
        ctx.fill();
        // Right face (darker)
        ctx.globalAlpha = invFlash * 0.5;
        ctx.beginPath();
        ctx.moveTo(bx + isoW, by + isoD);
        ctx.lineTo(bx + isoW/2, by + isoD * 2);
        ctx.lineTo(bx + isoW/2, by + isoH + isoD);
        ctx.lineTo(bx + isoW, by + isoH);
        ctx.closePath();
        ctx.fill();
        ctx.globalAlpha = invFlash;
        // Direction marker on top face
        ctx.fillStyle = '#fff';
        ctx.globalAlpha = invFlash * 0.9;
        ctx.beginPath();
        ctx.arc(bx + isoW/2 + player.facing * 4, by + isoD, 2, 0, Math.PI * 2);
        ctx.fill();
        ctx.globalAlpha = invFlash;
      }} else if (pStyle === 'tank') {{
        // Tank: body + treads + directional barrel
        var tbx = player.x, tby = player.y, tbw = player.w, tbh = player.h;
        // Treads (darker side bars)
        ctx.fillStyle = '#3a3a3a';
        ctx.globalAlpha = invFlash * 0.9;
        ctx.fillRect(tbx - 2, tby + 2, 3, tbh - 4);
        ctx.fillRect(tbx + tbw - 1, tby + 2, 3, tbh - 4);
        // Tread lines
        ctx.fillStyle = '#555';
        for (var tt = 0; tt < tbh - 4; tt += 4) {{
          ctx.fillRect(tbx - 2, tby + 2 + tt, 3, 2);
          ctx.fillRect(tbx + tbw - 1, tby + 2 + tt, 3, 2);
        }}
        // Tank body
        ctx.fillStyle = player.color;
        ctx.globalAlpha = invFlash;
        ctx.fillRect(tbx + 2, tby + 2, tbw - 4, tbh - 4);
        // Body highlight
        ctx.fillStyle = 'rgba(255,255,255,0.2)';
        ctx.fillRect(tbx + 3, tby + 3, tbw - 6, 3);
        // Barrel (points in tankDir)
        ctx.fillStyle = '#222';
        var bcx = tbx + tbw/2, bcy = tby + tbh/2;
        var bLen = tbw * 0.6;
        if (player.tankDir === 'up') {{
          ctx.fillRect(bcx - 2, tby - bLen + 4, 4, bLen);
        }} else if (player.tankDir === 'down') {{
          ctx.fillRect(bcx - 2, tby + tbh - 4, 4, bLen);
        }} else if (player.tankDir === 'left') {{
          ctx.fillRect(tbx - bLen + 4, bcy - 2, bLen, 4);
        }} else {{
          ctx.fillRect(tbx + tbw - 4, bcy - 2, bLen, 4);
        }}
        // Turret center
        ctx.fillStyle = '#1a1a1a';
        ctx.beginPath();
        ctx.arc(bcx, bcy, 4, 0, Math.PI * 2);
        ctx.fill();
      }} else {{
        // Humanoid: rectangle with walk-cycle animation
        var isMoving = Math.abs(player.vx) > 0.5 && player.onGround;
        var walkPhase = isMoving ? Math.floor(Date.now() / 80) % 4 : 0;
        var legOffsets = [[0, 0], [2, -2], [0, 0], [-2, -2]];
        var lo = legOffsets[walkPhase];
        // Body
        ctx.fillStyle = player.color;
        ctx.fillRect(player.x, player.y, player.w, player.h);
        // Eyes (face direction)
        ctx.fillStyle = '#fff';
        var eyeX = player.facing === -1 ? player.x + player.w*0.15 : player.x + player.w*0.55;
        ctx.fillRect(eyeX, player.y + player.h*0.2, 4, 4);
        ctx.fillRect(eyeX + player.w*0.25, player.y + player.h*0.2, 4, 4);
        // Legs (animated when walking)
        ctx.fillStyle = player.color;
        ctx.fillRect(player.x + player.w*0.15, player.y + player.h, 4, 3 + lo[0]);
        ctx.fillRect(player.x + player.w*0.65, player.y + player.h, 4, 3 + lo[1]);
        // Direction indicator
        ctx.fillStyle = typeof activePowerups !== 'undefined' && activePowerups.speed > 0 ? '#22c55e' : '#fff';
        var dirX = player.facing === -1 ? player.x : player.x + player.w - 3;
        ctx.fillRect(dirX, player.y + player.h*0.4, 3, 4);
      }}
      ctx.globalAlpha = 1;
    }}

    // Core particle rendering (world space, before camera restore)
    renderParticles();

    ctx.restore();

    // Extension rendering (particles, projectiles, powerups, etc.)
    // Rendered in screen space — extension functions subtract camera themselves.
    if (typeof renderExtensions === 'function') renderExtensions();
    renderEnemyProjectiles();
    // Feature rendering (tilemap, minimap, overlays) in screen space
    if (typeof renderFeatureSystems === 'function') renderFeatureSystems();
    // Polish rendering (combo, score popups, tutorial, transitions) in screen space
    if (typeof renderPolishSystems === 'function') renderPolishSystems();
    // Polish overlay (settings panel) on top of everything
    if (typeof renderPolishOverlay === 'function') renderPolishOverlay();

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

    // Post-processing: per-genre visual identity (scanlines, bloom, speed lines, etc.)
    // Falls back to a subtle vignette when no genre profile is active.
    if (typeof applyPostProcess === 'function') {{
      applyPostProcess();
    }} else {{
      var vGrad = ctx.createRadialGradient(W/2, H/2, Math.min(W, H) * 0.35, W/2, H/2, Math.max(W, H) * 0.75);
      vGrad.addColorStop(0, 'rgba(0,0,0,0)');
      vGrad.addColorStop(1, 'rgba(0,0,0,0.45)');
      ctx.fillStyle = vGrad;
      ctx.fillRect(0, 0, W, H);
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
    // AI-Native Game Bridge: report telemetry and apply directives each frame
    if (typeof window.bridgeTick === 'function') window.bridgeTick();
    render();
    requestAnimationFrame(loop);
  }}

  // Initial overlay
  updateLives();
  showOverlay(CONFIG.title.toUpperCase(), CONFIG.intro || CONFIG.quest, 'PRESS ANY KEY OR TAP TO START');
  requestAnimationFrame(loop);
}})();
{bridge_script}
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
