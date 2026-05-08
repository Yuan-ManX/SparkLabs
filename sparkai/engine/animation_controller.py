"""
SparkLabs Engine - Animation Controller

Animation state machine and blend tree system for the
SparkLabs AI-native game engine. Provides a node-based
animation controller with state transitions, parameter-driven
blending, and layered animation masks. AI agents can define
complex animation behaviors through a declarative graph API
that maps game state to animation output.

Architecture:
  AnimationController
    |-- AnimState (named state with clip + transition rules)
    |-- Transition (condition-based state switching)
    |-- BlendTree (parameter-driven pose blending)
    |-- AnimLayer (weighted animation layering with masks)
    |-- AnimParameter (float, int, bool, trigger types)
    |-- AnimClip (named animation with loop/ping-pong modes)
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple


class AnimParameterType(Enum):
    FLOAT = "float"
    INT = "int"
    BOOL = "bool"
    TRIGGER = "trigger"


class AnimConditionMode(Enum):
    GREATER = "greater"
    LESS = "less"
    EQUALS = "equals"
    NOT_EQUALS = "not_equals"
    GREATER_OR_EQUAL = "greater_or_equal"
    LESS_OR_EQUAL = "less_or_equal"


class AnimClipMode(Enum):
    ONCE = "once"
    LOOP = "loop"
    PING_PONG = "ping_pong"
    CLAMP_FOREVER = "clamp_forever"


class BlendTreeType(Enum):
    SIMPLE_1D = "simple_1d"
    SIMPLE_2D_DIRECTIONAL = "simple_2d_directional"
    SIMPLE_2D_FREEFORM = "simple_2d_freeform"


@dataclass
class AnimParameter:
    name: str
    param_type: AnimParameterType = AnimParameterType.FLOAT
    default_float: float = 0.0
    default_int: int = 0
    default_bool: bool = False

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "type": self.param_type.value,
            "value": self.get_value(),
        }

    def get_value(self) -> Any:
        if self.param_type == AnimParameterType.FLOAT:
            return self.default_float
        elif self.param_type == AnimParameterType.INT:
            return self.default_int
        elif self.param_type == AnimParameterType.BOOL:
            return self.default_bool
        return None


@dataclass
class AnimClip:
    clip_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    name: str = "clip"
    duration: float = 1.0
    mode: AnimClipMode = AnimClipMode.LOOP
    speed: float = 1.0
    start_frame: int = 0
    end_frame: int = 0
    frame_rate: float = 30.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def total_frames(self) -> int:
        if self.end_frame > self.start_frame:
            return self.end_frame - self.start_frame
        return int(self.duration * self.frame_rate)

    def to_dict(self) -> dict:
        return {
            "clip_id": self.clip_id,
            "name": self.name,
            "duration": self.duration,
            "mode": self.mode.value,
            "speed": self.speed,
            "total_frames": self.total_frames,
        }


@dataclass
class AnimCondition:
    parameter: str
    mode: AnimConditionMode = AnimConditionMode.EQUALS
    threshold_float: float = 0.0
    threshold_int: int = 0
    threshold_bool: bool = False
    parameter_type: AnimParameterType = AnimParameterType.FLOAT

    def evaluate(self, value: Any) -> bool:
        if self.parameter_type == AnimParameterType.FLOAT:
            threshold = self.threshold_float
            val = float(value) if value is not None else 0.0
        elif self.parameter_type == AnimParameterType.INT:
            threshold = self.threshold_int
            val = int(value) if value is not None else 0
        elif self.parameter_type == AnimParameterType.BOOL:
            return bool(value) == self.threshold_bool
        else:
            return True

        if self.mode == AnimConditionMode.GREATER:
            return val > threshold
        elif self.mode == AnimConditionMode.LESS:
            return val < threshold
        elif self.mode == AnimConditionMode.EQUALS:
            return val == threshold
        elif self.mode == AnimConditionMode.NOT_EQUALS:
            return val != threshold
        elif self.mode == AnimConditionMode.GREATER_OR_EQUAL:
            return val >= threshold
        elif self.mode == AnimConditionMode.LESS_OR_EQUAL:
            return val <= threshold
        return True

    def to_dict(self) -> dict:
        return {
            "parameter": self.parameter,
            "mode": self.mode.value,
            "threshold": self.threshold_float if self.parameter_type == AnimParameterType.FLOAT else self.threshold_int,
        }


@dataclass
class Transition:
    transition_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    from_state: str = ""
    to_state: str = ""
    conditions: List[AnimCondition] = field(default_factory=list)
    duration: float = 0.2
    exit_time: float = 0.0
    has_exit_time: bool = False
    priority: int = 0

    def evaluate(self, parameters: Dict[str, Any]) -> bool:
        if not self.conditions:
            return True
        return all(
            condition.evaluate(parameters.get(condition.parameter))
            for condition in self.conditions
        )

    def to_dict(self) -> dict:
        return {
            "transition_id": self.transition_id,
            "from": self.from_state,
            "to": self.to_state,
            "duration": self.duration,
            "priority": self.priority,
            "conditions": [c.to_dict() for c in self.conditions],
        }


@dataclass
class AnimState:
    state_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    name: str = "state"
    clip: Optional[AnimClip] = None
    speed: float = 1.0
    is_default: bool = False
    transitions: List[Transition] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)

    def add_transition(self, transition: Transition) -> Transition:
        self.transitions.append(transition)
        return transition

    def to_dict(self) -> dict:
        return {
            "state_id": self.state_id,
            "name": self.name,
            "clip": self.clip.to_dict() if self.clip else None,
            "speed": self.speed,
            "is_default": self.is_default,
            "transitions": [t.to_dict() for t in self.transitions],
            "tags": self.tags,
        }


@dataclass
class BlendTreeNode:
    node_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    name: str = "node"
    weight: float = 1.0
    clip: Optional[AnimClip] = None
    child_tree: Optional["BlendTree"] = None

    def to_dict(self) -> dict:
        return {
            "node_id": self.node_id,
            "name": self.name,
            "weight": self.weight,
            "clip": self.clip.to_dict() if self.clip else None,
        }


@dataclass
class BlendTree:
    tree_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    name: str = "blend_tree"
    tree_type: BlendTreeType = BlendTreeType.SIMPLE_1D
    blend_parameter: str = ""
    blend_parameter_y: str = ""
    nodes: List[BlendTreeNode] = field(default_factory=list)
    min_threshold: float = 0.0
    max_threshold: float = 1.0

    def add_node(self, node: BlendTreeNode) -> BlendTreeNode:
        self.nodes.append(node)
        return node

    def to_dict(self) -> dict:
        return {
            "tree_id": self.tree_id,
            "name": self.name,
            "type": self.tree_type.value,
            "blend_parameter": self.blend_parameter,
            "nodes": [n.to_dict() for n in self.nodes],
        }


@dataclass
class AnimLayer:
    layer_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    name: str = "layer"
    weight: float = 1.0
    mask: Optional[Set[str]] = None
    blending_mode: str = "override"
    states: List[AnimState] = field(default_factory=list)
    default_state: Optional[str] = None

    def add_state(self, state: AnimState) -> AnimState:
        self.states.append(state)
        if state.is_default or self.default_state is None:
            self.default_state = state.name
        return state

    def to_dict(self) -> dict:
        return {
            "layer_id": self.layer_id,
            "name": self.name,
            "weight": self.weight,
            "blending_mode": self.blending_mode,
            "states": [s.to_dict() for s in self.states],
            "default_state": self.default_state,
        }


class AnimationController:
    """
    Animation state machine and blend tree controller.

    Provides a node-based animation control system where AI
    agents define states, transitions, and blend trees to
    create complex animation behaviors. Parameters drive
    transitions between states and control blend tree weights.
    Multiple layers can be stacked with masks for partial
    animation overrides (e.g., upper body aiming while
    lower body runs).
    """

    _instance: Optional["AnimationController"] = None

    def __init__(self):
        self._clip_library: Dict[str, AnimClip] = {}
        self._layers: Dict[str, AnimLayer] = {}
        self._parameters: Dict[str, AnimParameter] = {}
        self._blend_trees: Dict[str, BlendTree] = {}
        self._active_states: Dict[str, str] = {}
        self._trigger_consumed: Set[str] = set()
        self._elapsed: float = 0.0

    @classmethod
    def get_instance(cls) -> "AnimationController":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def create_clip(
        self,
        name: str,
        duration: float = 1.0,
        mode: AnimClipMode = AnimClipMode.LOOP,
        speed: float = 1.0,
        **kwargs,
    ) -> AnimClip:
        clip = AnimClip(name=name, duration=duration, mode=mode, speed=speed, **kwargs)
        self._clip_library[clip.clip_id] = clip
        return clip

    def get_clip(self, clip_id: str) -> Optional[AnimClip]:
        return self._clip_library.get(clip_id)

    def create_parameter(self, name: str, param_type: AnimParameterType = AnimParameterType.FLOAT, **kwargs) -> AnimParameter:
        param = AnimParameter(name=name, param_type=param_type, **kwargs)
        self._parameters[name] = param
        return param

    def set_float(self, name: str, value: float) -> None:
        if name in self._parameters:
            self._parameters[name].default_float = value

    def set_int(self, name: str, value: int) -> None:
        if name in self._parameters:
            self._parameters[name].default_int = value

    def set_bool(self, name: str, value: bool) -> None:
        if name in self._parameters:
            self._parameters[name].default_bool = value

    def set_trigger(self, name: str) -> None:
        if name in self._parameters:
            self._parameters[name].default_bool = True

    def get_parameter_value(self, name: str) -> Any:
        param = self._parameters.get(name)
        return param.get_value() if param else None

    def create_layer(self, name: str, weight: float = 1.0) -> AnimLayer:
        layer = AnimLayer(name=name, weight=weight)
        self._layers[layer.layer_id] = layer
        return layer

    def create_state(
        self,
        name: str,
        layer: Optional[AnimLayer] = None,
        clip: Optional[AnimClip] = None,
        is_default: bool = False,
    ) -> AnimState:
        state = AnimState(name=name, clip=clip, is_default=is_default)
        if layer:
            layer.add_state(state)
        return state

    def create_transition(
        self,
        from_state: str,
        to_state: str,
        duration: float = 0.2,
        conditions: Optional[List[AnimCondition]] = None,
    ) -> Transition:
        transition = Transition(
            from_state=from_state,
            to_state=to_state,
            duration=duration,
            conditions=conditions or [],
        )
        return transition

    def create_condition(
        self,
        parameter: str,
        mode: AnimConditionMode = AnimConditionMode.EQUALS,
        threshold: Any = 0.0,
    ) -> AnimCondition:
        param = self._parameters.get(parameter)
        param_type = param.param_type if param else AnimParameterType.FLOAT
        condition = AnimCondition(
            parameter=parameter,
            mode=mode,
            parameter_type=param_type,
        )
        if param_type == AnimParameterType.FLOAT:
            condition.threshold_float = float(threshold)
        elif param_type == AnimParameterType.INT:
            condition.threshold_int = int(threshold)
        elif param_type == AnimParameterType.BOOL:
            condition.threshold_bool = bool(threshold)
        return condition

    def create_blend_tree(
        self,
        name: str,
        tree_type: BlendTreeType = BlendTreeType.SIMPLE_1D,
        blend_parameter: str = "",
    ) -> BlendTree:
        tree = BlendTree(name=name, tree_type=tree_type, blend_parameter=blend_parameter)
        self._blend_trees[tree.tree_id] = tree
        return tree

    def update(self, delta_time: float) -> None:
        self._elapsed += delta_time
        param_values = {
            name: param.get_value()
            for name, param in self._parameters.items()
        }

        for layer_id, layer in self._layers.items():
            current_state_name = self._active_states.get(layer_id, layer.default_state)
            if not current_state_name:
                continue

            for state in layer.states:
                if state.name != current_state_name:
                    continue
                for transition in state.transitions:
                    if transition.evaluate(param_values):
                        self._active_states[layer_id] = transition.to_state
                        break
                break

        self._trigger_consumed.clear()

    def get_active_clips(self) -> Dict[str, Optional[AnimClip]]:
        result = {}
        for layer_id, layer in self._layers.items():
            state_name = self._active_states.get(layer_id, layer.default_state)
            if not state_name:
                continue
            for state in layer.states:
                if state.name == state_name:
                    result[layer_id] = state.clip
                    break
        return result

    def get_active_state_names(self) -> Dict[str, str]:
        return {
            layer.name: self._active_states.get(layer_id, layer.default_state or "none")
            for layer_id, layer in self._layers.items()
        }

    def get_clip_progress(self, clip: AnimClip) -> float:
        if clip.duration <= 0:
            return 1.0
        raw = (self._elapsed * clip.speed) % clip.duration
        progress = raw / clip.duration
        if clip.mode == AnimClipMode.PING_PONG:
            cycle = int(raw / clip.duration)
            if cycle % 2 == 1:
                progress = 1.0 - progress
        return progress

    def get_stats(self) -> dict:
        return {
            "clips": len(self._clip_library),
            "parameters": len(self._parameters),
            "layers": len(self._layers),
            "blend_trees": len(self._blend_trees),
            "active_states": self.get_active_state_names(),
            "elapsed": self._elapsed,
        }

    def reset(self) -> None:
        self._clip_library.clear()
        self._layers.clear()
        self._parameters.clear()
        self._blend_trees.clear()
        self._active_states.clear()
        self._trigger_consumed.clear()
        self._elapsed = 0.0


def get_animation_controller() -> AnimationController:
    return AnimationController.get_instance()
