"""
SparkLabs Engine - Game Physics

A server-side 2D physics engine that mirrors the client-side JavaScript
physics in generated games. This enables the cognitive layer to simulate
game states, predict action outcomes, and test parameter changes before
applying them to live games.

Original SparkLabs design:
  1. Rigid Body Dynamics - Each body has position, velocity, acceleration,
     mass, restitution (bounciness), and friction coefficient. Forces
     are integrated using semi-implicit Euler for stability.
  2. AABB Collision - Axis-aligned bounding box collision detection
     with signed-distance resolution. Resolution separates bodies along
     the minimum penetration axis to avoid jitter.
  3. Wall-Slide - When a body touches a wall while falling, vertical
     velocity is capped to a wall-slide speed, enabling controlled
     descent. The body's facing direction tracks the wall side.
  4. Wall-Jump - A body that is wall-sliding can launch off the wall
     with a velocity vector pointing away from the wall and upward.
     A short input lock prevents the held direction from immediately
     canceling the wall-jump's outbound velocity.
  5. Coyote Time - A grace period after leaving a ledge during which
     the body can still jump, simulating forgiving game feel.
  6. Jump Buffer - A grace period before landing during which a jump
     press is queued and executed on landing.
  7. Variable Jump Height - Holding the jump key produces a taller jump;
     releasing it early cuts the upward velocity short.
  8. Deterministic - Given the same initial state and input sequence,
     the simulation produces identical results, enabling replay.

The physics engine is intentionally simple (no rotation, no joints) to
match the scope of 2D platformer/parkour/top-down games that SparkLabs
generates. It runs at a fixed timestep (default 1/60s) for determinism.
"""

from __future__ import annotations

import logging
import math
import threading
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


# =============================================================================
# Enums
# =============================================================================

class BodyType(Enum):
    """Type of physics body."""
    STATIC = "static"      # Immovable (walls, ground, platforms)
    DYNAMIC = "dynamic"    # Affected by gravity and collisions
    KINEMATIC = "kinematic"  # Moved manually, not by physics


class CollisionSide(Enum):
    """Which side of a body was hit in a collision."""
    NONE = "none"
    TOP = "top"
    BOTTOM = "bottom"
    LEFT = "left"
    RIGHT = "right"


class PhysicsState(Enum):
    """High-level state of the physics world."""
    IDLE = "idle"
    RUNNING = "running"
    PAUSED = "paused"
    STEPPING = "stepping"


# =============================================================================
# Data Structures
# =============================================================================

@dataclass
class Vector2:
    """A 2D vector."""
    x: float = 0.0
    y: float = 0.0

    def __add__(self, other: "Vector2") -> "Vector2":
        return Vector2(self.x + other.x, self.y + other.y)

    def __sub__(self, other: "Vector2") -> "Vector2":
        return Vector2(self.x - other.x, self.y - other.y)

    def __mul__(self, scalar: float) -> "Vector2":
        return Vector2(self.x * scalar, self.y * scalar)

    def magnitude(self) -> float:
        return math.sqrt(self.x * self.x + self.y * self.y)

    def normalized(self) -> "Vector2":
        mag = self.magnitude()
        if mag < 1e-9:
            return Vector2(0.0, 0.0)
        return Vector2(self.x / mag, self.y / mag)

    def to_dict(self) -> Dict[str, float]:
        return {"x": self.x, "y": self.y}


@dataclass
class AABB:
    """Axis-aligned bounding box."""
    x: float
    y: float
    width: float
    height: float

    @property
    def left(self) -> float:
        return self.x

    @property
    def right(self) -> float:
        return self.x + self.width

    @property
    def top(self) -> float:
        return self.y

    @property
    def bottom(self) -> float:
        return self.y + self.height

    @property
    def center(self) -> Vector2:
        return Vector2(self.x + self.width / 2, self.y + self.height / 2)

    def intersects(self, other: "AABB") -> bool:
        """Check if two AABBs overlap."""
        return (
            self.left < other.right
            and self.right > other.left
            and self.top < other.bottom
            and self.bottom > other.top
        )

    def penetration(self, other: "AABB") -> Tuple[float, CollisionSide]:
        """
        Compute penetration depth and side for collision resolution.
        Returns (depth, side) where side is the side of `self` that was hit.
        """
        if not self.intersects(other):
            return (0.0, CollisionSide.NONE)

        # Compute overlaps on each axis
        overlap_left = self.right - other.left      # self is to the left of other
        overlap_right = other.right - self.left     # self is to the right of other
        overlap_top = self.bottom - other.top       # self is above other
        overlap_bottom = other.bottom - self.top    # self is below other

        # Find minimum penetration axis
        min_x = min(overlap_left, overlap_right)
        min_y = min(overlap_top, overlap_bottom)

        if min_x < min_y:
            # Horizontal collision
            if overlap_left < overlap_right:
                return (overlap_left, CollisionSide.RIGHT)  # self's right hit other's left
            else:
                return (overlap_right, CollisionSide.LEFT)  # self's left hit other's right
        else:
            # Vertical collision
            if overlap_top < overlap_bottom:
                return (overlap_top, CollisionSide.BOTTOM)  # self's bottom hit other's top
            else:
                return (overlap_bottom, CollisionSide.TOP)  # self's top hit other's bottom


@dataclass
class RigidBody:
    """A rigid body in the physics world."""
    body_id: str
    body_type: BodyType = BodyType.DYNAMIC
    position: Vector2 = field(default_factory=Vector2)
    velocity: Vector2 = field(default_factory=Vector2)
    acceleration: Vector2 = field(default_factory=Vector2)
    width: float = 32.0
    height: float = 32.0
    mass: float = 1.0
    restitution: float = 0.2          # bounciness (0 = no bounce, 1 = perfect bounce)
    friction: float = 0.85            # multiplicative friction (1 = no friction)
    # Player-specific state
    is_player: bool = False
    on_ground: bool = False
    facing: int = 1                   # -1 (left) or 1 (right)
    # Wall-slide state
    touching_wall: CollisionSide = CollisionSide.NONE
    is_wall_sliding: bool = False
    # Jump state
    coyote_timer: float = 0.0         # seconds remaining
    jump_buffer_timer: float = 0.0    # seconds remaining
    wall_jump_lock: float = 0.0       # seconds remaining
    jumps_remaining: int = 0
    max_jumps: int = 1
    jump_held: bool = False           # whether jump key is currently held
    # Tags for filtering
    tags: List[str] = field(default_factory=list)

    @property
    def aabb(self) -> AABB:
        return AABB(self.position.x, self.position.y, self.width, self.height)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "body_id": self.body_id,
            "body_type": self.body_type.value,
            "position": self.position.to_dict(),
            "velocity": self.velocity.to_dict(),
            "width": self.width,
            "height": self.height,
            "mass": self.mass,
            "is_player": self.is_player,
            "on_ground": self.on_ground,
            "facing": self.facing,
            "touching_wall": self.touching_wall.value,
            "is_wall_sliding": self.is_wall_sliding,
            "coyote_timer": self.coyote_timer,
            "jump_buffer_timer": self.jump_buffer_timer,
            "wall_jump_lock": self.wall_jump_lock,
            "jumps_remaining": self.jumps_remaining,
            "tags": list(self.tags),
        }


@dataclass
class PhysicsConfig:
    """Configuration for the physics world."""
    gravity: float = 0.55
    jump_strength: float = 11.0
    move_speed: float = 4.2
    wall_slide_speed: float = 2.0
    wall_jump_kickback: float = 6.0
    wall_jump_lock_frames: int = 10
    coyote_frames: int = 6
    jump_buffer_frames: int = 6
    can_wall_jump: bool = True
    can_double_jump: bool = False
    variable_jump_cutoff: float = 0.5  # velocity multiplier when jump released early
    air_control: float = 0.6
    ground_friction: float = 0.75
    air_friction: float = 0.95
    fixed_timestep: float = 1.0 / 60.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "gravity": self.gravity,
            "jump_strength": self.jump_strength,
            "move_speed": self.move_speed,
            "wall_slide_speed": self.wall_slide_speed,
            "wall_jump_kickback": self.wall_jump_kickback,
            "can_wall_jump": self.can_wall_jump,
            "can_double_jump": self.can_double_jump,
            "coyote_frames": self.coyote_frames,
            "jump_buffer_frames": self.jump_buffer_frames,
            "fixed_timestep": self.fixed_timestep,
        }


@dataclass
class InputState:
    """Player input for a single physics step."""
    left: bool = False
    right: bool = False
    jump_pressed: bool = False   # edge-detected (just pressed this frame)
    jump_held: bool = False      # currently held
    up: bool = False
    down: bool = False
    shoot: bool = False


@dataclass
class CollisionEvent:
    """Recorded collision event for telemetry."""
    body_a_id: str
    body_b_id: str
    side: CollisionSide
    penetration: float
    tick: int


@dataclass
class PhysicsStepResult:
    """Result of a single physics step."""
    tick: int
    duration_s: float
    collisions: int = 0
    bodies_moved: int = 0
    player_on_ground: bool = False
    player_wall_sliding: bool = False
    player_velocity: Optional[Vector2] = None


# =============================================================================
# Physics World
# =============================================================================

class PhysicsWorld:
    """
    A 2D physics world with AABB collision, wall-slide, wall-jump,
    coyote time, and jump buffer. Runs at a fixed timestep for
    deterministic simulation.

    Thread-safe singleton: use get_instance() to access.
    """

    _instance: Optional["PhysicsWorld"] = None
    _instance_lock = threading.Lock()

    def __init__(self, config: Optional[PhysicsConfig] = None) -> None:
        self._lock = threading.RLock()
        self._config: PhysicsConfig = config or PhysicsConfig()
        self._bodies: Dict[str, RigidBody] = {}
        self._state: PhysicsState = PhysicsState.IDLE
        self._tick: int = 0
        self._total_duration_s: float = 0.0
        self._collision_history: List[CollisionEvent] = []
        self._max_collision_history = 128
        self._step_history: List[PhysicsStepResult] = []
        self._max_step_history = 64
        self._world_bounds: Optional[AABB] = None

    @classmethod
    def get_instance(cls) -> "PhysicsWorld":
        with cls._instance_lock:
            if cls._instance is None:
                cls._instance = cls()
            return cls._instance

    # ---- Configuration ----

    @property
    def config(self) -> PhysicsConfig:
        return self._config

    def configure(self, config: PhysicsConfig) -> None:
        with self._lock:
            self._config = config

    def set_world_bounds(self, x: float, y: float, width: float, height: float) -> None:
        with self._lock:
            self._world_bounds = AABB(x, y, width, height)

    # ---- Body Management ----

    def add_body(self, body: RigidBody) -> None:
        with self._lock:
            self._bodies[body.body_id] = body

    def remove_body(self, body_id: str) -> None:
        with self._lock:
            self._bodies.pop(body_id, None)

    def get_body(self, body_id: str) -> Optional[RigidBody]:
        with self._lock:
            return self._bodies.get(body_id)

    def get_player(self) -> Optional[RigidBody]:
        with self._lock:
            for body in self._bodies.values():
                if body.is_player:
                    return body
            return None

    def list_bodies(self, body_type: Optional[BodyType] = None) -> List[RigidBody]:
        with self._lock:
            if body_type is None:
                return list(self._bodies.values())
            return [b for b in self._bodies.values() if b.body_type == body_type]

    # ---- Default Scene ----

    def load_default_scene(self) -> None:
        """Load a default platformer scene for testing."""
        with self._lock:
            self._bodies.clear()
            # Ground
            self._bodies["ground"] = RigidBody(
                body_id="ground",
                body_type=BodyType.STATIC,
                position=Vector2(0, 500),
                width=1600, height=40,
                tags=["terrain", "ground"],
            )
            # Walls for wall-slide/wall-jump (positioned so the player can reach
            # them by jumping: wall_left to the left of player, wall_right to the right)
            self._bodies["wall_left"] = RigidBody(
                body_id="wall_left",
                body_type=BodyType.STATIC,
                position=Vector2(20, 350),
                width=28, height=150,
                tags=["terrain", "wall"],
            )
            self._bodies["wall_right"] = RigidBody(
                body_id="wall_right",
                body_type=BodyType.STATIC,
                position=Vector2(800, 350),
                width=28, height=150,
                tags=["terrain", "wall"],
            )
            # Platform
            self._bodies["platform"] = RigidBody(
                body_id="platform",
                body_type=BodyType.STATIC,
                position=Vector2(400, 400),
                width=120, height=18,
                tags=["terrain", "platform"],
            )
            # Player - starts on the ground (y = ground_top - player_height = 500 - 36 = 464)
            player_max_jumps = 2 if self._config.can_double_jump else 1
            self._bodies["player"] = RigidBody(
                body_id="player",
                body_type=BodyType.DYNAMIC,
                position=Vector2(100, 464),
                width=28, height=36,
                is_player=True,
                on_ground=True,
                max_jumps=player_max_jumps,
                jumps_remaining=player_max_jumps,
                tags=["player"],
            )
            # Enemy - starts on the ground
            self._bodies["enemy_1"] = RigidBody(
                body_id="enemy_1",
                body_type=BodyType.DYNAMIC,
                position=Vector2(600, 472),
                width=28, height=28,
                mass=0.5,
                on_ground=True,
                tags=["enemy"],
            )
            # World bounds keep bodies inside the playable area
            self._world_bounds = AABB(0, 0, 1600, 540)
            self._state = PhysicsState.IDLE
            self._tick = 0

    # ---- Lifecycle ----

    def start(self) -> None:
        with self._lock:
            self._state = PhysicsState.RUNNING

    def pause(self) -> None:
        with self._lock:
            self._state = PhysicsState.PAUSED

    def resume(self) -> None:
        with self._lock:
            if self._state == PhysicsState.PAUSED:
                self._state = PhysicsState.RUNNING

    def reset(self) -> None:
        with self._lock:
            self._bodies.clear()
            self._state = PhysicsState.IDLE
            self._tick = 0
            self._total_duration_s = 0.0
            self._collision_history.clear()
            self._step_history.clear()

    # ---- Physics Step ----

    def step(self, dt: Optional[float] = None, input_state: Optional[InputState] = None) -> PhysicsStepResult:
        """
        Advance the physics simulation by one fixed timestep.
        Returns a PhysicsStepResult with telemetry.
        """
        start_time = time.time()
        with self._lock:
            if self._state not in (PhysicsState.RUNNING, PhysicsState.STEPPING):
                result = PhysicsStepResult(
                    tick=self._tick, duration_s=0.0,
                )
                return result
            self._tick += 1
            current_tick = self._tick

        timestep = dt or self._config.fixed_timestep
        inp = input_state or InputState()

        # Step 1: Apply player input
        player = self.get_player()
        if player is not None:
            self._apply_player_input(player, inp, timestep)

        # Step 2: Apply gravity to dynamic bodies
        with self._lock:
            for body in self._bodies.values():
                if body.body_type == BodyType.DYNAMIC:
                    self._apply_gravity(body, timestep)

        # Step 3: Integrate velocity into position
        bodies_moved = 0
        with self._lock:
            for body in self._bodies.values():
                if body.body_type == BodyType.DYNAMIC:
                    body.position.x += body.velocity.x
                    body.position.y += body.velocity.y
                    bodies_moved += 1

        # Step 4: Collision detection and resolution
        collision_count = 0
        with self._lock:
            dynamic_bodies = [b for b in self._bodies.values() if b.body_type == BodyType.DYNAMIC]
            static_bodies = [b for b in self._bodies.values() if b.body_type == BodyType.STATIC]

            for body in dynamic_bodies:
                # Reset collision state
                body.on_ground = False
                body.touching_wall = CollisionSide.NONE

                # Check against static bodies
                for static_body in static_bodies:
                    if body.aabb.intersects(static_body.aabb):
                        depth, side = body.aabb.penetration(static_body.aabb)
                        if side != CollisionSide.NONE:
                            self._resolve_collision(body, static_body, side, depth)
                            collision_count += 1
                            # Record collision event
                            if len(self._collision_history) < self._max_collision_history:
                                self._collision_history.append(CollisionEvent(
                                    body_a_id=body.body_id,
                                    body_b_id=static_body.body_id,
                                    side=side,
                                    penetration=depth,
                                    tick=current_tick,
                                ))
                            # Update body state based on collision side
                            if side == CollisionSide.BOTTOM:
                                body.on_ground = True
                            elif side in (CollisionSide.LEFT, CollisionSide.RIGHT):
                                body.touching_wall = side

                # Check world bounds
                if self._world_bounds is not None:
                    self._resolve_world_bounds(body)

        # Step 5: Update wall-slide state
        if player is not None:
            self._update_wall_slide(player, timestep)

        # Step 6: Update player timers
        if player is not None:
            self._update_player_timers(player, inp, timestep)

        duration_s = time.time() - start_time
        with self._lock:
            self._total_duration_s += duration_s

        result = PhysicsStepResult(
            tick=current_tick,
            duration_s=duration_s,
            collisions=collision_count,
            bodies_moved=bodies_moved,
            player_on_ground=player.on_ground if player else False,
            player_wall_sliding=player.is_wall_sliding if player else False,
            player_velocity=player.velocity if player else None,
        )

        with self._lock:
            self._step_history.append(result)
            if len(self._step_history) > self._max_step_history:
                self._step_history = self._step_history[-self._max_step_history:]

        return result

    def _apply_player_input(self, player: RigidBody, inp: InputState, dt: float) -> None:
        """Apply player input to the player body."""
        config = self._config

        # Wall-jump lock: skip horizontal input override
        if player.wall_jump_lock > 0:
            player.wall_jump_lock -= dt
            # Keep wall-jump's outbound velocity
        else:
            # Horizontal movement
            if inp.left:
                player.velocity.x = -config.move_speed
                player.facing = -1
            elif inp.right:
                player.velocity.x = config.move_speed
                player.facing = 1
            else:
                # Apply friction
                friction = config.ground_friction if player.on_ground else config.air_friction
                player.velocity.x *= friction

        # Jump buffer: record jump press for later consumption
        if inp.jump_pressed:
            player.jump_buffer_timer = config.jump_buffer_frames * dt

        # Coyote time: refresh while grounded, decay when airborne
        if player.on_ground:
            player.coyote_timer = config.coyote_frames * dt
            player.jumps_remaining = player.max_jumps
        elif player.coyote_timer > 0:
            player.coyote_timer -= dt

        # Consume jump buffer
        if player.jump_buffer_timer > 0:
            player.jump_buffer_timer -= dt
            # Jump from ground or coyote time
            if player.coyote_timer > 0:
                player.velocity.y = -config.jump_strength
                player.on_ground = False
                player.coyote_timer = 0
                player.jump_buffer_timer = 0
                player.jumps_remaining = player.max_jumps - 1
            # Wall-jump
            elif config.can_wall_jump and player.is_wall_sliding:
                player.velocity.y = -config.jump_strength * 0.9
                player.velocity.x = -player.facing * config.wall_jump_kickback
                player.wall_jump_lock = config.wall_jump_lock_frames * dt
                player.jump_buffer_timer = 0
                player.jumps_remaining = player.max_jumps - 1
                player.is_wall_sliding = False
            # Double-jump
            elif config.can_double_jump and player.jumps_remaining > 0:
                player.velocity.y = -config.jump_strength * 0.85
                player.jumps_remaining -= 1
                player.jump_buffer_timer = 0

        # Variable jump height: cut upward velocity when jump released
        if not inp.jump_held and player.velocity.y < 0:
            player.velocity.y *= config.variable_jump_cutoff

    def _apply_gravity(self, body: RigidBody, dt: float) -> None:
        """Apply gravity to a dynamic body."""
        config = self._config
        if config.gravity <= 0:
            return

        # Wall-slide reduces fall speed
        if body.is_player and body.is_wall_sliding and body.velocity.y > config.wall_slide_speed:
            # Cap fall speed to wall-slide speed
            body.velocity.y = config.wall_slide_speed
        else:
            body.velocity.y += config.gravity

    def _resolve_collision(
        self, body: RigidBody, other: RigidBody,
        side: CollisionSide, depth: float,
    ) -> None:
        """Resolve a collision by separating the dynamic body from the static body."""
        if side == CollisionSide.TOP:
            # Body hit other from above (body's top penetrated other's bottom)
            body.position.y += depth
            body.velocity.y = max(0, body.velocity.y)  # stop upward velocity
        elif side == CollisionSide.BOTTOM:
            # Body hit other from below (body's bottom penetrated other's top)
            body.position.y -= depth
            body.velocity.y = min(0, body.velocity.y)  # stop downward velocity
            body.on_ground = True
        elif side == CollisionSide.LEFT:
            # Body's left hit other's right
            body.position.x += depth
            body.velocity.x = max(0, body.velocity.x)
        elif side == CollisionSide.RIGHT:
            # Body's right hit other's left
            body.position.x -= depth
            body.velocity.x = min(0, body.velocity.x)

    def _resolve_world_bounds(self, body: RigidBody) -> None:
        """Keep body within world bounds."""
        if self._world_bounds is None:
            return
        bounds = self._world_bounds
        if body.position.x < bounds.left:
            body.position.x = bounds.left
            body.velocity.x = max(0, body.velocity.x)
        if body.position.x + body.width > bounds.right:
            body.position.x = bounds.right - body.width
            body.velocity.x = min(0, body.velocity.x)
        if body.position.y < bounds.top:
            body.position.y = bounds.top
            body.velocity.y = max(0, body.velocity.y)
        if body.position.y + body.height > bounds.bottom:
            body.position.y = bounds.bottom - body.height
            body.velocity.y = min(0, body.velocity.y)
            body.on_ground = True

    def _update_wall_slide(self, player: RigidBody, dt: float) -> None:
        """Update wall-slide state based on touching wall and falling."""
        config = self._config
        if not config.can_wall_jump:
            player.is_wall_sliding = False
            return

        # Wall-slide when touching a wall and falling
        if (player.touching_wall in (CollisionSide.LEFT, CollisionSide.RIGHT)
                and not player.on_ground
                and player.velocity.y > 0):
            player.is_wall_sliding = True
        else:
            player.is_wall_sliding = False

    def _update_player_timers(self, player: RigidBody, inp: InputState, dt: float) -> None:
        """Update player-specific timers."""
        # Decay jump buffer
        if player.jump_buffer_timer > 0:
            player.jump_buffer_timer = max(0, player.jump_buffer_timer - dt)
        # Decay coyote timer
        if player.coyote_timer > 0 and not player.on_ground:
            player.coyote_timer = max(0, player.coyote_timer - dt)
        # Decay wall-jump lock
        if player.wall_jump_lock > 0:
            player.wall_jump_lock = max(0, player.wall_jump_lock - dt)

    # ---- Simulation Helpers ----

    def simulate(self, ticks: int, input_sequence: Optional[List[InputState]] = None) -> List[PhysicsStepResult]:
        """
        Run the simulation for N ticks. If input_sequence is provided,
        it must have at least N entries; otherwise default input is used.
        """
        results: List[PhysicsStepResult] = []
        for i in range(ticks):
            inp = input_sequence[i] if input_sequence and i < len(input_sequence) else InputState()
            result = self.step(input_state=inp)
            results.append(result)
        return results

    def predict_trajectory(
        self, body_id: str, ticks: int = 60,
        input_state: Optional[InputState] = None,
    ) -> List[Vector2]:
        """
        Predict the trajectory of a body for N ticks without modifying
        the actual world state. Returns a list of positions.
        """
        # Save current state
        with self._lock:
            body = self._bodies.get(body_id)
            if body is None:
                return []
            saved_pos = Vector2(body.position.x, body.position.y)
            saved_vel = Vector2(body.velocity.x, body.velocity.y)
            saved_state = self._state
            self._state = PhysicsState.STEPPING

        # Run simulation
        positions: List[Vector2] = []
        inp = input_state or InputState()
        for _ in range(ticks):
            self.step(input_state=inp)
            with self._lock:
                b = self._bodies.get(body_id)
                if b is not None:
                    positions.append(Vector2(b.position.x, b.position.y))

        # Restore state
        with self._lock:
            body = self._bodies.get(body_id)
            if body is not None:
                body.position = saved_pos
                body.velocity = saved_vel
            self._state = saved_state

        return positions

    # ---- Status & Telemetry ----

    def status(self) -> Dict[str, Any]:
        with self._lock:
            player = None
            for b in self._bodies.values():
                if b.is_player:
                    player = b
                    break
            return {
                "state": self._state.value,
                "tick": self._tick,
                "body_count": len(self._bodies),
                "dynamic_count": sum(1 for b in self._bodies.values() if b.body_type == BodyType.DYNAMIC),
                "static_count": sum(1 for b in self._bodies.values() if b.body_type == BodyType.STATIC),
                "config": self._config.to_dict(),
                "player": player.to_dict() if player else None,
                "total_duration_s": self._total_duration_s,
                "avg_step_duration_s": (
                    self._total_duration_s / max(1, self._tick)
                ),
                "collision_history_size": len(self._collision_history),
                "last_collision": {
                    "body_a": self._collision_history[-1].body_a_id,
                    "body_b": self._collision_history[-1].body_b_id,
                    "side": self._collision_history[-1].side.value,
                    "tick": self._collision_history[-1].tick,
                } if self._collision_history else None,
                "last_step": {
                    "tick": self._step_history[-1].tick,
                    "collisions": self._step_history[-1].collisions,
                    "bodies_moved": self._step_history[-1].bodies_moved,
                    "player_on_ground": self._step_history[-1].player_on_ground,
                    "player_wall_sliding": self._step_history[-1].player_wall_sliding,
                    "duration_s": self._step_history[-1].duration_s,
                } if self._step_history else None,
            }

    def list_bodies_dict(self, body_type: Optional[BodyType] = None) -> List[Dict[str, Any]]:
        with self._lock:
            return [b.to_dict() for b in self.list_bodies(body_type)]

    def collision_history(self, limit: int = 10) -> List[Dict[str, Any]]:
        with self._lock:
            return [
                {
                    "body_a": e.body_a_id,
                    "body_b": e.body_b_id,
                    "side": e.side.value,
                    "penetration": e.penetration,
                    "tick": e.tick,
                } for e in self._collision_history[-limit:]
            ]

    def step_history(self, limit: int = 10) -> List[Dict[str, Any]]:
        with self._lock:
            return [
                {
                    "tick": r.tick,
                    "collisions": r.collisions,
                    "bodies_moved": r.bodies_moved,
                    "player_on_ground": r.player_on_ground,
                    "player_wall_sliding": r.player_wall_sliding,
                    "duration_s": r.duration_s,
                } for r in self._step_history[-limit:]
            ]


# =============================================================================
# Module-Level Convenience
# =============================================================================

def get_physics_world() -> PhysicsWorld:
    """Get the singleton PhysicsWorld instance."""
    return PhysicsWorld.get_instance()


def step_physics(input_state: Optional[InputState] = None) -> PhysicsStepResult:
    """Run one physics step on the singleton world."""
    return get_physics_world().step(input_state=input_state)
