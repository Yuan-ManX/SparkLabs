"""
SparkLabs Agent - Game Progression Engine

Manages difficulty curves, reward pacing, and player journey design
for AI-native game creation. Provides tools to model progression arcs,
balance reward distribution, and validate pacing across game phases.

Architecture:
  GameProgressionEngine
    |-- ProgressionNode (individual progression checkpoint)
    |-- ProgressionCurve (complete progression arc definition)
    |-- DifficultyCurveMapper (curve type-to-parameter mapping)
    |-- PacingValidator (tension/reward rhythm analysis)
    |-- RewardBalancer (reward type distribution optimization)

Progression Phases:
  TUTORIAL -> EARLY -> MID -> LATE -> ENDGAME -> POSTGAME
"""

from __future__ import annotations

import math
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


class ProgressionPhase(Enum):
    TUTORIAL = "tutorial"
    EARLY = "early"
    MID = "mid"
    LATE = "late"
    ENDGAME = "endgame"
    POSTGAME = "postgame"


class DifficultyCurve(Enum):
    LINEAR = "linear"
    EXPONENTIAL = "exponential"
    LOGARITHMIC = "logarithmic"
    WAVE = "wave"
    SPIKE = "spike"
    FLAT = "flat"
    S_CURVE = "s_curve"


class RewardType(Enum):
    XP = "xp"
    CURRENCY = "currency"
    ITEM = "item"
    ABILITY = "ability"
    COSMETIC = "cosmetic"
    STORY_UNLOCK = "story_unlock"
    AREA_UNLOCK = "area_unlock"


@dataclass
class ProgressionNode:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    phase: ProgressionPhase = ProgressionPhase.EARLY
    target_level: int = 1
    difficulty_multiplier: float = 1.0
    reward_type: RewardType = RewardType.XP
    reward_amount: int = 10
    estimated_minutes: float = 5.0
    required_previous: List[str] = field(default_factory=list)
    unlock_conditions: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "phase": self.phase.value,
            "target_level": self.target_level,
            "difficulty_multiplier": self.difficulty_multiplier,
            "reward_type": self.reward_type.value,
            "reward_amount": self.reward_amount,
            "estimated_minutes": self.estimated_minutes,
            "required_previous": self.required_previous,
            "unlock_conditions": self.unlock_conditions,
        }


@dataclass
class ProgressionCurve:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = ""
    curve_type: DifficultyCurve = DifficultyCurve.LINEAR
    nodes: List[ProgressionNode] = field(default_factory=list)
    total_estimated_hours: float = 0.0
    target_audience: str = "general"
    pacing_profile: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "curve_type": self.curve_type.value,
            "node_count": len(self.nodes),
            "total_estimated_hours": self.total_estimated_hours,
            "target_audience": self.target_audience,
            "pacing_profile": self.pacing_profile,
            "nodes": [n.to_dict() for n in self.nodes],
        }


class GameProgressionEngine:
    """
    Game progression engine for AI-native game creation.

    Manages difficulty curves, reward pacing, and player journey
    design. Supports multiple curve types and automatic node generation
    based on progression descriptions.
    """

    _instance: Optional[GameProgressionEngine] = None

    @classmethod
    def get_instance(cls) -> GameProgressionEngine:
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self) -> None:
        self._curves: Dict[str, ProgressionCurve] = {}
        self._nodes: Dict[str, ProgressionNode] = {}
        self._curve_count: int = 0
        self._node_count: int = 0
        self._phase_weights: Dict[ProgressionPhase, float] = {
            ProgressionPhase.TUTORIAL: 0.10,
            ProgressionPhase.EARLY: 0.20,
            ProgressionPhase.MID: 0.30,
            ProgressionPhase.LATE: 0.25,
            ProgressionPhase.ENDGAME: 0.10,
            ProgressionPhase.POSTGAME: 0.05,
        }

    def create_curve(
        self,
        name: str,
        curve_type: str,
        node_count: int = 10,
    ) -> ProgressionCurve:
        ct = DifficultyCurve(curve_type)
        curve = ProgressionCurve(
            name=name,
            curve_type=ct,
        )
        self._curves[curve.id] = curve
        self._curve_count += 1

        phases = self._distribute_phases(node_count)
        level_increment = max(1, node_count // len(phases))

        for i, phase in enumerate(phases):
            level = (i + 1) * level_increment
            multiplier = self._compute_multiplier(i, node_count, ct)
            reward = self._select_reward_for_phase(phase)
            amount = self._compute_reward_amount(level, multiplier, reward)
            minutes = self._estimate_minutes_for_phase(phase, multiplier)

            node = ProgressionNode(
                phase=phase,
                target_level=level,
                difficulty_multiplier=round(multiplier, 2),
                reward_type=reward,
                reward_amount=amount,
                estimated_minutes=round(minutes, 1),
                unlock_conditions={"level": level},
            )
            self._nodes[node.id] = node
            self._node_count += 1
            curve.nodes.append(node)

        curve.total_estimated_hours = round(
            sum(n.estimated_minutes for n in curve.nodes) / 60.0, 1
        )
        curve.pacing_profile = self._build_pacing_profile(curve)
        return curve

    def add_node(
        self,
        curve_id: str,
        phase: str,
        level: int,
        multiplier: float,
        reward_type: str,
        reward_amount: int,
        minutes: float,
    ) -> str:
        curve = self._curves.get(curve_id)
        if not curve:
            return ""

        node = ProgressionNode(
            phase=ProgressionPhase(phase),
            target_level=level,
            difficulty_multiplier=multiplier,
            reward_type=RewardType(reward_type),
            reward_amount=reward_amount,
            estimated_minutes=minutes,
            unlock_conditions={"level": level},
        )
        self._nodes[node.id] = node
        self._node_count += 1
        curve.nodes.append(node)
        curve.total_estimated_hours = round(
            sum(n.estimated_minutes for n in curve.nodes) / 60.0, 1
        )
        curve.pacing_profile = self._build_pacing_profile(curve)
        return node.id

    def remove_node(self, curve_id: str, node_id: str) -> bool:
        curve = self._curves.get(curve_id)
        if not curve:
            return False

        before_count = len(curve.nodes)
        curve.nodes = [n for n in curve.nodes if n.id != node_id]

        if len(curve.nodes) < before_count:
            if node_id in self._nodes:
                del self._nodes[node_id]
            curve.total_estimated_hours = round(
                sum(n.estimated_minutes for n in curve.nodes) / 60.0, 1
            )
            curve.pacing_profile = self._build_pacing_profile(curve)
            return True
        return False

    def calculate_pacing_score(self, curve_id: str) -> float:
        curve = self._curves.get(curve_id)
        if not curve or not curve.nodes:
            return 0.0

        multipliers = [n.difficulty_multiplier for n in curve.nodes]
        minutes = [n.estimated_minutes for n in curve.nodes]

        variance_score = self._compute_variance(multipliers)
        if variance_score == 0:
            return 0.5

        expected = 0.5 + (1.0 - min(variance_score, 1.0)) * 0.5

        time_variance = self._compute_variance(minutes) / max(minutes) if max(minutes) > 0 else 0
        expected *= 0.7 + (1.0 - min(time_variance, 1.0)) * 0.3

        phase_transitions = 0
        for i in range(1, len(curve.nodes)):
            if curve.nodes[i].phase != curve.nodes[i - 1].phase:
                phase_transitions += 1
        expected *= 0.8 + min(phase_transitions / max(len(curve.nodes) - 1, 1), 1.0) * 0.2

        return round(min(1.0, expected), 3)

    def generate_curve_from_description(self, description: str) -> ProgressionCurve:
        desc_lower = description.lower()
        words = set(desc_lower.split())

        if "casual" in words or "easy" in words:
            curve_type = DifficultyCurve.LINEAR
            node_count = 5
            audience = "casual"
        elif "hard" in words or "brutal" in words:
            curve_type = DifficultyCurve.SPIKE
            node_count = 8
            audience = "hardcore"
        elif "story" in words or "narrative" in words:
            curve_type = DifficultyCurve.WAVE
            node_count = 12
            audience = "story"
        elif "rpg" in words or "long" in words:
            curve_type = DifficultyCurve.S_CURVE
            node_count = 15
            audience = "rpg"
        elif "competitive" in words or "pvp" in words:
            curve_type = DifficultyCurve.EXPONENTIAL
            node_count = 10
            audience = "competitive"
        else:
            curve_type = DifficultyCurve.LINEAR
            node_count = 8
            audience = "general"

        name_words = [w.capitalize() for w in description.split()[:4]]
        name = " ".join(name_words) if name_words else "Auto Curve"

        return self.create_curve(name, curve_type.value, node_count)

    def get_curve(self, curve_id: str) -> Optional[Dict[str, Any]]:
        curve = self._curves.get(curve_id)
        if curve:
            return curve.to_dict()
        return None

    def list_curves(
        self, curve_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        curves = list(self._curves.values())
        if curve_type:
            ct = DifficultyCurve(curve_type)
            curves = [c for c in curves if c.curve_type == ct]
        return [c.to_dict() for c in curves]

    def _distribute_phases(self, node_count: int) -> List[ProgressionPhase]:
        phases: List[ProgressionPhase] = []
        for phase, weight in self._phase_weights.items():
            count = max(1, round(node_count * weight))
            phases.extend([phase] * count)

        while len(phases) < node_count:
            phases.insert(-1, ProgressionPhase.MID)
        return phases[:node_count]

    def _compute_multiplier(
        self, index: int, total: int, curve_type: DifficultyCurve
    ) -> float:
        progress = index / max(total - 1, 1)

        if curve_type == DifficultyCurve.LINEAR:
            return round(0.5 + progress * 1.5, 2)
        elif curve_type == DifficultyCurve.EXPONENTIAL:
            return round(0.5 + (progress ** 2) * 2.5, 2)
        elif curve_type == DifficultyCurve.LOGARITHMIC:
            return round(0.5 + math.log(1 + progress * 9) * 1.0, 2)
        elif curve_type == DifficultyCurve.WAVE:
            wave = math.sin(progress * math.pi * 2) * 0.5 + 0.5
            return round(0.5 + wave * 1.5, 2)
        elif curve_type == DifficultyCurve.SPIKE:
            if progress < 0.7:
                return round(0.5 + progress * 0.5, 2)
            return round(0.85 + (progress - 0.7) / 0.3 * 1.65, 2)
        elif curve_type == DifficultyCurve.FLAT:
            return 1.0
        elif curve_type == DifficultyCurve.S_CURVE:
            sigmoid = 1.0 / (1.0 + math.exp(-10 * (progress - 0.5)))
            return round(0.5 + sigmoid * 2.0, 2)
        return 1.0

    def _select_reward_for_phase(self, phase: ProgressionPhase) -> RewardType:
        mapping: Dict[ProgressionPhase, List[RewardType]] = {
            ProgressionPhase.TUTORIAL: [RewardType.XP, RewardType.CURRENCY],
            ProgressionPhase.EARLY: [RewardType.XP, RewardType.CURRENCY, RewardType.ITEM],
            ProgressionPhase.MID: [RewardType.ITEM, RewardType.ABILITY, RewardType.CURRENCY],
            ProgressionPhase.LATE: [RewardType.ABILITY, RewardType.COSMETIC, RewardType.STORY_UNLOCK],
            ProgressionPhase.ENDGAME: [RewardType.COSMETIC, RewardType.AREA_UNLOCK, RewardType.STORY_UNLOCK],
            ProgressionPhase.POSTGAME: [RewardType.COSMETIC, RewardType.AREA_UNLOCK],
        }
        options = mapping.get(phase, [RewardType.XP])
        return options[hash(phase.value) % len(options)]

    def _compute_reward_amount(
        self, level: int, multiplier: float, reward_type: RewardType
    ) -> int:
        base = 10
        if reward_type == RewardType.XP:
            base = 100
        elif reward_type == RewardType.CURRENCY:
            base = 50
        elif reward_type == RewardType.ITEM:
            base = 1
        elif reward_type == RewardType.ABILITY:
            base = 1
        elif reward_type == RewardType.COSMETIC:
            base = 1
        elif reward_type == RewardType.STORY_UNLOCK:
            base = 1
        elif reward_type == RewardType.AREA_UNLOCK:
            base = 1
        return max(1, int(base * level * multiplier))

    def _estimate_minutes_for_phase(
        self, phase: ProgressionPhase, multiplier: float
    ) -> float:
        base_minutes: Dict[ProgressionPhase, float] = {
            ProgressionPhase.TUTORIAL: 3.0,
            ProgressionPhase.EARLY: 5.0,
            ProgressionPhase.MID: 8.0,
            ProgressionPhase.LATE: 12.0,
            ProgressionPhase.ENDGAME: 15.0,
            ProgressionPhase.POSTGAME: 10.0,
        }
        return round(base_minutes.get(phase, 5.0) * multiplier, 1)

    def _compute_variance(self, values: List[float]) -> float:
        if not values:
            return 0.0
        mean = sum(values) / len(values)
        return sum((v - mean) ** 2 for v in values) / len(values)

    def _build_pacing_profile(self, curve: ProgressionCurve) -> Dict[str, Any]:
        if not curve.nodes:
            return {}

        phase_order = [
            ProgressionPhase.TUTORIAL,
            ProgressionPhase.EARLY,
            ProgressionPhase.MID,
            ProgressionPhase.LATE,
            ProgressionPhase.ENDGAME,
            ProgressionPhase.POSTGAME,
        ]

        phase_minutes: Dict[str, float] = {}
        phase_rewards: Dict[str, List[str]] = {}

        for node in curve.nodes:
            pv = node.phase.value
            phase_minutes[pv] = phase_minutes.get(pv, 0) + node.estimated_minutes
            if pv not in phase_rewards:
                phase_rewards[pv] = []
            phase_rewards[pv].append(node.reward_type.value)

        avg_multiplier = (
            sum(n.difficulty_multiplier for n in curve.nodes) / len(curve.nodes)
            if curve.nodes else 0
        )

        return {
            "phase_distribution": {
                p.value: phase_minutes.get(p.value, 0) for p in phase_order
            },
            "reward_distribution": {
                pv: {
                    "total": len(rewards),
                    "types": list(set(rewards)),
                }
                for pv, rewards in phase_rewards.items()
            },
            "average_multiplier": round(avg_multiplier, 2),
            "pacing_score": self.calculate_pacing_score(curve.id),
            "total_nodes": len(curve.nodes),
            "total_estimated_hours": curve.total_estimated_hours,
        }

    def get_stats(self) -> Dict[str, Any]:
        curve_types: Dict[str, int] = {}
        for c in self._curves.values():
            curve_types[c.curve_type.value] = curve_types.get(c.curve_type.value, 0) + 1

        phase_counts: Dict[str, int] = {}
        for n in self._nodes.values():
            phase_counts[n.phase.value] = phase_counts.get(n.phase.value, 0) + 1

        return {
            "total_curves": self._curve_count,
            "total_nodes": self._node_count,
            "by_curve_type": curve_types,
            "by_phase": phase_counts,
            "available_phases": [p.value for p in ProgressionPhase],
            "available_curves": [c.value for c in DifficultyCurve],
            "available_rewards": [r.value for r in RewardType],
            "avg_nodes_per_curve": (
                self._node_count / self._curve_count if self._curve_count > 0 else 0
            ),
        }


def get_game_progression() -> GameProgressionEngine:
    return GameProgressionEngine.get_instance()