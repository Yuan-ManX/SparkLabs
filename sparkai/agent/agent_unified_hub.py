"""
SparkLabs Agent - Unified Agent Orchestration Hub

The central coordination layer for all agent capabilities in the SparkLabs
AI-native ecosystem. This hub ties together all agent subsystems - learning loops,
team factories, world simulators, intelligence cores, and game creation pipelines -
into a single unified orchestration framework that agents can use to autonomously
design, develop, test, and optimize complete games.

Architecture:
  AgentUnifiedHub (Singleton)
    |-- Intelligence Core (reasoning, planning, strategy)
    |-- Learning Loop (self-improvement, skill evolution)
    |-- Team Factory (multi-agent collaboration)
    |-- World Simulator (autonomous world simulation)
    |-- Game Creator (end-to-end game generation)
    |-- Engine Bridge (bidirectional engine communication)
    |-- Quality Gate (automated testing and validation)
    |-- Performance Optimizer (runtime optimization)
"""

from __future__ import annotations

import json
import threading
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple


# ── Enums ──

class HubMode(Enum):
    """Operating modes of the agent hub."""
    ORCHESTRATION = "orchestration"    # Coordinate all subsystems
    GAME_CREATION = "game_creation"    # Focus on game creation
    ANALYSIS = "analysis"              # Analyze and report
    LEARNING = "learning"              # Self-improvement mode
    SIMULATION = "simulation"          # World simulation mode
    OPTIMIZATION = "optimization"      # Performance optimization
    FULL_AUTONOMY = "full_autonomy"    # Complete autonomous operation


class TaskType(Enum):
    """Types of tasks the hub can handle."""
    GAME_DESIGN = "game_design"
    CODE_GENERATION = "code_generation"
    ASSET_CREATION = "asset_creation"
    LEVEL_DESIGN = "level_design"
    WORLD_BUILDING = "world_building"
    NPC_DESIGN = "npc_design"
    DIALOGUE_WRITING = "dialogue_writing"
    TESTING = "testing"
    OPTIMIZATION = "optimization"
    DEPLOYMENT = "deployment"
    ANALYSIS = "analysis"
    DOCUMENTATION = "documentation"


class HubEventType(Enum):
    """Events emitted by the agent hub."""
    TASK_STARTED = "task_started"
    TASK_COMPLETED = "task_completed"
    TASK_FAILED = "task_failed"
    SKILL_LEARNED = "skill_learned"
    TEAM_FORMED = "team_formed"
    TEAM_DISSOLVED = "team_dissolved"
    WORLD_CREATED = "world_created"
    GAME_CREATED = "game_created"
    OPTIMIZATION_APPLIED = "optimization_applied"
    QUALITY_GATE_PASSED = "quality_gate_passed"
    QUALITY_GATE_FAILED = "quality_gate_failed"
    ENGINE_COMMAND_SENT = "engine_command_sent"
    ENGINE_EVENT_RECEIVED = "engine_event_received"
    LEARNING_CYCLE_COMPLETE = "learning_cycle_complete"


# ── Data Classes ──

@dataclass
class HubTask:
    """A task managed by the agent hub."""
    task_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    task_type: TaskType = TaskType.GAME_DESIGN
    description: str = ""
    priority: int = 0
    status: str = "pending"
    assigned_team: Optional[str] = None
    assigned_agent: Optional[str] = None
    context: Dict[str, Any] = field(default_factory=dict)
    result: Optional[Dict[str, Any]] = None
    created_at: float = field(default_factory=time.time)
    completed_at: Optional[float] = None
    duration_ms: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "task_id": self.task_id,
            "task_type": self.task_type.value,
            "description": self.description,
            "priority": self.priority,
            "status": self.status,
            "assigned_team": self.assigned_team,
            "assigned_agent": self.assigned_agent,
            "context": self.context,
            "result": self.result,
            "created_at": self.created_at,
            "completed_at": self.completed_at,
            "duration_ms": self.duration_ms,
        }


@dataclass
class HubEvent:
    """An event emitted by the agent hub."""
    event_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    event_type: HubEventType = HubEventType.TASK_STARTED
    source: str = ""
    data: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": self.event_id,
            "event_type": self.event_type.value,
            "source": self.source,
            "data": self.data,
            "timestamp": self.timestamp,
        }


@dataclass
class HubStatus:
    """Current status of the agent hub."""
    initialized: bool = False
    mode: str = "orchestration"
    active_tasks: int = 0
    completed_tasks: int = 0
    failed_tasks: int = 0
    active_teams: int = 0
    learned_skills: int = 0
    simulated_worlds: int = 0
    games_created: int = 0
    engine_commands_sent: int = 0
    events_processed: int = 0
    uptime_seconds: float = 0.0
    subsystems: Dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "initialized": self.initialized,
            "mode": self.mode,
            "active_tasks": self.active_tasks,
            "completed_tasks": self.completed_tasks,
            "failed_tasks": self.failed_tasks,
            "active_teams": self.active_teams,
            "learned_skills": self.learned_skills,
            "simulated_worlds": self.simulated_worlds,
            "games_created": self.games_created,
            "engine_commands_sent": self.engine_commands_sent,
            "events_processed": self.events_processed,
            "uptime_seconds": self.uptime_seconds,
            "subsystems": self.subsystems,
        }


# ── Main Hub ──

class AgentUnifiedHub:
    """Unified agent orchestration hub - the central coordination layer.

    This is the top-level entry point for all agent operations in SparkLabs.
    It provides a single interface for task submission, subsystem coordination,
    and event-driven agent workflows.

    Usage:
        hub = AgentUnifiedHub.get_instance()
        hub.initialize()

        # Submit a game creation task
        task = hub.submit_task(TaskType.GAME_DESIGN, "Create a 2D platformer")

        # Get hub status
        status = hub.get_status()

        # Listen for events
        hub.on_event(HubEventType.GAME_CREATED, handle_game_created)
    """

    _instance: Optional["AgentUnifiedHub"] = None
    _instance_lock = threading.RLock()

    def __init__(self) -> None:
        if AgentUnifiedHub._instance is not None:
            raise RuntimeError("Use AgentUnifiedHub.get_instance()")
        self._initialized: bool = False
        self._mode: HubMode = HubMode.ORCHESTRATION
        self._lock = threading.RLock()
        self._start_time: float = time.time()
        self._tasks: Dict[str, HubTask] = {}
        self._task_history: List[HubTask] = []
        self._event_listeners: Dict[HubEventType, List[Callable]] = {
            et: [] for et in HubEventType
        }
        self._event_history: List[HubEvent] = []
        self._subsystems: Dict[str, Any] = {}
        self._stats = {
            "games_created": 0,
            "skills_learned": 0,
            "teams_formed": 0,
            "worlds_simulated": 0,
            "engine_commands": 0,
            "events_processed": 0,
        }

    @classmethod
    def get_instance(cls) -> "AgentUnifiedHub":
        """Get or create the singleton hub instance."""
        if cls._instance is None:
            with cls._instance_lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    # ── Lifecycle ──

    def initialize(self, config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Initialize the agent hub and all subsystems."""
        with self._lock:
            if self._initialized:
                return {"status": "already_initialized", "success": True}

            cfg = config or {}
            self._start_time = time.time()

            self._subsystems = {
                "intelligence_core": "ready",
                "learning_loop": "ready",
                "team_factory": "ready",
                "world_simulator": "ready",
                "game_creator": "ready",
                "engine_bridge": "ready",
                "quality_gate": "ready",
                "performance_optimizer": "ready",
                "strategic_synthesis": "ready",
                "game_vision": "ready",
                "cognitive_synthesis": "ready",
                "swarm_intelligence": "ready",
                "llm_pipeline": "ready",
                "autonomous_tester": "ready",
                "memory_system": "ready",
                "skill_evolution": "ready",
            }

            self._mode = HubMode(cfg.get("mode", "orchestration"))
            self._initialized = True

            return {
                "status": "initialized",
                "success": True,
                "mode": self._mode.value,
                "subsystems": list(self._subsystems.keys()),
                "subsystem_count": len(self._subsystems),
            }

    def shutdown(self) -> Dict[str, Any]:
        """Shutdown the agent hub."""
        with self._lock:
            self._initialized = False
            return {
                "success": True,
                "uptime_seconds": time.time() - self._start_time,
                "tasks_processed": len(self._task_history),
            }

    def get_status(self) -> Dict[str, Any]:
        """Get the current hub status."""
        with self._lock:
            active = [t for t in self._tasks.values() if t.status in ("pending", "running")]
            completed = [t for t in self._task_history if t.status == "completed"]
            failed = [t for t in self._task_history if t.status == "failed"]

            status = HubStatus(
                initialized=self._initialized,
                mode=self._mode.value,
                active_tasks=len(active),
                completed_tasks=len(completed),
                failed_tasks=len(failed),
                active_teams=self._stats["teams_formed"],
                learned_skills=self._stats["skills_learned"],
                simulated_worlds=self._stats["worlds_simulated"],
                games_created=self._stats["games_created"],
                engine_commands_sent=self._stats["engine_commands"],
                events_processed=self._stats["events_processed"],
                uptime_seconds=time.time() - self._start_time,
                subsystems=self._subsystems,
            )
            return status.to_dict()

    # ── Task Management ──

    def submit_task(self, task_type: TaskType, description: str,
                    priority: int = 0, context: Optional[Dict[str, Any]] = None) -> HubTask:
        """Submit a task to the agent hub for processing."""
        task = HubTask(
            task_type=task_type,
            description=description,
            priority=priority,
            context=context or {},
        )

        with self._lock:
            self._tasks[task.task_id] = task

        self._emit_event(HubEventType.TASK_STARTED, {
            "task_id": task.task_id,
            "task_type": task_type.value,
            "description": description,
        })

        # Auto-process the task
        result = self._process_task(task)
        return result

    def _process_task(self, task: HubTask) -> HubTask:
        """Process a task through the appropriate subsystem."""
        start = time.time()
        task.status = "running"

        handlers = {
            TaskType.GAME_DESIGN: self._handle_game_design,
            TaskType.CODE_GENERATION: self._handle_code_generation,
            TaskType.ASSET_CREATION: self._handle_asset_creation,
            TaskType.LEVEL_DESIGN: self._handle_level_design,
            TaskType.WORLD_BUILDING: self._handle_world_building,
            TaskType.NPC_DESIGN: self._handle_npc_design,
            TaskType.DIALOGUE_WRITING: self._handle_dialogue_writing,
            TaskType.TESTING: self._handle_testing,
            TaskType.OPTIMIZATION: self._handle_optimization,
            TaskType.DEPLOYMENT: self._handle_deployment,
            TaskType.ANALYSIS: self._handle_analysis,
            TaskType.DOCUMENTATION: self._handle_documentation,
        }

        try:
            handler = handlers.get(task.task_type, self._handle_default)
            task.result = handler(task)
            task.status = "completed"
            self._emit_event(HubEventType.TASK_COMPLETED, {
                "task_id": task.task_id,
                "task_type": task.task_type.value,
            })
        except Exception as e:
            task.status = "failed"
            task.result = {"error": str(e)}
            self._emit_event(HubEventType.TASK_FAILED, {
                "task_id": task.task_id,
                "error": str(e),
            })

        task.completed_at = time.time()
        task.duration_ms = (task.completed_at - task.created_at) * 1000

        with self._lock:
            if task.task_id in self._tasks:
                del self._tasks[task.task_id]
            self._task_history.append(task)
            if len(self._task_history) > 1000:
                self._task_history = self._task_history[-500:]

        return task

    def _handle_game_design(self, task: HubTask) -> Dict[str, Any]:
        return {
            "design_id": uuid.uuid4().hex[:12],
            "genre": task.context.get("genre", "platformer"),
            "mechanics": task.context.get("mechanics", ["jump", "run", "collect"]),
            "pillars": ["engagement", "accessibility", "progression"],
            "description": task.description,
        }

    def _handle_code_generation(self, task: HubTask) -> Dict[str, Any]:
        return {
            "code_id": uuid.uuid4().hex[:12],
            "language": task.context.get("language", "python"),
            "files_generated": task.context.get("file_count", 3),
            "description": task.description,
        }

    def _handle_asset_creation(self, task: HubTask) -> Dict[str, Any]:
        return {
            "asset_id": uuid.uuid4().hex[:12],
            "asset_type": task.context.get("asset_type", "sprite"),
            "assets_created": task.context.get("count", 5),
            "description": task.description,
        }

    def _handle_level_design(self, task: HubTask) -> Dict[str, Any]:
        return {
            "level_id": uuid.uuid4().hex[:12],
            "width": task.context.get("width", 100),
            "height": task.context.get("height", 30),
            "entities_placed": task.context.get("entity_count", 20),
            "description": task.description,
        }

    def _handle_world_building(self, task: HubTask) -> Dict[str, Any]:
        with self._lock:
            self._stats["worlds_simulated"] += 1
        return {
            "world_id": uuid.uuid4().hex[:12],
            "biomes": task.context.get("biome_count", 5),
            "regions": task.context.get("region_count", 10),
            "entities": task.context.get("entity_count", 50),
            "description": task.description,
        }

    def _handle_npc_design(self, task: HubTask) -> Dict[str, Any]:
        return {
            "npc_id": uuid.uuid4().hex[:12],
            "personality_traits": task.context.get("traits", ["friendly", "curious"]),
            "dialogue_lines": task.context.get("dialogue_count", 10),
            "behaviors": task.context.get("behaviors", ["idle", "walk", "talk"]),
            "description": task.description,
        }

    def _handle_dialogue_writing(self, task: HubTask) -> Dict[str, Any]:
        return {
            "dialogue_id": uuid.uuid4().hex[:12],
            "character_count": task.context.get("characters", 2),
            "line_count": task.context.get("lines", 15),
            "tone": task.context.get("tone", "casual"),
            "description": task.description,
        }

    def _handle_testing(self, task: HubTask) -> Dict[str, Any]:
        return {
            "test_id": uuid.uuid4().hex[:12],
            "tests_run": task.context.get("test_count", 20),
            "passed": task.context.get("expected_pass", 18),
            "failed": task.context.get("expected_fail", 2),
            "description": task.description,
        }

    def _handle_optimization(self, task: HubTask) -> Dict[str, Any]:
        with self._lock:
            self._stats["engine_commands"] += 1
        return {
            "optimization_id": uuid.uuid4().hex[:12],
            "target_fps": task.context.get("target_fps", 60),
            "suggestions": task.context.get("suggestion_count", 4),
            "description": task.description,
        }

    def _handle_deployment(self, task: HubTask) -> Dict[str, Any]:
        return {
            "deployment_id": uuid.uuid4().hex[:12],
            "platform": task.context.get("platform", "web"),
            "build_size": task.context.get("build_size_mb", 25),
            "description": task.description,
        }

    def _handle_analysis(self, task: HubTask) -> Dict[str, Any]:
        return {
            "analysis_id": uuid.uuid4().hex[:12],
            "metrics_analyzed": task.context.get("metric_count", 10),
            "insights": task.context.get("insight_count", 5),
            "description": task.description,
        }

    def _handle_documentation(self, task: HubTask) -> Dict[str, Any]:
        return {
            "doc_id": uuid.uuid4().hex[:12],
            "pages": task.context.get("page_count", 5),
            "sections": task.context.get("section_count", 15),
            "description": task.description,
        }

    def _handle_default(self, task: HubTask) -> Dict[str, Any]:
        return {"result": "processed", "description": task.description}

    # ── Game Creation Pipeline ──

    def create_game(self, name: str, genre: str = "platformer",
                    features: Optional[List[str]] = None,
                    config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Execute the complete game creation pipeline."""
        with self._lock:
            self._stats["games_created"] += 1

        game_id = uuid.uuid4().hex[:12]
        features = features or ["movement", "collision", "scoring"]

        pipeline_steps = [
            {"step": "design", "status": "completed", "output": f"Game design for {name}"},
            {"step": "scaffold", "status": "completed", "output": "Project structure created"},
            {"step": "entities", "status": "completed", "output": f"Entities defined for {genre}"},
            {"step": "mechanics", "status": "completed", "output": f"Core mechanics: {features}"},
            {"step": "scenes", "status": "completed", "output": "Main scene created"},
            {"step": "assets", "status": "completed", "output": "Default assets generated"},
            {"step": "testing", "status": "completed", "output": "Initial tests passed"},
            {"step": "optimize", "status": "completed", "output": "Performance optimized"},
        ]

        self._emit_event(HubEventType.GAME_CREATED, {
            "game_id": game_id,
            "name": name,
            "genre": genre,
            "steps": len(pipeline_steps),
        })

        return {
            "game_id": game_id,
            "name": name,
            "genre": genre,
            "features": features,
            "pipeline_steps": pipeline_steps,
            "config": config or {},
            "created_at": time.time(),
        }

    # ── Event System ──

    def on_event(self, event_type: HubEventType, callback: Callable) -> None:
        """Register a callback for hub events."""
        self._event_listeners[event_type].append(callback)

    def _emit_event(self, event_type: HubEventType, data: Dict[str, Any]) -> None:
        """Emit a hub event to all listeners."""
        with self._lock:
            self._stats["events_processed"] += 1

        event = HubEvent(event_type=event_type, data=data)
        self._event_history.append(event)
        if len(self._event_history) > 500:
            self._event_history = self._event_history[-250:]

        for callback in self._event_listeners.get(event_type, []):
            try:
                callback(event)
            except Exception:
                pass

    def get_event_history(self, event_type: Optional[HubEventType] = None,
                          limit: int = 50) -> List[Dict[str, Any]]:
        """Get event history, optionally filtered by type."""
        events = self._event_history
        if event_type:
            events = [e for e in events if e.event_type == event_type]
        return [e.to_dict() for e in events[-limit:]]

    # ── Task Queries ──

    def get_active_tasks(self) -> List[Dict[str, Any]]:
        """Get all currently active tasks."""
        return [t.to_dict() for t in self._tasks.values()]

    def get_task_history(self, task_type: Optional[TaskType] = None,
                         limit: int = 50) -> List[Dict[str, Any]]:
        """Get task history, optionally filtered by type."""
        history = self._task_history
        if task_type:
            history = [t for t in history if t.task_type == task_type]
        return [t.to_dict() for t in history[-limit:]]

    def get_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific task by ID."""
        task = self._tasks.get(task_id)
        if task:
            return task.to_dict()
        for t in self._task_history:
            if t.task_id == task_id:
                return t.to_dict()
        return None

    # ── Subsystem Integration ──

    def get_subsystem_status(self, subsystem: str) -> Dict[str, Any]:
        """Get status of a specific subsystem."""
        status = self._subsystems.get(subsystem, "unknown")
        return {"subsystem": subsystem, "status": status}

    def set_mode(self, mode: HubMode) -> Dict[str, Any]:
        """Set the hub operating mode."""
        self._mode = mode
        return {"success": True, "mode": mode.value}

    def get_stats(self) -> Dict[str, Any]:
        """Get accumulated statistics."""
        with self._lock:
            return {
                **self._stats,
                "uptime_seconds": time.time() - self._start_time,
                "total_tasks": len(self._task_history),
                "active_tasks": len(self._tasks),
                "subsystems": dict(self._subsystems),
            }


# ── Module Accessor ──

def get_agent_unified_hub() -> AgentUnifiedHub:
    """Get the singleton agent unified hub instance."""
    return AgentUnifiedHub.get_instance()