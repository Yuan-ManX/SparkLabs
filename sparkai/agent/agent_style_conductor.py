"""
SparkLabs Agent - AI Cross-Modal Style Conductor

A style conductor agent for the SparkLabs AI-native game engine. It
maintains a unified aesthetic identity across visual, audio, narrative,
and mechanical dimensions. The conductor defines style profiles, checks
coherence across modalities, suggests harmonization adjustments, and
tracks style drift over the course of game development so that every
generated asset, scene, soundscape, and mechanic shares a coherent
aesthetic DNA.

Architecture:
  StyleConductor (singleton)
    |-- StyleProfile, StyleDimension, CoherenceCheck, HarmonizationSuggestion,
       StyleDriftReport, ConductorStats, ConductorSnapshot, ConductorEvent
    |-- StyleModality, StyleMood, CoherenceLevel, DriftDirection,
       ConductorEventKind

Core Capabilities:
  - register_profile / get_profile / list_profiles / update_profile /
    delete_profile: style profile lifecycle management.
  - register_dimension / get_dimension / list_dimensions / remove_dimension:
    per-modality style dimension definitions.
  - check_coherence / get_check / list_checks: cross-modal coherence
    assessment with per-modality scoring.
  - suggest_harmonization / get_suggestion / list_suggestions: actionable
    harmonization adjustments derived from coherence checks.
  - record_drift / get_drift_report / list_drift_reports: style drift
    tracking over time with direction and magnitude.
  - set_active_profile / get_active_profile: designate the current
    governing style profile.
  - list_events / get_stats / get_status / get_snapshot / reset:
    observability and state management.

The class implements the singleton pattern with double-checked locking
using ``threading.RLock``; consumers should obtain the instance through
:meth:`StyleConductor.get_instance` or the module-level
:func:`get_style_conductor` factory.
"""

from __future__ import annotations

import threading
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Capacity Constants
# ---------------------------------------------------------------------------

_MAX_PROFILES: int = 300
_MAX_DIMENSIONS: int = 2000
_MAX_CHECKS: int = 3000
_MAX_SUGGESTIONS: int = 2000
_MAX_DRIFT_REPORTS: int = 1000
_MAX_EVENTS: int = 5000


# ---------------------------------------------------------------------------
# Helper Functions
# ---------------------------------------------------------------------------


def _now() -> str:
    return datetime.utcnow().isoformat() + "Z"


def _new_id(prefix: str = "") -> str:
    base = uuid.uuid4().hex[:12]
    return f"{prefix}_{base}" if prefix else base


def _evict_fifo_dict(store: Dict[str, Any], max_size: int) -> None:
    cap = max(1, int(max_size))
    while len(store) > cap:
        oldest_key = next(iter(store), None)
        if oldest_key is None:
            break
        store.pop(oldest_key, None)


def _evict_fifo_list(store: List[Any], max_size: int) -> None:
    cap = max(1, int(max_size))
    while len(store) > cap:
        if not store:
            break
        store.pop(0)


def _to_jsonable(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, dict):
        return {str(k): _to_jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_to_jsonable(v) for v in value]
    if hasattr(value, "to_dict") and callable(value.to_dict):
        return _dataclass_to_dict(value)
    return value


def _dataclass_to_dict(instance: Any) -> Dict[str, Any]:
    if instance is None:
        return {}
    if not hasattr(instance, "__dataclass_fields__"):
        return dict(instance) if isinstance(instance, dict) else {}
    out: Dict[str, Any] = {}
    for name in getattr(instance, "__dataclass_fields__", {}).keys():
        try:
            raw = getattr(instance, name)
        except Exception:
            continue
        out[name] = _to_jsonable(raw)
    return out


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


def _clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    try:
        v = float(value)
    except (TypeError, ValueError):
        v = low
    if v < low:
        return low
    if v > high:
        return high
    return v


# ---------------------------------------------------------------------------
# Domain Enums
# ---------------------------------------------------------------------------


class StyleModality(Enum):
    """Modalities across which style coherence is maintained."""
    VISUAL = "visual"
    AUDIO = "audio"
    NARRATIVE = "narrative"
    MECHANICAL = "mechanical"
    UI = "ui"
    CINEMATIC = "cinematic"
    ENVIRONMENT = "environment"
    CHARACTER = "character"


class StyleMood(Enum):
    """Emotional moods that a style profile can express."""
    WHIMSICAL = "whimsical"
    GRITTY = "gritty"
    EPIC = "epic"
    SERENE = "serene"
    TENSE = "tense"
    MELANCHOLIC = "melancholic"
    UPLIFTING = "uplifting"
    MYSTERIOUS = "mysterious"
    PLAYFUL = "playful"
    DARK = "dark"
    VIBRANT = "vibrant"
    MINIMALIST = "minimalist"


class CoherenceLevel(Enum):
    """Coherence assessment levels."""
    INCOHERENT = "incoherent"
    WEAK = "weak"
    MODERATE = "moderate"
    STRONG = "strong"
    UNIFIED = "unified"


class DriftDirection(Enum):
    """Direction of style drift relative to the profile."""
    TOWARD = "toward"
    AWAY = "away"
    STABLE = "stable"
    OSCILLATING = "oscillating"


class ConductorEventKind(Enum):
    """Audit event types emitted by the conductor."""
    PROFILE_REGISTERED = "profile_registered"
    PROFILE_UPDATED = "profile_updated"
    PROFILE_DELETED = "profile_deleted"
    DIMENSION_REGISTERED = "dimension_registered"
    DIMENSION_REMOVED = "dimension_removed"
    COHERENCE_CHECKED = "coherence_checked"
    SUGGESTION_GENERATED = "suggestion_generated"
    DRIFT_RECORDED = "drift_recorded"
    ACTIVE_SET = "active_set"


# ---------------------------------------------------------------------------
# Data Classes
# ---------------------------------------------------------------------------


@dataclass
class StyleDimension:
    """A per-modality style dimension with descriptor and intensity."""
    dimension_id: str = field(default_factory=lambda: _new_id("sdi"))
    modality: str = StyleModality.VISUAL.value
    name: str = ""
    descriptor: str = ""
    intensity: float = 0.5
    mood: str = StyleMood.SERENE.value
    palette: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class StyleProfile:
    """A unified aesthetic identity spanning all modalities."""
    profile_id: str = field(default_factory=lambda: _new_id("spr"))
    name: str = ""
    description: str = ""
    dimension_ids: List[str] = field(default_factory=list)
    primary_mood: str = StyleMood.EPIC.value
    secondary_moods: List[str] = field(default_factory=list)
    coherence_target: float = 0.8
    version: int = 1
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=_now)
    updated_at: str = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class CoherenceCheck:
    """Result of a cross-modal coherence assessment."""
    check_id: str = field(default_factory=lambda: _new_id("sch"))
    profile_id: str = ""
    modality_scores: Dict[str, float] = field(default_factory=dict)
    overall_coherence: float = 0.5
    coherence_level: str = CoherenceLevel.MODERATE.value
    conflict_pairs: List[Dict[str, Any]] = field(default_factory=list)
    checked_at: str = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class HarmonizationSuggestion:
    """An actionable suggestion to improve cross-modal coherence."""
    suggestion_id: str = field(default_factory=lambda: _new_id("sug"))
    check_id: str = ""
    profile_id: str = ""
    modality: str = StyleModality.VISUAL.value
    current_value: str = ""
    suggested_value: str = ""
    rationale: str = ""
    priority: float = 0.5
    created_at: str = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class StyleDriftReport:
    """A report tracking style drift over a period."""
    report_id: str = field(default_factory=lambda: _new_id("sdr"))
    profile_id: str = ""
    modality: str = StyleModality.VISUAL.value
    direction: str = DriftDirection.STABLE.value
    magnitude: float = 0.0
    description: str = ""
    from_snapshot: str = ""
    to_snapshot: str = ""
    recorded_at: str = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class ConductorStats:
    """Aggregate counters for the conductor."""
    total_profiles: int = 0
    total_dimensions: int = 0
    total_checks: int = 0
    total_suggestions: int = 0
    total_drift_reports: int = 0
    avg_coherence: float = 0.0
    coherence_distribution: Dict[str, int] = field(default_factory=dict)
    last_updated: str = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class ConductorSnapshot:
    """Immutable point-in-time capture of conductor state."""
    profiles: Dict[str, Any] = field(default_factory=dict)
    dimensions: Dict[str, Any] = field(default_factory=dict)
    checks: List[Dict[str, Any]] = field(default_factory=list)
    suggestions: List[Dict[str, Any]] = field(default_factory=list)
    drift_reports: List[Dict[str, Any]] = field(default_factory=list)
    stats: Dict[str, Any] = field(default_factory=dict)
    taken_at: str = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class ConductorEvent:
    """Audit log entry."""
    event_id: str = field(default_factory=lambda: _new_id("cev"))
    kind: str = ConductorEventKind.PROFILE_REGISTERED.value
    payload: Dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


# ---------------------------------------------------------------------------
# Style Conductor Singleton
# ---------------------------------------------------------------------------


class StyleConductor:
    """Singleton agent that conducts cross-modal style coherence.

    The conductor maintains style profiles (unified aesthetic identities),
    style dimensions (per-modality descriptors), and performs coherence
    checks across modalities. It generates harmonization suggestions when
    modalities conflict and tracks style drift over time.
    """

    _instance: Optional["StyleConductor"] = None
    _inner_lock = threading.RLock()

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._initialized: bool = False
        self._profiles: Dict[str, StyleProfile] = {}
        self._dimensions: Dict[str, StyleDimension] = {}
        self._checks: Dict[str, CoherenceCheck] = {}
        self._suggestions: Dict[str, HarmonizationSuggestion] = {}
        self._drift_reports: Dict[str, StyleDriftReport] = {}
        self._events: List[ConductorEvent] = []
        self._active_profile_id: str = ""
        self._dimensions_by_profile: Dict[str, List[str]] = {}
        self._dimensions_by_modality: Dict[str, List[str]] = {}

    # ------------------------------------------------------------------
    # Singleton
    # ------------------------------------------------------------------

    @classmethod
    def get_instance(cls) -> "StyleConductor":
        if cls._instance is None:
            with cls._inner_lock:
                if cls._instance is None:
                    cls._instance = cls()
                    cls._instance._initialize()
        return cls._instance

    def _initialize(self) -> None:
        with self._lock:
            if self._initialized:
                return
            self._seed_defaults()
            self._initialized = True

    def _seed_defaults(self) -> None:
        """Seed a default style profile with dimensions for each modality."""
        pid = _new_id("spr")
        dim_ids: List[str] = []
        defaults = [
            (StyleModality.VISUAL, "Color Palette", "Warm earth tones with cool accents",
             0.7, StyleMood.EPIC, ["#8B4513", "#DAA520", "#4682B4"]),
            (StyleModality.AUDIO, "Soundtrack Tone", "Orchestral with tribal percussion",
             0.6, StyleMood.EPIC, []),
            (StyleModality.NARRATIVE, "Story Voice", "Mythic third-person with colloquial dialogue",
             0.6, StyleMood.MYSTERIOUS, []),
            (StyleModality.MECHANICAL, "Gameplay Rhythm", "Deliberate pacing with burst combat",
             0.5, StyleMood.TENSE, []),
            (StyleModality.UI, "Interface Aesthetic", "Minimalist with ornate borders",
             0.4, StyleMood.MINIMALIST, []),
            (StyleModality.CINEMATIC, "Camera Language", "Slow pans with quick cuts on action",
             0.5, StyleMood.EPIC, []),
            (StyleModality.ENVIRONMENT, "World Atmosphere", "Vast landscapes with intimate details",
             0.6, StyleMood.SERENE, []),
            (StyleModality.CHARACTER, "Character Silhouettes", "Bold readable shapes with intricate armor",
             0.6, StyleMood.EPIC, []),
        ]
        for modality, name, desc, intensity, mood, palette in defaults:
            dim = StyleDimension(
                dimension_id=_new_id("sdi"),
                modality=modality.value,
                name=name,
                descriptor=desc,
                intensity=intensity,
                mood=mood.value,
                palette=palette,
            )
            self._dimensions[dim.dimension_id] = dim
            dim_ids.append(dim.dimension_id)
            self._index_append(self._dimensions_by_modality, modality.value, dim.dimension_id)

        profile = StyleProfile(
            profile_id=pid,
            name="Default Epic Fantasy",
            description="A unified epic fantasy aesthetic across all modalities",
            dimension_ids=dim_ids,
            primary_mood=StyleMood.EPIC.value,
            secondary_moods=[StyleMood.MYSTERIOUS.value, StyleMood.SERENE.value],
            coherence_target=0.8,
        )
        self._profiles[pid] = profile
        self._dimensions_by_profile[pid] = list(dim_ids)
        self._active_profile_id = pid

    def _index_append(self, index: Dict[str, List[str]], key: str, value: str) -> None:
        if key not in index:
            index[key] = []
        if value not in index[key]:
            index[key].append(value)

    def _emit_event(self, kind: ConductorEventKind, payload: Dict[str, Any]) -> None:
        evt = ConductorEvent(kind=kind.value, payload=payload)
        self._events.append(evt)
        _evict_fifo_list(self._events, _MAX_EVENTS)

    # ------------------------------------------------------------------
    # Dimension Management
    # ------------------------------------------------------------------

    def register_dimension(self, modality: Any = "", name: str = "",
                           descriptor: str = "", intensity: float = 0.5,
                           mood: Any = "serene", palette: Optional[List[str]] = None,
                           tags: Optional[List[str]] = None,
                           dimension_id: str = "",
                           metadata: Optional[Dict[str, Any]] = None) -> StyleDimension:
        with self._lock:
            mod_val = self._coerce_modality(modality).value
            did = dimension_id or _new_id("sdi")
            dim = StyleDimension(
                dimension_id=did,
                modality=mod_val,
                name=name,
                descriptor=descriptor,
                intensity=_clamp(intensity),
                mood=self._coerce_mood(mood).value,
                palette=list(palette) if palette else [],
                tags=list(tags) if tags else [],
                metadata=metadata or {},
            )
            self._dimensions[did] = dim
            self._index_append(self._dimensions_by_modality, mod_val, did)
            _evict_fifo_dict(self._dimensions, _MAX_DIMENSIONS)
            self._emit_event(ConductorEventKind.DIMENSION_REGISTERED, {"dimension_id": did})
            return dim

    def get_dimension(self, dimension_id: str) -> Optional[StyleDimension]:
        with self._lock:
            return self._dimensions.get(dimension_id)

    def list_dimensions(self, modality: Any = None, limit: int = 100) -> List[StyleDimension]:
        with self._lock:
            if modality is not None and modality != "":
                mod_val = self._coerce_modality(modality).value
                ids = self._dimensions_by_modality.get(mod_val, [])
                return [self._dimensions[did] for did in ids if did in self._dimensions][:limit]
            return list(self._dimensions.values())[-limit:]

    def remove_dimension(self, dimension_id: str) -> bool:
        with self._lock:
            dim = self._dimensions.pop(dimension_id, None)
            if dim is None:
                return False
            mod_list = self._dimensions_by_modality.get(dim.modality, [])
            if dimension_id in mod_list:
                mod_list.remove(dimension_id)
            for profile in self._profiles.values():
                if dimension_id in profile.dimension_ids:
                    profile.dimension_ids = [d for d in profile.dimension_ids if d != dimension_id]
            self._emit_event(ConductorEventKind.DIMENSION_REMOVED, {"dimension_id": dimension_id})
            return True

    # ------------------------------------------------------------------
    # Profile Management
    # ------------------------------------------------------------------

    def register_profile(self, name: str = "", description: str = "",
                         dimension_ids: Optional[List[str]] = None,
                         primary_mood: Any = "epic",
                         secondary_moods: Optional[List[str]] = None,
                         coherence_target: float = 0.8,
                         tags: Optional[List[str]] = None,
                         profile_id: str = "",
                         metadata: Optional[Dict[str, Any]] = None) -> StyleProfile:
        with self._lock:
            pid = profile_id or _new_id("spr")
            profile = StyleProfile(
                profile_id=pid,
                name=name,
                description=description,
                dimension_ids=list(dimension_ids) if dimension_ids else [],
                primary_mood=self._coerce_mood(primary_mood).value,
                secondary_moods=list(secondary_moods) if secondary_moods else [],
                coherence_target=_clamp(coherence_target),
                tags=list(tags) if tags else [],
                metadata=metadata or {},
            )
            self._profiles[pid] = profile
            self._dimensions_by_profile[pid] = list(profile.dimension_ids)
            _evict_fifo_dict(self._profiles, _MAX_PROFILES)
            self._emit_event(ConductorEventKind.PROFILE_REGISTERED, {"profile_id": pid})
            return profile

    def get_profile(self, profile_id: str) -> Optional[StyleProfile]:
        with self._lock:
            return self._profiles.get(profile_id)

    def list_profiles(self, limit: int = 100) -> List[StyleProfile]:
        with self._lock:
            return list(self._profiles.values())[-limit:]

    def update_profile(self, profile_id: str, **kwargs: Any) -> Optional[StyleProfile]:
        with self._lock:
            profile = self._profiles.get(profile_id)
            if profile is None:
                return None
            for key, value in kwargs.items():
                if key == "name" and isinstance(value, str):
                    profile.name = value
                elif key == "description" and isinstance(value, str):
                    profile.description = value
                elif key == "dimension_ids" and isinstance(value, list):
                    profile.dimension_ids = list(value)
                    self._dimensions_by_profile[profile_id] = list(value)
                elif key == "primary_mood":
                    profile.primary_mood = self._coerce_mood(value).value
                elif key == "secondary_moods" and isinstance(value, list):
                    profile.secondary_moods = list(value)
                elif key == "coherence_target":
                    profile.coherence_target = _clamp(value)
                elif key == "tags" and isinstance(value, list):
                    profile.tags = list(value)
                elif key == "metadata" and isinstance(value, dict):
                    profile.metadata = dict(value)
            profile.version += 1
            profile.updated_at = _now()
            self._emit_event(ConductorEventKind.PROFILE_UPDATED, {"profile_id": profile_id})
            return profile

    def delete_profile(self, profile_id: str) -> bool:
        with self._lock:
            if profile_id not in self._profiles:
                return False
            self._profiles.pop(profile_id)
            self._dimensions_by_profile.pop(profile_id, None)
            if self._active_profile_id == profile_id:
                self._active_profile_id = ""
            self._emit_event(ConductorEventKind.PROFILE_DELETED, {"profile_id": profile_id})
            return True

    def set_active_profile(self, profile_id: str) -> bool:
        with self._lock:
            if profile_id not in self._profiles:
                return False
            self._active_profile_id = profile_id
            self._emit_event(ConductorEventKind.ACTIVE_SET, {"profile_id": profile_id})
            return True

    def get_active_profile(self) -> Optional[StyleProfile]:
        with self._lock:
            if not self._active_profile_id:
                return None
            return self._profiles.get(self._active_profile_id)

    # ------------------------------------------------------------------
    # Coherence Checking
    # ------------------------------------------------------------------

    def check_coherence(self, profile_id: str = "") -> CoherenceCheck:
        """Assess cross-modal coherence for a style profile."""
        with self._lock:
            pid = profile_id or self._active_profile_id
            profile = self._profiles.get(pid)
            dim_ids = profile.dimension_ids if profile else []
            dims = [self._dimensions[d] for d in dim_ids if d in self._dimensions]

            modality_scores: Dict[str, float] = {}
            conflict_pairs: List[Dict[str, Any]] = []

            if not dims:
                overall = 0.0
                level = CoherenceLevel.INCOHERENT
            else:
                # Group dimensions by modality
                by_modality: Dict[str, List[StyleDimension]] = {}
                for d in dims:
                    by_modality.setdefault(d.modality, []).append(d)

                # Score each modality by mood alignment and intensity consistency
                profile_moods = set()
                if profile:
                    profile_moods.add(profile.primary_mood)
                    profile_moods.update(profile.secondary_moods)

                for mod, mod_dims in by_modality.items():
                    mood_match = 0
                    for d in mod_dims:
                        if d.mood in profile_moods or not profile_moods:
                            mood_match += 1
                    mood_score = mood_match / max(1, len(mod_dims))
                    avg_intensity = sum(d.intensity for d in mod_dims) / max(1, len(mod_dims))
                    modality_scores[mod] = round(mood_score * 0.6 + avg_intensity * 0.4, 4)

                # Detect conflicts between modalities
                modalities = list(by_modality.keys())
                for i in range(len(modalities)):
                    for j in range(i + 1, len(modalities)):
                        m1, m2 = modalities[i], modalities[j]
                        dims1 = by_modality[m1]
                        dims2 = by_modality[m2]
                        moods1 = set(d.mood for d in dims1)
                        moods2 = set(d.mood for d in dims2)
                        # Conflicting mood pairs
                        conflicts = {
                            (StyleMood.DARK.value, StyleMood.VIBRANT.value),
                            (StyleMood.GRITTY.value, StyleMood.WHIMSICAL.value),
                            (StyleMood.TENSE.value, StyleMood.SERENE.value),
                            (StyleMood.MELANCHOLIC.value, StyleMood.UPLIFTING.value),
                            (StyleMood.PLAYFUL.value, StyleMood.DARK.value),
                        }
                        for mo1 in moods1:
                            for mo2 in moods2:
                                if (mo1, mo2) in conflicts or (mo2, mo1) in conflicts:
                                    conflict_pairs.append({
                                        "modality_a": m1,
                                        "modality_b": m2,
                                        "mood_a": mo1,
                                        "mood_b": mo2,
                                        "reason": "conflicting moods",
                                    })

                overall = round(sum(modality_scores.values()) / max(1, len(modality_scores)), 4)
                # Penalty for conflicts
                if conflict_pairs:
                    overall = round(max(0.0, overall - 0.1 * len(conflict_pairs)), 4)

                if overall >= 0.9:
                    level = CoherenceLevel.UNIFIED
                elif overall >= 0.7:
                    level = CoherenceLevel.STRONG
                elif overall >= 0.5:
                    level = CoherenceLevel.MODERATE
                elif overall >= 0.3:
                    level = CoherenceLevel.WEAK
                else:
                    level = CoherenceLevel.INCOHERENT

            check = CoherenceCheck(
                profile_id=pid,
                modality_scores=modality_scores,
                overall_coherence=overall,
                coherence_level=level.value,
                conflict_pairs=conflict_pairs,
            )
            self._checks[check.check_id] = check
            _evict_fifo_dict(self._checks, _MAX_CHECKS)
            self._emit_event(ConductorEventKind.COHERENCE_CHECKED, {
                "check_id": check.check_id,
                "overall": overall,
                "level": level.value,
            })
            return check

    def get_check(self, check_id: str) -> Optional[CoherenceCheck]:
        with self._lock:
            return self._checks.get(check_id)

    def list_checks(self, profile_id: str = "", limit: int = 100) -> List[CoherenceCheck]:
        with self._lock:
            items = list(self._checks.values())
            if profile_id:
                items = [c for c in items if c.profile_id == profile_id]
            return items[-limit:]

    # ------------------------------------------------------------------
    # Harmonization Suggestions
    # ------------------------------------------------------------------

    def suggest_harmonization(self, check_id: str = "",
                              profile_id: str = "") -> List[HarmonizationSuggestion]:
        """Generate harmonization suggestions based on a coherence check."""
        with self._lock:
            check = self._checks.get(check_id)
            if check is None and profile_id:
                check = self.check_coherence(profile_id=profile_id)
            if check is None:
                return []

            suggestions: List[HarmonizationSuggestion] = []
            profile = self._profiles.get(check.profile_id)
            profile_mood = profile.primary_mood if profile else StyleMood.EPIC.value

            # Generate suggestions for conflicting pairs
            for conflict in check.conflict_pairs:
                mod = conflict.get("modality_a", "")
                mood_a = conflict.get("mood_a", "")
                sug = HarmonizationSuggestion(
                    suggestion_id=_new_id("sug"),
                    check_id=check.check_id,
                    profile_id=check.profile_id,
                    modality=mod,
                    current_value=mood_a,
                    suggested_value=profile_mood,
                    rationale=f"Align '{mod}' mood from '{mood_a}' to '{profile_mood}' for coherence",
                    priority=0.8,
                )
                self._suggestions[sug.suggestion_id] = sug
                suggestions.append(sug)

            # Generate suggestions for low-scoring modalities
            for mod, score in check.modality_scores.items():
                if score < 0.5:
                    sug = HarmonizationSuggestion(
                        suggestion_id=_new_id("sug"),
                        check_id=check.check_id,
                        profile_id=check.profile_id,
                        modality=mod,
                        current_value=f"score={score:.2f}",
                        suggested_value=f"target={profile.coherence_target:.2f}" if profile else "target=0.80",
                        rationale=f"'{mod}' modality scores below coherence target; review descriptors and mood alignment",
                        priority=0.6,
                    )
                    self._suggestions[sug.suggestion_id] = sug
                    suggestions.append(sug)

            _evict_fifo_dict(self._suggestions, _MAX_SUGGESTIONS)
            for sug in suggestions:
                self._emit_event(ConductorEventKind.SUGGESTION_GENERATED, {
                    "suggestion_id": sug.suggestion_id,
                    "modality": sug.modality,
                })
            return suggestions

    def get_suggestion(self, suggestion_id: str) -> Optional[HarmonizationSuggestion]:
        with self._lock:
            return self._suggestions.get(suggestion_id)

    def list_suggestions(self, profile_id: str = "", modality: Any = None,
                         limit: int = 100) -> List[HarmonizationSuggestion]:
        with self._lock:
            items = list(self._suggestions.values())
            if profile_id:
                items = [s for s in items if s.profile_id == profile_id]
            if modality is not None and modality != "":
                mod_val = self._coerce_modality(modality).value
                items = [s for s in items if s.modality == mod_val]
            return items[-limit:]

    # ------------------------------------------------------------------
    # Drift Tracking
    # ------------------------------------------------------------------

    def record_drift(self, profile_id: str = "", modality: Any = "",
                     direction: Any = "stable", magnitude: float = 0.0,
                     description: str = "", from_snapshot: str = "",
                     to_snapshot: str = "",
                     report_id: str = "") -> StyleDriftReport:
        with self._lock:
            mod_val = self._coerce_modality(modality).value
            rid = report_id or _new_id("sdr")
            report = StyleDriftReport(
                report_id=rid,
                profile_id=profile_id,
                modality=mod_val,
                direction=self._coerce_drift(direction).value,
                magnitude=_clamp(magnitude),
                description=description,
                from_snapshot=from_snapshot,
                to_snapshot=to_snapshot,
            )
            self._drift_reports[rid] = report
            _evict_fifo_dict(self._drift_reports, _MAX_DRIFT_REPORTS)
            self._emit_event(ConductorEventKind.DRIFT_RECORDED, {"report_id": rid})
            return report

    def get_drift_report(self, report_id: str) -> Optional[StyleDriftReport]:
        with self._lock:
            return self._drift_reports.get(report_id)

    def list_drift_reports(self, profile_id: str = "", modality: Any = None,
                           limit: int = 100) -> List[StyleDriftReport]:
        with self._lock:
            items = list(self._drift_reports.values())
            if profile_id:
                items = [r for r in items if r.profile_id == profile_id]
            if modality is not None and modality != "":
                mod_val = self._coerce_modality(modality).value
                items = [r for r in items if r.modality == mod_val]
            return items[-limit:]

    # ------------------------------------------------------------------
    # Enum Coercion Helpers
    # ------------------------------------------------------------------

    def _coerce_modality(self, value: Any) -> StyleModality:
        if isinstance(value, StyleModality):
            return value
        if isinstance(value, str) and value:
            try:
                return StyleModality(value)
            except ValueError:
                pass
        return StyleModality.VISUAL

    def _coerce_mood(self, value: Any) -> StyleMood:
        if isinstance(value, StyleMood):
            return value
        if isinstance(value, str) and value:
            try:
                return StyleMood(value)
            except ValueError:
                pass
        return StyleMood.SERENE

    def _coerce_drift(self, value: Any) -> DriftDirection:
        if isinstance(value, DriftDirection):
            return value
        if isinstance(value, str) and value:
            try:
                return DriftDirection(value)
            except ValueError:
                pass
        return DriftDirection.STABLE

    def _coerce_coherence(self, value: Any) -> CoherenceLevel:
        if isinstance(value, CoherenceLevel):
            return value
        if isinstance(value, str) and value:
            try:
                return CoherenceLevel(value)
            except ValueError:
                pass
        return CoherenceLevel.MODERATE

    # ------------------------------------------------------------------
    # Observability
    # ------------------------------------------------------------------

    def list_events(self, limit: int = 100) -> List[ConductorEvent]:
        with self._lock:
            return list(self._events[-limit:])

    def get_stats(self) -> ConductorStats:
        with self._lock:
            total_coherence = 0.0
            level_dist: Dict[str, int] = {}
            for c in self._checks.values():
                total_coherence += c.overall_coherence
                level_dist[c.coherence_level] = level_dist.get(c.coherence_level, 0) + 1
            avg = round(total_coherence / max(1, len(self._checks)), 4)
            return ConductorStats(
                total_profiles=len(self._profiles),
                total_dimensions=len(self._dimensions),
                total_checks=len(self._checks),
                total_suggestions=len(self._suggestions),
                total_drift_reports=len(self._drift_reports),
                avg_coherence=avg,
                coherence_distribution=level_dist,
            )

    def get_status(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "initialized": self._initialized,
                "profiles": len(self._profiles),
                "dimensions": len(self._dimensions),
                "checks": len(self._checks),
                "suggestions": len(self._suggestions),
                "drift_reports": len(self._drift_reports),
                "events": len(self._events),
                "active_profile_id": self._active_profile_id,
            }

    def get_snapshot(self) -> ConductorSnapshot:
        with self._lock:
            return ConductorSnapshot(
                profiles={pid: p.to_dict() for pid, p in list(self._profiles.items())[:50]},
                dimensions={did: d.to_dict() for did, d in list(self._dimensions.items())[:50]},
                checks=[c.to_dict() for c in list(self._checks.values())[-50:]],
                suggestions=[s.to_dict() for s in list(self._suggestions.values())[-50:]],
                drift_reports=[r.to_dict() for r in list(self._drift_reports.values())[-50:]],
                stats=self.get_stats().to_dict(),
            )

    def reset(self) -> None:
        with self._lock:
            self._profiles.clear()
            self._dimensions.clear()
            self._checks.clear()
            self._suggestions.clear()
            self._drift_reports.clear()
            self._events.clear()
            self._dimensions_by_profile.clear()
            self._dimensions_by_modality.clear()
            self._active_profile_id = ""
            self._seed_defaults()


def get_style_conductor() -> StyleConductor:
    """Factory function to obtain the singleton StyleConductor."""
    return StyleConductor.get_instance()
