"""
SparkLabs Agent - Adaptive Difficulty Engine

Dynamic gameplay parameter modulation based on real-time player
performance analysis. Continuously adjusts enemy aggression,
spawn rates, resource availability, puzzle complexity, and
encounter pacing to maintain optimal challenge-flow balance
without explicit difficulty selection.

Architecture:
  AdaptiveDifficultyEngine
    |-- PerformanceMonitor (latent skill estimation from gameplay)
    |-- DifficultyScaler (parameter interpolation across challenge bands)
    |-- FlowOptimizer (targets the optimal arousal-challenge zone)
    |-- FrustrationDetector (early warning for excessive deaths/failures)
    |-- BoredomDetector (trivial encounter detection)
    |-- AdaptationLogger (decision audit trail for tuning review)

Difficulty Bands:
  - RELAXED: guided experience, generous resources
  - BALANCED: standard challenge, fair resource distribution
  - INTENSE: heightened threat, scarce resources
  - NIGHTMARE: maximum pressure, minimal support
"""

from __future__ import annotations

import math
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


class DifficultyBand(Enum):
    RELAXED = (0.0, 0.35, "relaxed")
    BALANCED = (0.35, 0.65, "balanced")
    INTENSE = (0.65, 0.85, "intense")
    NIGHTMARE = (0.85, 1.0, "nightmare")

    def __new__(cls, min_val, max_val, label):
        obj = object.__new__(cls)
        obj._value_ = label
        obj.min_val = min_val
        obj.max_val = max_val
        return obj

    @classmethod
    def from_score(cls, score: float):
        for band in cls:
            if band.min_val <= score <= band.max_val:
                return band
        return cls.BALANCED


class FlowZone(Enum):
    BOREDOM = "boredom"
    FLOW = "flow"
    ANXIETY = "anxiety"
    OVERLOAD = "overload"


class AdaptationDomain(Enum):
    ENEMY_HEALTH = "enemy_health"
    ENEMY_DAMAGE = "enemy_damage"
    ENEMY_AGGRESSION = "enemy_aggression"
    SPAWN_RATE = "spawn_rate"
    RESOURCE_DROPS = "resource_drops"
    PUZZLE_TIMER = "puzzle_timer"
    CHECKPOINT_FREQUENCY = "checkpoint_frequency"
    AI_ACCURACY = "ai_accuracy"


@dataclass
class DifficultyParameter:
    domain: AdaptationDomain
    base_value: float = 0.5
    current_value: float = 0.5
    min_value: float = 0.1
    max_value: float = 1.0
    adapt_rate: float = 0.1
    inertia: float = 0.7

    def apply(self, direction: float):
        target = self.current_value + direction * self.adapt_rate * (self.max_value - self.min_value)
        target = max(self.min_value, min(self.max_value, target))
        self.current_value = self.current_value * self.inertia + target * (1.0 - self.inertia)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "domain": self.domain.value,
            "value": round(self.current_value, 3),
            "base": round(self.base_value, 3),
        }


@dataclass
class AdaptationEvent:
    event_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    player_id: str = ""
    previous_band: DifficultyBand = DifficultyBand.BALANCED
    new_band: DifficultyBand = DifficultyBand.BALANCED
    trigger: str = ""
    flow_zone: FlowZone = FlowZone.FLOW
    parameter_changes: Dict[str, float] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": self.event_id,
            "player_id": self.player_id,
            "band": f"{self.previous_band.value} -> {self.new_band.value}",
            "zone": self.flow_zone.value,
            "changes": self.parameter_changes,
        }


class AdaptiveDifficultyEngine:
    _instance: Optional[AdaptiveDifficultyEngine] = None

    @classmethod
    def get_instance(cls) -> AdaptiveDifficultyEngine:
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    DEFAULT_PARAMS = {
        AdaptationDomain.ENEMY_HEALTH: (0.5, 0.2, 1.0),
        AdaptationDomain.ENEMY_DAMAGE: (0.5, 0.1, 1.0),
        AdaptationDomain.ENEMY_AGGRESSION: (0.5, 0.2, 1.0),
        AdaptationDomain.SPAWN_RATE: (0.5, 0.1, 1.0),
        AdaptationDomain.RESOURCE_DROPS: (0.7, 0.2, 1.0),
        AdaptationDomain.PUZZLE_TIMER: (0.5, 0.3, 1.0),
        AdaptationDomain.CHECKPOINT_FREQUENCY: (0.5, 0.1, 1.0),
        AdaptationDomain.AI_ACCURACY: (0.5, 0.1, 1.0),
    }

    def __init__(self):
        self._player_params: Dict[str, Dict[AdaptationDomain, DifficultyParameter]] = {}
        self._current_bands: Dict[str, DifficultyBand] = {}
        self._event_log: List[AdaptationEvent] = []
        self._death_windows: Dict[str, List[float]] = {}
        self._success_windows: Dict[str, List[float]] = {}
        self._total_adaptations: int = 0
        self._cooldown_seconds: float = 30.0
        self._enabled: bool = True

    def init_player(self, player_id: str):
        if player_id in self._player_params:
            return
        self._player_params[player_id] = {}
        for domain, (base, _, _) in self.DEFAULT_PARAMS.items():
            self._player_params[player_id][domain] = DifficultyParameter(
                domain=domain, base_value=base, current_value=base)
        self._current_bands[player_id] = DifficultyBand.BALANCED
        self._death_windows[player_id] = []
        self._success_windows[player_id] = []

    def record_event(self, player_id: str, event_type: str, value: float = 1.0):
        if not self._enabled:
            return
        self.init_player(player_id)
        now = time.time()
        if event_type == "death":
            self._death_windows[player_id].append(now)
        elif event_type == "kill":
            self._success_windows[player_id].append(now)
        elif event_type == "heal":
            self._success_windows[player_id].append(now)

    def update(self, player_id: str, delta_time: float = 1.0) -> Optional[AdaptationEvent]:
        if not self._enabled or player_id not in self._player_params:
            return None

        now = time.time()
        deaths = self._death_windows.get(player_id, [])
        successes = self._success_windows.get(player_id, [])

        window = 60.0
        recent_deaths = sum(1 for t in deaths if now - t < window)
        recent_successes = sum(1 for t in successes if now - t < window)

        params = self._player_params[player_id]

        if recent_deaths >= 3:
            direction = -0.15
            flow_zone = FlowZone.ANXIETY
            if recent_deaths >= 6:
                direction = -0.3
                flow_zone = FlowZone.OVERLOAD
            self._apply_adaptation(player_id, direction, flow_zone, f"High deaths: {recent_deaths} in {window}s")
        elif recent_successes >= 10 and recent_deaths == 0:
            direction = 0.15
            flow_zone = FlowZone.BOREDOM
            self._apply_adaptation(player_id, direction, flow_zone, f"No challenge: {recent_successes} successes")
        else:
            flow_zone = FlowZone.FLOW
            self._apply_adaptation(player_id, 0.0, flow_zone, "Maintaining flow")

        self._death_windows[player_id] = [t for t in deaths if now - t < 300]
        self._success_windows[player_id] = [t for t in successes if now - t < 300]

        params = self._player_params[player_id]
        avg = sum(p.current_value for p in params.values()) / len(params)
        band = DifficultyBand.from_score(avg)
        self._current_bands[player_id] = band
        return None

    def _apply_adaptation(self, player_id: str, direction: float, zone: FlowZone, trigger: str):
        params = self._player_params[player_id]
        changes = {}
        for domain in (AdaptationDomain.ENEMY_HEALTH, AdaptationDomain.ENEMY_DAMAGE,
                       AdaptationDomain.ENEMY_AGGRESSION, AdaptationDomain.SPAWN_RATE):
            old_val = params[domain].current_value
            params[domain].apply(direction)
            changes[domain.value] = round(params[domain].current_value - old_val, 3)

        if direction < 0:
            params[AdaptationDomain.RESOURCE_DROPS].apply(-direction * 0.5)
            changes[AdaptationDomain.RESOURCE_DROPS.value] = round(
                params[AdaptationDomain.RESOURCE_DROPS].current_value, 3)

        if changes:
            event = AdaptationEvent(
                player_id=player_id,
                previous_band=self._current_bands.get(player_id, DifficultyBand.BALANCED),
                new_band=self._current_bands.get(player_id, DifficultyBand.BALANCED),
                trigger=trigger,
                flow_zone=zone,
                parameter_changes=changes,
            )
            self._event_log.append(event)
            self._total_adaptations += 1
            if len(self._event_log) > 100:
                self._event_log = self._event_log[-100:]

    def get_difficulty_params(self, player_id: str) -> Dict[str, Any]:
        if player_id not in self._player_params:
            return {"error": "Player not initialized"}
        return {
            "player_id": player_id,
            "band": self._current_bands.get(player_id, DifficultyBand.BALANCED).value,
            "parameters": {p.domain.value: p.to_dict() for p in self._player_params[player_id].values()},
        }

    def get_recent_adaptations(self, limit: int = 10) -> List[Dict[str, Any]]:
        return [e.to_dict() for e in self._event_log[-limit:]]

    def get_stats(self) -> Dict[str, Any]:
        return {
            "total_players": len(self._player_params),
            "total_adaptations": self._total_adaptations,
            "enabled": self._enabled,
            "cooldown_seconds": self._cooldown_seconds,
            "band_distribution": {
                band.value: sum(1 for b in self._current_bands.values() if b == band)
                for band in DifficultyBand
            },
            "parameter_domains": [d.value for d in AdaptationDomain],
        }


def get_adaptive_difficulty() -> AdaptiveDifficultyEngine:
    return AdaptiveDifficultyEngine.get_instance()