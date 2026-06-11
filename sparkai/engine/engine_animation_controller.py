"""
SparkLabs Engine - Animation Controller

An animation state machine system providing clip playback, blend
transitions, condition-based state flow, and runtime animation
instances for skeletal and sprite animations.

Architecture:
  EngineAnimationController (Singleton)
    |-- AnimationClip        — frame data with timing and playback mode
    |-- AnimationState       — named state referencing a clip with blend mode
    |-- AnimationParameter   — typed runtime parameter for transitions
    |-- AnimationTransition  — condition-gated transition between states
    |-- TransitionConditionData — single condition within a transition
    |-- AnimationInstance    — live playback instance tracking elapsed time
    |-- StateMachine         — state graph with parameters and transitions
    |-- AnimationEvent       — frame-anchored event trigger
"""

from __future__ import annotations

import math
import threading
import time as _time_module
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class AnimationBlendMode(str, Enum):
    """How an animation state blends with others."""
    OVERRIDE = "override"
    ADDITIVE = "additive"
    CROSSFADE = "crossfade"


class AnimationPlayMode(str, Enum):
    """Playback behaviour when a clip reaches its end."""
    ONCE = "once"
    LOOP = "loop"
    PINGPONG = "pingpong"
    CLAMP = "clamp"


class TransitionCondition(str, Enum):
    """Type of condition used to gate a state transition."""
    FINISHED = "finished"
    TIME_ELAPSED = "time-elapsed"
    PARAMETER = "parameter"
    EVENT = "event"
    FRAME_REACHED = "frame-reached"


class AnimationEventType(str, Enum):
    """When an animation event should fire."""
    FRAME = "frame"
    MARKER = "marker"
    START = "start"
    END = "end"


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------

@dataclass
class AnimationFrame:
    """A single frame within an animation clip."""
    frame_index: int = 0
    duration: float = 0.033
    sprite_id: str = ""
    uv_rect: Tuple[float, float, float, float] = (0.0, 0.0, 1.0, 1.0)
    pivot_x: float = 0.5
    pivot_y: float = 0.5
    event_triggers: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "frame_index": self.frame_index,
            "duration": self.duration,
            "sprite_id": self.sprite_id,
            "uv_rect": list(self.uv_rect),
            "pivot_x": self.pivot_x,
            "pivot_y": self.pivot_y,
            "event_triggers": list(self.event_triggers),
        }


@dataclass
class AnimationClip:
    """A sequence of frames forming a complete animation."""
    clip_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = "unnamed_clip"
    frames: List[AnimationFrame] = field(default_factory=list)
    fps: float = 30.0
    loop: bool = True
    play_mode: AnimationPlayMode = AnimationPlayMode.LOOP

    @property
    def total_duration(self) -> float:
        if not self.frames:
            return 0.0
        return sum(f.duration for f in self.frames)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "clip_id": self.clip_id,
            "name": self.name,
            "frame_count": len(self.frames),
            "fps": self.fps,
            "loop": self.loop,
            "play_mode": self.play_mode.value,
            "total_duration": round(self.total_duration, 4),
            "frames": [f.to_dict() for f in self.frames],
        }


@dataclass
class AnimationState:
    """A named state referencing an animation clip with blend settings."""
    state_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = "idle"
    clip_id: str = ""
    speed: float = 1.0
    blend_mode: AnimationBlendMode = AnimationBlendMode.OVERRIDE
    weight: float = 1.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "state_id": self.state_id,
            "name": self.name,
            "clip_id": self.clip_id,
            "speed": self.speed,
            "blend_mode": self.blend_mode.value,
            "weight": self.weight,
        }


@dataclass
class AnimationParameter:
    """A typed runtime parameter used in transition conditions."""
    param_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = "param"
    param_type: str = "float"
    value: Any = 0.0
    default_value: Any = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "param_id": self.param_id,
            "name": self.name,
            "param_type": self.param_type,
            "value": self.value,
            "default_value": self.default_value,
        }


@dataclass
class TransitionConditionData:
    """A single condition evaluated during transition checks."""
    condition_type: TransitionCondition = TransitionCondition.PARAMETER
    parameter_name: str = ""
    operator: str = "eq"
    compare_value: Any = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "condition_type": self.condition_type.value,
            "parameter_name": self.parameter_name,
            "operator": self.operator,
            "compare_value": self.compare_value,
        }


@dataclass
class AnimationTransition:
    """A directed edge between two animation states with conditions."""
    transition_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    from_state_id: str = ""
    to_state_id: str = ""
    conditions: List[TransitionConditionData] = field(default_factory=list)
    priority: int = 0
    duration: float = 0.2
    has_exit_time: bool = False
    exit_time: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "transition_id": self.transition_id,
            "from_state_id": self.from_state_id,
            "to_state_id": self.to_state_id,
            "conditions": [c.to_dict() for c in self.conditions],
            "priority": self.priority,
            "duration": self.duration,
            "has_exit_time": self.has_exit_time,
            "exit_time": self.exit_time,
        }


@dataclass
class AnimationInstance:
    """A live playback instance tracking elapsed time and blend state."""
    instance_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    state_machine_id: str = ""
    current_state_id: str = ""
    playback_time: float = 0.0
    speed: float = 1.0
    blend_weight: float = 1.0
    playing: bool = True
    elapsed: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "instance_id": self.instance_id,
            "state_machine_id": self.state_machine_id,
            "current_state_id": self.current_state_id,
            "playback_time": self.playback_time,
            "speed": self.speed,
            "blend_weight": self.blend_weight,
            "playing": self.playing,
            "elapsed": self.elapsed,
        }


@dataclass
class StateMachine:
    """A state graph containing states, transitions, and parameters."""
    machine_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = "default_machine"
    states: Dict[str, AnimationState] = field(default_factory=dict)
    transitions: List[AnimationTransition] = field(default_factory=list)
    parameters: Dict[str, AnimationParameter] = field(default_factory=dict)
    default_state_id: str = ""
    entry_state_id: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "machine_id": self.machine_id,
            "name": self.name,
            "state_count": len(self.states),
            "transition_count": len(self.transitions),
            "parameter_count": len(self.parameters),
            "default_state_id": self.default_state_id,
            "entry_state_id": self.entry_state_id,
            "states": [s.to_dict() for s in self.states.values()],
            "transitions": [t.to_dict() for t in self.transitions],
            "parameters": [p.to_dict() for p in self.parameters.values()],
        }


@dataclass
class AnimationEvent:
    """A named event anchored to a specific frame in a clip."""
    event_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    clip_id: str = ""
    frame_index: int = 0
    event_name: str = ""
    event_type: AnimationEventType = AnimationEventType.FRAME
    trigger_time: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": self.event_id,
            "clip_id": self.clip_id,
            "frame_index": self.frame_index,
            "event_name": self.event_name,
            "event_type": self.event_type.value,
            "trigger_time": self.trigger_time,
        }


# ---------------------------------------------------------------------------
# EngineAnimationController — Thread-Safe Singleton
# ---------------------------------------------------------------------------

class EngineAnimationController:
    """
    Central animation state machine orchestrator.

    Manages clips, state machines, runtime instances, transitions,
    and condition-based state flow. Thread-safe via reentrant lock.

    Usage:
        ctrl = get_animation_controller()
        clip = ctrl.create_clip("run", frames)
        sm = ctrl.create_state_machine("player")
        ctrl.add_state(sm.machine_id, AnimationState(name="run", clip_id=clip.clip_id))
        inst = ctrl.create_instance(sm.machine_id)
        ctrl.update_instance(inst.instance_id, 0.016)
    """

    _instance: Optional["EngineAnimationController"] = None
    _lock = threading.RLock()

    # ------------------------------------------------------------------
    # Singleton
    # ------------------------------------------------------------------

    def __new__(cls) -> "EngineAnimationController":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    instance = super().__new__(cls)
                    instance._initialized = False
                    cls._instance = instance
        return cls._instance

    @classmethod
    def get_instance(cls) -> "EngineAnimationController":
        """Return the singleton EngineAnimationController instance."""
        return cls()

    def __init__(self) -> None:
        if getattr(self, "_initialized", False):
            return
        self._initialized = True

        self._clips: Dict[str, AnimationClip] = {}
        self._machines: Dict[str, StateMachine] = {}
        self._instances: Dict[str, AnimationInstance] = {}
        self._events: Dict[str, Dict[str, AnimationEvent]] = {}
        self._pending_triggers: Dict[str, List[str]] = {}

        self._total_clips_created: int = 0
        self._total_machines_created: int = 0
        self._total_instances_created: int = 0

    # ------------------------------------------------------------------
    # Clip Management
    # ------------------------------------------------------------------

    def create_clip(
        self,
        name: str,
        frames: List[AnimationFrame],
        fps: float = 30.0,
        play_mode: AnimationPlayMode = AnimationPlayMode.LOOP,
    ) -> AnimationClip:
        """Create a new animation clip from a list of frames."""
        with self._lock:
            clip = AnimationClip(
                name=name,
                frames=list(frames),
                fps=fps,
                loop=(play_mode == AnimationPlayMode.LOOP or play_mode == AnimationPlayMode.PINGPONG),
                play_mode=play_mode,
            )
            self._clips[clip.clip_id] = clip
            self._events[clip.clip_id] = {}
            self._total_clips_created += 1
            return clip

    def get_clip_duration(self, clip_id: str) -> float:
        """Return the total duration of a clip in seconds."""
        clip = self._clips.get(clip_id)
        if clip is None:
            return 0.0
        return clip.total_duration

    # ------------------------------------------------------------------
    # State Machine Management
    # ------------------------------------------------------------------

    def create_state_machine(
        self,
        name: str,
        default_state: str = "idle",
    ) -> StateMachine:
        """Create a new animation state machine."""
        with self._lock:
            sm = StateMachine(
                name=name,
                default_state_id=default_state,
                entry_state_id=default_state,
            )
            self._machines[sm.machine_id] = sm
            self._pending_triggers[sm.machine_id] = []
            self._total_machines_created += 1
            return sm

    def add_state(self, machine_id: str, state: AnimationState) -> bool:
        """Add a state to a machine."""
        sm = self._machines.get(machine_id)
        if sm is None:
            return False
        sm.states[state.name] = state
        if not sm.entry_state_id:
            sm.entry_state_id = state.name
        if not sm.default_state_id:
            sm.default_state_id = state.name
        return True

    def add_transition(
        self, machine_id: str, transition: AnimationTransition,
    ) -> bool:
        """Add a transition to a machine."""
        sm = self._machines.get(machine_id)
        if sm is None:
            return False
        sm.transitions.append(transition)
        return True

    # ------------------------------------------------------------------
    # Parameter Management
    # ------------------------------------------------------------------

    def add_parameter(
        self, machine_id: str, param: AnimationParameter,
    ) -> bool:
        """Register a parameter on a state machine."""
        sm = self._machines.get(machine_id)
        if sm is None:
            return False
        sm.parameters[param.name] = param
        return True

    def set_parameter(
        self, machine_id: str, param_name: str, value: Any,
    ) -> bool:
        """Update a parameter value; triggers re-evaluation of transitions."""
        sm = self._machines.get(machine_id)
        if sm is None:
            return False
        param = sm.parameters.get(param_name)
        if param is None:
            return False
        param.value = value
        return True

    def get_parameter(self, machine_id: str, param_name: str) -> Any:
        """Retrieve the current value of a parameter."""
        sm = self._machines.get(machine_id)
        if sm is None:
            return None
        param = sm.parameters.get(param_name)
        if param is None:
            return None
        return param.value

    # ------------------------------------------------------------------
    # Instance Management
    # ------------------------------------------------------------------

    def create_instance(self, machine_id: str) -> Optional[AnimationInstance]:
        """Create a playback instance starting from the entry state."""
        sm = self._machines.get(machine_id)
        if sm is None:
            return None

        entry_name = sm.entry_state_id or sm.default_state_id
        entry_state = sm.states.get(entry_name)
        if entry_state is None:
            return None

        instance = AnimationInstance(
            state_machine_id=machine_id,
            current_state_id=entry_name,
        )
        self._instances[instance.instance_id] = instance
        self._total_instances_created += 1
        return instance

    def pause_instance(self, instance_id: str) -> bool:
        """Pause playback on an animation instance."""
        inst = self._instances.get(instance_id)
        if inst is None:
            return False
        inst.playing = False
        return True

    def resume_instance(self, instance_id: str) -> bool:
        """Resume playback on an animation instance."""
        inst = self._instances.get(instance_id)
        if inst is None:
            return False
        inst.playing = True
        return True

    def set_instance_speed(self, instance_id: str, speed: float) -> bool:
        """Set the playback speed multiplier for an instance."""
        inst = self._instances.get(instance_id)
        if inst is None:
            return False
        inst.speed = max(0.0, speed)
        return True

    # ------------------------------------------------------------------
    # Runtime Update
    # ------------------------------------------------------------------

    def update_instance(
        self, instance_id: str, delta_time: float,
    ) -> Optional[AnimationInstance]:
        """Advance playback by one frame, check transitions, handle blending."""
        inst = self._instances.get(instance_id)
        if inst is None:
            return None
        if not inst.playing:
            return inst

        dt = max(0.0, delta_time) * inst.speed
        inst.elapsed += dt

        sm = self._machines.get(inst.state_machine_id)
        if sm is None:
            return inst

        current_state = sm.states.get(inst.current_state_id)
        if current_state is None:
            return inst

        clip = self._clips.get(current_state.clip_id)
        if clip is None:
            return inst

        total = clip.total_duration
        if total <= 0.0:
            return inst

        inst.playback_time += dt

        # Handle clip-end behaviour
        if inst.playback_time >= total:
            if clip.play_mode == AnimationPlayMode.LOOP:
                inst.playback_time = inst.playback_time % total
            elif clip.play_mode == AnimationPlayMode.PINGPONG:
                # Ping-pong is handled by direction toggle externally;
                # for simplicity, wrap as loop but reverse is implicit.
                inst.playback_time = inst.playback_time % total
            elif clip.play_mode == AnimationPlayMode.CLAMP:
                inst.playback_time = total
            # ONCE: playback_time stays beyond total, indicating finished

        # Evaluate transitions
        transition = self.evaluate_transitions(sm.machine_id, inst.current_state_id, inst)
        if transition is not None:
            self.apply_transition(inst.instance_id, transition.transition_id, inst, sm)

        return inst

    def evaluate_transitions(
        self,
        machine_id: str,
        current_state_id: str,
        instance: AnimationInstance,
    ) -> Optional[AnimationTransition]:
        """Find the first eligible outgoing transition from the current state."""
        sm = self._machines.get(machine_id)
        if sm is None:
            return None

        current_state = sm.states.get(current_state_id)
        if current_state is None:
            return None

        clip = self._clips.get(current_state.clip_id)

        candidates = [
            t for t in sm.transitions
            if t.from_state_id == current_state_id
        ]
        candidates.sort(key=lambda t: -t.priority)

        for transition in candidates:
            if self._evaluate_transition_conditions(
                transition, sm.parameters, instance, current_state, clip,
            ):
                return transition

        return None

    def _evaluate_transition_conditions(
        self,
        transition: AnimationTransition,
        params: Dict[str, AnimationParameter],
        instance: AnimationInstance,
        current_state: AnimationState,
        clip: Optional[AnimationClip],
    ) -> bool:
        """Check whether all conditions on a transition are satisfied."""
        if not transition.conditions:
            return True

        for cond in transition.conditions:
            if not self._check_condition(cond, params, instance, current_state, clip):
                return False
        return True

    def _check_condition(
        self,
        condition: TransitionConditionData,
        params: Dict[str, AnimationParameter],
        instance: AnimationInstance,
        current_state: AnimationState,
        clip: Optional[AnimationClip],
    ) -> bool:
        """Evaluate a single TransitionConditionData."""
        if condition.condition_type == TransitionCondition.FINISHED:
            if clip is None:
                return False
            total = clip.total_duration
            if total <= 0.0:
                return True
            return instance.playback_time >= total

        elif condition.condition_type == TransitionCondition.TIME_ELAPSED:
            return instance.elapsed >= float(condition.compare_value or 0.0)

        elif condition.condition_type == TransitionCondition.PARAMETER:
            param = params.get(condition.parameter_name)
            if param is None:
                return False
            return self._compare_values(
                param.value,
                condition.operator,
                condition.compare_value,
            )

        elif condition.condition_type == TransitionCondition.EVENT:
            sm_id = instance.state_machine_id
            pending = self._pending_triggers.get(sm_id, [])
            return condition.parameter_name in pending

        elif condition.condition_type == TransitionCondition.FRAME_REACHED:
            if clip is None:
                return False
            target_frame = int(condition.compare_value or 0)
            return self._get_frame_index_at_time(clip, instance.playback_time) >= target_frame

        return False

    def apply_transition(
        self,
        instance_id: str,
        transition_id: str,
        instance: AnimationInstance,
        machine: StateMachine,
    ) -> bool:
        """Execute a transition, changing the current state."""
        transition = None
        for t in machine.transitions:
            if t.transition_id == transition_id:
                transition = t
                break
        if transition is None:
            return False

        to_state = machine.states.get(transition.to_state_id)
        if to_state is None:
            return False

        instance.current_state_id = transition.to_state_id
        instance.playback_time = 0.0

        # Clear consumed events from pending triggers
        trg_list = self._pending_triggers.get(machine.machine_id, [])
        for cond in transition.conditions:
            if cond.condition_type == TransitionCondition.EVENT:
                while cond.parameter_name in trg_list:
                    trg_list.remove(cond.parameter_name)

        return True

    # ------------------------------------------------------------------
    # Frame Query
    # ------------------------------------------------------------------

    def get_current_frame(self, instance_id: str) -> Optional[AnimationFrame]:
        """Get the frame to render based on the instance's playback time."""
        inst = self._instances.get(instance_id)
        if inst is None:
            return None

        sm = self._machines.get(inst.state_machine_id)
        if sm is None:
            return None

        state = sm.states.get(inst.current_state_id)
        if state is None:
            return None

        clip = self._clips.get(state.clip_id)
        if clip is None or not clip.frames:
            return None

        total = clip.total_duration
        if total <= 0.0:
            return clip.frames[0]

        t = inst.playback_time % max(total, 0.0001)
        accumulated = 0.0
        for frame in clip.frames:
            accumulated += frame.duration
            if t < accumulated:
                return frame

        # Clamped or finished — return last frame
        if clip.play_mode == AnimationPlayMode.CLAMP or clip.play_mode == AnimationPlayMode.ONCE:
            return clip.frames[-1]
        return clip.frames[0]

    @staticmethod
    def _get_frame_index_at_time(clip: AnimationClip, time: float) -> int:
        """Return the frame index at the given playback time."""
        if not clip.frames:
            return 0
        total = clip.total_duration
        if total <= 0.0:
            return 0
        t = time % total
        accumulated = 0.0
        for i, frame in enumerate(clip.frames):
            accumulated += frame.duration
            if t < accumulated:
                return frame.frame_index
        return clip.frames[-1].frame_index

    @staticmethod
    def _compare_values(left: Any, operator: str, right: Any) -> bool:
        """Compare two values using the given operator string."""
        try:
            if operator == "eq":
                return left == right
            elif operator == "neq":
                return left != right
            elif operator == "gt":
                return float(left) > float(right)
            elif operator == "gte":
                return float(left) >= float(right)
            elif operator == "lt":
                return float(left) < float(right)
            elif operator == "lte":
                return float(left) <= float(right)
        except (TypeError, ValueError):
            return False
        return False

    # ------------------------------------------------------------------
    # Events
    # ------------------------------------------------------------------

    def trigger_event(self, machine_id: str, event_name: str) -> bool:
        """Queue an event trigger on a state machine."""
        sm = self._machines.get(machine_id)
        if sm is None:
            return False
        self._pending_triggers.setdefault(machine_id, []).append(event_name)
        return True

    def add_event(self, clip_id: str, event: AnimationEvent) -> bool:
        """Register an animation event on a clip."""
        if clip_id not in self._clips:
            return False
        event.clip_id = clip_id
        self._events[clip_id][event.event_id] = event
        return True

    # ------------------------------------------------------------------
    # Stats
    # ------------------------------------------------------------------

    def get_animation_stats(self) -> Dict[str, Any]:
        """Return aggregate statistics about the animation system."""
        return {
            "clip_count": len(self._clips),
            "total_clips_created": self._total_clips_created,
            "machine_count": len(self._machines),
            "total_machines_created": self._total_machines_created,
            "active_instances": len(self._instances),
            "total_instances_created": self._total_instances_created,
        }

    # ------------------------------------------------------------------
    # Internal Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _get_state_by_name(
        machine: StateMachine, name: str,
    ) -> Optional[AnimationState]:
        """Look up a state by name within a machine."""
        return machine.states.get(name)

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def reset(self) -> None:
        """Remove all clips, machines, instances, and events."""
        with self._lock:
            self._clips.clear()
            self._machines.clear()
            self._instances.clear()
            self._events.clear()
            self._pending_triggers.clear()
            self._total_clips_created = 0
            self._total_machines_created = 0
            self._total_instances_created = 0


# ---------------------------------------------------------------------------
# Module-level Accessor
# ---------------------------------------------------------------------------

def get_animation_controller() -> EngineAnimationController:
    """Return the singleton EngineAnimationController instance."""
    return EngineAnimationController.get_instance()