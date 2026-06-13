"""
SparkLabs Agent - Experience Evolution System

A closed-loop self-improvement system that enables agents to autonomously
extract reusable skills and knowledge from their operational experiences.
Implements a continuous cycle of experience capture, pattern recognition,
skill crystallization, and background self-review — creating agents that
become more capable with every interaction.

Architecture:
  AgentExperienceEvolution (Singleton)
    |-- ExperienceCapture (records agent interactions and outcomes)
    |-- PatternRecognizer (identifies recurring successful patterns)
    |-- SkillCrystallizer (converts patterns into reusable skills)
    |-- BackgroundReviewer (periodic self-review for improvement nudges)
    |-- EvolutionMetrics (tracks learning progress and effectiveness)
    |-- EvolutionEvent (immutable evolution activity records)

Evolution Cycle:
  CAPTURE -> ANALYZE -> CRYSTALLIZE -> VALIDATE -> DEPLOY -> REVIEW

Self-Review Triggers:
  - User turn threshold (every N interactions)
  - Tool iteration threshold (every M tool calls)
  - Session boundary (session start/end)
  - Error threshold (after N consecutive errors)

Usage:
    evolver = get_agent_experience_evolution()
    evolver.start_background_review()
    evolver.capture_experience(trajectory)
    skills = evolver.extract_skills(context)
    evolver.shutdown()
"""

from __future__ import annotations

import json
import random
import threading
import time as _time_module
import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class EvolutionPhase(Enum):
    """Phases of the experience evolution cycle."""
    CAPTURE = "capture"
    ANALYZE = "analyze"
    CRYSTALLIZE = "crystallize"
    VALIDATE = "validate"
    DEPLOY = "deploy"
    REVIEW = "review"


class ExperienceType(Enum):
    """Categories of captured experiences."""
    SUCCESSFUL_COMPLETION = "successful_completion"
    ERROR_RECOVERY = "error_recovery"
    USER_CORRECTION = "user_correction"
    CREATIVE_DISCOVERY = "creative_discovery"
    PATTERN_REPETITION = "pattern_repetition"
    NOVEL_SOLUTION = "novel_solution"


class SkillConfidence(Enum):
    """Confidence levels for crystallized skills."""
    EXPERIMENTAL = "experimental"
    PROVEN = "proven"
    RELIABLE = "reliable"
    DEPRECATED = "deprecated"


class ReviewTrigger(Enum):
    """Triggers that initiate background self-review."""
    USER_TURN_THRESHOLD = "user_turn_threshold"
    TOOL_ITERATION_THRESHOLD = "tool_iteration_threshold"
    SESSION_START = "session_start"
    SESSION_END = "session_end"
    ERROR_THRESHOLD = "error_threshold"
    MANUAL = "manual"


class EvolutionStatus(Enum):
    """Runtime status of the evolution system."""
    IDLE = "idle"
    CAPTURING = "capturing"
    ANALYZING = "analyzing"
    CRYSTALLIZING = "crystallizing"
    REVIEWING = "reviewing"
    SHUTDOWN = "shutdown"


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------

@dataclass
class CapturedExperience:
    """A single recorded agent experience with full context."""
    experience_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    experience_type: ExperienceType = ExperienceType.SUCCESSFUL_COMPLETION
    timestamp: float = field(default_factory=_time_module.time)
    session_id: str = ""
    task_description: str = ""
    user_input: str = ""
    agent_response: str = ""
    tool_calls_made: List[str] = field(default_factory=list)
    tool_results: List[Dict[str, Any]] = field(default_factory=list)
    outcome: str = ""
    success_score: float = 0.0
    user_feedback: str = ""
    error_details: str = ""
    correction_applied: str = ""
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "experience_id": self.experience_id,
            "experience_type": self.experience_type.value,
            "timestamp": self.timestamp,
            "session_id": self.session_id,
            "task_description": self.task_description,
            "user_input": self.user_input[:200],
            "tool_calls_made": self.tool_calls_made,
            "outcome": self.outcome[:200],
            "success_score": round(self.success_score, 4),
            "tags": self.tags,
        }


@dataclass
class RecognizedPattern:
    """A pattern identified from accumulated experiences."""
    pattern_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    pattern_name: str = ""
    pattern_description: str = ""
    source_experiences: List[str] = field(default_factory=list)
    frequency: int = 0
    average_success_rate: float = 0.0
    applicable_contexts: List[str] = field(default_factory=list)
    key_conditions: List[str] = field(default_factory=list)
    confidence: float = 0.0
    discovered_at: float = field(default_factory=_time_module.time)
    last_observed_at: float = field(default_factory=_time_module.time)
    status: EvolutionStatus = EvolutionStatus.IDLE

    def to_dict(self) -> Dict[str, Any]:
        return {
            "pattern_id": self.pattern_id,
            "pattern_name": self.pattern_name,
            "pattern_description": self.pattern_description,
            "frequency": self.frequency,
            "average_success_rate": round(self.average_success_rate, 4),
            "applicable_contexts": self.applicable_contexts,
            "confidence": round(self.confidence, 4),
            "discovered_at": self.discovered_at,
        }


@dataclass
class CrystallizedSkill:
    """A reusable skill crystallized from recognized patterns."""
    skill_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    skill_name: str = ""
    skill_description: str = ""
    source_pattern_id: str = ""
    trigger_conditions: List[str] = field(default_factory=list)
    required_tools: List[str] = field(default_factory=list)
    execution_steps: List[Dict[str, Any]] = field(default_factory=list)
    expected_outcome: str = ""
    confidence: SkillConfidence = SkillConfidence.EXPERIMENTAL
    usage_count: int = 0
    success_count: int = 0
    failure_count: int = 0
    created_at: float = field(default_factory=_time_module.time)
    last_used_at: float = field(default_factory=_time_module.time)
    evolution_history: List[Dict[str, Any]] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    version: int = 1

    def to_dict(self) -> Dict[str, Any]:
        return {
            "skill_id": self.skill_id,
            "skill_name": self.skill_name,
            "skill_description": self.skill_description,
            "trigger_conditions": self.trigger_conditions,
            "required_tools": self.required_tools,
            "confidence": self.confidence.value,
            "usage_count": self.usage_count,
            "success_count": self.success_count,
            "failure_count": self.failure_count,
            "success_rate": round(self.success_count / max(1, self.usage_count), 4),
            "version": self.version,
            "tags": self.tags,
        }


@dataclass
class EvolutionEvent:
    """Immutable record of an evolution activity."""
    event_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    phase: EvolutionPhase = EvolutionPhase.CAPTURE
    timestamp: float = field(default_factory=_time_module.time)
    experience_id: str = ""
    pattern_id: str = ""
    skill_id: str = ""
    description: str = ""
    trigger: ReviewTrigger = ReviewTrigger.MANUAL
    duration_ms: float = 0.0
    result: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": self.event_id,
            "phase": self.phase.value,
            "timestamp": self.timestamp,
            "description": self.description,
            "trigger": self.trigger.value,
            "duration_ms": round(self.duration_ms, 2),
            "result": self.result,
        }


@dataclass
class EvolutionMetrics:
    """Aggregated metrics tracking evolution system performance."""
    total_experiences: int = 0
    total_patterns: int = 0
    total_skills: int = 0
    total_reviews: int = 0
    average_success_rate: float = 0.0
    skill_adoption_rate: float = 0.0
    pattern_accuracy: float = 0.0
    review_effectiveness: float = 0.0
    last_review_time: Optional[float] = None
    last_crystallization_time: Optional[float] = None
    evolution_phase_counts: Dict[str, int] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_experiences": self.total_experiences,
            "total_patterns": self.total_patterns,
            "total_skills": self.total_skills,
            "total_reviews": self.total_reviews,
            "average_success_rate": round(self.average_success_rate, 4),
            "skill_adoption_rate": round(self.skill_adoption_rate, 4),
            "pattern_accuracy": round(self.pattern_accuracy, 4),
            "review_effectiveness": round(self.review_effectiveness, 4),
            "last_review_time": self.last_review_time,
            "last_crystallization_time": self.last_crystallization_time,
        }


# ---------------------------------------------------------------------------
# Agent Experience Evolution - Singleton
# ---------------------------------------------------------------------------

class AgentExperienceEvolution:
    """Central evolution engine for autonomous agent self-improvement.

    Implements a continuous closed-loop learning system where agent
    experiences are captured, analyzed for patterns, crystallized into
    reusable skills, and deployed back to the agent for future use.
    Background self-review periodically evaluates performance and
    suggests improvements without blocking agent operations.
    """

    _instance = None
    _lock = threading.RLock()
    _initialized = False

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._experiences: Dict[str, CapturedExperience] = {}
        self._patterns: Dict[str, RecognizedPattern] = {}
        self._skills: Dict[str, CrystallizedSkill] = {}
        self._events: List[EvolutionEvent] = []
        self._event_handlers: Dict[EvolutionPhase, List[Callable]] = defaultdict(list)
        self._status: EvolutionStatus = EvolutionStatus.IDLE
        self._metrics: EvolutionMetrics = EvolutionMetrics()
        self._background_thread: Optional[threading.Thread] = None
        self._shutdown_flag = threading.Event()
        self._review_config: Dict[str, int] = {
            "user_turn_interval": 10,
            "tool_iteration_interval": 10,
            "error_threshold": 5,
            "background_review_interval_seconds": 300,
        }
        self._user_turns = 0
        self._tool_iterations = 0
        self._consecutive_errors = 0
        self._callback: Optional[Callable] = None
        self._initialized = True

    # ---- Experience Capture ----

    def capture_experience(
        self,
        experience_type: ExperienceType,
        task_description: str = "",
        user_input: str = "",
        agent_response: str = "",
        tool_calls_made: Optional[List[str]] = None,
        tool_results: Optional[List[Dict[str, Any]]] = None,
        outcome: str = "",
        success_score: float = 0.5,
        user_feedback: str = "",
        error_details: str = "",
        tags: Optional[List[str]] = None,
        session_id: str = "",
    ) -> CapturedExperience:
        """Record a new agent experience for future analysis.
        
        Args:
            experience_type: Category of this experience.
            task_description: Human-readable task description.
            user_input: The user's original input.
            agent_response: The agent's final response.
            tool_calls_made: List of tool names called.
            tool_results: Results from tool executions.
            outcome: Description of the final outcome.
            success_score: 0.0 to 1.0 success rating.
            user_feedback: Any explicit user feedback.
            error_details: Error information if applicable.
            tags: Categorization tags.
            session_id: Associated session identifier.
        
        Returns:
            The captured experience object.
        """
        with self._lock:
            exp = CapturedExperience(
                experience_type=experience_type,
                task_description=task_description,
                user_input=user_input,
                agent_response=agent_response,
                tool_calls_made=tool_calls_made or [],
                tool_results=tool_results or [],
                outcome=outcome,
                success_score=success_score,
                user_feedback=user_feedback,
                error_details=error_details,
                tags=tags or [],
                session_id=session_id,
            )
            self._experiences[exp.experience_id] = exp
            self._metrics.total_experiences += 1

            if success_score < 0.3:
                self._consecutive_errors += 1
            else:
                self._consecutive_errors = 0

            event = EvolutionEvent(
                phase=EvolutionPhase.CAPTURE,
                experience_id=exp.experience_id,
                description=f"Captured {experience_type.value} experience: {task_description[:100]}",
                trigger=ReviewTrigger.MANUAL,
            )
            self._events.append(event)
            self._emit_event(EvolutionPhase.CAPTURE, event)

            self._user_turns += 1
            self._check_review_triggers()

            return exp

    def capture_tool_execution(
        self,
        tool_name: str,
        tool_input: Dict[str, Any],
        tool_result: Any,
        success: bool,
    ) -> None:
        """Capture a single tool execution for iteration tracking.
        
        Args:
            tool_name: Name of the executed tool.
            tool_input: Input parameters to the tool.
            tool_result: Result from tool execution.
            success: Whether execution succeeded.
        """
        with self._lock:
            self._tool_iterations += 1
            if not success:
                self._consecutive_errors += 1
            self._check_review_triggers()

    # ---- Pattern Recognition ----

    def analyze_experiences(
        self,
        context_filter: Optional[List[str]] = None,
        min_frequency: int = 3,
    ) -> List[RecognizedPattern]:
        """Analyze captured experiences to identify recurring patterns.
        
        Args:
            context_filter: Optional list of contexts to filter by.
            min_frequency: Minimum occurrences for pattern recognition.
        
        Returns:
            List of recognized patterns.
        """
        with self._lock:
            self._status = EvolutionStatus.ANALYZING
            start_time = _time_module.time()

            # Cluster experiences by task similarity and outcome patterns
            clusters: Dict[str, List[CapturedExperience]] = defaultdict(list)
            for exp in self._experiences.values():
                key_parts = []
                if exp.experience_type.value:
                    key_parts.append(exp.experience_type.value)
                if exp.tags:
                    key_parts.extend(sorted(exp.tags[:3]))
                key = "|".join(key_parts) if key_parts else "general"
                clusters[key].append(exp)

            new_patterns = []
            for cluster_key, experiences in clusters.items():
                if len(experiences) < min_frequency:
                    continue

                success_scores = [e.success_score for e in experiences]
                avg_success = sum(success_scores) / len(success_scores)

                pattern = RecognizedPattern(
                    pattern_name=f"Pattern_{cluster_key[:40]}",
                    pattern_description=f"Recurring {experiences[0].experience_type.value} pattern with {len(experiences)} occurrences",
                    source_experiences=[e.experience_id for e in experiences],
                    frequency=len(experiences),
                    average_success_rate=avg_success,
                    applicable_contexts=list(set(
                        tag for e in experiences for tag in e.tags
                    )),
                    confidence=min(1.0, avg_success * (len(experiences) / min_frequency)),
                )
                self._patterns[pattern.pattern_id] = pattern
                new_patterns.append(pattern)
                self._metrics.total_patterns += 1

            self._status = EvolutionStatus.IDLE
            duration = (_time_module.time() - start_time) * 1000
            event = EvolutionEvent(
                phase=EvolutionPhase.ANALYZE,
                description=f"Analyzed {len(self._experiences)} experiences, found {len(new_patterns)} patterns",
                duration_ms=duration,
                result=f"patterns_found={len(new_patterns)}",
            )
            self._events.append(event)
            self._emit_event(EvolutionPhase.ANALYZE, event)

            return new_patterns

    # ---- Skill Crystallization ----

    def crystallize_skills(
        self,
        min_confidence: float = 0.6,
        max_skills: int = 10,
    ) -> List[CrystallizedSkill]:
        """Convert recognized patterns into reusable skills.
        
        Args:
            min_confidence: Minimum pattern confidence to crystallize.
            max_skills: Maximum number of skills to create.
        
        Returns:
            List of newly crystallized skills.
        """
        with self._lock:
            self._status = EvolutionStatus.CRYSTALLIZING
            start_time = _time_module.time()

            qualified_patterns = sorted(
                [
                    p for p in self._patterns.values()
                    if p.confidence >= min_confidence
                ],
                key=lambda p: p.confidence * p.frequency,
                reverse=True,
            )[:max_skills]

            new_skills = []
            for pattern in qualified_patterns:
                existing = [
                    s for s in self._skills.values()
                    if s.source_pattern_id == pattern.pattern_id
                ]
                if existing:
                    continue

                skill = CrystallizedSkill(
                    skill_name=pattern.pattern_name,
                    skill_description=pattern.pattern_description,
                    source_pattern_id=pattern.pattern_id,
                    trigger_conditions=pattern.key_conditions,
                    applicable_contexts=pattern.applicable_contexts,
                    confidence=(
                        SkillConfidence.RELIABLE if pattern.confidence > 0.85
                        else SkillConfidence.PROVEN if pattern.confidence > 0.7
                        else SkillConfidence.EXPERIMENTAL
                    ),
                )
                self._skills[skill.skill_id] = skill
                new_skills.append(skill)
                self._metrics.total_skills += 1

            self._status = EvolutionStatus.IDLE
            self._metrics.last_crystallization_time = _time_module.time()
            duration = (_time_module.time() - start_time) * 1000
            event = EvolutionEvent(
                phase=EvolutionPhase.CRYSTALLIZE,
                description=f"Crystallized {len(new_skills)} skills from {len(qualified_patterns)} patterns",
                duration_ms=duration,
                result=f"skills_created={len(new_skills)}",
            )
            self._events.append(event)
            self._emit_event(EvolutionPhase.CRYSTALLIZE, event)

            return new_skills

    # ---- Skill Retrieval & Management ----

    def get_skills_for_context(
        self,
        context_tags: List[str],
        min_confidence: SkillConfidence = SkillConfidence.EXPERIMENTAL,
        max_results: int = 5,
    ) -> List[CrystallizedSkill]:
        """Retrieve relevant skills for a given context.
        
        Args:
            context_tags: Tags describing the current context.
            min_confidence: Minimum confidence level for skills.
            max_results: Maximum number of skills to return.
        
        Returns:
            List of relevant skills sorted by relevance.
        """
        confidence_order = {
            SkillConfidence.RELIABLE: 3,
            SkillConfidence.PROVEN: 2,
            SkillConfidence.EXPERIMENTAL: 1,
            SkillConfidence.DEPRECATED: 0,
        }
        min_confidence_value = confidence_order.get(min_confidence, 0)

        scored = []
        for skill in self._skills.values():
            conf_val = confidence_order.get(skill.confidence, 0)
            if conf_val < min_confidence_value:
                continue

            context_overlap = len(
                set(context_tags) & set(skill.tags)
            ) if skill.tags else 0
            success_rate = (
                skill.success_count / max(1, skill.usage_count)
            )
            relevance = (
                context_overlap * 3 +
                success_rate * 2 +
                conf_val * 2
            )
            scored.append((relevance, skill))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [s for _, s in scored[:max_results]]

    def update_skill_usage(
        self,
        skill_id: str,
        success: bool,
    ) -> None:
        """Record a skill usage event for confidence tracking.
        
        Args:
            skill_id: ID of the skill that was used.
            success: Whether the skill execution succeeded.
        """
        with self._lock:
            skill = self._skills.get(skill_id)
            if not skill:
                return
            skill.usage_count += 1
            if success:
                skill.success_count += 1
            else:
                skill.failure_count += 1
            skill.last_used_at = _time_module.time()

            success_rate = skill.success_count / max(1, skill.usage_count)
            if success_rate > 0.9 and skill.usage_count > 10:
                skill.confidence = SkillConfidence.RELIABLE
            elif success_rate > 0.7 and skill.usage_count > 5:
                skill.confidence = SkillConfidence.PROVEN
            elif success_rate < 0.3 and skill.usage_count > 5:
                skill.confidence = SkillConfidence.DEPRECATED

    # ---- Background Self-Review ----

    def start_background_review(self) -> None:
        """Start the background self-review thread."""
        if self._background_thread is not None and self._background_thread.is_alive():
            return
        self._shutdown_flag.clear()
        self._background_thread = threading.Thread(
            target=self._background_review_loop,
            daemon=True,
            name="evolution-background-review",
        )
        self._background_thread.start()

    def _background_review_loop(self) -> None:
        """Background daemon loop for periodic self-review."""
        while not self._shutdown_flag.is_set():
            try:
                self._shutdown_flag.wait(
                    self._review_config["background_review_interval_seconds"]
                )
                if self._shutdown_flag.is_set():
                    break
                self._perform_review(ReviewTrigger.TOOL_ITERATION_THRESHOLD)
            except Exception:
                pass

    def _check_review_triggers(self) -> None:
        """Check if any review triggers have been met."""
        triggers = []

        if self._user_turns >= self._review_config["user_turn_interval"]:
            triggers.append(ReviewTrigger.USER_TURN_THRESHOLD)
            self._user_turns = 0

        if self._tool_iterations >= self._review_config["tool_iteration_interval"]:
            triggers.append(ReviewTrigger.TOOL_ITERATION_THRESHOLD)
            self._tool_iterations = 0

        if self._consecutive_errors >= self._review_config["error_threshold"]:
            triggers.append(ReviewTrigger.ERROR_THRESHOLD)
            self._consecutive_errors = 0

        for trigger in triggers:
            self._perform_review(trigger)

    def _perform_review(self, trigger: ReviewTrigger) -> Dict[str, Any]:
        """Execute a self-review cycle.
        
        Args:
            trigger: What triggered this review.
        
        Returns:
            Review results with recommendations.
        """
        with self._lock:
            self._status = EvolutionStatus.REVIEWING
            start_time = _time_module.time()

            patterns = self.analyze_experiences(min_frequency=2)
            skills = self.crystallize_skills(min_confidence=0.5, max_skills=5)

            review_summary = {
                "trigger": trigger.value,
                "timestamp": _time_module.time(),
                "experiences_analyzed": len(self._experiences),
                "patterns_discovered": len(patterns),
                "skills_crystallized": len(skills),
                "active_skills": sum(
                    1 for s in self._skills.values()
                    if s.confidence != SkillConfidence.DEPRECATED
                ),
                "deprecated_skills": sum(
                    1 for s in self._skills.values()
                    if s.confidence == SkillConfidence.DEPRECATED
                ),
                "skill_adoption_rate": round(
                    sum(s.usage_count for s in self._skills.values()) /
                    max(1, self._metrics.total_experiences), 4
                ),
                "recommendations": self._generate_recommendations(patterns),
            }

            self._metrics.total_reviews += 1
            self._metrics.last_review_time = _time_module.time()
            self._status = EvolutionStatus.IDLE

            duration = (_time_module.time() - start_time) * 1000
            event = EvolutionEvent(
                phase=EvolutionPhase.REVIEW,
                trigger=trigger,
                description=f"Self-review: {len(patterns)} patterns, {len(skills)} skills",
                duration_ms=duration,
                result=json.dumps(review_summary, default=str),
            )
            self._events.append(event)
            self._emit_event(EvolutionPhase.REVIEW, event)

            if self._callback:
                try:
                    self._callback(review_summary)
                except Exception:
                    pass

            return review_summary

    def _generate_recommendations(
        self,
        patterns: List[RecognizedPattern],
    ) -> List[str]:
        """Generate improvement recommendations from patterns.
        
        Args:
            patterns: Newly recognized patterns.
        
        Returns:
            List of recommendation strings.
        """
        recommendations = []

        for pattern in patterns:
            if pattern.average_success_rate > 0.8 and pattern.frequency >= 5:
                recommendations.append(
                    f"High-success pattern '{pattern.pattern_name}' with "
                    f"{pattern.frequency} occurrences — consider promoting to core workflow"
                )
            elif pattern.average_success_rate < 0.3 and pattern.frequency >= 3:
                recommendations.append(
                    f"Low-success pattern '{pattern.pattern_name}' detected — "
                    f"review and optimize approach"
                )

        error_count = sum(
            1 for e in self._experiences.values()
            if e.success_score < 0.3
        )
        if error_count > 10:
            recommendations.append(
                f"High error rate detected ({error_count} failures) — "
                f"consider increasing validation rigor"
            )

        return recommendations

    # ---- Event System ----

    def register_handler(
        self,
        phase: EvolutionPhase,
        handler: Callable[[EvolutionEvent], None],
    ) -> None:
        """Register a callback for evolution phase events.
        
        Args:
            phase: The evolution phase to listen for.
            handler: Callback receiving the EvolutionEvent.
        """
        self._event_handlers[phase].append(handler)

    def _emit_event(self, phase: EvolutionPhase, event: EvolutionEvent) -> None:
        """Emit an event to all registered handlers for the phase.
        
        Args:
            phase: The evolution phase.
            event: The event to emit.
        """
        for handler in self._event_handlers.get(phase, []):
            try:
                handler(event)
            except Exception:
                pass

    # ---- Configuration ----

    def configure(
        self,
        user_turn_interval: Optional[int] = None,
        tool_iteration_interval: Optional[int] = None,
        error_threshold: Optional[int] = None,
        background_review_interval_seconds: Optional[int] = None,
        callback: Optional[Callable] = None,
    ) -> None:
        """Configure evolution system parameters.
        
        Args:
            user_turn_interval: Turns between user-turn reviews.
            tool_iteration_interval: Tool calls between iteration reviews.
            error_threshold: Consecutive errors before review.
            background_review_interval_seconds: Seconds between background reviews.
            callback: Callback for review results notification.
        """
        if user_turn_interval is not None:
            self._review_config["user_turn_interval"] = user_turn_interval
        if tool_iteration_interval is not None:
            self._review_config["tool_iteration_interval"] = tool_iteration_interval
        if error_threshold is not None:
            self._review_config["error_threshold"] = error_threshold
        if background_review_interval_seconds is not None:
            self._review_config["background_review_interval_seconds"] = background_review_interval_seconds
        if callback is not None:
            self._callback = callback

    # ---- Status & Metrics ----

    def get_status(self) -> Dict[str, Any]:
        """Get the current status of the evolution system.
        
        Returns:
            Status dictionary with all relevant information.
        """
        return {
            "status": self._status.value,
            "total_experiences": self._metrics.total_experiences,
            "total_patterns": self._metrics.total_patterns,
            "total_skills": self._metrics.total_skills,
            "total_reviews": self._metrics.total_reviews,
            "active_skills": sum(
                1 for s in self._skills.values()
                if s.confidence != SkillConfidence.DEPRECATED
            ),
            "user_turns": self._user_turns,
            "tool_iterations": self._tool_iterations,
            "consecutive_errors": self._consecutive_errors,
            "background_review_active": (
                self._background_thread is not None
                and self._background_thread.is_alive()
            ),
        }

    def get_metrics(self) -> Dict[str, Any]:
        """Get detailed evolution metrics.
        
        Returns:
            Metrics dictionary.
        """
        return self._metrics.to_dict()

    def get_skills(self) -> List[Dict[str, Any]]:
        """Get all crystallized skills.
        
        Returns:
            List of skill dictionaries.
        """
        return [s.to_dict() for s in self._skills.values()]

    def get_experiences(
        self,
        experience_type: Optional[ExperienceType] = None,
        min_success_score: float = 0.0,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """Get captured experiences with optional filters.
        
        Args:
            experience_type: Filter by experience type.
            min_success_score: Minimum success score.
            limit: Maximum number of results.
        
        Returns:
            List of experience dictionaries.
        """
        results = []
        for exp in list(self._experiences.values()):
            if experience_type and exp.experience_type != experience_type:
                continue
            if exp.success_score < min_success_score:
                continue
            results.append(exp.to_dict())
        return sorted(
            results, key=lambda x: x["timestamp"], reverse=True
        )[:limit]

    # ---- Lifecycle ----

    def shutdown(self) -> None:
        """Gracefully shut down the evolution system."""
        with self._lock:
            self._status = EvolutionStatus.SHUTDOWN
            self._shutdown_flag.set()
            if self._background_thread and self._background_thread.is_alive():
                self._background_thread.join(timeout=5.0)
            self._background_thread = None

    def reset(self) -> None:
        """Reset all evolution data (for testing)."""
        with self._lock:
            self.shutdown()
            self._experiences.clear()
            self._patterns.clear()
            self._skills.clear()
            self._events.clear()
            self._user_turns = 0
            self._tool_iterations = 0
            self._consecutive_errors = 0
            self._metrics = EvolutionMetrics()
            self._status = EvolutionStatus.IDLE
            self._shutdown_flag.clear()


# ---------------------------------------------------------------------------
# Module-level accessor
# ---------------------------------------------------------------------------

def get_agent_experience_evolution() -> AgentExperienceEvolution:
    """Get the singleton AgentExperienceEvolution instance."""
    return AgentExperienceEvolution()