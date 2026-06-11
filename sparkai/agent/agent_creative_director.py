"""
SparkLabs Agent - Creative Director

An AI-driven game design orchestrator that generates and manages game
content ideas, level designs, character concepts, and gameplay mechanics.
Acts as a creative assistant that helps game designers brainstorm and
prototype across all design disciplines.

Core capabilities:
  - Design project management with genre and platform targeting
  - Idea generation with categorization by design discipline
  - Iterative idea refinement with version tracking
  - Creative prompt generation for brainstorming sessions
  - Feedback collection and aggregation per idea
  - Design element template library for reusable patterns
  - Mechanic combination exploration
  - Design document export for structured output

Architecture:
  AgentCreativeDirector (Singleton)
    |-- DesignIdea (dataclass)
    |-- DesignProject (dataclass)
    |-- DesignElementTemplate (dataclass)
    |-- DesignSession (dataclass)
    |-- DesignFeedback (dataclass)
    |-- DesignInspiration (dataclass)
    |-- create_project()
    |-- create_idea()
    |-- iterate_idea()
    |-- generate_prompts()
    |-- export_design_doc()
"""

from __future__ import annotations

import random
import threading
import time as _time_module
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class DesignCategory(Enum):
    LEVEL_DESIGN = "level-design"
    CHARACTER = "character"
    MECHANIC = "mechanic"
    NARRATIVE = "narrative"
    ENVIRONMENT = "environment"
    PUZZLE = "puzzle"
    COMBAT = "combat"
    ECONOMY = "economy"
    UI_UX = "ui-ux"
    AUDIO_VISUAL = "audio-visual"


class DesignComplexity(Enum):
    SIMPLE = "simple"
    MODERATE = "moderate"
    COMPLEX = "complex"
    EPIC = "epic"


class DesignStatus(Enum):
    DRAFT = "draft"
    REVIEW = "review"
    APPROVED = "approved"
    PROTOTYPED = "prototyped"
    ITERATED = "iterated"
    FINAL = "final"


class TargetAudience(Enum):
    CASUAL = "casual"
    CORE = "core"
    HARDCORE = "hardcore"
    EDUCATIONAL = "educational"
    KIDS = "kids"
    ALL_AGES = "all-ages"


class DesignElement(Enum):
    RULE = "rule"
    CONSTRAINT = "constraint"
    REWARD = "reward"
    CHALLENGE = "challenge"
    MECHANIC_ATOM = "mechanic-atom"
    AESTHETIC = "aesthetic"
    STORY_BEAT = "story-beat"


# ---------------------------------------------------------------------------
# Data Classes
# ---------------------------------------------------------------------------

@dataclass
class DesignIdea:
    idea_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    title: str = ""
    category: DesignCategory = DesignCategory.MECHANIC
    description: str = ""
    mechanics: List[str] = field(default_factory=list)
    visual_reference: str = ""
    complexity: DesignComplexity = DesignComplexity.MODERATE
    target_audience: TargetAudience = TargetAudience.CORE
    status: DesignStatus = DesignStatus.DRAFT
    tags: List[str] = field(default_factory=list)
    created_at: float = field(default_factory=_time_module.time)
    version: int = 1
    parent_idea_id: str = ""
    iteration_notes: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "idea_id": self.idea_id,
            "title": self.title,
            "category": self.category.value,
            "description": self.description,
            "mechanics": list(self.mechanics),
            "visual_reference": self.visual_reference,
            "complexity": self.complexity.value,
            "target_audience": self.target_audience.value,
            "status": self.status.value,
            "tags": list(self.tags),
            "created_at": self.created_at,
            "version": self.version,
            "parent_idea_id": self.parent_idea_id,
            "iteration_notes": list(self.iteration_notes),
        }


@dataclass
class DesignProject:
    project_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    name: str = ""
    description: str = ""
    genre: str = "platformer"
    platform: str = "web"
    ideas: Dict[str, DesignIdea] = field(default_factory=dict)
    current_phase: str = "ideation"
    created_at: float = field(default_factory=_time_module.time)
    modified_at: float = field(default_factory=_time_module.time)
    settings: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "project_id": self.project_id,
            "name": self.name,
            "description": self.description,
            "genre": self.genre,
            "platform": self.platform,
            "ideas_count": len(self.ideas),
            "current_phase": self.current_phase,
            "created_at": self.created_at,
            "modified_at": self.modified_at,
            "settings": dict(self.settings),
        }


@dataclass
class DesignElementTemplate:
    template_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    element_type: DesignElement = DesignElement.RULE
    name: str = ""
    description: str = ""
    parameters: Dict[str, Any] = field(default_factory=dict)
    constraints: Dict[str, Any] = field(default_factory=dict)
    examples: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "template_id": self.template_id,
            "element_type": self.element_type.value,
            "name": self.name,
            "description": self.description,
            "parameters": dict(self.parameters),
            "constraints": dict(self.constraints),
            "examples": list(self.examples),
        }


@dataclass
class DesignSession:
    session_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    project_id: str = ""
    focus_area: DesignCategory = DesignCategory.MECHANIC
    prompts_generated: int = 0
    ideas_created: int = 0
    started_at: float = field(default_factory=_time_module.time)
    ended_at: Optional[float] = None
    session_notes: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "session_id": self.session_id,
            "project_id": self.project_id,
            "focus_area": self.focus_area.value,
            "prompts_generated": self.prompts_generated,
            "ideas_created": self.ideas_created,
            "started_at": self.started_at,
            "ended_at": self.ended_at,
            "session_notes": list(self.session_notes),
        }


@dataclass
class DesignFeedback:
    feedback_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    idea_id: str = ""
    rating: int = 3
    strengths: List[str] = field(default_factory=list)
    weaknesses: List[str] = field(default_factory=list)
    suggestions: List[str] = field(default_factory=list)
    reviewer_role: str = "designer"
    created_at: float = field(default_factory=_time_module.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "feedback_id": self.feedback_id,
            "idea_id": self.idea_id,
            "rating": self.rating,
            "strengths": list(self.strengths),
            "weaknesses": list(self.weaknesses),
            "suggestions": list(self.suggestions),
            "reviewer_role": self.reviewer_role,
            "created_at": self.created_at,
        }


@dataclass
class DesignInspiration:
    inspiration_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    source: str = ""
    content: str = ""
    category: DesignCategory = DesignCategory.MECHANIC
    relevance_tags: List[str] = field(default_factory=list)
    used_in_idea_ids: List[str] = field(default_factory=list)
    created_at: float = field(default_factory=_time_module.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "inspiration_id": self.inspiration_id,
            "source": self.source,
            "content": self.content,
            "category": self.category.value,
            "relevance_tags": list(self.relevance_tags),
            "used_in_idea_ids": list(self.used_in_idea_ids),
            "created_at": self.created_at,
        }


# ---------------------------------------------------------------------------
# Prompt Templates
# ---------------------------------------------------------------------------

_PROMPT_TEMPLATES: Dict[str, List[str]] = {
    "level-design": [
        "Design a {genre} level that introduces {complexity} platforming challenges with escalating difficulty",
        "Create a {genre} environment that tells a story through its spatial layout and visual landmarks",
        "Sketch a {genre} secret area that rewards exploration with a unique gameplay twist",
    ],
    "character": [
        "Design a {genre} character whose abilities reflect their personal backstory and growth arc",
        "Create a {genre} antagonist whose motivation is morally ambiguous and relatable",
        "Sketch a {genre} companion NPC that provides both narrative depth and gameplay utility",
    ],
    "mechanic": [
        "Design a core {genre} mechanic that creates emergent gameplay through simple rule interactions",
        "Create a {genre} resource system that forces meaningful trade-off decisions under pressure",
        "Sketch a {genre} movement ability that transforms how players navigate the world",
    ],
    "narrative": [
        "Design a {genre} story branch where the player's inaction shapes the outcome as much as action",
        "Create a {genre} world-building detail that reveals itself gradually through environmental clues",
        "Sketch a {genre} dialogue system that reflects character relationships through word choice and tone",
    ],
    "environment": [
        "Design a {genre} biome that visually communicates its ecological history and current state",
        "Create a {genre} transition zone between two distinct areas that builds anticipation",
        "Sketch a {genre} weather system that affects both visual mood and gameplay mechanics",
    ],
    "puzzle": [
        "Design a {genre} puzzle that teaches its mechanics through progressive discovery rather than tutorials",
        "Create a {genre} multi-stage puzzle where each solution recontextualizes previous steps",
        "Sketch a {genre} environmental puzzle that uses spatial audio cues as hints",
    ],
    "combat": [
        "Design a {genre} enemy type that forces players to use a specific mechanic they recently learned",
        "Create a {genre} boss encounter with distinct phases that change the arena dynamically",
        "Sketch a {genre} combat rhythm that alternates between offensive windows and defensive repositioning",
    ],
    "economy": [
        "Design a {genre} currency loop where spending creates future earning opportunities",
        "Create a {genre} crafting system where material rarity drives exploration incentives",
        "Sketch a {genre} trade mechanic that fluctuates based on in-game events and player actions",
    ],
    "ui-ux": [
        "Design a {genre} HUD that communicates critical information through diegetic world elements",
        "Create a {genre} menu flow that minimizes cognitive load during high-intensity moments",
        "Sketch a {genre} feedback system that uses animation and sound to confirm player actions",
    ],
    "audio-visual": [
        "Design a {genre} audio landscape where the soundtrack dynamically responds to player pace",
        "Create a {genre} visual theme that uses color progression to signal narrative chapter changes",
        "Sketch a {genre} particle system that provides gameplay feedback through visual density and hue",
    ],
}

_TITLE_PREFIXES: Dict[str, List[str]] = {
    "level-design": ["The", "Hidden", "Forgotten", "Ascending", "Twisted"],
    "character": ["Shadow of", "Keeper of", "The Last", "Echo of", "Child of"],
    "mechanic": ["Flow of", "Rhythm of", "Gravity", "Momentum", "Chain"],
    "narrative": ["Tale of", "Legend of", "Whispers of", "Chronicle of", "Echoes of"],
    "environment": ["Realm of", "Expanse of", "Depths of", "Peaks of", "Vale of"],
    "puzzle": ["Riddle of", "Enigma of", "Labyrinth of", "Cipher of", "Mystery of"],
    "combat": ["Clash of", "Fury of", "Duel of", "Onslaught of", "Storm of"],
    "economy": ["Trade of", "Fortune of", "Bounty of", "Exchange of", "Guild of"],
    "ui-ux": ["Interface of", "Window to", "Portal of", "Lens of", "Display of"],
    "audio-visual": ["Symphony of", "Spectrum of", "Resonance of", "Hue of", "Cadence of"],
}

_TITLE_SUFFIXES: List[str] = [
    "the Ancients", "the Void", "Shadows", "Dreams", "the Colossus",
    "Time", "the Depths", "Storms", "Embers", "Horizons",
]


# ---------------------------------------------------------------------------
# Singleton Agent
# ---------------------------------------------------------------------------

class AgentCreativeDirector:
    """
    AI-driven game design orchestrator that generates and manages game
    content ideas, level designs, character concepts, and gameplay mechanics.

    Provides a structured creative workflow: create projects, generate ideas
    across design categories, run brainstorming sessions with prompt generation,
    collect feedback, iterate on ideas with version tracking, and export
    structured design documents.

    Usage:
        director = get_creative_director()
        project = director.create_project("Space Explorer", genre="platformer")
        idea = director.create_idea(project.project_id, "Double Jump",
            DesignCategory.MECHANIC, "A mid-air second jump ability")
        session = director.create_session(project.project_id, DesignCategory.MECHANIC)
        prompts = director.generate_prompts(project.project_id, session.session_id,
            DesignCategory.MECHANIC, count=3)
    """

    _instance: Optional["AgentCreativeDirector"] = None
    _lock: threading.RLock = threading.RLock()

    def __new__(cls) -> "AgentCreativeDirector":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    instance = super().__new__(cls)
                    instance._initialized = False
                    cls._instance = instance
        return cls._instance

    @classmethod
    def get_instance(cls) -> "AgentCreativeDirector":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
                    cls._instance._initialize()
        return cls._instance

    def _initialize(self) -> None:
        if self._initialized:
            return
        self._initialized = True
        self._projects: Dict[str, DesignProject] = {}
        self._feedback: Dict[str, List[DesignFeedback]] = {}
        self._sessions: Dict[str, DesignSession] = {}
        self._inspirations: Dict[str, DesignInspiration] = {}
        self._templates: Dict[str, DesignElementTemplate] = {}
        self._total_ideas_created: int = 0
        self._total_sessions_run: int = 0

    # ------------------------------------------------------------------
    # Project Management
    # ------------------------------------------------------------------

    def create_project(
        self,
        name: str,
        description: str = "",
        genre: str = "platformer",
        platform: str = "web",
    ) -> DesignProject:
        project = DesignProject(
            name=name,
            description=description,
            genre=genre,
            platform=platform,
        )
        self._projects[project.project_id] = project
        return project

    # ------------------------------------------------------------------
    # Idea Management
    # ------------------------------------------------------------------

    def create_idea(
        self,
        project_id: str,
        title: str,
        category: DesignCategory,
        description: str,
        mechanics: Optional[List[str]] = None,
        complexity: DesignComplexity = DesignComplexity.MODERATE,
        target_audience: TargetAudience = TargetAudience.CORE,
        tags: Optional[List[str]] = None,
        parent_idea_id: str = "",
    ) -> Optional[DesignIdea]:
        project = self._projects.get(project_id)
        if project is None:
            return None

        idea = DesignIdea(
            title=title,
            category=category,
            description=description,
            mechanics=mechanics if mechanics is not None else [],
            complexity=complexity,
            target_audience=target_audience,
            tags=tags if tags is not None else [],
            parent_idea_id=parent_idea_id,
        )

        project.ideas[idea.idea_id] = idea
        project.modified_at = _time_module.time()
        self._total_ideas_created += 1
        return idea

    def iterate_idea(
        self,
        project_id: str,
        idea_id: str,
        iteration_notes: List[str],
    ) -> Optional[DesignIdea]:
        project = self._projects.get(project_id)
        if project is None:
            return None

        original = project.ideas.get(idea_id)
        if original is None:
            return None

        new_idea = DesignIdea(
            title=original.title,
            category=original.category,
            description=original.description,
            mechanics=list(original.mechanics),
            visual_reference=original.visual_reference,
            complexity=original.complexity,
            target_audience=original.target_audience,
            status=DesignStatus.ITERATED,
            tags=list(original.tags),
            version=original.version + 1,
            parent_idea_id=idea_id,
            iteration_notes=list(iteration_notes),
        )

        project.ideas[new_idea.idea_id] = new_idea
        project.modified_at = _time_module.time()
        self._total_ideas_created += 1
        return new_idea

    def approve_idea(self, project_id: str, idea_id: str) -> bool:
        project = self._projects.get(project_id)
        if project is None:
            return False
        idea = project.ideas.get(idea_id)
        if idea is None:
            return False
        idea.status = DesignStatus.APPROVED
        project.modified_at = _time_module.time()
        return True

    def prototype_idea(self, project_id: str, idea_id: str) -> bool:
        project = self._projects.get(project_id)
        if project is None:
            return False
        idea = project.ideas.get(idea_id)
        if idea is None:
            return False
        idea.status = DesignStatus.PROTOTYPED
        project.modified_at = _time_module.time()
        return True

    # ------------------------------------------------------------------
    # Feedback
    # ------------------------------------------------------------------

    def add_feedback(
        self,
        idea_id: str,
        rating: int,
        strengths: List[str],
        weaknesses: List[str],
        suggestions: List[str],
        reviewer_role: str = "designer",
    ) -> DesignFeedback:
        clamped_rating = max(1, min(5, rating))
        feedback = DesignFeedback(
            idea_id=idea_id,
            rating=clamped_rating,
            strengths=list(strengths),
            weaknesses=list(weaknesses),
            suggestions=list(suggestions),
            reviewer_role=reviewer_role,
        )
        if idea_id not in self._feedback:
            self._feedback[idea_id] = []
        self._feedback[idea_id].append(feedback)
        return feedback

    def get_idea_feedback(self, idea_id: str) -> List[DesignFeedback]:
        return list(self._feedback.get(idea_id, []))

    # ------------------------------------------------------------------
    # Session Management
    # ------------------------------------------------------------------

    def create_session(
        self,
        project_id: str,
        focus_area: DesignCategory = DesignCategory.MECHANIC,
    ) -> DesignSession:
        session = DesignSession(
            project_id=project_id,
            focus_area=focus_area,
        )
        self._sessions[session.session_id] = session
        self._total_sessions_run += 1
        return session

    def end_session(self, session_id: str) -> bool:
        session = self._sessions.get(session_id)
        if session is None:
            return False
        session.ended_at = _time_module.time()
        return True

    # ------------------------------------------------------------------
    # Prompt Generation
    # ------------------------------------------------------------------

    def generate_prompts(
        self,
        project_id: str,
        session_id: str,
        category: DesignCategory,
        count: int = 3,
    ) -> List[str]:
        project = self._projects.get(project_id)
        session = self._sessions.get(session_id)

        category_key = category.value
        templates = _PROMPT_TEMPLATES.get(category_key, _PROMPT_TEMPLATES["mechanic"])
        genre = project.genre if project else "platformer"

        complexity_options = ["simple", "moderate", "complex", "epic"]

        prompts: List[str] = []
        for i in range(count):
            template = templates[i % len(templates)]
            chosen_complexity = complexity_options[i % len(complexity_options)]
            prompt = template.format(genre=genre, complexity=chosen_complexity)
            prompts.append(prompt)

        if session:
            session.prompts_generated += len(prompts)

        return prompts

    def generate_idea_from_prompt(
        self,
        project_id: str,
        category: DesignCategory,
        prompt: str,
    ) -> DesignIdea:
        project = self._projects.get(project_id)

        title = self._generate_title(category, project.genre if project else "platformer")
        mechanics = self._extract_mechanics_from_prompt(prompt)

        idea = DesignIdea(
            title=title,
            category=category,
            description=prompt,
            mechanics=mechanics,
            tags=[category.value, "ai-generated"],
        )

        if project:
            project.ideas[idea.idea_id] = idea
            project.modified_at = _time_module.time()
        self._total_ideas_created += 1

        session = self._find_active_session_for_project(project_id)
        if session:
            session.ideas_created += 1

        return idea

    # ------------------------------------------------------------------
    # Inspiration
    # ------------------------------------------------------------------

    def add_inspiration(
        self,
        source: str,
        content: str,
        category: DesignCategory,
        relevance_tags: Optional[List[str]] = None,
    ) -> DesignInspiration:
        inspiration = DesignInspiration(
            source=source,
            content=content,
            category=category,
            relevance_tags=relevance_tags if relevance_tags is not None else [],
        )
        self._inspirations[inspiration.inspiration_id] = inspiration
        return inspiration

    def link_inspiration(self, inspiration_id: str, idea_id: str) -> bool:
        inspiration = self._inspirations.get(inspiration_id)
        if inspiration is None:
            return False

        idea_found = False
        for project in self._projects.values():
            if idea_id in project.ideas:
                idea_found = True
                break

        if not idea_found:
            return False

        if idea_id not in inspiration.used_in_idea_ids:
            inspiration.used_in_idea_ids.append(idea_id)
        return True

    # ------------------------------------------------------------------
    # Query Methods
    # ------------------------------------------------------------------

    def get_project_ideas(
        self,
        project_id: str,
        status: Optional[DesignStatus] = None,
        category: Optional[DesignCategory] = None,
    ) -> List[DesignIdea]:
        project = self._projects.get(project_id)
        if project is None:
            return []

        ideas = list(project.ideas.values())
        if status is not None:
            ideas = [i for i in ideas if i.status == status]
        if category is not None:
            ideas = [i for i in ideas if i.category == category]
        return ideas

    # ------------------------------------------------------------------
    # Template Management
    # ------------------------------------------------------------------

    def add_element_template(
        self,
        element_type: DesignElement,
        name: str,
        description: str,
        parameters: Optional[Dict[str, Any]] = None,
        constraints: Optional[Dict[str, Any]] = None,
        examples: Optional[List[str]] = None,
    ) -> DesignElementTemplate:
        template = DesignElementTemplate(
            element_type=element_type,
            name=name,
            description=description,
            parameters=parameters if parameters is not None else {},
            constraints=constraints if constraints is not None else {},
            examples=examples if examples is not None else [],
        )
        self._templates[template.template_id] = template
        return template

    def get_templates_by_type(
        self, element_type: DesignElement
    ) -> List[DesignElementTemplate]:
        return [t for t in self._templates.values() if t.element_type == element_type]

    # ------------------------------------------------------------------
    # Project Statistics
    # ------------------------------------------------------------------

    def get_project_stats(self, project_id: str) -> Dict[str, Any]:
        project = self._projects.get(project_id)
        if project is None:
            return {"total_ideas": 0, "by_status": {}, "by_category": {}, "avg_rating": 0.0}

        ideas = list(project.ideas.values())

        by_status: Dict[str, int] = {}
        by_category: Dict[str, int] = {}
        for idea in ideas:
            status_key = idea.status.value
            by_status[status_key] = by_status.get(status_key, 0) + 1
            cat_key = idea.category.value
            by_category[cat_key] = by_category.get(cat_key, 0) + 1

        total_rating = 0.0
        rating_count = 0
        for idea in ideas:
            feedback_list = self._feedback.get(idea.idea_id, [])
            for fb in feedback_list:
                total_rating += fb.rating
                rating_count += 1

        avg_rating = round(total_rating / max(rating_count, 1), 2)

        return {
            "total_ideas": len(ideas),
            "by_status": by_status,
            "by_category": by_category,
            "avg_rating": avg_rating,
        }

    def generate_mechanic_combo(
        self, project_id: str, count: int = 3
    ) -> List[Tuple[str, str]]:
        project = self._projects.get(project_id)
        if project is None:
            return []

        mechanic_ideas = [
            i for i in project.ideas.values()
            if i.category == DesignCategory.MECHANIC
        ]

        if len(mechanic_ideas) < 2:
            return []

        combos: List[Tuple[str, str]] = []
        seen: set = set()

        max_attempts = count * 10
        attempts = 0
        while len(combos) < count and attempts < max_attempts:
            attempts += 1
            a = random.choice(mechanic_ideas)
            b = random.choice(mechanic_ideas)
            if a.idea_id == b.idea_id:
                continue
            pair = tuple(sorted([a.idea_id, b.idea_id]))
            if pair in seen:
                continue
            seen.add(pair)
            combo_name = f"{a.title} + {b.title}"
            combo_desc = (
                f"Combine '{a.title}' ({a.mechanics[0] if a.mechanics else 'core mechanic'}) "
                f"with '{b.title}' ({b.mechanics[0] if b.mechanics else 'secondary mechanic'}) "
                f"to create emergent gameplay interactions."
            )
            combos.append((combo_name, combo_desc))

        return combos

    def export_design_doc(self, project_id: str) -> Dict[str, Any]:
        project = self._projects.get(project_id)
        if project is None:
            return {"error": "project not found"}

        ideas = list(project.ideas.values())
        ideas_by_category: Dict[str, List[Dict[str, Any]]] = {}
        for idea in ideas:
            cat_key = idea.category.value
            if cat_key not in ideas_by_category:
                ideas_by_category[cat_key] = []
            ideas_by_category[cat_key].append(idea.to_dict())

        feedback_summary: Dict[str, List[Dict[str, Any]]] = {}
        for idea in ideas:
            fb_list = self._feedback.get(idea.idea_id, [])
            if fb_list:
                feedback_summary[idea.idea_id] = [fb.to_dict() for fb in fb_list]

        return {
            "project": project.to_dict(),
            "ideas_by_category": ideas_by_category,
            "feedback": feedback_summary,
            "total_ideas": len(ideas),
            "exported_at": _time_module.time(),
        }

    # ------------------------------------------------------------------
    # Internal Helpers
    # ------------------------------------------------------------------

    def _generate_title(self, category: DesignCategory, genre: str) -> str:
        category_key = category.value
        prefixes = _TITLE_PREFIXES.get(category_key, _TITLE_PREFIXES["mechanic"])
        prefix = random.choice(prefixes)
        suffix = random.choice(_TITLE_SUFFIXES)
        return f"{prefix} {suffix}"

    def _extract_mechanics_from_prompt(self, prompt: str) -> List[str]:
        mechanics: List[str] = []
        keywords = [
            "jump", "dash", "shoot", "build", "craft", "trade",
            "sneak", "climb", "glide", "teleport", "shield", "heal",
            "combo", "parry", "charge", "deploy", "transform", "possess",
        ]
        prompt_lower = prompt.lower()
        for kw in keywords:
            if kw in prompt_lower:
                mechanics.append(kw)
        if not mechanics:
            mechanics.append("core interaction")
        return mechanics

    def _find_active_session_for_project(
        self, project_id: str
    ) -> Optional[DesignSession]:
        for session in self._sessions.values():
            if session.project_id == project_id and session.ended_at is None:
                return session
        return None

    def get_project(self, project_id: str) -> Optional[DesignProject]:
        return self._projects.get(project_id)

    def get_stats(self) -> Dict[str, Any]:
        return {
            "total_projects": len(self._projects),
            "total_ideas_created": self._total_ideas_created,
            "total_sessions_run": self._total_sessions_run,
            "total_inspirations": len(self._inspirations),
            "total_templates": len(self._templates),
            "active_sessions": sum(
                1 for s in self._sessions.values() if s.ended_at is None
            ),
        }


def get_creative_director() -> AgentCreativeDirector:
    return AgentCreativeDirector.get_instance()