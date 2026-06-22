"""
SparkLabs Agent - Autonomous Tester Engine

AI agent that autonomously explores game states, discovers bugs, tests
edge cases, and generates comprehensive test reports. The engine
supports multiple testing strategies, captures game state snapshots,
computes test coverage metrics, and replays sessions for reproducible
bug analysis.

Architecture:
  AutonomousTesterEngine (Singleton)
    |-- TestCase (strategy, preconditions, steps, expected result)
    |-- BugReport (severity, category, reproduction steps, game state)
    |-- TestSession (strategy, test cases, bugs, coverage, duration)
    |-- GameStateSnapshot (entities, variables, position, timestamp)

Core Capabilities:
  - Create test sessions with configurable testing strategies
  - Add test cases with preconditions, steps, and expected results
  - Run autonomous exploration of game states
  - Record bugs with severity, category, and reproduction steps
  - Capture game state snapshots for reproducibility
  - Generate comprehensive test reports with coverage metrics
  - Compute coverage across entities, states, and code paths
  - Replay test sessions for reproducible debugging
"""

from __future__ import annotations

import math
import threading
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class TestStrategy(Enum):
    """Strategies for autonomous game testing."""
    RANDOM_WALK = "random_walk"
    GOAL_ORIENTED = "goal_oriented"
    BOUNDARY = "boundary"
    REGRESSION = "regression"
    STRESS = "stress"
    MONKEY = "monkey"


class BugSeverity(Enum):
    """Severity levels for discovered bugs."""
    CRITICAL = "critical"
    MAJOR = "major"
    MINOR = "minor"
    COSMETIC = "cosmetic"
    SUGGESTION = "suggestion"


class BugCategory(Enum):
    """Categories of game bugs."""
    CRASH = "crash"
    LOGIC = "logic"
    VISUAL = "visual"
    AUDIO = "audio"
    PERFORMANCE = "performance"
    BALANCE = "balance"
    UI = "ui"
    NETWORK = "network"


class TestPhase(Enum):
    """Phases of a test session."""
    EXPLORATION = "exploration"
    EXECUTION = "execution"
    VERIFICATION = "verification"
    REPORTING = "reporting"


# ---------------------------------------------------------------------------
# Severity Weight Map
# ---------------------------------------------------------------------------

_SEVERITY_WEIGHT: Dict[BugSeverity, float] = {
    BugSeverity.CRITICAL: 10.0,
    BugSeverity.MAJOR: 5.0,
    BugSeverity.MINOR: 2.0,
    BugSeverity.COSMETIC: 1.0,
    BugSeverity.SUGGESTION: 0.5,
}


# ---------------------------------------------------------------------------
# Data Classes
# ---------------------------------------------------------------------------

@dataclass
class TestCase:
    """A single test case with strategy, conditions, and expected outcome.

    Test cases define the preconditions that must be met before
    execution, the steps to perform, the expected result, and a
    timeout for automatic failure detection.
    """
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = ""
    strategy: TestStrategy = TestStrategy.RANDOM_WALK
    preconditions: List[str] = field(default_factory=list)
    steps: List[Dict[str, Any]] = field(default_factory=list)
    expected_result: str = ""
    timeout: float = 30.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "strategy": self.strategy.value,
            "preconditions": self.preconditions,
            "precondition_count": len(self.preconditions),
            "steps": self.steps,
            "step_count": len(self.steps),
            "expected_result": self.expected_result,
            "timeout": self.timeout,
            "metadata": self.metadata,
            "created_at": self.created_at,
        }

    def add_step(self, action: str, target: str = "", params: Optional[Dict[str, Any]] = None) -> None:
        self.steps.append({
            "action": action,
            "target": target,
            "params": params or {},
            "order": len(self.steps),
        })

    def add_precondition(self, condition: str) -> None:
        if condition not in self.preconditions:
            self.preconditions.append(condition)


@dataclass
class BugReport:
    """A discovered bug with full reproduction details.

    Contains the bug title, severity, category, description,
    step-by-step reproduction instructions, the game state at
    discovery, and optional screenshot references.
    """
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    title: str = ""
    severity: BugSeverity = BugSeverity.MINOR
    category: BugCategory = BugCategory.LOGIC
    description: str = ""
    reproduction_steps: List[str] = field(default_factory=list)
    game_state: Dict[str, Any] = field(default_factory=dict)
    screenshot_ref: str = ""
    discovered_by: str = ""
    discovered_at: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "severity": self.severity.value,
            "severity_weight": _SEVERITY_WEIGHT.get(self.severity, 1.0),
            "category": self.category.value,
            "description": self.description[:300],
            "reproduction_steps": self.reproduction_steps,
            "step_count": len(self.reproduction_steps),
            "game_state": self.game_state,
            "screenshot_ref": self.screenshot_ref,
            "discovered_by": self.discovered_by,
            "discovered_at": self.discovered_at,
            "metadata": self.metadata,
        }

    def add_reproduction_step(self, step: str) -> None:
        self.reproduction_steps.append(step)

    def get_severity_weight(self) -> float:
        return _SEVERITY_WEIGHT.get(self.severity, 1.0)


@dataclass
class TestSession:
    """A complete test session with test cases, bugs, and coverage data.

    Tracks the testing strategy, all test cases executed, bugs found,
    states explored, coverage metrics, and session duration for
    comprehensive reporting.
    """
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    game_id: str = ""
    strategy: TestStrategy = TestStrategy.RANDOM_WALK
    test_cases: List[str] = field(default_factory=list)
    bugs_found: List[str] = field(default_factory=list)
    states_explored: List[str] = field(default_factory=list)
    coverage: Dict[str, Any] = field(default_factory=dict)
    duration: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)
    started_at: Optional[float] = None
    completed_at: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "game_id": self.game_id,
            "strategy": self.strategy.value,
            "test_case_count": len(self.test_cases),
            "bug_count": len(self.bugs_found),
            "states_explored": len(self.states_explored),
            "coverage": self.coverage,
            "duration": round(self.duration, 2),
            "metadata": self.metadata,
            "created_at": self.created_at,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
        }

    def get_bug_rate(self) -> float:
        if not self.test_cases:
            return 0.0
        return len(self.bugs_found) / len(self.test_cases)

    def get_coverage_percentage(self) -> float:
        covered = self.coverage.get("covered_entities", 0)
        total = self.coverage.get("total_entities", 1)
        return min(1.0, covered / total) if total > 0 else 0.0


@dataclass
class GameStateSnapshot:
    """A point-in-time snapshot of the game state during testing.

    Captures entities, variables, position, and timestamp for
    reproducible bug analysis and session replay.
    """
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    session_id: str = ""
    entities: Dict[str, Any] = field(default_factory=dict)
    variables: Dict[str, Any] = field(default_factory=dict)
    position: Dict[str, float] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "session_id": self.session_id,
            "entity_count": len(self.entities),
            "entities": self.entities,
            "variables": self.variables,
            "variable_count": len(self.variables),
            "position": self.position,
            "timestamp": self.timestamp,
            "metadata": self.metadata,
        }

    def get_entity(self, entity_id: str) -> Optional[Dict[str, Any]]:
        return self.entities.get(entity_id)


# ---------------------------------------------------------------------------
# AutonomousTesterEngine
# ---------------------------------------------------------------------------

class AutonomousTesterEngine:
    """Thread-safe singleton engine for autonomous game testing.

    Manages test sessions, test cases, bug reports, and game state
    snapshots. Supports multiple testing strategies, autonomous
    exploration, coverage computation, and session replay for
    reproducible debugging.
    """

    _instance: Optional["AutonomousTesterEngine"] = None
    _lock = threading.RLock()

    _MAX_SESSIONS: int = 200
    _MAX_TEST_CASES: int = 5000
    _MAX_BUG_REPORTS: int = 10000
    _MAX_STATE_SNAPSHOTS: int = 50000
    _MAX_STATES_PER_SESSION: int = 1000
    _DEFAULT_TIMEOUT: float = 30.0

    def __init__(self) -> None:
        self._sessions: Dict[str, TestSession] = {}
        self._test_cases: Dict[str, TestCase] = {}
        self._test_cases_by_session: Dict[str, List[str]] = {}
        self._bug_reports: Dict[str, BugReport] = {}
        self._bugs_by_session: Dict[str, List[str]] = {}
        self._state_snapshots: Dict[str, GameStateSnapshot] = {}
        self._snapshots_by_session: Dict[str, List[str]] = {}
        self._total_sessions_created: int = 0
        self._total_test_cases_created: int = 0
        self._total_bugs_recorded: int = 0
        self._total_states_captured: int = 0
        self._total_reports_generated: int = 0
        self._total_explorations_run: int = 0

    @classmethod
    def get_instance(cls) -> "AutonomousTesterEngine":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    # ------------------------------------------------------------------
    # Session Management
    # ------------------------------------------------------------------

    def create_session(
        self,
        game_id: str = "",
        strategy: TestStrategy = TestStrategy.RANDOM_WALK,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> TestSession:
        with self._lock:
            self._enforce_max_sessions()

            session = TestSession(
                game_id=game_id,
                strategy=strategy,
                metadata=metadata or {},
            )
            self._sessions[session.id] = session
            self._test_cases_by_session[session.id] = []
            self._bugs_by_session[session.id] = []
            self._snapshots_by_session[session.id] = []
            self._total_sessions_created += 1
            return session

    def get_session(self, session_id: str) -> Optional[TestSession]:
        with self._lock:
            return self._sessions.get(session_id)

    def list_sessions(self, game_id: Optional[str] = None) -> List[Dict[str, Any]]:
        with self._lock:
            results = list(self._sessions.values())
            if game_id is not None:
                results = [s for s in results if s.game_id == game_id]
            return [s.to_dict() for s in results]

    # ------------------------------------------------------------------
    # Test Cases
    # ------------------------------------------------------------------

    def add_test_case(
        self,
        session_id: str,
        name: str = "",
        strategy: Optional[TestStrategy] = None,
        preconditions: Optional[List[str]] = None,
        steps: Optional[List[Dict[str, Any]]] = None,
        expected_result: str = "",
        timeout: float = 30.0,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Optional[TestCase]:
        with self._lock:
            session = self._sessions.get(session_id)
            if session is None:
                return None
            self._enforce_max_test_cases()

            tc = TestCase(
                name=name or f"Test Case {self._total_test_cases_created + 1}",
                strategy=strategy or session.strategy,
                preconditions=list(preconditions) if preconditions else [],
                steps=list(steps) if steps else [],
                expected_result=expected_result,
                timeout=timeout,
                metadata=metadata or {},
            )
            self._test_cases[tc.id] = tc
            self._test_cases_by_session[session_id].append(tc.id)
            session.test_cases.append(tc.id)
            self._total_test_cases_created += 1
            return tc

    def get_test_case(self, test_case_id: str) -> Optional[TestCase]:
        with self._lock:
            return self._test_cases.get(test_case_id)

    def get_session_test_cases(self, session_id: str) -> List[TestCase]:
        with self._lock:
            tc_ids = self._test_cases_by_session.get(session_id, [])
            return [self._test_cases[tid] for tid in tc_ids if tid in self._test_cases]

    # ------------------------------------------------------------------
    # Exploration
    # ------------------------------------------------------------------

    def run_exploration(
        self,
        session_id: str,
        exploration_steps: int = 100,
        state_provider: Optional[Callable[[], Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        with self._lock:
            self._total_explorations_run += 1

            session = self._sessions.get(session_id)
            if session is None:
                return {"error": "Session not found"}

            session.started_at = time.time()
            start_time = session.started_at

            states_explored = 0
            bugs_found = 0
            entities_seen: set = set()
            variables_seen: set = set()

            for step in range(exploration_steps):
                snapshot = self._generate_exploration_snapshot(
                    session_id, step, state_provider
                )
                if snapshot is not None:
                    self._state_snapshots[snapshot.id] = snapshot
                    self._snapshots_by_session[session_id].append(snapshot.id)
                    session.states_explored.append(snapshot.id)
                    states_explored += 1

                    for entity_key in snapshot.entities:
                        entities_seen.add(entity_key)
                    for var_key in snapshot.variables:
                        variables_seen.add(var_key)

                    anomalies = self._detect_anomalies(snapshot, session)
                    for anomaly in anomalies:
                        self.record_bug(
                            session_id=session_id,
                            title=anomaly.get("title", "Anomaly Detected"),
                            severity=anomaly.get("severity", BugSeverity.MINOR),
                            category=anomaly.get("category", BugCategory.LOGIC),
                            description=anomaly.get("description", ""),
                            reproduction_steps=anomaly.get("steps", []),
                            game_state=snapshot.to_dict(),
                        )
                        bugs_found += 1

            session.completed_at = time.time()
            session.duration = session.completed_at - start_time

            session.coverage = {
                "covered_entities": len(entities_seen),
                "total_entities": len(entities_seen),
                "covered_variables": len(variables_seen),
                "total_variables": len(variables_seen),
                "exploration_steps": exploration_steps,
                "states_explored": states_explored,
                "coverage_percentage": 1.0 if states_explored > 0 else 0.0,
            }

            return {
                "session_id": session_id,
                "strategy": session.strategy.value,
                "states_explored": states_explored,
                "bugs_found": bugs_found,
                "entities_covered": len(entities_seen),
                "variables_covered": len(variables_seen),
                "duration_seconds": round(session.duration, 2),
                "exploration_steps": exploration_steps,
            }

    # ------------------------------------------------------------------
    # Bug Recording
    # ------------------------------------------------------------------

    def record_bug(
        self,
        session_id: str = "",
        title: str = "",
        severity: BugSeverity = BugSeverity.MINOR,
        category: BugCategory = BugCategory.LOGIC,
        description: str = "",
        reproduction_steps: Optional[List[str]] = None,
        game_state: Optional[Dict[str, Any]] = None,
        screenshot_ref: str = "",
        discovered_by: str = "autonomous_tester",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> BugReport:
        with self._lock:
            self._enforce_max_bug_reports()

            bug = BugReport(
                title=title or f"Bug {self._total_bugs_recorded + 1}",
                severity=severity,
                category=category,
                description=description,
                reproduction_steps=list(reproduction_steps) if reproduction_steps else [],
                game_state=game_state or {},
                screenshot_ref=screenshot_ref,
                discovered_by=discovered_by,
                metadata=metadata or {},
            )
            self._bug_reports[bug.id] = bug
            self._total_bugs_recorded += 1

            if session_id:
                if session_id not in self._bugs_by_session:
                    self._bugs_by_session[session_id] = []
                self._bugs_by_session[session_id].append(bug.id)

                session = self._sessions.get(session_id)
                if session is not None:
                    session.bugs_found.append(bug.id)

            return bug

    def get_bug(self, bug_id: str) -> Optional[BugReport]:
        with self._lock:
            return self._bug_reports.get(bug_id)

    def get_session_bugs(self, session_id: str) -> List[BugReport]:
        with self._lock:
            bug_ids = self._bugs_by_session.get(session_id, [])
            return [self._bug_reports[bid] for bid in bug_ids if bid in self._bug_reports]

    def list_bugs(
        self,
        severity: Optional[BugSeverity] = None,
        category: Optional[BugCategory] = None,
    ) -> List[Dict[str, Any]]:
        with self._lock:
            results = list(self._bug_reports.values())
            if severity is not None:
                results = [b for b in results if b.severity == severity]
            if category is not None:
                results = [b for b in results if b.category == category]
            return [b.to_dict() for b in results]

    # ------------------------------------------------------------------
    # State Capture
    # ------------------------------------------------------------------

    def capture_state(
        self,
        session_id: str,
        entities: Optional[Dict[str, Any]] = None,
        variables: Optional[Dict[str, Any]] = None,
        position: Optional[Dict[str, float]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Optional[GameStateSnapshot]:
        with self._lock:
            session = self._sessions.get(session_id)
            if session is None:
                return None
            self._enforce_max_state_snapshots(session_id)

            snapshot = GameStateSnapshot(
                session_id=session_id,
                entities=entities or {},
                variables=variables or {},
                position=position or {},
                metadata=metadata or {},
            )
            self._state_snapshots[snapshot.id] = snapshot
            self._snapshots_by_session[session_id].append(snapshot.id)
            session.states_explored.append(snapshot.id)
            self._total_states_captured += 1
            return snapshot

    def get_state_snapshot(self, snapshot_id: str) -> Optional[GameStateSnapshot]:
        with self._lock:
            return self._state_snapshots.get(snapshot_id)

    def get_session_snapshots(self, session_id: str, limit: int = 50) -> List[GameStateSnapshot]:
        with self._lock:
            snapshot_ids = self._snapshots_by_session.get(session_id, [])
            return [
                self._state_snapshots[sid]
                for sid in snapshot_ids[-limit:]
                if sid in self._state_snapshots
            ]

    # ------------------------------------------------------------------
    # Reports
    # ------------------------------------------------------------------

    def generate_report(self, session_id: str) -> Dict[str, Any]:
        with self._lock:
            self._total_reports_generated += 1

            session = self._sessions.get(session_id)
            if session is None:
                return {"error": "Session not found"}

            bugs = self.get_session_bugs(session_id)
            test_cases = self.get_session_test_cases(session_id)
            coverage = self.compute_coverage(session_id)

            severity_dist: Dict[str, int] = {}
            category_dist: Dict[str, int] = {}
            for bug in bugs:
                s = bug.severity.value
                severity_dist[s] = severity_dist.get(s, 0) + 1
                c = bug.category.value
                category_dist[c] = category_dist.get(c, 0) + 1

            total_severity_weight = sum(bug.get_severity_weight() for bug in bugs)

            return {
                "report_id": uuid.uuid4().hex,
                "session_id": session_id,
                "game_id": session.game_id,
                "strategy": session.strategy.value,
                "test_case_count": len(test_cases),
                "bug_count": len(bugs),
                "states_explored": len(session.states_explored),
                "duration_seconds": round(session.duration, 2),
                "bug_rate": round(session.get_bug_rate(), 4),
                "severity_distribution": severity_dist,
                "category_distribution": category_dist,
                "total_severity_weight": round(total_severity_weight, 2),
                "coverage": coverage,
                "bugs": [b.to_dict() for b in bugs],
                "test_cases": [tc.to_dict() for tc in test_cases],
                "generated_at": time.time(),
            }

    # ------------------------------------------------------------------
    # Coverage
    # ------------------------------------------------------------------

    def compute_coverage(self, session_id: str) -> Dict[str, Any]:
        with self._lock:
            session = self._sessions.get(session_id)
            if session is None:
                return {"error": "Session not found"}

            snapshots = self.get_session_snapshots(session_id, limit=500)
            if not snapshots:
                return {
                    "session_id": session_id,
                    "covered_entities": 0,
                    "total_entities": 0,
                    "coverage_percentage": 0.0,
                }

            all_entities: set = set()
            all_variables: set = set()
            entity_visit_counts: Dict[str, int] = {}

            for snapshot in snapshots:
                for entity_key in snapshot.entities:
                    all_entities.add(entity_key)
                    entity_visit_counts[entity_key] = entity_visit_counts.get(entity_key, 0) + 1
                for var_key in snapshot.variables:
                    all_variables.add(var_key)

            uncovered_entities = sorted(
                all_entities,
                key=lambda e: entity_visit_counts.get(e, 0),
            )[:10]

            total_entities = len(all_entities)
            total_variables = len(all_variables)

            coverage_pct = 1.0 if total_entities > 0 else 0.0

            session.coverage = {
                "covered_entities": total_entities,
                "total_entities": total_entities,
                "covered_variables": total_variables,
                "total_variables": total_variables,
                "coverage_percentage": coverage_pct,
                "snapshots_analyzed": len(snapshots),
            }

            return {
                "session_id": session_id,
                "covered_entities": total_entities,
                "total_entities": total_entities,
                "covered_variables": total_variables,
                "total_variables": total_variables,
                "coverage_percentage": coverage_pct,
                "uncovered_entities": uncovered_entities,
                "snapshots_analyzed": len(snapshots),
                "entity_visit_counts": entity_visit_counts,
            }

    # ------------------------------------------------------------------
    # Session Replay
    # ------------------------------------------------------------------

    def replay_session(self, session_id: str) -> Dict[str, Any]:
        with self._lock:
            session = self._sessions.get(session_id)
            if session is None:
                return {"error": "Session not found"}

            snapshots = self.get_session_snapshots(session_id, limit=500)
            if not snapshots:
                return {"session_id": session_id, "error": "No snapshots to replay"}

            replay_steps: List[Dict[str, Any]] = []
            for i, snapshot in enumerate(snapshots):
                if i == 0:
                    prev_snapshot = None
                else:
                    prev_snapshot = snapshots[i - 1]

                changes: Dict[str, Any] = {}
                if prev_snapshot is not None:
                    for key in snapshot.entities:
                        if key in prev_snapshot.entities:
                            if snapshot.entities[key] != prev_snapshot.entities[key]:
                                changes[key] = {
                                    "from": prev_snapshot.entities[key],
                                    "to": snapshot.entities[key],
                                }
                        else:
                            changes[key] = {"from": None, "to": snapshot.entities[key]}

                    for key in snapshot.variables:
                        if key in prev_snapshot.variables:
                            if snapshot.variables[key] != prev_snapshot.variables[key]:
                                changes[key] = {
                                    "from": prev_snapshot.variables[key],
                                    "to": snapshot.variables[key],
                                }
                        else:
                            changes[key] = {"from": None, "to": snapshot.variables[key]}

                replay_steps.append({
                    "step": i,
                    "snapshot_id": snapshot.id,
                    "timestamp": snapshot.timestamp,
                    "position": snapshot.position,
                    "entity_count": len(snapshot.entities),
                    "variable_count": len(snapshot.variables),
                    "changes": changes,
                    "change_count": len(changes),
                })

            return {
                "session_id": session_id,
                "strategy": session.strategy.value,
                "total_steps": len(replay_steps),
                "replay_steps": replay_steps[:50],
                "duration_seconds": round(session.duration, 2),
            }

    # ------------------------------------------------------------------
    # Statistics
    # ------------------------------------------------------------------

    def get_stats(self) -> Dict[str, Any]:
        with self._lock:
            strategy_dist: Dict[str, int] = {}
            for session in self._sessions.values():
                s = session.strategy.value
                strategy_dist[s] = strategy_dist.get(s, 0) + 1

            severity_dist: Dict[str, int] = {}
            category_dist: Dict[str, int] = {}
            for bug in self._bug_reports.values():
                s = bug.severity.value
                severity_dist[s] = severity_dist.get(s, 0) + 1
                c = bug.category.value
                category_dist[c] = category_dist.get(c, 0) + 1

            total_snapshots = sum(
                len(s.states_explored) for s in self._sessions.values()
            )

            avg_duration = 0.0
            if self._sessions:
                avg_duration = sum(
                    s.duration for s in self._sessions.values() if s.duration > 0
                ) / max(1, sum(1 for s in self._sessions.values() if s.duration > 0))

            return {
                "total_sessions_created": self._total_sessions_created,
                "total_sessions_stored": len(self._sessions),
                "total_test_cases_created": self._total_test_cases_created,
                "total_test_cases_stored": len(self._test_cases),
                "total_bugs_recorded": self._total_bugs_recorded,
                "total_bugs_stored": len(self._bug_reports),
                "total_states_captured": self._total_states_captured,
                "total_states_stored": total_snapshots,
                "total_reports_generated": self._total_reports_generated,
                "total_explorations_run": self._total_explorations_run,
                "strategy_distribution": strategy_dist,
                "severity_distribution": severity_dist,
                "category_distribution": category_dist,
                "avg_session_duration_seconds": round(avg_duration, 2),
                "max_sessions": self._MAX_SESSIONS,
                "max_test_cases": self._MAX_TEST_CASES,
                "max_bug_reports": self._MAX_BUG_REPORTS,
            }

    def reset(self) -> None:
        with self._lock:
            self._sessions.clear()
            self._test_cases.clear()
            self._test_cases_by_session.clear()
            self._bug_reports.clear()
            self._bugs_by_session.clear()
            self._state_snapshots.clear()
            self._snapshots_by_session.clear()
            self._total_sessions_created = 0
            self._total_test_cases_created = 0
            self._total_bugs_recorded = 0
            self._total_states_captured = 0
            self._total_reports_generated = 0
            self._total_explorations_run = 0

    # ------------------------------------------------------------------
    # Internal: Exploration and Anomaly Detection
    # ------------------------------------------------------------------

    def _generate_exploration_snapshot(
        self,
        session_id: str,
        step: int,
        state_provider: Optional[Callable[[], Dict[str, Any]]],
    ) -> Optional[GameStateSnapshot]:
        if state_provider is not None:
            raw_state = state_provider()
            if raw_state is None:
                return None
            return GameStateSnapshot(
                session_id=session_id,
                entities=raw_state.get("entities", {}),
                variables=raw_state.get("variables", {}),
                position=raw_state.get("position", {}),
                metadata={"step": step, "source": "state_provider"},
            )

        return GameStateSnapshot(
            session_id=session_id,
            entities={
                f"entity_{step}_{i}": {
                    "state": "active",
                    "health": max(0, 100 - step % 20),
                    "type": ["player", "enemy", "npc", "item"][step % 4],
                }
                for i in range(3)
            },
            variables={
                "frame": step,
                "score": step * 10,
                "level": max(1, step // 10),
                "time_elapsed": step * 0.5,
            },
            position={"x": float(step % 10), "y": float(step % 8), "z": 0.0},
            metadata={"step": step, "source": "generated"},
        )

    def _detect_anomalies(
        self,
        snapshot: GameStateSnapshot,
        session: TestSession,
    ) -> List[Dict[str, Any]]:
        anomalies: List[Dict[str, Any]] = []

        for entity_key, entity_data in snapshot.entities.items():
            if isinstance(entity_data, dict):
                health = entity_data.get("health")
                if isinstance(health, (int, float)) and health < 0:
                    anomalies.append({
                        "title": f"Negative health on {entity_key}",
                        "severity": BugSeverity.MAJOR,
                        "category": BugCategory.LOGIC,
                        "description": f"Entity {entity_key} has negative health value: {health}",
                        "steps": [f"Observed entity {entity_key} during exploration"],
                    })

                if entity_data.get("state") == "active" and isinstance(health, (int, float)) and health <= 0:
                    anomalies.append({
                        "title": f"Active entity {entity_key} with zero or negative health",
                        "severity": BugSeverity.MINOR,
                        "category": BugCategory.LOGIC,
                        "description": f"Entity {entity_key} is active but has health {health}",
                        "steps": [f"Observed entity {entity_key} in active state"],
                    })

        for var_key, var_value in snapshot.variables.items():
            if isinstance(var_value, (int, float)):
                if var_value < 0 and var_key not in ("frame",):
                    anomalies.append({
                        "title": f"Negative value in variable {var_key}",
                        "severity": BugSeverity.MINOR,
                        "category": BugCategory.LOGIC,
                        "description": f"Variable {var_key} has unexpected negative value: {var_value}",
                        "steps": [f"Observed variable {var_key} during exploration"],
                    })

        position = snapshot.position
        if position.get("x", 0) > 10000 or position.get("y", 0) > 10000:
            anomalies.append({
                "title": "Entity outside expected bounds",
                "severity": BugSeverity.MINOR,
                "category": BugCategory.LOGIC,
                "description": f"Position exceeds expected bounds: {position}",
                "steps": ["Observed entity position during exploration"],
            })

        return anomalies

    # ------------------------------------------------------------------
    # Internal: Limit Enforcement
    # ------------------------------------------------------------------

    def _enforce_max_sessions(self) -> None:
        if len(self._sessions) >= self._MAX_SESSIONS:
            sorted_sessions = sorted(
                self._sessions.items(),
                key=lambda item: item[1].created_at,
            )
            overflow = len(self._sessions) - self._MAX_SESSIONS + 1
            for sid, _ in sorted_sessions[:overflow]:
                self._sessions.pop(sid, None)
                self._test_cases_by_session.pop(sid, None)
                self._bugs_by_session.pop(sid, None)
                self._snapshots_by_session.pop(sid, None)

    def _enforce_max_test_cases(self) -> None:
        if len(self._test_cases) >= self._MAX_TEST_CASES:
            sorted_tcs = sorted(
                self._test_cases.items(),
                key=lambda item: item[1].created_at,
            )
            overflow = len(self._test_cases) - self._MAX_TEST_CASES + 1
            for tid, tc in sorted_tcs[:overflow]:
                self._test_cases.pop(tid, None)
                for sid in self._test_cases_by_session:
                    if tid in self._test_cases_by_session[sid]:
                        self._test_cases_by_session[sid].remove(tid)

    def _enforce_max_bug_reports(self) -> None:
        if len(self._bug_reports) >= self._MAX_BUG_REPORTS:
            sorted_bugs = sorted(
                self._bug_reports.items(),
                key=lambda item: item[1].discovered_at,
            )
            overflow = len(self._bug_reports) - self._MAX_BUG_REPORTS + 1
            for bid, bug in sorted_bugs[:overflow]:
                self._bug_reports.pop(bid, None)
                for sid in self._bugs_by_session:
                    if bid in self._bugs_by_session[sid]:
                        self._bugs_by_session[sid].remove(bid)

    def _enforce_max_state_snapshots(self, session_id: str) -> None:
        if len(self._state_snapshots) >= self._MAX_STATE_SNAPSHOTS:
            sorted_snapshots = sorted(
                self._state_snapshots.items(),
                key=lambda item: item[1].timestamp,
            )
            overflow = len(self._state_snapshots) - self._MAX_STATE_SNAPSHOTS + 1
            for snap_id, snapshot in sorted_snapshots[:overflow]:
                self._state_snapshots.pop(snap_id, None)
                sess_snaps = self._snapshots_by_session.get(snapshot.session_id, [])
                if snap_id in sess_snaps:
                    sess_snaps.remove(snap_id)

        session_snaps = self._snapshots_by_session.get(session_id, [])
        if len(session_snaps) >= self._MAX_STATES_PER_SESSION:
            overflow = len(session_snaps) - self._MAX_STATES_PER_SESSION + 1
            for snap_id in session_snaps[:overflow]:
                self._state_snapshots.pop(snap_id, None)
            self._snapshots_by_session[session_id] = session_snaps[overflow:]


# ---------------------------------------------------------------------------
# Module-level accessor
# ---------------------------------------------------------------------------

def get_autonomous_tester() -> AutonomousTesterEngine:
    """Return the singleton AutonomousTesterEngine instance."""
    return AutonomousTesterEngine.get_instance()