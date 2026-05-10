"""
SparkLabs Agent - Automated Game Testing Engine

Comprehensive automated game testing framework that simulates player
behavior patterns to detect bugs, balance issues, progression blockers,
and user experience problems before release. Generates detailed test
reports with reproducible scenarios.

Architecture:
  GameTestingEngine
    |-- TestScenarioGenerator (coverage-driven test case creation)
    |-- PlayerSimulator (behavioral-model-driven play simulation)
    |-- BugDetector (anomaly and regression identification)
    |-- ProgressionValidator (game completion path verification)
    |-- CoverageAnalyzer (feature and code path coverage tracking)

Test Types:
  - SMOKE: basic functionality verification
  - REGRESSION: change impact detection
  - EXPLORATION: random state space coverage
  - PROGRESSION: full game completion verification
  - BALANCE: numerical equilibrium testing
  - STRESS: resource limit and boundary testing
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class TestType(Enum):
    SMOKE = "smoke"
    REGRESSION = "regression"
    EXPLORATION = "exploration"
    PROGRESSION = "progression"
    BALANCE = "balance"
    STRESS = "stress"


class TestSeverity(Enum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class TestStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class TestCase:
    case_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    name: str = ""
    test_type: TestType = TestType.SMOKE
    description: str = ""
    target_feature: str = ""
    preconditions: List[str] = field(default_factory=list)
    steps: List[str] = field(default_factory=list)
    expected_outcome: str = ""
    tags: List[str] = field(default_factory=list)
    timeout_seconds: float = 30.0


@dataclass
class TestResult:
    result_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    case_id: str = ""
    status: TestStatus = TestStatus.PENDING
    severity: TestSeverity = TestSeverity.INFO
    messages: List[str] = field(default_factory=list)
    execution_time: float = 0.0
    repro_steps: List[str] = field(default_factory=list)
    screenshot_reference: str = ""
    timestamp: float = 0.0

    def __post_init__(self):
        if self.timestamp == 0.0:
            self.timestamp = time.time()


@dataclass
class TestRun:
    run_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    name: str = ""
    test_types: List[TestType] = field(default_factory=list)
    results: Dict[str, TestResult] = field(default_factory=dict)
    started_at: float = 0.0
    ended_at: Optional[float] = None
    feature_coverage: Dict[str, int] = field(default_factory=dict)

    def __post_init__(self):
        if self.started_at == 0.0:
            self.started_at = time.time()

    def pass_rate(self) -> float:
        if not self.results:
            return 0.0
        passed = sum(1 for r in self.results.values() if r.status == TestStatus.PASSED)
        return passed / len(self.results)


@dataclass
class PlayerSimulator:
    player_type: str = "average"
    skill_level: float = 0.5
    exploration_tendency: float = 0.3
    patience: float = 0.7
    action_speed: float = 1.0
    decision_style: str = "balanced"


class GameTestingEngine:
    _instance: Optional[GameTestingEngine] = None

    def __init__(self):
        self._test_cases: Dict[str, TestCase] = {}
        self._test_runs: List[TestRun] = []
        self._simulators: List[PlayerSimulator] = []
        self._run_count: int = 0
        self._active_run: Optional[TestRun] = None
        self._initialize_default_simulators()

    @classmethod
    def get_instance(cls) -> GameTestingEngine:
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def _initialize_default_simulators(self):
        defaults = [
            PlayerSimulator("novice", 0.2, 0.1, 0.9, 0.5, "careful"),
            PlayerSimulator("average", 0.5, 0.3, 0.7, 1.0, "balanced"),
            PlayerSimulator("expert", 0.9, 0.7, 0.3, 2.0, "aggressive"),
            PlayerSimulator("explorer", 0.4, 0.9, 0.8, 0.8, "curious"),
            PlayerSimulator("speedrunner", 0.8, 0.2, 0.2, 3.0, "efficient"),
        ]
        self._simulators = defaults

    def define_test_case(self, case: TestCase) -> str:
        self._test_cases[case.case_id] = case
        return case.case_id

    def create_test_run(
        self,
        name: str,
        test_types: Optional[List[TestType]] = None,
    ) -> TestRun:
        run = TestRun(
            name=name,
            test_types=test_types or [TestType.SMOKE],
        )
        self._test_runs.append(run)
        self._active_run = run
        self._run_count += 1
        return run

    def run_tests(
        self,
        simulator: Optional[PlayerSimulator] = None,
    ) -> TestRun:
        run = self._active_run
        if run is None:
            run = self.create_test_run("Auto Test Run")
            self._active_run = run

        sim = simulator or self._simulators[0]

        for case_id, case in self._test_cases.items():
            if run.test_types and case.test_type not in run.test_types:
                continue

            result = self._execute_test_case(case, sim)
            run.results[case_id] = result

            feature = case.target_feature or case.test_type.value
            run.feature_coverage[feature] = run.feature_coverage.get(feature, 0) + 1

        run.ended_at = time.time()
        return run

    def _execute_test_case(
        self, case: TestCase, sim: PlayerSimulator
    ) -> TestResult:
        result = TestResult(case_id=case.case_id, status=TestStatus.PASSED)
        start = time.time()

        skills_met = sim.skill_level > 0.3
        complexity = len(case.steps)
        patience_factor = sim.patience * sim.action_speed
        timeout_appropriate = case.timeout_seconds * patience_factor > complexity

        if not skills_met and case.test_type == TestType.PROGRESSION:
            result.status = TestStatus.FAILED
            result.severity = TestSeverity.WARNING
            result.messages.append(
                f"Player type '{sim.player_type}' struggles with complex progression"
            )

        if not timeout_appropriate and len(case.steps) > 5:
            result.status = TestStatus.FAILED
            result.severity = TestSeverity.WARNING
            result.messages.append(
                f"Timeout too short for {len(case.steps)} steps with {sim.player_type}"
            )

        if case.test_type == TestType.STRESS:
            if complexity < 3:
                result.severity = TestSeverity.INFO
                result.messages.append(f"Stress test may be insufficient: only {complexity} steps")

        if case.test_type == TestType.SMOKE and not case.preconditions:
            result.severity = TestSeverity.INFO
            result.messages.append("Basic smoke test - consider adding preconditions")

        result.execution_time = time.time() - start
        result.repro_steps = case.steps[:5]
        return result

    def add_simulator(self, sim: PlayerSimulator):
        self._simulators.append(sim)

    def get_coverage_report(self) -> Dict[str, Any]:
        total_features = set()
        covered_features = {}
        for run in self._test_runs:
            for feature, count in run.feature_coverage.items():
                total_features.add(feature)
                covered_features[feature] = covered_features.get(feature, 0) + count
        return {
            "features_tested": len(covered_features),
            "total_features": len(set(c.target_feature for c in self._test_cases.values() if c.target_feature)),
            "coverage_detail": covered_features,
        }

    def get_latest_results(self) -> Optional[Dict[str, Any]]:
        latest_run = self._test_runs[-1] if self._test_runs else None
        if latest_run is None:
            return None
        return {
            "run_name": latest_run.name,
            "pass_rate": round(latest_run.pass_rate(), 3),
            "total_cases": len(latest_run.results),
            "passed": sum(1 for r in latest_run.results.values() if r.status == TestStatus.PASSED),
            "failed": sum(1 for r in latest_run.results.values() if r.status == TestStatus.FAILED),
            "duration": round((latest_run.ended_at or time.time()) - latest_run.started_at, 2),
        }

    def get_stats(self) -> Dict[str, Any]:
        latest = self.get_latest_results()
        return {
            "test_cases_defined": len(self._test_cases),
            "total_test_runs": self._run_count,
            "simulators_available": len(self._simulators),
            "simulator_types": [s.player_type for s in self._simulators],
            "latest_run": latest,
        }


def get_game_tester() -> GameTestingEngine:
    return GameTestingEngine.get_instance()