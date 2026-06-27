"""
SparkLabs Agent - Self-Reflection Engine

Autonomous self-reflection and self-improvement system that enables agents
to analyze their own performance, identify patterns, and generate improvement
strategies. Implements a continuous improvement loop where agents observe
their own behavior, evaluate outcomes, reflect on what worked and what didn't,
and adapt their strategies accordingly.

Architecture:
  SelfReflectionEngine (Singleton)
    |-- ReflectionSession (individual reflection cycle with phases)
    |-- PerformanceTrace (recorded execution with metrics)
    |-- InsightGenerator (extracts patterns and lessons from traces)
    |-- StrategyAdapter (generates and applies improvement strategies)
    |-- MetaEvaluator (evaluates the quality of reflections themselves)

Reflection Phases:
  - OBSERVE: Collect execution traces and performance data
  - ANALYZE: Identify patterns, bottlenecks, and anomalies
  - REFLECT: Generate insights about what worked and why
  - ADAPT: Create and apply improvement strategies
  - VERIFY: Validate that adaptations improved performance

Strategy Types:
  - BEHAVIORAL: Change how actions are selected and executed
  - COGNITIVE: Modify reasoning, planning, and decision-making
  - MEMORY: Adjust memory storage, retrieval, and consolidation
  - LEARNING: Update skill library and knowledge base
  - TOOL_USE: Refine tool selection and parameter optimization

Usage:
    sr = get_self_reflection()
    sr.initialize()

    # Start a reflection session
    session = sr.start_session("Improve NPC dialogue generation quality")

    # Record execution traces
    sr.record_trace(session.session_id, PerformanceTrace(
        task="generate_npc_dialogue",
        outcome="partial_success",
        metrics={"response_time_ms": 350, "quality_score": 0.72},
    ))

    # Generate insights and adapt
    insights = sr.reflect(session.session_id)
    adaptations = sr.adapt(session.session_id)

    sr.shutdown()
"""

from __future__ import annotations

import threading
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple


# =============================================================================
# Enums
# =============================================================================


class ReflectionPhase(Enum):
    """Phases of the self-reflection cycle."""
    OBSERVE = "observe"    # Collect execution traces
    ANALYZE = "analyze"    # Identify patterns and anomalies
    REFLECT = "reflect"    # Generate insights
    ADAPT = "adapt"        # Create improvement strategies
    VERIFY = "verify"      # Validate improvements


class InsightType(Enum):
    """Types of insights generated through reflection."""
    PERFORMANCE = "performance"        # Speed, resource usage observations
    QUALITY = "quality"                # Output quality observations
    PATTERN = "pattern"                # Recurring behavioral patterns
    BOTTLENECK = "bottleneck"          # Identified constraints
    OPPORTUNITY = "opportunity"        # Potential improvement areas
    RISK = "risk"                      # Identified risks and failure modes
    STRATEGY = "strategy"              # Strategic insights


class StrategyType(Enum):
    """Types of improvement strategies."""
    BEHAVIORAL = "behavioral"    # Change action selection/execution
    COGNITIVE = "cognitive"      # Modify reasoning and planning
    MEMORY = "memory"            # Adjust memory management
    LEARNING = "learning"        # Update skill library
    TOOL_USE = "tool_use"        # Refine tool selection
    COMMUNICATION = "communication"  # Improve inter-agent communication
    RESOURCE = "resource"        # Optimize resource allocation


class TraceOutcome(Enum):
    """Outcome of a traced execution."""
    SUCCESS = "success"
    PARTIAL_SUCCESS = "partial_success"
    FAILURE = "failure"
    TIMEOUT = "timeout"
    CANCELLED = "cancelled"
    ERROR = "error"


class InsightConfidence(Enum):
    """Confidence level of a generated insight."""
    HIGH = "high"          # Strong evidence, multiple confirmations
    MEDIUM = "medium"      # Some evidence, needs more validation
    LOW = "low"            # Weak evidence, speculative
    TENTATIVE = "tentative"  # Initial hypothesis, unverified


# =============================================================================
# Data Classes
# =============================================================================


@dataclass
class PerformanceTrace:
    """A recorded execution trace with performance metrics."""
    trace_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    task: str = ""
    outcome: TraceOutcome = TraceOutcome.SUCCESS
    metrics: Dict[str, float] = field(default_factory=dict)
    context: Dict[str, Any] = field(default_factory=dict)
    actions_taken: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    timestamp: float = field(default_factory=time.time)
    duration_ms: float = 0.0
    memory_usage_mb: float = 0.0
    cpu_usage_percent: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "trace_id": self.trace_id,
            "task": self.task,
            "outcome": self.outcome.value,
            "metrics": self.metrics,
            "context": self.context,
            "actions_taken": self.actions_taken,
            "errors": self.errors,
            "timestamp": self.timestamp,
            "duration_ms": self.duration_ms,
            "memory_usage_mb": self.memory_usage_mb,
            "cpu_usage_percent": self.cpu_usage_percent,
        }


@dataclass
class ReflectionInsight:
    """An insight generated through self-reflection."""
    insight_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    insight_type: InsightType = InsightType.PERFORMANCE
    description: str = ""
    evidence: List[str] = field(default_factory=list)
    confidence: InsightConfidence = InsightConfidence.MEDIUM
    related_traces: List[str] = field(default_factory=list)
    impact_score: float = 0.5
    actionable: bool = True
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "insight_id": self.insight_id,
            "insight_type": self.insight_type.value,
            "description": self.description,
            "evidence": self.evidence,
            "confidence": self.confidence.value,
            "related_traces": self.related_traces,
            "impact_score": self.impact_score,
            "actionable": self.actionable,
            "created_at": self.created_at,
        }


@dataclass
class ImprovementStrategy:
    """A strategy for improving agent performance."""
    strategy_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    name: str = ""
    strategy_type: StrategyType = StrategyType.BEHAVIORAL
    description: str = ""
    target_area: str = ""
    steps: List[Dict[str, Any]] = field(default_factory=list)
    expected_impact: float = 0.5
    risk_level: float = 0.3
    prerequisites: List[str] = field(default_factory=list)
    applied: bool = False
    applied_at: Optional[float] = None
    verified: bool = False
    verified_impact: Optional[float] = None
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "strategy_id": self.strategy_id,
            "name": self.name,
            "strategy_type": self.strategy_type.value,
            "description": self.description,
            "target_area": self.target_area,
            "steps": self.steps,
            "expected_impact": self.expected_impact,
            "risk_level": self.risk_level,
            "prerequisites": self.prerequisites,
            "applied": self.applied,
            "applied_at": self.applied_at,
            "verified": self.verified,
            "verified_impact": self.verified_impact,
            "created_at": self.created_at,
        }


@dataclass
class ReflectionSession:
    """A self-reflection session tracking a full improvement cycle."""
    session_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    goal: str = ""
    phase: ReflectionPhase = ReflectionPhase.OBSERVE
    traces: List[PerformanceTrace] = field(default_factory=list)
    insights: List[ReflectionInsight] = field(default_factory=list)
    strategies: List[ImprovementStrategy] = field(default_factory=list)
    meta_notes: List[str] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    completed_at: Optional[float] = None
    improvement_score: Optional[float] = None
    status: str = "active"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "session_id": self.session_id,
            "goal": self.goal,
            "phase": self.phase.value,
            "trace_count": len(self.traces),
            "insight_count": len(self.insights),
            "strategy_count": len(self.strategies),
            "meta_notes": self.meta_notes,
            "created_at": self.created_at,
            "completed_at": self.completed_at,
            "improvement_score": self.improvement_score,
            "status": self.status,
        }


@dataclass
class ReflectionReport:
    """Comprehensive report of a reflection session."""
    report_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    session_id: str = ""
    goal: str = ""
    summary: str = ""
    key_insights: List[str] = field(default_factory=list)
    strategies_applied: List[str] = field(default_factory=list)
    performance_delta: Dict[str, float] = field(default_factory=dict)
    recommendations: List[str] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "report_id": self.report_id,
            "session_id": self.session_id,
            "goal": self.goal,
            "summary": self.summary,
            "key_insights": self.key_insights,
            "strategies_applied": self.strategies_applied,
            "performance_delta": self.performance_delta,
            "recommendations": self.recommendations,
            "created_at": self.created_at,
        }


# =============================================================================
# SelfReflectionEngine (Singleton)
# =============================================================================


class SelfReflectionEngine:
    """Autonomous self-reflection and self-improvement engine.

    Drives continuous agent improvement through systematic observation,
    analysis, reflection, and adaptation. Enables agents to learn from
    their own experiences and automatically optimize their behavior.

    Usage:
        sr = SelfReflectionEngine.get_instance()
        sr.initialize()

        session = sr.start_session("Optimize game code generation")
        sr.record_trace(session.session_id, trace)
        insights = sr.reflect(session.session_id)
        sr.adapt(session.session_id)
    """

    _instance: Optional["SelfReflectionEngine"] = None
    _instance_lock = threading.RLock()

    def __init__(self) -> None:
        if SelfReflectionEngine._instance is not None:
            raise RuntimeError("Use SelfReflectionEngine.get_instance()")
        self._initialized: bool = False
        self._lock = threading.RLock()
        self._sessions: Dict[str, ReflectionSession] = {}
        self._session_history: List[ReflectionSession] = []
        self._global_insights: List[ReflectionInsight] = []
        self._strategy_library: Dict[str, ImprovementStrategy] = {}
        self._reports: Dict[str, ReflectionReport] = {}
        self._trace_buffer: List[PerformanceTrace] = []
        self._total_sessions: int = 0
        self._total_insights: int = 0
        self._total_strategies: int = 0

    @classmethod
    def get_instance(cls) -> "SelfReflectionEngine":
        if cls._instance is None:
            with cls._instance_lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    # -------------------------------------------------------------------------
    # Lifecycle
    # -------------------------------------------------------------------------

    def initialize(self, config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        with self._lock:
            if self._initialized:
                return {"status": "already_initialized", "success": True}

            self._register_default_strategies()
            self._initialized = True

            return {
                "status": "initialized",
                "success": True,
                "default_strategies": len(self._strategy_library),
            }

    def shutdown(self) -> Dict[str, Any]:
        with self._lock:
            self._initialized = False
            return {
                "success": True,
                "total_sessions": self._total_sessions,
                "total_insights": self._total_insights,
                "total_strategies": self._total_strategies,
            }

    def _register_default_strategies(self) -> None:
        """Register built-in improvement strategies."""
        defaults = [
            ImprovementStrategy(
                name="batch_similar_actions",
                strategy_type=StrategyType.BEHAVIORAL,
                description="Batch similar actions together to reduce overhead",
                target_area="action_execution",
                steps=[
                    {"action": "group_similar", "description": "Identify actions with shared parameters"},
                    {"action": "merge_params", "description": "Merge parameters into batch request"},
                    {"action": "execute_batch", "description": "Execute all actions in single batch"},
                ],
                expected_impact=0.3,
                risk_level=0.1,
            ),
            ImprovementStrategy(
                name="cache_frequent_queries",
                strategy_type=StrategyType.MEMORY,
                description="Cache frequently accessed data to reduce retrieval time",
                target_area="memory_retrieval",
                steps=[
                    {"action": "identify_hot_keys", "description": "Find most frequently accessed memory keys"},
                    {"action": "preload_cache", "description": "Preload hot data into working memory"},
                    {"action": "invalidate_stale", "description": "Set up cache invalidation for stale entries"},
                ],
                expected_impact=0.4,
                risk_level=0.15,
            ),
            ImprovementStrategy(
                name="simplify_reasoning_chain",
                strategy_type=StrategyType.COGNITIVE,
                description="Simplify reasoning chains by removing redundant steps",
                target_area="reasoning",
                steps=[
                    {"action": "analyze_chain", "description": "Analyze reasoning chain for redundancies"},
                    {"action": "prune_steps", "description": "Remove steps that don't contribute to conclusion"},
                    {"action": "merge_steps", "description": "Merge adjacent steps with similar premises"},
                ],
                expected_impact=0.25,
                risk_level=0.2,
            ),
            ImprovementStrategy(
                name="prioritize_high_value_actions",
                strategy_type=StrategyType.BEHAVIORAL,
                description="Prioritize actions with highest expected value",
                target_area="action_selection",
                steps=[
                    {"action": "score_actions", "description": "Score all available actions by expected value"},
                    {"action": "rank_actions", "description": "Rank actions by score descending"},
                    {"action": "select_top", "description": "Select top N actions within resource budget"},
                ],
                expected_impact=0.35,
                risk_level=0.1,
            ),
            ImprovementStrategy(
                name="parallel_independent_tasks",
                strategy_type=StrategyType.RESOURCE,
                description="Execute independent tasks in parallel",
                target_area="task_execution",
                steps=[
                    {"action": "identify_independent", "description": "Find tasks with no dependencies"},
                    {"action": "allocate_resources", "description": "Allocate resources for parallel execution"},
                    {"action": "execute_parallel", "description": "Execute tasks concurrently"},
                ],
                expected_impact=0.5,
                risk_level=0.25,
            ),
        ]

        for strategy in defaults:
            self._strategy_library[strategy.name] = strategy

    # -------------------------------------------------------------------------
    # Session Management
    # -------------------------------------------------------------------------

    def start_session(self, goal: str) -> Dict[str, Any]:
        """Start a new self-reflection session."""
        session = ReflectionSession(goal=goal)
        with self._lock:
            self._sessions[session.session_id] = session
            self._total_sessions += 1
        return session.to_dict()

    def end_session(self, session_id: str) -> Dict[str, Any]:
        """End a reflection session and generate a report."""
        with self._lock:
            session = self._sessions.pop(session_id, None)
            if not session:
                return {"success": False, "error": "Session not found"}

            session.completed_at = time.time()
            session.status = "completed"

            # Calculate improvement score
            if session.strategies:
                session.improvement_score = sum(
                    s.expected_impact for s in session.strategies
                ) / len(session.strategies)

            self._session_history.append(session)
            if len(self._session_history) > 500:
                self._session_history = self._session_history[-250:]

            # Generate report
            report = self._generate_report(session)
            self._reports[report.report_id] = report

            return {
                "success": True,
                "session": session.to_dict(),
                "report": report.to_dict(),
            }

    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get a reflection session by ID."""
        session = self._sessions.get(session_id)
        if session:
            return session.to_dict()
        for s in self._session_history:
            if s.session_id == session_id:
                return s.to_dict()
        return None

    # -------------------------------------------------------------------------
    # Trace Recording
    # -------------------------------------------------------------------------

    def record_trace(self, session_id: str, trace: PerformanceTrace) -> Dict[str, Any]:
        """Record a performance trace for a session."""
        with self._lock:
            session = self._sessions.get(session_id)
            if not session:
                # Buffer traces for unregistered sessions
                self._trace_buffer.append(trace)
                return {"success": True, "trace_id": trace.trace_id, "buffered": True}

            session.traces.append(trace)
            # Auto-advance phase if enough traces collected
            if len(session.traces) >= 5 and session.phase == ReflectionPhase.OBSERVE:
                session.phase = ReflectionPhase.ANALYZE

            return {"success": True, "trace_id": trace.trace_id, "session_id": session_id}

    def record_traces(self, session_id: str,
                      traces: List[PerformanceTrace]) -> Dict[str, Any]:
        """Record multiple traces at once."""
        results = []
        for trace in traces:
            results.append(self.record_trace(session_id, trace))
        return {"success": True, "recorded": len(results), "results": results}

    # -------------------------------------------------------------------------
    # Reflection
    # -------------------------------------------------------------------------

    def reflect(self, session_id: str) -> Dict[str, Any]:
        """Perform reflection on collected traces to generate insights."""
        with self._lock:
            session = self._sessions.get(session_id)
            if not session:
                return {"success": False, "error": "Session not found"}

            if not session.traces:
                return {"success": False, "error": "No traces to reflect on"}

            session.phase = ReflectionPhase.REFLECT

            insights = self._analyze_traces(session.traces)
            session.insights.extend(insights)
            self._global_insights.extend(insights)
            self._total_insights += len(insights)

            session.phase = ReflectionPhase.ADAPT

            return {
                "success": True,
                "session_id": session_id,
                "insights_generated": len(insights),
                "insights": [i.to_dict() for i in insights],
            }

    def _analyze_traces(self, traces: List[PerformanceTrace]) -> List[ReflectionInsight]:
        """Analyze traces to generate insights."""
        insights = []

        if not traces:
            return insights

        # Performance analysis
        durations = [t.duration_ms for t in traces if t.duration_ms > 0]
        if durations:
            avg_duration = sum(durations) / len(durations)
            if avg_duration > 1000:
                insights.append(ReflectionInsight(
                    insight_type=InsightType.PERFORMANCE,
                    description=f"Average task duration ({avg_duration:.0f}ms) exceeds threshold (1000ms)",
                    confidence=InsightConfidence.HIGH,
                    impact_score=0.7,
                    related_traces=[t.trace_id for t in traces if t.duration_ms > 1000],
                ))

        # Outcome analysis
        failures = [t for t in traces if t.outcome in (TraceOutcome.FAILURE, TraceOutcome.ERROR)]
        if failures:
            common_errors = {}
            for t in failures:
                for err in t.errors:
                    common_errors[err] = common_errors.get(err, 0) + 1
            if common_errors:
                top_error = max(common_errors, key=common_errors.get)
                insights.append(ReflectionInsight(
                    insight_type=InsightType.BOTTLENECK,
                    description=f"Recurring error pattern: '{top_error}' (occurred {common_errors[top_error]} times)",
                    confidence=InsightConfidence.HIGH,
                    impact_score=0.8,
                    related_traces=[t.trace_id for t in failures],
                ))

        # Pattern analysis
        success_rate = len([t for t in traces if t.outcome == TraceOutcome.SUCCESS]) / len(traces)
        if success_rate < 0.5:
            insights.append(ReflectionInsight(
                insight_type=InsightType.PATTERN,
                description=f"Low success rate ({success_rate:.1%}) indicates systematic issues",
                confidence=InsightConfidence.MEDIUM,
                impact_score=0.6,
                related_traces=[t.trace_id for t in traces],
            ))
        elif success_rate > 0.9:
            insights.append(ReflectionInsight(
                insight_type=InsightType.OPPORTUNITY,
                description=f"High success rate ({success_rate:.1%}) - identify success factors for replication",
                confidence=InsightConfidence.HIGH,
                impact_score=0.4,
                related_traces=[t.trace_id for t in traces if t.outcome == TraceOutcome.SUCCESS],
            ))

        # Resource analysis
        high_memory = [t for t in traces if t.memory_usage_mb > 500]
        if high_memory:
            insights.append(ReflectionInsight(
                insight_type=InsightType.RISK,
                description=f"High memory usage detected in {len(high_memory)} traces",
                confidence=InsightConfidence.MEDIUM,
                impact_score=0.5,
                related_traces=[t.trace_id for t in high_memory],
            ))

        return insights

    # -------------------------------------------------------------------------
    # Adaptation
    # -------------------------------------------------------------------------

    def adapt(self, session_id: str) -> Dict[str, Any]:
        """Generate and apply improvement strategies based on insights."""
        with self._lock:
            session = self._sessions.get(session_id)
            if not session:
                return {"success": False, "error": "Session not found"}

            if not session.insights:
                return {"success": False, "error": "No insights to adapt from"}

            session.phase = ReflectionPhase.ADAPT

            # Match strategies to insights
            strategies = self._match_strategies(session.insights)
            session.strategies.extend(strategies)
            self._total_strategies += len(strategies)

            # Apply strategies
            applied = []
            for strategy in strategies:
                result = self._apply_strategy(strategy)
                applied.append(result)

            return {
                "success": True,
                "session_id": session_id,
                "strategies_generated": len(strategies),
                "strategies": [s.to_dict() for s in strategies],
                "applied": applied,
            }

    def _match_strategies(self,
                          insights: List[ReflectionInsight]) -> List[ImprovementStrategy]:
        """Match insights to appropriate improvement strategies."""
        matched = []

        insight_type_to_strategy = {
            InsightType.PERFORMANCE: StrategyType.BEHAVIORAL,
            InsightType.BOTTLENECK: StrategyType.RESOURCE,
            InsightType.PATTERN: StrategyType.COGNITIVE,
            InsightType.QUALITY: StrategyType.LEARNING,
            InsightType.RISK: StrategyType.MEMORY,
            InsightType.OPPORTUNITY: StrategyType.TOOL_USE,
        }

        for insight in insights:
            target_strategy_type = insight_type_to_strategy.get(
                insight.insight_type, StrategyType.BEHAVIORAL
            )

            # Find matching strategies from library
            candidates = [
                s for s in self._strategy_library.values()
                if s.strategy_type == target_strategy_type and not s.applied
            ]

            if candidates:
                # Pick the best match based on expected impact
                candidates.sort(key=lambda s: s.expected_impact, reverse=True)
                best = candidates[0]
                matched.append(ImprovementStrategy(
                    name=f"{best.name}_{insight.insight_id[:8]}",
                    strategy_type=best.strategy_type,
                    description=f"Applied to address: {insight.description}",
                    target_area=best.target_area,
                    steps=best.steps,
                    expected_impact=best.expected_impact * insight.impact_score,
                    risk_level=best.risk_level,
                    prerequisites=best.prerequisites,
                ))

        return matched

    def _apply_strategy(self, strategy: ImprovementStrategy) -> Dict[str, Any]:
        """Apply an improvement strategy."""
        strategy.applied = True
        strategy.applied_at = time.time()
        return {
            "strategy_id": strategy.strategy_id,
            "name": strategy.name,
            "applied": True,
            "applied_at": strategy.applied_at,
        }

    # -------------------------------------------------------------------------
    # Verification
    # -------------------------------------------------------------------------

    def verify(self, session_id: str) -> Dict[str, Any]:
        """Verify that applied strategies improved performance."""
        with self._lock:
            session = self._sessions.get(session_id)
            if not session:
                return {"success": False, "error": "Session not found"}

            session.phase = ReflectionPhase.VERIFY

            verified = []
            for strategy in session.strategies:
                if strategy.applied and not strategy.verified:
                    # Simulate verification by checking metrics delta
                    pre_traces = session.traces[:len(session.traces)//2]
                    post_traces = session.traces[len(session.traces)//2:]

                    if pre_traces and post_traces:
                        pre_avg = sum(t.duration_ms for t in pre_traces) / len(pre_traces)
                        post_avg = sum(t.duration_ms for t in post_traces) / len(post_traces)
                        improvement = (pre_avg - post_avg) / max(pre_avg, 1)
                        strategy.verified = True
                        strategy.verified_impact = improvement
                        verified.append({
                            "strategy": strategy.name,
                            "verified": True,
                            "impact": improvement,
                        })

            return {
                "success": True,
                "session_id": session_id,
                "verified": verified,
            }

    # -------------------------------------------------------------------------
    # Reporting
    # -------------------------------------------------------------------------

    def _generate_report(self, session: ReflectionSession) -> ReflectionReport:
        """Generate a comprehensive reflection report."""
        summary_parts = []
        if session.insights:
            summary_parts.append(f"Generated {len(session.insights)} insights")
        if session.strategies:
            summary_parts.append(f"Applied {len(session.strategies)} strategies")

        return ReflectionReport(
            session_id=session.session_id,
            goal=session.goal,
            summary=". ".join(summary_parts) if summary_parts else "No significant findings",
            key_insights=[i.description for i in session.insights[:5]],
            strategies_applied=[s.name for s in session.strategies if s.applied],
            recommendations=[
                "Continue monitoring task performance",
                "Review high-impact strategies for permanence",
                "Share successful strategies across agent teams",
            ],
        )

    def get_report(self, report_id: str) -> Optional[Dict[str, Any]]:
        """Get a reflection report by ID."""
        report = self._reports.get(report_id)
        return report.to_dict() if report else None

    # -------------------------------------------------------------------------
    # Queries
    # -------------------------------------------------------------------------

    def get_status(self) -> Dict[str, Any]:
        """Get current engine status."""
        with self._lock:
            return {
                "initialized": self._initialized,
                "active_sessions": len(self._sessions),
                "total_sessions": self._total_sessions,
                "total_insights": self._total_insights,
                "total_strategies": self._total_strategies,
                "strategy_library_size": len(self._strategy_library),
                "reports_generated": len(self._reports),
            }

    def get_global_insights(self, insight_type: Optional[InsightType] = None,
                            limit: int = 50) -> List[Dict[str, Any]]:
        """Get global insights across all sessions."""
        insights = self._global_insights
        if insight_type:
            insights = [i for i in insights if i.insight_type == insight_type]
        return [i.to_dict() for i in insights[-limit:]]

    def get_strategy_library(self,
                             strategy_type: Optional[StrategyType] = None) -> List[Dict[str, Any]]:
        """Get available improvement strategies."""
        strategies = self._strategy_library.values()
        if strategy_type:
            strategies = [s for s in strategies if s.strategy_type == strategy_type]
        return [s.to_dict() for s in strategies]

    def list_sessions(self) -> List[Dict[str, Any]]:
        """List all active and historical reflection sessions."""
        sessions = list(self._sessions.values()) + self._session_history
        return [s.to_dict() for s in sessions]

    def get_session_history(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Get recent session history."""
        return [s.to_dict() for s in self._session_history[-limit:]]


# ── Module Accessor ──

def get_self_reflection() -> SelfReflectionEngine:
    """Get the singleton self-reflection engine instance."""
    return SelfReflectionEngine.get_instance()