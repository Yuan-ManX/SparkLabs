"""
SparkLabs Agent - Learning Loop Engine

Self-improving learning loop that creates skills from experience, refines
them through usage, and persists knowledge across sessions. The engine
maintains a continuous cycle of observation, pattern extraction, skill
creation, and self-evaluation.

Architecture:
  AgentLearningLoop (Singleton)
    |-- Experience Buffer (recent execution traces)
    |-- Pattern Extractor (identify recurring success/failure patterns)
    |-- Skill Factory (create skills from learned patterns)
    |-- Skill Refinery (improve existing skills based on usage)
    |-- Self Evaluator (periodic performance assessment)
    |-- Nudge Engine (trigger self-improvement cycles)
    |-- Knowledge Compactor (consolidate and prune knowledge)
"""

from __future__ import annotations

import hashlib
import threading
import time as _time_module
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple


class ExperienceType(Enum):
    SUCCESS = "success"
    FAILURE = "failure"
    RECOVERY = "recovery"
    DISCOVERY = "discovery"
    OPTIMIZATION = "optimization"


class PatternCategory(Enum):
    WORKFLOW = "workflow"
    CODING = "coding"
    DEBUGGING = "debugging"
    DESIGN = "design"
    COMMUNICATION = "communication"
    OPTIMIZATION = "optimization"
    GAME_LOGIC = "game_logic"
    LEVEL_DESIGN = "level_design"


class LearningPhase(Enum):
    OBSERVING = "observing"
    EXTRACTING = "extracting"
    CREATING = "creating"
    REFINING = "refining"
    EVALUATING = "evaluating"
    IDLE = "idle"


@dataclass
class ExperienceRecord:
    """Single execution trace entry."""
    experience_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    experience_type: ExperienceType = ExperienceType.SUCCESS
    category: PatternCategory = PatternCategory.WORKFLOW
    context: str = ""
    action_taken: str = ""
    outcome: str = ""
    metrics: Dict[str, float] = field(default_factory=dict)
    timestamp: float = field(default_factory=_time_module.time)
    related_skills: List[str] = field(default_factory=list)
    session_id: str = ""
    iteration_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "experience_id": self.experience_id,
            "experience_type": self.experience_type.value,
            "category": self.category.value,
            "context": self.context,
            "action_taken": self.action_taken,
            "outcome": self.outcome,
            "metrics": self.metrics,
            "timestamp": self.timestamp,
            "related_skills": self.related_skills,
            "session_id": self.session_id,
            "iteration_count": self.iteration_count,
        }


@dataclass
class LearnedPattern:
    """Recurring pattern extracted from experiences."""
    pattern_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    pattern_name: str = ""
    pattern_category: PatternCategory = PatternCategory.WORKFLOW
    description: str = ""
    trigger_conditions: List[str] = field(default_factory=list)
    action_sequence: List[str] = field(default_factory=list)
    success_rate: float = 0.0
    occurrence_count: int = 0
    last_seen: float = field(default_factory=_time_module.time)
    derived_skill_id: str = ""
    confidence: float = 0.0
    source_experiences: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "pattern_id": self.pattern_id,
            "pattern_name": self.pattern_name,
            "pattern_category": self.pattern_category.value,
            "description": self.description,
            "trigger_conditions": self.trigger_conditions,
            "action_sequence": self.action_sequence,
            "success_rate": self.success_rate,
            "occurrence_count": self.occurrence_count,
            "last_seen": self.last_seen,
            "derived_skill_id": self.derived_skill_id,
            "confidence": self.confidence,
            "source_experiences": self.source_experiences,
        }


@dataclass
class LearningReport:
    """Periodic self-evaluation report."""
    report_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    timestamp: float = field(default_factory=_time_module.time)
    total_experiences: int = 0
    total_patterns: int = 0
    total_skills_created: int = 0
    total_skills_refined: int = 0
    average_success_rate: float = 0.0
    improvement_areas: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)
    phase: LearningPhase = LearningPhase.IDLE

    def to_dict(self) -> Dict[str, Any]:
        return {
            "report_id": self.report_id,
            "timestamp": self.timestamp,
            "total_experiences": self.total_experiences,
            "total_patterns": self.total_patterns,
            "total_skills_created": self.total_skills_created,
            "total_skills_refined": self.total_skills_refined,
            "average_success_rate": self.average_success_rate,
            "improvement_areas": self.improvement_areas,
            "recommendations": self.recommendations,
            "phase": self.phase.value,
        }


class AgentLearningLoop:
    """
    Self-improving learning loop engine.

    Continuously observes agent execution, extracts patterns from
    successes and failures, creates new skills, and refines existing
    skills based on usage data. Periodically evaluates overall
    performance and generates improvement recommendations.
    """

    _instance = None
    _lock = threading.RLock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if hasattr(self, "_initialized") and self._initialized:
            return
        self._initialized = True
        self._experiences: Dict[str, ExperienceRecord] = {}
        self._patterns: Dict[str, LearnedPattern] = {}
        self._reports: List[LearningReport] = []
        self._phase: LearningPhase = LearningPhase.OBSERVING
        self._total_skills_created: int = 0
        self._total_skills_refined: int = 0
        self._nudge_interval: float = 300.0  # 5 minutes
        self._last_nudge_time: float = _time_module.time()
        self._pattern_threshold: int = 3  # min experiences to form a pattern
        self._confidence_threshold: float = 0.6
        self._on_skill_created: Optional[Callable] = None
        self._on_skill_refined: Optional[Callable] = None
        self._on_pattern_detected: Optional[Callable] = None

    @classmethod
    def get_instance(cls) -> "AgentLearningLoop":
        return cls()

    # ---- Experience Recording ----

    def record_experience(
        self,
        experience_type: ExperienceType,
        category: PatternCategory,
        context: str,
        action_taken: str,
        outcome: str,
        metrics: Optional[Dict[str, float]] = None,
        session_id: str = "",
        iteration_count: int = 0,
    ) -> ExperienceRecord:
        """Record an execution experience for learning."""
        with self._lock:
            exp = ExperienceRecord(
                experience_type=experience_type,
                category=category,
                context=context,
                action_taken=action_taken,
                outcome=outcome,
                metrics=metrics or {},
                session_id=session_id,
                iteration_count=iteration_count,
            )
            self._experiences[exp.experience_id] = exp
            self._maybe_trigger_nudge()
            return exp

    def record_success(
        self,
        category: PatternCategory,
        context: str,
        action: str,
        outcome: str,
        **kwargs,
    ) -> ExperienceRecord:
        """Convenience method to record a success."""
        return self.record_experience(
            ExperienceType.SUCCESS, category, context, action, outcome, **kwargs,
        )

    def record_failure(
        self,
        category: PatternCategory,
        context: str,
        action: str,
        outcome: str,
        **kwargs,
    ) -> ExperienceRecord:
        """Convenience method to record a failure."""
        return self.record_experience(
            ExperienceType.FAILURE, category, context, action, outcome, **kwargs,
        )

    def record_discovery(
        self,
        category: PatternCategory,
        context: str,
        action: str,
        outcome: str,
        **kwargs,
    ) -> ExperienceRecord:
        """Convenience method to record a discovery."""
        return self.record_experience(
            ExperienceType.DISCOVERY, category, context, action, outcome, **kwargs,
        )

    # ---- Pattern Extraction ----

    def extract_patterns(self, category: Optional[PatternCategory] = None) -> List[LearnedPattern]:
        """
        Extract recurring patterns from the experience buffer.

        Groups experiences by category and context similarity, identifies
        recurring action sequences, and creates learned patterns when
        occurrence thresholds are met.
        """
        with self._lock:
            self._phase = LearningPhase.EXTRACTING
            new_patterns: List[LearnedPattern] = []

            experiences = list(self._experiences.values())
            if category is not None:
                experiences = [e for e in experiences if e.category == category]

            # Group by category and context hash
            groups: Dict[str, List[ExperienceRecord]] = {}
            for exp in experiences:
                key = f"{exp.category.value}:{_hash_context(exp.context)}"
                if key not in groups:
                    groups[key] = []
                groups[key].append(exp)

            for key, group in groups.items():
                if len(group) < self._pattern_threshold:
                    continue

                cat = group[0].category
                successes = sum(1 for e in group if e.experience_type == ExperienceType.SUCCESS)
                success_rate = successes / len(group) if group else 0.0

                if success_rate < self._confidence_threshold:
                    continue

                # Extract common action steps
                actions = list(set(e.action_taken for e in group if e.action_taken))
                triggers = list(set(e.context for e in group if e.context))

                pattern = LearnedPattern(
                    pattern_name=f"auto_pattern_{cat.value}_{len(self._patterns)}",
                    pattern_category=cat,
                    description=f"Auto-extracted pattern from {len(group)} experiences",
                    trigger_conditions=triggers[:5],
                    action_sequence=actions[:10],
                    success_rate=success_rate,
                    occurrence_count=len(group),
                    confidence=success_rate,
                    source_experiences=[e.experience_id for e in group],
                )
                self._patterns[pattern.pattern_id] = pattern
                new_patterns.append(pattern)

                if self._on_pattern_detected:
                    self._on_pattern_detected(pattern)

            self._phase = LearningPhase.IDLE
            return new_patterns

    # ---- Skill Creation ----

    def create_skill_from_pattern(
        self,
        pattern_id: str,
        skill_name: str,
        skill_description: str = "",
    ) -> Optional[LearnedPattern]:
        """
        Convert a learned pattern into a concrete skill.

        The pattern is marked as having a derived skill, enabling
        the skill system to reference it during execution.
        """
        with self._lock:
            self._phase = LearningPhase.CREATING
            pattern = self._patterns.get(pattern_id)
            if pattern is None:
                self._phase = LearningPhase.IDLE
                return None

            pattern.derived_skill_id = uuid.uuid4().hex
            pattern.pattern_name = skill_name
            if skill_description:
                pattern.description = skill_description

            self._total_skills_created += 1

            if self._on_skill_created:
                self._on_skill_created(pattern)

            self._phase = LearningPhase.IDLE
            return pattern

    # ---- Skill Refinement ----

    def refine_skill(
        self,
        skill_id: str,
        new_action_sequence: Optional[List[str]] = None,
        new_trigger_conditions: Optional[List[str]] = None,
        updated_success_rate: Optional[float] = None,
    ) -> Optional[LearnedPattern]:
        """Refine an existing skill with new information."""
        with self._lock:
            self._phase = LearningPhase.REFINING
            for pattern in self._patterns.values():
                if pattern.derived_skill_id == skill_id:
                    if new_action_sequence:
                        pattern.action_sequence = new_action_sequence
                    if new_trigger_conditions:
                        pattern.trigger_conditions = new_trigger_conditions
                    if updated_success_rate is not None:
                        pattern.success_rate = updated_success_rate
                    pattern.occurrence_count += 1
                    pattern.last_seen = _time_module.time()
                    self._total_skills_refined += 1

                    if self._on_skill_refined:
                        self._on_skill_refined(pattern)

                    self._phase = LearningPhase.IDLE
                    return pattern
            self._phase = LearningPhase.IDLE
            return None

    # ---- Self Evaluation ----

    def evaluate(self) -> LearningReport:
        """Generate a periodic self-evaluation report."""
        with self._lock:
            self._phase = LearningPhase.EVALUATING
            success_count = sum(
                1 for e in self._experiences.values()
                if e.experience_type == ExperienceType.SUCCESS
            )
            total = len(self._experiences)
            avg_success = success_count / total if total > 0 else 0.0

            improvement_areas = []
            recommendations = []

            # Identify underperforming categories
            for cat in PatternCategory:
                cat_exps = [e for e in self._experiences.values() if e.category == cat]
                if not cat_exps:
                    continue
                cat_failures = sum(
                    1 for e in cat_exps if e.experience_type == ExperienceType.FAILURE
                )
                cat_rate = 1.0 - (cat_failures / len(cat_exps))
                if cat_rate < 0.5:
                    improvement_areas.append(cat.value)
                    recommendations.append(
                        f"Focus learning on {cat.value} patterns - current success rate {cat_rate:.0%}"
                    )

            if not self._patterns:
                recommendations.append(
                    "No patterns extracted yet. Continue recording experiences to build knowledge."
                )

            report = LearningReport(
                total_experiences=total,
                total_patterns=len(self._patterns),
                total_skills_created=self._total_skills_created,
                total_skills_refined=self._total_skills_refined,
                average_success_rate=avg_success,
                improvement_areas=improvement_areas,
                recommendations=recommendations,
                phase=self._phase,
            )
            self._reports.append(report)
            self._phase = LearningPhase.IDLE
            return report

    # ---- Nudge Engine ----

    def nudge(self) -> Optional[LearningReport]:
        """
        Trigger a self-improvement cycle.

        Extracts patterns, creates skills from high-confidence patterns,
        refines existing skills, and generates an evaluation report.
        """
        with self._lock:
            self.extract_patterns()
            for pattern in list(self._patterns.values()):
                if (
                    pattern.confidence >= self._confidence_threshold
                    and not pattern.derived_skill_id
                ):
                    self.create_skill_from_pattern(
                        pattern.pattern_id,
                        f"learned_{pattern.pattern_category.value}",
                    )
            self._last_nudge_time = _time_module.time()
            return self.evaluate()

    def _maybe_trigger_nudge(self):
        """Auto-trigger nudge if interval has elapsed."""
        if _time_module.time() - self._last_nudge_time >= self._nudge_interval:
            self.nudge()

    # ---- Query Methods ----

    def get_experiences(
        self,
        experience_type: Optional[ExperienceType] = None,
        category: Optional[PatternCategory] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """Query experiences with optional filtering."""
        with self._lock:
            results = list(self._experiences.values())
            if experience_type is not None:
                results = [e for e in results if e.experience_type == experience_type]
            if category is not None:
                results = [e for e in results if e.category == category]
            results.sort(key=lambda e: e.timestamp, reverse=True)
            return [e.to_dict() for e in results[:limit]]

    def get_patterns(
        self,
        category: Optional[PatternCategory] = None,
        min_confidence: float = 0.0,
    ) -> List[Dict[str, Any]]:
        """Query learned patterns with optional filtering."""
        with self._lock:
            results = list(self._patterns.values())
            if category is not None:
                results = [p for p in results if p.pattern_category == category]
            if min_confidence > 0.0:
                results = [p for p in results if p.confidence >= min_confidence]
            results.sort(key=lambda p: p.confidence, reverse=True)
            return [p.to_dict() for p in results]

    def get_stats(self) -> Dict[str, Any]:
        """Get learning loop statistics."""
        with self._lock:
            return {
                "total_experiences": len(self._experiences),
                "total_patterns": len(self._patterns),
                "total_skills_created": self._total_skills_created,
                "total_skills_refined": self._total_skills_refined,
                "current_phase": self._phase.value,
                "last_nudge_time": self._last_nudge_time,
                "nudge_interval": self._nudge_interval,
                "pattern_threshold": self._pattern_threshold,
                "confidence_threshold": self._confidence_threshold,
                "recent_reports": len(self._reports),
            }

    def set_callback(
        self,
        on_skill_created: Optional[Callable] = None,
        on_skill_refined: Optional[Callable] = None,
        on_pattern_detected: Optional[Callable] = None,
    ) -> None:
        """Register callbacks for learning events."""
        self._on_skill_created = on_skill_created
        self._on_skill_refined = on_skill_refined
        self._on_pattern_detected = on_pattern_detected


def _hash_context(context: str) -> str:
    """Generate a similarity hash for context grouping."""
    if not context:
        return "empty"
    normalized = " ".join(context.lower().split()[:20])
    return hashlib.md5(normalized.encode()).hexdigest()[:12]


# Module-level accessor
_learning_loop: Optional[AgentLearningLoop] = None


def get_learning_loop() -> AgentLearningLoop:
    global _learning_loop
    if _learning_loop is None:
        _learning_loop = AgentLearningLoop()
    return _learning_loop