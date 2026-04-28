"""
SparkAI Agent - Template Skill

Template Skills grow a library of project skeletons from experience.
They enable agents to scaffold stable game architectures by reusing
proven patterns rather than building from scratch each time.

Template types include game genres, engine configurations,
and project structures that evolve as the agent gains experience.
"""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from sparkai.agent.skills.base import Skill, SkillRegistry


@dataclass
class GameTemplate:
    """
    A reusable game project template.

    Templates capture the architecture, file structure,
    and configuration patterns for specific game types.
    They evolve as the agent successfully creates games.
    """

    name: str = ""
    genre: str = ""
    description: str = ""
    file_structure: Dict[str, str] = field(default_factory=dict)
    engine_config: Dict[str, Any] = field(default_factory=dict)
    default_systems: List[str] = field(default_factory=list)
    default_components: List[str] = field(default_factory=list)
    scene_layout: Dict[str, Any] = field(default_factory=dict)
    success_count: int = 0
    fail_count: int = 0
    id: str = field(default_factory=lambda: str(uuid.uuid4()))

    @property
    def reliability(self) -> float:
        total = self.success_count + self.fail_count
        if total == 0:
            return 0.5
        return self.success_count / total

    def record_success(self) -> None:
        self.success_count += 1

    def record_failure(self) -> None:
        self.fail_count += 1

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "genre": self.genre,
            "description": self.description,
            "file_structure": self.file_structure,
            "default_systems": self.default_systems,
            "default_components": self.default_components,
            "reliability": self.reliability,
            "success_count": self.success_count,
            "fail_count": self.fail_count,
        }


class TemplateLibrary:
    """
    Library of game project templates that grows from experience.

    Agents can query templates by genre, scaffold new projects
    from templates, and record outcomes to improve reliability scores.
    """

    def __init__(self):
        self._templates: Dict[str, GameTemplate] = {}
        self._load_builtin_templates()

    def _load_builtin_templates(self) -> None:
        builtin = [
            GameTemplate(
                name="2d-platformer",
                genre="platformer",
                description="2D side-scrolling platformer with physics and AI enemies",
                file_structure={
                    "scenes/": "Game scenes",
                    "assets/sprites/": "Sprite assets",
                    "assets/audio/": "Audio assets",
                    "scripts/": "Game scripts",
                },
                default_systems=["physics_system", "render_system", "collision_system", "ai_system", "input_system"],
                default_components=["transform", "renderable", "physics_body", "collider", "input_receiver", "animator"],
                scene_layout={"layers": ["background", "gameplay", "foreground", "ui"]},
            ),
            GameTemplate(
                name="3d-adventure",
                genre="adventure",
                description="3D adventure game with AI NPCs and branching narrative",
                file_structure={
                    "scenes/": "Game scenes",
                    "assets/meshes/": "3D mesh assets",
                    "assets/textures/": "Texture assets",
                    "assets/audio/": "Audio assets",
                    "narrative/": "Story and quest definitions",
                    "npcs/": "NPC definitions",
                },
                default_systems=["physics_system", "render_system", "ai_system", "animation_system", "audio_system", "collision_system"],
                default_components=["transform", "renderable", "physics_body", "collider", "camera", "ai_brain", "animator", "audio_source"],
                scene_layout={"layers": ["skybox", "terrain", "objects", "characters", "effects", "ui"]},
            ),
            GameTemplate(
                name="puzzle-game",
                genre="puzzle",
                description="Logic puzzle game with AI-generated levels",
                file_structure={
                    "scenes/": "Game scenes",
                    "assets/": "Visual assets",
                    "levels/": "Level definitions",
                    "logic/": "Game logic scripts",
                },
                default_systems=["render_system", "input_system", "tween_system", "audio_system"],
                default_components=["transform", "renderable", "input_receiver", "tween", "audio_source"],
                scene_layout={"layers": ["background", "grid", "pieces", "effects", "ui"]},
            ),
            GameTemplate(
                name="rpg-world",
                genre="rpg",
                description="RPG with AI-driven NPCs, quests, and dynamic world",
                file_structure={
                    "scenes/": "World maps and interiors",
                    "assets/": "All game assets",
                    "npcs/": "NPC definitions with AI brains",
                    "quests/": "Quest definitions",
                    "narrative/": "Story and dialogue",
                    "items/": "Item definitions",
                    "combat/": "Combat system scripts",
                },
                default_systems=["physics_system", "render_system", "ai_system", "collision_system", "animation_system", "audio_system", "input_system"],
                default_components=["transform", "renderable", "physics_body", "collider", "ai_brain", "animator", "audio_source", "input_receiver"],
                scene_layout={"layers": ["terrain", "objects", "characters", "effects", "ui"]},
            ),
            GameTemplate(
                name="strategy-game",
                genre="strategy",
                description="Real-time strategy with AI opponent and unit management",
                file_structure={
                    "scenes/": "Game maps",
                    "assets/": "Game assets",
                    "units/": "Unit definitions",
                    "ai/": "AI strategy scripts",
                    "maps/": "Map definitions",
                },
                default_systems=["physics_system", "render_system", "ai_system", "collision_system", "input_system"],
                default_components=["transform", "renderable", "collider", "ai_brain", "input_receiver"],
                scene_layout={"layers": ["terrain", "buildings", "units", "effects", "fog", "ui"]},
            ),
        ]
        for template in builtin:
            self._templates[template.name] = template

    def register(self, template: GameTemplate) -> None:
        self._templates[template.name] = template

    def get(self, name: str) -> Optional[GameTemplate]:
        return self._templates.get(name)

    def find_by_genre(self, genre: str) -> List[GameTemplate]:
        return [t for t in self._templates.values() if t.genre == genre]

    def find_best_for_genre(self, genre: str) -> Optional[GameTemplate]:
        templates = self.find_by_genre(genre)
        if not templates:
            return None
        return max(templates, key=lambda t: t.reliability)

    def list_templates(self) -> List[GameTemplate]:
        return list(self._templates.values())

    def list_genres(self) -> List[str]:
        return list(set(t.genre for t in self._templates.values()))

    def scaffold_project(self, template_name: str, project_name: str) -> Dict[str, Any]:
        template = self._templates.get(template_name)
        if not template:
            return {"error": f"Template '{template_name}' not found"}

        return {
            "project_name": project_name,
            "template": template_name,
            "genre": template.genre,
            "file_structure": template.file_structure,
            "systems": template.default_systems,
            "components": template.default_components,
            "scene_layout": template.scene_layout,
            "engine_config": template.engine_config,
        }


class TemplateSkill(Skill):
    """
    Skill for scaffolding game projects from templates.

    This skill grows a library of project skeletons from
    experience, enabling agents to create stable architectures
    rather than building from scratch.
    """

    def __init__(self):
        super().__init__(
            name="template_skill",
            description="Scaffold game projects from reusable templates",
            category="game_creation",
            instructions=(
                "Use this skill to scaffold game projects from proven templates.\n"
                "1. Identify the game genre and requirements\n"
                "2. Select the best matching template from the library\n"
                "3. Customize the template for the specific project\n"
                "4. Record outcomes to improve template reliability"
            ),
            steps=[
                "Identify game genre and core mechanics",
                "Select matching template from library",
                "Customize template with project-specific settings",
                "Generate file structure and initial scenes",
                "Configure default systems and components",
                "Verify the scaffolded project builds correctly",
            ],
            verification=[
                "Project file structure is complete",
                "All default systems are registered",
                "Scene hierarchy is properly configured",
                "Engine starts without errors",
            ],
        )
        self._library = TemplateLibrary()

    @property
    def library(self) -> TemplateLibrary:
        return self._library

    def scaffold(self, genre: str, project_name: str) -> Dict[str, Any]:
        template = self._library.find_best_for_genre(genre)
        if template:
            return self._library.scaffold_project(template.name, project_name)
        return {
            "project_name": project_name,
            "genre": genre,
            "message": "No matching template found, using generic scaffold",
            "systems": ["render_system", "input_system"],
            "components": ["transform", "renderable"],
        }


SkillRegistry.register(TemplateSkill())
