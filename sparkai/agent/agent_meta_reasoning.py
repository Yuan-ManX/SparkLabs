"""
SparkLabs Agent - Meta-Reasoning Engine

This module implements a meta-reasoning engine for AI agents operating inside
the SparkLabs AI-native game engine. Meta-reasoning is "reasoning about
reasoning": tracking the reasoning strategies an agent uses, evaluating their
effectiveness, selecting the best strategy for a new problem, adapting
strategies based on outcomes, and reflecting on the quality of the reasoning
process itself.

The meta-reasoning engine is distinct from (and complementary to) other
SparkLabs agent subsystems:

  * Chain-of-Thought tracks low-level reasoning chains.
  * Reflection Loop tracks iterative self-critique cycles.
  * Causal Reasoning tracks cause/effect modelling.
  * Meta-Reasoning (this module) tracks the strategies that govern which
    reasoning style the agent uses, how well those strategies perform, and
    how the agent adapts its strategy portfolio over time.

Core concepts:

  1. Reasoning Strategies
       A registered strategy has a type (deductive, inductive, abductive,
       analogical, causal, heuristic, bayesian, counterfactual), a domain
       affinity, and a lifecycle status. Strategies accumulate evaluations
       and may be adapted with new parameters.

  2. Reasoning Steps
       A single step in a reasoning chain captures a premise, a chosen
       inference rule, an intermediate conclusion, and a confidence score.

  3. Traces
       A complete trace records a problem, the strategy used, the ordered
       list of steps, the final answer, and an outcome (success/failure
       plus a numeric score).

  4. Evaluations
       A strategy evaluation measures a strategy against a specific
       criterion (accuracy, speed, robustness, interpretability, cost).

  5. Selections
       A strategy selection is a record of choosing a particular strategy
       for a particular problem, with a mode (greedy, exploration,
       exploitation, hybrid, automatic) and a confidence.

  6. Adaptations
       A strategy adaptation changes the parameters of a strategy based on
       observed outcomes, producing a new parameter set and a rationale.

  7. Reflections
       A meta-reflection is a higher-order judgement about the quality of
       a trace, identifying strengths, weaknesses, and recommendations.

Architecture:
  MetaReasoningEngine (Singleton, double-checked locking with threading.RLock)
    |-- ReasoningStrategy       -- a registered strategy
    |-- ReasoningStep           -- a single step in a trace
    |-- StrategyEvaluation      -- an evaluation of a strategy
    |-- StrategySelection       -- a record of selecting a strategy
    |-- StrategyAdaptation      -- a tuning of a strategy
    |-- ReasoningTrace          -- a complete reasoning trace
    |-- MetaReflection          -- a higher-order reflection
    |-- MetaReasoningStats      -- aggregate engine statistics
    |-- MetaReasoningSnapshot   -- complete engine state snapshot
    |-- MetaReasoningEvent      -- observable engine lifecycle event

All public mutating methods are protected by a re-entrant lock so the
engine is safe to call from multiple agent threads. Bounded in-memory
stores use FIFO eviction when their capacity constants are exceeded.
"""

from __future__ import annotations

import datetime
import threading
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Union


# ---------------------------------------------------------------------------
# Capacity constants - bounded in-memory stores with FIFO eviction
# ---------------------------------------------------------------------------

_MAX_AGENTS: int = 500
_MAX_STRATEGIES_PER_AGENT: int = 200
_MAX_TRACES_PER_AGENT: int = 500
_MAX_EVALUATIONS_PER_AGENT: int = 500
_MAX_SELECTIONS_PER_AGENT: int = 500
_MAX_ADAPTATIONS_PER_AGENT: int = 200
_MAX_REFLECTIONS_PER_AGENT: int = 200
_MAX_EVENTS: int = 2000


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _now() -> str:
    """Return a UTC ISO-8601 timestamp string terminated with 'Z'."""
    return datetime.datetime.utcnow().isoformat() + "Z"


def _new_id() -> str:
    """Generate a short unique identifier for a record."""
    return uuid.uuid4().hex[:16]


def _clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    """Clamp a numeric value into the inclusive [low, high] range."""
    if value < low:
        return low
    if value > high:
        return high
    return float(value)


def _evict_fifo_dict(store: Dict[str, Any], max_size: int) -> None:
    """Evict the oldest inserted entries from a dict until within bounds.

    Python dicts preserve insertion order (3.7+), so the first key returned
    by iteration is the oldest. This implements FIFO eviction.
    """
    while len(store) > max_size:
        oldest_key = next(iter(store))
        store.pop(oldest_key, None)


def _evict_fifo_list(store: List[Any], max_size: int) -> None:
    """Evict the oldest inserted entries from a list until within bounds."""
    while len(store) > max_size:
        store.pop(0)


def _normalize_problem(problem: str) -> str:
    """Return a normalized key for a problem description."""
    return (problem or "").strip().lower()


def _normalize_domain(
    domain: Union[ProblemDomain, str, None],
) -> Optional[ProblemDomain]:
    """Coerce a domain value into a :class:`ProblemDomain` enum instance.

    Accepts an enum, its string value, or ``None``. Falls back to ``None``
    when the value cannot be resolved.
    """
    if domain is None:
        return None
    if isinstance(domain, ProblemDomain):
        return domain
    if isinstance(domain, str):
        try:
            return ProblemDomain(domain)
        except ValueError:
            return None
    return None


def _normalize_mode(
    mode: Union[SelectionMode, str, None],
) -> SelectionMode:
    """Coerce a mode value into a :class:`SelectionMode` enum instance."""
    if isinstance(mode, SelectionMode):
        return mode
    if isinstance(mode, str):
        try:
            return SelectionMode(mode)
        except ValueError:
            return SelectionMode.AUTOMATIC
    return SelectionMode.AUTOMATIC


def _normalize_status(
    status: Union[StrategyStatus, str, None],
) -> StrategyStatus:
    """Coerce a status value into a :class:`StrategyStatus` enum instance."""
    if isinstance(status, StrategyStatus):
        return status
    if isinstance(status, str):
        try:
            return StrategyStatus(status)
        except ValueError:
            return StrategyStatus.ACTIVE
    return StrategyStatus.ACTIVE


def _normalize_criterion(
    criterion: Union[EvaluationCriterion, str, None],
) -> EvaluationCriterion:
    """Coerce a criterion value into an :class:`EvaluationCriterion` enum."""
    if isinstance(criterion, EvaluationCriterion):
        return criterion
    if isinstance(criterion, str):
        try:
            return EvaluationCriterion(criterion)
        except ValueError:
            return EvaluationCriterion.ACCURACY
    return EvaluationCriterion.ACCURACY


def _normalize_strategy_type(
    strategy_type: Union[ReasoningStrategyType, str, None],
) -> ReasoningStrategyType:
    """Coerce a strategy type value into a :class:`ReasoningStrategyType` enum."""
    if isinstance(strategy_type, ReasoningStrategyType):
        return strategy_type
    if isinstance(strategy_type, str):
        try:
            return ReasoningStrategyType(strategy_type)
        except ValueError:
            return ReasoningStrategyType.HEURISTIC
    return ReasoningStrategyType.HEURISTIC


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class ReasoningStrategyType(Enum):
    """The kind of reasoning a strategy embodies."""
    DEDUCTIVE = "deductive"
    INDUCTIVE = "inductive"
    ABDUCTIVE = "abductive"
    ANALOGICAL = "analogical"
    CAUSAL = "causal"
    HEURISTIC = "heuristic"
    BAYESIAN = "bayesian"
    COUNTERFACTUAL = "counterfactual"


class ProblemDomain(Enum):
    """The problem domain a strategy is most applicable to."""
    LOGIC = "logic"
    PLANNING = "planning"
    DIAGNOSIS = "diagnosis"
    PREDICTION = "prediction"
    CLASSIFICATION = "classification"
    CREATIVE = "creative"


class EvaluationCriterion(Enum):
    """The criterion used to evaluate a strategy."""
    ACCURACY = "accuracy"
    SPEED = "speed"
    ROBUSTNESS = "robustness"
    INTERPRETABILITY = "interpretability"
    COST = "cost"


class SelectionMode(Enum):
    """How a strategy was selected for a problem."""
    AUTOMATIC = "automatic"
    GREEDY = "greedy"
    EXPLORATION = "exploration"
    EXPLOITATION = "exploitation"
    HYBRID = "hybrid"


class StrategyStatus(Enum):
    """The lifecycle status of a strategy."""
    ACTIVE = "active"
    EXPERIMENTAL = "experimental"
    DEPRECATED = "deprecated"
    FAVORITE = "favorite"


class MetaReasoningEventKind(Enum):
    """Observable lifecycle events emitted by the meta-reasoning engine."""
    STRATEGY_REGISTERED = "strategy_registered"
    STRATEGY_USED = "strategy_used"
    STRATEGY_EVALUATED = "strategy_evaluated"
    STRATEGY_SELECTED = "strategy_selected"
    TRACE_RECORDED = "trace_recorded"
    REFLECTION_GENERATED = "reflection_generated"
    STRATEGY_ADAPTED = "strategy_adapted"


# ---------------------------------------------------------------------------
# Data Classes
# ---------------------------------------------------------------------------


@dataclass
class ReasoningStrategy:
    """A registered reasoning strategy for an agent."""
    strategy_id: str
    agent_id: str
    name: str
    strategy_type: ReasoningStrategyType
    description: str
    domain_affinity: Optional[ProblemDomain]
    parameters: Dict[str, Any]
    status: StrategyStatus
    use_count: int
    success_count: int
    failure_count: int
    avg_score: float
    created_at: str
    updated_at: str
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this strategy to a JSON-friendly dictionary."""
        return {
            "strategy_id": self.strategy_id,
            "agent_id": self.agent_id,
            "name": self.name,
            "strategy_type": self.strategy_type.value,
            "description": self.description,
            "domain_affinity": (
                self.domain_affinity.value if self.domain_affinity is not None else None
            ),
            "parameters": dict(self.parameters) if self.parameters else {},
            "status": self.status.value,
            "use_count": self.use_count,
            "success_count": self.success_count,
            "failure_count": self.failure_count,
            "avg_score": self.avg_score,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "metadata": dict(self.metadata) if self.metadata else {},
        }


@dataclass
class ReasoningStep:
    """A single step within a reasoning trace."""
    step_id: str
    index: int
    premise: str
    inference_rule: str
    conclusion: str
    confidence: float
    timestamp: str
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this step to a JSON-friendly dictionary."""
        return {
            "step_id": self.step_id,
            "index": self.index,
            "premise": self.premise,
            "inference_rule": self.inference_rule,
            "conclusion": self.conclusion,
            "confidence": self.confidence,
            "timestamp": self.timestamp,
            "metadata": dict(self.metadata) if self.metadata else {},
        }


@dataclass
class StrategyEvaluation:
    """An evaluation of a strategy against a specific criterion."""
    evaluation_id: str
    agent_id: str
    strategy_id: str
    criterion: EvaluationCriterion
    score: float
    outcome: str
    notes: str
    timestamp: str

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this evaluation to a JSON-friendly dictionary."""
        return {
            "evaluation_id": self.evaluation_id,
            "agent_id": self.agent_id,
            "strategy_id": self.strategy_id,
            "criterion": self.criterion.value,
            "score": self.score,
            "outcome": self.outcome,
            "notes": self.notes,
            "timestamp": self.timestamp,
        }


@dataclass
class StrategySelection:
    """A record of selecting a strategy for a problem."""
    selection_id: str
    agent_id: str
    problem: str
    domain: Optional[ProblemDomain]
    strategy_id: str
    mode: SelectionMode
    confidence: float
    rationale: str
    timestamp: str

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this selection to a JSON-friendly dictionary."""
        return {
            "selection_id": self.selection_id,
            "agent_id": self.agent_id,
            "problem": self.problem,
            "domain": self.domain.value if self.domain is not None else None,
            "strategy_id": self.strategy_id,
            "mode": self.mode.value,
            "confidence": self.confidence,
            "rationale": self.rationale,
            "timestamp": self.timestamp,
        }


@dataclass
class StrategyAdaptation:
    """An adaptation (parameter update) of a strategy."""
    adaptation_id: str
    agent_id: str
    strategy_id: str
    old_parameters: Dict[str, Any]
    new_parameters: Dict[str, Any]
    rationale: str
    expected_improvement: float
    timestamp: str

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this adaptation to a JSON-friendly dictionary."""
        return {
            "adaptation_id": self.adaptation_id,
            "agent_id": self.agent_id,
            "strategy_id": self.strategy_id,
            "old_parameters": dict(self.old_parameters) if self.old_parameters else {},
            "new_parameters": dict(self.new_parameters) if self.new_parameters else {},
            "rationale": self.rationale,
            "expected_improvement": self.expected_improvement,
            "timestamp": self.timestamp,
        }


@dataclass
class ReasoningTrace:
    """A complete reasoning trace for a problem."""
    trace_id: str
    agent_id: str
    problem: str
    domain: Optional[ProblemDomain]
    strategy_id: str
    steps: List[ReasoningStep]
    final_answer: str
    success: bool
    score: float
    started_at: str
    completed_at: str
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this trace to a JSON-friendly dictionary."""
        return {
            "trace_id": self.trace_id,
            "agent_id": self.agent_id,
            "problem": self.problem,
            "domain": self.domain.value if self.domain is not None else None,
            "strategy_id": self.strategy_id,
            "steps": [s.to_dict() for s in self.steps],
            "final_answer": self.final_answer,
            "success": self.success,
            "score": self.score,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "metadata": dict(self.metadata) if self.metadata else {},
        }


@dataclass
class MetaReflection:
    """A higher-order reflection on the quality of a trace."""
    reflection_id: str
    agent_id: str
    trace_id: str
    quality: float
    strengths: List[str]
    weaknesses: List[str]
    recommendations: List[str]
    timestamp: str

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this reflection to a JSON-friendly dictionary."""
        return {
            "reflection_id": self.reflection_id,
            "agent_id": self.agent_id,
            "trace_id": self.trace_id,
            "quality": self.quality,
            "strengths": list(self.strengths),
            "weaknesses": list(self.weaknesses),
            "recommendations": list(self.recommendations),
            "timestamp": self.timestamp,
        }


@dataclass
class MetaReasoningStats:
    """Aggregate statistics about the meta-reasoning engine."""
    total_agents: int
    total_strategies: int
    total_traces: int
    total_evaluations: int
    total_selections: int
    total_adaptations: int
    total_reflections: int
    avg_strategy_score: float

    def to_dict(self) -> Dict[str, Any]:
        """Serialize these statistics to a JSON-friendly dictionary."""
        return {
            "total_agents": self.total_agents,
            "total_strategies": self.total_strategies,
            "total_traces": self.total_traces,
            "total_evaluations": self.total_evaluations,
            "total_selections": self.total_selections,
            "total_adaptations": self.total_adaptations,
            "total_reflections": self.total_reflections,
            "avg_strategy_score": self.avg_strategy_score,
        }


@dataclass
class MetaReasoningSnapshot:
    """A complete snapshot of the meta-reasoning engine state."""
    initialized: bool
    strategies: List[ReasoningStrategy]
    traces: List[ReasoningTrace]
    evaluations: List[StrategyEvaluation]
    selections: List[StrategySelection]
    adaptations: List[StrategyAdaptation]
    reflections: List[MetaReflection]
    events: List[MetaReasoningEvent]
    stats: MetaReasoningStats

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this snapshot to a JSON-friendly dictionary."""
        return {
            "initialized": self.initialized,
            "strategies": [s.to_dict() for s in self.strategies],
            "traces": [t.to_dict() for t in self.traces],
            "evaluations": [e.to_dict() for e in self.evaluations],
            "selections": [s.to_dict() for s in self.selections],
            "adaptations": [a.to_dict() for a in self.adaptations],
            "reflections": [r.to_dict() for r in self.reflections],
            "events": [e.to_dict() for e in self.events],
            "stats": self.stats.to_dict(),
        }


@dataclass
class MetaReasoningEvent:
    """An observable lifecycle event emitted by the meta-reasoning engine."""
    event_id: str
    kind: MetaReasoningEventKind
    timestamp: str
    payload: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this event to a JSON-friendly dictionary."""
        return {
            "event_id": self.event_id,
            "kind": self.kind.value,
            "timestamp": self.timestamp,
            "payload": dict(self.payload) if self.payload else {},
        }


# ---------------------------------------------------------------------------
# Meta-Reasoning Engine (Singleton with double-checked locking)
# ---------------------------------------------------------------------------


class MetaReasoningEngine:
    """Meta-reasoning engine for AI game agents.

    The engine maintains a per-agent portfolio of reasoning strategies,
    accumulates traces of reasoning runs, evaluates strategies across
    multiple criteria, selects strategies for new problems, adapts
    strategies in response to observed outcomes, and produces
    higher-order reflections on the quality of past reasoning.

    It is a thread-safe singleton accessed via :meth:`get_instance` or the
    module-level :func:`get_meta_reasoning` helper.

    Usage:
        engine = get_meta_reasoning()
        engine.register_strategy(
            "agent_alpha", "deductive_solver", ReasoningStrategyType.DEDUCTIVE,
        )
        selection = engine.select_strategy(
            "agent_alpha", "Prove the theorem", ProblemDomain.LOGIC,
            mode=SelectionMode.EXPLOITATION,
        )
        trace = engine.record_trace(
            "agent_alpha", "Prove the theorem", selection.strategy_id, steps,
        )
        reflection = engine.generate_reflection("agent_alpha", trace.trace_id)
    """

    _instance: Optional["MetaReasoningEngine"] = None
    _lock: threading.RLock = threading.RLock()

    # -- Construction (double-checked locking) ---------------------------

    def __new__(cls) -> "MetaReasoningEngine":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self) -> None:
        # Fast path: already initialized singleton.
        if self._initialized:
            return
        with self._lock:
            # Second check inside the lock to guard against concurrent
            # construction.
            if self._initialized:
                return

            # Per-agent strategy portfolios keyed by agent_id, then by
            # strategy_id.
            self._strategies: Dict[str, Dict[str, ReasoningStrategy]] = {}

            # Per-agent traces, evaluations, selections, adaptations, and
            # reflections.
            self._traces: Dict[str, List[ReasoningTrace]] = {}
            self._evaluations: Dict[str, List[StrategyEvaluation]] = {}
            self._selections: Dict[str, List[StrategySelection]] = {}
            self._adaptations: Dict[str, List[StrategyAdaptation]] = {}
            self._reflections: Dict[str, List[MetaReflection]] = {}

            # Observable lifecycle events.
            self._events: List[MetaReasoningEvent] = []

            # Aggregate counters for diagnostics.
            self._strategy_counter: int = 0
            self._trace_counter: int = 0
            self._evaluation_counter: int = 0
            self._selection_counter: int = 0
            self._adaptation_counter: int = 0
            self._reflection_counter: int = 0
            self._agent_counter: int = 0

            self._initialized: bool = True

            # Seed baseline meta-reasoning data.
            self._seed_data()

    @classmethod
    def get_instance(cls) -> "MetaReasoningEngine":
        """Return the singleton MetaReasoningEngine instance."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    # ------------------------------------------------------------------
    # Internal helpers (caller must hold self._lock)
    # ------------------------------------------------------------------

    def _ensure_agent(self, agent_id: str) -> None:
        """Ensure per-agent storage exists for ``agent_id``.

        Assumes the caller already holds ``self._lock``.
        """
        if agent_id not in self._strategies:
            self._strategies[agent_id] = {}
            self._traces[agent_id] = []
            self._evaluations[agent_id] = []
            self._selections[agent_id] = []
            self._adaptations[agent_id] = []
            self._reflections[agent_id] = []
            self._agent_counter += 1

    def _record_event(
        self,
        kind: MetaReasoningEventKind,
        payload: Dict[str, Any],
    ) -> None:
        """Record an observable meta-reasoning event.

        Assumes the caller already holds ``self._lock``. The event log is
        bounded by ``_MAX_EVENTS`` with FIFO eviction.
        """
        event = MetaReasoningEvent(
            event_id=_new_id(),
            kind=kind,
            timestamp=_now(),
            payload=dict(payload) if payload else {},
        )
        self._events.append(event)
        _evict_fifo_list(self._events, _MAX_EVENTS)

    def _select_strategy_for_problem(
        self,
        agent_id: str,
        problem: str,
        domain: Optional[ProblemDomain],
        mode: SelectionMode,
    ) -> Optional[ReasoningStrategy]:
        """Pick the best strategy for ``problem``/``domain`` under ``mode``.

        The selection algorithm depends on the mode:

          * GREEDY: pick the active strategy with the highest avg_score that
            matches the domain (or any active strategy if no match).
          * EXPLORATION: prefer experimental strategies, then active ones.
          * EXPLOITATION: pick the active strategy with the highest
            success_count, breaking ties by avg_score.
          * HYBRID: 80% exploitation (best avg_score) / 20% exploration
            (experimental). Falls back to the best active strategy.
          * AUTOMATIC: prefer a domain match, otherwise pick the active
            strategy with the highest avg_score.

        Returns ``None`` when the agent has no strategies.
        Assumes the caller already holds ``self._lock``.
        """
        strategies = list(self._strategies.get(agent_id, {}).values())
        if not strategies:
            return None
        active = [s for s in strategies if s.status == StrategyStatus.ACTIVE]
        favorites = [s for s in strategies if s.status == StrategyStatus.FAVORITE]
        experimental = [s for s in strategies if s.status == StrategyStatus.EXPERIMENTAL]
        candidate_pool = active + favorites
        if not candidate_pool:
            candidate_pool = strategies

        # Domain-matching subset (within the candidate pool).
        if domain is not None:
            domain_match = [
                s for s in candidate_pool if s.domain_affinity == domain
            ]
        else:
            domain_match = []

        def _by_score(s: ReasoningStrategy) -> float:
            return s.avg_score

        def _by_uses(s: ReasoningStrategy) -> int:
            return s.success_count

        if mode == SelectionMode.GREEDY:
            pool = domain_match or candidate_pool
            return max(pool, key=_by_score)

        if mode == SelectionMode.EXPLORATION:
            pool = experimental or candidate_pool
            if domain is not None:
                domain_exp = [s for s in pool if s.domain_affinity == domain]
                if domain_exp:
                    pool = domain_exp
            return max(pool, key=_by_score)

        if mode == SelectionMode.EXPLOITATION:
            pool = domain_match or candidate_pool
            return max(pool, key=_by_uses)

        if mode == SelectionMode.HYBRID:
            pool = domain_match or candidate_pool
            best = max(pool, key=_by_score)
            if experimental and best.use_count > 0:
                # 20% chance of picking an experimental strategy.
                # Deterministic here: use a hash of the problem text so the
                # same problem always picks the same experimental strategy.
                bucket = hash(_normalize_problem(problem)) % 5
                if bucket == 0:
                    return max(experimental, key=_by_score)
            return best

        # AUTOMATIC (default).
        if domain is not None and domain_match:
            return max(domain_match, key=_by_score)
        return max(candidate_pool, key=_by_score)

    def _update_strategy_aggregate(
        self,
        strategy: ReasoningStrategy,
        success: bool,
        score: float,
    ) -> None:
        """Update aggregate counters on a strategy after a run.

        Assumes the caller already holds ``self._lock``.
        """
        strategy.use_count += 1
        if success:
            strategy.success_count += 1
        else:
            strategy.failure_count += 1
        # Running average of observed scores.
        n = strategy.use_count
        prev = strategy.avg_score
        strategy.avg_score = _clamp(round(((prev * (n - 1)) + float(score)) / n, 4))
        strategy.updated_at = _now()

    # ------------------------------------------------------------------
    # Strategy registration and lookup
    # ------------------------------------------------------------------

    def register_strategy(
        self,
        agent_id: str,
        name: str,
        strategy_type: Union[ReasoningStrategyType, str],
        description: str = "",
        domain_affinity: Union[ProblemDomain, str, None] = None,
        parameters: Optional[Dict[str, Any]] = None,
        status: Union[StrategyStatus, str, None] = StrategyStatus.ACTIVE,
    ) -> ReasoningStrategy:
        """Register a new reasoning strategy for an agent.

        Args:
            agent_id: Identifier of the agent.
            name: Short name of the strategy (e.g. ``"deductive_solver"``).
            strategy_type: A :class:`ReasoningStrategyType` enum or its
                string value.
            description: Optional human-readable description.
            domain_affinity: Optional :class:`ProblemDomain` (or string)
                indicating which problem domain the strategy is best suited
                to.
            parameters: Optional initial parameter dictionary.
            status: Initial :class:`StrategyStatus` (defaults to active).

        Returns:
            The newly created :class:`ReasoningStrategy`.
        """
        with self._lock:
            self._ensure_agent(agent_id)
            resolved_type = _normalize_strategy_type(strategy_type)
            resolved_domain = _normalize_domain(domain_affinity)
            resolved_status = _normalize_status(status)
            now = _now()
            strategy = ReasoningStrategy(
                strategy_id=_new_id(),
                agent_id=agent_id,
                name=name,
                strategy_type=resolved_type,
                description=description or "",
                domain_affinity=resolved_domain,
                parameters=dict(parameters) if parameters else {},
                status=resolved_status,
                use_count=0,
                success_count=0,
                failure_count=0,
                avg_score=0.0,
                created_at=now,
                updated_at=now,
                metadata={},
            )
            self._strategies[agent_id][strategy.strategy_id] = strategy
            self._strategy_counter += 1
            _evict_fifo_dict(
                self._strategies[agent_id], _MAX_STRATEGIES_PER_AGENT
            )
            self._record_event(
                MetaReasoningEventKind.STRATEGY_REGISTERED,
                {
                    "agent_id": agent_id,
                    "strategy_id": strategy.strategy_id,
                    "name": name,
                    "strategy_type": resolved_type.value,
                    "domain_affinity": (
                        resolved_domain.value if resolved_domain is not None else None
                    ),
                    "status": resolved_status.value,
                },
            )
            return strategy

    def get_strategy(
        self, agent_id: str, strategy_id: str
    ) -> Optional[ReasoningStrategy]:
        """Return a single strategy by id, or ``None`` if not found."""
        with self._lock:
            return self._strategies.get(agent_id, {}).get(strategy_id)

    def get_strategies(
        self,
        agent_id: str,
        status: Union[StrategyStatus, str, None] = None,
    ) -> List[ReasoningStrategy]:
        """Return strategies for an agent, optionally filtered by status."""
        with self._lock:
            strategies = list(self._strategies.get(agent_id, {}).values())
            if status is None:
                return strategies
            resolved = _normalize_status(status)
            return [s for s in strategies if s.status == resolved]

    def set_status(
        self,
        agent_id: str,
        strategy_id: str,
        status: Union[StrategyStatus, str],
    ) -> Optional[ReasoningStrategy]:
        """Update the lifecycle status of a strategy.

        Returns:
            The updated :class:`ReasoningStrategy`, or ``None`` if the
            strategy does not exist.
        """
        with self._lock:
            strategy = self._strategies.get(agent_id, {}).get(strategy_id)
            if strategy is None:
                return None
            strategy.status = _normalize_status(status)
            strategy.updated_at = _now()
            self._record_event(
                MetaReasoningEventKind.STRATEGY_REGISTERED,
                {
                    "agent_id": agent_id,
                    "strategy_id": strategy_id,
                    "status_change": strategy.status.value,
                },
            )
            return strategy

    # ------------------------------------------------------------------
    # Strategy selection
    # ------------------------------------------------------------------

    def select_strategy(
        self,
        agent_id: str,
        problem: str,
        domain: Union[ProblemDomain, str, None] = None,
        mode: Union[SelectionMode, str, None] = SelectionMode.AUTOMATIC,
    ) -> StrategySelection:
        """Select a strategy for a problem and record the selection.

        Args:
            agent_id: Identifier of the agent.
            problem: Description of the problem to solve.
            domain: Optional :class:`ProblemDomain` (or string) describing
                the problem domain. When omitted, any strategy is eligible.
            mode: The :class:`SelectionMode` (or string) controlling how
                the strategy is chosen.

        Returns:
            A :class:`StrategySelection` describing the chosen strategy.
            If the agent has no strategies, a "null" selection is returned
            that references an empty ``strategy_id`` and a low confidence.
        """
        with self._lock:
            self._ensure_agent(agent_id)
            resolved_domain = _normalize_domain(domain)
            resolved_mode = _normalize_mode(mode)
            chosen = self._select_strategy_for_problem(
                agent_id, problem, resolved_domain, resolved_mode
            )
            now = _now()
            if chosen is None:
                selection = StrategySelection(
                    selection_id=_new_id(),
                    agent_id=agent_id,
                    problem=problem,
                    domain=resolved_domain,
                    strategy_id="",
                    mode=resolved_mode,
                    confidence=0.0,
                    rationale="No strategies available for agent",
                    timestamp=now,
                )
            else:
                # Confidence is the strategy's avg_score scaled by mode.
                base_conf = chosen.avg_score
                if resolved_mode == SelectionMode.EXPLORATION:
                    base_conf = min(1.0, base_conf + 0.1)
                elif resolved_mode == SelectionMode.GREEDY:
                    base_conf = min(1.0, base_conf + 0.05)
                selection = StrategySelection(
                    selection_id=_new_id(),
                    agent_id=agent_id,
                    problem=problem,
                    domain=resolved_domain,
                    strategy_id=chosen.strategy_id,
                    mode=resolved_mode,
                    confidence=_clamp(round(base_conf, 4)),
                    rationale=(
                        f"Selected {chosen.name} via {resolved_mode.value} "
                        f"for domain {resolved_domain.value if resolved_domain else 'any'}"
                    ),
                    timestamp=now,
                )
            self._selections[agent_id].append(selection)
            if len(self._selections[agent_id]) > _MAX_SELECTIONS_PER_AGENT:
                self._selections[agent_id] = self._selections[agent_id][
                    -_MAX_SELECTIONS_PER_AGENT:
                ]
            self._selection_counter += 1
            self._record_event(
                MetaReasoningEventKind.STRATEGY_SELECTED,
                {
                    "agent_id": agent_id,
                    "selection_id": selection.selection_id,
                    "strategy_id": selection.strategy_id,
                    "mode": selection.mode.value,
                    "domain": (
                        selection.domain.value if selection.domain is not None else None
                    ),
                },
            )
            return selection

    def recommend_strategy(
        self,
        agent_id: str,
        problem: str,
        domain: Union[ProblemDomain, str, None] = None,
    ) -> StrategySelection:
        """Recommend a strategy using automatic hybrid selection.

        This is a convenience wrapper around :meth:`select_strategy` that
        always uses :attr:`SelectionMode.HYBRID` to balance exploitation
        and exploration.
        """
        return self.select_strategy(
            agent_id, problem, domain=domain, mode=SelectionMode.HYBRID
        )

    def get_selections(
        self,
        agent_id: str,
        limit: int = 50,
    ) -> List[StrategySelection]:
        """Return recent selections for an agent, newest first."""
        with self._lock:
            selections = self._selections.get(agent_id, [])
            n = max(0, int(limit))
            if n == 0:
                return []
            return list(reversed(selections))[:n]

    # ------------------------------------------------------------------
    # Trace recording
    # ------------------------------------------------------------------

    def record_trace(
        self,
        agent_id: str,
        problem: str,
        strategy_id: str,
        steps: List[Union[ReasoningStep, Dict[str, Any]]],
        final_answer: str = "",
        success: bool = True,
        score: float = 0.5,
        domain: Union[ProblemDomain, str, None] = None,
    ) -> Optional[ReasoningTrace]:
        """Record a complete reasoning trace for an agent.

        Args:
            agent_id: Identifier of the agent.
            problem: Description of the problem that was solved.
            strategy_id: Identifier of the strategy used. May be empty if
                the agent had no strategies available.
            steps: A list of :class:`ReasoningStep` instances or
                dictionaries with the keys ``premise``, ``inference_rule``,
                ``conclusion``, and ``confidence``.
            final_answer: The final answer produced by the reasoning chain.
            success: Whether the trace was successful.
            score: A numeric quality score in [0.0, 1.0] (clamped).
            domain: Optional :class:`ProblemDomain` for the problem.

        Returns:
            The newly created :class:`ReasoningTrace`, or ``None`` when no
            matching strategy is registered and ``strategy_id`` is
            non-empty.
        """
        with self._lock:
            self._ensure_agent(agent_id)
            resolved_domain = _normalize_domain(domain)
            strategy = self._strategies.get(agent_id, {}).get(strategy_id)
            if strategy_id and strategy is None:
                return None
            now = _now()
            normalized_steps: List[ReasoningStep] = []
            for index, raw in enumerate(steps or []):
                if isinstance(raw, ReasoningStep):
                    normalized_steps.append(raw)
                elif isinstance(raw, dict):
                    step = ReasoningStep(
                        step_id=_new_id(),
                        index=index,
                        premise=str(raw.get("premise", "")),
                        inference_rule=str(raw.get("inference_rule", "")),
                        conclusion=str(raw.get("conclusion", "")),
                        confidence=_clamp(float(raw.get("confidence", 0.5))),
                        timestamp=now,
                        metadata=dict(raw.get("metadata") or {}),
                    )
                    normalized_steps.append(step)
                else:
                    # Best-effort conversion for string steps.
                    normalized_steps.append(
                        ReasoningStep(
                            step_id=_new_id(),
                            index=index,
                            premise=str(raw),
                            inference_rule="",
                            conclusion="",
                            confidence=0.5,
                            timestamp=now,
                            metadata={},
                        )
                    )
            trace = ReasoningTrace(
                trace_id=_new_id(),
                agent_id=agent_id,
                problem=problem,
                domain=resolved_domain,
                strategy_id=strategy_id,
                steps=normalized_steps,
                final_answer=final_answer,
                success=bool(success),
                score=_clamp(float(score)),
                started_at=now,
                completed_at=now,
                metadata={},
            )
            self._traces[agent_id].append(trace)
            if len(self._traces[agent_id]) > _MAX_TRACES_PER_AGENT:
                self._traces[agent_id] = self._traces[agent_id][
                    -_MAX_TRACES_PER_AGENT:
                ]
            self._trace_counter += 1
            if strategy is not None:
                self._update_strategy_aggregate(
                    strategy, success=bool(success), score=trace.score
                )
            self._record_event(
                MetaReasoningEventKind.TRACE_RECORDED,
                {
                    "agent_id": agent_id,
                    "trace_id": trace.trace_id,
                    "strategy_id": strategy_id,
                    "step_count": len(normalized_steps),
                    "success": trace.success,
                    "score": trace.score,
                },
            )
            if strategy is not None:
                self._record_event(
                    MetaReasoningEventKind.STRATEGY_USED,
                    {
                        "agent_id": agent_id,
                        "strategy_id": strategy_id,
                        "trace_id": trace.trace_id,
                        "use_count": strategy.use_count,
                        "avg_score": strategy.avg_score,
                    },
                )
            return trace

    def get_traces(
        self,
        agent_id: str,
        limit: int = 50,
    ) -> List[ReasoningTrace]:
        """Return recent traces for an agent, newest first."""
        with self._lock:
            traces = self._traces.get(agent_id, [])
            n = max(0, int(limit))
            if n == 0:
                return []
            return list(reversed(traces))[:n]

    def get_trace(
        self, agent_id: str, trace_id: str
    ) -> Optional[ReasoningTrace]:
        """Return a single trace by id, or ``None`` if not found."""
        with self._lock:
            for trace in self._traces.get(agent_id, []):
                if trace.trace_id == trace_id:
                    return trace
            return None

    # ------------------------------------------------------------------
    # Strategy evaluation
    # ------------------------------------------------------------------

    def evaluate_strategy(
        self,
        agent_id: str,
        strategy_id: str,
        outcome: str = "success",
        criterion: Union[EvaluationCriterion, str] = EvaluationCriterion.ACCURACY,
        score: float = 0.5,
        notes: str = "",
    ) -> Optional[StrategyEvaluation]:
        """Record an evaluation of a strategy against a criterion.

        Args:
            agent_id: Identifier of the agent.
            strategy_id: Identifier of the strategy being evaluated.
            outcome: Short outcome label (e.g. ``"success"``, ``"failure"``,
                ``"neutral"``).
            criterion: The :class:`EvaluationCriterion` (or string).
            score: A numeric score in [0.0, 1.0] (clamped).
            notes: Optional human-readable notes.

        Returns:
            The newly created :class:`StrategyEvaluation`, or ``None`` when
            the strategy is not registered.
        """
        with self._lock:
            self._ensure_agent(agent_id)
            strategy = self._strategies.get(agent_id, {}).get(strategy_id)
            if strategy is None:
                return None
            resolved_criterion = _normalize_criterion(criterion)
            evaluation = StrategyEvaluation(
                evaluation_id=_new_id(),
                agent_id=agent_id,
                strategy_id=strategy_id,
                criterion=resolved_criterion,
                score=_clamp(float(score)),
                outcome=str(outcome),
                notes=str(notes or ""),
                timestamp=_now(),
            )
            self._evaluations[agent_id].append(evaluation)
            if len(self._evaluations[agent_id]) > _MAX_EVALUATIONS_PER_AGENT:
                self._evaluations[agent_id] = self._evaluations[agent_id][
                    -_MAX_EVALUATIONS_PER_AGENT:
                ]
            self._evaluation_counter += 1
            self._record_event(
                MetaReasoningEventKind.STRATEGY_EVALUATED,
                {
                    "agent_id": agent_id,
                    "strategy_id": strategy_id,
                    "evaluation_id": evaluation.evaluation_id,
                    "criterion": resolved_criterion.value,
                    "score": evaluation.score,
                    "outcome": evaluation.outcome,
                },
            )
            return evaluation

    def get_evaluations(
        self,
        agent_id: str,
        strategy_id: Optional[str] = None,
    ) -> List[StrategyEvaluation]:
        """Return evaluations for an agent, optionally filtered by strategy.

        When ``strategy_id`` is provided, only evaluations for that
        strategy are returned. When ``None``, all evaluations for the
        agent are returned.
        """
        with self._lock:
            evals = list(self._evaluations.get(agent_id, []))
            if strategy_id is None:
                return evals
            return [e for e in evals if e.strategy_id == strategy_id]

    # ------------------------------------------------------------------
    # Meta-reflection
    # ------------------------------------------------------------------

    def generate_reflection(
        self,
        agent_id: str,
        trace_id: str,
    ) -> Optional[MetaReflection]:
        """Generate a higher-order reflection on a trace.

        The reflection is derived from the trace's score, the average
        confidence of its steps, and the average score of the strategy
        used (if any). It returns strengths, weaknesses, and
        recommendations for the agent.

        Args:
            agent_id: Identifier of the agent.
            trace_id: Identifier of the trace to reflect on.

        Returns:
            The newly created :class:`MetaReflection`, or ``None`` when
            the trace does not exist.
        """
        with self._lock:
            self._ensure_agent(agent_id)
            trace = self.get_trace(agent_id, trace_id)
            if trace is None:
                return None
            avg_step_confidence = 0.0
            if trace.steps:
                avg_step_confidence = sum(s.confidence for s in trace.steps) / len(
                    trace.steps
                )
            strategy = self._strategies.get(agent_id, {}).get(trace.strategy_id)
            strategy_score = strategy.avg_score if strategy is not None else 0.0
            quality = round(
                0.5 * trace.score + 0.3 * avg_step_confidence + 0.2 * strategy_score,
                4,
            )
            quality = _clamp(quality)
            strengths: List[str] = []
            weaknesses: List[str] = []
            recommendations: List[str] = []
            if trace.success:
                strengths.append("Reasoning produced a successful outcome")
            else:
                weaknesses.append("Reasoning did not produce a successful outcome")
                recommendations.append("Consider an alternative strategy next time")
            if avg_step_confidence >= 0.7:
                strengths.append("Reasoning steps were highly confident")
            elif avg_step_confidence < 0.4:
                weaknesses.append("Reasoning steps had low average confidence")
                recommendations.append("Gather more evidence before each step")
            if strategy is not None and strategy.avg_score >= 0.6:
                strengths.append(
                    f"Strategy {strategy.name} is performing well overall"
                )
            elif strategy is not None and strategy.avg_score < 0.4:
                weaknesses.append(
                    f"Strategy {strategy.name} is underperforming (score "
                    f"{strategy.avg_score})"
                )
                recommendations.append(
                    f"Consider adapting {strategy.name} or trying another strategy"
                )
            if len(trace.steps) > 5:
                weaknesses.append("Trace has many steps; consider compressing")
                recommendations.append("Consolidate redundant steps into summaries")
            if not recommendations:
                recommendations.append("Continue using the current strategy")
            reflection = MetaReflection(
                reflection_id=_new_id(),
                agent_id=agent_id,
                trace_id=trace_id,
                quality=quality,
                strengths=strengths,
                weaknesses=weaknesses,
                recommendations=recommendations,
                timestamp=_now(),
            )
            self._reflections[agent_id].append(reflection)
            if len(self._reflections[agent_id]) > _MAX_REFLECTIONS_PER_AGENT:
                self._reflections[agent_id] = self._reflections[agent_id][
                    -_MAX_REFLECTIONS_PER_AGENT:
                ]
            self._reflection_counter += 1
            self._record_event(
                MetaReasoningEventKind.REFLECTION_GENERATED,
                {
                    "agent_id": agent_id,
                    "trace_id": trace_id,
                    "reflection_id": reflection.reflection_id,
                    "quality": quality,
                },
            )
            return reflection

    def get_reflections(
        self,
        agent_id: str,
        limit: int = 20,
    ) -> List[MetaReflection]:
        """Return recent reflections for an agent, newest first."""
        with self._lock:
            reflections = self._reflections.get(agent_id, [])
            n = max(0, int(limit))
            if n == 0:
                return []
            return list(reversed(reflections))[:n]

    # ------------------------------------------------------------------
    # Strategy adaptation
    # ------------------------------------------------------------------

    def adapt_strategy(
        self,
        agent_id: str,
        strategy_id: str,
        parameters: Dict[str, Any],
        rationale: str = "",
        expected_improvement: float = 0.05,
    ) -> Optional[StrategyAdaptation]:
        """Adapt a strategy's parameters and record the change.

        Args:
            agent_id: Identifier of the agent.
            strategy_id: Identifier of the strategy to adapt.
            parameters: New parameter dictionary (replaces existing).
            rationale: Human-readable reason for the adaptation.
            expected_improvement: Expected improvement in avg_score as a
                float in [-1.0, 1.0] (clamped).

        Returns:
            The newly created :class:`StrategyAdaptation`, or ``None`` when
            the strategy is not registered.
        """
        with self._lock:
            self._ensure_agent(agent_id)
            strategy = self._strategies.get(agent_id, {}).get(strategy_id)
            if strategy is None:
                return None
            old_parameters = dict(strategy.parameters)
            new_parameters = dict(parameters or {})
            strategy.parameters = new_parameters
            strategy.updated_at = _now()
            adaptation = StrategyAdaptation(
                adaptation_id=_new_id(),
                agent_id=agent_id,
                strategy_id=strategy_id,
                old_parameters=old_parameters,
                new_parameters=new_parameters,
                rationale=str(rationale or ""),
                expected_improvement=_clamp(
                    float(expected_improvement), low=-1.0, high=1.0
                ),
                timestamp=_now(),
            )
            self._adaptations[agent_id].append(adaptation)
            if len(self._adaptations[agent_id]) > _MAX_ADAPTATIONS_PER_AGENT:
                self._adaptations[agent_id] = self._adaptations[agent_id][
                    -_MAX_ADAPTATIONS_PER_AGENT:
                ]
            self._adaptation_counter += 1
            self._record_event(
                MetaReasoningEventKind.STRATEGY_ADAPTED,
                {
                    "agent_id": agent_id,
                    "strategy_id": strategy_id,
                    "adaptation_id": adaptation.adaptation_id,
                    "expected_improvement": adaptation.expected_improvement,
                },
            )
            return adaptation

    def get_adaptations(
        self,
        agent_id: str,
        strategy_id: Optional[str] = None,
    ) -> List[StrategyAdaptation]:
        """Return adaptations for an agent, optionally filtered by strategy."""
        with self._lock:
            adaptations = list(self._adaptations.get(agent_id, []))
            if strategy_id is None:
                return adaptations
            return [a for a in adaptations if a.strategy_id == strategy_id]

    # ------------------------------------------------------------------
    # Events, Stats, Status, Snapshot
    # ------------------------------------------------------------------

    def list_events(
        self, limit: int = 100
    ) -> List[MetaReasoningEvent]:
        """Return the most recent meta-reasoning events, newest first."""
        with self._lock:
            n = max(0, int(limit))
            if n == 0:
                return []
            return list(reversed(self._events))[:n]

    def get_stats(self) -> MetaReasoningStats:
        """Return aggregate statistics about the meta-reasoning engine."""
        with self._lock:
            total_strategies = 0
            total_traces = 0
            total_evaluations = 0
            total_selections = 0
            total_adaptations = 0
            total_reflections = 0
            score_sum = 0.0
            scored = 0
            for agent_id, strategies in self._strategies.items():
                total_strategies += len(strategies)
                total_traces += len(self._traces.get(agent_id, []))
                total_evaluations += len(self._evaluations.get(agent_id, []))
                total_selections += len(self._selections.get(agent_id, []))
                total_adaptations += len(self._adaptations.get(agent_id, []))
                total_reflections += len(self._reflections.get(agent_id, []))
                for strat in strategies.values():
                    if strat.use_count > 0:
                        score_sum += strat.avg_score
                        scored += 1
            avg_score = round(score_sum / scored, 4) if scored else 0.0
            return MetaReasoningStats(
                total_agents=len(self._strategies),
                total_strategies=total_strategies,
                total_traces=total_traces,
                total_evaluations=total_evaluations,
                total_selections=total_selections,
                total_adaptations=total_adaptations,
                total_reflections=total_reflections,
                avg_strategy_score=avg_score,
            )

    def get_status(self) -> Dict[str, Any]:
        """Return a comprehensive status dictionary for diagnostics."""
        with self._lock:
            stats = self.get_stats()
            status: Dict[str, Any] = {
                "initialized": self._initialized,
                "total_agents": len(self._strategies),
                "total_strategies": stats.total_strategies,
                "total_traces": stats.total_traces,
                "total_evaluations": stats.total_evaluations,
                "total_selections": stats.total_selections,
                "total_adaptations": stats.total_adaptations,
                "total_reflections": stats.total_reflections,
                "total_events": len(self._events),
                "strategy_counter": self._strategy_counter,
                "trace_counter": self._trace_counter,
                "evaluation_counter": self._evaluation_counter,
                "selection_counter": self._selection_counter,
                "adaptation_counter": self._adaptation_counter,
                "reflection_counter": self._reflection_counter,
                "agent_counter": self._agent_counter,
                "avg_strategy_score": stats.avg_strategy_score,
                "capacities": {
                    "max_agents": _MAX_AGENTS,
                    "max_strategies_per_agent": _MAX_STRATEGIES_PER_AGENT,
                    "max_traces_per_agent": _MAX_TRACES_PER_AGENT,
                    "max_evaluations_per_agent": _MAX_EVALUATIONS_PER_AGENT,
                    "max_selections_per_agent": _MAX_SELECTIONS_PER_AGENT,
                    "max_adaptations_per_agent": _MAX_ADAPTATIONS_PER_AGENT,
                    "max_reflections_per_agent": _MAX_REFLECTIONS_PER_AGENT,
                    "max_events": _MAX_EVENTS,
                },
            }
            return status

    def get_snapshot(self) -> MetaReasoningSnapshot:
        """Return a complete snapshot of the meta-reasoning engine state."""
        with self._lock:
            all_strategies: List[ReasoningStrategy] = []
            all_traces: List[ReasoningTrace] = []
            all_evaluations: List[StrategyEvaluation] = []
            all_selections: List[StrategySelection] = []
            all_adaptations: List[StrategyAdaptation] = []
            all_reflections: List[MetaReflection] = []
            for agent_id, strategies in self._strategies.items():
                all_strategies.extend(strategies.values())
                all_traces.extend(self._traces.get(agent_id, []))
                all_evaluations.extend(self._evaluations.get(agent_id, []))
                all_selections.extend(self._selections.get(agent_id, []))
                all_adaptations.extend(self._adaptations.get(agent_id, []))
                all_reflections.extend(self._reflections.get(agent_id, []))
            return MetaReasoningSnapshot(
                initialized=self._initialized,
                strategies=all_strategies,
                traces=all_traces,
                evaluations=all_evaluations,
                selections=all_selections,
                adaptations=all_adaptations,
                reflections=all_reflections,
                events=list(self._events),
                stats=self.get_stats(),
            )

    # ------------------------------------------------------------------
    # Reset
    # ------------------------------------------------------------------

    def reset(self) -> None:
        """Clear all tracked state and re-seed baseline data.

        Unlike a one-shot clear, ``reset`` re-seeds the baseline
        meta-reasoning data so the engine returns to a freshly
        initialised state.
        """
        with self._lock:
            self._strategies.clear()
            self._traces.clear()
            self._evaluations.clear()
            self._selections.clear()
            self._adaptations.clear()
            self._reflections.clear()
            self._events.clear()
            self._strategy_counter = 0
            self._trace_counter = 0
            self._evaluation_counter = 0
            self._selection_counter = 0
            self._adaptation_counter = 0
            self._reflection_counter = 0
            self._agent_counter = 0
            self._seed_data()

    # ------------------------------------------------------------------
    # Seed data
    # ------------------------------------------------------------------

    def _seed_data(self) -> None:
        """Populate the engine with baseline SparkLabs meta-reasoning data.

        Seeds two agents (``agent_alpha`` -- a tactical reasoner,
        ``agent_beta`` -- a creative reasoner) with four strategies each,
        three reasoning traces, four strategy evaluations, two strategy
        selections, two adaptations, and two meta-reflections.
        """
        # --- Agent Alpha: the tactical reasoner -------------------------
        self._ensure_agent("agent_alpha")
        alpha_deductive = self.register_strategy(
            "agent_alpha",
            "alpha_deductive",
            ReasoningStrategyType.DEDUCTIVE,
            description="Top-down deductive reasoning for logic problems",
            domain_affinity=ProblemDomain.LOGIC,
            parameters={"depth": 3, "rigor": 0.9},
            status=StrategyStatus.FAVORITE,
        )
        alpha_inductive = self.register_strategy(
            "agent_alpha",
            "alpha_inductive",
            ReasoningStrategyType.INDUCTIVE,
            description="Bottom-up inductive generalisation from examples",
            domain_affinity=ProblemDomain.PREDICTION,
            parameters={"sample_size": 50, "confidence_threshold": 0.7},
        )
        alpha_causal = self.register_strategy(
            "agent_alpha",
            "alpha_causal",
            ReasoningStrategyType.CAUSAL,
            description="Cause-and-effect chain modelling for diagnosis",
            domain_affinity=ProblemDomain.DIAGNOSIS,
            parameters={"max_chain_length": 5},
        )
        alpha_heuristic = self.register_strategy(
            "agent_alpha",
            "alpha_heuristic",
            ReasoningStrategyType.HEURISTIC,
            description="Fast-and-frugal heuristic for routine planning",
            domain_affinity=ProblemDomain.PLANNING,
            parameters={"lookahead": 2},
            status=StrategyStatus.EXPERIMENTAL,
        )

        # Traces for agent_alpha.
        if alpha_deductive is not None:
            self.record_trace(
                "agent_alpha",
                "Prove the implication from the axioms",
                alpha_deductive.strategy_id,
                steps=[
                    {
                        "premise": "All agents have a reasoning engine",
                        "inference_rule": "universal_instantiation",
                        "conclusion": "agent_alpha has a reasoning engine",
                        "confidence": 0.95,
                    },
                    {
                        "premise": "agent_alpha has a reasoning engine",
                        "inference_rule": "modus_ponens",
                        "conclusion": "agent_alpha can reason about itself",
                        "confidence": 0.9,
                    },
                ],
                final_answer="agent_alpha can reason about itself",
                success=True,
                score=0.92,
                domain=ProblemDomain.LOGIC,
            )
        if alpha_inductive is not None:
            self.record_trace(
                "agent_alpha",
                "Predict enemy movement from prior encounters",
                alpha_inductive.strategy_id,
                steps=[
                    {
                        "premise": "In 7/10 prior encounters enemies flanked left",
                        "inference_rule": "frequency_generalization",
                        "conclusion": "Enemy will likely flank left again",
                        "confidence": 0.7,
                    },
                ],
                final_answer="flank left",
                success=True,
                score=0.78,
                domain=ProblemDomain.PREDICTION,
            )
        if alpha_heuristic is not None:
            self.record_trace(
                "agent_alpha",
                "Choose the next waypoint during a routine patrol",
                alpha_heuristic.strategy_id,
                steps=[
                    {
                        "premise": "Nearest unvisited waypoint is 3 steps away",
                        "inference_rule": "nearest_neighbour",
                        "conclusion": "Move to the nearest unvisited waypoint",
                        "confidence": 0.6,
                    },
                ],
                final_answer="move to nearest waypoint",
                success=False,
                score=0.45,
                domain=ProblemDomain.PLANNING,
            )

        # Evaluations for agent_alpha.
        self.evaluate_strategy(
            "agent_alpha",
            alpha_deductive.strategy_id,
            outcome="success",
            criterion=EvaluationCriterion.ACCURACY,
            score=0.93,
            notes="Clean proofs with strong confidence",
        )
        self.evaluate_strategy(
            "agent_alpha",
            alpha_inductive.strategy_id,
            outcome="success",
            criterion=EvaluationCriterion.SPEED,
            score=0.75,
            notes="Fast generalisation from small samples",
        )
        self.evaluate_strategy(
            "agent_alpha",
            alpha_causal.strategy_id,
            outcome="neutral",
            criterion=EvaluationCriterion.INTERPRETABILITY,
            score=0.82,
            notes="Causal chains are easy to follow",
        )
        self.evaluate_strategy(
            "agent_alpha",
            alpha_heuristic.strategy_id,
            outcome="failure",
            criterion=EvaluationCriterion.ROBUSTNESS,
            score=0.4,
            notes="Heuristic failed on an unfamiliar waypoint layout",
        )

        # Selections for agent_alpha.
        alpha_selection = self.select_strategy(
            "agent_alpha",
            "Plan the ambush",
            domain=ProblemDomain.PLANNING,
            mode=SelectionMode.HYBRID,
        )
        # A second selection to satisfy the "2+ selections" requirement.
        self.select_strategy(
            "agent_alpha",
            "Diagnose the engine anomaly",
            domain=ProblemDomain.DIAGNOSIS,
            mode=SelectionMode.EXPLOITATION,
        )

        # Adaptations for agent_alpha.
        self.adapt_strategy(
            "agent_alpha",
            alpha_heuristic.strategy_id,
            parameters={"lookahead": 4, "fallback": "alpha_causal"},
            rationale="Heuristic failed with lookahead=2; widen search and add fallback",
            expected_improvement=0.15,
        )

        # Reflections for agent_alpha. Pick a trace to reflect on; we use
        # the first recorded trace.
        alpha_traces = self.get_traces("agent_alpha", limit=1)
        if alpha_traces:
            self.generate_reflection("agent_alpha", alpha_traces[0].trace_id)
            # Generate a second reflection on a different trace if available.
            all_alpha_traces = self.get_traces("agent_alpha", limit=10)
            if len(all_alpha_traces) > 1:
                self.generate_reflection(
                    "agent_alpha", all_alpha_traces[1].trace_id
                )

        # --- Agent Beta: the creative reasoner --------------------------
        self._ensure_agent("agent_beta")
        beta_abductive = self.register_strategy(
            "agent_beta",
            "beta_abductive",
            ReasoningStrategyType.ABDUCTIVE,
            description="Best-explanation inference for creative problem solving",
            domain_affinity=ProblemDomain.CREATIVE,
            parameters={"hypotheses": 5, "explanation_threshold": 0.6},
            status=StrategyStatus.FAVORITE,
        )
        beta_analogical = self.register_strategy(
            "agent_beta",
            "beta_analogical",
            ReasoningStrategyType.ANALOGICAL,
            description="Mapping knowledge from analogous past problems",
            domain_affinity=ProblemDomain.PLANNING,
            parameters={"mapping_depth": 3},
        )
        beta_bayesian = self.register_strategy(
            "agent_beta",
            "beta_bayesian",
            ReasoningStrategyType.BAYESIAN,
            description="Probabilistic reasoning under uncertainty",
            domain_affinity=ProblemDomain.PREDICTION,
            parameters={"prior_strength": 0.5, "update_rate": 0.1},
        )
        beta_counterfactual = self.register_strategy(
            "agent_beta",
            "beta_counterfactual",
            ReasoningStrategyType.COUNTERFACTUAL,
            description="What-if analysis for evaluating alternative decisions",
            domain_affinity=ProblemDomain.DIAGNOSIS,
            parameters={"branching_factor": 4},
            status=StrategyStatus.EXPERIMENTAL,
        )

        # Traces for agent_beta.
        if beta_abductive is not None:
            self.record_trace(
                "agent_beta",
                "Explain the strange behaviour of the NPCs",
                beta_abductive.strategy_id,
                steps=[
                    {
                        "premise": "NPCs are gathering at the same spot each night",
                        "inference_rule": "inference_to_best_explanation",
                        "conclusion": "A new quest is being seeded by the engine",
                        "confidence": 0.65,
                    },
                ],
                final_answer="engine-seeded quest",
                success=True,
                score=0.7,
                domain=ProblemDomain.CREATIVE,
            )
        if beta_analogical is not None:
            self.record_trace(
                "agent_beta",
                "Design a new puzzle by analogy to an old one",
                beta_analogical.strategy_id,
                steps=[
                    {
                        "premise": "Old puzzle used switches and timed doors",
                        "inference_rule": "structural_mapping",
                        "conclusion": "New puzzle can reuse switches and timed doors",
                        "confidence": 0.8,
                    },
                ],
                final_answer="reuse switch+door template",
                success=True,
                score=0.85,
                domain=ProblemDomain.PLANNING,
            )

        # Evaluations for agent_beta.
        self.evaluate_strategy(
            "agent_beta",
            beta_abductive.strategy_id,
            outcome="success",
            criterion=EvaluationCriterion.ACCURACY,
            score=0.74,
            notes="Good at generating plausible hypotheses",
        )
        self.evaluate_strategy(
            "agent_beta",
            beta_analogical.strategy_id,
            outcome="success",
            criterion=EvaluationCriterion.INTERPRETABILITY,
            score=0.88,
            notes="Analogical mappings are easy to explain",
        )
        self.evaluate_strategy(
            "agent_beta",
            beta_bayesian.strategy_id,
            outcome="neutral",
            criterion=EvaluationCriterion.COST,
            score=0.55,
            notes="Bayesian updates are computationally moderate",
        )

        # Selections for agent_beta.
        self.select_strategy(
            "agent_beta",
            "Compose a new quest narrative",
            domain=ProblemDomain.CREATIVE,
            mode=SelectionMode.EXPLORATION,
        )
        self.select_strategy(
            "agent_beta",
            "Forecast the next player behaviour",
            domain=ProblemDomain.PREDICTION,
            mode=SelectionMode.EXPLOITATION,
        )

        # Adaptations for agent_beta.
        self.adapt_strategy(
            "agent_beta",
            beta_bayesian.strategy_id,
            parameters={"prior_strength": 0.6, "update_rate": 0.15},
            rationale="Increase learning rate to respond to new player behaviours",
            expected_improvement=0.1,
        )

        # Reflections for agent_beta.
        beta_traces = self.get_traces("agent_beta", limit=1)
        if beta_traces:
            self.generate_reflection("agent_beta", beta_traces[0].trace_id)

        # Suppress unused-variable warning for the alpha_selection reference.
        _ = alpha_selection


# ---------------------------------------------------------------------------
# Module-Level Accessor
# ---------------------------------------------------------------------------


def get_meta_reasoning() -> MetaReasoningEngine:
    """Return the singleton MetaReasoningEngine instance."""
    return MetaReasoningEngine.get_instance()
