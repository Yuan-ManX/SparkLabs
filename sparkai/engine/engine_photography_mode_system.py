"""
SparkLabs Engine - Photography Mode System

Manages in-game photography with camera presets, filter pipelines,
composition guides, photo albums, challenges, and AI-driven scene
detection. Players capture, rate, and share photos while completing
photography quests that reward exploration and artistic skill.

Architecture:
  PhotographyModeSystem (singleton)
    |-- CameraPreset, FilterPreset, CompositionGuide, PhotoQuality,
       PhotoCategory, PhotographyEventKind
    |-- FilterDefinition, CameraSettings, CompositionOverlay, PhotoEntry,
       PhotoAlbum, PhotoChallenge, SceneDetection, PhotographyConfig,
       PhotographyStats, PhotographySnapshot, PhotographyEvent
    |-- get_photography_mode_system

Core Capabilities:
  - register_camera_preset / remove_camera_preset / get_camera_preset / list_camera_presets
  - register_filter / remove_filter / get_filter / list_filters
  - register_composition_guide / get_composition_guide / list_composition_guides
  - capture_photo / get_photo / list_photos / delete_photo
  - create_album / delete_album / get_album / list_albums / add_photo_to_album
  - register_challenge / remove_challenge / get_challenge / list_challenges
  - start_challenge / submit_photo / complete_challenge
  - rate_photo / get_photo_score / get_leaderboard
  - detect_scene / get_scene_suggestion / get_best_camera_settings
  - apply_filter / apply_composition_guide
  - tick / set_config / get_config
  - list_events / get_stats / get_status / get_snapshot / reset

The class implements the singleton pattern with double-checked locking
using ``threading.RLock``; consumers should obtain the instance through
:meth:`PhotographyModeSystem.get_instance` or the module-level
:func:`get_photography_mode_system` factory.
"""

from __future__ import annotations

import math
import threading
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Capacity Constants
# ---------------------------------------------------------------------------

_MAX_CAMERA_PRESETS: int = 100
_MAX_FILTERS: int = 200
_MAX_COMPOSITION_GUIDES: int = 50
_MAX_PHOTOS: int = 500000
_MAX_ALBUMS: int = 100000
_MAX_CHALLENGES: int = 500
_MAX_CHALLENGE_SUBMISSIONS: int = 1000000
_MAX_EVENTS: int = 10000


# ---------------------------------------------------------------------------
# Helper Functions
# ---------------------------------------------------------------------------

_LOCK = threading.RLock()


def _now() -> float:
    return time.time()


def _new_id(prefix: str = "") -> str:
    base = uuid.uuid4().hex[:12]
    return f"{prefix}_{base}" if prefix else base


def _safe_float(value: Any, default: float = 0.0) -> float:
    if value is None or value == "":
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _safe_int(value: Any, default: int = 0) -> int:
    if value is None or value == "":
        return default
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _clamp(value: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, value))


def _evict_fifo_list(store: List[Any], max_size: int) -> None:
    cap = max(1, int(max_size))
    while len(store) > cap:
        if not store:
            break
        store.pop(0)


def _dataclass_to_dict(obj: Any) -> Any:
    if hasattr(obj, "__dataclass_fields__"):
        result: Dict[str, Any] = {}
        for k in obj.__dataclass_fields__:
            v = getattr(obj, k)
            if hasattr(v, "__dataclass_fields__"):
                result[k] = _dataclass_to_dict(v)
            elif hasattr(v, "to_dict") and callable(v.to_dict):
                result[k] = v.to_dict()
            elif isinstance(v, list):
                result[k] = [_dataclass_to_dict(i) for i in v]
            elif isinstance(v, dict):
                result[k] = {kk: _dataclass_to_dict(vv) for kk, vv in v.items()}
            elif isinstance(v, tuple):
                result[k] = list(v)
            else:
                result[k] = v
        return result
    return obj


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class CameraPreset(str, Enum):
    """Pre-defined camera modes for photography."""
    FREE = "free"
    PORTRAIT = "portrait"
    LANDSCAPE = "landscape"
    ACTION = "action"
    MACRO = "macro"
    PANORAMIC = "panoramic"
    NIGHT = "night"
    HDR = "hdr"
    CINEMATIC = "cinematic"
    DRONE = "drone"


class FilterPreset(str, Enum):
    """Visual filter styles applied to photos."""
    NONE = "none"
    VINTAGE = "vintage"
    NOIR = "noir"
    VIBRANT = "vibrant"
    SOFT = "soft"
    DRAMATIC = "dramatic"
    WARM = "warm"
    COOL = "cool"
    SEPIA = "sepia"
    PASTEL = "pastel"
    CYBERPUNK = "cyberpunk"
    WATERCOLOR = "watercolor"


class CompositionGuide(str, Enum):
    """Composition overlay guides for framing photos."""
    NONE = "none"
    RULE_OF_THIRDS = "rule_of_thirds"
    GOLDEN_RATIO = "golden_ratio"
    CENTER = "center"
    DIAGONAL = "diagonal"
    GRID = "grid"
    SPIRAL = "spiral"
    TRIANGULAR = "triangular"
    FRAME_WITHIN_FRAME = "frame_within_frame"
    LEADING_LINES = "leading_lines"


class PhotoQuality(str, Enum):
    """Quality tier of a captured photo."""
    COMMON = "common"
    UNCOMMON = "uncommon"
    RARE = "rare"
    EPIC = "epic"
    LEGENDARY = "legendary"
    MASTERPIECE = "masterpiece"


class PhotoCategory(str, Enum):
    """Subject category of a photo."""
    LANDSCAPE = "landscape"
    PORTRAIT = "portrait"
    WILDLIFE = "wildlife"
    ACTION = "action"
    ARCHITECTURE = "architecture"
    NATURE = "nature"
    CHARACTER = "character"
    EVENT = "event"
    ABSTRACT = "abstract"
    GROUP = "group"


class PhotographyEventKind(str, Enum):
    """Audit event types emitted by the photography system."""
    CAMERA_PRESET_REGISTERED = "camera_preset_registered"
    CAMERA_PRESET_REMOVED = "camera_preset_removed"
    FILTER_REGISTERED = "filter_registered"
    FILTER_REMOVED = "filter_removed"
    COMPOSITION_REGISTERED = "composition_registered"
    PHOTO_CAPTURED = "photo_captured"
    PHOTO_DELETED = "photo_deleted"
    ALBUM_CREATED = "album_created"
    ALBUM_DELETED = "album_deleted"
    PHOTO_ADDED_TO_ALBUM = "photo_added_to_album"
    CHALLENGE_REGISTERED = "challenge_registered"
    CHALLENGE_STARTED = "challenge_started"
    CHALLENGE_SUBMITTED = "challenge_submitted"
    CHALLENGE_COMPLETED = "challenge_completed"
    PHOTO_RATED = "photo_rated"
    SCENE_DETECTED = "scene_detected"
    CONFIG_UPDATED = "config_updated"
    RESET = "reset"
    TICK = "tick"


# ---------------------------------------------------------------------------
# Data Classes
# ---------------------------------------------------------------------------

@dataclass
class FilterDefinition:
    """Definition of a visual filter."""
    filter_id: str
    name: str
    description: str = ""
    brightness: float = 1.0
    contrast: float = 1.0
    saturation: float = 1.0
    hue_shift: float = 0.0
    temperature: float = 0.0
    tint: float = 0.0
    vignette: float = 0.0
    grain: float = 0.0
    blur: float = 0.0
    sharpen: float = 0.0
    icon: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class CameraSettings:
    """Camera parameters for a photo capture."""
    preset: str = CameraPreset.FREE.value
    focal_length: float = 50.0
    aperture: float = 2.8
    shutter_speed: float = 0.01
    iso: int = 100
    exposure_compensation: float = 0.0
    white_balance: str = "auto"
    focus_distance: float = 10.0
    field_of_view: float = 60.0
    depth_of_field: float = 0.5
    zoom: float = 1.0
    position_x: float = 0.0
    position_y: float = 1.7
    position_z: float = 0.0
    target_x: float = 0.0
    target_y: float = 1.0
    target_z: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class CompositionOverlay:
    """Composition guide overlay settings."""
    guide: str = CompositionGuide.RULE_OF_THIRDS.value
    opacity: float = 0.5
    color: str = "#FFFFFF"
    show_safe_area: bool = True
    show_horizon: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class PhotoEntry:
    """A captured photo."""
    photo_id: str
    player_id: str
    title: str = ""
    description: str = ""
    category: str = PhotoCategory.LANDSCAPE.value
    quality: str = PhotoQuality.COMMON.value
    camera_settings: CameraSettings = field(default_factory=CameraSettings)
    filter_id: str = FilterPreset.NONE.value
    composition_guide: str = CompositionGuide.RULE_OF_THIRDS.value
    scene_id: str = ""
    location_x: float = 0.0
    location_y: float = 0.0
    location_z: float = 0.0
    world_time: float = 12.0
    weather: str = "clear"
    subject_entity_ids: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    score: float = 0.0
    ratings: List[float] = field(default_factory=list)
    rating_count: int = 0
    average_rating: float = 0.0
    captured_at: float = field(default_factory=_now)
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def is_rated(self) -> bool:
        return self.rating_count > 0

    def to_dict(self) -> Dict[str, Any]:
        d = _dataclass_to_dict(self)
        d["is_rated"] = self.is_rated
        return d


@dataclass
class PhotoAlbum:
    """A player-created photo album."""
    album_id: str
    player_id: str
    name: str
    description: str = ""
    photo_ids: List[str] = field(default_factory=list)
    cover_photo_id: str = ""
    is_public: bool = False
    created_at: float = field(default_factory=_now)
    updated_at: float = field(default_factory=_now)

    @property
    def photo_count(self) -> int:
        return len(self.photo_ids)

    def to_dict(self) -> Dict[str, Any]:
        d = _dataclass_to_dict(self)
        d["photo_count"] = self.photo_count
        return d


@dataclass
class PhotoChallenge:
    """A photography challenge or quest."""
    challenge_id: str
    name: str
    description: str = ""
    category: str = PhotoCategory.LANDSCAPE.value
    required_quality: str = PhotoQuality.COMMON.value
    required_filter: str = ""
    required_composition: str = ""
    required_subject: str = ""
    required_location: str = ""
    required_time_of_day: str = ""
    required_weather: str = ""
    min_score: float = 0.0
    reward_currency: str = "gold"
    reward_amount: float = 100.0
    reward_xp: int = 50
    reward_items: List[str] = field(default_factory=list)
    time_limit_hours: float = 0.0
    is_repeatable: bool = False
    is_active: bool = True
    created_at: float = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class ChallengeSubmission:
    """A player's submission for a photo challenge."""
    submission_id: str
    challenge_id: str
    player_id: str
    photo_id: str
    score: float = 0.0
    quality_achieved: str = PhotoQuality.COMMON.value
    completed: bool = False
    submitted_at: float = field(default_factory=_now)
    reward_claimed: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class SceneDetection:
    """Result of AI scene detection for photography."""
    scene_id: str
    scene_name: str
    confidence: float = 0.0
    suggested_preset: str = CameraPreset.LANDSCAPE.value
    suggested_filter: str = FilterPreset.VIBRANT.value
    suggested_composition: str = CompositionGuide.RULE_OF_THIRDS.value
    suggested_focal_length: float = 50.0
    suggested_aperture: float = 2.8
    suggested_iso: int = 100
    detected_subjects: List[str] = field(default_factory=list)
    lighting_quality: float = 0.5
    movement_level: float = 0.0
    recommended: bool = True
    detected_at: float = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class PhotographyConfig:
    """Global tuning parameters."""
    max_photos_per_player: int = 500
    max_albums_per_player: int = 50
    max_filter_strength: float = 2.0
    default_composition_opacity: float = 0.5
    enable_scene_detection: bool = True
    enable_auto_rating: bool = True
    rating_decay_per_day: float = 0.01
    challenge_check_interval: float = 60.0
    tick_rate_hz: float = 1.0

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class PhotographyStats:
    """Aggregate statistics."""
    total_camera_presets: int = 0
    total_filters: int = 0
    total_composition_guides: int = 0
    total_photos: int = 0
    total_albums: int = 0
    total_challenges: int = 0
    total_submissions: int = 0
    total_completions: int = 0
    total_ratings: int = 0
    average_score: float = 0.0
    tick_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class PhotographySnapshot:
    """Full state snapshot."""
    camera_presets: List[Dict[str, Any]] = field(default_factory=list)
    filters: List[Dict[str, Any]] = field(default_factory=list)
    composition_guides: List[Dict[str, Any]] = field(default_factory=list)
    stats: Dict[str, Any] = field(default_factory=dict)
    config: Dict[str, Any] = field(default_factory=dict)
    tick_count: int = 0
    timestamp: float = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class PhotographyEvent:
    """An audit event."""
    event_id: str
    kind: str
    timestamp: float
    photo_id: str = ""
    player_id: str = ""
    album_id: str = ""
    challenge_id: str = ""
    filter_id: str = ""
    description: str = ""
    details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


# ---------------------------------------------------------------------------
# Photography Mode System
# ---------------------------------------------------------------------------

class PhotographyModeSystem:
    """Manages in-game photography, filters, albums, and challenges."""

    _instance: Optional["PhotographyModeSystem"] = None
    _lock = threading.RLock()

    def __init__(self) -> None:
        self._camera_presets: Dict[str, CameraSettings] = {}
        self._filters: Dict[str, FilterDefinition] = {}
        self._composition_guides: Dict[str, CompositionOverlay] = {}
        self._photos: Dict[str, PhotoEntry] = {}
        self._player_photos: Dict[str, List[str]] = {}
        self._albums: Dict[str, PhotoAlbum] = {}
        self._player_albums: Dict[str, List[str]] = {}
        self._challenges: Dict[str, PhotoChallenge] = {}
        self._submissions: Dict[str, ChallengeSubmission] = {}
        self._player_submissions: Dict[str, List[str]] = {}
        self._leaderboard: List[Tuple[str, float]] = []
        self._events: List[PhotographyEvent] = []
        self._stats = PhotographyStats()
        self._config = PhotographyConfig()
        self._tick_count: int = 0
        self._event_counter: int = 0
        self._initialized: bool = False
        self._init_lock = threading.RLock()
        self._seed()

    @classmethod
    def get_instance(cls) -> "PhotographyModeSystem":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    # ------------------------------------------------------------------
    # Initialization
    # ------------------------------------------------------------------

    def _seed(self) -> None:
        with self._init_lock:
            if self._initialized:
                return

            # Camera presets
            presets = [
                ("cam_free", CameraPreset.FREE.value, 50.0, 2.8, 0.01, 100),
                ("cam_portrait", CameraPreset.PORTRAIT.value, 85.0, 1.8, 0.005, 200),
                ("cam_landscape", CameraPreset.LANDSCAPE.value, 24.0, 8.0, 0.02, 100),
                ("cam_action", CameraPreset.ACTION.value, 200.0, 4.0, 0.001, 800),
                ("cam_macro", CameraPreset.MACRO.value, 100.0, 2.8, 0.01, 200),
                ("cam_panoramic", CameraPreset.PANORAMIC.value, 16.0, 11.0, 0.05, 100),
                ("cam_night", CameraPreset.NIGHT.value, 35.0, 1.4, 0.5, 3200),
                ("cam_hdr", CameraPreset.HDR.value, 35.0, 5.6, 0.03, 100),
                ("cam_cinematic", CameraPreset.CINEMATIC.value, 50.0, 2.2, 0.02, 400),
                ("cam_drone", CameraPreset.DRONE.value, 24.0, 4.0, 0.01, 200),
            ]
            for pid, preset, fl, ap, ss, iso in presets:
                cs = CameraSettings(
                    preset=preset, focal_length=fl, aperture=ap,
                    shutter_speed=ss, iso=iso,
                )
                self._camera_presets[pid] = cs

            # Filters
            filters = [
                ("flt_none", FilterPreset.NONE.value, "None", "No filter applied", 1.0, 1.0, 1.0),
                ("flt_vintage", FilterPreset.VINTAGE.value, "Vintage", "Retro film look", 0.9, 0.85, 0.7),
                ("flt_noir", FilterPreset.NOIR.value, "Noir", "Black and white dramatic", 0.95, 1.3, 0.0),
                ("flt_vibrant", FilterPreset.VIBRANT.value, "Vibrant", "Enhanced colors", 1.1, 1.2, 1.5),
                ("flt_soft", FilterPreset.SOFT.value, "Soft", "Dreamy soft focus", 1.05, 0.8, 0.9),
                ("flt_dramatic", FilterPreset.DRAMATIC.value, "Dramatic", "High contrast dramatic", 0.85, 1.5, 1.1),
                ("flt_warm", FilterPreset.WARM.value, "Warm", "Warm golden tones", 1.05, 1.0, 1.1),
                ("flt_cool", FilterPreset.COOL.value, "Cool", "Cool blue tones", 1.0, 1.0, 0.9),
                ("flt_sepia", FilterPreset.SEPIA.value, "Sepia", "Classic sepia tones", 0.95, 0.9, 0.6),
                ("flt_pastel", FilterPreset.PASTEL.value, "Pastel", "Soft pastel colors", 1.1, 0.7, 0.85),
                ("flt_cyberpunk", FilterPreset.CYBERPUNK.value, "Cyberpunk", "Neon cyberpunk style", 0.9, 1.4, 1.6),
                ("flt_watercolor", FilterPreset.WATERCOLOR.value, "Watercolor", "Painted watercolor effect", 1.0, 0.75, 0.8),
            ]
            for fid, preset_val, name, desc, br, ct, sat in filters:
                fd = FilterDefinition(
                    filter_id=fid, name=name, description=desc,
                    brightness=br, contrast=ct, saturation=sat,
                )
                self._filters[fid] = fd

            # Composition guides
            guides = [
                ("comp_none", CompositionGuide.NONE.value, "None", 0.0),
                ("comp_thirds", CompositionGuide.RULE_OF_THIRDS.value, "Rule of Thirds", 0.5),
                ("comp_golden", CompositionGuide.GOLDEN_RATIO.value, "Golden Ratio", 0.5),
                ("comp_center", CompositionGuide.CENTER.value, "Center", 0.4),
                ("comp_diagonal", CompositionGuide.DIAGONAL.value, "Diagonal", 0.5),
                ("comp_grid", CompositionGuide.GRID.value, "Grid", 0.3),
                ("comp_spiral", CompositionGuide.SPIRAL.value, "Spiral", 0.6),
                ("comp_triangular", CompositionGuide.TRIANGULAR.value, "Triangular", 0.5),
                ("comp_frame", CompositionGuide.FRAME_WITHIN_FRAME.value, "Frame in Frame", 0.5),
                ("comp_leading", CompositionGuide.LEADING_LINES.value, "Leading Lines", 0.5),
            ]
            for gid, guide_val, name, opacity in guides:
                co = CompositionOverlay(guide=guide_val, opacity=opacity)
                self._composition_guides[gid] = co

            # Seeded photos
            photo1 = PhotoEntry(
                photo_id="photo_starter_01",
                player_id="player_starter",
                title="Sunrise over the Valley",
                description="A breathtaking sunrise captured from the eastern cliffs.",
                category=PhotoCategory.LANDSCAPE.value,
                quality=PhotoQuality.RARE.value,
                camera_settings=CameraSettings(preset=CameraPreset.LANDSCAPE.value, focal_length=24.0, aperture=8.0),
                filter_id="flt_warm",
                composition_guide=CompositionGuide.RULE_OF_THIRDS.value,
                scene_id="scene_valley_sunrise",
                location_x=100.0, location_y=50.0, location_z=200.0,
                world_time=6.5,
                weather="clear",
                tags=["sunrise", "valley", "landscape"],
                score=85.0,
                ratings=[85.0, 90.0, 80.0],
                rating_count=3,
                average_rating=85.0,
            )
            self._photos[photo1.photo_id] = photo1
            self._player_photos.setdefault("player_starter", []).append(photo1.photo_id)

            photo2 = PhotoEntry(
                photo_id="photo_starter_02",
                player_id="player_starter",
                title="Wolf in the Moonlight",
                description="A timber wolf under the full moon.",
                category=PhotoCategory.WILDLIFE.value,
                quality=PhotoQuality.EPIC.value,
                camera_settings=CameraSettings(preset=CameraPreset.NIGHT.value, focal_length=35.0, aperture=1.4, iso=3200),
                filter_id="flt_cool",
                composition_guide=CompositionGuide.CENTER.value,
                scene_id="scene_moonlit_forest",
                location_x=-50.0, location_y=30.0, location_z=100.0,
                world_time=22.0,
                weather="clear",
                subject_entity_ids=["ent_wolf_01"],
                tags=["wolf", "night", "moonlight"],
                score=92.0,
                ratings=[92.0, 95.0, 89.0, 90.0],
                rating_count=4,
                average_rating=91.5,
            )
            self._photos[photo2.photo_id] = photo2
            self._player_photos.setdefault("player_starter", []).append(photo2.photo_id)

            # Seeded album
            album1 = PhotoAlbum(
                album_id="album_starter_01",
                player_id="player_starter",
                name="My Best Shots",
                description="Collection of my finest photographs.",
                photo_ids=["photo_starter_01", "photo_starter_02"],
                cover_photo_id="photo_starter_02",
                is_public=True,
            )
            self._albums[album1.album_id] = album1
            self._player_albums.setdefault("player_starter", []).append(album1.album_id)

            # Seeded challenges
            challenge1 = PhotoChallenge(
                challenge_id="chlg_golden_hour",
                name="Golden Hour Master",
                description="Capture a landscape photo during golden hour (sunset).",
                category=PhotoCategory.LANDSCAPE.value,
                required_quality=PhotoQuality.UNCOMMON.value,
                required_time_of_day="sunset",
                required_weather="clear",
                min_score=70.0,
                reward_currency="gold",
                reward_amount=500.0,
                reward_xp=200,
                is_repeatable=True,
            )
            self._challenges[challenge1.challenge_id] = challenge1

            challenge2 = PhotoChallenge(
                challenge_id="chlg_wildlife_action",
                name="Wildlife in Motion",
                description="Photograph a wild creature in action.",
                category=PhotoCategory.WILDLIFE.value,
                required_quality=PhotoQuality.RARE.value,
                min_score=75.0,
                reward_currency="gold",
                reward_amount=800.0,
                reward_xp=350,
                reward_items=["item_camera_lens_telephoto"],
                is_repeatable=True,
            )
            self._challenges[challenge2.challenge_id] = challenge2

            challenge3 = PhotoChallenge(
                challenge_id="chgl_night_sky",
                name="Starry Night",
                description="Capture the night sky with stars visible.",
                category=PhotoCategory.LANDSCAPE.value,
                required_quality=PhotoQuality.RARE.value,
                required_time_of_day="night",
                required_weather="clear",
                required_filter="flt_cool",
                min_score=80.0,
                reward_currency="gold",
                reward_amount=1000.0,
                reward_xp=500,
                reward_items=["item_tripod", "item_star_chart"],
                is_repeatable=True,
            )
            self._challenges[challenge3.challenge_id] = challenge3

            # Seeded submission
            submission1 = ChallengeSubmission(
                submission_id="sub_starter_01",
                challenge_id="chlg_golden_hour",
                player_id="player_starter",
                photo_id="photo_starter_01",
                score=85.0,
                quality_achieved=PhotoQuality.RARE.value,
                completed=True,
                reward_claimed=True,
            )
            self._submissions[submission1.submission_id] = submission1
            self._player_submissions.setdefault("player_starter", []).append(submission1.submission_id)

            # Update leaderboard
            self._rebuild_leaderboard()

            # Update stats
            self._stats.total_camera_presets = len(self._camera_presets)
            self._stats.total_filters = len(self._filters)
            self._stats.total_composition_guides = len(self._composition_guides)
            self._stats.total_photos = len(self._photos)
            self._stats.total_albums = len(self._albums)
            self._stats.total_challenges = len(self._challenges)
            self._stats.total_submissions = len(self._submissions)
            self._stats.total_completions = 1
            self._stats.total_ratings = 7
            self._stats.average_score = 88.5

            self._initialized = True

    def _rebuild_leaderboard(self) -> None:
        scored = [(p.photo_id, p.score) for p in self._photos.values() if p.score > 0]
        scored.sort(key=lambda x: x[1], reverse=True)
        self._leaderboard = scored[:100]

    def _emit(self, kind: str, **kwargs: Any) -> None:
        self._event_counter += 1
        event = PhotographyEvent(
            event_id=f"pevt_{self._event_counter:08d}",
            kind=kind,
            timestamp=_now(),
            **kwargs,
        )
        self._events.append(event)
        _evict_fifo_list(self._events, _MAX_EVENTS)

    # ------------------------------------------------------------------
    # Camera Presets
    # ------------------------------------------------------------------

    def register_camera_preset(
        self, preset_id: str, preset_name: str,
        focal_length: float = 50.0, aperture: float = 2.8,
        shutter_speed: float = 0.01, iso: int = 100,
    ) -> Tuple[bool, str, Optional[CameraSettings]]:
        if preset_id in self._camera_presets:
            return False, "already_exists", None
        cs = CameraSettings(
            preset=preset_name,
            focal_length=focal_length,
            aperture=aperture,
            shutter_speed=shutter_speed,
            iso=iso,
        )
        self._camera_presets[preset_id] = cs
        self._stats.total_camera_presets = len(self._camera_presets)
        self._emit(PhotographyEventKind.CAMERA_PRESET_REGISTERED.value,
                   description=f"Camera preset registered: {preset_id}")
        return True, "registered", cs

    def remove_camera_preset(self, preset_id: str) -> Tuple[bool, str]:
        if preset_id not in self._camera_presets:
            return False, "not_found"
        del self._camera_presets[preset_id]
        self._stats.total_camera_presets = len(self._camera_presets)
        self._emit(PhotographyEventKind.CAMERA_PRESET_REMOVED.value,
                   description=f"Camera preset removed: {preset_id}")
        return True, "removed"

    def get_camera_preset(self, preset_id: str) -> Optional[CameraSettings]:
        return self._camera_presets.get(preset_id)

    def list_camera_presets(self) -> List[CameraSettings]:
        return list(self._camera_presets.values())

    # ------------------------------------------------------------------
    # Filters
    # ------------------------------------------------------------------

    def register_filter(
        self, filter_id: str, name: str, description: str = "",
        brightness: float = 1.0, contrast: float = 1.0, saturation: float = 1.0,
        hue_shift: float = 0.0, temperature: float = 0.0, tint: float = 0.0,
        vignette: float = 0.0, grain: float = 0.0,
    ) -> Tuple[bool, str, Optional[FilterDefinition]]:
        if filter_id in self._filters:
            return False, "already_exists", None
        fd = FilterDefinition(
            filter_id=filter_id, name=name, description=description,
            brightness=_clamp(brightness, 0.0, self._config.max_filter_strength),
            contrast=_clamp(contrast, 0.0, self._config.max_filter_strength),
            saturation=_clamp(saturation, 0.0, self._config.max_filter_strength),
            hue_shift=hue_shift, temperature=temperature, tint=tint,
            vignette=_clamp(vignette, 0.0, 1.0), grain=_clamp(grain, 0.0, 1.0),
        )
        self._filters[filter_id] = fd
        self._stats.total_filters = len(self._filters)
        self._emit(PhotographyEventKind.FILTER_REGISTERED.value,
                   filter_id=filter_id,
                   description=f"Filter registered: {filter_id}")
        return True, "registered", fd

    def remove_filter(self, filter_id: str) -> Tuple[bool, str]:
        if filter_id not in self._filters:
            return False, "not_found"
        del self._filters[filter_id]
        self._stats.total_filters = len(self._filters)
        self._emit(PhotographyEventKind.FILTER_REMOVED.value,
                   filter_id=filter_id,
                   description=f"Filter removed: {filter_id}")
        return True, "removed"

    def get_filter(self, filter_id: str) -> Optional[FilterDefinition]:
        return self._filters.get(filter_id)

    def list_filters(self) -> List[FilterDefinition]:
        return list(self._filters.values())

    # ------------------------------------------------------------------
    # Composition Guides
    # ------------------------------------------------------------------

    def register_composition_guide(
        self, guide_id: str, guide_name: str, opacity: float = 0.5,
        color: str = "#FFFFFF", show_safe_area: bool = True, show_horizon: bool = True,
    ) -> Tuple[bool, str, Optional[CompositionOverlay]]:
        if guide_id in self._composition_guides:
            return False, "already_exists", None
        co = CompositionOverlay(
            guide=guide_name, opacity=_clamp(opacity, 0.0, 1.0),
            color=color, show_safe_area=show_safe_area, show_horizon=show_horizon,
        )
        self._composition_guides[guide_id] = co
        self._stats.total_composition_guides = len(self._composition_guides)
        self._emit(PhotographyEventKind.COMPOSITION_REGISTERED.value,
                   description=f"Composition guide registered: {guide_id}")
        return True, "registered", co

    def get_composition_guide(self, guide_id: str) -> Optional[CompositionOverlay]:
        return self._composition_guides.get(guide_id)

    def list_composition_guides(self) -> List[CompositionOverlay]:
        return list(self._composition_guides.values())

    # ------------------------------------------------------------------
    # Photo Capture & Management
    # ------------------------------------------------------------------

    def capture_photo(
        self, player_id: str, title: str = "", description: str = "",
        category: str = PhotoCategory.LANDSCAPE.value,
        camera_preset_id: str = "cam_free", filter_id: str = "flt_none",
        composition_guide_id: str = "comp_thirds",
        scene_id: str = "", location_x: float = 0.0, location_y: float = 0.0, location_z: float = 0.0,
        world_time: float = 12.0, weather: str = "clear",
        subject_entity_ids: Optional[List[str]] = None, tags: Optional[List[str]] = None,
    ) -> Tuple[bool, str, Optional[PhotoEntry]]:
        player_photos = self._player_photos.get(player_id, [])
        if len(player_photos) >= self._config.max_photos_per_player:
            return False, "photo_limit_reached", None

        camera_settings = self._camera_presets.get(camera_preset_id, CameraSettings())
        photo_id = _new_id("photo")

        # Auto-detect quality based on composition and conditions
        quality = self._evaluate_quality(camera_settings, filter_id, composition_guide_id, world_time, weather)

        score = self._calculate_score(camera_settings, filter_id, composition_guide_id, world_time, weather, subject_entity_ids or [])

        photo = PhotoEntry(
            photo_id=photo_id,
            player_id=player_id,
            title=title or f"Photo #{photo_id[-6:]}",
            description=description,
            category=category,
            quality=quality,
            camera_settings=camera_settings,
            filter_id=filter_id,
            composition_guide=self._composition_guides.get(composition_guide_id, CompositionOverlay()).guide,
            scene_id=scene_id,
            location_x=location_x, location_y=location_y, location_z=location_z,
            world_time=world_time,
            weather=weather,
            subject_entity_ids=subject_entity_ids or [],
            tags=tags or [],
            score=score,
        )
        self._photos[photo_id] = photo
        self._player_photos.setdefault(player_id, []).append(photo_id)
        self._stats.total_photos = len(self._photos)
        self._emit(PhotographyEventKind.PHOTO_CAPTURED.value,
                   photo_id=photo_id, player_id=player_id,
                   description=f"Photo captured: {photo_id}")
        return True, "captured", photo

    def _evaluate_quality(
        self, camera: CameraSettings, filter_id: str, composition_id: str,
        world_time: float, weather: str,
    ) -> str:
        score = 0.0
        if 6.0 <= world_time <= 8.0 or 17.0 <= world_time <= 19.0:
            score += 30
        if weather in ("clear", "fog"):
            score += 20
        if filter_id != "flt_none":
            score += 15
        if composition_id != "comp_none":
            score += 20
        if camera.focal_length > 50:
            score += 15
        if camera.aperture < 4.0:
            score += 10

        if score >= 80:
            return PhotoQuality.LEGENDARY.value
        elif score >= 65:
            return PhotoQuality.EPIC.value
        elif score >= 50:
            return PhotoQuality.RARE.value
        elif score >= 30:
            return PhotoQuality.UNCOMMON.value
        return PhotoQuality.COMMON.value

    def _calculate_score(
        self, camera: CameraSettings, filter_id: str, composition_id: str,
        world_time: float, weather: str, subjects: List[str],
    ) -> float:
        score = 50.0
        if 6.0 <= world_time <= 8.0 or 17.0 <= world_time <= 19.0:
            score += 15.0
        if weather == "clear":
            score += 10.0
        elif weather == "fog":
            score += 8.0
        if filter_id != "flt_none":
            score += 8.0
        if composition_id != "comp_none":
            score += 10.0
        if len(subjects) > 0:
            score += 5.0 * min(len(subjects), 4)
        if camera.aperture < 2.8:
            score += 5.0
        if 24 <= camera.focal_length <= 85:
            score += 5.0
        return _clamp(score, 0.0, 100.0)

    def get_photo(self, photo_id: str) -> Optional[PhotoEntry]:
        return self._photos.get(photo_id)

    def list_photos(self, player_id: str = "") -> List[PhotoEntry]:
        if player_id:
            ids = self._player_photos.get(player_id, [])
            return [self._photos[pid] for pid in ids if pid in self._photos]
        return list(self._photos.values())

    def delete_photo(self, photo_id: str) -> Tuple[bool, str]:
        photo = self._photos.get(photo_id)
        if photo is None:
            return False, "not_found"
        player_id = photo.player_id
        del self._photos[photo_id]
        if player_id in self._player_photos:
            try:
                self._player_photos[player_id].remove(photo_id)
            except ValueError:
                pass
        for album in self._albums.values():
            if photo_id in album.photo_ids:
                album.photo_ids.remove(photo_id)
                if album.cover_photo_id == photo_id:
                    album.cover_photo_id = album.photo_ids[0] if album.photo_ids else ""
        self._stats.total_photos = len(self._photos)
        self._emit(PhotographyEventKind.PHOTO_DELETED.value,
                   photo_id=photo_id, player_id=player_id,
                   description=f"Photo deleted: {photo_id}")
        return True, "deleted"

    # ------------------------------------------------------------------
    # Albums
    # ------------------------------------------------------------------

    def create_album(
        self, player_id: str, name: str, description: str = "",
        is_public: bool = False,
    ) -> Tuple[bool, str, Optional[PhotoAlbum]]:
        player_albums = self._player_albums.get(player_id, [])
        if len(player_albums) >= self._config.max_albums_per_player:
            return False, "album_limit_reached", None
        album_id = _new_id("album")
        album = PhotoAlbum(
            album_id=album_id, player_id=player_id, name=name,
            description=description, is_public=is_public,
        )
        self._albums[album_id] = album
        self._player_albums.setdefault(player_id, []).append(album_id)
        self._stats.total_albums = len(self._albums)
        self._emit(PhotographyEventKind.ALBUM_CREATED.value,
                   album_id=album_id, player_id=player_id,
                   description=f"Album created: {album_id}")
        return True, "created", album

    def delete_album(self, album_id: str) -> Tuple[bool, str]:
        album = self._albums.get(album_id)
        if album is None:
            return False, "not_found"
        player_id = album.player_id
        del self._albums[album_id]
        if player_id in self._player_albums:
            try:
                self._player_albums[player_id].remove(album_id)
            except ValueError:
                pass
        self._stats.total_albums = len(self._albums)
        self._emit(PhotographyEventKind.ALBUM_DELETED.value,
                   album_id=album_id, player_id=player_id,
                   description=f"Album deleted: {album_id}")
        return True, "deleted"

    def get_album(self, album_id: str) -> Optional[PhotoAlbum]:
        return self._albums.get(album_id)

    def list_albums(self, player_id: str = "") -> List[PhotoAlbum]:
        if player_id:
            ids = self._player_albums.get(player_id, [])
            return [self._albums[aid] for aid in ids if aid in self._albums]
        return list(self._albums.values())

    def add_photo_to_album(self, album_id: str, photo_id: str) -> Tuple[bool, str, Optional[PhotoAlbum]]:
        album = self._albums.get(album_id)
        if album is None:
            return False, "album_not_found", None
        if photo_id not in self._photos:
            return False, "photo_not_found", album
        if photo_id in album.photo_ids:
            return False, "already_in_album", album
        album.photo_ids.append(photo_id)
        album.updated_at = _now()
        if not album.cover_photo_id:
            album.cover_photo_id = photo_id
        self._emit(PhotographyEventKind.PHOTO_ADDED_TO_ALBUM.value,
                   album_id=album_id, photo_id=photo_id,
                   description=f"Photo {photo_id} added to album {album_id}")
        return True, "added", album

    # ------------------------------------------------------------------
    # Challenges
    # ------------------------------------------------------------------

    def register_challenge(
        self, challenge_id: str, name: str, description: str = "",
        category: str = PhotoCategory.LANDSCAPE.value,
        required_quality: str = PhotoQuality.COMMON.value,
        required_filter: str = "", required_composition: str = "",
        required_subject: str = "", required_location: str = "",
        required_time_of_day: str = "", required_weather: str = "",
        min_score: float = 0.0,
        reward_currency: str = "gold", reward_amount: float = 100.0,
        reward_xp: int = 50, reward_items: Optional[List[str]] = None,
        time_limit_hours: float = 0.0, is_repeatable: bool = False,
    ) -> Tuple[bool, str, Optional[PhotoChallenge]]:
        if challenge_id in self._challenges:
            return False, "already_exists", None
        challenge = PhotoChallenge(
            challenge_id=challenge_id, name=name, description=description,
            category=category, required_quality=required_quality,
            required_filter=required_filter, required_composition=required_composition,
            required_subject=required_subject, required_location=required_location,
            required_time_of_day=required_time_of_day, required_weather=required_weather,
            min_score=min_score, reward_currency=reward_currency,
            reward_amount=reward_amount, reward_xp=reward_xp,
            reward_items=reward_items or [], time_limit_hours=time_limit_hours,
            is_repeatable=is_repeatable,
        )
        self._challenges[challenge_id] = challenge
        self._stats.total_challenges = len(self._challenges)
        self._emit(PhotographyEventKind.CHALLENGE_REGISTERED.value,
                   challenge_id=challenge_id,
                   description=f"Challenge registered: {challenge_id}")
        return True, "registered", challenge

    def remove_challenge(self, challenge_id: str) -> Tuple[bool, str]:
        if challenge_id not in self._challenges:
            return False, "not_found"
        del self._challenges[challenge_id]
        self._stats.total_challenges = len(self._challenges)
        return True, "removed"

    def get_challenge(self, challenge_id: str) -> Optional[PhotoChallenge]:
        return self._challenges.get(challenge_id)

    def list_challenges(self, active_only: bool = False) -> List[PhotoChallenge]:
        if active_only:
            return [c for c in self._challenges.values() if c.is_active]
        return list(self._challenges.values())

    def start_challenge(self, challenge_id: str, player_id: str) -> Tuple[bool, str]:
        challenge = self._challenges.get(challenge_id)
        if challenge is None:
            return False, "not_found"
        if not challenge.is_active:
            return False, "not_active"
        player_subs = self._player_submissions.get(player_id, [])
        for sid in player_subs:
            sub = self._submissions.get(sid)
            if sub and sub.challenge_id == challenge_id and sub.completed:
                if not challenge.is_repeatable:
                    return False, "already_completed"
        self._emit(PhotographyEventKind.CHALLENGE_STARTED.value,
                   challenge_id=challenge_id, player_id=player_id,
                   description=f"Challenge started: {challenge_id} by {player_id}")
        return True, "started"

    def submit_photo(
        self, challenge_id: str, player_id: str, photo_id: str,
    ) -> Tuple[bool, str, Optional[ChallengeSubmission]]:
        challenge = self._challenges.get(challenge_id)
        if challenge is None:
            return False, "challenge_not_found", None
        photo = self._photos.get(photo_id)
        if photo is None:
            return False, "photo_not_found", None
        if photo.player_id != player_id:
            return False, "not_owner", None

        # Check requirements
        quality_rank = self._quality_rank(photo.quality)
        required_rank = self._quality_rank(challenge.required_quality)
        if quality_rank < required_rank:
            return False, "quality_too_low", None
        if challenge.required_filter and photo.filter_id != challenge.required_filter:
            return False, "filter_mismatch", None
        if challenge.min_score > 0 and photo.score < challenge.min_score:
            return False, "score_too_low", None

        submission_id = _new_id("sub")
        completed = True
        submission = ChallengeSubmission(
            submission_id=submission_id,
            challenge_id=challenge_id,
            player_id=player_id,
            photo_id=photo_id,
            score=photo.score,
            quality_achieved=photo.quality,
            completed=completed,
        )
        self._submissions[submission_id] = submission
        self._player_submissions.setdefault(player_id, []).append(submission_id)
        self._stats.total_submissions = len(self._submissions)
        if completed:
            self._stats.total_completions += 1
        self._emit(PhotographyEventKind.CHALLENGE_SUBMITTED.value,
                   challenge_id=challenge_id, player_id=player_id, photo_id=photo_id,
                   description=f"Photo {photo_id} submitted for challenge {challenge_id}")
        return True, "submitted", submission

    def complete_challenge(self, submission_id: str) -> Tuple[bool, str, Optional[ChallengeSubmission]]:
        sub = self._submissions.get(submission_id)
        if sub is None:
            return False, "not_found", None
        if not sub.completed:
            return False, "not_completed", sub
        if sub.reward_claimed:
            return False, "already_claimed", sub
        sub.reward_claimed = True
        self._emit(PhotographyEventKind.CHALLENGE_COMPLETED.value,
                   challenge_id=sub.challenge_id, player_id=sub.player_id,
                   description=f"Challenge completed: {sub.challenge_id}")
        return True, "completed", sub

    def _quality_rank(self, quality: str) -> int:
        ranks = {
            PhotoQuality.COMMON.value: 0,
            PhotoQuality.UNCOMMON.value: 1,
            PhotoQuality.RARE.value: 2,
            PhotoQuality.EPIC.value: 3,
            PhotoQuality.LEGENDARY.value: 4,
            PhotoQuality.MASTERPIECE.value: 5,
        }
        return ranks.get(quality, 0)

    # ------------------------------------------------------------------
    # Rating & Leaderboard
    # ------------------------------------------------------------------

    def rate_photo(self, photo_id: str, rating: float) -> Tuple[bool, str, Optional[PhotoEntry]]:
        photo = self._photos.get(photo_id)
        if photo is None:
            return False, "not_found", None
        rating = _clamp(rating, 0.0, 100.0)
        photo.ratings.append(rating)
        photo.rating_count = len(photo.ratings)
        total = sum(photo.ratings)
        photo.average_rating = total / photo.rating_count
        self._stats.total_ratings += 1
        self._rebuild_leaderboard()
        self._emit(PhotographyEventKind.PHOTO_RATED.value,
                   photo_id=photo_id,
                   description=f"Photo rated: {photo_id} score={rating}")
        return True, "rated", photo

    def get_photo_score(self, photo_id: str) -> Optional[float]:
        photo = self._photos.get(photo_id)
        if photo is None:
            return None
        return photo.score

    def get_leaderboard(self, limit: int = 10) -> List[Dict[str, Any]]:
        limit = max(1, min(int(limit), 100))
        result: List[Dict[str, Any]] = []
        for photo_id, score in self._leaderboard[:limit]:
            photo = self._photos.get(photo_id)
            if photo:
                result.append({
                    "photo_id": photo_id,
                    "player_id": photo.player_id,
                    "title": photo.title,
                    "score": round(score, 2),
                    "quality": photo.quality,
                    "average_rating": round(photo.average_rating, 2),
                    "rating_count": photo.rating_count,
                })
        return result

    # ------------------------------------------------------------------
    # Scene Detection & AI Suggestions
    # ------------------------------------------------------------------

    def detect_scene(
        self, location_x: float, location_y: float, location_z: float,
        world_time: float = 12.0, weather: str = "clear",
        nearby_entities: Optional[List[str]] = None,
    ) -> Tuple[bool, str, Optional[SceneDetection]]:
        if not self._config.enable_scene_detection:
            return False, "disabled", None

        scene_id = _new_id("scene")
        scene_name = "Generic Scene"

        if 6.0 <= world_time <= 8.0:
            scene_name = "Sunrise Scene"
            suggested_preset = CameraPreset.LANDSCAPE.value
            suggested_filter = FilterPreset.WARM.value
            suggested_composition = CompositionGuide.RULE_OF_THIRDS.value
            suggested_focal = 24.0
            suggested_aperture = 8.0
            suggested_iso = 100
            lighting_quality = 0.9
        elif 17.0 <= world_time <= 19.0:
            scene_name = "Sunset Scene"
            suggested_preset = CameraPreset.LANDSCAPE.value
            suggested_filter = FilterPreset.WARM.value
            suggested_composition = CompositionGuide.RULE_OF_THIRDS.value
            suggested_focal = 35.0
            suggested_aperture = 5.6
            suggested_iso = 200
            lighting_quality = 0.9
        elif world_time >= 20 or world_time <= 5:
            scene_name = "Night Scene"
            suggested_preset = CameraPreset.NIGHT.value
            suggested_filter = FilterPreset.COOL.value
            suggested_composition = CompositionGuide.CENTER.value
            suggested_focal = 35.0
            suggested_aperture = 1.4
            suggested_iso = 3200
            lighting_quality = 0.3
        elif weather == "fog":
            scene_name = "Misty Scene"
            suggested_preset = CameraPreset.LANDSCAPE.value
            suggested_filter = FilterPreset.SOFT.value
            suggested_composition = CompositionGuide.LEADING_LINES.value
            suggested_focal = 50.0
            suggested_aperture = 4.0
            suggested_iso = 400
            lighting_quality = 0.5
        elif weather == "rain":
            scene_name = "Rainy Scene"
            suggested_preset = CameraPreset.HDR.value
            suggested_filter = FilterPreset.DRAMATIC.value
            suggested_composition = CompositionGuide.DIAGONAL.value
            suggested_focal = 50.0
            suggested_aperture = 4.0
            suggested_iso = 800
            lighting_quality = 0.4
        else:
            suggested_preset = CameraPreset.FREE.value
            suggested_filter = FilterPreset.VIBRANT.value
            suggested_composition = CompositionGuide.RULE_OF_THIRDS.value
            suggested_focal = 50.0
            suggested_aperture = 2.8
            suggested_iso = 100
            lighting_quality = 0.7

        movement_level = 0.0
        if nearby_entities:
            movement_level = min(len(nearby_entities) * 0.2, 1.0)

        detection = SceneDetection(
            scene_id=scene_id,
            scene_name=scene_name,
            confidence=0.75 + (lighting_quality * 0.2),
            suggested_preset=suggested_preset,
            suggested_filter=suggested_filter,
            suggested_composition=suggested_composition,
            suggested_focal_length=suggested_focal,
            suggested_aperture=suggested_aperture,
            suggested_iso=suggested_iso,
            detected_subjects=nearby_entities or [],
            lighting_quality=lighting_quality,
            movement_level=movement_level,
            recommended=lighting_quality > 0.4,
        )
        self._emit(PhotographyEventKind.SCENE_DETECTED.value,
                   description=f"Scene detected: {scene_name}")
        return True, "detected", detection

    def get_scene_suggestion(
        self, location_x: float, location_y: float, location_z: float,
        world_time: float = 12.0, weather: str = "clear",
        nearby_entities: Optional[List[str]] = None,
    ) -> Optional[SceneDetection]:
        ok, _, detection = self.detect_scene(
            location_x, location_y, location_z, world_time, weather, nearby_entities,
        )
        if ok:
            return detection
        return None

    def get_best_camera_settings(
        self, world_time: float = 12.0, weather: str = "clear",
    ) -> CameraSettings:
        ok, _, detection = self.detect_scene(0, 0, 0, world_time, weather)
        if ok and detection:
            return CameraSettings(
                preset=detection.suggested_preset,
                focal_length=detection.suggested_focal_length,
                aperture=detection.suggested_aperture,
                iso=detection.suggested_iso,
            )
        return CameraSettings()

    # ------------------------------------------------------------------
    # Apply Filter / Composition
    # ------------------------------------------------------------------

    def apply_filter(self, photo_id: str, filter_id: str) -> Tuple[bool, str, Optional[PhotoEntry]]:
        photo = self._photos.get(photo_id)
        if photo is None:
            return False, "photo_not_found", None
        if filter_id not in self._filters:
            return False, "filter_not_found", photo
        photo.filter_id = filter_id
        return True, "applied", photo

    def apply_composition_guide(self, photo_id: str, composition_guide_id: str) -> Tuple[bool, str, Optional[PhotoEntry]]:
        photo = self._photos.get(photo_id)
        if photo is None:
            return False, "photo_not_found", None
        guide = self._composition_guides.get(composition_guide_id)
        if guide is None:
            return False, "guide_not_found", photo
        photo.composition_guide = guide.guide
        return True, "applied", photo

    # ------------------------------------------------------------------
    # Tick / Config / Status
    # ------------------------------------------------------------------

    def tick(self) -> Dict[str, Any]:
        self._tick_count += 1
        self._stats.tick_count = self._tick_count
        self._emit(PhotographyEventKind.TICK.value,
                   description=f"Tick #{self._tick_count}")
        return {
            "tick_count": self._tick_count,
            "total_photos": self._stats.total_photos,
            "total_submissions": self._stats.total_submissions,
        }

    def set_config(self, config: Dict[str, Any]) -> Tuple[bool, str, PhotographyConfig]:
        if not isinstance(config, dict):
            return False, "invalid_config", self._config
        for key, value in config.items():
            if hasattr(self._config, key):
                setattr(self._config, key, value)
        self._emit(PhotographyEventKind.CONFIG_UPDATED.value,
                   description="Config updated")
        return True, "updated", self._config

    def get_config(self) -> PhotographyConfig:
        return self._config

    def list_events(self, limit: int = 100, kind: str = "") -> List[PhotographyEvent]:
        events = self._events if not kind else [e for e in self._events if e.kind == kind]
        if limit > 0:
            events = events[-limit:]
        return list(events)

    def get_stats(self) -> PhotographyStats:
        if self._photos:
            total_score = sum(p.score for p in self._photos.values() if p.score > 0)
            scored_count = sum(1 for p in self._photos.values() if p.score > 0)
            self._stats.average_score = round(total_score / scored_count, 2) if scored_count > 0 else 0.0
        return self._stats

    def get_status(self) -> Dict[str, Any]:
        return {
            "initialized": self._initialized,
            "total_camera_presets": len(self._camera_presets),
            "total_filters": len(self._filters),
            "total_composition_guides": len(self._composition_guides),
            "total_photos": len(self._photos),
            "total_albums": len(self._albums),
            "total_challenges": len(self._challenges),
            "total_submissions": len(self._submissions),
            "total_completions": self._stats.total_completions,
            "total_ratings": self._stats.total_ratings,
            "average_score": round(self._stats.average_score, 2),
            "tick_count": self._tick_count,
        }

    def get_snapshot(self) -> PhotographySnapshot:
        return PhotographySnapshot(
            camera_presets=[cs.to_dict() for cs in self._camera_presets.values()],
            filters=[f.to_dict() for f in self._filters.values()],
            composition_guides=[g.to_dict() for g in self._composition_guides.values()],
            stats=self.get_stats().to_dict(),
            config=self._config.to_dict(),
            tick_count=self._tick_count,
        )

    def reset(self) -> Tuple[bool, str]:
        with self._init_lock:
            self._camera_presets.clear()
            self._filters.clear()
            self._composition_guides.clear()
            self._photos.clear()
            self._player_photos.clear()
            self._albums.clear()
            self._player_albums.clear()
            self._challenges.clear()
            self._submissions.clear()
            self._player_submissions.clear()
            self._leaderboard.clear()
            self._events.clear()
            self._stats = PhotographyStats()
            self._config = PhotographyConfig()
            self._tick_count = 0
            self._event_counter = 0
            self._initialized = False
            self._seed()
            self._emit(PhotographyEventKind.RESET.value,
                       description="System reset")
        return True, "reset"


# ---------------------------------------------------------------------------
# Module-Level Factory
# ---------------------------------------------------------------------------

def get_photography_mode_system() -> PhotographyModeSystem:
    return PhotographyModeSystem.get_instance()
