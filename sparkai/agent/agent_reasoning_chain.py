"""
SparkLabs Agent - Reasoning Chain

A singleton multi-step reasoning system that decomposes complex game
design queries into structured reasoning chains. Supports chain-of-thought,
tree-of-thought exploration, self-verification, and multi-perspective
debate resolution for high-quality AI decisions in game creation.

Architecture:
  ReasoningChain (singleton)
    |-- ReasoningStep (atomic reasoning unit with evidence and confidence)
    |-- ReasoningPath (explored decision path with branching alternatives)
    |-- VerificationResult (self-consistency check with feedback)
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


class ReasoningMode(Enum):
    CHAIN_OF_THOUGHT = "chain_of_thought"
    TREE_OF_THOUGHT = "tree_of_thought"
    SELF_CONSISTENCY = "self_consistency"
    DEBATE = "debate"
    REFLEXION = "reflexion"


class StepType(Enum):
    OBSERVE = "observe"
    ANALYZE = "analyze"
    HYPOTHESIZE = "hypothesize"
    VERIFY = "verify"
    SYNTHESIZE = "synthesize"
    DECIDE = "decide"


class ConfidenceLevel(Enum):
    VERY_LOW = "very_low"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    VERY_HIGH = "very_high"


class VerificationStatus(Enum):
    PENDING = "pending"
    PASSED = "passed"
    FAILED = "failed"
    INCONCLUSIVE = "inconclusive"


# ------------------------------------------------------------------
# Dataclasses
# ------------------------------------------------------------------


@dataclass
class ReasoningStep:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    chain_id: str = ""
    step_type: StepType = StepType.ANALYZE
    content: str = ""
    evidence: List[str] = field(default_factory=list)
    confidence: ConfidenceLevel = ConfidenceLevel.MEDIUM
    confidence_score: float = 0.5
    parent_step_id: str = ""
    children_ids: List[str] = field(default_factory=list)
    alternatives: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=_time_module.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "chain_id": self.chain_id,
            "step_type": self.step_type.value,
            "content": self.content,
            "evidence": self.evidence,
            "confidence": self.confidence.value,
            "confidence_score": self.confidence_score,
            "children_ids": self.children_ids,
            "alternatives": self.alternatives,
            "metadata": self.metadata,
        }


@dataclass
class ReasoningPath:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    chain_id: str = ""
    step_ids: List[str] = field(default_factory=list)
    total_confidence: float = 0.0
    conclusion: str = ""
    is_selected: bool = False
    branch_point: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=_time_module.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "chain_id": self.chain_id,
            "step_count": len(self.step_ids),
            "total_confidence": self.total_confidence,
            "conclusion": self.conclusion,
            "is_selected": self.is_selected,
            "branch_point": self.branch_point,
            "metadata": self.metadata,
        }


@dataclass
class VerificationResult:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    chain_id: str = ""
    status: VerificationStatus = VerificationStatus.PENDING
    score: float = 0.0
    issues: List[str] = field(default_factory=list)
    suggestions: List[str] = field(default_factory=list)
    passed_checks: int = 0
    total_checks: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=_time_module.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "chain_id": self.chain_id,
            "status": self.status.value,
            "score": self.score,
            "issues": self.issues,
            "suggestions": self.suggestions,
            "passed_checks": self.passed_checks,
            "total_checks": self.total_checks,
            "metadata": self.metadata,
        }


@dataclass
class ChainSession:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    query: str = ""
    mode: ReasoningMode = ReasoningMode.CHAIN_OF_THOUGHT
    max_steps: int = 10
    steps: List[ReasoningStep] = field(default_factory=list)
    paths: List[ReasoningPath] = field(default_factory=list)
    verifications: List[VerificationResult] = field(default_factory=list)
    final_answer: str = ""
    is_complete: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=_time_module.time)
    completed_at: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "query": self.query,
            "mode": self.mode.value,
            "max_steps": self.max_steps,
            "step_count": len(self.steps),
            "path_count": len(self.paths),
            "final_answer": self.final_answer,
            "is_complete": self.is_complete,
            "metadata": self.metadata,
        }


# ------------------------------------------------------------------
# Constants
# ------------------------------------------------------------------

MAX_REASONING_STEPS = 20
MIN_CONFIDENCE_THRESHOLD = 0.3
DEFAULT_BEAM_WIDTH = 3
MAX_PATHS = 5
CONSISTENCY_SAMPLE_COUNT = 3

# ------------------------------------------------------------------
# ReasoningChain Singleton
# ------------------------------------------------------------------


class ReasoningChain:
    """Structured multi-step reasoning for game design decision-making.

    Decomposes complex queries into atomic reasoning steps, explores
    multiple solution paths, self-verifies conclusions through
    consistency checking, and resolves conflicts via debate mode.
    """

    _instance: Optional[ReasoningChain] = None
    _lock: threading.RLock = threading.RLock()

    def __new__(cls) -> ReasoningChain:
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    instance = super().__new__(cls)
                    instance._initialized = False
                    cls._instance = instance
        return cls._instance

    @classmethod
    def get_instance(cls) -> ReasoningChain:
        if cls._instance is None:
            cls()
        return cls._instance

    def __init__(self) -> None:
        if self._initialized:
            return
        self._initialized = True
        self._sessions: List[ChainSession] = []
        self._step_index: Dict[str, ReasoningStep] = {}
        self._active_chains: Dict[str, ChainSession] = {}

    def _get_or_create_singleton(self) -> ReasoningChain:
        return self.get_instance()

    def get_stats(self) -> Dict[str, Any]:
        return {
            "total_sessions": len(self._sessions),
            "active_chains": len(self._active_chains),
            "total_steps": len(self._step_index),
            "completed_sessions": sum(1 for s in self._sessions if s.is_complete),
        }

    def start_chain(
        self,
        query: str,
        mode: str = "chain_of_thought",
        max_steps: int = MAX_REASONING_STEPS,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> ChainSession:
        reasoning_mode = ReasoningMode(mode)
        session = ChainSession(
            query=query,
            mode=reasoning_mode,
            max_steps=min(max_steps, MAX_REASONING_STEPS),
            metadata=metadata or {},
        )
        self._sessions.append(session)
        self._active_chains[session.id] = session

        initial_step = ReasoningStep(
            chain_id=session.id,
            step_type=StepType.OBSERVE,
            content=f"Starting analysis of: {query[:200]}",
            confidence=ConfidenceLevel.HIGH,
            confidence_score=0.9,
        )
        session.steps.append(initial_step)
        self._step_index[initial_step.id] = initial_step

        return session

    def add_step(
        self,
        chain_id: str,
        content: str,
        step_type: str = "analyze",
        evidence: Optional[List[str]] = None,
        confidence_score: float = 0.5,
        parent_step_id: str = "",
    ) -> Optional[ReasoningStep]:
        session = self._active_chains.get(chain_id)
        if session is None:
            return None
        if session.is_complete:
            return None
        if len(session.steps) >= session.max_steps:
            return None

        step = ReasoningStep(
            chain_id=chain_id,
            step_type=StepType(step_type),
            content=content,
            evidence=evidence or [],
            confidence=self._score_to_level(confidence_score),
            confidence_score=max(0.0, min(1.0, confidence_score)),
            parent_step_id=parent_step_id,
        )
        session.steps.append(step)
        self._step_index[step.id] = step

        if parent_step_id and parent_step_id in self._step_index:
            self._step_index[parent_step_id].children_ids.append(step.id)

        return step

    def add_alternative(
        self,
        chain_id: str,
        step_id: str,
        alternative_content: str,
        confidence_score: float = 0.5,
    ) -> Optional[ReasoningStep]:
        session = self._active_chains.get(chain_id)
        if session is None:
            return None

        step = self._step_index.get(step_id)
        if step is None:
            return None

        alt = self.add_step(
            chain_id=chain_id,
            content=alternative_content,
            step_type=step.step_type.value,
            confidence_score=confidence_score,
            parent_step_id=step.parent_step_id,
        )
        if alt:
            step.alternatives.append(alt.id)
        return alt

    def explore_paths(
        self,
        chain_id: str,
        beam_width: int = DEFAULT_BEAM_WIDTH,
    ) -> List[ReasoningPath]:
        session = self._active_chains.get(chain_id)
        if session is None:
            return []

        paths: List[ReasoningPath] = []
        root_steps = [s for s in session.steps if not s.parent_step_id]

        for root in root_steps:
            path_ids = self._collect_path(root, [])
            if path_ids:
                avg_conf = self._compute_path_confidence(path_ids)
                path = ReasoningPath(
                    chain_id=chain_id,
                    step_ids=path_ids,
                    total_confidence=avg_conf,
                    conclusion=session.steps[-1].content if session.steps else "",
                )
                paths.append(path)

        paths.sort(key=lambda p: p.total_confidence, reverse=True)
        selected = paths[: min(beam_width, len(paths))]
        for p in selected:
            p.is_selected = True

        session.paths = paths
        return selected

    def verify_chain(
        self,
        chain_id: str,
    ) -> VerificationResult:
        session = self._active_chains.get(chain_id)
        if session is None:
            return VerificationResult(status=VerificationStatus.FAILED)

        checks_passed = 0
        total_checks = 4
        issues: List[str] = []
        suggestions: List[str] = []

        if len(session.steps) < 2:
            issues.append("Too few reasoning steps for meaningful analysis")
            suggestions.append("Add more intermediate steps before concluding")

        confidences = [
            s.confidence_score for s in session.steps if s.step_type != StepType.OBSERVE
        ]
        if confidences and sum(confidences) / len(confidences) < MIN_CONFIDENCE_THRESHOLD:
            issues.append("Average confidence below threshold")
            suggestions.append("Review low-confidence steps and gather more evidence")

        step_types_seen = {s.step_type for s in session.steps}
        required_types = {StepType.OBSERVE, StepType.ANALYZE, StepType.SYNTHESIZE}
        missing_types = required_types - step_types_seen
        if missing_types:
            names = [t.value for t in missing_types]
            issues.append(f"Missing reasoning types: {', '.join(names)}")
            suggestions.append(f"Include {' and '.join(names)} steps")

        has_evidence = any(len(s.evidence) > 0 for s in session.steps)
        if not has_evidence:
            issues.append("No evidence provided for any reasoning step")
            suggestions.append("Add supporting evidence to strengthen claims")

        checks_passed = total_checks - len(issues)
        score = checks_passed / max(total_checks, 1)

        status = VerificationStatus.PASSED if score >= 0.75 else (
            VerificationStatus.FAILED if score < 0.4 else VerificationStatus.INCONCLUSIVE
        )

        result = VerificationResult(
            chain_id=chain_id,
            status=status,
            score=score,
            issues=issues,
            suggestions=suggestions,
            passed_checks=checks_passed,
            total_checks=total_checks,
        )
        session.verifications.append(result)
        return result

    def complete_chain(
        self,
        chain_id: str,
        final_answer: str,
    ) -> Optional[ChainSession]:
        session = self._active_chains.get(chain_id)
        if session is None:
            return None

        decide_step = self.add_step(
            chain_id=chain_id,
            content=final_answer,
            step_type="decide",
            confidence_score=0.95,
        )
        if decide_step:
            decide_step.confidence = ConfidenceLevel.VERY_HIGH

        if session.paths:
            best_path = max(session.paths, key=lambda p: p.total_confidence)
            best_path.conclusion = final_answer

        session.final_answer = final_answer
        session.is_complete = True
        session.completed_at = _time_module.time
        self._active_chains.pop(chain_id, None)

        return session

    def _collect_path(self, step: ReasoningStep, visited: List[str]) -> List[str]:
        path = visited + [step.id]
        for child_id in step.children_ids:
            if child_id in self._step_index:
                child = self._step_index[child_id]
                if step.children_ids.index(child_id) == 0:
                    path = self._collect_path(child, path)
        return path

    def _compute_path_confidence(self, step_ids: List[str]) -> float:
        scores = []
        for sid in step_ids:
            step = self._step_index.get(sid)
            if step:
                scores.append(step.confidence_score)
        return sum(scores) / len(scores) if scores else 0.0

    def _score_to_level(self, score: float) -> ConfidenceLevel:
        if score >= 0.9:
            return ConfidenceLevel.VERY_HIGH
        if score >= 0.7:
            return ConfidenceLevel.HIGH
        if score >= 0.5:
            return ConfidenceLevel.MEDIUM
        if score >= 0.3:
            return ConfidenceLevel.LOW
        return ConfidenceLevel.VERY_LOW


def get_reasoning_chain() -> ReasoningChain:
    return ReasoningChain.get_instance()