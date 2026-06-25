"""
SparkLabs Agent - Unified Orchestration Core

A central coordination engine that integrates all agent subsystems into a
single, coherent orchestration framework. The Unified Orchestration Core
manages multi-agent collaboration, task dispatching, context sharing, and
cross-subsystem coordination for the AI-native game development pipeline.

Architecture:
  UnifiedOrchestrationCore (Singleton)
    |-- TaskDispatcher (intelligent task routing based on agent capabilities)
    |-- ContextAggregator (cross-subsystem context collection and sharing)
    |-- CollaborationManager (multi-agent collaboration protocol management)
    |-- PipelineCoordinator (end-to-end pipeline workflow orchestration)
    |-- ResourceAllocator (dynamic resource allocation across subsystems)
    |-- HealthMonitor (real-time subsystem health tracking and recovery)
"""

from __future__ import annotations

import json
import math
import random
import threading
import time
import uuid
from collections import defaultdict, deque
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

# ------------------------------------------------------------------ Enums ------------------------------------------------------------------

class OrchestrationMode(Enum):
    SEQUENTIAL = "sequential"
    PARALLEL = "parallel"
    ADAPTIVE = "adaptive"
    PRIORITY_DRIVEN = "priority_driven"
    EVENT_DRIVEN = "event_driven"


class TaskRoutingStrategy(Enum):
    CAPABILITY_MATCH = "capability_match"
    LOAD_BALANCED = "load_balanced"
    AFFINITY_BASED = "affinity_based"
    ROUND_ROBIN = "round_robin"
    INTELLIGENT = "intelligent"


class SubsystemType(Enum):
    COGNITIVE_SYNTHESIS = "cognitive_synthesis"
    GAME_INTELLIGENCE = "game_intelligence"
    AUTONOMOUS_CREATOR = "autonomous_creator"
    INTERACTION_LOOP = "interaction_loop"
    SWARM_INTELLIGENCE = "swarm_intelligence"
    LLM_PIPELINE = "llm_pipeline"
    GAME_CREATOR = "game_creator"
    BEHAVIOR_DESIGNER = "behavior_designer"
    DIALOGUE_ENGINE = "dialogue_engine"
    QUEST_GENERATOR = "quest_generator"
    WORLD_SIMULATOR = "world_simulator"
    STORY_ENGINE = "story_engine"
    GAME_DESIGNER = "game_designer"
    PLAYER_MODELER = "player_modeler"
    BALANCE_OPTIMIZER = "balance_optimizer"
    PERFORMANCE_OPTIMIZER = "performance_optimizer"
    EMOTION_ENGINE = "emotion_engine"
    SOCIAL_COGNITION = "social_cognition"
    PERCEPTION_FUSION = "perception_fusion"
    LEARNING_LOOP = "learning_loop"


class TaskPriority(Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    BACKGROUND = "background"


class TaskStatus(Enum):
    PENDING = "pending"
    DISPATCHED = "dispatched"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    RETRYING = "retrying"


class CollaborationPhase(Enum):
    DISCOVERY = "discovery"
    NEGOTIATION = "negotiation"
    EXECUTION = "execution"
    SYNCHRONIZATION = "synchronization"
    RESOLUTION = "resolution"


# ---------------------------------------------------------------- Dataclasses ----------------------------------------------------------------

@dataclass
class OrchestratedTask:
    task_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    name: str = ""
    description: str = ""
    target_subsystem: SubsystemType = SubsystemType.COGNITIVE_SYNTHESIS
    priority: TaskPriority = TaskPriority.MEDIUM
    status: TaskStatus = TaskStatus.PENDING
    payload: Dict[str, Any] = field(default_factory=dict)
    dependencies: List[str] = field(default_factory=list)
    result: Optional[Dict[str, Any]] = None
    created_at: float = field(default_factory=time.time)
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    retry_count: int = 0
    max_retries: int = 3

    def to_dict(self) -> Dict[str, Any]:
        return {
            "task_id": self.task_id, "name": self.name, "description": self.description,
            "target_subsystem": self.target_subsystem.value, "priority": self.priority.value,
            "status": self.status.value, "payload": dict(self.payload),
            "dependencies": list(self.dependencies),
            "result": dict(self.result) if self.result else None,
            "created_at": self.created_at, "started_at": self.started_at,
            "completed_at": self.completed_at, "retry_count": self.retry_count,
        }


@dataclass
class SubsystemProfile:
    subsystem_type: SubsystemType
    capabilities: List[str] = field(default_factory=list)
    current_load: float = 0.0
    max_capacity: int = 10
    health_status: str = "healthy"
    last_heartbeat: float = field(default_factory=time.time)
    active_tasks: int = 0
    completed_tasks: int = 0
    failed_tasks: int = 0
    avg_response_time: float = 0.0
    success_rate: float = 1.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "subsystem_type": self.subsystem_type.value,
            "capabilities": list(self.capabilities),
            "current_load": round(self.current_load, 2),
            "max_capacity": self.max_capacity,
            "health_status": self.health_status,
            "last_heartbeat": self.last_heartbeat,
            "active_tasks": self.active_tasks,
            "completed_tasks": self.completed_tasks,
            "failed_tasks": self.failed_tasks,
            "avg_response_time": round(self.avg_response_time, 4),
            "success_rate": round(self.success_rate, 4),
        }


@dataclass
class CollaborationSession:
    session_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    participants: List[SubsystemType] = field(default_factory=list)
    phase: CollaborationPhase = CollaborationPhase.DISCOVERY
    shared_context: Dict[str, Any] = field(default_factory=dict)
    consensus_reached: bool = False
    decisions: List[Dict[str, Any]] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    resolved_at: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "session_id": self.session_id,
            "participants": [p.value for p in self.participants],
            "phase": self.phase.value,
            "shared_context": dict(self.shared_context),
            "consensus_reached": self.consensus_reached,
            "decisions": [dict(d) for d in self.decisions],
            "created_at": self.created_at,
            "resolved_at": self.resolved_at,
        }


@dataclass
class PipelineWorkflow:
    workflow_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    name: str = ""
    stages: List[PipelineStage] = field(default_factory=list)
    current_stage: int = 0
    status: str = "pending"
    total_stages: int = 0
    created_at: float = field(default_factory=time.time)
    completed_at: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "workflow_id": self.workflow_id, "name": self.name,
            "stages": [s.to_dict() for s in self.stages],
            "current_stage": self.current_stage, "status": self.status,
            "total_stages": self.total_stages, "created_at": self.created_at,
            "completed_at": self.completed_at,
        }


@dataclass
class PipelineStage:
    stage_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    name: str = ""
    subsystem: SubsystemType = SubsystemType.COGNITIVE_SYNTHESIS
    tasks: List[str] = field(default_factory=list)
    status: str = "pending"
    order: int = 0
    depends_on: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "stage_id": self.stage_id, "name": self.name,
            "subsystem": self.subsystem.value, "tasks": list(self.tasks),
            "status": self.status, "order": self.order,
            "depends_on": list(self.depends_on),
        }


@dataclass
class OrchestrationReport:
    report_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    total_tasks: int = 0
    completed_tasks: int = 0
    failed_tasks: int = 0
    active_workflows: int = 0
    subsystem_health: Dict[str, str] = field(default_factory=dict)
    performance_metrics: Dict[str, float] = field(default_factory=dict)
    generated_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "report_id": self.report_id, "total_tasks": self.total_tasks,
            "completed_tasks": self.completed_tasks, "failed_tasks": self.failed_tasks,
            "active_workflows": self.active_workflows,
            "subsystem_health": dict(self.subsystem_health),
            "performance_metrics": {k: round(v, 4) for k, v in self.performance_metrics.items()},
            "generated_at": self.generated_at,
        }


# --------------------------------------------------------------- TaskDispatcher ---------------------------------------------------------------

class TaskDispatcher:
    """Intelligent task routing based on agent capabilities and load balancing."""

    _CAPABILITY_MAP: Dict[SubsystemType, List[str]] = {
        SubsystemType.COGNITIVE_SYNTHESIS: ["reasoning", "synthesis", "analysis", "planning"],
        SubsystemType.GAME_INTELLIGENCE: ["game_analysis", "design_evaluation", "pattern_detection", "quality_assessment"],
        SubsystemType.AUTONOMOUS_CREATOR: ["content_generation", "level_design", "quest_creation", "npc_design"],
        SubsystemType.INTERACTION_LOOP: ["perception", "action_selection", "execution", "feedback"],
        SubsystemType.SWARM_INTELLIGENCE: ["consensus", "collective_decision", "task_decomposition", "parallel_execution"],
        SubsystemType.LLM_PIPELINE: ["text_generation", "prompt_engineering", "chain_of_thought", "context_assembly"],
        SubsystemType.GAME_CREATOR: ["game_spec", "game_assembly", "creation_pipeline", "blueprint_generation"],
        SubsystemType.BEHAVIOR_DESIGNER: ["behavior_tree", "state_machine", "action_pattern", "npc_behavior"],
        SubsystemType.DIALOGUE_ENGINE: ["dialogue_generation", "conversation_flow", "character_voice", "narrative_dialogue"],
        SubsystemType.QUEST_GENERATOR: ["quest_design", "objective_creation", "reward_balancing", "quest_chain"],
        SubsystemType.WORLD_SIMULATOR: ["world_simulation", "entity_management", "ecosystem", "environment_dynamics"],
        SubsystemType.STORY_ENGINE: ["narrative_generation", "plot_development", "character_arc", "world_lore"],
        SubsystemType.GAME_DESIGNER: ["mechanic_design", "balance_tuning", "game_loop", "difficulty_curve"],
        SubsystemType.PLAYER_MODELER: ["player_profiling", "engagement_prediction", "difficulty_adaptation", "playstyle_analysis"],
        SubsystemType.BALANCE_OPTIMIZER: ["economy_balance", "combat_balance", "progression_balance", "resource_balance"],
        SubsystemType.PERFORMANCE_OPTIMIZER: ["bottleneck_detection", "optimization_suggestion", "resource_profiling", "frame_analysis"],
        SubsystemType.EMOTION_ENGINE: ["emotion_modeling", "affect_simulation", "mood_tracking", "personality_synthesis"],
        SubsystemType.SOCIAL_COGNITION: ["relationship_modeling", "social_dynamics", "reputation_system", "alliance_formation"],
        SubsystemType.PERCEPTION_FUSION: ["sensor_fusion", "attention_management", "saliency_detection", "percept_integration"],
        SubsystemType.LEARNING_LOOP: ["experience_learning", "pattern_extraction", "skill_acquisition", "adaptive_improvement"],
    }

    def __init__(self) -> None:
        self._subsystem_profiles: Dict[SubsystemType, SubsystemProfile] = {}
        self._task_queue: Dict[TaskPriority, deque] = {
            p: deque() for p in TaskPriority
        }
        self._routing_history: deque = deque(maxlen=500)
        self._strategy: TaskRoutingStrategy = TaskRoutingStrategy.INTELLIGENT
        self._lock = threading.RLock()

    def register_subsystem(self, subsystem: SubsystemType, capabilities: Optional[List[str]] = None) -> SubsystemProfile:
        with self._lock:
            caps = capabilities or self._CAPABILITY_MAP.get(subsystem, [])
            profile = SubsystemProfile(
                subsystem_type=subsystem,
                capabilities=caps,
            )
            self._subsystem_profiles[subsystem] = profile
            return profile

    def dispatch(self, task: OrchestratedTask) -> SubsystemType:
        with self._lock:
            if self._strategy == TaskRoutingStrategy.CAPABILITY_MATCH:
                target = self._route_by_capability(task)
            elif self._strategy == TaskRoutingStrategy.LOAD_BALANCED:
                target = self._route_by_load(task)
            elif self._strategy == TaskRoutingStrategy.INTELLIGENT:
                target = self._route_intelligently(task)
            else:
                target = task.target_subsystem

            task.target_subsystem = target
            task.status = TaskStatus.DISPATCHED
            task.started_at = time.time()

            if target in self._subsystem_profiles:
                self._subsystem_profiles[target].active_tasks += 1
                self._subsystem_profiles[target].current_load += 1.0 / self._subsystem_profiles[target].max_capacity

            self._routing_history.append({
                "task_id": task.task_id,
                "target": target.value,
                "strategy": self._strategy.value,
                "timestamp": time.time(),
            })
            return target

    def complete_task(self, task_id: str, success: bool, result: Optional[Dict[str, Any]] = None) -> None:
        with self._lock:
            for entry in self._routing_history:
                if entry["task_id"] == task_id:
                    subsystem = SubsystemType(entry["target"])
                    if subsystem in self._subsystem_profiles:
                        profile = self._subsystem_profiles[subsystem]
                        profile.active_tasks = max(0, profile.active_tasks - 1)
                        profile.current_load = max(0.0, profile.current_load - 1.0 / profile.max_capacity)
                        if success:
                            profile.completed_tasks += 1
                        else:
                            profile.failed_tasks += 1
                        total = profile.completed_tasks + profile.failed_tasks
                        profile.success_rate = profile.completed_tasks / max(total, 1)
                    break

    def _route_by_capability(self, task: OrchestratedTask) -> SubsystemType:
        required_caps = task.payload.get("required_capabilities", [])
        best_match = task.target_subsystem
        best_score = 0
        for stype, profile in self._subsystem_profiles.items():
            matching = len(set(required_caps) & set(profile.capabilities))
            score = matching / max(len(required_caps), 1)
            if score > best_score:
                best_score = score
                best_match = stype
        return best_match

    def _route_by_load(self, task: OrchestratedTask) -> SubsystemType:
        candidates = [
            stype for stype in self._subsystem_profiles
            if any(c in self._subsystem_profiles[stype].capabilities
                  for c in task.payload.get("required_capabilities", [task.name]))
        ]
        if not candidates:
            candidates = list(self._subsystem_profiles.keys())
        return min(candidates, key=lambda s: self._subsystem_profiles[s].current_load, default=task.target_subsystem)

    def _route_intelligently(self, task: OrchestratedTask) -> SubsystemType:
        capability_score = {}
        load_score = {}
        required_caps = task.payload.get("required_capabilities", [task.name])
        for stype, profile in self._subsystem_profiles.items():
            matching = len(set(required_caps) & set(profile.capabilities))
            capability_score[stype] = matching / max(len(required_caps), 1)
            load_score[stype] = 1.0 - profile.current_load
        composite = {
            s: capability_score.get(s, 0) * 0.6 + load_score.get(s, 0) * 0.4
            for s in self._subsystem_profiles
        }
        return max(composite, key=composite.get, default=task.target_subsystem)

    def get_profiles(self) -> Dict[SubsystemType, SubsystemProfile]:
        with self._lock:
            return dict(self._subsystem_profiles)


# ------------------------------------------------------------ ContextAggregator -------------------------------------------------------------

class ContextAggregator:
    """Cross-subsystem context collection and sharing for unified awareness."""

    def __init__(self) -> None:
        self._global_context: Dict[str, Any] = {}
        self._subsystem_contexts: Dict[SubsystemType, Dict[str, Any]] = defaultdict(dict)
        self._context_history: deque = deque(maxlen=200)
        self._lock = threading.RLock()

    def update_subsystem_context(self, subsystem: SubsystemType, context: Dict[str, Any]) -> None:
        with self._lock:
            self._subsystem_contexts[subsystem].update(context)
            self._subsystem_contexts[subsystem]["_last_updated"] = time.time()
            self._aggregate_global_context()

    def get_global_context(self) -> Dict[str, Any]:
        with self._lock:
            return dict(self._global_context)

    def get_subsystem_context(self, subsystem: SubsystemType) -> Dict[str, Any]:
        with self._lock:
            return dict(self._subsystem_contexts.get(subsystem, {}))

    def query_context(self, query: Dict[str, Any]) -> Dict[str, Any]:
        with self._lock:
            results = {}
            for stype, ctx in self._subsystem_contexts.items():
                matching = {}
                for key, value in query.items():
                    if key in ctx and ctx[key] == value:
                        matching[key] = ctx[key]
                if matching:
                    results[stype.value] = matching
            return results

    def snapshot(self) -> Dict[str, Any]:
        with self._lock:
            snap = {
                "global_context": dict(self._global_context),
                "subsystem_count": len(self._subsystem_contexts),
                "subsystems": {s.value: dict(c) for s, c in self._subsystem_contexts.items()},
                "timestamp": time.time(),
            }
            self._context_history.append(snap)
            return snap

    def _aggregate_global_context(self) -> None:
        aggregated: Dict[str, Any] = {}
        for ctx in self._subsystem_contexts.values():
            for key, value in ctx.items():
                if key.startswith("_"):
                    continue
                if key not in aggregated:
                    aggregated[key] = []
                aggregated[key].append(value)
        self._global_context = {
            k: v[0] if len(v) == 1 else v
            for k, v in aggregated.items()
        }


# ---------------------------------------------------------- CollaborationManager ------------------------------------------------------------

class CollaborationManager:
    """Multi-agent collaboration protocol management for coordinated task execution."""

    def __init__(self) -> None:
        self._active_sessions: Dict[str, CollaborationSession] = {}
        self._session_history: deque = deque(maxlen=100)
        self._lock = threading.RLock()

    def create_session(self, participants: List[SubsystemType], shared_context: Optional[Dict[str, Any]] = None) -> CollaborationSession:
        with self._lock:
            session = CollaborationSession(
                participants=participants,
                shared_context=shared_context or {},
            )
            self._active_sessions[session.session_id] = session
            return session

    def negotiate(self, session_id: str, proposals: List[Dict[str, Any]]) -> Dict[str, Any]:
        with self._lock:
            session = self._active_sessions.get(session_id)
            if not session:
                return {"error": "Session not found"}

            session.phase = CollaborationPhase.NEGOTIATION
            scores = []
            for proposal in proposals:
                score = sum(
                    proposal.get("confidence", 0.5) * 0.4 +
                    proposal.get("feasibility", 0.5) * 0.3 +
                    proposal.get("impact", 0.5) * 0.3
                )
                scores.append({"proposal": proposal, "score": score})

            scores.sort(key=lambda x: x["score"], reverse=True)
            winning = scores[0] if scores else None

            if winning and winning["score"] > 0.5:
                session.consensus_reached = True
                session.decisions.append({
                    "proposal": winning["proposal"],
                    "score": winning["score"],
                    "timestamp": time.time(),
                })

            return {
                "session_id": session_id,
                "consensus_reached": session.consensus_reached,
                "top_proposal": winning,
                "all_scores": scores,
            }

    def synchronize(self, session_id: str) -> Dict[str, Any]:
        with self._lock:
            session = self._active_sessions.get(session_id)
            if not session:
                return {"error": "Session not found"}

            session.phase = CollaborationPhase.SYNCHRONIZATION
            sync_data = {
                "session_id": session_id,
                "synchronized": True,
                "shared_context": dict(session.shared_context),
                "decisions": [dict(d) for d in session.decisions],
                "timestamp": time.time(),
            }
            return sync_data

    def resolve(self, session_id: str) -> CollaborationSession:
        with self._lock:
            session = self._active_sessions.pop(session_id, None)
            if session:
                session.phase = CollaborationPhase.RESOLUTION
                session.resolved_at = time.time()
                self._session_history.append(session)
            return session

    def get_active_sessions(self) -> List[Dict[str, Any]]:
        with self._lock:
            return [s.to_dict() for s in self._active_sessions.values()]


# ----------------------------------------------------------- PipelineCoordinator ------------------------------------------------------------

class PipelineCoordinator:
    """End-to-end pipeline workflow orchestration for game development."""

    _STANDARD_PIPELINES: Dict[str, List[Tuple[str, SubsystemType]]] = {
        "game_creation": [
            ("concept_design", SubsystemType.GAME_DESIGNER),
            ("story_development", SubsystemType.STORY_ENGINE),
            ("world_building", SubsystemType.WORLD_SIMULATOR),
            ("content_generation", SubsystemType.AUTONOMOUS_CREATOR),
            ("quest_design", SubsystemType.QUEST_GENERATOR),
            ("dialogue_writing", SubsystemType.DIALOGUE_ENGINE),
            ("behavior_setup", SubsystemType.BEHAVIOR_DESIGNER),
            ("balance_testing", SubsystemType.BALANCE_OPTIMIZER),
            ("performance_review", SubsystemType.PERFORMANCE_OPTIMIZER),
            ("quality_evaluation", SubsystemType.GAME_INTELLIGENCE),
        ],
        "content_generation": [
            ("requirement_analysis", SubsystemType.COGNITIVE_SYNTHESIS),
            ("level_design", SubsystemType.AUTONOMOUS_CREATOR),
            ("npc_creation", SubsystemType.AUTONOMOUS_CREATOR),
            ("item_design", SubsystemType.AUTONOMOUS_CREATOR),
            ("quality_check", SubsystemType.GAME_INTELLIGENCE),
        ],
        "intelligence_analysis": [
            ("data_collection", SubsystemType.PERCEPTION_FUSION),
            ("pattern_analysis", SubsystemType.COGNITIVE_SYNTHESIS),
            ("game_evaluation", SubsystemType.GAME_INTELLIGENCE),
            ("optimization_planning", SubsystemType.PERFORMANCE_OPTIMIZER),
            ("learning_feedback", SubsystemType.LEARNING_LOOP),
        ],
    }

    def __init__(self) -> None:
        self._active_workflows: Dict[str, PipelineWorkflow] = {}
        self._completed_workflows: deque = deque(maxlen=200)
        self._lock = threading.RLock()

    def create_workflow(self, name: str, pipeline_type: str = "game_creation") -> PipelineWorkflow:
        with self._lock:
            stages_def = self._STANDARD_PIPELINES.get(pipeline_type, self._STANDARD_PIPELINES["game_creation"])
            stages = []
            for i, (stage_name, subsystem) in enumerate(stages_def):
                stage = PipelineStage(
                    name=stage_name,
                    subsystem=subsystem,
                    order=i,
                    depends_on=[stages[i - 1].stage_id] if i > 0 else [],
                )
                stages.append(stage)

            workflow = PipelineWorkflow(
                name=name,
                stages=stages,
                total_stages=len(stages),
            )
            self._active_workflows[workflow.workflow_id] = workflow
            return workflow

    def advance_stage(self, workflow_id: str) -> Optional[PipelineStage]:
        with self._lock:
            workflow = self._active_workflows.get(workflow_id)
            if not workflow:
                return None

            if workflow.current_stage < len(workflow.stages):
                current = workflow.stages[workflow.current_stage]
                current.status = "completed"
                workflow.current_stage += 1

                if workflow.current_stage < len(workflow.stages):
                    next_stage = workflow.stages[workflow.current_stage]
                    next_stage.status = "in_progress"
                    return next_stage
                else:
                    workflow.status = "completed"
                    workflow.completed_at = time.time()
                    self._completed_workflows.append(workflow)
                    del self._active_workflows[workflow_id]
            return None

    def get_workflow_status(self, workflow_id: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            workflow = self._active_workflows.get(workflow_id)
            if workflow:
                return {
                    "workflow_id": workflow.workflow_id,
                    "name": workflow.name,
                    "status": workflow.status,
                    "progress": f"{workflow.current_stage}/{workflow.total_stages}",
                    "current_stage": workflow.stages[workflow.current_stage].name if workflow.current_stage < len(workflow.stages) else None,
                    "stages": [{"name": s.name, "status": s.status, "subsystem": s.subsystem.value} for s in workflow.stages],
                }
            return None

    def get_active_workflows(self) -> List[Dict[str, Any]]:
        with self._lock:
            return [w.to_dict() for w in self._active_workflows.values()]


# ----------------------------------------------------------- ResourceAllocator -------------------------------------------------------------

class ResourceAllocator:
    """Dynamic resource allocation across subsystems."""

    def __init__(self) -> None:
        self._resource_pools: Dict[str, float] = {
            "compute": 100.0,
            "memory": 100.0,
            "io": 100.0,
            "network": 100.0,
        }
        self._allocations: Dict[SubsystemType, Dict[str, float]] = defaultdict(dict)
        self._lock = threading.RLock()

    def allocate(self, subsystem: SubsystemType, requirements: Dict[str, float]) -> bool:
        with self._lock:
            for resource, amount in requirements.items():
                if resource not in self._resource_pools:
                    continue
                if self._resource_pools[resource] < amount:
                    return False
                self._resource_pools[resource] -= amount
                self._allocations[subsystem][resource] = self._allocations[subsystem].get(resource, 0) + amount
            return True

    def release(self, subsystem: SubsystemType, resources: Optional[Dict[str, float]] = None) -> None:
        with self._lock:
            if resources is None:
                resources = dict(self._allocations.get(subsystem, {}))
            for resource, amount in resources.items():
                if resource in self._resource_pools:
                    self._resource_pools[resource] = min(100.0, self._resource_pools[resource] + amount)
            if subsystem in self._allocations:
                for resource in resources:
                    self._allocations[subsystem].pop(resource, None)

    def get_availability(self) -> Dict[str, float]:
        with self._lock:
            return dict(self._resource_pools)

    def get_allocations(self) -> Dict[str, Dict[str, float]]:
        with self._lock:
            return {s.value: dict(a) for s, a in self._allocations.items()}


# ------------------------------------------------------------- HealthMonitor ----------------------------------------------------------------

class HealthMonitor:
    """Real-time subsystem health tracking and recovery management."""

    def __init__(self) -> None:
        self._health_records: Dict[SubsystemType, Dict[str, Any]] = defaultdict(dict)
        self._alert_history: deque = deque(maxlen=200)
        self._lock = threading.RLock()

    def update_health(self, subsystem: SubsystemType, metrics: Dict[str, Any]) -> None:
        with self._lock:
            record = self._health_records[subsystem]
            record.update(metrics)
            record["last_updated"] = time.time()

            status = self._compute_health_status(metrics)
            record["status"] = status

            if status in ("degraded", "critical", "offline"):
                self._alert_history.append({
                    "subsystem": subsystem.value,
                    "status": status,
                    "metrics": dict(metrics),
                    "timestamp": time.time(),
                })

    def get_health(self, subsystem: SubsystemType) -> Dict[str, Any]:
        with self._lock:
            return dict(self._health_records.get(subsystem, {}))

    def get_all_health(self) -> Dict[str, Dict[str, Any]]:
        with self._lock:
            return {s.value: dict(r) for s, r in self._health_records.items()}

    def get_alerts(self, limit: int = 20) -> List[Dict[str, Any]]:
        with self._lock:
            return list(self._alert_history)[-limit:]

    def _compute_health_status(self, metrics: Dict[str, Any]) -> str:
        success_rate = metrics.get("success_rate", 1.0)
        response_time = metrics.get("avg_response_time", 0.0)
        error_count = metrics.get("error_count", 0)

        if success_rate < 0.5 or error_count > 10:
            return "critical"
        elif success_rate < 0.8 or response_time > 5.0:
            return "degraded"
        elif success_rate < 0.95:
            return "warning"
        return "healthy"


# -------------------------------------------------------- UnifiedOrchestrationCore ----------------------------------------------------------

class UnifiedOrchestrationCore:
    """Central coordination engine for all agent subsystems."""

    _instance: Optional["UnifiedOrchestrationCore"] = None
    _instance_lock = threading.RLock()

    def __init__(self) -> None:
        if self._instance is not None:
            raise RuntimeError("Use UnifiedOrchestrationCore.get_instance()")
        self._task_dispatcher = TaskDispatcher()
        self._context_aggregator = ContextAggregator()
        self._collaboration_manager = CollaborationManager()
        self._pipeline_coordinator = PipelineCoordinator()
        self._resource_allocator = ResourceAllocator()
        self._health_monitor = HealthMonitor()
        self._mode: OrchestrationMode = OrchestrationMode.ADAPTIVE
        self._initialized: bool = False
        self._task_registry: Dict[str, OrchestratedTask] = {}
        self._lock = threading.RLock()

    @classmethod
    def get_instance(cls) -> "UnifiedOrchestrationCore":
        if cls._instance is None:
            with cls._instance_lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def initialize(self) -> None:
        with self._lock:
            if self._initialized:
                return
            for subsystem in SubsystemType:
                self._task_dispatcher.register_subsystem(subsystem)
                self._health_monitor.update_health(subsystem, {
                    "status": "healthy",
                    "success_rate": 1.0,
                    "avg_response_time": 0.0,
                    "error_count": 0,
                })
            self._initialized = True

    @property
    def task_dispatcher(self) -> TaskDispatcher:
        return self._task_dispatcher

    @property
    def context_aggregator(self) -> ContextAggregator:
        return self._context_aggregator

    @property
    def collaboration_manager(self) -> CollaborationManager:
        return self._collaboration_manager

    @property
    def pipeline_coordinator(self) -> PipelineCoordinator:
        return self._pipeline_coordinator

    @property
    def resource_allocator(self) -> ResourceAllocator:
        return self._resource_allocator

    @property
    def health_monitor(self) -> HealthMonitor:
        return self._health_monitor

    def submit_task(self, name: str, target: SubsystemType, payload: Optional[Dict[str, Any]] = None,
                    priority: TaskPriority = TaskPriority.MEDIUM) -> OrchestratedTask:
        with self._lock:
            task = OrchestratedTask(
                name=name,
                target_subsystem=target,
                priority=priority,
                payload=payload or {},
            )
            self._task_registry[task.task_id] = task
            self._task_dispatcher.dispatch(task)
            return task

    def complete_task(self, task_id: str, success: bool, result: Optional[Dict[str, Any]] = None) -> None:
        with self._lock:
            task = self._task_registry.get(task_id)
            if task:
                task.status = TaskStatus.COMPLETED if success else TaskStatus.FAILED
                task.result = result
                task.completed_at = time.time()
                self._task_dispatcher.complete_task(task_id, success, result)

    def orchestrate_pipeline(self, pipeline_type: str) -> PipelineWorkflow:
        with self._lock:
            return self._pipeline_coordinator.create_workflow(
                name=f"{pipeline_type}_{uuid.uuid4().hex[:8]}",
                pipeline_type=pipeline_type,
            )

    def generate_report(self) -> OrchestrationReport:
        with self._lock:
            profiles = self._task_dispatcher.get_profiles()
            return OrchestrationReport(
                total_tasks=len(self._task_registry),
                completed_tasks=sum(1 for t in self._task_registry.values() if t.status == TaskStatus.COMPLETED),
                failed_tasks=sum(1 for t in self._task_registry.values() if t.status == TaskStatus.FAILED),
                active_workflows=len(self._pipeline_coordinator._active_workflows),
                subsystem_health={
                    s.value: self._health_monitor.get_health(s).get("status", "unknown")
                    for s in SubsystemType
                },
                performance_metrics={
                    "avg_success_rate": sum(p.success_rate for p in profiles.values()) / max(len(profiles), 1),
                    "total_active_tasks": sum(p.active_tasks for p in profiles.values()),
                    "total_completed": sum(p.completed_tasks for p in profiles.values()),
                },
            )

    def get_status(self) -> Dict[str, Any]:
        with self._lock:
            report = self.generate_report()
            return {
                "mode": self._mode.value,
                "initialized": self._initialized,
                "subsystems_registered": len(self._task_dispatcher.get_profiles()),
                "active_tasks": sum(1 for t in self._task_registry.values() if t.status in (TaskStatus.PENDING, TaskStatus.DISPATCHED, TaskStatus.IN_PROGRESS)),
                "active_workflows": report.active_workflows,
                "resource_availability": self._resource_allocator.get_availability(),
                "recent_alerts": len(self._health_monitor.get_alerts(10)),
            }


# ----------------------------------------------------------------- Singleton Accessor ----------------------------------------------------------------

def get_unified_orchestration() -> UnifiedOrchestrationCore:
    """Get or create the singleton UnifiedOrchestrationCore instance."""
    return UnifiedOrchestrationCore.get_instance()