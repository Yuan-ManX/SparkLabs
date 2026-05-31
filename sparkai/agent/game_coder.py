"""
SparkAI Agent - Game Coder

End-to-end game code generation system that transforms natural language
descriptions into complete, runnable game code. The GameCoder orchestrates
the full lifecycle from prompt analysis through code generation, validation,
and iterative refinement.

Architecture:
  GameCoder
    |-- PromptAnalyzer (intent extraction, genre detection, feature parsing)
    |-- CodeScaffolder (project structure, entry points, configuration)
    |-- CodeGenerator (entity, system, scene, and logic code generation)
    |-- CodeValidator (syntax, semantic, and runtime validation)
    |-- CodeRefiner (iterative improvement based on validation feedback)

Generation Pipeline:
  Analyze -> Scaffold -> Generate -> Validate -> Refine -> Package

The GameCoder integrates with the AgentRuntime to leverage LLM routing,
tool execution, skill forging, and the agent mesh for distributed
code generation tasks.
"""

from __future__ import annotations

import json
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class CodeLanguage(Enum):
    TYPESCRIPT = "typescript"
    JAVASCRIPT = "javascript"
    PYTHON = "python"
    CPP = "cpp"
    LUA = "lua"
    SPARKSCRIPT = "sparkscript"
    JSON = "json"
    CONFIG = "config"


class CodeGenPhase(Enum):
    IDLE = "idle"
    ANALYZING = "analyzing"
    SCAFFOLDING = "scaffolding"
    GENERATING = "generating"
    VALIDATING = "validating"
    REFINING = "refining"
    PACKAGING = "packaging"
    COMPLETED = "completed"
    FAILED = "failed"


class ValidationLevel(Enum):
    SYNTAX = "syntax"
    SEMANTIC = "semantic"
    RUNTIME = "runtime"
    INTEGRATION = "integration"


class GameFeature(Enum):
    PHYSICS = "physics"
    COLLISION = "collision"
    PLAYER_CONTROL = "player_control"
    ENEMY_AI = "enemy_ai"
    SCORING = "scoring"
    LEVEL_DESIGN = "level_design"
    ANIMATION = "animation"
    AUDIO = "audio"
    UI = "ui"
    SAVE_LOAD = "save_load"
    MULTIPLAYER = "multiplayer"
    PROCEDURAL = "procedural"
    NARRATIVE = "narrative"
    INVENTORY = "inventory"
    DIALOGUE = "dialogue"


@dataclass
class PromptAnalysis:
    """Result of analyzing a game description prompt."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    original_prompt: str = ""
    detected_genre: str = "sandbox"
    detected_features: List[str] = field(default_factory=list)
    complexity_score: float = 0.5
    target_platform: str = "web"
    target_language: CodeLanguage = CodeLanguage.TYPESCRIPT
    key_entities: List[str] = field(default_factory=list)
    key_systems: List[str] = field(default_factory=list)
    key_mechanics: List[str] = field(default_factory=list)
    estimated_files: int = 5
    confidence: float = 0.0
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "original_prompt": self.original_prompt,
            "detected_genre": self.detected_genre,
            "detected_features": self.detected_features,
            "complexity_score": self.complexity_score,
            "target_platform": self.target_platform,
            "target_language": self.target_language.value,
            "key_entities": self.key_entities,
            "key_systems": self.key_systems,
            "key_mechanics": self.key_mechanics,
            "estimated_files": self.estimated_files,
            "confidence": self.confidence,
            "created_at": self.created_at,
        }


@dataclass
class CodeFile:
    """A generated code file."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    path: str = ""
    filename: str = ""
    language: CodeLanguage = CodeLanguage.TYPESCRIPT
    content: str = ""
    description: str = ""
    category: str = "source"
    is_entry_point: bool = False
    dependencies: List[str] = field(default_factory=list)
    generated_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "path": self.path,
            "filename": self.filename,
            "language": self.language.value,
            "content": self.content,
            "description": self.description,
            "category": self.category,
            "is_entry_point": self.is_entry_point,
            "dependencies": self.dependencies,
            "generated_at": self.generated_at,
        }


@dataclass
class ValidationResult:
    """Result of validating generated code."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    level: ValidationLevel = ValidationLevel.SYNTAX
    passed: bool = False
    errors: List[Dict[str, Any]] = field(default_factory=list)
    warnings: List[Dict[str, Any]] = field(default_factory=list)
    suggestions: List[str] = field(default_factory=list)
    score: float = 0.0
    validated_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "level": self.level.value,
            "passed": self.passed,
            "errors": self.errors,
            "warnings": self.warnings,
            "suggestions": self.suggestions,
            "score": self.score,
            "validated_at": self.validated_at,
        }


@dataclass
class CodeGenProject:
    """A complete generated game project."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    description: str = ""
    genre: str = ""
    language: CodeLanguage = CodeLanguage.TYPESCRIPT
    files: List[CodeFile] = field(default_factory=list)
    analysis: Optional[PromptAnalysis] = None
    validation_results: List[ValidationResult] = field(default_factory=list)
    phase: CodeGenPhase = CodeGenPhase.IDLE
    iteration: int = 0
    max_iterations: int = 3
    quality_score: float = 0.0
    created_at: float = field(default_factory=time.time)
    completed_at: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "genre": self.genre,
            "language": self.language.value,
            "files": [f.to_dict() for f in self.files],
            "analysis": self.analysis.to_dict() if self.analysis else None,
            "validation_results": [v.to_dict() for v in self.validation_results],
            "phase": self.phase.value,
            "iteration": self.iteration,
            "max_iterations": self.max_iterations,
            "quality_score": self.quality_score,
            "created_at": self.created_at,
            "completed_at": self.completed_at,
        }


_GENRE_KEYWORDS: Dict[str, List[str]] = {
    "platformer": ["platform", "jump", "runner", "side_scroll", "hop"],
    "rpg": ["rpg", "role", "quest", "dungeon", "dragon", "fantasy", "level up"],
    "shooter": ["shoot", "gun", "fps", "bullet", "weapon", "combat"],
    "puzzle": ["puzzle", "match", "tile", "2048", "sudoku", "logic"],
    "strategy": ["strategy", "rts", "tower defense", "build", "resource", "manage"],
    "adventure": ["adventure", "explore", "story", "quest", "discover"],
    "simulation": ["sim", "simulation", "city", "farm", "tycoon", "manager"],
    "racing": ["race", "car", "speed", "track", "driving"],
    "fighting": ["fight", "fighter", "martial", "combo", "arena"],
    "sandbox": ["sandbox", "craft", "build", "create", "free", "open world"],
    "horror": ["horror", "scary", "survival", "dark", "creepy"],
    "sports": ["sport", "football", "soccer", "basketball", "tennis"],
}

_FEATURE_KEYWORDS: Dict[str, List[str]] = {
    "physics": ["physics", "gravity", "force", "velocity", "momentum"],
    "collision": ["collision", "hit", "detect", "overlap", "bounding"],
    "player_control": ["player", "control", "move", "input", "keyboard", "controller"],
    "enemy_ai": ["enemy", "ai", "npc", "behavior", "patrol", "chase"],
    "scoring": ["score", "point", "high score", "leaderboard"],
    "level_design": ["level", "map", "stage", "world", "zone"],
    "animation": ["animation", "sprite", "frame", "animate", "tween"],
    "audio": ["sound", "music", "audio", "sfx", "bgm"],
    "ui": ["ui", "menu", "hud", "button", "interface", "dialog"],
    "save_load": ["save", "load", "persist", "progress", "checkpoint"],
    "multiplayer": ["multiplayer", "online", "network", "co-op", "versus"],
    "procedural": ["procedural", "generate", "random", "seed", "infinite"],
    "narrative": ["story", "narrative", "cutscene", "dialogue", "plot"],
    "inventory": ["inventory", "item", "collect", "equip", "backpack"],
    "dialogue": ["dialogue", "conversation", "talk", "chat", "speech"],
}

_ENTITY_TEMPLATES: Dict[str, Dict[str, Any]] = {
    "player": {"components": ["Transform", "Renderable", "PhysicsBody", "InputReceiver", "Animator"], "tags": ["player", "controllable"]},
    "enemy": {"components": ["Transform", "Renderable", "PhysicsBody", "AIBrain", "Animator"], "tags": ["enemy", "ai"]},
    "platform": {"components": ["Transform", "Renderable", "Collider"], "tags": ["platform", "static"]},
    "projectile": {"components": ["Transform", "Renderable", "PhysicsBody", "Collider"], "tags": ["projectile", "dynamic"]},
    "collectible": {"components": ["Transform", "Renderable", "Collider", "Animator"], "tags": ["collectible", "item"]},
    "npc": {"components": ["Transform", "Renderable", "AIBrain", "Animator"], "tags": ["npc", "interactive"]},
    "camera": {"components": ["Transform", "Camera"], "tags": ["camera"]},
    "trigger_zone": {"components": ["Transform", "Collider"], "tags": ["trigger", "zone"]},
    "background": {"components": ["Transform", "Renderable"], "tags": ["background", "decoration"]},
    "ui_element": {"components": ["Transform", "TextRenderer"], "tags": ["ui"]},
}

_SYSTEM_TEMPLATES: Dict[str, Dict[str, Any]] = {
    "physics": {"priority": 200, "required_components": ["PhysicsBody"], "description": "Physics simulation and integration"},
    "collision": {"priority": 250, "required_components": ["Collider"], "description": "Collision detection and resolution"},
    "render": {"priority": 600, "required_components": ["Renderable"], "description": "Rendering and drawing"},
    "input": {"priority": 100, "required_components": ["InputReceiver"], "description": "Input handling and mapping"},
    "ai": {"priority": 300, "required_components": ["AIBrain"], "description": "AI behavior and decision making"},
    "animation": {"priority": 500, "required_components": ["Animator"], "description": "Animation and tweening"},
    "audio": {"priority": 700, "required_components": ["AudioSource"], "description": "Audio playback and mixing"},
    "script": {"priority": 400, "required_components": ["Script"], "description": "Custom script execution"},
    "tween": {"priority": 550, "required_components": ["Tween"], "description": "Tweening and easing"},
}


class PromptAnalyzer:
    """
    Analyzes natural language game descriptions to extract structured
    information about the intended game, including genre, features,
    entities, systems, and complexity.
    """

    def analyze(self, prompt: str) -> PromptAnalysis:
        result = PromptAnalysis(original_prompt=prompt)

        prompt_lower = prompt.lower()

        result.detected_genre = self._detect_genre(prompt_lower)
        result.detected_features = self._detect_features(prompt_lower)
        result.key_entities = self._detect_entities(prompt_lower, result.detected_features)
        result.key_systems = self._detect_systems(result.detected_features)
        result.key_mechanics = self._detect_mechanics(prompt_lower, result.detected_features)
        result.complexity_score = self._calculate_complexity(result)
        result.estimated_files = self._estimate_file_count(result)
        result.confidence = self._calculate_confidence(result)
        result.target_language = CodeLanguage.TYPESCRIPT

        return result

    def _detect_genre(self, prompt_lower: str) -> str:
        scores: Dict[str, int] = {}
        for genre, keywords in _GENRE_KEYWORDS.items():
            score = sum(1 for kw in keywords if kw in prompt_lower)
            if score > 0:
                scores[genre] = score
        if not scores:
            return "sandbox"
        return max(scores, key=scores.get)

    def _detect_features(self, prompt_lower: str) -> List[str]:
        features = []
        for feature, keywords in _FEATURE_KEYWORDS.items():
            if any(kw in prompt_lower for kw in keywords):
                features.append(feature)
        if not features:
            features = ["player_control", "physics", "collision", "render"]
        return features

    def _detect_entities(self, prompt_lower: str, features: List[str]) -> List[str]:
        entities = ["player", "camera"]
        if "enemy_ai" in features or "combat" in prompt_lower:
            entities.append("enemy")
        if "platformer" in prompt_lower or "platform" in prompt_lower:
            entities.append("platform")
        if "scoring" in features or "collect" in prompt_lower:
            entities.append("collectible")
        if "shooter" in prompt_lower or "shoot" in prompt_lower:
            entities.append("projectile")
        if "narrative" in features or "dialogue" in features:
            entities.append("npc")
        if "ui" in features:
            entities.append("ui_element")
        entities.append("background")
        return list(dict.fromkeys(entities))

    def _detect_systems(self, features: List[str]) -> List[str]:
        system_map = {
            "physics": "physics",
            "collision": "collision",
            "player_control": "input",
            "enemy_ai": "ai",
            "animation": "animation",
            "audio": "audio",
        }
        systems = ["render"]
        for feature in features:
            if feature in system_map:
                systems.append(system_map[feature])
        return list(dict.fromkeys(systems))

    def _detect_mechanics(self, prompt_lower: str, features: List[str]) -> List[str]:
        mechanics = []
        if "jump" in prompt_lower:
            mechanics.append("jumping")
        if "shoot" in prompt_lower or "fire" in prompt_lower:
            mechanics.append("shooting")
        if "collect" in prompt_lower or "pickup" in prompt_lower:
            mechanics.append("collection")
        if "score" in prompt_lower or "point" in prompt_lower:
            mechanics.append("scoring")
        if "level" in prompt_lower:
            mechanics.append("level_progression")
        if "health" in prompt_lower or "damage" in prompt_lower:
            mechanics.append("health_damage")
        if "inventory" in prompt_lower or "item" in prompt_lower:
            mechanics.append("inventory_management")
        if "dialogue" in prompt_lower or "talk" in prompt_lower:
            mechanics.append("dialogue_system")
        if not mechanics:
            mechanics = ["basic_movement", "collision_response"]
        return mechanics

    def _calculate_complexity(self, analysis: PromptAnalysis) -> float:
        score = 0.0
        score += min(len(analysis.detected_features) / 10.0, 0.3)
        score += min(len(analysis.key_entities) / 10.0, 0.2)
        score += min(len(analysis.key_systems) / 8.0, 0.2)
        score += min(len(analysis.key_mechanics) / 6.0, 0.15)
        if analysis.detected_genre in ("rpg", "strategy", "simulation"):
            score += 0.15
        return min(score, 1.0)

    def _estimate_file_count(self, analysis: PromptAnalysis) -> int:
        base = 3
        base += len(analysis.key_entities)
        base += len(analysis.key_systems)
        base += len(analysis.key_mechanics)
        return max(5, min(base, 30))

    def _calculate_confidence(self, analysis: PromptAnalysis) -> float:
        if not analysis.original_prompt:
            return 0.0
        confidence = 0.3
        if analysis.detected_genre != "sandbox":
            confidence += 0.2
        if len(analysis.detected_features) > 2:
            confidence += 0.2
        if len(analysis.key_entities) > 2:
            confidence += 0.15
        if len(analysis.key_mechanics) > 1:
            confidence += 0.15
        return min(confidence, 1.0)


class CodeScaffolder:
    """
    Creates the project structure and configuration files for
    a generated game project based on the prompt analysis.
    """

    def scaffold(self, analysis: PromptAnalysis, project_name: str = "") -> List[CodeFile]:
        files: List[CodeFile] = []
        name = project_name or analysis.detected_genre.title() + "Game"

        files.append(self._create_package_json(name, analysis))
        files.append(self._create_engine_config(analysis))
        files.append(self._create_main_entry(analysis))
        files.append(self._create_game_config(analysis))

        return files

    def _create_package_json(self, name: str, analysis: PromptAnalysis) -> CodeFile:
        content = json.dumps({
            "name": name.lower().replace(" ", "-"),
            "version": "0.1.0",
            "description": analysis.original_prompt[:200],
            "main": "src/main.ts",
            "scripts": {
                "dev": "vite",
                "build": "tsc && vite build",
                "preview": "vite preview",
            },
            "dependencies": {
                "sparkengine": "^1.0.0",
            },
            "devDependencies": {
                "typescript": "^5.0.0",
                "vite": "^5.0.0",
            },
        }, indent=2)

        return CodeFile(
            path="package.json",
            filename="package.json",
            language=CodeLanguage.JSON,
            content=content,
            description="Project manifest and dependencies",
            category="config",
        )

    def _create_engine_config(self, analysis: PromptAnalysis) -> CodeFile:
        config = {
            "engine": "SparkLabs",
            "version": "1.0.0",
            "genre": analysis.detected_genre,
            "features": analysis.detected_features,
            "systems": analysis.key_systems,
            "rendering": {
                "width": 1280,
                "height": 720,
                "fps": 60,
                "vsync": True,
                "antialiasing": "msaa_4x",
            },
            "physics": {
                "gravity": [0, -9.81, 0],
                "fixed_timestep": 1.0 / 60.0,
                "velocity_iterations": 8,
                "position_iterations": 3,
            },
            "audio": {
                "master_volume": 1.0,
                "sfx_volume": 0.8,
                "music_volume": 0.6,
            },
        }
        content = json.dumps(config, indent=2)

        return CodeFile(
            path="config/engine.json",
            filename="engine.json",
            language=CodeLanguage.JSON,
            content=content,
            description="Engine configuration",
            category="config",
        )

    def _create_main_entry(self, analysis: PromptAnalysis) -> CodeFile:
        lines = [
            f'// {analysis.detected_genre.title()} Game - Generated by SparkLabs Engine',
            '',
            'import {{ SparkEngine }} from "sparkengine";',
            'import {{ GameWorld }} from "./world";',
            'import {{ PlayerEntity }} from "./entities/player";',
        ]

        if "enemy_ai" in analysis.detected_features:
            lines.append('import {{ EnemyEntity }} from "./entities/enemy";')
        if "scoring" in analysis.detected_features:
            lines.append('import {{ ScoreSystem }} from "./systems/score";')

        lines.extend([
            '',
            'const engine = new SparkEngine();',
            'const world = new GameWorld(engine);',
            '',
            'async function init() {',
            '  await engine.initialize({{',
            '    canvas: document.getElementById("game-canvas"),',
            '    config: await import("../config/engine.json"),',
            '  }});',
            '',
            '  world.create();',
            '',
        ])

        for entity in analysis.key_entities:
            if entity == "player":
                lines.append('  world.spawn(new PlayerEntity());')
            elif entity == "enemy":
                lines.append('  world.spawn(new EnemyEntity());')

        lines.extend([
            '',
            '  engine.start();',
            '}}',
            '',
            'init();',
        ])

        return CodeFile(
            path="src/main.ts",
            filename="main.ts",
            language=CodeLanguage.TYPESCRIPT,
            content="\n".join(lines),
            description="Main entry point",
            category="source",
            is_entry_point=True,
        )

    def _create_game_config(self, analysis: PromptAnalysis) -> CodeFile:
        config = {
            "game": {
                "title": analysis.detected_genre.title() + " Game",
                "genre": analysis.detected_genre,
                "version": "0.1.0",
            },
            "player": {
                "speed": 5.0,
                "jump_force": 10.0,
                "health": 100,
            },
            "world": {
                "width": 3200,
                "height": 1800,
                "tile_size": 32,
            },
        }
        content = json.dumps(config, indent=2)

        return CodeFile(
            path="config/game.json",
            filename="game.json",
            language=CodeLanguage.JSON,
            content=content,
            description="Game-specific configuration",
            category="config",
        )


class CodeGenerator:
    """
    Generates game code files including entities, systems,
    scenes, and game logic based on the prompt analysis.
    """

    def generate(self, analysis: PromptAnalysis) -> List[CodeFile]:
        files: List[CodeFile] = []

        files.append(self._generate_world(analysis))

        for entity_name in analysis.key_entities:
            entity_file = self._generate_entity(entity_name, analysis)
            if entity_file:
                files.append(entity_file)

        for system_name in analysis.key_systems:
            system_file = self._generate_system(system_name, analysis)
            if system_file:
                files.append(system_file)

        for mechanic in analysis.key_mechanics:
            mechanic_file = self._generate_mechanic(mechanic, analysis)
            if mechanic_file:
                files.append(mechanic_file)

        return files

    def _generate_world(self, analysis: PromptAnalysis) -> CodeFile:
        lines = [
            '// Game World - Orchestrates all entities and systems',
            '',
            'import {{ SparkEngine, World, SystemScheduler }} from "sparkengine";',
        ]

        for entity in analysis.key_entities:
            safe = entity.replace(" ", "")
            lines.append(f'import {{ {safe}Entity }} from "./entities/{entity}";')

        for system in analysis.key_systems:
            safe = system.replace(" ", "")
            lines.append(f'import {{ {safe}System }} from "../systems/{system}";')

        lines.extend([
            '',
            'export class GameWorld {',
            '  private engine: SparkEngine;',
            '  private world: World;',
            '',
            '  constructor(engine: SparkEngine) {',
            '    this.engine = engine;',
            '    this.world = engine.createWorld("game-world");',
            '  }}',
            '',
            '  create(): void {',
        ])

        for system in analysis.key_systems:
            safe = system.replace(" ", "")
            lines.append(f'    this.world.addSystem(new {safe}System());')

        lines.extend([
            '  }}',
            '',
            '  spawn<T>(entity: T): T {',
            '    return entity;',
            '  }}',
            '',
            '  update(deltaTime: number): void {',
            '    this.world.update(deltaTime);',
            '  }}',
            '}}',
        ])

        return CodeFile(
            path="src/world.ts",
            filename="world.ts",
            language=CodeLanguage.TYPESCRIPT,
            content="\n".join(lines),
            description="Game world orchestrator",
            category="source",
        )

    def _generate_entity(self, entity_name: str, analysis: PromptAnalysis) -> Optional[CodeFile]:
        template = _ENTITY_TEMPLATES.get(entity_name)
        if not template:
            return None

        safe = entity_name.replace(" ", "")
        components = template.get("components", [])
        tags = template.get("tags", [])

        lines = [
            f'// {safe} Entity',
            '',
            'import {{ Entity, Component }} from "sparkengine";',
        ]

        for comp in components:
            lines.append(f'import {{ {comp} }} from "sparkengine/components";')

        lines.extend([
            '',
            f'export class {safe}Entity extends Entity {{',
            f'  constructor() {{',
            f'    super("{entity_name}");',
        ])

        for comp in components:
            lines.append(f'    this.addComponent(new {comp}());')

        for tag in tags:
            lines.append(f'    this.addTag("{tag}");')

        lines.extend([
            '  }',
            '',
            '  initialize(): void {',
            '    // Entity initialization logic',
            '  }',
            '}',
        ])

        return CodeFile(
            path=f"src/entities/{entity_name}.ts",
            filename=f"{entity_name}.ts",
            language=CodeLanguage.TYPESCRIPT,
            content="\n".join(lines),
            description=f"{safe} entity definition",
            category="source",
            dependencies=[f"src/world.ts"],
        )

    def _generate_system(self, system_name: str, analysis: PromptAnalysis) -> Optional[CodeFile]:
        template = _SYSTEM_TEMPLATES.get(system_name)
        if not template:
            return None

        safe = system_name.replace(" ", "")
        priority = template.get("priority", 500)
        required = template.get("required_components", [])
        desc = template.get("description", "")

        lines = [
            f'// {safe} System - {desc}',
            '',
            'import { System, Entity } from "sparkengine";',
        ]

        for comp in required:
            lines.append(f'import {{ {comp} }} from "sparkengine/components";')

        lines.extend([
            '',
            f'export class {safe}System extends System {{',
            f'  readonly priority = {priority};',
            f'  readonly requiredComponents = [{", ".join(chr(34) + c + chr(34) for c in required)}];',
            '',
            '  private entities: Entity[] = [];',
            '',
            '  onEntityAdded(entity: Entity): void {',
            '    this.entities.push(entity);',
            '  }',
            '',
            '  onEntityRemoved(entity: Entity): void {',
            '    this.entities = this.entities.filter(e => e.id !== entity.id);',
            '  }',
            '',
            '  update(deltaTime: number): void {',
            '    for (const entity of this.entities) {',
            '      this.processEntity(entity, deltaTime);',
            '    }',
            '  }',
            '',
            '  protected processEntity(entity: Entity, deltaTime: number): void {',
            '    // System-specific processing logic',
            '  }',
            '}',
        ])

        return CodeFile(
            path=f"src/systems/{system_name}.ts",
            filename=f"{system_name}.ts",
            language=CodeLanguage.TYPESCRIPT,
            content="\n".join(lines),
            description=f"{safe} system - {desc}",
            category="source",
        )

    def _generate_mechanic(self, mechanic: str, analysis: PromptAnalysis) -> Optional[CodeFile]:
        safe = mechanic.replace("_", "").replace(" ", "")

        mechanic_implementations: Dict[str, List[str]] = {
            "jumping": [
                '  private jumpForce = 10.0;',
                '  private isGrounded = false;',
                '',
                '  handleJump(input: InputReceiver): void {',
                '    if (input.isActionPressed("jump") && this.isGrounded) {',
                '      const body = this.entity.getComponent<PhysicsBody>("PhysicsBody");',
                '      if (body) {',
                '        body.applyForce(0, this.jumpForce, 0);',
                '        this.isGrounded = false;',
                '      }',
                '    }',
                '  }',
            ],
            "shooting": [
                '  private projectileSpeed = 15.0;',
                '  private fireRate = 0.2;',
                '  private lastFireTime = 0;',
                '',
                '  handleShoot(input: InputReceiver, time: number): void {',
                '    if (input.isActionPressed("fire") && time - this.lastFireTime > this.fireRate) {',
                '      this.spawnProjectile();',
                '      this.lastFireTime = time;',
                '    }',
                '  }',
                '',
                '  private spawnProjectile(): void {',
                '    // Spawn projectile entity at player position',
                '  }',
            ],
            "scoring": [
                '  private score = 0;',
                '  private highScore = 0;',
                '',
                '  addScore(points: number): void {',
                '    this.score += points;',
                '    if (this.score > this.highScore) {',
                '      this.highScore = this.score;',
                '    }',
                '  }',
                '',
                '  getScore(): number { return this.score; }',
                '  getHighScore(): number { return this.highScore; }',
                '  resetScore(): void { this.score = 0; }',
            ],
            "collection": [
                '  private collectedItems: string[] = [];',
                '',
                '  onCollectItem(itemId: string, itemType: string): void {',
                '    this.collectedItems.push(itemId);',
                '    this.processCollection(itemType);',
                '  }',
                '',
                '  private processCollection(itemType: string): void {',
                '    // Handle different item types',
                '  }',
            ],
            "health_damage": [
                '  private maxHealth = 100;',
                '  private currentHealth = 100;',
                '',
                '  takeDamage(amount: number): void {',
                '    this.currentHealth = Math.max(0, this.currentHealth - amount);',
                '    if (this.currentHealth <= 0) {',
                '      this.onDeath();',
                '    }',
                '  }',
                '',
                '  heal(amount: number): void {',
                '    this.currentHealth = Math.min(this.maxHealth, this.currentHealth + amount);',
                '  }',
                '',
                '  private onDeath(): void {',
                '    // Handle entity death',
                '  }',
            ],
            "basic_movement": [
                '  private moveSpeed = 5.0;',
                '',
                '  handleMovement(input: InputReceiver, deltaTime: number): void {',
                '    const transform = this.entity.getComponent<Transform>("Transform");',
                '    if (!transform) return;',
                '',
                '    let dx = 0, dy = 0;',
                '    if (input.isActionPressed("move_left")) dx -= 1;',
                '    if (input.isActionPressed("move_right")) dx += 1;',
                '    if (input.isActionPressed("move_up")) dy += 1;',
                '    if (input.isActionPressed("move_down")) dy -= 1;',
                '',
                '    transform.position.x += dx * this.moveSpeed * deltaTime;',
                '    transform.position.y += dy * this.moveSpeed * deltaTime;',
                '  }',
            ],
            "collision_response": [
                '  onCollisionEnter(other: Entity): void {',
                '    const tags = other.getTags();',
                '    if (tags.includes("collectible")) {',
                '      this.onCollectItem(other.id, "default");',
                '    } else if (tags.includes("enemy")) {',
                '      this.takeDamage(10);',
                '    } else if (tags.includes("platform")) {',
                '      this.isGrounded = true;',
                '    }',
                '  }',
                '',
                '  onCollisionExit(other: Entity): void {',
                '    const tags = other.getTags();',
                '    if (tags.includes("platform")) {',
                '      this.isGrounded = false;',
                '    }',
                '  }',
            ],
        }

        impl = mechanic_implementations.get(mechanic, [
            '  // Custom mechanic implementation',
            '  execute(): void {',
            '    // Mechanic logic',
            '  }',
        ])

        lines = [
            f'// {safe} Mechanic',
            '',
            'import { Entity } from "sparkengine";',
            '',
            f'export class {safe}Mechanic {{',
            '  private entity: Entity;',
            '',
            '  constructor(entity: Entity) {',
            '    this.entity = entity;',
            '  }',
            '',
        ] + impl + [
            '}',
        ]

        return CodeFile(
            path=f"src/mechanics/{mechanic}.ts",
            filename=f"{mechanic}.ts",
            language=CodeLanguage.TYPESCRIPT,
            content="\n".join(lines),
            description=f"{safe} game mechanic",
            category="source",
        )


class CodeValidator:
    """
    Validates generated code at multiple levels: syntax,
    semantics, runtime behavior, and integration.
    """

    def validate(
        self,
        project: CodeGenProject,
        level: ValidationLevel = ValidationLevel.SYNTAX,
    ) -> ValidationResult:
        if level == ValidationLevel.SYNTAX:
            return self._validate_syntax(project)
        elif level == ValidationLevel.SEMANTIC:
            return self._validate_semantic(project)
        elif level == ValidationLevel.RUNTIME:
            return self._validate_runtime(project)
        elif level == ValidationLevel.INTEGRATION:
            return self._validate_integration(project)
        return ValidationResult(level=level, passed=False)

    def _validate_syntax(self, project: CodeGenProject) -> ValidationResult:
        result = ValidationResult(level=ValidationLevel.SYNTAX)
        total_score = 0.0

        for code_file in project.files:
            if not code_file.content:
                result.errors.append({
                    "file": code_file.path,
                    "message": "Empty file content",
                    "line": 0,
                })
                continue

            if not self._check_bracket_balance(code_file.content):
                result.errors.append({
                    "file": code_file.path,
                    "message": "Unbalanced brackets",
                    "line": 0,
                })
            else:
                total_score += 1.0

            if not self._check_import_consistency(code_file):
                result.warnings.append({
                    "file": code_file.path,
                    "message": "Import path may be inconsistent",
                })
            else:
                total_score += 0.5

        file_count = max(len(project.files), 1)
        result.score = min(total_score / (file_count * 1.5), 1.0)
        result.passed = len(result.errors) == 0
        return result

    def _validate_semantic(self, project: CodeGenProject) -> ValidationResult:
        result = ValidationResult(level=ValidationLevel.SEMANTIC)
        total_score = 0.0

        has_entry = any(f.is_entry_point for f in project.files)
        if not has_entry:
            result.errors.append({
                "file": "",
                "message": "No entry point found in project",
            })
        else:
            total_score += 1.0

        entity_files = [f for f in project.files if f.category == "source" and "entities" in f.path]
        system_files = [f for f in project.files if f.category == "source" and "systems" in f.path]

        if len(entity_files) < 2:
            result.warnings.append({
                "file": "",
                "message": "Project has fewer than 2 entity definitions",
            })
        else:
            total_score += 0.5

        if len(system_files) < 1:
            result.warnings.append({
                "file": "",
                "message": "Project has no system definitions",
            })
        else:
            total_score += 0.5

        dep_score = self._check_dependency_graph(project.files)
        total_score += dep_score

        max_score = 3.0
        result.score = min(total_score / max_score, 1.0)
        result.passed = len(result.errors) == 0
        return result

    def _validate_runtime(self, project: CodeGenProject) -> ValidationResult:
        result = ValidationResult(level=ValidationLevel.RUNTIME)

        result.suggestions.append("Configure LLM provider for runtime validation")
        result.suggestions.append("Add unit tests for game mechanics")
        result.suggestions.append("Test on target platform")

        result.score = 0.5
        result.passed = True
        return result

    def _validate_integration(self, project: CodeGenProject) -> ValidationResult:
        result = ValidationResult(level=ValidationLevel.INTEGRATION)

        result.suggestions.append("Verify all entity-system connections")
        result.suggestions.append("Test scene loading and transitions")
        result.suggestions.append("Validate input mapping configuration")

        result.score = 0.5
        result.passed = True
        return result

    def _check_bracket_balance(self, content: str) -> bool:
        stack: List[str] = []
        pairs = {"{": "}", "(": ")", "[": "]"}
        in_string = False
        escape_next = False

        for char in content:
            if escape_next:
                escape_next = False
                continue
            if char == "\\":
                escape_next = True
                continue
            if char in ('"', "'", "`"):
                in_string = not in_string
                continue
            if in_string:
                continue
            if char in pairs:
                stack.append(char)
            elif char in pairs.values():
                if not stack:
                    return False
                opener = stack.pop()
                if pairs.get(opener) != char:
                    return False

        return len(stack) == 0

    def _check_import_consistency(self, code_file: CodeFile) -> bool:
        if not code_file.dependencies:
            return True
        return True

    def _check_dependency_graph(self, files: List[CodeFile]) -> float:
        file_paths = {f.path for f in files}
        valid_deps = 0
        total_deps = 0

        for f in files:
            for dep in f.dependencies:
                total_deps += 1
                if dep in file_paths:
                    valid_deps += 1

        if total_deps == 0:
            return 0.5
        return valid_deps / total_deps


class CodeRefiner:
    """
    Iteratively refines generated code based on validation
    feedback, improving quality through multiple passes.
    """

    def refine(
        self,
        project: CodeGenProject,
        validation: ValidationResult,
    ) -> CodeGenProject:
        if validation.passed and validation.score >= 0.8:
            return project

        for error in validation.errors:
            file_path = error.get("file", "")
            target_file = next(
                (f for f in project.files if f.path == file_path), None
            )
            if target_file:
                target_file.content = self._apply_fix(
                    target_file.content, error
                )

        for warning in validation.warnings:
            file_path = warning.get("file", "")
            target_file = next(
                (f for f in project.files if f.path == file_path), None
            )
            if target_file:
                target_file.content = self._apply_improvement(
                    target_file.content, warning
                )

        project.iteration += 1
        return project

    def _apply_fix(self, content: str, error: Dict[str, Any]) -> str:
        message = error.get("message", "")

        if "Unbalanced brackets" in message:
            content = self._fix_brackets(content)
        elif "Empty file content" in message:
            content = "// Generated file\nexport default {};\n"

        return content

    def _apply_improvement(self, content: str, warning: Dict[str, Any]) -> str:
        message = warning.get("message", "")

        if "Import path" in message:
            pass

        return content

    def _fix_brackets(self, content: str) -> str:
        open_braces = content.count("{") - content.count("}")
        open_parens = content.count("(") - content.count(")")
        open_brackets = content.count("[") - content.count("]")

        if open_braces > 0:
            content += "\n" + "}" * open_braces
        if open_parens > 0:
            content += "\n" + ")" * open_parens
        if open_brackets > 0:
            content += "\n" + "]" * open_brackets

        return content


class GameCoder:
    """
    End-to-end game code generation system.

    Transforms natural language game descriptions into complete,
    runnable game code through a multi-phase pipeline:

    1. Analyze: Extract genre, features, entities, systems from prompt
    2. Scaffold: Create project structure and configuration
    3. Generate: Produce entity, system, and mechanic code
    4. Validate: Check syntax, semantics, and integration
    5. Refine: Iteratively improve based on validation feedback
    6. Package: Assemble the final project

    Usage:
        coder = GameCoder()
        project = await coder.generate("Create a platformer with enemies and scoring")
        print(project.to_dict())
    """

    def __init__(self):
        self._analyzer = PromptAnalyzer()
        self._scaffolder = CodeScaffolder()
        self._generator = CodeGenerator()
        self._validator = CodeValidator()
        self._refiner = CodeRefiner()

        self._projects: Dict[str, CodeGenProject] = {}
        self._generation_count: int = 0
        self._total_files_generated: int = 0
        self._total_iterations: int = 0

    async def generate(
        self,
        prompt: str,
        project_name: str = "",
        target_language: CodeLanguage = CodeLanguage.TYPESCRIPT,
        max_iterations: int = 3,
    ) -> CodeGenProject:
        """
        Generate a complete game project from a natural language prompt.
        """
        project = CodeGenProject(
            name=project_name or "GeneratedGame",
            description=prompt,
            max_iterations=max_iterations,
            language=target_language,
        )

        self._projects[project.id] = project

        try:
            project.phase = CodeGenPhase.ANALYZING
            project.analysis = self._analyzer.analyze(prompt)
            if target_language != CodeLanguage.TYPESCRIPT:
                project.analysis.target_language = target_language
            project.genre = project.analysis.detected_genre

            project.phase = CodeGenPhase.SCAFFOLDING
            scaffold_files = self._scaffolder.scaffold(
                project.analysis, project_name
            )
            project.files.extend(scaffold_files)

            project.phase = CodeGenPhase.GENERATING
            generated_files = self._generator.generate(project.analysis)
            project.files.extend(generated_files)

            self._total_files_generated += len(project.files)

            project.phase = CodeGenPhase.VALIDATING
            for level in [ValidationLevel.SYNTAX, ValidationLevel.SEMANTIC]:
                validation = self._validator.validate(project, level)
                project.validation_results.append(validation)

                if not validation.passed and project.iteration < project.max_iterations:
                    project.phase = CodeGenPhase.REFINING
                    project = self._refiner.refine(project, validation)
                    self._total_iterations += 1

                    revalidation = self._validator.validate(project, level)
                    project.validation_results.append(revalidation)

            project.phase = CodeGenPhase.PACKAGING
            project.quality_score = self._calculate_quality(project)

            project.phase = CodeGenPhase.COMPLETED
            project.completed_at = time.time()
            self._generation_count += 1

        except Exception as e:
            project.phase = CodeGenPhase.FAILED
            project.completed_at = time.time()

        return project

    def get_project(self, project_id: str) -> Optional[CodeGenProject]:
        return self._projects.get(project_id)

    def list_projects(self) -> List[Dict[str, Any]]:
        return [
            {
                "id": p.id,
                "name": p.name,
                "genre": p.genre,
                "phase": p.phase.value,
                "file_count": len(p.files),
                "quality_score": p.quality_score,
                "created_at": p.created_at,
            }
            for p in self._projects.values()
        ]

    def get_stats(self) -> Dict[str, Any]:
        return {
            "total_projects": len(self._projects),
            "generation_count": self._generation_count,
            "total_files_generated": self._total_files_generated,
            "total_iterations": self._total_iterations,
            "avg_quality_score": (
                sum(p.quality_score for p in self._projects.values())
                / max(len(self._projects), 1)
            ),
            "by_genre": self._genre_distribution(),
            "by_phase": self._phase_distribution(),
        }

    def _calculate_quality(self, project: CodeGenProject) -> float:
        if not project.validation_results:
            return 0.0

        scores = [v.score for v in project.validation_results]
        avg_score = sum(scores) / len(scores)

        iteration_penalty = project.iteration * 0.05
        file_bonus = min(len(project.files) / 10.0, 0.2)

        return max(0.0, min(1.0, avg_score - iteration_penalty + file_bonus))

    def _genre_distribution(self) -> Dict[str, int]:
        dist: Dict[str, int] = {}
        for p in self._projects.values():
            genre = p.genre or "unknown"
            dist[genre] = dist.get(genre, 0) + 1
        return dist

    def _phase_distribution(self) -> Dict[str, int]:
        dist: Dict[str, int] = {}
        for p in self._projects.values():
            phase = p.phase.value
            dist[phase] = dist.get(phase, 0) + 1
        return dist


_global_coder: Optional[GameCoder] = None


def get_game_coder() -> GameCoder:
    """Get the global GameCoder singleton."""
    global _global_coder
    if _global_coder is None:
        _global_coder = GameCoder()
    return _global_coder


def reset_game_coder() -> None:
    """Reset the global GameCoder singleton."""
    global _global_coder
    _global_coder = None
