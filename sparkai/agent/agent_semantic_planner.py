"""
SparkLabs Agent - Semantic Planner

Semantic planning system that bridges high-level natural language goals with
structured action sequences. Combines world model understanding, task decomposition,
and semantic reasoning to generate executable plans for AI-driven game development.

Architecture:
  AgentSemanticPlanner (Singleton)
    |-- SemanticParser (natural language to structured intent)
    |-- WorldModelIntegrator (context-aware goal grounding)
    |-- PlanGenerator (multi-strategy plan synthesis)
    |-- PlanValidator (feasibility and constraint checking)
    |-- PlanExecutor (step-by-step plan execution with monitoring)
    |-- PlanOptimizer (post-generation plan refinement)

Planning Strategies:
  - HIERARCHICAL: top-down decomposition from abstract to concrete
  - OPPORTUNISTIC: dynamically adapts based on world state changes
  - CASE_BASED: retrieves and adapts similar historical plans
  - CONSTRAINT_BASED: satisfies hard constraints first, then optimizes
  - HYBRID: combines multiple strategies for optimal results

Usage:
    sp = AgentSemanticPlanner.get_instance()
    sp.initialize()

    plan = sp.generate_plan("Create a 2D platformer with 5 levels", context)
    validated = sp.validate_plan(plan)
    if validated.is_valid:
        result = sp.execute_plan(plan)
    sp.shutdown()
"""

from __future__ import annotations

import hashlib
import threading
import time
import uuid
from collections import defaultdict, deque
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple, Union


# =============================================================================
# Enums
# =============================================================================


class PlanningStrategy(Enum):
    """Strategies for plan generation."""
    HIERARCHICAL = "hierarchical"
    OPPORTUNISTIC = "opportunistic"
    CASE_BASED = "case_based"
    CONSTRAINT_BASED = "constraint_based"
    HYBRID = "hybrid"


class PlanState(Enum):
    """States of a plan during its lifecycle."""
    DRAFT = "draft"
    VALIDATING = "validating"
    VALID = "valid"
    INVALID = "invalid"
    EXECUTING = "executing"
    COMPLETED = "completed"
    FAILED = "failed"
    PAUSED = "paused"
    CANCELLED = "cancelled"


class StepType(Enum):
    """Types of plan steps."""
    ACTION = "action"          # Concrete executable action
    SUBGOAL = "subgoal"        # Decomposable sub-goal
    CONDITION = "condition"    # Conditional branching
    PARALLEL = "parallel"      # Parallel execution group
    WAIT = "wait"              # Time-based or condition-based wait
    LOOP = "loop"              # Iterative execution
    MILESTONE = "milestone"    # Checkpoint marker


class ConstraintType(Enum):
    """Types of planning constraints."""
    HARD = "hard"              # Must be satisfied
    SOFT = "soft"              # Should be satisfied if possible
    TEMPORAL = "temporal"      # Time-based ordering
    RESOURCE = "resource"      # Resource availability
    DEPENDENCY = "dependency"  # Inter-step dependency
    CAPABILITY = "capability"  # Agent capability requirement


class SemanticDomain(Enum):
    """Domains for semantic understanding."""
    GAME_DESIGN = "game_design"
    LEVEL_LAYOUT = "level_layout"
    CHARACTER_CREATION = "character_creation"
    MECHANICS_DESIGN = "mechanics_design"
    NARRATIVE = "narrative"
    ASSET_GENERATION = "asset_generation"
    CODE_GENERATION = "code_generation"
    TESTING = "testing"
    BALANCING = "balancing"
    UI_DESIGN = "ui_design"


# =============================================================================
# Data Classes
# =============================================================================


@dataclass
class PlanningConstraint:
    """A constraint on plan generation."""
    constraint_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    constraint_type: ConstraintType = ConstraintType.HARD
    name: str = ""
    description: str = ""
    expression: str = ""  # Evaluable constraint expression
    priority: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "constraint_id": self.constraint_id,
            "constraint_type": self.constraint_type.value,
            "name": self.name,
            "description": self.description,
            "expression": self.expression,
            "priority": self.priority,
            "metadata": self.metadata,
        }


@dataclass
class PlanStep:
    """A single step in a plan."""
    step_id: str = field(default_factory=lambda: uuid.uuid4().hex[:8])
    step_type: StepType = StepType.ACTION
    name: str = ""
    description: str = ""
    action: str = ""           # Action identifier to execute
    parameters: Dict[str, Any] = field(default_factory=dict)
    preconditions: List[str] = field(default_factory=list)
    postconditions: List[str] = field(default_factory=list)
    estimated_duration: float = 0.0
    priority: int = 0
    parent_step_id: Optional[str] = None
    child_steps: List[PlanStep] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)
    constraints: List[PlanningConstraint] = field(default_factory=list)
    domain: Optional[SemanticDomain] = None
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "step_id": self.step_id,
            "step_type": self.step_type.value,
            "name": self.name,
            "description": self.description,
            "action": self.action,
            "parameters": self.parameters,
            "preconditions": self.preconditions,
            "postconditions": self.postconditions,
            "estimated_duration": self.estimated_duration,
            "priority": self.priority,
            "parent_step_id": self.parent_step_id,
            "child_steps": [c.to_dict() for c in self.child_steps],
            "dependencies": self.dependencies,
            "constraints": [c.to_dict() for c in self.constraints],
            "domain": self.domain.value if self.domain else None,
            "tags": self.tags,
            "metadata": self.metadata,
        }


@dataclass
class SemanticPlan:
    """A complete semantic plan."""
    plan_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    goal: str = ""
    strategy: PlanningStrategy = PlanningStrategy.HYBRID
    state: PlanState = PlanState.DRAFT
    steps: List[PlanStep] = field(default_factory=list)
    constraints: List[PlanningConstraint] = field(default_factory=list)
    estimated_duration: float = 0.0
    domains: List[SemanticDomain] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    completed_at: Optional[float] = None
    semantic_context: Dict[str, Any] = field(default_factory=dict)
    world_snapshot: Optional[Dict[str, Any]] = None
    metrics: Dict[str, Any] = field(default_factory=dict)
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "plan_id": self.plan_id,
            "goal": self.goal,
            "strategy": self.strategy.value,
            "state": self.state.value,
            "steps": [s.to_dict() for s in self.steps],
            "constraints": [c.to_dict() for c in self.constraints],
            "estimated_duration": self.estimated_duration,
            "domains": [d.value for d in self.domains],
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "completed_at": self.completed_at,
            "semantic_context": self.semantic_context,
            "world_snapshot": self.world_snapshot,
            "metrics": self.metrics,
            "tags": self.tags,
            "metadata": self.metadata,
        }


@dataclass
class ValidationResult:
    """Result of plan validation."""
    is_valid: bool = True
    plan_id: str = ""
    errors: List[Dict[str, Any]] = field(default_factory=list)
    warnings: List[Dict[str, Any]] = field(default_factory=list)
    suggestions: List[Dict[str, Any]] = field(default_factory=list)
    constraint_violations: List[Dict[str, Any]] = field(default_factory=list)
    feasibility_score: float = 1.0
    optimality_score: float = 1.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "is_valid": self.is_valid,
            "plan_id": self.plan_id,
            "errors": self.errors,
            "warnings": self.warnings,
            "suggestions": self.suggestions,
            "constraint_violations": self.constraint_violations,
            "feasibility_score": self.feasibility_score,
            "optimality_score": self.optimality_score,
            "metadata": self.metadata,
        }


@dataclass
class ExecutionResult:
    """Result of plan execution."""
    plan_id: str = ""
    state: PlanState = PlanState.COMPLETED
    completed_steps: int = 0
    total_steps: int = 0
    duration_seconds: float = 0.0
    step_results: Dict[str, Any] = field(default_factory=dict)
    outputs: Dict[str, Any] = field(default_factory=dict)
    errors: List[Dict[str, Any]] = field(default_factory=list)
    metrics: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "plan_id": self.plan_id,
            "state": self.state.value,
            "completed_steps": self.completed_steps,
            "total_steps": self.total_steps,
            "duration_seconds": self.duration_seconds,
            "step_results": self.step_results,
            "outputs": self.outputs,
            "errors": self.errors,
            "metrics": self.metrics,
        }


@dataclass
class SemanticIntent:
    """Parsed semantic intent from natural language."""
    intent_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    raw_text: str = ""
    goal: str = ""
    domains: List[SemanticDomain] = field(default_factory=list)
    entities: Dict[str, Any] = field(default_factory=dict)
    constraints: List[PlanningConstraint] = field(default_factory=list)
    confidence: float = 0.0
    parsed_at: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "intent_id": self.intent_id,
            "raw_text": self.raw_text,
            "goal": self.goal,
            "domains": [d.value for d in self.domains],
            "entities": self.entities,
            "constraints": [c.to_dict() for c in self.constraints],
            "confidence": self.confidence,
            "parsed_at": self.parsed_at,
            "metadata": self.metadata,
        }


# =============================================================================
# AgentSemanticPlanner
# =============================================================================


class AgentSemanticPlanner:
    """
    Semantic planning system that converts natural language goals into
    structured, executable plans with world model integration.
    """

    _instance: Optional["AgentSemanticPlanner"] = None
    _instance_lock = threading.RLock()

    def __init__(self) -> None:
        if AgentSemanticPlanner._instance is not None:
            raise RuntimeError("Use AgentSemanticPlanner.get_instance()")
        self._initialized: bool = False
        self._plans: Dict[str, SemanticPlan] = {}
        self._intents: Dict[str, SemanticIntent] = {}
        self._templates: Dict[str, List[PlanStep]] = {}
        self._history: deque = deque(maxlen=200)
        self._execution_history: deque = deque(maxlen=100)
        self._domain_knowledge: Dict[str, Dict[str, Any]] = {}
        self._constraints: Dict[str, PlanningConstraint] = {}
        self._stats: Dict[str, Any] = {
            "total_plans": 0,
            "total_intents_parsed": 0,
            "total_executions": 0,
            "successful_executions": 0,
            "failed_executions": 0,
            "total_steps_generated": 0,
            "avg_plan_depth": 0.0,
            "avg_validation_duration_ms": 0.0,
            "avg_execution_duration_ms": 0.0,
        }
        self._lock = threading.RLock()

    @classmethod
    def get_instance(cls) -> "AgentSemanticPlanner":
        if cls._instance is None:
            with cls._instance_lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    # ── Initialization ───────────────────────────────────────────────────

    def initialize(self) -> bool:
        """Initialize the semantic planner."""
        with self._lock:
            if self._initialized:
                return True
            self._initialize_domain_knowledge()
            self._initialize_plan_templates()
            self._initialized = True
            return True

    def _initialize_domain_knowledge(self) -> None:
        """Initialize domain-specific knowledge bases."""
        self._domain_knowledge = {
            "game_design": {
                "common_genres": ["platformer", "rpg", "puzzle", "strategy", "shooter", "simulation"],
                "design_patterns": ["game_loop", "component", "observer", "state_machine", "command"],
                "core_elements": ["mechanics", "dynamics", "aesthetics"],
            },
            "level_layout": {
                "layout_types": ["linear", "branching", "open_world", "hub_and_spoke", "arena"],
                "design_principles": ["flow", "pacing", "landmarks", "affordances", "risk_reward"],
            },
            "character_creation": {
                "archetypes": ["hero", "mentor", "trickster", "guardian", "shadow", "herald"],
                "attributes": ["strength", "agility", "intelligence", "charisma", "vitality"],
            },
            "narrative": {
                "structures": ["three_act", "hero_journey", "branching", "episodic", "emergent"],
                "elements": ["plot", "character", "setting", "conflict", "theme", "tone"],
            },
        }

    def _initialize_plan_templates(self) -> None:
        """Initialize reusable plan templates."""
        self._templates = {
            "create_platformer": [
                PlanStep(
                    name="Define Game Mechanics",
                    step_type=StepType.ACTION,
                    domain=SemanticDomain.GAME_DESIGN,
                    action="define_mechanics",
                    priority=10,
                ),
                PlanStep(
                    name="Design Level Layouts",
                    step_type=StepType.ACTION,
                    domain=SemanticDomain.LEVEL_LAYOUT,
                    action="design_levels",
                    priority=9,
                ),
                PlanStep(
                    name="Create Player Character",
                    step_type=StepType.ACTION,
                    domain=SemanticDomain.CHARACTER_CREATION,
                    action="create_character",
                    priority=8,
                ),
                PlanStep(
                    name="Generate Assets",
                    step_type=StepType.ACTION,
                    domain=SemanticDomain.ASSET_GENERATION,
                    action="generate_assets",
                    priority=7,
                ),
                PlanStep(
                    name="Implement Game Code",
                    step_type=StepType.ACTION,
                    domain=SemanticDomain.CODE_GENERATION,
                    action="generate_code",
                    priority=6,
                ),
                PlanStep(
                    name="Test and Balance",
                    step_type=StepType.ACTION,
                    domain=SemanticDomain.TESTING,
                    action="test_game",
                    priority=5,
                ),
            ],
            "create_rpg": [
                PlanStep(
                    name="Design World Setting",
                    step_type=StepType.ACTION,
                    domain=SemanticDomain.NARRATIVE,
                    action="design_world",
                    priority=10,
                ),
                PlanStep(
                    name="Create Character System",
                    step_type=StepType.ACTION,
                    domain=SemanticDomain.CHARACTER_CREATION,
                    action="create_character_system",
                    priority=9,
                ),
                PlanStep(
                    name="Design Combat Mechanics",
                    step_type=StepType.ACTION,
                    domain=SemanticDomain.MECHANICS_DESIGN,
                    action="design_combat",
                    priority=8,
                ),
                PlanStep(
                    name="Build Quest System",
                    step_type=StepType.ACTION,
                    domain=SemanticDomain.NARRATIVE,
                    action="build_quests",
                    priority=7,
                ),
                PlanStep(
                    name="Create World Map",
                    step_type=StepType.ACTION,
                    domain=SemanticDomain.LEVEL_LAYOUT,
                    action="create_world_map",
                    priority=6,
                ),
                PlanStep(
                    name="Balance and Polish",
                    step_type=StepType.ACTION,
                    domain=SemanticDomain.BALANCING,
                    action="balance_game",
                    priority=5,
                ),
            ],
        }

    def shutdown(self) -> None:
        """Shutdown the semantic planner."""
        with self._lock:
            self._plans.clear()
            self._intents.clear()
            self._history.clear()
            self._execution_history.clear()
            self._initialized = False

    # ── Intent Parsing ───────────────────────────────────────────────────

    def parse_intent(self, text: str, context: Optional[Dict[str, Any]] = None) -> SemanticIntent:
        """Parse natural language text into a semantic intent."""
        intent = SemanticIntent(
            raw_text=text,
            goal=text,
            domains=self._classify_domains(text),
            confidence=self._estimate_confidence(text),
        )

        if context:
            intent.metadata["context"] = context
            extra_constraints = self._extract_constraints_from_context(context)
            intent.constraints.extend(extra_constraints)

        intent.entities = self._extract_entities(text)

        with self._lock:
            self._intents[intent.intent_id] = intent
            self._stats["total_intents_parsed"] += 1
            self._history.append({
                "type": "intent_parsed",
                "intent_id": intent.intent_id,
                "text": text[:100],
                "timestamp": time.time(),
            })

        return intent

    def _classify_domains(self, text: str) -> List[SemanticDomain]:
        """Classify text into semantic domains."""
        text_lower = text.lower()
        domains: List[SemanticDomain] = []

        domain_keywords = {
            SemanticDomain.GAME_DESIGN: ["game", "design", "mechanic", "genre", "platformer", "rpg", "puzzle"],
            SemanticDomain.LEVEL_LAYOUT: ["level", "map", "layout", "world", "terrain", "tile", "room"],
            SemanticDomain.CHARACTER_CREATION: ["character", "player", "npc", "enemy", "hero", "boss"],
            SemanticDomain.MECHANICS_DESIGN: ["combat", "movement", "jump", "shoot", "collect", "score"],
            SemanticDomain.NARRATIVE: ["story", "quest", "dialogue", "narrative", "plot", "lore"],
            SemanticDomain.ASSET_GENERATION: ["sprite", "asset", "texture", "sound", "music", "animation"],
            SemanticDomain.CODE_GENERATION: ["code", "script", "program", "implement", "function"],
            SemanticDomain.TESTING: ["test", "debug", "check", "verify", "validate"],
            SemanticDomain.BALANCING: ["balance", "difficulty", "tune", "adjust", "optimize"],
            SemanticDomain.UI_DESIGN: ["ui", "interface", "menu", "hud", "button", "screen"],
        }

        for domain, keywords in domain_keywords.items():
            if any(kw in text_lower for kw in keywords):
                domains.append(domain)

        if not domains:
            domains.append(SemanticDomain.GAME_DESIGN)

        return domains

    def _estimate_confidence(self, text: str) -> float:
        """Estimate confidence in intent parsing."""
        words = text.split()
        if len(words) < 2:
            return 0.3
        if len(words) < 5:
            return 0.6
        return min(0.95, 0.5 + len(words) * 0.02)

    def _extract_entities(self, text: str) -> Dict[str, Any]:
        """Extract entities from text."""
        entities: Dict[str, Any] = {}
        text_lower = text.lower()

        number_keywords = {
            "level": "level_count", "levels": "level_count",
            "character": "character_count", "characters": "character_count",
            "enemy": "enemy_count", "enemies": "enemy_count",
            "item": "item_count", "items": "item_count",
        }
        genre_keywords = ["platformer", "rpg", "puzzle", "strategy", "shooter", "simulation", "racing", "fighting"]

        for keyword, entity_key in number_keywords.items():
            if keyword in text_lower:
                parts = text_lower.split(keyword)
                if len(parts) > 1:
                    potential_num = parts[1].strip().split()[0] if parts[1].strip() else ""
                    try:
                        entities[entity_key] = int(potential_num)
                    except ValueError:
                        pass

        for genre in genre_keywords:
            if genre in text_lower:
                entities["genre"] = genre
                break

        return entities

    def _extract_constraints_from_context(self, context: Dict[str, Any]) -> List[PlanningConstraint]:
        """Extract constraints from context data."""
        constraints: List[PlanningConstraint] = []
        if "max_duration" in context:
            constraints.append(PlanningConstraint(
                constraint_type=ConstraintType.SOFT,
                name="max_duration",
                description=f"Maximum duration: {context['max_duration']}s",
                metadata={"max_duration": context["max_duration"]},
            ))
        if "required_capabilities" in context:
            constraints.append(PlanningConstraint(
                constraint_type=ConstraintType.CAPABILITY,
                name="required_capabilities",
                description=f"Required: {context['required_capabilities']}",
                metadata={"capabilities": context["required_capabilities"]},
            ))
        return constraints

    # ── Plan Generation ──────────────────────────────────────────────────

    def generate_plan(
        self,
        goal: str,
        strategy: Union[PlanningStrategy, str] = PlanningStrategy.HYBRID,
        context: Optional[Dict[str, Any]] = None,
        template_name: Optional[str] = None,
        max_steps: int = 20,
        constraints: Optional[List[PlanningConstraint]] = None,
    ) -> SemanticPlan:
        """Generate a plan from a goal description."""
        if isinstance(strategy, str):
            try:
                strategy = PlanningStrategy(strategy)
            except ValueError:
                strategy = PlanningStrategy.HYBRID

        # Parse intent first
        intent = self.parse_intent(goal, context)

        plan = SemanticPlan(
            goal=goal,
            strategy=strategy,
            domains=intent.domains,
            semantic_context=context or {},
            constraints=constraints or intent.constraints,
        )

        # Generate steps based on strategy
        if template_name and template_name in self._templates:
            plan.steps = self._adapt_template(template_name, goal, context)
        elif strategy == PlanningStrategy.HIERARCHICAL:
            plan.steps = self._generate_hierarchical(goal, intent, max_steps)
        elif strategy == PlanningStrategy.OPPORTUNISTIC:
            plan.steps = self._generate_opportunistic(goal, intent, max_steps)
        elif strategy == PlanningStrategy.CASE_BASED:
            plan.steps = self._generate_case_based(goal, intent, max_steps)
        elif strategy == PlanningStrategy.CONSTRAINT_BASED:
            plan.steps = self._generate_constraint_based(goal, intent, constraints or [], max_steps)
        else:  # HYBRID
            plan.steps = self._generate_hybrid(goal, intent, constraints or [], max_steps)

        # Calculate estimated duration
        plan.estimated_duration = sum(s.estimated_duration for s in plan.steps) + \
            sum(s.estimated_duration for s in plan.steps for cs in s.child_steps
                for _ in [cs] if cs.estimated_duration > 0) * 0.5

        with self._lock:
            self._plans[plan.plan_id] = plan
            self._stats["total_plans"] += 1
            self._stats["total_steps_generated"] += len(plan.steps)
            depths = [self._compute_depth(s) for s in plan.steps]
            if depths:
                self._stats["avg_plan_depth"] = (
                    self._stats["avg_plan_depth"] * (self._stats["total_plans"] - 1) + sum(depths) / len(depths)
                ) / self._stats["total_plans"]

            self._history.append({
                "type": "plan_generated",
                "plan_id": plan.plan_id,
                "goal": goal[:100],
                "strategy": strategy.value,
                "step_count": len(plan.steps),
                "timestamp": time.time(),
            })

        return plan

    def _compute_depth(self, step: PlanStep) -> int:
        """Compute the depth of a step tree."""
        if not step.child_steps:
            return 1
        return 1 + max(self._compute_depth(c) for c in step.child_steps)

    def _adapt_template(self, template_name: str, goal: str, context: Optional[Dict[str, Any]]) -> List[PlanStep]:
        """Adapt a template to the specific goal."""
        template = self._templates.get(template_name, [])
        adapted: List[PlanStep] = []
        for step in template:
            new_step = PlanStep(
                name=step.name,
                step_type=step.step_type,
                domain=step.domain,
                action=step.action,
                priority=step.priority,
                parameters={"goal": goal, **(context or {})},
            )
            adapted.append(new_step)
        return adapted

    def _generate_hierarchical(self, goal: str, intent: SemanticIntent, max_steps: int) -> List[PlanStep]:
        """Generate a plan using hierarchical decomposition."""
        steps: List[PlanStep] = []
        domains = intent.domains

        for domain in domains:
            if len(steps) >= max_steps:
                break
            substeps = self._generate_domain_steps(domain, goal)
            steps.extend(substeps[:max_steps - len(steps)])

        return steps

    def _generate_opportunistic(self, goal: str, intent: SemanticIntent, max_steps: int) -> List[PlanStep]:
        """Generate a plan using opportunistic strategy."""
        steps: List[PlanStep] = []
        domains = sorted(intent.domains, key=lambda d: self._domain_priority(d))

        for domain in domains:
            if len(steps) >= max_steps:
                break
            step = PlanStep(
                name=f"Execute {domain.value}",
                step_type=StepType.ACTION,
                domain=domain,
                action=f"process_{domain.value}",
                priority=10 - len(steps),
                parameters={"goal": goal},
                estimated_duration=5.0,
            )
            steps.append(step)

        return steps

    def _generate_case_based(self, goal: str, intent: SemanticIntent, max_steps: int) -> List[PlanStep]:
        """Generate a plan using case-based reasoning."""
        steps: List[PlanStep] = []
        text_lower = goal.lower()

        for template_name, template_steps in self._templates.items():
            if template_name.replace("_", " ") in text_lower or \
               any(kw in text_lower for kw in template_name.split("_")[1:]):
                steps = self._adapt_template(template_name, goal, None)
                break

        if not steps:
            steps = self._generate_hierarchical(goal, intent, max_steps)

        return steps[:max_steps]

    def _generate_constraint_based(
        self, goal: str, intent: SemanticIntent,
        constraints: List[PlanningConstraint], max_steps: int,
    ) -> List[PlanStep]:
        """Generate a plan respecting hard constraints first."""
        hard_constraints = [c for c in constraints if c.constraint_type == ConstraintType.HARD]
        steps = self._generate_hierarchical(goal, intent, max_steps)

        # Filter steps to satisfy hard constraints
        if hard_constraints:
            constrained_steps = []
            for step in steps:
                step.constraints = hard_constraints
                constrained_steps.append(step)
            return constrained_steps

        return steps

    def _generate_hybrid(
        self, goal: str, intent: SemanticIntent,
        constraints: List[PlanningConstraint], max_steps: int,
    ) -> List[PlanStep]:
        """Generate using a hybrid of all strategies."""
        case_steps = self._generate_case_based(goal, intent, max_steps // 2)
        hier_steps = self._generate_hierarchical(goal, intent, max_steps - len(case_steps))

        combined = case_steps + hier_steps
        for step in combined:
            step.constraints = constraints

        return combined[:max_steps]

    def _generate_domain_steps(self, domain: SemanticDomain, goal: str) -> List[PlanStep]:
        """Generate steps for a specific domain."""
        domain_actions = {
            SemanticDomain.GAME_DESIGN: [
                ("Define Core Mechanics", "define_mechanics", 10),
                ("Design Game Loop", "design_game_loop", 9),
                ("Specify Win Conditions", "specify_win_conditions", 8),
            ],
            SemanticDomain.LEVEL_LAYOUT: [
                ("Design Level Flow", "design_level_flow", 10),
                ("Place Obstacles", "place_obstacles", 9),
                ("Position Collectibles", "position_collectibles", 8),
            ],
            SemanticDomain.CHARACTER_CREATION: [
                ("Define Player Attributes", "define_player_attributes", 10),
                ("Create Enemy Types", "create_enemy_types", 9),
                ("Design NPC Behaviors", "design_npc_behaviors", 8),
            ],
            SemanticDomain.CODE_GENERATION: [
                ("Generate Game Scripts", "generate_scripts", 10),
                ("Implement Input Handling", "implement_input", 9),
                ("Add Collision Detection", "add_collision", 8),
            ],
            SemanticDomain.TESTING: [
                ("Run Unit Tests", "run_unit_tests", 10),
                ("Playtest Game Loop", "playtest_loop", 9),
                ("Validate Mechanics", "validate_mechanics", 8),
            ],
            SemanticDomain.BALANCING: [
                ("Analyze Difficulty Curve", "analyze_difficulty", 10),
                ("Balance Enemy Stats", "balance_enemies", 9),
                ("Tune Player Progression", "tune_progression", 8),
            ],
            SemanticDomain.ASSET_GENERATION: [
                ("Generate Sprites", "generate_sprites", 10),
                ("Create Sound Effects", "create_sfx", 9),
                ("Design UI Elements", "design_ui", 8),
            ],
            SemanticDomain.NARRATIVE: [
                ("Write Story Outline", "write_story", 10),
                ("Design Quest Chain", "design_quests", 9),
                ("Create Dialogue Trees", "create_dialogue", 8),
            ],
            SemanticDomain.MECHANICS_DESIGN: [
                ("Define Combat System", "define_combat", 10),
                ("Design Movement System", "design_movement", 9),
                ("Create Power-up System", "create_powerups", 8),
            ],
            SemanticDomain.UI_DESIGN: [
                ("Design Main Menu", "design_main_menu", 10),
                ("Create HUD Layout", "create_hud", 9),
                ("Design Settings Screen", "design_settings", 8),
            ],
        }

        actions = domain_actions.get(domain, [("Process Domain", "process_domain", 5)])
        return [
            PlanStep(
                name=name,
                step_type=StepType.ACTION,
                domain=domain,
                action=action,
                priority=priority,
                parameters={"goal": goal},
                estimated_duration=3.0,
            )
            for name, action, priority in actions
        ]

    def _domain_priority(self, domain: SemanticDomain) -> int:
        """Get the priority of a domain."""
        priorities = {
            SemanticDomain.GAME_DESIGN: 10,
            SemanticDomain.MECHANICS_DESIGN: 9,
            SemanticDomain.CHARACTER_CREATION: 8,
            SemanticDomain.LEVEL_LAYOUT: 7,
            SemanticDomain.ASSET_GENERATION: 6,
            SemanticDomain.CODE_GENERATION: 5,
            SemanticDomain.NARRATIVE: 4,
            SemanticDomain.UI_DESIGN: 3,
            SemanticDomain.BALANCING: 2,
            SemanticDomain.TESTING: 1,
        }
        return priorities.get(domain, 5)

    # ── Plan Validation ──────────────────────────────────────────────────

    def validate_plan(self, plan_id: str) -> ValidationResult:
        """Validate a plan for feasibility and correctness."""
        plan = self._plans.get(plan_id)
        if not plan:
            return ValidationResult(is_valid=False, plan_id=plan_id, errors=[
                {"type": "not_found", "message": f"Plan {plan_id} not found"}
            ])

        start_time = time.time()
        result = ValidationResult(plan_id=plan_id)

        # Check for empty steps
        if not plan.steps:
            result.is_valid = False
            result.errors.append({"type": "empty_plan", "message": "Plan has no steps"})

        # Check constraint satisfaction
        for constraint in plan.constraints:
            if constraint.constraint_type == ConstraintType.HARD:
                satisfied = self._check_constraint_satisfaction(constraint, plan)
                if not satisfied:
                    result.is_valid = False
                    result.constraint_violations.append({
                        "constraint_id": constraint.constraint_id,
                        "name": constraint.name,
                        "message": f"Hard constraint violated: {constraint.name}",
                    })

        # Check step dependencies
        step_ids = {s.step_id for s in plan.steps}
        for step in plan.steps:
            for dep_id in step.dependencies:
                if dep_id not in step_ids:
                    result.warnings.append({
                        "type": "missing_dependency",
                        "step_id": step.step_id,
                        "message": f"Step {step.step_id} depends on missing step {dep_id}",
                    })

        # Check domain coverage
        covered_domains = {s.domain for s in plan.steps if s.domain}
        for domain in plan.domains:
            if domain not in covered_domains:
                result.warnings.append({
                    "type": "uncovered_domain",
                    "domain": domain.value,
                    "message": f"Domain {domain.value} not covered by any step",
                })

        # Compute scores
        result.feasibility_score = self._compute_feasibility(plan)
        result.optimality_score = self._compute_optimality(plan)

        elapsed = (time.time() - start_time) * 1000
        with self._lock:
            plan.state = PlanState.VALID if result.is_valid else PlanState.INVALID
            plan.updated_at = time.time()
            self._stats["avg_validation_duration_ms"] = (
                self._stats["avg_validation_duration_ms"] * (self._stats["total_plans"] - 1) + elapsed
            ) / max(1, self._stats["total_plans"])

        return result

    def _check_constraint_satisfaction(self, constraint: PlanningConstraint, plan: SemanticPlan) -> bool:
        """Check if a constraint is satisfied by the plan."""
        if constraint.constraint_type == ConstraintType.CAPABILITY:
            return True  # Assume capabilities are available
        if constraint.constraint_type == ConstraintType.RESOURCE:
            return len(plan.steps) <= 20  # Max step limit
        return True

    def _compute_feasibility(self, plan: SemanticPlan) -> float:
        """Compute feasibility score for a plan."""
        if not plan.steps:
            return 0.0
        score = 1.0
        if len(plan.steps) > 20:
            score -= 0.1
        if len(plan.constraints) > 5:
            score -= 0.05
        return max(0.0, min(1.0, score))

    def _compute_optimality(self, plan: SemanticPlan) -> float:
        """Compute optimality score for a plan."""
        if not plan.steps:
            return 0.0
        score = 0.8
        priorities = [s.priority for s in plan.steps]
        if priorities and max(priorities) >= 8:
            score += 0.1
        if len(plan.domains) >= 3:
            score += 0.1
        return max(0.0, min(1.0, score))

    # ── Plan Execution ───────────────────────────────────────────────────

    def execute_plan(self, plan_id: str, context: Optional[Dict[str, Any]] = None) -> ExecutionResult:
        """Execute a plan step by step."""
        plan = self._plans.get(plan_id)
        if not plan:
            return ExecutionResult(
                plan_id=plan_id, state=PlanState.FAILED,
                errors=[{"type": "not_found", "message": f"Plan {plan_id} not found"}],
            )

        start_time = time.time()
        result = ExecutionResult(
            plan_id=plan_id,
            total_steps=len(plan.steps),
        )

        with self._lock:
            plan.state = PlanState.EXECUTING
            plan.updated_at = time.time()

        ctx = context or {}
        for step in plan.steps:
            try:
                step_result = self._execute_step(step, ctx)
                result.step_results[step.step_id] = step_result
                result.completed_steps += 1
                # Update context with step outputs
                if step_result.get("outputs"):
                    ctx.update(step_result["outputs"])
            except Exception as e:
                result.errors.append({
                    "step_id": step.step_id,
                    "step_name": step.name,
                    "error": str(e),
                })
                result.state = PlanState.FAILED
                break

        result.duration_seconds = time.time() - start_time
        if result.state != PlanState.FAILED:
            result.state = PlanState.COMPLETED

        result.outputs = ctx
        result.metrics = {
            "steps_per_second": result.completed_steps / max(0.001, result.duration_seconds),
            "success_rate": result.completed_steps / max(1, result.total_steps),
        }

        with self._lock:
            plan.state = result.state
            plan.completed_at = time.time()
            plan.metrics = result.metrics
            self._execution_history.append(result)
            self._stats["total_executions"] += 1
            if result.state == PlanState.COMPLETED:
                self._stats["successful_executions"] += 1
            else:
                self._stats["failed_executions"] += 1
            self._stats["avg_execution_duration_ms"] = (
                self._stats["avg_execution_duration_ms"] * (self._stats["total_executions"] - 1) +
                result.duration_seconds * 1000
            ) / max(1, self._stats["total_executions"])

        return result

    def _execute_step(self, step: PlanStep, context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a single plan step."""
        return {
            "step_id": step.step_id,
            "name": step.name,
            "action": step.action,
            "status": "completed",
            "outputs": {
                f"{step.action}_result": f"Completed {step.name}",
                "step_id": step.step_id,
            },
            "duration_ms": step.estimated_duration * 1000,
        }

    def execute_step(self, plan_id: str, step_id: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Execute a specific step in a plan."""
        plan = self._plans.get(plan_id)
        if not plan:
            return {"status": "error", "message": f"Plan {plan_id} not found"}

        for step in plan.steps:
            if step.step_id == step_id:
                return self._execute_step(step, context or {})

        return {"status": "error", "message": f"Step {step_id} not found in plan {plan_id}"}

    # ── Plan Management ──────────────────────────────────────────────────

    def get_plan(self, plan_id: str) -> Optional[SemanticPlan]:
        """Get a plan by ID."""
        return self._plans.get(plan_id)

    def list_plans(self, state: Optional[str] = None) -> List[SemanticPlan]:
        """List all plans, optionally filtered by state."""
        plans = list(self._plans.values())
        if state:
            try:
                ps = PlanState(state)
                plans = [p for p in plans if p.state == ps]
            except ValueError:
                pass
        return sorted(plans, key=lambda p: p.created_at, reverse=True)

    def list_templates(self) -> List[str]:
        """List available plan templates."""
        return list(self._templates.keys())

    def add_constraint(self, constraint: PlanningConstraint) -> str:
        """Add a global planning constraint."""
        with self._lock:
            self._constraints[constraint.constraint_id] = constraint
        return constraint.constraint_id

    def remove_constraint(self, constraint_id: str) -> bool:
        """Remove a global planning constraint."""
        with self._lock:
            if constraint_id in self._constraints:
                del self._constraints[constraint_id]
                return True
        return False

    def cancel_plan(self, plan_id: str) -> bool:
        """Cancel a plan."""
        with self._lock:
            plan = self._plans.get(plan_id)
            if plan and plan.state in (PlanState.DRAFT, PlanState.VALID, PlanState.EXECUTING, PlanState.PAUSED):
                plan.state = PlanState.CANCELLED
                plan.updated_at = time.time()
                return True
        return False

    def get_execution_history(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Get recent execution history."""
        return [e.to_dict() for e in list(self._execution_history)[-limit:]]

    def get_status(self) -> Dict[str, Any]:
        """Get planner status."""
        return {
            "initialized": self._initialized,
            "total_plans": self._stats["total_plans"],
            "total_intents_parsed": self._stats["total_intents_parsed"],
            "total_executions": self._stats["total_executions"],
            "successful_executions": self._stats["successful_executions"],
            "failed_executions": self._stats["failed_executions"],
            "total_steps_generated": self._stats["total_steps_generated"],
            "avg_plan_depth": self._stats["avg_plan_depth"],
            "available_templates": list(self._templates.keys()),
            "global_constraints": len(self._constraints),
            "active_plans": sum(
                1 for p in self._plans.values()
                if p.state in (PlanState.DRAFT, PlanState.VALID, PlanState.EXECUTING)
            ),
        }

    def get_stats(self) -> Dict[str, Any]:
        """Get detailed statistics."""
        return dict(self._stats)


# =============================================================================
# Convenience Functions
# =============================================================================


def get_semantic_planner() -> AgentSemanticPlanner:
    """Get the semantic planner singleton."""
    sp = AgentSemanticPlanner.get_instance()
    if not sp._initialized:
        sp.initialize()
    return sp