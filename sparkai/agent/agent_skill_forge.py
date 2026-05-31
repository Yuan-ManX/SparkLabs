"""
SparkLabs Agent - Skill Forge

An autonomous skill creation and procedural memory system 
L4 Skills layer. The SkillForge enables dynamic discovery,
creation, improvement, execution, and consolidation of procedural skills
across all game development domains.

Architecture:
  SkillForge (singleton)
    |-- SkillTemplate (procedural skill blueprint with versioned steps)
    |-- SkillSession (execution/creation session tracking)
    |-- SkillCategory (domain taxonomy: GAME_LOGIC, AI_BEHAVIOR, etc.)
    |-- SkillStatus (lifecycle: CREATED -> IMPROVING -> STABLE -> DEPRECATED)

Core Capabilities:
  - create_skill: Synthesize a new procedural skill from task description and result
  - improve_skill: Evolve a skill based on usage patterns and success metrics
  - execute_skill: Run a stored multi-step workflow against a game context
  - discover_skills: Search and rank skills by contextual relevance
  - get_skill_stats: Aggregate analytics across the skill ecosystem
  - consolidate_skills: Merge semantically similar skills to reduce fragmentation

The forge maintains a growing library of domain-specific procedural knowledge
that becomes more reliable and efficient with each execution cycle.
"""

from __future__ import annotations

import json
import math
import re
import threading
import time
import uuid
from collections import Counter
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Sequence, Tuple

_time_module = time


class SkillCategory(Enum):
    GAME_LOGIC = "game_logic"
    ASSET_GENERATION = "asset_generation"
    LEVEL_DESIGN = "level_design"
    UI_LAYOUT = "ui_layout"
    AI_BEHAVIOR = "ai_behavior"
    ANIMATION = "animation"
    PHYSICS = "physics"
    AUDIO = "audio"
    NETWORKING = "networking"
    UTILITY = "utility"


class SkillStatus(Enum):
    CREATED = "created"
    IMPROVING = "improving"
    STABLE = "stable"
    DEPRECATED = "deprecated"


class SessionOutcome(Enum):
    SUCCESS = "success"
    PARTIAL = "partial"
    FAILURE = "failure"


# ------------------------------------------------------------------
# Dataclasses
# ------------------------------------------------------------------


@dataclass
class SkillTemplate:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = ""
    category: SkillCategory = SkillCategory.UTILITY
    description: str = ""
    steps: List[Dict[str, Any]] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    version: str = "1.0"
    usage_count: int = 0
    success_rate: float = 0.0
    created_at: float = field(default_factory=_time_module.time)
    updated_at: float = field(default_factory=_time_module.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "category": self.category.value,
            "description": self.description,
            "step_count": len(self.steps),
            "steps": self.steps,
            "tags": self.tags,
            "version": self.version,
            "usage_count": self.usage_count,
            "success_rate": round(self.success_rate, 4),
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    def bump_version(self) -> str:
        parts = self.version.split(".")
        minor = int(parts[-1]) + 1 if len(parts) > 1 else 1
        if len(parts) >= 2:
            parts[-1] = str(minor)
        else:
            parts.append(str(minor))
        self.version = ".".join(parts)
        self.updated_at = _time_module.time()
        return self.version

    def compute_complexity_score(self) -> float:
        if not self.steps:
            return 0.0
        total_actions = sum(len(step.get("actions", [])) for step in self.steps)
        param_count = sum(len(step.get("params", {})) for step in self.steps)
        depth = len(self.steps)
        raw = math.log1p(depth * 0.5 + total_actions * 0.3 + param_count * 0.2)
        return round(min(1.0, raw / 4.0), 4)

    def compute_quality_score(self) -> float:
        usage_weight = min(self.usage_count / 50.0, 1.0)
        recency_weight = 1.0
        if self.updated_at > 0:
            hours_since = (_time_module.time() - self.updated_at) / 3600.0
            recency_weight = max(0.3, 1.0 - hours_since / 720.0)
        return round(self.success_rate * 0.55 + usage_weight * 0.30 + recency_weight * 0.15, 4)


@dataclass
class SkillSession:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    skill_id: str = ""
    status: SkillStatus = SkillStatus.CREATED
    outcome: SessionOutcome = SessionOutcome.SUCCESS
    result_json: str = "{}"
    duration_ms: float = 0.0
    error_message: str = ""
    created_at: float = field(default_factory=_time_module.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "skill_id": self.skill_id,
            "status": self.status.value,
            "outcome": self.outcome.value,
            "result_json": self.result_json[:500],
            "duration_ms": self.duration_ms,
            "error_message": self.error_message[:200],
            "created_at": self.created_at,
        }


# ------------------------------------------------------------------
# Skill Forge Singleton
# ------------------------------------------------------------------


class SkillForge:
    """
    Autonomous skill creation and procedural memory system.

    Maintains a library of procedural skill blueprints organized by
    game development domain. Skills are created from task results,
    improved through usage pattern analysis, executed as multi-step
    workflows, and consolidated to eliminate redundancy.

    Usage:
        forge = SkillForge.get_instance()
        skill = forge.create_skill(
            task_description="Design a combat system for an RPG",
            task_result={"mechanics": ["turn-based", "elemental"], "systems": 4},
            category=SkillCategory.GAME_LOGIC,
        )
        forge.execute_skill(skill.id, context={"genre": "rpg"})
    """

    _instance: Optional[SkillForge] = None
    _lock: threading.RLock = threading.RLock()

    _MAX_SKILLS: int = 200
    _MAX_SESSIONS: int = 1000
    _MIN_SIMILARITY_FOR_CONSOLIDATION: float = 0.75
    _IMPROVE_THRESHOLD_USAGES: int = 5
    _DEPRECATE_THRESHOLD_FAILURES: int = 10
    _DEPRECATE_MIN_SUCCESS_RATE: float = 0.25

    def __new__(cls) -> SkillForge:
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    instance = super().__new__(cls)
                    instance._initialized = False
                    cls._instance = instance
        return cls._instance

    @classmethod
    def get_instance(cls) -> SkillForge:
        if cls._instance is None:
            cls()
        return cls._instance

    def __init__(self) -> None:
        if self._initialized:
            return
        self._initialized = True

        self._skills: Dict[str, SkillTemplate] = {}
        self._sessions: Dict[str, SkillSession] = {}
        self._skill_sessions: Dict[str, List[str]] = {}
        self._tag_index: Dict[str, List[str]] = {}
        self._category_index: Dict[str, List[str]] = {}
        for cat in SkillCategory:
            self._category_index[cat.value] = []

        self._total_skills_created: int = 0
        self._total_sessions_recorded: int = 0

    # ------------------------------------------------------------------
    # Skill Creation
    # ------------------------------------------------------------------

    def create_skill(
        self,
        task_description: str,
        task_result: Dict[str, Any],
        category: SkillCategory = SkillCategory.UTILITY,
        tags: Optional[List[str]] = None,
        steps_override: Optional[List[Dict[str, Any]]] = None,
    ) -> SkillTemplate:
        with self._lock:
            self._enforce_max_skills()

            generated_steps = steps_override or self._synthesize_steps(
                task_description, task_result, category
            )

            name = self._derive_skill_name(task_description, category)
            description = self._summarize_description(task_description, task_result)

            skill = SkillTemplate(
                name=name,
                category=category,
                description=description,
                steps=generated_steps,
                tags=tags or self._extract_tags(task_description, category),
                success_rate=1.0,
                usage_count=1,
            )

            self._skills[skill.id] = skill
            self._index_skill(skill)
            self._total_skills_created += 1

            session = SkillSession(
                skill_id=skill.id,
                status=SkillStatus.CREATED,
                outcome=SessionOutcome.SUCCESS,
                result_json=json.dumps(task_result, default=str)[:2000],
                duration_ms=0.0,
            )
            self._sessions[session.id] = session
            self._skill_sessions.setdefault(skill.id, []).append(session.id)
            self._total_sessions_recorded += 1

            return skill

    # ------------------------------------------------------------------
    # Skill Improvement
    # ------------------------------------------------------------------

    def improve_skill(
        self,
        skill_id: str,
        execution_result: Dict[str, Any],
        success: bool,
        duration_ms: float = 0.0,
        error: Optional[str] = None,
    ) -> Optional[SkillTemplate]:
        with self._lock:
            skill = self._skills.get(skill_id)
            if skill is None:
                return None

            prev_success_rate = skill.success_rate
            skill.usage_count += 1
            total_success = prev_success_rate * (skill.usage_count - 1) + (1.0 if success else 0.0)
            skill.success_rate = total_success / skill.usage_count
            skill.updated_at = _time_module.time()

            outcome = SessionOutcome.SUCCESS if success else SessionOutcome.FAILURE
            session = SkillSession(
                skill_id=skill_id,
                status=SkillStatus.IMPROVING,
                outcome=outcome,
                result_json=json.dumps(execution_result, default=str)[:2000],
                duration_ms=duration_ms,
                error_message=error or "",
            )
            self._sessions[session.id] = session
            self._skill_sessions.setdefault(skill_id, []).append(session.id)
            self._total_sessions_recorded += 1

            if skill.usage_count >= self._IMPROVE_THRESH_USAGES:
                self._apply_improvements(skill, session)

            if (
                skill.usage_count >= self._DEPRECATE_THRESHOLD_FAILURES
                and skill.success_rate < self._DEPRECATE_MIN_SUCCESS_RATE
            ):
                skill.status = SkillStatus.DEPRECATED
                return skill

            return skill

    def _apply_improvements(self, skill: SkillTemplate, session: SkillSession) -> None:
        adjustments: List[Dict[str, Any]] = []

        if skill.success_rate < 0.6 and len(skill.steps) > 2:
            slowest_step = max(
                range(len(skill.steps)),
                key=lambda i: skill.steps[i].get("estimated_ms", 0),
                default=None,
            )
            if slowest_step is not None:
                skill.steps[slowest_step]["priority"] = "review"
                adjustments.append({
                    "type": "flag_slow_step",
                    "step_index": slowest_step,
                    "reason": "performance_bottleneck",
                })

        if session.duration_ms > 10000 and len(skill.steps) > 1:
            for step in skill.steps:
                if step.get("parallelizable", False):
                    step["strategy"] = "parallel"
                    adjustments.append({
                        "type": "enable_parallel",
                        "step_name": step.get("name", ""),
                        "reason": "reduce_latency",
                    })

        if skill.success_rate < 0.5 and skill.usage_count >= 8:
            skill.steps.insert(0, {
                "name": "pre_validation",
                "description": "Validate inputs and context before execution",
                "actions": ["check_prerequisites", "validate_context", "prepare_environment"],
                "params": {"strict_mode": True},
                "estimated_ms": 500,
                "priority": "critical",
            })
            adjustments.append({
                "type": "add_validation_gate",
                "reason": "success_rate_recovery",
            })

        if adjustments:
            skill.bump_version()

    # ------------------------------------------------------------------
    # Skill Execution
    # ------------------------------------------------------------------

    def execute_skill(
        self,
        skill_id: str,
        context: Optional[Dict[str, Any]] = None,
        dry_run: bool = False,
    ) -> Dict[str, Any]:
        with self._lock:
            skill = self._skills.get(skill_id)
            if skill is None:
                return {"success": False, "error": f"Skill '{skill_id}' not found"}

            start_time = _time_module.time()
            step_results: List[Dict[str, Any]] = []
            total_actions = 0

            for i, step in enumerate(skill.steps):
                step_start = _time_module.time()
                actions = step.get("actions", [])
                step_result = self._execute_step(skill, step, i, context or {}, dry_run)
                step_duration = (_time_module.time() - step_start) * 1000.0
                step_result["duration_ms"] = round(step_duration, 2)
                step_results.append(step_result)
                total_actions += len(actions)

            total_duration_ms = (_time_module.time() - start_time) * 1000.0

            success = all(r.get("status") == "completed" for r in step_results)
            outcome = SessionOutcome.SUCCESS if success else SessionOutcome.PARTIAL

            session = SkillSession(
                skill_id=skill_id,
                status=SkillStatus.STABLE if success else SkillStatus.IMPROVING,
                outcome=outcome,
                result_json=json.dumps(step_results, default=str)[:2000],
                duration_ms=total_duration_ms,
            )
            self._sessions[session.id] = session
            self._skill_sessions.setdefault(skill_id, []).append(session.id)
            self._total_sessions_recorded += 1

            return {
                "success": success,
                "skill_id": skill_id,
                "skill_name": skill.name,
                "category": skill.category.value,
                "total_steps": len(skill.steps),
                "total_actions": total_actions,
                "duration_ms": round(total_duration_ms, 2),
                "step_results": step_results,
                "session_id": session.id,
            }

    def _execute_step(
        self,
        skill: SkillTemplate,
        step: Dict[str, Any],
        step_index: int,
        context: Dict[str, Any],
        dry_run: bool,
    ) -> Dict[str, Any]:
        step_name = step.get("name", f"step_{step_index}")
        actions = step.get("actions", [])

        if dry_run:
            return {
                "step_index": step_index,
                "step_name": step_name,
                "status": "dry_run",
                "actions_planned": len(actions),
                "action_list": actions,
            }

        executed: List[str] = []
        for action in actions:
            if isinstance(action, str):
                executed.append(action)
            elif isinstance(action, dict):
                executed.append(action.get("name", str(action)))

        return {
            "step_index": step_index,
            "step_name": step_name,
            "status": "completed",
            "actions_executed": len(executed),
            "action_log": executed,
            "params_used": list(step.get("params", {}).keys()),
        }

    # ------------------------------------------------------------------
    # Skill Discovery
    # ------------------------------------------------------------------

    def discover_skills(
        self,
        query: str = "",
        category: Optional[SkillCategory] = None,
        tags: Optional[List[str]] = None,
        min_success_rate: float = 0.0,
        limit: int = 20,
    ) -> List[SkillTemplate]:
        candidates: List[SkillTemplate] = []

        if category is not None:
            candidates = self._get_by_category(category)
        else:
            candidates = list(self._skills.values())

        if query:
            candidates = self._rank_by_relevance(candidates, query)

        if tags:
            tag_ids: set = set()
            for tag in tags:
                tag_ids.update(self._tag_index.get(tag.lower(), []))
            if tag_ids:
                scored: List[Tuple[SkillTemplate, int]] = []
                for skill in candidates:
                    match_count = sum(1 for t in tags if t.lower() in [tt.lower() for tt in skill.tags])
                    if match_count > 0:
                        scored.append((skill, match_count))
                scored.sort(key=lambda x: x[1], reverse=True)
                candidates = [s for s, _ in scored]

        if min_success_rate > 0:
            candidates = [s for s in candidates if s.success_rate >= min_success_rate]

        candidates.sort(key=lambda s: s.compute_quality_score(), reverse=True)
        return candidates[:limit]

    def _rank_by_relevance(self, candidates: List[SkillTemplate], query: str) -> List[SkillTemplate]:
        if not candidates:
            return candidates

        query_lower = query.lower()
        query_terms: List[str] = re.findall(r"[a-zA-Z_]+", query_lower)

        scored: List[Tuple[SkillTemplate, float]] = []
        for skill in candidates:
            score = 0.0

            name_lower = skill.name.lower()
            desc_lower = skill.description.lower()

            exact_name = 3.0 if query_lower == name_lower else 0.0
            name_contains = 2.0 if query_lower in name_lower else 0.0
            desc_contains = 1.0 if query_lower in desc_lower else 0.0

            term_matches = 0
            for term in query_terms:
                if term in name_lower:
                    term_matches += 2
                elif term in desc_lower:
                    term_matches += 1
                elif any(term in tag.lower() for tag in skill.tags):
                    term_matches += 1
                elif term in skill.category.value:
                    term_matches += 1

            tag_score = 0.0
            for term in query_terms:
                for tag in skill.tags:
                    if term in tag.lower():
                        tag_score += 0.5

            quality = skill.compute_quality_score()

            score = exact_name + name_contains + desc_contains + term_matches * 0.5 + tag_score + quality * 0.5
            scored.append((skill, score))

        scored.sort(key=lambda x: x[1], reverse=True)
        return [s for s, _ in scored]

    # ------------------------------------------------------------------
    # Skill Statistics
    # ------------------------------------------------------------------

    def get_skill_stats(self) -> Dict[str, Any]:
        with self._lock:
            total = len(self._skills)
            if total == 0:
                return self._empty_stats()

            by_category: Dict[str, int] = {}
            by_status: Dict[str, int] = {}
            all_rates: List[float] = []
            all_usages: List[int] = []
            all_complexities: List[float] = []

            for skill in self._skills.values():
                cat = skill.category.value
                by_category[cat] = by_category.get(cat, 0) + 1
                # skill.status does not exist on SkillTemplate per the spec - 
                # derive from success_rate heuristics
                status = self._derive_status(skill)
                by_status[status] = by_status.get(status, 0) + 1
                all_rates.append(skill.success_rate)
                all_usages.append(skill.usage_count)
                all_complexities.append(skill.compute_complexity_score())

            avg_success = sum(all_rates) / total
            avg_usage = sum(all_usages) / total
            avg_complexity = sum(all_complexities) / total

            sorted_rates = sorted(all_rates)
            n = len(sorted_rates)
            if n % 2 == 1:
                median_success = sorted_rates[n // 2]
            else:
                median_success = (sorted_rates[n // 2 - 1] + sorted_rates[n // 2]) / 2.0

            top_skills = sorted(
                self._skills.values(),
                key=lambda s: s.compute_quality_score(),
                reverse=True,
            )[:5]

            return {
                "total_skills": total,
                "total_skills_created": self._total_skills_created,
                "total_sessions": len(self._sessions),
                "total_sessions_recorded": self._total_sessions_recorded,
                "by_category": by_category,
                "by_derived_status": by_status,
                "avg_success_rate": round(avg_success, 4),
                "median_success_rate": round(median_success, 4),
                "avg_usage_count": round(avg_usage, 2),
                "avg_complexity_score": round(avg_complexity, 4),
                "top_skills": [s.to_dict() for s in top_skills],
                "skill_count_limit": self._MAX_SKILLS,
            }

    def _derive_status(self, skill: SkillTemplate) -> str:
        if skill.success_rate < self._DEPRECATE_MIN_SUCCESS_RATE and skill.usage_count >= self._DEPRECATE_THRESHOLD_FAILURES:
            return SkillStatus.DEPRECATED.value
        if skill.usage_count >= 20 and skill.success_rate >= 0.85:
            return SkillStatus.STABLE.value
        if skill.usage_count >= self._IMPROVE_THRESH_USAGES:
            return SkillStatus.IMPROVING.value
        return SkillStatus.CREATED.value

    def _empty_stats(self) -> Dict[str, Any]:
        return {
            "total_skills": 0,
            "total_skills_created": 0,
            "total_sessions": 0,
            "total_sessions_recorded": 0,
            "by_category": {},
            "by_derived_status": {},
            "avg_success_rate": 0.0,
            "median_success_rate": 0.0,
            "avg_usage_count": 0.0,
            "avg_complexity_score": 0.0,
            "top_skills": [],
            "skill_count_limit": self._MAX_SKILLS,
        }

    # ------------------------------------------------------------------
    # Skill Consolidation
    # ------------------------------------------------------------------

    def consolidate_skills(
        self,
        category: Optional[SkillCategory] = None,
        dry_run: bool = True,
    ) -> Dict[str, Any]:
        with self._lock:
            pool = (
                self._get_by_category(category)
                if category is not None
                else list(self._skills.values())
            )

            if len(pool) < 2:
                return {"consolidated": 0, "candidates": [], "message": "Not enough skills to consolidate"}

            groups = self._cluster_similar_skills(pool)
            merge_candidates: List[Dict[str, Any]] = []

            for group in groups:
                if len(group) < 2:
                    continue

                merged = self._merge_skill_group(group, dry_run)
                if merged is not None:
                    merge_candidates.append(merged)

            if dry_run:
                return {
                    "consolidated": 0,
                    "candidate_groups": len(merge_candidates),
                    "candidates": merge_candidates,
                    "message": f"Dry run: {len(merge_candidates)} groups identified for consolidation",
                }

            consolidated_count = 0
            for candidate in merge_candidates:
                if self._perform_merge(candidate):
                    consolidated_count += 1

            return {
                "consolidated": consolidated_count,
                "candidates": merge_candidates,
                "message": f"Consolidated {consolidated_count} skill groups",
            }

    def _cluster_similar_skills(self, skills: List[SkillTemplate]) -> List[List[SkillTemplate]]:
        if len(skills) <= 1:
            return [skills]

        groups: List[List[SkillTemplate]] = []
        remaining = list(skills)

        while remaining:
            seed = remaining.pop(0)
            group = [seed]

            i = 0
            while i < len(remaining):
                sim = self._compute_semantic_similarity(seed, remaining[i])
                if sim >= self._MIN_SIMILARITY_FOR_CONSOLIDATION:
                    group.append(remaining.pop(i))
                else:
                    i += 1

            groups.append(group)

        return groups

    def _compute_semantic_similarity(self, a: SkillTemplate, b: SkillTemplate) -> float:
        if a.category != b.category:
            return 0.0

        score = 0.0

        name_words_a: set = set(re.findall(r"[a-z]+", a.name.lower()))
        name_words_b: set = set(re.findall(r"[a-z]+", b.name.lower()))
        if name_words_a and name_words_b:
            name_overlap = len(name_words_a & name_words_b) / max(len(name_words_a | name_words_b), 1)
            score += name_overlap * 0.35

        tags_a: set = {t.lower() for t in a.tags}
        tags_b: set = {t.lower() for t in b.tags}
        if tags_a and tags_b:
            tag_overlap = len(tags_a & tags_b) / max(len(tags_a | tags_b), 1)
            score += tag_overlap * 0.35

        desc_words_a: set = set(re.findall(r"[a-z]+", a.description.lower()))
        desc_words_b: set = set(re.findall(r"[a-z]+", b.description.lower()))
        if desc_words_a and desc_words_b:
            desc_overlap = len(desc_words_a & desc_words_b) / max(len(desc_words_a | desc_words_b), 1)
            score += desc_overlap * 0.15

        steps_a = sum(len(s.get("actions", [])) for s in a.steps)
        steps_b = sum(len(s.get("actions", [])) for s in b.steps)
        if max(steps_a, steps_b) > 0:
            step_sim = 1.0 - abs(steps_a - steps_b) / max(steps_a, steps_b, 1)
            score += step_sim * 0.15

        return round(score, 4)

    def _merge_skill_group(
        self, group: List[SkillTemplate], dry_run: bool
    ) -> Optional[Dict[str, Any]]:
        if len(group) < 2:
            return None

        primary = max(group, key=lambda s: s.compute_quality_score())
        others = [s for s in group if s.id != primary.id]

        merged_tags = list(set(sum([s.tags for s in group], [])))

        merged_steps = list(primary.steps)
        seen_step_names: set = {s.get("name", "") for s in merged_steps}
        for other in others:
            for step in other.steps:
                name = step.get("name", "")
                if name and name not in seen_step_names:
                    merged_steps.append(step)
                    seen_step_names.add(name)

        total_usage = sum(s.usage_count for s in group)
        weighted_success = sum(s.success_rate * s.usage_count for s in group) / max(total_usage, 1)

        return {
            "primary_skill_id": primary.id,
            "primary_skill_name": primary.name,
            "merged_skill_ids": [s.id for s in others],
            "merged_skill_names": [s.name for s in others],
            "group_size": len(group),
            "merged_tags": merged_tags,
            "merged_step_count": len(merged_steps),
            "aggregated_usage": total_usage,
            "aggregated_success_rate": round(weighted_success, 4),
            "category": primary.category.value,
        }

    def _perform_merge(self, candidate: Dict[str, Any]) -> bool:
        primary = self._skills.get(candidate["primary_skill_id"])
        if primary is None:
            return False

        for merged_id in candidate["merged_skill_ids"]:
            skill = self._skills.pop(merged_id, None)
            if skill is not None:
                self._unindex_skill(skill)

        primary.tags = candidate["merged_tags"]
        primary.usage_count = candidate["aggregated_usage"]
        primary.success_rate = candidate["aggregated_success_rate"]
        primary.updated_at = _time_module.time()
        primary.bump_version()

        self._index_skill(primary)
        return True

    # ------------------------------------------------------------------
    # Skill Accessors
    # ------------------------------------------------------------------

    def get_skill(self, skill_id: str) -> Optional[SkillTemplate]:
        return self._skills.get(skill_id)

    def get_skill_sessions(self, skill_id: str, limit: int = 50) -> List[SkillSession]:
        session_ids = self._skill_sessions.get(skill_id, [])
        return [self._sessions[sid] for sid in session_ids[-limit:] if sid in self._sessions]

    def list_skills(
        self,
        category: Optional[SkillCategory] = None,
        limit: int = 50,
    ) -> List[SkillTemplate]:
        pool = self._get_by_category(category) if category else list(self._skills.values())
        pool.sort(key=lambda s: s.compute_quality_score(), reverse=True)
        return pool[:limit]

    def reset(self) -> None:
        with self._lock:
            self._skills.clear()
            self._sessions.clear()
            self._skill_sessions.clear()
            self._tag_index.clear()
            for cat in SkillCategory:
                self._category_index[cat.value] = []
            self._total_skills_created = 0
            self._total_sessions_recorded = 0

    # ------------------------------------------------------------------
    # Internal Helpers
    # ------------------------------------------------------------------

    def _synthesize_steps(
        self,
        task_description: str,
        task_result: Dict[str, Any],
        category: SkillCategory,
    ) -> List[Dict[str, Any]]:
        desc_lower = task_description.lower()
        steps: List[Dict[str, Any]] = []

        has_analysis = any(kw in desc_lower for kw in ["analyze", "assess", "evaluate", "review"])
        has_generation = any(kw in desc_lower for kw in ["generate", "create", "build", "produce"])
        has_config = any(kw in desc_lower for kw in ["configure", "setup", "initialize", "settings"])
        has_validate = any(kw in desc_lower for kw in ["validate", "verify", "test", "check"])

        steps.append({
            "name": "context_analysis",
            "description": "Analyze the current context and gather requirements",
            "actions": ["scan_environment" if has_analysis else "collect_dependencies", "identify_constraints", "load_references"],
            "params": {"category": category.value},
            "estimated_ms": 300,
            "priority": "high",
        })

        if has_generation or not has_analysis:
            steps.append({
                "name": "core_generation",
                "description": "Generate the primary output for the task",
                "actions": ["apply_domain_knowledge", "generate_output", "apply_best_practices"],
                "params": {"domain": category.value},
                "estimated_ms": 1500,
                "priority": "critical",
                "parallelizable": True,
            })

        if has_config:
            steps.append({
                "name": "configuration",
                "description": "Apply configuration and tune parameters",
                "actions": ["apply_settings", "tune_parameters", "resolve_dependencies"],
                "params": {"auto_tune": True},
                "estimated_ms": 600,
                "priority": "medium",
            })

        steps.append({
            "name": "validation",
            "description": "Validate output against quality criteria",
            "actions": ["run_validation_checks" if has_validate else "sanity_check", "measure_quality", "flag_issues"],
            "params": {"strict_mode": False},
            "estimated_ms": 400,
            "priority": "high",
        })

        result_keys = list(task_result.keys())[:5] if task_result else []
        if result_keys:
            steps.append({
                "name": "result_assembly",
                "description": "Assemble and format the final result",
                "actions": ["aggregate_outputs"] + [f"package_{k}" for k in result_keys],
                "params": {"output_keys": result_keys},
                "estimated_ms": 200,
                "priority": "medium",
            })

        return steps

    def _derive_skill_name(self, task_description: str, category: SkillCategory) -> str:
        words = re.findall(r"[a-zA-Z_]+", task_description.lower())
        stopwords = {"a", "an", "the", "for", "and", "or", "in", "on", "to", "of", "with", "is", "that", "this"}
        meaningful = [w for w in words if w not in stopwords and len(w) > 2]
        prefix = category.value.replace("_", "-")
        if meaningful:
            key_terms = meaningful[:3]
            return f"{prefix}--{'-'.join(key_terms)}"
        return f"{prefix}-skill-{self._total_skills_created + 1:04d}"

    def _summarize_description(self, task_description: str, task_result: Dict[str, Any]) -> str:
        summary = task_description.strip()[:200]
        if task_result:
            keys = list(task_result.keys())[:4]
            summary += f" [outputs: {', '.join(keys)}]"
        return summary

    def _extract_tags(self, task_description: str, category: SkillCategory) -> List[str]:
        tags: List[str] = [category.value]
        desc_lower = task_description.lower()

        keyword_map: Dict[str, List[str]] = {
            "rpg": ["rpg", "role-playing"],
            "platformer": ["platformer", "platform"],
            "puzzle": ["puzzle"],
            "shooter": ["shooter", "shooting"],
            "combat": ["combat", "battle", "fighting"],
            "inventory": ["inventory", "items"],
            "dialogue": ["dialogue", "conversation"],
            "quest": ["quest", "mission"],
            "ai": ["ai", "behavior", "enemy"],
            "physics": ["physics", "collision", "gravity"],
            "animation": ["animation", "animator"],
            "audio": ["audio", "sound", "music"],
            "ui": ["ui", "interface", "menu", "hud"],
            "network": ["network", "multiplayer", "online"],
            "level": ["level", "map", "world"],
            "asset": ["asset", "sprite", "model", "texture"],
            "2d": ["2d", "two-dimensional"],
            "3d": ["3d", "three-dimensional"],
            "turn-based": ["turn-based", "turn based"],
            "real-time": ["real-time", "real time"],
        }

        for tag, keywords in keyword_map.items():
            if any(kw in desc_lower for kw in keywords):
                tags.append(tag)

        return list(dict.fromkeys(tags))

    def _index_skill(self, skill: SkillTemplate) -> None:
        cat_key = skill.category.value
        if skill.id not in self._category_index.get(cat_key, []):
            self._category_index.setdefault(cat_key, []).append(skill.id)

        for tag in skill.tags:
            tag_lower = tag.lower()
            self._tag_index.setdefault(tag_lower, [])
            if skill.id not in self._tag_index[tag_lower]:
                self._tag_index[tag_lower].append(skill.id)

    def _unindex_skill(self, skill: SkillTemplate) -> None:
        cat_key = skill.category.value
        cat_list = self._category_index.get(cat_key, [])
        if skill.id in cat_list:
            cat_list.remove(skill.id)

        for tag in skill.tags:
            tag_lower = tag.lower()
            tag_list = self._tag_index.get(tag_lower, [])
            if skill.id in tag_list:
                tag_list.remove(skill.id)

    def _get_by_category(self, category: SkillCategory) -> List[SkillTemplate]:
        ids = self._category_index.get(category.value, [])
        return [self._skills[i] for i in ids if i in self._skills]

    def _enforce_max_skills(self) -> None:
        if len(self._skills) >= self._MAX_SKILLS:
            sorted_skills = sorted(
                self._skills.values(),
                key=lambda s: (s.compute_quality_score(), s.updated_at),
            )
            evict_count = max(1, len(self._skills) - self._MAX_SKILLS + 1)
            for skill in sorted_skills[:evict_count]:
                self._skills.pop(skill.id, None)
                self._unindex_skill(skill)

    def get_stats(self) -> Dict[str, Any]:
        """Return comprehensive SkillForge subsystem statistics."""
        return self.get_skill_stats()


# ------------------------------------------------------------------
# Module-level Accessor
# ------------------------------------------------------------------


def get_skill_forge() -> SkillForge:
    return SkillForge.get_instance()