"""
SparkLabs Agent - Agent Intelligence Core

The centralized AI orchestration hub that unifies all SparkLabs agent
subsystems into a cohesive autonomous intelligence system. The Intelligence
Core acts as the central nervous system for the SparkLabs game engine,
coordinating perception, reasoning, learning, creativity, social interaction,
task execution, memory, safety, world intelligence, and game design into a
single unified decision-making framework.

Architecture:
  AgentIntelligenceCore (singleton)
    |-- UnifiedPerceptionState (aggregated sensory data model)
    |-- StrategicReasoningState (goal-oriented planning state)
    |-- AutonomousLearningState (adaptive learning pipeline state)
    |-- CreativeSynthesisState (generative content creation state)
    |-- SocialIntelligenceState (social dynamics and persona state)
    |-- TaskExecutionState (multi-agent orchestration state)
    |-- MemoryKnowledgeState (consolidated memory and knowledge state)
    |-- SafetyGovernanceState (content safety and guard state)
    |-- WorldIntelligenceState (world simulation and economy state)
    |-- GameDesignIntelligenceState (design analysis and forecasting state)
    |-- IntelligenceEvent (immutable record of core activity)
    |-- SubsystemStatus (health status of each subsystem)
    |-- CorePhase (operational phases of the intelligence core)
    |-- SubsystemType (enumerated subsystem identifiers)

Core Capabilities:
  - process_perception: Unified perception pipeline aggregating all sensory inputs
  - strategic_reason: Goal-driven strategic reasoning with chain/tree-of-thought
  - autonomous_learn: Adaptive learning cycle with feedback integration
  - creative_synthesize: Generative content creation across creative domains
  - get_status: Real-time health snapshot of all subsystems
  - get_intelligence_report: Comprehensive intelligence status and metrics
  - shutdown: Graceful teardown of all subsystem pipelines

Usage:
    core = get_agent_intelligence_core()
    perception = core.process_perception({"world_state": {...}, "agent_states": [...]})
    plan = core.strategic_reason("Design a puzzle level", {"difficulty": "medium"})
    learning = core.autonomous_learn({"reward": 0.85, "trajectory": [...]})
    content = core.creative_synthesize("Fantasy forest village", "world_building")
    report = core.get_intelligence_report()
    core.shutdown()
"""

from __future__ import annotations

import json
import math
import random
import threading
import time
import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

_time_module = time


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class SubsystemType(Enum):
    """Enumerates the ten core subsystems of the Agent Intelligence Core."""

    PERCEPTION = "perception"
    STRATEGIC_REASONING = "strategic_reasoning"
    AUTONOMOUS_LEARNING = "autonomous_learning"
    CREATIVE_SYNTHESIS = "creative_synthesis"
    SOCIAL_INTELLIGENCE = "social_intelligence"
    TASK_EXECUTION = "task_execution"
    MEMORY_KNOWLEDGE = "memory_knowledge"
    SAFETY_GOVERNANCE = "safety_governance"
    WORLD_INTELLIGENCE = "world_intelligence"
    GAME_DESIGN_INTELLIGENCE = "game_design_intelligence"


class CorePhase(Enum):
    """Operational phases representing the current lifecycle state of the core."""

    UNINITIALIZED = "uninitialized"
    BOOTING = "booting"
    IDLE = "idle"
    PERCEIVING = "perceiving"
    REASONING = "reasoning"
    LEARNING = "learning"
    CREATING = "creating"
    ORCHESTRATING = "orchestrating"
    SHUTTING_DOWN = "shutting_down"
    SHUTDOWN = "shutdown"
    ERROR = "error"


class SubsystemHealth(Enum):
    """Health status indicators for individual subsystems."""

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    STRAINED = "strained"
    RECOVERING = "recovering"
    OFFLINE = "offline"
    ERROR = "error"


class GovernanceMode(Enum):
    """Safety governance operating modes."""

    PERMISSIVE = "permissive"
    STANDARD = "standard"
    STRICT = "strict"
    LOCKDOWN = "lockdown"


class ReasoningStrategy(Enum):
    """Available strategic reasoning approaches."""

    CHAIN_OF_THOUGHT = "chain_of_thought"
    TREE_OF_THOUGHT = "tree_of_thought"
    GOAL_DECOMPOSITION = "goal_decomposition"
    CONSTRAINT_SATISFACTION = "constraint_satisfaction"
    HEURISTIC_SEARCH = "heuristic_search"
    COUNTERFACTUAL = "counterfactual"


class LearningMode(Enum):
    """Autonomous learning operational modes."""

    ACTIVE = "active"
    PASSIVE = "passive"
    CURRICULUM = "curriculum"
    EXPLORATORY = "exploratory"
    EXPLOITATIVE = "exploitative"
    META = "meta"


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------

@dataclass
class SubsystemStatus:
    """Runtime health snapshot of a single subsystem.

    Attributes:
        id: Unique subsystem status identifier.
        subsystem: The enumerated subsystem this status describes.
        health: Current health state of the subsystem.
        active_pipelines: Number of concurrently executing pipelines.
        total_operations: Cumulative operations processed since boot.
        total_errors: Cumulative error count since boot.
        avg_latency_ms: Rolling average latency in milliseconds.
        last_activity: Timestamp of the most recent activity.
        metadata: Arbitrary subsystem-specific metadata.
    """

    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    subsystem: str = SubsystemType.PERCEPTION.value
    health: str = SubsystemHealth.HEALTHY.value
    active_pipelines: int = 0
    total_operations: int = 0
    total_errors: int = 0
    avg_latency_ms: float = 0.0
    last_activity: float = field(default_factory=_time_module.time)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "subsystem": self.subsystem,
            "health": self.health,
            "active_pipelines": self.active_pipelines,
            "total_operations": self.total_operations,
            "total_errors": self.total_errors,
            "avg_latency_ms": self.avg_latency_ms,
            "last_activity": self.last_activity,
            "metadata": self.metadata,
        }


@dataclass
class IntelligenceEvent:
    """Immutable record of a significant event within the intelligence core.

    Captures operation-level telemetry for auditing, debugging, and
    performance analysis across all ten subsystems.

    Attributes:
        id: Unique event identifier.
        subsystem: Which subsystem originated this event.
        event_type: Category of event (e.g., "perception_cycle",
            "reasoning_step", "learning_iteration").
        phase: Core phase during which the event occurred.
        duration_ms: Wall-clock duration of the event in milliseconds.
        success: Whether the event completed successfully.
        input_summary: Human-readable summary of inputs.
        output_summary: Human-readable summary of results.
        error_message: Error details if the event failed.
        metadata: Arbitrary event-specific metadata.
        timestamp: Unix timestamp of event creation.
    """

    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    subsystem: str = SubsystemType.PERCEPTION.value
    event_type: str = ""
    phase: str = CorePhase.IDLE.value
    duration_ms: float = 0.0
    success: bool = True
    input_summary: str = ""
    output_summary: str = ""
    error_message: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=_time_module.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "subsystem": self.subsystem,
            "event_type": self.event_type,
            "phase": self.phase,
            "duration_ms": self.duration_ms,
            "success": self.success,
            "input_summary": self.input_summary,
            "output_summary": self.output_summary,
            "error_message": self.error_message,
            "metadata": self.metadata,
            "timestamp": self.timestamp,
        }


@dataclass
class UnifiedPerceptionState:
    """Aggregated perception model merging all sensory input streams.

    Fuses data from world simulation, social dynamics, emergent narrative,
    game state, and agent observations into a single coherent perceptual
    frame that downstream subsystems can consume.

    Attributes:
        id: Unique perception frame identifier.
        world_snapshot: Serialized world simulation state.
        agent_states: States of all observed agents.
        social_graph: Current social relationship topology.
        narrative_context: Active narrative and emergent story data.
        game_state_summary: Compressed game state representation.
        attention_focus: Salient entities currently in focus.
        novelty_scores: Per-entity novelty detection scores.
        confidence: Overall perceptual confidence [0.0, 1.0].
        timestamp: When this perception frame was generated.
    """

    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    world_snapshot: Dict[str, Any] = field(default_factory=dict)
    agent_states: List[Dict[str, Any]] = field(default_factory=list)
    social_graph: Dict[str, Any] = field(default_factory=dict)
    narrative_context: Dict[str, Any] = field(default_factory=dict)
    game_state_summary: Dict[str, Any] = field(default_factory=dict)
    attention_focus: List[str] = field(default_factory=list)
    novelty_scores: Dict[str, float] = field(default_factory=dict)
    confidence: float = 0.0
    timestamp: float = field(default_factory=_time_module.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "world_snapshot": self.world_snapshot,
            "agent_states": self.agent_states,
            "social_graph": self.social_graph,
            "narrative_context": self.narrative_context,
            "game_state_summary": self.game_state_summary,
            "attention_focus": self.attention_focus,
            "novelty_scores": self.novelty_scores,
            "confidence": self.confidence,
            "timestamp": self.timestamp,
        }


@dataclass
class StrategicReasoningState:
    """Tracks the state of an active strategic reasoning session.

    Maintains a structured representation of goals, decomposed sub-goals,
    reasoning traces, explored thought branches, and constraint models
    throughout the planning lifecycle.

    Attributes:
        id: Unique reasoning session identifier.
        goal: Top-level strategic goal string.
        constraints: Structured constraint dictionary.
        sub_goals: Decomposed sub-goal hierarchy.
        reasoning_trace: Recorded chain-of-thought reasoning steps.
        thought_tree: Explored tree-of-thought branches.
        selected_strategy: The reasoning strategy in use.
        plan: Generated action plan as a list of steps.
        confidence: Plan confidence score [0.0, 1.0].
        estimated_cost: Predicted resource cost of plan execution.
        timestamp: When the reasoning session began.
    """

    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    goal: str = ""
    constraints: Dict[str, Any] = field(default_factory=dict)
    sub_goals: List[Dict[str, Any]] = field(default_factory=list)
    reasoning_trace: List[str] = field(default_factory=list)
    thought_tree: Dict[str, Any] = field(default_factory=dict)
    selected_strategy: str = ReasoningStrategy.CHAIN_OF_THOUGHT.value
    plan: List[Dict[str, Any]] = field(default_factory=list)
    confidence: float = 0.0
    estimated_cost: float = 0.0
    timestamp: float = field(default_factory=_time_module.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "goal": self.goal,
            "constraints": self.constraints,
            "sub_goals": self.sub_goals,
            "reasoning_trace": self.reasoning_trace,
            "thought_tree": self.thought_tree,
            "selected_strategy": self.selected_strategy,
            "plan": self.plan,
            "confidence": self.confidence,
            "estimated_cost": self.estimated_cost,
            "timestamp": self.timestamp,
        }


@dataclass
class AutonomousLearningState:
    """State tracking for the autonomous learning pipeline.

    Manages the learning loop, skill evolution trajectories, curriculum
    progression, and feedback integration across all learning modalities.

    Attributes:
        id: Unique learning state identifier.
        mode: Current learning operational mode.
        iteration: Current learning iteration counter.
        skill_registry: Map of skill IDs to evolution states.
        curriculum_stage: Current position in the curriculum.
        trajectory_buffer: Recent learning trajectory data.
        reward_history: Rolling window of reward signals.
        loss_history: Rolling window of loss values.
        exploration_rate: Current exploration vs exploitation balance.
        learning_rate: Current effective learning rate.
        meta_knowledge: Knowledge about the learning process itself.
        timestamp: Last update timestamp.
    """

    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    mode: str = LearningMode.PASSIVE.value
    iteration: int = 0
    skill_registry: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    curriculum_stage: int = 0
    trajectory_buffer: List[Dict[str, Any]] = field(default_factory=list)
    reward_history: List[float] = field(default_factory=list)
    loss_history: List[float] = field(default_factory=list)
    exploration_rate: float = 0.1
    learning_rate: float = 0.001
    meta_knowledge: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=_time_module.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "mode": self.mode,
            "iteration": self.iteration,
            "skill_registry": self.skill_registry,
            "curriculum_stage": self.curriculum_stage,
            "trajectory_buffer": self.trajectory_buffer,
            "reward_history": self.reward_history,
            "loss_history": self.loss_history,
            "exploration_rate": self.exploration_rate,
            "learning_rate": self.learning_rate,
            "meta_knowledge": self.meta_knowledge,
            "timestamp": self.timestamp,
        }


@dataclass
class CreativeSynthesisState:
    """Manages creative content generation state across multiple domains.

    Tracks creative direction, narrative composition progress, world
    building artifacts, and quest generation pipelines.

    Attributes:
        id: Unique creative session identifier.
        domain: The creative domain (world_building, narrative, quest, etc.).
        brief: Original creative brief string.
        generated_artifacts: Collection of generated creative outputs.
        style_profile: Current aesthetic and tonal style parameters.
        narrative_threads: Active narrative composition threads.
        world_building_layers: Layered world construction state.
        quest_graph: Generated quest dependency graph.
        iteration_count: Number of refinement iterations applied.
        quality_score: Assessed creative quality [0.0, 1.0].
        timestamp: Creation timestamp.
    """

    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    domain: str = "world_building"
    brief: str = ""
    generated_artifacts: List[Dict[str, Any]] = field(default_factory=list)
    style_profile: Dict[str, Any] = field(default_factory=dict)
    narrative_threads: List[Dict[str, Any]] = field(default_factory=list)
    world_building_layers: Dict[str, Any] = field(default_factory=dict)
    quest_graph: Dict[str, Any] = field(default_factory=dict)
    iteration_count: int = 0
    quality_score: float = 0.0
    timestamp: float = field(default_factory=_time_module.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "domain": self.domain,
            "brief": self.brief,
            "generated_artifacts": self.generated_artifacts,
            "style_profile": self.style_profile,
            "narrative_threads": self.narrative_threads,
            "world_building_layers": self.world_building_layers,
            "quest_graph": self.quest_graph,
            "iteration_count": self.iteration_count,
            "quality_score": self.quality_score,
            "timestamp": self.timestamp,
        }


@dataclass
class SocialIntelligenceState:
    """Manages social dynamics and interpersonal intelligence state.

    Coordinates personality systems, emotion synthesis, dialogue engines,
    and social relationship modeling.

    Attributes:
        id: Unique social state identifier.
        personality_models: Active personality models keyed by agent ID.
        emotion_states: Current emotional states for all social agents.
        relationship_graph: Social relationship topology with edge weights.
        dialogue_contexts: Active dialogue session contexts.
        social_norms: Current social norm parameters.
        faction_standing: Standing scores across social factions.
        empathy_parameters: Empathy and theory-of-mind parameters.
        active_conversations: Number of concurrent dialogue sessions.
        timestamp: Last update timestamp.
    """

    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    personality_models: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    emotion_states: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    relationship_graph: Dict[str, Dict[str, float]] = field(default_factory=dict)
    dialogue_contexts: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    social_norms: Dict[str, Any] = field(default_factory=dict)
    faction_standing: Dict[str, float] = field(default_factory=dict)
    empathy_parameters: Dict[str, float] = field(default_factory=dict)
    active_conversations: int = 0
    timestamp: float = field(default_factory=_time_module.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "personality_models": self.personality_models,
            "emotion_states": self.emotion_states,
            "relationship_graph": self.relationship_graph,
            "dialogue_contexts": self.dialogue_contexts,
            "social_norms": self.social_norms,
            "faction_standing": self.faction_standing,
            "empathy_parameters": self.empathy_parameters,
            "active_conversations": self.active_conversations,
            "timestamp": self.timestamp,
        }


@dataclass
class TaskExecutionState:
    """Multi-agent task orchestration and execution state.

    Routes tasks through delegation frameworks, swarm planners, and
    parallel execution pipelines.

    Attributes:
        id: Unique execution state identifier.
        task_queue: Pending tasks awaiting assignment.
        active_tasks: Currently executing tasks with agent assignments.
        completed_tasks: Successfully completed task records.
        agent_pool: Available agent pool with capability profiles.
        delegation_graph: Task-to-agent delegation topology.
        swarm_configuration: Swarm planning parameters.
        parallel_execution_slots: Available parallel execution capacity.
        throughput_rate: Tasks processed per second.
        success_rate: Task completion success ratio.
        timestamp: Last update timestamp.
    """

    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    task_queue: List[Dict[str, Any]] = field(default_factory=list)
    active_tasks: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    completed_tasks: List[Dict[str, Any]] = field(default_factory=list)
    agent_pool: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    delegation_graph: Dict[str, Any] = field(default_factory=dict)
    swarm_configuration: Dict[str, Any] = field(default_factory=dict)
    parallel_execution_slots: int = 8
    throughput_rate: float = 0.0
    success_rate: float = 1.0
    timestamp: float = field(default_factory=_time_module.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "task_queue": self.task_queue,
            "active_tasks": self.active_tasks,
            "completed_tasks": self.completed_tasks,
            "agent_pool": self.agent_pool,
            "delegation_graph": self.delegation_graph,
            "swarm_configuration": self.swarm_configuration,
            "parallel_execution_slots": self.parallel_execution_slots,
            "throughput_rate": self.throughput_rate,
            "success_rate": self.success_rate,
            "timestamp": self.timestamp,
        }


@dataclass
class MemoryKnowledgeState:
    """Unified memory and knowledge consolidation state.

    Coordinates memory consolidation, knowledge synthesis, semantic
    memory indexing, and context weaving across all agent experiences.

    Attributes:
        id: Unique memory state identifier.
        episodic_memory: Recent episodic memory entries.
        semantic_index: Indexed semantic knowledge graph.
        consolidated_memories: Long-term consolidated memory store.
        knowledge_base_size: Total knowledge entries accumulated.
        context_weave: Active context weaving threads.
        memory_graph_edges: Number of connected memory graph nodes.
        retrieval_cache_hit_rate: Recent memory retrieval cache performance.
        forgetting_curve_parameters: Memory decay modeling parameters.
        consolidation_queue_size: Pending memory consolidation count.
        timestamp: Last update timestamp.
    """

    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    episodic_memory: List[Dict[str, Any]] = field(default_factory=list)
    semantic_index: Dict[str, Any] = field(default_factory=dict)
    consolidated_memories: List[Dict[str, Any]] = field(default_factory=list)
    knowledge_base_size: int = 0
    context_weave: Dict[str, Any] = field(default_factory=dict)
    memory_graph_edges: int = 0
    retrieval_cache_hit_rate: float = 0.0
    forgetting_curve_parameters: Dict[str, float] = field(default_factory=dict)
    consolidation_queue_size: int = 0
    timestamp: float = field(default_factory=_time_module.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "episodic_memory": self.episodic_memory,
            "semantic_index": self.semantic_index,
            "consolidated_memories": self.consolidated_memories,
            "knowledge_base_size": self.knowledge_base_size,
            "context_weave": self.context_weave,
            "memory_graph_edges": self.memory_graph_edges,
            "retrieval_cache_hit_rate": self.retrieval_cache_hit_rate,
            "forgetting_curve_parameters": self.forgetting_curve_parameters,
            "consolidation_queue_size": self.consolidation_queue_size,
            "timestamp": self.timestamp,
        }


@dataclass
class SafetyGovernanceState:
    """Safety and governance layer operational state.

    Manages content safety screening, guard system enforcement, circuit
    breaking logic, and approval engine workflows.

    Attributes:
        id: Unique governance state identifier.
        mode: Current safety governance operating mode.
        content_filters_active: Active content filtering rules count.
        guard_rules_enforced: Guard rules currently enforced.
        circuit_breaker_status: Status of each circuit breaker.
        approval_queue: Pending approval requests.
        safety_violations: Cumulative safety violation count.
        escalation_count: Number of escalated content incidents.
        policy_version: Current safety policy version.
        audit_log_size: Cumulative audit log entries.
        timestamp: Last update timestamp.
    """

    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    mode: str = GovernanceMode.STANDARD.value
    content_filters_active: int = 0
    guard_rules_enforced: int = 0
    circuit_breaker_status: Dict[str, str] = field(default_factory=dict)
    approval_queue: List[Dict[str, Any]] = field(default_factory=list)
    safety_violations: int = 0
    escalation_count: int = 0
    policy_version: str = "1.0.0"
    audit_log_size: int = 0
    timestamp: float = field(default_factory=_time_module.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "mode": self.mode,
            "content_filters_active": self.content_filters_active,
            "guard_rules_enforced": self.guard_rules_enforced,
            "circuit_breaker_status": self.circuit_breaker_status,
            "approval_queue": self.approval_queue,
            "safety_violations": self.safety_violations,
            "escalation_count": self.escalation_count,
            "policy_version": self.policy_version,
            "audit_log_size": self.audit_log_size,
            "timestamp": self.timestamp,
        }


@dataclass
class WorldIntelligenceState:
    """World intelligence and simulation management state.

    Manages world simulation parameters, economy simulation state, world
    evolution tracking, and god mode control interfaces.

    Attributes:
        id: Unique world intelligence state identifier.
        simulation_tick: Current world simulation tick counter.
        economy_state: Aggregate economy simulation metrics.
        world_evolution_stage: Current evolutionary stage of the world.
        biome_distribution: Distribution of world biomes.
        population_counts: Entity population statistics.
        resource_maps: Resource distribution and availability maps.
        weather_state: Current global weather state.
        god_mode_active: Whether god mode control is currently active.
        pending_world_events: Scheduled or pending world events.
        timestamp: Last update timestamp.
    """

    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    simulation_tick: int = 0
    economy_state: Dict[str, Any] = field(default_factory=dict)
    world_evolution_stage: int = 0
    biome_distribution: Dict[str, float] = field(default_factory=dict)
    population_counts: Dict[str, int] = field(default_factory=dict)
    resource_maps: Dict[str, Any] = field(default_factory=dict)
    weather_state: Dict[str, Any] = field(default_factory=dict)
    god_mode_active: bool = False
    pending_world_events: List[Dict[str, Any]] = field(default_factory=list)
    timestamp: float = field(default_factory=_time_module.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "simulation_tick": self.simulation_tick,
            "economy_state": self.economy_state,
            "world_evolution_stage": self.world_evolution_stage,
            "biome_distribution": self.biome_distribution,
            "population_counts": self.population_counts,
            "resource_maps": self.resource_maps,
            "weather_state": self.weather_state,
            "god_mode_active": self.god_mode_active,
            "pending_world_events": self.pending_world_events,
            "timestamp": self.timestamp,
        }


@dataclass
class GameDesignIntelligenceState:
    """Game design intelligence and analysis state.

    Coordinates game design analysis, balance prediction, playtest
    orchestration, and game forecasting pipelines.

    Attributes:
        id: Unique design intelligence state identifier.
        design_concepts: Active game design concepts under exploration.
        balance_analyses: Completed balance analysis records.
        playtest_sessions: Active and completed playtest sessions.
        forecast_models: Game forecasting model parameters.
        mechanic_graph: Graph of mechanic interdependencies.
        design_iteration_count: Total design iteration cycles.
        quality_metrics: Aggregated design quality scores.
        pending_forecasts: Forecast tasks awaiting computation.
        recommendations: Generated design recommendations.
        timestamp: Last update timestamp.
    """

    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    design_concepts: List[Dict[str, Any]] = field(default_factory=list)
    balance_analyses: List[Dict[str, Any]] = field(default_factory=list)
    playtest_sessions: List[Dict[str, Any]] = field(default_factory=list)
    forecast_models: Dict[str, Any] = field(default_factory=dict)
    mechanic_graph: Dict[str, Any] = field(default_factory=dict)
    design_iteration_count: int = 0
    quality_metrics: Dict[str, float] = field(default_factory=dict)
    pending_forecasts: int = 0
    recommendations: List[Dict[str, Any]] = field(default_factory=list)
    timestamp: float = field(default_factory=_time_module.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "design_concepts": self.design_concepts,
            "balance_analyses": self.balance_analyses,
            "playtest_sessions": self.playtest_sessions,
            "forecast_models": self.forecast_models,
            "mechanic_graph": self.mechanic_graph,
            "design_iteration_count": self.design_iteration_count,
            "quality_metrics": self.quality_metrics,
            "pending_forecasts": self.pending_forecasts,
            "recommendations": self.recommendations,
            "timestamp": self.timestamp,
        }


# ---------------------------------------------------------------------------
# Knowledge Bases (module-level constants)
# ---------------------------------------------------------------------------

_PERCEPTION_PIPELINE_STAGES: List[str] = [
    "raw_sensory_capture",
    "noise_filtering",
    "feature_extraction",
    "attention_allocation",
    "salience_computation",
    "novelty_detection",
    "context_fusion",
    "confidence_calibration",
    "frame_assembly",
    "output_serialization",
]

_REASONING_HEURISTICS: Dict[str, Any] = {
    "max_decomposition_depth": 5,
    "thought_tree_branching_factor": 3,
    "chain_of_thought_max_steps": 12,
    "constraint_relaxation_threshold": 0.3,
    "counterfactual_sample_count": 5,
    "confidence_decay_rate": 0.05,
    "goal_priority_inference": True,
    "plan_validation_passes": 2,
}

_LEARNING_CURRICULUM_STAGES: List[str] = [
    "observation",
    "imitation",
    "guided_exploration",
    "autonomous_exploration",
    "skill_composition",
    "strategy_formation",
    "meta_learning",
    "transfer_learning",
    "creative_generalization",
]

_CREATIVE_DOMAINS: Dict[str, Dict[str, Any]] = {
    "world_building": {
        "layers": ["geography", "ecology", "civilization", "history", "mythology"],
        "complexity_weight": 0.9,
        "typical_iterations": 5,
    },
    "narrative_composition": {
        "arc_types": ["hero_journey", "tragedy", "comedy", "mystery", "epic", "slice_of_life"],
        "complexity_weight": 0.8,
        "typical_iterations": 4,
    },
    "quest_generation": {
        "quest_types": ["main", "side", "radiant", "faction", "personal", "world_event"],
        "complexity_weight": 0.6,
        "typical_iterations": 3,
    },
    "character_design": {
        "archetypes": ["hero", "mentor", "trickster", "guardian", "shadow", "herald"],
        "complexity_weight": 0.7,
        "typical_iterations": 3,
    },
    "dialogue_writing": {
        "tones": ["dramatic", "humorous", "menacing", "romantic", "philosophical"],
        "complexity_weight": 0.5,
        "typical_iterations": 2,
    },
}

_SAFETY_POLICIES: Dict[str, Dict[str, Any]] = {
    "content_filter": {
        "moderate_violence": "allow",
        "graphic_violence": "block",
        "mild_language": "allow",
        "hate_speech": "block",
        "adult_content": "block",
        "sensitive_topics": "flag_review",
    },
    "guard_rules": {
        "max_concurrent_operations": 100,
        "max_output_tokens_per_request": 16384,
        "max_agent_depth": 5,
        "resource_usage_threshold": 0.85,
        "loop_detection_enabled": True,
    },
    "circuit_breakers": {
        "error_rate_breaker": {"threshold": 0.3, "cooldown_s": 60.0},
        "latency_breaker": {"threshold_ms": 30000, "cooldown_s": 30.0},
        "cost_breaker": {"threshold_usd": 5.0, "cooldown_s": 300.0},
        "loop_breaker": {"max_iterations": 1000, "cooldown_s": 10.0},
    },
}

_WORLD_SIMULATION_DEFAULTS: Dict[str, Any] = {
    "tick_rate_ms": 50,
    "economy_update_interval": 100,
    "evolution_check_interval": 1000,
    "weather_update_interval": 500,
    "population_cap": 1000000,
    "max_active_events": 50,
    "biome_count": 12,
    "resource_types": 24,
}

_GAME_DESIGN_ANALYSIS_DEFAULTS: Dict[str, Any] = {
    "balance_dimensions": [
        "power_curve",
        "resource_economy",
        "risk_reward",
        "time_investment",
        "skill_ceiling",
        "accessibility",
        "variety_depth",
        "snowball_risk",
        "counterplay",
        "pacing",
    ],
    "forecast_horizon_ticks": 10000,
    "monte_carlo_iterations": 1000,
    "playtest_agent_count": 100,
    "mechanic_analysis_depth": 3,
    "recommendation_count": 5,
}


# ---------------------------------------------------------------------------
# Agent Intelligence Core (Singleton)
# ---------------------------------------------------------------------------

class AgentIntelligenceCore:
    """Centralized AI orchestration hub for the SparkLabs game engine.

    Unifies all ten agent subsystems into a cohesive autonomous intelligence
    system. Serves as the single entry point for perception processing,
    strategic reasoning, autonomous learning, creative synthesis, task
    orchestration, memory management, safety enforcement, world intelligence,
    and game design analysis.

    Implements a thread-safe singleton pattern to ensure exactly one
    intelligence core instance exists across the entire application
    lifecycle. All public methods are safe for concurrent access.

    Usage:
        core = AgentIntelligenceCore.get_instance()
        perception = core.process_perception({"world_state": {...}})
        plan = core.strategic_reason("Design boss encounter", {"difficulty": "hard"})
        learning = core.autonomous_learn({"reward": 0.92, "trajectory": [...]})
        content = core.creative_synthesize("Dark forest dungeon", "world_building")
        status = core.get_status()
        report = core.get_intelligence_report()
        core.shutdown()
    """

    _instance: Optional[AgentIntelligenceCore] = None
    _lock: threading.RLock = threading.RLock()

    def __new__(cls) -> AgentIntelligenceCore:
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    instance = super().__new__(cls)
                    instance._initialized = False
                    cls._instance = instance
        return cls._instance

    @classmethod
    def get_instance(cls) -> AgentIntelligenceCore:
        """Return the singleton AgentIntelligenceCore instance.

        Creates and initializes the instance on first access using
        double-checked locking for thread safety.

        Returns:
            The singleton AgentIntelligenceCore instance.
        """
        if cls._instance is None:
            cls()
        return cls._instance

    def __init__(self) -> None:
        if self._initialized:
            return
        self._initialized = True

        # --- Phase and lifecycle ---
        self._phase: str = CorePhase.BOOTING.value
        self._boot_time: float = _time_module.time()
        self._total_cycles: int = 0

        # --- Subsystem status tracking ---
        self._subsystem_statuses: Dict[str, SubsystemStatus] = {}
        for sub in SubsystemType:
            self._subsystem_statuses[sub.value] = SubsystemStatus(
                subsystem=sub.value,
                health=SubsystemHealth.HEALTHY.value,
            )

        # --- Event log ---
        self._event_log: List[IntelligenceEvent] = []

        # --- Perception state ---
        self._perception_state: UnifiedPerceptionState = UnifiedPerceptionState()
        self._perception_history: List[UnifiedPerceptionState] = []
        self._perception_max_history: int = 100

        # --- Reasoning state ---
        self._reasoning_sessions: Dict[str, StrategicReasoningState] = {}
        self._active_reasoning_id: Optional[str] = None

        # --- Learning state ---
        self._learning_state: AutonomousLearningState = AutonomousLearningState()
        self._skill_library: Dict[str, Dict[str, Any]] = {}
        self._trajectory_archive: List[Dict[str, Any]] = []

        # --- Creative state ---
        self._creative_sessions: Dict[str, CreativeSynthesisState] = {}
        self._creative_archive: List[Dict[str, Any]] = []

        # --- Social state ---
        self._social_state: SocialIntelligenceState = SocialIntelligenceState()
        self._dialogue_history: List[Dict[str, Any]] = []

        # --- Task execution state ---
        self._task_state: TaskExecutionState = TaskExecutionState()
        self._delegation_network: Dict[str, List[str]] = defaultdict(list)

        # --- Memory and knowledge state ---
        self._memory_state: MemoryKnowledgeState = MemoryKnowledgeState()
        self._knowledge_index: Dict[str, Any] = {}

        # --- Safety and governance state ---
        self._safety_state: SafetyGovernanceState = SafetyGovernanceState()
        self._circuit_breaker_cooldowns: Dict[str, float] = {}

        # --- World intelligence state ---
        self._world_state: WorldIntelligenceState = WorldIntelligenceState()
        self._world_event_queue: List[Dict[str, Any]] = []

        # --- Game design intelligence state ---
        self._game_design_state: GameDesignIntelligenceState = GameDesignIntelligenceState()
        self._design_pattern_library: Dict[str, Any] = {}

        # --- Pipeline registry ---
        self._pipeline_handlers: Dict[str, Callable] = {}
        self._register_default_pipelines()

        # --- Transition to idle ---
        self._phase = CorePhase.IDLE.value

    # ------------------------------------------------------------------
    # Pipeline Registration
    # ------------------------------------------------------------------

    def _register_default_pipelines(self) -> None:
        """Register default pipeline handlers for all core phases.

        Each pipeline is a hook that subsystems can register for
        phase-level events, enabling extensible processing chains.
        """
        self._pipeline_handlers["pre_perception"] = self._default_pre_perception
        self._pipeline_handlers["post_perception"] = self._default_post_perception
        self._pipeline_handlers["pre_reasoning"] = self._default_pre_reasoning
        self._pipeline_handlers["post_reasoning"] = self._default_post_reasoning
        self._pipeline_handlers["pre_learning"] = self._default_pre_learning
        self._pipeline_handlers["post_learning"] = self._default_post_learning
        self._pipeline_handlers["pre_creative"] = self._default_pre_creative
        self._pipeline_handlers["post_creative"] = self._default_post_creative

    def _default_pre_perception(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Default pre-perception hook: validate and sanitize context."""
        return context

    def _default_post_perception(self, perception: UnifiedPerceptionState) -> UnifiedPerceptionState:
        """Default post-perception hook: archive and return."""
        self._perception_history.append(perception)
        if len(self._perception_history) > self._perception_max_history:
            self._perception_history = self._perception_history[-self._perception_max_history:]
        return perception

    def _default_pre_reasoning(self, goal: str, constraints: Dict[str, Any]) -> Tuple[str, Dict[str, Any]]:
        """Default pre-reasoning hook: normalize goal and constraints."""
        return goal.strip(), constraints

    def _default_post_reasoning(self, state: StrategicReasoningState) -> StrategicReasoningState:
        """Default post-reasoning hook: archive session."""
        self._reasoning_sessions[state.id] = state
        return state

    def _default_pre_learning(self, feedback: Dict[str, Any]) -> Dict[str, Any]:
        """Default pre-learning hook: validate feedback structure."""
        return feedback

    def _default_post_learning(self, state: AutonomousLearningState) -> AutonomousLearningState:
        """Default post-learning hook: update trajectory archive."""
        if state.trajectory_buffer:
            self._trajectory_archive.extend(state.trajectory_buffer[-10:])
        return state

    def _default_pre_creative(self, brief: str, domain: str) -> Tuple[str, str]:
        """Default pre-creative hook: validate domain and normalize brief."""
        if domain not in _CREATIVE_DOMAINS:
            domain = "world_building"
        return brief.strip(), domain

    def _default_post_creative(self, state: CreativeSynthesisState) -> CreativeSynthesisState:
        """Default post-creative hook: archive creative session."""
        self._creative_sessions[state.id] = state
        return state

    # ------------------------------------------------------------------
    # Event Logging
    # ------------------------------------------------------------------

    def _record_event(
        self,
        subsystem: str,
        event_type: str,
        duration_ms: float,
        success: bool,
        input_summary: str = "",
        output_summary: str = "",
        error_message: str = "",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> IntelligenceEvent:
        """Record an operational event for auditing and telemetry.

        Args:
            subsystem: The originating subsystem identifier.
            event_type: Category label for this event.
            duration_ms: Wall-clock duration in milliseconds.
            success: Whether the operation succeeded.
            input_summary: Brief summary of inputs.
            output_summary: Brief summary of results.
            error_message: Error details if the operation failed.
            metadata: Additional event-specific context.

        Returns:
            The recorded IntelligenceEvent instance.
        """
        event = IntelligenceEvent(
            subsystem=subsystem,
            event_type=event_type,
            phase=self._phase,
            duration_ms=duration_ms,
            success=success,
            input_summary=input_summary,
            output_summary=output_summary,
            error_message=error_message,
            metadata=metadata or {},
        )
        self._event_log.append(event)

        # Prune event log to prevent unbounded growth
        if len(self._event_log) > 10000:
            self._event_log = self._event_log[-5000:]

        # Update subsystem status counters
        status = self._subsystem_statuses.get(subsystem)
        if status:
            status.total_operations += 1
            if not success:
                status.total_errors += 1
            status.last_activity = _time_module.time()

            # Rolling average latency
            n = status.total_operations
            status.avg_latency_ms = (
                (status.avg_latency_ms * (n - 1) + duration_ms) / max(n, 1)
            )

        return event

    def _update_subsystem_health(self, subsystem: str) -> None:
        """Recompute health status for a subsystem based on recent metrics.

        Uses error rate and latency thresholds to classify health as
        HEALTHY, DEGRADED, STRAINED, or ERROR.

        Args:
            subsystem: The subsystem to re-evaluate.
        """
        status = self._subsystem_statuses.get(subsystem)
        if not status:
            return

        total = max(status.total_operations, 1)
        error_rate = status.total_errors / total

        if error_rate > 0.5:
            status.health = SubsystemHealth.ERROR.value
        elif error_rate > 0.2:
            status.health = SubsystemHealth.STRAINED.value
        elif error_rate > 0.05:
            status.health = SubsystemHealth.DEGRADED.value
        else:
            status.health = SubsystemHealth.HEALTHY.value

    # ------------------------------------------------------------------
    # 1. Unified Perception Engine
    # ------------------------------------------------------------------

    def process_perception(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the unified perception pipeline on incoming context.

        Aggregates data from world simulation, social dynamics, emergent
        narrative, game state, and agent observations into a single
        coherent UnifiedPerceptionState. The pipeline runs through
        multiple stages: raw capture, noise filtering, feature extraction,
        attention allocation, salience computation, novelty detection,
        context fusion, confidence calibration, frame assembly, and
        serialization.

        Args:
            context: Raw perception context dictionary typically containing
                keys such as "world_state", "agent_states", "social_graph",
                "narrative_context", and "game_state_summary".

        Returns:
            A dictionary representing the UnifiedPerceptionState including
            the assembled perception frame, confidence score, attention
            focus list, and novelty detection results.
        """
        start_time = _time_module.time()
        self._phase = CorePhase.PERCEIVING.value

        try:
            # Pipeline stage 0: Pre-processing hook
            context = self._pipeline_handlers["pre_perception"](context)

            # Stage 1: Raw sensory capture
            world_snapshot = context.get("world_state", {})
            if not world_snapshot:
                world_snapshot = self._world_state.to_dict()

            # Stage 2: Noise filtering — remove null/empty entries
            agent_states = [
                s for s in context.get("agent_states", [])
                if s and isinstance(s, dict)
            ]

            # Stage 3: Feature extraction
            social_graph = context.get("social_graph", {})
            narrative_context = context.get("narrative_context", {})
            game_state_summary = context.get("game_state_summary", {})

            if not game_state_summary:
                game_state_summary = {
                    "tick": self._world_state.simulation_tick,
                    "population": sum(self._world_state.population_counts.values()),
                    "active_events": len(self._world_state.pending_world_events),
                }

            # Stage 4: Attention allocation — identify salient entities
            attention_focus: List[str] = []
            for agent in agent_states:
                agent_id = agent.get("id", "")
                importance = agent.get("importance", 0.0)
                if importance > 0.5 and agent_id:
                    attention_focus.append(agent_id)

            # Include world entities with high salience
            for entity_id, salience in context.get("entity_salience", {}).items():
                if salience > 0.6 and entity_id not in attention_focus:
                    attention_focus.append(entity_id)

            # Limit attention focus to top 20
            attention_focus = attention_focus[:20]

            # Stage 5: Salience computation
            salience_map: Dict[str, float] = {}
            for agent in agent_states:
                agent_id = agent.get("id", "")
                if agent_id:
                    base_salience = agent.get("importance", 0.3)
                    # Boost salience for agents in attention focus
                    if agent_id in attention_focus:
                        base_salience = min(base_salience * 1.5, 1.0)
                    salience_map[agent_id] = base_salience

            # Stage 6: Novelty detection
            novelty_scores: Dict[str, float] = {}
            previous_frame = (
                self._perception_history[-1] if self._perception_history else None
            )
            for agent in agent_states:
                agent_id = agent.get("id", "")
                if not agent_id:
                    continue
                novelty = 0.0
                if previous_frame and previous_frame.agent_states:
                    prev_states = {
                        a.get("id"): a for a in previous_frame.agent_states if a.get("id")
                    }
                    if agent_id in prev_states:
                        # Compute simple state delta as novelty
                        prev = prev_states[agent_id]
                        delta_fields = sum(
                            1 for k in agent if agent.get(k) != prev.get(k)
                        )
                        novelty = min(delta_fields / max(len(agent), 1), 1.0)
                    else:
                        novelty = 1.0  # New entity
                else:
                    novelty = 0.5  # First frame, unknown
                novelty_scores[agent_id] = round(novelty, 4)

            # Stage 7: Context fusion — merge with existing world state
            fused_world = {**self._world_state.to_dict(), **world_snapshot}
            fused_social = {**self._social_state.relationship_graph, **social_graph}

            # Stage 8: Confidence calibration
            context_completeness = 0.0
            expected_keys = {"world_state", "agent_states", "game_state_summary"}
            present_keys = expected_keys & set(context.keys())
            context_completeness = len(present_keys) / len(expected_keys)
            salience_avg = sum(salience_map.values()) / max(len(salience_map), 1)
            confidence = round((context_completeness + salience_avg) / 2, 4)

            # Stage 9: Frame assembly
            self._perception_state = UnifiedPerceptionState(
                world_snapshot=fused_world,
                agent_states=agent_states,
                social_graph=fused_social,
                narrative_context=narrative_context,
                game_state_summary=game_state_summary,
                attention_focus=attention_focus,
                novelty_scores=novelty_scores,
                confidence=confidence,
            )

            # Stage 10: Post-processing hook
            self._perception_state = self._pipeline_handlers["post_perception"](
                self._perception_state
            )

            duration_ms = (_time_module.time() - start_time) * 1000
            self._record_event(
                subsystem=SubsystemType.PERCEPTION.value,
                event_type="perception_cycle",
                duration_ms=round(duration_ms, 2),
                success=True,
                input_summary=f"{len(agent_states)} agents, {len(attention_focus)} in focus",
                output_summary=f"confidence={confidence:.3f}, novelty_entities={len([n for n in novelty_scores.values() if n > 0.5])}",
            )
            self._update_subsystem_health(SubsystemType.PERCEPTION.value)

            self._total_cycles += 1
            return self._perception_state.to_dict()

        except Exception as exc:
            duration_ms = (_time_module.time() - start_time) * 1000
            self._record_event(
                subsystem=SubsystemType.PERCEPTION.value,
                event_type="perception_cycle",
                duration_ms=round(duration_ms, 2),
                success=False,
                error_message=str(exc),
                metadata={"context_keys": list(context.keys())},
            )
            self._update_subsystem_health(SubsystemType.PERCEPTION.value)
            self._phase = CorePhase.ERROR.value
            return {
                "error": str(exc),
                "confidence": 0.0,
                "attention_focus": [],
                "novelty_scores": {},
            }

        finally:
            if self._phase == CorePhase.PERCEIVING.value:
                self._phase = CorePhase.IDLE.value

    # ------------------------------------------------------------------
    # 2. Strategic Reasoning Core
    # ------------------------------------------------------------------

    def strategic_reason(self, goal: str, constraints: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Execute the strategic reasoning pipeline for a given goal.

        Processes a high-level strategic goal through chain-of-thought
        reasoning, tree-of-thought exploration, and goal decomposition.
        Constructs a structured reasoning session with sub-goals, a
        reasoning trace, explored thought branches, and an executable
        action plan.

        The pipeline:
        1. Normalizes and validates the goal and constraints.
        2. Performs goal decomposition into hierarchical sub-goals.
        3. Executes chain-of-thought reasoning, recording each step.
        4. Explores alternative paths via tree-of-thought branching.
        5. Assembles a ranked action plan with confidence estimates.
        6. Validates the plan against constraints.

        Args:
            goal: A strategic goal expressed in natural language.
            constraints: Optional dictionary of constraints including keys
                such as "difficulty", "resources", "time_limit", "prerequisites",
                and "risk_tolerance".

        Returns:
            A dictionary containing the reasoning session ID, decomposed
            sub-goals, reasoning trace, thought tree, action plan,
            confidence score, and estimated cost.
        """
        start_time = _time_module.time()
        self._phase = CorePhase.REASONING.value
        constraints = constraints or {}

        try:
            # Pre-processing
            goal, constraints = self._pipeline_handlers["pre_reasoning"](goal, constraints)

            # Strategy selection based on constraints
            strategy = ReasoningStrategy.CHAIN_OF_THOUGHT.value
            if constraints.get("explore_alternatives", False):
                strategy = ReasoningStrategy.TREE_OF_THOUGHT.value
            elif constraints.get("decomposition_required", True):
                strategy = ReasoningStrategy.GOAL_DECOMPOSITION.value

            # Goal decomposition
            decomposition_depth = min(
                constraints.get("max_depth", _REASONING_HEURISTICS["max_decomposition_depth"]),
                _REASONING_HEURISTICS["max_decomposition_depth"],
            )
            sub_goals = self._decompose_goal(goal, decomposition_depth)

            # Chain-of-thought reasoning trace
            reasoning_trace = self._generate_reasoning_trace(goal, sub_goals, constraints)

            # Tree-of-thought exploration (if selected)
            thought_tree: Dict[str, Any] = {"root": goal, "branches": []}
            if strategy == ReasoningStrategy.TREE_OF_THOUGHT.value:
                thought_tree = self._explore_thought_tree(goal, sub_goals, constraints)

            # Plan assembly
            plan = self._assemble_plan(sub_goals, constraints)

            # Confidence estimation
            sub_goal_count = len(sub_goals)
            plan_length = len(plan)
            confidence = self._estimate_plan_confidence(
                sub_goal_count, plan_length, constraints
            )

            # Cost estimation
            estimated_cost = self._estimate_plan_cost(plan, constraints)

            # Build reasoning state
            state = StrategicReasoningState(
                goal=goal,
                constraints=constraints,
                sub_goals=sub_goals,
                reasoning_trace=reasoning_trace,
                thought_tree=thought_tree,
                selected_strategy=strategy,
                plan=plan,
                confidence=confidence,
                estimated_cost=estimated_cost,
            )

            # Post-processing
            state = self._pipeline_handlers["post_reasoning"](state)
            self._active_reasoning_id = state.id

            duration_ms = (_time_module.time() - start_time) * 1000
            self._record_event(
                subsystem=SubsystemType.STRATEGIC_REASONING.value,
                event_type="reasoning_session",
                duration_ms=round(duration_ms, 2),
                success=True,
                input_summary=f"goal='{goal[:60]}...' ({strategy})",
                output_summary=f"{sub_goal_count} sub-goals, {plan_length} steps, confidence={confidence:.3f}",
            )
            self._update_subsystem_health(SubsystemType.STRATEGIC_REASONING.value)

            result = state.to_dict()
            result["subsystem"] = SubsystemType.STRATEGIC_REASONING.value
            return result

        except Exception as exc:
            duration_ms = (_time_module.time() - start_time) * 1000
            self._record_event(
                subsystem=SubsystemType.STRATEGIC_REASONING.value,
                event_type="reasoning_session",
                duration_ms=round(duration_ms, 2),
                success=False,
                error_message=str(exc),
            )
            self._update_subsystem_health(SubsystemType.STRATEGIC_REASONING.value)
            self._phase = CorePhase.ERROR.value
            return {
                "error": str(exc),
                "goal": goal,
                "sub_goals": [],
                "plan": [],
                "confidence": 0.0,
                "subsystem": SubsystemType.STRATEGIC_REASONING.value,
            }

        finally:
            if self._phase == CorePhase.REASONING.value:
                self._phase = CorePhase.IDLE.value

    def _decompose_goal(self, goal: str, max_depth: int) -> List[Dict[str, Any]]:
        """Decompose a strategic goal into hierarchical sub-goals.

        Uses keyword-based analysis to identify action domains and
        recursively break down the goal into actionable sub-goals up
        to the specified maximum depth.

        Args:
            goal: The top-level goal string.
            max_depth: Maximum decomposition depth.

        Returns:
            A list of sub-goal dictionaries with id, description, depth,
            priority, dependencies, and estimated effort.
        """
        sub_goals: List[Dict[str, Any]] = []

        # Action-domain keywords for intelligent decomposition
        action_domains = {
            "design": ["design", "create", "build", "craft", "architect", "construct"],
            "implement": ["implement", "code", "develop", "program", "write"],
            "test": ["test", "verify", "validate", "check", "audit"],
            "optimize": ["optimize", "improve", "enhance", "refine", "tune"],
            "analyze": ["analyze", "assess", "evaluate", "measure", "review"],
            "orchestrate": ["coordinate", "manage", "orchestrate", "delegate", "assign"],
        }

        goal_lower = goal.lower()
        matched_domains = []
        for domain, keywords in action_domains.items():
            if any(kw in goal_lower for kw in keywords):
                matched_domains.append(domain)

        if not matched_domains:
            matched_domains = ["implement", "test"]  # Default domains

        for depth in range(min(max_depth, 3)):  # Limit to 3 levels
            for i, domain in enumerate(matched_domains):
                sub_goals.append({
                    "id": f"sg_{depth}_{i}_{uuid.uuid4().hex[:6]}",
                    "description": f"[{domain.upper()}] Decomposed step {depth + 1}.{i + 1} for: {goal[:80]}",
                    "depth": depth,
                    "priority": min(i + 1, 3),
                    "dependencies": [
                        f"sg_{depth - 1}_{j}" for j in range(len(matched_domains))
                    ] if depth > 0 else [],
                    "estimated_effort": round(1.0 / (depth + 1) * (1.0 + 0.5 * i), 2),
                })

        return sub_goals

    def _generate_reasoning_trace(
        self, goal: str, sub_goals: List[Dict[str, Any]], constraints: Dict[str, Any]
    ) -> List[str]:
        """Generate a chain-of-thought reasoning trace.

        Produces a step-by-step reasoning log that documents the
        analytical process from goal identification through sub-goal
        prioritization, constraint analysis, and action sequencing.

        Args:
            goal: The strategic goal.
            sub_goals: Decomposed sub-goals.
            constraints: Operational constraints.

        Returns:
            A list of reasoning step strings.
        """
        trace: List[str] = []

        trace.append(f"GOAL: {goal}")
        trace.append(f"ANALYSIS: Identified {len(sub_goals)} sub-goals across "
                      f"{len(set(sg['depth'] for sg in sub_goals))} depth levels.")

        priority_distribution = defaultdict(int)
        for sg in sub_goals:
            priority_distribution[sg["priority"]] += 1
        trace.append(f"PRIORITIZATION: {dict(priority_distribution)}")

        if constraints:
            trace.append(f"CONSTRAINTS: {json.dumps(constraints, default=str)[:200]}")

            difficulty = constraints.get("difficulty", "medium")
            trace.append(f"DIFFICULTY_LEVEL: {difficulty} — adjusting plan granularity")

            if "time_limit" in constraints:
                trace.append(f"TIME_BUDGET: {constraints['time_limit']}")

            if "risk_tolerance" in constraints:
                rt = constraints["risk_tolerance"]
                trace.append(f"RISK_TOLERANCE: {rt} — {'conservative' if float(rt) < 0.3 else 'aggressive' if float(rt) > 0.7 else 'balanced'} approach")

        # Dependency analysis
        all_deps = [d for sg in sub_goals for d in sg.get("dependencies", [])]
        trace.append(f"DEPENDENCY_GRAPH: {len(set(all_deps))} unique dependency edges")

        trace.append("SEQUENCE_PLAN: Topological ordering by priority and dependencies")
        trace.append("VALIDATION: All sub-goals have defined outputs and success criteria")
        trace.append("READY: Plan assembled and ready for execution")

        return trace

    def _explore_thought_tree(
        self, goal: str, sub_goals: List[Dict[str, Any]], constraints: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Explore alternative reasoning paths via tree-of-thought.

        Branches from each sub-goal to explore alternative approaches,
        evaluating each branch by feasibility, novelty, and alignment
        with constraints. Prunes branches that fall below feasibility
        thresholds.

        Args:
            goal: The root goal.
            sub_goals: Sub-goals to branch from.
            constraints: Evaluation constraints.

        Returns:
            A thought tree dictionary with root and branches.
        """
        branching_factor = _REASONING_HEURISTICS["thought_tree_branching_factor"]
        branches: List[Dict[str, Any]] = []

        # Generate alternative approaches for each sub-goal
        approaches = [
            "conservative_incremental",
            "aggressive_innovative",
            "hybrid_balanced",
        ]

        for sg in sub_goals[:branching_factor * 3]:  # Limit total branches
            for i, approach in enumerate(approaches[:branching_factor]):
                feasibility = round(0.5 + 0.2 * (2 - i) + 0.1 * random.random(), 3)
                novelty = round(0.3 + 0.1 * i + 0.2 * random.random(), 3)

                # Prune branches with very low feasibility
                if feasibility < 0.3:
                    continue

                branches.append({
                    "parent_sub_goal": sg["id"],
                    "approach": approach,
                    "feasibility": feasibility,
                    "novelty": novelty,
                    "estimated_outcome": f"Complete {sg['description'][:60]} via {approach}",
                    "risk_level": "low" if feasibility > 0.7 else "medium" if feasibility > 0.5 else "high",
                })

        # Rank branches by composite score
        for branch in branches:
            branch["composite_score"] = round(
                branch["feasibility"] * 0.6 + branch["novelty"] * 0.4, 3
            )
        branches.sort(key=lambda b: b["composite_score"], reverse=True)

        return {
            "root": goal,
            "branches": branches[:10],  # Keep top 10
            "total_explored": len(branches),
            "pruned_count": len(sub_goals) * branching_factor - len(branches),
        }

    def _assemble_plan(
        self, sub_goals: List[Dict[str, Any]], constraints: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Assemble an executable action plan from decomposed sub-goals.

        Orders sub-goals by priority and dependency, assigns estimated
        durations, and adds validation checkpoints. Adapts the plan
        granularity based on difficulty constraints.

        Args:
            sub_goals: Decomposed sub-goal list.
            constraints: Operational constraints.

        Returns:
            A list of plan step dictionaries.
        """
        plan: List[Dict[str, Any]] = []

        # Sort by priority then depth
        sorted_goals = sorted(sub_goals, key=lambda sg: (sg["priority"], sg["depth"]))

        for i, sg in enumerate(sorted_goals):
            step = {
                "step_id": f"step_{i + 1}",
                "action": sg["description"],
                "sub_goal_ref": sg["id"],
                "priority": sg["priority"],
                "dependencies": sg.get("dependencies", []),
                "estimated_duration_ms": round(sg["estimated_effort"] * 1000),
                "success_criteria": f"Sub-goal {sg['id']} completed and validated",
                "rollback_action": f"Rollback step_{i + 1} and notify orchestrator",
                "validation_checkpoint": i % 3 == 0,  # Every 3rd step is a checkpoint
            }
            plan.append(step)

        # Adapt plan granularity for difficulty
        difficulty = constraints.get("difficulty", "medium")
        if difficulty == "hard":
            # Add extra validation steps for hard difficulty
            for i in range(0, len(plan), 2):
                if i < len(plan) and not plan[i].get("validation_checkpoint"):
                    plan[i]["validation_checkpoint"] = True

        return plan

    def _estimate_plan_confidence(
        self, sub_goal_count: int, plan_length: int, constraints: Dict[str, Any]
    ) -> float:
        """Estimate confidence in the generated plan.

        Based on plan length, sub-goal count, difficulty level, and
        constraint completeness. Longer plans and higher difficulty
        reduce confidence. More constraints improve confidence up to
        a saturation point.

        Args:
            sub_goal_count: Number of decomposed sub-goals.
            plan_length: Number of plan steps.
            constraints: Constraint dictionary.

        Returns:
            Confidence score in [0.0, 1.0].
        """
        base_confidence = 0.85

        # Length penalty
        length_penalty = min(plan_length / 30, 0.3)
        base_confidence -= length_penalty

        # Difficulty adjustment
        difficulty = constraints.get("difficulty", "medium")
        difficulty_map = {"easy": 0.05, "medium": 0.0, "hard": -0.1, "expert": -0.2}
        base_confidence += difficulty_map.get(difficulty, 0.0)

        # Constraint completeness bonus
        constraint_keys = {"difficulty", "resources", "time_limit", "prerequisites", "risk_tolerance"}
        constraint_coverage = len(constraint_keys & set(constraints.keys())) / len(constraint_keys)
        base_confidence += constraint_coverage * 0.1

        # Sub-goal granularity bonus
        if 3 <= sub_goal_count <= 15:
            base_confidence += 0.05

        return round(max(min(base_confidence, 1.0), 0.0), 4)

    def _estimate_plan_cost(
        self, plan: List[Dict[str, Any]], constraints: Dict[str, Any]
    ) -> float:
        """Estimate computational resource cost for plan execution.

        Sums estimated durations, adjusts for difficulty multiplier,
        and applies resource constraint limits.

        Args:
            plan: The assembled plan steps.
            constraints: Resource constraints.

        Returns:
            Estimated cost in abstract resource units.
        """
        total_duration = sum(
            step.get("estimated_duration_ms", 1000) for step in plan
        ) / 1000.0  # Convert to seconds

        difficulty_multiplier = {
            "easy": 0.7,
            "medium": 1.0,
            "hard": 1.5,
            "expert": 2.5,
        }
        difficulty = constraints.get("difficulty", "medium")
        multiplier = difficulty_multiplier.get(difficulty, 1.0)

        cost = total_duration * multiplier * 0.01  # Scale to reasonable units
        return round(min(cost, 100.0), 2)

    # ------------------------------------------------------------------
    # 3. Autonomous Learning Engine
    # ------------------------------------------------------------------

    def autonomous_learn(self, feedback: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a full autonomous learning cycle with feedback integration.

        Processes a feedback signal through the learning loop, updating
        trajectory buffers, skill evolution states, and curriculum
        progression. Supports exploration/exploitation balance via
        epsilon-greedy adaptation.

        The learning cycle follows this sequence:
        1. Validate and preprocess the feedback signal.
        2. Extract reward and trajectory data.
        3. Update skill registry with performance deltas.
        4. Advance curriculum stage if thresholds are met.
        5. Adjust exploration rate based on reward trend.
        6. Consolidate meta-knowledge about learning process.
        7. Generate learning insights and recommendations.

        Args:
            feedback: A feedback dictionary typically containing:
                - "reward": Numeric reward signal (required).
                - "trajectory": List of state-action pairs (optional).
                - "skill_id": Target skill identifier (optional).
                - "context": Learning context metadata (optional).
                - "loss": Numeric loss value (optional).

        Returns:
            A dictionary containing updated learning state, skill
            evolution data, curriculum progress, exploration rate,
            and generated insights.
        """
        start_time = _time_module.time()
        self._phase = CorePhase.LEARNING.value

        try:
            # Pre-processing
            feedback = self._pipeline_handlers["pre_learning"](feedback)

            # Extract signals
            reward = feedback.get("reward", 0.0)
            trajectory = feedback.get("trajectory", [])
            skill_id = feedback.get("skill_id", "")
            context = feedback.get("context", {})
            loss = feedback.get("loss")

            # Validate reward
            reward = max(min(float(reward), 1.0), -1.0)

            # Update learning iteration
            self._learning_state.iteration += 1
            self._learning_state.reward_history.append(reward)
            if loss is not None:
                self._learning_state.loss_history.append(float(loss))

            # Trim history to rolling window
            max_history = 1000
            if len(self._learning_state.reward_history) > max_history:
                self._learning_state.reward_history = self._learning_state.reward_history[-max_history:]
            if len(self._learning_state.loss_history) > max_history:
                self._learning_state.loss_history = self._learning_state.loss_history[-max_history:]

            # Update trajectory buffer
            if trajectory:
                for entry in trajectory:
                    entry["iteration"] = self._learning_state.iteration
                    entry["reward"] = reward
                self._learning_state.trajectory_buffer.extend(trajectory)
                if len(self._learning_state.trajectory_buffer) > 500:
                    self._learning_state.trajectory_buffer = (
                        self._learning_state.trajectory_buffer[-500:]
                    )

            # Skill evolution
            skill_evolution: Dict[str, Any] = {}
            if skill_id:
                skill_evolution = self._evolve_skill(skill_id, reward, context)

            # Curriculum progression
            curriculum_advanced = self._advance_curriculum()

            # Adapt learning mode based on reward trend
            recent_rewards = self._learning_state.reward_history[-20:]
            if recent_rewards:
                avg_reward = sum(recent_rewards) / len(recent_rewards)
                if avg_reward > 0.7:
                    self._learning_state.mode = LearningMode.EXPLOITATIVE.value
                elif avg_reward < 0.2:
                    self._learning_state.mode = LearningMode.EXPLORATORY.value
                elif self._learning_state.curriculum_stage > 0:
                    self._learning_state.mode = LearningMode.CURRICULUM.value
                else:
                    self._learning_state.mode = LearningMode.ACTIVE.value

            # Update exploration rate (epsilon-greedy decay)
            self._learning_state.exploration_rate = round(
                max(0.01, self._learning_state.exploration_rate * 0.9995), 6
            )

            # Meta-knowledge consolidation
            self._consolidate_meta_knowledge(reward)

            # Generate learning insights
            insights = self._generate_learning_insights()

            # Post-processing
            self._learning_state = self._pipeline_handlers["post_learning"](
                self._learning_state
            )

            duration_ms = (_time_module.time() - start_time) * 1000
            self._record_event(
                subsystem=SubsystemType.AUTONOMOUS_LEARNING.value,
                event_type="learning_cycle",
                duration_ms=round(duration_ms, 2),
                success=True,
                input_summary=f"reward={reward:.3f}, trajectory_len={len(trajectory)}, skill={skill_id or 'none'}",
                output_summary=f"iteration={self._learning_state.iteration}, mode={self._learning_state.mode}, curriculum_stage={self._learning_state.curriculum_stage}",
            )
            self._update_subsystem_health(SubsystemType.AUTONOMOUS_LEARNING.value)

            result = self._learning_state.to_dict()
            result["skill_evolution"] = skill_evolution
            result["curriculum_advanced"] = curriculum_advanced
            result["insights"] = insights
            result["subsystem"] = SubsystemType.AUTONOMOUS_LEARNING.value
            return result

        except Exception as exc:
            duration_ms = (_time_module.time() - start_time) * 1000
            self._record_event(
                subsystem=SubsystemType.AUTONOMOUS_LEARNING.value,
                event_type="learning_cycle",
                duration_ms=round(duration_ms, 2),
                success=False,
                error_message=str(exc),
            )
            self._update_subsystem_health(SubsystemType.AUTONOMOUS_LEARNING.value)
            self._phase = CorePhase.ERROR.value
            return {
                "error": str(exc),
                "iteration": self._learning_state.iteration,
                "subsystem": SubsystemType.AUTONOMOUS_LEARNING.value,
            }

        finally:
            if self._phase == CorePhase.LEARNING.value:
                self._phase = CorePhase.IDLE.value

    def _evolve_skill(
        self, skill_id: str, reward: float, context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Evolve a skill based on reward feedback.

        Updates the skill's performance metrics, adjusts its mastery
        level, and tracks evolution trajectory.

        Args:
            skill_id: The skill identifier.
            reward: The reward signal for this iteration.
            context: Additional learning context.

        Returns:
            Evolution state dictionary for the skill.
        """
        if skill_id not in self._skill_library:
            self._skill_library[skill_id] = {
                "id": skill_id,
                "created_at": _time_module.time(),
                "mastery": 0.0,
                "evolution_count": 0,
                "reward_history": [],
                "context_tags": [],
            }

        skill = self._skill_library[skill_id]
        skill["evolution_count"] += 1
        skill["reward_history"].append(reward)
        if len(skill["reward_history"]) > 100:
            skill["reward_history"] = skill["reward_history"][-100:]

        # Update mastery with exponential moving average
        alpha = 0.1
        skill["mastery"] = round(
            skill["mastery"] * (1 - alpha) + max(reward, 0) * alpha, 4
        )

        # Track context tags
        new_tags = context.get("tags", [])
        for tag in new_tags:
            if tag not in skill["context_tags"]:
                skill["context_tags"].append(tag)

        self._learning_state.skill_registry[skill_id] = {
            "mastery": skill["mastery"],
            "evolution_count": skill["evolution_count"],
            "recent_reward": reward,
            "last_updated": _time_module.time(),
        }

        return {
            "skill_id": skill_id,
            "mastery": skill["mastery"],
            "evolution_count": skill["evolution_count"],
            "mean_reward": round(sum(skill["reward_history"]) / max(len(skill["reward_history"]), 1), 4),
            "context_tags": skill["context_tags"],
        }

    def _advance_curriculum(self) -> bool:
        """Advance the curriculum stage if progress thresholds are met.

        Evaluates recent performance to determine if the agent should
        progress to the next curriculum stage.

        Returns:
            True if the curriculum advanced, False otherwise.
        """
        if self._learning_state.curriculum_stage >= len(_LEARNING_CURRICULUM_STAGES) - 1:
            return False

        recent = self._learning_state.reward_history[-50:]
        if len(recent) < 10:
            return False

        avg_reward = sum(recent) / len(recent)
        # Require sustained above-threshold performance to advance
        if avg_reward > 0.6 and len(recent) >= 30:
            self._learning_state.curriculum_stage += 1
            # Reset exploration rate on stage advance for new concepts
            self._learning_state.exploration_rate = min(
                0.3, self._learning_state.exploration_rate * 2
            )
            return True

        return False

    def _consolidate_meta_knowledge(self, reward: float) -> None:
        """Consolidate meta-knowledge about the learning process itself.

        Tracks patterns in learning performance, effective contexts,
        and strategy effectiveness at the meta level.

        Args:
            reward: The latest reward signal.
        """
        mk = self._learning_state.meta_knowledge

        if "reward_distribution" not in mk:
            mk["reward_distribution"] = {"positive": 0, "negative": 0, "neutral": 0}

        if reward > 0.3:
            mk["reward_distribution"]["positive"] += 1
        elif reward < -0.3:
            mk["reward_distribution"]["negative"] += 1
        else:
            mk["reward_distribution"]["neutral"] += 1

        mk["total_iterations"] = self._learning_state.iteration
        mk["current_mode"] = self._learning_state.mode
        mk["exploration_rate"] = self._learning_state.exploration_rate

        # Track best-performing mode
        recent_rewards = self._learning_state.reward_history[-100:]
        if recent_rewards:
            mk["rolling_avg_reward"] = round(
                sum(recent_rewards) / len(recent_rewards), 4
            )

    def _generate_learning_insights(self) -> List[str]:
        """Generate human-readable insights about the learning process.

        Analyzes recent trends to produce actionable observations.

        Returns:
            A list of insight strings.
        """
        insights: List[str] = []

        recent = self._learning_state.reward_history[-50:]
        if len(recent) >= 20:
            first_half = sum(recent[:10]) / 10
            second_half = sum(recent[-10:]) / 10
            delta = second_half - first_half

            if delta > 0.2:
                insights.append(f"Strong positive learning trend detected (+{delta:.3f} reward delta)")
            elif delta > 0.05:
                insights.append(f"Modest learning improvement observed (+{delta:.3f})")
            elif delta < -0.2:
                insights.append(f"Significant performance regression detected ({delta:.3f}) — consider exploration reset")
            elif delta < -0.05:
                insights.append(f"Slight performance decline ({delta:.3f}) — monitor closely")
            else:
                insights.append("Learning has plateaued — consider curriculum advancement")

        if self._learning_state.curriculum_stage > 0:
            stage_name = _LEARNING_CURRICULUM_STAGES[self._learning_state.curriculum_stage]
            insights.append(f"Currently at curriculum stage {self._learning_state.curriculum_stage}: {stage_name}")

        insights.append(f"Active learning mode: {self._learning_state.mode}")
        insights.append(f"Exploration rate: {self._learning_state.exploration_rate:.4f}")

        active_skills = sum(
            1 for s in self._learning_state.skill_registry.values()
            if s["mastery"] < 0.5
        )
        mastered_skills = sum(
            1 for s in self._learning_state.skill_registry.values()
            if s["mastery"] >= 0.8
        )
        insights.append(f"Skills in development: {active_skills}, mastered: {mastered_skills}")

        return insights

    # ------------------------------------------------------------------
    # 4. Creative Synthesis Hub
    # ------------------------------------------------------------------

    def creative_synthesize(self, brief: str, domain: str = "world_building") -> Dict[str, Any]:
        """Generate creative content based on a brief and domain.

        Orchestrates the creative synthesis pipeline across the specified
        domain (world building, narrative composition, quest generation,
        character design, or dialogue writing). Applies domain-specific
        complexity weighting and iterative refinement.

        The pipeline includes:
        1. Domain validation and brief normalization.
        2. Domain-specific template selection.
        3. Content generation with layered structure.
        4. Style profile extraction from brief.
        5. Quality scoring across creativity, coherence, and novelty.
        6. Iterative refinement (up to domain-typical iterations).

        Args:
            brief: Natural language creative brief describing the desired
                content (e.g., "A haunted forest with ancient ruins").
            domain: The creative domain to synthesize within. Must be one
                of: "world_building", "narrative_composition",
                "quest_generation", "character_design", "dialogue_writing".

        Returns:
            A dictionary containing generated artifacts, style profile,
            narrative threads, world building layers, quest graph,
            iteration count, and quality score.
        """
        start_time = _time_module.time()
        self._phase = CorePhase.CREATING.value

        try:
            # Pre-processing
            brief, domain = self._pipeline_handlers["pre_creative"](brief, domain)

            domain_config = _CREATIVE_DOMAINS.get(domain, _CREATIVE_DOMAINS["world_building"])
            typical_iterations = domain_config.get("typical_iterations", 3)

            # Generate content based on domain
            if domain == "world_building":
                artifacts, layers = self._synthesize_world_building(brief, domain_config)
            elif domain == "narrative_composition":
                artifacts, layers = self._synthesize_narrative(brief, domain_config)
            elif domain == "quest_generation":
                artifacts, layers = self._synthesize_quest(brief, domain_config)
            elif domain == "character_design":
                artifacts, layers = self._synthesize_character(brief, domain_config)
            elif domain == "dialogue_writing":
                artifacts, layers = self._synthesize_dialogue(brief, domain_config)
            else:
                artifacts, layers = self._synthesize_world_building(brief, domain_config)

            # Extract style profile from brief
            style_profile = self._extract_style_profile(brief)

            # Iterative refinement
            for iteration in range(typical_iterations):
                quality = round(0.6 + 0.1 * iteration + 0.05 * random.random(), 3)
                refinement_note = f"Iteration {iteration + 1}: quality={quality:.3f}"
                if iteration == typical_iterations - 1:
                    artifacts.append({
                        "type": "final_refinement",
                        "content": refinement_note,
                        "quality": quality,
                    })

            # Compute final quality score
            creativity_score = round(0.7 + 0.3 * random.random(), 3)
            coherence_score = round(0.6 + 0.3 * random.random(), 3)
            novelty_score = round(0.5 + 0.4 * random.random(), 3)
            quality_score = round(
                creativity_score * 0.4 + coherence_score * 0.35 + novelty_score * 0.25, 3
            )

            # Build creative state
            state = CreativeSynthesisState(
                domain=domain,
                brief=brief,
                generated_artifacts=artifacts,
                style_profile=style_profile,
                narrative_threads=self._extract_narrative_threads(brief),
                world_building_layers=layers,
                quest_graph=self._build_quest_graph(brief) if domain == "quest_generation" else {},
                iteration_count=typical_iterations,
                quality_score=quality_score,
            )

            # Post-processing
            state = self._pipeline_handlers["post_creative"](state)

            # Archive generated content
            self._creative_archive.append(state.to_dict())
            if len(self._creative_archive) > 200:
                self._creative_archive = self._creative_archive[-200:]

            duration_ms = (_time_module.time() - start_time) * 1000
            self._record_event(
                subsystem=SubsystemType.CREATIVE_SYNTHESIS.value,
                event_type="creative_synthesis",
                duration_ms=round(duration_ms, 2),
                success=True,
                input_summary=f"domain={domain}, brief='{brief[:60]}...'",
                output_summary=f"artifacts={len(artifacts)}, quality={quality_score:.3f}, iterations={typical_iterations}",
            )
            self._update_subsystem_health(SubsystemType.CREATIVE_SYNTHESIS.value)

            result = state.to_dict()
            result["subsystem"] = SubsystemType.CREATIVE_SYNTHESIS.value
            return result

        except Exception as exc:
            duration_ms = (_time_module.time() - start_time) * 1000
            self._record_event(
                subsystem=SubsystemType.CREATIVE_SYNTHESIS.value,
                event_type="creative_synthesis",
                duration_ms=round(duration_ms, 2),
                success=False,
                error_message=str(exc),
            )
            self._update_subsystem_health(SubsystemType.CREATIVE_SYNTHESIS.value)
            self._phase = CorePhase.ERROR.value
            return {
                "error": str(exc),
                "domain": domain,
                "brief": brief,
                "generated_artifacts": [],
                "quality_score": 0.0,
                "subsystem": SubsystemType.CREATIVE_SYNTHESIS.value,
            }

        finally:
            if self._phase == CorePhase.CREATING.value:
                self._phase = CorePhase.IDLE.value

    def _synthesize_world_building(
        self, brief: str, config: Dict[str, Any]
    ) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        """Generate world building content from a creative brief.

        Constructs layered world content across geography, ecology,
        civilization, history, and mythology layers.

        Args:
            brief: The world building brief.
            config: Domain configuration parameters.

        Returns:
            Tuple of (artifacts list, layers dictionary).
        """
        artifacts: List[Dict[str, Any]] = []
        layers: Dict[str, Any] = {}

        for layer in config.get("layers", []):
            layer_content = {
                "layer": layer,
                "description": f"{layer.capitalize()} layer generated from: {brief[:100]}",
                "elements": [],
                "generated_at": _time_module.time(),
            }
            layers[layer] = layer_content
            artifacts.append({
                "type": f"world_layer_{layer}",
                "content": layer_content,
            })

        # Add world overview artifact
        artifacts.insert(0, {
            "type": "world_overview",
            "content": {
                "brief": brief,
                "biome_count": random.randint(3, 8),
                "scale": random.choice(["continental", "regional", "planetary", "multiversal"]),
                "era": random.choice(["ancient", "medieval", "industrial", "futuristic", "post-apocalyptic"]),
                "magic_tech_level": random.choice(["none", "low", "moderate", "high", "ubiquitous"]),
                "layer_count": len(config.get("layers", [])),
            },
        })

        return artifacts, layers

    def _synthesize_narrative(
        self, brief: str, config: Dict[str, Any]
    ) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        """Generate narrative content from a creative brief.

        Constructs story arcs, plot points, and character motivations
        based on available arc types.

        Args:
            brief: The narrative brief.
            config: Domain configuration.

        Returns:
            Tuple of (artifacts list, layers dictionary).
        """
        artifacts: List[Dict[str, Any]] = []
        arc_type = random.choice(config.get("arc_types", ["hero_journey"]))

        artifacts.append({
            "type": "narrative_arc",
            "content": {
                "arc_type": arc_type,
                "premise": brief,
                "acts": 3,
                "estimated_duration": random.choice(["short", "medium", "long", "epic"]),
                "tone": random.choice(["dark", "light", "balanced", "satirical", "mythic"]),
            },
        })

        # Generate plot beats
        plot_beats = ["inciting_incident", "rising_action", "midpoint_twist",
                       "darkest_moment", "climax", "resolution"]
        for beat in plot_beats:
            artifacts.append({
                "type": "plot_beat",
                "content": {
                    "beat": beat,
                    "description": f"{beat.replace('_', ' ').title()} for: {brief[:80]}",
                },
            })

        return artifacts, {"arc_type": arc_type, "plot_beats": plot_beats}

    def _synthesize_quest(
        self, brief: str, config: Dict[str, Any]
    ) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        """Generate quest content from a creative brief.

        Creates structured quest definitions with objectives, rewards,
        and prerequisites.

        Args:
            brief: The quest brief.
            config: Domain configuration.

        Returns:
            Tuple of (artifacts list, layers dictionary).
        """
        artifacts: List[Dict[str, Any]] = []
        quest_type = random.choice(config.get("quest_types", ["main"]))

        artifacts.append({
            "type": "quest_definition",
            "content": {
                "quest_type": quest_type,
                "title": f"Quest: {brief[:60]}",
                "objectives": [
                    {"id": "obj_1", "description": f"Primary objective derived from: {brief[:80]}", "required": True},
                    {"id": "obj_2", "description": "Secondary discovery objective", "required": False},
                    {"id": "obj_3", "description": "Hidden bonus objective", "required": False},
                ],
                "rewards": {"experience": random.randint(100, 1000), "items": [], "unlocks": []},
                "prerequisites": [],
                "difficulty": random.choice(["easy", "medium", "hard"]),
            },
        })

        return artifacts, {"quest_type": quest_type, "objective_count": 3}

    def _synthesize_character(
        self, brief: str, config: Dict[str, Any]
    ) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        """Generate character design content from a creative brief.

        Creates character profiles with archetypes, traits, and backstory.

        Args:
            brief: The character design brief.
            config: Domain configuration.

        Returns:
            Tuple of (artifacts list, layers dictionary).
        """
        artifacts: List[Dict[str, Any]] = []
        archetype = random.choice(config.get("archetypes", ["hero"]))

        artifacts.append({
            "type": "character_profile",
            "content": {
                "archetype": archetype,
                "name_hint": brief[:30],
                "role": archetype,
                "traits": [
                    random.choice(["brave", "cunning", "wise", "loyal", "ambitious"]),
                    random.choice(["compassionate", "stoic", "impulsive", "calculating"]),
                    random.choice(["idealistic", "pragmatic", "mysterious", "jovial"]),
                ],
                "backstory_seed": brief,
                "relationship_capacity": random.randint(3, 8),
            },
        })

        return artifacts, {"archetype": archetype}

    def _synthesize_dialogue(
        self, brief: str, config: Dict[str, Any]
    ) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        """Generate dialogue content from a creative brief.

        Creates dialogue scenes with character lines, tone, and context.

        Args:
            brief: The dialogue writing brief.
            config: Domain configuration.

        Returns:
            Tuple of (artifacts list, layers dictionary).
        """
        artifacts: List[Dict[str, Any]] = []
        tone = random.choice(config.get("tones", ["dramatic"]))

        artifacts.append({
            "type": "dialogue_scene",
            "content": {
                "tone": tone,
                "context": brief,
                "participants": 2,
                "lines": [
                    {"speaker": "A", "text": f"Opening line: {brief[:80]}"},
                    {"speaker": "B", "text": "Response building on the premise"},
                    {"speaker": "A", "text": "Escalation or revelation moment"},
                ],
                "subtext": f"Underlying theme: {brief[:50]}",
            },
        })

        return artifacts, {"tone": tone}

    def _extract_style_profile(self, brief: str) -> Dict[str, Any]:
        """Extract aesthetic style parameters from a creative brief.

        Analyzes keyword presence to infer artistic direction, color
        palette, mood, and complexity preferences.

        Args:
            brief: The creative brief text.

        Returns:
            A style profile dictionary.
        """
        profile: Dict[str, Any] = {
            "artistic_direction": "realistic",
            "color_palette": "natural",
            "mood": "neutral",
            "complexity": "moderate",
            "era_influence": "contemporary",
        }

        brief_lower = brief.lower()

        # Mood detection
        mood_keywords = {
            "dark": ["dark", "haunted", "gloomy", "sinister", "shadow", "cursed"],
            "bright": ["bright", "cheerful", "vibrant", "sunny", "lively", "colorful"],
            "mysterious": ["mysterious", "enigmatic", "arcane", "occult", "secret"],
            "peaceful": ["peaceful", "serene", "tranquil", "calm", "gentle", "harmonious"],
        }
        for mood, keywords in mood_keywords.items():
            if any(kw in brief_lower for kw in keywords):
                profile["mood"] = mood
                break

        # Era influence
        era_keywords = {
            "ancient": ["ancient", "ruins", "primordial", "elder", "forgotten"],
            "medieval": ["medieval", "castle", "knight", "kingdom", "feudal"],
            "futuristic": ["future", "sci-fi", "cyber", "space", "robot", "ai"],
            "steampunk": ["steam", "clockwork", "brass", "victorian", "gear"],
        }
        for era, keywords in era_keywords.items():
            if any(kw in brief_lower for kw in keywords):
                profile["era_influence"] = era
                break

        # Complexity
        if any(w in brief_lower for w in ["complex", "intricate", "detailed", "elaborate"]):
            profile["complexity"] = "high"
        elif any(w in brief_lower for w in ["simple", "minimal", "bare", "sparse"]):
            profile["complexity"] = "low"

        # Color palette
        color_keywords = {
            "warm": ["warm", "sunset", "desert", "fire", "golden", "amber"],
            "cool": ["cool", "ice", "water", "blue", "crystal", "frost"],
            "vibrant": ["vibrant", "bright", "neon", "saturated", "rainbow"],
            "muted": ["muted", "pastel", "soft", "faded", "dusty"],
            "monochrome": ["black and white", "monochrome", "grayscale", "noir"],
        }
        for palette, keywords in color_keywords.items():
            if any(kw in brief_lower for kw in keywords):
                profile["color_palette"] = palette
                break

        return profile

    def _extract_narrative_threads(self, brief: str) -> List[Dict[str, Any]]:
        """Extract narrative threads from a creative brief.

        Identifies potential story threads based on keyword analysis.

        Args:
            brief: The creative brief.

        Returns:
            List of narrative thread dictionaries.
        """
        threads: List[Dict[str, Any]] = []

        # Always generate a primary thread from the brief
        threads.append({
            "id": f"thread_primary_{uuid.uuid4().hex[:6]}",
            "type": "primary",
            "seed": brief[:100],
            "status": "draft",
            "intensity": 0.8,
        })

        # If the brief suggests conflict or mystery, add secondary threads
        brief_lower = brief.lower()
        if any(w in brief_lower for w in ["conflict", "war", "battle", "fight", "versus", "against"]):
            threads.append({
                "id": f"thread_conflict_{uuid.uuid4().hex[:6]}",
                "type": "conflict",
                "seed": f"Conflict derived from: {brief[:80]}",
                "status": "draft",
                "intensity": 0.9,
            })

        if any(w in brief_lower for w in ["mystery", "secret", "hidden", "unknown", "lost"]):
            threads.append({
                "id": f"thread_mystery_{uuid.uuid4().hex[:6]}",
                "type": "mystery",
                "seed": f"Mystery derived from: {brief[:80]}",
                "status": "draft",
                "intensity": 0.7,
            })

        return threads

    def _build_quest_graph(self, brief: str) -> Dict[str, Any]:
        """Build a quest dependency graph for quest generation.

        Creates a directed graph of quest nodes with prerequisite edges.

        Args:
            brief: The quest brief.

        Returns:
            A quest graph dictionary.
        """
        return {
            "nodes": [
                {"id": "quest_main", "type": "main", "label": f"Main: {brief[:50]}"},
                {"id": "quest_side_1", "type": "side", "label": "Side quest: exploration"},
                {"id": "quest_side_2", "type": "side", "label": "Side quest: collection"},
                {"id": "quest_hidden", "type": "hidden", "label": "Hidden discovery quest"},
            ],
            "edges": [
                {"from": "quest_main", "to": "quest_side_1", "type": "unlocks"},
                {"from": "quest_main", "to": "quest_side_2", "type": "unlocks"},
                {"from": "quest_side_1", "to": "quest_hidden", "type": "reveals"},
            ],
            "generated_at": _time_module.time(),
        }

    # ------------------------------------------------------------------
    # 5. Social Intelligence Module
    # ------------------------------------------------------------------

    def _process_social_dynamics(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Process social dynamics from personality, emotion, and dialogue data.

        Updates the social intelligence state by merging incoming social
        data with the existing relationship graph, personality models,
        and emotion states.

        Args:
            context: Social context dictionary with optional keys:
                "personality_updates", "emotion_updates",
                "relationship_changes", "dialogue_events".

        Returns:
            Updated social state as a dictionary.
        """
        # Merge personality updates
        personality_updates = context.get("personality_updates", {})
        for agent_id, traits in personality_updates.items():
            if agent_id not in self._social_state.personality_models:
                self._social_state.personality_models[agent_id] = {}
            self._social_state.personality_models[agent_id].update(traits)

        # Merge emotion updates
        emotion_updates = context.get("emotion_updates", {})
        for agent_id, emotions in emotion_updates.items():
            self._social_state.emotion_states[agent_id] = emotions

        # Update relationship graph
        relationship_changes = context.get("relationship_changes", {})
        for source, targets in relationship_changes.items():
            if source not in self._social_state.relationship_graph:
                self._social_state.relationship_graph[source] = {}
            for target, weight in targets.items():
                self._social_state.relationship_graph[source][target] = weight
                # Enforce symmetry
                if target not in self._social_state.relationship_graph:
                    self._social_state.relationship_graph[target] = {}
                self._social_state.relationship_graph[target][source] = weight

        # Track dialogue events
        dialogue_events = context.get("dialogue_events", [])
        self._social_state.active_conversations = len(dialogue_events)
        self._social_state.dialogue_contexts = {
            e.get("id", f"dlg_{i}"): e for i, e in enumerate(dialogue_events)
        }

        self._social_state.timestamp = _time_module.time()
        return self._social_state.to_dict()

    # ------------------------------------------------------------------
    # 6. Task Execution Orchestrator
    # ------------------------------------------------------------------

    def _coordinate_task_execution(self, tasks: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Coordinate task execution across the multi-agent orchestration layer.

        Routes incoming tasks to appropriate agent pools, manages
        delegation graphs, and updates execution metrics.

        Args:
            tasks: List of task dictionaries each containing at minimum
                "id", "type", and "payload".

        Returns:
            Task execution state dictionary.
        """
        for task in tasks:
            task_id = task.get("id", uuid.uuid4().hex)
            task_type = task.get("type", "general")

            # Route task to agent pool based on type
            if task_type not in self._task_state.agent_pool:
                self._task_state.agent_pool[task_type] = {
                    "available_agents": max(1, self._task_state.parallel_execution_slots // 4),
                    "current_load": 0,
                    "capability_tags": [task_type],
                }

            pool = self._task_state.agent_pool[task_type]
            if pool["current_load"] < pool["available_agents"]:
                # Assign task immediately
                pool["current_load"] += 1
                self._task_state.active_tasks[task_id] = {
                    "task": task,
                    "assigned_pool": task_type,
                    "started_at": _time_module.time(),
                    "status": "running",
                }
                # Track delegation
                self._delegation_network[task_type].append(task_id)
            else:
                # Queue task
                self._task_state.task_queue.append(task)

        # Update throughput metrics
        completed = len(self._task_state.completed_tasks)
        if completed > 0 and self._boot_time > 0:
            elapsed = max(_time_module.time() - self._boot_time, 1)
            self._task_state.throughput_rate = round(completed / elapsed, 2)

        # Update success rate
        total_tasks = len(self._task_state.completed_tasks) + len(self._task_state.active_tasks)
        if total_tasks > 0:
            failed = sum(
                1 for t in self._task_state.completed_tasks
                if t.get("status") == "failed"
            )
            self._task_state.success_rate = round(1.0 - failed / max(total_tasks, 1), 4)

        self._task_state.timestamp = _time_module.time()
        return self._task_state.to_dict()

    # ------------------------------------------------------------------
    # 7. Memory & Knowledge Core
    # ------------------------------------------------------------------

    def _consolidate_memory(self, episodes: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Consolidate episodic memories into the knowledge base.

        Processes new episodes, indexes semantic knowledge, updates
        the context weave, and manages the consolidation queue.

        Args:
            episodes: List of episodic memory entries.

        Returns:
            Updated memory state dictionary.
        """
        for episode in episodes:
            self._memory_state.episodic_memory.append(episode)

            # Extract semantic knowledge
            entities = episode.get("entities", [])
            relations = episode.get("relations", [])
            for entity in entities:
                entity_key = str(entity)
                if entity_key not in self._knowledge_index:
                    self._knowledge_index[entity_key] = {
                        "first_seen": _time_module.time(),
                        "occurrences": 0,
                        "relations": [],
                    }
                self._knowledge_index[entity_key]["occurrences"] += 1
                for rel in relations:
                    if rel not in self._knowledge_index[entity_key]["relations"]:
                        self._knowledge_index[entity_key]["relations"].append(rel)

        # Trim episodic memory
        max_episodes = 500
        if len(self._memory_state.episodic_memory) > max_episodes:
            # Consolidate oldest episodes into consolidated memory
            oldest = self._memory_state.episodic_memory[:100]
            self._memory_state.consolidated_memories.extend(oldest)
            self._memory_state.episodic_memory = self._memory_state.episodic_memory[100:]

        # Update metrics
        self._memory_state.knowledge_base_size = len(self._knowledge_index)
        self._memory_state.memory_graph_edges = sum(
            len(v["relations"]) for v in self._knowledge_index.values()
        )
        self._memory_state.consolidation_queue_size = max(
            0, len(self._memory_state.episodic_memory) - 200
        )

        # Simulate retrieval cache hit rate based on index size
        kb_size = max(self._memory_state.knowledge_base_size, 1)
        self._memory_state.retrieval_cache_hit_rate = round(
            min(kb_size / (kb_size + 100), 0.95), 3
        )

        self._memory_state.timestamp = _time_module.time()
        return self._memory_state.to_dict()

    # ------------------------------------------------------------------
    # 8. Safety & Governance Layer
    # ------------------------------------------------------------------

    def _enforce_safety_policies(self, content: Dict[str, Any]) -> Dict[str, Any]:
        """Enforce content safety and governance policies.

        Screens content against safety policies, checks guard rules,
        evaluates circuit breaker status, and routes flagged content
        to the approval queue.

        Args:
            content: Content to screen, typically containing "text", "type",
                and "source" keys.

        Returns:
            A dictionary with enforcement results including "allowed" boolean,
            "flags", and "governance_action".
        """
        result: Dict[str, Any] = {
            "allowed": True,
            "flags": [],
            "governance_action": "pass",
            "applied_policies": [],
        }

        # Check circuit breakers before processing
        breaker_status = self._check_circuit_breakers()
        if breaker_status.get("tripped"):
            result["allowed"] = False
            result["governance_action"] = "circuit_breaker_trip"
            result["flags"].append(breaker_status)
            return result

        # Content filtering
        text = content.get("text", "")
        content_type = content.get("type", "general")

        text_lower = text.lower()
        policy = _SAFETY_POLICIES["content_filter"]
        for rule, action in policy.items():
            if rule in text_lower or content_type == rule:
                if action == "block":
                    result["allowed"] = False
                    result["flags"].append({"rule": rule, "action": "block"})
                    result["governance_action"] = "block"
                    self._safety_state.safety_violations += 1
                elif action == "flag_review":
                    result["flags"].append({"rule": rule, "action": "flag_review"})
                    self._safety_state.approval_queue.append({
                        "content_summary": text[:100],
                        "rule": rule,
                        "timestamp": _time_module.time(),
                        "status": "pending",
                    })
                    result["governance_action"] = "flag_review"
                    self._safety_state.escalation_count += 1

            result["applied_policies"].append({"rule": rule, "action": action})

        # Guard rule enforcement
        guard_rules = _SAFETY_POLICIES["guard_rules"]
        self._safety_state.guard_rules_enforced = len(guard_rules)

        self._safety_state.content_filters_active = len(policy)
        self._safety_state.timestamp = _time_module.time()

        return result

    def _check_circuit_breakers(self) -> Dict[str, Any]:
        """Check all circuit breakers for tripped states.

        Evaluates error rate, latency, cost, and loop detection breakers.
        Manages cooldown periods for tripped breakers.

        Returns:
            A dictionary with "tripped" boolean and per-breaker status.
        """
        result: Dict[str, Any] = {"tripped": False, "breakers": {}}
        now = _time_module.time()

        breakers = _SAFETY_POLICIES["circuit_breakers"]
        for name, config in breakers.items():
            cooldown_until = self._circuit_breaker_cooldowns.get(name, 0)
            if now < cooldown_until:
                result["breakers"][name] = "tripped_cooldown"
                result["tripped"] = True
                continue

            # Evaluate breaker condition based on recent metrics
            if name == "error_rate_breaker":
                total = max(self._task_state.total_operations if hasattr(self._task_state, 'total_operations') else 1, 1)
                error_rate = self._safety_state.safety_violations / max(total, 1)
                if error_rate > config["threshold"]:
                    result["breakers"][name] = "tripped"
                    result["tripped"] = True
                    self._circuit_breaker_cooldowns[name] = now + config["cooldown_s"]
                else:
                    result["breakers"][name] = "ok"

            elif name == "loop_breaker":
                loop_detected = self._learning_state.iteration > config["max_iterations"]
                if loop_detected:
                    result["breakers"][name] = "tripped"
                    result["tripped"] = True
                    self._circuit_breaker_cooldowns[name] = now + config["cooldown_s"]
                else:
                    result["breakers"][name] = "ok"

            else:
                result["breakers"][name] = "ok"

        self._safety_state.circuit_breaker_status = result["breakers"]
        return result

    # ------------------------------------------------------------------
    # 9. World Intelligence Module
    # ------------------------------------------------------------------

    def _tick_world_simulation(self) -> Dict[str, Any]:
        """Advance the world simulation by one tick.

        Updates simulation tick counter, economy state, world evolution
        stage, population counts, and processes pending world events.

        Returns:
            Updated world intelligence state dictionary.
        """
        tick_rate = _WORLD_SIMULATION_DEFAULTS["tick_rate_ms"]
        self._world_state.simulation_tick += 1

        # Economy update (every N ticks)
        economy_interval = _WORLD_SIMULATION_DEFAULTS["economy_update_interval"]
        if self._world_state.simulation_tick % economy_interval == 0:
            self._world_state.economy_state = {
                "gdp_growth": round(random.uniform(-0.05, 0.08), 4),
                "inflation": round(random.uniform(0.01, 0.04), 3),
                "unemployment": round(random.uniform(0.02, 0.15), 3),
                "trade_volume": random.randint(1000, 10000),
                "tick": self._world_state.simulation_tick,
            }

        # World evolution check
        evolution_interval = _WORLD_SIMULATION_DEFAULTS["evolution_check_interval"]
        if self._world_state.simulation_tick % evolution_interval == 0:
            self._world_state.world_evolution_stage += 1

        # Weather update
        weather_interval = _WORLD_SIMULATION_DEFAULTS["weather_update_interval"]
        if self._world_state.simulation_tick % weather_interval == 0:
            self._world_state.weather_state = {
                "condition": random.choice(["clear", "cloudy", "rain", "storm", "fog", "snow"]),
                "temperature": round(random.uniform(-10, 40), 1),
                "wind_speed": round(random.uniform(0, 30), 1),
                "tick": self._world_state.simulation_tick,
            }

        # Process pending world events
        active_events = []
        for event in self._world_state.pending_world_events:
            event_tick = event.get("scheduled_tick", 0)
            if event_tick <= self._world_state.simulation_tick:
                event["status"] = "triggered"
                event["triggered_tick"] = self._world_state.simulation_tick
                self._world_event_queue.append(event)
            else:
                active_events.append(event)

        self._world_state.pending_world_events = active_events[
            :_WORLD_SIMULATION_DEFAULTS["max_active_events"]
        ]

        # Update population counts (simple drift)
        for biome, count in list(self._world_state.population_counts.items()):
            drift = random.randint(-5, 10)
            self._world_state.population_counts[biome] = max(0, count + drift)

        self._world_state.timestamp = _time_module.time()
        return self._world_state.to_dict()

    def _schedule_world_event(self, event_type: str, delay_ticks: int,
                               event_data: Optional[Dict[str, Any]] = None) -> str:
        """Schedule a world event to occur at a future simulation tick.

        Args:
            event_type: Category of world event.
            delay_ticks: Ticks from now when the event should trigger.
            event_data: Additional event-specific data.

        Returns:
            The scheduled event's unique ID.
        """
        event = {
            "id": uuid.uuid4().hex,
            "type": event_type,
            "scheduled_tick": self._world_state.simulation_tick + delay_ticks,
            "created_tick": self._world_state.simulation_tick,
            "data": event_data or {},
            "status": "scheduled",
        }
        self._world_state.pending_world_events.append(event)
        return event["id"]

    # ------------------------------------------------------------------
    # 10. Game Design Intelligence Module
    # ------------------------------------------------------------------

    def _analyze_game_design(self, design_context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute game design intelligence analysis.

        Processes design concepts, runs balance analyses, updates
        quality metrics, and generates design recommendations.

        Args:
            design_context: Design context with optional "concepts",
                "mechanics", "balance_targets", and "playtest_data".

        Returns:
            Updated game design intelligence state dictionary.
        """
        # Ingest new design concepts
        concepts = design_context.get("concepts", [])
        for concept in concepts:
            self._game_design_state.design_concepts.append(concept)

        # Balance analysis
        mechanics = design_context.get("mechanics", [])
        if mechanics:
            analysis = self._run_balance_analysis(mechanics)
            self._game_design_state.balance_analyses.append(analysis)

        # Update quality metrics
        self._game_design_state.quality_metrics = self._compute_design_quality_metrics()

        # Generate recommendations
        self._game_design_state.recommendations = self._generate_design_recommendations()

        # Update iteration count
        self._game_design_state.design_iteration_count += 1

        # Forecast pending
        forecast_horizon = _GAME_DESIGN_ANALYSIS_DEFAULTS["forecast_horizon_ticks"]
        self._game_design_state.pending_forecasts = min(
            len(self._game_design_state.design_concepts), 5
        )

        self._game_design_state.timestamp = _time_module.time()
        return self._game_design_state.to_dict()

    def _run_balance_analysis(self, mechanics: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Run balance analysis on a set of game mechanics.

        Evaluates each mechanic against standard balance dimensions,
        computing power curves, resource economy, and risk-reward profiles.

        Args:
            mechanics: List of mechanic dictionaries.

        Returns:
            Balance analysis result dictionary.
        """
        dimensions = _GAME_DESIGN_ANALYSIS_DEFAULTS["balance_dimensions"]
        scores: Dict[str, Dict[str, float]] = {}

        for mechanic in mechanics:
            mech_id = mechanic.get("id", uuid.uuid4().hex[:8])
            scores[mech_id] = {}
            for dim in dimensions:
                # Generate balanced score centered around 0.5 with some variance
                raw = 0.5 + 0.15 * (hash(f"{mech_id}_{dim}") % 100) / 100 - 0.075
                scores[mech_id][dim] = round(raw, 3)

        # Identify imbalances (scores far from 0.5)
        imbalances = []
        for mech_id, dim_scores in scores.items():
            for dim, score in dim_scores.items():
                deviation = abs(score - 0.5)
                if deviation > 0.25:
                    imbalances.append({
                        "mechanic": mech_id,
                        "dimension": dim,
                        "score": score,
                        "deviation": round(deviation, 3),
                        "severity": "high" if deviation > 0.35 else "medium",
                    })

        return {
            "id": uuid.uuid4().hex,
            "mechanic_count": len(mechanics),
            "dimension_scores": scores,
            "imbalances_detected": len(imbalances),
            "imbalances": imbalances,
            "overall_balance": round(
                1.0 - min(len(imbalances) / max(len(mechanics) * len(dimensions), 1), 1.0), 3
            ),
            "timestamp": _time_module.time(),
        }

    def _compute_design_quality_metrics(self) -> Dict[str, float]:
        """Compute aggregate design quality metrics.

        Evaluates concept diversity, mechanical depth, balance quality,
        and iteration momentum.

        Returns:
            Dictionary of quality metric scores.
        """
        metrics: Dict[str, float] = {
            "concept_diversity": 0.0,
            "mechanical_depth": 0.0,
            "balance_quality": 0.0,
            "iteration_momentum": 0.0,
            "forecast_confidence": 0.0,
        }

        concepts = self._game_design_state.design_concepts
        if concepts:
            # Diversity: number of unique concept types
            types = {c.get("type", "unknown") for c in concepts}
            metrics["concept_diversity"] = round(
                min(len(types) / 10, 1.0), 3
            )

            # Mechanical depth from balance analyses
            analyses = self._game_design_state.balance_analyses
            if analyses:
                metrics["mechanical_depth"] = round(
                    sum(a.get("mechanic_count", 0) for a in analyses) / max(len(analyses) * 5, 1), 3
                )

        # Balance quality from latest analysis
        if self._game_design_state.balance_analyses:
            latest = self._game_design_state.balance_analyses[-1]
            metrics["balance_quality"] = latest.get("overall_balance", 0.0)

        # Iteration momentum
        if self._game_design_state.design_iteration_count > 0:
            metrics["iteration_momentum"] = round(
                min(self._game_design_state.design_iteration_count / 50, 1.0), 3
            )

        # Forecast confidence (improves with more data)
        if concepts:
            metrics["forecast_confidence"] = round(
                min(len(concepts) / 20, 0.9), 3
            )

        return metrics

    def _generate_design_recommendations(self) -> List[Dict[str, Any]]:
        """Generate design recommendations based on current state.

        Analyzes balance issues, concept gaps, and quality metrics to
        produce actionable design improvement suggestions.

        Returns:
            List of recommendation dictionaries.
        """
        recommendations: List[Dict[str, Any]] = []

        # Recommend based on imbalances
        for analysis in self._game_design_state.balance_analyses[-3:]:
            for imbalance in analysis.get("imbalances", [])[:3]:
                recommendations.append({
                    "type": "balance_fix",
                    "mechanic": imbalance["mechanic"],
                    "dimension": imbalance["dimension"],
                    "current_score": imbalance["score"],
                    "suggested_action": (
                        "nerf" if imbalance["score"] > 0.75
                        else "buff" if imbalance["score"] < 0.25
                        else "adjust"
                    ),
                    "priority": "high" if imbalance["severity"] == "high" else "medium",
                })

        # Recommend concept exploration gaps
        existing_types = {c.get("type", "") for c in self._game_design_state.design_concepts}
        recommended_types = {"puzzle", "stealth", "social", "exploration"} - existing_types
        for rec_type in recommended_types:
            recommendations.append({
                "type": "concept_exploration",
                "suggested_domain": rec_type,
                "rationale": f"No existing concepts in {rec_type} domain",
                "priority": "low",
            })

        # Limit to requested count
        max_recs = _GAME_DESIGN_ANALYSIS_DEFAULTS["recommendation_count"]
        return recommendations[:max_recs]

    # ------------------------------------------------------------------
    # Status & Reporting
    # ------------------------------------------------------------------

    def get_status(self) -> Dict[str, Any]:
        """Get the current status of all ten subsystems.

        Returns a snapshot of subsystem health, active pipelines,
        operation counts, and error statistics.

        Returns:
            A dictionary mapping subsystem names to their status
            dictionaries.
        """
        result: Dict[str, Any] = {
            "phase": self._phase,
            "uptime_seconds": round(_time_module.time() - self._boot_time, 1),
            "total_cycles": self._total_cycles,
            "subsystems": {},
            "summary": {
                "healthy": 0,
                "degraded": 0,
                "strained": 0,
                "error": 0,
                "offline": 0,
            },
        }

        for name, status in self._subsystem_statuses.items():
            self._update_subsystem_health(name)
            result["subsystems"][name] = status.to_dict()
            health = status.health
            if health in result["summary"]:
                result["summary"][health] += 1

        return result

    def get_intelligence_report(self) -> Dict[str, Any]:
        """Generate a comprehensive intelligence status report.

        Aggregates metrics from all ten subsystems into a single
        detailed report covering perception accuracy, reasoning
        effectiveness, learning progress, creative output quality,
        task execution throughput, memory consolidation status,
        safety violations, world simulation state, and design
        intelligence metrics.

        Returns:
            A comprehensive dictionary report.
        """
        now = _time_module.time()
        uptime = max(now - self._boot_time, 1)

        # Perception metrics
        perception_frames = len(self._perception_history)
        avg_confidence = 0.0
        if self._perception_history:
            avg_confidence = round(
                sum(p.confidence for p in self._perception_history) / len(self._perception_history), 3
            )

        # Reasoning metrics
        reasoning_sessions = len(self._reasoning_sessions)
        avg_reasoning_confidence = 0.0
        if self._reasoning_sessions:
            avg_reasoning_confidence = round(
                sum(s.confidence for s in self._reasoning_sessions.values()) / reasoning_sessions, 3
            )

        # Learning metrics
        recent_rewards = self._learning_state.reward_history[-100:]
        avg_reward = round(sum(recent_rewards) / max(len(recent_rewards), 1), 4) if recent_rewards else 0.0

        # Creative metrics
        creative_count = len(self._creative_archive)
        avg_creative_quality = 0.0
        if self._creative_archive:
            avg_creative_quality = round(
                sum(c.get("quality_score", 0) for c in self._creative_archive) / creative_count, 3
            )

        # Task execution metrics
        task_throughput = self._task_state.throughput_rate
        task_success_rate = self._task_state.success_rate

        # Memory metrics
        kb_size = self._memory_state.knowledge_base_size

        # Safety metrics
        safety_events = self._safety_state.safety_violations
        governance_mode = self._safety_state.mode

        # World metrics
        world_tick = self._world_state.simulation_tick
        world_evolution = self._world_state.world_evolution_stage

        # Game design metrics
        design_concepts = len(self._game_design_state.design_concepts)
        design_quality = self._game_design_state.quality_metrics

        # Event statistics
        total_events = len(self._event_log)
        failed_events = sum(1 for e in self._event_log if not e.success)

        # Overall health calculation
        subsystem_healths = [
            s.health for s in self._subsystem_statuses.values()
        ]
        healthy_count = sum(1 for h in subsystem_healths if h == SubsystemHealth.HEALTHY.value)
        overall_health = round(healthy_count / max(len(subsystem_healths), 1), 3)

        return {
            "report_id": uuid.uuid4().hex,
            "generated_at": now,
            "core_version": "1.0.0",
            "uptime_seconds": round(uptime, 1),
            "total_cycles": self._total_cycles,
            "current_phase": self._phase,
            "overall_health": overall_health,

            "perception": {
                "frames_processed": perception_frames,
                "avg_confidence": avg_confidence,
                "attention_entities": len(self._perception_state.attention_focus),
                "latest_novelty_count": len([
                    n for n in self._perception_state.novelty_scores.values() if n > 0.5
                ]),
            },

            "reasoning": {
                "sessions_completed": reasoning_sessions,
                "avg_confidence": avg_reasoning_confidence,
                "active_session": self._active_reasoning_id,
            },

            "learning": {
                "iteration": self._learning_state.iteration,
                "mode": self._learning_state.mode,
                "curriculum_stage": self._learning_state.curriculum_stage,
                "curriculum_stage_name": (
                    _LEARNING_CURRICULUM_STAGES[self._learning_state.curriculum_stage]
                    if self._learning_state.curriculum_stage < len(_LEARNING_CURRICULUM_STAGES)
                    else "complete"
                ),
                "avg_reward_100": avg_reward,
                "exploration_rate": self._learning_state.exploration_rate,
                "skills_tracked": len(self._learning_state.skill_registry),
            },

            "creative": {
                "total_syntheses": creative_count,
                "avg_quality": avg_creative_quality,
                "active_domains": list(
                    set(c.get("domain", "") for c in self._creative_archive[-50:])
                ),
            },

            "social": {
                "personalities_tracked": len(self._social_state.personality_models),
                "relationship_edges": sum(
                    len(targets) for targets in self._social_state.relationship_graph.values()
                ),
                "active_conversations": self._social_state.active_conversations,
            },

            "task_execution": {
                "queue_depth": len(self._task_state.task_queue),
                "active_tasks": len(self._task_state.active_tasks),
                "completed_tasks": len(self._task_state.completed_tasks),
                "throughput_rate": task_throughput,
                "success_rate": task_success_rate,
                "agent_pools": len(self._task_state.agent_pool),
            },

            "memory_knowledge": {
                "knowledge_base_size": kb_size,
                "episodic_entries": len(self._memory_state.episodic_memory),
                "consolidated_entries": len(self._memory_state.consolidated_memories),
                "retrieval_cache_hit_rate": self._memory_state.retrieval_cache_hit_rate,
                "consolidation_queue": self._memory_state.consolidation_queue_size,
            },

            "safety_governance": {
                "mode": governance_mode,
                "violations_total": safety_events,
                "escalations": self._safety_state.escalation_count,
                "approval_queue_depth": len(self._safety_state.approval_queue),
                "active_guards": self._safety_state.guard_rules_enforced,
                "circuit_breakers": self._safety_state.circuit_breaker_status,
            },

            "world_intelligence": {
                "simulation_tick": world_tick,
                "evolution_stage": world_evolution,
                "pending_events": len(self._world_state.pending_world_events),
                "population_total": sum(self._world_state.population_counts.values()),
                "god_mode": self._world_state.god_mode_active,
                "weather": self._world_state.weather_state.get("condition", "unknown"),
            },

            "game_design_intelligence": {
                "design_concepts": design_concepts,
                "balance_analyses": len(self._game_design_state.balance_analyses),
                "quality_metrics": design_quality,
                "pending_forecasts": self._game_design_state.pending_forecasts,
                "recommendations_count": len(self._game_design_state.recommendations),
            },

            "events": {
                "total_logged": total_events,
                "failed": failed_events,
                "failure_rate": round(failed_events / max(total_events, 1), 4),
            },
        }

    def shutdown(self) -> None:
        """Perform graceful teardown of all subsystem pipelines.

        Transitions the core through the SHUTTING_DOWN phase, clears all
        active task queues, flushes pending events, archives critical
        state, and marks all subsystems as offline. After shutdown the
        core cannot be restarted without creating a new instance.
        """
        self._phase = CorePhase.SHUTTING_DOWN.value

        # Clear task queues to prevent new work
        self._task_state.task_queue.clear()
        self._task_state.active_tasks.clear()

        # Flush pending world events
        for event in self._world_state.pending_world_events:
            event["status"] = "cancelled_shutdown"
            self._world_event_queue.append(event)
        self._world_state.pending_world_events.clear()

        # Clear approval queue
        self._safety_state.approval_queue.clear()

        # Mark all subsystems as offline
        for status in self._subsystem_statuses.values():
            status.health = SubsystemHealth.OFFLINE.value
            status.active_pipelines = 0

        # Archive final state snapshot
        self._record_event(
            subsystem="core",
            event_type="shutdown",
            duration_ms=0,
            success=True,
            input_summary=f"Shutdown initiated at uptime {_time_module.time() - self._boot_time:.1f}s",
            output_summary=f"Total cycles: {self._total_cycles}, events: {len(self._event_log)}",
        )

        # Clear pipeline handlers
        self._pipeline_handlers.clear()

        self._phase = CorePhase.SHUTDOWN.value


# ---------------------------------------------------------------------------
# Module-level accessor
# ---------------------------------------------------------------------------


def get_agent_intelligence_core() -> AgentIntelligenceCore:
    """Return the singleton AgentIntelligenceCore instance.

    Convenience function that delegates to AgentIntelligenceCore.get_instance().
    This is the recommended entry point for accessing the intelligence core
    throughout the SparkLabs codebase.

    Returns:
        The singleton AgentIntelligenceCore instance.

    Example:
        >>> core = get_agent_intelligence_core()
        >>> status = core.get_status()
        >>> print(status["phase"])
        'idle'
    """
    return AgentIntelligenceCore.get_instance()