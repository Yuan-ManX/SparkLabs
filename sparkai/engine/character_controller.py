"""
SparkLabs Engine - Character Controller System

Physics-integrated character movement and control system for
AI-native game entities. Provides configurable movement modes
including walking, running, jumping, crouching, and climbing
with acceleration curves, ground detection, and animation
state synchronization.

Architecture:
  CharacterController
    |-- MovementComponent (velocity, acceleration, drag)
    |-- JumpComponent (gravity, apex control, double-jump)
    |-- GroundDetector (raycast, slope handling, step offset)
    |-- RotationComponent (look direction, turn smoothing)
    |-- CollisionResponse (push-back, slide against walls)

Movement Modes:
  - IDLE: stationary
  - WALK: base movement speed with limited acceleration
  - RUN: increased speed with higher acceleration
  - CROUCH: reduced speed, lower collision profile
  - AIRBORNE: gravity-affected movement with limited control
  - CLIMBING: vertical surface traversal
"""

from __future__ import annotations

import math
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


class MovementMode(Enum):
    IDLE = "idle"
    WALK = "walk"
    RUN = "run"
    CROUCH = "crouch"
    AIRBORNE = "airborne"
    CLIMBING = "climbing"


class CollisionShape(Enum):
    CAPSULE = "capsule"
    BOX = "box"
    SPHERE = "sphere"
    CYLINDER = "cylinder"


@dataclass
class CharacterConfig:
    character_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    walk_speed: float = 3.5
    run_speed: float = 7.0
    crouch_speed: float = 1.5
    climb_speed: float = 2.0
    jump_force: float = 8.0
    gravity: float = 9.81
    max_fall_speed: float = -30.0
    collider_height: float = 1.8
    collider_radius: float = 0.35
    collider_shape: CollisionShape = CollisionShape.CAPSULE
    step_height: float = 0.3
    slope_limit: float = 45.0
    acceleration: float = 20.0
    deceleration: float = 15.0
    air_control: float = 0.3
    turn_smoothing: float = 10.0
    can_double_jump: bool = False
    can_crouch: bool = True
    can_climb: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "character_id": self.character_id,
            "walk_speed": self.walk_speed,
            "run_speed": self.run_speed,
            "jump_force": self.jump_force,
            "collider_shape": self.collider_shape.value,
        }


@dataclass
class CharacterState:
    character_id: str = ""
    position: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    velocity: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    rotation: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    mode: MovementMode = MovementMode.IDLE
    is_grounded: bool = True
    is_jumping: bool = False
    current_speed: float = 0.0
    horizontal_input: Tuple[float, float] = (0.0, 0.0)
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "character_id": self.character_id,
            "position": list(self.position),
            "velocity": list(self.velocity),
            "mode": self.mode.value,
            "grounded": self.is_grounded,
            "jumping": self.is_jumping,
            "speed": round(self.current_speed, 2),
        }


class CharacterController:
    _instance: Optional[CharacterController] = None

    @classmethod
    def get_instance(cls) -> CharacterController:
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self):
        self._configs: Dict[str, CharacterConfig] = {}
        self._states: Dict[str, CharacterState] = {}
        self._total_characters: int = 0

    def create_character(self, character_id: str, config: Optional[CharacterConfig] = None) -> CharacterState:
        cfg = config or CharacterConfig(character_id=character_id)
        self._configs[character_id] = cfg
        state = CharacterState(character_id=character_id, mode=MovementMode.IDLE, is_grounded=True)
        self._states[character_id] = state
        self._total_characters += 1
        return state

    def set_movement_input(self, character_id: str, horizontal: Tuple[float, float],
                           jump_pressed: bool = False, run_pressed: bool = False,
                           crouch_pressed: bool = False) -> Optional[CharacterState]:
        state = self._states.get(character_id)
        config = self._configs.get(character_id)
        if state is None or config is None:
            return None

        state.horizontal_input = horizontal

        if crouch_pressed and config.can_crouch and state.is_grounded:
            state.mode = MovementMode.CROUCH
        elif run_pressed and state.is_grounded and state.mode != MovementMode.CROUCH:
            state.mode = MovementMode.RUN
        elif state.is_grounded and state.mode not in (MovementMode.AIRBORNE, MovementMode.CLIMBING):
            state.mode = MovementMode.WALK

        if jump_pressed and state.is_grounded:
            state.velocity = (state.velocity[0], config.jump_force, state.velocity[2])
            state.mode = MovementMode.AIRBORNE
        elif jump_pressed and not state.is_grounded and config.can_double_jump and not state.is_jumping:
            state.velocity = (state.velocity[0], config.jump_force * 0.8, state.velocity[2])

        return state

    def update(self, character_id: str, delta_time: float,
               is_grounded: bool = True) -> Optional[CharacterState]:
        state = self._states.get(character_id)
        config = self._configs.get(character_id)
        if state is None or config is None:
            return None

        dt = max(0.001, delta_time)
        state.is_grounded = is_grounded

        target_speed = config.walk_speed
        if state.mode == MovementMode.RUN:
            target_speed = config.run_speed
        elif state.mode == MovementMode.CROUCH:
            target_speed = config.crouch_speed
        elif state.mode == MovementMode.CLIMBING:
            target_speed = config.climb_speed

        input_mag = math.sqrt(state.horizontal_input[0] ** 2 + state.horizontal_input[1] ** 2)
        if input_mag > 0.001 and state.mode != MovementMode.IDLE:
            control_factor = config.air_control if not state.is_grounded else 1.0
            state.current_speed += config.acceleration * dt * control_factor
        else:
            state.current_speed -= config.deceleration * dt

        state.current_speed = max(0.0, min(state.current_speed, target_speed))

        if not state.is_grounded:
            vy = state.velocity[1] - config.gravity * dt
            vy = max(vy, config.max_fall_speed)
            state.velocity = (state.velocity[0], vy, state.velocity[2])
            state.mode = MovementMode.AIRBORNE
        else:
            state.velocity = (state.velocity[0], 0.0, state.velocity[2])
            if state.mode == MovementMode.AIRBORNE:
                state.mode = MovementMode.IDLE

        move_x = state.horizontal_input[0] * state.current_speed * dt
        move_z = state.horizontal_input[1] * state.current_speed * dt
        state.position = (
            state.position[0] + move_x,
            state.position[1] + state.velocity[1] * dt,
            state.position[2] + move_z,
        )

        state.timestamp = time.time()
        return state

    def get_state(self, character_id: str) -> Optional[CharacterState]:
        return self._states.get(character_id)

    def remove_character(self, character_id: str):
        self._configs.pop(character_id, None)
        self._states.pop(character_id, None)

    def get_stats(self) -> Dict[str, Any]:
        return {
            "total_characters": self._total_characters,
            "active_characters": len(self._states),
            "mode_distribution": {
                mode.value: sum(1 for s in self._states.values() if s.mode == mode)
                for mode in MovementMode
            },
        }


def get_character_controller() -> CharacterController:
    return CharacterController.get_instance()