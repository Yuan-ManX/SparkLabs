"""
SparkLabs Agent - Skill Autonomy Engine

Autonomous skill creation system that extracts reusable capability
patterns from agent interaction history. Observes session turns,
identifies successful action sequences, and codifies them into
versioned, searchable AutonomousSkill records with maturity tracking.

Architecture:
  SkillAutonomyEngine
    |-- Session Observer (extract patterns from interaction turns)
    |-- Skill Synthesizer (codify patterns into structured skills)
    |-- Skill Search Engine (semantic lookup by domain and query)
    |-- Outcome Tracker (success/failure feedback loop for maturity)
    |-- Evolution Engine (iterative improvement of existing skills)

Skill domains cover game mechanics, AI behavior, UI patterns,
asset generation, performance tuning, and networking.
"""

from __future__ import annotations

import threading
import time
import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class SkillDomain(Enum):
    GAME_MECHANICS = "game_mechanics"
    AI_BEHAVIOR = "ai_behavior"
    UI_PATTERN = "ui_pattern"
    ASSET_GENERATION = "asset_generation"
    PERFORMANCE = "performance"
    NETWORKING = "networking"


class SkillMaturity(Enum):
    NASCENT = "nascent"
    TESTED = "tested"
    PROVEN = "proven"
    DEPRECATED = "deprecated"


@dataclass
class SkillStep:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    order: int = 0
    instruction: str = ""
    expected_outcome: str = ""
    code_template: str = ""
    parameters: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "order": self.order,
            "instruction": self.instruction[:120],
            "expected_outcome": self.expected_outcome[:120],
            "code_template_preview": self.code_template[:80],
            "parameters": self.parameters,
        }


@dataclass
class AutonomousSkill:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = ""
    domain: SkillDomain = SkillDomain.GAME_MECHANICS
    trigger_pattern: str = ""
    steps: List[SkillStep] = field(default_factory=list)
    pitfalls: List[str] = field(default_factory=list)
    maturity: SkillMaturity = SkillMaturity.NASCENT
    usage_count: int = 0
    success_rate: float = 1.0
    first_created: float = field(default_factory=time.time)
    last_updated: float = field(default_factory=time.time)
    parent_skill_ids: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "domain": self.domain.value,
            "trigger_pattern": self.trigger_pattern[:100],
            "steps_count": len(self.steps),
            "pitfalls_count": len(self.pitfalls),
            "maturity": self.maturity.value,
            "usage_count": self.usage_count,
            "success_rate": round(self.success_rate, 3),
            "parent_skill_ids": self.parent_skill_ids,
            "tags": self.tags,
        }

    def to_full_dict(self) -> Dict[str, Any]:
        result = self.to_dict()
        result["steps"] = [s.to_dict() for s in self.steps]
        result["pitfalls"] = self.pitfalls
        return result


class SkillAutonomyEngine:
    """Autonomous skill creation from agent interaction history."""

    _instance: Optional["SkillAutonomyEngine"] = None
    _lock = threading.Lock()

    MAX_SKILLS = 500
    MAX_STEPS_PER_SKILL = 50

    def __init__(self):
        self._skills: Dict[str, AutonomousSkill] = {}
        self._domain_index: Dict[SkillDomain, List[str]] = defaultdict(list)
        self._tag_index: Dict[str, List[str]] = defaultdict(list)
        self._sessions_processed: int = 0
        self._total_skills_extracted: int = 0

    @classmethod
    def get_instance(cls) -> "SkillAutonomyEngine":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def extract_skill_from_session(
        self, session_turns: list
    ) -> Optional[AutonomousSkill]:
        if not session_turns or len(session_turns) < 2:
            return None

        domain_keywords = {
            SkillDomain.GAME_MECHANICS: ["move", "jump", "collision", "physics", "sprite"],
            SkillDomain.AI_BEHAVIOR: ["agent", "npc", "patrol", "chase", "fsm"],
            SkillDomain.UI_PATTERN: ["ui", "menu", "hud", "button", "panel"],
            SkillDomain.ASSET_GENERATION: ["texture", "sprite", "sound", "mesh", "generate"],
            SkillDomain.PERFORMANCE: ["optimize", "cache", "batch", "pool", "fps"],
            SkillDomain.NETWORKING: ["sync", "rpc", "socket", "latency", "packet"],
        }

        all_text = " ".join(str(t) for t in session_turns).lower()
        detected_domain = SkillDomain.GAME_MECHANICS
        max_score = 0
        for domain, kws in domain_keywords.items():
            score = sum(1 for kw in kws if kw in all_text)
            if score > max_score:
                max_score = score
                detected_domain = domain

        skill_name = f"AutoSkill-{detected_domain.value}-{uuid.uuid4().hex[:6]}"
        trigger = " ".join(str(t)[:40] for t in session_turns[:2])[:120]

        steps: List[SkillStep] = []
        for idx, turn in enumerate(session_turns[: self.MAX_STEPS_PER_SKILL]):
            step = SkillStep(
                order=idx + 1,
                instruction=str(turn)[:200],
                expected_outcome=f"Complete step {idx + 1} of {len(session_turns[:self.MAX_STEPS_PER_SKILL])}",
            )
            steps.append(step)

        pitfalls: List[str] = []
        for turn in session_turns:
            text = str(turn).lower()
            if any(w in text for w in ["error", "fail", "issue", "problem", "warning"]):
                pitfalls.append(str(turn)[:120])
                if len(pitfalls) >= 5:
                    break

        skill = AutonomousSkill(
            name=skill_name,
            domain=detected_domain,
            trigger_pattern=trigger,
            steps=steps,
            pitfalls=pitfalls,
            maturity=SkillMaturity.NASCENT,
            tags=[detected_domain.value],
        )

        self._skills[skill.id] = skill
        self._domain_index[detected_domain].append(skill.id)
        for tag in skill.tags:
            self._tag_index[tag].append(skill.id)

        self._sessions_processed += 1
        self._total_skills_extracted += 1

        if len(self._skills) > self.MAX_SKILLS:
            oldest = min(self._skills.values(), key=lambda s: s.first_created)
            self._remove_skill_internal(oldest.id)

        return skill

    def search_skills(self, query: str) -> List[AutonomousSkill]:
        query_lower = query.lower()
        results: List[AutonomousSkill] = []
        seen_ids: set = set()

        for skill in self._skills.values():
            if skill.id in seen_ids:
                continue
            score = 0
            if query_lower in skill.name.lower():
                score += 5
            if query_lower in skill.trigger_pattern.lower():
                score += 3
            if query_lower in skill.domain.value:
                score += 2
            for tag in skill.tags:
                if query_lower in tag.lower():
                    score += 1
            if score > 0:
                results.append(skill)
                seen_ids.add(skill.id)

        results.sort(
            key=lambda s: (s.success_rate * s.usage_count), reverse=True
        )
        return results[:20]

    def apply_skill(
        self, skill_id: str, parameters: dict
    ) -> Optional[SkillStep]:
        skill = self._skills.get(skill_id)
        if skill is None or not skill.steps:
            return None

        skill.usage_count += 1
        skill.last_updated = time.time()
        return skill.steps[0]

    def mark_outcome(
        self, skill_id: str, success: bool, notes: str
    ) -> None:
        skill = self._skills.get(skill_id)
        if skill is None:
            return

        total = skill.usage_count
        if total > 0:
            prev_successes = skill.success_rate * (total - 1)
            new_successes = prev_successes + (1.0 if success else 0.0)
            skill.success_rate = new_successes / total

        if total >= 5:
            if skill.success_rate >= 0.85:
                skill.maturity = SkillMaturity.PROVEN
            elif skill.success_rate >= 0.6:
                skill.maturity = SkillMaturity.TESTED
            elif skill.success_rate < 0.3:
                skill.maturity = SkillMaturity.DEPRECATED

    def evolve_skill(
        self, skill_id: str, improvement_description: str
    ) -> Optional[AutonomousSkill]:
        original = self._skills.get(skill_id)
        if original is None:
            return None

        evolved = AutonomousSkill(
            name=f"{original.name}-v{len(original.parent_skill_ids) + 1}",
            domain=original.domain,
            trigger_pattern=original.trigger_pattern,
            steps=[SkillStep(**s.__dict__) for s in original.steps],
            pitfalls=list(original.pitfalls),
            maturity=SkillMaturity.NASCENT,
            parent_skill_ids=original.parent_skill_ids + [original.id],
            tags=list(original.tags),
        )

        evolved.pitfalls.append(improvement_description[:200])
        self._skills[evolved.id] = evolved
        self._domain_index[evolved.domain].append(evolved.id)
        for tag in evolved.tags:
            self._tag_index[tag].append(evolved.id)

        if len(self._skills) > self.MAX_SKILLS:
            oldest = min(self._skills.values(), key=lambda s: s.first_created)
            self._remove_skill_internal(oldest.id)

        return evolved

    def deprecate_skill(self, skill_id: str) -> None:
        skill = self._skills.get(skill_id)
        if skill is not None:
            skill.maturity = SkillMaturity.DEPRECATED
            skill.last_updated = time.time()

    def _remove_skill_internal(self, skill_id: str) -> None:
        skill = self._skills.pop(skill_id, None)
        if skill is None:
            return
        domain_list = self._domain_index.get(skill.domain, [])
        if skill_id in domain_list:
            domain_list.remove(skill_id)
        for tag in skill.tags:
            tag_list = self._tag_index.get(tag, [])
            if skill_id in tag_list:
                tag_list.remove(skill_id)

    def get_stats(self) -> dict:
        domain_counts: Dict[str, int] = defaultdict(int)
        maturity_counts: Dict[str, int] = defaultdict(int)
        for skill in self._skills.values():
            domain_counts[skill.domain.value] += 1
            maturity_counts[skill.maturity.value] += 1

        total_usage = sum(s.usage_count for s in self._skills.values())
        avg_success_rate = (
            sum(s.success_rate for s in self._skills.values())
            / max(1, len(self._skills))
        )

        return {
            "total_skills": len(self._skills),
            "sessions_processed": self._sessions_processed,
            "total_skills_extracted": self._total_skills_extracted,
            "domain_distribution": dict(domain_counts),
            "maturity_distribution": dict(maturity_counts),
            "total_skill_applications": total_usage,
            "average_success_rate": round(avg_success_rate, 3),
            "tags_indexed": len(self._tag_index),
            "max_skills": self.MAX_SKILLS,
        }


def get_skill_autonomy() -> SkillAutonomyEngine:
    return SkillAutonomyEngine.get_instance()