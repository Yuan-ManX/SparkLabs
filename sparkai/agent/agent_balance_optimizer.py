"""
SparkLabs Agent - Balance Optimizer

Autonomous game balance optimization system that analyzes game parameters
and finds optimal balance configurations through simulation-based tuning.
Uses a hill-climbing approach with configurable mutation strategies to
converge on parameter values that satisfy target gameplay metrics.

Architecture:
  AgentBalanceOptimizer (singleton)
    |-- GameParameter (parameter definition with bounds and constraints)
    |-- BalanceTarget (desired metric outcome specification)
    |-- SimulationResult (per-iteration fitness and metric snapshot)
    |-- OptimizationSession (full optimization run lifecycle)
    |-- BalanceReport (post-optimization analysis and recommendations)

Optimization Domains:
  - COMBAT: damage, health, cooldowns, critical hit rates
  - ECONOMY: currency flow, item pricing, resource generation
  - PROGRESSION: XP curves, unlock pacing, power scaling
  - DIFFICULTY: enemy stats, spawn rates, challenge scaling
  - LOOT: drop rates, rarity distributions, reward frequencies
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


# ------------------------------------------------------------------
# Enums
# ------------------------------------------------------------------


class BalanceDomain(Enum):
    """Game domain that balance optimization targets."""
    COMBAT = "combat"
    ECONOMY = "economy"
    PROGRESSION = "progression"
    DIFFICULTY = "difficulty"
    LOOT = "loot"


class OptimizationGoal(Enum):
    """The type of optimization objective to pursue."""
    MAX_FAIRNESS = "max_fairness"
    TARGET_WIN_RATE = "target_win_rate"
    RESOURCE_FLOW = "resource_flow"
    PROGRESSION_PACE = "progression_pace"
    ENGAGEMENT_CURVE = "engagement_curve"


class ParameterType(Enum):
    """The data type of a game parameter."""
    FLOAT = "float"
    INTEGER = "integer"
    BOOLEAN = "boolean"
    ENUMERATION = "enumeration"
    CURVE = "curve"


class OptimizationStatus(Enum):
    """Current state of an optimization session."""
    IDLE = "idle"
    RUNNING = "running"
    CONVERGED = "converged"
    MAX_ITERATIONS = "max_iterations"
    FAILED = "failed"


# ------------------------------------------------------------------
# Dataclasses
# ------------------------------------------------------------------


@dataclass
class GameParameter:
    """A tunable game parameter with value constraints and metadata."""
    param_id: str = field(default_factory=lambda: uuid.uuid4().hex[:8])
    name: str = ""
    param_type: ParameterType = ParameterType.FLOAT
    current_value: Any = 1.0
    min_value: float = 0.0
    max_value: float = 100.0
    step: float = 0.1
    enumeration_options: List[str] = field(default_factory=list)
    description: str = ""
    domain: BalanceDomain = BalanceDomain.COMBAT
    weight: float = 1.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "param_id": self.param_id,
            "name": self.name,
            "param_type": self.param_type.value,
            "current_value": self.current_value,
            "min_value": self.min_value,
            "max_value": self.max_value,
            "step": self.step,
            "enumeration_options": list(self.enumeration_options),
            "description": self.description,
            "domain": self.domain.value,
            "weight": self.weight,
        }

    def clamp_value(self, value: Any) -> Any:
        """Clamp a value to the parameter's valid range."""
        if self.param_type == ParameterType.BOOLEAN:
            return bool(value)
        if self.param_type == ParameterType.ENUMERATION:
            if self.enumeration_options and value not in self.enumeration_options:
                return self.enumeration_options[0] if self.enumeration_options else value
            return value
        if self.param_type == ParameterType.INTEGER:
            return int(max(self.min_value, min(self.max_value, round(float(value)))))
        if self.param_type == ParameterType.CURVE:
            return float(max(self.min_value, min(self.max_value, float(value))))
        return float(max(self.min_value, min(self.max_value, float(value))))


@dataclass
class BalanceTarget:
    """A desired metric outcome for the optimization process."""
    target_id: str = field(default_factory=lambda: uuid.uuid4().hex[:8])
    name: str = ""
    domain: BalanceDomain = BalanceDomain.COMBAT
    goal: OptimizationGoal = OptimizationGoal.TARGET_WIN_RATE
    target_value: float = 0.5
    tolerance: float = 0.05
    description: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "target_id": self.target_id,
            "name": self.name,
            "domain": self.domain.value,
            "goal": self.goal.value,
            "target_value": self.target_value,
            "tolerance": self.tolerance,
            "description": self.description,
        }

    def is_satisfied(self, actual_value: float) -> bool:
        """Check whether an actual metric value satisfies this target."""
        return abs(actual_value - self.target_value) <= self.tolerance


@dataclass
class SimulationResult:
    """The outcome of a single simulation run with parameter values."""
    result_id: str = field(default_factory=lambda: uuid.uuid4().hex[:8])
    parameter_values: Dict[str, Any] = field(default_factory=dict)
    metrics: Dict[str, float] = field(default_factory=dict)
    fitness_score: float = 0.0
    iteration: int = 0
    timestamp: float = field(default_factory=_time_module.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "result_id": self.result_id,
            "parameter_values": dict(self.parameter_values),
            "metrics": dict(self.metrics),
            "fitness_score": self.fitness_score,
            "iteration": self.iteration,
            "timestamp": self.timestamp,
        }


@dataclass
class OptimizationSession:
    """A complete balance optimization run tracking parameters and history."""
    session_id: str = field(default_factory=lambda: uuid.uuid4().hex[:8])
    name: str = ""
    domain: BalanceDomain = BalanceDomain.COMBAT
    parameters: List[GameParameter] = field(default_factory=list)
    targets: List[BalanceTarget] = field(default_factory=list)
    history: List[SimulationResult] = field(default_factory=list)
    status: OptimizationStatus = OptimizationStatus.IDLE
    current_iteration: int = 0
    max_iterations: int = 100
    best_result: Optional[SimulationResult] = None
    created_at: float = field(default_factory=_time_module.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "session_id": self.session_id,
            "name": self.name,
            "domain": self.domain.value,
            "parameter_count": len(self.parameters),
            "target_count": len(self.targets),
            "history_length": len(self.history),
            "status": self.status.value,
            "current_iteration": self.current_iteration,
            "max_iterations": self.max_iterations,
            "best_fitness": self.best_result.fitness_score if self.best_result else 0.0,
            "created_at": self.created_at,
        }


@dataclass
class BalanceReport:
    """Post-optimization analysis summarizing changes and recommendations."""
    report_id: str = field(default_factory=lambda: uuid.uuid4().hex[:8])
    session_id: str = ""
    summary: str = ""
    recommendations: List[str] = field(default_factory=list)
    before_metrics: Dict[str, float] = field(default_factory=dict)
    after_metrics: Dict[str, float] = field(default_factory=dict)
    parameter_changes: Dict[str, dict] = field(default_factory=dict)
    improvement_pct: float = 0.0
    generated_at: float = field(default_factory=_time_module.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "report_id": self.report_id,
            "session_id": self.session_id,
            "summary": self.summary,
            "recommendations": list(self.recommendations),
            "before_metrics": dict(self.before_metrics),
            "after_metrics": dict(self.after_metrics),
            "parameter_changes": {
                k: dict(v) for k, v in self.parameter_changes.items()
            },
            "improvement_pct": self.improvement_pct,
            "generated_at": self.generated_at,
        }


# ------------------------------------------------------------------
# AgentBalanceOptimizer Singleton
# ------------------------------------------------------------------


class AgentBalanceOptimizer:
    """
    Singleton system for autonomous game balance optimization.

    Defines tunable parameters and target metrics, then iteratively
    simulates and evaluates parameter configurations using a hill-climbing
    strategy to converge on optimal balance settings.
    """

    _instance: Optional[AgentBalanceOptimizer] = None
    _lock = threading.RLock()

    def __new__(cls) -> AgentBalanceOptimizer:
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    instance = super().__new__(cls)
                    cls._instance = instance
        return cls._instance

    @classmethod
    def get_instance(cls) -> AgentBalanceOptimizer:
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
            self._parameters: Dict[str, GameParameter] = {}
            self._targets: Dict[str, BalanceTarget] = {}
            self._sessions: Dict[str, OptimizationSession] = {}
            self._stats: Dict[str, Any] = {
                "total_sessions_created": 0,
                "total_simulations_run": 0,
                "total_optimizations_completed": 0,
                "total_parameters_defined": 0,
                "total_targets_defined": 0,
            }
            self._initialized = True

    # ------------------------------------------------------------------
    # Parameter Management
    # ------------------------------------------------------------------

    def create_parameter(
        self,
        name: str,
        param_type: ParameterType,
        domain: BalanceDomain,
        current_value: Any = 1.0,
        min_value: float = 0.0,
        max_value: float = 100.0,
        description: str = "",
        weight: float = 1.0,
        step: float = 0.1,
        enumeration_options: Optional[List[str]] = None,
    ) -> GameParameter:
        """Create a new tunable game parameter definition."""
        with self._lock:
            parameter = GameParameter(
                name=name,
                param_type=param_type,
                domain=domain,
                current_value=current_value,
                min_value=min_value,
                max_value=max_value,
                description=description,
                weight=weight,
                step=step,
                enumeration_options=enumeration_options or [],
            )
            self._parameters[parameter.param_id] = parameter
            self._stats["total_parameters_defined"] += 1
            return parameter

    def update_parameter(
        self, parameter_id: str, new_value: Any
    ) -> Optional[GameParameter]:
        """Update the current value of an existing parameter."""
        with self._lock:
            parameter = self._parameters.get(parameter_id)
            if parameter is None:
                return None
            parameter.current_value = parameter.clamp_value(new_value)
            return parameter

    def list_parameters(
        self,
        domain: Optional[BalanceDomain] = None,
        param_type: Optional[ParameterType] = None,
    ) -> List[GameParameter]:
        """List all parameters, optionally filtered by domain and/or type."""
        results = list(self._parameters.values())
        if domain is not None:
            results = [p for p in results if p.domain == domain]
        if param_type is not None:
            results = [p for p in results if p.param_type == param_type]
        return results

    def get_parameter(self, parameter_id: str) -> Optional[GameParameter]:
        """Retrieve a single parameter by its ID."""
        return self._parameters.get(parameter_id)

    # ------------------------------------------------------------------
    # Target Management
    # ------------------------------------------------------------------

    def create_target(
        self,
        name: str,
        domain: BalanceDomain,
        goal: OptimizationGoal,
        target_value: float,
        tolerance: float = 0.05,
        description: str = "",
    ) -> BalanceTarget:
        """Create a balance target that defines a desired metric outcome."""
        with self._lock:
            target = BalanceTarget(
                name=name,
                domain=domain,
                goal=goal,
                target_value=target_value,
                tolerance=tolerance,
                description=description,
            )
            self._targets[target.target_id] = target
            self._stats["total_targets_defined"] += 1
            return target

    def list_targets(
        self, domain: Optional[BalanceDomain] = None
    ) -> List[BalanceTarget]:
        """List all balance targets, optionally filtered by domain."""
        results = list(self._targets.values())
        if domain is not None:
            results = [t for t in results if t.domain == domain]
        return results

    # ------------------------------------------------------------------
    # Session Management
    # ------------------------------------------------------------------

    def create_session(
        self,
        name: str,
        domain: BalanceDomain,
        parameter_ids: List[str],
        target_ids: List[str],
        max_iterations: int = 100,
    ) -> Optional[OptimizationSession]:
        """Create an optimization session linking parameters and targets."""
        with self._lock:
            parameters = []
            for pid in parameter_ids:
                param = self._parameters.get(pid)
                if param is None:
                    return None
                parameters.append(param)

            targets = []
            for tid in target_ids:
                target = self._targets.get(tid)
                if target is None:
                    return None
                targets.append(target)

            if not parameters or not targets:
                return None

            session = OptimizationSession(
                name=name,
                domain=domain,
                parameters=parameters,
                targets=targets,
                max_iterations=max_iterations,
            )
            self._sessions[session.session_id] = session
            self._stats["total_sessions_created"] += 1
            return session

    def get_session(self, session_id: str) -> Optional[OptimizationSession]:
        """Retrieve an optimization session by its ID."""
        return self._sessions.get(session_id)

    def list_sessions(
        self,
        domain: Optional[BalanceDomain] = None,
        status: Optional[OptimizationStatus] = None,
    ) -> List[OptimizationSession]:
        """List all sessions, optionally filtered by domain and/or status."""
        results = list(self._sessions.values())
        if domain is not None:
            results = [s for s in results if s.domain == domain]
        if status is not None:
            results = [s for s in results if s.status == status]
        return results

    def delete_session(self, session_id: str) -> bool:
        """Delete an optimization session and its history."""
        with self._lock:
            if session_id in self._sessions:
                del self._sessions[session_id]
                return True
            return False

    # ------------------------------------------------------------------
    # Simulation Engine
    # ------------------------------------------------------------------

    def run_simulation(
        self, session_id: str, parameter_values: Dict[str, Any]
    ) -> Optional[SimulationResult]:
        """
        Run a single simulation with the given parameter values.

        Computes a fitness score by simulating gameplay metrics based on
        the provided parameter values and comparing them against the
        session's balance targets. Realistic noise is injected to model
        game variance.
        """
        with self._lock:
            session = self._sessions.get(session_id)
            if session is None:
                return None

            if session.status == OptimizationStatus.IDLE:
                session.status = OptimizationStatus.RUNNING

            session.current_iteration += 1
            iteration = session.current_iteration

            # Clamp all parameter values to their defined ranges
            clamped_values: Dict[str, Any] = {}
            for param in session.parameters:
                raw_value = parameter_values.get(param.param_id, param.current_value)
                clamped_values[param.param_id] = param.clamp_value(raw_value)

            # Simulate metrics based on parameter values
            metrics = self._compute_metrics(clamped_values, session)
            fitness = self._compute_fitness(metrics, session)

            result = SimulationResult(
                parameter_values=dict(clamped_values),
                metrics=metrics,
                fitness_score=fitness,
                iteration=iteration,
            )
            session.history.append(result)

            if session.best_result is None or fitness > session.best_result.fitness_score:
                session.best_result = result

            self._stats["total_simulations_run"] += 1
            return result

    def _compute_metrics(
        self, parameter_values: Dict[str, Any], session: OptimizationSession
    ) -> Dict[str, float]:
        """
        Compute simulated gameplay metrics from parameter values.

        Each parameter contributes to a set of derived metrics using
        a weighted model with noise to simulate real game variance.
        """
        metrics: Dict[str, float] = {}
        noise = random.gauss(0.0, 0.05)

        for target in session.targets:
            param_contributions = []
            for param in session.parameters:
                pid = param.param_id
                val = float(parameter_values.get(pid, param.current_value))
                normalized = (val - param.min_value) / max(
                    param.max_value - param.min_value, 0.001
                )
                param_contributions.append(normalized * param.weight)

            if param_contributions:
                base_value = sum(param_contributions) / len(param_contributions)
            else:
                base_value = 0.5

            # Apply target-specific transforms
            if target.goal == OptimizationGoal.TARGET_WIN_RATE:
                metrics[target.target_id] = max(0.0, min(1.0, base_value + noise))
            elif target.goal == OptimizationGoal.MAX_FAIRNESS:
                deviation = abs(base_value - 0.5)
                metrics[target.target_id] = max(0.0, 1.0 - deviation * 2.0 + noise)
            elif target.goal == OptimizationGoal.RESOURCE_FLOW:
                metrics[target.target_id] = max(0.0, base_value * 100.0 + noise * 10.0)
            elif target.goal == OptimizationGoal.PROGRESSION_PACE:
                metrics[target.target_id] = max(0.0, min(1.0, base_value * 0.8 + 0.2 + noise))
            elif target.goal == OptimizationGoal.ENGAGEMENT_CURVE:
                engagement = math.sin(base_value * math.pi) * 0.8 + 0.1
                metrics[target.target_id] = max(0.0, min(1.0, engagement + noise))

        return metrics

    def _compute_fitness(
        self, metrics: Dict[str, float], session: OptimizationSession
    ) -> float:
        """
        Compute an overall fitness score by comparing simulated metrics
        against target values. Higher scores indicate better alignment.
        """
        if not session.targets:
            return 0.0

        total_score = 0.0
        total_weight = 0.0

        for target in session.targets:
            actual = metrics.get(target.target_id, 0.0)
            deviation = abs(actual - target.target_value)
            max_deviation = max(target.target_value, 1.0 - target.target_value, 0.1)
            normalized_deviation = min(deviation / max_deviation, 1.0)
            target_score = max(0.0, 1.0 - normalized_deviation)

            weight = 1.0
            total_score += target_score * weight
            total_weight += weight

        if total_weight == 0.0:
            return 0.0

        return total_score / total_weight

    # ------------------------------------------------------------------
    # Optimization Runner
    # ------------------------------------------------------------------

    def run_optimization(self, session_id: str) -> Optional[OptimizationSession]:
        """
        Run the full iterative optimization process.

        Uses a hill-climbing approach: each iteration mutates the current
        best parameters, simulates the result, and keeps the better
        configuration. Stops on convergence, max iterations, or failure.
        """
        with self._lock:
            session = self._sessions.get(session_id)
            if session is None:
                return None

            if session.status == OptimizationStatus.RUNNING:
                return session

            session.status = OptimizationStatus.RUNNING

            # Build initial parameter values from current defaults
            current_values: Dict[str, Any] = {}
            for param in session.parameters:
                current_values[param.param_id] = param.current_value

            # Run initial baseline simulation
            self.run_simulation(session_id, current_values)
            best_fitness = session.best_result.fitness_score if session.best_result else 0.0
            best_values = dict(current_values)

            convergence_streak = 0
            convergence_threshold = 10
            fitness_history: List[float] = []

            try:
                while session.current_iteration < session.max_iterations:
                    # Mutate parameters
                    mutated_values = self._mutate_parameters(best_values, session)

                    # Run simulation with mutated values
                    result = self.run_simulation(session_id, mutated_values)
                    if result is None:
                        session.status = OptimizationStatus.FAILED
                        return session

                    new_fitness = result.fitness_score

                    # Hill-climbing: keep the better configuration
                    if new_fitness > best_fitness:
                        best_fitness = new_fitness
                        best_values = dict(mutated_values)
                        convergence_streak = 0
                    else:
                        convergence_streak += 1

                    fitness_history.append(best_fitness)

                    # Check for convergence
                    if convergence_streak >= convergence_threshold:
                        if len(fitness_history) >= convergence_threshold:
                            recent = fitness_history[-convergence_threshold:]
                            delta = max(recent) - min(recent)
                            if delta < 0.001:
                                session.status = OptimizationStatus.CONVERGED
                                self._stats["total_optimizations_completed"] += 1
                                return session

                    # Check if fitness is near-perfect
                    if best_fitness >= 0.999:
                        session.status = OptimizationStatus.CONVERGED
                        self._stats["total_optimizations_completed"] += 1
                        return session

                session.status = OptimizationStatus.MAX_ITERATIONS
                self._stats["total_optimizations_completed"] += 1

            except Exception:
                session.status = OptimizationStatus.FAILED

            return session

    def _mutate_parameters(
        self,
        current_values: Dict[str, Any],
        session: OptimizationSession,
    ) -> Dict[str, Any]:
        """
        Mutate parameter values for the next optimization iteration.

        Applies random perturbations proportional to the parameter's step
        size and range, with occasional larger jumps to escape local optima.
        """
        mutated: Dict[str, Any] = {}
        for param in session.parameters:
            current = current_values.get(param.param_id, param.current_value)
            if param.param_type == ParameterType.BOOLEAN:
                if random.random() < 0.1:
                    mutated[param.param_id] = not bool(current)
                else:
                    mutated[param.param_id] = current
            elif param.param_type == ParameterType.ENUMERATION:
                if param.enumeration_options and random.random() < 0.15:
                    mutated[param.param_id] = random.choice(param.enumeration_options)
                else:
                    mutated[param.param_id] = current
            elif param.param_type == ParameterType.INTEGER:
                step = max(1, int(param.step))
                delta = random.randint(-step * 2, step * 2)
                # Occasional larger jump
                if random.random() < 0.05:
                    delta = random.randint(-step * 10, step * 10)
                new_val = int(current) + delta
                mutated[param.param_id] = param.clamp_value(new_val)
            else:
                # FLOAT and CURVE types
                range_size = param.max_value - param.min_value
                delta = random.gauss(0.0, range_size * 0.05)
                # Occasional larger jump
                if random.random() < 0.05:
                    delta = random.gauss(0.0, range_size * 0.2)
                new_val = float(current) + delta
                mutated[param.param_id] = param.clamp_value(new_val)
        return mutated

    # ------------------------------------------------------------------
    # Reporting
    # ------------------------------------------------------------------

    def generate_report(self, session_id: str) -> Optional[BalanceReport]:
        """
        Generate a comprehensive balance report for an optimization session.

        Compares before and after metrics, computes improvement percentage,
        and provides actionable recommendations based on parameter changes.
        """
        with self._lock:
            session = self._sessions.get(session_id)
            if session is None:
                return None

            if not session.history:
                return None

            # Before metrics: first simulation result
            first_result = session.history[0]
            before_metrics = dict(first_result.metrics)

            # After metrics: best result or last result
            if session.best_result is not None:
                after_metrics = dict(session.best_result.metrics)
            else:
                after_metrics = dict(session.history[-1].metrics)

            # Compute parameter changes
            parameter_changes: Dict[str, dict] = {}
            best_values = {}
            if session.best_result is not None:
                best_values = session.best_result.parameter_values

            for param in session.parameters:
                old_val = first_result.parameter_values.get(param.param_id, param.current_value)
                new_val = best_values.get(param.param_id, old_val)
                if old_val != new_val:
                    parameter_changes[param.param_id] = {
                        "name": param.name,
                        "domain": param.domain.value,
                        "old_value": old_val,
                        "new_value": new_val,
                        "param_type": param.param_type.value,
                    }

            # Compute improvement percentage
            before_fitness = first_result.fitness_score
            after_fitness = session.best_result.fitness_score if session.best_result else before_fitness
            if before_fitness > 0.0:
                improvement_pct = ((after_fitness - before_fitness) / before_fitness) * 100.0
            else:
                improvement_pct = after_fitness * 100.0 if after_fitness > 0.0 else 0.0

            # Generate recommendations
            recommendations = self._generate_recommendations(
                session, parameter_changes, after_metrics
            )

            # Build summary
            summary = (
                f"Optimization session '{session.name}' completed with status "
                f"'{session.status.value}' after {session.current_iteration} iterations. "
                f"Fitness improved from {before_fitness:.4f} to {after_fitness:.4f} "
                f"({improvement_pct:+.1f}%). "
                f"{len(parameter_changes)} parameters were adjusted."
            )

            report = BalanceReport(
                session_id=session_id,
                summary=summary,
                recommendations=recommendations,
                before_metrics=before_metrics,
                after_metrics=after_metrics,
                parameter_changes=parameter_changes,
                improvement_pct=improvement_pct,
            )
            return report

    def _generate_recommendations(
        self,
        session: OptimizationSession,
        parameter_changes: Dict[str, dict],
        after_metrics: Dict[str, float],
    ) -> List[str]:
        """Generate human-readable recommendations from optimization results."""
        recommendations: List[str] = []

        for pid, change in parameter_changes.items():
            old_val = change["old_value"]
            new_val = change["new_value"]
            name = change["name"]
            if isinstance(old_val, (int, float)) and isinstance(new_val, (int, float)):
                direction = "increased" if new_val > old_val else "decreased"
                recommendations.append(
                    f"Adjust '{name}' from {old_val} to {new_val} ({direction} by "
                    f"{abs(new_val - old_val):.3f}) to improve balance."
                )
            else:
                recommendations.append(
                    f"Update '{name}' from '{old_val}' to '{new_val}'."
                )

        for target in session.targets:
            actual = after_metrics.get(target.target_id, 0.0)
            if not target.is_satisfied(actual):
                gap = actual - target.target_value
                direction = "above" if gap > 0 else "below"
                recommendations.append(
                    f"Target '{target.name}' is {direction} target by "
                    f"{abs(gap):.4f} (actual: {actual:.4f}, target: "
                    f"{target.target_value:.4f}). Further tuning recommended."
                )

        if not recommendations:
            recommendations.append(
                "All targets are within tolerance. The current balance configuration "
                "is optimal for the defined goals."
            )

        return recommendations

    # ------------------------------------------------------------------
    # Analysis Utilities
    # ------------------------------------------------------------------

    def parameter_sensitivity(self, session_id: str) -> Optional[Dict[str, float]]:
        """
        Compute sensitivity scores for each parameter in a session.

        Sensitivity measures how much the fitness score changes when a
        parameter is perturbed, indicating how influential each parameter is.
        """
        with self._lock:
            session = self._sessions.get(session_id)
            if session is None or not session.parameters:
                return None

            sensitivity: Dict[str, float] = {}
            base_values: Dict[str, Any] = {}
            for param in session.parameters:
                base_values[param.param_id] = param.current_value

            # Baseline fitness
            base_result = self.run_simulation(session_id, base_values)
            base_fitness = base_result.fitness_score if base_result else 0.0

            for param in session.parameters:
                perturbed = dict(base_values)
                if param.param_type == ParameterType.BOOLEAN:
                    perturbed[param.param_id] = not bool(base_values[param.param_id])
                elif param.param_type == ParameterType.INTEGER:
                    delta = max(1, int(param.step * 5))
                    perturbed[param.param_id] = param.clamp_value(
                        int(base_values[param.param_id]) + delta
                    )
                else:
                    range_size = param.max_value - param.min_value
                    delta = range_size * 0.1
                    perturbed[param.param_id] = param.clamp_value(
                        float(base_values[param.param_id]) + delta
                    )

                perturbed_result = self.run_simulation(session_id, perturbed)
                perturbed_fitness = perturbed_result.fitness_score if perturbed_result else base_fitness

                sensitivity[param.param_id] = abs(perturbed_fitness - base_fitness)

            return sensitivity

    def find_optimal_range(
        self, param_id: str, target_id: str, steps: int = 10
    ) -> Optional[List[Dict[str, Any]]]:
        """
        Scan a parameter's range and find the value that best satisfies
        a specific target. Returns a list of {value, fitness} entries.
        """
        with self._lock:
            parameter = self._parameters.get(param_id)
            target = self._targets.get(target_id)
            if parameter is None or target is None:
                return None

            results: List[Dict[str, Any]] = []
            param_type = parameter.param_type

            if param_type == ParameterType.BOOLEAN:
                for val in [False, True]:
                    test_metrics = {
                        target.target_id: self._compute_single_metric(
                            parameter, val, target
                        )
                    }
                    fitness = max(
                        0.0,
                        1.0
                        - abs(test_metrics[target.target_id] - target.target_value)
                        / max(target.target_value, 1.0 - target.target_value, 0.1),
                    )
                    results.append({"value": val, "fitness": fitness})
            elif param_type == ParameterType.ENUMERATION:
                options = parameter.enumeration_options or []
                for val in options:
                    test_metrics = {
                        target.target_id: self._compute_single_metric(
                            parameter, val, target
                        )
                    }
                    fitness = max(
                        0.0,
                        1.0
                        - abs(test_metrics[target.target_id] - target.target_value)
                        / max(target.target_value, 1.0 - target.target_value, 0.1),
                    )
                    results.append({"value": val, "fitness": fitness})
            elif param_type == ParameterType.INTEGER:
                step_size = max(1, int((parameter.max_value - parameter.min_value) / steps))
                val = int(parameter.min_value)
                while val <= int(parameter.max_value):
                    test_metrics = {
                        target.target_id: self._compute_single_metric(
                            parameter, val, target
                        )
                    }
                    fitness = max(
                        0.0,
                        1.0
                        - abs(test_metrics[target.target_id] - target.target_value)
                        / max(target.target_value, 1.0 - target.target_value, 0.1),
                    )
                    results.append({"value": val, "fitness": fitness})
                    val += step_size
            else:
                # FLOAT and CURVE
                range_size = parameter.max_value - parameter.min_value
                step_size = range_size / max(steps, 1)
                val = parameter.min_value
                while val <= parameter.max_value:
                    test_metrics = {
                        target.target_id: self._compute_single_metric(
                            parameter, val, target
                        )
                    }
                    fitness = max(
                        0.0,
                        1.0
                        - abs(test_metrics[target.target_id] - target.target_value)
                        / max(target.target_value, 1.0 - target.target_value, 0.1),
                    )
                    results.append({"value": round(val, 4), "fitness": round(fitness, 4)})
                    val += step_size

            results.sort(key=lambda r: r["fitness"], reverse=True)
            return results

    def _compute_single_metric(
        self,
        parameter: GameParameter,
        value: Any,
        target: BalanceTarget,
    ) -> float:
        """Compute a single metric value for a parameter-target pair."""
        if parameter.param_type == ParameterType.BOOLEAN:
            normalized = 1.0 if value else 0.0
        elif parameter.param_type == ParameterType.ENUMERATION:
            options = parameter.enumeration_options or []
            if options and value in options:
                normalized = options.index(value) / max(len(options) - 1, 1)
            else:
                normalized = 0.5
        else:
            normalized = (float(value) - parameter.min_value) / max(
                parameter.max_value - parameter.min_value, 0.001
            )

        if target.goal == OptimizationGoal.TARGET_WIN_RATE:
            return max(0.0, min(1.0, normalized))
        elif target.goal == OptimizationGoal.MAX_FAIRNESS:
            deviation = abs(normalized - 0.5)
            return max(0.0, 1.0 - deviation * 2.0)
        elif target.goal == OptimizationGoal.RESOURCE_FLOW:
            return max(0.0, normalized * 100.0)
        elif target.goal == OptimizationGoal.PROGRESSION_PACE:
            return max(0.0, min(1.0, normalized * 0.8 + 0.2))
        elif target.goal == OptimizationGoal.ENGAGEMENT_CURVE:
            return max(0.0, min(1.0, math.sin(normalized * math.pi) * 0.8 + 0.1))
        return normalized

    def compare_sessions(self, session_ids: List[str]) -> Dict[str, Any]:
        """
        Compare multiple optimization sessions side by side.

        Returns a dictionary with comparative metrics for each session
        including fitness scores, iterations, convergence status, and
        parameter counts.
        """
        with self._lock:
            comparison: Dict[str, Any] = {
                "session_count": len(session_ids),
                "sessions": [],
                "best_overall": None,
                "summary": "",
            }

            best_fitness = -1.0
            best_id = None

            for sid in session_ids:
                session = self._sessions.get(sid)
                if session is None:
                    continue

                best_fit = session.best_result.fitness_score if session.best_result else 0.0
                entry = {
                    "session_id": session.session_id,
                    "name": session.name,
                    "domain": session.domain.value,
                    "status": session.status.value,
                    "iterations": session.current_iteration,
                    "max_iterations": session.max_iterations,
                    "best_fitness": best_fit,
                    "parameter_count": len(session.parameters),
                    "target_count": len(session.targets),
                    "history_length": len(session.history),
                }
                comparison["sessions"].append(entry)

                if best_fit > best_fitness:
                    best_fitness = best_fit
                    best_id = session.session_id

            comparison["best_overall"] = best_id
            if comparison["sessions"]:
                comparison["summary"] = (
                    f"Compared {len(comparison['sessions'])} sessions. "
                    f"Best session: {best_id} with fitness {best_fitness:.4f}."
                )
            else:
                comparison["summary"] = "No valid sessions found for comparison."

            return comparison

    def export_parameters(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Export optimized parameters from a session as a configuration dict.

        Returns the best-known parameter values in a format suitable for
        direct use in game configuration files.
        """
        with self._lock:
            session = self._sessions.get(session_id)
            if session is None:
                return None

            exported: Dict[str, Any] = {
                "session_id": session.session_id,
                "session_name": session.name,
                "domain": session.domain.value,
                "status": session.status.value,
                "exported_at": _time_module.time(),
                "parameters": {},
            }

            if session.best_result is not None:
                source_values = session.best_result.parameter_values
            else:
                source_values = {
                    p.param_id: p.current_value for p in session.parameters
                }

            for param in session.parameters:
                val = source_values.get(param.param_id, param.current_value)
                exported["parameters"][param.param_id] = {
                    "name": param.name,
                    "type": param.param_type.value,
                    "value": val,
                    "domain": param.domain.value,
                    "description": param.description,
                }

            return exported

    # ------------------------------------------------------------------
    # Stats
    # ------------------------------------------------------------------

    def get_stats(self) -> Dict[str, Any]:
        """Return aggregate statistics for the balance optimizer."""
        with self._lock:
            active_sessions = sum(
                1 for s in self._sessions.values()
                if s.status == OptimizationStatus.RUNNING
            )
            converged_sessions = sum(
                1 for s in self._sessions.values()
                if s.status == OptimizationStatus.CONVERGED
            )
            failed_sessions = sum(
                1 for s in self._sessions.values()
                if s.status == OptimizationStatus.FAILED
            )

            domain_counts: Dict[str, int] = {}
            for s in self._sessions.values():
                d = s.domain.value
                domain_counts[d] = domain_counts.get(d, 0) + 1

            return {
                "total_parameters": len(self._parameters),
                "total_targets": len(self._targets),
                "total_sessions": len(self._sessions),
                "active_sessions": active_sessions,
                "converged_sessions": converged_sessions,
                "failed_sessions": failed_sessions,
                "sessions_by_domain": domain_counts,
                "total_sessions_created": self._stats["total_sessions_created"],
                "total_simulations_run": self._stats["total_simulations_run"],
                "total_optimizations_completed": self._stats["total_optimizations_completed"],
                "total_parameters_defined": self._stats["total_parameters_defined"],
                "total_targets_defined": self._stats["total_targets_defined"],
            }


# ------------------------------------------------------------------
# Module-level accessor
# ------------------------------------------------------------------


def get_balance_optimizer() -> AgentBalanceOptimizer:
    """Return the singleton AgentBalanceOptimizer instance."""
    return AgentBalanceOptimizer.get_instance()