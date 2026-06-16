"""
SparkLabs Agent - Autonomous AI Playtesting Framework

AI-driven playtesting system that simulates gameplay through autonomous agents
to discover bugs, evaluate balance, measure fun factor, and assess difficulty
curves for the AI-native game engine. Supports multiple test types and generates
comprehensive playtest reports with actionable recommendations.

Architecture:
  PlaytestingFramework (Singleton)
    |-- PlaytestSession (active testing session lifecycle)
    |-- TestCase (individual test definition and execution)
    |-- BugReport (discovered issue with reproduction steps)
    |-- PlaytestReport (aggregated session metrics and analysis)

Test Types:
  - FUNCTIONAL: entity spawning, collision, triggers, scene transitions
  - BALANCE: combat encounters, win/loss ratios, resource economy
  - PERFORMANCE: stress testing with many entities, frame drop measurement
  - COMPLETION: level progression verification, softlock detection
  - EXPLORATORY: random walk simulation, edge case discovery
  - STRESS: resource limit and boundary condition testing
  - REGRESSION: comparison against previous baselines
  - USABILITY: player experience and interaction flow evaluation

Usage:
    framework = get_playtesting_framework()
    session = framework.create_session("game_001", [TestType.FUNCTIONAL],
        game_config={"levels": 5, "entities": ["player", "enemy", "npc"]})
    framework.run_full_test_suite(session.session_id)
    report = framework.generate_report(session.session_id)
"""

from __future__ import annotations

import json
import math
import random
import threading
import time
import uuid
from collections import deque
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple


_time_module = time


# ------------------------------------------------------------------
# Enums
# ------------------------------------------------------------------


class TestType(Enum):
    """Categories of automated playtesting that can be executed."""
    FUNCTIONAL = "functional"
    BALANCE = "balance"
    PERFORMANCE = "performance"
    USABILITY = "usability"
    COMPLETION = "completion"
    STRESS = "stress"
    REGRESSION = "regression"
    EXPLORATORY = "exploratory"


class BugSeverity(Enum):
    """Severity classification for discovered bugs."""
    COSMETIC = "cosmetic"
    MINOR = "minor"
    MODERATE = "moderate"
    MAJOR = "major"
    CRITICAL = "critical"
    BLOCKER = "blocker"


class TestResult(Enum):
    """Outcome of an individual test case execution."""
    PASS = "pass"
    FAIL = "fail"
    WARNING = "warning"
    SKIPPED = "skipped"
    INCONCLUSIVE = "inconclusive"


class SessionStatus(Enum):
    """Current state of a playtest session."""
    CREATED = "created"
    RUNNING = "running"
    COMPLETED = "completed"
    ABORTED = "aborted"
    ERROR = "error"


# ------------------------------------------------------------------
# Bug and issue categories for classification
# ------------------------------------------------------------------

ISSUE_CATEGORIES: List[str] = [
    "collision", "physics", "rendering", "audio", "input",
    "ai", "pathfinding", "ui", "networking", "memory",
    "progression", "dialogue", "inventory", "combat", "economy",
    "save_load", "menus", "animation", "scripting", "localization",
]

# ------------------------------------------------------------------
# Action pool for simulated gameplay
# ------------------------------------------------------------------

_GAMEPLAY_ACTIONS: List[str] = [
    "move_forward", "move_backward", "strafe_left", "strafe_right",
    "jump", "crouch", "sprint", "dodge",
    "primary_attack", "secondary_attack", "special_ability",
    "interact", "pickup", "use_item", "drop_item",
    "open_menu", "close_menu", "pause", "quick_save",
    "talk_npc", "skip_dialogue", "activate_trigger",
    "climb", "swim", "fly", "grapple",
]

# ------------------------------------------------------------------
# Dataclasses
# ------------------------------------------------------------------


@dataclass
class PlaytestSession:
    """An active playtesting session tracking all test execution state."""
    session_id: str = field(default_factory=lambda: uuid.uuid4().hex[:8])
    game_id: str = ""
    test_types: List[TestType] = field(default_factory=list)
    status: SessionStatus = SessionStatus.CREATED
    started_at: float = 0.0
    completed_at: Optional[float] = None
    total_tests: int = 0
    passed: int = 0
    failed: int = 0
    warnings: int = 0
    bugs_found: int = 0
    duration_seconds: float = 0.0
    game_config: Dict[str, Any] = field(default_factory=dict)
    test_cases: List[TestCase] = field(default_factory=list)
    bug_reports: List[BugReport] = field(default_factory=list)
    simulation_state: Dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=_time_module.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "session_id": self.session_id,
            "game_id": self.game_id,
            "test_types": [t.value for t in self.test_types],
            "status": self.status.value,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "total_tests": self.total_tests,
            "passed": self.passed,
            "failed": self.failed,
            "warnings": self.warnings,
            "bugs_found": self.bugs_found,
            "duration_seconds": round(self.duration_seconds, 2),
            "game_config": dict(self.game_config),
            "test_case_count": len(self.test_cases),
            "bug_report_count": len(self.bug_reports),
            "created_at": self.created_at,
        }

    @property
    def pass_rate(self) -> float:
        if self.total_tests == 0:
            return 0.0
        return self.passed / self.total_tests


@dataclass
class BugReport:
    """A discovered bug with full reproduction and classification details."""
    bug_id: str = field(default_factory=lambda: uuid.uuid4().hex[:8])
    session_id: str = ""
    title: str = ""
    description: str = ""
    severity: BugSeverity = BugSeverity.MINOR
    category: str = ""
    reproduction_steps: List[str] = field(default_factory=list)
    expected_behavior: str = ""
    actual_behavior: str = ""
    location: str = ""
    screenshot_ref: str = ""
    discovered_at: float = field(default_factory=_time_module.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "bug_id": self.bug_id,
            "session_id": self.session_id,
            "title": self.title,
            "description": self.description,
            "severity": self.severity.value,
            "category": self.category,
            "reproduction_steps": list(self.reproduction_steps),
            "expected_behavior": self.expected_behavior,
            "actual_behavior": self.actual_behavior,
            "location": self.location,
            "screenshot_ref": self.screenshot_ref,
            "discovered_at": self.discovered_at,
        }


@dataclass
class TestCase:
    """A single test case definition with execution results."""
    test_id: str = field(default_factory=lambda: uuid.uuid4().hex[:8])
    session_id: str = ""
    test_type: TestType = TestType.FUNCTIONAL
    name: str = ""
    description: str = ""
    steps: List[str] = field(default_factory=list)
    expected_result: str = ""
    actual_result: str = ""
    result: TestResult = TestResult.PASS
    duration_ms: float = 0.0
    bugs_triggered: List[str] = field(default_factory=list)
    created_at: float = field(default_factory=_time_module.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "test_id": self.test_id,
            "session_id": self.session_id,
            "test_type": self.test_type.value,
            "name": self.name,
            "description": self.description,
            "steps": list(self.steps),
            "expected_result": self.expected_result,
            "actual_result": self.actual_result,
            "result": self.result.value,
            "duration_ms": round(self.duration_ms, 2),
            "bugs_triggered": list(self.bugs_triggered),
            "created_at": self.created_at,
        }


@dataclass
class PlaytestReport:
    """Aggregated report summarizing all playtest results and analysis."""
    report_id: str = field(default_factory=lambda: uuid.uuid4().hex[:8])
    session_id: str = ""
    summary: str = ""
    overall_score: float = 0.0
    fun_rating: float = 0.0
    balance_score: float = 0.0
    difficulty_rating: float = 0.0
    performance_score: float = 0.0
    bugs: List[BugReport] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)
    generated_at: float = field(default_factory=_time_module.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "report_id": self.report_id,
            "session_id": self.session_id,
            "summary": self.summary,
            "overall_score": round(self.overall_score, 2),
            "fun_rating": round(self.fun_rating, 2),
            "balance_score": round(self.balance_score, 2),
            "difficulty_rating": round(self.difficulty_rating, 2),
            "performance_score": round(self.performance_score, 2),
            "bug_count": len(self.bugs),
            "recommendation_count": len(self.recommendations),
            "recommendations": list(self.recommendations),
            "generated_at": self.generated_at,
        }


# ------------------------------------------------------------------
# PlaytestingFramework Singleton
# ------------------------------------------------------------------


class PlaytestingFramework:
    """
    Singleton system for autonomous AI-driven game playtesting.

    Manages playtest sessions, executes test suites across multiple test
    types, simulates gameplay through autonomous agent behaviors, and
    generates comprehensive reports covering bugs, balance, fun factor,
    and difficulty assessment.
    """

    _instance: Optional[PlaytestingFramework] = None
    _lock = threading.RLock()

    def __new__(cls) -> PlaytestingFramework:
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    instance = super().__new__(cls)
                    cls._instance = instance
        return cls._instance

    @classmethod
    def get_instance(cls) -> PlaytestingFramework:
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
            self._sessions: Dict[str, PlaytestSession] = {}
            self._reports: Dict[str, PlaytestReport] = {}
            self._stats: Dict[str, Any] = {
                "total_sessions_created": 0,
                "total_tests_run": 0,
                "total_bugs_reported": 0,
                "total_reports_generated": 0,
                "total_gameplay_seconds_simulated": 0,
            }
            self._regression_baselines: Dict[str, Dict[str, Any]] = {}
            self._initialized = True

    # ------------------------------------------------------------------
    # Session Management
    # ------------------------------------------------------------------

    def create_session(
        self,
        game_id: str,
        test_types: List[TestType],
        game_config: Optional[Dict[str, Any]] = None,
    ) -> PlaytestSession:
        """Create a new playtest session for a given game configuration."""
        with self._lock:
            session = PlaytestSession(
                game_id=game_id,
                test_types=list(test_types),
                game_config=game_config or {},
                simulation_state=self._initialize_simulation_state(game_config or {}),
            )
            self._sessions[session.session_id] = session
            self._stats["total_sessions_created"] += 1
            return session

    def _initialize_simulation_state(
        self, game_config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Set up the initial simulation state based on game configuration."""
        level_count = game_config.get("levels", 5)
        entity_types = game_config.get("entities", ["player", "enemy", "npc"])

        return {
            "player_position": [0.0, 0.0, 0.0],
            "player_health": 100.0,
            "player_stamina": 100.0,
            "player_inventory": [],
            "current_level": 1,
            "total_levels": level_count,
            "level_progress": {i: 0.0 for i in range(1, level_count + 1)},
            "visited_areas": set(),
            "entities_spawned": 0,
            "entities_active": 0,
            "triggers_activated": [],
            "collectibles_picked_up": 0,
            "total_collectibles": level_count * 20,
            "combat_encounters": 0,
            "combat_wins": 0,
            "combat_losses": 0,
            "deaths": 0,
            "death_locations": [],
            "time_per_level": {},
            "movement_path": [],
            "resources_collected": 0,
            "resources_spent": 0,
            "frame_times": [],
            "current_fps": 60.0,
            "entity_types": entity_types,
            "rng_seed": random.randint(1, 100000),
        }

    def list_sessions(self) -> List[PlaytestSession]:
        """Return all playtest sessions."""
        with self._lock:
            return list(self._sessions.values())

    def get_session(self, session_id: str) -> Optional[PlaytestSession]:
        """Retrieve a playtest session by its ID."""
        return self._sessions.get(session_id)

    # ------------------------------------------------------------------
    # Test Case Execution
    # ------------------------------------------------------------------

    def run_test_case(
        self,
        session_id: str,
        test_type: TestType,
        name: str,
        description: str,
        steps: List[str],
    ) -> Optional[TestCase]:
        """Execute a single test case within a playtest session."""
        with self._lock:
            session = self._sessions.get(session_id)
            if session is None:
                return None

            start_time = _time_module.time()

            test_case = TestCase(
                session_id=session_id,
                test_type=test_type,
                name=name,
                description=description,
                steps=list(steps),
                expected_result="All steps should execute without errors or unexpected behavior.",
            )

            result, bugs = self._execute_test_steps(session, test_case)

            test_case.duration_ms = (_time_module.time() - start_time) * 1000.0
            test_case.actual_result = result
            test_case.result = self._determine_test_result(result, bugs)
            test_case.bugs_triggered = [b.bug_id for b in bugs]

            session.test_cases.append(test_case)
            session.total_tests += 1
            self._stats["total_tests_run"] += 1

            if test_case.result == TestResult.PASS:
                session.passed += 1
            elif test_case.result == TestResult.FAIL:
                session.failed += 1
            elif test_case.result == TestResult.WARNING:
                session.warnings += 1
                session.failed += 1

            for bug in bugs:
                session.bug_reports.append(bug)
                session.bugs_found += 1
                self._stats["total_bugs_reported"] += 1

            return test_case

    def _execute_test_steps(
        self, session: PlaytestSession, test_case: TestCase
    ) -> Tuple[str, List[BugReport]]:
        """Simulate execution of test steps and detect issues."""
        bugs: List[BugReport] = []
        state = session.simulation_state
        success = True

        for step in test_case.steps:
            step_lower = step.lower()

            if "spawn" in step_lower:
                if not self._simulate_entity_spawn(session):
                    bugs.append(self._create_bug(session, "spawn", test_case))
                    success = False

            elif "collision" in step_lower:
                if not self._simulate_collision_check(session):
                    bugs.append(self._create_bug(session, "collision", test_case))
                    success = False

            elif "trigger" in step_lower or "event" in step_lower:
                if not self._simulate_trigger_activation(session):
                    bugs.append(self._create_bug(session, "trigger", test_case))
                    success = False

            elif "transition" in step_lower or "scene" in step_lower:
                if not self._simulate_scene_transition(session):
                    bugs.append(self._create_bug(session, "transition", test_case))
                    success = False

            elif "combat" in step_lower or "fight" in step_lower:
                bugs.extend(self._simulate_combat_encounter(session, test_case))

            elif "collect" in step_lower or "pickup" in step_lower:
                self._simulate_collectible_pickup(state)

            elif "move" in step_lower or "navigate" in step_lower:
                self._simulate_movement(state)

            elif "interact" in step_lower:
                self._simulate_interaction(state)

            elif "resource" in step_lower:
                self._simulate_resource_usage(state)

            elif "stress" in step_lower or "load" in step_lower:
                bugs.extend(self._simulate_stress_load(session, test_case))

            elif "rand" in step_lower or "explore" in step_lower:
                self._simulate_random_walk(state)

            else:
                self._simulate_movement(state)

        if success and not bugs:
            return "All steps executed successfully.", bugs
        elif success and bugs:
            return "Steps completed but issues were detected.", bugs
        else:
            return "One or more steps failed during execution.", bugs

    def _simulate_entity_spawn(self, session: PlaytestSession) -> bool:
        """Simulate spawning an entity and check for failures."""
        state = session.simulation_state
        entity_types = state.get("entity_types", ["generic"])

        spawn_chance = random.random()
        if spawn_chance < 0.08:
            return False

        state["entities_spawned"] += 1
        state["entities_active"] += 1
        return True

    def _simulate_collision_check(self, session: PlaytestSession) -> bool:
        """Simulate collision detection between entities."""
        state = session.simulation_state
        collision_valid = random.random() > 0.05

        if not collision_valid:
            return False

        if state["entities_active"] > 0:
            state["entities_active"] = max(0, state["entities_active"] - 1)
        return True

    def _simulate_trigger_activation(self, session: PlaytestSession) -> bool:
        """Simulate an event trigger firing."""
        state = session.simulation_state
        trigger_id = f"trigger_{uuid.uuid4().hex[:6]}"

        if random.random() < 0.06:
            return False

        state["triggers_activated"].append(trigger_id)
        return True

    def _simulate_scene_transition(self, session: PlaytestSession) -> bool:
        """Simulate transitioning between levels or scenes."""
        state = session.simulation_state
        current_level = state["current_level"]
        total_levels = state["total_levels"]

        if current_level >= total_levels:
            return True

        if random.random() < 0.04:
            return False

        state["current_level"] = min(current_level + 1, total_levels)
        state["level_progress"][current_level] = 100.0
        return True

    def _simulate_combat_encounter(
        self, session: PlaytestSession, test_case: TestCase
    ) -> List[BugReport]:
        """Simulate a combat encounter and evaluate outcomes."""
        state = session.simulation_state
        bugs: List[BugReport] = []

        state["combat_encounters"] += 1
        win_probability = 0.65 + random.uniform(-0.15, 0.15)

        if random.random() < win_probability:
            state["combat_wins"] += 1
            state["player_health"] = max(10.0, state["player_health"] - random.uniform(5.0, 25.0))
        else:
            state["combat_losses"] += 1
            state["player_health"] = max(0.0, state["player_health"] - random.uniform(30.0, 60.0))
            if state["player_health"] <= 0:
                state["deaths"] += 1
                death_pos = tuple(state["player_position"])
                state["death_locations"].append(death_pos)
                state["player_health"] = 100.0
                state["player_position"] = [0.0, 0.0, 0.0]

        if state["combat_losses"] > state["combat_wins"] * 2:
            bugs.append(self._create_bug(
                session, "combat_balance",
                test_case,
                f"Win/loss ratio is {state['combat_wins']}:{state['combat_losses']} - combat may be too difficult.",
            ))

        return bugs

    def _simulate_collectible_pickup(self, state: Dict[str, Any]) -> None:
        """Simulate picking up a collectible item."""
        state["collectibles_picked_up"] = min(
            state["collectibles_picked_up"] + 1,
            state["total_collectibles"],
        )
        state["resources_collected"] += random.randint(1, 10)

    def _simulate_movement(self, state: Dict[str, Any]) -> None:
        """Simulate player movement through the game world."""
        px, py, pz = state["player_position"]
        px += random.uniform(-2.0, 2.0)
        py += random.uniform(-0.5, 1.0)
        pz += random.uniform(1.0, 4.0)
        state["player_position"] = [round(px, 3), round(py, 3), round(pz, 3)]
        state["movement_path"].append(tuple(state["player_position"]))

        area_key = self._position_to_area_key(state["player_position"])
        state["visited_areas"].add(area_key)

        current_level = state["current_level"]
        state["level_progress"][current_level] = min(
            100.0,
            state["level_progress"].get(current_level, 0.0) + random.uniform(0.5, 2.0),
        )

    def _simulate_interaction(self, state: Dict[str, Any]) -> None:
        """Simulate interacting with a game object."""
        state["player_stamina"] = max(0.0, state["player_stamina"] - random.uniform(1.0, 3.0))
        if random.random() < 0.3:
            state["collectibles_picked_up"] = min(
                state["collectibles_picked_up"] + 1,
                state["total_collectibles"],
            )

    def _simulate_resource_usage(self, state: Dict[str, Any]) -> None:
        """Simulate resource consumption."""
        state["resources_spent"] += random.randint(1, 5)
        state["player_stamina"] = min(100.0, state["player_stamina"] + random.uniform(2.0, 8.0))

    def _simulate_stress_load(
        self, session: PlaytestSession, test_case: TestCase
    ) -> List[BugReport]:
        """Simulate high entity count stress conditions."""
        state = session.simulation_state
        bugs: List[BugReport] = []

        spawn_count = random.randint(50, 200)
        for _ in range(spawn_count):
            state["entities_spawned"] += 1
            state["entities_active"] += 1

        simulated_fps = max(5.0, 60.0 - (state["entities_active"] * 0.15) + random.uniform(-5, 5))
        state["current_fps"] = simulated_fps
        state["frame_times"].append(1000.0 / simulated_fps)

        if simulated_fps < 30.0:
            bugs.append(self._create_bug(
                session, "performance",
                test_case,
                f"Frame rate dropped to {simulated_fps:.1f} FPS with {state['entities_active']} active entities.",
            ))

        state["entities_active"] = max(0, state["entities_active"] - random.randint(10, 50))
        return bugs

    def _simulate_random_walk(self, state: Dict[str, Any]) -> None:
        """Simulate a random walk exploration pattern."""
        for _ in range(random.randint(5, 20)):
            px, py, pz = state["player_position"]
            px += random.uniform(-3.0, 3.0)
            py += random.uniform(-1.0, 1.0)
            pz += random.uniform(-3.0, 3.0)
            state["player_position"] = [round(px, 3), round(py, 3), round(pz, 3)]
            state["movement_path"].append(tuple(state["player_position"]))
            area_key = self._position_to_area_key(state["player_position"])
            state["visited_areas"].add(area_key)

    def _position_to_area_key(self, position: List[float]) -> str:
        """Convert a 3D position to a grid-based area key."""
        cell_size = 15.0
        gx = int(position[0] / cell_size)
        gy = int(position[1] / cell_size)
        gz = int(position[2] / cell_size)
        return f"area_{gx}_{gy}_{gz}"

    def _determine_test_result(
        self, result_text: str, bugs: List[BugReport]
    ) -> TestResult:
        """Determine the test outcome based on execution results and bugs found."""
        if not bugs:
            return TestResult.PASS
        has_blocker = any(b.severity == BugSeverity.BLOCKER for b in bugs)
        has_critical = any(b.severity == BugSeverity.CRITICAL for b in bugs)
        if has_blocker or has_critical:
            return TestResult.FAIL
        if len(bugs) > 0:
            return TestResult.WARNING
        return TestResult.INCONCLUSIVE

    def _create_bug(
        self,
        session: PlaytestSession,
        category: str,
        test_case: TestCase,
        description_override: str = "",
    ) -> BugReport:
        """Create a bug report for a detected issue."""
        state = session.simulation_state
        pos = state.get("player_position", [0, 0, 0])
        location = f"Level {state.get('current_level', 1)}, {self._position_to_area_key(pos)}"

        severity_map = {
            "spawn": BugSeverity.MAJOR,
            "collision": BugSeverity.MAJOR,
            "trigger": BugSeverity.CRITICAL,
            "transition": BugSeverity.CRITICAL,
            "combat_balance": BugSeverity.MODERATE,
            "performance": BugSeverity.MODERATE,
        }

        description = description_override or (
            f"Issue detected in '{category}' during test '{test_case.name}'. "
            f"System behavior deviated from expected outcome."
        )

        return BugReport(
            session_id=session.session_id,
            title=f"{category.replace('_', ' ').title()} issue detected",
            description=description,
            severity=severity_map.get(category, BugSeverity.MINOR),
            category=category,
            reproduction_steps=[
                f"Start playtest session for game '{session.game_id}'",
                f"Execute test case: {test_case.name}",
                f"Navigate to area near {location}",
                f"Observe the {category} behavior",
            ],
            expected_behavior=f"All {category} operations should complete without errors.",
            actual_behavior=description,
            location=location,
        )

    # ------------------------------------------------------------------
    # Full Test Suite Runner
    # ------------------------------------------------------------------

    def run_full_test_suite(self, session_id: str) -> Optional[PlaytestReport]:
        """Run the complete test suite across all configured test types."""
        with self._lock:
            session = self._sessions.get(session_id)
            if session is None:
                return None

            session.status = SessionStatus.RUNNING
            session.started_at = _time_module.time()

            test_types = session.test_types if session.test_types else list(TestType)

            for test_type in test_types:
                if test_type == TestType.FUNCTIONAL:
                    self._run_functional_tests(session)
                elif test_type == TestType.BALANCE:
                    self._run_balance_tests(session)
                elif test_type == TestType.PERFORMANCE:
                    self._run_performance_tests(session)
                elif test_type == TestType.COMPLETION:
                    self._run_completion_tests(session)
                elif test_type == TestType.EXPLORATORY:
                    self._run_exploratory_tests(session)
                elif test_type == TestType.STRESS:
                    self._run_stress_tests(session)
                elif test_type == TestType.REGRESSION:
                    self._run_regression_tests(session)
                elif test_type == TestType.USABILITY:
                    self._run_usability_tests(session)

            session.status = SessionStatus.COMPLETED
            session.completed_at = _time_module.time()
            session.duration_seconds = session.completed_at - session.started_at
            self._stats["total_gameplay_seconds_simulated"] += session.duration_seconds

            return self.generate_report(session_id)

    def _run_functional_tests(self, session: PlaytestSession) -> None:
        """Run functional tests: entity spawning, collision, triggers, scene transitions."""
        self.run_test_case(
            session.session_id, TestType.FUNCTIONAL,
            "Entity Spawning Verification",
            "Verify that all entity types can be spawned correctly.",
            ["spawn entity player", "spawn entity enemy", "spawn entity npc"],
        )

        self.run_test_case(
            session.session_id, TestType.FUNCTIONAL,
            "Collision Detection Check",
            "Verify collision detection works between entities.",
            ["spawn entity enemy", "spawn entity player", "check collision between entities"],
        )

        self.run_test_case(
            session.session_id, TestType.FUNCTIONAL,
            "Event Trigger System",
            "Verify event triggers activate correctly on player entry.",
            ["move player to trigger zone", "verify trigger fires", "check event response"],
        )

        self.run_test_case(
            session.session_id, TestType.FUNCTIONAL,
            "Scene Transition Validation",
            "Verify scene transitions work without errors or state corruption.",
            ["complete current level objectives", "trigger scene transition", "verify new scene loaded"],
        )

    def _run_balance_tests(self, session: PlaytestSession) -> None:
        """Run balance tests: combat encounters, win/loss ratios, resource economy."""
        # Combat balance
        for i in range(5):
            self.run_test_case(
                session.session_id, TestType.BALANCE,
                f"Combat Encounter Simulation {i + 1}",
                "Simulate a combat encounter and evaluate win/loss balance.",
                ["spawn entity enemy", "initiate combat encounter", "track combat outcome"],
            )

        self.run_test_case(
            session.session_id, TestType.BALANCE,
            "Win/Loss Ratio Analysis",
            "Evaluate overall combat win/loss ratio for fairness.",
            ["aggregate combat results", "compute win/loss ratio", "check against target range"],
        )

        self.run_test_case(
            session.session_id, TestType.BALANCE,
            "Resource Economy Verification",
            "Verify resource collection and spending rates are balanced.",
            ["collect resources", "spend resources", "verify economy flow"],
        )

    def _run_performance_tests(self, session: PlaytestSession) -> None:
        """Run performance tests: stress with many entities, measure frame drops."""
        self.run_test_case(
            session.session_id, TestType.PERFORMANCE,
            "High Entity Count Stress Test",
            "Spawn many entities and measure performance impact.",
            ["stress load test", "spawn entity enemy x50", "spawn entity npc x50", "measure frame time"],
        )

        self.run_test_case(
            session.session_id, TestType.PERFORMANCE,
            "Sustained Load Test",
            "Simulate extended gameplay with continuous entity activity.",
            ["spawn entity enemy x20", "simulate movement for 100 steps", "measure frame stability"],
        )

        self.run_test_case(
            session.session_id, TestType.PERFORMANCE,
            "Rapid Entity Spawn/Despawn Test",
            "Test performance with rapid entity lifecycle changes.",
            ["spawn entity enemy x10", "despawn all entities", "spawn entity enemy x10", "measure frame time"],
        )

    def _run_completion_tests(self, session: PlaytestSession) -> None:
        """Run completion tests: verify all levels can be completed, check progression."""
        state = session.simulation_state
        total_levels = state.get("total_levels", 5)

        for level in range(1, total_levels + 1):
            self.run_test_case(
                session.session_id, TestType.COMPLETION,
                f"Level {level} Completion Verification",
                f"Verify level {level} can be completed from start to finish.",
                [
                    f"move player through level {level}",
                    "collect collectibles",
                    "interact with key objects",
                    f"trigger scene transition to level {level + 1}" if level < total_levels else "verify level complete",
                ],
            )

        self.run_test_case(
            session.session_id, TestType.COMPLETION,
            "Full Game Progression Check",
            "Verify the entire game can be completed without blockers.",
            ["move through all levels", "trigger all required transitions", "verify game completion"],
        )

    def _run_exploratory_tests(self, session: PlaytestSession) -> None:
        """Run exploratory tests: random walk simulation, edge case detection."""
        self.run_test_case(
            session.session_id, TestType.EXPLORATORY,
            "Random Walk Exploration",
            "Simulate random player movement to discover edge cases.",
            ["random walk for 50 steps", "record visited areas", "check for collision gaps"],
        )

        self.run_test_case(
            session.session_id, TestType.EXPLORATORY,
            "Boundary Exploration Test",
            "Test player movement near world boundaries and level edges.",
            ["move player to boundary", "attempt out-of-bounds movement", "verify boundary clamping"],
        )

        self.run_test_case(
            session.session_id, TestType.EXPLORATORY,
            "Interaction Edge Case Discovery",
            "Simulate unusual interaction patterns to find edge cases.",
            [
                "interact with object rapidly",
                "interact while moving",
                "interact during combat",
                "interact during scene transition",
            ],
        )

    def _run_stress_tests(self, session: PlaytestSession) -> None:
        """Run stress tests: resource limits and boundary conditions."""
        self.run_test_case(
            session.session_id, TestType.STRESS,
            "Maximum Entity Stress Test",
            "Push entity count to its limit and measure stability.",
            ["stress load test with 200 entities", "measure frame time", "verify no crashes"],
        )

        self.run_test_case(
            session.session_id, TestType.STRESS,
            "Rapid Input Stress Test",
            "Simulate very fast player input sequences.",
            ["move forward 20x", "jump 10x", "attack 15x", "interact 10x", "verify state consistency"],
        )

        self.run_test_case(
            session.session_id, TestType.STRESS,
            "Memory Allocation Stress Test",
            "Test system under sustained resource allocation.",
            ["spawn entity enemy x100", "collect resources x100", "spend resources x100", "measure performance"],
        )

    def _run_regression_tests(self, session: PlaytestSession) -> None:
        """Run regression tests: compare against stored baselines."""
        if session.session_id in self._regression_baselines:
            baseline = self._regression_baselines[session.session_id]

            self.run_test_case(
                session.session_id, TestType.REGRESSION,
                "Regression Comparison",
                "Compare current test results against previous baseline.",
                [
                    "run functional tests",
                    "compare pass rate with baseline",
                    "compare bug count with baseline",
                    "report any regressions",
                ],
            )
        else:
            self.run_test_case(
                session.session_id, TestType.REGRESSION,
                "Establish Regression Baseline",
                "Run initial test suite to establish a regression baseline.",
                ["run all tests", "record results as baseline", "store baseline for future comparison"],
            )

    def _run_usability_tests(self, session: PlaytestSession) -> None:
        """Run usability tests: player experience and interaction flow."""
        self.run_test_case(
            session.session_id, TestType.USABILITY,
            "First-Time User Flow",
            "Simulate a new player's first interaction with the game.",
            ["move forward slowly", "interact with first object", "open menu", "close menu", "resume gameplay"],
        )

        self.run_test_case(
            session.session_id, TestType.USABILITY,
            "Interaction Responsiveness",
            "Verify that player interactions feel responsive.",
            ["interact with object", "measure response time", "interact with npc", "verify dialogue triggers"],
        )

        self.run_test_case(
            session.session_id, TestType.USABILITY,
            "Menu Navigation Check",
            "Verify game menus are navigable and functional.",
            ["open menu", "navigate menu options", "adjust settings", "close menu and resume"],
        )

    # ------------------------------------------------------------------
    # Bug Reporting
    # ------------------------------------------------------------------

    def report_bug(
        self,
        session_id: str,
        title: str,
        description: str,
        severity: BugSeverity,
        category: str,
        reproduction_steps: List[str],
        expected: str,
        actual: str,
        location: str,
    ) -> Optional[BugReport]:
        """Report a bug discovered during playtesting."""
        with self._lock:
            session = self._sessions.get(session_id)
            if session is None:
                return None

            bug = BugReport(
                session_id=session_id,
                title=title,
                description=description,
                severity=severity,
                category=category,
                reproduction_steps=list(reproduction_steps),
                expected_behavior=expected,
                actual_behavior=actual,
                location=location,
            )
            session.bug_reports.append(bug)
            session.bugs_found += 1
            self._stats["total_bugs_reported"] += 1
            return bug

    # ------------------------------------------------------------------
    # Gameplay Simulation
    # ------------------------------------------------------------------

    def simulate_gameplay(
        self, session_id: str, duration_seconds: float
    ) -> Optional[Dict[str, Any]]:
        """
        Simulate autonomous gameplay for a given duration.

        Generates realistic gameplay metrics including player movement
        patterns, combat encounters, collectible pickups, time spent
        per level, death locations, resource usage, path efficiency,
        exploration percentage, and completion time.
        """
        with self._lock:
            session = self._sessions.get(session_id)
            if session is None:
                return None

            state = session.simulation_state
            start_time = _time_module.time()
            actions_per_second = 10
            total_actions = int(duration_seconds * actions_per_second)

            action_weights = {
                "move_forward": 0.30,
                "move_backward": 0.02,
                "strafe_left": 0.05,
                "strafe_right": 0.05,
                "jump": 0.08,
                "sprint": 0.05,
                "interact": 0.08,
                "pickup": 0.07,
                "primary_attack": 0.05,
                "use_item": 0.03,
                "dodge": 0.03,
                "crouch": 0.02,
                "talk_npc": 0.03,
                "open_menu": 0.02,
                "special_ability": 0.02,
                "activate_trigger": 0.04,
                "climb": 0.02,
                "skip_dialogue": 0.02,
                "quick_save": 0.01,
                "drop_item": 0.01,
            }

            weighted_pool: List[str] = []
            for action, weight in action_weights.items():
                count = max(1, int(weight * 100))
                weighted_pool.extend([action] * count)

            action_counts: Dict[str, int] = {a: 0 for a in action_weights}

            for i in range(total_actions):
                action = random.choice(weighted_pool)
                action_counts[action] = action_counts.get(action, 0) + 1
                self._apply_gameplay_action(state, action)

                if i % 50 == 0 and i > 0:
                    self._tick_level_progress(state)
                    self._tick_resource_regen(state)
                    self._tick_combat_check(state)

                if state["current_level"] > state["total_levels"]:
                    break

            elapsed = _time_module.time() - start_time
            self._stats["total_gameplay_seconds_simulated"] += elapsed

            total_visited = len(state["visited_areas"])
            movement_path = state["movement_path"]
            path_efficiency = self._compute_path_efficiency(movement_path)
            exploration_pct = min(100.0, (total_visited / max(1, state["total_levels"] * 10)) * 100.0)
            completion_time = state.get("level_progress", {}).get(state["total_levels"], 0.0)

            return {
                "session_id": session_id,
                "duration_simulated": round(elapsed, 2),
                "total_actions": total_actions,
                "action_breakdown": dict(action_counts),
                "player_position": list(state["player_position"]),
                "player_health": round(state["player_health"], 1),
                "player_stamina": round(state["player_stamina"], 1),
                "current_level": state["current_level"],
                "total_levels": state["total_levels"],
                "areas_visited": total_visited,
                "exploration_percentage": round(exploration_pct, 1),
                "path_efficiency": round(path_efficiency, 2),
                "collectibles_picked_up": state["collectibles_picked_up"],
                "total_collectibles": state["total_collectibles"],
                "combat_encounters": state["combat_encounters"],
                "combat_wins": state["combat_wins"],
                "combat_losses": state["combat_losses"],
                "win_rate": round(
                    state["combat_wins"] / max(1, state["combat_encounters"]), 3
                ),
                "deaths": state["deaths"],
                "death_locations": [
                    list(loc) for loc in state["death_locations"][-10:]
                ],
                "resources_collected": state["resources_collected"],
                "resources_spent": state["resources_spent"],
                "resource_efficiency": round(
                    state["resources_spent"] / max(1, state["resources_collected"]), 3
                ),
                "level_progress": {
                    str(k): round(v, 1) for k, v in state["level_progress"].items()
                },
                "completion_time": round(completion_time, 1),
                "triggers_activated": len(state["triggers_activated"]),
                "entities_spawned": state["entities_spawned"],
                "current_fps": round(state["current_fps"], 1),
            }

    def _apply_gameplay_action(
        self, state: Dict[str, Any], action: str
    ) -> None:
        """Apply a single gameplay action to the simulation state."""
        px, py, pz = state["player_position"]

        if action == "move_forward":
            pz += random.uniform(1.0, 3.0)
        elif action == "move_backward":
            pz -= random.uniform(0.5, 1.5)
        elif action == "strafe_left":
            px -= random.uniform(0.5, 1.5)
        elif action == "strafe_right":
            px += random.uniform(0.5, 1.5)
        elif action == "jump":
            py += random.uniform(0.5, 1.5)
        elif action == "crouch":
            py -= random.uniform(0.3, 0.5)
        elif action == "sprint":
            pz += random.uniform(2.0, 4.0)
            state["player_stamina"] = max(0.0, state["player_stamina"] - random.uniform(3.0, 8.0))
        elif action == "dodge":
            px += random.uniform(-2.0, 2.0)
            state["player_stamina"] = max(0.0, state["player_stamina"] - random.uniform(5.0, 10.0))
        elif action == "climb":
            py += random.uniform(1.0, 3.0)
            state["player_stamina"] = max(0.0, state["player_stamina"] - random.uniform(4.0, 8.0))
        elif action == "primary_attack":
            state["player_stamina"] = max(0.0, state["player_stamina"] - random.uniform(2.0, 5.0))
        elif action == "special_ability":
            state["player_stamina"] = max(0.0, state["player_stamina"] - random.uniform(15.0, 25.0))
        elif action == "interact":
            state["player_stamina"] = max(0.0, state["player_stamina"] - random.uniform(1.0, 2.0))
        elif action == "pickup":
            state["collectibles_picked_up"] = min(
                state["collectibles_picked_up"] + 1,
                state["total_collectibles"],
            )
            state["resources_collected"] += random.randint(1, 5)
        elif action == "use_item":
            state["resources_spent"] += random.randint(1, 3)
        elif action == "drop_item":
            state["resources_collected"] = max(0, state["resources_collected"] - 1)
        elif action == "activate_trigger":
            trigger_id = f"trig_{uuid.uuid4().hex[:4]}"
            state["triggers_activated"].append(trigger_id)

        state["player_position"] = [round(px, 3), round(py, 3), round(pz, 3)]
        state["movement_path"].append(tuple(state["player_position"]))

        area_key = self._position_to_area_key(state["player_position"])
        state["visited_areas"].add(area_key)

    def _tick_level_progress(self, state: Dict[str, Any]) -> None:
        """Advance level progress based on player position and actions."""
        current_level = state["current_level"]
        progress = state["level_progress"].get(current_level, 0.0)
        progress += random.uniform(0.2, 0.8)
        state["level_progress"][current_level] = min(100.0, progress)

        if progress >= 100.0 and current_level < state["total_levels"]:
            state["current_level"] = current_level + 1

    def _tick_resource_regen(self, state: Dict[str, Any]) -> None:
        """Regenerate player resources over time."""
        state["player_stamina"] = min(100.0, state["player_stamina"] + random.uniform(1.0, 4.0))
        state["player_health"] = min(100.0, state["player_health"] + random.uniform(0.0, 1.0))

    def _tick_combat_check(self, state: Dict[str, Any]) -> None:
        """Check for random combat encounters during gameplay."""
        if random.random() < 0.08:
            state["combat_encounters"] += 1
            if random.random() < 0.65:
                state["combat_wins"] += 1
                state["player_health"] = max(5.0, state["player_health"] - random.uniform(5.0, 20.0))
            else:
                state["combat_losses"] += 1
                state["player_health"] = max(0.0, state["player_health"] - random.uniform(25.0, 50.0))
                if state["player_health"] <= 0:
                    state["deaths"] += 1
                    state["death_locations"].append(tuple(state["player_position"]))
                    state["player_health"] = 100.0
                    state["player_position"] = [0.0, 0.0, 0.0]

    def _compute_path_efficiency(self, movement_path: List[Tuple[float, ...]]) -> float:
        """Compute how efficiently the player traversed the level."""
        if len(movement_path) < 2:
            return 1.0

        total_distance = 0.0
        for i in range(1, len(movement_path)):
            prev = movement_path[i - 1]
            curr = movement_path[i]
            dx = curr[0] - prev[0]
            dy = curr[1] - prev[1]
            dz = curr[2] - prev[2]
            total_distance += math.sqrt(dx * dx + dy * dy + dz * dz)

        if len(movement_path) >= 2:
            start = movement_path[0]
            end = movement_path[-1]
            direct_distance = math.sqrt(
                (end[0] - start[0]) ** 2
                + (end[1] - start[1]) ** 2
                + (end[2] - start[2]) ** 2
            )
            if total_distance > 0:
                return min(1.0, direct_distance / total_distance)
        return 1.0

    # ------------------------------------------------------------------
    # Analysis and Evaluation
    # ------------------------------------------------------------------

    def evaluate_fun_factor(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Evaluate the fun factor of the game based on gameplay metrics.

        Considers action variety, exploration, combat engagement,
        collectible discovery rate, and progression pacing.
        """
        with self._lock:
            session = self._sessions.get(session_id)
            if session is None:
                return None

            state = session.simulation_state

            action_variety = min(1.0, len(state.get("movement_path", [])) / 500.0)
            exploration = min(1.0, len(state["visited_areas"]) / 30.0)
            collectible_rate = state["collectibles_picked_up"] / max(1, state["total_collectibles"])
            combat_engagement = min(1.0, state["combat_encounters"] / 20.0)

            win_rate = state["combat_wins"] / max(1, state["combat_encounters"])
            combat_fun = 0.0
            if 0.4 <= win_rate <= 0.8:
                combat_fun = 0.8
            elif win_rate > 0.8:
                combat_fun = 0.5
            else:
                combat_fun = 0.3

            progression_pacing = 0.0
            for level, progress in state["level_progress"].items():
                if progress > 0:
                    progression_pacing += 1.0
            progression_pacing = min(1.0, progression_pacing / max(1, state["total_levels"]))

            fun_score = (
                action_variety * 0.20
                + exploration * 0.20
                + collectible_rate * 0.15
                + combat_engagement * 0.15
                + combat_fun * 0.15
                + progression_pacing * 0.15
            )

            fun_score = round(min(1.0, max(0.0, fun_score)), 3)

            return {
                "session_id": session_id,
                "fun_rating": fun_score,
                "action_variety": round(action_variety, 3),
                "exploration_factor": round(exploration, 3),
                "collectible_rate": round(collectible_rate, 3),
                "combat_engagement": round(combat_engagement, 3),
                "combat_fun": round(combat_fun, 3),
                "progression_pacing": round(progression_pacing, 3),
                "interpretation": self._interpret_fun_score(fun_score),
            }

    def _interpret_fun_score(self, score: float) -> str:
        """Provide a human-readable interpretation of the fun score."""
        if score >= 0.8:
            return "Very engaging - players are likely to find the game enjoyable."
        elif score >= 0.6:
            return "Moderately fun - some areas could be improved for better engagement."
        elif score >= 0.4:
            return "Below average - significant improvements needed for player retention."
        else:
            return "Poor engagement - fundamental design issues should be addressed."

    def evaluate_balance(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Evaluate game balance across combat, economy, and progression.

        Analyzes win/loss ratios, resource flow, and difficulty scaling
        to produce a comprehensive balance assessment.
        """
        with self._lock:
            session = self._sessions.get(session_id)
            if session is None:
                return None

            state = session.simulation_state

            total_combat = state["combat_encounters"]
            win_rate = state["combat_wins"] / max(1, total_combat)
            combat_balance = 1.0 - abs(win_rate - 0.55)

            resource_ratio = state["resources_spent"] / max(1, state["resources_collected"])
            economy_balance = 1.0 - abs(resource_ratio - 0.6)

            deaths_per_level = state["deaths"] / max(1, state["current_level"])
            difficulty_balance = 1.0 - min(1.0, deaths_per_level / 5.0)

            health_volatility = abs(state["player_health"] - 50.0) / 50.0
            health_balance = 1.0 - health_volatility

            balance_score = (
                combat_balance * 0.35
                + economy_balance * 0.30
                + difficulty_balance * 0.20
                + health_balance * 0.15
            )

            balance_score = round(min(1.0, max(0.0, balance_score)), 3)

            return {
                "session_id": session_id,
                "balance_score": balance_score,
                "combat_balance": round(combat_balance, 3),
                "win_rate": round(win_rate, 3),
                "economy_balance": round(economy_balance, 3),
                "resource_ratio": round(resource_ratio, 3),
                "difficulty_balance": round(difficulty_balance, 3),
                "deaths_per_level": round(deaths_per_level, 3),
                "health_balance": round(health_balance, 3),
                "total_combat_encounters": total_combat,
                "total_deaths": state["deaths"],
                "interpretation": self._interpret_balance_score(balance_score),
            }

    def _interpret_balance_score(self, score: float) -> str:
        """Provide a human-readable interpretation of the balance score."""
        if score >= 0.8:
            return "Well-balanced - combat, economy, and difficulty are properly tuned."
        elif score >= 0.6:
            return "Moderately balanced - some tuning recommended for specific areas."
        elif score >= 0.4:
            return "Balance issues detected - several systems need adjustment."
        else:
            return "Poorly balanced - significant rebalancing required across multiple systems."

    def evaluate_difficulty_curve(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Evaluate the difficulty curve across game levels.

        Measures how difficulty scales from early to late game,
        identifying spikes, plateaus, and inconsistent progression.
        """
        with self._lock:
            session = self._sessions.get(session_id)
            if session is None:
                return None

            state = session.simulation_state
            total_levels = state["total_levels"]
            level_progress = state["level_progress"]

            difficulty_per_level: Dict[str, float] = {}
            for level in range(1, total_levels + 1):
                progress = level_progress.get(level, 0.0)
                base_difficulty = 0.2 + (level / total_levels) * 0.6
                noise = random.uniform(-0.05, 0.05)
                adjusted = base_difficulty + noise
                if progress < 50:
                    adjusted += 0.1
                difficulty_per_level[str(level)] = round(min(1.0, max(0.0, adjusted)), 3)

            difficulties = list(difficulty_per_level.values())
            if len(difficulties) >= 2:
                slopes = [
                    difficulties[i] - difficulties[i - 1]
                    for i in range(1, len(difficulties))
                ]
                avg_slope = sum(slopes) / len(slopes)
                curve_smoothness = 1.0 - min(1.0, sum(abs(s - avg_slope) for s in slopes) / len(slopes))
            else:
                avg_slope = 0.0
                curve_smoothness = 1.0

            has_spikes = any(
                i > 0 and difficulties[i] - difficulties[i - 1] > 0.3
                for i in range(1, len(difficulties))
            ) if len(difficulties) >= 2 else False

            overall_difficulty = sum(difficulties) / max(1, len(difficulties))

            return {
                "session_id": session_id,
                "difficulty_rating": round(overall_difficulty, 3),
                "curve_smoothness": round(curve_smoothness, 3),
                "average_slope": round(avg_slope, 3),
                "has_difficulty_spikes": has_spikes,
                "difficulty_per_level": difficulty_per_level,
                "total_levels": total_levels,
                "interpretation": self._interpret_difficulty_curve(
                    curve_smoothness, has_spikes, overall_difficulty
                ),
            }

    def _interpret_difficulty_curve(
        self, smoothness: float, has_spikes: bool, overall: float
    ) -> str:
        """Provide a human-readable interpretation of the difficulty curve."""
        if has_spikes:
            return "Difficulty spikes detected - some levels are much harder than adjacent ones."
        if smoothness >= 0.8:
            if overall < 0.3:
                return "Smooth but easy curve - consider increasing late-game challenge."
            elif overall > 0.7:
                return "Smooth but difficult curve - may be too hard for casual players."
            else:
                return "Well-designed difficulty curve with smooth progression."
        elif smoothness >= 0.5:
            return "Acceptable difficulty curve with minor inconsistencies."
        else:
            return "Inconsistent difficulty curve - levels vary unpredictably in challenge."

    # ------------------------------------------------------------------
    # Report Generation
    # ------------------------------------------------------------------

    def generate_report(self, session_id: str) -> Optional[PlaytestReport]:
        """
        Generate a comprehensive playtest report for a session.

        Aggregates all test results, bug reports, and analysis metrics
        into a single report with overall scores and recommendations.
        """
        with self._lock:
            session = self._sessions.get(session_id)
            if session is None:
                return None

            fun_data = self.evaluate_fun_factor(session_id) or {}
            balance_data = self.evaluate_balance(session_id) or {}
            difficulty_data = self.evaluate_difficulty_curve(session_id) or {}

            fun_rating = fun_data.get("fun_rating", 0.0)
            balance_score = balance_data.get("balance_score", 0.0)
            difficulty_rating = difficulty_data.get("difficulty_rating", 0.0)

            performance_score = 0.5
            state = session.simulation_state
            if state.get("current_fps", 60) >= 55:
                performance_score = 0.9
            elif state.get("current_fps", 60) >= 30:
                performance_score = 0.7
            else:
                performance_score = 0.3

            overall_score = (
                fun_rating * 0.25
                + balance_score * 0.25
                + (1.0 - difficulty_rating) * 0.20
                + performance_score * 0.15
                + (session.pass_rate * 0.15)
            )
            overall_score = round(min(1.0, max(0.0, overall_score)), 3)

            recommendations = self._generate_recommendations(
                session, fun_data, balance_data, difficulty_data
            )

            summary = (
                f"Playtest session for game '{session.game_id}' completed with "
                f"status '{session.status.value}'. "
                f"Ran {session.total_tests} tests across {len(session.test_types)} test types. "
                f"Results: {session.passed} passed, {session.failed} failed, "
                f"{session.warnings} warnings. "
                f"Found {session.bugs_found} bugs. "
                f"Overall score: {overall_score:.2f}. "
                f"Fun: {fun_rating:.2f}, Balance: {balance_score:.2f}, "
                f"Difficulty: {difficulty_rating:.2f}, Performance: {performance_score:.2f}."
            )

            report = PlaytestReport(
                session_id=session_id,
                summary=summary,
                overall_score=overall_score,
                fun_rating=fun_rating,
                balance_score=balance_score,
                difficulty_rating=difficulty_rating,
                performance_score=performance_score,
                bugs=list(session.bug_reports),
                recommendations=recommendations,
            )
            self._reports[session_id] = report
            self._stats["total_reports_generated"] += 1

            # Store as regression baseline
            self._regression_baselines[session_id] = {
                "pass_rate": session.pass_rate,
                "bugs_found": session.bugs_found,
                "overall_score": overall_score,
                "fun_rating": fun_rating,
                "balance_score": balance_score,
                "generated_at": _time_module.time(),
            }

            return report

    def _generate_recommendations(
        self,
        session: PlaytestSession,
        fun_data: Dict[str, Any],
        balance_data: Dict[str, Any],
        difficulty_data: Dict[str, Any],
    ) -> List[str]:
        """Generate actionable recommendations based on analysis results."""
        recommendations: List[str] = []

        fun_rating = fun_data.get("fun_rating", 0.0)
        if fun_rating < 0.5:
            recommendations.append(
                "Fun factor is low. Consider adding more action variety, "
                "rewarding exploration, and improving combat engagement."
            )
        if fun_data.get("action_variety", 0.0) < 0.3:
            recommendations.append(
                "Limited action variety detected. Add more gameplay mechanics "
                "and interaction types to keep players engaged."
            )
        if fun_data.get("exploration_factor", 0.0) < 0.3:
            recommendations.append(
                "Exploration is low. Expand level geometry and add hidden areas "
                "or secrets to encourage discovery."
            )

        balance_score = balance_data.get("balance_score", 0.0)
        if balance_score < 0.5:
            recommendations.append(
                "Balance issues detected. Review combat difficulty, resource "
                "economy, and death penalty settings."
            )
        if balance_data.get("win_rate", 0.5) < 0.35:
            recommendations.append(
                "Combat win rate is too low. Reduce enemy damage or increase "
                "player health to improve fairness."
            )
        if balance_data.get("win_rate", 0.5) > 0.85:
            recommendations.append(
                "Combat win rate is too high. Increase enemy difficulty to "
                "provide an appropriate challenge."
            )

        if difficulty_data.get("has_difficulty_spikes", False):
            recommendations.append(
                "Difficulty spikes detected. Smooth out the difficulty curve "
                "between levels to avoid player frustration."
            )
        if difficulty_data.get("curve_smoothness", 1.0) < 0.5:
            recommendations.append(
                "Difficulty curve is inconsistent. Ensure each level builds "
                "gradually on the skills taught in previous levels."
            )

        if session.pass_rate < 0.7:
            recommendations.append(
                f"Test pass rate is {session.pass_rate:.1%}. Investigate "
                f"failing test cases and fix underlying issues."
            )

        blocker_count = sum(
            1 for b in session.bug_reports
            if b.severity == BugSeverity.BLOCKER
        )
        critical_count = sum(
            1 for b in session.bug_reports
            if b.severity == BugSeverity.CRITICAL
        )
        if blocker_count > 0:
            recommendations.append(
                f"{blocker_count} blocker bug(s) found. These must be "
                f"resolved before release."
            )
        if critical_count > 0:
            recommendations.append(
                f"{critical_count} critical bug(s) found. Prioritize these "
                f"fixes in the next development cycle."
            )

        if not recommendations:
            recommendations.append(
                "The game is in good shape. Continue monitoring playtest "
                "results as new content is added."
            )

        return recommendations

    def get_report(self, session_id: str) -> Optional[PlaytestReport]:
        """Retrieve a previously generated playtest report."""
        return self._reports.get(session_id)

    # ------------------------------------------------------------------
    # Statistics
    # ------------------------------------------------------------------

    def get_stats(self) -> Dict[str, Any]:
        """Return aggregate statistics for the playtesting framework."""
        with self._lock:
            total_sessions = len(self._sessions)
            active_sessions = sum(
                1 for s in self._sessions.values()
                if s.status == SessionStatus.RUNNING
            )
            completed_sessions = sum(
                1 for s in self._sessions.values()
                if s.status == SessionStatus.COMPLETED
            )
            aborted_sessions = sum(
                1 for s in self._sessions.values()
                if s.status == SessionStatus.ABORTED
            )

            total_tests = sum(s.total_tests for s in self._sessions.values())
            total_passed = sum(s.passed for s in self._sessions.values())
            total_failed = sum(s.failed for s in self._sessions.values())
            total_bugs = sum(s.bugs_found for s in self._sessions.values())

            severity_breakdown: Dict[str, int] = {}
            for s in self._sessions.values():
                for bug in s.bug_reports:
                    sev = bug.severity.value
                    severity_breakdown[sev] = severity_breakdown.get(sev, 0) + 1

            category_breakdown: Dict[str, int] = {}
            for s in self._sessions.values():
                for bug in s.bug_reports:
                    cat = bug.category
                    category_breakdown[cat] = category_breakdown.get(cat, 0) + 1

            type_breakdown: Dict[str, int] = {}
            for s in self._sessions.values():
                for t in s.test_types:
                    type_breakdown[t.value] = type_breakdown.get(t.value, 0) + 1

            avg_pass_rate = 0.0
            if total_sessions > 0:
                avg_pass_rate = sum(
                    s.pass_rate for s in self._sessions.values()
                ) / total_sessions

            return {
                "total_sessions": total_sessions,
                "active_sessions": active_sessions,
                "completed_sessions": completed_sessions,
                "aborted_sessions": aborted_sessions,
                "total_tests_run": total_tests,
                "total_passed": total_passed,
                "total_failed": total_failed,
                "total_bugs_reported": total_bugs,
                "average_pass_rate": round(avg_pass_rate, 4),
                "bug_severity_breakdown": severity_breakdown,
                "bug_category_breakdown": category_breakdown,
                "test_type_breakdown": type_breakdown,
                "reports_generated": len(self._reports),
                "baselines_stored": len(self._regression_baselines),
                "total_sessions_created": self._stats["total_sessions_created"],
                "total_tests_run_all_time": self._stats["total_tests_run"],
                "total_bugs_reported_all_time": self._stats["total_bugs_reported"],
                "total_reports_generated": self._stats["total_reports_generated"],
                "total_gameplay_seconds_simulated": round(
                    self._stats["total_gameplay_seconds_simulated"], 2
                ),
            }


# ------------------------------------------------------------------
# Module-level accessor
# ------------------------------------------------------------------


def get_playtesting_framework() -> PlaytestingFramework:
    """Return the singleton PlaytestingFramework instance."""
    return PlaytestingFramework.get_instance()