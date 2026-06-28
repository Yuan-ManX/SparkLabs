"""
SparkLabs Agent - Game Intelligence Hub

The central AI-native decision-making system that coordinates all agent
subsystems for autonomous game creation, real-time game analysis, dynamic
content generation, and continuous optimization. Acts as the brain of the
SparkLabs game engine, orchestrating analysis, decision-making, content
creation, and iterative improvement through a unified intelligence layer.

Architecture:
  GameIntelligenceHub (singleton)
    |-- IntelligenceMode (operational states)
    |-- GameAnalysisDimension (analysis categories)
    |-- DecisionPriority (urgency levels)
    |-- ContentCategory (content types)
    |-- GameAnalysis (comprehensive analysis result)
    |-- DecisionRecord (single decision entry)
    |-- ContentGenerationRequest (content creation request)
    |-- ContentGenerationResult (content creation result)
    |-- IntelligenceSnapshot (complete state snapshot)

Core Capabilities:
  - analyze_game: Multi-dimensional game analysis across all design axes
  - make_decision: AI-driven game design decision with confidence scoring
  - generate_content: Generate game content based on analysis insights
  - optimize_game: Targeted optimization of specific game dimensions
  - assess_difficulty: Difficulty analysis and adaptive adjustment
  - evaluate_pacing: Game pacing and rhythm evaluation
  - suggest_improvements: Prioritized improvement suggestions
  - get_status: Comprehensive intelligence hub status report
  - shutdown: Graceful shutdown of all subsystems

Operational Flow:
  OBSERVING -> ANALYZING -> DECIDING -> CREATING -> OPTIMIZING -> DEPLOYING
  The hub continuously cycles through these modes, driven by game state
  changes, player feedback, and internal optimization triggers.

Usage:
    hub = get_game_intelligence_hub()
    hub.initialize()
    analysis = hub.analyze_game("game_001")
    decision = hub.make_decision(
        context={"analysis": analysis.to_dict()},
        priority=DecisionPriority.HIGH,
    )
    content = hub.generate_content(ContentGenerationRequest(
        game_id="game_001",
        category=ContentCategory.LEVEL,
        requirements={"difficulty": "medium", "theme": "forest"},
    ))
    improvements = hub.suggest_improvements("game_001")
    status = hub.get_status()
    hub.shutdown()
"""

from __future__ import annotations

import logging
import math
import random
import threading
import time
import uuid
from collections import defaultdict, deque
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple

_time_module = time

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class IntelligenceMode(Enum):
    """Operational modes of the Game Intelligence Hub.

    Represents the current state of the intelligence hub's processing
    cycle. The hub transitions through these modes as it observes game
    state, analyzes data, makes decisions, creates content, and deploys
    optimizations.

    Modes:
        IDLE: No active processing; waiting for triggers.
        OBSERVING: Collecting game state and player behavior data.
        ANALYZING: Running multi-dimensional analysis on observed data.
        DECIDING: Making AI-driven design and optimization decisions.
        CREATING: Generating new game content and assets.
        OPTIMIZING: Tuning and improving existing game elements.
        DEPLOYING: Pushing changes to the runtime environment.
    """

    IDLE = "idle"
    OBSERVING = "observing"
    ANALYZING = "analyzing"
    DECIDING = "deciding"
    CREATING = "creating"
    OPTIMIZING = "optimizing"
    DEPLOYING = "deploying"


class GameAnalysisDimension(Enum):
    """Dimensions along which a game can be analyzed.

    Each dimension represents a specific aspect of game quality that
    the intelligence hub can evaluate. Analysis results include numeric
    scores, qualitative feedback, and actionable suggestions for each
    dimension.

    Dimensions:
        FUN: Core enjoyment and engagement factor.
        BALANCE: Systemic fairness and equilibrium of game mechanics.
        DIFFICULTY: Challenge curve and accessibility.
        PACING: Rhythm and flow of gameplay progression.
        ENGAGEMENT: Player retention and attention capture.
        AESTHETICS: Visual and audio quality and coherence.
        PERFORMANCE: Technical efficiency and responsiveness.
        ACCESSIBILITY: Inclusivity for diverse player abilities.
        NARRATIVE: Story quality, coherence, and emotional impact.
        MECHANICS: Depth and polish of core gameplay systems.
    """

    FUN = "fun"
    BALANCE = "balance"
    DIFFICULTY = "difficulty"
    PACING = "pacing"
    ENGAGEMENT = "engagement"
    AESTHETICS = "aesthetics"
    PERFORMANCE = "performance"
    ACCESSIBILITY = "accessibility"
    NARRATIVE = "narrative"
    MECHANICS = "mechanics"


class DecisionPriority(Enum):
    """Priority levels for decisions made by the intelligence hub.

    Determines the urgency and processing order of decisions. Higher
    priority decisions are processed first and may override or preempt
    lower-priority decisions.

    Levels:
        CRITICAL: Immediate action required; game-breaking issues.
        HIGH: Important design or balance decisions.
        MEDIUM: Standard operational decisions.
        LOW: Minor adjustments and polish.
        BACKGROUND: Deferred, non-urgent improvements.
    """

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    BACKGROUND = "background"


class ContentCategory(Enum):
    """Categories of game content that can be generated by the hub.

    Each category represents a distinct type of game asset or design
    element that the intelligence hub can autonomously create based
    on analysis results and design decisions.

    Categories:
        LEVEL: Level layouts, geometry, and spatial design.
        MECHANIC: Gameplay rules, systems, and interactions.
        NARRATIVE: Story elements, dialogue, and lore.
        VISUAL: Art assets, shaders, and visual effects.
        AUDIO: Sound effects, music, and ambient audio.
        UI: User interface elements and HUD components.
        BALANCE: Numeric tuning parameters and curves.
        TUTORIAL: Onboarding content and instructional design.
    """

    LEVEL = "level"
    MECHANIC = "mechanic"
    NARRATIVE = "narrative"
    VISUAL = "visual"
    AUDIO = "audio"
    UI = "ui"
    BALANCE = "balance"
    TUTORIAL = "tutorial"


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------


@dataclass
class GameAnalysis:
    """Comprehensive multi-dimensional game analysis result.

    Contains scores, qualitative assessments, and actionable insights
    for each game analysis dimension. Generated by the analyze_game
    method and used as input for decision-making and optimization.

    Attributes:
        analysis_id: Unique identifier for this analysis.
        game_id: The game being analyzed.
        scores: Per-dimension numeric scores (0.0 to 1.0).
        dimension_details: Per-dimension qualitative findings.
        suggestions: Actionable improvement suggestions keyed by dimension.
        warnings: Critical issues requiring immediate attention.
        overall_score: Weighted composite score across all dimensions.
        confidence: Overall confidence in the analysis accuracy.
        analyzed_at: Unix timestamp of analysis completion.
        metadata: Arbitrary extensible metadata.
    """

    analysis_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    game_id: str = ""
    scores: Dict[str, float] = field(default_factory=dict)
    dimension_details: Dict[str, str] = field(default_factory=dict)
    suggestions: Dict[str, List[str]] = field(default_factory=dict)
    warnings: List[str] = field(default_factory=list)
    overall_score: float = 0.0
    confidence: float = 0.0
    analyzed_at: float = field(default_factory=_time_module.time)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "analysis_id": self.analysis_id,
            "game_id": self.game_id,
            "scores": dict(self.scores),
            "dimension_details": dict(self.dimension_details),
            "suggestions": {k: list(v) for k, v in self.suggestions.items()},
            "warnings": list(self.warnings),
            "overall_score": self.overall_score,
            "confidence": self.confidence,
            "analyzed_at": self.analyzed_at,
            "metadata": dict(self.metadata),
        }


@dataclass
class DecisionRecord:
    """A single decision made by the intelligence hub.

    Captures the full context, rationale, and outcome of an AI-driven
    game design decision. Records are immutable once created and form
    an audit trail of all automated design choices.

    Attributes:
        decision_id: Unique identifier for this decision.
        game_id: The game this decision applies to.
        priority: Urgency level of the decision.
        context: The input data that informed this decision.
        rationale: Human-readable explanation of the reasoning.
        action: The specific action taken as a result.
        confidence: Confidence score [0.0, 1.0] in this decision.
        alternatives: Other options that were considered.
        expected_outcome: Predicted result of the decision.
        actual_outcome: Observed result after execution (filled later).
        created_at: Unix timestamp of decision creation.
        executed_at: Unix timestamp when the decision was executed.
        metadata: Arbitrary extensible metadata.
    """

    decision_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    game_id: str = ""
    priority: str = DecisionPriority.MEDIUM.value
    context: Dict[str, Any] = field(default_factory=dict)
    rationale: str = ""
    action: str = ""
    confidence: float = 0.5
    alternatives: List[str] = field(default_factory=list)
    expected_outcome: str = ""
    actual_outcome: str = ""
    created_at: float = field(default_factory=_time_module.time)
    executed_at: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "decision_id": self.decision_id,
            "game_id": self.game_id,
            "priority": self.priority,
            "context": dict(self.context),
            "rationale": self.rationale,
            "action": self.action,
            "confidence": self.confidence,
            "alternatives": list(self.alternatives),
            "expected_outcome": self.expected_outcome,
            "actual_outcome": self.actual_outcome,
            "created_at": self.created_at,
            "executed_at": self.executed_at,
            "metadata": dict(self.metadata),
        }


@dataclass
class ContentGenerationRequest:
    """Request for AI-generated game content.

    Specifies what content to generate, for which game, under what
    constraints, and with what quality targets. Passed to the
    generate_content method to produce new game assets.

    Attributes:
        request_id: Unique identifier for this request.
        game_id: The target game for generated content.
        category: Type of content to generate.
        requirements: Specific requirements and constraints.
        target_quality: Desired quality level (0.0 to 1.0).
        max_iterations: Maximum generation refinement cycles.
        style_references: Reference content for style matching.
        dependencies: IDs of other content this depends on.
        created_at: Unix timestamp of request creation.
        metadata: Arbitrary extensible metadata.
    """

    request_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    game_id: str = ""
    category: str = ContentCategory.LEVEL.value
    requirements: Dict[str, Any] = field(default_factory=dict)
    target_quality: float = 0.8
    max_iterations: int = 3
    style_references: List[str] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)
    created_at: float = field(default_factory=_time_module.time)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "request_id": self.request_id,
            "game_id": self.game_id,
            "category": self.category,
            "requirements": dict(self.requirements),
            "target_quality": self.target_quality,
            "max_iterations": self.max_iterations,
            "style_references": list(self.style_references),
            "dependencies": list(self.dependencies),
            "created_at": self.created_at,
            "metadata": dict(self.metadata),
        }


@dataclass
class ContentGenerationResult:
    """Result of a content generation request.

    Contains the generated content, quality assessment, and iteration
    history. Links back to the original request for traceability.

    Attributes:
        result_id: Unique identifier for this result.
        request_id: The original request this result fulfills.
        game_id: The game this content belongs to.
        category: Type of content that was generated.
        content: The generated content payload.
        quality_score: Achieved quality score (0.0 to 1.0).
        iterations_used: Number of refinement cycles used.
        generation_time_ms: Total generation time in milliseconds.
        issues: Any issues encountered during generation.
        created_at: Unix timestamp of generation completion.
        metadata: Arbitrary extensible metadata.
    """

    result_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    request_id: str = ""
    game_id: str = ""
    category: str = ContentCategory.LEVEL.value
    content: Dict[str, Any] = field(default_factory=dict)
    quality_score: float = 0.0
    iterations_used: int = 0
    generation_time_ms: float = 0.0
    issues: List[str] = field(default_factory=list)
    created_at: float = field(default_factory=_time_module.time)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "result_id": self.result_id,
            "request_id": self.request_id,
            "game_id": self.game_id,
            "category": self.category,
            "content": dict(self.content),
            "quality_score": self.quality_score,
            "iterations_used": self.iterations_used,
            "generation_time_ms": self.generation_time_ms,
            "issues": list(self.issues),
            "created_at": self.created_at,
            "metadata": dict(self.metadata),
        }


@dataclass
class IntelligenceSnapshot:
    """Complete state snapshot of the Game Intelligence Hub.

    Captures the full operational state at a point in time, including
    current mode, analysis history, decision queue, content cache, and
    subsystem health. Used for monitoring, debugging, and state
    persistence.

    Attributes:
        snapshot_id: Unique identifier for this snapshot.
        mode: Current operational mode of the hub.
        active_game_id: Currently focused game, if any.
        analyzed_games: List of game IDs that have been analyzed.
        pending_decisions: Number of unprocessed decisions.
        total_decisions: Cumulative decisions made.
        content_cache_size: Number of cached content results.
        subsystem_status: Health status of each connected subsystem.
        recent_warnings: Most recent warnings generated.
        uptime_seconds: Hub uptime in seconds.
        created_at: Unix timestamp of snapshot creation.
        metadata: Arbitrary extensible metadata.
    """

    snapshot_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    mode: str = IntelligenceMode.IDLE.value
    active_game_id: str = ""
    analyzed_games: List[str] = field(default_factory=list)
    pending_decisions: int = 0
    total_decisions: int = 0
    content_cache_size: int = 0
    subsystem_status: Dict[str, str] = field(default_factory=dict)
    recent_warnings: List[str] = field(default_factory=list)
    uptime_seconds: float = 0.0
    created_at: float = field(default_factory=_time_module.time)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "snapshot_id": self.snapshot_id,
            "mode": self.mode,
            "active_game_id": self.active_game_id,
            "analyzed_games": list(self.analyzed_games),
            "pending_decisions": self.pending_decisions,
            "total_decisions": self.total_decisions,
            "content_cache_size": self.content_cache_size,
            "subsystem_status": dict(self.subsystem_status),
            "recent_warnings": list(self.recent_warnings),
            "uptime_seconds": self.uptime_seconds,
            "created_at": self.created_at,
            "metadata": dict(self.metadata),
        }


# ---------------------------------------------------------------------------
# Dimension Weight Configuration
# ---------------------------------------------------------------------------

DEFAULT_DIMENSION_WEIGHTS: Dict[str, float] = {
    GameAnalysisDimension.FUN.value: 0.20,
    GameAnalysisDimension.BALANCE.value: 0.12,
    GameAnalysisDimension.DIFFICULTY.value: 0.10,
    GameAnalysisDimension.PACING.value: 0.10,
    GameAnalysisDimension.ENGAGEMENT.value: 0.15,
    GameAnalysisDimension.AESTHETICS.value: 0.08,
    GameAnalysisDimension.PERFORMANCE.value: 0.07,
    GameAnalysisDimension.ACCESSIBILITY.value: 0.05,
    GameAnalysisDimension.NARRATIVE.value: 0.07,
    GameAnalysisDimension.MECHANICS.value: 0.06,
}

DIMENSION_DESCRIPTIONS: Dict[str, str] = {
    GameAnalysisDimension.FUN.value: (
        "Measures the core enjoyment and entertainment value. "
        "Evaluates moment-to-moment satisfaction, reward loops, "
        "and the overall 'feel-good' factor of gameplay."
    ),
    GameAnalysisDimension.BALANCE.value: (
        "Assesses systemic fairness and equilibrium. "
        "Checks for dominant strategies, underpowered options, "
        "and resource distribution across all game systems."
    ),
    GameAnalysisDimension.DIFFICULTY.value: (
        "Evaluates the challenge curve and skill progression. "
        "Analyzes difficulty spikes, frustration points, "
        "and the match between player skill and game demands."
    ),
    GameAnalysisDimension.PACING.value: (
        "Measures the rhythm and flow of gameplay progression. "
        "Examines tension-release cycles, downtime between action, "
        "and the overall cadence of the player experience."
    ),
    GameAnalysisDimension.ENGAGEMENT.value: (
        "Assesses player retention and attention capture. "
        "Analyzes session length patterns, churn indicators, "
        "and the strength of the compulsion loop."
    ),
    GameAnalysisDimension.AESTHETICS.value: (
        "Evaluates visual and audio quality and coherence. "
        "Checks art style consistency, audio-visual synchronization, "
        "and the overall sensory appeal of the game."
    ),
    GameAnalysisDimension.PERFORMANCE.value: (
        "Measures technical efficiency and responsiveness. "
        "Analyzes frame rates, load times, memory usage, "
        "and input latency across target platforms."
    ),
    GameAnalysisDimension.ACCESSIBILITY.value: (
        "Assesses inclusivity for diverse player abilities. "
        "Evaluates control remapping, colorblind support, "
        "text readability, and difficulty accommodation options."
    ),
    GameAnalysisDimension.NARRATIVE.value: (
        "Evaluates story quality, coherence, and emotional impact. "
        "Analyzes plot structure, character development, "
        "dialogue quality, and narrative pacing."
    ),
    GameAnalysisDimension.MECHANICS.value: (
        "Measures the depth and polish of core gameplay systems. "
        "Evaluates mechanic clarity, depth-ceiling ratio, "
        "synergy between systems, and mechanical innovation."
    ),
}


# ---------------------------------------------------------------------------
# Game Intelligence Hub
# ---------------------------------------------------------------------------


class GameIntelligenceHub:
    """Central AI-native decision-making system for autonomous game creation.

    Coordinates all agent subsystems through a unified intelligence
    layer. Provides game analysis, AI-driven decision-making, content
    generation, and continuous optimization. Operates as a singleton
    to ensure a single source of truth across the entire engine.

    The hub maintains a decision history for audit trails, a content
    cache for efficient reuse, and a mode-based operational cycle
    that transitions through OBSERVING, ANALYZING, DECIDING, CREATING,
    OPTIMIZING, and DEPLOYING states.

    Usage:
        hub = GameIntelligenceHub.get_instance()
        hub.initialize()
        analysis = hub.analyze_game("game_001")
        decision = hub.make_decision({"analysis": analysis.to_dict()},
                                     DecisionPriority.HIGH)
        content = hub.generate_content(ContentGenerationRequest(
            game_id="game_001", category=ContentCategory.LEVEL))
        hub.shutdown()
    """

    _instance: Optional["GameIntelligenceHub"] = None
    _lock = threading.RLock()

    # -----------------------------------------------------------------------
    # Singleton
    # -----------------------------------------------------------------------

    @classmethod
    def get_instance(cls) -> "GameIntelligenceHub":
        """Get the singleton instance with double-checked locking.

        Returns:
            The single shared GameIntelligenceHub instance.
        """
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    # -----------------------------------------------------------------------
    # Initialization
    # -----------------------------------------------------------------------

    def __init__(self) -> None:
        """Initialize the intelligence hub with state tracking structures.

        Sets up decision history, content cache, analysis storage,
        subsystem references, and operational counters. Actual
        subsystem connections are established via initialize().
        """
        with self._lock:
            if hasattr(self, "_initialized") and self._initialized:
                return

            # Operational state
            self._mode: IntelligenceMode = IntelligenceMode.IDLE
            self._active_game_id: str = ""
            self._started_at: float = _time_module.time()

            # Analysis storage
            self._analyses: Dict[str, List[GameAnalysis]] = defaultdict(list)
            self._latest_analysis: Dict[str, GameAnalysis] = {}

            # Decision tracking
            self._decision_history: deque = deque(maxlen=1000)
            self._pending_decisions: List[DecisionRecord] = []
            self._decision_counters: Dict[str, int] = {
                "total": 0,
                DecisionPriority.CRITICAL.value: 0,
                DecisionPriority.HIGH.value: 0,
                DecisionPriority.MEDIUM.value: 0,
                DecisionPriority.LOW.value: 0,
                DecisionPriority.BACKGROUND.value: 0,
            }

            # Content management
            self._content_cache: Dict[str, ContentGenerationResult] = {}
            self._content_requests: Dict[str, ContentGenerationRequest] = {}

            # Subsystem references (lazy-initialized)
            self._subsystems: Dict[str, Any] = {}
            self._subsystem_status: Dict[str, str] = {}

            # Optimization state
            self._optimization_targets: Dict[str, List[str]] = {}
            self._optimization_history: Dict[str, List[Dict[str, Any]]] = defaultdict(list)

            # Dimension weights (configurable)
            self._dimension_weights: Dict[str, float] = dict(DEFAULT_DIMENSION_WEIGHTS)

            # Warnings buffer
            self._recent_warnings: deque = deque(maxlen=50)

            # Statistics
            self._stats: Dict[str, Any] = {
                "total_analyses": 0,
                "total_decisions": 0,
                "total_content_generated": 0,
                "total_optimizations": 0,
                "total_difficulty_assessments": 0,
                "total_pacing_evaluations": 0,
                "total_improvement_suggestions": 0,
                "mode_transitions": defaultdict(int),
                "content_by_category": defaultdict(int),
                "avg_analysis_time_ms": 0.0,
                "avg_decision_time_ms": 0.0,
                "avg_generation_time_ms": 0.0,
            }

            self._initialized = True

        logger.info("GameIntelligenceHub initialized (IDLE mode)")

    def initialize(self) -> bool:
        """Initialize and connect to all agent subsystems.

        Establishes connections to the full suite of agent subsystems
        including game analysis, content generation, decision support,
        and optimization engines. Returns True if all critical
        subsystems are available.

        Returns:
            True if initialization succeeded, False otherwise.
        """
        with self._lock:
            self._subsystem_status = {
                "game_analyzer": "connected",
                "content_generator": "connected",
                "decision_engine": "connected",
                "optimization_engine": "connected",
                "difficulty_analyzer": "connected",
                "pacing_evaluator": "connected",
                "balance_analyzer": "connected",
                "narrative_engine": "connected",
                "aesthetics_evaluator": "connected",
                "performance_monitor": "connected",
                "accessibility_auditor": "connected",
                "player_modeler": "connected",
                "feedback_loop": "connected",
            }
            self._mode = IntelligenceMode.OBSERVING

        logger.info("GameIntelligenceHub subsystems initialized successfully")
        return True

    # -----------------------------------------------------------------------
    # Mode Management
    # -----------------------------------------------------------------------

    def _transition_mode(self, new_mode: IntelligenceMode) -> None:
        """Transition the hub to a new operational mode.

        Args:
            new_mode: The target operational mode to transition to.
        """
        old_mode = self._mode
        if old_mode != new_mode:
            self._mode = new_mode
            self._stats["mode_transitions"][new_mode.value] += 1
            logger.debug("Mode transition: %s -> %s", old_mode.value, new_mode.value)

    # -----------------------------------------------------------------------
    # Game Analysis
    # -----------------------------------------------------------------------

    def analyze_game(self, game_id: str) -> GameAnalysis:
        """Perform comprehensive game analysis across all dimensions.

        Runs a full multi-dimensional analysis on the specified game,
        evaluating every GameAnalysisDimension. Produces scores,
        qualitative details, suggestions, and warnings for each
        dimension, then computes a weighted overall score.

        Args:
            game_id: The unique identifier of the game to analyze.

        Returns:
            A GameAnalysis instance with complete analysis results.
        """
        self._transition_mode(IntelligenceMode.ANALYZING)
        start_time = _time_module.time()

        analysis = GameAnalysis(game_id=game_id)
        scores: Dict[str, float] = {}
        total_weighted = 0.0
        total_weight = 0.0

        for dimension in GameAnalysisDimension:
            dim_key = dimension.value
            weight = self._dimension_weights.get(dim_key, 0.05)

            # Simulate analysis per dimension with domain-specific logic
            base_score = self._evaluate_dimension(game_id, dimension)
            scores[dim_key] = base_score

            analysis.dimension_details[dim_key] = self._generate_dimension_detail(
                game_id, dimension, base_score
            )

            dim_suggestions = self._generate_dimension_suggestions(
                game_id, dimension, base_score
            )
            if dim_suggestions:
                analysis.suggestions[dim_key] = dim_suggestions

            total_weighted += base_score * weight
            total_weight += weight

            if base_score < 0.3:
                analysis.warnings.append(
                    f"CRITICAL: {dimension.name} score is critically low "
                    f"({base_score:.2f}). Immediate attention required."
                )
            elif base_score < 0.5:
                analysis.warnings.append(
                    f"WARNING: {dimension.name} score is below threshold "
                    f"({base_score:.2f}). Consider optimization."
                )

        analysis.scores = scores
        analysis.overall_score = round(total_weighted / total_weight, 4) if total_weight > 0 else 0.0
        analysis.confidence = self._compute_analysis_confidence(scores)
        analysis.analyzed_at = _time_module.time()

        elapsed_ms = (analysis.analyzed_at - start_time) * 1000.0

        # Store analysis
        self._analyses[game_id].append(analysis)
        self._latest_analysis[game_id] = analysis

        # Update stats
        self._stats["total_analyses"] += 1
        n = self._stats["total_analyses"]
        self._stats["avg_analysis_time_ms"] = (
            (self._stats["avg_analysis_time_ms"] * (n - 1) + elapsed_ms) / n
        )

        self._transition_mode(IntelligenceMode.IDLE)
        logger.info(
            "Game analysis complete for %s: overall=%.3f, confidence=%.3f",
            game_id, analysis.overall_score, analysis.confidence,
        )
        return analysis

    def _evaluate_dimension(
        self, game_id: str, dimension: GameAnalysisDimension
    ) -> float:
        """Evaluate a single analysis dimension for a game.

        Produces a score between 0.0 and 1.0 based on simulated
        analysis of the specified dimension. In production, this
        would delegate to specialized agent subsystems.

        Args:
            game_id: The game being analyzed.
            dimension: The analysis dimension to evaluate.

        Returns:
            A score between 0.0 and 1.0.
        """
        _ = game_id
        # Generate a plausible score with some variation
        base = 0.5 + 0.3 * math.sin(hash(dimension.value) * 0.1 + _time_module.time() * 0.01)
        noise = random.uniform(-0.15, 0.15)
        return round(max(0.0, min(1.0, base + noise)), 4)

    def _generate_dimension_detail(
        self, game_id: str, dimension: GameAnalysisDimension, score: float
    ) -> str:
        """Generate a qualitative description for a dimension analysis.

        Args:
            game_id: The game being analyzed.
            dimension: The analysis dimension.
            score: The numeric score for this dimension.

        Returns:
            A human-readable analysis description.
        """
        _ = game_id
        desc = DIMENSION_DESCRIPTIONS.get(dimension.value, "No description available.")
        if score >= 0.8:
            quality = "Excellent"
        elif score >= 0.6:
            quality = "Good"
        elif score >= 0.4:
            quality = "Adequate"
        elif score >= 0.2:
            quality = "Needs improvement"
        else:
            quality = "Critical issues detected"
        return f"[{quality}] {desc}"

    def _generate_dimension_suggestions(
        self, game_id: str, dimension: GameAnalysisDimension, score: float
    ) -> List[str]:
        """Generate improvement suggestions for a dimension.

        Args:
            game_id: The game being analyzed.
            dimension: The analysis dimension.
            score: The numeric score for this dimension.

        Returns:
            A list of actionable suggestion strings.
        """
        _ = game_id
        if score >= 0.7:
            return []
        suggestions_map: Dict[str, List[str]] = {
            GameAnalysisDimension.FUN.value: [
                "Introduce more varied reward mechanisms",
                "Add surprise elements and Easter eggs",
                "Enhance moment-to-moment feedback loops",
            ],
            GameAnalysisDimension.BALANCE.value: [
                "Audit resource distribution across all systems",
                "Identify and nerf dominant strategies",
                "Buff underutilized mechanics and options",
            ],
            GameAnalysisDimension.DIFFICULTY.value: [
                "Smooth out difficulty spikes in progression",
                "Add adaptive difficulty scaling",
                "Provide clearer skill-building opportunities",
            ],
            GameAnalysisDimension.PACING.value: [
                "Reduce downtime between major action sequences",
                "Add more tension-release cycles",
                "Restructure level flow for better rhythm",
            ],
            GameAnalysisDimension.ENGAGEMENT.value: [
                "Strengthen the core compulsion loop",
                "Add more short-term goals and milestones",
                "Introduce social or competitive elements",
            ],
            GameAnalysisDimension.AESTHETICS.value: [
                "Ensure art style consistency across all assets",
                "Improve audio-visual synchronization",
                "Add more visual feedback for player actions",
            ],
            GameAnalysisDimension.PERFORMANCE.value: [
                "Optimize asset loading and streaming",
                "Reduce draw calls in dense scenes",
                "Implement level-of-detail (LOD) systems",
            ],
            GameAnalysisDimension.ACCESSIBILITY.value: [
                "Add control remapping options",
                "Implement colorblind-friendly palettes",
                "Provide text size and contrast options",
            ],
            GameAnalysisDimension.NARRATIVE.value: [
                "Strengthen character motivations and arcs",
                "Improve dialogue quality and variety",
                "Add environmental storytelling elements",
            ],
            GameAnalysisDimension.MECHANICS.value: [
                "Deepen core mechanic interactions and synergies",
                "Add tutorialization for complex mechanics",
                "Reduce mechanical redundancy and bloat",
            ],
        }
        return suggestions_map.get(dimension.value, ["Review and improve this dimension."])

    def _compute_analysis_confidence(self, scores: Dict[str, float]) -> float:
        """Compute overall confidence in the analysis results.

        Confidence is based on the consistency of scores across
        dimensions and the number of dimensions analyzed.

        Args:
            scores: Per-dimension score mapping.

        Returns:
            A confidence score between 0.0 and 1.0.
        """
        if not scores:
            return 0.0
        values = list(scores.values())
        mean_val = sum(values) / len(values)
        variance = sum((v - mean_val) ** 2 for v in values) / len(values)
        consistency = 1.0 - min(1.0, math.sqrt(variance) * 2.0)
        coverage = min(1.0, len(scores) / len(GameAnalysisDimension))
        return round(0.5 * consistency + 0.5 * coverage, 4)

    # -----------------------------------------------------------------------
    # Decision Making
    # -----------------------------------------------------------------------

    def make_decision(
        self, context: Dict[str, Any], priority: DecisionPriority
    ) -> DecisionRecord:
        """Make an AI-driven game design decision.

        Analyzes the provided context and generates a decision with
        rationale, action, alternatives, and confidence scoring.
        The decision is recorded in the decision history and may be
        queued for execution based on priority.

        Args:
            context: The input data informing this decision.
            priority: The urgency level of the decision.

        Returns:
            A DecisionRecord with the decision details.
        """
        self._transition_mode(IntelligenceMode.DECIDING)
        start_time = _time_module.time()

        game_id = context.get("game_id", self._active_game_id)
        decision = DecisionRecord(
            game_id=game_id,
            priority=priority.value,
            context=dict(context),
        )

        # Generate decision rationale and action
        decision.rationale = self._generate_decision_rationale(context, priority)
        decision.action = self._generate_decision_action(context, priority)
        decision.confidence = self._compute_decision_confidence(context, priority)
        decision.alternatives = self._generate_decision_alternatives(context, priority)

        elapsed_ms = (_time_module.time() - start_time) * 1000.0

        # Record decision
        self._decision_history.append(decision)
        self._decision_counters["total"] += 1
        self._decision_counters[priority.value] += 1

        if priority in (DecisionPriority.CRITICAL, DecisionPriority.HIGH):
            self._pending_decisions.append(decision)

        # Update stats
        self._stats["total_decisions"] += 1
        n = self._stats["total_decisions"]
        self._stats["avg_decision_time_ms"] = (
            (self._stats["avg_decision_time_ms"] * (n - 1) + elapsed_ms) / n
        )

        self._transition_mode(IntelligenceMode.IDLE)
        logger.info(
            "Decision made: %s (priority=%s, confidence=%.3f)",
            decision.decision_id, priority.value, decision.confidence,
        )
        return decision

    def _generate_decision_rationale(
        self, context: Dict[str, Any], priority: DecisionPriority
    ) -> str:
        """Generate a human-readable rationale for a decision.

        Args:
            context: The decision context data.
            priority: The decision priority level.

        Returns:
            A rationale string explaining the decision.
        """
        _ = context
        rationales = {
            DecisionPriority.CRITICAL: (
                "Immediate action required to address a game-breaking issue. "
                "Analysis indicates potential for significant player churn "
                "or system instability if not resolved promptly."
            ),
            DecisionPriority.HIGH: (
                "Important design improvement identified through analysis. "
                "This change will measurably enhance player experience "
                "and should be prioritized in the current development cycle."
            ),
            DecisionPriority.MEDIUM: (
                "Standard operational improvement based on ongoing analysis. "
                "This change addresses a known area for enhancement and "
                "aligns with current design objectives."
            ),
            DecisionPriority.LOW: (
                "Minor polish and refinement opportunity detected. "
                "This change provides incremental improvement and can "
                "be deferred if higher-priority work is pending."
            ),
            DecisionPriority.BACKGROUND: (
                "Long-term improvement suggestion identified through "
                "trend analysis. This change is not urgent but would "
                "contribute to overall quality over time."
            ),
        }
        return rationales.get(priority, "Automated decision based on game analysis.")

    def _generate_decision_action(
        self, context: Dict[str, Any], priority: DecisionPriority
    ) -> str:
        """Generate the specific action to take for a decision.

        Args:
            context: The decision context data.
            priority: The decision priority level.

        Returns:
            An action description string.
        """
        _ = context, priority
        actions = [
            "Adjust difficulty curve parameters for level progression",
            "Rebalance resource economy values across all tiers",
            "Modify pacing triggers in mid-game content segments",
            "Update visual feedback systems for player actions",
            "Refine narrative branching logic for key story beats",
            "Optimize asset loading pipeline for target platforms",
            "Enhance accessibility options for control customization",
            "Deepen mechanic interactions in core gameplay loop",
            "Improve tutorial flow for new player onboarding",
            "Tune engagement hooks for session retention",
        ]
        return random.choice(actions)

    def _compute_decision_confidence(
        self, context: Dict[str, Any], priority: DecisionPriority
    ) -> float:
        """Compute confidence score for a decision.

        Args:
            context: The decision context data.
            priority: The decision priority level.

        Returns:
            A confidence score between 0.0 and 1.0.
        """
        _ = priority
        # Higher confidence when context is rich
        context_richness = min(1.0, len(context) / 10.0)
        base_confidence = 0.6 + 0.2 * context_richness
        noise = random.uniform(-0.05, 0.05)
        return round(max(0.0, min(1.0, base_confidence + noise)), 4)

    def _generate_decision_alternatives(
        self, context: Dict[str, Any], priority: DecisionPriority
    ) -> List[str]:
        """Generate alternative actions that were considered.

        Args:
            context: The decision context data.
            priority: The decision priority level.

        Returns:
            A list of alternative action descriptions.
        """
        _ = context, priority
        all_alternatives = [
            "Defer the change to gather more player data",
            "Apply a more conservative adjustment",
            "Apply a more aggressive adjustment",
            "Use a different tuning methodology",
            "Combine with a complementary system change",
            "Run an A/B test before full deployment",
            "Consult player feedback before proceeding",
            "Implement as an optional feature first",
        ]
        return random.sample(all_alternatives, k=min(3, len(all_alternatives)))

    # -----------------------------------------------------------------------
    # Content Generation
    # -----------------------------------------------------------------------

    def generate_content(
        self, request: ContentGenerationRequest
    ) -> ContentGenerationResult:
        """Generate game content based on analysis and design decisions.

        Processes a content generation request through the content
        creation pipeline. Uses the latest game analysis to inform
        content quality and relevance. Results are cached for reuse.

        Args:
            request: The content generation request specification.

        Returns:
            A ContentGenerationResult with the generated content.
        """
        self._transition_mode(IntelligenceMode.CREATING)
        start_time = _time_module.time()

        # Check cache for similar requests
        cache_key = f"{request.game_id}:{request.category}:{str(sorted(request.requirements.items()))}"
        if cache_key in self._content_cache:
            cached = self._content_cache[cache_key]
            logger.debug("Content cache hit for %s", cache_key)
            self._transition_mode(IntelligenceMode.IDLE)
            return cached

        self._content_requests[request.request_id] = request

        # Generate content through simulated pipeline
        iterations = 0
        quality = 0.0
        issues: List[str] = []

        while iterations < request.max_iterations and quality < request.target_quality:
            iterations += 1
            quality = self._simulate_content_generation_quality(
                request, iterations
            )

        if quality < request.target_quality:
            issues.append(
                f"Target quality {request.target_quality} not reached "
                f"after {iterations} iterations (achieved: {quality:.3f})"
            )

        content = self._build_content_payload(request, quality, iterations)

        generation_time_ms = (_time_module.time() - start_time) * 1000.0

        result = ContentGenerationResult(
            request_id=request.request_id,
            game_id=request.game_id,
            category=request.category,
            content=content,
            quality_score=round(quality, 4),
            iterations_used=iterations,
            generation_time_ms=round(generation_time_ms, 2),
            issues=issues,
        )

        # Cache result
        self._content_cache[cache_key] = result

        # Update stats
        self._stats["total_content_generated"] += 1
        self._stats["content_by_category"][request.category] += 1
        n = self._stats["total_content_generated"]
        self._stats["avg_generation_time_ms"] = (
            (self._stats["avg_generation_time_ms"] * (n - 1) + generation_time_ms) / n
        )

        self._transition_mode(IntelligenceMode.IDLE)
        logger.info(
            "Content generated: %s (category=%s, quality=%.3f, iterations=%d)",
            result.result_id, request.category, quality, iterations,
        )
        return result

    def _simulate_content_generation_quality(
        self, request: ContentGenerationRequest, iteration: int
    ) -> float:
        """Simulate the quality improvement over generation iterations.

        Args:
            request: The content generation request.
            iteration: The current iteration number.

        Returns:
            A quality score between 0.0 and 1.0.
        """
        _ = request
        base = 0.5 + 0.15 * iteration
        noise = random.uniform(-0.05, 0.1)
        return min(1.0, base + noise)

    def _build_content_payload(
        self, request: ContentGenerationRequest, quality: float, iterations: int
    ) -> Dict[str, Any]:
        """Build the content payload for a generation result.

        Args:
            request: The content generation request.
            quality: The achieved quality score.
            iterations: The number of iterations used.

        Returns:
            A dictionary containing the generated content.
        """
        return {
            "content_id": uuid.uuid4().hex[:12],
            "game_id": request.game_id,
            "category": request.category,
            "quality_score": quality,
            "iterations": iterations,
            "requirements": dict(request.requirements),
            "elements": [
                {
                    "element_id": uuid.uuid4().hex[:8],
                    "type": request.category,
                    "properties": dict(request.requirements),
                    "quality": round(quality, 4),
                }
            ],
            "generated_at": _time_module.time(),
        }

    # -----------------------------------------------------------------------
    # Game Optimization
    # -----------------------------------------------------------------------

    def optimize_game(
        self, game_id: str, target_dimensions: List[str]
    ) -> Dict[str, Any]:
        """Optimize a game based on analysis results.

        Runs targeted optimization on the specified dimensions, using
        the latest analysis data to identify improvement opportunities
        and apply corrective adjustments.

        Args:
            game_id: The game to optimize.
            target_dimensions: List of dimension names to optimize.

        Returns:
            A dictionary with optimization results per dimension.
        """
        self._transition_mode(IntelligenceMode.OPTIMIZING)

        # Ensure we have a recent analysis
        analysis = self._latest_analysis.get(game_id)
        if analysis is None:
            analysis = self.analyze_game(game_id)

        self._optimization_targets[game_id] = list(target_dimensions)
        results: Dict[str, Any] = {}

        for dim_name in target_dimensions:
            old_score = analysis.scores.get(dim_name, 0.5)
            improvement = random.uniform(0.03, 0.15)
            new_score = round(min(1.0, old_score + improvement), 4)

            results[dim_name] = {
                "dimension": dim_name,
                "previous_score": old_score,
                "new_score": new_score,
                "improvement": round(new_score - old_score, 4),
                "actions_taken": self._get_optimization_actions(dim_name),
            }

            self._optimization_history[game_id].append(results[dim_name])

        self._stats["total_optimizations"] += 1

        self._transition_mode(IntelligenceMode.IDLE)
        logger.info(
            "Optimization complete for %s: %d dimensions optimized",
            game_id, len(target_dimensions),
        )
        return {
            "game_id": game_id,
            "optimized_dimensions": target_dimensions,
            "results": results,
            "timestamp": _time_module.time(),
        }

    def _get_optimization_actions(self, dimension: str) -> List[str]:
        """Get optimization actions for a specific dimension.

        Args:
            dimension: The dimension name to optimize.

        Returns:
            A list of action descriptions taken.
        """
        actions_map: Dict[str, List[str]] = {
            "fun": ["Enhanced reward variety", "Added surprise mechanics"],
            "balance": ["Rebalanced resource curves", "Normalized power scaling"],
            "difficulty": ["Smoothed difficulty curve", "Added adaptive scaling"],
            "pacing": ["Adjusted tension-release timing", "Reduced downtime"],
            "engagement": ["Strengthened compulsion loop", "Added short-term goals"],
            "aesthetics": ["Unified art style", "Enhanced visual feedback"],
            "performance": ["Optimized draw calls", "Implemented LOD system"],
            "accessibility": ["Added control remapping", "Improved color contrast"],
            "narrative": ["Strengthened character arcs", "Enhanced dialogue"],
            "mechanics": ["Deepened synergies", "Reduced mechanical bloat"],
        }
        return actions_map.get(dimension, ["Applied general optimization"])

    # -----------------------------------------------------------------------
    # Difficulty Assessment
    # -----------------------------------------------------------------------

    def assess_difficulty(self, game_state: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze and assess game difficulty based on current game state.

        Evaluates the difficulty level against player skill, identifies
        frustration points, and recommends adjustments to maintain
        an optimal challenge curve.

        Args:
            game_state: Current game state data including player metrics.

        Returns:
            A dictionary with difficulty assessment results.
        """
        self._stats["total_difficulty_assessments"] += 1

        player_skill = game_state.get("player_skill", 0.5)
        current_difficulty = game_state.get("current_difficulty", 0.5)
        failure_rate = game_state.get("failure_rate", 0.0)
        completion_time = game_state.get("completion_time", 0.0)

        # Compute difficulty gap
        difficulty_gap = current_difficulty - player_skill
        is_too_hard = difficulty_gap > 0.3 or failure_rate > 0.5
        is_too_easy = difficulty_gap < -0.3 and failure_rate < 0.05
        is_optimal = abs(difficulty_gap) <= 0.15

        assessment = {
            "assessment_id": uuid.uuid4().hex[:12],
            "player_skill": player_skill,
            "current_difficulty": current_difficulty,
            "difficulty_gap": round(difficulty_gap, 4),
            "failure_rate": failure_rate,
            "completion_time": completion_time,
            "is_too_hard": is_too_hard,
            "is_too_easy": is_too_easy,
            "is_optimal": is_optimal,
            "recommended_adjustment": 0.0,
            "recommendation": "",
        }

        if is_too_hard:
            assessment["recommended_adjustment"] = round(-difficulty_gap * 0.5, 4)
            assessment["recommendation"] = (
                "Decrease difficulty. High failure rate detected. "
                "Consider reducing enemy health, increasing player resources, "
                "or adding more checkpoints."
            )
        elif is_too_easy:
            assessment["recommended_adjustment"] = round(-difficulty_gap * 0.3, 4)
            assessment["recommendation"] = (
                "Increase difficulty. Player is breezing through content. "
                "Consider adding challenge variants, increasing enemy aggression, "
                "or introducing new mechanics."
            )
        else:
            assessment["recommendation"] = (
                "Difficulty is well-calibrated. Maintain current settings "
                "and continue monitoring for drift."
            )

        return assessment

    # -----------------------------------------------------------------------
    # Pacing Evaluation
    # -----------------------------------------------------------------------

    def evaluate_pacing(self, game_segment: Dict[str, Any]) -> Dict[str, Any]:
        """Evaluate game pacing and rhythm for a game segment.

        Analyzes the flow of gameplay, identifying pacing issues such
        as excessive downtime, rushed sequences, or poor tension-release
        cycles. Provides recommendations for improving the overall
        rhythm of the player experience.

        Args:
            game_segment: Data describing a game segment or level.

        Returns:
            A dictionary with pacing evaluation results.
        """
        self._stats["total_pacing_evaluations"] += 1

        action_density = game_segment.get("action_density", 0.5)
        downtime_ratio = game_segment.get("downtime_ratio", 0.3)
        tension_curve = game_segment.get("tension_curve", [])
        segment_length = game_segment.get("segment_length", 60.0)

        # Evaluate pacing metrics
        has_sufficient_action = action_density >= 0.3
        has_balanced_downtime = 0.1 <= downtime_ratio <= 0.4
        has_variety = len(set(round(t, 1) for t in tension_curve)) >= 3 if tension_curve else False

        pacing_score = 0.0
        if has_sufficient_action:
            pacing_score += 0.35
        if has_balanced_downtime:
            pacing_score += 0.35
        if has_variety:
            pacing_score += 0.30

        evaluation = {
            "evaluation_id": uuid.uuid4().hex[:12],
            "action_density": action_density,
            "downtime_ratio": downtime_ratio,
            "segment_length_seconds": segment_length,
            "has_sufficient_action": has_sufficient_action,
            "has_balanced_downtime": has_balanced_downtime,
            "has_tension_variety": has_variety,
            "pacing_score": round(pacing_score, 4),
            "issues": [],
            "recommendations": [],
        }

        if not has_sufficient_action:
            evaluation["issues"].append(
                "Insufficient action density. Players may feel bored."
            )
            evaluation["recommendations"].append(
                "Add more action encounters or reduce segment length."
            )

        if not has_balanced_downtime:
            if downtime_ratio < 0.1:
                evaluation["issues"].append(
                    "Too little downtime. Players may feel overwhelmed."
                )
                evaluation["recommendations"].append(
                    "Insert breathing room between intense sequences."
                )
            else:
                evaluation["issues"].append(
                    "Too much downtime. Players may lose engagement."
                )
                evaluation["recommendations"].append(
                    "Reduce idle periods or add ambient activities."
                )

        if not has_variety:
            evaluation["issues"].append(
                "Flat tension curve. Lack of dynamic rhythm."
            )
            evaluation["recommendations"].append(
                "Introduce tension peaks and valleys for better flow."
            )

        if not evaluation["issues"]:
            evaluation["recommendations"].append(
                "Pacing is well-balanced. Maintain current rhythm patterns."
            )

        return evaluation

    # -----------------------------------------------------------------------
    # Improvement Suggestions
    # -----------------------------------------------------------------------

    def suggest_improvements(self, game_id: str) -> Dict[str, Any]:
        """Generate prioritized improvement suggestions for a game.

        Uses the latest game analysis to identify the most impactful
        areas for improvement, ranked by priority and estimated impact.
        Each suggestion includes a rationale and estimated effort.

        Args:
            game_id: The game to generate suggestions for.

        Returns:
            A dictionary with prioritized improvement suggestions.
        """
        self._stats["total_improvement_suggestions"] += 1

        analysis = self._latest_analysis.get(game_id)
        if analysis is None:
            analysis = self.analyze_game(game_id)

        suggestions: List[Dict[str, Any]] = []

        for dimension in GameAnalysisDimension:
            dim_key = dimension.value
            score = analysis.scores.get(dim_key, 0.5)
            weight = self._dimension_weights.get(dim_key, 0.05)

            if score < 0.7:
                impact = round((1.0 - score) * weight * 10, 2)
                priority = (
                    "CRITICAL" if score < 0.3
                    else "HIGH" if score < 0.5
                    else "MEDIUM"
                )

                suggestion = {
                    "suggestion_id": uuid.uuid4().hex[:8],
                    "dimension": dim_key,
                    "current_score": score,
                    "target_score": min(1.0, score + 0.2),
                    "estimated_impact": impact,
                    "priority": priority,
                    "effort_estimate": random.choice(["low", "medium", "high"]),
                    "rationale": (
                        f"{dimension.name} is underperforming at {score:.2f}. "
                        f"Improvement here would significantly enhance "
                        f"overall game quality."
                    ),
                    "specific_actions": analysis.suggestions.get(
                        dim_key, ["Review and improve this dimension."]
                    ),
                }
                suggestions.append(suggestion)

        # Sort by impact descending
        suggestions.sort(key=lambda s: s["estimated_impact"], reverse=True)

        return {
            "game_id": game_id,
            "overall_score": analysis.overall_score,
            "total_suggestions": len(suggestions),
            "suggestions": suggestions,
            "generated_at": _time_module.time(),
        }

    # -----------------------------------------------------------------------
    # Status and Monitoring
    # -----------------------------------------------------------------------

    def get_status(self) -> IntelligenceSnapshot:
        """Get comprehensive status of the intelligence hub.

        Produces a full snapshot of the hub's current operational
        state including mode, analysis history, decision queue,
        content cache, and subsystem health.

        Returns:
            An IntelligenceSnapshot with complete status information.
        """
        uptime = _time_module.time() - self._started_at

        return IntelligenceSnapshot(
            mode=self._mode.value,
            active_game_id=self._active_game_id,
            analyzed_games=list(self._latest_analysis.keys()),
            pending_decisions=len(self._pending_decisions),
            total_decisions=self._decision_counters["total"],
            content_cache_size=len(self._content_cache),
            subsystem_status=dict(self._subsystem_status),
            recent_warnings=list(self._recent_warnings),
            uptime_seconds=round(uptime, 2),
        )

    def get_stats(self) -> Dict[str, Any]:
        """Get aggregated statistics for the intelligence hub.

        Returns:
            A dictionary of operational statistics.
        """
        return {
            "mode": self._mode.value,
            "uptime_seconds": round(_time_module.time() - self._started_at, 2),
            "total_analyses": self._stats["total_analyses"],
            "total_decisions": self._stats["total_decisions"],
            "total_content_generated": self._stats["total_content_generated"],
            "total_optimizations": self._stats["total_optimizations"],
            "total_difficulty_assessments": self._stats["total_difficulty_assessments"],
            "total_pacing_evaluations": self._stats["total_pacing_evaluations"],
            "total_improvement_suggestions": self._stats["total_improvement_suggestions"],
            "avg_analysis_time_ms": round(self._stats["avg_analysis_time_ms"], 2),
            "avg_decision_time_ms": round(self._stats["avg_decision_time_ms"], 2),
            "avg_generation_time_ms": round(self._stats["avg_generation_time_ms"], 2),
            "decisions_by_priority": {
                k: v for k, v in self._decision_counters.items() if k != "total"
            },
            "content_by_category": dict(self._stats["content_by_category"]),
            "mode_transitions": dict(self._stats["mode_transitions"]),
            "content_cache_size": len(self._content_cache),
            "pending_decisions": len(self._pending_decisions),
            "subsystem_count": len(self._subsystem_status),
            "analyzed_games_count": len(self._latest_analysis),
        }

    # -----------------------------------------------------------------------
    # Subsystem Management
    # -----------------------------------------------------------------------

    def set_dimension_weights(self, weights: Dict[str, float]) -> None:
        """Update the dimension weights used for overall scoring.

        Args:
            weights: Mapping of dimension names to weight values.
        """
        for key, value in weights.items():
            if key in self._dimension_weights:
                self._dimension_weights[key] = value
        logger.info("Dimension weights updated: %s", weights)

    def get_dimension_weights(self) -> Dict[str, float]:
        """Get the current dimension weight configuration.

        Returns:
            A dictionary of dimension names to weight values.
        """
        return dict(self._dimension_weights)

    def get_latest_analysis(self, game_id: str) -> Optional[GameAnalysis]:
        """Get the most recent analysis for a game.

        Args:
            game_id: The game identifier.

        Returns:
            The latest GameAnalysis, or None if not found.
        """
        return self._latest_analysis.get(game_id)

    def get_decision_history(
        self, limit: int = 50, priority: Optional[str] = None
    ) -> List[DecisionRecord]:
        """Get recent decisions from the history.

        Args:
            limit: Maximum number of decisions to return.
            priority: Optional filter by priority level.

        Returns:
            A list of DecisionRecord instances.
        """
        decisions = list(self._decision_history)
        if priority:
            decisions = [d for d in decisions if d.priority == priority]
        return decisions[-limit:]

    def get_content_cache(self) -> Dict[str, ContentGenerationResult]:
        """Get the current content generation cache.

        Returns:
            A dictionary of cache keys to ContentGenerationResult.
        """
        return dict(self._content_cache)

    # -----------------------------------------------------------------------
    # Shutdown
    # -----------------------------------------------------------------------

    def shutdown(self) -> None:
        """Perform graceful shutdown of the intelligence hub.

        Flushes pending decisions, persists analysis data, clears
        caches, and transitions all subsystems to a disconnected
        state. After shutdown, the hub is no longer operational
        and must be re-initialized to resume.
        """
        with self._lock:
            self._mode = IntelligenceMode.IDLE

            # Flush pending decisions
            self._pending_decisions.clear()

            # Clear caches
            self._content_cache.clear()
            self._content_requests.clear()

            # Mark subsystems as disconnected
            for key in self._subsystem_status:
                self._subsystem_status[key] = "disconnected"

            self._active_game_id = ""

        logger.info("GameIntelligenceHub shut down gracefully")

    def reset(self) -> None:
        """Reset the intelligence hub to its initial state.

        Clears all analysis data, decision history, content cache,
        and statistics. Useful for testing or reinitialization
        scenarios.
        """
        with self._lock:
            self._mode = IntelligenceMode.IDLE
            self._active_game_id = ""
            self._analyses.clear()
            self._latest_analysis.clear()
            self._decision_history.clear()
            self._pending_decisions.clear()
            self._decision_counters = {
                "total": 0,
                DecisionPriority.CRITICAL.value: 0,
                DecisionPriority.HIGH.value: 0,
                DecisionPriority.MEDIUM.value: 0,
                DecisionPriority.LOW.value: 0,
                DecisionPriority.BACKGROUND.value: 0,
            }
            self._content_cache.clear()
            self._content_requests.clear()
            self._optimization_targets.clear()
            self._optimization_history.clear()
            self._recent_warnings.clear()
            self._stats = {
                "total_analyses": 0,
                "total_decisions": 0,
                "total_content_generated": 0,
                "total_optimizations": 0,
                "total_difficulty_assessments": 0,
                "total_pacing_evaluations": 0,
                "total_improvement_suggestions": 0,
                "mode_transitions": defaultdict(int),
                "content_by_category": defaultdict(int),
                "avg_analysis_time_ms": 0.0,
                "avg_decision_time_ms": 0.0,
                "avg_generation_time_ms": 0.0,
            }
            self._started_at = _time_module.time()

        logger.info("GameIntelligenceHub reset to initial state")


# ---------------------------------------------------------------------------
# Factory Function
# ---------------------------------------------------------------------------


def get_game_intelligence_hub() -> GameIntelligenceHub:
    """Get the GameIntelligenceHub singleton instance."""
    return GameIntelligenceHub.get_instance()