"""
SparkLabs Agent - Autonomous Learning Cycle Engine

Manages the full lifecycle of agent self-improvement through structured
learning cycles. The engine orchestrates Plan -> Execute -> Reflect -> Improve
phases, maintains an experience replay buffer for accumulating task outcomes,
tracks skill levels across game development domains, and generates adaptive
strategies based on historical performance patterns.

Architecture:
  LearningCycleEngine
    |-- LearningCycle (five-phase cycle: Planning, Execution, Reflection, Improvement, Consolidation)
    |-- LearningExperience (replay buffer entries cataloging task outcomes)
    |-- DomainSkill (per-domain proficiency tracking with level progression)
    |-- InsightExtractor (pattern extraction from accumulated experiences)
    |-- NudgeGenerator (periodic self-improvement suggestion engine)
"""

from __future__ import annotations

import time
import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


class CyclePhase(Enum):
    PLANNING = "planning"
    EXECUTION = "execution"
    REFLECTION = "reflection"
    IMPROVEMENT = "improvement"
    CONSOLIDATION = "consolidation"


class LearningDomain(Enum):
    CODE_GENERATION = "code_generation"
    ASSET_CREATION = "asset_creation"
    LEVEL_DESIGN = "level_design"
    GAME_BALANCE = "game_balance"
    NARRATIVE_DESIGN = "narrative_design"
    UI_LAYOUT = "ui_layout"
    PERFORMANCE_TUNING = "performance_tuning"
    BUG_FIXING = "bug_fixing"


class SkillLevel(Enum):
    NOVICE = "novice"
    BEGINNER = "beginner"
    COMPETENT = "competent"
    PROFICIENT = "proficient"
    EXPERT = "expert"
    MASTER = "master"


SKILL_LEVEL_ORDER: Dict[SkillLevel, int] = {
    SkillLevel.NOVICE: 0,
    SkillLevel.BEGINNER: 1,
    SkillLevel.COMPETENT: 2,
    SkillLevel.PROFICIENT: 3,
    SkillLevel.EXPERT: 4,
    SkillLevel.MASTER: 5,
}

SKILL_LEVEL_THRESHOLDS: Dict[SkillLevel, Tuple[int, float, float]] = {
    SkillLevel.NOVICE: (0, 0.0, 0.0),
    SkillLevel.BEGINNER: (5, 0.4, 0.3),
    SkillLevel.COMPETENT: (15, 0.6, 0.5),
    SkillLevel.PROFICIENT: (35, 0.75, 0.65),
    SkillLevel.EXPERT: (70, 0.85, 0.8),
    SkillLevel.MASTER: (120, 0.92, 0.9),
}

DOMAIN_NUDGE_TEMPLATES: Dict[LearningDomain, List[str]] = {
    LearningDomain.CODE_GENERATION: [
        "Review recent compilation failures and identify recurring syntax patterns to address.",
        "Consider breaking down complex code generation tasks into smaller, verifiable units.",
        "Apply stricter pre-generation linting checks to catch errors before execution.",
        "Cross-reference generated code against successful past patterns in the same domain.",
    ],
    LearningDomain.ASSET_CREATION: [
        "Audit recent asset outputs for consistency with project style guidelines.",
        "Experiment with alternative asset generation parameters to improve visual coherence.",
        "Review asset resolution and format choices against target platform constraints.",
    ],
    LearningDomain.LEVEL_DESIGN: [
        "Analyze player flow data to identify level segments with high abandonment rates.",
        "Adjust entity placement density based on recent playtest feedback.",
        "Re-evaluate difficulty curve pacing across the most recent designed levels.",
    ],
    LearningDomain.GAME_BALANCE: [
        "Run statistical analysis on win/loss ratios across recent balance adjustments.",
        "Compare current parameter values against baseline values from successful sessions.",
        "Check for unintended interactions between recently modified game systems.",
    ],
    LearningDomain.NARRATIVE_DESIGN: [
        "Review narrative branch coherence by tracing all possible story paths.",
        "Check character dialogue consistency across recent narrative segments.",
        "Ensure newly added narrative branches properly connect to existing story nodes.",
    ],
    LearningDomain.UI_LAYOUT: [
        "Verify UI element contrast ratios meet accessibility standards.",
        "Test UI layouts at multiple screen resolutions for responsive behavior.",
        "Review input interaction flows for unnecessary complexity or steps.",
    ],
    LearningDomain.PERFORMANCE_TUNING: [
        "Profile the most recently modified game systems for performance regressions.",
        "Re-evaluate asset loading strategies based on recent frame time data.",
        "Check memory allocation patterns for potential leaks in frequently executed paths.",
    ],
    LearningDomain.BUG_FIXING: [
        "Categorize recent bug fixes to identify systemic issue areas requiring deeper refactoring.",
        "Review fixed bugs for regression risk in related systems.",
        "Analyze fix turnaround times to identify bottlenecks in the debugging workflow.",
    ],
}


@dataclass
class LearningExperience:
    exp_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    domain: LearningDomain = LearningDomain.CODE_GENERATION
    task_description: str = ""
    outcome_success: bool = False
    quality_score: float = 0.0
    time_taken_ms: float = 0.0
    lessons_learned: List[str] = field(default_factory=list)
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "exp_id": self.exp_id,
            "domain": self.domain.value,
            "task_description": self.task_description,
            "outcome_success": self.outcome_success,
            "quality_score": self.quality_score,
            "time_taken_ms": self.time_taken_ms,
            "lessons_learned": self.lessons_learned,
            "timestamp": self.timestamp,
        }


@dataclass
class LearningCycle:
    cycle_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    phase: CyclePhase = CyclePhase.PLANNING
    domain: LearningDomain = LearningDomain.CODE_GENERATION
    plan_steps: List[str] = field(default_factory=list)
    execution_result: str = ""
    reflection_notes: str = ""
    improvements: List[str] = field(default_factory=list)
    duration_ms: float = 0.0
    completed: bool = False
    timestamp: float = field(default_factory=time.time)
    phase_timestamps: Dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "cycle_id": self.cycle_id,
            "phase": self.phase.value,
            "domain": self.domain.value,
            "plan_steps": self.plan_steps,
            "execution_result": self.execution_result,
            "reflection_notes": self.reflection_notes,
            "improvements": self.improvements,
            "duration_ms": self.duration_ms,
            "completed": self.completed,
            "timestamp": self.timestamp,
        }


@dataclass
class DomainSkill:
    domain: LearningDomain = LearningDomain.CODE_GENERATION
    current_level: SkillLevel = SkillLevel.NOVICE
    experience_count: int = 0
    success_rate: float = 0.0
    average_quality: float = 0.0
    last_updated: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "domain": self.domain.value,
            "current_level": self.current_level.value,
            "experience_count": self.experience_count,
            "success_rate": round(self.success_rate, 3),
            "average_quality": round(self.average_quality, 3),
            "last_updated": self.last_updated,
        }


class LearningCycleEngine:
    """
    Autonomous learning cycle orchestrator for the SparkLabs AI-native game engine.

    Drives continuous agent improvement through structured Plan -> Execute ->
    Reflect -> Improve -> Consolidate cycles. Maintains an experience replay
    buffer for cross-domain pattern extraction, tracks per-domain skill
    progression with level thresholds, and generates adaptive improvement
    nudges based on accumulated performance history.
    """

    _instance: Optional["LearningCycleEngine"] = None

    def __init__(self):
        self._cycles: Dict[str, LearningCycle] = {}
        self._experiences: List[LearningExperience] = []
        self._domain_skills: Dict[LearningDomain, DomainSkill] = {}
        self._complete_count: int = 0
        self._total_duration_ms: float = 0.0
        self._max_experiences: int = 2000
        self._nudge_interval_cycles: int = 10
        self._insight_min_confidence: float = 0.6
        self._cycles_since_last_nudge: int = 0
        self._last_nudge_text: str = ""
        self._init_domain_skills()

    def _init_domain_skills(self) -> None:
        for domain in LearningDomain:
            self._domain_skills[domain] = DomainSkill(domain=domain)

    @classmethod
    def get_instance(cls) -> "LearningCycleEngine":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def start_cycle(
        self,
        domain: LearningDomain,
        task_description: str,
    ) -> LearningCycle:
        cycle = LearningCycle(
            phase=CyclePhase.PLANNING,
            domain=domain,
            plan_steps=[task_description],
        )
        cycle.phase_timestamps[CyclePhase.PLANNING.value] = time.time()
        self._cycles[cycle.cycle_id] = cycle
        return cycle

    def record_phase(
        self,
        cycle_id: str,
        phase: CyclePhase,
        details: str,
    ) -> None:
        cycle = self._cycles.get(cycle_id)
        if cycle is None:
            return

        cycle.phase = phase
        cycle.phase_timestamps[phase.value] = time.time()

        if phase == CyclePhase.PLANNING:
            cycle.plan_steps.append(details)
        elif phase == CyclePhase.EXECUTION:
            cycle.execution_result = details
        elif phase == CyclePhase.REFLECTION:
            cycle.reflection_notes = details
        elif phase == CyclePhase.IMPROVEMENT:
            cycle.improvements.append(details)

    def complete_cycle(
        self,
        cycle_id: str,
        outcome_success: bool,
        quality_score: float,
        lessons: List[str],
    ) -> Optional[LearningCycle]:
        cycle = self._cycles.get(cycle_id)
        if cycle is None:
            return None

        cycle.phase = CyclePhase.CONSOLIDATION
        cycle.completed = True
        cycle.phase_timestamps[CyclePhase.CONSOLIDATION.value] = time.time()

        start_time = cycle.phase_timestamps.get(CyclePhase.PLANNING.value, cycle.timestamp)
        cycle.duration_ms = (time.time() - start_time) * 1000.0

        quality_score = max(0.0, min(1.0, quality_score))

        experience = LearningExperience(
            domain=cycle.domain,
            task_description=cycle.plan_steps[0] if cycle.plan_steps else "",
            outcome_success=outcome_success,
            quality_score=quality_score,
            time_taken_ms=cycle.duration_ms,
            lessons_learned=list(lessons),
            timestamp=time.time(),
        )
        self._experiences.append(experience)
        if len(self._experiences) > self._max_experiences:
            self._experiences = self._experiences[-self._max_experiences:]

        self._update_domain_skill(cycle.domain, outcome_success, quality_score)
        self._complete_count += 1
        self._total_duration_ms += cycle.duration_ms
        self._cycles_since_last_nudge += 1

        return cycle

    def _update_domain_skill(
        self,
        domain: LearningDomain,
        success: bool,
        quality: float,
    ) -> None:
        skill = self._domain_skills.get(domain)
        if skill is None:
            return

        n = skill.experience_count
        skill.experience_count = n + 1
        skill.success_rate = (skill.success_rate * n + (1.0 if success else 0.0)) / (n + 1)
        skill.average_quality = (skill.average_quality * n + quality) / (n + 1)
        skill.last_updated = time.time()

        self._recalculate_level(skill)

    def _recalculate_level(self, skill: DomainSkill) -> None:
        ordered_levels = sorted(SKILL_LEVEL_ORDER.keys(), key=lambda l: SKILL_LEVEL_ORDER[l])

        for i in range(len(ordered_levels) - 1, -1, -1):
            level = ordered_levels[i]
            min_exp, min_success, min_quality = SKILL_LEVEL_THRESHOLDS.get(level, (0, 0.0, 0.0))
            if (
                skill.experience_count >= min_exp
                and skill.success_rate >= min_success
                and skill.average_quality >= min_quality
            ):
                skill.current_level = level
                break

    def store_experience(self, experience: LearningExperience) -> str:
        self._experiences.append(experience)
        if len(self._experiences) > self._max_experiences:
            self._experiences = self._experiences[-self._max_experiences:]

        self._update_domain_skill(
            experience.domain,
            experience.outcome_success,
            experience.quality_score,
        )
        return experience.exp_id

    def retrieve_similar_experiences(
        self,
        domain: LearningDomain,
        limit: int = 10,
    ) -> List[LearningExperience]:
        domain_experiences = [e for e in self._experiences if e.domain == domain]
        domain_experiences.sort(key=lambda e: e.timestamp, reverse=True)
        return domain_experiences[:limit]

    def evaluate_skill_level(self, domain: LearningDomain) -> DomainSkill:
        skill = self._domain_skills.get(domain)
        if skill is None:
            skill = DomainSkill(domain=domain)
            self._domain_skills[domain] = skill
        return skill

    def generate_improvement_nudge(self) -> str:
        strategies = [
            self._nudge_from_weakest_domain,
            self._nudge_from_stagnant_domain,
            self._nudge_general,
        ]

        for strategy_fn in strategies:
            nudge = strategy_fn()
            if nudge:
                self._last_nudge_text = nudge
                self._cycles_since_last_nudge = 0
                return nudge

        return "Continue accumulating experience across domains to unlock deeper learning patterns."

    def _nudge_from_weakest_domain(self) -> str:
        if self._cycles_since_last_nudge < self._nudge_interval_cycles:
            return ""

        weakest = None
        for domain, skill in self._domain_skills.items():
            if skill.experience_count < 3:
                continue
            if weakest is None or skill.success_rate < weakest[1].success_rate:
                weakest = (domain, skill)

        if weakest is None or weakest[1].success_rate >= 0.7:
            return ""

        domain, skill = weakest
        templates = DOMAIN_NUDGE_TEMPLATES.get(domain, [])
        if not templates:
            return f"Focus attention on {domain.value.replace('_', ' ')}: success rate is {skill.success_rate:.0%}. Review recent failures for improvement patterns."

        selected = templates[hash(str(time.time())) % len(templates)]
        return f"[{domain.value.replace('_', ' ').title()}] {selected} (current success rate: {skill.success_rate:.0%})"

    def _nudge_from_stagnant_domain(self) -> str:
        stagnant = None
        for domain, skill in self._domain_skills.items():
            if skill.experience_count < 5:
                continue
            if skill.current_level in (SkillLevel.COMPETENT, SkillLevel.PROFICIENT):
                if skill.success_rate < 0.7 or skill.average_quality < 0.65:
                    stagnant = (domain, skill)
                    break
            if skill.current_level == SkillLevel.BEGINNER and skill.experience_count >= 15:
                if skill.success_rate < 0.5:
                    stagnant = (domain, skill)
                    break

        if stagnant is None:
            return ""

        domain, skill = stagnant
        templates = DOMAIN_NUDGE_TEMPLATES.get(domain, [])
        if not templates:
            return ""

        selected = templates[(hash(str(self._complete_count)) + 1) % len(templates)]
        return f"[{domain.value.replace('_', ' ').title()}] {selected}"

    def _nudge_general(self) -> str:
        total = len(self._experiences)
        if total == 0:
            return "Begin your first learning cycle to establish baseline performance metrics."

        success_count = sum(1 for e in self._experiences if e.outcome_success)
        overall_rate = success_count / total

        if overall_rate < 0.5:
            return (
                f"Overall success rate is {overall_rate:.0%}. "
                "Consider adopting more conservative planning strategies "
                "with smaller, verifiable task scopes."
            )

        if total >= 20 and overall_rate > 0.85:
            return (
                f"Strong overall performance detected ({overall_rate:.0%} success rate). "
                "Gradually increase task complexity to push skill boundaries."
            )

        if self._complete_count >= 30:
            domain_counts = defaultdict(int)
            for e in self._experiences:
                domain_counts[e.domain] += 1
            rare_domains = [d for d in LearningDomain if domain_counts.get(d, 0) < 3]
            if rare_domains:
                domain_name = rare_domains[0].value.replace("_", " ")
                return f"Expand experience in underrepresented domains. Consider practicing {domain_name} to build well-rounded capabilities."

        return ""

    def extract_insights(
        self,
        domain: LearningDomain,
        min_experiences: int = 5,
    ) -> List[str]:
        domain_experiences = [e for e in self._experiences if e.domain == domain]
        if len(domain_experiences) < min_experiences:
            return []

        insights: List[str] = []

        success_count = sum(1 for e in domain_experiences if e.outcome_success)
        success_rate = success_count / len(domain_experiences)

        recent_n = domain_experiences[-min(20, len(domain_experiences)):]
        recent_success = sum(1 for e in recent_n if e.outcome_success) / len(recent_n)

        all_lessons: List[str] = []
        for e in domain_experiences:
            all_lessons.extend(e.lessons_learned)

        if recent_success > success_rate + 0.15:
            insights.append(
                f"{domain.value.replace('_', ' ').title()}: "
                f"Recent performance ({recent_success:.0%}) significantly exceeds historical average ({success_rate:.0%}). "
                f"Current strategies are producing strong results."
            )

        if recent_success < success_rate - 0.15 and len(recent_n) >= 5:
            insights.append(
                f"{domain.value.replace('_', ' ').title()}: "
                f"Recent performance ({recent_success:.0%}) has declined below historical average ({success_rate:.0%}). "
                f"Review recent changes for potential regressions."
            )

        avg_quality = sum(e.quality_score for e in domain_experiences) / len(domain_experiences)
        if avg_quality < 0.5 and len(domain_experiences) >= 8:
            insights.append(
                f"{domain.value.replace('_', ' ').title()}: "
                f"Average quality score is low ({avg_quality:.2f}). "
                f"Focus on output quality over throughput in this domain."
            )

        success_times = [e.time_taken_ms for e in domain_experiences if e.outcome_success]
        fail_times = [e.time_taken_ms for e in domain_experiences if not e.outcome_success]
        if success_times and fail_times:
            avg_success_time = sum(success_times) / len(success_times)
            avg_fail_time = sum(fail_times) / len(fail_times)
            if avg_fail_time > avg_success_time * 1.5:
                insights.append(
                    f"{domain.value.replace('_', ' ').title()}: "
                    f"Failed tasks take {avg_fail_time/avg_success_time:.1f}x longer than successful ones. "
                    f"Consider earlier bail-out criteria for failing attempts."
                )

        lesson_freq: Dict[str, int] = {}
        for lesson in all_lessons:
            normalized = lesson.strip().lower()
            lesson_freq[normalized] = lesson_freq.get(normalized, 0) + 1

        recurring_lessons = [
            lesson for lesson, count in lesson_freq.items()
            if count >= min(3, max(2, len(domain_experiences) // 3))
        ]
        if recurring_lessons:
            top_lesson = max(recurring_lessons, key=lambda l: lesson_freq[l])
            insights.append(
                f"{domain.value.replace('_', ' ').title()}: "
                f"Recurring lesson pattern detected: '{top_lesson}' "
                f"(appeared in {lesson_freq[top_lesson]} experiences)."
            )

        skill = self._domain_skills.get(domain)
        if skill and skill.current_level in (SkillLevel.COMPETENT, SkillLevel.PROFICIENT):
            next_level_idx = SKILL_LEVEL_ORDER[skill.current_level] + 1
            if next_level_idx < len(SKILL_LEVEL_ORDER):
                ordered = sorted(SKILL_LEVEL_ORDER.keys(), key=lambda l: SKILL_LEVEL_ORDER[l])
                next_level = ordered[next_level_idx]
                min_exp, min_success, min_quality = SKILL_LEVEL_THRESHOLDS[next_level]
                gaps = []
                if skill.experience_count < min_exp:
                    gaps.append(f"{min_exp - skill.experience_count} more experiences needed")
                if skill.success_rate < min_success:
                    gaps.append(f"success rate to {min_success:.0%}")
                if skill.average_quality < min_quality:
                    gaps.append(f"quality to {min_quality:.0%}")
                if gaps:
                    insights.append(
                        f"{domain.value.replace('_', ' ').title()}: "
                        f"Path to {next_level.value}: improve {' and '.join(gaps)}."
                    )

        return insights

    def get_stats(self) -> Dict[str, Any]:
        total = len(self._experiences)
        success_count = sum(1 for e in self._experiences if e.outcome_success)
        completion_rate = success_count / max(total, 1)

        avg_quality = (
            sum(e.quality_score for e in self._experiences) / max(total, 1)
            if total > 0
            else 0.0
        )

        domain_skill_levels: Dict[str, Dict[str, Any]] = {}
        for domain, skill in self._domain_skills.items():
            domain_skill_levels[domain.value] = {
                "level": skill.current_level.value,
                "experience_count": skill.experience_count,
                "success_rate": round(skill.success_rate, 3),
                "average_quality": round(skill.average_quality, 3),
            }

        avg_duration = self._total_duration_ms / max(self._complete_count, 1)

        return {
            "total_cycles": len(self._cycles),
            "completed_cycles": self._complete_count,
            "total_experiences": total,
            "completion_rate": round(completion_rate, 3),
            "average_quality": round(avg_quality, 3),
            "average_duration_ms": round(avg_duration, 1),
            "domain_skill_levels": domain_skill_levels,
            "replay_buffer_usage": f"{total}/{self._max_experiences}",
            "cycles_since_last_nudge": self._cycles_since_last_nudge,
        }

    @property
    def replay_buffer_size(self) -> int:
        return len(self._experiences)

    def reset(self) -> None:
        self._cycles.clear()
        self._experiences.clear()
        self._domain_skills.clear()
        self._complete_count = 0
        self._total_duration_ms = 0.0
        self._cycles_since_last_nudge = 0
        self._last_nudge_text = ""
        self._init_domain_skills()


def get_learning_cycle() -> LearningCycleEngine:
    return LearningCycleEngine.get_instance()