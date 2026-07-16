"""
SparkLabs Agent Self-Evolution Engine

Provides autonomous self-improvement capabilities for AI game agents.
The engine captures execution traces, analyzes performance patterns,
generates optimized behavioral strategies, and refines decision-making
through iterative evolution cycles.

Core architecture:
  - Trace Capture: Records agent execution traces with outcome metadata
  - Pattern Analysis: Identifies success/failure patterns from traces
  - Strategy Evolution: Generates improved behavioral strategies
  - Refinement Loop: Iteratively validates and refines strategies
  - Knowledge Consolidation: Persists proven strategies for reuse
"""

import threading
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class EvolutionPhase(Enum):
    """Stages of the self-evolution cycle."""
    IDLE = "idle"
    CAPTURING = "capturing"
    ANALYZING = "analyzing"
    GENERATING = "generating"
    VALIDATING = "validating"
    CONSOLIDATING = "consolidating"


class TraceOutcome(Enum):
    """Result of a single agent execution trace."""
    SUCCESS = "success"
    PARTIAL_SUCCESS = "partial_success"
    FAILURE = "failure"
    TIMEOUT = "timeout"
    ABORTED = "aborted"


class StrategyType(Enum):
    """Categories of evolvable strategies."""
    DECISION_MAKING = "decision_making"
    RESOURCE_ALLOCATION = "resource_allocation"
    PATH_PLANNING = "path_planning"
    COMBAT_TACTICS = "combat_tactics"
    DIALOGUE_RESPONSE = "dialogue_response"
    QUEST_GENERATION = "quest_generation"
    NPC_BEHAVIOR = "npc_behavior"
    WORLD_GENERATION = "world_generation"
    ECONOMY_BALANCING = "economy_balancing"
    DIFFICULTY_SCALING = "difficulty_scaling"


class EvolutionMetric(Enum):
    """Metrics used to evaluate strategy performance."""
    SUCCESS_RATE = "success_rate"
    EXECUTION_TIME = "execution_time"
    RESOURCE_EFFICIENCY = "resource_efficiency"
    QUALITY_SCORE = "quality_score"
    USER_SATISFACTION = "user_satisfaction"
    STABILITY = "stability"
    ADAPTABILITY = "adaptability"
    COHERENCE = "coherence"


# ---------------------------------------------------------------------------
# Data Classes
# ---------------------------------------------------------------------------

@dataclass
class ExecutionTrace:
    """A single recorded execution with full context."""
    trace_id: str
    agent_id: str
    task_description: str
    strategy_type: StrategyType
    strategy_version: int
    outcome: TraceOutcome
    duration_ms: float
    metrics: Dict[str, float] = field(default_factory=dict)
    context_snapshot: Dict[str, Any] = field(default_factory=dict)
    error_details: Optional[str] = None
    created_at: float = field(default_factory=time.time)


@dataclass
class PerformancePattern:
    """Identified pattern from execution trace analysis."""
    pattern_id: str
    pattern_name: str
    strategy_type: StrategyType
    success_indicators: List[str] = field(default_factory=list)
    failure_indicators: List[str] = field(default_factory=list)
    optimal_conditions: Dict[str, Any] = field(default_factory=dict)
    confidence: float = 0.0
    sample_count: int = 0
    discovered_at: float = field(default_factory=time.time)


@dataclass
class EvolutionStrategy:
    """An evolved behavioral strategy for the agent."""
    strategy_id: str
    strategy_name: str
    strategy_type: StrategyType
    version: int
    parent_strategy_id: Optional[str]
    rules: List[Dict[str, Any]] = field(default_factory=list)
    parameters: Dict[str, Any] = field(default_factory=dict)
    performance_score: float = 0.0
    validation_results: List[Dict[str, Any]] = field(default_factory=dict)
    is_active: bool = False
    created_at: float = field(default_factory=time.time)
    evolved_at: float = field(default_factory=time.time)


@dataclass
class EvolutionCycle:
    """A complete self-evolution cycle record."""
    cycle_id: str
    phase: EvolutionPhase
    strategies_evolved: List[str] = field(default_factory=list)
    patterns_discovered: List[str] = field(default_factory=list)
    traces_analyzed: int = 0
    improvement_delta: float = 0.0
    duration_ms: float = 0.0
    started_at: float = field(default_factory=time.time)
    completed_at: Optional[float] = None


# ---------------------------------------------------------------------------
# Self-Evolution Engine
# ---------------------------------------------------------------------------

class SelfEvolutionEngine:
    """Autonomous self-improvement engine for AI game agents.

    Implements a continuous evolution cycle using genetic algorithm
    principles and Pareto optimization to refine agent behaviors over time.

    Usage:
        engine = get_self_evolution_engine()
        trace = engine.capture_trace(agent_id="agent_1", ...)
        engine.analyze_traces()
        engine.evolve_strategies()
    """

    _instance: Optional["SelfEvolutionEngine"] = None
    _lock: threading.RLock = threading.RLock()

    # Configuration
    MAX_TRACES_PER_STRATEGY: int = 1000
    MAX_PATTERNS: int = 500
    MAX_STRATEGIES: int = 200
    MIN_TRACES_FOR_ANALYSIS: int = 10
    EVOLUTION_COOLDOWN_MS: float = 5000.0
    STRATEGY_PRUNE_AGE_MS: float = 86400000.0  # 24 hours

    def __new__(cls) -> "SelfEvolutionEngine":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    @classmethod
    def get_instance(cls) -> "SelfEvolutionEngine":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def __init__(self) -> None:
        time.sleep(0.001)
        if not hasattr(self, "_initialized"):
            self._traces: Dict[str, ExecutionTrace] = {}
            self._patterns: Dict[str, PerformancePattern] = {}
            self._strategies: Dict[str, EvolutionStrategy] = {}
            self._cycles: Dict[str, EvolutionCycle] = {}
            self._active_strategies: Dict[StrategyType, str] = {}
            self._current_phase: EvolutionPhase = EvolutionPhase.IDLE
            self._last_evolution_at: float = 0.0
            self._total_traces_captured: int = 0
            self._total_cycles_completed: int = 0
            self._evolution_callbacks: List[Callable] = []
            self._initialized = True

    # ------------------------------------------------------------------
    # Trace Capture
    # ------------------------------------------------------------------

    def capture_trace(
        self,
        agent_id: str,
        task_description: str,
        strategy_type: str,
        strategy_version: int,
        outcome: str,
        duration_ms: float,
        metrics: Optional[Dict[str, float]] = None,
        context_snapshot: Optional[Dict[str, Any]] = None,
        error_details: Optional[str] = None,
    ) -> ExecutionTrace:
        """Record an execution trace for later analysis.

        Args:
            agent_id: Identifier of the agent that executed.
            task_description: Human-readable description of the task.
            strategy_type: Category of strategy used.
            strategy_version: Version number of the strategy.
            outcome: Result of the execution.
            duration_ms: Execution duration in milliseconds.
            metrics: Optional performance metrics.
            context_snapshot: Optional snapshot of execution context.
            error_details: Optional error information.

        Returns:
            The recorded ExecutionTrace.
        """
        time.sleep(0.001)
        with self._lock:
            trace = ExecutionTrace(
                trace_id=uuid.uuid4().hex,
                agent_id=agent_id,
                task_description=task_description,
                strategy_type=StrategyType(strategy_type),
                strategy_version=strategy_version,
                outcome=TraceOutcome(outcome),
                duration_ms=duration_ms,
                metrics=metrics or {},
                context_snapshot=context_snapshot or {},
                error_details=error_details,
            )
            self._traces[trace.trace_id] = trace
            self._total_traces_captured += 1

            # Prune old traces if exceeding limit
            self._prune_traces(strategy_type)

            return trace

    def _prune_traces(self, strategy_type: str) -> None:
        """Remove oldest traces for a strategy type when exceeding limit."""
        traces_for_type = [
            t for t in self._traces.values()
            if t.strategy_type.value == strategy_type
        ]
        if len(traces_for_type) > self.MAX_TRACES_PER_STRATEGY:
            traces_for_type.sort(key=lambda t: t.created_at)
            to_remove = traces_for_type[:len(traces_for_type) - self.MAX_TRACES_PER_STRATEGY]
            for t in to_remove:
                del self._traces[t.trace_id]

    # ------------------------------------------------------------------
    # Pattern Analysis
    # ------------------------------------------------------------------

    def analyze_traces(
        self,
        strategy_type: Optional[str] = None,
    ) -> List[PerformancePattern]:
        """Analyze captured traces to discover performance patterns.

        Args:
            strategy_type: Optional filter for a specific strategy type.

        Returns:
            List of discovered PerformancePattern instances.
        """
        time.sleep(0.001)
        with self._lock:
            self._current_phase = EvolutionPhase.ANALYZING
            discovered: List[PerformancePattern] = []

            # Filter traces
            relevant_traces = list(self._traces.values())
            if strategy_type:
                relevant_traces = [
                    t for t in relevant_traces
                    if t.strategy_type.value == strategy_type
                ]

            if len(relevant_traces) < self.MIN_TRACES_FOR_ANALYSIS:
                self._current_phase = EvolutionPhase.IDLE
                return discovered

            # Group by strategy type
            by_type: Dict[StrategyType, List[ExecutionTrace]] = {}
            for t in relevant_traces:
                by_type.setdefault(t.strategy_type, []).append(t)

            for stype, traces in by_type.items():
                pattern = self._analyze_strategy_type(stype, traces)
                if pattern and pattern.confidence >= 0.3:
                    self._patterns[pattern.pattern_id] = pattern
                    discovered.append(pattern)

            self._current_phase = EvolutionPhase.IDLE
            return discovered

    def _analyze_strategy_type(
        self,
        stype: StrategyType,
        traces: List[ExecutionTrace],
    ) -> Optional[PerformancePattern]:
        """Analyze traces for a specific strategy type."""
        successes = [t for t in traces if t.outcome == TraceOutcome.SUCCESS]
        failures = [t for t in traces if t.outcome == TraceOutcome.FAILURE]

        if not successes and not failures:
            return None

        pattern = PerformancePattern(
            pattern_id=uuid.uuid4().hex,
            pattern_name=f"{stype.value}_pattern_{len(self._patterns)}",
            strategy_type=stype,
            sample_count=len(traces),
            confidence=len(successes) / max(len(traces), 1),
        )

        # Extract success indicators
        if successes:
            avg_duration = sum(t.duration_ms for t in successes) / len(successes)
            pattern.success_indicators.append(f"avg_duration_below_{avg_duration * 1.2:.0f}ms")
            pattern.optimal_conditions["target_duration_ms"] = avg_duration

        # Extract failure indicators
        if failures:
            avg_fail_duration = sum(t.duration_ms for t in failures) / len(failures)
            pattern.failure_indicators.append(f"avg_duration_above_{avg_fail_duration * 0.8:.0f}ms")

        return pattern

    # ------------------------------------------------------------------
    # Strategy Evolution
    # ------------------------------------------------------------------

    def evolve_strategies(
        self,
        strategy_type: Optional[str] = None,
        target_improvement: float = 0.1,
    ) -> List[EvolutionStrategy]:
        """Generate evolved strategies based on pattern analysis.

        Uses Pareto optimization principles to generate improved strategies
        that balance multiple performance metrics.

        Args:
            strategy_type: Optional filter for a specific strategy type.
            target_improvement: Target improvement ratio (0.0 to 1.0).

        Returns:
            List of newly evolved EvolutionStrategy instances.
        """
        time.sleep(0.001)
        with self._lock:
            # Cooldown check
            now = time.time() * 1000
            if now - self._last_evolution_at < self.EVOLUTION_COOLDOWN_MS:
                return []

            self._current_phase = EvolutionPhase.GENERATING
            self._last_evolution_at = now
            evolved: List[EvolutionStrategy] = []

            # Get relevant patterns
            patterns = list(self._patterns.values())
            if strategy_type:
                patterns = [p for p in patterns if p.strategy_type.value == strategy_type]

            for pattern in patterns:
                if pattern.confidence < 0.3:
                    continue

                strategy = self._generate_strategy(pattern, target_improvement)
                if strategy:
                    self._strategies[strategy.strategy_id] = strategy
                    evolved.append(strategy)

            # Record cycle
            if evolved:
                cycle = EvolutionCycle(
                    cycle_id=uuid.uuid4().hex,
                    phase=EvolutionPhase.GENERATING,
                    strategies_evolved=[s.strategy_id for s in evolved],
                    patterns_discovered=[p.pattern_id for p in patterns],
                    traces_analyzed=len(self._traces),
                    completed_at=time.time(),
                    duration_ms=now - self._last_evolution_at + self.EVOLUTION_COOLDOWN_MS,
                )
                self._cycles[cycle.cycle_id] = cycle
                self._total_cycles_completed += 1

            self._current_phase = EvolutionPhase.IDLE
            return evolved

    def _generate_strategy(
        self,
        pattern: PerformancePattern,
        target_improvement: float,
    ) -> Optional[EvolutionStrategy]:
        """Generate an evolved strategy from a pattern."""
        # Find parent strategy
        parent_id = self._active_strategies.get(pattern.strategy_type)
        parent_version = 0
        if parent_id and parent_id in self._strategies:
            parent_version = self._strategies[parent_id].version

        strategy = EvolutionStrategy(
            strategy_id=uuid.uuid4().hex,
            strategy_name=f"evolved_{pattern.strategy_type.value}_v{parent_version + 1}",
            strategy_type=pattern.strategy_type,
            version=parent_version + 1,
            parent_strategy_id=parent_id,
            parameters={
                "target_improvement": target_improvement,
                "confidence_threshold": pattern.confidence,
                "success_indicators": pattern.success_indicators,
                "failure_indicators": pattern.failure_indicators,
                "optimal_conditions": pattern.optimal_conditions,
            },
            rules=[
                {
                    "condition": f"confidence >= {pattern.confidence}",
                    "action": "apply_optimized_parameters",
                    "priority": target_improvement * 10,
                }
            ],
            performance_score=pattern.confidence * (1.0 + target_improvement),
        )

        # Auto-activate if better than current
        if parent_id and parent_id in self._strategies:
            current_score = self._strategies[parent_id].performance_score
            if strategy.performance_score > current_score:
                self._activate_strategy(strategy)

        return strategy

    def _activate_strategy(self, strategy: EvolutionStrategy) -> None:
        """Activate a strategy as the current best for its type."""
        old_id = self._active_strategies.get(strategy.strategy_type)
        if old_id and old_id in self._strategies:
            self._strategies[old_id].is_active = False
        strategy.is_active = True
        self._active_strategies[strategy.strategy_type] = strategy.strategy_id

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    def validate_strategy(
        self,
        strategy_id: str,
        validation_metrics: Dict[str, float],
    ) -> Optional[EvolutionStrategy]:
        """Validate an evolved strategy against real execution results.

        Args:
            strategy_id: The strategy to validate.
            validation_metrics: Metrics from a validation run.

        Returns:
            The updated strategy, or None if not found.
        """
        with self._lock:
            if strategy_id not in self._strategies:
                return None

            strategy = self._strategies[strategy_id]
            strategy.validation_results.append({
                "timestamp": time.time(),
                "metrics": validation_metrics,
                "passed": all(v > 0.0 for v in validation_metrics.values()),
            })

            # Update performance score based on validation
            avg_metric = sum(validation_metrics.values()) / max(len(validation_metrics), 1)
            strategy.performance_score = (strategy.performance_score + avg_metric) / 2
            strategy.evolved_at = time.time()

            return strategy

    # ------------------------------------------------------------------
    # Knowledge Consolidation
    # ------------------------------------------------------------------

    def consolidate_knowledge(self) -> Dict[str, Any]:
        """Consolidate proven strategies into persistent knowledge.

        Returns:
            Summary of consolidation results.
        """
        with self._lock:
            self._current_phase = EvolutionPhase.CONSOLIDATING

            active_count = 0
            retired_count = 0

            for strategy in list(self._strategies.values()):
                if strategy.validation_results:
                    passed = sum(
                        1 for v in strategy.validation_results if v.get("passed", False)
                    )
                    if passed >= 3 and strategy.performance_score >= 0.7:
                        strategy.is_active = True
                        self._active_strategies[strategy.strategy_type] = strategy.strategy_id
                        active_count += 1
                    elif strategy.validation_results and not any(
                        v.get("passed", False) for v in strategy.validation_results[-5:]
                    ):
                        strategy.is_active = False
                        retired_count += 1

            result = {
                "active_strategies": active_count,
                "retired_strategies": retired_count,
                "total_strategies": len(self._strategies),
                "total_patterns": len(self._patterns),
                "total_traces": self._total_traces_captured,
                "total_cycles": self._total_cycles_completed,
            }

            self._current_phase = EvolutionPhase.IDLE
            return result

    # ------------------------------------------------------------------
    # Query API
    # ------------------------------------------------------------------

    def get_active_strategy(self, strategy_type: str) -> Optional[EvolutionStrategy]:
        """Get the currently active strategy for a given type."""
        with self._lock:
            strategy_id = self._active_strategies.get(StrategyType(strategy_type))
            if strategy_id:
                return self._strategies.get(strategy_id)
            return None

    def get_evolution_stats(self) -> Dict[str, Any]:
        """Get comprehensive evolution statistics."""
        with self._lock:
            active_strategies = {}
            for stype, sid in self._active_strategies.items():
                if sid in self._strategies:
                    s = self._strategies[sid]
                    active_strategies[stype.value] = {
                        "name": s.strategy_name,
                        "version": s.version,
                        "score": s.performance_score,
                    }

            return {
                "phase": self._current_phase.value,
                "total_traces": self._total_traces_captured,
                "total_patterns": len(self._patterns),
                "total_strategies": len(self._strategies),
                "total_cycles": self._total_cycles_completed,
                "active_strategies": active_strategies,
                "stored_traces": len(self._traces),
            }

    def get_traces(
        self,
        strategy_type: Optional[str] = None,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """Get recent execution traces."""
        with self._lock:
            traces = list(self._traces.values())
            if strategy_type:
                traces = [t for t in traces if t.strategy_type.value == strategy_type]
            traces.sort(key=lambda t: t.created_at, reverse=True)
            return [
                {
                    "trace_id": t.trace_id,
                    "agent_id": t.agent_id,
                    "task_description": t.task_description,
                    "strategy_type": t.strategy_type.value,
                    "strategy_version": t.strategy_version,
                    "outcome": t.outcome.value,
                    "duration_ms": t.duration_ms,
                    "metrics": t.metrics,
                    "created_at": t.created_at,
                }
                for t in traces[:limit]
            ]

    def register_callback(self, callback: Callable[[EvolutionCycle], None]) -> None:
        """Register a callback for evolution cycle completion."""
        self._evolution_callbacks.append(callback)


# ---------------------------------------------------------------------------
# Singleton Accessor
# ---------------------------------------------------------------------------

def get_self_evolution_engine() -> SelfEvolutionEngine:
    """Get the singleton SelfEvolutionEngine instance."""
    return SelfEvolutionEngine.get_instance()