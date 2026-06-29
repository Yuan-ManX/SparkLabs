"""
SparkLabs Cognitive Kernel

A unified cognitive architecture that coordinates perception, attention,
memory, reasoning, and decision-making for AI agents. The kernel runs a
continuous cognitive cycle: perceive -> attend -> reason -> decide -> act ->
reflect, enabling autonomous agents to maintain coherent thought processes
across long game sessions.

The kernel provides:
- Cognitive process orchestration with priority scheduling
- Self-awareness through metacognitive monitoring
- Attention allocation with configurable focus strategies
- Cognitive load management to prevent overload
- Introspective state inspection for debugging and transparency
"""

from __future__ import annotations

import threading
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple


class CognitiveProcess(Enum):
    """Enumeration of cognitive processes managed by the kernel."""
    PERCEPTION = "perception"
    ATTENTION = "attention"
    MEMORY = "memory"
    REASONING = "reasoning"
    DECISION = "decision"
    ACTION = "action"
    REFLECTION = "reflection"
    LEARNING = "learning"


class CognitiveState(Enum):
    """Current operational state of the cognitive kernel."""
    DORMANT = "dormant"
    PERCEIVING = "perceiving"
    ATTENDING = "attending"
    REASONING = "reasoning"
    DECIDING = "deciding"
    ACTING = "acting"
    REFLECTING = "reflecting"
    IDLE = "idle"


class AttentionStrategy(Enum):
    """Strategies for allocating attention across competing stimuli."""
    FOCUSED = "focused"
    DIVIDED = "divided"
    SELECTIVE = "selective"
    ALTERNATING = "alternating"
    THREAT_PRIORITY = "threat_priority"
    GOAL_DIRECTED = "goal_directed"


class ReflectionMode(Enum):
    """Modes of self-reflection the kernel can engage in."""
    NONE = "none"
    BRIEF = "brief"
    DEEP = "deep"
    CRITICAL = "critical"
    POST_MORTEM = "post_mortem"


@dataclass
class CognitiveCycle:
    """A single iteration of the cognitive cycle."""
    cycle_id: str = field(default_factory=lambda: f"cycle_{uuid.uuid4().hex[:10]}")
    timestamp: float = field(default_factory=time.time)
    state: CognitiveState = CognitiveState.DORMANT
    perception_data: Dict[str, Any] = field(default_factory=dict)
    attention_focus: List[str] = field(default_factory=list)
    reasoning_trace: List[Dict[str, Any]] = field(default_factory=list)
    decision: Optional[Dict[str, Any]] = None
    action_taken: Optional[str] = None
    reflection_notes: str = ""
    cognitive_load: float = 0.0
    duration_ms: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "cycle_id": self.cycle_id,
            "timestamp": self.timestamp,
            "state": self.state.value,
            "perception_data": dict(self.perception_data),
            "attention_focus": list(self.attention_focus),
            "reasoning_trace": list(self.reasoning_trace),
            "decision": self.decision,
            "action_taken": self.action_taken,
            "reflection_notes": self.reflection_notes,
            "cognitive_load": self.cognitive_load,
            "duration_ms": self.duration_ms,
        }


@dataclass
class AttentionTarget:
    """A target of attention with priority and salience."""
    target_id: str
    target_type: str
    priority: float = 0.5
    salience: float = 0.5
    novelty: float = 0.0
    relevance: float = 0.0
    urgency: float = 0.0
    data: Dict[str, Any] = field(default_factory=dict)

    @property
    def attention_weight(self) -> float:
        """Composite attention weight from all factors."""
        return (
            self.priority * 0.30
            + self.salience * 0.25
            + self.novelty * 0.15
            + self.relevance * 0.20
            + self.urgency * 0.10
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "target_id": self.target_id,
            "target_type": self.target_type,
            "priority": self.priority,
            "salience": self.salience,
            "novelty": self.novelty,
            "relevance": self.relevance,
            "urgency": self.urgency,
            "attention_weight": self.attention_weight,
            "data": dict(self.data),
        }


@dataclass
class MetacognitiveReport:
    """Self-assessment of cognitive state and performance."""
    confidence: float = 0.5
    uncertainty: float = 0.5
    cognitive_load: float = 0.0
    focus_quality: float = 0.5
    reasoning_depth: int = 0
    biases_detected: List[str] = field(default_factory=list)
    self_corrections: List[str] = field(default_factory=list)
    improvement_suggestions: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "confidence": self.confidence,
            "uncertainty": self.uncertainty,
            "cognitive_load": self.cognitive_load,
            "focus_quality": self.focus_quality,
            "reasoning_depth": self.reasoning_depth,
            "biases_detected": list(self.biases_detected),
            "self_corrections": list(self.self_corrections),
            "improvement_suggestions": list(self.improvement_suggestions),
        }


@dataclass
class CognitiveSnapshot:
    """Complete snapshot of the cognitive kernel state."""
    kernel_id: str
    state: CognitiveState
    current_cycle: Optional[CognitiveCycle]
    attention_targets: List[AttentionTarget]
    metacognition: MetacognitiveReport
    cycles_completed: int
    uptime_seconds: float
    avg_cycle_duration_ms: float
    last_reflection: Optional[Dict[str, Any]]
    active_goals: List[str]
    focus_strategy: AttentionStrategy
    reflection_mode: ReflectionMode
    max_cognitive_load: float
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "kernel_id": self.kernel_id,
            "state": self.state.value,
            "current_cycle": self.current_cycle.to_dict() if self.current_cycle else None,
            "attention_targets": [t.to_dict() for t in self.attention_targets],
            "metacognition": self.metacognition.to_dict(),
            "cycles_completed": self.cycles_completed,
            "uptime_seconds": self.uptime_seconds,
            "avg_cycle_duration_ms": self.avg_cycle_duration_ms,
            "last_reflection": self.last_reflection,
            "active_goals": list(self.active_goals),
            "focus_strategy": self.focus_strategy.value,
            "reflection_mode": self.reflection_mode.value,
            "max_cognitive_load": self.max_cognitive_load,
            "timestamp": self.timestamp,
        }


class CognitiveKernel:
    """
    Singleton cognitive kernel that orchestrates all cognitive processes
    for an AI agent. Manages the perceive-attend-reason-decide-act-reflect
    cycle, attention allocation, metacognitive monitoring, and cognitive
    load management.
    """

    _instance: Optional["CognitiveKernel"] = None
    _lock = threading.RLock()

    def __init__(self) -> None:
        self._kernel_id: str = f"kernel_{uuid.uuid4().hex[:12]}"
        self._state: CognitiveState = CognitiveState.DORMANT
        self._initialized: bool = True
        self._is_running: bool = False
        self._instance_lock = threading.RLock()

        self._focus_strategy: AttentionStrategy = AttentionStrategy.GOAL_DIRECTED
        self._reflection_mode: ReflectionMode = ReflectionMode.BRIEF
        self._max_cognitive_load: float = 1.0

        self._current_cycle: Optional[CognitiveCycle] = None
        self._attention_targets: List[AttentionTarget] = []
        self._metacognition: MetacognitiveReport = MetacognitiveReport()
        self._active_goals: List[str] = []
        self._last_reflection: Optional[Dict[str, Any]] = None

        self._cycles_completed: int = 0
        self._cycle_durations: List[float] = []
        self._start_time: float = time.time()

        self._perception_handlers: List[Callable] = []
        self._reasoning_handlers: List[Callable] = []
        self._decision_handlers: List[Callable] = []
        self._reflection_handlers: List[Callable] = []

        self._cognitive_history: List[Dict[str, Any]] = []
        self._max_history: int = 200

    @classmethod
    def get_instance(cls) -> "CognitiveKernel":
        with cls._lock:
            if cls._instance is None:
                cls._instance = cls()
            return cls._instance

    def initialize(
        self,
        focus_strategy: AttentionStrategy = AttentionStrategy.GOAL_DIRECTED,
        reflection_mode: ReflectionMode = ReflectionMode.BRIEF,
        max_cognitive_load: float = 1.0,
    ) -> None:
        with self._instance_lock:
            self._focus_strategy = focus_strategy
            self._reflection_mode = reflection_mode
            self._max_cognitive_load = max_cognitive_load
            self._is_running = True
            self._state = CognitiveState.IDLE

    def register_perception_handler(self, handler: Callable) -> None:
        with self._instance_lock:
            self._perception_handlers.append(handler)

    def register_reasoning_handler(self, handler: Callable) -> None:
        with self._instance_lock:
            self._reasoning_handlers.append(handler)

    def register_decision_handler(self, handler: Callable) -> None:
        with self._instance_lock:
            self._decision_handlers.append(handler)

    def register_reflection_handler(self, handler: Callable) -> None:
        with self._instance_lock:
            self._reflection_handlers.append(handler)

    def add_attention_target(self, target: AttentionTarget) -> None:
        with self._instance_lock:
            existing = next(
                (t for t in self._attention_targets if t.target_id == target.target_id),
                None,
            )
            if existing is not None:
                existing.priority = target.priority
                existing.salience = target.salience
                existing.novelty = target.novelty
                existing.relevance = target.relevance
                existing.urgency = target.urgency
                existing.data = target.data
            else:
                self._attention_targets.append(target)

    def remove_attention_target(self, target_id: str) -> bool:
        with self._instance_lock:
            before = len(self._attention_targets)
            self._attention_targets = [
                t for t in self._attention_targets if t.target_id != target_id
            ]
            return len(self._attention_targets) < before

    def get_attention_focus(self, max_targets: int = 5) -> List[AttentionTarget]:
        with self._instance_lock:
            sorted_targets = sorted(
                self._attention_targets,
                key=lambda t: t.attention_weight,
                reverse=True,
            )
            return sorted_targets[:max_targets]

    def add_goal(self, goal_id: str) -> None:
        with self._instance_lock:
            if goal_id not in self._active_goals:
                self._active_goals.append(goal_id)

    def remove_goal(self, goal_id: str) -> bool:
        with self._instance_lock:
            if goal_id in self._active_goals:
                self._active_goals.remove(goal_id)
                return True
            return False

    def run_cycle(
        self,
        perception_input: Optional[Dict[str, Any]] = None,
    ) -> CognitiveCycle:
        """Run one complete cognitive cycle."""
        with self._instance_lock:
            cycle_start = time.time()
            cycle = CognitiveCycle(
                state=CognitiveState.PERCEIVING,
                perception_data=perception_input or {},
            )

            # Phase 1: Perception
            self._state = CognitiveState.PERCEIVING
            perception_result = self._run_perception(perception_input)
            cycle.perception_data = perception_result

            # Phase 2: Attention
            self._state = CognitiveState.ATTENDING
            focus = self.get_attention_focus()
            cycle.attention_focus = [t.target_id for t in focus]

            # Phase 3: Reasoning
            self._state = CognitiveState.REASONING
            reasoning = self._run_reasoning(perception_result, focus)
            cycle.reasoning_trace = reasoning

            # Phase 4: Decision
            self._state = CognitiveState.DECIDING
            decision = self._run_decision(reasoning)
            cycle.decision = decision

            # Phase 5: Action
            self._state = CognitiveState.ACTING
            cycle.action_taken = decision.get("action") if decision else None

            # Phase 6: Reflection
            self._state = CognitiveState.REFLECTING
            reflection = self._run_reflection(cycle)
            cycle.reflection_notes = reflection

            # Finalize
            cycle.duration_ms = (time.time() - cycle_start) * 1000.0
            cycle.cognitive_load = self._compute_cognitive_load()
            cycle.state = CognitiveState.IDLE

            self._cycles_completed += 1
            self._cycle_durations.append(cycle.duration_ms)
            if len(self._cycle_durations) > 100:
                self._cycle_durations = self._cycle_durations[-100:]

            self._current_cycle = cycle
            self._state = CognitiveState.IDLE

            self._cognitive_history.append(cycle.to_dict())
            if len(self._cognitive_history) > self._max_history:
                self._cognitive_history = self._cognitive_history[-self._max_history:]

            return cycle

    def _run_perception(self, input_data: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        result: Dict[str, Any] = dict(input_data or {})
        for handler in self._perception_handlers:
            try:
                handler_result = handler(input_data)
                if isinstance(handler_result, dict):
                    result.update(handler_result)
            except Exception:
                pass
        result["_timestamp"] = time.time()
        return result

    def _run_reasoning(
        self,
        perception: Dict[str, Any],
        focus: List[AttentionTarget],
    ) -> List[Dict[str, Any]]:
        traces: List[Dict[str, Any]] = []
        for handler in self._reasoning_handlers:
            try:
                handler_result = handler(perception, focus)
                if isinstance(handler_result, dict):
                    traces.append(handler_result)
                elif isinstance(handler_result, list):
                    traces.extend(handler_result)
            except Exception:
                pass
        if not traces:
            traces.append({
                "step": "default",
                "input": perception,
                "focus": [t.target_id for t in focus],
                "output": "no_reasoning_handlers",
            })
        return traces

    def _run_decision(self, reasoning: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        for handler in self._decision_handlers:
            try:
                result = handler(reasoning)
                if result is not None:
                    return result if isinstance(result, dict) else {"action": str(result)}
            except Exception:
                pass
        if reasoning:
            last = reasoning[-1]
            return {"action": last.get("output", "none"), "confidence": 0.3}
        return None

    def _run_reflection(self, cycle: CognitiveCycle) -> str:
        notes_parts: List[str] = []
        for handler in self._reflection_handlers:
            try:
                result = handler(cycle)
                if isinstance(result, str):
                    notes_parts.append(result)
            except Exception:
                pass

        if self._reflection_mode == ReflectionMode.NONE:
            return ""
        if self._reflection_mode == ReflectionMode.BRIEF:
            return f"Cycle {cycle.cycle_id} completed in {cycle.duration_ms:.1f}ms"
        if self._reflection_mode == ReflectionMode.DEEP:
            return (
                f"Cycle {cycle.cycle_id} | Load: {cycle.cognitive_load:.2f} | "
                f"Focus: {len(cycle.attention_focus)} | "
                f"Reasoning steps: {len(cycle.reasoning_trace)} | "
                f"Decision: {cycle.decision.get('action', 'none') if cycle.decision else 'none'}"
            )
        if self._reflection_mode == ReflectionMode.CRITICAL:
            self._metacognition.self_corrections.append(
                f"cycle_{self._cycles_completed}"
            )
            return f"Critical reflection on cycle {cycle.cycle_id}"
        return "; ".join(notes_parts) if notes_parts else "reflected"

    def _compute_cognitive_load(self) -> float:
        target_load = len(self._attention_targets) / max(1, 10)
        cycle_load = len(self._current_cycle.reasoning_trace) / max(1, 5) if self._current_cycle else 0.0
        goal_load = len(self._active_goals) / max(1, 5)
        return min(self._max_cognitive_load, target_load * 0.4 + cycle_load * 0.4 + goal_load * 0.2)

    def run_metacognition(self) -> MetacognitiveReport:
        """Perform a metacognitive self-assessment."""
        with self._instance_lock:
            self._metacognition.cognitive_load = self._compute_cognitive_load()
            self._metacognition.reasoning_depth = (
                len(self._current_cycle.reasoning_trace) if self._current_cycle else 0
            )
            if self._cycle_durations:
                avg = sum(self._cycle_durations) / len(self._cycle_durations)
                self._metacognition.focus_quality = max(0.0, 1.0 - (avg / 1000.0))
            if self._metacognition.cognitive_load > 0.8:
                self._metacognition.improvement_suggestions.append(
                    "reduce_attention_targets"
                )
            if self._metacognition.confidence < 0.3:
                self._metacognition.improvement_suggestions.append(
                    "gather_more_information"
                )
            self._last_reflection = self._metacognition.to_dict()
            return self._metacognition

    def get_status(self) -> Dict[str, Any]:
        with self._instance_lock:
            avg_duration = (
                sum(self._cycle_durations) / len(self._cycle_durations)
                if self._cycle_durations
                else 0.0
            )
            return {
                "kernel_id": self._kernel_id,
                "state": self._state.value,
                "is_running": self._is_running,
                "cycles_completed": self._cycles_completed,
                "uptime_seconds": time.time() - self._start_time,
                "avg_cycle_duration_ms": avg_duration,
                "attention_targets": len(self._attention_targets),
                "active_goals": list(self._active_goals),
                "focus_strategy": self._focus_strategy.value,
                "reflection_mode": self._reflection_mode.value,
                "cognitive_load": self._compute_cognitive_load(),
                "max_cognitive_load": self._max_cognitive_load,
            }

    def get_snapshot(self) -> CognitiveSnapshot:
        with self._instance_lock:
            avg_duration = (
                sum(self._cycle_durations) / len(self._cycle_durations)
                if self._cycle_durations
                else 0.0
            )
            return CognitiveSnapshot(
                kernel_id=self._kernel_id,
                state=self._state,
                current_cycle=self._current_cycle,
                attention_targets=list(self._attention_targets),
                metacognition=self._metacognition,
                cycles_completed=self._cycles_completed,
                uptime_seconds=time.time() - self._start_time,
                avg_cycle_duration_ms=avg_duration,
                last_reflection=self._last_reflection,
                active_goals=list(self._active_goals),
                focus_strategy=self._focus_strategy,
                reflection_mode=self._reflection_mode,
                max_cognitive_load=self._max_cognitive_load,
            )

    def get_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        with self._instance_lock:
            return list(self._cognitive_history[-limit:])

    def reset(self) -> None:
        with self._instance_lock:
            self._state = CognitiveState.DORMANT
            self._is_running = False
            self._current_cycle = None
            self._attention_targets.clear()
            self._active_goals.clear()
            self._metacognition = MetacognitiveReport()
            self._last_reflection = None
            self._cycles_completed = 0
            self._cycle_durations.clear()
            self._cognitive_history.clear()
            self._start_time = time.time()


def get_cognitive_kernel() -> CognitiveKernel:
    """Module-level factory for the CognitiveKernel singleton."""
    return CognitiveKernel.get_instance()
