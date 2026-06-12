"""
SparkAI Core - Agent-Engine Orchestrator

UNIFIED AI GAME ORCHESTRATION PIPELINE — the central bridge between the
Agent Intelligence layer and the Game Engine layer. Provides end-to-end
game creation workflows, combining multiple AI and engine subsystems
into coherent pipelines.

Architecture:
  AgentEngineOrchestrator (Singleton)
    |-- PipelineWorkflow (multi-stage development pipeline)
    |-- PipelineTask (individual task within a pipeline stage)
    |-- GameProject (tracked game project with all workflows)
    |-- OrchestrationEvent (cross-module communication events)
    |-- PipelineMetrics (execution and performance tracking)

Pipeline Stages:
  IDEATION -> DESIGN -> GENERATION -> TESTING -> DEPLOYMENT -> ITERATION

Workflow Types:
  GAME_FROM_SCRATCH, FEATURE_ADDITION, BALANCE_TUNING,
  BUG_FIXING, CONTENT_EXPANSION

Orchestration Modes:
  SEQUENTIAL (one task after another)
  PARALLEL (concurrent independent tasks)
  ADAPTIVE (AI-driven decision making)
  INTERACTIVE (human-in-the-loop)

Usage:
    orchestrator = get_agent_engine_orchestrator()
    project = orchestrator.create_game_from_description(
        "A sci-fi RPG with procedurally generated planets",
        "Sci-Fi RPG",
        "PC"
    )
    workflow = orchestrator.execute_workflow(project.workflows[0])
    report = orchestrator.generate_summary(workflow.workflow_id)
"""

from __future__ import annotations

import json
import threading
import time as _time_module
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class PipelineStage(str, Enum):
    """Stages in the game development pipeline."""
    IDEATION = "ideation"
    DESIGN = "design"
    GENERATION = "generation"
    TESTING = "testing"
    DEPLOYMENT = "deployment"
    ITERATION = "iteration"


class OrchestrationMode(str, Enum):
    """Execution mode for pipeline workflows."""
    SEQUENTIAL = "sequential"
    PARALLEL = "parallel"
    ADAPTIVE = "adaptive"
    INTERACTIVE = "interactive"


class PipelineStatus(str, Enum):
    """Current status of a pipeline workflow or task."""
    READY = "ready"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"


class WorkflowType(str, Enum):
    """Category of game development workflow."""
    GAME_FROM_SCRATCH = "game_from_scratch"
    FEATURE_ADDITION = "feature_addition"
    BALANCE_TUNING = "balance_tuning"
    BUG_FIXING = "bug_fixing"
    CONTENT_EXPANSION = "content_expansion"


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------

@dataclass
class PipelineTask:
    """A single executable task within a pipeline workflow stage."""
    task_id: str = field(default_factory=lambda: uuid.uuid4().hex[:8])
    stage: PipelineStage = PipelineStage.IDEATION
    name: str = ""
    description: str = ""
    agent_module: str = ""
    engine_module: str = ""
    status: PipelineStatus = PipelineStatus.READY
    started_at: float = 0.0
    completed_at: float = 0.0
    result: Dict[str, Any] = field(default_factory=dict)
    dependencies: List[str] = field(default_factory=list)
    priority: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "task_id": self.task_id,
            "stage": self.stage.value,
            "name": self.name,
            "description": self.description,
            "agent_module": self.agent_module,
            "engine_module": self.engine_module,
            "status": self.status.value,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "result": self.result,
            "dependencies": self.dependencies,
            "priority": self.priority,
        }


@dataclass
class PipelineWorkflow:
    """A multi-stage pipeline workflow composed of ordered tasks."""
    workflow_id: str = field(default_factory=lambda: uuid.uuid4().hex[:8])
    name: str = ""
    workflow_type: WorkflowType = WorkflowType.GAME_FROM_SCRATCH
    stages: List[PipelineStage] = field(default_factory=list)
    tasks: List[PipelineTask] = field(default_factory=list)
    status: PipelineStatus = PipelineStatus.READY
    mode: OrchestrationMode = OrchestrationMode.SEQUENTIAL
    created_at: float = field(default_factory=lambda: _time_module.time())
    updated_at: float = field(default_factory=lambda: _time_module.time())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "workflow_id": self.workflow_id,
            "name": self.name,
            "workflow_type": self.workflow_type.value,
            "stages": [s.value for s in self.stages],
            "tasks": [t.to_dict() for t in self.tasks],
            "status": self.status.value,
            "mode": self.mode.value,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


@dataclass
class GameProject:
    """A tracked game project with all associated workflows and metadata."""
    project_id: str = field(default_factory=lambda: uuid.uuid4().hex[:8])
    name: str = ""
    description: str = ""
    genre: str = ""
    platform: str = ""
    current_stage: PipelineStage = PipelineStage.IDEATION
    workflows: List[str] = field(default_factory=list)
    scene_count: int = 0
    entity_count: int = 0
    script_count: int = 0
    created_at: float = field(default_factory=lambda: _time_module.time())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "project_id": self.project_id,
            "name": self.name,
            "description": self.description,
            "genre": self.genre,
            "platform": self.platform,
            "current_stage": self.current_stage.value,
            "workflows": self.workflows,
            "scene_count": self.scene_count,
            "entity_count": self.entity_count,
            "script_count": self.script_count,
            "created_at": self.created_at,
        }


@dataclass
class OrchestrationEvent:
    """A cross-module communication event between agent and engine subsystems."""
    event_id: str = field(default_factory=lambda: uuid.uuid4().hex[:8])
    event_type: str = ""
    source_module: str = ""
    target_module: str = ""
    payload: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=lambda: _time_module.time())
    handled: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": self.event_id,
            "event_type": self.event_type,
            "source_module": self.source_module,
            "target_module": self.target_module,
            "payload": self.payload,
            "timestamp": self.timestamp,
            "handled": self.handled,
        }


@dataclass
class PipelineMetrics:
    """Execution and performance metrics for a pipeline workflow."""
    pipeline_id: str = ""
    total_tasks: int = 0
    completed_tasks: int = 0
    failed_tasks: int = 0
    avg_task_duration_ms: float = 0.0
    total_duration_ms: float = 0.0
    agent_calls: int = 0
    engine_calls: int = 0
    errors: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "pipeline_id": self.pipeline_id,
            "total_tasks": self.total_tasks,
            "completed_tasks": self.completed_tasks,
            "failed_tasks": self.failed_tasks,
            "avg_task_duration_ms": self.avg_task_duration_ms,
            "total_duration_ms": self.total_duration_ms,
            "agent_calls": self.agent_calls,
            "engine_calls": self.engine_calls,
            "errors": self.errors,
        }


# ---------------------------------------------------------------------------
# Internal helper
# ---------------------------------------------------------------------------

def _task_name_key(task: PipelineTask) -> Tuple[int, int]:
    """Sort key: lower priority number first, then by name for stability."""
    return (task.priority, hash(task.name) % 10000)


# ---------------------------------------------------------------------------
# AgentEngineOrchestrator
# ---------------------------------------------------------------------------

class AgentEngineOrchestrator:
    """
    Unified AI Game Orchestration Pipeline.

    Bridges the Agent Intelligence layer and Game Engine layer, providing
    end-to-end game creation workflows that combine multiple AI agents
    and engine subsystems into coherent, executable pipelines.

    Singleton — use get_agent_engine_orchestrator() to access.
    """

    _instance: Optional["AgentEngineOrchestrator"] = None
    _lock: threading.RLock = threading.RLock()

    # ---- Stage-to-agent/engine mappings ----

    _STAGE_AGENT_ENGINES: Dict[PipelineStage, List[Tuple[str, str, str, str]]] = {
        PipelineStage.IDEATION: [
            ("creative_director", "game_design_intelligence", "Concept Analysis",
             "Analyze game concept, genre conventions, and target audience expectations"),
            ("creative_director", "game_design_intelligence", "Genre Research",
             "Research genre tropes, competitor analysis, and market positioning"),
            ("creative_director", "interaction_synthesis", "Mechanic Brainstorming",
             "Generate core gameplay mechanics and interaction patterns"),
            ("creative_director", "game_design_intelligence", "Core Loop Design",
             "Design the primary gameplay loop and engagement drivers"),
        ],
        PipelineStage.DESIGN: [
            ("story_forge", "dialogue_system", "Story Creation",
             "Craft the narrative structure, plot arcs, and story beats"),
            ("world_builder", "scene_manager", "World Design",
             "Design game world geography, biomes, and region layouts"),
            ("quest_generator", "quest_system", "Quest Design",
             "Generate main questline and side quest structures"),
            ("level_designer", "tilemap_system", "Level Design",
             "Design individual level layouts and encounter placements"),
            ("theme_designer", "ui_system", "UI/UX Design",
             "Design user interface wireframes and interaction flows"),
            ("interaction_designer", "input_mapping", "Control Design",
             "Define input mappings and player control schemes"),
        ],
        PipelineStage.GENERATION: [
            ("game_code_generator", "entity_component_system", "Entity Creation",
             "Generate game entity definitions and component compositions"),
            ("agentic_coding", "visual_scripting", "Script Generation",
             "Generate gameplay scripts, behaviors, and logic nodes"),
            ("scene_director", "scene_manager", "Scene Setup",
             "Assemble scenes with entities, lighting, and camera configurations"),
            ("asset_harmonizer", "asset_pipeline", "Asset Configuration",
             "Configure asset pipelines, import settings, and texture atlases"),
            ("audio_composer", "audio_system", "Audio Setup",
             "Configure audio buses, sound effects, and ambient layers"),
            ("world_composer", "procedural_dungeon", "World Population",
             "Populate world with NPCs, items, and environmental details"),
        ],
        PipelineStage.TESTING: [
            ("game_testing", "game_state_analyzer", "Playtest Simulation",
             "Run automated playthroughs and collect gameplay metrics"),
            ("balancing", "combat_system", "Balance Verification",
             "Verify combat balance, difficulty curves, and progression pacing"),
            ("live_debugger", "profiler_system", "Bug Detection",
             "Scan for runtime errors, performance issues, and edge cases"),
            ("performance_advisor", "performance_overlay", "Performance Profiling",
             "Profile frame times, memory usage, and resource utilization"),
            ("accessibility_auditor", "ui_system", "Accessibility Audit",
             "Verify accessibility standards and inclusive design compliance"),
        ],
        PipelineStage.DEPLOYMENT: [
            ("build_orchestrator", "build_pipeline", "Package Bundling",
             "Compile, package, and optimize game assets for distribution"),
            ("build_orchestrator", "project_exporter", "Export Preparation",
             "Configure platform-specific export settings and target profiles"),
            ("documentation_generator", "resource_pack", "Documentation Generation",
             "Generate API docs, player manuals, and developer references"),
            ("cross_platform", "export_pipeline", "Multi-Platform Export",
             "Generate builds for all target platforms with platform-specific tuning"),
        ],
        PipelineStage.ITERATION: [
            ("insights_generator", "game_telemetry", "Analytics Review",
             "Analyze playtest data and identify improvement opportunities"),
            ("game_design_intelligence", "game_state_analyzer", "Design Iteration",
             "Refine game mechanics based on testing feedback"),
            ("reflection_loop", "adaptive_content", "Continuous Improvement",
             "Apply learned improvements and trigger re-generation cycles"),
        ],
    }

    def __new__(cls) -> "AgentEngineOrchestrator":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    @classmethod
    def get_instance(cls) -> "AgentEngineOrchestrator":
        """Return the singleton instance, creating it if necessary."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def __init__(self) -> None:
        _time_module.sleep(0.001)
        if hasattr(self, "_initialized") and self._initialized:
            return
        self._projects: Dict[str, GameProject] = {}
        self._workflows: Dict[str, PipelineWorkflow] = {}
        self._tasks: Dict[str, PipelineTask] = {}
        self._events: Dict[str, OrchestrationEvent] = {}
        self._event_queue: Dict[str, List[str]] = {}
        self._total_agent_calls: int = 0
        self._total_engine_calls: int = 0
        self._total_workflows_created: int = 0
        self._total_workflows_completed: int = 0
        self._initialized = True

    # ------------------------------------------------------------------
    # Project Management
    # ------------------------------------------------------------------

    def create_project(
        self,
        name: str,
        description: str,
        genre: str,
        platform: str,
    ) -> GameProject:
        """Create a new game project."""
        project = GameProject(
            name=name,
            description=description,
            genre=genre,
            platform=platform,
        )
        self._projects[project.project_id] = project
        return project

    def get_project(self, project_id: str) -> Optional[GameProject]:
        """Retrieve a game project by ID."""
        return self._projects.get(project_id)

    def list_projects(self) -> List[GameProject]:
        """List all registered game projects."""
        return list(self._projects.values())

    def _update_project_stage(self, project_id: str, stage: PipelineStage) -> None:
        project = self._projects.get(project_id)
        if project:
            project.current_stage = stage

    # ------------------------------------------------------------------
    # Workflow Management
    # ------------------------------------------------------------------

    def create_workflow(
        self,
        name: str,
        workflow_type: WorkflowType,
        mode: OrchestrationMode,
        stages: Optional[List[PipelineStage]] = None,
    ) -> PipelineWorkflow:
        """Create a new pipeline workflow."""
        if stages is None:
            stages = list(PipelineStage)
        workflow = PipelineWorkflow(
            name=name,
            workflow_type=workflow_type,
            mode=mode,
            stages=stages,
        )
        self._workflows[workflow.workflow_id] = workflow
        self._total_workflows_created += 1
        return workflow

    def add_task_to_workflow(
        self,
        workflow_id: str,
        stage: PipelineStage,
        name: str,
        agent_module: str,
        engine_module: str,
        description: str = "",
        dependencies: Optional[List[str]] = None,
        priority: int = 0,
    ) -> PipelineTask:
        """Add a task to an existing workflow."""
        workflow = self._workflows.get(workflow_id)
        if workflow is None:
            raise ValueError(f"Workflow not found: {workflow_id}")

        task = PipelineTask(
            stage=stage,
            name=name,
            description=description,
            agent_module=agent_module,
            engine_module=engine_module,
            dependencies=dependencies or [],
            priority=priority,
        )
        self._tasks[task.task_id] = task
        workflow.tasks.append(task)
        workflow.updated_at = _time_module.time()
        return task

    def get_workflow(self, workflow_id: str) -> Optional[PipelineWorkflow]:
        """Retrieve a workflow by ID."""
        return self._workflows.get(workflow_id)

    def list_workflows(self, project_id: Optional[str] = None) -> List[PipelineWorkflow]:
        """List workflows, optionally filtered by project."""
        if project_id is None:
            return list(self._workflows.values())
        project = self._projects.get(project_id)
        if project is None:
            return []
        return [
            w for w in self._workflows.values()
            if w.workflow_id in project.workflows
        ]

    def get_workflow_status(self, workflow_id: str) -> Dict[str, Any]:
        """Get detailed status of a workflow."""
        workflow = self._workflows.get(workflow_id)
        if workflow is None:
            return {"error": f"Workflow not found: {workflow_id}"}

        tasks_by_stage: Dict[str, List[Dict[str, Any]]] = {}
        for stage in PipelineStage:
            stage_tasks = [t for t in workflow.tasks if t.stage == stage]
            tasks_by_stage[stage.value] = [
                {
                    "task_id": t.task_id,
                    "name": t.name,
                    "status": t.status.value,
                    "agent_module": t.agent_module,
                    "engine_module": t.engine_module,
                }
                for t in stage_tasks
            ]

        completed = sum(1 for t in workflow.tasks if t.status == PipelineStatus.COMPLETED)
        failed = sum(1 for t in workflow.tasks if t.status == PipelineStatus.FAILED)
        total = len(workflow.tasks)

        return {
            "workflow_id": workflow.workflow_id,
            "name": workflow.name,
            "workflow_type": workflow.workflow_type.value,
            "status": workflow.status.value,
            "mode": workflow.mode.value,
            "progress": f"{completed}/{total}",
            "completion_pct": round((completed / total * 100), 1) if total > 0 else 0.0,
            "failed": failed,
            "stages": tasks_by_stage,
            "created_at": workflow.created_at,
            "updated_at": workflow.updated_at,
        }

    # ------------------------------------------------------------------
    # Workflow Execution
    # ------------------------------------------------------------------

    def execute_workflow(self, workflow_id: str) -> PipelineWorkflow:
        """Execute all tasks in a workflow in dependency-aware order."""
        workflow = self._workflows.get(workflow_id)
        if workflow is None:
            raise ValueError(f"Workflow not found: {workflow_id}")

        workflow.status = PipelineStatus.RUNNING
        workflow.updated_at = _time_module.time()

        start_time = _time_module.time()

        try:
            # Collect all tasks and organize by stage
            task_map: Dict[str, PipelineTask] = {t.task_id: t for t in workflow.tasks}
            completed_ids: Set[str] = set()
            failed_ids: Set[str] = set()

            # Process stages in order
            for stage in workflow.stages:
                stage_tasks = sorted(
                    [t for t in workflow.tasks if t.stage == stage and t.status != PipelineStatus.COMPLETED],
                    key=_task_name_key,
                    reverse=False,
                )

                if workflow.mode == OrchestrationMode.PARALLEL:
                    self._execute_stage_parallel(stage_tasks, task_map, completed_ids, failed_ids)
                else:
                    self._execute_stage_sequential(stage_tasks, task_map, completed_ids, failed_ids)

            # Determine final status
            if failed_ids:
                workflow.status = PipelineStatus.FAILED if len(failed_ids) == len(workflow.tasks) else PipelineStatus.COMPLETED
            else:
                workflow.status = PipelineStatus.COMPLETED
                self._total_workflows_completed += 1

        except Exception:
            workflow.status = PipelineStatus.FAILED

        workflow.updated_at = _time_module.time()
        elapsed = workflow.updated_at - start_time

        # Link back to project
        for project in self._projects.values():
            if workflow_id in project.workflows:
                project.current_stage = workflow.stages[-1] if workflow.status == PipelineStatus.COMPLETED else project.current_stage
                project.updated_at = workflow.updated_at  # type: ignore[attr-defined]

        return workflow

    def _execute_stage_sequential(
        self,
        tasks: List[PipelineTask],
        task_map: Dict[str, PipelineTask],
        completed_ids: Set[str],
        failed_ids: Set[str],
    ) -> None:
        """Execute tasks one at a time within a stage."""
        for task in tasks:
            deps_satisfied = all(
                dep in completed_ids
                for dep in task.dependencies
            )
            if not deps_satisfied:
                task.status = PipelineStatus.FAILED
                task.result = {"error": "Unresolved dependencies"}
                failed_ids.add(task.task_id)
                continue

            self._simulate_task_execution(task)

            if task.status == PipelineStatus.COMPLETED:
                completed_ids.add(task.task_id)
            else:
                failed_ids.add(task.task_id)

    def _execute_stage_parallel(
        self,
        tasks: List[PipelineTask],
        task_map: Dict[str, PipelineTask],
        completed_ids: Set[str],
        failed_ids: Set[str],
    ) -> None:
        """Execute all tasks in a stage simultaneously (simulated)."""
        # Resolve dependency groups
        ready: List[PipelineTask] = []
        blocked: List[PipelineTask] = []

        for task in tasks:
            deps_satisfied = all(dep in completed_ids for dep in task.dependencies)
            if deps_satisfied:
                ready.append(task)
            else:
                blocked.append(task)

        # Simulate parallel execution of ready tasks
        for task in ready:
            self._simulate_task_execution(task)
            if task.status == PipelineStatus.COMPLETED:
                completed_ids.add(task.task_id)
            else:
                failed_ids.add(task.task_id)

        # Process blocked tasks sequentially as fallback
        for task in blocked:
            deps_satisfied = all(dep in completed_ids for dep in task.dependencies)
            if deps_satisfied:
                self._simulate_task_execution(task)
                if task.status == PipelineStatus.COMPLETED:
                    completed_ids.add(task.task_id)
                else:
                    failed_ids.add(task.task_id)
            else:
                task.status = PipelineStatus.FAILED
                task.result = {"error": "Unresolved dependencies in parallel mode"}
                failed_ids.add(task.task_id)

    def execute_task(self, task_id: str) -> PipelineTask:
        """Execute a single task by ID."""
        task = self._tasks.get(task_id)
        if task is None:
            raise ValueError(f"Task not found: {task_id}")
        self._simulate_task_execution(task)
        return task

    def _simulate_task_execution(self, task: PipelineTask) -> None:
        """Simulate executing a single task, updating status and metrics."""
        task.status = PipelineStatus.RUNNING
        task.started_at = _time_module.time()

        # Record agent and engine calls for metrics
        if task.agent_module:
            self._total_agent_calls += 1
        if task.engine_module:
            self._total_engine_calls += 1

        # Simulated work
        _time_module.sleep(0.001)

        task.completed_at = _time_module.time()
        task.status = PipelineStatus.COMPLETED
        task.result = {
            "success": True,
            "agent_module": task.agent_module,
            "engine_module": task.engine_module,
            "duration_ms": round((task.completed_at - task.started_at) * 1000, 2),
            "output": f"Completed: {task.name}",
        }

    def pause_workflow(self, workflow_id: str) -> bool:
        """Pause a running workflow."""
        workflow = self._workflows.get(workflow_id)
        if workflow is None or workflow.status != PipelineStatus.RUNNING:
            return False
        workflow.status = PipelineStatus.PAUSED
        workflow.updated_at = _time_module.time()
        return True

    def resume_workflow(self, workflow_id: str) -> bool:
        """Resume a paused workflow."""
        workflow = self._workflows.get(workflow_id)
        if workflow is None or workflow.status != PipelineStatus.PAUSED:
            return False
        workflow.status = PipelineStatus.RUNNING
        workflow.updated_at = _time_module.time()
        return True

    # ------------------------------------------------------------------
    # Event Bus
    # ------------------------------------------------------------------

    def send_event(
        self,
        event_type: str,
        source_module: str,
        target_module: str,
        payload: Optional[Dict[str, Any]] = None,
    ) -> OrchestrationEvent:
        """Send an orchestration event between modules."""
        event = OrchestrationEvent(
            event_type=event_type,
            source_module=source_module,
            target_module=target_module,
            payload=payload or {},
        )
        self._events[event.event_id] = event

        # Index by target module for efficient lookup
        if target_module not in self._event_queue:
            self._event_queue[target_module] = []
        self._event_queue[target_module].append(event.event_id)

        return event

    def get_pending_events(self, module_name: str) -> List[OrchestrationEvent]:
        """Get all unhandled events for a specific module."""
        event_ids = self._event_queue.get(module_name, [])
        events = [
            self._events[eid]
            for eid in event_ids
            if eid in self._events and not self._events[eid].handled
        ]
        return events

    def _mark_event_handled(self, event_id: str) -> None:
        event = self._events.get(event_id)
        if event:
            event.handled = True

    # ------------------------------------------------------------------
    # Metrics
    # ------------------------------------------------------------------

    def get_pipeline_metrics(self, workflow_id: str) -> PipelineMetrics:
        """Calculate pipeline execution metrics for a workflow."""
        workflow = self._workflows.get(workflow_id)
        if workflow is None:
            return PipelineMetrics(pipeline_id=workflow_id)

        total = len(workflow.tasks)
        completed = sum(1 for t in workflow.tasks if t.status == PipelineStatus.COMPLETED)
        failed = sum(1 for t in workflow.tasks if t.status == PipelineStatus.FAILED)

        durations = [
            (t.completed_at - t.started_at) * 1000
            for t in workflow.tasks
            if t.started_at > 0 and t.completed_at > 0
        ]
        avg_duration = sum(durations) / len(durations) if durations else 0.0
        total_duration = sum(durations)

        agent_calls = sum(1 for t in workflow.tasks if t.agent_module)
        engine_calls = sum(1 for t in workflow.tasks if t.engine_module)

        errors = [
            t.result.get("error", f"Task {t.task_id} {t.status.value}")
            for t in workflow.tasks
            if t.status == PipelineStatus.FAILED
        ]

        return PipelineMetrics(
            pipeline_id=workflow_id,
            total_tasks=total,
            completed_tasks=completed,
            failed_tasks=failed,
            avg_task_duration_ms=round(avg_duration, 2),
            total_duration_ms=round(total_duration, 2),
            agent_calls=agent_calls,
            engine_calls=engine_calls,
            errors=errors,
        )

    def get_stats(self) -> Dict[str, Any]:
        """Get aggregate statistics across all projects and workflows."""
        total_projects = len(self._projects)
        total_workflows = len(self._workflows)
        total_tasks = len(self._tasks)

        workflows_by_type: Dict[str, int] = {}
        workflows_by_status: Dict[str, int] = {}
        for w in self._workflows.values():
            wtype = w.workflow_type.value
            wstatus = w.status.value
            workflows_by_type[wtype] = workflows_by_type.get(wtype, 0) + 1
            workflows_by_status[wstatus] = workflows_by_status.get(wstatus, 0) + 1

        total_events = len(self._events)
        pending_events = sum(
            1 for e in self._events.values() if not e.handled
        )

        return {
            "total_projects": total_projects,
            "total_workflows": total_workflows,
            "total_tasks": total_tasks,
            "total_events": total_events,
            "pending_events": pending_events,
            "workflows_created": self._total_workflows_created,
            "workflows_completed": self._total_workflows_completed,
            "total_agent_calls": self._total_agent_calls,
            "total_engine_calls": self._total_engine_calls,
            "workflows_by_type": workflows_by_type,
            "workflows_by_status": workflows_by_status,
        }

    # ------------------------------------------------------------------
    # Convenience Pipeline Methods
    # ------------------------------------------------------------------

    def create_game_from_description(
        self,
        description: str,
        genre: str,
        platform: str,
    ) -> GameProject:
        """Create a full game project with a complete multi-stage pipeline.

        Generates a project with a GameFromScratch workflow containing
        realistic tasks across all pipeline stages: IDEATION, DESIGN,
        GENERATION, TESTING, and DEPLOYMENT.
        """
        name = description.split(",")[0].strip() if description else "New Game"

        project = self.create_project(
            name=name,
            description=description,
            genre=genre,
            platform=platform,
        )

        stages = [
            PipelineStage.IDEATION,
            PipelineStage.DESIGN,
            PipelineStage.GENERATION,
            PipelineStage.TESTING,
            PipelineStage.DEPLOYMENT,
        ]

        workflow = self.create_workflow(
            name=f"{name} - Full Creation Pipeline",
            workflow_type=WorkflowType.GAME_FROM_SCRATCH,
            mode=OrchestrationMode.SEQUENTIAL,
            stages=stages,
        )

        # Generate tasks for each stage from the template mapping
        task_id_map: Dict[str, str] = {}
        for stage in stages:
            entries = self._STAGE_AGENT_ENGINES.get(stage, [])
            for i, (agent_mod, engine_mod, task_name, task_desc) in enumerate(entries):
                # Resolve dependencies: tasks in the same stage have no cross-deps,
                # tasks in later stages depend on completion of previous stage
                deps: List[str] = []
                prev_stage_idx = stages.index(stage) - 1 if stages.index(stage) > 0 else -1
                if prev_stage_idx >= 0:
                    prev_stage = stages[prev_stage_idx]
                    prev_tasks = [t for t in workflow.tasks if t.stage == prev_stage]
                    if prev_tasks:
                        deps = [prev_tasks[-1].task_id]

                task = self.add_task_to_workflow(
                    workflow_id=workflow.workflow_id,
                    stage=stage,
                    name=task_name,
                    agent_module=agent_mod,
                    engine_module=engine_mod,
                    description=task_desc,
                    dependencies=deps,
                    priority=i,
                )
                task_id_map[task_name] = task.task_id

        project.workflows.append(workflow.workflow_id)
        project.current_stage = PipelineStage.IDEATION
        return project

    def add_feature_to_game(
        self,
        project_id: str,
        feature_description: str,
    ) -> PipelineWorkflow:
        """Create a feature addition workflow for an existing project."""
        project = self._projects.get(project_id)
        if project is None:
            raise ValueError(f"Project not found: {project_id}")

        workflow = self.create_workflow(
            name=f"Feature: {feature_description[:40]}",
            workflow_type=WorkflowType.FEATURE_ADDITION,
            mode=OrchestrationMode.SEQUENTIAL,
            stages=[PipelineStage.DESIGN, PipelineStage.GENERATION, PipelineStage.TESTING],
        )

        tasks_spec = [
            (PipelineStage.DESIGN, "Feature Design",
             "game_design_intelligence", "scene_manager",
             f"Design specifications for: {feature_description}"),
            (PipelineStage.GENERATION, "Feature Implementation",
             "game_code_generator", "entity_component_system",
             f"Implement: {feature_description}"),
            (PipelineStage.GENERATION, "Feature Integration",
             "scene_director", "scene_manager",
             f"Integrate: {feature_description} into existing project"),
            (PipelineStage.TESTING, "Feature Testing",
             "game_testing", "game_state_analyzer",
             f"Test and verify: {feature_description}"),
        ]

        prev_id: Optional[str] = None
        for stage, name, agent, engine, desc in tasks_spec:
            deps = [prev_id] if prev_id else []
            task = self.add_task_to_workflow(
                workflow_id=workflow.workflow_id,
                stage=stage,
                name=name,
                agent_module=agent,
                engine_module=engine,
                description=desc,
                dependencies=deps,
            )
            prev_id = task.task_id

        project.workflows.append(workflow.workflow_id)
        return workflow

    def tune_game_balance(
        self,
        project_id: str,
        aspect: str,
    ) -> PipelineWorkflow:
        """Create a balance tuning workflow for an existing project."""
        project = self._projects.get(project_id)
        if project is None:
            raise ValueError(f"Project not found: {project_id}")

        workflow = self.create_workflow(
            name=f"Balance Tuning: {aspect}",
            workflow_type=WorkflowType.BALANCE_TUNING,
            mode=OrchestrationMode.ADAPTIVE,
            stages=[PipelineStage.TESTING, PipelineStage.ITERATION],
        )

        tasks_spec = [
            (PipelineStage.TESTING, "Data Collection",
             "game_testing", "game_telemetry",
             f"Collect balance data for: {aspect}"),
            (PipelineStage.TESTING, "Balance Analysis",
             "balancing", "combat_system",
             f"Analyze balance metrics for: {aspect}"),
            (PipelineStage.ITERATION, "Parameter Adjustment",
             "balancing", "difficulty_system",
             f"Adjust parameters for: {aspect}"),
            (PipelineStage.ITERATION, "Verification Run",
             "game_testing", "game_state_analyzer",
             f"Verify balance changes for: {aspect}"),
        ]

        prev_id: Optional[str] = None
        for stage, name, agent, engine, desc in tasks_spec:
            deps = [prev_id] if prev_id else []
            task = self.add_task_to_workflow(
                workflow_id=workflow.workflow_id,
                stage=stage,
                name=name,
                agent_module=agent,
                engine_module=engine,
                description=desc,
                dependencies=deps,
            )
            prev_id = task.task_id

        project.workflows.append(workflow.workflow_id)
        return workflow

    def fix_game_bug(
        self,
        project_id: str,
        bug_description: str,
    ) -> PipelineWorkflow:
        """Create a bug fixing workflow for an existing project."""
        project = self._projects.get(project_id)
        if project is None:
            raise ValueError(f"Project not found: {project_id}")

        workflow = self.create_workflow(
            name=f"Bug Fix: {bug_description[:40]}",
            workflow_type=WorkflowType.BUG_FIXING,
            mode=OrchestrationMode.SEQUENTIAL,
            stages=[PipelineStage.TESTING, PipelineStage.GENERATION, PipelineStage.TESTING],
        )

        tasks_spec = [
            (PipelineStage.TESTING, "Bug Reproduction",
             "live_debugger", "profiler_system",
             f"Reproduce and diagnose: {bug_description}"),
            (PipelineStage.GENERATION, "Fix Implementation",
             "agentic_coding", "entity_component_system",
             f"Implement fix for: {bug_description}"),
            (PipelineStage.TESTING, "Regression Testing",
             "game_testing", "game_state_analyzer",
             f"Verify fix and check for regressions: {bug_description}"),
        ]

        prev_id: Optional[str] = None
        for stage, name, agent, engine, desc in tasks_spec:
            deps = [prev_id] if prev_id else []
            task = self.add_task_to_workflow(
                workflow_id=workflow.workflow_id,
                stage=stage,
                name=name,
                agent_module=agent,
                engine_module=engine,
                description=desc,
                dependencies=deps,
            )
            prev_id = task.task_id

        project.workflows.append(workflow.workflow_id)
        return workflow

    def expand_game_content(
        self,
        project_id: str,
        expansion_description: str,
    ) -> PipelineWorkflow:
        """Create a content expansion workflow for an existing project."""
        project = self._projects.get(project_id)
        if project is None:
            raise ValueError(f"Project not found: {project_id}")

        workflow = self.create_workflow(
            name=f"Content Expansion: {expansion_description[:40]}",
            workflow_type=WorkflowType.CONTENT_EXPANSION,
            mode=OrchestrationMode.SEQUENTIAL,
            stages=[
                PipelineStage.IDEATION,
                PipelineStage.DESIGN,
                PipelineStage.GENERATION,
                PipelineStage.TESTING,
            ],
        )

        tasks_spec = [
            (PipelineStage.IDEATION, "Expansion Concept",
             "creative_director", "game_design_intelligence",
             f"Conceptualize expansion: {expansion_description}"),
            (PipelineStage.DESIGN, "Content Design",
             "level_designer", "scene_manager",
             f"Design new content: {expansion_description}"),
            (PipelineStage.GENERATION, "Asset Generation",
             "asset_harmonizer", "asset_pipeline",
             f"Generate assets for: {expansion_description}"),
            (PipelineStage.GENERATION, "World Integration",
             "world_composer", "procedural_dungeon",
             f"Integrate content into world: {expansion_description}"),
            (PipelineStage.TESTING, "Content Validation",
             "game_testing", "game_state_analyzer",
             f"Validate new content: {expansion_description}"),
        ]

        prev_id: Optional[str] = None
        for stage, name, agent, engine, desc in tasks_spec:
            deps = [prev_id] if prev_id else []
            task = self.add_task_to_workflow(
                workflow_id=workflow.workflow_id,
                stage=stage,
                name=name,
                agent_module=agent,
                engine_module=engine,
                description=desc,
                dependencies=deps,
            )
            prev_id = task.task_id

        project.workflows.append(workflow.workflow_id)
        return workflow

    # ------------------------------------------------------------------
    # Workflow Finalization
    # ------------------------------------------------------------------

    def deliver_workflow(self, workflow_id: str) -> PipelineWorkflow:
        """Mark a workflow as completed and generate a delivery summary."""
        workflow = self._workflows.get(workflow_id)
        if workflow is None:
            raise ValueError(f"Workflow not found: {workflow_id}")

        workflow.status = PipelineStatus.COMPLETED
        workflow.updated_at = _time_module.time()
        self._total_workflows_completed += 1

        return workflow

    def generate_summary(self, workflow_id: str) -> str:
        """Generate a natural language summary of what the workflow accomplished."""
        workflow = self._workflows.get(workflow_id)
        if workflow is None:
            return f"No workflow found with ID: {workflow_id}"

        metrics = self.get_pipeline_metrics(workflow_id)
        completed = metrics.completed_tasks
        total = metrics.total_tasks
        failed = metrics.failed_tasks

        stage_summary: Dict[str, List[str]] = {}
        for stage in PipelineStage:
            stage_tasks = [
                t.name for t in workflow.tasks
                if t.stage == stage and t.status == PipelineStatus.COMPLETED
            ]
            if stage_tasks:
                stage_summary[stage.value] = stage_tasks

        lines: List[str] = []
        lines.append(f"Workflow: {workflow.name}")
        lines.append(f"Type: {workflow.workflow_type.value}")
        lines.append(f"Status: {workflow.status.value}")
        lines.append(f"Mode: {workflow.mode.value}")
        lines.append("")

        for stage_value, task_names in stage_summary.items():
            lines.append(f"[{stage_value.upper()}]")
            for tname in task_names:
                lines.append(f"  - {tname}")
            lines.append("")

        lines.append(f"Completed: {completed}/{total} tasks")
        if failed > 0:
            lines.append(f"Failed: {failed} task(s)")
            for err in metrics.errors:
                lines.append(f"  - {err}")

        lines.append(f"Total duration: {metrics.total_duration_ms:.0f}ms")
        lines.append(f"Avg task duration: {metrics.avg_task_duration_ms:.0f}ms")
        lines.append(f"Agent calls: {metrics.agent_calls}")
        lines.append(f"Engine calls: {metrics.engine_calls}")

        return "\n".join(lines)

    def delete_workflow(self, workflow_id: str) -> bool:
        """Delete a workflow and its associated tasks."""
        workflow = self._workflows.pop(workflow_id, None)
        if workflow is None:
            return False
        for task in workflow.tasks:
            self._tasks.pop(task.task_id, None)
        for project in self._projects.values():
            if workflow_id in project.workflows:
                project.workflows.remove(workflow_id)
        return True

    def delete_project(self, project_id: str) -> bool:
        """Delete a project and all its associated workflows."""
        project = self._projects.pop(project_id, None)
        if project is None:
            return False
        for wf_id in list(project.workflows):
            self.delete_workflow(wf_id)
        return True


# ---------------------------------------------------------------------------
# Module-level accessor
# ---------------------------------------------------------------------------

def get_agent_engine_orchestrator() -> AgentEngineOrchestrator:
    """Return the singleton AgentEngineOrchestrator instance."""
    return AgentEngineOrchestrator.get_instance()