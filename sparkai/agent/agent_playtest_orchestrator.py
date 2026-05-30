"""
SparkLabs Agent - Playtest Orchestrator

A singleton system for automated virtual playtesting at scale.
Simulates thousands of AI-driven player sessions to discover balance
issues, difficulty spikes, broken progression paths, and gameplay
friction points before human testing begins.

Architecture:
  PlaytestOrchestrator (singleton)
    |-- PlaytestSession (individual virtual player session state)
    |-- PlaytestArchetype (player behavior model template)
    |-- SessionReport (per-session findings and metrics)
"""

from __future__ import annotations

import math
import random
import threading
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


_time_module = time


class PlayerArchetype(Enum):
    EXPLORER = "explorer"
    ACHIEVER = "achiever"
    SOCIALIZER = "socializer"
    KILLER = "killer"
    SPEEDRUNNER = "speedrunner"
    COMPLETIONIST = "completionist"
    CASUAL = "casual"
    GRINDER = "grinder"


class SessionOutcome(Enum):
    COMPLETED = "completed"
    ABANDONED = "abandoned"
    BLOCKED = "blocked"
    REPEATED_DEATH = "repeated_death"
    SPEED_COMPLETE = "speed_complete"
    FULL_CLEAR = "full_clear"


class SeverityLevel(Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"
    BLOCKER = "blocker"


class IssueCategory(Enum):
    BALANCE = "balance"
    DIFFICULTY_SPIKE = "difficulty_spike"
    PROGRESSION_BLOCK = "progression_block"
    RESOURCE_SCARCITY = "resource_scarcity"
    PATHFINDING_FAILURE = "pathfinding_failure"
    SOFT_LOCK = "soft_lock"
    EXPLOITABLE = "exploitable"
    CONFUSION = "confusion"


# ------------------------------------------------------------------
# Dataclasses
# ------------------------------------------------------------------


@dataclass
class PlaytestArchetype:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    archetype: PlayerArchetype = PlayerArchetype.CASUAL
    exploration_weight: float = 0.5
    combat_aggressiveness: float = 0.5
    completion_thoroughness: float = 0.5
    skip_cutscenes: bool = False
    average_reaction_time: float = 0.3
    use_guides: bool = False
    quit_threshold: float = 0.1

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "archetype": self.archetype.value,
            "exploration_weight": self.exploration_weight,
            "combat_aggressiveness": self.combat_aggressiveness,
            "completion_thoroughness": self.completion_thoroughness,
            "skip_cutscenes": self.skip_cutscenes,
            "average_reaction_time": self.average_reaction_time,
            "use_guides": self.use_guides,
            "quit_threshold": self.quit_threshold,
        }


@dataclass
class PlaytestSession:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    batch_id: str = ""
    archetype: PlayerArchetype = PlayerArchetype.CASUAL
    total_time: float = 0.0
    deaths: int = 0
    damage_taken_points: List[float] = field(default_factory=list)
    levels_completed: int = 0
    items_collected: int = 0
    quests_attempted: int = 0
    quit_reason: str = ""
    outcome: SessionOutcome = SessionOutcome.COMPLETED
    critical_path_time: float = 0.0
    frustration_events: int = 0
    bottlenecks_hit: List[str] = field(default_factory=list)
    timestamp: float = field(default_factory=_time_module.time)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "batch_id": self.batch_id,
            "archetype": self.archetype.value,
            "total_time": self.total_time,
            "deaths": self.deaths,
            "damage_spikes": sum(self.damage_taken_points),
            "levels_completed": self.levels_completed,
            "items_collected": self.items_collected,
            "quests_attempted": self.quests_attempted,
            "quit_reason": self.quit_reason,
            "outcome": self.outcome.value,
            "critical_path_time": self.critical_path_time,
            "frustration_events": self.frustration_events,
            "bottlenecks_hit": list(self.bottlenecks_hit),
            "timestamp": self.timestamp,
            "metadata": dict(self.metadata),
        }


@dataclass
class SessionReport:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    batch_id: str = ""
    session_id: str = ""
    issues_found: int = 0
    difficulty_rating: float = 50.0
    balance_score: float = 50.0
    pacing_score: float = 50.0
    key_findings: List[Dict[str, Any]] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)
    timestamp: float = field(default_factory=_time_module.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "batch_id": self.batch_id,
            "session_id": self.session_id,
            "issues_found": self.issues_found,
            "difficulty_rating": self.difficulty_rating,
            "balance_score": self.balance_score,
            "pacing_score": self.pacing_score,
            "key_findings": list(self.key_findings),
            "recommendations": list(self.recommendations),
            "timestamp": self.timestamp,
        }


@dataclass
class PlaytestBatch:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = ""
    level_id: str = ""
    session_count: int = 0
    target_sessions: int = 100
    status: str = "pending"
    sessions: List[PlaytestSession] = field(default_factory=list)
    reports: List[SessionReport] = field(default_factory=list)
    aggregate_report: Optional[Dict[str, Any]] = None
    started_at: float = 0.0
    completed_at: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "level_id": self.level_id,
            "session_count": self.session_count,
            "target_sessions": self.target_sessions,
            "status": self.status,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
        }


# ------------------------------------------------------------------
# Singleton
# ------------------------------------------------------------------

ARCHETYPE_SESSION_MULTIPLIER: int = 8
BATCH_SIZE_DEFAULT: int = 1000
ISSUE_FREQ_THRESHOLD: float = 0.25


class PlaytestOrchestrator:
    """Automated virtual playtesting at production scale.

    Orchestrates thousands of simulated player sessions across diverse
    archetypes and difficulty profiles. Aggregates findings into
    actionable reports identifying balance issues, progression
    blockers, difficulty spikes, and friction points.
    """

    _instance: Optional[PlaytestOrchestrator] = None
    _lock: threading.RLock = threading.RLock()

    def __new__(cls) -> PlaytestOrchestrator:
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    instance = super().__new__(cls)
                    instance._initialized = False
                    cls._instance = instance
        return cls._instance

    @classmethod
    def get_instance(cls) -> PlaytestOrchestrator:
        if cls._instance is None:
            cls()
        return cls._instance

    def __init__(self) -> None:
        if self._initialized:
            return
        self._initialized = True
        self._archetypes: List[PlaytestArchetype] = []
        self._batches: List[PlaytestBatch] = []
        self._all_sessions: List[PlaytestSession] = []
        self._all_reports: List[SessionReport] = []
        self._initialize_default_archetypes()

    def _get_or_create_singleton(self) -> PlaytestOrchestrator:
        return self.get_instance()

    def get_stats(self) -> Dict[str, Any]:
        return {
            "archetypes": len(self._archetypes),
            "batches": len(self._batches),
            "total_sessions": len(self._all_sessions),
            "total_reports": len(self._all_reports),
            "active_batches": sum(
                1 for b in self._batches if b.status == "running"
            ),
        }

    # --- Batch Operations ---

    def create_batch(
        self,
        name: str,
        level_id: str = "",
        target_sessions: int = BATCH_SIZE_DEFAULT,
    ) -> PlaytestBatch:
        batch = PlaytestBatch(
            name=name,
            level_id=level_id,
            target_sessions=target_sessions,
            status="created",
        )
        self._batches.append(batch)
        return batch

    def run_batch(self, batch_id: str) -> PlaytestBatch:
        batch = self._find_batch(batch_id)
        if not batch:
            raise ValueError(f"Batch {batch_id} not found")

        batch.status = "running"
        batch.started_at = _time_module.time()

        sessions_per_archetype = max(
            1, batch.target_sessions // max(1, len(self._archetypes))
        )

        for archetype_obj in self._archetypes:
            for _ in range(sessions_per_archetype):
                session = PlaytestSession(
                    batch_id=batch_id,
                    archetype=archetype_obj.archetype,
                )
                session.bottlenecks_hit = self._simulate_bottlenecks(archetype_obj)
                session.frustration_events = self._simulate_frustration(archetype_obj)
                session.deaths = self._simulate_deaths(archetype_obj)
                session.outcome = self._simulate_outcome(archetype_obj)
                session.total_time = self._simulate_playtime(archetype_obj)
                session.levels_completed = self._simulate_progress(archetype_obj)
                session.items_collected = self._simulate_collection(archetype_obj)
                session.quests_attempted = self._simulate_quests(archetype_obj)

                batch.sessions.append(session)
                self._all_sessions.append(session)

        batch.session_count = len(batch.sessions)
        batch.status = "completed"
        batch.completed_at = _time_module.time()
        return batch

    def generate_batch_report(self, batch_id: str) -> Dict[str, Any]:
        batch = self._find_batch(batch_id)
        if not batch or not batch.sessions:
            return {"error": "No sessions to analyze"}

        outcomes: Dict[str, int] = {}
        total_deaths = 0
        total_frustration = 0
        total_time = 0.0
        all_bottlenecks: Dict[str, int] = {}

        for session in batch.sessions:
            outcomes[session.outcome.value] = outcomes.get(session.outcome.value, 0) + 1
            total_deaths += session.deaths
            total_frustration += session.frustration_events
            total_time += session.total_time

            for bn in session.bottlenecks_hit:
                all_bottlenecks[bn] = all_bottlenecks.get(bn, 0) + 1

        session_count = len(batch.sessions)
        avg_deaths = total_deaths / max(1, session_count)
        avg_time = total_time / max(1, session_count)
        avg_frustration = total_frustration / max(1, session_count)

        completion_rate = (
            outcomes.get("completed", 0) + outcomes.get("speed_complete", 0) + outcomes.get("full_clear", 0)
        ) / max(1, session_count)

        blocked_rate = (
            outcomes.get("blocked", 0) + outcomes.get("soft_lock", 0)
        ) / max(1, session_count)

        critical_bottlenecks = [
            {"bottleneck": k, "frequency": v, "rate": v / max(1, session_count)}
            for k, v in all_bottlenecks.items()
            if v / max(1, session_count) >= ISSUE_FREQ_THRESHOLD
        ]
        critical_bottlenecks.sort(key=lambda x: x["rate"], reverse=True)

        findings: List[Dict[str, Any]] = []
        if avg_deaths > 10:
            findings.append({"category": "difficulty_spike", "severity": "critical", "detail": f"Average {avg_deaths:.1f} deaths per session"})
        if completion_rate < 0.5:
            findings.append({"category": "balance", "severity": "warning", "detail": f"Completion rate: {completion_rate:.1%}"})
        if blocked_rate > 0.1:
            findings.append({"category": "progression_block", "severity": "critical", "detail": f"Blocked rate: {blocked_rate:.1%}"})
        if avg_frustration > 5:
            findings.append({"category": "balance", "severity": "warning", "detail": f"Frustration events avg: {avg_frustration:.1f}"})

        score = max(0, min(100, 100 - (1 - completion_rate) * 50 - blocked_rate * 200 - (avg_deaths / 10) * 10))

        report = SessionReport(
            batch_id=batch_id,
            issues_found=len(findings),
            difficulty_rating=score,
            balance_score=score,
            pacing_score=max(0, min(100, 100 - (len(critical_bottlenecks) * 10))),
            key_findings=findings,
            recommendations=[
                f"Investigate {bn['bottleneck']} (affects {bn['rate']:.0%} of players)"
                for bn in critical_bottlenecks[:5]
            ],
        )
        self._all_reports.append(report)
        batch.reports.append(report)

        return {
            "batch_id": batch_id,
            "name": batch.name,
            "sessions": session_count,
            "outcomes": outcomes,
            "completion_rate": completion_rate,
            "blocked_rate": blocked_rate,
            "avg_deaths": avg_deaths,
            "avg_time_minutes": avg_time / 60,
            "avg_frustration": avg_frustration,
            "score": score,
            "critical_bottlenecks": critical_bottlenecks[:10],
            "findings": findings,
            "report_id": report.id,
        }

    def get_batch(self, batch_id: str) -> Optional[PlaytestBatch]:
        return self._find_batch(batch_id)

    def list_batches(self) -> List[PlaytestBatch]:
        return list(self._batches)

    def create_archetype_profile(
        self,
        archetype: str,
        exploration: float = 0.5,
        aggressiveness: float = 0.5,
        thoroughness: float = 0.5,
    ) -> PlaytestArchetype:
        profile = PlaytestArchetype(
            archetype=PlayerArchetype(archetype),
            exploration_weight=exploration,
            combat_aggressiveness=aggressiveness,
            completion_thoroughness=thoroughness,
        )
        self._archetypes.append(profile)
        return profile

    def list_archetypes(self) -> List[PlaytestArchetype]:
        return list(self._archetypes)

    # --- Internal ---

    def _find_batch(self, batch_id: str) -> Optional[PlaytestBatch]:
        for b in self._batches:
            if b.id == batch_id:
                return b
        return None

    def _initialize_default_archetypes(self) -> None:
        configs: List[Tuple[str, float, float, float]] = [
            ("explorer", 1.0, 0.3, 0.8),
            ("achiever", 0.5, 0.7, 0.9),
            ("socializer", 0.3, 0.2, 0.3),
            ("killer", 0.4, 1.0, 0.2),
            ("speedrunner", 0.1, 0.5, 0.1),
            ("completionist", 0.9, 0.5, 1.0),
            ("casual", 0.4, 0.3, 0.3),
            ("grinder", 0.7, 0.8, 0.9),
        ]
        for archetype, exp, agg, thorough in configs:
            profile = PlaytestArchetype(
                archetype=PlayerArchetype(archetype),
                exploration_weight=exp,
                combat_aggressiveness=agg,
                completion_thoroughness=thorough,
            )
            if archetype == "speedrunner":
                profile.skip_cutscenes = True
            self._archetypes.append(profile)

    def _simulate_bottlenecks(self, arch: PlaytestArchetype) -> List[str]:
        possible = ["boss_room_3", "lava_corridor", "puzzle_gate", "elite_patrol", "minefield_passage"]
        count = max(0, int(random.gauss(1.5, 1.0)))
        if arch.combat_aggressiveness > 0.7:
            count += random.randint(1, 3)
        return random.sample(possible, min(count, len(possible)))

    def _simulate_frustration(self, arch: PlaytestArchetype) -> int:
        base = random.randint(0, 3)
        if arch.quit_threshold < 0.05:
            base += random.randint(5, 15)
        if arch.combat_aggressiveness > 0.8:
            base += random.randint(1, 5)
        return base

    def _simulate_deaths(self, arch: PlaytestArchetype) -> int:
        deaths = random.randint(0, 5)
        if arch.combat_aggressiveness > 0.8:
            deaths *= 2
        if arch.average_reaction_time > 0.5:
            deaths = deaths * 3 // 2
        return deaths

    def _simulate_outcome(self, arch: PlaytestArchetype) -> SessionOutcome:
        roll = random.random()
        if arch.quit_threshold > 0.8:
            return SessionOutcome.ABANDONED
        if roll < 0.15 and arch.combat_aggressiveness > 0.8:
            return SessionOutcome.REPEATED_DEATH
        if roll < 0.05:
            return SessionOutcome.BLOCKED
        if roll < 0.08:
            return SessionOutcome.ABANDONED
        if roll > 0.95 and arch.completion_thoroughness > 0.8:
            return SessionOutcome.FULL_CLEAR
        if arch.archetype == PlayerArchetype.SPEEDRUNNER:
            return SessionOutcome.SPEED_COMPLETE
        return SessionOutcome.COMPLETED

    def _simulate_playtime(self, arch: PlaytestArchetype) -> float:
        base = 3600.0
        variation = random.gauss(0, 600)
        if arch.exploration_weight > 0.8:
            variation += random.uniform(600, 1800)
        if arch.archetype == PlayerArchetype.SPEEDRUNNER:
            return max(300.0, base * 0.3)
        return max(600.0, base + variation)

    def _simulate_progress(self, arch: PlaytestArchetype) -> int:
        total = 10
        return min(total, random.randint(total // 2, total))

    def _simulate_collection(self, arch: PlaytestArchetype) -> int:
        items = random.randint(10, 100)
        if arch.completion_thoroughness > 0.8:
            items = items * 2
        return items

    def _simulate_quests(self, arch: PlaytestArchetype) -> int:
        total = 20
        return random.randint(total // 4, total)


def get_playtest_orchestrator() -> PlaytestOrchestrator:
    return PlaytestOrchestrator.get_instance()