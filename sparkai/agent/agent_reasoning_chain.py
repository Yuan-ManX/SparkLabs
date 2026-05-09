"""
SparkLabs Agent - Reasoning Chain

Structured reasoning chain for the SparkLabs AI-native game engine agent.
Implements a think-act-observe loop with explicit reasoning trace recording,
chain-of-thought decomposition for complex game development tasks, and
decision provenance tracking. Enables the AI agent to break down game
design requests into structured reasoning steps before acting, providing
full transparency into the agent's decision process.

Architecture:
  ReasoningChain
    |-- ReasoningStep (single think/act/observe unit)
    |-- DecompositionNode (hierarchical task breakdown tree)
    |-- ReasoningTrace (full reasoning session with timeline)
    |-- DecisionRecord (what was decided, why, and alternatives)
    |-- ChainConfig (max depth, branching factor, timeout)
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional


class ReasoningPhase(Enum):
    ANALYZE = "analyze"
    DECOMPOSE = "decompose"
    RESEARCH = "research"
    PLAN = "plan"
    DECIDE = "decide"
    ACT = "act"
    VERIFY = "verify"
    REVISE = "revise"


class DecisionConfidence(Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    UNCERTAIN = "uncertain"


@dataclass
class ReasoningStep:
    step_id: int = 0
    phase: ReasoningPhase = ReasoningPhase.ANALYZE
    thought: str = ""
    action: str = ""
    observation: str = ""
    timestamp: float = field(default_factory=time.time)
    duration_ms: float = 0.0
    token_count: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "step_id": self.step_id,
            "phase": self.phase.value,
            "thought": self.thought[:500],
            "action": self.action[:200],
            "observation": self.observation[:300],
            "duration_ms": self.duration_ms,
            "tokens": self.token_count,
        }


@dataclass
class DecompositionNode:
    node_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    task: str = ""
    description: str = ""
    parent_id: Optional[str] = None
    children: List["DecompositionNode"] = field(default_factory=list)
    estimated_complexity: str = "medium"
    order_index: int = 0
    completed: bool = False
    output_summary: str = ""

    def add_child(self, task: str, description: str = "", complexity: str = "medium") -> "DecompositionNode":
        child = DecompositionNode(
            task=task,
            description=description,
            parent_id=self.node_id,
            estimated_complexity=complexity,
            order_index=len(self.children),
        )
        self.children.append(child)
        return child

    def to_dict(self) -> dict:
        return {
            "node_id": self.node_id,
            "task": self.task,
            "description": self.description,
            "complexity": self.estimated_complexity,
            "completed": self.completed,
            "children": [c.to_dict() for c in self.children],
        }

    def flatten(self) -> List["DecompositionNode"]:
        result = [self]
        for child in self.children:
            result.extend(child.flatten())
        return result

    def count_nodes(self) -> int:
        return 1 + sum(child.count_nodes() for child in self.children)


@dataclass
class DecisionRecord:
    decision_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    question: str = ""
    chosen_option: str = ""
    alternatives: List[str] = field(default_factory=list)
    rationale: str = ""
    confidence: DecisionConfidence = DecisionConfidence.MEDIUM
    reversible: bool = True
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> dict:
        return {
            "decision_id": self.decision_id,
            "question": self.question,
            "chosen": self.chosen_option,
            "alternatives": self.alternatives,
            "rationale": self.rationale,
            "confidence": self.confidence.value,
        }


@dataclass
class ReasoningTrace:
    trace_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    goal: str = ""
    steps: List[ReasoningStep] = field(default_factory=list)
    root_decomposition: Optional[DecompositionNode] = None
    decisions: List[DecisionRecord] = field(default_factory=list)
    started_at: float = field(default_factory=time.time)
    ended_at: Optional[float] = None
    total_tokens: int = 0
    final_outcome: str = ""
    success: bool = True

    def add_step(self, phase: ReasoningPhase, thought: str = "", action: str = "", observation: str = "", **kwargs) -> ReasoningStep:
        step = ReasoningStep(
            step_id=len(self.steps),
            phase=phase,
            thought=thought,
            action=action,
            observation=observation,
            **kwargs,
        )
        self.steps.append(step)
        self.total_tokens += step.token_count
        return step

    def add_decision(self, question: str, chosen: str, rationale: str, alternatives: Optional[List[str]] = None, **kwargs) -> DecisionRecord:
        decision = DecisionRecord(
            question=question,
            chosen_option=chosen,
            rationale=rationale,
            alternatives=alternatives or [],
            **kwargs,
        )
        self.decisions.append(decision)
        return decision

    def generate_summary(self) -> str:
        lines = [f"Goal: {self.goal}", f"Steps: {len(self.steps)}", f"Decisions: {len(self.decisions)}", ""]
        for step in self.steps:
            marker = "✓" if True else "✗"
            lines.append(f"  [{step.phase.value}] {marker} {step.thought[:80]}")
        lines.append("")
        lines.append("Decisions:")
        for d in self.decisions:
            lines.append(f"  - {d.question}: {d.chosen_option} ({d.confidence.value})")
        return "\n".join(lines)

    def to_dict(self) -> dict:
        return {
            "trace_id": self.trace_id,
            "goal": self.goal,
            "step_count": len(self.steps),
            "decision_count": len(self.decisions),
            "total_tokens": self.total_tokens,
            "success": self.success,
            "decomposition": self.root_decomposition.to_dict() if self.root_decomposition else None,
        }

    def to_full_dict(self) -> dict:
        return {
            **self.to_dict(),
            "steps": [s.to_dict() for s in self.steps],
            "decisions": [d.to_dict() for d in self.decisions],
        }


class ReasoningChain:
    """
    Structured reasoning chain controller for AI game development agents.

    Implements a think-act-observe reasoning loop where each step is
    recorded as a ReasoningStep with full provenance. Supports hierarchical
    task decomposition via DecompositionNode trees, explicit decision
    recording with confidence levels and alternatives, and trace export
    for post-hoc analysis of agent reasoning quality.
    """

    _instance: Optional["ReasoningChain"] = None

    def __init__(self):
        self._active_trace: Optional[ReasoningTrace] = None
        self._trace_history: List[ReasoningTrace] = []
        self._max_history: int = 50
        self._verbose: bool = True
        self._on_step: Optional[Callable[[ReasoningStep], None]] = None

    @classmethod
    def get_instance(cls) -> "ReasoningChain":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def begin(self, goal: str) -> ReasoningTrace:
        self._active_trace = ReasoningTrace(goal=goal)
        return self._active_trace

    @property
    def active(self) -> Optional[ReasoningTrace]:
        return self._active_trace

    def think(self, thought: str, phase: ReasoningPhase = ReasoningPhase.ANALYZE, **kwargs) -> Optional[ReasoningStep]:
        if not self._active_trace:
            return None
        step = self._active_trace.add_step(phase, thought=thought, **kwargs)
        if self._on_step:
            self._on_step(step)
        return step

    def observe(self, observation: str, phase: ReasoningPhase = ReasoningPhase.VERIFY, **kwargs) -> Optional[ReasoningStep]:
        if not self._active_trace:
            return None
        step = self._active_trace.add_step(phase, observation=observation, **kwargs)
        if self._on_step:
            self._on_step(step)
        return step

    def act(self, action: str, thought: str = "", phase: ReasoningPhase = ReasoningPhase.ACT, **kwargs) -> Optional[ReasoningStep]:
        if not self._active_trace:
            return None
        step = self._active_trace.add_step(phase, thought=thought, action=action, **kwargs)
        if self._on_step:
            self._on_step(step)
        return step

    def decide(self, question: str, chosen: str, rationale: str, alternatives: Optional[List[str]] = None, confidence: DecisionConfidence = DecisionConfidence.MEDIUM) -> Optional[DecisionRecord]:
        if not self._active_trace:
            return None
        return self._active_trace.add_decision(question, chosen, rationale, alternatives, confidence=confidence)

    def decompose(self, main_task: str, description: str = "") -> DecompositionNode:
        root = DecompositionNode(task=main_task, description=description)
        if self._active_trace:
            self._active_trace.root_decomposition = root
        return root

    def finish(self, outcome: str = "", success: bool = True) -> Optional[ReasoningTrace]:
        if not self._active_trace:
            return None
        self._active_trace.ended_at = time.time()
        self._active_trace.final_outcome = outcome
        self._active_trace.success = success
        self._trace_history.append(self._active_trace)
        if len(self._trace_history) > self._max_history:
            self._trace_history = self._trace_history[-self._max_history:]
        trace = self._active_trace
        self._active_trace = None
        return trace

    def on_step(self, callback: Callable[[ReasoningStep], None]) -> None:
        self._on_step = callback

    def get_history(self, limit: int = 10) -> List[ReasoningTrace]:
        return self._trace_history[-limit:]

    def get_trace(self, trace_id: str) -> Optional[ReasoningTrace]:
        for trace in self._trace_history:
            if trace.trace_id == trace_id:
                return trace
        return None

    def get_stats(self) -> dict:
        return {
            "active": self._active_trace is not None,
            "history_size": len(self._trace_history),
            "total_decisions": sum(len(t.decisions) for t in self._trace_history),
            "total_tokens": sum(t.total_tokens for t in self._trace_history),
            "verbose": self._verbose,
        }

    def reset(self) -> None:
        self._active_trace = None
        self._trace_history.clear()


def get_reasoning_chain() -> ReasoningChain:
    return ReasoningChain.get_instance()
