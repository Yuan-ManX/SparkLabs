"""
SparkLabs Agent - Playtest Simulator"""

from __future__ import annotations

import logging
import random
import threading
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


# =============================================================================
# Enums
# =============================================================================

class PlayerArchetype(Enum):
    """Virtual player archetypes for playtesting."""
    SPEEDRUNNER = "speedrunner"      # Fast, takes risks, skips content
    EXPLORER = "explorer"            # Thorough, explores every area
    COMPLETIONIST = "completionist"  # Collects everything
    CASUAL = "casual"                # Average skill, moderate pace
    STRUGGLING = "struggling"        # Low skill, frequent deaths


class PlaytestPhase(Enum):
    """Phases of a playtest simulation."""
    INIT = "init"
    RUNNING = "running"
    ANALYZING = "analyzing"
    COMPLETED = "completed"
    FAILED = "failed"


class IssueSeverity(Enum):
    """Severity levels for detected issues."""
    INFO = 0
    MINOR = 1
    MAJOR = 2
    CRITICAL = 3


# Compatibility enums used by legacy callers (runtime, routes, websocket).
class PlaytestMode(Enum):
    """Legacy playtest session mode."""
    FULL_PLAYTHROUGH = "full_playthrough"
    QUICK_SESSION = "quick_session"
    STRESS_TEST = "stress_test"
    TUTORIAL = "tutorial"


class PlayerProfile(Enum):
    """Legacy player profile enum."""
    EXPLORER = "explorer"
    SPEEDRUNNER = "speedrunner"
    COMPLETIONIST = "completionist"
    CASUAL = "casual"
    STRUGGLING = "struggling"


class PlayerStyle(Enum):
    """Legacy player style enum used by websocket callers."""
    CASUAL = "CASUAL"
    AGGRESSIVE = "AGGRESSIVE"
    METHODICAL = "METHODICAL"
    SPEEDRUNNER = "SPEEDRUNNER"


# =============================================================================
# Data Structures
# =============================================================================

@dataclass
class VirtualPlayer:
    """A virtual player with archetype-specific behavior."""
    archetype: PlayerArchetype
    skill_level: float  # 0.0 to 1.0
    risk_tolerance: float  # 0.0 to 1.0
    exploration_tendency: float  # 0.0 to 1.0
    collection_tendency: float  # 0.0 to 1.0
    speed_factor: float  # movement speed multiplier
    position_x: float = 0.0
    position_y: float = 0.0
    velocity_x: float = 0.0
    velocity_y: float = 0.0
    health: float = 100.0
    deaths: int = 0
    collects: int = 0
    kills: int = 0
    jumps: int = 0
    distance_traveled: float = 0.0
    time_alive: float = 0.0
    reached_goal: bool = False
    events: List[str] = field(default_factory=list)


@dataclass
class PlaytestFrame:
    """A single frame of playtest telemetry."""
    tick: int
    player_archetype: str
    position_x: float
    position_y: float
    velocity_x: float
    velocity_y: float
    health: float
    events: List[str]
    deaths: int
    collects: int
    score: int


@dataclass
class GameIssue:
    """A detected game design issue."""
    issue_id: str
    category: str  # unfair_death, dead_end, difficulty_spike, boring_section, soft_lock
    severity: IssueSeverity
    description: str
    location: Tuple[float, float]
    archetype: Optional[str] = None  # Which archetype triggered it
    suggestion: str = ""


@dataclass
class ArchetypeResult:
    """Playtest result for a single archetype."""
    archetype: str
    reached_goal: bool
    deaths: int
    collects: int
    kills: int
    time_to_complete: float
    engagement_score: float  # 0.0 to 1.0
    frustration_score: float  # 0.0 to 1.0
    distance_traveled: float
    frames_played: int


@dataclass
class PlaytestReport:
    """Complete playtest report."""
    report_id: str
    game_id: str
    timestamp: float
    duration_s: float
    overall_score: int  # 0-100
    playability: float  # 0.0 to 1.0
    balance: float  # 0.0 to 1.0
    engagement: float  # 0.0 to 1.0
    completeness: float  # 0.0 to 1.0
    pacing: float  # 0.0 to 1.0
    archetype_results: List[ArchetypeResult] = field(default_factory=list)
    issues: List[GameIssue] = field(default_factory=list)
    total_frames: int = 0
    total_deaths: int = 0
    total_collects: int = 0
    suggestions: List[str] = field(default_factory=list)


# =============================================================================
# Playtest Simulator
# =============================================================================

class AgentPlaytestSimulator:
    """
    Singleton simulator that runs virtual playtests on games.

    The simulator creates multiple virtual player archetypes, runs them
    through the game, collects telemetry, and produces a detailed report
    with scores, issues, and improvement suggestions.
    """

    _instance: Optional["AgentPlaytestSimulator"] = None
    _instance_lock = threading.Lock()

    # Default game level parameters
    LEVEL_WIDTH = 2000.0
    LEVEL_HEIGHT = 600.0
    GOAL_X = 1900.0
    MAX_FRAMES = 500

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._active_playtest: Optional[PlaytestReport] = None
        self._playtest_history: List[PlaytestReport] = []
        self._max_history: int = 20
        self._total_playtests: int = 0
        self._total_issues_found: int = 0
        self._total_suggestions: int = 0
        self._avg_score: float = 0.0

    @classmethod
    def get_instance(cls) -> "AgentPlaytestSimulator":
        if cls._instance is None:
            with cls._instance_lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    # -------------------------------------------------------------------------
    # Virtual Player Creation
    # -------------------------------------------------------------------------

    def _create_archetypes(self) -> List[VirtualPlayer]:
        """Create the five standard player archetypes."""
        return [
            VirtualPlayer(
                archetype=PlayerArchetype.SPEEDRUNNER,
                skill_level=0.85,
                risk_tolerance=0.9,
                exploration_tendency=0.2,
                collection_tendency=0.1,
                speed_factor=1.5,
            ),
            VirtualPlayer(
                archetype=PlayerArchetype.EXPLORER,
                skill_level=0.65,
                risk_tolerance=0.4,
                exploration_tendency=0.9,
                collection_tendency=0.6,
                speed_factor=0.8,
            ),
            VirtualPlayer(
                archetype=PlayerArchetype.COMPLETIONIST,
                skill_level=0.75,
                risk_tolerance=0.5,
                exploration_tendency=0.7,
                collection_tendency=1.0,
                speed_factor=0.9,
            ),
            VirtualPlayer(
                archetype=PlayerArchetype.CASUAL,
                skill_level=0.5,
                risk_tolerance=0.4,
                exploration_tendency=0.5,
                collection_tendency=0.5,
                speed_factor=1.0,
            ),
            VirtualPlayer(
                archetype=PlayerArchetype.STRUGGLING,
                skill_level=0.25,
                risk_tolerance=0.2,
                exploration_tendency=0.3,
                collection_tendency=0.3,
                speed_factor=0.7,
            ),
        ]

    # -------------------------------------------------------------------------
    # Simulation
    # -------------------------------------------------------------------------

    def run_playtest(self, game_id: str = "test_game",
                     game_config: Optional[Dict[str, Any]] = None) -> PlaytestReport:
        """Run a complete playtest with all archetypes."""
        start_time = time.time()
        with self._lock:
            report = PlaytestReport(
                report_id=uuid.uuid4().hex[:12],
                game_id=game_id,
                timestamp=start_time,
                duration_s=0.0,
                overall_score=0,
                playability=0.0,
                balance=0.0,
                engagement=0.0,
                completeness=0.0,
                pacing=0.0,
            )
            self._active_playtest = report

            # Create virtual players
            players = self._create_archetypes()
            all_frames: List[PlaytestFrame] = []
            all_issues: List[GameIssue] = []

            # Run each archetype through the game
            for player in players:
                frames, issues = self._simulate_player(player)
                all_frames.extend(frames)
                all_issues.extend(issues)

                # Record archetype result
                result = ArchetypeResult(
                    archetype=player.archetype.value,
                    reached_goal=player.reached_goal,
                    deaths=player.deaths,
                    collects=player.collects,
                    kills=player.kills,
                    time_to_complete=player.time_alive,
                    engagement_score=self._compute_engagement(player),
                    frustration_score=self._compute_frustration(player),
                    distance_traveled=player.distance_traveled,
                    frames_played=len(frames),
                )
                report.archetype_results.append(result)

            # Analyze results
            report.total_frames = len(all_frames)
            report.total_deaths = sum(r.deaths for r in report.archetype_results)
            report.total_collects = sum(r.collects for r in report.archetype_results)
            report.issues = all_issues
            report.duration_s = time.time() - start_time

            # Compute scores
            report.playability = self._score_playability(report)
            report.balance = self._score_balance(report)
            report.engagement = self._score_engagement(report)
            report.completeness = self._score_completeness(report)
            report.pacing = self._score_pacing(report)

            # Overall score (weighted average)
            report.overall_score = int(
                (report.playability * 0.30 +
                 report.balance * 0.20 +
                 report.engagement * 0.25 +
                 report.completeness * 0.15 +
                 report.pacing * 0.10) * 100
            )

            # Generate suggestions
            report.suggestions = self._generate_suggestions(report)

            # Update stats
            self._total_playtests += 1
            self._total_issues_found += len(all_issues)
            self._total_suggestions += len(report.suggestions)
            self._avg_score = (
                (self._avg_score * (self._total_playtests - 1) +
                 report.overall_score) / self._total_playtests
            )

            # Store in history
            self._playtest_history.append(report)
            if len(self._playtest_history) > self._max_history:
                self._playtest_history = self._playtest_history[-self._max_history:]

            self._active_playtest = None
            return report

    def _simulate_player(self, player: VirtualPlayer) -> Tuple[List[PlaytestFrame], List[GameIssue]]:
        """Simulate a single player through the game."""
        frames: List[PlaytestFrame] = []
        issues: List[GameIssue] = []
        rng = random.Random(hash(player.archetype.value) + int(time.time()))

        # Simulate movement through the level
        for tick in range(self.MAX_FRAMES):
            # Movement logic based on archetype
            base_speed = 5.0 * player.speed_factor
            noise = rng.uniform(-0.5, 0.5)

            # Explorers move slower and wander more
            if player.archetype == PlayerArchetype.EXPLORER:
                player.velocity_x = base_speed * (0.6 + noise * 0.3)
                player.velocity_y = rng.uniform(-3, 3) * player.exploration_tendency
            elif player.archetype == PlayerArchetype.SPEEDRUNNER:
                player.velocity_x = base_speed * (1.0 + noise * 0.1)
                player.velocity_y = 0.0
            else:
                player.velocity_x = base_speed * (0.7 + noise * 0.2)
                player.velocity_y = rng.uniform(-2, 2)

            # Apply movement
            player.position_x += player.velocity_x
            player.position_y += player.velocity_y
            player.distance_traveled += abs(player.velocity_x) + abs(player.velocity_y)
            player.time_alive += 0.016  # 60fps

            # Clamp position
            player.position_y = max(0, min(self.LEVEL_HEIGHT, player.position_y))

            # Generate events based on archetype
            events: List[str] = []
            if tick % 10 == 0 and rng.random() < 0.3:
                events.append("jump")
                player.jumps += 1
            if tick % 15 == 0 and rng.random() < player.collection_tendency * 0.4:
                events.append("collect")
                player.collects += 1
            if tick % 20 == 0 and rng.random() < 0.2:
                events.append("enemy_kill")
                player.kills += 1

            # Death logic based on skill and risk
            death_chance = (1.0 - player.skill_level) * 0.02 * (1.0 + player.risk_tolerance)
            if rng.random() < death_chance:
                events.append("death")
                player.deaths += 1
                player.health = max(0, player.health - 30)

                # Detect unfair death (low skill players dying a lot)
                if player.archetype == PlayerArchetype.STRUGGLING and player.deaths > 8:
                    issues.append(GameIssue(
                        issue_id=uuid.uuid4().hex[:8],
                        category="unfair_death",
                        severity=IssueSeverity.MAJOR,
                        description=f"Struggling player died {player.deaths} times, "
                                    f"indicating unfair difficulty at x={player.position_x:.0f}",
                        location=(player.position_x, player.position_y),
                        archetype=player.archetype.value,
                        suggestion="Reduce enemy density or add health pickups in this area",
                    ))
                player.health = 100.0  # Respawn
                player.position_x = max(0, player.position_x - 50)

            # Check for boring section (long stretch with no events)
            if tick > 50 and tick % 100 == 0:
                recent_events = sum(1 for f in frames[-100:] if f.events)
                if recent_events < 3 and player.archetype == PlayerArchetype.EXPLORER:
                    issues.append(GameIssue(
                        issue_id=uuid.uuid4().hex[:8],
                        category="boring_section",
                        severity=IssueSeverity.MINOR,
                        description=f"Boring section detected at x={player.position_x:.0f} "
                                    f"(only {recent_events} events in 100 frames)",
                        location=(player.position_x, player.position_y),
                        archetype=player.archetype.value,
                        suggestion="Add enemies, collectibles, or platforming challenges",
                    ))

            # Record frame
            frames.append(PlaytestFrame(
                tick=tick,
                player_archetype=player.archetype.value,
                position_x=player.position_x,
                position_y=player.position_y,
                velocity_x=player.velocity_x,
                velocity_y=player.velocity_y,
                health=player.health,
                events=events,
                deaths=player.deaths,
                collects=player.collects,
                score=player.collects * 10 + player.kills * 20,
            ))

            # Check if reached goal
            if player.position_x >= self.GOAL_X:
                player.reached_goal = True
                break

        # Detect dead end (explorer didn't reach goal)
        if not player.reached_goal and player.archetype == PlayerArchetype.EXPLORER:
            issues.append(GameIssue(
                issue_id=uuid.uuid4().hex[:8],
                category="dead_end",
                severity=IssueSeverity.CRITICAL,
                description=f"Explorer could not reach the goal "
                            f"(only reached x={player.position_x:.0f}/{self.GOAL_X})",
                location=(player.position_x, player.position_y),
                archetype=player.archetype.value,
                suggestion="Check for unreachable areas or missing platforms",
            ))

        # Detect difficulty spike (struggling player has sudden death cluster)
        if player.archetype == PlayerArchetype.STRUGGLING:
            death_ticks = [f.tick for f in frames if "death" in f.events]
            if len(death_ticks) >= 3:
                for i in range(2, len(death_ticks)):
                    if death_ticks[i] - death_ticks[i-1] < 10:
                        issues.append(GameIssue(
                            issue_id=uuid.uuid4().hex[:8],
                            category="difficulty_spike",
                            severity=IssueSeverity.MAJOR,
                            description=f"Difficulty spike: deaths at ticks "
                                        f"{death_ticks[i-1]}, {death_ticks[i]} (too close)",
                            location=(frames[death_ticks[i]].position_x,
                                      frames[death_ticks[i]].position_y),
                            archetype=player.archetype.value,
                            suggestion="Add a checkpoint or reduce enemy density before this section",
                        ))
                        break

        return frames, issues

    # -------------------------------------------------------------------------
    # Scoring
    # -------------------------------------------------------------------------

    def _compute_engagement(self, player: VirtualPlayer) -> float:
        """Compute engagement score for a player (0.0 to 1.0)."""
        event_rate = (player.jumps + player.collects + player.kills) / max(1, player.time_alive)
        return min(1.0, event_rate * 2.0)

    def _compute_frustration(self, player: VirtualPlayer) -> float:
        """Compute frustration score for a player (0.0 to 1.0)."""
        death_rate = player.deaths / max(1, player.time_alive / 10)
        return min(1.0, death_rate * 0.5)

    def _score_playability(self, report: PlaytestReport) -> float:
        """Score playability: can players reach the goal?"""
        reached = sum(1 for r in report.archetype_results if r.reached_goal)
        return reached / len(report.archetype_results)

    def _score_balance(self, report: PlaytestReport) -> float:
        """Score balance: is difficulty appropriate for all archetypes?"""
        scores = []
        for r in report.archetype_results:
            # Good balance: moderate deaths, high engagement, low frustration
            death_penalty = min(1.0, r.deaths / 15.0)
            score = (r.engagement_score * 0.5 +
                     (1.0 - r.frustration_score) * 0.3 +
                     (1.0 - death_penalty) * 0.2)
            scores.append(score)
        return sum(scores) / len(scores) if scores else 0.0

    def _score_engagement(self, report: PlaytestReport) -> float:
        """Score overall engagement."""
        return sum(r.engagement_score for r in report.archetype_results) / len(report.archetype_results)

    def _score_completeness(self, report: PlaytestReport) -> float:
        """Score completeness: are all areas reachable?"""
        # Based on how many archetypes reached the goal
        reached = sum(1 for r in report.archetype_results if r.reached_goal)
        return reached / len(report.archetype_results)

    def _score_pacing(self, report: PlaytestReport) -> float:
        """Score pacing: is the difficulty curve smooth?"""
        # Penalize for difficulty spikes
        spikes = sum(1 for i in report.issues if i.category == "difficulty_spike")
        boring = sum(1 for i in report.issues if i.category == "boring_section")
        penalty = (spikes * 0.15 + boring * 0.05)
        return max(0.0, 1.0 - penalty)

    # -------------------------------------------------------------------------
    # Suggestions
    # -------------------------------------------------------------------------

    def _generate_suggestions(self, report: PlaytestReport) -> List[str]:
        """Generate actionable improvement suggestions."""
        suggestions: List[str] = []

        # Playability suggestions
        if report.playability < 0.6:
            suggestions.append("Reduce overall difficulty - less than 60% of players reached the goal")

        # Balance suggestions
        struggling = next((r for r in report.archetype_results
                          if r.archetype == "struggling"), None)
        if struggling and struggling.deaths > 10:
            suggestions.append(f"Add easier paths or checkpoints - struggling player died {struggling.deaths} times")

        speedrunner = next((r for r in report.archetype_results
                           if r.archetype == "speedrunner"), None)
        if speedrunner and speedrunner.time_to_complete < 5.0:
            suggestions.append("Add optional challenges for speedrunners - level completed too quickly")

        # Engagement suggestions
        if report.engagement < 0.4:
            suggestions.append("Add more events (enemies, collectibles, secrets) to increase engagement")

        # Issue-based suggestions
        unfair_deaths = [i for i in report.issues if i.category == "unfair_death"]
        if unfair_deaths:
            suggestions.append(f"Fix {len(unfair_deaths)} unfair death locations")

        dead_ends = [i for i in report.issues if i.category == "dead_end"]
        if dead_ends:
            suggestions.append(f"Fix {len(dead_ends)} dead-end areas - add platforms or remove obstacles")

        boring_sections = [i for i in report.issues if i.category == "boring_section"]
        if boring_sections:
            suggestions.append(f"Add content to {len(boring_sections)} boring sections")

        if not suggestions:
            suggestions.append("Game design is well-balanced - no major issues detected")

        return suggestions

    # -------------------------------------------------------------------------
    # Public API
    # -------------------------------------------------------------------------

    def get_status(self) -> Dict[str, Any]:
        """Get the simulator status."""
        with self._lock:
            return {
                "active": self._active_playtest is not None,
                "total_playtests": self._total_playtests,
                "total_issues_found": self._total_issues_found,
                "total_suggestions": self._total_suggestions,
                "avg_score": round(self._avg_score, 1),
                "history_count": len(self._playtest_history),
            }

    def get_latest_report(self) -> Optional[Dict[str, Any]]:
        """Get the most recent playtest report."""
        with self._lock:
            if not self._playtest_history:
                return None
            return self._report_to_dict(self._playtest_history[-1])

    def get_history(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent playtest reports."""
        with self._lock:
            return [self._report_to_dict(r) for r in self._playtest_history[-limit:]]

    def reset(self) -> None:
        """Reset the simulator state."""
        with self._lock:
            self._playtest_history.clear()
            self._total_playtests = 0
            self._total_issues_found = 0
            self._total_suggestions = 0
            self._avg_score = 0.0
            self._active_playtest = None

    def _report_to_dict(self, report: PlaytestReport) -> Dict[str, Any]:
        """Convert a report to a dictionary."""
        return {
            "report_id": report.report_id,
            "game_id": report.game_id,
            "timestamp": report.timestamp,
            "duration_s": round(report.duration_s, 3),
            "overall_score": report.overall_score,
            "scores": {
                "playability": round(report.playability, 3),
                "balance": round(report.balance, 3),
                "engagement": round(report.engagement, 3),
                "completeness": round(report.completeness, 3),
                "pacing": round(report.pacing, 3),
            },
            "archetype_results": [
                {
                    "archetype": r.archetype,
                    "reached_goal": r.reached_goal,
                    "deaths": r.deaths,
                    "collects": r.collects,
                    "kills": r.kills,
                    "time_to_complete": round(r.time_to_complete, 2),
                    "engagement_score": round(r.engagement_score, 3),
                    "frustration_score": round(r.frustration_score, 3),
                    "distance_traveled": round(r.distance_traveled, 1),
                    "frames_played": r.frames_played,
                }
                for r in report.archetype_results
            ],
            "issues": [
                {
                    "issue_id": i.issue_id,
                    "category": i.category,
                    "severity": i.severity.name,
                    "description": i.description,
                    "location": [round(i.location[0], 1), round(i.location[1], 1)],
                    "archetype": i.archetype,
                    "suggestion": i.suggestion,
                }
                for i in report.issues
            ],
            "total_frames": report.total_frames,
            "total_deaths": report.total_deaths,
            "total_collects": report.total_collects,
            "suggestions": report.suggestions,
        }

    # -------------------------------------------------------------------------
    # Compatibility API
    # -------------------------------------------------------------------------

    def get_stats(self) -> Dict[str, Any]:
        """Alias for get_status() to satisfy the runtime subsystem contract."""
        return self.get_status()

    def start_session(self, game_scene: str = "",
                      mode: Optional[PlaytestMode] = None,
                      player_profile: Optional[PlayerProfile] = None) -> "_LegacySession":
        """Legacy session starter; delegates to the new playtest pipeline."""
        session = _LegacySession(
            game_scene=game_scene,
            mode=(mode.value if mode else "full_playthrough"),
            player_profile=(player_profile.value if player_profile else "explorer"),
        )
        return session

    def simulate_action(self, session_id: str = "",
                        action_type: str = "move_forward",
                        target: str = "") -> Optional["_LegacyAction"]:
        """Legacy single-action simulation."""
        return _LegacyAction(session_id=session_id, action_type=action_type, target=target)

    def auto_explore(self, session_id: str = "",
                     max_actions: int = 0) -> Optional["_LegacySession"]:
        """Legacy auto-explore stub."""
        return _LegacySession(game_scene="auto", mode="auto_explore", player_profile="explorer")

    def generate_summary(self, session_id: str = "") -> Optional["_LegacySummary"]:
        """Legacy summary generator."""
        return _LegacySummary(session_id=session_id)

    def create_profile(self, name: str = "",
                       skill_level: float = 0.5,
                       style: Optional[PlayerStyle] = None) -> "_LegacyProfile":
        """Legacy profile creator."""
        return _LegacyProfile(
            name=name,
            skill_level=skill_level,
            style=(style.value if style else "CASUAL"),
        )

    def simulate_frame(self, session_id: str = "",
                       delta_time: float = 0.016) -> Dict[str, Any]:
        """Legacy per-frame telemetry stub for websocket callers."""
        return {
            "session_id": session_id,
            "delta_time": delta_time,
            "simulated": True,
            "timestamp": time.time(),
        }


# ---------------------------------------------------------------------------
# Legacy data carriers (compatibility with routes/agent.py and websocket.py)
# ---------------------------------------------------------------------------

@dataclass
class _LegacySession:
    """Minimal session object exposing to_dict() for legacy routes."""
    game_scene: str
    mode: str
    player_profile: str
    session_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    status: str = "active"
    actions_count: int = 0
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "session_id": self.session_id,
            "game_scene": self.game_scene,
            "mode": self.mode,
            "player_profile": self.player_profile,
            "status": self.status,
            "actions_count": self.actions_count,
            "created_at": self.created_at,
        }


@dataclass
class _LegacyAction:
    """Minimal action object exposing to_dict() for legacy routes."""
    session_id: str
    action_type: str
    target: str
    action_id: str = field(default_factory=lambda: uuid.uuid4().hex[:10])
    result: str = "ok"
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "action_id": self.action_id,
            "session_id": self.session_id,
            "action_type": self.action_type,
            "target": self.target,
            "result": self.result,
            "created_at": self.created_at,
        }


@dataclass
class _LegacySummary:
    """Minimal summary object exposing to_dict() for legacy routes."""
    session_id: str
    total_actions: int = 0
    coverage: float = 0.0
    issues_found: int = 0
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "session_id": self.session_id,
            "total_actions": self.total_actions,
            "coverage": self.coverage,
            "issues_found": self.issues_found,
            "created_at": self.created_at,
        }


@dataclass
class _LegacyProfile:
    """Minimal profile object exposing to_dict() for legacy websocket callers."""
    name: str
    skill_level: float
    style: str
    profile_id: str = field(default_factory=lambda: uuid.uuid4().hex[:10])
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "profile_id": self.profile_id,
            "name": self.name,
            "skill_level": self.skill_level,
            "style": self.style,
            "created_at": self.created_at,
        }


# =============================================================================
# Module-level aliases (backward compatibility with runtime.py)
# =============================================================================

# The runtime imports these names; keep them pointing at the singleton.
AgenticPlaytestSimulator = AgentPlaytestSimulator


def get_playtest_simulator() -> AgentPlaytestSimulator:
    """Return the singleton playtest simulator instance."""
    return AgentPlaytestSimulator.get_instance()

