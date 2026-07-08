"""
SparkLabs Agent - AI Photo Director

An AI-native cinematic capture system that judges photo composition,
selects focal points, recommends angles and filters, and schedules
captures at dramatic moments. Fuses AI aesthetic judgment with engine
camera control to produce share-worthy screenshots automatically.

Designed for integration with the camera controller, cinematographer,
and frame capture system. The AI evaluates scene composition using
rule-of-thirds, golden ratio, leading lines, depth-of-field, and
dramatic tension to recommend optimal capture moments.
"""

from __future__ import annotations

import math
import threading
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Helper Functions
# ---------------------------------------------------------------------------

def _now() -> float:
    return time.time()


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None:
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        if value is None:
            return default
        return int(value)
    except (TypeError, ValueError):
        return default


def _clamp(value: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, value))


def _dataclass_to_dict(obj: Any) -> Dict[str, Any]:
    if hasattr(obj, "__dataclass_fields__"):
        result: Dict[str, Any] = {}
        for k in obj.__dataclass_fields__:
            v = getattr(obj, k)
            if hasattr(v, "to_dict") and callable(v.to_dict):
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
# Capacity Constants
# ---------------------------------------------------------------------------

_MAX_CAPTURES = 5000
_MAX_SCENES = 2000
_MAX_FILTERS = 200
_MAX_SCHEDULES = 500
_MAX_EVENTS = 5000


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class CaptureMode(str, Enum):
    FREE_CAM = "free_cam"
    AUTO_COMPOSE = "auto_compose"
    DRAMATIC = "dramatic"
    LANDSCAPE = "landscape"
    PORTRAIT = "portrait"
    ACTION = "action"
    MACRO = "macro"
    PANORAMA = "panorama"
    TIMELAPSE = "timelapse"


class CompositionRule(str, Enum):
    RULE_OF_THIRDS = "rule_of_thirds"
    GOLDEN_RATIO = "golden_ratio"
    CENTERED = "centered"
    DIAGONAL = "diagonal"
    SYMMETRY = "symmetry"
    LEADING_LINES = "leading_lines"
    NEGATIVE_SPACE = "negative_space"
    FRAMING = "framing"
    TRIANGULAR = "triangular"


class FocalSubject(str, Enum):
    PLAYER = "player"
    ENEMY = "enemy"
    BOSS = "boss"
    VEHICLE = "vehicle"
    LANDSCAPE = "landscape"
    EXPLOSION = "explosion"
    NPC = "npc"
    STRUCTURE = "structure"
    SUNSET = "sunset"
    WATERFALL = "waterfall"
    CUSTOM = "custom"


class FilterKind(str, Enum):
    NONE = "none"
    VINTAGE = "vintage"
    NOIR = "noir"
    SEPIA = "sepia"
    VIVID = "vivid"
    PASTEL = "pastel"
    CYBERPUNK = "cyberpunk"
    WATERCOLOR = "watercolor"
    HDR = "hdr"
    DRAMATIC = "dramatic"
    WARM = "warm"
    COOL = "cool"
    MONOCHROME = "monochrome"
    INFRARED = "infrared"
    DREAMY = "dreamy"


class CaptureStatus(str, Enum):
    PENDING = "pending"
    SCHEDULED = "scheduled"
    CAPTURED = "captured"
    FAILED = "failed"
    ARCHIVED = "archived"


class CaptureTrigger(str, Enum):
    MANUAL = "manual"
    DRAMATIC_MOMENT = "dramatic_moment"
    KILL_STREAK = "kill_streak"
    BOSS_ENCOUNTER = "boss_encounter"
    EXPLOSION = "explosion"
    SUNSET = "sunset"
    VICTORY = "victory"
    LEVEL_UP = "level_up"
    DISCOVERY = "discovery"
    SCHEDULED = "scheduled"


class PhotoEventKind(str, Enum):
    CAPTURE_QUEUED = "capture_queued"
    CAPTURE_TAKEN = "capture_taken"
    CAPTURE_FAILED = "capture_failed"
    SCENE_ANALYZED = "scene_analyzed"
    FILTER_RECOMMENDED = "filter_recommended"
    COMPOSITION_SCORED = "composition_scored"
    SCHEDULED = "scheduled"
    ARCHIVED = "archived"
    DELETED = "deleted"
    TICK = "tick"


# ---------------------------------------------------------------------------
# Data Classes
# ---------------------------------------------------------------------------

@dataclass
class SceneAnalysis:
    analysis_id: str
    timestamp: float = field(default_factory=_now)
    subject_id: str = ""
    subject_type: str = FocalSubject.PLAYER.value
    subject_position: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    camera_position: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    camera_target: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    fov: float = 60.0
    light_intensity: float = 0.7
    color_saturation: float = 0.6
    color_temperature: float = 5500.0
    motion_intensity: float = 0.2
    depth_of_field: float = 0.3
    particle_density: float = 0.1
    entity_count: int = 5
    dramatic_tension: float = 0.3
    composition_scores: Dict[str, float] = field(default_factory=dict)
    recommended_rules: List[str] = field(default_factory=list)
    recommended_filter: str = FilterKind.NONE.value
    recommended_focal_length: float = 50.0
    recommended_aperture: float = 2.8
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class FilterProfile:
    filter_id: str
    kind: str = FilterKind.NONE.value
    name: str = ""
    contrast: float = 1.0
    saturation: float = 1.0
    brightness: float = 1.0
    hue_shift: float = 0.0
    temperature: float = 0.0
    tint: float = 0.0
    vignette: float = 0.0
    grain: float = 0.0
    blur: float = 0.0
    chromatic_aberration: float = 0.0
    bloom: float = 0.0
    description: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class CaptureRequest:
    capture_id: str
    mode: str = CaptureMode.AUTO_COMPOSE.value
    trigger: str = CaptureTrigger.MANUAL.value
    subject_id: str = ""
    subject_type: str = FocalSubject.PLAYER.value
    camera_position: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    camera_target: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    fov: float = 60.0
    focal_length: float = 50.0
    aperture: float = 2.8
    filter_id: str = FilterKind.NONE.value
    composition_rule: str = CompositionRule.RULE_OF_THIRDS.value
    resolution_width: int = 1920
    resolution_height: int = 1080
    quality: float = 0.9
    metadata: Dict[str, Any] = field(default_factory=dict)
    status: str = CaptureStatus.PENDING.value
    created_at: float = field(default_factory=_now)
    captured_at: float = 0.0
    file_path: str = ""
    file_size: int = 0
    composition_score: float = 0.0
    dramatic_score: float = 0.0
    share_worthiness: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class CaptureSchedule:
    schedule_id: str
    trigger: str = CaptureTrigger.DRAMATIC_MOMENT.value
    enabled: bool = True
    cooldown: float = 30.0
    last_fired: float = 0.0
    min_tension: float = 0.5
    min_composition: float = 0.4
    preferred_mode: str = CaptureMode.DRAMATIC.value
    preferred_filter: str = FilterKind.DRAMATIC.value
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class PhotoConfig:
    max_captures: int = 1000
    max_schedules: int = 20
    auto_capture_enabled: bool = True
    auto_capture_cooldown: float = 15.0
    auto_capture_min_score: float = 0.6
    auto_filter_selection: bool = True
    auto_composition_selection: bool = True
    default_resolution_width: int = 1920
    default_resolution_height: int = 1080
    default_quality: float = 0.9
    share_worthiness_threshold: float = 0.7
    dramatic_tension_weight: float = 0.30
    composition_weight: float = 0.25
    lighting_weight: float = 0.15
    motion_weight: float = 0.10
    color_weight: float = 0.10
    depth_weight: float = 0.10
    save_directory: str = "/captures"

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class PhotoStats:
    total_captures: int = 0
    pending_captures: int = 0
    captured: int = 0
    failed: int = 0
    archived: int = 0
    auto_captures: int = 0
    manual_captures: int = 0
    total_scenes_analyzed: int = 0
    avg_composition_score: float = 0.0
    avg_share_worthiness: float = 0.0
    best_composition_score: float = 0.0
    best_share_worthiness: float = 0.0
    tick_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class PhotoSnapshot:
    captures: List[Dict[str, Any]] = field(default_factory=list)
    schedules: List[Dict[str, Any]] = field(default_factory=list)
    filters: List[Dict[str, Any]] = field(default_factory=list)
    stats: Dict[str, Any] = field(default_factory=dict)
    tick_count: int = 0
    timestamp: float = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class PhotoEvent:
    event_id: str
    kind: str
    timestamp: float
    details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


# ---------------------------------------------------------------------------
# AI Photo Director
# ---------------------------------------------------------------------------

class PhotoDirector:
    """AI-driven cinematic capture system with composition judgment."""

    _instance: Optional["PhotoDirector"] = None
    _lock = threading.RLock()

    def __init__(self) -> None:
        self._captures: Dict[str, CaptureRequest] = {}
        self._scenes: Dict[str, SceneAnalysis] = {}
        self._filters: Dict[str, FilterProfile] = {}
        self._schedules: Dict[str, CaptureSchedule] = {}
        self._events: List[PhotoEvent] = []
        self._stats = PhotoStats()
        self._config = PhotoConfig()
        self._tick_count: int = 0
        self._initialized: bool = False
        self._init_lock = threading.RLock()
        self._last_auto_capture: float = 0.0
        self._seed()

    @classmethod
    def get_instance(cls) -> "PhotoDirector":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def _seed(self) -> None:
        """Seed sample filters, schedules, and captures."""
        # Filter profiles
        self._filters["flt_none"] = FilterProfile(
            filter_id="flt_none", kind=FilterKind.NONE.value, name="Natural",
            description="No filter applied, natural game rendering."
        )
        self._filters["flt_vintage"] = FilterProfile(
            filter_id="flt_vintage", kind=FilterKind.VINTAGE.value, name="Vintage Film",
            contrast=1.1, saturation=0.8, brightness=0.95, temperature=0.15, vignette=0.3, grain=0.15,
            description="Warm vintage film look with subtle grain."
        )
        self._filters["flt_noir"] = FilterProfile(
            filter_id="flt_noir", kind=FilterKind.NOIR.value, name="Film Noir",
            contrast=1.4, saturation=0.0, brightness=0.9, vignette=0.4, grain=0.2,
            description="High-contrast black and white noir aesthetic."
        )
        self._filters["flt_cyberpunk"] = FilterProfile(
            filter_id="flt_cyberpunk", kind=FilterKind.CYBERPUNK.value, name="Cyberpunk Neon",
            contrast=1.2, saturation=1.3, brightness=0.85, hue_shift=10.0, tint=0.2, bloom=0.4,
            chromatic_aberration=0.15,
            description="Neon-soaked cyberpunk atmosphere with bloom."
        )
        self._filters["flt_dramatic"] = FilterProfile(
            filter_id="flt_dramatic", kind=FilterKind.DRAMATIC.value, name="Dramatic Cinema",
            contrast=1.25, saturation=1.05, brightness=0.92, vignette=0.25, bloom=0.2,
            description="Cinematic dramatic tone with vignette."
        )
        self._filters["flt_hdr"] = FilterProfile(
            filter_id="flt_hdr", kind=FilterKind.HDR.value, name="HDR Enhanced",
            contrast=1.15, saturation=1.2, brightness=1.0, bloom=0.3,
            description="High dynamic range with vivid colors."
        )
        self._filters["flt_dreamy"] = FilterProfile(
            filter_id="flt_dreamy", kind=FilterKind.DREAMY.value, name="Dreamy Soft",
            contrast=0.9, saturation=1.1, brightness=1.05, blur=0.15, bloom=0.5,
            description="Soft dreamy atmosphere with bloom glow."
        )
        self._filters["flt_warm"] = FilterProfile(
            filter_id="flt_warm", kind=FilterKind.WARM.value, name="Warm Sunset",
            temperature=0.25, saturation=1.1, brightness=1.0, vignette=0.1,
            description="Warm golden hour lighting."
        )
        self._filters["flt_cool"] = FilterProfile(
            filter_id="flt_cool", kind=FilterKind.COOL.value, name="Cool Blue",
            temperature=-0.2, saturation=0.95, brightness=0.98,
            description="Cool blue-toned atmosphere."
        )
        self._filters["flt_mono"] = FilterProfile(
            filter_id="flt_mono", kind=FilterKind.MONOCHROME.value, name="Monochrome",
            saturation=0.0, contrast=1.15, brightness=0.95,
            description="Classic monochrome rendering."
        )

        # Schedules
        self._schedules["sch_dramatic"] = CaptureSchedule(
            schedule_id="sch_dramatic",
            trigger=CaptureTrigger.DRAMATIC_MOMENT.value,
            cooldown=20.0,
            min_tension=0.6,
            min_composition=0.5,
            preferred_mode=CaptureMode.DRAMATIC.value,
            preferred_filter="flt_dramatic",
        )
        self._schedules["sch_kill_streak"] = CaptureSchedule(
            schedule_id="sch_kill_streak",
            trigger=CaptureTrigger.KILL_STREAK.value,
            cooldown=45.0,
            min_tension=0.7,
            min_composition=0.4,
            preferred_mode=CaptureMode.ACTION.value,
            preferred_filter="flt_hdr",
        )
        self._schedules["sch_sunset"] = CaptureSchedule(
            schedule_id="sch_sunset",
            trigger=CaptureTrigger.SUNSET.value,
            cooldown=120.0,
            min_tension=0.3,
            min_composition=0.6,
            preferred_mode=CaptureMode.LANDSCAPE.value,
            preferred_filter="flt_warm",
        )

        # Sample captures
        cap1 = CaptureRequest(
            capture_id="cap_sample_001",
            mode=CaptureMode.DRAMATIC.value,
            trigger=CaptureTrigger.BOSS_ENCOUNTER.value,
            subject_id="boss_dragon",
            subject_type=FocalSubject.BOSS.value,
            camera_position=(15.0, 8.0, 20.0),
            camera_target=(0.0, 5.0, 0.0),
            fov=55.0,
            focal_length=85.0,
            aperture=2.0,
            filter_id="flt_dramatic",
            composition_rule=CompositionRule.RULE_OF_THIRDS.value,
            status=CaptureStatus.CAPTURED.value,
            captured_at=_now() - 120.0,
            composition_score=0.82,
            dramatic_score=0.91,
            share_worthiness=0.87,
            file_path="/captures/cap_sample_001.png",
            file_size=2400000,
        )
        self._captures[cap1.capture_id] = cap1

        cap2 = CaptureRequest(
            capture_id="cap_sample_002",
            mode=CaptureMode.LANDSCAPE.value,
            trigger=CaptureTrigger.SUNSET.value,
            subject_id="vista_point_01",
            subject_type=FocalSubject.LANDSCAPE.value,
            camera_position=(100.0, 50.0, 100.0),
            camera_target=(95.0, 30.0, 95.0),
            fov=75.0,
            focal_length=24.0,
            aperture=8.0,
            filter_id="flt_warm",
            composition_rule=CompositionRule.GOLDEN_RATIO.value,
            status=CaptureStatus.CAPTURED.value,
            captured_at=_now() - 600.0,
            composition_score=0.88,
            dramatic_score=0.65,
            share_worthiness=0.79,
            file_path="/captures/cap_sample_002.png",
            file_size=3100000,
        )
        self._captures[cap2.capture_id] = cap2

        self._stats.total_captures = len(self._captures)
        self._stats.captured = len(self._captures)
        self._stats.avg_composition_score = (cap1.composition_score + cap2.composition_score) / 2
        self._stats.avg_share_worthiness = (cap1.share_worthiness + cap2.share_worthiness) / 2
        self._stats.best_composition_score = max(cap1.composition_score, cap2.composition_score)
        self._stats.best_share_worthiness = max(cap1.share_worthiness, cap2.share_worthiness)
        self._initialized = True

    # ------------------------------------------------------------------
    # Private Helpers
    # ------------------------------------------------------------------

    def _emit_event(self, kind: str, details: Optional[Dict[str, Any]] = None) -> None:
        event = PhotoEvent(
            event_id=f"evt_{self._tick_count}_{len(self._events)}",
            kind=kind,
            timestamp=_now(),
            details=details or {},
        )
        self._events.append(event)
        if len(self._events) > _MAX_EVENTS:
            self._events = self._events[-_MAX_EVENTS:]

    def _recompute_stats(self) -> None:
        self._stats.total_captures = len(self._captures)
        pending = 0
        captured = 0
        failed = 0
        archived = 0
        comp_scores = []
        share_scores = []
        for cap in self._captures.values():
            if cap.status == CaptureStatus.PENDING.value:
                pending += 1
            elif cap.status == CaptureStatus.CAPTURED.value:
                captured += 1
                if cap.composition_score > 0:
                    comp_scores.append(cap.composition_score)
                if cap.share_worthiness > 0:
                    share_scores.append(cap.share_worthiness)
            elif cap.status == CaptureStatus.FAILED.value:
                failed += 1
            elif cap.status == CaptureStatus.ARCHIVED.value:
                archived += 1
        self._stats.pending_captures = pending
        self._stats.captured = captured
        self._stats.failed = failed
        self._stats.archived = archived
        if comp_scores:
            self._stats.avg_composition_score = sum(comp_scores) / len(comp_scores)
            self._stats.best_composition_score = max(comp_scores)
        if share_scores:
            self._stats.avg_share_worthiness = sum(share_scores) / len(share_scores)
            self._stats.best_share_worthiness = max(share_scores)

    def _score_rule_of_thirds(self, subject_pos: Tuple[float, float, float], camera_target: Tuple[float, float, float]) -> float:
        """Score how well the subject follows the rule of thirds."""
        dx = subject_pos[0] - camera_target[0]
        dz = subject_pos[2] - camera_target[2]
        dist = math.sqrt(dx * dx + dz * dz)
        if dist < 0.01:
            return 0.5
        # Ideal: subject at 1/3 or 2/3 of frame
        angle = math.degrees(math.atan2(dz, dx))
        # Perfect third positions: 0, 90, 180, 270 degrees offset
        ideal_angles = [30.0, 150.0, 210.0, 330.0]
        best_diff = min(abs(((angle - a + 180) % 360) - 180) for a in ideal_angles)
        return _clamp(1.0 - best_diff / 45.0, 0.0, 1.0)

    def _score_golden_ratio(self, subject_pos: Tuple[float, float, float], camera_target: Tuple[float, float, float]) -> float:
        """Score golden ratio composition."""
        dx = subject_pos[0] - camera_target[0]
        dz = subject_pos[2] - camera_target[2]
        dist = math.sqrt(dx * dx + dz * dz)
        if dist < 0.01:
            return 0.5
        angle = math.degrees(math.atan2(dz, dx))
        # Golden ratio spiral points
        golden = 137.5
        ideal_angles = [golden * i % 360 for i in range(1, 5)]
        best_diff = min(abs(((angle - a + 180) % 360) - 180) for a in ideal_angles)
        return _clamp(1.0 - best_diff / 50.0, 0.0, 1.0)

    def _score_symmetry(self, subject_pos: Tuple[float, float, float], camera_target: Tuple[float, float, float]) -> float:
        """Score centered symmetry composition."""
        dx = subject_pos[0] - camera_target[0]
        dz = subject_pos[2] - camera_target[2]
        dist = math.sqrt(dx * dx + dz * dz)
        if dist < 0.01:
            return 1.0
        # Closer to center = better symmetry
        return _clamp(1.0 - min(dist / 20.0, 1.0) * 0.5, 0.5, 1.0)

    def _score_leading_lines(self, entity_count: int, motion_intensity: float) -> float:
        """Score leading lines (simplified based on scene structure)."""
        return _clamp(0.3 + entity_count * 0.1 + motion_intensity * 0.3, 0.0, 1.0)

    def _score_negative_space(self, entity_count: int, particle_density: float) -> float:
        """Score negative space availability."""
        return _clamp(1.0 - entity_count * 0.08 - particle_density * 0.5, 0.0, 1.0)

    def _recommend_filter(self, scene: SceneAnalysis) -> str:
        """Recommend a filter based on scene analysis."""
        if scene.dramatic_tension > 0.7:
            return "flt_dramatic"
        if scene.color_temperature < 4000:
            return "flt_cool"
        if scene.color_temperature > 7000:
            return "flt_warm"
        if scene.motion_intensity > 0.6:
            return "flt_hdr"
        if scene.subject_type == FocalSubject.LANDSCAPE.value:
            return "flt_warm"
        if scene.subject_type == FocalSubject.BOSS.value:
            return "flt_dramatic"
        if scene.subject_type == FocalSubject.EXPLOSION.value:
            return "flt_hdr"
        if scene.particle_density > 0.4:
            return "flt_dreamy"
        if scene.light_intensity < 0.3:
            return "flt_cyberpunk"
        return "flt_none"

    def _recommend_composition_rule(self, scene: SceneAnalysis) -> str:
        """Recommend a composition rule based on scene analysis."""
        if scene.subject_type in (FocalSubject.LANDSCAPE.value, FocalSubject.SUNSET.value):
            return CompositionRule.GOLDEN_RATIO.value
        if scene.subject_type in (FocalSubject.BOSS.value, FocalSubject.PLAYER.value):
            if scene.dramatic_tension > 0.6:
                return CompositionRule.DIAGONAL.value
            return CompositionRule.RULE_OF_THIRDS.value
        if scene.subject_type == FocalSubject.STRUCTURE.value:
            return CompositionRule.SYMMETRY.value
        if scene.subject_type == FocalSubject.EXPLOSION.value:
            return CompositionRule.CENTERED.value
        return CompositionRule.RULE_OF_THIRDS.value

    # ------------------------------------------------------------------
    # Scene Analysis
    # ------------------------------------------------------------------

    def analyze_scene(
        self,
        subject_id: str,
        subject_type: str,
        subject_position: Tuple[float, float, float],
        camera_position: Tuple[float, float, float],
        camera_target: Tuple[float, float, float],
        fov: float = 60.0,
        light_intensity: float = 0.7,
        color_saturation: float = 0.6,
        color_temperature: float = 5500.0,
        motion_intensity: float = 0.2,
        depth_of_field: float = 0.3,
        particle_density: float = 0.1,
        entity_count: int = 5,
        dramatic_tension: float = 0.3,
    ) -> SceneAnalysis:
        """Analyze a scene and compute composition scores."""
        analysis_id = f"scn_{self._tick_count}_{len(self._scenes)}"
        scene = SceneAnalysis(
            analysis_id=analysis_id,
            subject_id=subject_id,
            subject_type=subject_type,
            subject_position=subject_position,
            camera_position=camera_position,
            camera_target=camera_target,
            fov=fov,
            light_intensity=_clamp(light_intensity, 0.0, 1.0),
            color_saturation=_clamp(color_saturation, 0.0, 1.0),
            color_temperature=color_temperature,
            motion_intensity=_clamp(motion_intensity, 0.0, 1.0),
            depth_of_field=_clamp(depth_of_field, 0.0, 1.0),
            particle_density=_clamp(particle_density, 0.0, 1.0),
            entity_count=max(0, int(entity_count)),
            dramatic_tension=_clamp(dramatic_tension, 0.0, 1.0),
        )

        # Compute composition scores
        scores: Dict[str, float] = {}
        scores[CompositionRule.RULE_OF_THIRDS.value] = round(self._score_rule_of_thirds(subject_position, camera_target), 4)
        scores[CompositionRule.GOLDEN_RATIO.value] = round(self._score_golden_ratio(subject_position, camera_target), 4)
        scores[CompositionRule.SYMMETRY.value] = round(self._score_symmetry(subject_position, camera_target), 4)
        scores[CompositionRule.LEADING_LINES.value] = round(self._score_leading_lines(entity_count, motion_intensity), 4)
        scores[CompositionRule.NEGATIVE_SPACE.value] = round(self._score_negative_space(entity_count, particle_density), 4)
        scene.composition_scores = scores

        # Recommend best composition rules
        sorted_rules = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        scene.recommended_rules = [r[0] for r in sorted_rules[:3]]

        # Recommend filter
        scene.recommended_filter = self._recommend_filter(scene)

        # Recommend focal length based on subject type
        focal_map = {
            FocalSubject.LANDSCAPE.value: 24.0,
            FocalSubject.SUNSET.value: 35.0,
            FocalSubject.PLAYER.value: 50.0,
            FocalSubject.ENEMY.value: 85.0,
            FocalSubject.BOSS.value: 100.0,
            FocalSubject.VEHICLE.value: 70.0,
            FocalSubject.EXPLOSION.value: 35.0,
            FocalSubject.NPC.value: 50.0,
            FocalSubject.STRUCTURE.value: 28.0,
            FocalSubject.WATERFALL.value: 35.0,
        }
        scene.recommended_focal_length = focal_map.get(subject_type, 50.0)

        # Recommend aperture
        if depth_of_field > 0.6:
            scene.recommended_aperture = 1.4
        elif depth_of_field > 0.3:
            scene.recommended_aperture = 2.8
        else:
            scene.recommended_aperture = 8.0

        with self._init_lock:
            self._scenes[analysis_id] = scene
            if len(self._scenes) > _MAX_SCENES:
                oldest = next(iter(self._scenes))
                del self._scenes[oldest]
            self._stats.total_scenes_analyzed += 1
            self._emit_event(PhotoEventKind.SCENE_ANALYZED.value, {
                "analysis_id": analysis_id,
                "best_rule": scene.recommended_rules[0] if scene.recommended_rules else "",
                "filter": scene.recommended_filter,
                "dramatic_tension": scene.dramatic_tension,
            })
        return scene

    def get_scene(self, analysis_id: str) -> Optional[SceneAnalysis]:
        return self._scenes.get(analysis_id)

    def list_scenes(self, subject_type: Optional[str] = None, limit: int = 50) -> List[SceneAnalysis]:
        results = list(self._scenes.values())
        if subject_type:
            results = [s for s in results if s.subject_type == subject_type]
        return results[-max(0, int(limit)):]

    # ------------------------------------------------------------------
    # Filter Management
    # ------------------------------------------------------------------

    def register_filter(self, flt: FilterProfile) -> FilterProfile:
        with self._init_lock:
            self._filters[flt.filter_id] = flt
            self._emit_event(PhotoEventKind.FILTER_RECOMMENDED.value, {"filter_id": flt.filter_id, "kind": flt.kind})
            return flt

    def get_filter(self, filter_id: str) -> Optional[FilterProfile]:
        return self._filters.get(filter_id)

    def list_filters(self, kind: Optional[str] = None, limit: int = 100) -> List[FilterProfile]:
        results = list(self._filters.values())
        if kind:
            results = [f for f in results if f.kind == kind]
        return results[:max(0, int(limit))]

    def remove_filter(self, filter_id: str) -> bool:
        with self._init_lock:
            if filter_id not in self._filters:
                return False
            del self._filters[filter_id]
            return True

    # ------------------------------------------------------------------
    # Capture Management
    # ------------------------------------------------------------------

    def request_capture(self, req: CaptureRequest) -> CaptureRequest:
        with self._init_lock:
            if len(self._captures) >= _MAX_CAPTURES:
                oldest = next(iter(self._captures))
                del self._captures[oldest]
            self._captures[req.capture_id] = req
            req.created_at = _now()
            self._emit_event(PhotoEventKind.CAPTURE_QUEUED.value, {
                "capture_id": req.capture_id,
                "mode": req.mode,
                "trigger": req.trigger,
            })
            self._recompute_stats()
            return req

    def execute_capture(self, capture_id: str, file_path: str = "", file_size: int = 0) -> Optional[CaptureRequest]:
        cap = self._captures.get(capture_id)
        if cap is None:
            return None
        cap.status = CaptureStatus.CAPTURED.value
        cap.captured_at = _now()
        cap.file_path = file_path or f"/captures/{capture_id}.png"
        cap.file_size = file_size
        # Compute scores
        scene = self._scenes.get(f"scn_for_{capture_id}")
        if scene:
            cap.composition_score = max(scene.composition_scores.values()) if scene.composition_scores else 0.5
            cap.dramatic_score = scene.dramatic_tension
        else:
            cap.composition_score = _clamp(0.5 + cap.quality * 0.3, 0.0, 1.0)
            cap.dramatic_score = _clamp(0.4, 0.0, 1.0)
        # Share worthiness: weighted combination
        cap.share_worthiness = _clamp(
            cap.composition_score * 0.35
            + cap.dramatic_score * 0.30
            + cap.quality * 0.20
            + 0.15,
            0.0,
            1.0,
        )
        self._emit_event(PhotoEventKind.CAPTURE_TAKEN.value, {
            "capture_id": capture_id,
            "composition_score": cap.composition_score,
            "share_worthiness": cap.share_worthiness,
        })
        self._recompute_stats()
        return cap

    def get_capture(self, capture_id: str) -> Optional[CaptureRequest]:
        return self._captures.get(capture_id)

    def list_captures(self, status: Optional[str] = None, trigger: Optional[str] = None, limit: int = 50) -> List[CaptureRequest]:
        results = list(self._captures.values())
        if status:
            results = [c for c in results if c.status == status]
        if trigger:
            results = [c for c in results if c.trigger == trigger]
        results.sort(key=lambda c: c.created_at, reverse=True)
        return results[:max(0, int(limit))]

    def archive_capture(self, capture_id: str) -> Optional[CaptureRequest]:
        cap = self._captures.get(capture_id)
        if cap is None:
            return None
        cap.status = CaptureStatus.ARCHIVED.value
        self._emit_event(PhotoEventKind.ARCHIVED.value, {"capture_id": capture_id})
        self._recompute_stats()
        return cap

    def delete_capture(self, capture_id: str) -> bool:
        with self._init_lock:
            if capture_id not in self._captures:
                return False
            del self._captures[capture_id]
            self._emit_event(PhotoEventKind.DELETED.value, {"capture_id": capture_id})
            self._recompute_stats()
            return True

    # ------------------------------------------------------------------
    # Scheduling
    # ------------------------------------------------------------------

    def register_schedule(self, schedule: CaptureSchedule) -> CaptureSchedule:
        with self._init_lock:
            self._schedules[schedule.schedule_id] = schedule
            self._emit_event(PhotoEventKind.SCHEDULED.value, {"schedule_id": schedule.schedule_id, "trigger": schedule.trigger})
            return schedule

    def get_schedule(self, schedule_id: str) -> Optional[CaptureSchedule]:
        return self._schedules.get(schedule_id)

    def list_schedules(self, enabled_only: bool = False) -> List[CaptureSchedule]:
        results = list(self._schedules.values())
        if enabled_only:
            results = [s for s in results if s.enabled]
        return results

    def remove_schedule(self, schedule_id: str) -> bool:
        with self._init_lock:
            if schedule_id not in self._schedules:
                return False
            del self._schedules[schedule_id]
            return True

    def trigger_schedule(self, schedule_id: str, scene_analysis: Optional[SceneAnalysis] = None) -> Optional[CaptureRequest]:
        sch = self._schedules.get(schedule_id)
        if sch is None or not sch.enabled:
            return None
        now = _now()
        if now - sch.last_fired < sch.cooldown:
            return None
        if scene_analysis:
            if scene_analysis.dramatic_tension < sch.min_tension:
                return None
        sch.last_fired = now
        cap = CaptureRequest(
            capture_id=f"cap_auto_{self._tick_count}_{len(self._captures)}",
            mode=sch.preferred_mode,
            trigger=sch.trigger,
            filter_id=sch.preferred_filter,
            composition_rule=CompositionRule.RULE_OF_THIRDS.value,
            status=CaptureStatus.PENDING.value,
        )
        self._captures[cap.capture_id] = cap
        self._stats.auto_captures += 1
        self._emit_event(PhotoEventKind.CAPTURE_QUEUED.value, {
            "capture_id": cap.capture_id,
            "trigger": sch.trigger,
            "auto": True,
        })
        self._recompute_stats()
        return cap

    # ------------------------------------------------------------------
    # AI Recommendations
    # ------------------------------------------------------------------

    def recommend_capture(
        self,
        subject_id: str,
        subject_type: str,
        subject_position: Tuple[float, float, float],
        camera_position: Tuple[float, float, float],
        camera_target: Tuple[float, float, float],
        **scene_kwargs: Any,
    ) -> Dict[str, Any]:
        """Full AI recommendation: analyze scene and propose capture settings."""
        scene = self.analyze_scene(
            subject_id=subject_id,
            subject_type=subject_type,
            subject_position=subject_position,
            camera_position=camera_position,
            camera_target=camera_target,
            **scene_kwargs,
        )
        return {
            "analysis_id": scene.analysis_id,
            "recommended_composition": scene.recommended_rules[0] if scene.recommended_rules else CompositionRule.RULE_OF_THIRDS.value,
            "recommended_filter": scene.recommended_filter,
            "recommended_focal_length": scene.recommended_focal_length,
            "recommended_aperture": scene.recommended_aperture,
            "recommended_mode": self._recommend_mode(scene),
            "composition_scores": scene.composition_scores,
            "dramatic_tension": scene.dramatic_tension,
            "share_worthiness_estimate": self._estimate_share_worthiness(scene),
        }

    def _recommend_mode(self, scene: SceneAnalysis) -> str:
        if scene.dramatic_tension > 0.7:
            return CaptureMode.DRAMATIC.value
        if scene.subject_type == FocalSubject.LANDSCAPE.value:
            return CaptureMode.LANDSCAPE.value
        if scene.subject_type in (FocalSubject.PLAYER.value, FocalSubject.ENEMY.value):
            if scene.motion_intensity > 0.5:
                return CaptureMode.ACTION.value
            return CaptureMode.PORTRAIT.value
        if scene.motion_intensity > 0.7:
            return CaptureMode.ACTION.value
        return CaptureMode.AUTO_COMPOSE.value

    def _estimate_share_worthiness(self, scene: SceneAnalysis) -> float:
        comp = max(scene.composition_scores.values()) if scene.composition_scores else 0.5
        worth = (
            comp * self._config.composition_weight
            + scene.dramatic_tension * self._config.dramatic_tension_weight
            + scene.light_intensity * self._config.lighting_weight
            + scene.motion_intensity * self._config.motion_weight
            + scene.color_saturation * self._config.color_weight
            + scene.depth_of_field * self._config.depth_weight
        )
        return round(_clamp(worth, 0.0, 1.0), 4)

    # ------------------------------------------------------------------
    # Simulation Tick
    # ------------------------------------------------------------------

    def tick(self, delta_time: float = 0.016, current_time: Optional[float] = None) -> Dict[str, Any]:
        self._tick_count += 1
        events_emitted = 0

        # Auto-capture check
        if self._config.auto_capture_enabled:
            now = _now()
            if now - self._last_auto_capture > self._config.auto_capture_cooldown:
                # Find best scene for auto-capture
                best_scene = None
                best_tension = 0.0
                for scene in self._scenes.values():
                    if scene.dramatic_tension > best_tension:
                        best_tension = scene.dramatic_tension
                        best_scene = scene
                if best_scene and best_tension > self._config.auto_capture_min_score:
                    # Check schedules
                    for sch in self._schedules.values():
                        if sch.enabled and now - sch.last_fired > sch.cooldown:
                            cap = self.trigger_schedule(sch.schedule_id, best_scene)
                            if cap:
                                self._last_auto_capture = now
                                events_emitted += 1
                                break

        self._stats.tick_count = self._tick_count
        self._recompute_stats()

        return {
            "tick": self._tick_count,
            "captures_pending": self._stats.pending_captures,
            "scenes_analyzed": len(self._scenes),
            "events_emitted": events_emitted,
        }

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------

    def get_config(self) -> PhotoConfig:
        return self._config

    def set_config(self, config: PhotoConfig) -> PhotoConfig:
        with self._init_lock:
            self._config = config
            return self._config

    def list_events(self, limit: int = 100) -> List[PhotoEvent]:
        return list(self._events)[-max(0, int(limit)):]

    def get_stats(self) -> PhotoStats:
        self._recompute_stats()
        return self._stats

    def get_status(self) -> Dict[str, Any]:
        return {
            "initialized": self._initialized,
            "total_captures": len(self._captures),
            "total_scenes": len(self._scenes),
            "total_filters": len(self._filters),
            "total_schedules": len(self._schedules),
            "tick_count": self._tick_count,
            "config": self._config.to_dict(),
        }

    def get_snapshot(self) -> PhotoSnapshot:
        self._recompute_stats()
        return PhotoSnapshot(
            captures=[c.to_dict() for c in list(self._captures.values())[-20:]],
            schedules=[s.to_dict() for s in list(self._schedules.values())],
            filters=[f.to_dict() for f in list(self._filters.values())[:20]],
            stats=self._stats.to_dict(),
            tick_count=self._tick_count,
        )

    def reset(self) -> None:
        self._captures.clear()
        self._scenes.clear()
        self._filters.clear()
        self._schedules.clear()
        self._events.clear()
        self._stats = PhotoStats()
        self._config = PhotoConfig()
        self._tick_count = 0
        self._last_auto_capture = 0.0
        self._seed()


# ---------------------------------------------------------------------------
# Factory Function
# ---------------------------------------------------------------------------

def get_photo_director() -> PhotoDirector:
    """Return the singleton PhotoDirector instance."""
    return PhotoDirector.get_instance()
