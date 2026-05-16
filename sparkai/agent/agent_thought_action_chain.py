"""
SparkLabs Agent - Thought Action Chain

Structured Think-Act-Observe-Decide reasoning loop for the SparkLabs
AI-native game engine agent. Implements a full cyclical reasoning pipeline
where the agent generates reasoning content, executes tool-based actions,
processes observations from those actions, and decides on the next course
of action. Includes a reflect phase for post-hoc chain analysis and
full trace recording for observability and debugging.

Architecture:
  ThoughtActionChain
    |-- ThinkStep (single reasoning unit with confidence scoring)
    |-- ActionStep (tool invocation with parameter schema)
    |-- ObservationResult (processed output from an action)
    |-- ChainTrace (complete session trace with timeline)
    |-- ChainPhase (THINK -> ACT -> OBSERVE -> DECIDE -> REFLECT)
    |-- DecisionOutcome (branching logic after observation)
"""

from __future__ import annotations

import json
import threading
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class ChainPhase(Enum):
    THINK = "think"
    ACT = "act"
    OBSERVE = "observe"
    DECIDE = "decide"
    REFLECT = "reflect"


class ActionType(Enum):
    TOOL_CALL = "tool_call"
    LLM_QUERY = "llm_query"
    CODE_EXECUTE = "code_execute"
    ASSET_GENERATE = "asset_generate"
    WAIT = "wait"
    DELEGATE = "delegate"
    TERMINATE = "terminate"


class ObservationType(Enum):
    TOOL_RESULT = "tool_result"
    ERROR = "error"
    TIMEOUT = "timeout"
    USER_FEEDBACK = "user_feedback"
    STATE_CHANGE = "state_change"


class DecisionOutcome(Enum):
    PROCEED = "proceed"
    RETRY = "retry"
    ALTERNATIVE_PATH = "alternative_path"
    ESCALATE = "escalate"
    COMPLETE = "complete"


@dataclass
class ThinkStep:
    step_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    phase: ChainPhase = ChainPhase.THINK
    reasoning_content: str = ""
    confidence: float = 0.5
    duration_ms: float = 0.0

    def to_dict(self) -> dict:
        return {
            "step_id": self.step_id,
            "phase": self.phase.value,
            "reasoning_content": self.reasoning_content[:1000],
            "confidence": self.confidence,
            "duration_ms": self.duration_ms,
        }


@dataclass
class ActionStep:
    action_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    tool_name: str = ""
    action_type: ActionType = ActionType.TOOL_CALL
    parameters: Dict[str, Any] = field(default_factory=dict)
    expected_output_schema: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> dict:
        return {
            "action_id": self.action_id,
            "tool_name": self.tool_name,
            "action_type": self.action_type.value,
            "parameters": self.parameters,
            "expected_output_schema": self.expected_output_schema,
        }


@dataclass
class ObservationResult:
    observation_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    observation_type: ObservationType = ObservationType.TOOL_RESULT
    success: bool = True
    data: Dict[str, Any] = field(default_factory=dict)
    error_message: str = ""
    latency_ms: float = 0.0
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> dict:
        return {
            "observation_id": self.observation_id,
            "observation_type": self.observation_type.value,
            "success": self.success,
            "data": self.data,
            "error_message": self.error_message[:500],
            "latency_ms": self.latency_ms,
        }


@dataclass
class ChainTrace:
    session_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    goal_description: str = ""
    steps_list: List[Dict[str, Any]] = field(default_factory=list)
    final_outcome: DecisionOutcome = DecisionOutcome.COMPLETE
    total_duration: float = 0.0
    token_usage: int = 0
    started_at: float = field(default_factory=time.time)
    ended_at: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def add_step(self, step_data: Dict[str, Any]) -> None:
        self.steps_list.append(step_data)

    def finalize(self, outcome: DecisionOutcome, tokens: int = 0) -> None:
        self.final_outcome = outcome
        self.token_usage = tokens
        self.ended_at = time.time()
        self.total_duration = self.ended_at - self.started_at

    def to_dict(self) -> dict:
        return {
            "session_id": self.session_id,
            "goal_description": self.goal_description,
            "steps_count": len(self.steps_list),
            "steps_list": self.steps_list,
            "final_outcome": self.final_outcome.value,
            "total_duration": round(self.total_duration, 3),
            "token_usage": self.token_usage,
            "started_at": self.started_at,
            "ended_at": self.ended_at,
            "metadata": self.metadata,
        }


class ThoughtActionChain:
    """Think-Act-Observe-Decide reasoning loop with full trace recording.

    Manages the full lifecycle of an agent reasoning session including
    thought generation, action execution, observation processing, decision
    routing, and post-hoc reflection. Maintains session-level state and
    produces structured chain traces for observability.

    Singleton access via get_instance() or module-level get_thought_action_chain().
    """

    _instance: Optional["ThoughtActionChain"] = None
    _lock = threading.Lock()

    MAX_TRACES = 200
    MAX_STEPS_PER_TRACE = 500
    SIMULATED_TOKEN_COST_THINK = 150
    SIMULATED_TOKEN_COST_DECIDE = 80
    SIMULATED_TOKEN_COST_REFLECT = 200

    def __init__(self):
        self._traces: Dict[str, ChainTrace] = {}
        self._active_sessions: Dict[str, ChainTrace] = {}
        self._step_counters: Dict[str, int] = {}
        self._total_sessions: int = 0
        self._total_steps: int = 0

    @classmethod
    def get_instance(cls) -> "ThoughtActionChain":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def start_chain(self, goal_description: str) -> str:
        """Initialize a new reasoning chain session for the given goal.

        Args:
            goal_description: Human-readable description of the goal to achieve.

        Returns:
            The session_id string for the newly created chain session.
        """
        trace = ChainTrace(goal_description=goal_description)
        session_id = trace.session_id
        self._active_sessions[session_id] = trace
        self._step_counters[session_id] = 0
        self._total_sessions += 1
        return session_id

    def think(self, context: str, session_id: Optional[str] = None) -> ThinkStep:
        """Generate reasoning for the next step based on the current context.

        Simulates an LLM reasoning pass that produces structured thought content
        with a confidence score. Records the think step in the active session trace.

        Args:
            context: The current situational context to reason about.
            session_id: Optional session identifier. Uses the most recent active
                session if not provided.

        Returns:
            A ThinkStep containing the generated reasoning content and metadata.
        """
        sid = self._resolve_session(session_id)
        start = time.time()

        confidence = self._simulate_confidence(context)
        reasoning = self._generate_reasoning(context)

        end = time.time()
        step = ThinkStep(
            phase=ChainPhase.THINK,
            reasoning_content=reasoning,
            confidence=confidence,
            duration_ms=(end - start) * 1000.0,
        )
        self._record_step(sid, "think", step)
        return step

    def act(
        self,
        tool_name: str,
        parameters: Optional[Dict[str, Any]] = None,
        action_type: ActionType = ActionType.TOOL_CALL,
        expected_output_schema: Optional[Dict[str, Any]] = None,
        session_id: Optional[str] = None,
    ) -> ActionStep:
        """Record and prepare a tool/action for execution.

        Creates an ActionStep representing the intended action invocation.
        Does not actually execute the tool — that is done externally and
        the result is fed back via observe().

        Args:
            tool_name: Name identifier of the tool or action to invoke.
            parameters: Key-value parameters passed to the action.
            action_type: Category of the action being performed.
            expected_output_schema: Optional schema describing the expected
                shape of the action's output.
            session_id: Optional session identifier.

        Returns:
            An ActionStep capturing the action details.
        """
        sid = self._resolve_session(session_id)
        step = ActionStep(
            tool_name=tool_name,
            action_type=action_type,
            parameters=parameters or {},
            expected_output_schema=expected_output_schema or {},
        )
        self._record_step(sid, "act", step)
        return step

    def observe(
        self,
        result: Dict[str, Any],
        observation_type: ObservationType = ObservationType.TOOL_RESULT,
        success: bool = True,
        error_message: str = "",
        latency_ms: float = 0.0,
        session_id: Optional[str] = None,
    ) -> ObservationResult:
        """Process an observation returned from a previously executed action.

        Creates an ObservationResult that captures the outcome, latency,
        and any error information from the action execution.

        Args:
            result: The raw result data from the action execution.
            observation_type: Category of the observation.
            success: Whether the action completed successfully.
            error_message: Error description if the action failed.
            latency_ms: Measured latency of the action execution.
            session_id: Optional session identifier.

        Returns:
            An ObservationResult with structured observation data.
        """
        sid = self._resolve_session(session_id)
        obs = ObservationResult(
            observation_type=observation_type,
            success=success,
            data=result,
            error_message=error_message,
            latency_ms=latency_ms,
        )
        self._record_step(sid, "observe", obs)
        return obs

    def decide(
        self,
        options: Optional[List[Dict[str, Any]]] = None,
        session_id: Optional[str] = None,
    ) -> DecisionOutcome:
        """Determine the next course of action based on the chain's state.

        Evaluates available options and the session history to decide whether
        to proceed, retry, take an alternative path, escalate, or mark the
        chain as complete. Simulates a lightweight decision engine.

        Args:
            options: List of option dictionaries, each with 'name', 'viability',
                and 'risk' keys.
            session_id: Optional session identifier.

        Returns:
            The DecisionOutcome indicating the next action for the chain.
        """
        sid = self._resolve_session(session_id)
        trace = self._active_sessions.get(sid)
        if trace is None:
            return DecisionOutcome.ESCALATE

        if self._step_counters.get(sid, 0) >= self.MAX_STEPS_PER_TRACE:
            return DecisionOutcome.ESCALATE

        if options is None or len(options) == 0:
            if self._step_counters.get(sid, 0) > 0:
                return DecisionOutcome.PROCEED
            return DecisionOutcome.COMPLETE

        decision = self._evaluate_options(options, trace)
        step_data = {
            "phase": ChainPhase.DECIDE.value,
            "options_considered": len(options),
            "outcome": decision.value,
        }
        self._record_step(sid, "decide", step_data)
        return decision

    def reflect(self, session_id: Optional[str] = None) -> Dict[str, Any]:
        """Perform post-hoc analysis of the entire reasoning chain.

        Reviews the complete session trace and produces a reflection summary
        including effectiveness scoring, bottleneck identification, and
        improvement suggestions.

        Args:
            session_id: Optional session identifier.

        Returns:
            A dictionary with reflection analysis results.
        """
        sid = self._resolve_session(session_id)
        trace = self._active_sessions.get(sid)
        if trace is None:
            return {"error": "session not found", "session_id": sid}

        think_steps = sum(
            1 for s in trace.steps_list if s.get("phase") == ChainPhase.THINK.value
        )
        act_steps = sum(
            1 for s in trace.steps_list if s.get("phase") == ChainPhase.ACT.value
        )
        observe_steps = sum(
            1 for s in trace.steps_list if s.get("phase") == ChainPhase.OBSERVE.value
        )
        decide_steps = sum(
            1 for s in trace.steps_list if s.get("phase") == ChainPhase.DECIDE.value
        )

        successes = sum(
            1 for s in trace.steps_list
            if isinstance(s.get("data"), dict) and s.get("data", {}).get("success", True)
            or s.get("phase") not in (ChainPhase.OBSERVE.value,)
        )
        success_rate = successes / max(len(trace.steps_list), 1)

        bottlenecks = self._identify_bottlenecks(trace)
        suggestions = self._generate_suggestions(trace, success_rate)

        reflection = {
            "session_id": sid,
            "goal": trace.goal_description,
            "total_steps": len(trace.steps_list),
            "phase_breakdown": {
                "think": think_steps,
                "act": act_steps,
                "observe": observe_steps,
                "decide": decide_steps,
            },
            "success_rate": round(success_rate, 3),
            "bottlenecks": bottlenecks,
            "suggestions": suggestions,
            "effectiveness_score": self._compute_effectiveness(trace, success_rate),
        }
        step_data = {
            "phase": ChainPhase.REFLECT.value,
            "reflection": reflection,
        }
        self._record_step(sid, "reflect", step_data)
        return reflection

    def get_trace(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Return the full chain trace for the given session.

        Args:
            session_id: The session identifier to retrieve.

        Returns:
            A dictionary representation of the ChainTrace, or None if not found.
        """
        trace = self._traces.get(session_id) or self._active_sessions.get(session_id)
        if trace is None:
            return None
        return trace.to_dict()

    def get_stats(self) -> Dict[str, Any]:
        """Return aggregate statistics across all recorded sessions.

        Returns:
            A dictionary with global chain statistics.
        """
        total_traces = len(self._traces) + len(self._active_sessions)
        total_steps = sum(
            len(t.steps_list)
            for t in list(self._traces.values()) + list(self._active_sessions.values())
        )
        completed = sum(
            1 for t in self._traces.values()
            if t.final_outcome == DecisionOutcome.COMPLETE
        )
        avg_duration = 0.0
        durations = [
            t.total_duration
            for t in list(self._traces.values()) + list(self._active_sessions.values())
            if t.total_duration > 0
        ]
        if durations:
            avg_duration = sum(durations) / len(durations)

        outcome_counts: Dict[str, int] = {}
        for t in list(self._traces.values()) + list(self._active_sessions.values()):
            key = t.final_outcome.value
            outcome_counts[key] = outcome_counts.get(key, 0) + 1

        return {
            "total_sessions_created": self._total_sessions,
            "active_sessions": len(self._active_sessions),
            "archived_traces": len(self._traces),
            "total_steps": total_steps,
            "completed_sessions": completed,
            "average_duration_sec": round(avg_duration, 3),
            "outcome_distribution": outcome_counts,
        }

    def _resolve_session(self, session_id: Optional[str]) -> str:
        if session_id and session_id in self._active_sessions:
            return session_id
        if self._active_sessions:
            return list(self._active_sessions.keys())[-1]
        return self.start_chain("default")

    def _record_step(
        self, session_id: str, phase_name: str, step_or_data: Any
    ) -> None:
        trace = self._active_sessions.get(session_id)
        if trace is None:
            return
        if hasattr(step_or_data, "to_dict"):
            step_data = step_or_data.to_dict()
        elif isinstance(step_or_data, dict):
            step_data = step_or_data
        else:
            step_data = {"phase": phase_name, "value": str(step_or_data)}
        trace.add_step(step_data)
        self._step_counters[session_id] = self._step_counters.get(session_id, 0) + 1
        self._total_steps += 1

    def _simulate_confidence(self, context: str) -> float:
        context_len = len(context)
        if context_len < 20:
            return 0.2
        if context_len < 100:
            return 0.5
        return round(min(0.95, 0.5 + (context_len - 100) * 0.002), 3)

    def _generate_reasoning(self, context: str) -> str:
        if not context.strip():
            return "No context provided. Awaiting further input to begin reasoning."
        segments = context.split(".")
        primary = segments[0].strip() if segments else context.strip()
        return (
            f"Analyzing: '{primary}'. "
            f"Decomposing into sub-tasks, evaluating prerequisites, "
            f"and preparing action plan for execution."
        )

    def _evaluate_options(
        self, options: List[Dict[str, Any]], trace: ChainTrace
    ) -> DecisionOutcome:
        viable = [
            o for o in options
            if o.get("viability", 0.5) > 0.3 and o.get("risk", 0.5) < 0.8
        ]
        if not viable:
            return DecisionOutcome.ESCALATE

        best = max(viable, key=lambda o: o.get("viability", 0.5))
        if best.get("viability", 0.5) > 0.8:
            return DecisionOutcome.PROCEED

        failed_steps = sum(
            1 for s in trace.steps_list
            if isinstance(s, dict) and not s.get("success", True)
        )
        if failed_steps > 0:
            return DecisionOutcome.RETRY

        return DecisionOutcome.ALTERNATIVE_PATH

    def _identify_bottlenecks(self, trace: ChainTrace) -> List[str]:
        bottlenecks: List[str] = []
        observe_steps = [
            s for s in trace.steps_list
            if isinstance(s, dict) and s.get("phase") == ChainPhase.OBSERVE.value
        ]
        high_latency = [
            s for s in observe_steps
            if isinstance(s, dict) and s.get("latency_ms", 0) > 5000
        ]
        if high_latency:
            bottlenecks.append(
                f"{len(high_latency)} observation(s) exceeded 5s latency threshold"
            )

        errors = [
            s for s in trace.steps_list
            if isinstance(s, dict) and not s.get("success", True)
        ]
        if errors:
            bottlenecks.append(
                f"{len(errors)} error(s) encountered during chain execution"
            )
        return bottlenecks

    def _generate_suggestions(
        self, trace: ChainTrace, success_rate: float
    ) -> List[str]:
        suggestions: List[str] = []
        if success_rate < 0.7:
            suggestions.append(
                "Consider breaking the goal into smaller sub-goals to improve "
                "step-level success rate."
            )
        act_steps = sum(
            1 for s in trace.steps_list
            if isinstance(s, dict) and s.get("phase") == ChainPhase.ACT.value
        )
        think_steps = sum(
            1 for s in trace.steps_list
            if isinstance(s, dict) and s.get("phase") == ChainPhase.THINK.value
        )
        if act_steps > think_steps * 2:
            suggestions.append(
                "Action-heavy chain detected. Increase thinking depth before "
                "executing to reduce unnecessary actions."
            )
        if len(trace.steps_list) > 50:
            suggestions.append(
                "Long chain detected. Review for potential infinite loops or "
                "redundant step sequences."
            )
        return suggestions

    def _compute_effectiveness(
        self, trace: ChainTrace, success_rate: float
    ) -> float:
        if len(trace.steps_list) == 0:
            return 0.0
        diversity = min(1.0, len({
            s.get("phase", "") for s in trace.steps_list if isinstance(s, dict)
        }) / 4.0)
        return round((success_rate * 0.6 + diversity * 0.4), 3)


def get_thought_action_chain() -> ThoughtActionChain:
    return ThoughtActionChain.get_instance()