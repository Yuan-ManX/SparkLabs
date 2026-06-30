"""
SparkLabs Agent - Agent Explanation Engine

Interpretability system that produces human-readable explanations for
AI agent decisions in the SparkLabs AI-native game engine. The engine
records the reasoning chain behind each decision, generates explanations
at multiple levels of detail, reports confidence, runs counterfactual
what-if analysis, surfaces feature importance, and keeps a complete audit
trail of every explanation for review.

Architecture:
  ExplanationEngine (Singleton)
    |-- Decision Tracing (records the step-by-step reasoning chain)
    |-- Explanation Generation (turns traces into human-readable text)
    |-- Confidence Reporting (aggregates per-step confidence)
    |-- Counterfactual Analysis (what would have happened if...)
    |-- Feature Importance (which factors drove the decision)
    |-- Explanation Templates (pre-built templates per decision category)
    |-- Audit Trail (complete history of explanations)

Core Capabilities:
  - start_trace: Begin recording a decision trace
  - add_step: Append a reasoning step to a trace
  - complete_trace: Finalize a trace with outcome and alternatives
  - generate_explanation: Produce a human-readable explanation
  - add_feature_importance: Attach feature importance weights to a trace
  - add_counterfactual: Attach a what-if scenario to a trace
  - compute_confidence: Aggregate confidence across all steps
  - get_audit_trail: Return the full explanation history for an agent
  - register_template: Register a reusable explanation template
  - export_trace / import_trace: Serialize and restore traces

Usage:
    engine = get_explanation_engine()
    trace = engine.start_trace(
        agent_id="agent_1",
        category=DecisionCategory.MOVEMENT,
        summary="Move north toward resource node",
        context={"position": [10, 20]},
    )
    engine.add_step(
        trace_id=trace.id,
        step_type=TraceStepType.PERCEPTION,
        description="Detected resource node 5 tiles north",
        inputs={"scan_radius": 10},
        outputs={"node": [10, 25]},
        confidence=0.92,
    )
    engine.complete_trace(trace.id, outcome="moved_north", confidence=0.88)
    explanation = engine.generate_explanation(trace.id, level=ExplanationLevel.STANDARD)
"""

from __future__ import annotations

import threading
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class ExplanationLevel(Enum):
    """Level of detail for a generated explanation."""
    BRIEF = "brief"
    STANDARD = "standard"
    DETAILED = "detailed"
    FULL = "full"


class DecisionCategory(Enum):
    """Categories of agent decisions that can be traced and explained."""
    MOVEMENT = "movement"
    COMBAT = "combat"
    RESOURCE = "resource"
    SOCIAL = "social"
    STRATEGIC = "strategic"
    CREATIVE = "creative"
    NAVIGATION = "navigation"
    SURVIVAL = "survival"
    CUSTOM = "custom"


class TraceStepType(Enum):
    """Type of a single step within a decision reasoning chain."""
    PERCEPTION = "perception"
    INFERENCE = "inference"
    EVALUATION = "evaluation"
    SELECTION = "selection"
    EXECUTION = "execution"
    REFLECTION = "reflection"


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------


@dataclass
class FeatureImportance:
    """A single factor that influenced a decision with its relative weight."""
    feature_name: str = ""
    weight: float = 0.0
    description: str = ""
    value: Any = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "feature_name": self.feature_name,
            "weight": self.weight,
            "description": self.description,
            "value": self.value,
        }


@dataclass
class TraceStep:
    """A single step in a decision reasoning chain."""
    step_type: TraceStepType = TraceStepType.INFERENCE
    description: str = ""
    inputs: Dict[str, Any] = field(default_factory=dict)
    outputs: Dict[str, Any] = field(default_factory=dict)
    confidence: float = 0.5
    timestamp: float = field(default_factory=time.time)
    duration_ms: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "step_type": self.step_type.value,
            "description": self.description,
            "inputs": dict(self.inputs),
            "outputs": dict(self.outputs),
            "confidence": self.confidence,
            "timestamp": self.timestamp,
            "iso_time": time.strftime(
                "%Y-%m-%dT%H:%M:%S", time.localtime(self.timestamp)
            ),
            "duration_ms": self.duration_ms,
            "metadata": dict(self.metadata),
        }


@dataclass
class Counterfactual:
    """A what-if scenario describing an alternative condition and outcome."""
    condition: str = ""
    expected_outcome: str = ""
    probability: float = 0.5
    description: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "condition": self.condition,
            "expected_outcome": self.expected_outcome,
            "probability": self.probability,
            "description": self.description,
        }


@dataclass
class DecisionTrace:
    """Complete reasoning chain behind a single agent decision."""
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    agent_id: str = ""
    category: DecisionCategory = DecisionCategory.CUSTOM
    decision_summary: str = ""
    steps: List[TraceStep] = field(default_factory=list)
    outcome: str = ""
    confidence: float = 0.5
    alternatives: List[str] = field(default_factory=list)
    features: List[FeatureImportance] = field(default_factory=list)
    context: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)
    # Internal lifecycle flag, not serialized as a public field
    completed: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "agent_id": self.agent_id,
            "category": self.category.value,
            "decision_summary": self.decision_summary,
            "steps": [s.to_dict() for s in self.steps],
            "outcome": self.outcome,
            "confidence": self.confidence,
            "alternatives": list(self.alternatives),
            "features": [f.to_dict() for f in self.features],
            "context": dict(self.context),
            "timestamp": self.timestamp,
            "iso_time": time.strftime(
                "%Y-%m-%dT%H:%M:%S", time.localtime(self.timestamp)
            ),
            "metadata": dict(self.metadata),
            "completed": self.completed,
        }


@dataclass
class ExplanationTemplate:
    """A reusable text template for generating explanations of a category."""
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = ""
    category: DecisionCategory = DecisionCategory.CUSTOM
    template_text: str = ""
    placeholders: List[str] = field(default_factory=list)
    language: str = "en"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "category": self.category.value,
            "template_text": self.template_text,
            "placeholders": list(self.placeholders),
            "language": self.language,
        }

    def render(self, values: Dict[str, Any]) -> str:
        """Render the template text by substituting {placeholder} tokens."""
        text = self.template_text
        for key in self.placeholders:
            token = "{" + key + "}"
            replacement = values.get(key, "")
            text = text.replace(token, str(replacement))
        return text


@dataclass
class Explanation:
    """A generated human-readable explanation for a decision trace."""
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    trace_id: str = ""
    agent_id: str = ""
    level: ExplanationLevel = ExplanationLevel.STANDARD
    text: str = ""
    structured_data: Dict[str, Any] = field(default_factory=dict)
    features: List[FeatureImportance] = field(default_factory=list)
    confidence_score: float = 0.5
    counterfactuals: List[Counterfactual] = field(default_factory=list)
    generated_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "trace_id": self.trace_id,
            "agent_id": self.agent_id,
            "level": self.level.value,
            "text": self.text,
            "structured_data": dict(self.structured_data),
            "features": [f.to_dict() for f in self.features],
            "confidence_score": self.confidence_score,
            "counterfactuals": [c.to_dict() for c in self.counterfactuals],
            "generated_at": self.generated_at,
            "iso_time": time.strftime(
                "%Y-%m-%dT%H:%M:%S", time.localtime(self.generated_at)
            ),
        }


@dataclass
class ExplanationStats:
    """Aggregate statistics for the explanation engine."""
    total_traces: int = 0
    total_explanations: int = 0
    total_counterfactuals: int = 0
    avg_confidence: float = 0.0
    by_category: Dict[str, int] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_traces": self.total_traces,
            "total_explanations": self.total_explanations,
            "total_counterfactuals": self.total_counterfactuals,
            "avg_confidence": self.avg_confidence,
            "by_category": dict(self.by_category),
        }


@dataclass
class ExplanationSnapshot:
    """Point-in-time snapshot of the engine state."""
    traces: List[DecisionTrace] = field(default_factory=list)
    explanations: List[Explanation] = field(default_factory=list)
    templates: List[ExplanationTemplate] = field(default_factory=list)
    stats: ExplanationStats = field(default_factory=ExplanationStats)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "traces": [t.to_dict() for t in self.traces],
            "explanations": [e.to_dict() for e in self.explanations],
            "templates": [t.to_dict() for t in self.templates],
            "stats": self.stats.to_dict(),
        }


# ---------------------------------------------------------------------------
# Event kinds for handler registration
# ---------------------------------------------------------------------------


class ExplanationEventKind(Enum):
    """Kinds of events emitted by the explanation engine."""
    TRACE_STARTED = "trace_started"
    STEP_ADDED = "step_added"
    TRACE_COMPLETED = "trace_completed"
    EXPLANATION_GENERATED = "explanation_generated"
    TEMPLATE_REGISTERED = "template_registered"
    FEATURE_ADDED = "feature_added"
    COUNTERFACTUAL_ADDED = "counterfactual_added"


# ---------------------------------------------------------------------------
# ExplanationEngine Singleton
# ---------------------------------------------------------------------------


class ExplanationEngine:
    """Singleton engine that traces agent decisions and produces explanations.

    The engine records the reasoning chain behind each AI decision, computes
    confidence, attaches feature importance and counterfactual analysis, and
    generates human-readable explanations at four levels of detail. All public
    methods are thread-safe, guarded by a re-entrant lock.
    """

    _instance: Optional["ExplanationEngine"] = None
    _lock: threading.RLock = threading.RLock()

    _MAX_TRACES = 5000
    _MAX_EXPLANATIONS = 5000
    _MAX_EVENTS = 2000

    @classmethod
    def get_instance(cls) -> "ExplanationEngine":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def __init__(self) -> None:
        if hasattr(self, "_initialized"):
            return
        self._traces: Dict[str, DecisionTrace] = {}
        self._trace_order: List[str] = []
        self._explanations: Dict[str, Explanation] = {}
        self._explanation_order: List[str] = []
        self._templates: Dict[str, ExplanationTemplate] = {}
        self._event_handlers: Dict[str, List[tuple]] = {}
        self._events: List[Dict[str, Any]] = []
        self._stats: Dict[str, int] = {
            "traces_started": 0,
            "traces_completed": 0,
            "steps_added": 0,
            "explanations_generated": 0,
            "templates_registered": 0,
            "features_added": 0,
            "counterfactuals_added": 0,
        }
        self._initialized: bool = True
        self._seed_default_data()

    # ------------------------------------------------------------------
    # Seeding
    # ------------------------------------------------------------------

    def _seed_default_data(self) -> None:
        """Seed default templates and sample traces so the engine works
        immediately without configuration."""
        # Three explanation templates for common decision categories
        movement_template = ExplanationTemplate(
            name="Movement Decision Template",
            category=DecisionCategory.MOVEMENT,
            template_text=(
                "Agent {agent_id} moved {direction} to {reason}. "
                "Confidence: {confidence}."
            ),
            placeholders=["agent_id", "direction", "reason", "confidence"],
        )
        combat_template = ExplanationTemplate(
            name="Combat Decision Template",
            category=DecisionCategory.COMBAT,
            template_text=(
                "Agent {agent_id} chose to {action} against {target}. "
                "Expected damage: {damage}. Survival odds: {survival}."
            ),
            placeholders=["agent_id", "action", "target", "damage", "survival"],
        )
        resource_template = ExplanationTemplate(
            name="Resource Decision Template",
            category=DecisionCategory.RESOURCE,
            template_text=(
                "Agent {agent_id} harvested {resource} from {source}. "
                "Yield: {yield_amount}. Remaining capacity: {capacity}."
            ),
            placeholders=["agent_id", "resource", "source", "yield_amount", "capacity"],
        )
        for template in (movement_template, combat_template, resource_template):
            self._templates[template.id] = template

        # Sample trace 1: a movement decision
        trace1 = DecisionTrace(
            agent_id="agent_alpha",
            category=DecisionCategory.MOVEMENT,
            decision_summary="Move north to avoid enemy and reach resource",
            context={"position": [12, 8], "threat_level": "high"},
            completed=True,
        )
        trace1.steps = [
            TraceStep(
                step_type=TraceStepType.PERCEPTION,
                description="Detected hostile enemy 3 tiles to the south",
                inputs={"scan_radius": 6, "sensors": ["proximity", "threat"]},
                outputs={"enemy_pos": [12, 5], "enemy_type": "wolf"},
                confidence=0.95,
            ),
            TraceStep(
                step_type=TraceStepType.INFERENCE,
                description="Inferred that staying risks combat within 2 turns",
                inputs={"enemy_pos": [12, 5], "self_pos": [12, 8]},
                outputs={"risk_estimate": 0.82, "turns_to_contact": 2},
                confidence=0.78,
            ),
            TraceStep(
                step_type=TraceStepType.EVALUATION,
                description="Evaluated move options: north, east, west",
                inputs={"options": ["north", "east", "west", "south"]},
                outputs={"north_score": 0.91, "east_score": 0.55, "west_score": 0.40},
                confidence=0.86,
            ),
            TraceStep(
                step_type=TraceStepType.SELECTION,
                description="Selected north as it maximizes distance from enemy and reaches a resource node",
                inputs={"north_score": 0.91},
                outputs={"chosen": "north"},
                confidence=0.90,
            ),
            TraceStep(
                step_type=TraceStepType.EXECUTION,
                description="Executed move command to tile [12, 9]",
                inputs={"target_tile": [12, 9]},
                outputs={"new_position": [12, 9], "ap_cost": 1},
                confidence=0.99,
            ),
        ]
        trace1.features = [
            FeatureImportance(
                feature_name="enemy_proximity",
                weight=0.42,
                description="Distance to the nearest hostile entity",
                value=3,
            ),
            FeatureImportance(
                feature_name="resource_distance",
                weight=0.31,
                description="Distance to the nearest resource node",
                value=1,
            ),
            FeatureImportance(
                feature_name="terrain_cost",
                weight=0.18,
                description="Movement cost of the chosen terrain",
                value=1,
            ),
            FeatureImportance(
                feature_name="health_ratio",
                weight=0.09,
                description="Current health as a fraction of maximum",
                value=0.7,
            ),
        ]
        trace1_cf_1 = Counterfactual(
            condition="If the enemy were 6 tiles away instead of 3",
            expected_outcome="Agent would have moved east to a higher-yield resource node",
            probability=0.74,
            description="Greater distance reduces threat weight and shifts selection toward resource gain",
        )
        trace1_cf_2 = Counterfactual(
            condition="If agent health were full",
            expected_outcome="Agent might have engaged the enemy to clear the path",
            probability=0.41,
            description="Full health raises the expected value of direct combat",
        )
        # Store counterfactuals in metadata so they travel with the trace
        trace1.metadata["counterfactuals"] = [trace1_cf_1.to_dict(), trace1_cf_2.to_dict()]
        trace1.alternatives = ["move_east", "move_west", "engage_enemy"]
        trace1.outcome = "moved_north_to_safe_tile"
        trace1.confidence = ExplanationEngine._compute_confidence(trace1)
        self._traces[trace1.id] = trace1
        self._trace_order.append(trace1.id)

        # Sample trace 2: a combat decision
        trace2 = DecisionTrace(
            agent_id="agent_bravo",
            category=DecisionCategory.COMBAT,
            decision_summary="Attack the nearby goblin with a ranged ability",
            context={"position": [5, 5], "weapon": "short_bow", "mana": 12},
            completed=True,
        )
        trace2.steps = [
            TraceStep(
                step_type=TraceStepType.PERCEPTION,
                description="Spotted goblin at tile [6, 5] within bow range",
                inputs={"scan_radius": 8},
                outputs={"target_pos": [6, 5], "target_hp": 18},
                confidence=0.93,
            ),
            TraceStep(
                step_type=TraceStepType.EVALUATION,
                description="Compared ranged attack, melee charge, and retreat",
                inputs={"options": ["ranged", "melee", "retreat"]},
                outputs={"ranged_score": 0.88, "melee_score": 0.46, "retreat_score": 0.30},
                confidence=0.82,
            ),
            TraceStep(
                step_type=TraceStepType.SELECTION,
                description="Selected ranged attack to exploit range advantage",
                inputs={"ranged_score": 0.88},
                outputs={"chosen": "ranged_attack"},
                confidence=0.87,
            ),
            TraceStep(
                step_type=TraceStepType.EXECUTION,
                description="Fired short bow at goblin for 14 damage",
                inputs={"target": "goblin", "ability": "short_bow"},
                outputs={"damage": 14, "target_hp_after": 4},
                confidence=0.97,
            ),
            TraceStep(
                step_type=TraceStepType.REFLECTION,
                description="Noted that target survived and may counterattack next turn",
                inputs={"target_hp_after": 4},
                outputs={"follow_up": "prepare_dodge"},
                confidence=0.71,
            ),
        ]
        trace2.features = [
            FeatureImportance(
                feature_name="target_hp",
                weight=0.38,
                description="Current hit points of the target",
                value=18,
            ),
            FeatureImportance(
                feature_name="weapon_range",
                weight=0.34,
                description="Effective range of the equipped weapon",
                value=5,
            ),
            FeatureImportance(
                feature_name="agent_mana",
                weight=0.16,
                description="Mana available for abilities",
                value=12,
            ),
            FeatureImportance(
                feature_name="counterattack_risk",
                weight=0.12,
                description="Estimated chance of a counterattack",
                value=0.29,
            ),
        ]
        trace2_cf_1 = Counterfactual(
            condition="If the goblin had 6 HP instead of 18",
            expected_outcome="Agent would have used a stronger ability to guarantee a kill",
            probability=0.68,
            description="Lower target HP raises the value of burst damage to secure a kill",
        )
        trace2_cf_2 = Counterfactual(
            condition="If agent mana were below 6",
            expected_outcome="Agent would have switched to a melee charge to conserve mana",
            probability=0.55,
            description="Low mana reduces the feasibility of ranged abilities",
        )
        trace2.metadata["counterfactuals"] = [trace2_cf_1.to_dict(), trace2_cf_2.to_dict()]
        trace2.alternatives = ["melee_charge", "retreat", "use_ability"]
        trace2.outcome = "dealt_14_damage_target_survived"
        trace2.confidence = 0.86
        self._traces[trace2.id] = trace2
        self._trace_order.append(trace2.id)

        # Update seeded stats to reflect the seeded data
        self._stats["traces_completed"] = 2
        self._stats["steps_added"] = len(trace1.steps) + len(trace2.steps)
        self._stats["templates_registered"] = 3
        self._stats["features_added"] = len(trace1.features) + len(trace2.features)
        self._stats["counterfactuals_added"] = (
            len(trace1.metadata.get("counterfactuals", []))
            + len(trace2.metadata.get("counterfactuals", []))
        )

    # ------------------------------------------------------------------
    # Event dispatch
    # ------------------------------------------------------------------

    def _emit_event(self, kind: ExplanationEventKind, payload: Dict[str, Any]) -> None:
        """Record an event and invoke any registered handlers."""
        event = {
            "event_id": uuid.uuid4().hex,
            "kind": kind.value,
            "timestamp": time.time(),
            "payload": payload,
        }
        self._events.append(event)
        if len(self._events) > self._MAX_EVENTS:
            self._events = self._events[-self._MAX_EVENTS:]
        handlers = self._event_handlers.get(kind.value, [])
        for _handler_id, handler in handlers:
            try:
                handler(event)
            except Exception:
                # A faulty handler must not break engine operation
                pass

    # ------------------------------------------------------------------
    # Trace lifecycle
    # ------------------------------------------------------------------

    def start_trace(
        self,
        agent_id: str,
        category: DecisionCategory,
        summary: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> DecisionTrace:
        """Begin recording a decision trace.

        Args:
            agent_id: Identifier of the agent making the decision.
            category: Decision category for grouping and template selection.
            summary: Short human-readable summary of the decision.
            context: Optional context dictionary captured with the trace.

        Returns:
            The newly created DecisionTrace.
        """
        with self._lock:
            trace = DecisionTrace(
                agent_id=agent_id,
                category=category,
                decision_summary=summary,
                context=context or {},
            )
            self._traces[trace.id] = trace
            self._trace_order.append(trace.id)
            self._enforce_trace_capacity()
            self._stats["traces_started"] += 1
            self._emit_event(
                ExplanationEventKind.TRACE_STARTED,
                {"trace_id": trace.id, "agent_id": agent_id, "category": category.value},
            )
            return trace

    def add_step(
        self,
        trace_id: str,
        step_type: TraceStepType,
        description: str,
        inputs: Optional[Dict[str, Any]] = None,
        outputs: Optional[Dict[str, Any]] = None,
        confidence: float = 0.5,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Optional[TraceStep]:
        """Append a reasoning step to an existing trace.

        Returns the created step, or None if the trace was not found.
        """
        with self._lock:
            trace = self._traces.get(trace_id)
            if trace is None:
                return None
            start = time.time()
            step = TraceStep(
                step_type=step_type,
                description=description,
                inputs=inputs or {},
                outputs=outputs or {},
                confidence=max(0.0, min(1.0, confidence)),
                metadata=metadata or {},
            )
            step.duration_ms = (time.time() - start) * 1000.0
            trace.steps.append(step)
            self._stats["steps_added"] += 1
            self._emit_event(
                ExplanationEventKind.STEP_ADDED,
                {"trace_id": trace_id, "step_type": step_type.value},
            )
            return step

    def complete_trace(
        self,
        trace_id: str,
        outcome: str = "",
        alternatives: Optional[List[str]] = None,
        confidence: Optional[float] = None,
    ) -> Optional[DecisionTrace]:
        """Finalize a trace with its outcome and alternatives.

        If confidence is not provided it is computed from the recorded steps.
        Returns the completed trace, or None if not found.
        """
        with self._lock:
            trace = self._traces.get(trace_id)
            if trace is None:
                return None
            trace.outcome = outcome
            trace.alternatives = list(alternatives or [])
            trace.completed = True
            trace.confidence = (
                confidence if confidence is not None else self._compute_confidence(trace)
            )
            self._stats["traces_completed"] += 1
            self._emit_event(
                ExplanationEventKind.TRACE_COMPLETED,
                {"trace_id": trace_id, "outcome": outcome},
            )
            return trace

    # ------------------------------------------------------------------
    # Feature importance and counterfactuals
    # ------------------------------------------------------------------

    def add_feature_importance(
        self,
        trace_id: str,
        feature_name: str,
        weight: float,
        description: str = "",
        value: Any = None,
    ) -> Optional[FeatureImportance]:
        """Attach a feature importance entry to a trace."""
        with self._lock:
            trace = self._traces.get(trace_id)
            if trace is None:
                return None
            feature = FeatureImportance(
                feature_name=feature_name,
                weight=weight,
                description=description,
                value=value,
            )
            trace.features.append(feature)
            self._stats["features_added"] += 1
            self._emit_event(
                ExplanationEventKind.FEATURE_ADDED,
                {"trace_id": trace_id, "feature_name": feature_name},
            )
            return feature

    def add_counterfactual(
        self,
        trace_id: str,
        condition: str,
        expected_outcome: str,
        probability: float = 0.5,
        description: str = "",
    ) -> Optional[Counterfactual]:
        """Attach a counterfactual what-if scenario to a trace."""
        with self._lock:
            trace = self._traces.get(trace_id)
            if trace is None:
                return None
            cf = Counterfactual(
                condition=condition,
                expected_outcome=expected_outcome,
                probability=max(0.0, min(1.0, probability)),
                description=description,
            )
            # Store counterfactuals in metadata so they travel with the trace
            cf_list = trace.metadata.setdefault("counterfactuals", [])
            cf_list.append(cf.to_dict())
            self._stats["counterfactuals_added"] += 1
            self._emit_event(
                ExplanationEventKind.COUNTERFACTUAL_ADDED,
                {"trace_id": trace_id, "condition": condition},
            )
            return cf

    # ------------------------------------------------------------------
    # Confidence computation
    # ------------------------------------------------------------------

    @staticmethod
    def _compute_confidence(trace: DecisionTrace) -> float:
        """Aggregate confidence from all steps using a weighted average.

        Steps are weighted equally. If no steps exist, returns 0.5.
        """
        if not trace.steps:
            return 0.5
        total = sum(max(0.0, min(1.0, s.confidence)) for s in trace.steps)
        return total / len(trace.steps)

    def compute_confidence(self, trace_id: str) -> float:
        """Compute and store the aggregated confidence for a trace."""
        with self._lock:
            trace = self._traces.get(trace_id)
            if trace is None:
                return 0.0
            trace.confidence = self._compute_confidence(trace)
            return trace.confidence

    # ------------------------------------------------------------------
    # Explanation generation
    # ------------------------------------------------------------------

    def generate_explanation(
        self,
        trace_id: str,
        level: ExplanationLevel = ExplanationLevel.STANDARD,
        template_id: Optional[str] = None,
    ) -> Optional[Explanation]:
        """Generate a human-readable explanation for a trace.

        Args:
            trace_id: The trace to explain.
            level: Level of detail (BRIEF, STANDARD, DETAILED, FULL).
            template_id: Optional template to use for rendering. If not
                provided, a category-matched template is selected when
                available.

        Returns:
            The generated Explanation, or None if the trace was not found.
        """
        with self._lock:
            trace = self._traces.get(trace_id)
            if trace is None:
                return None

            template = None
            if template_id is not None:
                template = self._templates.get(template_id)
            if template is None:
                template = self._select_template_for_category(trace.category)

            text = self._render_explanation_text(trace, level, template)
            confidence_score = self._compute_confidence(trace)

            counterfactuals: List[Counterfactual] = []
            cf_data = trace.metadata.get("counterfactuals", [])
            for entry in cf_data:
                if isinstance(entry, dict):
                    counterfactuals.append(
                        Counterfactual(
                            condition=entry.get("condition", ""),
                            expected_outcome=entry.get("expected_outcome", ""),
                            probability=float(entry.get("probability", 0.5)),
                            description=entry.get("description", ""),
                        )
                    )

            structured_data = {
                "category": trace.category.value,
                "outcome": trace.outcome,
                "step_count": len(trace.steps),
                "alternative_count": len(trace.alternatives),
                "feature_count": len(trace.features),
                "context_keys": list(trace.context.keys()),
            }

            explanation = Explanation(
                trace_id=trace.id,
                agent_id=trace.agent_id,
                level=level,
                text=text,
                structured_data=structured_data,
                features=list(trace.features),
                confidence_score=confidence_score,
                counterfactuals=counterfactuals,
            )
            self._explanations[explanation.id] = explanation
            self._explanation_order.append(explanation.id)
            self._enforce_explanation_capacity()
            self._stats["explanations_generated"] += 1
            self._emit_event(
                ExplanationEventKind.EXPLANATION_GENERATED,
                {
                    "explanation_id": explanation.id,
                    "trace_id": trace_id,
                    "level": level.value,
                },
            )
            return explanation

    def _select_template_for_category(
        self, category: DecisionCategory
    ) -> Optional[ExplanationTemplate]:
        """Pick the first template whose category matches."""
        for template in self._templates.values():
            if template.category == category:
                return template
        return None

    def _render_explanation_text(
        self,
        trace: DecisionTrace,
        level: ExplanationLevel,
        template: Optional[ExplanationTemplate],
    ) -> str:
        """Build the explanation text according to the requested level."""
        if level == ExplanationLevel.BRIEF:
            return self._render_brief(trace)
        if level == ExplanationLevel.STANDARD:
            return self._render_standard(trace, template)
        if level == ExplanationLevel.DETAILED:
            return self._render_detailed(trace)
        return self._render_full(trace)

    def _render_brief(self, trace: DecisionTrace) -> str:
        """One-sentence summary of the decision."""
        summary = trace.decision_summary or trace.outcome or "made a decision"
        return f"Agent {trace.agent_id} {summary} (confidence: {trace.confidence:.2f})."

    def _render_standard(
        self, trace: DecisionTrace, template: Optional[ExplanationTemplate]
    ) -> str:
        """Summary plus two to three key factors."""
        template_text = ""
        if template is not None:
            values = self._build_template_values(trace)
            template_text = template.render(values)

        factors = self._top_features(trace, 3)
        if factors:
            factor_text = "; ".join(
                f"{f.feature_name} (weight {f.weight:.2f})" for f in factors
            )
        else:
            factor_text = "no feature importance recorded"

        confidence_text = f"Overall confidence: {trace.confidence:.2f}."

        parts: List[str] = []
        if template_text:
            parts.append(template_text)
        parts.append(f"Key factors: {factor_text}.")
        parts.append(confidence_text)
        return " ".join(parts)

    def _render_detailed(self, trace: DecisionTrace) -> str:
        """Full reasoning chain with a step-by-step breakdown."""
        lines: List[str] = []
        lines.append(
            f"Detailed reasoning for agent {trace.agent_id} "
            f"({trace.category.value}): {trace.decision_summary}"
        )
        lines.append(f"Outcome: {trace.outcome or 'pending'}")
        lines.append(f"Overall confidence: {trace.confidence:.2f}")
        lines.append("Reasoning chain:")
        for index, step in enumerate(trace.steps, start=1):
            lines.append(
                f"  {index}. [{step.step_type.value}] {step.description} "
                f"(confidence: {step.confidence:.2f})"
            )
        if trace.alternatives:
            lines.append(f"Alternatives considered: {', '.join(trace.alternatives)}")
        return "\n".join(lines)

    def _render_full(self, trace: DecisionTrace) -> str:
        """Everything in DETAILED plus counterfactuals, features, alternatives."""
        lines: List[str] = [self._render_detailed(trace)]
        if trace.features:
            lines.append("Feature importance:")
            for feature in sorted(trace.features, key=lambda f: f.weight, reverse=True):
                lines.append(
                    f"  - {feature.feature_name}: weight {feature.weight:.2f}, "
                    f"{feature.description}"
                )
        cf_data = trace.metadata.get("counterfactuals", [])
        if cf_data:
            lines.append("Counterfactual analysis:")
            for entry in cf_data:
                if isinstance(entry, dict):
                    lines.append(
                        f"  - {entry.get('condition', '')}: "
                        f"{entry.get('expected_outcome', '')} "
                        f"(probability {float(entry.get('probability', 0.5)):.2f})"
                    )
        return "\n".join(lines)

    def _build_template_values(self, trace: DecisionTrace) -> Dict[str, Any]:
        """Build placeholder values for template rendering from a trace."""
        values: Dict[str, Any] = {
            "agent_id": trace.agent_id,
            "confidence": f"{trace.confidence:.2f}",
        }
        # Populate from context for common placeholders
        for key, val in trace.context.items():
            if key not in values:
                values[key] = val
        # Populate from outcome and summary
        values.setdefault("direction", trace.context.get("direction", "north"))
        values.setdefault("reason", trace.decision_summary)
        values.setdefault("action", trace.outcome)
        values.setdefault("target", trace.context.get("target", "unknown"))
        values.setdefault("damage", trace.context.get("damage", 0))
        values.setdefault("survival", f"{trace.confidence:.2f}")
        values.setdefault("resource", trace.context.get("resource", "wood"))
        values.setdefault("source", trace.context.get("source", "node"))
        values.setdefault("yield_amount", trace.context.get("yield_amount", 0))
        values.setdefault("capacity", trace.context.get("capacity", 100))
        return values

    @staticmethod
    def _top_features(trace: DecisionTrace, count: int) -> List[FeatureImportance]:
        """Return the top-N features sorted by descending weight."""
        return sorted(
            trace.features, key=lambda f: f.weight, reverse=True
        )[:count]

    # ------------------------------------------------------------------
    # Templates
    # ------------------------------------------------------------------

    def register_template(
        self,
        name: str,
        category: DecisionCategory,
        template_text: str,
        placeholders: Optional[List[str]] = None,
    ) -> ExplanationTemplate:
        """Register a reusable explanation template."""
        with self._lock:
            template = ExplanationTemplate(
                name=name,
                category=category,
                template_text=template_text,
                placeholders=list(placeholders or []),
            )
            self._templates[template.id] = template
            self._stats["templates_registered"] += 1
            self._emit_event(
                ExplanationEventKind.TEMPLATE_REGISTERED,
                {"template_id": template.id, "name": name},
            )
            return template

    def get_template(self, template_id: str) -> Optional[ExplanationTemplate]:
        """Retrieve a registered template by id."""
        with self._lock:
            return self._templates.get(template_id)

    def list_templates(
        self, category: Optional[DecisionCategory] = None
    ) -> List[ExplanationTemplate]:
        """List templates, optionally filtered by category."""
        with self._lock:
            if category is None:
                return list(self._templates.values())
            return [
                t for t in self._templates.values() if t.category == category
            ]

    # ------------------------------------------------------------------
    # Trace queries
    # ------------------------------------------------------------------

    def get_trace(self, trace_id: str) -> Optional[DecisionTrace]:
        """Retrieve a trace by id."""
        with self._lock:
            return self._traces.get(trace_id)

    def list_traces(
        self,
        agent_id: Optional[str] = None,
        category: Optional[DecisionCategory] = None,
        limit: int = 50,
    ) -> List[DecisionTrace]:
        """List traces, optionally filtered by agent and/or category."""
        with self._lock:
            results: List[DecisionTrace] = []
            for trace_id in reversed(self._trace_order):
                trace = self._traces.get(trace_id)
                if trace is None:
                    continue
                if agent_id is not None and trace.agent_id != agent_id:
                    continue
                if category is not None and trace.category != category:
                    continue
                results.append(trace)
                if len(results) >= limit:
                    break
            return list(reversed(results))

    # ------------------------------------------------------------------
    # Explanation queries
    # ------------------------------------------------------------------

    def get_explanation(self, explanation_id: str) -> Optional[Explanation]:
        """Retrieve a generated explanation by id."""
        with self._lock:
            return self._explanations.get(explanation_id)

    def list_explanations(
        self,
        agent_id: Optional[str] = None,
        limit: int = 50,
    ) -> List[Explanation]:
        """List explanations, optionally filtered by agent."""
        with self._lock:
            results: List[Explanation] = []
            for explanation_id in reversed(self._explanation_order):
                explanation = self._explanations.get(explanation_id)
                if explanation is None:
                    continue
                if agent_id is not None and explanation.agent_id != agent_id:
                    continue
                results.append(explanation)
                if len(results) >= limit:
                    break
            return list(reversed(results))

    # ------------------------------------------------------------------
    # Audit trail
    # ------------------------------------------------------------------

    def get_audit_trail(
        self, agent_id: Optional[str] = None, limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Return the full explanation history for review.

        Each entry pairs a trace with its most recent explanation so a
        reviewer can see both the decision and how it was explained.
        """
        with self._lock:
            trail: List[Dict[str, Any]] = []
            traces = self.list_traces(agent_id=agent_id, limit=limit)
            for trace in traces:
                explanation = self._latest_explanation_for_trace(trace.id)
                entry = {
                    "trace": trace.to_dict(),
                    "explanation": explanation.to_dict() if explanation else None,
                }
                trail.append(entry)
            return trail

    def _latest_explanation_for_trace(
        self, trace_id: str
    ) -> Optional[Explanation]:
        """Return the most recently generated explanation for a trace."""
        latest: Optional[Explanation] = None
        for explanation in self._explanations.values():
            if explanation.trace_id == trace_id:
                if latest is None or explanation.generated_at > latest.generated_at:
                    latest = explanation
        return latest

    # ------------------------------------------------------------------
    # Event handlers and event listing
    # ------------------------------------------------------------------

    def register_event_handler(
        self,
        event_kind: ExplanationEventKind,
        handler: Callable[[Dict[str, Any]], None],
    ) -> str:
        """Register a handler for a specific event kind.

        Returns a handler id that can be used for future de-registration.
        """
        with self._lock:
            handler_id = uuid.uuid4().hex
            key = event_kind.value
            if key not in self._event_handlers:
                self._event_handlers[key] = []
            self._event_handlers[key].append((handler_id, handler))
            return handler_id

    def list_events(
        self,
        event_kind: Optional[ExplanationEventKind] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """Return recent events, optionally filtered by kind."""
        with self._lock:
            events = list(self._events)
            if event_kind is not None:
                events = [e for e in events if e["kind"] == event_kind.value]
            return events[-limit:]

    # ------------------------------------------------------------------
    # Export / import
    # ------------------------------------------------------------------

    def export_trace(self, trace_id: str) -> Optional[Dict[str, Any]]:
        """Export a trace as a JSON-serializable dictionary."""
        with self._lock:
            trace = self._traces.get(trace_id)
            if trace is None:
                return None
            return {
                "version": 1,
                "exported_at": time.time(),
                "trace": trace.to_dict(),
            }

    def import_trace(self, data: Dict[str, Any]) -> Optional[DecisionTrace]:
        """Import a previously exported trace dictionary."""
        with self._lock:
            trace_data = data.get("trace", data)
            if not isinstance(trace_data, dict):
                return None
            try:
                category = DecisionCategory(
                    trace_data.get("category", DecisionCategory.CUSTOM.value)
                )
            except ValueError:
                category = DecisionCategory.CUSTOM

            trace = DecisionTrace(
                id=trace_data.get("id", uuid.uuid4().hex),
                agent_id=trace_data.get("agent_id", ""),
                category=category,
                decision_summary=trace_data.get("decision_summary", ""),
                outcome=trace_data.get("outcome", ""),
                confidence=float(trace_data.get("confidence", 0.5)),
                alternatives=list(trace_data.get("alternatives", [])),
                context=dict(trace_data.get("context", {})),
                metadata=dict(trace_data.get("metadata", {})),
                completed=bool(trace_data.get("completed", False)),
            )

            for step_data in trace_data.get("steps", []):
                try:
                    step_type = TraceStepType(
                        step_data.get("step_type", TraceStepType.INFERENCE.value)
                    )
                except ValueError:
                    step_type = TraceStepType.INFERENCE
                step = TraceStep(
                    step_type=step_type,
                    description=step_data.get("description", ""),
                    inputs=dict(step_data.get("inputs", {})),
                    outputs=dict(step_data.get("outputs", {})),
                    confidence=float(step_data.get("confidence", 0.5)),
                    duration_ms=float(step_data.get("duration_ms", 0.0)),
                    metadata=dict(step_data.get("metadata", {})),
                )
                trace.steps.append(step)

            for feature_data in trace_data.get("features", []):
                trace.features.append(
                    FeatureImportance(
                        feature_name=feature_data.get("feature_name", ""),
                        weight=float(feature_data.get("weight", 0.0)),
                        description=feature_data.get("description", ""),
                        value=feature_data.get("value"),
                    )
                )

            self._traces[trace.id] = trace
            if trace.id not in self._trace_order:
                self._trace_order.append(trace.id)
                self._enforce_trace_capacity()
            return trace

    # ------------------------------------------------------------------
    # Status, snapshot, and lifecycle
    # ------------------------------------------------------------------

    def get_stats(self) -> ExplanationStats:
        """Compute aggregate statistics from current state."""
        with self._lock:
            total_traces = len(self._traces)
            total_explanations = len(self._explanations)
            total_counterfactuals = sum(
                len(t.metadata.get("counterfactuals", []))
                for t in self._traces.values()
            )
            confidence_values = [
                t.confidence for t in self._traces.values() if t.steps
            ]
            avg_confidence = (
                sum(confidence_values) / len(confidence_values)
                if confidence_values
                else 0.0
            )
            by_category: Dict[str, int] = {}
            for trace in self._traces.values():
                key = trace.category.value
                by_category[key] = by_category.get(key, 0) + 1
            return ExplanationStats(
                total_traces=total_traces,
                total_explanations=total_explanations,
                total_counterfactuals=total_counterfactuals,
                avg_confidence=avg_confidence,
                by_category=by_category,
            )

    def get_status(self) -> Dict[str, Any]:
        """Return the current operational status of the engine."""
        with self._lock:
            stats = self.get_stats()
            return {
                "engine_id": id(self),
                "initialized": self._initialized,
                "total_traces": len(self._traces),
                "total_explanations": len(self._explanations),
                "total_templates": len(self._templates),
                "total_events": len(self._events),
                "stats": dict(self._stats),
                "aggregate": stats.to_dict(),
            }

    def get_snapshot(self) -> ExplanationSnapshot:
        """Capture a point-in-time snapshot of the engine state."""
        with self._lock:
            return ExplanationSnapshot(
                traces=list(self._traces.values()),
                explanations=list(self._explanations.values()),
                templates=list(self._templates.values()),
                stats=self.get_stats(),
            )

    def reset(self) -> None:
        """Reset the engine to its initial seeded state."""
        with self._lock:
            self._traces.clear()
            self._trace_order.clear()
            self._explanations.clear()
            self._explanation_order.clear()
            self._templates.clear()
            self._event_handlers.clear()
            self._events.clear()
            self._stats = {
                "traces_started": 0,
                "traces_completed": 0,
                "steps_added": 0,
                "explanations_generated": 0,
                "templates_registered": 0,
                "features_added": 0,
                "counterfactuals_added": 0,
            }
            self._seed_default_data()

    # ------------------------------------------------------------------
    # Capacity management
    # ------------------------------------------------------------------

    def _enforce_trace_capacity(self) -> None:
        """Evict the oldest traces when the capacity is exceeded."""
        while len(self._trace_order) > self._MAX_TRACES:
            oldest_id = self._trace_order.pop(0)
            self._traces.pop(oldest_id, None)

    def _enforce_explanation_capacity(self) -> None:
        """Evict the oldest explanations when the capacity is exceeded."""
        while len(self._explanation_order) > self._MAX_EXPLANATIONS:
            oldest_id = self._explanation_order.pop(0)
            self._explanations.pop(oldest_id, None)


# ---------------------------------------------------------------------------
# Module-level factory
# ---------------------------------------------------------------------------


def get_explanation_engine() -> ExplanationEngine:
    """Get or create the global ExplanationEngine singleton."""
    return ExplanationEngine.get_instance()
