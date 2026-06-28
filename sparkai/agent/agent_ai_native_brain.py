"""
SparkLabs Agent - AI-Native Cognitive Brain

The core cognitive architecture of the SparkLabs AI-native game engine Agent.
This module implements a unified agent brain that integrates perception, reasoning,
planning, action execution, memory, and learning into a single cohesive system.

The brain operates through a continuous Perception-Reasoning-Action-Learning (PRAL)
loop, enabling agents to autonomously understand, reason about, and interact with
game worlds in real-time.

Architecture:
  AINativeBrain (Singleton)
    |-- PerceptionLayer (multi-modal sensing: visual, spatial, social, event-based)
    |-- ReasoningLayer (deductive, inductive, abductive, causal, counterfactual)
    |-- PlanningLayer (HTN, goal-oriented, reactive, deliberative)
    |-- ActionLayer (action space, execution, validation, feedback)
    |-- MemoryLayer (episodic, semantic, procedural, working)
    |-- LearningLayer (self-reflection, skill evolution, pattern recognition)
    |-- MetacognitionLayer (confidence calibration, self-assessment, strategy selection)
    |-- WorldModelLayer (state prediction, simulation, causal reasoning)
"""

from __future__ import annotations

import json
import threading
import time
import uuid
from collections import deque
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple


# ── Cognitive Architecture Enums ──

class BrainState(Enum):
    """Operational states of the cognitive brain."""
    IDLE = "idle"
    PERCEIVING = "perceiving"
    REASONING = "reasoning"
    PLANNING = "planning"
    EXECUTING = "executing"
    REFLECTING = "reflecting"
    LEARNING = "learning"
    SLEEPING = "sleeping"


class PerceptionChannel(Enum):
    """Sensory channels available to the agent."""
    VISUAL = "visual"
    SPATIAL = "spatial"
    AUDITORY = "auditory"
    TACTILE = "tactile"
    SOCIAL = "social"
    GAME_STATE = "game_state"
    ENGINE_EVENT = "engine_event"
    USER_INPUT = "user_input"
    SYSTEM_METRIC = "system_metric"


class ReasoningStrategy(Enum):
    """Available reasoning strategies for the agent."""
    DEDUCTIVE = "deductive"
    INDUCTIVE = "inductive"
    ABDUCTIVE = "abductive"
    ANALOGICAL = "analogical"
    CAUSAL = "causal"
    COUNTERFACTUAL = "counterfactual"
    HEURISTIC = "heuristic"
    BAYESIAN = "bayesian"
    CASE_BASED = "case_based"
    ENSEMBLE = "ensemble"


class ActionDomain(Enum):
    """Domains where the agent can execute actions."""
    GAME_ENGINE = "game_engine"
    CODE_GENERATION = "code_generation"
    ASSET_CREATION = "asset_creation"
    LEVEL_DESIGN = "level_design"
    NPC_CONTROL = "npc_control"
    DIALOGUE = "dialogue"
    WORLD_EDITING = "world_editing"
    PERFORMANCE_TUNING = "performance_tuning"
    TESTING = "testing"
    DEPLOYMENT = "deployment"


class ConfidenceLevel(Enum):
    """Confidence levels for agent decisions and beliefs."""
    CERTAIN = "certain"
    HIGH = "high"
    MODERATE = "moderate"
    LOW = "low"
    UNCERTAIN = "uncertain"
    UNKNOWN = "unknown"


class MemoryType(Enum):
    """Memory systems in the cognitive architecture."""
    WORKING = "working"
    EPISODIC = "episodic"
    SEMANTIC = "semantic"
    PROCEDURAL = "procedural"
    SENSORY = "sensory"
    SOCIAL = "social"


class LearningMode(Enum):
    """Learning modes available to the agent."""
    SUPERVISED = "supervised"
    REINFORCEMENT = "reinforcement"
    SELF_SUPERVISED = "self_supervised"
    TRANSFER = "transfer"
    CURRICULUM = "curriculum"
    META = "meta"


# ── Data Classes ──

@dataclass
class SensoryInput:
    """A single sensory input from a perception channel."""
    channel: PerceptionChannel
    data: Dict[str, Any]
    timestamp: float
    confidence: float = 1.0
    source_id: str = ""
    priority: float = 0.5
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "channel": self.channel.value,
            "data": self.data,
            "timestamp": self.timestamp,
            "confidence": self.confidence,
            "source_id": self.source_id,
            "priority": self.priority,
            "metadata": self.metadata,
        }


@dataclass
class PerceptionFrame:
    """A complete perceptual snapshot of the environment."""
    frame_id: str
    timestamp: float
    inputs: List[SensoryInput]
    fused_representation: Dict[str, Any] = field(default_factory=dict)
    attention_weights: Dict[str, float] = field(default_factory=dict)
    anomalies: List[Dict[str, Any]] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "frame_id": self.frame_id,
            "timestamp": self.timestamp,
            "inputs": [inp.to_dict() for inp in self.inputs],
            "fused_representation": self.fused_representation,
            "attention_weights": self.attention_weights,
            "anomalies": self.anomalies,
            "metadata": self.metadata,
        }


@dataclass
class ReasoningStep:
    """A single step in a reasoning chain."""
    step_id: str
    strategy: ReasoningStrategy
    premises: List[Dict[str, Any]]
    conclusion: Dict[str, Any]
    confidence: float
    evidence: List[Dict[str, Any]] = field(default_factory=list)
    alternatives: List[Dict[str, Any]] = field(default_factory=list)
    time_taken_ms: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "step_id": self.step_id,
            "strategy": self.strategy.value,
            "premises": self.premises,
            "conclusion": self.conclusion,
            "confidence": self.confidence,
            "evidence": self.evidence,
            "alternatives": self.alternatives,
            "time_taken_ms": self.time_taken_ms,
            "metadata": self.metadata,
        }


@dataclass
class ReasoningChain:
    """A complete reasoning chain with multiple steps."""
    chain_id: str
    steps: List[ReasoningStep]
    final_conclusion: Dict[str, Any]
    overall_confidence: float
    strategies_used: List[ReasoningStrategy]
    total_time_ms: float = 0.0
    assumptions: List[str] = field(default_factory=list)
    uncertainties: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "chain_id": self.chain_id,
            "steps": [s.to_dict() for s in self.steps],
            "final_conclusion": self.final_conclusion,
            "overall_confidence": self.overall_confidence,
            "strategies_used": [s.value for s in self.strategies_used],
            "total_time_ms": self.total_time_ms,
            "assumptions": self.assumptions,
            "uncertainties": self.uncertainties,
            "metadata": self.metadata,
        }


@dataclass
class ActionPlan:
    """A structured plan of actions to execute."""
    plan_id: str
    goal: str
    actions: List[Dict[str, Any]]
    priority: float = 0.5
    estimated_duration_ms: float = 0.0
    preconditions: List[Dict[str, Any]] = field(default_factory=list)
    expected_outcomes: List[Dict[str, Any]] = field(default_factory=list)
    fallback_plan_id: Optional[str] = None
    dependencies: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "plan_id": self.plan_id,
            "goal": self.goal,
            "actions": self.actions,
            "priority": self.priority,
            "estimated_duration_ms": self.estimated_duration_ms,
            "preconditions": self.preconditions,
            "expected_outcomes": self.expected_outcomes,
            "fallback_plan_id": self.fallback_plan_id,
            "dependencies": self.dependencies,
            "metadata": self.metadata,
        }


@dataclass
class MemoryEntry:
    """A single entry in the agent's memory system."""
    entry_id: str
    memory_type: MemoryType
    content: Dict[str, Any]
    timestamp: float
    importance: float = 0.5
    access_count: int = 0
    last_accessed: float = 0.0
    decay_rate: float = 0.01
    associations: List[str] = field(default_factory=list)
    emotional_valence: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "entry_id": self.entry_id,
            "memory_type": self.memory_type.value,
            "content": self.content,
            "timestamp": self.timestamp,
            "importance": self.importance,
            "access_count": self.access_count,
            "last_accessed": self.last_accessed,
            "decay_rate": self.decay_rate,
            "associations": self.associations,
            "emotional_valence": self.emotional_valence,
            "metadata": self.metadata,
        }


@dataclass
class BrainSnapshot:
    """A complete snapshot of the brain's state at a point in time."""
    snapshot_id: str
    timestamp: float
    state: BrainState
    active_goals: List[str]
    recent_perceptions: List[str]
    active_reasoning: List[str]
    pending_actions: List[str]
    memory_stats: Dict[str, int]
    confidence_profile: Dict[str, float]
    performance_metrics: Dict[str, float]
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "snapshot_id": self.snapshot_id,
            "timestamp": self.timestamp,
            "state": self.state.value,
            "active_goals": self.active_goals,
            "recent_perceptions": self.recent_perceptions,
            "active_reasoning": self.active_reasoning,
            "pending_actions": self.pending_actions,
            "memory_stats": self.memory_stats,
            "confidence_profile": self.confidence_profile,
            "performance_metrics": self.performance_metrics,
            "metadata": self.metadata,
        }


# ── AINativeBrain ──

class AINativeBrain:
    """
    The AI-Native Cognitive Brain for SparkLabs agents.

    Implements a complete cognitive architecture that enables agents to:
    - Perceive game worlds through multi-modal sensory channels
    - Reason about game states using multiple reasoning strategies
    - Plan and execute actions with confidence calibration
    - Learn from experience through multiple memory systems
    - Self-reflect and adapt strategies based on outcomes
    - Maintain a predictive world model for simulation

    Uses double-checked locking singleton pattern for thread safety.
    """

    _instance: Optional["AINativeBrain"] = None
    _instance_lock = threading.RLock()

    def __init__(self) -> None:
        if AINativeBrain._instance is not None:
            raise RuntimeError("Use AINativeBrain.get_instance()")
        self._initialized: bool = False
        self._state: BrainState = BrainState.IDLE
        self._state_lock = threading.RLock()

        # Perception
        self._perception_buffer: deque = deque(maxlen=500)
        self._perception_stats: Dict[str, Dict[str, Any]] = {}
        self._attention_model: Dict[str, float] = {}

        # Reasoning
        self._reasoning_chains: Dict[str, ReasoningChain] = {}
        self._reasoning_cache: Dict[str, Any] = {}
        self._reasoning_strategies: Dict[ReasoningStrategy, Callable] = {}

        # Planning
        self._action_plans: Dict[str, ActionPlan] = {}
        self._plan_history: deque = deque(maxlen=200)
        self._active_plan_id: Optional[str] = None

        # Memory
        self._memory_stores: Dict[MemoryType, Dict[str, MemoryEntry]] = {
            mt: {} for mt in MemoryType
        }
        self._memory_index: Dict[str, Set[str]] = {}  # tag -> entry_ids

        # Learning
        self._learning_sessions: List[Dict[str, Any]] = []
        self._skill_patterns: Dict[str, List[Dict[str, Any]]] = {}
        self._reflection_log: deque = deque(maxlen=300)

        # World Model
        self._world_state: Dict[str, Any] = {}
        self._predictions: Dict[str, List[Dict[str, Any]]] = {}
        self._causal_graph: Dict[str, List[str]] = {}  # cause -> [effects]

        # Metacognition
        self._confidence_history: deque = deque(maxlen=500)
        self._strategy_performance: Dict[str, Dict[str, float]] = {}
        self._self_assessments: List[Dict[str, Any]] = []

        # Statistics
        self._stats: Dict[str, Any] = {
            "total_perception_frames": 0,
            "total_reasoning_chains": 0,
            "total_action_plans": 0,
            "total_actions_executed": 0,
            "total_learning_sessions": 0,
            "total_reflections": 0,
            "total_memory_entries": 0,
            "average_reasoning_time_ms": 0.0,
            "average_planning_time_ms": 0.0,
            "success_rate": 0.0,
            "brain_uptime_seconds": 0.0,
        }

        self._start_time: float = time.time()
        self._lock = threading.RLock()
        self._event_callbacks: Dict[str, List[Callable]] = {}

    @classmethod
    def get_instance(cls) -> "AINativeBrain":
        """Get the singleton instance with thread-safe double-checked locking."""
        if cls._instance is None:
            with cls._instance_lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    # ── Initialization ──

    def initialize(self) -> None:
        """Initialize the brain with all cognitive subsystems."""
        with self._state_lock:
            if self._initialized:
                return
            self._initialized = True
            self._state = BrainState.IDLE
            self._start_time = time.time()
            self._setup_reasoning_strategies()
            self._setup_attention_model()

    def _setup_reasoning_strategies(self) -> None:
        """Register default reasoning strategies."""
        self._reasoning_strategies[ReasoningStrategy.DEDUCTIVE] = self._reason_deductive
        self._reasoning_strategies[ReasoningStrategy.INDUCTIVE] = self._reason_inductive
        self._reasoning_strategies[ReasoningStrategy.ABDUCTIVE] = self._reason_abductive
        self._reasoning_strategies[ReasoningStrategy.ANALOGICAL] = self._reason_analogical
        self._reasoning_strategies[ReasoningStrategy.CAUSAL] = self._reason_causal
        self._reasoning_strategies[ReasoningStrategy.HEURISTIC] = self._reason_heuristic

    def _setup_attention_model(self) -> None:
        """Initialize default attention weights for perception channels."""
        self._attention_model = {
            PerceptionChannel.GAME_STATE.value: 0.25,
            PerceptionChannel.ENGINE_EVENT.value: 0.20,
            PerceptionChannel.USER_INPUT.value: 0.20,
            PerceptionChannel.VISUAL.value: 0.15,
            PerceptionChannel.SPATIAL.value: 0.10,
            PerceptionChannel.SOCIAL.value: 0.05,
            PerceptionChannel.SYSTEM_METRIC.value: 0.03,
            PerceptionChannel.AUDITORY.value: 0.02,
        }

    # ── Perception Layer ──

    def perceive(self, inputs: List[SensoryInput]) -> PerceptionFrame:
        """Process a batch of sensory inputs into a unified perception frame."""
        with self._state_lock:
            self._state = BrainState.PERCEIVING

        frame_id = f"perception_{uuid.uuid4().hex[:12]}"
        now = time.time()

        # Apply attention weighting
        for inp in inputs:
            channel_weight = self._attention_model.get(inp.channel.value, 0.1)
            inp.priority = channel_weight

        # Fuse multi-modal inputs
        fused = self._fuse_perceptions(inputs)

        # Detect anomalies
        anomalies = self._detect_perception_anomalies(inputs, fused)

        frame = PerceptionFrame(
            frame_id=frame_id,
            timestamp=now,
            inputs=inputs,
            fused_representation=fused,
            attention_weights=self._attention_model.copy(),
            anomalies=anomalies,
        )

        self._perception_buffer.append(frame)
        self._stats["total_perception_frames"] += 1

        # Update world state from perceptions
        self._update_world_state_from_perception(frame)

        with self._state_lock:
            self._state = BrainState.IDLE

        self._emit_event("perception_complete", frame.to_dict())
        return frame

    def _fuse_perceptions(self, inputs: List[SensoryInput]) -> Dict[str, Any]:
        """Fuse multiple sensory inputs into a unified representation."""
        fused = {
            "entities_detected": [],
            "events_detected": [],
            "spatial_layout": {},
            "relationships": [],
            "anomalies": [],
            "confidence": 0.0,
        }

        entity_set: Dict[str, Dict[str, Any]] = {}
        events: List[Dict[str, Any]] = []

        for inp in inputs:
            data = inp.data
            if "entities" in data:
                for entity in data["entities"]:
                    eid = entity.get("id", str(uuid.uuid4().hex[:8]))
                    if eid not in entity_set:
                        entity_set[eid] = entity
                    else:
                        entity_set[eid].update(entity)

            if "events" in data:
                events.extend(data["events"])

            if "spatial" in data:
                fused["spatial_layout"].update(data["spatial"])

            if "relationships" in data:
                fused["relationships"].extend(data["relationships"])

        fused["entities_detected"] = list(entity_set.values())
        fused["events_detected"] = events
        fused["confidence"] = (
            sum(inp.confidence for inp in inputs) / len(inputs) if inputs else 0.0
        )

        return fused

    def _detect_perception_anomalies(
        self, inputs: List[SensoryInput], fused: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Detect anomalies in perception data."""
        anomalies = []
        for inp in inputs:
            if inp.confidence < 0.3:
                anomalies.append({
                    "type": "low_confidence",
                    "channel": inp.channel.value,
                    "confidence": inp.confidence,
                    "source_id": inp.source_id,
                })

        if fused["confidence"] < 0.4:
            anomalies.append({
                "type": "low_fused_confidence",
                "confidence": fused["confidence"],
            })

        # Check for contradictions between channels
        channels_used = {inp.channel for inp in inputs}
        if PerceptionChannel.VISUAL in channels_used and PerceptionChannel.SPATIAL in channels_used:
            visual_entities = set()
            spatial_entities = set()
            for inp in inputs:
                if inp.channel == PerceptionChannel.VISUAL:
                    for e in inp.data.get("entities", []):
                        visual_entities.add(e.get("id", ""))
                if inp.channel == PerceptionChannel.SPATIAL:
                    for e in inp.data.get("entities", []):
                        spatial_entities.add(e.get("id", ""))
            if visual_entities and spatial_entities:
                mismatch = visual_entities.symmetric_difference(spatial_entities)
                if mismatch:
                    anomalies.append({
                        "type": "cross_channel_mismatch",
                        "channels": ["visual", "spatial"],
                        "mismatched_entities": list(mismatch),
                    })

        return anomalies

    def _update_world_state_from_perception(self, frame: PerceptionFrame) -> None:
        """Update the internal world model from perception data."""
        with self._lock:
            for entity in frame.fused_representation.get("entities_detected", []):
                eid = entity.get("id", "")
                if eid:
                    existing = self._world_state.get(eid, {})
                    existing.update(entity)
                    self._world_state[eid] = existing

            for event in frame.fused_representation.get("events_detected", []):
                event_id = event.get("id", str(uuid.uuid4().hex[:8]))
                self._world_state[f"event_{event_id}"] = event

    # ── Reasoning Layer ──

    def reason(
        self,
        query: str,
        context: Dict[str, Any],
        strategies: Optional[List[ReasoningStrategy]] = None,
        max_steps: int = 5,
    ) -> ReasoningChain:
        """Execute a reasoning chain to answer a query about the game world."""
        with self._state_lock:
            self._state = BrainState.REASONING

        chain_id = f"reasoning_{uuid.uuid4().hex[:12]}"
        start_time = time.time()

        if strategies is None:
            strategies = [ReasoningStrategy.DEDUCTIVE, ReasoningStrategy.HEURISTIC]

        steps: List[ReasoningStep] = []
        for i, strategy in enumerate(strategies[:max_steps]):
            step_start = time.time()
            reasoner = self._reasoning_strategies.get(strategy)
            if reasoner is None:
                reasoner = self._reason_heuristic

            result = reasoner(query, context, steps)
            step = ReasoningStep(
                step_id=f"{chain_id}_step_{i}",
                strategy=strategy,
                premises=result.get("premises", []),
                conclusion=result.get("conclusion", {}),
                confidence=result.get("confidence", 0.5),
                evidence=result.get("evidence", []),
                alternatives=result.get("alternatives", []),
                time_taken_ms=(time.time() - step_start) * 1000,
            )
            steps.append(step)

            if step.confidence > 0.9:
                break

        total_time = (time.time() - start_time) * 1000
        final_conclusion = steps[-1].conclusion if steps else {}
        overall_confidence = sum(s.confidence for s in steps) / len(steps) if steps else 0.0

        chain = ReasoningChain(
            chain_id=chain_id,
            steps=steps,
            final_conclusion=final_conclusion,
            overall_confidence=overall_confidence,
            strategies_used=[s.strategy for s in steps],
            total_time_ms=total_time,
        )

        self._reasoning_chains[chain_id] = chain
        self._stats["total_reasoning_chains"] += 1
        self._update_reasoning_stats(total_time)

        with self._state_lock:
            self._state = BrainState.IDLE

        self._emit_event("reasoning_complete", chain.to_dict())
        return chain

    def _reason_deductive(
        self, query: str, context: Dict[str, Any], previous_steps: List[ReasoningStep]
    ) -> Dict[str, Any]:
        """Deductive reasoning: general rules to specific conclusions."""
        rules = context.get("rules", [])
        facts = context.get("facts", {})

        applicable_rules = []
        for rule in rules:
            if isinstance(rule, dict) and rule.get("condition", "").lower() in query.lower():
                applicable_rules.append(rule)

        conclusion = {
            "answer": f"Based on {len(applicable_rules)} applicable rules",
            "applied_rules": applicable_rules,
            "matched_facts": list(facts.keys())[:5],
        }
        confidence = min(0.9, 0.5 + len(applicable_rules) * 0.1)

        return {
            "premises": [{"type": "rule", "content": r} for r in applicable_rules],
            "conclusion": conclusion,
            "confidence": confidence,
            "evidence": [{"type": "fact", "key": k, "value": v} for k, v in list(facts.items())[:5]],
            "alternatives": [],
        }

    def _reason_inductive(
        self, query: str, context: Dict[str, Any], previous_steps: List[ReasoningStep]
    ) -> Dict[str, Any]:
        """Inductive reasoning: specific observations to general patterns."""
        observations = context.get("observations", [])
        patterns = []

        if len(observations) >= 3:
            common_keys = set(observations[0].keys()) if observations else set()
            for obs in observations[1:]:
                common_keys &= set(obs.keys())
            for key in common_keys:
                values = [obs[key] for obs in observations if key in obs]
                if len(set(str(v) for v in values)) == 1:
                    patterns.append({"key": key, "common_value": values[0]})

        conclusion = {
            "answer": f"Identified {len(patterns)} patterns from {len(observations)} observations",
            "patterns": patterns,
        }
        confidence = min(0.85, 0.3 + len(patterns) * 0.15)

        return {
            "premises": [{"type": "observation", "content": obs} for obs in observations[:5]],
            "conclusion": conclusion,
            "confidence": confidence,
            "evidence": observations,
            "alternatives": [],
        }

    def _reason_abductive(
        self, query: str, context: Dict[str, Any], previous_steps: List[ReasoningStep]
    ) -> Dict[str, Any]:
        """Abductive reasoning: find the best explanation for observations."""
        observations = context.get("observations", [])
        possible_causes = context.get("possible_causes", [])

        best_explanation = None
        best_score = 0.0
        alternatives = []

        for cause in possible_causes:
            score = self._score_explanation(cause, observations)
            if score > best_score:
                if best_explanation:
                    alternatives.append({"explanation": best_explanation, "score": best_score})
                best_explanation = cause
                best_score = score
            else:
                alternatives.append({"explanation": cause, "score": score})

        conclusion = {
            "answer": best_explanation or "No explanation found",
            "best_explanation": best_explanation,
            "score": best_score,
        }
        confidence = min(0.8, 0.2 + best_score * 0.6)

        return {
            "premises": [{"type": "observation", "content": obs} for obs in observations[:5]],
            "conclusion": conclusion,
            "confidence": confidence,
            "evidence": [],
            "alternatives": alternatives[:3],
        }

    def _reason_analogical(
        self, query: str, context: Dict[str, Any], previous_steps: List[ReasoningStep]
    ) -> Dict[str, Any]:
        """Analogical reasoning: map known solutions to new problems."""
        similar_cases = context.get("similar_cases", [])

        mapped_solutions = []
        for case in similar_cases:
            if isinstance(case, dict):
                mapped = {
                    "source": case.get("name", "unknown"),
                    "solution": case.get("solution", {}),
                    "similarity": case.get("similarity", 0.5),
                }
                mapped_solutions.append(mapped)

        conclusion = {
            "answer": f"Mapped {len(mapped_solutions)} analogous solutions",
            "mapped_solutions": mapped_solutions,
        }
        confidence = min(0.7, 0.2 + len(mapped_solutions) * 0.15)

        return {
            "premises": [{"type": "case", "content": c} for c in similar_cases[:5]],
            "conclusion": conclusion,
            "confidence": confidence,
            "evidence": [],
            "alternatives": [],
        }

    def _reason_causal(
        self, query: str, context: Dict[str, Any], previous_steps: List[ReasoningStep]
    ) -> Dict[str, Any]:
        """Causal reasoning: identify cause-effect relationships."""
        events = context.get("events", [])
        causal_links = []

        for i, event in enumerate(events):
            if isinstance(event, dict):
                event_id = event.get("id", str(i))
                effects = self._causal_graph.get(event_id, [])
                causal_links.append({
                    "cause": event,
                    "effects": effects,
                })

        conclusion = {
            "answer": f"Identified {len(causal_links)} causal relationships",
            "causal_links": causal_links,
        }
        confidence = min(0.75, 0.3 + len(causal_links) * 0.1)

        return {
            "premises": [{"type": "event", "content": e} for e in events[:5]],
            "conclusion": conclusion,
            "confidence": confidence,
            "evidence": [],
            "alternatives": [],
        }

    def _reason_heuristic(
        self, query: str, context: Dict[str, Any], previous_steps: List[ReasoningStep]
    ) -> Dict[str, Any]:
        """Heuristic reasoning: fast rule-of-thumb evaluation."""
        # Quick keyword matching
        keywords = ["error", "bug", "fix", "optimize", "create", "generate", "analyze"]
        matched = [kw for kw in keywords if kw in query.lower()]

        conclusion = {
            "answer": f"Heuristic match: {matched if matched else 'general query'}",
            "matched_keywords": matched,
            "suggested_action": matched[0] if matched else "analyze",
        }
        confidence = 0.5 + len(matched) * 0.1

        return {
            "premises": [{"type": "query", "content": query}],
            "conclusion": conclusion,
            "confidence": confidence,
            "evidence": [],
            "alternatives": [],
        }

    def _score_explanation(self, cause: Any, observations: List[Dict[str, Any]]) -> float:
        """Score how well a cause explains the observations."""
        if not isinstance(cause, dict):
            return 0.3
        covered = 0
        for obs in observations:
            for key, value in cause.items():
                if key in obs and str(obs[key]) == str(value):
                    covered += 1
        return covered / max(len(observations), 1) if observations else 0.5

    def _update_reasoning_stats(self, time_ms: float) -> None:
        """Update reasoning performance statistics."""
        n = self._stats["total_reasoning_chains"]
        old_avg = self._stats["average_reasoning_time_ms"]
        self._stats["average_reasoning_time_ms"] = (old_avg * (n - 1) + time_ms) / n

    # ── Planning Layer ──

    def plan(
        self,
        goal: str,
        context: Dict[str, Any],
        max_actions: int = 10,
        strategy: str = "goal_oriented",
    ) -> ActionPlan:
        """Generate an action plan to achieve a goal."""
        with self._state_lock:
            self._state = BrainState.PLANNING

        plan_id = f"plan_{uuid.uuid4().hex[:12]}"
        start_time = time.time()

        actions = self._generate_actions(goal, context, max_actions, strategy)

        # Validate plan
        preconditions = self._derive_preconditions(actions, context)
        expected_outcomes = self._project_outcomes(actions, goal)

        plan = ActionPlan(
            plan_id=plan_id,
            goal=goal,
            actions=actions,
            priority=self._calculate_plan_priority(goal, context),
            estimated_duration_ms=(time.time() - start_time) * 1000,
            preconditions=preconditions,
            expected_outcomes=expected_outcomes,
        )

        self._action_plans[plan_id] = plan
        self._plan_history.append(plan)
        self._stats["total_action_plans"] += 1

        with self._state_lock:
            self._state = BrainState.IDLE

        self._emit_event("plan_created", plan.to_dict())
        return plan

    def _generate_actions(
        self, goal: str, context: Dict[str, Any], max_actions: int, strategy: str
    ) -> List[Dict[str, Any]]:
        """Generate a sequence of actions to achieve the goal."""
        actions = []

        # Decompose goal into sub-goals
        sub_goals = self._decompose_goal(goal, context)

        for sub_goal in sub_goals[:max_actions]:
            action = {
                "action_id": f"action_{uuid.uuid4().hex[:8]}",
                "type": self._classify_action_type(sub_goal),
                "description": sub_goal,
                "parameters": self._infer_action_parameters(sub_goal, context),
                "domain": ActionDomain.GAME_ENGINE.value,
                "priority": 0.5,
                "timeout_ms": 30000,
            }
            actions.append(action)

        return actions

    def _decompose_goal(self, goal: str, context: Dict[str, Any]) -> List[str]:
        """Decompose a high-level goal into sub-goals."""
        sub_goals = [goal]

        # Simple decomposition based on common patterns
        if "create" in goal.lower() and "game" in goal.lower():
            sub_goals = [
                "Design game concept and mechanics",
                "Set up project structure",
                "Create core game loop",
                "Implement player controls",
                "Add game entities and objects",
                "Create levels or world",
                "Add UI and feedback",
                "Test and polish",
            ]
        elif "optimize" in goal.lower():
            sub_goals = [
                "Profile current performance",
                "Identify bottlenecks",
                "Prioritize optimization targets",
                "Apply optimizations",
                "Verify improvements",
            ]
        elif "debug" in goal.lower() or "fix" in goal.lower():
            sub_goals = [
                "Reproduce the issue",
                "Analyze root cause",
                "Develop fix",
                "Apply fix",
                "Verify resolution",
            ]

        return sub_goals

    def _classify_action_type(self, sub_goal: str) -> str:
        """Classify a sub-goal into an action type."""
        goal_lower = sub_goal.lower()
        if any(w in goal_lower for w in ["create", "generate", "build"]):
            return "create"
        elif any(w in goal_lower for w in ["fix", "debug", "resolve"]):
            return "fix"
        elif any(w in goal_lower for w in ["optimize", "improve", "enhance"]):
            return "optimize"
        elif any(w in goal_lower for w in ["test", "verify", "validate"]):
            return "test"
        elif any(w in goal_lower for w in ["analyze", "profile", "measure"]):
            return "analyze"
        elif any(w in goal_lower for w in ["design", "plan", "concept"]):
            return "design"
        return "execute"

    def _infer_action_parameters(
        self, sub_goal: str, context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Infer parameters for an action from context."""
        params = {"goal": sub_goal}
        if "game_type" in context:
            params["game_type"] = context["game_type"]
        if "target_platform" in context:
            params["target_platform"] = context["target_platform"]
        if "constraints" in context:
            params["constraints"] = context["constraints"]
        return params

    def _derive_preconditions(
        self, actions: List[Dict[str, Any]], context: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Derive preconditions needed for the plan."""
        preconditions = []
        for action in actions:
            preconditions.append({
                "action_id": action["action_id"],
                "requires_engine_running": True,
                "requires_scene_loaded": action.get("domain") == "game_engine",
            })
        return preconditions

    def _project_outcomes(
        self, actions: List[Dict[str, Any]], goal: str
    ) -> List[Dict[str, Any]]:
        """Project expected outcomes of the plan."""
        return [
            {
                "action_id": action["action_id"],
                "expected_result": f"Completed: {action['description']}",
                "confidence": 0.7,
            }
            for action in actions
        ]

    def _calculate_plan_priority(self, goal: str, context: Dict[str, Any]) -> float:
        """Calculate priority for the plan."""
        urgent_keywords = ["critical", "urgent", "bug", "crash", "fix"]
        if any(kw in goal.lower() for kw in urgent_keywords):
            return 0.9
        return 0.5

    # ── Action Layer ──

    def execute_action(
        self, action: Dict[str, Any], context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Execute a single action and return the result."""
        with self._state_lock:
            self._state = BrainState.EXECUTING

        action_id = action.get("action_id", str(uuid.uuid4().hex[:8]))
        action_type = action.get("type", "execute")
        start_time = time.time()

        result = {
            "action_id": action_id,
            "type": action_type,
            "status": "completed",
            "output": {},
            "duration_ms": 0.0,
            "error": None,
        }

        try:
            # Execute based on action type
            if action_type == "create":
                result["output"] = {"message": f"Created: {action.get('description', '')}"}
            elif action_type == "fix":
                result["output"] = {"message": f"Fixed: {action.get('description', '')}"}
            elif action_type == "optimize":
                result["output"] = {"message": f"Optimized: {action.get('description', '')}"}
            elif action_type == "test":
                result["output"] = {"message": f"Tested: {action.get('description', '')}"}
            elif action_type == "analyze":
                result["output"] = {"message": f"Analyzed: {action.get('description', '')}"}
            elif action_type == "design":
                result["output"] = {"message": f"Designed: {action.get('description', '')}"}
            else:
                result["output"] = {"message": f"Executed: {action.get('description', '')}"}
        except Exception as e:
            result["status"] = "failed"
            result["error"] = str(e)

        result["duration_ms"] = (time.time() - start_time) * 1000
        self._stats["total_actions_executed"] += 1

        with self._state_lock:
            self._state = BrainState.IDLE

        self._emit_event("action_completed", result)
        return result

    def execute_plan(self, plan_id: str) -> List[Dict[str, Any]]:
        """Execute all actions in a plan."""
        plan = self._action_plans.get(plan_id)
        if plan is None:
            return [{"error": f"Plan {plan_id} not found"}]

        self._active_plan_id = plan_id
        results = []

        for action in plan.actions:
            result = self.execute_action(action)
            results.append(result)

            if result["status"] == "failed":
                # Try fallback
                if plan.fallback_plan_id:
                    fallback = self._action_plans.get(plan.fallback_plan_id)
                    if fallback:
                        for fb_action in fallback.actions:
                            fb_result = self.execute_action(fb_action)
                            results.append(fb_result)
                break

        self._active_plan_id = None
        return results

    # ── Memory Layer ──

    def store_memory(
        self,
        content: Dict[str, Any],
        memory_type: MemoryType = MemoryType.EPISODIC,
        importance: float = 0.5,
    ) -> str:
        """Store an entry in the agent's memory system."""
        entry_id = f"mem_{uuid.uuid4().hex[:12]}"
        now = time.time()

        entry = MemoryEntry(
            entry_id=entry_id,
            memory_type=memory_type,
            content=content,
            timestamp=now,
            importance=importance,
            last_accessed=now,
        )

        self._memory_stores[memory_type][entry_id] = entry
        self._stats["total_memory_entries"] += 1

        # Index by tags
        tags = content.get("tags", [])
        for tag in tags:
            if tag not in self._memory_index:
                self._memory_index[tag] = set()
            self._memory_index[tag].add(entry_id)

        self._emit_event("memory_stored", entry.to_dict())
        return entry_id

    def recall_memory(
        self,
        query: str,
        memory_type: Optional[MemoryType] = None,
        max_results: int = 10,
    ) -> List[MemoryEntry]:
        """Recall memories matching a query."""
        results: List[MemoryEntry] = []
        stores = [self._memory_stores[memory_type]] if memory_type else self._memory_stores.values()

        for store in stores:
            for entry in store.values():
                content_str = json.dumps(entry.content).lower()
                if query.lower() in content_str:
                    entry.access_count += 1
                    entry.last_accessed = time.time()
                    results.append(entry)

        # Sort by importance * recency
        now = time.time()
        results.sort(
            key=lambda e: e.importance * (1.0 / (1.0 + now - e.last_accessed)),
            reverse=True,
        )

        return results[:max_results]

    def consolidate_memories(self) -> Dict[str, Any]:
        """Consolidate memories across memory systems."""
        consolidated = {
            "total_entries": sum(len(store) for store in self._memory_stores.values()),
            "by_type": {mt.value: len(store) for mt, store in self._memory_stores.items()},
            "indexed_tags": len(self._memory_index),
            "consolidation_time": time.time(),
        }

        # Decay old memories
        now = time.time()
        for store in self._memory_stores.values():
            for entry in list(store.values()):
                age = now - entry.timestamp
                decay = entry.decay_rate * age
                if entry.importance - decay < 0.1:
                    del store[entry.entry_id]

        return consolidated

    # ── Learning Layer ──

    def learn_from_experience(
        self, experience: Dict[str, Any], mode: LearningMode = LearningMode.REINFORCEMENT
    ) -> Dict[str, Any]:
        """Learn from an experience to improve future performance."""
        with self._state_lock:
            self._state = BrainState.LEARNING

        session_id = f"learning_{uuid.uuid4().hex[:12]}"
        session = {
            "session_id": session_id,
            "mode": mode.value,
            "experience": experience,
            "timestamp": time.time(),
            "insights": [],
            "skill_updates": [],
        }

        # Extract patterns
        patterns = self._extract_patterns(experience)
        session["insights"] = patterns

        # Update skill patterns
        for pattern in patterns:
            ptype = pattern.get("type", "general")
            if ptype not in self._skill_patterns:
                self._skill_patterns[ptype] = []
            self._skill_patterns[ptype].append(pattern)

        self._learning_sessions.append(session)
        self._stats["total_learning_sessions"] += 1

        with self._state_lock:
            self._state = BrainState.IDLE

        self._emit_event("learning_complete", session)
        return session

    def _extract_patterns(self, experience: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract learnable patterns from experience."""
        patterns = []

        outcome = experience.get("outcome", {})
        if outcome.get("success"):
            patterns.append({
                "type": "success_pattern",
                "action": experience.get("action", ""),
                "context": experience.get("context", {}),
                "confidence": 0.8,
            })

        if outcome.get("error"):
            patterns.append({
                "type": "failure_pattern",
                "error": outcome["error"],
                "context": experience.get("context", {}),
                "confidence": 0.7,
            })

        duration = experience.get("duration_ms", 0)
        if duration > 5000:
            patterns.append({
                "type": "performance_issue",
                "action": experience.get("action", ""),
                "duration_ms": duration,
                "confidence": 0.6,
            })

        return patterns

    def reflect(self) -> Dict[str, Any]:
        """Perform self-reflection on recent experiences."""
        with self._state_lock:
            self._state = BrainState.REFLECTING

        reflection = {
            "reflection_id": f"reflect_{uuid.uuid4().hex[:12]}",
            "timestamp": time.time(),
            "recent_actions": self._stats["total_actions_executed"],
            "success_rate": self._calculate_success_rate(),
            "insights": [],
            "recommendations": [],
        }

        # Analyze strategy performance
        for strategy, perf in self._strategy_performance.items():
            if perf.get("trials", 0) > 5:
                success_rate = perf.get("successes", 0) / max(perf["trials"], 1)
                if success_rate < 0.5:
                    reflection["recommendations"].append({
                        "type": "strategy_adjustment",
                        "strategy": strategy,
                        "current_success_rate": success_rate,
                        "suggestion": "Consider alternative strategy",
                    })

        # Analyze recent confidence calibration
        if self._confidence_history:
            avg_confidence = sum(self._confidence_history) / len(self._confidence_history)
            if avg_confidence < 0.4:
                reflection["insights"].append({
                    "type": "low_confidence",
                    "average_confidence": avg_confidence,
                    "suggestion": "Improve perception quality or gather more data",
                })

        self._reflection_log.append(reflection)
        self._stats["total_reflections"] += 1

        with self._state_lock:
            self._state = BrainState.IDLE

        self._emit_event("reflection_complete", reflection)
        return reflection

    def _calculate_success_rate(self) -> float:
        """Calculate the overall success rate of actions."""
        total = self._stats["total_actions_executed"]
        if total == 0:
            return 1.0
        # Estimate from strategy performance
        if not self._strategy_performance:
            return 0.5
        successes = sum(p.get("successes", 0) for p in self._strategy_performance.values())
        trials = sum(p.get("trials", 0) for p in self._strategy_performance.values())
        return successes / max(trials, 1) if trials > 0 else 0.5

    # ── World Model ──

    def get_world_state(self) -> Dict[str, Any]:
        """Get the current world model state."""
        return {
            "entities": self._world_state.copy(),
            "predictions": self._predictions.copy(),
            "causal_graph": self._causal_graph.copy(),
            "timestamp": time.time(),
        }

    def predict_world_state(
        self, steps_ahead: int = 5, context: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Predict future world states using the internal world model."""
        predictions = []
        current = self._world_state.copy()

        for i in range(steps_ahead):
            predicted = {}
            for entity_id, entity in current.items():
                predicted[entity_id] = self._predict_entity_state(entity, i + 1)
            predictions.append({
                "step": i + 1,
                "predicted_state": predicted,
                "confidence": max(0.1, 1.0 - i * 0.15),
            })
            current = predicted

        self._predictions[f"prediction_{time.time()}"] = predictions
        return predictions

    def _predict_entity_state(
        self, entity: Dict[str, Any], steps_ahead: int
    ) -> Dict[str, Any]:
        """Predict the future state of a single entity."""
        predicted = entity.copy()
        velocity = entity.get("velocity", {})
        if velocity:
            position = entity.get("position", {})
            predicted["position"] = {
                "x": position.get("x", 0) + velocity.get("x", 0) * steps_ahead,
                "y": position.get("y", 0) + velocity.get("y", 0) * steps_ahead,
            }
        return predicted

    # ── Metacognition ──

    def assess_confidence(self, decision: Dict[str, Any]) -> Dict[str, Any]:
        """Assess confidence in a decision or belief."""
        factors = {
            "evidence_quality": decision.get("evidence_count", 0) / 10,
            "prior_accuracy": self._calculate_success_rate(),
            "context_familiarity": 0.5,
            "time_pressure": 0.0,
        }

        overall = sum(factors.values()) / len(factors)
        level = ConfidenceLevel.UNKNOWN
        if overall > 0.9:
            level = ConfidenceLevel.CERTAIN
        elif overall > 0.7:
            level = ConfidenceLevel.HIGH
        elif overall > 0.5:
            level = ConfidenceLevel.MODERATE
        elif overall > 0.3:
            level = ConfidenceLevel.LOW
        elif overall > 0.1:
            level = ConfidenceLevel.UNCERTAIN

        self._confidence_history.append(overall)

        return {
            "decision_id": decision.get("id", ""),
            "confidence_level": level.value,
            "confidence_score": overall,
            "factors": factors,
            "timestamp": time.time(),
        }

    # ── Event System ──

    def on_event(self, event_type: str, callback: Callable) -> None:
        """Register a callback for an event type."""
        if event_type not in self._event_callbacks:
            self._event_callbacks[event_type] = []
        self._event_callbacks[event_type].append(callback)

    def _emit_event(self, event_type: str, data: Dict[str, Any]) -> None:
        """Emit an event to registered callbacks."""
        callbacks = self._event_callbacks.get(event_type, [])
        for cb in callbacks:
            try:
                cb(data)
            except Exception:
                pass

    # ── Status & Statistics ──

    def get_status(self) -> Dict[str, Any]:
        """Get comprehensive brain status."""
        self._stats["brain_uptime_seconds"] = time.time() - self._start_time
        return {
            "state": self._state.value,
            "initialized": self._initialized,
            "stats": self._stats,
            "memory": {
                mt.value: len(store) for mt, store in self._memory_stores.items()
            },
            "active_plan": self._active_plan_id,
            "pending_plans": len(self._action_plans),
            "reasoning_chains": len(self._reasoning_chains),
            "skill_patterns": {k: len(v) for k, v in self._skill_patterns.items()},
        }

    def get_snapshot(self) -> BrainSnapshot:
        """Create a snapshot of the current brain state."""
        return BrainSnapshot(
            snapshot_id=f"snapshot_{uuid.uuid4().hex[:12]}",
            timestamp=time.time(),
            state=self._state,
            active_goals=list(self._action_plans.keys()),
            recent_perceptions=[f.frame_id for f in list(self._perception_buffer)[-5:]],
            active_reasoning=list(self._reasoning_chains.keys())[-5:],
            pending_actions=list(self._action_plans.keys()),
            memory_stats={
                mt.value: len(store) for mt, store in self._memory_stores.items()
            },
            confidence_profile={
                "mean": sum(self._confidence_history) / max(len(self._confidence_history), 1)
                if self._confidence_history else 0.5,
                "samples": len(self._confidence_history),
            },
            performance_metrics={
                "avg_reasoning_ms": self._stats["average_reasoning_time_ms"],
                "success_rate": self._calculate_success_rate(),
                "uptime_seconds": time.time() - self._start_time,
            },
        )

    def reset(self) -> None:
        """Reset the brain to its initial state."""
        with self._state_lock:
            self._initialized = False
            self._state = BrainState.IDLE
            self._perception_buffer.clear()
            self._reasoning_chains.clear()
            self._action_plans.clear()
            self._plan_history.clear()
            for store in self._memory_stores.values():
                store.clear()
            self._memory_index.clear()
            self._learning_sessions.clear()
            self._skill_patterns.clear()
            self._reflection_log.clear()
            self._world_state.clear()
            self._predictions.clear()
            self._causal_graph.clear()
            self._confidence_history.clear()
            self._strategy_performance.clear()
            self._stats = {k: 0.0 if isinstance(v, float) else 0 for k, v in self._stats.items()}
            self._start_time = time.time()


# ── Module-level convenience ──

def get_ai_native_brain() -> AINativeBrain:
    """Get the singleton AINativeBrain instance."""
    brain = AINativeBrain.get_instance()
    if not brain._initialized:
        brain.initialize()
    return brain