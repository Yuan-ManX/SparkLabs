"""
SparkLabs Engine - Player Avatar System

AI-native player avatar customization engine for the SparkLabs game platform.
The system lets players assemble richly customizable avatars from modular
parts, apply curated outfits, drive idle and emotive animations, strike
poses, save reusable presets, and share their creations across social and
export channels. A procedural thumbnail generator produces deterministic
preview imagery so avatars can be rendered without a live GPU pipeline.

Architecture:
  PlayerAvatarSystem (singleton)
    |-- AvatarPart, AvatarOutfit, PlayerAvatar, AvatarAnimation, AvatarPose,
        AvatarPreset, AvatarShareLink, AvatarSystemConfig, AvatarSystemStats,
        AvatarSystemSnapshot, AvatarSystemEvent
    |-- AvatarPartType, AvatarCategory, AnimationType, PoseType, RarityTier,
        ColorScheme, AvatarStatus, SharePlatform

Core Capabilities:
  - register_part / get_part / list_parts / update_part / remove_part: manage
    the catalog of modular avatar components (heads, hair, bodies, accessories,
    backgrounds, frames, effects) with rarity, color scheme, and unlock rules.
  - create_outfit / get_outfit / list_outfits / update_outfit / remove_outfit:
    curate named bundles of parts that players can apply in a single step.
  - create_avatar / get_avatar / list_avatars / update_avatar / remove_avatar:
    assemble and maintain per-player avatars with parts, outfit, animation,
    pose, background, frame, status, and metadata.
  - register_animation / get_animation / list_animations / remove_animation:
    maintain the library of avatar animations (idle, wave, dance, jump, etc.).
  - register_pose / get_pose / list_poses / remove_pose: maintain static pose
    definitions with bone data for skeletal rendering.
  - create_preset / get_preset / list_presets / apply_preset / remove_preset:
    save reusable avatar configurations and instantiate avatars from them.
  - set_avatar_part / remove_avatar_part / set_avatar_animation /
    set_avatar_pose: fine-grained avatar mutation endpoints.
  - share_avatar / get_share_link / list_share_links / revoke_share: create
    expiring share links for social media, image export, video export, embed,
    and internal channels.
  - feature_avatar / unfeature_avatar: promote or demote avatars to featured
    status for community showcases.
  - generate_thumbnail: produce a deterministic procedural thumbnail for an
    avatar without requiring a rendering backend.
  - list_events / get_status / get_stats / get_snapshot / get_config /
    set_config / tick / reset: observability, tuning, and lifecycle control.
"""

from __future__ import annotations

import math
import threading
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Capacity Constants
# ---------------------------------------------------------------------------

_MAX_AVATARS: int = 10000
_MAX_PARTS: int = 5000
_MAX_OUTFITS: int = 2000
_MAX_ANIMATIONS: int = 1000
_MAX_POSES: int = 500
_MAX_PRESETS: int = 2000
_MAX_SHARE_LINKS: int = 20000
_MAX_AVATARS_PER_PLAYER: int = 50
_MAX_EVENTS: int = 10000

# Thumbnail dimensions (square grid)
_THUMBNAIL_SIZE: int = 24

# Base URL for generated share links
_SHARE_URL_BASE: str = "https://sparklabs.game/avatar/share/"

# Default share-link lifetime in seconds (7 days)
_DEFAULT_SHARE_TTL: int = 7 * 24 * 60 * 60

# Rarity weight used by the procedural thumbnail palette mixer
_RARITY_WEIGHTS: Dict[str, float] = {
    "common": 1.0,
    "uncommon": 1.5,
    "rare": 2.0,
    "epic": 3.0,
    "legendary": 4.0,
    "mythic": 5.0,
}

# Status values that count as "active" for stats roll-ups
_ACTIVE_STATUSES = ("saved", "published", "featured")


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
    if value < low:
        return low
    if value > high:
        return high
    return value


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None:
            return default
        f = float(value)
        if math.isnan(f) or math.isinf(f):
            return default
        return f
    except (TypeError, ValueError):
        return default


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        if value is None:
            return default
        return int(value)
    except (TypeError, ValueError):
        return default


def _parse_iso(ts: str) -> Optional[datetime]:
    if not ts:
        return None
    try:
        cleaned = ts.rstrip("Z")
        return datetime.fromisoformat(cleaned)
    except (ValueError, TypeError):
        return None


def _hex_to_rgb(hex_color: str) -> Tuple[int, int, int]:
    """Convert a #RRGGBB hex string to an (r, g, b) tuple."""
    if not hex_color:
        return (128, 128, 128)
    c = hex_color.lstrip("#")
    if len(c) == 3:
        c = "".join(ch * 2 for ch in c)
    if len(c) != 6:
        return (128, 128, 128)
    try:
        return (int(c[0:2], 16), int(c[2:4], 16), int(c[4:6], 16))
    except (ValueError, IndexError):
        return (128, 128, 128)


def _rgb_to_hex(r: int, g: int, b: int) -> str:
    r = max(0, min(255, int(r)))
    g = max(0, min(255, int(g)))
    b = max(0, min(255, int(b)))
    return f"#{r:02X}{g:02X}{b:02X}"


def _mix_hex_colors(colors: List[str], weights: Optional[List[float]] = None) -> str:
    """Blend a list of hex colors into a single hex color.

    Optional weights scale each color's contribution. When omitted, all
    colors contribute equally.
    """
    if not colors:
        return "#808080"
    if weights is None:
        weights = [1.0] * len(colors)
    total_w = sum(weights)
    if total_w <= 0:
        return colors[0]
    r_sum = 0.0
    g_sum = 0.0
    b_sum = 0.0
    for color, w in zip(colors, weights):
        r, g, b = _hex_to_rgb(color)
        r_sum += r * w
        g_sum += g * w
        b_sum += b * w
    return _rgb_to_hex(
        r_sum / total_w,
        g_sum / total_w,
        b_sum / total_w,
    )


def _hash_str(s: str) -> int:
    """Deterministic 32-bit hash for procedural generation."""
    h = 0
    for ch in s:
        h = (h * 31 + ord(ch)) & 0xFFFFFFFF
    return h


def _lerp(a: float, b: float, t: float) -> float:
    return a + (b - a) * _clamp(t, 0.0, 1.0)


# ---------------------------------------------------------------------------
# Domain Enums
# ---------------------------------------------------------------------------

class AvatarPartType(str, Enum):
    """Categories of modular components that compose an avatar."""
    HEAD = "head"
    FACE = "face"
    HAIR = "hair"
    BODY = "body"
    ARMS = "arms"
    LEGS = "legs"
    HANDS = "hands"
    FEET = "feet"
    ACCESSORY = "accessory"
    BACKGROUND = "background"
    FRAME = "frame"
    EFFECT = "effect"


class AvatarCategory(str, Enum):
    """Thematic family an avatar part or outfit belongs to."""
    HUMAN = "human"
    FANTASY = "fantasy"
    ROBOT = "robot"
    ANIMAL = "animal"
    MONSTER = "monster"
    ABSTRACT = "abstract"
    PIXEL = "pixel"
    MINIMALIST = "minimalist"


class AnimationType(str, Enum):
    """Types of animations that can drive an avatar's movement."""
    IDLE = "idle"
    WAVE = "wave"
    DANCE = "dance"
    JUMP = "jump"
    CELEBRATE = "celebrate"
    THINK = "think"
    WAVE_2 = "wave_2"
    BOW = "bow"
    LAUGH = "laugh"
    CUSTOM = "custom"


class PoseType(str, Enum):
    """Static poses an avatar can hold."""
    STANDING = "standing"
    SITTING = "sitting"
    RUNNING = "running"
    JUMPING = "jumping"
    FLYING = "flying"
    FIGHTING = "fighting"
    RELAXING = "relaxing"
    CUSTOM = "custom"


class RarityTier(str, Enum):
    """Rarity levels that gate availability and visual prestige."""
    COMMON = "common"
    UNCOMMON = "uncommon"
    RARE = "rare"
    EPIC = "epic"
    LEGENDARY = "legendary"
    MYTHIC = "mythic"


class ColorScheme(str, Enum):
    """Color palette families for parts and outfits."""
    WARM = "warm"
    COOL = "cool"
    MONOCHROME = "monochrome"
    VIBRANT = "vibrant"
    PASTEL = "pastel"
    NEON = "neon"
    EARTH = "earth"
    RAINBOW = "rainbow"


class AvatarStatus(str, Enum):
    """Lifecycle status of a player avatar."""
    DRAFT = "draft"
    SAVED = "saved"
    PUBLISHED = "published"
    FEATURED = "featured"
    ARCHIVED = "archived"


class SharePlatform(str, Enum):
    """Distribution channels for avatar share links."""
    INTERNAL = "internal"
    SOCIAL_MEDIA = "social_media"
    EXPORT_IMAGE = "export_image"
    EXPORT_VIDEO = "export_video"
    EMBED = "embed"


# ---------------------------------------------------------------------------
# Data Classes
# ---------------------------------------------------------------------------

@dataclass
class AvatarPart:
    """A modular component that can be slotted into an avatar.

    Each part has a type (head, face, hair, body, etc.), a thematic category,
    a rarity tier, a color scheme, optional mesh and texture URLs, a primary
    color, and unlock gating. Parts are the atomic building blocks of outfits
    and avatars.
    """
    part_id: str
    name: str
    part_type: AvatarPartType
    category: AvatarCategory
    rarity: RarityTier
    color_scheme: ColorScheme
    mesh_url: str = ""
    texture_url: str = ""
    color_hex: str = "#808080"
    is_default: bool = False
    is_unlockable: bool = False
    unlock_condition: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class AvatarOutfit:
    """A named bundle of avatar parts that can be applied as a set.

    Outfits group parts into coherent looks (e.g., "Knight Regalia") so
    players can switch styles in a single operation rather than swapping
    parts individually.
    """
    outfit_id: str
    name: str
    description: str
    part_ids: List[str] = field(default_factory=list)
    category: AvatarCategory = AvatarCategory.HUMAN
    rarity: RarityTier = RarityTier.COMMON
    is_featured: bool = False
    created_at: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class PlayerAvatar:
    """A fully assembled player avatar.

    Combines a set of parts (keyed by part type), an optional outfit, a
    driving animation, a pose, a background color, a frame, and a lifecycle
    status. Avatars are owned by players and can be shared socially.
    """
    avatar_id: str
    player_id: str
    name: str
    parts: Dict[str, str] = field(default_factory=dict)
    outfit_id: str = ""
    animation: str = ""
    pose: str = ""
    background_color: str = "#1A1A2E"
    frame_id: str = ""
    status: AvatarStatus = AvatarStatus.DRAFT
    created_at: str = ""
    updated_at: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class AvatarAnimation:
    """A playable animation definition for avatars.

    Includes the animation type, duration, loop flag, and a frame list that
    describes key poses over time. Animations drive idle, emote, and action
    sequences.
    """
    animation_id: str
    name: str
    type: AnimationType
    duration: float = 1.0
    loop: bool = False
    frames: List[Dict[str, Any]] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class AvatarPose:
    """A static pose definition with skeletal bone data.

    Bone data is a dictionary mapping bone names to transforms (position,
    rotation, scale) that a skeletal renderer can consume directly.
    """
    pose_id: str
    name: str
    type: PoseType
    bone_data: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class AvatarPreset:
    """A reusable avatar configuration template.

    Stores a full avatar config (parts, colors, animation, pose, etc.) so
    players can quickly spawn new avatars from a saved starting point.
    Usage count tracks how many avatars have been created from this preset.
    """
    preset_id: str
    name: str
    description: str
    avatar_config: Dict[str, Any] = field(default_factory=dict)
    category: AvatarCategory = AvatarCategory.HUMAN
    is_featured: bool = False
    usage_count: int = 0
    created_at: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class AvatarShareLink:
    """An expiring share link for distributing an avatar.

    Tracks the target platform, a public URL, an expiry timestamp, and a
    view count so the system can measure reach and revoke stale links.
    """
    share_id: str
    avatar_id: str
    platform: SharePlatform
    url: str
    expires_at: str = ""
    view_count: int = 0
    created_at: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class AvatarSystemConfig:
    """Tunable configuration for the avatar system."""
    max_avatars: int = 10000
    max_parts_per_avatar: int = 50
    max_presets: int = 2000
    default_animation: str = "anim_idle_01"
    auto_generate_thumbnail: bool = True
    enable_sharing: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class AvatarSystemStats:
    """Roll-up statistics maintained across the system's lifetime."""
    total_avatars: int = 0
    total_parts: int = 0
    total_outfits: int = 0
    total_presets: int = 0
    total_shares: int = 0
    active_avatars: int = 0
    tick_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class AvatarSystemSnapshot:
    """A point-in-time snapshot of the system's full state."""
    timestamp: str
    avatars: List[Dict[str, Any]] = field(default_factory=list)
    parts: List[Dict[str, Any]] = field(default_factory=list)
    outfits: List[Dict[str, Any]] = field(default_factory=list)
    presets: List[Dict[str, Any]] = field(default_factory=list)
    stats: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class AvatarSystemEvent:
    """An internal audit event emitted by the avatar system."""
    event_id: str
    timestamp: str
    event_type: str
    avatar_id: str = ""
    description: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


# ---------------------------------------------------------------------------
# Main System - Player Avatar System (Singleton)
# ---------------------------------------------------------------------------

class PlayerAvatarSystem:
    """AI-native player avatar customization engine.

    The system maintains a catalog of avatar parts, outfits, animations,
    poses, presets, share links, and player avatars. It is thread-safe and
    implemented as a singleton with double-checked locking. The _init_lock
    guards singleton creation; _lock guards all mutating operations to keep
    internal dictionaries consistent.
    """

    _instance: Optional["PlayerAvatarSystem"] = None
    _init_lock = threading.RLock()

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._initialized: bool = False
        self._parts: Dict[str, AvatarPart] = {}
        self._outfits: Dict[str, AvatarOutfit] = {}
        self._avatars: Dict[str, PlayerAvatar] = {}
        self._player_avatars: Dict[str, List[str]] = {}
        self._animations: Dict[str, AvatarAnimation] = {}
        self._poses: Dict[str, AvatarPose] = {}
        self._presets: Dict[str, AvatarPreset] = {}
        self._share_links: Dict[str, AvatarShareLink] = {}
        self._avatar_shares: Dict[str, List[str]] = {}
        self._events: List[AvatarSystemEvent] = []
        self._config = AvatarSystemConfig()
        self._stats = AvatarSystemStats()
        self._tick_count: int = 0

    @classmethod
    def get_instance(cls) -> "PlayerAvatarSystem":
        if cls._instance is None:
            with cls._init_lock:
                if cls._instance is None:
                    cls._instance = cls()
        cls._instance.initialize()
        return cls._instance

    def _seed(self) -> None:
        """Populate the system with a canonical set of avatar data."""
        with self._lock:
            if self._initialized:
                return

            base_time = datetime.utcnow()

            # --------------------------------------------------------------
            # Avatar Parts (15)
            # --------------------------------------------------------------
            part_seeds: List[Tuple[str, str, AvatarPartType, AvatarCategory,
                                   RarityTier, ColorScheme, str, str, str,
                                   bool, bool, str, Dict[str, Any]]] = [
                ("part_head_human_01", "Human Head Base", AvatarPartType.HEAD,
                 AvatarCategory.HUMAN, RarityTier.COMMON, ColorScheme.WARM,
                 "mesh://parts/head_human_01.glb",
                 "tex://parts/head_human_01.png",
                 "#F5D5B8", True, False, "", {"slot": "head_base"}),
                ("part_face_eyes_blue_01", "Blue Eyes", AvatarPartType.FACE,
                 AvatarCategory.HUMAN, RarityTier.COMMON, ColorScheme.COOL,
                 "mesh://parts/face_eyes_blue_01.glb",
                 "tex://parts/face_eyes_blue_01.png",
                 "#4A90D9", True, False, "", {"slot": "face_eyes"}),
                ("part_hair_short_01", "Short Hair", AvatarPartType.HAIR,
                 AvatarCategory.HUMAN, RarityTier.COMMON, ColorScheme.WARM,
                 "mesh://parts/hair_short_01.glb",
                 "tex://parts/hair_short_01.png",
                 "#6B4226", True, False, "", {"slot": "hair_top"}),
                ("part_hair_long_01", "Long Flowing Hair", AvatarPartType.HAIR,
                 AvatarCategory.HUMAN, RarityTier.UNCOMMON, ColorScheme.WARM,
                 "mesh://parts/hair_long_01.glb",
                 "tex://parts/hair_long_01.png",
                 "#8B4513", False, True, "reach_level_5",
                 {"slot": "hair_top", "physics": True}),
                ("part_body_armor_01", "Steel Armor", AvatarPartType.BODY,
                 AvatarCategory.FANTASY, RarityTier.RARE, ColorScheme.COOL,
                 "mesh://parts/body_armor_01.glb",
                 "tex://parts/body_armor_01.png",
                 "#708090", False, True, "complete_tutorial",
                 {"slot": "body_torso", "defense": 15}),
                ("part_body_robe_01", "Mage Robe", AvatarPartType.BODY,
                 AvatarCategory.FANTASY, RarityTier.UNCOMMON, ColorScheme.VIBRANT,
                 "mesh://parts/body_robe_01.glb",
                 "tex://parts/body_robe_01.png",
                 "#4B0082", False, True, "reach_level_3",
                 {"slot": "body_torso", "magic": 10}),
                ("part_arms_plate_01", "Plate Arms", AvatarPartType.ARMS,
                 AvatarCategory.FANTASY, RarityTier.RARE, ColorScheme.COOL,
                 "mesh://parts/arms_plate_01.glb",
                 "tex://parts/arms_plate_01.png",
                 "#778899", False, True, "complete_tutorial",
                 {"slot": "arms"}),
                ("part_legs_pants_01", "Travel Pants", AvatarPartType.LEGS,
                 AvatarCategory.HUMAN, RarityTier.COMMON, ColorScheme.EARTH,
                 "mesh://parts/legs_pants_01.glb",
                 "tex://parts/legs_pants_01.png",
                 "#556B2F", True, False, "", {"slot": "legs"}),
                ("part_hands_gloves_01", "Leather Gloves", AvatarPartType.HANDS,
                 AvatarCategory.HUMAN, RarityTier.COMMON, ColorScheme.EARTH,
                 "mesh://parts/hands_gloves_01.glb",
                 "tex://parts/hands_gloves_01.png",
                 "#8B4513", True, False, "", {"slot": "hands"}),
                ("part_feet_boots_01", "Adventure Boots", AvatarPartType.FEET,
                 AvatarCategory.HUMAN, RarityTier.COMMON, ColorScheme.EARTH,
                 "mesh://parts/feet_boots_01.glb",
                 "tex://parts/feet_boots_01.png",
                 "#654321", True, False, "", {"slot": "feet"}),
                ("part_accessory_crown_01", "Golden Crown", AvatarPartType.ACCESSORY,
                 AvatarCategory.FANTASY, RarityTier.LEGENDARY, ColorScheme.WARM,
                 "mesh://parts/acc_crown_01.glb",
                 "tex://parts/acc_crown_01.png",
                 "#FFD700", False, True, "win_season_rank_1",
                 {"slot": "accessory_head", "prestige": 100}),
                ("part_bg_sunset_01", "Sunset Backdrop", AvatarPartType.BACKGROUND,
                 AvatarCategory.ABSTRACT, RarityTier.UNCOMMON, ColorScheme.WARM,
                 "", "tex://parts/bg_sunset_01.png",
                 "#FF7F50", False, True, "reach_level_10",
                 {"slot": "background"}),
                ("part_frame_gold_01", "Gilded Frame", AvatarPartType.FRAME,
                 AvatarCategory.MINIMALIST, RarityTier.EPIC, ColorScheme.WARM,
                 "", "tex://parts/frame_gold_01.png",
                 "#DAA520", False, True, "collect_50_achievements",
                 {"slot": "frame"}),
                ("part_effect_sparkle_01", "Sparkle Aura", AvatarPartType.EFFECT,
                 AvatarCategory.FANTASY, RarityTier.EPIC, ColorScheme.VIBRANT,
                 "mesh://parts/eff_sparkle_01.glb",
                 "tex://parts/eff_sparkle_01.png",
                 "#FF69B4", False, True, "complete_event_holiday",
                 {"slot": "effect_aura", "particles": 120}),
                ("part_head_robot_01", "Robot Visor Head", AvatarPartType.HEAD,
                 AvatarCategory.ROBOT, RarityTier.UNCOMMON, ColorScheme.NEON,
                 "mesh://parts/head_robot_01.glb",
                 "tex://parts/head_robot_01.png",
                 "#00CED1", False, True, "unlock_robot_faction",
                 {"slot": "head_base", "glow": True}),
            ]
            for (pid, name, ptype, cat, rar, cs, mesh, tex, color,
                 is_def, is_unlock, unlock_cond, meta) in part_seeds:
                self._parts[pid] = AvatarPart(
                    part_id=pid, name=name, part_type=ptype, category=cat,
                    rarity=rar, color_scheme=cs, mesh_url=mesh,
                    texture_url=tex, color_hex=color, is_default=is_def,
                    is_unlockable=is_unlock, unlock_condition=unlock_cond,
                    metadata=dict(meta, seed=True),
                )

            # --------------------------------------------------------------
            # Avatar Outfits (6)
            # --------------------------------------------------------------
            outfit_seeds: List[Tuple[str, str, str, List[str], AvatarCategory,
                                     RarityTier, bool, Dict[str, Any]]] = [
                ("outfit_knight_01", "Knight Regalia",
                 "A polished steel ensemble for the noble warrior.",
                 ["part_body_armor_01", "part_arms_plate_01",
                  "part_hands_gloves_01", "part_feet_boots_01"],
                 AvatarCategory.FANTASY, RarityTier.RARE, True,
                 {"theme": "medieval", "set_bonus": "defense"}),
                ("outfit_mage_01", "Arcane Scholar",
                 "Flowing robes imbued with dormant magical resonance.",
                 ["part_body_robe_01", "part_hands_gloves_01"],
                 AvatarCategory.FANTASY, RarityTier.UNCOMMON, False,
                 {"theme": "medieval", "set_bonus": "magic"}),
                ("outfit_adventurer_01", "Wandering Adventurer",
                 "Practical gear for long journeys across the realm.",
                 ["part_body_robe_01", "part_legs_pants_01",
                  "part_hands_gloves_01", "part_feet_boots_01"],
                 AvatarCategory.HUMAN, RarityTier.COMMON, False,
                 {"theme": "travel", "set_bonus": "stamina"}),
                ("outfit_royal_01", "Royal Attire",
                 "Regal vestments befitting true nobility.",
                 ["part_body_armor_01", "part_accessory_crown_01",
                  "part_frame_gold_01"],
                 AvatarCategory.FANTASY, RarityTier.LEGENDARY, True,
                 {"theme": "royal", "set_bonus": "prestige"}),
                ("outfit_cyber_01", "Cyber Pioneer",
                 "Sleek robotic plating with neon accent lighting.",
                 ["part_head_robot_01", "part_body_robe_01"],
                 AvatarCategory.ROBOT, RarityTier.UNCOMMON, False,
                 {"theme": "sci-fi", "set_bonus": "tech"}),
                ("outfit_default_01", "Default Citizen",
                 "The standard starting look for new players.",
                 ["part_head_human_01", "part_hair_short_01",
                  "part_legs_pants_01", "part_feet_boots_01"],
                 AvatarCategory.HUMAN, RarityTier.COMMON, False,
                 {"theme": "starter", "set_bonus": "none"}),
            ]
            for oid, name, desc, pids, cat, rar, featured, meta in outfit_seeds:
                self._outfits[oid] = AvatarOutfit(
                    outfit_id=oid, name=name, description=desc, part_ids=list(pids),
                    category=cat, rarity=rar, is_featured=featured,
                    created_at=_now(), metadata=dict(meta, seed=True),
                )

            # --------------------------------------------------------------
            # Avatar Animations (6)
            # --------------------------------------------------------------
            anim_seeds: List[Tuple[str, str, AnimationType, float, bool,
                                    List[Dict[str, Any]], Dict[str, Any]]] = [
                ("anim_idle_01", "Idle Bob", AnimationType.IDLE, 2.0, True,
                 [{"t": 0.0, "y": 0.0}, {"t": 1.0, "y": 0.02},
                  {"t": 2.0, "y": 0.0}],
                 {"fps": 30}),
                ("anim_wave_01", "Friendly Wave", AnimationType.WAVE, 1.5, False,
                 [{"t": 0.0, "arm_r": 0.0}, {"t": 0.5, "arm_r": 1.2},
                  {"t": 1.0, "arm_r": 0.8}, {"t": 1.5, "arm_r": 0.0}],
                 {"fps": 30}),
                ("anim_dance_01", "Victory Dance", AnimationType.DANCE, 4.0, True,
                 [{"t": 0.0, "pose": "start"}, {"t": 1.0, "pose": "spin"},
                  {"t": 2.0, "pose": "jump"}, {"t": 3.0, "pose": "land"},
                  {"t": 4.0, "pose": "start"}],
                 {"fps": 30, "music_sync": True}),
                ("anim_jump_01", "Jump", AnimationType.JUMP, 0.8, False,
                 [{"t": 0.0, "y": 0.0}, {"t": 0.2, "y": 0.5},
                  {"t": 0.4, "y": 1.0}, {"t": 0.6, "y": 0.5},
                  {"t": 0.8, "y": 0.0}],
                 {"fps": 30}),
                ("anim_celebrate_01", "Celebration", AnimationType.CELEBRATE,
                 3.0, False,
                 [{"t": 0.0, "arms": 0.0}, {"t": 0.5, "arms": 1.5},
                  {"t": 1.5, "arms": 1.5}, {"t": 3.0, "arms": 0.0}],
                 {"fps": 30}),
                ("anim_think_01", "Pondering", AnimationType.THINK, 2.5, True,
                 [{"t": 0.0, "hand_chin": 0.0},
                  {"t": 1.0, "hand_chin": 1.0},
                  {"t": 2.5, "hand_chin": 1.0}],
                 {"fps": 30}),
            ]
            for aid, name, atype, dur, loop, frames, meta in anim_seeds:
                self._animations[aid] = AvatarAnimation(
                    animation_id=aid, name=name, type=atype, duration=dur,
                    loop=loop, frames=list(frames), metadata=dict(meta, seed=True),
                )

            # --------------------------------------------------------------
            # Avatar Poses (5)
            # --------------------------------------------------------------
            pose_seeds: List[Tuple[str, str, PoseType, Dict[str, Any],
                                   Dict[str, Any]]] = [
                ("pose_standing_01", "Standing Tall", PoseType.STANDING,
                 {"spine": {"rot_z": 0.0}, "arms": {"rot_z": 0.0},
                  "legs": {"rot_z": 0.0}},
                 {"biped": True}),
                ("pose_sitting_01", "Cross-Legged Sit", PoseType.SITTING,
                 {"spine": {"rot_z": 0.0}, "legs": {"rot_z": -90.0},
                  "arms": {"rot_z": 15.0}},
                 {"biped": True}),
                ("pose_running_01", "Sprint", PoseType.RUNNING,
                 {"spine": {"rot_z": 15.0}, "arms": {"rot_z": 45.0},
                  "legs": {"rot_z": 30.0}},
                 {"biped": True, "motion_blur": True}),
                ("pose_jumping_01", "Mid-Air Leap", PoseType.JUMPING,
                 {"spine": {"rot_z": -10.0}, "arms": {"rot_z": 120.0},
                  "legs": {"rot_z": 60.0}},
                 {"biped": True}),
                ("pose_relaxing_01", "Lean Back", PoseType.RELAXING,
                 {"spine": {"rot_z": -15.0}, "arms": {"rot_z": -30.0},
                  "legs": {"rot_z": 10.0}},
                 {"biped": True}),
            ]
            for pid, name, ptype, bones, meta in pose_seeds:
                self._poses[pid] = AvatarPose(
                    pose_id=pid, name=name, type=ptype, bone_data=dict(bones),
                    metadata=dict(meta, seed=True),
                )

            # --------------------------------------------------------------
            # Player Avatars (8)
            # --------------------------------------------------------------
            avatar_seeds: List[Tuple[str, str, str, Dict[str, str], str,
                                     str, str, str, str, AvatarStatus,
                                     Dict[str, Any]]] = [
                ("avatar_p001_01", "player_001", "Sir Gallant",
                 {"head": "part_head_human_01", "face": "part_face_eyes_blue_01",
                  "hair": "part_hair_short_01", "body": "part_body_armor_01",
                  "arms": "part_arms_plate_01", "hands": "part_hands_gloves_01",
                  "legs": "part_legs_pants_01", "feet": "part_feet_boots_01"},
                 "outfit_knight_01", "anim_idle_01", "pose_standing_01",
                 "#1A1A2E", "", AvatarStatus.PUBLISHED,
                 {"level": 42, "class": "knight"}),
                ("avatar_p002_01", "player_002", "Mystic Elara",
                 {"head": "part_head_human_01", "face": "part_face_eyes_blue_01",
                  "hair": "part_hair_long_01", "body": "part_body_robe_01",
                  "hands": "part_hands_gloves_01", "legs": "part_legs_pants_01",
                  "feet": "part_feet_boots_01"},
                 "outfit_mage_01", "anim_think_01", "pose_standing_01",
                 "#0F0F23", "", AvatarStatus.SAVED,
                 {"level": 28, "class": "mage"}),
                ("avatar_p003_01", "player_003", "Wanderer Kai",
                 {"head": "part_head_human_01", "face": "part_face_eyes_blue_01",
                  "hair": "part_hair_short_01", "body": "part_body_robe_01",
                  "hands": "part_hands_gloves_01", "legs": "part_legs_pants_01",
                  "feet": "part_feet_boots_01"},
                 "outfit_adventurer_01", "anim_idle_01", "pose_running_01",
                 "#2D1B4E", "", AvatarStatus.PUBLISHED,
                 {"level": 19, "class": "ranger"}),
                ("avatar_p004_01", "player_004", "Queen Aurelia",
                 {"head": "part_head_human_01", "face": "part_face_eyes_blue_01",
                  "hair": "part_hair_long_01", "body": "part_body_armor_01",
                  "accessory": "part_accessory_crown_01",
                  "frame": "part_frame_gold_01", "effect": "part_effect_sparkle_01",
                  "hands": "part_hands_gloves_01", "feet": "part_feet_boots_01"},
                 "outfit_royal_01", "anim_celebrate_01", "pose_standing_01",
                 "#1A0F2E", "part_frame_gold_01", AvatarStatus.FEATURED,
                 {"level": 60, "class": "royal", "title": "Season Champion"}),
                ("avatar_p005_01", "player_005", "Unit-7",
                 {"head": "part_head_robot_01", "body": "part_body_robe_01",
                  "hands": "part_hands_gloves_01", "legs": "part_legs_pants_01",
                  "feet": "part_feet_boots_01"},
                 "outfit_cyber_01", "anim_idle_01", "pose_standing_01",
                 "#0D1117", "", AvatarStatus.DRAFT,
                 {"level": 12, "class": "engineer"}),
                ("avatar_p006_01", "player_006", "Brave Lyra",
                 {"head": "part_head_human_01", "face": "part_face_eyes_blue_01",
                  "hair": "part_hair_short_01", "body": "part_body_armor_01",
                  "arms": "part_arms_plate_01", "hands": "part_hands_gloves_01",
                  "legs": "part_legs_pants_01", "feet": "part_feet_boots_01",
                  "background": "part_bg_sunset_01"},
                 "outfit_knight_01", "anim_wave_01", "pose_standing_01",
                 "#FF7F50", "", AvatarStatus.PUBLISHED,
                 {"level": 35, "class": "knight"}),
                ("avatar_p002_02", "player_002", "Elara Festive",
                 {"head": "part_head_human_01", "face": "part_face_eyes_blue_01",
                  "hair": "part_hair_long_01", "body": "part_body_robe_01",
                  "effect": "part_effect_sparkle_01",
                  "hands": "part_hands_gloves_01", "feet": "part_feet_boots_01"},
                 "", "anim_dance_01", "pose_relaxing_01",
                 "#2D1B4E", "", AvatarStatus.SAVED,
                 {"level": 28, "class": "mage", "variant": "festive"}),
                ("avatar_p007_01", "player_007", "Nova Sage",
                 {"head": "part_head_human_01", "face": "part_face_eyes_blue_01",
                  "hair": "part_hair_long_01", "body": "part_body_robe_01",
                  "hands": "part_hands_gloves_01", "legs": "part_legs_pants_01",
                  "feet": "part_feet_boots_01",
                  "background": "part_bg_sunset_01"},
                 "outfit_mage_01", "anim_think_01", "pose_sitting_01",
                 "#1A1A2E", "", AvatarStatus.PUBLISHED,
                 {"level": 47, "class": "sage"}),
            ]
            for (aid, pid, name, parts, outfit, anim, pose, bg, frame,
                 status, meta) in avatar_seeds:
                ts = (base_time - timedelta(hours=len(avatar_seeds))).isoformat() + "Z"
                self._avatars[aid] = PlayerAvatar(
                    avatar_id=aid, player_id=pid, name=name,
                    parts=dict(parts), outfit_id=outfit, animation=anim,
                    pose=pose, background_color=bg, frame_id=frame,
                    status=status, created_at=ts, updated_at=ts,
                    metadata=dict(meta, seed=True),
                )
                self._player_avatars.setdefault(pid, []).append(aid)

            # --------------------------------------------------------------
            # Avatar Presets (5)
            # --------------------------------------------------------------
            preset_seeds: List[Tuple[str, str, str, Dict[str, Any],
                                     AvatarCategory, bool, int, Dict[str, Any]]] = [
                ("preset_warrior_01", "Warrior", "A sturdy melee fighter preset.",
                 {"parts": {"head": "part_head_human_01",
                            "body": "part_body_armor_01",
                            "arms": "part_arms_plate_01",
                            "hands": "part_hands_gloves_01",
                            "legs": "part_legs_pants_01",
                            "feet": "part_feet_boots_01"},
                  "animation": "anim_idle_01", "pose": "pose_standing_01",
                  "background_color": "#1A1A2E"},
                 AvatarCategory.HUMAN, True, 142,
                 {"tags": ["melee", "tank"]}),
                ("preset_mage_01", "Mage", "An arcane spellcaster preset.",
                 {"parts": {"head": "part_head_human_01",
                            "hair": "part_hair_long_01",
                            "body": "part_body_robe_01",
                            "hands": "part_hands_gloves_01",
                            "legs": "part_legs_pants_01",
                            "feet": "part_feet_boots_01"},
                  "animation": "anim_think_01", "pose": "pose_standing_01",
                  "background_color": "#0F0F23"},
                 AvatarCategory.FANTASY, False, 87,
                 {"tags": ["magic", "caster"]}),
                ("preset_explorer_01", "Explorer", "A rugged traveler preset.",
                 {"parts": {"head": "part_head_human_01",
                            "hair": "part_hair_short_01",
                            "body": "part_body_robe_01",
                            "hands": "part_hands_gloves_01",
                            "legs": "part_legs_pants_01",
                            "feet": "part_feet_boots_01"},
                  "animation": "anim_idle_01", "pose": "pose_running_01",
                  "background_color": "#2D1B4E"},
                 AvatarCategory.HUMAN, False, 53,
                 {"tags": ["travel", "ranger"]}),
                ("preset_celebrity_01", "Celebrity",
                 "A glamorous showpiece preset for featured profiles.",
                 {"parts": {"head": "part_head_human_01",
                            "hair": "part_hair_long_01",
                            "body": "part_body_armor_01",
                            "accessory": "part_accessory_crown_01",
                            "effect": "part_effect_sparkle_01",
                            "frame": "part_frame_gold_01"},
                  "animation": "anim_celebrate_01", "pose": "pose_standing_01",
                  "background_color": "#1A0F2E"},
                 AvatarCategory.FANTASY, True, 31,
                 {"tags": ["featured", "showcase"]}),
                ("preset_minimalist_01", "Minimalist",
                 "A clean understated preset for a focused look.",
                 {"parts": {"head": "part_head_human_01",
                            "face": "part_face_eyes_blue_01",
                            "body": "part_body_robe_01",
                            "legs": "part_legs_pants_01"},
                  "animation": "anim_idle_01", "pose": "pose_relaxing_01",
                  "background_color": "#1A1A2E"},
                 AvatarCategory.MINIMALIST, False, 19,
                 {"tags": ["clean", "simple"]}),
            ]
            for pid, name, desc, config, cat, featured, usage, meta in preset_seeds:
                self._presets[pid] = AvatarPreset(
                    preset_id=pid, name=name, description=desc,
                    avatar_config=dict(config), category=cat,
                    is_featured=featured, usage_count=usage,
                    created_at=_now(), metadata=dict(meta, seed=True),
                )

            # --------------------------------------------------------------
            # Share Links (4)
            # --------------------------------------------------------------
            share_seeds: List[Tuple[str, str, SharePlatform, int, int,
                                    Dict[str, Any]]] = [
                ("share_001", "avatar_p001_01", SharePlatform.INTERNAL,
                 120, 42, {"note": "internal showcase link"}),
                ("share_002", "avatar_p004_01", SharePlatform.SOCIAL_MEDIA,
                 5000, 1840, {"note": "season champion feature"}),
                ("share_003", "avatar_p002_01", SharePlatform.EXPORT_IMAGE,
                 300, 156, {"format": "png", "resolution": "1024x1024"}),
                ("share_004", "avatar_p006_01", SharePlatform.EMBED,
                 800, 73, {"embed_width": 480, "embed_height": 640}),
            ]
            for sid, aid, platform, ttl_offset, views, meta in share_seeds:
                created = base_time - timedelta(seconds=ttl_offset)
                expires = base_time + timedelta(days=7)
                self._share_links[sid] = AvatarShareLink(
                    share_id=sid, avatar_id=aid, platform=platform,
                    url=f"{_SHARE_URL_BASE}{sid}",
                    expires_at=expires.isoformat() + "Z",
                    view_count=views,
                    created_at=created.isoformat() + "Z",
                    metadata=dict(meta, seed=True),
                )
                self._avatar_shares.setdefault(aid, []).append(sid)

            # --------------------------------------------------------------
            # Events (5)
            # --------------------------------------------------------------
            self._emit("system_seeded", avatar_id="",
                       description="Avatar system initialized with canonical data",
                       data={"parts": len(self._parts),
                             "outfits": len(self._outfits),
                             "avatars": len(self._avatars),
                             "animations": len(self._animations),
                             "poses": len(self._poses),
                             "presets": len(self._presets),
                             "share_links": len(self._share_links)})
            self._emit("avatar_created", avatar_id="avatar_p001_01",
                       description="Sir Gallant created by player_001",
                       data={"player_id": "player_001"})
            self._emit("avatar_featured", avatar_id="avatar_p004_01",
                       description="Queen Aurelia promoted to featured status",
                       data={"player_id": "player_004"})
            self._emit("share_created", avatar_id="avatar_p004_01",
                       description="Social media share link generated",
                       data={"share_id": "share_002",
                             "platform": "social_media"})
            self._emit("preset_applied", avatar_id="avatar_p006_01",
                       description="Warrior preset applied to create Brave Lyra",
                       data={"preset_id": "preset_warrior_01",
                             "player_id": "player_006"})

            self._refresh_stats()
            self._initialized = True

    def initialize(self) -> None:
        """Explicitly initialize the system if it has not been seeded yet."""
        if self._initialized:
            return
        with self._lock:
            if self._initialized:
                return
            self._seed()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _emit(
        self,
        event_type: str,
        avatar_id: str = "",
        description: str = "",
        data: Optional[Dict[str, Any]] = None,
    ) -> None:
        event = AvatarSystemEvent(
            event_id=_new_id("evt"),
            timestamp=_now(),
            event_type=event_type,
            avatar_id=avatar_id,
            description=description,
            metadata=data or {},
        )
        self._events.append(event)
        _evict_fifo_list(self._events, _MAX_EVENTS)

    def _refresh_stats(self) -> None:
        self._stats.total_avatars = len(self._avatars)
        self._stats.total_parts = len(self._parts)
        self._stats.total_outfits = len(self._outfits)
        self._stats.total_presets = len(self._presets)
        self._stats.total_shares = len(self._share_links)
        self._stats.tick_count = self._tick_count
        self._stats.active_avatars = sum(
            1 for a in self._avatars.values()
            if a.status.value in _ACTIVE_STATUSES
        )

    def _player_avatar_list(self, player_id: str) -> List[PlayerAvatar]:
        ids = self._player_avatars.get(player_id, [])
        out: List[PlayerAvatar] = []
        for aid in ids:
            avatar = self._avatars.get(aid)
            if avatar is not None:
                out.append(avatar)
        return out

    def _avatar_share_list(self, avatar_id: str) -> List[AvatarShareLink]:
        ids = self._avatar_shares.get(avatar_id, [])
        out: List[AvatarShareLink] = []
        for sid in ids:
            link = self._share_links.get(sid)
            if link is not None:
                out.append(link)
        return out

    @staticmethod
    def _rarity_weight(rarity: RarityTier) -> float:
        return _RARITY_WEIGHTS.get(rarity.value, 1.0)

    def _avatar_palette(self, avatar: PlayerAvatar) -> List[str]:
        """Collect the hex colors of all parts on an avatar."""
        colors: List[str] = []
        for part_id in avatar.parts.values():
            part = self._parts.get(part_id)
            if part is not None:
                colors.append(part.color_hex)
        if avatar.background_color:
            colors.append(avatar.background_color)
        return colors

    # ------------------------------------------------------------------
    # Avatar Part Lifecycle
    # ------------------------------------------------------------------

    def register_part(
        self,
        part_id: str,
        name: str,
        part_type: Any,
        category: Any,
        rarity: Any,
        color_scheme: Any,
        mesh_url: str = "",
        texture_url: str = "",
        color_hex: str = "#808080",
        is_default: bool = False,
        is_unlockable: bool = False,
        unlock_condition: str = "",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Tuple[bool, str, Optional[AvatarPart]]:
        """Register a new modular avatar part in the catalog."""
        if not part_id or not name:
            return False, "part_id and name are required", None

        pt = _coerce_enum(AvatarPartType, part_type)
        if pt is None:
            return False, f"invalid part_type: {part_type}", None

        cat = _coerce_enum(AvatarCategory, category)
        if cat is None:
            return False, f"invalid category: {category}", None

        rar = _coerce_enum(RarityTier, rarity)
        if rar is None:
            return False, f"invalid rarity: {rarity}", None

        cs = _coerce_enum(ColorScheme, color_scheme)
        if cs is None:
            return False, f"invalid color_scheme: {color_scheme}", None

        with self._lock:
            if part_id in self._parts:
                return False, f"part_id already exists: {part_id}", None

            part = AvatarPart(
                part_id=part_id, name=name, part_type=pt, category=cat,
                rarity=rar, color_scheme=cs, mesh_url=mesh_url,
                texture_url=texture_url, color_hex=color_hex,
                is_default=bool(is_default), is_unlockable=bool(is_unlockable),
                unlock_condition=unlock_condition, metadata=metadata or {},
            )
            self._parts[part_id] = part
            _evict_fifo_dict(self._parts, _MAX_PARTS)
            self._emit("part_registered", avatar_id="",
                       description=f"Part registered: {name}",
                       data={"part_id": part_id, "part_type": pt.value})
            return True, "success", part

    def get_part(self, part_id: str) -> Optional[AvatarPart]:
        return self._parts.get(part_id)

    def list_parts(
        self,
        part_type: Optional[str] = None,
        limit: int = 200,
    ) -> List[AvatarPart]:
        """List avatar parts, optionally filtered by part type."""
        type_enum = _coerce_enum(AvatarPartType, part_type) if part_type else None
        cap = max(1, _safe_int(limit, 200))
        result: List[AvatarPart] = []
        for part in self._parts.values():
            if type_enum is not None and part.part_type != type_enum:
                continue
            result.append(part)
            if len(result) >= cap:
                break
        result.sort(key=lambda p: (p.part_type.value, p.rarity.value))
        return result

    def update_part(
        self,
        part_id: str,
        **kwargs: Any,
    ) -> Tuple[bool, str, Optional[AvatarPart]]:
        """Update mutable fields on an existing avatar part."""
        with self._lock:
            part = self._parts.get(part_id)
            if part is None:
                return False, "not found", None

            mutable = {"name", "part_type", "category", "rarity",
                       "color_scheme", "mesh_url", "texture_url",
                       "color_hex", "is_default", "is_unlockable",
                       "unlock_condition"}
            applied: List[str] = []
            for key, value in kwargs.items():
                if key not in mutable:
                    continue
                if key == "part_type":
                    pt = _coerce_enum(AvatarPartType, value)
                    if pt is None:
                        return False, f"invalid part_type: {value}", None
                    part.part_type = pt
                elif key == "category":
                    cat = _coerce_enum(AvatarCategory, value)
                    if cat is None:
                        return False, f"invalid category: {value}", None
                    part.category = cat
                elif key == "rarity":
                    rar = _coerce_enum(RarityTier, value)
                    if rar is None:
                        return False, f"invalid rarity: {value}", None
                    part.rarity = rar
                elif key == "color_scheme":
                    cs = _coerce_enum(ColorScheme, value)
                    if cs is None:
                        return False, f"invalid color_scheme: {value}", None
                    part.color_scheme = cs
                elif key in ("is_default", "is_unlockable"):
                    setattr(part, key, bool(value))
                else:
                    setattr(part, key, str(value))
                applied.append(key)

            if not applied:
                return False, "no valid fields supplied", part

            self._emit("part_updated", avatar_id="",
                       description=f"Part updated: {part_id}",
                       data={"part_id": part_id, "fields": applied})
            return True, "updated", part

    def remove_part(self, part_id: str) -> Tuple[bool, str]:
        with self._lock:
            part = self._parts.pop(part_id, None)
            if part is None:
                return False, "not found"
            self._emit("part_removed", avatar_id="",
                       description=f"Part removed: {part.name}",
                       data={"part_id": part_id})
            return True, "removed"

    # ------------------------------------------------------------------
    # Avatar Outfit Lifecycle
    # ------------------------------------------------------------------

    def create_outfit(
        self,
        outfit_id: str,
        name: str,
        description: str = "",
        part_ids: Optional[List[str]] = None,
        category: Any = AvatarCategory.HUMAN,
        rarity: Any = RarityTier.COMMON,
        is_featured: bool = False,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Tuple[bool, str, Optional[AvatarOutfit]]:
        """Create a named bundle of avatar parts."""
        if not outfit_id or not name:
            return False, "outfit_id and name are required", None

        cat = _coerce_enum(AvatarCategory, category, AvatarCategory.HUMAN)
        rar = _coerce_enum(RarityTier, rarity, RarityTier.COMMON)

        with self._lock:
            if outfit_id in self._outfits:
                return False, f"outfit_id already exists: {outfit_id}", None

            resolved_parts: List[str] = []
            for pid in (part_ids or []):
                if pid in self._parts:
                    resolved_parts.append(pid)

            outfit = AvatarOutfit(
                outfit_id=outfit_id, name=name, description=description,
                part_ids=resolved_parts, category=cat, rarity=rar,
                is_featured=bool(is_featured), created_at=_now(),
                metadata=metadata or {},
            )
            self._outfits[outfit_id] = outfit
            _evict_fifo_dict(self._outfits, _MAX_OUTFITS)
            self._emit("outfit_created", avatar_id="",
                       description=f"Outfit created: {name}",
                       data={"outfit_id": outfit_id,
                             "parts": len(resolved_parts)})
            return True, "success", outfit

    def get_outfit(self, outfit_id: str) -> Optional[AvatarOutfit]:
        return self._outfits.get(outfit_id)

    def list_outfits(
        self,
        category: str = "",
        limit: int = 100,
    ) -> List[AvatarOutfit]:
        cat_enum = _coerce_enum(AvatarCategory, category) if category else None
        cap = max(1, _safe_int(limit, 100))
        result: List[AvatarOutfit] = []
        for outfit in self._outfits.values():
            if cat_enum is not None and outfit.category != cat_enum:
                continue
            result.append(outfit)
            if len(result) >= cap:
                break
        result.sort(key=lambda o: (not o.is_featured, o.name))
        return result

    def update_outfit(
        self,
        outfit_id: str,
        **kwargs: Any,
    ) -> Tuple[bool, str, Optional[AvatarOutfit]]:
        """Update mutable fields on an existing outfit."""
        with self._lock:
            outfit = self._outfits.get(outfit_id)
            if outfit is None:
                return False, "not found", None

            mutable = {"name", "description", "part_ids", "category",
                       "rarity", "is_featured"}
            applied: List[str] = []
            for key, value in kwargs.items():
                if key not in mutable:
                    continue
                if key == "category":
                    cat = _coerce_enum(AvatarCategory, value)
                    if cat is None:
                        return False, f"invalid category: {value}", None
                    outfit.category = cat
                elif key == "rarity":
                    rar = _coerce_enum(RarityTier, value)
                    if rar is None:
                        return False, f"invalid rarity: {value}", None
                    outfit.rarity = rar
                elif key == "is_featured":
                    outfit.is_featured = bool(value)
                elif key == "part_ids":
                    if isinstance(value, list):
                        outfit.part_ids = [
                            pid for pid in value if pid in self._parts
                        ]
                else:
                    setattr(outfit, key, str(value))
                applied.append(key)

            if not applied:
                return False, "no valid fields supplied", outfit

            self._emit("outfit_updated", avatar_id="",
                       description=f"Outfit updated: {outfit_id}",
                       data={"outfit_id": outfit_id, "fields": applied})
            return True, "updated", outfit

    def remove_outfit(self, outfit_id: str) -> Tuple[bool, str]:
        with self._lock:
            outfit = self._outfits.pop(outfit_id, None)
            if outfit is None:
                return False, "not found"
            self._emit("outfit_removed", avatar_id="",
                       description=f"Outfit removed: {outfit.name}",
                       data={"outfit_id": outfit_id})
            return True, "removed"

    # ------------------------------------------------------------------
    # Player Avatar Lifecycle
    # ------------------------------------------------------------------

    def create_avatar(
        self,
        avatar_id: str,
        player_id: str,
        name: str,
        parts: Optional[Dict[str, str]] = None,
        outfit_id: str = "",
        animation: str = "",
        pose: str = "",
        background_color: str = "#1A1A2E",
        frame_id: str = "",
        status: Any = AvatarStatus.DRAFT,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Tuple[bool, str, Optional[PlayerAvatar]]:
        """Create a new player avatar from a set of parts."""
        if not avatar_id or not player_id or not name:
            return False, "avatar_id, player_id, and name are required", None

        st = _coerce_enum(AvatarStatus, status, AvatarStatus.DRAFT)

        with self._lock:
            if avatar_id in self._avatars:
                return False, f"avatar_id already exists: {avatar_id}", None

            resolved_parts: Dict[str, str] = {}
            for slot, pid in (parts or {}).items():
                if pid in self._parts:
                    resolved_parts[slot] = pid

            if outfit_id and outfit_id not in self._outfits:
                outfit_id = ""

            if animation and animation not in self._animations:
                animation = self._config.default_animation

            if pose and pose not in self._poses:
                pose = ""

            if frame_id and frame_id not in self._parts:
                frame_id = ""

            now_ts = _now()
            avatar = PlayerAvatar(
                avatar_id=avatar_id, player_id=player_id, name=name,
                parts=resolved_parts, outfit_id=outfit_id, animation=animation,
                pose=pose, background_color=background_color,
                frame_id=frame_id, status=st, created_at=now_ts,
                updated_at=now_ts, metadata=metadata or {},
            )
            self._avatars[avatar_id] = avatar
            bucket = self._player_avatars.setdefault(player_id, [])
            bucket.append(avatar_id)
            _evict_fifo_dict(self._avatars, self._config.max_avatars)
            _evict_fifo_list(bucket, _MAX_AVATARS_PER_PLAYER)

            self._emit("avatar_created", avatar_id=avatar_id,
                       description=f"Avatar created: {name}",
                       data={"player_id": player_id, "status": st.value})
            return True, "success", avatar

    def get_avatar(self, avatar_id: str) -> Optional[PlayerAvatar]:
        return self._avatars.get(avatar_id)

    def list_avatars(
        self,
        player_id: str,
        limit: int = 100,
    ) -> List[PlayerAvatar]:
        """List avatars owned by a specific player."""
        cap = max(1, _safe_int(limit, 100))
        result = self._player_avatar_list(player_id)
        result.sort(key=lambda a: a.updated_at, reverse=True)
        return result[:cap]

    def update_avatar(
        self,
        avatar_id: str,
        **kwargs: Any,
    ) -> Tuple[bool, str, Optional[PlayerAvatar]]:
        """Update mutable fields on an existing avatar."""
        with self._lock:
            avatar = self._avatars.get(avatar_id)
            if avatar is None:
                return False, "not found", None

            mutable = {"name", "parts", "outfit_id", "animation", "pose",
                       "background_color", "frame_id", "status"}
            applied: List[str] = []
            for key, value in kwargs.items():
                if key not in mutable:
                    continue
                if key == "status":
                    st = _coerce_enum(AvatarStatus, value)
                    if st is None:
                        return False, f"invalid status: {value}", None
                    avatar.status = st
                elif key == "parts":
                    if isinstance(value, dict):
                        resolved: Dict[str, str] = {}
                        for slot, pid in value.items():
                            if pid in self._parts:
                                resolved[slot] = pid
                        avatar.parts = resolved
                elif key == "outfit_id":
                    if value and value in self._outfits:
                        avatar.outfit_id = str(value)
                    else:
                        avatar.outfit_id = ""
                elif key == "animation":
                    if value and value in self._animations:
                        avatar.animation = str(value)
                    else:
                        avatar.animation = ""
                elif key == "pose":
                    if value and value in self._poses:
                        avatar.pose = str(value)
                    else:
                        avatar.pose = ""
                elif key == "frame_id":
                    if value and value in self._parts:
                        avatar.frame_id = str(value)
                    else:
                        avatar.frame_id = ""
                else:
                    setattr(avatar, key, str(value))
                applied.append(key)

            if not applied:
                return False, "no valid fields supplied", avatar

            avatar.updated_at = _now()
            self._emit("avatar_updated", avatar_id=avatar_id,
                       description=f"Avatar updated: {avatar.name}",
                       data={"fields": applied})
            return True, "updated", avatar

    def remove_avatar(self, avatar_id: str) -> Tuple[bool, str]:
        with self._lock:
            avatar = self._avatars.pop(avatar_id, None)
            if avatar is None:
                return False, "not found"
            bucket = self._player_avatars.get(avatar.player_id)
            if bucket:
                try:
                    bucket.remove(avatar_id)
                except ValueError:
                    pass
            share_ids = self._avatar_shares.pop(avatar_id, [])
            for sid in share_ids:
                self._share_links.pop(sid, None)
            self._emit("avatar_removed", avatar_id=avatar_id,
                       description=f"Avatar removed: {avatar.name}",
                       data={"player_id": avatar.player_id})
            return True, "removed"

    # ------------------------------------------------------------------
    # Avatar Part Mutation
    # ------------------------------------------------------------------

    def set_avatar_part(
        self,
        avatar_id: str,
        part_id: str,
    ) -> Tuple[bool, str, Optional[PlayerAvatar]]:
        """Set or replace a part on an avatar. The slot is derived from the
        part's type."""
        with self._lock:
            avatar = self._avatars.get(avatar_id)
            if avatar is None:
                return False, "avatar not found", None
            part = self._parts.get(part_id)
            if part is None:
                return False, "part not found", None

            slot = part.part_type.value
            avatar.parts[slot] = part_id
            avatar.updated_at = _now()
            self._emit("avatar_part_set", avatar_id=avatar_id,
                       description=f"Part set: {part.name} on {avatar.name}",
                       data={"part_id": part_id, "slot": slot})
            return True, "success", avatar

    def remove_avatar_part(
        self,
        avatar_id: str,
        slot: str,
    ) -> Tuple[bool, str, Optional[PlayerAvatar]]:
        """Remove a part from a specific slot on an avatar."""
        with self._lock:
            avatar = self._avatars.get(avatar_id)
            if avatar is None:
                return False, "avatar not found", None
            if slot not in avatar.parts:
                return False, f"slot not occupied: {slot}", None

            removed_part_id = avatar.parts.pop(slot)
            avatar.updated_at = _now()
            self._emit("avatar_part_removed", avatar_id=avatar_id,
                       description=f"Part removed from slot {slot}",
                       data={"slot": slot, "part_id": removed_part_id})
            return True, "success", avatar

    def set_avatar_animation(
        self,
        avatar_id: str,
        animation_id: str,
    ) -> Tuple[bool, str, Optional[PlayerAvatar]]:
        """Set the driving animation on an avatar."""
        with self._lock:
            avatar = self._avatars.get(avatar_id)
            if avatar is None:
                return False, "avatar not found", None
            if animation_id and animation_id not in self._animations:
                return False, "animation not found", None

            avatar.animation = animation_id
            avatar.updated_at = _now()
            self._emit("avatar_animation_set", avatar_id=avatar_id,
                       description=f"Animation set: {animation_id}",
                       data={"animation_id": animation_id})
            return True, "success", avatar

    def set_avatar_pose(
        self,
        avatar_id: str,
        pose_id: str,
    ) -> Tuple[bool, str, Optional[PlayerAvatar]]:
        """Set the static pose on an avatar."""
        with self._lock:
            avatar = self._avatars.get(avatar_id)
            if avatar is None:
                return False, "avatar not found", None
            if pose_id and pose_id not in self._poses:
                return False, "pose not found", None

            avatar.pose = pose_id
            avatar.updated_at = _now()
            self._emit("avatar_pose_set", avatar_id=avatar_id,
                       description=f"Pose set: {pose_id}",
                       data={"pose_id": pose_id})
            return True, "success", avatar

    # ------------------------------------------------------------------
    # Animation Lifecycle
    # ------------------------------------------------------------------

    def register_animation(
        self,
        animation_id: str,
        name: str,
        animation_type: Any,
        duration: float = 1.0,
        loop: bool = False,
        frames: Optional[List[Dict[str, Any]]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Tuple[bool, str, Optional[AvatarAnimation]]:
        """Register a new avatar animation."""
        if not animation_id or not name:
            return False, "animation_id and name are required", None

        atype = _coerce_enum(AnimationType, animation_type)
        if atype is None:
            return False, f"invalid animation_type: {animation_type}", None

        with self._lock:
            if animation_id in self._animations:
                return False, f"animation_id already exists: {animation_id}", None

            anim = AvatarAnimation(
                animation_id=animation_id, name=name, type=atype,
                duration=max(0.0, _safe_float(duration, 1.0)),
                loop=bool(loop), frames=list(frames or []),
                metadata=metadata or {},
            )
            self._animations[animation_id] = anim
            _evict_fifo_dict(self._animations, _MAX_ANIMATIONS)
            self._emit("animation_registered", avatar_id="",
                       description=f"Animation registered: {name}",
                       data={"animation_id": animation_id,
                             "type": atype.value})
            return True, "success", anim

    def get_animation(self, animation_id: str) -> Optional[AvatarAnimation]:
        return self._animations.get(animation_id)

    def list_animations(
        self,
        animation_type: str = "",
        limit: int = 100,
    ) -> List[AvatarAnimation]:
        type_enum = _coerce_enum(AnimationType, animation_type) if animation_type else None
        cap = max(1, _safe_int(limit, 100))
        result: List[AvatarAnimation] = []
        for anim in self._animations.values():
            if type_enum is not None and anim.type != type_enum:
                continue
            result.append(anim)
            if len(result) >= cap:
                break
        result.sort(key=lambda a: a.name)
        return result

    def remove_animation(self, animation_id: str) -> Tuple[bool, str]:
        with self._lock:
            anim = self._animations.pop(animation_id, None)
            if anim is None:
                return False, "not found"
            for avatar in self._avatars.values():
                if avatar.animation == animation_id:
                    avatar.animation = ""
                    avatar.updated_at = _now()
            self._emit("animation_removed", avatar_id="",
                       description=f"Animation removed: {anim.name}",
                       data={"animation_id": animation_id})
            return True, "removed"

    # ------------------------------------------------------------------
    # Pose Lifecycle
    # ------------------------------------------------------------------

    def register_pose(
        self,
        pose_id: str,
        name: str,
        pose_type: Any,
        bone_data: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Tuple[bool, str, Optional[AvatarPose]]:
        """Register a new avatar pose."""
        if not pose_id or not name:
            return False, "pose_id and name are required", None

        ptype = _coerce_enum(PoseType, pose_type)
        if ptype is None:
            return False, f"invalid pose_type: {pose_type}", None

        with self._lock:
            if pose_id in self._poses:
                return False, f"pose_id already exists: {pose_id}", None

            pose = AvatarPose(
                pose_id=pose_id, name=name, type=ptype,
                bone_data=bone_data or {}, metadata=metadata or {},
            )
            self._poses[pose_id] = pose
            _evict_fifo_dict(self._poses, _MAX_POSES)
            self._emit("pose_registered", avatar_id="",
                       description=f"Pose registered: {name}",
                       data={"pose_id": pose_id, "type": ptype.value})
            return True, "success", pose

    def get_pose(self, pose_id: str) -> Optional[AvatarPose]:
        return self._poses.get(pose_id)

    def list_poses(
        self,
        pose_type: str = "",
        limit: int = 100,
    ) -> List[AvatarPose]:
        type_enum = _coerce_enum(PoseType, pose_type) if pose_type else None
        cap = max(1, _safe_int(limit, 100))
        result: List[AvatarPose] = []
        for pose in self._poses.values():
            if type_enum is not None and pose.type != type_enum:
                continue
            result.append(pose)
            if len(result) >= cap:
                break
        result.sort(key=lambda p: p.name)
        return result

    def remove_pose(self, pose_id: str) -> Tuple[bool, str]:
        with self._lock:
            pose = self._poses.pop(pose_id, None)
            if pose is None:
                return False, "not found"
            for avatar in self._avatars.values():
                if avatar.pose == pose_id:
                    avatar.pose = ""
                    avatar.updated_at = _now()
            self._emit("pose_removed", avatar_id="",
                       description=f"Pose removed: {pose.name}",
                       data={"pose_id": pose_id})
            return True, "removed"

    # ------------------------------------------------------------------
    # Preset Lifecycle
    # ------------------------------------------------------------------

    def create_preset(
        self,
        preset_id: str,
        name: str,
        description: str = "",
        avatar_config: Optional[Dict[str, Any]] = None,
        category: Any = AvatarCategory.HUMAN,
        is_featured: bool = False,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Tuple[bool, str, Optional[AvatarPreset]]:
        """Create a reusable avatar configuration preset."""
        if not preset_id or not name:
            return False, "preset_id and name are required", None

        cat = _coerce_enum(AvatarCategory, category, AvatarCategory.HUMAN)

        with self._lock:
            if preset_id in self._presets:
                return False, f"preset_id already exists: {preset_id}", None

            preset = AvatarPreset(
                preset_id=preset_id, name=name, description=description,
                avatar_config=avatar_config or {}, category=cat,
                is_featured=bool(is_featured), usage_count=0,
                created_at=_now(), metadata=metadata or {},
            )
            self._presets[preset_id] = preset
            _evict_fifo_dict(self._presets, self._config.max_presets)
            self._emit("preset_created", avatar_id="",
                       description=f"Preset created: {name}",
                       data={"preset_id": preset_id})
            return True, "success", preset

    def get_preset(self, preset_id: str) -> Optional[AvatarPreset]:
        return self._presets.get(preset_id)

    def list_presets(
        self,
        category: str = "",
        limit: int = 100,
    ) -> List[AvatarPreset]:
        cat_enum = _coerce_enum(AvatarCategory, category) if category else None
        cap = max(1, _safe_int(limit, 100))
        result: List[AvatarPreset] = []
        for preset in self._presets.values():
            if cat_enum is not None and preset.category != cat_enum:
                continue
            result.append(preset)
            if len(result) >= cap:
                break
        result.sort(key=lambda p: (not p.is_featured, -p.usage_count))
        return result

    def apply_preset(
        self,
        preset_id: str,
        player_id: str,
        avatar_id: str = "",
        name: str = "",
    ) -> Tuple[bool, str, Optional[PlayerAvatar]]:
        """Create a new avatar from a saved preset.

        The preset's avatar_config supplies parts, animation, pose,
        background color, and other fields. The preset's usage_count is
        incremented on success.
        """
        if not preset_id or not player_id:
            return False, "preset_id and player_id are required", None

        with self._lock:
            preset = self._presets.get(preset_id)
            if preset is None:
                return False, "preset not found", None

            config = preset.avatar_config
            aid = avatar_id or _new_id("avatar")
            avatar_name = name or f"{preset.name} Clone"

            parts = config.get("parts", {})
            outfit_id = config.get("outfit_id", "")
            animation = config.get("animation", "")
            pose = config.get("pose", "")
            bg_color = config.get("background_color", "#1A1A2E")
            frame_id = config.get("frame_id", "")

            ok, msg, avatar = self.create_avatar(
                avatar_id=aid, player_id=player_id, name=avatar_name,
                parts=parts, outfit_id=outfit_id, animation=animation,
                pose=pose, background_color=bg_color, frame_id=frame_id,
                status=AvatarStatus.DRAFT,
                metadata={"source_preset": preset_id},
            )
            if not ok or avatar is None:
                return False, msg, None

            preset.usage_count += 1
            self._emit("preset_applied", avatar_id=aid,
                       description=f"Preset applied: {preset.name}",
                       data={"preset_id": preset_id,
                             "avatar_id": aid,
                             "player_id": player_id})
            return True, "success", avatar

    def remove_preset(self, preset_id: str) -> Tuple[bool, str]:
        with self._lock:
            preset = self._presets.pop(preset_id, None)
            if preset is None:
                return False, "not found"
            self._emit("preset_removed", avatar_id="",
                       description=f"Preset removed: {preset.name}",
                       data={"preset_id": preset_id})
            return True, "removed"

    # ------------------------------------------------------------------
    # Sharing Lifecycle
    # ------------------------------------------------------------------

    def share_avatar(
        self,
        avatar_id: str,
        platform: Any,
        expires_in: int = _DEFAULT_SHARE_TTL,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Tuple[bool, str, Optional[AvatarShareLink]]:
        """Generate an expiring share link for an avatar."""
        if not avatar_id:
            return False, "avatar_id is required", None

        plat = _coerce_enum(SharePlatform, platform)
        if plat is None:
            return False, f"invalid platform: {platform}", None

        with self._lock:
            avatar = self._avatars.get(avatar_id)
            if avatar is None:
                return False, "avatar not found", None

            if not self._config.enable_sharing:
                return False, "sharing is disabled", None

            share_id = _new_id("share")
            ttl = max(60, _safe_int(expires_in, _DEFAULT_SHARE_TTL))
            expires_dt = datetime.utcnow() + timedelta(seconds=ttl)

            link = AvatarShareLink(
                share_id=share_id, avatar_id=avatar_id, platform=plat,
                url=f"{_SHARE_URL_BASE}{share_id}",
                expires_at=expires_dt.isoformat() + "Z",
                view_count=0, created_at=_now(),
                metadata=metadata or {},
            )
            self._share_links[share_id] = link
            self._avatar_shares.setdefault(avatar_id, []).append(share_id)
            _evict_fifo_dict(self._share_links, _MAX_SHARE_LINKS)
            self._emit("share_created", avatar_id=avatar_id,
                       description=f"Share link created: {plat.value}",
                       data={"share_id": share_id, "platform": plat.value})
            return True, "success", link

    def get_share_link(self, share_id: str) -> Optional[AvatarShareLink]:
        link = self._share_links.get(share_id)
        if link is None:
            return None
        with self._lock:
            link.view_count += 1
        return link

    def list_share_links(
        self,
        avatar_id: str = "",
        platform: str = "",
        limit: int = 100,
    ) -> List[AvatarShareLink]:
        plat_enum = _coerce_enum(SharePlatform, platform) if platform else None
        cap = max(1, _safe_int(limit, 100))
        result: List[AvatarShareLink] = []
        if avatar_id:
            source = self._avatar_share_list(avatar_id)
        else:
            source = list(self._share_links.values())
        for link in source:
            if plat_enum is not None and link.platform != plat_enum:
                continue
            result.append(link)
            if len(result) >= cap:
                break
        result.sort(key=lambda s: s.created_at, reverse=True)
        return result

    def revoke_share(self, share_id: str) -> Tuple[bool, str]:
        with self._lock:
            link = self._share_links.pop(share_id, None)
            if link is None:
                return False, "not found"
            bucket = self._avatar_shares.get(link.avatar_id)
            if bucket:
                try:
                    bucket.remove(share_id)
                except ValueError:
                    pass
            self._emit("share_revoked", avatar_id=link.avatar_id,
                       description=f"Share link revoked: {share_id}",
                       data={"share_id": share_id})
            return True, "revoked"

    # ------------------------------------------------------------------
    # Featured Status
    # ------------------------------------------------------------------

    def feature_avatar(self, avatar_id: str) -> Tuple[bool, str, Optional[PlayerAvatar]]:
        """Promote an avatar to featured status for community showcase."""
        with self._lock:
            avatar = self._avatars.get(avatar_id)
            if avatar is None:
                return False, "not found", None
            avatar.status = AvatarStatus.FEATURED
            avatar.updated_at = _now()
            self._emit("avatar_featured", avatar_id=avatar_id,
                       description=f"Avatar featured: {avatar.name}",
                       data={"player_id": avatar.player_id})
            return True, "featured", avatar

    def unfeature_avatar(self, avatar_id: str) -> Tuple[bool, str, Optional[PlayerAvatar]]:
        """Demote a featured avatar back to published status."""
        with self._lock:
            avatar = self._avatars.get(avatar_id)
            if avatar is None:
                return False, "not found", None
            if avatar.status == AvatarStatus.FEATURED:
                avatar.status = AvatarStatus.PUBLISHED
            avatar.updated_at = _now()
            self._emit("avatar_unfeatured", avatar_id=avatar_id,
                       description=f"Avatar unfeatured: {avatar.name}",
                       data={"player_id": avatar.player_id})
            return True, "unfeatured", avatar

    # ------------------------------------------------------------------
    # Procedural Thumbnail Generation
    # ------------------------------------------------------------------

    def generate_thumbnail(
        self,
        avatar_id: str,
        size: int = _THUMBNAIL_SIZE,
    ) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        """Produce a deterministic procedural thumbnail for an avatar.

        Generates a square pixel grid whose colors are derived from the
        avatar's part colors and background, arranged into a vertically
        symmetric silhouette pattern seeded by the avatar_id hash. The
        result is a dictionary describing the palette, dimensions, and
        pixel data so a frontend can render it without a GPU backend.
        """
        with self._lock:
            avatar = self._avatars.get(avatar_id)
            if avatar is None:
                return False, "avatar not found", None

            grid_size = max(8, min(64, _safe_int(size, _THUMBNAIL_SIZE)))
            palette = self._avatar_palette(avatar)
            if not palette:
                palette = [avatar.background_color or "#1A1A2E"]

            bg_color = avatar.background_color or "#1A1A2E"
            bg_rgb = _hex_to_rgb(bg_color)

            # Derive part colors with rarity-weighted prominence.
            part_colors: List[str] = []
            part_weights: List[float] = []
            for part_id in avatar.parts.values():
                part = self._parts.get(part_id)
                if part is not None:
                    part_colors.append(part.color_hex)
                    part_weights.append(self._rarity_weight(part.rarity))
            if not part_colors:
                part_colors = [palette[0]]
                part_weights = [1.0]

            dominant_color = _mix_hex_colors(part_colors, part_weights)
            dominant_rgb = _hex_to_rgb(dominant_color)

            seed = _hash_str(avatar_id)
            pixels: List[str] = []
            half = grid_size // 2

            for y in range(grid_size):
                for x in range(half):
                    # Normalized position in the left half of the grid.
                    nx = x / max(1, half - 1)
                    ny = y / max(1, grid_size - 1)

                    # Silhouette mask: a vertical body shape that is wider
                    # in the middle and tapers at top and bottom.
                    center_dist = abs(ny - 0.45)
                    body_width = _lerp(0.35, 0.7, 1.0 - center_dist * 1.8)
                    body_width = _clamp(body_width, 0.1, 0.8)

                    in_body = nx < body_width
                    # Deterministic noise from the seed for texture.
                    noise_val = ((seed >> ((x * 7 + y * 13) % 24)) & 0xFF) / 255.0
                    in_body = in_body and noise_val > 0.15

                    if in_body:
                        # Blend dominant part color with a noise-driven shade.
                        shade = _lerp(0.7, 1.1, noise_val)
                        r = _clamp(dominant_rgb[0] * shade, 0, 255)
                        g = _clamp(dominant_rgb[1] * shade, 0, 255)
                        b = _clamp(dominant_rgb[2] * shade, 0, 255)
                        pixel = _rgb_to_hex(r, g, b)
                    else:
                        # Background with a subtle vertical gradient.
                        grad = _lerp(1.0, 0.7, ny)
                        r = _clamp(bg_rgb[0] * grad, 0, 255)
                        g = _clamp(bg_rgb[1] * grad, 0, 255)
                        b = _clamp(bg_rgb[2] * grad, 0, 255)
                        pixel = _rgb_to_hex(r, g, b)

                    pixels.append(pixel)

            # Mirror the left half to the right half for vertical symmetry.
            full_pixels: List[str] = []
            for y in range(grid_size):
                row_left = pixels[y * half:(y + 1) * half]
                full_pixels.extend(row_left)
                full_pixels.extend(reversed(row_left))

            thumbnail = {
                "thumbnail_id": _new_id("thumb"),
                "avatar_id": avatar_id,
                "avatar_name": avatar.name,
                "width": grid_size,
                "height": grid_size,
                "palette": palette[:8],
                "dominant_color": dominant_color,
                "background_color": bg_color,
                "pixels": full_pixels,
                "format": "pixel_grid",
                "generated_at": _now(),
            }

            avatar.metadata["thumbnail"] = thumbnail
            avatar.updated_at = _now()
            self._emit("thumbnail_generated", avatar_id=avatar_id,
                       description=f"Thumbnail generated: {avatar.name}",
                       data={"size": grid_size,
                             "dominant_color": dominant_color})
            return True, "success", thumbnail

    # ------------------------------------------------------------------
    # Event Log and Observability
    # ------------------------------------------------------------------

    def list_events(
        self,
        avatar_id: str = "",
        limit: int = 100,
    ) -> List[AvatarSystemEvent]:
        cap = max(1, _safe_int(limit, 100))
        result: List[AvatarSystemEvent] = []
        for e in reversed(self._events):
            if avatar_id and e.avatar_id != avatar_id:
                continue
            result.append(e)
            if len(result) >= cap:
                break
        return result

    def get_status(self) -> Dict[str, Any]:
        self._refresh_stats()
        return {
            "initialized": self._initialized,
            "parts": len(self._parts),
            "outfits": len(self._outfits),
            "avatars": len(self._avatars),
            "animations": len(self._animations),
            "poses": len(self._poses),
            "presets": len(self._presets),
            "share_links": len(self._share_links),
            "events": len(self._events),
            "tick_count": self._tick_count,
            "config": self._config.to_dict(),
        }

    def get_stats(self) -> AvatarSystemStats:
        self._refresh_stats()
        return self._stats

    def get_snapshot(self) -> AvatarSystemSnapshot:
        self._refresh_stats()
        return AvatarSystemSnapshot(
            timestamp=_now(),
            avatars=[a.to_dict() for a in list(self._avatars.values())[-100:]],
            parts=[p.to_dict() for p in list(self._parts.values())[-100:]],
            outfits=[o.to_dict() for o in list(self._outfits.values())[-50:]],
            presets=[p.to_dict() for p in list(self._presets.values())[-50:]],
            stats=self._stats.to_dict(),
        )

    def get_config(self) -> AvatarSystemConfig:
        return self._config

    def set_config(self, **kwargs: Any) -> Tuple[bool, str, AvatarSystemConfig]:
        """Update tunable configuration fields.

        Only known fields on AvatarSystemConfig are accepted. Numeric fields
        are coerced and clamped to safe ranges.
        """
        with self._lock:
            known = set(self._config.__dataclass_fields__.keys())
            applied: List[str] = []
            for key, value in kwargs.items():
                if key not in known:
                    continue
                if key == "max_avatars":
                    self._config.max_avatars = max(1, _safe_int(value, 10000))
                elif key == "max_parts_per_avatar":
                    self._config.max_parts_per_avatar = max(1, _safe_int(value, 50))
                elif key == "max_presets":
                    self._config.max_presets = max(1, _safe_int(value, 2000))
                elif key == "default_animation":
                    self._config.default_animation = str(value)
                elif key == "auto_generate_thumbnail":
                    self._config.auto_generate_thumbnail = bool(value)
                elif key == "enable_sharing":
                    self._config.enable_sharing = bool(value)
                else:
                    continue
                applied.append(key)

            if not applied:
                return False, "no valid config fields supplied", self._config

            self._emit("config_updated", avatar_id="",
                       description="Configuration updated",
                       data={"fields": applied})
            return True, "updated", self._config

    # ------------------------------------------------------------------
    # Tick and Lifecycle
    # ------------------------------------------------------------------

    def tick(self, dt: float = 1.0) -> Dict[str, Any]:
        """Advance the avatar system by one tick.

        Refreshes statistics, expires share links whose expiry has passed,
        and auto-generates thumbnails for avatars that lack one when the
        config flag is set.
        """
        with self._lock:
            self._tick_count += 1
            self._refresh_stats()

            expired_shares: List[str] = []
            now_dt = datetime.utcnow()
            for sid, link in list(self._share_links.items()):
                exp = _parse_iso(link.expires_at)
                if exp is not None and exp < now_dt:
                    expired_shares.append(sid)

            for sid in expired_shares:
                link = self._share_links.pop(sid, None)
                if link is not None:
                    bucket = self._avatar_shares.get(link.avatar_id)
                    if bucket:
                        try:
                            bucket.remove(sid)
                        except ValueError:
                            pass

            thumbnails_generated: List[str] = []
            if self._config.auto_generate_thumbnail:
                for avatar in list(self._avatars.values()):
                    if "thumbnail" not in avatar.metadata:
                        ok, _, _ = self.generate_thumbnail(avatar.avatar_id)
                        if ok:
                            thumbnails_generated.append(avatar.avatar_id)
                            if len(thumbnails_generated) >= 20:
                                break

            self._emit("tick", avatar_id="",
                       description=f"Tick {self._tick_count}",
                       data={"tick": self._tick_count,
                             "dt": _safe_float(dt, 1.0),
                             "expired_shares": expired_shares,
                             "thumbnails_generated": thumbnails_generated})

            return {
                "status": "ok",
                "tick": self._tick_count,
                "dt": _safe_float(dt, 1.0),
                "parts": len(self._parts),
                "avatars": len(self._avatars),
                "expired_shares": expired_shares,
                "thumbnails_generated": thumbnails_generated,
                "stats": self._stats.to_dict(),
            }

    def reset(self) -> None:
        """Clear all system state and re-seed the canonical dataset."""
        with self._lock:
            self._parts.clear()
            self._outfits.clear()
            self._avatars.clear()
            self._player_avatars.clear()
            self._animations.clear()
            self._poses.clear()
            self._presets.clear()
            self._share_links.clear()
            self._avatar_shares.clear()
            self._events.clear()
            self._config = AvatarSystemConfig()
            self._stats = AvatarSystemStats()
            self._tick_count = 0
            self._initialized = False
            self._seed()


# ---------------------------------------------------------------------------
# Factory Function
# ---------------------------------------------------------------------------

def get_player_avatar_system() -> PlayerAvatarSystem:
    """Return the shared PlayerAvatarSystem singleton instance."""
    return PlayerAvatarSystem.get_instance()


# ---------------------------------------------------------------------------
# Exported Symbols
# ---------------------------------------------------------------------------

__all__ = [
    # Enums
    "AvatarPartType",
    "AvatarCategory",
    "AnimationType",
    "PoseType",
    "RarityTier",
    "ColorScheme",
    "AvatarStatus",
    "SharePlatform",
    # Data classes
    "AvatarPart",
    "AvatarOutfit",
    "PlayerAvatar",
    "AvatarAnimation",
    "AvatarPose",
    "AvatarPreset",
    "AvatarShareLink",
    "AvatarSystemConfig",
    "AvatarSystemStats",
    "AvatarSystemSnapshot",
    "AvatarSystemEvent",
    # Main system
    "PlayerAvatarSystem",
    "get_player_avatar_system",
]
