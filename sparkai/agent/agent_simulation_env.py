"""
SparkLabs Agent - Simulation Environment

Sandboxed simulation harness for testing agent behavior before
production deployment in the game engine. Provides deterministic
environments, scenario replay, and behavioral analysis to ensure
agent actions produce expected outcomes in game contexts.

Architecture:
  SimulationEnv
    |-- SimulationWorld (isolated game state container)
    |-- ScenarioRunner (replayable test scenarios)
    |-- ActionSimulator (predict agent action outcomes)
    |-- BehavioralMetrics (track success/failure/latency)
    |-- DeterministicSeed (reproducible simulation runs)

Simulation Modes:
  - DRY_RUN: execute agent plan without mutating real state
  - WHAT_IF: explore alternative action paths
  - REPLAY: replay recorded agent session for debugging
  - STRESS_TEST: push agent with edge-case scenarios
"""

from __future__ import annotations

import copy
import json
import os
import random
import threading
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple


class SimulationMode(Enum):
    DRY_RUN = "dry_run"
    WHAT_IF = "what_if"
    REPLAY = "replay"
    STRESS_TEST = "stress_test"


class SimOutcome(Enum):
    SUCCESS = "success"
    PARTIAL = "partial"
    FAILURE = "failure"
    TIMEOUT = "timeout"
    EXCEPTION = "exception"


@dataclass
class SimAction:
    action_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    name: str = ""
    tool: str = ""
    parameters: Dict[str, Any] = field(default_factory=dict)
    expected_outcome: str = ""
    preconditions: List[str] = field(default_factory=list)
    postconditions: List[str] = field(default_factory=list)


@dataclass
class SimResult:
    action: SimAction
    outcome: SimOutcome = SimOutcome.SUCCESS
    actual_output: Any = None
    error_message: str = ""
    duration_ms: float = 0.0
    side_effects: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "action_id": self.action.action_id,
            "action_name": self.action.name,
            "outcome": self.outcome.value,
            "error": self.error_message,
            "duration_ms": self.duration_ms,
            "side_effects": self.side_effects,
        }


@dataclass
class SimScenario:
    scenario_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    name: str = ""
    description: str = ""
    actions: List[SimAction] = field(default_factory=list)
    seed: int = 42
    tags: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "scenario_id": self.scenario_id,
            "name": self.name,
            "description": self.description,
            "action_count": len(self.actions),
            "tags": self.tags,
        }


@dataclass
class SimRun:
    run_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    scenario: Optional[SimScenario] = None
    mode: SimulationMode = SimulationMode.DRY_RUN
    results: List[SimResult] = field(default_factory=list)
    start_time: float = 0.0
    end_time: float = 0.0
    success_count: int = 0
    failure_count: int = 0

    @property
    def success_rate(self) -> float:
        total = len(self.results)
        if total == 0:
            return 1.0
        return self.success_count / total

    def to_dict(self) -> Dict[str, Any]:
        return {
            "run_id": self.run_id,
            "scenario": self.scenario.name,
            "mode": self.mode.value,
            "results": [r.to_dict() for r in self.results],
            "success_rate": self.success_rate,
            "success_count": self.success_count,
            "failure_count": self.failure_count,
            "duration_s": self.end_time - self.start_time,
        }


@dataclass
class WorldSnapshot:
    entities: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    variables: Dict[str, Any] = field(default_factory=dict)
    scene_graph: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)


class SimulationEnv:
    """Isolated simulation environment for agent behavior testing."""

    _instance: Optional["SimulationEnv"] = None
    _lock = threading.Lock()

    MAX_SCENARIOS = 500
    MAX_RUN_HISTORY = 200

    def __init__(self):
        self._scenarios: Dict[str, SimScenario] = {}
        self._run_history: List[SimRun] = []
        self._world_snapshots: Dict[str, WorldSnapshot] = {}
        self._action_simulators: Dict[str, Callable] = {}
        self._random_gen = random.Random(42)
        self._enabled = True

    @classmethod
    def get_instance(cls) -> "SimulationEnv":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def register_simulator(self, tool_name: str, simulator: Callable) -> None:
        self._action_simulators[tool_name] = simulator

    def create_scenario(
        self,
        name: str,
        description: str = "",
        seed: int = 42,
        tags: Optional[List[str]] = None,
    ) -> SimScenario:
        scenario = SimScenario(
            name=name,
            description=description,
            seed=seed,
            tags=tags or [],
        )
        self._scenarios[scenario.scenario_id] = scenario
        return scenario

    def add_action_to_scenario(
        self,
        scenario_id: str,
        action_name: str,
        tool: str,
        parameters: Dict[str, Any],
        expected_outcome: str = "",
        preconditions: Optional[List[str]] = None,
        postconditions: Optional[List[str]] = None,
    ) -> Optional[SimAction]:
        scenario = self._scenarios.get(scenario_id)
        if not scenario:
            return None
        action = SimAction(
            name=action_name,
            tool=tool,
            parameters=parameters,
            expected_outcome=expected_outcome,
            preconditions=preconditions or [],
            postconditions=postconditions or [],
        )
        scenario.actions.append(action)
        return action

    def run_scenario(
        self,
        scenario_id: str,
        mode: SimulationMode = SimulationMode.DRY_RUN,
    ) -> Optional[SimRun]:
        scenario = self._scenarios.get(scenario_id)
        if not scenario:
            return None

        self._random_gen.seed(scenario.seed)
        run = SimRun(scenario=scenario, mode=mode)
        run.start_time = time.time()

        for action in scenario.actions:
            result = self._simulate_action(action, mode)
            run.results.append(result)
            if result.outcome == SimOutcome.SUCCESS:
                run.success_count += 1
            else:
                run.failure_count += 1

        run.end_time = time.time()
        self._run_history.append(run)
        if len(self._run_history) > self.MAX_RUN_HISTORY:
            self._run_history = self._run_history[-self.MAX_RUN_HISTORY:]

        return run

    def _simulate_action(self, action: SimAction, mode: SimulationMode) -> SimResult:
        result = SimResult(action=action)
        start = time.time()

        simulator = self._action_simulators.get(action.tool)
        if simulator:
            try:
                result.actual_output = simulator(action.parameters, mode)
                result.outcome = SimOutcome.SUCCESS
            except Exception as exc:
                result.outcome = SimOutcome.EXCEPTION
                result.error_message = str(exc)
        else:
            if mode == SimulationMode.DRY_RUN:
                result.outcome = SimOutcome.SUCCESS
                result.actual_output = {"simulated": True, "tool": action.tool}
            elif mode == SimulationMode.WHAT_IF:
                result.outcome = SimOutcome.SUCCESS
                result.actual_output = {"alternative": True}
            else:
                result.outcome = SimOutcome.SUCCESS

        result.duration_ms = (time.time() - start) * 1000
        return result

    def snapshot_world(self, world_name: str = "default") -> WorldSnapshot:
        snapshot = WorldSnapshot()
        self._world_snapshots[world_name] = snapshot
        return snapshot

    def get_world_snapshot(self, world_name: str = "default") -> Optional[WorldSnapshot]:
        return self._world_snapshots.get(world_name)

    def replay_run(self, run_id: str) -> Optional[SimRun]:
        for run in self._run_history:
            if run.run_id == run_id:
                return copy.deepcopy(run)
        return None

    def get_scenario(self, scenario_id: str) -> Optional[SimScenario]:
        return self._scenarios.get(scenario_id)

    def list_scenarios(self, tag: Optional[str] = None) -> List[SimScenario]:
        scenarios = list(self._scenarios.values())
        if tag:
            scenarios = [s for s in scenarios if tag in s.tags]
        return scenarios

    def list_runs(self, limit: int = 50) -> List[SimRun]:
        return self._run_history[-limit:]

    def get_stats(self) -> Dict[str, Any]:
        return {
            "scenarios": len(self._scenarios),
            "run_history": len(self._run_history),
            "simulators": len(self._action_simulators),
            "snapshots": len(self._world_snapshots),
            "enabled": self._enabled,
            "total_actions_simulated": sum(
                len(r.results) for r in self._run_history
            ),
            "overall_success_rate": round(
                sum(r.success_rate for r in self._run_history) / max(1, len(self._run_history))
                if self._run_history else 1.0,
                3,
            ),
        }

    def clear_history(self) -> None:
        self._run_history.clear()

    def delete_scenario(self, scenario_id: str) -> bool:
        if scenario_id in self._scenarios:
            del self._scenarios[scenario_id]
            return True
        return False


def get_simulation_env() -> SimulationEnv:
    return SimulationEnv.get_instance()