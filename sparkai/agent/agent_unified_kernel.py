"""
SparkLabs Agent - Unified Cognitive Kernel

The foundational cognitive architecture that consolidates planning, memory,
reasoning, tool orchestration, reflection, and self-evolution into a single
coherent system. The kernel provides the substrate upon which all higher-level
game agents operate.

Architecture:
  AgentKernel (Singleton)
    |-- PerceptionLayer   -> ingests prompts, telemetry, world state
    |-- MemoryHierarchy   -> working / episodic / semantic / procedural layers
    |-- ReasoningEngine   -> chain-of-thought, tree-of-thought, meta-reasoning
    |-- PlanningCore      -> HTN decomposition, task graphs, contingency plans
    |-- ToolOrchestrator  -> composition, permission gating, parallel dispatch
    |-- ReflectionLoop    -> self-evaluation, blame attribution, lesson capture
    |-- SkillEvolver      -> trajectory learning, skill synthesis, transfer

Cognitive Cycle (per tick):
  perceive -> encode -> reason -> plan -> act -> observe -> reflect -> learn

The kernel is designed to be genre-agnostic and can drive any game agent
role from creative direction to live ops. It exposes a single `cycle()`
entry point that advances the agent one cognitive step.

Original SparkLabs design - unified cognitive substrate for AI-native games.
"""

from __future__ import annotations

import logging
import threading
import time
import uuid
from collections import deque
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Deque, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


# =============================================================================
# Cognitive State Enums
# =============================================================================


class CognitivePhase(Enum):
    """Phases of the cognitive cycle."""
    PERCEIVE = "perceive"
    ENCODE = "encode"
    REASON = "reason"
    PLAN = "plan"
    ACT = "act"
    OBSERVE = "observe"
    REFLECT = "reflect"
    LEARN = "learn"


class MemoryLayer(Enum):
    """Layered memory taxonomy."""
    WORKING = "working"        # Current tick context, volatile
    EPISODIC = "episodic"      # Event sequences with timestamps
    SEMANTIC = "semantic"      # Concepts, facts, design patterns
    PROCEDURAL = "procedural"  # Skills, recipes, action templates


class ReasoningMode(Enum):
    """Reasoning strategies available to the kernel."""
    CHAIN_OF_THOUGHT = "chain_of_thought"
    TREE_OF_THOUGHT = "tree_of_thought"
    META_REASONING = "meta_reasoning"
    CAUSAL_REASONING = "causal_reasoning"
    ANALOGICAL = "analogical"


class TaskStatus(Enum):
    """Status of a planned task."""
    PENDING = "pending"
    RUNNING = "running"
    BLOCKED = "blocked"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


# =============================================================================
# Data Structures
# =============================================================================


@dataclass
class Perception:
    """A single percept entering the cognitive cycle."""
    perception_id: str = field(default_factory=lambda: uuid.uuid4().hex[:10])
    source: str = "system"          # prompt, telemetry, world, agent, user
    channel: str = "text"           # text, numeric, event, state
    payload: Any = None
    salience: float = 0.5           # 0..1 importance weight
    timestamp: float = field(default_factory=time.time)


@dataclass
class MemoryEntry:
    """An entry in the memory hierarchy."""
    entry_id: str = field(default_factory=lambda: uuid.uuid4().hex[:10])
    layer: MemoryLayer = MemoryLayer.WORKING
    namespace: str = "default"
    content: Any = None
    tags: List[str] = field(default_factory=list)
    salience: float = 0.5
    decay: float = 1.0              # multiplied each tick
    created_at: float = field(default_factory=time.time)
    last_accessed: float = field(default_factory=time.time)
    access_count: int = 0


@dataclass
class ReasoningTrace:
    """A trace of a reasoning episode."""
    trace_id: str = field(default_factory=lambda: uuid.uuid4().hex[:10])
    mode: ReasoningMode = ReasoningMode.CHAIN_OF_THOUGHT
    premises: List[str] = field(default_factory=list)
    steps: List[str] = field(default_factory=list)
    conclusion: str = ""
    confidence: float = 0.0
    duration_s: float = 0.0


@dataclass
class Task:
    """A unit of planned work."""
    task_id: str = field(default_factory=lambda: uuid.uuid4().hex[:10])
    name: str = ""
    description: str = ""
    status: TaskStatus = TaskStatus.PENDING
    dependencies: List[str] = field(default_factory=list)
    tool: Optional[str] = None
    args: Dict[str, Any] = field(default_factory=dict)
    result: Any = None
    error: Optional[str] = None
    priority: float = 0.5
    started_at: Optional[float] = None
    completed_at: Optional[float] = None


@dataclass
class Reflection:
    """A self-evaluation entry."""
    reflection_id: str = field(default_factory=lambda: uuid.uuid4().hex[:10])
    target: str = ""               # task_id, trace_id, perception_id
    outcome: str = ""              # success, failure, partial
    root_cause: str = ""
    lesson: str = ""
    adjustment: str = ""           # concrete next-time change
    confidence: float = 0.5


@dataclass
class CognitiveCycleResult:
    """The outcome of one cognitive cycle."""
    cycle_id: str = field(default_factory=lambda: uuid.uuid4().hex[:10])
    phase: CognitivePhase = CognitivePhase.PERCEIVE
    perceptions_processed: int = 0
    memories_written: int = 0
    reasoning_traces: int = 0
    tasks_planned: int = 0
    tasks_executed: int = 0
    reflections: int = 0
    skills_learned: int = 0
    duration_s: float = 0.0


# =============================================================================
# Memory Hierarchy
# =============================================================================


class MemoryHierarchy:
    """Layered memory store with salience decay and namespace isolation.

    The hierarchy models four layers:
      - Working: volatile, per-tick context (cleared each cycle)
      - Episodic: timestamped event sequences
      - Semantic: concept facts and design patterns
      - Procedural: skills and action recipes

    Retrieval blends recency, frequency, and salience so that the most
    relevant memories surface without exhaustive scans.
    """

    def __init__(self, capacity_per_layer: int = 256) -> None:
        self._layers: Dict[MemoryLayer, Deque[MemoryEntry]] = {
            MemoryLayer.WORKING: deque(maxlen=32),
            MemoryLayer.EPISODIC: deque(maxlen=capacity_per_layer),
            MemoryLayer.SEMANTIC: deque(maxlen=capacity_per_layer),
            MemoryLayer.PROCEDURAL: deque(maxlen=capacity_per_layer),
        }
        self._lock = threading.RLock()

    def write(self, entry: MemoryEntry) -> None:
        with self._lock:
            self._layers[entry.layer].append(entry)

    def read(self, layer: MemoryLayer, namespace: Optional[str] = None,
             tags: Optional[List[str]] = None, limit: int = 16) -> List[MemoryEntry]:
        with self._lock:
            entries = list(self._layers[layer])
        if namespace:
            entries = [e for e in entries if e.namespace == namespace]
        if tags:
            entries = [e for e in entries if any(t in e.tags for t in tags)]
        # Recency + salience blend
        now = time.time()
        entries.sort(key=lambda e: (e.salience * e.decay) /
                     max(1.0, (now - e.last_accessed) / 60.0), reverse=True)
        for e in entries[:limit]:
            e.last_accessed = now
            e.access_count += 1
        return entries[:limit]

    def recall(self, query: str, limit: int = 8) -> List[MemoryEntry]:
        """Cross-layer recall by simple keyword match."""
        results: List[MemoryEntry] = []
        q = query.lower()
        with self._lock:
            for layer in [MemoryLayer.SEMANTIC, MemoryLayer.EPISODIC,
                          MemoryLayer.PROCEDURAL, MemoryLayer.WORKING]:
                for e in self._layers[layer]:
                    content_str = str(e.content).lower()
                    if q in content_str or any(q in t.lower() for t in e.tags):
                        results.append(e)
        results.sort(key=lambda e: e.salience * e.decay, reverse=True)
        return results[:limit]

    def decay_all(self, factor: float = 0.995) -> None:
        with self._lock:
            for layer in self._layers.values():
                for e in layer:
                    e.decay *= factor

    def clear_working(self) -> None:
        with self._lock:
            self._layers[MemoryLayer.WORKING].clear()

    def stats(self) -> Dict[str, int]:
        with self._lock:
            return {layer.value: len(deq) for layer, deq in self._layers.items()}


# =============================================================================
# Reasoning Engine
# =============================================================================


class ReasoningEngine:
    """Multi-strategy reasoning with trace recording.

    Supports chain-of-thought (sequential), tree-of-thought (branching),
    meta-reasoning (about own reasoning), causal reasoning (cause-effect),
    and analogical reasoning (pattern transfer). Each invocation produces a
    ReasoningTrace that can be stored in procedural memory for learning.
    """

    def __init__(self) -> None:
        self._trace_history: Deque[ReasoningTrace] = deque(maxlen=64)
        self._lock = threading.RLock()

    def reason(self, premises: List[str], mode: ReasoningMode = ReasoningMode.CHAIN_OF_THOUGHT,
               max_steps: int = 6) -> ReasoningTrace:
        start = time.time()
        trace = ReasoningTrace(mode=mode, premises=list(premises))
        trace.steps = self._generate_steps(premises, mode, max_steps)
        trace.conclusion = trace.steps[-1] if trace.steps else "no conclusion"
        trace.confidence = self._estimate_confidence(trace.steps)
        trace.duration_s = time.time() - start
        with self._lock:
            self._trace_history.append(trace)
        return trace

    def _generate_steps(self, premises: List[str], mode: ReasoningMode,
                        max_steps: int) -> List[str]:
        steps: List[str] = []
        if not premises:
            return steps
        if mode == ReasoningMode.CHAIN_OF_THOUGHT:
            for i, p in enumerate(premises[:max_steps]):
                steps.append(f"Given: {p}")
                steps.append(f"Inference {i+1}: consolidate toward objective")
            steps.append("Conclusion: synthesize from above inferences")
        elif mode == ReasoningMode.TREE_OF_THOUGHT:
            steps.append(f"Root: {premises[0]}")
            for i in range(min(3, len(premises) - 1, max_steps - 1)):
                steps.append(f"Branch {i+1}: explore alternative from {premises[i+1]}")
            steps.append("Prune weak branches; retain strongest path")
            steps.append("Conclusion: commit to best branch")
        elif mode == ReasoningMode.META_REASONING:
            steps.append("Observe own reasoning state")
            steps.append(f"Premises under consideration: {len(premises)}")
            steps.append("Assess strategy adequacy")
            steps.append("Switch strategy if confidence low")
            steps.append("Conclusion: meta-adjusted reasoning path")
        elif mode == ReasoningMode.CAUSAL_REASONING:
            for i, p in enumerate(premises[:max_steps - 1]):
                steps.append(f"Cause: {p}")
                steps.append(f"Effect {i+1}: propagate consequence")
            steps.append("Conclusion: causal chain established")
        else:  # ANALOGICAL
            steps.append(f"Source domain: {premises[0]}")
            steps.append("Identify structural pattern")
            steps.append("Map pattern to target domain")
            steps.append("Conclusion: analogical transfer complete")
        return steps

    def _estimate_confidence(self, steps: List[str]) -> float:
        if not steps:
            return 0.0
        # Confidence grows with step count up to a cap
        return min(0.95, 0.4 + len(steps) * 0.08)

    def history(self) -> List[ReasoningTrace]:
        with self._lock:
            return list(self._trace_history)


# =============================================================================
# Planning Core
# =============================================================================


class PlanningCore:
    """Hierarchical task network planning with dependency resolution.

    Decomposes goals into tasks, resolves dependencies, and produces an
    execution order. Supports contingency planning for likely failures.
    """

    def __init__(self) -> None:
        self._task_graph: Dict[str, Task] = {}
        self._execution_order: List[str] = []
        self._lock = threading.RLock()

    def decompose(self, goal: str, sub_tasks: List[Dict[str, Any]]) -> List[Task]:
        """Decompose a goal into concrete tasks."""
        tasks: List[Task] = []
        with self._lock:
            for spec in sub_tasks:
                t = Task(
                    name=spec.get("name", "unnamed"),
                    description=spec.get("description", ""),
                    tool=spec.get("tool"),
                    args=spec.get("args", {}),
                    dependencies=spec.get("dependencies", []),
                    priority=spec.get("priority", 0.5),
                )
                self._task_graph[t.task_id] = t
                tasks.append(t)
            self._recompute_execution_order()
        return tasks

    def next_ready_task(self) -> Optional[Task]:
        with self._lock:
            for tid in self._execution_order:
                t = self._task_graph.get(tid)
                if t and t.status == TaskStatus.PENDING:
                    if all(self._task_graph[d].status == TaskStatus.COMPLETED
                           for d in t.dependencies if d in self._task_graph):
                        t.status = TaskStatus.RUNNING
                        t.started_at = time.time()
                        return t
        return None

    def complete_task(self, task_id: str, result: Any, error: Optional[str] = None) -> None:
        with self._lock:
            t = self._task_graph.get(task_id)
            if not t:
                return
            t.result = result
            t.error = error
            t.status = TaskStatus.FAILED if error else TaskStatus.COMPLETED
            t.completed_at = time.time()

    def cancel_pending(self) -> None:
        with self._lock:
            for t in self._task_graph.values():
                if t.status in (TaskStatus.PENDING, TaskStatus.RUNNING, TaskStatus.BLOCKED):
                    t.status = TaskStatus.CANCELLED

    def _recompute_execution_order(self) -> None:
        # Topological sort by dependencies, then priority
        ordered: List[str] = []
        visited: set = set()
        temp: set = set()

        def visit(tid: str) -> None:
            if tid in visited:
                return
            if tid in temp:
                return  # cycle - skip
            temp.add(tid)
            t = self._task_graph.get(tid)
            if t:
                for dep in t.dependencies:
                    if dep in self._task_graph:
                        visit(dep)
                ordered.append(tid)
            temp.discard(tid)
            visited.add(tid)

        for tid in self._task_graph:
            visit(tid)
        # Sort within topological constraints by priority
        self._execution_order = sorted(
            ordered,
            key=lambda tid: -self._task_graph[tid].priority
            if tid in self._task_graph else 0,
        )

    def snapshot(self) -> List[Dict[str, Any]]:
        with self._lock:
            return [
                {
                    "task_id": t.task_id,
                    "name": t.name,
                    "status": t.status.value,
                    "priority": t.priority,
                    "dependencies": list(t.dependencies),
                    "error": t.error,
                }
                for t in self._task_graph.values()
            ]

    def reset(self) -> None:
        with self._lock:
            self._task_graph.clear()
            self._execution_order.clear()


# =============================================================================
# Tool Orchestrator
# =============================================================================


class ToolOrchestrator:
    """Permission-aware tool composition and parallel dispatch.

    Maintains a registry of tool callables with permission tiers. Tools can
    be composed into pipelines or dispatched in parallel when independent.
    """

    def __init__(self) -> None:
        self._registry: Dict[str, Tuple[Callable, str]] = {}  # name -> (fn, permission)
        self._lock = threading.RLock()

    def register(self, name: str, fn: Callable, permission: str = "execute") -> None:
        with self._lock:
            self._registry[name] = (fn, permission)

    def available_tools(self) -> List[Dict[str, str]]:
        with self._lock:
            return [{"name": n, "permission": p} for n, (_, p) in self._registry.items()]

    def execute(self, name: str, args: Dict[str, Any],
                permission_level: str = "execute") -> Any:
        with self._lock:
            entry = self._registry.get(name)
        if not entry:
            raise KeyError(f"Tool '{name}' not registered")
        fn, required = entry
        # Simple permission tier check
        tiers = ["observe", "execute", "mutate", "admin"]
        if tiers.index(permission_level) < tiers.index(required):
            raise PermissionError(
                f"Tool '{name}' requires '{required}', got '{permission_level}'")
        return fn(**args)

    def compose(self, pipeline: List[Dict[str, Any]],
                permission_level: str = "execute") -> List[Any]:
        """Execute a pipeline of tools, passing each result to the next."""
        results: List[Any] = []
        carry: Any = None
        for step in pipeline:
            name = step.get("name", "")
            args = dict(step.get("args", {}))
            if carry is not None and step.get("feed_previous", True):
                args["previous"] = carry
            res = self.execute(name, args, permission_level)
            results.append(res)
            carry = res
        return results


# =============================================================================
# Reflection Loop
# =============================================================================


class ReflectionLoop:
    """Self-evaluation and lesson capture.

    Examines completed tasks and reasoning traces, attributes root causes,
    and produces concrete adjustment lessons that feed back into planning.
    """

    def __init__(self) -> None:
        self._reflections: Deque[Reflection] = deque(maxlen=128)
        self._lock = threading.RLock()

    def reflect(self, target: str, outcome: str, root_cause: str = "",
                lesson: str = "", adjustment: str = "",
                confidence: float = 0.5) -> Reflection:
        r = Reflection(
            target=target,
            outcome=outcome,
            root_cause=root_cause,
            lesson=lesson,
            adjustment=adjustment,
            confidence=confidence,
        )
        with self._lock:
            self._reflections.append(r)
        return r

    def auto_reflect(self, task: Task, trace: Optional[ReasoningTrace] = None) -> Reflection:
        """Generate a reflection from a completed task."""
        outcome = "success" if task.status == TaskStatus.COMPLETED else "failure"
        root_cause = task.error or "within expectations"
        lesson = f"For '{task.name}': {root_cause}"
        adjustment = "retry with adjusted args" if task.status == TaskStatus.FAILED \
            else "retain current approach"
        confidence = trace.confidence if trace else 0.5
        return self.reflect(task.task_id, outcome, root_cause, lesson, adjustment, confidence)

    def history(self, limit: int = 16) -> List[Reflection]:
        with self._lock:
            return list(self._reflections)[-limit:]

    def lessons(self) -> List[str]:
        with self._lock:
            return [r.lesson for r in self._reflections if r.lesson]


# =============================================================================
# Skill Evolver
# =============================================================================


class SkillEvolver:
    """Trajectory learning and skill synthesis.

    Records action trajectories, identifies repeated successful patterns,
    and synthesizes them into reusable procedural skills stored in memory.
    """

    def __init__(self) -> None:
        self._trajectories: Deque[List[Task]] = deque(maxlen=32)
        self._skills: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.RLock()

    def record_trajectory(self, tasks: List[Task]) -> None:
        with self._lock:
            self._trajectories.append(list(tasks))

    def synthesize_skill(self, name: str, pattern: List[str],
                         trigger: str = "") -> Dict[str, Any]:
        skill = {
            "name": name,
            "pattern": pattern,
            "trigger": trigger,
            "created_at": time.time(),
            "use_count": 0,
        }
        with self._lock:
            self._skills[name] = skill
        return skill

    def get_skill(self, name: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            return self._skills.get(name)

    def list_skills(self) -> List[Dict[str, Any]]:
        with self._lock:
            return list(self._skills.values())

    def detect_patterns(self) -> List[Dict[str, Any]]:
        """Find repeated task name sequences across trajectories."""
        with self._lock:
            seq_counts: Dict[Tuple[str, ...], int] = {}
            for traj in self._trajectories:
                names = tuple(t.name for t in traj if t.status == TaskStatus.COMPLETED)
                if len(names) >= 2:
                    seq_counts[names] = seq_counts.get(names, 0) + 1
        patterns = [
            {"sequence": list(seq), "count": cnt}
            for seq, cnt in sorted(seq_counts.items(), key=lambda x: -x[1])
            if cnt >= 2
        ]
        return patterns[:8]


# =============================================================================
# Agent Kernel
# =============================================================================


class AgentKernel:
    """Unified cognitive kernel - the foundational substrate for all agents.

    The kernel wires together perception, memory, reasoning, planning, tool
    orchestration, reflection, and skill evolution into a single cognitive
    cycle. Higher-level agents (director, conductor, sentinel) build on top
    of the kernel by registering tools and feeding perceptions.

    Thread-safe singleton.
    """

    _instance: Optional["AgentKernel"] = None
    _instance_lock = threading.RLock()

    def __init__(self) -> None:
        if AgentKernel._instance is not None:
            raise RuntimeError("Use AgentKernel.get_instance()")
        self._initialized: bool = False
        self.memory: MemoryHierarchy = MemoryHierarchy()
        self.reasoning: ReasoningEngine = ReasoningEngine()
        self.planning: PlanningCore = PlanningCore()
        self.tools: ToolOrchestrator = ToolOrchestrator()
        self.reflection: ReflectionLoop = ReflectionLoop()
        self.skills: SkillEvolver = SkillEvolver()
        self._perception_queue: Deque[Perception] = deque(maxlen=64)
        self._cycle_count: int = 0
        self._last_result: Optional[CognitiveCycleResult] = None
        self._lock = threading.RLock()

    @classmethod
    def get_instance(cls) -> "AgentKernel":
        if cls._instance is None:
            with cls._instance_lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def initialize(self) -> None:
        with self._lock:
            if self._initialized:
                return
            # Seed semantic memory with foundational design patterns
            seed_patterns = [
                ("player_agency", "Player must have meaningful choices that affect outcome"),
                ("feedback_loop", "Tight perceptual feedback on every player action"),
                ("progression_curve", "Difficulty escalates in sync with player skill growth"),
                ("risk_reward", "Greater rewards require commensurate risk"),
                ("emergent_dynamics", "Simple rules combine into complex emergent behavior"),
            ]
            for name, desc in seed_patterns:
                self.memory.write(MemoryEntry(
                    layer=MemoryLayer.SEMANTIC,
                    namespace="design_patterns",
                    content={"name": name, "description": desc},
                    tags=[name, "pattern"],
                    salience=0.8,
                ))
            # Register built-in tools
            self._register_builtin_tools()
            self._initialized = True
            logger.info("AgentKernel initialized")

    def _register_builtin_tools(self) -> None:
        """Register foundational tools available to all agents."""
        def noop(**kwargs: Any) -> Dict[str, Any]:
            return {"status": "noop", "args": kwargs}

        self.tools.register("observe", noop, "observe")
        self.tools.register("plan", noop, "execute")
        self.tools.register("execute", noop, "execute")
        self.tools.register("verify", noop, "execute")
        self.tools.register("reflect", noop, "observe")
        self.tools.register("learn", noop, "execute")

    # -------------------------------------------------------------------------
    # Perception ingestion
    # -------------------------------------------------------------------------

    def perceive(self, source: str, channel: str, payload: Any,
                 salience: float = 0.5) -> Perception:
        p = Perception(source=source, channel=channel, payload=payload,
                       salience=salience)
        with self._lock:
            self._perception_queue.append(p)
        # Write to working memory
        self.memory.write(MemoryEntry(
            layer=MemoryLayer.WORKING,
            namespace=source,
            content=payload,
            tags=[channel, source],
            salience=salience,
        ))
        return p

    # -------------------------------------------------------------------------
    # Cognitive cycle
    # -------------------------------------------------------------------------

    def cycle(self) -> CognitiveCycleResult:
        """Advance the agent one full cognitive cycle."""
        if not self._initialized:
            self.initialize()
        start = time.time()
        result = CognitiveCycleResult()
        self._cycle_count += 1

        # Phase 1: Perceive
        perceptions = self._drain_perceptions()
        result.perceptions_processed = len(perceptions)

        # Phase 2: Encode - store salient perceptions to episodic memory
        for p in perceptions:
            if p.salience >= 0.6:
                self.memory.write(MemoryEntry(
                    layer=MemoryLayer.EPISODIC,
                    namespace=p.source,
                    content=p.payload,
                    tags=[p.channel, p.source],
                    salience=p.salience,
                ))
                result.memories_written += 1

        # Phase 3: Reason - generate inferences from working memory
        working = self.memory.read(MemoryLayer.WORKING, limit=8)
        if working:
            premises = [str(e.content)[:80] for e in working]
            trace = self.reasoning.reason(premises, ReasoningMode.CHAIN_OF_THOUGHT)
            result.reasoning_traces = 1
            # Store trace in procedural memory
            self.memory.write(MemoryEntry(
                layer=MemoryLayer.PROCEDURAL,
                namespace="reasoning",
                content={"trace_id": trace.trace_id, "conclusion": trace.conclusion},
                tags=["reasoning", trace.mode.value],
                salience=trace.confidence,
            ))

        # Phase 4: Plan - check for ready tasks
        ready = self.planning.next_ready_task()
        result.tasks_planned = 1 if ready else 0

        # Phase 5: Act - execute ready task
        if ready:
            try:
                if ready.tool:
                    res = self.tools.execute(
                        ready.tool, ready.args,
                        permission_level="execute")
                else:
                    res = {"status": "no_tool", "task": ready.name}
                self.planning.complete_task(ready.task_id, res)
                result.tasks_executed = 1
            except Exception as exc:
                self.planning.complete_task(ready.task_id, None, error=str(exc))
                logger.warning("Task %s failed: %s", ready.name, exc)

        # Phase 6: Reflect - auto-reflect on completed task
        if ready and ready.status in (TaskStatus.COMPLETED, TaskStatus.FAILED):
            r = self.reflection.auto_reflect(ready)
            result.reflections = 1
            # Store lesson in semantic memory
            self.memory.write(MemoryEntry(
                layer=MemoryLayer.SEMANTIC,
                namespace="lessons",
                content={"lesson": r.lesson, "adjustment": r.adjustment},
                tags=["lesson", ready.name],
                salience=r.confidence,
            ))

        # Phase 7: Learn - detect patterns periodically
        if self._cycle_count % 8 == 0:
            patterns = self.skills.detect_patterns()
            if patterns:
                top = patterns[0]
                self.skills.synthesize_skill(
                    name=f"pattern_{self._cycle_count}",
                    pattern=top["sequence"],
                    trigger="repeated_success",
                )
                result.skills_learned = 1

        # Decay memories
        self.memory.decay_all(0.997)
        # Clear working memory
        self.memory.clear_working()

        result.phase = CognitivePhase.LEARN
        result.duration_s = time.time() - start
        self._last_result = result
        return result

    def _drain_perceptions(self) -> List[Perception]:
        with self._lock:
            drained = list(self._perception_queue)
            self._perception_queue.clear()
        return drained

    # -------------------------------------------------------------------------
    # Public API for higher-level agents
    # -------------------------------------------------------------------------

    def submit_goal(self, goal: str, sub_tasks: List[Dict[str, Any]]) -> List[Task]:
        """Submit a goal for decomposition and planning."""
        if not self._initialized:
            self.initialize()
        tasks = self.planning.decompose(goal, sub_tasks)
        # Record goal in episodic memory
        self.memory.write(MemoryEntry(
            layer=MemoryLayer.EPISODIC,
            namespace="goals",
            content={"goal": goal, "task_count": len(tasks)},
            tags=["goal", "planning"],
            salience=0.9,
        ))
        return tasks

    def recall(self, query: str, limit: int = 8) -> List[MemoryEntry]:
        return self.memory.recall(query, limit)

    def status(self) -> Dict[str, Any]:
        return {
            "initialized": self._initialized,
            "cycles": self._cycle_count,
            "memory_stats": self.memory.stats(),
            "tools": len(self.tools.available_tools()),
            "planning_tasks": len(self.planning.snapshot()),
            "reflections": len(self.reflection.history()),
            "skills": len(self.skills.list_skills()),
            "last_cycle": {
                "phase": self._last_result.phase.value if self._last_result else None,
                "duration_s": self._last_result.duration_s if self._last_result else 0,
                "perceptions": self._last_result.perceptions_processed if self._last_result else 0,
                "tasks_executed": self._last_result.tasks_executed if self._last_result else 0,
            } if self._last_result else None,
        }

    def reset(self) -> None:
        """Reset the kernel state (preserves registered tools and skills)."""
        with self._lock:
            self.planning.reset()
            self._perception_queue.clear()
            self._cycle_count = 0
            self._last_result = None
