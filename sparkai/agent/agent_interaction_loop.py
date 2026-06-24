"""
SparkLabs Agent - Interaction Loop Engine

Manages continuous agent-environment feedback loops for game environments.
Implements the full perception-action-reflection-learning cycle that enables
agents to observe, decide, execute, reflect, and improve over time. The engine
orchestrates structured feedback loops with exploration-exploitation tradeoffs,
learning curves, and strategy adaptation.

Architecture:
  InteractionLoopEngine (Singleton)
    |-- PerceptionProcessor (raw data -> structured frames)
    |-- DecisionEngine (state + strategy -> action selection)
    |-- ActionExecutor (action -> environment result)
    |-- ReflectionEngine (experience -> insights)
    |-- LearningEngine (feedback -> knowledge updates)
    |-- InteractionCycle (complete loop record)
    |-- LoopState (aggregate performance tracking)
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
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class LoopPhase(Enum):
    """Phases of a single interaction loop cycle."""
    PERCEPTION = "perception"
    INTERPRETATION = "interpretation"
    DECISION = "decision"
    ACTION = "action"
    EXECUTION = "execution"
    OBSERVATION = "observation"
    REFLECTION = "reflection"
    LEARNING = "learning"


class ActionType(Enum):
    """Types of actions an agent can perform in the environment."""
    MOVE = "move"
    ATTACK = "attack"
    DEFEND = "defend"
    INTERACT = "interact"
    COLLECT = "collect"
    CRAFT = "craft"
    DIALOGUE = "dialogue"
    OBSERVE = "observe"
    WAIT = "wait"
    USE_ITEM = "use_item"


class FeedbackSignal(Enum):
    """Signals received from the environment after action execution."""
    REWARD = "reward"
    PUNISHMENT = "punishment"
    NEUTRAL = "neutral"
    CURIOSITY = "curiosity"
    SURPRISE = "surprise"
    SATISFACTION = "satisfaction"
    FRUSTRATION = "frustration"


class ExplorationStrategy(Enum):
    """Strategies for balancing exploration vs exploitation."""
    GREEDY = "greedy"
    EPSILON_GREEDY = "epsilon_greedy"
    UCB = "ucb"
    THOMPSON_SAMPLING = "thompson_sampling"
    ENTROPY_MAX = "entropy_max"
    CURIOSITY_DRIVEN = "curiosity_driven"


class LearningMode(Enum):
    """Modes of learning the agent can employ."""
    SUPERVISED = "supervised"
    REINFORCEMENT = "reinforcement"
    IMITATION = "imitation"
    SELF_SUPERVISED = "self_supervised"
    ACTIVE = "active"
    TRANSFER = "transfer"


# ---------------------------------------------------------------------------
# Data Classes
# ---------------------------------------------------------------------------


@dataclass
class PerceptionFrame:
    """Structured representation of the agent's perceived environment state."""
    frame_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    timestamp: float = field(default_factory=time.time)
    visual_data: Dict[str, Any] = field(default_factory=dict)
    audio_data: Dict[str, Any] = field(default_factory=dict)
    spatial_data: Dict[str, Any] = field(default_factory=dict)
    entity_detections: List[Dict[str, Any]] = field(default_factory=list)
    environment_state: Dict[str, Any] = field(default_factory=dict)
    confidence: float = 0.5

    def to_dict(self) -> Dict[str, Any]:
        return {
            "frame_id": self.frame_id,
            "timestamp": self.timestamp,
            "visual_data": self.visual_data,
            "audio_data": self.audio_data,
            "spatial_data": self.spatial_data,
            "entity_detections": self.entity_detections,
            "environment_state": self.environment_state,
            "confidence": self.confidence,
        }


@dataclass
class ActionDecision:
    """An action choice made by the decision engine with supporting rationale."""
    decision_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    chosen_action: ActionType = ActionType.OBSERVE
    alternatives: List[Tuple[ActionType, float]] = field(default_factory=list)
    expected_outcome: Dict[str, Any] = field(default_factory=dict)
    risk_assessment: float = 0.0
    confidence: float = 0.5
    reasoning: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "decision_id": self.decision_id,
            "chosen_action": self.chosen_action.value,
            "alternatives": [(a.value, s) for a, s in self.alternatives],
            "expected_outcome": self.expected_outcome,
            "risk_assessment": self.risk_assessment,
            "confidence": self.confidence,
            "reasoning": self.reasoning[:200],
        }


@dataclass
class ExecutionResult:
    """Result of executing an action in the environment."""
    result_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    action: ActionType = ActionType.OBSERVE
    success: bool = False
    outcome_state: Dict[str, Any] = field(default_factory=dict)
    reward: float = 0.0
    time_taken: float = 0.0
    side_effects: List[Dict[str, Any]] = field(default_factory=list)
    error_info: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "result_id": self.result_id,
            "action": self.action.value,
            "success": self.success,
            "outcome_state": self.outcome_state,
            "reward": self.reward,
            "time_taken": self.time_taken,
            "side_effects": self.side_effects,
            "error_info": self.error_info,
        }


@dataclass
class ReflectionEntry:
    """Post-cycle analysis of what happened and what was learned."""
    entry_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    experience_summary: str = ""
    lessons_learned: List[str] = field(default_factory=list)
    surprise_factors: List[Dict[str, Any]] = field(default_factory=list)
    strategy_adjustments: List[Dict[str, Any]] = field(default_factory=list)
    confidence_update: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "entry_id": self.entry_id,
            "experience_summary": self.experience_summary[:200],
            "lessons_learned": self.lessons_learned,
            "surprise_factors": self.surprise_factors,
            "strategy_adjustments": self.strategy_adjustments,
            "confidence_update": self.confidence_update,
        }


@dataclass
class LearningUpdate:
    """Knowledge and skill changes derived from feedback and reflection."""
    update_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    knowledge_gained: List[Dict[str, Any]] = field(default_factory=list)
    skill_improvements: List[Dict[str, Any]] = field(default_factory=list)
    parameter_adjustments: Dict[str, float] = field(default_factory=dict)
    exploration_rate_change: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "update_id": self.update_id,
            "knowledge_gained": self.knowledge_gained,
            "skill_improvements": self.skill_improvements,
            "parameter_adjustments": self.parameter_adjustments,
            "exploration_rate_change": self.exploration_rate_change,
        }


@dataclass
class InteractionCycle:
    """A complete cycle of the interaction loop with all phase data."""
    cycle_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    phase_timings: Dict[str, float] = field(default_factory=dict)
    perception_frame: Optional[PerceptionFrame] = None
    action_decision: Optional[ActionDecision] = None
    execution_result: Optional[ExecutionResult] = None
    reflection: Optional[ReflectionEntry] = None
    learning_update: Optional[LearningUpdate] = None

    @property
    def total_time(self) -> float:
        if not self.phase_timings:
            return 0.0
        return sum(self.phase_timings.values())

    @property
    def was_successful(self) -> bool:
        if self.execution_result is None:
            return False
        return self.execution_result.success

    def to_dict(self) -> Dict[str, Any]:
        return {
            "cycle_id": self.cycle_id,
            "phase_timings": self.phase_timings,
            "total_time": self.total_time,
            "was_successful": self.was_successful,
            "perception": self.perception_frame.to_dict() if self.perception_frame else None,
            "decision": self.action_decision.to_dict() if self.action_decision else None,
            "execution": self.execution_result.to_dict() if self.execution_result else None,
            "reflection": self.reflection.to_dict() if self.reflection else None,
            "learning": self.learning_update.to_dict() if self.learning_update else None,
        }


@dataclass
class LoopState:
    """Aggregate state tracking across all cycles."""
    state_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    total_cycles: int = 0
    exploration_rate: float = 1.0
    performance_curve: List[float] = field(default_factory=list)
    learning_progress: Dict[str, Any] = field(default_factory=dict)
    strategy_distribution: Dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "state_id": self.state_id,
            "total_cycles": self.total_cycles,
            "exploration_rate": self.exploration_rate,
            "performance_curve": self.performance_curve[-50:],
            "learning_progress": self.learning_progress,
            "strategy_distribution": self.strategy_distribution,
        }


# ---------------------------------------------------------------------------
# Component Classes
# ---------------------------------------------------------------------------


class PerceptionProcessor:
    """
    Processes raw environment data into structured perception frames.

    Fuses multi-modal sensory inputs (visual, audio, spatial) into a
    unified perception frame with confidence scoring. Handles entity
    detection, spatial reasoning, and state estimation.
    """

    def __init__(self):
        self._sensor_noise: float = 0.02
        self._detection_threshold: float = 0.3
        self._entity_templates: Dict[str, Dict[str, Any]] = _build_entity_templates()

    def process(self, raw_data: Dict[str, Any]) -> PerceptionFrame:
        """Convert raw environment data into a structured perception frame."""
        visual = self._extract_visual(raw_data)
        audio = self._extract_audio(raw_data)
        spatial = self._extract_spatial(raw_data)
        entities = self._detect_entities(raw_data)
        env_state = self._parse_environment_state(raw_data)

        visual_conf = self._compute_confidence(visual, "visual")
        audio_conf = self._compute_confidence(audio, "audio")
        spatial_conf = self._compute_confidence(spatial, "spatial")
        overall_confidence = (visual_conf + audio_conf + spatial_conf) / 3.0

        return PerceptionFrame(
            visual_data=visual,
            audio_data=audio,
            spatial_data=spatial,
            entity_detections=entities,
            environment_state=env_state,
            confidence=round(overall_confidence, 4),
        )

    def _extract_visual(self, raw: Dict[str, Any]) -> Dict[str, Any]:
        visual = raw.get("visual", raw.get("vision", {}))
        return {
            "visible_objects": visual.get("objects", []),
            "terrain_type": visual.get("terrain", "unknown"),
            "lighting_level": visual.get("lighting", 0.5),
            "visibility_range": visual.get("range", 10.0),
            "obstacles": visual.get("obstacles", []),
            "color_dominant": visual.get("dominant_color", "neutral"),
        }

    def _extract_audio(self, raw: Dict[str, Any]) -> Dict[str, Any]:
        audio = raw.get("audio", raw.get("sound", {}))
        return {
            "ambient_level": audio.get("ambient", 0.0),
            "detected_sounds": audio.get("sounds", []),
            "sound_directions": audio.get("directions", []),
            "speech_detected": audio.get("speech", False),
            "audio_intensity": audio.get("intensity", 0.0),
        }

    def _extract_spatial(self, raw: Dict[str, Any]) -> Dict[str, Any]:
        spatial = raw.get("spatial", raw.get("position", {}))
        return {
            "agent_position": spatial.get("position", [0.0, 0.0, 0.0]),
            "agent_orientation": spatial.get("orientation", [0.0, 0.0, 0.0]),
            "nearby_points": spatial.get("nearby", []),
            "distance_to_goal": spatial.get("goal_distance", float("inf")),
            "region": spatial.get("region", "unknown"),
            "elevation": spatial.get("elevation", 0.0),
        }

    def _detect_entities(self, raw: Dict[str, Any]) -> List[Dict[str, Any]]:
        entities = raw.get("entities", raw.get("objects", []))
        detected = []
        for ent in entities:
            if isinstance(ent, dict):
                entity_type = ent.get("type", "unknown")
                template = self._entity_templates.get(entity_type, {})
                confidence = ent.get("confidence", random.uniform(0.5, 0.95))
                if confidence >= self._detection_threshold:
                    detected.append({
                        "entity_type": entity_type,
                        "entity_id": ent.get("id", str(uuid.uuid4())[:8]),
                        "position": ent.get("position", [0.0, 0.0, 0.0]),
                        "confidence": confidence,
                        "attributes": {**template, **ent.get("attributes", {})},
                        "distance": ent.get("distance", 0.0),
                        "threat_level": ent.get("threat", 0.0),
                    })
        return detected

    def _parse_environment_state(self, raw: Dict[str, Any]) -> Dict[str, Any]:
        env = raw.get("environment", raw.get("env", {}))
        return {
            "time_of_day": env.get("time", "day"),
            "weather": env.get("weather", "clear"),
            "danger_level": env.get("danger", 0.0),
            "resource_density": env.get("resources", 0.5),
            "map_id": env.get("map", "default"),
            "global_state": env.get("state", {}),
        }

    def _compute_confidence(self, data: Dict[str, Any], modality: str) -> float:
        noise = random.gauss(0, self._sensor_noise)
        base = 0.85 if data.get("visibility_range", 0) > 0 else 0.6
        if modality == "audio" and data.get("ambient_level", 0) > 0.7:
            base -= 0.1
        if modality == "visual" and data.get("lighting_level", 0.5) < 0.3:
            base -= 0.15
        return max(0.1, min(1.0, base + noise))


def _build_entity_templates() -> Dict[str, Dict[str, Any]]:
    """Build default entity recognition templates."""
    return {
        "player": {"interactive": True, "hostile": False, "collectible": False},
        "enemy": {"interactive": False, "hostile": True, "collectible": False},
        "npc": {"interactive": True, "hostile": False, "collectible": False},
        "item": {"interactive": True, "hostile": False, "collectible": True},
        "obstacle": {"interactive": False, "hostile": False, "collectible": False},
        "resource": {"interactive": True, "hostile": False, "collectible": True},
        "portal": {"interactive": True, "hostile": False, "collectible": False},
        "trap": {"interactive": False, "hostile": True, "collectible": False},
    }


class DecisionEngine:
    """
    Selects actions based on current state, exploration strategy, and learned policies.

    Implements multiple exploration-exploitation strategies including
    epsilon-greedy, UCB, Thompson sampling, and curiosity-driven selection.
    Maintains Q-value estimates and action success statistics.
    """

    def __init__(self):
        self._q_values: Dict[str, Dict[ActionType, float]] = defaultdict(
            lambda: {a: random.uniform(0.0, 0.3) for a in ActionType}
        )
        self._action_counts: Dict[str, Dict[ActionType, int]] = defaultdict(
            lambda: {a: 0 for a in ActionType}
        )
        self._action_successes: Dict[str, Dict[ActionType, int]] = defaultdict(
            lambda: {a: 0 for a in ActionType}
        )
        self._total_actions: int = 0
        self._state_visits: Dict[str, int] = defaultdict(int)

    def decide(
        self,
        perception: PerceptionFrame,
        strategy: Optional[ExplorationStrategy] = None,
    ) -> ActionDecision:
        """
        Select the best action given the current perception and strategy.

        If no strategy is specified, defaults to epsilon-greedy as a
        reasonable balance between exploration and exploitation.
        """
        if strategy is None:
            strategy = ExplorationStrategy.EPSILON_GREEDY

        state_key = self._derive_state_key(perception)
        self._state_visits[state_key] += 1
        self._total_actions += 1

        chosen_action = self._select_action(state_key, strategy)
        alternatives = self._rank_alternatives(state_key, chosen_action)
        expected = self._estimate_outcome(chosen_action, perception)
        risk = self._assess_risk(chosen_action, state_key)

        confidence = self._compute_decision_confidence(chosen_action, state_key)
        reasoning = self._generate_reasoning(chosen_action, strategy, perception)

        return ActionDecision(
            chosen_action=chosen_action,
            alternatives=alternatives,
            expected_outcome=expected,
            risk_assessment=round(risk, 4),
            confidence=round(confidence, 4),
            reasoning=reasoning,
        )

    def _derive_state_key(self, perception: PerceptionFrame) -> str:
        """Derive a compact state key from the perception frame."""
        env = perception.environment_state
        entities = perception.entity_detections
        nearby_types = sorted(set(
            e["entity_type"] for e in entities if e.get("distance", 0) < 5.0
        ))
        threat = sum(e.get("threat_level", 0) for e in entities)
        time_of_day = env.get("time_of_day", "day")
        danger = "high" if env.get("danger_level", 0) > 0.5 else "low"
        parts = [time_of_day, danger, f"threat_{threat:.1f}", ",".join(nearby_types[:3])]
        return "|".join(parts)

    def _select_action(
        self,
        state_key: str,
        strategy: ExplorationStrategy,
    ) -> ActionType:
        """Select an action using the specified exploration strategy."""
        if strategy == ExplorationStrategy.GREEDY:
            return self._select_greedy(state_key)
        elif strategy == ExplorationStrategy.EPSILON_GREEDY:
            return self._select_epsilon_greedy(state_key)
        elif strategy == ExplorationStrategy.UCB:
            return self._select_ucb(state_key)
        elif strategy == ExplorationStrategy.THOMPSON_SAMPLING:
            return self._select_thompson(state_key)
        elif strategy == ExplorationStrategy.ENTROPY_MAX:
            return self._select_entropy_max(state_key)
        elif strategy == ExplorationStrategy.CURIOSITY_DRIVEN:
            return self._select_curiosity(state_key)
        return self._select_epsilon_greedy(state_key)

    def _select_greedy(self, state_key: str) -> ActionType:
        q = self._q_values[state_key]
        best_value = max(q.values())
        best_actions = [a for a, v in q.items() if v == best_value]
        return random.choice(best_actions)

    def _select_epsilon_greedy(self, state_key: str) -> ActionType:
        epsilon = max(0.05, 1.0 / (1 + math.sqrt(self._total_actions / 100)))
        if random.random() < epsilon:
            return random.choice(list(ActionType))
        return self._select_greedy(state_key)

    def _select_ucb(self, state_key: str) -> ActionType:
        q = self._q_values[state_key]
        counts = self._action_counts[state_key]
        best_action = ActionType.OBSERVE
        best_ucb = float("-inf")
        c = 2.0
        for action in ActionType:
            n = counts[action]
            if n == 0:
                return action
            ucb_value = q[action] + c * math.sqrt(math.log(self._total_actions + 1) / n)
            if ucb_value > best_ucb:
                best_ucb = ucb_value
                best_action = action
        return best_action

    def _select_thompson(self, state_key: str) -> ActionType:
        successes = self._action_successes[state_key]
        counts = self._action_counts[state_key]
        best_action = ActionType.OBSERVE
        best_sample = float("-inf")
        for action in ActionType:
            alpha = successes[action] + 1
            beta = counts[action] - successes[action] + 1
            sample = random.betavariate(max(1, alpha), max(1, beta))
            if sample > best_sample:
                best_sample = sample
                best_action = action
        return best_action

    def _select_entropy_max(self, state_key: str) -> ActionType:
        q = self._q_values[state_key]
        softmax_vals = _softmax([q[a] for a in ActionType])
        entropy = -sum(p * math.log(p + 1e-10) for p in softmax_vals)
        if entropy > 1.5:
            # High uncertainty — explore
            return random.choice(list(ActionType))
        return self._select_greedy(state_key)

    def _select_curiosity(self, state_key: str) -> ActionType:
        counts = self._action_counts[state_key]
        least_visited = min(counts, key=counts.get)
        if counts[least_visited] < 3:
            return least_visited
        return self._select_ucb(state_key)

    def _rank_alternatives(
        self,
        state_key: str,
        chosen: ActionType,
    ) -> List[Tuple[ActionType, float]]:
        q = self._q_values[state_key]
        ranked = sorted(
            [(a, v) for a, v in q.items() if a != chosen],
            key=lambda x: x[1],
            reverse=True,
        )
        return ranked[:3]

    def _estimate_outcome(
        self,
        action: ActionType,
        perception: PerceptionFrame,
    ) -> Dict[str, Any]:
        return {
            "action": action.value,
            "expected_reward": self._q_values.get(
                self._derive_state_key(perception), {}
            ).get(action, 0.0),
            "success_probability": self._estimate_success_rate(action),
            "estimated_duration": random.uniform(0.1, 2.0),
        }

    def _estimate_success_rate(self, action: ActionType) -> float:
        total = sum(
            self._action_counts[sk][action]
            for sk in self._action_counts
            if action in self._action_counts[sk]
        )
        if total == 0:
            return 0.5
        successes = sum(
            self._action_successes[sk][action]
            for sk in self._action_successes
            if action in self._action_successes[sk]
        )
        return round(successes / total, 4)

    def _assess_risk(self, action: ActionType, state_key: str) -> float:
        counts = self._action_counts[state_key]
        successes = self._action_successes[state_key]
        n = counts[action]
        if n == 0:
            return 0.5
        failure_rate = 1.0 - (successes[action] / n)
        risky_actions = {ActionType.ATTACK, ActionType.INTERACT}
        base_risk = 0.1 if action in risky_actions else 0.02
        return round(base_risk + failure_rate * 0.5, 4)

    def _compute_decision_confidence(self, action: ActionType, state_key: str) -> float:
        counts = self._action_counts[state_key]
        n = counts[action]
        if n == 0:
            return 0.3
        experience_factor = 1.0 - math.exp(-n / 10.0)
        q_value = self._q_values[state_key][action]
        return round(min(0.95, experience_factor * (0.5 + q_value * 0.5)), 4)

    def _generate_reasoning(
        self,
        action: ActionType,
        strategy: ExplorationStrategy,
        perception: PerceptionFrame,
    ) -> str:
        threat = sum(e.get("threat_level", 0) for e in perception.entity_detections)
        if threat > 0.7 and action == ActionType.DEFEND:
            return "High threat detected — prioritizing defense."
        if threat < 0.2 and action == ActionType.EXPLORE:
            return "Safe environment — exploring to gather information."
        if action == ActionType.COLLECT and perception.environment_state.get("resource_density", 0) > 0.5:
            return "Resource-rich area detected — collecting resources."
        return f"Selected {action.value} using {strategy.value} strategy."

    def update_q(self, state_key: str, action: ActionType, reward: float, lr: float = 0.1) -> None:
        """Update Q-value estimate using temporal-difference learning."""
        current = self._q_values[state_key][action]
        self._q_values[state_key][action] = current + lr * (reward - current)
        self._action_counts[state_key][action] += 1
        if reward > 0:
            self._action_successes[state_key][action] += 1


class ActionExecutor:
    """
    Executes actions in the environment and captures results.

    Simulates action execution with realistic timing, success/failure
    dynamics, side effects, and reward computation. Supports both
    deterministic and stochastic outcome models.
    """

    def __init__(self):
        self._base_success_rates: Dict[ActionType, float] = {
            ActionType.MOVE: 0.95,
            ActionType.ATTACK: 0.65,
            ActionType.DEFEND: 0.90,
            ActionType.INTERACT: 0.80,
            ActionType.COLLECT: 0.85,
            ActionType.CRAFT: 0.70,
            ActionType.DIALOGUE: 0.90,
            ActionType.OBSERVE: 0.98,
            ActionType.WAIT: 0.99,
            ActionType.USE_ITEM: 0.88,
        }
        self._action_durations: Dict[ActionType, Tuple[float, float]] = {
            ActionType.MOVE: (0.1, 0.5),
            ActionType.ATTACK: (0.2, 1.0),
            ActionType.DEFEND: (0.1, 0.3),
            ActionType.INTERACT: (0.3, 1.5),
            ActionType.COLLECT: (0.2, 0.8),
            ActionType.CRAFT: (0.5, 3.0),
            ActionType.DIALOGUE: (0.5, 2.0),
            ActionType.OBSERVE: (0.05, 0.2),
            ActionType.WAIT: (0.1, 1.0),
            ActionType.USE_ITEM: (0.1, 0.5),
        }

    def execute(self, action: ActionDecision, context: Dict[str, Any]) -> ExecutionResult:
        """Execute the chosen action in the given context and return the result."""
        action_type = action.chosen_action
        base_success = self._base_success_rates.get(action_type, 0.75)
        context_modifier = self._compute_context_modifier(action_type, context)
        success_prob = min(0.99, max(0.01, base_success * context_modifier))

        success = random.random() < success_prob
        time_taken = random.uniform(*self._action_durations.get(action_type, (0.1, 1.0)))

        reward = self._compute_reward(action_type, success, context)
        outcome_state = self._build_outcome_state(action_type, success, context)
        side_effects = self._generate_side_effects(action_type, success, context)
        error_info = None if success else self._generate_error(action_type, context)

        return ExecutionResult(
            action=action_type,
            success=success,
            outcome_state=outcome_state,
            reward=round(reward, 4),
            time_taken=round(time_taken, 4),
            side_effects=side_effects,
            error_info=error_info,
        )

    def _compute_context_modifier(
        self,
        action_type: ActionType,
        context: Dict[str, Any],
    ) -> float:
        modifier = 1.0
        env = context.get("environment", {})
        if env.get("danger_level", 0) > 0.7 and action_type in {ActionType.ATTACK, ActionType.MOVE}:
            modifier -= 0.15
        if env.get("weather") == "storm" and action_type == ActionType.MOVE:
            modifier -= 0.1
        if action_type == ActionType.CRAFT:
            skill_level = context.get("agent_skill", 0.5)
            modifier += (skill_level - 0.5) * 0.3
        return modifier

    def _compute_reward(
        self,
        action_type: ActionType,
        success: bool,
        context: Dict[str, Any],
    ) -> float:
        if not success:
            return random.uniform(-1.0, -0.1)
        base_rewards = {
            ActionType.MOVE: 0.1,
            ActionType.ATTACK: 0.6,
            ActionType.DEFEND: 0.3,
            ActionType.INTERACT: 0.5,
            ActionType.COLLECT: 0.7,
            ActionType.CRAFT: 0.8,
            ActionType.DIALOGUE: 0.4,
            ActionType.OBSERVE: 0.05,
            ActionType.WAIT: -0.05,
            ActionType.USE_ITEM: 0.5,
        }
        base = base_rewards.get(action_type, 0.2)
        noise = random.gauss(0, 0.1)
        return max(-1.0, min(1.0, base + noise))

    def _build_outcome_state(
        self,
        action_type: ActionType,
        success: bool,
        context: Dict[str, Any],
    ) -> Dict[str, Any]:
        prev_state = context.get("environment", {})
        return {
            "action_performed": action_type.value,
            "success": success,
            "position_changed": action_type == ActionType.MOVE,
            "resources_collected": int(action_type == ActionType.COLLECT and success),
            "damage_dealt": round(random.uniform(5, 30), 1) if action_type == ActionType.ATTACK and success else 0,
            "items_crafted": int(action_type == ActionType.CRAFT and success),
            "dialogue_triggered": action_type == ActionType.DIALOGUE and success,
            "previous_danger": prev_state.get("danger_level", 0),
        }

    def _generate_side_effects(
        self,
        action_type: ActionType,
        success: bool,
        context: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        effects = []
        if action_type == ActionType.ATTACK and success:
            effects.append({"effect": "noise_generated", "magnitude": random.uniform(0.3, 0.8)})
            effects.append({"effect": "entity_alerted", "range": 15.0})
        if action_type == ActionType.COLLECT and success:
            effects.append({"effect": "resource_depleted", "location": "current"})
        if action_type == ActionType.MOVE:
            effects.append({"effect": "position_updated", "distance": random.uniform(0.5, 3.0)})
        if random.random() < 0.1:
            effects.append({"effect": "unexpected_event", "type": "random"})
        return effects

    def _generate_error(self, action_type: ActionType, context: Dict[str, Any]) -> str:
        errors = {
            ActionType.MOVE: ["Path blocked by obstacle", "Terrain impassable"],
            ActionType.ATTACK: ["Target out of range", "Insufficient stamina"],
            ActionType.INTERACT: ["Object not interactive", "Interaction cooldown active"],
            ActionType.COLLECT: ["Resource already depleted", "Inventory full"],
            ActionType.CRAFT: ["Missing required materials", "Crafting station unavailable"],
            ActionType.DIALOGUE: ["NPC not available", "Dialogue already exhausted"],
        }
        options = errors.get(action_type, ["Unknown error occurred"])
        return random.choice(options)


class ReflectionEngine:
    """
    Analyzes experiences and adjusts strategies based on outcomes.

    Compares expected vs actual outcomes, identifies surprise factors,
    generates lessons learned, and recommends strategy adjustments.
    Maintains a rolling memory of recent experiences for pattern analysis.
    """

    def __init__(self):
        self._experience_buffer: deque = deque(maxlen=200)
        self._strategy_performance: Dict[ExplorationStrategy, List[float]] = defaultdict(list)
        self._surprise_threshold: float = 0.3
        self._adaptation_rate: float = 0.1

    def reflect(self, cycle: InteractionCycle) -> ReflectionEntry:
        """Analyze a completed cycle and generate a reflection entry."""
        decision = cycle.action_decision
        result = cycle.execution_result

        if decision is None or result is None:
            return ReflectionEntry(
                experience_summary="Incomplete cycle — no reflection possible.",
                lessons_learned=["Ensure all cycle phases complete before reflection."],
            )

        summary = self._summarize_experience(cycle)
        lessons = self._extract_lessons(decision, result)
        surprises = self._detect_surprises(decision, result)
        adjustments = self._recommend_adjustments(decision, result)
        confidence_delta = self._compute_confidence_update(decision, result)

        self._experience_buffer.append({
            "action": decision.chosen_action.value,
            "success": result.success,
            "reward": result.reward,
            "confidence": decision.confidence,
            "time": time.time(),
        })

        return ReflectionEntry(
            experience_summary=summary,
            lessons_learned=lessons,
            surprise_factors=surprises,
            strategy_adjustments=adjustments,
            confidence_update=round(confidence_delta, 4),
        )

    def _summarize_experience(self, cycle: InteractionCycle) -> str:
        decision = cycle.action_decision
        result = cycle.execution_result
        outcome = "succeeded" if result.success else "failed"
        return (
            f"Agent {outcome} in executing {decision.chosen_action.value} "
            f"with reward {result.reward:.3f} and confidence {decision.confidence:.3f}. "
            f"Time taken: {result.time_taken:.3f}s."
        )

    def _extract_lessons(
        self,
        decision: ActionDecision,
        result: ExecutionResult,
    ) -> List[str]:
        lessons = []
        if result.success and result.reward > 0.5:
            lessons.append(
                f"Action {decision.chosen_action.value} is highly effective — "
                f"consider prioritizing in similar states."
            )
        if not result.success:
            lessons.append(
                f"Action {decision.chosen_action.value} failed — "
                f"evaluate alternative actions or preconditions."
            )
            if result.error_info:
                lessons.append(f"Failure cause: {result.error_info}.")
        if result.reward < -0.5:
            lessons.append(
                f"Strong negative feedback for {decision.chosen_action.value} — "
                f"avoid in similar contexts."
            )
        if result.time_taken > 2.0:
            lessons.append(
                f"Action {decision.chosen_action.value} is time-consuming — "
                f"consider faster alternatives when time is critical."
            )
        if not lessons:
            lessons.append(
                f"Action {decision.chosen_action.value} produced neutral results — "
                f"continue monitoring."
            )
        return lessons

    def _detect_surprises(
        self,
        decision: ActionDecision,
        result: ExecutionResult,
    ) -> List[Dict[str, Any]]:
        surprises = []
        expected_reward = decision.expected_outcome.get("expected_reward", 0.0)
        actual_reward = result.reward
        reward_delta = abs(actual_reward - expected_reward)

        if reward_delta > self._surprise_threshold:
            surprises.append({
                "factor": "reward_mismatch",
                "expected": expected_reward,
                "actual": actual_reward,
                "delta": round(reward_delta, 4),
                "interpretation": (
                    "Better than expected" if actual_reward > expected_reward
                    else "Worse than expected"
                ),
            })

        if result.side_effects and len(result.side_effects) > 2:
            surprises.append({
                "factor": "unexpected_side_effects",
                "count": len(result.side_effects),
                "effects": [s.get("effect", "unknown") for s in result.side_effects],
            })

        if not result.success and decision.confidence > 0.7:
            surprises.append({
                "factor": "overconfidence",
                "confidence": decision.confidence,
                "interpretation": "Agent was overconfident — failed despite high confidence.",
            })

        return surprises

    def _recommend_adjustments(
        self,
        decision: ActionDecision,
        result: ExecutionResult,
    ) -> List[Dict[str, Any]]:
        adjustments = []
        if not result.success:
            adjustments.append({
                "adjustment": "reduce_action_priority",
                "action": decision.chosen_action.value,
                "reason": "Action failed — temporarily reduce selection probability.",
                "magnitude": round(self._adaptation_rate, 4),
            })
        if result.reward < -0.3:
            adjustments.append({
                "adjustment": "increase_exploration",
                "reason": "Negative reward suggests poor policy — explore alternatives.",
                "magnitude": round(self._adaptation_rate * 1.5, 4),
            })
        if result.success and result.reward > 0.7:
            adjustments.append({
                "adjustment": "reinforce_strategy",
                "action": decision.chosen_action.value,
                "reason": "High reward — reinforce current policy.",
                "magnitude": round(self._adaptation_rate * 0.5, 4),
            })
        return adjustments

    def _compute_confidence_update(
        self,
        decision: ActionDecision,
        result: ExecutionResult,
    ) -> float:
        expected_success = decision.expected_outcome.get("success_probability", 0.5)
        actual_success = 1.0 if result.success else 0.0
        delta = actual_success - expected_success
        return delta * self._adaptation_rate

    def track_strategy(self, strategy: ExplorationStrategy, reward: float) -> None:
        """Track strategy performance for adaptive strategy selection."""
        self._strategy_performance[strategy].append(reward)
        if len(self._strategy_performance[strategy]) > 100:
            self._strategy_performance[strategy] = self._strategy_performance[strategy][-100:]

    def get_best_strategy(self) -> ExplorationStrategy:
        """Return the best-performing strategy based on tracked history."""
        if not self._strategy_performance:
            return ExplorationStrategy.EPSILON_GREEDY
        best_strategy = ExplorationStrategy.EPSILON_GREEDY
        best_avg = float("-inf")
        for strategy, rewards in self._strategy_performance.items():
            if rewards:
                avg = sum(rewards) / len(rewards)
                if avg > best_avg:
                    best_avg = avg
                    best_strategy = strategy
        return best_strategy


class LearningEngine:
    """
    Updates knowledge and skills based on feedback from the environment.

    Manages the learning rate schedule, exploration rate decay, skill
    acquisition curves, and knowledge representation updates. Implements
    progressive learning with diminishing returns and transfer learning
    capabilities.
    """

    def __init__(self):
        self._learning_rate: float = 0.1
        self._min_learning_rate: float = 0.01
        self._learning_rate_decay: float = 0.9995
        self._exploration_rate: float = 1.0
        self._min_exploration: float = 0.05
        self._exploration_decay: float = 0.998
        self._skill_levels: Dict[str, float] = defaultdict(lambda: 0.0)
        self._knowledge_base: Dict[str, Dict[str, Any]] = {}
        self._learning_curve: List[float] = []
        self._update_count: int = 0

    def learn(
        self,
        reflection: ReflectionEntry,
        execution: ExecutionResult,
    ) -> LearningUpdate:
        """
        Generate a learning update from reflection and execution data.

        Adjusts parameters, updates skills, accumulates knowledge,
        and decays exploration rate based on experience.
        """
        self._update_count += 1

        knowledge = self._accumulate_knowledge(reflection, execution)
        skill_improvements = self._improve_skills(execution)
        params = self._adjust_parameters(execution)
        exploration_change = self._decay_exploration(execution)

        self._learning_curve.append(execution.reward)

        return LearningUpdate(
            knowledge_gained=knowledge,
            skill_improvements=skill_improvements,
            parameter_adjustments=params,
            exploration_rate_change=round(exploration_change, 6),
        )

    def _accumulate_knowledge(
        self,
        reflection: ReflectionEntry,
        execution: ExecutionResult,
    ) -> List[Dict[str, Any]]:
        knowledge = []
        action_key = execution.action.value

        if action_key not in self._knowledge_base:
            self._knowledge_base[action_key] = {
                "attempts": 0,
                "successes": 0,
                "total_reward": 0.0,
                "last_used": time.time(),
            }

        kb = self._knowledge_base[action_key]
        kb["attempts"] += 1
        if execution.success:
            kb["successes"] += 1
        kb["total_reward"] += execution.reward
        kb["last_used"] = time.time()

        success_rate = kb["successes"] / kb["attempts"] if kb["attempts"] > 0 else 0.0
        avg_reward = kb["total_reward"] / kb["attempts"] if kb["attempts"] > 0 else 0.0

        knowledge.append({
            "action": action_key,
            "success_rate": round(success_rate, 4),
            "average_reward": round(avg_reward, 4),
            "total_attempts": kb["attempts"],
        })

        for lesson in reflection.lessons_learned:
            knowledge.append({
                "type": "lesson",
                "content": lesson,
                "source": "reflection",
            })

        return knowledge

    def _improve_skills(self, execution: ExecutionResult) -> List[Dict[str, Any]]:
        improvements = []
        action_key = execution.action.value

        # Skill improvement with diminishing returns
        current = self._skill_levels[action_key]
        if execution.success:
            gain = self._learning_rate * (1.0 - current) * execution.reward
            new_level = min(1.0, current + gain)
        else:
            # Small learning even from failures
            gain = self._learning_rate * 0.1 * (1.0 - current)
            new_level = min(1.0, current + gain)

        self._skill_levels[action_key] = new_level

        improvements.append({
            "skill": action_key,
            "previous_level": round(current, 4),
            "new_level": round(new_level, 4),
            "improvement": round(new_level - current, 6),
        })

        # Transfer learning — related skills get small boost
        related = _get_related_skills(action_key)
        for related_skill in related:
            r_current = self._skill_levels[related_skill]
            transfer_gain = self._learning_rate * 0.05 * (1.0 - r_current)
            if transfer_gain > 0.001:
                self._skill_levels[related_skill] = min(1.0, r_current + transfer_gain)
                improvements.append({
                    "skill": related_skill,
                    "previous_level": round(r_current, 4),
                    "new_level": round(self._skill_levels[related_skill], 4),
                    "improvement": round(transfer_gain, 6),
                    "transfer_from": action_key,
                })

        return improvements

    def _adjust_parameters(self, execution: ExecutionResult) -> Dict[str, float]:
        self._learning_rate = max(
            self._min_learning_rate,
            self._learning_rate * self._learning_rate_decay,
        )
        return {
            "learning_rate": round(self._learning_rate, 6),
            "exploration_rate": round(self._exploration_rate, 6),
            "update_count": self._update_count,
        }

    def _decay_exploration(self, execution: ExecutionResult) -> float:
        previous = self._exploration_rate
        decay = self._exploration_decay
        if execution.success and execution.reward > 0.5:
            decay = self._exploration_decay ** 2  # Faster decay on high-reward success
        if not execution.success:
            decay = self._exploration_decay ** 0.5  # Slower decay on failure
        self._exploration_rate = max(self._min_exploration, self._exploration_rate * decay)
        return previous - self._exploration_rate

    def get_exploration_rate(self) -> float:
        return self._exploration_rate

    def get_skill_level(self, action_type: str) -> float:
        return self._skill_levels.get(action_type, 0.0)

    def get_learning_progress(self) -> Dict[str, Any]:
        return {
            "learning_rate": self._learning_rate,
            "exploration_rate": self._exploration_rate,
            "update_count": self._update_count,
            "skill_levels": dict(self._skill_levels),
            "knowledge_entries": len(self._knowledge_base),
            "recent_rewards": self._learning_curve[-50:],
        }


def _get_related_skills(action_key: str) -> List[str]:
    """Return skill names that are related to the given action (transfer learning)."""
    relations = {
        "move": ["attack", "defend"],
        "attack": ["move", "defend"],
        "defend": ["attack", "move"],
        "collect": ["craft", "interact"],
        "craft": ["collect", "use_item"],
        "interact": ["dialogue", "observe"],
        "dialogue": ["interact", "observe"],
        "use_item": ["craft", "interact"],
    }
    return relations.get(action_key, [])


def _softmax(values: List[float]) -> List[float]:
    """Compute softmax probabilities for a list of values."""
    max_val = max(values) if values else 0.0
    exp_vals = [math.exp(v - max_val) for v in values]
    total = sum(exp_vals)
    if total == 0:
        n = len(values)
        return [1.0 / n] * n
    return [v / total for v in exp_vals]


# ---------------------------------------------------------------------------
# Interaction Loop Engine (Singleton)
# ---------------------------------------------------------------------------


class InteractionLoopEngine:
    """
    Main singleton orchestrating the full perception-action-reflection-learning loop.

    Coordinates the PerceptionProcessor, DecisionEngine, ActionExecutor,
    ReflectionEngine, and LearningEngine to run continuous interaction cycles.
    Manages cycle history, loop state, and performance metrics with thread safety.
    """

    _instance: Optional["InteractionLoopEngine"] = None
    _lock = threading.RLock()

    def __new__(cls) -> "InteractionLoopEngine":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if hasattr(self, "_initialized") and self._initialized:
            return
        self._initialized = True

        self._perception_processor = PerceptionProcessor()
        self._decision_engine = DecisionEngine()
        self._action_executor = ActionExecutor()
        self._reflection_engine = ReflectionEngine()
        self._learning_engine = LearningEngine()

        self._cycle_history: List[InteractionCycle] = []
        self._max_history: int = 1000
        self._loop_state = LoopState()
        self._current_strategy: ExplorationStrategy = ExplorationStrategy.EPSILON_GREEDY
        self._strategy_switch_interval: int = 50
        self._on_cycle_complete: Optional[Callable] = None
        self._on_learning_update: Optional[Callable] = None

    @classmethod
    def get_instance(cls) -> "InteractionLoopEngine":
        return cls()

    # ---- Core Loop Methods ----

    def run_cycle(self, environment_state: Dict[str, Any]) -> InteractionCycle:
        """
        Execute a complete interaction loop cycle.

        Runs through perception, decision, execution, reflection, and
        learning phases, recording timing and data at each step.
        """
        with self._lock:
            cycle = InteractionCycle()
            phase_timings: Dict[str, float] = {}

            # Phase 1: Perception
            t0 = time.time()
            perception = self.process_perception(environment_state)
            phase_timings[LoopPhase.PERCEPTION.value] = time.time() - t0
            cycle.perception_frame = perception

            # Phase 2: Interpretation — built into perception processing
            phase_timings[LoopPhase.INTERPRETATION.value] = 0.0

            # Phase 3: Decision
            t0 = time.time()
            decision = self.decide_action(perception, self._current_strategy)
            phase_timings[LoopPhase.DECISION.value] = time.time() - t0
            cycle.action_decision = decision

            # Phase 4: Action — decision is the action phase
            phase_timings[LoopPhase.ACTION.value] = 0.0

            # Phase 5: Execution
            t0 = time.time()
            execution = self.execute_action(decision, environment_state)
            phase_timings[LoopPhase.EXECUTION.value] = time.time() - t0
            cycle.execution_result = execution

            # Phase 6: Observation — captured in execution result
            phase_timings[LoopPhase.OBSERVATION.value] = 0.0

            # Phase 7: Reflection
            t0 = time.time()
            reflection = self.reflect(cycle)
            phase_timings[LoopPhase.REFLECTION.value] = time.time() - t0
            cycle.reflection = reflection

            # Phase 8: Learning
            t0 = time.time()
            learning = self.learn(reflection, execution)
            phase_timings[LoopPhase.LEARNING.value] = time.time() - t0
            cycle.learning_update = learning

            cycle.phase_timings = phase_timings

            # Update state
            self._update_loop_state(cycle)

            # Store cycle
            self._cycle_history.append(cycle)
            if len(self._cycle_history) > self._max_history:
                self._cycle_history = self._cycle_history[-self._max_history:]

            # Periodic strategy switching
            if self._loop_state.total_cycles % self._strategy_switch_interval == 0:
                self._adapt_strategy()

            if self._on_cycle_complete:
                self._on_cycle_complete(cycle)

            return cycle

    def process_perception(self, raw_data: Dict[str, Any]) -> PerceptionFrame:
        """Process raw environment data into a structured perception frame."""
        return self._perception_processor.process(raw_data)

    def decide_action(
        self,
        perception: PerceptionFrame,
        strategy: Optional[ExplorationStrategy] = None,
    ) -> ActionDecision:
        """Select an action based on current perception and exploration strategy."""
        return self._decision_engine.decide(perception, strategy or self._current_strategy)

    def execute_action(
        self,
        action: ActionDecision,
        context: Dict[str, Any],
    ) -> ExecutionResult:
        """Execute the chosen action in the environment and capture results."""
        return self._action_executor.execute(action, context)

    def reflect(self, cycle: InteractionCycle) -> ReflectionEntry:
        """Analyze a completed cycle and generate a reflection entry."""
        entry = self._reflection_engine.reflect(cycle)
        if cycle.action_decision and cycle.execution_result:
            self._reflection_engine.track_strategy(
                self._current_strategy,
                cycle.execution_result.reward,
            )
        return entry

    def learn(
        self,
        reflection: ReflectionEntry,
        execution: ExecutionResult,
    ) -> LearningUpdate:
        """Update knowledge and skills based on reflection and execution results."""
        update = self._learning_engine.learn(reflection, execution)

        # Update Q-values in the decision engine based on outcome
        if hasattr(execution, "action") and execution.action is not None:
            state_key = "latest"  # Simplified — in practice, state key would be tracked
            self._decision_engine.update_q(
                state_key,
                execution.action,
                execution.reward,
                self._learning_engine._learning_rate,
            )

        if self._on_learning_update:
            self._on_learning_update(update)

        return update

    # ---- State & History ----

    def get_loop_state(self) -> LoopState:
        """Get the current aggregate loop state."""
        with self._lock:
            self._loop_state.exploration_rate = self._learning_engine.get_exploration_rate()
            self._loop_state.learning_progress = self._learning_engine.get_learning_progress()
            self._loop_state.strategy_distribution = self._compute_strategy_distribution()
            return self._loop_state

    def get_cycle_history(self, limit: int = 50) -> List[InteractionCycle]:
        """Get recent cycle history, up to the specified limit."""
        with self._lock:
            return self._cycle_history[-limit:]

    def reset_loop(self) -> None:
        """Reset the loop engine to its initial state."""
        with self._lock:
            self._perception_processor = PerceptionProcessor()
            self._decision_engine = DecisionEngine()
            self._action_executor = ActionExecutor()
            self._reflection_engine = ReflectionEngine()
            self._learning_engine = LearningEngine()
            self._cycle_history = []
            self._loop_state = LoopState()
            self._current_strategy = ExplorationStrategy.EPSILON_GREEDY

    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get comprehensive performance metrics across all cycles."""
        with self._lock:
            cycles = self._cycle_history
            if not cycles:
                return {
                    "total_cycles": 0,
                    "success_rate": 0.0,
                    "average_reward": 0.0,
                    "average_cycle_time": 0.0,
                    "exploration_rate": self._learning_engine.get_exploration_rate(),
                    "learning_rate": self._learning_engine._learning_rate,
                    "current_strategy": self._current_strategy.value,
                    "skill_levels": self._learning_engine.get_learning_progress().get("skill_levels", {}),
                }

            successes = sum(1 for c in cycles if c.was_successful)
            total_reward = sum(
                c.execution_result.reward
                for c in cycles
                if c.execution_result is not None
            )
            total_time = sum(c.total_time for c in cycles)

            recent = cycles[-100:]
            recent_successes = sum(1 for c in recent if c.was_successful)
            recent_rewards = [
                c.execution_result.reward
                for c in recent
                if c.execution_result is not None
            ]

            return {
                "total_cycles": len(cycles),
                "success_rate": round(successes / len(cycles), 4) if cycles else 0.0,
                "average_reward": round(total_reward / len(cycles), 4) if cycles else 0.0,
                "average_cycle_time": round(total_time / len(cycles), 4) if cycles else 0.0,
                "recent_success_rate": round(recent_successes / len(recent), 4) if recent else 0.0,
                "recent_avg_reward": round(sum(recent_rewards) / len(recent_rewards), 4) if recent_rewards else 0.0,
                "exploration_rate": round(self._learning_engine.get_exploration_rate(), 6),
                "learning_rate": round(self._learning_engine._learning_rate, 6),
                "current_strategy": self._current_strategy.value,
                "best_strategy": self._reflection_engine.get_best_strategy().value,
                "skill_levels": self._learning_engine.get_learning_progress().get("skill_levels", {}),
                "performance_curve": self._loop_state.performance_curve[-50:],
            }

    # ---- Internal Methods ----

    def _update_loop_state(self, cycle: InteractionCycle) -> None:
        """Update the aggregate loop state with data from a completed cycle."""
        self._loop_state.total_cycles += 1
        if cycle.execution_result is not None:
            self._loop_state.performance_curve.append(cycle.execution_result.reward)
            if len(self._loop_state.performance_curve) > 500:
                self._loop_state.performance_curve = self._loop_state.performance_curve[-500:]

    def _adapt_strategy(self) -> None:
        """Periodically switch to the best-performing strategy."""
        best = self._reflection_engine.get_best_strategy()
        if best != self._current_strategy:
            self._current_strategy = best

    def _compute_strategy_distribution(self) -> Dict[str, float]:
        """Compute the distribution of strategies used across cycles."""
        perf = self._reflection_engine._strategy_performance
        distribution = {}
        for strategy, rewards in perf.items():
            if rewards:
                distribution[strategy.value] = round(sum(rewards) / len(rewards), 4)
        if not distribution:
            distribution[self._current_strategy.value] = 1.0
        return distribution

    # ---- Configuration ----

    def set_strategy(self, strategy: ExplorationStrategy) -> None:
        """Manually set the exploration strategy."""
        with self._lock:
            self._current_strategy = strategy

    def set_callbacks(
        self,
        on_cycle_complete: Optional[Callable] = None,
        on_learning_update: Optional[Callable] = None,
    ) -> None:
        """Register callbacks for loop events."""
        self._on_cycle_complete = on_cycle_complete
        self._on_learning_update = on_learning_update

    def export_cycle_history(self) -> List[Dict[str, Any]]:
        """Export all cycle history as dictionaries for serialization."""
        with self._lock:
            return [c.to_dict() for c in self._cycle_history]


# ---------------------------------------------------------------------------
# Module-level accessor
# ---------------------------------------------------------------------------


def get_interaction_loop() -> InteractionLoopEngine:
    """Return the singleton InteractionLoopEngine instance."""
    return InteractionLoopEngine.get_instance()