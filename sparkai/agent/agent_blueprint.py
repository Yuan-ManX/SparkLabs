"""
SparkAI Agent - Game Design Blueprint

Spec-driven game design system that captures game concepts as
structured blueprints. Each blueprint defines the game's core loop,
mechanics, progression, and aesthetic direction as a living document
that evolves through the development lifecycle.

Architecture:
  BlueprintEngine
    |-- GameBlueprint (top-level game design spec)
    |-- CoreLoop (primary gameplay cycle definition)
    |-- MechanicSpec (individual game mechanic specification)
    |-- ProgressionModel (player advancement structure)
    |-- AestheticDirection (visual and audio style guide)
    |-- BlueprintRevision (version history and change tracking)
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class BlueprintState(Enum):
    DRAFT = "draft"
    REVIEW = "review"
    APPROVED = "approved"
    IMPLEMENTING = "implementing"
    ITERATING = "iterating"
    FINALIZED = "finalized"


class LoopPhase(Enum):
    SETUP = "setup"
    ACTION = "action"
    FEEDBACK = "feedback"
    REWARD = "reward"
    RESET = "reset"


class MechanicType(Enum):
    MOVEMENT = "movement"
    COMBAT = "combat"
    PUZZLE = "puzzle"
    ECONOMY = "economy"
    SOCIAL = "social"
    EXPLORATION = "exploration"
    CRAFTING = "crafting"
    PROGRESSION = "progression"
    CUSTOM = "custom"


class ProgressionType(Enum):
    LINEAR = "linear"
    BRANCHING = "branching"
    OPEN_WORLD = "open_world"
    ROGUELIKE = "roguelike"
    LEVEL_BASED = "level_based"
    SKILL_TREE = "skill_tree"


class AestheticPillar(Enum):
    REALISTIC = "realistic"
    STYLIZED = "stylized"
    PIXEL_ART = "pixel_art"
    LOW_POLY = "low_poly"
    HAND_DRAWN = "hand_drawn"
    VOXEL = "voxel"
    MINIMALIST = "minimalist"
    DARK_FANTASY = "dark_fantasy"
    RETRO = "retro"
    NEON = "neon"


@dataclass
class LoopPhaseDef:
    name: str = ""
    phase: LoopPhase = LoopPhase.ACTION
    description: str = ""
    player_action: str = ""
    system_response: str = ""
    duration_estimate: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "phase": self.phase.value,
            "description": self.description,
            "player_action": self.player_action,
            "system_response": self.system_response,
            "duration_estimate": self.duration_estimate,
        }


@dataclass
class CoreLoop:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    description: str = ""
    phases: List[LoopPhaseDef] = field(default_factory=list)
    loop_frequency: str = "continuous"
    engagement_hooks: List[str] = field(default_factory=list)
    exit_conditions: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "phases": [p.to_dict() for p in self.phases],
            "loop_frequency": self.loop_frequency,
            "engagement_hooks": self.engagement_hooks,
            "exit_conditions": self.exit_conditions,
        }


@dataclass
class MechanicSpec:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    mechanic_type: MechanicType = MechanicType.CUSTOM
    description: str = ""
    player_input: str = ""
    system_output: str = ""
    parameters: Dict[str, Any] = field(default_factory=dict)
    dependencies: List[str] = field(default_factory=list)
    conflicts: List[str] = field(default_factory=list)
    priority: int = 2
    complexity: str = "medium"
    implementation_notes: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "mechanic_type": self.mechanic_type.value,
            "description": self.description,
            "player_input": self.player_input,
            "system_output": self.system_output,
            "parameters": self.parameters,
            "dependencies": self.dependencies,
            "conflicts": self.conflicts,
            "priority": self.priority,
            "complexity": self.complexity,
            "implementation_notes": self.implementation_notes,
        }


@dataclass
class ProgressionModel:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    progression_type: ProgressionType = ProgressionType.LINEAR
    description: str = ""
    milestones: List[Dict[str, Any]] = field(default_factory=list)
    reward_schedule: List[Dict[str, Any]] = field(default_factory=list)
    difficulty_curve: str = "gradual"
    unlock_structure: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "progression_type": self.progression_type.value,
            "description": self.description,
            "milestones": self.milestones,
            "reward_schedule": self.reward_schedule,
            "difficulty_curve": self.difficulty_curve,
            "unlock_structure": self.unlock_structure,
        }


@dataclass
class AestheticDirection:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    pillars: List[AestheticPillar] = field(default_factory=list)
    color_palette: List[str] = field(default_factory=list)
    mood_keywords: List[str] = field(default_factory=list)
    visual_references: List[str] = field(default_factory=list)
    audio_style: str = ""
    ui_style: str = ""
    typography: str = ""
    animation_style: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "pillars": [p.value for p in self.pillars],
            "color_palette": self.color_palette,
            "mood_keywords": self.mood_keywords,
            "visual_references": self.visual_references,
            "audio_style": self.audio_style,
            "ui_style": self.ui_style,
            "typography": self.typography,
            "animation_style": self.animation_style,
        }


@dataclass
class BlueprintRevision:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    version: int = 1
    author: str = ""
    description: str = ""
    changes: List[str] = field(default_factory=list)
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "version": self.version,
            "author": self.author,
            "description": self.description,
            "changes": self.changes,
            "timestamp": self.timestamp,
        }


@dataclass
class GameBlueprint:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    genre: str = ""
    state: BlueprintState = BlueprintState.DRAFT
    tagline: str = ""
    description: str = ""
    target_audience: str = ""
    platform: str = "web"
    core_loop: Optional[CoreLoop] = None
    mechanics: List[MechanicSpec] = field(default_factory=list)
    progression: Optional[ProgressionModel] = None
    aesthetic: Optional[AestheticDirection] = None
    revisions: List[BlueprintRevision] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "genre": self.genre,
            "state": self.state.value,
            "tagline": self.tagline,
            "description": self.description,
            "target_audience": self.target_audience,
            "platform": self.platform,
            "core_loop": self.core_loop.to_dict() if self.core_loop else None,
            "mechanics": [m.to_dict() for m in self.mechanics],
            "progression": self.progression.to_dict() if self.progression else None,
            "aesthetic": self.aesthetic.to_dict() if self.aesthetic else None,
            "revisions": [r.to_dict() for r in self.revisions],
            "tags": self.tags,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


class BlueprintEngine:
    """
    Spec-driven game design system.

    Captures game concepts as structured blueprints with core loops,
    mechanics, progression models, and aesthetic directions. Supports
    version tracking and collaborative iteration.
    """

    def __init__(self):
        self._blueprints: Dict[str, GameBlueprint] = {}
        self._blueprint_count: int = 0
        self._revision_count: int = 0

    def create_blueprint(
        self,
        name: str,
        genre: str = "",
        tagline: str = "",
        description: str = "",
        target_audience: str = "",
        platform: str = "web",
        tags: Optional[List[str]] = None,
    ) -> GameBlueprint:
        bp = GameBlueprint(
            name=name,
            genre=genre,
            tagline=tagline,
            description=description,
            target_audience=target_audience,
            platform=platform,
            tags=tags or [],
        )
        bp.revisions.append(BlueprintRevision(
            version=1,
            author="system",
            description="Initial blueprint creation",
            changes=["Created blueprint"],
        ))
        self._blueprints[bp.id] = bp
        self._blueprint_count += 1
        self._revision_count += 1
        return bp

    def get_blueprint(self, blueprint_id: str) -> Optional[Dict[str, Any]]:
        bp = self._blueprints.get(blueprint_id)
        return bp.to_dict() if bp else None

    def list_blueprints(self, state: Optional[BlueprintState] = None) -> List[Dict[str, Any]]:
        bps = list(self._blueprints.values())
        if state:
            bps = [b for b in bps if b.state == state]
        return [b.to_dict() for b in bps]

    def update_blueprint(self, blueprint_id: str, updates: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        bp = self._blueprints.get(blueprint_id)
        if not bp:
            return None

        changes = []
        for key, value in updates.items():
            if key in ("name", "genre", "tagline", "description", "target_audience", "platform", "state", "tags"):
                old_value = getattr(bp, key, None)
                if old_value != value:
                    setattr(bp, key, value)
                    changes.append(f"Updated {key}")

        if changes:
            bp.updated_at = time.time()
            bp.revisions.append(BlueprintRevision(
                version=len(bp.revisions) + 1,
                author="system",
                description="Blueprint update",
                changes=changes,
            ))
            self._revision_count += 1

        return bp.to_dict()

    def set_core_loop(
        self,
        blueprint_id: str,
        name: str,
        description: str = "",
        phases: Optional[List[Dict[str, Any]]] = None,
        loop_frequency: str = "continuous",
        engagement_hooks: Optional[List[str]] = None,
        exit_conditions: Optional[List[str]] = None,
    ) -> Optional[Dict[str, Any]]:
        bp = self._blueprints.get(blueprint_id)
        if not bp:
            return None

        phase_defs = []
        for p in (phases or []):
            phase_defs.append(LoopPhaseDef(
                name=p.get("name", ""),
                phase=LoopPhase(p.get("phase", "action")),
                description=p.get("description", ""),
                player_action=p.get("player_action", ""),
                system_response=p.get("system_response", ""),
                duration_estimate=p.get("duration_estimate", 0.0),
            ))

        bp.core_loop = CoreLoop(
            name=name,
            description=description,
            phases=phase_defs,
            loop_frequency=loop_frequency,
            engagement_hooks=engagement_hooks or [],
            exit_conditions=exit_conditions or [],
        )
        bp.updated_at = time.time()
        bp.revisions.append(BlueprintRevision(
            version=len(bp.revisions) + 1,
            author="system",
            description=f"Set core loop: {name}",
            changes=[f"Added core loop with {len(phase_defs)} phases"],
        ))
        self._revision_count += 1
        return bp.to_dict()

    def add_mechanic(
        self,
        blueprint_id: str,
        name: str,
        mechanic_type: str = "custom",
        description: str = "",
        player_input: str = "",
        system_output: str = "",
        parameters: Optional[Dict[str, Any]] = None,
        dependencies: Optional[List[str]] = None,
        priority: int = 2,
        complexity: str = "medium",
    ) -> Optional[Dict[str, Any]]:
        bp = self._blueprints.get(blueprint_id)
        if not bp:
            return None

        mechanic = MechanicSpec(
            name=name,
            mechanic_type=MechanicType(mechanic_type),
            description=description,
            player_input=player_input,
            system_output=system_output,
            parameters=parameters or {},
            dependencies=dependencies or [],
            priority=priority,
            complexity=complexity,
        )
        bp.mechanics.append(mechanic)
        bp.updated_at = time.time()
        bp.revisions.append(BlueprintRevision(
            version=len(bp.revisions) + 1,
            author="system",
            description=f"Added mechanic: {name}",
            changes=[f"Added {mechanic_type} mechanic: {name}"],
        ))
        self._revision_count += 1
        return bp.to_dict()

    def remove_mechanic(self, blueprint_id: str, mechanic_id: str) -> Optional[Dict[str, Any]]:
        bp = self._blueprints.get(blueprint_id)
        if not bp:
            return None
        bp.mechanics = [m for m in bp.mechanics if m.id != mechanic_id]
        bp.updated_at = time.time()
        return bp.to_dict()

    def set_progression(
        self,
        blueprint_id: str,
        name: str,
        progression_type: str = "linear",
        description: str = "",
        milestones: Optional[List[Dict[str, Any]]] = None,
        difficulty_curve: str = "gradual",
    ) -> Optional[Dict[str, Any]]:
        bp = self._blueprints.get(blueprint_id)
        if not bp:
            return None

        bp.progression = ProgressionModel(
            name=name,
            progression_type=ProgressionType(progression_type),
            description=description,
            milestones=milestones or [],
            difficulty_curve=difficulty_curve,
        )
        bp.updated_at = time.time()
        bp.revisions.append(BlueprintRevision(
            version=len(bp.revisions) + 1,
            author="system",
            description=f"Set progression: {name}",
            changes=[f"Added {progression_type} progression model"],
        ))
        self._revision_count += 1
        return bp.to_dict()

    def set_aesthetic(
        self,
        blueprint_id: str,
        name: str,
        pillars: Optional[List[str]] = None,
        color_palette: Optional[List[str]] = None,
        mood_keywords: Optional[List[str]] = None,
        audio_style: str = "",
        ui_style: str = "",
    ) -> Optional[Dict[str, Any]]:
        bp = self._blueprints.get(blueprint_id)
        if not bp:
            return None

        bp.aesthetic = AestheticDirection(
            name=name,
            pillars=[AestheticPillar(p) for p in (pillars or [])],
            color_palette=color_palette or [],
            mood_keywords=mood_keywords or [],
            audio_style=audio_style,
            ui_style=ui_style,
        )
        bp.updated_at = time.time()
        bp.revisions.append(BlueprintRevision(
            version=len(bp.revisions) + 1,
            author="system",
            description=f"Set aesthetic: {name}",
            changes=[f"Added aesthetic direction with {len(pillars or [])} pillars"],
        ))
        self._revision_count += 1
        return bp.to_dict()

    def get_revisions(self, blueprint_id: str) -> List[Dict[str, Any]]:
        bp = self._blueprints.get(blueprint_id)
        if not bp:
            return []
        return [r.to_dict() for r in bp.revisions]

    def transition_state(self, blueprint_id: str, new_state: str) -> Optional[Dict[str, Any]]:
        bp = self._blueprints.get(blueprint_id)
        if not bp:
            return None
        old_state = bp.state.value
        bp.state = BlueprintState(new_state)
        bp.updated_at = time.time()
        bp.revisions.append(BlueprintRevision(
            version=len(bp.revisions) + 1,
            author="system",
            description=f"State transition: {old_state} -> {new_state}",
            changes=[f"Changed state from {old_state} to {new_state}"],
        ))
        self._revision_count += 1
        return bp.to_dict()

    def get_stats(self) -> Dict[str, Any]:
        return {
            "total_blueprints": len(self._blueprints),
            "total_revisions": self._revision_count,
            "by_state": {s.value: sum(1 for b in self._blueprints.values() if b.state == s) for s in BlueprintState},
            "by_genre": {genre: sum(1 for b in self._blueprints.values() if b.genre == genre) for genre in set(b.genre for b in self._blueprints.values() if b.genre)},
            "avg_mechanics": sum(len(b.mechanics) for b in self._blueprints.values()) / len(self._blueprints) if self._blueprints else 0.0,
        }


_blueprint_engine: Optional[BlueprintEngine] = None


def get_blueprint_engine() -> BlueprintEngine:
    global _blueprint_engine
    if _blueprint_engine is None:
        _blueprint_engine = BlueprintEngine()
    return _blueprint_engine
