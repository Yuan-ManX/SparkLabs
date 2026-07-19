"""
SparkLabs - Cognitive Architect

A unified cognitive architecture that orchestrates multi-modal reasoning,
tool evolution, and knowledge synthesis into a single coherent system.
The architect binds the AgentKernel with engine subsystems to deliver
original AI-native cognition for game creation and runtime direction.

Core responsibilities:
  1. Reasoning Orchestration - select and chain reasoning modes (CoT, ToT,
     meta, causal, analogical) based on task signature and historical success.
  2. Tool Evolution Pipeline - forge, test, refine, and deploy new tools on
     demand when the kernel encounters gaps in its capability surface.
  3. Knowledge Synthesis Engine - consolidate episodic memory into semantic
     knowledge, build cross-domain indices, and retrieve actionable insight.
  4. Collaboration Protocol - coordinate multiple cognitive sub-agents
     through a shared blackboard with conflict resolution and consensus.
  5. Architect Cycle - a single tick that runs perceive → reason → plan →
     forge → synthesize → reflect, producing an ArchitectDecision.
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


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class ReasoningStrategy(Enum):
    """Selection strategy for choosing a reasoning mode."""
    SINGLE_BEST = "single_best"        # Pick the single highest-scoring mode
    SEQUENTIAL_CHAIN = "sequential"    # Run modes in sequence, feed outputs
    PARALLEL_FANOUT = "parallel"       # Run modes in parallel, merge results
    ADAPTIVE_SWITCH = "adaptive"       # Switch mode mid-reasoning on stall


class ToolForgeStage(Enum):
    """Stages of the tool evolution pipeline."""
    IDENTIFY = "identify"      # Detect a capability gap
    DESIGN = "design"          # Draft a tool specification
    IMPLEMENT = "implement"    # Generate the tool implementation
    TEST = "test"              # Validate against test cases
    REFINE = "refine"          # Iterate on failures
    DEPLOY = "deploy"          # Register with the kernel's tool orchestrator
    RETIRE = "retire"          # Remove obsolete or broken tools


class KnowledgeSynthesisPhase(Enum):
    """Phases of the knowledge synthesis engine."""
    CONSOLIDATE = "consolidate"    # Merge episodic entries into semantic facts
    INDEX = "index"                # Build cross-domain retrieval indices
    RETRIEVE = "retrieve"          # Fetch relevant knowledge for a query
    APPLY = "apply"                # Translate knowledge into actionable steps
    PRUNE = "prune"                # Decay low-salience or stale knowledge


class ArchitectPhase(Enum):
    """Phases of a single architect cycle."""
    PERCEIVE = "perceive"
    REASON = "reason"
    PLAN = "plan"
    FORGE = "forge"
    SYNTHESIZE = "synthesize"
    REFLECT = "reflect"


class CollaborationRole(Enum):
    """Roles a sub-agent can take in a collaboration session."""
    LEAD = "lead"            # Drives the task decomposition
    CONTRIBUTOR = "contributor"  # Provides specialized output
    REVIEWER = "reviewer"    # Validates outputs from contributors
    SYNTHESIZER = "synthesizer"  # Merges outputs into final result


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------

@dataclass
class ReasoningRequest:
    """A request for multi-modal reasoning."""
    request_id: str = field(default_factory=lambda: uuid.uuid4().hex[:10])
    task: str = ""
    context: Dict[str, Any] = field(default_factory=dict)
    preferred_modes: List[str] = field(default_factory=list)
    strategy: ReasoningStrategy = ReasoningStrategy.ADAPTIVE_SWITCH
    max_steps: int = 6
    confidence_threshold: float = 0.6


@dataclass
class ReasoningResult:
    """The outcome of a reasoning orchestration."""
    result_id: str = field(default_factory=lambda: uuid.uuid4().hex[:10])
    request_id: str = ""
    conclusion: str = ""
    confidence: float = 0.0
    modes_used: List[str] = field(default_factory=list)
    steps: List[str] = field(default_factory=list)
    artifacts: Dict[str, Any] = field(default_factory=dict)
    duration_s: float = 0.0
    success: bool = False


@dataclass
class ToolSpecification:
    """A specification for a new tool to be forged."""
    spec_id: str = field(default_factory=lambda: uuid.uuid4().hex[:10])
    name: str = ""
    intent: str = ""
    input_schema: Dict[str, Any] = field(default_factory=dict)
    output_schema: Dict[str, Any] = field(default_factory=dict)
    implementation: str = ""     # A callable name or script reference
    test_cases: List[Dict[str, Any]] = field(default_factory=list)
    permissions: List[str] = field(default_factory=list)
    stage: ToolForgeStage = ToolForgeStage.IDENTIFY
    confidence: float = 0.0
    failure_count: int = 0
    created_at: float = field(default_factory=time.time)


@dataclass
class KnowledgeFact:
    """A consolidated semantic knowledge fact."""
    fact_id: str = field(default_factory=lambda: uuid.uuid4().hex[:10])
    domain: str = "general"
    statement: str = ""
    evidence: List[str] = field(default_factory=list)
    confidence: float = 0.5
    salience: float = 0.5
    tags: List[str] = field(default_factory=list)
    source_episodes: List[str] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    last_accessed: float = field(default_factory=time.time)
    access_count: int = 0


@dataclass
class CollaborationTask:
    """A task delegated to multiple sub-agents."""
    task_id: str = field(default_factory=lambda: uuid.uuid4().hex[:10])
    objective: str = ""
    decomposed_subtasks: List[Dict[str, Any]] = field(default_factory=list)
    assigned_roles: Dict[str, CollaborationRole] = field(default_factory=dict)
    contributions: Dict[str, Any] = field(default_factory=dict)
    conflicts: List[Dict[str, Any]] = field(default_factory=list)
    consensus: Optional[str] = None
    status: str = "pending"     # pending, in_progress, resolved, abandoned
    created_at: float = field(default_factory=time.time)


@dataclass
class ArchitectDecision:
    """The outcome of one architect cycle."""
    cycle_id: str = field(default_factory=lambda: uuid.uuid4().hex[:10])
    phase: ArchitectPhase = ArchitectPhase.PERCEIVE
    reasoning_result: Optional[ReasoningResult] = None
    tools_forged: List[str] = field(default_factory=list)
    knowledge_synthesized: int = 0
    collaboration_tasks: int = 0
    directives: List[Dict[str, Any]] = field(default_factory=list)
    duration_s: float = 0.0
    notes: List[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Reasoning Orchestrator
# ---------------------------------------------------------------------------

class ReasoningOrchestrator:
    """Selects and chains reasoning modes based on task signature."""

    # Mode suitability scores per task category (0..1)
    _SUITABILITY: Dict[str, Dict[str, float]] = {
        "analytical": {
            "chain_of_thought": 0.9, "tree_of_thought": 0.7,
            "meta": 0.5, "causal": 0.8, "analogical": 0.4,
        },
        "exploratory": {
            "chain_of_thought": 0.5, "tree_of_thought": 0.9,
            "meta": 0.6, "causal": 0.4, "analogical": 0.8,
        },
        "diagnostic": {
            "chain_of_thought": 0.7, "tree_of_thought": 0.6,
            "meta": 0.5, "causal": 0.9, "analogical": 0.5,
        },
        "creative": {
            "chain_of_thought": 0.4, "tree_of_thought": 0.7,
            "meta": 0.4, "causal": 0.3, "analogical": 0.9,
        },
        "meta_cognitive": {
            "chain_of_thought": 0.5, "tree_of_thought": 0.5,
            "meta": 0.9, "causal": 0.4, "analogical": 0.5,
        },
    }

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._history: Deque[ReasoningResult] = deque(maxlen=64)
        self._mode_success_rate: Dict[str, float] = {
            "chain_of_thought": 0.7,
            "tree_of_thought": 0.7,
            "meta": 0.7,
            "causal": 0.7,
            "analogical": 0.7,
        }

    def classify_task(self, task: str) -> str:
        """Classify a task into a category for mode selection."""
        text = task.lower()
        if any(w in text for w in ["why", "cause", "because", "effect", "result"]):
            return "diagnostic"
        if any(w in text for w in ["create", "design", "imagine", "invent", "novel"]):
            return "creative"
        if any(w in text for w in ["reflect", "evaluate", "assess", "critique", "meta"]):
            return "meta_cognitive"
        if any(w in text for w in ["explore", "brainstorm", "alternatives", "options"]):
            return "exploratory"
        return "analytical"

    def select_modes(
        self, task: str, preferred: List[str], strategy: ReasoningStrategy,
    ) -> List[str]:
        """Select reasoning modes based on task, preference, and strategy."""
        category = self.classify_task(task)
        suitability = self._SUITABILITY.get(category, self._SUITABILITY["analytical"])

        with self._lock:
            # Blend suitability with historical success rate
            scored: List[Tuple[str, float]] = []
            for mode, base_score in suitability.items():
                success = self._mode_success_rate.get(mode, 0.5)
                score = 0.6 * base_score + 0.4 * success
                scored.append((mode, score))

        # Honor explicit preferences by boosting their score
        if preferred:
            scored = [(m, s + (0.3 if m in preferred else 0.0)) for m, s in scored]

        scored.sort(key=lambda x: x[1], reverse=True)

        if strategy == ReasoningStrategy.SINGLE_BEST:
            return [scored[0][0]] if scored else []
        if strategy == ReasoningStrategy.SEQUENTIAL_CHAIN:
            return [m for m, _ in scored[:3]]
        if strategy == ReasoningStrategy.PARALLEL_FANOUT:
            return [m for m, _ in scored[:3]]
        # ADAPTIVE_SWITCH: start with the best, allow switching mid-reasoning
        return [scored[0][0]] if scored else []

    def update_success_rate(self, mode: str, success: bool) -> None:
        """Update the rolling success rate for a reasoning mode."""
        with self._lock:
            current = self._mode_success_rate.get(mode, 0.5)
            # Exponential moving average
            alpha = 0.2
            self._mode_success_rate[mode] = (
                (1 - alpha) * current + alpha * (1.0 if success else 0.0)
            )

    def record(self, result: ReasoningResult) -> None:
        with self._lock:
            self._history.append(result)

    def stats(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "history_size": len(self._history),
                "mode_success_rate": dict(self._mode_success_rate),
            }


# ---------------------------------------------------------------------------
# Tool Evolution Pipeline
# ---------------------------------------------------------------------------

class ToolEvolutionPipeline:
    """Forges, tests, refines, and deploys new tools on demand."""

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._active_specs: Dict[str, ToolSpecification] = {}
        self._deployed_tools: Dict[str, ToolSpecification] = {}
        self._retired_tools: Dict[str, ToolSpecification] = {}
        self._max_failure_count = 3
        self._max_active_specs = 32

    def identify_gap(
        self, task: str, missing_capability: str,
    ) -> ToolSpecification:
        """Identify a capability gap and create a tool specification."""
        with self._lock:
            if len(self._active_specs) >= self._max_active_specs:
                # Evict the oldest spec
                oldest_id = next(iter(self._active_specs))
                self._active_specs.pop(oldest_id)

        spec = ToolSpecification(
            name=f"tool_{missing_capability[:24]}_{uuid.uuid4().hex[:6]}",
            intent=missing_capability,
            stage=ToolForgeStage.IDENTIFY,
            confidence=0.3,
        )
        with self._lock:
            self._active_specs[spec.spec_id] = spec
        logger.info("Tool gap identified: %s -> %s", missing_capability, spec.name)
        return spec

    def design(
        self, spec: ToolSpecification, input_schema: Dict[str, Any],
        output_schema: Dict[str, Any], permissions: List[str],
    ) -> ToolSpecification:
        """Design the tool's interface and constraints."""
        spec.input_schema = dict(input_schema)
        spec.output_schema = dict(output_schema)
        spec.permissions = list(permissions)
        spec.stage = ToolForgeStage.DESIGN
        spec.confidence = 0.4
        return spec

    def implement(
        self, spec: ToolSpecification, implementation: str,
        test_cases: List[Dict[str, Any]],
    ) -> ToolSpecification:
        """Provide the implementation reference and test cases."""
        spec.implementation = implementation
        spec.test_cases = list(test_cases)
        spec.stage = ToolForgeStage.IMPLEMENT
        spec.confidence = 0.5
        return spec

    def test(self, spec: ToolSpecification) -> Tuple[bool, str]:
        """Run test cases against the tool implementation."""
        spec.stage = ToolForgeStage.TEST
        if not spec.test_cases:
            spec.confidence = 0.6
            return True, "no_test_cases"
        # Simulated test execution: in production this would invoke the tool
        passed = 0
        for case in spec.test_cases:
            # Simple schema validation
            inputs = case.get("inputs", {})
            valid = all(k in inputs for k in spec.input_schema.get("required", []))
            if valid:
                passed += 1
        total = len(spec.test_cases)
        success = passed == total
        if success:
            spec.confidence = 0.8
        else:
            spec.failure_count += 1
            spec.confidence = max(0.1, spec.confidence - 0.15)
        return success, f"{passed}/{total}_passed"

    def refine(self, spec: ToolSpecification, feedback: str) -> ToolSpecification:
        """Apply refinement feedback and return to implementation stage."""
        spec.stage = ToolForgeStage.IMPLEMENT
        spec.confidence = max(0.1, spec.confidence - 0.05)
        logger.info("Refining tool %s: %s", spec.name, feedback[:80])
        return spec

    def deploy(self, spec: ToolSpecification) -> Tuple[bool, str]:
        """Deploy the tool to the kernel's tool orchestrator."""
        if spec.failure_count >= self._max_failure_count:
            spec.stage = ToolForgeStage.RETIRE
            with self._lock:
                self._active_specs.pop(spec.spec_id, None)
                self._retired_tools[spec.spec_id] = spec
            return False, "max_failures_exceeded"

        spec.stage = ToolForgeStage.DEPLOY
        spec.confidence = min(1.0, spec.confidence + 0.1)
        with self._lock:
            self._active_specs.pop(spec.spec_id, None)
            self._deployed_tools[spec.spec_id] = spec
        logger.info("Tool deployed: %s", spec.name)
        return True, "deployed"

    def retire(self, tool_name: str) -> bool:
        """Retire a deployed tool by name."""
        with self._lock:
            for spec_id, spec in list(self._deployed_tools.items()):
                if spec.name == tool_name:
                    spec.stage = ToolForgeStage.RETIRE
                    self._deployed_tools.pop(spec_id)
                    self._retired_tools[spec_id] = spec
                    return True
        return False

    def list_active(self) -> List[ToolSpecification]:
        with self._lock:
            return list(self._active_specs.values())

    def list_deployed(self) -> List[ToolSpecification]:
        with self._lock:
            return list(self._deployed_tools.values())

    def stats(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "active_specs": len(self._active_specs),
                "deployed_tools": len(self._deployed_tools),
                "retired_tools": len(self._retired_tools),
                "max_active_specs": self._max_active_specs,
            }


# ---------------------------------------------------------------------------
# Knowledge Synthesis Engine
# ---------------------------------------------------------------------------

class KnowledgeSynthesisEngine:
    """Consolidates episodic memory into semantic knowledge and retrieves it."""

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._facts: Dict[str, KnowledgeFact] = {}
        self._domain_index: Dict[str, List[str]] = {}
        self._tag_index: Dict[str, List[str]] = {}
        self._max_facts = 512
        self._salience_decay_per_tick = 0.995

    def consolidate(
        self, episodes: List[Dict[str, Any]],
    ) -> List[KnowledgeFact]:
        """Consolidate episodic entries into semantic facts."""
        if not episodes:
            return []

        # Group episodes by domain
        by_domain: Dict[str, List[Dict[str, Any]]] = {}
        for ep in episodes:
            domain = ep.get("domain", "general")
            by_domain.setdefault(domain, []).append(ep)

        new_facts: List[KnowledgeFact] = []
        for domain, eps in by_domain.items():
            # Extract a representative statement from the episodes
            statements = [e.get("summary", e.get("content", "")) for e in eps]
            merged = " | ".join(s for s in statements if s)
            if not merged:
                continue

            # Check for an existing fact in the same domain with similar content
            existing = self._find_similar(domain, merged)
            if existing is not None:
                # Reinforce existing fact
                existing.evidence.extend([e.get("id", "") for e in eps[:3]])
                existing.confidence = min(1.0, existing.confidence + 0.05)
                existing.salience = min(1.0, existing.salience + 0.1)
                existing.access_count += 1
                existing.last_accessed = time.time()
                new_facts.append(existing)
            else:
                fact = KnowledgeFact(
                    domain=domain,
                    statement=merged[:500],
                    evidence=[e.get("id", "") for e in eps[:3]],
                    confidence=0.6,
                    salience=0.7,
                    tags=[domain, "synthesized"],
                    source_episodes=[e.get("id", "") for e in eps],
                )
                with self._lock:
                    if len(self._facts) >= self._max_facts:
                        self._evict_lowest_salience()
                    self._facts[fact.fact_id] = fact
                    self._index_fact(fact)
                new_facts.append(fact)

        logger.info("Consolidated %d facts from %d episodes", len(new_facts), len(episodes))
        return new_facts

    def _find_similar(self, domain: str, statement: str) -> Optional[KnowledgeFact]:
        """Find a fact in the same domain with similar content."""
        with self._lock:
            domain_fact_ids = self._domain_index.get(domain, [])
            target_words = set(statement.lower().split())
            best: Optional[KnowledgeFact] = None
            best_overlap = 0.0
            for fid in domain_fact_ids:
                fact = self._facts.get(fid)
                if not fact:
                    continue
                fact_words = set(fact.statement.lower().split())
                if not target_words or not fact_words:
                    continue
                overlap = len(target_words & fact_words) / len(target_words | fact_words)
                if overlap > 0.4 and overlap > best_overlap:
                    best = fact
                    best_overlap = overlap
        return best

    def _index_fact(self, fact: KnowledgeFact) -> None:
        """Index a fact by domain and tags."""
        self._domain_index.setdefault(fact.domain, []).append(fact.fact_id)
        for tag in fact.tags:
            self._tag_index.setdefault(tag, []).append(fact.fact_id)

    def _evict_lowest_salience(self) -> None:
        """Evict the fact with the lowest salience."""
        if not self._facts:
            return
        lowest_id = min(self._facts, key=lambda fid: self._facts[fid].salience)
        fact = self._facts.pop(lowest_id)
        # Clean up indices
        domain_list = self._domain_index.get(fact.domain, [])
        if lowest_id in domain_list:
            domain_list.remove(lowest_id)
        for tag in fact.tags:
            tag_list = self._tag_index.get(tag, [])
            if lowest_id in tag_list:
                tag_list.remove(lowest_id)

    def retrieve(
        self, query: str, domain: Optional[str] = None, limit: int = 5,
    ) -> List[KnowledgeFact]:
        """Retrieve the most relevant facts for a query."""
        with self._lock:
            candidates: List[KnowledgeFact] = []
            if domain:
                candidates = [
                    self._facts[fid] for fid in self._domain_index.get(domain, [])
                    if fid in self._facts
                ]
            else:
                candidates = list(self._facts.values())

            if not candidates:
                return []

            query_words = set(query.lower().split())
            scored: List[Tuple[KnowledgeFact, float]] = []
            for fact in candidates:
                fact_words = set(fact.statement.lower().split())
                if not query_words or not fact_words:
                    score = fact.salience * fact.confidence
                else:
                    overlap = len(query_words & fact_words) / len(query_words | fact_words)
                    score = (0.5 * overlap + 0.3 * fact.salience + 0.2 * fact.confidence)
                scored.append((fact, score))
                fact.last_accessed = time.time()
                fact.access_count += 1

            scored.sort(key=lambda x: x[1], reverse=True)
            return [f for f, _ in scored[:limit]]

    def apply(self, facts: List[KnowledgeFact]) -> List[Dict[str, Any]]:
        """Translate knowledge facts into actionable steps."""
        actions: List[Dict[str, Any]] = []
        for fact in facts:
            actions.append({
                "fact_id": fact.fact_id,
                "domain": fact.domain,
                "statement": fact.statement,
                "confidence": fact.confidence,
                "suggested_action": f"Apply knowledge from {fact.domain}: {fact.statement[:80]}",
            })
        return actions

    def prune(self, salience_floor: float = 0.1) -> int:
        """Prune facts below the salience floor."""
        with self._lock:
            to_remove = [
                fid for fid, fact in self._facts.items()
                if fact.salience < salience_floor
            ]
            for fid in to_remove:
                fact = self._facts.pop(fid)
                domain_list = self._domain_index.get(fact.domain, [])
                if fid in domain_list:
                    domain_list.remove(fid)
                for tag in fact.tags:
                    tag_list = self._tag_index.get(tag, [])
                    if fid in tag_list:
                        tag_list.remove(fid)
            return len(to_remove)

    def decay(self) -> None:
        """Apply salience decay to all facts."""
        with self._lock:
            for fact in self._facts.values():
                fact.salience *= self._salience_decay_per_tick

    def stats(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "total_facts": len(self._facts),
                "domains": len(self._domain_index),
                "tags": len(self._tag_index),
                "max_facts": self._max_facts,
            }


# ---------------------------------------------------------------------------
# Collaboration Protocol
# ---------------------------------------------------------------------------

class CollaborationProtocol:
    """Coordinates multiple cognitive sub-agents through a shared blackboard."""

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._active_tasks: Dict[str, CollaborationTask] = {}
        self._completed_tasks: Deque[CollaborationTask] = deque(maxlen=64)
        self._max_active_tasks = 16

    def propose_task(
        self, objective: str, subtasks: List[Dict[str, Any]],
    ) -> CollaborationTask:
        """Propose a new collaboration task."""
        with self._lock:
            if len(self._active_tasks) >= self._max_active_tasks:
                # Evict the oldest pending task
                oldest_id = min(
                    self._active_tasks,
                    key=lambda tid: self._active_tasks[tid].created_at,
                )
                self._active_tasks.pop(oldest_id)

        task = CollaborationTask(
            objective=objective,
            decomposed_subtasks=list(subtasks),
            status="pending",
        )
        with self._lock:
            self._active_tasks[task.task_id] = task
        return task

    def assign_role(
        self, task_id: str, agent_name: str, role: CollaborationRole,
    ) -> bool:
        """Assign a role to an agent for a task."""
        with self._lock:
            task = self._active_tasks.get(task_id)
            if not task:
                return False
            task.assigned_roles[agent_name] = role
            if task.status == "pending":
                task.status = "in_progress"
            return True

    def submit_contribution(
        self, task_id: str, agent_name: str, contribution: Any,
    ) -> bool:
        """Submit a contribution from an agent."""
        with self._lock:
            task = self._active_tasks.get(task_id)
            if not task:
                return False
            task.contributions[agent_name] = contribution
            return True

    def detect_conflicts(self, task_id: str) -> List[Dict[str, Any]]:
        """Detect conflicts between contributions."""
        with self._lock:
            task = self._active_tasks.get(task_id)
            if not task or len(task.contributions) < 2:
                return []
            conflicts: List[Dict[str, Any]] = []
            contribs = list(task.contributions.items())
            for i in range(len(contribs)):
                for j in range(i + 1, len(contribs)):
                    a_name, a_val = contribs[i]
                    b_name, b_val = contribs[j]
                    # Simple conflict detection: string mismatch
                    a_str = str(a_val)[:200]
                    b_str = str(b_val)[:200]
                    if a_str != b_str:
                        # Check if they share any keywords
                        a_words = set(a_str.lower().split())
                        b_words = set(b_str.lower().split())
                        overlap = len(a_words & b_words)
                        if overlap > 2:
                            conflicts.append({
                                "agents": [a_name, b_name],
                                "overlap": overlap,
                                "summary": f"{a_name} and {b_name} differ on shared context",
                            })
            task.conflicts = conflicts
            return conflicts

    def resolve_conflicts(self, task_id: str) -> Optional[str]:
        """Resolve conflicts by selecting the contribution from the lead agent."""
        with self._lock:
            task = self._active_tasks.get(task_id)
            if not task:
                return None
            # Find the lead agent
            lead_name: Optional[str] = None
            for name, role in task.assigned_roles.items():
                if role == CollaborationRole.LEAD:
                    lead_name = name
                    break
            if lead_name and lead_name in task.contributions:
                task.consensus = str(task.contributions[lead_name])
                task.status = "resolved"
                return task.consensus
            # Fallback: pick the longest contribution
            if task.contributions:
                longest = max(task.contributions.items(), key=lambda x: len(str(x[1])))
                task.consensus = str(longest[1])
                task.status = "resolved"
                return task.consensus
            return None

    def complete_task(self, task_id: str) -> bool:
        """Move a resolved task to completed."""
        with self._lock:
            task = self._active_tasks.pop(task_id, None)
            if not task:
                return False
            task.status = "resolved"
            self._completed_tasks.append(task)
            return True

    def stats(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "active_tasks": len(self._active_tasks),
                "completed_tasks": len(self._completed_tasks),
                "max_active_tasks": self._max_active_tasks,
            }


# ---------------------------------------------------------------------------
# Cognitive Architect (Singleton)
# ---------------------------------------------------------------------------

class CognitiveArchitect:
    """
    Singleton cognitive architect that unifies reasoning orchestration,
    tool evolution, knowledge synthesis, and collaboration into one cycle.
    """

    _instance: Optional["CognitiveArchitect"] = None
    _instance_lock = threading.Lock()

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._initialized = False
        self._kernel: Optional[Any] = None
        self._integrator: Optional[Any] = None
        self._brain: Optional[Any] = None
        self._reasoning = ReasoningOrchestrator()
        self._tool_pipeline = ToolEvolutionPipeline()
        self._knowledge = KnowledgeSynthesisEngine()
        self._collaboration = CollaborationProtocol()
        self._cycle_count = 0
        self._last_result: Optional[ArchitectDecision] = None
        self._pending_requests: Deque[ReasoningRequest] = deque(maxlen=32)
        self._max_cycle_steps = 8

    @classmethod
    def get_instance(cls) -> "CognitiveArchitect":
        with cls._instance_lock:
            if cls._instance is None:
                cls._instance = cls()
            return cls._instance

    def initialize(self) -> None:
        """Initialize the architect by acquiring the kernel and integrator."""
        with self._lock:
            if self._initialized:
                return
            try:
                from sparkai.agent.agent_unified_kernel import AgentKernel
                self._kernel = AgentKernel.get_instance()
            except Exception as exc:
                logger.warning("AgentKernel acquisition failed: %s", exc)
                self._kernel = None
            try:
                from sparkai.engine.engine_kernel_integration import (
                    KernelEngineIntegrator,
                )
                self._integrator = KernelEngineIntegrator.get_instance()
            except Exception as exc:
                logger.warning("KernelEngineIntegrator acquisition failed: %s", exc)
                self._integrator = None
            try:
                from sparkai.agent.agent_game_brain import GameBrain
                self._brain = GameBrain.get_instance()
            except Exception as exc:
                logger.warning("GameBrain acquisition failed: %s", exc)
                self._brain = None
            self._initialized = True
            logger.info("CognitiveArchitect initialized")

    # -----------------------------------------------------------------
    # Public API
    # -----------------------------------------------------------------

    def submit_reasoning_request(self, request: ReasoningRequest) -> str:
        """Submit a reasoning request for processing in the next cycle."""
        with self._lock:
            self._pending_requests.append(request)
        return request.request_id

    def run_reasoning(self, request: ReasoningRequest) -> ReasoningResult:
        """Run a reasoning request immediately and return the result."""
        start = time.time()
        modes = self._reasoning.select_modes(
            request.task, request.preferred_modes, request.strategy,
        )
        result = ReasoningResult(
            request_id=request.request_id,
            modes_used=modes,
            steps=[],
        )

        # Execute reasoning via the kernel if available
        if self._kernel is not None:
            try:
                # Submit the task as a perception and cycle the kernel
                self._kernel.perceive(
                    source="architect",
                    channel="reasoning_request",
                    payload={"task": request.task, "modes": modes},
                    salience=0.8,
                )
                cycle_result = self._kernel.cycle()
                result.steps.append(
                    f"kernel_cycle_{cycle_result.cycle_id[:8]}_"
                    f"traces={cycle_result.reasoning_traces}"
                )
                result.confidence = 0.7 if cycle_result.reasoning_traces > 0 else 0.3
                result.conclusion = (
                    f"Reasoned over '{request.task[:60]}' using {modes}"
                )
                result.success = True
            except Exception as exc:
                result.conclusion = f"Kernel reasoning failed: {exc}"
                result.success = False
        else:
            # Fallback: simulate reasoning
            result.steps.append(f"simulated_modes={modes}")
            result.conclusion = f"Simulated reasoning over '{request.task[:60]}'"
            result.confidence = 0.5
            result.success = True

        # Update success rates
        for mode in modes:
            self._reasoning.update_success_rate(mode, result.success)

        result.duration_s = time.time() - start
        self._reasoning.record(result)
        return result

    def forge_tool_on_demand(
        self, missing_capability: str, input_schema: Dict[str, Any],
        output_schema: Dict[str, Any], test_cases: List[Dict[str, Any]],
    ) -> Tuple[bool, str]:
        """Forge and deploy a new tool to fill a capability gap."""
        spec = self._tool_pipeline.identify_gap("", missing_capability)
        self._tool_pipeline.design(spec, input_schema, output_schema, ["read"])
        self._tool_pipeline.implement(
            spec, f"lambda inputs: {missing_capability}_handler(inputs)", test_cases,
        )
        success, msg = self._tool_pipeline.test(spec)
        if not success and spec.failure_count < 3:
            self._tool_pipeline.refine(spec, f"Test failed: {msg}")
            success, msg = self._tool_pipeline.test(spec)
        if success:
            deployed, deploy_msg = self._tool_pipeline.deploy(spec)
            return deployed, deploy_msg
        return False, msg

    def synthesize_knowledge(
        self, episodes: List[Dict[str, Any]],
    ) -> List[KnowledgeFact]:
        """Consolidate episodic entries into semantic facts."""
        return self._knowledge.consolidate(episodes)

    def query_knowledge(
        self, query: str, domain: Optional[str] = None, limit: int = 5,
    ) -> List[KnowledgeFact]:
        """Retrieve relevant knowledge facts for a query."""
        return self._knowledge.retrieve(query, domain, limit)

    def propose_collaboration(
        self, objective: str, subtasks: List[Dict[str, Any]],
    ) -> CollaborationTask:
        """Propose a multi-agent collaboration task."""
        return self._collaboration.propose_task(objective, subtasks)

    def cycle(self) -> ArchitectDecision:
        """Run one architect cycle: perceive → reason → plan → forge → synthesize → reflect."""
        if not self._initialized:
            self.initialize()
        start = time.time()
        with self._lock:
            self._cycle_count += 1
        decision = ArchitectDecision()
        decision.phase = ArchitectPhase.PERCEIVE

        # Phase 1: Perceive - pull pending reasoning requests
        pending = []
        with self._lock:
            while self._pending_requests:
                pending.append(self._pending_requests.popleft())

        # Phase 2: Reason - run each pending request
        decision.phase = ArchitectPhase.REASON
        for request in pending[:self._max_cycle_steps]:
            result = self.run_reasoning(request)
            decision.reasoning_result = result
            if result.success and result.confidence < 0.6:
                # Low confidence - identify a potential tool gap
                decision.phase = ArchitectPhase.FORGE
                gap = f"reasoning_support_for_{request.task[:20]}"
                deployed, msg = self.forge_tool_on_demand(
                    gap,
                    input_schema={"required": ["task"], "optional": ["context"]},
                    output_schema={"required": ["conclusion"]},
                    test_cases=[{"inputs": {"task": "test"}}],
                )
                if deployed:
                    decision.tools_forged.append(gap)

        # Phase 3: Plan - decompose any unresolved requests into collaboration tasks
        decision.phase = ArchitectPhase.PLAN
        unresolved = [r for r in pending if decision.reasoning_result is None
                      or not decision.reasoning_result.success]
        for req in unresolved[:2]:
            subtasks = [
                {"name": "analyze", "description": req.task, "role": "contributor"},
                {"name": "validate", "description": "validate analysis", "role": "reviewer"},
            ]
            self._collaboration.propose_task(req.task, subtasks)
            decision.collaboration_tasks += 1

        # Phase 4: Synthesize - pull recent episodic memory and consolidate
        decision.phase = ArchitectPhase.SYNTHESIZE
        if self._kernel is not None:
            try:
                recent = self._kernel.recall("recent", limit=8)
                episodes = [
                    {
                        "id": getattr(e, "entry_id", ""),
                        "domain": "runtime",
                        "summary": str(getattr(e, "content", ""))[:200],
                        "content": str(getattr(e, "content", "")),
                    }
                    for e in recent
                ]
                if episodes:
                    facts = self._knowledge.consolidate(episodes)
                    decision.knowledge_synthesized = len(facts)
            except Exception as exc:
                decision.notes.append(f"knowledge_synthesis_failed: {exc}")

        # Decay knowledge salience each cycle
        self._knowledge.decay()

        # Phase 5: Reflect - record the decision
        decision.phase = ArchitectPhase.REFLECT
        decision.duration_s = time.time() - start
        with self._lock:
            self._last_result = decision

        # Emit directives to the brain if available
        if self._brain is not None and decision.reasoning_result is not None:
            decision.directives.append({
                "source": "architect",
                "intent": decision.reasoning_result.conclusion[:100],
                "confidence": decision.reasoning_result.confidence,
            })

        return decision

    # -----------------------------------------------------------------
    # Status and Inspection
    # -----------------------------------------------------------------

    def status(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "initialized": self._initialized,
                "cycle_count": self._cycle_count,
                "kernel_attached": self._kernel is not None,
                "integrator_attached": self._integrator is not None,
                "brain_attached": self._brain is not None,
                "pending_requests": len(self._pending_requests),
                "reasoning": self._reasoning.stats(),
                "tool_pipeline": self._tool_pipeline.stats(),
                "knowledge": self._knowledge.stats(),
                "collaboration": self._collaboration.stats(),
                "last_cycle": {
                    "phase": self._last_result.phase.value if self._last_result else None,
                    "tools_forged": len(self._last_result.tools_forged) if self._last_result else 0,
                    "knowledge_synthesized": self._last_result.knowledge_synthesized if self._last_result else 0,
                    "collaboration_tasks": self._last_result.collaboration_tasks if self._last_result else 0,
                    "duration_s": self._last_result.duration_s if self._last_result else 0,
                } if self._last_result else None,
            }

    def list_deployed_tools(self) -> List[Dict[str, Any]]:
        return [
            {
                "name": t.name, "intent": t.intent,
                "confidence": t.confidence, "stage": t.stage.value,
            }
            for t in self._tool_pipeline.list_deployed()
        ]

    def list_active_specs(self) -> List[Dict[str, Any]]:
        return [
            {
                "name": s.name, "intent": s.intent,
                "stage": s.stage.value, "confidence": s.confidence,
                "failure_count": s.failure_count,
            }
            for s in self._tool_pipeline.list_active()
        ]

    def list_facts(self, domain: Optional[str] = None, limit: int = 10) -> List[Dict[str, Any]]:
        facts = self._knowledge.retrieve("", domain=domain, limit=limit)
        return [
            {
                "fact_id": f.fact_id, "domain": f.domain,
                "statement": f.statement[:200], "confidence": f.confidence,
                "salience": f.salience, "tags": f.tags,
            }
            for f in facts
        ]

    def reset(self) -> None:
        """Reset the architect state (preserves wiring)."""
        with self._lock:
            self._cycle_count = 0
            self._last_result = None
            self._pending_requests.clear()


# ---------------------------------------------------------------------------
# Module-level Convenience
# ---------------------------------------------------------------------------

def get_architect() -> CognitiveArchitect:
    return CognitiveArchitect.get_instance()


def quick_architect_status() -> Dict[str, Any]:
    return get_architect().status()
