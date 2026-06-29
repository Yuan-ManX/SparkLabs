"""
SparkLabs Reasoning Synthesis Engine

A multi-strategy reasoning engine that combines chain-of-thought,
tree-of-thought, and mixture-of-agents reasoning approaches. The engine
runs parallel reasoning paths and synthesizes them into a unified
conclusion with confidence scoring.

Key capabilities:
- Multiple reasoning strategies with automatic selection
- Parallel reasoning path execution
- Consensus synthesis from divergent conclusions
- Confidence scoring with uncertainty quantification
- Reasoning trace recording for transparency and debugging
- Adaptive strategy selection based on task complexity
"""

from __future__ import annotations

import threading
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple


class ReasoningStrategy(Enum):
    """Available reasoning strategies."""
    CHAIN_OF_THOUGHT = "chain_of_thought"
    TREE_OF_THOUGHT = "tree_of_thought"
    MIXTURE_OF_AGENTS = "mixture_of_agents"
    REFLEXIVE = "reflexive"
    DECOMPOSITIVE = "decompositive"
    ANALOGICAL = "analogical"
    ABDUCTIVE = "abductive"
    DEDUCTIVE = "deductive"


class SynthesisMode(Enum):
    """How to combine multiple reasoning paths."""
    MAJORITY_VOTE = "majority_vote"
    WEIGHTED_AVERAGE = "weighted_average"
    BEST_PATH = "best_path"
    CONSENSUS = "consensus"
    HIERARCHICAL = "hierarchical"


class ReasoningState(Enum):
    """State of the reasoning engine."""
    IDLE = "idle"
    ANALYZING = "analyzing"
    REASONING = "reasoning"
    SYNTHESIZING = "synthesizing"
    COMPLETE = "complete"
    FAILED = "failed"


@dataclass
class ReasoningPath:
    """A single reasoning path through a problem."""
    path_id: str = field(default_factory=lambda: f"path_{uuid.uuid4().hex[:8]}")
    strategy: ReasoningStrategy = ReasoningStrategy.CHAIN_OF_THOUGHT
    steps: List[Dict[str, Any]] = field(default_factory=list)
    conclusion: str = ""
    confidence: float = 0.5
    tokens_used: int = 0
    duration_ms: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def add_step(self, thought: str, evidence: str = "", action: str = "") -> None:
        self.steps.append({
            "step_num": len(self.steps) + 1,
            "thought": thought,
            "evidence": evidence,
            "action": action,
            "timestamp": time.time(),
        })

    @property
    def step_count(self) -> int:
        return len(self.steps)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "path_id": self.path_id,
            "strategy": self.strategy.value,
            "steps": list(self.steps),
            "conclusion": self.conclusion,
            "confidence": self.confidence,
            "tokens_used": self.tokens_used,
            "duration_ms": self.duration_ms,
            "step_count": self.step_count,
            "metadata": dict(self.metadata),
        }


@dataclass
class ReasoningResult:
    """The final synthesized result of multi-path reasoning."""
    result_id: str = field(default_factory=lambda: f"result_{uuid.uuid4().hex[:10]}")
    query: str = ""
    paths: List[ReasoningPath] = field(default_factory=list)
    synthesis: str = ""
    confidence: float = 0.5
    uncertainty: float = 0.5
    consensus_level: float = 0.0
    strategy_used: ReasoningStrategy = ReasoningStrategy.CHAIN_OF_THOUGHT
    synthesis_mode: SynthesisMode = SynthesisMode.CONSENSUS
    total_tokens: int = 0
    total_duration_ms: float = 0.0
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "result_id": self.result_id,
            "query": self.query,
            "paths": [p.to_dict() for p in self.paths],
            "synthesis": self.synthesis,
            "confidence": self.confidence,
            "uncertainty": self.uncertainty,
            "consensus_level": self.consensus_level,
            "strategy_used": self.strategy_used.value,
            "synthesis_mode": self.synthesis_mode.value,
            "total_tokens": self.total_tokens,
            "total_duration_ms": self.total_duration_ms,
            "path_count": len(self.paths),
            "timestamp": self.timestamp,
        }


@dataclass
class ReasoningSnapshot:
    """Snapshot of the reasoning engine state."""
    engine_id: str
    state: ReasoningState
    total_queries: int
    avg_confidence: float
    avg_duration_ms: float
    strategy_usage: Dict[str, int]
    active_paths: int
    last_result: Optional[Dict[str, Any]]
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "engine_id": self.engine_id,
            "state": self.state.value,
            "total_queries": self.total_queries,
            "avg_confidence": self.avg_confidence,
            "avg_duration_ms": self.avg_duration_ms,
            "strategy_usage": dict(self.strategy_usage),
            "active_paths": self.active_paths,
            "last_result": self.last_result,
            "timestamp": self.timestamp,
        }


class ReasoningSynthesisEngine:
    """
    Singleton engine that orchestrates multi-strategy reasoning with
    parallel path execution and consensus synthesis.
    """

    _instance: Optional["ReasoningSynthesisEngine"] = None
    _lock = threading.RLock()

    def __init__(self) -> None:
        self._engine_id: str = f"reasoning_{uuid.uuid4().hex[:10]}"
        self._state: ReasoningState = ReasoningState.IDLE
        self._initialized: bool = True
        self._instance_lock = threading.RLock()

        self._strategy_handlers: Dict[ReasoningStrategy, Callable] = {}
        self._synthesis_handlers: Dict[SynthesisMode, Callable] = {}

        self._total_queries: int = 0
        self._confidence_history: List[float] = []
        self._duration_history: List[float] = []
        self._strategy_usage: Dict[str, int] = {s.value: 0 for s in ReasoningStrategy}
        self._last_result: Optional[Dict[str, Any]] = None

        self._max_paths: int = 5
        self._default_strategies: List[ReasoningStrategy] = [
            ReasoningStrategy.CHAIN_OF_THOUGHT,
            ReasoningStrategy.TREE_OF_THOUGHT,
            ReasoningStrategy.MIXTURE_OF_AGENTS,
        ]
        self._default_synthesis: SynthesisMode = SynthesisMode.CONSENSUS

    @classmethod
    def get_instance(cls) -> "ReasoningSynthesisEngine":
        with cls._lock:
            if cls._instance is None:
                cls._instance = cls()
            return cls._instance

    def initialize(
        self,
        max_paths: int = 5,
        strategies: Optional[List[ReasoningStrategy]] = None,
        synthesis_mode: SynthesisMode = SynthesisMode.CONSENSUS,
    ) -> None:
        with self._instance_lock:
            self._max_paths = max_paths
            self._default_strategies = strategies or self._default_strategies
            self._default_synthesis = synthesis_mode
            self._state = ReasoningState.IDLE

    def register_strategy_handler(
        self, strategy: ReasoningStrategy, handler: Callable
    ) -> None:
        with self._instance_lock:
            self._strategy_handlers[strategy] = handler

    def register_synthesis_handler(
        self, mode: SynthesisMode, handler: Callable
    ) -> None:
        with self._instance_lock:
            self._synthesis_handlers[mode] = handler

    def select_strategies(self, query: str, complexity: float = 0.5) -> List[ReasoningStrategy]:
        """Select reasoning strategies based on query complexity."""
        if complexity < 0.3:
            return [ReasoningStrategy.CHAIN_OF_THOUGHT, ReasoningStrategy.REFLEXIVE]
        if complexity < 0.6:
            return [ReasoningStrategy.CHAIN_OF_THOUGHT, ReasoningStrategy.TREE_OF_THOUGHT]
        return [ReasoningStrategy.TREE_OF_THOUGHT, ReasoningStrategy.MIXTURE_OF_AGENTS, ReasoningStrategy.DEDUCTIVE]

    def run_reasoning(
        self,
        query: str,
        context: Optional[Dict[str, Any]] = None,
        strategies: Optional[List[ReasoningStrategy]] = None,
        synthesis_mode: Optional[SynthesisMode] = None,
    ) -> ReasoningResult:
        """Run multi-strategy reasoning and synthesize results."""
        with self._instance_lock:
            start_time = time.time()
            self._state = ReasoningState.ANALYZING
            self._total_queries += 1

            selected = strategies or self._default_strategies[: self._max_paths]
            mode = synthesis_mode or self._default_synthesis

            self._state = ReasoningState.REASONING
            paths: List[ReasoningPath] = []
            for strategy in selected:
                path = self._run_single_path(strategy, query, context or {})
                paths.append(path)
                self._strategy_usage[strategy.value] = (
                    self._strategy_usage.get(strategy.value, 0) + 1
                )

            self._state = ReasoningState.SYNTHESIZING
            result = ReasoningResult(
                query=query,
                paths=paths,
                synthesis_mode=mode,
                strategy_used=selected[0] if selected else ReasoningStrategy.CHAIN_OF_THOUGHT,
            )

            synthesis_output = self._synthesize(paths, mode)
            result.synthesis = synthesis_output.get("conclusion", "")
            result.confidence = synthesis_output.get("confidence", 0.5)
            result.uncertainty = 1.0 - result.confidence
            result.consensus_level = synthesis_output.get("consensus", 0.0)

            result.total_tokens = sum(p.tokens_used for p in paths)
            result.total_duration_ms = (time.time() - start_time) * 1000.0

            self._confidence_history.append(result.confidence)
            self._duration_history.append(result.total_duration_ms)
            if len(self._confidence_history) > 100:
                self._confidence_history = self._confidence_history[-100:]
            if len(self._duration_history) > 100:
                self._duration_history = self._duration_history[-100:]

            self._last_result = result.to_dict()
            self._state = ReasoningState.COMPLETE
            return result

    def _run_single_path(
        self,
        strategy: ReasoningStrategy,
        query: str,
        context: Dict[str, Any],
    ) -> ReasoningPath:
        path_start = time.time()
        path = ReasoningPath(strategy=strategy, metadata={"context_keys": list(context.keys())})

        handler = self._strategy_handlers.get(strategy)
        if handler is not None:
            try:
                handler_result = handler(query, context)
                if isinstance(handler_result, dict):
                    path.conclusion = handler_result.get("conclusion", "")
                    path.confidence = handler_result.get("confidence", 0.5)
                    path.tokens_used = handler_result.get("tokens", 0)
                    for step in handler_result.get("steps", []):
                        path.add_step(
                            thought=step.get("thought", ""),
                            evidence=step.get("evidence", ""),
                            action=step.get("action", ""),
                        )
                elif isinstance(handler_result, str):
                    path.conclusion = handler_result
                    path.confidence = 0.5
            except Exception as e:
                path.conclusion = f"error: {e}"
                path.confidence = 0.0
        else:
            path.add_step(thought=f"Analyzing query with {strategy.value}", action="analyze")
            path.add_step(thought="No handler registered, using heuristic", action="heuristic")
            path.conclusion = f"Heuristic analysis of: {query[:100]}"
            path.confidence = 0.3
            path.tokens_used = 50

        path.duration_ms = (time.time() - path_start) * 1000.0
        return path

    def _synthesize(self, paths: List[ReasoningPath], mode: SynthesisMode) -> Dict[str, Any]:
        handler = self._synthesis_handlers.get(mode)
        if handler is not None:
            try:
                return handler(paths)
            except Exception:
                pass

        if not paths:
            return {"conclusion": "no_paths", "confidence": 0.0, "consensus": 0.0}

        if mode == SynthesisMode.MAJORITY_VOTE:
            conclusions: Dict[str, int] = {}
            for p in paths:
                conclusions[p.conclusion] = conclusions.get(p.conclusion, 0) + 1
            best = max(conclusions, key=conclusions.get)
            vote_ratio = conclusions[best] / len(paths)
            return {"conclusion": best, "confidence": vote_ratio, "consensus": vote_ratio}

        if mode == SynthesisMode.WEIGHTED_AVERAGE:
            total_weight = sum(p.confidence for p in paths)
            if total_weight == 0:
                return {"conclusion": paths[0].conclusion, "confidence": 0.0, "consensus": 0.0}
            weighted_conf = sum(p.confidence * p.confidence for p in paths) / total_weight
            best_path = max(paths, key=lambda p: p.confidence)
            return {
                "conclusion": best_path.conclusion,
                "confidence": weighted_conf,
                "consensus": weighted_conf,
            }

        if mode == SynthesisMode.BEST_PATH:
            best = max(paths, key=lambda p: p.confidence)
            return {
                "conclusion": best.conclusion,
                "confidence": best.confidence,
                "consensus": best.confidence,
            }

        # CONSENSUS and HIERARCHICAL default
        avg_conf = sum(p.confidence for p in paths) / len(paths)
        conclusions = [p.conclusion for p in paths]
        unique = set(conclusions)
        consensus = 1.0 - (len(unique) - 1) / max(1, len(paths))

        best_path = max(paths, key=lambda p: p.confidence)
        synthesis_text = best_path.conclusion
        if len(unique) > 1 and consensus < 0.5:
            synthesis_text = (
                f"Multiple conclusions reached. Primary: {best_path.conclusion}. "
                f"Alternatives: {[c for c in unique if c != best_path.conclusion][:3]}"
            )

        return {
            "conclusion": synthesis_text,
            "confidence": avg_conf,
            "consensus": consensus,
        }

    def get_status(self) -> Dict[str, Any]:
        with self._instance_lock:
            avg_conf = (
                sum(self._confidence_history) / len(self._confidence_history)
                if self._confidence_history
                else 0.0
            )
            avg_dur = (
                sum(self._duration_history) / len(self._duration_history)
                if self._duration_history
                else 0.0
            )
            return {
                "engine_id": self._engine_id,
                "state": self._state.value,
                "total_queries": self._total_queries,
                "avg_confidence": avg_conf,
                "avg_duration_ms": avg_dur,
                "strategy_usage": dict(self._strategy_usage),
                "active_paths": 0,
                "last_result": self._last_result,
            }

    def get_snapshot(self) -> ReasoningSnapshot:
        with self._instance_lock:
            avg_conf = (
                sum(self._confidence_history) / len(self._confidence_history)
                if self._confidence_history
                else 0.0
            )
            avg_dur = (
                sum(self._duration_history) / len(self._duration_history)
                if self._duration_history
                else 0.0
            )
            return ReasoningSnapshot(
                engine_id=self._engine_id,
                state=self._state,
                total_queries=self._total_queries,
                avg_confidence=avg_conf,
                avg_duration_ms=avg_dur,
                strategy_usage=dict(self._strategy_usage),
                active_paths=0,
                last_result=self._last_result,
            )

    def reset(self) -> None:
        with self._instance_lock:
            self._state = ReasoningState.IDLE
            self._total_queries = 0
            self._confidence_history.clear()
            self._duration_history.clear()
            self._strategy_usage = {s.value: 0 for s in ReasoningStrategy}
            self._last_result = None


def get_reasoning_synthesis_engine() -> ReasoningSynthesisEngine:
    """Module-level factory for the ReasoningSynthesisEngine singleton."""
    return ReasoningSynthesisEngine.get_instance()
