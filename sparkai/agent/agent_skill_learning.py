"""
SparkLabs Agent - Skill Learning and Refinement System

A skill acquisition and refinement system that models how agents learn
new capabilities through experience. Skills are defined as templates with
preconditions and effects, stored in a library, refined through usage,
and composed into complex behavior chains.

Architecture:
  SkillLearningSystem (Singleton)
    |-- SkillTemplate (preconditions, effects, parameters)
    |-- SkillLibrary (storage and retrieval of known skills)
    |-- SkillRefinementEngine (experience-based skill improvement)
    |-- SkillCompositionEngine (combining skills into chains)
"""

from __future__ import annotations

import threading
import time as _time_module
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple


class SkillDomain(Enum):
    """Domain classification for skills."""
    NAVIGATION = "navigation"
    COMBAT = "combat"
    SOCIAL = "social"
    CRAFTING = "crafting"
    EXPLORATION = "exploration"
    DIALOGUE = "dialogue"
    PUZZLE = "puzzle"
    STRATEGY = "strategy"
    PERCEPTION = "perception"
    COORDINATION = "coordination"


class SkillProficiency(Enum):
    """Proficiency level of a learned skill."""
    NOVICE = "novice"
    APPRENTICE = "apprentice"
    COMPETENT = "competent"
    PROFICIENT = "proficient"
    EXPERT = "expert"
    MASTER = "master"


class CompositionType(Enum):
    """How skills are composed together."""
    SEQUENCE = "sequence"
    PARALLEL = "parallel"
    CONDITIONAL = "conditional"
    ALTERNATIVE = "alternative"
    PIPELINE = "pipeline"


class RefinementStrategy(Enum):
    """Strategy used for skill refinement."""
    PARAMETER_TUNING = "parameter_tuning"
    PRECONDITION_RELAXATION = "precondition_relaxation"
    EFFECT_AMPLIFICATION = "effect_amplification"
    COST_REDUCTION = "cost_reduction"
    GENERALIZATION = "generalization"
    SPECIALIZATION = "specialization"


@dataclass
class SkillTemplate:
    """A skill definition with preconditions, effects, and parameters."""
    skill_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = ""
    description: str = ""
    domain: SkillDomain = SkillDomain.NAVIGATION
    preconditions: Dict[str, Any] = field(default_factory=dict)
    effects: Dict[str, Any] = field(default_factory=dict)
    parameters: Dict[str, Any] = field(default_factory=dict)
    proficiency: SkillProficiency = SkillProficiency.NOVICE
    base_cost: float = 1.0
    base_duration: float = 0.0
    success_rate: float = 0.5
    usage_count: int = 0
    refinement_count: int = 0
    created_at: float = field(default_factory=_time_module.time)
    last_used: float = field(default_factory=_time_module.time)
    tags: List[str] = field(default_factory=list)
    parent_skill_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "skill_id": self.skill_id,
            "name": self.name,
            "description": self.description,
            "domain": self.domain.value,
            "preconditions": self.preconditions,
            "effects": self.effects,
            "parameters": self.parameters,
            "proficiency": self.proficiency.value,
            "base_cost": self.base_cost,
            "base_duration": self.base_duration,
            "success_rate": self.success_rate,
            "usage_count": self.usage_count,
            "refinement_count": self.refinement_count,
            "created_at": self.created_at,
            "last_used": self.last_used,
            "tags": self.tags,
            "parent_skill_id": self.parent_skill_id,
            "metadata": self.metadata,
        }

    def proficiency_value(self) -> float:
        """Map proficiency to a numeric value."""
        mapping = {
            SkillProficiency.NOVICE: 0.2,
            SkillProficiency.APPRENTICE: 0.4,
            SkillProficiency.COMPETENT: 0.6,
            SkillProficiency.PROFICIENT: 0.8,
            SkillProficiency.EXPERT: 0.9,
            SkillProficiency.MASTER: 1.0,
        }
        return mapping.get(self.proficiency, 0.2)

    def effective_cost(self) -> float:
        return self.base_cost * (1.0 - self.proficiency_value() * 0.5)

    def effective_success_rate(self) -> float:
        return min(1.0, self.success_rate * (1.0 + self.proficiency_value() * 0.3))


class SkillLibrary:
    """
    Stores and retrieves learned skills.
    Provides domain-based indexing and similarity search.
    """

    def __init__(self) -> None:
        self._skills: Dict[str, SkillTemplate] = {}
        self._domain_index: Dict[SkillDomain, List[str]] = {}
        self._tag_index: Dict[str, List[str]] = {}
        self._lock = threading.RLock()

    def store(self, skill: SkillTemplate) -> SkillTemplate:
        """Store a skill in the library."""
        with self._lock:
            self._skills[skill.skill_id] = skill
            if skill.domain not in self._domain_index:
                self._domain_index[skill.domain] = []
            if skill.skill_id not in self._domain_index[skill.domain]:
                self._domain_index[skill.domain].append(skill.skill_id)
            for tag in skill.tags:
                if tag not in self._tag_index:
                    self._tag_index[tag] = []
                if skill.skill_id not in self._tag_index[tag]:
                    self._tag_index[tag].append(skill.skill_id)
            return skill

    def create_skill(
        self,
        name: str,
        description: str = "",
        domain: str = "navigation",
        preconditions: Optional[Dict[str, Any]] = None,
        effects: Optional[Dict[str, Any]] = None,
        parameters: Optional[Dict[str, Any]] = None,
        tags: Optional[List[str]] = None,
    ) -> SkillTemplate:
        """Create and store a new skill."""
        skill = SkillTemplate(
            name=name,
            description=description,
            domain=SkillDomain(domain),
            preconditions=preconditions or {},
            effects=effects or {},
            parameters=parameters or {},
            tags=tags or [],
        )
        return self.store(skill)

    def retrieve(self, skill_id: str) -> Optional[SkillTemplate]:
        with self._lock:
            return self._skills.get(skill_id)

    def retrieve_by_domain(self, domain: SkillDomain, proficiency: Optional[SkillProficiency] = None) -> List[SkillTemplate]:
        with self._lock:
            ids = self._domain_index.get(domain, [])
            skills = [self._skills[sid] for sid in ids if sid in self._skills]
            if proficiency:
                skills = [s for s in skills if s.proficiency == proficiency]
            return skills

    def retrieve_by_tags(self, tags: List[str]) -> List[SkillTemplate]:
        with self._lock:
            matching_ids: Set[str] = set()
            for tag in tags:
                matching_ids.update(self._tag_index.get(tag, []))
            return [self._skills[sid] for sid in matching_ids if sid in self._skills]

    def search(self, query: str, domain: Optional[SkillDomain] = None,
               limit: int = 20) -> List[SkillTemplate]:
        """Search skills by name and description similarity."""
        with self._lock:
            candidates = list(self._skills.values())
            if domain:
                candidates = [s for s in candidates if s.domain == domain]
            query_lower = query.lower()
            scored = [(s, _skill_match_score(query_lower, s)) for s in candidates]
            scored.sort(key=lambda x: x[1], reverse=True)
            return [s for s, _ in scored[:limit] if _ > 0]

    def list_domains(self) -> List[SkillDomain]:
        with self._lock:
            return list(self._domain_index.keys())

    def to_dict(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "total_skills": len(self._skills),
                "domains": {d.value: len(ids) for d, ids in self._domain_index.items()},
                "tag_count": len(self._tag_index),
            }


class SkillRefinementEngine:
    """
    Refines skills through experience and usage data.
    Adjusts parameters, relaxes preconditions, and amplifies
    effects based on successful and failed executions.
    """

    def __init__(self) -> None:
        self._refinement_history: List[Dict[str, Any]] = []
        self._lock = threading.RLock()

    def refine(
        self,
        skill: SkillTemplate,
        execution_success: bool,
        context: Optional[Dict[str, Any]] = None,
    ) -> SkillTemplate:
        """Refine a skill based on an execution outcome."""
        with self._lock:
            skill.usage_count += 1
            skill.last_used = _time_module.time()

            if execution_success:
                skill.success_rate = (
                    skill.success_rate * (skill.usage_count - 1) + 1.0
                ) / skill.usage_count
                self._apply_success_refinement(skill)
            else:
                skill.success_rate = (
                    skill.success_rate * (skill.usage_count - 1)
                ) / skill.usage_count
                self._apply_failure_adjustment(skill, context)

            skill.refinement_count += 1
            self._refinement_history.append({
                "skill_id": skill.skill_id,
                "success": execution_success,
                "new_success_rate": skill.success_rate,
                "proficiency": skill.proficiency.value,
                "timestamp": _time_module.time(),
            })
            return skill

    def _apply_success_refinement(self, skill: SkillTemplate) -> None:
        """Apply improvements from a successful execution."""
        if skill.usage_count >= 50 and skill.success_rate >= 0.95:
            skill.proficiency = SkillProficiency.MASTER
        elif skill.usage_count >= 30 and skill.success_rate >= 0.9:
            skill.proficiency = SkillProficiency.EXPERT
        elif skill.usage_count >= 20 and skill.success_rate >= 0.8:
            skill.proficiency = SkillProficiency.PROFICIENT
        elif skill.usage_count >= 10 and skill.success_rate >= 0.7:
            skill.proficiency = SkillProficiency.COMPETENT
        elif skill.usage_count >= 5 and skill.success_rate >= 0.6:
            skill.proficiency = SkillProficiency.APPRENTICE

        skill.base_cost *= 0.98
        skill.base_duration *= 0.99

    def _apply_failure_adjustment(self, skill: SkillTemplate,
                                   context: Optional[Dict[str, Any]] = None) -> None:
        """Adjust skill parameters after a failure."""
        skill.base_cost = min(skill.base_cost * 1.02, skill.base_cost * 2.0)

    def refine_by_strategy(
        self,
        skill: SkillTemplate,
        strategy: RefinementStrategy,
        magnitude: float = 0.1,
    ) -> SkillTemplate:
        """Apply a specific refinement strategy to a skill."""
        with self._lock:
            if strategy == RefinementStrategy.PARAMETER_TUNING:
                for key in skill.parameters:
                    if isinstance(skill.parameters[key], (int, float)):
                        skill.parameters[key] *= (1.0 + magnitude)
            elif strategy == RefinementStrategy.PRECONDITION_RELAXATION:
                relaxed = {}
                for key, value in skill.preconditions.items():
                    if isinstance(value, (int, float)):
                        relaxed[key] = value * (1.0 - magnitude)
                    else:
                        relaxed[key] = value
                skill.preconditions = relaxed
            elif strategy == RefinementStrategy.EFFECT_AMPLIFICATION:
                for key in skill.effects:
                    if isinstance(skill.effects[key], (int, float)):
                        skill.effects[key] *= (1.0 + magnitude)
            elif strategy == RefinementStrategy.COST_REDUCTION:
                skill.base_cost *= (1.0 - magnitude)
            elif strategy == RefinementStrategy.GENERALIZATION:
                skill.tags.append("generalized")
            elif strategy == RefinementStrategy.SPECIALIZATION:
                skill.tags.append("specialized")

            skill.refinement_count += 1
            return skill

    def to_dict(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "total_refinements": len(self._refinement_history),
                "recent": self._refinement_history[-10:],
            }


class SkillCompositionEngine:
    """
    Combines multiple skills into complex behavior chains.
    Supports sequential, parallel, conditional, and pipeline
    composition patterns.
    """

    def __init__(self) -> None:
        self._compositions: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.RLock()

    def compose_sequence(
        self,
        name: str,
        skills: List[SkillTemplate],
        library: SkillLibrary,
    ) -> Dict[str, Any]:
        """Compose skills into a sequential chain."""
        with self._lock:
            composition = {
                "composition_id": str(uuid.uuid4().hex),
                "name": name,
                "type": CompositionType.SEQUENCE.value,
                "skills": [s.skill_id for s in skills],
                "total_cost": sum(s.effective_cost() for s in skills),
                "total_duration": sum(s.base_duration for s in skills),
                "estimated_success_rate": _compute_chain_success_rate(skills),
                "created_at": _time_module.time(),
            }
            self._compositions[composition["composition_id"]] = composition
            return composition

    def compose_conditional(
        self,
        name: str,
        primary: SkillTemplate,
        fallback: SkillTemplate,
        condition_key: str,
        library: SkillLibrary,
    ) -> Dict[str, Any]:
        """Compose skills with a conditional branch."""
        with self._lock:
            composition = {
                "composition_id": str(uuid.uuid4().hex),
                "name": name,
                "type": CompositionType.CONDITIONAL.value,
                "primary_skill": primary.skill_id,
                "fallback_skill": fallback.skill_id,
                "condition_key": condition_key,
                "estimated_success_rate": max(primary.effective_success_rate(),
                                               fallback.effective_success_rate()),
                "created_at": _time_module.time(),
            }
            self._compositions[composition["composition_id"]] = composition
            return composition

    def compose_parallel(
        self,
        name: str,
        skills: List[SkillTemplate],
        library: SkillLibrary,
    ) -> Dict[str, Any]:
        """Compose skills for parallel execution."""
        with self._lock:
            composition = {
                "composition_id": str(uuid.uuid4().hex),
                "name": name,
                "type": CompositionType.PARALLEL.value,
                "skills": [s.skill_id for s in skills],
                "total_cost": sum(s.effective_cost() for s in skills),
                "max_duration": max((s.base_duration for s in skills), default=0.0),
                "estimated_success_rate": _compute_parallel_success_rate(skills),
                "created_at": _time_module.time(),
            }
            self._compositions[composition["composition_id"]] = composition
            return composition

    def get_composition(self, composition_id: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            return self._compositions.get(composition_id)

    def list_compositions(self) -> List[Dict[str, Any]]:
        with self._lock:
            return list(self._compositions.values())

    def to_dict(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "composition_count": len(self._compositions),
                "compositions": list(self._compositions.values()),
            }


def _skill_match_score(query: str, skill: SkillTemplate) -> float:
    """Compute a match score between a query and a skill."""
    name_lower = skill.name.lower()
    desc_lower = skill.description.lower()
    score = 0.0
    query_words = query.split()
    for word in query_words:
        if word in name_lower:
            score += 0.3
        if word in desc_lower:
            score += 0.1
    return min(score, 1.0)


def _compute_chain_success_rate(skills: List[SkillTemplate]) -> float:
    if not skills:
        return 1.0
    product = 1.0
    for s in skills:
        product *= s.effective_success_rate()
    return product


def _compute_parallel_success_rate(skills: List[SkillTemplate]) -> float:
    if not skills:
        return 1.0
    failure_product = 1.0
    for s in skills:
        failure_product *= (1.0 - s.effective_success_rate())
    return 1.0 - failure_product


class SkillLearningSystem:
    """
    Skill acquisition and refinement system for AI agents.

    Models how agents learn new capabilities through experience,
    refine skills based on usage, and compose them into complex
    behavior chains.
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
        self._library = SkillLibrary()
        self._refinement_engine = SkillRefinementEngine()
        self._composition_engine = SkillCompositionEngine()

    @classmethod
    def get_instance(cls) -> "SkillLearningSystem":
        return cls()

    @property
    def library(self) -> SkillLibrary:
        return self._library

    @property
    def refinement(self) -> SkillRefinementEngine:
        return self._refinement_engine

    @property
    def composition(self) -> SkillCompositionEngine:
        return self._composition_engine

    def learn_skill(
        self,
        name: str,
        description: str = "",
        domain: str = "navigation",
        preconditions: Optional[Dict[str, Any]] = None,
        effects: Optional[Dict[str, Any]] = None,
        parameters: Optional[Dict[str, Any]] = None,
        tags: Optional[List[str]] = None,
    ) -> SkillTemplate:
        """Acquire a new skill."""
        return self._library.create_skill(
            name=name,
            description=description,
            domain=domain,
            preconditions=preconditions,
            effects=effects,
            parameters=parameters,
            tags=tags,
        )

    def execute_and_refine(
        self,
        skill_id: str,
        success: bool,
        context: Optional[Dict[str, Any]] = None,
    ) -> Optional[SkillTemplate]:
        """Record a skill execution and refine the skill."""
        skill = self._library.retrieve(skill_id)
        if not skill:
            return None
        return self._refinement_engine.refine(skill, success, context)

    def compose_sequence(
        self,
        name: str,
        skill_ids: List[str],
    ) -> Optional[Dict[str, Any]]:
        """Compose a sequence of skills into a chain."""
        skills = []
        for sid in skill_ids:
            skill = self._library.retrieve(sid)
            if skill:
                skills.append(skill)
        if not skills:
            return None
        return self._composition_engine.compose_sequence(name, skills, self._library)

    def get_stats(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "library": self._library.to_dict(),
                "refinement": self._refinement_engine.to_dict(),
                "composition": self._composition_engine.to_dict(),
            }


_global_skill_learning: Optional[SkillLearningSystem] = None


def get_skill_learning() -> SkillLearningSystem:
    global _global_skill_learning
    if _global_skill_learning is None:
        _global_skill_learning = SkillLearningSystem()
    return _global_skill_learning