"""
SparkLabs ECS - Built-in Components

Core components that provide fundamental game engine capabilities:
- Transform: Position, rotation, scale in 2D/3D space
- Renderable: Visual representation data
- PhysicsBody: Rigid body physics properties
- Collider: Collision shape data
- Camera: View projection
- AudioSource: Sound playback
- Animator: Animation state
- InputReceiver: Input mapping
- AIBrain: AI agent integration for autonomous entities
- Script: Custom behavior scripts
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from sparkai.engine.ecs.component import Component, component


@component
class Transform(Component):
    component_type: str = "transform"

    def __init__(self, **kwargs: Any):
        super().__init__(**kwargs)
        self.x: float = kwargs.get("x", 0.0)
        self.y: float = kwargs.get("y", 0.0)
        self.z: float = kwargs.get("z", 0.0)
        self.rotation_x: float = kwargs.get("rotation_x", 0.0)
        self.rotation_y: float = kwargs.get("rotation_y", 0.0)
        self.rotation_z: float = kwargs.get("rotation_z", 0.0)
        self.scale_x: float = kwargs.get("scale_x", 1.0)
        self.scale_y: float = kwargs.get("scale_y", 1.0)
        self.scale_z: float = kwargs.get("scale_z", 1.0)
        self.origin_x: float = kwargs.get("origin_x", 0.0)
        self.origin_y: float = kwargs.get("origin_y", 0.0)
        self.anchor_x: float = kwargs.get("anchor_x", 0.0)
        self.anchor_y: float = kwargs.get("anchor_y", 0.0)
        self.skew_x: float = kwargs.get("skew_x", 0.0)
        self.skew_y: float = kwargs.get("skew_y", 0.0)

    @property
    def position(self) -> List[float]:
        return [self.x, self.y, self.z]

    @position.setter
    def position(self, value: List[float]) -> None:
        self.x, self.y, self.z = value[0], value[1], value[2] if len(value) > 2 else 0.0

    @property
    def rotation(self) -> List[float]:
        return [self.rotation_x, self.rotation_y, self.rotation_z]

    @rotation.setter
    def rotation(self, value: List[float]) -> None:
        self.rotation_x = value[0]
        self.rotation_y = value[1] if len(value) > 1 else 0.0
        self.rotation_z = value[2] if len(value) > 2 else 0.0

    @property
    def scale(self) -> List[float]:
        return [self.scale_x, self.scale_y, self.scale_z]

    @scale.setter
    def scale(self, value: List[float]) -> None:
        self.scale_x = value[0]
        self.scale_y = value[1] if len(value) > 1 else 1.0
        self.scale_z = value[2] if len(value) > 2 else 1.0

    def translate(self, dx: float, dy: float, dz: float = 0.0) -> None:
        self.x += dx
        self.y += dy
        self.z += dz

    def rotate(self, dx: float, dy: float = 0.0, dz: float = 0.0) -> None:
        self.rotation_x += dx
        self.rotation_y += dy
        self.rotation_z += dz

    def set_position(self, x: float, y: float, z: float = 0.0) -> None:
        self.x, self.y, self.z = x, y, z

    def distance_to(self, other: "Transform") -> float:
        return (
            (self.x - other.x) ** 2
            + (self.y - other.y) ** 2
            + (self.z - other.z) ** 2
        ) ** 0.5


@component
class Renderable(Component):
    component_type: str = "renderable"

    def __init__(self, **kwargs: Any):
        super().__init__(**kwargs)
        self.visible: bool = kwargs.get("visible", True)
        self.opacity: float = kwargs.get("opacity", 1.0)
        self.z_index: int = kwargs.get("z_index", 0)
        self.render_layer: str = kwargs.get("render_layer", "default")
        self.shader: str = kwargs.get("shader", "default")
        self.material: str = kwargs.get("material", "default")
        self.color: List[float] = kwargs.get("color", [1.0, 1.0, 1.0, 1.0])
        self.blend_mode: str = kwargs.get("blend_mode", "normal")
        self.width: float = kwargs.get("width", 0.0)
        self.height: float = kwargs.get("height", 0.0)


@component
class SpriteRenderer(Component):
    component_type: str = "sprite_renderer"

    def __init__(self, **kwargs: Any):
        super().__init__(**kwargs)
        self.sprite_resource: str = kwargs.get("sprite_resource", "")
        self.flip_x: bool = kwargs.get("flip_x", False)
        self.flip_y: bool = kwargs.get("flip_y", False)
        self.source_x: float = kwargs.get("source_x", 0.0)
        self.source_y: float = kwargs.get("source_y", 0.0)
        self.source_width: float = kwargs.get("source_width", 0.0)
        self.source_height: float = kwargs.get("source_height", 0.0)


@component
class TextRenderer(Component):
    component_type: str = "text_renderer"

    def __init__(self, **kwargs: Any):
        super().__init__(**kwargs)
        self.text: str = kwargs.get("text", "")
        self.font_family: str = kwargs.get("font_family", "Arial")
        self.font_size: float = kwargs.get("font_size", 16.0)
        self.font_weight: str = kwargs.get("font_weight", "normal")
        self.color: List[float] = kwargs.get("color", [1.0, 1.0, 1.0, 1.0])
        self.alignment: str = kwargs.get("alignment", "left")
        self.line_height: float = kwargs.get("line_height", 1.2)
        self.max_width: float = kwargs.get("max_width", 0.0)
        self.word_wrap: bool = kwargs.get("word_wrap", False)


@component
class PhysicsBody(Component):
    component_type: str = "physics_body"

    def __init__(self, **kwargs: Any):
        super().__init__(**kwargs)
        self.body_type: str = kwargs.get("body_type", "dynamic")
        self.mass: float = kwargs.get("mass", 1.0)
        self.friction: float = kwargs.get("friction", 0.3)
        self.restitution: float = kwargs.get("restitution", 0.2)
        self.velocity_x: float = kwargs.get("velocity_x", 0.0)
        self.velocity_y: float = kwargs.get("velocity_y", 0.0)
        self.velocity_z: float = kwargs.get("velocity_z", 0.0)
        self.angular_velocity: float = kwargs.get("angular_velocity", 0.0)
        self.gravity_scale: float = kwargs.get("gravity_scale", 1.0)
        self.linear_damping: float = kwargs.get("linear_damping", 0.0)
        self.angular_damping: float = kwargs.get("angular_damping", 0.0)
        self.fixed_rotation: bool = kwargs.get("fixed_rotation", False)
        self.is_sensor: bool = kwargs.get("is_sensor", False)

    @property
    def velocity(self) -> List[float]:
        return [self.velocity_x, self.velocity_y, self.velocity_z]

    @velocity.setter
    def velocity(self, value: List[float]) -> None:
        self.velocity_x = value[0]
        self.velocity_y = value[1] if len(value) > 1 else 0.0
        self.velocity_z = value[2] if len(value) > 2 else 0.0

    def apply_force(self, fx: float, fy: float, fz: float = 0.0) -> None:
        if self.mass > 0:
            self.velocity_x += fx / self.mass
            self.velocity_y += fy / self.mass
            self.velocity_z += fz / self.mass

    def apply_impulse(self, ix: float, iy: float, iz: float = 0.0) -> None:
        self.velocity_x += ix
        self.velocity_y += iy
        self.velocity_z += iz


@component
class Collider(Component):
    component_type: str = "collider"

    def __init__(self, **kwargs: Any):
        super().__init__(**kwargs)
        self.collider_type: str = kwargs.get("collider_type", "box")
        self.offset_x: float = kwargs.get("offset_x", 0.0)
        self.offset_y: float = kwargs.get("offset_y", 0.0)
        self.width: float = kwargs.get("width", 1.0)
        self.height: float = kwargs.get("height", 1.0)
        self.radius: float = kwargs.get("radius", 0.5)
        self.is_trigger: bool = kwargs.get("is_trigger", False)
        self.collision_layer: int = kwargs.get("collision_layer", 1)
        self.collision_mask: int = kwargs.get("collision_mask", 1)


@component
class Camera(Component):
    component_type: str = "camera"

    def __init__(self, **kwargs: Any):
        super().__init__(**kwargs)
        self.projection: str = kwargs.get("projection", "perspective")
        self.fov: float = kwargs.get("fov", 60.0)
        self.near_clip: float = kwargs.get("near_clip", 0.1)
        self.far_clip: float = kwargs.get("far_clip", 1000.0)
        self.viewport_width: float = kwargs.get("viewport_width", 1.0)
        self.viewport_height: float = kwargs.get("viewport_height", 1.0)
        self.orthographic_size: float = kwargs.get("orthographic_size", 10.0)
        self.clear_color: List[float] = kwargs.get("clear_color", [0.0, 0.0, 0.0, 1.0])
        self.priority: int = kwargs.get("priority", 0)
        self.is_main: bool = kwargs.get("is_main", False)


@component
class AudioSource(Component):
    component_type: str = "audio_source"

    def __init__(self, **kwargs: Any):
        super().__init__(**kwargs)
        self.clip_resource: str = kwargs.get("clip_resource", "")
        self.volume: float = kwargs.get("volume", 1.0)
        self.pitch: float = kwargs.get("pitch", 1.0)
        self.loop: bool = kwargs.get("loop", False)
        self.auto_play: bool = kwargs.get("auto_play", False)
        self.is_3d: bool = kwargs.get("is_3d", False)
        self.min_distance: float = kwargs.get("min_distance", 1.0)
        self.max_distance: float = kwargs.get("max_distance", 100.0)
        self.spatial_blend: float = kwargs.get("spatial_blend", 1.0)
        self.play_state: str = kwargs.get("play_state", "stopped")


@component
class Animator(Component):
    component_type: str = "animator"

    def __init__(self, **kwargs: Any):
        super().__init__(**kwargs)
        self.current_state: str = kwargs.get("current_state", "")
        self.speed: float = kwargs.get("speed", 1.0)
        self.loop: bool = kwargs.get("loop", True)
        self.time: float = kwargs.get("time", 0.0)
        self.normalized_time: float = kwargs.get("normalized_time", 0.0)
        self.states: Dict[str, Any] = kwargs.get("states", {})
        self.transitions: List[Dict[str, Any]] = kwargs.get("transitions", [])
        self.parameters: Dict[str, Any] = kwargs.get("parameters", {})

    def set_float(self, name: str, value: float) -> None:
        self.parameters[name] = {"type": "float", "value": value}

    def set_bool(self, name: str, value: bool) -> None:
        self.parameters[name] = {"type": "bool", "value": value}

    def set_trigger(self, name: str) -> None:
        self.parameters[name] = {"type": "trigger", "value": True}

    def play(self, state_name: str) -> None:
        self.current_state = state_name
        self.time = 0.0
        self.normalized_time = 0.0


@component
class InputReceiver(Component):
    component_type: str = "input_receiver"

    def __init__(self, **kwargs: Any):
        super().__init__(**kwargs)
        self.input_map: Dict[str, str] = kwargs.get("input_map", {})
        self.actions: Dict[str, bool] = kwargs.get("actions", {})
        self.axis_values: Dict[str, float] = kwargs.get("axis_values", {})
        self.consume_input: bool = kwargs.get("consume_input", True)
        self.priority: int = kwargs.get("priority", 0)


@component
class AIBrain(Component):
    component_type: str = "ai_brain"

    def __init__(self, **kwargs: Any):
        super().__init__(**kwargs)
        self.agent_id: str = kwargs.get("agent_id", "")
        self.behavior_mode: str = kwargs.get("behavior_mode", "autonomous")
        self.decision_interval: float = kwargs.get("decision_interval", 0.5)
        self.awareness_radius: float = kwargs.get("awareness_radius", 10.0)
        self.memory_capacity: int = kwargs.get("memory_capacity", 100)
        self.creativity: float = kwargs.get("creativity", 0.7)
        self.coherence: float = kwargs.get("coherence", 0.85)
        self.detail_level: float = kwargs.get("detail_level", 0.8)
        self.current_goal: str = kwargs.get("current_goal", "")
        self.emotional_state: str = kwargs.get("emotional_state", "neutral")
        self.personality_traits: Dict[str, float] = kwargs.get("personality_traits", {})
        self.knowledge: Dict[str, Any] = kwargs.get("knowledge", {})
        self._decision_timer: float = 0.0
        self._last_decision: Optional[Dict[str, Any]] = None

    def set_goal(self, goal: str) -> None:
        self.current_goal = goal

    def set_emotion(self, emotion: str) -> None:
        self.emotional_state = emotion

    def set_trait(self, trait: str, value: float) -> None:
        self.personality_traits[trait] = max(0.0, min(1.0, value))

    def add_knowledge(self, key: str, value: Any) -> None:
        self.knowledge[key] = value


@component
class Script(Component):
    component_type: str = "script"

    def __init__(self, **kwargs: Any):
        super().__init__(**kwargs)
        self.script_path: str = kwargs.get("script_path", "")
        self.script_type: str = kwargs.get("script_type", "python")
        self.properties: Dict[str, Any] = kwargs.get("properties", {})
        self.update_interval: float = kwargs.get("update_interval", 0.0)
        self._timer: float = 0.0


@component
class Tween(Component):
    component_type: str = "tween"

    def __init__(self, **kwargs: Any):
        super().__init__(**kwargs)
        self.property_name: str = kwargs.get("property_name", "")
        self.from_value: float = kwargs.get("from_value", 0.0)
        self.to_value: float = kwargs.get("to_value", 1.0)
        self.duration: float = kwargs.get("duration", 1.0)
        self.elapsed: float = kwargs.get("elapsed", 0.0)
        self.easing: str = kwargs.get("easing", "linear")
        self.loop: bool = kwargs.get("loop", False)
        self.yoyo: bool = kwargs.get("yoyo", False)
        self.auto_start: bool = kwargs.get("auto_start", True)
        self.is_playing: bool = kwargs.get("is_playing", False)
        self.on_complete: Optional[str] = kwargs.get("on_complete", None)
