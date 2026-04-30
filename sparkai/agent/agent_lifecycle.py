"""
SparkLabs Agent Lifecycle System

Unified lifecycle management for AI-native game engine agents.
Implements a Blueprint-driven spawn pipeline with Plan-Execute-Reflect cycle,
confidence-scored verification, and context-aware delegation.
"""

from __future__ import annotations

import json
import uuid
import time
import asyncio
from enum import Enum
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Set, Tuple


class LifecyclePhase(Enum):
    SPAWN = "spawn"
    CONFIGURE = "configure"
    PLAN = "plan"
    EXECUTE = "execute"
    REFLECT = "reflect"
    VERIFY = "verify"
    EVOLVE = "evolve"
    COMPLETE = "complete"
    FAILED = "failed"


class BlueprintTier(Enum):
    DIRECTOR = "director"
    LEAD = "lead"
    SPECIALIST = "specialist"
    WORKER = "worker"


class ReflectionVerdict(Enum):
    ON_TRACK = "on_track"
    NEEDS_ADJUSTMENT = "needs_adjustment"
    NEEDS_REPLAN = "needs_replan"
    CRITICAL_FAILURE = "critical_failure"


class VerificationConfidence(Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    FAILED = "failed"


@dataclass
class ToolRequirement:
    name: str
    required: bool = True
    config: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SkillRequirement:
    name: str
    min_maturity: str = "seed"
    required: bool = True


@dataclass
class VerificationCriterion:
    name: str
    description: str
    weight: float = 1.0
    threshold: float = 0.7
    requires_approval: bool = False


@dataclass
class AgentBlueprint:
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    name: str = ""
    tier: BlueprintTier = BlueprintTier.SPECIALIST
    description: str = ""
    system_prompt: str = ""
    capabilities: List[str] = field(default_factory=list)
    tool_requirements: List[ToolRequirement] = field(default_factory=list)
    skill_requirements: List[SkillRequirement] = field(default_factory=list)
    verification_criteria: List[VerificationCriterion] = field(default_factory=list)
    parent_blueprint: Optional[str] = None
    config: Dict[str, Any] = field(default_factory=dict)
    max_replans: int = 2
    reflection_interval: int = 3
    timeout_seconds: float = 300.0


@dataclass
class PlanStep:
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    description: str = ""
    tool: Optional[str] = None
    tool_params: Dict[str, Any] = field(default_factory=dict)
    dependencies: List[str] = field(default_factory=list)
    verification: Optional[VerificationCriterion] = None
    status: str = "pending"
    output: Any = None
    confidence: float = 0.0
    duration_ms: float = 0.0


@dataclass
class ExecutionPlan:
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    goal: str = ""
    steps: List[PlanStep] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    replan_count: int = 0
    max_replans: int = 2


@dataclass
class ReflectionResult:
    verdict: ReflectionVerdict = ReflectionVerdict.ON_TRACK
    confidence: float = 0.0
    observations: List[str] = field(default_factory=list)
    adjustments: List[str] = field(default_factory=list)
    replan_reason: Optional[str] = None


@dataclass
class VerificationResult:
    criterion_name: str = ""
    passed: bool = False
    confidence: float = 0.0
    confidence_level: VerificationConfidence = VerificationConfidence.FAILED
    details: str = ""
    requires_approval: bool = False
    approved: Optional[bool] = None


@dataclass
class LifecycleEvent:
    phase: LifecyclePhase
    agent_id: str
    timestamp: float = field(default_factory=time.time)
    data: Dict[str, Any] = field(default_factory=dict)


class AgentLifecycleManager:
    """
    Unified lifecycle manager for SparkLabs agents.

    Manages the full agent lifecycle from blueprint-based spawning
    through Plan-Execute-Reflect cycles with confidence-scored verification.
    """

    def __init__(self):
        self._blueprints: Dict[str, AgentBlueprint] = {}
        self._lifecycle_events: List[LifecycleEvent] = []
        self._active_plans: Dict[str, ExecutionPlan] = {}
        self._verification_results: Dict[str, List[VerificationResult]] = {}
        self._pending_approvals: Dict[str, VerificationResult] = {}
        self._phase_handlers: Dict[LifecyclePhase, List[Callable]] = {}
        self._max_events = 2000
        self._seed_blueprints()

    def _seed_blueprints(self):
        director_blueprint = AgentBlueprint(
            name="Game Director",
            tier=BlueprintTier.DIRECTOR,
            description="Oversees the full game creation pipeline, makes high-level design decisions",
            system_prompt="You are the Game Director. You oversee the entire game creation process, make creative decisions, and coordinate all departments.",
            capabilities=["reasoning", "workflow_orchestration", "quality_review", "gameplay_design"],
            tool_requirements=[
                ToolRequirement(name="game_context", required=True),
                ToolRequirement(name="quality_gate", required=True),
            ],
            skill_requirements=[
                SkillRequirement(name="game_design", min_maturity="growing"),
                SkillRequirement(name="project_management", min_maturity="seed"),
            ],
            verification_criteria=[
                VerificationCriterion(name="design_coherence", description="Game design is internally consistent", weight=1.5, threshold=0.8),
                VerificationCriterion(name="scope_feasibility", description="Project scope is achievable", weight=1.0, threshold=0.7),
            ],
            max_replans=3,
            reflection_interval=2,
        )

        lead_blueprint = AgentBlueprint(
            name="Department Lead",
            tier=BlueprintTier.LEAD,
            description="Manages a department of specialists, ensures quality and consistency",
            system_prompt="You are a Department Lead. You manage specialists in your domain, review their work, and ensure quality standards.",
            capabilities=["reasoning", "code_generation", "quality_review"],
            tool_requirements=[
                ToolRequirement(name="code_executor", required=True),
                ToolRequirement(name="asset_pipeline", required=False),
            ],
            skill_requirements=[
                SkillRequirement(name="code_review", min_maturity="sprout"),
                SkillRequirement(name="debugging", min_maturity="seed"),
            ],
            verification_criteria=[
                VerificationCriterion(name="code_quality", description="Code meets quality standards", weight=1.2, threshold=0.75),
                VerificationCriterion(name="spec_compliance", description="Output matches specification", weight=1.0, threshold=0.8),
            ],
            max_replans=2,
            reflection_interval=3,
        )

        specialist_blueprint = AgentBlueprint(
            name="Domain Specialist",
            tier=BlueprintTier.SPECIALIST,
            description="Executes specialized tasks within a domain",
            system_prompt="You are a Specialist. You execute tasks in your domain of expertise with precision and efficiency.",
            capabilities=["code_generation", "asset_generation", "world_building"],
            tool_requirements=[
                ToolRequirement(name="code_executor", required=True),
            ],
            skill_requirements=[
                SkillRequirement(name="code_generation", min_maturity="seed"),
            ],
            verification_criteria=[
                VerificationCriterion(name="task_completion", description="Task is fully completed", weight=1.0, threshold=0.7),
                VerificationCriterion(name="output_correctness", description="Output is correct and functional", weight=1.5, threshold=0.8, requires_approval=False),
            ],
            max_replans=1,
            reflection_interval=4,
        )

        worker_blueprint = AgentBlueprint(
            name="Task Worker",
            tier=BlueprintTier.WORKER,
            description="Performs atomic tasks assigned by leads or specialists",
            system_prompt="You are a Worker. You perform specific tasks efficiently and report results.",
            capabilities=["code_generation", "testing"],
            tool_requirements=[],
            skill_requirements=[
                SkillRequirement(name="code_generation", min_maturity="seed"),
            ],
            verification_criteria=[
                VerificationCriterion(name="task_done", description="Task completed", weight=1.0, threshold=0.6),
            ],
            max_replans=1,
            reflection_interval=5,
        )

        for bp in [director_blueprint, lead_blueprint, specialist_blueprint, worker_blueprint]:
            self._blueprints[bp.name] = bp

    def register_blueprint(self, blueprint: AgentBlueprint) -> str:
        key = blueprint.name or blueprint.id
        self._blueprints[key] = blueprint
        return key

    def get_blueprint(self, name: str) -> Optional[AgentBlueprint]:
        return self._blueprints.get(name)

    def list_blueprints(self) -> List[Dict[str, Any]]:
        return [
            {
                "name": bp.name,
                "tier": bp.tier.value,
                "description": bp.description,
                "capabilities": bp.capabilities,
                "tool_count": len(bp.tool_requirements),
                "skill_count": len(bp.skill_requirements),
                "verification_count": len(bp.verification_criteria),
                "max_replans": bp.max_replans,
            }
            for bp in self._blueprints.values()
        ]

    def spawn_from_blueprint(self, blueprint_name: str, overrides: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        bp = self._blueprints.get(blueprint_name)
        if not bp:
            return {"error": f"Blueprint '{blueprint_name}' not found"}

        agent_config = {
            "id": str(uuid.uuid4())[:8],
            "name": bp.name,
            "tier": bp.tier.value,
            "description": bp.description,
            "system_prompt": bp.system_prompt,
            "capabilities": list(bp.capabilities),
            "tools": [{"name": t.name, "required": t.required, "config": t.config} for t in bp.tool_requirements],
            "skills": [{"name": s.name, "min_maturity": s.min_maturity, "required": s.required} for s in bp.skill_requirements],
            "verification_criteria": [
                {"name": v.name, "description": v.description, "weight": v.weight, "threshold": v.threshold, "requires_approval": v.requires_approval}
                for v in bp.verification_criteria
            ],
            "max_replans": bp.max_replans,
            "reflection_interval": bp.reflection_interval,
            "timeout_seconds": bp.timeout_seconds,
            "config": dict(bp.config),
        }

        if overrides:
            for key, value in overrides.items():
                if key in agent_config:
                    agent_config[key] = value

        self._emit_event(LifecyclePhase.SPAWN, agent_config["id"], {"blueprint": blueprint_name, "config": agent_config})
        return agent_config

    def create_plan(self, agent_id: str, goal: str, max_replans: int = 2) -> ExecutionPlan:
        plan = ExecutionPlan(goal=goal, max_replans=max_replans)
        self._active_plans[agent_id] = plan
        self._emit_event(LifecyclePhase.PLAN, agent_id, {"plan_id": plan.id, "goal": goal})
        return plan

    def add_plan_step(
        self,
        agent_id: str,
        description: str,
        tool: Optional[str] = None,
        tool_params: Optional[Dict[str, Any]] = None,
        dependencies: Optional[List[str]] = None,
        verification: Optional[VerificationCriterion] = None,
    ) -> Optional[PlanStep]:
        plan = self._active_plans.get(agent_id)
        if not plan:
            return None
        step = PlanStep(
            description=description,
            tool=tool,
            tool_params=tool_params or {},
            dependencies=dependencies or [],
            verification=verification,
        )
        plan.steps.append(step)
        return step

    def execute_step(self, agent_id: str, step_id: str, output: Any, confidence: float = 0.0, duration_ms: float = 0.0) -> bool:
        plan = self._active_plans.get(agent_id)
        if not plan:
            return False
        for step in plan.steps:
            if step.id == step_id:
                step.status = "completed"
                step.output = output
                step.confidence = confidence
                step.duration_ms = duration_ms
                self._emit_event(LifecyclePhase.EXECUTE, agent_id, {"step_id": step_id, "confidence": confidence})
                return True
        return False

    def fail_step(self, agent_id: str, step_id: str, error: str) -> bool:
        plan = self._active_plans.get(agent_id)
        if not plan:
            return False
        for step in plan.steps:
            if step.id == step_id:
                step.status = "failed"
                step.output = error
                self._emit_event(LifecyclePhase.EXECUTE, agent_id, {"step_id": step_id, "error": error})
                return True
        return False

    def reflect(
        self,
        agent_id: str,
        steps_completed: int,
        total_steps: int,
        avg_confidence: float,
        errors: List[str],
    ) -> ReflectionResult:
        plan = self._active_plans.get(agent_id)
        max_replans = plan.max_replans if plan else 2

        observations = []
        adjustments = []

        if avg_confidence >= 0.8:
            verdict = ReflectionVerdict.ON_TRACK
        elif avg_confidence >= 0.5:
            verdict = ReflectionVerdict.NEEDS_ADJUSTMENT
            adjustments.append("Review recent steps for quality issues")
            adjustments.append("Consider adjusting tool parameters")
        elif errors and len(errors) > total_steps * 0.3:
            if plan and plan.replan_count < max_replans:
                verdict = ReflectionVerdict.NEEDS_REPLAN
                plan.replan_count += 1
            else:
                verdict = ReflectionVerdict.CRITICAL_FAILURE
        else:
            if plan and plan.replan_count < max_replans:
                verdict = ReflectionVerdict.NEEDS_REPLAN
                plan.replan_count += 1
            else:
                verdict = ReflectionVerdict.NEEDS_ADJUSTMENT
                adjustments.append("Proceeding with current plan despite low confidence")

        if steps_completed > 0:
            observations.append(f"Completed {steps_completed}/{total_steps} steps")
        if errors:
            observations.append(f"Encountered {len(errors)} errors: {'; '.join(errors[:3])}")
        if avg_confidence > 0:
            observations.append(f"Average confidence: {avg_confidence:.2f}")

        result = ReflectionResult(
            verdict=verdict,
            confidence=avg_confidence,
            observations=observations,
            adjustments=adjustments,
            replan_reason=f"Low confidence ({avg_confidence:.2f}) with {len(errors)} errors" if verdict == ReflectionVerdict.NEEDS_REPLAN else None,
        )

        self._emit_event(LifecyclePhase.REFLECT, agent_id, {
            "verdict": verdict.value,
            "confidence": avg_confidence,
            "observations": observations,
            "adjustments": adjustments,
        })

        return result

    def verify(
        self,
        agent_id: str,
        criteria: List[VerificationCriterion],
        results: Dict[str, Tuple[bool, float, str]],
    ) -> List[VerificationResult]:
        verification_results = []
        for criterion in criteria:
            if criterion.name in results:
                passed, confidence, details = results[criterion.name]
                if confidence >= 0.8:
                    confidence_level = VerificationConfidence.HIGH
                elif confidence >= 0.5:
                    confidence_level = VerificationConfidence.MEDIUM
                elif passed:
                    confidence_level = VerificationConfidence.LOW
                else:
                    confidence_level = VerificationConfidence.FAILED

                vr = VerificationResult(
                    criterion_name=criterion.name,
                    passed=passed,
                    confidence=confidence,
                    confidence_level=confidence_level,
                    details=details,
                    requires_approval=criterion.requires_approval,
                )

                if criterion.requires_approval and passed and confidence < 0.9:
                    vr.requires_approval = True
                    vr.approved = None
                    self._pending_approvals[f"{agent_id}:{criterion.name}"] = vr

                verification_results.append(vr)
            else:
                verification_results.append(VerificationResult(
                    criterion_name=criterion.name,
                    passed=False,
                    confidence=0.0,
                    confidence_level=VerificationConfidence.FAILED,
                    details="No result provided for this criterion",
                ))

        self._verification_results[agent_id] = verification_results
        self._emit_event(LifecyclePhase.VERIFY, agent_id, {
            "results": [{"criterion": vr.criterion_name, "passed": vr.passed, "confidence": vr.confidence, "level": vr.confidence_level.value} for vr in verification_results],
        })

        return verification_results

    def approve_verification(self, agent_id: str, criterion_name: str, approved: bool) -> bool:
        key = f"{agent_id}:{criterion_name}"
        vr = self._pending_approvals.get(key)
        if vr:
            vr.approved = approved
            if not approved:
                vr.passed = False
            del self._pending_approvals[key]
            return True
        return False

    def get_pending_approvals(self) -> List[Dict[str, Any]]:
        return [
            {
                "agent_id": key.split(":")[0],
                "criterion": vr.criterion_name,
                "confidence": vr.confidence,
                "confidence_level": vr.confidence_level.value,
                "details": vr.details,
            }
            for key, vr in self._pending_approvals.items()
        ]

    def get_plan(self, agent_id: str) -> Optional[Dict[str, Any]]:
        plan = self._active_plans.get(agent_id)
        if not plan:
            return None
        return {
            "id": plan.id,
            "goal": plan.goal,
            "steps": [
                {
                    "id": s.id,
                    "description": s.description,
                    "tool": s.tool,
                    "status": s.status,
                    "confidence": s.confidence,
                    "duration_ms": s.duration_ms,
                    "dependencies": s.dependencies,
                }
                for s in plan.steps
            ],
            "replan_count": plan.replan_count,
            "max_replans": plan.max_replans,
            "created_at": plan.created_at,
        }

    def get_verification_results(self, agent_id: str) -> List[Dict[str, Any]]:
        results = self._verification_results.get(agent_id, [])
        return [
            {
                "criterion": vr.criterion_name,
                "passed": vr.passed,
                "confidence": vr.confidence,
                "confidence_level": vr.confidence_level.value,
                "details": vr.details,
                "requires_approval": vr.requires_approval,
                "approved": vr.approved,
            }
            for vr in results
        ]

    def on_phase(self, phase: LifecyclePhase, handler: Callable):
        if phase not in self._phase_handlers:
            self._phase_handlers[phase] = []
        self._phase_handlers[phase].append(handler)

    def _emit_event(self, phase: LifecyclePhase, agent_id: str, data: Dict[str, Any]):
        event = LifecycleEvent(phase=phase, agent_id=agent_id, data=data)
        self._lifecycle_events.append(event)
        if len(self._lifecycle_events) > self._max_events:
            self._lifecycle_events = self._lifecycle_events[-self._max_events:]
        for handler in self._phase_handlers.get(phase, []):
            try:
                handler(event)
            except Exception:
                pass

    def get_lifecycle_events(self, agent_id: Optional[str] = None, phase: Optional[LifecyclePhase] = None, limit: int = 50) -> List[Dict[str, Any]]:
        events = self._lifecycle_events
        if agent_id:
            events = [e for e in events if e.agent_id == agent_id]
        if phase:
            events = [e for e in events if e.phase == phase]
        return [
            {
                "phase": e.phase.value,
                "agent_id": e.agent_id,
                "timestamp": e.timestamp,
                "data": e.data,
            }
            for e in events[-limit:]
        ]

    def get_stats(self) -> Dict[str, Any]:
        phase_counts = {}
        for event in self._lifecycle_events:
            key = event.phase.value
            phase_counts[key] = phase_counts.get(key, 0) + 1
        return {
            "blueprints": len(self._blueprints),
            "active_plans": len(self._active_plans),
            "pending_approvals": len(self._pending_approvals),
            "total_events": len(self._lifecycle_events),
            "phase_distribution": phase_counts,
        }
