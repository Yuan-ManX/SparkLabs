"""
SparkAI Agent - Game Template Library

Rich template library for game project scaffolding. Each template
defines the file structure, default systems, entity templates,
and configuration for a specific game genre.

Templates are organized by genre and support progressive maturity
levels: seed -> validated -> production.
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class TemplateMaturity(Enum):
    SEED = "seed"
    VALIDATED = "validated"
    PRODUCTION = "production"


class GameGenre(Enum):
    PLATFORMER = "platformer"
    RPG = "rpg"
    SHOOTER = "shooter"
    PUZZLE = "puzzle"
    STRATEGY = "strategy"
    RACING = "racing"
    FIGHTING = "fighting"
    SURVIVAL = "survival"
    SIMULATION = "simulation"
    ADVENTURE = "adventure"
    ROGUELIKE = "roguelike"
    CARD_GAME = "card_game"
    IDLE = "idle"
    SPORTS = "sports"
    RHYTHM = "rhythm"
    SANDBOX = "sandbox"
    HORROR = "horror"
    METROIDVANIA = "metroidvania"


@dataclass
class FileTemplate:
    path: str = ""
    file_type: str = "code"
    description: str = ""
    is_entry_point: bool = False
    dependencies: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "path": self.path,
            "file_type": self.file_type,
            "description": self.description,
            "is_entry_point": self.is_entry_point,
            "dependencies": self.dependencies,
        }


@dataclass
class EntityTemplate:
    name: str = ""
    components: List[str] = field(default_factory=list)
    description: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "components": self.components,
            "description": self.description,
        }


@dataclass
class SystemTemplate:
    name: str = ""
    priority: int = 0
    required_components: List[str] = field(default_factory=list)
    description: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "priority": self.priority,
            "required_components": self.required_components,
            "description": self.description,
        }


@dataclass
class GenreTemplate:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    genre: GameGenre = GameGenre.PLATFORMER
    description: str = ""
    maturity: TemplateMaturity = TemplateMaturity.SEED
    tags: List[str] = field(default_factory=list)
    file_structure: List[FileTemplate] = field(default_factory=list)
    entity_templates: List[EntityTemplate] = field(default_factory=list)
    system_templates: List[SystemTemplate] = field(default_factory=list)
    default_config: Dict[str, Any] = field(default_factory=dict)
    usage_count: int = 0
    success_count: int = 0
    failure_count: int = 0
    version: int = 1
    created_at: float = field(default_factory=time.time)

    @property
    def success_rate(self) -> float:
        total = self.success_count + self.failure_count
        return self.success_count / total if total > 0 else 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "genre": self.genre.value,
            "description": self.description,
            "maturity": self.maturity.value,
            "tags": self.tags,
            "file_structure": [f.to_dict() for f in self.file_structure],
            "entity_templates": [e.to_dict() for e in self.entity_templates],
            "system_templates": [s.to_dict() for s in self.system_templates],
            "default_config": self.default_config,
            "usage_count": self.usage_count,
            "success_count": self.success_count,
            "failure_count": self.failure_count,
            "success_rate": self.success_rate,
            "version": self.version,
        }


@dataclass
class ScaffoldResult:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    project_name: str = ""
    genre: str = ""
    template_id: str = ""
    files: List[Dict[str, str]] = field(default_factory=list)
    entities: List[Dict[str, Any]] = field(default_factory=list)
    systems: List[Dict[str, Any]] = field(default_factory=list)
    config: Dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "project_name": self.project_name,
            "genre": self.genre,
            "template_id": self.template_id,
            "files": self.files,
            "entities": self.entities,
            "systems": self.systems,
            "config": self.config,
            "created_at": self.created_at,
        }


def _build_seed_templates() -> Dict[str, GenreTemplate]:
    templates = {}

    platformer = GenreTemplate(
        name="2D Platformer",
        genre=GameGenre.PLATFORMER,
        description="Side-scrolling platformer with jumping, collectibles, and enemies",
        tags=["2d", "side-scroller", "jump", "collectibles"],
        file_structure=[
            FileTemplate(path="src/main.ts", file_type="code", description="Game entry point", is_entry_point=True),
            FileTemplate(path="src/player.ts", file_type="code", description="Player controller with jump mechanics"),
            FileTemplate(path="src/level.ts", file_type="code", description="Level loader and tilemap"),
            FileTemplate(path="src/enemy.ts", file_type="code", description="Enemy AI and patrol behavior"),
            FileTemplate(path="src/collectible.ts", file_type="code", description="Collectible items and scoring"),
            FileTemplate(path="src/camera.ts", file_type="code", description="Follow camera with smoothing"),
            FileTemplate(path="src/ui.ts", file_type="code", description="HUD with score and lives"),
            FileTemplate(path="config/engine.json", file_type="config", description="Engine configuration"),
        ],
        entity_templates=[
            EntityTemplate(name="Player", components=["Transform", "PhysicsBody", "SpriteRenderer", "InputReceiver", "Animator"], description="Player character with jump and move"),
            EntityTemplate(name="Platform", components=["Transform", "Collider", "SpriteRenderer"], description="Solid platform for standing on"),
            EntityTemplate(name="Enemy", components=["Transform", "PhysicsBody", "SpriteRenderer", "AIBrain"], description="Patrolling enemy"),
            EntityTemplate(name="Coin", components=["Transform", "Collider", "SpriteRenderer", "Tween"], description="Collectible coin with animation"),
            EntityTemplate(name="Goal", components=["Transform", "Collider", "SpriteRenderer"], description="Level exit trigger"),
        ],
        system_templates=[
            SystemTemplate(name="PhysicsSystem", priority=10, required_components=["PhysicsBody"], description="Gravity and collision"),
            SystemTemplate(name="InputSystem", priority=20, required_components=["InputReceiver"], description="Player input handling"),
            SystemTemplate(name="AnimationSystem", priority=30, required_components=["Animator"], description="Sprite animation"),
            SystemTemplate(name="AISystem", priority=40, required_components=["AIBrain"], description="Enemy behavior"),
            SystemTemplate(name="TweenSystem", priority=50, required_components=["Tween"], description="Smooth animations"),
        ],
        default_config={"gravity": 980, "player_speed": 200, "jump_force": 400, "tile_size": 32},
    )
    templates["platformer"] = platformer

    rpg = GenreTemplate(
        name="Turn-Based RPG",
        genre=GameGenre.RPG,
        description="Turn-based RPG with party management, combat, and exploration",
        tags=["rpg", "turn-based", "party", "combat", "exploration"],
        file_structure=[
            FileTemplate(path="src/main.ts", file_type="code", description="Game entry point", is_entry_point=True),
            FileTemplate(path="src/party.ts", file_type="code", description="Party member management"),
            FileTemplate(path="src/combat.ts", file_type="code", description="Turn-based combat system"),
            FileTemplate(path="src/skills.ts", file_type="code", description="Skill and ability definitions"),
            FileTemplate(path="src/inventory.ts", file_type="code", description="Item and equipment system"),
            FileTemplate(path="src/dialogue.ts", file_type="code", description="Dialogue and conversation trees"),
            FileTemplate(path="src/overworld.ts", file_type="code", description="Exploration map and encounters"),
            FileTemplate(path="src/ui.ts", file_type="code", description="Battle UI and menus"),
            FileTemplate(path="config/engine.json", file_type="config", description="Engine configuration"),
        ],
        entity_templates=[
            EntityTemplate(name="Hero", components=["Transform", "SpriteRenderer", "AIBrain", "Script"], description="Party member with stats"),
            EntityTemplate(name="Enemy", components=["Transform", "SpriteRenderer", "AIBrain"], description="Combat enemy with AI"),
            EntityTemplate(name="NPC", components=["Transform", "SpriteRenderer", "AIBrain", "Script"], description="Dialogue NPC"),
            EntityTemplate(name="ItemPickup", components=["Transform", "Collider", "SpriteRenderer"], description="Collectible item"),
        ],
        system_templates=[
            SystemTemplate(name="AISystem", priority=10, required_components=["AIBrain"], description="NPC and enemy behavior"),
            SystemTemplate(name="ScriptSystem", priority=20, required_components=["Script"], description="Custom game logic"),
            SystemTemplate(name="CollisionSystem", priority=30, required_components=["Collider"], description="Trigger detection"),
        ],
        default_config={"turn_order": "speed", "max_party_size": 4, "encounter_rate": 0.15},
    )
    templates["rpg"] = rpg

    shooter = GenreTemplate(
        name="Top-Down Shooter",
        genre=GameGenre.SHOOTER,
        description="Top-down shooter with wave-based enemies and power-ups",
        tags=["shooter", "top-down", "waves", "power-ups"],
        file_structure=[
            FileTemplate(path="src/main.ts", file_type="code", description="Game entry point", is_entry_point=True),
            FileTemplate(path="src/player.ts", file_type="code", description="Player with aiming and shooting"),
            FileTemplate(path="src/projectile.ts", file_type="code", description="Bullet and projectile system"),
            FileTemplate(path="src/wave.ts", file_type="code", description="Wave spawner and difficulty"),
            FileTemplate(path="src/powerup.ts", file_type="code", description="Power-up drops and effects"),
            FileTemplate(path="src/ui.ts", file_type="code", description="HUD with health and score"),
            FileTemplate(path="config/engine.json", file_type="config", description="Engine configuration"),
        ],
        entity_templates=[
            EntityTemplate(name="Player", components=["Transform", "PhysicsBody", "SpriteRenderer", "InputReceiver", "Animator"], description="Player with dual-stick controls"),
            EntityTemplate(name="Bullet", components=["Transform", "PhysicsBody", "SpriteRenderer"], description="Player projectile"),
            EntityTemplate(name="Enemy", components=["Transform", "PhysicsBody", "SpriteRenderer", "AIBrain"], description="Chasing/shooting enemy"),
            EntityTemplate(name="PowerUp", components=["Transform", "Collider", "SpriteRenderer", "Tween"], description="Collectible power-up"),
        ],
        system_templates=[
            SystemTemplate(name="PhysicsSystem", priority=10, required_components=["PhysicsBody"], description="Movement and collision"),
            SystemTemplate(name="InputSystem", priority=20, required_components=["InputReceiver"], description="Aiming and shooting"),
            SystemTemplate(name="AISystem", priority=30, required_components=["AIBrain"], description="Enemy targeting"),
        ],
        default_config={"player_speed": 180, "bullet_speed": 400, "wave_delay": 3.0},
    )
    templates["shooter"] = shooter

    puzzle = GenreTemplate(
        name="Match-3 Puzzle",
        genre=GameGenre.PUZZLE,
        description="Match-3 puzzle game with combos and special pieces",
        tags=["puzzle", "match-3", "combo", "casual"],
        file_structure=[
            FileTemplate(path="src/main.ts", file_type="code", description="Game entry point", is_entry_point=True),
            FileTemplate(path="src/board.ts", file_type="code", description="Grid board and piece management"),
            FileTemplate(path="src/matcher.ts", file_type="code", description="Match detection and cascading"),
            FileTemplate(path="src/specials.ts", file_type="code", description="Special piece effects"),
            FileTemplate(path="src/scoring.ts", file_type="code", description="Score calculation and combos"),
            FileTemplate(path="src/ui.ts", file_type="code", description="Game UI and animations"),
            FileTemplate(path="config/engine.json", file_type="config", description="Engine configuration"),
        ],
        entity_templates=[
            EntityTemplate(name="Piece", components=["Transform", "SpriteRenderer", "Tween"], description="Board piece"),
            EntityTemplate(name="Cursor", components=["Transform", "SpriteRenderer", "InputReceiver"], description="Selection cursor"),
        ],
        system_templates=[
            SystemTemplate(name="InputSystem", priority=10, required_components=["InputReceiver"], description="Piece selection"),
            SystemTemplate(name="TweenSystem", priority=20, required_components=["Tween"], description="Swap and fall animations"),
        ],
        default_config={"board_width": 8, "board_height": 8, "piece_types": 6, "cascade_delay": 0.2},
    )
    templates["puzzle"] = puzzle

    strategy = GenreTemplate(
        name="Tower Defense",
        genre=GameGenre.STRATEGY,
        description="Tower defense with upgrade paths and enemy waves",
        tags=["strategy", "tower-defense", "upgrades", "waves"],
        file_structure=[
            FileTemplate(path="src/main.ts", file_type="code", description="Game entry point", is_entry_point=True),
            FileTemplate(path="src/tower.ts", file_type="code", description="Tower placement and targeting"),
            FileTemplate(path="src/enemy.ts", file_type="code", description="Enemy pathfinding and health"),
            FileTemplate(path="src/path.ts", file_type="code", description="Path definition and waypoints"),
            FileTemplate(path="src/wave.ts", file_type="code", description="Wave composition and timing"),
            FileTemplate(path="src/upgrade.ts", file_type="code", description="Tower upgrade tree"),
            FileTemplate(path="src/ui.ts", file_type="code", description="Build menu and HUD"),
            FileTemplate(path="config/engine.json", file_type="config", description="Engine configuration"),
        ],
        entity_templates=[
            EntityTemplate(name="Tower", components=["Transform", "SpriteRenderer", "AIBrain", "Script"], description="Defensive tower"),
            EntityTemplate(name="Enemy", components=["Transform", "PhysicsBody", "SpriteRenderer", "AIBrain"], description="Path-following enemy"),
            EntityTemplate(name="Projectile", components=["Transform", "SpriteRenderer"], description="Tower projectile"),
        ],
        system_templates=[
            SystemTemplate(name="AISystem", priority=10, required_components=["AIBrain"], description="Tower targeting and enemy pathfinding"),
            SystemTemplate(name="PhysicsSystem", priority=20, required_components=["PhysicsBody"], description="Enemy movement"),
        ],
        default_config={"grid_size": 32, "starting_gold": 100, "wave_interval": 15},
    )
    templates["strategy"] = strategy

    roguelike = GenreTemplate(
        name="Roguelike Dungeon Crawler",
        genre=GameGenre.ROGUELIKE,
        description="Procedural dungeon crawler with permadeath and loot",
        tags=["roguelike", "procedural", "permadeath", "loot"],
        file_structure=[
            FileTemplate(path="src/main.ts", file_type="code", description="Game entry point", is_entry_point=True),
            FileTemplate(path="src/dungeon.ts", file_type="code", description="Procedural dungeon generation"),
            FileTemplate(path="src/player.ts", file_type="code", description="Player with stats and inventory"),
            FileTemplate(path="src/combat.ts", file_type="code", description="Real-time combat system"),
            FileTemplate(path="src/loot.ts", file_type="code", description="Loot tables and item generation"),
            FileTemplate(path="src/fog.ts", file_type="code", description="Fog of war system"),
            FileTemplate(path="src/ui.ts", file_type="code", description="Inventory and stats HUD"),
            FileTemplate(path="config/engine.json", file_type="config", description="Engine configuration"),
        ],
        entity_templates=[
            EntityTemplate(name="Player", components=["Transform", "PhysicsBody", "SpriteRenderer", "InputReceiver", "Script"], description="Player character"),
            EntityTemplate(name="Enemy", components=["Transform", "SpriteRenderer", "AIBrain"], description="Dungeon enemy"),
            EntityTemplate(name="Item", components=["Transform", "Collider", "SpriteRenderer"], description="Loot drop"),
            EntityTemplate(name="Stairs", components=["Transform", "Collider", "SpriteRenderer"], description="Level transition"),
        ],
        system_templates=[
            SystemTemplate(name="PhysicsSystem", priority=10, required_components=["PhysicsBody"], description="Movement and collision"),
            SystemTemplate(name="AISystem", priority=20, required_components=["AIBrain"], description="Enemy behavior"),
            SystemTemplate(name="ScriptSystem", priority=30, required_components=["Script"], description="Custom game logic"),
        ],
        default_config={"dungeon_width": 50, "dungeon_height": 50, "room_count": 12, "max_floor": 10},
    )
    templates["roguelike"] = roguelike

    survival = GenreTemplate(
        name="Survival Crafting",
        genre=GameGenre.SURVIVAL,
        description="Survival game with crafting, hunger, and day-night cycle",
        tags=["survival", "crafting", "hunger", "day-night"],
        file_structure=[
            FileTemplate(path="src/main.ts", file_type="code", description="Game entry point", is_entry_point=True),
            FileTemplate(path="src/player.ts", file_type="code", description="Player with survival stats"),
            FileTemplate(path="src/crafting.ts", file_type="code", description="Recipe and crafting system"),
            FileTemplate(path="src/world.ts", file_type="code", description="Procedural world generation"),
            FileTemplate(path="src/daynight.ts", file_type="code", description="Day-night cycle system"),
            FileTemplate(path="src/resources.ts", file_type="code", description="Resource nodes and gathering"),
            FileTemplate(path="src/ui.ts", file_type="code", description="Survival HUD and crafting menu"),
            FileTemplate(path="config/engine.json", file_type="config", description="Engine configuration"),
        ],
        entity_templates=[
            EntityTemplate(name="Player", components=["Transform", "PhysicsBody", "SpriteRenderer", "InputReceiver", "Script"], description="Player with hunger and health"),
            EntityTemplate(name="ResourceNode", components=["Transform", "Collider", "SpriteRenderer"], description="Harvestable resource"),
            EntityTemplate(name="CraftingStation", components=["Transform", "Collider", "SpriteRenderer"], description="Crafting workbench"),
        ],
        system_templates=[
            SystemTemplate(name="PhysicsSystem", priority=10, required_components=["PhysicsBody"], description="Movement and collision"),
            SystemTemplate(name="ScriptSystem", priority=20, required_components=["Script"], description="Survival mechanics"),
        ],
        default_config={"day_length": 120, "hunger_rate": 0.5, "craft_time": 2.0},
    )
    templates["survival"] = survival

    racing = GenreTemplate(
        name="Arcade Racing",
        genre=GameGenre.RACING,
        description="Arcade-style racing with boost and drifting",
        tags=["racing", "arcade", "boost", "drift"],
        file_structure=[
            FileTemplate(path="src/main.ts", file_type="code", description="Game entry point", is_entry_point=True),
            FileTemplate(path="src/vehicle.ts", file_type="code", description="Vehicle physics and controls"),
            FileTemplate(path="src/track.ts", file_type="code", description="Track definition and checkpoints"),
            FileTemplate(path="src/ai_racer.ts", file_type="code", description="AI opponent racing"),
            FileTemplate(path="src/ui.ts", file_type="code", description="Speedometer and position HUD"),
            FileTemplate(path="config/engine.json", file_type="config", description="Engine configuration"),
        ],
        entity_templates=[
            EntityTemplate(name="PlayerCar", components=["Transform", "PhysicsBody", "SpriteRenderer", "InputReceiver"], description="Player vehicle"),
            EntityTemplate(name="AICar", components=["Transform", "PhysicsBody", "SpriteRenderer", "AIBrain"], description="AI opponent"),
            EntityTemplate(name="Checkpoint", components=["Transform", "Collider"], description="Track checkpoint"),
        ],
        system_templates=[
            SystemTemplate(name="PhysicsSystem", priority=10, required_components=["PhysicsBody"], description="Vehicle physics"),
            SystemTemplate(name="AISystem", priority=20, required_components=["AIBrain"], description="AI racing behavior"),
        ],
        default_config={"max_speed": 500, "acceleration": 200, "drift_factor": 0.9},
    )
    templates["racing"] = racing

    fighting = GenreTemplate(
        name="2D Fighting Game",
        genre=GameGenre.FIGHTING,
        description="2D fighting game with combo system and special moves",
        tags=["fighting", "2d", "combos", "special-moves"],
        file_structure=[
            FileTemplate(path="src/main.ts", file_type="code", description="Game entry point", is_entry_point=True),
            FileTemplate(path="src/fighter.ts", file_type="code", description="Fighter with hitboxes and moves"),
            FileTemplate(path="src/combo.ts", file_type="code", description="Combo chain system"),
            FileTemplate(path="src/hitbox.ts", file_type="code", description="Hitbox and hurtbox detection"),
            FileTemplate(path="src/ui.ts", file_type="code", description="Health bars and combo counter"),
            FileTemplate(path="config/engine.json", file_type="config", description="Engine configuration"),
        ],
        entity_templates=[
            EntityTemplate(name="Fighter", components=["Transform", "PhysicsBody", "SpriteRenderer", "InputReceiver", "Animator"], description="Fighter character"),
        ],
        system_templates=[
            SystemTemplate(name="PhysicsSystem", priority=10, required_components=["PhysicsBody"], description="Movement and knockback"),
            SystemTemplate(name="AnimationSystem", priority=20, required_components=["Animator"], description="Attack animations"),
            SystemTemplate(name="InputSystem", priority=30, required_components=["InputReceiver"], description="Move input"),
        ],
        default_config={"round_time": 99, "max_health": 1000, "combo_window": 0.3},
    )
    templates["fighting"] = fighting

    card_game = GenreTemplate(
        name="Card Battler",
        genre=GameGenre.CARD_GAME,
        description="Turn-based card game with deck building and strategy",
        tags=["card", "deck-building", "strategy", "turn-based"],
        file_structure=[
            FileTemplate(path="src/main.ts", file_type="code", description="Game entry point", is_entry_point=True),
            FileTemplate(path="src/card.ts", file_type="code", description="Card definitions and effects"),
            FileTemplate(path="src/deck.ts", file_type="code", description="Deck management and drawing"),
            FileTemplate(path="src/board.ts", file_type="code", description="Play area and card placement"),
            FileTemplate(path="src/ai_opponent.ts", file_type="code", description="AI opponent strategy"),
            FileTemplate(path="src/ui.ts", file_type="code", description="Card hand and board UI"),
            FileTemplate(path="config/engine.json", file_type="config", description="Engine configuration"),
        ],
        entity_templates=[
            EntityTemplate(name="Card", components=["Transform", "SpriteRenderer", "Tween"], description="Playing card"),
            EntityTemplate(name="CardSlot", components=["Transform", "Collider"], description="Board card slot"),
        ],
        system_templates=[
            SystemTemplate(name="TweenSystem", priority=10, required_components=["Tween"], description="Card animations"),
            SystemTemplate(name="AISystem", priority=20, required_components=["AIBrain"], description="AI card selection"),
        ],
        default_config={"hand_size": 5, "max_mana": 10, "deck_size": 30},
    )
    templates["card_game"] = card_game

    metroidvania = GenreTemplate(
        name="Metroidvania",
        genre=GameGenre.METROIDVANIA,
        description="Exploration-focused platformer with ability gating and backtracking",
        tags=["metroidvania", "exploration", "ability-gate", "backtracking"],
        file_structure=[
            FileTemplate(path="src/main.ts", file_type="code", description="Game entry point", is_entry_point=True),
            FileTemplate(path="src/player.ts", file_type="code", description="Player with unlockable abilities"),
            FileTemplate(path="src/map.ts", file_type="code", description="Interconnected world map"),
            FileTemplate(path="src/ability.ts", file_type="code", description="Ability unlock system"),
            FileTemplate(path="src/save.ts", file_type="code", description="Save and checkpoint system"),
            FileTemplate(path="src/ui.ts", file_type="code", description="Map screen and ability HUD"),
            FileTemplate(path="config/engine.json", file_type="config", description="Engine configuration"),
        ],
        entity_templates=[
            EntityTemplate(name="Player", components=["Transform", "PhysicsBody", "SpriteRenderer", "InputReceiver", "Animator", "Script"], description="Player with abilities"),
            EntityTemplate(name="AbilityGate", components=["Transform", "Collider", "SpriteRenderer"], description="Gate requiring specific ability"),
            EntityTemplate(name="SavePoint", components=["Transform", "Collider", "SpriteRenderer"], description="Save and heal station"),
            EntityTemplate(name="Boss", components=["Transform", "PhysicsBody", "SpriteRenderer", "AIBrain"], description="Area boss"),
        ],
        system_templates=[
            SystemTemplate(name="PhysicsSystem", priority=10, required_components=["PhysicsBody"], description="Movement and collision"),
            SystemTemplate(name="AISystem", priority=20, required_components=["AIBrain"], description="Boss and enemy behavior"),
            SystemTemplate(name="ScriptSystem", priority=30, required_components=["Script"], description="Ability logic"),
        ],
        default_config={"map_width": 200, "map_height": 100, "tile_size": 16},
    )
    templates["metroidvania"] = metroidvania

    idle = GenreTemplate(
        name="Idle Clicker",
        genre=GameGenre.IDLE,
        description="Idle clicker game with upgrades and automation",
        tags=["idle", "clicker", "incremental", "automation"],
        file_structure=[
            FileTemplate(path="src/main.ts", file_type="code", description="Game entry point", is_entry_point=True),
            FileTemplate(path="src/currency.ts", file_type="code", description="Currency and generation"),
            FileTemplate(path="src/upgrade.ts", file_type="code", description="Upgrade tree and costs"),
            FileTemplate(path="src/automation.ts", file_type="code", description="Auto-clicker and generators"),
            FileTemplate(path="src/prestige.ts", file_type="code", description="Prestige and reset system"),
            FileTemplate(path="src/ui.ts", file_type="code", description="Click area and upgrade panels"),
            FileTemplate(path="config/engine.json", file_type="config", description="Engine configuration"),
        ],
        entity_templates=[
            EntityTemplate(name="ClickTarget", components=["Transform", "SpriteRenderer", "InputReceiver", "Tween"], description="Clickable target"),
        ],
        system_templates=[
            SystemTemplate(name="InputSystem", priority=10, required_components=["InputReceiver"], description="Click detection"),
            SystemTemplate(name="TweenSystem", priority=20, required_components=["Tween"], description="Click feedback animations"),
        ],
        default_config={"base_click_value": 1, "upgrade_cost_mult": 1.15, "tick_rate": 10},
    )
    templates["idle"] = idle

    rhythm = GenreTemplate(
        name="Rhythm Game",
        genre=GameGenre.RHYTHM,
        description="Rhythm game with note patterns and scoring",
        tags=["rhythm", "music", "timing", "scoring"],
        file_structure=[
            FileTemplate(path="src/main.ts", file_type="code", description="Game entry point", is_entry_point=True),
            FileTemplate(path="src/note.ts", file_type="code", description="Note spawning and movement"),
            FileTemplate(path="src/judge.ts", file_type="code", description="Timing judgment system"),
            FileTemplate(path="src/chart.ts", file_type="code", description="Chart format and loader"),
            FileTemplate(path="src/audio.ts", file_type="code", description="Audio sync and playback"),
            FileTemplate(path="src/ui.ts", file_type="code", description="Note highway and score display"),
            FileTemplate(path="config/engine.json", file_type="config", description="Engine configuration"),
        ],
        entity_templates=[
            EntityTemplate(name="Note", components=["Transform", "SpriteRenderer", "Tween"], description="Falling note"),
            EntityTemplate(name="HitZone", components=["Transform", "SpriteRenderer", "InputReceiver"], description="Timing target zone"),
        ],
        system_templates=[
            SystemTemplate(name="InputSystem", priority=10, required_components=["InputReceiver"], description="Hit detection"),
            SystemTemplate(name="AudioSystem", priority=20, required_components=["AudioSource"], description="Music playback"),
        ],
        default_config={"scroll_speed": 400, "perfect_window": 50, "great_window": 100, "good_window": 150},
    )
    templates["rhythm"] = rhythm

    horror = GenreTemplate(
        name="Survival Horror",
        genre=GameGenre.HORROR,
        description="Atmospheric horror with resource management and stealth",
        tags=["horror", "survival", "stealth", "atmosphere"],
        file_structure=[
            FileTemplate(path="src/main.ts", file_type="code", description="Game entry point", is_entry_point=True),
            FileTemplate(path="src/player.ts", file_type="code", description="Player with stealth mechanics"),
            FileTemplate(path="src/monster.ts", file_type="code", description="Monster AI and detection"),
            FileTemplate(path="src/atmosphere.ts", file_type="code", description="Lighting and ambiance"),
            FileTemplate(path="src/puzzle.ts", file_type="code", description="Environmental puzzles"),
            FileTemplate(path="src/ui.ts", file_type="code", description="Minimal HUD"),
            FileTemplate(path="config/engine.json", file_type="config", description="Engine configuration"),
        ],
        entity_templates=[
            EntityTemplate(name="Player", components=["Transform", "PhysicsBody", "SpriteRenderer", "InputReceiver", "Script"], description="Player with flashlight"),
            EntityTemplate(name="Monster", components=["Transform", "SpriteRenderer", "AIBrain"], description="Stalking monster"),
            EntityTemplate(name="Item", components=["Transform", "Collider", "SpriteRenderer"], description="Key or resource"),
        ],
        system_templates=[
            SystemTemplate(name="PhysicsSystem", priority=10, required_components=["PhysicsBody"], description="Movement"),
            SystemTemplate(name="AISystem", priority=20, required_components=["AIBrain"], description="Monster pathfinding"),
            SystemTemplate(name="ScriptSystem", priority=30, required_components=["Script"], description="Stealth mechanics"),
        ],
        default_config={"detection_range": 200, "sanity_drain": 0.1, "flashlight_battery": 100},
    )
    templates["horror"] = horror

    sandbox = GenreTemplate(
        name="Sandbox Builder",
        genre=GameGenre.SANDBOX,
        description="Sandbox building game with block placement and crafting",
        tags=["sandbox", "building", "blocks", "crafting"],
        file_structure=[
            FileTemplate(path="src/main.ts", file_type="code", description="Game entry point", is_entry_point=True),
            FileTemplate(path="src/world.ts", file_type="code", description="Chunk-based world generation"),
            FileTemplate(path="src/blocks.ts", file_type="code", description="Block types and properties"),
            FileTemplate(path="src/player.ts", file_type="code", description="Player with building tools"),
            FileTemplate(path="src/crafting.ts", file_type="code", description="Recipe system"),
            FileTemplate(path="src/ui.ts", file_type="code", description="Inventory and hotbar"),
            FileTemplate(path="config/engine.json", file_type="config", description="Engine configuration"),
        ],
        entity_templates=[
            EntityTemplate(name="Player", components=["Transform", "PhysicsBody", "SpriteRenderer", "InputReceiver"], description="Player builder"),
            EntityTemplate(name="Block", components=["Transform", "Collider", "SpriteRenderer"], description="Placeable block"),
        ],
        system_templates=[
            SystemTemplate(name="PhysicsSystem", priority=10, required_components=["PhysicsBody"], description="Gravity and collision"),
            SystemTemplate(name="InputSystem", priority=20, required_components=["InputReceiver"], description="Block placement"),
        ],
        default_config={"chunk_size": 16, "world_width": 256, "world_height": 128},
    )
    templates["sandbox"] = sandbox

    simulation = GenreTemplate(
        name="City Simulation",
        genre=GameGenre.SIMULATION,
        description="City builder with resource management and citizen AI",
        tags=["simulation", "city-builder", "management", "citizens"],
        file_structure=[
            FileTemplate(path="src/main.ts", file_type="code", description="Game entry point", is_entry_point=True),
            FileTemplate(path="src/city.ts", file_type="code", description="City grid and zones"),
            FileTemplate(path="src/citizen.ts", file_type="code", description="Citizen AI and needs"),
            FileTemplate(path="src/building.ts", file_type="code", description="Building types and effects"),
            FileTemplate(path="src/economy.ts", file_type="code", description="Resource and budget system"),
            FileTemplate(path="src/ui.ts", file_type="code", description="Build menu and stats panel"),
            FileTemplate(path="config/engine.json", file_type="config", description="Engine configuration"),
        ],
        entity_templates=[
            EntityTemplate(name="Building", components=["Transform", "SpriteRenderer", "Script"], description="Placeable building"),
            EntityTemplate(name="Citizen", components=["Transform", "SpriteRenderer", "AIBrain"], description="AI citizen"),
        ],
        system_templates=[
            SystemTemplate(name="AISystem", priority=10, required_components=["AIBrain"], description="Citizen behavior"),
            SystemTemplate(name="ScriptSystem", priority=20, required_components=["Script"], description="Building effects"),
        ],
        default_config={"grid_size": 32, "starting_budget": 10000, "tax_rate": 0.1},
    )
    templates["simulation"] = simulation

    return templates


class GameTemplateLibrary:
    """
    Rich template library for game project scaffolding.

    Provides 16 genre-specific templates with file structures,
    entity templates, system templates, and default configurations.
    """

    def __init__(self):
        self._templates: Dict[str, GenreTemplate] = _build_seed_templates()
        self._scaffolds: List[ScaffoldResult] = []

    def list_templates(self, genre: Optional[GameGenre] = None) -> List[Dict[str, Any]]:
        templates = list(self._templates.values())
        if genre:
            templates = [t for t in templates if t.genre == genre]
        return [t.to_dict() for t in templates]

    def get_template(self, template_id: str) -> Optional[Dict[str, Any]]:
        for t in self._templates.values():
            if t.id == template_id:
                return t.to_dict()
        if template_id in self._templates:
            return self._templates[template_id].to_dict()
        return None

    def find_by_genre(self, genre: str) -> Optional[Dict[str, Any]]:
        try:
            g = GameGenre(genre)
        except ValueError:
            for key, t in self._templates.items():
                if key == genre or t.genre.value == genre:
                    return t.to_dict()
            return None
        for t in self._templates.values():
            if t.genre == g:
                return t.to_dict()
        return None

    def scaffold(self, project_name: str, genre: str) -> ScaffoldResult:
        template = None
        for key, t in self._templates.items():
            if key == genre or t.genre.value == genre:
                template = t
                break

        if not template:
            try:
                g = GameGenre(genre)
                for t in self._templates.values():
                    if t.genre == g:
                        template = t
                        break
            except ValueError:
                pass

        if not template:
            template = self._templates.get("platformer")

        template.usage_count += 1

        files = []
        for ft in template.file_structure:
            files.append({
                "path": ft.path,
                "type": ft.file_type,
                "description": ft.description,
                "is_entry_point": ft.is_entry_point,
            })

        entities = [e.to_dict() for e in template.entity_templates]
        systems = [s.to_dict() for s in template.system_templates]

        result = ScaffoldResult(
            project_name=project_name,
            genre=template.genre.value,
            template_id=template.id,
            files=files,
            entities=entities,
            systems=systems,
            config=template.default_config,
        )
        self._scaffolds.append(result)
        return result

    def list_genres(self) -> List[Dict[str, Any]]:
        return [{"value": g.value, "name": g.value.replace("_", " ").title()} for g in GameGenre]

    def record_result(self, genre: str, success: bool) -> None:
        for t in self._templates.values():
            if t.genre.value == genre:
                if success:
                    t.success_count += 1
                else:
                    t.failure_count += 1
                break

    def get_stats(self) -> Dict[str, Any]:
        return {
            "total_templates": len(self._templates),
            "total_genres": len(GameGenre),
            "by_maturity": {m.value: sum(1 for t in self._templates.values() if t.maturity == m) for m in TemplateMaturity},
            "by_genre": {t.genre.value: t.success_rate for t in self._templates.values()},
            "total_scaffolds": len(self._scaffolds),
            "avg_success_rate": sum(t.success_rate for t in self._templates.values()) / len(self._templates) if self._templates else 0.0,
        }


_game_template_library: Optional[GameTemplateLibrary] = None


def get_game_template_library() -> GameTemplateLibrary:
    global _game_template_library
    if _game_template_library is None:
        _game_template_library = GameTemplateLibrary()
    return _game_template_library
