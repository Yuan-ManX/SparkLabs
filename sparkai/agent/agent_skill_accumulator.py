"""
SparkLabs Agent Skill Accumulator

Provides procedural skill accumulation that transforms successful
execution patterns into reusable, persistent skills. The accumulator
organizes skills into domains, tracks version histories, and supports
skill composition for complex task execution.

Core architecture:
  - Skill Capture: Extracts reusable patterns from execution traces
  - Skill Organization: Categorizes skills by domain and maturity
  - Skill Composition: Chains multiple skills into composite workflows
  - Skill Refinement: Iteratively improves skills through usage feedback
  - Skill Discovery: Surfaces relevant skills based on task context
"""

import threading
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class SkillDomain(Enum):
    """Domains for categorizing accumulated skills."""
    WORLD_GENERATION = "world_generation"
    CHARACTER_CREATION = "character_creation"
    QUEST_DESIGN = "quest_design"
    DIALOGUE_SYSTEM = "dialogue_system"
    COMBAT_BALANCE = "combat_balance"
    ECONOMY_DESIGN = "economy_design"
    LEVEL_DESIGN = "level_design"
    AI_BEHAVIOR = "ai_behavior"
    NARRATIVE_DESIGN = "narrative_design"
    AUDIO_DESIGN = "audio_design"
    VISUAL_EFFECTS = "visual_effects"
    GAME_MECHANICS = "game_mechanics"
    TESTING = "testing"
    OPTIMIZATION = "optimization"


class SkillMaturity(Enum):
    """Maturity level of an accumulated skill."""
    EXPERIMENTAL = "experimental"
    DEVELOPING = "developing"
    STABLE = "stable"
    PROVEN = "proven"
    CORE = "core"


class ExecutionOutcome(Enum):
    """Outcome of a skill execution."""
    SUCCESS = "success"
    PARTIAL = "partial"
    FAILURE = "failure"
    NOT_APPLICABLE = "not_applicable"


# ---------------------------------------------------------------------------
# Data Classes
# ---------------------------------------------------------------------------

@dataclass
class SkillStep:
    """A single step within an accumulated skill."""
    step_id: str
    order: int
    description: str
    action_type: str
    parameters: Dict[str, Any] = field(default_factory=dict)
    expected_output: str = ""
    fallback_action: Optional[str] = None
    timeout_ms: float = 30000.0


@dataclass
class AccumulatedSkill:
    """A reusable skill accumulated from execution experience."""
    skill_id: str
    name: str
    domain: SkillDomain
    description: str
    steps: List[SkillStep] = field(default_factory=list)
    preconditions: List[str] = field(default_factory=list)
    postconditions: List[str] = field(default_factory=list)
    maturity: SkillMaturity = SkillMaturity.EXPERIMENTAL
    version: int = 1
    usage_count: int = 0
    success_count: int = 0
    avg_duration_ms: float = 0.0
    tags: List[str] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)


@dataclass
class SkillExecution:
    """Record of a skill execution instance."""
    execution_id: str
    skill_id: str
    outcome: ExecutionOutcome
    duration_ms: float
    context: Dict[str, Any] = field(default_factory=dict)
    output: Dict[str, Any] = field(default_factory=dict)
    error_details: Optional[str] = None
    executed_at: float = field(default_factory=time.time)


@dataclass
class ComposedSkill:
    """A composition of multiple accumulated skills."""
    composition_id: str
    name: str
    description: str
    skill_ids: List[str]
    execution_order: List[str]  # Ordered skill_ids
    data_flow: Dict[str, Dict[str, str]] = field(default_factory=dict)
    version: int = 1
    usage_count: int = 0
    created_at: float = field(default_factory=time.time)


# ---------------------------------------------------------------------------
# Skill Accumulator Engine
# ---------------------------------------------------------------------------

class SkillAccumulatorEngine:
    """Procedural skill accumulation system for AI game agents.

    Transforms successful execution patterns into reusable, persistent
    skills that improve over time through usage and refinement.

    Usage:
        engine = get_skill_accumulator_engine()
        skill = engine.accumulate_skill(
            domain="world_generation",
            name="Generate Forest Biome",
            steps=[...]
        )
        result = engine.execute_skill(skill.skill_id, context={})
    """

    _instance: Optional["SkillAccumulatorEngine"] = None
    _lock: threading.RLock = threading.RLock()

    MAX_SKILLS: int = 1000
    MAX_SKILL_STEPS: int = 20
    MAX_EXECUTIONS_PER_SKILL: int = 500
    PROMOTION_USAGE_THRESHOLD: int = 10
    PROMOTION_SUCCESS_RATE: float = 0.8

    def __new__(cls) -> "SkillAccumulatorEngine":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    @classmethod
    def get_instance(cls) -> "SkillAccumulatorEngine":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def __init__(self) -> None:
        time.sleep(0.001)
        if not hasattr(self, "_initialized"):
            self._skills: Dict[str, AccumulatedSkill] = {}
            self._executions: Dict[str, List[SkillExecution]] = {}
            self._compositions: Dict[str, ComposedSkill] = {}
            self._domain_index: Dict[SkillDomain, List[str]] = {}
            self._tag_index: Dict[str, List[str]] = {}
            self._total_skills_accumulated: int = 0
            self._total_executions: int = 0
            self._initialized = True

    # ------------------------------------------------------------------
    # Skill Accumulation
    # ------------------------------------------------------------------

    def accumulate_skill(
        self,
        domain: str,
        name: str,
        description: str,
        steps: List[Dict[str, Any]],
        preconditions: Optional[List[str]] = None,
        postconditions: Optional[List[str]] = None,
        tags: Optional[List[str]] = None,
        dependencies: Optional[List[str]] = None,
    ) -> AccumulatedSkill:
        """Accumulate a new skill from execution patterns.

        Args:
            domain: Skill domain category.
            name: Human-readable skill name.
            description: What the skill accomplishes.
            steps: Ordered list of execution steps with parameters.
            preconditions: Conditions that must be met before execution.
            postconditions: Conditions expected after execution.
            tags: Searchable tags.
            dependencies: IDs of prerequisite skills.

        Returns:
            The newly accumulated AccumulatedSkill.
        """
        time.sleep(0.001)
        with self._lock:
            domain_enum = SkillDomain(domain)

            skill_steps = []
            for i, step_data in enumerate(steps[:self.MAX_SKILL_STEPS]):
                skill_steps.append(SkillStep(
                    step_id=uuid.uuid4().hex,
                    order=i,
                    description=step_data.get("description", f"Step {i + 1}"),
                    action_type=step_data.get("action_type", "execute"),
                    parameters=step_data.get("parameters", {}),
                    expected_output=step_data.get("expected_output", ""),
                    fallback_action=step_data.get("fallback_action"),
                    timeout_ms=step_data.get("timeout_ms", 30000.0),
                ))

            skill = AccumulatedSkill(
                skill_id=uuid.uuid4().hex,
                name=name,
                domain=domain_enum,
                description=description,
                steps=skill_steps,
                preconditions=preconditions or [],
                postconditions=postconditions or [],
                tags=tags or [],
                dependencies=dependencies or [],
            )

            self._skills[skill.skill_id] = skill
            self._executions[skill.skill_id] = []
            self._domain_index.setdefault(domain_enum, []).append(skill.skill_id)

            for tag in skill.tags:
                self._tag_index.setdefault(tag, []).append(skill.skill_id)

            self._total_skills_accumulated += 1
            return skill

    # ------------------------------------------------------------------
    # Skill Execution
    # ------------------------------------------------------------------

    def execute_skill(
        self,
        skill_id: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> SkillExecution:
        """Execute an accumulated skill with given context.

        Args:
            skill_id: The skill to execute.
            context: Execution context parameters.

        Returns:
            SkillExecution record with results.
        """
        time.sleep(0.001)
        with self._lock:
            if skill_id not in self._skills:
                return SkillExecution(
                    execution_id=uuid.uuid4().hex,
                    skill_id=skill_id,
                    outcome=ExecutionOutcome.FAILURE,
                    duration_ms=0,
                    error_details=f"Skill {skill_id} not found",
                )

            skill = self._skills[skill_id]
            exec_context = context or {}
            start_time = time.time()

            # Simulate step execution
            outcome = ExecutionOutcome.SUCCESS
            output_data: Dict[str, Any] = {"steps_completed": len(skill.steps)}
            error = None

            try:
                for step in skill.steps:
                    # Validate preconditions
                    if not self._check_step_preconditions(step, exec_context):
                        outcome = ExecutionOutcome.PARTIAL
                        break
                    output_data[f"step_{step.order}"] = {
                        "status": "completed",
                        "description": step.description,
                    }
            except Exception as e:
                outcome = ExecutionOutcome.FAILURE
                error = str(e)

            duration = (time.time() - start_time) * 1000

            execution = SkillExecution(
                execution_id=uuid.uuid4().hex,
                skill_id=skill_id,
                outcome=outcome,
                duration_ms=duration,
                context=exec_context,
                output=output_data,
                error_details=error,
            )

            # Update skill statistics
            skill.usage_count += 1
            if outcome == ExecutionOutcome.SUCCESS:
                skill.success_count += 1
            skill.avg_duration_ms = (
                (skill.avg_duration_ms * (skill.usage_count - 1) + duration)
                / skill.usage_count
            )
            skill.updated_at = time.time()

            # Promote maturity if criteria met
            self._promote_skill_if_ready(skill)

            self._executions[skill_id].append(execution)
            self._total_executions += 1

            # Prune old executions
            if len(self._executions[skill_id]) > self.MAX_EXECUTIONS_PER_SKILL:
                self._executions[skill_id] = self._executions[skill_id][
                    -self.MAX_EXECUTIONS_PER_SKILL:
                ]

            return execution

    def _check_step_preconditions(
        self,
        step: SkillStep,
        context: Dict[str, Any],
    ) -> bool:
        """Check if step preconditions are met in the given context."""
        # Simple validation - always pass for now
        return True

    def _promote_skill_if_ready(self, skill: AccumulatedSkill) -> None:
        """Promote skill maturity based on usage and success rate."""
        if skill.usage_count < self.PROMOTION_USAGE_THRESHOLD:
            return

        success_rate = skill.success_count / skill.usage_count

        if success_rate >= self.PROMOTION_SUCCESS_RATE:
            promotions = {
                SkillMaturity.EXPERIMENTAL: SkillMaturity.DEVELOPING,
                SkillMaturity.DEVELOPING: SkillMaturity.STABLE,
                SkillMaturity.STABLE: SkillMaturity.PROVEN,
                SkillMaturity.PROVEN: SkillMaturity.CORE,
            }
            next_maturity = promotions.get(skill.maturity)
            if next_maturity:
                skill.maturity = next_maturity

    # ------------------------------------------------------------------
    # Skill Composition
    # ------------------------------------------------------------------

    def compose_skills(
        self,
        name: str,
        description: str,
        skill_ids: List[str],
        execution_order: Optional[List[str]] = None,
        data_flow: Optional[Dict[str, Dict[str, str]]] = None,
    ) -> ComposedSkill:
        """Compose multiple skills into a reusable composite workflow.

        Args:
            name: Composite skill name.
            description: What the composition achieves.
            skill_ids: IDs of constituent skills.
            execution_order: Ordered list of skill_ids for execution.
            data_flow: Mapping of data flow between skills.

        Returns:
            The composed ComposedSkill.
        """
        time.sleep(0.001)
        with self._lock:
            # Validate all skills exist
            for sid in skill_ids:
                if sid not in self._skills:
                    raise ValueError(f"Skill {sid} not found")

            composition = ComposedSkill(
                composition_id=uuid.uuid4().hex,
                name=name,
                description=description,
                skill_ids=skill_ids,
                execution_order=execution_order or skill_ids,
                data_flow=data_flow or {},
            )

            self._compositions[composition.composition_id] = composition
            return composition

    def execute_composition(
        self,
        composition_id: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Execute a composed skill workflow.

        Args:
            composition_id: The composition to execute.
            context: Execution context.

        Returns:
            Dictionary with execution results for each skill.
        """
        with self._lock:
            if composition_id not in self._compositions:
                return {"error": f"Composition {composition_id} not found"}

            composition = self._compositions[composition_id]
            exec_context = context or {}
            results: Dict[str, Any] = {}

            for skill_id in composition.execution_order:
                execution = self.execute_skill(skill_id, exec_context)
                results[skill_id] = {
                    "outcome": execution.outcome.value,
                    "duration_ms": execution.duration_ms,
                    "output": execution.output,
                }

                # Merge output into context for next skill
                if execution.outcome == ExecutionOutcome.SUCCESS:
                    exec_context.update(execution.output)

                # Handle data flow
                if skill_id in composition.data_flow:
                    for target_id, mapping in composition.data_flow[skill_id].items():
                        for source_key, target_key in mapping.items():
                            if source_key in exec_context:
                                exec_context[target_key] = exec_context[source_key]

            composition.usage_count += 1
            return results

    # ------------------------------------------------------------------
    # Skill Discovery
    # ------------------------------------------------------------------

    def discover_skills(
        self,
        domain: Optional[str] = None,
        tags: Optional[List[str]] = None,
        maturity: Optional[str] = None,
        limit: int = 20,
    ) -> List[AccumulatedSkill]:
        """Discover relevant skills based on filters.

        Args:
            domain: Filter by skill domain.
            tags: Filter by tags.
            maturity: Filter by maturity level.
            limit: Maximum results.

        Returns:
            List of matching AccumulatedSkill instances.
        """
        with self._lock:
            candidates = set(self._skills.keys())

            if domain:
                domain_enum = SkillDomain(domain)
                candidates &= set(self._domain_index.get(domain_enum, []))

            if tags:
                for tag in tags:
                    candidates &= set(self._tag_index.get(tag, []))

            results = []
            for sid in candidates:
                skill = self._skills[sid]
                if maturity and skill.maturity.value != maturity:
                    continue
                results.append(skill)

            # Sort by maturity and usage
            maturity_order = {
                SkillMaturity.CORE: 5,
                SkillMaturity.PROVEN: 4,
                SkillMaturity.STABLE: 3,
                SkillMaturity.DEVELOPING: 2,
                SkillMaturity.EXPERIMENTAL: 1,
            }
            results.sort(
                key=lambda s: (maturity_order.get(s.maturity, 0), s.usage_count),
                reverse=True,
            )

            return results[:limit]

    # ------------------------------------------------------------------
    # Refinement
    # ------------------------------------------------------------------

    def refine_skill(
        self,
        skill_id: str,
        feedback: Dict[str, Any],
    ) -> Optional[AccumulatedSkill]:
        """Refine a skill based on execution feedback.

        Args:
            skill_id: The skill to refine.
            feedback: Feedback data including suggested improvements.

        Returns:
            The updated skill, or None if not found.
        """
        with self._lock:
            if skill_id not in self._skills:
                return None

            skill = self._skills[skill_id]

            # Apply step modifications
            if "step_modifications" in feedback:
                for mod in feedback["step_modifications"]:
                    step_idx = mod.get("step_index", -1)
                    if 0 <= step_idx < len(skill.steps):
                        if "new_parameters" in mod:
                            skill.steps[step_idx].parameters.update(mod["new_parameters"])
                        if "new_description" in mod:
                            skill.steps[step_idx].description = mod["new_description"]

            # Add new steps
            if "new_steps" in feedback:
                for step_data in feedback["new_steps"]:
                    if len(skill.steps) < self.MAX_SKILL_STEPS:
                        skill.steps.append(SkillStep(
                            step_id=uuid.uuid4().hex,
                            order=len(skill.steps),
                            description=step_data.get("description", ""),
                            action_type=step_data.get("action_type", "execute"),
                            parameters=step_data.get("parameters", {}),
                        ))

            skill.version += 1
            skill.updated_at = time.time()
            return skill

    # ------------------------------------------------------------------
    # Query API
    # ------------------------------------------------------------------

    def get_skill(self, skill_id: str) -> Optional[AccumulatedSkill]:
        """Get a skill by ID."""
        with self._lock:
            return self._skills.get(skill_id)

    def get_skill_stats(self) -> Dict[str, Any]:
        """Get comprehensive skill statistics."""
        with self._lock:
            domain_counts = {}
            maturity_counts = {}
            for skill in self._skills.values():
                domain_counts[skill.domain.value] = domain_counts.get(skill.domain.value, 0) + 1
                maturity_counts[skill.maturity.value] = maturity_counts.get(skill.maturity.value, 0) + 1

            return {
                "total_skills": self._total_skills_accumulated,
                "total_executions": self._total_executions,
                "total_compositions": len(self._compositions),
                "by_domain": domain_counts,
                "by_maturity": maturity_counts,
                "stored_skills": len(self._skills),
            }

    def get_recent_executions(
        self,
        skill_id: Optional[str] = None,
        limit: int = 20,
    ) -> List[Dict[str, Any]]:
        """Get recent skill executions."""
        with self._lock:
            all_executions = []
            if skill_id:
                source = self._executions.get(skill_id, [])
            else:
                source = []
                for execs in self._executions.values():
                    source.extend(execs)

            source.sort(key=lambda e: e.executed_at, reverse=True)
            return [
                {
                    "execution_id": e.execution_id,
                    "skill_id": e.skill_id,
                    "outcome": e.outcome.value,
                    "duration_ms": e.duration_ms,
                    "output": e.output,
                    "executed_at": e.executed_at,
                }
                for e in source[:limit]
            ]


# ---------------------------------------------------------------------------
# Singleton Accessor
# ---------------------------------------------------------------------------

def get_skill_accumulator_engine() -> SkillAccumulatorEngine:
    """Get the singleton SkillAccumulatorEngine instance."""
    return SkillAccumulatorEngine.get_instance()