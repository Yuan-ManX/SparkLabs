"""
SparkLabs Agent - Skill Lifecycle Engine

A self-improving skill lifecycle management system. Skills are created
from experience, refined during use, persisted across sessions, and
shared across domains. This is an original SparkLabs design for
autonomous skill evolution.

The engine treats every skill as a living artifact that moves through
distinct lifecycle phases, accumulates execution experiences, and is
periodically refined by heuristic strategies. Refined knowledge is
captured as artifacts (procedures, patterns, heuristics, rules) that
travel with the skill when it is shared or persisted.

Architecture:
  SkillLifecycleEngine
    |-- SkillPhase (lifecycle stage of a skill)
    |-- RefinementStrategy (tuning approach applied during refinement)
    |-- PersistenceState (durability tier of skill data)
    |-- SkillOrigin (provenance of a skill)
    |-- ArtifactContentType (kind of knowledge captured in an artifact)
    |-- SkillMetadata (canonical skill record)
    |-- SkillExperience (single execution observation)
    |-- RefinementCycle (one refinement iteration result)
    |-- SkillArtifact (reusable knowledge fragment)
    |-- LifecycleEvent (phase transition audit record)

Lifecycle Flow:
  EMBRYONIC -> DEVELOPING -> MATURE -> REFINING -> MATURE (loop)
  any active phase -> DEPRECATED -> ARCHIVED
"""

from __future__ import annotations

import threading
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class SkillPhase(Enum):
    EMBRYONIC = "embryonic"
    DEVELOPING = "developing"
    MATURE = "mature"
    REFINING = "refining"
    DEPRECATED = "deprecated"
    ARCHIVED = "archived"


class RefinementStrategy(Enum):
    PARAMETER_TUNING = "parameter_tuning"
    STEP_OPTIMIZATION = "step_optimization"
    CONTEXT_EXPANSION = "context_expansion"
    FAILURE_ANALYSIS = "failure_analysis"
    PERFORMANCE_PROFILING = "performance_profiling"


class PersistenceState(Enum):
    VOLATILE = "volatile"
    CACHED = "cached"
    PERSISTED = "persisted"
    DISTRIBUTED = "distributed"


class SkillOrigin(Enum):
    EXPERIENCE_DERIVED = "experience_derived"
    MANUALLY_CRAFTED = "manually_crafted"
    COMPOSED = "composed"
    EVOLVED = "evolved"
    IMPORTED = "imported"


class ArtifactContentType(Enum):
    PROCEDURE = "procedure"
    PATTERN = "pattern"
    HEURISTIC = "heuristic"
    RULE = "rule"


# ---------------------------------------------------------------------------
# Phase transition rules
# ---------------------------------------------------------------------------

# Valid forward and lateral transitions between lifecycle phases.
VALID_PHASE_TRANSITIONS: Dict[SkillPhase, Set[SkillPhase]] = {
    SkillPhase.EMBRYONIC: {SkillPhase.DEVELOPING, SkillPhase.DEPRECATED},
    SkillPhase.DEVELOPING: {SkillPhase.MATURE, SkillPhase.REFINING, SkillPhase.DEPRECATED},
    SkillPhase.MATURE: {SkillPhase.REFINING, SkillPhase.DEPRECATED},
    SkillPhase.REFINING: {SkillPhase.MATURE, SkillPhase.DEPRECATED},
    SkillPhase.DEPRECATED: {SkillPhase.ARCHIVED, SkillPhase.MATURE},
    SkillPhase.ARCHIVED: set(),  # terminal state
}

# Minimum evidence required to graduate into a forward phase.
PHASE_REQUIREMENTS: Dict[Tuple[SkillPhase, SkillPhase], Dict[str, float]] = {
    (SkillPhase.EMBRYONIC, SkillPhase.DEVELOPING): {
        "min_executions": 5,
        "min_success_rate": 0.3,
    },
    (SkillPhase.DEVELOPING, SkillPhase.MATURE): {
        "min_executions": 15,
        "min_success_rate": 0.6,
    },
}


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------


@dataclass
class SkillExperience:
    experience_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    skill_id: str = ""
    execution_context: Dict[str, Any] = field(default_factory=dict)
    outcome: str = ""
    duration_ms: float = 0.0
    success_score: float = 0.0
    failure_points: List[str] = field(default_factory=list)
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "experience_id": self.experience_id,
            "skill_id": self.skill_id,
            "execution_context": self.execution_context,
            "outcome": self.outcome,
            "duration_ms": self.duration_ms,
            "success_score": self.success_score,
            "failure_points": self.failure_points,
            "timestamp": self.timestamp,
        }


@dataclass
class RefinementCycle:
    cycle_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    skill_id: str = ""
    strategy: RefinementStrategy = RefinementStrategy.PARAMETER_TUNING
    before_score: float = 0.0
    after_score: float = 0.0
    changes_made: List[str] = field(default_factory=list)
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "cycle_id": self.cycle_id,
            "skill_id": self.skill_id,
            "strategy": self.strategy.value,
            "before_score": self.before_score,
            "after_score": self.after_score,
            "changes_made": self.changes_made,
            "timestamp": self.timestamp,
        }


@dataclass
class SkillMetadata:
    skill_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    name: str = ""
    domain: str = ""
    description: str = ""
    phase: SkillPhase = SkillPhase.EMBRYONIC
    origin: SkillOrigin = SkillOrigin.MANUALLY_CRAFTED
    persistence_state: PersistenceState = PersistenceState.VOLATILE
    version: int = 1
    success_rate: float = 0.0
    avg_duration: float = 0.0
    total_executions: int = 0
    last_used: float = field(default_factory=time.time)
    dependencies: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "skill_id": self.skill_id,
            "name": self.name,
            "domain": self.domain,
            "description": self.description,
            "phase": self.phase.value,
            "origin": self.origin.value,
            "persistence_state": self.persistence_state.value,
            "version": self.version,
            "success_rate": self.success_rate,
            "avg_duration": self.avg_duration,
            "total_executions": self.total_executions,
            "last_used": self.last_used,
            "dependencies": self.dependencies,
            "tags": self.tags,
        }


@dataclass
class SkillArtifact:
    artifact_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    skill_id: str = ""
    content_type: ArtifactContentType = ArtifactContentType.HEURISTIC
    content: Dict[str, Any] = field(default_factory=dict)
    confidence: float = 0.0
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "artifact_id": self.artifact_id,
            "skill_id": self.skill_id,
            "content_type": self.content_type.value,
            "content": self.content,
            "confidence": self.confidence,
            "created_at": self.created_at,
        }


@dataclass
class LifecycleEvent:
    event_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    skill_id: str = ""
    event_type: str = ""
    description: str = ""
    old_phase: Optional[SkillPhase] = None
    new_phase: Optional[SkillPhase] = None
    timestamp: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": self.event_id,
            "skill_id": self.skill_id,
            "event_type": self.event_type,
            "description": self.description,
            "old_phase": self.old_phase.value if self.old_phase else None,
            "new_phase": self.new_phase.value if self.new_phase else None,
            "timestamp": self.timestamp,
            "metadata": self.metadata,
        }


# ---------------------------------------------------------------------------
# SkillLifecycleEngine Singleton
# ---------------------------------------------------------------------------


class SkillLifecycleEngine:
    """
    Central skill lifecycle system for SparkLabs.

    Skills are created, exercised through recorded experiences, refined
    by heuristic strategies, transitioned across lifecycle phases,
    persisted at varying durability tiers, and shared across domains.
    All state mutations are serialized through a single lock to keep
    the in-memory registries consistent under concurrent access.
    """

    _instance: Optional["SkillLifecycleEngine"] = None
    _lock = threading.Lock()

    # Window of recent experiences considered during refinement analysis.
    REFINEMENT_WINDOW = 10
    # Success score at or above which an execution is treated as a success.
    SUCCESS_THRESHOLD = 0.5

    def __init__(self) -> None:
        self._skills: Dict[str, SkillMetadata] = {}
        self._experiences: Dict[str, List[SkillExperience]] = {}
        self._artifacts: Dict[str, List[SkillArtifact]] = {}
        self._refinements: Dict[str, List[RefinementCycle]] = {}
        self._events: Dict[str, List[LifecycleEvent]] = {}

    @classmethod
    def get_instance(cls) -> "SkillLifecycleEngine":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    # ------------------------------------------------------------------
    # Internal helpers (callers must already hold the lock)
    # ------------------------------------------------------------------

    def _emit_event(
        self,
        skill_id: str,
        event_type: str,
        description: str,
        old_phase: Optional[SkillPhase] = None,
        new_phase: Optional[SkillPhase] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> LifecycleEvent:
        event = LifecycleEvent(
            skill_id=skill_id,
            event_type=event_type,
            description=description,
            old_phase=old_phase,
            new_phase=new_phase,
            metadata=metadata or {},
        )
        self._events.setdefault(skill_id, []).append(event)
        return event

    def _add_artifact_internal(
        self,
        skill_id: str,
        content_type: ArtifactContentType,
        content: Dict[str, Any],
        confidence: float,
    ) -> SkillArtifact:
        artifact = SkillArtifact(
            skill_id=skill_id,
            content_type=content_type,
            content=dict(content),
            confidence=max(0.0, min(1.0, confidence)),
        )
        self._artifacts.setdefault(skill_id, []).append(artifact)
        return artifact

    def _compute_skill_score(
        self,
        skill: SkillMetadata,
        experiences: List[SkillExperience],
    ) -> float:
        """Composite performance score in [0, 1] derived from recent experience."""
        if not experiences:
            return max(0.0, min(1.0, skill.success_rate))
        recent = experiences[-self.REFINEMENT_WINDOW:]
        avg_success = sum(e.success_score for e in recent) / len(recent)
        total_failures = sum(len(e.failure_points) for e in recent)
        # Normalize failure density against a generous upper bound so a few
        # failure points do not dominate the score.
        failure_density = min(1.0, total_failures / max(1.0, len(recent) * 3.0))
        avg_dur = sum(e.duration_ms for e in recent) / len(recent)
        # Faster executions score higher; 2000ms maps to zero efficiency.
        duration_efficiency = max(0.0, min(1.0, 1.0 - (avg_dur / 2000.0)))
        score = (
            avg_success * 0.6
            + (1.0 - failure_density) * 0.25
            + duration_efficiency * 0.15
        )
        return max(0.0, min(1.0, score))

    def _auto_evolve(self, skill: SkillMetadata) -> None:
        """Promote a skill when accumulated evidence clears phase thresholds."""
        target: Optional[SkillPhase] = None
        if skill.phase == SkillPhase.EMBRYONIC:
            target = SkillPhase.DEVELOPING
        elif skill.phase == SkillPhase.DEVELOPING:
            target = SkillPhase.MATURE
        if target is None:
            return
        reqs = PHASE_REQUIREMENTS.get((skill.phase, target))
        if not reqs:
            return
        if (
            skill.total_executions >= reqs["min_executions"]
            and skill.success_rate >= reqs["min_success_rate"]
        ):
            old_phase = skill.phase
            skill.phase = target
            self._emit_event(
                skill.skill_id,
                "phase_transition",
                f"Auto-promoted from {old_phase.value} to {target.value}",
                old_phase=old_phase,
                new_phase=target,
                metadata={
                    "total_executions": skill.total_executions,
                    "success_rate": skill.success_rate,
                    "auto": True,
                },
            )

    # ------------------------------------------------------------------
    # Skill creation and lookup
    # ------------------------------------------------------------------

    def create_skill(
        self,
        name: str,
        domain: str,
        description: str = "",
        origin: SkillOrigin = SkillOrigin.MANUALLY_CRAFTED,
        dependencies: Optional[List[str]] = None,
        tags: Optional[List[str]] = None,
    ) -> SkillMetadata:
        with self._lock:
            skill = SkillMetadata(
                name=name,
                domain=domain,
                description=description,
                origin=origin,
                dependencies=list(dependencies or []),
                tags=list(tags or []),
            )
            self._skills[skill.skill_id] = skill
            self._emit_event(
                skill.skill_id,
                "created",
                f"Skill '{name}' created in domain '{domain}'",
                new_phase=skill.phase,
                metadata={"origin": origin.value, "domain": domain},
            )
            return skill

    def get_skill(self, skill_id: str) -> Optional[SkillMetadata]:
        with self._lock:
            return self._skills.get(skill_id)

    # ------------------------------------------------------------------
    # Experience recording
    # ------------------------------------------------------------------

    def record_experience(
        self,
        skill_id: str,
        execution_context: Dict[str, Any],
        outcome: str,
        duration_ms: float,
        success_score: float,
        failure_points: Optional[List[str]] = None,
    ) -> SkillExperience:
        with self._lock:
            skill = self._skills.get(skill_id)
            if skill is None:
                raise ValueError(f"Skill '{skill_id}' not found")
            experience = SkillExperience(
                skill_id=skill_id,
                execution_context=dict(execution_context),
                outcome=outcome,
                duration_ms=duration_ms,
                success_score=max(0.0, min(1.0, success_score)),
                failure_points=list(failure_points or []),
            )
            self._experiences.setdefault(skill_id, []).append(experience)

            # Update rolling statistics on the skill metadata.
            prior_total = skill.total_executions
            new_total = prior_total + 1
            skill.success_rate = (
                (skill.success_rate * prior_total + experience.success_score)
                / new_total
            )
            skill.avg_duration = (
                (skill.avg_duration * prior_total + duration_ms) / new_total
            )
            skill.total_executions = new_total
            skill.last_used = time.time()

            self._emit_event(
                skill_id,
                "experience_recorded",
                f"Recorded experience with outcome '{outcome}'",
                metadata={
                    "success_score": experience.success_score,
                    "duration_ms": duration_ms,
                    "failure_count": len(experience.failure_points),
                },
            )

            # Autonomous promotion when thresholds are cleared.
            self._auto_evolve(skill)
            return experience

    # ------------------------------------------------------------------
    # Refinement
    # ------------------------------------------------------------------

    def refine_skill(
        self,
        skill_id: str,
        strategy: RefinementStrategy,
    ) -> RefinementCycle:
        with self._lock:
            skill = self._skills.get(skill_id)
            if skill is None:
                raise ValueError(f"Skill '{skill_id}' not found")

            experiences = self._experiences.get(skill_id, [])
            before_score = self._compute_skill_score(skill, experiences)
            changes, after_score, updates = self._apply_refinement(
                skill, experiences, strategy, before_score
            )

            # Apply metadata updates produced by the strategy.
            if "avg_duration" in updates:
                skill.avg_duration = updates["avg_duration"]
            if "tags" in updates:
                skill.tags = list(updates["tags"])

            # Bump version and reflect projected success improvement.
            skill.version += 1
            # Blend the projected improvement into the running success rate
            # so refinement has a tangible effect on discoverability.
            skill.success_rate = max(
                skill.success_rate,
                min(1.0, skill.success_rate + (after_score - before_score) * 0.5),
            )

            # Move mature skills into the refining phase while work is ongoing.
            old_phase: Optional[SkillPhase] = None
            if skill.phase == SkillPhase.MATURE:
                old_phase = skill.phase
                skill.phase = SkillPhase.REFINING
                self._emit_event(
                    skill_id,
                    "phase_transition",
                    "Entered refining phase",
                    old_phase=old_phase,
                    new_phase=skill.phase,
                    metadata={"strategy": strategy.value},
                )

            cycle = RefinementCycle(
                skill_id=skill_id,
                strategy=strategy,
                before_score=before_score,
                after_score=after_score,
                changes_made=changes,
            )
            self._refinements.setdefault(skill_id, []).append(cycle)

            self._emit_event(
                skill_id,
                "refined",
                f"Applied {strategy.value}: score {before_score:.3f} -> {after_score:.3f}",
                metadata={
                    "strategy": strategy.value,
                    "before_score": before_score,
                    "after_score": after_score,
                    "changes": changes,
                    "version": skill.version,
                },
            )
            return cycle

    def _apply_refinement(
        self,
        skill: SkillMetadata,
        experiences: List[SkillExperience],
        strategy: RefinementStrategy,
        before_score: float,
    ) -> Tuple[List[str], float, Dict[str, Any]]:
        """
        Apply heuristic refinement logic for the chosen strategy.

        Returns a tuple of (changes_made, after_score, metadata_updates).
        metadata_updates may contain keys such as 'avg_duration' or 'tags'
        that the caller applies to the skill metadata.
        """
        changes: List[str] = []
        updates: Dict[str, Any] = {}
        room = max(0.0, 1.0 - before_score)

        recent = experiences[-self.REFINEMENT_WINDOW:] if experiences else []
        avg_success = (
            sum(e.success_score for e in recent) / len(recent)
            if recent else skill.success_rate
        )
        avg_dur = (
            sum(e.duration_ms for e in recent) / len(recent)
            if recent else skill.avg_duration
        )
        all_failures: List[str] = []
        for exp in recent:
            all_failures.extend(exp.failure_points)

        if strategy == RefinementStrategy.PARAMETER_TUNING:
            # Adjust acceptance thresholds based on the success/failure ratio.
            base_threshold = self.SUCCESS_THRESHOLD
            if avg_success < 0.5:
                new_threshold = min(0.9, base_threshold + 0.15)
                changes.append(
                    f"Tightened acceptance threshold from {base_threshold:.2f} to {new_threshold:.2f}"
                )
                changes.append("Reduced risk tolerance to filter low-confidence outputs")
                improvement = room * 0.18
            elif avg_success > 0.8:
                new_threshold = max(0.2, base_threshold - 0.10)
                changes.append(
                    f"Relaxed acceptance threshold from {base_threshold:.2f} to {new_threshold:.2f}"
                )
                changes.append("Widened applicability window for high-performing skill")
                improvement = room * 0.10
            else:
                new_threshold = base_threshold
                changes.append("Calibrated parameter weights using recent success distribution")
                changes.append(f"Adjusted confidence weighting by {room * 0.12:.2f}")
                improvement = room * 0.12
            updates["acceptance_threshold"] = new_threshold

        elif strategy == RefinementStrategy.STEP_OPTIMIZATION:
            # Trim redundant steps and shorten the critical path.
            if avg_dur > 1500:
                redundant = max(1, int(room * 10))
                reduction_pct = min(35, int(room * 100))
                changes.append(f"Identified {redundant} redundant step(s) in execution path")
                changes.append(f"Projected {reduction_pct}% duration reduction via step elimination")
                improvement = room * 0.15
                updates["avg_duration"] = avg_dur * 0.85
            elif avg_dur > 800:
                changes.append("Reordered execution steps for shorter critical path")
                changes.append("Merged sequential independent steps into a parallel batch")
                improvement = room * 0.10
                updates["avg_duration"] = avg_dur * 0.92
            else:
                changes.append("Step sequence already near optimal; applied micro-optimizations")
                improvement = room * 0.05

        elif strategy == RefinementStrategy.CONTEXT_EXPANSION:
            # Mine successful execution contexts for new applicable dimensions.
            successful = [e for e in recent if e.success_score >= 0.6]
            context_keys: Set[str] = set()
            for exp in successful:
                context_keys.update(exp.execution_context.keys())
            new_tags = [k for k in sorted(context_keys) if k not in skill.tags]
            if new_tags:
                preview = ", ".join(new_tags[:5])
                changes.append(f"Added {len(new_tags)} context-derived tag(s): {preview}")
                updates["tags"] = skill.tags + new_tags
                improvement = room * 0.14
            else:
                changes.append("No new context dimensions discovered; reinforced existing bindings")
                improvement = room * 0.06

        elif strategy == RefinementStrategy.FAILURE_ANALYSIS:
            # Cluster failure points and emit a mitigation rule artifact.
            if all_failures:
                failure_counts: Dict[str, int] = {}
                for fp in all_failures:
                    key = fp.lower().split(":")[0].strip()
                    failure_counts[key] = failure_counts.get(key, 0) + 1
                top_failure = max(failure_counts, key=failure_counts.get)
                top_count = failure_counts[top_failure]
                changes.append(
                    f"Analyzed {len(all_failures)} failure point(s) across {len(recent)} execution(s)"
                )
                changes.append(f"Top failure mode: '{top_failure}' ({top_count} occurrence(s))")
                changes.append(f"Generated mitigation rule for '{top_failure}'")
                self._add_artifact_internal(
                    skill.skill_id,
                    ArtifactContentType.RULE,
                    {
                        "target_failure": top_failure,
                        "occurrences": top_count,
                        "mitigation": f"Add pre-check to avoid {top_failure}",
                    },
                    confidence=min(0.9, 0.5 + top_count * 0.1),
                )
                improvement = room * 0.20
            else:
                changes.append("No failure points recorded; reinforced success-path heuristics")
                improvement = room * 0.05

        elif strategy == RefinementStrategy.PERFORMANCE_PROFILING:
            # Profile execution times, flag outliers, and set a budget.
            if recent:
                durations = [e.duration_ms for e in recent]
                mean_dur = sum(durations) / len(durations)
                max_dur = max(durations)
                outliers = [d for d in durations if d > mean_dur * 1.5]
                budget = mean_dur * 1.2
                changes.append(
                    f"Profiled {len(durations)} execution(s): mean={mean_dur:.0f}ms, max={max_dur:.0f}ms"
                )
                changes.append(f"Set performance budget to {budget:.0f}ms")
                if outliers:
                    changes.append(
                        f"Flagged {len(outliers)} outlier execution(s) exceeding 1.5x mean"
                    )
                    improvement = room * 0.12
                else:
                    changes.append("Execution times within stable band; no outliers detected")
                    improvement = room * 0.06
                updates["avg_duration"] = mean_dur
            else:
                changes.append("Insufficient data for profiling; retained current performance baseline")
                improvement = room * 0.03

        else:
            changes.append(f"Unknown strategy {strategy}; no changes applied")
            improvement = 0.0

        after_score = min(1.0, before_score + improvement)
        return changes, after_score, updates

    # ------------------------------------------------------------------
    # Phase evolution
    # ------------------------------------------------------------------

    def evolve_phase(
        self,
        skill_id: str,
        target_phase: SkillPhase,
    ) -> LifecycleEvent:
        with self._lock:
            skill = self._skills.get(skill_id)
            if skill is None:
                raise ValueError(f"Skill '{skill_id}' not found")
            old_phase = skill.phase
            if old_phase == target_phase:
                # No-op transition still produces an audit record.
                return self._emit_event(
                    skill_id,
                    "phase_transition",
                    f"Skill already in {target_phase.value} phase",
                    old_phase=old_phase,
                    new_phase=target_phase,
                )
            allowed = VALID_PHASE_TRANSITIONS.get(old_phase, set())
            if target_phase not in allowed:
                raise ValueError(
                    f"Invalid phase transition: {old_phase.value} -> {target_phase.value}"
                )
            reqs = PHASE_REQUIREMENTS.get((old_phase, target_phase))
            if reqs:
                if skill.total_executions < reqs["min_executions"]:
                    raise ValueError(
                        f"Phase transition requires {reqs['min_executions']} executions, "
                        f"found {skill.total_executions}"
                    )
                if skill.success_rate < reqs["min_success_rate"]:
                    raise ValueError(
                        f"Phase transition requires success rate >= {reqs['min_success_rate']}, "
                        f"found {skill.success_rate:.3f}"
                    )
            skill.phase = target_phase
            return self._emit_event(
                skill_id,
                "phase_transition",
                f"Transitioned from {old_phase.value} to {target_phase.value}",
                old_phase=old_phase,
                new_phase=target_phase,
                metadata={
                    "total_executions": skill.total_executions,
                    "success_rate": skill.success_rate,
                },
            )

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def persist_skill(
        self,
        skill_id: str,
        persistence_state: PersistenceState,
    ) -> bool:
        with self._lock:
            skill = self._skills.get(skill_id)
            if skill is None:
                return False
            old_state = skill.persistence_state
            skill.persistence_state = persistence_state
            self._emit_event(
                skill_id,
                "persisted",
                f"Persistence state changed from {old_state.value} to {persistence_state.value}",
                metadata={
                    "old_state": old_state.value,
                    "new_state": persistence_state.value,
                },
            )
            return True

    # ------------------------------------------------------------------
    # Sharing
    # ------------------------------------------------------------------

    def share_skill(
        self,
        skill_id: str,
        target_domain: str,
    ) -> SkillMetadata:
        with self._lock:
            source = self._skills.get(skill_id)
            if source is None:
                raise ValueError(f"Skill '{skill_id}' not found")
            clone = SkillMetadata(
                name=source.name,
                domain=target_domain,
                description=source.description,
                phase=SkillPhase.EMBRYONIC,
                origin=SkillOrigin.IMPORTED,
                persistence_state=PersistenceState.VOLATILE,
                version=1,
                dependencies=list(source.dependencies),
                tags=list(source.tags),
            )
            self._skills[clone.skill_id] = clone
            # Copy artifacts so the imported skill starts with the same
            # knowledge fragments as the source.
            for artifact in self._artifacts.get(skill_id, []):
                self._add_artifact_internal(
                    clone.skill_id,
                    artifact.content_type,
                    artifact.content,
                    artifact.confidence,
                )
            self._emit_event(
                clone.skill_id,
                "shared",
                f"Skill shared from domain '{source.domain}' to '{target_domain}'",
                new_phase=clone.phase,
                metadata={
                    "source_skill_id": skill_id,
                    "source_domain": source.domain,
                    "target_domain": target_domain,
                    "artifacts_copied": len(self._artifacts.get(skill_id, [])),
                },
            )
            return clone

    # ------------------------------------------------------------------
    # Archival
    # ------------------------------------------------------------------

    def archive_skill(
        self,
        skill_id: str,
        reason: str,
    ) -> LifecycleEvent:
        with self._lock:
            skill = self._skills.get(skill_id)
            if skill is None:
                raise ValueError(f"Skill '{skill_id}' not found")
            old_phase = skill.phase
            # Route through DEPRECATED first when the skill is still active,
            # then drop into ARCHIVED so the transition graph stays valid.
            if old_phase != SkillPhase.DEPRECATED and old_phase != SkillPhase.ARCHIVED:
                skill.phase = SkillPhase.DEPRECATED
            if skill.phase != SkillPhase.ARCHIVED:
                skill.phase = SkillPhase.ARCHIVED
            return self._emit_event(
                skill_id,
                "archived",
                f"Skill archived: {reason}",
                old_phase=old_phase,
                new_phase=skill.phase,
                metadata={"reason": reason},
            )

    # ------------------------------------------------------------------
    # Artifacts
    # ------------------------------------------------------------------

    def get_skill_artifacts(self, skill_id: str) -> List[SkillArtifact]:
        with self._lock:
            return list(self._artifacts.get(skill_id, []))

    def add_artifact(
        self,
        skill_id: str,
        content_type: ArtifactContentType,
        content: Dict[str, Any],
        confidence: float,
    ) -> SkillArtifact:
        with self._lock:
            skill = self._skills.get(skill_id)
            if skill is None:
                raise ValueError(f"Skill '{skill_id}' not found")
            artifact = self._add_artifact_internal(
                skill_id, content_type, content, confidence
            )
            self._emit_event(
                skill_id,
                "artifact_added",
                f"Added {content_type.value} artifact",
                metadata={
                    "artifact_id": artifact.artifact_id,
                    "content_type": content_type.value,
                    "confidence": artifact.confidence,
                },
            )
            return artifact

    # ------------------------------------------------------------------
    # History and discovery
    # ------------------------------------------------------------------

    def get_lifecycle_history(self, skill_id: str) -> List[LifecycleEvent]:
        with self._lock:
            return list(self._events.get(skill_id, []))

    def discover_skills(
        self,
        domain: Optional[str] = None,
        tags: Optional[List[str]] = None,
        min_success_rate: float = 0.0,
    ) -> List[SkillMetadata]:
        with self._lock:
            results: List[SkillMetadata] = []
            tag_set = set(tags) if tags else None
            for skill in self._skills.values():
                if skill.phase in (SkillPhase.DEPRECATED, SkillPhase.ARCHIVED):
                    continue
                if domain and skill.domain != domain:
                    continue
                if tag_set and not (set(skill.tags) & tag_set):
                    continue
                if skill.success_rate < min_success_rate:
                    continue
                results.append(skill)
            # Rank by success rate descending, then by total executions.
            results.sort(
                key=lambda s: (s.success_rate, s.total_executions),
                reverse=True,
            )
            return results

    # ------------------------------------------------------------------
    # Stats
    # ------------------------------------------------------------------

    def get_stats(self) -> Dict[str, Any]:
        with self._lock:
            phase_counts: Dict[str, int] = {}
            origin_counts: Dict[str, int] = {}
            persistence_counts: Dict[str, int] = {}
            domain_counts: Dict[str, int] = {}
            total_experiences = 0
            total_artifacts = 0
            total_refinements = 0
            total_events = 0
            for skill in self._skills.values():
                phase_counts[skill.phase.value] = phase_counts.get(skill.phase.value, 0) + 1
                origin_counts[skill.origin.value] = origin_counts.get(skill.origin.value, 0) + 1
                persistence_counts[skill.persistence_state.value] = (
                    persistence_counts.get(skill.persistence_state.value, 0) + 1
                )
                domain_counts[skill.domain] = domain_counts.get(skill.domain, 0) + 1
                total_experiences += len(self._experiences.get(skill.skill_id, []))
                total_artifacts += len(self._artifacts.get(skill.skill_id, []))
                total_refinements += len(self._refinements.get(skill.skill_id, []))
                total_events += len(self._events.get(skill.skill_id, []))
            return {
                "total_skills": len(self._skills),
                "total_experiences": total_experiences,
                "total_artifacts": total_artifacts,
                "total_refinements": total_refinements,
                "total_events": total_events,
                "by_phase": phase_counts,
                "by_origin": origin_counts,
                "by_persistence_state": persistence_counts,
                "by_domain": domain_counts,
            }


# ---------------------------------------------------------------------------
# Module-level singleton accessor
# ---------------------------------------------------------------------------


_global_skill_lifecycle_engine: Optional[SkillLifecycleEngine] = None


def get_skill_lifecycle_engine() -> SkillLifecycleEngine:
    """Return the shared SkillLifecycleEngine singleton instance."""
    global _global_skill_lifecycle_engine
    if _global_skill_lifecycle_engine is None:
        _global_skill_lifecycle_engine = SkillLifecycleEngine.get_instance()
    return _global_skill_lifecycle_engine
