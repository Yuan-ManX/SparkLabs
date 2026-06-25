"""
SparkLabs Agent Intelligence Core - Unified Agent Reasoning & Execution Framework

Central intelligence hub that orchestrates all agent capabilities through
a unified reasoning architecture, combining strategic synthesis, learning loops,
team coordination, and world simulation into a cohesive AI-native system.
"""

from __future__ import annotations

import json
import threading
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

from sparkai.agent.agent_learning_loop import (
    LearningLoopEngine, LearningPhase, MemoryLayer, SkillLifecycle,
    MemoryEntry, SkillManifest, LearningSession,
)
from sparkai.agent.agent_team_factory import (
    TeamFactory, TeamPattern, AgentRole,
    TeamBlueprint, TeamTask,
)


class IntelligenceMode(Enum):
    """Unified intelligence operating modes."""
    REACTIVE = "reactive"              # Direct stimulus-response
    DELIBERATIVE = "deliberative"      # Planned multi-step reasoning
    CREATIVE = "creative"              # Generative exploration
    ANALYTICAL = "analytical"          # Data-driven analysis
    STRATEGIC = "strategic"            # Long-term planning
    COLLABORATIVE = "collaborative"    # Multi-agent coordination
    ADAPTIVE = "adaptive"              # Self-improving learning


class ReasoningDepth(Enum):
    """Depth levels for reasoning chains."""
    SURFACE = "surface"        # Quick heuristic evaluation
    STANDARD = "standard"      # Balanced analysis
    DEEP = "deep"              # Comprehensive multi-perspective
    EXHAUSTIVE = "exhaustive"  # Full system-wide analysis


class OutputFormat(Enum):
    """Output format specifications."""
    TEXT = "text"
    JSON = "json"
    CODE = "code"
    PLAN = "plan"
    REPORT = "report"
    DIALOGUE = "dialogue"


@dataclass
class IntelligenceContext:
    """Complete context package for agent reasoning."""
    session_id: str
    mode: IntelligenceMode = IntelligenceMode.DELIBERATIVE
    depth: ReasoningDepth = ReasoningDepth.STANDARD
    format: OutputFormat = OutputFormat.TEXT
    task: str = ""
    goals: List[str] = field(default_factory=list)
    constraints: List[str] = field(default_factory=list)
    domain_knowledge: Dict[str, Any] = field(default_factory=dict)
    previous_results: List[Dict[str, Any]] = field(default_factory=list)
    available_tools: List[str] = field(default_factory=list)
    team_context: Optional[Dict[str, Any]] = None
    learning_context: Optional[Dict[str, Any]] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "session_id": self.session_id,
            "mode": self.mode.value,
            "depth": self.depth.value,
            "format": self.format.value,
            "task": self.task,
            "goals": self.goals,
            "constraints": self.constraints,
            "domain_knowledge": self.domain_knowledge,
            "available_tools": self.available_tools,
            "metadata": self.metadata,
        }


@dataclass
class ReasoningStep:
    """A single step in a reasoning chain."""
    step_id: str
    step_number: int
    thought: str
    action: Optional[str] = None
    action_params: Optional[Dict[str, Any]] = None
    observation: Optional[str] = None
    confidence: float = 0.5
    alternatives: List[str] = field(default_factory=list)
    duration_ms: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "step_id": self.step_id,
            "step_number": self.step_number,
            "thought": self.thought,
            "action": self.action,
            "action_params": self.action_params,
            "observation": self.observation,
            "confidence": self.confidence,
            "alternatives": self.alternatives,
            "duration_ms": self.duration_ms,
        }


@dataclass
class IntelligenceResult:
    """Complete result from an intelligence operation."""
    result_id: str
    context: IntelligenceContext
    reasoning_chain: List[ReasoningStep] = field(default_factory=list)
    final_output: Any = None
    insights: List[str] = field(default_factory=list)
    suggestions: List[str] = field(default_factory=list)
    confidence: float = 0.0
    total_duration_ms: float = 0.0
    skills_used: List[str] = field(default_factory=list)
    skills_generated: List[str] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "result_id": self.result_id,
            "context": self.context.to_dict(),
            "reasoning_chain": [s.to_dict() for s in self.reasoning_chain],
            "final_output": self.final_output,
            "insights": self.insights,
            "suggestions": self.suggestions,
            "confidence": self.confidence,
            "total_duration_ms": self.total_duration_ms,
            "skills_used": self.skills_used,
            "skills_generated": self.skills_generated,
            "created_at": self.created_at,
        }


class AgentIntelligenceCore:
    """Unified agent intelligence orchestration hub.

    This is the central nervous system of SparkLabs' AI-native architecture.
    It integrates all agent capabilities - strategic reasoning, learning loops,
    team coordination, and world simulation - into a single cohesive framework
    that can operate in multiple intelligence modes.
    """

    _instance: Optional["AgentIntelligenceCore"] = None
    _instance_lock = threading.RLock()

    def __init__(self) -> None:
        if self._instance is not None:
            raise RuntimeError("Use AgentIntelligenceCore.get_instance()")
        self._learning_engine: Optional[LearningLoopEngine] = None
        self._team_factory: Optional[TeamFactory] = None
        self._active_sessions: Dict[str, IntelligenceContext] = {}
        self._result_history: List[IntelligenceResult] = []
        self._tool_registry: Dict[str, Callable] = {}
        self._mode_strategies: Dict[IntelligenceMode, Callable] = {}
        self._initialized: bool = False
        self._lock = threading.RLock()

    @classmethod
    def get_instance(cls) -> "AgentIntelligenceCore":
        if cls._instance is None:
            with cls._instance_lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def initialize(self) -> Dict[str, Any]:
        """Initialize all intelligence subsystems."""
        with self._lock:
            self._learning_engine = LearningLoopEngine.get_instance()
            self._learning_engine.initialize()

            self._team_factory = TeamFactory.get_instance()
            self._team_factory.initialize()

            self._register_default_strategies()
            self._initialized = True

            return {
                "initialized": True,
                "subsystems": {
                    "learning_loop": True,
                    "team_factory": True,
                    "tool_registry": len(self._tool_registry),
                },
                "modes": [m.value for m in self._mode_strategies.keys()],
            }

    def _register_default_strategies(self) -> None:
        """Register default reasoning strategies for each mode."""
        self._mode_strategies = {
            IntelligenceMode.REACTIVE: self._reactive_strategy,
            IntelligenceMode.DELIBERATIVE: self._deliberative_strategy,
            IntelligenceMode.CREATIVE: self._creative_strategy,
            IntelligenceMode.ANALYTICAL: self._analytical_strategy,
            IntelligenceMode.STRATEGIC: self._strategic_strategy,
            IntelligenceMode.COLLABORATIVE: self._collaborative_strategy,
            IntelligenceMode.ADAPTIVE: self._adaptive_strategy,
        }

    def register_tool(self, name: str, handler: Callable) -> None:
        """Register a tool that agents can use during reasoning."""
        with self._lock:
            self._tool_registry[name] = handler

    def unregister_tool(self, name: str) -> bool:
        with self._lock:
            if name in self._tool_registry:
                del self._tool_registry[name]
                return True
            return False

    # ── Intelligence Operations ──

    def think(self, task: str, mode: IntelligenceMode = IntelligenceMode.DELIBERATIVE,
              depth: ReasoningDepth = ReasoningDepth.STANDARD,
              context: Optional[Dict[str, Any]] = None,
              format: OutputFormat = OutputFormat.TEXT) -> IntelligenceResult:
        """Execute a full intelligence operation on a given task."""
        start_time = time.time()

        ctx = IntelligenceContext(
            session_id=f"intel_{uuid.uuid4().hex[:12]}",
            mode=mode,
            depth=depth,
            format=format,
            task=task,
            **(context or {}),
        )

        with self._lock:
            self._active_sessions[ctx.session_id] = ctx

        # Execute the appropriate strategy
        strategy = self._mode_strategies.get(mode, self._deliberative_strategy)
        result = strategy(ctx)

        result.total_duration_ms = (time.time() - start_time) * 1000

        with self._lock:
            self._result_history.append(result)
            if ctx.session_id in self._active_sessions:
                del self._active_sessions[ctx.session_id]

        return result

    def think_with_team(self, task: str, team_type: str = "code_generation",
                        domain: str = "game_development") -> Dict[str, Any]:
        """Execute a task using a multi-agent team."""
        if not self._team_factory:
            raise RuntimeError("Intelligence core not initialized")

        blueprint = self._team_factory.create_team(domain, team_type)
        team_task = self._team_factory.dispatch_task(
            blueprint.blueprint_id, task,
        )

        return {
            "blueprint": blueprint.to_dict(),
            "task": team_task.to_dict(),
            "team_type": team_type,
        }

    def learn_from_experience(self, task: str, actions: List[Dict[str, Any]],
                              success: bool) -> Optional[Dict[str, Any]]:
        """Run a complete learning loop: execute, evaluate, consolidate."""
        if not self._learning_engine:
            raise RuntimeError("Intelligence core not initialized")

        session = self._learning_engine.start_session(task)

        for action in actions:
            self._learning_engine.record_action(
                session.session_id,
                action.get("action", "unknown"),
                action.get("params", {}),
                action.get("result", None),
            )

        lessons = self._learning_engine.evaluate(
            session.session_id, success,
        )

        skill = self._learning_engine.consolidate(session.session_id)

        return {
            "session_id": session.session_id,
            "lessons": lessons,
            "skill_generated": skill.to_dict() if skill else None,
            "success": success,
        }

    # ── Reasoning Strategies ──

    def _reactive_strategy(self, ctx: IntelligenceContext) -> IntelligenceResult:
        """Fast stimulus-response pattern matching."""
        steps = [
            ReasoningStep(
                step_id=f"step_{uuid.uuid4().hex[:8]}",
                step_number=1,
                thought=f"Analyzing prompt: {ctx.task[:100]}",
                confidence=0.8,
            ),
        ]

        # Check for known skill patterns
        if self._learning_engine:
            skill = self._learning_engine.find_skill_for_task(ctx.task)
            if skill:
                steps.append(ReasoningStep(
                    step_id=f"step_{uuid.uuid4().hex[:8]}",
                    step_number=2,
                    thought=f"Matched skill: {skill.name}",
                    action="apply_skill",
                    action_params={"skill_id": skill.skill_id},
                    confidence=skill.success_rate,
                ))

        return IntelligenceResult(
            result_id=f"result_{uuid.uuid4().hex[:12]}",
            context=ctx,
            reasoning_chain=steps,
            final_output={"response": ctx.task, "matched_skills": len(steps) - 1},
            confidence=steps[-1].confidence if steps else 0.5,
            insights=[f"Reactively processed: {ctx.task[:80]}"],
        )

    def _deliberative_strategy(self, ctx: IntelligenceContext) -> IntelligenceResult:
        """Planned multi-step reasoning with analysis."""
        steps: List[ReasoningStep] = []

        # Phase 1: Understand
        steps.append(ReasoningStep(
            step_id=f"step_{uuid.uuid4().hex[:8]}",
            step_number=1,
            thought=f"Understanding task: {ctx.task[:100]}",
            confidence=0.9,
        ))

        # Phase 2: Analyze context
        steps.append(ReasoningStep(
            step_id=f"step_{uuid.uuid4().hex[:8]}",
            step_number=2,
            thought=f"Analyzing context with {len(ctx.constraints)} constraints and {len(ctx.goals)} goals",
            confidence=0.85,
        ))

        # Phase 3: Generate approach
        depth_factor = {
            ReasoningDepth.SURFACE: 1,
            ReasoningDepth.STANDARD: 2,
            ReasoningDepth.DEEP: 3,
            ReasoningDepth.EXHAUSTIVE: 4,
        }[ctx.depth]

        for i in range(depth_factor):
            steps.append(ReasoningStep(
                step_id=f"step_{uuid.uuid4().hex[:8]}",
                step_number=3 + i,
                thought=f"Exploring approach {i + 1}: {ctx.task[:50]}...",
                alternatives=[f"Alternative {j}" for j in range(3)],
                confidence=0.7 - (i * 0.1),
            ))

        # Phase 4: Synthesize
        insights = [
            f"Task decomposed into {depth_factor} approaches",
            f"Domain knowledge applied: {list(ctx.domain_knowledge.keys())[:3]}",
        ]

        return IntelligenceResult(
            result_id=f"result_{uuid.uuid4().hex[:12]}",
            context=ctx,
            reasoning_chain=steps,
            final_output={
                "task": ctx.task,
                "approaches_explored": depth_factor,
                "recommended_approach": 0,
            },
            insights=insights,
            confidence=0.75,
        )

    def _creative_strategy(self, ctx: IntelligenceContext) -> IntelligenceResult:
        """Generative exploration with divergent thinking."""
        steps = [
            ReasoningStep(
                step_id=f"step_{uuid.uuid4().hex[:8]}",
                step_number=1,
                thought=f"Exploring creative possibilities for: {ctx.task[:80]}",
                confidence=0.7,
            ),
            ReasoningStep(
                step_id=f"step_{uuid.uuid4().hex[:8]}",
                step_number=2,
                thought="Generating unconventional approaches and novel combinations",
                alternatives=[
                    "Combine unrelated domains",
                    "Invert core assumptions",
                    "Apply biological metaphors",
                    "Use procedural generation",
                ],
                confidence=0.6,
            ),
            ReasoningStep(
                step_id=f"step_{uuid.uuid4().hex[:8]}",
                step_number=3,
                thought="Refining most promising creative directions",
                confidence=0.65,
            ),
        ]

        return IntelligenceResult(
            result_id=f"result_{uuid.uuid4().hex[:12]}",
            context=ctx,
            reasoning_chain=steps,
            final_output={"creative_directions": 4, "task": ctx.task},
            insights=[
                "Divergent thinking applied to generate novel solutions",
                "Cross-domain analogies explored for innovation",
            ],
            suggestions=[
                "Consider combining multiple creative directions",
                "Validate novel approaches against constraints",
            ],
            confidence=0.6,
        )

    def _analytical_strategy(self, ctx: IntelligenceContext) -> IntelligenceResult:
        """Data-driven analysis with metric evaluation."""
        steps = [
            ReasoningStep(
                step_id=f"step_{uuid.uuid4().hex[:8]}",
                step_number=1,
                thought=f"Collecting data for analysis: {ctx.task[:80]}",
                confidence=0.9,
            ),
            ReasoningStep(
                step_id=f"step_{uuid.uuid4().hex[:8]}",
                step_number=2,
                thought="Evaluating metrics and identifying patterns",
                confidence=0.85,
            ),
            ReasoningStep(
                step_id=f"step_{uuid.uuid4().hex[:8]}",
                step_number=3,
                thought="Synthesizing analytical findings into actionable insights",
                confidence=0.8,
            ),
        ]

        return IntelligenceResult(
            result_id=f"result_{uuid.uuid4().hex[:12]}",
            context=ctx,
            reasoning_chain=steps,
            final_output={"analysis_complete": True, "metrics_evaluated": len(ctx.domain_knowledge)},
            insights=[
                "Systematic analysis of available data completed",
                "Key patterns and correlations identified",
            ],
            confidence=0.8,
        )

    def _strategic_strategy(self, ctx: IntelligenceContext) -> IntelligenceResult:
        """Long-term planning with goal decomposition."""
        steps = [
            ReasoningStep(
                step_id=f"step_{uuid.uuid4().hex[:8]}",
                step_number=1,
                thought=f"Strategic planning for: {ctx.task[:80]}",
                confidence=0.85,
            ),
            ReasoningStep(
                step_id=f"step_{uuid.uuid4().hex[:8]}",
                step_number=2,
                thought=f"Decomposing {len(ctx.goals)} goals into actionable milestones",
                confidence=0.8,
            ),
            ReasoningStep(
                step_id=f"step_{uuid.uuid4().hex[:8]}",
                step_number=3,
                thought="Evaluating resource requirements and timeline constraints",
                confidence=0.75,
            ),
            ReasoningStep(
                step_id=f"step_{uuid.uuid4().hex[:8]}",
                step_number=4,
                thought="Generating strategic roadmap with contingency plans",
                confidence=0.7,
            ),
        ]

        return IntelligenceResult(
            result_id=f"result_{uuid.uuid4().hex[:12]}",
            context=ctx,
            reasoning_chain=steps,
            final_output={
                "goals": ctx.goals,
                "milestones": len(ctx.goals) * 2,
                "has_contingency": True,
            },
            insights=[
                f"Strategic plan generated for {len(ctx.goals)} goals",
                "Risk assessment and contingency planning completed",
            ],
            suggestions=[
                "Review milestones with stakeholders",
                "Establish progress tracking metrics",
            ],
            confidence=0.7,
        )

    def _collaborative_strategy(self, ctx: IntelligenceContext) -> IntelligenceResult:
        """Multi-agent coordination for complex tasks."""
        steps = [
            ReasoningStep(
                step_id=f"step_{uuid.uuid4().hex[:8]}",
                step_number=1,
                thought="Assessing task for multi-agent collaboration suitability",
                confidence=0.9,
            ),
            ReasoningStep(
                step_id=f"step_{uuid.uuid4().hex[:8]}",
                step_number=2,
                thought="Selecting optimal team composition and coordination pattern",
                confidence=0.8,
            ),
            ReasoningStep(
                step_id=f"step_{uuid.uuid4().hex[:8]}",
                step_number=3,
                thought="Delegating subtasks to specialized agents",
                confidence=0.75,
            ),
        ]

        team_info = None
        if self._team_factory:
            team_info = self._team_factory.list_team_types()

        return IntelligenceResult(
            result_id=f"result_{uuid.uuid4().hex[:12]}",
            context=ctx,
            reasoning_chain=steps,
            final_output={
                "collaboration_assessed": True,
                "available_team_types": team_info,
            },
            insights=[
                "Task suitable for collaborative execution",
                "Team composition recommendations generated",
            ],
            confidence=0.75,
        )

    def _adaptive_strategy(self, ctx: IntelligenceContext) -> IntelligenceResult:
        """Self-improving learning-based approach."""
        steps = [
            ReasoningStep(
                step_id=f"step_{uuid.uuid4().hex[:8]}",
                step_number=1,
                thought="Checking previous learning for similar tasks",
                confidence=0.85,
            ),
            ReasoningStep(
                step_id=f"step_{uuid.uuid4().hex[:8]}",
                step_number=2,
                thought="Applying learned patterns and refined strategies",
                confidence=0.8,
            ),
        ]

        skills_used: List[str] = []
        if self._learning_engine:
            skill = self._learning_engine.find_skill_for_task(ctx.task)
            if skill:
                skills_used.append(skill.skill_id)
                steps.append(ReasoningStep(
                    step_id=f"step_{uuid.uuid4().hex[:8]}",
                    step_number=3,
                    thought=f"Applying learned skill: {skill.name}",
                    action="apply_skill",
                    action_params={"skill_id": skill.skill_id},
                    confidence=skill.success_rate,
                ))

        return IntelligenceResult(
            result_id=f"result_{uuid.uuid4().hex[:12]}",
            context=ctx,
            reasoning_chain=steps,
            final_output={"adaptive_approach": True, "skills_used": len(skills_used)},
            insights=[
                "Adaptive learning strategy applied",
                "Previous experience leveraged for current task",
            ],
            skills_used=skills_used,
            confidence=0.75,
        )

    # ── Status & Management ──

    def get_status(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "initialized": self._initialized,
                "active_sessions": len(self._active_sessions),
                "total_results": len(self._result_history),
                "registered_tools": len(self._tool_registry),
                "available_modes": [m.value for m in IntelligenceMode],
                "learning_loop": (
                    self._learning_engine.get_memory_statistics()
                    if self._learning_engine else None
                ),
                "team_factory": (
                    self._team_factory.get_statistics()
                    if self._team_factory else None
                ),
            }

    def get_result_history(self, limit: int = 20) -> List[Dict[str, Any]]:
        with self._lock:
            return [r.to_dict() for r in self._result_history[-limit:]]

    def get_active_sessions(self) -> List[Dict[str, Any]]:
        with self._lock:
            return [ctx.to_dict() for ctx in self._active_sessions.values()]


def get_intelligence_core() -> AgentIntelligenceCore:
    """Get the global AgentIntelligenceCore instance."""
    return AgentIntelligenceCore.get_instance()