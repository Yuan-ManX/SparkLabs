"""
Agent World Model - Predictive internal world model for AI agents.
Enables agents to simulate and predict outcomes of their actions
before execution, supporting look-ahead planning and reasoning.
"""

import threading
import uuid
import time as _time_module
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Tuple, Any, Callable


class SimulationMode(Enum):
    """Modes for world simulation."""
    DETERMINISTIC = "deterministic"
    PROBABILISTIC = "probabilistic"
    MONTE_CARLO = "monte_carlo"
    HEURISTIC = "heuristic"


class PredictionConfidence(Enum):
    """Confidence levels for predictions."""
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    UNKNOWN = "unknown"


@dataclass
class WorldEntity:
    """An entity in the agent's world model."""
    entity_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    entity_type: str = ""
    position: Tuple[float, float] = (0.0, 0.0)
    properties: Dict[str, Any] = field(default_factory=dict)
    last_observed: float = field(default_factory=_time_module.time)
    confidence: float = 1.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "entity_id": self.entity_id,
            "entity_type": self.entity_type,
            "position": list(self.position),
            "properties": self.properties,
            "last_observed": self.last_observed,
            "confidence": self.confidence,
        }


@dataclass
class WorldStateSnapshot:
    """Snapshot of the world model at a point in time."""
    snapshot_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    entities: Dict[str, WorldEntity] = field(default_factory=dict)
    global_state: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=_time_module.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "snapshot_id": self.snapshot_id,
            "entities": {k: v.to_dict() for k, v in self.entities.items()},
            "global_state": self.global_state,
            "timestamp": self.timestamp,
        }


@dataclass
class Prediction:
    """A prediction about future world state."""
    prediction_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    action_name: str = ""
    expected_outcome: Dict[str, Any] = field(default_factory=dict)
    confidence: PredictionConfidence = PredictionConfidence.MEDIUM
    probability: float = 0.5
    side_effects: List[Dict[str, Any]] = field(default_factory=list)
    reasoning: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "prediction_id": self.prediction_id,
            "action_name": self.action_name,
            "expected_outcome": self.expected_outcome,
            "confidence": self.confidence.value,
            "probability": self.probability,
            "side_effects": self.side_effects,
            "reasoning": self.reasoning,
        }


@dataclass
class SimulationResult:
    """Result of a world simulation."""
    result_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    initial_state: Dict[str, Any] = field(default_factory=dict)
    final_state: Dict[str, Any] = field(default_factory=dict)
    action_sequence: List[str] = field(default_factory=list)
    success: bool = False
    reward: float = 0.0
    steps: int = 0
    mode: SimulationMode = SimulationMode.DETERMINISTIC

    def to_dict(self) -> Dict[str, Any]:
        return {
            "result_id": self.result_id,
            "initial_state": self.initial_state,
            "final_state": self.final_state,
            "action_sequence": self.action_sequence,
            "success": self.success,
            "reward": self.reward,
            "steps": self.steps,
            "mode": self.mode.value,
        }


class AgentWorldModel:
    """
    Internal world model for AI agents to predict and simulate outcomes.
    Supports look-ahead planning, counterfactual reasoning, and
    probabilistic simulation of game world dynamics.
    """

    _instance = None
    _lock = threading.RLock()
    _initialized = False

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if not self._initialized:
            self._agents: Dict[str, WorldStateSnapshot] = {}
            self._transition_rules: Dict[str, Callable] = {}
            self._prediction_cache: Dict[str, List[Prediction]] = {}
            self._simulation_history: Dict[str, List[SimulationResult]] = {}
            self._observations: Dict[str, List[Dict[str, Any]]] = {}
            self._initialized = True

    @classmethod
    def get_instance(cls) -> 'AgentWorldModel':
        return cls()

    def initialize_agent_world(self, agent_id: str, initial_state: Dict[str, Any] = None):
        """Initialize a world model for an agent."""
        snapshot = WorldStateSnapshot(global_state=initial_state or {})
        self._agents[agent_id] = snapshot
        self._observations[agent_id] = []
        self._simulation_history[agent_id] = []

    def observe_entity(self, agent_id: str, entity: WorldEntity):
        """Register an observation of a world entity."""
        snapshot = self._agents.get(agent_id)
        if not snapshot:
            self.initialize_agent_world(agent_id)
            snapshot = self._agents[agent_id]

        snapshot.entities[entity.entity_id] = entity
        self._observations.setdefault(agent_id, []).append({
            "entity_id": entity.entity_id,
            "entity_type": entity.entity_type,
            "position": entity.position,
            "timestamp": _time_module.time(),
        })

    def update_global_state(self, agent_id: str, state_update: Dict[str, Any]):
        """Update the global state in the agent's world model."""
        snapshot = self._agents.get(agent_id)
        if not snapshot:
            self.initialize_agent_world(agent_id, state_update)
            return
        snapshot.global_state.update(state_update)
        snapshot.timestamp = _time_module.time()

    def register_transition(self, action_name: str, transition_fn: Callable[[Dict[str, Any], Dict[str, Any]], Dict[str, Any]]):
        """Register a state transition function for an action."""
        self._transition_rules[action_name] = transition_fn

    def predict_outcome(self, agent_id: str, action_name: str,
                        action_params: Dict[str, Any] = None) -> Prediction:
        """Predict the outcome of an action in the current world state."""
        snapshot = self._agents.get(agent_id)
        if not snapshot:
            return Prediction(
                action_name=action_name,
                confidence=PredictionConfidence.UNKNOWN,
                probability=0.0,
                reasoning="No world model initialized",
            )

        transition = self._transition_rules.get(action_name)
        if transition:
            try:
                result = transition(snapshot.global_state, action_params or {})
                confidence = PredictionConfidence.HIGH
                probability = 0.9
            except Exception:
                result = {}
                confidence = PredictionConfidence.LOW
                probability = 0.3
        else:
            result = self._heuristic_prediction(snapshot, action_name, action_params or {})
            confidence = PredictionConfidence.MEDIUM
            probability = 0.5

        prediction = Prediction(
            action_name=action_name,
            expected_outcome=result,
            confidence=confidence,
            probability=probability,
            reasoning=f"Predicted outcome for {action_name} with {confidence.value} confidence",
        )

        self._prediction_cache.setdefault(agent_id, []).append(prediction)
        return prediction

    def _heuristic_prediction(self, snapshot: WorldStateSnapshot,
                              action_name: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Generate a heuristic prediction when no transition rule exists."""
        outcome: Dict[str, Any] = {"action": action_name, "predicted_changes": {}}

        if "move" in action_name.lower():
            outcome["predicted_changes"]["position_changed"] = True
        elif "attack" in action_name.lower():
            outcome["predicted_changes"]["damage_dealt"] = True
        elif "collect" in action_name.lower() or "pickup" in action_name.lower():
            outcome["predicted_changes"]["inventory_changed"] = True
        elif "talk" in action_name.lower() or "dialogue" in action_name.lower():
            outcome["predicted_changes"]["dialogue_started"] = True

        return outcome

    def simulate_sequence(self, agent_id: str, actions: List[Tuple[str, Dict[str, Any]]],
                          mode: SimulationMode = SimulationMode.DETERMINISTIC) -> SimulationResult:
        """Simulate a sequence of actions in the world model."""
        snapshot = self._agents.get(agent_id)
        if not snapshot:
            return SimulationResult(success=False)

        current_state = dict(snapshot.global_state)
        initial_state = dict(current_state)
        action_names = []
        total_reward = 0.0

        for action_name, params in actions:
            action_names.append(action_name)
            transition = self._transition_rules.get(action_name)

            if transition:
                current_state = transition(current_state, params)
            else:
                current_state = self._apply_heuristic(current_state, action_name, params)

            total_reward += self._calculate_reward(current_state, action_name)

        result = SimulationResult(
            initial_state=initial_state,
            final_state=current_state,
            action_sequence=action_names,
            success=True,
            reward=total_reward,
            steps=len(actions),
            mode=mode,
        )

        self._simulation_history.setdefault(agent_id, []).append(result)
        return result

    def _apply_heuristic(self, state: Dict[str, Any], action_name: str,
                         params: Dict[str, Any]) -> Dict[str, Any]:
        """Apply a heuristic state transition."""
        new_state = dict(state)
        new_state["last_action"] = action_name
        new_state["action_params"] = params
        return new_state

    def _calculate_reward(self, state: Dict[str, Any], action_name: str) -> float:
        """Calculate reward for a state transition."""
        reward = 0.0
        if "goal_progress" in state:
            reward += state["goal_progress"] * 0.5
        if "damage_received" in state:
            reward -= state["damage_received"] * 0.3
        if "items_collected" in state:
            reward += state["items_collected"] * 0.2
        return reward

    def compare_predictions(self, agent_id: str, action_name: str,
                            prediction: Prediction, actual_outcome: Dict[str, Any]) -> float:
        """Compare a prediction with actual outcome and return accuracy score."""
        if not prediction.expected_outcome:
            return 0.0

        expected = prediction.expected_outcome
        matches = 0
        total = 0

        for key, expected_val in expected.items():
            total += 1
            if key in actual_outcome and actual_outcome[key] == expected_val:
                matches += 1

        accuracy = matches / max(1, total)
        return accuracy

    def get_agent_world(self, agent_id: str) -> Optional[WorldStateSnapshot]:
        """Get the current world model for an agent."""
        return self._agents.get(agent_id)

    def get_predictions(self, agent_id: str, limit: int = 20) -> List[Prediction]:
        """Get recent predictions for an agent."""
        predictions = self._prediction_cache.get(agent_id, [])
        return predictions[-limit:]

    def get_simulation_history(self, agent_id: str, limit: int = 10) -> List[SimulationResult]:
        """Get simulation history for an agent."""
        history = self._simulation_history.get(agent_id, [])
        return history[-limit:]

    def get_stats(self) -> Dict[str, Any]:
        """Get world model system statistics."""
        return {
            "total_agents": len(self._agents),
            "total_transitions": len(self._transition_rules),
            "total_predictions": sum(len(p) for p in self._prediction_cache.values()),
            "total_simulations": sum(len(s) for s in self._simulation_history.values()),
            "total_observations": sum(len(o) for o in self._observations.values()),
        }


def get_world_model() -> AgentWorldModel:
    return AgentWorldModel.get_instance()