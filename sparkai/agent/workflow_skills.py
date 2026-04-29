"""
SparkAI Agent - Workflow Skills

Structured game development workflow commands that guide the creative
and technical process from concept to release. Each workflow skill
encapsulates a complete development workflow with defined inputs,
outputs, steps, and quality checkpoints.

Architecture:
  WorkflowSkillSystem
    |-- SkillRegistry (workflow skill definitions)
    |-- SkillExecutor (executes workflow steps)
    |-- WorkflowPipeline (chains skills into development pipelines)

Workflow Categories:
  Design - brainstorm, system design, UX design
  Development - scaffold, implement, integrate
  Review - code review, design review, balance check
  Testing - smoke test, regression, playtest
  Production - milestone review, release checklist
  Creative - prototype, localize, asset creation

Each workflow skill follows a consistent execution pattern:
  Prepare -> Execute -> Validate -> Report
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class WorkflowCategory(Enum):
    DESIGN = "design"
    DEVELOPMENT = "development"
    REVIEW = "review"
    TESTING = "testing"
    PRODUCTION = "production"
    CREATIVE = "creative"
    ORCHESTRATION = "orchestration"


class WorkflowPhase(Enum):
    PREPARE = "prepare"
    EXECUTE = "execute"
    VALIDATE = "validate"
    REPORT = "report"


class StepStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class WorkflowStep:
    """A single step in a workflow skill."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    description: str = ""
    order: int = 0
    status: StepStatus = StepStatus.PENDING
    required_inputs: List[str] = field(default_factory=list)
    outputs: List[str] = field(default_factory=list)
    agent_role: str = ""
    estimated_duration: float = 0.0
    actual_duration: float = 0.0
    result: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "order": self.order,
            "status": self.status.value,
            "required_inputs": self.required_inputs,
            "outputs": self.outputs,
            "agent_role": self.agent_role,
            "estimated_duration": self.estimated_duration,
            "actual_duration": self.actual_duration,
            "result": self.result,
            "error": self.error,
        }


@dataclass
class WorkflowSkill:
    """A complete workflow skill definition."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    display_name: str = ""
    description: str = ""
    category: WorkflowCategory = WorkflowCategory.DEVELOPMENT
    slash_command: str = ""
    steps: List[WorkflowStep] = field(default_factory=list)
    required_inputs: List[str] = field(default_factory=list)
    outputs: List[str] = field(default_factory=list)
    quality_gates: List[str] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    usage_count: int = 0
    success_rate: float = 0.0
    enabled: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "display_name": self.display_name,
            "description": self.description,
            "category": self.category.value,
            "slash_command": self.slash_command,
            "step_count": len(self.steps),
            "steps": [s.to_dict() for s in self.steps],
            "required_inputs": self.required_inputs,
            "outputs": self.outputs,
            "quality_gates": self.quality_gates,
            "dependencies": self.dependencies,
            "tags": self.tags,
            "usage_count": self.usage_count,
            "success_rate": self.success_rate,
            "enabled": self.enabled,
        }


@dataclass
class WorkflowExecution:
    """Record of a workflow skill execution."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    skill_id: str = ""
    skill_name: str = ""
    status: StepStatus = StepStatus.PENDING
    current_step: int = 0
    total_steps: int = 0
    inputs: Dict[str, Any] = field(default_factory=dict)
    outputs: Dict[str, Any] = field(default_factory=dict)
    step_results: List[Dict[str, Any]] = field(default_factory=list)
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    duration_ms: float = 0.0
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "skill_id": self.skill_id,
            "skill_name": self.skill_name,
            "status": self.status.value,
            "current_step": self.current_step,
            "total_steps": self.total_steps,
            "inputs": self.inputs,
            "outputs": self.outputs,
            "step_results": self.step_results,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "duration_ms": self.duration_ms,
            "error": self.error,
        }


def _build_skill_registry() -> Dict[str, WorkflowSkill]:
    """Build the initial set of workflow skills."""
    skills: Dict[str, WorkflowSkill] = {}

    skill_defs = [
        {
            "name": "brainstorm",
            "display_name": "Brainstorm",
            "description": "Explore game concepts and generate creative ideas",
            "category": WorkflowCategory.DESIGN,
            "slash_command": "/brainstorm",
            "steps": [
                {"name": "gather_context", "description": "Gather existing context and constraints", "agent_role": "creative_director"},
                {"name": "generate_ideas", "description": "Generate multiple game concept variations", "agent_role": "creative_director"},
                {"name": "evaluate_ideas", "description": "Evaluate ideas against criteria", "agent_role": "producer"},
                {"name": "select_concept", "description": "Select and refine the best concept", "agent_role": "creative_director"},
            ],
            "outputs": ["game_concept", "core_mechanics", "visual_direction"],
            "tags": ["creative", "concept", "ideation"],
        },
        {
            "name": "design_system",
            "display_name": "Design System",
            "description": "Design a game system with mechanics, rules, and balance",
            "category": WorkflowCategory.DESIGN,
            "slash_command": "/design-system",
            "steps": [
                {"name": "define_requirements", "description": "Define system requirements and constraints", "agent_role": "game_designer"},
                {"name": "design_mechanics", "description": "Design core mechanics and rules", "agent_role": "game_designer"},
                {"name": "define_balance", "description": "Define balance parameters and curves", "agent_role": "game_designer"},
                {"name": "create_spec", "description": "Create detailed system specification", "agent_role": "game_designer"},
            ],
            "outputs": ["system_spec", "balance_curves", "mechanic_descriptions"],
            "quality_gates": ["design_consistency"],
            "tags": ["design", "mechanics", "balance"],
        },
        {
            "name": "scaffold_project",
            "display_name": "Scaffold Project",
            "description": "Create project structure from a game template",
            "category": WorkflowCategory.DEVELOPMENT,
            "slash_command": "/scaffold",
            "steps": [
                {"name": "select_template", "description": "Select best matching project template", "agent_role": "lead_programmer"},
                {"name": "generate_structure", "description": "Generate project file structure", "agent_role": "lead_programmer"},
                {"name": "configure_engine", "description": "Configure engine settings for the game", "agent_role": "engine_programmer"},
                {"name": "setup_systems", "description": "Setup core game systems", "agent_role": "lead_programmer"},
            ],
            "outputs": ["project_files", "engine_config", "system_setup"],
            "quality_gates": ["build_health"],
            "tags": ["scaffold", "project", "setup"],
        },
        {
            "name": "implement_feature",
            "display_name": "Implement Feature",
            "description": "Implement a game feature end-to-end",
            "category": WorkflowCategory.DEVELOPMENT,
            "slash_command": "/implement",
            "steps": [
                {"name": "analyze_requirements", "description": "Analyze feature requirements", "agent_role": "lead_programmer"},
                {"name": "design_architecture", "description": "Design feature architecture", "agent_role": "lead_programmer"},
                {"name": "implement_code", "description": "Write implementation code", "agent_role": "gameplay_programmer"},
                {"name": "integrate", "description": "Integrate with existing systems", "agent_role": "engine_programmer"},
                {"name": "test_integration", "description": "Test integration points", "agent_role": "qa_tester"},
            ],
            "outputs": ["feature_code", "integration_tests", "documentation"],
            "quality_gates": ["code_quality", "build_health"],
            "tags": ["implement", "feature", "code"],
        },
        {
            "name": "code_review",
            "display_name": "Code Review",
            "description": "Review code for quality, patterns, and issues",
            "category": WorkflowCategory.REVIEW,
            "slash_command": "/code-review",
            "steps": [
                {"name": "scan_code", "description": "Scan code for patterns and issues", "agent_role": "lead_programmer"},
                {"name": "check_standards", "description": "Check against coding standards", "agent_role": "lead_programmer"},
                {"name": "identify_issues", "description": "Identify bugs and anti-patterns", "agent_role": "qa_tester"},
                {"name": "suggest_improvements", "description": "Suggest improvements and refactoring", "agent_role": "lead_programmer"},
            ],
            "outputs": ["review_report", "issues_list", "improvement_suggestions"],
            "quality_gates": ["code_quality"],
            "tags": ["review", "quality", "code"],
        },
        {
            "name": "balance_check",
            "display_name": "Balance Check",
            "description": "Check game balance and difficulty curves",
            "category": WorkflowCategory.REVIEW,
            "slash_command": "/balance-check",
            "steps": [
                {"name": "analyze_mechanics", "description": "Analyze game mechanics and parameters", "agent_role": "game_designer"},
                {"name": "simulate_progression", "description": "Simulate player progression curves", "agent_role": "game_designer"},
                {"name": "check_difficulty", "description": "Check difficulty curve and spikes", "agent_role": "game_designer"},
                {"name": "report_findings", "description": "Report balance findings and recommendations", "agent_role": "game_designer"},
            ],
            "outputs": ["balance_report", "difficulty_curve", "recommendations"],
            "tags": ["balance", "difficulty", "design"],
        },
        {
            "name": "smoke_test",
            "display_name": "Smoke Test",
            "description": "Run quick validation tests on the game build",
            "category": WorkflowCategory.TESTING,
            "slash_command": "/smoke-test",
            "steps": [
                {"name": "build_check", "description": "Verify the game builds successfully", "agent_role": "qa_tester"},
                {"name": "startup_test", "description": "Test game starts without errors", "agent_role": "qa_tester"},
                {"name": "basic_gameplay", "description": "Test basic gameplay functions", "agent_role": "qa_tester"},
                {"name": "report_results", "description": "Report smoke test results", "agent_role": "qa_lead"},
            ],
            "outputs": ["test_results", "bug_list", "pass_rate"],
            "quality_gates": ["build_health", "performance"],
            "tags": ["testing", "smoke", "validation"],
        },
        {
            "name": "playtest",
            "display_name": "Playtest",
            "description": "Conduct a structured playtest session",
            "category": WorkflowCategory.TESTING,
            "slash_command": "/playtest",
            "steps": [
                {"name": "prepare_build", "description": "Prepare a playable build", "agent_role": "lead_programmer"},
                {"name": "define_scenarios", "description": "Define playtest scenarios", "agent_role": "game_designer"},
                {"name": "execute_playtest", "description": "Execute playtest scenarios", "agent_role": "qa_tester"},
                {"name": "collect_feedback", "description": "Collect and analyze feedback", "agent_role": "qa_lead"},
                {"name": "report_findings", "description": "Report playtest findings", "agent_role": "qa_lead"},
            ],
            "outputs": ["playtest_report", "feedback_summary", "issue_priorities"],
            "quality_gates": ["playability", "performance"],
            "tags": ["playtest", "feedback", "quality"],
        },
        {
            "name": "milestone_review",
            "display_name": "Milestone Review",
            "description": "Review progress against milestone goals",
            "category": WorkflowCategory.PRODUCTION,
            "slash_command": "/milestone-review",
            "steps": [
                {"name": "check_progress", "description": "Check progress against milestone goals", "agent_role": "producer"},
                {"name": "evaluate_quality", "description": "Evaluate quality of deliverables", "agent_role": "qa_lead"},
                {"name": "assess_risks", "description": "Assess risks and blockers", "agent_role": "producer"},
                {"name": "plan_next", "description": "Plan next milestone", "agent_role": "producer"},
            ],
            "outputs": ["milestone_report", "risk_assessment", "next_plan"],
            "tags": ["milestone", "production", "planning"],
        },
        {
            "name": "release_checklist",
            "display_name": "Release Checklist",
            "description": "Run through the release readiness checklist",
            "category": WorkflowCategory.PRODUCTION,
            "slash_command": "/release-checklist",
            "steps": [
                {"name": "quality_gates", "description": "Verify all quality gates pass", "agent_role": "qa_lead"},
                {"name": "performance_audit", "description": "Run performance audit", "agent_role": "engine_programmer"},
                {"name": "bug_triage", "description": "Triage remaining bugs", "agent_role": "qa_lead"},
                {"name": "build_release", "description": "Build release candidate", "agent_role": "lead_programmer"},
                {"name": "final_verification", "description": "Final verification on release build", "agent_role": "producer"},
            ],
            "outputs": ["release_build", "verification_report", "known_issues"],
            "quality_gates": ["build_health", "performance", "playability"],
            "tags": ["release", "checklist", "production"],
        },
        {
            "name": "prototype",
            "display_name": "Prototype",
            "description": "Quick prototype a game concept",
            "category": WorkflowCategory.CREATIVE,
            "slash_command": "/prototype",
            "steps": [
                {"name": "define_scope", "description": "Define prototype scope and goals", "agent_role": "creative_director"},
                {"name": "build_core", "description": "Build core mechanic prototype", "agent_role": "gameplay_programmer"},
                {"name": "test_feel", "description": "Test game feel and responsiveness", "agent_role": "game_designer"},
                {"name": "iterate", "description": "Iterate based on feel testing", "agent_role": "gameplay_programmer"},
            ],
            "outputs": ["prototype_build", "feel_report", "iteration_notes"],
            "tags": ["prototype", "creative", "iteration"],
        },
        {
            "name": "team_combat",
            "display_name": "Team: Combat",
            "description": "Coordinate team for combat system development",
            "category": WorkflowCategory.ORCHESTRATION,
            "slash_command": "/team-combat",
            "steps": [
                {"name": "design_mechanics", "description": "Design combat mechanics", "agent_role": "game_designer"},
                {"name": "implement_code", "description": "Implement combat code", "agent_role": "gameplay_programmer"},
                {"name": "create_ai", "description": "Create enemy AI behaviors", "agent_role": "ai_programmer"},
                {"name": "add_effects", "description": "Add visual and audio effects", "agent_role": "technical_artist"},
                {"name": "balance_test", "description": "Balance and test combat", "agent_role": "qa_tester"},
            ],
            "outputs": ["combat_system", "ai_behaviors", "effects", "balance_report"],
            "quality_gates": ["combat_balance", "input_responsiveness"],
            "tags": ["team", "combat", "coordination"],
        },
        {
            "name": "team_narrative",
            "display_name": "Team: Narrative",
            "description": "Coordinate team for narrative content development",
            "category": WorkflowCategory.ORCHESTRATION,
            "slash_command": "/team-narrative",
            "steps": [
                {"name": "write_story", "description": "Write story and plot", "agent_role": "writer"},
                {"name": "design_characters", "description": "Design characters and dialogue", "agent_role": "narrative_director"},
                {"name": "create_dialogue", "description": "Create dialogue trees", "agent_role": "writer"},
                {"name": "build_quests", "description": "Build quest system", "agent_role": "gameplay_programmer"},
                {"name": "test_flow", "description": "Test narrative flow", "agent_role": "qa_tester"},
            ],
            "outputs": ["story_content", "dialogue_trees", "quest_system", "flow_report"],
            "quality_gates": ["character_consistency", "quest_flow"],
            "tags": ["team", "narrative", "story"],
        },
    ]

    for defn in skill_defs:
        steps = []
        for i, step_def in enumerate(defn.get("steps", [])):
            steps.append(WorkflowStep(
                name=step_def["name"],
                description=step_def.get("description", ""),
                order=i,
                agent_role=step_def.get("agent_role", ""),
                required_inputs=step_def.get("required_inputs", []),
                outputs=step_def.get("outputs", []),
            ))

        skill = WorkflowSkill(
            name=defn["name"],
            display_name=defn.get("display_name", defn["name"]),
            description=defn.get("description", ""),
            category=defn.get("category", WorkflowCategory.DEVELOPMENT),
            slash_command=defn.get("slash_command", f"/{defn['name']}"),
            steps=steps,
            required_inputs=defn.get("required_inputs", []),
            outputs=defn.get("outputs", []),
            quality_gates=defn.get("quality_gates", []),
            dependencies=defn.get("dependencies", []),
            tags=defn.get("tags", []),
        )
        skills[skill.id] = skill

    return skills


class WorkflowSkillSystem:
    """
    Structured game development workflow system for the SparkLabs
    AI-Native Game Engine.

    Provides workflow skills that guide the creative and technical
    process from concept to release. Each skill encapsulates a
    complete development workflow with defined steps and quality gates.

    Usage:
        wfs = WorkflowSkillSystem()
        skills = wfs.list_skills(category="design")
        execution = wfs.execute_skill(skill_id, inputs={"concept": "platformer"})
    """

    def __init__(self):
        self._skills: Dict[str, WorkflowSkill] = _build_skill_registry()
        self._command_index: Dict[str, str] = {}
        self._executions: List[WorkflowExecution] = []

        for skill in self._skills.values():
            if skill.slash_command:
                self._command_index[skill.slash_command] = skill.id

    def get_skill(self, skill_id: str) -> Optional[WorkflowSkill]:
        return self._skills.get(skill_id)

    def find_by_command(self, command: str) -> Optional[WorkflowSkill]:
        skill_id = self._command_index.get(command)
        if skill_id:
            return self._skills.get(skill_id)
        return None

    def list_skills(
        self,
        category: Optional[WorkflowCategory] = None,
        tag: Optional[str] = None,
    ) -> List[WorkflowSkill]:
        skills = list(self._skills.values())
        if category:
            skills = [s for s in skills if s.category == category]
        if tag:
            skills = [s for s in skills if tag in s.tags]
        return sorted(skills, key=lambda s: (s.category.value, s.name))

    def execute_skill(
        self,
        skill_id: str,
        inputs: Optional[Dict[str, Any]] = None,
    ) -> WorkflowExecution:
        skill = self._skills.get(skill_id)
        if not skill:
            return WorkflowExecution(
                skill_id=skill_id,
                skill_name="unknown",
                status=StepStatus.FAILED,
                error=f"Skill '{skill_id}' not found",
            )

        execution = WorkflowExecution(
            skill_id=skill.id,
            skill_name=skill.name,
            total_steps=len(skill.steps),
            inputs=inputs or {},
            started_at=time.time(),
        )

        for i, step in enumerate(skill.steps):
            execution.current_step = i
            step.status = StepStatus.RUNNING
            step_start = time.time()

            try:
                step.result = self._execute_step(step, execution.inputs, skill)
                step.status = StepStatus.COMPLETED
                step.actual_duration = time.time() - step_start
                execution.step_results.append(step.to_dict())
            except Exception as e:
                step.status = StepStatus.FAILED
                step.error = str(e)
                step.actual_duration = time.time() - step_start
                execution.step_results.append(step.to_dict())
                execution.status = StepStatus.FAILED
                execution.error = f"Step '{step.name}' failed: {e}"
                break

        if execution.status != StepStatus.FAILED:
            execution.status = StepStatus.COMPLETED

        execution.completed_at = time.time()
        execution.duration_ms = (execution.completed_at - execution.started_at) * 1000

        skill.usage_count += 1
        self._executions.append(execution)
        return execution

    def _execute_step(
        self,
        step: WorkflowStep,
        inputs: Dict[str, Any],
        skill: WorkflowSkill,
    ) -> Dict[str, Any]:
        return {
            "step_name": step.name,
            "agent_role": step.agent_role,
            "status": "completed",
            "message": f"Step '{step.name}' executed successfully",
            "skill_category": skill.category.value,
        }

    def get_executions(self, limit: int = 20) -> List[WorkflowExecution]:
        return self._executions[-limit:]

    def get_stats(self) -> Dict[str, Any]:
        by_category: Dict[str, int] = {}
        for s in self._skills.values():
            by_category[s.category.value] = by_category.get(s.category.value, 0) + 1

        total_executions = len(self._executions)
        completed = sum(1 for e in self._executions if e.status == StepStatus.COMPLETED)

        return {
            "total_skills": len(self._skills),
            "by_category": by_category,
            "total_executions": total_executions,
            "completed_executions": completed,
            "success_rate": completed / max(total_executions, 1),
            "avg_duration_ms": (
                sum(e.duration_ms for e in self._executions) / max(total_executions, 1)
            ),
        }


_global_wfs: Optional[WorkflowSkillSystem] = None


def get_workflow_skill_system() -> WorkflowSkillSystem:
    """Get the global WorkflowSkillSystem singleton."""
    global _global_wfs
    if _global_wfs is None:
        _global_wfs = WorkflowSkillSystem()
    return _global_wfs


def reset_workflow_skill_system() -> None:
    """Reset the global WorkflowSkillSystem singleton."""
    global _global_wfs
    _global_wfs = None
