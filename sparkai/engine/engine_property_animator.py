"""
SparkLabs Engine - Property Animator

Universal property animator that can animate any property of any object.
Animation clips compose one or more tracks, each binding a target object
and property name to a start/end value over a duration. A library of
interpolation curves and loop modes is provided.

Architecture:
  PropertyAnimator (Singleton)
    |-- AnimationCurve (interpolation curves)
    |-- AnimationLoop  (looping modes)
    |-- AnimationTrack (a single animated property binding)
    |-- AnimationClip  (a collection of tracks played together)
    |-- PropertyAnimatorSnapshot (immutable snapshot of system state)

Lifecycle:
  1. create_clip(name) -> AnimationClip
  2. add_track(clip_id, track) -> AnimationTrack
  3. play(clip_id) -> bool / pause(clip_id) / stop(clip_id)
  4. update(delta_time) -> List[str] (completed clip ids)
  5. get_snapshot() -> PropertyAnimatorSnapshot
  6. reset() -> None

Usage:
    animator = get_property_animator()
    clip = animator.create_clip("fade_in")
    track = AnimationTrack(
        target_object=my_sprite,
        property_name="alpha",
        start_value=0.0,
        end_value=1.0,
        duration=2.0,
        curve=AnimationCurve.EASE_IN_OUT,
    )
    animator.add_track(clip.clip_id, track)
    animator.play(clip.clip_id)
    completed = animator.update(0.016)
"""

from __future__ import annotations

import math
import threading
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


# =============================================================================
# Enums
# =============================================================================


class AnimationCurve(Enum):
    """Interpolation curves applied to animation progress."""
    LINEAR = "linear"
    EASE_IN = "ease_in"
    EASE_OUT = "ease_out"
    EASE_IN_OUT = "ease_in_out"
    BOUNCE = "bounce"
    ELASTIC = "elastic"
    BACK = "back"
    CIRCULAR = "circular"


class AnimationLoop(Enum):
    """Looping modes for animation tracks."""
    NONE = "none"
    LOOP = "loop"
    PING_PONG = "ping_pong"
    REPEAT = "repeat"


# =============================================================================
# Data Classes
# =============================================================================


@dataclass
class AnimationTrack:
    """A single animated property binding.

    Attributes:
        track_id: Unique identifier (auto-generated).
        target_object: The object whose property is animated. May be ``None``
            for introspection-only tracks.
        property_name: Name of the property to animate.
        start_value: Initial value of the property.
        end_value: Final value of the property.
        duration: Duration of the animation in seconds.
        curve: Interpolation curve applied to the progress.
        loop_mode: Looping behavior of the track.
        elapsed: Time elapsed since the track started playing.
    """
    track_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    target_object: Any = None
    property_name: str = ""
    start_value: Any = 0.0
    end_value: Any = 1.0
    duration: float = 1.0
    curve: AnimationCurve = AnimationCurve.LINEAR
    loop_mode: AnimationLoop = AnimationLoop.NONE
    elapsed: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "track_id": self.track_id,
            "property_name": self.property_name,
            "start_value": self.start_value,
            "end_value": self.end_value,
            "duration": self.duration,
            "curve": self.curve.value,
            "loop_mode": self.loop_mode.value,
            "elapsed": self.elapsed,
        }


@dataclass
class AnimationClip:
    """A collection of tracks played together.

    Attributes:
        clip_id: Unique identifier (auto-generated).
        name: Human-readable name of the clip.
        tracks: The tracks composing the clip.
        duration: Maximum track duration in the clip.
        is_playing: Whether the clip is currently playing.
    """
    clip_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = ""
    tracks: List[AnimationTrack] = field(default_factory=list)
    duration: float = 0.0
    is_playing: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "clip_id": self.clip_id,
            "name": self.name,
            "tracks": [t.to_dict() for t in self.tracks],
            "duration": self.duration,
            "is_playing": self.is_playing,
        }


@dataclass
class PropertyAnimatorSnapshot:
    """Immutable snapshot of the property animator state.

    Attributes:
        total_clips: Number of registered clips.
        playing_clips: Number of clips currently playing.
        total_tracks: Total number of tracks across all clips.
        clips: Serialized clips captured at snapshot time.
        timestamp: Time the snapshot was taken.
    """
    total_clips: int = 0
    playing_clips: int = 0
    total_tracks: int = 0
    clips: List[Dict[str, Any]] = field(default_factory=list)
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_clips": self.total_clips,
            "playing_clips": self.playing_clips,
            "total_tracks": self.total_tracks,
            "clips": list(self.clips),
            "timestamp": self.timestamp,
        }


# =============================================================================
# Property Animator (Singleton)
# =============================================================================


class PropertyAnimator:
    """Singleton universal property animator.

    Manages animation clips composed of tracks that animate arbitrary
    properties of arbitrary objects. The animator is driven by an external
    clock via :meth:`update`, which advances every playing clip and reports
    the ids of clips that completed during the update. All public methods
    are thread-safe.

    Typical usage::

        animator = PropertyAnimator.get_instance()
        clip = animator.create_clip("fade_in")
        animator.add_track(clip.clip_id, track)
        animator.play(clip.clip_id)
        animator.update(0.016)
    """

    _instance: Optional["PropertyAnimator"] = None
    _lock: threading.RLock = threading.RLock()

    # ------------------------------------------------------------------
    # Singleton management
    # ------------------------------------------------------------------

    def __new__(cls) -> "PropertyAnimator":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self) -> None:
        # Guard against re-initialization of the singleton.
        if getattr(self, "_initialized", False):
            return
        self._instance_lock: threading.RLock = threading.RLock()
        self._initialized: bool = True
        self._clips: Dict[str, AnimationClip] = {}
        self._updates: int = 0

    @classmethod
    def get_instance(cls) -> "PropertyAnimator":
        """Return the singleton PropertyAnimator instance (thread-safe)."""
        return cls()

    # ------------------------------------------------------------------
    # Clip Management
    # ------------------------------------------------------------------

    def create_clip(self, name: str) -> AnimationClip:
        """Create and register a new animation clip.

        Args:
            name: Human-readable name of the clip.

        Returns:
            The newly created AnimationClip.
        """
        with self._instance_lock:
            clip = AnimationClip(name=name)
            self._clips[clip.clip_id] = clip
            return clip

    def add_track(self, clip_id: str, track: AnimationTrack) -> AnimationTrack:
        """Attach a track to an existing clip.

        Args:
            clip_id: Identifier of the target clip.
            track: The track to attach.

        Returns:
            The attached track.

        Raises:
            KeyError: If the clip id is not registered.
        """
        with self._instance_lock:
            clip = self._clips.get(clip_id)
            if clip is None:
                raise KeyError(f"Unknown animation clip: {clip_id}")
            clip.tracks.append(track)
            if track.duration > clip.duration:
                clip.duration = track.duration
            return track

    # ------------------------------------------------------------------
    # Playback Control
    # ------------------------------------------------------------------

    def play(self, clip_id: str) -> bool:
        """Start playing a clip.

        Args:
            clip_id: Identifier of the clip to play.

        Returns:
            True if the clip was started, False if not found.
        """
        with self._instance_lock:
            clip = self._clips.get(clip_id)
            if clip is None:
                return False
            clip.is_playing = True
            return True

    def pause(self, clip_id: str) -> None:
        """Pause a playing clip.

        Args:
            clip_id: Identifier of the clip to pause.
        """
        with self._instance_lock:
            clip = self._clips.get(clip_id)
            if clip is not None:
                clip.is_playing = False

    def stop(self, clip_id: str) -> None:
        """Stop a clip and reset the elapsed time of its tracks.

        Args:
            clip_id: Identifier of the clip to stop.
        """
        with self._instance_lock:
            clip = self._clips.get(clip_id)
            if clip is None:
                return
            clip.is_playing = False
            for track in clip.tracks:
                track.elapsed = 0.0

    # ------------------------------------------------------------------
    # Update
    # ------------------------------------------------------------------

    def update(self, delta_time: float) -> List[str]:
        """Advance every playing clip by ``delta_time`` seconds.

        Args:
            delta_time: Time to advance, in seconds.

        Returns:
            The ids of clips that completed during this update.
        """
        completed: List[str] = []
        with self._instance_lock:
            self._updates += 1
            for clip in self._clips.values():
                if not clip.is_playing:
                    continue
                all_tracks_done = True
                for track in clip.tracks:
                    self._advance_track(track, delta_time)
                    if not self._is_track_finished(track):
                        all_tracks_done = False
                if all_tracks_done and clip.tracks:
                    clip.is_playing = False
                    completed.append(clip.clip_id)
            return completed

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------

    def get_active_clips(self) -> List[AnimationClip]:
        """Return a copy of all clips currently playing."""
        with self._instance_lock:
            return [c for c in self._clips.values() if c.is_playing]

    def get_clip(self, clip_id: str) -> Optional[AnimationClip]:
        """Return the clip with the given id, if registered."""
        with self._instance_lock:
            return self._clips.get(clip_id)

    # ------------------------------------------------------------------
    # Status and Snapshot
    # ------------------------------------------------------------------

    def get_status(self) -> Dict[str, Any]:
        """Return a summary of the current system state."""
        with self._instance_lock:
            active = sum(1 for c in self._clips.values() if c.is_playing)
            total_tracks = sum(len(c.tracks) for c in self._clips.values())
            return {
                "total_clips": len(self._clips),
                "active_clips": active,
                "total_tracks": total_tracks,
                "total_updates": self._updates,
            }

    def get_snapshot(self) -> PropertyAnimatorSnapshot:
        """Capture an immutable snapshot of the system state."""
        with self._instance_lock:
            active = sum(1 for c in self._clips.values() if c.is_playing)
            total_tracks = sum(len(c.tracks) for c in self._clips.values())
            return PropertyAnimatorSnapshot(
                total_clips=len(self._clips),
                playing_clips=active,
                total_tracks=total_tracks,
                clips=[c.to_dict() for c in self._clips.values()],
                timestamp=time.time(),
            )

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def reset(self) -> None:
        """Clear all clips and counters."""
        with self._instance_lock:
            self._clips.clear()
            self._updates = 0

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _advance_track(self, track: AnimationTrack, delta_time: float) -> None:
        """Advance a single track by ``delta_time`` seconds and apply its
        interpolated value to the bound property of the target object.
        """
        if track.duration <= 0:
            progress = 1.0
        else:
            track.elapsed += delta_time
            progress = track.elapsed / track.duration

        # Resolve looping before computing the final progress.
        if self._is_track_finished(track):
            progress = self._resolve_loop(track, progress)

        progress = max(0.0, min(1.0, progress))
        eased = self._apply_curve(track.curve, progress)
        try:
            value = self._interpolate(track.start_value, track.end_value, eased)
        except (TypeError, ValueError):
            value = track.end_value

        if track.target_object is not None and track.property_name:
            try:
                setattr(track.target_object, track.property_name, value)
            except (AttributeError, TypeError):
                # The target may not accept the property; keep animating
                # so introspection still reflects progress.
                pass

    def _is_track_finished(self, track: AnimationTrack) -> bool:
        """Return whether a track has completed its current pass."""
        if track.duration <= 0:
            return True
        return track.elapsed >= track.duration

    def _resolve_loop(
        self,
        track: AnimationTrack,
        progress: float,
    ) -> float:
        """Apply the loop mode of a finished track and return the new
        progress value. Returns ``1.0`` when the track should hold.
        """
        mode = track.loop_mode
        if mode == AnimationLoop.NONE:
            return 1.0
        if mode == AnimationLoop.LOOP or mode == AnimationLoop.REPEAT:
            track.elapsed = 0.0
            return 0.0
        if mode == AnimationLoop.PING_PONG:
            # Swap direction by flipping start/end and resetting elapsed.
            track.start_value, track.end_value = track.end_value, track.start_value
            track.elapsed = 0.0
            return 0.0
        return 1.0

    @staticmethod
    def _interpolate(start_value: Any, end_value: Any, progress: float) -> Any:
        """Linearly interpolate between two numeric values."""
        if isinstance(start_value, (int, float)) and isinstance(end_value, (int, float)):
            return start_value + (end_value - start_value) * progress
        # Non-numeric values are not interpolated; return end at progress 1.
        return end_value if progress >= 1.0 else start_value

    @staticmethod
    def _apply_curve(curve: AnimationCurve, progress: float) -> float:
        """Map a linear progress value through the given curve."""
        t = max(0.0, min(1.0, progress))
        if curve == AnimationCurve.LINEAR:
            return t
        if curve == AnimationCurve.EASE_IN:
            return t * t
        if curve == AnimationCurve.EASE_OUT:
            return 1.0 - (1.0 - t) * (1.0 - t)
        if curve == AnimationCurve.EASE_IN_OUT:
            if t < 0.5:
                return 2.0 * t * t
            return 1.0 - 2.0 * (1.0 - t) * (1.0 - t)
        if curve == AnimationCurve.CIRCULAR:
            return 1.0 - math.sqrt(1.0 - t * t)
        if curve == AnimationCurve.BACK:
            c1 = 1.70158
            c3 = c1 + 1.0
            return 1.0 + c3 * (t - 1.0) ** 3 + c1 * (t - 1.0) ** 2
        if curve == AnimationCurve.ELASTIC:
            if t == 0.0 or t == 1.0:
                return t
            c4 = (2.0 * math.pi) / 3.0
            return 2.0 ** (-10.0 * t) * math.sin((t * 10.0 - 0.75) * c4) + 1.0
        if curve == AnimationCurve.BOUNCE:
            n1 = 7.5625
            d1 = 2.75
            if t < 1.0 / d1:
                return n1 * t * t
            if t < 2.0 / d1:
                t -= 1.5 / d1
                return n1 * t * t + 0.75
            if t < 2.5 / d1:
                t -= 2.25 / d1
                return n1 * t * t + 0.9375
            t -= 2.625 / d1
            return n1 * t * t + 0.984375
        return t


# =============================================================================
# Module-Level Accessor
# =============================================================================


def get_property_animator() -> PropertyAnimator:
    """Return the singleton PropertyAnimator instance."""
    return PropertyAnimator.get_instance()
