"""
SparkLabs Engine - Procedural Gameplay Generation

An AI-driven procedural gameplay generation system that dynamically
creates game mechanics, events, challenges, and interactions based on
design intent and player behavior for the AI-native game engine.

Architecture:
  ProceduralGameplayEngine (Singleton)
    |-- MechanicType          — classification of generated gameplay elements
    |-- DifficultyTier        — scaling from trivial to impossible challenges
    |-- GenerationStyle       — style bias for generation algorithms
    |-- GameplayMechanic      — atomic gameplay unit with parameters and rules
    |-- GameplayEvent         — time-bound composition of multiple mechanics
    |-- GameplaySession       — state container for a generation run
"""

from __future__ import annotations

import json
import math
import random
import threading
import time
import uuid
from collections import deque
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class MechanicType(Enum):
    """Classification of procedurally generated gameplay elements."""
    CHALLENGE = "challenge"
    PUZZLE = "puzzle"
    ENCOUNTER = "encounter"
    EVENT = "event"
    REWARD = "reward"
    OBSTACLE = "obstacle"
    BOSS = "boss"
    COLLECTIBLE = "collectible"


class DifficultyTier(Enum):
    """Difficulty scaling for generated gameplay content."""
    TRIVIAL = "trivial"
    EASY = "easy"
    NORMAL = "normal"
    HARD = "hard"
    EXTREME = "extreme"
    IMPOSSIBLE = "impossible"

    @property
    def numeric_value(self) -> int:
        """Map difficulty tier to a numeric scale for calculations."""
        _map = {
            DifficultyTier.TRIVIAL: 1,
            DifficultyTier.EASY: 2,
            DifficultyTier.NORMAL: 3,
            DifficultyTier.HARD: 4,
            DifficultyTier.EXTREME: 5,
            DifficultyTier.IMPOSSIBLE: 6,
        }
        return _map[self]

    @classmethod
    def from_numeric(cls, value: float) -> "DifficultyTier":
        """Convert a numeric value back to the closest difficulty tier."""
        tiers = list(cls)
        idx = max(0, min(len(tiers) - 1, int(round(value)) - 1))
        return tiers[idx]


class GenerationStyle(Enum):
    """Stylistic bias for procedural generation algorithms."""
    BALANCED = "balanced"
    AGGRESSIVE = "aggressive"
    DEFENSIVE = "defensive"
    EXPLORATORY = "exploratory"
    NARRATIVE = "narrative"
    CHAOTIC = "chaotic"


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------

@dataclass
class GameplayMechanic:
    """An atomic procedurally generated gameplay unit.

    Represents a single gameplay element such as a challenge, puzzle,
    encounter, or reward. Contains parameterized rules, difficulty
    modifiers, and reward definitions that the engine can evaluate
    at runtime.
    """
    mechanic_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    type: MechanicType = MechanicType.CHALLENGE
    difficulty: DifficultyTier = DifficultyTier.NORMAL
    style: GenerationStyle = GenerationStyle.BALANCED
    name: str = ""
    description: str = ""
    parameters: Dict[str, Any] = field(default_factory=dict)
    rules: Dict[str, Any] = field(default_factory=dict)
    rewards: Dict[str, Any] = field(default_factory=dict)
    tags: List[str] = field(default_factory=list)
    seed: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "mechanic_id": self.mechanic_id,
            "type": self.type.value,
            "difficulty": self.difficulty.value,
            "style": self.style.value,
            "name": self.name,
            "description": self.description,
            "parameters": self.parameters,
            "rules": self.rules,
            "rewards": self.rewards,
            "tags": self.tags,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "GameplayMechanic":
        return cls(
            mechanic_id=data.get("mechanic_id", uuid.uuid4().hex),
            type=MechanicType(data.get("type", "challenge")),
            difficulty=DifficultyTier(data.get("difficulty", "normal")),
            style=GenerationStyle(data.get("style", "balanced")),
            name=data.get("name", ""),
            description=data.get("description", ""),
            parameters=data.get("parameters", {}),
            rules=data.get("rules", {}),
            rewards=data.get("rewards", {}),
            tags=data.get("tags", []),
            seed=data.get("seed", 0),
        )


@dataclass
class GameplayEvent:
    """A time-bound composition of gameplay mechanics.

    Events bundle multiple mechanics together with trigger conditions,
    duration constraints, cooldown periods, and priority ordering.
    The engine evaluates trigger conditions each frame and activates
    the event when conditions are met.
    """
    event_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    trigger_condition: Dict[str, Any] = field(default_factory=dict)
    mechanics: List[GameplayMechanic] = field(default_factory=list)
    duration: float = 30.0
    cooldown: float = 0.0
    priority: int = 0
    name: str = ""
    description: str = ""
    style: GenerationStyle = GenerationStyle.BALANCED
    seed: int = 0
    last_triggered: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": self.event_id,
            "trigger_condition": self.trigger_condition,
            "mechanics": [m.to_dict() for m in self.mechanics],
            "duration": self.duration,
            "cooldown": self.cooldown,
            "priority": self.priority,
            "name": self.name,
            "description": self.description,
            "style": self.style.value,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "GameplayEvent":
        return cls(
            event_id=data.get("event_id", uuid.uuid4().hex),
            trigger_condition=data.get("trigger_condition", {}),
            mechanics=[GameplayMechanic.from_dict(m) for m in data.get("mechanics", [])],
            duration=data.get("duration", 30.0),
            cooldown=data.get("cooldown", 0.0),
            priority=data.get("priority", 0),
            name=data.get("name", ""),
            description=data.get("description", ""),
            style=GenerationStyle(data.get("style", "balanced")),
            seed=data.get("seed", 0),
        )


@dataclass
class GameplaySession:
    """State container for a procedural gameplay generation run.

    Tracks all active mechanics and events within a session, along
    with the generation style, target difficulty, player context,
    and a reproducible random seed.
    """
    session_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    style: GenerationStyle = GenerationStyle.BALANCED
    difficulty: DifficultyTier = DifficultyTier.NORMAL
    active_mechanics: List[GameplayMechanic] = field(default_factory=list)
    active_events: List[GameplayEvent] = field(default_factory=list)
    player_level: int = 1
    seed: int = 0
    total_mechanics_generated: int = 0
    total_events_generated: int = 0
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "session_id": self.session_id,
            "style": self.style.value,
            "difficulty": self.difficulty.value,
            "active_mechanics": [m.to_dict() for m in self.active_mechanics],
            "active_events": [e.to_dict() for e in self.active_events],
            "player_level": self.player_level,
            "seed": self.seed,
            "total_mechanics_generated": self.total_mechanics_generated,
            "total_events_generated": self.total_events_generated,
            "created_at": self.created_at,
        }


# ---------------------------------------------------------------------------
# Procedural Generation Data
# ---------------------------------------------------------------------------

# Name components for generating descriptive mechanic names
_MECHANIC_PREFIXES: Dict[MechanicType, List[str]] = {
    MechanicType.CHALLENGE: ["Time", "Speed", "Precision", "Endurance", "Reflex",
                              "Accuracy", "Survival", "Gauntlet", "Trial", "Proving"],
    MechanicType.PUZZLE: ["Logic", "Pattern", "Sequence", "Riddle", "Cipher",
                           "Maze", "Lock", "Code", "Symbol", "Grid"],
    MechanicType.ENCOUNTER: ["Ambush", "Patrol", "Scout", "Raider", "Wanderer",
                              "Guardian", "Sentinel", "Marauder", "Stalker", "Hunter"],
    MechanicType.EVENT: ["Storm", "Eclipse", "Quake", "Surge", "Shift",
                          "Bloom", "Convergence", "Anomaly", "Rift", "Tide"],
    MechanicType.REWARD: ["Cache", "Trove", "Vault", "Hoard", "Stash",
                           "Bounty", "Spoils", "Chest", "Relic", "Artifact"],
    MechanicType.OBSTACLE: ["Barrier", "Wall", "Gap", "Pit", "Thorns",
                             "Spikes", "Chasm", "Blockade", "Fissure", "Bramble"],
    MechanicType.BOSS: ["Overlord", "Titan", "Colossus", "Dread", "Tyrant",
                         "Leviathan", "Warden", "Sovereign", "Ancient", "Behemoth"],
    MechanicType.COLLECTIBLE: ["Shard", "Orb", "Gem", "Token", "Fragment",
                                "Essence", "Crystal", "Ember", "Seed", "Core"],
}

_MECHANIC_SUFFIXES: Dict[MechanicType, List[str]] = {
    MechanicType.CHALLENGE: ["Run", "Test", "Dash", "Clash", "Rush",
                              "Trial", "Bout", "Race", "Fight", "March"],
    MechanicType.PUZZLE: ["Puzzle", "Enigma", "Mystery", "Conundrum", "Secret",
                           "Problem", "Trick", "Twist", "Game", "Test"],
    MechanicType.ENCOUNTER: ["Pack", "Squad", "Horde", "Band", "Group",
                              "Cluster", "Swarm", "Troop", "Unit", "Force"],
    MechanicType.EVENT: ["Event", "Occurrence", "Phase", "Wave", "Pulse",
                          "Burst", "Cycle", "Period", "Season", "Epoch"],
    MechanicType.REWARD: ["Drop", "Prize", "Gift", "Loot", "Find",
                           "Haul", "Score", "Take", "Yield", "Gain"],
    MechanicType.OBSTACLE: ["Block", "Wall", "Trap", "Snare", "Gate",
                             "Hurdle", "Fence", "Stop", "Jam", "Cork"],
    MechanicType.BOSS: ["Fight", "Battle", "Duel", "Showdown", "Clash",
                         "War", "Siege", "Brawl", "Struggle", "Conflict"],
    MechanicType.COLLECTIBLE: ["Pickup", "Find", "Grab", "Item", "Token",
                                "Unit", "Piece", "Bit", "Drop", "Loot"],
}

# Difficulty scaling factors for parameter generation
_DIFFICULTY_SCALE: Dict[DifficultyTier, Dict[str, float]] = {
    DifficultyTier.TRIVIAL:    {"health": 0.4, "damage": 0.3, "speed": 0.6, "count": 1.0, "reward": 0.5},
    DifficultyTier.EASY:       {"health": 0.7, "damage": 0.6, "speed": 0.8, "count": 1.5, "reward": 0.7},
    DifficultyTier.NORMAL:     {"health": 1.0, "damage": 1.0, "speed": 1.0, "count": 2.0, "reward": 1.0},
    DifficultyTier.HARD:       {"health": 1.5, "damage": 1.6, "speed": 1.2, "count": 3.0, "reward": 1.5},
    DifficultyTier.EXTREME:    {"health": 2.5, "damage": 2.5, "speed": 1.4, "count": 5.0, "reward": 2.5},
    DifficultyTier.IMPOSSIBLE: {"health": 4.0, "damage": 4.0, "speed": 1.6, "count": 8.0, "reward": 4.0},
}

# Style modifiers that bias generation parameters
_STYLE_MODIFIERS: Dict[GenerationStyle, Dict[str, float]] = {
    GenerationStyle.BALANCED:     {"health": 1.0, "damage": 1.0, "count": 1.0, "variance": 0.15},
    GenerationStyle.AGGRESSIVE:   {"health": 0.8, "damage": 1.5, "count": 1.3, "variance": 0.25},
    GenerationStyle.DEFENSIVE:    {"health": 1.6, "damage": 0.6, "count": 0.8, "variance": 0.10},
    GenerationStyle.EXPLORATORY:  {"health": 0.9, "damage": 0.9, "count": 1.5, "variance": 0.30},
    GenerationStyle.NARRATIVE:    {"health": 1.1, "damage": 1.1, "count": 0.7, "variance": 0.12},
    GenerationStyle.CHAOTIC:      {"health": 1.3, "damage": 1.3, "count": 2.0, "variance": 0.50},
}

# Performance thresholds for difficulty adaptation
_PERFORMANCE_THRESHOLDS: List[Tuple[float, int]] = [
    (0.95, +3),   # Near-perfect -> increase difficulty significantly
    (0.85, +2),   # Excellent -> increase difficulty
    (0.75, +1),   # Good -> slight increase
    (0.55,  0),   # Average -> maintain
    (0.40, -1),   # Below average -> slight decrease
    (0.25, -2),   # Poor -> decrease
    (0.00, -3),   # Very poor -> decrease significantly
]


# ---------------------------------------------------------------------------
# ProceduralGameplayEngine (Singleton)
# ---------------------------------------------------------------------------

class ProceduralGameplayEngine:
    """AI-driven procedural gameplay generation engine.

    Dynamically creates game mechanics, events, encounters, and
    challenges based on design intent, player context, and style
    parameters. Uses seeded randomization for reproducible generation
    and adapts difficulty based on player performance metrics.

    Usage:
        pg = get_procedural_gameplay()
        session = pg.create_session(GenerationStyle.BALANCED,
            DifficultyTier.NORMAL, player_level=5, seed=42)
        mechanic = pg.generate_mechanic(session.session_id,
            MechanicType.CHALLENGE)
        event = pg.generate_event(session.session_id,
            {"type": "timer", "interval": 60.0}, mechanic_count=3)
        result = pg.evaluate_challenge(mechanic.mechanic_id,
            {"attack": 50, "defense": 30, "speed": 40})
        new_diff = pg.adapt_difficulty(session.session_id,
            {"win_rate": 0.85, "time_per_encounter": 45.0})
    """

    _instance: Optional["ProceduralGameplayEngine"] = None
    _lock: threading.RLock = threading.RLock()

    # ------------------------------------------------------------------
    # Singleton
    # ------------------------------------------------------------------

    def __new__(cls) -> "ProceduralGameplayEngine":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if getattr(self, "_initialized", False):
            return
        self._initialized: bool = True
        self._sessions: Dict[str, GameplaySession] = {}
        self._mechanics: Dict[str, GameplayMechanic] = {}
        self._events: Dict[str, GameplayEvent] = {}
        self._total_generated: int = 0
        self._total_sessions: int = 0
        self._generation_history: deque = deque(maxlen=200)

    # ------------------------------------------------------------------
    # Session Management
    # ------------------------------------------------------------------

    def create_session(
        self,
        style: GenerationStyle,
        difficulty: DifficultyTier,
        player_level: int = 1,
        seed: int = 0,
    ) -> GameplaySession:
        """Create a new gameplay generation session.

        Args:
            style: The generation style bias to apply.
            difficulty: The target difficulty tier for generated content.
            player_level: The current player level for scaling.
            seed: Random seed for reproducible generation (0 = random).

        Returns:
            A new GameplaySession ready for content generation.
        """
        actual_seed = seed if seed != 0 else random.randint(1, 2**31 - 1)
        session = GameplaySession(
            style=style,
            difficulty=difficulty,
            player_level=player_level,
            seed=actual_seed,
        )
        with self._lock:
            self._sessions[session.session_id] = session
            self._total_sessions += 1
        return session

    def get_session(self, session_id: str) -> Optional[GameplaySession]:
        """Retrieve a session by its identifier."""
        with self._lock:
            return self._sessions.get(session_id)

    def delete_session(self, session_id: str) -> bool:
        """Remove a session and its associated content."""
        with self._lock:
            if session_id not in self._sessions:
                return False
            session = self._sessions[session_id]
            for m in session.active_mechanics:
                self._mechanics.pop(m.mechanic_id, None)
            for e in session.active_events:
                self._events.pop(e.event_id, None)
            del self._sessions[session_id]
            return True

    def list_sessions(self) -> List[Dict[str, Any]]:
        """List all active sessions with summary information."""
        with self._lock:
            return [
                {
                    "session_id": s.session_id,
                    "style": s.style.value,
                    "difficulty": s.difficulty.value,
                    "player_level": s.player_level,
                    "mechanic_count": len(s.active_mechanics),
                    "event_count": len(s.active_events),
                    "created_at": s.created_at,
                }
                for s in self._sessions.values()
            ]

    # ------------------------------------------------------------------
    # Mechanic Generation
    # ------------------------------------------------------------------

    def _make_rng(self, session: GameplaySession, offset: int = 0) -> random.Random:
        """Create a seeded random number generator for a session."""
        return random.Random(str(session.seed) + str(session.total_mechanics_generated + offset))

    def _generate_mechanic_name(
        self, rng: random.Random, mechanic_type: MechanicType
    ) -> str:
        """Generate a descriptive name for a mechanic."""
        prefixes = _MECHANIC_PREFIXES.get(mechanic_type, ["Unknown"])
        suffixes = _MECHANIC_SUFFIXES.get(mechanic_type, ["Thing"])
        prefix = rng.choice(prefixes)
        suffix = rng.choice(suffixes)
        return f"{prefix} {suffix}"

    def _generate_mechanic_parameters(
        self,
        rng: random.Random,
        mechanic_type: MechanicType,
        difficulty: DifficultyTier,
        style: GenerationStyle,
        player_level: int,
    ) -> Dict[str, Any]:
        """Generate parameter values for a mechanic based on type, difficulty, and style."""
        diff_scale = _DIFFICULTY_SCALE.get(difficulty, _DIFFICULTY_SCALE[DifficultyTier.NORMAL])
        style_mod = _STYLE_MODIFIERS.get(style, _STYLE_MODIFIERS[GenerationStyle.BALANCED])
        level_mod = 1.0 + (player_level - 1) * 0.1

        base_params: Dict[str, Any] = {}

        if mechanic_type == MechanicType.CHALLENGE:
            base_params["health"] = round(100.0 * diff_scale["health"] * style_mod["health"] * level_mod, 1)
            base_params["damage"] = round(20.0 * diff_scale["damage"] * style_mod["damage"] * level_mod, 1)
            base_params["time_limit"] = round(90.0 / diff_scale["speed"] * level_mod, 1)
            base_params["score_target"] = round(100.0 * diff_scale["count"], 1)
            base_params["failure_penalty"] = round(10.0 * diff_scale["damage"], 1)

        elif mechanic_type == MechanicType.PUZZLE:
            base_params["complexity"] = round(3.0 * diff_scale["count"], 1)
            base_params["time_limit"] = round(120.0 / diff_scale["speed"] * level_mod, 1)
            base_params["hints_available"] = max(0, int(5 - diff_scale["count"]))
            base_params["steps_required"] = int(3 * diff_scale["count"])
            base_params["failure_cost"] = round(5.0 * diff_scale["damage"], 1)

        elif mechanic_type == MechanicType.ENCOUNTER:
            base_params["enemy_count"] = max(1, int(diff_scale["count"] * style_mod["count"]))
            base_params["enemy_health"] = round(80.0 * diff_scale["health"] * style_mod["health"] * level_mod, 1)
            base_params["enemy_damage"] = round(15.0 * diff_scale["damage"] * style_mod["damage"] * level_mod, 1)
            base_params["aggro_range"] = round(100.0 + 20.0 * diff_scale["count"], 1)
            base_params["reinforcement_chance"] = round(min(0.5, 0.1 * diff_scale["count"]), 2)

        elif mechanic_type == MechanicType.EVENT:
            base_params["duration"] = round(30.0 * diff_scale["speed"], 1)
            base_params["intensity"] = round(diff_scale["damage"], 2)
            base_params["area_radius"] = round(200.0 * diff_scale["count"], 1)
            base_params["effect_strength"] = round(diff_scale["damage"] * style_mod["damage"], 2)
            base_params["recurrence"] = rng.choice(["once", "periodic", "triggered"])

        elif mechanic_type == MechanicType.REWARD:
            base_params["value"] = round(50.0 * diff_scale["reward"] * level_mod, 1)
            base_params["rarity"] = rng.choice(["common", "uncommon", "rare", "epic"])
            base_params["quantity"] = max(1, int(diff_scale["count"] * 2))
            base_params["drop_chance"] = round(1.0 / diff_scale["count"], 3)
            base_params["bonus_modifier"] = round(1.0 + 0.2 * diff_scale["reward"], 2)

        elif mechanic_type == MechanicType.OBSTACLE:
            base_params["height"] = round(40.0 * diff_scale["health"], 1)
            base_params["width"] = round(60.0 * diff_scale["count"], 1)
            base_params["speed"] = round(10.0 * diff_scale["speed"], 1)
            base_params["damage_on_contact"] = round(25.0 * diff_scale["damage"], 1)
            base_params["is_moving"] = rng.choice([True, False])

        elif mechanic_type == MechanicType.BOSS:
            base_params["health"] = round(500.0 * diff_scale["health"] * style_mod["health"] * level_mod, 1)
            base_params["damage"] = round(50.0 * diff_scale["damage"] * style_mod["damage"] * level_mod, 1)
            base_params["phase_count"] = max(1, int(diff_scale["count"]))
            base_params["minion_spawn_rate"] = round(0.2 * diff_scale["count"], 2)
            base_params["enrage_threshold"] = round(0.3 - 0.05 * diff_scale["count"], 2)

        elif mechanic_type == MechanicType.COLLECTIBLE:
            base_params["value"] = round(10.0 * diff_scale["reward"], 1)
            base_params["spawn_count"] = max(1, int(diff_scale["count"] * 3))
            base_params["respawn_time"] = round(30.0 / diff_scale["speed"], 1)
            base_params["collection_radius"] = round(20.0, 1)
            base_params["effect_duration"] = round(15.0 * diff_scale["reward"], 1)

        # Apply style variance
        for key in base_params:
            if isinstance(base_params[key], (int, float)) and not isinstance(base_params[key], bool):
                variance = style_mod.get("variance", 0.15)
                base_params[key] = round(
                    base_params[key] * (1.0 + rng.uniform(-variance, variance)), 2
                )

        # Apply integer rounding for count-like parameters
        int_keys = {"enemy_count", "phase_count", "spawn_count", "steps_required",
                    "quantity", "hints_available"}
        for key in int_keys:
            if key in base_params:
                base_params[key] = max(1, int(round(base_params[key])))

        return base_params

    def _generate_mechanic_rules(
        self,
        rng: random.Random,
        mechanic_type: MechanicType,
        difficulty: DifficultyTier,
    ) -> Dict[str, Any]:
        """Generate rule definitions that govern mechanic behavior."""
        rules: Dict[str, Any] = {
            "can_retry": difficulty != DifficultyTier.IMPOSSIBLE,
            "fail_on_timeout": True,
            "scales_with_player": True,
        }

        if mechanic_type == MechanicType.CHALLENGE:
            rules.update({
                "completion_criteria": rng.choice(["score", "survival", "time", "accuracy"]),
                "scoring_mode": rng.choice(["cumulative", "threshold", "comparative"]),
                "retry_penalty": round(0.1 * difficulty.numeric_value, 2),
                "grace_period": round(3.0 / difficulty.numeric_value, 1),
            })

        elif mechanic_type == MechanicType.PUZZLE:
            rules.update({
                "reset_on_failure": rng.choice([True, False]),
                "sequential_steps": rng.choice([True, False]),
                "partial_credit": rng.random() > 0.5,
                "max_attempts": max(1, 10 - difficulty.numeric_value),
            })

        elif mechanic_type == MechanicType.ENCOUNTER:
            rules.update({
                "aggro_type": rng.choice(["proximity", "line_of_sight", "scripted", "global"]),
                "flee_threshold": round(0.2 + 0.05 * difficulty.numeric_value, 2),
                "call_reinforcements": difficulty.numeric_value >= 3,
                "patrol_pattern": rng.choice(["idle", "path", "random", "guard"]),
            })

        elif mechanic_type == MechanicType.BOSS:
            rules.update({
                "phase_transition_health": [round(1.0 - (i / 3), 2) for i in range(1, 3)],
                "invulnerability_duration": round(2.0 * difficulty.numeric_value, 1),
                "telegraph_attacks": difficulty.numeric_value <= 4,
                "arena_lock": difficulty.numeric_value >= 3,
            })

        elif mechanic_type == MechanicType.OBSTACLE:
            rules.update({
                "destructible": rng.random() > 0.6,
                "pass_through": rng.random() > 0.8,
                "damage_type": rng.choice(["instant", "over_time", "percentage"]),
                "knockback_force": round(50.0 * difficulty.numeric_value, 1),
            })

        return rules

    def _generate_mechanic_rewards(
        self,
        rng: random.Random,
        mechanic_type: MechanicType,
        difficulty: DifficultyTier,
        player_level: int,
    ) -> Dict[str, Any]:
        """Generate reward definitions for completing a mechanic."""
        diff_scale = _DIFFICULTY_SCALE.get(difficulty, _DIFFICULTY_SCALE[DifficultyTier.NORMAL])
        level_mod = 1.0 + (player_level - 1) * 0.1

        rewards: Dict[str, Any] = {
            "experience": round(10.0 * diff_scale["reward"] * level_mod, 1),
            "currency": round(5.0 * diff_scale["reward"] * level_mod, 1),
        }

        if mechanic_type in (MechanicType.BOSS, MechanicType.CHALLENGE):
            rewards["unique_item_chance"] = round(0.05 * diff_scale["reward"], 3)
            rewards["bonus_currency"] = round(20.0 * diff_scale["reward"] * level_mod, 1)

        if mechanic_type == MechanicType.PUZZLE:
            rewards["knowledge_points"] = int(3 * diff_scale["reward"])

        if mechanic_type == MechanicType.COLLECTIBLE:
            rewards["collection_score"] = int(5 * diff_scale["reward"])
            rewards["set_bonus"] = rng.choice([True, False])

        if mechanic_type == MechanicType.ENCOUNTER:
            rewards["loot_table"] = rng.choice(["common", "uncommon", "rare"])
            rewards["drop_count"] = max(1, int(diff_scale["count"]))

        return rewards

    def generate_mechanic(
        self,
        session_id: str,
        mechanic_type: MechanicType,
        difficulty_tier: Optional[DifficultyTier] = None,
    ) -> Optional[GameplayMechanic]:
        """Generate a single gameplay mechanic within a session.

        Args:
            session_id: The session to generate the mechanic for.
            mechanic_type: The type of mechanic to generate.
            difficulty_tier: Override the session's difficulty (optional).

        Returns:
            A new GameplayMechanic, or None if the session is not found.
        """
        with self._lock:
            session = self._sessions.get(session_id)
            if session is None:
                return None

            difficulty = difficulty_tier or session.difficulty
            rng = self._make_rng(session)
            session.total_mechanics_generated += 1

        name = self._generate_mechanic_name(rng, mechanic_type)
        parameters = self._generate_mechanic_parameters(
            rng, mechanic_type, difficulty, session.style, session.player_level
        )
        rules = self._generate_mechanic_rules(rng, mechanic_type, difficulty)
        rewards = self._generate_mechanic_rewards(
            rng, mechanic_type, difficulty, session.player_level
        )

        mechanic = GameplayMechanic(
            type=mechanic_type,
            difficulty=difficulty,
            style=session.style,
            name=name,
            description=f"A {difficulty.value} {mechanic_type.value}: {name}",
            parameters=parameters,
            rules=rules,
            rewards=rewards,
            seed=session.seed,
            tags=[mechanic_type.value, difficulty.value, session.style.value],
        )

        with self._lock:
            self._mechanics[mechanic.mechanic_id] = mechanic
            session.active_mechanics.append(mechanic)
            self._total_generated += 1
            self._generation_history.append({
                "type": "mechanic",
                "mechanic_id": mechanic.mechanic_id,
                "mechanic_type": mechanic_type.value,
                "difficulty": difficulty.value,
                "timestamp": time.time(),
            })

        return mechanic

    # ------------------------------------------------------------------
    # Event Generation
    # ------------------------------------------------------------------

    def generate_event(
        self,
        session_id: str,
        trigger_condition: Dict[str, Any],
        mechanic_count: int = 2,
        duration: float = 30.0,
        cooldown: float = 0.0,
        priority: int = 0,
    ) -> Optional[GameplayEvent]:
        """Generate a gameplay event composed of multiple mechanics.

        Args:
            session_id: The session to generate the event for.
            trigger_condition: Dict describing when the event activates
                (e.g., {"type": "timer", "interval": 60.0}).
            mechanic_count: Number of mechanics to bundle in the event.
            duration: How long the event lasts in seconds.
            cooldown: Minimum time between event activations.
            priority: Execution priority (higher = more urgent).

        Returns:
            A new GameplayEvent, or None if the session is not found.
        """
        with self._lock:
            session = self._sessions.get(session_id)
            if session is None:
                return None

        # Distribute mechanic types across the event
        available_types = [
            MechanicType.CHALLENGE,
            MechanicType.ENCOUNTER,
            MechanicType.OBSTACLE,
            MechanicType.REWARD,
            MechanicType.PUZZLE,
        ]
        rng = self._make_rng(session, offset=1000)
        selected_types = rng.choices(available_types, k=mechanic_count)

        event_mechanics: List[GameplayMechanic] = []
        for mtype in selected_types:
            mech = self.generate_mechanic(session_id, mtype)
            if mech:
                event_mechanics.append(mech)

        event = GameplayEvent(
            trigger_condition=trigger_condition,
            mechanics=event_mechanics,
            duration=duration,
            cooldown=cooldown,
            priority=priority,
            name=f"Event: {trigger_condition.get('type', 'custom')}",
            description=f"Event triggering on {json.dumps(trigger_condition)}",
            style=session.style,
            seed=session.seed,
        )

        with self._lock:
            session = self._sessions.get(session_id)
            if session is None:
                return None
            self._events[event.event_id] = event
            session.active_events.append(event)
            session.total_events_generated += 1
            self._generation_history.append({
                "type": "event",
                "event_id": event.event_id,
                "mechanic_count": len(event_mechanics),
                "timestamp": time.time(),
            })

        return event

    # ------------------------------------------------------------------
    # Encounter Generation
    # ------------------------------------------------------------------

    def generate_encounter(
        self,
        session_id: str,
        difficulty: Optional[DifficultyTier] = None,
        style: Optional[GenerationStyle] = None,
    ) -> Optional[Dict[str, Any]]:
        """Generate a complete encounter with multiple mechanic types.

        An encounter combines enemies, obstacles, and potential rewards
        into a single gameplay package. The composition is influenced by
        the session's style and difficulty.

        Args:
            session_id: The session to generate the encounter for.
            difficulty: Override difficulty tier (optional).
            style: Override generation style (optional).

        Returns:
            A dict with encounter_id, mechanics, difficulty, and metadata.
        """
        with self._lock:
            session = self._sessions.get(session_id)
            if session is None:
                return None

            eff_difficulty = difficulty or session.difficulty
            eff_style = style or session.style

        rng = self._make_rng(session, offset=2000 + session.total_mechanics_generated)

        encounter_mechanics: List[Dict[str, Any]] = []

        # Main encounter enemy group
        enemy_count = max(1, int(_DIFFICULTY_SCALE[eff_difficulty]["count"]))
        for i in range(enemy_count):
            mech = self.generate_mechanic(session_id, MechanicType.ENCOUNTER, eff_difficulty)
            if mech:
                encounter_mechanics.append(mech.to_dict())

        # Obstacles based on style
        obstacle_chance = 0.3
        if eff_style in (GenerationStyle.DEFENSIVE, GenerationStyle.CHAOTIC):
            obstacle_chance = 0.6
        if rng.random() < obstacle_chance:
            obs = self.generate_mechanic(session_id, MechanicType.OBSTACLE, eff_difficulty)
            if obs:
                encounter_mechanics.append(obs.to_dict())

        # Rewards
        reward = self.generate_mechanic(session_id, MechanicType.REWARD, eff_difficulty)
        if reward:
            encounter_mechanics.append(reward.to_dict())

        # Boss chance based on difficulty
        boss_chance = min(0.3, eff_difficulty.numeric_value * 0.06)
        if rng.random() < boss_chance:
            boss = self.generate_mechanic(session_id, MechanicType.BOSS, eff_difficulty)
            if boss:
                encounter_mechanics.append(boss.to_dict())

        encounter_id = uuid.uuid4().hex

        # Compute aggregate metrics
        total_enemy_health = sum(
            m.get("parameters", {}).get("enemy_health", 0)
            + m.get("parameters", {}).get("health", 0)
            for m in encounter_mechanics
        )
        total_enemy_damage = sum(
            m.get("parameters", {}).get("enemy_damage", 0)
            + m.get("parameters", {}).get("damage", 0)
            for m in encounter_mechanics
        )

        result = {
            "encounter_id": encounter_id,
            "session_id": session_id,
            "difficulty": eff_difficulty.value,
            "style": eff_style.value,
            "mechanics": encounter_mechanics,
            "mechanic_count": len(encounter_mechanics),
            "aggregate_health": round(total_enemy_health, 1),
            "aggregate_damage": round(total_enemy_damage, 1),
            "estimated_duration": round(30.0 * eff_difficulty.numeric_value * 0.5, 1),
            "recommended_player_level": max(1, session.player_level + eff_difficulty.numeric_value - 3),
        }

        return result

    # ------------------------------------------------------------------
    # Wave Generation
    # ------------------------------------------------------------------

    def generate_wave(
        self,
        session_id: str,
        wave_number: int,
        intensity: float = 1.0,
    ) -> Optional[List[GameplayMechanic]]:
        """Generate a wave of mechanics for progressive gameplay.

        Each successive wave increases in difficulty and mechanical
        variety. Intensity scales the overall challenge of the wave.

        Args:
            session_id: The session to generate the wave for.
            wave_number: The wave index (1-based).
            intensity: Multiplier for wave difficulty (1.0 = normal).

        Returns:
            A list of GameplayMechanic objects, or None if session not found.
        """
        with self._lock:
            session = self._sessions.get(session_id)
            if session is None:
                return None

        rng = self._make_rng(session, offset=3000 + wave_number * 100)

        # Escalate difficulty with wave number
        base_tier_idx = DifficultyTier.NORMAL.numeric_value - 1
        wave_tier_idx = min(
            len(DifficultyTier) - 1,
            base_tier_idx + int((wave_number - 1) * intensity * 0.5),
        )
        wave_difficulty = DifficultyTier.from_numeric(float(wave_tier_idx + 1))

        # Determine mechanic composition
        mechanic_count = max(2, min(8, int(2 + wave_number * intensity)))
        wave_mechanics: List[GameplayMechanic] = []

        # Early waves: mostly encounters and obstacles
        # Mid waves: add challenges and puzzles
        # Late waves: add bosses and events
        type_weights: Dict[MechanicType, float] = {
            MechanicType.ENCOUNTER: max(0.1, 0.5 - wave_number * 0.05),
            MechanicType.OBSTACLE: max(0.05, 0.25 - wave_number * 0.03),
            MechanicType.CHALLENGE: min(0.3, 0.1 + wave_number * 0.03),
            MechanicType.REWARD: 0.15,
            MechanicType.PUZZLE: min(0.2, wave_number * 0.02),
            MechanicType.BOSS: min(0.3, 0.05 + wave_number * 0.04),
        }

        types = list(type_weights.keys())
        weights = list(type_weights.values())

        for _ in range(mechanic_count):
            selected_type = rng.choices(types, weights=weights, k=1)[0]
            mech = self.generate_mechanic(session_id, selected_type, wave_difficulty)
            if mech:
                wave_mechanics.append(mech)

        return wave_mechanics

    # ------------------------------------------------------------------
    # Challenge Evaluation
    # ------------------------------------------------------------------

    def evaluate_challenge(
        self,
        mechanic_id: str,
        player_stats: Dict[str, float],
    ) -> Optional[Dict[str, Any]]:
        """Evaluate a player's likelihood of success against a mechanic.

        Simulates a challenge resolution using the mechanic's parameters
        and the player's stats. Returns detailed outcome metrics.

        Args:
            mechanic_id: The mechanic to evaluate.
            player_stats: Dict with player attributes (attack, defense,
                speed, precision, puzzle_skill, etc.)

        Returns:
            Dict with success probability, estimated duration, damage
            taken, score, and reward estimates.
        """
        with self._lock:
            mechanic = self._mechanics.get(mechanic_id)
            if mechanic is None:
                return None

        params = mechanic.parameters
        player_attack = player_stats.get("attack", 10.0)
        player_defense = player_stats.get("defense", 10.0)
        player_speed = player_stats.get("speed", 10.0)
        player_precision = player_stats.get("precision", 10.0)
        player_puzzle = player_stats.get("puzzle_skill", 10.0)

        diff_val = mechanic.difficulty.numeric_value

        if mechanic.type == MechanicType.CHALLENGE:
            challenge_health = params.get("health", 100.0)
            challenge_damage = params.get("damage", 20.0)
            time_limit = params.get("time_limit", 90.0)

            player_dps = player_attack * (player_speed / 20.0) * (player_precision / 15.0)
            time_to_kill = challenge_health / max(player_dps, 0.1)
            incoming_dps = challenge_damage * (1.0 - min(0.8, player_defense / 100.0))
            estimated_damage = incoming_dps * min(time_to_kill, time_limit)
            success_prob = min(1.0, max(0.01, (time_limit / max(time_to_kill, 0.1)) * 0.5
                                        + (player_defense / (challenge_damage * 3.0)) * 0.5))

        elif mechanic.type == MechanicType.PUZZLE:
            complexity = params.get("complexity", 3.0)
            time_limit = params.get("time_limit", 120.0)
            steps = params.get("steps_required", 3)

            effective_skill = player_puzzle * (1.0 + player_precision / 100.0)
            solve_time_per_step = 15.0 * complexity / max(effective_skill, 1.0)
            total_solve_time = solve_time_per_step * steps
            success_prob = min(1.0, max(0.01, effective_skill / (complexity * 5.0)))
            estimated_damage = max(0.0, (total_solve_time - time_limit) * 0.2)
            time_to_kill = total_solve_time
            time_limit = time_limit
            challenge_health = complexity * steps * 10.0
            challenge_damage = 0.0

        elif mechanic.type == MechanicType.ENCOUNTER:
            enemy_health = params.get("enemy_health", 80.0)
            enemy_damage = params.get("enemy_damage", 15.0)
            enemy_count = params.get("enemy_count", 1)

            player_dps = player_attack * (player_speed / 20.0)
            time_per_enemy = enemy_health / max(player_dps, 0.1)
            time_to_kill = time_per_enemy * enemy_count * 1.3  # overhead for switching targets
            incoming_dps = enemy_damage * enemy_count * (1.0 - min(0.75, player_defense / 100.0))
            estimated_damage = incoming_dps * time_to_kill
            success_prob = min(1.0, max(0.01,
                (player_defense * 3.0 + player_attack * 2.0) / (enemy_health * enemy_count * 0.5)))
            time_limit = 120.0
            challenge_health = enemy_health * enemy_count
            challenge_damage = enemy_damage * enemy_count

        elif mechanic.type == MechanicType.BOSS:
            boss_health = params.get("health", 500.0)
            boss_damage = params.get("damage", 50.0)
            phases = params.get("phase_count", 1)

            player_dps = player_attack * (player_speed / 20.0) * (player_precision / 15.0)
            time_to_kill = boss_health * (1.0 + 0.2 * phases) / max(player_dps, 0.1)
            incoming_dps = boss_damage * (1.0 - min(0.7, player_defense / 120.0))
            estimated_damage = incoming_dps * time_to_kill
            success_prob = min(1.0, max(0.005,
                (player_attack + player_defense + player_speed) / (boss_damage * 2.0 + boss_health / 20.0)))
            time_limit = 300.0
            challenge_health = boss_health
            challenge_damage = boss_damage

        else:
            time_to_kill = 10.0
            estimated_damage = 0.0
            success_prob = 0.9
            time_limit = 60.0
            challenge_health = 50.0
            challenge_damage = 10.0

        # Compute score
        base_score = 100.0 * mechanic.difficulty.numeric_value
        time_bonus = max(0.0, (time_limit - time_to_kill) / max(time_limit, 1.0)) * 50.0
        damage_penalty = estimated_damage * 0.5
        estimated_score = max(0.0, round(base_score + time_bonus - damage_penalty, 1))

        # Reward estimates
        reward_exp = mechanic.rewards.get("experience", 0)
        reward_currency = mechanic.rewards.get("currency", 0)
        reward_scaled = {
            "experience": round(reward_exp * success_prob, 1),
            "currency": round(reward_currency * success_prob, 1),
        }

        return {
            "mechanic_id": mechanic_id,
            "mechanic_type": mechanic.type.value,
            "difficulty": mechanic.difficulty.value,
            "success_probability": round(success_prob, 4),
            "estimated_duration": round(time_to_kill, 1),
            "estimated_damage_taken": round(estimated_damage, 1),
            "estimated_score": estimated_score,
            "estimated_rewards": reward_scaled,
            "time_limit": round(time_limit, 1),
            "player_dps": round(player_attack * (player_speed / 20.0) * (player_precision / 15.0), 1),
        }

    # ------------------------------------------------------------------
    # Difficulty Adaptation
    # ------------------------------------------------------------------

    def adapt_difficulty(
        self,
        session_id: str,
        player_performance: Dict[str, float],
    ) -> Optional[DifficultyTier]:
        """Adjust session difficulty based on player performance metrics.

        Analyzes win rate, completion times, and other performance
        indicators to determine if the current difficulty should be
        adjusted up or down.

        Args:
            session_id: The session to adjust.
            player_performance: Dict with metrics such as win_rate,
                average_time, completion_rate, deaths_per_encounter.

        Returns:
            The new DifficultyTier after adaptation.
        """
        with self._lock:
            session = self._sessions.get(session_id)
            if session is None:
                return None

        win_rate = player_performance.get("win_rate", 0.5)
        completion_rate = player_performance.get("completion_rate", 0.5)
        avg_time = player_performance.get("average_time", 60.0)
        deaths = player_performance.get("deaths_per_encounter", 1.0)

        # Compute a composite performance score
        time_factor = max(0.0, 1.0 - (avg_time / 120.0))
        death_penalty = max(0.0, 1.0 - (deaths * 0.3))
        composite = (win_rate * 0.35 + completion_rate * 0.25
                     + time_factor * 0.20 + death_penalty * 0.20)

        # Determine shift amount
        shift = 0
        for threshold, delta in _PERFORMANCE_THRESHOLDS:
            if composite >= threshold:
                shift = delta
                break

        current_idx = session.difficulty.numeric_value - 1
        new_idx = max(0, min(len(DifficultyTier) - 1, current_idx + shift))
        new_tier = DifficultyTier.from_numeric(float(new_idx + 1))

        with self._lock:
            session = self._sessions.get(session_id)
            if session is not None:
                session.difficulty = new_tier

        return new_tier

    # ------------------------------------------------------------------
    # Statistics
    # ------------------------------------------------------------------

    def get_stats(self) -> Dict[str, Any]:
        """Return aggregate statistics about the generation engine.

        Returns:
            Dict with total counts, per-type breakdowns, and history.
        """
        with self._lock:
            type_counts: Dict[str, int] = {}
            diff_counts: Dict[str, int] = {}
            for m in self._mechanics.values():
                type_counts[m.type.value] = type_counts.get(m.type.value, 0) + 1
                diff_counts[m.difficulty.value] = diff_counts.get(m.difficulty.value, 0) + 1

            style_counts: Dict[str, int] = {}
            for s in self._sessions.values():
                style_counts[s.style.value] = style_counts.get(s.style.value, 0) + 1

            recent = list(self._generation_history)[-10:]

            return {
                "total_mechanics": len(self._mechanics),
                "total_events": len(self._events),
                "total_sessions": self._total_sessions,
                "active_sessions": len(self._sessions),
                "total_generated": self._total_generated,
                "by_mechanic_type": type_counts,
                "by_difficulty": diff_counts,
                "by_style": style_counts,
                "recent_generations": recent,
            }

    # ------------------------------------------------------------------
    # Serialization
    # ------------------------------------------------------------------

    def export_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Export a session and all its content as a serializable dict.

        Args:
            session_id: The session to export.

        Returns:
            A dict representation of the session and its content.
        """
        with self._lock:
            session = self._sessions.get(session_id)
            if session is None:
                return None
            return session.to_dict()

    def import_session(self, data: Dict[str, Any]) -> GameplaySession:
        """Import a session from a previously exported dict.

        Args:
            data: The serialized session data.

        Returns:
            The reconstructed GameplaySession.
        """
        session = GameplaySession(
            session_id=data.get("session_id", uuid.uuid4().hex),
            style=GenerationStyle(data.get("style", "balanced")),
            difficulty=DifficultyTier(data.get("difficulty", "normal")),
            player_level=data.get("player_level", 1),
            seed=data.get("seed", 0),
            total_mechanics_generated=data.get("total_mechanics_generated", 0),
            total_events_generated=data.get("total_events_generated", 0),
            created_at=data.get("created_at", time.time()),
        )

        for m_data in data.get("active_mechanics", []):
            mechanic = GameplayMechanic.from_dict(m_data)
            session.active_mechanics.append(mechanic)
            self._mechanics[mechanic.mechanic_id] = mechanic

        for e_data in data.get("active_events", []):
            event = GameplayEvent.from_dict(e_data)
            session.active_events.append(event)
            self._events[event.event_id] = event

        with self._lock:
            self._sessions[session.session_id] = session
            if session.total_mechanics_generated == 0:
                session.total_mechanics_generated = len(session.active_mechanics)
                session.total_events_generated = len(session.active_events)

        return session

    # ------------------------------------------------------------------
    # Cleanup
    # ------------------------------------------------------------------

    def clear_session(self, session_id: str) -> bool:
        """Remove all generated content from a session without deleting it.

        Args:
            session_id: The session to clear.

        Returns:
            True if the session was found and cleared.
        """
        with self._lock:
            session = self._sessions.get(session_id)
            if session is None:
                return False
            for m in session.active_mechanics:
                self._mechanics.pop(m.mechanic_id, None)
            for e in session.active_events:
                self._events.pop(e.event_id, None)
            session.active_mechanics.clear()
            session.active_events.clear()
            return True

    def reset(self):
        """Reset the entire engine: drop all sessions, mechanics, and events."""
        with self._lock:
            self._sessions.clear()
            self._mechanics.clear()
            self._events.clear()
            self._generation_history.clear()
            self._total_generated = 0
            self._total_sessions = 0


# ---------------------------------------------------------------------------
# Module-Level Singleton Accessor
# ---------------------------------------------------------------------------

def get_procedural_gameplay() -> ProceduralGameplayEngine:
    """Return the singleton ProceduralGameplayEngine instance."""
    return ProceduralGameplayEngine()