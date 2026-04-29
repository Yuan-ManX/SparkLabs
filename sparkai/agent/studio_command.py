"""
SparkAI Agent - Studio Command System

Comprehensive slash command system for game development workflows.
Organized into categories covering the full game development lifecycle
from concept through release.

Command categories:
  - Onboarding: project setup and navigation
  - Design: game design and brainstorming
  - Development: coding and implementation
  - Art: visual assets and style
  - Audio: sound and music
  - Narrative: story and dialogue
  - QA: testing and quality
  - Production: project management
  - Release: deployment and distribution
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional


class CommandCategory(Enum):
    ONBOARDING = "onboarding"
    DESIGN = "design"
    DEVELOPMENT = "development"
    ART = "art"
    AUDIO = "audio"
    NARRATIVE = "narrative"
    QA = "qa"
    PRODUCTION = "production"
    RELEASE = "release"
    CREATIVE = "creative"
    ORCHESTRATION = "orchestration"


@dataclass
class StudioCommandDef:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    slash: str = ""
    category: CommandCategory = CommandCategory.DEVELOPMENT
    description: str = ""
    agent_role: str = ""
    steps: List[str] = field(default_factory=list)
    inputs: List[str] = field(default_factory=list)
    outputs: List[str] = field(default_factory=list)
    quality_gates: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    enabled: bool = True
    usage_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "slash": self.slash,
            "category": self.category.value,
            "description": self.description,
            "agent_role": self.agent_role,
            "steps": self.steps,
            "inputs": self.inputs,
            "outputs": self.outputs,
            "quality_gates": self.quality_gates,
            "tags": self.tags,
            "enabled": self.enabled,
            "usage_count": self.usage_count,
        }


@dataclass
class CommandExecution:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    command_name: str = ""
    slash: str = ""
    status: str = "pending"
    current_step: int = 0
    total_steps: int = 0
    inputs: Dict[str, Any] = field(default_factory=dict)
    outputs: Dict[str, Any] = field(default_factory=dict)
    step_results: List[Dict[str, Any]] = field(default_factory=list)
    started_at: float = field(default_factory=time.time)
    completed_at: Optional[float] = None
    duration_ms: float = 0.0
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "command_name": self.command_name,
            "slash": self.slash,
            "status": self.status,
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


_SEED_COMMANDS: List[Dict[str, Any]] = [
    {"name": "Start Project", "slash": "/start", "category": CommandCategory.ONBOARDING, "description": "Initialize a new game project with guided setup", "agent_role": "producer", "steps": ["Detect project state", "Configure engine", "Set up workspace"], "inputs": ["project_name", "genre"], "outputs": ["project_config", "workspace_structure"], "quality_gates": ["build_integrity"], "tags": ["setup", "onboarding"]},
    {"name": "Brainstorm", "slash": "/brainstorm", "category": CommandCategory.DESIGN, "description": "Generate creative game concepts and mechanics", "agent_role": "creative_director", "steps": ["Analyze theme", "Generate concepts", "Evaluate feasibility"], "inputs": ["theme", "constraints"], "outputs": ["concept_list", "mechanic_ideas"], "quality_gates": ["design_alignment"], "tags": ["creative", "ideation"]},
    {"name": "Design System", "slash": "/design-system", "category": CommandCategory.DESIGN, "description": "Create detailed game system design document", "agent_role": "game_designer", "steps": ["Define system scope", "Design mechanics", "Specify parameters", "Create test cases"], "inputs": ["system_name", "requirements"], "outputs": ["system_design_doc", "parameter_table"], "quality_gates": ["design_alignment", "build_integrity"], "tags": ["design", "documentation"]},
    {"name": "Map Systems", "slash": "/map-systems", "category": CommandCategory.DESIGN, "description": "Map all game systems and their interdependencies", "agent_role": "game_designer", "steps": ["Inventory systems", "Map dependencies", "Identify conflicts", "Prioritize implementation"], "inputs": ["project_scope"], "outputs": ["system_map", "dependency_graph"], "quality_gates": ["design_alignment"], "tags": ["design", "architecture"]},
    {"name": "Quick Design", "slash": "/quick-design", "category": CommandCategory.DESIGN, "description": "Rapid design pass for prototyping", "agent_role": "game_designer", "steps": ["Capture core loop", "Define MVP features", "Sketch flow"], "inputs": ["concept"], "outputs": ["quick_design_doc"], "quality_gates": [], "tags": ["design", "prototype"]},
    {"name": "Create Architecture", "slash": "/create-architecture", "category": CommandCategory.DEVELOPMENT, "description": "Design the technical architecture for the game", "agent_role": "technical_director", "steps": ["Analyze requirements", "Select patterns", "Define modules", "Plan integration"], "inputs": ["requirements", "constraints"], "outputs": ["architecture_doc", "module_diagram"], "quality_gates": ["build_integrity", "performance_budget"], "tags": ["architecture", "technical"]},
    {"name": "Architecture Decision", "slash": "/adr", "category": CommandCategory.DEVELOPMENT, "description": "Record an architecture decision with context and rationale", "agent_role": "technical_director", "steps": ["State decision", "Document context", "List alternatives", "Record rationale"], "inputs": ["decision_title", "context"], "outputs": ["adr_document"], "quality_gates": [], "tags": ["architecture", "documentation"]},
    {"name": "Dev Story", "slash": "/dev-story", "category": CommandCategory.DEVELOPMENT, "description": "Implement a user story with full development workflow", "agent_role": "gameplay_programmer", "steps": ["Review story requirements", "Plan implementation", "Write code", "Test locally", "Submit for review"], "inputs": ["story_id", "requirements"], "outputs": ["implementation", "test_results"], "quality_gates": ["code_standards", "build_integrity"], "tags": ["development", "implementation"]},
    {"name": "Code Review", "slash": "/code-review", "category": CommandCategory.DEVELOPMENT, "description": "Review code against standards and best practices", "agent_role": "lead_programmer", "steps": ["Analyze code structure", "Check standards", "Identify issues", "Suggest improvements"], "inputs": ["code_path", "scope"], "outputs": ["review_report", "suggestions"], "quality_gates": ["code_standards"], "tags": ["review", "quality"]},
    {"name": "Design Review", "slash": "/design-review", "category": CommandCategory.DESIGN, "description": "Review game design for coherence and fun factor", "agent_role": "creative_director", "steps": ["Evaluate coherence", "Check fun factor", "Assess scope", "Provide feedback"], "inputs": ["design_doc"], "outputs": ["review_report", "feedback"], "quality_gates": ["design_alignment"], "tags": ["review", "design"]},
    {"name": "Art Bible", "slash": "/art-bible", "category": CommandCategory.ART, "description": "Create or update the visual style guide", "agent_role": "art_director", "steps": ["Define style pillars", "Set color palette", "Establish proportions", "Create reference sheet"], "inputs": ["style_direction", "references"], "outputs": ["art_bible_doc", "color_palette", "style_guide"], "quality_gates": ["visual_consistency"], "tags": ["art", "style"]},
    {"name": "Asset Spec", "slash": "/asset-spec", "category": CommandCategory.ART, "description": "Create detailed asset specification for production", "agent_role": "art_director", "steps": ["Define requirements", "Set technical specs", "List animations", "Specify LODs"], "inputs": ["asset_name", "asset_type"], "outputs": ["asset_spec_doc"], "quality_gates": ["visual_consistency"], "tags": ["art", "specification"]},
    {"name": "Sound Design", "slash": "/sound-design", "category": CommandCategory.AUDIO, "description": "Plan sound design for game features", "agent_role": "audio_director", "steps": ["Inventory sound needs", "Define audio style", "Plan spatial audio", "Create priority list"], "inputs": ["feature_name", "mood"], "outputs": ["sound_design_doc", "audio_priority_list"], "quality_gates": [], "tags": ["audio", "design"]},
    {"name": "Create Quest", "slash": "/create-quest", "category": CommandCategory.NARRATIVE, "description": "Design a quest with objectives, rewards, and narrative", "agent_role": "narrative_director", "steps": ["Define quest concept", "Set objectives", "Write dialogue", "Plan rewards", "Create branches"], "inputs": ["quest_name", "quest_type"], "outputs": ["quest_doc", "dialogue_script"], "quality_gates": ["design_alignment"], "tags": ["narrative", "quest"]},
    {"name": "Write Dialogue", "slash": "/write-dialogue", "category": CommandCategory.NARRATIVE, "description": "Write character dialogue with branching options", "agent_role": "writer", "steps": ["Character analysis", "Write lines", "Create branches", "Add conditions"], "inputs": ["character_id", "context"], "outputs": ["dialogue_tree", "character_voices"], "quality_gates": [], "tags": ["narrative", "dialogue"]},
    {"name": "QA Plan", "slash": "/qa-plan", "category": CommandCategory.QA, "description": "Create comprehensive testing plan", "agent_role": "qa_lead", "steps": ["Identify test areas", "Define test cases", "Set acceptance criteria", "Plan automation"], "inputs": ["feature_scope"], "outputs": ["qa_plan_doc", "test_case_list"], "quality_gates": [], "tags": ["qa", "testing"]},
    {"name": "Smoke Check", "slash": "/smoke-check", "category": CommandCategory.QA, "description": "Run quick smoke tests on the build", "agent_role": "qa_tester", "steps": ["Launch build", "Test critical paths", "Check for crashes", "Report results"], "inputs": ["build_path"], "outputs": ["smoke_report", "pass_fail_status"], "quality_gates": ["build_integrity"], "tags": ["qa", "testing"]},
    {"name": "Regression Suite", "slash": "/regression", "category": CommandCategory.QA, "description": "Run full regression test suite", "agent_role": "qa_tester", "steps": ["Load test suite", "Execute tests", "Collect results", "Analyze failures"], "inputs": ["test_scope"], "outputs": ["regression_report", "failure_analysis"], "quality_gates": ["build_integrity"], "tags": ["qa", "regression"]},
    {"name": "Sprint Plan", "slash": "/sprint-plan", "category": CommandCategory.PRODUCTION, "description": "Plan the next sprint with stories and priorities", "agent_role": "producer", "steps": ["Review backlog", "Estimate stories", "Assign resources", "Set milestones"], "inputs": ["sprint_duration", "team_capacity"], "outputs": ["sprint_plan", "story_assignments"], "quality_gates": [], "tags": ["production", "planning"]},
    {"name": "Sprint Status", "slash": "/sprint-status", "category": CommandCategory.PRODUCTION, "description": "Get current sprint progress and blockers", "agent_role": "producer", "steps": ["Collect status", "Identify blockers", "Calculate velocity", "Forecast completion"], "inputs": [], "outputs": ["status_report", "blocker_list"], "quality_gates": [], "tags": ["production", "status"]},
    {"name": "Milestone Review", "slash": "/milestone-review", "category": CommandCategory.PRODUCTION, "description": "Review milestone completion and quality", "agent_role": "producer", "steps": ["Check deliverables", "Evaluate quality", "Assess timeline", "Decide go/no-go"], "inputs": ["milestone_id"], "outputs": ["milestone_report", "go_no_go_decision"], "quality_gates": ["build_integrity", "playability"], "tags": ["production", "review"]},
    {"name": "Bug Report", "slash": "/bug-report", "category": CommandCategory.QA, "description": "File a structured bug report with reproduction steps", "agent_role": "qa_tester", "steps": ["Describe issue", "List reproduction steps", "Set severity", "Assign component"], "inputs": ["description", "severity"], "outputs": ["bug_report"], "quality_gates": [], "tags": ["qa", "bugs"]},
    {"name": "Bug Triage", "slash": "/bug-triage", "category": CommandCategory.QA, "description": "Triage and prioritize bug backlog", "agent_role": "qa_lead", "steps": ["Categorize bugs", "Assess impact", "Set priority", "Assign owners"], "inputs": ["bug_list"], "outputs": ["triage_report", "priority_list"], "quality_gates": [], "tags": ["qa", "bugs"]},
    {"name": "Release Checklist", "slash": "/release-checklist", "category": CommandCategory.RELEASE, "description": "Generate pre-release verification checklist", "agent_role": "producer", "steps": ["Verify build stability", "Check content completeness", "Validate platforms", "Confirm legal"], "inputs": ["release_version", "target_platforms"], "outputs": ["checklist", "verification_status"], "quality_gates": ["build_integrity", "playability"], "tags": ["release", "checklist"]},
    {"name": "Changelog", "slash": "/changelog", "category": CommandCategory.RELEASE, "description": "Generate changelog from commit history", "agent_role": "producer", "steps": ["Collect commits", "Categorize changes", "Format entries", "Review accuracy"], "inputs": ["version", "since_tag"], "outputs": ["changelog_doc"], "quality_gates": [], "tags": ["release", "documentation"]},
    {"name": "Prototype", "slash": "/prototype", "category": CommandCategory.CREATIVE, "description": "Create a rapid prototype to test a concept", "agent_role": "gameplay_programmer", "steps": ["Define core mechanic", "Build minimal version", "Test playability", "Document findings"], "inputs": ["concept", "timebox"], "outputs": ["prototype_build", "findings_doc"], "quality_gates": ["playability"], "tags": ["creative", "prototype"]},
    {"name": "Balance Check", "slash": "/balance-check", "category": CommandCategory.DESIGN, "description": "Analyze game balance and tuning parameters", "agent_role": "game_designer", "steps": ["Collect metrics", "Analyze win rates", "Check economy", "Suggest adjustments"], "inputs": ["game_mode", "metrics_data"], "outputs": ["balance_report", "tuning_suggestions"], "quality_gates": ["design_alignment"], "tags": ["design", "balance"]},
    {"name": "Perf Profile", "slash": "/perf-profile", "category": CommandCategory.DEVELOPMENT, "description": "Profile performance and identify bottlenecks", "agent_role": "engine_programmer", "steps": ["Set up profiling", "Capture metrics", "Analyze hotspots", "Suggest optimizations"], "inputs": ["target_scene", "duration"], "outputs": ["profile_report", "optimization_list"], "quality_gates": ["performance_budget"], "tags": ["performance", "optimization"]},
    {"name": "Tech Debt", "slash": "/tech-debt", "category": CommandCategory.DEVELOPMENT, "description": "Audit technical debt and create remediation plan", "agent_role": "lead_programmer", "steps": ["Scan codebase", "Identify debt items", "Assess impact", "Prioritize fixes"], "inputs": ["scope"], "outputs": ["debt_report", "remediation_plan"], "quality_gates": ["code_standards"], "tags": ["technical", "maintenance"]},
    {"name": "Team Combat", "slash": "/team-combat", "category": CommandCategory.ORCHESTRATION, "description": "Coordinate combat system team across design, code, and VFX", "agent_role": "creative_director", "steps": ["Assign combat roles", "Coordinate design-code-art", "Review integration", "Test gameplay feel"], "inputs": ["combat_system_scope"], "outputs": ["combat_system", "integration_report"], "quality_gates": ["playability", "visual_consistency"], "tags": ["team", "combat"]},
    {"name": "Team UI", "slash": "/team-ui", "category": CommandCategory.ORCHESTRATION, "description": "Coordinate UI team across UX, art, and programming", "agent_role": "art_director", "steps": ["Define UX flows", "Design UI mockups", "Implement UI code", "Test accessibility"], "inputs": ["ui_scope"], "outputs": ["ui_system", "accessibility_report"], "quality_gates": ["visual_consistency", "playability"], "tags": ["team", "ui"]},
    {"name": "Team Narrative", "slash": "/team-narrative", "category": CommandCategory.ORCHESTRATION, "description": "Coordinate narrative team across writing, dialogue, and quests", "agent_role": "narrative_director", "steps": ["Plan story arc", "Write dialogue", "Implement quests", "Test narrative flow"], "inputs": ["narrative_scope"], "outputs": ["narrative_system", "dialogue_database"], "quality_gates": ["design_alignment"], "tags": ["team", "narrative"]},
    {"name": "Team Level", "slash": "/team-level", "category": CommandCategory.ORCHESTRATION, "description": "Coordinate level design team across layout, encounters, and flow", "agent_role": "game_designer", "steps": ["Plan level layout", "Design encounters", "Place props and lighting", "Playtest pacing"], "inputs": ["level_scope"], "outputs": ["level_build", "encounter_data"], "quality_gates": ["playability", "visual_consistency"], "tags": ["team", "level"]},
    {"name": "Team QA", "slash": "/team-qa", "category": CommandCategory.ORCHESTRATION, "description": "Coordinate QA team for comprehensive testing", "agent_role": "qa_lead", "steps": ["Plan test coverage", "Execute test suites", "Triage findings", "Verify fixes"], "inputs": ["test_scope"], "outputs": ["qa_report", "coverage_metrics"], "quality_gates": ["build_integrity"], "tags": ["team", "qa"]},
    {"name": "Gate Check", "slash": "/gate-check", "category": CommandCategory.QA, "description": "Run quality gate checks for current phase", "agent_role": "qa_lead", "steps": ["Identify phase", "Run applicable gates", "Collect results", "Render verdict"], "inputs": ["phase"], "outputs": ["gate_report", "verdict"], "quality_gates": [], "tags": ["qa", "quality"]},
    {"name": "Consistency Check", "slash": "/consistency-check", "category": CommandCategory.QA, "description": "Check cross-system consistency and coherence", "agent_role": "creative_director", "steps": ["Audit design docs", "Check code-design alignment", "Verify asset consistency", "Report discrepancies"], "inputs": ["scope"], "outputs": ["consistency_report", "discrepancy_list"], "quality_gates": ["visual_consistency", "design_alignment"], "tags": ["qa", "consistency"]},
    {"name": "Scope Check", "slash": "/scope-check", "category": CommandCategory.PRODUCTION, "description": "Analyze project scope and identify creep risks", "agent_role": "producer", "steps": ["Inventory features", "Estimate effort", "Compare to capacity", "Flag risks"], "inputs": [], "outputs": ["scope_report", "risk_list"], "quality_gates": [], "tags": ["production", "scope"]},
    {"name": "Retrospective", "slash": "/retrospective", "category": CommandCategory.PRODUCTION, "description": "Conduct a sprint retrospective with action items", "agent_role": "producer", "steps": ["Gather feedback", "Identify wins", "Identify improvements", "Create action items"], "inputs": ["sprint_id"], "outputs": ["retro_doc", "action_items"], "quality_gates": [], "tags": ["production", "retrospective"]},
    {"name": "Launch Checklist", "slash": "/launch-checklist", "category": CommandCategory.RELEASE, "description": "Final pre-launch verification and sign-off", "agent_role": "producer", "steps": ["Verify all systems", "Confirm platform compliance", "Check store listings", "Final smoke test"], "inputs": ["platforms"], "outputs": ["launch_readiness_report", "sign_off_sheet"], "quality_gates": ["build_integrity", "playability", "visual_consistency"], "tags": ["release", "launch"]},
]


class StudioCommandSystem:
    """
    Comprehensive slash command system for game development workflows.

    Provides 35+ organized commands spanning the full game development
    lifecycle from concept through release.
    """

    def __init__(self):
        self._commands: Dict[str, StudioCommandDef] = {}
        self._executions: Dict[str, CommandExecution] = {}
        self._execution_count: int = 0
        self._completed_count: int = 0
        self._failed_count: int = 0
        self._history: List[Dict[str, Any]] = []
        self._load_seed_commands()

    def _load_seed_commands(self) -> None:
        for cmd_data in _SEED_COMMANDS:
            cmd = StudioCommandDef(
                name=cmd_data["name"],
                slash=cmd_data["slash"],
                category=cmd_data["category"],
                description=cmd_data["description"],
                agent_role=cmd_data["agent_role"],
                steps=cmd_data["steps"],
                inputs=cmd_data["inputs"],
                outputs=cmd_data["outputs"],
                quality_gates=cmd_data["quality_gates"],
                tags=cmd_data["tags"],
            )
            self._commands[cmd.slash] = cmd

    def list_commands(
        self,
        category: Optional[CommandCategory] = None,
        tag: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        cmds = list(self._commands.values())
        if category:
            cmds = [c for c in cmds if c.category == category]
        if tag:
            cmds = [c for c in cmds if tag in c.tags]
        return [c.to_dict() for c in cmds]

    def get_command(self, slash: str) -> Optional[Dict[str, Any]]:
        cmd = self._commands.get(slash)
        if not cmd:
            normalized = f"/{slash}" if not slash.startswith("/") else slash
            cmd = self._commands.get(normalized)
        return cmd.to_dict() if cmd else None

    def find_command(self, query: str) -> List[Dict[str, Any]]:
        query_lower = query.lower()
        results = []
        for cmd in self._commands.values():
            if (query_lower in cmd.name.lower() or
                query_lower in cmd.slash.lower() or
                query_lower in cmd.description.lower() or
                any(query_lower in t for t in cmd.tags)):
                results.append(cmd.to_dict())
        return results

    def execute_command(self, slash: str, inputs: Optional[Dict[str, Any]] = None) -> CommandExecution:
        cmd = self._commands.get(slash)
        if not cmd:
            normalized = f"/{slash}" if not slash.startswith("/") else slash
            cmd = self._commands.get(normalized)

        execution = CommandExecution(
            command_name=cmd.name if cmd else "Unknown",
            slash=slash,
            inputs=inputs or {},
            total_steps=len(cmd.steps) if cmd else 0,
        )

        if not cmd:
            execution.status = "failed"
            execution.error = f"Command '{slash}' not found"
            execution.completed_at = time.time()
            self._failed_count += 1
        elif not cmd.enabled:
            execution.status = "failed"
            execution.error = f"Command '{slash}' is disabled"
            execution.completed_at = time.time()
            self._failed_count += 1
        else:
            cmd.usage_count += 1
            execution.status = "running"
            execution.current_step = 0

            for i, step in enumerate(cmd.steps):
                execution.current_step = i + 1
                execution.step_results.append({
                    "step": step,
                    "status": "completed",
                    "order": i + 1,
                })

            execution.status = "completed"
            execution.completed_at = time.time()
            execution.duration_ms = (execution.completed_at - execution.started_at) * 1000

            for output_key in cmd.outputs:
                execution.outputs[output_key] = f"Generated {output_key}"

            self._completed_count += 1

        self._executions[execution.id] = execution
        self._execution_count += 1

        self._history.append({
            "event": "execute",
            "command": slash,
            "status": execution.status,
            "duration_ms": execution.duration_ms,
            "timestamp": time.time(),
        })

        return execution

    def get_execution(self, execution_id: str) -> Optional[Dict[str, Any]]:
        execution = self._executions.get(execution_id)
        return execution.to_dict() if execution else None

    def list_executions(self, limit: int = 20) -> List[Dict[str, Any]]:
        executions = sorted(self._executions.values(), key=lambda e: e.started_at, reverse=True)
        return [e.to_dict() for e in executions[:limit]]

    def list_categories(self) -> List[Dict[str, Any]]:
        categories = {}
        for cmd in self._commands.values():
            cat = cmd.category.value
            if cat not in categories:
                categories[cat] = {"name": cat, "command_count": 0, "commands": []}
            categories[cat]["command_count"] += 1
            categories[cat]["commands"].append(cmd.slash)
        return list(categories.values())

    def get_stats(self) -> Dict[str, Any]:
        return {
            "total_commands": len(self._commands),
            "enabled_commands": sum(1 for c in self._commands.values() if c.enabled),
            "by_category": {cat.value: sum(1 for c in self._commands.values() if c.category == cat) for cat in CommandCategory},
            "total_executions": self._execution_count,
            "completed_executions": self._completed_count,
            "failed_executions": self._failed_count,
            "success_rate": self._completed_count / self._execution_count if self._execution_count > 0 else 0.0,
            "top_commands": sorted(
                [(c.slash, c.usage_count) for c in self._commands.values()],
                key=lambda x: x[1], reverse=True,
            )[:5],
        }

    def get_history(self, limit: int = 20) -> List[Dict[str, Any]]:
        return self._history[-limit:]


_studio_command_system: Optional[StudioCommandSystem] = None


def get_studio_command_system() -> StudioCommandSystem:
    global _studio_command_system
    if _studio_command_system is None:
        _studio_command_system = StudioCommandSystem()
    return _studio_command_system
