"""
SparkLabs Agent - Tutorial Orchestrator

A singleton system that observes developer behavior patterns and
generates adaptive interactive tutorials. Tracks feature usage,
identifies knowledge gaps, and creates personalized learning paths
for the AI-native game engine.

Architecture:
  TutorialOrchestrator (singleton)
    |-- LearnerProfile (per-developer skill model and progress)
    |-- TutorialSession (active interactive learning experience)
    |-- TutorialStep (individual instructional unit)
    |-- Behavior Tracker (observes tool/feature usage patterns)
    |-- Gap Detector (identifies missing knowledge from behavior)
    |-- Tutorial Generator (produces adaptive tutorial content)
    |-- Skill Assessor (estimates current competence level)
"""

from __future__ import annotations

import random
import threading
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


_time_module = time


# ------------------------------------------------------------------
# Enumerations
# ------------------------------------------------------------------


class TutorialType(Enum):
    WALKTHROUGH = "walkthrough"
    TOOLTIP = "tooltip"
    EXERCISE = "exercise"
    VIDEO_SCRIPT = "video_script"
    INTERACTIVE_GUIDE = "interactive_guide"
    QUICK_REFERENCE = "quick_reference"


class SkillLevel(Enum):
    ABSOLUTE_BEGINNER = "absolute_beginner"
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"
    EXPERT = "expert"


class LearningObjective(Enum):
    ENGINE_BASICS = "engine_basics"
    SCENE_CREATION = "scene_creation"
    SCRIPTING = "scripting"
    ASSETS = "assets"
    PHYSICS = "physics"
    UI_DESIGN = "ui_design"
    MULTIPLAYER = "multiplayer"
    OPTIMIZATION = "optimization"
    PUBLISHING = "publishing"


class TutorialTrigger(Enum):
    FIRST_USE = "first_use"
    REPEATED_STRUGGLE = "repeated_struggle"
    FEATURE_DISCOVERY = "feature_discovery"
    ACHIEVEMENT_UNLOCK = "achievement_unlock"
    USER_REQUEST = "user_request"


# ------------------------------------------------------------------
# Learning dependency graph (which objectives require others first)
# ------------------------------------------------------------------

_LEARNING_PREREQUISITES: Dict[LearningObjective, List[LearningObjective]] = {
    LearningObjective.ENGINE_BASICS: [],
    LearningObjective.SCENE_CREATION: [LearningObjective.ENGINE_BASICS],
    LearningObjective.SCRIPTING: [LearningObjective.ENGINE_BASICS],
    LearningObjective.ASSETS: [LearningObjective.ENGINE_BASICS],
    LearningObjective.PHYSICS: [LearningObjective.SCENE_CREATION],
    LearningObjective.UI_DESIGN: [LearningObjective.SCENE_CREATION],
    LearningObjective.MULTIPLAYER: [LearningObjective.SCRIPTING, LearningObjective.SCENE_CREATION],
    LearningObjective.OPTIMIZATION: [LearningObjective.SCRIPTING, LearningObjective.ASSETS],
    LearningObjective.PUBLISHING: [
        LearningObjective.SCENE_CREATION,
        LearningObjective.SCRIPTING,
        LearningObjective.ASSETS,
    ],
}


# ------------------------------------------------------------------
# Feature-to-objective mapping for behavior tracking
# ------------------------------------------------------------------

_FEATURE_OBJECTIVE_MAP: Dict[str, LearningObjective] = {
    "project_creation": LearningObjective.ENGINE_BASICS,
    "navigation": LearningObjective.ENGINE_BASICS,
    "viewport_controls": LearningObjective.ENGINE_BASICS,
    "scene_setup": LearningObjective.SCENE_CREATION,
    "game_object_placement": LearningObjective.SCENE_CREATION,
    "hierarchy_organization": LearningObjective.SCENE_CREATION,
    "script_editor": LearningObjective.SCRIPTING,
    "code_generation": LearningObjective.SCRIPTING,
    "debugging": LearningObjective.SCRIPTING,
    "sprite_import": LearningObjective.ASSETS,
    "audio_import": LearningObjective.ASSETS,
    "model_import": LearningObjective.ASSETS,
    "texture_editor": LearningObjective.ASSETS,
    "rigidbody_setup": LearningObjective.PHYSICS,
    "collision_detection": LearningObjective.PHYSICS,
    "force_application": LearningObjective.PHYSICS,
    "canvas_editor": LearningObjective.UI_DESIGN,
    "ui_component_design": LearningObjective.UI_DESIGN,
    "event_wiring": LearningObjective.UI_DESIGN,
    "network_setup": LearningObjective.MULTIPLAYER,
    "rpc_calls": LearningObjective.MULTIPLAYER,
    "lobby_system": LearningObjective.MULTIPLAYER,
    "profiling": LearningObjective.OPTIMIZATION,
    "batching": LearningObjective.OPTIMIZATION,
    "memory_analysis": LearningObjective.OPTIMIZATION,
    "build_export": LearningObjective.PUBLISHING,
    "platform_config": LearningObjective.PUBLISHING,
    "asset_bundling": LearningObjective.PUBLISHING,
}


# ------------------------------------------------------------------
# Dataclasses
# ------------------------------------------------------------------


@dataclass
class TutorialStep:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    title: str = ""
    description: str = ""
    action_required: str = ""
    expected_result: str = ""
    hints: List[str] = field(default_factory=list)
    completion_criteria: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "action_required": self.action_required,
            "expected_result": self.expected_result,
            "hints": list(self.hints),
            "completion_criteria": dict(self.completion_criteria),
        }


@dataclass
class TutorialSession:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    objective: LearningObjective = LearningObjective.ENGINE_BASICS
    steps: List[TutorialStep] = field(default_factory=list)
    current_step_index: int = 0
    started_at: float = field(default_factory=_time_module.time)
    completed_steps: List[str] = field(default_factory=list)
    skill_level: SkillLevel = SkillLevel.ABSOLUTE_BEGINNER

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "objective": self.objective.value,
            "steps": [s.to_dict() for s in self.steps],
            "current_step_index": self.current_step_index,
            "started_at": self.started_at,
            "completed_steps": list(self.completed_steps),
            "skill_level": self.skill_level.value,
        }

    @property
    def total_steps(self) -> int:
        return len(self.steps)

    @property
    def progress_fraction(self) -> float:
        if not self.steps:
            return 0.0
        return len(self.completed_steps) / len(self.steps)

    @property
    def is_complete(self) -> bool:
        return self.current_step_index >= len(self.steps) and len(self.steps) > 0


@dataclass
class LearnerProfile:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    observed_behaviors: Dict[str, int] = field(default_factory=dict)
    mastered_topics: List[str] = field(default_factory=list)
    struggle_areas: List[str] = field(default_factory=list)
    recommended_next: List[str] = field(default_factory=list)
    last_updated: float = field(default_factory=_time_module.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "observed_behaviors": dict(self.observed_behaviors),
            "mastered_topics": list(self.mastered_topics),
            "struggle_areas": list(self.struggle_areas),
            "recommended_next": list(self.recommended_next),
            "last_updated": self.last_updated,
        }


# ------------------------------------------------------------------
# TutorialOrchestrator (Singleton)
# ------------------------------------------------------------------


class TutorialOrchestrator:
    """
    Singleton orchestrator for adaptive interactive tutorial generation.

    Observes developer behavior, builds learner profiles, detects
    knowledge gaps, and produces personalized tutorial sessions
    that adapt to the developer's current skill level.
    """

    _instance: Optional[TutorialOrchestrator] = None
    _lock = threading.RLock()

    def __new__(cls) -> TutorialOrchestrator:
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    instance = super().__new__(cls)
                    cls._instance = instance
        return cls._instance

    @classmethod
    def get_instance(cls) -> TutorialOrchestrator:
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    instance = super().__new__(cls)
                    instance.__init__()
                    cls._instance = instance
        return cls._instance

    def __init__(self) -> None:
        with self._lock:
            if hasattr(self, "_initialized") and self._initialized:
                return
            self._tutorial_templates: Dict[str, Dict[str, Any]] = {}
            self._learner_profiles: Dict[str, LearnerProfile] = {}
            self._active_sessions: Dict[str, TutorialSession] = {}
            self._stats: Dict[str, Any] = {
                "total_behaviors_tracked": 0,
                "total_sessions_generated": 0,
                "total_steps_completed": 0,
                "tutorials_by_type": {
                    t.value: 0 for t in TutorialType
                },
                "sessions_by_objective": {
                    o.value: 0 for o in LearningObjective
                },
            }
            self._behavior_history: Dict[str, List[Dict[str, Any]]] = {}
            self._max_history_per_user: int = 200
            self._initialized = True

    # ------------------------------------------------------------------
    # Behavior Tracking
    # ------------------------------------------------------------------

    def track_behavior(self, user_id: str, action: str, context: Optional[Dict[str, Any]] = None) -> None:
        with self._lock:
            profile = self._ensure_profile(user_id)

            profile.observed_behaviors[action] = profile.observed_behaviors.get(action, 0) + 1
            profile.last_updated = _time_module.time()

            entry: Dict[str, Any] = {
                "action": action,
                "timestamp": _time_module.time(),
                "context": context or {},
            }
            if user_id not in self._behavior_history:
                self._behavior_history[user_id] = []
            history = self._behavior_history[user_id]
            history.append(entry)
            if len(history) > self._max_history_per_user:
                self._behavior_history[user_id] = history[-self._max_history_per_user:]

            self._stats["total_behaviors_tracked"] += 1

            objective = _FEATURE_OBJECTIVE_MAP.get(action)
            if objective is not None:
                objective_key = objective.value
                if objective_key not in profile.mastered_topics:
                    usage_count = profile.observed_behaviors.get(action, 0)
                    related_actions = [
                        a for a, obj in _FEATURE_OBJECTIVE_MAP.items()
                        if obj == objective and a in profile.observed_behaviors
                    ]
                    if len(related_actions) >= 3 and usage_count >= 5:
                        if objective_key not in profile.mastered_topics:
                            profile.mastered_topics.append(objective_key)

            self._refresh_recommendations(profile)

    # ------------------------------------------------------------------
    # Knowledge Gap Detection
    # ------------------------------------------------------------------

    def detect_knowledge_gap(self, user_id: str) -> List[LearningObjective]:
        with self._lock:
            profile = self._ensure_profile(user_id)

            touched_objectives: set = set()
            for action, count in profile.observed_behaviors.items():
                objective = _FEATURE_OBJECTIVE_MAP.get(action)
                if objective is not None:
                    touched_objectives.add(objective)

            mastered = set()
            for topic_name in profile.mastered_topics:
                try:
                    mastered.add(LearningObjective(topic_name))
                except ValueError:
                    pass

            gaps: List[Tuple[LearningObjective, int]] = []
            for obj in LearningObjective:
                if obj in mastered:
                    continue

                prereqs = _LEARNING_PREREQUISITES.get(obj, [])
                prereqs_met = all(p in mastered for p in prereqs)
                if not prereqs_met:
                    continue

                used_features = sum(
                    1 for a, o in _FEATURE_OBJECTIVE_MAP.items()
                    if o == obj and a in profile.observed_behaviors
                )
                priority = 10 - used_features
                gaps.append((obj, priority))

            gaps.sort(key=lambda x: x[1], reverse=True)

            return [g[0] for g in gaps]

    # ------------------------------------------------------------------
    # Tutorial Generation
    # ------------------------------------------------------------------

    def generate_tutorial(
        self,
        user_id: str,
        objective: LearningObjective,
        tutorial_type: TutorialType,
    ) -> TutorialSession:
        with self._lock:
            profile = self._ensure_profile(user_id)
            skill = self._assess_skill_internal(profile)

            steps = self._build_tutorial_steps(objective, tutorial_type, skill)

            session = TutorialSession(
                objective=objective,
                steps=steps,
                skill_level=skill,
            )
            self._active_sessions[session.id] = session

            self._stats["total_sessions_generated"] += 1
            self._stats["tutorials_by_type"][tutorial_type.value] += 1
            self._stats["sessions_by_objective"][objective.value] += 1

            return session

    # ------------------------------------------------------------------
    # Session Step Navigation
    # ------------------------------------------------------------------

    def get_next_step(self, session_id: str) -> Optional[TutorialStep]:
        with self._lock:
            session = self._active_sessions.get(session_id)
            if session is None:
                return None
            if session.is_complete:
                return None
            if session.current_step_index >= len(session.steps):
                return None
            return session.steps[session.current_step_index]

    def complete_step(self, session_id: str, step_id: str) -> bool:
        with self._lock:
            session = self._active_sessions.get(session_id)
            if session is None:
                return False

            if session.is_complete:
                return False

            current = session.steps[session.current_step_index]
            if current.id != step_id:
                return False

            session.completed_steps.append(step_id)
            session.current_step_index += 1
            self._stats["total_steps_completed"] += 1

            return True

    # ------------------------------------------------------------------
    # Skill Assessment
    # ------------------------------------------------------------------

    def assess_skill_level(self, user_id: str) -> SkillLevel:
        with self._lock:
            profile = self._ensure_profile(user_id)
            return self._assess_skill_internal(profile)

    def _assess_skill_internal(self, profile: LearnerProfile) -> SkillLevel:
        total_actions = sum(profile.observed_behaviors.values())
        num_mastered = len(profile.mastered_topics)
        unique_features = len(profile.observed_behaviors)
        struggle_count = len(profile.struggle_areas)

        if total_actions == 0:
            return SkillLevel.ABSOLUTE_BEGINNER

        if num_mastered >= 7 and unique_features >= 18 and struggle_count <= 1:
            return SkillLevel.EXPERT
        if num_mastered >= 5 and unique_features >= 14:
            return SkillLevel.ADVANCED
        if num_mastered >= 3 and unique_features >= 9:
            return SkillLevel.INTERMEDIATE
        if total_actions >= 5 and unique_features >= 3:
            return SkillLevel.BEGINNER
        return SkillLevel.ABSOLUTE_BEGINNER

    # ------------------------------------------------------------------
    # Learning Path Recommendation
    # ------------------------------------------------------------------

    def recommend_learning_path(self, user_id: str) -> List[LearningObjective]:
        with self._lock:
            profile = self._ensure_profile(user_id)

            mastered = set()
            for topic_name in profile.mastered_topics:
                try:
                    mastered.add(LearningObjective(topic_name))
                except ValueError:
                    pass

            touched_objectives: set = set()
            objective_usage: Dict[LearningObjective, int] = {}
            for action, count in profile.observed_behaviors.items():
                objective = _FEATURE_OBJECTIVE_MAP.get(action)
                if objective is not None:
                    touched_objectives.add(objective)
                    objective_usage[objective] = objective_usage.get(objective, 0) + count

            remaining: List[Tuple[LearningObjective, int]] = []
            for obj in LearningObjective:
                if obj in mastered:
                    continue

                prereqs = _LEARNING_PREREQUISITES.get(obj, [])
                prereqs_met = all(p in mastered for p in prereqs)
                if not prereqs_met:
                    continue

                priority = 0
                if obj in touched_objectives:
                    priority += objective_usage.get(obj, 0)
                priority += (9 - len(_LEARNING_PREREQUISITES.get(obj, []))) * 2
                remaining.append((obj, priority))

            remaining.sort(key=lambda x: x[1], reverse=True)

            path = [r[0] for r in remaining]

            for obj in LearningObjective:
                if obj not in path and obj not in mastered:
                    prereqs = _LEARNING_PREREQUISITES.get(obj, [])
                    prereqs_mastered = all(p in mastered for p in prereqs)
                    if prereqs_mastered:
                        path.append(obj)

            return path

    # ------------------------------------------------------------------
    # Statistics
    # ------------------------------------------------------------------

    def get_stats(self) -> Dict[str, Any]:
        with self._lock:
            active_count = sum(
                1 for s in self._active_sessions.values() if not s.is_complete
            )
            completed_count = sum(
                1 for s in self._active_sessions.values() if s.is_complete
            )
            total_steps_across_sessions = sum(
                s.total_steps for s in self._active_sessions.values()
            )

            skill_distribution: Dict[str, int] = {}
            for profile in self._learner_profiles.values():
                skill = self._assess_skill_internal(profile)
                key = skill.value
                skill_distribution[key] = skill_distribution.get(key, 0) + 1

            return {
                "total_learner_profiles": len(self._learner_profiles),
                "total_behaviors_tracked": self._stats["total_behaviors_tracked"],
                "total_sessions_generated": self._stats["total_sessions_generated"],
                "total_steps_completed": self._stats["total_steps_completed"],
                "active_sessions": active_count,
                "completed_sessions": completed_count,
                "total_steps_in_sessions": total_steps_across_sessions,
                "tutorials_by_type": dict(self._stats["tutorials_by_type"]),
                "sessions_by_objective": dict(self._stats["sessions_by_objective"]),
                "skill_distribution": skill_distribution,
            }

    # ------------------------------------------------------------------
    # Internal Helpers
    # ------------------------------------------------------------------

    def _ensure_profile(self, user_id: str) -> LearnerProfile:
        if user_id not in self._learner_profiles:
            profile = LearnerProfile()
            self._learner_profiles[user_id] = profile
        return self._learner_profiles[user_id]

    def _refresh_recommendations(self, profile: LearnerProfile) -> None:
        mastered = set(profile.mastered_topics)
        recommendations: List[str] = []

        for obj in LearningObjective:
            if obj.value in mastered:
                continue
            prereqs = _LEARNING_PREREQUISITES.get(obj, [])
            if all(p.value in mastered for p in prereqs):
                recommendations.append(obj.value)

        profile.recommended_next = recommendations
        profile.last_updated = _time_module.time()

    def _build_tutorial_steps(
        self,
        objective: LearningObjective,
        tutorial_type: TutorialType,
        skill: SkillLevel,
    ) -> List[TutorialStep]:
        step_count = self._step_count_for_level(skill)
        objective_data = self._objective_step_templates(objective)

        steps: List[TutorialStep] = []
        for i in range(min(step_count, len(objective_data))):
            template = objective_data[i]
            hints = list(template.get("hints", []))
            if skill in (SkillLevel.ABSOLUTE_BEGINNER, SkillLevel.BEGINNER):
                hints = hints[:4]
            else:
                hints = hints[:2] if hints else []

            step = TutorialStep(
                title=template.get("title", f"Step {i + 1}"),
                description=template.get("description", ""),
                action_required=template.get("action_required", ""),
                expected_result=template.get("expected_result", ""),
                hints=hints,
                completion_criteria=template.get("completion_criteria", {}),
            )
            steps.append(step)

        return steps

    @staticmethod
    def _step_count_for_level(skill: SkillLevel) -> int:
        mapping = {
            SkillLevel.ABSOLUTE_BEGINNER: 8,
            SkillLevel.BEGINNER: 6,
            SkillLevel.INTERMEDIATE: 5,
            SkillLevel.ADVANCED: 4,
            SkillLevel.EXPERT: 3,
        }
        return mapping.get(skill, 6)

    @staticmethod
    def _objective_step_templates(objective: LearningObjective) -> List[Dict[str, Any]]:
        templates: Dict[LearningObjective, List[Dict[str, Any]]] = {
            LearningObjective.ENGINE_BASICS: [
                {
                    "title": "Launch the SparkLabs Editor",
                    "description": "Open the SparkLabs application and create a new project to begin exploring the game engine interface.",
                    "action_required": "Click 'New Project' on the welcome screen and select the 2D template.",
                    "expected_result": "A blank project opens with the main editor layout visible: viewport, hierarchy, inspector, and project panels.",
                    "hints": [
                        "You can also use File > New Project from the menu bar",
                        "The 2D template includes a default camera and light setup",
                        "Try switching between the 3D and 2D template previews",
                    ],
                    "completion_criteria": {"project_created": True, "editor_visible": True},
                },
                {
                    "title": "Navigate the Viewport",
                    "description": "Learn basic viewport controls to move around your scene efficiently.",
                    "action_required": "Use scroll to zoom, right-click drag to rotate, and middle-click drag to pan the viewport camera.",
                    "expected_result": "You can zoom in/out, rotate around the scene origin, and pan freely within the viewport.",
                    "hints": [
                        "Hold Shift while panning to move faster",
                        "Press F to focus on the selected object",
                        "The compass widget in the corner shows your current view angle",
                    ],
                    "completion_criteria": {"viewport_navigated": True},
                },
                {
                    "title": "Explore the Hierarchy Panel",
                    "description": "Understand the scene hierarchy where all game objects are organized in parent-child relationships.",
                    "action_required": "Click on objects in the hierarchy to select them. Try dragging objects to re-parent them.",
                    "expected_result": "Selected objects highlight in the viewport and their properties appear in the inspector panel.",
                    "hints": [
                        "Right-click in the hierarchy to create new objects",
                        "Objects can be nested for organizational grouping",
                        "Use the search bar at the top to quickly find objects by name",
                    ],
                    "completion_criteria": {"objects_selected": 3, "hierarchy_explored": True},
                },
                {
                    "title": "Use the Inspector Panel",
                    "description": "Modify object properties through the inspector to change how objects behave in your scene.",
                    "action_required": "Select a game object and modify its transform position, rotation, or scale values.",
                    "expected_result": "The object moves, rotates, or scales in the viewport in real-time as values change.",
                    "hints": [
                        "You can type exact values or click-drag on the label to scrub",
                        "The reset button returns transform values to their defaults",
                        "Components can be added via the 'Add Component' button at the bottom",
                    ],
                    "completion_criteria": {"property_modified": True},
                },
                {
                    "title": "Save Your Project",
                    "description": "Learn to save your work and understand the project file structure on disk.",
                    "action_required": "Press Ctrl+S (Cmd+S on Mac) to save the current scene and project.",
                    "expected_result": "The project is saved to disk. The title bar no longer shows an unsaved indicator.",
                    "hints": [
                        "Scenes are saved as .spark files in the Assets/Scenes folder",
                        "Auto-save can be enabled in Edit > Preferences",
                        "Use File > Save As to create versioned scene copies",
                    ],
                    "completion_criteria": {"project_saved": True},
                },
                {
                    "title": "Open the Asset Browser",
                    "description": "Explore the project panel to see all files and assets available in your current project.",
                    "action_required": "Click through folders in the project panel and preview assets by double-clicking them.",
                    "expected_result": "The project panel displays folder contents with thumbnails for supported asset types.",
                    "hints": [
                        "Right-click to create new folders and assets",
                        "Drag assets from your file system directly into the panel",
                        "The filter dropdown lets you view only specific file types",
                    ],
                    "completion_criteria": {"asset_browser_opened": True},
                },
                {
                    "title": "Configure Project Settings",
                    "description": "Adjust project-wide settings that affect how your game runs and is displayed.",
                    "action_required": "Open Edit > Project Settings and browse the available configuration categories.",
                    "expected_result": "The project settings window appears with tabs for graphics, input, physics, and publishing.",
                    "hints": [
                        "Resolution and aspect ratio are configured under Graphics",
                        "Input mappings define which keys trigger which actions",
                        "Changes to settings apply immediately to the editor preview",
                    ],
                    "completion_criteria": {"settings_explored": True},
                },
                {
                    "title": "Run the Game Preview",
                    "description": "Test your scene by entering play mode to see how it behaves at runtime.",
                    "action_required": "Click the Play button in the toolbar to enter play mode, then click it again to stop.",
                    "expected_result": "The viewport enters play mode with runtime behavior active. Changes made in play mode are discarded on stop.",
                    "hints": [
                        "Pause and Step buttons let you freeze and advance frame-by-frame",
                        "Changes to scripts during play mode take effect on the next play",
                        "The console panel shows runtime logs and errors",
                    ],
                    "completion_criteria": {"play_mode_entered": True},
                },
            ],
            LearningObjective.SCENE_CREATION: [
                {
                    "title": "Create a New Scene",
                    "description": "Set up a new scene file that will contain your game level or menu.",
                    "action_required": "Right-click in the project panel, select Create > Scene, and name it 'Level1'.",
                    "expected_result": "A new empty scene is created and opened, ready for content.",
                    "hints": [
                        "Scenes can be loaded via the scene manager at runtime",
                        "Use descriptive names for easy identification",
                        "Multiple scenes can be open simultaneously in different tabs",
                    ],
                    "completion_criteria": {"scene_created": True},
                },
                {
                    "title": "Place Game Objects",
                    "description": "Add 3D primitives and 2D sprites to populate your scene with visible content.",
                    "action_required": "Right-click in the hierarchy and add a Cube, a Sphere, and a Plane to the scene.",
                    "expected_result": "Three objects appear in the viewport and hierarchy with default materials.",
                    "hints": [
                        "Use the Gizmo toolbar to switch between move, rotate, and scale modes",
                        "Objects snap to grid when holding Ctrl (Cmd on Mac) while moving",
                        "Duplicate objects with Ctrl+D (Cmd+D on Mac) for rapid layout",
                    ],
                    "completion_criteria": {"objects_placed": 3},
                },
                {
                    "title": "Arrange Objects in 3D Space",
                    "description": "Position and orient objects to create an interesting scene composition.",
                    "action_required": "Move, rotate, and scale the objects to create a platform with obstacles arrangement.",
                    "expected_result": "Objects are positioned in a spatial layout that forms a playable area.",
                    "hints": [
                        "Switch to top-down view (press 7 on the numpad) for precise layout",
                        "Use vertex snapping (hold V) to align objects perfectly",
                        "Group related objects under an empty parent for easy manipulation",
                    ],
                    "completion_criteria": {"objects_arranged": True},
                },
                {
                    "title": "Apply Materials",
                    "description": "Give visual identity to objects by applying colored or textured materials.",
                    "action_required": "Create a new material, assign a color, and drag it onto a game object.",
                    "expected_result": "The object changes color in the viewport. Multiple objects can share the same material.",
                    "hints": [
                        "Right-click in the project panel > Create > Material",
                        "Materials support PBR properties: albedo, metallic, smoothness",
                        "Texture maps can be dragged into material property slots",
                    ],
                    "completion_criteria": {"material_applied": True},
                },
                {
                    "title": "Add Lighting",
                    "description": "Illuminate your scene with directional, point, and spot lights for atmosphere.",
                    "action_required": "Add a Directional Light and a Point Light, adjusting their intensity and color.",
                    "expected_result": "The scene is lit with shadows and ambient illumination. Point light creates a localized glow effect.",
                    "hints": [
                        "Directional lights simulate sunlight with parallel rays",
                        "Point lights emit in all directions from a single point",
                        "Use the light's Range property to limit influence distance",
                    ],
                    "completion_criteria": {"lighting_added": True},
                },
            ],
            LearningObjective.SCRIPTING: [
                {
                    "title": "Create Your First Script",
                    "description": "Write a simple script that controls a game object's behavior at runtime.",
                    "action_required": "Right-click in the project panel > Create > Script, name it 'Rotator', and open it.",
                    "expected_result": "The script editor opens with a template class. The script compiles without errors.",
                    "hints": [
                        "Scripts in SparkLabs use Python by default",
                        "The Start method runs once when the object is created",
                        "The Update method runs every frame",
                    ],
                    "completion_criteria": {"script_created": True},
                },
                {
                    "title": "Rotate an Object",
                    "description": "Write code to make an object continuously rotate in the scene.",
                    "action_required": "In the Update method, add code to rotate the object around its Y axis using delta time.",
                    "expected_result": "The attached object spins smoothly in play mode at a consistent speed.",
                    "hints": [
                        "Use self.transform.rotate() for incremental rotation",
                        "Multiply by Time.delta_time for frame-rate independence",
                        "Try different axes (X, Y, Z) to see different rotation effects",
                    ],
                    "completion_criteria": {"rotation_working": True},
                },
                {
                    "title": "Respond to Input",
                    "description": "Handle keyboard or mouse input to make an object interactive.",
                    "action_required": "Write code to move an object when arrow keys or WASD are pressed.",
                    "expected_result": "The object moves in response to key presses in play mode.",
                    "hints": [
                        "Use Input.get_key() to check for key states each frame",
                        "Input.get_axis('Horizontal') works with arrow keys and WASD",
                        "Combine input with Time.delta_time for smooth movement",
                    ],
                    "completion_criteria": {"input_handling_working": True},
                },
                {
                    "title": "Use Variables and Properties",
                    "description": "Create exposed variables that can be adjusted from the inspector without changing code.",
                    "action_required": "Add a public float variable for speed and modify it in the inspector.",
                    "expected_result": "Changing the speed value in the inspector immediately affects runtime behavior.",
                    "hints": [
                        "Use the @expose decorator to show variables in the inspector",
                        "Range attributes like @range(0, 100) create sliders",
                        "Organize exposed variables with @category('Movement')",
                    ],
                    "completion_criteria": {"exposed_variable_used": True},
                },
                {
                    "title": "Debug with Logging",
                    "description": "Use console logging to inspect values and trace execution during development.",
                    "action_required": "Add Debug.log() calls to print object position each frame.",
                    "expected_result": "The console panel shows position values updating in real-time during play mode.",
                    "hints": [
                        "Use Debug.log_warning() and Debug.log_error() for severity levels",
                        "String interpolation: Debug.log(f'Position: {pos}')",
                        "Filter console output by type using the toolbar buttons",
                    ],
                    "completion_criteria": {"logging_used": True},
                },
            ],
            LearningObjective.ASSETS: [
                {
                    "title": "Import External Assets",
                    "description": "Bring images, audio files, and 3D models from outside into your project.",
                    "action_required": "Drag an image file from your file explorer into the project panel's Assets folder.",
                    "expected_result": "The image appears in the project panel with a thumbnail preview and is ready to use.",
                    "hints": [
                        "Supported image formats: PNG, JPG, TGA, PSD, HDR",
                        "Drag multiple files at once for batch import",
                        "The import settings dialog lets you configure compression per asset",
                    ],
                    "completion_criteria": {"asset_imported": True},
                },
                {
                    "title": "Configure Sprite Settings",
                    "description": "Set up 2D sprites with proper pivot points, slice sheets, and filtering modes.",
                    "action_required": "Select an imported image and change its Texture Type to Sprite in the inspector.",
                    "expected_result": "The image can now be dragged into the scene as a sprite object.",
                    "hints": [
                        "Set Sprite Mode to Multiple for sprite sheets",
                        "Pivot point determines the rotation and position origin",
                        "Filter Mode affects how the sprite looks when scaled",
                    ],
                    "completion_criteria": {"sprite_configured": True},
                },
                {
                    "title": "Add Audio to the Scene",
                    "description": "Import and configure sound effects or background music for your game.",
                    "action_required": "Import an audio file and add an Audio Source component to a game object.",
                    "expected_result": "Sound plays when the scene runs. Audio can be 2D (no spatialization) or 3D (positional).",
                    "hints": [
                        "Supported audio formats: WAV, MP3, OGG, FLAC",
                        "Use AudioSource.play_on_start() for background music",
                        "3D audio requires an Audio Listener on the main camera",
                    ],
                    "completion_criteria": {"audio_working": True},
                },
                {
                    "title": "Build a Prefab",
                    "description": "Create reusable asset templates by converting configured game objects into prefabs.",
                    "action_required": "Drag a configured game object from the hierarchy into the project panel.",
                    "expected_result": "A prefab asset is created. Dragging it back into the scene creates identical instances.",
                    "hints": [
                        "Prefab instances are shown in blue in the hierarchy",
                        "Overrides on instances are shown in bold in the inspector",
                        "Use Apply to push instance changes back to the prefab source",
                    ],
                    "completion_criteria": {"prefab_created": True},
                },
            ],
            LearningObjective.PHYSICS: [
                {
                    "title": "Add Rigidbody Component",
                    "description": "Enable physics simulation on a game object by attaching a rigidbody.",
                    "action_required": "Select a game object and add a Rigidbody component from the inspector.",
                    "expected_result": "The object falls under gravity when entering play mode, colliding with other physics objects.",
                    "hints": [
                        "Set Mass to control how heavy the object feels",
                        "Drag affects how quickly the object slows in air",
                        "Use Kinematic mode when you want script-controlled physics movement",
                    ],
                    "completion_criteria": {"rigidbody_added": True},
                },
                {
                    "title": "Configure Colliders",
                    "description": "Define collision shapes that determine how objects physically interact.",
                    "action_required": "Add a Box Collider, adjust its size, and observe collision behavior in play mode.",
                    "expected_result": "Objects bounce and rest on each other based on their collider shapes and physics materials.",
                    "hints": [
                        "Use primitive colliders (box, sphere, capsule) for better performance",
                        "Mesh colliders match the exact visual shape but are more expensive",
                        "Trigger colliders detect overlaps without physical collision response",
                    ],
                    "completion_criteria": {"collider_configured": True},
                },
                {
                    "title": "Apply Forces via Script",
                    "description": "Control physics objects programmatically by applying forces and impulses.",
                    "action_required": "Write a script that applies an upward force when the spacebar is pressed.",
                    "expected_result": "The object jumps upward each time spacebar is pressed, with realistic physics.",
                    "hints": [
                        "Use rigidbody.add_force() for continuous force application",
                        "Use rigidbody.add_impulse() for instantaneous pushes",
                        "ForceMode.Impulse applies the force instantly without mass scaling",
                    ],
                    "completion_criteria": {"force_applied": True},
                },
                {
                    "title": "Create Physics Materials",
                    "description": "Define surface properties like bounciness and friction for realistic interactions.",
                    "action_required": "Create a Physics Material with high bounciness and assign it to a collider.",
                    "expected_result": "Objects with the bouncy material rebound energetically on collision.",
                    "hints": [
                        "Bounciness of 1.0 means perfectly elastic (no energy loss)",
                        "Static friction controls resistance to starting movement",
                        "Dynamic friction controls resistance during movement",
                    ],
                    "completion_criteria": {"physics_material_created": True},
                },
            ],
            LearningObjective.UI_DESIGN: [
                {
                    "title": "Create a Canvas",
                    "description": "Set up the UI rendering surface that all interface elements live on.",
                    "action_required": "Right-click in the hierarchy > UI > Canvas. Set its render mode to Screen Space Overlay.",
                    "expected_result": "A canvas appears covering the game view. All UI elements added as children render on screen.",
                    "hints": [
                        "Screen Space Overlay renders UI on top of the game view",
                        "Screen Space Camera places UI in world space relative to a camera",
                        "World Space allows UI to exist as 3D objects in the scene",
                    ],
                    "completion_criteria": {"canvas_created": True},
                },
                {
                    "title": "Add a Button",
                    "description": "Create an interactive button that responds to clicks and hovers.",
                    "action_required": "Right-click the Canvas > UI > Button. Configure its text label and colors.",
                    "expected_result": "A button appears on screen. It changes color on hover and triggers an event on click.",
                    "hints": [
                        "The Button component has Normal, Highlighted, Pressed, and Disabled color states",
                        "Use the OnClick event list to wire up script methods",
                        "Button text is controlled by its child Text component",
                    ],
                    "completion_criteria": {"button_created": True},
                },
                {
                    "title": "Layout with Anchors",
                    "description": "Use anchor presets to make UI elements adapt to different screen sizes.",
                    "action_required": "Select the button and use the anchor preset dropdown to anchor it to the bottom-center.",
                    "expected_result": "The button stays fixed to the bottom-center of the screen regardless of window resizing.",
                    "hints": [
                        "Hold Shift to also set the pivot position",
                        "Hold Alt to also set the position",
                        "Stretch anchors make elements scale with screen size",
                    ],
                    "completion_criteria": {"anchors_configured": True},
                },
                {
                    "title": "Create a Slider",
                    "description": "Build a slider control for adjusting numeric values like volume or settings.",
                    "action_required": "Add a Slider UI element with min value 0 and max value 100.",
                    "expected_result": "Dragging the slider handle changes its value, displayed in the inspector and accessible via script.",
                    "hints": [
                        "The OnValueChanged event fires every time the slider moves",
                        "Use WholeNumbers mode to snap to integer values",
                        "Customize handle, fill, and background visuals independently",
                    ],
                    "completion_criteria": {"slider_created": True},
                },
                {
                    "title": "Wire UI to Game Logic",
                    "description": "Connect UI events to game scripts for interactive functionality.",
                    "action_required": "Write a script method that changes an object's color and wire it to the button's OnClick event.",
                    "expected_result": "Clicking the button in play mode triggers the script and the object changes color.",
                    "hints": [
                        "Drag the script component into the OnClick slot",
                        "Select the target method from the dropdown",
                        "Use public method signatures for easy event binding",
                    ],
                    "completion_criteria": {"ui_game_linked": True},
                },
            ],
            LearningObjective.MULTIPLAYER: [
                {
                    "title": "Configure Network Manager",
                    "description": "Set up the core networking component that handles connections and spawning.",
                    "action_required": "Add a Network Manager component to an empty game object in the scene.",
                    "expected_result": "The network manager appears in the inspector with configuration for transport, player prefab, and spawn settings.",
                    "hints": [
                        "The transport layer handles the actual network communication",
                        "Player prefab is spawned for each connecting client",
                        "Network Manager can operate as Host (server+client) or Server only",
                    ],
                    "completion_criteria": {"network_manager_configured": True},
                },
                {
                    "title": "Create a Networked Object",
                    "description": "Make a game object synchronize its state across all connected clients.",
                    "action_required": "Add a Network Identity component to a game object and enable server authority.",
                    "expected_result": "The object's transform and networked variables sync across all connected players.",
                    "hints": [
                        "Network Identity is required on every networked object",
                        "Server Authority means only the server can modify the object",
                        "Local Player Authority allows the owning client to control the object",
                    ],
                    "completion_criteria": {"networked_object_created": True},
                },
                {
                    "title": "Sync Variables",
                    "description": "Declare variables that automatically synchronize across the network.",
                    "action_required": "Create a script with a SyncVar health variable and display it on a UI text element.",
                    "expected_result": "When health changes on the server, all clients see the updated value automatically.",
                    "hints": [
                        "Use the @sync_var decorator on fields that need network sync",
                        "SyncVar hooks let you trigger callbacks when values change",
                        "Only the server should modify SyncVars directly",
                    ],
                    "completion_criteria": {"sync_var_working": True},
                },
                {
                    "title": "Send Remote Procedure Calls",
                    "description": "Call methods across the network with RPCs for game events and commands.",
                    "action_required": "Create a ClientRpc method that spawns a visual effect on all clients.",
                    "expected_result": "Calling the RPC on the server triggers the visual effect on every connected client.",
                    "hints": [
                        "ServerRpc: client calls, server executes",
                        "ClientRpc: server calls, all clients execute",
                        "TargetRpc: server calls, specific client executes",
                    ],
                    "completion_criteria": {"rpc_working": True},
                },
            ],
            LearningObjective.OPTIMIZATION: [
                {
                    "title": "Open the Profiler",
                    "description": "Use the performance profiler to identify bottlenecks in your game.",
                    "action_required": "Open Window > Profiler and enter play mode to capture performance data.",
                    "expected_result": "The profiler displays CPU usage, memory allocation, and rendering statistics in real-time.",
                    "hints": [
                        "The timeline view shows per-frame performance breakdown",
                        "Deep Profile mode instruments every method call for granular data",
                        "Click on a spike to see what caused the frame time increase",
                    ],
                    "completion_criteria": {"profiler_opened": True},
                },
                {
                    "title": "Batch Draw Calls",
                    "description": "Reduce the number of GPU draw calls by combining similar objects.",
                    "action_required": "Enable Static Batching on multiple stationary objects and observe the draw call reduction in the stats panel.",
                    "expected_result": "The draw call count decreases while visual output remains identical.",
                    "hints": [
                        "Static batching works only on objects marked as Static",
                        "Objects must share the same material to batch together",
                        "Dynamic batching handles moving objects automatically",
                    ],
                    "completion_criteria": {"batching_enabled": True},
                },
                {
                    "title": "Implement Object Pooling",
                    "description": "Reuse frequently spawned objects instead of creating and destroying them repeatedly.",
                    "action_required": "Write an object pool script that pre-instantiates bullets and recycles them.",
                    "expected_result": "Bullets are taken from the pool and returned instead of being created and garbage collected.",
                    "hints": [
                        "Pre-warm the pool with enough instances during scene load",
                        "Use object.active = True/False instead of instantiate/destroy",
                        "Reset object state when retrieving from the pool",
                    ],
                    "completion_criteria": {"object_pooling_implemented": True},
                },
                {
                    "title": "Optimize Textures",
                    "description": "Configure texture import settings for optimal memory usage and visual quality.",
                    "action_required": "Reduce the Max Size and enable compression on imported textures through the inspector.",
                    "expected_result": "Texture memory usage decreases with minimal visual quality loss at appropriate sizes.",
                    "hints": [
                        "Use power-of-two texture sizes for GPU efficiency",
                        "Crunch compression reduces size further with slight quality trade-off",
                        "Generate Mip Maps for textures viewed at varying distances",
                    ],
                    "completion_criteria": {"texture_optimized": True},
                },
            ],
            LearningObjective.PUBLISHING: [
                {
                    "title": "Configure Build Settings",
                    "description": "Set up the target platform and build options for your game export.",
                    "action_required": "Open File > Build Settings, select your target platform, and click Switch Platform.",
                    "expected_result": "The build pipeline reimports assets for the selected platform. The platform icon appears next to it.",
                    "hints": [
                        "Common targets: Windows, macOS, Linux, Web, iOS, Android",
                        "Switching platforms requires asset reimport, which can take time",
                        "Add scenes to the build list to include them in the final build",
                    ],
                    "completion_criteria": {"build_settings_configured": True},
                },
                {
                    "title": "Set Player Settings",
                    "description": "Define application metadata, icons, and resolution defaults for your published game.",
                    "action_required": "Click Player Settings in Build Settings and configure the company name and product name.",
                    "expected_result": "The game executable will display the configured name and icon in the operating system.",
                    "hints": [
                        "The Default Icon section controls the application icon across platforms",
                        "Resolution settings determine the default window size and fullscreen mode",
                        "Splash screen settings let you customize the loading screen",
                    ],
                    "completion_criteria": {"player_settings_configured": True},
                },
                {
                    "title": "Perform a Development Build",
                    "description": "Create a debug-enabled build to test your game outside the editor.",
                    "action_required": "Enable Development Build in Build Settings and click Build to export the game.",
                    "expected_result": "A standalone executable is created. Running it shows debug logs and profiling capabilities.",
                    "hints": [
                        "Development builds include debug symbols and logging",
                        "Autoconnect Profiler links the running build to the editor profiler",
                        "Script debugging is only available in development builds",
                    ],
                    "completion_criteria": {"development_build_complete": True},
                },
            ],
        }
        return templates.get(objective, [])


# ------------------------------------------------------------------
# Module-level accessor
# ------------------------------------------------------------------


def get_tutorial_orchestrator() -> TutorialOrchestrator:
    return TutorialOrchestrator.get_instance()