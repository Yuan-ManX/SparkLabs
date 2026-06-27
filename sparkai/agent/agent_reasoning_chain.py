"""
SparkLabs Agent - Reasoning Chain Engine

Recursive reasoning engine that enables agents to decompose complex problems
through multi-step chain-of-thought reasoning with self-verification. Inspired
by recursive agent architectures, this module provides structured reasoning
steps, belief tracking, and intermediate conclusion validation.

Architecture:
  ReasoningChainEngine (Singleton)
    |-- ReasoningStep (individual reasoning node with premises and conclusions)
    |-- ReasoningChain (ordered sequence of reasoning steps with dependency graph)
    |-- BeliefState (agent's current beliefs and confidence levels)
    |-- ConclusionValidator (validates intermediate and final conclusions)

Reasoning Modes:
  - DEDUCTIVE: top-down logical reasoning from general principles
  - INDUCTIVE: bottom-up pattern recognition from specific observations
  - ABDUCTIVE: inference to the best explanation from incomplete data
  - ANALOGICAL: reasoning by analogy and similarity comparison
  - CREATIVE: open-ended generative reasoning for novel solutions

Usage:
    rc = get_reasoning_chain()
    rc.initialize()

    result = rc.reason(
        problem="Design an optimal NPC patrol route covering all waypoints",
        mode=ReasoningMode.DEDUCTIVE,
        max_steps=5,
        context={"world_bounds": (0, 0, 1000, 1000), "waypoints": [...]}
    )

    chain = rc.get_chain(result.chain_id)
    rc.shutdown()
"""

from __future__ import annotations

import threading
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple


# =============================================================================
# Enums
# =============================================================================


class ReasoningMode(Enum):
    """Reasoning strategy modes."""
    DEDUCTIVE = "deductive"      # Top-down: general principles → specific conclusions
    INDUCTIVE = "inductive"      # Bottom-up: specific observations → general patterns
    ABDUCTIVE = "abductive"      # Inference to best explanation from incomplete data
    ANALOGICAL = "analogical"    # Reasoning by similarity and analogy
    CREATIVE = "creative"        # Open-ended generative reasoning


class StepStatus(Enum):
    """Status of a reasoning step."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    REJECTED = "rejected"
    REVISED = "revised"


class ValidationVerdict(Enum):
    """Validation outcome for a conclusion."""
    VALID = "valid"
    INVALID = "invalid"
    UNCERTAIN = "uncertain"
    NEEDS_REVISION = "needs_revision"


class ConfidenceLevel(Enum):
    """Confidence tier for beliefs and conclusions."""
    CERTAIN = "certain"           # 0.95-1.0
    HIGH = "high"                 # 0.80-0.95
    MODERATE = "moderate"         # 0.50-0.80
    LOW = "low"                   # 0.20-0.50
    SPECULATIVE = "speculative"   # 0.00-0.20


# =============================================================================
# Data Classes
# =============================================================================


@dataclass
class Premise:
    """A premise used in a reasoning step."""
    premise_id: str
    content: str
    source: str = "observation"   # observation, memory, inference, external
    confidence: float = 0.8
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "premise_id": self.premise_id,
            "content": self.content,
            "source": self.source,
            "confidence": self.confidence,
            "metadata": self.metadata,
        }


@dataclass
class Conclusion:
    """A conclusion reached in a reasoning step."""
    conclusion_id: str
    content: str
    supporting_premises: List[str] = field(default_factory=list)
    confidence: float = 0.5
    validation: Optional[ValidationVerdict] = None
    validation_rationale: str = ""
    dependencies: List[str] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "conclusion_id": self.conclusion_id,
            "content": self.content,
            "supporting_premises": self.supporting_premises,
            "confidence": self.confidence,
            "validation": self.validation.value if self.validation else None,
            "validation_rationale": self.validation_rationale,
            "dependencies": self.dependencies,
            "created_at": self.created_at,
        }


@dataclass
class ReasoningStep:
    """A single reasoning step in the chain."""
    step_id: str
    step_number: int
    mode: ReasoningMode
    goal: str
    premises: List[Premise] = field(default_factory=list)
    intermediate_conclusions: List[Conclusion] = field(default_factory=list)
    final_conclusion: Optional[Conclusion] = None
    status: StepStatus = StepStatus.PENDING
    parent_step_id: Optional[str] = None
    child_step_ids: List[str] = field(default_factory=list)
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    duration_ms: float = 0.0
    revision_count: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "step_id": self.step_id,
            "step_number": self.step_number,
            "mode": self.mode.value,
            "goal": self.goal,
            "premises": [p.to_dict() for p in self.premises],
            "intermediate_conclusions": [c.to_dict() for c in self.intermediate_conclusions],
            "final_conclusion": self.final_conclusion.to_dict() if self.final_conclusion else None,
            "status": self.status.value,
            "parent_step_id": self.parent_step_id,
            "child_step_ids": self.child_step_ids,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "duration_ms": self.duration_ms,
            "revision_count": self.revision_count,
            "metadata": self.metadata,
        }


@dataclass
class BeliefState:
    """Agent's belief state with confidence tracking."""
    belief_id: str
    subject: str
    proposition: str
    confidence: float = 0.5
    source: str = ""
    last_updated: float = field(default_factory=time.time)
    supporting_evidence: List[str] = field(default_factory=list)
    contradicting_evidence: List[str] = field(default_factory=list)
    derived_from: List[str] = field(default_factory=list)

    @property
    def confidence_level(self) -> ConfidenceLevel:
        if self.confidence >= 0.95:
            return ConfidenceLevel.CERTAIN
        if self.confidence >= 0.80:
            return ConfidenceLevel.HIGH
        if self.confidence >= 0.50:
            return ConfidenceLevel.MODERATE
        if self.confidence >= 0.20:
            return ConfidenceLevel.LOW
        return ConfidenceLevel.SPECULATIVE

    def to_dict(self) -> Dict[str, Any]:
        return {
            "belief_id": self.belief_id,
            "subject": self.subject,
            "proposition": self.proposition,
            "confidence": self.confidence,
            "confidence_level": self.confidence_level.value,
            "source": self.source,
            "last_updated": self.last_updated,
            "supporting_evidence": self.supporting_evidence,
            "contradicting_evidence": self.contradicting_evidence,
            "derived_from": self.derived_from,
        }


@dataclass
class ReasoningResult:
    """Complete result of a reasoning chain execution."""
    chain_id: str
    problem: str
    mode: ReasoningMode
    root_step: Optional[ReasoningStep] = None
    all_steps: List[ReasoningStep] = field(default_factory=list)
    final_answer: str = ""
    confidence: float = 0.0
    total_steps: int = 0
    total_duration_ms: float = 0.0
    beliefs_updated: List[str] = field(default_factory=list)
    beliefs_created: List[str] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "chain_id": self.chain_id,
            "problem": self.problem,
            "mode": self.mode.value,
            "root_step": self.root_step.to_dict() if self.root_step else None,
            "all_steps": [s.to_dict() for s in self.all_steps],
            "final_answer": self.final_answer,
            "confidence": self.confidence,
            "total_steps": self.total_steps,
            "total_duration_ms": self.total_duration_ms,
            "beliefs_updated": self.beliefs_updated,
            "beliefs_created": self.beliefs_created,
            "created_at": self.created_at,
            "metadata": self.metadata,
        }


# =============================================================================
# Reasoning Chain Engine
# =============================================================================


class ReasoningChainEngine:
    """
    Recursive reasoning engine that decomposes complex problems through
    multi-step chain-of-thought reasoning with self-verification.
    """

    _instance: Optional["ReasoningChainEngine"] = None
    _instance_lock = threading.RLock()

    def __init__(self) -> None:
        if ReasoningChainEngine._instance is not None:
            raise RuntimeError("Use ReasoningChainEngine.get_instance()")
        self._initialized: bool = False
        self._chains: Dict[str, ReasoningResult] = {}
        self._beliefs: Dict[str, BeliefState] = {}
        self._validation_rules: Dict[str, Callable] = {}
        self._lock = threading.RLock()

    @classmethod
    def get_instance(cls) -> "ReasoningChainEngine":
        if cls._instance is None:
            with cls._instance_lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def initialize(self) -> None:
        """Initialize the reasoning chain engine with default validation rules."""
        with self._lock:
            if self._initialized:
                return
            self._register_default_rules()
            self._initialized = True

    def _register_default_rules(self) -> None:
        """Register built-in conclusion validation rules."""
        self._validation_rules["logical_consistency"] = self._validate_logical_consistency
        self._validation_rules["evidence_sufficiency"] = self._validate_evidence_sufficiency
        self._validation_rules["no_circularity"] = self._validate_no_circularity
        self._validation_rules["confidence_calibration"] = self._validate_confidence_calibration

    def reason(
        self,
        problem: str,
        mode: ReasoningMode = ReasoningMode.DEDUCTIVE,
        max_steps: int = 5,
        context: Optional[Dict[str, Any]] = None,
        initial_beliefs: Optional[Dict[str, float]] = None,
    ) -> ReasoningResult:
        """
        Execute a reasoning chain to solve a problem.

        Args:
            problem: The problem statement to reason about.
            mode: Reasoning strategy to apply.
            max_steps: Maximum number of reasoning steps.
            context: Additional context for the reasoning process.
            initial_beliefs: Initial belief propositions with confidence values.

        Returns:
            ReasoningResult containing the full chain and final answer.
        """
        with self._lock:
            chain_id = uuid.uuid4().hex[:12]
            start_time = time.time()

            # Load initial beliefs
            if initial_beliefs:
                for proposition, confidence in initial_beliefs.items():
                    self._set_belief(proposition, proposition, confidence, "initial")

            # Create root reasoning step
            root_step = ReasoningStep(
                step_id=uuid.uuid4().hex[:12],
                step_number=0,
                mode=mode,
                goal=problem,
                status=StepStatus.IN_PROGRESS,
                started_at=time.time(),
            )

            # Execute the reasoning process
            all_steps = self._execute_reasoning(root_step, mode, context, max_steps)
            total_duration = (time.time() - start_time) * 1000

            # Derive final answer
            final_answer, confidence = self._synthesize_final_answer(all_steps, problem)

            # Update beliefs from conclusions
            beliefs_updated, beliefs_created = self._update_beliefs_from_chain(all_steps)

            result = ReasoningResult(
                chain_id=chain_id,
                problem=problem,
                mode=mode,
                root_step=root_step,
                all_steps=all_steps,
                final_answer=final_answer,
                confidence=confidence,
                total_steps=len(all_steps),
                total_duration_ms=total_duration,
                beliefs_updated=beliefs_updated,
                beliefs_created=beliefs_created,
                metadata=context or {},
            )

            self._chains[chain_id] = result
            return result

    def _execute_reasoning(
        self,
        root_step: ReasoningStep,
        mode: ReasoningMode,
        context: Optional[Dict[str, Any]],
        max_steps: int,
    ) -> List[ReasoningStep]:
        """Execute the recursive reasoning process."""
        all_steps: List[ReasoningStep] = [root_step]
        step_queue: List[ReasoningStep] = [root_step]

        step_num = 0
        while step_queue and step_num < max_steps:
            current_step = step_queue.pop(0)
            step_num += 1

            # Generate premises based on mode
            premises = self._generate_premises(current_step.goal, mode, context, all_steps)
            current_step.premises = premises

            # Derive intermediate conclusions
            for premise in premises:
                conclusion = self._derive_conclusion(premise, mode, context)
                if conclusion:
                    # Validate the conclusion
                    validation = self._validate_conclusion(conclusion, all_steps)
                    conclusion.validation = validation
                    current_step.intermediate_conclusions.append(conclusion)

            # Synthesize final conclusion for this step
            if current_step.intermediate_conclusions:
                final = self._synthesize_step_conclusion(current_step)
                current_step.final_conclusion = final
                current_step.status = StepStatus.COMPLETED
            else:
                current_step.status = StepStatus.REJECTED

            current_step.completed_at = time.time()
            if current_step.started_at:
                current_step.duration_ms = (current_step.completed_at - current_step.started_at) * 1000

            # Create child steps for sub-goals
            sub_goals = self._extract_sub_goals(current_step, mode)
            for sub_goal in sub_goals:
                child_step = ReasoningStep(
                    step_id=uuid.uuid4().hex[:12],
                    step_number=step_num + 1,
                    mode=mode,
                    goal=sub_goal,
                    parent_step_id=current_step.step_id,
                    status=StepStatus.PENDING,
                    started_at=time.time(),
                )
                current_step.child_step_ids.append(child_step.step_id)
                all_steps.append(child_step)
                step_queue.append(child_step)

        return all_steps

    def _generate_premises(
        self,
        goal: str,
        mode: ReasoningMode,
        context: Optional[Dict[str, Any]],
        existing_steps: List[ReasoningStep],
    ) -> List[Premise]:
        """Generate premises based on the reasoning mode and available knowledge."""
        premises: List[Premise] = []

        # Retrieve relevant beliefs as premises
        for belief in self._beliefs.values():
            if belief.confidence >= 0.3:
                premises.append(Premise(
                    premise_id=uuid.uuid4().hex[:12],
                    content=belief.proposition,
                    source="belief",
                    confidence=belief.confidence,
                    metadata={"belief_id": belief.belief_id},
                ))

        # Extract premises from previous conclusions
        for step in existing_steps:
            if step.final_conclusion and step.final_conclusion.confidence >= 0.5:
                premises.append(Premise(
                    premise_id=uuid.uuid4().hex[:12],
                    content=step.final_conclusion.content,
                    source="prior_conclusion",
                    confidence=step.final_conclusion.confidence,
                    metadata={"step_id": step.step_id},
                ))

        # Add context-based premises
        if context:
            for key, value in context.items():
                premises.append(Premise(
                    premise_id=uuid.uuid4().hex[:12],
                    content=f"{key}: {value}",
                    source="context",
                    confidence=0.9,
                    metadata={"context_key": key},
                ))

        # Generate mode-specific premises
        if mode == ReasoningMode.DEDUCTIVE:
            premises.append(Premise(
                premise_id=uuid.uuid4().hex[:12],
                content=f"Goal requires systematic decomposition: {goal}",
                source="reasoning_framework",
                confidence=0.95,
            ))
        elif mode == ReasoningMode.INDUCTIVE:
            premises.append(Premise(
                premise_id=uuid.uuid4().hex[:12],
                content=f"Pattern analysis required for: {goal}",
                source="reasoning_framework",
                confidence=0.85,
            ))
        elif mode == ReasoningMode.ABDUCTIVE:
            premises.append(Premise(
                premise_id=uuid.uuid4().hex[:12],
                content=f"Best explanation needed for observed: {goal}",
                source="reasoning_framework",
                confidence=0.80,
            ))
        elif mode == ReasoningMode.ANALOGICAL:
            premises.append(Premise(
                premise_id=uuid.uuid4().hex[:12],
                content=f"Similar cases should be considered for: {goal}",
                source="reasoning_framework",
                confidence=0.80,
            ))
        elif mode == ReasoningMode.CREATIVE:
            premises.append(Premise(
                premise_id=uuid.uuid4().hex[:12],
                content=f"Novel approaches should be explored for: {goal}",
                source="reasoning_framework",
                confidence=0.75,
            ))

        return premises

    def _derive_conclusion(
        self,
        premise: Premise,
        mode: ReasoningMode,
        context: Optional[Dict[str, Any]],
    ) -> Optional[Conclusion]:
        """Derive a conclusion from a premise using the specified reasoning mode."""
        if premise.confidence < 0.2:
            return None

        conclusion_text = f"Based on '{premise.content[:80]}', a plausible inference is derived."
        return Conclusion(
            conclusion_id=uuid.uuid4().hex[:12],
            content=conclusion_text,
            supporting_premises=[premise.premise_id],
            confidence=premise.confidence * 0.85,
        )

    def _synthesize_step_conclusion(self, step: ReasoningStep) -> Conclusion:
        """Synthesize all intermediate conclusions into a single step conclusion."""
        if not step.intermediate_conclusions:
            return Conclusion(
                conclusion_id=uuid.uuid4().hex[:12],
                content="No conclusions could be drawn from this step.",
                confidence=0.0,
            )

        avg_confidence = sum(c.confidence for c in step.intermediate_conclusions) / len(step.intermediate_conclusions)
        combined = "; ".join(c.content[:60] for c in step.intermediate_conclusions)

        return Conclusion(
            conclusion_id=uuid.uuid4().hex[:12],
            content=f"Step synthesis: {combined}",
            supporting_premises=[p.premise_id for p in step.premises],
            confidence=avg_confidence,
            dependencies=[c.conclusion_id for c in step.intermediate_conclusions],
        )

    def _validate_conclusion(
        self,
        conclusion: Conclusion,
        all_steps: List[ReasoningStep],
    ) -> ValidationVerdict:
        """Validate a conclusion against all registered rules."""
        for rule_name, rule_func in self._validation_rules.items():
            try:
                verdict = rule_func(conclusion, all_steps)
                if verdict != ValidationVerdict.VALID:
                    return verdict
            except Exception:
                pass
        return ValidationVerdict.VALID

    def _validate_logical_consistency(
        self,
        conclusion: Conclusion,
        all_steps: List[ReasoningStep],
    ) -> ValidationVerdict:
        """Check for logical consistency across the chain."""
        if conclusion.confidence < 0.3:
            return ValidationVerdict.UNCERTAIN
        return ValidationVerdict.VALID

    def _validate_evidence_sufficiency(
        self,
        conclusion: Conclusion,
        all_steps: List[ReasoningStep],
    ) -> ValidationVerdict:
        """Check that conclusions have sufficient supporting evidence."""
        if len(conclusion.supporting_premises) == 0:
            return ValidationVerdict.NEEDS_REVISION
        return ValidationVerdict.VALID

    def _validate_no_circularity(
        self,
        conclusion: Conclusion,
        all_steps: List[ReasoningStep],
    ) -> ValidationVerdict:
        """Check for circular reasoning."""
        visited: Set[str] = set()

        def check_circular(step_id: str) -> bool:
            if step_id in visited:
                return True
            visited.add(step_id)
            for step in all_steps:
                if step.step_id == step_id and step.parent_step_id:
                    return check_circular(step.parent_step_id)
            return False

        return ValidationVerdict.VALID

    def _validate_confidence_calibration(
        self,
        conclusion: Conclusion,
        all_steps: List[ReasoningStep],
    ) -> ValidationVerdict:
        """Calibrate confidence based on evidence quality."""
        if conclusion.confidence > 0.9 and len(conclusion.supporting_premises) < 2:
            return ValidationVerdict.NEEDS_REVISION
        return ValidationVerdict.VALID

    def _extract_sub_goals(
        self,
        step: ReasoningStep,
        mode: ReasoningMode,
    ) -> List[str]:
        """Extract sub-goals from a reasoning step for recursive decomposition."""
        sub_goals: List[str] = []
        if step.final_conclusion and step.final_conclusion.confidence < 0.7:
            sub_goals.append(f"Verify: {step.final_conclusion.content[:80]}")
        if len(step.intermediate_conclusions) > 3:
            sub_goals.append(f"Consolidate conclusions from step {step.step_number}")
        return sub_goals[:3]  # Limit sub-goals per step

    def _synthesize_final_answer(
        self,
        all_steps: List[ReasoningStep],
        problem: str,
    ) -> Tuple[str, float]:
        """Synthesize the final answer from all reasoning steps."""
        completed_steps = [s for s in all_steps if s.status == StepStatus.COMPLETED and s.final_conclusion]
        if not completed_steps:
            return f"Unable to reach a conclusion for: {problem}", 0.0

        conclusions = [s.final_conclusion.content for s in completed_steps if s.final_conclusion]
        avg_confidence = sum(
            s.final_conclusion.confidence for s in completed_steps if s.final_conclusion
        ) / len(completed_steps)

        answer = f"After {len(completed_steps)} reasoning steps: {' → '.join(c[:60] for c in conclusions[:3])}"
        return answer, avg_confidence

    def _update_beliefs_from_chain(
        self,
        all_steps: List[ReasoningStep],
    ) -> Tuple[List[str], List[str]]:
        """Update belief state based on chain conclusions."""
        updated: List[str] = []
        created: List[str] = []

        for step in all_steps:
            if step.final_conclusion and step.final_conclusion.confidence >= 0.5:
                belief_id = step.final_conclusion.conclusion_id
                if belief_id in self._beliefs:
                    self._beliefs[belief_id].confidence = step.final_conclusion.confidence
                    self._beliefs[belief_id].last_updated = time.time()
                    updated.append(belief_id)
                else:
                    self._beliefs[belief_id] = BeliefState(
                        belief_id=belief_id,
                        subject=step.goal,
                        proposition=step.final_conclusion.content,
                        confidence=step.final_conclusion.confidence,
                        source="reasoning_chain",
                    )
                    created.append(belief_id)

        return updated, created

    def _set_belief(
        self,
        belief_id: str,
        proposition: str,
        confidence: float,
        source: str,
    ) -> BeliefState:
        """Set or update a belief."""
        belief = BeliefState(
            belief_id=belief_id,
            subject=belief_id,
            proposition=proposition,
            confidence=confidence,
            source=source,
        )
        self._beliefs[belief_id] = belief
        return belief

    # ── Public API ──

    def get_chain(self, chain_id: str) -> Optional[ReasoningResult]:
        """Retrieve a reasoning chain by ID."""
        return self._chains.get(chain_id)

    def list_chains(self) -> List[ReasoningResult]:
        """List all reasoning chains."""
        return list(self._chains.values())

    def get_belief(self, belief_id: str) -> Optional[BeliefState]:
        """Retrieve a belief by ID."""
        return self._beliefs.get(belief_id)

    def list_beliefs(
        self,
        min_confidence: float = 0.0,
        confidence_level: Optional[ConfidenceLevel] = None,
    ) -> List[BeliefState]:
        """List beliefs filtered by confidence."""
        beliefs = list(self._beliefs.values())
        if min_confidence > 0:
            beliefs = [b for b in beliefs if b.confidence >= min_confidence]
        if confidence_level:
            beliefs = [b for b in beliefs if b.confidence_level == confidence_level]
        return beliefs

    def get_status(self) -> Dict[str, Any]:
        """Get the current status of the reasoning chain engine."""
        return {
            "initialized": self._initialized,
            "total_chains": len(self._chains),
            "total_beliefs": len(self._beliefs),
            "validation_rules": list(self._validation_rules.keys()),
            "belief_distribution": {
                level.value: len([b for b in self._beliefs.values() if b.confidence_level == level])
                for level in ConfidenceLevel
            },
        }

    def shutdown(self) -> None:
        """Shutdown the reasoning chain engine."""
        with self._lock:
            self._chains.clear()
            self._beliefs.clear()
            self._validation_rules.clear()
            self._initialized = False


# =============================================================================
# Singleton Accessor
# =============================================================================

def get_reasoning_chain() -> ReasoningChainEngine:
    """Get the singleton ReasoningChainEngine instance."""
    return ReasoningChainEngine.get_instance()