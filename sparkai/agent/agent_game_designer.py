"""
SparkLabs Agent - Game Designer Engine

AI system that generates game mechanics, designs levels, computes
balance profiles, and constructs core gameplay loops. The engine
provides systematic tools for creating and tuning game elements
across multiple mechanic types, difficulty tiers, and balance
dimensions. It supports analytical balance checking, encounter
generation, and automated tuning suggestions.

Architecture:
  GameDesignerEngine (Singleton)
    |-- GameMechanic (movement, combat, puzzle, resource, etc.)
    |-- LevelDesign (theme, difficulty, spawn points, objectives)
    |-- BalanceProfile (metric scaling with tier modifiers)
    |-- GameLoop (phases, transitions, trigger conditions)

Core Capabilities:
  - Create game mechanics with typed parameters and balance weights
  - Design levels with difficulty tiers, spawn points, and objectives
  - Build balance profiles with scaling factors and tier modifiers
  - Construct game loops with phase transitions and reward structures
  - Analyze balance across mechanics for fairness and viability
  - Suggest tuning adjustments based on balance analysis
  - Generate encounters by combining mechanics, levels, and balance
"""

from __future__ import annotations

import math
import threading
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class MechanicType(Enum):
    """Categories of game mechanics."""
    MOVEMENT = "movement"
    COMBAT = "combat"
    PUZZLE = "puzzle"
    RESOURCE = "resource"
    SOCIAL = "social"
    STEALTH = "stealth"
    CRAFTING = "crafting"


class DifficultyTier(Enum):
    """Standard difficulty levels for game content."""
    TRIVIAL = "trivial"
    EASY = "easy"
    NORMAL = "normal"
    HARD = "hard"
    EXPERT = "expert"
    NIGHTMARE = "nightmare"


class BalanceMetric(Enum):
    """Metrics used for game balance calculations."""
    DAMAGE = "damage"
    HEALTH = "health"
    SPEED = "speed"
    RANGE = "range"
    COOLDOWN = "cooldown"
    COST = "cost"


class GamePillar(Enum):
    """Core design pillars that define gameplay focus."""
    EXPLORATION = "exploration"
    COMBAT = "combat"
    NARRATIVE = "narrative"
    PROGRESSION = "progression"
    SOCIAL = "social"


# ---------------------------------------------------------------------------
# Tier Multipliers
# ---------------------------------------------------------------------------

_TIER_MULTIPLIERS: Dict[DifficultyTier, float] = {
    DifficultyTier.TRIVIAL: 0.3,
    DifficultyTier.EASY: 0.6,
    DifficultyTier.NORMAL: 1.0,
    DifficultyTier.HARD: 1.5,
    DifficultyTier.EXPERT: 2.2,
    DifficultyTier.NIGHTMARE: 3.0,
}


# ---------------------------------------------------------------------------
# Data Classes
# ---------------------------------------------------------------------------

@dataclass
class GameMechanic:
    """A defined game mechanic with typed parameters and balance weights.

    Mechanics represent discrete gameplay systems such as movement
    abilities, combat actions, puzzle elements, resource management
    rules, social interactions, stealth behaviors, or crafting recipes.
    """
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = ""
    mechanic_type: MechanicType = MechanicType.COMBAT
    description: str = ""
    parameters: Dict[str, Any] = field(default_factory=dict)
    prerequisites: List[str] = field(default_factory=list)
    unlocks: List[str] = field(default_factory=list)
    balance_weights: Dict[str, float] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "mechanic_type": self.mechanic_type.value,
            "description": self.description[:200],
            "parameters": self.parameters,
            "prerequisites": self.prerequisites,
            "unlocks": self.unlocks,
            "balance_weights": self.balance_weights,
            "metadata": self.metadata,
            "created_at": self.created_at,
        }

    def get_balance_weight(self, metric: str) -> float:
        return self.balance_weights.get(metric, 0.0)

    def set_balance_weight(self, metric: str, weight: float) -> None:
        self.balance_weights[metric] = max(0.0, min(1.0, weight))

    def has_prerequisite(self, mechanic_id: str) -> bool:
        return mechanic_id in self.prerequisites

    def unlocks_mechanic(self, mechanic_id: str) -> bool:
        return mechanic_id in self.unlocks


@dataclass
class LevelDesign:
    """A level design blueprint with layout, spawn points, and objectives.

    Levels are defined by their theme, difficulty tier, the mechanics
    they exercise, spawn point configurations, objective lists, and
    layout data for spatial arrangement.
    """
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = ""
    theme: str = ""
    difficulty: DifficultyTier = DifficultyTier.NORMAL
    mechanics: List[str] = field(default_factory=list)
    spawn_points: List[Dict[str, Any]] = field(default_factory=list)
    objectives: List[Dict[str, Any]] = field(default_factory=list)
    layout_data: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "theme": self.theme,
            "difficulty": self.difficulty.value,
            "difficulty_multiplier": _TIER_MULTIPLIERS.get(self.difficulty, 1.0),
            "mechanic_count": len(self.mechanics),
            "mechanics": self.mechanics,
            "spawn_points": self.spawn_points,
            "spawn_point_count": len(self.spawn_points),
            "objectives": self.objectives,
            "objective_count": len(self.objectives),
            "layout_data": self.layout_data,
            "metadata": self.metadata,
            "created_at": self.created_at,
        }

    def add_spawn_point(self, entity_type: str, position: Dict[str, float], properties: Optional[Dict[str, Any]] = None) -> None:
        self.spawn_points.append({
            "entity_type": entity_type,
            "position": position,
            "properties": properties or {},
        })

    def add_objective(self, description: str, objective_type: str = "primary", is_optional: bool = False) -> None:
        self.objectives.append({
            "description": description,
            "objective_type": objective_type,
            "is_optional": is_optional,
        })

    def get_difficulty_multiplier(self) -> float:
        return _TIER_MULTIPLIERS.get(self.difficulty, 1.0)


@dataclass
class BalanceProfile:
    """A balance profile defining how a metric scales across difficulty.

    Each profile targets a specific balance metric and defines its
    base value, scaling factor, allowed range, and per-tier modifiers
    for fine-grained difficulty tuning.
    """
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    target_metric: BalanceMetric = BalanceMetric.DAMAGE
    base_value: float = 1.0
    scaling_factor: float = 1.0
    min_value: float = 0.0
    max_value: float = 100.0
    tier_modifiers: Dict[str, float] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "target_metric": self.target_metric.value,
            "base_value": self.base_value,
            "scaling_factor": self.scaling_factor,
            "min_value": self.min_value,
            "max_value": self.max_value,
            "tier_modifiers": self.tier_modifiers,
            "metadata": self.metadata,
            "created_at": self.created_at,
        }

    def compute_for_tier(self, tier: DifficultyTier) -> float:
        tier_mult = _TIER_MULTIPLIERS.get(tier, 1.0)
        tier_mod = self.tier_modifiers.get(tier.value, 0.0)
        value = self.base_value * (self.scaling_factor * tier_mult + tier_mod)
        return max(self.min_value, min(self.max_value, value))

    def compute_for_all_tiers(self) -> Dict[str, float]:
        result: Dict[str, float] = {}
        for tier in DifficultyTier:
            result[tier.value] = self.compute_for_tier(tier)
        return result

    def is_within_bounds(self, value: float) -> bool:
        return self.min_value <= value <= self.max_value


@dataclass
class GameLoop:
    """A core gameplay loop with phases, transitions, and rewards.

    The game loop defines the cyclical structure of gameplay: phases
    that players progress through, conditions that trigger transitions
    between phases, and rewards granted for completing each phase.
    """
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = ""
    phases: List[Dict[str, Any]] = field(default_factory=list)
    trigger_conditions: Dict[str, Any] = field(default_factory=dict)
    transitions: List[Dict[str, Any]] = field(default_factory=list)
    rewards: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "phases": self.phases,
            "phase_count": len(self.phases),
            "trigger_conditions": self.trigger_conditions,
            "transitions": self.transitions,
            "transition_count": len(self.transitions),
            "rewards": self.rewards,
            "metadata": self.metadata,
            "created_at": self.created_at,
        }

    def add_phase(self, name: str, description: str = "", duration_seconds: float = 0.0) -> None:
        self.phases.append({
            "name": name,
            "description": description,
            "duration_seconds": duration_seconds,
            "order": len(self.phases),
        })

    def add_transition(self, from_phase: str, to_phase: str, condition: str = "") -> None:
        self.transitions.append({
            "from_phase": from_phase,
            "to_phase": to_phase,
            "condition": condition,
        })

    def set_reward(self, phase_name: str, reward_type: str, amount: float) -> None:
        if phase_name not in self.rewards:
            self.rewards[phase_name] = []
        self.rewards[phase_name].append({
            "reward_type": reward_type,
            "amount": amount,
        })

    def get_phase_order(self) -> List[str]:
        sorted_phases = sorted(self.phases, key=lambda p: p["order"])
        return [p["name"] for p in sorted_phases]


# ---------------------------------------------------------------------------
# GameDesignerEngine
# ---------------------------------------------------------------------------

class GameDesignerEngine:
    """Thread-safe singleton engine for game design and balancing.

    Provides systematic generation of mechanics, levels, balance
    profiles, and gameplay loops. Supports analytical balance checking,
    automated tuning suggestions, and encounter generation by combining
    mechanics with level designs and balance profiles.
    """

    _instance: Optional["GameDesignerEngine"] = None
    _lock = threading.RLock()

    _MAX_MECHANICS: int = 1000
    _MAX_LEVELS: int = 500
    _MAX_BALANCE_PROFILES: int = 1000
    _MAX_GAME_LOOPS: int = 200
    _BALANCE_THRESHOLD: float = 0.15

    def __init__(self) -> None:
        self._mechanics: Dict[str, GameMechanic] = {}
        self._mechanics_by_type: Dict[str, List[str]] = {}
        self._levels: Dict[str, LevelDesign] = {}
        self._balance_profiles: Dict[str, BalanceProfile] = {}
        self._game_loops: Dict[str, GameLoop] = {}
        self._total_mechanics_created: int = 0
        self._total_levels_created: int = 0
        self._total_balance_profiles_created: int = 0
        self._total_game_loops_created: int = 0
        self._total_balance_analyses: int = 0
        self._total_encounters_generated: int = 0

    @classmethod
    def get_instance(cls) -> "GameDesignerEngine":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    # ------------------------------------------------------------------
    # Mechanics
    # ------------------------------------------------------------------

    def create_mechanic(
        self,
        name: str = "",
        mechanic_type: MechanicType = MechanicType.COMBAT,
        description: str = "",
        parameters: Optional[Dict[str, Any]] = None,
        prerequisites: Optional[List[str]] = None,
        unlocks: Optional[List[str]] = None,
        balance_weights: Optional[Dict[str, float]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> GameMechanic:
        with self._lock:
            self._enforce_max_mechanics()

            mechanic = GameMechanic(
                name=name or f"Mechanic {self._total_mechanics_created + 1}",
                mechanic_type=mechanic_type,
                description=description,
                parameters=parameters or {},
                prerequisites=list(prerequisites) if prerequisites else [],
                unlocks=list(unlocks) if unlocks else [],
                balance_weights=balance_weights or {},
                metadata=metadata or {},
            )
            self._mechanics[mechanic.id] = mechanic
            self._index_mechanic(mechanic)
            self._total_mechanics_created += 1
            return mechanic

    def get_mechanic(self, mechanic_id: str) -> Optional[GameMechanic]:
        with self._lock:
            return self._mechanics.get(mechanic_id)

    def list_mechanics(
        self,
        mechanic_type: Optional[MechanicType] = None,
    ) -> List[Dict[str, Any]]:
        with self._lock:
            if mechanic_type is not None:
                ids = self._mechanics_by_type.get(mechanic_type.value, [])
                return [self._mechanics[mid].to_dict() for mid in ids if mid in self._mechanics]
            return [m.to_dict() for m in self._mechanics.values()]

    def get_mechanics_by_type(self, mechanic_type: MechanicType) -> List[GameMechanic]:
        with self._lock:
            ids = self._mechanics_by_type.get(mechanic_type.value, [])
            return [self._mechanics[mid] for mid in ids if mid in self._mechanics]

    # ------------------------------------------------------------------
    # Levels
    # ------------------------------------------------------------------

    def create_level(
        self,
        name: str = "",
        theme: str = "",
        difficulty: DifficultyTier = DifficultyTier.NORMAL,
        mechanics: Optional[List[str]] = None,
        spawn_points: Optional[List[Dict[str, Any]]] = None,
        objectives: Optional[List[Dict[str, Any]]] = None,
        layout_data: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> LevelDesign:
        with self._lock:
            self._enforce_max_levels()

            level = LevelDesign(
                name=name or f"Level {self._total_levels_created + 1}",
                theme=theme,
                difficulty=difficulty,
                mechanics=list(mechanics) if mechanics else [],
                spawn_points=list(spawn_points) if spawn_points else [],
                objectives=list(objectives) if objectives else [],
                layout_data=layout_data or {},
                metadata=metadata or {},
            )
            self._levels[level.id] = level
            self._total_levels_created += 1
            return level

    def get_level(self, level_id: str) -> Optional[LevelDesign]:
        with self._lock:
            return self._levels.get(level_id)

    def list_levels(self, difficulty: Optional[DifficultyTier] = None) -> List[Dict[str, Any]]:
        with self._lock:
            results = list(self._levels.values())
            if difficulty is not None:
                results = [l for l in results if l.difficulty == difficulty]
            return [l.to_dict() for l in results]

    # ------------------------------------------------------------------
    # Balance Profiles
    # ------------------------------------------------------------------

    def create_balance_profile(
        self,
        target_metric: BalanceMetric = BalanceMetric.DAMAGE,
        base_value: float = 1.0,
        scaling_factor: float = 1.0,
        min_value: float = 0.0,
        max_value: float = 100.0,
        tier_modifiers: Optional[Dict[str, float]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> BalanceProfile:
        with self._lock:
            self._enforce_max_balance_profiles()

            profile = BalanceProfile(
                target_metric=target_metric,
                base_value=base_value,
                scaling_factor=scaling_factor,
                min_value=min_value,
                max_value=max_value,
                tier_modifiers=tier_modifiers or {},
                metadata=metadata or {},
            )
            self._balance_profiles[profile.id] = profile
            self._total_balance_profiles_created += 1
            return profile

    def get_balance_profile(self, profile_id: str) -> Optional[BalanceProfile]:
        with self._lock:
            return self._balance_profiles.get(profile_id)

    def list_balance_profiles(self) -> List[Dict[str, Any]]:
        with self._lock:
            return [p.to_dict() for p in self._balance_profiles.values()]

    # ------------------------------------------------------------------
    # Game Loops
    # ------------------------------------------------------------------

    def create_game_loop(
        self,
        name: str = "",
        phases: Optional[List[Dict[str, Any]]] = None,
        trigger_conditions: Optional[Dict[str, Any]] = None,
        transitions: Optional[List[Dict[str, Any]]] = None,
        rewards: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> GameLoop:
        with self._lock:
            self._enforce_max_game_loops()

            loop = GameLoop(
                name=name or f"Game Loop {self._total_game_loops_created + 1}",
                phases=list(phases) if phases else [],
                trigger_conditions=trigger_conditions or {},
                transitions=list(transitions) if transitions else [],
                rewards=rewards or {},
                metadata=metadata or {},
            )
            self._game_loops[loop.id] = loop
            self._total_game_loops_created += 1
            return loop

    def get_game_loop(self, loop_id: str) -> Optional[GameLoop]:
        with self._lock:
            return self._game_loops.get(loop_id)

    def list_game_loops(self) -> List[Dict[str, Any]]:
        with self._lock:
            return [l.to_dict() for l in self._game_loops.values()]

    # ------------------------------------------------------------------
    # Balance Analysis
    # ------------------------------------------------------------------

    def analyze_balance(
        self,
        mechanic_ids: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        with self._lock:
            self._total_balance_analyses += 1

            if mechanic_ids is not None:
                target_mechanics = [
                    self._mechanics[mid]
                    for mid in mechanic_ids
                    if mid in self._mechanics
                ]
            else:
                target_mechanics = list(self._mechanics.values())

            if not target_mechanics:
                return {"error": "No mechanics to analyze", "verdict": "inconclusive"}

            metric_weights: Dict[str, List[float]] = {}
            for mechanic in target_mechanics:
                for metric, weight in mechanic.balance_weights.items():
                    if metric not in metric_weights:
                        metric_weights[metric] = []
                    metric_weights[metric].append(weight)

            metric_stats: Dict[str, Dict[str, float]] = {}
            for metric, weights in metric_weights.items():
                if not weights:
                    continue
                avg = sum(weights) / len(weights)
                variance = sum((w - avg) ** 2 for w in weights) / len(weights)
                metric_stats[metric] = {
                    "mean": round(avg, 4),
                    "variance": round(variance, 4),
                    "std_dev": round(math.sqrt(variance), 4),
                    "min": round(min(weights), 4),
                    "max": round(max(weights), 4),
                    "is_balanced": variance < self._BALANCE_THRESHOLD,
                }

            all_balanced = all(
                s["is_balanced"] for s in metric_stats.values()
            ) if metric_stats else True

            total_weight_sum = 0.0
            for mechanic in target_mechanics:
                total_weight_sum += sum(mechanic.balance_weights.values())

            avg_total_weight = total_weight_sum / len(target_mechanics) if target_mechanics else 0.0

            return {
                "mechanic_count": len(target_mechanics),
                "metric_stats": metric_stats,
                "all_balanced": all_balanced,
                "verdict": "balanced" if all_balanced else "needs_tuning",
                "avg_total_weight": round(avg_total_weight, 4),
                "balance_threshold": self._BALANCE_THRESHOLD,
            }

    def suggest_tuning(
        self,
        mechanic_ids: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        with self._lock:
            analysis = self.analyze_balance(mechanic_ids)
            if "error" in analysis:
                return analysis

            suggestions: List[Dict[str, Any]] = []
            metric_stats = analysis.get("metric_stats", {})

            for metric, stats in metric_stats.items():
                if stats["is_balanced"]:
                    continue

                mean = stats["mean"]
                std_dev = stats["std_dev"]

                if mechanic_ids is not None:
                    target_mechanics = [
                        self._mechanics[mid]
                        for mid in mechanic_ids
                        if mid in self._mechanics
                    ]
                else:
                    target_mechanics = list(self._mechanics.values())

                for mechanic in target_mechanics:
                    weight = mechanic.balance_weights.get(metric, 0.0)
                    if abs(weight - mean) > std_dev:
                        direction = "increase" if weight < mean else "decrease"
                        delta = mean - weight
                        suggestions.append({
                            "mechanic_id": mechanic.id,
                            "mechanic_name": mechanic.name,
                            "metric": metric,
                            "current_weight": round(weight, 4),
                            "target_weight": round(mean, 4),
                            "delta": round(delta, 4),
                            "suggestion": f"{direction.capitalize()} {metric} by {abs(delta):.4f}",
                        })

            suggestions.sort(key=lambda s: abs(s["delta"]), reverse=True)

            return {
                "analysis": analysis,
                "suggestion_count": len(suggestions),
                "suggestions": suggestions[:20],
            }

    # ------------------------------------------------------------------
    # Encounter Generation
    # ------------------------------------------------------------------

    def generate_encounter(
        self,
        level_id: str,
        mechanic_ids: Optional[List[str]] = None,
        encounter_type: str = "combat",
    ) -> Dict[str, Any]:
        with self._lock:
            self._total_encounters_generated += 1

            level = self._levels.get(level_id)
            if level is None:
                return {"error": "Level not found"}

            if mechanic_ids is not None:
                encounter_mechanics = [
                    self._mechanics[mid]
                    for mid in mechanic_ids
                    if mid in self._mechanics
                ]
            else:
                encounter_mechanics = [
                    self._mechanics[mid]
                    for mid in level.mechanics
                    if mid in self._mechanics
                ]

            if not encounter_mechanics:
                encounter_mechanics = [
                    m for m in self._mechanics.values()
                    if m.mechanic_type.value == encounter_type
                ][:3]

            tier_mult = level.get_difficulty_multiplier()
            encounter_params: Dict[str, Any] = {}

            for mechanic in encounter_mechanics:
                scaled_params = {}
                for param, value in mechanic.parameters.items():
                    if isinstance(value, (int, float)):
                        scaled_params[param] = round(value * tier_mult, 2)
                    else:
                        scaled_params[param] = value
                encounter_params[mechanic.name] = scaled_params

            relevant_spawns = [
                sp for sp in level.spawn_points
                if sp.get("entity_type", "") in [
                    m.mechanic_type.value for m in encounter_mechanics
                ]
            ]
            if not relevant_spawns:
                relevant_spawns = level.spawn_points[:3] if level.spawn_points else []

            return {
                "encounter_id": uuid.uuid4().hex,
                "level_id": level_id,
                "level_name": level.name,
                "difficulty": level.difficulty.value,
                "difficulty_multiplier": tier_mult,
                "encounter_type": encounter_type,
                "mechanics": [m.to_dict() for m in encounter_mechanics],
                "mechanic_count": len(encounter_mechanics),
                "encounter_params": encounter_params,
                "spawn_points": relevant_spawns,
                "objectives": level.objectives[:3],
                "generated_at": time.time(),
            }

    # ------------------------------------------------------------------
    # Statistics
    # ------------------------------------------------------------------

    def get_stats(self) -> Dict[str, Any]:
        with self._lock:
            mechanic_type_dist: Dict[str, int] = {}
            for mechanic in self._mechanics.values():
                mt = mechanic.mechanic_type.value
                mechanic_type_dist[mt] = mechanic_type_dist.get(mt, 0) + 1

            difficulty_dist: Dict[str, int] = {}
            for level in self._levels.values():
                d = level.difficulty.value
                difficulty_dist[d] = difficulty_dist.get(d, 0) + 1

            metric_dist: Dict[str, int] = {}
            for profile in self._balance_profiles.values():
                m = profile.target_metric.value
                metric_dist[m] = metric_dist.get(m, 0) + 1

            return {
                "total_mechanics_created": self._total_mechanics_created,
                "total_mechanics_stored": len(self._mechanics),
                "total_levels_created": self._total_levels_created,
                "total_levels_stored": len(self._levels),
                "total_balance_profiles_created": self._total_balance_profiles_created,
                "total_balance_profiles_stored": len(self._balance_profiles),
                "total_game_loops_created": self._total_game_loops_created,
                "total_game_loops_stored": len(self._game_loops),
                "total_balance_analyses": self._total_balance_analyses,
                "total_encounters_generated": self._total_encounters_generated,
                "mechanic_type_distribution": mechanic_type_dist,
                "difficulty_distribution": difficulty_dist,
                "metric_distribution": metric_dist,
                "max_mechanics": self._MAX_MECHANICS,
                "max_levels": self._MAX_LEVELS,
                "balance_threshold": self._BALANCE_THRESHOLD,
            }

    def reset(self) -> None:
        with self._lock:
            self._mechanics.clear()
            self._mechanics_by_type.clear()
            self._levels.clear()
            self._balance_profiles.clear()
            self._game_loops.clear()
            self._total_mechanics_created = 0
            self._total_levels_created = 0
            self._total_balance_profiles_created = 0
            self._total_game_loops_created = 0
            self._total_balance_analyses = 0
            self._total_encounters_generated = 0

    # ------------------------------------------------------------------
    # Internal Helpers
    # ------------------------------------------------------------------

    def _index_mechanic(self, mechanic: GameMechanic) -> None:
        key = mechanic.mechanic_type.value
        if key not in self._mechanics_by_type:
            self._mechanics_by_type[key] = []
        if mechanic.id not in self._mechanics_by_type[key]:
            self._mechanics_by_type[key].append(mechanic.id)

    def _enforce_max_mechanics(self) -> None:
        if len(self._mechanics) >= self._MAX_MECHANICS:
            sorted_mechanics = sorted(
                self._mechanics.items(),
                key=lambda item: item[1].created_at,
            )
            overflow = len(self._mechanics) - self._MAX_MECHANICS + 1
            for mid, mechanic in sorted_mechanics[:overflow]:
                self._mechanics.pop(mid, None)
                key = mechanic.mechanic_type.value
                if key in self._mechanics_by_type and mid in self._mechanics_by_type[key]:
                    self._mechanics_by_type[key].remove(mid)

    def _enforce_max_levels(self) -> None:
        if len(self._levels) >= self._MAX_LEVELS:
            sorted_levels = sorted(
                self._levels.items(),
                key=lambda item: item[1].created_at,
            )
            overflow = len(self._levels) - self._MAX_LEVELS + 1
            for lid, _ in sorted_levels[:overflow]:
                self._levels.pop(lid, None)

    def _enforce_max_balance_profiles(self) -> None:
        if len(self._balance_profiles) >= self._MAX_BALANCE_PROFILES:
            sorted_profiles = sorted(
                self._balance_profiles.items(),
                key=lambda item: item[1].created_at,
            )
            overflow = len(self._balance_profiles) - self._MAX_BALANCE_PROFILES + 1
            for pid, _ in sorted_profiles[:overflow]:
                self._balance_profiles.pop(pid, None)

    def _enforce_max_game_loops(self) -> None:
        if len(self._game_loops) >= self._MAX_GAME_LOOPS:
            sorted_loops = sorted(
                self._game_loops.items(),
                key=lambda item: item[1].created_at,
            )
            overflow = len(self._game_loops) - self._MAX_GAME_LOOPS + 1
            for lid, _ in sorted_loops[:overflow]:
                self._game_loops.pop(lid, None)


# ---------------------------------------------------------------------------
# Module-level accessor
# ---------------------------------------------------------------------------

def get_game_designer() -> GameDesignerEngine:
    """Return the singleton GameDesignerEngine instance."""
    return GameDesignerEngine.get_instance()