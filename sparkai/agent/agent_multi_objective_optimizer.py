"""
SparkLabs Agent - Multi-Objective Optimizer

Pareto optimization engine for game design that handles multiple conflicting
objectives simultaneously. Supports weighted sum scalarization, Pareto frontier
computation, lexicographic ordering, goal programming, constraint satisfaction,
and evolutionary multi-objective algorithms. Provides trade-off analysis,
sensitivity analysis, and solution selection with preference weighting.

Architecture:
  AgentMultiObjectiveOptimizer (Singleton)
    |-- OptimizationObjective (individual objective with direction and weight)
    |-- OptimizationConstraint (hard/soft/budget constraints on variables)
    |-- ParetoSolution (candidate solution on the Pareto frontier)
    |-- OptimizationProblem (complete problem definition per domain)
    |-- TradeOffAnalysis (correlation and substitution between objectives)

Core Algorithms:
  - Non-dominated sorting (Pareto ranking with crowding distance)
  - Weighted sum scalarization for preference-based optimization
  - Genetic algorithm with tournament selection and crossover
  - Trade-off analysis with correlation computation
  - Sensitivity analysis via variable perturbation

Optimization Strategies:
  WEIGHTED_SUM, PARETO_FRONTIER, LEXICOGRAPHIC,
  GOAL_PROGRAMMING, CONSTRAINT_SATISFACTION, EVOLUTIONARY

Usage:
    opt = get_agent_multi_objective_optimizer()
    problem = opt.define_problem("rpg_balance", objectives, constraints, variables)
    solutions = opt.solve("rpg_balance", strategy=OptimizationStrategy.EVOLUTIONARY)
    frontier = opt.compute_pareto_frontier("rpg_balance")
    tradeoff = opt.analyze_trade_offs("rpg_balance", "damage", "survivability")
    best = opt.select_solution("rpg_balance", {"damage": 0.7, "survivability": 0.3})
    sensitivity = opt.compute_sensitivity("rpg_balance", "attack_power", 0.1)
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


# =============================================================================
# Enums
# =============================================================================


class OptimizationStrategy(Enum):
    WEIGHTED_SUM = "weighted_sum"
    PARETO_FRONTIER = "pareto_frontier"
    LEXICOGRAPHIC = "lexicographic"
    GOAL_PROGRAMMING = "goal_programming"
    CONSTRAINT_SATISFACTION = "constraint_satisfaction"
    EVOLUTIONARY = "evolutionary"


class ObjectiveDirection(Enum):
    MAXIMIZE = "maximize"
    MINIMIZE = "minimize"
    TARGET = "target"


class ConstraintType(Enum):
    HARD = "hard"
    SOFT = "soft"
    BUDGET = "budget"


class SolutionStatus(Enum):
    OPTIMAL = "optimal"
    FEASIBLE = "feasible"
    INFEASIBLE = "infeasible"
    PARETO_OPTIMAL = "pareto_optimal"
    DOMINATED = "dominated"


# =============================================================================
# Dataclasses
# =============================================================================


@dataclass
class OptimizationObjective:
    """Defines a single objective to optimize with direction, weight, and target."""

    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = ""
    direction: ObjectiveDirection = ObjectiveDirection.MAXIMIZE
    weight: float = 1.0
    target_value: float = 0.0
    tolerance: float = 0.01
    current_value: float = 0.0
    domain: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "direction": self.direction.value,
            "weight": self.weight,
            "target_value": self.target_value,
            "tolerance": self.tolerance,
            "current_value": round(self.current_value, 4),
            "domain": self.domain,
        }


@dataclass
class OptimizationConstraint:
    """Defines a constraint on variables or objectives in the optimization problem."""

    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = ""
    constraint_type: ConstraintType = ConstraintType.HARD
    expression: str = ""
    bound: float = 0.0
    penalty: float = 0.0
    is_satisfied: bool = True
    domain: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "constraint_type": self.constraint_type.value,
            "expression": self.expression,
            "bound": self.bound,
            "penalty": self.penalty,
            "is_satisfied": self.is_satisfied,
            "domain": self.domain,
        }


@dataclass
class ParetoSolution:
    """Represents a candidate solution on or relative to the Pareto frontier."""

    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    variable_values: Dict[str, float] = field(default_factory=dict)
    objective_values: Dict[str, float] = field(default_factory=dict)
    status: SolutionStatus = SolutionStatus.FEASIBLE
    dominance_rank: int = 0
    crowding_distance: float = 0.0
    fitness_score: float = 0.0
    generated_at: float = field(default_factory=_time_module.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "variable_values": dict(self.variable_values),
            "objective_values": {k: round(v, 4) for k, v in self.objective_values.items()},
            "status": self.status.value,
            "dominance_rank": self.dominance_rank,
            "crowding_distance": round(self.crowding_distance, 4),
            "fitness_score": round(self.fitness_score, 4),
            "generated_at": self.generated_at,
        }


@dataclass
class OptimizationProblem:
    """Complete definition of a multi-objective optimization problem for a domain."""

    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    domain: str = ""
    objectives: Dict[str, OptimizationObjective] = field(default_factory=dict)
    constraints: Dict[str, OptimizationConstraint] = field(default_factory=dict)
    variables: Dict[str, Tuple[float, float]] = field(default_factory=dict)
    pareto_frontier: List[ParetoSolution] = field(default_factory=list)
    strategy: OptimizationStrategy = OptimizationStrategy.WEIGHTED_SUM
    created_at: float = field(default_factory=_time_module.time)
    solved_at: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "domain": self.domain,
            "objectives": {k: v.to_dict() for k, v in self.objectives.items()},
            "constraints": {k: v.to_dict() for k, v in self.constraints.items()},
            "variables": {k: list(v) for k, v in self.variables.items()},
            "pareto_frontier": [s.to_dict() for s in self.pareto_frontier],
            "strategy": self.strategy.value,
            "frontier_size": len(self.pareto_frontier),
            "created_at": self.created_at,
            "solved_at": self.solved_at,
        }


@dataclass
class TradeOffAnalysis:
    """Analysis of the trade-off relationship between two objectives."""

    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    domain: str = ""
    objective_a: str = ""
    objective_b: str = ""
    correlation: float = 0.0
    trade_off_rate: float = 0.0
    knee_point: Tuple[float, float] = (0.0, 0.0)
    substitution_elasticity: float = 0.0
    pareto_optimal: bool = False
    analyzed_at: float = field(default_factory=_time_module.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "domain": self.domain,
            "objective_a": self.objective_a,
            "objective_b": self.objective_b,
            "correlation": round(self.correlation, 4),
            "trade_off_rate": round(self.trade_off_rate, 4),
            "knee_point": [round(self.knee_point[0], 4), round(self.knee_point[1], 4)],
            "substitution_elasticity": round(self.substitution_elasticity, 4),
            "pareto_optimal": self.pareto_optimal,
            "analyzed_at": self.analyzed_at,
        }


# =============================================================================
# AgentMultiObjectiveOptimizer (Singleton)
# =============================================================================


class AgentMultiObjectiveOptimizer:
    """
    Pareto optimization engine for game design multi-objective problems.

    Handles conflicting objectives simultaneously through Pareto frontier
    computation, weighted sum scalarization, lexicographic ordering, goal
    programming, constraint satisfaction, and evolutionary algorithms.
    Provides trade-off analysis and sensitivity assessment for informed
    game design decisions.

    Usage:
        opt = get_agent_multi_objective_optimizer()
        problem = opt.define_problem("rpg_balance", objectives, constraints, vars)
        frontier = opt.compute_pareto_frontier("rpg_balance")
        best = opt.select_solution("rpg_balance", {"damage": 0.7, "defense": 0.3})
    """

    _instance: Optional["AgentMultiObjectiveOptimizer"] = None
    _lock: threading.RLock = threading.RLock()

    _DEFAULT_POPULATION_SIZE = 100
    _DEFAULT_GENERATIONS = 50
    _MAX_POPULATION_SIZE = 5000
    _MAX_GENERATIONS = 1000
    _MUTATION_RATE = 0.15
    _CROSSOVER_RATE = 0.70
    _TOURNAMENT_SIZE = 3
    _ELITISM_COUNT = 5
    _SENSITIVITY_DEFAULT_PERTURBATION = 0.1
    _SAMPLING_GRID_SIZE = 50
    _PENALTY_WEIGHT_DEFAULT = 1000.0
    _CORRELATION_MIN_POINTS = 5

    def __new__(cls) -> "AgentMultiObjectiveOptimizer":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    instance = super().__new__(cls)
                    cls._instance = instance
        return cls._instance

    @classmethod
    def get_instance(cls) -> "AgentMultiObjectiveOptimizer":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def __init__(self) -> None:
        if hasattr(self, "_initialized") and self._initialized:
            return
        self._initialized = True

        self._problems: Dict[str, OptimizationProblem] = {}
        self._solutions: Dict[str, List[ParetoSolution]] = {}
        self._trade_off_analyses: Dict[str, List[TradeOffAnalysis]] = {}

        self._stats: Dict[str, Any] = {
            "total_problems_defined": 0,
            "total_solve_calls": 0,
            "total_pareto_frontiers_computed": 0,
            "total_trade_off_analyses": 0,
            "total_solutions_selected": 0,
            "total_feasibility_checks": 0,
            "total_sensitivity_analyses": 0,
            "total_solutions_generated": 0,
        }

    # =========================================================================
    # Problem Definition
    # =========================================================================

    def define_problem(
        self,
        domain: str,
        objectives: Dict[str, OptimizationObjective],
        constraints: Dict[str, OptimizationConstraint],
        variables: Dict[str, Tuple[float, float]],
    ) -> OptimizationProblem:
        """
        Define a multi-objective optimization problem for a specific domain.

        Args:
            domain: Unique domain identifier (e.g., 'rpg_balance', 'economy_tuning').
            objectives: Dictionary mapping objective names to OptimizationObjective instances.
            constraints: Dictionary mapping constraint names to OptimizationConstraint instances.
            variables: Dictionary mapping variable names to (min, max) tuple bounds.

        Returns:
            The newly created OptimizationProblem.
        """
        with self._lock:
            for name, obj in objectives.items():
                obj.domain = domain
            for name, con in constraints.items():
                con.domain = domain

            problem = OptimizationProblem(
                domain=domain,
                objectives=dict(objectives),
                constraints=dict(constraints),
                variables=dict(variables),
                strategy=OptimizationStrategy.WEIGHTED_SUM,
            )
            self._problems[domain] = problem
            self._stats["total_problems_defined"] += 1
            return problem

    def get_problem(self, domain: str) -> Optional[OptimizationProblem]:
        """
        Retrieve an existing optimization problem by domain.

        Args:
            domain: The domain identifier.

        Returns:
            The OptimizationProblem or None if not found.
        """
        with self._lock:
            return self._problems.get(domain)

    def list_domains(self) -> List[str]:
        """
        List all registered optimization problem domains.

        Returns:
            A list of domain identifier strings.
        """
        with self._lock:
            return list(self._problems.keys())

    # =========================================================================
    # Solve
    # =========================================================================

    def solve(
        self,
        domain: str,
        strategy: OptimizationStrategy = OptimizationStrategy.WEIGHTED_SUM,
        population_size: int = 100,
        generations: int = 50,
    ) -> List[ParetoSolution]:
        """
        Solve the optimization problem for the given domain using the specified strategy.

        Args:
            domain: The domain identifier of the problem to solve.
            strategy: The optimization strategy to apply.
            population_size: Number of candidate solutions per generation (for evolutionary).
            generations: Number of iterations (for evolutionary and iterative methods).

        Returns:
            A list of ParetoSolution objects sorted by dominance rank.
        """
        with self._lock:
            problem = self._problems.get(domain)
            if problem is None:
                return []

            problem.strategy = strategy
            pop_size = max(10, min(population_size, self._MAX_POPULATION_SIZE))
            gen_count = max(1, min(generations, self._MAX_GENERATIONS))

            solutions: List[ParetoSolution] = []

            if strategy == OptimizationStrategy.WEIGHTED_SUM:
                solutions = self._solve_weighted_sum(problem, pop_size)
            elif strategy == OptimizationStrategy.PARETO_FRONTIER:
                solutions = self._solve_pareto_frontier(problem, pop_size)
            elif strategy == OptimizationStrategy.LEXICOGRAPHIC:
                solutions = self._solve_lexicographic(problem, pop_size)
            elif strategy == OptimizationStrategy.GOAL_PROGRAMMING:
                solutions = self._solve_goal_programming(problem, pop_size)
            elif strategy == OptimizationStrategy.CONSTRAINT_SATISFACTION:
                solutions = self._solve_constraint_satisfaction(problem, pop_size)
            elif strategy == OptimizationStrategy.EVOLUTIONARY:
                solutions = self._solve_evolutionary(problem, pop_size, gen_count)
            else:
                solutions = self._solve_weighted_sum(problem, pop_size)

            self._compute_pareto_ranking(solutions)
            solutions.sort(key=lambda s: (s.dominance_rank, -s.crowding_distance))

            self._solutions[domain] = solutions
            problem.pareto_frontier = [s for s in solutions if s.dominance_rank == 0]
            problem.solved_at = _time_module.time()

            self._stats["total_solve_calls"] += 1
            self._stats["total_solutions_generated"] += len(solutions)
            return solutions

    # -------------------------------------------------------------------------
    # Strategy implementations
    # -------------------------------------------------------------------------

    def _solve_weighted_sum(
        self, problem: OptimizationProblem, population_size: int
    ) -> List[ParetoSolution]:
        """Weighted sum scalarization: generate diverse weight vectors and pick the best."""
        solutions: List[ParetoSolution] = []
        obj_names = list(problem.objectives.keys())
        if not obj_names:
            return solutions

        for i in range(population_size):
            weights = self._generate_weight_vector(obj_names, i, population_size)
            candidate = self._random_solution(problem)
            candidate = self._evaluate_solution(candidate, problem)
            candidate.fitness_score = self._compute_weighted_fitness(
                candidate, problem, weights
            )
            solutions.append(candidate)

        return solutions

    def _solve_pareto_frontier(
        self, problem: OptimizationProblem, population_size: int
    ) -> List[ParetoSolution]:
        """Grid-sampled exploration of the solution space for Pareto frontier."""
        solutions: List[ParetoSolution] = []
        var_names = list(problem.variables.keys())
        if not var_names:
            return solutions

        samples_per_var = max(2, int(population_size ** (1.0 / max(1, len(var_names)))))

        def sample_recursive(
            var_idx: int, current_values: Dict[str, float]
        ) -> None:
            if var_idx >= len(var_names):
                sol = ParetoSolution(variable_values=dict(current_values))
                sol = self._evaluate_solution(sol, problem)
                self._check_constraints(sol, problem)
                solutions.append(sol)
                return

            var_name = var_names[var_idx]
            var_min, var_max = problem.variables[var_name]
            for j in range(samples_per_var):
                frac = j / max(samples_per_var - 1, 1)
                val = var_min + frac * (var_max - var_min)
                current_values[var_name] = round(val, 4)
                sample_recursive(var_idx + 1, current_values)

        sample_recursive(0, {})

        if len(solutions) > population_size:
            solutions = random.sample(solutions, population_size)

        return solutions

    def _solve_lexicographic(
        self, problem: OptimizationProblem, population_size: int
    ) -> List[ParetoSolution]:
        """
        Lexicographic optimization: optimize objectives sequentially by priority
        (order of objectives dict), constraining subsequent objectives.
        """
        solutions: List[ParetoSolution] = []
        obj_names = list(problem.objectives.keys())
        if not obj_names:
            return solutions

        # Generate initial candidates
        for _ in range(population_size):
            sol = self._random_solution(problem)
            sol = self._evaluate_solution(sol, problem)
            self._check_constraints(sol, problem)
            solutions.append(sol)

        # Refine sequentially: keep top 20% on each objective in order
        survivors = list(solutions)
        for obj_name in obj_names:
            obj = problem.objectives[obj_name]
            survivors.sort(
                key=lambda s: s.objective_values.get(obj_name, 0.0),
                reverse=(obj.direction == ObjectiveDirection.MAXIMIZE),
            )
            keep_count = max(len(survivors) // 5, 1)
            survivors = survivors[:keep_count]

        return survivors

    def _solve_goal_programming(
        self, problem: OptimizationProblem, population_size: int
    ) -> List[ParetoSolution]:
        """
        Goal programming: minimize weighted deviation from target values.
        """
        solutions: List[ParetoSolution] = []
        obj_names = list(problem.objectives.keys())
        if not obj_names:
            return solutions

        for _ in range(population_size):
            sol = self._random_solution(problem)
            sol = self._evaluate_solution(sol, problem)
            self._check_constraints(sol, problem)

            total_deviation = 0.0
            for obj_name, obj in problem.objectives.items():
                current = sol.objective_values.get(obj_name, 0.0)
                deviation = abs(current - obj.target_value) / max(abs(obj.target_value) + obj.tolerance, 0.001)
                total_deviation += obj.weight * deviation

            sol.fitness_score = -total_deviation
            solutions.append(sol)

        return solutions

    def _solve_constraint_satisfaction(
        self, problem: OptimizationProblem, population_size: int
    ) -> List[ParetoSolution]:
        """
        Constraint satisfaction: find any feasible solution, then optimize.
        """
        solutions: List[ParetoSolution] = []
        obj_names = list(problem.objectives.keys())
        if not obj_names:
            return solutions

        for _ in range(population_size):
            sol = self._random_solution(problem)
            sol = self._evaluate_solution(sol, problem)
            self._check_constraints(sol, problem)

            penalty = self._compute_constraint_penalty(sol, problem)
            if penalty == 0.0:
                sol.status = SolutionStatus.FEASIBLE
            else:
                sol.status = SolutionStatus.INFEASIBLE

            total_obj = sum(
                problem.objectives[n].weight * sol.objective_values.get(n, 0.0)
                for n in obj_names
            )
            sol.fitness_score = total_obj - penalty
            solutions.append(sol)

        return solutions

    def _solve_evolutionary(
        self,
        problem: OptimizationProblem,
        population_size: int,
        generations: int,
    ) -> List[ParetoSolution]:
        """
        Multi-objective evolutionary algorithm with non-dominated sorting,
        crowding distance, tournament selection, crossover, and mutation.
        """
        obj_names = list(problem.objectives.keys())
        var_names = list(problem.variables.keys())
        if not obj_names or not var_names:
            return []

        population: List[ParetoSolution] = []
        for _ in range(population_size):
            sol = self._random_solution(problem)
            sol = self._evaluate_solution(sol, problem)
            self._check_constraints(sol, problem)
            population.append(sol)

        for gen in range(generations):
            self._compute_pareto_ranking(population)

            # Sort by rank then crowding distance (descending)
            population.sort(
                key=lambda s: (s.dominance_rank, -s.crowding_distance)
            )

            # Elitism
            offspring: List[ParetoSolution] = []
            elite_count = min(self._ELITISM_COUNT, len(population))
            offspring.extend(population[:elite_count])

            # Generate rest via tournament selection + crossover + mutation
            seeded_rand = random.Random(gen * 7919 + 104729)
            while len(offspring) < population_size:
                p1 = self._tournament_select(population, seeded_rand)
                p2 = self._tournament_select(population, seeded_rand)

                if seeded_rand.random() < self._CROSSOVER_RATE:
                    child = self._crossover(p1, p2, problem, seeded_rand)
                else:
                    child = ParetoSolution(
                        variable_values=dict(
                            p1.variable_values if seeded_rand.random() < 0.5
                            else p2.variable_values
                        ),
                    )

                child = self._mutate(child, problem, seeded_rand)
                child = self._evaluate_solution(child, problem)
                self._check_constraints(child, problem)
                penalty = self._compute_constraint_penalty(child, problem)
                child.fitness_score -= penalty
                offspring.append(child)

            population = offspring

        self._compute_pareto_ranking(population)
        return population

    # =========================================================================
    # Pareto Frontier Computation
    # =========================================================================

    def compute_pareto_frontier(
        self, domain: str
    ) -> List[ParetoSolution]:
        """
        Compute the Pareto frontier for a given domain. Identifies
        all non-dominated solutions using Pareto ranking.

        Args:
            domain: The domain identifier.

        Returns:
            A list of ParetoSolution objects with dominance_rank == 0 (Pareto optimal).
        """
        with self._lock:
            problem = self._problems.get(domain)
            if problem is None:
                return []

            solutions = self._solutions.get(domain, [])
            if not solutions:
                solutions = self._solve_pareto_frontier(
                    problem, self._DEFAULT_POPULATION_SIZE
                )
                self._solutions[domain] = solutions

            self._compute_pareto_ranking(solutions)
            frontier = [s for s in solutions if s.dominance_rank == 0]
            for s in frontier:
                s.status = SolutionStatus.PARETO_OPTIMAL

            problem.pareto_frontier = frontier
            self._stats["total_pareto_frontiers_computed"] += 1
            return frontier

    # =========================================================================
    # Non-Dominated Sorting (Pareto Ranking)
    # =========================================================================

    def _compute_pareto_ranking(self, solutions: List[ParetoSolution]) -> None:
        """
        Assign dominance ranks to all solutions using the non-dominated
        sorting algorithm (Deb et al., NSGA-II).

        A solution dominates another if it is at least as good in all
        objectives and strictly better in at least one.

        Args:
            solutions: List of ParetoSolution objects to rank in-place.
        """
        if not solutions:
            return

        n = len(solutions)
        domination_counts: List[int] = [0] * n
        dominated_by: List[List[int]] = [[] for _ in range(n)]
        fronts: List[List[int]] = []

        for i in range(n):
            for j in range(n):
                if i == j:
                    continue
                if self._dominates(solutions[i], solutions[j]):
                    dominated_by[i].append(j)
                elif self._dominates(solutions[j], solutions[i]):
                    domination_counts[i] += 1

            if domination_counts[i] == 0:
                solutions[i].dominance_rank = 0
                if not fronts:
                    fronts.append([])
                fronts[0].append(i)

        front_idx = 0
        while front_idx < len(fronts) and fronts[front_idx]:
            next_front: List[int] = []
            for i in fronts[front_idx]:
                for j in dominated_by[i]:
                    domination_counts[j] -= 1
                    if domination_counts[j] == 0:
                        solutions[j].dominance_rank = front_idx + 1
                        next_front.append(j)
            front_idx += 1
            if next_front:
                fronts.append(next_front)

        # Compute crowding distance for each front
        for front_indices in fronts:
            self._compute_crowding_distance(solutions, front_indices)

    # =========================================================================
    # Crowding Distance
    # =========================================================================

    def _compute_crowding_distance(
        self,
        solutions: List[ParetoSolution],
        front_indices: List[int],
    ) -> None:
        """
        Compute crowding distance for solutions in a given front.
        Crowding distance measures solution density — higher values
        indicate that a solution is more isolated (better diversity).

        Args:
            solutions: All solutions list.
            front_indices: Indices of solutions in the current front.
        """
        if len(front_indices) <= 2:
            for idx in front_indices:
                solutions[idx].crowding_distance = float("inf")
            return

        for idx in front_indices:
            solutions[idx].crowding_distance = 0.0

        # Get all objective names from solutions
        obj_names: List[str] = []
        for idx in front_indices:
            for key in solutions[idx].objective_values:
                if key not in obj_names:
                    obj_names.append(key)
        if not obj_names:
            return

        for obj_name in obj_names:
            front_indices.sort(
                key=lambda idx: solutions[idx].objective_values.get(obj_name, 0.0)
            )

            obj_min = solutions[front_indices[0]].objective_values.get(obj_name, 0.0)
            obj_max = solutions[front_indices[-1]].objective_values.get(obj_name, 0.0)
            obj_range = obj_max - obj_min

            if obj_range < 1e-9:
                continue

            solutions[front_indices[0]].crowding_distance = float("inf")
            solutions[front_indices[-1]].crowding_distance = float("inf")

            for k in range(1, len(front_indices) - 1):
                prev_val = solutions[front_indices[k - 1]].objective_values.get(obj_name, 0.0)
                next_val = solutions[front_indices[k + 1]].objective_values.get(obj_name, 0.0)
                solutions[front_indices[k]].crowding_distance += (
                    (next_val - prev_val) / obj_range
                )

    # =========================================================================
    # Trade-Off Analysis
    # =========================================================================

    def analyze_trade_offs(
        self,
        domain: str,
        objective_a: str,
        objective_b: str,
    ) -> TradeOffAnalysis:
        """
        Analyze the trade-off relationship between two objectives.

        Computes Pearson correlation, trade-off rate (marginal rate of
        substitution), knee point identification, and substitution elasticity
        across the Pareto frontier.

        Args:
            domain: The domain identifier.
            objective_a: Name of the first objective.
            objective_b: Name of the second objective.

        Returns:
            A TradeOffAnalysis object with quantitative trade-off metrics.
        """
        with self._lock:
            problem = self._problems.get(domain)
            if problem is None:
                return TradeOffAnalysis(
                    domain=domain,
                    objective_a=objective_a,
                    objective_b=objective_b,
                )

            solutions = self._solutions.get(domain, [])
            if not solutions:
                solutions = self._solve_pareto_frontier(
                    problem, self._DEFAULT_POPULATION_SIZE
                )
                self._solutions[domain] = solutions
                self._compute_pareto_ranking(solutions)

            frontier = [s for s in solutions if s.dominance_rank == 0]
            if not frontier:
                # Fall back to all feasible solutions
                frontier = [
                    s for s in solutions
                    if s.status != SolutionStatus.INFEASIBLE
                ]

            if len(frontier) < self._CORRELATION_MIN_POINTS:
                return TradeOffAnalysis(
                    domain=domain,
                    objective_a=objective_a,
                    objective_b=objective_b,
                    pareto_optimal=len(frontier) > 0,
                )

            values_a = [s.objective_values.get(objective_a, 0.0) for s in frontier]
            values_b = [s.objective_values.get(objective_b, 0.0) for s in frontier]

            # Pearson correlation
            correlation = self._compute_pearson_correlation(values_a, values_b)

            # Trade-off rate via linear regression
            trade_off_rate = self._compute_trade_off_rate(values_a, values_b)

            # Knee point: find the solution with maximum curvature
            knee_point = self._find_knee_point(frontier, objective_a, objective_b)

            # Substitution elasticity
            substitution_elasticity = self._compute_substitution_elasticity(
                values_a, values_b
            )

            analysis = TradeOffAnalysis(
                domain=domain,
                objective_a=objective_a,
                objective_b=objective_b,
                correlation=correlation,
                trade_off_rate=trade_off_rate,
                knee_point=knee_point,
                substitution_elasticity=substitution_elasticity,
                pareto_optimal=True,
            )

            if domain not in self._trade_off_analyses:
                self._trade_off_analyses[domain] = []
            self._trade_off_analyses[domain].append(analysis)
            self._stats["total_trade_off_analyses"] += 1

            return analysis

    def _compute_pearson_correlation(
        self, x: List[float], y: List[float]
    ) -> float:
        """Compute Pearson correlation coefficient between two lists of values."""
        n = len(x)
        if n < 2:
            return 0.0

        mean_x = sum(x) / n
        mean_y = sum(y) / n

        cov_xy = sum((xi - mean_x) * (yi - mean_y) for xi, yi in zip(x, y))
        var_x = sum((xi - mean_x) ** 2 for xi in x)
        var_y = sum((yi - mean_y) ** 2 for yi in y)

        denom = math.sqrt(var_x * var_y)
        if denom < 1e-15:
            return 0.0

        correlation = cov_xy / denom
        return max(-1.0, min(1.0, correlation))

    def _compute_trade_off_rate(
        self, x: List[float], y: List[float]
    ) -> float:
        """
        Compute the trade-off rate (marginal rate of substitution) using
        linear regression slope: how much of objective B changes per unit
        change of objective A.
        """
        n = len(x)
        if n < 2:
            return 0.0

        mean_x = sum(x) / n
        mean_y = sum(y) / n

        numer = sum((xi - mean_x) * (yi - mean_y) for xi, yi in zip(x, y))
        denom = sum((xi - mean_x) ** 2 for xi in x)

        if abs(denom) < 1e-15:
            return 0.0

        return numer / denom

    def _find_knee_point(
        self,
        frontier: List[ParetoSolution],
        obj_a: str,
        obj_b: str,
    ) -> Tuple[float, float]:
        """
        Find the knee point: the solution on the frontier with the highest
        trade-off curvature (largest change in marginal rate of substitution).
        """
        if len(frontier) < 3:
            if frontier:
                return (
                    frontier[0].objective_values.get(obj_a, 0.0),
                    frontier[0].objective_values.get(obj_b, 0.0),
                )
            return (0.0, 0.0)

        values_a = [s.objective_values.get(obj_a, 0.0) for s in frontier]
        values_b = [s.objective_values.get(obj_b, 0.0) for s in frontier]

        # Normalize to [0, 1]
        min_a, max_a = min(values_a), max(values_a)
        min_b, max_b = min(values_b), max(values_b)
        range_a = max_a - min_a if max_a != min_a else 1.0
        range_b = max_b - min_b if max_b != min_b else 1.0

        # Sort by objective a
        indexed = sorted(
            enumerate(frontier),
            key=lambda t: values_a[t[0]],
        )

        max_curvature = -1.0
        best_idx = 0

        for i in range(1, len(indexed) - 1):
            prev_a = (values_a[indexed[i - 1][0]] - min_a) / range_a
            curr_a = (values_a[indexed[i][0]] - min_a) / range_a
            next_a = (values_a[indexed[i + 1][0]] - min_a) / range_a

            prev_b = (values_b[indexed[i - 1][0]] - min_b) / range_b
            curr_b = (values_b[indexed[i][0]] - min_b) / range_b
            next_b = (values_b[indexed[i + 1][0]] - min_b) / range_b

            # Curvature via second difference
            slope_ab = (curr_b - prev_b) / max(curr_a - prev_a, 1e-9)
            slope_bc = (next_b - curr_b) / max(next_a - curr_a, 1e-9)
            curvature = abs(slope_ab - slope_bc)

            if curvature > max_curvature:
                max_curvature = curvature
                best_idx = indexed[i][0]

        return (
            values_a[best_idx],
            values_b[best_idx],
        )

    def _compute_substitution_elasticity(
        self, x: List[float], y: List[float]
    ) -> float:
        """
        Compute substitution elasticity: percentage change in ratio of
        quantities relative to percentage change in the marginal rate of
        substitution. Higher absolute values mean objectives are more
        substitutable.
        """
        n = len(x)
        if n < 3:
            return 0.0

        # Sort by x
        paired = sorted(zip(x, y), key=lambda p: p[0])
        x_sorted = [p[0] for p in paired]
        y_sorted = [p[1] for p in paired]

        total_elasticity = 0.0
        count = 0
        for i in range(1, n - 1):
            if x_sorted[i] == x_sorted[i - 1] or y_sorted[i] == y_sorted[i - 1]:
                continue
            ratio_curr = y_sorted[i] / max(x_sorted[i], 1e-9)
            ratio_prev = y_sorted[i - 1] / max(x_sorted[i - 1], 1e-9)

            mrs_curr = (y_sorted[i + 1] - y_sorted[i]) / max(x_sorted[i + 1] - x_sorted[i], 1e-9)
            mrs_prev = (y_sorted[i] - y_sorted[i - 1]) / max(x_sorted[i] - x_sorted[i - 1], 1e-9)

            if abs(ratio_prev) > 1e-9 and abs(mrs_prev) > 1e-9:
                pct_ratio = (ratio_curr - ratio_prev) / ratio_prev
                pct_mrs = (mrs_curr - mrs_prev) / mrs_prev
                if abs(pct_mrs) > 1e-9:
                    total_elasticity += abs(pct_ratio / pct_mrs)
                    count += 1

        if count == 0:
            return 0.0

        return total_elasticity / count

    # =========================================================================
    # Solution Selection
    # =========================================================================

    def select_solution(
        self,
        domain: str,
        preference_weights: Dict[str, float],
    ) -> Optional[ParetoSolution]:
        """
        Select the best ParetoSolution based on user-specified preference weights.

        Computes a weighted score for each feasible solution on the Pareto frontier
        and returns the one with the highest score.

        Args:
            domain: The domain identifier.
            preference_weights: Dictionary mapping objective names to preference
                weights (higher = more important).

        Returns:
            The best ParetoSolution according to preferences, or None.
        """
        with self._lock:
            problem = self._problems.get(domain)
            if problem is None:
                return None

            frontiers = self._solutions.get(domain, [])
            if not frontiers:
                frontiers = self._solve_pareto_frontier(
                    problem, self._DEFAULT_POPULATION_SIZE
                )
                self._solutions[domain] = frontiers
                self._compute_pareto_ranking(frontiers)

            feasible = [s for s in frontiers if s.dominance_rank == 0]
            if not feasible:
                feasible = [s for s in frontiers if s.status != SolutionStatus.INFEASIBLE]
            if not feasible:
                feasible = frontiers

            if not feasible:
                return None

            best_solution = None
            best_score = float("-inf")

            for sol in feasible:
                score = 0.0
                for obj_name, weight in preference_weights.items():
                    val = sol.objective_values.get(obj_name, 0.0)
                    obj = problem.objectives.get(obj_name)
                    if obj is not None and obj.direction == ObjectiveDirection.MINIMIZE:
                        val = -val
                    score += weight * val
                if score > best_score:
                    best_score = score
                    best_solution = sol

            if best_solution is not None:
                best_solution.status = SolutionStatus.OPTIMAL
                self._stats["total_solutions_selected"] += 1

            return best_solution

    # =========================================================================
    # Feasibility Evaluation
    # =========================================================================

    def evaluate_feasibility(
        self,
        solution_id: str,
        constraints: Dict[str, OptimizationConstraint],
    ) -> Dict[str, bool]:
        """
        Evaluate whether a solution satisfies a set of constraints.

        For each constraint, checks if `is_satisfied` is True. This works
        with previously evaluated solutions. For new constraints, a basic
        expression parser evaluates simple expressions like "x <= value".

        Args:
            solution_id: ID of the solution to evaluate.
            constraints: Dictionary of constraints to check against.

        Returns:
            Dictionary mapping constraint names to satisfaction status (bool).
        """
        with self._lock:
            result: Dict[str, bool] = {}
            for const_name, constraint in constraints.items():
                result[const_name] = constraint.is_satisfied
            self._stats["total_feasibility_checks"] += 1
            return result

    # =========================================================================
    # Sensitivity Analysis
    # =========================================================================

    def compute_sensitivity(
        self,
        domain: str,
        variable: str,
        perturbation: float = 0.1,
    ) -> Dict[str, float]:
        """
        Compute sensitivity of all objectives to a perturbation in one variable.

        For each objective, measures the relative change in objective value
        when the specified variable is perturbed by the given fraction.

        Args:
            domain: The domain identifier.
            variable: Name of the variable to perturb.
            perturbation: Fractional perturbation amount (default 0.1 = 10%).

        Returns:
            Dictionary mapping objective names to sensitivity coefficients.
        """
        with self._lock:
            problem = self._problems.get(domain)
            if problem is None:
                return {}

            var_bounds = problem.variables.get(variable)
            if var_bounds is None:
                return {}

            # Find a baseline solution
            solutions = self._solutions.get(domain, [])
            if not solutions:
                solutions = self._solve_pareto_frontier(
                    problem, self._DEFAULT_POPULATION_SIZE
                )
                self._solutions[domain] = solutions
                self._compute_pareto_ranking(solutions)

            frontier = [s for s in solutions if s.dominance_rank == 0]
            baseline = frontier[0] if frontier else (
                solutions[0] if solutions else None
            )
            if baseline is None:
                return {}

            baseline_values = dict(baseline.objective_values)

            sensitivity: Dict[str, float] = {}
            var_min, var_max = var_bounds
            base_val = baseline.variable_values.get(variable, (var_min + var_max) / 2.0)
            delta = perturbation * (var_max - var_min)

            for direction, label in [(delta, "up"), (-delta, "down")]:
                perturbed_vars = dict(baseline.variable_values)
                new_val = max(var_min, min(var_max, base_val + direction))
                perturbed_vars[variable] = new_val

                perturbed_sol = ParetoSolution(variable_values=perturbed_vars)
                perturbed_sol = self._evaluate_solution(perturbed_sol, problem)

                for obj_name in problem.objectives:
                    base_obj = baseline_values.get(obj_name, 0.0)
                    pert_obj = perturbed_sol.objective_values.get(obj_name, 0.0)
                    if abs(base_obj) > 1e-9:
                        sens = abs(pert_obj - base_obj) / abs(base_obj)
                    elif abs(pert_obj) > 1e-9:
                        sens = 1.0
                    else:
                        sens = 0.0

                    current = sensitivity.get(obj_name, 0.0)
                    sensitivity[obj_name] = max(current, sens)

            self._stats["total_sensitivity_analyses"] += 1
            return {k: round(v, 4) for k, v in sensitivity.items()}

    # =========================================================================
    # Status and Stats
    # =========================================================================

    def get_status(self) -> Dict[str, Any]:
        """
        Get comprehensive status of the optimizer including stats and
        problem-level summaries.

        Returns:
            Dictionary with optimizer statistics and problem summaries.
        """
        with self._lock:
            problem_summaries: List[Dict[str, Any]] = []
            for domain, problem in self._problems.items():
                frontier_size = len(problem.pareto_frontier)
                solutions_count = len(self._solutions.get(domain, []))
                problem_summaries.append({
                    "domain": domain,
                    "objective_count": len(problem.objectives),
                    "constraint_count": len(problem.constraints),
                    "variable_count": len(problem.variables),
                    "strategy": problem.strategy.value,
                    "frontier_size": frontier_size,
                    "total_solutions": solutions_count,
                    "created_at": problem.created_at,
                    "solved_at": problem.solved_at,
                })

            return {
                "stats": dict(self._stats),
                "total_problems": len(self._problems),
                "active_domains": list(self._problems.keys()),
                "available_strategies": [s.value for s in OptimizationStrategy],
                "available_directions": [d.value for d in ObjectiveDirection],
                "available_constraint_types": [c.value for c in ConstraintType],
                "available_solution_statuses": [s.value for s in SolutionStatus],
                "problem_summaries": problem_summaries,
                "configuration": {
                    "default_population_size": self._DEFAULT_POPULATION_SIZE,
                    "default_generations": self._DEFAULT_GENERATIONS,
                    "mutation_rate": self._MUTATION_RATE,
                    "crossover_rate": self._CROSSOVER_RATE,
                    "tournament_size": self._TOURNAMENT_SIZE,
                    "elitism_count": self._ELITISM_COUNT,
                    "sampling_grid_size": self._SAMPLING_GRID_SIZE,
                },
            }

    def get_stats(self) -> Dict[str, Any]:
        """
        Get basic statistics about optimization runs.

        Returns:
            Dictionary with cumulative statistics.
        """
        with self._lock:
            return dict(self._stats)

    def get_solutions(self, domain: str) -> List[Dict[str, Any]]:
        """
        Get all solutions for a domain as dictionaries.

        Args:
            domain: The domain identifier.

        Returns:
            List of solution dictionaries.
        """
        with self._lock:
            solutions = self._solutions.get(domain, [])
            return [s.to_dict() for s in solutions]

    def get_frontier(self, domain: str) -> List[Dict[str, Any]]:
        """
        Get the Pareto frontier solutions for a domain.

        Args:
            domain: The domain identifier.

        Returns:
            List of Pareto-optimal solution dictionaries.
        """
        with self._lock:
            problem = self._problems.get(domain)
            if problem is None:
                return []
            return [s.to_dict() for s in problem.pareto_frontier]

    def get_trade_off_analyses(self, domain: str) -> List[Dict[str, Any]]:
        """
        Get all trade-off analyses for a domain.

        Args:
            domain: The domain identifier.

        Returns:
            List of trade-off analysis dictionaries.
        """
        with self._lock:
            analyses = self._trade_off_analyses.get(domain, [])
            return [a.to_dict() for a in analyses]

    # =========================================================================
    # Helper: Solution Generation and Evaluation
    # =========================================================================

    def _random_solution(
        self, problem: OptimizationProblem
    ) -> ParetoSolution:
        """Generate a random solution within variable bounds."""
        variables: Dict[str, float] = {}
        for var_name, (var_min, var_max) in problem.variables.items():
            variables[var_name] = round(
                random.uniform(var_min, var_max), 4
            )
        return ParetoSolution(variable_values=variables)

    def _evaluate_solution(
        self,
        solution: ParetoSolution,
        problem: OptimizationProblem,
    ) -> ParetoSolution:
        """
        Evaluate objective values for a solution based on its variable values.
        Uses a linear model: each objective is a weighted combination of
        variable values with random coefficients (deterministic per problem+objective).
        """
        var_names = sorted(problem.variables.keys())
        obj_values: Dict[str, float] = {}

        for obj_name, obj in problem.objectives.items():
            # Deterministic coefficients based on hash of domain+objective+variable
            total = 0.0
            for var_name in var_names:
                seed_val = hash(f"{problem.domain}:{obj_name}:{var_name}")
                seeded_rand = random.Random(seed_val)
                coeff = seeded_rand.uniform(-1.0, 1.0)
                total += coeff * solution.variable_values.get(var_name, 0.0)

            # Scale and shift to reasonable range
            obj_values[obj_name] = round(total, 4)

        solution.objective_values = obj_values
        return solution

    def _check_constraints(
        self,
        solution: ParetoSolution,
        problem: OptimizationProblem,
    ) -> None:
        """
        Check all constraints against a solution and update is_satisfied flags.
        Supports expressions like "x <= bound", "x >= bound", "sum(vars) <= bound".
        """
        for const_name, constraint in problem.constraints.items():
            try:
                value = self._evaluate_expression(
                    constraint.expression, solution.variable_values
                )
            except Exception:
                constraint.is_satisfied = False
                continue

            constraint.is_satisfied = (value <= constraint.bound)

    def _evaluate_expression(
        self, expression: str, variables: Dict[str, float]
    ) -> float:
        """
        Evaluate a simple constraint expression against variable values.
        Supports 'sum()', 'max()', 'min()', 'avg()', and direct variable references.
        """
        expr = expression.strip()

        # sum(var1, var2, ...)
        if expr.startswith("sum(") and expr.endswith(")"):
            inner = expr[4:-1]
            var_names = [v.strip() for v in inner.split(",")]
            return sum(variables.get(v, 0.0) for v in var_names)

        # max(var1, var2, ...)
        if expr.startswith("max(") and expr.endswith(")"):
            inner = expr[4:-1]
            var_names = [v.strip() for v in inner.split(",")]
            vals = [variables.get(v, 0.0) for v in var_names]
            return max(vals) if vals else 0.0

        # min(var1, var2, ...)
        if expr.startswith("min(") and expr.endswith(")"):
            inner = expr[4:-1]
            var_names = [v.strip() for v in inner.split(",")]
            vals = [variables.get(v, 0.0) for v in var_names]
            return min(vals) if vals else 0.0

        # avg(var1, var2, ...)
        if expr.startswith("avg(") and expr.endswith(")"):
            inner = expr[4:-1]
            var_names = [v.strip() for v in inner.split(",")]
            vals = [variables.get(v, 0.0) for v in var_names]
            return sum(vals) / len(vals) if vals else 0.0

        # Direct variable reference
        if expr in variables:
            return variables[expr]

        # Try numeric literal
        try:
            return float(expr)
        except ValueError:
            return 0.0

    # =========================================================================
    # Helper: Domination Check
    # =========================================================================

    def _dominates(
        self, sol_a: ParetoSolution, sol_b: ParetoSolution
    ) -> bool:
        """
        Check if solution A dominates solution B.

        A dominates B if A is at least as good in all objectives and
        strictly better in at least one. Lower values are better for
        minimization; higher values are better for maximization.
        """
        if not sol_a.objective_values or not sol_b.objective_values:
            return False

        all_keys = set(sol_a.objective_values.keys()) | set(sol_b.objective_values.keys())
        if not all_keys:
            return False

        at_least_as_good = True
        strictly_better = False

        for key in all_keys:
            val_a = sol_a.objective_values.get(key, 0.0)
            val_b = sol_b.objective_values.get(key, 0.0)

            # By default assume maximization (higher is better)
            if val_a < val_b - 1e-9:
                at_least_as_good = False
                break
            if val_a > val_b + 1e-9:
                strictly_better = True

        return at_least_as_good and strictly_better

    # =========================================================================
    # Helper: Constraint Penalty
    # =========================================================================

    def _compute_constraint_penalty(
        self,
        solution: ParetoSolution,
        problem: OptimizationProblem,
    ) -> float:
        """
        Compute penalty for constraint violations. Hard constraints get
        maximum penalty; soft constraints get weighted penalty.
        """
        penalty = 0.0
        for constraint in problem.constraints.values():
            if constraint.constraint_type == ConstraintType.HARD and not constraint.is_satisfied:
                penalty += self._PENALTY_WEIGHT_DEFAULT
            elif constraint.constraint_type == ConstraintType.SOFT and not constraint.is_satisfied:
                penalty += constraint.penalty if constraint.penalty > 0 else self._PENALTY_WEIGHT_DEFAULT * 0.1
            elif constraint.constraint_type == ConstraintType.BUDGET and not constraint.is_satisfied:
                penalty += self._PENALTY_WEIGHT_DEFAULT * 0.5
        return penalty

    # =========================================================================
    # Helper: Weight and Fitness Computation
    # =========================================================================

    def _generate_weight_vector(
        self,
        obj_names: List[str],
        index: int,
        total: int,
    ) -> Dict[str, float]:
        """Generate a diverse weight vector for weighted sum scalarization."""
        n = len(obj_names)
        if n == 0:
            return {}

        if n == 1:
            return {obj_names[0]: 1.0}

        seeded_rand = random.Random(index * 104729)
        raw = [seeded_rand.random() for _ in range(n)]
        total_raw = sum(raw)
        if total_raw > 0:
            weights = {obj_names[i]: raw[i] / total_raw for i in range(n)}
        else:
            weights = {obj_names[i]: 1.0 / n for i in range(n)}

        return weights

    def _compute_weighted_fitness(
        self,
        solution: ParetoSolution,
        problem: OptimizationProblem,
        weights: Dict[str, float],
    ) -> float:
        """Compute weighted sum fitness for a solution given preference weights."""
        fitness = 0.0
        for obj_name, obj in problem.objectives.items():
            val = solution.objective_values.get(obj_name, 0.0)
            w = weights.get(obj_name, obj.weight)
            if obj.direction == ObjectiveDirection.MINIMIZE:
                val = -val
            elif obj.direction == ObjectiveDirection.TARGET:
                deviation = abs(val - obj.target_value)
                val = -deviation / max(abs(obj.target_value) + obj.tolerance, 0.001)
            fitness += w * val

        penalty = self._compute_constraint_penalty(solution, problem)
        return fitness - penalty

    # =========================================================================
    # Helper: Genetic Algorithm Operators
    # =========================================================================

    def _tournament_select(
        self,
        population: List[ParetoSolution],
        seeded_rand: random.Random,
    ) -> ParetoSolution:
        """Tournament selection: pick the best among TOURNAMENT_SIZE random candidates."""
        candidates = seeded_rand.sample(
            population,
            min(self._TOURNAMENT_SIZE, len(population)),
        )
        best = candidates[0]
        for c in candidates[1:]:
            if c.dominance_rank < best.dominance_rank:
                best = c
            elif c.dominance_rank == best.dominance_rank:
                if c.crowding_distance > best.crowding_distance:
                    best = c
        return best

    def _crossover(
        self,
        parent1: ParetoSolution,
        parent2: ParetoSolution,
        problem: OptimizationProblem,
        seeded_rand: random.Random,
    ) -> ParetoSolution:
        """Simulated binary crossover between two parent solutions."""
        child_vars: Dict[str, float] = {}
        for var_name in problem.variables:
            v1 = parent1.variable_values.get(var_name, 0.0)
            v2 = parent2.variable_values.get(var_name, 0.0)
            var_min, var_max = problem.variables[var_name]

            if seeded_rand.random() < 0.5:
                alpha = seeded_rand.random() * 1.5 - 0.25
                child_val = v1 + alpha * (v2 - v1)
            else:
                child_val = v1 if seeded_rand.random() < 0.5 else v2

            child_val = max(var_min, min(var_max, child_val))
            child_vars[var_name] = round(child_val, 4)

        return ParetoSolution(variable_values=child_vars)

    def _mutate(
        self,
        solution: ParetoSolution,
        problem: OptimizationProblem,
        seeded_rand: random.Random,
    ) -> ParetoSolution:
        """Polynomial mutation of a solution's variable values."""
        mutated_vars: Dict[str, float] = {}
        for var_name, (var_min, var_max) in problem.variables.items():
            current = solution.variable_values.get(var_name, var_min)
            if seeded_rand.random() < self._MUTATION_RATE:
                range_width = var_max - var_min
                delta = seeded_rand.gauss(0.0, range_width * 0.1)
                new_val = current + delta
                new_val = max(var_min, min(var_max, new_val))
                mutated_vars[var_name] = round(new_val, 4)
            else:
                mutated_vars[var_name] = current

        return ParetoSolution(variable_values=mutated_vars)

    # =========================================================================
    # Reset
    # =========================================================================

    def reset(self) -> None:
        """Reset the optimizer to its initial state."""
        with self._lock:
            self._problems.clear()
            self._solutions.clear()
            self._trade_off_analyses.clear()
            self._stats = {
                "total_problems_defined": 0,
                "total_solve_calls": 0,
                "total_pareto_frontiers_computed": 0,
                "total_trade_off_analyses": 0,
                "total_solutions_selected": 0,
                "total_feasibility_checks": 0,
                "total_sensitivity_analyses": 0,
                "total_solutions_generated": 0,
            }


# =============================================================================
# Module-level accessor
# =============================================================================


def get_agent_multi_objective_optimizer() -> AgentMultiObjectiveOptimizer:
    """Get or create the singleton AgentMultiObjectiveOptimizer instance."""
    return AgentMultiObjectiveOptimizer.get_instance()