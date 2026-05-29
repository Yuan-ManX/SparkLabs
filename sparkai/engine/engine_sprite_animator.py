"""
SpriteAnimator - State-driven sprite animation with blend transitions and frame events.

Manages animation clips, playback states, and transition blending for 2D sprite
entities in the SparkLabs game engine. Supports multiple playback modes, crossfade
transitions between clips, per-frame event callbacks, and layered animation stacking
via AnimationLayer.
"""

import threading
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

_time_module = time


class PlaybackMode(Enum):
    """Controls how an animation clip advances through its frame sequence.

    ONCE plays through once and stops on the last frame.
    LOOP repeats the sequence continuously or for a fixed count.
    PING_PONG alternates between forward and reverse playback.
    CLAMP_FOREVER plays once then holds the last frame indefinitely.
    RANDOM_FRAME selects a random frame each update tick.
    """

    ONCE = "once"
    LOOP = "loop"
    PING_PONG = "ping_pong"
    CLAMP_FOREVER = "clamp_forever"
    RANDOM_FRAME = "random_frame"


class BlendType(Enum):
    """Interpolation curve used during animation clip transitions.

    CUT instantly switches to the target clip with no blending.
    CROSSFADE linearly interpolates between source and target frames.
    EASE_IN accelerates from zero at the start of the blend.
    EASE_OUT decelerates to zero at the end of the blend.
    EASE_IN_OUT combines ease-in and ease-out for smooth transitions.
    """

    CUT = "cut"
    CROSSFADE = "crossfade"
    EASE_IN = "ease_in"
    EASE_OUT = "ease_out"
    EASE_IN_OUT = "ease_in_out"

    def compute_blend_factor(self, t: float) -> float:
        """Computes the interpolation factor for a given linear progress.

        Maps a linear time parameter t (0.0 to 1.0) through the easing
        function defined by this blend type. CUT always returns 1.0.

        Args:
            t: Linear progress value between 0.0 and 1.0.

        Returns:
            The eased blend factor between 0.0 and 1.0.
        """
        t = max(0.0, min(1.0, t))
        if self == BlendType.CUT:
            return 1.0
        elif self == BlendType.CROSSFADE:
            return t
        elif self == BlendType.EASE_IN:
            return t * t
        elif self == BlendType.EASE_OUT:
            return 1.0 - (1.0 - t) * (1.0 - t)
        elif self == BlendType.EASE_IN_OUT:
            if t < 0.5:
                return 2.0 * t * t
            return 1.0 - (-2.0 * t + 2.0) ** 2 / 2.0
        return t


class SpriteEvent(Enum):
    """Event types dispatched during animation playback.

    FRAME_ENTER fires when playback reaches a new frame index.
    FRAME_EXIT fires when playback leaves the current frame index.
    ANIM_START fires when an animation clip begins playing.
    ANIM_END fires when a non-looping animation reaches its final frame.
    LOOP_COMPLETE fires each time a looping animation wraps around.
    CUSTOM fires for user-defined events attached to specific frames.
    """

    FRAME_ENTER = "frame_enter"
    FRAME_EXIT = "frame_exit"
    ANIM_START = "anim_start"
    ANIM_END = "anim_end"
    LOOP_COMPLETE = "loop_complete"
    CUSTOM = "custom"


class AnimationLayer(Enum):
    """Layering strategy for stacking multiple animations on one entity.

    BASE is the foundation layer, overwritten by higher layers.
    OVERLAY draws on top of the base with alpha blending.
    ADDITIVE adds pixel values for effects like glow or damage flash.
    MASK selectively reveals or hides portions of lower layers.
    """

    BASE = "base"
    OVERLAY = "overlay"
    ADDITIVE = "additive"
    MASK = "mask"

    @property
    def sort_order(self) -> int:
        """Returns the natural compositing order for this layer.

        Lower values are drawn first, with higher layers composited on top.
        """
        return {
            AnimationLayer.BASE: 0,
            AnimationLayer.OVERLAY: 1,
            AnimationLayer.ADDITIVE: 2,
            AnimationLayer.MASK: 3,
        }[self]


@dataclass
class AnimationClip:
    """Defines a named sequence of sprite frames with playback control.

    Maps a list of frame indices to timing and looping behavior. Events
    can be attached to specific frame positions and fire during playback.
    Each clip has a unique ID for referencing in state transitions.
    """

    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = ""
    frame_indices: List[int] = field(default_factory=list)
    frame_duration: float = 0.1
    playback_mode: PlaybackMode = PlaybackMode.LOOP
    loop_count: int = 0
    events: List[Dict[str, Any]] = field(default_factory=list)
    layer: AnimationLayer = AnimationLayer.BASE
    created_at: float = field(default_factory=_time_module.time)

    def __post_init__(self) -> None:
        """Validates clip parameters after construction."""
        if self.frame_duration <= 0.0:
            raise ValueError(
                f"frame_duration must be positive, got {self.frame_duration}"
            )
        if not self.frame_indices:
            raise ValueError("frame_indices must not be empty")

    @property
    def frame_count(self) -> int:
        """Total number of frames in this animation clip."""
        return len(self.frame_indices)

    @property
    def total_duration(self) -> float:
        """Total playback duration in seconds for one full cycle."""
        return self.frame_count * self.frame_duration

    def get_frame_at_time(self, elapsed: float, loop_iteration: int = 0) -> int:
        """Resolves the frame index at a given elapsed time.

        Respects the playback mode to correctly compute the frame position
        including wrapping for LOOP and reflection for PING_PONG.

        Args:
            elapsed: Elapsed playback time in seconds.
            loop_iteration: Current loop count for loop-limiting logic.

        Returns:
            The resolved frame index into frame_indices.
        """
        total_frames = self.frame_count
        if total_frames == 0:
            return 0

        if self.playback_mode == PlaybackMode.ONCE:
            frame_idx = int(elapsed / self.frame_duration)
            return min(frame_idx, total_frames - 1)

        elif self.playback_mode == PlaybackMode.LOOP:
            if self.loop_count > 0 and loop_iteration >= self.loop_count:
                return total_frames - 1
            frame_idx = int(elapsed / self.frame_duration) % total_frames
            return frame_idx

        elif self.playback_mode == PlaybackMode.PING_PONG:
            cycle_frames = 2 * (total_frames - 1)
            if cycle_frames <= 0:
                return 0
            pos = int(elapsed / self.frame_duration) % cycle_frames
            if pos < total_frames:
                return pos
            return 2 * (total_frames - 1) - pos

        elif self.playback_mode == PlaybackMode.CLAMP_FOREVER:
            frame_idx = int(elapsed / self.frame_duration)
            return min(frame_idx, total_frames - 1)

        elif self.playback_mode == PlaybackMode.RANDOM_FRAME:
            import random
            return random.randint(0, total_frames - 1)

        return 0

    def get_events_at_frame(self, frame_index: int) -> List[Dict[str, Any]]:
        """Returns all events registered for a specific frame index.

        Args:
            frame_index: The frame position to query.

        Returns:
            A list of event dictionaries attached to the given frame.
        """
        return [
            event for event in self.events
            if event.get("frame_index") == frame_index
        ]

    def to_dict(self) -> dict:
        """Serializes the animation clip to a dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "frame_indices": list(self.frame_indices),
            "frame_count": self.frame_count,
            "frame_duration": self.frame_duration,
            "total_duration": self.total_duration,
            "playback_mode": self.playback_mode.value,
            "loop_count": self.loop_count,
            "events": list(self.events),
            "layer": self.layer.value,
            "created_at": self.created_at,
        }

    def __repr__(self) -> str:
        return (
            f"AnimationClip(id={self.id[:8]}..., name={self.name}, "
            f"frames={self.frame_count}, mode={self.playback_mode.value}, "
            f"duration={self.frame_duration}s)"
        )


@dataclass
class AnimationState:
    """Tracks the runtime playback state for an entity's animation.

    Maintains current clip reference, frame position, timing accumulators,
    loop tracking, and transition blending state. Each entity has exactly
    one AnimationState that evolves each update tick.
    """

    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    entity_id: str = ""
    current_clip_id: str = ""
    current_frame: int = 0
    previous_frame: int = -1
    elapsed_time: float = 0.0
    loop_iteration: int = 0
    is_playing: bool = False
    speed_multiplier: float = 1.0
    blend_target_clip_id: str = ""
    blend_progress: float = 0.0
    blend_duration: float = 0.0
    blend_type: BlendType = BlendType.CUT
    blend_source_frame: int = 0
    created_at: float = field(default_factory=_time_module.time)

    def __post_init__(self) -> None:
        """Validates state parameters after construction."""
        if self.speed_multiplier <= 0.0:
            raise ValueError(
                f"speed_multiplier must be positive, got {self.speed_multiplier}"
            )

    @property
    def is_blending(self) -> bool:
        """Whether a transition blend is currently active."""
        return bool(self.blend_target_clip_id) and self.blend_progress < 1.0

    @property
    def effective_frame(self) -> int:
        """The resolved frame index taking blend state into account."""
        return self.current_frame

    def to_dict(self) -> dict:
        """Serializes the animation state to a dictionary."""
        return {
            "id": self.id,
            "entity_id": self.entity_id,
            "current_clip_id": self.current_clip_id,
            "current_frame": self.current_frame,
            "previous_frame": self.previous_frame,
            "elapsed_time": self.elapsed_time,
            "loop_iteration": self.loop_iteration,
            "is_playing": self.is_playing,
            "speed_multiplier": self.speed_multiplier,
            "is_blending": self.is_blending,
            "blend_target_clip_id": self.blend_target_clip_id,
            "blend_progress": self.blend_progress,
            "blend_duration": self.blend_duration,
            "blend_type": self.blend_type.value,
            "blend_source_frame": self.blend_source_frame,
            "created_at": self.created_at,
        }

    def __repr__(self) -> str:
        return (
            f"AnimationState(id={self.id[:8]}..., entity={self.entity_id[:8]}..., "
            f"clip={self.current_clip_id[:8]}..., frame={self.current_frame}, "
            f"playing={self.is_playing})"
        )


@dataclass
class TransitionConfig:
    """Defines a transition rule between two animation clips.

    When playback switches from the source clip to the target clip and a
    matching TransitionConfig exists, the transition uses the specified
    blend type and duration instead of an instant cut. Optional condition
    strings enable conditional transition routing.
    """

    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    from_clip_id: str = ""
    to_clip_id: str = ""
    blend_type: BlendType = BlendType.CROSSFADE
    blend_duration: float = 0.25
    condition: str = ""
    created_at: float = field(default_factory=_time_module.time)

    def __post_init__(self) -> None:
        """Validates transition configuration after construction."""
        if self.blend_duration < 0.0:
            raise ValueError(
                f"blend_duration must be non-negative, got {self.blend_duration}"
            )

    @property
    def transition_key(self) -> str:
        """Composite key for looking up transitions by source and target."""
        return f"{self.from_clip_id}->{self.to_clip_id}"

    def to_dict(self) -> dict:
        """Serializes the transition config to a dictionary."""
        return {
            "id": self.id,
            "from_clip_id": self.from_clip_id,
            "to_clip_id": self.to_clip_id,
            "transition_key": self.transition_key,
            "blend_type": self.blend_type.value,
            "blend_duration": self.blend_duration,
            "condition": self.condition,
            "created_at": self.created_at,
        }

    def __repr__(self) -> str:
        return (
            f"TransitionConfig(id={self.id[:8]}..., "
            f"from={self.from_clip_id[:8]}..., "
            f"to={self.to_clip_id[:8]}..., "
            f"blend={self.blend_type.value}, dur={self.blend_duration}s)"
        )


class SpriteAnimator:
    """Singleton manager for sprite animation playback and transitions.

    Owns all animation clip definitions, per-entity playback states, and
    transition rules. Drives frame-by-frame animation updates, resolves
    blend progress during transitions, and dispatches frame events.

    Thread-safe via a reentrant lock. Use get_sprite_animator() or
    SpriteAnimator.get_instance() to obtain the singleton instance.
    """

    _instance: Optional["SpriteAnimator"] = None
    _lock: threading.RLock = threading.RLock()

    # ------------------------------------------------------------------
    # Singleton construction
    # ------------------------------------------------------------------

    def __new__(cls) -> "SpriteAnimator":
        """Thread-safe singleton construction with double-check locking."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    instance = super().__new__(cls)
                    instance._initialized = False
                    cls._instance = instance
        return cls._instance

    def __init__(self) -> None:
        """Initializes internal state on first construction only."""
        if getattr(self, "_initialized", False):
            return
        self._clips: Dict[str, AnimationClip] = {}
        self._states: Dict[str, AnimationState] = {}
        self._transitions: Dict[str, TransitionConfig] = {}
        self._stats: Dict[str, Any] = {
            "total_clips_created": 0,
            "total_states_created": 0,
            "total_transitions_added": 0,
            "total_frames_advanced": 0,
            "total_events_fired": 0,
            "total_blends_completed": 0,
        }
        self._initialized = True

    @classmethod
    def get_instance(cls) -> "SpriteAnimator":
        """Returns the singleton SpriteAnimator instance."""
        return cls()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _lookup_clip(self, clip_id: str) -> AnimationClip:
        """Retrieves an animation clip by ID with validation.

        Args:
            clip_id: The unique clip identifier.

        Returns:
            The matching AnimationClip.

        Raises:
            KeyError: If no clip exists with the given ID.
        """
        clip = self._clips.get(clip_id)
        if clip is None:
            raise KeyError(f"AnimationClip not found: {clip_id}")
        return clip

    def _lookup_state(self, entity_id: str) -> AnimationState:
        """Retrieves the animation state for an entity with validation.

        Args:
            entity_id: The entity identifier.

        Returns:
            The matching AnimationState.

        Raises:
            KeyError: If no state exists for the given entity.
        """
        state = self._states.get(entity_id)
        if state is None:
            raise KeyError(f"AnimationState not found for entity: {entity_id}")
        return state

    def _resolve_transition(
        self, from_clip_id: str, to_clip_id: str
    ) -> Optional[TransitionConfig]:
        """Finds a transition config matching the given clip pair.

        Returns None if no explicit transition is registered, implying
        an instant CUT should be used.

        Args:
            from_clip_id: The source clip identifier.
            to_clip_id: The target clip identifier.

        Returns:
            The TransitionConfig if found, None otherwise.
        """
        key = f"{from_clip_id}->{to_clip_id}"
        return self._transitions.get(key)

    def _collect_events(
        self,
        state: AnimationState,
        clip: AnimationClip,
        old_frame: int,
        new_frame: int,
        loop_wrapped: bool,
    ) -> List[Dict[str, Any]]:
        """Collects frame and animation lifecycle events for this update.

        Detects frame changes, animation start/end, loop completions,
        and fires any custom events attached to the current frame index.

        Args:
            state: The entity's animation state.
            clip: The currently playing animation clip.
            old_frame: The frame index before this update.
            new_frame: The frame index after this update.
            loop_wrapped: Whether a loop boundary was crossed.

        Returns:
            A list of event dictionaries describing what occurred.
        """
        events_fired: List[Dict[str, Any]] = []

        if old_frame != new_frame:
            if old_frame >= 0:
                events_fired.append({
                    "event_type": SpriteEvent.FRAME_EXIT.value,
                    "entity_id": state.entity_id,
                    "clip_id": clip.id,
                    "clip_name": clip.name,
                    "frame_index": old_frame,
                    "sprite_index": (
                        clip.frame_indices[old_frame]
                        if old_frame < len(clip.frame_indices)
                        else -1
                    ),
                })
            events_fired.append({
                "event_type": SpriteEvent.FRAME_ENTER.value,
                "entity_id": state.entity_id,
                "clip_id": clip.id,
                "clip_name": clip.name,
                "frame_index": new_frame,
                "sprite_index": (
                    clip.frame_indices[new_frame]
                    if new_frame < len(clip.frame_indices)
                    else -1
                ),
            })

        if loop_wrapped:
            events_fired.append({
                "event_type": SpriteEvent.LOOP_COMPLETE.value,
                "entity_id": state.entity_id,
                "clip_id": clip.id,
                "clip_name": clip.name,
                "loop_iteration": state.loop_iteration,
            })

        custom_events = clip.get_events_at_frame(new_frame)
        for custom in custom_events:
            events_fired.append({
                "event_type": SpriteEvent.CUSTOM.value,
                "entity_id": state.entity_id,
                "clip_id": clip.id,
                "clip_name": clip.name,
                "frame_index": new_frame,
                "event_data": custom.get("event_data"),
            })

        return events_fired

    def _check_animation_end(
        self, state: AnimationState, clip: AnimationClip, new_frame: int
    ) -> bool:
        """Determines if the animation has reached its natural end.

        Evaluates if playback should stop based on the playback mode
        and the current frame position. Used to fire ANIM_END events.

        Args:
            state: The entity's animation state.
            clip: The currently playing animation clip.
            new_frame: The newly computed frame index.

        Returns:
            True if the animation has completed, False otherwise.
        """
        total_frames = clip.frame_count
        if clip.playback_mode == PlaybackMode.ONCE:
            return new_frame >= total_frames - 1
        elif clip.playback_mode == PlaybackMode.CLAMP_FOREVER:
            return new_frame >= total_frames - 1
        elif clip.playback_mode == PlaybackMode.LOOP:
            if clip.loop_count > 0:
                return state.loop_iteration >= clip.loop_count
        return False

    # ------------------------------------------------------------------
    # Public API: Clip management
    # ------------------------------------------------------------------

    def create_clip(
        self,
        name: str,
        frame_indices: List[int],
        frame_duration: float = 0.1,
        playback_mode: PlaybackMode = PlaybackMode.LOOP,
        loop_count: int = 0,
        events: Optional[List[Dict[str, Any]]] = None,
        layer: AnimationLayer = AnimationLayer.BASE,
    ) -> AnimationClip:
        """Creates and registers a new animation clip definition.

        Args:
            name: Human-readable name for the clip.
            frame_indices: Ordered list of sprite frame indices.
            frame_duration: Time in seconds per frame.
            playback_mode: The playback behavior for this clip.
            loop_count: Max loop iterations (0 for unlimited in LOOP mode).
            events: Optional list of frame event descriptors.
            layer: The compositing layer for this animation.

        Returns:
            The newly created AnimationClip.

        Raises:
            ValueError: If frame_indices is empty or frame_duration <= 0.
        """
        with self._lock:
            if not frame_indices:
                raise ValueError("frame_indices must not be empty")
            if frame_duration <= 0.0:
                raise ValueError("frame_duration must be positive")

            clip = AnimationClip(
                name=name,
                frame_indices=list(frame_indices),
                frame_duration=frame_duration,
                playback_mode=playback_mode,
                loop_count=loop_count,
                events=list(events) if events else [],
                layer=layer,
            )
            self._clips[clip.id] = clip
            self._stats["total_clips_created"] += 1
            return clip

    def get_clip(self, clip_id: str) -> Optional[AnimationClip]:
        """Retrieves an animation clip by its unique ID.

        Args:
            clip_id: The clip identifier.

        Returns:
            The AnimationClip if found, None otherwise.
        """
        with self._lock:
            return self._clips.get(clip_id)

    def get_clip_by_name(self, name: str) -> Optional[AnimationClip]:
        """Finds the first animation clip with the given name.

        Args:
            name: The clip name to search for.

        Returns:
            The matching AnimationClip if found, None otherwise.
        """
        with self._lock:
            for clip in self._clips.values():
                if clip.name == name:
                    return clip
            return None

    def remove_clip(self, clip_id: str) -> bool:
        """Removes an animation clip and its associated transitions.

        Also cleans up any transition configs that reference this clip
        as source or target.

        Args:
            clip_id: The clip identifier to remove.

        Returns:
            True if the clip was found and removed, False otherwise.
        """
        with self._lock:
            if clip_id not in self._clips:
                return False

            del self._clips[clip_id]

            keys_to_remove = []
            for key, trans in self._transitions.items():
                if trans.from_clip_id == clip_id or trans.to_clip_id == clip_id:
                    keys_to_remove.append(key)
            for key in keys_to_remove:
                del self._transitions[key]

            return True

    def list_clips(self) -> List[AnimationClip]:
        """Returns all registered animation clips.

        Returns:
            A list of all AnimationClip objects.
        """
        with self._lock:
            return list(self._clips.values())

    # ------------------------------------------------------------------
    # Public API: State management
    # ------------------------------------------------------------------

    def create_state(
        self, entity_id: str, initial_clip_id: str
    ) -> AnimationState:
        """Creates and registers an animation state for an entity.

        Each entity can have exactly one state. The state starts paused
        so playback must be explicitly started via play().

        Args:
            entity_id: The entity to attach animation state to.
            initial_clip_id: The clip this entity will reference.

        Returns:
            The newly created AnimationState.

        Raises:
            KeyError: If initial_clip_id does not reference a valid clip.
        """
        with self._lock:
            if initial_clip_id not in self._clips:
                raise KeyError(f"AnimationClip not found: {initial_clip_id}")

            state = AnimationState(
                entity_id=entity_id,
                current_clip_id=initial_clip_id,
                is_playing=False,
            )
            self._states[entity_id] = state
            self._stats["total_states_created"] += 1
            return state

    def get_state(self, entity_id: str) -> Optional[AnimationState]:
        """Retrieves the animation state for an entity.

        Args:
            entity_id: The entity identifier.

        Returns:
            The AnimationState if found, None otherwise.
        """
        with self._lock:
            return self._states.get(entity_id)

    def remove_state(self, entity_id: str) -> bool:
        """Removes the animation state for an entity.

        Args:
            entity_id: The entity identifier.

        Returns:
            True if the state was found and removed, False otherwise.
        """
        with self._lock:
            if entity_id in self._states:
                del self._states[entity_id]
                return True
            return False

    # ------------------------------------------------------------------
    # Public API: Transition management
    # ------------------------------------------------------------------

    def add_transition(
        self,
        from_clip_id: str,
        to_clip_id: str,
        blend_type: BlendType = BlendType.CROSSFADE,
        blend_duration: float = 0.25,
        condition: str = "",
    ) -> TransitionConfig:
        """Registers a transition rule between two animation clips.

        When playback switches from from_clip to to_clip, this transition
        config determines the blend behavior. If no transition is registered
        for a clip pair, an instant CUT is used.

        Args:
            from_clip_id: The source clip identifier.
            to_clip_id: The target clip identifier.
            blend_type: The interpolation curve for the blend.
            blend_duration: Duration of the blend in seconds.
            condition: Optional condition string for conditional routing.

        Returns:
            The created TransitionConfig.

        Raises:
            KeyError: If either clip ID does not exist.
        """
        with self._lock:
            if from_clip_id not in self._clips:
                raise KeyError(f"AnimationClip not found: {from_clip_id}")
            if to_clip_id not in self._clips:
                raise KeyError(f"AnimationClip not found: {to_clip_id}")

            config = TransitionConfig(
                from_clip_id=from_clip_id,
                to_clip_id=to_clip_id,
                blend_type=blend_type,
                blend_duration=blend_duration,
                condition=condition,
            )
            self._transitions[config.transition_key] = config
            self._stats["total_transitions_added"] += 1
            return config

    def get_transition(
        self, from_clip_id: str, to_clip_id: str
    ) -> Optional[TransitionConfig]:
        """Looks up a transition config for a clip pair.

        Args:
            from_clip_id: The source clip identifier.
            to_clip_id: The target clip identifier.

        Returns:
            The TransitionConfig if found, None otherwise.
        """
        with self._lock:
            key = f"{from_clip_id}->{to_clip_id}"
            return self._transitions.get(key)

    def remove_transition(self, from_clip_id: str, to_clip_id: str) -> bool:
        """Removes a transition rule between two clips.

        Args:
            from_clip_id: The source clip identifier.
            to_clip_id: The target clip identifier.

        Returns:
            True if the transition was found and removed, False otherwise.
        """
        with self._lock:
            key = f"{from_clip_id}->{to_clip_id}"
            if key in self._transitions:
                del self._transitions[key]
                return True
            return False

    def list_transitions(self) -> List[TransitionConfig]:
        """Returns all registered transition configs.

        Returns:
            A list of all TransitionConfig objects.
        """
        with self._lock:
            return list(self._transitions.values())

    # ------------------------------------------------------------------
    # Public API: Playback control
    # ------------------------------------------------------------------

    def play(
        self,
        entity_id: str,
        clip_id: str,
        speed: float = 1.0,
    ) -> None:
        """Starts or switches animation playback for an entity.

        If a transition is registered from the current clip to the new clip,
        blending begins. Otherwise the switch is instant. If the entity
        is already playing the same clip, only the speed is updated.

        Args:
            entity_id: The entity to control playback for.
            clip_id: The clip to start playing.
            speed: Playback speed multiplier (1.0 is normal speed).

        Raises:
            KeyError: If the entity state or clip is not found.
        """
        with self._lock:
            state = self._lookup_state(entity_id)
            clip = self._lookup_clip(clip_id)

            if state.current_clip_id == clip_id and state.is_playing:
                state.speed_multiplier = speed
                return

            transition = self._resolve_transition(state.current_clip_id, clip_id)

            if transition is not None and transition.blend_duration > 0.0:
                state.blend_target_clip_id = clip_id
                state.blend_progress = 0.0
                state.blend_duration = transition.blend_duration
                state.blend_type = transition.blend_type
                state.blend_source_frame = state.current_frame
            else:
                state.blend_target_clip_id = ""
                state.blend_progress = 0.0
                state.blend_duration = 0.0
                state.blend_type = BlendType.CUT

            state.current_clip_id = clip_id
            state.elapsed_time = 0.0
            state.current_frame = 0
            state.previous_frame = -1
            state.loop_iteration = 0
            state.speed_multiplier = speed
            state.is_playing = True

    def stop(self, entity_id: str) -> None:
        """Stops animation playback for an entity.

        The entity remains on its current frame but no longer advances.
        Call play() to resume playback.

        Args:
            entity_id: The entity to stop playback for.

        Raises:
            KeyError: If no state exists for the entity.
        """
        with self._lock:
            state = self._lookup_state(entity_id)
            state.is_playing = False

    def pause(self, entity_id: str) -> None:
        """Pauses animation playback without resetting frame position.

        Equivalent to stop() in behavior.

        Args:
            entity_id: The entity to pause.

        Raises:
            KeyError: If no state exists for the entity.
        """
        self.stop(entity_id)

    def resume(self, entity_id: str) -> None:
        """Resumes playback from the current paused position.

        Args:
            entity_id: The entity to resume.

        Raises:
            KeyError: If no state exists for the entity.
        """
        with self._lock:
            state = self._lookup_state(entity_id)
            state.is_playing = True

    def set_speed(self, entity_id: str, speed: float) -> None:
        """Adjusts the playback speed multiplier for an entity.

        Args:
            entity_id: The entity to adjust.
            speed: New speed multiplier (must be positive).

        Raises:
            KeyError: If no state exists for the entity.
            ValueError: If speed is not positive.
        """
        with self._lock:
            if speed <= 0.0:
                raise ValueError(
                    f"speed must be positive, got {speed}"
                )
            state = self._lookup_state(entity_id)
            state.speed_multiplier = speed

    def set_frame(self, entity_id: str, frame_index: int) -> None:
        """Jumps to a specific frame index in the current clip.

        Args:
            entity_id: The entity to reposition.
            frame_index: The target frame index (0-based).

        Raises:
            KeyError: If no state exists for the entity.
            IndexError: If frame_index is out of range.
        """
        with self._lock:
            state = self._lookup_state(entity_id)
            clip = self._lookup_clip(state.current_clip_id)
            if frame_index < 0 or frame_index >= clip.frame_count:
                raise IndexError(
                    f"frame_index {frame_index} out of range "
                    f"[0, {clip.frame_count - 1}]"
                )
            state.current_frame = frame_index
            state.elapsed_time = frame_index * clip.frame_duration

    # ------------------------------------------------------------------
    # Public API: Frame update
    # ------------------------------------------------------------------

    def update(self, entity_id: str, delta_time: float) -> Dict[str, Any]:
        """Advances animation state for one entity by a time step.

        This is the core per-frame update. It advances elapsed time,
        resolves the current frame based on the playback mode, processes
        blend transitions, and collects all events fired during this tick.

        Args:
            entity_id: The entity to update.
            delta_time: Time elapsed since the last update in seconds.

        Returns:
            A dictionary with keys:
                current_frame: The resolved sprite frame index.
                blend_progress: Transition blend factor (0.0-1.0).
                blend_frame: Blending source frame index (or -1).
                blend_type: Active blend type string (or empty).
                events_fired: List of event dictionaries.
                is_playing: Whether playback is still active.
        """
        state = self._lookup_state(entity_id)

        if not state.is_playing:
            return {
                "current_frame": (
                    self._lookup_clip(state.current_clip_id)
                    .frame_indices[state.current_frame]
                    if state.current_frame < len(
                        self._lookup_clip(state.current_clip_id).frame_indices
                    )
                    else 0
                ),
                "blend_progress": 0.0,
                "blend_frame": -1,
                "blend_type": "",
                "events_fired": [],
                "is_playing": False,
            }

        clip = self._lookup_clip(state.current_clip_id)
        events_fired: List[Dict[str, Any]] = []

        old_frame = state.current_frame
        old_loop = state.loop_iteration

        state.elapsed_time += delta_time * state.speed_multiplier

        loop_boundary_crossed = False
        total_duration = clip.total_duration
        if total_duration > 0.0:
            new_loop = int(state.elapsed_time / total_duration)
            if new_loop > old_loop:
                state.loop_iteration = new_loop
                loop_boundary_crossed = True

        new_frame = clip.get_frame_at_time(state.elapsed_time, state.loop_iteration)

        if clip.playback_mode == PlaybackMode.ONCE and new_frame >= clip.frame_count - 1:
            state.is_playing = False

        if (
            clip.playback_mode == PlaybackMode.CLAMP_FOREVER
            and new_frame >= clip.frame_count - 1
        ):
            state.is_playing = False

        if (
            clip.playback_mode == PlaybackMode.LOOP
            and clip.loop_count > 0
            and state.loop_iteration >= clip.loop_count
        ):
            state.is_playing = False
            new_frame = clip.frame_count - 1

        anim_just_started = old_frame < 0
        if anim_just_started:
            events_fired.append({
                "event_type": SpriteEvent.ANIM_START.value,
                "entity_id": state.entity_id,
                "clip_id": clip.id,
                "clip_name": clip.name,
            })

        frame_events = self._collect_events(
            state, clip, old_frame, new_frame, loop_boundary_crossed
        )
        events_fired.extend(frame_events)

        anim_ended = self._check_animation_end(state, clip, new_frame)
        if anim_ended:
            events_fired.append({
                "event_type": SpriteEvent.ANIM_END.value,
                "entity_id": state.entity_id,
                "clip_id": clip.id,
                "clip_name": clip.name,
                "final_frame": new_frame,
            })

        state.previous_frame = state.current_frame
        state.current_frame = new_frame

        self._stats["total_frames_advanced"] += 1
        self._stats["total_events_fired"] += len(events_fired)

        blend_frame = -1
        blend_type_str = ""
        blend_progress = 0.0

        if state.is_blending:
            state.blend_progress += delta_time / max(state.blend_duration, 0.001)
            state.blend_progress = min(state.blend_progress, 1.0)

            blend_progress = state.blend_type.compute_blend_factor(
                state.blend_progress
            )
            blend_frame = state.blend_source_frame
            blend_type_str = state.blend_type.value

            if state.blend_progress >= 1.0:
                state.blend_target_clip_id = ""
                state.blend_progress = 0.0
                self._stats["total_blends_completed"] += 1

        current_sprite = (
            clip.frame_indices[state.current_frame]
            if state.current_frame < len(clip.frame_indices)
            else 0
        )

        return {
            "current_frame": current_sprite,
            "blend_progress": blend_progress,
            "blend_frame": blend_frame,
            "blend_type": blend_type_str,
            "events_fired": events_fired,
            "is_playing": state.is_playing,
        }

    # ------------------------------------------------------------------
    # Public API: Statistics and queries
    # ------------------------------------------------------------------

    def get_stats(self) -> Dict[str, Any]:
        """Returns a comprehensive statistics dictionary for monitoring.

        Includes clip, state, and transition counts, active animation
        metrics, and cumulative event/frame counters.

        Returns:
            A dictionary with string keys and numeric/collection values.
        """
        with self._lock:
            clip_count = len(self._clips)
            state_count = len(self._states)
            transition_count = len(self._transitions)

            active_states = sum(
                1 for s in self._states.values() if s.is_playing
            )
            blending_states = sum(
                1 for s in self._states.values() if s.is_blending
            )
            paused_states = state_count - active_states

            avg_frame_duration = 0.0
            if clip_count > 0:
                avg_frame_duration = sum(
                    c.frame_duration for c in self._clips.values()
                ) / clip_count

            mode_distribution: Dict[str, int] = {}
            for clip in self._clips.values():
                mode_name = clip.playback_mode.value
                mode_distribution[mode_name] = (
                    mode_distribution.get(mode_name, 0) + 1
                )

            layer_distribution: Dict[str, int] = {}
            for clip in self._clips.values():
                layer_name = clip.layer.value
                layer_distribution[layer_name] = (
                    layer_distribution.get(layer_name, 0) + 1
                )

            blend_distribution: Dict[str, int] = {}
            for trans in self._transitions.values():
                blend_name = trans.blend_type.value
                blend_distribution[blend_name] = (
                    blend_distribution.get(blend_name, 0) + 1
                )

            total_frame_indices = sum(
                c.frame_count for c in self._clips.values()
            )

            return {
                "clip_count": clip_count,
                "state_count": state_count,
                "transition_count": transition_count,
                "active_states": active_states,
                "blending_states": blending_states,
                "paused_states": paused_states,
                "total_clips_created": self._stats["total_clips_created"],
                "total_states_created": self._stats["total_states_created"],
                "total_transitions_added": self._stats["total_transitions_added"],
                "total_frames_advanced": self._stats["total_frames_advanced"],
                "total_events_fired": self._stats["total_events_fired"],
                "total_blends_completed": self._stats["total_blends_completed"],
                "avg_frame_duration": round(avg_frame_duration, 4),
                "total_frame_indices": total_frame_indices,
                "mode_distribution": mode_distribution,
                "layer_distribution": layer_distribution,
                "blend_distribution": blend_distribution,
            }

    def reset(self) -> None:
        """Performs a complete reset of all animator state.

        Clears all clips, states, transitions, and resets statistics
        counters. The singleton instance remains valid.
        """
        with self._lock:
            self._clips.clear()
            self._states.clear()
            self._transitions.clear()
            self._stats = {
                "total_clips_created": 0,
                "total_states_created": 0,
                "total_transitions_added": 0,
                "total_frames_advanced": 0,
                "total_events_fired": 0,
                "total_blends_completed": 0,
            }

    def __repr__(self) -> str:
        with self._lock:
            active = sum(1 for s in self._states.values() if s.is_playing)
            return (
                f"SpriteAnimator(clips={len(self._clips)}, "
                f"states={len(self._states)}, "
                f"active={active}, "
                f"transitions={len(self._transitions)})"
            )


def get_sprite_animator() -> SpriteAnimator:
    """Module-level accessor for the SpriteAnimator singleton.

    Convenience function that returns the singleton instance without
    needing to reference SpriteAnimator.get_instance() directly.

    Returns:
        The singleton SpriteAnimator instance.
    """
    return SpriteAnimator.get_instance()