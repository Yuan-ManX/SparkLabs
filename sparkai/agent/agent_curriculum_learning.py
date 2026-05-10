"""
SparkLabs Agent - Curriculum Learning Engine

Progressive difficulty orchestration for player skill development.
Constructs adaptive learning paths that dynamically adjust challenge
levels based on player performance, ensuring optimal engagement
through scaffolding and spaced repetition principles.

Architecture:
  CurriculumLearningEngine
    |-- SkillGraph (interconnected skill dependency network)
    |-- DifficultyOptimizer (performance-based challenge tuning)
    |-- SessionPlanner (multi-session progression scheduling)
    |-- MilestoneTracker (competency checkpoint evaluation)
    |-- AdaptationController (real-time difficulty modulation)

Strategies:
  - SCAFFOLDED: guided progression with explicit support
  - EXPLORATORY: open-ended discovery with gradual unlocks
  - MASTERY: competency-gated advancement thresholds
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


class LearningStrategy(Enum):
    SCAFFOLDED = "scaffolded"
    EXPLORATORY = "exploratory"
    MASTERY = "mastery"


class SkillLevel(Enum):
    NOVICE = "novice"
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"
    EXPERT = "expert"


@dataclass
class SkillNode:
    skill_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    name: str = ""
    description: str = ""
    level: SkillLevel = SkillLevel.NOVICE
    prerequisites: List[str] = field(default_factory=list)
    unlocks: List[str] = field(default_factory=list)
    difficulty_baseline: float = 1.0
    mastery_threshold: float = 0.8
    current_proficiency: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "skill_id": self.skill_id,
            "name": self.name,
            "level": self.level.value,
            "prerequisites": self.prerequisites,
            "difficulty_baseline": self.difficulty_baseline,
            "proficiency": self.current_proficiency,
        }


@dataclass
class LearningSession:
    session_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    target_skills: List[str] = field(default_factory=list)
    strategy: LearningStrategy = LearningStrategy.SCAFFOLDED
    difficulty_modifier: float = 1.0
    completed_tasks: List[str] = field(default_factory=list)
    performance_scores: List[float] = field(default_factory=list)
    started_at: float = 0.0
    ended_at: Optional[float] = None

    def __post_init__(self):
        if self.started_at == 0.0:
            self.started_at = time.time()

    def average_performance(self) -> float:
        if not self.performance_scores:
            return 0.0
        return sum(self.performance_scores) / len(self.performance_scores)


@dataclass
class Milestone:
    milestone_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    name: str = ""
    required_skills: List[str] = field(default_factory=list)
    proficiency_threshold: float = 0.8
    achieved: bool = False
    achieved_at: Optional[float] = None


class CurriculumLearningEngine:
    _instance: Optional[CurriculumLearningEngine] = None

    def __init__(self):
        self._skills: Dict[str, SkillNode] = {}
        self._sessions: List[LearningSession] = []
        self._milestones: Dict[str, Milestone] = {}
        self._active_session: Optional[LearningSession] = None
        self._strategy: LearningStrategy = LearningStrategy.SCAFFOLDED
        self._session_count: int = 0

    @classmethod
    def get_instance(cls) -> CurriculumLearningEngine:
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def register_skill(self, skill: SkillNode) -> str:
        self._skills[skill.skill_id] = skill
        return skill.skill_id

    def define_prerequisite(self, skill_id: str, prereq_id: str) -> bool:
        if skill_id in self._skills and prereq_id in self._skills:
            if prereq_id not in self._skills[skill_id].prerequisites:
                self._skills[skill_id].prerequisites.append(prereq_id)
            if skill_id not in self._skills[prereq_id].unlocks:
                self._skills[prereq_id].unlocks.append(skill_id)
            return True
        return False

    def set_strategy(self, strategy: LearningStrategy):
        self._strategy = strategy

    def start_session(
        self,
        target_skills: List[str],
        strategy: Optional[LearningStrategy] = None,
    ) -> LearningSession:
        session = LearningSession(
            target_skills=target_skills,
            strategy=strategy or self._strategy,
        )
        session.difficulty_modifier = self._calculate_initial_difficulty(target_skills)
        self._active_session = session
        self._sessions.append(session)
        self._session_count += 1
        return session

    def _calculate_initial_difficulty(self, skill_ids: List[str]) -> float:
        if not skill_ids:
            return 1.0
        proficiency_sum = 0.0
        for sid in skill_ids:
            skill = self._skills.get(sid)
            if skill:
                proficiency_sum += skill.current_proficiency
        avg_proficiency = proficiency_sum / len(skill_ids)
        base = 1.0
        modifiers = {
            LearningStrategy.SCAFFOLDED: 0.7,
            LearningStrategy.EXPLORATORY: 1.3,
            LearningStrategy.MASTERY: max(1.0, 1.5 - avg_proficiency),
        }
        return base * modifiers.get(self._strategy, 1.0)

    def record_performance(
        self, skill_id: str, score: float, task_id: str = ""
    ) -> Optional[float]:
        skill = self._skills.get(skill_id)
        if skill is None:
            return None

        skill.current_proficiency = 0.8 * skill.current_proficiency + 0.2 * score

        if self._active_session:
            self._active_session.performance_scores.append(score)
            if task_id:
                self._active_session.completed_tasks.append(task_id)
            avg = self._active_session.average_performance()

            if self._strategy == LearningStrategy.SCAFFOLDED:
                self._active_session.difficulty_modifier = max(0.5, min(2.0, avg))
            elif self._strategy == LearningStrategy.MASTERY:
                if avg >= skill.mastery_threshold:
                    self._active_session.difficulty_modifier *= 1.2

        self._check_milestones()
        return skill.current_proficiency

    def _check_milestones(self):
        for milestone in self._milestones.values():
            if milestone.achieved:
                continue
            all_met = True
            for skill_id in milestone.required_skills:
                skill = self._skills.get(skill_id)
                if skill is None or skill.current_proficiency < milestone.proficiency_threshold:
                    all_met = False
                    break
            if all_met:
                milestone.achieved = True
                milestone.achieved_at = time.time()

    def define_milestone(self, milestone: Milestone) -> str:
        self._milestones[milestone.milestone_id] = milestone
        return milestone.milestone_id

    def get_skill_graph(self) -> Dict[str, Any]:
        graph = {}
        for sid, skill in self._skills.items():
            graph[sid] = {
                "name": skill.name,
                "level": skill.level.value,
                "proficiency": skill.current_proficiency,
                "prerequisites": skill.prerequisites,
                "unlocks": skill.unlocks,
            }
        return graph

    def get_recommended_skills(self, count: int = 3) -> List[SkillNode]:
        available = []
        for skill in self._skills.values():
            if skill.current_proficiency >= skill.mastery_threshold:
                for unlock_id in skill.unlocks:
                    unlocked = self._skills.get(unlock_id)
                    if unlocked and unlocked.current_proficiency < 0.5:
                        available.append(unlocked)
        sorted_skills = sorted(available, key=lambda s: s.current_proficiency)
        return sorted_skills[:count]

    def end_session(self) -> Optional[Dict[str, Any]]:
        if self._active_session is None:
            return None
        self._active_session.ended_at = time.time()
        session = self._active_session
        self._active_session = None
        return {
            "session_id": session.session_id,
            "average_performance": session.average_performance(),
            "completed_tasks": len(session.completed_tasks),
            "duration": session.ended_at - session.started_at,
        }

    def get_stats(self) -> Dict[str, Any]:
        proficiency_values = [s.current_proficiency for s in self._skills.values()]
        avg_proficiency = sum(proficiency_values) / len(proficiency_values) if proficiency_values else 0.0
        return {
            "total_skills": len(self._skills),
            "total_sessions": self._session_count,
            "active_strategy": self._strategy.value,
            "average_proficiency": round(avg_proficiency, 3),
            "milestones_achieved": sum(1 for m in self._milestones.values() if m.achieved),
            "total_milestones": len(self._milestones),
        }


def get_curriculum_learning() -> CurriculumLearningEngine:
    return CurriculumLearningEngine.get_instance()