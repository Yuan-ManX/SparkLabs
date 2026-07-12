"""
SparkLabs Agent - AI Voice Synthesizer

An AI-native fusion module that synthesizes spoken voice lines for the
SparkLabs game engine. The synthesizer treats NPC and player speech as a
living system: reusable voice profiles are assembled from acoustic
parameters, then instantiated into synthesized lines that carry emotion
colouring, pitch and speed overrides, phoneme and viseme data, and
deterministic duration modelling that reacts to the live game context.

This module embodies the AI-native principle: voice is not a static asset
but an adaptive construction that scales to narrative beats, shifts emotion
on the fly as the game context changes, layers prosody rules across
speech, and records a full event timeline that can be replayed, audited,
and tuned.

Architecture:
  AIVoiceSynthesizer (singleton)
    |-- VoiceProfile, VoiceLine, SynthesisBatch, VoiceClone,
        EmotionPreset, VoiceDirection, PhonemeMap, ProsodyRule,
        VoiceSynthConfig, VoiceSynthStats, VoiceSynthSnapshot,
        VoiceSynthEvent
    |-- VoiceGender, VoiceEmotion, VoiceLanguage, VoiceAgeGroup,
        VoiceAccent, SynthesisStatus, VoiceProfileType, AudioFormat,
        VoiceSynthEventKind

Core Capabilities:
  - register_profile / get_profile / list_profiles / remove_profile /
    update_profile: voice profile library management across every gender,
    age group, language, and accent.
  - synthesize_line / get_line / list_lines / remove_line: speech
    synthesis from text with emotion, pitch, speed, and volume overrides
    plus deterministic phoneme and viseme generation.
  - create_batch / get_batch / list_batches / add_line_to_batch /
    remove_line_from_batch / process_batch / remove_batch: batch synthesis
    lifecycle management with progress tracking.
  - clone_voice / get_clone / list_clones / remove_clone: voice cloning
    from source profile samples with quality scoring.
  - create_emotion_preset / get_emotion_preset / list_emotion_presets /
    remove_emotion_preset / apply_emotion: emotion preset library and
    live emotion application to profiles.
  - create_direction / get_direction / list_directions / remove_direction:
    voice direction management tied to scene context.
  - register_phoneme_map / get_phoneme_map / list_phoneme_maps:
    language-specific phoneme and viseme set management.
  - register_prosody_rule / get_prosody_rule / list_prosody_rules /
    remove_prosody_rule: prosody rule library for speech shaping.
  - auto_direct / auto_generate_lines / batch_synthesize: AI-driven
    scene analysis, dialogue generation, and bulk synthesis.
  - list_events / get_stats / get_status / get_snapshot / set_config /
    get_config / tick / reset: observability, tuning, and state management.
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

_MAX_PROFILES: int = 1000
_MAX_LINES: int = 5000
_MAX_BATCHES: int = 500
_MAX_CLONES: int = 200
_MAX_EMOTION_PRESETS: int = 500
_MAX_DIRECTIONS: int = 500
_MAX_PHONEME_MAPS: int = 64
_MAX_PROSODY_RULES: int = 500
_MAX_EVENTS: int = 8000
_MAX_LINES_PER_BATCH: int = 256


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


def _coerce_enum(enum_cls: Any, value: Any, default: Any = None) -> Any:
    if value is None:
        return default
    if isinstance(value, enum_cls):
        return value
    try:
        return enum_cls(value)
    except (ValueError, KeyError):
        return default


def _to_jsonable(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, dict):
        return {str(k): _to_jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_to_jsonable(v) for v in value]
    if hasattr(value, "__dataclass_fields__"):
        return _dataclass_to_dict(value)
    if hasattr(value, "to_dict") and callable(value.to_dict):
        return value.to_dict()
    return value


def _dataclass_to_dict(instance: Any) -> Dict[str, Any]:
    # Check __dataclass_fields__ BEFORE to_dict to avoid recursion when a
    # dataclass also defines a to_dict method that delegates back here.
    if instance is None:
        return {}
    if not hasattr(instance, "__dataclass_fields__"):
        if isinstance(instance, dict):
            return {str(k): _to_jsonable(v) for k, v in instance.items()}
        if hasattr(instance, "to_dict") and callable(instance.to_dict):
            return instance.to_dict()
        return {}
    out: Dict[str, Any] = {}
    for name in getattr(instance, "__dataclass_fields__", {}).keys():
        try:
            raw = getattr(instance, name)
        except Exception:
            continue
        out[name] = _to_jsonable(raw)
    return out


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


# ---------------------------------------------------------------------------
# Emotion Acoustic Tables
# ---------------------------------------------------------------------------

# Pitch shift in Hz applied per emotion. Positive raises the voice, negative
# lowers it. The shift is scaled by the requested intensity.
_EMOTION_PITCH_SHIFT: Dict["VoiceEmotion", float] = {}


# Speed multiplier applied per emotion. Values above 1.0 speed the voice up,
# values below 1.0 slow it down.
_EMOTION_SPEED_MULT: Dict["VoiceEmotion", float] = {}


# Maps a vowel character to its canonical viseme label.
_VOWEL_TO_VISEME: Dict[str, str] = {
    "a": "viseme_a",
    "e": "viseme_e",
    "i": "viseme_i",
    "o": "viseme_o",
    "u": "viseme_u",
}


# Scene keyword table used by auto_direct and auto_generate_lines. Each entry
# is (keywords, emotion, pace, intensity). The first matching entry wins.
_SCENE_EMOTION_KEYWORDS: List[Tuple[List[str], "VoiceEmotion", str, float]] = []


# Dialogue templates per emotion used by auto_generate_lines.
_DIALOGUE_TEMPLATES: Dict["VoiceEmotion", List[str]] = {}


# ---------------------------------------------------------------------------
# Domain Enums
# ---------------------------------------------------------------------------


class VoiceGender(str, Enum):
    """Biological gender category of a voice profile."""
    MALE = "male"
    FEMALE = "female"
    NEUTRAL = "neutral"
    ANDROGYNOUS = "androgynous"


class VoiceEmotion(str, Enum):
    """Emotional colour applied to a synthesized voice line."""
    NEUTRAL = "neutral"
    HAPPY = "happy"
    SAD = "sad"
    ANGRY = "angry"
    EXCITED = "excited"
    FEARFUL = "fearful"
    SURPRISED = "surprised"
    DISGUSTED = "disgusted"
    CONFUSED = "confused"
    CALM = "calm"
    WHISPER = "whisper"
    SHOUT = "shout"
    SARCASTIC = "sarcastic"
    TIRED = "tired"
    PROFESSIONAL = "professional"


class VoiceLanguage(str, Enum):
    """Spoken language of a voice profile or synthesized line."""
    EN_US = "en_us"
    EN_GB = "en_gb"
    JA_JP = "ja_jp"
    ZH_CN = "zh_cn"
    KO_KR = "ko_kr"
    ES_ES = "es_es"
    FR_FR = "fr_fr"
    DE_DE = "de_de"
    PT_BR = "pt_br"
    RU_RU = "ru_ru"
    IT_IT = "it_it"
    AR_SA = "ar_sa"
    HI_IN = "hi_in"


class VoiceAgeGroup(str, Enum):
    """Age bracket that shapes the timbre of a voice profile."""
    CHILD = "child"
    TEEN = "teen"
    YOUNG_ADULT = "young_adult"
    ADULT = "adult"
    MIDDLE_AGED = "middle_aged"
    ELDERLY = "elderly"


class VoiceAccent(str, Enum):
    """Regional accent applied to a voice profile."""
    STANDARD = "standard"
    SOUTHERN = "southern"
    BRITISH = "british"
    AUSTRALIAN = "australian"
    SCOTTISH = "scottish"
    IRISH = "irish"
    NEW_YORK = "new_york"
    SOUTHERN_US = "southern_us"
    MIDWESTERN = "midwestern"
    TEXAN = "texan"
    BOSTON = "boston"
    CUSTOM = "custom"


class SynthesisStatus(str, Enum):
    """Lifecycle state of a synthesis line or batch."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class VoiceProfileType(str, Enum):
    """Role a voice profile plays inside the game world."""
    NPC = "npc"
    PLAYER = "player"
    NARRATOR = "narrator"
    ANNOUNCER = "announcer"
    CREATURE = "creature"
    ROBOT = "robot"
    GHOST = "ghost"
    CUSTOM = "custom"


class AudioFormat(str, Enum):
    """Container format of a synthesized audio asset."""
    WAV = "wav"
    MP3 = "mp3"
    OGG = "ogg"
    FLAC = "flac"
    PCM = "pcm"


class VoiceSynthEventKind(str, Enum):
    """Audit event kind recorded on the synthesizer timeline."""
    PROFILE_CREATED = "profile_created"
    PROFILE_UPDATED = "profile_updated"
    PROFILE_REMOVED = "profile_removed"
    LINE_SYNTHESIZED = "line_synthesized"
    BATCH_STARTED = "batch_started"
    BATCH_COMPLETED = "batch_completed"
    VOICE_CLONED = "voice_cloned"
    EMOTION_CHANGED = "emotion_changed"


# Populate the emotion acoustic tables now that the enums exist.
_EMOTION_PITCH_SHIFT = {
    VoiceEmotion.NEUTRAL: 0.0,
    VoiceEmotion.HAPPY: 15.0,
    VoiceEmotion.SAD: -20.0,
    VoiceEmotion.ANGRY: 25.0,
    VoiceEmotion.EXCITED: 30.0,
    VoiceEmotion.FEARFUL: 40.0,
    VoiceEmotion.SURPRISED: 35.0,
    VoiceEmotion.DISGUSTED: -10.0,
    VoiceEmotion.CONFUSED: -5.0,
    VoiceEmotion.CALM: -5.0,
    VoiceEmotion.WHISPER: -15.0,
    VoiceEmotion.SHOUT: 50.0,
    VoiceEmotion.SARCASTIC: 5.0,
    VoiceEmotion.TIRED: -25.0,
    VoiceEmotion.PROFESSIONAL: 0.0,
}

_EMOTION_SPEED_MULT = {
    VoiceEmotion.NEUTRAL: 1.0,
    VoiceEmotion.HAPPY: 1.1,
    VoiceEmotion.SAD: 0.85,
    VoiceEmotion.ANGRY: 1.2,
    VoiceEmotion.EXCITED: 1.25,
    VoiceEmotion.FEARFUL: 1.3,
    VoiceEmotion.SURPRISED: 1.15,
    VoiceEmotion.DISGUSTED: 0.9,
    VoiceEmotion.CONFUSED: 0.95,
    VoiceEmotion.CALM: 0.9,
    VoiceEmotion.WHISPER: 0.8,
    VoiceEmotion.SHOUT: 1.3,
    VoiceEmotion.SARCASTIC: 0.95,
    VoiceEmotion.TIRED: 0.75,
    VoiceEmotion.PROFESSIONAL: 1.0,
}

_SCENE_EMOTION_KEYWORDS = [
    (["battle", "combat", "fight", "war", "attack", "enemy", "sword",
      "blade", "assault"], VoiceEmotion.ANGRY, "fast", 0.8),
    (["charge", "victory", "win", "celebrate", "triumph", "cheer",
      "festival"], VoiceEmotion.EXCITED, "fast", 0.9),
    (["sad", "death", "loss", "grief", "mourn", "tears", "funeral",
      "goodbye"], VoiceEmotion.SAD, "slow", 0.7),
    (["happy", "joy", "laugh", "smile", "cheer", "party",
      "birthday"], VoiceEmotion.HAPPY, "normal", 0.7),
    (["fear", "scared", "dark", "horror", "monster", "terrified",
      "nightmare"], VoiceEmotion.FEARFUL, "slow", 0.8),
    (["surprise", "shock", "unexpected", "amazing",
      "astonish"], VoiceEmotion.SURPRISED, "normal", 0.8),
    (["mystery", "secret", "puzzle", "riddle", "unknown",
      "clue"], VoiceEmotion.CONFUSED, "slow", 0.6),
    (["calm", "peace", "rest", "serene", "tranquil",
      "meditation"], VoiceEmotion.CALM, "slow", 0.4),
    (["whisper", "silent", "stealth", "sneak", "hide",
      "sneaking"], VoiceEmotion.WHISPER, "slow", 0.6),
    (["shout", "yell", "rage", "furious", "scream",
      "roar"], VoiceEmotion.SHOUT, "fast", 0.9),
    (["tired", "exhausted", "weary", "sleepy", "drained",
      "fatigue"], VoiceEmotion.TIRED, "slow", 0.7),
    (["professional", "formal", "business", "official", "report",
      "briefing"], VoiceEmotion.PROFESSIONAL, "normal", 0.5),
    (["disgust", "gross", "revolting", "nausea",
      "foul"], VoiceEmotion.DISGUSTED, "slow", 0.7),
    (["sarcastic", "irony", "mock", "sneer",
      "scorn"], VoiceEmotion.SARCASTIC, "normal", 0.6),
]

_DIALOGUE_TEMPLATES = {
    VoiceEmotion.ANGRY: [
        "You will pay for this!",
        "Stand aside, now!",
        "I have had enough of your tricks.",
        "Draw your blade, coward!",
        "Justice comes for you.",
        "Do not test my patience.",
        "Your lies end here.",
    ],
    VoiceEmotion.EXCITED: [
        "We did it! We actually did it!",
        "This is the best day ever!",
        "I cannot believe our luck!",
        "Onward, to glory!",
        "Hurry, the adventure awaits!",
        "This is going to be legendary!",
    ],
    VoiceEmotion.SAD: [
        "I... I never thought it would end like this.",
        "The memories are all I have left.",
        "Forgive me. I tried my best.",
        "Some burdens are too heavy to carry.",
        "Farewell, my friend.",
        "The light has gone out of this place.",
    ],
    VoiceEmotion.HAPPY: [
        "What a beautiful morning!",
        "The sun could not shine any brighter today.",
        "I am so glad to see you!",
        "Everything is going wonderfully.",
        "Let us celebrate together!",
        "Today is a gift, my friend.",
    ],
    VoiceEmotion.FEARFUL: [
        "Did you hear that? Something is watching us.",
        "I... I do not think we should go in there.",
        "Stay close. The shadows move on their own here.",
        "My hands will not stop shaking.",
        "We are not alone in this place.",
        "Please, let us turn back.",
    ],
    VoiceEmotion.SURPRISED: [
        "Wait, what? How is that even possible?",
        "I never expected to see you here!",
        "That... that changes everything.",
        "You certainly know how to make an entrance.",
        "Well, that was unexpected!",
        "I did not see that coming at all.",
    ],
    VoiceEmotion.CONFUSED: [
        "I... I do not understand. What do you mean?",
        "Something about this place does not add up.",
        "Wait, are you saying the map is wrong?",
        "None of this makes any sense.",
        "Could you explain that again?",
        "I am not sure I follow your reasoning.",
    ],
    VoiceEmotion.CALM: [
        "Take a breath. We have time.",
        "The river sounds peaceful today.",
        "There is no need to rush.",
        "All things come in their own season.",
        "Rest a while. The path will wait.",
        "The world feels still here, does it not?",
    ],
    VoiceEmotion.WHISPER: [
        "Quiet... they will hear us.",
        "Stay low, and follow my lead.",
        "Not a sound, do you understand?",
        "The guards patrol just ahead.",
        "We must move like shadows.",
        "Keep your voice down, friend.",
    ],
    VoiceEmotion.SHOUT: [
        "CHARGE!",
        "EVERYONE, GET BACK!",
        "NOW IS OUR MOMENT!",
        "STAND YOUR GROUND!",
        "FORWARD, TO VICTORY!",
        "HEAR ME, ALL OF YOU!",
    ],
    VoiceEmotion.TIRED: [
        "Can we... can we rest for a moment?",
        "Every step feels heavier than the last.",
        "I just need to catch my breath.",
        "The road has been long today.",
        "I am not as young as I once was.",
        "My legs will not carry me much further.",
    ],
    VoiceEmotion.PROFESSIONAL: [
        "The report confirms our initial assessment.",
        "Per regulations, this requires authorization.",
        "Your request has been logged and processed.",
        "Status update: all systems nominal.",
        "Please proceed according to protocol.",
        "The findings are consistent with expectations.",
    ],
    VoiceEmotion.NEUTRAL: [
        "I see. Tell me more.",
        "That is an interesting perspective.",
        "Let us consider the options.",
        "Very well, proceed.",
        "Understood. What is next?",
        "Go on, I am listening.",
    ],
    VoiceEmotion.DISGUSTED: [
        "Ugh, the stench is unbearable.",
        "I cannot believe you would do such a thing.",
        "This is revolting, beyond words.",
        "Keep that away from me.",
        "Some deeds leave a foul taste.",
        "I have no desire to hear more of this.",
    ],
    VoiceEmotion.SARCASTIC: [
        "Oh, brilliant plan. Truly masterful.",
        "Yes, because that worked so well last time.",
        "By all means, lead the way, hero.",
        "What a stunning surprise. Nobody saw it coming.",
        "Sure, that sounds like a wonderful idea.",
        "How very thoughtful of you, as always.",
    ],
}


# ---------------------------------------------------------------------------
# Data Classes
# ---------------------------------------------------------------------------


@dataclass
class VoiceProfile:
    """A reusable voice profile bound to a character or role."""
    profile_id: str
    name: str
    character_name: str
    gender: str
    age_group: str
    language: str
    accent: str
    profile_type: str
    base_pitch: float = 120.0
    base_speed: float = 1.0
    base_volume: float = 1.0
    pitch_range: float = 50.0
    breathiness: float = 0.0
    roughness: float = 0.0
    resonance: float = 0.5
    sample_url: str = ""
    enabled: bool = True
    tags: List[str] = field(default_factory=list)
    created_at: str = field(default_factory=_now)
    updated_at: str = field(default_factory=_now)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class VoiceLine:
    """A single synthesized speech line with acoustic and viseme data."""
    line_id: str
    profile_id: str
    text: str
    emotion: str
    intensity: float = 0.5
    pitch_override: float = 0.0
    speed_override: float = 0.0
    volume_override: float = 0.0
    duration: float = 0.0
    audio_url: str = ""
    audio_format: str = "wav"
    sample_rate: int = 22050
    language: str = "en_us"
    phonemes: List[str] = field(default_factory=list)
    visemes: List[str] = field(default_factory=list)
    status: str = "pending"
    created_at: str = field(default_factory=_now)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class SynthesisBatch:
    """A batch of synthesis lines processed together."""
    batch_id: str
    name: str
    profile_id: str
    line_ids: List[str] = field(default_factory=list)
    total_lines: int = 0
    completed_lines: int = 0
    failed_lines: int = 0
    status: str = "pending"
    started_at: str = ""
    completed_at: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class VoiceClone:
    """A cloned voice derived from a source profile and sample set."""
    clone_id: str
    source_profile_id: str
    target_name: str
    sample_urls: List[str] = field(default_factory=list)
    sample_duration: float = 0.0
    quality: float = 0.8
    status: str = "pending"
    created_at: str = field(default_factory=_now)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class EmotionPreset:
    """A reusable emotion preset with acoustic multipliers."""
    preset_id: str
    name: str
    emotion: str
    pitch_shift: float = 0.0
    speed_mult: float = 1.0
    volume_mult: float = 1.0
    breathiness_mult: float = 1.0
    roughness_mult: float = 1.0
    color: str = "#FFFFFF"
    description: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class VoiceDirection:
    """A voice direction tied to a scene context and desired emotion."""
    direction_id: str
    profile_id: str
    scene_context: str
    desired_emotion: str
    intensity: float = 0.5
    pace: str = "normal"
    notes: str = ""
    suggested_lines: List[str] = field(default_factory=list)
    created_at: str = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class VoiceSynthConfig:
    """Global tuning parameters for the voice synthesizer."""
    max_profiles: int = 1000
    max_lines: int = 5000
    max_batches: int = 500
    max_clones: int = 200
    max_emotion_presets: int = 500
    max_directions: int = 500
    max_events: int = 8000
    default_language: str = "en_us"
    default_format: str = "wav"
    default_sample_rate: int = 22050
    auto_phonemize: bool = True
    auto_visemes: bool = True
    enable_prosody: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class VoiceSynthStats:
    """Aggregate counters describing synthesizer activity."""
    total_profiles: int = 0
    total_lines: int = 0
    total_batches: int = 0
    total_clones: int = 0
    total_emotion_presets: int = 0
    total_directions: int = 0
    active_batches: int = 0
    total_synthesized: int = 0
    total_failed: int = 0
    avg_duration: float = 0.0
    tick_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class VoiceSynthSnapshot:
    """Full state snapshot for persistence and inspection."""
    timestamp: str = field(default_factory=_now)
    profiles: List[Dict[str, Any]] = field(default_factory=list)
    lines: List[Dict[str, Any]] = field(default_factory=list)
    batches: List[Dict[str, Any]] = field(default_factory=list)
    clones: List[Dict[str, Any]] = field(default_factory=list)
    events: List[Dict[str, Any]] = field(default_factory=list)
    stats: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class VoiceSynthEvent:
    """An audit event recorded on the synthesizer timeline."""
    event_id: str
    timestamp: str
    event_type: str
    profile_id: str = ""
    description: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class PhonemeMap:
    """A language-specific phoneme and viseme set with mapping."""
    language: str
    phoneme_set: List[str] = field(default_factory=list)
    viseme_set: List[str] = field(default_factory=list)
    phoneme_to_viseme: Dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class ProsodyRule:
    """A prosody rule that adjusts pitch, speed, and pauses by condition."""
    rule_id: str
    name: str
    condition: str
    pitch_adjust: float = 0.0
    speed_adjust: float = 0.0
    pause_before: float = 0.0
    pause_after: float = 0.0
    emphasis: float = 1.0

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


# ---------------------------------------------------------------------------
# AI Voice Synthesizer Singleton
# ---------------------------------------------------------------------------


# Module-level lock and singleton holder for double-checked locking.
_lock = threading.RLock()
_instance: Optional["AIVoiceSynthesizer"] = None


class AIVoiceSynthesizer:
    """
    AI-native fusion module that synthesizes spoken voice lines for the
    SparkLabs game engine. The synthesizer owns the voice profile library,
    synthesized line registry, batch lifecycle, voice clones, emotion
    presets, voice directions, phoneme maps, and prosody rules as a single
    coherent state machine.

    Implements a singleton via module-level double-checked locking. All
    mutations to internal state are guarded by an instance lock so the
    synthesizer is safe to call from multiple threads. Seed population is
    guarded by a dedicated init lock so re-entrancy during reset cannot
    double-seed the canonical dataset.

    AI methods (auto_direct, auto_generate_lines, batch_synthesize) use
    deterministic logic driven by scene keyword tables and acoustic
    multipliers so results are reproducible across runs without external
    network calls.
    """

    _init_lock = threading.RLock()

    # ------------------------------------------------------------------
    # Construction and Singleton
    # ------------------------------------------------------------------

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._profiles: Dict[str, VoiceProfile] = {}
        self._lines: Dict[str, VoiceLine] = {}
        self._batches: Dict[str, SynthesisBatch] = {}
        self._clones: Dict[str, VoiceClone] = {}
        self._emotion_presets: Dict[str, EmotionPreset] = {}
        self._directions: Dict[str, VoiceDirection] = {}
        self._phoneme_maps: Dict[str, PhonemeMap] = {}
        self._prosody_rules: Dict[str, ProsodyRule] = {}
        self._events: List[VoiceSynthEvent] = []
        self._config = VoiceSynthConfig()
        self._stats = VoiceSynthStats()
        self._tick_count: int = 0
        self._synth_counter: int = 0
        self._fail_counter: int = 0
        self._duration_accum: float = 0.0
        self._duration_count: int = 0
        self._initialized: bool = False
        self.initialize()

    @classmethod
    def get_instance(cls) -> "AIVoiceSynthesizer":
        global _instance
        if _instance is None:
            with _lock:
                if _instance is None:
                    _instance = cls()
        return _instance

    def initialize(self) -> None:
        """Idempotently initialize and seed the synthesizer."""
        if self._initialized:
            return
        with self._init_lock:
            if self._initialized:
                return
            self._seed()

    # ------------------------------------------------------------------
    # Internal Helpers
    # ------------------------------------------------------------------

    def _emit(self, event_type: str, profile_id: str = "",
              description: str = "",
              data: Optional[Dict[str, Any]] = None) -> None:
        event = VoiceSynthEvent(
            event_id=_new_id("evt"),
            timestamp=_now(),
            event_type=event_type,
            profile_id=profile_id,
            description=description,
            metadata=data or {},
        )
        self._events.append(event)
        _evict_fifo_list(self._events, self._config.max_events)

    def _refresh_stats(self) -> None:
        self._stats.total_profiles = len(self._profiles)
        self._stats.total_lines = len(self._lines)
        self._stats.total_batches = len(self._batches)
        self._stats.total_clones = len(self._clones)
        self._stats.total_emotion_presets = len(self._emotion_presets)
        self._stats.total_directions = len(self._directions)
        self._stats.active_batches = sum(
            1 for b in self._batches.values()
            if b.status in (SynthesisStatus.PENDING.value,
                            SynthesisStatus.PROCESSING.value)
        )
        self._stats.total_synthesized = self._synth_counter
        self._stats.total_failed = self._fail_counter
        if self._duration_count > 0:
            self._stats.avg_duration = round(
                self._duration_accum / self._duration_count, 4
            )
        else:
            self._stats.avg_duration = 0.0
        self._stats.tick_count = self._tick_count

    def _resolve_language(self, language: str,
                          profile: Optional[VoiceProfile] = None) -> str:
        """Resolve a language string falling back to profile then config."""
        if language:
            lang_enum = _coerce_enum(VoiceLanguage, language)
            if lang_enum is not None:
                return lang_enum.value
            return str(language).lower()
        if profile is not None and profile.language:
            return profile.language
        return self._config.default_language

    def _resolve_format(self, audio_format: str) -> str:
        if audio_format:
            fmt_enum = _coerce_enum(AudioFormat, audio_format)
            if fmt_enum is not None:
                return fmt_enum.value
            return str(audio_format).lower()
        return self._config.default_format

    def _compute_duration(self, text: str, profile: VoiceProfile,
                          emotion_enum: VoiceEmotion, intensity: float,
                          speed_override: float) -> float:
        """Estimate line duration from text length, emotion, and speed."""
        char_count = max(1, len(text))
        emotion_mult = _EMOTION_SPEED_MULT.get(emotion_enum, 1.0)
        effective_speed = (profile.base_speed * emotion_mult) + speed_override
        if effective_speed <= 0.05:
            effective_speed = 0.05
        chars_per_second = 14.0 * effective_speed
        duration = char_count / chars_per_second
        if duration < 0.2:
            duration = 0.2
        return round(duration, 3)

    def _generate_phonemes(self, text: str, language: str) -> List[str]:
        """Deterministically derive a phoneme sequence from the input text."""
        if not text:
            return []
        words = [w for w in text.split() if w]
        phonemes: List[str] = []
        vowel_set = set("aeiouAEIOU")
        for word in words:
            clean = "".join(c for c in word if c.isalpha())
            if not clean:
                continue
            for ch in clean:
                if ch in vowel_set:
                    phonemes.append(f"V_{ch.lower()}")
                else:
                    phonemes.append(f"C_{ch.lower()}")
            phonemes.append("PAU")
        if phonemes and phonemes[-1] == "PAU":
            phonemes.pop()
        return phonemes

    def _generate_visemes(self, phonemes: List[str],
                          language: str) -> List[str]:
        """Map a phoneme sequence to a viseme sequence."""
        visemes: List[str] = []
        for ph in phonemes:
            if ph == "PAU":
                visemes.append("viseme_rest")
            elif ph.startswith("V_"):
                vowel = ph[2:]
                visemes.append(_VOWEL_TO_VISEME.get(vowel, "viseme_neutral"))
            else:
                visemes.append("viseme_consonant")
        return visemes

    def _scene_to_emotion(self, scene_context: str) -> Tuple[VoiceEmotion,
                                                             str, float]:
        """Map a scene context string to an emotion, pace, and intensity.

        Returns the first keyword group that matches the lowercased scene
        context. Falls back to a neutral emotion when no keywords match.
        """
        if not scene_context:
            return VoiceEmotion.NEUTRAL, "normal", 0.5
        lowered = scene_context.lower()
        for keywords, emotion, pace, intensity in _SCENE_EMOTION_KEYWORDS:
            for kw in keywords:
                if kw in lowered:
                    return emotion, pace, intensity
        return VoiceEmotion.NEUTRAL, "normal", 0.5

    def _apply_prosody_rules(self, text: str, profile: VoiceProfile,
                             pitch: float, speed: float) -> Tuple[float, float]:
        """Apply matching prosody rules to pitch and speed values."""
        if not self._config.enable_prosody:
            return pitch, speed
        if not text:
            return pitch, speed
        lowered = text.lower()
        for rule in self._prosody_rules.values():
            condition = (rule.condition or "").lower()
            if not condition:
                continue
            if condition in lowered or any(
                token in lowered for token in condition.split()
            ):
                pitch += rule.pitch_adjust
                speed += rule.speed_adjust
        return pitch, speed

    # ------------------------------------------------------------------
    # Profile Management
    # ------------------------------------------------------------------

    def register_profile(self, profile_id, name, character_name="",
                         gender="neutral", age_group="adult",
                         language="en_us", accent="standard",
                         profile_type="npc", base_pitch=120.0,
                         base_speed=1.0, base_volume=1.0, pitch_range=50.0,
                         breathiness=0.0, roughness=0.0, resonance=0.5,
                         sample_url="", enabled=True, tags=None,
                         metadata=None) -> Tuple[bool, str, Optional[VoiceProfile]]:
        """Register a voice profile in the synthesizer library."""
        with self._lock:
            if not profile_id:
                return False, "invalid_profile_id", None
            if profile_id in self._profiles:
                return False, "profile_exists", None
            if len(self._profiles) >= self._config.max_profiles:
                return False, "profiles_capacity", None
            gender_enum = _coerce_enum(VoiceGender, gender, VoiceGender.NEUTRAL)
            age_enum = _coerce_enum(VoiceAgeGroup, age_group, VoiceAgeGroup.ADULT)
            lang_enum = _coerce_enum(VoiceLanguage, language,
                                     VoiceLanguage(self._config.default_language)
                                     if self._config.default_language
                                     else VoiceLanguage.EN_US)
            accent_enum = _coerce_enum(VoiceAccent, accent, VoiceAccent.STANDARD)
            type_enum = _coerce_enum(VoiceProfileType, profile_type,
                                     VoiceProfileType.NPC)
            now = _now()
            profile = VoiceProfile(
                profile_id=profile_id,
                name=name,
                character_name=character_name,
                gender=gender_enum.value,
                age_group=age_enum.value,
                language=lang_enum.value,
                accent=accent_enum.value,
                profile_type=type_enum.value,
                base_pitch=_safe_float(base_pitch, 120.0),
                base_speed=_safe_float(base_speed, 1.0),
                base_volume=_safe_float(base_volume, 1.0),
                pitch_range=_safe_float(pitch_range, 50.0),
                breathiness=_clamp(_safe_float(breathiness, 0.0), 0.0, 1.0),
                roughness=_clamp(_safe_float(roughness, 0.0), 0.0, 1.0),
                resonance=_clamp(_safe_float(resonance, 0.5), 0.0, 1.0),
                sample_url=sample_url or "",
                enabled=bool(enabled),
                tags=list(tags) if tags else [],
                created_at=now,
                updated_at=now,
                metadata=metadata or {},
            )
            self._profiles[profile_id] = profile
            self._emit(
                VoiceSynthEventKind.PROFILE_CREATED.value,
                profile_id=profile_id,
                description=f"Profile '{name}' registered",
                data={"gender": gender_enum.value,
                      "profile_type": type_enum.value,
                      "language": lang_enum.value},
            )
            return True, "registered", profile

    def get_profile(self, profile_id) -> Optional[VoiceProfile]:
        with self._lock:
            return self._profiles.get(profile_id)

    def list_profiles(self, gender=None, language=None, profile_type=None,
                      enabled=None, limit=100) -> List[VoiceProfile]:
        with self._lock:
            items = list(self._profiles.values())
            if gender is not None:
                gender_enum = _coerce_enum(VoiceGender, gender)
                if gender_enum is not None:
                    items = [p for p in items if p.gender == gender_enum.value]
                else:
                    items = [p for p in items if p.gender == gender]
            if language is not None:
                lang_enum = _coerce_enum(VoiceLanguage, language)
                if lang_enum is not None:
                    items = [p for p in items if p.language == lang_enum.value]
                else:
                    items = [p for p in items if p.language == language]
            if profile_type is not None:
                type_enum = _coerce_enum(VoiceProfileType, profile_type)
                if type_enum is not None:
                    items = [p for p in items
                             if p.profile_type == type_enum.value]
                else:
                    items = [p for p in items
                             if p.profile_type == profile_type]
            if enabled is not None:
                items = [p for p in items if p.enabled == bool(enabled)]
            if limit and limit > 0:
                items = items[:limit]
            return items

    def remove_profile(self, profile_id) -> Tuple[bool, str]:
        with self._lock:
            if profile_id not in self._profiles:
                return False, "not_found"
            del self._profiles[profile_id]
            self._emit(
                VoiceSynthEventKind.PROFILE_REMOVED.value,
                profile_id=profile_id,
                description=f"Profile '{profile_id}' removed",
            )
            return True, "removed"

    def update_profile(self, profile_id, **kwargs) -> Tuple[bool, str, Optional[VoiceProfile]]:
        """Apply keyword updates to an existing voice profile."""
        with self._lock:
            profile = self._profiles.get(profile_id)
            if profile is None:
                return False, "not_found", None
            if not kwargs:
                return False, "no_updates", profile
            updatable = {
                "name", "character_name", "base_pitch", "base_speed",
                "base_volume", "pitch_range", "breathiness", "roughness",
                "resonance", "sample_url", "enabled",
            }
            for key, value in kwargs.items():
                if key == "gender":
                    enum_val = _coerce_enum(VoiceGender, value, VoiceGender.NEUTRAL)
                    profile.gender = enum_val.value
                elif key == "age_group":
                    enum_val = _coerce_enum(VoiceAgeGroup, value, VoiceAgeGroup.ADULT)
                    profile.age_group = enum_val.value
                elif key == "language":
                    enum_val = _coerce_enum(VoiceLanguage, value)
                    if enum_val is not None:
                        profile.language = enum_val.value
                elif key == "accent":
                    enum_val = _coerce_enum(VoiceAccent, value, VoiceAccent.STANDARD)
                    profile.accent = enum_val.value
                elif key == "profile_type":
                    enum_val = _coerce_enum(VoiceProfileType, value,
                                            VoiceProfileType.NPC)
                    profile.profile_type = enum_val.value
                elif key == "tags" and isinstance(value, list):
                    profile.tags = list(value)
                elif key == "metadata" and isinstance(value, dict):
                    profile.metadata.update(value)
                elif key in updatable:
                    if key in ("base_pitch", "base_speed", "base_volume",
                               "pitch_range"):
                        setattr(profile, key, _safe_float(value,
                                getattr(profile, key)))
                    elif key in ("breathiness", "roughness", "resonance"):
                        setattr(profile, key, _clamp(
                            _safe_float(value, getattr(profile, key)), 0.0, 1.0))
                    elif key == "enabled":
                        profile.enabled = bool(value)
                    else:
                        setattr(profile, key, value)
            profile.updated_at = _now()
            self._emit(
                VoiceSynthEventKind.PROFILE_UPDATED.value,
                profile_id=profile_id,
                description=f"Profile '{profile_id}' updated",
                data={"keys": list(kwargs.keys())},
            )
            return True, "updated", profile

    # ------------------------------------------------------------------
    # Line Synthesis
    # ------------------------------------------------------------------

    def synthesize_line(self, line_id, profile_id, text,
                        emotion="neutral", intensity=0.5,
                        pitch_override=0.0, speed_override=0.0,
                        volume_override=0.0, language="",
                        audio_format="wav", sample_rate=22050,
                        metadata=None) -> Tuple[bool, str, Optional[VoiceLine]]:
        """Synthesize a single voice line from text."""
        with self._lock:
            if not line_id:
                return False, "invalid_line_id", None
            if line_id in self._lines:
                return False, "line_exists", None
            if len(self._lines) >= self._config.max_lines:
                return False, "lines_capacity", None
            if not text:
                return False, "invalid_text", None
            profile = self._profiles.get(profile_id)
            if profile is None:
                return False, "profile_not_found", None
            if not profile.enabled:
                return False, "profile_disabled", None

            emotion_enum = _coerce_enum(VoiceEmotion, emotion,
                                        VoiceEmotion.NEUTRAL)
            intensity_val = _clamp(_safe_float(intensity, 0.5), 0.0, 1.0)
            pitch_over = _safe_float(pitch_override, 0.0)
            speed_over = _safe_float(speed_override, 0.0)
            volume_over = _safe_float(volume_override, 0.0)
            fmt = self._resolve_format(audio_format)
            lang = self._resolve_language(language, profile)
            rate = _safe_int(sample_rate, self._config.default_sample_rate)
            if rate <= 0:
                rate = self._config.default_sample_rate

            duration = self._compute_duration(
                text, profile, emotion_enum, intensity_val, speed_over
            )

            phonemes: List[str] = []
            visemes: List[str] = []
            if self._config.auto_phonemize:
                phonemes = self._generate_phonemes(text, lang)
            if self._config.auto_visemes:
                visemes = self._generate_visemes(phonemes, lang)

            audio_url = f"audio://{profile_id}/{line_id}.{fmt}"

            line = VoiceLine(
                line_id=line_id,
                profile_id=profile_id,
                text=text,
                emotion=emotion_enum.value,
                intensity=intensity_val,
                pitch_override=pitch_over,
                speed_override=speed_over,
                volume_override=volume_over,
                duration=duration,
                audio_url=audio_url,
                audio_format=fmt,
                sample_rate=rate,
                language=lang,
                phonemes=phonemes,
                visemes=visemes,
                status=SynthesisStatus.COMPLETED.value,
                created_at=_now(),
                metadata=metadata or {},
            )
            self._lines[line_id] = line
            self._synth_counter += 1
            self._duration_accum += duration
            self._duration_count += 1

            self._emit(
                VoiceSynthEventKind.LINE_SYNTHESIZED.value,
                profile_id=profile_id,
                description=f"Line '{line_id}' synthesized",
                data={"line_id": line_id,
                      "emotion": emotion_enum.value,
                      "duration": duration,
                      "phoneme_count": len(phonemes),
                      "viseme_count": len(visemes)},
            )
            return True, "synthesized", line

    def get_line(self, line_id) -> Optional[VoiceLine]:
        with self._lock:
            return self._lines.get(line_id)

    def list_lines(self, profile_id=None, emotion=None, status=None,
                   limit=100) -> List[VoiceLine]:
        with self._lock:
            items = list(self._lines.values())
            if profile_id is not None:
                items = [l for l in items if l.profile_id == profile_id]
            if emotion is not None:
                emotion_enum = _coerce_enum(VoiceEmotion, emotion)
                if emotion_enum is not None:
                    items = [l for l in items if l.emotion == emotion_enum.value]
                else:
                    items = [l for l in items if l.emotion == emotion]
            if status is not None:
                status_enum = _coerce_enum(SynthesisStatus, status)
                if status_enum is not None:
                    items = [l for l in items if l.status == status_enum.value]
                else:
                    items = [l for l in items if l.status == status]
            if limit and limit > 0:
                items = items[-limit:]
            return items

    def remove_line(self, line_id) -> Tuple[bool, str]:
        with self._lock:
            if line_id not in self._lines:
                return False, "not_found"
            del self._lines[line_id]
            # Drop the line from any batch that contained it.
            for batch in self._batches.values():
                if line_id in batch.line_ids:
                    batch.line_ids.remove(line_id)
                    batch.total_lines = len(batch.line_ids)
                    if batch.completed_lines > batch.total_lines:
                        batch.completed_lines = batch.total_lines
            return True, "removed"

    # ------------------------------------------------------------------
    # Batch Management
    # ------------------------------------------------------------------

    def create_batch(self, batch_id, name, profile_id, lines=None,
                     metadata=None) -> Tuple[bool, str, Optional[SynthesisBatch]]:
        """Create a synthesis batch bound to a profile."""
        with self._lock:
            if not batch_id:
                return False, "invalid_batch_id", None
            if batch_id in self._batches:
                return False, "batch_exists", None
            if len(self._batches) >= self._config.max_batches:
                return False, "batches_capacity", None
            if profile_id not in self._profiles:
                return False, "profile_not_found", None
            line_ids = list(lines) if lines else []
            if len(line_ids) > _MAX_LINES_PER_BATCH:
                return False, "too_many_lines", None
            batch = SynthesisBatch(
                batch_id=batch_id,
                name=name,
                profile_id=profile_id,
                line_ids=line_ids,
                total_lines=len(line_ids),
                completed_lines=0,
                failed_lines=0,
                status=SynthesisStatus.PENDING.value,
                started_at="",
                completed_at="",
                metadata=metadata or {},
            )
            self._batches[batch_id] = batch
            self._emit(
                VoiceSynthEventKind.BATCH_STARTED.value,
                profile_id=profile_id,
                description=f"Batch '{batch_id}' created",
                data={"batch_id": batch_id,
                      "total_lines": batch.total_lines},
            )
            return True, "created", batch

    def get_batch(self, batch_id) -> Optional[SynthesisBatch]:
        with self._lock:
            return self._batches.get(batch_id)

    def list_batches(self, profile_id=None, status=None,
                     limit=100) -> List[SynthesisBatch]:
        with self._lock:
            items = list(self._batches.values())
            if profile_id is not None:
                items = [b for b in items if b.profile_id == profile_id]
            if status is not None:
                status_enum = _coerce_enum(SynthesisStatus, status)
                if status_enum is not None:
                    items = [b for b in items if b.status == status_enum.value]
                else:
                    items = [b for b in items if b.status == status]
            if limit and limit > 0:
                items = items[-limit:]
            return items

    def add_line_to_batch(self, batch_id, line_id) -> Tuple[bool, str, Optional[SynthesisBatch]]:
        """Append a line id to an existing batch."""
        with self._lock:
            batch = self._batches.get(batch_id)
            if batch is None:
                return False, "batch_not_found", None
            if line_id not in self._lines:
                return False, "line_not_found", None
            if line_id in batch.line_ids:
                return False, "line_already_in_batch", batch
            if len(batch.line_ids) >= _MAX_LINES_PER_BATCH:
                return False, "too_many_lines", batch
            batch.line_ids.append(line_id)
            batch.total_lines = len(batch.line_ids)
            line = self._lines.get(line_id)
            if line is not None and line.status == SynthesisStatus.COMPLETED.value:
                batch.completed_lines += 1
            elif line is not None and line.status == SynthesisStatus.FAILED.value:
                batch.failed_lines += 1
            return True, "added", batch

    def remove_line_from_batch(self, batch_id, line_id) -> Tuple[bool, str, Optional[SynthesisBatch]]:
        """Remove a line id from an existing batch."""
        with self._lock:
            batch = self._batches.get(batch_id)
            if batch is None:
                return False, "batch_not_found", None
            if line_id not in batch.line_ids:
                return False, "line_not_in_batch", batch
            line = self._lines.get(line_id)
            if line is not None and line.status == SynthesisStatus.COMPLETED.value:
                if batch.completed_lines > 0:
                    batch.completed_lines -= 1
            elif line is not None and line.status == SynthesisStatus.FAILED.value:
                if batch.failed_lines > 0:
                    batch.failed_lines -= 1
            batch.line_ids.remove(line_id)
            batch.total_lines = len(batch.line_ids)
            return True, "removed", batch

    def process_batch(self, batch_id) -> Tuple[bool, str, Optional[SynthesisBatch]]:
        """Process a batch by counting completed and failed lines."""
        with self._lock:
            batch = self._batches.get(batch_id)
            if batch is None:
                return False, "batch_not_found", None
            if batch.status == SynthesisStatus.COMPLETED.value:
                return False, "already_completed", batch
            if not batch.started_at:
                batch.started_at = _now()
            batch.status = SynthesisStatus.PROCESSING.value
            completed = 0
            failed = 0
            for lid in batch.line_ids:
                line = self._lines.get(lid)
                if line is None:
                    failed += 1
                    continue
                if line.status == SynthesisStatus.COMPLETED.value:
                    completed += 1
                elif line.status == SynthesisStatus.FAILED.value:
                    failed += 1
            batch.completed_lines = completed
            batch.failed_lines = failed
            batch.status = SynthesisStatus.COMPLETED.value
            batch.completed_at = _now()
            self._emit(
                VoiceSynthEventKind.BATCH_COMPLETED.value,
                profile_id=batch.profile_id,
                description=f"Batch '{batch_id}' processed",
                data={"batch_id": batch_id,
                      "completed": completed,
                      "failed": failed,
                      "total": batch.total_lines},
            )
            return True, "processed", batch

    def remove_batch(self, batch_id) -> Tuple[bool, str]:
        with self._lock:
            if batch_id not in self._batches:
                return False, "not_found"
            del self._batches[batch_id]
            return True, "removed"

    # ------------------------------------------------------------------
    # Voice Cloning
    # ------------------------------------------------------------------

    def clone_voice(self, clone_id, source_profile_id, target_name,
                    sample_urls=None, sample_duration=0.0, quality=0.8,
                    metadata=None) -> Tuple[bool, str, Optional[VoiceClone]]:
        """Clone a voice from a source profile and sample set."""
        with self._lock:
            if not clone_id:
                return False, "invalid_clone_id", None
            if clone_id in self._clones:
                return False, "clone_exists", None
            if len(self._clones) >= self._config.max_clones:
                return False, "clones_capacity", None
            if source_profile_id not in self._profiles:
                return False, "source_profile_not_found", None
            urls = list(sample_urls) if sample_urls else []
            if not urls:
                return False, "no_samples", None
            sample_dur = _safe_float(sample_duration, 0.0)
            requested_quality = _clamp(_safe_float(quality, 0.8), 0.0, 1.0)
            # Effective quality scales with available sample material. A
            # full 30 seconds of source audio is enough to reach the
            # requested quality ceiling.
            coverage = min(1.0, sample_dur / 30.0) if sample_dur > 0 else 0.5
            effective_quality = round(requested_quality * coverage, 3)
            clone = VoiceClone(
                clone_id=clone_id,
                source_profile_id=source_profile_id,
                target_name=target_name,
                sample_urls=urls,
                sample_duration=sample_dur,
                quality=effective_quality,
                status=SynthesisStatus.COMPLETED.value,
                created_at=_now(),
                metadata=metadata or {},
            )
            self._clones[clone_id] = clone
            self._emit(
                VoiceSynthEventKind.VOICE_CLONED.value,
                profile_id=source_profile_id,
                description=f"Voice cloned as '{target_name}'",
                data={"clone_id": clone_id,
                      "source_profile_id": source_profile_id,
                      "target_name": target_name,
                      "quality": effective_quality,
                      "sample_count": len(urls),
                      "sample_duration": sample_dur},
            )
            return True, "cloned", clone

    def get_clone(self, clone_id) -> Optional[VoiceClone]:
        with self._lock:
            return self._clones.get(clone_id)

    def list_clones(self, source_profile_id=None, status=None,
                    limit=100) -> List[VoiceClone]:
        with self._lock:
            items = list(self._clones.values())
            if source_profile_id is not None:
                items = [c for c in items
                         if c.source_profile_id == source_profile_id]
            if status is not None:
                status_enum = _coerce_enum(SynthesisStatus, status)
                if status_enum is not None:
                    items = [c for c in items if c.status == status_enum.value]
                else:
                    items = [c for c in items if c.status == status]
            if limit and limit > 0:
                items = items[-limit:]
            return items

    def remove_clone(self, clone_id) -> Tuple[bool, str]:
        with self._lock:
            if clone_id not in self._clones:
                return False, "not_found"
            del self._clones[clone_id]
            return True, "removed"

    # ------------------------------------------------------------------
    # Emotion Presets
    # ------------------------------------------------------------------

    def create_emotion_preset(self, preset_id, name, emotion,
                              pitch_shift=0.0, speed_mult=1.0,
                              volume_mult=1.0, breathiness_mult=1.0,
                              roughness_mult=1.0, color="#FFFFFF",
                              description="") -> Tuple[bool, str, Optional[EmotionPreset]]:
        """Create a reusable emotion preset."""
        with self._lock:
            if not preset_id:
                return False, "invalid_preset_id", None
            if preset_id in self._emotion_presets:
                return False, "preset_exists", None
            if len(self._emotion_presets) >= self._config.max_emotion_presets:
                return False, "presets_capacity", None
            emotion_enum = _coerce_enum(VoiceEmotion, emotion,
                                        VoiceEmotion.NEUTRAL)
            preset = EmotionPreset(
                preset_id=preset_id,
                name=name,
                emotion=emotion_enum.value,
                pitch_shift=_safe_float(pitch_shift, 0.0),
                speed_mult=_safe_float(speed_mult, 1.0),
                volume_mult=_safe_float(volume_mult, 1.0),
                breathiness_mult=_safe_float(breathiness_mult, 1.0),
                roughness_mult=_safe_float(roughness_mult, 1.0),
                color=color or "#FFFFFF",
                description=description or "",
            )
            self._emotion_presets[preset_id] = preset
            self._emit(
                VoiceSynthEventKind.EMOTION_CHANGED.value,
                description=f"Emotion preset '{name}' created",
                data={"preset_id": preset_id,
                      "emotion": emotion_enum.value},
            )
            return True, "created", preset

    def get_emotion_preset(self, preset_id) -> Optional[EmotionPreset]:
        with self._lock:
            return self._emotion_presets.get(preset_id)

    def list_emotion_presets(self, emotion=None,
                             limit=100) -> List[EmotionPreset]:
        with self._lock:
            items = list(self._emotion_presets.values())
            if emotion is not None:
                emotion_enum = _coerce_enum(VoiceEmotion, emotion)
                if emotion_enum is not None:
                    items = [p for p in items
                             if p.emotion == emotion_enum.value]
                else:
                    items = [p for p in items if p.emotion == emotion]
            if limit and limit > 0:
                items = items[:limit]
            return items

    def remove_emotion_preset(self, preset_id) -> Tuple[bool, str]:
        with self._lock:
            if preset_id not in self._emotion_presets:
                return False, "not_found"
            del self._emotion_presets[preset_id]
            return True, "removed"

    def apply_emotion(self, profile_id, emotion,
                      intensity=0.5) -> Tuple[bool, str, Optional[VoiceProfile]]:
        """Apply an emotion's acoustic shift to a profile's base parameters."""
        with self._lock:
            profile = self._profiles.get(profile_id)
            if profile is None:
                return False, "profile_not_found", None
            emotion_enum = _coerce_enum(VoiceEmotion, emotion,
                                        VoiceEmotion.NEUTRAL)
            intensity_val = _clamp(_safe_float(intensity, 0.5), 0.0, 1.0)
            pitch_shift = _EMOTION_PITCH_SHIFT.get(emotion_enum, 0.0)
            speed_mult = _EMOTION_SPEED_MULT.get(emotion_enum, 1.0)
            profile.base_pitch = max(
                40.0, profile.base_pitch + (pitch_shift * intensity_val)
            )
            profile.base_speed = max(
                0.25, profile.base_speed * speed_mult
            )
            profile.updated_at = _now()
            self._emit(
                VoiceSynthEventKind.EMOTION_CHANGED.value,
                profile_id=profile_id,
                description=f"Emotion '{emotion_enum.value}' applied",
                data={"emotion": emotion_enum.value,
                      "intensity": intensity_val,
                      "pitch_shift": pitch_shift * intensity_val,
                      "speed_mult": speed_mult},
            )
            return True, "applied", profile

    # ------------------------------------------------------------------
    # Voice Direction
    # ------------------------------------------------------------------

    def create_direction(self, direction_id, profile_id, scene_context,
                         desired_emotion, intensity=0.5, pace="normal",
                         notes="") -> Tuple[bool, str, Optional[VoiceDirection]]:
        """Create a voice direction tied to a scene context."""
        with self._lock:
            if not direction_id:
                return False, "invalid_direction_id", None
            if direction_id in self._directions:
                return False, "direction_exists", None
            if len(self._directions) >= self._config.max_directions:
                return False, "directions_capacity", None
            if profile_id not in self._profiles:
                return False, "profile_not_found", None
            emotion_enum = _coerce_enum(VoiceEmotion, desired_emotion,
                                        VoiceEmotion.NEUTRAL)
            direction = VoiceDirection(
                direction_id=direction_id,
                profile_id=profile_id,
                scene_context=scene_context,
                desired_emotion=emotion_enum.value,
                intensity=_clamp(_safe_float(intensity, 0.5), 0.0, 1.0),
                pace=pace or "normal",
                notes=notes or "",
                suggested_lines=[],
                created_at=_now(),
            )
            self._directions[direction_id] = direction
            return True, "created", direction

    def get_direction(self, direction_id) -> Optional[VoiceDirection]:
        with self._lock:
            return self._directions.get(direction_id)

    def list_directions(self, profile_id=None,
                        limit=100) -> List[VoiceDirection]:
        with self._lock:
            items = list(self._directions.values())
            if profile_id is not None:
                items = [d for d in items if d.profile_id == profile_id]
            if limit and limit > 0:
                items = items[-limit:]
            return items

    def remove_direction(self, direction_id) -> Tuple[bool, str]:
        with self._lock:
            if direction_id not in self._directions:
                return False, "not_found"
            del self._directions[direction_id]
            return True, "removed"

    # ------------------------------------------------------------------
    # Phoneme Maps
    # ------------------------------------------------------------------

    def register_phoneme_map(self, language, phoneme_set=None,
                             viseme_set=None,
                             phoneme_to_viseme=None) -> Tuple[bool, str, Optional[PhonemeMap]]:
        """Register a phoneme and viseme map for a language."""
        with self._lock:
            if not language:
                return False, "invalid_language", None
            lang_enum = _coerce_enum(VoiceLanguage, language)
            lang_value = lang_enum.value if lang_enum is not None else str(language).lower()
            if lang_value in self._phoneme_maps:
                return False, "phoneme_map_exists", None
            if len(self._phoneme_maps) >= _MAX_PHONEME_MAPS:
                return False, "phoneme_maps_capacity", None
            phoneme_map = PhonemeMap(
                language=lang_value,
                phoneme_set=list(phoneme_set) if phoneme_set else [],
                viseme_set=list(viseme_set) if viseme_set else [],
                phoneme_to_viseme=dict(phoneme_to_viseme) if phoneme_to_viseme else {},
            )
            self._phoneme_maps[lang_value] = phoneme_map
            return True, "registered", phoneme_map

    def get_phoneme_map(self, language) -> Optional[PhonemeMap]:
        with self._lock:
            if not language:
                return None
            lang_enum = _coerce_enum(VoiceLanguage, language)
            lang_value = lang_enum.value if lang_enum is not None else str(language).lower()
            return self._phoneme_maps.get(lang_value)

    def list_phoneme_maps(self) -> List[PhonemeMap]:
        with self._lock:
            return list(self._phoneme_maps.values())

    # ------------------------------------------------------------------
    # Prosody Rules
    # ------------------------------------------------------------------

    def register_prosody_rule(self, rule_id, name, condition,
                              pitch_adjust=0.0, speed_adjust=0.0,
                              pause_before=0.0, pause_after=0.0,
                              emphasis=1.0) -> Tuple[bool, str, Optional[ProsodyRule]]:
        """Register a prosody rule for speech shaping."""
        with self._lock:
            if not rule_id:
                return False, "invalid_rule_id", None
            if rule_id in self._prosody_rules:
                return False, "rule_exists", None
            if len(self._prosody_rules) >= _MAX_PROSODY_RULES:
                return False, "rules_capacity", None
            rule = ProsodyRule(
                rule_id=rule_id,
                name=name,
                condition=condition or "",
                pitch_adjust=_safe_float(pitch_adjust, 0.0),
                speed_adjust=_safe_float(speed_adjust, 0.0),
                pause_before=max(0.0, _safe_float(pause_before, 0.0)),
                pause_after=max(0.0, _safe_float(pause_after, 0.0)),
                emphasis=_clamp(_safe_float(emphasis, 1.0), 0.0, 2.0),
            )
            self._prosody_rules[rule_id] = rule
            return True, "registered", rule

    def get_prosody_rule(self, rule_id) -> Optional[ProsodyRule]:
        with self._lock:
            return self._prosody_rules.get(rule_id)

    def list_prosody_rules(self, limit=100) -> List[ProsodyRule]:
        with self._lock:
            items = list(self._prosody_rules.values())
            if limit and limit > 0:
                items = items[:limit]
            return items

    def remove_prosody_rule(self, rule_id) -> Tuple[bool, str]:
        with self._lock:
            if rule_id not in self._prosody_rules:
                return False, "not_found"
            del self._prosody_rules[rule_id]
            return True, "removed"

    # ------------------------------------------------------------------
    # AI Methods
    # ------------------------------------------------------------------

    def auto_direct(self, profile_id,
                    scene_context) -> Tuple[bool, str, Optional[VoiceDirection]]:
        """Analyze a scene context and create a suggested voice direction.

        Uses a deterministic keyword table to map scene context phrases to
        an emotion, pace, and intensity. Suggested dialogue lines are drawn
        from the dialogue template table for the detected emotion.
        """
        with self._lock:
            if profile_id not in self._profiles:
                return False, "profile_not_found", None
            if not scene_context:
                return False, "invalid_scene_context", None
            emotion_enum, pace, intensity = self._scene_to_emotion(scene_context)
            templates = _DIALOGUE_TEMPLATES.get(emotion_enum, [])
            suggested = list(templates[:4])
            direction_id = _new_id("dir")
            direction = VoiceDirection(
                direction_id=direction_id,
                profile_id=profile_id,
                scene_context=scene_context,
                desired_emotion=emotion_enum.value,
                intensity=intensity,
                pace=pace,
                notes=f"Auto-derived from scene keywords. Emotion: {emotion_enum.value}.",
                suggested_lines=suggested,
                created_at=_now(),
            )
            self._directions[direction_id] = direction
            self._emit(
                VoiceSynthEventKind.EMOTION_CHANGED.value,
                profile_id=profile_id,
                description=f"Auto direction '{direction_id}' created",
                data={"scene_context": scene_context,
                      "emotion": emotion_enum.value,
                      "pace": pace,
                      "intensity": intensity},
            )
            return True, "auto_directed", direction

    def auto_generate_lines(self, profile_id, scene_context,
                            count=5) -> Tuple[bool, str, List[VoiceLine]]:
        """Generate dialogue lines for a profile from scene context.

        Selects dialogue templates matching the detected emotion and
        synthesizes each as a completed voice line. Returns the list of
        generated lines.
        """
        with self._lock:
            if profile_id not in self._profiles:
                return False, "profile_not_found", []
            if not scene_context:
                return False, "invalid_scene_context", []
            if count <= 0:
                return False, "invalid_count", []
            emotion_enum, pace, intensity = self._scene_to_emotion(scene_context)
            templates = _DIALOGUE_TEMPLATES.get(emotion_enum, [])
            if not templates:
                templates = _DIALOGUE_TEMPLATES[VoiceEmotion.NEUTRAL]
            desired = min(int(count), len(templates))
            if desired <= 0:
                desired = 1
            generated: List[VoiceLine] = []
            for idx in range(desired):
                text = templates[idx % len(templates)]
                line_id = _new_id("line")
                line = self._synthesize_internal(
                    line_id=line_id,
                    profile_id=profile_id,
                    text=text,
                    emotion_enum=emotion_enum,
                    intensity=intensity,
                    metadata={"auto_generated": True,
                              "scene_context": scene_context,
                              "pace": pace},
                )
                if line is not None:
                    generated.append(line)
            return True, "auto_generated", generated

    def _synthesize_internal(self, line_id, profile_id, text,
                             emotion_enum, intensity,
                             metadata=None) -> Optional[VoiceLine]:
        """Internal synthesis path that assumes the lock is already held."""
        profile = self._profiles.get(profile_id)
        if profile is None:
            return None
        if line_id in self._lines:
            return None
        if len(self._lines) >= self._config.max_lines:
            return None
        intensity_val = _clamp(_safe_float(intensity, 0.5), 0.0, 1.0)
        fmt = self._config.default_format
        lang = profile.language or self._config.default_language
        rate = self._config.default_sample_rate
        duration = self._compute_duration(
            text, profile, emotion_enum, intensity_val, 0.0
        )
        phonemes: List[str] = []
        visemes: List[str] = []
        if self._config.auto_phonemize:
            phonemes = self._generate_phonemes(text, lang)
        if self._config.auto_visemes:
            visemes = self._generate_visemes(phonemes, lang)
        audio_url = f"audio://{profile_id}/{line_id}.{fmt}"
        line = VoiceLine(
            line_id=line_id,
            profile_id=profile_id,
            text=text,
            emotion=emotion_enum.value,
            intensity=intensity_val,
            pitch_override=0.0,
            speed_override=0.0,
            volume_override=0.0,
            duration=duration,
            audio_url=audio_url,
            audio_format=fmt,
            sample_rate=rate,
            language=lang,
            phonemes=phonemes,
            visemes=visemes,
            status=SynthesisStatus.COMPLETED.value,
            created_at=_now(),
            metadata=metadata or {},
        )
        self._lines[line_id] = line
        self._synth_counter += 1
        self._duration_accum += duration
        self._duration_count += 1
        self._emit(
            VoiceSynthEventKind.LINE_SYNTHESIZED.value,
            profile_id=profile_id,
            description=f"Line '{line_id}' synthesized",
            data={"line_id": line_id,
                  "emotion": emotion_enum.value,
                  "duration": duration,
                  "auto": True},
        )
        return line

    def batch_synthesize(self, profile_id, texts,
                         emotion="neutral") -> Tuple[bool, str, Optional[SynthesisBatch]]:
        """Create a batch and synthesize every text line in one call."""
        with self._lock:
            if profile_id not in self._profiles:
                return False, "profile_not_found", None
            if not texts:
                return False, "invalid_texts", None
            text_list = list(texts)
            if len(text_list) > _MAX_LINES_PER_BATCH:
                return False, "too_many_lines", None
            emotion_enum = _coerce_enum(VoiceEmotion, emotion,
                                        VoiceEmotion.NEUTRAL)
            batch_id = _new_id("batch")
            batch = SynthesisBatch(
                batch_id=batch_id,
                name=f"batch_{batch_id}",
                profile_id=profile_id,
                line_ids=[],
                total_lines=len(text_list),
                completed_lines=0,
                failed_lines=0,
                status=SynthesisStatus.PROCESSING.value,
                started_at=_now(),
                completed_at="",
                metadata={"emotion": emotion_enum.value,
                          "auto": True},
            )
            self._batches[batch_id] = batch
            self._emit(
                VoiceSynthEventKind.BATCH_STARTED.value,
                profile_id=profile_id,
                description=f"Batch '{batch_id}' started",
                data={"batch_id": batch_id,
                      "total_lines": batch.total_lines,
                      "emotion": emotion_enum.value},
            )
            for text in text_list:
                if not text:
                    batch.failed_lines += 1
                    continue
                line_id = _new_id("line")
                line = self._synthesize_internal(
                    line_id=line_id,
                    profile_id=profile_id,
                    text=text,
                    emotion_enum=emotion_enum,
                    intensity=0.5,
                    metadata={"batch_id": batch_id,
                              "batch_emotion": emotion_enum.value},
                )
                if line is None:
                    batch.failed_lines += 1
                    self._fail_counter += 1
                else:
                    batch.line_ids.append(line_id)
                    batch.completed_lines += 1
            batch.total_lines = len(text_list)
            batch.status = SynthesisStatus.COMPLETED.value
            batch.completed_at = _now()
            self._emit(
                VoiceSynthEventKind.BATCH_COMPLETED.value,
                profile_id=profile_id,
                description=f"Batch '{batch_id}' completed",
                data={"batch_id": batch_id,
                      "completed": batch.completed_lines,
                      "failed": batch.failed_lines,
                      "total": batch.total_lines},
            )
            return True, "batch_synthesized", batch

    # ------------------------------------------------------------------
    # Observability
    # ------------------------------------------------------------------

    def list_events(self, limit=100) -> List[VoiceSynthEvent]:
        with self._lock:
            items = list(self._events)
            if limit and limit > 0:
                items = items[-limit:]
            return items

    def get_status(self) -> Dict[str, Any]:
        with self._lock:
            self._refresh_stats()
            return {
                "initialized": self._initialized,
                "profiles": len(self._profiles),
                "lines": len(self._lines),
                "batches": len(self._batches),
                "clones": len(self._clones),
                "emotion_presets": len(self._emotion_presets),
                "directions": len(self._directions),
                "phoneme_maps": len(self._phoneme_maps),
                "prosody_rules": len(self._prosody_rules),
                "active_batches": self._stats.active_batches,
                "total_synthesized": self._stats.total_synthesized,
                "total_failed": self._stats.total_failed,
                "events": len(self._events),
                "tick_count": self._tick_count,
            }

    def get_stats(self) -> Dict[str, Any]:
        with self._lock:
            self._refresh_stats()
            return self._stats.to_dict()

    def get_snapshot(self) -> Dict[str, Any]:
        with self._lock:
            self._refresh_stats()
            snapshot = VoiceSynthSnapshot(
                timestamp=_now(),
                profiles=[p.to_dict() for p in list(self._profiles.values())[:50]],
                lines=[l.to_dict() for l in list(self._lines.values())[-100:]],
                batches=[b.to_dict() for b in list(self._batches.values())[-50:]],
                clones=[c.to_dict() for c in list(self._clones.values())[-50:]],
                events=[e.to_dict() for e in self._events[-100:]],
                stats=self._stats.to_dict(),
            )
            return snapshot.to_dict()

    # ------------------------------------------------------------------
    # Config and Tick
    # ------------------------------------------------------------------

    def get_config(self) -> VoiceSynthConfig:
        with self._lock:
            return self._config

    def set_config(self, **kwargs) -> Tuple[bool, str, VoiceSynthConfig]:
        """Apply keyword config updates to the synthesizer."""
        with self._lock:
            if not kwargs:
                return False, "no_updates", self._config
            known = set(self._config.__dataclass_fields__.keys())
            for key, value in kwargs.items():
                if key not in known or key == "metadata":
                    if key == "metadata" and isinstance(value, dict):
                        self._config.metadata.update(value)
                    continue
                if key in ("max_profiles", "max_lines", "max_batches",
                           "max_clones", "max_emotion_presets",
                           "max_directions", "max_events",
                           "default_sample_rate"):
                    setattr(self._config, key,
                            max(1, _safe_int(value, getattr(self._config, key))))
                elif key in ("auto_phonemize", "auto_visemes",
                             "enable_prosody"):
                    setattr(self._config, key, bool(value))
                elif key in ("default_language",):
                    lang_enum = _coerce_enum(VoiceLanguage, value)
                    if lang_enum is not None:
                        self._config.default_language = lang_enum.value
                elif key in ("default_format",):
                    fmt_enum = _coerce_enum(AudioFormat, value)
                    if fmt_enum is not None:
                        self._config.default_format = fmt_enum.value
                else:
                    setattr(self._config, key, value)
            self._emit(
                VoiceSynthEventKind.PROFILE_UPDATED.value,
                description="Config updated",
                data={"keys": list(kwargs.keys())},
            )
            return True, "updated", self._config

    def tick(self, dt=1.0) -> Dict[str, Any]:
        """Advance the synthesizer by one tick, resolving transient states."""
        with self._lock:
            self._tick_count += 1
            lines_completed = 0
            lines_failed = 0
            batches_advanced = 0

            # Resolve any lines still in pending or processing state.
            for line in self._lines.values():
                if line.status in (SynthesisStatus.PENDING.value,
                                   SynthesisStatus.PROCESSING.value):
                    line.status = SynthesisStatus.COMPLETED.value
                    lines_completed += 1
                    self._synth_counter += 1

            # Advance any batch in processing state to completed.
            for batch in self._batches.values():
                if batch.status == SynthesisStatus.PROCESSING.value:
                    completed = 0
                    failed = 0
                    for lid in batch.line_ids:
                        ln = self._lines.get(lid)
                        if ln is None:
                            failed += 1
                        elif ln.status == SynthesisStatus.COMPLETED.value:
                            completed += 1
                        elif ln.status == SynthesisStatus.FAILED.value:
                            failed += 1
                    batch.completed_lines = completed
                    batch.failed_lines = failed
                    batch.status = SynthesisStatus.COMPLETED.value
                    if not batch.completed_at:
                        batch.completed_at = _now()
                    batches_advanced += 1

            self._refresh_stats()
            return {
                "tick": self._tick_count,
                "dt": dt,
                "lines_completed": lines_completed,
                "lines_failed": lines_failed,
                "batches_advanced": batches_advanced,
                "active_batches": self._stats.active_batches,
                "total_lines": self._stats.total_lines,
                "total_profiles": self._stats.total_profiles,
                "total_synthesized": self._stats.total_synthesized,
                "avg_duration": self._stats.avg_duration,
            }

    def reset(self) -> None:
        """Clear all synthesizer state and re-seed the canonical dataset."""
        with self._lock:
            self._profiles.clear()
            self._lines.clear()
            self._batches.clear()
            self._clones.clear()
            self._emotion_presets.clear()
            self._directions.clear()
            self._phoneme_maps.clear()
            self._prosody_rules.clear()
            self._events.clear()
            self._config = VoiceSynthConfig()
            self._stats = VoiceSynthStats()
            self._tick_count = 0
            self._synth_counter = 0
            self._fail_counter = 0
            self._duration_accum = 0.0
            self._duration_count = 0
            self._initialized = False
            self._seed()

    # ------------------------------------------------------------------
    # Seed Data
    # ------------------------------------------------------------------

    def _seed(self) -> None:
        """Populate the synthesizer with a canonical set of voice content."""
        self._seed_profiles()
        self._seed_lines()
        self._seed_batches()
        self._seed_clones()
        self._seed_emotion_presets()
        self._seed_directions()
        self._seed_phoneme_maps()
        self._seed_prosody_rules()
        self._seed_events()
        self._refresh_stats()
        self._initialized = True

    def _seed_profiles(self) -> None:
        """Seed 8 voice profiles spanning narrator, NPC, announcer, creature."""
        profiles = [
            VoiceProfile(
                profile_id="profile_narrator_male",
                name="Narrator Male",
                character_name="The Narrator",
                gender=VoiceGender.MALE.value,
                age_group=VoiceAgeGroup.MIDDLE_AGED.value,
                language=VoiceLanguage.EN_US.value,
                accent=VoiceAccent.BRITISH.value,
                profile_type=VoiceProfileType.NARRATOR.value,
                base_pitch=110.0,
                base_speed=0.95,
                base_volume=0.9,
                pitch_range=40.0,
                breathiness=0.1,
                roughness=0.2,
                resonance=0.6,
                sample_url="samples://narrator_male/base.wav",
                enabled=True,
                tags=["narrator", "male", "story"],
                metadata={"seeded": True, "timbre": "warm"},
            ),
            VoiceProfile(
                profile_id="profile_narrator_female",
                name="Narrator Female",
                character_name="The Narrator",
                gender=VoiceGender.FEMALE.value,
                age_group=VoiceAgeGroup.ADULT.value,
                language=VoiceLanguage.EN_US.value,
                accent=VoiceAccent.STANDARD.value,
                profile_type=VoiceProfileType.NARRATOR.value,
                base_pitch=190.0,
                base_speed=1.0,
                base_volume=0.9,
                pitch_range=45.0,
                breathiness=0.05,
                roughness=0.1,
                resonance=0.65,
                sample_url="samples://narrator_female/base.wav",
                enabled=True,
                tags=["narrator", "female", "story"],
                metadata={"seeded": True, "timbre": "clear"},
            ),
            VoiceProfile(
                profile_id="profile_npc_warrior",
                name="Warrior",
                character_name="Kael Ironhand",
                gender=VoiceGender.MALE.value,
                age_group=VoiceAgeGroup.YOUNG_ADULT.value,
                language=VoiceLanguage.EN_US.value,
                accent=VoiceAccent.SOUTHERN_US.value,
                profile_type=VoiceProfileType.NPC.value,
                base_pitch=95.0,
                base_speed=1.05,
                base_volume=1.0,
                pitch_range=60.0,
                breathiness=0.0,
                roughness=0.4,
                resonance=0.7,
                sample_url="samples://npc_warrior/base.wav",
                enabled=True,
                tags=["npc", "warrior", "male", "combat"],
                metadata={"seeded": True, "faction": "iron_vanguard"},
            ),
            VoiceProfile(
                profile_id="profile_npc_merchant",
                name="Merchant",
                character_name="Vessa Threadgold",
                gender=VoiceGender.FEMALE.value,
                age_group=VoiceAgeGroup.ADULT.value,
                language=VoiceLanguage.EN_US.value,
                accent=VoiceAccent.NEW_YORK.value,
                profile_type=VoiceProfileType.NPC.value,
                base_pitch=210.0,
                base_speed=1.15,
                base_volume=0.95,
                pitch_range=55.0,
                breathiness=0.15,
                roughness=0.05,
                resonance=0.55,
                sample_url="samples://npc_merchant/base.wav",
                enabled=True,
                tags=["npc", "merchant", "female", "trade"],
                metadata={"seeded": True, "shop": "threadgold_goods"},
            ),
            VoiceProfile(
                profile_id="profile_npc_child",
                name="Child",
                character_name="Pip",
                gender=VoiceGender.NEUTRAL.value,
                age_group=VoiceAgeGroup.CHILD.value,
                language=VoiceLanguage.EN_US.value,
                accent=VoiceAccent.STANDARD.value,
                profile_type=VoiceProfileType.NPC.value,
                base_pitch=260.0,
                base_speed=1.2,
                base_volume=0.85,
                pitch_range=70.0,
                breathiness=0.2,
                roughness=0.0,
                resonance=0.4,
                sample_url="samples://npc_child/base.wav",
                enabled=True,
                tags=["npc", "child", "neutral"],
                metadata={"seeded": True, "village": "oakhaven"},
            ),
            VoiceProfile(
                profile_id="profile_announcer",
                name="Announcer",
                character_name="The Arena Announcer",
                gender=VoiceGender.MALE.value,
                age_group=VoiceAgeGroup.ADULT.value,
                language=VoiceLanguage.EN_US.value,
                accent=VoiceAccent.MIDWESTERN.value,
                profile_type=VoiceProfileType.ANNOUNCER.value,
                base_pitch=130.0,
                base_speed=1.1,
                base_volume=1.0,
                pitch_range=50.0,
                breathiness=0.0,
                roughness=0.25,
                resonance=0.75,
                sample_url="samples://announcer/base.wav",
                enabled=True,
                tags=["announcer", "male", "arena"],
                metadata={"seeded": True, "venue": "grand_arena"},
            ),
            VoiceProfile(
                profile_id="profile_creature",
                name="Forest Creature",
                character_name="Garrun",
                gender=VoiceGender.ANDROGYNOUS.value,
                age_group=VoiceAgeGroup.ADULT.value,
                language=VoiceLanguage.EN_US.value,
                accent=VoiceAccent.CUSTOM.value,
                profile_type=VoiceProfileType.CREATURE.value,
                base_pitch=70.0,
                base_speed=0.85,
                base_volume=0.95,
                pitch_range=80.0,
                breathiness=0.3,
                roughness=0.6,
                resonance=0.5,
                sample_url="samples://creature/base.wav",
                enabled=True,
                tags=["creature", "androgynous", "forest"],
                metadata={"seeded": True, "species": "thornback"},
            ),
            VoiceProfile(
                profile_id="profile_ghost",
                name="Ghost",
                character_name="The Pale Witness",
                gender=VoiceGender.FEMALE.value,
                age_group=VoiceAgeGroup.ELDERLY.value,
                language=VoiceLanguage.EN_GB.value,
                accent=VoiceAccent.SCOTTISH.value,
                profile_type=VoiceProfileType.GHOST.value,
                base_pitch=175.0,
                base_speed=0.75,
                base_volume=0.7,
                pitch_range=35.0,
                breathiness=0.5,
                roughness=0.2,
                resonance=0.45,
                sample_url="samples://ghost/base.wav",
                enabled=True,
                tags=["ghost", "female", "supernatural"],
                metadata={"seeded": True, "haunt": "greyhollow"},
            ),
        ]
        for profile in profiles:
            self._profiles[profile.profile_id] = profile

    def _seed_lines(self) -> None:
        """Seed 10 voice lines covering distinct emotions and profiles."""
        line_specs = [
            ("line_narrator_intro_01", "profile_narrator_male",
             "In the age before memory, the land slept beneath a sky of iron.",
             VoiceEmotion.NEUTRAL, 0.4, 0.0, 0.0, 0.0),
            ("line_narrator_intro_02", "profile_narrator_female",
             "But the sleep was never meant to last, and the waking was not gentle.",
             VoiceEmotion.CALM, 0.5, 0.0, -0.1, 0.0),
            ("line_warrior_battle_01", "profile_npc_warrior",
             "For the vanguard! Hold the line, do not break formation!",
             VoiceEmotion.ANGRY, 0.85, 10.0, 0.2, 0.0),
            ("line_warrior_battle_02", "profile_npc_warrior",
             "Stand aside, this foe is mine alone to face.",
             VoiceEmotion.EXCITED, 0.8, 0.0, 0.15, 0.0),
            ("line_merchant_greet_01", "profile_npc_merchant",
             "Welcome, welcome! Step closer, I have just the thing for you.",
             VoiceEmotion.HAPPY, 0.7, 0.0, 0.1, 0.0),
            ("line_merchant_sad_01", "profile_npc_merchant",
             "Business has not been the same since the road closed.",
             VoiceEmotion.SAD, 0.6, -15.0, -0.15, 0.0),
            ("line_child_fear_01", "profile_npc_child",
             "I... I do not want to go down there. It is too dark.",
             VoiceEmotion.FEARFUL, 0.75, 0.0, -0.05, 0.0),
            ("line_announcer_shout_01", "profile_announcer",
             "LADIES AND GENTLEMEN, WELCOME TO THE GRAND ARENA!",
             VoiceEmotion.SHOUT, 0.95, 20.0, 0.25, 0.1),
            ("line_creature_angry_01", "profile_creature",
             "Grrr... leave this place, intruders. Leave or perish.",
             VoiceEmotion.ANGRY, 0.8, -5.0, -0.1, 0.0),
            ("line_ghost_whisper_01", "profile_ghost",
             "You should not have come here. The hollow remembers.",
             VoiceEmotion.WHISPER, 0.65, -10.0, -0.2, -0.1),
        ]
        for (line_id, profile_id, text, emotion, intensity,
             pitch_over, speed_over, vol_over) in line_specs:
            profile = self._profiles.get(profile_id)
            if profile is None:
                continue
            duration = self._compute_duration(
                text, profile, emotion, intensity, speed_over
            )
            lang = profile.language
            phonemes = self._generate_phonemes(text, lang)
            visemes = self._generate_visemes(phonemes, lang)
            fmt = self._config.default_format
            audio_url = f"audio://{profile_id}/{line_id}.{fmt}"
            line = VoiceLine(
                line_id=line_id,
                profile_id=profile_id,
                text=text,
                emotion=emotion.value,
                intensity=intensity,
                pitch_override=pitch_over,
                speed_override=speed_over,
                volume_override=vol_over,
                duration=duration,
                audio_url=audio_url,
                audio_format=fmt,
                sample_rate=self._config.default_sample_rate,
                language=lang,
                phonemes=phonemes,
                visemes=visemes,
                status=SynthesisStatus.COMPLETED.value,
                created_at=_now(),
                metadata={"seeded": True},
            )
            self._lines[line_id] = line
            self._synth_counter += 1
            self._duration_accum += duration
            self._duration_count += 1

    def _seed_batches(self) -> None:
        """Seed 3 synthesis batches grouping seeded lines."""
        batch_specs = [
            ("batch_narrator_intro", "Narrator Introduction",
             "profile_narrator_male",
             ["line_narrator_intro_01"]),
            ("batch_warrior_battle", "Warrior Battle Lines",
             "profile_npc_warrior",
             ["line_warrior_battle_01", "line_warrior_battle_02"]),
            ("batch_market_scene", "Market Scene Dialogue",
             "profile_npc_merchant",
             ["line_merchant_greet_01", "line_merchant_sad_01"]),
        ]
        for batch_id, name, profile_id, line_ids in batch_specs:
            completed = sum(
                1 for lid in line_ids
                if self._lines.get(lid) is not None
                and self._lines[lid].status == SynthesisStatus.COMPLETED.value
            )
            batch = SynthesisBatch(
                batch_id=batch_id,
                name=name,
                profile_id=profile_id,
                line_ids=list(line_ids),
                total_lines=len(line_ids),
                completed_lines=completed,
                failed_lines=0,
                status=SynthesisStatus.COMPLETED.value,
                started_at=_now(),
                completed_at=_now(),
                metadata={"seeded": True},
            )
            self._batches[batch_id] = batch

    def _seed_clones(self) -> None:
        """Seed 2 voice clones derived from existing profiles."""
        clone_specs = [
            ("clone_warrior_alt", "profile_npc_warrior",
             "Kael Ironhand (Alt)", 28.5, 0.85,
             ["samples://npc_warrior/alt_01.wav",
              "samples://npc_warrior/alt_02.wav"]),
            ("clone_merchant_alt", "profile_npc_merchant",
             "Vessa Threadgold (Alt)", 22.0, 0.78,
             ["samples://npc_merchant/alt_01.wav",
              "samples://npc_merchant/alt_02.wav",
              "samples://npc_merchant/alt_03.wav"]),
        ]
        for (clone_id, source_profile_id, target_name, sample_dur,
             requested_quality, urls) in clone_specs:
            coverage = min(1.0, sample_dur / 30.0) if sample_dur > 0 else 0.5
            effective_quality = round(requested_quality * coverage, 3)
            clone = VoiceClone(
                clone_id=clone_id,
                source_profile_id=source_profile_id,
                target_name=target_name,
                sample_urls=list(urls),
                sample_duration=sample_dur,
                quality=effective_quality,
                status=SynthesisStatus.COMPLETED.value,
                created_at=_now(),
                metadata={"seeded": True},
            )
            self._clones[clone_id] = clone

    def _seed_emotion_presets(self) -> None:
        """Seed 8 emotion presets covering the major emotions."""
        presets = [
            EmotionPreset(
                preset_id="preset_neutral",
                name="Neutral",
                emotion=VoiceEmotion.NEUTRAL.value,
                pitch_shift=0.0,
                speed_mult=1.0,
                volume_mult=1.0,
                breathiness_mult=1.0,
                roughness_mult=1.0,
                color="#CCCCCC",
                description="Flat baseline emotion with no modulation.",
            ),
            EmotionPreset(
                preset_id="preset_happy",
                name="Happy",
                emotion=VoiceEmotion.HAPPY.value,
                pitch_shift=15.0,
                speed_mult=1.1,
                volume_mult=1.05,
                breathiness_mult=1.1,
                roughness_mult=0.8,
                color="#FFE066",
                description="Bright, lifted delivery for joyful moments.",
            ),
            EmotionPreset(
                preset_id="preset_sad",
                name="Sad",
                emotion=VoiceEmotion.SAD.value,
                pitch_shift=-20.0,
                speed_mult=0.85,
                volume_mult=0.9,
                breathiness_mult=1.3,
                roughness_mult=1.1,
                color="#6C8EAD",
                description="Low, slow, breathy delivery for grief.",
            ),
            EmotionPreset(
                preset_id="preset_angry",
                name="Angry",
                emotion=VoiceEmotion.ANGRY.value,
                pitch_shift=25.0,
                speed_mult=1.2,
                volume_mult=1.15,
                breathiness_mult=0.6,
                roughness_mult=1.4,
                color="#E74C3C",
                description="Hard, fast, forceful delivery for conflict.",
            ),
            EmotionPreset(
                preset_id="preset_excited",
                name="Excited",
                emotion=VoiceEmotion.EXCITED.value,
                pitch_shift=30.0,
                speed_mult=1.25,
                volume_mult=1.1,
                breathiness_mult=1.0,
                roughness_mult=0.9,
                color="#F39C12",
                description="Energetic, high-pitched delivery for triumph.",
            ),
            EmotionPreset(
                preset_id="preset_fearful",
                name="Fearful",
                emotion=VoiceEmotion.FEARFUL.value,
                pitch_shift=40.0,
                speed_mult=1.3,
                volume_mult=0.85,
                breathiness_mult=1.5,
                roughness_mult=1.2,
                color="#8E44AD",
                description="Trembling, breathy delivery for dread.",
            ),
            EmotionPreset(
                preset_id="preset_calm",
                name="Calm",
                emotion=VoiceEmotion.CALM.value,
                pitch_shift=-5.0,
                speed_mult=0.9,
                volume_mult=0.95,
                breathiness_mult=1.2,
                roughness_mult=0.7,
                color="#A3E4D7",
                description="Soft, steady delivery for peace.",
            ),
            EmotionPreset(
                preset_id="preset_whisper",
                name="Whisper",
                emotion=VoiceEmotion.WHISPER.value,
                pitch_shift=-15.0,
                speed_mult=0.8,
                volume_mult=0.5,
                breathiness_mult=2.0,
                roughness_mult=0.5,
                color="#D5DBDB",
                description="Hushed, breathy delivery for secrecy.",
            ),
        ]
        for preset in presets:
            self._emotion_presets[preset.preset_id] = preset

    def _seed_directions(self) -> None:
        """Seed 4 voice directions tied to scene contexts."""
        directions = [
            VoiceDirection(
                direction_id="direction_warrior_battle",
                profile_id="profile_npc_warrior",
                scene_context="The warrior enters a fierce battle against invading forces.",
                desired_emotion=VoiceEmotion.ANGRY.value,
                intensity=0.85,
                pace="fast",
                notes="Channel aggression; keep delivery hard and urgent.",
                suggested_lines=[
                    "For the vanguard!",
                    "Hold the line!",
                    "No retreat, no surrender!",
                    "Drive them back!",
                ],
                created_at=_now(),
            ),
            VoiceDirection(
                direction_id="direction_merchant_market",
                profile_id="profile_npc_merchant",
                scene_context="A bustling market scene with cheerful customers browsing wares.",
                desired_emotion=VoiceEmotion.HAPPY.value,
                intensity=0.7,
                pace="normal",
                notes="Warm and inviting; pitch the sales pitch lightly.",
                suggested_lines=[
                    "Welcome, friend!",
                    "Step right up!",
                    "Fresh goods today!",
                    "A bargain just for you!",
                ],
                created_at=_now(),
            ),
            VoiceDirection(
                direction_id="direction_ghost_haunt",
                profile_id="profile_ghost",
                scene_context="A haunted hall where the ghost whispers of old tragedies.",
                desired_emotion=VoiceEmotion.WHISPER.value,
                intensity=0.65,
                pace="slow",
                notes="Breathy and distant; let pauses linger.",
                suggested_lines=[
                    "You should not be here.",
                    "The hollow remembers.",
                    "Leave while you can.",
                    "We are all that remains.",
                ],
                created_at=_now(),
            ),
            VoiceDirection(
                direction_id="direction_narrator_intro",
                profile_id="profile_narrator_male",
                scene_context="The opening narration establishing the world and its history.",
                desired_emotion=VoiceEmotion.NEUTRAL.value,
                intensity=0.4,
                pace="normal",
                notes="Measured and authoritative; avoid melodrama.",
                suggested_lines=[
                    "In the age before memory...",
                    "The land slept beneath a sky of iron.",
                    "But the sleep was never meant to last.",
                    "And the waking was not gentle.",
                ],
                created_at=_now(),
            ),
        ]
        for direction in directions:
            self._directions[direction.direction_id] = direction

    def _seed_phoneme_maps(self) -> None:
        """Seed 4 phoneme maps for English, Japanese, Chinese, Korean."""
        en_us = PhonemeMap(
            language=VoiceLanguage.EN_US.value,
            phoneme_set=["V_a", "V_e", "V_i", "V_o", "V_u",
                         "C_b", "C_c", "C_d", "C_f", "C_g", "C_h",
                         "C_j", "C_k", "C_l", "C_m", "C_n", "C_p",
                         "C_r", "C_s", "C_t", "C_v", "C_w", "C_y", "C_z",
                         "PAU"],
            viseme_set=["viseme_a", "viseme_e", "viseme_i", "viseme_o",
                        "viseme_u", "viseme_consonant", "viseme_rest"],
            phoneme_to_viseme={
                "V_a": "viseme_a", "V_e": "viseme_e", "V_i": "viseme_i",
                "V_o": "viseme_o", "V_u": "viseme_u", "PAU": "viseme_rest",
            },
        )
        ja_jp = PhonemeMap(
            language=VoiceLanguage.JA_JP.value,
            phoneme_set=["V_a", "V_i", "V_u", "V_e", "V_o",
                         "C_k", "C_s", "C_t", "C_n", "C_h", "C_m", "C_y",
                         "C_r", "C_w", "C_g", "C_z", "C_d", "C_b", "C_p",
                         "PAU"],
            viseme_set=["viseme_a", "viseme_i", "viseme_u", "viseme_e",
                        "viseme_o", "viseme_consonant", "viseme_rest"],
            phoneme_to_viseme={
                "V_a": "viseme_a", "V_i": "viseme_i", "V_u": "viseme_u",
                "V_e": "viseme_e", "V_o": "viseme_o", "PAU": "viseme_rest",
            },
        )
        zh_cn = PhonemeMap(
            language=VoiceLanguage.ZH_CN.value,
            phoneme_set=["V_a", "V_o", "V_e", "V_i", "V_u", "V_v",
                         "C_b", "C_p", "C_m", "C_f", "C_d", "C_t", "C_n",
                         "C_l", "C_g", "C_k", "C_h", "C_j", "C_q", "C_x",
                         "C_zh", "C_ch", "C_sh", "C_r", "C_z", "C_c", "C_s",
                         "C_y", "C_w",
                         "PAU"],
            viseme_set=["viseme_a", "viseme_o", "viseme_e", "viseme_i",
                        "viseme_u", "viseme_v", "viseme_consonant",
                        "viseme_rest"],
            phoneme_to_viseme={
                "V_a": "viseme_a", "V_o": "viseme_o", "V_e": "viseme_e",
                "V_i": "viseme_i", "V_u": "viseme_u", "V_v": "viseme_v",
                "PAU": "viseme_rest",
            },
        )
        ko_kr = PhonemeMap(
            language=VoiceLanguage.KO_KR.value,
            phoneme_set=["V_a", "V_e", "V_o", "V_u", "V_i", "V_ae",
                         "C_g", "C_k", "C_n", "C_d", "C_t", "C_l", "C_m",
                         "C_b", "C_p", "C_s", "C_j", "C_ch", "C_h",
                         "PAU"],
            viseme_set=["viseme_a", "viseme_e", "viseme_o", "viseme_u",
                        "viseme_i", "viseme_ae", "viseme_consonant",
                        "viseme_rest"],
            phoneme_to_viseme={
                "V_a": "viseme_a", "V_e": "viseme_e", "V_o": "viseme_o",
                "V_u": "viseme_u", "V_i": "viseme_i", "V_ae": "viseme_ae",
                "PAU": "viseme_rest",
            },
        )
        for phoneme_map in (en_us, ja_jp, zh_cn, ko_kr):
            self._phoneme_maps[phoneme_map.language] = phoneme_map

    def _seed_prosody_rules(self) -> None:
        """Seed 5 prosody rules for common speech shaping patterns."""
        rules = [
            ProsodyRule(
                rule_id="rule_question_rise",
                name="Question Rise",
                condition="?",
                pitch_adjust=20.0,
                speed_adjust=0.0,
                pause_before=0.0,
                pause_after=0.15,
                emphasis=1.1,
            ),
            ProsodyRule(
                rule_id="rule_exclamation_force",
                name="Exclamation Force",
                condition="!",
                pitch_adjust=15.0,
                speed_adjust=0.1,
                pause_before=0.0,
                pause_after=0.2,
                emphasis=1.3,
            ),
            ProsodyRule(
                rule_id="rule_pause_comma",
                name="Comma Pause",
                condition=",",
                pitch_adjust=-5.0,
                speed_adjust=-0.05,
                pause_before=0.0,
                pause_after=0.12,
                emphasis=0.9,
            ),
            ProsodyRule(
                rule_id="rule_sentence_end",
                name="Sentence End Drop",
                condition=".",
                pitch_adjust=-15.0,
                speed_adjust=-0.1,
                pause_before=0.0,
                pause_after=0.3,
                emphasis=0.85,
            ),
            ProsodyRule(
                rule_id="rule_ellipsis_trail",
                name="Ellipsis Trail",
                condition="...",
                pitch_adjust=-10.0,
                speed_adjust=-0.15,
                pause_before=0.1,
                pause_after=0.4,
                emphasis=0.7,
            ),
        ]
        for rule in rules:
            self._prosody_rules[rule.rule_id] = rule

    def _seed_events(self) -> None:
        """Seed 6 audit events marking the initial dataset population."""
        events = [
            VoiceSynthEvent(
                event_id="evt_seed_profiles",
                timestamp=_now(),
                event_type=VoiceSynthEventKind.PROFILE_CREATED.value,
                profile_id="profile_narrator_male",
                description="Seeded 8 voice profiles",
                metadata={"seeded": True, "count": 8},
            ),
            VoiceSynthEvent(
                event_id="evt_seed_lines",
                timestamp=_now(),
                event_type=VoiceSynthEventKind.LINE_SYNTHESIZED.value,
                profile_id="profile_narrator_male",
                description="Seeded 10 voice lines",
                metadata={"seeded": True, "count": 10},
            ),
            VoiceSynthEvent(
                event_id="evt_seed_batches",
                timestamp=_now(),
                event_type=VoiceSynthEventKind.BATCH_COMPLETED.value,
                profile_id="profile_npc_warrior",
                description="Seeded 3 synthesis batches",
                metadata={"seeded": True, "count": 3},
            ),
            VoiceSynthEvent(
                event_id="evt_seed_clones",
                timestamp=_now(),
                event_type=VoiceSynthEventKind.VOICE_CLONED.value,
                profile_id="profile_npc_warrior",
                description="Seeded 2 voice clones",
                metadata={"seeded": True, "count": 2},
            ),
            VoiceSynthEvent(
                event_id="evt_seed_presets",
                timestamp=_now(),
                event_type=VoiceSynthEventKind.EMOTION_CHANGED.value,
                description="Seeded 8 emotion presets",
                metadata={"seeded": True, "count": 8},
            ),
            VoiceSynthEvent(
                event_id="evt_seed_directions",
                timestamp=_now(),
                event_type=VoiceSynthEventKind.PROFILE_UPDATED.value,
                profile_id="profile_npc_warrior",
                description="Seeded 4 voice directions",
                metadata={"seeded": True, "count": 4},
            ),
        ]
        for event in events:
            self._events.append(event)


# ---------------------------------------------------------------------------
# Module-Level Factory
# ---------------------------------------------------------------------------


def get_ai_voice_synthesizer() -> AIVoiceSynthesizer:
    """Factory function returning the singleton AIVoiceSynthesizer instance."""
    return AIVoiceSynthesizer.get_instance()


__all__ = [
    # Enums
    "VoiceGender",
    "VoiceEmotion",
    "VoiceLanguage",
    "VoiceAgeGroup",
    "VoiceAccent",
    "SynthesisStatus",
    "VoiceProfileType",
    "AudioFormat",
    "VoiceSynthEventKind",
    # Data classes
    "VoiceProfile",
    "VoiceLine",
    "SynthesisBatch",
    "VoiceClone",
    "EmotionPreset",
    "VoiceDirection",
    "VoiceSynthConfig",
    "VoiceSynthStats",
    "VoiceSynthSnapshot",
    "VoiceSynthEvent",
    "PhonemeMap",
    "ProsodyRule",
    # Main system class
    "AIVoiceSynthesizer",
    # Factory
    "get_ai_voice_synthesizer",
]
