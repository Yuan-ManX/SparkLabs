"""
SparkLabs Agent - Tutorial Designer Engine

AI-driven tutorial design system for the AI-native game engine.
Creates adaptive tutorials that respond to player skill level,
learning pace, and behavior patterns. Generates personalized
learning sequences with dynamic step ordering, difficulty
calibration, and comprehension-aware scaffolding.

Architecture:
  TutorialDesignerEngine
    |-- SkillAssessor (latent skill estimation from gameplay)
    |-- StyleDetector (learning style inference from behavior)
    |-- ModuleComposer (step sequence generation with prerequisites)
    |-- ProgressTracker (per-player tutorial state management)
    |-- AdaptationEngine (in-flight difficulty and pace adjustment)

Design Goals:
  - Minimize tutorial friction for experienced players
  - Provide extra scaffolding when player struggles are detected
  - Respect individual learning style preferences
  - Enable partial tutorial replay for targeted skill gaps
"""

from __future__ import annotations

import json
import random
import threading
import time
import uuid
from collections import deque
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class TutorialType(Enum):
    """Categories of tutorial delivery methods."""
    WALKTHROUGH = "walkthrough"
    INTERACTIVE = "interactive"
    TOOLTIP = "tooltip"
    VIDEO = "video"
    CHALLENGE = "challenge"
    SANDBOX = "sandbox"
    ONBOARDING = "onboarding"
    ADVANCED = "advanced"
    REFRESHER = "refresher"


class LearningStyle(Enum):
    """Player learning modality preferences inferred from behavior."""
    VISUAL = "visual"
    TEXTUAL = "textual"
    KINESTHETIC = "kinesthetic"
    HYBRID = "hybrid"
    ADAPTIVE = "adaptive"


class SkillLevel(Enum):
    """Granular player proficiency tiers."""
    BEGINNER = "beginner"
    NOVICE = "novice"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"
    EXPERT = "expert"
    MASTER = "master"

    @classmethod
    def from_score(cls, score: float) -> SkillLevel:
        """Map a numeric proficiency score (0.0-1.0) to a skill level."""
        if score < 0.15:
            return cls.BEGINNER
        if score < 0.35:
            return cls.NOVICE
        if score < 0.60:
            return cls.INTERMEDIATE
        if score < 0.80:
            return cls.ADVANCED
        if score < 0.95:
            return cls.EXPERT
        return cls.MASTER

    @property
    def tier(self) -> int:
        """Numeric tier for ordering comparisons (0-5)."""
        return {
            SkillLevel.BEGINNER: 0,
            SkillLevel.NOVICE: 1,
            SkillLevel.INTERMEDIATE: 2,
            SkillLevel.ADVANCED: 3,
            SkillLevel.EXPERT: 4,
            SkillLevel.MASTER: 5,
        }[self]


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------


@dataclass
class TutorialStep:
    """A single instructional step within a tutorial module."""
    step_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    title: str = ""
    instruction: str = ""
    action_required: str = ""
    expected_input: str = ""
    help_text: str = ""
    completion_criteria: Dict[str, Any] = field(default_factory=dict)
    is_optional: bool = False
    order: int = 0
    duration_estimate: float = 30.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "step_id": self.step_id,
            "title": self.title,
            "instruction": self.instruction,
            "action_required": self.action_required,
            "expected_input": self.expected_input,
            "help_text": self.help_text,
            "completion_criteria": self.completion_criteria,
            "is_optional": self.is_optional,
            "order": self.order,
            "duration_estimate": self.duration_estimate,
        }


@dataclass
class TutorialModule:
    """A complete tutorial covering a specific topic with ordered steps."""
    module_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    title: str = ""
    description: str = ""
    topic: str = ""
    tutorial_type: TutorialType = TutorialType.INTERACTIVE
    learning_style: LearningStyle = LearningStyle.ADAPTIVE
    skill_level: SkillLevel = SkillLevel.BEGINNER
    steps: List[TutorialStep] = field(default_factory=list)
    prerequisites: List[str] = field(default_factory=list)
    learning_objectives: List[str] = field(default_factory=list)
    estimated_duration: float = 0.0
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "module_id": self.module_id,
            "title": self.title,
            "description": self.description,
            "topic": self.topic,
            "tutorial_type": self.tutorial_type.value,
            "learning_style": self.learning_style.value,
            "skill_level": self.skill_level.value,
            "step_count": len(self.steps),
            "prerequisites": self.prerequisites,
            "learning_objectives": self.learning_objectives,
            "estimated_duration": self.estimated_duration,
            "created_at": self.created_at,
        }


@dataclass
class PlayerProgress:
    """Tracks a player's progress through a specific tutorial module."""
    progress_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    player_id: str = ""
    module_id: str = ""
    current_step: int = 0
    completed_steps: List[str] = field(default_factory=list)
    failed_steps: List[str] = field(default_factory=list)
    attempts: Dict[str, int] = field(default_factory=dict)
    time_spent: float = 0.0
    comprehension_score: float = 0.0
    needs_help: bool = False
    last_updated: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "progress_id": self.progress_id,
            "player_id": self.player_id,
            "module_id": self.module_id,
            "current_step": self.current_step,
            "completed_steps": self.completed_steps,
            "failed_steps": self.failed_steps,
            "attempts": self.attempts,
            "time_spent": self.time_spent,
            "comprehension_score": self.comprehension_score,
            "needs_help": self.needs_help,
            "last_updated": self.last_updated,
        }


# ---------------------------------------------------------------------------
# Step Template Banks
# ---------------------------------------------------------------------------

_TOPIC_INTROS: Dict[str, List[str]] = {
    "movement": [
        "Let's get you moving! Start with basic movement controls.",
        "Movement is the foundation of gameplay. Let's master it.",
        "Before anything else, you need to know how to navigate the world.",
    ],
    "combat": [
        "Combat is all about timing and positioning. Here are the basics.",
        "Ready to fight? Let's cover the fundamentals of combat.",
        "Understanding combat will keep you alive. Let's begin.",
    ],
    "inventory": [
        "Managing your items is key to survival. Let's explore your inventory.",
        "Your inventory is your lifeline. Here's how to use it.",
        "Items, equipment, resources — let's organize them all.",
    ],
    "crafting": [
        "Crafting turns raw materials into useful tools. Let's learn how.",
        "Create powerful items from basic components through crafting.",
        "The crafting system opens up endless possibilities. Let's start.",
    ],
    "dialogue": [
        "Conversations shape your story. Here's how dialogue works.",
        "Talking to NPCs can reveal secrets, quests, and lore.",
        "Every conversation can change your path. Let's see how.",
    ],
    "quests": [
        "Quests drive the story forward. Here's how to track and complete them.",
        "Your quest journal keeps track of everything. Let's review it.",
        "Accepting, tracking, and completing quests — all the essentials.",
    ],
    "skills": [
        "Skills define your character's abilities. Let's review your options.",
        "Invest in the right skills for your playstyle. Here's how.",
        "Your skill tree grows with you. Let's plan your build.",
    ],
    "map": [
        "Navigation is crucial. Let's learn to read the map.",
        "The map reveals everything about the world. Here's how to use it.",
        "Never get lost again. Master the map system.",
    ],
}

_ACTION_TEMPLATES: Dict[str, str] = {
    "observe": "Watch the highlighted area on screen.",
    "press": "Press the indicated key or button.",
    "hold": "Hold down the indicated key or button.",
    "click": "Click on the highlighted element.",
    "drag": "Drag the item to the target location.",
    "select": "Select the highlighted option from the menu.",
    "type": "Type the requested input in the text field.",
    "navigate": "Move your character to the marked destination.",
    "interact": "Interact with the highlighted object or NPC.",
    "confirm": "Confirm your selection to continue.",
}

_HELP_TEMPLATES: Dict[str, List[str]] = {
    "movement": [
        "Use W/A/S/D or arrow keys to move your character.",
        "Try holding Shift to sprint for faster movement.",
        "Press Space to jump over obstacles.",
    ],
    "combat": [
        "Left-click to perform a basic attack on your target.",
        "Right-click to block or parry incoming attacks.",
        "Use number keys 1-9 to activate abilities quickly.",
    ],
    "inventory": [
        "Press I or Tab to open your inventory panel.",
        "Right-click an item to use or equip it.",
        "Drag items between slots to reorganize your inventory.",
    ],
    "crafting": [
        "Check the recipe requirements on the right panel.",
        "Gather missing materials marked in red before crafting.",
        "Click the Craft button when all materials are ready.",
    ],
    "default": [
        "Take your time — there's no rush to complete this step.",
        "If you're stuck, try looking around for visual hints.",
        "Remember, you can always revisit this tutorial later.",
    ],
}

_STEP_TYPES_BY_SKILL: Dict[str, List[Dict[str, Any]]] = {
    "beginner": [
        {"title": "Getting Started", "action": "observe", "duration": 45.0, "optional": False},
        {"title": "Basic Controls", "action": "press", "duration": 30.0, "optional": False},
        {"title": "Try It Yourself", "action": "navigate", "duration": 60.0, "optional": False},
        {"title": "Understanding Feedback", "action": "observe", "duration": 25.0, "optional": True},
    ],
    "novice": [
        {"title": "Core Mechanics", "action": "interact", "duration": 40.0, "optional": False},
        {"title": "Practice Session", "action": "navigate", "duration": 60.0, "optional": False},
        {"title": "Common Patterns", "action": "select", "duration": 35.0, "optional": False},
        {"title": "Tips & Tricks", "action": "observe", "duration": 20.0, "optional": True},
    ],
    "intermediate": [
        {"title": "Advanced Techniques", "action": "hold", "duration": 45.0, "optional": False},
        {"title": "Efficiency Tips", "action": "select", "duration": 30.0, "optional": False},
        {"title": "Challenge Round", "action": "navigate", "duration": 75.0, "optional": False},
        {"title": "Deep Dive", "action": "observe", "duration": 40.0, "optional": True},
    ],
    "advanced": [
        {"title": "Expert Maneuvers", "action": "hold", "duration": 50.0, "optional": False},
        {"title": "Optimization Strategies", "action": "select", "duration": 35.0, "optional": False},
        {"title": "Speed Challenge", "action": "navigate", "duration": 60.0, "optional": False},
        {"title": "Hidden Mechanics", "action": "observe", "duration": 30.0, "optional": True},
    ],
    "expert": [
        {"title": "Mastery Check", "action": "navigate", "duration": 45.0, "optional": False},
        {"title": "Edge Cases", "action": "interact", "duration": 40.0, "optional": False},
        {"title": "Timed Execution", "action": "hold", "duration": 60.0, "optional": True},
    ],
    "master": [
        {"title": "Innovation Lab", "action": "interact", "duration": 30.0, "optional": False},
        {"title": "Teach Others", "action": "select", "duration": 45.0, "optional": True},
    ],
}

_STYLE_ADAPTATIONS: Dict[str, Dict[str, Any]] = {
    "visual": {
        "instruction_prefix": "[VISUAL] ",
        "action_preference": "observe",
        "duration_multiplier": 1.3,
    },
    "textual": {
        "instruction_prefix": "[READ] ",
        "action_preference": "select",
        "duration_multiplier": 1.5,
    },
    "kinesthetic": {
        "instruction_prefix": "[DO] ",
        "action_preference": "navigate",
        "duration_multiplier": 0.8,
    },
    "hybrid": {
        "instruction_prefix": "",
        "action_preference": "interact",
        "duration_multiplier": 1.1,
    },
    "adaptive": {
        "instruction_prefix": "",
        "action_preference": "interact",
        "duration_multiplier": 1.0,
    },
}


# ---------------------------------------------------------------------------
# TutorialDesignerEngine
# ---------------------------------------------------------------------------


class TutorialDesignerEngine:
    """
    AI-driven tutorial design system that generates adaptive tutorials,
    tracks player progress, and adjusts instruction based on demonstrated
    skill level and learning behavior.
    """

    _instance: Optional["TutorialDesignerEngine"] = None
    _lock = threading.RLock()
    _initialized: bool = False

    def __new__(cls) -> "TutorialDesignerEngine":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    instance = super().__new__(cls)
                    cls._instance = instance
        return cls._instance

    def __init__(self) -> None:
        if self._initialized:
            return
        self._modules: Dict[str, TutorialModule] = {}
        self._progress: Dict[str, PlayerProgress] = {}
        self._player_progress_index: Dict[str, Dict[str, str]] = {}
        self._total_modules_created: int = 0
        self._total_steps_created: int = 0
        self._total_tutorials_started: int = 0
        self._total_steps_completed: int = 0
        self._total_steps_failed: int = 0
        self._initialized = True

    @classmethod
    def get_instance(cls) -> "TutorialDesignerEngine":
        return cls()

    # ------------------------------------------------------------------
    # Module Creation
    # ------------------------------------------------------------------

    def create_module(
        self,
        title: str,
        topic: str,
        tutorial_type: str = "interactive",
        learning_style: str = "adaptive",
        skill_level: str = "beginner",
        description: str = "",
        learning_objectives: Optional[List[str]] = None,
    ) -> TutorialModule:
        """Create a new tutorial module with the given parameters."""
        try:
            tt = TutorialType(tutorial_type.lower())
        except ValueError:
            tt = TutorialType.INTERACTIVE

        try:
            ls = LearningStyle(learning_style.lower())
        except ValueError:
            ls = LearningStyle.ADAPTIVE

        try:
            sl = SkillLevel(skill_level.lower())
        except ValueError:
            sl = SkillLevel.BEGINNER

        module = TutorialModule(
            title=title,
            description=description,
            topic=topic,
            tutorial_type=tt,
            learning_style=ls,
            skill_level=sl,
            learning_objectives=learning_objectives or [],
        )

        with self._lock:
            self._modules[module.module_id] = module
            self._total_modules_created += 1

        return module

    def add_step(
        self,
        module_id: str,
        title: str,
        instruction: str,
        action_required: str = "",
        expected_input: str = "",
        help_text: str = "",
        completion_criteria: Optional[Dict[str, Any]] = None,
        is_optional: bool = False,
        order: int = -1,
        duration_estimate: float = 30.0,
    ) -> Optional[TutorialStep]:
        """Add an instructional step to an existing tutorial module."""
        module = self._modules.get(module_id)
        if module is None:
            return None

        if order < 0:
            order = len(module.steps) + 1

        step = TutorialStep(
            title=title,
            instruction=instruction,
            action_required=action_required,
            expected_input=expected_input,
            help_text=help_text,
            completion_criteria=completion_criteria or {},
            is_optional=is_optional,
            order=order,
            duration_estimate=duration_estimate,
        )

        with self._lock:
            module.steps.append(step)
            module.estimated_duration += step.duration_estimate
            self._total_steps_created += 1

        module.steps.sort(key=lambda s: s.order)
        return step

    # ------------------------------------------------------------------
    # Skill Assessment
    # ------------------------------------------------------------------

    def assess_player_skill(
        self,
        player_id: str,
        game_data: Dict[str, Any],
    ) -> SkillLevel:
        """
        Estimate a player's skill level from game data.

        Uses completion times, error rates, replay frequency, and
        past tutorial performance to compute a proficiency score.
        """
        if not game_data:
            return SkillLevel.BEGINNER

        # Compute a composite proficiency score from available signals
        signals: List[float] = []

        # Previous tutorial performance
        tutorial_history = game_data.get("tutorial_history", [])
        if tutorial_history:
            completion_rates = [
                h.get("comprehension_score", 0.0) for h in tutorial_history
                if isinstance(h, dict)
            ]
            if completion_rates:
                signals.append(sum(completion_rates) / len(completion_rates))

        # Task completion efficiency
        completion_times = game_data.get("task_completion_times", {})
        if completion_times:
            avg_time = sum(completion_times.values()) / len(completion_times)
            baseline = game_data.get("baseline_completion_time", avg_time)
            if baseline > 0:
                efficiency = min(1.0, baseline / max(avg_time, 0.01))
                signals.append(efficiency)

        # Error rate (lower is better skill)
        error_rate = game_data.get("error_rate", 0.5)
        if error_rate is not None:
            accuracy = 1.0 - min(1.0, error_rate)
            signals.append(accuracy)

        # Known skill level from previous assessments
        known_tier = game_data.get("known_skill_tier")
        if known_tier is not None and 0 <= known_tier <= 5:
            signals.append(known_tier / 5.0)

        # Self-reported experience
        experience_level = game_data.get("experience_level")
        experience_map = {
            "none": 0.0,
            "beginner": 0.1,
            "some": 0.35,
            "intermediate": 0.6,
            "experienced": 0.8,
            "expert": 0.95,
        }
        if experience_level and experience_level in experience_map:
            signals.append(experience_map[experience_level])

        # Gameplay statistics
        play_stats = game_data.get("play_stats", {})
        playtime = play_stats.get("total_playtime_minutes", 0)
        playtime_score = min(1.0, playtime / 600.0)
        signals.append(playtime_score)

        if not signals:
            return SkillLevel.BEGINNER

        # Weight later signals higher for recency bias
        weighted_sum = 0.0
        total_weight = 0.0
        for i, sig in enumerate(signals):
            weight = 0.5 + (0.5 * (i + 1) / len(signals))
            weighted_sum += sig * weight
            total_weight += weight

        proficiency = weighted_sum / total_weight if total_weight > 0 else 0.0
        return SkillLevel.from_score(proficiency)

    # ------------------------------------------------------------------
    # Tutorial Recommendation
    # ------------------------------------------------------------------

    def recommend_tutorials(
        self,
        player_id: str,
        skill_level: Optional[SkillLevel] = None,
        topic: str = "",
    ) -> List[TutorialModule]:
        """
        Recommend tutorials for a player based on skill level and topic.

        Filters modules that match the player's current skill and ranks
        them by relevance. Skips tutorials the player has already completed
        with high comprehension.
        """
        recommendations: List[Tuple[TutorialModule, float]] = []

        player_progress_map = self._player_progress_index.get(player_id, {})

        for module in self._modules.values():
            # Filter by topic if specified
            if topic and module.topic != topic:
                continue

            # Filter by skill level if provided
            if skill_level is not None:
                level_diff = abs(module.skill_level.tier - skill_level.tier)
                if level_diff > 2:
                    continue

            # Skip already mastered modules
            progress_id = player_progress_map.get(module.module_id)
            if progress_id:
                progress = self._progress.get(progress_id)
                if progress and progress.comprehension_score >= 0.85:
                    continue

            # Score relevance
            relevance = 0.0
            if skill_level is not None:
                level_diff = abs(module.skill_level.tier - skill_level.tier)
                relevance += max(0.0, 1.0 - level_diff * 0.3)
            else:
                relevance += 0.5

            if progress_id:
                progress = self._progress.get(progress_id)
                if progress and progress.current_step > 0:
                    relevance += 0.3

            if topic and module.topic == topic:
                relevance += 0.5

            recommendations.append((module, relevance))

        recommendations.sort(key=lambda x: x[1], reverse=True)
        return [r[0] for r in recommendations]

    # ------------------------------------------------------------------
    # Adaptive Tutorial Generation
    # ------------------------------------------------------------------

    def generate_adaptive_tutorial(
        self,
        player_id: str,
        topic: str,
        game_context: Dict[str, Any],
    ) -> TutorialModule:
        """
        Generate a personalized tutorial module tailored to a specific player.

        This method:
        - Assesses player skill level from game data
        - Determines the appropriate learning style
        - Creates steps matched to the player's demonstrated abilities
        - Skips steps the player has already shown mastery of
        - Adds extra help steps for areas where the player struggles
        """
        # Step 1: Assess skill level
        skill_level = self.assess_player_skill(player_id, game_context)

        # Step 2: Determine learning style
        behavior_data = game_context.get("behavior_data", {})
        learning_style = self._detect_learning_style(game_context)

        # Step 3: Determine tutorial type
        tutorial_type = self._select_tutorial_type(skill_level, game_context)

        # Step 4: Identify known and weak areas
        known_topics = game_context.get("mastered_topics", [])
        weak_areas = game_context.get("weak_areas", [])
        tutorial_history = game_context.get("tutorial_history", [])

        # Build a description based on the player's profile
        description = self._build_description(topic, skill_level, learning_style)

        # Build learning objectives
        learning_objectives = self._build_objectives(topic, skill_level, weak_areas)

        # Step 5: Create the module
        module = self.create_module(
            title=self._generate_title(topic, skill_level),
            topic=topic,
            tutorial_type=tutorial_type.value,
            learning_style=learning_style.value,
            skill_level=skill_level.value,
            description=description,
            learning_objectives=learning_objectives,
        )

        # Step 6: Generate steps based on skill level
        skill_key = skill_level.value
        step_templates = _STEP_TYPES_BY_SKILL.get(skill_key, _STEP_TYPES_BY_SKILL["beginner"])

        style_adaptation = _STYLE_ADAPTATIONS.get(
            learning_style.value, _STYLE_ADAPTATIONS["adaptive"]
        )
        action_preference = style_adaptation["action_preference"]
        duration_multiplier = style_adaptation["duration_multiplier"]
        instruction_prefix = style_adaptation["instruction_prefix"]

        topic_intros = _TOPIC_INTROS.get(topic, [
            f"Welcome to the {topic} tutorial. Let's get started.",
            f"This tutorial will teach you the fundamentals of {topic}.",
        ])

        help_templates = _HELP_TEMPLATES.get(topic, _HELP_TEMPLATES["default"])

        step_order = 0

        # Generate core steps
        for template in step_templates:
            step_order += 1
            step_title = template["title"]
            action_key = template["action"]
            is_optional = template["optional"]

            # Skip steps for known topics
            if is_optional and topic in known_topics:
                continue

            # Use the player's preferred action type when appropriate
            if action_key == "observe" and action_preference != "observe":
                action_key = action_preference

            action_instruction = _ACTION_TEMPLATES.get(action_key, _ACTION_TEMPLATES["interact"])

            # Build instruction
            intro_line = random.choice(topic_intros) if step_order == 1 else ""
            instruction = f"{instruction_prefix}{intro_line} {action_instruction}".strip()

            # Add extra help for weak areas
            help_text = ""
            if topic in weak_areas:
                extra_help = random.choice(help_templates)
                context_help = game_context.get("struggle_context", "")
                if context_help:
                    help_text = f"{extra_help} Hint: {context_help}"
                else:
                    help_text = extra_help
            else:
                if random.random() < 0.4:
                    help_text = random.choice(help_templates)

            duration = template["duration"] * duration_multiplier

            completion_criteria: Dict[str, Any] = {
                "action_completed": True,
                "time_limit": duration * 2.0,
            }
            if topic in weak_areas:
                completion_criteria["retry_allowed"] = True
                completion_criteria["max_retries"] = 5

            self.add_step(
                module_id=module.module_id,
                title=step_title,
                instruction=instruction,
                action_required=action_key,
                expected_input=action_key,
                help_text=help_text,
                completion_criteria=completion_criteria,
                is_optional=is_optional,
                order=step_order,
                duration_estimate=duration,
            )

        # Add struggle-support steps for weak areas
        if topic in weak_areas:
            step_order += 1
            struggle_help = (
                f"We noticed you might need extra practice with {topic}. "
                f"Let's go through it together."
            )
            self.add_step(
                module_id=module.module_id,
                title="Extra Practice",
                instruction=f"{instruction_prefix}{struggle_help}",
                action_required="navigate",
                expected_input="navigate",
                help_text=(
                    f"Don't worry — everyone learns at their own pace. "
                    f"Focus on one thing at a time."
                ),
                completion_criteria={
                    "action_completed": True,
                    "retry_allowed": True,
                    "max_retries": 10,
                },
                is_optional=False,
                order=step_order,
                duration_estimate=90.0 * duration_multiplier,
            )

        # Add a summary/recap step
        step_order += 1
        summary_text = (
            f"Great job! You've completed the {topic} tutorial. "
            f"Practice these skills in the game to solidify your learning."
        )
        self.add_step(
            module_id=module.module_id,
            title="Summary",
            instruction=f"{instruction_prefix}{summary_text}",
            action_required="confirm",
            expected_input="confirm",
            help_text="You can replay this tutorial anytime from the help menu.",
            completion_criteria={"confirmed": True},
            is_optional=False,
            order=step_order,
            duration_estimate=15.0,
        )

        return module

    def _detect_learning_style(self, game_context: Dict[str, Any]) -> LearningStyle:
        """Infer the player's preferred learning style from behavior data."""
        style_preference = game_context.get("learning_style")
        if style_preference:
            try:
                return LearningStyle(style_preference.lower())
            except ValueError:
                pass

        behavior = game_context.get("behavior_data", {})

        # Count actions by type as signals of style preference
        visual_signals = behavior.get("camera_zoom_events", 0) + behavior.get("ui_hover_time", 0)
        textual_signals = behavior.get("lore_read_count", 0) + behavior.get("menu_read_time", 0)
        action_signals = behavior.get("button_mash_count", 0) + behavior.get("retry_count", 0)

        total = visual_signals + textual_signals + action_signals

        if total == 0:
            return LearningStyle.ADAPTIVE

        visual_ratio = visual_signals / total
        textual_ratio = textual_signals / total
        action_ratio = action_signals / total

        if visual_ratio > 0.5:
            return LearningStyle.VISUAL
        if textual_ratio > 0.5:
            return LearningStyle.TEXTUAL
        if action_ratio > 0.5:
            return LearningStyle.KINESTHETIC

        return LearningStyle.HYBRID

    def _select_tutorial_type(
        self,
        skill_level: SkillLevel,
        game_context: Dict[str, Any],
    ) -> TutorialType:
        """Choose the most appropriate tutorial type for the player."""
        forced_type = game_context.get("preferred_tutorial_type")
        if forced_type:
            try:
                return TutorialType(forced_type.lower())
            except ValueError:
                pass

        if skill_level in (SkillLevel.BEGINNER, SkillLevel.NOVICE):
            return TutorialType.ONBOARDING
        if skill_level == SkillLevel.INTERMEDIATE:
            return TutorialType.WALKTHROUGH
        if skill_level == SkillLevel.ADVANCED:
            return TutorialType.INTERACTIVE
        if skill_level == SkillLevel.EXPERT:
            return TutorialType.CHALLENGE
        return TutorialType.SANDBOX

    def _generate_title(self, topic: str, skill_level: SkillLevel) -> str:
        """Generate a descriptive title for the tutorial."""
        prefix_map = {
            SkillLevel.BEGINNER: "Introduction to",
            SkillLevel.NOVICE: "Basics of",
            SkillLevel.INTERMEDIATE: "Understanding",
            SkillLevel.ADVANCED: "Mastering",
            SkillLevel.EXPERT: "Perfecting",
            SkillLevel.MASTER: "Innovating with",
        }
        prefix = prefix_map.get(skill_level, "Learning")
        return f"{prefix} {topic.title()}"

    def _build_description(
        self,
        topic: str,
        skill_level: SkillLevel,
        learning_style: LearningStyle,
    ) -> str:
        """Build a personalized tutorial description."""
        style_desc = {
            LearningStyle.VISUAL: "with visual demonstrations",
            LearningStyle.TEXTUAL: "with detailed text instructions",
            LearningStyle.KINESTHETIC: "through hands-on practice",
            LearningStyle.HYBRID: "using mixed instruction methods",
            LearningStyle.ADAPTIVE: "adapted to your learning pace",
        }
        return (
            f"A {skill_level.value}-level tutorial covering {topic} "
            f"{style_desc.get(learning_style, '')}."
        ).strip()

    def _build_objectives(
        self,
        topic: str,
        skill_level: SkillLevel,
        weak_areas: List[str],
    ) -> List[str]:
        """Build a list of learning objectives for the tutorial."""
        objectives = [
            f"Understand core {topic} mechanics",
            f"Apply {topic} skills in practice scenarios",
        ]

        if skill_level.tier >= 2:
            objectives.append(f"Identify common {topic} patterns and shortcuts")
        if skill_level.tier >= 3:
            objectives.append(f"Optimize {topic} execution for efficiency")
        if topic in weak_areas:
            objectives.append(f"Build confidence with {topic} through guided practice")

        return objectives

    # ------------------------------------------------------------------
    # Tutorial Session Management
    # ------------------------------------------------------------------

    def start_tutorial(
        self,
        player_id: str,
        module_id: str,
    ) -> Optional[PlayerProgress]:
        """Begin tracking a player's progress through a tutorial module."""
        module = self._modules.get(module_id)
        if module is None:
            return None

        # Check if progress already exists
        existing_progress = self.get_player_progress(player_id, module_id)
        if existing_progress:
            existing_progress.last_updated = time.time()
            return existing_progress

        progress = PlayerProgress(
            player_id=player_id,
            module_id=module_id,
        )

        with self._lock:
            self._progress[progress.progress_id] = progress
            if player_id not in self._player_progress_index:
                self._player_progress_index[player_id] = {}
            self._player_progress_index[player_id][module_id] = progress.progress_id
            self._total_tutorials_started += 1

        return progress

    def complete_step(
        self,
        progress_id: str,
        step_id: str,
        success: bool,
        time_spent: float = 0.0,
    ) -> Optional[PlayerProgress]:
        """Record the completion (success or failure) of a tutorial step."""
        progress = self._progress.get(progress_id)
        if progress is None:
            return None

        module = self._modules.get(progress.module_id)
        if module is None:
            return None

        # Find the step
        step_index = -1
        for i, step in enumerate(module.steps):
            if step.step_id == step_id:
                step_index = i
                break

        if step_index < 0:
            return None

        current_attempts = progress.attempts.get(step_id, 0) + 1

        with self._lock:
            progress.time_spent += time_spent
            progress.attempts[step_id] = current_attempts
            progress.last_updated = time.time()

            if success:
                if step_id not in progress.completed_steps:
                    progress.completed_steps.append(step_id)
                    self._total_steps_completed += 1
                if step_id in progress.failed_steps:
                    progress.failed_steps.remove(step_id)

                # Advance to next non-optional step
                next_step = step_index + 1
                while next_step < len(module.steps):
                    if not module.steps[next_step].is_optional:
                        break
                    if module.steps[next_step].step_id not in progress.completed_steps:
                        progress.completed_steps.append(module.steps[next_step].step_id)
                    next_step += 1
                progress.current_step = min(next_step, len(module.steps))

            else:
                if step_id not in progress.failed_steps:
                    progress.failed_steps.append(step_id)
                    self._total_steps_failed += 1
                if current_attempts >= 3:
                    progress.needs_help = True

            # Recompute comprehension score
            total_steps = len(module.steps)
            if total_steps > 0:
                required_steps = sum(1 for s in module.steps if not s.is_optional)
                completed_required = sum(
                    1 for sid in progress.completed_steps
                    for s in module.steps
                    if s.step_id == sid and not s.is_optional
                )
                if required_steps > 0:
                    progress.comprehension_score = completed_required / required_steps

        return progress

    def skip_step(
        self,
        progress_id: str,
        step_id: str,
    ) -> Optional[PlayerProgress]:
        """Skip a tutorial step, marking it as optional-complete."""
        progress = self._progress.get(progress_id)
        if progress is None:
            return None

        module = self._modules.get(progress.module_id)
        if module is None:
            return None

        step_found = any(s.step_id == step_id for s in module.steps)
        if not step_found:
            return None

        with self._lock:
            if step_id not in progress.completed_steps:
                progress.completed_steps.append(step_id)
            if step_id in progress.failed_steps:
                progress.failed_steps.remove(step_id)
            progress.last_updated = time.time()

            # Advance current step
            step_index = -1
            for i, step in enumerate(module.steps):
                if step.step_id == step_id:
                    step_index = i
                    break

            if step_index >= 0:
                next_step = step_index + 1
                while next_step < len(module.steps):
                    if not module.steps[next_step].is_optional:
                        break
                    next_step += 1
                progress.current_step = min(next_step, len(module.steps))

            # Recompute comprehension
            total_steps = len(module.steps)
            if total_steps > 0:
                required_steps = sum(1 for s in module.steps if not s.is_optional)
                completed_required = sum(
                    1 for sid in progress.completed_steps
                    for s in module.steps
                    if s.step_id == sid and not s.is_optional
                )
                if required_steps > 0:
                    progress.comprehension_score = completed_required / required_steps

        return progress

    def get_player_progress(
        self,
        player_id: str,
        module_id: str,
    ) -> Optional[PlayerProgress]:
        """Retrieve a player's progress for a specific module."""
        index = self._player_progress_index.get(player_id, {})
        progress_id = index.get(module_id)
        if progress_id:
            return self._progress.get(progress_id)
        return None

    def get_module(self, module_id: str) -> Optional[TutorialModule]:
        """Retrieve a tutorial module by its identifier."""
        return self._modules.get(module_id)

    def list_modules(
        self,
        topic: str = "",
        skill_level: Optional[str] = None,
        tutorial_type: Optional[str] = None,
    ) -> List[TutorialModule]:
        """List all tutorial modules, optionally filtered."""
        results: List[TutorialModule] = []
        for module in self._modules.values():
            if topic and module.topic != topic:
                continue
            if skill_level:
                try:
                    sl = SkillLevel(skill_level.lower())
                    if module.skill_level != sl:
                        continue
                except ValueError:
                    pass
            if tutorial_type:
                try:
                    tt = TutorialType(tutorial_type.lower())
                    if module.tutorial_type != tt:
                        continue
                except ValueError:
                    pass
            results.append(module)
        return results

    # ------------------------------------------------------------------
    # Statistics
    # ------------------------------------------------------------------

    def get_stats(self) -> Dict[str, Any]:
        """Return engine usage statistics."""
        topic_distribution: Dict[str, int] = {}
        style_distribution: Dict[str, int] = {}
        level_distribution: Dict[str, int] = {}
        type_distribution: Dict[str, int] = {}

        for module in self._modules.values():
            t = module.topic
            topic_distribution[t] = topic_distribution.get(t, 0) + 1

            s = module.learning_style.value
            style_distribution[s] = style_distribution.get(s, 0) + 1

            lv = module.skill_level.value
            level_distribution[lv] = level_distribution.get(lv, 0) + 1

            tt = module.tutorial_type.value
            type_distribution[tt] = type_distribution.get(tt, 0) + 1

        active_progress = len(self._progress)
        players_with_progress = len(self._player_progress_index)

        return {
            "total_modules": len(self._modules),
            "total_modules_created": self._total_modules_created,
            "total_steps_created": self._total_steps_created,
            "total_tutorials_started": self._total_tutorials_started,
            "total_steps_completed": self._total_steps_completed,
            "total_steps_failed": self._total_steps_failed,
            "active_progress_records": active_progress,
            "players_with_progress": players_with_progress,
            "topic_distribution": topic_distribution,
            "style_distribution": style_distribution,
            "level_distribution": level_distribution,
            "type_distribution": type_distribution,
        }


# ---------------------------------------------------------------------------
# Module-level Accessor
# ---------------------------------------------------------------------------


def get_tutorial_designer() -> TutorialDesignerEngine:
    """Get the singleton TutorialDesignerEngine instance."""
    return TutorialDesignerEngine.get_instance()