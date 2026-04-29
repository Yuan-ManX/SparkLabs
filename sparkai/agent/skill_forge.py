"""
SparkAI Agent - Skill Forge

Dynamic skill creation, evolution, and learning system.
The forge enables agents to create new skills from experience,
evolve existing skills based on success/failure patterns, and
compose complex skills from simpler building blocks.

Forge architecture:
  - Skill Blueprint: Template for creating new skills
  - Skill Evolution: Track skill performance and adapt over time
  - Skill Composition: Combine skills into multi-step workflows
  - Skill Library: Curated collection of proven skills
  - Forge Operations: Create, evolve, compose, validate, export

The forge learns from every skill execution, building a growing
library of game development expertise that becomes more reliable
over time.
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

from sparkai.agent.skills.base import Skill, SkillRegistry


class ForgeOperation(Enum):
    CREATE = "create"
    EVOLVE = "evolve"
    COMPOSE = "compose"
    VALIDATE = "validate"
    EXPORT = "export"
    IMPORT = "import"


class SkillMaturity(Enum):
    EXPERIMENTAL = "experimental"
    VALIDATED = "validated"
    PROVEN = "proven"
    CORE = "core"


@dataclass
class SkillBlueprint:
    """
    Template for creating new skills in the forge.

    Blueprints define the structure and parameters of a skill
    before it's instantiated and tested.
    """
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    category: str = "general"
    description: str = ""
    base_instructions: str = ""
    required_parameters: List[str] = field(default_factory=list)
    optional_parameters: Dict[str, Any] = field(default_factory=dict)
    composition_steps: List[str] = field(default_factory=list)
    verification_criteria: List[str] = field(default_factory=list)
    parent_skill: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "category": self.category,
            "description": self.description,
            "base_instructions": self.base_instructions[:300],
            "required_parameters": self.required_parameters,
            "optional_parameters": self.optional_parameters,
            "composition_steps": self.composition_steps,
            "verification_criteria": self.verification_criteria,
            "parent_skill": self.parent_skill,
            "tags": self.tags,
            "created_at": self.created_at,
        }


@dataclass
class SkillEvolution:
    """
    Tracks the performance and evolution of a skill over time.

    Records every execution, success rate, and adaptation to build
    a reliability profile for each skill.
    """
    skill_name: str = ""
    maturity: SkillMaturity = SkillMaturity.EXPERIMENTAL
    total_executions: int = 0
    successful_executions: int = 0
    failed_executions: int = 0
    success_rate: float = 0.0
    avg_duration_ms: float = 0.0
    last_executed: Optional[float] = None
    last_error: Optional[str] = None
    adaptations: List[Dict[str, Any]] = field(default_factory=list)
    version_history: List[str] = field(default_factory=lambda: ["1.0"])
    reliability_score: float = 0.0

    def record_execution(self, success: bool, duration_ms: float = 0.0, error: Optional[str] = None) -> None:
        self.total_executions += 1
        if success:
            self.successful_executions += 1
        else:
            self.failed_executions += 1
            self.last_error = error
        self.success_rate = self.successful_executions / self.total_executions
        self.last_executed = time.time()
        if duration_ms > 0:
            n = self.total_executions
            self.avg_duration_ms = (self.avg_duration_ms * (n - 1) + duration_ms) / n
        self._update_maturity()
        self._update_reliability()

    def _update_maturity(self) -> None:
        if self.total_executions >= 50 and self.success_rate >= 0.9:
            self.maturity = SkillMaturity.CORE
        elif self.total_executions >= 20 and self.success_rate >= 0.8:
            self.maturity = SkillMaturity.PROVEN
        elif self.total_executions >= 5 and self.success_rate >= 0.6:
            self.maturity = SkillMaturity.VALIDATED
        else:
            self.maturity = SkillMaturity.EXPERIMENTAL

    def _update_reliability(self) -> None:
        if self.total_executions == 0:
            self.reliability_score = 0.0
            return
        execution_weight = min(self.total_executions / 50.0, 1.0)
        success_weight = self.success_rate
        recency = 1.0
        if self.last_executed:
            hours_since = (time.time() - self.last_executed) / 3600
            recency = max(0.5, 1.0 - hours_since / 168.0)
        self.reliability_score = (success_weight * 0.6 + execution_weight * 0.3 + recency * 0.1)

    def add_adaptation(self, change: str, reason: str) -> None:
        self.adaptations.append({
            "change": change,
            "reason": reason,
            "timestamp": time.time(),
            "version": self.version_history[-1] if self.version_history else "1.0",
        })

    def to_dict(self) -> Dict[str, Any]:
        return {
            "skill_name": self.skill_name,
            "maturity": self.maturity.value,
            "total_executions": self.total_executions,
            "successful_executions": self.successful_executions,
            "failed_executions": self.failed_executions,
            "success_rate": round(self.success_rate, 3),
            "avg_duration_ms": round(self.avg_duration_ms, 1),
            "last_executed": self.last_executed,
            "reliability_score": round(self.reliability_score, 3),
            "adaptation_count": len(self.adaptations),
            "version": self.version_history[-1] if self.version_history else "1.0",
        }


@dataclass
class ComposedSkill:
    """
    A skill composed from multiple simpler skills.

    Composed skills chain multiple skill executions together,
    passing context between steps.
    """
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    description: str = ""
    category: str = "composed"
    steps: List[str] = field(default_factory=list)
    step_context_mapping: Dict[str, Dict[str, str]] = field(default_factory=dict)
    version: str = "1.0"
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "category": self.category,
            "steps": self.steps,
            "step_context_mapping": self.step_context_mapping,
            "version": self.version,
            "created_at": self.created_at,
        }


class SkillForge:
    """
    Dynamic skill creation and evolution system for the SparkLabs
    AI-Native Game Engine.

    The forge enables:
    - Creating new skills from blueprints
    - Tracking skill performance and reliability
    - Evolving skills based on execution history
    - Composing complex skills from simpler ones
    - Validating skills against criteria
    - Exporting/importing skill definitions

    Usage:
        forge = SkillForge()
        blueprint = forge.create_blueprint("level_design", "level_design", ...)
        skill = forge.forge_skill(blueprint)
        forge.record_execution("level_design", success=True, duration_ms=1500)
    """

    def __init__(self):
        self._blueprints: Dict[str, SkillBlueprint] = {}
        self._evolutions: Dict[str, SkillEvolution] = {}
        self._composed: Dict[str, ComposedSkill] = {}
        self._forge_history: List[Dict[str, Any]] = []
        self._max_history = 500

    def create_blueprint(
        self,
        name: str,
        category: str,
        description: str = "",
        instructions: str = "",
        required_params: Optional[List[str]] = None,
        optional_params: Optional[Dict[str, Any]] = None,
        verification: Optional[List[str]] = None,
        tags: Optional[List[str]] = None,
    ) -> SkillBlueprint:
        """Create a new skill blueprint for forging."""
        blueprint = SkillBlueprint(
            name=name,
            category=category,
            description=description,
            base_instructions=instructions,
            required_parameters=required_params or [],
            optional_parameters=optional_params or {},
            verification_criteria=verification or [],
            tags=tags or [],
        )
        self._blueprints[blueprint.id] = blueprint
        self._record_operation(ForgeOperation.CREATE, name, blueprint.id)
        return blueprint

    def forge_skill(self, blueprint: SkillBlueprint) -> Skill:
        """Forge a skill from a blueprint and register it."""
        steps = blueprint.composition_steps or [
            f"Analyze the {blueprint.category} requirements",
            f"Apply {blueprint.name} knowledge",
            f"Generate output for {blueprint.category}",
            f"Verify against criteria",
        ]

        skill = Skill(
            name=blueprint.name,
            description=blueprint.description,
            category=blueprint.category,
            instructions=blueprint.base_instructions,
            steps=steps,
            parameters=blueprint.optional_parameters,
            verification=blueprint.verification_criteria,
        )

        SkillRegistry.register(skill)

        if blueprint.name not in self._evolutions:
            self._evolutions[blueprint.name] = SkillEvolution(skill_name=blueprint.name)

        self._record_operation(ForgeOperation.CREATE, blueprint.name, skill.id)
        return skill

    def compose_skill(
        self,
        name: str,
        description: str,
        skill_names: List[str],
        context_mapping: Optional[Dict[str, Dict[str, str]]] = None,
    ) -> ComposedSkill:
        """
        Compose a new skill from multiple existing skills.

        The composed skill chains the specified skills together,
        passing context between steps.
        """
        valid_steps = []
        for skill_name in skill_names:
            existing = SkillRegistry.get(skill_name)
            if existing:
                valid_steps.append(skill_name)

        if not valid_steps:
            raise ValueError("No valid skills found for composition")

        composed = ComposedSkill(
            name=name,
            description=description,
            steps=valid_steps,
            step_context_mapping=context_mapping or {},
        )
        self._composed[composed.id] = composed

        composed_skill = Skill(
            name=name,
            description=description,
            category="composed",
            instructions=f"Execute composed workflow: {' -> '.join(valid_steps)}",
            steps=[f"Execute {s}" for s in valid_steps],
            parameters={"skill_chain": valid_steps},
        )
        SkillRegistry.register(composed_skill)

        if name not in self._evolutions:
            self._evolutions[name] = SkillEvolution(skill_name=name)

        self._record_operation(ForgeOperation.COMPOSE, name, composed.id)
        return composed

    def record_execution(
        self,
        skill_name: str,
        success: bool,
        duration_ms: float = 0.0,
        error: Optional[str] = None,
    ) -> SkillEvolution:
        """Record a skill execution for evolution tracking."""
        if skill_name not in self._evolutions:
            self._evolutions[skill_name] = SkillEvolution(skill_name=skill_name)
        evolution = self._evolutions[skill_name]
        evolution.record_execution(success, duration_ms, error)
        return evolution

    def evolve_skill(self, skill_name: str) -> Optional[SkillEvolution]:
        """
        Attempt to evolve a skill based on its execution history.

        If a skill has a low success rate, the forge may suggest
        adaptations to improve reliability.
        """
        evolution = self._evolutions.get(skill_name)
        if not evolution:
            return None

        if evolution.success_rate < 0.5 and evolution.total_executions >= 5:
            evolution.add_adaptation(
                "review_instructions",
                f"Success rate below 50% ({evolution.success_rate:.1%})",
            )

        if evolution.avg_duration_ms > 5000 and evolution.total_executions >= 3:
            evolution.add_adaptation(
                "optimize_steps",
                f"Average duration exceeds 5s ({evolution.avg_duration_ms:.0f}ms)",
            )

        self._record_operation(ForgeOperation.EVOLVE, skill_name, None)
        return evolution

    def validate_skill(self, skill_name: str) -> Dict[str, Any]:
        """Validate a skill against its verification criteria."""
        skill = SkillRegistry.get(skill_name)
        if not skill:
            return {"valid": False, "error": f"Skill '{skill_name}' not found"}

        evolution = self._evolutions.get(skill_name)
        checks = {
            "has_instructions": bool(skill.instructions),
            "has_steps": bool(skill.steps),
            "has_verification": bool(skill.verification),
            "is_registered": True,
            "maturity": evolution.maturity.value if evolution else "unknown",
            "reliability": evolution.reliability_score if evolution else 0.0,
            "success_rate": evolution.success_rate if evolution else 0.0,
        }

        all_passed = checks["has_instructions"] and checks["has_steps"]
        self._record_operation(ForgeOperation.VALIDATE, skill_name, None)
        return {"valid": all_passed, "checks": checks}

    def get_evolution(self, skill_name: str) -> Optional[Dict[str, Any]]:
        evolution = self._evolutions.get(skill_name)
        return evolution.to_dict() if evolution else None

    def list_blueprints(self) -> List[Dict[str, Any]]:
        return [b.to_dict() for b in self._blueprints.values()]

    def list_composed(self) -> List[Dict[str, Any]]:
        return [c.to_dict() for c in self._composed.values()]

    def list_evolutions(self, min_maturity: Optional[SkillMaturity] = None) -> List[Dict[str, Any]]:
        evolutions = self._evolutions.values()
        if min_maturity:
            maturity_order = [SkillMaturity.EXPERIMENTAL, SkillMaturity.VALIDATED, SkillMaturity.PROVEN, SkillMaturity.CORE]
            min_idx = maturity_order.index(min_maturity)
            evolutions = [e for e in evolutions if maturity_order.index(e.maturity) >= min_idx]
        return [e.to_dict() for e in evolutions]

    def get_stats(self) -> Dict[str, Any]:
        total = len(self._evolutions)
        by_maturity = {}
        for e in self._evolutions.values():
            key = e.maturity.value
            by_maturity[key] = by_maturity.get(key, 0) + 1

        return {
            "total_skills": total,
            "total_blueprints": len(self._blueprints),
            "total_composed": len(self._composed),
            "by_maturity": by_maturity,
            "avg_success_rate": (
                sum(e.success_rate for e in self._evolutions.values()) / total
                if total > 0 else 0.0
            ),
            "avg_reliability": (
                sum(e.reliability_score for e in self._evolutions.values()) / total
                if total > 0 else 0.0
            ),
            "forge_operations": len(self._forge_history),
        }

    def _record_operation(self, op: ForgeOperation, skill_name: str, target_id: Optional[str]) -> None:
        self._forge_history.append({
            "operation": op.value,
            "skill_name": skill_name,
            "target_id": target_id,
            "timestamp": time.time(),
        })
        if len(self._forge_history) > self._max_history:
            self._forge_history = self._forge_history[-self._max_history:]

    def get_forge_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        return self._forge_history[-limit:]


_global_forge: Optional[SkillForge] = None


def get_skill_forge() -> SkillForge:
    """Get the global SkillForge singleton."""
    global _global_forge
    if _global_forge is None:
        _global_forge = SkillForge()
    return _global_forge


def reset_skill_forge() -> None:
    """Reset the global SkillForge singleton."""
    global _global_forge
    _global_forge = None
