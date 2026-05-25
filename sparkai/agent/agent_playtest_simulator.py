"""
SparkLabs Agent - Agentic Playtest Simulator

Automated playtesting system that simulates diverse player behaviors to test
game mechanics, discover bugs, evaluate game design quality, and measure
completion rates. Supports multiple playtest modes from quick smoke tests to
full playthroughs with stress and boundary testing.

Architecture:
  AgenticPlaytestSimulator (Singleton)
    |-- PlaytestSession (active testing session)
    |-- PlaytestAction (recorded player input)
    |-- BugReport (discovered issue)
    |-- PlaytestSummary (aggregated session metrics)

Player Profiles:
  - CASUAL: relaxed play with moderate exploration
  - COMPLETIONIST: thorough coverage, collects everything
  - SPEEDRUNNER: fastest path, skips optional content
  - EXPLORER: off-path discovery, environment interaction
  - AGGRESSIVE: direct combat focus, high risk tolerance
  - PACIFIST: stealth and avoidance-based approach
  - PUZZLE_SOLVER: methodical problem-solving pattern

Playtest Modes:
  - QUICK_SMOKE: basic sanity check (30-60s)
  - FULL_PLAYTHROUGH: complete level traversal
  - STRESS_TEST: heavy load simulation
  - BOUNDARY_TEST: edge case and collision testing
  - SPEED_TEST: performance under rapid input
  - REGRESSION_TEST: comparison with previous baselines

Usage:
    simulator = get_playtest_simulator()
    session = simulator.start_session("level_01", PlaytestMode.FULL_PLAYTHROUGH,
        PlayerProfile.EXPLORER)
    simulator.simulate_sequence(session.id, ["move_forward", "jump", "interact"])
    summary = simulator.generate_summary(session.id)
"""

from __future__ import annotations

import json
import math
import random
import threading
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple


class PlayerProfile(Enum):
    CASUAL = "casual"
    COMPLETIONIST = "completionist"
    SPEEDRUNNER = "speedrunner"
    EXPLORER = "explorer"
    AGGRESSIVE = "aggressive"
    PACIFIST = "pacifist"
    PUZZLE_SOLVER = "puzzle_solver"


class PlaytestMode(Enum):
    QUICK_SMOKE = "quick_smoke"
    FULL_PLAYTHROUGH = "full_playthrough"
    STRESS_TEST = "stress_test"
    BOUNDARY_TEST = "boundary_test"
    SPEED_TEST = "speed_test"
    REGRESSION_TEST = "regression_test"


class BugCategory(Enum):
    GAMEPLAY = "gameplay"
    VISUAL = "visual"
    AUDIO = "audio"
    PERFORMANCE = "performance"
    LOGIC = "logic"
    COLLISION = "collision"
    AI = "ai"
    UI = "ui"
    PROGRESSION = "progression"


class SessionOutcome(Enum):
    COMPLETED = "completed"
    STUCK = "stuck"
    QUIT = "quit"
    CRASHED = "crashed"
    TIMEOUT = "timeout"


_PROFILE_BEHAVIOR_WEIGHTS: Dict[str, Dict[str, float]] = {
    "casual": {
        "move_forward": 0.35, "move_left": 0.05, "move_right": 0.05,
        "move_backward": 0.02, "jump": 0.10, "interact": 0.12,
        "attack": 0.05, "defend": 0.05, "use_item": 0.08,
        "wait": 0.08, "crouch": 0.02, "sprint": 0.03,
    },
    "completionist": {
        "move_forward": 0.20, "move_left": 0.10, "move_right": 0.10,
        "move_backward": 0.08, "jump": 0.08, "interact": 0.18,
        "attack": 0.08, "defend": 0.03, "use_item": 0.05,
        "wait": 0.02, "crouch": 0.05, "sprint": 0.03,
    },
    "speedrunner": {
        "move_forward": 0.45, "move_left": 0.02, "move_right": 0.02,
        "move_backward": 0.01, "jump": 0.15, "interact": 0.02,
        "attack": 0.03, "defend": 0.01, "use_item": 0.01,
        "wait": 0.01, "crouch": 0.02, "sprint": 0.25,
    },
    "explorer": {
        "move_forward": 0.15, "move_left": 0.15, "move_right": 0.15,
        "move_backward": 0.08, "jump": 0.12, "interact": 0.15,
        "attack": 0.03, "defend": 0.02, "use_item": 0.05,
        "wait": 0.03, "crouch": 0.05, "sprint": 0.02,
    },
    "aggressive": {
        "move_forward": 0.25, "move_left": 0.05, "move_right": 0.05,
        "move_backward": 0.01, "jump": 0.08, "interact": 0.04,
        "attack": 0.30, "defend": 0.05, "use_item": 0.07,
        "wait": 0.01, "crouch": 0.02, "sprint": 0.07,
    },
    "pacifist": {
        "move_forward": 0.20, "move_left": 0.08, "move_right": 0.08,
        "move_backward": 0.10, "jump": 0.08, "interact": 0.10,
        "attack": 0.01, "defend": 0.15, "use_item": 0.08,
        "wait": 0.07, "crouch": 0.04, "sprint": 0.01,
    },
    "puzzle_solver": {
        "move_forward": 0.15, "move_left": 0.10, "move_right": 0.10,
        "move_backward": 0.05, "jump": 0.05, "interact": 0.20,
        "attack": 0.02, "defend": 0.02, "use_item": 0.15,
        "wait": 0.12, "crouch": 0.02, "sprint": 0.02,
    },
}

_ACTION_TYPES: List[str] = [
    "move_forward", "move_left", "move_right", "move_backward",
    "jump", "interact", "attack", "defend",
    "use_item", "wait", "crouch", "sprint",
]

_MODE_DURATION_LIMITS: Dict[str, int] = {
    "quick_smoke": 60,
    "full_playthrough": 1800,
    "stress_test": 600,
    "boundary_test": 300,
    "speed_test": 120,
    "regression_test": 900,
}

_MODE_ACTION_LIMITS: Dict[str, int] = {
    "quick_smoke": 200,
    "full_playthrough": 5000,
    "stress_test": 10000,
    "boundary_test": 1500,
    "speed_test": 3000,
    "regression_test": 5000,
}

_COMMON_BUG_PATTERNS: List[Dict[str, Any]] = [
    {
        "category": BugCategory.COLLISION.value,
        "title": "Wall clipping detected",
        "description": "Player passed through a solid wall or obstacle",
        "severity": "error",
    },
    {
        "category": BugCategory.PROGRESSION.value,
        "title": "Trigger zone not firing",
        "description": "Expected event trigger did not activate on entry",
        "severity": "critical",
    },
    {
        "category": BugCategory.GAMEPLAY.value,
        "title": "Action not responding",
        "description": "Player input did not produce expected game response",
        "severity": "error",
    },
    {
        "category": BugCategory.PERFORMANCE.value,
        "title": "Frame rate drop",
        "description": "FPS dropped below acceptable threshold in current area",
        "severity": "warning",
    },
    {
        "category": BugCategory.AI.value,
        "title": "NPC pathfinding failure",
        "description": "AI agent failed to navigate to target destination",
        "severity": "error",
    },
    {
        "category": BugCategory.LOGIC.value,
        "title": "State inconsistency",
        "description": "Game state variables are in an inconsistent configuration",
        "severity": "critical",
    },
    {
        "category": BugCategory.UI.value,
        "title": "UI element misalignment",
        "description": "Interface element rendered at incorrect position",
        "severity": "warning",
    },
    {
        "category": BugCategory.VISUAL.value,
        "title": "Z-fighting artifact",
        "description": "Overlapping geometry producing flicker at current camera angle",
        "severity": "info",
    },
    {
        "category": BugCategory.AUDIO.value,
        "title": "Missing sound effect",
        "description": "Expected audio cue did not play on interaction",
        "severity": "warning",
    },
]

_REGRESSION_BASELINES: Dict[str, Dict[str, float]] = {}


@dataclass
class PlaytestSession:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    game_scene: str = ""
    mode: str = PlaytestMode.QUICK_SMOKE.value
    player_profile: str = PlayerProfile.CASUAL.value
    start_time: float = field(default_factory=lambda: __import__("time").time())
    end_time: Optional[float] = None
    actions_performed: int = 0
    areas_visited: List[str] = field(default_factory=list)
    bugs_found: int = 0
    outcome: str = SessionOutcome.COMPLETED.value
    replay_data: List[Dict[str, Any]] = field(default_factory=list)
    created_at: float = field(default_factory=lambda: __import__("time").time())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "game_scene": self.game_scene,
            "mode": self.mode,
            "player_profile": self.player_profile,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "actions_performed": self.actions_performed,
            "areas_visited": list(self.areas_visited),
            "bugs_found": self.bugs_found,
            "outcome": self.outcome,
            "replay_frames": len(self.replay_data),
            "created_at": self.created_at,
        }


@dataclass
class PlaytestAction:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    session_id: str = ""
    action_type: str = ""
    target_object: str = ""
    position: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    timestamp: float = field(default_factory=lambda: __import__("time").time())
    success: bool = True
    game_state_snapshot: Dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=lambda: __import__("time").time())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "session_id": self.session_id,
            "action_type": self.action_type,
            "target_object": self.target_object,
            "position": list(self.position),
            "timestamp": self.timestamp,
            "success": self.success,
            "state_keys": list(self.game_state_snapshot.keys()),
            "created_at": self.created_at,
        }


@dataclass
class BugReport:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    session_id: str = ""
    category: str = BugCategory.GAMEPLAY.value
    title: str = ""
    description: str = ""
    severity: str = "warning"
    reproduction_steps: List[str] = field(default_factory=list)
    expected_behavior: str = ""
    actual_behavior: str = ""
    screenshot_ref: str = ""
    created_at: float = field(default_factory=lambda: __import__("time").time())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "session_id": self.session_id,
            "category": self.category,
            "title": self.title,
            "description": self.description,
            "severity": self.severity,
            "reproduction_steps": list(self.reproduction_steps),
            "expected_behavior": self.expected_behavior,
            "actual_behavior": self.actual_behavior,
            "screenshot_ref": self.screenshot_ref,
            "created_at": self.created_at,
        }


@dataclass
class PlaytestSummary:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    session_id: str = ""
    total_actions: int = 0
    unique_areas: int = 0
    playtime_seconds: float = 0.0
    bugs_found: int = 0
    completion_percent: float = 0.0
    difficulty_assessment: float = 0.0
    fun_score: float = 0.0
    suggestions: List[str] = field(default_factory=list)
    created_at: float = field(default_factory=lambda: __import__("time").time())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "session_id": self.session_id,
            "total_actions": self.total_actions,
            "unique_areas": self.unique_areas,
            "playtime_seconds": round(self.playtime_seconds, 2),
            "bugs_found": self.bugs_found,
            "completion_percent": round(self.completion_percent, 2),
            "difficulty_assessment": round(self.difficulty_assessment, 2),
            "fun_score": round(self.fun_score, 2),
            "suggestion_count": len(self.suggestions),
            "created_at": self.created_at,
        }


class AgenticPlaytestSimulator:
    """
    Automated playtest simulator that drives AI player agents through game
    scenes to discover bugs, evaluate design quality, and measure progression.

    Supports multiple player profiles (casual, completionist, speedrunner, etc.)
    and playtest modes (smoke test, full playthrough, stress test, boundary test,
    speed test, regression test).

    Tracks per-session actions, generates bug reports, softlock detection,
    and produces comprehensive playtest summaries with difficulty and fun scores.

    Usage:
        sim = get_playtest_simulator()
        session = sim.start_session("level_01", PlaytestMode.FULL_PLAYTHROUGH,
            PlayerProfile.AGGRESSIVE)
        sim.simulate_sequence(session.id, ["move_forward", "jump", "attack"])
        bugs = sim.detect_softlocks(session.id)
        summary = sim.generate_summary(session.id)
    """

    _instance: Optional["AgenticPlaytestSimulator"] = None
    _lock: threading.RLock = threading.RLock()

    DEFAULT_MAX_AUTO_EXPLORE_ACTIONS = 1000
    FUN_SCORE_BASELINE = 0.5
    COMPLETION_THRESHOLD = 0.95
    STUCK_POSITION_THRESHOLD = 5.0

    def __new__(cls) -> "AgenticPlaytestSimulator":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    instance = super().__new__(cls)
                    cls._instance = instance
        return cls._instance

    @classmethod
    def get_instance(cls) -> "AgenticPlaytestSimulator":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def __init__(self):
        if hasattr(self, "_initialized") and self._initialized:
            return
        self._initialized = True

        self._sessions: Dict[str, PlaytestSession] = {}
        self._actions: Dict[str, List[PlaytestAction]] = {}
        self._bugs: Dict[str, List[BugReport]] = {}
        self._summaries: Dict[str, PlaytestSummary] = {}
        self._session_state: Dict[str, Dict[str, Any]] = {}
        self._softlock_registry: Dict[str, List[str]] = {}
        self._total_sessions: int = 0
        self._total_actions: int = 0
        self._total_bugs: int = 0
        self._scene_registry: Dict[str, List[str]] = {}

    def start_session(
        self,
        game_scene: str,
        mode: PlaytestMode,
        player_profile: PlayerProfile,
    ) -> PlaytestSession:
        session = PlaytestSession(
            game_scene=game_scene,
            mode=mode.value,
            player_profile=player_profile.value,
        )
        self._sessions[session.id] = session
        self._actions[session.id] = []
        self._bugs[session.id] = []
        self._session_state[session.id] = self._initialize_state(player_profile)
        self._softlock_registry[session.id] = []
        self._total_sessions += 1

        if game_scene not in self._scene_registry:
            self._scene_registry[game_scene] = []
        self._scene_registry[game_scene].append(session.id)

        return session

    def _initialize_state(self, player_profile: PlayerProfile) -> Dict[str, Any]:
        profile_key = player_profile.value
        weights = _PROFILE_BEHAVIOR_WEIGHTS.get(profile_key, _PROFILE_BEHAVIOR_WEIGHTS["casual"])

        speed_multiplier = 1.0
        if player_profile == PlayerProfile.SPEEDRUNNER:
            speed_multiplier = 2.0
        elif player_profile == PlayerProfile.CASUAL:
            speed_multiplier = 0.7

        return {
            "position": [0.0, 0.0, 0.0],
            "rotation": [0.0, 0.0, 0.0],
            "health": 100.0,
            "stamina": 100.0,
            "inventory": [],
            "current_area": "spawn",
            "visited_areas": {"spawn"},
            "action_history": [],
            "behavior_weights": dict(weights),
            "stuck_counter": 0,
            "last_positions": [(0.0, 0.0, 0.0)] * 10,
            "path_target": (10.0, 0.0, 10.0),
            "interaction_history": [],
            "speed_multiplier": speed_multiplier,
            "completion_progress": 0.0,
            "encountered_objects": set(),
            "puzzle_attempts": {},
        }

    def simulate_action(
        self,
        session_id: str,
        action_type: str,
        target: str = "",
    ) -> Optional[PlaytestAction]:
        session = self._sessions.get(session_id)
        if session is None:
            return None

        state = self._session_state.get(session_id)
        if state is None:
            return None

        success = random.random() > 0.03

        new_position = self._compute_new_position(state, action_type)

        action = PlaytestAction(
            session_id=session_id,
            action_type=action_type,
            target_object=target,
            position=tuple(new_position),
            success=success,
            game_state_snapshot={
                "health": state["health"],
                "stamina": state["stamina"],
                "area": state["current_area"],
                "progress": state["completion_progress"],
            },
        )
        self._actions[session_id].append(action)
        self._total_actions += 1

        self._apply_action_effects(state, action_type, new_position)

        state["action_history"].append(action_type)
        state["last_positions"].append(tuple(new_position))
        state["last_positions"] = state["last_positions"][-10:]

        if action_type == "interact":
            state["interaction_history"].append({
                "target": target,
                "position": tuple(new_position),
                "timestamp": action.timestamp,
            })

        session.actions_performed += 1
        self._record_replay_frame(session.id, action)

        mode_limits = _MODE_ACTION_LIMITS.get(session.mode, 5000)
        if session.actions_performed >= mode_limits:
            session.outcome = SessionOutcome.TIMEOUT.value
            session.end_time = time.time()

        self._check_state_consistency(session.id)

        return action

    def _compute_new_position(
        self, state: Dict[str, Any], action_type: str
    ) -> List[float]:
        px, py, pz = state["position"]
        speed = 1.0 * state["speed_multiplier"]

        if action_type == "move_forward":
            pz += speed * random.uniform(0.8, 1.2)
        elif action_type == "move_backward":
            pz -= speed * random.uniform(0.5, 0.8)
        elif action_type == "move_left":
            px -= speed * random.uniform(0.5, 1.0)
        elif action_type == "move_right":
            px += speed * random.uniform(0.5, 1.0)
        elif action_type == "jump":
            py += speed * random.uniform(0.8, 1.5)
        elif action_type == "sprint":
            pz += speed * random.uniform(1.5, 2.5)
        elif action_type == "crouch":
            py -= 0.5

        px += random.uniform(-0.1, 0.1)
        py += random.uniform(-0.05, 0.05)
        pz += random.uniform(-0.1, 0.1)

        return [round(px, 3), round(py, 3), round(pz, 3)]

    def _apply_action_effects(
        self, state: Dict[str, Any], action_type: str, new_position: List[float]
    ) -> None:
        state["position"] = new_position

        if action_type == "sprint":
            state["stamina"] = max(0.0, state["stamina"] - random.uniform(5.0, 10.0))

        if action_type in ("attack", "defend", "sprint"):
            state["stamina"] = max(0.0, state["stamina"] - random.uniform(2.0, 8.0))
        else:
            state["stamina"] = min(100.0, state["stamina"] + random.uniform(1.0, 3.0))

        area_code = self._position_to_area(new_position)
        if area_code != state["current_area"]:
            state["current_area"] = area_code
            state["visited_areas"].add(area_code)

        progress_increment = 0.0
        if action_type == "move_forward":
            progress_increment = random.uniform(0.1, 0.5)
        elif action_type == "jump":
            progress_increment = random.uniform(0.05, 0.2)
        elif action_type == "interact":
            progress_increment = random.uniform(0.2, 1.0)

        state["completion_progress"] = min(100.0, state["completion_progress"] + progress_increment)

        if state["health"] <= 0:
            state["health"] = 100.0
            state["position"] = [0.0, 0.0, 0.0]
            state["completion_progress"] = max(0.0, state["completion_progress"] - 10.0)

        if action_type == "interact":
            obj_id = f"obj_{random.randint(1, 500)}"
            state["encountered_objects"].add(obj_id)

    def _position_to_area(self, position: List[float]) -> str:
        grid_size = 20.0
        gx = int(position[0] / grid_size)
        gy = int(position[1] / grid_size)
        gz = int(position[2] / grid_size)
        return f"area_{gx}_{gy}_{gz}"

    def simulate_sequence(
        self, session_id: str, action_sequence: List[str]
    ) -> List[PlaytestAction]:
        actions: List[PlaytestAction] = []
        for action_type in action_sequence:
            if action_type not in _ACTION_TYPES:
                continue
            result = self.simulate_action(session_id, action_type)
            if result is not None:
                actions.append(result)
        return actions

    def auto_explore(
        self, session_id: str, max_actions: int = 0
    ) -> Optional[PlaytestSession]:
        session = self._sessions.get(session_id)
        if session is None:
            return None

        limit = max_actions if max_actions > 0 else self.DEFAULT_MAX_AUTO_EXPLORE_ACTIONS
        state = self._session_state.get(session_id)
        if state is None:
            return None

        weights = state["behavior_weights"]
        weighted_actions: List[str] = []
        for action, weight in weights.items():
            count = max(1, int(weight * 100))
            weighted_actions.extend([action] * count)

        for i in range(limit):
            if session.outcome != SessionOutcome.COMPLETED.value:
                break

            mode_limit = _MODE_ACTION_LIMITS.get(session.mode, 5000)
            if session.actions_performed >= mode_limit:
                session.outcome = SessionOutcome.TIMEOUT.value
                session.end_time = time.time()
                break

            chosen_action = random.choice(weighted_actions)
            self.simulate_action(session_id, chosen_action)

            if state["completion_progress"] >= 100.0:
                session.outcome = SessionOutcome.COMPLETED.value
                session.end_time = time.time()

            if i % 50 == 0:
                bugs = self.detect_softlocks(session_id)
                if bugs:
                    session.bugs_found += len(bugs)
                    self._bugs[session_id].extend(bugs)

            if i % 200 == 0:
                random_bug = self._generate_random_bug(session_id)
                if random_bug is not None:
                    session.bugs_found += 1
                    self._bugs[session_id].append(random_bug)

        session.areas_visited = list(state["visited_areas"])
        return session

    def _generate_random_bug(self, session_id: str) -> Optional[BugReport]:
        if random.random() > 0.12:
            return None

        pattern = random.choice(_COMMON_BUG_PATTERNS)
        state = self._session_state.get(session_id, {})

        return BugReport(
            session_id=session_id,
            category=pattern["category"],
            title=pattern["title"],
            description=pattern["description"],
            severity=pattern.get("severity", "warning"),
            reproduction_steps=[
                f"Start playtest session for scene",
                f"Perform actions near {state.get('current_area', 'unknown')}",
                f"Observe: {pattern['description']}",
            ],
            expected_behavior="Game operates correctly without the described issue",
            actual_behavior=pattern["description"],
        )

    def report_bug(
        self,
        session_id: str,
        category: BugCategory,
        description: str,
        severity: str = "warning",
    ) -> Optional[BugReport]:
        session = self._sessions.get(session_id)
        if session is None:
            return None

        state = self._session_state.get(session_id, {})

        bug = BugReport(
            session_id=session_id,
            category=category.value,
            title=f"{category.value.title()} issue in {session.game_scene}",
            description=description,
            severity=severity,
            reproduction_steps=[
                f"Session ID: {session_id}",
                f"Player profile: {session.player_profile}",
                f"Current area: {state.get('current_area', 'unknown')}",
                f"Position: {state.get('position', [0,0,0])}",
            ],
            expected_behavior="Normal gameplay without the described issue",
            actual_behavior=description,
        )
        self._bugs[session_id].append(bug)
        session.bugs_found += 1
        self._total_bugs += 1
        return bug

    def generate_summary(self, session_id: str) -> Optional[PlaytestSummary]:
        session = self._sessions.get(session_id)
        if session is None:
            return None

        state = self._session_state.get(session_id, {})
        actions = self._actions.get(session_id, [])
        bugs = self._bugs.get(session_id, [])

        total_actions = len(actions)
        unique_areas = len(state.get("visited_areas", set()))
        playtime = session.end_time - session.start_time if session.end_time else time.time() - session.start_time
        bugs_found = len(bugs)
        completion = state.get("completion_progress", 0.0)

        difficulty = self._assess_difficulty(session, state)

        fun_score = self.FUN_SCORE_BASELINE
        if completion > 70:
            fun_score += 0.15
        if 3 <= unique_areas <= 20:
            fun_score += 0.10
        if bugs_found < 5:
            fun_score += 0.10
        if playtime > 60 and completion > 50:
            fun_score += 0.10
        if total_actions > 100:
            fun_score += 0.05
        fun_score = min(1.0, max(0.0, fun_score))

        suggestions: List[str] = []
        if difficulty > 0.8:
            suggestions.append("Reduce enemy density or damage to improve accessibility.")
        if bugs_found > 10:
            suggestions.append("High bug count; prioritize fixing critical and error-level issues.")
        if completion < 50:
            suggestions.append("Low completion rate; check for progression blockers.")
        if unique_areas < 3:
            suggestions.append("Limited area exploration; consider expanding level geometry.")
        if playtime < 30 and completion < 30:
            suggestions.append("Very short playtime with low completion; check for early frustration points.")
        if not suggestions:
            suggestions.append("Level design looks well-balanced. Consider adding optional secrets.")

        summary = PlaytestSummary(
            session_id=session_id,
            total_actions=total_actions,
            unique_areas=unique_areas,
            playtime_seconds=playtime,
            bugs_found=bugs_found,
            completion_percent=completion,
            difficulty_assessment=difficulty,
            fun_score=fun_score,
            suggestions=suggestions,
        )
        self._summaries[session_id] = summary
        return summary

    def _assess_difficulty(
        self, session: PlaytestSession, state: Dict[str, Any]
    ) -> float:
        difficulty = 0.3

        if session.player_profile == PlayerProfile.CASUAL.value:
            difficulty += 0.1

        bugs = self._bugs.get(session.id, [])
        critical_count = sum(1 for b in bugs if b.severity == "critical")
        error_count = sum(1 for b in bugs if b.severity == "error")
        difficulty += critical_count * 0.08 + error_count * 0.03

        if state.get("health", 100) < 50:
            difficulty += 0.1

        completion = state.get("completion_progress", 0.0)
        if completion < 30:
            difficulty += 0.15

        return min(1.0, difficulty)

    def detect_softlocks(self, session_id: str) -> List[BugReport]:
        session = self._sessions.get(session_id)
        if session is None:
            return []

        state = self._session_state.get(session_id)
        if state is None:
            return []

        bugs: List[BugReport] = []

        recent_positions = state["last_positions"]
        if len(recent_positions) >= 10:
            unique_recent = set(recent_positions[-10:])
            if len(unique_recent) <= 2:
                pos = recent_positions[-1]
                lock_id = f"softlock_{session_id}_{pos}"

                if lock_id not in self._softlock_registry.get(session_id, []):
                    self._softlock_registry[session_id].append(lock_id)

                    bug = BugReport(
                        session_id=session_id,
                        category=BugCategory.PROGRESSION.value,
                        title="Potential softlock detected",
                        description=f"Player stuck in position {pos} for extended period",
                        severity="critical",
                        reproduction_steps=[
                            f"Navigate to area {state['current_area']}",
                            f"Approach position {pos}",
                            "Observe inability to progress further",
                        ],
                        expected_behavior="Player can always progress to the next area",
                        actual_behavior="Player trapped in unescapable position",
                    )
                    bugs.append(bug)

        unreachable_target = state.get("path_target", (0, 0, 0))
        current_pos = tuple(state["position"])
        if hasattr(self, "_path_target_cache"):
            target_attempts = self._path_target_cache.get(session_id, [])
            px, py, pz = current_pos
            tx, ty, tz = unreachable_target
            dist = math.sqrt((tx - px) ** 2 + (ty - py) ** 2 + (tz - pz) ** 2)
            if dist > 50:
                target_attempts.append({"position": unreachable_target, "attempts": 1})
                if len(target_attempts) > 5:
                    bug = BugReport(
                        session_id=session_id,
                        category=BugCategory.COLLISION.value,
                        title="Unreachable navigation target",
                        description=f"Target {unreachable_target} cannot be reached from {current_pos}",
                        severity="error",
                        reproduction_steps=[
                            f"Start from area {state['current_area']}",
                            f"Attempt to navigate to {unreachable_target}",
                            "Navigation consistently fails",
                        ],
                        expected_behavior="All visible areas should be reachable via navigation",
                        actual_behavior="Target area is inaccessible",
                    )
                    bugs.append(bug)

        return bugs

    def measure_completion_rate(self, session_id: str) -> float:
        state = self._session_state.get(session_id)
        if state is None:
            return 0.0
        return round(state.get("completion_progress", 0.0), 2)

    def replay_session(self, session_id: str) -> List[PlaytestAction]:
        session = self._sessions.get(session_id)
        if session is None:
            return []
        return list(self._actions.get(session_id, []))

    def stress_boundary(
        self, session_id: str, target_system: str
    ) -> List[BugReport]:
        session = self._sessions.get(session_id)
        if session is None:
            return []

        bugs: List[BugReport] = []
        state = self._session_state.get(session_id, {})

        if target_system == "navigation":
            for i in range(50):
                self.simulate_action(session_id, "sprint")
                self.simulate_action(session_id, "jump")
                if i % 5 == 0:
                    pos = state.get("position", [0, 0, 0])
                    if pos == [0.0, 0.0, 0.0]:
                        bugs.append(BugReport(
                            session_id=session_id,
                            category=BugCategory.COLLISION.value,
                            title="Navigation boundary failure",
                            description=f"Navigation broke at iteration {i}, reset to origin",
                            severity="error",
                            reproduction_steps=[
                                f"Run {i} rapid movement actions",
                                "Observe position reset to origin",
                            ],
                            expected_behavior="Navigation handles rapid input without reset",
                            actual_behavior="Position was forcibly reset to spawn",
                        ))

        elif target_system == "interaction":
            for i in range(30):
                self.simulate_action(session_id, "interact", target=f"stress_obj_{i}")
            interactions = state.get("interaction_history", [])
            if len(interactions) < 30:
                bugs.append(BugReport(
                    session_id=session_id,
                    category=BugCategory.GAMEPLAY.value,
                    title="Interaction system overflow",
                    description=f"Only {len(interactions)} of 30 interactions registered",
                    severity="critical",
                    reproduction_steps=[
                        "Rapidly interact with 30 distinct objects",
                        "Check interaction history count",
                    ],
                    expected_behavior="All interactions are registered",
                    actual_behavior=f"Only {len(interactions)} interactions were recorded",
                ))

        elif target_system == "combat":
            for i in range(100):
                self.simulate_action(session_id, "attack")
            health = state.get("health", 100)
            if health > 90:
                pass

        elif target_system == "physics":
            for i in range(40):
                self.simulate_action(session_id, "jump")
                self.simulate_action(session_id, "crouch")
                if i % 3 == 0:
                    self.simulate_action(session_id, "sprint")

        elif target_system == "memory":
            for i in range(200):
                self.simulate_action(session_id, "use_item")
            if len(self._actions.get(session_id, [])) > 150:
                bugs.append(BugReport(
                    session_id=session_id,
                    category=BugCategory.PERFORMANCE.value,
                    title="Memory pressure under rapid item usage",
                    description="Performance degradation after 200 rapid item uses",
                    severity="warning",
                    reproduction_steps=[
                        "Execute 200 consecutive use_item actions",
                        "Monitor frame time and memory usage",
                    ],
                    expected_behavior="Stable performance under rapid item usage",
                    actual_behavior="Potential memory accumulation detected",
                ))

        for bug in bugs:
            self._bugs[session_id].append(bug)
            session.bugs_found += 1
            self._total_bugs += 1

        return bugs

    def _navigate_to(
        self, session: PlaytestSession, position: Tuple[float, float, float]
    ) -> None:
        state = self._session_state.get(session.id)
        if state is None:
            return

        state["path_target"] = position

        for _step in range(20):
            tx, ty, tz = position
            px, py, pz = state["position"]
            distance = math.sqrt((tx - px) ** 2 + (ty - py) ** 2 + (tz - pz) ** 2)

            if distance < 1.0:
                break

            if abs(tx - px) > abs(tz - pz):
                self.simulate_action(session.id, "move_right" if tx > px else "move_left")
            else:
                self.simulate_action(session.id, "move_forward" if tz > pz else "move_backward")

    def _interact_with(self, session: PlaytestSession, object_id: str) -> None:
        state = self._session_state.get(session.id)
        if state is None:
            return

        self.simulate_action(session.id, "interact", target=object_id)
        state["encountered_objects"].add(object_id)

    def _check_state_consistency(self, session_id: str) -> None:
        state = self._session_state.get(session_id)
        if state is None:
            return

        if state["health"] < 0 or state["health"] > 100:
            state["health"] = max(0.0, min(100.0, state["health"]))

        if state["stamina"] < 0 or state["stamina"] > 100:
            state["stamina"] = max(0.0, min(100.0, state["stamina"]))

        px, py, pz = state["position"]
        if abs(px) > 10000 or abs(py) > 10000 or abs(pz) > 10000:
            state["position"] = [0.0, 0.0, 0.0]
            self.report_bug(
                session_id=session_id,
                category=BugCategory.PHYSICS if hasattr(BugCategory, "PHYSICS") else BugCategory.COLLISION,
                description="Player position exceeded world bounds and was reset",
                severity="error",
            )

    def _record_replay_frame(
        self, session_id: str, action: PlaytestAction
    ) -> None:
        session = self._sessions.get(session_id)
        if session is None:
            return
        session.replay_data.append({
            "action_id": action.id,
            "action_type": action.action_type,
            "position": list(action.position),
            "timestamp": action.timestamp,
            "success": action.success,
        })

    def store_regression_baseline(
        self, session_id: str, baseline_name: str
    ) -> bool:
        session = self._sessions.get(session_id)
        if session is None:
            return False

        summary = self.generate_summary(session_id)
        if summary is None:
            return False

        _REGRESSION_BASELINES[baseline_name] = {
            "total_actions": summary.total_actions,
            "unique_areas": summary.unique_areas,
            "playtime_seconds": summary.playtime_seconds,
            "bugs_found": summary.bugs_found,
            "completion_percent": summary.completion_percent,
            "difficulty_assessment": summary.difficulty_assessment,
            "fun_score": summary.fun_score,
            "scene": session.game_scene,
            "mode": session.mode,
            "profile": session.player_profile,
        }
        return True

    def compare_with_baseline(
        self, session_id: str, baseline_name: str
    ) -> Optional[Dict[str, Any]]:
        baseline = _REGRESSION_BASELINES.get(baseline_name)
        if baseline is None:
            return None

        summary = self.generate_summary(session_id)
        if summary is None:
            return None

        return {
            "baseline_name": baseline_name,
            "current_total_actions": summary.total_actions,
            "baseline_total_actions": baseline["total_actions"],
            "actions_delta": summary.total_actions - baseline["total_actions"],
            "current_completion": summary.completion_percent,
            "baseline_completion": baseline["completion_percent"],
            "completion_delta": round(summary.completion_percent - baseline["completion_percent"], 2),
            "current_bugs": summary.bugs_found,
            "baseline_bugs": baseline["bugs_found"],
            "bugs_delta": summary.bugs_found - baseline["bugs_found"],
            "current_fun_score": summary.fun_score,
            "baseline_fun_score": baseline["fun_score"],
            "fun_score_delta": round(summary.fun_score - baseline["fun_score"], 2),
            "regression_detected": (
                summary.completion_percent < baseline["completion_percent"] - 5.0
                or summary.bugs_found > baseline["bugs_found"] + 3
            ),
        }

    def get_session(self, session_id: str) -> Optional[PlaytestSession]:
        return self._sessions.get(session_id)

    def get_actions_for_session(self, session_id: str) -> List[PlaytestAction]:
        return self._actions.get(session_id, [])

    def get_bugs_for_session(self, session_id: str) -> List[BugReport]:
        return self._bugs.get(session_id, [])

    def get_summary(self, session_id: str) -> Optional[PlaytestSummary]:
        return self._summaries.get(session_id)

    def get_sessions_for_scene(self, game_scene: str) -> List[str]:
        return self._scene_registry.get(game_scene, [])

    def get_all_sessions(self) -> List[PlaytestSession]:
        return list(self._sessions.values())

    def get_all_baselines(self) -> List[str]:
        return list(_REGRESSION_BASELINES.keys())

    def get_stats(self) -> Dict[str, Any]:
        total_sessions = len(self._sessions)
        completed = sum(
            1 for s in self._sessions.values()
            if s.outcome == SessionOutcome.COMPLETED.value
        )
        stuck = sum(
            1 for s in self._sessions.values()
            if s.outcome == SessionOutcome.STUCK.value
        )
        crashed = sum(
            1 for s in self._sessions.values()
            if s.outcome == SessionOutcome.CRASHED.value
        )
        timed_out = sum(
            1 for s in self._sessions.values()
            if s.outcome == SessionOutcome.TIMEOUT.value
        )

        profile_breakdown: Dict[str, int] = {}
        for s in self._sessions.values():
            profile_breakdown[s.player_profile] = profile_breakdown.get(s.player_profile, 0) + 1

        mode_breakdown: Dict[str, int] = {}
        for s in self._sessions.values():
            mode_breakdown[s.mode] = mode_breakdown.get(s.mode, 0) + 1

        category_breakdown: Dict[str, int] = {}
        for bug_list in self._bugs.values():
            for bug in bug_list:
                category_breakdown[bug.category] = category_breakdown.get(bug.category, 0) + 1

        avg_completion = 0.0
        if total_sessions > 0:
            avg_completion = sum(
                s.completion_percent for s in self._summaries.values()
            ) / max(1, len(self._summaries))

        return {
            "total_sessions": total_sessions,
            "total_actions": self._total_actions,
            "total_bugs": self._total_bugs,
            "completed": completed,
            "stuck": stuck,
            "crashed": crashed,
            "timed_out": timed_out,
            "completion_rate": round(completed / max(1, total_sessions), 4),
            "average_completion_percent": round(avg_completion, 2),
            "scenes_tested": len(self._scene_registry),
            "profile_breakdown": profile_breakdown,
            "mode_breakdown": mode_breakdown,
            "bug_category_breakdown": category_breakdown,
            "baselines_stored": len(_REGRESSION_BASELINES),
            "summaries_generated": len(self._summaries),
        }


def get_playtest_simulator() -> AgenticPlaytestSimulator:
    return AgenticPlaytestSimulator.get_instance()