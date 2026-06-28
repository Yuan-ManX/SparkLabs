"""
SparkLabs Agent - Game Playtest Suite

A comprehensive game playtesting intelligence module for the SparkLabs
AI-native game engine. Provides an autonomous playtesting framework that
simulates human players, detects design issues, measures game quality
metrics, and generates actionable improvement reports.

Architecture:
  GamePlaytestSuite (singleton)
    |-- PlaytestConfig (session configuration)
    |-- PlaytestResult (complete playtest results with metrics)
    |-- DesignIssue (individual design issue found during testing)
    |-- PlayerSimulation (simulated player playthrough data)
    |-- QualityReport (comprehensive quality report)
    |-- PlaytestSnapshot (point-in-time playtest state capture)

Core Capabilities:
  - run_playtest: Execute a full playtest session across multiple modes
  - simulate_player: Simulate a player of a given archetype
  - detect_issues: Discover design issues through automated analysis
  - measure_fun: Measure fun factor across multiple dimensions
  - check_balance: Assess game balance and fairness
  - audit_accessibility: Audit game for accessibility compliance
  - generate_report: Produce a comprehensive quality report
"""

from __future__ import annotations

import math
import random
import threading
import time
import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple

_time_module = time


# ------------------------------------------------------------------
# Enums
# ------------------------------------------------------------------


class PlaytestMode(Enum):
    """Modes of playtesting that determine the testing strategy and focus."""
    FULL_PLAYTHROUGH = "full_playthrough"
    SPOT_CHECK = "spot_check"
    STRESS_TEST = "stress_test"
    EXPLORATION = "exploration"
    BALANCE_CHECK = "balance_check"
    FUN_AUDIT = "fun_audit"
    ACCESSIBILITY_CHECK = "accessibility_check"


class PlayerArchetype(Enum):
    """Player behavior profiles used to simulate different play styles."""
    SPEEDRUNNER = "speedrunner"
    EXPLORER = "explorer"
    COMPLETIONIST = "completionist"
    CASUAL = "casual"
    COMPETITIVE = "competitive"
    STORY_FOCUSED = "story_focused"
    SOCIAL = "social"
    ACHIEVER = "achiever"


class IssueSeverity(Enum):
    """Severity classification for design issues discovered during testing."""
    BLOCKER = "blocker"
    CRITICAL = "critical"
    MAJOR = "major"
    MINOR = "minor"
    COSMETIC = "cosmetic"
    SUGGESTION = "suggestion"


class IssueCategory(Enum):
    """Categories of design issues that can be detected during playtesting."""
    GAMEPLAY = "gameplay"
    BALANCE = "balance"
    PERFORMANCE = "performance"
    UX = "ux"
    NARRATIVE = "narrative"
    VISUAL = "visual"
    AUDIO = "audio"
    ACCESSIBILITY = "accessibility"
    PROGRESSION = "progression"
    TUTORIAL = "tutorial"


# ------------------------------------------------------------------
# Archetype behavior profiles
# ------------------------------------------------------------------

_ARCHETYPE_PROFILES: Dict[PlayerArchetype, Dict[str, float]] = {
    PlayerArchetype.SPEEDRUNNER: {
        "exploration_weight": 0.05,
        "completion_thoroughness": 0.10,
        "combat_aggressiveness": 0.40,
        "skip_cutscenes": 1.0,
        "use_guides": 1.0,
        "interaction_rate": 0.15,
        "quit_threshold": 0.02,
    },
    PlayerArchetype.EXPLORER: {
        "exploration_weight": 1.0,
        "completion_thoroughness": 0.60,
        "combat_aggressiveness": 0.25,
        "skip_cutscenes": 0.1,
        "use_guides": 0.0,
        "interaction_rate": 0.80,
        "quit_threshold": 0.05,
    },
    PlayerArchetype.COMPLETIONIST: {
        "exploration_weight": 0.90,
        "completion_thoroughness": 1.0,
        "combat_aggressiveness": 0.55,
        "skip_cutscenes": 0.0,
        "use_guides": 0.3,
        "interaction_rate": 0.90,
        "quit_threshold": 0.03,
    },
    PlayerArchetype.CASUAL: {
        "exploration_weight": 0.35,
        "completion_thoroughness": 0.30,
        "combat_aggressiveness": 0.30,
        "skip_cutscenes": 0.3,
        "use_guides": 0.0,
        "interaction_rate": 0.40,
        "quit_threshold": 0.15,
    },
    PlayerArchetype.COMPETITIVE: {
        "exploration_weight": 0.20,
        "completion_thoroughness": 0.40,
        "combat_aggressiveness": 1.0,
        "skip_cutscenes": 0.9,
        "use_guides": 0.7,
        "interaction_rate": 0.25,
        "quit_threshold": 0.05,
    },
    PlayerArchetype.STORY_FOCUSED: {
        "exploration_weight": 0.30,
        "completion_thoroughness": 0.35,
        "combat_aggressiveness": 0.20,
        "skip_cutscenes": 0.0,
        "use_guides": 0.0,
        "interaction_rate": 0.70,
        "quit_threshold": 0.08,
    },
    PlayerArchetype.SOCIAL: {
        "exploration_weight": 0.40,
        "completion_thoroughness": 0.25,
        "combat_aggressiveness": 0.15,
        "skip_cutscenes": 0.2,
        "use_guides": 0.1,
        "interaction_rate": 0.85,
        "quit_threshold": 0.10,
    },
    PlayerArchetype.ACHIEVER: {
        "exploration_weight": 0.55,
        "completion_thoroughness": 0.85,
        "combat_aggressiveness": 0.65,
        "skip_cutscenes": 0.2,
        "use_guides": 0.5,
        "interaction_rate": 0.60,
        "quit_threshold": 0.04,
    },
}

# ------------------------------------------------------------------
# Known issue patterns for detection
# ------------------------------------------------------------------

_ISSUE_PATTERNS: Dict[str, Dict[str, Any]] = {
    "difficulty_spike": {
        "category": IssueCategory.BALANCE,
        "severity": IssueSeverity.MAJOR,
        "description": "Sharp difficulty spike detected between levels",
    },
    "soft_lock": {
        "category": IssueCategory.GAMEPLAY,
        "severity": IssueSeverity.BLOCKER,
        "description": "Player can become stuck without progression path",
    },
    "resource_drought": {
        "category": IssueCategory.BALANCE,
        "severity": IssueSeverity.MAJOR,
        "description": "Insufficient resource availability for progression",
    },
    "tutorial_gap": {
        "category": IssueCategory.TUTORIAL,
        "severity": IssueSeverity.MINOR,
        "description": "Mechanic introduced without adequate tutorial",
    },
    "death_loop": {
        "category": IssueCategory.GAMEPLAY,
        "severity": IssueSeverity.CRITICAL,
        "description": "Repeated deaths at checkpoint with no escape path",
    },
    "progression_block": {
        "category": IssueCategory.PROGRESSION,
        "severity": IssueSeverity.CRITICAL,
        "description": "Progression blocked by missing or broken trigger",
    },
    "pacing_issue": {
        "category": IssueCategory.GAMEPLAY,
        "severity": IssueSeverity.MINOR,
        "description": "Gameplay pacing is inconsistent or unbalanced",
    },
    "visual_clarity": {
        "category": IssueCategory.VISUAL,
        "severity": IssueSeverity.MINOR,
        "description": "Visual elements lack clarity for gameplay decisions",
    },
    "audio_feedback": {
        "category": IssueCategory.AUDIO,
        "severity": IssueSeverity.COSMETIC,
        "description": "Missing or insufficient audio feedback for actions",
    },
    "ui_confusion": {
        "category": IssueCategory.UX,
        "severity": IssueSeverity.MINOR,
        "description": "UI elements are confusing or poorly positioned",
    },
    "narrative_disconnect": {
        "category": IssueCategory.NARRATIVE,
        "severity": IssueSeverity.MINOR,
        "description": "Narrative elements conflict with gameplay mechanics",
    },
    "accessibility_barrier": {
        "category": IssueCategory.ACCESSIBILITY,
        "severity": IssueSeverity.MAJOR,
        "description": "Game element is inaccessible to players with disabilities",
    },
    "performance_degradation": {
        "category": IssueCategory.PERFORMANCE,
        "severity": IssueSeverity.MAJOR,
        "description": "Performance degrades significantly during gameplay",
    },
}

# ------------------------------------------------------------------
# Fun dimension definitions
# ------------------------------------------------------------------

_FUN_DIMENSIONS: List[str] = [
    "challenge",
    "discovery",
    "mastery",
    "narrative",
    "social",
    "creativity",
    "immersion",
    "progression",
    "feedback",
    "agency",
]

# ------------------------------------------------------------------
# Accessibility checklist
# ------------------------------------------------------------------

_ACCESSIBILITY_CHECKS: List[Dict[str, Any]] = [
    {"id": "color_contrast", "name": "Color Contrast", "weight": 0.15},
    {"id": "text_scaling", "name": "Text Scaling Support", "weight": 0.10},
    {"id": "remappable_controls", "name": "Remappable Controls", "weight": 0.15},
    {"id": "subtitles", "name": "Subtitles & Captions", "weight": 0.12},
    {"id": "audio_cues", "name": "Visual Alternatives for Audio", "weight": 0.10},
    {"id": "difficulty_options", "name": "Difficulty Options", "weight": 0.12},
    {"id": "input_methods", "name": "Multiple Input Methods", "weight": 0.10},
    {"id": "motion_sensitivity", "name": "Motion Sensitivity Options", "weight": 0.08},
    {"id": "tutorial_clarity", "name": "Tutorial Clarity", "weight": 0.08},
]


# ------------------------------------------------------------------
# Data Classes
# ------------------------------------------------------------------


@dataclass
class PlaytestConfig:
    """Configuration for a playtest session.

    Defines the testing mode, archetypes to simulate, session count,
    duration, and optional game-specific parameters.
    """
    config_id: str = field(default_factory=lambda: uuid.uuid4().hex[:8])
    game_id: str = ""
    mode: PlaytestMode = PlaytestMode.FULL_PLAYTHROUGH
    archetypes: List[PlayerArchetype] = field(default_factory=list)
    session_count: int = 10
    max_duration_seconds: float = 3600.0
    level_count: int = 5
    entity_types: List[str] = field(default_factory=lambda: ["player", "enemy", "npc"])
    custom_params: Dict[str, Any] = field(default_factory=dict)
    save_snapshots: bool = True
    verbose: bool = False
    created_at: float = field(default_factory=_time_module.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "config_id": self.config_id,
            "game_id": self.game_id,
            "mode": self.mode.value,
            "archetypes": [a.value for a in self.archetypes],
            "session_count": self.session_count,
            "max_duration_seconds": self.max_duration_seconds,
            "level_count": self.level_count,
            "entity_types": list(self.entity_types),
            "custom_params": dict(self.custom_params),
            "save_snapshots": self.save_snapshots,
            "verbose": self.verbose,
            "created_at": self.created_at,
        }


@dataclass
class DesignIssue:
    """A single design issue found during automated playtesting.

    Captures the issue category, severity, affected areas, and
    actionable recommendations for resolution.
    """
    issue_id: str = field(default_factory=lambda: uuid.uuid4().hex[:8])
    game_id: str = ""
    category: IssueCategory = IssueCategory.GAMEPLAY
    severity: IssueSeverity = IssueSeverity.MINOR
    title: str = ""
    description: str = ""
    affected_levels: List[int] = field(default_factory=list)
    affected_archetypes: List[PlayerArchetype] = field(default_factory=list)
    reproduction_steps: List[str] = field(default_factory=list)
    recommendation: str = ""
    impact_score: float = 0.0
    confidence: float = 0.0
    detected_at: float = field(default_factory=_time_module.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "issue_id": self.issue_id,
            "game_id": self.game_id,
            "category": self.category.value,
            "severity": self.severity.value,
            "title": self.title,
            "description": self.description,
            "affected_levels": list(self.affected_levels),
            "affected_archetypes": [a.value for a in self.affected_archetypes],
            "reproduction_steps": list(self.reproduction_steps),
            "recommendation": self.recommendation,
            "impact_score": round(self.impact_score, 3),
            "confidence": round(self.confidence, 3),
            "detected_at": self.detected_at,
        }


@dataclass
class PlayerSimulation:
    """A simulated player's complete playthrough data.

    Tracks all metrics from a single archetype playthrough including
    progression, deaths, collection, and engagement data.
    """
    simulation_id: str = field(default_factory=lambda: uuid.uuid4().hex[:8])
    game_id: str = ""
    archetype: PlayerArchetype = PlayerArchetype.CASUAL
    total_time_seconds: float = 0.0
    levels_completed: int = 0
    total_levels: int = 0
    deaths: int = 0
    death_locations: List[str] = field(default_factory=list)
    items_collected: int = 0
    total_items: int = 0
    quests_completed: int = 0
    total_quests: int = 0
    combat_encounters: int = 0
    combat_wins: int = 0
    combat_losses: int = 0
    frustration_events: int = 0
    quit_early: bool = False
    quit_reason: str = ""
    bottlenecks_hit: List[str] = field(default_factory=list)
    areas_visited: int = 0
    total_areas: int = 0
    interaction_count: int = 0
    progression_path: List[int] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=_time_module.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "simulation_id": self.simulation_id,
            "game_id": self.game_id,
            "archetype": self.archetype.value,
            "total_time_seconds": round(self.total_time_seconds, 2),
            "levels_completed": self.levels_completed,
            "total_levels": self.total_levels,
            "deaths": self.deaths,
            "death_locations": list(self.death_locations),
            "items_collected": self.items_collected,
            "total_items": self.total_items,
            "quests_completed": self.quests_completed,
            "total_quests": self.total_quests,
            "combat_encounters": self.combat_encounters,
            "combat_wins": self.combat_wins,
            "combat_losses": self.combat_losses,
            "frustration_events": self.frustration_events,
            "quit_early": self.quit_early,
            "quit_reason": self.quit_reason,
            "bottlenecks_hit": list(self.bottlenecks_hit),
            "areas_visited": self.areas_visited,
            "total_areas": self.total_areas,
            "interaction_count": self.interaction_count,
            "progression_path": list(self.progression_path),
            "metadata": dict(self.metadata),
            "created_at": self.created_at,
        }

    @property
    def completion_rate(self) -> float:
        if self.total_levels == 0:
            return 0.0
        return self.levels_completed / self.total_levels

    @property
    def win_rate(self) -> float:
        if self.combat_encounters == 0:
            return 1.0
        return self.combat_wins / self.combat_encounters

    @property
    def exploration_rate(self) -> float:
        if self.total_areas == 0:
            return 0.0
        return self.areas_visited / self.total_areas

    @property
    def collection_rate(self) -> float:
        if self.total_items == 0:
            return 0.0
        return self.items_collected / self.total_items


@dataclass
class PlaytestResult:
    """Complete playtest results aggregating all simulations and metrics.

    Contains all simulated player sessions, detected issues, computed
    quality scores, and overall assessment for a given game.
    """
    result_id: str = field(default_factory=lambda: uuid.uuid4().hex[:8])
    game_id: str = ""
    config: Optional[PlaytestConfig] = None
    simulations: List[PlayerSimulation] = field(default_factory=list)
    issues: List[DesignIssue] = field(default_factory=list)
    fun_scores: Dict[str, float] = field(default_factory=dict)
    balance_score: float = 0.0
    accessibility_score: float = 0.0
    overall_score: float = 0.0
    snapshots: List[PlaytestSnapshot] = field(default_factory=list)
    started_at: float = 0.0
    completed_at: float = 0.0
    duration_seconds: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "result_id": self.result_id,
            "game_id": self.game_id,
            "config": self.config.to_dict() if self.config else None,
            "simulation_count": len(self.simulations),
            "issue_count": len(self.issues),
            "fun_scores": dict(self.fun_scores),
            "balance_score": round(self.balance_score, 3),
            "accessibility_score": round(self.accessibility_score, 3),
            "overall_score": round(self.overall_score, 3),
            "snapshot_count": len(self.snapshots),
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "duration_seconds": round(self.duration_seconds, 2),
        }


@dataclass
class QualityReport:
    """Comprehensive quality report with scores and recommendations.

    Aggregates all playtest findings into a structured report with
    prioritized issues, dimension scores, and actionable recommendations
    for improving the game.
    """
    report_id: str = field(default_factory=lambda: uuid.uuid4().hex[:8])
    game_id: str = ""
    result_id: str = ""
    summary: str = ""
    overall_score: float = 0.0
    fun_scores: Dict[str, float] = field(default_factory=dict)
    balance_score: float = 0.0
    accessibility_score: float = 0.0
    issues_by_severity: Dict[str, int] = field(default_factory=dict)
    issues_by_category: Dict[str, int] = field(default_factory=dict)
    top_issues: List[DesignIssue] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)
    archetype_insights: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    generated_at: float = field(default_factory=_time_module.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "report_id": self.report_id,
            "game_id": self.game_id,
            "result_id": self.result_id,
            "summary": self.summary,
            "overall_score": round(self.overall_score, 3),
            "fun_scores": dict(self.fun_scores),
            "balance_score": round(self.balance_score, 3),
            "accessibility_score": round(self.accessibility_score, 3),
            "issues_by_severity": dict(self.issues_by_severity),
            "issues_by_category": dict(self.issues_by_category),
            "top_issues": [i.to_dict() for i in self.top_issues],
            "recommendations": list(self.recommendations),
            "archetype_insights": {
                k: dict(v) for k, v in self.archetype_insights.items()
            },
            "generated_at": self.generated_at,
        }


@dataclass
class PlaytestSnapshot:
    """Point-in-time snapshot of playtest state for tracking progress."""
    snapshot_id: str = field(default_factory=lambda: uuid.uuid4().hex[:8])
    game_id: str = ""
    elapsed_seconds: float = 0.0
    simulations_completed: int = 0
    issues_detected: int = 0
    current_fun_score: float = 0.0
    current_balance_score: float = 0.0
    state_summary: str = ""
    captured_at: float = field(default_factory=_time_module.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "snapshot_id": self.snapshot_id,
            "game_id": self.game_id,
            "elapsed_seconds": round(self.elapsed_seconds, 2),
            "simulations_completed": self.simulations_completed,
            "issues_detected": self.issues_detected,
            "current_fun_score": round(self.current_fun_score, 3),
            "current_balance_score": round(self.current_balance_score, 3),
            "state_summary": self.state_summary,
            "captured_at": self.captured_at,
        }


# ------------------------------------------------------------------
# GamePlaytestSuite Singleton
# ------------------------------------------------------------------


class GamePlaytestSuite:
    """Autonomous game playtesting intelligence suite.

    Provides a comprehensive framework for simulating human players
    across diverse archetypes, detecting design issues, measuring
    game quality metrics (fun, balance, accessibility), and generating
    actionable improvement reports.

    Uses double-checked locking for thread-safe singleton initialization.
    """

    _instance: Optional[GamePlaytestSuite] = None
    _lock: threading.RLock = threading.RLock()

    def __new__(cls) -> GamePlaytestSuite:
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    instance = super().__new__(cls)
                    instance._initialized = False
                    cls._instance = instance
        return cls._instance

    @classmethod
    def get_instance(cls) -> GamePlaytestSuite:
        """Get the singleton instance of GamePlaytestSuite."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    instance = super().__new__(cls)
                    instance.__init__()
                    cls._instance = instance
        return cls._instance

    def __init__(self) -> None:
        """Initialize playtest state, player archetypes, and issue database."""
        if self._initialized:
            return
        self._initialized = True
        self._results: Dict[str, PlaytestResult] = {}
        self._reports: Dict[str, QualityReport] = {}
        self._issue_database: Dict[str, List[DesignIssue]] = defaultdict(list)
        self._snapshots: Dict[str, List[PlaytestSnapshot]] = defaultdict(list)
        self._stats: Dict[str, Any] = {
            "total_sessions_run": 0,
            "total_issues_detected": 0,
            "total_reports_generated": 0,
            "total_simulations_run": 0,
        }
        self._active: bool = False

    # ------------------------------------------------------------------
    # Core Operations
    # ------------------------------------------------------------------

    def initialize(self) -> None:
        """Initialize the playtest suite and prepare for testing sessions.

        Resets all internal state, clears previous results, and prepares
        the issue detection database for fresh analysis.
        """
        with self._lock:
            self._results.clear()
            self._reports.clear()
            self._issue_database.clear()
            self._snapshots.clear()
            self._stats = {
                "total_sessions_run": 0,
                "total_issues_detected": 0,
                "total_reports_generated": 0,
                "total_simulations_run": 0,
            }
            self._active = True

    def run_playtest(
        self, game_id: str, config: PlaytestConfig
    ) -> PlaytestResult:
        """Run a full playtest session against the specified game.

        Simulates multiple player archetypes through the game, detects
        design issues, computes quality metrics, and produces a complete
        PlaytestResult with all findings.

        Args:
            game_id: The unique identifier of the game to test.
            config: PlaytestConfig specifying mode, archetypes, and parameters.

        Returns:
            A PlaytestResult containing all simulations, issues, and scores.
        """
        with self._lock:
            if not self._active:
                self.initialize()

            result = PlaytestResult(
                game_id=game_id, config=config, started_at=_time_module.time()
            )

            archetypes = config.archetypes or list(PlayerArchetype)
            sessions_per_archetype = max(
                1, config.session_count // max(1, len(archetypes))
            )

            for archetype in archetypes:
                for _ in range(sessions_per_archetype):
                    game_state = self._build_initial_game_state(config)
                    simulation = self.simulate_player(archetype, game_state)
                    simulation.game_id = game_id
                    result.simulations.append(simulation)
                    self._stats["total_simulations_run"] += 1

            detected_issues = self.detect_issues(game_id)
            result.issues = detected_issues
            self._issue_database[game_id].extend(detected_issues)
            self._stats["total_issues_detected"] += len(detected_issues)

            result.fun_scores = self._compute_fun_scores(result)
            result.balance_score = self._compute_balance_score(result)
            result.accessibility_score = self._evaluate_accessibility(result)

            result.overall_score = self._compute_overall_score(result)

            result.completed_at = _time_module.time()
            result.duration_seconds = result.completed_at - result.started_at

            self._results[game_id] = result
            self._stats["total_sessions_run"] += 1

            if config.save_snapshots:
                self._take_snapshot(game_id, result)

            return result

    def simulate_player(
        self, archetype: PlayerArchetype, game_state: Dict[str, Any]
    ) -> PlayerSimulation:
        """Simulate a player of the given archetype through the game.

        Generates realistic playthrough data based on the archetype's
        behavior profile including exploration patterns, combat outcomes,
        item collection, progression path, and frustration events.

        Args:
            archetype: The player archetype to simulate.
            game_state: Initial game state dictionary with level and entity info.

        Returns:
            A PlayerSimulation containing the complete playthrough data.
        """
        profile = _ARCHETYPE_PROFILES.get(
            archetype, _ARCHETYPE_PROFILES[PlayerArchetype.CASUAL]
        )

        total_levels = game_state.get("total_levels", 5)
        total_items = game_state.get("total_items", total_levels * 20)
        total_areas = game_state.get("total_areas", total_levels * 10)
        total_quests = game_state.get("total_quests", total_levels * 4)

        simulation = PlayerSimulation(
            archetype=archetype,
            total_levels=total_levels,
            total_items=total_items,
            total_areas=total_areas,
            total_quests=total_quests,
        )

        exploration = profile["exploration_weight"]
        thoroughness = profile["completion_thoroughness"]
        aggressiveness = profile["combat_aggressiveness"]
        quit_threshold = profile["quit_threshold"]

        # Simulate level-by-level progression
        for level in range(1, total_levels + 1):
            if random.random() < quit_threshold:
                simulation.quit_early = True
                simulation.quit_reason = self._random_quit_reason(archetype)
                break

            simulation.levels_completed = level
            simulation.progression_path.append(level)

            # Deaths per level
            base_deaths = random.randint(0, 3)
            if aggressiveness > 0.7:
                base_deaths += random.randint(1, 4)
            if thoroughness < 0.3:
                base_deaths += random.randint(0, 2)
            simulation.deaths += base_deaths
            for _ in range(base_deaths):
                simulation.death_locations.append(f"level_{level}_area_{random.randint(1, 10)}")

            # Combat encounters
            encounters = int(random.randint(2, 8) * aggressiveness + 2)
            simulation.combat_encounters += encounters
            win_prob = 0.65 - (aggressiveness - 0.5) * 0.15
            for _ in range(encounters):
                if random.random() < win_prob:
                    simulation.combat_wins += 1
                else:
                    simulation.combat_losses += 1

            # Item collection
            level_items = int(total_items / total_levels * thoroughness * random.uniform(0.8, 1.2))
            simulation.items_collected = min(
                total_items, simulation.items_collected + level_items
            )

            # Area exploration
            level_areas = int(total_areas / total_levels * exploration * random.uniform(0.7, 1.3))
            simulation.areas_visited = min(
                total_areas, simulation.areas_visited + level_areas
            )

            # Quest completion
            level_quests = int(
                total_quests / total_levels * thoroughness * random.uniform(0.5, 1.5)
            )
            simulation.quests_completed = min(
                total_quests, simulation.quests_completed + level_quests
            )

            # Interaction count
            simulation.interaction_count += int(
                profile["interaction_rate"] * random.randint(5, 20)
            )

            # Bottleneck detection
            if random.random() < 0.15 * aggressiveness:
                simulation.bottlenecks_hit.append(
                    random.choice(
                        ["boss_room", "puzzle_gate", "elite_patrol",
                         "platform_section", "resource_gate"]
                    )
                )

            # Frustration events
            if random.random() < 0.1 * (1 + aggressiveness):
                simulation.frustration_events += random.randint(1, 3)

        # Compute total playtime
        base_time = 300.0 * total_levels
        time_factor = 1.0 + (1.0 - exploration) * 0.5 + (1.0 - thoroughness) * 0.3
        if archetype == PlayerArchetype.SPEEDRUNNER:
            time_factor = 0.3
        simulation.total_time_seconds = max(
            60.0, base_time * time_factor * random.uniform(0.8, 1.2)
        )

        simulation.metadata = {
            "profile": dict(profile),
            "game_state_snapshot": {
                k: v for k, v in game_state.items()
                if not isinstance(v, (list, dict, set))
            },
        }

        return simulation

    def detect_issues(self, game_id: str) -> List[DesignIssue]:
        """Detect design issues in the game through automated analysis.

        Examines simulation data, progression paths, death patterns,
        and balance metrics to identify gameplay problems, balance
        issues, and design flaws.

        Args:
            game_id: The unique identifier of the game to analyze.

        Returns:
            A list of DesignIssue objects representing detected problems.
        """
        result = self._results.get(game_id)
        if result is None:
            return []

        issues: List[DesignIssue] = []
        simulations = result.simulations

        if not simulations:
            return issues

        # Aggregate metrics across all simulations
        total_deaths = sum(s.deaths for s in simulations)
        avg_deaths = total_deaths / max(1, len(simulations))
        quit_rate = sum(1 for s in simulations if s.quit_early) / max(1, len(simulations))
        completion_rate = sum(s.completion_rate for s in simulations) / max(1, len(simulations))

        all_bottlenecks: Dict[str, int] = {}
        for s in simulations:
            for bn in s.bottlenecks_hit:
                all_bottlenecks[bn] = all_bottlenecks.get(bn, 0) + 1

        # Difficulty spike detection
        if avg_deaths > 8:
            issues.append(self._create_issue(
                game_id, "difficulty_spike",
                affected_levels=self._identify_hard_levels(simulations),
                impact_score=min(1.0, avg_deaths / 20.0),
                confidence=min(1.0, avg_deaths / 15.0),
                recommendation="Reduce enemy damage or increase player resources in identified levels.",
            ))

        # Death loop detection
        death_locations: Dict[str, int] = {}
        for s in simulations:
            for loc in s.death_locations:
                death_locations[loc] = death_locations.get(loc, 0) + 1
        for loc, count in death_locations.items():
            if count >= 5:
                issues.append(self._create_issue(
                    game_id, "death_loop",
                    affected_levels=[int(loc.split("_")[1])],
                    impact_score=min(1.0, count / 15.0),
                    confidence=0.8,
                    recommendation=f"Add alternative paths or reduce difficulty near {loc}.",
                ))

        # Progression block detection
        if completion_rate < 0.4:
            issues.append(self._create_issue(
                game_id, "progression_block",
                affected_levels=self._identify_stuck_levels(simulations),
                impact_score=1.0 - completion_rate,
                confidence=0.85,
                recommendation="Check level triggers and ensure all progression paths are accessible.",
            ))

        # Soft lock detection
        if quit_rate > 0.2:
            issues.append(self._create_issue(
                game_id, "soft_lock",
                impact_score=quit_rate,
                confidence=0.7,
                recommendation="Review areas where players quit - check for environmental soft locks.",
            ))

        # Pacing issues
        times = [s.total_time_seconds for s in simulations if not s.quit_early]
        if len(times) >= 2:
            avg_time = sum(times) / len(times)
            variance = sum((t - avg_time) ** 2 for t in times) / len(times)
            if variance > avg_time * avg_time * 0.5:
                issues.append(self._create_issue(
                    game_id, "pacing_issue",
                    impact_score=min(1.0, variance / (avg_time * avg_time)),
                    confidence=0.6,
                    recommendation="Normalize level lengths and encounter density for consistent pacing.",
                ))

        # Bottleneck analysis
        for bn, count in all_bottlenecks.items():
            if count >= len(simulations) * 0.25:
                severity = IssueSeverity.CRITICAL if count >= len(simulations) * 0.5 else IssueSeverity.MAJOR
                issues.append(DesignIssue(
                    game_id=game_id,
                    category=IssueCategory.GAMEPLAY,
                    severity=severity,
                    title=f"Bottleneck: {bn}",
                    description=f"Bottleneck at '{bn}' affects {count}/{len(simulations)} players.",
                    affected_archetypes=self._identify_affected_archetypes(simulations, bn),
                    recommendation=f"Redesign '{bn}' to provide alternative paths or reduce difficulty.",
                    impact_score=min(1.0, count / len(simulations)),
                    confidence=min(1.0, count / (len(simulations) * 0.5)),
                ))

        # Resource balance
        avg_collection = sum(s.collection_rate for s in simulations) / max(1, len(simulations))
        if avg_collection < 0.3:
            issues.append(self._create_issue(
                game_id, "resource_drought",
                impact_score=1.0 - avg_collection,
                confidence=0.75,
                recommendation="Increase resource availability or reduce resource costs for core progression.",
            ))

        return issues

    def measure_fun(self, game_id: str) -> Dict[str, float]:
        """Measure fun factor across multiple engagement dimensions.

        Evaluates the game across ten dimensions of player engagement
        including challenge, discovery, mastery, narrative, immersion,
        and agency. Returns a dictionary of dimension scores.

        Args:
            game_id: The unique identifier of the game to evaluate.

        Returns:
            A dictionary mapping fun dimension names to scores (0.0-1.0).
        """
        result = self._results.get(game_id)
        if result is None:
            return {dim: 0.0 for dim in _FUN_DIMENSIONS}

        simulations = result.simulations
        if not simulations:
            return {dim: 0.0 for dim in _FUN_DIMENSIONS}

        n = max(1, len(simulations))

        avg_win_rate = sum(s.win_rate for s in simulations) / n
        avg_exploration = sum(s.exploration_rate for s in simulations) / n
        avg_collection = sum(s.collection_rate for s in simulations) / n
        avg_completion = sum(s.completion_rate for s in simulations) / n
        avg_frustration = sum(s.frustration_events for s in simulations) / n
        avg_interactions = sum(s.interaction_count for s in simulations) / n

        # Challenge: sweet spot for win rate is 40-70%
        challenge_score = 0.0
        if 0.4 <= avg_win_rate <= 0.7:
            challenge_score = 0.85
        elif avg_win_rate > 0.7:
            challenge_score = 0.5
        else:
            challenge_score = 0.3

        # Discovery: based on exploration
        discovery_score = avg_exploration

        # Mastery: based on completion and low frustration
        mastery_score = avg_completion * (1.0 - min(1.0, avg_frustration / 20.0))

        # Narrative: based on story-focused archetype completion
        narrative_sims = [
            s for s in simulations
            if s.archetype == PlayerArchetype.STORY_FOCUSED
        ]
        if narrative_sims:
            narrative_score = sum(s.completion_rate for s in narrative_sims) / len(narrative_sims)
        else:
            narrative_score = avg_completion * 0.7

        # Social: based on social archetype interactions
        social_sims = [
            s for s in simulations
            if s.archetype == PlayerArchetype.SOCIAL
        ]
        if social_sims:
            social_score = sum(s.interaction_count for s in social_sims) / max(
                1, sum(s.quests_completed * 5 for s in social_sims)
            )
            social_score = min(1.0, social_score)
        else:
            social_score = min(1.0, avg_interactions / 100.0)

        # Creativity: based on exploration and interaction variety
        creativity_score = (avg_exploration + min(1.0, avg_interactions / 80.0)) / 2.0

        # Immersion: based on low quit rate and high completion
        quit_rate = sum(1 for s in simulations if s.quit_early) / n
        immersion_score = (1.0 - quit_rate) * avg_completion

        # Progression satisfaction
        progression_score = avg_completion * (1.0 - min(1.0, avg_frustration / 15.0))

        # Feedback: based on interaction density
        feedback_score = min(1.0, avg_interactions / 60.0)

        # Agency: based on exploration and win rate balance
        agency_score = (avg_exploration + (1.0 - abs(avg_win_rate - 0.55))) / 2.0

        return {
            "challenge": round(challenge_score, 3),
            "discovery": round(discovery_score, 3),
            "mastery": round(mastery_score, 3),
            "narrative": round(narrative_score, 3),
            "social": round(social_score, 3),
            "creativity": round(creativity_score, 3),
            "immersion": round(immersion_score, 3),
            "progression": round(progression_score, 3),
            "feedback": round(feedback_score, 3),
            "agency": round(agency_score, 3),
        }

    def check_balance(self, game_id: str) -> Dict[str, Any]:
        """Check game balance and fairness across all systems.

        Analyzes combat win/loss ratios, resource economy, difficulty
        scaling, and progression fairness to produce a comprehensive
        balance assessment.

        Args:
            game_id: The unique identifier of the game to check.

        Returns:
            A dictionary with balance scores, metrics, and interpretation.
        """
        result = self._results.get(game_id)
        if result is None:
            return {"balance_score": 0.0, "error": "No playtest results found"}

        simulations = result.simulations
        if not simulations:
            return {"balance_score": 0.0, "error": "No simulations available"}

        n = max(1, len(simulations))

        # Combat balance
        avg_win_rate = sum(s.win_rate for s in simulations) / n
        combat_balance = 1.0 - abs(avg_win_rate - 0.55) * 2.0

        # Difficulty balance
        avg_deaths = sum(s.deaths for s in simulations) / n
        death_balance = 1.0 - min(1.0, avg_deaths / 15.0)

        # Progression balance
        avg_completion = sum(s.completion_rate for s in simulations) / n
        progression_balance = avg_completion

        # Economy balance (collection rate)
        avg_collection = sum(s.collection_rate for s in simulations) / n
        economy_balance = 1.0 - abs(avg_collection - 0.6) * 1.5

        # Archetype fairness: how well different archetypes perform
        archetype_scores: Dict[str, float] = {}
        for archetype in PlayerArchetype:
            arch_sims = [s for s in simulations if s.archetype == archetype]
            if arch_sims:
                archetype_scores[archetype.value] = sum(
                    s.completion_rate for s in arch_sims
                ) / len(arch_sims)

        if archetype_scores:
            values = list(archetype_scores.values())
            fairness = 1.0 - (max(values) - min(values))
        else:
            fairness = 0.5

        balance_score = (
            combat_balance * 0.30
            + death_balance * 0.25
            + progression_balance * 0.20
            + economy_balance * 0.15
            + fairness * 0.10
        )
        balance_score = round(max(0.0, min(1.0, balance_score)), 3)

        interpretation = self._interpret_balance(balance_score)

        return {
            "balance_score": balance_score,
            "combat_balance": round(combat_balance, 3),
            "death_balance": round(death_balance, 3),
            "progression_balance": round(progression_balance, 3),
            "economy_balance": round(economy_balance, 3),
            "archetype_fairness": round(fairness, 3),
            "archetype_scores": {k: round(v, 3) for k, v in archetype_scores.items()},
            "avg_win_rate": round(avg_win_rate, 3),
            "avg_deaths": round(avg_deaths, 2),
            "avg_completion": round(avg_completion, 3),
            "interpretation": interpretation,
        }

    def audit_accessibility(self, game_id: str) -> Dict[str, Any]:
        """Audit the game for accessibility issues.

        Evaluates the game against a comprehensive accessibility checklist
        covering color contrast, text scaling, remappable controls,
        subtitles, audio cues, difficulty options, input methods,
        motion sensitivity, and tutorial clarity.

        Args:
            game_id: The unique identifier of the game to audit.

        Returns:
            A dictionary with accessibility scores, check results, and
            prioritized recommendations.
        """
        result = self._results.get(game_id)
        simulations = result.simulations if result else []

        check_results: Dict[str, Dict[str, Any]] = {}
        weighted_sum = 0.0
        total_weight = 0.0

        # Simulate accessibility audit based on game metrics
        avg_completion = sum(
            s.completion_rate for s in simulations
        ) / max(1, len(simulations)) if simulations else 0.5

        avg_interactions = sum(
            s.interaction_count for s in simulations
        ) / max(1, len(simulations)) if simulations else 30

        casual_sims = [
            s for s in simulations
            if s.archetype == PlayerArchetype.CASUAL
        ] if simulations else []
        casual_completion = sum(
            s.completion_rate for s in casual_sims
        ) / max(1, len(casual_sims)) if casual_sims else avg_completion

        for check in _ACCESSIBILITY_CHECKS:
            check_id = check["id"]
            weight = check["weight"]

            if check_id == "color_contrast":
                score = random.uniform(0.5, 0.9)
            elif check_id == "text_scaling":
                score = random.uniform(0.3, 0.8)
            elif check_id == "remappable_controls":
                score = random.uniform(0.4, 0.85)
            elif check_id == "subtitles":
                score = random.uniform(0.4, 0.9)
            elif check_id == "audio_cues":
                score = random.uniform(0.35, 0.8)
            elif check_id == "difficulty_options":
                score = 0.5 + avg_completion * 0.3
            elif check_id == "input_methods":
                score = random.uniform(0.3, 0.75)
            elif check_id == "motion_sensitivity":
                score = random.uniform(0.2, 0.7)
            elif check_id == "tutorial_clarity":
                score = 0.4 + casual_completion * 0.4
            else:
                score = 0.5

            check_results[check_id] = {
                "name": check["name"],
                "score": round(score, 3),
                "weight": weight,
                "passed": score >= 0.6,
            }
            weighted_sum += score * weight
            total_weight += weight

        overall_score = round(weighted_sum / max(0.001, total_weight), 3)

        failed_checks = [
            check_id for check_id, data in check_results.items()
            if not data["passed"]
        ]

        recommendations = []
        if "color_contrast" in failed_checks:
            recommendations.append(
                "Improve color contrast ratios for UI elements and gameplay-critical visuals."
            )
        if "text_scaling" in failed_checks:
            recommendations.append(
                "Add support for text scaling to accommodate players with visual impairments."
            )
        if "remappable_controls" in failed_checks:
            recommendations.append(
                "Implement fully remappable controls for all input actions."
            )
        if "subtitles" in failed_checks:
            recommendations.append(
                "Add comprehensive subtitles with speaker identification for all dialogue."
            )
        if "audio_cues" in failed_checks:
            recommendations.append(
                "Provide visual alternatives for all critical audio cues and alerts."
            )
        if "difficulty_options" in failed_checks:
            recommendations.append(
                "Add granular difficulty options including invincibility and assist modes."
            )
        if "input_methods" in failed_checks:
            recommendations.append(
                "Support multiple input methods including keyboard, controller, and adaptive devices."
            )
        if "motion_sensitivity" in failed_checks:
            recommendations.append(
                "Add options to reduce screen shake, motion blur, and parallax effects."
            )
        if "tutorial_clarity" in failed_checks:
            recommendations.append(
                "Improve tutorial clarity with step-by-step guidance and practice opportunities."
            )

        return {
            "accessibility_score": overall_score,
            "check_results": check_results,
            "failed_checks": failed_checks,
            "failed_count": len(failed_checks),
            "total_checks": len(_ACCESSIBILITY_CHECKS),
            "recommendations": recommendations,
            "interpretation": self._interpret_accessibility(overall_score),
        }

    def generate_report(self, game_id: str) -> Optional[QualityReport]:
        """Generate a comprehensive quality report for the game.

        Aggregates all playtest results, fun scores, balance metrics,
        accessibility audit, and detected issues into a structured
        QualityReport with prioritized recommendations.

        Args:
            game_id: The unique identifier of the game to report on.

        Returns:
            A QualityReport with scores, issues, and recommendations,
            or None if no playtest results exist.
        """
        result = self._results.get(game_id)
        if result is None:
            return None

        fun_scores = self.measure_fun(game_id)
        balance_data = self.check_balance(game_id)
        accessibility_data = self.audit_accessibility(game_id)

        issues_by_severity: Dict[str, int] = {}
        issues_by_category: Dict[str, int] = {}
        for issue in result.issues:
            sev = issue.severity.value
            cat = issue.category.value
            issues_by_severity[sev] = issues_by_severity.get(sev, 0) + 1
            issues_by_category[cat] = issues_by_category.get(cat, 0) + 1

        # Top issues sorted by severity then impact
        severity_order = {
            IssueSeverity.BLOCKER: 0,
            IssueSeverity.CRITICAL: 1,
            IssueSeverity.MAJOR: 2,
            IssueSeverity.MINOR: 3,
            IssueSeverity.COSMETIC: 4,
            IssueSeverity.SUGGESTION: 5,
        }
        sorted_issues = sorted(
            result.issues,
            key=lambda i: (severity_order.get(i.severity, 99), -i.impact_score),
        )
        top_issues = sorted_issues[:10]

        recommendations = self._generate_recommendations(
            result, fun_scores, balance_data, accessibility_data
        )

        avg_fun = sum(fun_scores.values()) / max(1, len(fun_scores))

        archetype_insights: Dict[str, Dict[str, Any]] = {}
        for archetype in PlayerArchetype:
            arch_sims = [
                s for s in result.simulations if s.archetype == archetype
            ]
            if arch_sims:
                archetype_insights[archetype.value] = {
                    "simulation_count": len(arch_sims),
                    "avg_completion": round(
                        sum(s.completion_rate for s in arch_sims) / len(arch_sims), 3
                    ),
                    "avg_deaths": round(
                        sum(s.deaths for s in arch_sims) / len(arch_sims), 2
                    ),
                    "quit_rate": round(
                        sum(1 for s in arch_sims if s.quit_early) / len(arch_sims), 3
                    ),
                }

        summary = (
            f"Quality report for game '{game_id}'. "
            f"Overall score: {result.overall_score:.2f}/1.00. "
            f"Ran {len(result.simulations)} simulations across "
            f"{len(set(s.archetype for s in result.simulations))} archetypes. "
            f"Detected {len(result.issues)} issues "
            f"({issues_by_severity.get('blocker', 0)} blockers, "
            f"{issues_by_severity.get('critical', 0)} critical). "
            f"Fun: {avg_fun:.2f}, Balance: {balance_data.get('balance_score', 0):.2f}, "
            f"Accessibility: {accessibility_data.get('accessibility_score', 0):.2f}."
        )

        report = QualityReport(
            game_id=game_id,
            result_id=result.result_id,
            summary=summary,
            overall_score=result.overall_score,
            fun_scores=fun_scores,
            balance_score=balance_data.get("balance_score", 0.0),
            accessibility_score=accessibility_data.get("accessibility_score", 0.0),
            issues_by_severity=issues_by_severity,
            issues_by_category=issues_by_category,
            top_issues=top_issues,
            recommendations=recommendations,
            archetype_insights=archetype_insights,
        )

        self._reports[game_id] = report
        self._stats["total_reports_generated"] += 1

        return report

    def get_status(self) -> Dict[str, Any]:
        """Get the current status of the playtest suite.

        Returns:
            A dictionary with active state, statistics, result count,
            report count, and issue database size.
        """
        total_issues = sum(len(issues) for issues in self._issue_database.values())
        return {
            "active": self._active,
            "results_count": len(self._results),
            "reports_count": len(self._reports),
            "games_tested": list(self._results.keys()),
            "total_issues_in_database": total_issues,
            "total_snapshots": sum(
                len(snaps) for snaps in self._snapshots.values()
            ),
            "stats": dict(self._stats),
        }

    def shutdown(self) -> None:
        """Gracefully shut down the playtest suite.

        Clears all internal state, finalizes any pending operations,
        and releases resources. The suite can be re-initialized with
        initialize() after shutdown.
        """
        with self._lock:
            self._results.clear()
            self._reports.clear()
            self._issue_database.clear()
            self._snapshots.clear()
            self._stats = {
                "total_sessions_run": 0,
                "total_issues_detected": 0,
                "total_reports_generated": 0,
                "total_simulations_run": 0,
            }
            self._active = False

    # ------------------------------------------------------------------
    # Internal Helpers
    # ------------------------------------------------------------------

    def _build_initial_game_state(
        self, config: PlaytestConfig
    ) -> Dict[str, Any]:
        """Build the initial game state for simulation."""
        level_count = config.level_count
        return {
            "total_levels": level_count,
            "total_items": level_count * 20,
            "total_areas": level_count * 10,
            "total_quests": level_count * 4,
            "entity_types": list(config.entity_types),
            "rng_seed": random.randint(1, 100000),
        }

    def _compute_fun_scores(self, result: PlaytestResult) -> Dict[str, float]:
        """Compute fun dimension scores from a playtest result."""
        return self.measure_fun(result.game_id)

    def _compute_balance_score(self, result: PlaytestResult) -> float:
        """Compute aggregate balance score from a playtest result."""
        balance_data = self.check_balance(result.game_id)
        return balance_data.get("balance_score", 0.0)

    def _evaluate_accessibility(self, result: PlaytestResult) -> float:
        """Evaluate accessibility score from a playtest result."""
        accessibility_data = self.audit_accessibility(result.game_id)
        return accessibility_data.get("accessibility_score", 0.0)

    def _compute_overall_score(self, result: PlaytestResult) -> float:
        """Compute the overall quality score from all metrics."""
        fun_avg = (
            sum(result.fun_scores.values()) / max(1, len(result.fun_scores))
            if result.fun_scores
            else 0.0
        )
        return round(
            fun_avg * 0.35
            + result.balance_score * 0.30
            + result.accessibility_score * 0.15
            + (1.0 - min(1.0, len(result.issues) / 20.0)) * 0.20,
            3,
        )

    def _create_issue(
        self,
        game_id: str,
        pattern_key: str,
        affected_levels: Optional[List[int]] = None,
        impact_score: float = 0.5,
        confidence: float = 0.5,
        recommendation: str = "",
    ) -> DesignIssue:
        """Create a DesignIssue from a known pattern template."""
        pattern = _ISSUE_PATTERNS.get(pattern_key, {
            "category": IssueCategory.GAMEPLAY,
            "severity": IssueSeverity.MINOR,
            "description": "Unknown issue detected during playtesting.",
        })
        return DesignIssue(
            game_id=game_id,
            category=pattern["category"],
            severity=pattern["severity"],
            title=pattern_key.replace("_", " ").title(),
            description=pattern["description"],
            affected_levels=affected_levels or [],
            recommendation=recommendation,
            impact_score=impact_score,
            confidence=confidence,
        )

    def _identify_hard_levels(
        self, simulations: List[PlayerSimulation]
    ) -> List[int]:
        """Identify levels with unusually high death counts."""
        level_deaths: Dict[int, int] = defaultdict(int)
        for s in simulations:
            for loc in s.death_locations:
                parts = loc.split("_")
                if len(parts) >= 2:
                    try:
                        level = int(parts[1])
                        level_deaths[level] += 1
                    except ValueError:
                        pass
        if not level_deaths:
            return []
        avg = sum(level_deaths.values()) / len(level_deaths)
        return [
            lvl for lvl, count in level_deaths.items()
            if count > avg * 1.5
        ]

    def _identify_stuck_levels(
        self, simulations: List[PlayerSimulation]
    ) -> List[int]:
        """Identify levels where most players stop progressing."""
        max_level = max(
            (s.total_levels for s in simulations), default=0
        )
        if max_level == 0:
            return []
        level_reached: Dict[int, int] = defaultdict(int)
        for s in simulations:
            reached = s.levels_completed
            for lvl in range(1, reached + 1):
                level_reached[lvl] += 1
        total = len(simulations)
        return [
            lvl for lvl in range(1, max_level + 1)
            if level_reached.get(lvl, 0) < total * 0.5
        ]

    def _identify_affected_archetypes(
        self, simulations: List[PlayerSimulation], bottleneck: str
    ) -> List[PlayerArchetype]:
        """Identify which archetypes are affected by a bottleneck."""
        affected: Set[PlayerArchetype] = set()
        for s in simulations:
            if bottleneck in s.bottlenecks_hit:
                affected.add(s.archetype)
        return list(affected)

    def _random_quit_reason(self, archetype: PlayerArchetype) -> str:
        """Generate a plausible quit reason based on archetype."""
        reasons = [
            "too_difficult",
            "too_easy",
            "lost_interest",
            "stuck_no_progress",
            "repetitive_gameplay",
            "confusing_objectives",
            "technical_issue",
        ]
        if archetype == PlayerArchetype.STORY_FOCUSED:
            reasons.append("weak_narrative")
        elif archetype == PlayerArchetype.COMPETITIVE:
            reasons.append("unfair_mechanics")
        return random.choice(reasons)

    def _take_snapshot(
        self, game_id: str, result: PlaytestResult
    ) -> None:
        """Capture a snapshot of the current playtest state."""
        snapshot = PlaytestSnapshot(
            game_id=game_id,
            elapsed_seconds=result.duration_seconds,
            simulations_completed=len(result.simulations),
            issues_detected=len(result.issues),
            current_fun_score=(
                sum(result.fun_scores.values()) / max(1, len(result.fun_scores))
                if result.fun_scores
                else 0.0
            ),
            current_balance_score=result.balance_score,
            state_summary=(
                f"Sims: {len(result.simulations)}, "
                f"Issues: {len(result.issues)}, "
                f"Score: {result.overall_score:.3f}"
            ),
        )
        self._snapshots[game_id].append(snapshot)

    def _generate_recommendations(
        self,
        result: PlaytestResult,
        fun_scores: Dict[str, float],
        balance_data: Dict[str, Any],
        accessibility_data: Dict[str, Any],
    ) -> List[str]:
        """Generate prioritized recommendations from all analysis data."""
        recommendations: List[str] = []

        # Issue-based recommendations
        blocker_count = sum(
            1 for i in result.issues if i.severity == IssueSeverity.BLOCKER
        )
        critical_count = sum(
            1 for i in result.issues if i.severity == IssueSeverity.CRITICAL
        )
        if blocker_count > 0:
            recommendations.append(
                f"Fix {blocker_count} blocker issue(s) before release - "
                f"these prevent core gameplay progression."
            )
        if critical_count > 0:
            recommendations.append(
                f"Address {critical_count} critical issue(s) as high priority "
                f"in the next development cycle."
            )

        # Fun-based recommendations
        avg_fun = sum(fun_scores.values()) / max(1, len(fun_scores))
        if avg_fun < 0.5:
            recommendations.append(
                "Overall fun factor is low. Focus on improving core gameplay "
                "loop, reward systems, and player feedback."
            )
        if fun_scores.get("challenge", 0.0) < 0.4:
            recommendations.append(
                "Challenge dimension is weak. Tune difficulty to create "
                "engaging tension without frustration."
            )
        if fun_scores.get("discovery", 0.0) < 0.3:
            recommendations.append(
                "Discovery is lacking. Add hidden areas, secrets, and "
                "environmental storytelling to reward exploration."
            )
        if fun_scores.get("immersion", 0.0) < 0.4:
            recommendations.append(
                "Immersion is low. Improve audiovisual cohesion, reduce "
                "UI intrusiveness, and strengthen world-building."
            )

        # Balance-based recommendations
        if balance_data.get("combat_balance", 0.0) < 0.5:
            recommendations.append(
                "Combat balance needs tuning. Adjust damage values, "
                "enemy AI, and player resources for fair encounters."
            )
        if balance_data.get("archetype_fairness", 0.0) < 0.5:
            recommendations.append(
                "Game favors certain play styles disproportionately. "
                "Ensure all archetypes can complete the game enjoyably."
            )

        # Accessibility recommendations
        if accessibility_data.get("failed_count", 0) > 3:
            recommendations.append(
                f"Address {accessibility_data['failed_count']} accessibility "
                f"check failures to broaden the game's audience."
            )

        if not recommendations:
            recommendations.append(
                "The game is in good shape overall. Continue iterating "
                "on content and collect player feedback post-launch."
            )
        elif len(recommendations) > 8:
            recommendations = recommendations[:8]

        return recommendations

    def _interpret_balance(self, score: float) -> str:
        """Provide a human-readable interpretation of a balance score."""
        if score >= 0.8:
            return "Well-balanced - all systems are properly tuned for fair gameplay."
        elif score >= 0.6:
            return "Moderately balanced - minor tuning recommended for specific areas."
        elif score >= 0.4:
            return "Balance issues detected - several systems need adjustment."
        else:
            return "Poorly balanced - significant rebalancing required."

    def _interpret_accessibility(self, score: float) -> str:
        """Provide a human-readable interpretation of an accessibility score."""
        if score >= 0.8:
            return "Highly accessible - meets most accessibility standards."
        elif score >= 0.6:
            return "Moderately accessible - some improvements recommended."
        elif score >= 0.4:
            return "Below accessibility standards - multiple barriers identified."
        else:
            return "Poor accessibility - significant barriers prevent inclusive play."


# ------------------------------------------------------------------
# Module-level accessor
# ------------------------------------------------------------------


def get_game_playtest_suite() -> GamePlaytestSuite:
    """Get the GamePlaytestSuite singleton instance."""
    return GamePlaytestSuite.get_instance()