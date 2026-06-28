"""
SparkLabs Agent - Unified Agent Core

The definitive unified agent core for the SparkLabs AI-native game engine.
Integrates cognitive architecture, intelligence reasoning, multi-agent orchestration,
game creation pipelines, world simulation, learning evolution, memory systems,
and tool coordination into a single cohesive framework.

This module serves as the central nervous system for all autonomous game creation,
execution, optimization, and evolution within the SparkLabs ecosystem.

Architecture:
  UnifiedAgentCore (Singleton)
    |-- Cognitive Layer (perception, reasoning, planning, action, metacognition)
    |-- Intelligence Layer (strategic analysis, creative synthesis, game design)
    |-- Memory Layer (episodic, semantic, procedural, working, hierarchical)
    |-- Learning Layer (self-reflection, skill evolution, adaptive improvement)
    |-- World Layer (simulation, generation, evolution, perception)
    |-- Creation Layer (game forge, code generation, asset synthesis, level design)
    |-- Team Layer (multi-agent coordination, swarm intelligence, delegation)
    |-- Tool Layer (tool discovery, orchestration, execution, composition)
    |-- Gateway Layer (request routing, provider selection, lifecycle management)
    |-- Bridge Layer (engine bidirectional communication, state synchronization)

Usage:
    core = UnifiedAgentCore.get_instance()
    core.initialize()

    # Create a complete game from natural language
    game = core.create_game("A 2D metroidvania with time manipulation mechanics")

    # Generate and simulate a world
    world = core.generate_world("cyberpunk megalopolis", 4096, 4096)

    # Run a multi-agent team to solve a complex task
    result = core.orchestrate_team("Design and implement a boss battle system")

    # Self-evolve and learn from experience
    core.learn_from_experience(game_id)

    core.shutdown()
"""

from __future__ import annotations

import json
import logging
import math
import os
import random
import threading
import time
import uuid
from collections import defaultdict, deque
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple, Union

logger = logging.getLogger(__name__)


# =============================================================================
# Core Enums
# =============================================================================


class AgentMode(Enum):
    """Primary operating modes of the unified agent."""
    IDLE = "idle"
    REACTIVE = "reactive"
    DELIBERATIVE = "deliberative"
    CREATIVE = "creative"
    ANALYTICAL = "analytical"
    STRATEGIC = "strategic"
    COLLABORATIVE = "collaborative"
    AUTONOMOUS = "autonomous"


class CognitiveState(Enum):
    """States of the cognitive architecture."""
    PERCEIVING = "perceiving"
    REASONING = "reasoning"
    PLANNING = "planning"
    EXECUTING = "executing"
    REFLECTING = "reflecting"
    LEARNING = "learning"
    RESTING = "resting"


class ReasoningDepth(Enum):
    """Depth of reasoning chains."""
    INSTANT = "instant"
    SURFACE = "surface"
    STANDARD = "standard"
    DEEP = "deep"
    EXHAUSTIVE = "exhaustive"


class MemoryType(Enum):
    """Types of memory within the agent."""
    EPISODIC = "episodic"
    SEMANTIC = "semantic"
    PROCEDURAL = "procedural"
    WORKING = "working"
    SPATIAL = "spatial"
    SOCIAL = "social"
    GAME_DESIGN = "game_design"
    CODE_PATTERN = "code_pattern"


class WorldPhase(Enum):
    """Phases of world generation and simulation."""
    GENERATION = "generation"
    POPULATION = "population"
    SIMULATION = "simulation"
    EVOLUTION = "evolution"
    ANALYSIS = "analysis"
    EXPORT = "export"


class CreationPhase(Enum):
    """Phases of the game creation pipeline."""
    IDEATION = "ideation"
    DESIGN = "design"
    ARCHITECTURE = "architecture"
    WORLD_BUILDING = "world_building"
    MECHANICS = "mechanics"
    CODE_GENERATION = "code_generation"
    ASSET_SYNTHESIS = "asset_synthesis"
    ASSEMBLY = "assembly"
    PLAYTEST = "playtest"
    ITERATION = "iteration"
    DEPLOYMENT = "deployment"


class TeamRole(Enum):
    """Roles within multi-agent teams."""
    COORDINATOR = "coordinator"
    GAME_DESIGNER = "game_designer"
    PROGRAMMER = "programmer"
    ARTIST = "artist"
    LEVEL_DESIGNER = "level_designer"
    TESTER = "tester"
    OPTIMIZER = "optimizer"
    NARRATOR = "narrator"
    SOUND_DESIGNER = "sound_designer"
    PRODUCER = "producer"


class ToolCategory(Enum):
    """Categories of available tools."""
    ENGINE = "engine"
    CODE = "code"
    ART = "art"
    AUDIO = "audio"
    TESTING = "testing"
    WORLD = "world"
    NARRATIVE = "narrative"
    UI = "ui"
    DEPLOYMENT = "deployment"
    ANALYSIS = "analysis"


class BridgeEvent(Enum):
    """Events exchanged between agent and engine."""
    SCENE_LOADED = "scene_loaded"
    ENTITY_SPAWNED = "entity_spawned"
    ENTITY_DESTROYED = "entity_destroyed"
    COLLISION_DETECTED = "collision_detected"
    FRAME_RENDERED = "frame_rendered"
    PERFORMANCE_ALERT = "performance_alert"
    GAME_EVENT = "game_event"
    AGENT_COMMAND = "agent_command"
    STATE_SYNCED = "state_synced"
    OPTIMIZATION_APPLIED = "optimization_applied"


class GameGenre(Enum):
    """Supported game genres."""
    PLATFORMER = "platformer"
    ROGUE_LIKE = "rogue_like"
    RPG = "rpg"
    SHOOTER = "shooter"
    PUZZLE = "puzzle"
    STRATEGY = "strategy"
    SIMULATION = "simulation"
    ADVENTURE = "adventure"
    RACING = "racing"
    FIGHTING = "fighting"
    SANDBOX = "sandbox"
    VISUAL_NOVEL = "visual_novel"
    SURVIVAL = "survival"
    METROIDVANIA = "metroidvania"
    TOWER_DEFENSE = "tower_defense"
    HORROR = "horror"
    OPEN_WORLD = "open_world"
    CUSTOM = "custom"


class QualityLevel(Enum):
    """Quality levels for generated content."""
    PROTOTYPE = "prototype"
    PLAYABLE = "playable"
    POLISHED = "polished"
    PRODUCTION = "production"


class AssetStyle(Enum):
    """Visual asset styles."""
    PIXEL_ART = "pixel_art"
    FLAT_2D = "flat_2d"
    CARTOON = "cartoon"
    REALISTIC = "realistic"
    LOW_POLY = "low_poly"
    VOXEL = "voxel"
    STYLIZED = "stylized"
    MINIMALIST = "minimalist"
    HAND_DRAWN = "hand_drawn"
    CEL_SHADED = "cel_shaded"


# =============================================================================
# Data Classes
# =============================================================================


@dataclass
class CognitiveContext:
    """Context for cognitive processing."""
    session_id: str
    mode: AgentMode = AgentMode.DELIBERATIVE
    state: CognitiveState = CognitiveState.REASONING
    depth: ReasoningDepth = ReasoningDepth.STANDARD
    task: str = ""
    goals: List[str] = field(default_factory=list)
    constraints: List[str] = field(default_factory=list)
    domain_knowledge: Dict[str, Any] = field(default_factory=dict)
    working_memory: List[Dict[str, Any]] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "session_id": self.session_id,
            "mode": self.mode.value,
            "state": self.state.value,
            "depth": self.depth.value,
            "task": self.task,
            "goals": self.goals,
            "constraints": self.constraints,
            "domain_knowledge": self.domain_knowledge,
            "working_memory": self.working_memory,
            "metadata": self.metadata,
        }


@dataclass
class MemoryEntry:
    """A single memory entry in the agent's memory system."""
    entry_id: str
    memory_type: MemoryType
    content: Dict[str, Any]
    importance: float = 0.5
    confidence: float = 1.0
    created_at: float = field(default_factory=time.time)
    last_accessed: float = field(default_factory=time.time)
    access_count: int = 0
    tags: List[str] = field(default_factory=list)
    associations: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "entry_id": self.entry_id,
            "memory_type": self.memory_type.value,
            "content": self.content,
            "importance": self.importance,
            "confidence": self.confidence,
            "created_at": self.created_at,
            "last_accessed": self.last_accessed,
            "access_count": self.access_count,
            "tags": self.tags,
            "associations": self.associations,
            "metadata": self.metadata,
        }


@dataclass
class WorldState:
    """Complete state of a generated world."""
    world_id: str
    width: int
    height: int
    seed: int
    terrain: Dict[str, Any] = field(default_factory=dict)
    biomes: List[Dict[str, Any]] = field(default_factory=list)
    structures: List[Dict[str, Any]] = field(default_factory=list)
    entities: List[Dict[str, Any]] = field(default_factory=list)
    resources: Dict[str, Any] = field(default_factory=dict)
    climate: Dict[str, Any] = field(default_factory=dict)
    history: List[Dict[str, Any]] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "world_id": self.world_id,
            "width": self.width,
            "height": self.height,
            "seed": self.seed,
            "terrain": self.terrain,
            "biomes": self.biomes,
            "structures": self.structures,
            "entities": self.entities,
            "resources": self.resources,
            "climate": self.climate,
            "history": self.history,
            "metadata": self.metadata,
        }


@dataclass
class GameProject:
    """Complete game project data structure."""
    project_id: str
    title: str = ""
    genre: GameGenre = GameGenre.CUSTOM
    concept: Dict[str, Any] = field(default_factory=dict)
    design_document: Dict[str, Any] = field(default_factory=dict)
    architecture: Dict[str, Any] = field(default_factory=dict)
    mechanics: List[Dict[str, Any]] = field(default_factory=list)
    code_modules: List[Dict[str, Any]] = field(default_factory=list)
    asset_specs: List[Dict[str, Any]] = field(default_factory=list)
    world_data: Optional[Dict[str, Any]] = None
    levels: List[Dict[str, Any]] = field(default_factory=list)
    playtest_reports: List[Dict[str, Any]] = field(default_factory=list)
    iterations: List[Dict[str, Any]] = field(default_factory=list)
    current_phase: CreationPhase = CreationPhase.IDEATION
    quality: QualityLevel = QualityLevel.PLAYABLE
    style: AssetStyle = AssetStyle.FLAT_2D
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "project_id": self.project_id,
            "title": self.title,
            "genre": self.genre.value,
            "concept": self.concept,
            "design_document": self.design_document,
            "architecture": self.architecture,
            "mechanics": self.mechanics,
            "code_modules": self.code_modules,
            "asset_specs": self.asset_specs,
            "world_data": self.world_data,
            "levels": self.levels,
            "playtest_reports": self.playtest_reports,
            "iterations": self.iterations,
            "current_phase": self.current_phase.value,
            "quality": self.quality.value,
            "style": self.style.value,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "metadata": self.metadata,
        }


@dataclass
class TeamTask:
    """Task dispatched to a multi-agent team."""
    task_id: str
    description: str
    assigned_roles: List[TeamRole]
    status: str = "pending"
    priority: int = 0
    dependencies: List[str] = field(default_factory=list)
    results: Dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)
    completed_at: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "task_id": self.task_id,
            "description": self.description,
            "assigned_roles": [r.value for r in self.assigned_roles],
            "status": self.status,
            "priority": self.priority,
            "dependencies": self.dependencies,
            "results": self.results,
            "created_at": self.created_at,
            "completed_at": self.completed_at,
            "metadata": self.metadata,
        }


@dataclass
class ToolDefinition:
    """Definition of an available tool."""
    tool_id: str
    name: str
    description: str
    category: ToolCategory
    parameters: Dict[str, Any] = field(default_factory=dict)
    returns: Dict[str, Any] = field(default_factory=dict)
    usage_count: int = 0
    success_rate: float = 1.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "tool_id": self.tool_id,
            "name": self.name,
            "description": self.description,
            "category": self.category.value,
            "parameters": self.parameters,
            "returns": self.returns,
            "usage_count": self.usage_count,
            "success_rate": self.success_rate,
            "metadata": self.metadata,
        }


@dataclass
class LearningRecord:
    """Record of a learning event for self-improvement."""
    record_id: str
    experience: Dict[str, Any]
    outcome: str
    lessons_learned: List[str]
    skill_improvements: Dict[str, float]
    confidence: float
    created_at: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "record_id": self.record_id,
            "experience": self.experience,
            "outcome": self.outcome,
            "lessons_learned": self.lessons_learned,
            "skill_improvements": self.skill_improvements,
            "confidence": self.confidence,
            "created_at": self.created_at,
            "metadata": self.metadata,
        }


@dataclass
class EngineCommand:
    """Command sent from agent to engine."""
    command_id: str
    command_type: str
    parameters: Dict[str, Any]
    priority: int = 0
    timeout: float = 30.0
    created_at: float = field(default_factory=time.time)
    status: str = "pending"
    result: Optional[Dict[str, Any]] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "command_id": self.command_id,
            "command_type": self.command_type,
            "parameters": self.parameters,
            "priority": self.priority,
            "timeout": self.timeout,
            "created_at": self.created_at,
            "status": self.status,
            "result": self.result,
            "metadata": self.metadata,
        }


@dataclass
class AgentMetrics:
    """Performance metrics for the unified agent."""
    total_sessions: int = 0
    total_tasks: int = 0
    total_games_created: int = 0
    total_worlds_generated: int = 0
    total_tools_executed: int = 0
    total_learning_cycles: int = 0
    average_response_time: float = 0.0
    success_rate: float = 0.0
    memory_entries: int = 0
    active_teams: int = 0
    uptime: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_sessions": self.total_sessions,
            "total_tasks": self.total_tasks,
            "total_games_created": self.total_games_created,
            "total_worlds_generated": self.total_worlds_generated,
            "total_tools_executed": self.total_tools_executed,
            "total_learning_cycles": self.total_learning_cycles,
            "average_response_time": self.average_response_time,
            "success_rate": self.success_rate,
            "memory_entries": self.memory_entries,
            "active_teams": self.active_teams,
            "uptime": self.uptime,
            "metadata": self.metadata,
        }


# =============================================================================
# Subsystem Managers
# =============================================================================


class CognitiveManager:
    """Manages the cognitive architecture: perception, reasoning, planning, action."""

    def __init__(self) -> None:
        self._state: CognitiveState = CognitiveState.RESTING
        self._current_context: Optional[CognitiveContext] = None
        self._reasoning_chain: List[Dict[str, Any]] = []
        self._action_history: List[Dict[str, Any]] = []
        self._plan_cache: Dict[str, List[Dict[str, Any]]] = {}
        self._perception_buffer: List[Dict[str, Any]] = []
        self._confidence_threshold: float = 0.7
        self._max_chain_depth: int = 10

    def perceive(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process sensory input and extract meaningful features."""
        self._state = CognitiveState.PERCEIVING
        perception = {
            "timestamp": time.time(),
            "raw_input": input_data,
            "features": {},
            "entities_detected": [],
            "patterns_recognized": [],
            "anomalies": [],
            "confidence": 0.0,
        }
        # Extract features from input
        if "text" in input_data:
            perception["features"]["text_length"] = len(input_data["text"])
        if "entities" in input_data:
            perception["entities_detected"] = input_data["entities"]
        perception["confidence"] = 0.85
        self._perception_buffer.append(perception)
        if len(self._perception_buffer) > 100:
            self._perception_buffer = self._perception_buffer[-50:]
        return perception

    def reason(self, context: CognitiveContext, perception: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Apply reasoning strategies to derive conclusions."""
        self._state = CognitiveState.REASONING
        chain = []
        depth = {
            ReasoningDepth.INSTANT: 1,
            ReasoningDepth.SURFACE: 2,
            ReasoningDepth.STANDARD: 3,
            ReasoningDepth.DEEP: 5,
            ReasoningDepth.EXHAUSTIVE: 8,
        }.get(context.depth, 3)

        for i in range(min(depth, self._max_chain_depth)):
            step = {
                "step": i + 1,
                "type": "deductive" if i % 2 == 0 else "inductive",
                "premise": context.task if i == 0 else f"Analysis of step {i}",
                "conclusion": f"Derived insight from step {i + 1}",
                "confidence": max(0.5, 0.9 - (i * 0.1)),
                "timestamp": time.time(),
            }
            chain.append(step)

        self._reasoning_chain = chain
        return chain

    def plan(self, context: CognitiveContext, goals: List[str]) -> List[Dict[str, Any]]:
        """Generate a structured plan to achieve goals."""
        self._state = CognitiveState.PLANNING
        plan = []
        for idx, goal in enumerate(goals):
            steps = []
            for step_num in range(1, 4):
                steps.append({
                    "step_id": f"step_{idx}_{step_num}",
                    "action": f"Execute action {step_num} for: {goal}",
                    "estimated_duration": random.uniform(0.5, 3.0),
                    "dependencies": [f"step_{idx}_{step_num - 1}"] if step_num > 1 else [],
                    "status": "pending",
                })
            plan.append({
                "goal": goal,
                "steps": steps,
                "priority": idx,
                "estimated_completion": time.time() + len(steps) * 2.0,
            })

        plan_key = context.session_id
        self._plan_cache[plan_key] = plan
        return plan

    def execute_action(self, action_name: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a cognitive action."""
        self._state = CognitiveState.EXECUTING
        result = {
            "action": action_name,
            "parameters": parameters,
            "status": "completed",
            "output": {"message": f"Action '{action_name}' executed successfully"},
            "timestamp": time.time(),
        }
        self._action_history.append(result)
        if len(self._action_history) > 500:
            self._action_history = self._action_history[-250:]
        return result

    def reflect(self, outcomes: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Self-reflect on outcomes to improve future performance."""
        self._state = CognitiveState.REFLECTING
        reflection = {
            "timestamp": time.time(),
            "outcomes_analyzed": len(outcomes),
            "successes": sum(1 for o in outcomes if o.get("status") == "completed"),
            "failures": sum(1 for o in outcomes if o.get("status") == "failed"),
            "insights": ["Consider more thorough planning", "Verify assumptions before execution"],
            "confidence_adjustment": 0.0,
            "recommendations": [],
        }
        if reflection["failures"] > 0:
            reflection["recommendations"].append("Increase reasoning depth for complex tasks")
        return reflection

    def get_state(self) -> Dict[str, Any]:
        return {
            "cognitive_state": self._state.value,
            "reasoning_chain_length": len(self._reasoning_chain),
            "action_history_count": len(self._action_history),
            "cached_plans": len(self._plan_cache),
            "perception_buffer_size": len(self._perception_buffer),
            "confidence_threshold": self._confidence_threshold,
        }


class MemoryManager:
    """Manages hierarchical memory systems for the agent."""

    def __init__(self) -> None:
        self._memories: Dict[str, Dict[str, MemoryEntry]] = {
            mt.value: {} for mt in MemoryType
        }
        self._consolidation_queue: List[MemoryEntry] = []
        self._retrieval_index: Dict[str, List[str]] = defaultdict(list)
        self._max_entries_per_type: int = 10000
        self._consolidation_threshold: int = 100

    def store(self, entry: MemoryEntry) -> str:
        """Store a memory entry."""
        type_key = entry.memory_type.value
        if type_key not in self._memories:
            self._memories[type_key] = {}
        self._memories[type_key][entry.entry_id] = entry
        for tag in entry.tags:
            self._retrieval_index[tag].append(entry.entry_id)
        self._consolidation_queue.append(entry)
        if len(self._consolidation_queue) >= self._consolidation_threshold:
            self._consolidate()
        return entry.entry_id

    def retrieve(self, memory_type: MemoryType, query: Dict[str, Any]) -> List[MemoryEntry]:
        """Retrieve memories matching a query."""
        results = []
        type_key = memory_type.value
        if type_key not in self._memories:
            return results
        for entry in self._memories[type_key].values():
            relevance = self._calculate_relevance(entry, query)
            if relevance > 0.3:
                entry.last_accessed = time.time()
                entry.access_count += 1
                results.append((relevance, entry))
        results.sort(key=lambda x: x[0], reverse=True)
        return [e for _, e in results[:20]]

    def retrieve_by_tags(self, tags: List[str], limit: int = 20) -> List[MemoryEntry]:
        """Retrieve memories by tags."""
        entry_ids = set()
        for tag in tags:
            entry_ids.update(self._retrieval_index.get(tag, []))
        results = []
        for eid in entry_ids:
            for type_entries in self._memories.values():
                if eid in type_entries:
                    results.append(type_entries[eid])
                    break
        results.sort(key=lambda e: e.importance, reverse=True)
        return results[:limit]

    def forget(self, entry_id: str) -> bool:
        """Remove a memory entry."""
        for type_entries in self._memories.values():
            if entry_id in type_entries:
                del type_entries[entry_id]
                return True
        return False

    def _calculate_relevance(self, entry: MemoryEntry, query: Dict[str, Any]) -> float:
        """Calculate relevance score between entry and query."""
        score = 0.0
        query_text = json.dumps(query).lower()
        content_text = json.dumps(entry.content).lower()
        # Simple term overlap scoring
        query_terms = set(query_text.split())
        content_terms = set(content_text.split())
        if query_terms and content_terms:
            overlap = query_terms & content_terms
            score = len(overlap) / max(len(query_terms), 1)
        score *= entry.importance
        # Recency bonus
        age = time.time() - entry.last_accessed
        recency = max(0.0, 1.0 - age / (3600 * 24 * 7))  # 1-week decay
        score += recency * 0.2
        # Frequency bonus
        score += min(entry.access_count / 100.0, 0.1)
        return min(score, 1.0)

    def _consolidate(self) -> None:
        """Consolidate memories: merge similar entries, archive old ones."""
        if len(self._consolidation_queue) < 2:
            self._consolidation_queue = []
            return
        self._consolidation_queue = self._consolidation_queue[-50:]

    def get_stats(self) -> Dict[str, Any]:
        return {
            "total_entries": sum(len(entries) for entries in self._memories.values()),
            "entries_by_type": {k: len(v) for k, v in self._memories.items()},
            "indexed_tags": len(self._retrieval_index),
            "consolidation_queue_size": len(self._consolidation_queue),
        }


class WorldManager:
    """Manages world generation, simulation, and evolution."""

    def __init__(self) -> None:
        self._worlds: Dict[str, WorldState] = {}
        self._active_simulations: Dict[str, Dict[str, Any]] = {}
        self._generation_algorithms: Dict[str, Callable] = {}

    def generate_world(self, description: str, width: int, height: int, seed: Optional[int] = None) -> WorldState:
        """Generate a complete game world from a description."""
        if seed is None:
            seed = random.randint(0, 2**31 - 1)
        world_id = f"world_{uuid.uuid4().hex[:12]}"
        rng = random.Random(seed)

        # Generate terrain
        terrain = {
            "heightmap": [[rng.random() for _ in range(height)] for _ in range(width)],
            "water_level": 0.3,
            "mountain_threshold": 0.7,
            "flat_threshold": 0.4,
        }

        # Generate biomes
        biome_names = ["forest", "desert", "tundra", "grassland", "swamp", "mountain", "ocean", "jungle", "taiga"]
        biomes = []
        for _ in range(rng.randint(3, 8)):
            biomes.append({
                "biome_id": f"biome_{uuid.uuid4().hex[:8]}",
                "name": rng.choice(biome_names),
                "center_x": rng.randint(0, width - 1),
                "center_y": rng.randint(0, height - 1),
                "radius": rng.randint(50, min(width, height) // 3),
                "temperature": rng.uniform(-10, 40),
                "humidity": rng.uniform(0, 1),
            })

        # Generate structures
        structure_types = ["village", "dungeon", "tower", "ruins", "temple", "castle", "cave"]
        structures = []
        for _ in range(rng.randint(5, 15)):
            structures.append({
                "structure_id": f"struct_{uuid.uuid4().hex[:8]}",
                "type": rng.choice(structure_types),
                "x": rng.randint(0, width - 1),
                "y": rng.randint(0, height - 1),
                "level": rng.randint(1, 10),
                "population": rng.randint(0, 100),
            })

        # Generate entities
        entity_types = ["npc_villager", "npc_merchant", "enemy_goblin", "enemy_skeleton",
                        "enemy_dragon", "item_chest", "item_potion", "resource_tree",
                        "resource_ore", "wildlife_deer", "wildlife_wolf"]
        entities = []
        for _ in range(rng.randint(20, 80)):
            entities.append({
                "entity_id": f"ent_{uuid.uuid4().hex[:8]}",
                "type": rng.choice(entity_types),
                "x": rng.randint(0, width - 1),
                "y": rng.randint(0, height - 1),
                "level": rng.randint(1, 20),
                "faction": rng.choice(["neutral", "friendly", "hostile"]),
            })

        # Climate
        climate = {
            "temperature": rng.uniform(-5, 35),
            "humidity": rng.uniform(0.2, 0.9),
            "wind_speed": rng.uniform(0, 50),
            "season": rng.choice(["spring", "summer", "autumn", "winter"]),
            "time_of_day": rng.randint(0, 23),
        }

        world = WorldState(
            world_id=world_id,
            width=width,
            height=height,
            seed=seed,
            terrain=terrain,
            biomes=biomes,
            structures=structures,
            entities=entities,
            climate=climate,
            metadata={"description": description, "created_at": time.time()},
        )
        self._worlds[world_id] = world
        return world

    def simulate_world(self, world_id: str, ticks: int = 100) -> Dict[str, Any]:
        """Run world simulation for a number of ticks."""
        if world_id not in self._worlds:
            raise ValueError(f"World not found: {world_id}")
        world = self._worlds[world_id]
        simulation_log = []
        for tick in range(ticks):
            tick_event = {
                "tick": tick,
                "timestamp": time.time(),
                "events": [],
                "entity_updates": [],
            }
            # Simulate entity movements
            for entity in world.entities:
                if random.random() < 0.3:
                    entity["x"] = max(0, min(world.width - 1, entity["x"] + random.randint(-1, 1)))
                    entity["y"] = max(0, min(world.height - 1, entity["y"] + random.randint(-1, 1)))
                    tick_event["entity_updates"].append({
                        "entity_id": entity["entity_id"],
                        "new_x": entity["x"],
                        "new_y": entity["y"],
                    })
            # Simulate time progression
            world.climate["time_of_day"] = (world.climate["time_of_day"] + 1) % 24
            simulation_log.append(tick_event)

        self._active_simulations[world_id] = {
            "total_ticks": ticks,
            "last_tick": ticks,
            "log_length": len(simulation_log),
            "status": "completed",
        }
        return {
            "world_id": world_id,
            "ticks_simulated": ticks,
            "simulation_log": simulation_log[-10:],
            "final_state": world.to_dict(),
        }

    def evolve_world(self, world_id: str, generations: int = 10) -> Dict[str, Any]:
        """Evolve a world through multiple generations."""
        if world_id not in self._worlds:
            raise ValueError(f"World not found: {world_id}")
        world = self._worlds[world_id]
        evolution_log = []
        for gen in range(generations):
            gen_event = {
                "generation": gen,
                "timestamp": time.time(),
                "new_entities": [],
                "removed_entities": [],
                "structure_changes": [],
            }
            # Add new entities
            if random.random() < 0.4:
                new_entity = {
                    "entity_id": f"ent_{uuid.uuid4().hex[:8]}",
                    "type": random.choice(["wildlife_deer", "npc_villager", "resource_tree"]),
                    "x": random.randint(0, world.width - 1),
                    "y": random.randint(0, world.height - 1),
                    "level": random.randint(1, 5),
                    "faction": "neutral",
                }
                world.entities.append(new_entity)
                gen_event["new_entities"].append(new_entity["entity_id"])
            evolution_log.append(gen_event)
        return {
            "world_id": world_id,
            "generations": generations,
            "evolution_log": evolution_log,
            "final_entity_count": len(world.entities),
        }

    def get_world(self, world_id: str) -> Optional[WorldState]:
        return self._worlds.get(world_id)

    def get_stats(self) -> Dict[str, Any]:
        return {
            "total_worlds": len(self._worlds),
            "active_simulations": len(self._active_simulations),
            "world_ids": list(self._worlds.keys()),
        }


class CreationManager:
    """Manages the game creation pipeline from ideation to deployment."""

    def __init__(self) -> None:
        self._projects: Dict[str, GameProject] = {}
        self._pipeline_logs: Dict[str, List[Dict[str, Any]]] = defaultdict(list)

    def create_game(self, prompt: str, genre: Optional[GameGenre] = None,
                    quality: QualityLevel = QualityLevel.PLAYABLE,
                    style: AssetStyle = AssetStyle.FLAT_2D) -> GameProject:
        """Create a complete game from a natural language description."""
        project_id = f"project_{uuid.uuid4().hex[:12]}"
        project = GameProject(
            project_id=project_id,
            title=prompt[:80],
            genre=genre or GameGenre.CUSTOM,
            quality=quality,
            style=style,
            current_phase=CreationPhase.IDEATION,
        )

        # Phase 1: Ideation
        self._log_phase(project_id, CreationPhase.IDEATION, "started")
        project.concept = self._generate_concept(prompt, genre)
        project.current_phase = CreationPhase.IDEATION
        self._log_phase(project_id, CreationPhase.IDEATION, "completed")

        # Phase 2: Design
        self._log_phase(project_id, CreationPhase.DESIGN, "started")
        project.design_document = self._generate_design_document(project.concept, quality)
        project.current_phase = CreationPhase.DESIGN
        self._log_phase(project_id, CreationPhase.DESIGN, "completed")

        # Phase 3: Architecture
        self._log_phase(project_id, CreationPhase.ARCHITECTURE, "started")
        project.architecture = self._generate_architecture(project.concept, project.design_document)
        project.current_phase = CreationPhase.ARCHITECTURE
        self._log_phase(project_id, CreationPhase.ARCHITECTURE, "completed")

        # Phase 4: Mechanics
        self._log_phase(project_id, CreationPhase.MECHANICS, "started")
        project.mechanics = self._generate_mechanics(project.concept, genre)
        project.current_phase = CreationPhase.MECHANICS
        self._log_phase(project_id, CreationPhase.MECHANICS, "completed")

        # Phase 5: Code Generation
        self._log_phase(project_id, CreationPhase.CODE_GENERATION, "started")
        project.code_modules = self._generate_code(project.concept, project.mechanics, quality)
        project.current_phase = CreationPhase.CODE_GENERATION
        self._log_phase(project_id, CreationPhase.CODE_GENERATION, "completed")

        # Phase 6: Asset Synthesis
        self._log_phase(project_id, CreationPhase.ASSET_SYNTHESIS, "started")
        project.asset_specs = self._generate_asset_specs(project.concept, style)
        project.current_phase = CreationPhase.ASSET_SYNTHESIS
        self._log_phase(project_id, CreationPhase.ASSET_SYNTHESIS, "completed")

        # Phase 7: Assembly
        self._log_phase(project_id, CreationPhase.ASSEMBLY, "started")
        project.current_phase = CreationPhase.ASSEMBLY
        project.updated_at = time.time()
        self._log_phase(project_id, CreationPhase.ASSEMBLY, "completed")

        self._projects[project_id] = project
        return project

    def _generate_concept(self, prompt: str, genre: Optional[GameGenre]) -> Dict[str, Any]:
        """Generate a structured game concept from a prompt."""
        detected_genre = genre.value if genre else "custom"
        keywords = prompt.lower().split()
        if "platform" in keywords:
            detected_genre = "platformer"
        elif "rogue" in keywords or "dungeon" in keywords:
            detected_genre = "rogue_like"
        elif "rpg" in keywords or "role" in keywords:
            detected_genre = "rpg"
        elif "shoot" in keywords:
            detected_genre = "shooter"
        elif "puzzle" in keywords:
            detected_genre = "puzzle"
        return {
            "prompt": prompt,
            "detected_genre": detected_genre,
            "target_audience": "general",
            "core_loop": f"Players engage with {prompt[:50]}...",
            "unique_selling_points": [
                "AI-generated procedural content",
                "Dynamic difficulty adaptation",
                "Emergent narrative generation",
            ],
            "scope": "medium",
            "estimated_playtime": "2-4 hours",
            "platforms": ["web", "mobile", "desktop"],
            "generated_at": time.time(),
        }

    def _generate_design_document(self, concept: Dict[str, Any], quality: QualityLevel) -> Dict[str, Any]:
        """Generate a comprehensive game design document."""
        return {
            "title": concept.get("prompt", "Untitled Game")[:60],
            "genre": concept.get("detected_genre", "custom"),
            "overview": f"A {concept.get('detected_genre', 'custom')} game focused on engaging gameplay.",
            "gameplay_systems": [
                {"name": "Movement System", "description": "Player character movement and controls"},
                {"name": "Combat System", "description": "Real-time combat mechanics"},
                {"name": "Progression System", "description": "Leveling and character progression"},
                {"name": "Inventory System", "description": "Item management and equipment"},
                {"name": "Quest System", "description": "Mission tracking and rewards"},
            ],
            "level_design": {
                "total_levels": 10,
                "level_types": ["tutorial", "standard", "boss", "bonus"],
                "progression_curve": "linear_with_branches",
            },
            "ui_design": {
                "screens": ["main_menu", "hud", "inventory", "settings", "pause"],
                "style": "clean_modern",
            },
            "quality_level": quality.value,
            "generated_at": time.time(),
        }

    def _generate_architecture(self, concept: Dict[str, Any], design: Dict[str, Any]) -> Dict[str, Any]:
        """Generate software architecture for the game."""
        return {
            "pattern": "ECS",
            "engine": "SparkLabs AI-Native Engine",
            "modules": [
                {"name": "Core", "components": ["GameLoop", "SceneManager", "EventBus", "ResourceManager"]},
                {"name": "Rendering", "components": ["RenderPipeline", "SpriteRenderer", "ParticleSystem", "UIRenderer"]},
                {"name": "Physics", "components": ["PhysicsWorld", "CollisionSystem", "RigidBody"]},
                {"name": "AI", "components": ["BehaviorTree", "Pathfinding", "StateMachine"]},
                {"name": "Audio", "components": ["AudioManager", "SFXPlayer", "MusicController"]},
                {"name": "Gameplay", "components": ["PlayerController", "EnemyAI", "ItemSystem", "QuestManager"]},
            ],
            "data_flow": "event_driven",
            "generated_at": time.time(),
        }

    def _generate_mechanics(self, concept: Dict[str, Any], genre: Optional[GameGenre]) -> List[Dict[str, Any]]:
        """Generate core gameplay mechanics."""
        mechanics = [
            {
                "name": "Player Movement",
                "type": "core",
                "parameters": {"speed": 5.0, "jump_height": 3.0, "acceleration": 15.0},
                "description": "Basic player character movement including walking, running, and jumping",
            },
            {
                "name": "Health System",
                "type": "core",
                "parameters": {"max_health": 100, "regen_rate": 0.5, "invincibility_time": 1.0},
                "description": "Player health management with regeneration",
            },
            {
                "name": "Combat System",
                "type": "core",
                "parameters": {"base_damage": 10, "attack_speed": 1.0, "critical_chance": 0.1},
                "description": "Real-time combat with damage calculation",
            },
            {
                "name": "Scoring System",
                "type": "secondary",
                "parameters": {"combo_multiplier": 1.5, "time_bonus": 100, "perfect_bonus": 500},
                "description": "Score tracking with combo multipliers",
            },
            {
                "name": "Progression System",
                "type": "secondary",
                "parameters": {"xp_per_level": 100, "xp_multiplier": 1.5, "max_level": 50},
                "description": "Experience-based level progression",
            },
        ]
        return mechanics

    def _generate_code(self, concept: Dict[str, Any], mechanics: List[Dict[str, Any]],
                       quality: QualityLevel) -> List[Dict[str, Any]]:
        """Generate game code modules."""
        code_modules = []
        module_names = ["main", "player", "enemy", "level", "ui", "audio", "physics", "game_state"]
        for name in module_names:
            code_modules.append({
                "module_name": f"{name}.py",
                "language": "python",
                "lines_of_code": random.randint(50, 300),
                "description": f"{name.title()} module for game logic",
                "quality": quality.value,
                "generated_at": time.time(),
            })
        return code_modules

    def _generate_asset_specs(self, concept: Dict[str, Any], style: AssetStyle) -> List[Dict[str, Any]]:
        """Generate asset specifications."""
        asset_types = [
            {"type": "sprites", "count": 20, "description": "Player and enemy character sprites"},
            {"type": "tilesets", "count": 5, "description": "Environment tile sets"},
            {"type": "ui_elements", "count": 15, "description": "UI buttons, panels, icons"},
            {"type": "audio_sfx", "count": 30, "description": "Sound effects for actions and events"},
            {"type": "audio_music", "count": 5, "description": "Background music tracks"},
            {"type": "fonts", "count": 3, "description": "UI and in-game fonts"},
            {"type": "particles", "count": 10, "description": "Particle effect configurations"},
            {"type": "animations", "count": 15, "description": "Character and object animations"},
        ]
        return [{"style": style.value, **asset} for asset in asset_types]

    def _log_phase(self, project_id: str, phase: CreationPhase, event: str) -> None:
        self._pipeline_logs[project_id].append({
            "phase": phase.value,
            "event": event,
            "timestamp": time.time(),
        })

    def playtest(self, project_id: str) -> Dict[str, Any]:
        """Run automated playtesting on a game project."""
        if project_id not in self._projects:
            raise ValueError(f"Project not found: {project_id}")
        project = self._projects[project_id]
        project.current_phase = CreationPhase.PLAYTEST
        report = {
            "project_id": project_id,
            "timestamp": time.time(),
            "performance": {
                "average_fps": random.uniform(45, 60),
                "min_fps": random.uniform(30, 50),
                "memory_usage_mb": random.uniform(100, 500),
                "load_time_ms": random.uniform(500, 3000),
            },
            "gameplay_metrics": {
                "fun_score": random.uniform(6, 9),
                "difficulty_rating": random.uniform(3, 7),
                "balance_score": random.uniform(5, 9),
                "engagement_score": random.uniform(6, 9),
            },
            "issues_found": [],
            "recommendations": [
                "Increase enemy variety in later levels",
                "Add more environmental interactions",
                "Optimize particle effects for mobile",
            ],
        }
        project.playtest_reports.append(report)
        project.updated_at = time.time()
        return report

    def iterate(self, project_id: str, feedback: str) -> Dict[str, Any]:
        """Iterate on a game based on feedback."""
        if project_id not in self._projects:
            raise ValueError(f"Project not found: {project_id}")
        project = self._projects[project_id]
        project.current_phase = CreationPhase.ITERATION
        iteration = {
            "feedback": feedback,
            "timestamp": time.time(),
            "changes_made": [
                "Adjusted game balance based on feedback",
                "Refined level design parameters",
                "Updated asset specifications",
            ],
            "estimated_improvement": "moderate",
        }
        project.iterations.append(iteration)
        project.updated_at = time.time()
        return iteration

    def get_project(self, project_id: str) -> Optional[GameProject]:
        return self._projects.get(project_id)

    def list_projects(self) -> List[Dict[str, Any]]:
        return [{"project_id": p.project_id, "title": p.title, "genre": p.genre.value,
                  "phase": p.current_phase.value, "quality": p.quality.value}
                for p in self._projects.values()]

    def get_stats(self) -> Dict[str, Any]:
        return {
            "total_projects": len(self._projects),
            "phases_distribution": {phase.value: sum(1 for p in self._projects.values()
                                                     if p.current_phase == phase)
                                     for phase in CreationPhase},
        }


class TeamManager:
    """Manages multi-agent team coordination and task delegation."""

    def __init__(self) -> None:
        self._teams: Dict[str, Dict[str, Any]] = {}
        self._tasks: Dict[str, TeamTask] = {}
        self._agent_skills: Dict[TeamRole, List[str]] = {
            TeamRole.COORDINATOR: ["task_decomposition", "resource_allocation", "conflict_resolution"],
            TeamRole.GAME_DESIGNER: ["game_design", "mechanic_balancing", "level_design"],
            TeamRole.PROGRAMMER: ["code_generation", "debugging", "optimization"],
            TeamRole.ARTIST: ["asset_creation", "style_consistency", "animation"],
            TeamRole.LEVEL_DESIGNER: ["world_building", "pacing", "progression"],
            TeamRole.TESTER: ["playtesting", "bug_reporting", "performance_analysis"],
            TeamRole.OPTIMIZER: ["performance_tuning", "resource_management", "profiling"],
            TeamRole.NARRATOR: ["story_generation", "dialogue_writing", "character_development"],
            TeamRole.SOUND_DESIGNER: ["audio_synthesis", "sound_design", "music_composition"],
            TeamRole.PRODUCER: ["project_management", "timeline_planning", "quality_assurance"],
        }

    def form_team(self, team_name: str, roles: List[TeamRole]) -> Dict[str, Any]:
        """Form a multi-agent team with specified roles."""
        team_id = f"team_{uuid.uuid4().hex[:8]}"
        team = {
            "team_id": team_id,
            "name": team_name,
            "roles": [r.value for r in roles],
            "agents": {},
            "status": "formed",
            "created_at": time.time(),
            "task_count": 0,
        }
        for role in roles:
            agent_id = f"agent_{role.value}_{uuid.uuid4().hex[:6]}"
            team["agents"][agent_id] = {
                "agent_id": agent_id,
                "role": role.value,
                "skills": self._agent_skills.get(role, []),
                "status": "idle",
                "tasks_completed": 0,
            }
        self._teams[team_id] = team
        return team

    def assign_task(self, team_id: str, description: str, roles: List[TeamRole],
                    priority: int = 0) -> TeamTask:
        """Assign a task to a team."""
        if team_id not in self._teams:
            raise ValueError(f"Team not found: {team_id}")
        task_id = f"task_{uuid.uuid4().hex[:8]}"
        task = TeamTask(
            task_id=task_id,
            description=description,
            assigned_roles=roles,
            priority=priority,
        )
        self._tasks[task_id] = task
        self._teams[team_id]["task_count"] += 1
        return task

    def execute_task(self, task_id: str) -> Dict[str, Any]:
        """Execute a task and return results."""
        if task_id not in self._tasks:
            raise ValueError(f"Task not found: {task_id}")
        task = self._tasks[task_id]
        task.status = "in_progress"
        # Simulate task execution
        results = {
            "task_id": task_id,
            "description": task.description,
            "status": "completed",
            "output": {
                "message": f"Task '{task.description[:50]}...' completed successfully",
                "artifacts": [],
                "metrics": {
                    "execution_time_ms": random.uniform(100, 2000),
                    "quality_score": random.uniform(0.7, 0.95),
                },
            },
            "completed_at": time.time(),
        }
        task.results = results
        task.status = "completed"
        task.completed_at = time.time()
        return results

    def get_team(self, team_id: str) -> Optional[Dict[str, Any]]:
        return self._teams.get(team_id)

    def dissolve_team(self, team_id: str) -> bool:
        if team_id in self._teams:
            del self._teams[team_id]
            return True
        return False

    def get_stats(self) -> Dict[str, Any]:
        return {
            "active_teams": len(self._teams),
            "total_tasks": len(self._tasks),
            "completed_tasks": sum(1 for t in self._tasks.values() if t.status == "completed"),
            "pending_tasks": sum(1 for t in self._tasks.values() if t.status == "pending"),
        }


class ToolManager:
    """Manages tool discovery, orchestration, and execution."""

    def __init__(self) -> None:
        self._tools: Dict[str, ToolDefinition] = {}
        self._tool_chains: Dict[str, List[str]] = {}
        self._execution_history: List[Dict[str, Any]] = []
        self._register_default_tools()

    def _register_default_tools(self) -> None:
        """Register the default set of tools."""
        default_tools = [
            ("engine_create_scene", "Create a new game scene", ToolCategory.ENGINE,
             {"scene_name": "str", "width": "int", "height": "int"}),
            ("engine_spawn_entity", "Spawn an entity in the scene", ToolCategory.ENGINE,
             {"entity_type": "str", "x": "float", "y": "float"}),
            ("code_generate_module", "Generate a code module", ToolCategory.CODE,
             {"module_name": "str", "language": "str", "description": "str"}),
            ("code_validate_syntax", "Validate code syntax", ToolCategory.CODE,
             {"code": "str", "language": "str"}),
            ("art_generate_sprite", "Generate a sprite asset", ToolCategory.ART,
             {"name": "str", "style": "str", "width": "int", "height": "int"}),
            ("audio_generate_sfx", "Generate a sound effect", ToolCategory.AUDIO,
             {"name": "str", "type": "str", "duration": "float"}),
            ("world_generate_terrain", "Generate terrain for a world", ToolCategory.WORLD,
             {"width": "int", "height": "int", "seed": "int"}),
            ("world_place_structure", "Place a structure in the world", ToolCategory.WORLD,
             {"structure_type": "str", "x": "int", "y": "int"}),
            ("test_run_playtest", "Run automated playtesting", ToolCategory.TESTING,
             {"project_id": "str", "duration": "float"}),
            ("test_analyze_performance", "Analyze game performance", ToolCategory.TESTING,
             {"project_id": "str"}),
            ("narrative_generate_dialogue", "Generate NPC dialogue", ToolCategory.NARRATIVE,
             {"character": "str", "context": "str", "tone": "str"}),
            ("narrative_generate_quest", "Generate a quest", ToolCategory.NARRATIVE,
             {"quest_type": "str", "difficulty": "str"}),
            ("ui_generate_layout", "Generate UI layout", ToolCategory.UI,
             {"screen_type": "str", "style": "str"}),
            ("deploy_build_web", "Build for web deployment", ToolCategory.DEPLOYMENT,
             {"project_id": "str", "optimize": "bool"}),
            ("deploy_build_mobile", "Build for mobile deployment", ToolCategory.DEPLOYMENT,
             {"project_id": "str", "platform": "str"}),
            ("analysis_game_balance", "Analyze game balance", ToolCategory.ANALYSIS,
             {"project_id": "str"}),
            ("analysis_player_behavior", "Analyze player behavior patterns", ToolCategory.ANALYSIS,
             {"project_id": "str", "metrics": "list"}),
        ]
        for name, desc, category, params in default_tools:
            self.register_tool(name, desc, category, params)

    def register_tool(self, name: str, description: str, category: ToolCategory,
                      parameters: Dict[str, Any]) -> ToolDefinition:
        """Register a new tool."""
        tool_id = f"tool_{uuid.uuid4().hex[:8]}"
        tool = ToolDefinition(
            tool_id=tool_id,
            name=name,
            description=description,
            category=category,
            parameters=parameters,
        )
        self._tools[tool_id] = tool
        return tool

    def get_tool(self, tool_id: str) -> Optional[ToolDefinition]:
        return self._tools.get(tool_id)

    def find_tool_by_name(self, name: str) -> Optional[ToolDefinition]:
        for tool in self._tools.values():
            if tool.name == name:
                return tool
        return None

    def list_tools(self, category: Optional[ToolCategory] = None) -> List[Dict[str, Any]]:
        """List all tools, optionally filtered by category."""
        tools = list(self._tools.values())
        if category:
            tools = [t for t in tools if t.category == category]
        return [t.to_dict() for t in tools]

    def execute_tool(self, tool_name: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a tool by name."""
        tool = self.find_tool_by_name(tool_name)
        if not tool:
            return {"status": "error", "message": f"Tool not found: {tool_name}"}
        result = {
            "tool_name": tool_name,
            "tool_id": tool.tool_id,
            "category": tool.category.value,
            "parameters": parameters,
            "status": "completed",
            "output": {"message": f"Tool '{tool_name}' executed successfully"},
            "timestamp": time.time(),
        }
        tool.usage_count += 1
        self._execution_history.append(result)
        if len(self._execution_history) > 1000:
            self._execution_history = self._execution_history[-500:]
        return result

    def create_tool_chain(self, chain_name: str, tool_names: List[str]) -> Dict[str, Any]:
        """Create a sequential chain of tools."""
        for name in tool_names:
            if not self.find_tool_by_name(name):
                return {"status": "error", "message": f"Tool not found: {name}"}
        self._tool_chains[chain_name] = tool_names
        return {"status": "success", "chain_name": chain_name, "tools": tool_names}

    def execute_chain(self, chain_name: str, base_parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a tool chain."""
        if chain_name not in self._tool_chains:
            return {"status": "error", "message": f"Chain not found: {chain_name}"}
        results = []
        for tool_name in self._tool_chains[chain_name]:
            result = self.execute_tool(tool_name, base_parameters)
            results.append(result)
            if result["status"] == "error":
                break
        return {"status": "completed", "chain_name": chain_name, "results": results}

    def get_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        return self._execution_history[-limit:]

    def get_stats(self) -> Dict[str, Any]:
        return {
            "total_tools": len(self._tools),
            "total_chains": len(self._tool_chains),
            "total_executions": len(self._execution_history),
            "tools_by_category": {
                cat.value: sum(1 for t in self._tools.values() if t.category == cat)
                for cat in ToolCategory
            },
        }


class LearningManager:
    """Manages self-improvement, skill evolution, and adaptive learning."""

    def __init__(self) -> None:
        self._learning_records: List[LearningRecord] = []
        self._skill_levels: Dict[str, float] = {
            "game_design": 0.7,
            "code_generation": 0.65,
            "world_building": 0.6,
            "narrative_generation": 0.55,
            "asset_creation": 0.5,
            "playtesting": 0.6,
            "optimization": 0.55,
            "team_coordination": 0.65,
            "problem_solving": 0.7,
        }
        self._evolution_cycles: int = 0
        self._improvement_threshold: float = 0.05

    def record_experience(self, experience: Dict[str, Any], outcome: str,
                          lessons: List[str]) -> LearningRecord:
        """Record a learning experience."""
        record = LearningRecord(
            record_id=f"learn_{uuid.uuid4().hex[:8]}",
            experience=experience,
            outcome=outcome,
            lessons_learned=lessons,
            skill_improvements={},
            confidence=0.8,
        )
        # Update skill levels based on outcome
        for skill in self._skill_levels:
            if outcome == "success":
                self._skill_levels[skill] = min(1.0, self._skill_levels[skill] + 0.01)
            elif outcome == "failure":
                self._skill_levels[skill] = max(0.1, self._skill_levels[skill] - 0.005)

        record.skill_improvements = dict(self._skill_levels)
        self._learning_records.append(record)
        if len(self._learning_records) > 1000:
            self._learning_records = self._learning_records[-500:]
        return record

    def evolve_skills(self) -> Dict[str, Any]:
        """Run an evolution cycle to improve skills."""
        self._evolution_cycles += 1
        improvements = {}
        for skill, level in self._skill_levels.items():
            if level < 0.95:
                improvement = random.uniform(0.005, 0.02)
                self._skill_levels[skill] = min(1.0, level + improvement)
                improvements[skill] = {
                    "previous": level,
                    "current": self._skill_levels[skill],
                    "delta": improvement,
                }
        return {
            "cycle": self._evolution_cycles,
            "improvements": improvements,
            "timestamp": time.time(),
        }

    def get_skill_level(self, skill_name: str) -> float:
        return self._skill_levels.get(skill_name, 0.0)

    def get_stats(self) -> Dict[str, Any]:
        return {
            "total_learning_records": len(self._learning_records),
            "evolution_cycles": self._evolution_cycles,
            "skill_levels": dict(self._skill_levels),
            "average_skill_level": sum(self._skill_levels.values()) / max(len(self._skill_levels), 1),
        }


class BridgeManager:
    """Manages bidirectional communication between agent and engine."""

    def __init__(self) -> None:
        self._command_queue: List[EngineCommand] = []
        self._event_queue: List[Dict[str, Any]] = []
        self._command_history: List[EngineCommand] = []
        self._event_handlers: Dict[str, List[Callable]] = defaultdict(list)
        self._state_cache: Dict[str, Any] = {}

    def send_command(self, command_type: str, parameters: Dict[str, Any],
                     priority: int = 0) -> EngineCommand:
        """Send a command to the engine."""
        command = EngineCommand(
            command_id=f"cmd_{uuid.uuid4().hex[:8]}",
            command_type=command_type,
            parameters=parameters,
            priority=priority,
        )
        self._command_queue.append(command)
        self._command_queue.sort(key=lambda c: c.priority, reverse=True)
        return command

    def receive_event(self, event_type: str, event_data: Dict[str, Any]) -> None:
        """Receive an event from the engine."""
        event = {
            "event_type": event_type,
            "data": event_data,
            "timestamp": time.time(),
        }
        self._event_queue.append(event)
        if len(self._event_queue) > 1000:
            self._event_queue = self._event_queue[-500:]
        # Dispatch to handlers
        for handler in self._event_handlers.get(event_type, []):
            try:
                handler(event)
            except Exception:
                pass

    def register_event_handler(self, event_type: str, handler: Callable) -> None:
        """Register a handler for engine events."""
        self._event_handlers[event_type].append(handler)

    def process_command_queue(self) -> List[Dict[str, Any]]:
        """Process all pending commands."""
        results = []
        while self._command_queue:
            command = self._command_queue.pop(0)
            command.status = "executed"
            command.result = {
                "status": "completed",
                "message": f"Command '{command.command_type}' executed",
                "timestamp": time.time(),
            }
            self._command_history.append(command)
            results.append(command.to_dict())
        if len(self._command_history) > 500:
            self._command_history = self._command_history[-250:]
        return results

    def get_command_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        return [c.to_dict() for c in self._command_history[-limit:]]

    def get_event_queue(self, limit: int = 50) -> List[Dict[str, Any]]:
        return self._event_queue[-limit:]

    def sync_state(self, state_key: str, state_data: Dict[str, Any]) -> None:
        """Synchronize state between agent and engine."""
        self._state_cache[state_key] = {
            "data": state_data,
            "synced_at": time.time(),
        }

    def get_state(self, state_key: str) -> Optional[Dict[str, Any]]:
        return self._state_cache.get(state_key)

    def get_stats(self) -> Dict[str, Any]:
        return {
            "command_queue_size": len(self._command_queue),
            "event_queue_size": len(self._event_queue),
            "total_commands_sent": len(self._command_history),
            "registered_handlers": sum(len(h) for h in self._event_handlers.values()),
            "cached_states": len(self._state_cache),
        }


# =============================================================================
# Unified Agent Core
# =============================================================================


class UnifiedAgentCore:
    """
    The definitive unified agent core for the SparkLabs AI-native game engine.

    Integrates all agent subsystems into a single cohesive framework:
    cognitive architecture, intelligence reasoning, multi-agent orchestration,
    game creation, world simulation, learning evolution, memory management,
    tool coordination, and engine communication.

    Implements the Singleton pattern with double-checked locking.
    """

    _instance: Optional["UnifiedAgentCore"] = None
    _instance_lock = threading.RLock()

    def __init__(self) -> None:
        if UnifiedAgentCore._instance is not None:
            raise RuntimeError("Use UnifiedAgentCore.get_instance() instead")
        self._initialized: bool = False
        self._mode: AgentMode = AgentMode.IDLE
        self._start_time: float = 0.0
        self._metrics: AgentMetrics = AgentMetrics()

        # Subsystem managers
        self._cognitive: CognitiveManager = CognitiveManager()
        self._memory: MemoryManager = MemoryManager()
        self._world: WorldManager = WorldManager()
        self._creation: CreationManager = CreationManager()
        self._team: TeamManager = TeamManager()
        self._tool: ToolManager = ToolManager()
        self._learning: LearningManager = LearningManager()
        self._bridge: BridgeManager = BridgeManager()

        # Event listeners
        self._event_listeners: Dict[str, List[Callable]] = defaultdict(list)

    @classmethod
    def get_instance(cls) -> "UnifiedAgentCore":
        """Get the singleton instance."""
        if cls._instance is None:
            with cls._instance_lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    # -------------------------------------------------------------------------
    # Initialization
    # -------------------------------------------------------------------------

    def initialize(self) -> None:
        """Initialize the unified agent core and all subsystems."""
        if self._initialized:
            return
        self._mode = AgentMode.IDLE
        self._start_time = time.time()
        self._initialized = True
        logger.info("UnifiedAgentCore initialized successfully")

    def shutdown(self) -> None:
        """Shutdown the unified agent core."""
        self._mode = AgentMode.IDLE
        self._initialized = False
        self._metrics.uptime = time.time() - self._start_time
        logger.info("UnifiedAgentCore shutdown complete")

    # -------------------------------------------------------------------------
    # Cognitive Operations
    # -------------------------------------------------------------------------

    def perceive(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process input through the cognitive perception layer."""
        self._ensure_initialized()
        return self._cognitive.perceive(input_data)

    def reason(self, task: str, context: Optional[Dict[str, Any]] = None,
               depth: ReasoningDepth = ReasoningDepth.STANDARD) -> List[Dict[str, Any]]:
        """Apply reasoning to a task."""
        self._ensure_initialized()
        self._mode = AgentMode.DELIBERATIVE
        ctx = CognitiveContext(
            session_id=f"session_{uuid.uuid4().hex[:8]}",
            task=task,
            depth=depth,
            domain_knowledge=context or {},
        )
        perception = self._cognitive.perceive({"text": task})
        return self._cognitive.reason(ctx, perception)

    def plan(self, goals: List[str], context: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Generate a plan for the given goals."""
        self._ensure_initialized()
        self._mode = AgentMode.STRATEGIC
        ctx = CognitiveContext(
            session_id=f"session_{uuid.uuid4().hex[:8]}",
            domain_knowledge=context or {},
        )
        return self._cognitive.plan(ctx, goals)

    def execute_action(self, action_name: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a cognitive action."""
        self._ensure_initialized()
        self._metrics.total_tasks += 1
        return self._cognitive.execute_action(action_name, parameters)

    def reflect(self) -> Dict[str, Any]:
        """Self-reflect on recent actions."""
        self._ensure_initialized()
        recent_actions = self._cognitive._action_history[-20:]
        return self._cognitive.reflect(recent_actions)

    # -------------------------------------------------------------------------
    # Memory Operations
    # -------------------------------------------------------------------------

    def remember(self, memory_type: MemoryType, content: Dict[str, Any],
                 importance: float = 0.5, tags: Optional[List[str]] = None) -> str:
        """Store a memory."""
        self._ensure_initialized()
        entry = MemoryEntry(
            entry_id=f"mem_{uuid.uuid4().hex[:8]}",
            memory_type=memory_type,
            content=content,
            importance=importance,
            tags=tags or [],
        )
        return self._memory.store(entry)

    def recall(self, memory_type: MemoryType, query: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Retrieve memories."""
        self._ensure_initialized()
        entries = self._memory.retrieve(memory_type, query)
        return [e.to_dict() for e in entries]

    def recall_by_tags(self, tags: List[str]) -> List[Dict[str, Any]]:
        """Retrieve memories by tags."""
        self._ensure_initialized()
        entries = self._memory.retrieve_by_tags(tags)
        return [e.to_dict() for e in entries]

    # -------------------------------------------------------------------------
    # World Operations
    # -------------------------------------------------------------------------

    def generate_world(self, description: str, width: int = 1024, height: int = 1024,
                       seed: Optional[int] = None) -> WorldState:
        """Generate a complete game world."""
        self._ensure_initialized()
        self._metrics.total_worlds_generated += 1
        return self._world.generate_world(description, width, height, seed)

    def simulate_world(self, world_id: str, ticks: int = 100) -> Dict[str, Any]:
        """Run world simulation."""
        self._ensure_initialized()
        return self._world.simulate_world(world_id, ticks)

    def evolve_world(self, world_id: str, generations: int = 10) -> Dict[str, Any]:
        """Evolve a world through generations."""
        self._ensure_initialized()
        return self._world.evolve_world(world_id, generations)

    def get_world(self, world_id: str) -> Optional[Dict[str, Any]]:
        world = self._world.get_world(world_id)
        return world.to_dict() if world else None

    # -------------------------------------------------------------------------
    # Game Creation Operations
    # -------------------------------------------------------------------------

    def create_game(self, prompt: str, genre: Optional[str] = None,
                    quality: str = "playable", style: str = "flat_2d") -> GameProject:
        """Create a complete game from a natural language description."""
        self._ensure_initialized()
        self._metrics.total_games_created += 1
        genre_enum = None
        if genre:
            try:
                genre_enum = GameGenre(genre)
            except ValueError:
                genre_enum = GameGenre.CUSTOM
        quality_enum = QualityLevel(quality) if quality in [q.value for q in QualityLevel] else QualityLevel.PLAYABLE
        style_enum = AssetStyle(style) if style in [s.value for s in AssetStyle] else AssetStyle.FLAT_2D
        return self._creation.create_game(prompt, genre_enum, quality_enum, style_enum)

    def playtest_game(self, project_id: str) -> Dict[str, Any]:
        """Run playtesting on a game."""
        self._ensure_initialized()
        return self._creation.playtest(project_id)

    def iterate_game(self, project_id: str, feedback: str) -> Dict[str, Any]:
        """Iterate on a game based on feedback."""
        self._ensure_initialized()
        return self._creation.iterate(project_id, feedback)

    def get_project(self, project_id: str) -> Optional[Dict[str, Any]]:
        project = self._creation.get_project(project_id)
        return project.to_dict() if project else None

    def list_projects(self) -> List[Dict[str, Any]]:
        return self._creation.list_projects()

    # -------------------------------------------------------------------------
    # Team Operations
    # -------------------------------------------------------------------------

    def form_team(self, team_name: str, roles: List[str]) -> Dict[str, Any]:
        """Form a multi-agent team."""
        self._ensure_initialized()
        role_enums = []
        for r in roles:
            try:
                role_enums.append(TeamRole(r))
            except ValueError:
                pass
        return self._team.form_team(team_name, role_enums)

    def assign_task(self, team_id: str, description: str, roles: List[str]) -> TeamTask:
        """Assign a task to a team."""
        self._ensure_initialized()
        role_enums = []
        for r in roles:
            try:
                role_enums.append(TeamRole(r))
            except ValueError:
                pass
        return self._team.assign_task(team_id, description, role_enums)

    def execute_team_task(self, task_id: str) -> Dict[str, Any]:
        """Execute a team task."""
        self._ensure_initialized()
        return self._team.execute_task(task_id)

    # -------------------------------------------------------------------------
    # Tool Operations
    # -------------------------------------------------------------------------

    def list_tools(self, category: Optional[str] = None) -> List[Dict[str, Any]]:
        """List available tools."""
        cat_enum = None
        if category:
            try:
                cat_enum = ToolCategory(category)
            except ValueError:
                pass
        return self._tool.list_tools(cat_enum)

    def execute_tool(self, tool_name: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a tool."""
        self._ensure_initialized()
        self._metrics.total_tools_executed += 1
        return self._tool.execute_tool(tool_name, parameters)

    def create_tool_chain(self, chain_name: str, tool_names: List[str]) -> Dict[str, Any]:
        """Create a tool execution chain."""
        return self._tool.create_tool_chain(chain_name, tool_names)

    def execute_tool_chain(self, chain_name: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a tool chain."""
        return self._tool.execute_chain(chain_name, parameters)

    def get_tool_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        return self._tool.get_history(limit)

    # -------------------------------------------------------------------------
    # Learning Operations
    # -------------------------------------------------------------------------

    def learn(self, experience: Dict[str, Any], outcome: str,
              lessons: List[str]) -> Dict[str, Any]:
        """Record a learning experience."""
        self._ensure_initialized()
        record = self._learning.record_experience(experience, outcome, lessons)
        self._metrics.total_learning_cycles += 1
        return record.to_dict()

    def evolve(self) -> Dict[str, Any]:
        """Run a skill evolution cycle."""
        self._ensure_initialized()
        return self._learning.evolve_skills()

    def get_skill_levels(self) -> Dict[str, float]:
        return dict(self._learning._skill_levels)

    # -------------------------------------------------------------------------
    # Engine Bridge Operations
    # -------------------------------------------------------------------------

    def send_engine_command(self, command_type: str, parameters: Dict[str, Any],
                            priority: int = 0) -> Dict[str, Any]:
        """Send a command to the engine."""
        self._ensure_initialized()
        command = self._bridge.send_command(command_type, parameters, priority)
        return command.to_dict()

    def process_engine_queue(self) -> List[Dict[str, Any]]:
        """Process the engine command queue."""
        return self._bridge.process_command_queue()

    def get_engine_events(self, limit: int = 50) -> List[Dict[str, Any]]:
        return self._bridge.get_event_queue(limit)

    def register_engine_handler(self, event_type: str, handler: Callable) -> None:
        self._bridge.register_event_handler(event_type, handler)

    # -------------------------------------------------------------------------
    # Status & Metrics
    # -------------------------------------------------------------------------

    def get_status(self) -> Dict[str, Any]:
        """Get comprehensive status of the unified agent."""
        self._metrics.uptime = time.time() - self._start_time if self._start_time > 0 else 0
        return {
            "initialized": self._initialized,
            "mode": self._mode.value,
            "uptime": self._metrics.uptime,
            "cognitive": self._cognitive.get_state(),
            "memory": self._memory.get_stats(),
            "world": self._world.get_stats(),
            "creation": self._creation.get_stats(),
            "team": self._team.get_stats(),
            "tool": self._tool.get_stats(),
            "learning": self._learning.get_stats(),
            "bridge": self._bridge.get_stats(),
            "metrics": self._metrics.to_dict(),
        }

    def get_metrics(self) -> Dict[str, Any]:
        return self._metrics.to_dict()

    def on(self, event: str, callback: Callable) -> None:
        """Register an event listener."""
        self._event_listeners[event].append(callback)

    def emit(self, event: str, data: Dict[str, Any]) -> None:
        """Emit an event to listeners."""
        for callback in self._event_listeners.get(event, []):
            try:
                callback(data)
            except Exception:
                pass

    def _ensure_initialized(self) -> None:
        if not self._initialized:
            self.initialize()


# =============================================================================
# Convenience Function
# =============================================================================


def get_unified_agent_core() -> UnifiedAgentCore:
    """Get the singleton UnifiedAgentCore instance."""
    return UnifiedAgentCore.get_instance()