"""
Project Template - Game genre project templates and instantiation for the AI editor.

Architecture:
    ProjectTemplate/
    |-- GameGenre (genre classification enumeration)
    |-- TemplateAsset (packaged starter asset dataclass)
    |-- TemplateScene (pre-built scene structure dataclass)
    |-- ProjectTemplate (complete template definition dataclass)
    |-- ProjectTemplateSystem (global template orchestration)

Provides the AI game editor with pre-configured project templates for common
game genres. Each template includes starter scenes, object presets, behavior
configurations, and asset placeholders that the AI can build upon.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Dict, List, Optional


class GameGenre(Enum):
    PLATFORMER = auto()
    TOP_DOWN_RPG = auto()
    SHOOTER = auto()
    PUZZLE = auto()
    RACING = auto()
    TOWER_DEFENSE = auto()
    ROGUELIKE = auto()
    VISUAL_NOVEL = auto()
    ENDLESS_RUNNER = auto()
    SIMULATION = auto()
    CARD_GAME = auto()
    CUSTOM = auto()


@dataclass
class TemplateAsset:
    asset_name: str = ""
    asset_type: str = "sprite"
    description: str = ""
    suggested_size: str = "64x64"
    placeholder_color: str = "#888888"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.asset_name,
            "type": self.asset_type,
            "description": self.description,
            "size": self.suggested_size,
        }


@dataclass
class TemplateScene:
    scene_name: str = ""
    scene_type: str = "gameplay"
    objects: List[Dict[str, Any]] = field(default_factory=list)
    layer_count: int = 3
    camera_follow: bool = True
    background_color: str = "#222222"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.scene_name,
            "type": self.scene_type,
            "object_count": len(self.objects),
            "layers": self.layer_count,
            "camera_follow": self.camera_follow,
        }


@dataclass
class ProjectTemplate:
    template_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    genre: GameGenre = GameGenre.CUSTOM
    description: str = ""
    scenes: List[TemplateScene] = field(default_factory=list)
    assets: List[TemplateAsset] = field(default_factory=list)
    behaviors: List[str] = field(default_factory=list)
    input_actions: List[str] = field(default_factory=list)
    target_resolution: Tuple[int, int] = (800, 600)
    physics_gravity: float = 9.8
    starter_code: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "template_id": self.template_id,
            "name": self.name,
            "genre": self.genre.name,
            "description": self.description,
            "scene_count": len(self.scenes),
            "asset_count": len(self.assets),
            "behavior_count": len(self.behaviors),
            "resolution": list(self.target_resolution),
        }


class ProjectTemplateSystem:
    _instance: Optional["ProjectTemplateSystem"] = None

    def __init__(self):
        self._templates: Dict[str, ProjectTemplate] = {}
        self._register_builtin_templates()

    def _register_builtin_templates(self) -> None:
        self._register_platformer()
        self._register_top_down_rpg()
        self._register_shooter()
        self._register_puzzle()

    def _register_platformer(self) -> None:
        template = ProjectTemplate(
            name="2D Platformer",
            genre=GameGenre.PLATFORMER,
            description="Side-scrolling platformer with jumping, collecting, and enemy avoidance.",
            behaviors=["PlatformerCharacter", "Collectible", "EnemyPatrol", "DeathZone"],
            input_actions=["move_left", "move_right", "jump", "interact"],
            scenes=[
                TemplateScene(
                    scene_name="Level1",
                    scene_type="gameplay",
                    objects=[
                        {"type": "Player", "x": 100, "y": 400},
                        {"type": "Ground", "x": 0, "y": 550, "width": 800},
                        {"type": "Platform", "x": 300, "y": 400, "width": 120},
                        {"type": "Platform", "x": 550, "y": 300, "width": 120},
                        {"type": "Coin", "x": 350, "y": 370},
                        {"type": "Coin", "x": 600, "y": 270},
                        {"type": "Enemy", "x": 500, "y": 530},
                        {"type": "GoalFlag", "x": 750, "y": 450},
                    ],
                ),
            ],
            assets=[
                TemplateAsset("player", "sprite", "Player character", "32x48"),
                TemplateAsset("ground", "tile", "Ground tile texture", "64x64", "#4a7c59"),
                TemplateAsset("platform", "tile", "Floating platform", "64x32", "#8b7355"),
                TemplateAsset("coin", "sprite", "Collectible coin", "24x24", "#ffd700"),
                TemplateAsset("enemy", "sprite", "Basic enemy", "32x32", "#cc3333"),
                TemplateAsset("flag", "sprite", "Level end flag", "32x48", "#33cc33"),
                TemplateAsset("background", "background", "Sky background", "800x600", "#87ceeb"),
            ],
        )
        self._templates[template.template_id] = template

    def _register_top_down_rpg(self) -> None:
        template = ProjectTemplate(
            name="Top-Down RPG",
            genre=GameGenre.TOP_DOWN_RPG,
            description="Top-down role-playing game with four-direction movement, NPCs, and quest items.",
            behaviors=["TopDownMovement", "Interactable", "DialogTrigger", "ItemPickup"],
            input_actions=["move_up", "move_down", "move_left", "move_right", "interact", "inventory"],
            scenes=[
                TemplateScene(
                    scene_name="Village",
                    scene_type="gameplay",
                    objects=[
                        {"type": "Player", "x": 400, "y": 300},
                        {"type": "Wall", "x": 200, "y": 150, "width": 32, "height": 200},
                        {"type": "Wall", "x": 400, "y": 100, "width": 200, "height": 32},
                        {"type": "NPC", "x": 300, "y": 200, "dialog_id": "elder_greeting"},
                        {"type": "NPC", "x": 500, "y": 350, "dialog_id": "shopkeeper"},
                        {"type": "Item", "x": 250, "y": 450, "item_id": "health_potion"},
                        {"type": "Chest", "x": 600, "y": 200, "contains": "sword"},
                    ],
                    background_color="#5a8a4a",
                ),
            ],
            assets=[
                TemplateAsset("player", "sprite", "Player character (top-down)", "32x32"),
                TemplateAsset("wall", "tile", "Wall obstacle", "32x32", "#666666"),
                TemplateAsset("npc", "sprite", "Non-player character", "32x32", "#4488cc"),
                TemplateAsset("item", "sprite", "Item pickup", "16x16", "#ffaa00"),
                TemplateAsset("chest", "sprite", "Treasure chest", "32x32", "#8b4513"),
                TemplateAsset("ground", "tile", "Grass ground", "32x32", "#4a8a3a"),
            ],
        )
        self._templates[template.template_id] = template

    def _register_shooter(self) -> None:
        template = ProjectTemplate(
            name="Space Shooter",
            genre=GameGenre.SHOOTER,
            description="Top-down space shooter with player ship, enemy waves, and power-ups.",
            behaviors=["ShipMovement", "BulletShooter", "EnemyWave", "PowerUp"],
            input_actions=["move_up", "move_down", "move_left", "move_right", "shoot", "special"],
            scenes=[
                TemplateScene(
                    scene_name="Space",
                    scene_type="gameplay",
                    objects=[
                        {"type": "PlayerShip", "x": 400, "y": 500},
                        {"type": "EnemySpawner", "x": 200, "y": -50},
                        {"type": "EnemySpawner", "x": 600, "y": -50},
                        {"type": "StarField", "x": 0, "y": 0},
                    ],
                    background_color="#000011",
                ),
            ],
            assets=[
                TemplateAsset("player_ship", "sprite", "Player spaceship", "48x48", "#3399ff"),
                TemplateAsset("enemy_basic", "sprite", "Basic enemy ship", "32x32", "#ff3333"),
                TemplateAsset("bullet", "sprite", "Player bullet", "8x16", "#ffff00"),
                TemplateAsset("enemy_bullet", "sprite", "Enemy bullet", "8x16", "#ff6600"),
                TemplateAsset("power_up", "sprite", "Power-up item", "24x24", "#00ff00"),
                TemplateAsset("explosion", "spritesheet", "Explosion animation", "64x64", "#ff8800"),
                TemplateAsset("star", "tile", "Star field tile", "64x64", "#111122"),
            ],
        )
        self._templates[template.template_id] = template

    def _register_puzzle(self) -> None:
        template = ProjectTemplate(
            name="Match-3 Puzzle",
            genre=GameGenre.PUZZLE,
            description="Grid-based match-three puzzle game with score tracking and combos.",
            behaviors=["GridPiece", "MatchDetector", "ScoreTracker", "ComboSystem"],
            input_actions=["select_piece", "swipe"],
            scenes=[
                TemplateScene(
                    scene_name="GameBoard",
                    scene_type="gameplay",
                    objects=[
                        {"type": "GameGrid", "x": 0, "y": 0, "cols": 8, "rows": 8, "cell_size": 64},
                        {"type": "ScoreDisplay", "x": 600, "y": 20},
                        {"type": "TimerDisplay", "x": 600, "y": 60},
                    ],
                    background_color="#1a1a2e",
                ),
            ],
            assets=[
                TemplateAsset("gem_red", "sprite", "Red gem", "48x48", "#ff4444"),
                TemplateAsset("gem_blue", "sprite", "Blue gem", "48x48", "#4444ff"),
                TemplateAsset("gem_green", "sprite", "Green gem", "48x48", "#44ff44"),
                TemplateAsset("gem_yellow", "sprite", "Yellow gem", "48x48", "#ffff44"),
                TemplateAsset("gem_purple", "sprite", "Purple gem", "48x48", "#ff44ff"),
                TemplateAsset("gem_orange", "sprite", "Orange gem", "48x48", "#ff8844"),
                TemplateAsset("board_bg", "background", "Board background", "512x512", "#0f0f23"),
                TemplateAsset("selector", "sprite", "Grid selector highlight", "64x64", "rgba(255,255,255,0.3)"),
            ],
        )
        self._templates[template.template_id] = template

    @classmethod
    def get_instance(cls) -> "ProjectTemplateSystem":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def get(self, template_id: str) -> Optional[ProjectTemplate]:
        return self._templates.get(template_id)

    def register(self, template: ProjectTemplate) -> str:
        self._templates[template.template_id] = template
        return template.template_id

    def list_by_genre(self, genre: Optional[GameGenre] = None) -> List[ProjectTemplate]:
        if genre:
            return [t for t in self._templates.values() if t.genre == genre]
        return list(self._templates.values())

    def list_all(self) -> List[ProjectTemplate]:
        return list(self._templates.values())

    def list_genres(self) -> List[Dict[str, Any]]:
        return [{
            "genre": g.name,
            "template_count": sum(1 for t in self._templates.values() if t.genre == g),
        } for g in GameGenre]

    def get_template_names(self) -> List[str]:
        return [t.name for t in self._templates.values()]

    def remove(self, template_id: str) -> bool:
        if template_id in self._templates:
            del self._templates[template_id]
            return True
        return False

    def get_stats(self) -> Dict[str, Any]:
        return {
            "template_count": len(self._templates),
            "templates": [t.to_dict() for t in self._templates.values()],
            "genres": [g.name for g in GameGenre],
            "total_scenes": sum(len(t.scenes) for t in self._templates.values()),
            "total_assets": sum(len(t.assets) for t in self._templates.values()),
        }


def get_project_template_system() -> ProjectTemplateSystem:
    return ProjectTemplateSystem.get_instance()
