"""
SparkLabs Agent - Playtest Simulator

Automated game testing system that simulates AI-driven player agents
traversing game levels, collecting metrics on difficulty, fun factor,
progression flow, and potential soft-locks.

Architecture:
  PlaytestSimulator
    |-- PlayerProfileGenerator (diverse player personas)
    |-- SessionRunner (executes playthrough simulations)
    |-- MetricsCollector (gathers gameplay telemetry)
    |-- IssueDetector (identifies blockers and anomalies)
    |-- ReportGenerator (summarizes findings)

Simulation Aspects:
  - PATH_FINDING: navigation capability assessment
  - DIFFICULTY: challenge level measurement
  - PROGRESSION: level completion flow analysis
  - INTERACTION: object and npc engagement tracking
  - PERFORMANCE: frame rate and resource monitoring during play
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


class PlayerStyle(Enum):
    COMPLETIONIST = "completionist"
    SPEEDRUNNER = "speedrunner"
    CASUAL = "casual"
    EXPLORER = "explorer"
    AGGRESSIVE = "aggressive"
    PACIFIST = "pacifist"


class CompletionStatus(Enum):
    COMPLETED = "completed"
    ABANDONED = "abandoned"
    STUCK = "stuck"
    INCOMPLETE = "incomplete"


class IssueType(Enum):
    SOFT_LOCK = "soft_lock"
    BALANCE_SPIKE = "balance_spike"
    NAVIGATION_BLOCK = "navigation_block"
    PERFORMANCE_DROP = "performance_drop"
    MISSING_ASSET = "missing_asset"
    PROGRESSION_BLOCK = "progression_block"
    COLLISION_ERROR = "collision_error"


@dataclass
class PlayerProfile:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = "Unnamed Player"
    skill_level: float = 0.5
    patience: float = 0.5
    exploration_style: PlayerStyle = PlayerStyle.CASUAL
    preferred_strategies: List[str] = field(default_factory=list)
    input_latency_tolerance: float = 0.1
    attention_span_seconds: float = 600.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "skill_level": round(self.skill_level, 2),
            "patience": round(self.patience, 2),
            "exploration_style": self.exploration_style.value,
            "preferred_strategies": self.preferred_strategies,
            "input_latency_tolerance": self.input_latency_tolerance,
            "attention_span_seconds": self.attention_span_seconds,
        }


@dataclass
class PlaySession:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    profile_id: str = ""
    level_id: str = ""
    start_time: float = field(default_factory=time.time)
    end_time: Optional[float] = None
    completion_status: CompletionStatus = CompletionStatus.INCOMPLETE
    path_taken: List[Tuple[float, float, float]] = field(default_factory=list)
    interactions: List[Dict[str, Any]] = field(default_factory=list)
    deaths: int = 0
    time_spent: float = 0.0
    collected_items: int = 0
    enemies_defeated: int = 0
    current_position: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    current_health: float = 100.0
    frame_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "profile_id": self.profile_id,
            "level_id": self.level_id,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "completion_status": self.completion_status.value,
            "path_length": len(self.path_taken),
            "interactions": len(self.interactions),
            "deaths": self.deaths,
            "time_spent": round(self.time_spent, 2),
            "collected_items": self.collected_items,
            "enemies_defeated": self.enemies_defeated,
        }


@dataclass
class GameplayMetric:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    session_id: str = ""
    metric_name: str = ""
    value: float = 0.0
    timestamp: float = field(default_factory=time.time)
    location: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    category: str = "engagement"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "session_id": self.session_id,
            "metric_name": self.metric_name,
            "value": round(self.value, 4),
            "timestamp": self.timestamp,
            "location": self.location,
            "category": self.category,
        }


@dataclass
class PlaytestIssue:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    session_id: str = ""
    issue_type: IssueType = IssueType.SOFT_LOCK
    severity: float = 0.5
    location: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    description: str = ""
    reproduction_steps: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "session_id": self.session_id,
            "issue_type": self.issue_type.value,
            "severity": round(self.severity, 2),
            "location": self.location,
            "description": self.description,
            "reproduction_steps": self.reproduction_steps,
        }


@dataclass
class PlaytestReport:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    level_id: str = ""
    sessions_run: int = 0
    avg_completion_time: float = 0.0
    completion_rate: float = 0.0
    difficulty_rating: float = 0.0
    fun_score: float = 0.0
    issues_found: int = 0
    top_issues: List[PlaytestIssue] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "level_id": self.level_id,
            "sessions_run": self.sessions_run,
            "avg_completion_time": round(self.avg_completion_time, 2),
            "completion_rate": round(self.completion_rate, 2),
            "difficulty_rating": round(self.difficulty_rating, 2),
            "fun_score": round(self.fun_score, 2),
            "issues_found": self.issues_found,
            "top_issues": [i.to_dict() for i in self.top_issues],
            "recommendations": self.recommendations,
        }


_SEED_PLAYER_PROFILES: List[Dict[str, Any]] = [
    {
        "name": "Casual Gamer",
        "skill_level": 0.35,
        "patience": 0.80,
        "exploration_style": "casual",
        "preferred_strategies": ["safe_routes", "avoid_conflict"],
        "input_latency_tolerance": 0.15,
        "attention_span_seconds": 900.0,
    },
    {
        "name": "Speed Runner",
        "skill_level": 0.85,
        "patience": 0.15,
        "exploration_style": "speedrunner",
        "preferred_strategies": ["optimal_path", "skip_cutscenes", "glitch_abuse"],
        "input_latency_tolerance": 0.02,
        "attention_span_seconds": 1800.0,
    },
    {
        "name": "Completionist",
        "skill_level": 0.70,
        "patience": 0.90,
        "exploration_style": "completionist",
        "preferred_strategies": ["full_clear", "collect_all", "secret_hunt"],
        "input_latency_tolerance": 0.08,
        "attention_span_seconds": 3600.0,
    },
    {
        "name": "Explorer",
        "skill_level": 0.50,
        "patience": 0.85,
        "exploration_style": "explorer",
        "preferred_strategies": ["off_path", "environment_interaction", "lore_discovery"],
        "input_latency_tolerance": 0.10,
        "attention_span_seconds": 2700.0,
    },
    {
        "name": "Aggressive Player",
        "skill_level": 0.75,
        "patience": 0.25,
        "exploration_style": "aggressive",
        "preferred_strategies": ["direct_combat", "rush_enemies", "high_risk"],
        "input_latency_tolerance": 0.05,
        "attention_span_seconds": 1200.0,
    },
    {
        "name": "Pacifist",
        "skill_level": 0.55,
        "patience": 0.95,
        "exploration_style": "pacifist",
        "preferred_strategies": ["stealth", "bypass_enemies", "dialog_resolution"],
        "input_latency_tolerance": 0.12,
        "attention_span_seconds": 2400.0,
    },
]


class PlaytestSimulator:
    """
    Automated playtest simulator that runs AI-driven player agents through
    game levels, collecting metrics on gameplay quality and detecting issues.
    """

    _instance: Optional["PlaytestSimulator"] = None
    _lock: threading.RLock = threading.RLock()

    LEVEL_DURATION_BASELINE = 300.0
    AVG_FRAME_TIME = 0.016
    DIFFICULTY_CURVE_POINTS = 20

    @classmethod
    def get_instance(cls) -> "PlaytestSimulator":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def __init__(self):
        self._profiles: Dict[str, PlayerProfile] = {}
        self._sessions: Dict[str, PlaySession] = {}
        self._reports: Dict[str, PlaytestReport] = {}
        self._metrics: List[GameplayMetric] = []
        self._issues: List[PlaytestIssue] = []
        self._session_state: Dict[str, Dict[str, Any]] = {}
        self._seed_profiles()

    def _seed_profiles(self) -> None:
        for seed in _SEED_PLAYER_PROFILES:
            self.create_profile(
                name=seed["name"],
                skill_level=seed["skill_level"],
                style=PlayerStyle(seed["exploration_style"]),
            )
            profile = self._profiles[
                next(reversed(self._profiles))
            ]
            profile.patience = seed["patience"]
            profile.preferred_strategies = seed["preferred_strategies"]
            profile.input_latency_tolerance = seed["input_latency_tolerance"]
            profile.attention_span_seconds = seed["attention_span_seconds"]

    def create_profile(
        self,
        name: str,
        skill_level: float = 0.5,
        style: PlayerStyle = PlayerStyle.CASUAL,
    ) -> PlayerProfile:
        profile = PlayerProfile(
            name=name,
            skill_level=max(0.0, min(1.0, skill_level)),
            exploration_style=style,
        )
        self._profiles[profile.id] = profile
        return profile

    def start_session(self, profile_id: str, level_id: str) -> Optional[PlaySession]:
        profile = self._profiles.get(profile_id)
        if profile is None:
            return None

        session = PlaySession(
            profile_id=profile_id,
            level_id=level_id,
        )
        self._sessions[session.id] = session
        self._session_state[session.id] = {
            "position": [0.0, 0.0, 0.0],
            "velocity": [0.0, 0.0, 0.0],
            "progress": 0.0,
            "health": 100.0,
            "stamina": 100.0,
            "current_action": "idle",
            "enemies_nearby": 0,
            "items_nearby": 0,
            "obstacles_nearby": 0,
            "target_position": [10.0, 0.0, 10.0],
            "stuck_timer": 0.0,
            "frustration_level": 0.0,
            "total_distance": 0.0,
        }
        return session

    def simulate_frame(
        self, session_id: str, delta_time: float = 0.016
    ) -> Dict[str, Any]:
        session = self._sessions.get(session_id)
        if session is None:
            return {"error": "Session not found"}

        profile = self._profiles.get(session.profile_id)
        if profile is None:
            return {"error": "Profile not found"}

        state = self._session_state.get(session_id)
        if state is None:
            return {"error": "Session state not found"}

        dt = delta_time
        skill = profile.skill_level
        patience = profile.patience
        style = profile.exploration_style

        speed_base = 4.0 + skill * 8.0
        if style == PlayerStyle.SPEEDRUNNER:
            speed_base *= 1.6
        elif style == PlayerStyle.CASUAL:
            speed_base *= 0.7

        speed = speed_base + random.uniform(-0.5, 0.5)

        tx, ty, tz = state["target_position"]
        px, py, pz = state["position"]
        dx = tx - px
        dy = ty - py
        dz = tz - pz
        distance_to_target = math.sqrt(dx * dx + dy * dy + dz * dz)

        if distance_to_target < 0.5:
            state["target_position"] = [
                tx + random.uniform(5.0, 20.0),
                ty + random.uniform(-1.0, 1.0),
                tz + random.uniform(5.0, 20.0),
            ]
            state["progress"] += random.uniform(2.0, 8.0)
            dx = state["target_position"][0] - px
            dy = state["target_position"][1] - py
            dz = state["target_position"][2] - pz
            distance_to_target = math.sqrt(dx * dx + dy * dy + dz * dz)

        move_fraction = min(1.0, (speed * dt) / max(0.01, distance_to_target))
        nx = px + dx * move_fraction + random.uniform(-0.05, 0.05)
        ny = py + dy * move_fraction + random.uniform(-0.02, 0.02)
        nz = pz + dz * move_fraction + random.uniform(-0.05, 0.05)

        step_distance = math.sqrt(
            (nx - px) ** 2 + (ny - py) ** 2 + (nz - pz) ** 2
        )
        state["total_distance"] += step_distance

        state["position"] = [nx, ny, nz]
        state["velocity"] = [
            (nx - px) / max(dt, 0.001),
            (ny - py) / max(dt, 0.001),
            (nz - pz) / max(dt, 0.001),
        ]

        if step_distance < 0.01:
            state["stuck_timer"] += dt
        else:
            state["stuck_timer"] = max(0.0, state["stuck_timer"] - dt * 3.0)

        state["enemies_nearby"] = random.randint(0, 5)
        state["items_nearby"] = random.randint(0, 3)
        state["obstacles_nearby"] = random.randint(0, 2)

        if state["enemies_nearby"] > 0:
            if style == PlayerStyle.AGGRESSIVE:
                state["current_action"] = "attacking"
                if random.random() < skill * 0.3:
                    session.enemies_defeated += 1
                    state["enemies_nearby"] = max(0, state["enemies_nearby"] - 1)
            elif style == PlayerStyle.PACIFIST:
                state["current_action"] = "evading"
            else:
                if random.random() < 0.6:
                    state["current_action"] = "attacking"
                    if random.random() < skill * 0.25:
                        session.enemies_defeated += 1
                        state["enemies_nearby"] = max(0, state["enemies_nearby"] - 1)
                else:
                    state["current_action"] = "evading"

            damage_chance = (1.0 - skill) * 0.3
            if random.random() < damage_chance:
                state["health"] = max(0.0, state["health"] - random.uniform(5.0, 20.0))
        else:
            action_roll = random.random()
            if action_roll < 0.7:
                state["current_action"] = "moving"
            elif action_roll < 0.85:
                state["current_action"] = "interacting"
                if random.random() < 0.3:
                    session.collected_items += 1
                    interaction = {
                        "type": "pickup",
                        "item": f"item_{random.randint(1, 100)}",
                        "position": tuple(state["position"]),
                        "timestamp": time.time(),
                    }
                    session.interactions.append(interaction)
            else:
                state["current_action"] = "idle"

        if state["health"] <= 0:
            state["health"] = 100.0
            state["position"] = [0.0, 0.0, 0.0]
            state["target_position"] = [10.0, 0.0, 10.0]
            session.deaths += 1

        frame_time_ms = (dt * 1000.0) + random.uniform(-1.0, 3.0)
        fps = 1000.0 / max(frame_time_ms, 0.001)

        input_latency = random.uniform(0.005, 0.025)
        if profile.input_latency_tolerance < input_latency:
            state["frustration_level"] = min(
                1.0, state["frustration_level"] + 0.01
            )

        session.frame_count += 1
        session.time_spent += dt
        session.current_position = (nx, ny, nz)
        session.current_health = state["health"]
        session.path_taken.append((nx, ny, nz))

        if state["stuck_timer"] > 3.0:
            stuck_pos = tuple(state["position"])
            self.detect_issue(
                session_id=session_id,
                issue_type=IssueType.NAVIGATION_BLOCK,
                severity=min(0.9, state["stuck_timer"] / 10.0),
                location=stuck_pos,
                description=f"Agent stuck for {state['stuck_timer']:.1f}s at {stuck_pos}",
            )
            state["stuck_timer"] = 0.0

        if session.time_spent > profile.attention_span_seconds and patience < 0.3:
            if random.random() < 0.1:
                self.complete_session(session_id, status=CompletionStatus.ABANDONED)

        if state["progress"] >= 100.0:
            self.complete_session(session_id, status=CompletionStatus.COMPLETED)

        if frame_time_ms > 33.0:
            self.record_metric(
                session_id=session_id,
                name="frame_time_spike",
                value=frame_time_ms,
                location=session.current_position,
                category="performance",
            )

        if state["frustration_level"] > 0.7:
            self.record_metric(
                session_id=session_id,
                name="frustration_event",
                value=state["frustration_level"],
                location=session.current_position,
                category="difficulty",
            )

        telemetry = {
            "session_id": session_id,
            "frame": session.frame_count,
            "delta_time": round(dt, 4),
            "position": (round(nx, 2), round(ny, 2), round(nz, 2)),
            "velocity": (
                round(state["velocity"][0], 2),
                round(state["velocity"][1], 2),
                round(state["velocity"][2], 2),
            ),
            "action": state["current_action"],
            "health": round(state["health"], 1),
            "enemies_nearby": state["enemies_nearby"],
            "items_nearby": state["items_nearby"],
            "frustration": round(state["frustration_level"], 2),
            "progress": round(state["progress"], 1),
            "frame_time_ms": round(frame_time_ms, 2),
            "fps": round(fps, 0),
            "input_latency_ms": round(input_latency * 1000.0, 2),
            "deaths": session.deaths,
            "time_spent": round(session.time_spent, 2),
        }

        return telemetry

    def record_metric(
        self,
        session_id: str,
        name: str,
        value: float,
        location: Tuple[float, float, float],
        category: str = "engagement",
    ) -> Optional[GameplayMetric]:
        session = self._sessions.get(session_id)
        if session is None:
            return None
        metric = GameplayMetric(
            session_id=session_id,
            metric_name=name,
            value=value,
            location=location,
            category=category,
        )
        self._metrics.append(metric)
        return metric

    def detect_issue(
        self,
        session_id: str,
        issue_type: IssueType,
        severity: float,
        location: Tuple[float, float, float],
        description: str,
    ) -> Optional[PlaytestIssue]:
        session = self._sessions.get(session_id)
        if session is None:
            return None
        issue = PlaytestIssue(
            session_id=session_id,
            issue_type=issue_type,
            severity=min(1.0, max(0.0, severity)),
            location=location,
            description=description,
            reproduction_steps=[
                f"Start session for player profile {session.profile_id}",
                f"Play level {session.level_id} until reaching position {location}",
                description,
            ],
        )
        self._issues.append(issue)
        return issue

    def complete_session(
        self,
        session_id: str,
        status: CompletionStatus = CompletionStatus.COMPLETED,
    ) -> None:
        session = self._sessions.get(session_id)
        if session is None:
            return
        session.end_time = time.time()
        session.completion_status = status

    def generate_report(self, level_id: str) -> PlaytestReport:
        level_sessions = [
            s for s in self._sessions.values() if s.level_id == level_id
        ]
        level_issues = [
            i for i in self._issues
            if i.session_id in {s.id for s in level_sessions}
        ]

        completed = [
            s for s in level_sessions
            if s.completion_status == CompletionStatus.COMPLETED
        ]
        completion_rate = len(completed) / max(1, len(level_sessions))

        completion_times = [
            (s.end_time - s.start_time)
            for s in completed
            if s.end_time is not None
        ]
        avg_completion_time = (
            sum(completion_times) / max(1, len(completion_times))
        )

        total_deaths = sum(s.deaths for s in level_sessions)
        total_time = sum(s.time_spent for s in level_sessions)
        death_rate = total_deaths / max(1.0, total_time / 60.0)

        difficulty_rating = 0.0
        if death_rate > 3.0:
            difficulty_rating = 0.9
        elif death_rate > 1.5:
            difficulty_rating = 0.7
        elif death_rate > 0.5:
            difficulty_rating = 0.45
        elif death_rate > 0.1:
            difficulty_rating = 0.25
        else:
            difficulty_rating = 0.1

        difficulty_rating += (1.0 - completion_rate) * 0.2
        difficulty_rating = min(1.0, difficulty_rating)

        fun_score = 0.5
        if completion_rate > 0.7:
            fun_score += 0.2
        if 0.3 < difficulty_rating < 0.8:
            fun_score += 0.15
        if len(level_issues) < 3:
            fun_score += 0.1
        if death_rate > 0.2 and death_rate < 2.0:
            fun_score += 0.05

        fun_score = min(1.0, fun_score)

        sorted_issues = sorted(level_issues, key=lambda i: i.severity, reverse=True)
        top_issues = sorted_issues[:5]

        recommendations: List[str] = []
        if difficulty_rating > 0.75:
            recommendations.append(
                "Reduce enemy density or damage scaling to lower difficulty rating."
            )
        if completion_rate < 0.5:
            recommendations.append(
                "Investigate progression blockers preventing session completion."
            )
        if any(i.issue_type == IssueType.NAVIGATION_BLOCK for i in level_issues):
            recommendations.append(
                "Review navmesh coverage and obstacle placement at reported block locations."
            )
        if any(i.issue_type == IssueType.PERFORMANCE_DROP for i in level_issues):
            recommendations.append(
                "Profile frame-time spikes and optimize heavy rendering or script paths."
            )
        if not recommendations:
            recommendations.append(
                "Level design is well-tuned. Consider adding optional secrets for replay value."
            )

        report = PlaytestReport(
            level_id=level_id,
            sessions_run=len(level_sessions),
            avg_completion_time=avg_completion_time,
            completion_rate=round(completion_rate, 3),
            difficulty_rating=round(difficulty_rating, 3),
            fun_score=round(fun_score, 3),
            issues_found=len(level_issues),
            top_issues=top_issues,
            recommendations=recommendations,
        )
        self._reports[level_id] = report
        return report

    def get_difficulty_curve(
        self, level_id: str
    ) -> List[Tuple[float, float]]:
        level_sessions = [
            s for s in self._sessions.values() if s.level_id == level_id
        ]
        if not level_sessions:
            return []

        points = self.DIFFICULTY_CURVE_POINTS
        curve: List[Tuple[float, float]] = []

        for i in range(points):
            progress = (i / (points - 1)) * 100.0

            deaths_at_progress = 0
            total_sessions_at_progress = 0

            for session in level_sessions:
                session_progress_estimate = (
                    min(100.0, (session.time_spent / self.LEVEL_DURATION_BASELINE) * 100.0)
                )
                if session_progress_estimate >= progress:
                    total_sessions_at_progress += 1

            if total_sessions_at_progress > 0:
                difficulty = (
                    sum(
                        1
                        for s in level_sessions
                        if s.deaths > 0
                    )
                    / max(1, total_sessions_at_progress)
                )
                difficulty = min(1.0, difficulty + random.uniform(-0.05, 0.05))
            else:
                difficulty = 0.0

            curve.append((round(progress, 1), round(difficulty, 3)))

        return curve

    def get_heat_map(self, level_id: str) -> Dict[str, Any]:
        level_sessions = [
            s for s in self._sessions.values() if s.level_id == level_id
        ]
        if not level_sessions:
            return {"level_id": level_id, "zones": []}

        zone_size = 10.0
        zones: Dict[Tuple[int, int, int], Dict[str, Any]] = {}

        for session in level_sessions:
            for pos in session.path_taken:
                zx = int(pos[0] / zone_size)
                zy = int(pos[1] / zone_size)
                zz = int(pos[2] / zone_size)
                key = (zx, zy, zz)
                if key not in zones:
                    zones[key] = {
                        "center": (
                            zx * zone_size + zone_size / 2,
                            zy * zone_size + zone_size / 2,
                            zz * zone_size + zone_size / 2,
                        ),
                        "visit_count": 0,
                        "death_count": 0,
                    }
                zones[key]["visit_count"] += 1

        for session in level_sessions:
            for pos in session.path_taken:
                zx = int(pos[0] / zone_size)
                zy = int(pos[1] / zone_size)
                zz = int(pos[2] / zone_size)
                key = (zx, zy, zz)
                if key in zones:
                    zones[key]["death_count"] = max(
                        zones[key]["death_count"],
                        session.deaths,
                    )

        zone_list = sorted(
            [
                {
                    "center": v["center"],
                    "visit_count": v["visit_count"],
                    "death_count": v["death_count"],
                    "heat_level": round(
                        min(1.0, v["visit_count"] / max(1, max(z["visit_count"] for z in zones.values()))),
                        2,
                    ),
                }
                for v in zones.values()
            ],
            key=lambda z: z["heat_level"],
            reverse=True,
        )

        return {
            "level_id": level_id,
            "zone_size": zone_size,
            "total_zones": len(zones),
            "max_visits": max((z["visit_count"] for z in zones.values()), default=0),
            "zones": zone_list[:20],
        }

    def get_stats(self) -> Dict[str, Any]:
        total_sessions = len(self._sessions)
        completed = sum(
            1 for s in self._sessions.values()
            if s.completion_status == CompletionStatus.COMPLETED
        )
        abandoned = sum(
            1 for s in self._sessions.values()
            if s.completion_status == CompletionStatus.ABANDONED
        )
        stuck = sum(
            1 for s in self._sessions.values()
            if s.completion_status == CompletionStatus.STUCK
        )

        return {
            "profiles": len(self._profiles),
            "sessions": total_sessions,
            "completed": completed,
            "abandoned": abandoned,
            "stuck": stuck,
            "total_metrics": len(self._metrics),
            "total_issues": len(self._issues),
            "reports_generated": len(self._reports),
            "profile_names": [p.name for p in self._profiles.values()],
            "issue_breakdown": self._get_issue_breakdown(),
            "avg_session_time": round(
                sum(s.time_spent for s in self._sessions.values())
                / max(1, total_sessions),
                2,
            ),
        }

    def _get_issue_breakdown(self) -> Dict[str, int]:
        breakdown: Dict[str, int] = {}
        for issue in self._issues:
            key = issue.issue_type.value
            breakdown[key] = breakdown.get(key, 0) + 1
        return breakdown

    def get_session(self, session_id: str) -> Optional[PlaySession]:
        return self._sessions.get(session_id)

    def get_profile(self, profile_id: str) -> Optional[PlayerProfile]:
        return self._profiles.get(profile_id)

    def get_all_profiles(self) -> List[PlayerProfile]:
        return list(self._profiles.values())

    def get_all_sessions(self) -> List[PlaySession]:
        return list(self._sessions.values())

    def get_sessions_for_level(self, level_id: str) -> List[PlaySession]:
        return [s for s in self._sessions.values() if s.level_id == level_id]

    def get_issues_for_session(self, session_id: str) -> List[PlaytestIssue]:
        return [i for i in self._issues if i.session_id == session_id]

    def run_full_simulation(
        self,
        level_id: str,
        duration_seconds: float = 60.0,
        frame_delta: float = 0.016,
    ) -> Dict[str, Any]:
        results: Dict[str, Dict[str, Any]] = {}

        for profile in list(self._profiles.values()):
            session = self.start_session(profile.id, level_id)
            if session is None:
                continue

            simulated_time = 0.0
            while simulated_time < duration_seconds:
                telemetry = self.simulate_frame(session.id, frame_delta)
                simulated_time += frame_delta

                session_obj = self._sessions.get(session.id)
                if session_obj and session_obj.completion_status in (
                    CompletionStatus.COMPLETED,
                    CompletionStatus.ABANDONED,
                ):
                    break

            results[profile.name] = {
                "session_id": session.id,
                "status": session.completion_status.value,
                "time_spent": round(session.time_spent, 2),
                "deaths": session.deaths,
                "items_collected": session.collected_items,
                "enemies_defeated": session.enemies_defeated,
                "path_length": len(session.path_taken),
            }

        report = self.generate_report(level_id)

        return {
            "level_id": level_id,
            "simulation_duration": duration_seconds,
            "profiles_simulated": len(results),
            "profile_results": results,
            "report_summary": {
                "completion_rate": report.completion_rate,
                "difficulty_rating": report.difficulty_rating,
                "fun_score": report.fun_score,
                "issues_found": report.issues_found,
                "recommendations": report.recommendations[:3],
            },
        }


def get_playtest_simulator() -> PlaytestSimulator:
    return PlaytestSimulator.get_instance()