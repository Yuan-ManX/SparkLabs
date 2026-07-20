"""
SparkLabs Engine - Cognitive Fusion Layer

Integrates three previously-independent modules into a single
coordinated cognitive loop:
  1. CognitiveGameEngine - the unified perceive/reason/act/reflect/learn tick
  2. CognitiveSkillForge - persistent skill library with extraction/matching/evolution
  3. AdaptivePhysicsDirector - flow-channel physics tuning

The fusion layer runs the three modules in a coordinated sequence:
  - BEFORE tick: query skill forge for matched skills, query physics
    director for current parameters
  - DURING tick: the CognitiveGameEngine runs its 6-phase cognitive cycle
  - AFTER tick: extract skill candidates from successful outcomes,
    record player signals to physics director, run physics adaptation
    at its own interval, run skill evolution at its own interval

This produces a self-reinforcing learning loop: the engine acts,
the forge captures successful actions as skills, the physics director
tunes parameters to maintain flow, and on the next tick the engine
benefits from both. Over time, the system converges on a parameter
surface and skill library tuned to the player's skill level.

Thread-safe singleton: use get_instance() to access.
"""

from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from sparkai.agent.agent_cognitive_skill_forge import (
    CognitiveSkillForge, StateSignature,
)
from sparkai.engine.engine_adaptive_physics_director import (
    AdaptivePhysicsDirector, FlowState,
)
from sparkai.engine.engine_cognitive_game_engine import (
    CognitiveGameEngine, get_cognitive_engine,
)

logger = logging.getLogger(__name__)


# =============================================================================
# Fusion Tick Result
# =============================================================================

@dataclass
class FusionTickResult:
    """Result of a single fused cognitive tick."""
    tick: int
    cognitive_phase: str = ""
    actions_planned: int = 0
    actions_executed: int = 0
    confidence: float = 0.0
    lesson: str = ""
    # Skill forge results
    skills_matched: int = 0
    skill_extracted: bool = False
    # Physics director results
    physics_adapted: bool = False
    flow_state: str = "unknown"
    skill_estimate: float = 0.5
    target_difficulty: float = 0.5
    # Timing
    duration_s: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "tick": self.tick,
            "cognitive_phase": self.cognitive_phase,
            "actions_planned": self.actions_planned,
            "actions_executed": self.actions_executed,
            "confidence": self.confidence,
            "lesson": self.lesson,
            "skills_matched": self.skills_matched,
            "skill_extracted": self.skill_extracted,
            "physics_adapted": self.physics_adapted,
            "flow_state": self.flow_state,
            "skill_estimate": self.skill_estimate,
            "target_difficulty": self.target_difficulty,
            "duration_s": self.duration_s,
        }


# =============================================================================
# Cognitive Fusion Layer
# =============================================================================

class CognitiveFusionLayer:
    """
    The fusion layer coordinating the cognitive engine, skill forge,
    and physics director. Thread-safe singleton.
    """

    _instance: Optional["CognitiveFusionLayer"] = None
    _instance_lock = threading.Lock()

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._engine: CognitiveGameEngine = get_cognitive_engine()
        self._forge: CognitiveSkillForge = CognitiveSkillForge.get_instance()
        self._director: AdaptivePhysicsDirector = AdaptivePhysicsDirector.get_instance()

        # Telemetry
        self._fusion_tick_count: int = 0
        self._total_duration_s: float = 0.0
        self._last_result: Optional[FusionTickResult] = None
        self._history: List[FusionTickResult] = []
        self._max_history = 64

        # Configuration
        self._record_player_signals = True
        self._extract_skills = True
        self._evolve_skills = True

    @classmethod
    def get_instance(cls) -> "CognitiveFusionLayer":
        with cls._instance_lock:
            if cls._instance is None:
                cls._instance = cls()
            return cls._instance

    # ---- Lifecycle ----

    def initialize(self) -> None:
        """Initialize all three subsystems."""
        self._engine.initialize()

    def start(self) -> None:
        """Start the fusion layer."""
        if self._engine._state.value == "cold":
            self._engine.initialize()
        self._engine._state = self._engine._state.__class__("running") \
            if hasattr(self._engine._state, "value") and self._engine._state.value != "paused" \
            else self._engine._state

    def pause(self) -> None:
        self._engine.pause()

    def resume(self) -> None:
        self._engine.resume()

    def reset(self) -> None:
        with self._lock:
            self._engine.reset()
            self._forge.reset()
            self._director.reset()
            self._fusion_tick_count = 0
            self._total_duration_s = 0.0
            self._last_result = None
            self._history.clear()

    # ---- Fused Tick ----

    def fused_tick(self, dt: float = 1.0 / 60.0) -> FusionTickResult:
        """
        Run one fused cognitive tick. This is the single entry point
        that coordinates all three modules.
        """
        start = time.time()
        with self._lock:
            self._fusion_tick_count += 1

        # Phase 1: BEFORE tick - query skill forge for matched skills
        state_snapshot = self._build_state_snapshot()
        matched_skills = self._forge.match_skills(state_snapshot, limit=3)
        # Note: matched skills are logged but not directly injected into
        # the reasoning layer (the engine's ReasoningLayer already queries
        # procedural memory). The forge provides a richer, cross-session
        # skill library that supplements procedural memory.

        # Phase 2: DURING tick - run the cognitive engine's 6-phase tick
        cog_result = self._engine.cognitive_tick(dt)

        # Phase 3: AFTER tick - extract skills and record signals

        # Extract skill from this tick's outcomes
        skill_extracted = False
        if self._extract_skills and cog_result.actions_planned:
            actions_data = [
                {
                    "action_type": a.action_type.value,
                    "params": dict(a.params),
                    "target_id": a.target_id,
                    "expected_outcome": a.expected_outcome,
                    "confidence": a.confidence,
                } for a in cog_result.actions_planned
            ]
            outcomes_data = []
            if cog_result.outcome is not None:
                outcomes_data.append({
                    "success": cog_result.outcome.success,
                    "notes": cog_result.outcome.notes,
                })
            # Build state snapshot from the perception frame
            perception = cog_result.perception
            if perception is not None:
                snapshot = {
                    "player_health": perception.player.health if perception.player else 100.0,
                    "enemy_count": sum(
                        1 for e in perception.entities if e.entity_type == "enemy"
                    ),
                    "pacing_zone": perception.metrics.get("pacing_zone", "normal"),
                    "difficulty": perception.metrics.get("difficulty", 0.5),
                }
                skill = self._forge.extract_from_tick(
                    tick=cog_result.tick,
                    actions=actions_data,
                    outcomes=outcomes_data,
                    state_snapshot=snapshot,
                )
                skill_extracted = skill is not None

        # Record player signals to physics director
        physics_adapted = False
        flow_state = "unknown"
        skill_estimate = 0.5
        target_difficulty = 0.5
        if self._record_player_signals and cog_result.perception is not None:
            perception = cog_result.perception
            player = perception.player
            if player is not None:
                self._director.record_tick(
                    tick=cog_result.tick,
                    died=(player.health < 30),  # heuristic: low health = recent death
                    jumped=abs(player.vy) > 2.0,  # heuristic: vertical velocity
                    wall_touch=False,  # not directly observable from perception
                    speed=abs(player.vx),
                    collected=False,  # not directly observable
                    progress_delta=max(0.0, player.vx * dt),
                )
            # Run physics adaptation at its own interval
            adapt_result = self._director.adapt(cog_result.tick)
            if adapt_result is not None:
                physics_adapted = True
                flow_state = adapt_result.get("flow_state", "unknown")
                skill_estimate = adapt_result.get("skill_estimate", 0.5)
                target_difficulty = adapt_result.get("target_difficulty", 0.5)

        # Run skill evolution at its own interval
        if self._evolve_skills:
            self._forge.evolve(cog_result.tick)

        duration_s = time.time() - start
        with self._lock:
            self._total_duration_s += duration_s

        result = FusionTickResult(
            tick=cog_result.tick,
            cognitive_phase=cog_result.phase.value,
            actions_planned=len(cog_result.actions_planned),
            actions_executed=cog_result.actions_executed,
            confidence=cog_result.confidence,
            lesson=cog_result.lesson,
            skills_matched=len(matched_skills),
            skill_extracted=skill_extracted,
            physics_adapted=physics_adapted,
            flow_state=flow_state,
            skill_estimate=skill_estimate,
            target_difficulty=target_difficulty,
            duration_s=duration_s,
        )

        with self._lock:
            self._last_result = result
            self._history.append(result)
            if len(self._history) > self._max_history:
                self._history = self._history[-self._max_history:]

        return result

    def _build_state_snapshot(self) -> Dict[str, Any]:
        """Build a state snapshot for skill matching."""
        status = self._engine.status()
        entities = status.get("entities", [])
        metrics = status.get("metrics", {})
        player = None
        for e in entities:
            if e.get("type") == "player":
                player = e
                break
        return {
            "player_health": player.get("health", 100.0) if player else 100.0,
            "enemy_count": sum(1 for e in entities if e.get("type") == "enemy"),
            "pacing_zone": metrics.get("pacing_zone", "normal"),
            "difficulty": metrics.get("difficulty", 0.5),
        }

    # ---- Fused Batch ----

    def fused_batch(self, count: int = 10, dt: float = 1.0 / 60.0) -> Dict[str, Any]:
        """Run N fused ticks in sequence."""
        count = max(1, min(count, 200))
        last_result = None
        for _ in range(count):
            last_result = self.fused_tick(dt)
        return {
            "ticks_run": count,
            "last_result": last_result.to_dict() if last_result else None,
            "status": self.status(),
        }

    # ---- Status ----

    def status(self) -> Dict[str, Any]:
        with self._lock:
            engine_status = self._engine.status()
            forge_status = self._forge.status()
            director_status = self._director.status()
            return {
                "fusion_tick_count": self._fusion_tick_count,
                "total_duration_s": self._total_duration_s,
                "avg_fusion_duration_s": (
                    self._total_duration_s / max(1, self._fusion_tick_count)
                ),
                "engine_state": engine_status.get("state", "cold"),
                "engine_tick": engine_status.get("tick", 0),
                "engine_entity_count": engine_status.get("entity_count", 0),
                "forge_total_skills": forge_status.get("total_skills", 0),
                "forge_active_skills": forge_status.get("by_status", {}).get("active", 0),
                "forge_total_extracted": forge_status.get("total_extracted", 0),
                "forge_total_evolved": forge_status.get("total_evolved", 0),
                "director_flow_state": director_status.get("flow_estimate", {}).get("flow_state", "unknown"),
                "director_skill_estimate": director_status.get("flow_estimate", {}).get("skill_estimate", 0.5),
                "director_target_difficulty": director_status.get("flow_estimate", {}).get("target_difficulty", 0.5),
                "director_total_adjustments": director_status.get("total_adjustments", 0),
                "director_profiles_count": director_status.get("profiles_count", 0),
                "last_result": self._last_result.to_dict() if self._last_result else None,
            }

    def history(self, limit: int = 10) -> List[Dict[str, Any]]:
        with self._lock:
            return [r.to_dict() for r in self._history[-limit:]]

    def full_status(self) -> Dict[str, Any]:
        """Get the complete status of all three subsystems."""
        with self._lock:
            return {
                "fusion": self.status(),
                "engine": self._engine.status(),
                "forge": self._forge.status(),
                "director": self._director.status(),
            }


# =============================================================================
# Module-Level Convenience
# =============================================================================

def get_fusion_layer() -> CognitiveFusionLayer:
    """Get the singleton CognitiveFusionLayer instance."""
    return CognitiveFusionLayer.get_instance()


def fused_tick(dt: float = 1.0 / 60.0) -> FusionTickResult:
    """Run one fused cognitive tick."""
    return get_fusion_layer().fused_tick(dt)
