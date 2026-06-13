"""
SparkLabs Agent - Adaptive Cognition System

A unified cognitive architecture that combines metacognition, curiosity-driven
exploration, and reinforcement learning into a single adaptive intelligence
framework. This system enables AI agents to reason about their own reasoning,
explore novel strategies, and improve through experience.

Architecture:
  AdaptiveCognition
    |-- SelfReasoningEngine (introspection, confidence calibration, bias detection)
    |-- CuriosityDriver (novelty seeking, exploration vs exploitation balance)
    |-- ExperienceLearner (reinforcement from outcomes, pattern recognition)
    |-- StrategyOptimizer (multi-armed bandit, policy gradient improvement)
    |-- CognitiveState (attention, focus, mental energy modeling)

Capabilities:
  - Self-reflection and reasoning about own decision processes
  - Curiosity-driven exploration of untested strategies
  - Experience-based learning from successes and failures
  - Strategy optimization through multi-armed bandit selection
  - Cognitive resource management (attention, focus, mental energy)
"""

from __future__ import annotations

import math
import random
import threading
import time
import uuid
from collections import deque
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple


class CognitiveMode(Enum):
    EXPLORE = "explore"
    EXPLOIT = "exploit"
    REFLECT = "reflect"
    LEARN = "learn"
    IDLE = "idle"


class ConfidenceLevel(Enum):
    VERY_LOW = "very_low"
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"
    VERY_HIGH = "very_high"


class ExplorationStrategy(Enum):
    RANDOM = "random"
    UCB = "ucb"
    THOMPSON = "thompson"
    EPSILON_GREEDY = "epsilon_greedy"
    CURIOSITY_DRIVEN = "curiosity_driven"


class LearningOutcome(Enum):
    SUCCESS = "success"
    FAILURE = "failure"
    PARTIAL = "partial"
    UNKNOWN = "unknown"


@dataclass
class CognitiveMetric:
    """A single cognitive metric tracking."""
    name: str
    value: float
    history: List[float] = field(default_factory=list)
    trend: str = "stable"
    threshold_low: float = 0.0
    threshold_high: float = 1.0

    def update(self, new_value: float):
        self.history.append(self.value)
        if len(self.history) > 100:
            self.history = self.history[-100:]
        self.value = max(0.0, min(1.0, new_value))
        if len(self.history) >= 3:
            recent = self.history[-3:]
            if all(recent[i] < recent[i + 1] for i in range(len(recent) - 1)):
                self.trend = "rising"
            elif all(recent[i] > recent[i + 1] for i in range(len(recent) - 1)):
                self.trend = "falling"
            else:
                self.trend = "stable"


@dataclass
class Strategy:
    """A strategy that can be selected and evaluated."""
    strategy_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = ""
    description: str = ""
    times_selected: int = 0
    total_reward: float = 0.0
    avg_reward: float = 0.0
    confidence: float = 0.5
    last_used: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def record_outcome(self, reward: float):
        self.times_selected += 1
        self.total_reward += reward
        self.avg_reward = self.total_reward / self.times_selected
        self.confidence = min(1.0, self.confidence + 0.05 * reward)
        self.last_used = time.time()


@dataclass
class Experience:
    """A recorded experience for learning."""
    experience_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    action: str = ""
    context: Dict[str, Any] = field(default_factory=dict)
    outcome: LearningOutcome = LearningOutcome.UNKNOWN
    reward: float = 0.0
    timestamp: float = field(default_factory=time.time)
    reflection: str = ""
    lessons: List[str] = field(default_factory=list)


@dataclass
class CognitiveState:
    """Current cognitive state of the agent."""
    mode: CognitiveMode = CognitiveMode.IDLE
    attention: float = 1.0
    focus: float = 0.8
    mental_energy: float = 1.0
    confidence: ConfidenceLevel = ConfidenceLevel.MODERATE
    curiosity: float = 0.5
    exploration_rate: float = 0.3
    learning_rate: float = 0.1
    strategy: ExplorationStrategy = ExplorationStrategy.CURIOSITY_DRIVEN


class AgentAdaptiveCognition:
    """
    Unified adaptive cognition system combining metacognition, curiosity,
    and experience learning.
    """

    def __init__(self):
        self._lock = threading.RLock()
        self._strategies: Dict[str, Strategy] = {}
        self._experiences: deque = deque(maxlen=1000)
        self._metrics: Dict[str, CognitiveMetric] = {}
        self._state = CognitiveState()
        self._session_id = uuid.uuid4().hex
        self._total_actions = 0
        self._successful_actions = 0
        self._insights: List[str] = []
        self._initialize_metrics()

    def _initialize_metrics(self):
        self._metrics["exploration"] = CognitiveMetric("exploration", 0.5)
        self._metrics["exploitation"] = CognitiveMetric("exploitation", 0.5)
        self._metrics["learning"] = CognitiveMetric("learning", 0.3)
        self._metrics["creativity"] = CognitiveMetric("creativity", 0.5)
        self._metrics["efficiency"] = CognitiveMetric("efficiency", 0.7)
        self._metrics["adaptability"] = CognitiveMetric("adaptability", 0.5)

    # ---- Strategy Management ----

    def register_strategy(self, name: str, description: str = "",
                          metadata: Dict[str, Any] = None) -> Strategy:
        strategy = Strategy(
            name=name,
            description=description,
            metadata=metadata or {}
        )
        with self._lock:
            self._strategies[strategy.strategy_id] = strategy
        return strategy

    def select_strategy(self, strategy: ExplorationStrategy = None) -> Optional[Strategy]:
        strat = strategy or self._state.strategy
        with self._lock:
            if not self._strategies:
                return None
            strategies = list(self._strategies.values())

            if strat == ExplorationStrategy.RANDOM:
                return random.choice(strategies)
            elif strat == ExplorationStrategy.UCB:
                return self._select_ucb(strategies)
            elif strat == ExplorationStrategy.THOMPSON:
                return self._select_thompson(strategies)
            elif strat == ExplorationStrategy.EPSILON_GREEDY:
                return self._select_epsilon_greedy(strategies)
            elif strat == ExplorationStrategy.CURIOSITY_DRIVEN:
                return self._select_curiosity_driven(strategies)
            return random.choice(strategies)

    def _select_ucb(self, strategies: List[Strategy]) -> Strategy:
        total = sum(s.times_selected for s in strategies) + 1
        best = max(strategies, key=lambda s: (
            s.avg_reward + math.sqrt(2 * math.log(total) / max(1, s.times_selected))
        ))
        return best

    def _select_thompson(self, strategies: List[Strategy]) -> Strategy:
        return max(strategies, key=lambda s: random.betavariate(
            max(1, s.total_reward + 1),
            max(1, s.times_selected - s.total_reward + 1)
        ))

    def _select_epsilon_greedy(self, strategies: List[Strategy]) -> Strategy:
        if random.random() < self._state.exploration_rate:
            return random.choice(strategies)
        return max(strategies, key=lambda s: s.avg_reward)

    def _select_curiosity_driven(self, strategies: List[Strategy]) -> Strategy:
        sorted_by_novelty = sorted(strategies,
                                   key=lambda s: (1 - min(1.0, s.times_selected / 10)) * (1 - s.avg_reward))
        return sorted_by_novelty[0]

    def record_strategy_outcome(self, strategy_id: str, reward: float):
        with self._lock:
            if strategy_id in self._strategies:
                self._strategies[strategy_id].record_outcome(reward)

    # ---- Experience Learning ----

    def record_experience(self, action: str, context: Dict[str, Any],
                          outcome: LearningOutcome, reward: float = 0.0) -> Experience:
        exp = Experience(
            action=action,
            context=context,
            outcome=outcome,
            reward=reward
        )
        with self._lock:
            self._experiences.append(exp)
            self._total_actions += 1
            if outcome == LearningOutcome.SUCCESS:
                self._successful_actions += 1

        self._update_from_experience(exp)
        return exp

    def _update_from_experience(self, exp: Experience):
        if exp.outcome == LearningOutcome.SUCCESS:
            self._metrics["learning"].update(self._metrics["learning"].value + 0.05)
            self._metrics["efficiency"].update(self._metrics["efficiency"].value + 0.02)
        elif exp.outcome == LearningOutcome.FAILURE:
            self._metrics["learning"].update(self._metrics["learning"].value - 0.02)
            self._metrics["exploration"].update(self._metrics["exploration"].value + 0.03)

        self._metrics["adaptability"].update(
            self._metrics["adaptability"].value + 0.01 * exp.reward
        )

    def generate_insights(self) -> List[str]:
        insights = []
        with self._lock:
            recent = list(self._experiences)[-50:]
            if not recent:
                return insights

            success_rate = sum(1 for e in recent if e.outcome == LearningOutcome.SUCCESS) / len(recent)
            if success_rate > 0.8:
                insights.append("High success rate: current strategies are effective")
            elif success_rate < 0.3:
                insights.append("Low success rate: consider exploring new strategies")

            if self._metrics["exploration"].trend == "falling":
                insights.append("Exploration decreasing: may benefit from more variety")
            if self._metrics["creativity"].trend == "rising":
                insights.append("Creativity increasing: novel approaches emerging")

            self._insights.extend(insights)
            return insights

    # ---- Cognitive State ----

    def update_cognitive_state(self, mode: CognitiveMode = None,
                               attention: float = None,
                               focus: float = None,
                               mental_energy: float = None,
                               curiosity: float = None,
                               exploration_rate: float = None,
                               learning_rate: float = None):
        with self._lock:
            if mode is not None:
                self._state.mode = mode
            if attention is not None:
                self._state.attention = max(0.0, min(1.0, attention))
            if focus is not None:
                self._state.focus = max(0.0, min(1.0, focus))
            if mental_energy is not None:
                self._state.mental_energy = max(0.0, min(1.0, mental_energy))
            if curiosity is not None:
                self._state.curiosity = max(0.0, min(1.0, curiosity))
                self._metrics["exploration"].update(curiosity)
            if exploration_rate is not None:
                self._state.exploration_rate = max(0.0, min(1.0, exploration_rate))
            if learning_rate is not None:
                self._state.learning_rate = max(0.0, min(1.0, learning_rate))

            self._state.confidence = self._compute_confidence()

    def _compute_confidence(self) -> ConfidenceLevel:
        success_rate = self._successful_actions / max(1, self._total_actions)
        if success_rate > 0.8:
            return ConfidenceLevel.VERY_HIGH
        elif success_rate > 0.6:
            return ConfidenceLevel.HIGH
        elif success_rate > 0.4:
            return ConfidenceLevel.MODERATE
        elif success_rate > 0.2:
            return ConfidenceLevel.LOW
        return ConfidenceLevel.VERY_LOW

    # ---- Self-Reflection ----

    def reflect(self) -> Dict[str, Any]:
        insights = self.generate_insights()
        with self._lock:
            return {
                "session_id": self._session_id,
                "total_actions": self._total_actions,
                "success_rate": self._successful_actions / max(1, self._total_actions),
                "cognitive_state": {
                    "mode": self._state.mode.value,
                    "attention": self._state.attention,
                    "focus": self._state.focus,
                    "mental_energy": self._state.mental_energy,
                    "confidence": self._state.confidence.value,
                    "curiosity": self._state.curiosity,
                    "exploration_rate": self._state.exploration_rate,
                    "learning_rate": self._state.learning_rate,
                },
                "metrics": {
                    name: {"value": m.value, "trend": m.trend}
                    for name, m in self._metrics.items()
                },
                "insights": insights,
                "strategy_count": len(self._strategies),
                "experience_count": len(self._experiences),
            }

    def get_stats(self) -> Dict[str, Any]:
        return self.reflect()

    def get_cognitive_state(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "mode": self._state.mode.value,
                "attention": self._state.attention,
                "focus": self._state.focus,
                "mental_energy": self._state.mental_energy,
                "confidence": self._state.confidence.value,
                "curiosity": self._state.curiosity,
                "exploration_rate": self._state.exploration_rate,
                "learning_rate": self._state.learning_rate,
            }

    def list_strategies(self) -> List[Dict[str, Any]]:
        with self._lock:
            return [
                {
                    "strategy_id": s.strategy_id,
                    "name": s.name,
                    "times_selected": s.times_selected,
                    "avg_reward": s.avg_reward,
                    "confidence": s.confidence,
                }
                for s in self._strategies.values()
            ]

    def list_experiences(self, limit: int = 50) -> List[Dict[str, Any]]:
        with self._lock:
            return [
                {
                    "experience_id": e.experience_id,
                    "action": e.action,
                    "outcome": e.outcome.value,
                    "reward": e.reward,
                    "timestamp": e.timestamp,
                }
                for e in list(self._experiences)[-limit:]
            ]


# Singleton instance
_adaptive_cognition: Optional[AgentAdaptiveCognition] = None
_cognition_lock = threading.RLock()


def get_adaptive_cognition() -> AgentAdaptiveCognition:
    global _adaptive_cognition
    with _cognition_lock:
        if _adaptive_cognition is None:
            _adaptive_cognition = AgentAdaptiveCognition()
        return _adaptive_cognition