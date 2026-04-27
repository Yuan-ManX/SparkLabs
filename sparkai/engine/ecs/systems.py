"""
SparkLabs ECS - Built-in Systems

Core systems that process entities with specific component combinations:
- TransformSystem: Hierarchical transform propagation
- PhysicsSystem: Rigid body simulation
- RenderSystem: Visual rendering pipeline
- AnimationSystem: Animator state machine
- AudioSystem: Sound playback management
- InputSystem: Input event dispatch
- AISystem: AI brain decision processing
- TweenSystem: Tween animation interpolation
- ScriptSystem: Custom script execution
- CollisionSystem: Collision detection
"""

from __future__ import annotations

import math
from typing import Any, Dict, List, Optional

from sparkai.engine.ecs.system import System, SystemPriority, system
from sparkai.engine.ecs.entity import Entity


@system
class TransformSystem(System):
    system_type: str = "transform_system"
    priority: int = SystemPriority.PHYSICS

    @property
    def required_components(self) -> List[str]:
        return ["transform"]

    def update(self, delta_time: float, entities: List[Entity]) -> None:
        for entity in entities:
            transform = entity.get_component("transform")
            if not transform or not transform.enabled:
                continue
            if entity.parent:
                parent_entity = None
                if self._world:
                    parent_entity = self._world.entities.get_entity(entity.parent)
                if parent_entity:
                    parent_transform = parent_entity.get_component("transform")
                    if parent_transform:
                        pass


@system
class PhysicsSystem(System):
    system_type: str = "physics_system"
    priority: int = SystemPriority.PHYSICS

    def __init__(self):
        super().__init__()
        self.gravity_x: float = 0.0
        self.gravity_y: float = -9.81
        self.gravity_z: float = 0.0

    @property
    def required_components(self) -> List[str]:
        return ["transform", "physics_body"]

    def update(self, delta_time: float, entities: List[Entity]) -> None:
        for entity in entities:
            transform = entity.get_component("transform")
            body = entity.get_component("physics_body")
            if not transform or not body or not body.enabled:
                continue

            if body.body_type == "static":
                continue

            if body.body_type in ("dynamic", "kinematic"):
                ax = self.gravity_x * body.gravity_scale
                ay = self.gravity_y * body.gravity_scale
                az = self.gravity_z * body.gravity_scale

                body.velocity_x += ax * delta_time
                body.velocity_y += ay * delta_time
                body.velocity_z += az * delta_time

                body.velocity_x *= (1.0 - body.linear_damping * delta_time)
                body.velocity_y *= (1.0 - body.linear_damping * delta_time)
                body.velocity_z *= (1.0 - body.linear_damping * delta_time)

                transform.x += body.velocity_x * delta_time
                transform.y += body.velocity_y * delta_time
                transform.z += body.velocity_z * delta_time

                if not body.fixed_rotation:
                    transform.rotation_z += body.angular_velocity * delta_time
                    body.angular_velocity *= (1.0 - body.angular_damping * delta_time)


@system
class RenderSystem(System):
    system_type: str = "render_system"
    priority: int = SystemPriority.RENDER

    def __init__(self):
        super().__init__()
        self._render_queue: List[Dict[str, Any]] = []

    @property
    def required_components(self) -> List[str]:
        return ["transform", "renderable"]

    def update(self, delta_time: float, entities: List[Entity]) -> None:
        self._render_queue.clear()
        for entity in entities:
            transform = entity.get_component("transform")
            renderable = entity.get_component("renderable")
            if not transform or not renderable or not renderable.enabled:
                continue
            if not renderable.visible:
                continue

            render_item = {
                "entity_id": entity.id,
                "position": [transform.x, transform.y, transform.z],
                "rotation": [transform.rotation_x, transform.rotation_y, transform.rotation_z],
                "scale": [transform.scale_x, transform.scale_y, transform.scale_z],
                "z_index": renderable.z_index,
                "render_layer": renderable.render_layer,
                "opacity": renderable.opacity,
                "shader": renderable.shader,
                "material": renderable.material,
                "color": renderable.color,
                "width": renderable.width,
                "height": renderable.height,
            }

            sprite = entity.get_component("sprite_renderer")
            if sprite:
                render_item["sprite"] = {
                    "resource": sprite.sprite_resource,
                    "flip_x": sprite.flip_x,
                    "flip_y": sprite.flip_y,
                    "source": [sprite.source_x, sprite.source_y, sprite.source_width, sprite.source_height],
                }

            text = entity.get_component("text_renderer")
            if text:
                render_item["text"] = {
                    "content": text.text,
                    "font": text.font_family,
                    "size": text.font_size,
                    "color": text.color,
                    "alignment": text.alignment,
                }

            self._render_queue.append(render_item)

        self._render_queue.sort(key=lambda item: (item["z_index"], item["position"][2]))

    @property
    def render_queue(self) -> List[Dict[str, Any]]:
        return self._render_queue


@system
class AnimationSystem(System):
    system_type: str = "animation_system"
    priority: int = SystemPriority.ANIMATION

    @property
    def required_components(self) -> List[str]:
        return ["animator"]

    def update(self, delta_time: float, entities: List[Entity]) -> None:
        for entity in entities:
            animator = entity.get_component("animator")
            if not animator or not animator.enabled or not animator.current_state:
                continue

            animator.time += delta_time * animator.speed

            current_state_data = animator.states.get(animator.current_state)
            if current_state_data:
                duration = current_state_data.get("duration", 1.0)
                if duration > 0:
                    animator.normalized_time = animator.time / duration

                if animator.time >= duration:
                    if animator.loop:
                        animator.time = animator.time % duration
                        animator.normalized_time = animator.time / duration if duration > 0 else 0.0
                    else:
                        animator.normalized_time = 1.0

                for transition in animator.transitions:
                    from_state = transition.get("from", "")
                    to_state = transition.get("to", "")
                    conditions = transition.get("conditions", {})

                    if from_state == animator.current_state:
                        should_transition = True
                        for param_name, condition in conditions.items():
                            param = animator.parameters.get(param_name)
                            if not param:
                                should_transition = False
                                break
                            if condition.get("type") == "trigger" and param.get("value"):
                                animator.parameters[param_name]["value"] = False
                            elif condition.get("type") == "bool" and param.get("value") != condition.get("value"):
                                should_transition = False
                                break
                            elif condition.get("type") == "float":
                                op = condition.get("op", ">=")
                                val = condition.get("value", 0)
                                param_val = param.get("value", 0)
                                if op == ">=" and not (param_val >= val):
                                    should_transition = False
                                elif op == "<=" and not (param_val <= val):
                                    should_transition = False
                                elif op == "==" and not (param_val == val):
                                    should_transition = False

                        if should_transition:
                            animator.current_state = to_state
                            animator.time = 0.0
                            animator.normalized_time = 0.0
                            break


@system
class AudioSystem(System):
    system_type: str = "audio_system"
    priority: int = SystemPriority.AUDIO

    def __init__(self):
        super().__init__()
        self._playing_sources: List[str] = []
        self.master_volume: float = 1.0

    @property
    def required_components(self) -> List[str]:
        return ["audio_source"]

    def update(self, delta_time: float, entities: List[Entity]) -> None:
        self._playing_sources.clear()
        for entity in entities:
            audio = entity.get_component("audio_source")
            if not audio or not audio.enabled:
                continue
            if audio.play_state == "playing":
                self._playing_sources.append(entity.id)
            if audio.auto_play and audio.play_state == "stopped":
                audio.play_state = "playing"

    @property
    def playing_sources(self) -> List[str]:
        return self._playing_sources


@system
class InputSystem(System):
    system_type: str = "input_system"
    priority: int = SystemPriority.INPUT

    def __init__(self):
        super().__init__()
        self._input_state: Dict[str, Any] = {
            "keys": {},
            "mouse": {"x": 0, "y": 0, "buttons": {}},
            "touches": [],
        }

    @property
    def required_components(self) -> List[str]:
        return ["input_receiver"]

    def update(self, delta_time: float, entities: List[Entity]) -> None:
        sorted_entities = sorted(
            entities,
            key=lambda e: e.get_component("input_receiver").priority if e.get_component("input_receiver") else 0,
            reverse=True,
        )
        for entity in sorted_entities:
            input_receiver = entity.get_component("input_receiver")
            if not input_receiver or not input_receiver.enabled:
                continue
            input_receiver.actions = {}
            for action_name, key in input_receiver.input_map.items():
                input_receiver.actions[action_name] = self._input_state.get("keys", {}).get(key, False)

    def set_input_state(self, state: Dict[str, Any]) -> None:
        self._input_state = state

    def press_key(self, key: str) -> None:
        self._input_state.setdefault("keys", {})[key] = True

    def release_key(self, key: str) -> None:
        self._input_state.setdefault("keys", {})[key] = False

    def set_mouse(self, x: float, y: float) -> None:
        self._input_state.setdefault("mouse", {})["x"] = x
        self._input_state["mouse"]["y"] = y


@system
class AISystem(System):
    system_type: str = "ai_system"
    priority: int = SystemPriority.AI

    @property
    def required_components(self) -> List[str]:
        return ["ai_brain"]

    def update(self, delta_time: float, entities: List[Entity]) -> None:
        for entity in entities:
            brain = entity.get_component("ai_brain")
            if not brain or not brain.enabled:
                continue

            brain._decision_timer += delta_time
            if brain._decision_timer < brain.decision_interval:
                continue
            brain._decision_timer = 0.0

            transform = entity.get_component("transform")
            if transform:
                nearby_entities = []
                if self._world:
                    all_entities = self._world.entities.all_entities()
                    for other in all_entities:
                        if other.id == entity.id:
                            continue
                        other_transform = other.get_component("transform")
                        if other_transform:
                            dist = transform.distance_to(other_transform)
                            if dist <= brain.awareness_radius:
                                nearby_entities.append({
                                    "entity_id": other.id,
                                    "name": other.name,
                                    "distance": dist,
                                    "position": other_transform.position,
                                })

                brain._last_decision = {
                    "entity_id": entity.id,
                    "nearby_count": len(nearby_entities),
                    "nearby_entities": nearby_entities[:5],
                    "current_goal": brain.current_goal,
                    "emotional_state": brain.emotional_state,
                }


@system
class TweenSystem(System):
    system_type: str = "tween_system"
    priority: int = SystemPriority.ANIMATION

    @property
    def required_components(self) -> List[str]:
        return ["tween"]

    def update(self, delta_time: float, entities: List[Entity]) -> None:
        for entity in entities:
            tween = entity.get_component("tween")
            if not tween or not tween.enabled or not tween.is_playing:
                if tween and tween.auto_start and not tween.is_playing:
                    tween.is_playing = True
                continue

            tween.elapsed += delta_time
            progress = min(tween.elapsed / tween.duration, 1.0) if tween.duration > 0 else 1.0
            eased_progress = self._ease(progress, tween.easing)

            if tween.property_name and entity.has_component("transform"):
                transform = entity.get_component("transform")
                current_value = tween.from_value + (tween.to_value - tween.from_value) * eased_progress
                self._apply_tween_value(transform, tween.property_name, current_value)

            if progress >= 1.0:
                if tween.loop:
                    tween.elapsed = 0.0
                    if tween.yoyo:
                        tween.from_value, tween.to_value = tween.to_value, tween.from_value
                else:
                    tween.is_playing = False
                    tween.elapsed = tween.duration

    def _ease(self, t: float, easing: str) -> float:
        if easing == "linear":
            return t
        elif easing == "ease_in_quad":
            return t * t
        elif easing == "ease_out_quad":
            return t * (2 - t)
        elif easing == "ease_in_out_quad":
            return 2 * t * t if t < 0.5 else -1 + (4 - 2 * t) * t
        elif easing == "ease_in_cubic":
            return t * t * t
        elif easing == "ease_out_cubic":
            t -= 1
            return t * t * t + 1
        elif easing == "ease_in_out_cubic":
            return 4 * t * t * t if t < 0.5 else (t - 1) * (2 * t - 2) * (2 * t - 2) + 1
        elif easing == "ease_in_elastic":
            if t == 0 or t == 1:
                return t
            return -math.pow(2, 10 * (t - 1)) * math.sin((t - 1.1) * 5 * math.pi)
        elif easing == "ease_out_bounce":
            if t < 1 / 2.75:
                return 7.5625 * t * t
            elif t < 2 / 2.75:
                t -= 1.5 / 2.75
                return 7.5625 * t * t + 0.75
            elif t < 2.5 / 2.75:
                t -= 2.25 / 2.75
                return 7.5625 * t * t + 0.9375
            else:
                t -= 2.625 / 2.75
                return 7.5625 * t * t + 0.984375
        return t

    def _apply_tween_value(self, transform: Any, property_name: str, value: float) -> None:
        prop_map = {
            "x": "x", "y": "y", "z": "z",
            "scale_x": "scale_x", "scale_y": "scale_y", "scale_z": "scale_z",
            "rotation_x": "rotation_x", "rotation_y": "rotation_y", "rotation_z": "rotation_z",
            "opacity": "opacity",
        }
        attr = prop_map.get(property_name)
        if attr and hasattr(transform, attr):
            setattr(transform, attr, value)


@system
class ScriptSystem(System):
    system_type: str = "script_system"
    priority: int = SystemPriority.GAMEPLAY

    @property
    def required_components(self) -> List[str]:
        return ["script"]

    def update(self, delta_time: float, entities: List[Entity]) -> None:
        for entity in entities:
            script = entity.get_component("script")
            if not script or not script.enabled:
                continue
            if script.update_interval > 0:
                script._timer += delta_time
                if script._timer < script.update_interval:
                    continue
                script._timer = 0.0


@system
class CollisionSystem(System):
    system_type: str = "collision_system"
    priority: int = SystemPriority.PHYSICS

    def __init__(self):
        super().__init__()
        self._collisions: List[Dict[str, Any]] = []

    @property
    def required_components(self) -> List[str]:
        return ["transform", "collider"]

    def update(self, delta_time: float, entities: List[Entity]) -> None:
        self._collisions.clear()
        for i, entity_a in enumerate(entities):
            transform_a = entity_a.get_component("transform")
            collider_a = entity_a.get_component("collider")
            if not transform_a or not collider_a or not collider_a.enabled:
                continue

            for entity_b in entities[i + 1:]:
                transform_b = entity_b.get_component("transform")
                collider_b = entity_b.get_component("collider")
                if not transform_b or not collider_b or not collider_b.enabled:
                    continue

                if not (collider_a.collision_layer & collider_b.collision_mask):
                    continue

                collision = self._check_collision(
                    transform_a, collider_a, transform_b, collider_b
                )
                if collision:
                    self._collisions.append({
                        "entity_a": entity_a.id,
                        "entity_b": entity_b.id,
                        "type": collision,
                    })

    def _check_collision(
        self,
        transform_a: Any, collider_a: Any,
        transform_b: Any, collider_b: Any,
    ) -> Optional[str]:
        if collider_a.collider_type == "box" and collider_b.collider_type == "box":
            ax = transform_a.x + collider_a.offset_x
            ay = transform_a.y + collider_a.offset_y
            bx = transform_b.x + collider_b.offset_x
            by = transform_b.y + collider_b.offset_y

            half_a_w = collider_a.width / 2 * transform_a.scale_x
            half_a_h = collider_a.height / 2 * transform_a.scale_y
            half_b_w = collider_b.width / 2 * transform_b.scale_x
            half_b_h = collider_b.height / 2 * transform_b.scale_y

            if (
                ax - half_a_w < bx + half_b_w
                and ax + half_a_w > bx - half_b_w
                and ay - half_a_h < by + half_b_h
                and ay + half_a_h > by - half_b_h
            ):
                return "aabb"

        elif collider_a.collider_type == "circle" and collider_b.collider_type == "circle":
            dx = transform_a.x + collider_a.offset_x - (transform_b.x + collider_b.offset_x)
            dy = transform_a.y + collider_a.offset_y - (transform_b.y + collider_b.offset_y)
            dist = math.sqrt(dx * dx + dy * dy)
            if dist < collider_a.radius + collider_b.radius:
                return "circle"

        return None

    @property
    def collisions(self) -> List[Dict[str, Any]]:
        return self._collisions
