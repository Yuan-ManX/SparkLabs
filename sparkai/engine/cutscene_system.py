"""
SparkLabs Engine - Cutscene System

Cinematic sequence orchestration for narrative-driven game moments.
Manages camera movements, character animations, dialogue timing,
visual effects, and audio cues in synchronized timeline sequences.

Architecture:
  CutsceneSystem
    |-- TimelineSequencer (frame-accurate event scheduling)
    |-- CameraDirector (cinematic camera path interpolation)
    |-- ActionOrchestrator (character action and animation sync)
    |-- TransitionLibrary (fade, wipe, and dissolve transitions)
    |-- SkipManager (player-initiated skip with chapter markers)

Transition Types:
  - FADE_IN, FADE_OUT, CROSSFADE
  - WIPE_LEFT, WIPE_RIGHT, WIPE_UP, WIPE_DOWN
  - DISSOLVE, IRIS_IN, IRIS_OUT
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple


class CutsceneState(Enum):
    IDLE = "idle"
    PLAYING = "playing"
    PAUSED = "paused"
    SKIPPING = "skipping"
    FINISHED = "finished"


class TransitionType(Enum):
    FADE_IN = "fade_in"
    FADE_OUT = "fade_out"
    CROSSFADE = "crossfade"
    WIPE_LEFT = "wipe_left"
    WIPE_RIGHT = "wipe_right"
    WIPE_UP = "wipe_up"
    WIPE_DOWN = "wipe_down"
    DISSOLVE = "dissolve"
    IRIS_IN = "iris_in"
    IRIS_OUT = "iris_out"


class ActionType(Enum):
    MOVE = "move"
    ROTATE = "rotate"
    DIALOGUE = "dialogue"
    ANIMATION = "animation"
    PLAY_SOUND = "play_sound"
    PLAY_MUSIC = "play_music"
    SPAWN_EFFECT = "spawn_effect"
    CAMERA_SHAKE = "camera_shake"
    FADE_SCREEN = "fade_screen"
    PAUSE = "pause"
    TRIGGER_EVENT = "trigger_event"
    SET_PROP = "set_prop"


@dataclass
class CutsceneAction:
    action_type: ActionType
    action_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    trigger_time: float = 0.0
    duration: float = 0.0
    target_id: str = ""
    params: Dict[str, Any] = field(default_factory=dict)
    easing: str = "linear"
    wait_for_completion: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "action_id": self.action_id,
            "type": self.action_type.value,
            "trigger_time": self.trigger_time,
            "duration": self.duration,
            "target": self.target_id,
        }


@dataclass
class CameraKeyframe:
    time: float
    position: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    target: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    fov: float = 60.0
    roll: float = 0.0
    easing: str = "ease_in_out"


@dataclass
class ChapterMarker:
    marker_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    name: str = ""
    trigger_time: float = 0.0
    is_skip_point: bool = True
    save_on_trigger: bool = False


@dataclass
class CutsceneDefinition:
    scene_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    name: str = ""
    description: str = ""
    total_duration: float = 0.0
    is_skippable: bool = True
    actions: List[CutsceneAction] = field(default_factory=list)
    camera_keyframes: List[CameraKeyframe] = field(default_factory=list)
    chapters: List[ChapterMarker] = field(default_factory=list)
    initial_transition: Optional[TransitionType] = None
    final_transition: Optional[TransitionType] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "scene_id": self.scene_id,
            "name": self.name,
            "duration": self.total_duration,
            "actions": len(self.actions),
            "chapters": len(self.chapters),
        }


class CutsceneSystem:
    _instance: Optional[CutsceneSystem] = None

    def __init__(self):
        self._definitions: Dict[str, CutsceneDefinition] = {}
        self._active_scene: Optional[CutsceneDefinition] = None
        self._playback_time: float = 0.0
        self._state: CutsceneState = CutsceneState.IDLE
        self._completed_actions: Set[str] = set()
        self._playback_speed: float = 1.0
        self._play_count: int = 0

    @classmethod
    def get_instance(cls) -> CutsceneSystem:
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def register_scene(self, scene: CutsceneDefinition) -> str:
        scene.total_duration = self._calculate_duration(scene)
        if scene.initial_transition:
            start_action = CutsceneAction(
                action_type=ActionType.FADE_SCREEN,
                trigger_time=0.0,
                duration=1.0,
                params={"transition": scene.initial_transition.value, "from_black": True},
            )
            scene.actions.insert(0, start_action)
        if scene.final_transition:
            end_action = CutsceneAction(
                action_type=ActionType.FADE_SCREEN,
                trigger_time=scene.total_duration - 1.0,
                duration=1.0,
                params={"transition": scene.final_transition.value, "from_black": False},
            )
            scene.actions.append(end_action)
        self._definitions[scene.scene_id] = scene
        return scene.scene_id

    def _calculate_duration(self, scene: CutsceneDefinition) -> float:
        max_time = 0.0
        for action in scene.actions:
            end_time = action.trigger_time + action.duration
            if end_time > max_time:
                max_time = end_time
        for kf in scene.camera_keyframes:
            if kf.time > max_time:
                max_time = kf.time
        return max(max_time, 1.0)

    def play(self, scene_id: str, start_time: float = 0.0) -> bool:
        scene = self._definitions.get(scene_id)
        if scene is None:
            return False

        self._active_scene = scene
        self._playback_time = start_time
        self._state = CutsceneState.PLAYING
        self._completed_actions.clear()
        self._playback_speed = 1.0
        self._play_count += 1
        return True

    def update(self, delta_seconds: float) -> Dict[str, Any]:
        if self._state != CutsceneState.PLAYING or self._active_scene is None:
            return {"state": self._state.value}

        self._playback_time += delta_seconds * self._playback_speed
        scene = self._active_scene

        triggered_actions = []
        for action in scene.actions:
            if action.action_id in self._completed_actions:
                continue
            if action.trigger_time <= self._playback_time:
                triggered_actions.append(action)
                if not action.wait_for_completion:
                    self._completed_actions.add(action.action_id)
                elif self._playback_time >= action.trigger_time + action.duration:
                    self._completed_actions.add(action.action_id)

        if self._playback_time >= scene.total_duration:
            self._state = CutsceneState.FINISHED
            remaining_actions = [
                a for a in scene.actions if a.action_id not in self._completed_actions
            ]
            for action in remaining_actions:
                self._completed_actions.add(action.action_id)

        camera_state = self._interpolate_camera(scene)

        return {
            "state": self._state.value,
            "playback_time": round(self._playback_time, 3),
            "total_duration": scene.total_duration,
            "progress": round(min(1.0, self._playback_time / max(scene.total_duration, 0.01)), 3),
            "triggered_actions": [a.action_type.value for a in triggered_actions],
            "camera": camera_state,
        }

    def _interpolate_camera(
        self, scene: CutsceneDefinition
    ) -> Dict[str, Any]:
        kfs = scene.camera_keyframes
        if not kfs:
            return {"position": (0, 0, 0), "target": (0, 0, 0), "fov": 60.0}

        if self._playback_time <= kfs[0].time:
            kf = kfs[0]
            return {"position": kf.position, "target": kf.target, "fov": kf.fov}

        if self._playback_time >= kfs[-1].time:
            kf = kfs[-1]
            return {"position": kf.position, "target": kf.target, "fov": kf.fov}

        prev_kf = kfs[0]
        next_kf = kfs[-1]
        for i in range(1, len(kfs)):
            if kfs[i].time >= self._playback_time:
                prev_kf = kfs[i - 1]
                next_kf = kfs[i]
                break

        duration = next_kf.time - prev_kf.time
        if duration <= 0:
            t = 1.0
        else:
            t = (self._playback_time - prev_kf.time) / duration

        t = self._apply_easing(t, next_kf.easing)

        def lerp3(a: Tuple[float, float, float], b: Tuple[float, float, float], t: float):
            return (
                a[0] + (b[0] - a[0]) * t,
                a[1] + (b[1] - a[1]) * t,
                a[2] + (b[2] - a[2]) * t,
            )

        return {
            "position": lerp3(prev_kf.position, next_kf.position, t),
            "target": lerp3(prev_kf.target, next_kf.target, t),
            "fov": prev_kf.fov + (next_kf.fov - prev_kf.fov) * t,
        }

    def _apply_easing(self, t: float, easing: str) -> float:
        if easing == "linear":
            return t
        elif easing == "ease_in":
            return t * t
        elif easing == "ease_out":
            return t * (2 - t)
        elif easing == "ease_in_out":
            if t < 0.5:
                return 2 * t * t
            else:
                return -1 + (4 - 2 * t) * t
        return t

    def skip(self) -> bool:
        if not self._active_scene or not self._active_scene.is_skippable:
            return False
        self._state = CutsceneState.SKIPPING
        if self._active_scene:
            self._playback_time = self._active_scene.total_duration
        self._state = CutsceneState.FINISHED
        return True

    def skip_to_chapter(self, chapter_name: str) -> bool:
        if self._active_scene is None:
            return False
        for chapter in self._active_scene.chapters:
            if chapter.name == chapter_name and chapter.is_skip_point:
                self._playback_time = chapter.trigger_time
                return True
        return False

    def pause(self):
        if self._state == CutsceneState.PLAYING:
            self._state = CutsceneState.PAUSED

    def resume(self):
        if self._state == CutsceneState.PAUSED:
            self._state = CutsceneState.PLAYING

    def stop(self):
        self._active_scene = None
        self._state = CutsceneState.IDLE
        self._playback_time = 0.0

    def get_current_state(self) -> Dict[str, Any]:
        if self._active_scene is None:
            return {"state": CutsceneState.IDLE.value}
        return {
            "state": self._state.value,
            "scene_name": self._active_scene.name,
            "playback_time": round(self._playback_time, 3),
            "total_duration": self._active_scene.total_duration,
            "progress": round(min(1.0, self._playback_time / max(self._active_scene.total_duration, 0.01)), 3),
            "is_skippable": self._active_scene.is_skippable,
            "chapters": [
                {"name": c.name, "time": c.trigger_time}
                for c in self._active_scene.chapters
            ],
        }

    def get_stats(self) -> Dict[str, Any]:
        return {
            "total_scenes": len(self._definitions),
            "plays_count": self._play_count,
            "current_state": self._state.value,
            "scenes": [
                {"id": sid, "name": s.name, "duration": s.total_duration}
                for sid, s in self._definitions.items()
            ],
        }


def get_cutscene_system() -> CutsceneSystem:
    return CutsceneSystem.get_instance()