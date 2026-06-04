"""
SparkLabs Agent Scene Director

AI-powered scene orchestration system that coordinates cameras, NPCs,
narrative elements, lighting, and events to create cinematic game scenes.
The director manages scene composition, actor blocking, camera direction,
and emotional pacing to deliver immersive gameplay experiences.
"""

from __future__ import annotations

import math
import threading
import time as _time_module
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class SceneMood(str, Enum):
    """Emotional tone of a scene."""
    NEUTRAL = "neutral"
    TENSE = "tense"
    JOYFUL = "joyful"
    SOMBER = "somber"
    MYSTERIOUS = "mysterious"
    EPIC = "epic"
    ROMANTIC = "romantic"
    DREADFUL = "dreadful"
    HOPEFUL = "hopeful"
    CHAOTIC = "chaotic"


class CameraStyle(str, Enum):
    """Camera composition style for a scene."""
    WIDE_ESTABLISHING = "wide_establishing"
    MEDIUM_TWO_SHOT = "medium_two_shot"
    CLOSE_UP = "close_up"
    OVER_SHOULDER = "over_shoulder"
    TRACKING = "tracking"
    AERIAL = "aerial"
    DUTCH_ANGLE = "dutch_angle"
    POV = "pov"
    PANNING = "panning"
    STATIC = "static"


class ActorRole(str, Enum):
    """Role of an actor in a scene."""
    PROTAGONIST = "protagonist"
    ANTAGONIST = "antagonist"
    SUPPORTING = "supporting"
    BACKGROUND = "background"
    NARRATOR = "narrator"
    CROWD = "crowd"


class ScenePhase(str, Enum):
    """Phase of scene execution."""
    PENDING = "pending"
    PREPARING = "preparing"
    ACTIVE = "active"
    CLIMAX = "climax"
    RESOLVING = "resolving"
    COMPLETE = "complete"
    CANCELLED = "cancelled"


class LightingScheme(str, Enum):
    """Lighting configuration for a scene."""
    NATURAL_DAY = "natural_day"
    NATURAL_NIGHT = "natural_night"
    DRAMATIC = "dramatic"
    SILHOUETTE = "silhouette"
    WARM_INTIMATE = "warm_intimate"
    COLD_STERILE = "cold_sterile"
    STROBE = "strobe"
    FLICKERING = "flickering"


class TransitionType(str, Enum):
    """Scene transition type."""
    CUT = "cut"
    FADE_IN = "fade_in"
    FADE_OUT = "fade_out"
    DISSOLVE = "dissolve"
    WIPE = "wipe"
    IRIS = "iris"
    ZOOM_TRANSITION = "zoom_transition"


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------


@dataclass
class ActorBlocking:
    """Position and movement data for a scene actor."""
    actor_id: str = ""
    role: ActorRole = ActorRole.SUPPORTING
    start_x: float = 0.0
    start_y: float = 0.0
    end_x: float = 0.0
    end_y: float = 0.0
    facing_direction: float = 0.0
    movement_style: str = "walk"
    gesture_id: str = ""
    dialogue_line_id: str = ""
    emotion: str = "neutral"
    enter_at_time: float = 0.0
    exit_at_time: float = -1.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "actor_id": self.actor_id,
            "role": self.role.value,
            "start_x": self.start_x,
            "start_y": self.start_y,
            "end_x": self.end_x,
            "end_y": self.end_y,
            "facing_direction": self.facing_direction,
            "movement_style": self.movement_style,
            "gesture_id": self.gesture_id,
            "dialogue_line_id": self.dialogue_line_id,
            "emotion": self.emotion,
            "enter_at_time": self.enter_at_time,
            "exit_at_time": self.exit_at_time,
        }


@dataclass
class CameraDirective:
    """Camera instruction for a scene segment."""
    style: CameraStyle = CameraStyle.WIDE_ESTABLISHING
    target_x: float = 0.0
    target_y: float = 0.0
    zoom_level: float = 1.0
    pan_speed: float = 0.0
    shake_intensity: float = 0.0
    focus_actor_id: str = ""
    start_time: float = 0.0
    duration: float = 3.0
    transition: TransitionType = TransitionType.CUT
    transition_duration: float = 0.5

    def to_dict(self) -> Dict[str, Any]:
        return {
            "style": self.style.value,
            "target_x": self.target_x,
            "target_y": self.target_y,
            "zoom_level": self.zoom_level,
            "pan_speed": self.pan_speed,
            "shake_intensity": self.shake_intensity,
            "focus_actor_id": self.focus_actor_id,
            "start_time": self.start_time,
            "duration": self.duration,
            "transition": self.transition.value,
            "transition_duration": self.transition_duration,
        }


@dataclass
class SceneEvent:
    """A scripted event within a scene."""
    event_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    event_type: str = "dialogue"
    trigger_time: float = 0.0
    target_id: str = ""
    parameters: Dict[str, Any] = field(default_factory=dict)
    has_fired: bool = False
    fire_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": self.event_id,
            "event_type": self.event_type,
            "trigger_time": self.trigger_time,
            "target_id": self.target_id,
            "parameters": self.parameters,
            "has_fired": self.has_fired,
            "fire_count": self.fire_count,
        }


@dataclass
class SceneDefinition:
    """Complete scene definition with all directorial elements."""
    scene_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    title: str = "Untitled Scene"
    description: str = ""
    mood: SceneMood = SceneMood.NEUTRAL
    duration: float = 10.0
    location_id: str = ""
    background_music: str = ""
    ambient_sound: str = ""
    lighting: LightingScheme = LightingScheme.NATURAL_DAY
    camera_directives: List[CameraDirective] = field(default_factory=list)
    actor_blockings: List[ActorBlocking] = field(default_factory=list)
    scene_events: List[SceneEvent] = field(default_factory=list)
    narrative_beat_id: str = ""
    phase: ScenePhase = ScenePhase.PENDING
    elapsed_time: float = 0.0
    created_at: float = field(default_factory=_time_module.time)
    tags: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "scene_id": self.scene_id,
            "title": self.title,
            "description": self.description,
            "mood": self.mood.value,
            "duration": self.duration,
            "location_id": self.location_id,
            "background_music": self.background_music,
            "ambient_sound": self.ambient_sound,
            "lighting": self.lighting.value,
            "camera_directives": [d.to_dict() for d in self.camera_directives],
            "actor_blockings": [b.to_dict() for b in self.actor_blockings],
            "scene_events": [e.to_dict() for e in self.scene_events],
            "narrative_beat_id": self.narrative_beat_id,
            "phase": self.phase.value,
            "elapsed_time": self.elapsed_time,
            "tags": self.tags,
        }


@dataclass
class SceneSequence:
    """A sequence of scenes forming a narrative arc."""
    sequence_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    name: str = "Scene Sequence"
    scene_ids: List[str] = field(default_factory=list)
    current_index: int = 0
    is_looping: bool = False
    transition_overlap: float = 0.5
    created_at: float = field(default_factory=_time_module.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "sequence_id": self.sequence_id,
            "name": self.name,
            "scene_ids": self.scene_ids,
            "current_index": self.current_index,
            "is_looping": self.is_looping,
            "transition_overlap": self.transition_overlap,
        }


# ---------------------------------------------------------------------------
# Agent Scene Director
# ---------------------------------------------------------------------------


class AgentSceneDirector:
    """
    AI-powered scene orchestrator that coordinates camera, actors,
    lighting, and events to create cinematic game scenes.

    The director manages the complete lifecycle of scene composition,
    from initial blocking through execution and resolution.
    """

    _instance: Optional["AgentSceneDirector"] = None
    _lock = threading.RLock()

    def __new__(cls) -> "AgentSceneDirector":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    @classmethod
    def get_instance(cls) -> "AgentSceneDirector":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self) -> None:
        if self._initialized:
            return
        self._initialized = True

        self._scenes: Dict[str, SceneDefinition] = {}
        self._sequences: Dict[str, SceneSequence] = {}
        self._active_scene_id: Optional[str] = None
        self._active_sequence_id: Optional[str] = None
        self._scene_history: List[Dict[str, Any]] = []
        self._total_scenes_created: int = 0
        self._total_scenes_completed: int = 0

        # Scene composition templates
        self._composition_presets: Dict[str, List[CameraDirective]] = {
            "dialogue": [
                CameraDirective(style=CameraStyle.WIDE_ESTABLISHING, duration=2.0),
                CameraDirective(style=CameraStyle.MEDIUM_TWO_SHOT, duration=4.0),
                CameraDirective(style=CameraStyle.OVER_SHOULDER, duration=3.0),
                CameraDirective(style=CameraStyle.CLOSE_UP, duration=2.0),
            ],
            "action": [
                CameraDirective(style=CameraStyle.WIDE_ESTABLISHING, duration=1.5),
                CameraDirective(style=CameraStyle.TRACKING, duration=2.0, pan_speed=120.0),
                CameraDirective(style=CameraStyle.DUTCH_ANGLE, duration=1.0, shake_intensity=0.3),
                CameraDirective(style=CameraStyle.CLOSE_UP, duration=1.5),
                CameraDirective(style=CameraStyle.AERIAL, duration=2.0),
            ],
            "exploration": [
                CameraDirective(style=CameraStyle.AERIAL, duration=3.0),
                CameraDirective(style=CameraStyle.TRACKING, duration=5.0, pan_speed=60.0),
                CameraDirective(style=CameraStyle.PANNING, duration=4.0, pan_speed=30.0),
            ],
            "reveal": [
                CameraDirective(style=CameraStyle.CLOSE_UP, duration=2.0),
                CameraDirective(style=CameraStyle.WIDE_ESTABLISHING, duration=2.0,
                              transition=TransitionType.ZOOM_TRANSITION),
                CameraDirective(style=CameraStyle.AERIAL, duration=3.0),
            ],
            "emotional": [
                CameraDirective(style=CameraStyle.CLOSE_UP, duration=3.0),
                CameraDirective(style=CameraStyle.OVER_SHOULDER, duration=2.0),
                CameraDirective(style=CameraStyle.STATIC, duration=2.0),
                CameraDirective(style=CameraStyle.CLOSE_UP, duration=2.0,
                              transition=TransitionType.DISSOLVE),
            ],
        }

        # Mood-to-lighting mapping
        self._mood_lighting: Dict[SceneMood, LightingScheme] = {
            SceneMood.NEUTRAL: LightingScheme.NATURAL_DAY,
            SceneMood.TENSE: LightingScheme.COLD_STERILE,
            SceneMood.JOYFUL: LightingScheme.WARM_INTIMATE,
            SceneMood.SOMBER: LightingScheme.SILHOUETTE,
            SceneMood.MYSTERIOUS: LightingScheme.FLICKERING,
            SceneMood.EPIC: LightingScheme.DRAMATIC,
            SceneMood.ROMANTIC: LightingScheme.WARM_INTIMATE,
            SceneMood.DREADFUL: LightingScheme.STROBE,
            SceneMood.HOPEFUL: LightingScheme.NATURAL_DAY,
            SceneMood.CHAOTIC: LightingScheme.STROBE,
        }

    # ------------------------------------------------------------------
    # Scene Creation
    # ------------------------------------------------------------------

    def create_scene(
        self,
        title: str = "Untitled Scene",
        description: str = "",
        mood: SceneMood = SceneMood.NEUTRAL,
        duration: float = 10.0,
        location_id: str = "",
        composition_type: str = "dialogue",
        tags: Optional[List[str]] = None,
    ) -> SceneDefinition:
        """Create a new scene with camera directives based on composition type."""
        with self._lock:
            scene = SceneDefinition(
                title=title,
                description=description,
                mood=mood,
                duration=duration,
                location_id=location_id,
                tags=tags or [],
            )

            # Auto-assign lighting based on mood
            scene.lighting = self._mood_lighting.get(mood, LightingScheme.NATURAL_DAY)

            # Apply camera composition preset
            preset = self._composition_presets.get(
                composition_type,
                self._composition_presets["dialogue"],
            )
            scene.camera_directives = [
                CameraDirective(
                    style=d.style,
                    duration=d.duration,
                    pan_speed=d.pan_speed,
                    shake_intensity=d.shake_intensity,
                    transition=d.transition,
                    start_time=sum(
                        p.duration for p in scene.camera_directives
                    ),
                )
                for d in preset
            ]

            self._scenes[scene.scene_id] = scene
            self._total_scenes_created += 1
            return scene

    def add_actor_blocking(
        self,
        scene_id: str,
        actor_id: str,
        role: ActorRole = ActorRole.SUPPORTING,
        start_x: float = 0.0,
        start_y: float = 0.0,
        end_x: float = 0.0,
        end_y: float = 0.0,
        facing_direction: float = 0.0,
        emotion: str = "neutral",
        enter_at_time: float = 0.0,
        exit_at_time: float = -1.0,
    ) -> Optional[ActorBlocking]:
        """Add an actor blocking instruction to a scene."""
        with self._lock:
            scene = self._scenes.get(scene_id)
            if scene is None:
                return None

            blocking = ActorBlocking(
                actor_id=actor_id,
                role=role,
                start_x=start_x,
                start_y=start_y,
                end_x=end_x,
                end_y=end_y,
                facing_direction=facing_direction,
                emotion=emotion,
                enter_at_time=enter_at_time,
                exit_at_time=exit_at_time,
            )
            scene.actor_blockings.append(blocking)
            return blocking

    def add_scene_event(
        self,
        scene_id: str,
        event_type: str = "dialogue",
        trigger_time: float = 0.0,
        target_id: str = "",
        parameters: Optional[Dict[str, Any]] = None,
    ) -> Optional[SceneEvent]:
        """Add a timed event to a scene."""
        with self._lock:
            scene = self._scenes.get(scene_id)
            if scene is None:
                return None

            event = SceneEvent(
                event_type=event_type,
                trigger_time=trigger_time,
                target_id=target_id,
                parameters=parameters or {},
            )
            scene.scene_events.append(event)
            return event

    def add_camera_directive(
        self,
        scene_id: str,
        style: CameraStyle = CameraStyle.WIDE_ESTABLISHING,
        target_x: float = 0.0,
        target_y: float = 0.0,
        duration: float = 3.0,
        zoom_level: float = 1.0,
        transition: TransitionType = TransitionType.CUT,
    ) -> Optional[CameraDirective]:
        """Add a camera directive to a scene."""
        with self._lock:
            scene = self._scenes.get(scene_id)
            if scene is None:
                return None

            start_time = sum(d.duration for d in scene.camera_directives)
            directive = CameraDirective(
                style=style,
                target_x=target_x,
                target_y=target_y,
                duration=duration,
                zoom_level=zoom_level,
                transition=transition,
                start_time=start_time,
            )
            scene.camera_directives.append(directive)
            return directive

    # ------------------------------------------------------------------
    # Scene Sequence Management
    # ------------------------------------------------------------------

    def create_sequence(
        self,
        name: str = "Scene Sequence",
        scene_ids: Optional[List[str]] = None,
        is_looping: bool = False,
        transition_overlap: float = 0.5,
    ) -> SceneSequence:
        """Create a sequence of scenes for narrative flow."""
        with self._lock:
            sequence = SceneSequence(
                name=name,
                scene_ids=scene_ids or [],
                is_looping=is_looping,
                transition_overlap=transition_overlap,
            )
            self._sequences[sequence.sequence_id] = sequence
            return sequence

    def add_scene_to_sequence(
        self, sequence_id: str, scene_id: str
    ) -> bool:
        """Add a scene to an existing sequence."""
        with self._lock:
            sequence = self._sequences.get(sequence_id)
            if sequence is None:
                return False
            if scene_id not in self._scenes:
                return False
            sequence.scene_ids.append(scene_id)
            return True

    # ------------------------------------------------------------------
    # Scene Execution
    # ------------------------------------------------------------------

    def start_scene(self, scene_id: str) -> bool:
        """Begin executing a scene."""
        with self._lock:
            scene = self._scenes.get(scene_id)
            if scene is None:
                return False
            scene.phase = ScenePhase.ACTIVE
            scene.elapsed_time = 0.0
            self._active_scene_id = scene_id
            return True

    def tick_scene(self, scene_id: str, delta_time: float) -> Optional[Dict[str, Any]]:
        """Advance scene execution by delta_time seconds."""
        with self._lock:
            scene = self._scenes.get(scene_id)
            if scene is None:
                return None
            if scene.phase not in (ScenePhase.ACTIVE, ScenePhase.CLIMAX):
                return None

            scene.elapsed_time += delta_time

            # Check for scene completion
            if scene.elapsed_time >= scene.duration:
                scene.phase = ScenePhase.COMPLETE
                self._total_scenes_completed += 1
                self._scene_history.append({
                    "scene_id": scene_id,
                    "title": scene.title,
                    "completed_at": _time_module.time(),
                    "duration": scene.elapsed_time,
                })
                return {"phase": "complete", "elapsed": scene.elapsed_time}

            # Check for climax point (around 70% of duration)
            progress = scene.elapsed_time / max(scene.duration, 0.001)
            if progress >= 0.7 and scene.phase == ScenePhase.ACTIVE:
                scene.phase = ScenePhase.CLIMAX

            # Fire pending events
            fired_events = []
            for event in scene.scene_events:
                if not event.has_fired and scene.elapsed_time >= event.trigger_time:
                    event.has_fired = True
                    event.fire_count += 1
                    fired_events.append(event.to_dict())

            # Get current camera directive
            current_camera = None
            cumulative_time = 0.0
            for directive in scene.camera_directives:
                cumulative_time += directive.duration
                if scene.elapsed_time <= cumulative_time:
                    current_camera = directive.to_dict()
                    break

            return {
                "phase": scene.phase.value,
                "elapsed": scene.elapsed_time,
                "progress": progress,
                "current_camera": current_camera,
                "fired_events": fired_events,
            }

    def stop_scene(self, scene_id: str) -> bool:
        """Stop scene execution."""
        with self._lock:
            scene = self._scenes.get(scene_id)
            if scene is None:
                return False
            scene.phase = ScenePhase.CANCELLED
            if self._active_scene_id == scene_id:
                self._active_scene_id = None
            return True

    def reset_scene(self, scene_id: str) -> bool:
        """Reset a scene to its initial state."""
        with self._lock:
            scene = self._scenes.get(scene_id)
            if scene is None:
                return False
            scene.phase = ScenePhase.PENDING
            scene.elapsed_time = 0.0
            for event in scene.scene_events:
                event.has_fired = False
                event.fire_count = 0
            return True

    # ------------------------------------------------------------------
    # Sequence Execution
    # ------------------------------------------------------------------

    def start_sequence(self, sequence_id: str) -> bool:
        """Begin executing a scene sequence."""
        with self._lock:
            sequence = self._sequences.get(sequence_id)
            if sequence is None or not sequence.scene_ids:
                return False
            sequence.current_index = 0
            self._active_sequence_id = sequence_id
            first_scene_id = sequence.scene_ids[0]
            return self.start_scene(first_scene_id)

    def advance_sequence(self, sequence_id: str) -> Optional[str]:
        """Move to the next scene in the sequence."""
        with self._lock:
            sequence = self._sequences.get(sequence_id)
            if sequence is None:
                return None

            next_index = sequence.current_index + 1
            if next_index >= len(sequence.scene_ids):
                if sequence.is_looping:
                    next_index = 0
                else:
                    self._active_sequence_id = None
                    return None

            sequence.current_index = next_index
            next_scene_id = sequence.scene_ids[next_index]
            self.start_scene(next_scene_id)
            return next_scene_id

    # ------------------------------------------------------------------
    # Query Methods
    # ------------------------------------------------------------------

    def get_scene(self, scene_id: str) -> Optional[SceneDefinition]:
        """Get a scene by ID."""
        return self._scenes.get(scene_id)

    def get_active_scene(self) -> Optional[SceneDefinition]:
        """Get the currently active scene."""
        if self._active_scene_id:
            return self._scenes.get(self._active_scene_id)
        return None

    def get_sequence(self, sequence_id: str) -> Optional[SceneSequence]:
        """Get a sequence by ID."""
        return self._sequences.get(sequence_id)

    def get_scene_history(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Get recent scene completion history."""
        return self._scene_history[-limit:]

    def get_all_scenes(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Get all scenes as dictionaries."""
        scenes = list(self._scenes.values())[:limit]
        return [s.to_dict() for s in scenes]

    def get_all_sequences(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get all sequences as dictionaries."""
        sequences = list(self._sequences.values())[:limit]
        return [s.to_dict() for s in sequences]

    def get_stats(self) -> Dict[str, Any]:
        """Get system statistics."""
        active_scene = None
        if self._active_scene_id:
            active_scene = self._scenes.get(self._active_scene_id)
        return {
            "total_scenes": len(self._scenes),
            "total_sequences": len(self._sequences),
            "total_created": self._total_scenes_created,
            "total_completed": self._total_scenes_completed,
            "active_scene": active_scene.to_dict() if active_scene else None,
            "active_sequence_id": self._active_sequence_id,
            "composition_presets": list(self._composition_presets.keys()),
            "recent_history": self._scene_history[-5:],
        }

    def get_composition_presets(self) -> Dict[str, List[Dict[str, Any]]]:
        """Get available camera composition presets."""
        return {
            name: [d.to_dict() for d in directives]
            for name, directives in self._composition_presets.items()
        }


# ---------------------------------------------------------------------------
# Module-level accessor
# ---------------------------------------------------------------------------


def get_scene_director() -> AgentSceneDirector:
    """Get or create the singleton AgentSceneDirector instance."""
    return AgentSceneDirector.get_instance()