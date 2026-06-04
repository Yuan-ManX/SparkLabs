"""
SparkLabs Agent - Intent Router

LLM-driven intent routing and task decomposition system for the
SparkLabs AI-native game engine. Receives raw user intents,
classifies them against registered intent patterns, produces
routing decisions with confidence scores, and decomposes complex
intents into structured sub-task execution plans managed by
spawned sub-agents.

Architecture:
  AgentIntentRouter (singleton)
    |-- IntentPattern Registry (learnable pattern matching)
    |-- RoutingDecision Engine (confidence-ranked intent routing)
    |-- DecompositionPlanner (intent → sub-task plan generation)
    |-- SubAgentSpawner (isolated sub-agent lifecycle management)
    |-- RoutingOptimizer (path analysis and optimization)
    |-- StatsAggregator (telemetry and analytics)

Routing Strategies:
  - DIRECT:       route intent straight to a single module
  - DELEGATE:     hand off to a specialized sub-agent
  - PARALLEL:     fan out to multiple agents concurrently
  - CASCADE:      try primary module, fall back through chain
  - ROUND_ROBIN:  distribute across available modules evenly
  - CONTEXT_AWARE:choose routing based on session context
"""

from __future__ import annotations

import re
import threading
import time
import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


_time_module = time


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _generate_uid_stub() -> str:
    """Return a UUID4 hex string for unique identifier generation."""
    return uuid.uuid4().hex


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class IntentCategory(Enum):
    GAME_CREATION = "game_creation"
    ASSET_GENERATION = "asset_generation"
    LEVEL_DESIGN = "level_design"
    CHARACTER_CREATION = "character_creation"
    PHYSICS_SETUP = "physics_setup"
    AI_BEHAVIOR = "ai_behavior"
    AUDIO_DESIGN = "audio_design"
    UI_DESIGN = "ui_design"
    DEBUGGING = "debugging"
    OPTIMIZATION = "optimization"
    WORLD_BUILDING = "world_building"
    NARRATIVE_DESIGN = "narrative_design"
    CODE_GENERATION = "code_generation"
    TESTING = "testing"
    DEPLOYMENT = "deployment"


class SubAgentStatus(Enum):
    SPAWNED = "spawned"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMED_OUT = "timed_out"
    CANCELLED = "cancelled"


class RoutingStrategy(Enum):
    DIRECT = "direct"
    DELEGATE = "delegate"
    PARALLEL = "parallel"
    CASCADE = "cascade"
    ROUND_ROBIN = "round_robin"
    CONTEXT_AWARE = "context_aware"


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------


@dataclass
class IntentPattern:
    """Registered intent pattern used for matching and routing.

    Each pattern maps natural-language trigger phrases to a target
    module so the router can determine where to send a user intent.
    """

    intent_id: str = field(default_factory=_generate_uid_stub)
    name: str = ""
    description: str = ""
    trigger_phrases: List[str] = field(default_factory=list)
    target_module: str = ""
    action_type: str = ""
    parameters_schema: Dict[str, Any] = field(default_factory=dict)
    priority: int = 5
    confidence_threshold: float = 0.5
    usage_count: int = 0
    success_rate: float = 1.0
    avg_response_time: float = 0.0
    created_at: float = field(default_factory=_time_module.time)
    updated_at: float = field(default_factory=_time_module.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "intent_id": self.intent_id,
            "name": self.name,
            "description": self.description,
            "trigger_phrases": list(self.trigger_phrases),
            "target_module": self.target_module,
            "action_type": self.action_type,
            "parameters_schema": dict(self.parameters_schema),
            "priority": self.priority,
            "confidence_threshold": self.confidence_threshold,
            "usage_count": self.usage_count,
            "success_rate": self.success_rate,
            "avg_response_time": round(self.avg_response_time, 4),
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


@dataclass
class DecompositionPlan:
    """Structured plan that breaks a complex intent into sub-tasks.

    Each sub-task is a dict containing task_id, description, module,
    priority, dependencies, status, assigned_agent, result, start_time,
    and end_time. The plan tracks overall progress across all sub-tasks.
    """

    plan_id: str = field(default_factory=_generate_uid_stub)
    original_intent: str = ""
    sub_tasks: List[Dict[str, Any]] = field(default_factory=list)
    status: str = "pending"
    progress: float = 0.0
    created_at: float = field(default_factory=_time_module.time)
    completed_at: Optional[float] = None
    total_steps: int = 0
    completed_steps: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "plan_id": self.plan_id,
            "original_intent": self.original_intent,
            "sub_tasks": [dict(t) for t in self.sub_tasks],
            "status": self.status,
            "progress": round(self.progress, 3),
            "created_at": self.created_at,
            "completed_at": self.completed_at,
            "total_steps": self.total_steps,
            "completed_steps": self.completed_steps,
        }

    def _recompute_progress(self) -> None:
        self.total_steps = len(self.sub_tasks)
        self.completed_steps = sum(
            1 for t in self.sub_tasks if t.get("status") == "completed"
        )
        self.progress = (
            self.completed_steps / max(self.total_steps, 1)
        )


@dataclass
class RoutingDecision:
    """Result of analyzing input text against registered intent patterns.

    Contains the ranked list of matched intents with confidence scores,
    the selected primary module, fallback routing chain, and timestamp
    for traceability.
    """

    decision_id: str = field(default_factory=_generate_uid_stub)
    input_text: str = ""
    matched_intents: List[Dict[str, Any]] = field(default_factory=list)
    selected_module: str = ""
    fallback_modules: List[str] = field(default_factory=list)
    routing_path: RoutingStrategy = RoutingStrategy.DIRECT
    timestamp: float = field(default_factory=_time_module.time)
    user_feedback: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "decision_id": self.decision_id,
            "input_text": self.input_text[:200],
            "matched_intents": [dict(m) for m in self.matched_intents],
            "selected_module": self.selected_module,
            "fallback_modules": list(self.fallback_modules),
            "routing_path": self.routing_path.value,
            "timestamp": self.timestamp,
            "user_feedback": self.user_feedback,
        }


@dataclass
class SubAgentContext:
    """Context for a spawned sub-agent handling a single sub-task.

    Tracks the agent's lifecycle from spawn through completion or
    failure, with isolation guarantees and configurable timeout.
    """

    agent_id: str = field(default_factory=_generate_uid_stub)
    parent_plan_id: str = ""
    task_description: str = ""
    assigned_module: str = ""
    input_context: Dict[str, Any] = field(default_factory=dict)
    output_context: Dict[str, Any] = field(default_factory=dict)
    status: SubAgentStatus = SubAgentStatus.SPAWNED
    isolation_level: str = "process"
    timeout: float = 300.0
    spawned_at: float = field(default_factory=_time_module.time)
    completed_at: Optional[float] = None
    error_log: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "agent_id": self.agent_id,
            "parent_plan_id": self.parent_plan_id,
            "task_description": self.task_description,
            "assigned_module": self.assigned_module,
            "input_context": dict(self.input_context),
            "output_context": dict(self.output_context),
            "status": self.status.value,
            "isolation_level": self.isolation_level,
            "timeout": self.timeout,
            "spawned_at": self.spawned_at,
            "completed_at": self.completed_at,
            "error_log": self.error_log,
        }


# ---------------------------------------------------------------------------
# Category Keyword Index
# ---------------------------------------------------------------------------

_CATEGORY_KEYWORDS: Dict[IntentCategory, List[str]] = {
    IntentCategory.GAME_CREATION: [
        "create game", "new game", "make game", "build game",
        "start project", "game template", "scaffold game",
    ],
    IntentCategory.ASSET_GENERATION: [
        "asset", "sprite", "texture", "model", "material",
        "mesh", "generate asset", "create asset", "import model",
    ],
    IntentCategory.LEVEL_DESIGN: [
        "level", "map", "terrain", "layout", "tilemap",
        "design level", "build level", "create map", "dungeon",
    ],
    IntentCategory.CHARACTER_CREATION: [
        "character", "player", "npc", "enemy", "boss",
        "create character", "design character", "avatar",
    ],
    IntentCategory.PHYSICS_SETUP: [
        "physics", "collision", "gravity", "rigidbody",
        "velocity", "force", "collider", "trigger",
        "raycast", "joint", "constraint",
    ],
    IntentCategory.AI_BEHAVIOR: [
        "ai", "behavior", "pathfinding", "navmesh", "patrol",
        "state machine", "fsm", "behavior tree", "decision",
        "enemy ai", "npc behavior", "agent", "autonomous",
    ],
    IntentCategory.AUDIO_DESIGN: [
        "audio", "sound", "music", "sfx", "ambient",
        "voice", "background music", "sound effect",
        "audio source", "audio listener", "mixer",
    ],
    IntentCategory.UI_DESIGN: [
        "ui", "hud", "menu", "button", "panel",
        "dialog", "interface", "canvas", "screen",
        "widget", "layout", "overlay",
    ],
    IntentCategory.DEBUGGING: [
        "debug", "fix", "error", "bug", "crash",
        "issue", "problem", "broken", "trace", "log",
        "breakpoint", "inspect", "exception",
    ],
    IntentCategory.OPTIMIZATION: [
        "optimize", "performance", "fps", "frame rate",
        "memory", "profiling", "bottleneck", "lag",
        "stutter", "draw call", "batching", "lod",
        "culling", "reduce", "improve performance",
    ],
    IntentCategory.WORLD_BUILDING: [
        "world", "environment", "landscape", "biome",
        "open world", "procedural", "terrain generation",
        "world building", "zone", "area",
    ],
    IntentCategory.NARRATIVE_DESIGN: [
        "story", "narrative", "dialogue", "quest",
        "plot", "cutscene", "lore", "script",
        "branching", "choice", "conversation",
    ],
    IntentCategory.CODE_GENERATION: [
        "code", "script", "generate code", "class",
        "function", "component", "boilerplate",
        "template", "snippet", "implement",
    ],
    IntentCategory.TESTING: [
        "test", "qa", "assert", "unit test",
        "playtest", "simulate", "verify", "validate",
        "regression", "coverage",
    ],
    IntentCategory.DEPLOYMENT: [
        "deploy", "build", "publish", "release",
        "package", "export", "ship", "launch",
        "webgl", "mobile", "desktop", "console",
    ],
}


# ---------------------------------------------------------------------------
# AgentIntentRouter Singleton
# ---------------------------------------------------------------------------


class AgentIntentRouter:
    """LLM-driven intent routing and task decomposition.

    Maintains a registry of intent patterns that map natural-language
    triggers to target game-dev modules. Analyzes incoming text against
    those patterns, produces confidence-ranked routing decisions, and
    decomposes complex intents into sub-task plans executed by spawned
    sub-agents with configurable isolation levels and timeouts.

    Singleton – use get_instance() or the module-level accessor.
    """

    _instance: Optional[AgentIntentRouter] = None
    _lock = threading.RLock()

    MAX_PATTERNS = 1000
    MAX_PLANS = 500
    MAX_AGENTS = 5000
    MAX_HISTORY = 200

    def __new__(cls) -> AgentIntentRouter:
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    instance = super().__new__(cls)
                    cls._instance = instance
        return cls._instance

    @classmethod
    def get_instance(cls) -> AgentIntentRouter:
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    instance = super().__new__(cls)
                    instance.__init__()
                    cls._instance = instance
        return cls._instance

    def __init__(self) -> None:
        with self._lock:
            if hasattr(self, "_initialized") and self._initialized:
                return
            self._patterns: Dict[str, IntentPattern] = {}
            self._plans: Dict[str, DecompositionPlan] = {}
            self._agents: Dict[str, SubAgentContext] = {}
            self._decisions: List[RoutingDecision] = []
            self._decision_index: Dict[str, DecompositionPlan] = {}
            self._routing_stats: Dict[str, Any] = {
                "total_intents": 0,
                "active_plans": 0,
                "completed_plans": 0,
                "spawned_agents": 0,
                "avg_decomposition_time_ms": 0.0,
                "avg_routing_time_ms": 0.0,
                "total_decomposition_time_ms": 0.0,
                "total_routing_time_ms": 0.0,
                "intent_distribution": {c.value: 0 for c in IntentCategory},
                "strategy_distribution": {s.value: 0 for s in RoutingStrategy},
            }
            self._phrase_index: Dict[str, List[str]] = {}
            self._initialized = True

    # ------------------------------------------------------------------
    # Intent Pattern CRUD
    # ------------------------------------------------------------------

    def register_intent_pattern(
        self,
        name: str,
        description: str,
        trigger_phrases: List[str],
        target_module: str,
        action_type: str,
        parameters_schema: Optional[Dict[str, Any]] = None,
        priority: int = 5,
        confidence_threshold: float = 0.5,
    ) -> IntentPattern:
        """Register a new intent pattern in the routing registry."""
        with self._lock:
            if len(self._patterns) >= self.MAX_PATTERNS:
                raise RuntimeError(
                    f"Maximum pattern count ({self.MAX_PATTERNS}) reached."
                )

            pattern = IntentPattern(
                name=name,
                description=description,
                trigger_phrases=[p.lower().strip() for p in trigger_phrases],
                target_module=target_module,
                action_type=action_type,
                parameters_schema=parameters_schema or {},
                priority=max(0, min(priority, 10)),
                confidence_threshold=max(0.0, min(confidence_threshold, 1.0)),
            )

            self._patterns[pattern.intent_id] = pattern

            for phrase in pattern.trigger_phrases:
                words = self._tokenize(phrase)
                for word in words:
                    if word not in self._phrase_index:
                        self._phrase_index[word] = []
                    if pattern.intent_id not in self._phrase_index[word]:
                        self._phrase_index[word].append(pattern.intent_id)

            return pattern

    def update_intent_pattern(self, intent_id: str, **kwargs: Any) -> bool:
        """Update fields on an existing intent pattern by intent_id."""
        with self._lock:
            pattern = self._patterns.get(intent_id)
            if pattern is None:
                return False

            updatable = (
                "name", "description", "trigger_phrases", "target_module",
                "action_type", "parameters_schema", "priority",
                "confidence_threshold", "usage_count", "success_rate",
                "avg_response_time",
            )

            for key, value in kwargs.items():
                if key in updatable and hasattr(pattern, key):
                    if key == "trigger_phrases" and isinstance(value, list):
                        old_phrases = set(pattern.trigger_phrases)
                        new_phrases = [
                            p.lower().strip() for p in value
                        ]
                        setattr(pattern, key, new_phrases)

                        removed_phrases = old_phrases - set(new_phrases)
                        for phrase in removed_phrases:
                            words = self._tokenize(phrase)
                            for word in words:
                                if word in self._phrase_index:
                                    self._phrase_index[word] = [
                                        pid
                                        for pid in self._phrase_index[word]
                                        if pid != intent_id
                                    ]
                                    if not self._phrase_index[word]:
                                        del self._phrase_index[word]

                        for phrase in new_phrases:
                            if phrase not in old_phrases:
                                words = self._tokenize(phrase)
                                for word in words:
                                    if word not in self._phrase_index:
                                        self._phrase_index[word] = []
                                    if intent_id not in self._phrase_index[word]:
                                        self._phrase_index[word].append(intent_id)
                    else:
                        setattr(pattern, key, value)

            pattern.updated_at = _time_module.time()
            return True

    def delete_intent_pattern(self, intent_id: str) -> bool:
        """Remove an intent pattern from the registry."""
        with self._lock:
            pattern = self._patterns.pop(intent_id, None)
            if pattern is None:
                return False

            for phrase in pattern.trigger_phrases:
                words = self._tokenize(phrase)
                for word in words:
                    if word in self._phrase_index:
                        self._phrase_index[word] = [
                            pid
                            for pid in self._phrase_index[word]
                            if pid != intent_id
                        ]
                        if not self._phrase_index[word]:
                            del self._phrase_index[word]

            return True

    # ------------------------------------------------------------------
    # Intent Analysis & Routing
    # ------------------------------------------------------------------

    def analyze_intent(
        self,
        text: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> RoutingDecision:
        """Analyze input text against registered patterns and produce
        a confidence-ranked routing decision."""
        with self._lock:
            start_time = _time_module.time()
            ctx = context or {}
            text_lower = text.lower().strip()
            text_words = set(self._tokenize(text_lower))

            decision = RoutingDecision(
                input_text=text,
                routing_path=ctx.get("preferred_strategy", RoutingStrategy.DIRECT),
            )

            candidates: List[Dict[str, Any]] = []

            for pattern in self._patterns.values():
                phrase_score = 0.0

                for phrase in pattern.trigger_phrases:
                    similarity = self._sequence_similarity(text_lower, phrase)
                    phrase_score = max(phrase_score, similarity)

                keyword_score = 0.0
                phrase_words: set = set()
                for phrase in pattern.trigger_phrases:
                    phrase_words.update(self._tokenize(phrase))
                if phrase_words:
                    keyword_hits = len(text_words & phrase_words)
                    keyword_score = keyword_hits / max(len(phrase_words), 1)

                combined_score = phrase_score * 0.6 + keyword_score * 0.3
                combined_score += pattern.priority * 0.01
                combined_score = min(combined_score, 0.99)

                if combined_score >= pattern.confidence_threshold:
                    candidates.append({
                        "intent_id": pattern.intent_id,
                        "confidence": round(combined_score, 4),
                        "reasoning": (
                            f"phrase_score={phrase_score:.3f}, "
                            f"keyword_score={keyword_score:.3f}, "
                            f"priority={pattern.priority}"
                        ),
                    })

            candidates.sort(key=lambda c: c["confidence"], reverse=True)
            decision.matched_intents = candidates[:10]

            if candidates:
                best = candidates[0]
                best_pattern = self._patterns.get(best["intent_id"])
                if best_pattern:
                    decision.selected_module = best_pattern.target_module
                    best_pattern.usage_count += 1

                fallback_candidates = candidates[1:6]
                decision.fallback_modules = [
                    self._patterns[c["intent_id"]].target_module
                    for c in fallback_candidates
                    if c["intent_id"] in self._patterns
                ]

            routing_time_ms = (_time_module.time() - start_time) * 1000.0

            self._routing_stats["total_intents"] += 1
            self._routing_stats["total_routing_time_ms"] += routing_time_ms
            self._routing_stats["avg_routing_time_ms"] = round(
                self._routing_stats["total_routing_time_ms"]
                / max(self._routing_stats["total_intents"], 1),
                3,
            )

            if candidates:
                best_pattern = self._patterns.get(candidates[0]["intent_id"])
                if best_pattern:
                    cat = self._classify_intent_category(best_pattern.trigger_phrases)
                    self._routing_stats["intent_distribution"][cat.value] += 1

            self._routing_stats["strategy_distribution"][
                decision.routing_path.value
            ] += 1

            self._decisions.append(decision)
            if len(self._decisions) > self.MAX_HISTORY:
                self._decisions = self._decisions[-self.MAX_HISTORY:]

            return decision

    # ------------------------------------------------------------------
    # Decomposition
    # ------------------------------------------------------------------

    def decompose_intent(
        self,
        decision_id: str,
        max_subtasks: int = 10,
    ) -> DecompositionPlan:
        """Break a routing decision into a structured sub-task plan."""
        with self._lock:
            if len(self._plans) >= self.MAX_PLANS:
                raise RuntimeError(
                    f"Maximum plan count ({self.MAX_PLANS}) reached."
                )

            start_time = _time_module.time()

            decision = next(
                (d for d in self._decisions if d.decision_id == decision_id),
                None,
            )

            original_intent = decision.input_text if decision else ""

            plan = DecompositionPlan(
                original_intent=original_intent,
                status="in_progress",
            )

            modules_seen: set = set()
            for match in (decision.matched_intents if decision else []):
                pattern = self._patterns.get(match["intent_id"])
                if pattern and pattern.target_module not in modules_seen:
                    modules_seen.add(pattern.target_module)

            if decision and decision.selected_module:
                modules_seen.add(decision.selected_module)

            if not modules_seen:
                modules_seen.add("general_agent")

            module_list = list(modules_seen)[:max_subtasks]
            subtask_count = min(
                max_subtasks, max(1, len(module_list))
            )

            for i in range(subtask_count):
                module = (
                    module_list[i]
                    if i < len(module_list)
                    else module_list[i % len(module_list)]
                )
                task_id = _generate_uid_stub()
                dependencies: List[str] = []
                if i > 0:
                    dependencies.append(plan.sub_tasks[i - 1]["task_id"])

                sub_task = {
                    "task_id": task_id,
                    "description": f"Sub-task {i + 1}: route to {module}",
                    "module": module,
                    "priority": 5 - i,
                    "dependencies": dependencies,
                    "status": "pending",
                    "assigned_agent": "",
                    "result": None,
                    "start_time": None,
                    "end_time": None,
                }
                plan.sub_tasks.append(sub_task)

            plan._recompute_progress()

            self._plans[plan.plan_id] = plan
            self._decision_index[decision_id] = plan

            self._routing_stats["active_plans"] += 1

            decomposition_time_ms = (
                _time_module.time() - start_time
            ) * 1000.0
            self._routing_stats["total_decomposition_time_ms"] += (
                decomposition_time_ms
            )
            total_decompositions = max(
                self._routing_stats["completed_plans"]
                + self._routing_stats["active_plans"],
                1,
            )
            self._routing_stats["avg_decomposition_time_ms"] = round(
                self._routing_stats["total_decomposition_time_ms"]
                / total_decompositions,
                3,
            )

            return plan

    # ------------------------------------------------------------------
    # Sub-Task Management
    # ------------------------------------------------------------------

    def assign_sub_task(
        self, plan_id: str, task_id: str, module: str
    ) -> bool:
        """Assign a sub-task within a plan to a target module."""
        with self._lock:
            plan = self._plans.get(plan_id)
            if plan is None:
                return False

            for task in plan.sub_tasks:
                if task["task_id"] == task_id:
                    task["module"] = module
                    task["status"] = "assigned"
                    plan._recompute_progress()
                    return True

            return False

    def get_sub_task_status(self, plan_id: str, task_id: str) -> Dict[str, Any]:
        """Retrieve the status dict for a specific sub-task."""
        with self._lock:
            plan = self._plans.get(plan_id)
            if plan is None:
                return {"error": "Plan not found"}

            for task in plan.sub_tasks:
                if task["task_id"] == task_id:
                    return dict(task)

            return {"error": "Sub-task not found"}

    def complete_sub_task(
        self, plan_id: str, task_id: str, result: Any
    ) -> bool:
        """Mark a sub-task as completed and store its result."""
        with self._lock:
            plan = self._plans.get(plan_id)
            if plan is None:
                return False

            for task in plan.sub_tasks:
                if task["task_id"] == task_id:
                    task["status"] = "completed"
                    task["result"] = result
                    task["end_time"] = _time_module.time()
                    plan._recompute_progress()

                    if plan.completed_steps >= plan.total_steps:
                        plan.status = "completed"
                        plan.completed_at = _time_module.time()
                        self._routing_stats["active_plans"] = max(
                            0, self._routing_stats["active_plans"] - 1
                        )
                        self._routing_stats["completed_plans"] += 1

                    return True

            return False

    # ------------------------------------------------------------------
    # Sub-Agent Lifecycle
    # ------------------------------------------------------------------

    def spawn_sub_agent(
        self,
        plan_id: str,
        task_id: str,
        isolation_level: str = "process",
    ) -> SubAgentContext:
        """Spawn a sub-agent to execute a specific sub-task in isolation."""
        with self._lock:
            if len(self._agents) >= self.MAX_AGENTS:
                raise RuntimeError(
                    f"Maximum agent count ({self.MAX_AGENTS}) reached."
                )

            plan = self._plans.get(plan_id)
            task_desc = ""
            assigned_module = "general_agent"

            if plan is not None:
                for task in plan.sub_tasks:
                    if task["task_id"] == task_id:
                        task_desc = task["description"]
                        assigned_module = task["module"]
                        task["status"] = "in_progress"
                        task["start_time"] = _time_module.time()
                        plan._recompute_progress()
                        break

            agent = SubAgentContext(
                parent_plan_id=plan_id,
                task_description=task_desc,
                assigned_module=assigned_module,
                isolation_level=isolation_level,
            )

            self._agents[agent.agent_id] = agent

            if plan is not None:
                for task in plan.sub_tasks:
                    if task["task_id"] == task_id:
                        task["assigned_agent"] = agent.agent_id
                        break

            self._routing_stats["spawned_agents"] += 1

            return agent

    def await_sub_agent(
        self, agent_id: str, timeout: float = 300.0
    ) -> SubAgentContext:
        """Wait for a sub-agent to complete, or time out.

        In production this would integrate with a real sub-process or
        async agent runtime. Here we mark the agent as COMPLETED after
        checking timeout logic against spawned_at.
        """
        with self._lock:
            agent = self._agents.get(agent_id)
            if agent is None:
                raise ValueError(f"Sub-agent {agent_id} not found.")

            elapsed = _time_module.time() - agent.spawned_at

            if elapsed >= timeout:
                agent.status = SubAgentStatus.TIMED_OUT
                agent.completed_at = _time_module.time()
                agent.error_log = (
                    f"Timed out after {elapsed:.1f}s (limit: {timeout}s)."
                )
                return agent

            agent.status = SubAgentStatus.COMPLETED
            agent.completed_at = _time_module.time()

            if agent.parent_plan_id:
                plan = self._plans.get(agent.parent_plan_id)
                if plan is not None:
                    cycle_completed = False
                    for task in plan.sub_tasks:
                        if task["assigned_agent"] == agent_id:
                            task["status"] = "completed"
                            task["end_time"] = _time_module.time()
                            task["result"] = agent.output_context
                            cycle_completed = True
                    if cycle_completed:
                        plan._recompute_progress()

            return agent

    def cancel_sub_agent(self, agent_id: str) -> bool:
        """Cancel a running sub-agent."""
        with self._lock:
            agent = self._agents.get(agent_id)
            if agent is None:
                return False

            agent.status = SubAgentStatus.CANCELLED
            agent.completed_at = _time_module.time()
            agent.error_log = "Cancelled by request."

            if agent.parent_plan_id:
                plan = self._plans.get(agent.parent_plan_id)
                if plan is not None:
                    for task in plan.sub_tasks:
                        if task["assigned_agent"] == agent_id:
                            task["status"] = "cancelled"
                            task["end_time"] = _time_module.time()
                            plan._recompute_progress()

            return True

    # ------------------------------------------------------------------
    # Plan Progress
    # ------------------------------------------------------------------

    def get_plan_progress(self, plan_id: str) -> Dict[str, Any]:
        """Return a progress snapshot for a decomposition plan."""
        with self._lock:
            plan = self._plans.get(plan_id)
            if plan is None:
                return {"error": "Plan not found"}

            status_breakdown: Dict[str, int] = defaultdict(int)
            for task in plan.sub_tasks:
                status_breakdown[task.get("status", "unknown")] += 1

            return {
                "plan_id": plan.plan_id,
                "original_intent": plan.original_intent[:200],
                "status": plan.status,
                "progress": round(plan.progress, 3),
                "total_steps": plan.total_steps,
                "completed_steps": plan.completed_steps,
                "status_breakdown": dict(status_breakdown),
                "created_at": plan.created_at,
                "completed_at": plan.completed_at,
            }

    # ------------------------------------------------------------------
    # Routing Stats & Analytics
    # ------------------------------------------------------------------

    def get_routing_stats(self) -> Dict[str, Any]:
        """Return aggregated routing telemetry."""
        with self._lock:
            intent_dist = dict(self._routing_stats["intent_distribution"])
            top_intents = sorted(
                intent_dist.items(), key=lambda x: x[1], reverse=True
            )[:10]

            return {
                "total_intents": self._routing_stats["total_intents"],
                "active_plans": self._routing_stats["active_plans"],
                "completed_plans": self._routing_stats["completed_plans"],
                "spawned_agents": self._routing_stats["spawned_agents"],
                "avg_decomposition_time_ms": self._routing_stats[
                    "avg_decomposition_time_ms"
                ],
                "avg_routing_time_ms": self._routing_stats[
                    "avg_routing_time_ms"
                ],
                "intent_distribution": [
                    {"category": cat, "count": cnt}
                    for cat, cnt in top_intents
                ],
                "strategy_distribution": dict(
                    self._routing_stats["strategy_distribution"]
                ),
                "total_patterns": len(self._patterns),
                "total_plans": len(self._plans),
                "total_agents": len(self._agents),
                "generated_at": _time_module.time(),
            }

    # ------------------------------------------------------------------
    # Pattern Suggestion
    # ------------------------------------------------------------------

    def suggest_intent_patterns(
        self, text_samples: List[str]
    ) -> List[Dict[str, Any]]:
        """Suggest new intent patterns by analyzing sample text that
        currently have low-confidence routing matches."""
        with self._lock:
            suggestions: List[Dict[str, Any]] = []

            for text in text_samples:
                decision = self.analyze_intent(text)
                if (
                    not decision.matched_intents
                    or decision.matched_intents[0]["confidence"] < 0.4
                ):
                    category = self._classify_intent_category([text])
                    suggestion = {
                        "suggested_name": f"intent_{_generate_uid_stub()[:8]}",
                        "description": f"Auto-suggested pattern for: {text[:80]}",
                        "trigger_phrases": [text.lower().strip()],
                        "target_module": self._default_module_for_category(
                            category
                        ),
                        "action_type": "auto",
                        "suggested_priority": 3,
                        "suggested_confidence_threshold": 0.3,
                        "reason": (
                            f"Low confidence ({decision.matched_intents[0]['confidence']:.2f})"
                            if decision.matched_intents
                            else "No patterns matched"
                        ),
                        "category": category.value,
                    }
                    suggestions.append(suggestion)

            return suggestions

    # ------------------------------------------------------------------
    # Routing Optimization
    # ------------------------------------------------------------------

    def optimize_routing_paths(self) -> Dict[str, Any]:
        """Analyze routing history and suggest optimized paths."""
        with self._lock:
            original_routes: List[str] = []
            optimized_routes: List[str] = []
            total_improvement = 0.0

            module_performance: Dict[str, List[float]] = defaultdict(list)

            for pattern in self._patterns.values():
                if pattern.usage_count > 0:
                    module_performance[pattern.target_module].append(
                        pattern.success_rate
                    )

            for decision in self._decisions[-50:]:
                original_routes.append(
                    f"{decision.selected_module} via {decision.routing_path.value}"
                )

                better_module = decision.selected_module
                for match in decision.matched_intents:
                    pattern = self._patterns.get(match["intent_id"])
                    if (
                        pattern
                        and pattern.success_rate > 0.8
                        and pattern.avg_response_time < 500.0
                    ):
                        better_module = pattern.target_module
                        break

                if better_module != decision.selected_module:
                    optimized_routes.append(
                        f"{better_module} via {RoutingStrategy.CONTEXT_AWARE.value}"
                    )
                    total_improvement += (
                        decision.matched_intents[0]["confidence"]
                        if decision.matched_intents
                        else 0.0
                    )
                else:
                    optimized_routes.append(
                        f"{decision.selected_module} (already optimal)"
                    )

            return {
                "original_routes": original_routes[-20:],
                "optimized_routes": optimized_routes[-20:],
                "estimated_improvement": round(total_improvement, 4),
                "routes_analyzed": len(original_routes),
                "routes_improved": len(optimized_routes)
                - optimized_routes.count(
                    optimized_routes[0] if optimized_routes else ""
                ),
            }

    # ------------------------------------------------------------------
    # Reset
    # ------------------------------------------------------------------

    def reset(self) -> None:
        """Clear all state – patterns, plans, agents, history, and stats."""
        with self._lock:
            self._patterns.clear()
            self._plans.clear()
            self._agents.clear()
            self._decisions.clear()
            self._decision_index.clear()
            self._phrase_index.clear()
            self._routing_stats = {
                "total_intents": 0,
                "active_plans": 0,
                "completed_plans": 0,
                "spawned_agents": 0,
                "avg_decomposition_time_ms": 0.0,
                "avg_routing_time_ms": 0.0,
                "total_decomposition_time_ms": 0.0,
                "total_routing_time_ms": 0.0,
                "intent_distribution": {c.value: 0 for c in IntentCategory},
                "strategy_distribution": {s.value: 0 for s in RoutingStrategy},
            }

    # ------------------------------------------------------------------
    # Internal Helpers
    # ------------------------------------------------------------------

    def _classify_intent_category(
        self, trigger_phrases: List[str]
    ) -> IntentCategory:
        """Classify which IntentCategory best matches a set of phrases."""
        all_text = " ".join(trigger_phrases).lower()
        scores: Dict[IntentCategory, int] = defaultdict(int)

        for category, keywords in _CATEGORY_KEYWORDS.items():
            for kw in keywords:
                if kw in all_text:
                    scores[category] += 1

        if not scores:
            return IntentCategory.GAME_CREATION

        return max(scores, key=scores.get)

    def _default_module_for_category(
        self, category: IntentCategory
    ) -> str:
        """Return a sensible default target module for a category."""
        default_map: Dict[IntentCategory, str] = {
            IntentCategory.GAME_CREATION: "game_designer",
            IntentCategory.ASSET_GENERATION: "asset_synthesizer",
            IntentCategory.LEVEL_DESIGN: "level_designer",
            IntentCategory.CHARACTER_CREATION: "character_creator",
            IntentCategory.PHYSICS_SETUP: "physics_tuner",
            IntentCategory.AI_BEHAVIOR: "behavior_designer",
            IntentCategory.AUDIO_DESIGN: "audio_composer",
            IntentCategory.UI_DESIGN: "ui_designer",
            IntentCategory.DEBUGGING: "debug_agent",
            IntentCategory.OPTIMIZATION: "performance_advisor",
            IntentCategory.WORLD_BUILDING: "world_builder",
            IntentCategory.NARRATIVE_DESIGN: "narrative_composer",
            IntentCategory.CODE_GENERATION: "code_generator",
            IntentCategory.TESTING: "game_testing",
            IntentCategory.DEPLOYMENT: "build_orchestrator",
        }
        return default_map.get(category, "general_agent")

    def _sequence_similarity(self, text: str, pattern: str) -> float:
        """Compute a fast similarity between text and a pattern phrase."""
        text_words = set(self._tokenize(text))
        pattern_words = set(self._tokenize(pattern))

        if not pattern_words:
            return 0.0

        intersection = text_words & pattern_words
        jaccard = len(intersection) / max(
            len(text_words | pattern_words), 1
        )

        if pattern in text:
            containment_bonus = 0.3
        else:
            containment_bonus = 0.0

        word_order_score = 0.0
        pattern_tokens = self._tokenize(pattern)
        text_tokens = self._tokenize(text)
        if len(pattern_tokens) >= 2 and len(text_tokens) >= 2:
            matches_in_order = 0
            ti = 0
            for pt in pattern_tokens:
                while ti < len(text_tokens):
                    if text_tokens[ti] == pt:
                        matches_in_order += 1
                        ti += 1
                        break
                    ti += 1
            word_order_score = matches_in_order / max(len(pattern_tokens), 1)

        return min(
            jaccard * 0.4 + containment_bonus + word_order_score * 0.3, 1.0
        )

    @staticmethod
    def _tokenize(text: str) -> List[str]:
        """Extract lowercase alphanumeric tokens from text."""
        return re.findall(r"[a-z0-9]{2,}", text.lower())


# ---------------------------------------------------------------------------
# Module-Level Accessor
# ---------------------------------------------------------------------------


def get_agent_intent_router() -> AgentIntentRouter:
    """Return the singleton AgentIntentRouter instance."""
    return AgentIntentRouter.get_instance()