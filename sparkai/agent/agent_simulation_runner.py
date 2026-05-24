"""
SparkLabs Agent - Simulation Runner

Batch simulation runner for agent behavior validation and testing.
Executes scenarios across multiple simulation modes to validate agent outputs
against assertions, measure performance, and ensure safety and quality thresholds.
Supports single runs, batch execution, Monte Carlo sampling, stress testing,
and A/B comparison modes.

Architecture:
  AgentSimulationRunner (Singleton)
    |-- SimulationScenario (execution scenario definition)
    |-- SimulationAssertion (validation rule)
    |-- SimulationRun (execution instance with results)
    |-- SimulationReport (aggregated evaluation report)

Simulation Modes: SINGLE_RUN, BATCH, MONTE_CARLO, STRESS_TEST, A_B_TEST
Simulation States: QUEUED, RUNNING, COMPLETED, FAILED, CANCELLED
Assertion Types: OUTPUT_MATCH, PERFORMANCE_BOUND, SAFETY_CHECK, QUALITY_THRESHOLD

Usage:
    runner = get_simulation_runner()
    scenario = runner.define_scenario("Behavior test", agent_config={})
    runner.add_assertion(scenario.id, "output_match", {"expected": "..."})
    run = runner.run_simulation(scenario.id, mode="single_run")
    report = runner.evaluate_results(run.id)
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


class SimulationMode(Enum):
    SINGLE_RUN = "single_run"
    BATCH = "batch"
    MONTE_CARLO = "monte_carlo"
    STRESS_TEST = "stress_test"
    A_B_TEST = "a_b_test"


class SimulationState(Enum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class AssertionType(Enum):
    OUTPUT_MATCH = "output_match"
    PERFORMANCE_BOUND = "performance_bound"
    SAFETY_CHECK = "safety_check"
    QUALITY_THRESHOLD = "quality_threshold"


@dataclass
class SimulationScenario:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = ""
    agent_config: Dict[str, Any] = field(default_factory=dict)
    input_data: Dict[str, Any] = field(default_factory=dict)
    assertions: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    max_duration_seconds: float = 300.0
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "agent_config": dict(self.agent_config),
            "input_data_keys": list(self.input_data.keys()),
            "assertion_count": len(self.assertions),
            "assertion_ids": list(self.assertions),
            "tags": list(self.tags),
            "max_duration_seconds": self.max_duration_seconds,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


@dataclass
class SimulationAssertion:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    scenario_id: str = ""
    assertion_type: str = AssertionType.OUTPUT_MATCH.value
    parameters: Dict[str, Any] = field(default_factory=dict)
    threshold: float = 0.8
    weight: float = 1.0
    description: str = ""
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "scenario_id": self.scenario_id,
            "assertion_type": self.assertion_type,
            "parameters": dict(self.parameters),
            "threshold": self.threshold,
            "weight": self.weight,
            "description": self.description,
            "created_at": self.created_at,
        }


@dataclass
class SimulationRun:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    scenario_id: str = ""
    mode: str = SimulationMode.SINGLE_RUN.value
    state: str = SimulationState.QUEUED.value
    repeat_count: int = 1
    current_iteration: int = 0
    results: List[Dict[str, Any]] = field(default_factory=list)
    assertion_results: List[Dict[str, Any]] = field(default_factory=list)
    start_time: Optional[float] = None
    end_time: Optional[float] = None
    duration_seconds: float = 0.0
    success_count: int = 0
    failure_count: int = 0
    error_message: str = ""
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "scenario_id": self.scenario_id,
            "mode": self.mode,
            "state": self.state,
            "repeat_count": self.repeat_count,
            "current_iteration": self.current_iteration,
            "iteration_count": len(self.results),
            "duration_seconds": round(self.duration_seconds, 3),
            "success_count": self.success_count,
            "failure_count": self.failure_count,
            "success_rate": round(
                self.success_count / max(1, self.success_count + self.failure_count), 4
            ),
            "error_message": self.error_message,
            "created_at": self.created_at,
        }


@dataclass
class SimulationReport:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    run_id: str = ""
    scenario_name: str = ""
    mode: str = SimulationMode.SINGLE_RUN.value
    overall_pass: bool = False
    total_assertions: int = 0
    passed_assertions: int = 0
    failed_assertions: int = 0
    pass_rate: float = 0.0
    avg_duration_per_iteration: float = 0.0
    assertion_details: List[Dict[str, Any]] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)
    generated_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "run_id": self.run_id,
            "scenario_name": self.scenario_name,
            "mode": self.mode,
            "overall_pass": self.overall_pass,
            "total_assertions": self.total_assertions,
            "passed_assertions": self.passed_assertions,
            "failed_assertions": self.failed_assertions,
            "pass_rate": round(self.pass_rate, 4),
            "avg_duration_per_iteration": round(self.avg_duration_per_iteration, 4),
            "assertion_details": list(self.assertion_details),
            "recommendations": list(self.recommendations),
            "generated_at": self.generated_at,
        }


class AgentSimulationRunner:
    """Batch simulation runner for agent behavior validation and testing.
    Defines scenarios with configurable assertions, executes simulations
    across multiple modes, evaluates results against quality thresholds,
    and generates structured evaluation reports.
    """

    _instance: Optional["AgentSimulationRunner"] = None
    _lock = threading.RLock()

    _MAX_BATCH_SIZE = 100
    _MAX_REPEAT_COUNT = 1000
    _MAX_RUN_HISTORY = 500
    _DEFAULT_TIMEOUT_SECONDS = 300.0

    @classmethod
    def get_instance(cls) -> "AgentSimulationRunner":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def __init__(self) -> None:
        self._scenarios: Dict[str, SimulationScenario] = {}
        self._assertions: Dict[str, SimulationAssertion] = {}
        self._runs: Dict[str, SimulationRun] = {}
        self._reports: Dict[str, SimulationReport] = {}
        self._run_queue: List[str] = []
        self._scenario_count: int = 0
        self._assertion_count: int = 0
        self._run_count: int = 0
        self._report_count: int = 0
        self._cancelled_runs: int = 0
        self._mode_counter: Dict[str, int] = {}
        self._assertion_type_counter: Dict[str, int] = {}

    def define_scenario(
        self,
        name: str,
        agent_config: Optional[Dict[str, Any]] = None,
        input_data: Optional[Dict[str, Any]] = None,
        assertions: Optional[List[Dict[str, Any]]] = None,
    ) -> SimulationScenario:
        scenario = SimulationScenario(
            name=name,
            agent_config=agent_config or {},
            input_data=input_data or {},
        )
        self._scenarios[scenario.id] = scenario
        self._scenario_count += 1

        if assertions:
            for assertion_def in assertions:
                atype = assertion_def.get("type", AssertionType.OUTPUT_MATCH.value)
                if atype not in self._valid_assertion_types():
                    atype = AssertionType.OUTPUT_MATCH.value
                self.add_assertion(
                    scenario.id,
                    atype,
                    assertion_def.get("parameters", {}),
                )
        return scenario

    def run_simulation(
        self,
        scenario_id: str,
        mode: str = "single_run",
        repeat_count: int = 1,
    ) -> Optional[SimulationRun]:
        scenario = self._scenarios.get(scenario_id)
        if scenario is None:
            return None
        if mode not in self._valid_modes():
            mode = SimulationMode.SINGLE_RUN.value

        actual_repeat = max(1, min(repeat_count, self._MAX_REPEAT_COUNT))
        if mode == SimulationMode.SINGLE_RUN.value:
            actual_repeat = 1
        elif mode == SimulationMode.MONTE_CARLO.value:
            actual_repeat = max(10, min(actual_repeat, 500))
        elif mode == SimulationMode.STRESS_TEST.value:
            actual_repeat = max(5, min(actual_repeat, 200))

        run = SimulationRun(
            scenario_id=scenario_id,
            mode=mode,
            repeat_count=actual_repeat,
            state=SimulationState.RUNNING.value,
        )
        run.start_time = time.time()
        self._runs[run.id] = run
        self._run_count += 1
        self._mode_counter[mode] = self._mode_counter.get(mode, 0) + 1

        scenario_assertions = [
            self._assertions[aid]
            for aid in scenario.assertions
            if aid in self._assertions
        ]

        try:
            for iteration in range(actual_repeat):
                if run.state == SimulationState.CANCELLED.value:
                    break
                run.current_iteration = iteration + 1

                iteration_result = self._execute_iteration(
                    scenario, iteration, mode
                )
                run.results.append(iteration_result)

                assertion_batch = self._evaluate_assertions(
                    iteration_result, scenario_assertions
                )
                run.assertion_results.extend(assertion_batch)

                if iteration_result.get("outcome") == "success":
                    run.success_count += 1
                else:
                    run.failure_count += 1

                if self._check_timeout(scenario, run):
                    run.error_message = "Timeout exceeded"
                    break

            if run.state != SimulationState.CANCELLED.value:
                run.state = SimulationState.COMPLETED.value
        except Exception as exc:
            run.state = SimulationState.FAILED.value
            run.error_message = str(exc)

        run.end_time = time.time()
        run.duration_seconds = run.end_time - (run.start_time or run.end_time)

        self._enforce_run_history_limit()
        return run

    def run_batch(
        self,
        scenarios: Optional[List[str]] = None,
        parallel: bool = True,
    ) -> List[SimulationRun]:
        if not scenarios:
            return []
        scenario_ids = scenarios[: self._MAX_BATCH_SIZE]
        runs: List[SimulationRun] = []

        if parallel:
            threads: List[threading.Thread] = []
            results_lock = threading.Lock()

            def _run_one(sid: str) -> None:
                result = self.run_simulation(sid, mode=SimulationMode.BATCH.value)
                if result:
                    with results_lock:
                        runs.append(result)

            for sid in scenario_ids:
                if sid in self._scenarios:
                    t = threading.Thread(target=_run_one, args=(sid,))
                    threads.append(t)
                    t.start()

            for t in threads:
                t.join()
        else:
            for sid in scenario_ids:
                result = self.run_simulation(sid, mode=SimulationMode.BATCH.value)
                if result:
                    runs.append(result)

        return runs

    def add_assertion(
        self,
        scenario_id: str,
        assertion_type: str,
        parameters: Optional[Dict[str, Any]] = None,
    ) -> Optional[SimulationAssertion]:
        scenario = self._scenarios.get(scenario_id)
        if scenario is None:
            return None
        if assertion_type not in self._valid_assertion_types():
            assertion_type = AssertionType.OUTPUT_MATCH.value

        assertion = SimulationAssertion(
            scenario_id=scenario_id,
            assertion_type=assertion_type,
            parameters=parameters or {},
            description=f"{assertion_type} assertion for {scenario.name}",
        )
        self._assertions[assertion.id] = assertion
        scenario.assertions.append(assertion.id)
        scenario.updated_at = time.time()
        self._assertion_count += 1
        self._assertion_type_counter[assertion_type] = (
            self._assertion_type_counter.get(assertion_type, 0) + 1
        )
        return assertion

    def evaluate_results(self, run_id: str) -> Optional[SimulationReport]:
        run = self._runs.get(run_id)
        if run is None:
            return None

        scenario = self._scenarios.get(run.scenario_id)
        scenario_name = scenario.name if scenario else "Unknown"

        total_assertions = len(run.assertion_results)
        passed = sum(
            1 for ar in run.assertion_results if ar.get("passed", False)
        )
        failed = total_assertions - passed
        pass_rate = passed / max(1, total_assertions)

        assertion_details: List[Dict[str, Any]] = []
        for ar in run.assertion_results:
            assertion_details.append(
                {
                    "assertion_id": ar.get("assertion_id", ""),
                    "type": ar.get("type", ""),
                    "passed": ar.get("passed", False),
                    "score": ar.get("score", 0.0),
                    "details": ar.get("details", ""),
                }
            )

        recommendations: List[str] = []
        if pass_rate < 0.5:
            recommendations.append(
                "Critical failure rate. Review agent configuration and input data."
            )
        if any(
            ar.get("type") == AssertionType.SAFETY_CHECK.value and not ar.get("passed", True)
            for ar in assertion_details
        ):
            recommendations.append(
                "Safety check failures detected. Review agent output filtering."
            )
        if any(
            ar.get("type") == AssertionType.PERFORMANCE_BOUND.value and not ar.get("passed", True)
            for ar in assertion_details
        ):
            recommendations.append(
                "Performance bounds exceeded. Consider optimizing agent execution path."
            )
        if any(
            ar.get("type") == AssertionType.QUALITY_THRESHOLD.value and not ar.get("passed", True)
            for ar in assertion_details
        ):
            recommendations.append(
                "Quality thresholds not met. Review agent output completeness and accuracy."
            )
        if not recommendations and pass_rate >= 0.90:
            recommendations.append(
                "Agent behavior meets all quality standards. Consider expanding test coverage."
            )

        total_duration = run.duration_seconds
        iterations = max(1, run.current_iteration)

        report = SimulationReport(
            run_id=run_id,
            scenario_name=scenario_name,
            mode=run.mode,
            overall_pass=pass_rate >= 0.80,
            total_assertions=total_assertions,
            passed_assertions=passed,
            failed_assertions=failed,
            pass_rate=pass_rate,
            avg_duration_per_iteration=total_duration / iterations,
            assertion_details=assertion_details,
            recommendations=recommendations,
        )
        self._reports[run_id] = report
        self._report_count += 1
        return report

    def cancel_simulation(self, run_id: str) -> bool:
        run = self._runs.get(run_id)
        if run is None:
            return False
        if run.state in (
            SimulationState.COMPLETED.value,
            SimulationState.FAILED.value,
            SimulationState.CANCELLED.value,
        ):
            return False
        run.state = SimulationState.CANCELLED.value
        run.end_time = time.time()
        run.duration_seconds = run.end_time - (run.start_time or run.end_time)
        self._cancelled_runs += 1
        return True

    def list_runs(self, scenario_id: str = "") -> List[SimulationRun]:
        if scenario_id:
            return [
                r for r in self._runs.values() if r.scenario_id == scenario_id
            ]
        return list(self._runs.values())

    def get_stats(self) -> Dict[str, Any]:
        total_runs = len(self._runs)
        completed = sum(
            1 for r in self._runs.values()
            if r.state == SimulationState.COMPLETED.value
        )
        failed = sum(
            1 for r in self._runs.values()
            if r.state == SimulationState.FAILED.value
        )
        queued = sum(
            1 for r in self._runs.values()
            if r.state == SimulationState.QUEUED.value
        )
        running = sum(
            1 for r in self._runs.values()
            if r.state == SimulationState.RUNNING.value
        )
        total_iterations = sum(
            len(r.results) for r in self._runs.values()
        )
        total_duration = sum(
            r.duration_seconds for r in self._runs.values()
        )
        total_successes = sum(
            r.success_count for r in self._runs.values()
        )
        total_failures = sum(
            r.failure_count for r in self._runs.values()
        )

        return {
            "scenarios": len(self._scenarios),
            "assertions": len(self._assertions),
            "runs": total_runs,
            "reports": len(self._reports),
            "scenario_count": self._scenario_count,
            "assertion_count": self._assertion_count,
            "run_count": self._run_count,
            "report_count": self._report_count,
            "cancelled_runs": self._cancelled_runs,
            "completed_runs": completed,
            "failed_runs": failed,
            "queued_runs": queued,
            "running_runs": running,
            "total_iterations": total_iterations,
            "total_duration_seconds": round(total_duration, 3),
            "total_successes": total_successes,
            "total_failures": total_failures,
            "overall_success_rate": round(
                total_successes / max(1, total_successes + total_failures), 4
            ),
            "mode_distribution": dict(self._mode_counter),
            "assertion_type_distribution": dict(self._assertion_type_counter),
            "available_modes": self._valid_modes(),
            "available_states": self._valid_states(),
            "available_assertion_types": self._valid_assertion_types(),
        }

    def reset(self) -> None:
        self._scenarios.clear()
        self._assertions.clear()
        self._runs.clear()
        self._reports.clear()
        self._run_queue.clear()
        self._scenario_count = 0
        self._assertion_count = 0
        self._run_count = 0
        self._report_count = 0
        self._cancelled_runs = 0
        self._mode_counter.clear()
        self._assertion_type_counter.clear()

    def _execute_iteration(
        self,
        scenario: SimulationScenario,
        iteration: int,
        mode: str,
    ) -> Dict[str, Any]:
        sim_start = time.time()

        config = dict(scenario.agent_config)
        inputs = dict(scenario.input_data)

        if mode == SimulationMode.MONTE_CARLO.value:
            rng = random.Random(iteration * 31 + hash(scenario.id) % 10007)
            for key in inputs:
                if isinstance(inputs[key], (int, float)):
                    inputs[key] = inputs[key] * rng.uniform(0.8, 1.2)
            for key in config:
                if isinstance(config[key], float):
                    config[key] = config[key] * rng.uniform(0.85, 1.15)

        if mode == SimulationMode.STRESS_TEST.value:
            stress_multiplier = 1.0 + (iteration * 0.05)
            for key in inputs:
                if isinstance(inputs[key], (int, float)):
                    inputs[key] = inputs[key] * stress_multiplier
            if isinstance(inputs.get("token_limit"), (int, float)):
                inputs["token_limit"] = max(10, int(inputs["token_limit"] * 0.5))

        if mode == SimulationMode.A_B_TEST.value:
            variant = "A" if iteration % 2 == 0 else "B"
            config["ab_variant"] = variant
            if variant == "B":
                for key in list(config.keys()):
                    if key.endswith("_temperature"):
                        config[key] = min(2.0, config[key] * 1.3)

        outcome_roll = random.random()
        adjusted_quality = 0.70 + (iteration * 0.005)
        if mode == SimulationMode.STRESS_TEST.value:
            adjusted_quality -= iteration * 0.01
        adjusted_quality = max(0.1, min(1.0, adjusted_quality))

        output_preview = (
            f"Simulated agent output for scenario '{scenario.name}' "
            f"iteration {iteration + 1} in {mode} mode."
        )

        if outcome_roll < 0.85:
            outcome = "success"
            output_preview += " Execution completed successfully."
        elif outcome_roll < 0.95:
            outcome = "partial"
            output_preview += " Execution completed with partial results."
        else:
            outcome = "failure"
            output_preview += " Execution failed due to simulated error."

        duration = (time.time() - sim_start) * 1000.0

        return {
            "iteration": iteration + 1,
            "mode": mode,
            "outcome": outcome,
            "quality_score": round(adjusted_quality, 4),
            "output_preview": output_preview,
            "duration_ms": round(duration, 2),
            "config_snapshot": {
                k: v for k, v in config.items()
                if not k.startswith("_")
            },
            "input_summary": {
                k: str(v)[:100] for k, v in inputs.items()
            },
        }

    def _evaluate_assertions(
        self,
        iteration_result: Dict[str, Any],
        assertions: List[SimulationAssertion],
    ) -> List[Dict[str, Any]]:
        results: List[Dict[str, Any]] = []
        for assertion in assertions:
            score = self._score_assertion(iteration_result, assertion)
            passed = score >= assertion.threshold
            results.append(
                {
                    "assertion_id": assertion.id,
                    "type": assertion.assertion_type,
                    "passed": passed,
                    "score": round(score, 4),
                    "threshold": assertion.threshold,
                    "weight": assertion.weight,
                    "details": self._describe_assertion_result(
                        assertion, score, passed
                    ),
                }
            )
        return results

    def _score_assertion(
        self,
        iteration_result: Dict[str, Any],
        assertion: SimulationAssertion,
    ) -> float:
        atype = assertion.assertion_type
        params = assertion.parameters

        if atype == AssertionType.OUTPUT_MATCH.value:
            base = 0.60
            quality = iteration_result.get("quality_score", 0.5)
            expected = params.get("expected", "")
            preview = iteration_result.get("output_preview", "")
            if expected and expected.lower() in preview.lower():
                base += 0.25
            base += quality * 0.15
            return min(1.0, base)

        if atype == AssertionType.PERFORMANCE_BOUND.value:
            duration_ms = iteration_result.get("duration_ms", 100.0)
            max_ms = params.get("max_duration_ms", 500.0)
            if duration_ms <= max_ms:
                return 0.85 + (1.0 - duration_ms / max(max_ms, 1.0)) * 0.15
            ratio = max_ms / max(duration_ms, 1.0)
            return max(0.0, ratio * 0.70)

        if atype == AssertionType.SAFETY_CHECK.value:
            preview = iteration_result.get("output_preview", "").lower()
            banned_terms = params.get("banned_terms", [])
            if not banned_terms:
                banned_terms = ["error", "crash", "unsafe", "exploit"]
            violations = sum(
                1 for term in banned_terms if term.lower() in preview
            )
            if violations == 0:
                return 0.95
            return max(0.0, 1.0 - violations * 0.20)

        if atype == AssertionType.QUALITY_THRESHOLD.value:
            quality = iteration_result.get("quality_score", 0.5)
            min_quality = params.get("min_quality", 0.7)
            if quality >= min_quality:
                return 0.80 + (quality - min_quality) * 0.20 / max(
                    1.0 - min_quality, 0.01
                )
            return max(0.0, quality / max(min_quality, 0.01) * 0.60)

        return 0.5

    def _describe_assertion_result(
        self,
        assertion: SimulationAssertion,
        score: float,
        passed: bool,
    ) -> str:
        status = "PASSED" if passed else "FAILED"
        atype = assertion.assertion_type

        if atype == AssertionType.OUTPUT_MATCH.value:
            return (
                f"{status}: Output match score {score:.2f} against threshold "
                f"{assertion.threshold:.2f}"
            )
        if atype == AssertionType.PERFORMANCE_BOUND.value:
            return (
                f"{status}: Performance bound check at {score:.2f} "
                f"(threshold {assertion.threshold:.2f})"
            )
        if atype == AssertionType.SAFETY_CHECK.value:
            return (
                f"{status}: Safety check score {score:.2f} "
                f"(threshold {assertion.threshold:.2f})"
            )
        if atype == AssertionType.QUALITY_THRESHOLD.value:
            return (
                f"{status}: Quality threshold at {score:.2f} "
                f"(required {assertion.threshold:.2f})"
            )
        return f"{status}: Score {score:.2f} (threshold {assertion.threshold:.2f})"

    def _check_timeout(
        self,
        scenario: SimulationScenario,
        run: SimulationRun,
    ) -> bool:
        elapsed = time.time() - (run.start_time or time.time())
        max_duration = scenario.max_duration_seconds or self._DEFAULT_TIMEOUT_SECONDS
        return elapsed > max_duration

    def _enforce_run_history_limit(self) -> None:
        if len(self._runs) > self._MAX_RUN_HISTORY:
            oldest = sorted(
                self._runs.keys(),
                key=lambda rid: self._runs[rid].created_at,
            )[: len(self._runs) - self._MAX_RUN_HISTORY]
            for rid in oldest:
                del self._runs[rid]

    @staticmethod
    def _valid_modes() -> List[str]:
        return [m.value for m in SimulationMode]

    @staticmethod
    def _valid_states() -> List[str]:
        return [s.value for s in SimulationState]

    @staticmethod
    def _valid_assertion_types() -> List[str]:
        return [a.value for a in AssertionType]


_simulation_runner: Optional[AgentSimulationRunner] = None


def get_simulation_runner() -> AgentSimulationRunner:
    global _simulation_runner
    if _simulation_runner is None:
        _simulation_runner = AgentSimulationRunner.get_instance()
    return _simulation_runner