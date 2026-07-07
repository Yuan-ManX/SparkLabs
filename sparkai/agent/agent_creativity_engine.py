"""
SparkLabs AI-Native Game Engine - Agent Creativity Engine
=========================================================

Divergent thinking, combinatorial creativity, and novelty assessment for
AI agents in the SparkLabs AI-native game engine.

This module equips agents with the ability to generate original game ideas,
mechanics, narratives, characters, levels, and solutions. Rather than
recombining fixed templates, the Creativity Engine models the cognitive
processes that underlie human creativity: divergent exploration of a
solution space, combinatorial blending of distant concepts, and principled
novelty assessment that separates genuinely original ideas from minor
variations of existing work.

Creative Cognition Model
------------------------
The engine implements four interlocking capabilities:

1. **Divergent Thinking** -- Agents enumerate many candidate ideas within a
   creative domain, deliberately widening the search before any pruning
   happens. Each ``ThinkingMode`` (DIVERGENT, LATERAL, BISOCIATIVE, ...)
   biases the generation process toward a different exploration pattern.

2. **Combinatorial Creativity** -- Novelty frequently emerges at the
   intersection of two unrelated ideas. ``combine_ideas`` fuses source
   ideas into a new result whose novelty is boosted by the diversity of
   its parents (different domains, thinking modes, and tag spaces).

3. **Novelty Assessment** -- Every idea receives a ``novelty_score`` in
   [0, 1] computed from token overlap with existing ideas in the same
   domain plus tag rarity. The score is mapped to a qualitative
   ``NoveltyLevel`` ranging from MUNDANE to RADICAL.

4. **Creative Domains** -- The engine partitions the creative output
   space into domains (MECHANIC, NARRATIVE, CHARACTER, ...) so that
   novelty is judged relative to prior art within the same domain.

Inspirations (NATURE, MYTHOLOGY, SCIENCE, ART, ...) seed the creative
process. Each idea is created as a DRAFT, then optionally evaluated.
Evaluation records an evaluator's judgment of novelty, usefulness, and
surprise, updates the idea's combined score, and transitions the idea to
EVALUATED status. Refinement creates a derivative idea with
``refined_from`` pointing back to its ancestor.

The engine is a process-wide singleton accessed via ``get_instance()`` or
the module-level ``get_creativity_engine()`` helper. All public methods
are guarded by a reentrant lock for thread safety. In-memory stores are
bounded by capacity constants and use FIFO eviction so the engine never
grows without limit.
"""

from __future__ import annotations

import datetime
import threading
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Capacity constants - bounded in-memory stores with FIFO eviction
# ---------------------------------------------------------------------------

_MAX_IDEAS: int = 5000
_MAX_COMBINATIONS: int = 3000
_MAX_DOMAINS: int = 200
_MAX_INSPIRATIONS: int = 2000
_MAX_EVALUATIONS: int = 3000
_MAX_EVENTS: int = 2000


# ---------------------------------------------------------------------------
# Module-level helper functions
# ---------------------------------------------------------------------------

def _now() -> str:
    """Return the current UTC time as an ISO-8601 string with a 'Z' suffix."""
    return datetime.datetime.utcnow().isoformat() + "Z"


def _new_id() -> str:
    """Return a 16-character hexadecimal identifier."""
    return uuid.uuid4().hex[:16]


def _clamp(value: float, low: float, high: float) -> float:
    """Clamp ``value`` into the inclusive range [low, high]."""
    if value < low:
        return low
    if value > high:
        return high
    return value


def _token_overlap(a: str, b: str) -> float:
    """Return the Jaccard token overlap of two strings as a float in [0, 1].

    Both inputs are lowercased and split on whitespace. Two empty strings
    have zero overlap (not one), so that an empty description is treated
    as maximally novel rather than identical to other empty descriptions.
    """
    tokens_a = set(a.lower().split()) if a else set()
    tokens_b = set(b.lower().split()) if b else set()
    if not tokens_a or not tokens_b:
        return 0.0
    union = tokens_a | tokens_b
    if not union:
        return 0.0
    intersection = tokens_a & tokens_b
    return len(intersection) / len(union)


def _evict_fifo_dict(store: Dict[str, Any], max_size: int) -> None:
    """Evict the oldest inserted entries from a dict until within bounds.

    Python dicts preserve insertion order (3.7+), so the first key
    returned by iteration is the oldest. This implements FIFO eviction.
    """
    while len(store) > max_size:
        oldest_key = next(iter(store))
        store.pop(oldest_key, None)


def _evict_fifo_list(store: List[Any], max_size: int) -> None:
    """Evict the oldest inserted entries from a list until within bounds."""
    while len(store) > max_size:
        store.pop(0)


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class CreativeDomain(str, Enum):
    """A creative domain partitioning the space of generated game ideas."""
    MECHANIC = "mechanic"
    NARRATIVE = "narrative"
    CHARACTER = "character"
    LEVEL = "level"
    QUEST = "quest"
    ITEM = "item"
    ABILITY = "ability"
    VISUAL = "visual"
    AUDIO = "audio"
    WORLD = "world"
    STORY = "story"
    PUZZLE = "puzzle"
    COMBAT = "combat"
    ECONOMY = "economy"
    FACTION = "faction"


class ThinkingMode(str, Enum):
    """Cognitive strategy an agent uses when generating a creative idea."""
    DIVERGENT = "divergent"
    CONVERGENT = "convergent"
    LATERAL = "lateral"
    COMBINATORIAL = "combinatorial"
    ANALOGICAL = "analogical"
    TRANSFORMATIVE = "transformative"
    BISOCIATIVE = "bisociative"
    ABDUCTIVE = "abductive"


class IdeaStatus(str, Enum):
    """Lifecycle status of a creative idea."""
    DRAFT = "draft"
    PROPOSED = "proposed"
    EVALUATED = "evaluated"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    REFINED = "refined"
    ARCHIVED = "archived"


class NoveltyLevel(str, Enum):
    """Qualitative band for an idea's novelty score."""
    MUNDANE = "mundane"
    CONVENTIONAL = "conventional"
    MILD_NOVEL = "mild_novel"
    NOVEL = "novel"
    HIGHLY_NOVEL = "highly_novel"
    RADICAL = "radical"


class InspirationSource(str, Enum):
    """Origin category for an external creative inspiration."""
    NATURE = "nature"
    MYTHOLOGY = "mythology"
    SCIENCE = "science"
    ART = "art"
    MUSIC = "music"
    HISTORY = "history"
    DREAMS = "dreams"
    CROSS_DOMAIN = "cross_domain"
    PLAYER_BEHAVIOR = "player_behavior"
    EMERGENT_GAMEPLAY = "emergent_gameplay"


class CreativityEventKind(str, Enum):
    """Kind of observable event emitted by the creativity engine."""
    IDEA_GENERATED = "idea_generated"
    COMBINATION_CREATED = "combination_created"
    DOMAIN_REGISTERED = "domain_registered"
    INSPIRATION_ADDED = "inspiration_added"
    IDEA_EVALUATED = "idea_evaluated"
    IDEA_REFINED = "idea_refined"
    IDEA_ACCEPTED = "idea_accepted"
    IDEA_REJECTED = "idea_rejected"


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------

@dataclass
class CreativeIdea:
    """A single creative idea generated by an AI agent."""

    idea_id: str = field(default_factory=_new_id)
    title: str = ""
    description: str = ""
    domain: CreativeDomain = CreativeDomain.MECHANIC
    thinking_mode: ThinkingMode = ThinkingMode.DIVERGENT
    novelty_score: float = 0.0
    usefulness_score: float = 0.5
    surprise_score: float = 0.5
    combined_score: float = 0.0
    novelty_level: NoveltyLevel = NoveltyLevel.MUNDANE
    tags: List[str] = field(default_factory=list)
    source_inspirations: List[str] = field(default_factory=list)
    status: IdeaStatus = IdeaStatus.DRAFT
    agent_id: str = ""
    created_at: str = field(default_factory=_now)
    evaluated_at: Optional[str] = None
    refined_from: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "idea_id": self.idea_id,
            "title": self.title,
            "description": self.description,
            "domain": self.domain.value,
            "thinking_mode": self.thinking_mode.value,
            "novelty_score": self.novelty_score,
            "usefulness_score": self.usefulness_score,
            "surprise_score": self.surprise_score,
            "combined_score": self.combined_score,
            "novelty_level": self.novelty_level.value,
            "tags": list(self.tags),
            "source_inspirations": list(self.source_inspirations),
            "status": self.status.value,
            "agent_id": self.agent_id,
            "created_at": self.created_at,
            "evaluated_at": self.evaluated_at,
            "refined_from": self.refined_from,
            "metadata": dict(self.metadata),
        }


@dataclass
class IdeaCombination:
    """Record of a new idea created by fusing two or more source ideas."""

    combination_id: str = field(default_factory=_new_id)
    source_idea_ids: List[str] = field(default_factory=list)
    result_idea_id: str = ""
    combination_strategy: str = ""
    created_at: str = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "combination_id": self.combination_id,
            "source_idea_ids": list(self.source_idea_ids),
            "result_idea_id": self.result_idea_id,
            "combination_strategy": self.combination_strategy,
            "created_at": self.created_at,
        }


@dataclass
class DomainProfile:
    """Per-domain creative statistics and metadata."""

    domain: CreativeDomain = CreativeDomain.MECHANIC
    description: str = ""
    idea_count: int = 0
    avg_novelty: float = 0.0
    avg_usefulness: float = 0.0
    top_tags: List[str] = field(default_factory=list)
    created_at: str = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "domain": self.domain.value,
            "description": self.description,
            "idea_count": self.idea_count,
            "avg_novelty": self.avg_novelty,
            "avg_usefulness": self.avg_usefulness,
            "top_tags": list(self.top_tags),
            "created_at": self.created_at,
        }


@dataclass
class Inspiration:
    """An external creative seed that can inspire generated ideas."""

    inspiration_id: str = field(default_factory=_new_id)
    source: InspirationSource = InspirationSource.NATURE
    domain: CreativeDomain = CreativeDomain.MECHANIC
    content: str = ""
    relevance_score: float = 0.5
    tags: List[str] = field(default_factory=list)
    created_at: str = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "inspiration_id": self.inspiration_id,
            "source": self.source.value,
            "domain": self.domain.value,
            "content": self.content,
            "relevance_score": self.relevance_score,
            "tags": list(self.tags),
            "created_at": self.created_at,
        }


@dataclass
class IdeaEvaluation:
    """An evaluator's judgment of a creative idea."""

    evaluation_id: str = field(default_factory=_new_id)
    idea_id: str = ""
    novelty_score: float = 0.0
    usefulness_score: float = 0.0
    surprise_score: float = 0.0
    combined_score: float = 0.0
    novelty_level: NoveltyLevel = NoveltyLevel.MUNDANE
    feedback: str = ""
    evaluator: str = ""
    evaluated_at: str = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "evaluation_id": self.evaluation_id,
            "idea_id": self.idea_id,
            "novelty_score": self.novelty_score,
            "usefulness_score": self.usefulness_score,
            "surprise_score": self.surprise_score,
            "combined_score": self.combined_score,
            "novelty_level": self.novelty_level.value,
            "feedback": self.feedback,
            "evaluator": self.evaluator,
            "evaluated_at": self.evaluated_at,
        }


@dataclass
class CreativityStats:
    """Aggregate statistics across all creativity artifacts."""

    total_ideas: int = 0
    total_combinations: int = 0
    total_domains: int = 0
    total_inspirations: int = 0
    total_evaluations: int = 0
    avg_novelty: float = 0.0
    avg_usefulness: float = 0.0
    avg_surprise: float = 0.0
    ideas_by_status: Dict[str, int] = field(default_factory=dict)
    ideas_by_domain: Dict[str, int] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_ideas": self.total_ideas,
            "total_combinations": self.total_combinations,
            "total_domains": self.total_domains,
            "total_inspirations": self.total_inspirations,
            "total_evaluations": self.total_evaluations,
            "avg_novelty": self.avg_novelty,
            "avg_usefulness": self.avg_usefulness,
            "avg_surprise": self.avg_surprise,
            "ideas_by_status": dict(self.ideas_by_status),
            "ideas_by_domain": dict(self.ideas_by_domain),
        }


@dataclass
class CreativityEvent:
    """An observable event emitted by the creativity engine."""

    event_id: str = field(default_factory=_new_id)
    kind: CreativityEventKind = CreativityEventKind.IDEA_GENERATED
    timestamp: str = field(default_factory=_now)
    payload: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": self.event_id,
            "kind": self.kind.value,
            "timestamp": self.timestamp,
            "payload": dict(self.payload),
        }


@dataclass
class CreativitySnapshot:
    """Point-in-time snapshot of the entire creativity engine state."""

    initialized: bool = False
    ideas: List[Dict[str, Any]] = field(default_factory=list)
    combinations: List[Dict[str, Any]] = field(default_factory=list)
    domains: List[Dict[str, Any]] = field(default_factory=list)
    inspirations: List[Dict[str, Any]] = field(default_factory=list)
    evaluations: List[Dict[str, Any]] = field(default_factory=list)
    events: List[Dict[str, Any]] = field(default_factory=list)
    stats: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "initialized": self.initialized,
            "ideas": list(self.ideas),
            "combinations": list(self.combinations),
            "domains": list(self.domains),
            "inspirations": list(self.inspirations),
            "evaluations": list(self.evaluations),
            "events": list(self.events),
            "stats": dict(self.stats),
        }


# ---------------------------------------------------------------------------
# Creativity Engine (Singleton)
# ---------------------------------------------------------------------------

class CreativityEngine:
    """
    Divergent-thinking, combinatorial-creativity, and novelty-assessment
    engine for AI agents in the SparkLabs game engine.

    The engine lets agents generate creative ideas, fuse existing ideas
    into new ones, judge novelty against prior art within a creative
    domain, and track an idea through its lifecycle from DRAFT to
    ACCEPTED, REJECTED, or ARCHIVED. Inspirations (NATURE, MYTHOLOGY,
    SCIENCE, ...) seed the creative process and can be cited as the
    source of any idea.

    The engine is a process-wide singleton accessed via ``get_instance()``
    or the module-level ``get_creativity_engine()`` helper. All public
    methods are guarded by a reentrant lock for thread safety. In-memory
    stores are bounded by capacity constants and use FIFO eviction so
    the engine never grows without limit.
    """

    _instance: Optional["CreativityEngine"] = None
    _lock = threading.RLock()

    # Scoring weights for the combined score
    _NOVELTY_WEIGHT: float = 0.4
    _USEFULNESS_WEIGHT: float = 0.3
    _SURPRISE_WEIGHT: float = 0.3

    # Refinement novelty boost applied to derivative ideas
    _REFINE_NOVELTY_BOOST: float = 0.05

    # Maximum novelty boost a combination can earn from source diversity
    _COMBINE_DIVERSITY_BOOST_CAP: float = 0.2

    def __new__(cls) -> "CreativityEngine":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    instance = super().__new__(cls)
                    instance._initialized = False
                    cls._instance = instance
        return cls._instance

    @classmethod
    def get_instance(cls) -> "CreativityEngine":
        """Return the singleton CreativityEngine instance.

        Uses double-checked locking so that calls after initialization
        take the fast path without acquiring the lock. Does NOT reset
        ``_initialized``; only constructs the singleton if it is absent.
        """
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def __init__(self) -> None:
        # Guard against re-initialization of the singleton.
        if self._initialized:
            return
        with self._lock:
            if self._initialized:
                return

            # Core storage keyed by entity id
            self._ideas: Dict[str, CreativeIdea] = {}
            self._combinations: Dict[str, IdeaCombination] = {}
            self._domains: Dict[str, DomainProfile] = {}
            self._inspirations: Dict[str, Inspiration] = {}
            self._evaluations: Dict[str, IdeaEvaluation] = {}

            # Observable event log
            self._events: List[CreativityEvent] = []

            # Monotonic counters for diagnostics
            self._idea_counter: int = 0
            self._combination_counter: int = 0
            self._domain_counter: int = 0
            self._inspiration_counter: int = 0
            self._evaluation_counter: int = 0

            # Mark initialization complete, then seed baseline data.
            # _seed_data is called at the END of init as required.
            self._initialized: bool = True
            self._seed_data()

    # ------------------------------------------------------------------
    # Seed Data
    # ------------------------------------------------------------------

    def _seed_data(self) -> None:
        """Populate the engine with baseline creative content.

        Seeds five creative domains, six cross-domain inspirations, five
        sample ideas spanning different thinking modes, two evaluations,
        and one combination record.
        """
        now = _now()

        # --- Creative Domains -----------------------------------------
        domain_specs = [
            (CreativeDomain.MECHANIC,
             "Gameplay mechanics: rules, interactions, and player verbs."),
            (CreativeDomain.NARRATIVE,
             "Story arcs, plot beats, and thematic structure."),
            (CreativeDomain.CHARACTER,
             "Player and non-player characters: personality, arc, abilities."),
            (CreativeDomain.LEVEL,
             "Level design: layout, pacing, and spatial composition."),
            (CreativeDomain.QUEST,
             "Quest and mission design: objectives, branches, rewards."),
        ]
        for domain, description in domain_specs:
            profile = DomainProfile(
                domain=domain,
                description=description,
                created_at=now,
            )
            self._domains[domain.value] = profile
            self._domain_counter += 1
            self._record_event(
                CreativityEventKind.DOMAIN_REGISTERED,
                {"domain": domain.value, "description": description},
            )

        # --- Inspirations --------------------------------------------
        inspiration_specs = [
            (InspirationSource.NATURE, CreativeDomain.MECHANIC,
             "Flocking birds: emergent group movement from simple local rules.",
             0.8, ["emergence", "flocking", "boids"]),
            (InspirationSource.NATURE, CreativeDomain.VISUAL,
             "Bioluminescence: deep-sea organisms producing living light.",
             0.75, ["light", "organic", "glow"]),
            (InspirationSource.MYTHOLOGY, CreativeDomain.NARRATIVE,
             "The hero's journey: monomyth structure of call, trial, return.",
             0.85, ["monomyth", "journey", "archetype"]),
            (InspirationSource.MYTHOLOGY, CreativeDomain.CHARACTER,
             "Trickster gods: boundary-crossers who disrupt order for change.",
             0.7, ["trickster", "chaos", "change"]),
            (InspirationSource.SCIENCE, CreativeDomain.MECHANIC,
             "Gravity waves: ripples in spacetime from cosmic events.",
             0.8, ["gravity", "waves", "physics"]),
            (InspirationSource.ART, CreativeDomain.VISUAL,
             "Cubism: simultaneous multiple viewpoints of a single subject.",
             0.72, ["cubism", "perspective", "fragmentation"]),
        ]
        for source, domain, content, relevance, tags in inspiration_specs:
            inspiration = Inspiration(
                source=source,
                domain=domain,
                content=content,
                relevance_score=relevance,
                tags=list(tags),
                created_at=now,
            )
            self._inspirations[inspiration.inspiration_id] = inspiration
            self._inspiration_counter += 1
            self._record_event(
                CreativityEventKind.INSPIRATION_ADDED,
                {
                    "inspiration_id": inspiration.inspiration_id,
                    "source": source.value,
                    "domain": domain.value,
                },
            )

        # --- Creative Ideas ------------------------------------------
        # Five seeded ideas spanning different thinking modes and domains.
        # Novelty scores and levels are set explicitly to match the
        # intended creative profile of each idea.
        idea_specs = [
            (
                "Gravity-Reversing Platforms",
                "Platforms that invert the player's gravity vector when "
                "stepped on, creating vertical puzzle sequences.",
                CreativeDomain.MECHANIC,
                ThinkingMode.DIVERGENT,
                0.75,
                NoveltyLevel.NOVEL,
                ["gravity", "platforming", "physics"],
            ),
            (
                "Non-Linear Memory Quest",
                "A quest whose objectives are reconstructed from the player's "
                "own memories, with branching order depending on recall.",
                CreativeDomain.QUEST,
                ThinkingMode.LATERAL,
                0.82,
                NoveltyLevel.NOVEL,
                ["memory", "non-linear", "quest"],
            ),
            (
                "Shape-Shifting Protagonist",
                "A protagonist whose identity and abilities shift based on "
                "the form they currently inhabit, blending character and "
                "mechanic design.",
                CreativeDomain.CHARACTER,
                ThinkingMode.COMBINATORIAL,
                0.68,
                NoveltyLevel.MILD_NOVEL,
                ["transformation", "character", "identity"],
            ),
            (
                "Procedural Dream World",
                "A world whose geography, palette, and rules are procedurally "
                "regenerated each time the player sleeps, evoking dream logic.",
                CreativeDomain.WORLD,
                ThinkingMode.BISOCIATIVE,
                0.91,
                NoveltyLevel.HIGHLY_NOVEL,
                ["procedural", "dream", "surreal"],
            ),
            (
                "Echo-Based Combat",
                "Combat where every action emits a sound echo that enemies "
                "use to locate the player, turning audio into a tactical "
                "resource.",
                CreativeDomain.COMBAT,
                ThinkingMode.ANALOGICAL,
                0.78,
                NoveltyLevel.NOVEL,
                ["sound", "echo", "combat"],
            ),
        ]

        seeded_idea_ids: List[str] = []
        for (title, description, domain, thinking_mode, novelty,
             novelty_level, tags) in idea_specs:
            usefulness = 0.5
            surprise = 0.5
            combined = (
                self._NOVELTY_WEIGHT * novelty
                + self._USEFULNESS_WEIGHT * usefulness
                + self._SURPRISE_WEIGHT * surprise
            )
            idea = CreativeIdea(
                title=title,
                description=description,
                domain=domain,
                thinking_mode=thinking_mode,
                novelty_score=novelty,
                usefulness_score=usefulness,
                surprise_score=surprise,
                combined_score=combined,
                novelty_level=novelty_level,
                tags=list(tags),
                source_inspirations=[],
                status=IdeaStatus.DRAFT,
                agent_id="seed_agent",
                created_at=now,
            )
            self._ideas[idea.idea_id] = idea
            self._idea_counter += 1
            seeded_idea_ids.append(idea.idea_id)
            self._record_event(
                CreativityEventKind.IDEA_GENERATED,
                {
                    "idea_id": idea.idea_id,
                    "title": title,
                    "domain": domain.value,
                    "thinking_mode": thinking_mode.value,
                    "novelty_score": novelty,
                    "novelty_level": novelty_level.value,
                },
            )

        # Update domain statistics to reflect seeded ideas.
        self._refresh_domain_profiles()

        # --- Evaluations ---------------------------------------------
        # Evaluate two of the seeded ideas to demonstrate the evaluation
        # workflow. Evaluation updates the idea's scores, combined score,
        # novelty level, and transitions it to EVALUATED status.
        if len(seeded_idea_ids) >= 1:
            self._apply_evaluation(
                idea_id=seeded_idea_ids[0],
                novelty_score=0.78,
                usefulness_score=0.72,
                surprise_score=0.68,
                feedback="Strong mechanic with clear puzzle potential.",
                evaluator="seed_evaluator",
                evaluated_at=now,
            )
        if len(seeded_idea_ids) >= 4:
            self._apply_evaluation(
                idea_id=seeded_idea_ids[3],
                novelty_score=0.92,
                usefulness_score=0.65,
                surprise_score=0.88,
                feedback="Radical concept; needs careful pacing work.",
                evaluator="seed_evaluator",
                evaluated_at=now,
            )

        # --- Combination ---------------------------------------------
        # Combine idea 1 (Gravity-Reversing Platforms) with idea 5
        # (Echo-Based Combat) into a new fused idea.
        if len(seeded_idea_ids) >= 5:
            source_ids = [seeded_idea_ids[0], seeded_idea_ids[4]]
            combined_novelty = _clamp(
                0.85 + self._COMBINE_DIVERSITY_BOOST_CAP,
                0.0,
                1.0,
            )
            combined_usefulness = 0.6
            combined_surprise = 0.82
            combined_score = (
                self._NOVELTY_WEIGHT * combined_novelty
                + self._USEFULNESS_WEIGHT * combined_usefulness
                + self._SURPRISE_WEIGHT * combined_surprise
            )
            fused_idea = CreativeIdea(
                title="Echo Gravity Wells",
                description="Gravity-reversing platforms whose inversions "
                            "emit sound echoes that enemies track, fusing "
                            "vertical platforming with audio stealth.",
                domain=CreativeDomain.MECHANIC,
                thinking_mode=ThinkingMode.COMBINATORIAL,
                novelty_score=combined_novelty,
                usefulness_score=combined_usefulness,
                surprise_score=combined_surprise,
                combined_score=combined_score,
                novelty_level=self._assign_novelty_level(combined_novelty),
                tags=["gravity", "echo", "stealth", "platforming"],
                source_inspirations=[],
                status=IdeaStatus.DRAFT,
                agent_id="seed_agent",
                created_at=now,
            )
            self._ideas[fused_idea.idea_id] = fused_idea
            self._idea_counter += 1

            combination = IdeaCombination(
                source_idea_ids=list(source_ids),
                result_idea_id=fused_idea.idea_id,
                combination_strategy="concept_fusion",
                created_at=now,
            )
            self._combinations[combination.combination_id] = combination
            self._combination_counter += 1
            self._record_event(
                CreativityEventKind.COMBINATION_CREATED,
                {
                    "combination_id": combination.combination_id,
                    "source_idea_ids": list(source_ids),
                    "result_idea_id": fused_idea.idea_id,
                    "strategy": "concept_fusion",
                },
            )

        # Refresh domain statistics after the fused idea and evaluations.
        self._refresh_domain_profiles()

    # ------------------------------------------------------------------
    # Idea Generation
    # ------------------------------------------------------------------

    def generate_idea(
        self,
        title: str,
        description: str,
        domain: CreativeDomain,
        thinking_mode: ThinkingMode,
        agent_id: str,
        tags: Optional[List[str]] = None,
        source_inspirations: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> CreativeIdea:
        """Generate a new DRAFT creative idea.

        Novelty is computed from tag rarity and description token-overlap
        with existing ideas in the same domain. Usefulness and surprise
        start at 0.5. The combined score is a weighted blend (0.4
        novelty + 0.3 usefulness + 0.3 surprise), and ``novelty_level``
        is derived from the novelty score via fixed thresholds.
        """
        with self._lock:
            # Normalize domain / thinking_mode from string if needed.
            if isinstance(domain, str):
                try:
                    domain = CreativeDomain(domain)
                except ValueError:
                    domain = CreativeDomain.MECHANIC
            if isinstance(thinking_mode, str):
                try:
                    thinking_mode = ThinkingMode(thinking_mode)
                except ValueError:
                    thinking_mode = ThinkingMode.DIVERGENT

            tags_list = list(tags) if tags else []
            source_list = list(source_inspirations) if source_inspirations else []
            meta = dict(metadata) if metadata else {}

            novelty = self._compute_novelty(description, tags_list, domain)
            usefulness = 0.5
            surprise = 0.5
            combined = (
                self._NOVELTY_WEIGHT * novelty
                + self._USEFULNESS_WEIGHT * usefulness
                + self._SURPRISE_WEIGHT * surprise
            )
            novelty_level = self._assign_novelty_level(novelty)

            idea = CreativeIdea(
                title=title,
                description=description,
                domain=domain,
                thinking_mode=thinking_mode,
                novelty_score=novelty,
                usefulness_score=usefulness,
                surprise_score=surprise,
                combined_score=combined,
                novelty_level=novelty_level,
                tags=tags_list,
                source_inspirations=source_list,
                status=IdeaStatus.DRAFT,
                agent_id=agent_id,
                metadata=meta,
            )

            self._ideas[idea.idea_id] = idea
            self._idea_counter += 1
            _evict_fifo_dict(self._ideas, _MAX_IDEAS)
            self._refresh_domain_profiles()

            self._record_event(
                CreativityEventKind.IDEA_GENERATED,
                {
                    "idea_id": idea.idea_id,
                    "title": title,
                    "domain": domain.value,
                    "thinking_mode": thinking_mode.value,
                    "novelty_score": novelty,
                    "novelty_level": novelty_level.value,
                    "agent_id": agent_id,
                },
            )
            return idea

    def list_ideas(
        self,
        domain: Optional[CreativeDomain] = None,
        status: Optional[IdeaStatus] = None,
        thinking_mode: Optional[ThinkingMode] = None,
        agent_id: Optional[str] = None,
        min_novelty: Optional[float] = None,
    ) -> List[CreativeIdea]:
        """List ideas filtered by domain, status, thinking mode, agent, or minimum novelty."""
        with self._lock:
            # Normalize string inputs to enum values when possible.
            if isinstance(domain, str):
                try:
                    domain = CreativeDomain(domain)
                except ValueError:
                    domain = None
            if isinstance(status, str):
                try:
                    status = IdeaStatus(status)
                except ValueError:
                    status = None
            if isinstance(thinking_mode, str):
                try:
                    thinking_mode = ThinkingMode(thinking_mode)
                except ValueError:
                    thinking_mode = None

            results: List[CreativeIdea] = []
            for idea in self._ideas.values():
                if domain is not None and idea.domain != domain:
                    continue
                if status is not None and idea.status != status:
                    continue
                if thinking_mode is not None and idea.thinking_mode != thinking_mode:
                    continue
                if agent_id is not None and idea.agent_id != agent_id:
                    continue
                if min_novelty is not None and idea.novelty_score < min_novelty:
                    continue
                results.append(idea)
            return results

    def get_idea(self, idea_id: str) -> Optional[CreativeIdea]:
        """Retrieve a single creative idea by ID."""
        with self._lock:
            return self._ideas.get(idea_id)

    def update_idea(
        self,
        idea_id: str,
        title: Optional[str] = None,
        description: Optional[str] = None,
        status: Optional[IdeaStatus] = None,
        tags: Optional[List[str]] = None,
    ) -> Optional[CreativeIdea]:
        """Update mutable fields of an idea.

        Only the supplied fields are changed. If ``description`` or
        ``tags`` change, the idea's ``novelty_score`` and
        ``novelty_level`` are recomputed and the ``combined_score`` is
        updated accordingly.
        """
        with self._lock:
            idea = self._ideas.get(idea_id)
            if idea is None:
                return None

            recompute_novelty = False
            if title is not None:
                idea.title = title
            if description is not None:
                idea.description = description
                recompute_novelty = True
            if status is not None:
                if isinstance(status, str):
                    try:
                        status = IdeaStatus(status)
                    except ValueError:
                        status = idea.status
                idea.status = status
            if tags is not None:
                idea.tags = list(tags)
                recompute_novelty = True

            if recompute_novelty:
                idea.novelty_score = self._compute_novelty(
                    idea.description, idea.tags, idea.domain
                )
                idea.novelty_level = self._assign_novelty_level(idea.novelty_score)
                idea.combined_score = (
                    self._NOVELTY_WEIGHT * idea.novelty_score
                    + self._USEFULNESS_WEIGHT * idea.usefulness_score
                    + self._SURPRISE_WEIGHT * idea.surprise_score
                )
                self._refresh_domain_profiles()

            return idea

    # ------------------------------------------------------------------
    # Combinatorial Creativity
    # ------------------------------------------------------------------

    def combine_ideas(
        self,
        source_idea_ids: List[str],
        title: str,
        description: str,
        domain: CreativeDomain,
        thinking_mode: ThinkingMode,
        agent_id: str,
        combination_strategy: str,
    ) -> Tuple[CreativeIdea, IdeaCombination]:
        """Create a new idea by fusing two or more existing source ideas.

        Novelty is boosted by the diversity of the source ideas (distinct
        domains, thinking modes, and tag spaces). An ``IdeaCombination``
        record is stored so that creative lineage can be traced.
        """
        with self._lock:
            # Normalize enum inputs from strings if needed.
            if isinstance(domain, str):
                try:
                    domain = CreativeDomain(domain)
                except ValueError:
                    domain = CreativeDomain.MECHANIC
            if isinstance(thinking_mode, str):
                try:
                    thinking_mode = ThinkingMode(thinking_mode)
                except ValueError:
                    thinking_mode = ThinkingMode.COMBINATORIAL

            sources: List[CreativeIdea] = []
            for sid in source_idea_ids:
                idea = self._ideas.get(sid)
                if idea is not None:
                    sources.append(idea)

            base_novelty = self._compute_novelty(description, [], domain)
            diversity_boost = self._compute_source_diversity_boost(sources)
            novelty = _clamp(base_novelty + diversity_boost, 0.0, 1.0)
            usefulness = 0.5
            surprise = 0.5
            combined = (
                self._NOVELTY_WEIGHT * novelty
                + self._USEFULNESS_WEIGHT * usefulness
                + self._SURPRISE_WEIGHT * surprise
            )
            novelty_level = self._assign_novelty_level(novelty)

            merged_tags: List[str] = []
            seen_tags: set = set()
            for src in sources:
                for tag in src.tags:
                    if tag not in seen_tags:
                        seen_tags.add(tag)
                        merged_tags.append(tag)

            result_idea = CreativeIdea(
                title=title,
                description=description,
                domain=domain,
                thinking_mode=thinking_mode,
                novelty_score=novelty,
                usefulness_score=usefulness,
                surprise_score=surprise,
                combined_score=combined,
                novelty_level=novelty_level,
                tags=merged_tags,
                source_inspirations=[],
                status=IdeaStatus.DRAFT,
                agent_id=agent_id,
                metadata={
                    "combined_from": list(source_idea_ids),
                    "combination_strategy": combination_strategy,
                },
            )
            self._ideas[result_idea.idea_id] = result_idea
            self._idea_counter += 1
            _evict_fifo_dict(self._ideas, _MAX_IDEAS)

            combination = IdeaCombination(
                source_idea_ids=list(source_idea_ids),
                result_idea_id=result_idea.idea_id,
                combination_strategy=combination_strategy,
            )
            self._combinations[combination.combination_id] = combination
            self._combination_counter += 1
            _evict_fifo_dict(self._combinations, _MAX_COMBINATIONS)

            self._refresh_domain_profiles()
            self._record_event(
                CreativityEventKind.COMBINATION_CREATED,
                {
                    "combination_id": combination.combination_id,
                    "source_idea_ids": list(source_idea_ids),
                    "result_idea_id": result_idea.idea_id,
                    "strategy": combination_strategy,
                    "diversity_boost": diversity_boost,
                },
            )
            return result_idea, combination

    def list_combinations(self) -> List[IdeaCombination]:
        """Return all stored idea-combination records."""
        with self._lock:
            return list(self._combinations.values())

    def _compute_source_diversity_boost(
        self, sources: List[CreativeIdea]
    ) -> float:
        """Compute the novelty boost earned from source-idea diversity.

        Diversity is measured across three axes: distinct domains,
        distinct thinking modes, and the size of the union of tag sets.
        The composite is scaled to the configured cap.
        """
        if not sources:
            return 0.0
        domains = {src.domain.value for src in sources}
        modes = {src.thinking_mode.value for src in sources}
        tag_union: set = set()
        for src in sources:
            tag_union.update(src.tags)

        n = len(sources)
        # Each axis contributes a ratio in [1/n, 1].
        domain_ratio = len(domains) / n
        mode_ratio = len(modes) / n
        # Tag diversity: reward a large union of tags relative to sources.
        tag_ratio = min(len(tag_union) / max(n * 3.0, 1.0), 1.0)

        diversity = (domain_ratio + mode_ratio + tag_ratio) / 3.0
        return _clamp(
            diversity * self._COMBINE_DIVERSITY_BOOST_CAP,
            0.0,
            self._COMBINE_DIVERSITY_BOOST_CAP,
        )

    # ------------------------------------------------------------------
    # Domain Management
    # ------------------------------------------------------------------

    def register_domain(
        self,
        domain: CreativeDomain,
        description: str,
    ) -> DomainProfile:
        """Register or update a creative domain profile.

        If a profile already exists for the domain, its description is
        updated and its statistics are refreshed; otherwise a new
        profile is created.
        """
        with self._lock:
            if isinstance(domain, str):
                try:
                    domain = CreativeDomain(domain)
                except ValueError:
                    domain = CreativeDomain.MECHANIC

            existing = self._domains.get(domain.value)
            if existing is not None:
                existing.description = description
                self._refresh_domain(domain)
                self._record_event(
                    CreativityEventKind.DOMAIN_REGISTERED,
                    {"domain": domain.value, "description": description,
                     "updated": True},
                )
                return existing

            profile = DomainProfile(
                domain=domain,
                description=description,
                created_at=_now(),
            )
            self._domains[domain.value] = profile
            self._domain_counter += 1
            _evict_fifo_dict(self._domains, _MAX_DOMAINS)
            self._refresh_domain(domain)
            self._record_event(
                CreativityEventKind.DOMAIN_REGISTERED,
                {"domain": domain.value, "description": description},
            )
            return profile

    def list_domains(self) -> List[DomainProfile]:
        """Return all registered creative domain profiles."""
        with self._lock:
            return list(self._domains.values())

    def get_domain(self, domain: CreativeDomain) -> Optional[DomainProfile]:
        """Retrieve a domain profile by domain enum value."""
        with self._lock:
            if isinstance(domain, str):
                try:
                    domain = CreativeDomain(domain)
                except ValueError:
                    return None
            return self._domains.get(domain.value)

    def _refresh_domain(self, domain: CreativeDomain) -> None:
        """Recompute statistics for a single domain from stored ideas."""
        profile = self._domains.get(domain.value)
        if profile is None:
            return
        ideas_in_domain = [
            i for i in self._ideas.values() if i.domain == domain
        ]
        profile.idea_count = len(ideas_in_domain)
        if ideas_in_domain:
            profile.avg_novelty = sum(
                i.novelty_score for i in ideas_in_domain
            ) / len(ideas_in_domain)
            profile.avg_usefulness = sum(
                i.usefulness_score for i in ideas_in_domain
            ) / len(ideas_in_domain)
        else:
            profile.avg_novelty = 0.0
            profile.avg_usefulness = 0.0

        # Top tags by frequency within this domain.
        tag_counts: Dict[str, int] = {}
        for idea in ideas_in_domain:
            for tag in idea.tags:
                tag_counts[tag] = tag_counts.get(tag, 0) + 1
        ranked = sorted(tag_counts.items(), key=lambda x: x[1], reverse=True)
        profile.top_tags = [tag for tag, _ in ranked[:10]]

    def _refresh_domain_profiles(self) -> None:
        """Recompute statistics for every registered domain."""
        for domain in list(self._domains.keys()):
            try:
                dom_enum = CreativeDomain(domain)
            except ValueError:
                continue
            self._refresh_domain(dom_enum)

    # ------------------------------------------------------------------
    # Inspirations
    # ------------------------------------------------------------------

    def add_inspiration(
        self,
        source: InspirationSource,
        domain: CreativeDomain,
        content: str,
        relevance_score: float,
        tags: Optional[List[str]] = None,
    ) -> Inspiration:
        """Add a new external inspiration to the creative pool."""
        with self._lock:
            if isinstance(source, str):
                try:
                    source = InspirationSource(source)
                except ValueError:
                    source = InspirationSource.NATURE
            if isinstance(domain, str):
                try:
                    domain = CreativeDomain(domain)
                except ValueError:
                    domain = CreativeDomain.MECHANIC

            inspiration = Inspiration(
                source=source,
                domain=domain,
                content=content,
                relevance_score=_clamp(relevance_score, 0.0, 1.0),
                tags=list(tags) if tags else [],
            )
            self._inspirations[inspiration.inspiration_id] = inspiration
            self._inspiration_counter += 1
            _evict_fifo_dict(self._inspirations, _MAX_INSPIRATIONS)
            self._record_event(
                CreativityEventKind.INSPIRATION_ADDED,
                {
                    "inspiration_id": inspiration.inspiration_id,
                    "source": source.value,
                    "domain": domain.value,
                    "relevance_score": inspiration.relevance_score,
                },
            )
            return inspiration

    def list_inspirations(
        self,
        domain: Optional[CreativeDomain] = None,
        source: Optional[InspirationSource] = None,
    ) -> List[Inspiration]:
        """List inspirations filtered by domain and/or source."""
        with self._lock:
            if isinstance(domain, str):
                try:
                    domain = CreativeDomain(domain)
                except ValueError:
                    domain = None
            if isinstance(source, str):
                try:
                    source = InspirationSource(source)
                except ValueError:
                    source = None

            results: List[Inspiration] = []
            for insp in self._inspirations.values():
                if domain is not None and insp.domain != domain:
                    continue
                if source is not None and insp.source != source:
                    continue
                results.append(insp)
            return results

    # ------------------------------------------------------------------
    # Evaluation
    # ------------------------------------------------------------------

    def evaluate_idea(
        self,
        idea_id: str,
        novelty_score: float,
        usefulness_score: float,
        surprise_score: float,
        feedback: str,
        evaluator: str,
    ) -> Optional[IdeaEvaluation]:
        """Evaluate an idea and update its scores and status.

        Records a new ``IdeaEvaluation``, then updates the target idea's
        ``novelty_score``, ``usefulness_score``, ``surprise_score``,
        ``combined_score``, ``novelty_level``, ``evaluated_at`` and
        transitions its status to ``EVALUATED``. Returns the evaluation
        record, or ``None`` if the idea does not exist.
        """
        with self._lock:
            return self._apply_evaluation(
                idea_id=idea_id,
                novelty_score=novelty_score,
                usefulness_score=usefulness_score,
                surprise_score=surprise_score,
                feedback=feedback,
                evaluator=evaluator,
                evaluated_at=_now(),
            )

    def _apply_evaluation(
        self,
        idea_id: str,
        novelty_score: float,
        usefulness_score: float,
        surprise_score: float,
        feedback: str,
        evaluator: str,
        evaluated_at: str,
    ) -> Optional[IdeaEvaluation]:
        """Internal helper that performs the actual evaluation update.

        Assumes the caller already holds ``self._lock``.
        """
        idea = self._ideas.get(idea_id)
        if idea is None:
            return None

        novelty = _clamp(novelty_score, 0.0, 1.0)
        usefulness = _clamp(usefulness_score, 0.0, 1.0)
        surprise = _clamp(surprise_score, 0.0, 1.0)
        combined = (
            self._NOVELTY_WEIGHT * novelty
            + self._USEFULNESS_WEIGHT * usefulness
            + self._SURPRISE_WEIGHT * surprise
        )
        novelty_level = self._assign_novelty_level(novelty)

        evaluation = IdeaEvaluation(
            idea_id=idea_id,
            novelty_score=novelty,
            usefulness_score=usefulness,
            surprise_score=surprise,
            combined_score=combined,
            novelty_level=novelty_level,
            feedback=feedback,
            evaluator=evaluator,
            evaluated_at=evaluated_at,
        )
        self._evaluations[evaluation.evaluation_id] = evaluation
        self._evaluation_counter += 1
        _evict_fifo_dict(self._evaluations, _MAX_EVALUATIONS)

        # Mutate the idea to reflect the evaluation.
        idea.novelty_score = novelty
        idea.usefulness_score = usefulness
        idea.surprise_score = surprise
        idea.combined_score = combined
        idea.novelty_level = novelty_level
        idea.evaluated_at = evaluated_at
        idea.status = IdeaStatus.EVALUATED

        self._refresh_domain(idea.domain)
        self._record_event(
            CreativityEventKind.IDEA_EVALUATED,
            {
                "evaluation_id": evaluation.evaluation_id,
                "idea_id": idea_id,
                "novelty_score": novelty,
                "usefulness_score": usefulness,
                "surprise_score": surprise,
                "combined_score": combined,
                "novelty_level": novelty_level.value,
                "evaluator": evaluator,
            },
        )
        return evaluation

    def list_evaluations(
        self, idea_id: Optional[str] = None
    ) -> List[IdeaEvaluation]:
        """List evaluations, optionally filtered by idea ID."""
        with self._lock:
            if idea_id is None:
                return list(self._evaluations.values())
            return [
                e for e in self._evaluations.values() if e.idea_id == idea_id
            ]

    # ------------------------------------------------------------------
    # Idea Lifecycle
    # ------------------------------------------------------------------

    def refine_idea(
        self,
        idea_id: str,
        new_title: str,
        new_description: str,
        agent_id: str,
    ) -> Optional[CreativeIdea]:
        """Create a refined derivative of an existing idea.

        The refined idea is a new ``CreativeIdea`` with ``refined_from``
        set to the original idea's ID and a small novelty boost applied
        to the recomputed novelty score. The original idea's status
        transitions to ``REFINED``.
        """
        with self._lock:
            original = self._ideas.get(idea_id)
            if original is None:
                return None

            base_novelty = self._compute_novelty(
                new_description, original.tags, original.domain
            )
            novelty = _clamp(
                base_novelty + self._REFINE_NOVELTY_BOOST, 0.0, 1.0
            )
            usefulness = original.usefulness_score
            surprise = original.surprise_score
            combined = (
                self._NOVELTY_WEIGHT * novelty
                + self._USEFULNESS_WEIGHT * usefulness
                + self._SURPRISE_WEIGHT * surprise
            )
            novelty_level = self._assign_novelty_level(novelty)

            refined = CreativeIdea(
                title=new_title,
                description=new_description,
                domain=original.domain,
                thinking_mode=original.thinking_mode,
                novelty_score=novelty,
                usefulness_score=usefulness,
                surprise_score=surprise,
                combined_score=combined,
                novelty_level=novelty_level,
                tags=list(original.tags),
                source_inspirations=list(original.source_inspirations),
                status=IdeaStatus.DRAFT,
                agent_id=agent_id,
                refined_from=original.idea_id,
                metadata=dict(original.metadata),
            )
            self._ideas[refined.idea_id] = refined
            self._idea_counter += 1
            _evict_fifo_dict(self._ideas, _MAX_IDEAS)

            original.status = IdeaStatus.REFINED
            self._refresh_domain(original.domain)
            self._record_event(
                CreativityEventKind.IDEA_REFINED,
                {
                    "original_idea_id": original.idea_id,
                    "refined_idea_id": refined.idea_id,
                    "novelty_score": novelty,
                    "agent_id": agent_id,
                },
            )
            return refined

    def accept_idea(self, idea_id: str) -> Optional[CreativeIdea]:
        """Transition an idea to ACCEPTED status."""
        with self._lock:
            idea = self._ideas.get(idea_id)
            if idea is None:
                return None
            idea.status = IdeaStatus.ACCEPTED
            self._record_event(
                CreativityEventKind.IDEA_ACCEPTED,
                {"idea_id": idea_id, "title": idea.title},
            )
            return idea

    def reject_idea(self, idea_id: str) -> Optional[CreativeIdea]:
        """Transition an idea to REJECTED status."""
        with self._lock:
            idea = self._ideas.get(idea_id)
            if idea is None:
                return None
            idea.status = IdeaStatus.REJECTED
            self._record_event(
                CreativityEventKind.IDEA_REJECTED,
                {"idea_id": idea_id, "title": idea.title},
            )
            return idea

    def archive_idea(self, idea_id: str) -> Optional[CreativeIdea]:
        """Transition an idea to ARCHIVED status."""
        with self._lock:
            idea = self._ideas.get(idea_id)
            if idea is None:
                return None
            idea.status = IdeaStatus.ARCHIVED
            self._record_event(
                CreativityEventKind.IDEA_REJECTED,
                {"idea_id": idea_id, "title": idea.title, "archived": True},
            )
            return idea

    # ------------------------------------------------------------------
    # Ranking & Query
    # ------------------------------------------------------------------

    def list_top_ideas(
        self,
        domain: Optional[CreativeDomain] = None,
        count: int = 10,
        sort_by: str = "combined",
    ) -> List[CreativeIdea]:
        """Return the top ideas ranked by a chosen score dimension.

        ``sort_by`` may be one of ``"combined"``, ``"novelty"``,
        ``"usefulness"``, or ``"surprise"``. Results are returned in
        descending score order.
        """
        with self._lock:
            if isinstance(domain, str):
                try:
                    domain = CreativeDomain(domain)
                except ValueError:
                    domain = None

            valid_keys = {"combined", "novelty", "usefulness", "surprise"}
            key = sort_by if sort_by in valid_keys else "combined"

            field_map = {
                "combined": "combined_score",
                "novelty": "novelty_score",
                "usefulness": "usefulness_score",
                "surprise": "surprise_score",
            }
            attr = field_map[key]

            candidates: List[CreativeIdea] = []
            for idea in self._ideas.values():
                if domain is not None and idea.domain != domain:
                    continue
                candidates.append(idea)

            candidates.sort(key=lambda i: getattr(i, attr), reverse=True)
            limit = max(0, int(count))
            return candidates[:limit]

    # ------------------------------------------------------------------
    # Internal Helpers
    # ------------------------------------------------------------------

    def _compute_novelty(
        self,
        description: str,
        tags: List[str],
        domain: CreativeDomain,
    ) -> float:
        """Compute a novelty score in [0, 1] for a candidate idea.

        Novelty is the complement of similarity to existing ideas in
        the same domain. Similarity is the maximum token overlap of the
        description with any prior idea's description. Tag rarity adds
        a small bonus when the candidate uses tags that are uncommon
        within the domain.
        """
        # Collect prior ideas in the same domain.
        prior_in_domain: List[CreativeIdea] = [
            i for i in self._ideas.values() if i.domain == domain
        ]

        # Description uniqueness: 1 - max overlap with any prior idea.
        max_overlap = 0.0
        if prior_in_domain and description:
            for prior in prior_in_domain:
                overlap = _token_overlap(description, prior.description)
                if overlap > max_overlap:
                    max_overlap = overlap
                    if max_overlap >= 1.0:
                        break
        description_novelty = _clamp(1.0 - max_overlap, 0.0, 1.0)

        # Tag rarity: average rarity of the candidate's tags within the
        # domain. Rarer tags contribute more novelty.
        tag_rarity = 0.0
        if tags and prior_in_domain:
            # Frequency of each tag among prior ideas in this domain.
            tag_freq: Dict[str, int] = {}
            total_prior = len(prior_in_domain)
            for prior in prior_in_domain:
                for t in prior.tags:
                    tag_freq[t] = tag_freq.get(t, 0) + 1
            rarity_sum = 0.0
            for t in tags:
                freq = tag_freq.get(t, 0)
                # Rarity = 1 - normalized frequency; unseen tags are fully rare.
                rarity_sum += 1.0 - (freq / max(total_prior, 1))
            tag_rarity = rarity_sum / len(tags)
        elif tags and not prior_in_domain:
            # No prior art in this domain: any tag is maximally novel.
            tag_rarity = 1.0

        # Weighted blend: description uniqueness dominates, tag rarity
        # contributes the remainder.
        if tags:
            novelty = 0.7 * description_novelty + 0.3 * tag_rarity
        else:
            novelty = description_novelty
        return _clamp(novelty, 0.0, 1.0)

    def _assign_novelty_level(self, score: float) -> NoveltyLevel:
        """Map a numeric novelty score to a qualitative ``NoveltyLevel``."""
        if score < 0.2:
            return NoveltyLevel.MUNDANE
        if score < 0.4:
            return NoveltyLevel.CONVENTIONAL
        if score < 0.6:
            return NoveltyLevel.MILD_NOVEL
        if score < 0.8:
            return NoveltyLevel.NOVEL
        if score < 0.95:
            return NoveltyLevel.HIGHLY_NOVEL
        return NoveltyLevel.RADICAL

    def _record_event(
        self, kind: CreativityEventKind, payload: Dict[str, Any]
    ) -> None:
        """Record an observable creativity event.

        Assumes the caller already holds ``self._lock``. The event log
        is bounded by ``_MAX_EVENTS`` with FIFO eviction.
        """
        event = CreativityEvent(
            kind=kind,
            payload=dict(payload) if payload else {},
        )
        self._events.append(event)
        _evict_fifo_list(self._events, _MAX_EVENTS)

    # ------------------------------------------------------------------
    # Events, Stats, Status, Snapshot
    # ------------------------------------------------------------------

    def list_events(self, limit: int = 100) -> List[CreativityEvent]:
        """Return the most recent creativity events, newest first."""
        with self._lock:
            n = max(0, int(limit))
            if n == 0:
                return []
            # Events are appended in chronological order; return newest first.
            return list(reversed(self._events))[:n]

    def get_stats(self) -> CreativityStats:
        """Compute aggregate statistics across all creativity artifacts."""
        with self._lock:
            ideas = list(self._ideas.values())
            total = len(ideas)
            avg_novelty = 0.0
            avg_usefulness = 0.0
            avg_surprise = 0.0
            if total > 0:
                avg_novelty = sum(i.novelty_score for i in ideas) / total
                avg_usefulness = sum(i.usefulness_score for i in ideas) / total
                avg_surprise = sum(i.surprise_score for i in ideas) / total

            ideas_by_status: Dict[str, int] = {}
            ideas_by_domain: Dict[str, int] = {}
            for idea in ideas:
                s = idea.status.value
                ideas_by_status[s] = ideas_by_status.get(s, 0) + 1
                d = idea.domain.value
                ideas_by_domain[d] = ideas_by_domain.get(d, 0) + 1

            return CreativityStats(
                total_ideas=total,
                total_combinations=len(self._combinations),
                total_domains=len(self._domains),
                total_inspirations=len(self._inspirations),
                total_evaluations=len(self._evaluations),
                avg_novelty=round(avg_novelty, 4),
                avg_usefulness=round(avg_usefulness, 4),
                avg_surprise=round(avg_surprise, 4),
                ideas_by_status=ideas_by_status,
                ideas_by_domain=ideas_by_domain,
            )

    def get_status(self) -> Dict[str, Any]:
        """Return a comprehensive status dictionary for diagnostics.

        The ``initialized`` flag is always the first key.
        """
        with self._lock:
            ideas = list(self._ideas.values())
            status_counts: Dict[str, int] = {}
            domain_counts: Dict[str, int] = {}
            novelty_level_counts: Dict[str, int] = {}
            thinking_mode_counts: Dict[str, int] = {}
            for idea in ideas:
                status_counts[idea.status.value] = (
                    status_counts.get(idea.status.value, 0) + 1
                )
                domain_counts[idea.domain.value] = (
                    domain_counts.get(idea.domain.value, 0) + 1
                )
                novelty_level_counts[idea.novelty_level.value] = (
                    novelty_level_counts.get(idea.novelty_level.value, 0) + 1
                )
                thinking_mode_counts[idea.thinking_mode.value] = (
                    thinking_mode_counts.get(idea.thinking_mode.value, 0) + 1
                )

            inspiration_source_counts: Dict[str, int] = {}
            for insp in self._inspirations.values():
                src = insp.source.value
                inspiration_source_counts[src] = (
                    inspiration_source_counts.get(src, 0) + 1
                )

            return {
                "initialized": self._initialized,
                "total_ideas": len(self._ideas),
                "total_combinations": len(self._combinations),
                "total_domains": len(self._domains),
                "total_inspirations": len(self._inspirations),
                "total_evaluations": len(self._evaluations),
                "total_events": len(self._events),
                "idea_counter": self._idea_counter,
                "combination_counter": self._combination_counter,
                "domain_counter": self._domain_counter,
                "inspiration_counter": self._inspiration_counter,
                "evaluation_counter": self._evaluation_counter,
                "idea_status_distribution": status_counts,
                "idea_domain_distribution": domain_counts,
                "idea_novelty_level_distribution": novelty_level_counts,
                "idea_thinking_mode_distribution": thinking_mode_counts,
                "inspiration_source_distribution": inspiration_source_counts,
                "capacity_limits": {
                    "max_ideas": _MAX_IDEAS,
                    "max_combinations": _MAX_COMBINATIONS,
                    "max_domains": _MAX_DOMAINS,
                    "max_inspirations": _MAX_INSPIRATIONS,
                    "max_evaluations": _MAX_EVALUATIONS,
                    "max_events": _MAX_EVENTS,
                },
                "last_updated": _now(),
            }

    def get_snapshot(self) -> CreativitySnapshot:
        """Capture a point-in-time snapshot of the entire engine state."""
        with self._lock:
            stats = self.get_stats()
            return CreativitySnapshot(
                initialized=self._initialized,
                ideas=[i.to_dict() for i in self._ideas.values()],
                combinations=[c.to_dict() for c in self._combinations.values()],
                domains=[d.to_dict() for d in self._domains.values()],
                inspirations=[
                    i.to_dict() for i in self._inspirations.values()
                ],
                evaluations=[
                    e.to_dict() for e in self._evaluations.values()
                ],
                events=[ev.to_dict() for ev in self._events],
                stats=stats.to_dict(),
            )

    def reset(self) -> None:
        """Clear all stores and re-seed the engine with baseline data.

        The ``_initialized`` flag is preserved so that the singleton
        guard in ``__init__`` does not re-run. Counters are reset to
        zero before re-seeding.
        """
        with self._lock:
            self._ideas.clear()
            self._combinations.clear()
            self._domains.clear()
            self._inspirations.clear()
            self._evaluations.clear()
            self._events.clear()
            self._idea_counter = 0
            self._combination_counter = 0
            self._domain_counter = 0
            self._inspiration_counter = 0
            self._evaluation_counter = 0
            self._seed_data()


# ---------------------------------------------------------------------------
# Module-Level Accessor
# ---------------------------------------------------------------------------

def get_creativity_engine() -> CreativityEngine:
    """Return the singleton CreativityEngine instance."""
    return CreativityEngine.get_instance()
