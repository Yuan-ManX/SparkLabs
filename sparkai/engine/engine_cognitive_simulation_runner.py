"""
SparkLabs Engine - Cognitive Simulation Runner

A unified simulation runner that creates a self-playing game where the
AI agent both plays the game (via physics-driven virtual player) and
directs the game (via cognitive engine). This is the capstone module
that demonstrates the full AI-native game engine in action.

The simulation loop:
  1. VIRTUAL PLAYER: A heuristic controller generates input based on
     the current physics state (move toward goal, jump over gaps,
     wall-jump when stuck). This simulates a human player.
  2. PHYSICS ENGINE: Steps the world with the virtual player's input,
     producing collision events, position changes, and state transitions.
  3. COGNITIVE FUSION: The fusion layer runs its 6-phase cognitive
     cycle (perceive/reason/plan/act/reflect/learn) observing the
     physics state and taking engine-level actions.
  4. ADAPTIVE DIRECTOR: Records player signals and tunes physics
     parameters to maintain flow.
  5. SKILL FORGE: Extracts skills from successful action sequences.
  6. TELEMETRY: Records full simulation telemetry for replay/analysis.

The result is a closed-loop simulation where:
  - The virtual player navigates the level
  - The cognitive engine adapts the game in real-time
  - The system learns what works and applies it to future runs

Thread-safe singleton: use get_instance() to access.
"""

from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

from sparkai.engine.engine_game_physics import (
    PhysicsWorld, InputState, BodyType, CollisionSide,
)
from sparkai.engine.engine_cognitive_fusion import CognitiveFusionLayer
from sparkai.engine.engine_cognitive_game_engine import CognitiveGameEngine
from sparkai.engine.engine_adaptive_physics_director import AdaptivePhysicsDirector
from sparkai.agent.agent_cognitive_skill_forge import CognitiveSkillForge

logger = logging.getLogger(__name__)


# =============================================================================
# Simulation States
# =============================================================================

class SimulationState(Enum):
    IDLE = "idle"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"


class PlayerStrategy(Enum):
    """Virtual player movement strategies."""
    SPEEDRUN = "speedrun"       # Move right as fast as possible, jump over gaps
    CAUTIOUS = "cautious"        # Move slowly, jump carefully
    EXPLORER = "explorer"        # Move around, try wall-jumps and double-jumps
    AGGRESSIVE = "aggressive"    # Move fast, take risks, wall-jump frequently
    RANDOM = "random"            # Random inputs (baseline for testing)


# =============================================================================
# Data Structures
# =============================================================================

@dataclass
class SimulationFrame:
    """A single frame of simulation telemetry."""
    tick: int
    # Physics state
    player_x: float = 0.0
    player_y: float = 0.0
    player_vx: float = 0.0
    player_vy: float = 0.0
    on_ground: bool = False
    wall_sliding: bool = False
    jumps_remaining: int = 0
    # Input applied
    input_left: bool = False
    input_right: bool = False
    input_jump: bool = False
    # Collisions this frame
    collisions: int = 0
    # Cognitive state
    cognitive_phase: str = ""
    actions_planned: int = 0
    actions_executed: int = 0
    confidence: float = 0.0
    # Adaptation state
    flow_state: str = "unknown"
    skill_estimate: float = 0.5
    target_difficulty: float = 0.5
    physics_adapted: bool = False
    skill_extracted: bool = False
    # Timing
    duration_s: float = 0.0


@dataclass
class SimulationResult:
    """Complete result of a simulation run."""
    strategy: str
    total_ticks: int
    completed: bool
    # Final state
    final_x: float = 0.0
    final_y: float = 0.0
    max_x: float = 0.0
    max_height: float = 0.0
    # Metrics
    total_collisions: int = 0
    total_jumps: int = 0
    total_wall_slides: int = 0
    total_wall_jumps: int = 0
    total_deaths: int = 0
    # Cognitive metrics
    total_actions_planned: int = 0
    total_actions_executed: int = 0
    total_skills_extracted: int = 0
    total_physics_adaptations: int = 0
    avg_confidence: float = 0.0
    # Flow metrics
    flow_distribution: Dict[str, int] = field(default_factory=dict)
    final_skill_estimate: float = 0.5
    final_target_difficulty: float = 0.5
    # Timing
    total_duration_s: float = 0.0
    avg_frame_duration_s: float = 0.0
    # Trajectory (sampled)
    trajectory: List[Dict[str, float]] = field(default_factory=list)


# =============================================================================
# Virtual Player Controller
# =============================================================================

class VirtualPlayerController:
    """
    Generates input for the physics world based on the current state.
    This simulates a human player navigating a level.

    The controller uses simple heuristics:
      - SPEEDRUN: Always move right, jump when hitting a wall or gap
      - CAUTIOUS: Move right slowly, jump when on ground and approaching obstacle
      - EXPLORER: Move right, try wall-jumps and double-jumps
      - AGGRESSIVE: Move right fast, wall-jump whenever touching a wall
      - RANDOM: Random inputs
    """

    def __init__(self, strategy: PlayerStrategy = PlayerStrategy.SPEEDRUN):
        self._strategy = strategy
        self._jump_cooldown: int = 0
        self._frames_since_ground: int = 0
        self._frames_at_same_x: int = 0
        self._last_x: float = 0.0

    def decide_input(
        self,
        player_x: float,
        player_y: float,
        player_vx: float,
        player_vy: float,
        on_ground: bool,
        wall_sliding: bool,
        touching_wall: str,
        jumps_remaining: int,
        tick: int,
    ) -> InputState:
        """Decide the input for this frame based on the player state."""
        if self._jump_cooldown > 0:
            self._jump_cooldown -= 1

        # Track stuck detection
        if abs(player_x - self._last_x) < 0.5:
            self._frames_at_same_x += 1
        else:
            self._frames_at_same_x = 0
        self._last_x = player_x

        if on_ground:
            self._frames_since_ground = 0
        else:
            self._frames_since_ground += 1

        if self._strategy == PlayerStrategy.RANDOM:
            import random
            return InputState(
                left=random.random() < 0.1,
                right=random.random() < 0.7,
                jump_pressed=random.random() < 0.1,
                jump_held=random.random() < 0.3,
            )

        if self._strategy == PlayerStrategy.SPEEDRUN:
            return self._decide_speedrun(
                player_x, player_vy, on_ground, wall_sliding,
                touching_wall, jumps_remaining, tick,
            )

        if self._strategy == PlayerStrategy.CAUTIOUS:
            return self._decide_cautious(
                player_x, player_vy, on_ground, wall_sliding,
                touching_wall, jumps_remaining, tick,
            )

        if self._strategy == PlayerStrategy.EXPLORER:
            return self._decide_explorer(
                player_x, player_vy, on_ground, wall_sliding,
                touching_wall, jumps_remaining, tick,
            )

        if self._strategy == PlayerStrategy.AGGRESSIVE:
            return self._decide_aggressive(
                player_x, player_vy, on_ground, wall_sliding,
                touching_wall, jumps_remaining, tick,
            )

        # Default: move right
        return InputState(right=True)

    def _decide_speedrun(
        self, x: float, vy: float, on_ground: bool, wall_sliding: bool,
        touching_wall: str, jumps: int, tick: int,
    ) -> InputState:
        """Speedrun: always move right, jump over obstacles."""
        jump_pressed = False
        jump_held = False

        # Jump if stuck (not moving right for 10+ frames)
        if self._frames_at_same_x > 10 and self._jump_cooldown == 0:
            jump_pressed = True
            self._jump_cooldown = 10

        # Wall-jump if sliding on a wall
        if wall_sliding and self._jump_cooldown == 0:
            jump_pressed = True
            self._jump_cooldown = 8
            # Wall-jump: release direction toward wall, push opposite
            return InputState(
                right=(touching_wall == "left"),
                left=(touching_wall == "right"),
                jump_pressed=jump_pressed,
                jump_held=True,
            )

        # Jump if on ground and moving slowly (approaching obstacle)
        if on_ground and abs(vy) < 0.1 and self._jump_cooldown == 0:
            if tick % 30 == 0:  # periodic jump to clear gaps
                jump_pressed = True
                jump_held = True
                self._jump_cooldown = 15

        # Double-jump if falling and have jumps available
        if not on_ground and vy > 3.0 and jumps > 0 and self._jump_cooldown == 0:
            jump_pressed = True
            jump_held = True
            self._jump_cooldown = 12

        return InputState(
            right=True,
            jump_pressed=jump_pressed,
            jump_held=jump_held or jump_pressed,
        )

    def _decide_cautious(
        self, x: float, vy: float, on_ground: bool, wall_sliding: bool,
        touching_wall: str, jumps: int, tick: int,
    ) -> InputState:
        """Cautious: move slowly, jump carefully."""
        jump_pressed = False
        jump_held = False

        # Only jump when on ground and stable
        if on_ground and self._jump_cooldown == 0 and tick % 45 == 0:
            jump_pressed = True
            jump_held = True
            self._jump_cooldown = 20

        # Wall-jump only if stuck for a long time
        if wall_sliding and self._frames_at_same_x > 20 and self._jump_cooldown == 0:
            jump_pressed = True
            self._jump_cooldown = 15
            return InputState(
                right=(touching_wall == "left"),
                left=(touching_wall == "right"),
                jump_pressed=jump_pressed,
                jump_held=True,
            )

        # Move right at half speed (alternate frames)
        move_right = (tick % 3 != 0)

        return InputState(
            right=move_right,
            jump_pressed=jump_pressed,
            jump_held=jump_held or jump_pressed,
        )

    def _decide_explorer(
        self, x: float, vy: float, on_ground: bool, wall_sliding: bool,
        touching_wall: str, jumps: int, tick: int,
    ) -> InputState:
        """Explorer: move right, try wall-jumps and double-jumps."""
        jump_pressed = False
        jump_held = False

        # Jump periodically
        if on_ground and self._jump_cooldown == 0 and tick % 25 == 0:
            jump_pressed = True
            jump_held = True
            self._jump_cooldown = 12

        # Wall-jump eagerly (explorer likes to wall-jump)
        if wall_sliding and self._jump_cooldown == 0:
            jump_pressed = True
            self._jump_cooldown = 10
            return InputState(
                right=(touching_wall == "left"),
                left=(touching_wall == "right"),
                jump_pressed=jump_pressed,
                jump_held=True,
            )

        # Try double-jump in the air
        if not on_ground and jumps > 0 and self._jump_cooldown == 0:
            if tick % 15 == 0:
                jump_pressed = True
                jump_held = True
                self._jump_cooldown = 15

        return InputState(
            right=True,
            jump_pressed=jump_pressed,
            jump_held=jump_held or jump_pressed,
        )

    def _decide_aggressive(
        self, x: float, vy: float, on_ground: bool, wall_sliding: bool,
        touching_wall: str, jumps: int, tick: int,
    ) -> InputState:
        """Aggressive: move fast, wall-jump whenever possible."""
        jump_pressed = False
        jump_held = False

        # Jump frequently
        if on_ground and self._jump_cooldown == 0 and tick % 20 == 0:
            jump_pressed = True
            jump_held = True
            self._jump_cooldown = 10

        # Wall-jump immediately whenever touching a wall
        if wall_sliding and self._jump_cooldown == 0:
            jump_pressed = True
            self._jump_cooldown = 6
            return InputState(
                right=(touching_wall == "left"),
                left=(touching_wall == "right"),
                jump_pressed=jump_pressed,
                jump_held=True,
            )

        # Double-jump aggressively
        if not on_ground and jumps > 0 and self._jump_cooldown == 0:
            jump_pressed = True
            jump_held = True
            self._jump_cooldown = 8

        return InputState(
            right=True,
            jump_pressed=jump_pressed,
            jump_held=jump_held or jump_pressed,
        )


# =============================================================================
# Cognitive Simulation Runner
# =============================================================================

class CognitiveSimulationRunner:
    """
    Runs a complete AI-driven game simulation that integrates the physics
    engine, cognitive engine, fusion layer, adaptive director, and skill
    forge into a single coherent loop.

    Thread-safe singleton: use get_instance() to access.
    """

    _instance: Optional["CognitiveSimulationRunner"] = None
    _instance_lock = threading.Lock()

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._state: SimulationState = SimulationState.IDLE
        self._strategy: PlayerStrategy = PlayerStrategy.SPEEDRUN
        self._controller: VirtualPlayerController = VirtualPlayerController(self._strategy)

        # Subsystems
        self._physics: PhysicsWorld = PhysicsWorld.get_instance()
        self._fusion: CognitiveFusionLayer = CognitiveFusionLayer.get_instance()
        self._engine: CognitiveGameEngine = CognitiveGameEngine.get_instance()
        self._director: AdaptivePhysicsDirector = AdaptivePhysicsDirector.get_instance()
        self._forge: CognitiveSkillForge = CognitiveSkillForge.get_instance()

        # Simulation parameters
        self._max_ticks: int = 600  # 10 seconds at 60fps
        self._goal_x: float = 1500.0  # reach right side of level
        self._death_y: float = 600.0  # fell off the world

        # Telemetry
        self._current_tick: int = 0
        self._frames: List[SimulationFrame] = []
        self._max_frames: int = 600
        self._last_result: Optional[SimulationResult] = None
        self._total_duration_s: float = 0.0

        # Metrics accumulators
        self._total_jumps: int = 0
        self._total_wall_slides: int = 0
        self._total_wall_jumps: int = 0
        self._total_collisions: int = 0
        self._total_deaths: int = 0
        self._total_actions_planned: int = 0
        self._total_actions_executed: int = 0
        self._total_skills_extracted: int = 0
        self._total_physics_adaptations: int = 0
        self._confidence_sum: float = 0.0
        self._flow_distribution: Dict[str, int] = {}
        self._max_x: float = 0.0
        self._max_height: float = 0.0
        self._prev_wall_sliding: bool = False

    @classmethod
    def get_instance(cls) -> "CognitiveSimulationRunner":
        with cls._instance_lock:
            if cls._instance is None:
                cls._instance = cls()
            return cls._instance

    # ---- Lifecycle ----

    def configure(
        self,
        strategy: str = "speedrun",
        max_ticks: int = 600,
        goal_x: float = 1500.0,
    ) -> None:
        """Configure the simulation parameters."""
        with self._lock:
            try:
                self._strategy = PlayerStrategy(strategy)
            except ValueError:
                self._strategy = PlayerStrategy.SPEEDRUN
            self._controller = VirtualPlayerController(self._strategy)
            self._max_ticks = max(60, min(max_ticks, 3600))
            self._goal_x = goal_x

    def start(self) -> Dict[str, Any]:
        """Start a new simulation run."""
        with self._lock:
            self._reset_state()
            self._state = SimulationState.RUNNING

            # Reset all subsystems
            self._physics.load_default_scene()
            self._physics.start()
            self._fusion.reset()
            self._fusion.start()

            return {
                "status": "started",
                "strategy": self._strategy.value,
                "max_ticks": self._max_ticks,
                "goal_x": self._goal_x,
            }

    def pause(self) -> Dict[str, Any]:
        self._state = SimulationState.PAUSED
        return {"status": "paused", "tick": self._current_tick}

    def resume(self) -> Dict[str, Any]:
        if self._state == SimulationState.PAUSED:
            self._state = SimulationState.RUNNING
        return {"status": "resumed", "tick": self._current_tick}

    def stop(self) -> Dict[str, Any]:
        """Stop the simulation and return the final result."""
        self._state = SimulationState.COMPLETED
        result = self._build_result(completed=False)
        self._last_result = result
        return {"status": "stopped", "result": result.__dict__}

    def reset(self) -> Dict[str, Any]:
        """Reset the simulation to idle state."""
        with self._lock:
            self._reset_state()
            self._physics.load_default_scene()
            self._physics.start()
            self._fusion.reset()
            self._state = SimulationState.IDLE
        return {"status": "reset"}

    def _reset_state(self) -> None:
        self._current_tick = 0
        self._frames.clear()
        self._total_duration_s = 0.0
        self._total_jumps = 0
        self._total_wall_slides = 0
        self._total_wall_jumps = 0
        self._total_collisions = 0
        self._total_deaths = 0
        self._total_actions_planned = 0
        self._total_actions_executed = 0
        self._total_skills_extracted = 0
        self._total_physics_adaptations = 0
        self._confidence_sum = 0.0
        self._flow_distribution.clear()
        self._max_x = 0.0
        self._max_height = 0.0
        self._prev_wall_sliding = False
        self._controller = VirtualPlayerController(self._strategy)

    # ---- Simulation Step ----

    def step(self) -> Dict[str, Any]:
        """Run one simulation frame. Returns the frame telemetry."""
        if self._state != SimulationState.RUNNING:
            return {"status": self._state.value, "message": "Simulation not running"}

        frame_start = time.time()

        # 1. Get current player state from physics
        player = self._physics.get_player()
        if player is None:
            self._state = SimulationState.FAILED
            return {"status": "failed", "message": "No player body in physics world"}

        player_x = player.position.x
        player_y = player.position.y
        player_vx = player.velocity.x
        player_vy = player.velocity.y
        on_ground = player.on_ground
        wall_sliding = player.is_wall_sliding
        touching_wall = player.touching_wall
        jumps_remaining = player.jumps_remaining

        # 2. Check win/lose conditions
        if player_x >= self._goal_x:
            self._state = SimulationState.COMPLETED
            result = self._build_result(completed=True)
            self._last_result = result
            return {"status": "completed", "result": result.__dict__}

        if player_y > self._death_y:
            self._total_deaths += 1
            # Respawn: reset player position
            player.position.x = 100.0
            player.position.y = 464.0
            player.velocity.x = 0.0
            player.velocity.y = 0.0
            player.on_ground = True
            player.jumps_remaining = player.max_jumps

        # 3. Virtual player decides input
        input_state = self._controller.decide_input(
            player_x=player_x,
            player_y=player_y,
            player_vx=player_vx,
            player_vy=player_vy,
            on_ground=on_ground,
            wall_sliding=wall_sliding,
            touching_wall=touching_wall,
            jumps_remaining=jumps_remaining,
            tick=self._current_tick,
        )

        # Track jumps and wall-jumps
        if input_state.jump_pressed:
            self._total_jumps += 1
            if wall_sliding:
                self._total_wall_jumps += 1

        # Track wall-slide frames
        if wall_sliding:
            self._total_wall_slides += 1

        # Track wall-jump transition (was sliding, now jumping)
        if self._prev_wall_sliding and input_state.jump_pressed:
            pass  # already counted above
        self._prev_wall_sliding = wall_sliding

        # 4. Step physics with the virtual player's input
        physics_result = self._physics.step(input_state=input_state)

        # 5. Run cognitive fusion tick (observes state, takes actions)
        fusion_result = self._fusion.fused_tick(dt=1.0 / 60.0)

        # 6. Update metrics
        self._total_collisions += physics_result.collisions
        self._total_actions_planned += fusion_result.actions_planned
        self._total_actions_executed += fusion_result.actions_executed
        self._confidence_sum += fusion_result.confidence
        if fusion_result.skill_extracted:
            self._total_skills_extracted += 1
        if fusion_result.physics_adapted:
            self._total_physics_adaptations += 1

        flow = fusion_result.flow_state
        self._flow_distribution[flow] = self._flow_distribution.get(flow, 0) + 1

        # Track progress
        if player_x > self._max_x:
            self._max_x = player_x
        # Height is negative-Y (up), so lower Y = higher
        if player_y < self._max_height or self._max_height == 0.0:
            if player_y > 0:
                self._max_height = player_y

        # 7. Build frame telemetry
        duration_s = time.time() - frame_start
        self._total_duration_s += duration_s

        frame = SimulationFrame(
            tick=self._current_tick,
            player_x=player_x,
            player_y=player_y,
            player_vx=player_vx,
            player_vy=player_vy,
            on_ground=on_ground,
            wall_sliding=wall_sliding,
            jumps_remaining=jumps_remaining,
            input_left=input_state.left,
            input_right=input_state.right,
            input_jump=input_state.jump_pressed,
            collisions=physics_result.collisions,
            cognitive_phase=fusion_result.cognitive_phase,
            actions_planned=fusion_result.actions_planned,
            actions_executed=fusion_result.actions_executed,
            confidence=fusion_result.confidence,
            flow_state=flow,
            skill_estimate=fusion_result.skill_estimate,
            target_difficulty=fusion_result.target_difficulty,
            physics_adapted=fusion_result.physics_adapted,
            skill_extracted=fusion_result.skill_extracted,
            duration_s=duration_s,
        )
        self._frames.append(frame)
        if len(self._frames) > self._max_frames:
            self._frames = self._frames[-self._max_frames:]

        self._current_tick += 1

        # 8. Check if max ticks reached
        if self._current_tick >= self._max_ticks:
            self._state = SimulationState.COMPLETED
            result = self._build_result(completed=False)
            self._last_result = result
            return {"status": "completed", "result": result.__dict__}

        return {
            "status": "running",
            "frame": frame.__dict__,
        }

    def step_batch(self, count: int = 60) -> Dict[str, Any]:
        """Run multiple simulation frames. Returns summary telemetry."""
        count = max(1, min(count, 600))
        frames: List[Dict[str, Any]] = []

        for _ in range(count):
            result = self.step()
            if result["status"] != "running":
                return {
                    "status": result["status"],
                    "frames_run": len(frames),
                    "result": result.get("result"),
                    "frames": frames[-10:],  # last 10 frames
                }
            if "frame" in result:
                frames.append(result["frame"])

        return {
            "status": "running",
            "frames_run": len(frames),
            "frames": frames[-10:],  # last 10 frames
            "current_tick": self._current_tick,
        }

    # ---- Build Result ----

    def _build_result(self, completed: bool) -> SimulationResult:
        """Build the final simulation result from accumulated telemetry."""
        player = self._physics.get_player()
        final_x = player.position.x if player else 0.0
        final_y = player.position.y if player else 0.0

        # Sample trajectory (every 10th frame to keep payload small)
        trajectory = [
            {"x": f.player_x, "y": f.player_y, "tick": f.tick}
            for f in self._frames[::10]
        ]

        avg_confidence = (
            self._confidence_sum / self._current_tick
            if self._current_tick > 0 else 0.0
        )
        avg_frame_duration = (
            self._total_duration_s / self._current_tick
            if self._current_tick > 0 else 0.0
        )

        return SimulationResult(
            strategy=self._strategy.value,
            total_ticks=self._current_tick,
            completed=completed,
            final_x=final_x,
            final_y=final_y,
            max_x=self._max_x,
            max_height=self._max_height,
            total_collisions=self._total_collisions,
            total_jumps=self._total_jumps,
            total_wall_slides=self._total_wall_slides,
            total_wall_jumps=self._total_wall_jumps,
            total_deaths=self._total_deaths,
            total_actions_planned=self._total_actions_planned,
            total_actions_executed=self._total_actions_executed,
            total_skills_extracted=self._total_skills_extracted,
            total_physics_adaptations=self._total_physics_adaptations,
            avg_confidence=avg_confidence,
            flow_distribution=dict(self._flow_distribution),
            final_skill_estimate=self._director.status().get("skill_estimate", 0.5),
            final_target_difficulty=self._director.status().get("target_difficulty", 0.5),
            total_duration_s=self._total_duration_s,
            avg_frame_duration_s=avg_frame_duration,
            trajectory=trajectory,
        )

    # ---- Query ----

    def status(self) -> Dict[str, Any]:
        """Get the current simulation status."""
        player = self._physics.get_player()
        return {
            "state": self._state.value,
            "strategy": self._strategy.value,
            "current_tick": self._current_tick,
            "max_ticks": self._max_ticks,
            "goal_x": self._goal_x,
            "player": {
                "x": player.position.x if player else 0.0,
                "y": player.position.y if player else 0.0,
                "vx": player.velocity.x if player else 0.0,
                "vy": player.velocity.y if player else 0.0,
                "on_ground": player.on_ground if player else False,
                "wall_sliding": player.is_wall_sliding if player else False,
                "jumps_remaining": player.jumps_remaining if player else 0,
            },
            "metrics": {
                "total_jumps": self._total_jumps,
                "total_wall_slides": self._total_wall_slides,
                "total_wall_jumps": self._total_wall_jumps,
                "total_collisions": self._total_collisions,
                "total_deaths": self._total_deaths,
                "total_actions_planned": self._total_actions_planned,
                "total_actions_executed": self._total_actions_executed,
                "total_skills_extracted": self._total_skills_extracted,
                "total_physics_adaptations": self._total_physics_adaptations,
                "max_x": self._max_x,
                "progress": (self._max_x / self._goal_x) if self._goal_x > 0 else 0.0,
            },
            "flow_distribution": dict(self._flow_distribution),
            "last_result": self._last_result.__dict__ if self._last_result else None,
        }

    def history(self, limit: int = 60) -> List[Dict[str, Any]]:
        """Get recent simulation frames."""
        limit = max(1, min(limit, self._max_frames))
        return [f.__dict__ for f in self._frames[-limit:]]

    def trajectory(self) -> List[Dict[str, float]]:
        """Get the full player trajectory."""
        return [
            {"x": f.player_x, "y": f.player_y, "tick": f.tick}
            for f in self._frames
        ]

    def last_result(self) -> Optional[Dict[str, Any]]:
        """Get the last completed simulation result."""
        return self._last_result.__dict__ if self._last_result else None


# =============================================================================
# Module-level accessor
# =============================================================================

def get_simulation_runner() -> CognitiveSimulationRunner:
    """Get the singleton CognitiveSimulationRunner instance."""
    return CognitiveSimulationRunner.get_instance()
